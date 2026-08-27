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

/* include -----------------------------------------------------------*/
#include "et6x_etimer.h"
#include "et6x_crg.h"

/* typedef -----------------------------------------------------------*/
/* macro -------------------------------------------------------------*/
#define IS_ETIMER_CHANNEL(CHANNEL)        (((CHANNEL) != 0x00UL) && (((CHANNEL) & 0xC000UL) == 0x00UL))
#define IS_GET_ETIMER_CHANNEL(CHANNEL) \
        (((CHANNEL) == ETIMER_CHANNEL_0) || \
         ((CHANNEL) == ETIMER_CHANNEL_1) || \
         ((CHANNEL) == ETIMER_CHANNEL_2) || \
         ((CHANNEL) == ETIMER_CHANNEL_3) || \
         ((CHANNEL) == ETIMER_CHANNEL_4) || \
         ((CHANNEL) == ETIMER_CHANNEL_5) || \
         ((CHANNEL) == ETIMER_CHANNEL_6) || \
         ((CHANNEL) == ETIMER_CHANNEL_7) || \
         ((CHANNEL) == ETIMER_CHANNEL_8) || \
         ((CHANNEL) == ETIMER_CHANNEL_9) || \
         ((CHANNEL) == ETIMER_CHANNEL_10) || \
         ((CHANNEL) == ETIMER_CHANNEL_11) || \
         ((CHANNEL) == ETIMER_CHANNEL_12) || \
         ((CHANNEL) == ETIMER_CHANNEL_13))
#define IS_ETIMER_DMA_CHANNEL(CHANNEL)    (((CHANNEL) != 0x00UL) && (((CHANNEL) & 0xF0UL) == 0x00))

#define ETIMER_LOADMODE_PERIOD_SHADOW_CMD_POS       (8UL)
#define ETIMER_LOADMODE_PERIOD_SHADOW_CMD_MASK      (1UL << ETIMER_LOADMODE_PERIOD_SHADOW_CMD_POS)
#define ETIMER_LOADMODE_COMPARE_SHADOW_CMD_POS      (9UL)
#define ETIMER_LOADMODE_COMPARE_SHADOW_CMD_MASK     (1UL << ETIMER_LOADMODE_COMPARE_SHADOW_CMD_POS)
#define ETIMER_LOADMODE_EVENTCNT_SHADOW_CMD_POS     (10UL)
#define ETIMER_LOADMODE_EVENTCNT_SHADOW_CMD_MASK    (1UL << ETIMER_LOADMODE_EVENTCNT_SHADOW_CMD_POS)

/* variables ---------------------------------------------------------*/
/* function prototypes -----------------------------------------------*/
/* Private functions ---------------------------------------------------------*/

/**
 * @brief Deinit ETIMER peripheral
 *
 */
void ETIMER_deinit(void)
{
//    CRG_PeriphReset(CRG_SRST_ETIM);
}

/**
 * @brief Initializes ETIMER time base initial structure
 *
 * @param initStruct: point to a ETIMER_TimeBaseInitParam
 * structure that contains time base configuration information for the specifed
 * ETIMER peripheral
 */
void ETIMER_initTimeBaseStruct(ETIMER_TimeBaseInitParam *initStruct)
{
    initStruct->channelMask    = 0;
    initStruct->period         = 0;
    initStruct->periodShadowEn = DISABLE;
    initStruct->prescaler      = ETIMER_CLK_DIV1;
    initStruct->phase          = 0;
}

/**
 * @brief Initializes the ETIMER Time Base Unit Peripheral
 *
 * @param init: point to a ETIMER_TimeBaseInitParam
 * structure that contains time base configuration information for the specifed
 * ETIMER peripheral
 */
void ETIMER_initTimeBase(ETIMER_TimeBaseInitParam *init)
{
    uint8_t  pos     = 0;
    uint32_t posMask = 0;

    assert_param(IS_ETIMER_CHANNEL(init->channelMask));

    for (pos = 0; pos < ETIMER_CHANNEL_NUM; pos++)
    {
        posMask = BIT_MASK(pos);
        if (DRV_IS_BIT_SET(init->channelMask, posMask))
        {
            MODIFY_REG(ETIMER->CORE[pos].PWM_CTRL,
                       ETIMER_CORE_PWM_CTRL_CLKDIV_FAC_Msk | ETIMER_LOADMODE_PERIOD_SHADOW_CMD_MASK,
                       (uint32_t)init->prescaler << ETIMER_CORE_PWM_CTRL_CLKDIV_FAC_Pos |
                       (uint32_t)init->periodShadowEn << ETIMER_LOADMODE_PERIOD_SHADOW_CMD_POS);

            WRITE_REG(ETIMER->CORE[pos].TIMER_CYC, init->period);

            WRITE_REG(ETIMER->CORE[pos].CTRPHS, init->phase);
        }
    }
}

