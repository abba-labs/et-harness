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

#ifndef __ET6X_QEP_H
#define __ET6X_QEP_H

#include "et6x.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup QEP
 * @{
 */

/** @defgroup QEP_CountMode
 * @{
 */
#define QEP_CONFIG_QUADRATURE    0x00000000U  /* quadrature counting mode */
#define QEP_CONFIG_CLOCK_DIR     0x40000000U  /* direction counting mode */
#define QEP_CONFIG_UP_COUNT      0x80000000U  /* Up-count mode, QDIR = 1 */
#define QEP_CONFIG_DOWN_COUNT    0xC0000000U  /* Down-count mode, QDIR = 0 */

/**
 * @}
 */
/** @defgroup QEP_NonQuadrature_SigDectMode
 * @{
 */
#define QEP_CONFIG_2X_RESOLUTION    0x00000000U /* Count rising and falling edge, in NonQuadrature mode */
#define QEP_CONFIG_1X_RESOLUTION    0x08000000U /* Count rising edge only, in NonQuadrature mode */

/**
 * @}
 */
/** @defgroup QEP_AB_SwapMode
 * @{
 */
#define QEP_CONFIG_NO_SWAP    0x00000000U     /* Do not swap QEPA and QEPB */
#define QEP_CONFIG_SWAP       0x04000000U     /* Swap QEPA and QEPB */

/**
 * @}
 */
/** @defgroup QEP_iGate_Mode
 * @{
 */
#define QEP_CONFIG_IGATE_DISABLE    0x00000000U   /* Disable gating of Index pulse */
#define QEP_CONFIG_IGATE_ENABLE     0x02000000U   /* Gate the index pin with strobe */

/**
 * @}
 */
/** @defgroup QEP_Interrupt_Source
 * @{
 */
#define QEP_INT_DIR_CHANGE           0x0001U  /* Quadrature direction change */
#define QEP_INT_PHASE_ERROR          0x0002U  /* Quadrature phase error */
#define QEP_INT_POS_CNT_ERROR        0x0004U  /* Position counter error */
#define QEP_INT_STROBE_EVNT_LATCH    0x0008U  /* Strobe event latch */
#define QEP_INT_INDEX_EVNT_LATCH     0x0010U  /* Index event latch */
#define QEP_INT_POS_COMP_READY       0x0020U  /* Position-compare ready */
#define QEP_INT_POS_COMP_MATCH       0x0040U  /* Position-compare match */
#define QEP_INT_UNDERFLOW            0x0080U  /* Position counter underflow */
#define QEP_INT_OVERFLOW             0x0100U  /* Position counter overflow */
#define QEP_INT_WATCHDOG             0x0200U  /* Watchdog time-out */
#define QEP_INT_UNIT_TIME_OUT        0x0400U  /* Unit time-out */
#define QEP_INT_QMA_ERROR            0x0800U  /* QMA error */

/**
 * @}
 */
/** @defgroup QEP_Status
 * @{
 */
#define QEP_STS_POS_CNT_ERROR       0x0001U   /* Position counter error occurred */
#define QEP_STS_1ST_IDX_FLAG        0x0002U   /* Set by the occurrence of the first index pulse */
#define QEP_STS_CAP_DIR_ERROR       0x0004U   /* Direction change occurred between position capture events */
#define QEP_STS_CAP_OVRFLW_ERROR    0x0008U   /* Overflow occurred in QEP capture timer */
#define QEP_STS_DIR_LATCH           0x0010U   /*  If set, clockwise rotation occurred on last index event marker */
#define QEP_STS_DIR_FLAG            0x0020U   /* If set, movement is clockwise rotation */
#define QEP_STS_DIR_ON_1ST_IDX      0x0040U   /* If set, clockwise rotation (forward movement) occurred on the first
                                               * index event */
#define QEP_STS_UNIT_POS_EVNT       0x0080U   /* Unit position event detected */

/**
 * @}
 */
/** @defgroup QEP_InitMode
 * @{
 */
#define QEP_INIT_DO_NOTHING         0x0000U  /* Action is disabled */
#define QEP_INIT_RISING_STROBE      0x0800U  /* On rising edge of strobe */
#define QEP_INIT_EDGE_DIR_STROBE    0x0C00U  /* On rising edge when clockwise, on falling when counter clockwise */
#define QEP_INIT_RISING_INDEX       0x0200U  /* On rising edge of index */
#define QEP_INIT_FALLING_INDEX      0x0300U  /* On falling edge of index */

/**
 * @}
 */
/** @defgroup QEP_LatchMode
 * @{
 */
#define QEP_LATCH_CNT_READ_BY_CPU    0x0000U /* On position counter read */
#define QEP_LATCH_UNIT_TIME_OUT      0x0004U /* On unit time-out event */

#define QEP_LATCH_RISING_INDEX       0x0010U /* On rising edge of index */
#define QEP_LATCH_FALLING_INDEX      0x0020U /* On falling edge of index */
#define QEP_LATCH_SW_INDEX_MARKER    0x0030U /* On software index marker */

#define QEP_LATCH_RISING_STROBE      0x0000U /* On rising edge of strobe */
#define QEP_LATCH_EDGE_DIR_STROBE    0x0040U /* On rising edge when clockwise, on falling when counter clockwise */

/**
 * @}
 */
/** @defgroup QEP_CompareOutputMode
 * @{
 */
typedef enum
{
    QEP_COMPARE_IDX_SYNC_OUT    = 0x00U,    /* Sync output on index pin */
    QEP_COMPARE_STROBE_SYNC_OUT = 0x01U     /* Sync output on strobe pin */
} QEP_CompareSyncOut;

typedef enum
{
    QEP_COMPARE_LOAD_ON_ZERO  = 0x00U,   /* Load on QPOSCNT = 0 */
    QEP_COMPARE_LOAD_ON_MATCH = 0x01U    /* Load on QPOSCNT = QPOSCMP */
} QEP_Compare_ShadowSigSel;

/**
 * @}
 */
typedef enum
{
    QEP_POSITION_RESET_IDX           = 0x00U,   /* Reset position on index pulse */
    QEP_POSITION_RESET_MAX_POS       = 0x01U,   /* Reset position on maximum position */
    QEP_POSITION_RESET_1ST_IDX       = 0x02U,   /* Reset position on the first index pulse */
    QEP_POSITION_RESET_UNIT_TIME_OUT = 0x03U    /* Reset position on a unit time event */
} QEP_PositionResetMode;

typedef enum
{
    QEP_CAPTURE_CLK_DIV_1   = 0x00U,    /* CAPCLK = SYSCLKOUT/1 */
    QEP_CAPTURE_CLK_DIV_2   = 0x01U,    /* CAPCLK = SYSCLKOUT/2 */
    QEP_CAPTURE_CLK_DIV_4   = 0x02U,    /* CAPCLK = SYSCLKOUT/4 */
    QEP_CAPTURE_CLK_DIV_8   = 0x03U,    /* CAPCLK = SYSCLKOUT/8 */
    QEP_CAPTURE_CLK_DIV_16  = 0x04U,    /* CAPCLK = SYSCLKOUT/16 */
    QEP_CAPTURE_CLK_DIV_32  = 0x05U,    /* CAPCLK = SYSCLKOUT/32 */
    QEP_CAPTURE_CLK_DIV_64  = 0x06U,    /* CAPCLK = SYSCLKOUT/64 */
    QEP_CAPTURE_CLK_DIV_128 = 0x07U     /* CAPCLK = SYSCLKOUT/128 */
} QEP_CAPCLKPrescaler;
typedef enum
{
    QEP_UNIT_POS_EVNT_DIV_1    = 0x00U,   /* UPEVNT = QCLK/1 */
    QEP_UNIT_POS_EVNT_DIV_2    = 0x01U,   /* UPEVNT = QCLK/2 */
    QEP_UNIT_POS_EVNT_DIV_4    = 0x02U,   /* UPEVNT = QCLK/4 */
    QEP_UNIT_POS_EVNT_DIV_8    = 0x03U,   /* UPEVNT = QCLK/8 */
    QEP_UNIT_POS_EVNT_DIV_16   = 0x04U,   /* UPEVNT = QCLK/16 */
    QEP_UNIT_POS_EVNT_DIV_32   = 0x05U,   /* UPEVNT = QCLK/32 */
    QEP_UNIT_POS_EVNT_DIV_64   = 0x06U,   /* UPEVNT = QCLK/64 */
    QEP_UNIT_POS_EVNT_DIV_128  = 0x07U,   /* UPEVNT = QCLK/128 */
    QEP_UNIT_POS_EVNT_DIV_256  = 0x08U,   /* UPEVNT = QCLK/256 */
    QEP_UNIT_POS_EVNT_DIV_512  = 0x09U,   /* UPEVNT = QCLK/512 */
    QEP_UNIT_POS_EVNT_DIV_1024 = 0x0AU,   /* UPEVNT = QCLK/1024 */
    QEP_UNIT_POS_EVNT_DIV_2048 = 0x0BU    /* UPEVNT = QCLK/2048 */
} QEP_UPEVNTPrescaler;
typedef enum
{
    QEP_QMA_MODE_BYPASS = 0x00U,   /* QMA module is bypassed */
    QEP_QMA_MODE_1      = 0x01U,   /* QMA mode-1 operation is selected */
    QEP_QMA_MODE_2      = 0x02U    /* QMA mode-2 operation is selected */
} QEP_QMAMode;

typedef enum
{
    QEP_SOURCE_DEVICE_PIN      = 0x00U,   /* signal comes from Device Pin */
    QEP_SOURCE_ACMP0L          = 0x01U,   /* signal comes from ACMP0 cmpc_ctripl[0]*/
    QEP_SOURCE_ACMP1L          = 0x02U,   /* signal comes from ACMP1 cmpc_ctripl[1]*/
    QEP_SOURCE_ACMP2L          = 0x03U,   /* signal comes from ACMP2 cmpc_ctripl[2]*/
    QEP_SOURCE_ACMP3L          = 0x04U,   /* signal comes from ACMP3 cmpc_ctripl[3]*/
    QEP_SOURCE_ACMP0H          = 0x05U,   /* signal comes from ACMP0 cmpc_ctriph[0]*/
    QEP_SOURCE_ACMP1H          = 0x06U,   /* signal comes from ACMP1 cmpc_ctriph[1]*/
    QEP_SOURCE_ACMP2H          = 0x07U,   /* signal comes from ACMP2 cmpc_ctriph[2]*/
    QEP_SOURCE_ACMP3H          = 0x08U,   /* signal comes from ACMP3 cmpc_ctriph[3]*/
    QEP_SOURCE_XBAR_GRP0_PFXB0 = 0x09U,   /* signal comes from PWMXBAR1 XBAR2PWM_fault[0]*/
    QEP_SOURCE_XBAR_GRP0_PFXB1 = 0x0AU,   /* signal comes from PWMXBAR2 XBAR2PWM_fault[1]*/
    QEP_SOURCE_XBAR_GRP0_PFXB2 = 0x0BU,   /* signal comes from PWMXBAR3 XBAR2PWM_fault[2]*/
    QEP_SOURCE_XBAR_GRP0_PFXB3 = 0x0CU,   /* signal comes from PWMXBAR4 XBAR2PWM_fault[3]*/
    QEP_SOURCE_XBAR_GRP0_PFXB4 = 0x0DU,   /* signal comes from PWMXBAR5 XBAR2PWM_fault[4]*/
    QEP_SOURCE_XBAR_GRP0_PFXB5 = 0x0EU,   /* signal comes from PWMXBAR6 XBAR2PWM_fault[5]*/
    QEP_SOURCE_XBAR_GRP1_PFXB0 = 0x0FU    /* signal comes from PWMXBAR7 XBAR2PWM_fault[6]*/
} QEP_Source;
typedef struct
{
    QEP_Source sourceA;
    QEP_Source sourceB;
    QEP_Source sourceIndex;
} QEP_SourceSelect;
typedef enum
{
    QEP_EMULATIONMODE_STOPIMMEDIATELY = 0x00U, /* Counters stop immediately */
    QEP_EMULATIONMODE_STOPATROLLOVER  = 0x01U, /* Counters stop at period rollover */
    QEP_EMULATIONMODE_RUNFREE         = 0x02U  /* Counter unaffected by suspend */
} QEP_EmulationMode;

typedef enum
{
    QEP_STROBE_FROM_GPIO  = 0x00U,   /* Strobe signal comes from GPIO */
    QEP_STROBE_OR_ADCSOCA = 0x02U,   /* Strobe signal is OR'd with ADCSOCA */
    QEP_STROBE_OR_ADCSOCB = 0x03U    /* Strobe signal is OR'd with ADCSOCB */
} QEP_StrobeSource;

typedef struct
{
    FunctionalState          compareOutputEn;
    FunctionalState          Outputpolarity;
    QEP_CompareSyncOut       compareOutputPinSel;

    FunctionalState          shadowModeEn;
    QEP_Compare_ShadowSigSel shadowSigSel;
} QEP_CompareConfigParam;

/* basic configuration */
void QEP_enableModule(QEP_Type *QEPx);
void QEP_disableModule(QEP_Type *QEPx);
void QEP_enableCapture(QEP_Type *QEPx);
void QEP_disableCapture(QEP_Type *QEPx);
void QEP_enableUnitTimer(QEP_Type *QEPx, uint32_t period);
void QEP_disableUnitTimer(QEP_Type *QEPx);
void QEP_loadUnitTimer(QEP_Type *QEPx, uint32_t period);
void QEP_setDecoderConfig(QEP_Type *QEPx, uint32_t config);
void QEP_setPositionCounterConfig(QEP_Type *QEPx, QEP_PositionResetMode mode, uint32_t maxPosition);
void QEP_setCaptureConfig(QEP_Type *QEPx, QEP_CAPCLKPrescaler capPrescaler, QEP_UPEVNTPrescaler evntPrescaler);
void QEP_setQMAModuleMode(QEP_Type *QEPx, QEP_QMAMode qmaMode);
void QEP_setStrobeSource(QEP_Type *QEPx, QEP_StrobeSource strobeSrc);
void QEP_selectSource(QEP_Type *QEPx, QEP_SourceSelect sourceConfig);
void QEP_setInputPolarity(QEP_Type *QEPx, bool invertQEPA, bool invertQEPB, bool invertIndex, bool invertStrobe);
void QEP_setPosition(QEP_Type *QEPx, uint32_t position);
void QEP_setPositionInitMode(QEP_Type *QEPx, uint16_t initMode);
void QEP_setSWPositionInit(QEP_Type *QEPx, bool initialize);
void QEP_setInitialPosition(QEP_Type *QEPx, uint32_t position);
uint32_t QEP_getPosition(QEP_Type *QEPx);
uint16_t QEP_getCapturePeriod(QEP_Type *QEPx);
uint16_t QEP_getCaptureTimer(QEP_Type *QEPx);
int16_t QEP_getDirection(QEP_Type *QEPx);

/* compare the outputs */
void QEP_enableCompare(QEP_Type *QEPx);
void QEP_disableCompare(QEP_Type *QEPx);
void QEP_setCompareConfig(QEP_Type *QEPx, QEP_CompareConfigParam config, uint32_t compareValue, uint16_t cycles);
void QEP_setComparePulseWidth(QEP_Type *QEPx, uint16_t cycles);

/* stall detection watchdog */
void QEP_enableWatchdog(QEP_Type *QEPx, uint16_t period);
void QEP_disableWatchdog(QEP_Type *QEPx);
void QEP_setWatchdogTimerValue(QEP_Type *QEPx, uint16_t value);
uint16_t QEP_getWatchdogTimerValue(QEP_Type *QEPx);

/* latch mode */
void QEP_setLatchMode(QEP_Type *QEPx, uint32_t latchMode);
uint32_t QEP_getIndexPositionLatch(QEP_Type *QEPx);
uint32_t QEP_getStrobePositionLatch(QEP_Type *QEPx);
uint32_t QEP_getPositionLatch(QEP_Type *QEPx);
uint16_t QEP_getCaptureTimerLatch(QEP_Type *QEPx);
uint16_t QEP_getCapturePeriodLatch(QEP_Type *QEPx);

/* interrupt function*/
void QEP_enableInterrupt(QEP_Type *QEPx, uint16_t intFlags);
void QEP_disableInterrupt(QEP_Type *QEPx, uint16_t intFlags);
void QEP_enableInterruptMask(QEP_Type *QEPx, uint16_t intFlags);
void QEP_disableInterruptMask(QEP_Type *QEPx, uint16_t intFlags);
uint16_t QEP_getInterruptStatus(QEP_Type *QEPx);
uint16_t QEP_getInterruptRawStatus(QEP_Type *QEPx);
void QEP_clearInterruptStatus(QEP_Type *QEPx, uint16_t intFlags);
void QEP_forceInterrupt(QEP_Type *QEPx, uint16_t intFlags);
bool QEP_getError(QEP_Type *QEPx);
uint8_t QEP_getStatus(QEP_Type *QEPx);
void QEP_clearStatus(QEP_Type *QEPx, uint8_t statusFlags);


void QEP_setEmulationMode(QEP_Type *QEPx, QEP_EmulationMode emuMode);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif  /*__ET6X_QEP_H */

/******************* END ***************************/
