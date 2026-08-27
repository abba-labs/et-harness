/**
 * @file et_crc_service.c
 * @brief Decode CRC commands, execute CRC Wrap operations and return facts.
 *
 * This service owns only CRC lifecycle state and bounded IRQ evidence. Test
 * sequencing, expected values, performance limits and final verdicts remain
 * in the trusted PC control plane.
 */
#include "et_crc_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Decode one unaligned little-endian 32-bit CRC Wire field.
 *
 * @param[in] data Four bytes containing the encoded value.
 *
 * @note This helper only reads caller-owned request memory and does not access CRC hardware.
 *
 * @return Decoded 32-bit value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Decode one unaligned little-endian 64-bit CRC Wire value from two 32-bit words.
 *
 * @param[in] data Eight bytes containing the encoded value.
 *
 * @note This helper only reads caller-owned request memory and does not interpret the value as an
 *       address until a command-specific handler explicitly performs width validation.
 *
 * @return Decoded 64-bit value.
 */
static uint64_t read_u64(const uint8_t *data)
{
    return (uint64_t)read_u32(data) | ((uint64_t)read_u32(&data[4]) << 32u);
}

/**
 * @brief Verify that one reserved CRC Wire region contains only zero bytes.
 *
 * @param[in] data Reserved bytes to validate.
 * @param[in] length Number of reserved bytes to inspect.
 *
 * @note Reserved bytes are deliberately not assigned semantics by Firmware; nonzero content is
 *       rejected so future protocol extensions cannot be silently misinterpreted.
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
 * @brief Encode one 16-bit value into an unaligned little-endian CRC Wire field.
 *
 * @param[out] data Two-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned response memory and does not modify Service state.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian CRC Wire field.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned response memory and does not modify Service state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Normalize one CRC Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status CRC Wrap status returned by a chip-neutral hardware action.
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
 * @brief Return the legal public value mask for the active CRC width.
 *
 * @param[in] mode Stable CRC8, CRC16 or CRC32 mode.
 *
 * @note The mask is used to reject values that would otherwise be silently truncated by hardware.
 *       No CRC hardware is accessed.
 *
 * @return UINT8_MAX for CRC8, UINT16_MAX for CRC16, otherwise UINT32_MAX.
 */
static uint32_t mode_value_mask(uint8_t mode)
{
    if (mode == ET_CRC_WRAP_MODE_CRC8)
    {
        return UINT8_MAX;
    }

    if (mode == ET_CRC_WRAP_MODE_CRC16)
    {
        return UINT16_MAX;
    }

    return UINT32_MAX;
}

/**
 * @brief Report whether the CRC Service lifecycle is both enabled and configured.
 *
 * @param[in] service CRC Service instance whose lifecycle state is queried.
 *
 * @note This is a read-only Service-state query used before commands that require active configuration.
 *
 * @return Nonzero when service exists and is enabled/configured, otherwise zero.
 */
static uint8_t state_is_configured(const et_crc_service_t *service)
{
    return (uint8_t)((service != NULL) && (service->enabled != 0u) && (service->configured != 0u));
}

/**
 * @brief Decode the fixed CONFIGURE Wire body into the versioned CRC Wrap configuration.
 *
 * @param[in] service CRC Service instance providing the stable logical CRC identifier.
 * @param[in] body Fixed CONFIGURE request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] config Chip-neutral CRC Wrap configuration populated from the Wire fields.
 *
 * @note This function validates only Wire shape and published flag bits. Semantic ranges such as
 *       polynomial width and FIFO limit remain centralized in CRC Wrap; no hardware is configured here.
 *
 * @return 0 when the request is decoded successfully.
 * @return -1 when required pointers, body size or published flags are invalid.
 */
