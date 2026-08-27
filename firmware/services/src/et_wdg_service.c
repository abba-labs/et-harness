/**
 * @file et_wdg_service.c
 * @brief Decode WDG commands and return raw watchdog observations.
 */

#include "et_wdg_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Read one little-endian 32-bit Wire value.
 * @param[in] data Four readable Wire bytes.
 * @note This codec helper does not access watchdog hardware.
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
    data[0] = (uint8_t)(value & ET_WDG_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_WDG_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Write one little-endian 32-bit Wire value.
 * @param[out] data Four writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This codec helper has no hardware side effect.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & ET_WDG_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_WDG_SERVICE_WIRE_BYTE_MASK);
    data[2] = (uint8_t)((value >> 16u) & ET_WDG_SERVICE_WIRE_BYTE_MASK);
    data[3] = (uint8_t)((value >> 24u) & ET_WDG_SERVICE_WIRE_BYTE_MASK);
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
 * @brief Decode one complete WDG configuration request.
 * @param[in] service WDG Service owning the logical instance.
 * @param[in] body Raw command body.
 * @param[in] length Number of readable bytes.
 * @param[out] config Decoded public Wrap configuration.
 * @note Validation of hardware limits remains owned by WDG Wrap.
 * @return Zero on success, otherwise minus one.
 */
static int decode_config(const et_wdg_service_t *service, const uint8_t *body, uint16_t length,
                         et_wdg_wrap_config_t *config)
{
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_WDG_SERVICE_CONFIG_SIZE))
    {
        return -1;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_WDG_WRAP_API_VERSION;
    config->wdg_id = service->wdg_id;
    config->reload_count = read_u32(&body[ET_WDG_SERVICE_CONFIG_RELOAD_OFFSET]);
    config->window_low_count = read_u32(&body[ET_WDG_SERVICE_CONFIG_WINDOW_LOW_OFFSET]);
    config->window_high_count = read_u32(&body[ET_WDG_SERVICE_CONFIG_WINDOW_HIGH_OFFSET]);
    config->mode = body[ET_WDG_SERVICE_CONFIG_MODE_OFFSET];
    config->work_mode = body[ET_WDG_SERVICE_CONFIG_WORK_MODE_OFFSET];
    config->reset_enable = body[ET_WDG_SERVICE_CONFIG_RESET_ENABLE_OFFSET];
    config->halt_pause_enable = body[ET_WDG_SERVICE_CONFIG_HALT_PAUSE_OFFSET];

    return 0;
}

/**
 * @brief Encode one complete WDG configuration snapshot.
 * @param[out] body Response buffer with ET_WDG_SERVICE_CONFIG_SIZE bytes.
 * @param[in] config Public configuration to encode.
 * @note This helper performs Wire encoding only.
 */
static void encode_config(uint8_t *body, const et_wdg_wrap_config_t *config)
{
    write_u32(&body[ET_WDG_SERVICE_CONFIG_RELOAD_OFFSET], config->reload_count);
    write_u32(&body[ET_WDG_SERVICE_CONFIG_WINDOW_LOW_OFFSET], config->window_low_count);
    write_u32(&body[ET_WDG_SERVICE_CONFIG_WINDOW_HIGH_OFFSET], config->window_high_count);
    body[ET_WDG_SERVICE_CONFIG_MODE_OFFSET] = config->mode;
    body[ET_WDG_SERVICE_CONFIG_WORK_MODE_OFFSET] = config->work_mode;
    body[ET_WDG_SERVICE_CONFIG_RESET_ENABLE_OFFSET] = config->reset_enable;
    body[ET_WDG_SERVICE_CONFIG_HALT_PAUSE_OFFSET] = config->halt_pause_enable;
}

/**
 * @brief Record one real WDG IRQ delivery and clear the observed source.
 * @param[in,out] context WDG Service callback context.
 * @param[in] irq_line Physical IRQ line that dispatched the callback.
 * @param[in] route_events Stable route event mask.
 * @note The callback is bounded and records facts only; it never decides PASS or FAIL.
 */
