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

/* Define to prevent recursive inclusion ----------------------------------------------------*/
#ifndef __ET6X_STIMER_H
#define __ET6X_STIMER_H

#ifdef __cplusplus
extern "C" {
#endif
/* includes ---------------------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup STIMER
 * @{
 */
/* Exported typedef -------------------------------------------------------------------------*/

/**
 * @brief STIMER interrupt flags
 * @note
 */
//*****************************************************************************
//
// Interrupt flags for use with STIMER_enableInterrupt(), STIMER_disableInterrupt(),
// STIMER_clearInterruptStatus() & STIMER_getInterruptStatus() functions.
//
//*****************************************************************************

#define STIMER_INT_COMPARE_EVT0      0x00000001U  //!< compare event 0
#define STIMER_INT_COMPARE_EVT1      0x00000002U  //!< compare event 1
#define STIMER_INT_COMPARE_EVT2      0x00000004U  //!< compare event 2
#define STIMER_INT_COMPARE_EVT3      0x00000008U  //!< compare event 3
#define STIMER_INT_COUNT_OVERFLOW    0x00000010U  //!< overflow event
#define STIMER_INT_FLAGS_ALL         0x0000001FU  //!< all interrupt flags

//*****************************************************************************
//
// Values that can be returned by STIMER_getStatus().
//
//*****************************************************************************
#define STIMER_STS_COMPARE_EVT0_VAL_ERROR    0x00000001U          //!< compare event 0 value < current counter
#define STIMER_STS_COMPARE_EVT1_VAL_ERROR    0x00000002U          //!< compare event 1 value < current counter
#define STIMER_STS_COMPARE_EVT2_VAL_ERROR    0x00000004U          //!< compare event 2 value < current counter
#define STIMER_STS_COMPARE_EVT3_VAL_ERROR    0x00000008U          //!< compare event 3 value < current counter
#define STIMER_STS_COUNT_OVERFLOW            0x00000010U          //!< overflow event
#define STIMER_STS_COMPARE_EVT0_OVERFLOW     0x00000020U          //!< compare event 0 overflow
#define STIMER_STS_COMPARE_EVT1_OVERFLOW     0x00000040U          //!< compare event 1 overflow
#define STIMER_STS_COMPARE_EVT2_OVERFLOW     0x00000080U          //!< compare event 2 overflow
#define STIMER_STS_COMPARE_EVT3_OVERFLOW     0x00000100U          //!< compare event 3 overflow
#define STIMER_STS_ALL                       0x000001FFU          //!< all status
//*****************************************************************************
//
// Defines that can be used for enabling and disabling DMA requests in the
// STIMER_selectDMARequest() functions.
//
//*****************************************************************************
#define STIMER_DMA_REQ_COUNT_OVERFLOW    0U //!< DMA request source overflow event
#define STIMER_DMA_REQ_COMPARE_EVT0      1U //!< DMA request source compare event 0
#define STIMER_DMA_REQ_COMPARE_EVT1      2U //!< DMA request source compare event 1
#define STIMER_DMA_REQ_COMPARE_EVT2      3U //!< DMA request source compare event 2
#define STIMER_DMA_REQ_COMPARE_EVT3      4U //!< DMA request source compare event 3
//*****************************************************************************
//
//! Values that can be passed to STIMER_setEmulationMode() as the
//! \e mode parameter.
//
//****************************************************************************
typedef enum
{
    //! Denotes that the timer will stop when it reaches zero
    STIMER_EMULATIONMODE_STOPATZERO = 0x0,
    //! Denotes that the timer will run free
    STIMER_EMULATIONMODE_RUNFREE    = 0x1
} STIMER_EmulationMode;

//*****************************************************************************
//
//! Values that can be passed to STIMER_setLoadMode() as the
//! \e mode parameter.
//
//****************************************************************************
typedef enum
{
    //Load immediately mode
    STIMER_LOADMODE_IMMEDIATELY = 0x0,
    //Shadow Loading Mode
    STIMER_LOADMODE_SHADOW      = 0x1
} STIMER_LoadMode;

//
// Counter Compare Module
//
//*****************************************************************************
//
//! Values that can be passed to the STIMER_getCounterCompareStatus()
//! as the \e compModule parameter.
//
//*****************************************************************************
typedef enum
{
    STIMER_COUNTER_COMPARE_0 = 0, //!< Counter compare 0
    STIMER_COUNTER_COMPARE_1 = 1, //!< Counter compare 1
    STIMER_COUNTER_COMPARE_2 = 2, //!< Counter compare 2
    STIMER_COUNTER_COMPARE_3 = 3  //!< Counter compare 3
} STIMER_CounterCompareModule;


/* Basic functions ------------------------------------------------------------------*/
void STIMER_setEmulationMode(STIMER_Type *STIMx, STIMER_EmulationMode mode);
void STIMER_setLoadMode(STIMER_Type *STIMx, STIMER_LoadMode mode);
void STIMER_setPeriod(STIMER_Type *STIMx, uint64_t period);
void STIMER_setPreScaler(STIMER_Type *STIMx, uint16_t prescaler);
uint64_t STIMER_getTimerCountLatch(STIMER_Type *STIMx);
uint32_t STIMER_getTimerCount(STIMER_Type *STIMx);
void STIMER_resetTimerCount(STIMER_Type *STIMx);
void STIMER_startTimer(STIMER_Type *STIMx);
void STIMER_pauseTimer(STIMER_Type *STIMx);
void STIMER_resumeTimer(STIMER_Type *STIMx);
void STIMER_stopTimer(STIMER_Type *STIMx);
void STIMER_reloadTimerCounter(STIMER_Type *STIMx);
void STIMER_enableCPUHalt(STIMER_Type *STIMx);
void STIMER_disableCPUHalt(STIMER_Type *STIMx);
bool STIMER_getTimerOverflowStatus(STIMER_Type *STIMx);
void STIMER_loadCounterCompareValue(STIMER_Type *STIMx, STIMER_CounterCompareModule compModule, uint64_t compCount);
bool STIMER_getStatus(STIMER_Type *STIMx, uint32_t stsFlags);

/* Interrupts and flags management functions --------------------------------------------------*/
void STIMER_enableInterrupt(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_disableInterrupt(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_setInterruptMask(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_clearInterruptMask(STIMER_Type *STIMx, uint32_t intFlags);
bool STIMER_getInterruptStatus(STIMER_Type *STIMx, uint32_t intFlags);
uint32_t STIMER_getAllInterruptStatus(STIMER_Type *STIMx);
bool STIMER_getInterruptStatusRaw(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_clearInterruptStatus(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_forceInterrupt(STIMER_Type *STIMx, uint32_t intFlags);
void STIMER_selectDMARequest(STIMER_Type *STIMx, uint32_t request);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* ET6801 encodes one to 256 event-clock cycles in an 8-bit cycles-minus-one field. */
#define STIMER_TEST_EVENT_PULSE_WIDTH_MIN_CYCLES 1U
#define STIMER_TEST_EVENT_PULSE_WIDTH_MAX_CYCLES ((uint16_t)UINT8_MAX + 1U)

/**
 * @brief Set one hardware-representable 32-bit period for validation.
 * @param STIMx STIMER module base.
 * @param period Period in timer ticks, range 1 to UINT32_MAX.
 * @return DRV_OK after the period load request is issued.
 * @return DRV_PARAM_ERR when period is zero.
 */
DRV_Status STIMER_testSetPeriod32(STIMER_Type *STIMx, uint32_t period);

/**
 * @brief Load one 32-bit compare threshold into the selected channel.
 * @param STIMx STIMER module base.
 * @param compModule Compare channel.
 * @param compareValue Hardware compare threshold.
 * @return DRV_OK after the compare-load request is issued.
 */
DRV_Status STIMER_testLoadCompare32(STIMER_Type *STIMx,
                                    STIMER_CounterCompareModule compModule,
                                    uint32_t compareValue);

/**
 * @brief Read the complete read-to-clear runtime status in one access.
 * @param STIMx STIMER module base.
 * @return Raw STM_STATUS_RPT snapshot captured before hardware clears it.
 */
uint32_t STIMER_testGetStatusSnapshot(STIMER_Type *STIMx);

/**
 * @brief Configure one STIMER event pulse width for validation.
 * @param STIMx STIMER module base.
 * @param eventFlag One STIMER_INT_COMPARE_EVTx or STIMER_INT_COUNT_OVERFLOW flag.
 * @param widthCycles Public pulse width in STIMER clock cycles, range 1 to 256.
 * @return DRV_OK after the event pulse-width register is updated.
 * @return DRV_PARAM_ERR when the source or width cannot be represented.
 */
DRV_Status STIMER_testSetEventPulseWidth(STIMER_Type *STIMx, uint32_t eventFlag,
                                         uint16_t widthCycles);

/**
 * @brief Configure one logical emergency source for STIMER capture validation.
 * @param STIMx STIMER module base.
 * @param stimerIndex ET6801 system-capture index associated with STIMx.
 * @param emergencySignal Emergency trigger group, zero or one.
 * @param sourceMask Chip Driver source mask selected by the chip mapping.
 * @return DRV_OK after the XBAR route is enabled.
 * @return DRV_PARAM_ERR when the index, signal or source mask is invalid.
 *
 * The source mask is intentionally accepted only at the chip-driver
 * extension boundary.  Public Wrap and Service APIs use a logical source ID.
 */
DRV_Status STIMER_testConfigureEmergencyCapture(STIMER_Type *STIMx, uint8_t stimerIndex,
                                                uint8_t emergencySignal,
                                                uint32_t sourceMask);

/**
 * @brief Read the system-level STIMER emergency capture value.
 * @param stimerIndex ET6801 system-capture index.
 * @param count Destination for SYSC.STMx.SYSC_ERG_CNT.
 * @return DRV_OK when the read-only capture register is returned.
 * @return DRV_PARAM_ERR when the index or destination is invalid.
 */
DRV_Status STIMER_testGetEmergencyCapture(uint8_t stimerIndex, uint32_t *count);

/**
 * @brief Disable one STIMER emergency route used by validation.
 * @param stimerIndex ET6801 system-capture index.
 * @param emergencySignal Emergency trigger group, zero or one.
 * @return DRV_OK after the XBAR route is disabled.
 * @return DRV_PARAM_ERR when the index or signal is invalid.
 *
 * ET6801 exposes the capture value as read-only.  This operation clears the
 * trigger route; the read-only value is replaced by the next accepted trigger.
 */
DRV_Status STIMER_testClearEmergencyCapture(uint8_t stimerIndex, uint8_t emergencySignal);

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

#endif /* __ET6X_STIMER_H */
