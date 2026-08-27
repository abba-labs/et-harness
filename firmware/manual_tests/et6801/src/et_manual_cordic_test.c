#include <stdint.h>

#include "et6x_ahbdma.h"
#include "et6x_cordic.h"
#include "et6x_crg.h"
#include "et6x_sysctrl.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_cordic(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_CORDIC_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_CORDIC_CLOCK);
    CRG_lockClockConfig();
}

static void reset_cordic_dma(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_CORDIC_DMA_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_CORDIC_DMA_CLOCK);
    CRG_lockClockConfig();
}

static void configure_cordic_scale7_arctan(void)
{
    CORDIC_InitParams config;

    CORDIC_initStruct(&config);
    config.scale = CORDIC_SCALE_7;
    config.argDataFormat = CORDIC_DATA_FORMAT_BIT32;
    config.resDataFormat = CORDIC_DATA_FORMAT_BIT32;
    config.workMode = CORDIC_WORK_MODE_POLLING;
    config.precision = CORDIC_PRECISIO_8;
    config.floatDataEn = DISABLE;
    CORDIC_init(&config);
    CORDIC_clearStatus(ET_MANUAL_CORDIC_ALL_STATUS);
}

int et_manual_cordic_p1_003_scale7_arctan_precision(void)
{
    uint32_t wait_count = ET_MANUAL_CORDIC_WAIT_LIMIT;
    uint32_t status;
    uint32_t cleared;
    uint32_t actual_raw;
    uint32_t absolute_delta;

    /* Every standalone Case starts from a hardware reset before any configuration. */
    reset_cordic();
    configure_cordic_scale7_arctan();

    et_manual_log_text("[MANUAL] case=cordic_p1_003 feature=scale7_arctan_precision\r\n");
    CORDIC_setArg(ET_MANUAL_CORDIC_ARCTAN_INPUT_RAW, CORDIC_FUNCTION_ARCTAN);

    do
    {
        status = CORDIC_getStatus();
        --wait_count;
    } while (((status & CORDIC_STS_CALCULATE_COMPLETE) == 0u) && (wait_count > 0u));

    actual_raw = CORDIC_getResult1();
    absolute_delta = (actual_raw >= ET_MANUAL_CORDIC_ARCTAN_EXPECTED_RAW)
                         ? (actual_raw - ET_MANUAL_CORDIC_ARCTAN_EXPECTED_RAW)
                         : (ET_MANUAL_CORDIC_ARCTAN_EXPECTED_RAW - actual_raw);

    CORDIC_clearStatus(CORDIC_STS_CALCULATE_COMPLETE);
    cleared = CORDIC_getStatus();

    et_manual_log_u32("[CONFIG] scale", CORDIC_SCALE_7);
    et_manual_log_u32("[CONFIG] input_raw", ET_MANUAL_CORDIC_ARCTAN_INPUT_RAW);
    et_manual_log_u32("[OBSERVE] status", status);
    et_manual_log_u32("[OBSERVE] actual_raw", actual_raw);
    et_manual_log_u32("[EXPECT] expected_raw", ET_MANUAL_CORDIC_ARCTAN_EXPECTED_RAW);
    et_manual_log_u32("[OBSERVE] absolute_delta_raw", absolute_delta);
    et_manual_log_u32("[EXPECT] tolerance_raw", ET_MANUAL_CORDIC_ARCTAN_TOLERANCE_RAW);
    et_manual_log_u32("[OBSERVE] status_after_clear", cleared);

    return ((wait_count > 0u) && ((status & CORDIC_STS_CALCULATE_COMPLETE) != 0u) &&
            (absolute_delta <= ET_MANUAL_CORDIC_ARCTAN_TOLERANCE_RAW) &&
            ((cleared & CORDIC_STS_CALCULATE_COMPLETE) == 0u))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}

/*
 * 测试Feature：CORDIC DMA工作模式的输入搬运、计算和结果搬运。
 * 测试方法：先以Polling计算SQRT基线，再用ET6801历史映射40/39和DMA0通道0/1搬运同一输入。
 * 通过条件：两条DMA通道完成且DMA结果与Polling结果完全相同。
 */
