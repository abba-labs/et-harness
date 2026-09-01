#include <stdint.h>

#include "et6x_crg.h"
#include "et6x_uart.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_uart_pair(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_UART_DUT_CLOCK);
    CRG_enablePeripheral(ET_MANUAL_UART_PEER_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_UART_DUT_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_UART_PEER_CLOCK);
    CRG_lockClockConfig();
}

static void configure_uart(UART_Type *uart, UART_StopBit stop_bits)
{
    UART_ConfigParams config;

    (void)UART_performSoftwareReset(uart);
    UART_initConfigParams(&config);
    config.baudRate = ET_MANUAL_UART_TEST_BAUDRATE;
    config.wordLength = UART_WORDLENGTH_8B;
    config.stopBits = stop_bits;
    config.parity = UART_PARITY_NONE;
    config.mode = UART_MODE_NORMAL;
    config.DMAMode = UART_DMA_DISABLE;
    config.irqEnableFlag = UART_IT_NONE;
    config.TXFIFOThreshold = UART_TXFIFO_THRESHOLD_0BYTES;
    config.RXFIFOThreshold = UART_RXFIFO_THRESHOLD_1BYTES;
    (void)UART_config(uart, &config);
}

int et_manual_uart_p1_008_framing_error_detection(void)
{
    const uint8_t payload[ET_MANUAL_UART_FRAMING_PAYLOAD_SIZE] = {0x55u, 0xAAu, 0x00u, 0xFFu};
    UART_TestInterruptSnapshot_TypeDef snapshot;

    /* 复位：DUT和Peer均从独立硬件状态开始，不继承上一Case的UART配置。 */
    reset_uart_pair();

    et_manual_log_text("[MANUAL] case=uart_p1_008 feature=framing_error\r\n");
    et_manual_log_text("[CONFIG] uart1=8N2 uart2=8N1 wiring=uart2_tx_to_uart1_rx\r\n");

    configure_uart(ET_MANUAL_UART_DUT, UART_STOPBITS_2);
    configure_uart(ET_MANUAL_UART_PEER, UART_STOPBITS_1);
    UART_enableInterrupt(ET_MANUAL_UART_DUT, UART_IT_ERROR_FLAG);
    (void)UART_transmit(ET_MANUAL_UART_PEER, (void *)payload, ET_MANUAL_UART_FRAMING_PAYLOAD_SIZE,
                        UART_BLOCK_TRANSMIT_FIFO);
    (void)UART_waitTransmitDone(ET_MANUAL_UART_PEER, ET_MANUAL_UART_WAIT_LIMIT);
    (void)UART_testGetInterruptSnapshot(ET_MANUAL_UART_DUT, &snapshot);

    et_manual_log_u32("[OBSERVE] IIR", snapshot.interruptStatus);
    et_manual_log_u32("[OBSERVE] RESOLVED_IIR", snapshot.resolvedInterruptStatus);
    et_manual_log_u32("[OBSERVE] LSR", snapshot.lineStatus);
    et_manual_log_u32("[EXPECT] LSR_FE_MASK", UART_LINE_STA_FE_FLAG);

    return ((snapshot.lineStatus & UART_LINE_STA_FE_FLAG) != 0u) ? ET_MANUAL_RESULT_PASS
                                                                 : ET_MANUAL_RESULT_FAIL;
}

