#include "et_manual_test.h"

#include <stddef.h>
#include <stdint.h>

#include "et6x_crg.h"
#include "et6x_gpio.h"
#include "et6x_uart.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"
#include "system_et6x.h"

#define ET_MANUAL_ARRAY_SIZE(array) (sizeof(array) / sizeof((array)[0]))

typedef int (*et_manual_case_handler_t)(void);

typedef struct
{
    const char *case_id;
    et_manual_case_handler_t handler;
} et_manual_case_entry_t;

typedef struct
{
    const char *ip_name;
    const et_manual_case_entry_t *cases;
    size_t case_count;
} et_manual_ip_entry_t;


/* Comment a Case entry to exclude it from the selected IP. */
static const et_manual_case_entry_t g_dualcore_cases[] = {
    {"dualcore_smoke", et_manual_dualcore_smoke},
};

/* Comment a Case entry to exclude it from the selected IP. */
static const et_manual_case_entry_t g_crg_cases[] = {
    {"crg_register_reset_matrix", et_manual_crg_register_reset_matrix},
};

static const et_manual_case_entry_t g_uart_cases[] = {
    {"uart_p1_008", et_manual_uart_p1_008_framing_error_detection},
    {"uart_p1_012", et_manual_uart_p1_012_busy_detect_irq},
    {"uart_p3_009", et_manual_uart_p3_009_direct_fifo_access},
};

static const et_manual_case_entry_t g_crc_cases[] = {
    {"crc_p1_012", et_manual_crc_p1_012_fifo_overflow_recovery},
};

static const et_manual_case_entry_t g_aes_cases[] = {
    {"aes_p1_009", et_manual_aes_p1_009_output_conflict},
};

static const et_manual_case_entry_t g_cordic_cases[] = {
    {"cordic_p1_003", et_manual_cordic_p1_003_scale7_arctan_precision},
    {"cordic_p2_001", et_manual_cordic_p2_001_dma_mode_equivalence},
};

static const et_manual_case_entry_t g_fmac_cases[] = {
    {"fmac_p1_006", et_manual_fmac_p1_006_float_overflow_clear},
    {"fmac_p1_010", et_manual_fmac_p1_010_negative_status_clear},
};

/*
 * wdg_p0_004与wdg_p1_003都会复位整个SoC，结论只能在复位后的下一次上电读出，
 * 因此同一次构建只选其中一个，避免两者互相重新武装。
 */
static const et_manual_case_entry_t g_wdg_cases[] = {
    //{"wdg_p1_004", et_manual_wdg_p1_004_module_reset_and_recovery},
    //{"wdg_p0_004", et_manual_wdg_p0_004_system_reset_and_record},
    {"wdg_p1_003", et_manual_wdg_p1_003_round_mode_reset},
    //{"wdg_p2_001", et_manual_wdg_p2_001_clock_divider_rate},
};

static const et_manual_case_entry_t g_stimer_cases[] = {
    //{"stimer_p1_001", et_manual_stimer_p1_001_prescaler_ratio},
    {"stimer_p2_003", et_manual_stimer_p2_003_debugger_halt_behavior},
};

/*
 * Comment an IP entry to exclude all of its Cases from this build.  STIMER is
 * kept last because its debugger-dependent Case may halt firmware execution.
 */
static const et_manual_ip_entry_t g_manual_ip_registry[] = {
    //{"crg", g_crg_cases, ET_MANUAL_ARRAY_SIZE(g_crg_cases)},
    //{"uart", g_uart_cases, ET_MANUAL_ARRAY_SIZE(g_uart_cases)},
    //{"crc", g_crc_cases, ET_MANUAL_ARRAY_SIZE(g_crc_cases)},
    //{"aes", g_aes_cases, ET_MANUAL_ARRAY_SIZE(g_aes_cases)},
    //{"cordic", g_cordic_cases, ET_MANUAL_ARRAY_SIZE(g_cordic_cases)},
    //{"fmac", g_fmac_cases, ET_MANUAL_ARRAY_SIZE(g_fmac_cases)},
    {"wdg", g_wdg_cases, ET_MANUAL_ARRAY_SIZE(g_wdg_cases)},
    //{"stimer", g_stimer_cases, ET_MANUAL_ARRAY_SIZE(g_stimer_cases)},
		//{"dualcore", g_dualcore_cases, ET_MANUAL_ARRAY_SIZE(g_dualcore_cases)},
};



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

static int run_registered_ip(const et_manual_ip_entry_t *ip_entry)
{
    size_t case_index;
    int failures = 0;

    et_manual_log_text("[MANUAL] ip=");
    et_manual_log_text(ip_entry->ip_name);
    et_manual_log_text(" start\r\n");

    for (case_index = 0u; case_index < ip_entry->case_count; ++case_index)
    {
        const et_manual_case_entry_t *case_entry = &ip_entry->cases[case_index];
        int result = case_entry->handler();

        et_manual_log_result(case_entry->case_id, result);

        if (result != ET_MANUAL_RESULT_PASS)
        {
            ++failures;
        }
    }

    et_manual_log_text("[MANUAL] ip=");
    et_manual_log_text(ip_entry->ip_name);
    et_manual_log_text(" end\r\n");

    return failures;
}

int et_manual_test_run(void)
{
    size_t ip_index;
    int failures = 0;

    initialize_hardware();
    //wait_for_pc_capture();
    et_manual_log_text("[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS start\r\n");

    for (ip_index = 0u; ip_index < ET_MANUAL_ARRAY_SIZE(g_manual_ip_registry); ++ip_index)
    {
        failures += run_registered_ip(&g_manual_ip_registry[ip_index]);
    }

    et_manual_log_u32("[OBSERVE] failure_count", (uint32_t)failures);
    et_manual_log_text("[MANUAL] suite=ET6801_MANUAL_DIAGNOSTICS end\r\n");

    for (;;)
    {
    }
}
