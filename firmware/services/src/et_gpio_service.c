/** @file et_gpio_service.c @brief Decode one signal request and call GPIO Wrap only. */
#include "et_gpio_service.h"

#include <string.h>
#include "et_gpio_wrap.h"
#include "et_message.h"

/**
 * @brief Decode one unaligned little-endian word from the validated body.
 * @param[in] data Two available bytes.
 * @return Unsigned decoded value.
 * @note Pure Wire decoding, without hardware access.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8u));
}

/**
 * @brief Translate a GPIO Wrap result into the common response status.
 * @param[in] status GPIO Wrap result.
 * @return Protocol status preserving unsupported, invalid and busy outcomes.
 * @note No device or Service state is changed.
 */
static uint16_t status_from_wrap(et_wrap_status_t status)
{
    switch (status)
    {
        case ET_WRAP_STATUS_OK:
        {
            return ET_STATUS_OK;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_INVALID_ARGUMENT:
        {
            return ET_STATUS_INVALID_PARAM;
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
 * @brief Decode and dispatch one fixed-size GPIO signal action.
 * @param[in,out] context Initialized descriptor storage.
 * @param[in] command_id Stable GPIO command.
 * @param[in] request_body Three logical u16 fields.
 * @param[in] request_length Available request bytes.
 * @param[out] response_body Unused because both commands return status only.
 * @param[in] response_capacity Unused empty response capacity.
 * @param[out] response_length Set to zero before execution.
 * @return Exact validation or Wrap result.
 * @note Runs in command context; no SPI, CRG, IRQ or test workflow is executed.
 */
static uint16_t gpio_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                            uint16_t request_length, uint8_t *response_body,
                            uint16_t response_capacity, uint16_t *response_length)
{
    uint16_t pin;
    uint16_t function;
    uint16_t instance;

    (void)response_body;
    (void)response_capacity;

    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if ((context == NULL) || (request_body == NULL) ||
        (request_length != ET_GPIO_SERVICE_REQUEST_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    pin = read_u16(&request_body[ET_GPIO_SERVICE_PIN_OFFSET]);
    function = read_u16(&request_body[ET_GPIO_SERVICE_FUNCTION_OFFSET]);
    instance = read_u16(&request_body[ET_GPIO_SERVICE_INSTANCE_OFFSET]);

    switch (command_id)
    {
        case ET_GPIO_COMMAND_VALIDATE_SIGNAL:
        {
            return status_from_wrap(et_gpio_wrap_validate_signal(pin, function, instance));
        }

        case ET_GPIO_COMMAND_CONFIGURE_SIGNAL:
        {
            return status_from_wrap(et_gpio_wrap_configure_signal(pin, function, instance));
        }

        default:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Initialize the single GPIO support descriptor.
 * @param[out] service Application-owned storage.
 * @param[in] instance_id Must be zero; signal instance is in each request body.
 * @param[in,out] irq_manager Unused factory dependency; GPIO support allocates no IRQ.
 * @param[in] irq_priority Unused factory priority.
 * @return Zero on success, minus one for invalid storage or service instance.
 * @note Registration does not configure any pad or peripheral.
 */
int et_gpio_service_init(et_gpio_service_t *service, uint16_t instance_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    (void)irq_manager;
    (void)irq_priority;

    if ((service == NULL) || (instance_id != 0u))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->descriptor.service_id = ET_GPIO_SERVICE_ID;
    service->descriptor.instance_id = instance_id;
    service->descriptor.context = service;
    service->descriptor.handle = gpio_handle;

    return 0;
}

/**
 * @brief Return the initialized GPIO descriptor.
 * @param[in] service Application-owned storage.
 * @return Descriptor alias or NULL for invalid storage.
 * @note No hardware access or initialization is performed.
 */
const et_service_descriptor_t *et_gpio_service_descriptor(const et_gpio_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct the GPIO descriptor through the existing Service factory.
 * @param[out] storage Application-owned Service storage.
 * @param[in] instance_id Logical support service identity.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Resulting router descriptor.
 * @return Zero on success, minus one when initialization fails.
 * @note Does not configure pins or allocate interrupt routes.
 */
int et_gpio_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_gpio_service_t *service = (et_gpio_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_gpio_service_init(service, instance_id, context->irq_manager, context->irq_priority) !=
        0)
    {
        return -1;
    }

    *descriptor = et_gpio_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
