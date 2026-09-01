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

#include "et6x_srpwm.h"

#define SRPWM_CORE_NUM             (12UL)
#define SRPWM_CORE_NUM_OF_GROUP    (4UL)
#define SRPWM_LR_POS               (7UL)
#define SRPWM_LR_MSK               (0x7FFFFE0UL)
#define SRPWM_DB_LR_MSK            (0x7FFE0UL)
#define SRPWM_HR_POS               (0UL)
#define SRPWM_HR_MSK               (0x1FUL)

#define IS_SRPWM_PERIPH(PERIPH) \
        (((PERIPH) == SRPWM0) || ((PERIPH) == SRPWM1) || \
         ((PERIPH) == SRPWM2) || ((PERIPH) == SRPWM3) || \
         ((PERIPH) == SRPWM4) || ((PERIPH) == SRPWM5) || \
         ((PERIPH) == SRPWM6) || ((PERIPH) == SRPWM7) || \
         ((PERIPH) == SRPWM8) || ((PERIPH) == SRPWM9) || \
         ((PERIPH) == SRPWM10) || ((PERIPH) == SRPWM11) || \
         ((PERIPH) == SRPWM_GLOBAL))

#define IS_SRPWM_CHANNEL(CHANNEL)                   (((CHANNEL) != 0x00) && (((CHANNEL) & 0xF000) == 0x00))
#define IS_SRPWM_HR_CHANNEL(CHANNEL)                (((CHANNEL) != 0x00) && (((CHANNEL) & 0xFFF0) == 0x00))
#define IS_GET_SRPWM_CHANNEL(CHANNEL) \
        (((CHANNEL) == SRPWM_CHANNEL_0) || \
         ((CHANNEL) == SRPWM_CHANNEL_1) || \
         ((CHANNEL) == SRPWM_CHANNEL_2) || \
         ((CHANNEL) == SRPWM_CHANNEL_3) || \
         ((CHANNEL) == SRPWM_CHANNEL_4) || \
         ((CHANNEL) == SRPWM_CHANNEL_5) || \
         ((CHANNEL) == SRPWM_CHANNEL_6) || \
         ((CHANNEL) == SRPWM_CHANNEL_7) || \
         ((CHANNEL) == SRPWM_CHANNEL_8) || \
         ((CHANNEL) == SRPWM_CHANNEL_9) || \
         ((CHANNEL) == SRPWM_CHANNEL_10) || \
         ((CHANNEL) == SRPWM_CHANNEL_11))
#define IS_SRPWM_MUTEX_RESULT_GRP(GRP)              (((GRP) != 0x00) && (((GRP) & 0xF000) == 0x00))
#define IS_GET_SRPWM_MUTEX_RESULT_GRP(GRP) \
        (((GRP) == SRPWM_MUTEX_RESULT_GRP_0) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_1) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_2) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_3) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_4) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_5) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_6) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_7) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_8) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_9) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_10) || \
         ((GRP) == SRPWM_MUTEX_RESULT_GRP_11))

#define IS_SRPWM_SYNCEVTLOAD1(SYNCEVT)              ((SYNCEVT) < 0x4000)
#define IS_SRPWM_SYNCEVTLOAD2(SYNCEVT)              ((SYNCEVT) < 0x4000)
#define IS_SRPWM_ALLEVT(EVT)                        ((EVT) < 0x40000000)
#define IS_SRPWM_OUT_EVT(EVT)                       ((EVT) < 0x1000000)
#define IS_SRPWM_GET_OUT_EVT(EVT) \
        (((EVT) == SRPWM_OUTEVT_SYNC_ZERO_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_PRD_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPA_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPB_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPC_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPD_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_BURST_A_NEG) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_BURST_A_POS) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_BURST_B_NEG) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_BURST_B_POS) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_TIMER_0SYNC) || \
         ((EVT) == SRPWM_OUTEVT_SYNC_TIMER_1SYNC))

#define IS_SRPWM_TBCOUNTER_SYNCEVT(SYNCEVT)         ((SYNCEVT) < 0x80)
#define IS_SRPWM_AQ_SWSYNC(SWSYNC)                  ((SWSYNC) < 0x400)
#define IS_SRPWM_AQ_PRIORITY_GAP(GAP)               ((GAP) < 0x10)
#define IS_SRPWM_AQ_SW_DLY_FALLING_RISING(DELAY)    ((DELAY) < 0x400)
#define IS_SRPWM_BURST_START_SYNC(EVT)              ((EVT) < 0x40)
#define IS_SRPWM_FPP_FAULT_SIG(SIG)                 ((SIG) < 0x40U)
#define IS_SRPWM_FPP_FILTER_LEN(LEN)                ((LEN) < 0x400U)
#define IS_SRPWM_GET_FPP_FAULT_SIG(SIG) \
        (((SIG) == SRPWM_FPP_FAULT_SIG_GRP0) || ((SIG) == SRPWM_FPP_FAULT_SIG_GRP1) || \
         ((SIG) == SRPWM_FPP_FAULT_SIG_GRP2) || ((SIG) == SRPWM_FPP_FAULT_SIG_GRP3) || \
         ((SIG) == SRPWM_FPP_FAULT_SIG_GRP4) || ((SIG) == SRPWM_FPP_FAULT_SIG_GRP5))

#define IS_SRPWM_FPP_FAULT_REAL_LATCH(SIG) \
        (((SIG) == SRPWM_FPP_FAULT_REAL0) || ((SIG) == SRPWM_FPP_FAULT_REAL1) || \
         ((SIG) == SRPWM_FPP_FAULT_REAL2) || ((SIG) == SRPWM_FPP_FAULT_REAL3) || \
         ((SIG) == SRPWM_FPP_FAULT_REAL4) || ((SIG) == SRPWM_FPP_FAULT_REAL5) || \
         ((SIG) == SRPWM_FPP_FAULT_LATCH0) || ((SIG) == SRPWM_FPP_FAULT_LATCH1) || \
         ((SIG) == SRPWM_FPP_FAULT_LATCH2) || ((SIG) == SRPWM_FPP_FAULT_LATCH3) || \
         ((SIG) == SRPWM_FPP_FAULT_LATCH4) || ((SIG) == SRPWM_FPP_FAULT_LATCH5))

#define IS_SRPWM_PREP_SIG(SIG)          ((SIG) < 0x2000)
#define IS_SRPWM_PREP_UNRES_SIG(SIG)    ((SIG) < 0x1000)

#define IS_SRPWM_PREP_TIMER(STATE) \
        (((STATE) == SRPWM_PREP_A_SET_TIMER) || ((STATE) == SRPWM_PREP_A_CLR_TIMER) || \
         ((STATE) == SRPWM_PREP_A_INVERT_TIMER) || ((STATE) == SRPWM_PREP_A_HIZ_TIMER) || \
         ((STATE) == SRPWM_PREP_B_SET_TIMER) || ((STATE) == SRPWM_PREP_B_CLR_TIMER) || \
         ((STATE) == SRPWM_PREP_B_INVERT_TIMER) || ((STATE) == SRPWM_PREP_B_HIZ_TIMER))

#define IS_SRPWM_PSTP_FAULT_SIG(SIG)         ((SIG) < 0x10)

#define IS_SRPWM_IT(IT)                      (((IT) != 0x00) && ((IT) < (uint16_t)(1 << 14)))
#define IS_SRPWM_GET_IT(IT) \
        (((IT) == SRPWM_IT_EVT) || ((IT) == SRPWM_IT_BURST_OVER) || \
         ((IT) == SRPWM_IT_FAULT_REAL0) || ((IT) == SRPWM_IT_FAULT_REAL1) || \
         ((IT) == SRPWM_IT_FAULT_REAL2) || ((IT) == SRPWM_IT_FAULT_REAL3) || \
         ((IT) == SRPWM_IT_FAULT_REAL4) || ((IT) == SRPWM_IT_FAULT_REAL5) || \
         ((IT) == SRPWM_IT_FAULT_LATCH0) || ((IT) == SRPWM_IT_FAULT_LATCH1) || \
         ((IT) == SRPWM_IT_FAULT_LATCH2) || ((IT) == SRPWM_IT_FAULT_LATCH3) || \
         ((IT) == SRPWM_IT_FAULT_LATCH4) || ((IT) == SRPWM_IT_FAULT_LATCH5))

#define IS_SRPWM_SHADOW_MULTICFG_REG(REG)    ((REG) < 0x40)

#define IS_SRPWM_PERIOD(PERIOD)              ((PERIOD) < 0x400000)
#define IS_SRPWM_CMP(CMP)                    ((CMP) < 0x400000)
#define IS_SRPWM_PHASE(PHASE)                ((PHASE) < 0x400000)
#define IS_SRPWM_HR(HR)                      ((HR) < 0x20)
#define IS_SRPWM_DEADTIME(DEADTIME)          ((DEADTIME) < 0x4000)
#define IS_SRPWM_HRPWM_FILTER_LEN(LEN)       ((LEN) < 0x400)
#define IS_SRPWM_OEP_SYNC_DLY(DLY)           ((DLY) < 0x10)
/* Private functions ---------------------------------------------------------*/

/**
 * @brief specifying spwm modules is enabled via the spwmcom module
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @attention This function should be called after all SRPWM_initXXXX() functions.
 */
void SRPWMCOM_enable(uint16_t channelMask)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    SET_BIT(SRPWMCOM->EPWM_EN, channelMask);
}

/**
 * @brief specifying spwm modules is disabled via the spwmcom module
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 */
void SRPWMCOM_disable(uint16_t channelMask)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    CLEAR_BIT(SRPWMCOM->EPWM_EN, channelMask);
}

/**
 * @brief Generates a Software Event For Various Sync Signal Selections
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 */
void SRPWMCOM_generateSwEvt(uint16_t channelMask)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    SET_BIT(SRPWMCOM->EPWM_SFT_EVT, channelMask);
}

/**
 * @brief enable the counter latch function of the spwm module
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 */
void SRPWMCOM_enableLatchCnt(uint16_t channel)
{
    uint8_t bitGourpPos = 0;

    assert_param(IS_GET_SRPWM_CHANNEL(channel));

    bitGourpPos = POSITION_VAL(channel) / SRPWM_CORE_NUM_OF_GROUP;

    SET_BIT(SRPWMCOM->MEPWM_TBCNT_LC_EN, BIT_MASK(bitGourpPos));
}

/**
 * @brief disable the counter latch function of the spwm module
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 */
void SRPWMCOM_disableLatchCnt(uint16_t channel)
{
    uint8_t bitGourpPos = 0;

    assert_param(IS_GET_SRPWM_CHANNEL(channel));

    bitGourpPos = POSITION_VAL(channel) / SRPWM_CORE_NUM_OF_GROUP;

    CLEAR_BIT(SRPWMCOM->MEPWM_TBCNT_LC_EN, BIT_MASK(bitGourpPos));
}

/**
 * @brief counter latch sync signal  select signal
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param latchSrc  the specified latch source
 */
void SRPWMCOM_setLatchCntSrc(uint16_t channel, SRPWMCOM_LatchCntSrc latchSrc)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));

    if (channel < SRPWM_CHANNEL_4)
    {
        MODIFY_REG(SRPWMCOM->MEPWM_TBCNT_LCSIG_SEL,
                   SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG0_SEL_Msk,
                   (uint32_t)latchSrc << SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG0_SEL_Pos);
    }
    else if (channel < SRPWM_CHANNEL_8)
    {
        MODIFY_REG(SRPWMCOM->MEPWM_TBCNT_LCSIG_SEL,
                   SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG1_SEL_Msk,
                   (uint32_t)latchSrc << SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG1_SEL_Pos);
    }
    else
    {
        MODIFY_REG(SRPWMCOM->MEPWM_TBCNT_LCSIG_SEL,
                   SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG2_SEL_Msk,
                   (uint32_t)latchSrc << SRPWMCOM_MEPWM_TBCNT_LCSIG_SEL_MEPWM_TBCNT_LCSIG2_SEL_Pos);
    }
}

/**
 * @brief get the current value of the time base counter by latch
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @return uint32_t return the time base counter value
 */
uint32_t SRPWMCOM_getTimeBaseCounterValue(uint16_t channel)
{
    uint32_t ret = 0;

    assert_param(IS_GET_SRPWM_CHANNEL(channel));

    ret = READ_REG(SRPWMCOM->TB_SFTLOCK[POSITION_VAL(channel)]);

    return ret;
}

/**
 * @brief enable the broadcast function
 *
 * @param channelMask select the channel to be enabled
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @return * void
 */
void SRPWMCOM_enableBroadcast(uint16_t channelMask)
{
    SET_BIT(SYSC->SYSC2SPWM, channelMask);
}

/**
 * @brief disable the broadcast function
 *
 * @param channelMask select the channel to be disabled
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @return * void
 */
void SRPWMCOM_disableBroadcast(uint16_t channelMask)
{
    CLEAR_BIT(SYSC->SYSC2SPWM, channelMask);
}

/**
 * @brief TBInitStruct Init
 *
 * @param initStruct
 */
void SRPWM_initTBStruct(SRPWM_TBInitTypeDef *initStruct)
{
    initStruct->period              = 0;
    initStruct->periodHR            = 0;
    initStruct->countMode           = SRPWM_COUNTMODE_UPDOWN;
    initStruct->phase0              = 0;
    initStruct->phase1              = 0;
    initStruct->waitSync0TimerEn    = DISABLE;
    initStruct->sync0CountDir       = SRPWM_SYNC_DIR_DOWN;
    initStruct->sync1CountDir       = SRPWM_SYNC_DIR_DOWN;
    initStruct->periodShadowLoadEn  = DISABLE;
    initStruct->periodShadowLoadSel = 0;
    initStruct->phase0ShadowLoadEn  = DISABLE;
    initStruct->phase0ShadowLoadSel = 0;
    initStruct->syncIn0             = 0;
    initStruct->syncIn1             = 0;
}

/**
 * @brief initialize time base including period\counting mode\ synchronization signal\ phase etc
 *
 * @param SRPWMx select the specified srpwm
 * @param init the pointer to the srpwm init structure
 *      - periodShadowLoadSel - phase0ShadowLoadSel
 *       - SRPWM_SYNCEVTLOAD1_ZERO_EVT
 *       - SRPWM_SYNCEVTLOAD1_PERIOD_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS0
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS1
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS2
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS3
 *       - SRPWM_SYNCEVTLOAD1_SYNC0
 *       - SRPWM_SYNCEVTLOAD1_SYNC1
 *       - SRPWM_SYNCEVTLOAD1_BURST_OVER
 *       - SRPWM_SYNCEVTLOAD1_SORTWARE_UPDATE
 *      - syncIn0
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS0
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS1
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS2
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS3
 *       - SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN0
 *       - SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN1
 *       - SRPWM_TBCOUNTER_SYNCEVT_SOFTWARE_UPDATE_EVT
 *      - syncIn1
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS0
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS1
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS2
 *       - SRPWM_TBCOUNTER_SYNCEVT_FPP_FAULT_POS3
 *       - SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN0
 *       - SRPWM_TBCOUNTER_SYNCEVT_SYNC_IN1
 *       - SRPWM_TBCOUNTER_SYNCEVT_SOFTWARE_UPDATE_EVT
 */
void SRPWM_initTB(SRPWM_Type *SRPWMx, SRPWM_TBInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SYNCEVTLOAD1(init->periodShadowLoadSel));
    assert_param(IS_SRPWM_SYNCEVTLOAD1(init->phase0ShadowLoadSel));
    assert_param(IS_SRPWM_TBCOUNTER_SYNCEVT(init->syncIn0));
    assert_param(IS_SRPWM_TBCOUNTER_SYNCEVT(init->syncIn1));
    assert_param(IS_SRPWM_PERIOD(init->period));
    assert_param(IS_SRPWM_HR(init->periodHR));
    /* config period */
    WRITE_REG(SRPWMx->TB_PRD, (uint32_t)(init->period << SRPWM_LR_POS) |
              init->periodHR);

    MODIFY_REG(SRPWMx->TB_CTL,
               SRPWM0_TB_CTL_TB_MD_Msk |         /* config the countMode(up-down or up) */
               SRPWM0_TB_CTL_TB_SYNC_EN_Msk |    /* configure tb counter synchronization to enable or disable it */
               SRPWM0_TB_CTL_TB_1DIR_Msk |       /* config the count direction when the sync 0 or 1 is coming */
               SRPWM0_TB_CTL_TB_0DIR_Msk,
               (uint32_t)init->countMode << SRPWM0_TB_CTL_TB_MD_Pos |
               (uint32_t)init->waitSync0TimerEn << SRPWM0_TB_CTL_TB_SYNC_EN_Pos |
               (uint32_t)init->sync1CountDir << SRPWM0_TB_CTL_TB_1DIR_Pos |
               (uint32_t)init->sync0CountDir << SRPWM0_TB_CTL_TB_0DIR_Pos);
    /* config the sync(TB period phase sync signal select) and whether ENABLE*/
    MODIFY_REG(SRPWMx->TB_SYNC,
               SRPWM0_TB_SYNC_TB_SYNC0_MSEL_Msk |
               SRPWM0_TB_SYNC_TB_SYNC1_MSEL_Msk,
               (uint32_t)init->syncIn0 << SRPWM0_TB_SYNC_TB_SYNC0_MSEL_Pos |
               (uint32_t)init->syncIn1 << SRPWM0_TB_SYNC_TB_SYNC1_MSEL_Pos);

    /* configure the cycle to load the synchronization signal and enable or disable cycle load synchronization
     * function*/
    MODIFY_REG(SRPWMx->TB_PRD_LDSYNC,
               SRPWM0_TB_PRD_LDSYNC_TB_PRD_LDSYNC_MSEL_Msk |
               SRPWM0_TB_PRD_LDSYNC_TB_PRD_LDSYNC_EN_Msk,
               (uint32_t)init->periodShadowLoadSel << SRPWM0_TB_PRD_LDSYNC_TB_PRD_LDSYNC_MSEL_Pos |
               (uint32_t)init->periodShadowLoadEn << SRPWM0_TB_PRD_LDSYNC_TB_PRD_LDSYNC_EN_Pos);
    /* configure phase synchronous loading */
    MODIFY_REG(SRPWMx->TB_PH_LDSYNC,
               SRPWM0_TB_PH_LDSYNC_TB_PH_LDSYNC_MSEL_Msk |
               SRPWM0_TB_PH_LDSYNC_TB_PH_LDSYNC_EN_Msk,
               (uint32_t)init->phase0ShadowLoadSel << SRPWM0_TB_PH_LDSYNC_TB_PH_LDSYNC_MSEL_Pos |
               (uint32_t)init->phase0ShadowLoadEn << SRPWM0_TB_PH_LDSYNC_TB_PH_LDSYNC_EN_Pos);
    /* config the phase when sync0 or sync1 is coming */
    WRITE_REG(SRPWMx->TB_0PHASE, init->phase0);
    WRITE_REG(SRPWMx->TB_1PHASE, init->phase1);
}