/**
 * @brief
 *
 * @param initStruct
 * @return * void
 */
void ETIMER_initOCStruct(ETIMER_OCInitParam *initStruct)
{
    initStruct->channelMask     = 0;
    initStruct->compareA        = 0;
    initStruct->compareB        = 0;
    initStruct->compareShadowEn = DISABLE;
    initStruct->compareMode     = ETIMER_COMPAREMODE_COMPAREA;
}

/**
 * @brief
 *
 * @param init
 * @return * void
 */
void ETIMER_initOC(ETIMER_OCInitParam *init)
{
    uint8_t  pos     = 0;
    uint32_t posMask = 0;

    for (pos = 0; pos < ETIMER_CHANNEL_NUM; pos++)
    {
        posMask = BIT_MASK(pos);
        if (DRV_IS_BIT_SET(init->channelMask, posMask))
        {
            /* set the compare A and B */
            WRITE_REG(ETIMER->CORE[pos].COMPA, init->compareA);
            WRITE_REG(ETIMER->CORE[pos].COMPB, init->compareB);
            /* set the compare mode */
            MODIFY_REG(ETIMER->CORE[pos].PWM_CTRL,
                       ETIMER_CORE_PWM_CTRL_COMP_MODE_Msk | ETIMER_LOADMODE_COMPARE_SHADOW_CMD_MASK,
                       (uint32_t)init->compareMode << ETIMER_CORE_PWM_CTRL_COMP_MODE_Pos |
                       (uint32_t)init->compareShadowEn << ETIMER_LOADMODE_COMPARE_SHADOW_CMD_POS);
        }
    }
}

void ETIMER_initDBStruct(ETIMER_DBInitParam *initStruct)
{
    initStruct->a.risingDelay          = 0;
    initStruct->a.fallingDelay         = 0;
    initStruct->a.selComplementChannel = DISABLE;
    initStruct->a.selRisingDelay       = DISABLE;
    initStruct->a.selFallingDelay      = DISABLE;
    initStruct->a.selOutputState       = ETIMER_DB_OUTPUT_STATE_NONE;

    initStruct->b.risingDelay          = 0;
    initStruct->b.fallingDelay         = 0;
    initStruct->b.selComplementChannel = DISABLE;
    initStruct->b.selRisingDelay       = DISABLE;
    initStruct->b.selFallingDelay      = DISABLE;
    initStruct->b.selOutputState       = ETIMER_DB_OUTPUT_STATE_NONE;
}

void ETIMER_initDB(uint32_t channelGroup, ETIMER_DBInitParam *init)
{
    //todo 断言
    MODIFY_REG(ETIMER->OUT[channelGroup].DB_SEL, ETIMER_OUT_DB_SEL_DB_S0A_Msk |
               ETIMER_OUT_DB_SEL_DB_S1A_Msk |
               ETIMER_OUT_DB_SEL_DB_S2A_Msk |
               ETIMER_OUT_DB_SEL_DB_S3A_Msk |
               ETIMER_OUT_DB_SEL_DB_S0B_Msk |
               ETIMER_OUT_DB_SEL_DB_S1B_Msk |
               ETIMER_OUT_DB_SEL_DB_S2B_Msk |
               ETIMER_OUT_DB_SEL_DB_S3B_Msk,
               (uint32_t)init->a.selComplementChannel << ETIMER_OUT_DB_SEL_DB_S0A_Pos |
               (uint32_t)init->a.selRisingDelay << ETIMER_OUT_DB_SEL_DB_S1A_Pos |
               (uint32_t)init->a.selFallingDelay << ETIMER_OUT_DB_SEL_DB_S2A_Pos |
               (uint32_t)init->a.selOutputState << ETIMER_OUT_DB_SEL_DB_S3A_Pos |
               (uint32_t)init->b.selComplementChannel << ETIMER_OUT_DB_SEL_DB_S0B_Pos |
               (uint32_t)init->b.selRisingDelay << ETIMER_OUT_DB_SEL_DB_S1B_Pos |
               (uint32_t)init->b.selFallingDelay << ETIMER_OUT_DB_SEL_DB_S2B_Pos |
               (uint32_t)init->b.selOutputState << ETIMER_OUT_DB_SEL_DB_S3B_Pos);
    WRITE_REG(ETIMER->OUT[channelGroup].APOS_DLY, (uint32_t)init->a.risingDelay);
    WRITE_REG(ETIMER->OUT[channelGroup].ANEG_DLY, (uint32_t)init->a.fallingDelay);
    WRITE_REG(ETIMER->OUT[channelGroup].BPOS_DLY, (uint32_t)init->b.risingDelay);
    WRITE_REG(ETIMER->OUT[channelGroup].BNEG_DLY, (uint32_t)init->b.fallingDelay);
}