static int decode_config(et_crc_service_t *service, const uint8_t *body, uint16_t length,
                         et_crc_wrap_config_t *config)
{
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_CRC_SERVICE_CONFIG_REQUEST_SIZE) ||
        ((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] & ~ET_CRC_SERVICE_CONFIG_FLAGS_MASK) != 0u))
    {
        return -1;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_CRC_WRAP_API_VERSION;
    config->crc_id = service->crc_id;
    config->mode = body[ET_CRC_SERVICE_CONFIG_MODE_OFFSET];
    config->ref_in = (uint8_t)((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] &
                                ET_CRC_SERVICE_CONFIG_REF_IN_FLAG) != 0u);
    config->ref_out = (uint8_t)((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] &
                                 ET_CRC_SERVICE_CONFIG_REF_OUT_FLAG) != 0u);
    config->byte_swap = (uint8_t)((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] &
                                   ET_CRC_SERVICE_CONFIG_BYTE_SWAP_FLAG) != 0u);
    config->auto_length_reload = (uint8_t)((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] &
                                            ET_CRC_SERVICE_CONFIG_AUTO_RELOAD_FLAG) != 0u);
    config->result_check = (uint8_t)((body[ET_CRC_SERVICE_CONFIG_FLAGS_OFFSET] &
                                      ET_CRC_SERVICE_CONFIG_RESULT_CHECK_FLAG) != 0u);
    config->xor_out = body[ET_CRC_SERVICE_CONFIG_XOR_OFFSET];
    config->fifo_threshold = body[ET_CRC_SERVICE_CONFIG_FIFO_THRESHOLD_OFFSET];
    config->polynomial = read_u32(&body[ET_CRC_SERVICE_CONFIG_POLYNOMIAL_OFFSET]);
    config->initial_value = read_u32(&body[ET_CRC_SERVICE_CONFIG_INITIAL_VALUE_OFFSET]);

    return 0;
}

/**
 * @brief Decode and validate one nonempty normalized CRC interrupt-source mask.
 *
 * @param[in] body Fixed source-mask request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] source_bits Stable CRC Wrap interrupt-source mask.
 *
 * @note Unknown source bits are rejected before any IRQ state is changed; this helper performs no
 *       hardware operation.
 *
 * @return 0 when one valid nonempty source mask is decoded.
 * @return -1 when pointers, body size or source bits are invalid.
 */
static int decode_source_bits(const uint8_t *body, uint16_t length, uint32_t *source_bits)
{
    if ((body == NULL) || (source_bits == NULL) || (length != ET_CRC_SERVICE_SOURCE_REQUEST_SIZE))
    {
        return -1;
    }

    *source_bits = read_u32(body);

    if ((*source_bits == 0u) || ((*source_bits & ~ET_CRC_WRAP_IRQ_ALL) != 0u))
    {
        return -1;
    }

    return 0;
}

/**
 * @brief Capture bounded CRC interrupt observations into Service-owned evidence state.
 *
 * @param[in,out] context CRC Service instance registered as the IRQ callback context.
 * @param[in] irq_line Physical IRQ line reported by IRQ Manager.
 * @param[in] route_events Normalized route events associated with the binding.
 *
 * @note This callback executes in interrupt context and remains bounded: it snapshots CRC IRQ facts,
 *       updates fixed counters/last-event state and clears only observed Service-owned sources. It
 *       never allocates memory, advances a PC Case or decides PASS/FAIL.
 */
static void crc_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_crc_service_t *service = (et_crc_service_t *)context;
    et_crc_wrap_irq_snapshot_t snapshot;
    uint32_t event_bits;

    (void)irq_line;
    (void)route_events;

    /* Phase 1: Ignore stale callback entry and snapshot current normalized CRC hardware facts. */
    if ((service == NULL) || (service->irq_bound == 0u))
    {
        return;
    }

    if (et_crc_wrap_irq_snapshot_get(service->crc_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        return;
    }

    /* Phase 2: Publish bounded raw/effective evidence and saturating callback count. */
    event_bits = snapshot.status & service->irq_enabled_sources;
    service->irq_last_raw = snapshot.raw;
    service->irq_last_event = event_bits;

    if (service->irq_event_count != UINT32_MAX)
    {
        ++service->irq_event_count;
    }

    /* Phase 3: Acknowledge only events observed and owned by this Service instance. */
    if (event_bits != 0u)
    {
        (void)et_crc_wrap_irq_clear(service->crc_id, event_bits);
    }
}

/**
 * @brief Release the CRC Service's dynamic IRQ Manager binding when one is active.
 *
 * @param[in,out] service CRC Service instance that owns the callback binding.
 *
 * @note Callers disable CRC interrupt sources before unbinding so no enabled source is left without a
 *       callback. The local irq_bound flag is cleared only after IRQ Manager confirms release.
 *
 * @return 0 when no binding exists or the binding is released successfully.
 * @return -1 when the active binding cannot be released.
 */
static int crc_irq_unbind(et_crc_service_t *service)
{
    if ((service == NULL) || (service->irq_bound == 0u))
    {
        return 0;
    }

    if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line, crc_irq_callback,
                              service) != 0)
    {
        return -1;
    }

    service->irq_bound = 0u;

    return 0;
}