int et_manual_cordic_p2_001_dma_mode_equivalence(void)
{
    CORDIC_InitParams cordic_config;
    AHBDMA_Ch_Init_TypeDef channel_config;
    uint32_t input_raw = ET_MANUAL_CORDIC_DMA_INPUT_RAW;
    uint32_t output_raw = ET_MANUAL_CORDIC_DMA_RESULT_SENTINEL;
    uint32_t polling_raw;
    uint32_t polling_status;
    uint32_t dma_status;
    uint32_t wait_count;
    DRV_Status input_config_status;
    DRV_Status output_config_status;

    /* 基线：复位CORDIC后使用Polling路径取得同一输入的硬件结果。 */
    reset_cordic();
    CORDIC_initStruct(&cordic_config);
    cordic_config.workMode = CORDIC_WORK_MODE_POLLING;
    CORDIC_init(&cordic_config);
    CORDIC_clearStatus(ET_MANUAL_CORDIC_ALL_STATUS);
    CORDIC_setArg(input_raw, CORDIC_FUNCTION_SQUAREROOT);

    wait_count = ET_MANUAL_CORDIC_WAIT_LIMIT;
    do
    {
        polling_status = CORDIC_getStatus();
        --wait_count;
    } while (((polling_status & CORDIC_STS_CALCULATE_COMPLETE) == 0u) && (wait_count > 0u));

    polling_raw = CORDIC_getResult1();

    /* 配置：再次复位CORDIC和DMA0，再建立两条固定且可审计的ET6801 DMA路径。 */
    reset_cordic();
    reset_cordic_dma();
    CORDIC_initStruct(&cordic_config);
    cordic_config.workMode = ET_MANUAL_CORDIC_DMA_WORK_MODE;
    CORDIC_init(&cordic_config);
    CORDIC_clearStatus(ET_MANUAL_CORDIC_ALL_STATUS);

    SYSCTRL_configDMAMux(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_INPUT_INTERFACE,
                         ET_MANUAL_CORDIC_DMA_INPUT_REQUEST);
    SYSCTRL_configDMAMux(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_OUTPUT_INTERFACE,
                         ET_MANUAL_CORDIC_DMA_OUTPUT_REQUEST);
    (void)AHBDMA_enableModule(ET_MANUAL_CORDIC_DMA);

    AHBDMA_initChannelStruct(&channel_config);
    output_config_status = AHBDMA_setDefaultP2M(
        &channel_config, (uint32_t)&CORDIC->RES1_RPT, (uint32_t)&output_raw,
        ET_MANUAL_CORDIC_DMA_WORD_COUNT, ET_MANUAL_CORDIC_DMA_OUTPUT_INTERFACE);
    channel_config.srcTrWidth = AHBDMA_BITS_32;
    channel_config.dstTrWidth = AHBDMA_BITS_32;
    channel_config.dstAddressInc = AHBDMA_INCREMENTAL;
    (void)AHBDMA_initChannel(ET_MANUAL_CORDIC_DMA, &channel_config,
                             ET_MANUAL_CORDIC_DMA_OUTPUT_CHANNEL);
    (void)AHBDMA_enableChannel(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_OUTPUT_CHANNEL);

    AHBDMA_initChannelStruct(&channel_config);
    input_config_status = AHBDMA_setDefaultM2P(
        &channel_config, (uint32_t)&input_raw, (uint32_t)&CORDIC->SQRT_CAL,
        ET_MANUAL_CORDIC_DMA_WORD_COUNT, ET_MANUAL_CORDIC_DMA_INPUT_INTERFACE);
    channel_config.srcTrWidth = AHBDMA_BITS_32;
    channel_config.dstTrWidth = AHBDMA_BITS_32;
    channel_config.srcAddressInc = AHBDMA_INCREMENTAL;
    (void)AHBDMA_initChannel(ET_MANUAL_CORDIC_DMA, &channel_config,
                             ET_MANUAL_CORDIC_DMA_INPUT_CHANNEL);

    /* 激励：结果通道已经就绪后，启动输入通道触发一次SQRT运算。 */
    (void)AHBDMA_enableChannel(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_INPUT_CHANNEL);

    wait_count = ET_MANUAL_CORDIC_WAIT_LIMIT;
    do
    {
        dma_status = CORDIC_getStatus();
        --wait_count;
    } while (((AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA,
                                    ET_MANUAL_CORDIC_DMA_INPUT_CHANNEL) == false) ||
              (AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA,
                                    ET_MANUAL_CORDIC_DMA_OUTPUT_CHANNEL) == false)) &&
             (wait_count > 0u));

    /* 观测：打印当前映射、通道终态、CORDIC状态和Polling/DMA原始结果。 */
    et_manual_log_text("[MANUAL] case=cordic_p2_001 feature=dma_mode_equivalence\r\n");
    et_manual_log_u32("[CONFIG] input_request_id", ET_MANUAL_CORDIC_DMA_INPUT_REQUEST);
    et_manual_log_u32("[CONFIG] output_request_id", ET_MANUAL_CORDIC_DMA_OUTPUT_REQUEST);
    et_manual_log_u32("[CONFIG] input_endpoint", (uint32_t)&CORDIC->SQRT_CAL);
    et_manual_log_u32("[CONFIG] output_endpoint", (uint32_t)&CORDIC->RES1_RPT);
    et_manual_log_u32("[OBSERVE] input_config_status", (uint32_t)input_config_status);
    et_manual_log_u32("[OBSERVE] output_config_status", (uint32_t)output_config_status);
    et_manual_log_u32("[OBSERVE] input_channel_free",
                      AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA,
                                           ET_MANUAL_CORDIC_DMA_INPUT_CHANNEL)
                          ? 1u
                          : 0u);
    et_manual_log_u32("[OBSERVE] output_channel_free",
                      AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA,
                                           ET_MANUAL_CORDIC_DMA_OUTPUT_CHANNEL)
                          ? 1u
                          : 0u);
    et_manual_log_u32("[OBSERVE] cordic_status", dma_status);
    et_manual_log_u32("[OBSERVE] polling_result_raw", polling_raw);
    et_manual_log_u32("[OBSERVE] dma_result_raw", output_raw);
    et_manual_log_u32("[EXPECT] dma_result_raw", polling_raw);

    return ((input_config_status == DRV_OK) && (output_config_status == DRV_OK) &&
            (wait_count > 0u) &&
            AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_INPUT_CHANNEL) &&
            AHBDMA_isChannelFree(ET_MANUAL_CORDIC_DMA, ET_MANUAL_CORDIC_DMA_OUTPUT_CHANNEL) &&
            (output_raw == polling_raw))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