/**
 * @brief enable the specified etimer
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enable(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN0, channelMask << ETIMER_EN0_ETIM_EN_Pos);
}

/**
 * @brief disable the specified etimer
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disable(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN0, channelMask << ETIMER_EN0_ETIM_EN_Pos);
}

/**
 * @brief enable specifies the etimer module counter
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enableTimer(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN0, channelMask << ETIMER_EN0_TIMER_EN_Pos);
}

/**
 * @brief disable specifies the etimer module counter
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disableTimer(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN0, channelMask << ETIMER_EN0_TIMER_EN_Pos);
}

/**
 * @brief enable  the specified etimer module pwm function
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enablePWM(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN1, channelMask << ETIMER_EN1_PWM_EN_Pos);
}

/**
 * @brief enable  the specified etimer module pwm function
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disablePWM(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN1, channelMask << ETIMER_EN1_PWM_EN_Pos);
}

/**
 * @brief sets the period value that specifies the etimer module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param period: timer period.
 *              range:0x0~0xFFFFFFFF
 */
void ETIMER_setPeriod(uint32_t channel, uint32_t period)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    WRITE_REG(ETIMER->CORE[POSITION_VAL(channel)].TIMER_CYC, period);
}

/**
 * @brief sets the comparison value a for the specified etimer module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param compare: compare output value
 *                  range:0x0~0xFFFFFFFF
 */
void ETIMER_setCompareA(uint32_t channel, uint32_t compare)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    WRITE_REG(ETIMER->CORE[POSITION_VAL(channel)].COMPA, compare);
}

/**
 * @brief sets the comparison value b of the specified etimer module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param compare: compare output value
 *                  range:0x0~0xFFFFFFFF
 */
void ETIMER_setCompareB(uint32_t channel, uint32_t compare)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    WRITE_REG(ETIMER->CORE[POSITION_VAL(channel)].COMPB, compare);
}

/**
 * @brief confirm that the shadow load of the comparison value is valid if the ab comparison value is modified and
 * shadow loading of the comparison value is enabled you need to call this api to confirm
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_confirmCompareShadow(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_UPDATE_VLD_Msk);
}

/**
 * @brief gets the counter value for the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @return uint32_t: get etimer counter value
 */
uint32_t ETIMER_getCount(uint32_t channel)
{
    uint32_t regValue = 0;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_CNTLK_Msk);

    regValue = READ_REG(ETIMER->CORE[POSITION_VAL(channel)].LKCNT_RPT);

    return regValue;
}

/**
 * @brief clears the counter value for the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_clearCount(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_TCLR_Msk);
}

/**
 * @brief enables the specified interrupt function of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param interruptFlagMask: specified etimer interrupt source
 *      @arg ETIMER_IT_PWM_FAULT_ONE_SHOT
 *      @arg ETIMER_IT_PWM_FAULT_CBC
 *      @arg ETIMER_IT_FAULT_OVERFLOW
 *      @arg ETIMER_IT_COMPAB_CFG_ERR
 *      @arg ETIMER_IT_COMPA
 *      @arg ETIMER_IT_COMPB
 *      @arg ETIMER_IT_PERIOD
 *      @arg ETIMER_IT_COUNTER_OVERFLOW
 *      @arg ETIMER_IT_CAP_EVT0
 *      @arg ETIMER_IT_CAP_EVT1
 *      @arg ETIMER_IT_CAP_EVT2
 *      @arg ETIMER_IT_CAP_EVT3
 */
void ETIMER_enableInterrupt(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_EN, interruptFlagMask);
}

/**
 * @brief disable the specified interrupt function of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 */
