/**
 * @file et_aes_service.c
 * @brief Decode AES wire commands, execute AES Wrap and return facts.
 *
 * Resource handles are resolved only through Resource Wrap. The service does
 * not call another IP Service, wait for a wall-clock deadline, or emit a test
 * verdict. IRQ callbacks only capture bounded AES-local facts.
 */
#include "et_aes_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Verify that a reserved AES Wire region contains only zero bytes.
 *
 * @param[in] data Reserved bytes to validate.
 * @param[in] length Number of reserved bytes to inspect.
 *
 * @note Nonzero reserved bytes are rejected so older Firmware cannot silently accept a future
 *       protocol extension. This helper reads request memory only and has no hardware side effect.
 *
 * @return Nonzero when every reserved byte is zero, otherwise zero.
 */
static uint8_t bytes_are_zero(const uint8_t *data, uint16_t length)
{
    uint16_t index;

    for (index = 0u; index < length; ++index)
    {
        if (data[index] != 0u)
        {
            return 0u;
        }
    }

    return 1u;
}

/**
 * @brief Decode one unaligned little-endian 32-bit AES Wire field.
 *
 * @param[in] data Four bytes containing the encoded value.
 *
 * @note This helper reads caller-owned request memory only and does not access AES hardware.
 *
 * @return Decoded 32-bit value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Decode one unaligned little-endian 64-bit AES Wire field.
 *
 * @param[in] data Eight bytes containing the encoded value.
 *
 * @note The helper performs Wire decoding only; command-specific code assigns semantic meaning.
 *
 * @return Decoded 64-bit value.
 */
