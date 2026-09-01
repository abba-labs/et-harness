#include <stdint.h>
#include <string.h>

#if defined(ET_MANUAL_TEST_ENABLE)

#include "et_manual_test.h"

#else

/**
 * @file main.c
 * @brief Board-selected startup and non-blocking firmware control loop.
 *
 * This file composes common components only. IP test behavior is reached later
 * through PC command -> Service -> Wrap -> chip Driver.
 */

#include "et_control_uart.h"
#include "et_cortex_wrap.h"
#include "et_gpio_wrap.h"
#include "et_irq_wrap.h"
#include "et_board_config_contract.h"
#include "et_runtime.h"
#include "et_service_manifest.h"
#include "et_services.h"
#include "et_system_wrap.h"
#include "et_uart_wrap.h"

#endif

#if !defined(ET_MANUAL_TEST_ENABLE)

static et_runtime_t runtime;
static et_services_t services;
static et_control_uart_t control_uart;
static uint8_t control_rx_storage[ET_CONTROL_UART_RX_BUFFER_SIZE];
static uint8_t control_tx_storage[ET_CONTROL_UART_TX_BUFFER_SIZE];

typedef struct
{
    et_gpio_id_t gpio_id;
    et_gpio_function_id_t function_id;
} et_test_uart_pin_config_t;

static const et_test_uart_pin_config_t test_uart_pins[] = {ET_TEST_UART_PIN_CONFIGS};

/**
 * @brief Stop firmware deterministically after an unrecoverable startup failure.
 *
 * @note This function intentionally never returns and performs no additional cleanup or hardware
 *       mutation. The failed startup stage is expected to have left the platform unusable.
 */
static void stop_on_startup_error(void)
{
    for (;;)
    {
    }
}

/**
 * @brief Build the dedicated control UART configuration from board-owned constants.
 *
 * @param[out] config Control UART configuration populated for later transport initialization.
 *
 * @note This helper only constructs software configuration and binds static ring storage. It does
 *       not configure GPIO, UART or interrupt-controller hardware.
 */
static void make_control_uart_config(et_control_uart_config_t *config)
{
    memset(config, 0, sizeof(*config));

    config->uart.struct_size = (uint16_t)sizeof(config->uart);
    config->uart.api_version = ET_UART_WRAP_API_VERSION;
    config->uart.uart_id = (et_uart_id_t)ET_CONTROL_UART_ID;
    config->uart.baudrate = ET_CONTROL_UART_BAUDRATE;
    config->uart.data_bits = ET_CONTROL_UART_DATA_BITS;
    config->uart.stop_bits = ET_CONTROL_UART_STOP_BITS;
    config->uart.parity = ET_CONTROL_UART_PARITY;

    config->tx_gpio.struct_size = (uint16_t)sizeof(config->tx_gpio);
    config->tx_gpio.api_version = ET_GPIO_WRAP_API_VERSION;
    config->tx_gpio.gpio_id = (et_gpio_id_t)ET_CONTROL_UART_TX_GPIO_ID;
    config->tx_gpio.function_id = (et_gpio_function_id_t)ET_CONTROL_UART_TX_FUNCTION_ID;

    config->rx_gpio.struct_size = (uint16_t)sizeof(config->rx_gpio);
    config->rx_gpio.api_version = ET_GPIO_WRAP_API_VERSION;
    config->rx_gpio.gpio_id = (et_gpio_id_t)ET_CONTROL_UART_RX_GPIO_ID;
    config->rx_gpio.function_id = (et_gpio_function_id_t)ET_CONTROL_UART_RX_FUNCTION_ID;

    config->irq_priority = ET_CONTROL_UART_IRQ_PRIORITY;
    config->rx_mode = ET_CONTROL_UART_RX_MODE;
    config->tx_mode = ET_CONTROL_UART_TX_MODE;
    config->rx_storage = control_rx_storage;
    config->rx_capacity = sizeof(control_rx_storage);
    config->tx_storage = control_tx_storage;
    config->tx_capacity = sizeof(control_tx_storage);
}

/**
 * @brief Apply every board-selected GPIO route required by test UART instances.
 *
 * @note This function configures GPIO/IOMUX hardware through the GPIO Wrap. It stops on the first
 *       route that cannot be applied and does not attempt to undo routes already configured.
 *
 * @return 0 when every test UART pin route is configured successfully.
 * @return -1 when any board-selected GPIO route cannot be configured.
 */