void ETIMER_disableInterrupt(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    CLEAR_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_EN, interruptFlagMask);
}

/**
 * @brief enable interrupt masking
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 */
void ETIMER_setInterruptMask(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_MASK, interruptFlagMask);
}

/**
 * @brief disable interrupt masking
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 */
void ETIMER_clearInterruptMask(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    CLEAR_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_MASK, interruptFlagMask);
}

/**
 * @brief forces the triggering of a specified interrupt for the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 */
void ETIMER_forceInterrupt(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_FORCE_IND, interruptFlagMask);
}

/**
 * @brief clears the interrupt pending status flag for the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 */
void ETIMER_clearInterruptStatus(uint32_t channel, uint16_t interruptFlagMask)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_CLR, interruptFlagMask);
}

/**
 * @brief gets the break status of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 * @return ITStatus
 *         SET: the specified etimer interrupt occurs
 *         RESET: the specified etimer interrupt does not occur
 */
ITStatus ETIMER_getInterruptStatus(uint32_t channel, uint16_t interruptFlag)
{
    ITStatus bitStatus = RESET;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    bitStatus = DRV_IS_BIT_SET(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_STATUS_RPT, interruptFlag) ? SET : RESET;

    return bitStatus;
}

/**
 * @brief gets the interrupt raw status of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param IT: specified etimer interrupt source
 * @return ITStatus
 *         SET: the specified etimer interrupt occurs
 *         RESET: the specified etimer interrupt does not occur
 */
ITStatus ETIMER_getInterruptStatusRaw(uint32_t channel, uint16_t interruptFlag)
{
    ITStatus bitStatus = RESET;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    bitStatus = DRV_IS_BIT_SET(ETIMER->CMN_INT[POSITION_VAL(channel)].INT_RAW_RPT, interruptFlag) ? SET : RESET;

    return bitStatus;
}

/**
 * @brief ICStruct Init
 *
 * @param initStruct: pointer to capture initial structure
 */
void ETIMER_initICStruct(ETIMER_ICInitParam *initStruct)
{
    initStruct->channelMask       = 0;
    initStruct->capPrescaler      = ETIMER_CAP_CLK_DIV1;
    initStruct->capInputSrcSel    = ETIMER_CAPTURE_INPUT_SRC_INXB0;
    initStruct->cap0EdgeSel       = ETIMER_CAPTURE_EDGE_RISING;
    initStruct->cap0TimeStampMode = ETIMER_CAPTURE_TIMESTAMP_MODE_ABSOLUTE;
    initStruct->cap1EdgeSel       = ETIMER_CAPTURE_EDGE_RISING;
    initStruct->cap1TimeStampMode = ETIMER_CAPTURE_TIMESTAMP_MODE_ABSOLUTE;
    initStruct->cap2EdgeSel       = ETIMER_CAPTURE_EDGE_RISING;
    initStruct->cap2TimeStampMode = ETIMER_CAPTURE_TIMESTAMP_MODE_ABSOLUTE;
    initStruct->cap3EdgeSel       = ETIMER_CAPTURE_EDGE_RISING;
    initStruct->cap3TimeStampMode = ETIMER_CAPTURE_TIMESTAMP_MODE_ABSOLUTE;
    initStruct->capLoadEn         = DISABLE;
    initStruct->capMode           = ETIMER_CAPTURE_MODE_EVT0_CONTINUOUS;

    initStruct->filterInitNoZeroEn = DISABLE;
    initStruct->filterClkDiv       = 0;
    initStruct->filterThresh       = 0;
    initStruct->filterSampWindows  = 0;
}

/**
 * @brief initialize the input capture IC
 *
 * @param init: pointer to capture initial structure
 */
