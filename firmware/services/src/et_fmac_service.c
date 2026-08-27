/**
 * @file et_fmac_service.c
 * @brief Decode FMAC commands, call FMAC Wrap and return hardware facts.
 */

#include "et_fmac_service.h"

#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Decode one unaligned little-endian 16-bit Wire field.
 * @param[in] data Two-byte request field.
 * @note This helper only reads caller-owned Wire memory.
 * @return Decoded unsigned value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8u);
}

/**
 * @brief Decode one unaligned little-endian 32-bit Wire field.
 * @param[in] data Four-byte request field.
 * @note This helper only reads caller-owned Wire memory.
 * @return Decoded unsigned value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Encode one unaligned little-endian 16-bit Wire field.
 * @param[out] data Two-byte response field.
 * @param[in] value Value to encode.
 * @note This helper only writes caller-owned Wire memory.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one unaligned little-endian 32-bit Wire field.
 * @param[out] data Four-byte response field.
 * @param[in] value Value to encode.
 * @note This helper only writes caller-owned Wire memory.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Verify that one reserved Wire range contains only zero bytes.
 * @param[in] data Start of the reserved range.
 * @param[in] length Range length in bytes.
 * @note Reserved bytes have no implicit extension semantics.
 * @return Nonzero when every byte is zero, otherwise zero.
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
 * @brief Translate one stable Wrap result to the ET protocol status namespace.
 * @param[in] status FMAC Wrap status.
 * @note This helper does not expose selected-chip Driver values on Wire.
 * @return Equivalent stable ET status.
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
        case ET_WRAP_STATUS_NO_RESOURCE:
        case ET_WRAP_STATUS_TIMEOUT:
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
 * @brief Return the byte width for one stable FMAC data format.
 * @param[in] format Public FMAC data-format value.
 * @note Unknown formats intentionally map to zero for request rejection.
 * @return Item width in bytes, or zero when unsupported.
 */
static uint8_t data_item_size(uint8_t format)
{
    if (format == ET_FMAC_SERVICE_DATA_FORMAT_Q15)
    {
        return (uint8_t)sizeof(int16_t);
    }

    if (format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32)
    {
        return (uint8_t)sizeof(float);
    }

    return 0u;
}

/**
 * @brief Resolve one count-based FMAC Resource request without exposing raw addresses on Wire.
 * @param[in] body Fixed FMAC Resource request body.
 * @param[in] length Request-body length.
 * @param[out] address Resolved target address.
 * @param[out] count Validated item count.
 * @param[out] format Validated public data format.
 * @note Resolution is delegated to Resource Wrap; raw target addresses never cross the Wire.
 * @return Stable Wrap status describing validation or resolution result.
 */