static int configure_test_uart_pins(void)
{
    et_gpio_wrap_config_t config;
    size_t index;

    for (index = 0u; index < (sizeof(test_uart_pins) / sizeof(test_uart_pins[0])); ++index)
    {
        memset(&config, 0, sizeof(config));
        config.struct_size = (uint16_t)sizeof(config);
        config.api_version = ET_GPIO_WRAP_API_VERSION;
        config.gpio_id = test_uart_pins[index].gpio_id;
        config.function_id = test_uart_pins[index].function_id;

        if (et_gpio_wrap_configure(&config) != ET_WRAP_STATUS_OK)
        {
            return -1;
        }
    }

    return 0;
}

#endif

/**
 * @brief Initialize the platform and run the allocation-free firmware protocol loop.
 *
 * @note Startup follows five explicit phases: platform prerequisites, Runtime creation, control
 *       transport initialization, Service registration, then cooperative polling. IP test behavior
 *       remains behind Service -> Wrap -> Driver and ISR work stays bounded.
 *
 * @return This function does not return during normal firmware operation.
 */
int main(void)
{
#if defined(ET_MANUAL_TEST_ENABLE)

    return et_manual_test_run();

#else

    et_control_uart_config_t control_uart_config;
    et_runtime_config_t runtime_config;
    et_services_config_t services_config;

    /* Phase 1: establish core clock, test-IP clocks, vector table and board pins. */
    if (((ET_CORTEX_ENABLE_ICACHE != 0u) &&
         (et_cortex_wrap_enable_instruction_cache() != ET_WRAP_STATUS_OK)) ||
        ((ET_SYSTEM_UPDATE_CORE_CLOCK != 0u) &&
         (et_system_wrap_update_core_clock() != ET_WRAP_STATUS_OK)) ||
        (et_service_manifest_prepare() != 0) || (et_irq_wrap_init() != ET_WRAP_STATUS_OK) ||
        (configure_test_uart_pins() != 0))
    {
        stop_on_startup_error();
    }

    /* Phase 2: create common Runtime before binding transport or IP callbacks. */
    memset(&runtime_config, 0, sizeof(runtime_config));
    /*
     * No session exists at boot. Framework HELLO proposes a fresh nonzero
     * session ID, which the protocol binds after a successful response.
     */
    runtime_config.session_id = 0u;
    runtime_config.session_open_service_id = ET_FRAMEWORK_SERVICE_ID;
    runtime_config.session_open_command_id = ET_FRAMEWORK_COMMAND_HELLO;
    runtime_config.io = et_control_uart_protocol_io(&control_uart);

    if (et_runtime_init(&runtime, &runtime_config) != 0)
    {
        stop_on_startup_error();
    }

    /* Phase 3: initialize the dedicated PC protocol transport. */
    make_control_uart_config(&control_uart_config);
    control_uart_config.irq_manager = et_runtime_irqs(&runtime);

    if (et_control_uart_init(&control_uart, &control_uart_config) != 0)
    {
        stop_on_startup_error();
    }

    /* Phase 4: register framework and board-selected IP command endpoints. */
    memset(&services_config, 0, sizeof(services_config));
    services_config.framework.chip_id = ET_FIRMWARE_CHIP_ID;
    services_config.framework.firmware_build_id = ET_FIRMWARE_BUILD_ID;
    services_config.framework.reset_reason_supported = 0u;
    services_config.irq_manager = et_runtime_irqs(&runtime);
    services_config.groups = et_service_manifest_get(&services_config.group_count);

    if ((et_services_register_all(&services, &services_config, et_runtime_services(&runtime),
                                  et_runtime_protocol_stats(&runtime)) != 0) ||
        (et_control_uart_open(&control_uart) != 0) || (et_runtime_start(&runtime) != 0))
    {
        et_control_uart_close(&control_uart);
        stop_on_startup_error();
    }

    /* Phase 5: cooperative loop; ISR work remains bounded and parsing runs here. */
    for (;;)
    {
        size_t consumed;

        et_control_uart_poll(&control_uart);
        (void)et_runtime_poll(&runtime);

        if (et_control_uart_take_rx_idle(&control_uart) != 0)
        {
            /*
             * RX IDLE can arrive after a complete long frame has already
             * reached the ring. Drain every queued chunk before deciding
             * whether the parser contains a truly truncated frame.
             */
            do
            {
                consumed = et_runtime_poll(&runtime);
            } while (consumed != 0u);

            if (et_runtime_rx_incomplete(&runtime) != 0)
            {
                et_runtime_reset_rx(&runtime);
            }
        }
    }

#endif
}
