#include "et6801.h"
#include "et6x_crg.h"
#include "et6x_fmac.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_fmac(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_FMAC_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_FMAC_CLOCK);
    CRG_lockClockConfig();
}

static void configure_fmac(FMAC_OutputDataMode output_mode, uint16_t output_offset,
                           ControlStatus float_input)
{
    FMAC_ConfigParams config = {0};

    config.X1_BuffBase = ET_MANUAL_FMAC_X1_BASE;
    config.X1_BuffSize = ET_MANUAL_FMAC_X1_SIZE;
    config.X1_BuffFIFOTrhd = FMAC_TRHD_1;
    config.X2_BuffBase = ET_MANUAL_FMAC_X2_BASE;
    config.X2_BuffSize = ET_MANUAL_FMAC_X2_SIZE;
    config.Y_BuffBase = ET_MANUAL_FMAC_Y_BASE;
    config.Y_BuffSize = ET_MANUAL_FMAC_Y_SIZE;
    config.Y_BuffFIFOTrhd = FMAC_TRHD_1;
    config.accumulatorWrapEn = DISABLE;
    config.outputDataMode = output_mode;
    config.DMADataReadEn = DISABLE;
    config.DMADataWriteEn = DISABLE;
    config.clipEn = DISABLE;
    config.outputDataOffset = output_offset;
    config.outputDataShift = FMAC_NO_SHIFT;
    config.floatDataReadEn = float_input;
    config.floatDataWriteEn = DISABLE;

    FMAC_config(&config);
}

/*
 * 测试Feature：Float32超范围输入置位FLOAT2FIXED_OVF_RPT，正常输入解除硬件条件后软件Clear。
 * 测试方法：FMAC复位后向Y缓冲区装载四个2.0f触发Overflow；再装载一个0.25f解除实时
 *           Overflow条件，最后执行软件Clear并读取状态。
 * 通过条件：越界输入后Overflow置位，正常输入被硬件接收，软件Clear后Overflow清零。
 */
int et_manual_fmac_p1_006_float_overflow_clear(void)
{
    float input[ET_MANUAL_FMAC_SAMPLE_COUNT];
    float recovery_input = ET_MANUAL_FMAC_FLOAT_RECOVERY_INPUT;
    DRV_Status recovery_load_status;
    DRV_Status clear_status;
    uint32_t index;
    uint32_t status_after_trigger;
    uint32_t status_after_recovery;
    uint32_t status_after_clear;

    /* 复位：每个手动Case都从独立的FMAC硬件状态开始。 */
    reset_fmac();
    configure_fmac(FMAC_NO_OFFSET_AND_SAT, 0u, ENABLE);

    /* 激励：超出Q15范围的Float32输入必须触发转换Overflow。 */
    for (index = 0u; index < ET_MANUAL_FMAC_SAMPLE_COUNT; ++index)
    {
        input[index] = ET_MANUAL_FMAC_FLOAT_OVERFLOW_INPUT;
    }

    (void)FMAC_testLoadYFloat(input, ET_MANUAL_FMAC_SAMPLE_COUNT, ET_MANUAL_FMAC_WAIT_LIMIT);

    for (index = 0u; index < ET_MANUAL_FMAC_SAMPLE_COUNT; ++index)
    {
        (void)FMAC_getFIFOData();
    }

    status_after_trigger = FMAC_testGetStatusRaw();

    /* 恢复输入：送入一个Q15范围内的Float32值，先解除硬件实时Overflow条件。 */
    recovery_load_status = FMAC_testLoadYFloat(&recovery_input, 1u, ET_MANUAL_FMAC_WAIT_LIMIT);
    (void)FMAC_getFIFOData();
    status_after_recovery = FMAC_testGetStatusRaw();

    /* 软件清除：实时条件解除后，Driver通过W1C清除Sticky报告位。 */
    clear_status = FMAC_testClearDynamicState(ET_MANUAL_FMAC_WAIT_LIMIT);
    status_after_clear = FMAC_testGetStatusRaw();

    et_manual_log_text("[MANUAL] chip=ET6801 ip=FMAC case=fmac_p1_006\r\n");
    et_manual_log_u32("[CONFIG] input_count", ET_MANUAL_FMAC_SAMPLE_COUNT);
    et_manual_log_u32("[CONFIG] input_float_raw", ET_MANUAL_FMAC_FLOAT_OVERFLOW_INPUT_RAW);
    et_manual_log_u32("[CONFIG] recovery_float_raw", ET_MANUAL_FMAC_FLOAT_RECOVERY_INPUT_RAW);
    et_manual_log_u32("[OBSERVE] sr_after_trigger", status_after_trigger);
    et_manual_log_u32("[OBSERVE] recovery_load_status", recovery_load_status);
    et_manual_log_u32("[OBSERVE] sr_after_recovery", status_after_recovery);
    et_manual_log_u32("[OBSERVE] clear_status", clear_status);
    et_manual_log_u32("[OBSERVE] sr_after_clear", status_after_clear);
    et_manual_log_u32("[EXPECT] overflow_mask", FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk);

    if (((status_after_trigger & FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk) == 0u) ||
        (recovery_load_status != DRV_OK) || (clear_status != DRV_OK) ||
        ((status_after_clear & FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk) != 0u))
    {
        return ET_MANUAL_RESULT_FAIL;
    }

    return ET_MANUAL_RESULT_PASS;
}

