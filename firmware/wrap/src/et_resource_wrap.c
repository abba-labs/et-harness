#include "et_resource_wrap.h"

/**
 * @file et_resource_wrap.c
 * @brief Static monotonic resource pool with generation-checked opaque handles.
 */

#include <string.h>

#define ET_RESOURCE_HANDLE_SLOT_BITS 16u

typedef struct
{
    uint32_t offset;
    uint32_t size;
    uint32_t alignment;
    uint16_t generation;
    uint8_t in_use;
    uint8_t reserved;
} et_resource_descriptor_t;

static uint32_t resource_pool_words[(ET_RESOURCE_WRAP_POOL_SIZE + sizeof(uint32_t) - 1u) /
                                    sizeof(uint32_t)] ET_RESOURCE_WRAP_POOL_SECTION;
static et_resource_descriptor_t resource_descriptors[ET_RESOURCE_WRAP_MAX_RESOURCES];
static uint32_t resource_pool_used;
static uint16_t resource_generation = 1u;
static uint8_t resource_initialized;

/**
 * @brief Return the byte-addressable view of the statically aligned Resource backing arena.
 *
 * @note The returned pointer aliases platform-owned static storage. This helper allocates nothing and
 *       does not change descriptor, generation or pool-allocation state.
 *
 * @return Pointer to the first byte of the Resource backing arena.
 */
static uint8_t *resource_pool(void)
{
    return (uint8_t *)resource_pool_words;
}

/**
 * @brief Test whether one unsigned alignment value is a nonzero power of two.
 *
 * @param[in] value Alignment candidate in bytes.
 *
 * @note This is a pure arithmetic helper used before monotonic pool allocation; it has no state or
 *       hardware side effect.
 *
 * @return Nonzero when value is a power of two, otherwise zero.
 */
static uint8_t is_power_of_two(uint32_t value)
{
    return (uint8_t)((value != 0u) && ((value & (value - 1u)) == 0u));
}

/**
 * @brief Round one byte offset upward to a caller-validated power-of-two alignment.
 *
 * @param[in] value Unaligned byte offset.
 * @param[in] alignment Power-of-two alignment in bytes.
 *
 * @note The caller must validate alignment before calling this helper. No pool or descriptor state is
 *       modified by the arithmetic operation.
 *
 * @return Smallest aligned offset greater than or equal to value.
 */
static uint32_t align_up(uint32_t value, uint32_t alignment)
{
    return (value + alignment - 1u) & ~(alignment - 1u);
}

/**
 * @brief Encode one descriptor generation and slot into an opaque nonzero Resource handle.
 *
 * @param[in] generation Current Resource-generation value.
 * @param[in] slot Zero-based descriptor slot index.
 *
 * @note The low half stores slot + 1 so handle value zero is permanently invalid. Handle generation
 *       prevents a stale handle from resolving after reset or last-allocation destruction.
 *
 * @return Encoded opaque Resource handle.
 */
static et_resource_handle_t make_handle(uint16_t generation, uint16_t slot)
{
    /* Low half stores slot+1 so handle value zero can never become valid. */
    return ((uint32_t)generation << ET_RESOURCE_HANDLE_SLOT_BITS) | ((uint32_t)slot + 1u);
}

/**
 * @brief Resolve one opaque Resource handle to its live generation-matched descriptor.
 *
 * @param[in] handle Opaque Resource handle supplied by a trusted caller.
 * @param[out] descriptor Matching live descriptor owned by the Resource pool.
 *
 * @note Resolution validates initialization, nonzero slot encoding, descriptor bounds, in-use state
 *       and generation. The returned pointer aliases internal descriptor storage and transfers no ownership.
 *
 * @return ET_WRAP_STATUS_OK when handle resolves to one current live descriptor.
 * @return ET_WRAP_STATUS_STATE_ERROR when Resource Wrap is not initialized or handle is invalid-zero.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT for a NULL output pointer or stale/malformed handle.
 */
