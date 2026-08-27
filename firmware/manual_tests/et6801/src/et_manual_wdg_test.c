#include <stdint.h>

#include "et6x_cortex.h"
#include "et6x_crg.h"
#include "et6x_wdg.h"
#include "et_manual_test_config.h"
#include "et_manual_test_internal.h"

static void reset_wdg(void)
{
    CRG_unlockClockConfig();
    (void)WDG_testResetModule(ET_MANUAL_WDG);
    CRG_lockClockConfig();
}

static void configure_wdg(uint32_t reload)
{
    WDG_unlock(ET_MANUAL_WDG);
    WDG_disableWatchdog(ET_MANUAL_WDG);
    WDG_setWatchdogMode(ET_MANUAL_WDG, WD_MODE_INTERRUPT);
    WDG_disableWindowedWatchdog(ET_MANUAL_WDG);
    WDG_setWatchdogWorkMode(ET_MANUAL_WDG, ROUND1_IT_AND_ROUND2_RESET);
    WDG_setWatchdogReloadValue(ET_MANUAL_WDG, reload);
}

static void select_wdg_apb1_clock(uint8_t divider)
{
    CRG_unlockClockConfig();
    CRG_selectWDGClockSource(ET_MANUAL_WDG, CRG_WDG_CLKSRC_APB1, divider);
    CRG_lockClockConfig();
}

/*
 * 测试Feature：WDG模块复位以及复位后的重新配置和计数恢复。
 * 测试方法：WDG0先建立非默认运行状态，执行模块复位，再写入另一Reload并重新启动。
 * 通过条件：复位前WDG使能、复位后WDG禁用、重新配置后WDG再次使能且Counter大于零。
 */
int et_manual_wdg_p1_004_module_reset_and_recovery(void)
{
    uint32_t counter_before;
    uint32_t counter_after_reset;
    uint32_t counter_recovered;
    uint32_t enabled_before;
    uint32_t enabled_after_reset;
    uint32_t enabled_recovered;

    /* 配置：Case开始先复位WDG0，再建立明确的非默认运行状态。 */
    reset_wdg();
    configure_wdg(ET_MANUAL_WDG_ACTIVE_RELOAD);
    WDG_enableWatchdog(ET_MANUAL_WDG);
    enabled_before = WDG_isWatchdogEnabled(ET_MANUAL_WDG) ? 1u : 0u;
    counter_before = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);

    /* 激励：在CRG写保护已解锁的窗口内执行模块级复位。 */
    reset_wdg();
    enabled_after_reset = WDG_isWatchdogEnabled(ET_MANUAL_WDG) ? 1u : 0u;
    counter_after_reset = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);

    /* 恢复：复位后重新配置另一组Reload并启动计数。 */
    configure_wdg(ET_MANUAL_WDG_RECOVERY_RELOAD);
    WDG_enableWatchdog(ET_MANUAL_WDG);
    enabled_recovered = WDG_isWatchdogEnabled(ET_MANUAL_WDG) ? 1u : 0u;
    counter_recovered = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);

    /* 观测：打印复位前、复位后和恢复后的实际硬件状态。 */
    et_manual_log_text("[MANUAL] case=wdg_p1_004 feature=module_reset_and_recovery\r\n");
    et_manual_log_u32("[OBSERVE] enabled_before", enabled_before);
    et_manual_log_u32("[OBSERVE] counter_before", counter_before);
    et_manual_log_u32("[OBSERVE] enabled_after_reset", enabled_after_reset);
    et_manual_log_u32("[OBSERVE] counter_after_reset", counter_after_reset);
    et_manual_log_u32("[OBSERVE] enabled_recovered", enabled_recovered);
    et_manual_log_u32("[OBSERVE] counter_recovered", counter_recovered);
    et_manual_log_u32("[EXPECT] recovered_reload", ET_MANUAL_WDG_RECOVERY_RELOAD);

    return ((enabled_before != 0u) && (enabled_after_reset == 0u) &&
            (enabled_recovered != 0u) && (counter_recovered > 0u))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}

