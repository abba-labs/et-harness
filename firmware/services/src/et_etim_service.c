/** @file et_etim_service.c @brief Decode ETIM basic operations without test policy or IRQ delivery. */
#include "et_etim_service.h"
#include <stddef.h>
#include <string.h>

/**
 * @brief Decode one little-endian word without aligned memory access.
 * @param[in] data Four readable bytes.
 * @note Pure Wire conversion; no hardware side effects.
 * @return Unsigned word value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Decode one full-width little-endian period.
 * @param[in] data Eight readable bytes.
 * @note No native structure casts or hardware access.
 * @return Unsigned 64-bit value.
 */
static uint64_t read_u64(const uint8_t *data)
{
    return (uint64_t)read_u32(data) | ((uint64_t)read_u32(data + ET_ETIM_SERVICE_WORD_SIZE) << 32u);
}

/**
 * @brief Encode one little-endian word.
 * @param[out] data Four writable bytes.
 * @param[in] value Word to encode.
 * @note Truncating casts select individual Wire bytes, not hardware fields.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Encode one little-endian halfword.
 * @param[out] data Two writable bytes.
 * @param[in] value Halfword to encode.
 * @note Pure Wire encoding, independent of host alignment.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one full-width little-endian period.
 * @param[out] data Eight writable bytes.
 * @param[in] value Value to encode.
 * @note This preserves periods beyond a 32-bit terminal-count encoding.
 */
static void write_u64(uint8_t *data, uint64_t value)
{
    write_u32(data, (uint32_t)value);
    write_u32(data + ET_ETIM_SERVICE_WORD_SIZE, (uint32_t)(value >> 32u));
}

/**
 * @brief Translate a Wrap result into the common protocol status.
 * @param[in] status Stable Wrap result.
 * @note Detailed errors remain in the ETIM body; timeout is not collapsed into IO error.
 * @return Common ET-Frame status.
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
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_BUSY:
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
 * @brief Encode an ETIM result prefix, preserving an optional data body.
 * @param[in] status Wrap result.
 * @param[out] body Response buffer with at least detail-size capacity.
 * @param[in,out] length Success data size, or zero for an acknowledgement.
 * @note On errors, this helper discards uninitialized success data, not count observations.
 * @return Common ET-Frame status.
 */
static uint16_t encode_result(et_wrap_status_t status, uint8_t *body, uint16_t *length)
{
    write_u32(body, (uint32_t)(int32_t)status);

    if (status != ET_WRAP_STATUS_OK || *length == 0u)
    {
        *length = ET_ETIM_SERVICE_DETAIL_SIZE;
    }

    return status_from_wrap(status);
}

/**
 * @brief Encode the per-channel capability response after successful lookup.
 * @param[out] body Full capability response buffer.
 * @param[in] caps Chip-neutral capability facts.
 * @note Offsets are the fixed ETIM body layout, not native struct layout.
 */
static void encode_capabilities(uint8_t *body, const et_etim_capabilities_t *caps)
{
    write_u16(&body[4], ET_ETIM_SERVICE_API_VERSION);
    write_u16(&body[6], ET_ETIM_SERVICE_CAPABILITIES_SIZE);
    write_u32(&body[8], caps->maximum_divider);
    write_u64(&body[12], caps->maximum_period_ticks);
    write_u32(&body[20], caps->maximum_count_polls);
    write_u32(&body[24], caps->irq_sources);
}

/**
 * @brief Execute a single bounded count pulse and preserve its observations.
 * @param[in] service Selected logical timer.
 * @param[in] command Latch or clear command.
 * @param[in] polls Explicit software sampling budget.
 * @param[out] body Buffer for detail and five observed words.
 * @param[out] length Actual encoded response size.
 * @note May issue one latch/clear pulse; never retries. Busy/timeout retain actual samples.
 * @return Common status with a distinguishable detailed Wrap result.
 */
static uint16_t handle_count_action(const et_etim_service_t *service, uint16_t command,
                                    uint32_t polls, uint8_t *body, uint16_t *length)
{
    et_etim_count_observation_t observed;
    et_wrap_status_t status;

    if (command == ET_ETIM_COMMAND_COUNT_LATCH)
    {
        status = et_etim_wrap_count_latch(service->etim_id, polls, &observed);
    }
    else
    {
        status = et_etim_wrap_count_clear(service->etim_id, polls, &observed);
    }

    write_u32(body, (uint32_t)(int32_t)status);
    *length = ET_ETIM_SERVICE_DETAIL_SIZE;

    if (status == ET_WRAP_STATUS_OK || status == ET_WRAP_STATUS_BUSY ||
        status == ET_WRAP_STATUS_TIMEOUT)
    {
        write_u32(&body[ET_ETIM_SERVICE_OBS_BEFORE_OFFSET], observed.before);
        write_u32(&body[ET_ETIM_SERVICE_OBS_PREVIOUS_OFFSET], observed.previous_latched);
        write_u32(&body[ET_ETIM_SERVICE_OBS_LATCHED_OFFSET], observed.latched);
        write_u32(&body[ET_ETIM_SERVICE_OBS_LIVE_OFFSET], observed.live);
        write_u32(&body[ET_ETIM_SERVICE_OBS_POLLS_OFFSET], observed.polls);
        *length = ET_ETIM_SERVICE_OBSERVATION_SIZE;
    }

    return status_from_wrap(status);
}

