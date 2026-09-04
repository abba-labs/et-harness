#include "et_gpio_wrap.h"

/**
 * @file et_gpio_wrap.c
 * @brief Map stable board pin/function IDs to the selected GPIO Driver operations.
 */

#include <stddef.h>

#include "et6x_gpio.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_gpio_id_t gpio_id;
    GPIO_PinNumber physical_pin;
    uint8_t gpio_function;
    et_gpio_function_id_t alternate_function_id;
    uint8_t alternate_function;
} et_gpio_wrap_mapping_t;

static const et_gpio_wrap_mapping_t gpio_mappings[] = ET_CHIP_GPIO_MAP_TABLE;

/** Full signal identity prevents a valid pin from selecting the wrong peripheral instance. */
typedef struct
{
    et_gpio_id_t gpio_id;
    et_gpio_function_id_t function_id;
    uint16_t instance_id;
    GPIO_PinNumber physical_pin;
    uint8_t physical_function;
} et_gpio_signal_mapping_t;

static const et_gpio_signal_mapping_t signal_mappings[] = ET_CHIP_GPIO_SIGNAL_MAP_TABLE;

/**
 * @brief Find the exact logical signal route in the chip mapping.
 * @param[in] gpio_id Logical pad identity.
 * @param[in] function_id Stable signal kind, independent of mux encoding.
 * @param[in] instance_id Logical peripheral instance owning the signal.
 * @return Immutable mapping row, or NULL when the combination is unsupported.
 * @note Performs no hardware access; legacy UART mapping remains unchanged.
 */
static const et_gpio_signal_mapping_t *
find_signal(et_gpio_id_t gpio_id, et_gpio_function_id_t function_id, uint16_t instance_id)
{
    size_t index;

    for (index = 0u; index < sizeof(signal_mappings) / sizeof(signal_mappings[0]); ++index)
    {
        const et_gpio_signal_mapping_t *mapping = &signal_mappings[index];

        if ((mapping->gpio_id == gpio_id) && (mapping->function_id == function_id) &&
            (mapping->instance_id == instance_id))
        {
            return mapping;
        }
    }

    return NULL;
}

/* Chip pin and alternate-function facts are confined to the generated map. */

/**
 * @brief Normalize one GPIO Driver result into the stable Wrap status namespace.
 *
 * @param[in] status GPIO Driver status returned by the selected chip SDK.
 *
 * @note This helper translates status values only and does not access GPIO hardware or mapping state.
 *
 * @return Stable Wrap status corresponding to the Driver result.
 */