/**
 * @brief CMPStruct Init
 *
 * @param initStruct pointer to the srpwm cmp init structure
 */
void SRPWM_initCMPStruct(SRPWM_CMPInitTypeDef *initStruct)
{
    initStruct->cmpEventOutSingleEn = DISABLE;
    initStruct->cmpEventOutMode     = SRPWM_CMP_EVTOUT_MODE_EQUAL_EVENT;
    initStruct->cmpA              = 0;
    initStruct->a.risingHR        = 0;
    initStruct->cmpB              = 0;
    initStruct->a.fallingHR       = 0;
    initStruct->cmpC              = 0;
    initStruct->b.risingHR        = 0;
    initStruct->cmpD              = 0;
    initStruct->b.fallingHR       = 0;
    initStruct->scmpA             = 0;
    initStruct->scmpB             = 0;
    initStruct->scmpC             = 0;
    initStruct->scmpD             = 0;
    initStruct->cmpShadowLoadEn   = DISABLE;
    initStruct->cmpShadowLoadSel  = 0;
    initStruct->scmpShadowLoadEn  = DISABLE;
    initStruct->scmpShadowLoadSel = 0;
}

/**
 * @brief initialize the cmp includes 4 cmp 4 scmp and synchronous loading of master slave
 *
 * @param SRPWMx select the specified srpwm
 * @param init pointer to the srpwm cmp init structure
 *      - cmpShadowLoadSel - scmpShadowLoadSel
 *       - SRPWM_SYNCEVTLOAD1_ZERO_EVT
 *       - SRPWM_SYNCEVTLOAD1_PERIOD_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS0
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS1
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS2
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS3
 *       - SRPWM_SYNCEVTLOAD1_SYNC0
 *       - SRPWM_SYNCEVTLOAD1_SYNC1
 *       - SRPWM_SYNCEVTLOAD1_BURST_OVER
 *       - SRPWM_SYNCEVTLOAD1_SORTWARE_UPDATE
 */
void SRPWM_initCMP(SRPWM_Type *SRPWMx, SRPWM_CMPInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SYNCEVTLOAD1(init->cmpShadowLoadSel));
    assert_param(IS_SRPWM_SYNCEVTLOAD1(init->scmpShadowLoadSel));
    assert_param(IS_SRPWM_CMP(init->cmpA));
    assert_param(IS_SRPWM_CMP(init->cmpB));
    assert_param(IS_SRPWM_CMP(init->cmpC));
    assert_param(IS_SRPWM_CMP(init->cmpD));
    assert_param(IS_SRPWM_HR(init->a.risingHR));
    assert_param(IS_SRPWM_HR(init->a.fallingHR));
    assert_param(IS_SRPWM_HR(init->b.risingHR));
    assert_param(IS_SRPWM_HR(init->b.fallingHR));

    WRITE_REG(SRPWMx->CMP_CTL, (uint32_t)init->cmpEventOutSingleEn << SRPWM0_CMP_CTL_CMP_ONETIME_Pos |
              (uint32_t)init->cmpEventOutMode << SRPWM0_CMP_CTL_CMP_MD_Pos);
    /* config the cmp(A,B,C,D),scmp(A,B,C,D),sync load evt and whether sync enable*/
    WRITE_REG(SRPWMx->CMP_CMPA, (uint32_t)init->cmpA << 6 |
              init->a.risingHR);
    WRITE_REG(SRPWMx->CMP_CMPB, (uint32_t)init->cmpB << 6 |
              init->a.fallingHR);
    WRITE_REG(SRPWMx->CMP_CMPC, (uint32_t)init->cmpC << 6 |
              init->b.risingHR);
    WRITE_REG(SRPWMx->CMP_CMPD, (uint32_t)init->cmpD << 6 |
              init->b.fallingHR);
    WRITE_REG(SRPWMx->CMP_SCMPA, init->scmpA);
    WRITE_REG(SRPWMx->CMP_SCMPB, init->scmpB);
    WRITE_REG(SRPWMx->CMP_SCMPC, init->scmpC);
    WRITE_REG(SRPWMx->CMP_SCMPD, init->scmpD);
    /* configure cmp event synchronous loading */
    MODIFY_REG(SRPWMx->CPM_LDSYNC,
               SRPWM0_CPM_LDSYNC_CMP_LDSYNC_MSEL_Msk |
               SRPWM0_CPM_LDSYNC_CMP_LDSYNC_EN_Msk,
               (uint32_t)init->cmpShadowLoadSel << SRPWM0_CPM_LDSYNC_CMP_LDSYNC_MSEL_Pos |
               (uint32_t)init->cmpShadowLoadEn << SRPWM0_CPM_LDSYNC_CMP_LDSYNC_EN_Pos);
    /* configure scmp event synchronization loading */
    MODIFY_REG(SRPWMx->SCPM_LDSYNC,
               SRPWM0_SCPM_LDSYNC_SCMP_LDSYNC_MSEL_Msk |
               SRPWM0_SCPM_LDSYNC_SCMP_LDSYNC_EN_Msk,
               (uint32_t)init->scmpShadowLoadSel << SRPWM0_SCPM_LDSYNC_SCMP_LDSYNC_MSEL_Pos |
               (uint32_t)init->scmpShadowLoadEn << SRPWM0_SCPM_LDSYNC_SCMP_LDSYNC_EN_Pos);
}

/**
 * @brief Enables the DMA request for the specified SRPWM channel(s).
 *
 * @param dmaChannel The DMA channel to be enabled. ref to @ref SRPWM_DMAChannel.
 * @param channel the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @note This function modifies the DMA selection register and enables the specified DMA channel.
 *
 * @return void
 */
void SRPWMCOM_enableDMA(SRPWM_DMAChannel dmaChannel, uint16_t channel)
{
    assert_param(IS_SRPWM_CHANNEL(channel));

//    MODIFY_REG(SRPWMCOM->MEPWM_DMA_SEL,
//               SRPWMCOM_MEPWM_DMA_SEL_MEPWM_DMA_REQ0_SEL_Msk << (uint32_t)(dmaChannel * 4),
//               (uint32_t)POSITION_VAL(channel) << (uint32_t)(dmaChannel * 4));

    SET_BIT(SRPWMCOM->MEPWM_DMA_EN, BIT_MASK(dmaChannel));
}

/**
 * @brief DBStruct Init
 *
 * @param initStruct pointer to the srpwm db init structure
 */
void SRPWM_initDBStruct(SRPWM_DBInitTypeDef *initStruct)
{
    initStruct->shadowLoadEn           = DISABLE;
    initStruct->shadowLoadSel          = 0;
    initStruct->a.selComplementChannel = DISABLE;
    initStruct->a.selRisingDelay       = DISABLE;
    initStruct->a.selFallingDelay      = DISABLE;
    initStruct->a.selOutputState       = SRPWM_DB_OUTPUT_STATE_NONE;
    initStruct->a.risingDelay          = 0;
    initStruct->a.risingDelayHR        = 0;
    initStruct->a.fallingDelay         = 0;
    initStruct->a.fallingDelayHR       = 0;
    initStruct->b.selComplementChannel = DISABLE;
    initStruct->b.selRisingDelay       = DISABLE;
    initStruct->b.selFallingDelay      = DISABLE;
    initStruct->b.selOutputState       = SRPWM_DB_OUTPUT_STATE_NONE;
    initStruct->b.risingDelay          = 0;
    initStruct->b.risingDelayHR        = 0;
    initStruct->b.fallingDelay         = 0;
    initStruct->b.fallingDelayHR       = 0;
}

/**
 * @brief initialize the dead zone
 *
 * @param SRPWMx select the specified srpwm
 * @param init pointer to the srpwm db init structure
 *      - shadowLoadSel
 *       - SRPWM_SYNCEVTLOAD2_ZERO_EVT
 *       - SRPWM_SYNCEVTLOAD2_PERIOD_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPC_UP_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPD_UP_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPC_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPD_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS0
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS1
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS2
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS3
 *       - SRPWM_SYNCEVTLOAD2_SYNC0
 *       - SRPWM_SYNCEVTLOAD2_SYNC1
 *       - SRPWM_SYNCEVTLOAD2_BURST_OVER
 *       - SRPWM_SYNCEVTLOAD2_SORTWARE_UPDATE
 */
void SRPWM_initDB(SRPWM_Type *SRPWMx, SRPWM_DBInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SYNCEVTLOAD2(init->shadowLoadSel));
    assert_param(IS_SRPWM_DEADTIME(init->a.fallingDelay));
    assert_param(IS_SRPWM_HR(init->a.fallingDelayHR));
    assert_param(IS_SRPWM_DEADTIME(init->a.risingDelay));
    assert_param(IS_SRPWM_HR(init->a.risingDelayHR));
    assert_param(IS_SRPWM_DEADTIME(init->b.fallingDelay));
    assert_param(IS_SRPWM_HR(init->b.fallingDelayHR));
    assert_param(IS_SRPWM_DEADTIME(init->b.risingDelay));
    assert_param(IS_SRPWM_HR(init->b.risingDelayHR));
    /* config the polarity */
    MODIFY_REG(SRPWMx->DB_SEL, SRPWM0_DB_SEL_DB_S3B_Msk |
               SRPWM0_DB_SEL_DB_S2B_Msk |
               SRPWM0_DB_SEL_DB_S1B_Msk |
               SRPWM0_DB_SEL_DB_S0B_Msk |
               SRPWM0_DB_SEL_DB_S3A_Msk |
               SRPWM0_DB_SEL_DB_S2A_Msk |
               SRPWM0_DB_SEL_DB_S1A_Msk |
               SRPWM0_DB_SEL_DB_S0A_Msk,
               (uint32_t)init->b.selOutputState << SRPWM0_DB_SEL_DB_S3B_Pos |
               (uint32_t)init->b.selFallingDelay << SRPWM0_DB_SEL_DB_S2B_Pos |
               (uint32_t)init->b.selRisingDelay << SRPWM0_DB_SEL_DB_S1B_Pos |
               (uint32_t)init->b.selComplementChannel << SRPWM0_DB_SEL_DB_S0B_Pos |
               (uint32_t)init->a.selOutputState << SRPWM0_DB_SEL_DB_S3A_Pos |
               (uint32_t)init->a.selFallingDelay << SRPWM0_DB_SEL_DB_S2A_Pos |
               (uint32_t)init->a.selRisingDelay << SRPWM0_DB_SEL_DB_S1A_Pos |
               (uint32_t)init->a.selComplementChannel << SRPWM0_DB_SEL_DB_S0A_Pos);
    /* config the deadtime */
    WRITE_REG(SRPWMx->DB_APOS_DLY, (uint32_t)init->a.risingDelay << 6 |
              init->a.risingDelayHR);
    WRITE_REG(SRPWMx->DB_ANEG_DLY, (uint32_t)init->a.fallingDelay << 6 |
              init->a.fallingDelayHR);
    WRITE_REG(SRPWMx->DB_BPOS_DLY, (uint32_t)init->b.risingDelay << 6 |
              init->b.risingDelayHR);
    WRITE_REG(SRPWMx->DB_BNEG_DLY, (uint32_t)init->b.fallingDelay << 6 |
              init->b.fallingDelayHR);
    /* config the sync */
    MODIFY_REG(SRPWMx->DB_LDSYNC,
               SRPWM0_DB_LDSYNC_DB_LDYSNC_MSEL_Msk |
               SRPWM0_DB_LDSYNC_DB_LDSYNC_EN_Msk,
               (uint32_t)init->shadowLoadSel << SRPWM0_DB_LDSYNC_DB_LDYSNC_MSEL_Pos |
               (uint32_t)init->shadowLoadEn << SRPWM0_DB_LDSYNC_DB_LDSYNC_EN_Pos);
}

/**
 * @brief set the period value of standard accuracy
 *
 * @param SRPWMx select the specified srpwm
 * @param periodCount the standard precision of the period value
 *               range: 0x0 ~ 0x3FFFFF
 */
void SRPWM_setTimeBasePeriod(SRPWM_Type *SRPWMx, uint32_t periodCount)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_PERIOD(periodCount));

    MODIFY_REG(SRPWMx->TB_PRD, SRPWM_LR_MSK, (uint32_t)periodCount << SRPWM_LR_POS);
}

/**
 * @brief get the period value of standard accuracy
 *
 * @param SRPWMx select the specified srpwm
 * @return * uint32_t The period count value.
 */
uint32_t SRPWM_getTimeBasePeriod(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    return((READ_REG(SRPWMx->TB_PRD) & SRPWM_LR_MSK) >> SRPWM_LR_POS);
}

/**
 * @brief set the counter compare value of standard accuracy
 *
 * @param SRPWMx select the specified srpwm
 * @param compModule the counter compare module
 * @param compCount the standard precision of the comparison value
 * @return * void
 */
void SRPWM_setCounterCompareValue(SRPWM_Type *SRPWMx, SRPWM_CounterCompareModule compModule, uint32_t compCount)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_CMP(compCount));

    switch (compModule)
    {
    case SRPWM_COUNTER_COMPARE_A:
        MODIFY_REG(SRPWMx->CMP_CMPA, SRPWM_LR_MSK, (uint32_t)compCount << SRPWM_LR_POS);
        break;

    case SRPWM_COUNTER_COMPARE_B:
        MODIFY_REG(SRPWMx->CMP_CMPB, SRPWM_LR_MSK, (uint32_t)compCount << SRPWM_LR_POS);
        break;

    case SRPWM_COUNTER_COMPARE_C:
        MODIFY_REG(SRPWMx->CMP_CMPC, SRPWM_LR_MSK, (uint32_t)compCount << SRPWM_LR_POS);
        break;

    case SRPWM_COUNTER_COMPARE_D:
        MODIFY_REG(SRPWMx->CMP_CMPD, SRPWM_LR_MSK, (uint32_t)compCount << SRPWM_LR_POS);
        break;

    case SRPWM_COUNTER_COMPARE_A_SLAVE:
        WRITE_REG(SRPWMx->CMP_SCMPA, (uint32_t)compCount);
        break;

    case SRPWM_COUNTER_COMPARE_B_SLAVE:
        WRITE_REG(SRPWMx->CMP_SCMPB, (uint32_t)compCount);
        break;

    case SRPWM_COUNTER_COMPARE_C_SLAVE:
        WRITE_REG(SRPWMx->CMP_SCMPC, (uint32_t)compCount);
        break;

    case SRPWM_COUNTER_COMPARE_D_SLAVE:
        WRITE_REG(SRPWMx->CMP_SCMPD, (uint32_t)compCount);
        break;
    }
}

/**
 * @brief set the phase shift value
 *
 * @param SRPWMx select the specified srpwm
 * @param phaseType the phase type
 * @param phaseCount the standard precision of the phase value
 * @return * void
 */
void SRPWM_setPhaseShift(SRPWM_Type *SRPWMx, SRPWM_PhaseType phaseType, uint32_t phaseCount)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_PHASE(phaseCount));

    if (phaseType == SRPWM_PHASE0)
    {
        WRITE_REG(SRPWMx->TB_0PHASE, phaseCount);
    }
    else
    {
        WRITE_REG(SRPWMx->TB_1PHASE, phaseCount);
    }
}

/**
 * @brief set the dead time of the rising edge and falling edge of the ab road
 *
 * @param SRPWMx select the specified srpwm
 * @param edge select the rising or falling edge of the dead delay
 * @param deadTime standard accuracy for deadband delay
 */
void SRPWM_setDB(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint16_t deadTime)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_DEADTIME(deadTime));

    switch (edge)
    {
    case SRPWM_EDGE_POS_A:
        MODIFY_REG(SRPWMx->DB_APOS_DLY, SRPWM_DB_LR_MSK, (uint32_t)deadTime << SRPWM_LR_POS);
        break;

    case SRPWM_EDGE_NEG_A:
        MODIFY_REG(SRPWMx->DB_ANEG_DLY, SRPWM_DB_LR_MSK, (uint32_t)deadTime << SRPWM_LR_POS);
        break;

    case SRPWM_EDGE_POS_B:
        MODIFY_REG(SRPWMx->DB_BPOS_DLY, SRPWM_DB_LR_MSK, (uint32_t)deadTime << SRPWM_LR_POS);
        break;

    case SRPWM_EDGE_NEG_B:
        MODIFY_REG(SRPWMx->DB_BNEG_DLY, SRPWM_DB_LR_MSK, (uint32_t)deadTime << SRPWM_LR_POS);
        break;
    }
}