void ETIMER_initIC(ETIMER_ICInitParam *init)
{
    uint8_t  pos     = 0;
    uint32_t posMask = 0;

    assert_param(IS_ETIMER_CHANNEL(init->channelMask));

    for (pos = 0; pos < ETIMER_CHANNEL_NUM; pos++)
    {
        posMask = BIT_MASK(pos);
        if (DRV_IS_BIT_SET(init->channelMask, posMask))
        {
            MODIFY_REG(ETIMER->CORE[pos].CAP_CTRL, ETIMER_CORE_CAP_CTRL_CAP_PRE_DIV_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP_IN_SRCSEL_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP1_POLAR_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP1_CLR_CNT_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP2_POLAR_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP2_CLR_CNT_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP3_POLAR_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP3_CLR_CNT_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP4_POLAR_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP4_CLR_CNT_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP_LOAD_EN_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP_MODE_Msk |
                       ETIMER_CORE_CAP_CTRL_CAP_STOP_WRAP_Msk,
                       (uint32_t)init->capPrescaler << ETIMER_CORE_CAP_CTRL_CAP_PRE_DIV_Pos |
                       (uint32_t)init->capInputSrcSel << ETIMER_CORE_CAP_CTRL_CAP_IN_SRCSEL_Pos |
                       (uint32_t)init->cap0EdgeSel << ETIMER_CORE_CAP_CTRL_CAP1_POLAR_Pos |
                       (uint32_t)init->cap0TimeStampMode << ETIMER_CORE_CAP_CTRL_CAP1_CLR_CNT_Pos |
                       (uint32_t)init->cap1EdgeSel << ETIMER_CORE_CAP_CTRL_CAP2_POLAR_Pos |
                       (uint32_t)init->cap1TimeStampMode << ETIMER_CORE_CAP_CTRL_CAP2_CLR_CNT_Pos |
                       (uint32_t)init->cap2EdgeSel << ETIMER_CORE_CAP_CTRL_CAP3_POLAR_Pos |
                       (uint32_t)init->cap2TimeStampMode << ETIMER_CORE_CAP_CTRL_CAP3_CLR_CNT_Pos |
                       (uint32_t)init->cap3EdgeSel << ETIMER_CORE_CAP_CTRL_CAP4_POLAR_Pos |
                       (uint32_t)init->cap3TimeStampMode << ETIMER_CORE_CAP_CTRL_CAP4_CLR_CNT_Pos |
                       (uint32_t)init->capLoadEn << ETIMER_CORE_CAP_CTRL_CAP_LOAD_EN_Pos |
                       (uint32_t)init->capMode << ETIMER_CORE_CAP_CTRL_CAP_MODE_Pos);

            MODIFY_REG(ETIMER->CORE[pos].CAP_FILTER, ETIMER_CORE_CAP_FILTER_FILINIT_Msk |
                       ETIMER_CORE_CAP_FILTER_CLKPRESCALE_Msk |
                       ETIMER_CORE_CAP_FILTER_THRESH_Msk |
                       ETIMER_CORE_CAP_FILTER_SAMPWIN_Msk,
                       (uint32_t)init->filterInitNoZeroEn << ETIMER_CORE_CAP_FILTER_FILINIT_Pos |
                       (uint32_t)init->filterClkDiv << ETIMER_CORE_CAP_FILTER_CLKPRESCALE_Pos |
                       (uint32_t)init->filterThresh << ETIMER_CORE_CAP_FILTER_THRESH_Pos |
                       (uint32_t)init->filterSampWindows << ETIMER_CORE_CAP_FILTER_SAMPWIN_Pos);
        }
    }
}

/**
 * @brief enable the capture function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enableCapture(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN1, channelMask << ETIMER_EN1_CAP_EN_Pos);
}

/**
 * @brief disable the capture function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disableCapture(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN1, channelMask << ETIMER_EN1_CAP_EN_Pos);
}

/**
 * @brief enable the input capture filtering function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enableCaptureFilter(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN2, channelMask << ETIMER_EN2_CAP_FILTER_EN_Pos);
}

/**
 * @brief disable the input capture filtering function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disableCaptureFilter(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN2, channelMask << ETIMER_EN2_CAP_FILTER_EN_Pos);
}

/**
 * @brief gets the capture cnt0 of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @return uint32_t: capture counter 0 value
 */
uint32_t ETIMER_getCaptureCnt0(uint32_t channel)
{
    uint32_t regValue = 0;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    regValue = READ_REG(ETIMER->CAP_CNT[POSITION_VAL(channel)].CAP1);

    return regValue;
}

/**
 * @brief gets the capture cnt1 of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @return uint32_t: capture counter 1 value
 */
uint32_t ETIMER_getCaptureCnt1(uint32_t channel)
{
    uint32_t regValue = 0;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    regValue = READ_REG(ETIMER->CAP_CNT[POSITION_VAL(channel)].CAP2);

    return regValue;
}

uint32_t ETIMER_getCaptureCnt2(uint32_t channel)
{
    uint32_t regValue = 0;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    regValue = READ_REG(ETIMER->CAP_CNT[POSITION_VAL(channel)].CAP3);

    return regValue;
}