static et_wrap_status_t map_driver_status(DRV_Status status)
{
    switch (status)
    {
        case DRV_OK:
        {
            return ET_WRAP_STATUS_OK;
        }

        case DRV_PARAM_ERR:
        case DRV_INVALID:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        case DRV_TIMEOUT:
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        case DRV_BUSY:
        {
            return ET_WRAP_STATUS_BUSY;
        }

        case DRV_ERROR:
        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Resolve one stable logical GPIO identifier to the selected physical pin.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[out] physical_pin Selected chip Driver pin selector.
 *
 * @note This helper reads compile-time Chip Config mapping data only and performs no GPIO/IOMUX action.
 *
 * @return ET_WRAP_STATUS_OK when a pin mapping exists.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the logical GPIO is absent on this chip.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when physical_pin is NULL.
 */
static et_wrap_status_t map_gpio(et_gpio_id_t gpio_id, GPIO_PinNumber *physical_pin)
{
    size_t index;

    if (physical_pin == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < (sizeof(gpio_mappings) / sizeof(gpio_mappings[0])); ++index)
    {
        if (gpio_mappings[index].gpio_id == gpio_id)
        {
            *physical_pin = gpio_mappings[index].physical_pin;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Translate one stable GPIO function into the selected physical pin and mux selector.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[in] function_id Stable GPIO or alternate-function identifier.
 * @param[out] physical_pin Selected chip Driver pin selector.
 * @param[out] physical_function Selected chip Driver mux value.
 *
 * @note GPIO and the one published alternate function are selected entirely from Chip Config facts.
 *       No pad or mux hardware is changed by this helper.
 *
 * @return ET_WRAP_STATUS_OK when the logical pin/function pair is supported.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the pair is absent on this chip.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when an output pointer is NULL.
 */
static et_wrap_status_t map_gpio_function(et_gpio_id_t gpio_id, et_gpio_function_id_t function_id,
                                          GPIO_PinNumber *physical_pin, uint8_t *physical_function)
{
    size_t index;

    if ((physical_pin == NULL) || (physical_function == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < (sizeof(gpio_mappings) / sizeof(gpio_mappings[0])); ++index)
    {
        if (gpio_mappings[index].gpio_id != gpio_id)
        {
            continue;
        }

        *physical_pin = gpio_mappings[index].physical_pin;

        if (function_id == ET_GPIO_FUNCTION_GPIO)
        {
            *physical_function = gpio_mappings[index].gpio_function;

            return ET_WRAP_STATUS_OK;
        }

        if (function_id == gpio_mappings[index].alternate_function_id)
        {
            *physical_function = gpio_mappings[index].alternate_function;

            return ET_WRAP_STATUS_OK;
        }

        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Configure one logical GPIO's default pad state and requested mux function.
 *
 * @param[in] config Versioned chip-neutral GPIO configuration.
 *
 * @note This function changes GPIO pad and mux hardware through the selected GPIO Driver. Versioned
 *       flags other than zero are rejected instead of silently inferring unsupported behavior.
 *
 * @return Stable Wrap status for config validation, mapping, pad configuration or mux configuration.
 */
et_wrap_status_t et_gpio_wrap_configure(const et_gpio_wrap_config_t *config)
{
    GPIO_PinNumber physical_pin;
    uint8_t physical_function;
    IOC_Init_TypeDef pad_config;
    et_wrap_status_t status;

    if ((config == NULL) || (config->struct_size < ET_GPIO_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_GPIO_WRAP_API_VERSION))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (config->flags != 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status =
        map_gpio_function(config->gpio_id, config->function_id, &physical_pin, &physical_function);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    GPIO_initPadConfigStruct(&pad_config);
    status = map_driver_status(GPIO_setPadConfig(physical_pin, &pad_config));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_setPinConfig(physical_pin, physical_function));
}

/**
 * @brief Validate a logical signal selection before any Case mutates hardware.
 * @param[in] gpio_id Logical pad selected by the PC connection configuration.
 * @param[in] function_id Stable peripheral signal kind.
 * @param[in] instance_id Logical peripheral instance.
 * @return OK for an exact match, otherwise NOT_SUPPORTED.
 * @note This query only reads constant chip mapping data; it does not configure the pad.
 */
et_wrap_status_t et_gpio_wrap_validate_signal(et_gpio_id_t gpio_id,
                                              et_gpio_function_id_t function_id,
                                              uint16_t instance_id)
{
    return find_signal(gpio_id, function_id, instance_id) == NULL ? ET_WRAP_STATUS_NOT_SUPPORTED
                                                                  : ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure one peripheral signal without configuring the peripheral itself.
 * @param[in] gpio_id Logical pad selected by the PC connection configuration.
 * @param[in] function_id Stable peripheral signal kind.
 * @param[in] instance_id Logical peripheral instance.
 * @return Stable Driver error or NOT_SUPPORTED for an unmapped combination.
 * @note Changes pad and mux through GPIO Driver only. Default pad enables input for role exchange.
 */
et_wrap_status_t et_gpio_wrap_configure_signal(et_gpio_id_t gpio_id,
                                               et_gpio_function_id_t function_id,
                                               uint16_t instance_id)
{
    const et_gpio_signal_mapping_t *mapping = find_signal(gpio_id, function_id, instance_id);
    IOC_Init_TypeDef pad;
    et_wrap_status_t status;

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    GPIO_initPadConfigStruct(&pad);
    status = map_driver_status(GPIO_setPadConfig(mapping->physical_pin, &pad));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_setPinConfig(mapping->physical_pin, mapping->physical_function));
}

/**
 * @brief Set the input/output direction of one logical GPIO pin.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[in] direction Chip-neutral input or output direction.
 *
 * @note This function changes GPIO direction hardware only after logical-to-physical mapping. It does
 *       not change pin mux or output value.
 *
 * @return Stable Wrap status for mapping, direction validation or Driver execution.
 */
et_wrap_status_t et_gpio_wrap_set_direction(et_gpio_id_t gpio_id,
                                            et_gpio_wrap_direction_t direction)
{
    GPIO_PinNumber physical_pin;
    GPIO_DIR_TypeDef driver_direction;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    switch (direction)
    {
        case ET_GPIO_WRAP_DIRECTION_OUTPUT:
        {
            driver_direction = GPIO_DIR_OUT;
            break;
        }

        case ET_GPIO_WRAP_DIRECTION_INPUT:
        {
            driver_direction = GPIO_DIR_IN;
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    return map_driver_status(GPIO_setPortDirectionMode(physical_pin, driver_direction));
}

/**
 * @brief Read one logical GPIO pin and normalize its value to canonical Boolean form.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[out] value Canonical 0/1 pin state.
 *
 * @note This function reads GPIO hardware only; it does not clear interrupt status or change pin state.
 *
 * @return Stable Wrap status for pointer validation, pin mapping and read completion.
 */
et_wrap_status_t et_gpio_wrap_read(et_gpio_id_t gpio_id, uint8_t *value)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *value = 0u;
    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    *value = (GPIO_readPin(physical_pin) == SET) ? 1u : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Drive one logical GPIO output to a canonical Boolean value.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[in] value Canonical 0/1 output value.
 *
 * @note This function atomically changes GPIO output hardware. It does not change pin direction or mux.
 *
 * @return Stable Wrap status for Boolean validation, pin mapping and atomic Driver write.
 */
et_wrap_status_t et_gpio_wrap_write(et_gpio_id_t gpio_id, uint8_t value)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    if (value > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_writePinAtomic(physical_pin, (value != 0u) ? SET : RESET));
}

/**
 * @brief Atomically toggle one logical GPIO output.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 *
 * @note This function changes GPIO output hardware only. Current direction/mux configuration is not modified.
 *
 * @return Stable Wrap status for pin mapping and atomic Driver toggle.
 */
et_wrap_status_t et_gpio_wrap_toggle(et_gpio_id_t gpio_id)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_togglePinAtomic(physical_pin));
}

/**
 * @brief Configure edge or level interrupt triggering for one logical GPIO.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[in] trigger Chip-neutral high/low level or rising/falling edge trigger.
 *
 * @note This function changes GPIO interrupt-trigger hardware only. It does not enable the interrupt
 *       source or bind a CPU IRQ callback.
 *
 * @return Stable Wrap status for mapping, trigger validation and Driver configuration.
 */
et_wrap_status_t et_gpio_wrap_configure_interrupt(et_gpio_id_t gpio_id,
                                                  et_gpio_wrap_interrupt_trigger_t trigger)
{
    GPIO_PinNumber physical_pin;
    GPIO_INT_Config_TypeDef driver_config;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    switch (trigger)
    {
        case ET_GPIO_WRAP_INTERRUPT_HIGH_LEVEL:
        {
            driver_config.mode = GPIO_INT_TYPE_LEVEL;
            driver_config.polarity = GPIO_INT_POL_HIGH_RISING;
            break;
        }

        case ET_GPIO_WRAP_INTERRUPT_LOW_LEVEL:
        {
            driver_config.mode = GPIO_INT_TYPE_LEVEL;
            driver_config.polarity = GPIO_INT_POL_LOW_FALLING;
            break;
        }

        case ET_GPIO_WRAP_INTERRUPT_RISING_EDGE:
        {
            driver_config.mode = GPIO_INT_TYPE_EDGE;
            driver_config.polarity = GPIO_INT_POL_HIGH_RISING;
            break;
        }

        case ET_GPIO_WRAP_INTERRUPT_FALLING_EDGE:
        {
            driver_config.mode = GPIO_INT_TYPE_EDGE;
            driver_config.polarity = GPIO_INT_POL_LOW_FALLING;
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    return map_driver_status(GPIO_setInterruptType(physical_pin, &driver_config));
}

/**
 * @brief Enable the previously configured interrupt source for one logical GPIO.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 *
 * @note This function changes GPIO peripheral interrupt-enable hardware only. CPU IRQ routing remains
 *       owned by IRQ Manager/IRQ Wrap.
 *
 * @return Stable Wrap status for pin mapping and Driver enable.
 */
et_wrap_status_t et_gpio_wrap_enable_interrupt(et_gpio_id_t gpio_id)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_enableInterrupt(physical_pin));
}

/**
 * @brief Disable the GPIO peripheral interrupt source for one logical pin.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 *
 * @note This function changes GPIO peripheral interrupt-enable hardware only and does not clear
 *       pending status or unbind CPU IRQ routing.
 *
 * @return Stable Wrap status for pin mapping and Driver disable.
 */
et_wrap_status_t et_gpio_wrap_disable_interrupt(et_gpio_id_t gpio_id)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_disableInterrupt(physical_pin));
}

/**
 * @brief Read whether one logical GPIO currently reports pending interrupt status.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 * @param[out] pending Canonical 0/1 pending-state observation.
 *
 * @note This function reads GPIO interrupt-status hardware only and does not acknowledge/clear it.
 *
 * @return Stable Wrap status for pointer validation, pin mapping and status read.
 */
et_wrap_status_t et_gpio_wrap_get_interrupt_status(et_gpio_id_t gpio_id, uint8_t *pending)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    if (pending == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *pending = 0u;
    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    *pending = (GPIO_getInterruptStatus(physical_pin) == SET) ? 1u : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear the pending GPIO interrupt status of one logical pin.
 *
 * @param[in] gpio_id Stable logical GPIO identifier.
 *
 * @note This function acknowledges GPIO peripheral interrupt-status hardware only. Source enable and
 *       CPU IRQ routing remain unchanged.
 *
 * @return Stable Wrap status for pin mapping and Driver clear operation.
 */
et_wrap_status_t et_gpio_wrap_clear_interrupt(et_gpio_id_t gpio_id)
{
    GPIO_PinNumber physical_pin;
    et_wrap_status_t status;

    status = map_gpio(gpio_id, &physical_pin);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(GPIO_clearInterruptStatus(physical_pin));
}