/**
 * @brief a software triggered forced action is performed on the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB specify either the a signal or the b signal
 */
void SRPWMCOM_forcePGSwSigOnePulse(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        SET_BIT(SRPWMCOM->AQ_OTSFT, (uint32_t)channelMask << SRPWMCOM_AQ_OTSFT_AQ_OTSFTA_Pos);
    }
    else
    {
//        SET_BIT(SRPWMCOM->AQ_OTSFT, (uint32_t)channelMask << SRPWMCOM_AQ_OTSFT_AQ_OTSFTB_Pos);
    }
}

/**
 * @brief continuously force trigger the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB the specified ab signal
 */
void SRPWMCOM_forcePGSwSigHighLevel(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        SET_BIT(SRPWMCOM->AQ_CSFT, (uint32_t)channelMask << SRPWMCOM_AQ_CSFT_AQ_CSFTA_Pos);
    }
    else
    {
//        SET_BIT(SRPWMCOM->AQ_CSFT, (uint32_t)channelMask << SRPWMCOM_AQ_CSFT_AQ_CSFTB_Pos);
    }
}

/**
 * @brief exit the continuous forced trigger action for the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB the specified ab signal
 */
void SRPWMCOM_forcePGSwSigLowLevel(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        CLEAR_BIT(SRPWMCOM->AQ_CSFT, (uint32_t)channelMask << SRPWMCOM_AQ_CSFT_AQ_CSFTA_Pos);
    }
    else
    {
//        CLEAR_BIT(SRPWMCOM->AQ_CSFT, (uint32_t)channelMask << SRPWMCOM_AQ_CSFT_AQ_CSFTB_Pos);
    }
}

/**
 * @brief PGStruct Init
 *
 * @param initStruct pointer to the srpwm pg init structure
 */
void SRPWM_initPGStruct(SRPWM_PGInitTypeDef *initStruct)
{
    initStruct->shadowLoadEn       = DISABLE;
    initStruct->shadowLoadSel      = 0;
    initStruct->priorityGap        = 0;
    initStruct->a.event            = SRPWM_PG_EVT_FPP_FAULT_POS0;
    initStruct->a.value            = SRPWM_PG_NONE;
    initStruct->a.swEndSigSyncEn   = DISABLE;
    initStruct->a.swStartSigSyncEn = DISABLE;
    initStruct->a.swEndSigSel      = 0;
    initStruct->a.swStartSigSel    = 0;
    initStruct->a.swDlyFalling     = 0;
    initStruct->a.swDlyRising      = 0;
    initStruct->b.event            = SRPWM_PG_EVT_FPP_FAULT_POS0;
    initStruct->b.value            = SRPWM_PG_NONE;
    initStruct->b.swEndSigSyncEn   = DISABLE;
    initStruct->b.swStartSigSyncEn = DISABLE;
    initStruct->b.swEndSigSel      = 0;
    initStruct->b.swStartSigSel    = 0;
    initStruct->b.swDlyFalling     = 0;
    initStruct->b.swDlyRising      = 0;
}

/**
 * @brief initialize the action matrix
 *
 * @param SRPWMx select the specified srpwm
 * @param init pointer to the srpwm pg init structure
 *      - shadowLoadSel
 *       - SRPWM_SYNCEVTLOAD2_ZERO_EVT
 *       - SRPWM_SYNCEVTLOAD2_PERIOD_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPC_UP_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPD_UP_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPC_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD2_SCMPD_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS0
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS1
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS2
 *       - SRPWM_SYNCEVTLOAD2_FPP_FAULT_POS3
 *       - SRPWM_SYNCEVTLOAD2_SYNC0
 *       - SRPWM_SYNCEVTLOAD2_SYNC1
 *       - SRPWM_SYNCEVTLOAD2_BURST_OVER
 *       - SRPWM_SYNCEVTLOAD2_SORTWARE_UPDATE
 *      - PWMA_PGSwEndSyncSel - PWMA_PGSwStartSyncSel - PWMB_PGSwEndSyncSel - PWMB_PGSwStartSyncSel
 *       - SRPWM_PG_SWSYNC_ZERO_EVT
 *       - SRPWM_PG_SWSYNC_PRD_EVT
 *       - SRPWM_PG_SWSYNC_SCMPA_UP_EVT
 *       - SRPWM_PG_SWSYNC_SCMPB_UP_EVT
 *       - SRPWM_PG_SWSYNC_SCMPA_DOWN_EVT
 *       - SRPWM_PG_SWSYNC_SCMPB_DOWN_EVT
 *       - SRPWM_PG_SWSYNC_BURST_PWMB_NEG
 *       - SRPWM_PG_SWSYNC_BURST_PWMB_POS
 *       - SRPWM_PG_SWSYNC_BURST_PWMA_NEG
 *       - SRPWM_PG_SWSYNC_BURST_PWMA_POS
 */
void SRPWM_initPG(SRPWM_Type *SRPWMx, SRPWM_PGInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SYNCEVTLOAD2(init->shadowLoadSel));
    assert_param(IS_SRPWM_AQ_SWSYNC(init->a.swEndSigSel));
    assert_param(IS_SRPWM_AQ_SWSYNC(init->a.swStartSigSel));
    assert_param(IS_SRPWM_AQ_SWSYNC(init->b.swEndSigSel));
    assert_param(IS_SRPWM_AQ_SWSYNC(init->b.swStartSigSel));
    assert_param(IS_SRPWM_AQ_PRIORITY_GAP(init->priorityGap));
    assert_param(IS_SRPWM_AQ_SW_DLY_FALLING_RISING(init->a.swDlyFalling));
    assert_param(IS_SRPWM_AQ_SW_DLY_FALLING_RISING(init->a.swDlyRising));
    assert_param(IS_SRPWM_AQ_SW_DLY_FALLING_RISING(init->b.swDlyFalling));
    assert_param(IS_SRPWM_AQ_SW_DLY_FALLING_RISING(init->b.swDlyRising));
    /* config the sync load */
    MODIFY_REG(SRPWMx->AQ_LDSYNC,
               SRPWM0_AQ_LDSYNC_AQ_CTL_LDSYNC_MSEL_Msk |
               SRPWM0_AQ_LDSYNC_AQ_CTL_LDSYNC_EN_Msk,
               (uint32_t)init->shadowLoadSel << SRPWM0_AQ_LDSYNC_AQ_CTL_LDSYNC_MSEL_Pos |
               (uint32_t)init->shadowLoadEn << SRPWM0_AQ_LDSYNC_AQ_CTL_LDSYNC_EN_Pos);
    /* configure the action matrix priority interval */
    MODIFY_REG(SRPWMx->AQ_CTL, SRPWM0_AQ_CTL_AQ_PRIOR_ITV_Msk,
               (uint32_t)init->priorityGap << SRPWM0_AQ_CTL_AQ_PRIOR_ITV_Pos);
    /* configure the action corresponding to the action event */
    if (init->a.event == SRPWM_PG_EVT_SW)
    {
        /* config the PG by software for force to init*/
        MODIFY_REG(SRPWMx->AQ_CTL_SFT,
                   SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTA_Msk,
                   (uint32_t)init->a.value << SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTA_Pos);
        MODIFY_REG(SRPWMx->AQ_SFT_SYNCA,
                   SRPWM0_AQ_SFT_SYNCA_AQ_SFTEND_SYNC_MSELA_Msk |
                   SRPWM0_AQ_SFT_SYNCA_AQ_SFTSTART_SYNC_MSELA_Msk,
                   (uint32_t)init->a.swEndSigSel << SRPWM0_AQ_SFT_SYNCA_AQ_SFTEND_SYNC_MSELA_Pos |
                   (uint32_t)init->a.swStartSigSel << SRPWM0_AQ_SFT_SYNCA_AQ_SFTSTART_SYNC_MSELA_Pos);
        MODIFY_REG(SRPWMx->AQ_CTL,
                   SRPWM0_AQ_CTL_AQ_SFTEND_MDA_Msk |
                   SRPWM0_AQ_CTL_AQ_SFTSTART_MDA_Msk,
                   (uint32_t)init->a.swEndSigSyncEn << SRPWM0_AQ_CTL_AQ_SFTEND_MDA_Pos |
                   (uint32_t)init->a.swStartSigSyncEn << SRPWM0_AQ_CTL_AQ_SFTSTART_MDA_Pos);
        /* configure the delay of the rising and falling edges of the A/B action by the action matrix software */
        MODIFY_REG(SRPWMx->AQ_CSFTA_DLY,
                   SRPWM0_AQ_CSFTA_DLY_AQ_CSFTA_NEG_DLY_Msk |
                   SRPWM0_AQ_CSFTA_DLY_AQ_CSFTA_POS_DLY_Msk,
                   (uint32_t)init->a.swDlyFalling << SRPWM0_AQ_CSFTA_DLY_AQ_CSFTA_NEG_DLY_Pos |
                   (uint32_t)init->a.swDlyRising << SRPWM0_AQ_CSFTA_DLY_AQ_CSFTA_POS_DLY_Pos);
    }
    else
    {
        /* config the PWMA PG */
        WRITE_REG(SRPWMx->AQ_CTLA[init->a.event], init->a.value);
    }
    if (init->b.event == SRPWM_PG_EVT_SW)
    {
        /* config the PG by software for force to init*/
        MODIFY_REG(SRPWMx->AQ_CTL_SFT,
                   SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTB_Msk,
                   (uint32_t)init->b.value << SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTB_Pos);
        MODIFY_REG(SRPWMx->AQ_SFT_SYNCB,
                   SRPWM0_AQ_SFT_SYNCB_AQ_SFTEND_SYNC_MSELB_Msk |
                   SRPWM0_AQ_SFT_SYNCB_AQ_SFTSTART_SYNC_MSELB_Msk,
                   (uint32_t)init->b.swEndSigSel << SRPWM0_AQ_SFT_SYNCB_AQ_SFTEND_SYNC_MSELB_Pos |
                   (uint32_t)init->b.swStartSigSel << SRPWM0_AQ_SFT_SYNCB_AQ_SFTSTART_SYNC_MSELB_Pos);
        MODIFY_REG(SRPWMx->AQ_CTL,
                   SRPWM0_AQ_CTL_AQ_SFTEND_MDB_Msk |
                   SRPWM0_AQ_CTL_AQ_SFTSTART_MDB_Msk,
                   (uint32_t)init->b.swEndSigSyncEn << SRPWM0_AQ_CTL_AQ_SFTEND_MDB_Pos |
                   (uint32_t)init->b.swStartSigSyncEn << SRPWM0_AQ_CTL_AQ_SFTSTART_MDB_Pos);
        /* configure the delay of the rising and falling edges of the A/B action by the action matrix software */
        MODIFY_REG(SRPWMx->AQ_CSFTB_DLY,
                   SRPWM0_AQ_CSFTB_DLY_AQ_CSFTB_NEG_DLY_Msk |
                   SRPWM0_AQ_CSFTB_DLY_AQ_CSFTB_POS_DLY_Msk,
                   (uint32_t)init->b.swDlyFalling << SRPWM0_AQ_CSFTB_DLY_AQ_CSFTB_NEG_DLY_Pos |
                   (uint32_t)init->b.swDlyRising << SRPWM0_AQ_CSFTB_DLY_AQ_CSFTB_POS_DLY_Pos);
    }
    else
    {
        /* config the PWMB PG */
        WRITE_REG(SRPWMx->AQ_CTLB[init->b.event], init->b.value);
    }
}

/**
 * @brief sets the action for the specified action event
 *
 * @param SRPWMx select the specified srpwm
 * @param pwmAB select the specified srpwm
 * @param event select the specified action event
 * @param value select the specified action value
 */
void SRPWM_setPG(SRPWM_Type *SRPWMx, SRPWM_AB pwmAB, SRPWM_PGEvt event, SRPWM_PGValue value)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (pwmAB != SRPWM_A)
    {
        if (event == SRPWM_PG_EVT_SW)
        {
            /* config the PG by software for force to init*/
            MODIFY_REG(SRPWMx->AQ_CTL_SFT,
                       SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTB_Msk,
                       (uint32_t)value << SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTB_Pos);
        }
        else
        {
            /* config the PWMB PG */
            WRITE_REG(SRPWMx->AQ_CTLB[event], value);
        }
    }
    else
    {
        if (event == SRPWM_PG_EVT_SW)
        {
            /* config the PG by software for force to init*/
            MODIFY_REG(SRPWMx->AQ_CTL_SFT,
                       SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTA_Msk,
                       (uint32_t)value << SRPWM0_AQ_CTL_SFT_AQ_CTL_SFTA_Pos);
        }
        else
        {
            /* config the PWMB PG */
            WRITE_REG(SRPWMx->AQ_CTLA[event], value);
        }
    }
}

/**
 * @brief enables the specified interrupt for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_enableInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    SET_BIT(SRPWMx->EPWM_INT_EN, (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_EN_EPWM_INT_EN_Pos);
}

/**
 * @brief Disable the specified interrupt for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_disableInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    CLEAR_BIT(SRPWMx->EPWM_INT_EN, (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_EN_EPWM_INT_EN_Pos);
}

/**
 * @brief enables the specified interrupt mask for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_setInterruptMask(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    SET_BIT(SRPWMx->EPWM_INT_MASK, (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_MASK_EPWM_INT_MASK_Pos);
}

/**
 * @brief Disable the specified interrupt mask for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_clearInterruptMask(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    CLEAR_BIT(SRPWMx->EPWM_INT_MASK, (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_MASK_EPWM_INT_MASK_Pos);
}

/**
 * @brief the software forces an interrupt
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_forceInterrupt(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    SET_BIT(SRPWMx->EPWM_INT_FORCE_IND,
            (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_FORCE_IND_EPWM_INT_FORCE_IND_Pos);
}

/**
 * @brief clear the interrupt flag
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 */
void SRPWM_clearInterruptStatus(SRPWM_Type *SRPWMx, uint16_t interruptFlagMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_IT(interruptFlagMask));

    SET_BIT(SRPWMx->EPWM_INT_CLR, (uint32_t)interruptFlagMask << SRPWM0_EPWM_INT_CLR_EPWM_INT_CLR_Pos);
}

/**
 * @brief gets the specified interrupt source mask state of the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 * @return ITStatus
 */
ITStatus SRPWM_getInterruptStatus(SRPWM_Type *SRPWMx, uint16_t interruptFlag)
{
    ITStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_GET_IT(interruptFlag));

    ret = DRV_IS_BIT_SET(SRPWMx->EPWM_INT_STATUS_RPT, interruptFlag) ? SET : RESET;

    return ret;
}

/**
 * @brief gets the specified interrupt source raw state of the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param interruptFlagMask the specified interrupt source
 *      - SRPWM_IT_EVT: incident interruption
 *      - SRPWM_IT_BURST_OVER: burst ends
 *      - SRPWM_IT_FAULT_REAL0: real time fault0
 *      - SRPWM_IT_FAULT_REAL1: real time fault1
 *      - SRPWM_IT_FAULT_REAL2: real time fault2
 *      - SRPWM_IT_FAULT_REAL3: real time fault3
 *      - SRPWM_IT_FAULT_REAL4: real time fault4
 *      - SRPWM_IT_FAULT_REAL5: real time fault5
 *      - SRPWM_IT_FAULT_LATCH0: fault0 after latching
 *      - SRPWM_IT_FAULT_LATCH1: fault1 after latching
 *      - SRPWM_IT_FAULT_LATCH2: fault2 after latching
 *      - SRPWM_IT_FAULT_LATCH3: fault3 after latching
 *      - SRPWM_IT_FAULT_LATCH4: fault4 after latching
 *      - SRPWM_IT_FAULT_LATCH5: fault5 after latching
 * @return ITStatus
 */
ITStatus SRPWM_getInterruptStatusRaw(SRPWM_Type *SRPWMx, uint16_t interruptFlag)
{
    ITStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_GET_IT(interruptFlag));

    ret = DRV_IS_BIT_SET(SRPWMx->EPWM_INT_RAW_RPT, interruptFlag) ? SET : RESET;

    return ret;
}

/**
 * @brief enable specifies the synchronization signal that the module uses to generate the event interrupt request
 * signal
 *
 * @param SRPWMx select the specified srpwm
 * @param outEventMask you can select multiple interrupt events by masking
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_enableEvtInterrupt(SRPWM_Type *SRPWMx, uint32_t outEventMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(outEventMask));

    SET_BIT(SRPWMx->EPWM_EVTINT_MSEL, outEventMask);
}

/**
 * @brief disable specifies the synchronization signal that the module uses to generate the event interrupt request
 * signal
 *
 * @param SRPWMx
 * @param outEventMask you can select multiple interrupt events by masking
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_disableEvtInterrupt(SRPWM_Type *SRPWMx, uint32_t outEventMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(outEventMask));

    CLEAR_BIT(SRPWMx->EPWM_EVTINT_MSEL, outEventMask);
}

/**
 * @brief enable event interrupt crossover
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableEvtInterruptFreqDiv(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->EPWM_EVTINT_DIV, SRPWM0_EPWM_EVTINT_DIV_EPWM_EVTINT_DIV_EN_Msk);
}

/**
 * @brief disable event interrupt crossover
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableEvtInterruptFreqDiv(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_BIT(SRPWMx->EPWM_EVTINT_DIV, SRPWM0_EPWM_EVTINT_DIV_EPWM_EVTINT_DIV_EN_Msk);
}

/**
 * @brief select the crossover factor for event interrupts
 *
 * @param SRPWMx select the specified srpwm
 * @param div the frequency divider of the event interrupt signal
 */
