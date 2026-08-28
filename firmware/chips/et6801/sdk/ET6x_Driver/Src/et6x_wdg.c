/*
 * Copyright (c) 2022, Chengdu ET Microelectronics Co., Ltd.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the, distribution.
 * 3. All advertising materials mentioning features or use of this software
 *    must display the following acknowledgement:
 *    This product includes software developed by the "ETMCU software". and
 *    its contributors.
 * 4. Neither the name of the Group nor the names of its contributors may
 *    be used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
 * PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
 * OF SUCH DAMAGE.
 */

/* Includes ------------------------------------------------------------------*/
#include "et6x_wdg.h"

#define WDG_UNLOCK_VALUE    (0x1ACCE551U)
#define WDG_LOCK_VALUE      (0)

/*! Parameter validity check for WDG peripheral  */
#define IS_WDG_PERIPHERAL(x) \
        (((x) == WDG0) ||        \
         ((x) == WDG1))

/**
 * @brief Enable watchdog counter pause while the CPU is halted by a debugger.
 *
 * @param WDGx watch dog module base
 */
void WDG_enableWatchdogInHalt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->CTRL, WDG0_CTRL_HALT_EN_Msk);

    if (WDGx == WDG0)
    {
        SET_BIT(SYSC->CTRL, SYSC_CTRL_WDG0_HALT_MODE_EN_Msk);
    }
    else
    {
        SET_BIT(SYSC->CTRL, SYSC_CTRL_WDG1_HALT_MODE_EN_Msk);
    }
}

/**
 * @brief Disable watchdog counter pause while the CPU is halted by a debugger.
 *
 * @param WDGx watch dog module base
 */
void WDG_disableWatchdogInHalt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    CLEAR_BIT(WDGx->CTRL, WDG0_CTRL_HALT_EN_Msk);

    if (WDGx == WDG0)
    {
        CLEAR_BIT(SYSC->CTRL, SYSC_CTRL_WDG0_HALT_MODE_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SYSC->CTRL, SYSC_CTRL_WDG1_HALT_MODE_EN_Msk);
    }
}

/**
 * @brief Configures whether the watchdog generates a reset or an interrupt signal.
 *
 * @param WDGx watch dog module base
 * @param mode select interrupt or reset
 */
void WDG_setWatchdogMode(WDG_Type *WDGx, WDG_WDMode mode)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (mode == WD_MODE_INTERRUPT_RESET)
    {
        SET_BIT(WDGx->CTRL, WDG0_CTRL_RST_EN_Msk);
    }
    else
    {
        CLEAR_BIT(WDGx->CTRL, WDG0_CTRL_RST_EN_Msk);
    }
}

/**
 * @brief Gets the status of the watchdog interrupt signal.
 *
 * @param WDGx watch dog module base
 */
bool WDG_isWatchdogInterruptActive(WDG_Type *WDGx)
{
    if (READ_BIT(WDGx->INT_STATUS_RPT, WDG0_INT_STATUS_RPT_WWDG_INT_STATUS_RPT_Msk) != 0)
    {
        return true;
    }
    else
    {
        return false;
    }
}

/**
 * @brief Disable WDG work
 *
 * @param WDGx watch dog module base
 */
void WDG_disableWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    CLEAR_BIT(WDGx->EN, WDG0_EN_WWDG_EN_Msk);
}

/**
 * @brief Enable WDG work
 *
 * @param WDGx watch dog module base
 */
void WDG_enableWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->EN, WDG0_EN_WWDG_EN_Msk);
}

/**
 * @brief Checks if the watchdog is enabled or not
 *
 * @param WDGx watch dog module base
 */
bool WDG_isWatchdogEnabled(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (READ_BIT(WDGx->EN, WDG0_EN_WWDG_EN_Msk) != 0)
    {
        return true;
    }
    else
    {
        return false;
    }
}

/**
 * @brief Services the watchdog.
 *
 * @param WDGx watch dog module base
 */
void WDG_serviceWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->RELOAD_REQ, WDG0_RELOAD_REQ_WWDG_RELOAD_REQ_Msk);
}

/**
 * @brief Reset the watchdog.
 *
 * @param WDGx watch dog module base
 */
void WDG_resetWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (WDGx == WDG0)
    {
        CRG_resetPeripheral(CRG_PERIPH_WDG0);
    }
    else
    {
        CRG_resetPeripheral(CRG_PERIPH_WDG1);
    }
}

/**
 * @brief Set the watchdog reload value.
 *
 * @param WDGx watch dog module base
 */
void WDG_setWatchdogReloadValue(WDG_Type *WDGx, uint32_t reload)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->RELOAD, reload);
}

/**
 * @brief Gets the watchdog counter value.
 *
 * @param WDGx watch dog module base
 */
uint32_t WDG_getWatchdogCounterValue(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    return READ_REG(WDGx->CUR_VAL);
}

