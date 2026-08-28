#include <stdint.h>

#include "et6x_cortex.h"
#include "et6x_crg.h"
#include "et6x_stimer.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

/* Keil Watch uses these arrays to compare PAUSE and RUN_FREE counter behavior. */
volatile uint32_t et_manual_stimer_pause_samples[ET_MANUAL_STIMER_DEBUG_SAMPLE_COUNT];
volatile uint32_t et_manual_stimer_run_free_samples[ET_MANUAL_STIMER_DEBUG_SAMPLE_COUNT];

static void reset_stimer(void)
{
    CRG_unlockClockConfig();
    CRG_enablePeripheral(ET_MANUAL_STIMER_CLOCK);
    CRG_resetPeripheral(ET_MANUAL_STIMER_CLOCK);
    CRG_lockClockConfig();
}

static void configure_stimer(void)
{
    STIMER_stopTimer(ET_MANUAL_STIMER);
    STIMER_setEmulationMode(ET_MANUAL_STIMER, STIMER_EMULATIONMODE_RUNFREE);
    STIMER_setLoadMode(ET_MANUAL_STIMER, STIMER_LOADMODE_IMMEDIATELY);
    STIMER_setPeriod(ET_MANUAL_STIMER, ET_MANUAL_STIMER_PERIOD_TICKS);
    STIMER_setPreScaler(ET_MANUAL_STIMER, ET_MANUAL_STIMER_PRESCALER);
    STIMER_resetTimerCount(ET_MANUAL_STIMER);
}

static uint32_t measure_stimer_delta(uint16_t prescaler)
{
    uint32_t count_before;
    uint32_t count_after;

    /* 每个独立分频场景都先复位STIMER0，再配置相同周期和采样窗口。 */
    reset_stimer();
    configure_stimer();
    STIMER_setPreScaler(ET_MANUAL_STIMER, prescaler);
    STIMER_startTimer(ET_MANUAL_STIMER);
    count_before = STIMER_getTimerCount(ET_MANUAL_STIMER);
    DWT_delay_us(ET_MANUAL_STIMER_RATE_WINDOW_US);
    count_after = STIMER_getTimerCount(ET_MANUAL_STIMER);
    STIMER_stopTimer(ET_MANUAL_STIMER);

    return count_after - count_before;
}

/*
 * 测试Feature：STIMER可编程预分频对COUNT.LIVE计数速率的影响。
 * 测试方法：STIMER0分别在divider=1和divider=4下复位、计数相同50ms并读取计数增量。
 * 通过条件：两组计数均推进，divider=1的增量约为divider=4的4倍。
 */
int et_manual_stimer_p1_001_prescaler_ratio(void)
{
    uint32_t fast_delta;
    uint32_t slow_delta;

    fast_delta = measure_stimer_delta(ET_MANUAL_STIMER_PRESCALER_FAST);
    slow_delta = measure_stimer_delta(ET_MANUAL_STIMER_PRESCALER_SLOW);

    /* 观测：保留两个Divider、固定时间窗口和COUNT.LIVE增量。 */
    et_manual_log_text("[MANUAL] case=stimer_p1_001 feature=prescaler_ratio\r\n");
    et_manual_log_u32("[CONFIG] fast_divider", ET_MANUAL_STIMER_PRESCALER_FAST);
    et_manual_log_u32("[CONFIG] slow_divider", ET_MANUAL_STIMER_PRESCALER_SLOW);
    et_manual_log_u32("[CONFIG] sample_window_us", ET_MANUAL_STIMER_RATE_WINDOW_US);
    et_manual_log_u32("[OBSERVE] fast_count_delta", fast_delta);
    et_manual_log_u32("[OBSERVE] slow_count_delta", slow_delta);
    et_manual_log_u32("[EXPECT] ratio_min", ET_MANUAL_STIMER_RATE_RATIO_MIN);
    et_manual_log_u32("[EXPECT] ratio_max", ET_MANUAL_STIMER_RATE_RATIO_MAX);

    return ((fast_delta > 0u) && (slow_delta > 0u) &&
            (fast_delta >= (slow_delta * ET_MANUAL_STIMER_RATE_RATIO_MIN)) &&
            (fast_delta <= (slow_delta * ET_MANUAL_STIMER_RATE_RATIO_MAX)))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}