static uint64_t read_u64(const uint8_t *data)
{
    return (uint64_t)read_u32(data) | ((uint64_t)read_u32(&data[4]) << 32u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian AES Wire field.
 *
 * @param[out] data Four-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note This helper writes caller-owned response memory only and does not modify Service state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Encode one 64-bit value into an unaligned little-endian AES Wire field.
 *
 * @param[out] data Eight-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note Encoding is composed from two canonical 32-bit writes and has no hardware side effect.
 */
static void write_u64(uint8_t *data, uint64_t value)
{
    write_u32(data, (uint32_t)value);
    write_u32(&data[4], (uint32_t)(value >> 32u));
}

/**
 * @brief Normalize one AES Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status AES Wrap status returned by a chip-neutral operation.
 *
 * @note This helper performs status translation only and never exposes selected-chip Driver values.
 *
 * @return Stable ET status corresponding to the supplied Wrap status.
 */
static uint16_t status_from_wrap(et_wrap_status_t status)
{
    switch (status)
    {
        case ET_WRAP_STATUS_OK:
        {
            return ET_STATUS_OK;
        }

        case ET_WRAP_STATUS_INVALID_ARGUMENT:
        case ET_WRAP_STATUS_STATE_ERROR:
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_BUSY:
        case ET_WRAP_STATUS_TIMEOUT:
        case ET_WRAP_STATUS_NO_RESOURCE:
        {
            return ET_STATUS_BUSY;
        }

        default:
        {
            return ET_STATUS_INTERNAL_ERROR;
        }
    }
}

/**
 * @brief Report whether the AES Service currently owns an enabled module lifecycle state.
 *
 * @param[in] service AES Service instance whose lifecycle state is queried.
 *
 * @note This is a read-only Service-state query and does not inspect or change AES hardware.
 *
 * @return Nonzero when service exists and is enabled, otherwise zero.
 */
static uint8_t state_is_enabled(const et_aes_service_t *service)
{
    return (uint8_t)((service != NULL) && (service->enabled != 0u));
}

/**
 * @brief Report whether the AES Service is enabled and owns a validated active configuration.
 *
 * @param[in] service AES Service instance whose lifecycle state is queried.
 *
 * @note Data and IRQ-transfer commands use this read-only guard so they cannot run against an
 *       enabled-but-unconfigured AES instance.
 *
 * @return Nonzero when service is enabled and configured, otherwise zero.
 */
static uint8_t state_is_configured(const et_aes_service_t *service)
{
    return (uint8_t)(state_is_enabled(service) && (service->configured != 0u));
}

/**
 * @brief Decode the fixed CONFIGURE Wire body into a versioned chip-neutral AES Wrap configuration.
 *
 * @param[in] service AES Service instance that owns the request lifecycle.
 * @param[in] body Fixed CONFIGURE request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] config AES Wrap configuration populated from validated Wire fields.
 *
 * @note This function validates published enum and reserved-byte relationships only. It does not
 *       configure AES hardware; selected-chip capability validation remains in AES Wrap.
 *
 * @return Nonzero when the request is valid and decoded, otherwise zero.
 */
static uint8_t decode_config(et_aes_service_t *service, const uint8_t *body, uint16_t length,
                             et_aes_wrap_config_t *config)
{
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_AES_SERVICE_CONFIG_REQUEST_SIZE) ||
        (body[ET_AES_SERVICE_CONFIG_RESERVED_OFFSET] != 0u) ||
        (body[ET_AES_SERVICE_CONFIG_RESERVED_OFFSET + 1u] != 0u) ||
        (body[ET_AES_SERVICE_CONFIG_DIRECTION_OFFSET] > ET_AES_WRAP_DIRECTION_DECRYPT) ||
        (body[ET_AES_SERVICE_CONFIG_KEY_SIZE_OFFSET] > ET_AES_WRAP_KEY_256) ||
        (body[ET_AES_SERVICE_CONFIG_MODE_OFFSET] > ET_AES_WRAP_MODE_CTR) ||
        (body[ET_AES_SERVICE_CONFIG_PADDING_OFFSET] > ET_AES_WRAP_PADDING_PKCS7) ||
        (body[ET_AES_SERVICE_CONFIG_ENDIAN_OFFSET] > ET_AES_WRAP_ENDIAN_BIG) ||
        (body[ET_AES_SERVICE_CONFIG_DMA_MODE_OFFSET] > ET_AES_WRAP_DMA_REGISTER) ||
        ((body[ET_AES_SERVICE_CONFIG_MODE_OFFSET] == ET_AES_WRAP_MODE_CTR) &&
         (body[ET_AES_SERVICE_CONFIG_PADDING_OFFSET] != ET_AES_WRAP_PADDING_NONE)))
    {
        return 0u;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_AES_WRAP_API_VERSION;
    config->direction = body[ET_AES_SERVICE_CONFIG_DIRECTION_OFFSET];
    config->key_size = body[ET_AES_SERVICE_CONFIG_KEY_SIZE_OFFSET];
    config->mode = body[ET_AES_SERVICE_CONFIG_MODE_OFFSET];
    config->padding = body[ET_AES_SERVICE_CONFIG_PADDING_OFFSET];
    config->endian = body[ET_AES_SERVICE_CONFIG_ENDIAN_OFFSET];
    config->dma_transfer_mode = body[ET_AES_SERVICE_CONFIG_DMA_MODE_OFFSET];
    config->ctr_counter = read_u32(&body[ET_AES_SERVICE_CONFIG_COUNTER_OFFSET]);

    return 1u;
}

/**
 * @brief Decode one AES processing request that refers only to opaque Resource handles and offsets.
 *
 * @param[in] service AES Service instance providing the published process-length bound.
 * @param[in] body Fixed PROCESS, TIMED_PROCESS or IRQ_TRANSFER request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] source_handle Decoded source Resource handle.
 * @param[out] source_offset Decoded source byte offset.
 * @param[out] destination_handle Decoded destination Resource handle.
 * @param[out] destination_offset Decoded destination byte offset.
 * @param[out] logical_length Decoded logical plaintext or ciphertext byte count.
 *
 * @note Raw target pointers are never accepted on the Wire. Resource ownership and range resolution
 *       occur later through Resource Wrap after this structural validation succeeds.
 *
 * @return Nonzero when all request fields are structurally valid, otherwise zero.
 */
static uint8_t decode_resource_request(const et_aes_service_t *service, const uint8_t *body,
                                       uint16_t length, et_resource_handle_t *source_handle,
                                       uint32_t *source_offset,
                                       et_resource_handle_t *destination_handle,
                                       uint32_t *destination_offset, uint32_t *logical_length)
{
    if ((service == NULL) || (body == NULL) || (length != ET_AES_SERVICE_PROCESS_REQUEST_SIZE) ||
        (source_handle == NULL) || (source_offset == NULL) || (destination_handle == NULL) ||
        (destination_offset == NULL) || (logical_length == NULL))
    {
        return 0u;
    }

    *source_handle = (et_resource_handle_t)read_u32(&body[ET_AES_SERVICE_SOURCE_HANDLE_OFFSET]);
    *source_offset = read_u32(&body[ET_AES_SERVICE_SOURCE_OFFSET_OFFSET]);
    *destination_handle =
        (et_resource_handle_t)read_u32(&body[ET_AES_SERVICE_DESTINATION_HANDLE_OFFSET]);
    *destination_offset = read_u32(&body[ET_AES_SERVICE_DESTINATION_OFFSET_OFFSET]);
    *logical_length = read_u32(&body[ET_AES_SERVICE_LOGICAL_LENGTH_OFFSET]);

    if ((*source_handle == ET_RESOURCE_HANDLE_INVALID) ||
        (*destination_handle == ET_RESOURCE_HANDLE_INVALID) || (*logical_length == 0u) ||
        (*logical_length > service->capabilities.max_process_bytes))
    {
        return 0u;
    }

    return 1u;
}

/**
 * @brief Resolve AES source and destination Resources and derive the exact mode-specific output bound.
 *
 * @param[in] service AES Service instance providing runtime capability limits.
 * @param[in] config Active validated AES configuration.
 * @param[in] source_handle Opaque source Resource handle.
 * @param[in] source_offset Source byte offset within the Resource.
 * @param[in] destination_handle Opaque destination Resource handle.
 * @param[in] destination_offset Destination byte offset within the Resource.
 * @param[in] logical_length Logical input length requested by the PC.
 * @param[out] source Resolved source pointer owned by Resource Wrap.
 * @param[out] destination Resolved destination pointer owned by Resource Wrap.
 * @param[out] source_size Number of source bytes exposed to this transfer.
 * @param[out] destination_size Exact output capacity required by mode, direction and padding.
 *
 * @note ECB/CBC block and padding rules are proven before either opaque Resource range is resolved.
 *       This helper does not start AES hardware or extend any range beyond published capabilities.
 *
 * @return Nonzero when both ranges and the derived capacity are valid, otherwise zero.
 */
static uint8_t resolve_resources(const et_aes_service_t *service,
                                 const et_aes_wrap_config_t *config,
                                 et_resource_handle_t source_handle, uint32_t source_offset,
                                 et_resource_handle_t destination_handle,
                                 uint32_t destination_offset, uint32_t logical_length,
                                 uint8_t **source, uint8_t **destination, uint32_t *source_size,
                                 uint32_t *destination_size)
{
    void *source_ptr;
    void *destination_ptr;
    uint32_t required_output;

    /* Phase 1: Validate active AES semantics before deriving or resolving any Resource range. */
    if ((service == NULL) || (config == NULL) || (logical_length == 0u) ||
        (logical_length > service->capabilities.max_process_bytes) ||
        (config->mode > ET_AES_WRAP_MODE_CTR) ||
        (config->direction > ET_AES_WRAP_DIRECTION_DECRYPT) ||
        (config->padding > ET_AES_WRAP_PADDING_PKCS7))
    {
        return 0u;
    }

    /* The hardware consumes complete blocks for ECB/CBC and decrypt paths. */
    if ((config->mode != ET_AES_WRAP_MODE_CTR) &&
        (((config->padding == ET_AES_WRAP_PADDING_NONE) ||
          (config->direction == ET_AES_WRAP_DIRECTION_DECRYPT)) &&
         ((logical_length % ET_AES_WRAP_BLOCK_SIZE) != 0u)))
    {
        return 0u;
    }

    /* Phase 2: Derive the exact output capacity from mode, direction and padding semantics. */
    if (config->mode == ET_AES_WRAP_MODE_CTR)
    {
        required_output = logical_length;
    }
    else if (config->direction == ET_AES_WRAP_DIRECTION_DECRYPT)
    {
        required_output = logical_length;
    }
    else if (config->padding == ET_AES_WRAP_PADDING_PKCS7)
    {
        required_output = ((logical_length / ET_AES_WRAP_BLOCK_SIZE) + 1u) * ET_AES_WRAP_BLOCK_SIZE;
    }
    else
    {
        required_output =
            ((logical_length + (ET_AES_WRAP_BLOCK_SIZE - 1u)) / ET_AES_WRAP_BLOCK_SIZE) *
            ET_AES_WRAP_BLOCK_SIZE;
    }

    if (required_output > service->capabilities.max_process_output_bytes)
    {
        return 0u;
    }

    /* Phase 3: Resolve both opaque Resource ranges only after all size relationships are known. */
    if ((et_resource_wrap_resolve_range(source_handle, source_offset, logical_length,
                                        &source_ptr) != ET_WRAP_STATUS_OK) ||
        (et_resource_wrap_resolve_range(destination_handle, destination_offset, required_output,
                                        &destination_ptr) != ET_WRAP_STATUS_OK))
    {
        /* The first two resolves fully validate the opaque ranges. */
        return 0u;
    }

    *source = (uint8_t *)source_ptr;
    *destination = (uint8_t *)destination_ptr;
    *source_size = logical_length;
    *destination_size = required_output;

    return 1u;
}

/**
 * @brief Increment one ISR-visible AES evidence counter without allowing wraparound.
 *
 * @param[in,out] value Counter to increment when it is valid and below UINT32_MAX.
 *
 * @note Saturation preserves monotonic diagnostic evidence. Callers retain responsibility for the
 *       IRQ or critical-section context in which the volatile counter is updated.
 */
static void increment_saturating(volatile uint32_t *value)
{
    if ((value != NULL) && (*value != UINT32_MAX))
    {
        ++(*value);
    }
}

/**
 * @brief Move the active AES IRQ transfer into terminal fault state and latch the fault fact.
 *
 * @param[in,out] service AES Service instance that owns IRQ-transfer state.
 * @param[in] fault Normalized AES fault or maintenance bits to preserve for status reporting.
 *
 * @note This helper is bounded for IRQ callback use: it updates Service-local evidence only,
 *       saturates overflow evidence and never calls hardware or allocates memory.
 */
static void mark_irq_fault(et_aes_service_t *service, uint32_t fault)
{
    if (service == NULL)
    {
        return;
    }

    service->irq_fault_flags |= fault;
    service->irq_state = ET_AES_IRQ_TRANSFER_FAULT;
    increment_saturating(&service->overflow_count);
}

/**
 * @brief Reset all AES IRQ-transfer buffer ownership, counters and fault facts to one explicit state.
 *
 * @param[in,out] service AES Service instance whose transfer-local state is cleared.
 * @param[in] state Terminal or idle transfer state to publish after clearing ownership.
 *
 * @note Resource pointers are forgotten rather than freed because Resource Wrap owns their lifetime.
 *       IRQ route and source ownership are intentionally not changed by this helper.
 */
static void clear_irq_transfer_state(et_aes_service_t *service, uint8_t state)
{
    if (service == NULL)
    {
        return;
    }

    service->irq_source = NULL;
    service->irq_destination = NULL;
    service->irq_source_size = 0u;
    service->irq_destination_size = 0u;
    service->irq_logical_length = 0u;
    service->irq_expected_bytes = 0u;
    service->irq_input_offset = 0u;
    service->irq_output_offset = 0u;
    service->irq_produced_bytes = 0u;
    service->irq_fault_flags = 0u;
    service->irq_block_count = 0u;
    service->irq_state = state;
}

/**
 * @brief Encode one 16-bit value into an unaligned little-endian AES Wire field.
 *
 * @param[out] data Two-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note This helper writes caller-owned response memory only and has no hardware side effect.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Feed at most one AES input block for a managed DATA_IN_REQ interrupt event.
 *
 * @param[in,out] service Active AES IRQ-transfer session owning the source Resource range.
 *
 * @note This function executes in IRQ context. It copies at most one bounded block, zero-fills the
 *       final partial block and performs one non-blocking AES Wrap write; invalid ownership or a
 *       failed write moves the transfer to terminal fault state.
 */
static void aes_irq_feed_input(et_aes_service_t *service)
{
    uint8_t block[ET_AES_WRAP_BLOCK_SIZE];
    uint32_t copy_bytes;

    if ((service->irq_source == NULL) || (service->irq_input_offset >= service->irq_logical_length))
    {
        mark_irq_fault(service, ET_AES_WRAP_IRQ_DATA_IN_REQ);

        return;
    }

    (void)memset(block, 0, sizeof(block));
    copy_bytes = service->irq_logical_length - service->irq_input_offset;

    if (copy_bytes > ET_AES_WRAP_BLOCK_SIZE)
    {
        copy_bytes = ET_AES_WRAP_BLOCK_SIZE;
    }

    (void)memcpy(block, &service->irq_source[service->irq_input_offset], copy_bytes);

    if (et_aes_wrap_block_write(service->aes_id, block) != ET_WRAP_STATUS_OK)
    {
        mark_irq_fault(service, ET_AES_WRAP_IRQ_DATA_IN_REQ);

        return;
    }

    service->irq_input_offset += copy_bytes;
}

/**
 * @brief Drain at most one AES output block for a managed DATA_OUT_REQ interrupt event.
 *
 * @param[in,out] service Active AES IRQ-transfer session owning the destination Resource range.
 *
 * @note This function executes in IRQ context. It performs one non-blocking Wrap read, copies only
 *       bytes inside the prevalidated destination bound and updates produced-byte evidence.
 */
static void aes_irq_drain_output(et_aes_service_t *service)
{
    uint8_t block[ET_AES_WRAP_BLOCK_SIZE];
    uint32_t copy_bytes;

    if ((service->irq_destination == NULL) ||
        (service->irq_output_offset > service->irq_destination_size) ||
        (service->irq_expected_bytes > service->irq_destination_size))
    {
        mark_irq_fault(service, ET_AES_WRAP_IRQ_DATA_OUT_REQ);

        return;
    }

    if (et_aes_wrap_block_read(service->aes_id, block) != ET_WRAP_STATUS_OK)
    {
        mark_irq_fault(service, ET_AES_WRAP_IRQ_DATA_OUT_REQ);

        return;
    }

    copy_bytes = ET_AES_WRAP_BLOCK_SIZE;

    if (service->irq_output_offset >= service->irq_expected_bytes)
    {
        copy_bytes = 0u;
    }
    else if ((service->irq_expected_bytes - service->irq_output_offset) < copy_bytes)
    {
        copy_bytes = service->irq_expected_bytes - service->irq_output_offset;
    }

    if (copy_bytes != 0u)
    {
        (void)memcpy(&service->irq_destination[service->irq_output_offset], block, copy_bytes);
    }

    service->irq_output_offset += copy_bytes;
    service->irq_produced_bytes += copy_bytes;
    increment_saturating(&service->irq_block_count);
}

/**
 * @brief Complete a managed AES IRQ transfer only when published input and output byte counts agree.
 *
 * @param[in,out] service Active AES IRQ-transfer session to validate and close.
 *
 * @note A COMPLETE interrupt is evidence, not proof of a correct transfer length. Any byte-count
 *       mismatch is converted into ET_AES_WRAP_FAULT_LENGTH rather than false completion.
 */
static void aes_irq_complete_transfer(et_aes_service_t *service)
{
    if ((service->irq_input_offset != service->irq_logical_length) ||
        (service->irq_produced_bytes != service->irq_expected_bytes))
    {
        mark_irq_fault(service, ET_AES_WRAP_FAULT_LENGTH);

        return;
    }

    service->irq_state = ET_AES_IRQ_TRANSFER_COMPLETE;
}

/**
 * @brief Capture one AES IRQ snapshot and service at most one input and one output block.
 *
 * @param[in,out] context AES Service instance registered as the IRQ callback context.
 * @param[in] irq_line Physical IRQ line reported by IRQ Manager.
 * @param[in] route_events Normalized events associated with this managed route.
 *
 * @note This callback executes in interrupt context and remains bounded: one snapshot, at most one
 *       block per direction and one clear or mask maintenance sequence. It never allocates, advances
 *       a PC Case or decides PASS/FAIL.
 */
static void aes_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_aes_service_t *service = (et_aes_service_t *)context;
    et_aes_wrap_irq_snapshot_t snapshot;
    uint32_t owned;

    (void)irq_line;
    (void)route_events;

    /* Phase 1: Reject stale callback entry and snapshot normalized AES IRQ facts. */
    if ((service == NULL) || (service->irq_bound == 0u))
    {
        return;
    }

    if (et_aes_wrap_irq_snapshot_get(service->aes_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        if (service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE)
        {
            mark_irq_fault(service, ET_AES_WRAP_FAULT_MAINTENANCE);
        }
        else
        {
            increment_saturating(&service->overflow_count);
        }

        return;
    }

    /* Phase 2: Publish bounded event evidence before servicing owned transfer requests. */
    owned = snapshot.status & service->enabled_events & route_events;
    service->latched_events |= owned;
    increment_saturating(&service->event_count);

    if ((snapshot.status & ~service->enabled_events) != 0u)
    {
        increment_saturating(&service->unexpected_count);
    }

    /* Phase 3: Service at most one owned input, output or completion action for this snapshot. */
    if (owned != 0u)
    {
        if ((service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE) &&
            ((owned & ET_AES_SERVICE_IRQ_TRANSFER_FAULT_EVENTS) != 0u))
        {
            mark_irq_fault(service, owned & ET_AES_SERVICE_IRQ_TRANSFER_FAULT_EVENTS);
        }

        if ((service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE) &&
            ((owned & ET_AES_WRAP_IRQ_DATA_IN_REQ) != 0u))
        {
            aes_irq_feed_input(service);
        }

        if ((service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE) &&
            ((owned & ET_AES_WRAP_IRQ_DATA_OUT_REQ) != 0u))
        {
            aes_irq_drain_output(service);
        }

        if ((service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE) &&
            ((owned & ET_AES_WRAP_IRQ_COMPLETE) != 0u))
        {
            aes_irq_complete_transfer(service);
        }

        /* Phase 4: Acknowledge observed sources, then suppress level requests without ownership. */
        if (et_aes_wrap_irq_clear(service->aes_id, owned) != ET_WRAP_STATUS_OK)
        {
            mark_irq_fault(service, ET_AES_WRAP_FAULT_MAINTENANCE);
        }

        /*
         * DATA_IN_REQ and DATA_OUT_REQ are level requests. Outside an active
         * transfer they have no buffer owner, so keep them masked after the
         * first observation to prevent an interrupt-only command from
         * starving the protocol loop. IRQ_TRANSFER_START releases them after
         * publishing the complete transfer context.
         */
        if ((service->irq_state != ET_AES_IRQ_TRANSFER_ACTIVE) &&
            ((owned & ET_AES_SERVICE_IRQ_REQUEST_EVENTS) != 0u) &&
            (et_aes_wrap_irq_mask(service->aes_id, owned & ET_AES_SERVICE_IRQ_REQUEST_EVENTS) !=
             ET_WRAP_STATUS_OK))
        {
            increment_saturating(&service->overflow_count);
        }
    }
}

/**
 * @brief Bind the selected AES board IRQ route through the common IRQ Manager exactly once.
 *
 * @param[in,out] service AES Service instance that will own callback and route state.
 *
 * @note Route facts come from AES Wrap and Chip Config; this helper does not enable AES interrupt
 *       sources. The local irq_bound flag is published only after IRQ Manager confirms the binding.
 *
 * @return 0 when an existing or new binding is valid, otherwise -1.
 */
static int aes_irq_bind(et_aes_service_t *service)
{
    if (service->irq_bound != 0u)
    {
        return 0;
    }

    if ((et_aes_wrap_get_irq_route(service->aes_id, &service->irq_route) != ET_WRAP_STATUS_OK) ||
        (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                             aes_irq_callback, service) != 0))
    {
        return -1;
    }

    service->irq_bound = 1u;

    return 0;
}

