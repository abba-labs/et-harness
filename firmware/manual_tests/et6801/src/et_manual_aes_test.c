#include <stdint.h>

#include "et6x_aes.h"
#include "et6x_crg.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static const uint32_t g_aes_key[4] = {
    ET_MANUAL_AES_KEY_WORD_0,
    ET_MANUAL_AES_KEY_WORD_1,
    ET_MANUAL_AES_KEY_WORD_2,
    ET_MANUAL_AES_KEY_WORD_3,
};

static const uint32_t g_aes_first_block[4] = {
    ET_MANUAL_AES_FIRST_WORD_0,
    ET_MANUAL_AES_FIRST_WORD_1,
    ET_MANUAL_AES_FIRST_WORD_2,
    ET_MANUAL_AES_FIRST_WORD_3,
};

static const uint32_t g_aes_second_block[4] = {
    ET_MANUAL_AES_SECOND_WORD_0,
    ET_MANUAL_AES_SECOND_WORD_1,
    ET_MANUAL_AES_SECOND_WORD_2,
    ET_MANUAL_AES_SECOND_WORD_3,
};

static void reset_aes(void)
{
    CRG_unlockClockConfig();
    CRG_resetPeripheral(ET_MANUAL_AES_CLOCK);
    CRG_lockClockConfig();
}

static void configure_aes_output_conflict(void)
{
    AES_ConfigParams config;

    config.keySize = AES_KEY_SIZE_128BIT;
    config.direction = AES_DIRECTION_ENCRYPTION;
    config.paddingMode = AES_NO_PADDING;
    config.opMode = AES_OPMODE_ECB;
    config.ctrCount = 0u;
    config.FIFOModeEn = DISABLE;
    config.endianSel = AES_ENDIAN_BIG;

    AES_disableDMARequest(AES_DMA_EN_DATA_IN | AES_DMA_EN_DATA_OUT);
    AES_disableInterrupt(ET_MANUAL_AES_ALL_INTERRUPTS);
    AES_setInterruptMask(ET_MANUAL_AES_ALL_INTERRUPTS);
    AES_clearInterruptStatus(ET_MANUAL_AES_ALL_INTERRUPTS);
    AES_enableModule();
    AES_setDataLength(ET_MANUAL_AES_DATA_LENGTH_BYTES);
    AES_configureModule(&config);
    AES_setKey(g_aes_key, AES_KEY_SIZE_128BIT);
    AES_enableInterrupt(AES_INT_OUTPUT_CONFLICT);
    AES_clearInterruptMask(AES_INT_OUTPUT_CONFLICT);
}

int et_manual_aes_p1_009_output_conflict(void)
{
    uint32_t baseline_raw = 0u;
    uint32_t baseline_status = 0u;
    uint32_t observed_raw = 0u;
    uint32_t observed_status = 0u;
    uint32_t cleared_raw = 0u;
    uint32_t cleared_status = 0u;
    DRV_Status stimulus_status;

    /* Every standalone Case starts from a hardware reset before any configuration. */
    reset_aes();
    configure_aes_output_conflict();

    et_manual_log_text("[MANUAL] case=aes_p1_009 feature=output_conflict_irq\r\n");
    (void)AES_testGetInterruptSnapshot(&baseline_raw, &baseline_status);

    /* Keep the first result unread, then submit the second block through the normal input handshake. */
    stimulus_status = AES_testWriteInputBlockPair(g_aes_first_block, g_aes_second_block,
                                                  ET_MANUAL_AES_TIMEOUT);
    (void)AES_testGetInterruptSnapshot(&observed_raw, &observed_status);

    AES_clearInterruptStatus(AES_INT_OUTPUT_CONFLICT);
    (void)AES_testGetInterruptSnapshot(&cleared_raw, &cleared_status);
    AES_disableInterrupt(AES_INT_OUTPUT_CONFLICT);
    AES_disableModule();

    et_manual_log_u32("[OBSERVE] stimulus_status", (uint32_t)stimulus_status);
    et_manual_log_u32("[OBSERVE] baseline_raw", baseline_raw);
    et_manual_log_u32("[OBSERVE] baseline_status", baseline_status);
    et_manual_log_u32("[OBSERVE] output_conflict_raw", observed_raw);
    et_manual_log_u32("[OBSERVE] output_conflict_status", observed_status);
    et_manual_log_u32("[OBSERVE] cleared_raw", cleared_raw);
    et_manual_log_u32("[OBSERVE] cleared_status", cleared_status);
    et_manual_log_u32("[EXPECT] output_conflict_mask", AES_INT_OUTPUT_CONFLICT);

    return ((stimulus_status == DRV_OK) &&
            ((observed_raw & AES_INT_OUTPUT_CONFLICT) != 0u) &&
            ((observed_status & AES_INT_OUTPUT_CONFLICT) != 0u) &&
            ((cleared_raw & AES_INT_OUTPUT_CONFLICT) == 0u) &&
            ((cleared_status & AES_INT_OUTPUT_CONFLICT) == 0u))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
