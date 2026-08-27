/**
 * @file et_cordic_service.c
 * @brief Decode CORDIC commands and return raw hardware observations.
 */

#include "et_cordic_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Decode one unaligned little-endian 32-bit Wire value.
 * @param[in] data Four encoded bytes.
 * @note This helper has no hardware side effect.
 * @return Decoded value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Encode one 16-bit value into an unaligned little-endian Wire field.
 * @param[out] data Two-byte destination.
 * @param[in] value Value to encode.
 * @note This helper changes only caller-owned response memory.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian Wire field.
 * @param[out] data Four-byte destination.
 * @param[in] value Value to encode.
 * @note This helper changes only caller-owned response memory.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Validate one reserved Wire region.
 * @param[in] data Reserved bytes.
 * @param[in] length Number of bytes to inspect.
 * @note This helper has no hardware side effect.
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
 * @brief Translate one Wrap result into the ET protocol status namespace.
 * @param[in] status Stable Wrap status.
 * @note Selected Driver status never crosses the Service boundary.
 * @return Stable ET protocol status.
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
 * @brief Decode one nonempty stable IRQ source request.
 * @param[in] body Request body.
 * @param[in] length Number of valid request bytes.
 * @param[out] sources Decoded stable IRQ source mask.
 * @note Validation completes before any IRQ state changes.
 * @return Zero on success, otherwise minus one.
 */
static int decode_irq_sources(const uint8_t *body, uint16_t length, uint32_t *sources)
{
    if ((body == NULL) || (sources == NULL) || (length != ET_CORDIC_SERVICE_IRQ_REQUEST_SIZE))
    {
        return -1;
    }

    *sources = read_u32(body);

    if ((*sources == 0u) || ((*sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return -1;
    }

    return 0;
}

/**
 * @brief Decode one complete public CORDIC configuration.
 * @param[in] service CORDIC Service owning the logical instance.
 * @param[in] body Fixed Wire request body.
 * @param[in] length Number of valid request bytes.
 * @param[out] config Versioned Wrap configuration.
 * @note Semantic range validation remains centralized in CORDIC Wrap.
 * @return Zero on success, otherwise minus one.
 */
static int decode_config(et_cordic_service_t *service, const uint8_t *body, uint16_t length,
                         et_cordic_wrap_config_t *config)
{
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_CORDIC_SERVICE_CONFIG_REQUEST_SIZE) ||
        (bytes_are_zero(&body[ET_CORDIC_SERVICE_CONFIG_RESERVED_OFFSET],
                        ET_CORDIC_SERVICE_CONFIG_RESERVED_SIZE) == 0u))
    {
        return -1;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_CORDIC_WRAP_API_VERSION;
    config->cordic_id = service->cordic_id;
    config->numeric_mode = body[ET_CORDIC_SERVICE_CONFIG_NUMERIC_OFFSET];
    config->argument_width = body[ET_CORDIC_SERVICE_CONFIG_ARGUMENT_WIDTH_OFFSET];
    config->result_width = body[ET_CORDIC_SERVICE_CONFIG_RESULT_WIDTH_OFFSET];
    config->input_range = body[ET_CORDIC_SERVICE_CONFIG_RANGE_OFFSET];
    config->scale = body[ET_CORDIC_SERVICE_CONFIG_SCALE_OFFSET];
    config->precision_cycles = body[ET_CORDIC_SERVICE_CONFIG_PRECISION_OFFSET];
    config->sincos_result_count = body[ET_CORDIC_SERVICE_CONFIG_SINCOS_RESULTS_OFFSET];
    config->phase_modulus_result_count = body[ET_CORDIC_SERVICE_CONFIG_PM_RESULTS_OFFSET];
    config->hsincos_result_count = body[ET_CORDIC_SERVICE_CONFIG_HSINCOS_RESULTS_OFFSET];
    config->work_mode = body[ET_CORDIC_SERVICE_CONFIG_WORK_MODE_OFFSET];

    return 0;
}

/**
 * @brief Record one real IRQ delivery and clear observed enabled sources.
 * @param[in,out] context CORDIC Service callback context.
 * @param[in] irq_line Physical line that dispatched the callback.
 * @param[in] route_events Stable route event mask.
 * @note The callback records facts only and never decides a test result.
 */
static void cordic_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_cordic_service_t *service = (et_cordic_service_t *)context;
    et_cordic_wrap_irq_snapshot_t snapshot;
    uint32_t observed;

    if ((service == NULL) || (irq_line != service->irq_route.irq_line) ||
        ((route_events & ET_CORDIC_WRAP_IRQ_ALL) == 0u) ||
        (et_cordic_wrap_irq_snapshot_get(service->cordic_id, &snapshot) != ET_WRAP_STATUS_OK))
    {
        return;
    }

    observed = snapshot.raw & service->irq_enabled_sources;

    if (observed != 0u)
    {
        service->irq_last_raw = snapshot.raw;
        service->irq_last_event = observed;

        if (service->irq_event_count != UINT32_MAX)
        {
            service->irq_event_count++;
        }

        (void)et_cordic_wrap_irq_clear(service->cordic_id, observed);
    }
}

