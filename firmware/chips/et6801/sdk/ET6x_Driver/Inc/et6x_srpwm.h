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

#ifndef __ET6X_SRPWM_H
#define __ET6X_SRPWM_H

#include "et6x.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup SRPWM
 * @{
 */

/** @defgroup SRPWM Channel Group
 * @{
 */
#define SRPWM_CHANNEL_0      (0x0001)
#define SRPWM_CHANNEL_1      (0x0002)
#define SRPWM_CHANNEL_2      (0x0004)
#define SRPWM_CHANNEL_3      (0x0008)
#define SRPWM_CHANNEL_4      (0x0010)
#define SRPWM_CHANNEL_5      (0x0020)
#define SRPWM_CHANNEL_6      (0x0040)
#define SRPWM_CHANNEL_7      (0x0080)
#define SRPWM_CHANNEL_8      (0x0100)
#define SRPWM_CHANNEL_9      (0x0200)
#define SRPWM_CHANNEL_10     (0x0400)
#define SRPWM_CHANNEL_11     (0x0800)
#define SRPWM_CHANNEL_ALL    (0x0FFF)

/**
 * @}
 */

/** @defgroup SRPWM Mutex Result Group
 * @{
 */
#define SRPWM_MUTEX_RESULT_GRP_0      (0x0001)
#define SRPWM_MUTEX_RESULT_GRP_1      (0x0002)
#define SRPWM_MUTEX_RESULT_GRP_2      (0x0004)
#define SRPWM_MUTEX_RESULT_GRP_3      (0x0008)
#define SRPWM_MUTEX_RESULT_GRP_4      (0x0010)
#define SRPWM_MUTEX_RESULT_GRP_5      (0x0020)
#define SRPWM_MUTEX_RESULT_GRP_6      (0x0040)
#define SRPWM_MUTEX_RESULT_GRP_7      (0x0080)
#define SRPWM_MUTEX_RESULT_GRP_8      (0x0100)
#define SRPWM_MUTEX_RESULT_GRP_9      (0x0200)
#define SRPWM_MUTEX_RESULT_GRP_10     (0x0400)
#define SRPWM_MUTEX_RESULT_GRP_11     (0x0800)
#define SRPWM_MUTEX_RESULT_GRP_ALL    (0x0FFF)

/**
 * @}
 */

/** @defgroup SRPWM Event Collections
 * @{
 */

/** @defgroup synchronous load event collections1
 * @{
 */
#define SRPWM_SYNCEVTLOAD1_ZERO_EVT           (0x0001)
#define SRPWM_SYNCEVTLOAD1_PERIOD_EVT         (0x0002)
#define SRPWM_SYNCEVTLOAD1_SCMPA_UP_EVT       (0x0004)
#define SRPWM_SYNCEVTLOAD1_SCMPB_UP_EVT       (0x0008)
#define SRPWM_SYNCEVTLOAD1_SCMPA_DOWN_EVT     (0x0010)
#define SRPWM_SYNCEVTLOAD1_SCMPB_DOWN_EVT     (0x0020)
#define SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS0     (0x0040)
#define SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS1     (0x0080)
#define SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS2     (0x0100)
#define SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS3     (0x0200)
#define SRPWM_SYNCEVTLOAD1_SYNC0              (0x0400)
#define SRPWM_SYNCEVTLOAD1_SYNC1              (0x0800)
#define SRPWM_SYNCEVTLOAD1_BURST_OVER         (0x1000)
#define SRPWM_SYNCEVTLOAD1_SORTWARE_UPDATE    (0x2000)

/**
 * @}
 */

/** @defgroup synchronous load event collections2
 * @{
 */
#define SRPWM_SYNCEVTLOAD2_ZERO_EVT           (0x0001)
#define SRPWM_SYNCEVTLOAD2_PERIOD_EVT         (0x0002)
#define SRPWM_SYNCEVTLOAD2_SCMPC_UP_EVT       (0x0004)
#define SRPWM_SYNCEVTLOAD2_SCMPD_UP_EVT       (0x0008)
#define SRPWM_SYNCEVTLOAD2_SCMPC_DOWN_EVT     (0x0010)
#define SRPWM_SYNCEVTLOAD2_SCMPD_DOWN_EVT     (0x0020)
#define SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS0     (0x0040)
#define SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS1     (0x0080)
#define SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS2     (0x0100)
#define SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS3     (0x0200)
#define SRPWM_SYNCEVTLOAD2_SYNC0              (0x0400)
#define SRPWM_SYNCEVTLOAD2_SYNC1              (0x0800)
#define SRPWM_SYNCEVTLOAD2_BURST_OVER         (0x1000)
#define SRPWM_SYNCEVTLOAD2_SORTWARE_UPDATE    (0x2000)

/**
 * @}
 */

/** @defgroup all event collections
 * @{
 */
#define SRPWM_ALLEVT_ZERO_EVT          ((uint32_t)(0x00000001))
#define SRPWM_ALLEVT_PRD_EVT           ((uint32_t)(0x00000002))
#define SRPWM_ALLEVT_SCMPA_UP_EVT      ((uint32_t)(0x00000004))
#define SRPWM_ALLEVT_SCMPB_UP_EVT      ((uint32_t)(0x00000008))
#define SRPWM_ALLEVT_SCMPC_UP_EVT      ((uint32_t)(0x00000010))
#define SRPWM_ALLEVT_SCMPD_UP_EVT      ((uint32_t)(0x00000020))
#define SRPWM_ALLEVT_SCMPA_DOWN_EVT    ((uint32_t)(0x00000040))
#define SRPWM_ALLEVT_SCMPB_DOWN_EVT    ((uint32_t)(0x00000080))
#define SRPWM_ALLEVT_SCMPC_DOWN_EVT    ((uint32_t)(0x00000100))
#define SRPWM_ALLEVT_SCMPD_DOWN_EVT    ((uint32_t)(0x00000200))
#define SRPWM_ALLEVT_CMPA_UP_EVT       ((uint32_t)(0x00000400))
#define SRPWM_ALLEVT_CMPB_UP_EVT       ((uint32_t)(0x00000800))
#define SRPWM_ALLEVT_CMPC_UP_EVT       ((uint32_t)(0x00001000))
#define SRPWM_ALLEVT_CMPD_UP_EVT       ((uint32_t)(0x00002000))
#define SRPWM_ALLEVT_CMPA_DOWN_EVT     ((uint32_t)(0x00004000))
#define SRPWM_ALLEVT_CMPB_DOWN_EVT     ((uint32_t)(0x00008000))
#define SRPWM_ALLEVT_CMPC_DOWN_EVT     ((uint32_t)(0x00010000))
#define SRPWM_ALLEVT_CMPD_DOWN_EVT     ((uint32_t)(0x00020000))
#define SRPWM_ALLEVT_FPP_FAULT_POS0    ((uint32_t)(0x00040000))
#define SRPWM_ALLEVT_FPP_FAULT_POS1    ((uint32_t)(0x00080000))
#define SRPWM_ALLEVT_FPP_FAULT_POS2    ((uint32_t)(0x00100000))
#define SRPWM_ALLEVT_FPP_FAULT_POS3    ((uint32_t)(0x00200000))
#define SRPWM_ALLEVT_SYNC0             ((uint32_t)(0x00400000))
#define SRPWM_ALLEVT_SYNC1             ((uint32_t)(0x00800000))
#define SRPWM_ALLEVT_BURST_OVER        ((uint32_t)(0x01000000))
#define SRPWM_ALLEVT_B_NEG             ((uint32_t)(0x02000000))
#define SRPWM_ALLEVT_B_POS             ((uint32_t)(0x04000000))
#define SRPWM_ALLEVT_A_NEG             ((uint32_t)(0x08000000))
#define SRPWM_ALLEVT_A_POS             ((uint32_t)(0x10000000))
#define SRPWM_ALLEVT_SW_EVT            ((uint32_t)(0x20000000))

/**
 * @}
 */

/** @defgroup SRPWM TBCOUNTER Synchronous Event Collections
 * @{
 */
#define SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS0         ((uint8_t)(0x0001))
#define SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS1         ((uint8_t)(0x0002))
#define SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS2         ((uint8_t)(0x0004))
#define SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS3         ((uint8_t)(0x0008))
#define SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN0               ((uint8_t)(0x0010))
#define SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN1               ((uint8_t)(0x0020))
#define SRPWM_TBCOUNTER_SYNCEVT_SOFTWARE_UPDATE_EVT    ((uint8_t)(0x0040))

/**
 * @}
 */

/** @defgroup SRPWM Output Event Collections
 * @{
 */
#define SRPWM_OUTEVT_SYNC_ZERO_EVT          ((uint32_t)(0x00000001))
#define SRPWM_OUTEVT_SYNC_PRD_EVT           ((uint32_t)(0x00000002))
#define SRPWM_OUTEVT_SYNC_CMPA_UP_EVT       ((uint32_t)(0x00000004))
#define SRPWM_OUTEVT_SYNC_CMPB_UP_EVT       ((uint32_t)(0x00000008))
#define SRPWM_OUTEVT_SYNC_CMPC_UP_EVT       ((uint32_t)(0x00000010))
#define SRPWM_OUTEVT_SYNC_CMPD_UP_EVT       ((uint32_t)(0x00000020))
#define SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT     ((uint32_t)(0x00000040))
#define SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT     ((uint32_t)(0x00000080))
#define SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT     ((uint32_t)(0x00000100))
#define SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT     ((uint32_t)(0x00000200))
#define SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT      ((uint32_t)(0x00000400))
#define SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT      ((uint32_t)(0x00000800))
#define SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT      ((uint32_t)(0x00001000))
#define SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT      ((uint32_t)(0x00002000))
#define SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT    ((uint32_t)(0x00004000))
#define SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT    ((uint32_t)(0x00008000))
#define SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT    ((uint32_t)(0x00010000))
#define SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT    ((uint32_t)(0x00020000))
#define SRPWM_OUTEVT_SYNC_BURST_A_NEG       ((uint32_t)(0x00040000))
#define SRPWM_OUTEVT_SYNC_BURST_A_POS       ((uint32_t)(0x00080000))
#define SRPWM_OUTEVT_SYNC_BURST_B_NEG       ((uint32_t)(0x00100000))
#define SRPWM_OUTEVT_SYNC_BURST_B_POS       ((uint32_t)(0x00200000))
#define SRPWM_OUTEVT_SYNC_TIMER_0SYNC       ((uint32_t)(0x00400000))
#define SRPWM_OUTEVT_SYNC_TIMER_1SYNC       ((uint32_t)(0x00800000))

/**
 * @}
 */

/** @defgroup SRPWM Burst Start Event Collections
 * @{
 */
#define SRPWM_BURST_START_SYNC_ZERO_EVT          ((uint8_t)(0x0001))
#define SRPWM_BURST_START_SYNC_PRD_EVT           ((uint8_t)(0x0002))
#define SRPWM_BURST_START_SYNC_SCMPA_UP_EVT      ((uint8_t)(0x0004))
#define SRPWM_BURST_START_SYNC_SCMPB_UP_EVT      ((uint8_t)(0x0008))
#define SRPWM_BURST_START_SYNC_SCMPA_DOWN_EVT    ((uint8_t)(0x0010))
#define SRPWM_BURST_START_SYNC_SCMPB_DOWN_EVT    ((uint8_t)(0x0020))

/**
 * @}
 */

/** @defgroup SRPWM PG Software Event Collections
 * @{
 */
#define SRPWM_PG_SWSYNC_ZERO_EVT          ((uint16_t)(0x0001))
#define SRPWM_PG_SWSYNC_PRD_EVT           ((uint16_t)(0x0002))
#define SRPWM_PG_SWSYNC_SCMPA_UP_EVT      ((uint16_t)(0x0004))
#define SRPWM_PG_SWSYNC_SCMPB_UP_EVT      ((uint16_t)(0x0008))
#define SRPWM_PG_SWSYNC_SCMPA_DOWN_EVT    ((uint16_t)(0x0010))
#define SRPWM_PG_SWSYNC_SCMPB_DOWN_EVT    ((uint16_t)(0x0020))
#define SRPWM_PG_SWSYNC_BURST_PWMB_NEG    ((uint16_t)(0x0040))
#define SRPWM_PG_SWSYNC_BURST_PWMB_POS    ((uint16_t)(0x0080))
#define SRPWM_PG_SWSYNC_BURST_PWMA_NEG    ((uint16_t)(0x0100))
#define SRPWM_PG_SWSYNC_BURST_PWMA_POS    ((uint16_t)(0x0200))

/**
 * @}
 */

/**
 * @}
 */

/** @defgroup SRPWM FPP Fault Signal Group
 * @{
 */
#define SRPWM_FPP_FAULT_SIG_GRP0    (0x01U)
#define SRPWM_FPP_FAULT_SIG_GRP1    (0x02U)
#define SRPWM_FPP_FAULT_SIG_GRP2    (0x04U)
#define SRPWM_FPP_FAULT_SIG_GRP3    (0x08U)
#define SRPWM_FPP_FAULT_SIG_GRP4    (0x10U)
#define SRPWM_FPP_FAULT_SIG_GRP5    (0x20U)

/**
 * @}
 */
/** @defgroup SRPWM FPP Fault Real and Latch Signal Group
 * @{
 */
#define SRPWM_FPP_FAULT_REAL0     ((uint16_t)(0x0001))
#define SRPWM_FPP_FAULT_REAL1     ((uint16_t)(0x0002))
#define SRPWM_FPP_FAULT_REAL2     ((uint16_t)(0x0004))
#define SRPWM_FPP_FAULT_REAL3     ((uint16_t)(0x0008))
#define SRPWM_FPP_FAULT_REAL4     ((uint16_t)(0x0010))
#define SRPWM_FPP_FAULT_REAL5     ((uint16_t)(0x0020))
#define SRPWM_FPP_FAULT_LATCH0    ((uint16_t)(0x0100))
#define SRPWM_FPP_FAULT_LATCH1    ((uint16_t)(0x0200))
#define SRPWM_FPP_FAULT_LATCH2    ((uint16_t)(0x0400))
#define SRPWM_FPP_FAULT_LATCH3    ((uint16_t)(0x0800))
#define SRPWM_FPP_FAULT_LATCH4    ((uint16_t)(0x1000))
#define SRPWM_FPP_FAULT_LATCH5    ((uint16_t)(0x2000))

/**
 * @}
 */
/** @defgroup SRPWM PREP Fault Real and Latch Signal Group
 * @{
 */
#define SRPWM_PREP_SIG_FAULT_REAL0     ((uint16_t)(0x0001))
#define SRPWM_PREP_SIG_FAULT_REAL1     ((uint16_t)(0x0002))
#define SRPWM_PREP_SIG_FAULT_REAL2     ((uint16_t)(0x0004))
#define SRPWM_PREP_SIG_FAULT_REAL3     ((uint16_t)(0x0008))
#define SRPWM_PREP_SIG_FAULT_REAL4     ((uint16_t)(0x0010))
#define SRPWM_PREP_SIG_FAULT_REAL5     ((uint16_t)(0x0020))
#define SRPWM_PREP_SIG_FAULT_LATCH0    ((uint16_t)(0x0040))
#define SRPWM_PREP_SIG_FAULT_LATCH1    ((uint16_t)(0x0080))
#define SRPWM_PREP_SIG_FAULT_LATCH2    ((uint16_t)(0x0100))
#define SRPWM_PREP_SIG_FAULT_LATCH3    ((uint16_t)(0x0200))
#define SRPWM_PREP_SIG_FAULT_LATCH4    ((uint16_t)(0x0400))
#define SRPWM_PREP_SIG_FAULT_LATCH5    ((uint16_t)(0x0800))
#define SRPWM_PREP_SIG_SW              ((uint16_t)(0x1000)) /* not supported Unconstrained protection */

/**
 * @}
 */
/** @defgroup SRPWM PREP Timer Control
 * @{
 */
#define SRPWM_PREP_A_SET_TIMER       ((uint16_t)(0x0001))
#define SRPWM_PREP_A_CLR_TIMER       ((uint16_t)(0x0002))
#define SRPWM_PREP_A_INVERT_TIMER    ((uint16_t)(0x0004))
#define SRPWM_PREP_A_HIZ_TIMER       ((uint16_t)(0x0008))
#define SRPWM_PREP_B_SET_TIMER       ((uint16_t)(0x0010))
#define SRPWM_PREP_B_CLR_TIMER       ((uint16_t)(0x0020))
#define SRPWM_PREP_B_INVERT_TIMER    ((uint16_t)(0x0040))
#define SRPWM_PREP_B_HIZ_TIMER       ((uint16_t)(0x0080))

/**
 * @}
 */
/** @defgroup SRPWM Interrupt Type
 * @{
 */
#define SRPWM_IT_EVT             ((uint16_t)(0x0001))
#define SRPWM_IT_BURST_OVER      ((uint16_t)(0x0002))
#define SRPWM_IT_FAULT_REAL0     ((uint16_t)(0x0004))
#define SRPWM_IT_FAULT_REAL1     ((uint16_t)(0x0008))
#define SRPWM_IT_FAULT_REAL2     ((uint16_t)(0x0010))
#define SRPWM_IT_FAULT_REAL3     ((uint16_t)(0x0020))
#define SRPWM_IT_FAULT_REAL4     ((uint16_t)(0x0040))
#define SRPWM_IT_FAULT_REAL5     ((uint16_t)(0x0080))
#define SRPWM_IT_FAULT_LATCH0    ((uint16_t)(0x0100))
#define SRPWM_IT_FAULT_LATCH1    ((uint16_t)(0x0200))
#define SRPWM_IT_FAULT_LATCH2    ((uint16_t)(0x0400))
#define SRPWM_IT_FAULT_LATCH3    ((uint16_t)(0x0800))
#define SRPWM_IT_FAULT_LATCH4    ((uint16_t)(0x1000))
#define SRPWM_IT_FAULT_LATCH5    ((uint16_t)(0x2000))

/**
 * @}
 */
/** @defgroup SRPWM Shadow Multi Sync
 * @{
 */
#define SRPWM_SHD_MULTI_SYNC_PRD      (0x01)
#define SRPWM_SHD_MULTI_SYNC_PHASE    (0x02)
#define SRPWM_SHD_MULTI_SYNC_CMP      (0x04)
#define SRPWM_SHD_MULTI_SYNC_SCMP     (0x08)
#define SRPWM_SHD_MULTI_SYNC_PG       (0x10)
#define SRPWM_SHD_MULTI_SYNC_DB       (0x20)
#define SRPWM_SHD_MULTI_SYNC_BURST    (0x40)

/**
 * @}
 */
/** @defgroup SRPWM DMA Number
 * @{
 */
#define SRPWMCOM_DMA0_MSK    (0x01)
#define SRPWMCOM_DMA1_MSK    (0x02)
#define SRPWMCOM_DMA2_MSK    (0x04)
#define SRPWMCOM_DMA3_MSK    (0x08)

/**
 * @}
 */

/** @defgroup SRPWM QEP Trigger Number
 * @{
 */
#define SRPWMCOM_QEP_TRIGGER_SRPWM0_SOC_AB     (0x00001)
#define SRPWMCOM_QEP_TRIGGER_SRPWM1_SOC_AB     (0x00002)
#define SRPWMCOM_QEP_TRIGGER_SRPWM2_SOC_AB     (0x00004)
#define SRPWMCOM_QEP_TRIGGER_SRPWM3_SOC_AB     (0x00008)
#define SRPWMCOM_QEP_TRIGGER_SRPWM4_SOC_AB     (0x00010)
#define SRPWMCOM_QEP_TRIGGER_SRPWM5_SOC_AB     (0x00020)
#define SRPWMCOM_QEP_TRIGGER_SRPWM6_SOC_AB     (0x00040)
#define SRPWMCOM_QEP_TRIGGER_SRPWM7_SOC_AB     (0x00080)
#define SRPWMCOM_QEP_TRIGGER_SRPWM8_SOC_AB     (0x00100)
#define SRPWMCOM_QEP_TRIGGER_SRPWM9_SOC_AB     (0x00200)
#define SRPWMCOM_QEP_TRIGGER_SRPWM10_SOC_AB    (0x00400)
#define SRPWMCOM_QEP_TRIGGER_SRPWM11_SOC_AB    (0x00800)
#define SRPWMCOM_QEP_TRIGGER_SRPWM12_SOC_AB    (0x01000)
#define SRPWMCOM_QEP_TRIGGER_SRPWM13_SOC_AB    (0x02000)
#define SRPWMCOM_QEP_TRIGGER_SRPWM14_SOC_AB    (0x04000)
#define SRPWMCOM_QEP_TRIGGER_SRPWM15_SOC_AB    (0x08000)
#define SRPWMCOM_QEP_TRIGGER_SRPWM16_SOC_AB    (0x10000)
#define SRPWMCOM_QEP_TRIGGER_SRPWM17_SOC_AB    (0x20000)

/**
 * @}
 */

/**
 * @brief specify the A or B route of the srpwm
 */
typedef enum
{
    SRPWM_A = 0, /*!< specify the A route of the srpwm  */
    SRPWM_B = 1  /*!< specify the B route of the srpwm  */
} SRPWM_AB;

/**
 * @brief specify the counter compare module of the srpwm
 */
typedef enum
{
    SRPWM_COUNTER_COMPARE_A       = 0, /*!< Counter compare A  */
    SRPWM_COUNTER_COMPARE_B       = 1, /*!< Counter compare B  */
    SRPWM_COUNTER_COMPARE_C       = 2, /*!< Counter compare C  */
    SRPWM_COUNTER_COMPARE_D       = 3, /*!< Counter compare D  */
    SRPWM_COUNTER_COMPARE_A_SLAVE = 4, /*!< Counter compare A slave  */
    SRPWM_COUNTER_COMPARE_B_SLAVE = 5, /*!< Counter compare B slave  */
    SRPWM_COUNTER_COMPARE_C_SLAVE = 6, /*!< Counter compare C slave  */
    SRPWM_COUNTER_COMPARE_D_SLAVE = 7  /*!< Counter compare D slave  */
} SRPWM_CounterCompareModule;

/**
 * @brief specify the phase type of the srpwm
 */
typedef enum
{
    SRPWM_PHASE0 = 0, /*!< phase 0  */
    SRPWM_PHASE1 = 1  /*!< phase 1  */
} SRPWM_PhaseType;

/**
 * @brief specify the sync number of the srpwm
 */
typedef enum
{
    SRPWM_SYNC0 = 0,
    SRPWM_SYNC1 = 1
} SRPWM_SyncType;

/**
 * @brief specify the start of conversion type of the srpwm
 */
typedef enum
{
    SRPWM_SOC_A = 0,
    SRPWM_SOC_B = 1
} SRPWM_ADCStartOfConversionType;

/**
 * @brief specifies the source from which the latched timebase counter value is held
 */
typedef enum
{
    SRPWMCOM_LATCHCNT_SRC_SRPWM0_SYNCOUT0  = 0,
    SRPWMCOM_LATCHCNT_SRC_SRPWM0_SYNCOUT1  = 1,
    SRPWMCOM_LATCHCNT_SRC_SRPWM1_SYNCOUT0  = 2,
    SRPWMCOM_LATCHCNT_SRC_SRPWM1_SYNCOUT1  = 3,
    SRPWMCOM_LATCHCNT_SRC_SRPWM2_SYNCOUT0  = 4,
    SRPWMCOM_LATCHCNT_SRC_SRPWM2_SYNCOUT1  = 5,
    SRPWMCOM_LATCHCNT_SRC_SRPWM3_SYNCOUT0  = 6,
    SRPWMCOM_LATCHCNT_SRC_SRPWM3_SYNCOUT1  = 7,
    SRPWMCOM_LATCHCNT_SRC_SRPWM4_SYNCOUT0  = 8,
    SRPWMCOM_LATCHCNT_SRC_SRPWM4_SYNCOUT1  = 9,
    SRPWMCOM_LATCHCNT_SRC_SRPWM5_SYNCOUT0  = 10,
    SRPWMCOM_LATCHCNT_SRC_SRPWM5_SYNCOUT1  = 11,
    SRPWMCOM_LATCHCNT_SRC_SRPWM6_SYNCOUT0  = 12,
    SRPWMCOM_LATCHCNT_SRC_SRPWM6_SYNCOUT1  = 13,
    SRPWMCOM_LATCHCNT_SRC_SRPWM7_SYNCOUT0  = 14,
    SRPWMCOM_LATCHCNT_SRC_SRPWM7_SYNCOUT1  = 15,
    SRPWMCOM_LATCHCNT_SRC_SRPWM8_SYNCOUT0  = 16,
    SRPWMCOM_LATCHCNT_SRC_SRPWM8_SYNCOUT1  = 17,
    SRPWMCOM_LATCHCNT_SRC_SRPWM9_SYNCOUT0  = 18,
    SRPWMCOM_LATCHCNT_SRC_SRPWM9_SYNCOUT1  = 19,
    SRPWMCOM_LATCHCNT_SRC_SRPWM10_SYNCOUT0 = 20,
    SRPWMCOM_LATCHCNT_SRC_SRPWM10_SYNCOUT1 = 21,
    SRPWMCOM_LATCHCNT_SRC_SRPWM11_SYNCOUT0 = 22,
    SRPWMCOM_LATCHCNT_SRC_SRPWM11_SYNCOUT1 = 23,

    SRPWMCOM_LATCHCNT_SRC_EN_POS_EDGE      = 24
} SRPWMCOM_LatchCntSrc;

/**
 * @brief specify the srpwm sync output number
 */
typedef enum
{
    SRPWMCOM_SRPWM0_SYNCOUT0  = 0,
    SRPWMCOM_SRPWM0_SYNCOUT1  = 1,
    SRPWMCOM_SRPWM1_SYNCOUT0  = 2,
    SRPWMCOM_SRPWM1_SYNCOUT1  = 3,
    SRPWMCOM_SRPWM2_SYNCOUT0  = 4,
    SRPWMCOM_SRPWM2_SYNCOUT1  = 5,
    SRPWMCOM_SRPWM3_SYNCOUT0  = 6,
    SRPWMCOM_SRPWM3_SYNCOUT1  = 7,
    SRPWMCOM_SRPWM4_SYNCOUT0  = 8,
    SRPWMCOM_SRPWM4_SYNCOUT1  = 9,
    SRPWMCOM_SRPWM5_SYNCOUT0  = 10,
    SRPWMCOM_SRPWM5_SYNCOUT1  = 11,
    SRPWMCOM_SRPWM6_SYNCOUT0  = 12,
    SRPWMCOM_SRPWM6_SYNCOUT1  = 13,
    SRPWMCOM_SRPWM7_SYNCOUT0  = 14,
    SRPWMCOM_SRPWM7_SYNCOUT1  = 15,
    SRPWMCOM_SRPWM8_SYNCOUT0  = 16,
    SRPWMCOM_SRPWM8_SYNCOUT1  = 17,
    SRPWMCOM_SRPWM9_SYNCOUT0  = 18,
    SRPWMCOM_SRPWM9_SYNCOUT1  = 19,
    SRPWMCOM_SRPWM10_SYNCOUT0 = 20,
    SRPWMCOM_SRPWM10_SYNCOUT1 = 21,
    SRPWMCOM_SRPWM11_SYNCOUT0 = 22,
    SRPWMCOM_SRPWM11_SYNCOUT1 = 23
} SRPWMCOM_SRPWM_SYNCOUT;

/**
 * @brief specify the xbar number
 */
typedef enum
{
    SRPWMCOM_XBAR0 = 0,
    SRPWMCOM_XBAR1 = 1,
    SRPWMCOM_XBAR2 = 2,
    SRPWMCOM_XBAR3 = 3
} SRPWMCOM_XBARx;

/**
 * @brief specify the dac number
 */
typedef enum
{
    SRPWMCOM_DAC0 = 0,
    SRPWMCOM_DAC1 = 1
} SRPWMCOM_DACx;

/**
 * @brief specify the acmp number
 */
typedef enum
{
    SRPWMCOM_ACMP0_H = 0,
    SRPWMCOM_ACMP0_L = 1,
    SRPWMCOM_ACMP1_H = 2,
    SRPWMCOM_ACMP1_L = 3,
    SRPWMCOM_ACMP2_H = 4,
    SRPWMCOM_ACMP2_L = 5,
    SRPWMCOM_ACMP3_H = 6,
    SRPWMCOM_ACMP3_L = 7
} SRPWMCOM_ACMPx;

/**
 * @brief specify the qep number
 */
typedef enum
{
    SRPWMCOM_QEP0 = 0,
    SRPWMCOM_QEP1 = 1
} SRPWMCOM_QEPx;

/**
 * @brief specify the mutex signal
 */
typedef enum
{
    SRPWMCOM_MUTEX_SIG_SRPWM0_A  = 0,
    SRPWMCOM_MUTEX_SIG_SRPWM1_A  = 1,
    SRPWMCOM_MUTEX_SIG_SRPWM2_A  = 2,
    SRPWMCOM_MUTEX_SIG_SRPWM3_A  = 3,
    SRPWMCOM_MUTEX_SIG_SRPWM4_A  = 4,
    SRPWMCOM_MUTEX_SIG_SRPWM5_A  = 5,
    SRPWMCOM_MUTEX_SIG_SRPWM6_A  = 6,
    SRPWMCOM_MUTEX_SIG_SRPWM7_A  = 7,
    SRPWMCOM_MUTEX_SIG_SRPWM8_A  = 8,
    SRPWMCOM_MUTEX_SIG_SRPWM9_A  = 9,
    SRPWMCOM_MUTEX_SIG_SRPWM10_A = 10,
    SRPWMCOM_MUTEX_SIG_SRPWM11_A = 11,
    SRPWMCOM_MUTEX_SIG_SRPWM0_B  = 12,
    SRPWMCOM_MUTEX_SIG_SRPWM1_B  = 13,
    SRPWMCOM_MUTEX_SIG_SRPWM2_B  = 14,
    SRPWMCOM_MUTEX_SIG_SRPWM3_B  = 15,
    SRPWMCOM_MUTEX_SIG_SRPWM4_B  = 16,
    SRPWMCOM_MUTEX_SIG_SRPWM5_B  = 17,
    SRPWMCOM_MUTEX_SIG_SRPWM6_B  = 18,
    SRPWMCOM_MUTEX_SIG_SRPWM7_B  = 19,
    SRPWMCOM_MUTEX_SIG_SRPWM8_B  = 20,
    SRPWMCOM_MUTEX_SIG_SRPWM9_B  = 21,
    SRPWMCOM_MUTEX_SIG_SRPWM10_B = 22,
    SRPWMCOM_MUTEX_SIG_SRPWM11_B = 23
} SRPWMCOM_MutexSig;

/**
 * @brief specify the mutex condition
 */
typedef enum
{
    SRPWMCOM_A_LOW_B_LOW   = 0,
    SRPWMCOM_A_LOW_B_HIGH  = 1,
    SRPWMCOM_A_HIGH_B_LOW  = 2,
    SRPWMCOM_A_HIGH_B_HIGH = 3
} SRPWMCOM_SRPWM_MutexCondition;

/**
 * @brief specifies the counting mode of the srpwm
 */
typedef enum
{
    SRPWM_COUNTMODE_UPDOWN = 0,
    SRPWM_COUNTMODE_UP     = 1
} SRPWM_CountMode;

/**
 * @brief specifies the sync direction of the srpwm
 */
typedef enum
{
    SRPWM_SYNC_DIR_DOWN = 0,
    SRPWM_SYNC_DIR_UP   = 1
} SRPWM_SyncDirMode;

/**
 * @brief specifies the event output mode of the srpwm
 */
typedef enum
{
    SRPWM_CMP_EVTOUT_MODE_EQUAL_EVENT       = 0x0,  /*!< an event occurs when the counter value is equal to the
                                                     * comparator value  */
    SRPWM_CMP_EVTOUT_MODE_UP_AND_DOWN_EVENT = 0x1   /*!< when counting upwards，the counter value is greater than or
                                                     * equal to the comparator value；or when counting downward，less than
                                                     * or equal to the comparator produces an event  */
} SRPWM_CMPEventOutMode;

/**
 * @brief specify the pwm generate(PG) event
 */
typedef enum
{
    SRPWM_PG_EVT_FPP_FAULT_POS0 = 0,
    SRPWM_PG_EVT_FPP_FAULT_POS1 = 1,
    SRPWM_PG_EVT_FPP_FAULT_POS2 = 2,
    SRPWM_PG_EVT_FPP_FAULT_POS3 = 3,
    SRPWM_PG_EVT_CMPD_UP        = 4,
    SRPWM_PG_EVT_CMPC_UP        = 5,
    SRPWM_PG_EVT_CMPB_UP        = 6,
    SRPWM_PG_EVT_CMPA_UP        = 7,
    SRPWM_PG_EVT_SCMPD_UP       = 8,
    SRPWM_PG_EVT_SCMPC_UP       = 9,
    SRPWM_PG_EVT_SCMPB_UP       = 10,
    SRPWM_PG_EVT_SCMPA_UP       = 11,
    SRPWM_PG_EVT_ZERO           = 12,
    SRPWM_PG_EVT_CMPD_DOWN      = 13,
    SRPWM_PG_EVT_CMPC_DOWN      = 14,
    SRPWM_PG_EVT_CMPB_DOWN      = 15,
    SRPWM_PG_EVT_CMPA_DOWN      = 16,
    SRPWM_PG_EVT_SCMPD_DOWN     = 17,
    SRPWM_PG_EVT_SCMPC_DOWN     = 18,
    SRPWM_PG_EVT_SCMPB_DOWN     = 19,
    SRPWM_PG_EVT_SCMPA_DOWN     = 20,
    SRPWM_PG_EVT_PERIOD         = 21,

    SRPWM_PG_EVT_SW             = 22        /* there are a total of 22 action matrix events and software events are not
                                             * actually in these 22 and a software event is placed here for easy
                                             * processing */
} SRPWM_PGEvt;

/**
 * @brief specify the output value of the PG event
 */
typedef enum
{
    SRPWM_PG_NONE   = 0,
    SRPWM_PG_CLEAR  = 1,
    SRPWM_PG_SET    = 2,
    SRPWM_PG_TOGGLE = 3
} SRPWM_PGValue;

/**
 * @brief specify the output state of the DB
 */
typedef enum
{
    SRPWM_DB_OUTPUT_STATE_NONE              = 0,
    SRPWM_DB_OUTPUT_STATE_POS_OR_NEG_AFTER  = 1,
    SRPWM_DB_OUTPUT_STATE_POS_OR_NEG_INVERT = 2
} SRPWM_DBOutputState;

/**
 * @brief specifies the wave mode of burst
 */
typedef enum
{
    SRPWM_BURST_N_WAVE_IN_BACK  = 0,   /* rear n waveforms for m cycles */
    SRPWM_BURST_N_WAVE_IN_FRONT = 1    /* advance n waveforms for m cycles*/
} SRPWM_BurstMode;

/**
 * @brief specify the failure mode of the fpp
 */
typedef enum
{
    SRPWM_FPP_FAULT_MODE_NORMAL            = 0,
    SRPWM_FPP_FAULT_MODE_ONE_BLK_ONE_FAULT = 1
} SRPWM_FPPFaultMode;

/**
 * @brief specify the blanking mode of the fpp
 */
typedef enum
{
    SRPWM_FPP_BLK_MODE_NONE   = 0,
    SRPWM_FPP_BLK_MODE_NORMAL = 1,
    SRPWM_FPP_BLK_MODE_LATCH  = 2
} SRPWM_FPPBlankingMode;

/**
 * @brief specify the edge selection of the fault signal
 */
typedef enum
{
    SRPWM_FPP_FAULT_SIG_EGDE_SEL_DIRECT = 0,
    SRPWM_FPP_FAULT_SIG_EGDE_SEL_INVERT = 1,
    SRPWM_FPP_FAULT_SIG_EGDE_SEL_POS    = 2,
    SRPWM_FPP_FAULT_SIG_EGDE_SEL_NES    = 3
} SRPWM_FPPFaultSigEgdeSel;

/**
 * @brief specify the count signal selection of the fpp
 */
typedef enum
{
    SRPWM_FPP_COUNT_SIG_FILTER_BEFORE = 0,
    SRPWM_FPP_COUNT_SIG_FILTER_BEHIND = 1
} SRPWM_FPPCountSigSel;

/**
 * @brief specify the state of the prep signal
 */
typedef enum
{
    SRPWM_PREP_A_SIG_STATE_UNRES  = (uint16_t)(0x0001),
    SRPWM_PREP_A_SIG_STATE_OS     = (uint16_t)(0x0002),
    SRPWM_PREP_A_SIG_STATE_CBC    = (uint16_t)(0x0004),
    SRPWM_PREP_A_SIG_STATE_HIZ    = (uint16_t)(0x0010),
    SRPWM_PREP_A_SIG_STATE_INVERT = (uint16_t)(0x0020),
    SRPWM_PREP_A_SIG_STATE_CLR    = (uint16_t)(0x0040),
    SRPWM_PREP_A_SIG_STATE_SET    = (uint16_t)(0x0080),
    SRPWM_PREP_B_SIG_STATE_UNRES  = (uint16_t)(0x0100),
    SRPWM_PREP_B_SIG_STATE_OS     = (uint16_t)(0x0200),
    SRPWM_PREP_B_SIG_STATE_CBC    = (uint16_t)(0x0400),
    SRPWM_PREP_B_SIG_STATE_HIZ    = (uint16_t)(0x1000),
    SRPWM_PREP_B_SIG_STATE_INVERT = (uint16_t)(0x2000),
    SRPWM_PREP_B_SIG_STATE_CLR    = (uint16_t)(0x4000),
    SRPWM_PREP_B_SIG_STATE_SET    = (uint16_t)(0x8000)
} SRPWM_PREP_SigState;

/**
 * @brief specify the output state of the prep signal
 */
typedef enum
{
    SRPWM_PREP_STATE_HIZ    = 0,
    SRPWM_PREP_STATE_CLR    = 1,
    SRPWM_PREP_STATE_SET    = 2,
    SRPWM_PREP_STATE_INVERT = 3
} SRPWM_PreprotectState;

/**
 * @brief specify the output status of the pstp
 */
typedef enum
{
    SRPWM_PSTP_MUTEX_OUTSTATE_NONE  = 0,
    SRPWM_PSTP_MUTEX_OUTSTATE_SET   = 1,
    SRPWM_PSTP_MUTEX_OUTSTATE_CLEAR = 2,
    SRPWM_PSTP_MUTEX_OUTSTATE_HIZ   = 3
} SRPWM_PSTPOutState;

/**
 * @brief specify the fault state of the pstp
 */
typedef enum
{
    SRPWM_PSTP_FAULT_STATE_SIG_A_SET_CLR_HIZ =   (uint8_t)(0x0001),
    SRPWM_PSTP_FAULT_STATE_SIG_B_SET_CLR_HIZ =   (uint8_t)(0x0002),
    SRPWM_PSTP_FAULT_STATE_SIG_AB_MUTEX      =   (uint8_t)(0x0004)
} SRPWM_PSTPFaultStateSig;

/**
 * @brief specify the valley edge detect mode
 */
typedef enum
{
    SRPWM_VALLEY_EDGE_DETECT_MODE_RISING             = 0x0,
    SRPWM_VALLEY_EDGE_DETECT_MODE_FALLING            = 0x1,
    SRPWM_VALLEY_EDGE_DETECT_MODE_FALLING_AND_RISING = 0X2
} SRPWM_ValleyEdgeDetectMode;

/**
 * @brief specify the valley trigger mode
 */
typedef enum
{
    SRPWM_VALLEY_TRIGGER_SW             = 0x0,
    SRPWM_VALLEY_TRIGGER_ZERO           = 0x1,
    SRPWM_VALLEY_TRIGGER_PERIOD         = 0x2,
    SRPWM_VALLEY_TRIGGER_ZERO_OR_PERIOD = 0x3,
    SRPWM_VALLEY_TRIGGER_SCMPC_UP       = 0x4,
    SRPWM_VALLEY_TRIGGER_SCMPC_DOWN     = 0x5,
    SRPWM_VALLEY_TRIGGER_SCMPD_UP       = 0x6,
    SRPWM_VALLEY_TRIGGER_SCMPD_DOWN     = 0x7,
    SRPWM_VALLEY_TRIGGER_FAULT_POS0     = 0x8,
    SRPWM_VALLEY_TRIGGER_FAULT_POS1     = 0x9,
    SRPWM_VALLEY_TRIGGER_FAULT_POS2     = 0xA,
    SRPWM_VALLEY_TRIGGER_FAULT_POS3     = 0xB
} SRPWM_ValleyTrigger;

/**
 * @brief specify the valley target edge
 */
typedef enum
{
    SRPWM_VALLEY_TARGET_EDGE_NONE = 0x0,
    SRPWM_VALLEY_TARGET_EDGE_1    = 0x1,
    SRPWM_VALLEY_TARGET_EDGE_2    = 0x2,
    SRPWM_VALLEY_TARGET_EDGE_3    = 0x3,
    SRPWM_VALLEY_TARGET_EDGE_4    = 0x4,
    SRPWM_VALLEY_TARGET_EDGE_5    = 0x5,
    SRPWM_VALLEY_TARGET_EDGE_6    = 0x6,
    SRPWM_VALLEY_TARGET_EDGE_7    = 0x7
} SRPWM_ValleyTargetEdge;

/**
 * @brief specify the valley count edge
 */
typedef enum
{
    SRPWM_VALLEY_COUNT_EDGE_NONE = 0x0,
    SRPWM_VALLEY_COUNT_EDGE_1    = 0x1,
    SRPWM_VALLEY_COUNT_EDGE_2    = 0x2,
    SRPWM_VALLEY_COUNT_EDGE_3    = 0x3,
    SRPWM_VALLEY_COUNT_EDGE_4    = 0x4,
    SRPWM_VALLEY_COUNT_EDGE_5    = 0x5,
    SRPWM_VALLEY_COUNT_EDGE_6    = 0x6,
    SRPWM_VALLEY_COUNT_EDGE_7    = 0x7,
    SRPWM_VALLEY_COUNT_EDGE_8    = 0x8,
    SRPWM_VALLEY_COUNT_EDGE_9    = 0x9,
    SRPWM_VALLEY_COUNT_EDGE_10   = 0xA,
    SRPWM_VALLEY_COUNT_EDGE_11   = 0xB,
    SRPWM_VALLEY_COUNT_EDGE_12   = 0xC,
    SRPWM_VALLEY_COUNT_EDGE_13   = 0xD,
    SRPWM_VALLEY_COUNT_EDGE_14   = 0xE,
    SRPWM_VALLEY_COUNT_EDGE_15   = 0xF
} SRPWM_ValleyCountEdge;

/**
 * @brief specify the valley delay mode
 */
typedef enum
{
    SRPWM_VALLEY_DELAY_MODE_SW_DELAY                           = 0x0,
    SRPWM_VALLEY_DELAY_MODE_INTERVAL_CNT_AND_SW_DELAY          = 0x1,
    SRPWM_VALLEY_DELAY_MODE_INTERVAL_CNT_DIVIDE2_AND_SW_DELAY  = 0x2,
    SRPWM_VALLEY_DELAY_MODE_INTERVAL_CNT_DIVIDE4_AND_SW_DELAY  = 0x3,
    SRPWM_VALLEY_DELAY_MODE_INTERVAL_CNT_DIVIDE8_AND_SW_DELAY  = 0x4,
    SRPWM_VALLEY_DELAY_MODE_INTERVAL_CNT_DIVIDE16_AND_SW_DELAY = 0x5
} SRPWM_ValleyDelayMode;

/**
 * @brief specify the valley capture source
 */
typedef enum
{
    SRPWM_VALLEY_CAPTURE_SRC_FAULT_REAL0 = 0x0,
    SRPWM_VALLEY_CAPTURE_SRC_FAULT_REAL1 = 0x1,
    SRPWM_VALLEY_CAPTURE_SRC_FAULT_REAL2 = 0x2,
    SRPWM_VALLEY_CAPTURE_SRC_FAULT_REAL3 = 0x3
} SRPWM_ValleyCaptureSrc;

/**
 * @brief specify the edge of the signal
 */
typedef enum
{
    SRPWM_EDGE_POS_A = 0,
    SRPWM_EDGE_NEG_A = 1,
    SRPWM_EDGE_POS_B = 2,
    SRPWM_EDGE_NEG_B = 3
} SRPWM_Edge;

/**
 * @brief specify the shadow update status
 */
typedef enum
{
    SRPWM_SHD_UPT_STATUS_PRD_UPT_DONE   = (uint16_t)(0x0001),
    SRPWM_SHD_UPT_STATUS_PHASE_UPT_DONE = (uint16_t)(0x0002),
    SRPWM_SHD_UPT_STATUS_CMP_UPT_DONE   = (uint16_t)(0x0004),
    SRPWM_SHD_UPT_STATUS_SCMP_UPT_DONE  = (uint16_t)(0x0008),
    SRPWM_SHD_UPT_STATUS_PG_UPT_DONE    = (uint16_t)(0x0010),
    SRPWM_SHD_UPT_STATUS_DB_UPT_DONE    = (uint16_t)(0x0020),
    SRPWM_SHD_UPT_STATUS_BURST_UPT_DONE = (uint16_t)(0x0040),
    SRPWM_SHD_UPT_STATUS_MULTI_CFG_DONE = (uint16_t)(0x0100)
} SRPWM_ShadowUpdateStatus;

/**
 * @brief specify the dma channel
 */
typedef enum
{
    SRPWM_DMA_CHANNEL0 = 0,
    SRPWM_DMA_CHANNEL1 = 1,
    SRPWM_DMA_CHANNEL2 = 2,
    SRPWM_DMA_CHANNEL3 = 3
} SRPWM_DMAChannel;


/**
 * @brief timebase initializes the struct
 */
typedef struct __PACKED
{
    uint32_t          period;   /* standard accuracy */
    uint8_t           periodHR; /* high precision */
    SRPWM_CountMode   countMode;
    uint32_t          phase0;
    uint32_t          phase1;
    FunctionalState   waitSync0TimerEn;
    SRPWM_SyncDirMode sync0CountDir; /* note:up-dowm mode is not supported in the synchronous counting direction */
    SRPWM_SyncDirMode sync1CountDir;
    FunctionalState   periodShadowLoadEn;
    uint16_t          periodShadowLoadSel; /* corresponds to synchronous load 1 */
    uint16_t          phase0ShadowLoadSel; /* corresponds to synchronous load 2 */
    FunctionalState   phase0ShadowLoadEn;
    uint8_t           syncIn0;
    uint8_t           syncIn1;
} SRPWM_TBInitTypeDef;
typedef struct __PACKED
{
    uint8_t risingHR;
    uint8_t fallingHR;
} SRPWM_AB_CMP_HRInitTypeDef;

/**
 * @brief the comparator initializes the struct
 */
typedef struct __PACKED
{
    FunctionalState            cmpEventOutSingleEn;
    SRPWM_CMPEventOutMode      cmpEventOutMode;
    uint32_t                   cmpA;
    uint32_t                   cmpB;
    uint32_t                   cmpC;
    uint32_t                   cmpD;
    SRPWM_AB_CMP_HRInitTypeDef a;
    SRPWM_AB_CMP_HRInitTypeDef b;
    uint32_t                   scmpA;
    uint32_t                   scmpB;
    uint32_t                   scmpC;
    uint32_t                   scmpD;
    FunctionalState            cmpShadowLoadEn;
    FunctionalState            scmpShadowLoadEn;
    uint16_t                   cmpShadowLoadSel;  /* corresponds to synchronous load event 1*/
    uint16_t                   scmpShadowLoadSel; /* corresponds to synchronous load event 1 */
} SRPWM_CMPInitTypeDef;

/**
 * @brief the pwm generator initializes the struct of A/B
 */
typedef struct __PACKED
{
    SRPWM_PGEvt     event;
    SRPWM_PGValue   value;

    FunctionalState swEndSigSyncEn;
    FunctionalState swStartSigSyncEn;
    uint16_t        swEndSigSel;
    uint16_t        swStartSigSel;
    uint16_t        swDlyFalling;
    uint16_t        swDlyRising;
} SRPWM_AB_PGInitTypeDef;

/**
 * @brief the pwm generator initializes the struct
 */
typedef struct __PACKED
{
    SRPWM_AB_PGInitTypeDef a;
    SRPWM_AB_PGInitTypeDef b;

    uint16_t               shadowLoadSel; /* corresponds to synchronous load event 2 */
    FunctionalState        shadowLoadEn;
    uint8_t                priorityGap;   /* action matrix priority interval */
} SRPWM_PGInitTypeDef;

/**
 * @brief the deadband initializes the struct of A/B
 */
typedef struct __PACKED
{
    FunctionalState     selComplementChannel;
    FunctionalState     selRisingDelay;
    FunctionalState     selFallingDelay;
    SRPWM_DBOutputState selOutputState;
    uint16_t            risingDelay;
    uint16_t            risingDelayHR;
    uint16_t            fallingDelay;
    uint16_t            fallingDelayHR;
} SRPWM_AB_DBInitTypeDef;

/**
 * @brief the deadband initializes the struct
 */
typedef struct __PACKED
{
    SRPWM_AB_DBInitTypeDef a;
    SRPWM_AB_DBInitTypeDef b;

    uint16_t               shadowLoadSel; /* corresponds to synchronous load event 2*/
    FunctionalState        shadowLoadEn;
} SRPWM_DBInitTypeDef;

/**
 * @brief the burst initializes the struct
 */
typedef struct __PACKED
{
    uint8_t         m;
    uint8_t         n;
    FunctionalState burstEn;
    SRPWM_BurstMode mode;
    uint8_t         startSync;
    FunctionalState shadowLoadEn;
    uint16_t        shadowLoadSel; /* corresponds to synchronous load event 1 */
} SRPWM_BurstInitTypeDef;

/**
 * @brief the fault pre-protection initializes the struct
 */
typedef struct __PACKED
{
    uint8_t                  faultSigGroupMask;
    FunctionalState          countFaultEn;
    FunctionalState          latchFaultEn;
    SRPWM_FPPFaultMode       faultMode;
    uint32_t                 blkEndSigSel; /* use the all events collection */
    uint32_t                 blkStartSigSel;
    uint16_t                 blkEndDly;
    uint16_t                 blkStartDly;
    FunctionalState          blkEn;
    SRPWM_FPPBlankingMode    blkMode;
    SRPWM_FPPFaultSigEgdeSel faultSigEgdeSel;
    FunctionalState          filterEn;
    uint16_t                 filterLen;
    uint8_t                  countThreshold;
    FunctionalState          countEn;
    SRPWM_FPPCountSigSel     countSigSel;
    uint8_t                  countMode;
    uint8_t                  countWindow;
    uint8_t                  countPeriod;
} SRPWM_FPPInitTypeDef;

/**
 * @brief the valley initializes the struct
 */
typedef struct __PACKED
{
    /* configure the heartbeat for the input */
    SRPWM_ValleyCaptureSrc     captureSrc;
    /* detects the edge pattern of the input */
    SRPWM_ValleyEdgeDetectMode edgeDetectMode;
    /* configure trigger signals */
    SRPWM_ValleyTrigger        triggerSrc;
    /* select the pulse edge of the resonant output */
    SRPWM_ValleyTargetEdge     targetEdge;

    /*
     * whether to enable the valley fault output channel channel selection for valley output if selected the original
     * abnormal signal will be replaced with the current output signal and sent to other modules as an abnormal signal
     */
    FunctionalState            outChannelEn;
    /* select the starting edge of the count */
    SRPWM_ValleyCountEdge      startCountEdge;
    /* select the end edge of the count */
    SRPWM_ValleyCountEdge      stopCountEdge;
    /* select the mode of delay */
    SRPWM_ValleyDelayMode      delayMode;
    /* set the software delay value */
    uint32_t                   swDelayValue;
    /* delay output enabled */
    FunctionalState            delayEn;
} SRPWM_ValleyInitTypeDef;

/**
 * @brief the preprotect initializes the struct of A/B
 */
typedef struct __PACKED
{
    uint16_t              cbcFaultProtectSig;
    uint16_t              osFaultProtectSig;
    uint16_t              unresFaultProtectSig; /* software mask signals are not supported */
    SRPWM_PreprotectState cbcFaultProtectState;
    SRPWM_PreprotectState osFaultProtectState;
    SRPWM_PreprotectState unresFaultProtectState;
    FunctionalState       osStartSyncEn;
    FunctionalState       osEndSyncEn;
    uint32_t              osStartSyncSel;
    uint32_t              osEndSyncSel;
    uint32_t              cbcEndSyncSel;
    uint16_t              setHighDly;
    uint16_t              setLowDly;
} SRPWM_AB_PREPInitTypeDef;

/**
 * @brief the preprotect initializes the struct
 */
typedef struct __PACKED
{
    SRPWM_AB_PREPInitTypeDef a;
    SRPWM_AB_PREPInitTypeDef b;

    FunctionalState          fastProtectMask;
} SRPWM_PREPInitTypeDef;     /* fault preprotect */

/**
 * @brief the postprotect initializes the struct of A/B
 */
typedef struct __PACKED
{
    SRPWM_PSTPOutState mutexOutState;
    FunctionalState    invertEn;
} SRPWM_AB_PSTPInitTypeDef;

/**
 * @brief the postprotect initializes the struct
 */
typedef struct __PACKED
{
    SRPWM_AB_PSTPInitTypeDef      a;
    SRPWM_AB_PSTPInitTypeDef      b;

    SRPWMCOM_SRPWM_MutexCondition mutexConditionAB;
    FunctionalState               mutexEn;
    FunctionalState               swapSyncEn;
    FunctionalState               swapEn;
} SRPWM_PSTPInitTypeDef;   /* post protect */

/**
 * @brief the mutex initializes the struct
 */
typedef struct __PACKED
{
    uint16_t                      mutexResultGroupMask;
    SRPWMCOM_MutexSig             mutexSig0;
    SRPWMCOM_MutexSig             mutexSig1;
    SRPWMCOM_SRPWM_MutexCondition mutexCondition;
} SRPWMCOM_MutexInitTypeDef;

/* common top level functionality SRPWM COM */
void SRPWMCOM_enable(uint16_t channelMask);
void SRPWMCOM_disable(uint16_t channelMask);
void SRPWMCOM_generateSwEvt(uint16_t channelMask);
void SRPWMCOM_enableLatchCnt(uint16_t channel);
void SRPWMCOM_disableLatchCnt(uint16_t channel);
void SRPWMCOM_setLatchCntSrc(uint16_t channel, SRPWMCOM_LatchCntSrc latchSrc);
uint32_t SRPWMCOM_getTimeBaseCounterValue(uint16_t channel);

/* broadcast function */
void SRPWMCOM_enableBroadcast(uint16_t channelMask);
void SRPWMCOM_disableBroadcast(uint16_t channelMask);

/* baisic pwm functionality*/
void SRPWM_initTBStruct(SRPWM_TBInitTypeDef *initStruct);
void SRPWM_initTB(SRPWM_Type *SRPWMx, SRPWM_TBInitTypeDef *init);
void SRPWM_initCMPStruct(SRPWM_CMPInitTypeDef *initStruct);
void SRPWM_initCMP(SRPWM_Type *SRPWMx, SRPWM_CMPInitTypeDef *init);
void SRPWM_initDBStruct(SRPWM_DBInitTypeDef *initStruct);
void SRPWM_initDB(SRPWM_Type *SRPWMx, SRPWM_DBInitTypeDef *init);
void SRPWM_setTimeBasePeriod(SRPWM_Type *SRPWMx, uint32_t periodCount);
uint32_t SRPWM_getTimeBasePeriod(SRPWM_Type *SRPWMx);
void SRPWM_setCounterCompareValue(SRPWM_Type *SRPWMx, SRPWM_CounterCompareModule compModule, uint32_t compCount);
void SRPWM_setPhaseShift(SRPWM_Type *SRPWMx, SRPWM_PhaseType phaseType, uint32_t phaseCount);
void SRPWM_setDB(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint16_t deadTime);

/* PWM generate function */
void SRPWMCOM_forcePGSwSigOnePulse(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWMCOM_forcePGSwSigHighLevel(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWMCOM_forcePGSwSigLowLevel(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWM_initPGStruct(SRPWM_PGInitTypeDef *initStruct);
void SRPWM_initPG(SRPWM_Type *SRPWMx, SRPWM_PGInitTypeDef *init);
void SRPWM_setPG(SRPWM_Type *SRPWMx, SRPWM_AB pwmAB, SRPWM_PGEvt event, SRPWM_PGValue value);

/* interrupt functionality */
void SRPWM_enableInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
void SRPWM_disableInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
void SRPWM_setInterruptMask(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
void SRPWM_clearInterruptMask(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
void SRPWM_forceInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
void SRPWM_clearInterruptStatus(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask);
ITStatus SRPWM_getInterruptStatus(SRPWM_Type *SRPWMx, uint16_t interruptFlag);
ITStatus SRPWM_getInterruptStatusRaw(SRPWM_Type *SRPWMx, uint16_t interruptFlag);

/* OEP event interrupt */
void SRPWM_enableEvtInterrupt(SRPWM_Type *SRPWMx, uint32_t outEventMask);
void SRPWM_disableEvtInterrupt(SRPWM_Type *SRPWMx, uint32_t outEventMask);
void SRPWM_enableEvtInterruptFreqDiv(SRPWM_Type *SRPWMx);
void SRPWM_disableEvtInterruptFreqDiv(SRPWM_Type *SRPWMx);
void SRPWM_setEvtInterruptFreqDiv(SRPWM_Type *SRPWMx, uint8_t div);
void SRPWM_enableEvtInterruptFreqMulti(SRPWM_Type *SRPWMx);
void SRPWM_disableEvtInterruptFreqMulti(SRPWM_Type *SRPWMx);
void SRPWM_setEvtInterruptFreqMulti(SRPWM_Type *SRPWMx, uint16_t multi);

/* burst function */
void SRPWM_initBurstStruct(SRPWM_BurstInitTypeDef *initStruct);
void SRPWM_initBurst(SRPWM_Type *SRPWMx, SRPWM_BurstInitTypeDef *init);
void SRPWM_setBurstM(SRPWM_Type *SRPWMx, uint8_t m);
void SRPWM_setBurstN(SRPWM_Type *SRPWMx, uint8_t n);

/* FPP exception pre processing capabilities */
void SRPWM_initFPPStruct(SRPWM_FPPInitTypeDef *initStruct);
void SRPWM_initFPP(SRPWM_Type *SRPWMx, SRPWM_FPPInitTypeDef *init);
void SRPWM_clearFPPFaultCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup);
void SRPWM_clearFPPLatchFault(SRPWM_Type *SRPWMx, uint8_t faultSigGroup);
void SRPWM_clearFPPFilterCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup);
FlagStatus SRPWM_getFPPFaultStatus(SRPWM_Type *SRPWMx, uint16_t faultSig);
uint16_t SRPWM_getFPPFaultCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup);

/* valley switch function */
void SRPWM_initValleyStruct(SRPWM_ValleyInitTypeDef *initStruct);
void SRPWM_initValley(SRPWM_Type *SRPWMx, SRPWM_ValleyInitTypeDef *init);
void SRPWM_enableValley(SRPWM_Type *SRPWMx);
void SRPWM_disableValley(SRPWM_Type *SRPWMx);
void SRPWM_forceValley(SRPWM_Type *SRPWMx);

/* PREP exception protection pre processing capabilities */
void SRPWMCOM_enterPREPOneShot(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWMCOM_exitPREPOneShot(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWMCOM_forcePREPCycleByCycle(uint16_t channelMask, SRPWM_AB pwmAB);
void SRPWM_setPREPUnresMinTime(SRPWM_Type *SRPWMx, uint16_t min_time);
void SRPWM_initPREPStruct(SRPWM_PREPInitTypeDef *initStruct);
void SRPWM_initPREP(SRPWM_Type *SRPWMx, SRPWM_PREPInitTypeDef *init);
void SRPWM_clearPREPTimer(SRPWM_Type *SRPWMx, uint8_t state);
FlagStatus SRPWM_getPREPSigState(SRPWM_Type *SRPWMx, SRPWM_PREP_SigState sigState);
uint32_t SRPWM_getPREPFaultTime(SRPWM_Type *SRPWMx, SRPWM_AB ab, SRPWM_PreprotectState sig);

/* PSTP post processing capabilities for exception protection */
void SRPWMCOM_forcePSTPOutState(uint16_t channel, SRPWM_AB pwmAB, SRPWM_PSTPOutState state);
void SRPWMCOM_initMutexStruct(SRPWMCOM_MutexInitTypeDef *initStruct);
void SRPWMCOM_initMutex(SRPWMCOM_MutexInitTypeDef *init);
void SRPWMCOM_enableMutex(uint16_t mutexResultGroupMask);
void SRPWMCOM_disableMutex(uint16_t mutexResultGroupMask);
void SRPWMCOM_enableMutexMsk(uint16_t channel, uint16_t mutexResultGroupMask);
void SRPWMCOM_disableMutexMsk(uint16_t channel, uint16_t mutexResultGroupMask);
FlagStatus SRPWMCOM_getMutexStatus(uint16_t mutexResultGroup);
uint16_t SRPWMCOM_getMutexStatusAllBits(void);
void SRPWMCOM_clearMutexStatus(uint16_t mutexResultGroupMask);
void SRPWM_initPSTPStruct(SRPWM_PSTPInitTypeDef *initStruct);
void SRPWM_initPSTP(SRPWM_Type *SRPWMx, SRPWM_PSTPInitTypeDef *init);
FlagStatus SRPWM_getPSTPFaultState(SRPWM_Type *SRPWMx, SRPWM_PSTPFaultStateSig sig);

/* HRPWM high precision functionality */
void SRPWM_setPeriodHR(SRPWM_Type *SRPWMx, uint8_t periodHR);
void SPPWM_setCompareHR(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint8_t cmpHR);
void SRPWM_setDBHR(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint8_t deadTimeHR);
void SRPWMCOM_enableHR(uint16_t channelMask);
void SRPWMCOM_disableHR(uint16_t channelMask);
void SRPWM_enableHRPWMDLL(uint16_t channel, SRPWM_AB ab);
void SRPWM_disableHRPWMDLL(uint16_t channel, SRPWM_AB ab);
void SRPWM_enableHRPWMBypass(SRPWM_Type *SRPWMx);
void SRPWM_disableHRPWMBypass(SRPWM_Type *SRPWMx);
void SRPWM_enableHRPWMFilter(SRPWM_Type *SRPWMx);
void SRPWM_disableHRPWMFilter(SRPWM_Type *SRPWMx);
void SRPWM_setHRPWMFilterWidth(SRPWM_Type *SRPWMx, uint16_t width);
uint8_t SRPWM_getHRPWMEgdeDly(SRPWM_Type *SRPWMx, SRPWM_Edge edge);

/* DMA Request */
void SRPWMCOM_enableDMA(SRPWM_DMAChannel dmaChannel, uint16_t channel);
void SRPWMCOM_disableDMA(SRPWM_DMAChannel dmaChannel);
void SRPWM_setDMARequest(SRPWM_Type *SRPWMx, uint32_t outEventMask);
void SRPWM_clearDMARequest(SRPWM_Type *SRPWMx, uint32_t outEventMask);
void SRPWM_enableDMAFreqDiv(SRPWM_Type *SRPWMx);
void SRPWM_disableDMAFreqDiv(SRPWM_Type *SRPWMx);
void SRPWM_setDMAFreqDiv(SRPWM_Type *SRPWMx, uint8_t div);
void SRPWM_enableDMAFreqMulti(SRPWM_Type *SRPWMx);
void SRPWM_disableDMAFreqMulti(SRPWM_Type *SRPWMx);
void SRPWM_setDMAFreqMulti(SRPWM_Type *SRPWMx, uint16_t multi);

/* ADC Trigger */
void SRPWMCOM_selectTriggerToQEP(uint32_t srcTriggerMask, SRPWMCOM_QEPx dstQepNumber);
void SRPWM_setADCTriggerSource(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint32_t socSource);
void SRPWM_clearADCTriggerSource(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint32_t socSource);
void SRPWM_enableADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType);
void SRPWM_disableADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType);
void SRPWM_setADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType,
                                      uint8_t preScaleCount);
void SRPWM_enableADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType);
void SRPWM_disableADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType);
void SRPWM_setADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint16_t multi);