/**
 * @brief Gets the watchdog reset status.
 *
 * @param WDGx watch dog module base
 */
bool WDG_getWatchdogResetStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (WDGx == WDG0)
    {
        if (READ_BIT(SYSC->RST_REC, SYSC_RST_REC_WDG0_RST_REC_Msk) != 0)
        {
            return true;
        }
        else
        {
            return false;
        }
    }
    else
    {
        if (READ_BIT(SYSC->RST_REC, SYSC_RST_REC_WDG1_RST_REC_Msk) != 0)
        {
            return true;
        }
        else
        {
            return false;
        }
    }
}

/**
 * @brief Clears the watchdog reset status.
 *
 * @param WDGx watch dog module base
 */
void WDG_clearWatchdogResetStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (WDGx == WDG0)
    {
        SET_BIT(SYSC->RST_REC, SYSC_RST_REC_WDG0_RST_REC_Msk);
    }
    else
    {
        SET_BIT(SYSC->RST_REC, SYSC_RST_REC_WDG1_RST_REC_Msk);
    }
}

/**
 * @brief Gets the watchdog interrupt status.
 *
 * @param WDGx watch dog module base
 */
bool WDG_getWatchdogInterruptRecordStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (WDGx == WDG0)
    {
        if (READ_BIT(SYSC->RST_REC, SYSC_RST_REC_SYSC_WDG0_INT_REC_Msk) != 0)
        {
            return true;
        }
        else
        {
            return false;
        }
    }
    else
    {
        if (READ_BIT(SYSC->RST_REC, SYSC_RST_REC_SYSC_WDG1_INT_REC_Msk) != 0)
        {
            return true;
        }
        else
        {
            return false;
        }
    }
}

/**
 * @brief Clears the watchdog interrupt status.
 *
 * @param WDGx watch dog module base
 */
void WDG_clearWatchdogInterruptRecordStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (WDGx == WDG0)
    {
        SET_BIT(SYSC->RST_REC, SYSC_RST_REC_SYSC_WDG0_INT_REC_Msk);
    }
    else
    {
        SET_BIT(SYSC->RST_REC, SYSC_RST_REC_SYSC_WDG1_INT_REC_Msk);
    }
}

/**
 * @brief Set the window value for windowed watchdog
 *
 * @param WDGx watch dog module base
 */
void WDG_setWatchdogWindowValue(WDG_Type *WDGx, uint32_t lowThreshold, uint32_t highThreshold)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->HIGH_THRESHOLD, highThreshold);
    WRITE_REG(WDGx->LOW_THRESHOLD, lowThreshold);
}

/**
 * @brief Enable windowed watchdog
 *
 * @param WDGx watch dog module base
 */
void WDG_enableWindowedWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    CLEAR_BIT(WDGx->MODE, WDG0_MODE_WWDG_MODE_Msk);
}

/**
 * @brief Disable windowed watchdog
 *
 * @param WDGx watch dog module base
 */
void WDG_disableWindowedWatchdog(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->MODE, WDG0_MODE_WWDG_MODE_Msk);
}

/**
 * @brief Disable windowed watchdog
 *
 * @param WDGx watch dog module base
 */
void WDG_setWatchdogWorkMode(WDG_Type *WDGx, WDG_workMode workMode)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->WORK_MODE, workMode);
}

/**
 * @brief Lock WDG module register write operation
 *
 * @param WDGx watch dog module base
 */
void WDG_lock(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->LOCK, 0x0);
}

/**
 * @brief Unlock WDG module register write operation
 *
 * @param WDGx watch dog module base
 */
void WDG_unlock(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->LOCK, 0x1ACCE551);
}

/**
 * @brief Enable interrupt
 *
 * @param WDGx watch dog module base
 */
void WDG_enableInterrupt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->INT_EN, WDG0_INT_EN_WWDG_INT_EN_Msk);
}

/**
 * @brief Disable interrupt
 *
 * @param WDGx watch dog module base
 */
void WDG_disableInterrupt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    CLEAR_BIT(WDGx->INT_EN, WDG0_INT_EN_WWDG_INT_EN_Msk);
}

/**
 * @brief Mask interrupt
 *
 * @param WDGx watch dog module base
 */
void WDG_maskInterrupt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    SET_BIT(WDGx->INT_MASK, WDG0_INT_MASK_WWDG_INT_MASK_Msk);
}

/**
 * @brief Unmask interrupt
 *
 * @param WDGx watch dog module base
 */
void WDG_unmaskInterrupt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    CLEAR_BIT(WDGx->INT_MASK, WDG0_INT_MASK_WWDG_INT_MASK_Msk);
}

/**
 * @brief Get WDG interrupt status
 * @param WDGx watch dog module base
 * @retval  ITStatus
 *          SET: WDGx is in interrupt
 *          RESET: WDGx is not in interrupt
 */
