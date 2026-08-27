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
#ifndef __ET6X_WDG_H
#define __ET6X_WDG_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"
#include "et6x_crg.h"

/** @addtogroup ET6X_Driver
 * @{
 */

/** @addtogroup WDG
 * @{
 */

typedef enum
{
    //! Watchdog can generate a reset signal
    WD_MODE_INTERRUPT_RESET,
    //! Watchdog can generate an interrupt signal; reset signal is disabled
    WD_MODE_INTERRUPT
} WDG_WDMode;

typedef enum
{
    ROUND1_IT_AND_ROUND2_RESET,
    ROUND1_IT_AND_RESET
} WDG_workMode;


void WDG_enableWatchdogInHalt(WDG_Type *WDGx);
void WDG_disableWatchdogInHalt(WDG_Type *WDGx);
void WDG_setWatchdogMode(WDG_Type *WDGx, WDG_WDMode mode);
bool WDG_isWatchdogInterruptActive(WDG_Type *WDGx);
void WDG_disableWatchdog(WDG_Type *WDGx);
void WDG_enableWatchdog(WDG_Type *WDGx);
bool WDG_isWatchdogEnabled(WDG_Type *WDGx);
void WDG_serviceWatchdog(WDG_Type *WDGx);
void WDG_resetWatchdog(WDG_Type *WDGx);
void WDG_setWatchdogReloadValue(WDG_Type *WDGx, uint32_t reload);
uint32_t WDG_getWatchdogCounterValue(WDG_Type *WDGx);
bool WDG_getWatchdogResetStatus(WDG_Type *WDGx);
void WDG_clearWatchdogResetStatus(WDG_Type *WDGx);
bool WDG_getWatchdogInterruptRecordStatus(WDG_Type *WDGx);
void WDG_clearWatchdogInterruptRecordStatus(WDG_Type *WDGx);
void WDG_setWatchdogWindowValue(WDG_Type *WDGx, uint32_t lowThreshold, uint32_t highThreshold);
void WDG_enableWindowedWatchdog(WDG_Type *WDGx);
void WDG_disableWindowedWatchdog(WDG_Type *WDGx);
void WDG_setWatchdogWorkMode(WDG_Type *WDGx, WDG_workMode workMode);
void WDG_lock(WDG_Type *WDGx);
void WDG_unlock(WDG_Type *WDGx);
void WDG_enableInterrupt(WDG_Type *WDGx);
void WDG_disableInterrupt(WDG_Type *WDGx);
void WDG_maskInterrupt(WDG_Type *WDGx);
void WDG_unmaskInterrupt(WDG_Type *WDGx);
ITStatus WDG_getInterruptStatus(WDG_Type *WDGx);
ITStatus WDG_getRawInterruptStatus(WDG_Type *WDGx);
void WDG_clearInterruptStatus(WDG_Type *WDGx);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Snapshot protected watchdog configuration for validation.
 * @note This type is test-only and remains isolated from the released Driver API.
 */
typedef struct
{
    uint32_t reload;
    uint32_t window_low;
    uint32_t window_high;
    uint8_t window_mode;
    uint8_t work_mode;
    uint8_t reset_enable;
    uint8_t halt_pause_enable;
} WDG_TestConfigSnapshot;

DRV_Status WDG_testGetConfiguration(WDG_Type *WDGx, WDG_TestConfigSnapshot *snapshot);
DRV_Status WDG_testForceInterrupt(WDG_Type *WDGx);
DRV_Status WDG_testResetModule(WDG_Type *WDGx);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /*__ET6X_WDG_H */