static void wdg_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_wdg_service_t *service = (et_wdg_service_t *)context;
    et_wdg_wrap_irq_snapshot_t snapshot;
    uint32_t observed;

    if ((service == NULL) || (irq_line != service->irq_route.irq_line) ||
        ((route_events & ET_WDG_WRAP_IRQ_ALL) == 0u) ||
        (et_wdg_wrap_irq_snapshot_get(service->wdg_id, &snapshot) != ET_WRAP_STATUS_OK))
    {
        return;
    }

    observed = snapshot.raw & service->irq_enabled_sources;

    if (observed != 0u)
    {
        service->irq_latched_sources |= observed;
        service->irq_last_raw = snapshot.raw;

        if (service->irq_event_count != UINT32_MAX)
        {
            service->irq_event_count++;
        }

        (void)et_wdg_wrap_irq_clear(service->wdg_id, observed);
    }
}

/**
 * @brief Bind the WDG route and enable the timeout source.
 * @param[in,out] service Configured WDG Service.
 * @param[in] sources Stable IRQ source mask.
 * @note A failed source-enable operation rolls back a newly created route binding.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_enable(et_wdg_service_t *service, uint32_t sources)
{
    uint8_t newly_bound = (uint8_t)(service->irq_bound == 0u);

    if ((service->irq_bound == 0u) &&
        ((et_wdg_wrap_get_irq_route(service->wdg_id, &service->irq_route) != ET_WRAP_STATUS_OK) ||
         (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                              wdg_irq_callback, service) != 0)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_bound = 1u;

    if (et_wdg_wrap_irq_enable(service->wdg_id, sources) != ET_WRAP_STATUS_OK)
    {
        if (newly_bound != 0u)
        {
            (void)et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                        wdg_irq_callback, service);
            service->irq_bound = 0u;
        }

        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources |= sources;

    return ET_STATUS_OK;
}

/**
 * @brief Disable WDG sources and release an unused IRQ route.
 * @param[in,out] service Configured WDG Service.
 * @param[in] sources Stable IRQ source mask.
 * @note Existing hardware pending state remains available until IRQ_CLEAR.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_disable(et_wdg_service_t *service, uint32_t sources)
{
    if (et_wdg_wrap_irq_disable(service->wdg_id, sources) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources &= ~sources;

    if ((service->irq_bound != 0u) && (service->irq_enabled_sources == 0u))
    {
        if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                  wdg_irq_callback, service) != 0)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        service->irq_bound = 0u;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Dispatch one validated WDG command to WDG Wrap or common IRQ Manager.
 * @param[in,out] context WDG Service retained by Router.
 * @param[in] command_id Stable WDG command identifier.
 * @param[in] request_body Optional request bytes.
 * @param[in] request_length Number of valid request bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 * @note This Service contains no Case verdict and calls no other Feature IP.
 * @return Stable ET protocol status.
 */