/**
 * @brief Validate and dispatch one bounded ETIM command.
 * @param[in,out] context Service-owned descriptor context.
 * @param[in] command_id Stable ETIM command selector.
 * @param[in] request_body Request bytes, nullable only for an empty request.
 * @param[in] request_length Exact request byte count.
 * @param[out] response_body Response storage.
 * @param[in] response_capacity Writable response byte count.
 * @param[out] response_length Encoded response byte count.
 * @note Main-loop context only; hardware actions stay in Own Wrap, with no NVIC or ISR binding.
 * @return Common ET-Frame status; body carries detailed Wrap outcomes.
 */
static uint16_t etim_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                            uint16_t request_length, uint8_t *response_body,
                            uint16_t response_capacity, uint16_t *response_length)
{
    et_etim_service_t *service = (et_etim_service_t *)context;
    et_wrap_status_t status;
    et_etim_timebase_t timebase;
    uint32_t value, latched;

    /* Phase 1: Reject unsafe buffers before decoding or touching the selected timer. */
    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (service == NULL || response_body == NULL ||
        response_capacity < ET_ETIM_SERVICE_DETAIL_SIZE ||
        (request_length != 0u && request_body == NULL))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Validate each fixed body, execute Own Wrap, then encode only real results. */
    switch (command_id)
    {
        case ET_ETIM_COMMAND_CAPABILITIES_GET:
        {
            et_etim_capabilities_t caps;

            if (request_length != 0u || response_capacity < ET_ETIM_SERVICE_CAPABILITIES_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_etim_wrap_capabilities_get(service->etim_id, &caps);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_capabilities(response_body, &caps);
                *response_length = ET_ETIM_SERVICE_CAPABILITIES_SIZE;
            }

            break;
        }

        case ET_ETIM_COMMAND_TIMEBASE_CONFIGURE:
        {
            if (request_length != ET_ETIM_SERVICE_TIMEBASE_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            timebase.divider = read_u32(request_body);
            timebase.period_ticks = read_u64(request_body + ET_ETIM_SERVICE_PERIOD_OFFSET);
            status = et_etim_wrap_timebase_configure(service->etim_id, &timebase);
            break;
        }

        case ET_ETIM_COMMAND_TIMEBASE_GET:
        {
            if (request_length != 0u || response_capacity < ET_ETIM_SERVICE_TIMEBASE_RESPONSE_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_etim_wrap_timebase_get(service->etim_id, &timebase);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_u32(response_body + ET_ETIM_SERVICE_DETAIL_SIZE, timebase.divider);
                write_u64(response_body + ET_ETIM_SERVICE_DETAIL_SIZE +
                              ET_ETIM_SERVICE_PERIOD_OFFSET,
                          timebase.period_ticks);
                *response_length = ET_ETIM_SERVICE_TIMEBASE_RESPONSE_SIZE;
            }

            break;
        }

        case ET_ETIM_COMMAND_ENABLE_SET:
        case ET_ETIM_COMMAND_ENABLE_GET:
        {
            uint16_t offset;

            if (request_length != ET_ETIM_SERVICE_ENABLE_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (offset = ET_ETIM_SERVICE_ENABLE_RESERVED_OFFSET;
                 offset < ET_ETIM_SERVICE_ENABLE_SIZE; ++offset)
            {
                if (request_body[offset] != 0u)
                {
                    return ET_STATUS_INVALID_PARAM;
                }
            }

            if (command_id == ET_ETIM_COMMAND_ENABLE_SET)
            {
                status =
                    et_etim_wrap_enable_set(service->etim_id, (et_etim_enable_t)request_body[0],
                                            request_body[ET_ETIM_SERVICE_ENABLE_VALUE_OFFSET]);
            }
            else
            {
                if (request_body[ET_ETIM_SERVICE_ENABLE_VALUE_OFFSET] != 0u ||
                    response_capacity < ET_ETIM_SERVICE_ENABLE_RESPONSE_SIZE)
                {
                    return ET_STATUS_INVALID_PARAM;
                }

                status = et_etim_wrap_enable_get(service->etim_id,
                                                 (et_etim_enable_t)request_body[0], &value);

                if (status == ET_WRAP_STATUS_OK)
                {
                    write_u32(response_body + ET_ETIM_SERVICE_DETAIL_SIZE, value);
                    *response_length = ET_ETIM_SERVICE_ENABLE_RESPONSE_SIZE;
                }
            }

            break;
        }

        case ET_ETIM_COMMAND_COUNT_GET:
        {
            if (request_length != 0u || response_capacity < ET_ETIM_SERVICE_COUNT_RESPONSE_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_etim_wrap_count_get(service->etim_id, &value, &latched);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_u32(&response_body[ET_ETIM_SERVICE_COUNT_LIVE_OFFSET], value);
                write_u32(&response_body[ET_ETIM_SERVICE_COUNT_LATCHED_OFFSET], latched);
                *response_length = ET_ETIM_SERVICE_COUNT_RESPONSE_SIZE;
            }

            break;
        }

        case ET_ETIM_COMMAND_COUNT_LATCH:
        case ET_ETIM_COMMAND_COUNT_CLEAR:
        {
            if (request_length != ET_ETIM_SERVICE_WORD_SIZE ||
                response_capacity < ET_ETIM_SERVICE_OBSERVATION_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return handle_count_action(service, command_id, read_u32(request_body), response_body,
                                       response_length);
        }

        case ET_ETIM_COMMAND_IRQ_CONFIGURE:
        {
            if (request_length != ET_ETIM_SERVICE_IRQ_CONFIG_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status =
                et_etim_wrap_irq_configure(service->etim_id, read_u32(request_body),
                                           read_u32(request_body + ET_ETIM_SERVICE_MASKED_OFFSET));
            break;
        }

        case ET_ETIM_COMMAND_IRQ_SNAPSHOT_GET:
        {
            et_etim_irq_snapshot_t snapshot;

            if (request_length != 0u || response_capacity < ET_ETIM_SERVICE_IRQ_SNAPSHOT_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_etim_wrap_irq_snapshot_get(service->etim_id, &snapshot);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_u32(&response_body[ET_ETIM_SERVICE_IRQ_ENABLED_OFFSET], snapshot.enabled);
                write_u32(&response_body[ET_ETIM_SERVICE_IRQ_MASKED_OFFSET], snapshot.masked);
                write_u32(&response_body[ET_ETIM_SERVICE_IRQ_RAW_OFFSET], snapshot.raw);
                write_u32(&response_body[ET_ETIM_SERVICE_IRQ_STATUS_OFFSET], snapshot.status);
                *response_length = ET_ETIM_SERVICE_IRQ_SNAPSHOT_SIZE;
            }

            break;
        }

        case ET_ETIM_COMMAND_IRQ_FORCE:
        case ET_ETIM_COMMAND_IRQ_CLEAR:
        {
            if (request_length != ET_ETIM_SERVICE_WORD_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            value = read_u32(request_body);

            if (command_id == ET_ETIM_COMMAND_IRQ_FORCE)
            {
                status = et_etim_wrap_irq_force(service->etim_id, value);
            }
            else
            {
                status = et_etim_wrap_irq_clear(service->etim_id, value);
            }

            break;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }

    return encode_result(status, response_body, response_length);
}

/**
 * @brief Initialize a stateless logical-channel service without hardware access.
 * @param[out] service Caller-owned storage.
 * @param[in] etim_id Explicit logical channel identifier.
 * @param[in] irq_manager Common factory dependency, validated but not retained.
 * @note Basic commands do not create IRQ sessions; no binding, reset or default configuration occurs.
 * @return Zero on success, minus one for a null dependency.
 */
int et_etim_service_init(et_etim_service_t *service, et_etim_id_t etim_id,
                         et_irq_manager_t *irq_manager)
{
    if (service == NULL || irq_manager == NULL)
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->etim_id = etim_id;
    service->descriptor.service_id = ET_ETIM_SERVICE_ID;
    service->descriptor.instance_id = etim_id;
    service->descriptor.context = service;
    service->descriptor.handle = etim_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the descriptor stored inside an initialized ETIM service.
 * @param[in] service Initialized service or NULL.
 * @note The returned pointer aliases caller-owned storage; no allocation occurs.
 * @return Descriptor or NULL.
 */
const et_service_descriptor_t *et_etim_service_descriptor(const et_etim_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Create one ETIM service through the standard static factory.
 * @param[out] storage Caller-owned service storage.
 * @param[in] instance_id Explicit logical channel.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Initialized descriptor.
 * @note Initialization has no timer or interrupt side effects.
 * @return Zero on success, minus one on invalid dependencies.
 */
int et_etim_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_etim_service_t *service = (et_etim_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_etim_service_init(service, (et_etim_id_t)instance_id, context->irq_manager) != 0)
    {
        return -1;
    }

    *descriptor = et_etim_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
