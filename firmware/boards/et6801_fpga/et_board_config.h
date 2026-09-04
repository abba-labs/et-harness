#ifndef ET6801_FPGA_BOARD_CONFIG_H
#define ET6801_FPGA_BOARD_CONFIG_H

/**
 * @file et_board_config.h
 * @brief ET6801 FPGA board facts consumed by common firmware startup.
 */

/* Firmware identity returned by Framework HELLO/VERSION commands. */
#define ET_FIRMWARE_CHIP_ID "et6801"
#define ET_FIRMWARE_BUILD_ID "et6801-fpga-common-v0.1"

/* Core startup policy for this board target. */
#define ET_SYSTEM_UPDATE_CORE_CLOCK 1u
#define ET_CORTEX_ENABLE_ICACHE 1u

/* Dedicated PC protocol UART; this instance is not a test UART. */
#define ET_CONTROL_UART_ID 0u
#define ET_CONTROL_UART_BAUDRATE 115200u
#define ET_CONTROL_UART_DATA_BITS 8u
#define ET_CONTROL_UART_PARITY ET_UART_WRAP_PARITY_NONE
#define ET_CONTROL_UART_STOP_BITS 1u
#define ET_CONTROL_UART_RX_MODE ET_CONTROL_UART_MODE_IRQ
#define ET_CONTROL_UART_TX_MODE ET_CONTROL_UART_MODE_POLLING
#define ET_CONTROL_UART_IRQ_PRIORITY 5u
#define ET_CONTROL_UART_RX_BUFFER_SIZE 8192u
#define ET_CONTROL_UART_TX_BUFFER_SIZE 8192u

/* Board pinmux route for the dedicated PC protocol UART. */
#define ET_CONTROL_UART_TX_GPIO_ID 12u
#define ET_CONTROL_UART_TX_FUNCTION_ID ET_GPIO_FUNCTION_UART_TX
#define ET_CONTROL_UART_RX_GPIO_ID 13u
#define ET_CONTROL_UART_RX_FUNCTION_ID ET_GPIO_FUNCTION_UART_RX

/* UART pins and logical IP instances exposed to automated tests. */
#define ET_TEST_UART_PIN_CONFIGS \
    {44u, ET_GPIO_FUNCTION_UART_TX}, \
    {45u, ET_GPIO_FUNCTION_UART_RX}, \
    {8u, ET_GPIO_FUNCTION_UART_TX}, \
    {9u, ET_GPIO_FUNCTION_UART_RX}

#define ET_TEST_UART_INSTANCE_IDS 1u, 2u
#define ET_TEST_DMA_INSTANCE_IDS 0u, 1u
#define ET_TEST_CRC_INSTANCE_IDS 0u
#define ET_TEST_AES_INSTANCE_IDS 0u
#define ET_TEST_FMAC_INSTANCE_IDS 0u
#define ET_TEST_CORDIC_INSTANCE_IDS 0u
#define ET_TEST_WDG_INSTANCE_IDS 0u, 1u
#define ET_TEST_CPU_INSTANCE_IDS 0u
/* Managed test IRQ priorities are board policy, not Service constants. */
#define ET_TEST_UART_CAPTURE_IRQ_PRIORITY 3u
#define ET_TEST_CRC_IRQ_PRIORITY 3u
#define ET_TEST_AES_IRQ_PRIORITY 3u
#define ET_TEST_FMAC_IRQ_PRIORITY 3u
#define ET_TEST_CORDIC_IRQ_PRIORITY 3u
#define ET_TEST_WDG_IRQ_PRIORITY 3u
#define ET_TEST_STIMER_INSTANCE_IDS 0u, 1u
#define ET_TEST_SPINLOCK_INSTANCE_IDS 0u
/* Logical IPCM controller and default NVIC capture priority; no mailbox Case policy. */
#define ET_TEST_IPCM_INSTANCE_IDS 0u
#define ET_TEST_IPCM_IRQ_PRIORITY 3u
/* One logical system counter; both register views refer to this instance. */
#define ET_TEST_SYSCNT_INSTANCE_IDS 0u

/* Publish selectable SPI instances; PC connection YAML chooses the actual pair. */
#define ET_TEST_SPI_INSTANCE_IDS 0u, 1u, 2u, 3u
#define ET_TEST_SPI_IRQ_PRIORITY 3u
/* One GPIO routing service; physical pad and peripheral instance are request fields. */
#define ET_TEST_GPIO_INSTANCE_IDS 0u
#define ET_TEST_STIMER_IRQ_PRIORITY 3u
#endif
