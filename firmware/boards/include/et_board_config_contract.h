#ifndef ET_BOARD_CONFIG_CONTRACT_H
#define ET_BOARD_CONFIG_CONTRACT_H

#include "et_control_uart.h"
#include "et_cortex_wrap.h"
#include "et_crg_wrap.h"
#include "et_gpio_wrap.h"
#include "et_system_wrap.h"
#include "et_uart_wrap.h"

/*
 * The build target contributes exactly one directory containing
 * et_board_config.h. Board configuration is compile-time data only; there is
 * no Board runtime interface.
 */
#include "et_board_config.h"

#ifndef ET_SYSTEM_UPDATE_CORE_CLOCK
#error "Board config must define ET_SYSTEM_UPDATE_CORE_CLOCK"
#endif
#ifndef ET_CORTEX_ENABLE_ICACHE
#error "Board config must define ET_CORTEX_ENABLE_ICACHE"
#endif
#ifndef ET_CONTROL_UART_ID
#error "Board config must define ET_CONTROL_UART_ID"
#endif
#ifndef ET_CONTROL_UART_BAUDRATE
#error "Board config must define ET_CONTROL_UART_BAUDRATE"
#endif
#ifndef ET_CONTROL_UART_DATA_BITS
#error "Board config must define ET_CONTROL_UART_DATA_BITS"
#endif
#ifndef ET_CONTROL_UART_PARITY
#error "Board config must define ET_CONTROL_UART_PARITY"
#endif
#ifndef ET_CONTROL_UART_STOP_BITS
#error "Board config must define ET_CONTROL_UART_STOP_BITS"
#endif
#ifndef ET_CONTROL_UART_TX_GPIO_ID
#error "Board config must define ET_CONTROL_UART_TX_GPIO_ID"
#endif
#ifndef ET_CONTROL_UART_TX_FUNCTION_ID
#error "Board config must define ET_CONTROL_UART_TX_FUNCTION_ID"
#endif
#ifndef ET_CONTROL_UART_RX_GPIO_ID
#error "Board config must define ET_CONTROL_UART_RX_GPIO_ID"
#endif
#ifndef ET_CONTROL_UART_RX_FUNCTION_ID
#error "Board config must define ET_CONTROL_UART_RX_FUNCTION_ID"
#endif
#ifndef ET_CONTROL_UART_IRQ_PRIORITY
#error "Board config must define ET_CONTROL_UART_IRQ_PRIORITY"
#endif
#ifndef ET_CONTROL_UART_RX_MODE
#error "Board config must define ET_CONTROL_UART_RX_MODE"
#endif
#ifndef ET_CONTROL_UART_TX_MODE
#error "Board config must define ET_CONTROL_UART_TX_MODE"
#endif
#ifndef ET_CONTROL_UART_RX_BUFFER_SIZE
#error "Board config must define ET_CONTROL_UART_RX_BUFFER_SIZE"
#endif
#ifndef ET_CONTROL_UART_TX_BUFFER_SIZE
#error "Board config must define ET_CONTROL_UART_TX_BUFFER_SIZE"
#endif
#ifndef ET_TEST_UART_PIN_CONFIGS
#error "Board config must define ET_TEST_UART_PIN_CONFIGS"
#endif
#ifndef ET_TEST_UART_INSTANCE_IDS
#error "Board config must define ET_TEST_UART_INSTANCE_IDS"
#endif
#ifndef ET_TEST_DMA_INSTANCE_IDS
#error "Board config must define ET_TEST_DMA_INSTANCE_IDS"
#endif
#ifndef ET_TEST_CRC_INSTANCE_IDS
#error "Board config must define ET_TEST_CRC_INSTANCE_IDS"
#endif
#ifndef ET_TEST_AES_INSTANCE_IDS
#error "Board config must define ET_TEST_AES_INSTANCE_IDS"
#endif
#ifndef ET_TEST_FMAC_INSTANCE_IDS
#error "Board config must define ET_TEST_FMAC_INSTANCE_IDS"
#endif
#ifndef ET_TEST_CORDIC_INSTANCE_IDS
#error "Board config must define ET_TEST_CORDIC_INSTANCE_IDS"
#endif
#ifndef ET_TEST_WDG_INSTANCE_IDS
#error "Board config must define ET_TEST_WDG_INSTANCE_IDS"
#endif
#ifndef ET_TEST_CPU_INSTANCE_IDS
#error "Board config must define ET_TEST_CPU_INSTANCE_IDS"
#endif
#ifndef ET_TEST_STIMER_INSTANCE_IDS
#error "Board config must define ET_TEST_STIMER_INSTANCE_IDS"
#endif
#ifndef ET_TEST_SPINLOCK_INSTANCE_IDS
#error "Board config must define ET_TEST_SPINLOCK_INSTANCE_IDS"
#endif
#ifndef ET_TEST_UART_CAPTURE_IRQ_PRIORITY
#error "Board config must define ET_TEST_UART_CAPTURE_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_CRC_IRQ_PRIORITY
#error "Board config must define ET_TEST_CRC_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_AES_IRQ_PRIORITY
#error "Board config must define ET_TEST_AES_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_FMAC_IRQ_PRIORITY
#error "Board config must define ET_TEST_FMAC_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_CORDIC_IRQ_PRIORITY
#error "Board config must define ET_TEST_CORDIC_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_WDG_IRQ_PRIORITY
#error "Board config must define ET_TEST_WDG_IRQ_PRIORITY"
#endif
#ifndef ET_TEST_STIMER_IRQ_PRIORITY
#error "Board config must define ET_TEST_STIMER_IRQ_PRIORITY"
#endif

#endif