/**
 * @brief Release the AES IRQ Manager binding while preserving retryable ownership on failure.
 *
 * @param[in,out] service AES Service instance that owns the callback binding.
 *
 * @note Callers are responsible for source-disable ordering. irq_bound is cleared only after IRQ
 *       Manager confirms unbind, so a failed release cannot masquerade as completed cleanup.
 *
 * @return 0 when no binding exists or release succeeds, otherwise -1.
 */
static int aes_irq_unbind(et_aes_service_t *service)
{
    if ((service == NULL) || (service->irq_bound == 0u))
    {
        return 0;
    }

    if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line, aes_irq_callback,
                              service) != 0)
    {
        return -1;
    }

    service->irq_bound = 0u;

    return 0;
}

/**
 * @brief Finalize one AES disable session after the module-disable hardware write has occurred.
 *
 * @param[in,out] service AES Service instance whose IRQ and lifecycle ownership is being closed.
 *
 * @note If INCOMPLETE_DISABLE is owned, a bounded settle loop keeps the route alive long enough to
 *       latch it. Sources are then disabled, the route is released and only successful cleanup clears
 *       enabled, configured and transfer-local state.
 *
 * @return ET_STATUS_OK when the complete session is closed, otherwise ET_STATUS_INTERNAL_ERROR.
 */