void SRPWM_setEvtInterruptFreqDiv(SRPWM_Type *SRPWMx, uint8_t div)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->EPWM_EVTINT_DIV, SRPWM0_EPWM_EVTINT_DIV_EPWM_EVTINT_DIV_Msk, div);
}

/**
 * @brief enable event interrupt multiplier
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableEvtInterruptFreqMulti(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->EPWM_EVTINT_MULTI, SRPWM0_EPWM_EVTINT_MULTI_EPWM_EVTINT_MULTI_EN_Msk);
}

/**
 * @brief disable event interrupt multiplier
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableEvtInterruptFreqMulti(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_BIT(SRPWMx->EPWM_EVTINT_MULTI, SRPWM0_EPWM_EVTINT_MULTI_EPWM_EVTINT_MULTI_EN_Msk);
}

/**
 * @brief select the crossover factor for event interrupts
 *
 * @param SRPWMx select the specified srpwm
 * @param multi the frequency multiple of the event interrupt signal
 */
void SRPWM_setEvtInterruptFreqMulti(SRPWM_Type *SRPWMx, uint16_t multi)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->EPWM_EVTINT_MULTI, SRPWM0_EPWM_EVTINT_MULTI_EPWM_EVTINT_MULTI_Msk, multi);
}

/**
 * @brief BurstStruct Init
 *
 * @param initStruct pointer to a SRPWM_BurstInitTypeDef structure
 */
void SRPWM_initBurstStruct(SRPWM_BurstInitTypeDef *initStruct)
{
    initStruct->m             = 0;
    initStruct->n             = 0;
    initStruct->burstEn       = DISABLE;
    initStruct->mode          = SRPWM_BURST_N_WAVE_IN_BACK;
    initStruct->startSync     = 0;
    initStruct->shadowLoadSel = 0;
    initStruct->shadowLoadEn  = DISABLE;
}

/**
 * @brief initialize the burst function
 *
 * @param SRPWMx select the specified srpwm
 * @param init pointer to a SRPWM_BurstInitTypeDef structure
 *      - shadowLoadSel
 *       - SRPWM_SYNCEVTLOAD1_ZERO_EVT
 *       - SRPWM_SYNCEVTLOAD1_PERIOD_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_UP_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPA_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_SCMPB_DOWN_EVT
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS0
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS1
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS2
 *       - SRPWM_SYNCEVTLOAD1_FPP_FAULT_POS3
 *       - SRPWM_SYNCEVTLOAD1_SYNC0
 *       - SRPWM_SYNCEVTLOAD1_SYNC1
 *       - SRPWM_SYNCEVTLOAD1_BURST_OVER
 *       - SRPWM_SYNCEVTLOAD1_SORTWARE_UPDATE
 *      - startSync
 *       - SRPWM_BURST_START_SYNC_ZERO_EVT
 *       - SRPWM_BURST_START_SYNC_PRD_EVT
 *       - SRPWM_BURST_START_SYNC_SCMPA_UP_EVT
 *       - SRPWM_BURST_START_SYNC_SCMPB_UP_EVT
 *       - SRPWM_BURST_START_SYNC_SCMPA_DOWN_EVT
 *       - SRPWM_BURST_START_SYNC_SCMPB_DOWN_EVT
 */
void SRPWM_initBurst(SRPWM_Type *SRPWMx, SRPWM_BurstInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SYNCEVTLOAD2(init->shadowLoadSel));
    assert_param(IS_SRPWM_BURST_START_SYNC(init->startSync));
    /* configure M\N */
    MODIFY_REG(SRPWMx->BURST_MN,
               SRPWM0_BURST_MN_BURST_M_Msk |
               SRPWM0_BURST_MN_BURST_N_Msk,
               (uint32_t)init->m << SRPWM0_BURST_MN_BURST_M_Pos |
               (uint32_t)init->n << SRPWM0_BURST_MN_BURST_N_Pos);
    /* configure the burst start sync signal */
    WRITE_REG(SRPWMx->BURST_SYNC_SEL, init->startSync);
    /* configure burst synchronous loading */
    MODIFY_REG(SRPWMx->BURST_LDSYNC,
               SRPWM0_BURST_LDSYNC_BURST_LDSYNC_EN_Msk |
               SRPWM0_BURST_LDSYNC_BURST_LDYSNC_MSEL_Msk,
               (uint32_t)init->shadowLoadSel << SRPWM0_BURST_LDSYNC_BURST_LDYSNC_MSEL_Pos |
               (uint32_t)init->shadowLoadEn << SRPWM0_BURST_LDSYNC_BURST_LDSYNC_EN_Pos);
    /* configure the burst wave mode */
    MODIFY_REG(SRPWMx->BURST_CRL,
               SRPWM0_BURST_CRL_BURST_MD_Msk |
               SRPWM0_BURST_CRL_BURST_EN_Msk,
               (uint32_t)init->mode << SRPWM0_BURST_CRL_BURST_MD_Pos |
               (uint32_t)init->burstEn << SRPWM0_BURST_CRL_BURST_EN_Pos);
}

/**
 * @brief set the m value of the burst function
 *
 * @param SRPWMx select the specified srpwm
 * @param m the m value
 */
void SRPWM_setBurstM(SRPWM_Type *SRPWMx, uint8_t m)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->BURST_MN,
               SRPWM0_BURST_MN_BURST_M_Msk,
               (uint32_t)m << SRPWM0_BURST_MN_BURST_M_Pos);
}

/**
 * @brief set the n value of the burst function
 *
 * @param SRPWMx select the specified srpwm
 * @param n the n value
 */
void SRPWM_setBurstN(SRPWM_Type *SRPWMx, uint8_t n)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->BURST_MN,
               SRPWM0_BURST_MN_BURST_N_Msk,
               (uint32_t)n << SRPWM0_BURST_MN_BURST_N_Pos);
}

/**
 * @brief FPPStruct Init
 *
 * @param initStruct pointer to a SRPWM_FPPInitTypeDef structure
 */
void SRPWM_initFPPStruct(SRPWM_FPPInitTypeDef *initStruct)
{
    initStruct->faultSigGroupMask = 0;
    initStruct->countFaultEn      = DISABLE;
    initStruct->latchFaultEn      = DISABLE;
    initStruct->faultMode         = SRPWM_FPP_FAULT_MODE_NORMAL;
    initStruct->blkEndSigSel      = 0;
    initStruct->blkStartSigSel    = 0;
    initStruct->blkEn             = DISABLE;
    initStruct->blkMode           = SRPWM_FPP_BLK_MODE_NONE;
    initStruct->faultSigEgdeSel   = SRPWM_FPP_FAULT_SIG_EGDE_SEL_DIRECT;
    initStruct->blkEndDly         = 0;
    initStruct->blkStartDly       = 0;
    initStruct->filterEn          = DISABLE;
    initStruct->filterLen         = 0;
    initStruct->countEn           = DISABLE;
    initStruct->countSigSel       = SRPWM_FPP_COUNT_SIG_FILTER_BEFORE;
    initStruct->countThreshold    = 0;
    initStruct->countMode         = 0;
    initStruct->countWindow       = 0;
    initStruct->countPeriod       = 0;
}

/**
 * @brief FPP initialization
 *
 * @param SRPWMx select the specified srpwm
 * @param init pointer to a SRPWM_FPPInitTypeDef structure
 *      - blkEndSigSel - blkStartSigSel
 *       - SRPWM_ALLEVT_ZERO_EVT
 *       - SRPWM_ALLEVT_PRD_EVT
 *       - SRPWM_ALLEVT_SCMPA_UP_EVT
 *       - SRPWM_ALLEVT_SCMPB_UP_EVT
 *       - SRPWM_ALLEVT_SCMPC_UP_EVT
 *       - SRPWM_ALLEVT_SCMPD_UP_EVT
 *       - SRPWM_ALLEVT_SCMPA_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPB_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPC_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPD_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPA_UP_EVT
 *       - SRPWM_ALLEVT_CMPB_UP_EVT
 *       - SRPWM_ALLEVT_CMPC_UP_EVT
 *       - SRPWM_ALLEVT_CMPD_UP_EVT
 *       - SRPWM_ALLEVT_CMPA_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPB_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPC_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPD_DOWN_EVT
 *       - SRPWM_ALLEVT_FPP_FAULT_POS0
 *       - SRPWM_ALLEVT_FPP_FAULT_POS1
 *       - SRPWM_ALLEVT_FPP_FAULT_POS2
 *       - SRPWM_ALLEVT_FPP_FAULT_POS3
 *       - SRPWM_ALLEVT_SYNC0
 *       - SRPWM_ALLEVT_SYNC1
 *       - SRPWM_ALLEVT_BURST_OVER
 *       - SRPWM_ALLEVT_B_NEG
 *       - SRPWM_ALLEVT_B_POS
 *       - SRPWM_ALLEVT_A_NEG
 *       - SRPWM_ALLEVT_A_POS
 *       - SRPWM_ALLEVT_SW_EVT
 *      - faultSigGroupMask
 *       - SRPWM_FPP_FAULT_SIG_GRP0
 *       - SRPWM_FPP_FAULT_SIG_GRP1
 *       - SRPWM_FPP_FAULT_SIG_GRP2
 *       - SRPWM_FPP_FAULT_SIG_GRP3
 *       - SRPWM_FPP_FAULT_SIG_GRP4
 *       - SRPWM_FPP_FAULT_SIG_GRP5
 *
 */
void SRPWM_initFPP(SRPWM_Type *SRPWMx, SRPWM_FPPInitTypeDef *init)
{
    uint8_t pos = 0, fppFaultSigNum = 6;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_FPP_FAULT_SIG(init->faultSigGroupMask));
    assert_param(IS_SRPWM_ALLEVT(init->blkEndSigSel));
    assert_param(IS_SRPWM_ALLEVT(init->blkStartSigSel));
    assert_param(IS_SRPWM_FPP_FILTER_LEN(init->filterLen));

    for (pos = 0; pos < fppFaultSigNum; pos++)
    {
        if (DRV_IS_BIT_SET(init->faultSigGroupMask, BIT_MASK(pos)))
        {
            MODIFY_REG(SRPWMx->FPP[pos].FPP_CTL,
                       SRPWM0_FPP_FPP_CTL_FPP_FPT_COUNT_MSK_Msk | /* enables or enables masking of latches and countsm
                                                                  */
                       SRPWM0_FPP_FPP_CTL_FPP_FPT_LATCH_MSK_Msk |
                       SRPWM0_FPP_FPP_CTL_FPP_FPT_MD_Msk |        /* configure the anomaly mode */
                       SRPWM0_FPP_FPP_CTL_FPP_BLK_END_SEL_Msk |   /* blanking time end and start signal selection */
                       SRPWM0_FPP_FPP_CTL_FPP_BLK_START_SEL_Msk |
                       SRPWM0_FPP_FPP_CTL_FPP_BLK_DLY_EN_Msk |    /* enable or disable blanking signal delay function */
                       SRPWM0_FPP_FPP_CTL_FPP_BLK_MD_Msk |        /* configure blanking mode */
                       SRPWM0_FPP_FPP_CTL_FPP_EDGE_SEL_Msk,       /* configure the exception signal along the selection
                                                                   */
                       (uint32_t)init->countFaultEn << SRPWM0_FPP_FPP_CTL_FPP_FPT_COUNT_MSK_Pos |
                       (uint32_t)init->latchFaultEn << SRPWM0_FPP_FPP_CTL_FPP_FPT_LATCH_MSK_Pos |
                       (uint32_t)init->faultMode << SRPWM0_FPP_FPP_CTL_FPP_FPT_MD_Pos |
                       (uint32_t)(POSITION_VAL(
                                      init->blkEndSigSel) & 0x1F) << SRPWM0_FPP_FPP_CTL_FPP_BLK_END_SEL_Pos |
                       (uint32_t)(POSITION_VAL(
                                      init->blkStartSigSel) & 0x1F) << SRPWM0_FPP_FPP_CTL_FPP_BLK_START_SEL_Pos |
                       (uint32_t)init->blkEn << SRPWM0_FPP_FPP_CTL_FPP_BLK_DLY_EN_Pos |
                       (uint32_t)init->blkMode << SRPWM0_FPP_FPP_CTL_FPP_BLK_MD_Pos |
                       (uint32_t)init->faultSigEgdeSel << SRPWM0_FPP_FPP_CTL_FPP_EDGE_SEL_Pos);
            /* configure the blanking delay */
            MODIFY_REG(SRPWMx->FPP[pos].FPP_BLK_DLY, SRPWM0_FPP_FPP_BLK_DLY_FPP_BLK_START_DLY_Msk,
                       (uint32_t)init->blkStartDly << SRPWM0_FPP_FPP_BLK_DLY_FPP_BLK_START_DLY_Pos);
            MODIFY_REG(SRPWMx->FPP[pos].FPP_BLK_DLY, SRPWM0_FPP_FPP_BLK_DLY_FPP_BLK_END_DLY_Msk,
                       (uint32_t)init->blkEndDly << SRPWM0_FPP_FPP_BLK_DLY_FPP_BLK_END_DLY_Pos);
            /* configure filtering */
            MODIFY_REG(SRPWMx->FPP[pos].FPP_FLT, SRPWM0_FPP_FPP_FLT_FPP_FLT_LEN_Msk,
                       (uint32_t)init->filterLen << SRPWM0_FPP_FPP_FLT_FPP_FLT_LEN_Pos);
            SET_BIT(SRPWMx->FPP[pos].FPP_FLT,
                    (uint32_t)init->filterEn << SRPWM0_FPP_FPP_FLT_FPP_FLT_EN_Pos);
            /* configure the exception count feature */
            MODIFY_REG(SRPWMx->FPP[pos].FPP_CNT, SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_TH_Msk,
                       (uint32_t)init->countThreshold << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_TH_Pos);
            MODIFY_REG(SRPWMx->FPP[pos].FPP_CNT, SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_SEL_Msk,
                       (uint32_t)init->countSigSel << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_SEL_Pos);
            SET_BIT(SRPWMx->FPP[pos].FPP_CNT,
                    (uint32_t)init->countEn << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_EN_Pos);
            SET_BIT(SRPWMx->FPP[pos].FPP_CNT,
                    (uint32_t)init->countMode << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_MD_Pos);
            MODIFY_REG(SRPWMx->FPP[pos].FPP_CNT, SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_WINDOW_Msk,
                       (uint32_t)init->countWindow << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_WINDOW_Pos);
            MODIFY_REG(SRPWMx->FPP[pos].FPP_CNT, SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_PRD_Msk,
                       (uint32_t)init->countPeriod << SRPWM0_FPP_FPP_CNT_FPP_FPT_CNT_PRD_Pos);
        }
    }
}

/**
 * @brief clears the exception count of the specified fpp exception preprocessing signal 0 5 for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param faultSigGroup specify fpp signals 0~5
 *      - SRPWM_FPP_FAULT_SIG_GRP0
 *      - SRPWM_FPP_FAULT_SIG_GRP1
 *      - SRPWM_FPP_FAULT_SIG_GRP2
 *      - SRPWM_FPP_FAULT_SIG_GRP3
 *      - SRPWM_FPP_FAULT_SIG_GRP4
 *      - SRPWM_FPP_FAULT_SIG_GRP5
 */
void SRPWM_clearFPPFaultCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_GET_FPP_FAULT_SIG(faultSigGroup));

    SET_BIT(SRPWMx->FPP[POSITION_VAL(faultSigGroup)].FPP_CLR, SRPWM0_FPP_FPP_CLR_FPP_FPT_CNT_CLR_Msk);
}

/**
 * @brief clears the specified fpp exception of the specified module preprocesses the latch exception signal 0 5
 *
 * @param SRPWMx select the specified srpwm
 * @param faultSigGroup specify fpp signals 0~5
 *       - SRPWM_FPP_FAULT_SIG_GRP0
 *       - SRPWM_FPP_FAULT_SIG_GRP1
 *       - SRPWM_FPP_FAULT_SIG_GRP2
 *       - SRPWM_FPP_FAULT_SIG_GRP3
 *       - SRPWM_FPP_FAULT_SIG_GRP4
 *       - SRPWM_FPP_FAULT_SIG_GRP5
 */
void SRPWM_clearFPPLatchFault(SRPWM_Type *SRPWMx, uint8_t faultSigGroup)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_GET_FPP_FAULT_SIG(faultSigGroup));

    SET_BIT(SRPWMx->FPP[POSITION_VAL(faultSigGroup)].FPP_CLR, SRPWM0_FPP_FPP_CLR_FPP_FPT_LATCH_CLR_Msk);
}

/**
 * @brief clears the filter count of 0~5 for the specified fpp exception preprocessing for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param faultSigGroup specify fpp signals 0~5
 *      - SRPWM_FPP_FAULT_SIG_GRP0
 *      - SRPWM_FPP_FAULT_SIG_GRP1
 *      - SRPWM_FPP_FAULT_SIG_GRP2
 *      - SRPWM_FPP_FAULT_SIG_GRP3
 *      - SRPWM_FPP_FAULT_SIG_GRP4
 *      - SRPWM_FPP_FAULT_SIG_GRP5
 */
