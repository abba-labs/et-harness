#include "et_manual_test.h"

#include <stddef.h>
#include <stdint.h>

#include "et6x_crg.h"
#include "et6x_gpio.h"
#include "et6x_uart.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"
#include "system_et6x.h"

static void configure_pin(GPIO_PinNumber pin, uint8_t mode)
{
    IOC_Init_TypeDef config;

    GPIO_initPadConfigStruct(&config);
    (void)GPIO_setPadConfig(pin, &config);
    (void)GPIO_setPinConfig(pin, mode);
}

static void initialize_uart(UART_Type *uart, uint32_t baudrate)
{
    UART_ConfigParams config;

    UART_initConfigParams(&config);
    config.baudRate = baudrate;
    config.wordLength = UART_WORDLENGTH_8B;
    config.stopBits = UART_STOPBITS_1;
    config.parity = UART_PARITY_NONE;
    config.mode = UART_MODE_NORMAL;
    config.DMAMode = UART_DMA_DISABLE;
    config.irqEnableFlag = UART_IT_NONE;
    (void)UART_config(uart, &config);
}

static void initialize_hardware(void)
{
    SystemCoreClockUpdate();
    SCB_EnableICache();

#if !defined(ET_MANUAL_CORE1_SMOKE_ONLY)
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_UART_DUT_CLOCK);
    CRG_enablePeripheral(ET_MANUAL_UART_PEER_CLOCK);
    CRG_enablePeripheral(ET_MANUAL_CRC_CLOCK);
    CRG_enablePeripheral(ET_MANUAL_FMAC_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_UART_DUT_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_UART_PEER_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_CRC_CLOCK);
    CRG_lockClockConfig();

    configure_pin(ET_MANUAL_UART_DUT_TX_PIN, ET_MANUAL_UART_DUT_TX_MODE);
    configure_pin(ET_MANUAL_UART_DUT_RX_PIN, ET_MANUAL_UART_DUT_RX_MODE);
    configure_pin(ET_MANUAL_UART_PEER_TX_PIN, ET_MANUAL_UART_PEER_TX_MODE);
    configure_pin(ET_MANUAL_UART_PEER_RX_PIN, ET_MANUAL_UART_PEER_RX_MODE);
#endif

    /* Configure the PC log UART last, matching the proven automated-firmware order. */
    configure_pin(ET_MANUAL_LOG_TX_PIN, ET_MANUAL_LOG_TX_MODE);
    configure_pin(ET_MANUAL_LOG_RX_PIN, ET_MANUAL_LOG_RX_MODE);

    initialize_uart(ET_MANUAL_LOG_UART, ET_MANUAL_LOG_UART_BAUDRATE);
}

static void wait_for_pc_capture(void)
{
    uint8_t trigger = 0u;

    /* Start only after the capture tool is open, so the first evidence line cannot be lost. */
    do
    {
        (void)UART_receive(ET_MANUAL_LOG_UART, &trigger, 1u);
    } while (trigger != ET_MANUAL_LOG_UART_START_TRIGGER);
}

void et_manual_log_text(const char *text)
{
    size_t length = 0u;
    size_t index;

    while (text[length] != '\0')
    {
        ++length;
    }

    /*
     * Match the proven formal control-UART transport: offer one byte only
     * after TEMT is asserted.  The FPGA UART model corrupts long blocking FIFO
     * bursts even though the same UART0 path is stable with this pacing.
     */
    for (index = 0u; index < length; ++index)
    {
        uint32_t wait_count = ET_MANUAL_UART_WAIT_LIMIT;

        while ((UART_getLineStatusFlag(ET_MANUAL_LOG_UART, UART_LINE_STA_TEMT_FLAG) == 0u) &&
               (wait_count > 0u))
        {
            --wait_count;
        }

        if (wait_count == 0u)
        {
            return;
        }

        (void)UART_transmitWithFIFO(ET_MANUAL_LOG_UART, (uint8_t *)&text[index], 1u,
                                    UART_NON_BLOCK_TRANSMIT_FIFO);
    }
}

void et_manual_log_u32(const char *name, uint32_t value)
{
    static const char hex_digits[] = "0123456789ABCDEF";
    char line[48];
    size_t index = 0u;
    uint32_t nibble;
    int shift;

    while ((name[index] != '\0') && (index < 28u))
    {
        line[index] = name[index];
        ++index;
    }

    line[index++] = '=';
    line[index++] = '0';
    line[index++] = 'x';

    for (shift = 28; shift >= 0; shift -= 4)
    {
        nibble = (value >> (uint32_t)shift) & 0x0Fu;
        line[index++] = hex_digits[nibble];
    }

    line[index++] = '\r';
    line[index++] = '\n';
    line[index] = '\0';
    et_manual_log_text(line);
}

void et_manual_log_result(const char *case_id, int result)
{
    et_manual_log_text("[RESULT] case=");
    et_manual_log_text(case_id);
    et_manual_log_text((result == ET_MANUAL_RESULT_PASS) ? " status=PASS\r\n" : " status=FAIL\r\n");
}

int et_manual_test_run(void)
{
    int failures = 0;
    int result;

    initialize_hardware();
    wait_for_pc_capture();
    et_manual_log_text("[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS start\r\n");

#if defined(ET_MANUAL_CORE1_SMOKE_ONLY)
    result = et_manual_dualcore_smoke();
    et_manual_log_result("dualcore_smoke", result);
    failures += result;
#else
    result = et_manual_crg_register_reset_matrix();
    et_manual_log_result("crg_register_reset_matrix", result);
    failures += result;

    result = et_manual_uart_p1_008_framing_error_detection();
    et_manual_log_result("uart_p1_008", result);
    failures += result;

    result = et_manual_uart_p1_012_busy_detect_irq();
    et_manual_log_result("uart_p1_012", result);
    failures += result;

    result = et_manual_uart_p3_009_direct_fifo_access();
    et_manual_log_result("uart_p3_009", result);
    failures += result;

    result = et_manual_crc_p1_011_fifo_threshold();
    et_manual_log_result("crc_p1_011", result);
    failures += result;

    result = et_manual_crc_p1_012_fifo_overflow_recovery();
    et_manual_log_result("crc_p1_012", result);
    failures += result;

    result = et_manual_aes_p1_009_output_conflict();
    et_manual_log_result("aes_p1_009", result);
    failures += result;

    result = et_manual_cordic_p1_003_scale7_arctan_precision();
    et_manual_log_result("cordic_p1_003", result);
    failures += result;

    result = et_manual_cordic_p2_001_dma_mode_equivalence();
    et_manual_log_result("cordic_p2_001", result);
    failures += result;

    result = et_manual_fmac_p1_006_float_overflow_clear();
    et_manual_log_result("fmac_p1_006", result);
    failures += result;

    result = et_manual_fmac_p1_010_negative_status_clear();
    et_manual_log_result("fmac_p1_010", result);
    failures += result;

    result = et_manual_stimer_p1_001_prescaler_ratio();
    et_manual_log_result("stimer_p1_001", result);
    failures += result;

    result = et_manual_stimer_p2_003_debugger_halt_behavior();
    et_manual_log_result("stimer_p2_003", result);
    failures += result;

    result = et_manual_wdg_p1_004_module_reset_and_recovery();
    et_manual_log_result("wdg_p1_004", result);
    failures += result;

    result = et_manual_wdg_p2_001_clock_divider_rate();
    et_manual_log_result("wdg_p2_001", result);
    failures += result;
#endif

    et_manual_log_u32("[OBSERVE] failure_count", (uint32_t)failures);
    et_manual_log_text("[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS end\r\n");

    for (;;)
    {
    }
}