/**
 * @brief Disable every Service-owned CRC interrupt source and release the callback route.
 *
 * @param[in,out] service CRC Service instance whose IRQ session is being shut down.
 *
 * @note Cleanup order is hardware source first, IRQ Manager binding second. A failed hardware disable
 *       preserves ownership state so cleanup is not falsely reported as complete.
 *
 * @return 0 when all owned sources are disabled and any binding is released.
 * @return -1 when service is invalid or cleanup cannot complete.
 */
static int crc_irq_shutdown(et_crc_service_t *service)
{
    if (service == NULL)
    {
        return -1;
    }

    if (service->irq_enabled_sources != 0u)
    {
        if (et_crc_wrap_irq_disable(service->crc_id, service->irq_enabled_sources) !=
            ET_WRAP_STATUS_OK)
        {
            return -1;
        }

        service->irq_enabled_sources = 0u;
    }

    return crc_irq_unbind(service);
}

/**
 * @brief Start or extend a deterministic managed CRC IRQ session for selected sources.
 *
 * @param[in,out] service CRC Service instance that owns IRQ evidence and callback state.
 * @param[in] source_bits Valid nonempty normalized CRC interrupt-source mask.
 *
 * @note Stale hardware state is disabled/cleared before route binding. Callback ownership is
 *       published before a level-sensitive source is enabled; newly created bindings are rolled back
 *       if hardware source enable fails.
 *
 * @return ET_STATUS_OK when selected sources are enabled under managed ownership.
 * @return ET_STATUS_INTERNAL_ERROR when hardware cleanup/binding/enable fails.
 */