void SRPWM_clearFPPFilterCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_GET_FPP_FAULT_SIG(faultSigGroup));

    SET_BIT(SRPWMx->FPP[POSITION_VAL(faultSigGroup)].FPP_CLR, SRPWM0_FPP_FPP_CLR_FPP_FLT_CNT_CLR_Msk);
}

/**
 * @brief gets the exception of the specified latch and real time exception signal for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param faultSig specify fpp signals 0~5
 *      - SRPWM_FPP_FAULT_REAL0
 *      - SRPWM_FPP_FAULT_REAL1
 *      - SRPWM_FPP_FAULT_REAL2
 *      - SRPWM_FPP_FAULT_REAL3
 *      - SRPWM_FPP_FAULT_REAL4
 *      - SRPWM_FPP_FAULT_REAL5
 *      - SRPWM_FPP_FAULT_LATCH0
 *      - SRPWM_FPP_FAULT_LATCH1
 *      - SRPWM_FPP_FAULT_LATCH2
 *      - SRPWM_FPP_FAULT_LATCH3
 *      - SRPWM_FPP_FAULT_LATCH4
 *      - SRPWM_FPP_FAULT_LATCH5
 * @return FlagStatus
 */
FlagStatus SRPWM_getFPPFaultStatus(SRPWM_Type *SRPWMx, uint16_t faultSig)
{
    FlagStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_FPP_FAULT_REAL_LATCH(faultSig));

    ret = DRV_IS_BIT_SET(SRPWMx->FPP_FAULT_RPT, faultSig) ? SET :RESET;

    return ret;
}

/**
 * @brief obtain the exception count of the specified fpp exception preprocessing signal 0 5 for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param faultSigGroup specify fpp signals 0~5
 *          - SRPWM_FPP_FAULT_SIG_GRP0
 *          - SRPWM_FPP_FAULT_SIG_GRP1
 *          - SRPWM_FPP_FAULT_SIG_GRP2
 *          - SRPWM_FPP_FAULT_SIG_GRP3
 *          - SRPWM_FPP_FAULT_SIG_GRP4
 *          - SRPWM_FPP_FAULT_SIG_GRP5
 * @return uint16_t
 */
uint16_t SRPWM_getFPPFaultCnt(SRPWM_Type *SRPWMx, uint8_t faultSigGroup)
{
    uint16_t ret = 0;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_FPP_FAULT_SIG(faultSigGroup));

    ret = (uint16_t)READ_REG(SRPWMx->FPP_FAULT_CNT_RPT[POSITION_VAL(faultSigGroup)]);

    return ret;
}

/**
 * @brief initializes the SRPWM_ValleyInitTypeDef structure
 *
 * @param initStruct
 * @return * void
 */
void SRPWM_initValleyStruct(SRPWM_ValleyInitTypeDef *initStruct)
{
    initStruct->captureSrc     = SRPWM_VALLEY_CAPTURE_SRC_FAULT_REAL0;
    initStruct->edgeDetectMode = SRPWM_VALLEY_EDGE_DETECT_MODE_RISING;
    initStruct->triggerSrc     = SRPWM_VALLEY_TRIGGER_SW;
    initStruct->targetEdge     = SRPWM_VALLEY_TARGET_EDGE_NONE;
    initStruct->outChannelEn   = DISABLE;
    initStruct->startCountEdge = SRPWM_VALLEY_COUNT_EDGE_NONE;
    initStruct->stopCountEdge  = SRPWM_VALLEY_COUNT_EDGE_NONE;
    initStruct->delayMode      = SRPWM_VALLEY_DELAY_MODE_SW_DELAY;
    initStruct->swDelayValue   = 0;
    initStruct->delayEn        = DISABLE;
}

/**
 * @brief configures the specified srpwm valley
 *
 * @param SRPWMx select the specified srpwm
 * @param init
 * @return * void
 */
void SRPWM_initValley(SRPWM_Type *SRPWMx, SRPWM_ValleyInitTypeDef *init)
{
    MODIFY_REG(SRPWMx->VALLEY_SW_CTRL, SRPWM0_VALLEY_SW_CTRL_VSW_SRCSEL_Msk |       /* input source */
               SRPWM0_VALLEY_SW_CTRL_VSW_EDGE_MODE_Msk |                            /* along the detection mode */
               SRPWM0_VALLEY_SW_CTRL_VSW_TRGSEL_Msk |                               /* trigger source */
               SRPWM0_VALLEY_SW_CTRL_VSW_TARGET_EDGE_Msk |                          /* resonant output pulses */
               SRPWM0_VALLEY_SW_CTRL_VALLEY_OUT_EN_Msk |                            /* the valley output channel */
               SRPWM0_VALLEY_SW_CTRL_RSNTPL_DLY_EN_Msk,                             /* indicates the pulse delay
                                                                                     * function */
               (uint32_t)init->captureSrc << SRPWM0_VALLEY_SW_CTRL_VSW_SRCSEL_Pos |
               (uint32_t)init->edgeDetectMode << SRPWM0_VALLEY_SW_CTRL_VSW_EDGE_MODE_Pos |
               (uint32_t)init->triggerSrc << SRPWM0_VALLEY_SW_CTRL_VSW_TRGSEL_Pos |
               (uint32_t)init->targetEdge << SRPWM0_VALLEY_SW_CTRL_VSW_TARGET_EDGE_Pos |
               (uint32_t)(init->outChannelEn << init->captureSrc) << SRPWM0_VALLEY_SW_CTRL_VALLEY_OUT_EN_Pos |
               (uint32_t)init->delayEn << SRPWM0_VALLEY_SW_CTRL_RSNTPL_DLY_EN_Pos);

    MODIFY_REG(SRPWMx->VALLEY_CAP, SRPWM0_VALLEY_CAP_VSWCNT_STOP_Msk |       /* input source */
               SRPWM0_VALLEY_CAP_VSWCNT_START_Msk,
               (uint32_t)init->startCountEdge << SRPWM0_VALLEY_CAP_VSWCNT_START_Pos |
               (uint32_t)init->stopCountEdge << SRPWM0_VALLEY_CAP_VSWCNT_STOP_Pos);

    MODIFY_REG(SRPWMx->VSW_DLY_CAL, SRPWM0_VSW_DLY_CAL_VSW_DLY_CAL_SEL_Msk |       /* input source */
               SRPWM0_VSW_DLY_CAL_VSW_SFT_DLY_Msk,
               (uint32_t)init->delayMode << SRPWM0_VSW_DLY_CAL_VSW_DLY_CAL_SEL_Pos |
               (uint32_t)init->swDelayValue << SRPWM0_VSW_DLY_CAL_VSW_SFT_DLY_Pos);
}

/**
 * @brief configures the specified srpwm valley
 *
 * @param SRPWMx select the specified srpwm
 * @return * void
 */
void SRPWM_enableValley(SRPWM_Type *SRPWMx)
{
    SET_BIT(SRPWMx->VALLEY_SW_CTRL, SRPWM0_VALLEY_SW_CTRL_VSW_EN_Msk);
}

/**
 * @brief configures the specified srpwm valley
 *
 * @param SRPWMx select the specified srpwm
 * @return * void
 */
void SRPWM_disableValley(SRPWM_Type *SRPWMx)
{
    CLEAR_BIT(SRPWMx->VALLEY_SW_CTRL, SRPWM0_VALLEY_SW_CTRL_VSW_EN_Msk);
}

/**
 * @brief configures the specified srpwm valley
 *
 * @param SRPWMx select the specified srpwm
 * @return * void
 */
void SRPWM_forceValley(SRPWM_Type *SRPWMx)
{
    SET_BIT(SRPWMx->VALLEY_SFT_TRG, SRPWM0_VALLEY_SFT_TRG_VSW_SFT_TRG_Msk);
}

/**
 * @brief forcefully trigger os prep protection once for the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB the specified ab signal
 */
void SRPWMCOM_enterPREPOneShot(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        SET_BIT(SRPWMCOM->PREP_OS_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_OS_SFT_PREP_OSA_SFT_Pos);
    }
    else
    {
//        SET_BIT(SRPWMCOM->PREP_OS_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_OS_SFT_PREP_OSB_SFT_Pos);
    }
}

/**
 * @brief quit forcefully trigger os prep protection once for the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB the specified ab signal
 */
void SRPWMCOM_exitPREPOneShot(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        CLEAR_BIT(SRPWMCOM->PREP_OS_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_OS_SFT_PREP_OSA_SFT_Pos);
    }
    else
    {
//        CLEAR_BIT(SRPWMCOM->PREP_OS_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_OS_SFT_PREP_OSB_SFT_Pos);
    }
}

/**
 * @brief forcefully trigger CBC prep protection once for the ab signal of the specified channel
 *
 * @param channelMask the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 * @param pwmAB optional ab signal
 */
void SRPWMCOM_forcePREPCycleByCycle(uint16_t channelMask, SRPWM_AB pwmAB)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    if (pwmAB != SRPWM_B)
    {
//        SET_BIT(SRPWMCOM->PREP_CBC_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_CBC_SFT_PREP_CBCA_SFT_Pos);
    }
    else
    {
//        SET_BIT(SRPWMCOM->PREP_CBC_SFT, (uint32_t)channelMask << SRPWMCOM_PREP_CBC_SFT_PREP_CBCB_SFT_Pos);
    }
}

/**
 * @brief set unres prep protection pulse time min value
 *
 * @param SRPWMx select the specified srpwm
 * @param min_time unres protect min time value
 */
void SRPWM_setPREPUnresMinTime(SRPWM_Type *SRPWMx, uint16_t min_time)
{
    MODIFY_REG(SRPWMx->PREP_UNRES_MIN_TIME, SRPWM0_PREP_UNRES_MIN_TIME_PREP_UNRES_MIN_TIME_Msk, min_time);
}

/**
 * @brief PREPStruct Init
 *
 * @param initStruct
 */
void SRPWM_initPREPStruct(SRPWM_PREPInitTypeDef *initStruct)
{
    initStruct->a.cbcFaultProtectSig     = 0;
    initStruct->a.osFaultProtectSig      = 0;
    initStruct->a.unresFaultProtectSig   = 0;
    initStruct->a.cbcFaultProtectState   = SRPWM_PREP_STATE_HIZ;
    initStruct->a.osFaultProtectState    = SRPWM_PREP_STATE_HIZ;
    initStruct->a.unresFaultProtectState = SRPWM_PREP_STATE_HIZ;
    initStruct->a.osStartSyncEn          = DISABLE;
    initStruct->a.osEndSyncEn            = ENABLE;
    initStruct->a.osStartSyncSel         = SRPWM_ALLEVT_ZERO_EVT;
    initStruct->a.osEndSyncSel           = SRPWM_ALLEVT_SW_EVT;
    initStruct->a.cbcEndSyncSel          = SRPWM_ALLEVT_ZERO_EVT;
    initStruct->a.setHighDly             = 0;
    initStruct->a.setLowDly              = 0;
    initStruct->b.cbcFaultProtectSig     = 0;
    initStruct->b.osFaultProtectSig      = 0;
    initStruct->b.unresFaultProtectSig   = 0;
    initStruct->b.cbcFaultProtectState   = SRPWM_PREP_STATE_HIZ;
    initStruct->b.osFaultProtectState    = SRPWM_PREP_STATE_HIZ;
    initStruct->b.unresFaultProtectState = SRPWM_PREP_STATE_HIZ;
    initStruct->b.osStartSyncEn          = DISABLE;
    initStruct->b.osEndSyncEn            = ENABLE;
    initStruct->b.osStartSyncSel         = SRPWM_ALLEVT_ZERO_EVT;
    initStruct->b.osEndSyncSel           = SRPWM_ALLEVT_SW_EVT;
    initStruct->b.cbcEndSyncSel          = SRPWM_ALLEVT_ZERO_EVT;
    initStruct->b.setHighDly             = 0;
    initStruct->b.setLowDly              = 0;

    initStruct->fastProtectMask = DISABLE;
}

/**
 * @brief initialize the exception pre protection feature
 *
 * @param SRPWMx select the specified srpwm
 * @param init parameter for structure \e SRPWM_PREPInitTypeDef initialization
 *      - cbcFaultProtectSig - osFaultProtectSig - unresFaultProtectSig
 *       - SRPWM_PREP_SIG_FAULT_REAL0
 *       - SRPWM_PREP_SIG_FAULT_REAL1
 *       - SRPWM_PREP_SIG_FAULT_REAL2
 *       - SRPWM_PREP_SIG_FAULT_REAL3
 *       - SRPWM_PREP_SIG_FAULT_REAL4
 *       - SRPWM_PREP_SIG_FAULT_REAL5
 *       - SRPWM_PREP_SIG_FAULT_LATCH0
 *       - SRPWM_PREP_SIG_FAULT_LATCH1
 *       - SRPWM_PREP_SIG_FAULT_LATCH2
 *       - SRPWM_PREP_SIG_FAULT_LATCH3
 *       - SRPWM_PREP_SIG_FAULT_LATCH4
 *       - SRPWM_PREP_SIG_FAULT_LATCH5
 *       - SRPWM_PREP_SIG_SW
 *      - osStartSyncSel - osEndSyncSel - cbcEndSyncSel
 *       - SRPWM_ALLEVT_ZERO_EVT
 *       - SRPWM_ALLEVT_PRD_EVT
 *       - SRPWM_ALLEVT_SCMPA_UP_EVT
 *       - SRPWM_ALLEVT_SCMPB_UP_EVT
 *       - SRPWM_ALLEVT_SCMPC_UP_EVT
 *       - SRPWM_ALLEVT_SCMPD_UP_EVT
 *       - SRPWM_ALLEVT_SCMPA_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPB_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPC_DOWN_EVT
 *       - SRPWM_ALLEVT_SCMPD_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPA_UP_EVT
 *       - SRPWM_ALLEVT_CMPB_UP_EVT
 *       - SRPWM_ALLEVT_CMPC_UP_EVT
 *       - SRPWM_ALLEVT_CMPD_UP_EVT
 *       - SRPWM_ALLEVT_CMPA_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPB_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPC_DOWN_EVT
 *       - SRPWM_ALLEVT_CMPD_DOWN_EVT
 *       - SRPWM_ALLEVT_FPP_FAULT_POS0
 *       - SRPWM_ALLEVT_FPP_FAULT_POS1
 *       - SRPWM_ALLEVT_FPP_FAULT_POS2
 *       - SRPWM_ALLEVT_FPP_FAULT_POS3
 *       - SRPWM_ALLEVT_SYNC0
 *       - SRPWM_ALLEVT_SYNC1
 *       - SRPWM_ALLEVT_BURST_OVER
 *       - SRPWM_ALLEVT_B_NEG
 *       - SRPWM_ALLEVT_B_POS
 *       - SRPWM_ALLEVT_A_NEG
 *       - SRPWM_ALLEVT_A_POS
 *       - SRPWM_ALLEVT_SW_EVT
 */