uint32_t ETIMER_getCaptureCnt3(uint32_t channel)
{
    uint32_t regValue = 0;

    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    regValue = READ_REG(ETIMER->CAP_CNT[POSITION_VAL(channel)].CAP4);

    return regValue;
}

void ETIMER_resetCapture(uint32_t channel)
{
    assert_param(IS_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].CAP_CTRL, ETIMER_CORE_CAP_CTRL_CAP_REARM_Msk);
}

/**
 * @brief FaultStruct Init
 *
 * @param initStruct: pointer to etimer fault initial strcture
 */
void ETIMER_initFaultStruct(ETIMER_FaultInitParam *initStruct)
{
    initStruct->channelMask = 0;
    initStruct->polarity    = ETIMER_FAULT_OUT_POLARITY_LOW;
    initStruct->mode        = ETIMER_FAULT_MODE_CBC;
    initStruct->trigger     = ETIMER_FAULT_TRIGGER_SW;
}

/**
 * @brief specifies the fault initialization of the module
 *
 * @param init: pointer to etimer fault initial strcture
 */
void ETIMER_initFault(ETIMER_FaultInitParam *init)
{
    uint8_t  pos     = 0;
    uint32_t posMask = 0;

    assert_param(IS_ETIMER_CHANNEL(init->channelMask));

    for (pos = 0; pos < ETIMER_CHANNEL_NUM; pos++)
    {
        posMask = BIT_MASK(pos);
        if (DRV_IS_BIT_SET(init->channelMask, posMask))
        {
            /* set fault out polarity */
            MODIFY_REG(ETIMER->CORE[pos].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_OUT_Msk |   /* set fault out polarity */
                       ETIMER_CORE_PWM_CTRL_FAULT_MODE_Msk |                              /* set fault mode */
                       ETIMER_CORE_PWM_CTRL_FAULT_SEL_Msk,                                /* set the fault trigger */
                       (uint32_t)init->polarity << ETIMER_CORE_PWM_CTRL_FAULT_OUT_Pos |
                       (uint32_t)init->mode << ETIMER_CORE_PWM_CTRL_FAULT_MODE_Pos |
                       (uint32_t)init->trigger << ETIMER_CORE_PWM_CTRL_FAULT_SEL_Pos);
        }
    }
}

/**
 * @brief clears the fault state of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_clearFault(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));
    /* clear the one-shot fault */
    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_CLR_Msk);
}

/**
 * @brief forces an exception to the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param state
 *        RESET: clear the fault input by software
 *        SET: force trig the fault by software
 */
void ETIMER_forceInputFault(uint32_t channel, FlagStatus state)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    if (state != RESET)
    {
        /* force trig the fault by software */
        SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_SW_Msk);
    }
    else
    {
        /* clear the fault input by software */
        CLEAR_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_SW_Msk);
    }
}

/**
 * @brief enable the fault function of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_enableFault(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_EN_Msk);
}

/**
 * @brief disable the fault function of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_disableFault(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    CLEAR_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_CORE_PWM_CTRL_FAULT_EN_Msk);
}

/**
 * @brief enable the event output function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_enableEventOut(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    SET_BIT(ETIMER->EN3, channelMask << ETIMER_EN3_EVENT_EN_Pos);
}

/**
 * @brief disable the event output function of the specified module
 *
 * @param channelMask
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 *      @arg ETIMER_CHANNEL_ALL
 */
void ETIMER_disableEventOut(uint32_t channelMask)
{
    assert_param(IS_ETIMER_CHANNEL(channelMask));

    CLEAR_BIT(ETIMER->EN3, channelMask << ETIMER_EN3_EVENT_EN_Pos);
}

/**
 * @brief enable the shadow loading function of the event value of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_enableEventCntShadow(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_LOADMODE_EVENTCNT_SHADOW_CMD_MASK);
}

/**
 * @brief disable the shadow loading function of the event value of the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 */
void ETIMER_disableEventCntShadow(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    CLEAR_BIT(ETIMER->CORE[POSITION_VAL(channel)].PWM_CTRL, ETIMER_LOADMODE_EVENTCNT_SHADOW_CMD_MASK);
}

