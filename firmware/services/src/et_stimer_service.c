/**
 * @file et_stimer_service.c
 * @brief Decode STIMER commands and return raw timer observations.
 */

#include "et_stimer_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Read one little-endian 16-bit Wire value.
 * @param[in] data Two readable Wire bytes.
 * @note This codec helper has no hardware side effect.
 * @return Decoded unsigned value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)(((uint16_t)data[0]) | ((uint16_t)data[1] << 8u));
}

/**
 * @brief Read one little-endian 32-bit Wire value.
 * @param[in] data Four readable Wire bytes.
 * @note This codec helper has no hardware side effect.
 * @return Decoded unsigned value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return ((uint32_t)data[0]) | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Write one little-endian 16-bit Wire value.
 * @param[out] data Two writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This codec helper has no hardware side effect.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Write one little-endian 32-bit Wire value.
 * @param[out] data Four writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This codec helper has no hardware side effect.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
    data[2] = (uint8_t)((value >> 16u) & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
    data[3] = (uint8_t)((value >> 24u) & ET_STIMER_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Translate one stable Wrap status into ET-Frame status.
 * @param[in] status Wrap operation result.
 * @note This helper does not retry or reinterpret hardware behavior.
 * @return Stable ET protocol status.
 */
static uint16_t status_from_wrap(et_wrap_status_t status)
{
    if (status == ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_OK;
    }

    if (status == ET_WRAP_STATUS_INVALID_ARGUMENT)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    if (status == ET_WRAP_STATUS_NOT_SUPPORTED)
    {
        return ET_STATUS_NOT_SUPPORTED;
    }

    if (status == ET_WRAP_STATUS_BUSY)
    {
        return ET_STATUS_BUSY;
    }

    return ET_STATUS_INTERNAL_ERROR;
}

/**
 * @brief Decode one complete STIMER configuration.
 * @param[in] service STIMER Service.
 * @param[in] body Wire body.
 * @param[in] length Body length.
 * @param[out] config Public Wrap configuration.
 * @note Stable syntax is decoded here; hardware limits remain owned by Wrap.
 * @return Zero on success, otherwise minus one.
 */
static int decode_config(const et_stimer_service_t *service, const uint8_t *body, uint16_t length,
                         et_stimer_wrap_config_t *config)
{
    uint16_t offset;

    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_STIMER_SERVICE_CONFIG_SIZE))
    {
        return -1;
    }

    for (offset = ET_STIMER_SERVICE_CONFIG_RESERVED_OFFSET;
         offset <
         (ET_STIMER_SERVICE_CONFIG_RESERVED_OFFSET + ET_STIMER_SERVICE_CONFIG_RESERVED_SIZE);
         ++offset)
    {
        if (body[offset] != 0u)
        {
            return -1;
        }
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_STIMER_WRAP_API_VERSION;
    config->stimer_id = service->stimer_id;
    config->period_ticks = read_u32(&body[ET_STIMER_SERVICE_CONFIG_PERIOD_OFFSET]);
    config->prescaler_divider = read_u16(&body[ET_STIMER_SERVICE_CONFIG_PRESCALER_OFFSET]);
    config->mode = body[ET_STIMER_SERVICE_CONFIG_MODE_OFFSET];
    config->load_mode = body[ET_STIMER_SERVICE_CONFIG_LOAD_MODE_OFFSET];

    return 0;
}

/**
 * @brief Decode one logical emergency route selector.
 * @param[in] body Fixed-size route request body.
 * @param[in] length Request body length.
 * @param[out] source_id Logical source identifier.
 * @param[out] trigger_group Logical emergency trigger group.
 * @note Reserved route bytes must be zero; this decoder has no hardware side effect.
 * @return Zero on success, otherwise minus one.
 */
static int decode_emergency_route(const uint8_t *body, uint16_t length, uint8_t *source_id,
                                  uint8_t *trigger_group)
{
    uint16_t offset;

    if ((body == NULL) || (source_id == NULL) || (trigger_group == NULL) ||
        (length != ET_STIMER_SERVICE_EMERGENCY_ROUTE_SIZE))
    {
        return -1;
    }

    for (offset = ET_STIMER_SERVICE_EMERGENCY_RESERVED_OFFSET;
         offset <
         (ET_STIMER_SERVICE_EMERGENCY_RESERVED_OFFSET + ET_STIMER_SERVICE_EMERGENCY_RESERVED_SIZE);
         ++offset)
    {
        if (body[offset] != 0u)
        {
            return -1;
        }
    }

    *source_id = body[ET_STIMER_SERVICE_EMERGENCY_SOURCE_OFFSET];
    *trigger_group = body[ET_STIMER_SERVICE_EMERGENCY_GROUP_OFFSET];

    return 0;
}