static et_wrap_status_t find_descriptor(et_resource_handle_t handle,
                                        et_resource_descriptor_t **descriptor)
{
    uint16_t encoded_slot;
    uint16_t slot;
    uint16_t generation;

    if (descriptor == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *descriptor = NULL;

    if ((resource_initialized == 0u) || (handle == ET_RESOURCE_HANDLE_INVALID))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    encoded_slot = (uint16_t)(handle & UINT16_MAX);

    if (encoded_slot == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    slot = (uint16_t)(encoded_slot - 1u);
    generation = (uint16_t)(handle >> ET_RESOURCE_HANDLE_SLOT_BITS);

    if ((slot >= ET_RESOURCE_WRAP_MAX_RESOURCES) || (resource_descriptors[slot].in_use == 0u) ||
        (resource_descriptors[slot].generation != generation))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *descriptor = &resource_descriptors[slot];

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one offset/size pair against a live Resource descriptor without overflow.
 *
 * @param[in] descriptor Live Resource descriptor defining the accessible byte range.
 * @param[in] offset Byte offset from the Resource base.
 * @param[in] size Number of bytes requested.
 *
 * @note The subtraction form avoids offset + size overflow while proving the complete range remains
 *       inside the descriptor. No memory is read or written.
 *
 * @return ET_WRAP_STATUS_OK when the complete range is inside the Resource.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when descriptor or range is invalid.
 */
static et_wrap_status_t validate_range(const et_resource_descriptor_t *descriptor, uint32_t offset,
                                       uint32_t size)
{
    if (descriptor == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((offset > descriptor->size) || (size > (descriptor->size - offset)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Initialize the bounded Resource descriptor table and monotonic backing arena.
 *
 * @note Initialization clears all static Resource bytes/descriptors, resets allocation to offset zero
 *       and starts generation at one. Repeated initialization is idempotent and performs no hardware access.
 *
 * @return ET_WRAP_STATUS_OK after initialization or when already initialized.
 */
et_wrap_status_t et_resource_wrap_init(void)
{
    if (resource_initialized != 0u)
    {
        return ET_WRAP_STATUS_OK;
    }

    (void)memset(resource_pool_words, 0, sizeof(resource_pool_words));
    (void)memset(resource_descriptors, 0, sizeof(resource_descriptors));
    resource_pool_used = 0u;
    resource_generation = 1u;
    resource_initialized = 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Release every live Resource and restart monotonic arena allocation from offset zero.
 *
 * @note Reset zeroes the complete backing arena and descriptor table, then advances generation so
 *       every previously issued opaque handle becomes stale. Generation value zero is skipped.
 *
 * @return ET_WRAP_STATUS_OK when the initialized pool is reset.
 * @return ET_WRAP_STATUS_STATE_ERROR when Resource Wrap has not been initialized.
 */
et_wrap_status_t et_resource_wrap_reset(void)
{
    if (resource_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    (void)memset(resource_pool_words, 0, sizeof(resource_pool_words));
    (void)memset(resource_descriptors, 0, sizeof(resource_descriptors));
    resource_pool_used = 0u;
    ++resource_generation;

    if (resource_generation == 0u)
    {
        resource_generation = 1u;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reserve one aligned bounded buffer from the static monotonic Resource arena.
 *
 * @param[in] size Requested Resource size in bytes.
 * @param[in] alignment Requested power-of-two alignment in bytes.
 * @param[out] handle Opaque generation-checked handle for the new Resource.
 *
 * @note Allocation never uses a heap and never compacts existing Resources. The arena high-water mark
 *       moves forward only after both byte-range capacity and a free descriptor slot are confirmed.
 *
 * @return ET_WRAP_STATUS_OK when a Resource is allocated and handle is published.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT for invalid size/alignment/output arguments.
 * @return ET_WRAP_STATUS_STATE_ERROR when Resource Wrap is not initialized.
 * @return ET_WRAP_STATUS_NO_RESOURCE when arena bytes or descriptor slots are exhausted.
 */
et_wrap_status_t et_resource_wrap_create(uint32_t size, uint32_t alignment,
                                         et_resource_handle_t *handle)
{
    uint32_t aligned_offset;
    uint16_t slot;

    /* Phase 1: Validate initialization, request size and alignment before touching allocation state. */
    if (handle == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *handle = ET_RESOURCE_HANDLE_INVALID;

    if (resource_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if ((size == 0u) || (is_power_of_two(alignment) == 0u) ||
        (alignment > ET_RESOURCE_WRAP_MAX_ALIGNMENT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Prove the aligned byte range fits before reserving any descriptor. */
    aligned_offset = align_up(resource_pool_used, alignment);

    if ((aligned_offset > ET_RESOURCE_WRAP_POOL_SIZE) ||
        (size > (ET_RESOURCE_WRAP_POOL_SIZE - aligned_offset)))
    {
        return ET_WRAP_STATUS_NO_RESOURCE;
    }

    /* Phase 3: Publish descriptor and high-water mark atomically at the first free slot. */
    for (slot = 0u; slot < ET_RESOURCE_WRAP_MAX_RESOURCES; ++slot)
    {
        if (resource_descriptors[slot].in_use == 0u)
        {
            resource_descriptors[slot].offset = aligned_offset;
            resource_descriptors[slot].size = size;
            resource_descriptors[slot].alignment = alignment;
            resource_descriptors[slot].generation = resource_generation;
            resource_descriptors[slot].in_use = 1u;
            resource_pool_used = aligned_offset + size;
            *handle = make_handle(resource_generation, slot);

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NO_RESOURCE;
}

/**
 * @brief Release the most recently allocated live Resource and invalidate stale handles.
 *
 * @param[in] handle Opaque Resource handle to destroy.
 *
 * @note The monotonic allocator supports LIFO destruction only: a Resource can be destroyed when its
 *       end equals the current high-water mark. Released bytes are zeroed and generation advances.
 *
 * @return ET_WRAP_STATUS_OK when the last allocation is released successfully.
 * @return ET_WRAP_STATUS_STATE_ERROR when handle is live but not the current last allocation.
 * @return Other stable Wrap errors when handle resolution fails.
 */
et_wrap_status_t et_resource_wrap_destroy(et_resource_handle_t handle)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    /* Phase 1: Resolve the opaque handle and enforce monotonic LIFO release ordering. */
    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((descriptor->offset + descriptor->size) != resource_pool_used)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Erase released bytes, rewind the high-water mark and clear the descriptor. */
    if (descriptor->size != 0u)
    {
        (void)memset(&resource_pool()[descriptor->offset], 0, descriptor->size);
    }

    resource_pool_used = descriptor->offset;
    (void)memset(descriptor, 0, sizeof(*descriptor));

    /* Phase 3: Advance generation so any handle issued before this release becomes stale. */
    ++resource_generation;

    if (resource_generation == 0u)
    {
        resource_generation = 1u;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Copy caller-owned bytes into one validated Resource subrange.
 *
 * @param[in] handle Opaque Resource handle identifying the destination buffer.
 * @param[in] offset Destination byte offset inside the Resource.
 * @param[in] data Source bytes to copy.
 * @param[in] size Number of bytes to copy.
 *
 * @note Zero-length writes allow data to be NULL. Nonzero writes occur only after generation and
 *       overflow-safe range validation; no Feature IP hardware is involved.
 *
 * @return ET_WRAP_STATUS_OK when the requested bytes are copied.
 * @return Stable validation/state errors when data, handle or range is invalid.
 */
et_wrap_status_t et_resource_wrap_write(et_resource_handle_t handle, uint32_t offset,
                                        const void *data, uint32_t size)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    if ((data == NULL) && (size != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_range(descriptor, offset, size);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (size != 0u)
    {
        (void)memcpy(&resource_pool()[descriptor->offset + offset], data, size);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Copy bytes from one validated Resource subrange into caller-owned storage.
 *
 * @param[in] handle Opaque Resource handle identifying the source buffer.
 * @param[in] offset Source byte offset inside the Resource.
 * @param[out] data Destination storage for copied bytes.
 * @param[in] size Number of bytes to copy.
 *
 * @note Zero-length reads allow data to be NULL. Nonzero reads occur only after generation and
 *       overflow-safe range validation; Resource contents are not modified.
 *
 * @return ET_WRAP_STATUS_OK when the requested bytes are copied.
 * @return Stable validation/state errors when data, handle or range is invalid.
 */
et_wrap_status_t et_resource_wrap_read(et_resource_handle_t handle, uint32_t offset, void *data,
                                       uint32_t size)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    if ((data == NULL) && (size != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_range(descriptor, offset, size);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (size != 0u)
    {
        (void)memcpy(data, &resource_pool()[descriptor->offset + offset], size);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Fill one validated Resource subrange with a repeated byte value.
 *
 * @param[in] handle Opaque Resource handle identifying the destination buffer.
 * @param[in] offset Destination byte offset inside the Resource.
 * @param[in] value Byte value written across the selected range.
 * @param[in] size Number of bytes to fill.
 *
 * @note The fill mutates only the static Resource arena after generation and range validation. It
 *       does not access Feature IP hardware.
 *
 * @return ET_WRAP_STATUS_OK when the range is filled, otherwise the stable handle/range error.
 */
et_wrap_status_t et_resource_wrap_fill(et_resource_handle_t handle, uint32_t offset, uint8_t value,
                                       uint32_t size)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_range(descriptor, offset, size);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (size != 0u)
    {
        (void)memset(&resource_pool()[descriptor->offset + offset], value, size);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one complete Resource handle into its static arena address and byte size.
 *
 * @param[in] handle Opaque Resource handle to resolve.
 * @param[out] address Base address of the live Resource.
 * @param[out] size Complete Resource size in bytes.
 *
 * @note The returned address aliases platform-owned static storage. Callers must not retain it after
 *       Resource reset/destruction invalidates the corresponding generation.
 *
 * @return ET_WRAP_STATUS_OK when handle resolves successfully, otherwise the stable validation error.
 */
et_wrap_status_t et_resource_wrap_resolve(et_resource_handle_t handle, void **address,
                                          uint32_t *size)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    if ((address == NULL) || (size == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *address = NULL;
    *size = 0u;
    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    *address = &resource_pool()[descriptor->offset];
    *size = descriptor->size;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one validated Resource subrange into its static arena address.
 *
 * @param[in] handle Opaque Resource handle to resolve.
 * @param[in] offset Byte offset inside the Resource.
 * @param[in] size Required contiguous range size in bytes.
 * @param[out] address Address of the validated subrange.
 *
 * @note The returned pointer aliases static Resource storage and is valid only while the handle
 *       generation remains live. No memory content is modified.
 *
 * @return ET_WRAP_STATUS_OK when the complete requested subrange is valid.
 * @return Stable validation/state errors when output, handle or range is invalid.
 */
et_wrap_status_t et_resource_wrap_resolve_range(et_resource_handle_t handle, uint32_t offset,
                                                uint32_t size, void **address)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    if (address == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *address = NULL;
    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_range(descriptor, offset, size);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    *address = &resource_pool()[descriptor->offset + offset];

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Verify that one absolute address range lies entirely inside a currently live Resource.
 *
 * @param[in] address Absolute start address to validate.
 * @param[in] size Nonzero range size in bytes.
 *
 * @note The scan trusts only currently in-use descriptors and uses subtraction after address ordering
 *       to avoid overflow. This is a Resource-safety query and does not read or modify pointed data.
 *
 * @return ET_WRAP_STATUS_OK when one live Resource contains the complete range.
 * @return ET_WRAP_STATUS_STATE_ERROR when Resource Wrap is not initialized.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when size/range is invalid or outside all live Resources.
 */
et_wrap_status_t et_resource_wrap_contains_range(uintptr_t address, uint32_t size)
{
    uintptr_t base;
    uintptr_t offset;
    uint16_t slot;

    if (resource_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (size == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (slot = 0u; slot < ET_RESOURCE_WRAP_MAX_RESOURCES; ++slot)
    {
        const et_resource_descriptor_t *descriptor = &resource_descriptors[slot];

        if (descriptor->in_use == 0u)
        {
            continue;
        }

        base = (uintptr_t)&resource_pool()[descriptor->offset];

        if (address < base)
        {
            continue;
        }

        offset = address - base;

        if ((offset <= descriptor->size) && (size <= (descriptor->size - (uint32_t)offset)))
        {
            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Return immutable size/alignment metadata for one live Resource handle.
 *
 * @param[in] handle Opaque Resource handle to inspect.
 * @param[out] info Resource size and alignment facts.
 *
 * @note Metadata is copied from the generation-validated descriptor only. Arena bytes and allocation
 *       state are not modified.
 *
 * @return ET_WRAP_STATUS_OK when live metadata is returned, otherwise the stable handle/output error.
 */
et_wrap_status_t et_resource_wrap_get_info(et_resource_handle_t handle,
                                           et_resource_wrap_info_t *info)
{
    et_resource_descriptor_t *descriptor;
    et_wrap_status_t status;

    if (info == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    info->size = 0u;
    info->alignment = 0u;
    status = find_descriptor(handle, &descriptor);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    info->size = descriptor->size;
    info->alignment = descriptor->alignment;

    return ET_WRAP_STATUS_OK;
}