static et_wrap_status_t resolve_resource_request(const uint8_t *body, uint16_t length,
                                                 void **address, uint8_t *count, uint8_t *format)
{
    et_resource_handle_t handle;
    uint32_t offset;
    uint32_t size_bytes;
    uint16_t requested_count;
    uint8_t item_size;

    if ((body == NULL) || (address == NULL) || (count == NULL) || (format == NULL) ||
        (length != ET_FMAC_SERVICE_RESOURCE_BODY_SIZE) ||
        (body[ET_FMAC_SERVICE_RESOURCE_RESERVED_OFFSET] != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    handle = (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_RESOURCE_HANDLE_OFFSET]);
    offset = read_u32(&body[ET_FMAC_SERVICE_RESOURCE_OFFSET_OFFSET]);
    requested_count = read_u16(&body[ET_FMAC_SERVICE_RESOURCE_COUNT_OFFSET]);
    *format = body[ET_FMAC_SERVICE_RESOURCE_FORMAT_OFFSET];
    item_size = data_item_size(*format);

    if ((requested_count == 0u) || (requested_count > ET_FMAC_WRAP_MAX_TRANSFER_ITEMS) ||
        (item_size == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *count = (uint8_t)requested_count;
    size_bytes = (uint32_t)(*count) * item_size;

    return et_resource_wrap_resolve_range(handle, offset, size_bytes, address);
}

/**
 * @brief Decode a complete fixed-size FMAC configuration request.
 * @param[in] service FMAC Service instance owning the logical ID.
 * @param[in] body Fixed configuration request body.
 * @param[in] length Request-body length.
 * @param[out] config Decoded chip-neutral Wrap configuration.
 * @note Semantic range validation remains owned by FMAC Wrap.
 * @return Zero when the Wire envelope is valid, otherwise -1.
 */
static int decode_config(et_fmac_service_t *service, const uint8_t *body, uint16_t length,
                         et_fmac_wrap_config_t *config)
{
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_FMAC_SERVICE_CONFIG_BODY_SIZE) ||
        (bytes_are_zero(&body[ET_FMAC_SERVICE_CONFIG_RESERVED_OFFSET],
                        ET_FMAC_SERVICE_CONFIG_RESERVED_SIZE) == 0u))
    {
        return -1;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_FMAC_WRAP_API_VERSION;
    config->fmac_id = service->fmac_id;
    config->x1_start = body[ET_FMAC_SERVICE_CONFIG_X1_START_OFFSET];
    config->x1_size = body[ET_FMAC_SERVICE_CONFIG_X1_SIZE_OFFSET];
    config->x1_full_watermark = body[ET_FMAC_SERVICE_CONFIG_X1_WATERMARK_OFFSET];
    config->x2_start = body[ET_FMAC_SERVICE_CONFIG_X2_START_OFFSET];
    config->x2_size = body[ET_FMAC_SERVICE_CONFIG_X2_SIZE_OFFSET];
    config->y_start = body[ET_FMAC_SERVICE_CONFIG_Y_START_OFFSET];
    config->y_size = body[ET_FMAC_SERVICE_CONFIG_Y_SIZE_OFFSET];
    config->y_empty_watermark = body[ET_FMAC_SERVICE_CONFIG_Y_WATERMARK_OFFSET];
    config->final_policy = body[ET_FMAC_SERVICE_CONFIG_FINAL_POLICY_OFFSET];
    config->output_mode = body[ET_FMAC_SERVICE_CONFIG_OUTPUT_MODE_OFFSET];
    config->internal_clip = body[ET_FMAC_SERVICE_CONFIG_INTERNAL_CLIP_OFFSET];
    config->float_input = body[ET_FMAC_SERVICE_CONFIG_FLOAT_INPUT_OFFSET];
    config->float_output = body[ET_FMAC_SERVICE_CONFIG_FLOAT_OUTPUT_OFFSET];
    config->output_shift = body[ET_FMAC_SERVICE_CONFIG_SHIFT_OFFSET];
    config->output_offset = read_u16(&body[ET_FMAC_SERVICE_CONFIG_OUTPUT_OFFSET_OFFSET]);

    return 0;
}

/**
 * @brief Encode stable FMAC capabilities into the fixed Wire response.
 * @param[in] capabilities Chip-neutral FMAC capabilities.
 * @param[out] body Fixed capability response body.
 * @note Only public capability fields are encoded.
 */
static void encode_capabilities(const et_fmac_wrap_capabilities_t *capabilities, uint8_t *body)
{
    write_u16(&body[0], capabilities->api_version);
    write_u16(&body[2], ET_FMAC_SERVICE_CAPABILITIES_SIZE);
    write_u32(&body[4], capabilities->feature_flags);
    write_u16(&body[8], capabilities->max_transfer_items);
    body[10] = capabilities->logical_address_bits;
    body[11] = capabilities->max_feedforward_taps;
    body[12] = capabilities->max_feedback_taps;
    body[13] = capabilities->watermark_mask;
    body[14] = capabilities->output_mode_mask;
    body[15] = capabilities->shift_mask_width;
    write_u16(&body[16], capabilities->irq_source_mask);
    body[18] = capabilities->fir_first_valid_output_index;
    body[19] = capabilities->iir_first_valid_output_index;
}

/**
 * @brief Encode a stable FMAC configuration snapshot.
 * @param[in] snapshot Chip-neutral FMAC configuration snapshot.
 * @param[out] body Fixed snapshot response body.
 * @note Encoding preserves the public configuration field order.
 */
static void encode_config_snapshot(const et_fmac_wrap_config_snapshot_t *snapshot, uint8_t *body)
{
    body[0] = snapshot->x1_start;
    body[1] = snapshot->x1_size;
    body[2] = snapshot->x1_full_watermark;
    body[3] = snapshot->x2_start;
    body[4] = snapshot->x2_size;
    body[5] = snapshot->y_start;
    body[6] = snapshot->y_size;
    body[7] = snapshot->y_empty_watermark;
    body[8] = snapshot->final_policy;
    body[9] = snapshot->output_mode;
    body[10] = snapshot->internal_clip;
    body[11] = snapshot->float_input;
    body[12] = snapshot->float_output;
    body[13] = snapshot->output_shift;
    write_u16(&body[14], snapshot->output_offset);
}

/**
 * @brief Encode one FMAC status snapshot without collapsing distinct hardware facts.
 * @param[in] snapshot Chip-neutral FMAC hardware status snapshot.
 * @param[out] body Fixed status response body.
 * @note Raw status and individual Boolean observations remain separately visible.
 */
static void encode_status(const et_fmac_wrap_status_snapshot_t *snapshot, uint8_t *body)
{
    body[0] = snapshot->active;
    body[1] = snapshot->x1_spare_count;
    body[2] = snapshot->y_unread_count;
    body[3] = snapshot->x1_full;
    body[4] = snapshot->y_empty;
    body[5] = snapshot->x1_overflow;
    body[6] = snapshot->y_underflow;
    body[7] = snapshot->accumulator_saturation;
    body[8] = snapshot->negative_after_offset;
    body[9] = snapshot->float_to_q15_overflow;
    body[10] = 0u;
    body[11] = 0u;
}

/**
 * @brief Snapshot and acknowledge Service-owned FMAC IRQ sources in interrupt context.
 * @param[in,out] context FMAC Service instance registered with IRQ Manager.
 * @param[in] irq_line Physical line reported by IRQ Manager.
 * @param[in] route_events Logical route-event mask delivered by IRQ Manager.
 * @note The callback performs one bounded snapshot, evidence update and owned-source clear.
 */
static void fmac_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_fmac_service_t *service = (et_fmac_service_t *)context;
    et_fmac_wrap_irq_snapshot_t snapshot;
    uint32_t delivered;

    (void)irq_line;
    (void)route_events;

    if ((service == NULL) || (service->irq_bound == 0u) ||
        (et_fmac_wrap_irq_snapshot_get(service->fmac_id, &snapshot) != ET_WRAP_STATUS_OK))
    {
        return;
    }

    delivered = snapshot.status & service->irq_enabled_sources & ~service->irq_masked_sources;
    service->irq_captured_raw |= snapshot.raw;
    service->irq_captured_status |= snapshot.status;
    service->irq_latched_sources |= delivered;

    if ((delivered != 0u) && (service->irq_event_count != UINT32_MAX))
    {
        ++service->irq_event_count;
    }

    if (delivered != 0u)
    {
        uint32_t auto_mask_sources = delivered & ET_FMAC_SERVICE_AUTO_MASK_IRQS;

        /*
         * Some FMAC sources remain asserted until the underlying condition is
         * repaired. Mask every delivered source before acknowledgement so one
         * malformed stimulus cannot monopolize the CPU in the ISR. The PC
         * explicitly clears and unmasks a source before rearming it.
         */
        if (auto_mask_sources != 0u)
        {
            (void)et_fmac_wrap_irq_mask(service->fmac_id, auto_mask_sources);
            service->irq_masked_sources |= auto_mask_sources;
        }

        (void)et_fmac_wrap_irq_clear(service->fmac_id, delivered);
    }
}

/**
 * @brief Release the FMAC IRQ Manager binding when no source remains owned.
 * @param[in,out] service FMAC Service instance.
 * @note Hardware interrupt sources must be disabled before this helper is called.
 * @return Zero when no route remains bound, otherwise -1.
 */
static int irq_unbind(et_fmac_service_t *service)
{
    if ((service == NULL) || (service->irq_bound == 0u))
    {
        return 0;
    }

    if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line, fmac_irq_callback,
                              service) != 0)
    {
        return -1;
    }

    service->irq_bound = 0u;

    return 0;
}