/**
 * @brief Record one real STIMER IRQ delivery and clear observed sources.
 * @param[in,out] context Service callback context.
 * @param[in] irq_line Physical IRQ line.
 * @param[in] route_events Stable route mask.
 * @note The callback is bounded and records facts only.
 */
static void stimer_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_stimer_service_t *service = (et_stimer_service_t *)context;
    et_stimer_wrap_irq_snapshot_t snapshot;
    uint32_t observed;

    if ((service == NULL) || (irq_line != service->irq_route.irq_line) ||
        ((route_events & ET_STIMER_WRAP_IRQ_ALL) == 0u) ||
        (et_stimer_wrap_irq_snapshot_get(service->stimer_id, &snapshot) != ET_WRAP_STATUS_OK))
    {
        return;
    }

    observed = snapshot.raw & service->irq_enabled_sources;

    if (observed != 0u)
    {
        service->irq_latched_sources |= observed;
        service->irq_last_raw = snapshot.raw;
        service->irq_last_event = observed;

        if (service->irq_event_count != UINT32_MAX)
        {
            service->irq_event_count++;
        }

        (void)et_stimer_wrap_irq_clear(service->stimer_id, observed);
    }
}

/**
 * @brief Bind the STIMER route and enable selected sources.
 * @param[in,out] service Configured STIMER Service.
 * @param[in] sources Stable source mask.
 * @note A failed source enable rolls back a newly created route binding.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_enable(et_stimer_service_t *service, uint32_t sources)
{
    uint8_t newly_bound = (uint8_t)(service->irq_bound == 0u);

    if ((service->irq_bound == 0u) &&
        ((et_stimer_wrap_get_irq_route(service->stimer_id, &service->irq_route) !=
          ET_WRAP_STATUS_OK) ||
         (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                              stimer_irq_callback, service) != 0)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_bound = 1u;

    if (et_stimer_wrap_irq_enable(service->stimer_id, sources) != ET_WRAP_STATUS_OK)
    {
        if (newly_bound != 0u)
        {
            (void)et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                        stimer_irq_callback, service);
            service->irq_bound = 0u;
        }

        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources |= sources;

    return ET_STATUS_OK;
}

/**
 * @brief Disable selected sources and release an unused route.
 * @param[in,out] service Configured STIMER Service.
 * @param[in] sources Stable source mask.
 * @note Existing hardware pending state remains available until IRQ_CLEAR.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_disable(et_stimer_service_t *service, uint32_t sources)
{
    if (et_stimer_wrap_irq_disable(service->stimer_id, sources) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources &= ~sources;

    if ((service->irq_bound != 0u) && (service->irq_enabled_sources == 0u))
    {
        if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                  stimer_irq_callback, service) != 0)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        service->irq_bound = 0u;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Dispatch one validated STIMER command.
 * @param[in,out] context Service context.
 * @param[in] command_id Stable command.
 * @param[in] request_body Request bytes.
 * @param[in] request_length Request length.
 * @param[out] response_body Response bytes.
 * @param[in] response_capacity Response capacity.
 * @param[out] response_length Produced length.
 * @note This Service contains no Case verdict and calls no other Feature IP.
 * @return Stable ET protocol status.
 */