ITStatus WDG_getInterruptStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (READ_BIT(WDGx->INT_STATUS_RPT, WDG0_INT_STATUS_RPT_WWDG_INT_STATUS_RPT_Msk) != 0)
    {
        return SET;
    }
    else
    {
        return RESET;
    }
}

/**
 * @brief Get WDG raw interrupt status
 *
 * @param WDGx watch dog module base
 * @retval  ITStatus
 *          SET: WDGx is in interrupt
 *          RESET: WDGx is not in interrupt
 */
ITStatus WDG_getRawInterruptStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (READ_BIT(WDGx->INT_RAW_RPT, WDG0_INT_RAW_RPT_WWDG_INT_RAW_RPT_Msk) != 0)
    {
        return SET;
    }
    else
    {
        return RESET;
    }
}

/**
 * @brief clear WDG interrupt signal
 *
 * @param WDGx watch dog module base
 */
void WDG_clearInterruptStatus(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->INT_CLR, WDG0_INT_CLR_WWDG_INT_CLR_Msk);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* Hold the active-low peripheral reset across a bounded number of CPU cycles.
 * The released CRG helper uses an optimizable empty loop, so it cannot provide
 * a deterministic reset pulse in an optimized validation firmware build. */
#define WDG_TEST_RESET_HOLD_ITERATIONS (1024U)

/**
 * @brief Read one coherent watchdog configuration snapshot for validation.
 *
 * @param WDGx Watchdog module base.
 * @param snapshot Destination test snapshot.
 * @return DRV_OK when the snapshot is returned.
 * @return DRV_PARAM_ERR when snapshot is NULL.
 */
DRV_Status WDG_testGetConfiguration(WDG_Type *WDGx, WDG_TestConfigSnapshot *snapshot)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    if (snapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    snapshot->reload = READ_REG(WDGx->RELOAD);
    snapshot->window_low = READ_REG(WDGx->LOW_THRESHOLD);
    snapshot->window_high = READ_REG(WDGx->HIGH_THRESHOLD);
    snapshot->window_mode =
        (READ_BIT(WDGx->MODE, WDG0_MODE_WWDG_MODE_Msk) == 0U) ? 1U : 0U;
    snapshot->work_mode =
        (uint8_t)(READ_BIT(WDGx->WORK_MODE, WDG0_WORK_MODE_WWDG_WORK_MODE_Msk) >>
                  WDG0_WORK_MODE_WWDG_WORK_MODE_Pos);
    snapshot->reset_enable =
        (READ_BIT(WDGx->CTRL, WDG0_CTRL_RST_EN_Msk) != 0U) ? 1U : 0U;
    /* Public test semantics and hardware HALT_EN both use 1=paused during Halt. */
    snapshot->halt_pause_enable =
        (READ_BIT(WDGx->CTRL, WDG0_CTRL_HALT_EN_Msk) != 0U) ? 1U : 0U;

    return DRV_OK;
}

/**
 * @brief Force the watchdog interrupt source for deterministic validation.
 *
 * @param WDGx Watchdog module base.
 * @return DRV_OK after issuing the self-clearing force pulse.
 */
DRV_Status WDG_testForceInterrupt(WDG_Type *WDGx)
{
    assert_param(IS_WDG_PERIPHERAL(WDGx));

    WRITE_REG(WDGx->INT_FORCE_IND, WDG0_INT_FORCE_IND_WWDG_INT_FORCE_IND_Msk);

    return DRV_OK;
}

/**
 * @brief Reset the selected watchdog using the ET6801 CRG reset-bit position.
 *
 * @param WDGx Watchdog module base.
 * @return DRV_OK after the assert/deassert reset sequence.
 * @note The released WDG_resetWatchdog API uses legacy CRG enum values that do
 *       not match the ET6801 SRST0 WDG bit positions. Keep this correction in
 *       the removable test extension until the released SDK Driver is fixed.
 */
DRV_Status WDG_testResetModule(WDG_Type *WDGx)
{
    uint32_t reset_mask;
    volatile uint32_t delay;

    assert_param(IS_WDG_PERIPHERAL(WDGx));

    reset_mask = (WDGx == WDG0) ? CRG_SRST0_CRG_SRST_N_WDG0_Msk
                                : CRG_SRST0_CRG_SRST_N_WDG1_Msk;

    /* SRST0 is write-protected; own the complete unlock/reset/lock sequence. */
    CRG_unlockClockConfig();
    CLEAR_BIT(CRG->SRST0, reset_mask);
    __DSB();

    for (delay = 0U; delay < WDG_TEST_RESET_HOLD_ITERATIONS; delay++)
    {
        __NOP();
    }

    SET_BIT(CRG->SRST0, reset_mask);
    __DSB();
    CRG_lockClockConfig();

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