void SRPWM_initPREP(SRPWM_Type *SRPWMx, SRPWM_PREPInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_PREP_SIG(init->a.cbcFaultProtectSig));
    assert_param(IS_SRPWM_PREP_SIG(init->a.osFaultProtectSig));
    assert_param(IS_SRPWM_PREP_UNRES_SIG(init->a.unresFaultProtectSig));
    assert_param(IS_SRPWM_PREP_SIG(init->b.cbcFaultProtectSig));
    assert_param(IS_SRPWM_PREP_SIG(init->b.osFaultProtectSig));
    assert_param(IS_SRPWM_PREP_UNRES_SIG(init->b.unresFaultProtectSig));
    assert_param(IS_SRPWM_ALLEVT(init->a.osStartSyncSel));
    assert_param(IS_SRPWM_ALLEVT(init->a.osEndSyncSel));
    assert_param(IS_SRPWM_ALLEVT(init->a.cbcEndSyncSel));
    assert_param(IS_SRPWM_ALLEVT(init->b.osStartSyncSel));
    assert_param(IS_SRPWM_ALLEVT(init->b.osEndSyncSel));
    assert_param(IS_SRPWM_ALLEVT(init->b.cbcEndSyncSel));

    /* configure cbc os and unconstrained exception protection signals */
    MODIFY_REG(SRPWMx->PREP_CBC_MSEL,
               SRPWM0_PREP_CBC_MSEL_PREP_CBCA_MSEL_Msk |
               SRPWM0_PREP_CBC_MSEL_PREP_CBCB_MSEL_Msk,
               (uint32_t)init->a.cbcFaultProtectSig << SRPWM0_PREP_CBC_MSEL_PREP_CBCA_MSEL_Pos |
               (uint32_t)init->b.cbcFaultProtectSig << SRPWM0_PREP_CBC_MSEL_PREP_CBCB_MSEL_Pos);
    MODIFY_REG(SRPWMx->PREP_OSC_MSEL,
               SRPWM0_PREP_OSC_MSEL_PREP_OSA_MSEL_Msk |
               SRPWM0_PREP_OSC_MSEL_PREP_OSB_MSEL_Msk,
               (uint32_t)init->a.osFaultProtectSig << SRPWM0_PREP_OSC_MSEL_PREP_OSA_MSEL_Pos |
               (uint32_t)init->b.osFaultProtectSig << SRPWM0_PREP_OSC_MSEL_PREP_OSB_MSEL_Pos);
    MODIFY_REG(SRPWMx->PREP_UNRES_MSEL,
               SRPWM0_PREP_UNRES_MSEL_PREP_UNRESA_MSEL_Msk |
               SRPWM0_PREP_UNRES_MSEL_PREP_UNRESB_MSEL_Msk,
               (uint32_t)init->a.unresFaultProtectSig << SRPWM0_PREP_UNRES_MSEL_PREP_UNRESA_MSEL_Pos |
               (uint32_t)init->b.unresFaultProtectSig << SRPWM0_PREP_UNRES_MSEL_PREP_UNRESB_MSEL_Pos);
    /* configure the output state after cbc os unconstrained protection */
    MODIFY_REG(SRPWMx->PREP_PROT_ST,
               SRPWM0_PREP_PROT_ST_PREP_CBCA_PROT_ST_Msk |
               SRPWM0_PREP_PROT_ST_PREP_OSA_PROT_ST_Msk |
               SRPWM0_PREP_PROT_ST_PREP_UNRESA_PROT_ST_Msk |
               SRPWM0_PREP_PROT_ST_PREP_CBCB_PROT_ST_Msk |
               SRPWM0_PREP_PROT_ST_PREP_OSB_PROT_ST_Msk |
               SRPWM0_PREP_PROT_ST_PREP_UNRESB_PROT_ST_Msk,
               (uint32_t)init->a.cbcFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_CBCA_PROT_ST_Pos |
               (uint32_t)init->a.osFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_OSA_PROT_ST_Pos |
               (uint32_t)init->a.unresFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_UNRESA_PROT_ST_Pos |
               (uint32_t)init->b.cbcFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_CBCB_PROT_ST_Pos |
               (uint32_t)init->b.osFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_OSB_PROT_ST_Pos |
               (uint32_t)init->b.unresFaultProtectState << SRPWM0_PREP_PROT_ST_PREP_UNRESB_PROT_ST_Pos);
    /* configure OS start end sync signal selection and configure the cbc end sync signal*/
    MODIFY_REG(SRPWMx->PREP_SYNC_SEL,
               SRPWM0_PREP_SYNC_SEL_PREP_OSA_START_SEL_Msk |
               SRPWM0_PREP_SYNC_SEL_PREP_OSA_END_SEL_Msk |
               SRPWM0_PREP_SYNC_SEL_PREP_CBCA_END_SEL_Msk |
               SRPWM0_PREP_SYNC_SEL_PREP_OSB_START_SEL_Msk |
               SRPWM0_PREP_SYNC_SEL_PREP_OSB_END_SEL_Msk |
               SRPWM0_PREP_SYNC_SEL_PREP_CBCB_END_SEL_Msk,
               (uint32_t)(POSITION_VAL(
                              init->a.osStartSyncSel) & 0x1F) << SRPWM0_PREP_SYNC_SEL_PREP_OSA_START_SEL_Pos |
               (uint32_t)(POSITION_VAL(
                              init->a.osEndSyncSel) & 0x1F) << SRPWM0_PREP_SYNC_SEL_PREP_OSA_END_SEL_Pos |
               (uint32_t)(POSITION_VAL(
                              init->a.cbcEndSyncSel) & 0x1F) << SRPWM0_PREP_SYNC_SEL_PREP_CBCA_END_SEL_Pos |
               (uint32_t)(POSITION_VAL(
                              init->b.osStartSyncSel) & 0x1F) << SRPWM0_PREP_SYNC_SEL_PREP_OSB_START_SEL_Pos |
               (uint32_t)(POSITION_VAL(
                              init->b.osEndSyncSel) & 0x1F) << SRPWM0_PREP_SYNC_SEL_PREP_OSB_END_SEL_Pos |
               (uint32_t)(POSITION_VAL(
                              init->b.cbcEndSyncSel) & 0x1F) <<
               SRPWM0_PREP_SYNC_SEL_PREP_CBCB_END_SEL_Pos);
    /* configure OS enable or disable  */
    MODIFY_REG(SRPWMx->PREP_SYNC_MD,
               SRPWM0_PREP_SYNC_MD_PREP_OSA_START_MD_Msk |
               SRPWM0_PREP_SYNC_MD_PREP_OSA_END_MD_Msk |
               SRPWM0_PREP_SYNC_MD_PREP_OSB_START_MD_Msk |
               SRPWM0_PREP_SYNC_MD_PREP_OSB_END_MD_Msk,
               (uint32_t)init->a.osStartSyncEn << SRPWM0_PREP_SYNC_MD_PREP_OSA_START_MD_Pos |
               (uint32_t)init->a.osEndSyncEn << SRPWM0_PREP_SYNC_MD_PREP_OSA_END_MD_Pos |
               (uint32_t)init->b.osStartSyncEn << SRPWM0_PREP_SYNC_MD_PREP_OSB_START_MD_Pos |
               (uint32_t)init->b.osEndSyncEn << SRPWM0_PREP_SYNC_MD_PREP_OSB_END_MD_Pos);
    /* set a b s high delay configuration */
    WRITE_REG(SRPWMx->PREP_SET_DLY, (uint32_t)init->a.setHighDly << SRPWM0_PREP_SET_DLY_PREP_SETA_DLY_Pos |
              (uint32_t)init->b.setHighDly << SRPWM0_PREP_SET_DLY_PREP_SETB_DLY_Pos);
    /* configure a b with low latency */
    WRITE_REG(SRPWMx->PREP_CLR_DLY, (uint32_t)init->a.setLowDly << SRPWM0_PREP_CLR_DLY_PREP_CLRA_DLY_Pos |
              (uint32_t)init->b.setLowDly << SRPWM0_PREP_CLR_DLY_PREP_CLRB_DLY_Pos);
    /* quick protect mode feature */
    WRITE_REG(SRPWMx->EPWM_FAST_MASK, init->fastProtectMask);
}

/**
 * @brief clears the specified time counter for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param state the specified time counter
 *      - SRPWM_PREP_A_SET_TIMER
 *      - SRPWM_PREP_A_CLR_TIMER
 *      - SRPWM_PREP_A_INVERT_TIMER
 *      - SRPWM_PREP_A_HIZ_TIMER
 *      - SRPWM_PREP_B_SET_TIMER
 *      - SRPWM_PREP_B_CLR_TIMER
 *      - SRPWM_PREP_B_INVERT_TIMER
 *      - SRPWM_PREP_B_HIZ_TIMER
 */
void SRPWM_clearPREPTimer(SRPWM_Type *SRPWMx, uint8_t state)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_PREP_TIMER(state));

    SET_BIT(SRPWMx->PREP_CNT_CLR, state);
}

/**
 * @brief gets the indication status of the specified signal for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param sigState the specified signal that needs to be acquired
 * @return FlagStatus
 */
FlagStatus SRPWM_getPREPSigState(SRPWM_Type *SRPWMx, SRPWM_PREP_SigState sigState)
{
    FlagStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    ret = DRV_IS_BIT_SET(SRPWMx->PREP_SETCLR_RPT, sigState) ? SET : RESET;

    return ret;
}

/**
 * @brief obtains the specified signal exception time before the specified module s prep exception protection
 *
 * @param SRPWMx select the specified srpwm
 * @param ab optional pwma and pwmb signals
 * @param sig the specified signal that needs to be acquired
 * @return uint16_t
 */
uint32_t SRPWM_getPREPFaultTime(SRPWM_Type *SRPWMx, SRPWM_AB ab, SRPWM_PreprotectState sig)
{
    uint32_t ret = 0;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (ab != SRPWM_B)
    {
        if (sig == SRPWM_PREP_STATE_HIZ)
        {
            ret = READ_REG(SRPWMx->PREPA_HIZ_CNT_RPT);
        }
        else if (sig == SRPWM_PREP_STATE_CLR)
        {
            ret = READ_REG(SRPWMx->PREPA_CLR_CNT_RPT);
        }
        else if (sig == SRPWM_PREP_STATE_SET)
        {
            ret = READ_REG(SRPWMx->PREPA_SET_CNT_RPT);
        }
        else
        {
            ret = READ_REG(SRPWMx->PREPA_INV_CNT_RPT);
        }
    }
    else
    {
        if (sig == SRPWM_PREP_STATE_HIZ)
        {
            ret = READ_REG(SRPWMx->PREPB_HIZ_CNT_RPT);
        }
        else if (sig == SRPWM_PREP_STATE_CLR)
        {
            ret = READ_REG(SRPWMx->PREPB_CLR_CNT_RPT);
        }
        else if (sig == SRPWM_PREP_STATE_SET)
        {
            ret = READ_REG(SRPWMx->PREPB_SET_CNT_RPT);
        }
        else
        {
            ret = READ_REG(SRPWMx->PREPB_INV_CNT_RPT);
        }
    }

    return ret;
}

/**
 * @brief the A/B signal of the specified channel is forced to output the post protection status
 *
 * @param channel the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param pwmAB optional signals
 * @param state optional state
 */
void SRPWMCOM_forcePSTPOutState(uint16_t channel, SRPWM_AB pwmAB, SRPWM_PSTPOutState state)
{
    uint8_t coreInterval           = 4; /* interval factor between spwm master channels */
    uint8_t coreABinterval         = 2; /* the interval factor between spwm master slave ab channels */
    uint8_t core07or811DividePoint = 7;
    uint8_t core811Pos             = 8; /* when the channel is 8 and above you need to subtract the calculated pos from
                                         * core811 pos to get the register pos that needs to be set */
    uint8_t core811PosMask         = 0;

    assert_param(IS_GET_SRPWM_CHANNEL(channel));

    if (POSITION_VAL(channel) <= core07or811DividePoint)
    {
//        MODIFY_REG(SRPWMCOM->PSTP_SFT_07FORCE,
//                   SRPWMCOM_PSTP_SFT_07FORCE_PSTP_SFT_FORCE0A_Msk <<
//                   (POSITION_VAL(channel) * coreInterval + pwmAB * coreABinterval),
//                   (uint32_t)state << (POSITION_VAL(channel) * coreInterval + pwmAB * coreABinterval));
    }
    else
    {
        core811PosMask = POSITION_VAL(channel) - core811Pos;
//        MODIFY_REG(SRPWMCOM->PSTP_SFT_811FORCE,
//                   SRPWMCOM_PSTP_SFT_07FORCE_PSTP_SFT_FORCE0A_Msk <<
//                   (core811PosMask * coreInterval + pwmAB * coreABinterval),
//                   (uint32_t)state << (core811PosMask * coreInterval + pwmAB * coreABinterval));
    }
}

/**
 * @brief MutexStruct Init
 *
 * @param initStruct
 */
void SRPWMCOM_initMutexStruct(SRPWMCOM_MutexInitTypeDef *initStruct)
{
    initStruct->mutexResultGroupMask = 0;
    initStruct->mutexSig0            = SRPWMCOM_MUTEX_SIG_SRPWM0_A;
    initStruct->mutexSig1            = SRPWMCOM_MUTEX_SIG_SRPWM0_A;
    initStruct->mutexCondition       = SRPWMCOM_A_LOW_B_LOW;
}

/**
 * @brief initialize the mutex function
 *
 * @param init the mutex init struct
 *      - mutexResultGroupMask
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_initMutex(SRPWMCOM_MutexInitTypeDef *init)
{
    uint8_t pos = 0;

    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(init->mutexResultGroupMask));

    for (pos = 0; pos < SRPWM_CORE_NUM; pos++)
    {
        if (DRV_IS_BIT_SET(init->mutexResultGroupMask, BIT_MASK(pos)))
        {
            /* configure mutex signal 0 */
            MODIFY_REG(SRPWMCOM->MEPWM_EXC_CFG[pos],
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXCSIG0_SEL_Msk,
                       (uint32_t)init->mutexSig0 <<
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXCSIG0_SEL_Pos);
            /* configure mutex signal 1 */
            MODIFY_REG(SRPWMCOM->MEPWM_EXC_CFG[pos],
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXCSIG1_SEL_Msk,
                       (uint32_t)init->mutexSig1 <<
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXCSIG1_SEL_Pos);
            /* configure the mutex state of the two mutex signals after selection */
            MODIFY_REG(SRPWMCOM->MEPWM_EXC_CFG[pos],
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXC_ST_Msk,
                       (uint32_t)init->mutexCondition <<
                       SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXC_ST_Pos);
        }
    }
}

/**
 * @brief enables the mutex determination function for the specified channel
 *
 * @param mutexResultGroupMask the specified mutex group number
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_enableMutex(uint16_t mutexResultGroupMask)
{
    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(mutexResultGroupMask));

    SET_BIT(SRPWMCOM->MEPWM_EXC_EN, mutexResultGroupMask);
}

/**
 * @brief disable specifies the mutex determination function of the channel
 *
 * @param mutexResultGroupMask  the specified mutex group number
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_disableMutex(uint16_t mutexResultGroupMask)
{
    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(mutexResultGroupMask));

    CLEAR_BIT(SRPWMCOM->MEPWM_EXC_EN, mutexResultGroupMask);
}

/**
 * @brief the mutex generated by enabling masking acts on the specified channel
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param mutexResultGroupMask  the specified mutex group number
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_enableMutexMsk(uint16_t channel, uint16_t mutexResultGroupMask)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));
    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(mutexResultGroupMask));

    SET_BIT(SRPWMCOM->MEPWM_EXC_CFG[POSITION_VAL(
                                        channel)],
            (uint32_t)mutexResultGroupMask << SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXC_MASK_Pos);
}

/**
 * @brief the mutex created by the incapacitation shield acts on the specified channel
 *
 * @param channel  the specified channel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param mutexResultGroupMask  the specified mutex group number
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_disableMutexMsk(uint16_t channel, uint16_t mutexResultGroupMask)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));
    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(mutexResultGroupMask));

    CLEAR_BIT(SRPWMCOM->MEPWM_EXC_CFG[POSITION_VAL(
                                          channel)],
              (uint32_t)mutexResultGroupMask << SRPWMCOM_MEPWM_EXC_CFG_MEPWM_EXC_MASK_Pos);
}

/**
 * @brief to obtain the mutex status of the specified spwm module note that only one set of spw ms is supported at the
 * same time
 *
 * @param mutexResultGroup  the specified mutex group number
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 * @return FlagStatus
 */
FlagStatus SRPWMCOM_getMutexStatus(uint16_t mutexResultGroup)
{
    FlagStatus ret = RESET;

    assert_param(IS_GET_SRPWM_MUTEX_RESULT_GRP(mutexResultGroup));

    ret = DRV_IS_BIT_SET(SRPWMCOM->MEPWM_EXC_RPT, mutexResultGroup) ? SET : RESET;

    return ret;
}

/**
 * @brief gets the mutex status for all channels
 *
 * @return uint16_t
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 */
uint16_t SRPWMCOM_getMutexStatusAllBits(void)
{
    uint16_t ret = 0;

    ret = (uint16_t)READ_REG(SRPWMCOM->MEPWM_EXC_RPT);

    return ret;
}

/**
 * @brief clears the mutex status of the specified spwm
 *
 * @param mutexResultGroupMask
 *      - SRPWM_MUTEX_RESULT_GRP_0
 *      - SRPWM_MUTEX_RESULT_GRP_1
 *      - SRPWM_MUTEX_RESULT_GRP_2
 *      - SRPWM_MUTEX_RESULT_GRP_3
 *      - SRPWM_MUTEX_RESULT_GRP_4
 *      - SRPWM_MUTEX_RESULT_GRP_5
 *      - SRPWM_MUTEX_RESULT_GRP_6
 *      - SRPWM_MUTEX_RESULT_GRP_7
 *      - SRPWM_MUTEX_RESULT_GRP_8
 *      - SRPWM_MUTEX_RESULT_GRP_9
 *      - SRPWM_MUTEX_RESULT_GRP_10
 *      - SRPWM_MUTEX_RESULT_GRP_11
 *      - SRPWM_MUTEX_RESULT_GRP_ALL
 */
void SRPWMCOM_clearMutexStatus(uint16_t mutexResultGroupMask)
{
    assert_param(IS_SRPWM_MUTEX_RESULT_GRP(mutexResultGroupMask));

    SET_BIT(SRPWMCOM->MEPWM_EXC_CLR, mutexResultGroupMask);
}

/**
 * @brief PSTPStruct Init
 *
 * @param initStruct the pointer to the structure of the PSTP init
 */
void SRPWM_initPSTPStruct(SRPWM_PSTPInitTypeDef *initStruct)
{
    initStruct->mutexConditionAB = SRPWMCOM_A_LOW_B_LOW;
    initStruct->mutexEn          = DISABLE;
    initStruct->swapSyncEn       = DISABLE;
    initStruct->swapEn           = DISABLE;
    initStruct->a.mutexOutState  = SRPWM_PSTP_MUTEX_OUTSTATE_NONE;
    initStruct->a.invertEn       = DISABLE;
    initStruct->b.mutexOutState  = SRPWM_PSTP_MUTEX_OUTSTATE_NONE;
    initStruct->b.invertEn       = DISABLE;
}

/**
 * @brief initialize the post protect function
 *
 * @param SRPWMx select the specified srpwm
 * @param init the pointer to the structure of the PSTP init
 */