static uint16_t stimer_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                              uint16_t request_length, uint8_t *response_body,
                              uint16_t response_capacity, uint16_t *response_length)
{
    et_stimer_service_t *service = (et_stimer_service_t *)context;
    et_stimer_wrap_capabilities_t capabilities;
    et_stimer_wrap_config_t config;
    et_stimer_wrap_irq_snapshot_t irq_snapshot;
    et_wrap_status_t wrap_status;
    uint32_t value;
    uint32_t irq_key;
    uint32_t event_count;
    uint32_t latched;
    uint32_t last_raw;
    uint32_t last_event;

    /* Phase 1: Validate the Router envelope before command-specific decoding. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *response_length = 0u;

    /* Phase 2: Execute one bounded STIMER-owned command. */
    switch (command_id)
    {
        case ET_STIMER_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_STIMER_SERVICE_CAPABILITIES_SIZE) ||
                (et_stimer_wrap_capabilities_get(service->stimer_id, &capabilities) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u16(&response_body[ET_STIMER_SERVICE_CAPS_API_VERSION_OFFSET],
                      ET_STIMER_SERVICE_API_VERSION);
            write_u16(&response_body[ET_STIMER_SERVICE_CAPS_STRUCT_SIZE_OFFSET],
                      ET_STIMER_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_STIMER_SERVICE_CAPS_FEATURES_OFFSET],
                      capabilities.features);
            write_u32(&response_body[ET_STIMER_SERVICE_CAPS_MAX_PERIOD_OFFSET],
                      capabilities.maximum_period_ticks);
            write_u16(&response_body[ET_STIMER_SERVICE_CAPS_MAX_PRESCALER_OFFSET],
                      capabilities.maximum_prescaler_divider);
            response_body[ET_STIMER_SERVICE_CAPS_COMPARE_CHANNELS_OFFSET] =
                capabilities.compare_channel_count;
            response_body[ET_STIMER_SERVICE_CAPS_INSTANCE_COUNT_OFFSET] =
                capabilities.instance_count;
            write_u32(&response_body[ET_STIMER_SERVICE_CAPS_IRQ_SOURCES_OFFSET],
                      capabilities.irq_sources);
            *response_length = ET_STIMER_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_STIMER_COMMAND_CONFIGURE:
        {
            if ((decode_config(service, request_body, request_length, &config) != 0) ||
                (et_stimer_wrap_configure(service->stimer_id, &config) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            service->configured = 1u;

            return ET_STATUS_OK;
        }

        case ET_STIMER_COMMAND_START:
        case ET_STIMER_COMMAND_STOP:
        case ET_STIMER_COMMAND_PAUSE:
        case ET_STIMER_COMMAND_RESUME:
        case ET_STIMER_COMMAND_CLEAR:
        case ET_STIMER_COMMAND_RELOAD:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_STIMER_COMMAND_START)
            {
                wrap_status = et_stimer_wrap_start(service->stimer_id);
            }
            else if (command_id == ET_STIMER_COMMAND_STOP)
            {
                wrap_status = et_stimer_wrap_stop(service->stimer_id);
            }
            else if (command_id == ET_STIMER_COMMAND_PAUSE)
            {
                wrap_status = et_stimer_wrap_pause(service->stimer_id);
            }
            else if (command_id == ET_STIMER_COMMAND_RESUME)
            {
                wrap_status = et_stimer_wrap_resume(service->stimer_id);
            }
            else if (command_id == ET_STIMER_COMMAND_CLEAR)
            {
                wrap_status = et_stimer_wrap_clear(service->stimer_id);
            }
            else
            {
                wrap_status = et_stimer_wrap_reload(service->stimer_id);
            }

            return status_from_wrap(wrap_status);
        }

        case ET_STIMER_COMMAND_LIVE_COUNT_GET:
        case ET_STIMER_COMMAND_LATCHED_COUNT_GET:
        case ET_STIMER_COMMAND_STATUS_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_STIMER_SERVICE_COUNT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_STIMER_COMMAND_LIVE_COUNT_GET)
            {
                wrap_status = et_stimer_wrap_live_count_get(service->stimer_id, &value);
            }
            else if (command_id == ET_STIMER_COMMAND_LATCHED_COUNT_GET)
            {
                wrap_status = et_stimer_wrap_latched_count_get(service->stimer_id, &value);
            }
            else
            {
                wrap_status = et_stimer_wrap_status_get(service->stimer_id, &value);
            }

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(response_body, value);
            *response_length = ET_STIMER_SERVICE_COUNT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_STIMER_COMMAND_COMPARE_SET:
        {
            uint16_t offset;

            if (request_length != ET_STIMER_SERVICE_COMPARE_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (offset = ET_STIMER_SERVICE_COMPARE_RESERVED_OFFSET;
                 offset < (ET_STIMER_SERVICE_COMPARE_RESERVED_OFFSET +
                           ET_STIMER_SERVICE_COMPARE_RESERVED_SIZE);
                 ++offset)
            {
                if (request_body[offset] != 0u)
                {
                    return ET_STATUS_INVALID_PARAM;
                }
            }

            return status_from_wrap(et_stimer_wrap_compare_set(
                service->stimer_id, request_body[ET_STIMER_SERVICE_COMPARE_CHANNEL_OFFSET],
                read_u32(&request_body[ET_STIMER_SERVICE_COMPARE_THRESHOLD_OFFSET])));
        }

        case ET_STIMER_COMMAND_EVENT_PULSE_WIDTH_SET:
        {
            uint16_t offset;

            if (request_length != ET_STIMER_SERVICE_EVENT_PULSE_WIDTH_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (offset = ET_STIMER_SERVICE_EVENT_PULSE_RESERVED_OFFSET;
                 offset < (ET_STIMER_SERVICE_EVENT_PULSE_RESERVED_OFFSET +
                           ET_STIMER_SERVICE_EVENT_PULSE_RESERVED_SIZE);
                 ++offset)
            {
                if (request_body[offset] != 0u)
                {
                    return ET_STATUS_INVALID_PARAM;
                }
            }

            return status_from_wrap(et_stimer_wrap_event_pulse_width_set(
                service->stimer_id,
                read_u32(&request_body[ET_STIMER_SERVICE_EVENT_PULSE_SOURCE_OFFSET]),
                read_u16(&request_body[ET_STIMER_SERVICE_EVENT_PULSE_WIDTH_OFFSET])));
        }

        case ET_STIMER_COMMAND_DMA_REQUEST_SELECT:
        {
            if (request_length != ET_STIMER_SERVICE_DMA_REQUEST_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_stimer_wrap_dma_request_select(service->stimer_id, read_u32(request_body)));
        }

        case ET_STIMER_COMMAND_DEBUG_HALT_POLICY_SET:
        {
            uint16_t offset;

            if (request_length != ET_STIMER_SERVICE_DEBUG_HALT_POLICY_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (offset = ET_STIMER_SERVICE_DEBUG_HALT_POLICY_RESERVED_OFFSET;
                 offset < (ET_STIMER_SERVICE_DEBUG_HALT_POLICY_RESERVED_OFFSET +
                           ET_STIMER_SERVICE_DEBUG_HALT_POLICY_RESERVED_SIZE);
                 ++offset)
            {
                if (request_body[offset] != 0u)
                {
                    return ET_STATUS_INVALID_PARAM;
                }
            }

            if (request_body[ET_STIMER_SERVICE_DEBUG_HALT_POLICY_OFFSET] >
                ET_STIMER_WRAP_DEBUG_HALT_RUN_FREE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_stimer_wrap_debug_halt_policy_set(
                service->stimer_id, request_body[ET_STIMER_SERVICE_DEBUG_HALT_POLICY_OFFSET]));
        }

        case ET_STIMER_COMMAND_EMERGENCY_CAPTURE_CONFIGURE:
        case ET_STIMER_COMMAND_EMERGENCY_CAPTURE_CLEAR:
        {
            uint8_t source_id;
            uint8_t trigger_group;

            if (decode_emergency_route(request_body, request_length, &source_id, &trigger_group) !=
                0)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_STIMER_COMMAND_EMERGENCY_CAPTURE_CONFIGURE)
            {
                wrap_status = et_stimer_wrap_emergency_capture_configure(service->stimer_id,
                                                                         source_id, trigger_group);
            }
            else
            {
                wrap_status = et_stimer_wrap_emergency_capture_clear(service->stimer_id, source_id,
                                                                     trigger_group);
            }

            return status_from_wrap(wrap_status);
        }

        case ET_STIMER_COMMAND_EMERGENCY_CAPTURE_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_STIMER_SERVICE_EMERGENCY_COUNT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_stimer_wrap_emergency_capture_get(service->stimer_id, &value);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(response_body, value);
            *response_length = ET_STIMER_SERVICE_EMERGENCY_COUNT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_STIMER_COMMAND_IRQ_ENABLE:
        case ET_STIMER_COMMAND_IRQ_DISABLE:
        case ET_STIMER_COMMAND_IRQ_MASK:
        case ET_STIMER_COMMAND_IRQ_UNMASK:
        case ET_STIMER_COMMAND_IRQ_FORCE:
        case ET_STIMER_COMMAND_IRQ_CLEAR:
        {
            if (request_length != ET_STIMER_SERVICE_MASK_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            value = read_u32(request_body);

            if (command_id == ET_STIMER_COMMAND_IRQ_ENABLE)
            {
                return handle_irq_enable(service, value);
            }

            if (command_id == ET_STIMER_COMMAND_IRQ_DISABLE)
            {
                return handle_irq_disable(service, value);
            }

            if (command_id == ET_STIMER_COMMAND_IRQ_MASK)
            {
                wrap_status = et_stimer_wrap_irq_mask(service->stimer_id, value);
            }
            else if (command_id == ET_STIMER_COMMAND_IRQ_UNMASK)
            {
                wrap_status = et_stimer_wrap_irq_unmask(service->stimer_id, value);
            }
            else if (command_id == ET_STIMER_COMMAND_IRQ_FORCE)
            {
                wrap_status = et_stimer_wrap_irq_force(service->stimer_id, value);
            }
            else
            {
                wrap_status = et_stimer_wrap_irq_clear(service->stimer_id, value);

                if (wrap_status == ET_WRAP_STATUS_OK)
                {
                    irq_key = et_irq_manager_enter_critical();
                    service->irq_latched_sources &= ~value;
                    et_irq_manager_exit_critical(irq_key);
                }
            }

            return status_from_wrap(wrap_status);
        }

        case ET_STIMER_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_STIMER_SERVICE_IRQ_SNAPSHOT_SIZE) ||
                (et_stimer_wrap_irq_snapshot_get(service->stimer_id, &irq_snapshot) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            irq_key = et_irq_manager_enter_critical();
            event_count = service->irq_event_count;
            latched = service->irq_latched_sources;
            last_raw = service->irq_last_raw;
            last_event = service->irq_last_event;
            et_irq_manager_exit_critical(irq_key);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_RAW_OFFSET], irq_snapshot.raw);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_STATUS_OFFSET], irq_snapshot.status);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_LATCHED_OFFSET], latched);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_EVENT_COUNT_OFFSET], event_count);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_LAST_RAW_OFFSET], last_raw);
            write_u32(&response_body[ET_STIMER_SERVICE_IRQ_LAST_EVENT_OFFSET], last_event);
            *response_length = ET_STIMER_SERVICE_IRQ_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one STIMER Service without touching hardware.
 * @param[out] service Application storage.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in,out] irq_manager Common IRQ Manager.
 * @param[in] irq_priority Board IRQ priority.
 * @note Initialization creates bounded state and one immutable descriptor only.
 * @return Zero on success, otherwise minus one.
 */