static uint16_t handle_irq_enable(et_crc_service_t *service, uint32_t source_bits)
{
    uint8_t newly_bound = 0u;

    /* Phase 1: Quiesce and clear stale state for exactly the requested CRC sources. */
    if (et_crc_wrap_irq_disable(service->crc_id, source_bits) != ET_WRAP_STATUS_OK ||
        et_crc_wrap_irq_clear(service->crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 2: Acquire the physical/logical route before any source can interrupt. */
    if (service->irq_bound == 0u)
    {
        if ((et_crc_wrap_get_irq_route(service->crc_id, &service->irq_route) !=
             ET_WRAP_STATUS_OK) ||
            (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                                 crc_irq_callback, service) != 0))
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        service->irq_bound = 1u;
        newly_bound = 1u;
    }

    /* Phase 3: Publish source ownership before level-sensitive hardware enable, then rollback on fail. */
    service->irq_enabled_sources |= source_bits;

    if (et_crc_wrap_irq_enable(service->crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        service->irq_enabled_sources &= ~source_bits;

        if (newly_bound != 0u)
        {
            (void)crc_irq_unbind(service);
        }

        return ET_STATUS_INTERNAL_ERROR;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Disable selected managed CRC IRQ sources and release the route when no sources remain.
 *
 * @param[in,out] service CRC Service instance that owns the IRQ session.
 * @param[in] source_bits Valid normalized CRC interrupt-source mask to disable.
 *
 * @note Source ownership bits are removed only after hardware disable succeeds. The IRQ route remains
 *       bound while any other Service-owned CRC source is still enabled.
 *
 * @return ET_STATUS_OK when selected sources are disabled and required unbind succeeds.
 * @return ET_STATUS_INTERNAL_ERROR when hardware disable or final route release fails.
 */
static uint16_t handle_irq_disable(et_crc_service_t *service, uint32_t source_bits)
{
    if (et_crc_wrap_irq_disable(service->crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_enabled_sources &= ~source_bits;

    if ((service->irq_enabled_sources == 0u) && (crc_irq_unbind(service) != 0))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Execute one bounded CRC calculation command and return result plus remaining input count.
 *
 * @param[in] service Configured CRC Service instance.
 * @param[in] request_body Fixed CALCULATE request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note The 64-bit Wire address must round-trip through target uintptr_t before CRC Wrap can access it.
 *       Firmware returns hardware facts only; expected CRC comparison remains PC-side.
 *
 * @return Stable ET status for lifecycle/payload validation or CRC Wrap execution.
 */
static uint16_t handle_calculate(et_crc_service_t *service, const uint8_t *request_body,
                                 uint16_t request_length, uint8_t *response_body,
                                 uint16_t response_capacity, uint16_t *response_length)
{
    uintptr_t source_address;
    uint64_t source_wire;
    uint32_t result;
    uint32_t remaining;
    et_wrap_status_t status;

    /* Phase 1: Validate lifecycle, fixed Wire shape and response capacity. */
    if ((state_is_configured(service) == 0u) || (request_body == NULL) ||
        (request_length != ET_CRC_SERVICE_CALCULATE_REQUEST_SIZE) ||
        (response_capacity < ET_CRC_SERVICE_CALCULATE_RESPONSE_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    source_wire = read_u64(&request_body[ET_CRC_SERVICE_CALCULATE_SOURCE_OFFSET]);
    source_address = (uintptr_t)source_wire;

    if ((uint64_t)source_address != source_wire)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute one bounded CRC hardware calculation using the active public mode. */
    status = et_crc_wrap_calculate(service->crc_id, service->mode, source_address,
                                   read_u32(&request_body[ET_CRC_SERVICE_CALCULATE_LENGTH_OFFSET]),
                                   ET_CRC_SERVICE_CALCULATE_TIMEOUT_BUDGET, &result);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    status = et_crc_wrap_data_length_get(service->crc_id, &remaining);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Encode only observed hardware result and remaining-input facts. */
    write_u32(&response_body[ET_CRC_SERVICE_CALCULATE_RESULT_OFFSET], result);
    write_u32(&response_body[ET_CRC_SERVICE_CALCULATE_REMAINING_OFFSET], remaining);
    *response_length = ET_CRC_SERVICE_CALCULATE_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Execute one target-local timed CRC32 validation operation and return raw timing facts.
 *
 * @param[in] service Configured CRC Service instance in CRC32 mode.
 * @param[in] request_body Fixed timed-calculation request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Timing comes from the CRC Test Driver boundary, not host time. Firmware returns result/cycles/
 *       measured bytes only and never evaluates a performance threshold.
 *
 * @return Stable ET status for lifecycle/Wire validation or timed CRC Wrap execution.
 */
static uint16_t handle_calculate_timed(et_crc_service_t *service, const uint8_t *request_body,
                                       uint16_t request_length, uint8_t *response_body,
                                       uint16_t response_capacity, uint16_t *response_length)
{
    uintptr_t source_address;
    uint64_t source_wire;
    uint32_t length_bytes;
    uint32_t result;
    uint32_t elapsed_cycles;
    et_wrap_status_t status;

    /* Phase 1: Require configured CRC32 state and a canonical reserved-zero Wire envelope. */
    if ((state_is_configured(service) == 0u) || (service->mode != ET_CRC_WRAP_MODE_CRC32) ||
        (request_length != ET_CRC_SERVICE_TIMED_REQUEST_SIZE) ||
        (response_capacity < ET_CRC_SERVICE_TIMED_RESPONSE_SIZE) ||
        (read_u32(&request_body[ET_CRC_SERVICE_TIMED_REQUEST_RESERVED_OFFSET]) != 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    source_wire = read_u64(&request_body[ET_CRC_SERVICE_TIMED_SOURCE_OFFSET]);
    source_address = (uintptr_t)source_wire;

    if ((uint64_t)source_address != source_wire)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute the target-local timed Driver path through CRC Wrap. */
    length_bytes = read_u32(&request_body[ET_CRC_SERVICE_TIMED_LENGTH_OFFSET]);
    status = et_crc_wrap_test_calculate_timed(service->crc_id, source_address, length_bytes,
                                              ET_CRC_SERVICE_CALCULATE_TIMEOUT_BUDGET, &result,
                                              &elapsed_cycles);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Return raw result/timing facts with the reserved response word deterministically zero. */
    write_u32(&response_body[ET_CRC_SERVICE_TIMED_RESULT_OFFSET], result);
    write_u32(&response_body[ET_CRC_SERVICE_TIMED_CYCLES_OFFSET], elapsed_cycles);
    write_u32(&response_body[ET_CRC_SERVICE_TIMED_VALUE_OFFSET], length_bytes);
    write_u32(&response_body[ET_CRC_SERVICE_TIMED_RESERVED_OFFSET], 0u);
    *response_length = ET_CRC_SERVICE_TIMED_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Dispatch CRC capability, lifecycle and configuration commands.
 *
 * @param[in,out] service CRC Service instance whose lifecycle may change.
 * @param[in] command_id Stable CRC command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note ENABLE/DISABLE/CONFIGURE are the only branches here that mutate CRC lifecycle/hardware.
 *       DISABLE first shuts down managed IRQ ownership so hardware cannot remain enabled without callback.
 *
 * @return Stable ET status for handled core command, or ET_STATUS_INVALID_COMMAND for another category.
 */
static uint16_t handle_core_commands(et_crc_service_t *service, uint16_t command_id,
                                     const uint8_t *request_body, uint16_t request_length,
                                     uint8_t *response_body, uint16_t response_capacity,
                                     uint16_t *response_length)
{
    et_crc_wrap_config_t config;
    et_wrap_status_t status;
    uint8_t fifo_threshold_max;

    /* Phase 1: Handle read-only capabilities before lifecycle-changing commands. */
    switch (command_id)
    {
        case ET_CRC_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_CRC_SERVICE_CAPABILITIES_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_get_fifo_threshold_max(service->crc_id, &fifo_threshold_max);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u16(&response_body[ET_CRC_SERVICE_CAP_API_VERSION_OFFSET],
                      ET_CRC_SERVICE_API_VERSION);
            write_u16(&response_body[ET_CRC_SERVICE_CAP_STRUCT_SIZE_OFFSET],
                      ET_CRC_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_CRC_SERVICE_CAP_FEATURES_OFFSET],
                      ET_CRC_SERVICE_IMPLEMENTED_FEATURES);
            response_body[ET_CRC_SERVICE_CAP_MODE_MASK_OFFSET] = ET_CRC_SERVICE_MODE_BITS;
            response_body[ET_CRC_SERVICE_CAP_IRQ_MASK_OFFSET] = ET_CRC_SERVICE_IRQ_BITS;
            response_body[ET_CRC_SERVICE_CAP_FIFO_THRESHOLD_OFFSET] = fifo_threshold_max;
            response_body[ET_CRC_SERVICE_CAP_FLAGS_OFFSET] =
                ET_CRC_SERVICE_CAPABILITY_FLAG_BOUNDED_SYNC;
            write_u32(&response_body[ET_CRC_SERVICE_CAP_MAX_CALCULATE_OFFSET],
                      ET_CRC_WRAP_MAX_CALCULATE_BYTES);
            *response_length = ET_CRC_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CRC_COMMAND_ENABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_enable(service->crc_id);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->enabled = 1u;
                service->configured = 0u;
            }

            return status_from_wrap(status);
        }

        /* Phase 2: Shutdown managed IRQ ownership before disabling CRC hardware. */
        case ET_CRC_COMMAND_DISABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (crc_irq_shutdown(service) != 0)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            status = et_crc_wrap_disable(service->crc_id);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->enabled = 0u;
                service->configured = 0u;
            }

            return status_from_wrap(status);
        }

        /* Phase 3: Apply one complete configuration only while the CRC module is enabled. */
        case ET_CRC_COMMAND_CONFIGURE:
        {
            if ((service->enabled == 0u) ||
                (decode_config(service, request_body, request_length, &config) != 0))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_configure(service->crc_id, &config);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->mode = config.mode;
                service->configured = 1u;
            }

            return status_from_wrap(status);
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch CRC calculation, length, result, check-value and FIFO-status commands.
 *
 * @param[in,out] service Configured CRC Service instance.
 * @param[in] command_id Stable CRC command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note These branches expose atomic CRC hardware actions/facts only. They do not sequence multi-step
 *       tests or compare results against a golden value.
 *
 * @return Stable ET status for handled data command, or ET_STATUS_INVALID_COMMAND for another category.
 */
static uint16_t handle_data_commands(et_crc_service_t *service, uint16_t command_id,
                                     const uint8_t *request_body, uint16_t request_length,
                                     uint8_t *response_body, uint16_t response_capacity,
                                     uint16_t *response_length)
{
    et_wrap_status_t status;
    uint32_t value;
    uint32_t result;
    uint32_t remaining;
    uint8_t overflow;

    /* Phase 1: Route calculations and hardware-length programming through atomic Wrap operations. */
    switch (command_id)
    {
        case ET_CRC_COMMAND_CALCULATE:
        {
            return handle_calculate(service, request_body, request_length, response_body,
                                    response_capacity, response_length);
        }

        case ET_CRC_COMMAND_DATA_LENGTH_SET:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_CRC_SERVICE_U32_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_crc_wrap_data_length_set(service->crc_id, service->mode,
                                                                read_u32(request_body)));
        }

        /* Phase 2: Return current hardware length/result observations without changing them. */
        case ET_CRC_COMMAND_DATA_LENGTH_GET:
        {
            if ((state_is_configured(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CRC_SERVICE_U32_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_data_length_get(service->crc_id, &remaining);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(response_body, remaining);
            *response_length = ET_CRC_SERVICE_U32_BODY_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CRC_COMMAND_RESULT_GET:
        {
            if ((state_is_configured(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CRC_SERVICE_U32_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_result_get(service->crc_id, &result);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(response_body, result);
            *response_length = ET_CRC_SERVICE_U32_BODY_SIZE;

            return ET_STATUS_OK;
        }

        /* Phase 3: Validate width-sensitive check values and return FIFO status as raw facts. */
        case ET_CRC_COMMAND_CHECK_VALUE_SET:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_CRC_SERVICE_U32_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            value = read_u32(request_body);

            if ((value & ~mode_value_mask(service->mode)) != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_crc_wrap_check_value_set(service->crc_id, service->mode, value));
        }

        case ET_CRC_COMMAND_FIFO_STATUS_GET:
        {
            if ((state_is_configured(service) == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CRC_SERVICE_U32_BODY_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_fifo_status_get(service->crc_id, &overflow);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            (void)memset(response_body, 0, ET_CRC_SERVICE_SOURCE_REQUEST_SIZE);
            response_body[ET_CRC_SERVICE_FIFO_OVERFLOW_OFFSET] = overflow;
            *response_length = ET_CRC_SERVICE_U32_BODY_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch managed CRC IRQ ownership, source-control and evidence commands.
 *
 * @param[in,out] service CRC Service instance owning IRQ route/evidence state.
 * @param[in] command_id Stable CRC IRQ command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Source enable/disable uses IRQ Manager ownership helpers; mask/unmask/force/clear remain atomic
 *       CRC Wrap actions. Snapshot copies callback-owned evidence under one critical section.
 *
 * @return Stable ET status for handled IRQ command, or ET_STATUS_INVALID_COMMAND for another category.
 */
static uint16_t handle_irq_commands(et_crc_service_t *service, uint16_t command_id,
                                    const uint8_t *request_body, uint16_t request_length,
                                    uint8_t *response_body, uint16_t response_capacity,
                                    uint16_t *response_length)
{
    et_crc_wrap_irq_snapshot_t irq_snapshot;
    et_wrap_status_t status;
    uint32_t source_bits;
    uint32_t irq_key;
    uint32_t event_count;
    uint32_t last_event;
    uint32_t last_raw;

    /* Phase 1: Handle source-control commands after configured-state and mask validation. */
    switch (command_id)
    {
        case ET_CRC_COMMAND_IRQ_ENABLE:
        case ET_CRC_COMMAND_IRQ_DISABLE:
        case ET_CRC_COMMAND_IRQ_MASK:
        case ET_CRC_COMMAND_IRQ_UNMASK:
        case ET_CRC_COMMAND_IRQ_FORCE:
        {
            if ((state_is_configured(service) == 0u) ||
                (decode_source_bits(request_body, request_length, &source_bits) != 0))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_CRC_COMMAND_IRQ_ENABLE)
            {
                return handle_irq_enable(service, source_bits);
            }

            if (command_id == ET_CRC_COMMAND_IRQ_DISABLE)
            {
                return handle_irq_disable(service, source_bits);
            }

            if (command_id == ET_CRC_COMMAND_IRQ_MASK)
            {
                status = et_crc_wrap_irq_mask(service->crc_id, source_bits);
            }
            else if (command_id == ET_CRC_COMMAND_IRQ_UNMASK)
            {
                status = et_crc_wrap_irq_unmask(service->crc_id, source_bits);
            }
            else
            {
                status = et_crc_wrap_irq_force(service->crc_id, source_bits);
            }

            return status_from_wrap(status);
        }

        /* Phase 2: Permit explicit source clear as cleanup even outside configured command flows. */
        case ET_CRC_COMMAND_IRQ_CLEAR:
        {
            if (decode_source_bits(request_body, request_length, &source_bits) != 0)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_crc_wrap_irq_clear(service->crc_id, source_bits));
        }

        /* Phase 3: Return one coherent hardware plus callback-owned IRQ evidence snapshot. */
        case ET_CRC_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_CRC_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_crc_wrap_irq_snapshot_get(service->crc_id, &irq_snapshot);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            /* Protect the three callback-owned values as one coherent snapshot. */
            irq_key = et_irq_manager_enter_critical();
            event_count = service->irq_event_count;
            last_event = service->irq_last_event;
            last_raw = service->irq_last_raw;
            et_irq_manager_exit_critical(irq_key);
            write_u32(&response_body[ET_CRC_SERVICE_IRQ_RAW_OFFSET], irq_snapshot.raw);
            write_u32(&response_body[ET_CRC_SERVICE_IRQ_STATUS_OFFSET], irq_snapshot.status);
            write_u32(&response_body[ET_CRC_SERVICE_IRQ_EVENT_COUNT_OFFSET], event_count);
            write_u32(&response_body[ET_CRC_SERVICE_IRQ_LAST_EVENT_OFFSET], last_event);
            write_u32(&response_body[ET_CRC_SERVICE_IRQ_LAST_RAW_OFFSET], last_raw);
            *response_length = ET_CRC_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch validation-only CRC input/burst/timing commands.
 *
 * @param[in,out] service Configured CRC Service instance.
 * @param[in] command_id Stable CRC validation command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note These commands expose hardware-validation observations through isolated Test Driver
 *       Extensions only. Firmware still returns raw facts and never converts timing/result data into verdicts.
 *
 * @return Stable ET status for handled validation command, or ET_STATUS_INVALID_COMMAND otherwise.
 */
static uint16_t handle_test_commands(et_crc_service_t *service, uint16_t command_id,
                                     const uint8_t *request_body, uint16_t request_length,
                                     uint8_t *response_body, uint16_t response_capacity,
                                     uint16_t *response_length)
{
    et_wrap_status_t status;
    uint32_t burst_values[ET_CRC_SERVICE_TEST_BURST_MAX_ITEMS];
    uint32_t checkpoint_result;
    uint32_t final_result;
    uint32_t burst_overflow;
    uint32_t index;
    uint8_t burst_count;
    uint8_t burst_checkpoint_count;

    /* Phase 1: Handle one explicit-width input write or delegate target-local timed calculation. */
    switch (command_id)
    {
        case ET_CRC_COMMAND_TEST_INPUT_WRITE:
        {
            if ((state_is_configured(service) == 0u) ||
                (request_length != ET_CRC_SERVICE_TEST_INPUT_REQUEST_SIZE) ||
                (bytes_are_zero(&request_body[ET_CRC_SERVICE_TEST_INPUT_RESERVED_OFFSET],
                                ET_CRC_SERVICE_TEST_INPUT_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_crc_wrap_test_input_write(
                service->crc_id, request_body[ET_CRC_SERVICE_TEST_INPUT_WIDTH_OFFSET],
                read_u32(&request_body[ET_CRC_SERVICE_TEST_INPUT_VALUE_OFFSET])));
        }

        case ET_CRC_COMMAND_TEST_CALCULATE_TIMED:
        {
            return handle_calculate_timed(service, request_body, request_length, response_body,
                                          response_capacity, response_length);
        }

        /* Phase 2: Preserve/validate the complete burst request before the shared buffer becomes response. */
        case ET_CRC_COMMAND_TEST_INPUT_BURST_32:
        {
            if ((state_is_configured(service) == 0u) || (service->mode != ET_CRC_WRAP_MODE_CRC32) ||
                (request_length != ET_CRC_SERVICE_TEST_BURST_REQUEST_SIZE) ||
                (response_capacity < ET_CRC_SERVICE_TEST_BURST_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            /*
             * The Router may reuse one buffer for request and response bodies.
             * Preserve echoed request fields before clearing the response body.
             */
            burst_count = request_body[ET_CRC_SERVICE_BURST_COUNT_REQUEST_OFFSET];
            burst_checkpoint_count = request_body[ET_CRC_SERVICE_BURST_CHECKPOINT_REQUEST_OFFSET];

            if ((burst_count == 0u) || (burst_count > ET_CRC_SERVICE_TEST_BURST_MAX_ITEMS) ||
                (burst_checkpoint_count > burst_count) ||
                (bytes_are_zero(&request_body[ET_CRC_SERVICE_BURST_RESERVED_OFFSET],
                                ET_CRC_SERVICE_BURST_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (index = 0u; index < ET_CRC_SERVICE_TEST_BURST_MAX_ITEMS; index++)
            {
                burst_values[index] =
                    read_u32(&request_body[ET_CRC_SERVICE_TEST_BURST_VALUES_OFFSET +
                                           ET_CRC_SERVICE_WORD_OFFSET(index)]);

                if ((index >= burst_count) && (burst_values[index] != 0u))
                {
                    return ET_STATUS_INVALID_PARAM;
                }
            }

            /* Phase 3: Execute one target-local burst and encode only returned hardware observations. */
            status = et_crc_wrap_test_input_burst_32(service->crc_id, burst_values, burst_count,
                                                     burst_checkpoint_count, &checkpoint_result,
                                                     &final_result, &burst_overflow);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            (void)memset(response_body, 0, ET_CRC_SERVICE_TEST_BURST_RESPONSE_SIZE);
            response_body[ET_CRC_SERVICE_BURST_COUNT_RESPONSE_OFFSET] = burst_count;
            response_body[ET_CRC_SERVICE_BURST_CHECKPOINT_RESPONSE_OFFSET] = burst_checkpoint_count;
            write_u32(&response_body[ET_CRC_SERVICE_BURST_CHECKPOINT_OFFSET], checkpoint_result);
            write_u32(&response_body[ET_CRC_SERVICE_BURST_FINAL_OFFSET], final_result);
            response_body[ET_CRC_SERVICE_BURST_OVERFLOW_OFFSET] = (uint8_t)burst_overflow;
            *response_length = ET_CRC_SERVICE_TEST_BURST_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Validate the common CRC request envelope and route one command category.
 *
 * @param[in,out] context CRC Service instance retained by the common Service Router.
 * @param[in] command_id Stable CRC command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Category handlers return INVALID_COMMAND only to allow the next category to inspect the same
 *       stable command ID. The first handled result is returned unchanged; no cross-IP action occurs.
 *
 * @return Stable ET status from the matching CRC command category.
 */
static uint16_t crc_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    et_crc_service_t *service = (et_crc_service_t *)context;
    uint16_t status;

    /* Phase 1: Validate the router envelope before any command-specific parsing. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *response_length = 0u;

    /* Phase 2: Try lifecycle/core and data command categories in fixed ownership order. */
    status = handle_core_commands(service, command_id, request_body, request_length, response_body,
                                  response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    status = handle_data_commands(service, command_id, request_body, request_length, response_body,
                                  response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    /* Phase 3: Route IRQ and validation-only commands after normal CRC operations. */
    status = handle_irq_commands(service, command_id, request_body, request_length, response_body,
                                 response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    return handle_test_commands(service, command_id, request_body, request_length, response_body,
                                response_capacity, response_length);
}

/**
 * @brief Initialize one CRC Service instance and its bounded software-owned IRQ state.
 *
 * @param[out] service CRC Service storage owned by the Application manifest.
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in,out] irq_manager Common IRQ Manager used by managed CRC interrupt commands.
 * @param[in] irq_priority Board-selected default priority for the CRC route.
 *
 * @note Initialization clears Service state and binds the descriptor only. CRC hardware remains
 *       untouched until a later command explicitly enables/configures it.
 *
 * @return 0 when Service state/descriptor are initialized.
 * @return -1 when service or irq_manager is NULL.
 */
int et_crc_service_init(et_crc_service_t *service, et_crc_id_t crc_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->crc_id = crc_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_CRC_SERVICE_ID;
    service->descriptor.instance_id = crc_id;
    service->descriptor.context = service;
    service->descriptor.handle = crc_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the CRC descriptor registered by the Application Service aggregator.
 *
 * @param[in] service Initialized CRC Service instance.
 *
 * @note The returned pointer aliases Service-owned storage and does not access CRC hardware.
 *
 * @return Pointer to the immutable descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_crc_service_descriptor(const et_crc_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Adapt the generic Service-factory contract to the existing CRC Service initializer.
 *
 * @param[out] storage Caller-owned storage for one CRC Service instance.
 * @param[in] instance_id Stable logical CRC instance identifier supplied by the manifest.
 * @param[in] context Common factory dependencies including IRQ Manager and board priority.
 * @param[out] descriptor Initialized CRC descriptor returned to the common registrar.
 *
 * @note This thin factory performs no Feature action or hardware configuration; it only forwards
 *       generic manifest facts into et_crc_service_init() and exposes the resulting descriptor.
 *
 * @return 0 when one CRC Service descriptor is created successfully.
 * @return -1 when dependencies are invalid or initialization/descriptor retrieval fails.
 */
int et_crc_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_crc_service_t *service = (et_crc_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_crc_service_init(service, (et_crc_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_crc_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