/**
 * @brief Reset only the mutable state owned by one FMAC Service instance.
 * @param[in,out] service FMAC Service instance.
 * @note The PC resets FMAC hardware through CRG before this command. This
 *       helper only releases the IRQ Manager binding and clears Service-owned
 *       bookkeeping; it does not call CRG, Resource, or another IP Wrap.
 * @return Stable ET status for the complete Service-state reset.
 */
static uint16_t state_reset(et_fmac_service_t *service)
{
    if ((service == NULL) || (irq_unbind(service) != 0))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->configured = 0u;
    service->irq_enabled_sources = 0u;
    service->irq_masked_sources = 0u;
    service->irq_captured_raw = 0u;
    service->irq_captured_status = 0u;
    service->irq_latched_sources = 0u;
    service->irq_event_count = 0u;
    (void)memset(&service->irq_route, 0, sizeof(service->irq_route));

    return ET_STATUS_OK;
}

/**
 * @brief Enable selected FMAC IRQ sources under one managed callback binding.
 * @param[in,out] service FMAC Service instance.
 * @param[in] source_bits Nonempty normalized FMAC source mask.
 * @note Route binding precedes hardware source enable; failures roll back partial ownership.
 * @return Stable ET status for the complete ownership operation.
 */
static uint16_t irq_enable(et_fmac_service_t *service, uint32_t source_bits)
{
    uint8_t newly_bound = 0u;

    if ((et_fmac_wrap_irq_disable(service->fmac_id, source_bits) != ET_WRAP_STATUS_OK) ||
        (et_fmac_wrap_irq_clear(service->fmac_id, source_bits) != ET_WRAP_STATUS_OK))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_captured_raw &= ~source_bits;
    service->irq_captured_status &= ~source_bits;
    service->irq_latched_sources &= ~source_bits;

    if (service->irq_bound == 0u)
    {
        if ((et_fmac_wrap_get_irq_route(service->fmac_id, &service->irq_route) !=
             ET_WRAP_STATUS_OK) ||
            (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                                 fmac_irq_callback, service) != 0))
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        service->irq_bound = 1u;
        newly_bound = 1u;
    }

    service->irq_enabled_sources |= source_bits;

    if (et_fmac_wrap_irq_enable(service->fmac_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        service->irq_enabled_sources &= ~source_bits;

        if (newly_bound != 0u)
        {
            (void)irq_unbind(service);
        }

        return ET_STATUS_INTERNAL_ERROR;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Disable selected FMAC IRQ sources and release an unused binding.
 * @param[in,out] service FMAC Service instance.
 * @param[in] source_bits Nonempty normalized FMAC source mask.
 * @note Source ownership changes only after hardware disable succeeds.
 * @return Stable ET status for the complete release operation.
 */
static uint16_t irq_disable(et_fmac_service_t *service, uint32_t source_bits)
{
    if (et_fmac_wrap_irq_disable(service->fmac_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_enabled_sources &= ~source_bits;
    service->irq_masked_sources &= ~source_bits;

    if ((service->irq_enabled_sources == 0u) && (irq_unbind(service) != 0))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Decode and validate one nonempty FMAC IRQ source request.
 * @param[in] service FMAC Service instance publishing the supported source mask.
 * @param[in] body Fixed source-mask request body.
 * @param[in] length Request-body length.
 * @param[out] source_bits Decoded normalized source mask.
 * @note Unknown bits are rejected before any interrupt state changes.
 * @return Zero when valid, otherwise -1.
 */
static int decode_source_bits(const et_fmac_service_t *service, const uint8_t *body,
                              uint16_t length, uint32_t *source_bits)
{
    if ((service == NULL) || (body == NULL) || (source_bits == NULL) ||
        (length != ET_FMAC_SERVICE_SOURCE_BODY_SIZE))
    {
        return -1;
    }

    *source_bits = read_u32(body);

    return ((*source_bits != 0u) && ((*source_bits & ~service->capabilities.irq_source_mask) == 0u))
               ? 0
               : -1;
}

/**
 * @brief Resolve both coefficient Resource ranges from one fixed request body.
 * @param[in] body Fixed coefficient-load request body.
 * @param[in] length Request-body length.
 * @param[out] feedforward Resolved feedforward array.
 * @param[out] feedforward_count Validated feedforward item count.
 * @param[out] feedback Resolved feedback array, or NULL for an empty array.
 * @param[out] feedback_count Validated feedback item count.
 * @note Both arrays remain caller-owned Resource allocations.
 * @return Stable Wrap status describing validation or resolution result.
 */
static et_wrap_status_t resolve_coefficients(const uint8_t *body, uint16_t length,
                                             int16_t **feedforward, uint8_t *feedforward_count,
                                             int16_t **feedback, uint8_t *feedback_count)
{
    et_resource_handle_t handle;
    uint32_t offset;
    uint32_t size;

    if ((body == NULL) || (feedforward == NULL) || (feedforward_count == NULL) ||
        (feedback == NULL) || (feedback_count == NULL) ||
        (length != ET_FMAC_SERVICE_COEFFICIENT_BODY_SIZE) ||
        (bytes_are_zero(&body[ET_FMAC_SERVICE_COEFF_FEEDFORWARD_RESERVED_OFFSET],
                        ET_FMAC_SERVICE_COEFF_RESERVED_SIZE) == 0u) ||
        (bytes_are_zero(&body[ET_FMAC_SERVICE_COEFF_FEEDBACK_RESERVED_OFFSET],
                        ET_FMAC_SERVICE_COEFF_RESERVED_SIZE) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *feedforward_count = body[ET_FMAC_SERVICE_COEFF_FEEDFORWARD_COUNT_OFFSET];
    *feedback_count = body[ET_FMAC_SERVICE_COEFF_FEEDBACK_COUNT_OFFSET];

    if (*feedforward_count == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    handle = (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_COEFF_FEEDFORWARD_HANDLE_OFFSET]);
    offset = read_u32(&body[ET_FMAC_SERVICE_COEFF_FEEDFORWARD_OFFSET_OFFSET]);
    size = (uint32_t)(*feedforward_count) * sizeof(int16_t);

    if (et_resource_wrap_resolve_range(handle, offset, size, (void **)feedforward) !=
        ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *feedback = NULL;

    if (*feedback_count != 0u)
    {
        handle =
            (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_COEFF_FEEDBACK_HANDLE_OFFSET]);
        offset = read_u32(&body[ET_FMAC_SERVICE_COEFF_FEEDBACK_OFFSET_OFFSET]);
        size = (uint32_t)(*feedback_count) * sizeof(int16_t);

        return et_resource_wrap_resolve_range(handle, offset, size, (void **)feedback);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute one bounded FMAC one-shot transaction over two Resource ranges.
 * @param[in,out] service Configured FMAC Service instance.
 * @param[in] body Fixed process request body.
 * @param[in] length Request-body length.
 * @param[out] response_body Process response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 * @note The command performs one bounded write/read transaction and returns observed counts/status.
 * @return Stable ET status for validation and hardware execution.
 */
static uint16_t handle_process(et_fmac_service_t *service, const uint8_t *body, uint16_t length,
                               uint8_t *response_body, uint16_t response_capacity,
                               uint16_t *response_length)
{
    void *source;
    void *destination;
    et_resource_handle_t source_handle;
    et_resource_handle_t destination_handle;
    uint32_t source_offset;
    uint32_t destination_offset;
    uint32_t input_count = 0u;
    uint32_t output_count = 0u;
    uint32_t accepted;
    uint32_t read;
    uint32_t budget = ET_FMAC_SERVICE_TIMEOUT_BUDGET;
    uint16_t count;
    uint8_t function;
    uint8_t feedforward_taps;
    uint8_t feedback_taps;
    uint8_t format;
    uint8_t item_size;
    et_wrap_status_t wrap_status;

    /* Phase 1: Validate the public envelope and resolve both caller-owned Resource ranges. */
    if ((service->configured == 0u) || (body == NULL) ||
        (length != ET_FMAC_SERVICE_PROCESS_BODY_SIZE) ||
        (response_capacity < ET_FMAC_SERVICE_PROCESS_RESPONSE_SIZE) ||
        (bytes_are_zero(&body[ET_FMAC_SERVICE_PROCESS_RESERVED_OFFSET],
                        ET_FMAC_SERVICE_PROCESS_RESERVED_SIZE) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    function = body[ET_FMAC_SERVICE_PROCESS_FUNCTION_OFFSET];
    feedforward_taps = body[ET_FMAC_SERVICE_PROCESS_FEEDFORWARD_OFFSET];
    feedback_taps = body[ET_FMAC_SERVICE_PROCESS_FEEDBACK_OFFSET];
    format = body[ET_FMAC_SERVICE_PROCESS_FORMAT_OFFSET];
    count = read_u16(&body[ET_FMAC_SERVICE_PROCESS_COUNT_OFFSET]);
    item_size = data_item_size(format);

    if ((count == 0u) || (count > service->capabilities.max_transfer_items) || (item_size == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    source_handle =
        (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_PROCESS_SOURCE_HANDLE_OFFSET]);
    source_offset = read_u32(&body[ET_FMAC_SERVICE_PROCESS_SOURCE_OFFSET_OFFSET]);
    destination_handle =
        (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_PROCESS_DESTINATION_HANDLE_OFFSET]);
    destination_offset = read_u32(&body[ET_FMAC_SERVICE_PROCESS_DESTINATION_OFFSET_OFFSET]);

    if ((et_resource_wrap_resolve_range(source_handle, source_offset, (uint32_t)count * item_size,
                                        &source) != ET_WRAP_STATUS_OK) ||
        (et_resource_wrap_resolve_range(destination_handle, destination_offset,
                                        (uint32_t)count * item_size,
                                        &destination) != ET_WRAP_STATUS_OK))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    if (et_fmac_wrap_start(service->fmac_id, function, feedforward_taps, feedback_taps) !=
        ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_BUSY;
    }

    /* Phase 2: Pump bounded input/output chunks while preserving the first Wrap failure. */
    while ((input_count < count) || (output_count < count))
    {
        accepted = 0u;
        read = 0u;

        if (input_count < count)
        {
            wrap_status = et_fmac_wrap_stream_write(
                service->fmac_id, &((uint8_t *)source)[input_count * item_size],
                (uint8_t)(count - input_count),
                (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32), &accepted);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                (void)et_fmac_wrap_stop(service->fmac_id);

                return status_from_wrap(wrap_status);
            }

            input_count += accepted;
        }

        if (output_count < count)
        {
            wrap_status = et_fmac_wrap_stream_read(
                service->fmac_id, &((uint8_t *)destination)[output_count * item_size],
                (uint8_t)(count - output_count),
                (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32), &read);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                (void)et_fmac_wrap_stop(service->fmac_id);

                return status_from_wrap(wrap_status);
            }

            output_count += read;
        }

        if ((accepted == 0u) && (read == 0u))
        {
            if (budget-- == 0u)
            {
                (void)et_fmac_wrap_stop(service->fmac_id);

                return ET_STATUS_BUSY;
            }
        }
    }

    /* Phase 3: Return only the accepted and observed item counts. */
    write_u32(&response_body[ET_FMAC_SERVICE_PROCESS_INPUT_COUNT_OFFSET], input_count);
    write_u32(&response_body[ET_FMAC_SERVICE_PROCESS_OUTPUT_COUNT_OFFSET], output_count);
    *response_length = ET_FMAC_SERVICE_PROCESS_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Execute one bounded FMAC transaction inside a target-local DWT timing window.
 * @param[in,out] service Configured FMAC Service instance.
 * @param[in] body Fixed process request body shared with PROCESS.
 * @param[in] length Request-body length.
 * @param[out] response_body Timed-process response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 * @note The FMAC Wrap owns the atomic hardware timing window; PC owns the performance verdict.
 * @return Stable ET status for validation and hardware execution.
 */
static uint16_t handle_process_timed(et_fmac_service_t *service, const uint8_t *body,
                                     uint16_t length, uint8_t *response_body,
                                     uint16_t response_capacity, uint16_t *response_length)
{
    void *source;
    void *destination;
    et_resource_handle_t source_handle;
    et_resource_handle_t destination_handle;
    uint32_t source_offset;
    uint32_t destination_offset;
    uint32_t accepted_count;
    uint32_t read_count;
    uint32_t elapsed_cycles;
    uint16_t count;
    uint8_t function;
    uint8_t feedforward_taps;
    uint8_t feedback_taps;
    uint8_t format;
    uint8_t item_size;
    et_wrap_status_t wrap_status;

    /* Phase 1: Validate the fixed Wire envelope and both Resource ranges. */
    if ((service->configured == 0u) || (body == NULL) ||
        (length != ET_FMAC_SERVICE_PROCESS_BODY_SIZE) ||
        (response_capacity < ET_FMAC_SERVICE_TIMED_PROCESS_RESPONSE_SIZE) ||
        (bytes_are_zero(&body[ET_FMAC_SERVICE_PROCESS_RESERVED_OFFSET],
                        ET_FMAC_SERVICE_PROCESS_RESERVED_SIZE) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    function = body[ET_FMAC_SERVICE_PROCESS_FUNCTION_OFFSET];
    feedforward_taps = body[ET_FMAC_SERVICE_PROCESS_FEEDFORWARD_OFFSET];
    feedback_taps = body[ET_FMAC_SERVICE_PROCESS_FEEDBACK_OFFSET];
    format = body[ET_FMAC_SERVICE_PROCESS_FORMAT_OFFSET];
    count = read_u16(&body[ET_FMAC_SERVICE_PROCESS_COUNT_OFFSET]);
    item_size = data_item_size(format);

    if ((count == 0u) || (count > service->capabilities.max_transfer_items) || (item_size == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    source_handle =
        (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_PROCESS_SOURCE_HANDLE_OFFSET]);
    source_offset = read_u32(&body[ET_FMAC_SERVICE_PROCESS_SOURCE_OFFSET_OFFSET]);
    destination_handle =
        (et_resource_handle_t)read_u32(&body[ET_FMAC_SERVICE_PROCESS_DESTINATION_HANDLE_OFFSET]);
    destination_offset = read_u32(&body[ET_FMAC_SERVICE_PROCESS_DESTINATION_OFFSET_OFFSET]);

    if ((et_resource_wrap_resolve_range(source_handle, source_offset, (uint32_t)count * item_size,
                                        &source) != ET_WRAP_STATUS_OK) ||
        (et_resource_wrap_resolve_range(destination_handle, destination_offset,
                                        (uint32_t)count * item_size,
                                        &destination) != ET_WRAP_STATUS_OK))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute exactly one target-side timed FMAC transaction. */
    wrap_status = et_fmac_wrap_process_timed(
        service->fmac_id, function, feedforward_taps, feedback_taps, source, destination, count,
        (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32), ET_FMAC_SERVICE_TIMEOUT_BUDGET,
        &accepted_count, &read_count, &elapsed_cycles);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(wrap_status);
    }

    /* Phase 3: Publish raw counts and cycle evidence without a performance verdict. */
    write_u32(&response_body[ET_FMAC_SERVICE_TIMED_INPUT_COUNT_OFFSET], accepted_count);
    write_u32(&response_body[ET_FMAC_SERVICE_TIMED_OUTPUT_COUNT_OFFSET], read_count);
    write_u32(&response_body[ET_FMAC_SERVICE_TIMED_CYCLES_OFFSET], elapsed_cycles);
    *response_length = ET_FMAC_SERVICE_TIMED_PROCESS_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Route one decoded FMAC command to its atomic Wrap operation.
 * @param[in,out] context FMAC Service instance.
 * @param[in] command_id Public FMAC command identifier.
 * @param[in] request_body Command request body.
 * @param[in] request_length Request-body length.
 * @param[out] response_body Response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 * @note Each branch performs one atomic FMAC Service operation; Case orchestration stays on PC.
 * @return Stable ET command status.
 */
static uint16_t fmac_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                            uint16_t request_length, uint8_t *response_body,
                            uint16_t response_capacity, uint16_t *response_length)
{
    et_fmac_service_t *service = (et_fmac_service_t *)context;
    et_fmac_wrap_config_t config;
    et_fmac_wrap_config_snapshot_t config_snapshot;
    et_fmac_wrap_status_snapshot_t status_snapshot;
    et_fmac_wrap_irq_snapshot_t irq_snapshot;
    void *resource;
    int16_t *feedforward;
    int16_t *feedback;
    uint32_t source_bits;
    uint32_t count;
    uint32_t raw_value;
    uint8_t item_count;
    uint8_t format;
    uint8_t feedforward_count;
    uint8_t feedback_count;
    et_wrap_status_t wrap_status = ET_WRAP_STATUS_INVALID_ARGUMENT;

    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *response_length = 0u;

    /* Phase 1: Route lifecycle, configuration and direct-data operations. */
    switch (command_id)
    {
        case ET_FMAC_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_FMAC_SERVICE_CAPABILITIES_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            encode_capabilities(&service->capabilities, response_body);
            *response_length = ET_FMAC_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_FMAC_COMMAND_CONFIGURE:
        {
            if (decode_config(service, request_body, request_length, &config) != 0)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_fmac_wrap_configure(service->fmac_id, &config);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            service->configured = 1u;

            return ET_STATUS_OK;
        }

        case ET_FMAC_COMMAND_CONFIG_SNAPSHOT_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_FMAC_SERVICE_CONFIG_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_fmac_wrap_config_snapshot_get(service->fmac_id, &config_snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            encode_config_snapshot(&config_snapshot, response_body);
            *response_length = ET_FMAC_SERVICE_CONFIG_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_FMAC_COMMAND_START:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_FMAC_SERVICE_START_BODY_SIZE) ||
                (request_body[ET_FMAC_SERVICE_START_RESERVED_OFFSET] != 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_fmac_wrap_start(
                service->fmac_id, request_body[ET_FMAC_SERVICE_START_FUNCTION_OFFSET],
                request_body[ET_FMAC_SERVICE_START_FEEDFORWARD_OFFSET],
                request_body[ET_FMAC_SERVICE_START_FEEDBACK_OFFSET]));
        }

        case ET_FMAC_COMMAND_START_UNCHECKED:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_FMAC_SERVICE_START_BODY_SIZE) ||
                (request_body[ET_FMAC_SERVICE_START_RESERVED_OFFSET] != 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_fmac_wrap_start_unchecked(
                service->fmac_id, request_body[ET_FMAC_SERVICE_START_FUNCTION_OFFSET],
                request_body[ET_FMAC_SERVICE_START_FEEDFORWARD_OFFSET],
                request_body[ET_FMAC_SERVICE_START_FEEDBACK_OFFSET]));
        }

        case ET_FMAC_COMMAND_STOP:
        {
            return (request_length == 0u) ? status_from_wrap(et_fmac_wrap_stop(service->fmac_id))
                                          : ET_STATUS_INVALID_PARAM;
        }

        case ET_FMAC_COMMAND_CLEAR:
        {
            return (request_length == 0u) ? status_from_wrap(et_fmac_wrap_clear(service->fmac_id))
                                          : ET_STATUS_INVALID_PARAM;
        }

        case ET_FMAC_COMMAND_STATE_RESET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return state_reset(service);
        }

        case ET_FMAC_COMMAND_X1_PRELOAD:
        case ET_FMAC_COMMAND_Y_PRELOAD:
        case ET_FMAC_COMMAND_STREAM_WRITE:
        case ET_FMAC_COMMAND_STREAM_READ:
        {
            wrap_status = resolve_resource_request(request_body, request_length, &resource,
                                                   &item_count, &format);

            if ((service->configured == 0u) || (wrap_status != ET_WRAP_STATUS_OK) ||
                (response_capacity < ET_FMAC_SERVICE_COUNT_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            count = item_count;

            if (command_id == ET_FMAC_COMMAND_X1_PRELOAD)
            {
                wrap_status = et_fmac_wrap_x1_preload(
                    service->fmac_id, resource, item_count,
                    (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32),
                    ET_FMAC_SERVICE_TIMEOUT_BUDGET);
            }
            else if (command_id == ET_FMAC_COMMAND_Y_PRELOAD)
            {
                wrap_status =
                    et_fmac_wrap_y_preload(service->fmac_id, resource, item_count,
                                           (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32),
                                           ET_FMAC_SERVICE_TIMEOUT_BUDGET);
            }
            else if (command_id == ET_FMAC_COMMAND_STREAM_WRITE)
            {
                wrap_status = et_fmac_wrap_stream_write(
                    service->fmac_id, resource, item_count,
                    (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32), &count);
            }
            else
            {
                wrap_status = et_fmac_wrap_stream_read(
                    service->fmac_id, resource, item_count,
                    (uint8_t)(format == ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32), &count);
            }

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(response_body, count);
            *response_length = ET_FMAC_SERVICE_COUNT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_FMAC_COMMAND_COEFFICIENTS_LOAD:
        {
            wrap_status = resolve_coefficients(request_body, request_length, &feedforward,
                                               &feedforward_count, &feedback, &feedback_count);

            if ((service->configured == 0u) || (wrap_status != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_fmac_wrap_coefficients_load(
                service->fmac_id, feedforward, feedforward_count, feedback, feedback_count,
                ET_FMAC_SERVICE_TIMEOUT_BUDGET));
        }

        case ET_FMAC_COMMAND_DATA_WRITE_ONE_UNCHECKED:
        {
            if ((service->configured == 0u) || (request_length != ET_FMAC_SERVICE_RAW_VALUE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_fmac_wrap_data_write_one_unchecked(service->fmac_id, read_u32(request_body)));
        }

        case ET_FMAC_COMMAND_DATA_READ_ONE_UNCHECKED:
        {
            if ((service->configured == 0u) || (request_length != 0u) ||
                (response_capacity < ET_FMAC_SERVICE_RAW_VALUE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_fmac_wrap_data_read_one_unchecked(service->fmac_id, &raw_value);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(response_body, raw_value);
            *response_length = ET_FMAC_SERVICE_RAW_VALUE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_FMAC_COMMAND_PROCESS:
        {
            return handle_process(service, request_body, request_length, response_body,
                                  response_capacity, response_length);
        }

        case ET_FMAC_COMMAND_PROCESS_TIMED:
        {
            return handle_process_timed(service, request_body, request_length, response_body,
                                        response_capacity, response_length);
        }

        case ET_FMAC_COMMAND_STATUS_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_FMAC_SERVICE_STATUS_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_fmac_wrap_status_get(service->fmac_id, &status_snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            encode_status(&status_snapshot, response_body);
            *response_length = ET_FMAC_SERVICE_STATUS_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        /* Phase 2: Route managed interrupt ownership and evidence operations. */
        case ET_FMAC_COMMAND_IRQ_ENABLE:
        case ET_FMAC_COMMAND_IRQ_DISABLE:
        case ET_FMAC_COMMAND_IRQ_MASK:
        case ET_FMAC_COMMAND_IRQ_UNMASK:
        case ET_FMAC_COMMAND_IRQ_FORCE:
        case ET_FMAC_COMMAND_IRQ_CLEAR:
        {
            if (decode_source_bits(service, request_body, request_length, &source_bits) != 0)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_FMAC_COMMAND_IRQ_ENABLE)
            {
                return irq_enable(service, source_bits);
            }

            if (command_id == ET_FMAC_COMMAND_IRQ_DISABLE)
            {
                return irq_disable(service, source_bits);
            }

            if (command_id == ET_FMAC_COMMAND_IRQ_MASK)
            {
                wrap_status = et_fmac_wrap_irq_mask(service->fmac_id, source_bits);

                if (wrap_status == ET_WRAP_STATUS_OK)
                {
                    service->irq_masked_sources |= source_bits;
                }
            }
            else if (command_id == ET_FMAC_COMMAND_IRQ_UNMASK)
            {
                wrap_status = et_fmac_wrap_irq_unmask(service->fmac_id, source_bits);

                if (wrap_status == ET_WRAP_STATUS_OK)
                {
                    service->irq_masked_sources &= ~source_bits;
                }
            }
            else if (command_id == ET_FMAC_COMMAND_IRQ_FORCE)
            {
                wrap_status = et_fmac_wrap_irq_force(service->fmac_id, source_bits);
            }
            else if (command_id == ET_FMAC_COMMAND_IRQ_CLEAR)
            {
                wrap_status = et_fmac_wrap_irq_clear(service->fmac_id, source_bits);

                if (wrap_status == ET_WRAP_STATUS_OK)
                {
                    service->irq_captured_raw &= ~source_bits;
                    service->irq_captured_status &= ~source_bits;
                    service->irq_latched_sources &= ~source_bits;
                }
            }

            return status_from_wrap(wrap_status);
        }

        /* Phase 3: Route the atomic DMA-request gate without configuring another IP. */
        case ET_FMAC_COMMAND_DMA_REQUEST_SET:
        {
            if ((request_body == NULL) || (request_length != ET_FMAC_SERVICE_SOURCE_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            source_bits = read_u32(request_body);

            if ((source_bits & ~ET_FMAC_WRAP_DMA_ALL) != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_fmac_wrap_dma_request_set(service->fmac_id, source_bits));
        }

        case ET_FMAC_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_FMAC_SERVICE_IRQ_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_fmac_wrap_irq_snapshot_get(service->fmac_id, &irq_snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_RAW_OFFSET],
                      irq_snapshot.raw | service->irq_captured_raw);
            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_STATUS_OFFSET],
                      irq_snapshot.status | service->irq_captured_status);
            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_LATCHED_OFFSET],
                      service->irq_latched_sources);
            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_EVENT_COUNT_OFFSET],
                      service->irq_event_count);
            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_ENABLED_OFFSET],
                      service->irq_enabled_sources);
            write_u32(&response_body[ET_FMAC_SERVICE_IRQ_MASKED_OFFSET],
                      service->irq_masked_sources);
            *response_length = ET_FMAC_SERVICE_IRQ_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one FMAC Service instance without touching FMAC hardware.
 * @param[out] service Caller-owned FMAC Service storage.
 * @param[in] fmac_id Stable logical FMAC instance identifier.
 * @param[in] irq_manager Common IRQ Manager used for managed interrupt evidence.
 * @param[in] irq_priority Board-selected interrupt priority.
 * @note Initialization creates state and descriptor only; no FMAC Feature action is executed.
 * @return Zero on success, otherwise -1.
 */
int et_fmac_service_init(et_fmac_service_t *service, et_fmac_id_t fmac_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    et_fmac_wrap_capabilities_t capabilities;

    if ((service == NULL) || (irq_manager == NULL) ||
        (et_fmac_wrap_get_capabilities(fmac_id, &capabilities) != ET_WRAP_STATUS_OK))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->fmac_id = fmac_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->capabilities = capabilities;
    service->descriptor.service_id = ET_FMAC_SERVICE_ID;
    service->descriptor.instance_id = fmac_id;
    service->descriptor.context = service;
    service->descriptor.handle = fmac_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable router descriptor for one initialized FMAC Service.
 * @param[in] service Initialized FMAC Service instance.
 * @note The returned pointer aliases Service-owned storage and performs no hardware access.
 * @return Service descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_fmac_service_descriptor(const et_fmac_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct one FMAC Service through the common static factory contract.
 * @param[out] storage Caller-owned storage for one FMAC Service instance.
 * @param[in] instance_id Stable logical FMAC instance identifier.
 * @param[in] context Common factory dependencies including IRQ Manager and priority.
 * @param[out] descriptor Initialized FMAC descriptor.
 * @note This thin adapter forwards manifest facts only and performs no FMAC Feature action.
 * @return Zero on success, otherwise -1.
 */
int et_fmac_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_fmac_service_t *service = (et_fmac_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_fmac_service_init(service, (et_fmac_id_t)instance_id, context->irq_manager,
                             context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_fmac_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