int et_stimer_service_init(et_stimer_service_t *service, et_stimer_id_t stimer_id,
                           et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->stimer_id = stimer_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_STIMER_SERVICE_ID;
    service->descriptor.instance_id = stimer_id;
    service->descriptor.context = service;
    service->descriptor.handle = stimer_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable descriptor of one initialized STIMER Service.
 * @param[in] service Initialized STIMER Service.
 * @note The descriptor aliases Service-owned storage.
 * @return Descriptor pointer or NULL when service is NULL.
 */
const et_service_descriptor_t *et_stimer_service_descriptor(const et_stimer_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/**
 * @brief Create one STIMER Service through the generic factory.
 * @param[out] storage Service storage.
 * @param[in] instance_id Stable logical identifier.
 * @param[in] context Common dependencies.
 * @param[out] descriptor Created descriptor.
 * @note Factory creation does not configure STIMER hardware.
 * @return Zero on success, otherwise minus one.
 */
int et_stimer_service_create(void *storage, uint16_t instance_id,
                             const et_service_factory_context_t *context,
                             const et_service_descriptor_t **descriptor)
{
    et_stimer_service_t *service = (et_stimer_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (descriptor == NULL) ||
        (et_stimer_service_init(service, (et_stimer_id_t)instance_id, context->irq_manager,
                                context->irq_priority) != 0))
    {
        return -1;
    }

    *descriptor = et_stimer_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}