/**
 * @brief Bind the CORDIC route and enable selected sources.
 * @param[in,out] service Configured CORDIC Service.
 * @param[in] sources Stable IRQ source mask.
 * @note A failed peripheral-enable step rolls back a newly created binding.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_enable(et_cordic_service_t *service, uint32_t sources)
{
    uint8_t newly_bound = (uint8_t)(service->irq_bound == 0u);

    if ((service->irq_bound == 0u) &&
        ((et_cordic_wrap_get_irq_route(service->cordic_id, &service->irq_route) !=
          ET_WRAP_STATUS_OK) ||
         (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                              cordic_irq_callback, service) != 0)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    service->irq_bound = 1u;

    if (et_cordic_wrap_irq_enable(service->cordic_id, sources) != ET_WRAP_STATUS_OK)
    {
        if (newly_bound != 0u)
        {
            (void)et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                        cordic_irq_callback, service);
            service->irq_bound = 0u;
        }

        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources |= sources;

    return ET_STATUS_OK;
}

/**
 * @brief Disable selected sources and release an unused IRQ route.
 * @param[in,out] service Configured CORDIC Service.
 * @param[in] sources Stable IRQ source mask.
 * @note Other enabled sources and their binding remain active.
 * @return Stable ET protocol status.
 */
static uint16_t handle_irq_disable(et_cordic_service_t *service, uint32_t sources)
{
    if (et_cordic_wrap_irq_disable(service->cordic_id, sources) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    service->irq_enabled_sources &= ~sources;

    if ((service->irq_bound != 0u) && (service->irq_enabled_sources == 0u))
    {
        if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                  cordic_irq_callback, service) != 0)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        service->irq_bound = 0u;
    }

    return ET_STATUS_OK;
}

/**
 * @brief Dispatch one validated CORDIC command to its own Wrap operation.
 * @param[in,out] context CORDIC Service retained by the Router.
 * @param[in] command_id Stable CORDIC command identifier.
 * @param[in] request_body Optional request body.
 * @param[in] request_length Number of valid request bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 * @note This Service calls only CORDIC Wrap and common IRQ Manager.
 * @return Stable ET protocol status.
 */