int et_manual_uart_p1_012_busy_detect_irq(void)
{
    uint8_t payload = ET_MANUAL_UART_BUSY_PAYLOAD_VALUE;
    uint32_t pre_trigger_usr = 0u;
    uint32_t observed_iir = 0u;
    uint32_t clear_usr = 0u;
    uint32_t after_clear_iir = 0u;
    uint32_t attempt;
    uint32_t transmitted = 0u;
    uint8_t busy_observed = 0u;
    uint8_t interrupt_observed = 0u;
    uint8_t cleared = 0u;
    uint8_t recovered = 0u;

    /* 复位：本Case在配置UART1之前先清除两个测试UART的硬件状态。 */
    reset_uart_pair();

    et_manual_log_text("[MANUAL] case=uart_p1_012 feature=busy_detect_irq\r\n");
    configure_uart(ET_MANUAL_UART_DUT, UART_STOPBITS_1);

    /* Keep the UART in normal FIFO mode. Each attempt writes one byte and
     * immediately changes LCR, so the write overlaps an active transfer when
     * the implementation exposes the documented Busy window. */
    for (attempt = 0u; attempt < ET_MANUAL_UART_BUSY_TRIGGER_ATTEMPTS; ++attempt)
    {
        transmitted +=
            UART_transmit(ET_MANUAL_UART_DUT, &payload, 1u, UART_NON_BLOCK_TRANSMIT_FIFO);
        pre_trigger_usr = READ_REG(ET_MANUAL_UART_DUT->USR);

        if ((pre_trigger_usr & UART_STA_BUSY_FLAG) != 0u)
        {
            busy_observed = 1u;
        }

        (void)UART_setLineConfig(ET_MANUAL_UART_DUT, UART_WORDLENGTH_8B,
                                 ((attempt & 1u) == 0u) ? UART_STOPBITS_2 : UART_STOPBITS_1,
                                 UART_PARITY_NONE);
        observed_iir = READ_REG(ET_MANUAL_UART_DUT->IIR);

        if ((observed_iir & UART0_IIR_IID_Msk) == UART_REG_IIR_IID_BUSY_DETECT)
        {
            interrupt_observed = 1u;
            break;
        }
    }

    if (interrupt_observed != 0u)
    {
        /* Reading USR is the documented Busy Detect clear sequence. */
        clear_usr = READ_REG(ET_MANUAL_UART_DUT->USR);
        after_clear_iir = READ_REG(ET_MANUAL_UART_DUT->IIR);
        cleared = ((after_clear_iir & UART0_IIR_IID_Msk) != UART_REG_IIR_IID_BUSY_DETECT) ? 1u : 0u;
    }

    if (UART_waitTransmitDone(ET_MANUAL_UART_DUT, ET_MANUAL_UART_BUSY_RECOVERY_WAIT_LIMIT) ==
        DRV_OK)
    {
        recovered = 1u;
    }

    et_manual_log_u32("[OBSERVE] transmitted", transmitted);
    et_manual_log_u32("[OBSERVE] pre_trigger_usr", pre_trigger_usr);
    et_manual_log_u32("[OBSERVE] observed_iir", observed_iir);
    et_manual_log_u32("[OBSERVE] clear_usr", clear_usr);
    et_manual_log_u32("[OBSERVE] after_clear_iir", after_clear_iir);
    et_manual_log_u32("[OBSERVE] busy_observed", busy_observed);
    et_manual_log_u32("[OBSERVE] irq_observed", interrupt_observed);
    et_manual_log_u32("[OBSERVE] cleared", cleared);
    et_manual_log_u32("[OBSERVE] recovered", recovered);

    return ((transmitted != 0u) && (busy_observed != 0u) && (interrupt_observed != 0u) &&
            (cleared != 0u) && (recovered != 0u))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}

int et_manual_uart_p3_009_direct_fifo_access(void)
{
    uint8_t fifo_access_active = 0u;
    uint8_t tx_value = 0u;
    uint8_t rx_value = 0u;
    DRV_Status enable_status;
    DRV_Status tx_status = DRV_ERROR;
    DRV_Status rx_status = DRV_ERROR;

    /* 复位：Direct FIFO配置不得继承前一个UART Case留下的LCR或FIFO状态。 */
    reset_uart_pair();

    et_manual_log_text("[MANUAL] case=uart_p3_009 feature=direct_fifo_access\r\n");
    configure_uart(ET_MANUAL_UART_DUT, UART_STOPBITS_1);
    enable_status = UART_testSetFIFOAccess(ET_MANUAL_UART_DUT, 1u, &fifo_access_active);

    if ((enable_status == DRV_OK) && (fifo_access_active != 0u))
    {
        UART_haltTransmission(ET_MANUAL_UART_DUT);
        (void)UART_transmit(ET_MANUAL_UART_DUT, (void *)&(uint8_t){ET_MANUAL_UART_FIFO_TX_VALUE},
                            1u, UART_NON_BLOCK_TRANSMIT_FIFO);
        tx_status = UART_testReadTxFIFO(ET_MANUAL_UART_DUT, &tx_value);
        UART_resumeTransmission(ET_MANUAL_UART_DUT);
        rx_status = UART_testWriteRxFIFO(ET_MANUAL_UART_DUT, ET_MANUAL_UART_FIFO_RX_VALUE, 0u, 0u);
        (void)UART_receive(ET_MANUAL_UART_DUT, &rx_value, 1u);
        (void)UART_testSetFIFOAccess(ET_MANUAL_UART_DUT, 0u, &fifo_access_active);
    }

    et_manual_log_u32("[OBSERVE] enable_status", (uint32_t)enable_status);
    et_manual_log_u32("[OBSERVE] tx_status", (uint32_t)tx_status);
    et_manual_log_u32("[OBSERVE] rx_status", (uint32_t)rx_status);
    et_manual_log_u32("[OBSERVE] tx_value", tx_value);
    et_manual_log_u32("[OBSERVE] rx_value", rx_value);
    et_manual_log_u32("[EXPECT] tx_value", ET_MANUAL_UART_FIFO_TX_VALUE);
    et_manual_log_u32("[EXPECT] rx_value", ET_MANUAL_UART_FIFO_RX_VALUE);

    return ((enable_status == DRV_OK) && (tx_status == DRV_OK) && (rx_status == DRV_OK) &&
            (tx_value == ET_MANUAL_UART_FIFO_TX_VALUE) &&
            (rx_value == ET_MANUAL_UART_FIFO_RX_VALUE))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