/*
 * 测试Feature：FIR输出加Offset后仍为负数时置位ADD_OFT_IS_NEG_RPT，软件W1C后状态恢复。
 * 测试方法：FMAC复位后配置SAT16和正Offset，装载单抽头系数及零历史，
 *           执行有界单抽头FIR负输入事务；目标状态置位后再执行一笔正输入事务，
 *           撤销实时负值条件，最后调用Driver Test Extension执行W1C。
 * 通过条件：两笔事务全部收发，负输出后目标状态位置位，正输入恢复后W1C可清零。
 */
int et_manual_fmac_p1_010_negative_status_clear(void)
{
    int16_t coefficient = ET_MANUAL_FMAC_UNIT_COEFFICIENT;
    int16_t history = ET_MANUAL_FMAC_ZERO_HISTORY;
    int16_t input[ET_MANUAL_FMAC_SAMPLE_COUNT];
    int16_t recovery_input[ET_MANUAL_FMAC_SAMPLE_COUNT];
    int16_t output[ET_MANUAL_FMAC_SAMPLE_COUNT] = {0};
    DRV_Status coefficient_status;
    DRV_Status history_status;
    DRV_Status process_status;
    DRV_Status recovery_status;
    DRV_Status clear_status;
    uint32_t accepted_count = 0u;
    uint32_t read_count = 0u;
    uint32_t elapsed_cycles = 0u;
    uint32_t recovery_accepted_count = 0u;
    uint32_t recovery_read_count = 0u;
    uint32_t recovery_elapsed_cycles = 0u;
    uint32_t index;
    uint32_t status_after_trigger;
    uint32_t status_after_recovery;
    uint32_t status_after_clear;

    /* 复位：本Case不得继承前一个FMAC Case留下的Sticky状态。 */
    reset_fmac();
    configure_fmac(FMAC_ADD_OFFSET_AND_SAT_TO_16BIT, ET_MANUAL_FMAC_POSITIVE_OFFSET, DISABLE);

    /* 准备：单抽头系数和零历史使输出因果链保持最小且可解释。 */
    coefficient_status =
        FMAC_testLoadX2(&coefficient, 1u, NULL, 0u, ET_MANUAL_FMAC_WAIT_LIMIT);
    history_status = FMAC_testLoadX1(&history, 1u, ET_MANUAL_FMAC_WAIT_LIMIT);

    /* 激励：负Q15输入经单抽头FIR和正Offset后仍为负数。 */
    for (index = 0u; index < ET_MANUAL_FMAC_SAMPLE_COUNT; ++index)
    {
        input[index] = ET_MANUAL_FMAC_NEGATIVE_INPUT;
    }

    process_status = FMAC_testProcessTimed(ET_MANUAL_FMAC_FUNCTION_FIR, 1u, 0u, input, output,
                                           ET_MANUAL_FMAC_SAMPLE_COUNT, DISABLE,
                                           ET_MANUAL_FMAC_WAIT_LIMIT, &accepted_count, &read_count,
                                           &elapsed_cycles);

    status_after_trigger = FMAC_testGetStatusRaw();

    /* 恢复：正Q15输入撤销实时负值条件，Sticky位留给后续W1C验证。 */
    for (index = 0u; index < ET_MANUAL_FMAC_SAMPLE_COUNT; ++index)
    {
        recovery_input[index] = ET_MANUAL_FMAC_POSITIVE_INPUT;
    }

    recovery_status = FMAC_testProcessTimed(
        ET_MANUAL_FMAC_FUNCTION_FIR, 1u, 0u, recovery_input, output,
        ET_MANUAL_FMAC_SAMPLE_COUNT, DISABLE, ET_MANUAL_FMAC_WAIT_LIMIT,
        &recovery_accepted_count, &recovery_read_count, &recovery_elapsed_cycles);
    status_after_recovery = FMAC_testGetStatusRaw();

    /* 清除：实时条件撤销后，统一通过Chip Driver Test Extension执行W1C。 */
    clear_status = FMAC_testClearDynamicState(ET_MANUAL_FMAC_WAIT_LIMIT);
    status_after_clear = FMAC_testGetStatusRaw();

    et_manual_log_text("[MANUAL] chip=ET6801 ip=FMAC case=fmac_p1_010\r\n");
    et_manual_log_u32("[CONFIG] input_count", ET_MANUAL_FMAC_SAMPLE_COUNT);
    et_manual_log_u32("[CONFIG] input_q15", (uint32_t)(uint16_t)ET_MANUAL_FMAC_NEGATIVE_INPUT);
    et_manual_log_u32("[CONFIG] coefficient_q15", (uint32_t)(uint16_t)coefficient);
    et_manual_log_u32("[CONFIG] output_offset", ET_MANUAL_FMAC_POSITIVE_OFFSET);
    et_manual_log_u32("[OBSERVE] coefficient_status", coefficient_status);
    et_manual_log_u32("[OBSERVE] history_status", history_status);
    et_manual_log_u32("[OBSERVE] process_status", process_status);
    et_manual_log_u32("[OBSERVE] accepted_count", accepted_count);
    et_manual_log_u32("[OBSERVE] read_count", read_count);
    et_manual_log_u32("[OBSERVE] output_last",
                      (uint32_t)(uint16_t)output[ET_MANUAL_FMAC_SAMPLE_COUNT - 1u]);
    et_manual_log_u32("[OBSERVE] elapsed_cycles", elapsed_cycles);
    et_manual_log_u32("[OBSERVE] sr_after_trigger", status_after_trigger);
    et_manual_log_u32("[OBSERVE] recovery_status", recovery_status);
    et_manual_log_u32("[OBSERVE] recovery_accepted", recovery_accepted_count);
    et_manual_log_u32("[OBSERVE] recovery_read", recovery_read_count);
    et_manual_log_u32("[OBSERVE] recovery_cycles", recovery_elapsed_cycles);
    et_manual_log_u32("[OBSERVE] sr_after_recovery", status_after_recovery);
    et_manual_log_u32("[OBSERVE] clear_status", clear_status);
    et_manual_log_u32("[OBSERVE] sr_after_w1c", status_after_clear);
    et_manual_log_u32("[EXPECT] negative_mask", FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk);

    if ((coefficient_status != DRV_OK) || (history_status != DRV_OK) ||
        (process_status != DRV_OK) || (accepted_count != ET_MANUAL_FMAC_SAMPLE_COUNT) ||
        (read_count != ET_MANUAL_FMAC_SAMPLE_COUNT) || (recovery_status != DRV_OK) ||
        (recovery_accepted_count != ET_MANUAL_FMAC_SAMPLE_COUNT) ||
        (recovery_read_count != ET_MANUAL_FMAC_SAMPLE_COUNT) || (clear_status != DRV_OK) ||
        ((status_after_trigger & FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk) == 0u) ||
        ((status_after_clear & FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk) != 0u))
    {
        return ET_MANUAL_RESULT_FAIL;
    }

    return ET_MANUAL_RESULT_PASS;
}
