#ifndef ET_GPIO_WRAP_H
#define ET_GPIO_WRAP_H

/**
 * @file et_gpio_wrap.h
 * @brief Stable logical-pin configuration and GPIO operation bridge.
 *
 * Board configuration selects logical pin/function IDs; chip pinmux and GPIO
 * Driver types remain private to the implementation.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_wrap_status.h"

#define ET_GPIO_WRAP_API_VERSION 1u
#define ET_GPIO_WRAP_CONFIG_RESERVED_WORDS 4u

/** Stable board-level pin identity, not a port register or bit mask. */
typedef uint16_t et_gpio_id_t;
/** Stable board-level alternate-function identity. */
typedef uint16_t et_gpio_function_id_t;

typedef enum
{
    ET_GPIO_FUNCTION_GPIO = 0u,
    ET_GPIO_FUNCTION_UART_TX = 1u,
    ET_GPIO_FUNCTION_UART_RX = 2u,
    ET_GPIO_FUNCTION_SPI_CLK = 3u,
    ET_GPIO_FUNCTION_SPI_CS = 4u,
    ET_GPIO_FUNCTION_SPI_MOSI = 5u,
    ET_GPIO_FUNCTION_SPI_MISO = 6u
} et_gpio_function_t;

typedef enum
{
    ET_GPIO_WRAP_DIRECTION_OUTPUT = 0u,
    ET_GPIO_WRAP_DIRECTION_INPUT = 1u
} et_gpio_wrap_direction_t;

typedef enum
{
    ET_GPIO_WRAP_INTERRUPT_HIGH_LEVEL = 0u,
    ET_GPIO_WRAP_INTERRUPT_LOW_LEVEL = 1u,
    ET_GPIO_WRAP_INTERRUPT_RISING_EDGE = 2u,
    ET_GPIO_WRAP_INTERRUPT_FALLING_EDGE = 3u
} et_gpio_wrap_interrupt_trigger_t;

typedef struct
{
    uint16_t struct_size;              /**< Caller-visible structure size. */
    uint16_t api_version;              /**< Must equal ET_GPIO_WRAP_API_VERSION. */
    et_gpio_id_t gpio_id;              /**< Logical board pin. */
    et_gpio_function_id_t function_id; /**< Requested pin function. */
    uint32_t flags;                    /**< Reserved function options; unsupported bits rejected. */
    uint32_t reserved[ET_GPIO_WRAP_CONFIG_RESERVED_WORDS]; /**< Must be zero. */
} et_gpio_wrap_config_t;

#define ET_GPIO_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_gpio_wrap_config_t, reserved))

/** Validate and apply one board pin/function mapping. */
et_wrap_status_t et_gpio_wrap_configure(const et_gpio_wrap_config_t *config);
/** Check a complete logical signal route without changing hardware. */
et_wrap_status_t et_gpio_wrap_validate_signal(et_gpio_id_t gpio_id,
                                              et_gpio_function_id_t function_id,
                                              uint16_t instance_id);
/** Configure a validated signal through the GPIO Driver, without touching its peripheral. */
et_wrap_status_t et_gpio_wrap_configure_signal(et_gpio_id_t gpio_id,
                                               et_gpio_function_id_t function_id,
                                               uint16_t instance_id);
/** Select GPIO input or output direction for one logical pin. */
et_wrap_status_t et_gpio_wrap_set_direction(et_gpio_id_t gpio_id,
                                            et_gpio_wrap_direction_t direction);
/** Read one GPIO input as normalized 0 or 1. */
et_wrap_status_t et_gpio_wrap_read(et_gpio_id_t gpio_id, uint8_t *value);
/** Drive one GPIO output using normalized 0 or 1. */
et_wrap_status_t et_gpio_wrap_write(et_gpio_id_t gpio_id, uint8_t value);
/** Invert the current output latch of one GPIO. */
et_wrap_status_t et_gpio_wrap_toggle(et_gpio_id_t gpio_id);
/** Configure one GPIO interrupt trigger without enabling it. */
et_wrap_status_t et_gpio_wrap_configure_interrupt(et_gpio_id_t gpio_id,
                                                  et_gpio_wrap_interrupt_trigger_t trigger);
/** Enable the configured GPIO interrupt source. */
et_wrap_status_t et_gpio_wrap_enable_interrupt(et_gpio_id_t gpio_id);
/** Disable the GPIO interrupt source. */
et_wrap_status_t et_gpio_wrap_disable_interrupt(et_gpio_id_t gpio_id);
/** Read pending state without clearing it. */
et_wrap_status_t et_gpio_wrap_get_interrupt_status(et_gpio_id_t gpio_id, uint8_t *pending);
/** Clear pending state for one logical GPIO. */
et_wrap_status_t et_gpio_wrap_clear_interrupt(et_gpio_id_t gpio_id);

#endif