void SRPWM_initPSTP(SRPWM_Type *SRPWMx, SRPWM_PSTPInitTypeDef *init)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->PSTP_CTL,
               SRPWM0_PSTP_CTL_PSTP_EXC_FORCEB_Msk |    /* configure the output state when ab is mutually exclusive
                                                         */
               SRPWM0_PSTP_CTL_PSTP_EXC_FORCEA_Msk |
               SRPWM0_PSTP_CTL_PSTP_OUTB_INV_SEL_Msk |  /* post protect whether ab takes the negative output after
                                                         * that */
               SRPWM0_PSTP_CTL_PSTP_OUTA_INV_SEL_Msk |
               SRPWM0_PSTP_CTL_PSTP_EXC_ST_Msk,         /* configure the mutex state of ab */
               (uint32_t)init->b.mutexOutState << SRPWM0_PSTP_CTL_PSTP_EXC_FORCEB_Pos |
               (uint32_t)init->a.mutexOutState << SRPWM0_PSTP_CTL_PSTP_EXC_FORCEA_Pos |
               (uint32_t)init->b.invertEn << SRPWM0_PSTP_CTL_PSTP_OUTB_INV_SEL_Pos |
               (uint32_t)init->a.invertEn << SRPWM0_PSTP_CTL_PSTP_OUTA_INV_SEL_Pos |
               (uint32_t)init->mutexConditionAB << SRPWM0_PSTP_CTL_PSTP_EXC_ST_Pos);
    /* enable or disable mutex detection */
    if (init->mutexEn != DISABLE)
    {
        SET_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_EXC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_EXC_EN_Msk);
    }
    /* the enable or disable output swaps whether to wait for a sync signal */
    if (init->swapSyncEn != DISABLE)
    {
        SET_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_SWAP_SYNC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_SWAP_SYNC_EN_Msk);
    }
    /* whether the output signal of ab is exchanged */
    if (init->swapEn != DISABLE)
    {
        SET_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_SWAP_Msk);
    }
    else
    {
        CLEAR_BIT(SRPWMx->PSTP_CTL, SRPWM0_PSTP_CTL_PSTP_SWAP_Msk);
    }
}

/**
 * @brief gets the exception status of the specified signal for the post processing of the pstp exception for the
 * specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param sig the specified signal that needs to be acquired
 * @return FlagStatus
 */
FlagStatus SRPWM_getPSTPFaultState(SRPWM_Type *SRPWMx, SRPWM_PSTPFaultStateSig sig)
{
    FlagStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    ret = DRV_IS_BIT_SET(SRPWMx->PSTP_FAULT_RPT, sig) ? SET : RESET;

    return ret;
}

/**
 * @brief set the period value including high accuracy
 *
 * @param SRPWMx select the specified srpwm
 * @param periodHR high accuracy of period values
 * @return * void
 */
void SRPWM_setPeriodHR(SRPWM_Type *SRPWMx, uint8_t periodHR)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_HR(periodHR));

    MODIFY_REG(SRPWMx->TB_PRD, SRPWM_HR_MSK, (uint32_t)periodHR << SRPWM_HR_POS);
}

/**
 * @brief set the high accuracy of the compare value
 *
 * @param SRPWMx select the specified srpwm
 * @param edge the edge type
 * @param cmpHR the high accuracy of the compare value
 * @return * void
 */
void SPPWM_setCompareHR(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint8_t cmpHR)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_HR(cmpHR));

    switch (edge)
    {
    case SRPWM_EDGE_POS_A:
        MODIFY_REG(SRPWMx->CMP_CMPA, SRPWM_HR_MSK, (uint32_t)cmpHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_NEG_A:
        MODIFY_REG(SRPWMx->CMP_CMPB, SRPWM_HR_MSK, (uint32_t)cmpHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_POS_B:
        MODIFY_REG(SRPWMx->CMP_CMPC, SRPWM_HR_MSK, (uint32_t)cmpHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_NEG_B:
        MODIFY_REG(SRPWMx->CMP_CMPD, SRPWM_HR_MSK, (uint32_t)cmpHR << SRPWM_HR_POS);
        break;
    }
}

/**
 * @brief set the high accuracy of the deadband
 *
 * @param SRPWMx select the specified srpwm
 * @param edge select the rising or falling edge of the dead delay
 * @param deadTimeHR high accuracy of the deadband
 * @return * void
 */
void SRPWM_setDBHR(SRPWM_Type *SRPWMx, SRPWM_Edge edge, uint8_t deadTimeHR)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_HR(deadTimeHR));

    switch (edge)
    {
    case SRPWM_EDGE_POS_A:
        MODIFY_REG(SRPWMx->DB_APOS_DLY, SRPWM_HR_MSK, (uint32_t)deadTimeHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_NEG_A:
        MODIFY_REG(SRPWMx->DB_ANEG_DLY, SRPWM_HR_MSK, (uint32_t)deadTimeHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_POS_B:
        MODIFY_REG(SRPWMx->DB_BPOS_DLY, SRPWM_HR_MSK, (uint32_t)deadTimeHR << SRPWM_HR_POS);
        break;

    case SRPWM_EDGE_NEG_B:
        MODIFY_REG(SRPWMx->DB_BNEG_DLY, SRPWM_HR_MSK, (uint32_t)deadTimeHR << SRPWM_HR_POS);
        break;
    }
}

/**
 * @brief the spwmcom common module enables the high precision functions of the specified module
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 * @attention only channel 0~3 support high precision function
 */
void SRPWMCOM_enableHR(uint16_t channelMask)
{
    assert_param(IS_SRPWM_HR_CHANNEL(channelMask));

    SET_BIT(SRPWMCOM->EPWM_HR_EN, channelMask);
}

/**
 * @brief the spwmcom common module disables the high precision functions of the specified module
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 * @attention only channel 0~3 support high precision function
 */
void SRPWMCOM_disableHR(uint16_t channelMask)
{
    assert_param(IS_SRPWM_HR_CHANNEL(channelMask));

    CLEAR_BIT(SRPWMCOM->EPWM_HR_EN, channelMask);
}

/**
 * @brief enable the dll function in the sysc module to turn on the high precision function for srpwm
 *
 * @param channelMask pwm channel 0~3
 * @param ab
 */
void SRPWM_enableHRPWMDLL(uint16_t channelMask, SRPWM_AB ab)
{
    assert_param(IS_SRPWM_HR_CHANNEL(channelMask));
    if (ab == SRPWM_A)
    {
//        SET_BIT(SYSC->DLL_EXT, (uint32_t)channelMask);
    }
    else
    {
//        SET_BIT(SYSC->DLL_EXT, (uint32_t)channelMask << 4);
    }
}

/**
 * @brief disables the dll function in the sysc module and turns off the high precision function to the srpwm
 *
 * @param channelMask pwm channel 0~3
 * @param ab
 */
void SRPWM_disableHRPWMDLL(uint16_t channelMask, SRPWM_AB ab)
{
    assert_param(IS_SRPWM_HR_CHANNEL(channelMask));
    if (ab == SRPWM_A)
    {
//        CLEAR_BIT(SYSC->DLL_EXT, (uint32_t)channelMask);
    }
    else
    {
//        CLEAR_BIT(SYSC->DLL_EXT, (uint32_t)channelMask << 4);
    }
}

/**
 * @brief enable specifies the spwm module s high precision bypass function
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableHRPWMBypass(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    WRITE_REG(SRPWMx->HRPWM_BPS, SRPWM0_HRPWM_BPS_HRPWM_BPS_Msk);
}

/**
 * @brief disable specifies the spwm module s high precision bypass function
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableHRPWMBypass(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_REG(SRPWMx->HRPWM_BPS);
}

/**
 * @brief enable the spwm module s high precision filtering function
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableHRPWMFilter(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

//    SET_BIT(SRPWMx->HRPWM_FILTER, SRPWM0_HRPWM_FILTER_HRPWM_FILTER_EN_Msk);
}

/**
 * @brief disable the spwm module s high precision filtering function
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableHRPWMFilter(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

//    CLEAR_BIT(SRPWMx->HRPWM_FILTER, SRPWM0_HRPWM_FILTER_HRPWM_FILTER_EN_Msk);
}

/**
 * @brief configure the high precision input filter length that specifies the spwm module
 *
 * @param SRPWMx select the specified srpwm
 * @param width the filter length
 */
void SRPWM_setHRPWMFilterWidth(SRPWM_Type *SRPWMx, uint16_t width)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_HRPWM_FILTER_LEN(width));

//    MODIFY_REG(SRPWMx->HRPWM_FILTER,
//               SRPWM0_HRPWM_FILTER_HRPWM_FILTER_LEN_Msk,
//               (uint32_t)width << SRPWM0_HRPWM_FILTER_HRPWM_FILTER_LEN_Pos);
}

/**
 * @brief obtain the delay time of the specified rising and falling edges of the specified module ab signal
 *
 * @param SRPWMx the specified module
 * @param edge specify the rising and falling edges of the ab signal
 * @return uint8_t
 */
uint8_t SRPWM_getHRPWMEgdeDly(SRPWM_Type *SRPWMx, SRPWM_Edge edge)
{
    uint32_t ret = 0;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (edge == SRPWM_EDGE_POS_A)
    {
        ret = READ_BIT(SRPWMx->HRPWM_DLY_RPT, SRPWM0_HRPWM_DLY_RPT_HRPWMA_POS_DLY_RPT_Msk);
    }
    else if (edge == SRPWM_EDGE_NEG_A)
    {
        ret =
            READ_BIT(SRPWMx->HRPWM_DLY_RPT,
                     SRPWM0_HRPWM_DLY_RPT_HRPWMA_NEG_DLY_RPT_Msk) >> SRPWM0_HRPWM_DLY_RPT_HRPWMA_NEG_DLY_RPT_Pos;
    }
    else if (edge == SRPWM_EDGE_POS_B)
    {
        ret =
            READ_BIT(SRPWMx->HRPWM_DLY_RPT,
                     SRPWM0_HRPWM_DLY_RPT_HRPWMB_POS_DLY_RPT_Msk) >> SRPWM0_HRPWM_DLY_RPT_HRPWMB_POS_DLY_RPT_Pos;
    }
    else
    {
        ret =
            READ_BIT(SRPWMx->HRPWM_DLY_RPT,
                     SRPWM0_HRPWM_DLY_RPT_HRPWMB_NEG_DLY_RPT_Msk) >> SRPWM0_HRPWM_DLY_RPT_HRPWMB_NEG_DLY_RPT_Pos;
    }

    return (uint8_t)ret;
}

/**
 * @brief Disables the DMA request for the specified SRPWM channel.
 *
 * @param dmaChannel The DMA channel to be disabled. It should be one of the following:
 * - SRPWM_DMA_CHANNEL0
 * - SRPWM_DMA_CHANNEL1
 * - SRPWM_DMA_CHANNEL2
 * - SRPWM_DMA_CHANNEL3
 *
 * @note This function modifies the DMA enable register and disables the specified DMA channel.
 *
 * @return void
 */
void SRPWMCOM_disableDMA(SRPWM_DMAChannel dmaChannel)
{
    CLEAR_BIT(SRPWMCOM->MEPWM_DMA_EN, BIT_MASK(dmaChannel));
}

/**
 * @brief enable specifies the synchronization signal that the module uses to generate the dma request signal
 *
 * @param SRPWMx select the specified srpwm
 * @param outEventMask synchronize collections with output events. @ref SRPWM Output Event Collections
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_setDMARequest(SRPWM_Type *SRPWMx, uint32_t outEventMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(outEventMask));

    SET_BIT(SRPWMx->EPWM_DMA_MSEL, outEventMask);
}

/**
 * @brief disable specifies the synchronization signal that the module uses to generate the dma request signal
 *
 * @param SRPWMx select the specified srpwm
 * @param outEventMask synchronize collections with output events. @ref SRPWM Output Event Collections
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_clearDMARequest(SRPWM_Type *SRPWMx, uint32_t outEventMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(outEventMask));

    CLEAR_BIT(SRPWMx->EPWM_DMA_MSEL, outEventMask);
}

/**
 * @brief select the divider factor for the dma request signal
 *
 * @param SRPWMx select the specified srpwm
 * @param div the frequency division factor of the dma request event
 */
void SRPWM_setDMAFreqDiv(SRPWM_Type *SRPWMx, uint8_t div)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->EPWM_DMA_DIV, SRPWM0_EPWM_DMA_DIV_EPWM_DMA_DIV_Msk, div);
}

/**
 * @brief enable the crossover function of dma
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableDMAFreqDiv(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->EPWM_DMA_DIV, SRPWM0_EPWM_DMA_DIV_EPWM_DMA_DIV_EN_Msk);
}

/**
 * @brief Disable the crossover function of dma
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableDMAFreqDiv(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_BIT(SRPWMx->EPWM_DMA_DIV, SRPWM0_EPWM_DMA_DIV_EPWM_DMA_DIV_EN_Msk);
}

/**
 * @brief enable the frequency doubling function after dma crossover
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableDMAFreqMulti(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->EPWM_DMA_MULTI, SRPWM0_EPWM_DMA_MULTI_EPWM_DMA_MULTI_EN_Msk);
}

/**
 * @brief disable the frequency doubling function after dma crossover
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableDMAFreqMulti(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_BIT(SRPWMx->EPWM_DMA_MULTI, SRPWM0_EPWM_DMA_MULTI_EPWM_DMA_MULTI_EN_Msk);
}

/**
 * @brief select the frequency multiplication coefficient of the signal after the dma request signal is divided
 *
 * @param SRPWMx select the specified srpwm
 * @param multi the frequency multiplier of the dma request
 */
void SRPWM_setDMAFreqMulti(SRPWM_Type *SRPWMx, uint16_t multi)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    MODIFY_REG(SRPWMx->EPWM_DMA_MULTI, SRPWM0_EPWM_DMA_MULTI_EPWM_DMA_MULTI_Msk, multi);
}

/**
 * @brief select the sync signal output to QEPx
 *
 * @param srcTrigger the trigger source matrix used to send to the adc
 * @param srcTriggerMask select the number in the trigger source matrix
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM0_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM1_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM2_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM3_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM4_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM5_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM6_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM7_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM8_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM9_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM10_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM11_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM12_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM13_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM14_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM15_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM16_SOC_AB
 *      - SRPWMCOM_QEP_TRIGGER_SRPWM17_SOC_AB
 * @return * void
 */
void SRPWMCOM_selectTriggerToQEP(uint32_t srcTriggerMask, SRPWMCOM_QEPx dstQepNumber)
{
    /* because the trigger signal of the qep is selected from the trigger source of the adc the trigger source of the
     * adc is configured first */

    WRITE_REG(SRPWMCOM->MEPWM_QEP_SYNC_SEL[dstQepNumber], srcTriggerMask);
}

/**
 * @brief enable specifies the synchronization signal that the module uses to generate the sadc0 request signal
 *         where sadc0 represents one of the two trigs trigger0 which can output an spwm
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of 1 of 2 is required for the
 * adc as the trigger
 * @param socSource the trigger source, the trigger source can be one or combination of the following:
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_setADCTriggerSource(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint32_t socSource)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(socSource));

    if (adcSOCType == SRPWM_SOC_A)
    {
        SET_BIT(SRPWMx->EPWM_SADC0_MSEL, socSource);
    }
    else
    {
        SET_BIT(SRPWMx->EPWM_SADC1_MSEL, socSource);
    }
}

/**
 * @brief disable specifies the synchronization signal that the module uses to generate the sadc0 request signal
 *         where sadc0 represents one of the two trigs trigger0 which can output an spwm
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of 1 of 2 is required for the
 * adc as the trigger
 * @param socSource the trigger source, the trigger source can be one or combination of the following:
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 */
void SRPWM_clearADCTriggerSource(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint32_t socSource)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OUT_EVT(socSource));

    if (adcSOCType == SRPWM_SOC_A)
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC0_MSEL, socSource);
    }
    else
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC1_MSEL, socSource);
    }
}

/**
 * @brief enables the divide function of the trigger signal sent to the adc
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of A of B is required for the adc
 * as the trigger
 */
void SRPWM_enableADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        SET_BIT(SRPWMx->EPWM_SADC0_DIV, SRPWM0_EPWM_SADC0_DIV_EPWM_SADC0_DIV_EN_Msk);
    }
    else
    {
        SET_BIT(SRPWMx->EPWM_SADC1_DIV, SRPWM0_EPWM_SADC1_DIV_EPWM_SADC1_DIV_EN_Msk);
    }
}

/**
 * @brief disables the divide function of the trigger signal sent to the adc
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of A of B is required for the adc
 * as the trigger
 */
void SRPWM_disableADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC0_DIV, SRPWM0_EPWM_SADC0_DIV_EPWM_SADC0_DIV_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC1_DIV, SRPWM0_EPWM_SADC1_DIV_EPWM_SADC1_DIV_EN_Msk);
    }
}

/**
 * @brief select the divider factor of the trigger signal to be sent to the adc
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of A of B is required for the adc
 * as the trigger
 * @param preScaleCount the frequency division factor of the trigger signal sent to the adc
 */
void SRPWM_setADCTriggerEventPrescale(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType,
                                      uint8_t preScaleCount)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        MODIFY_REG(SRPWMx->EPWM_SADC0_DIV, SRPWM0_EPWM_SADC0_DIV_EPWM_SADC0_DIV_Msk, preScaleCount);
    }
    else
    {
        MODIFY_REG(SRPWMx->EPWM_SADC1_DIV, SRPWM0_EPWM_SADC1_DIV_EPWM_SADC1_DIV_Msk, preScaleCount);
    }
}

/**
 * @brief enable the multiplication function of the signal sent to the adc after it is divided
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of 1 of 2 is required for the adc
 * as the trigger
 */