/*
 * 测试Feature：STIMER在Debugger CPU Halt期间的PAUSE与RUN_FREE策略。
 * 测试方法：STIMER0分别配置PAUSE和RUN_FREE；在Keil中逐步执行两个采样循环，每次直接读取CNT_RPT，
 *           使用单步之间的CPU Halt时间作为观测窗口。
 * 通过条件：PAUSE计数增量不超过RUN_FREE的十分之一，且RUN_FREE计数增量大于零。
 */
int et_manual_stimer_p2_003_debugger_halt_behavior(void)
{
    uint32_t pause_delta;
    uint32_t run_delta;
    uint32_t sample_index;

    et_manual_log_text("[MANUAL] case=stimer_p2_003 feature=debugger_halt_behavior\r\n");

    /* 配置：PAUSE场景从独立硬件复位开始，不继承其他STIMER状态。 */
    reset_stimer();
    configure_stimer();
    STIMER_enableCPUHalt(ET_MANUAL_STIMER);
    STIMER_startTimer(ET_MANUAL_STIMER);

    /* 激励：逐步执行，每次从硬件CNT_RPT寄存器直接保留一个PAUSE样本。 */
    for (sample_index = 0u; sample_index < ET_MANUAL_STIMER_DEBUG_SAMPLE_COUNT; ++sample_index)
    {
        et_manual_stimer_pause_samples[sample_index] = ET_MANUAL_STIMER->CNT_RPT;
    }

    pause_delta = et_manual_stimer_pause_samples[ET_MANUAL_STIMER_DEBUG_LAST_SAMPLE_INDEX] -
                  et_manual_stimer_pause_samples[0u];

    /* 配置：RUN_FREE场景再次复位，确保策略切换不依赖前一场景。 */
    reset_stimer();
    configure_stimer();
    STIMER_disableCPUHalt(ET_MANUAL_STIMER);
    STIMER_startTimer(ET_MANUAL_STIMER);

    /* 激励：保持相同单步节奏，直接保留RUN_FREE场景的硬件计数样本。 */
    for (sample_index = 0u; sample_index < ET_MANUAL_STIMER_DEBUG_SAMPLE_COUNT; ++sample_index)
    {
        et_manual_stimer_run_free_samples[sample_index] = ET_MANUAL_STIMER->CNT_RPT;
    }

    run_delta = et_manual_stimer_run_free_samples[ET_MANUAL_STIMER_DEBUG_LAST_SAMPLE_INDEX] -
                et_manual_stimer_run_free_samples[0u];

    /* 观测：同时保留两种策略的原始计数和增量，便于人工复核。 */
    et_manual_log_u32("[OBSERVE] pause_first",
                      et_manual_stimer_pause_samples[0u]);
    et_manual_log_u32("[OBSERVE] pause_last",
                      et_manual_stimer_pause_samples[ET_MANUAL_STIMER_DEBUG_LAST_SAMPLE_INDEX]);
    et_manual_log_u32("[OBSERVE] pause_delta", pause_delta);
    et_manual_log_u32("[OBSERVE] run_free_first",
                      et_manual_stimer_run_free_samples[0u]);
    et_manual_log_u32(
        "[OBSERVE] run_free_last",
        et_manual_stimer_run_free_samples[ET_MANUAL_STIMER_DEBUG_LAST_SAMPLE_INDEX]);
    et_manual_log_u32("[OBSERVE] run_free_delta", run_delta);
    et_manual_log_u32("[EXPECT] pause_ratio_divisor",
                      ET_MANUAL_STIMER_PAUSE_DELTA_RATIO_DIVISOR);

    return ((run_delta > 0u) &&
            (pause_delta <= (run_delta / ET_MANUAL_STIMER_PAUSE_DELTA_RATIO_DIVISOR)))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