/* OEP sync signal output */
void SRPWMCOM_selectSyncToSRPWM(SRPWMCOM_SRPWM_SYNCOUT srcSync, SRPWM_SyncType dstSyncTypeIn, uint16_t dstChannel);
void SRPWM_selectSyncOut(SRPWM_Type *SRPWMx, uint32_t srcSync, SRPWM_SyncType dstSyncTypeOut);
void SRPWM_selectSyncOutDly(SRPWM_Type *SRPWMx, SRPWM_SyncType syncTypeOut, uint8_t delay);
void SRPWMCOM_selectSyncToXBAR(SRPWMCOM_SRPWM_SYNCOUT srcSync, SRPWMCOM_XBARx dstXbarNumber);
void SRPWM_setDACTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_DACx dstDacNumber);
void SRPWM_setACMPTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_ACMPx dstAcmpNumber);
void SRPWM_setACMPBlankingTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_ACMPx dstAcmpNumber);

/* shadow function */
void SRPWMCOM_forceMultiChannelShadow(uint16_t channelMask);
void SRPWM_enableShadowMultiRegSync(SRPWM_Type *SRPWMx, uint8_t regMask);
void SRPWM_disableShadowMultiRegSync(SRPWM_Type *SRPWMx, uint8_t regMask);
void SRPWM_enableMultiShadowWaitPrd(SRPWM_Type *SRPWMx);
void SRPWM_disableMultiShadowWaitPrd(SRPWM_Type *SRPWMx);
FlagStatus SRPWM_getShadowUpdateStatus(SRPWM_Type *SRPWMx, SRPWM_ShadowUpdateStatus reg);
void SRPWM_clearShadowUpdateStatus(SRPWM_Type *SRPWMx, SRPWM_ShadowUpdateStatus reg);


/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif  /*__ET6X_SRPWM_H */