static uint16_t cordic_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                              uint16_t request_length, uint8_t *response_body,
                              uint16_t response_capacity, uint16_t *response_length)
{
    et_cordic_service_t *service = (et_cordic_service_t *)context;
    et_cordic_wrap_capabilities_t capabilities;
    et_cordic_wrap_config_t config;
    et_cordic_wrap_irq_snapshot_t irq_snapshot;
    uint32_t values[ET_CORDIC_SERVICE_RESULT_WORD_COUNT];
    uint32_t sources;
    uint32_t value;
    uint32_t irq_key;
    uint32_t event_count;
    uint32_t last_event;
    uint32_t last_raw;
    uint32_t elapsed_cycles;
    et_wrap_status_t wrap_status;

    /* Phase 1: Validate the common Router envelope before command-specific decoding. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *response_length = 0u;

    /* Phase 2: Decode one stable command and call only CORDIC-owned operations. */
    switch (command_id)
    {
        case ET_CORDIC_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_CORDIC_SERVICE_CAPABILITIES_SIZE) ||
                (et_cordic_wrap_capabilities_get(service->cordic_id, &capabilities) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            (void)memset(response_body, 0, ET_CORDIC_SERVICE_CAPABILITIES_SIZE);
            write_u16(&response_body[ET_CORDIC_SERVICE_CAPS_API_VERSION_OFFSET],
                      ET_CORDIC_SERVICE_API_VERSION);
            write_u16(&response_body[ET_CORDIC_SERVICE_CAPS_STRUCT_SIZE_OFFSET],
                      ET_CORDIC_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_CORDIC_SERVICE_CAPS_FEATURES_OFFSET],
                      capabilities.features);
            write_u16(&response_body[ET_CORDIC_SERVICE_CAPS_FUNCTIONS_OFFSET],
                      capabilities.function_mask);
            response_body[ET_CORDIC_SERVICE_CAPS_MAX_SCALE_OFFSET] = capabilities.maximum_scale;
            response_body[ET_CORDIC_SERVICE_CAPS_MAX_PRECISION_OFFSET] =
                capabilities.maximum_precision_cycles;
            response_body[ET_CORDIC_SERVICE_CAPS_IRQ_SOURCES_OFFSET] = capabilities.irq_sources;
            *response_length = ET_CORDIC_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_CONFIGURE:
        {
            if ((decode_config(service, request_body, request_length, &config) != 0) ||
                (et_cordic_wrap_configure(service->cordic_id, &config) != ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            service->configured = 1u;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_ARGUMENT_SUBMIT:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_CORDIC_SERVICE_ARGUMENT_REQUEST_SIZE) ||
                (bytes_are_zero(&request_body[ET_CORDIC_SERVICE_ARGUMENT_RESERVED_OFFSET],
                                ET_CORDIC_SERVICE_ARGUMENT_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_cordic_wrap_argument_submit(
                service->cordic_id, request_body[ET_CORDIC_SERVICE_ARGUMENT_FUNCTION_OFFSET],
                read_u32(&request_body[ET_CORDIC_SERVICE_ARGUMENT_VALUE_OFFSET])));
        }

        case ET_CORDIC_COMMAND_RESULT_GET:
        {
            if ((service->configured == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CORDIC_SERVICE_RESULT_RESPONSE_SIZE) ||
                (et_cordic_wrap_result_get(service->cordic_id, &values[0], &values[1]) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u32(&response_body[ET_CORDIC_SERVICE_RESULT_PRIMARY_OFFSET], values[0]);
            write_u32(&response_body[ET_CORDIC_SERVICE_RESULT_SECONDARY_OFFSET], values[1]);
            *response_length = ET_CORDIC_SERVICE_RESULT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_STATUS_GET:
        case ET_CORDIC_COMMAND_ARGUMENT_COUNT_GET:
        case ET_CORDIC_COMMAND_CONVERSION_STATUS_GET:
        {
            if ((service->configured == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CORDIC_SERVICE_WORD_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_CORDIC_COMMAND_STATUS_GET)
            {
                wrap_status = et_cordic_wrap_status_get(service->cordic_id, &value);
            }
            else if (command_id == ET_CORDIC_COMMAND_ARGUMENT_COUNT_GET)
            {
                wrap_status = et_cordic_wrap_argument_count_get(service->cordic_id, &value);
            }
            else
            {
                wrap_status = et_cordic_wrap_conversion_status_get(service->cordic_id, &value);
            }

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(response_body, value);
            *response_length = ET_CORDIC_SERVICE_WORD_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_STATUS_CLEAR:
        case ET_CORDIC_COMMAND_CONVERSION_STATUS_CLEAR:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_CORDIC_SERVICE_WORD_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            value = read_u32(request_body);
            wrap_status = (command_id == ET_CORDIC_COMMAND_STATUS_CLEAR)
                              ? et_cordic_wrap_status_clear(service->cordic_id, value)
                              : et_cordic_wrap_conversion_status_clear(service->cordic_id, value);

            return status_from_wrap(wrap_status);
        }

        case ET_CORDIC_COMMAND_IRQ_ENABLE:
        case ET_CORDIC_COMMAND_IRQ_DISABLE:
        case ET_CORDIC_COMMAND_IRQ_MASK:
        case ET_CORDIC_COMMAND_IRQ_UNMASK:
        case ET_CORDIC_COMMAND_IRQ_FORCE:
        case ET_CORDIC_COMMAND_IRQ_CLEAR:
        {
            if ((service->configured == 0u) ||
                (decode_irq_sources(request_body, request_length, &sources) != 0))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_CORDIC_COMMAND_IRQ_ENABLE)
            {
                return handle_irq_enable(service, sources);
            }

            if (command_id == ET_CORDIC_COMMAND_IRQ_DISABLE)
            {
                return handle_irq_disable(service, sources);
            }

            if (command_id == ET_CORDIC_COMMAND_IRQ_MASK)
            {
                wrap_status = et_cordic_wrap_irq_mask(service->cordic_id, sources);
            }
            else if (command_id == ET_CORDIC_COMMAND_IRQ_UNMASK)
            {
                wrap_status = et_cordic_wrap_irq_unmask(service->cordic_id, sources);
            }
            else if (command_id == ET_CORDIC_COMMAND_IRQ_FORCE)
            {
                wrap_status = et_cordic_wrap_irq_force(service->cordic_id, sources);
            }
            else
            {
                wrap_status = et_cordic_wrap_irq_clear(service->cordic_id, sources);
            }

            return status_from_wrap(wrap_status);
        }

        case ET_CORDIC_COMMAND_IRQ_SNAPSHOT_GET:
        {
            if ((service->configured == 0u) || (request_length != 0u) ||
                (response_capacity < ET_CORDIC_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE) ||
                (et_cordic_wrap_irq_snapshot_get(service->cordic_id, &irq_snapshot) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            irq_key = et_irq_manager_enter_critical();
            event_count = service->irq_event_count;
            last_event = service->irq_last_event;
            last_raw = service->irq_last_raw;
            et_irq_manager_exit_critical(irq_key);

            write_u32(&response_body[ET_CORDIC_SERVICE_IRQ_RAW_OFFSET], irq_snapshot.raw);
            write_u32(&response_body[ET_CORDIC_SERVICE_IRQ_STATUS_OFFSET], irq_snapshot.status);
            write_u32(&response_body[ET_CORDIC_SERVICE_IRQ_EVENT_COUNT_OFFSET], event_count);
            write_u32(&response_body[ET_CORDIC_SERVICE_IRQ_LAST_EVENT_OFFSET], last_event);
            write_u32(&response_body[ET_CORDIC_SERVICE_IRQ_LAST_RAW_OFFSET], last_raw);
            *response_length = ET_CORDIC_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_ZERO_OVERHEAD_EXECUTE:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_CORDIC_SERVICE_ZERO_OVERHEAD_REQUEST_SIZE) ||
                (response_capacity < ET_CORDIC_SERVICE_ZERO_OVERHEAD_RESPONSE_SIZE) ||
                (bytes_are_zero(&request_body[ET_CORDIC_SERVICE_ZERO_RESERVED_OFFSET],
                                ET_CORDIC_SERVICE_ZERO_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            values[0] = read_u32(&request_body[ET_CORDIC_SERVICE_ZERO_ARGUMENT0_OFFSET]);
            values[1] = read_u32(&request_body[ET_CORDIC_SERVICE_ZERO_ARGUMENT1_OFFSET]);
            wrap_status = et_cordic_wrap_zero_overhead_execute(
                service->cordic_id, request_body[ET_CORDIC_SERVICE_ZERO_FUNCTION_OFFSET], values,
                request_body[ET_CORDIC_SERVICE_ZERO_COUNT_OFFSET], &values[0], &values[1]);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_CORDIC_SERVICE_RESULT_PRIMARY_OFFSET], values[0]);
            write_u32(&response_body[ET_CORDIC_SERVICE_RESULT_SECONDARY_OFFSET], values[1]);
            *response_length = ET_CORDIC_SERVICE_ZERO_OVERHEAD_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CORDIC_COMMAND_TEST_EXECUTE_TIMED:
        {
            if ((service->configured == 0u) ||
                (request_length != ET_CORDIC_SERVICE_TIMED_REQUEST_SIZE) ||
                (response_capacity < ET_CORDIC_SERVICE_TIMED_RESPONSE_SIZE) ||
                (bytes_are_zero(&request_body[ET_CORDIC_SERVICE_TIMED_RESERVED_OFFSET],
                                ET_CORDIC_SERVICE_TIMED_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            values[0] = read_u32(&request_body[ET_CORDIC_SERVICE_TIMED_ARGUMENT0_OFFSET]);
            values[1] = read_u32(&request_body[ET_CORDIC_SERVICE_TIMED_ARGUMENT1_OFFSET]);
            wrap_status = et_cordic_wrap_execute_timed(
                service->cordic_id, request_body[ET_CORDIC_SERVICE_TIMED_FUNCTION_OFFSET], values,
                request_body[ET_CORDIC_SERVICE_TIMED_COUNT_OFFSET],
                read_u32(&request_body[ET_CORDIC_SERVICE_TIMED_TIMEOUT_OFFSET]), &values[0],
                &values[1], &elapsed_cycles);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_CORDIC_SERVICE_TIMED_PRIMARY_OFFSET], values[0]);
            write_u32(&response_body[ET_CORDIC_SERVICE_TIMED_SECONDARY_OFFSET], values[1]);
            write_u32(&response_body[ET_CORDIC_SERVICE_TIMED_CYCLES_OFFSET], elapsed_cycles);
            *response_length = ET_CORDIC_SERVICE_TIMED_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one CORDIC Service without touching CORDIC hardware.
 * @param[out] service Application-owned Service storage.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in,out] irq_manager Common IRQ Manager.
 * @param[in] irq_priority Board-selected NVIC priority.
 * @note Initialization only creates bounded software state and a descriptor.
 * @return Zero on success, otherwise minus one.
 */
int et_cordic_service_init(et_cordic_service_t *service, et_cordic_id_t cordic_id,
                           et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->cordic_id = cordic_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_CORDIC_SERVICE_ID;
    service->descriptor.instance_id = cordic_id;
    service->descriptor.context = service;
    service->descriptor.handle = cordic_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable descriptor of one initialized CORDIC Service.
 * @param[in] service Initialized CORDIC Service.
 * @note The descriptor aliases Service-owned storage.
 * @return Descriptor pointer, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_cordic_service_descriptor(const et_cordic_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Create one CORDIC Service through the generic factory contract.
 * @param[out] storage Caller-owned Service storage.
 * @param[in] instance_id Stable logical CORDIC instance identifier.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Initialized descriptor.
 * @note Factory creation does not configure CORDIC hardware.
 * @return Zero on success, otherwise minus one.
 */
int et_cordic_service_create(void *storage, uint16_t instance_id,
                             const et_service_factory_context_t *context,
                             const et_service_descriptor_t **descriptor)
{
    et_cordic_service_t *service = (et_cordic_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_cordic_service_init(service, (et_cordic_id_t)instance_id, context->irq_manager,
                               context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_cordic_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
