#ifndef ET_RESOURCE_WRAP_H
#define ET_RESOURCE_WRAP_H

/**
 * @file et_resource_wrap.h
 * @brief Allocation-free target buffer pool exposed through opaque handles.
 *
 * PC tests use resources for cross-command buffers. Handles never expose raw
 * target addresses on Wire; only trusted firmware layers may resolve them.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_wrap_status.h"

#define ET_RESOURCE_WRAP_API_VERSION 1u

#ifndef ET_RESOURCE_WRAP_POOL_SIZE
#define ET_RESOURCE_WRAP_POOL_SIZE 16384u
#endif

#ifndef ET_RESOURCE_WRAP_MAX_RESOURCES
#define ET_RESOURCE_WRAP_MAX_RESOURCES 16u
#endif

#ifndef ET_RESOURCE_WRAP_POOL_SECTION
#define ET_RESOURCE_WRAP_POOL_SECTION __attribute__((section("ET_RESOURCE_POOL")))
#endif

#define ET_RESOURCE_WRAP_MAX_ALIGNMENT 4u

/** Opaque generation-checked resource identity. Zero is always invalid. */
typedef uint32_t et_resource_handle_t;

#define ET_RESOURCE_HANDLE_INVALID ((et_resource_handle_t)0u)

typedef struct
{
    uint32_t size;      /**< Allocated bytes visible to the owner. */
    uint32_t alignment; /**< Guaranteed starting-address alignment. */
} et_resource_wrap_info_t;

/** Initialize the static pool and invalidate all prior handles. */
et_wrap_status_t et_resource_wrap_init(void);
/** Release every resource and invalidate all current handles. */
et_wrap_status_t et_resource_wrap_reset(void);
/** Allocate one zeroed, aligned range from the bounded pool. */
et_wrap_status_t et_resource_wrap_create(uint32_t size, uint32_t alignment,
                                         et_resource_handle_t *handle);
/** Release one live resource; stale or foreign handles are rejected. */
et_wrap_status_t et_resource_wrap_destroy(et_resource_handle_t handle);
/** Copy bytes into a validated handle-relative range. */
et_wrap_status_t et_resource_wrap_write(et_resource_handle_t handle, uint32_t offset,
                                        const void *data, uint32_t size);
/** Copy bytes from a validated handle-relative range. */
et_wrap_status_t et_resource_wrap_read(et_resource_handle_t handle, uint32_t offset, void *data,
                                       uint32_t size);
/** Fill a validated handle-relative range with one byte value. */
et_wrap_status_t et_resource_wrap_fill(et_resource_handle_t handle, uint32_t offset, uint8_t value,
                                       uint32_t size);
/** Resolve an entire live resource for trusted firmware consumers. */
et_wrap_status_t et_resource_wrap_resolve(et_resource_handle_t handle, void **address,
                                          uint32_t *size);
/** Resolve one validated subrange for trusted firmware consumers. */
et_wrap_status_t et_resource_wrap_resolve_range(et_resource_handle_t handle, uint32_t offset,
                                                uint32_t size, void **address);
/** Verify that a raw address range is fully contained in one live resource. */
et_wrap_status_t et_resource_wrap_contains_range(uintptr_t address, uint32_t size);
/** Return size and alignment facts for one live handle. */
et_wrap_status_t et_resource_wrap_get_info(et_resource_handle_t handle,
                                           et_resource_wrap_info_t *info);

#endif