/**
 * @brief sets the event value for the specified module
 *
 * @param channel
 *      @arg ETIMER_CHANNEL_0
 *      @arg ETIMER_CHANNEL_1
 *      @arg ETIMER_CHANNEL_2
 *      @arg ETIMER_CHANNEL_3
 *      @arg ETIMER_CHANNEL_4
 *      @arg ETIMER_CHANNEL_5
 *      @arg ETIMER_CHANNEL_6
 *      @arg ETIMER_CHANNEL_7
 *      @arg ETIMER_CHANNEL_8
 *      @arg ETIMER_CHANNEL_9
 *      @arg ETIMER_CHANNEL_10
 *      @arg ETIMER_CHANNEL_11
 * @param cnt
 *          range: 0x0 ~ 0xFFFFFFFF
 */
void ETIMER_setEventValue(uint32_t channel, uint32_t cnt)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    WRITE_REG(ETIMER->CORE[POSITION_VAL(channel)].EVENT_CNT, cnt);
}

void ETIMER_enableDMARequest(ETIMER_DMAChannel etimer2dmaChannel, ETIMER_DMARequest src)
{
    MODIFY_REG(ETIMER->CMN[etimer2dmaChannel].DMA, ETIMER_CMN_DMA_DMA_CH_SEL_Msk,
               (uint32_t)src << ETIMER_CMN_DMA_DMA_CH_SEL_Pos);
}

void ETIMER_enableSyncIn(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].SYNC_CTRL, ETIMER_CORE_SYNC_CTRL_SYNC_IN_EN_Msk);
}

void ETIMER_disableSyncIn(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    CLEAR_BIT(ETIMER->CORE[POSITION_VAL(channel)].SYNC_CTRL, ETIMER_CORE_SYNC_CTRL_SYNC_IN_EN_Msk);
}

void ETIMER_selectSyncIn(uint32_t channel, ETIMER_SyncIn syncSrc)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    MODIFY_REG(ETIMER->CORE[POSITION_VAL(channel)].SYNC_CTRL, ETIMER_CORE_SYNC_CTRL_SYNC_SRC_SEL_Msk,
               (uint32_t)syncSrc << ETIMER_CORE_SYNC_CTRL_SYNC_SRC_SEL_Pos);
}

void ETIMER_selectEventToETIMER(uint32_t channel, ETIMER_SyncOutEvent event)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    MODIFY_REG(ETIMER->CORE[POSITION_VAL(channel)].SYNC_CTRL, ETIMER_CORE_SYNC_CTRL_SYNCO_SEL_Msk,
               (uint32_t)event << ETIMER_CORE_SYNC_CTRL_SYNCO_SEL_Pos);
}

void ETIMER_selectEventToADC_DAC_ACMP(uint32_t channel, ETIMER_ADC_DAC_ACMP_SyncOutEvent event)
{
    WRITE_REG(ETIMER->CORE[POSITION_VAL(channel)].EVT_TO_ADC, (uint32_t)event << ETIMER_CORE_EVT_TO_ADC_EVT_TO_ADC_Pos);
}

void ETIMER_selectSyncToDAC(ETIMER_DACx dacNumber, ETIMER_DAC_ACMP_SyncOutSrc src)
{
    MODIFY_REG(ETIMER->DACC, ETIMER_DACC_DACC0_TRG_SEL_Msk << (dacNumber * ETIMER_DACC_DACC1_TRG_SEL_Pos),
               (uint32_t)src << (dacNumber * ETIMER_DACC_DACC1_TRG_SEL_Pos));
}

void ETIMER_selectSyncToACMP(ETIMER_ACMPx acmpNumber, ETIMER_DAC_ACMP_SyncOutSrc src)
{
    MODIFY_REG(ETIMER->CMPC[acmpNumber].DACCTRG_SEL, ETIMER_CMPC_DACCTRG_SEL_SEL_Msk,
               (uint32_t)src << ETIMER_CMPC_DACCTRG_SEL_SEL_Pos);
}

/**
 * @brief 软件强制输出一个事件源
 *
 * @param channel
 * @return * void
 */
void ETIMER_forceSyncOutEvent(uint32_t channel)
{
    assert_param(IS_GET_ETIMER_CHANNEL(channel));

    SET_BIT(ETIMER->CORE[POSITION_VAL(channel)].SYNC_CTRL, ETIMER_CORE_SYNC_CTRL_SW_SYNC_Msk);
}

void ETIMER_selectSyncToXBAROrPin(ETIMER_SyncOutSrc syncSrc)
{
    WRITE_REG(ETIMER->SYNC_OUT, (uint32_t)syncSrc);
}

/******************* end program ***************************/