/*
 * 测试Feature：CRG的WDG APB1 divider=0/1选择及其对WDG Counter速率的影响。
 * 测试方法：两个Divider场景分别先复位WDG0，在相同DWT时间窗口内读取Counter递减量和CRG读回。
 * 通过条件：源和Divider读回正确、两组Counter都递减，divider=0速率至少为divider=1的1.5倍。
 */
int et_manual_wdg_p2_001_clock_divider_rate(void)
{
    CRG_TestWdgClockSnapshot divider_zero_clock;
    CRG_TestWdgClockSnapshot divider_one_clock;
    uint32_t divider_zero_before;
    uint32_t divider_zero_after;
    uint32_t divider_zero_delta;
    uint32_t divider_one_before;
    uint32_t divider_one_after;
    uint32_t divider_one_delta;

    /* 配置：divider=0场景从独立WDG复位开始。 */
    reset_wdg();
    select_wdg_apb1_clock(ET_MANUAL_WDG_DIVIDER_ZERO);
    (void)CRG_testGetWDGClockConfig(ET_MANUAL_WDG, &divider_zero_clock);
    configure_wdg(ET_MANUAL_WDG_RATE_RELOAD);
    WDG_enableWatchdog(ET_MANUAL_WDG);
    divider_zero_before = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);
    DWT_delay_us(ET_MANUAL_WDG_RATE_WINDOW_US);
    divider_zero_after = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);
    divider_zero_delta = divider_zero_before - divider_zero_after;

    /* 配置：divider=1场景再次复位WDG，不继承前一场景状态。 */
    reset_wdg();
    select_wdg_apb1_clock(ET_MANUAL_WDG_DIVIDER_ONE);
    (void)CRG_testGetWDGClockConfig(ET_MANUAL_WDG, &divider_one_clock);
    configure_wdg(ET_MANUAL_WDG_RATE_RELOAD);
    WDG_enableWatchdog(ET_MANUAL_WDG);
    divider_one_before = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);
    DWT_delay_us(ET_MANUAL_WDG_RATE_WINDOW_US);
    divider_one_after = WDG_getWatchdogCounterValue(ET_MANUAL_WDG);
    divider_one_delta = divider_one_before - divider_one_after;

    /* 观测：保存CRG字段和同一目标时间窗口内的原始Counter样本。 */
    et_manual_log_text("[MANUAL] case=wdg_p2_001 feature=clock_divider_rate\r\n");
    et_manual_log_u32("[OBSERVE] divider_zero_source", divider_zero_clock.source);
    et_manual_log_u32("[OBSERVE] divider_zero_readback", divider_zero_clock.divider);
    et_manual_log_u32("[OBSERVE] divider_zero_before", divider_zero_before);
    et_manual_log_u32("[OBSERVE] divider_zero_after", divider_zero_after);
    et_manual_log_u32("[OBSERVE] divider_zero_delta", divider_zero_delta);
    et_manual_log_u32("[OBSERVE] divider_one_source", divider_one_clock.source);
    et_manual_log_u32("[OBSERVE] divider_one_readback", divider_one_clock.divider);
    et_manual_log_u32("[OBSERVE] divider_one_before", divider_one_before);
    et_manual_log_u32("[OBSERVE] divider_one_after", divider_one_after);
    et_manual_log_u32("[OBSERVE] divider_one_delta", divider_one_delta);
    et_manual_log_u32("[CONFIG] sample_window_us", ET_MANUAL_WDG_RATE_WINDOW_US);

    return ((divider_zero_clock.source == (uint8_t)CRG_WDG_CLKSRC_APB1) &&
            (divider_one_clock.source == (uint8_t)CRG_WDG_CLKSRC_APB1) &&
            (divider_zero_clock.divider == ET_MANUAL_WDG_DIVIDER_ZERO) &&
            (divider_one_clock.divider == ET_MANUAL_WDG_DIVIDER_ONE) &&
            (divider_zero_delta > 0u) && (divider_one_delta > 0u) &&
            ((divider_zero_delta * ET_MANUAL_WDG_RATE_RATIO_DENOMINATOR) >=
             (divider_one_delta * ET_MANUAL_WDG_RATE_RATIO_NUMERATOR)))
               ? ET_MANUAL_RESULT_PASS
               : ET_MANUAL_RESULT_FAIL;
}