static uint16_t finalize_disable_session(et_aes_service_t *service)
{
    uint32_t settle_budget = ET_AES_SERVICE_DISABLE_IRQ_SETTLE_BUDGET;

    /* Phase 1: Keep a bounded callback window for INCOMPLETE_DISABLE evidence. */
    if ((service->enabled_events & ET_AES_WRAP_IRQ_INCOMPLETE_DISABLE) != 0u)
    {
        while ((settle_budget != 0u) &&
               ((service->latched_events & ET_AES_WRAP_IRQ_INCOMPLETE_DISABLE) == 0u))
        {
            --settle_budget;
        }
    }

    /* Phase 2: Disable every owned source and release the common IRQ route. */
    if ((service->enabled_events != 0u) &&
        (et_aes_wrap_irq_disable(service->aes_id, service->enabled_events) != ET_WRAP_STATUS_OK))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->enabled_events = 0u;
    service->masked_events = 0u;

    if (aes_irq_unbind(service) != 0)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 3: Publish the closed lifecycle only after IRQ cleanup succeeds. */
    service->enabled = 0u;
    service->configured = 0u;
    clear_irq_transfer_state(service, ET_AES_IRQ_TRANSFER_IDLE);

    return ET_STATUS_OK;
}

/**
 * @brief Apply one AES IRQ enable, disable, mask, unmask, force or clear command under Service ownership.
 *
 * @param[in,out] service Enabled AES Service instance owning IRQ route and source state.
 * @param[in] command_id Stable AES IRQ-control command identifier.
 * @param[in] request_body Four-byte normalized event-mask body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note Source ownership is published before hardware enable so the first interrupt cannot race the
 *       callback. Level DATA_IN/OUT requests remain masked outside an active transfer; clear updates
 *       latched Service evidence inside IRQ Manager critical protection.
 *
 * @return Stable ET status for request validation, ownership maintenance or AES Wrap execution.
 */
