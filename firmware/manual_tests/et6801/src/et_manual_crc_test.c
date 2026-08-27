#include <stdint.h>

#include "et6x_crc.h"
#include "et6x_crg.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_crc(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_CRC_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_CRC_CLOCK);
    CRG_lockClockConfig();
}

static void configure_crc(uint8_t threshold)
{
    CRC_ConfigParams config;

    config.mode = CRC_MODE_CRC32;
    config.refIn = DISABLE;
    config.refOut = DISABLE;
    config.xorOut = ALL_ZERO;
    config.autoLengthReloadEn = DISABLE;
    config.byteswapEn = ENABLE;
    config.resultCheckEn = DISABLE;
    config.polynomial = ET_MANUAL_CRC_POLYNOMIAL;
    config.fifoThreshold = threshold;
    config.initialValue = ET_MANUAL_CRC_INITIAL_VALUE;
    CRC_enableModule();
    CRC_config(&config);
}

int et_manual_crc_p1_012_fifo_overflow_recovery(void)
{
    uint32_t recovery_input[2] = {0x04030201u, 0x08070605u};
    uint32_t index;
    uint32_t checkpoint;
    uint32_t final;
    uint32_t overflow;
    uint32_t recovery_result = 0u;
    DRV_Status recovery_status;

    et_manual_log_text("[MANUAL] case=crc_p1_012 feature=fifo_overflow_recovery\r\n");

    /* 复位：Overflow激励前先建立明确的CRC硬件初始状态。 */
    reset_crc();
    configure_crc(ET_MANUAL_CRC_OVERFLOW_THRESHOLD);
    CRC_setDataLength(ET_MANUAL_CRC_OVERFLOW_WRITE_COUNT);
    checkpoint = CRC_getResult();

    /* Keep the overflow stimulus deliberately simple: the CPU writes the CRC
     * input register continuously without polling or intermediate reads. */
    for (index = 0u; index < ET_MANUAL_CRC_OVERFLOW_WRITE_COUNT; ++index)
    {
        WRITE_REG(CRC->IR, ET_MANUAL_CRC_THRESHOLD_VALUE);
    }

    final = CRC_getResult();
    overflow = CRC_isFIFOOverflow() ? 1u : 0u;

    /* 复位：Recovery是第二个独立场景，重新复位后再配置正常计算路径。 */
    reset_crc();
    configure_crc(ET_MANUAL_CRC_OVERFLOW_THRESHOLD);
    recovery_status = CRC_calculate32(recovery_input, sizeof(recovery_input), &recovery_result,
                                      ET_MANUAL_CRC_TIMEOUT);

    et_manual_log_u32("[CONFIG] FIFO_TRHD", ET_MANUAL_CRC_OVERFLOW_THRESHOLD);
    et_manual_log_u32("[OBSERVE] RESULT_before", checkpoint);
    et_manual_log_u32("[OBSERVE] RESULT_after_64", final);
    et_manual_log_u32("[OBSERVE] FIFO_OVF", overflow);
    et_manual_log_u32("[OBSERVE] recovery_crc", recovery_result);
    et_manual_log_u32("[EXPECT] recovery_crc", ET_MANUAL_CRC_RECOVERY_EXPECTED);

    return ((overflow != 0u) && (recovery_status == DRV_OK) &&
            (recovery_result == ET_MANUAL_CRC_RECOVERY_EXPECTED))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