void SRPWM_enableADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        SET_BIT(SRPWMx->EPWM_SADC0_MULTI, SRPWM0_EPWM_SADC0_MULTI_EPWM_SADC0_MULTI_EN_Msk);
    }
    else
    {
        SET_BIT(SRPWMx->EPWM_SADC1_MULTI, SRPWM0_EPWM_SADC1_MULTI_EPWM_SADC1_MULTI_EN_Msk);
    }
}

/**
 * @brief disable the multiplication function of the signal sent to the adc after it is divided
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of 1 of 2 is required for the adc
 * as the trigger
 */
void SRPWM_disableADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC0_MULTI, SRPWM0_EPWM_SADC0_MULTI_EPWM_SADC0_MULTI_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SRPWMx->EPWM_SADC1_MULTI, SRPWM0_EPWM_SADC1_MULTI_EPWM_SADC1_MULTI_EN_Msk);
    }
}

/**
 * @brief select the multiplication factor of the signal after the trigger signal sent to the adc is divided
 *
 * @param SRPWMx select the specified srpwm
 * @param adcSOCType each pwm block can give the adc two trigger sync signals a choice of 1 of 2 is required for the adc
 * as the trigger
 * @param multi the frequency multiplier of the trigger signal sent to the adc
 */
void SRPWM_setADCTriggerFreqMulti(SRPWM_Type *SRPWMx, SRPWM_ADCStartOfConversionType adcSOCType, uint16_t multi)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    if (adcSOCType == SRPWM_SOC_A)
    {
        MODIFY_REG(SRPWMx->EPWM_SADC0_MULTI, SRPWM0_EPWM_SADC0_MULTI_EPWM_SADC0_MULTI_Msk, multi);
    }
    else
    {
        MODIFY_REG(SRPWMx->EPWM_SADC1_MULTI, SRPWM0_EPWM_SADC1_MULTI_EPWM_SADC1_MULTI_Msk, multi);
    }
}

/**
 * @brief the synchronization signal(spwmcom sync in 0/1) is selected for each spwm module(spwm sync out 0/1) via the
 * spwmcom module
 *
 * @param srcSync select the sync signal 0 or 1 in detail in sync signal
 * @param dstSyncTypeIn select the synchronization signal input type for the destination srpwm
 *      - SRPWM_SYNC0
 *      - SRPWM_SYNC1
 * @param dstChannel
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 */
void SRPWMCOM_selectSyncToSRPWM(SRPWMCOM_SRPWM_SYNCOUT srcSync, SRPWM_SyncType dstSyncTypeIn, uint16_t dstChannel)
{
    assert_param(IS_GET_SRPWM_CHANNEL(dstChannel));

    if (dstSyncTypeIn != SRPWM_SYNC0)
    {
        MODIFY_REG(SRPWMCOM->MEPWM_SYNC_SEL[POSITION_VAL(dstChannel)],
                   SRPWMCOM_MEPWM_SYNC_SEL_MEPWM_SYNCIN1_SEL_Msk,
                   (uint32_t)srcSync << SRPWMCOM_MEPWM_SYNC_SEL_MEPWM_SYNCIN1_SEL_Pos);
    }
    else
    {
        MODIFY_REG(SRPWMCOM->MEPWM_SYNC_SEL[POSITION_VAL(dstChannel)],
                   SRPWMCOM_MEPWM_SYNC_SEL_MEPWM_SYNCIN0_SEL_Msk,
                   (uint32_t)srcSync << SRPWMCOM_MEPWM_SYNC_SEL_MEPWM_SYNCIN0_SEL_Pos);
    }
}

/**
 * @brief select the output of sync signal 0
 *
 * @param SRPWMx select the specified srpwm
 * @param srcSync select the specified sync signal
 *      - SRPWM_ALLEVT_ZERO_EVT
 *      - SRPWM_ALLEVT_PRD_EVT
 *      - SRPWM_ALLEVT_SCMPA_UP_EVT
 *      - SRPWM_ALLEVT_SCMPB_UP_EVT
 *      - SRPWM_ALLEVT_SCMPC_UP_EVT
 *      - SRPWM_ALLEVT_SCMPD_UP_EVT
 *      - SRPWM_ALLEVT_SCMPA_DOWN_EVT
 *      - SRPWM_ALLEVT_SCMPB_DOWN_EVT
 *      - SRPWM_ALLEVT_SCMPC_DOWN_EVT
 *      - SRPWM_ALLEVT_SCMPD_DOWN_EVT
 *      - SRPWM_ALLEVT_CMPA_UP_EVT
 *      - SRPWM_ALLEVT_CMPB_UP_EVT
 *      - SRPWM_ALLEVT_CMPC_UP_EVT
 *      - SRPWM_ALLEVT_CMPD_UP_EVT
 *      - SRPWM_ALLEVT_CMPA_DOWN_EVT
 *      - SRPWM_ALLEVT_CMPB_DOWN_EVT
 *      - SRPWM_ALLEVT_CMPC_DOWN_EVT
 *      - SRPWM_ALLEVT_CMPD_DOWN_EVT
 *      - SRPWM_ALLEVT_FPP_FAULT_POS0
 *      - SRPWM_ALLEVT_FPP_FAULT_POS1
 *      - SRPWM_ALLEVT_FPP_FAULT_POS2
 *      - SRPWM_ALLEVT_FPP_FAULT_POS3
 *      - SRPWM_ALLEVT_SYNC0
 *      - SRPWM_ALLEVT_SYNC1
 *      - SRPWM_ALLEVT_BURST_OVER
 *      - SRPWM_ALLEVT_B_NEG
 *      - SRPWM_ALLEVT_B_POS
 *      - SRPWM_ALLEVT_A_NEG
 *      - SRPWM_ALLEVT_A_POS
 *      - SRPWM_ALLEVT_SW_EVT
 * @param dstSyncTypeOut select the specified sync signal output type
 */
void SRPWM_selectSyncOut(SRPWM_Type *SRPWMx, uint32_t srcSync, SRPWM_SyncType dstSyncTypeOut)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_ALLEVT(srcSync));

    if (dstSyncTypeOut == SRPWM_SYNC0)
    {
        MODIFY_REG(SRPWMx->EPWM_SYNCOUT, SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT0_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcSync) << SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT0_SEL_Pos);
    }
    else
    {
        MODIFY_REG(SRPWMx->EPWM_SYNCOUT, SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT1_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcSync) << SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT1_SEL_Pos);
    }
}

/**
 * @brief select the delay of sync signal
 *
 * @param SRPWMx select the specified srpwm
 * @param syncTypeOut select the specified sync signal output type
 * @param delay delay value
 */
void SRPWM_selectSyncOutDly(SRPWM_Type *SRPWMx, SRPWM_SyncType syncTypeOut, uint8_t delay)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_OEP_SYNC_DLY(delay));

    if (syncTypeOut == SRPWM_SYNC0)
    {
        MODIFY_REG(SRPWMx->EPWM_SYNCOUT,
                   SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT0_SEL_Msk,
                   (uint32_t)delay << SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT0_DLY_Pos);
    }
    else
    {
        MODIFY_REG(SRPWMx->EPWM_SYNCOUT,
                   SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT1_SEL_Msk,
                   (uint32_t)delay << SRPWM0_EPWM_SYNCOUT_EPWM_SYNCOUT1_DLY_Pos);
    }
}

/**
 * @brief select the sync signal output to xbar
 *
 * @param srcSync the specified output signal
 * @param dstXbarNumber the specified xbar number
 */
void SRPWMCOM_selectSyncToXBAR(SRPWMCOM_SRPWM_SYNCOUT srcSync, SRPWMCOM_XBARx dstXbarNumber)
{
    WRITE_REG(SRPWMCOM->MEPWM_XBAR_SYNC_SEL[dstXbarNumber], srcSync);
}

/**
 * @brief set the trigger signal of the dac
 *
 * @param channel select the specified srpwm
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param srcEvent select the specified event
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 * @param dstDacNumber select the ACMP number
 * @return * void
 */
void SRPWM_setDACTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_DACx dstDacNumber)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));
    assert_param(IS_SRPWM_GET_OUT_EVT(srcEvent));

    WRITE_REG(SRPWMCOM->MEPWM_DACC_SYNC_SEL[dstDacNumber], POSITION_VAL(channel));

    switch (channel)
    {
    case SRPWM_CHANNEL_0:
        MODIFY_REG(SRPWM0->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_1:
        MODIFY_REG(SRPWM1->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_2:
        MODIFY_REG(SRPWM2->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_3:
        MODIFY_REG(SRPWM3->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_4:
        MODIFY_REG(SRPWM4->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_5:
        MODIFY_REG(SRPWM5->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_6:
        MODIFY_REG(SRPWM6->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_7:
        MODIFY_REG(SRPWM7->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_8:
        MODIFY_REG(SRPWM8->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_9:
        MODIFY_REG(SRPWM9->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_10:
        MODIFY_REG(SRPWM10->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_11:
        MODIFY_REG(SRPWM11->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_BDAC_SYNC_SEL_Pos);
        break;
    }
}

/**
 * @brief set the trigger signal of the ACMP
 *
 * @param channel select the specified srpwm
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param srcEvent select the specified event
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 * @param dstAcmpNumber select the ACMP number
 * @return * void
 */
void SRPWM_setACMPTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_ACMPx dstAcmpNumber)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));
    assert_param(IS_SRPWM_GET_OUT_EVT(srcEvent));

    MODIFY_REG(SRPWMCOM->MEPWM_CMPC_SYNC_SEL[dstAcmpNumber],
               (uint32_t)SRPWMCOM_MEPWM_CMPC_SYNC_SEL_MEPWM_CMPC_SYNC_SEL_Msk,
               (uint32_t)POSITION_VAL(channel) << SRPWMCOM_MEPWM_CMPC_SYNC_SEL_MEPWM_CMPC_SYNC_SEL_Pos);

    switch (channel)
    {
    case SRPWM_CHANNEL_0:
        MODIFY_REG(SRPWM0->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_1:
        MODIFY_REG(SRPWM1->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_2:
        MODIFY_REG(SRPWM2->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_3:
        MODIFY_REG(SRPWM3->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_4:
        MODIFY_REG(SRPWM4->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_5:
        MODIFY_REG(SRPWM5->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_6:
        MODIFY_REG(SRPWM6->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_7:
        MODIFY_REG(SRPWM7->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_8:
        MODIFY_REG(SRPWM8->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_9:
        MODIFY_REG(SRPWM9->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_10:
        MODIFY_REG(SRPWM10->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;

    case SRPWM_CHANNEL_11:
        MODIFY_REG(SRPWM11->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_SYNC_SEL_Pos);
        break;
    }
}

/**
 * @brief select the trigger signal of the ACMP blanking
 *
 * @param channel select the specified srpwm
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 * @param srcEvent select the specified event
 *      - SRPWM_OUTEVT_SYNC_ZERO_EVT
 *      - SRPWM_OUTEVT_SYNC_PRD_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_CMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_UP_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPA_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPB_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPC_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_SCMPD_DOWN_EVT
 *      - SRPWM_OUTEVT_SYNC_BURST_A_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_A_POS
 *      - SRPWM_OUTEVT_SYNC_BURST_B_NEG
 *      - SRPWM_OUTEVT_SYNC_BURST_B_POS
 *      - SRPWM_OUTEVT_SYNC_TIMER_0SYNC
 *      - SRPWM_OUTEVT_SYNC_TIMER_1SYNC
 * @param dstAcmpNumber select the ACMP number
 * @return * void
 */
void SRPWM_setACMPBlankingTrigger(uint16_t channel, uint32_t srcEvent, SRPWMCOM_ACMPx dstAcmpNumber)
{
    assert_param(IS_GET_SRPWM_CHANNEL(channel));
    assert_param(IS_SRPWM_GET_OUT_EVT(srcEvent));

    MODIFY_REG(SRPWMCOM->MEPWM_CMPC_SYNC_SEL[dstAcmpNumber],
               (uint32_t)SRPWMCOM_MEPWM_CMPC_SYNC_SEL_MEPWM_CMPC_BLK_SEL_Msk,
               (uint32_t)POSITION_VAL(channel) << SRPWMCOM_MEPWM_CMPC_SYNC_SEL_MEPWM_CMPC_BLK_SEL_Pos);
    switch (channel)
    {
    case SRPWM_CHANNEL_0:
        MODIFY_REG(SRPWM0->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_1:
        MODIFY_REG(SRPWM1->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_2:
        MODIFY_REG(SRPWM2->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_3:
        MODIFY_REG(SRPWM3->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_4:
        MODIFY_REG(SRPWM4->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_5:
        MODIFY_REG(SRPWM5->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_6:
        MODIFY_REG(SRPWM6->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_7:
        MODIFY_REG(SRPWM7->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_8:
        MODIFY_REG(SRPWM8->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_9:
        MODIFY_REG(SRPWM9->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_10:
        MODIFY_REG(SRPWM10->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;

    case SRPWM_CHANNEL_11:
        MODIFY_REG(SRPWM11->CMPC_BDAC_TRG,
                   SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Msk,
                   (uint32_t)POSITION_VAL(srcEvent) << SRPWM0_CMPC_BDAC_TRG_CMPC_BLK_SEL_Pos);
        break;
    }
}

/**
 * @brief enable Multiple Spwm Module Configuration Registers Force Synchronous Updates
 *
 * @param channelMask
 *      - SRPWM_CHANNEL_0
 *      - SRPWM_CHANNEL_1
 *      - SRPWM_CHANNEL_2
 *      - SRPWM_CHANNEL_3
 *      - SRPWM_CHANNEL_4
 *      - SRPWM_CHANNEL_5
 *      - SRPWM_CHANNEL_6
 *      - SRPWM_CHANNEL_7
 *      - SRPWM_CHANNEL_8
 *      - SRPWM_CHANNEL_9
 *      - SRPWM_CHANNEL_10
 *      - SRPWM_CHANNEL_11
 *      - SRPWM_CHANNEL_ALL
 */
void SRPWMCOM_forceMultiChannelShadow(uint16_t channelMask)
{
    assert_param(IS_SRPWM_CHANNEL(channelMask));

    SET_BIT(SRPWMCOM->SHD_MULTICFG_UPT, channelMask);
}

/**
 * @brief multiple configuration registers of an enabling specified module are updated synchronously
 *
 * @param SRPWMx select the specified srpwm
 * @param regMask select the specified register
 *      - SRPWM_SHD_MULTI_SYNC_PRD
 *      - SRPWM_SHD_MULTI_SYNC_PHASE
 *      - SRPWM_SHD_MULTI_SYNC_CMP
 *      - SRPWM_SHD_MULTI_SYNC_SCMP
 *      - SRPWM_SHD_MULTI_SYNC_PG
 *      - SRPWM_SHD_MULTI_SYNC_DB
 *      - SRPWM_SHD_MULTI_SYNC_BURST
 */
void SRPWM_enableShadowMultiRegSync(SRPWM_Type *SRPWMx, uint8_t regMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SHADOW_MULTICFG_REG(regMask));

    SET_BIT(SRPWMx->PSTP_MULTICFG, regMask);
}

/**
 * @brief multiple configuration registers of an disabling specified module are updated synchronously
 *
 * @param SRPWMx select the specified srpwm
 * @param regMask select the specified register
 *      - SRPWM_SHD_MULTI_SYNC_PRD
 *      - SRPWM_SHD_MULTI_SYNC_PHASE
 *      - SRPWM_SHD_MULTI_SYNC_CMP
 *      - SRPWM_SHD_MULTI_SYNC_SCMP
 *      - SRPWM_SHD_MULTI_SYNC_PG
 *      - SRPWM_SHD_MULTI_SYNC_DB
 *      - SRPWM_SHD_MULTI_SYNC_BURST
 */
void SRPWM_disableShadowMultiRegSync(SRPWM_Type *SRPWMx, uint8_t regMask)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));
    assert_param(IS_SRPWM_SHADOW_MULTICFG_REG(regMask));

    CLEAR_BIT(SRPWMx->PSTP_MULTICFG, regMask);
}

/**
 * @brief enables the shadow function of the specified module
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_enableMultiShadowWaitPrd(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->PSTP_MULTICFG, SRPWM0_PSTP_MULTICFG_SHD_MULTICFG_ALIGN_EN_Msk);
}

/**
 * @brief incapacitation specifies the shadow function of the module
 *
 * @param SRPWMx select the specified srpwm
 */
void SRPWM_disableMultiShadowWaitPrd(SRPWM_Type *SRPWMx)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    CLEAR_BIT(SRPWMx->PSTP_MULTICFG, SRPWM0_PSTP_MULTICFG_SHD_MULTICFG_ALIGN_EN_Msk);
}

/**
 * @brief gets the shadow update completion status for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param reg select the specified register
 * @return FlagStatus
 */
FlagStatus SRPWM_getShadowUpdateStatus(SRPWM_Type *SRPWMx, SRPWM_ShadowUpdateStatus reg)
{
    FlagStatus ret = RESET;

    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    ret = DRV_IS_BIT_SET(SRPWMx->EPWM_UPT_DONE, reg) ? SET : RESET;
    return ret;
}

/**
 * @brief clears the shadow update completion status for the specified module
 *
 * @param SRPWMx select the specified srpwm
 * @param reg select the specified register
 */
void SRPWM_clearShadowUpdateStatus(SRPWM_Type *SRPWMx, SRPWM_ShadowUpdateStatus reg)
{
    assert_param(IS_SRPWM_PERIPH(SRPWMx));

    SET_BIT(SRPWMx->EPWM_UPT_DONE, reg);
}

/* end */