static uint16_t wdg_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    et_wdg_service_t *service = (et_wdg_service_t *)context;
    et_wdg_wrap_capabilities_t capabilities;
    et_wdg_wrap_config_t config;
    et_wdg_wrap_status_t status;
    et_wdg_wrap_irq_snapshot_t irq_snapshot;
    et_wdg_wrap_record_snapshot_t records;
    et_wrap_status_t wrap_status;
    uint32_t value;
    uint32_t irq_key;
    uint32_t event_count;
    uint32_t latched;
    uint32_t last_raw;

    /* Phase 1: Validate the Router envelope before command-specific decoding. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *response_length = 0u;

    /* Phase 2: Execute one bounded WDG-owned command. */
    switch (command_id)
    {
        case ET_WDG_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_WDG_SERVICE_CAPABILITIES_SIZE) ||
                (et_wdg_wrap_capabilities_get(service->wdg_id, &capabilities) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u16(&response_body[ET_WDG_SERVICE_CAPS_API_VERSION_OFFSET],
                      ET_WDG_SERVICE_API_VERSION);
            write_u16(&response_body[ET_WDG_SERVICE_CAPS_STRUCT_SIZE_OFFSET],
                      ET_WDG_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_WDG_SERVICE_CAPS_FEATURES_OFFSET], capabilities.features);
            write_u32(&response_body[ET_WDG_SERVICE_CAPS_MAX_RELOAD_OFFSET],
                      capabilities.maximum_reload_count);
            write_u32(&response_body[ET_WDG_SERVICE_CAPS_MAX_WINDOW_OFFSET],
                      capabilities.maximum_window_count);
            response_body[ET_WDG_SERVICE_CAPS_MODE_MASK_OFFSET] = capabilities.mode_mask;
            response_body[ET_WDG_SERVICE_CAPS_WORK_MODE_MASK_OFFSET] = capabilities.work_mode_mask;
            response_body[ET_WDG_SERVICE_CAPS_IRQ_SOURCES_OFFSET] = capabilities.irq_sources;
            response_body[ET_WDG_SERVICE_CAPS_INSTANCE_COUNT_OFFSET] = capabilities.instance_count;
            *response_length = ET_WDG_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_UNLOCK:
        case ET_WDG_COMMAND_LOCK:
        case ET_WDG_COMMAND_ENABLE:
        case ET_WDG_COMMAND_DISABLE:
        case ET_WDG_COMMAND_FEED:
        case ET_WDG_COMMAND_MODULE_RESET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_WDG_COMMAND_UNLOCK)
            {
                wrap_status = et_wdg_wrap_unlock(service->wdg_id);
            }
            else if (command_id == ET_WDG_COMMAND_LOCK)
            {
                wrap_status = et_wdg_wrap_lock(service->wdg_id);
            }
            else if (command_id == ET_WDG_COMMAND_ENABLE)
            {
                wrap_status = et_wdg_wrap_enable(service->wdg_id);
            }
            else if (command_id == ET_WDG_COMMAND_DISABLE)
            {
                wrap_status = et_wdg_wrap_disable(service->wdg_id);
            }
            else if (command_id == ET_WDG_COMMAND_FEED)
            {
                wrap_status = et_wdg_wrap_feed(service->wdg_id);
            }
            else
            {
                wrap_status = et_wdg_wrap_module_reset(service->wdg_id);
                service->configured = 0u;
            }

            return status_from_wrap(wrap_status);
        }

        case ET_WDG_COMMAND_CONFIGURE:
        {
            if ((decode_config(service, request_body, request_length, &config) != 0) ||
                (et_wdg_wrap_configure(service->wdg_id, &config) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            service->configured = 1u;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_CONFIG_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_WDG_SERVICE_CONFIG_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_wdg_wrap_config_get(service->wdg_id, &config);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            encode_config(response_body, &config);
            *response_length = ET_WDG_SERVICE_CONFIG_SIZE;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_STATUS_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_WDG_SERVICE_STATUS_SIZE) ||
                (et_wdg_wrap_status_get(service->wdg_id, &status) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            response_body[ET_WDG_SERVICE_STATUS_ENABLED_OFFSET] = status.enabled;
            (void)memset(&response_body[ET_WDG_SERVICE_STATUS_RESERVED_OFFSET], 0,
                         ET_WDG_SERVICE_STATUS_RESERVED_SIZE);
            write_u32(&response_body[ET_WDG_SERVICE_STATUS_COUNTER_OFFSET], status.counter);
            *response_length = ET_WDG_SERVICE_STATUS_SIZE;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_IRQ_ENABLE:
        case ET_WDG_COMMAND_IRQ_DISABLE:
        case ET_WDG_COMMAND_IRQ_MASK:
        case ET_WDG_COMMAND_IRQ_UNMASK:
        case ET_WDG_COMMAND_IRQ_FORCE:
        case ET_WDG_COMMAND_IRQ_CLEAR:
        {
            if (request_length != ET_WDG_SERVICE_MASK_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            value = read_u32(request_body);

            if (command_id == ET_WDG_COMMAND_IRQ_ENABLE)
            {
                return handle_irq_enable(service, value);
            }

            if (command_id == ET_WDG_COMMAND_IRQ_DISABLE)
            {
                return handle_irq_disable(service, value);
            }

            if (command_id == ET_WDG_COMMAND_IRQ_MASK)
            {
                wrap_status = et_wdg_wrap_irq_mask(service->wdg_id, value);
            }
            else if (command_id == ET_WDG_COMMAND_IRQ_UNMASK)
            {
                wrap_status = et_wdg_wrap_irq_unmask(service->wdg_id, value);
            }
            else if (command_id == ET_WDG_COMMAND_IRQ_FORCE)
            {
                wrap_status = et_wdg_wrap_irq_force(service->wdg_id, value);
            }
            else
            {
                wrap_status = et_wdg_wrap_irq_clear(service->wdg_id, value);

                if (wrap_status == ET_WRAP_STATUS_OK)
                {
                    irq_key = et_irq_manager_enter_critical();
                    service->irq_latched_sources &= ~value;
                    et_irq_manager_exit_critical(irq_key);
                }
            }

            return status_from_wrap(wrap_status);
        }

        case ET_WDG_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_WDG_SERVICE_IRQ_SNAPSHOT_SIZE) ||
                (et_wdg_wrap_irq_snapshot_get(service->wdg_id, &irq_snapshot) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            irq_key = et_irq_manager_enter_critical();
            event_count = service->irq_event_count;
            latched = service->irq_latched_sources;
            last_raw = service->irq_last_raw;
            et_irq_manager_exit_critical(irq_key);

            write_u32(&response_body[ET_WDG_SERVICE_IRQ_RAW_OFFSET], irq_snapshot.raw);
            write_u32(&response_body[ET_WDG_SERVICE_IRQ_STATUS_OFFSET], irq_snapshot.status);
            write_u32(&response_body[ET_WDG_SERVICE_IRQ_LATCHED_OFFSET], latched);
            write_u32(&response_body[ET_WDG_SERVICE_IRQ_EVENT_COUNT_OFFSET], event_count);
            write_u32(&response_body[ET_WDG_SERVICE_IRQ_LAST_RAW_OFFSET], last_raw);
            *response_length = ET_WDG_SERVICE_IRQ_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_RECORD_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_WDG_SERVICE_RECORD_SIZE) ||
                (et_wdg_wrap_record_get(service->wdg_id, &records) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            response_body[ET_WDG_SERVICE_RECORD_RESET_OFFSET] = records.reset;
            response_body[ET_WDG_SERVICE_RECORD_INTERRUPT_OFFSET] = records.interrupt;
            (void)memset(&response_body[ET_WDG_SERVICE_RECORD_RESERVED_OFFSET], 0,
                         ET_WDG_SERVICE_RECORD_RESERVED_SIZE);
            *response_length = ET_WDG_SERVICE_RECORD_SIZE;

            return ET_STATUS_OK;
        }

        case ET_WDG_COMMAND_RECORD_CLEAR:
        {
            if (request_length != ET_WDG_SERVICE_MASK_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_wdg_wrap_record_clear(service->wdg_id, read_u32(request_body)));
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one WDG Service without touching watchdog hardware.
 * @param[out] service Application-owned Service storage.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in,out] irq_manager Common IRQ Manager.
 * @param[in] irq_priority Board-selected NVIC priority.
 * @note Initialization creates bounded state and one immutable descriptor only.
 * @return Zero on success, otherwise minus one.
 */
int et_wdg_service_init(et_wdg_service_t *service, et_wdg_id_t wdg_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->wdg_id = wdg_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_WDG_SERVICE_ID;
    service->descriptor.instance_id = wdg_id;
    service->descriptor.context = service;
    service->descriptor.handle = wdg_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable descriptor of one initialized WDG Service.
 * @param[in] service Initialized WDG Service.
 * @note The descriptor aliases Service-owned storage.
 * @return Descriptor pointer or NULL when service is NULL.
 */
const et_service_descriptor_t *et_wdg_service_descriptor(const et_wdg_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Create one WDG Service through the generic factory contract.
 * @param[out] storage Caller-owned Service storage.
 * @param[in] instance_id Stable logical watchdog identifier.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Initialized descriptor.
 * @note Factory creation does not configure watchdog hardware.
 * @return Zero on success, otherwise minus one.
 */
int et_wdg_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_wdg_service_t *service = (et_wdg_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_wdg_service_init(service, (et_wdg_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_wdg_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