static uint16_t handle_irq_control(et_aes_service_t *service, uint16_t command_id,
                                   const uint8_t *request_body, uint16_t request_length)
{
    uint32_t events;

    /* Phase 1: Validate lifecycle and the normalized nonempty IRQ event mask. */
    if ((state_is_enabled(service) == 0u) || (request_length != ET_AES_SERVICE_U32_BODY_SIZE) ||
        (request_body == NULL) || (read_u32(request_body) == 0u) ||
        ((read_u32(request_body) & ~ET_AES_WRAP_IRQ_ALL) != 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Apply exactly one ownership or mask operation with callback-safe ordering. */
    events = read_u32(request_body);

    if (command_id == ET_AES_COMMAND_IRQ_ENABLE)
    {
        uint32_t previous_enabled_events;
        uint32_t request_events = events & ET_AES_SERVICE_IRQ_REQUEST_EVENTS;
        et_wrap_status_t irq_status;

        if (aes_irq_bind(service) != 0)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        /* Keep immediately asserted request sources masked until a transfer owns buffers. */
        if ((service->irq_state != ET_AES_IRQ_TRANSFER_ACTIVE) && (request_events != 0u) &&
            (et_aes_wrap_irq_mask(service->aes_id, request_events) != ET_WRAP_STATUS_OK))
        {
            if (service->enabled_events == 0u)
            {
                (void)aes_irq_unbind(service);
            }

            return ET_STATUS_INTERNAL_ERROR;
        }

        /* Publish ownership before enabling hardware so the first edge cannot race the ISR. */
        previous_enabled_events = service->enabled_events;
        service->enabled_events |= events;
        irq_status = et_aes_wrap_irq_enable(service->aes_id, events);

        if (irq_status != ET_WRAP_STATUS_OK)
        {
            service->enabled_events = previous_enabled_events;

            if (previous_enabled_events == 0u)
            {
                (void)aes_irq_unbind(service);
            }
        }

        return status_from_wrap(irq_status);
    }

    if (command_id == ET_AES_COMMAND_IRQ_DISABLE)
    {
        et_wrap_status_t irq_status = et_aes_wrap_irq_disable(service->aes_id, events);

        if (irq_status == ET_WRAP_STATUS_OK)
        {
            service->enabled_events &= ~events;

            if (service->enabled_events == 0u)
            {
                (void)aes_irq_unbind(service);
            }
        }

        return status_from_wrap(irq_status);
    }

    if (command_id == ET_AES_COMMAND_IRQ_MASK)
    {
        service->masked_events |= events;

        return status_from_wrap(et_aes_wrap_irq_mask(service->aes_id, events));
    }

    if (command_id == ET_AES_COMMAND_IRQ_UNMASK)
    {
        uint32_t immediate_events = events;

        service->masked_events &= ~events;

        if (service->irq_state != ET_AES_IRQ_TRANSFER_ACTIVE)
        {
            immediate_events &= ~ET_AES_SERVICE_IRQ_REQUEST_EVENTS;
        }

        if (immediate_events == 0u)
        {
            return ET_STATUS_OK;
        }

        return status_from_wrap(et_aes_wrap_irq_unmask(service->aes_id, immediate_events));
    }

    if (command_id == ET_AES_COMMAND_IRQ_FORCE)
    {
        return status_from_wrap(et_aes_wrap_irq_force(service->aes_id, events));
    }

    if (command_id == ET_AES_COMMAND_IRQ_CLEAR)
    {
        uint32_t irq_key;
        et_wrap_status_t irq_status = et_aes_wrap_irq_clear(service->aes_id, events);

        if (irq_status == ET_WRAP_STATUS_OK)
        {
            irq_key = et_irq_manager_enter_critical();
            service->latched_events &= ~events;
            et_irq_manager_exit_critical(irq_key);
        }

        return status_from_wrap(irq_status);
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Validate Resources, publish complete buffer ownership and arm one interrupt-driven AES transfer.
 *
 * @param[in,out] service Configured AES Service instance with an active managed IRQ binding.
 * @param[in] request_body Resource-handle transfer request body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note Request sources are disabled while stale status is cleared and new pointers and bounds are
 *       published. Only after ownership is complete are data length and configuration programmed and
 *       the required request and completion sources re-enabled.
 *
 * @return ET_STATUS_OK when the transfer is armed, ET_STATUS_INVALID_PARAM for an invalid session or
 *         range, otherwise ET_STATUS_INTERNAL_ERROR for hardware or IRQ-maintenance failure.
 */
static uint16_t handle_irq_transfer_start(et_aes_service_t *service, const uint8_t *request_body,
                                          uint16_t request_length)
{
    et_resource_handle_t source_handle;
    et_resource_handle_t destination_handle;
    uint8_t *source;
    uint8_t *destination;
    uint32_t source_offset;
    uint32_t destination_offset;
    uint32_t logical_length;
    uint32_t source_size;
    uint32_t destination_size;

    /* Phase 1: Validate configured lifecycle, managed IRQ ownership and both Resource ranges. */
    if ((state_is_configured(service) == 0u) ||
        (service->irq_state == ET_AES_IRQ_TRANSFER_ACTIVE) || (service->irq_bound == 0u) ||
        ((service->enabled_events & ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED) !=
         ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED) ||
        ((service->masked_events & ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED) != 0u) ||
        (decode_resource_request(service, request_body, request_length, &source_handle,
                                 &source_offset, &destination_handle, &destination_offset,
                                 &logical_length) == 0u) ||
        (resolve_resources(service, &service->config, source_handle, source_offset,
                           destination_handle, destination_offset, logical_length, &source,
                           &destination, &source_size, &destination_size) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Quiesce request IRQ delivery and clear stale request or completion observations. */
    if (et_aes_wrap_irq_disable(service->aes_id, ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED) !=
        ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    if (et_aes_wrap_clear_status(service->aes_id,
                                 ET_AES_WRAP_STATUS_FINISH | ET_AES_WRAP_STATUS_DATA_OUT_REQ) !=
        ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    if (et_aes_wrap_irq_clear(service->aes_id, ET_AES_WRAP_IRQ_DATA_OUT_REQ |
                                                   ET_AES_WRAP_IRQ_COMPLETE) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 3: Reset stale facts and publish every pointer and bound before hardware can interrupt. */
    clear_irq_transfer_state(service, ET_AES_IRQ_TRANSFER_ACTIVE);
    service->irq_source = source;
    service->irq_destination = destination;
    service->irq_source_size = source_size;
    service->irq_destination_size = destination_size;
    service->irq_logical_length = logical_length;
    service->irq_expected_bytes = destination_size;
    increment_saturating(&service->generation);

    /* Phase 4: Program data length and configuration only after ISR buffer ownership is complete. */
    if ((et_aes_wrap_set_data_length(service->aes_id, logical_length) != ET_WRAP_STATUS_OK) ||
        (et_aes_wrap_configure(service->aes_id, &service->config) != ET_WRAP_STATUS_OK))
    {
        mark_irq_fault(service, ET_AES_WRAP_FAULT_MAINTENANCE);

        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 5: Re-enable required sources and unmask request events to arm the transfer. */
    if (et_aes_wrap_irq_enable(service->aes_id, ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED) !=
        ET_WRAP_STATUS_OK)
    {
        mark_irq_fault(service, ET_AES_WRAP_FAULT_MAINTENANCE);

        return ET_STATUS_INTERNAL_ERROR;
    }

    if (et_aes_wrap_irq_unmask(service->aes_id, ET_AES_SERVICE_IRQ_REQUEST_EVENTS) !=
        ET_WRAP_STATUS_OK)
    {
        mark_irq_fault(service, ET_AES_WRAP_FAULT_MAINTENANCE);

        return ET_STATUS_INTERNAL_ERROR;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Encode the immutable runtime AES capability contract for one logical instance.
 *
 * @param[in] service AES Service instance providing the stable logical AES identifier.
 * @param[in] request_length Request-body length, which must be zero.
 * @param[out] response_body Caller-owned capability response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of capability response bytes produced.
 *
 * @note Capability facts are obtained from AES Wrap and Chip Config and encoded into the stable Wire
 *       schema. The function does not enable or configure AES hardware.
 *
 * @return ET_STATUS_OK on success, ET_STATUS_INVALID_PARAM for shape or capacity errors, or
 *         ET_STATUS_NOT_SUPPORTED when the logical AES instance has no capability mapping.
 */
static uint16_t handle_capabilities_get(et_aes_service_t *service, uint16_t request_length,
                                        uint8_t *response_body, uint16_t response_capacity,
                                        uint16_t *response_length)
{
    et_aes_wrap_capabilities_t capabilities;

    if ((request_length != 0u) || (response_capacity < ET_AES_SERVICE_CAPABILITIES_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    if (et_aes_wrap_get_capabilities(service->aes_id, &capabilities) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_NOT_SUPPORTED;
    }

    write_u16(&response_body[ET_AES_SERVICE_CAP_API_VERSION_OFFSET], capabilities.api_version);
    write_u16(&response_body[ET_AES_SERVICE_CAP_STRUCT_SIZE_OFFSET],
              ET_AES_SERVICE_CAPABILITIES_SIZE);
    write_u32(&response_body[ET_AES_SERVICE_CAP_FEATURE_FLAGS_OFFSET], capabilities.feature_flags);
    write_u32(&response_body[ET_AES_SERVICE_CAP_BLOCK_SIZE_OFFSET], capabilities.block_size_bytes);
    write_u32(&response_body[ET_AES_SERVICE_CAP_LENGTH_BITS_OFFSET],
              capabilities.hardware_data_length_bits);
    write_u32(&response_body[ET_AES_SERVICE_CAP_MAX_PROCESS_OFFSET],
              capabilities.max_process_bytes);
    write_u32(&response_body[ET_AES_SERVICE_CAP_MAX_OUTPUT_OFFSET],
              capabilities.max_process_output_bytes);
    response_body[ET_AES_SERVICE_CAP_KEY_MASK_OFFSET] = capabilities.key_size_mask;
    response_body[ET_AES_SERVICE_CAP_MODE_MASK_OFFSET] = capabilities.mode_mask;
    response_body[ET_AES_SERVICE_CAP_PADDING_MASK_OFFSET] = capabilities.padding_mask;
    response_body[ET_AES_SERVICE_CAP_ENDIAN_MASK_OFFSET] = capabilities.endian_mask;
    response_body[ET_AES_SERVICE_CAP_DMA_MASK_OFFSET] = capabilities.dma_mode_mask;
    response_body[ET_AES_SERVICE_CAP_IRQ_MASK_OFFSET] = capabilities.irq_event_mask;
    response_body[ET_AES_SERVICE_CAP_IRQ_TRANSFER_OFFSET] = capabilities.irq_transfer_supported;
    response_body[ET_AES_SERVICE_CAP_TIMED_OFFSET] = capabilities.timed_process_supported;
    *response_length = ET_AES_SERVICE_CAPABILITIES_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Validate one canonical AES key body and program it through AES Wrap.
 *
 * @param[in] service Configured AES Service instance whose active key size must match the request.
 * @param[in] request_body Fixed key-size, reserved and key-material request body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note A 128-bit key requires the unused tail of the fixed 256-bit Wire body to remain zero. Key
 *       material is forwarded only after lifecycle and shape validation; the Service retains no copy.
 *
 * @return Stable ET status for request validation or AES Wrap key programming.
 */
static uint16_t handle_key_set(et_aes_service_t *service, const uint8_t *request_body,
                               uint16_t request_length)
{
    uint8_t key_tail_nonzero = 0u;
    uint8_t key_index;

    /* Phase 1: Validate configured lifecycle, fixed key envelope and active key-size agreement. */
    if ((state_is_configured(service) == 0u) ||
        (request_length != ET_AES_SERVICE_KEY_REQUEST_SIZE) ||
        (request_body[ET_AES_SERVICE_KEY_SIZE_OFFSET] > ET_AES_WRAP_KEY_256) ||
        (bytes_are_zero(&request_body[ET_AES_SERVICE_KEY_RESERVED_OFFSET],
                        ET_AES_SERVICE_KEY_RESERVED_SIZE) == 0u) ||
        (request_body[ET_AES_SERVICE_KEY_SIZE_OFFSET] != service->config.key_size))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Enforce a zero unused tail for the fixed-width 128-bit key encoding. */
    if (request_body[ET_AES_SERVICE_KEY_SIZE_OFFSET] == ET_AES_WRAP_KEY_128)
    {
        for (key_index = 0u; key_index < ET_AES_SERVICE_KEY_128_TAIL_SIZE; ++key_index)
        {
            if (request_body[ET_AES_SERVICE_KEY_128_TAIL_OFFSET + key_index] != 0u)
            {
                key_tail_nonzero = 1u;
            }
        }

        if (key_tail_nonzero != 0u)
        {
            return ET_STATUS_INVALID_PARAM;
        }
    }

    /* Phase 3: Program key material only after every Wire invariant has been proven. */
    return status_from_wrap(et_aes_wrap_set_key(service->aes_id,
                                                &request_body[ET_AES_SERVICE_KEY_MATERIAL_OFFSET],
                                                request_body[ET_AES_SERVICE_KEY_SIZE_OFFSET]));
}

/**
 * @brief Resolve Resources, execute one bounded synchronous AES transfer and encode observed status.
 *
 * @param[in] service Configured AES Service instance.
 * @param[in] request_body Resource-handle PROCESS request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned PROCESS response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of PROCESS response bytes produced.
 *
 * @note Resource Wrap resolves all memory ownership before AES Wrap is called. Firmware reports
 *       produced bytes and final hardware status facts only; expected-data comparison remains PC-side.
 *
 * @return Stable ET status for validation or synchronous AES execution.
 */
static uint16_t handle_process(et_aes_service_t *service, const uint8_t *request_body,
                               uint16_t request_length, uint8_t *response_body,
                               uint16_t response_capacity, uint16_t *response_length)
{
    et_aes_wrap_status_snapshot_t status;
    et_resource_handle_t source_handle;
    et_resource_handle_t destination_handle;
    uint8_t *source;
    uint8_t *destination;
    uint32_t source_offset;
    uint32_t destination_offset;
    uint32_t logical_length;
    uint32_t source_size;
    uint32_t destination_size;
    uint32_t produced;

    /* Phase 1: Validate lifecycle and resolve both opaque Resource ranges before execution. */
    if ((state_is_configured(service) == 0u) ||
        (decode_resource_request(service, request_body, request_length, &source_handle,
                                 &source_offset, &destination_handle, &destination_offset,
                                 &logical_length) == 0u) ||
        (resolve_resources(service, &service->config, source_handle, source_offset,
                           destination_handle, destination_offset, logical_length, &source,
                           &destination, &source_size, &destination_size) == 0u) ||
        (response_capacity < ET_AES_SERVICE_PROCESS_RESPONSE_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute one bounded synchronous AES Wrap transfer. */
    if (et_aes_wrap_process(service->aes_id, source, destination, logical_length, destination_size,
                            &produced) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 3: Snapshot final hardware facts and encode them without deriving a verdict. */
    if (et_aes_wrap_get_status(service->aes_id, &status) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u32(response_body, produced);
    response_body[ET_AES_SERVICE_PROCESS_BUSY_OFFSET] = status.busy;
    response_body[ET_AES_SERVICE_PROCESS_DATA_IN_OFFSET] = status.data_in_request;
    response_body[ET_AES_SERVICE_PROCESS_DATA_OUT_OFFSET] = status.data_out_request;
    response_body[ET_AES_SERVICE_PROCESS_FINISH_OFFSET] = status.finish;
    write_u32(&response_body[ET_AES_SERVICE_PROCESS_RESERVED_OFFSET], 0u);
    *response_length = ET_AES_SERVICE_PROCESS_RESPONSE_SIZE;
    (void)source_size;

    return ET_STATUS_OK;
}

/**
 * @brief Execute one bounded timed AES transfer and encode cycle, byte-count and final-status facts.
 *
 * @param[in] service Configured AES Service instance.
 * @param[in] request_body Resource-handle TIMED_PROCESS request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned timed-result response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of timed-result response bytes produced.
 *
 * @note Timing is measured by AES Wrap around the selected hardware transfer. The Service returns raw
 *       cycle, byte and status observations and does not compare them with a performance threshold.
 *
 * @return Stable ET status for validation, timed Wrap execution or final status observation.
 */
static uint16_t handle_timed_process(et_aes_service_t *service, const uint8_t *request_body,
                                     uint16_t request_length, uint8_t *response_body,
                                     uint16_t response_capacity, uint16_t *response_length)
{
    et_aes_wrap_status_snapshot_t status;
    et_resource_handle_t source_handle;
    et_resource_handle_t destination_handle;
    et_wrap_status_t timed_status;
    uint8_t *source;
    uint8_t *destination;
    uint32_t source_offset;
    uint32_t destination_offset;
    uint32_t logical_length;
    uint32_t source_size;
    uint32_t destination_size;
    uint32_t produced;
    uint32_t cycles = 0u;

    /* Phase 1: Validate the timed lifecycle and resolve both Resource ranges before measurement. */
    if ((state_is_configured(service) == 0u) ||
        (decode_resource_request(service, request_body, request_length, &source_handle,
                                 &source_offset, &destination_handle, &destination_offset,
                                 &logical_length) == 0u) ||
        (resolve_resources(service, &service->config, source_handle, source_offset,
                           destination_handle, destination_offset, logical_length, &source,
                           &destination, &source_size, &destination_size) == 0u) ||
        (response_capacity < ET_AES_SERVICE_TIMED_RESPONSE_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute the timed transfer entirely inside AES Wrap measurement boundaries. */
    timed_status = et_aes_wrap_process_timed(service->aes_id, source, destination, logical_length,
                                             destination_size, &produced, &cycles);

    if (timed_status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(timed_status);
    }

    /* Phase 3: Snapshot final AES hardware facts and encode timing observations without a verdict. */
    if (et_aes_wrap_get_status(service->aes_id, &status) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u32(&response_body[ET_AES_SERVICE_TIMED_CYCLES_OFFSET], cycles);
    write_u32(&response_body[ET_AES_SERVICE_TIMED_PRODUCED_OFFSET], produced);
    write_u32(&response_body[ET_AES_SERVICE_TIMED_MEASURED_OFFSET], logical_length);
    write_u32(&response_body[ET_AES_SERVICE_TIMED_STATUS_OFFSET],
              ((status.busy != 0u) ? ET_AES_SERVICE_TIMED_STATUS_BUSY : 0u) |
                  ((status.data_in_request != 0u) ? ET_AES_SERVICE_TIMED_STATUS_DATA_IN : 0u) |
                  ((status.data_out_request != 0u) ? ET_AES_SERVICE_TIMED_STATUS_DATA_OUT : 0u) |
                  ((status.finish != 0u) ? ET_AES_SERVICE_TIMED_STATUS_FINISH : 0u));
    *response_length = ET_AES_SERVICE_TIMED_RESPONSE_SIZE;
    (void)source_size;

    return ET_STATUS_OK;
}

/**
 * @brief Dispatch AES capability, lifecycle and persistent configuration commands.
 *
 * @param[in,out] service AES Service instance whose lifecycle or configuration state may change.
 * @param[in] command_id Stable AES command identifier.
 * @param[in] request_body Command-specific request body, or NULL for zero-length commands.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Service-local enabled and configured state is changed only after the corresponding Wrap action
 *       succeeds. DISABLE keeps the route alive through the hardware disable write so an owned
 *       INCOMPLETE_DISABLE event can still be captured before cleanup.
 *
 * @return Stable ET status for the selected lifecycle or configuration command, or INVALID_COMMAND
 *         when the command belongs to another AES command category.
 */
static uint16_t handle_lifecycle_commands(et_aes_service_t *service, uint16_t command_id,
                                          const uint8_t *request_body, uint16_t request_length,
                                          uint8_t *response_body, uint16_t response_capacity,
                                          uint16_t *response_length)
{
    et_aes_wrap_config_t config;
    uint64_t data_length;

    /* Step 1: Route capability and module lifecycle transitions with commit-after-Wrap semantics. */
    switch (command_id)
    {
        case ET_AES_COMMAND_CAPABILITIES_GET:
        {
            return handle_capabilities_get(service, request_length, response_body,
                                           response_capacity, response_length);
        }

        case ET_AES_COMMAND_ENABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (et_aes_wrap_enable(service->aes_id) != ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            service->enabled = 1u;
            service->configured = 0u;
            clear_irq_transfer_state(service, ET_AES_IRQ_TRANSFER_IDLE);

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_DISABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            (void)et_aes_wrap_dma_request_set(service->aes_id, 0u);

            /*
         * Keep the IRQ route alive through the hardware disable write so an
         * INCOMPLETE_DISABLE event can be captured before sources are removed.
         */
            if (et_aes_wrap_disable(service->aes_id) != ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            return finalize_disable_session(service);
        }

        case ET_AES_COMMAND_CONFIGURE:
        {
            if ((state_is_enabled(service) == 0u) ||
                (decode_config(service, request_body, request_length, &config) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (et_aes_wrap_configure(service->aes_id, &config) != ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            service->configured = 1u;
            service->config = config;

            return ET_STATUS_OK;
        }

        /* Step 2: Route persistent key, IV and data-length configuration or readback commands. */
        case ET_AES_COMMAND_KEY_SET:
        {
            return handle_key_set(service, request_body, request_length);
        }

        case ET_AES_COMMAND_IV_SET:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_AES_SERVICE_IV_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_aes_wrap_set_iv(service->aes_id, request_body));
        }

        case ET_AES_COMMAND_IV_GET:
        {
            if ((state_is_configured(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_AES_SERVICE_IV_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (et_aes_wrap_get_iv(service->aes_id, response_body) != ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            *response_length = ET_AES_SERVICE_IV_BODY_SIZE;

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_DATA_LENGTH_SET:
        {
            if ((state_is_enabled(service) == 0u) ||
                (request_length != ET_AES_SERVICE_LENGTH_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            data_length = read_u64(request_body);

            return status_from_wrap(et_aes_wrap_set_data_length(service->aes_id, data_length));
        }

        case ET_AES_COMMAND_DATA_LENGTH_GET:
        {
            if ((state_is_enabled(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_AES_SERVICE_LENGTH_BODY_SIZE) ||
                (et_aes_wrap_get_data_length(service->aes_id, &data_length) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u64(response_body, data_length);
            *response_length = ET_AES_SERVICE_LENGTH_BODY_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch synchronous AES processing and status observation or clear commands.
 *
 * @param[in,out] service AES Service instance used by the selected command.
 * @param[in] command_id Stable AES command identifier.
 * @param[in] request_body Command-specific request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note PROCESS delegates bounded Resource-backed execution to handle_process; STATUS_GET and CLEAR
 *       expose or clear normalized hardware facts only and never add test assertions.
 *
 * @return Stable ET status for the selected processing or status command, or INVALID_COMMAND when the
 *         command belongs to another AES command category.
 */
static uint16_t handle_processing_commands(et_aes_service_t *service, uint16_t command_id,
                                           const uint8_t *request_body, uint16_t request_length,
                                           uint8_t *response_body, uint16_t response_capacity,
                                           uint16_t *response_length)
{
    et_aes_wrap_status_snapshot_t status;

    switch (command_id)
    {
        case ET_AES_COMMAND_PROCESS:
        {
            return handle_process(service, request_body, request_length, response_body,
                                  response_capacity, response_length);
        }

        case ET_AES_COMMAND_STATUS_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_AES_SERVICE_STATUS_RESPONSE_SIZE) ||
                (et_aes_wrap_get_status(service->aes_id, &status) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            response_body[ET_AES_SERVICE_STATUS_BUSY_OFFSET] = status.busy;
            response_body[ET_AES_SERVICE_STATUS_DATA_IN_OFFSET] = status.data_in_request;
            response_body[ET_AES_SERVICE_STATUS_DATA_OUT_OFFSET] = status.data_out_request;
            response_body[ET_AES_SERVICE_STATUS_FINISH_OFFSET] = status.finish;
            write_u32(&response_body[ET_AES_SERVICE_STATUS_RESERVED_OFFSET], 0u);
            *response_length = ET_AES_SERVICE_STATUS_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_STATUS_CLEAR:
        {
            if ((request_length != ET_AES_SERVICE_U32_BODY_SIZE) ||
                (read_u32(request_body) > ET_AES_WRAP_STATUS_ALL))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_aes_wrap_clear_status(service->aes_id, (uint8_t)read_u32(request_body)));
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch managed AES IRQ, DMA-request, timed and validation-extension commands.
 *
 * @param[in,out] service AES Service instance owning IRQ and transfer evidence.
 * @param[in] command_id Stable AES command identifier.
 * @param[in] request_body Command-specific request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note IRQ snapshots are copied inside IRQ Manager critical protection. Direct block-write variants
 *       are gated by the explicit test-extension capability and remain bounded hardware operations.
 *
 * @return Stable ET status for the selected IRQ or extension command, or INVALID_COMMAND when unsupported.
 */
static uint16_t handle_irq_and_extension_commands(et_aes_service_t *service, uint16_t command_id,
                                                  const uint8_t *request_body,
                                                  uint16_t request_length, uint8_t *response_body,
                                                  uint16_t response_capacity,
                                                  uint16_t *response_length)
{
    et_aes_wrap_irq_snapshot_t irq_snapshot;
    uint32_t irq_key;

    /* Step 1: Route managed IRQ control and coherent IRQ evidence observation commands. */
    switch (command_id)
    {
        case ET_AES_COMMAND_IRQ_ENABLE:
        case ET_AES_COMMAND_IRQ_DISABLE:
        case ET_AES_COMMAND_IRQ_MASK:
        case ET_AES_COMMAND_IRQ_UNMASK:
        case ET_AES_COMMAND_IRQ_FORCE:
        case ET_AES_COMMAND_IRQ_CLEAR:
        {
            return handle_irq_control(service, command_id, request_body, request_length);
        }

        case ET_AES_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_AES_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE) ||
                (et_aes_wrap_irq_snapshot_get(service->aes_id, &irq_snapshot) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            irq_key = et_irq_manager_enter_critical();
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_RAW_OFFSET], irq_snapshot.raw);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_STATUS_OFFSET],
                      irq_snapshot.status);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_LATCHED_OFFSET],
                      service->latched_events);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_EVENT_COUNT_OFFSET],
                      service->event_count);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_UNEXPECTED_COUNT_OFFSET],
                      service->unexpected_count);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_OVERFLOW_COUNT_OFFSET],
                      service->overflow_count);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_SNAPSHOT_GENERATION_OFFSET],
                      service->generation);
            et_irq_manager_exit_critical(irq_key);
            *response_length = ET_AES_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        /* Step 2: Route DMA request, IRQ-transfer, timed and bounded test-extension commands. */
        case ET_AES_COMMAND_DMA_REQUEST_SET:
        {
            if ((request_length != ET_AES_SERVICE_U32_BODY_SIZE) ||
                (read_u32(request_body) > ET_AES_WRAP_DMA_ALL))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_aes_wrap_dma_request_set(service->aes_id, read_u32(request_body)));
        }

        case ET_AES_COMMAND_IRQ_TRANSFER_START:
        {
            return handle_irq_transfer_start(service, request_body, request_length);
        }

        case ET_AES_COMMAND_IRQ_TRANSFER_STATUS_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_AES_SERVICE_IRQ_TRANSFER_STATUS_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_STATE_OFFSET], service->irq_state);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_INPUT_OFFSET],
                      service->irq_input_offset);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_OUTPUT_OFFSET],
                      service->irq_output_offset);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_PRODUCED_OFFSET],
                      service->irq_produced_bytes);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_FAULT_OFFSET],
                      service->irq_fault_flags);
            write_u32(&response_body[ET_AES_SERVICE_IRQ_TRANSFER_BLOCK_COUNT_OFFSET],
                      service->irq_block_count);
            *response_length = ET_AES_SERVICE_IRQ_TRANSFER_STATUS_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_IRQ_TRANSFER_ABORT:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            clear_irq_transfer_state(service, ET_AES_IRQ_TRANSFER_ABORTED);

            if (et_aes_wrap_irq_mask(service->aes_id, ET_AES_SERVICE_IRQ_REQUEST_EVENTS) !=
                ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_TIMED_PROCESS:
        {
            return handle_timed_process(service, request_body, request_length, response_body,
                                        response_capacity, response_length);
        }

        case ET_AES_COMMAND_BLOCK_WRITE:
        {
            if ((state_is_configured(service) == 0u) || (request_length != ET_AES_WRAP_BLOCK_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            /*
         * The public BLOCK_WRITE command is a bounded synchronous action. It
         * must reach the hardware even when the input request arrives a few
         * cycles later; the ISR path continues to use the non-blocking Wrap.
         */
            return status_from_wrap(et_aes_wrap_block_write_wait(service->aes_id, request_body));
        }

        case ET_AES_COMMAND_BLOCK_READ:
        {
            if ((state_is_configured(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_AES_WRAP_BLOCK_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (et_aes_wrap_block_read(service->aes_id, response_body) != ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_BUSY;
            }

            *response_length = ET_AES_WRAP_BLOCK_SIZE;

            return ET_STATUS_OK;
        }

        case ET_AES_COMMAND_BLOCK_WRITE_DIRECT:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_AES_WRAP_BLOCK_SIZE) ||
                ((service->capabilities.feature_flags & ET_AES_WRAP_CAP_TEST_EXTENSIONS) == 0u))
            {
                return ET_STATUS_NOT_SUPPORTED;
            }

            return status_from_wrap(et_aes_wrap_block_write_direct(service->aes_id, request_body));
        }

        case ET_AES_COMMAND_BLOCK_WRITE_PAIR_DIRECT:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_AES_SERVICE_BLOCK_PAIR_SIZE) ||
                ((service->capabilities.feature_flags & ET_AES_WRAP_CAP_TEST_EXTENSIONS) == 0u))
            {
                return ET_STATUS_NOT_SUPPORTED;
            }

            return status_from_wrap(et_aes_wrap_block_write_pair_direct(
                service->aes_id, request_body, &request_body[ET_AES_WRAP_BLOCK_SIZE]));
        }

        case ET_AES_COMMAND_BLOCK_WRITE_DISABLE_DIRECT:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_AES_WRAP_BLOCK_SIZE) ||
                ((service->capabilities.feature_flags & ET_AES_WRAP_CAP_TEST_EXTENSIONS) == 0u))
            {
                return ET_STATUS_NOT_SUPPORTED;
            }

            if (et_aes_wrap_block_write_disable_direct(service->aes_id, request_body) !=
                ET_WRAP_STATUS_OK)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            return finalize_disable_session(service);
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Validate the common AES Service envelope and route one command through the command groups.
 *
 * @param[in,out] context AES Service instance retained by the common router.
 * @param[in] command_id Stable AES command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response-body bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Category dispatch treats INVALID_COMMAND only as a routing miss. Every real validation or
 *       hardware result is returned immediately and is never reinterpreted as a test verdict.
 *
 * @return Stable ET status for the selected command or INVALID_COMMAND when no AES command matches.
 */
static uint16_t aes_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    et_aes_service_t *service = (et_aes_service_t *)context;
    uint16_t status;

    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 1: Start from an empty response and try lifecycle or configuration commands. */
    *response_length = 0u;

    status = handle_lifecycle_commands(service, command_id, request_body, request_length,
                                       response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    /* Phase 2: Fall through only on INVALID_COMMAND to processing and status commands. */
    status = handle_processing_commands(service, command_id, request_body, request_length,
                                        response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    /* Phase 3: Route the remaining namespace to managed IRQ, timed and extension commands. */
    return handle_irq_and_extension_commands(service, command_id, request_body, request_length,
                                             response_body, response_capacity, response_length);
}

/**
 * @brief Initialize one static AES Service instance and cache its selected-chip capability facts.
 *
 * @param[out] service Caller-owned AES Service storage to initialize.
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in,out] irq_manager Common IRQ Manager used by later managed IRQ commands.
 * @param[in] irq_priority Priority requested when the AES IRQ route is bound.
 *
 * @note Initialization queries AES Wrap capabilities and builds the router descriptor only. It does
 *       not enable or configure AES hardware and does not bind an IRQ route.
 *
 * @return 0 when the instance is initialized, otherwise -1 for invalid dependencies or mapping.
 */
int et_aes_service_init(et_aes_service_t *service, et_aes_id_t aes_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    et_aes_wrap_capabilities_t capabilities;

    if ((service == NULL) || (irq_manager == NULL) ||
        (et_aes_wrap_get_capabilities(aes_id, &capabilities) != ET_WRAP_STATUS_OK))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->aes_id = aes_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->capabilities = capabilities;
    service->irq_state = ET_AES_IRQ_TRANSFER_IDLE;
    service->descriptor.service_id = ET_AES_SERVICE_ID;
    service->descriptor.instance_id = aes_id;
    service->descriptor.context = service;
    service->descriptor.handle = aes_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable router descriptor for one initialized AES Service instance.
 *
 * @param[in] service Initialized AES Service instance.
 *
 * @note The returned pointer aliases Service-owned storage; no Service or hardware state changes.
 *
 * @return Pointer to the descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_aes_service_descriptor(const et_aes_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct one AES Service instance through the common IP Service factory contract.
 *
 * @param[out] storage Caller-owned static storage reserved for et_aes_service_t.
 * @param[in] instance_id Stable logical AES instance identifier from the Application manifest.
 * @param[in] context Common factory dependencies including IRQ Manager and priority.
 * @param[out] descriptor Router descriptor produced by the initialized AES Service.
 *
 * @note This adapter delegates validation and capability discovery to et_aes_service_init and does
 *       not enable AES hardware or allocate dynamic memory.
 *
 * @return 0 when the Service and descriptor are created successfully, otherwise -1.
 */
int et_aes_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_aes_service_t *service = (et_aes_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_aes_service_init(service, (et_aes_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_aes_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
