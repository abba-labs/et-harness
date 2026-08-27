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
#include "et6x_adc.h"
#include "et6x_crg.h"


#define IS_ADC_PERIPH(PERIPH) \
        (((PERIPH) == ADC0) || ((PERIPH) == ADC1))
#define IS_ADC_VIRTUAL_CHANNEL(CHANNEL)       (((CHANNEL) != 0x00) && (((CHANNEL) & 0x10000) == 0x00))
#define IS_ADC_GET_VIRTUAL_CHANNEL(CHANNEL) \
        (((CHANNEL) == ADC_VIRTUAL_CHANNEL0) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL1) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL2) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL3) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL4) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL5) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL6) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL7) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL8) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL9) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL10) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL11) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL12) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL13) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL14) || \
         ((CHANNEL) == ADC_VIRTUAL_CHANNEL15))

#define IS_ADC_ANALOG_CHANNEL(CHANNEL)        (((CHANNEL) != 0x00))
#define IS_ADC_GET_ANALOG_CHANNEL(CHANNEL) \
        (((CHANNEL) == ADC_ANALOG_CHANNEL0) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL1) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL2) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL3) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL4) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL5) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL6) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL7) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL8) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL9) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL10) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL11) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL12) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL13) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL14) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL15) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL16) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL17) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL18) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL19) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL20) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL21) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL22) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL23) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL24) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL25) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL26) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL27) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL28) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL29) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL30) || \
         ((CHANNEL) == ADC_ANALOG_CHANNEL31))

#define IS_ADC_PREPROCESS_CHANNEL(CHANNEL)    (((CHANNEL) != 0x00) && (((CHANNEL) & 0x1000) == 0x00))
#define IS_ADC_GET_PREPROCESS_CHANNEL(CHANNEL) \
        (((CHANNEL) == ADC_PREPROCESS_CHANNEL0) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL1) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL2) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL3) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL4) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL5) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL6) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL7) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL8) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL9) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL10) || \
         ((CHANNEL) == ADC_PREPROCESS_CHANNEL11))

#define IS_ADC_FILTER_CHANNEL(CHANNEL)        (((CHANNEL) != 0x00) && (((CHANNEL) & 0x100) == 0x00))
#define IS_ADC_GET_FILTER_CHANNEL(CHANNEL) \
        (((CHANNEL) == ADC_FILTER_CHANNEL0) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL1) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL2) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL3) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL4) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL5) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL6) || \
         ((CHANNEL) == ADC_FILTER_CHANNEL7))

#define IS_ADC_DMA_CHANNEL(CHANNEL)           (((CHANNEL) != 0x00) && (((CHANNEL) & 0x10) == 0x00))
#define IS_ADC_GET_DMA_CHANNEL(CHANNEL) \
        (((CHANNEL) == ADC_DMA_CHANNEL0) || \
         ((CHANNEL) == ADC_DMA_CHANNEL1) || \
         ((CHANNEL) == ADC_DMA_CHANNEL2) || \
         ((CHANNEL) == ADC_DMA_CHANNEL3))

#define IS_ADC_SAMPLE_HOLD_TIME(TIME)         ((TIME) < 0x101)
#define IS_ADC_PARAM_13BIT(PARAM)             ((PARAM) < 0x2000)

#define IS_ADC_PREPROCESS_OFFSET(OFFSET)      (((OFFSET) > (-6145)) && ((OFFSET) < 6145))
#define IS_ADC_PREPROCESS_GAIN(GAIN)          ((GAIN) < 0x4000)

#define IS_ADC_NOAVER_COEFF(COEFF)            ((COEFF) < 0x10)

#define IS_ADC_TRIGGER_TIMEOUT(TIME)          (((TIME) >= 0x000A) && ((TIME) <= 0xFFFF))

#define ADC_VC_NUM                      (16)
/* used to determine the type of adc interrupt */
#define ADC_TRIG_TIMEOUT_ITMSK          (1U << 16)
#define ADC_ERROR_ITMSK                 (1U << 17)
#define ADC_FIFO_ITMSK                  (1U << 18)
#define ADC_RESULT_ITMSK                (1U << 19)
#define ADC_WDG_HIGH_THRESHOLD_ITMSK    (1U << 20)
#define ADC_WDG_LOW_THRESHOLD_ITMSK     (1U << 21)

/**
 * @brief resets the specified ADCx
 *
 * @param ADCx
 * @param ADC_InitStruct
 */
void ADC_deinit(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    if (ADCx == ADC0)
    {
//        CRG_PeriphReset(CRG_SRST_ADC0);
    }
    else
    {
//        CRG_PeriphReset(CRG_SRST_ADC1);
    }
}

/**
 * @brief Struct Init
 *
 * @param initStruct
 */
void ADC_initStruct(ADC_InitTypeDef *initStruct)
{
    initStruct->virtualChannelMask = 0;
    initStruct->trigMode           = ADC_TRIGGER_MODE_CONTINUOUS;
    initStruct->trigger            = ADC_TRIGGER_NONE;
    initStruct->sampleTime         = 0;
    initStruct->preResultAlign     = ADC_RESULT_ALIGN_RIGHT;
    initStruct->filterResultAlign  = ADC_RESULT_ALIGN_RIGHT;
    initStruct->preFifoModeEn      = DISABLE;
    initStruct->filterFifoModeEn   = DISABLE;
    initStruct->preFifoDepth       = 16;
    initStruct->filterFifoDepth    = 16;
}

/**
 * @brief initializes the specified virtual channel for the specified module
 * mainly initialize sampling mode trigger mode trigger source
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param initStruct
 *      virtualChannel
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 *      @arg ADC_VIRTUAL_CHANNELALL
 */
void ADC_init(ADC_Type *ADCx, ADC_InitTypeDef *initStruct)
{
    uint8_t pos = 0;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(initStruct->virtualChannelMask));

    for (pos = 0; pos < ADC_VC_NUM; pos++)
    {
        if (DRV_IS_BIT_SET(initStruct->virtualChannelMask, BIT_MASK(pos)))
        {
            /* configure the trigger mode and trigger source */
            MODIFY_REG(ADCx->VC_CTL[pos].VC_CTL,
                       ADC0_VC_CTL_VC_CTL_SARC_VC_TRIG_MODE_Msk | ADC0_VC_CTL_VC_CTL_SARC_VC_TRIG_SEL_Msk,
                       (uint32_t)initStruct->trigMode << ADC0_VC_CTL_VC_CTL_SARC_VC_TRIG_MODE_Pos |
                       (uint32_t)initStruct->trigger << ADC0_VC_CTL_VC_CTL_SARC_VC_TRIG_SEL_Pos);
            /* 配置采样窗口 */
            MODIFY_REG(ADCx->VC_CTL[pos].VC_CTL,
                       ADC0_VC_CTL_VC_CTL_SARC_VC_SPLTIME_Msk,
                       (uint32_t)initStruct->sampleTime << ADC0_VC_CTL_VC_CTL_SARC_VC_SPLTIME_Pos);
            /* 配置用户预处理和滤波后的FIFO模式 */
            MODIFY_REG(ADCx->FIFO_VC_SEL, BIT_MASK(pos) << ADC0_FIFO_VC_SEL_FIL_FIFO_VC_SEL_Pos,
                       (uint32_t)(initStruct->filterFifoModeEn << pos) << ADC0_FIFO_VC_SEL_FIL_FIFO_VC_SEL_Pos);
            MODIFY_REG(ADCx->FIFO_VC_SEL, BIT_MASK(pos) << ADC0_FIFO_VC_SEL_PRE_FIFO_VC_SEL_Pos,
                       (uint32_t)(initStruct->preFifoModeEn << pos) << ADC0_FIFO_VC_SEL_PRE_FIFO_VC_SEL_Pos);
        }
    }
    /* 配置FIFO深度 */
    MODIFY_REG(ADCx->FIFO_CTRL, ADC0_FIFO_CTRL_FIL_FIFO_DEPTH_Msk,
               (uint32_t)initStruct->filterFifoDepth << ADC0_FIFO_CTRL_FIL_FIFO_DEPTH_Pos);
    MODIFY_REG(ADCx->FIFO_CTRL, ADC0_FIFO_CTRL_PRE_FIFO_DEPTH_Msk,
               (uint32_t)initStruct->preFifoDepth << ADC0_FIFO_CTRL_PRE_FIFO_DEPTH_Pos);
    /* 配置采样结果上报的对齐模式 */
    MODIFY_REG(ADCx->RESULT_CTL, ADC0_RESULT_CTL_FIL_RES_MOD_Msk,
               (uint32_t)initStruct->filterResultAlign << ADC0_RESULT_CTL_FIL_RES_MOD_Pos);
    MODIFY_REG(ADCx->RESULT_CTL, ADC0_RESULT_CTL_PRE_RES_MOD_Msk,
               (uint32_t)initStruct->preResultAlign << ADC0_RESULT_CTL_PRE_RES_MOD_Pos);
    /* 将数字核配置为同步处理 */
    SET_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_READY_PROC_MOD_Msk);
}

/**
 * @brief enables the virtual channel for the specified module
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param channelMask
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 *      @arg ADC_VIRTUAL_CHANNELALL
 */
void ADC_enable(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));
    /* 时序约束:数字控制器不能早于模拟core */
    SET_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_ADC_EN_Msk);

    SET_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_SARC_EN_Msk);

    SET_BIT(ADCx->VCEN_CTL, virtualChannelMask);

    /* 这里默认写一次FIFO模式的bitmap功能，因FIFO模式有约束，VC使能之后，需要重新reload这个寄存器，保证FIFO映射的虚拟通道生效
     *  如果有些虚拟通道是FIFO，有些通道不是FIFO，那么根据配置的FIFO映射通道确定，这里不会影响到映射关系 */
    SET_BIT(ADCx->FIFO_CTRL, ADC0_FIFO_CTRL_FIL_FIFO_BITMAP_RELOAD_Msk | ADC0_FIFO_CTRL_PRE_FIFO_BITMAP_RELOAD_Msk);
}

/**
 * @brief disable the virtual channel for the specified module
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param channelMask
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 *      @arg ADC_VIRTUAL_CHANNELALL
 */
void ADC_disable(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    /* 时序约束:数字控制器不能早于模拟core */
    CLEAR_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_ADC_EN_Msk);

    CLEAR_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_SARC_EN_Msk);

    CLEAR_BIT(ADCx->VCEN_CTL, virtualChannelMask);
}

/**
 * @brief
 *
 * @param ADCx sets the priority group for the specified module virtual channel.
 *              the lower the value the higher the priority.in the same priority group the smaller the sequence number
 * of the vc the higher the priority
 * @param channel the api only supports a single virtual channel setting for a virtual channel that needs to be
 * prioritized
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 * @param priority
 *      @arg ADC_VC_PRIORITY_GROUP_0
 *      @arg ADC_VC_PRIORITY_GROUP_1
 *      @arg ADC_VC_PRIORITY_GROUP_2
 *      @arg ADC_VC_PRIORITY_GROUP_3
 */
void ADC_setVCPriorityGroup(ADC_Type *ADCx, uint16_t channel, ADC_VCPriorityGroup priority)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(channel));

    MODIFY_REG(ADCx->VC_CTL[POSITION_VAL(channel)].VC_CTL, ADC0_VC_CTL_VC_CTL_SARC_VC_PRIORITY_Msk,
               (uint32_t)priority << ADC0_VC_CTL_VC_CTL_SARC_VC_PRIORITY_Pos);
}

/**
 * @brief specifies how the adc block handles event conflicts,
 *          refers to a scenario where multiple virtual channels trigger sampling at the same time
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param priorityMode
 *      @arg ADC_PRIORITY_MODE_LOW_DISCARD
 *      @arg ADC_PRIORITY_MODE_LOW_QUEUE
 *          note:low priority may be preempted when priority is queued
 */
void ADC_setPriorityMode(ADC_Type *ADCx, ADC_PriorityMode priorityMode)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_ADC_EVENT_CONFLICT_Msk,
               (uint32_t)priorityMode << ADC0_ADC_CTL0_SARC_ADC_EVENT_CONFLICT_Pos);
}

/**
 * @brief remaps the virtual channel to the specified physical channel and the physical channel is single ended sampling
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 * @param analogChannel
 *      @arg ADC_ANALOG_CHANNEL0
 *      @arg ADC_ANALOG_CHANNEL1
 *      @arg ADC_ANALOG_CHANNEL2
 *      @arg ADC_ANALOG_CHANNEL3
 *      @arg ADC_ANALOG_CHANNEL4
 *      @arg ADC_ANALOG_CHANNEL5
 *      @arg ADC_ANALOG_CHANNEL6
 *      @arg ADC_ANALOG_CHANNEL7
 *      @arg ADC_ANALOG_CHANNEL8
 *      @arg ADC_ANALOG_CHANNEL9
 *      @arg ADC_ANALOG_CHANNEL10
 *      @arg ADC_ANALOG_CHANNEL11
 *      @arg ADC_ANALOG_CHANNEL12
 *      @arg ADC_ANALOG_CHANNEL13
 *      @arg ADC_ANALOG_CHANNEL14
 *      @arg ADC_ANALOG_CHANNEL15
 *      @arg ADC_ANALOG_CHANNEL16
 *      @arg ADC_ANALOG_CHANNEL17
 *      @arg ADC_ANALOG_CHANNEL18
 *      @arg ADC_ANALOG_CHANNEL19
 *      @arg ADC_ANALOG_CHANNEL20
 *      @arg ADC_ANALOG_CHANNEL21
 *      @arg ADC_ANALOG_CHANNEL22
 *      @arg ADC_ANALOG_CHANNEL23
 *      @arg ADC_ANALOG_CHANNEL24
 *      @arg ADC_ANALOG_CHANNEL25
 *      @arg ADC_ANALOG_CHANNEL26
 *      @arg ADC_ANALOG_CHANNEL27
 *      @arg ADC_ANALOG_CHANNEL28
 *      @arg ADC_ANALOG_CHANNEL29
 *      @arg ADC_ANALOG_CHANNEL30
 *      @arg ADC_ANALOG_CHANNEL31
 */
void ADC_remapSingleAC(ADC_Type *ADCx, uint16_t virtualChannel, uint32_t analogChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));
    assert_param(IS_ADC_GET_ANALOG_CHANNEL(analogChannel));

    MODIFY_REG(ADCx->VC_CTL[POSITION_VAL(virtualChannel)].VC_CTL,
               ADC0_VC_CTL_VC_CTL_SARC_VC_SE_MUX_Msk,
               (uint32_t)POSITION_VAL(analogChannel) << ADC0_VC_CTL_VC_CTL_SARC_VC_SE_MUX_Pos);
}

/**
 * @brief gets the sampling status of the specified adc block.emphasize
 * this api refers to the sampling state of the entire adc
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @return uint8_t
 *      @arg bit4:adc sample done status        ADC_SAMPLE_STATUS_DONE
 *      @arg bit5:ADC sample the busy state     ADC_SAMPLE_STATUS_BUSY
 *      @arg bit other:none
 *
 */
bool ADC_isBusy(ADC_Type *ADCx)
{
    bool ret = false;

    assert_param(IS_ADC_PERIPH(ADCx));

    ret = (bool)READ_BIT(ADCx->ADC_STATUS, ADC0_ADC_STATUS_SARC_ADC_BUSY_Msk);

    return ret;
}

/**
 * @brief gets the virtual channel sampling status of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @return uint32_t every 2bit represent a VC status
 *      @arg bit[1:0]:VC0
 *                      00:IDLE             ADC_VC_SAMPLE_STATUS_IDLE
 *                      01:pending          ADC_VC_SAMPLE_STATUS_PENDING
 *                      10:busy             ADC_VC_SAMPLE_STATUS_BUSY
 *                      11:reserve
 *      @arg bit[3:2]:VC1
 *                      00:IDLE             ADC_VC_SAMPLE_STATUS_IDLE << (POSITION_VAL(virtualChannel) * 2)
 *                      01:pending          ADC_VC_SAMPLE_STATUS_PENDING << (POSITION_VAL(virtualChannel) * 2)
 *                      10:busy             ADC_VC_SAMPLE_STATUS_BUSY << (POSITION_VAL(virtualChannel) * 2)
 *                      11:reserve
 *      @arg bit[x:x]:VC.....
 *
 *      @arg bit[31:30]:VC15
 *                      00:IDLE
 *                      01:pending
 *                      10:busy
 *                      11:reserve
 */
uint32_t ADC_getVCSampleStatus(ADC_Type *ADCx)
{
    uint32_t ret = 0;

    assert_param(IS_ADC_PERIPH(ADCx));

    ret = READ_REG(ADCx->VC_STATUS);
    return ret;
}

/**
 * @brief software forces to trigger a virtual channel conversion of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannelMask
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 *      @arg ADC_VIRTUAL_CHANNELALL
 */
void ADC_forceVC(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    WRITE_REG(ADCx->VC_FORCE, virtualChannelMask);
}

/**
 * @brief converts the obtained virtual channel result value to a true unsigned sampled value
 *
 * @param data pass in the result value obtained from the virtual channel
 * @return uint16_t returns a true unsigned sampled value
 */
uint16_t ADC_S16D2toUint(int16_t data)
{
    int16_t temp = 0;

    temp = (data >> 2) + 2048;

    /* saturation of the cut off */
    if (temp < 0)
    {
        temp = 0;
    }
    else if (temp > 4095)
    {
        temp = 4095;
    }

    return (uint16_t)temp;
}

/**
 * @brief converts the obtained virtual channel result value to a true fractional sampled value
 *
 * @param data pass in the result value obtained from the virtual channel
 * @return float returns a true fractional sampled value
 */
float ADC_S16D2toFloat(int16_t data)
{
    float decimal = 0.0f;
    float temp    = 0;

    decimal = (data & 0x3) * 0.25f;
    temp    = (float)((data >> 2) + 2048) + decimal;

    /* saturation of the cut off */
    if (temp < 0)
    {
        temp = 0;
    }
    else if (temp > 4095)
    {
        temp = 4095;
    }

    return temp;
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannel
 * @return int16_t
 */
int16_t ADC_getPreResult(ADC_Type *ADCx, uint16_t virtualChannel)
{
    int16_t ret = 0;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    ret =
        (int16_t)READ_BIT(ADCx->PRE_RESULT[POSITION_VAL(virtualChannel)].PRE, ADC0_PRE_RESULT_PRE_PRE_RESULT_Msk);

    return ret;
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannel
 * @return int16_t
 */
int16_t ADC_getFilterResult(ADC_Type *ADCx, uint16_t virtualChannel)
{
    int16_t ret = 0;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    ret =
        (int16_t)READ_BIT(ADCx->FIL_RESULT[POSITION_VAL(virtualChannel)].FIL, ADC0_FIL_RESULT_FIL_FIL_RESULT_Msk);

    return ret;
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannel
 * @return true
 * @return false
 */
bool ADC_getPreResultStatus(ADC_Type *ADCx, uint16_t virtualChannel)
{
    bool ret = false;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    ret =
        READ_BIT(ADCx->PRE_RESULT[POSITION_VAL(virtualChannel)].PRE,
                 ADC0_PRE_RESULT_PRE_PRE_RESULT_VAL_Msk) ? true : false;

    return ret;
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannel
 * @return true
 * @return false
 */
bool ADC_getFilterResultStatus(ADC_Type *ADCx, uint16_t virtualChannel)
{
    FlagStatus ret = RESET;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    ret =
        READ_BIT(ADCx->FIL_RESULT[POSITION_VAL(virtualChannel)].FIL,
                 ADC0_FIL_RESULT_FIL_FIL_RESULT_VAL_Msk) ? SET : RESET;

    return ret;
}

/**
 * @brief start adc calibration
 *
 * @param ADCx
 */
void ADC_startCalibration(ADC_Type *ADCx)
{
    // uint8_t  i           = 0;
    // float    code_refp   = 0.0f;
    // float    code_refn   = 0.0f;
    // float    gainTemp    = 0.0f;
    // int8_t   gainInteger = 0;
    // int16_t  gainDec     = 0;
    // uint16_t gain        = 0;
    // int16_t  offsetTemp  = 0;
    // int8_t   offset      = 0;

    assert_param(IS_ADC_PERIPH(ADCx));

    // /* make sure adc ctl1 in the register adc_pwdn = 0, adc_en = 0 */
    // CLEAR_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_ADC_EN_Msk);
    // SET_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_SARC_EN_Msk);
    // /* configure the mode of operation in which the correction is corrected single ended or differential */
    // MODIFY_REG(ADCx->CAL_CTL, ADC0_CAL_CTL_SARC_ADC_CAL_CH_MODE_Msk,
    //            (uint32_t)ADC_WORK_MODE_SINGLE << ADC0_CAL_CTL_SARC_ADC_CAL_CH_MODE_Pos);
    // /* open refp to make sure refn is turned off*/
    // MODIFY_REG(ADCx->CAL_CTL, (uint32_t)0xf, ADC0_CAL_CTL_SARC_D2A_ADC_CAL_SE_REFP_INJ_Msk);
    // /* you need to set up the correction first flag */
    // SET_BIT(ADCx->CAL_CTL, ADC0_CAL_CTL_SARC_ADC_CAL_FLAG_Msk);
    // /* start the conversion */
    // SET_BIT(ADCx->CAL_CONV_CTL, ADC0_CAL_CONV_CTL_SARC_ADC_CAL_CONV_START_Msk);/* start calibration */
    // /* wait for the conversion to work */
    // while (READ_BIT(ADCx->CAL_REF, ADC0_CAL_REF_SARC_CAL_AVER_VAL_Msk) == RESET);
    // /* gets a valid result value refp */
    // code_refp = ADC_S16D2toFloat((int16_t)READ_BIT(ADCx->CAL_REF, ADC0_CAL_REF_SARC_CAL_AVER_VALUE_Msk));
    // /* turn off the refp switch */
    // CLEAR_BIT(ADCx->CAL_CTL, ADC0_CAL_CTL_SARC_D2A_ADC_CAL_SE_REFP_INJ_Msk);
    // /* open ref n make sure refp is turned off*/
    // MODIFY_REG(ADCx->CAL_CTL, (uint32_t)0xf, ADC0_CAL_CTL_SARC_D2A_ADC_CAL_SE_REFN_INJ_Msk);
    // /* start the conversion,adc_cal_flag set 1 */
    // SET_BIT(ADCx->CAL_CONV_CTL, ADC0_CAL_CONV_CTL_SARC_ADC_CAL_CONV_START_Msk);/* start calibration */
    // /* wait for the conversion to work */
    // while (READ_BIT(ADCx->CAL_REF, ADC0_CAL_REF_SARC_CAL_AVER_VAL_Msk) == RESET);
    // /* gets a valid result value refn */
    // code_refn = ADC_S16D2toFloat((int16_t)READ_BIT(ADCx->CAL_REF, ADC0_CAL_REF_SARC_CAL_AVER_VALUE_Msk));
    // /* close refn */
    // CLEAR_BIT(ADCx->CAL_CTL, ADC0_CAL_CTL_SARC_D2A_ADC_CAL_SE_REFN_INJ_Msk);
    // /* correction calculations */
    // gainTemp = (code_refp - code_refn) / 4096;
    // /* gain(calculate the value) * gain(register setting value)= 1 */
    // if (gainTemp != 0.0f)
    // {
    //     gainTemp = 1.0f / gainTemp;
    // }

    // gainInteger = (int8_t)gainTemp;
    // gainDec     = (int16_t)((gainTemp - gainInteger) * 4096);
    // gain        = (uint16_t)((gainInteger & 0x3) << 12 | gainDec);
    // /* gain needs to be saturated */
    // if (gainTemp >= 4.0f)
    // {
    //     gain = 0x3FFF;
    // }
    // else if (gainTemp <= 0.0f)
    // {
    //     gain = 0;
    // }
    // offsetTemp = (int16_t)((code_refp + code_refn) / 2) - 2048;
    // /* offset(calculate the value) + offset(register setting value)= 0 */
    // offsetTemp = -offsetTemp;

    // /* the offset needs to be processed,range:-16LSB(10000) ~ +15LSB(01111)
    //  *  bit4:symbol bits
    //  */
    // if (offsetTemp < -16)
    // {
    //     offset = -16;
    // }
    // else if (offsetTemp > 15)
    // {
    //     offset = 15;
    // }
    // else
    // {
    //     offset = (int8_t)offsetTemp;
    // }
    // /* turn on correcting digital gain and offset enabled */
    // SET_BIT(ADCx->CAL_OS, ADC0_CAL_OS_SARC_CAL_OS_EN_Msk);
    // SET_BIT(ADCx->CAL_GAIN, ADC0_CAL_GAIN_SARC_CAL_GAIN_EN_Msk);
    // /* set gain and offset */
    // MODIFY_REG(ADCx->CAL_GAIN, ADC0_CAL_GAIN_SARC_CAL_SE_GAIN_Msk,
    //            (uint32_t)(gain & 0x3FFF) << ADC0_CAL_GAIN_SARC_CAL_SE_GAIN_Pos);
    // MODIFY_REG(ADCx->CAL_OS, ADC0_CAL_OS_SARC_CAL_SE_OS_Msk,
    //            (uint32_t)(offset & 0x1F) << ADC0_CAL_OS_SARC_CAL_SE_OS_Pos);
    // /* finally it needs to be cleared adc_cal_flag */
    // CLEAR_BIT(ADCx->CAL_CTL, ADC0_CAL_CTL_SARC_ADC_CAL_FLAG_Msk);/* configure the calibration start
    //                                                               * flag:calibrating the adc */
    // /* finally turn off analog and digital enables */
    // CLEAR_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_ADC_EN_Msk);
    // CLEAR_BIT(ADCx->ADC_CTL0, ADC0_ADC_CTL0_SARC_SARC_EN_Msk);
    // /*after the correction process the results need to be read once to clear the status of the results  */
    // for (i = 0; i < 16; i++)
    // {
    //     ADC_GetVCResult(ADCx, (uint16_t)BIT_MASK(i));
    // }
}

/**
 * @brief 选择EOC事件输出的事件源
 *
 * @param ADCx
 * @param num
 * @param event
 */
void ADC_selectEOCOutEvent(ADC_Type *ADCx, ADC_EOCEventNum num, ADC_EOCEventSrc event)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    if (num == ADC_EOC_EVT_NUM_0)
    {
        MODIFY_REG(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC2SPL_TRIG0_SEL_Msk,
                   (uint32_t)event << ADC0_EOC_CTL_EOC2SPL_TRIG0_SEL_Pos);
    }
    else
    {
        MODIFY_REG(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC2SPL_TRIG1_SEL_Msk,
                   (uint32_t)event << ADC0_EOC_CTL_EOC2SPL_TRIG1_SEL_Pos);
    }
}

/**
 * @brief set the pulse mode of the eoc
 *
 * @param ADCx specified peripherals
 *      - ADC0
 *      - ADC1
 * @param pulseMode the pulse mode
 */
void ADC_setEOCPulseMode(ADC_Type *ADCx, ADC_EOCPulseMode pulseMode)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC_MOD_Msk,
               (uint32_t)pulseMode << ADC0_EOC_CTL_EOC_MOD_Pos);
}

/**
 * @brief 使能EOC时刻延时产生中断
 *
 * @param ADCx
 */
void ADC_enableEOCDelay(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    SET_BIT(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC_DLY_EN_Msk);
}

/**
 * @brief 失能EOC时刻延时产生中断
 *
 * @param ADCx
 */
void ADC_disableEOCDelay(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    CLEAR_BIT(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC_DLY_EN_Msk);
}

/**
 * @brief 设置EOC到产生中断的延时时间
 *
 * @param ADCx
 * @param delay
 */
void ADC_setEOCDelay(ADC_Type *ADCx, uint16_t delay)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //todo

    MODIFY_REG(ADCx->EOC_CTL, ADC0_EOC_CTL_EOC_DLY_Msk, (uint32_t)delay << ADC0_EOC_CTL_EOC_DLY_Pos);
}

/**
 * @brief 获取ECO是否告警
 *
 * @param ADCx
 * @return true
 * @return false
 */
bool ADC_isEOCAlarm(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    return (bool)READ_BIT(ADCx->EOC_STS, ADC0_EOC_STS_EOC_ALM_FLAG_Msk);
}

/**
 * @brief 获取产生EOC告警的虚拟通道编号
 *
 * @param ADCx
 * @return uint8_t 返回值为具体的虚拟通道编号
 */
uint8_t ADC_getEOCAlarmVCChannel(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    return (uint8_t)READ_BIT(ADCx->EOC_STS, ADC0_EOC_STS_EOC_ALM_VCNUM_Msk);
}

/**
 * @brief 获取触发到开始采样的绝对延时时间
 *
 * @param ADCx
 * @param virtualChannel
 * @return uint16_t 范围：0 ~ 4095
 */
uint16_t ADC_getTrig2SampleDelay(ADC_Type *ADCx, uint16_t virtualChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    return (uint16_t)READ_REG(ADCx->T2S_STAMP[POSITION_VAL(virtualChannel)].DLY);
}

/**
 * @brief enable interrupts that specify the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param interruptTrigger
 */
void ADC_enableInterrupt(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    switch (interruptTrigger)
    {
    case ADC_INT_TRIGGER_EOC0_EOC:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk,
                   (uint32_t)POSITION_VAL(virtualChannel) << ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC0_PRE_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 16) << ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC0_FILTER_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 32) << ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_EOC:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk,
                   (uint32_t)POSITION_VAL(virtualChannel) << ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_PRE_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 16) << ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_FILTER_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 32) << ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_EOC:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk,
                   (uint32_t)POSITION_VAL(virtualChannel) << ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_PRE_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 16) << ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_FILTER_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 32) << ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_EOC:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk,
                   (uint32_t)POSITION_VAL(virtualChannel) << ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_PRE_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 16) << ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_FILTER_RESULT:
        MODIFY_REG(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk,
                   (uint32_t)(POSITION_VAL(virtualChannel) + 32) << ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Pos);
        SET_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD:
        SET_BIT(ADCx->WDT_INT_EN, (uint32_t)virtualChannel << ADC0_WDT_INT_EN_WDT_HI_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_WDG_LOW_THRESHOLD:
        SET_BIT(ADCx->WDT_INT_EN, (uint32_t)virtualChannel << ADC0_WDT_INT_EN_WDT_LO_INT_EN_Pos);
        break;
    }
}

/**
 * @brief disable interrupts that specify the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param interruptTrigger
 */
void ADC_disableInterrupt(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    switch (interruptTrigger)
    {
    case ADC_INT_TRIGGER_EOC0_EOC:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC0_PRE_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC0_FILTER_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC0_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)1 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_EOC:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_PRE_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC1_FILTER_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC1_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)2 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_EOC:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_PRE_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC2_FILTER_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC2_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)4 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_EOC:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_PRE_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_EOC3_FILTER_RESULT:
        CLEAR_BIT(ADCx->EOC_INT_SRC_SEL, ADC0_EOC_INT_SRC_SEL_EOC3_SEL_Msk);
        CLEAR_BIT(ADCx->EOC_INT_EN, (uint32_t)8 << ADC0_EOC_INT_EN_EOC_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD:
        CLEAR_BIT(ADCx->WDT_INT_EN, (uint32_t)virtualChannel << ADC0_WDT_INT_EN_WDT_HI_INT_EN_Pos);
        break;

    case ADC_INT_TRIGGER_WDG_LOW_THRESHOLD:
        CLEAR_BIT(ADCx->WDT_INT_EN, (uint32_t)virtualChannel << ADC0_WDT_INT_EN_WDT_LO_INT_EN_Pos);
        break;
    }
}

/**
 * @brief enable interrupt masking that specifies the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 */
void ADC_maskInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        SET_BIT(ADCx->EOC_INT_MASK, (uint32_t)1 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 1:
        SET_BIT(ADCx->EOC_INT_MASK, (uint32_t)2 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 2:
        SET_BIT(ADCx->EOC_INT_MASK, (uint32_t)4 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 3:
        SET_BIT(ADCx->EOC_INT_MASK, (uint32_t)8 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            SET_BIT(ADCx->WDT_INT_MASK, (uint32_t)virtualChannelMask << ADC0_WDT_INT_MASK_WDT_HI_INT_MASK_Pos);
        }
        else
        {
            SET_BIT(ADCx->WDT_INT_MASK, (uint32_t)virtualChannelMask << ADC0_WDT_INT_MASK_WDT_LO_INT_MASK_Pos);
        }
        break;
    }
}

/**
 * @brief disable interrupt masking that specifies the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 */
void ADC_unmaskInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        CLEAR_BIT(ADCx->EOC_INT_MASK, (uint32_t)1 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 1:
        CLEAR_BIT(ADCx->EOC_INT_MASK, (uint32_t)2 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 2:
        CLEAR_BIT(ADCx->EOC_INT_MASK, (uint32_t)4 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 3:
        CLEAR_BIT(ADCx->EOC_INT_MASK, (uint32_t)8 << ADC0_EOC_INT_MASK_EOC_INT_MASK_Pos);
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            CLEAR_BIT(ADCx->WDT_INT_MASK, (uint32_t)virtualChannelMask << ADC0_WDT_INT_MASK_WDT_HI_INT_MASK_Pos);
        }
        else
        {
            CLEAR_BIT(ADCx->WDT_INT_MASK, (uint32_t)virtualChannelMask << ADC0_WDT_INT_MASK_WDT_LO_INT_MASK_Pos);
        }
        break;
    }
}

/**
 * @brief forces an interrupt to trigger the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 */
void ADC_forceInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        SET_BIT(ADCx->EOC_INT_FORCE_IND, (uint32_t)1 << ADC0_EOC_INT_FORCE_IND_EOC_INT_FR_IND_Pos);
        break;

    case 1:
        SET_BIT(ADCx->EOC_INT_FORCE_IND, (uint32_t)2 << ADC0_EOC_INT_FORCE_IND_EOC_INT_FR_IND_Pos);
        break;

    case 2:
        SET_BIT(ADCx->EOC_INT_FORCE_IND, (uint32_t)4 << ADC0_EOC_INT_FORCE_IND_EOC_INT_FR_IND_Pos);
        break;

    case 3:
        SET_BIT(ADCx->EOC_INT_FORCE_IND, (uint32_t)8 << ADC0_EOC_INT_FORCE_IND_EOC_INT_FR_IND_Pos);
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            SET_BIT(ADCx->WDT_INT_FORCE_IND,
                    (uint32_t)virtualChannelMask << ADC0_WDT_INT_FORCE_IND_WDT_HI_INT_FR_IND_Pos);
        }
        else
        {
            SET_BIT(ADCx->WDT_INT_FORCE_IND,
                    (uint32_t)virtualChannelMask << ADC0_WDT_INT_FORCE_IND_WDT_LO_INT_FR_IND_Pos);
        }
        break;
    }
}

/**
 * @brief gets the interrupt status of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param interruptTrigger
 * @return bool
 */
bool ADC_getInterruptStatus(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言
    bool    ret  = false;
    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_STS,
                             (uint32_t)1 << ADC0_EOC_INT_STS_EOC_INT_STS_Pos)? true : false;
        break;

    case 1:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_STS,
                             (uint32_t)2 << ADC0_EOC_INT_STS_EOC_INT_STS_Pos)? true : false;
        break;

    case 2:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_STS,
                             (uint32_t)4 << ADC0_EOC_INT_STS_EOC_INT_STS_Pos)? true : false;
        break;

    case 3:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_STS,
                             (uint32_t)8 << ADC0_EOC_INT_STS_EOC_INT_STS_Pos)? true : false;
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            ret = DRV_IS_BIT_SET(ADCx->WDT_INT_STS,
                                 (uint32_t)virtualChannel << ADC0_WDT_INT_STS_WDT_HI_INT_STS_Pos)? true : false;
        }
        else
        {
            ret = DRV_IS_BIT_SET(ADCx->WDT_INT_STS,
                                 (uint32_t)virtualChannel << ADC0_WDT_INT_STS_WDT_LO_INT_STS_Pos)? true : false;
        }
        break;
    }

    return ret;
}

/**
 * @brief gets the interrupt raw status of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 * @return ITStatus
 */
bool ADC_getInterruptStatusRaw(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言
    bool    ret  = false;
    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_RAW,
                             (uint32_t)1 << ADC0_EOC_INT_RAW_EOC_INT_RAW_Pos)? true : false;
        break;

    case 1:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_RAW,
                             (uint32_t)2 << ADC0_EOC_INT_RAW_EOC_INT_RAW_Pos)? true : false;
        break;

    case 2:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_RAW,
                             (uint32_t)4 << ADC0_EOC_INT_RAW_EOC_INT_RAW_Pos)? true : false;
        break;

    case 3:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_RAW,
                             (uint32_t)8 << ADC0_EOC_INT_RAW_EOC_INT_RAW_Pos)? true : false;
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            ret =
                DRV_IS_BIT_SET(ADCx->WDT_INT_RAW,
                               (uint32_t)virtualChannel << ADC0_WDT_INT_RAW_WDT_HI_INT_RAW_Pos)? true : false;
        }
        else
        {
            ret =
                DRV_IS_BIT_SET(ADCx->WDT_INT_RAW,
                               (uint32_t)virtualChannel << ADC0_WDT_INT_RAW_WDT_LO_INT_RAW_Pos)? true : false;
        }
        break;
    }

    return ret;
}

/**
 * @brief gets the interrupt overflow alarm status for the specified adc module
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 * @return ITStatus
 */
bool ADC_getInterruptOverflowStatus(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言
    bool    ret  = false;
    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_OVF,
                             (uint32_t)1 << ADC0_EOC_INT_OVF_EOC_INT_OVF_Pos)? true : false;
        break;

    case 1:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_OVF,
                             (uint32_t)2 << ADC0_EOC_INT_OVF_EOC_INT_OVF_Pos)? true : false;
        break;

    case 2:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_OVF,
                             (uint32_t)4 << ADC0_EOC_INT_OVF_EOC_INT_OVF_Pos)? true : false;
        break;

    case 3:
        ret = DRV_IS_BIT_SET(ADCx->EOC_INT_OVF,
                             (uint32_t)8 << ADC0_EOC_INT_OVF_EOC_INT_OVF_Pos)? true : false;
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            ret =
                DRV_IS_BIT_SET(ADCx->WDT_INT_OVF,
                               (uint32_t)virtualChannel << ADC0_WDT_INT_OVF_WDT_HI_INT_OVF_Pos)? true : false;
        }
        else
        {
            ret =
                DRV_IS_BIT_SET(ADCx->WDT_INT_OVF,
                               (uint32_t)virtualChannel << ADC0_WDT_INT_OVF_WDT_LO_INT_OVF_Pos)? true : false;
        }
        break;
    }

    return ret;
}

/**
 * @brief clears the interrupt state of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 */
void ADC_clearInterruptStatus(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        SET_BIT(ADCx->EOC_INT_CLR, (uint32_t)1 << ADC0_EOC_INT_CLR_EOC_INT_CLR_Pos);
        break;

    case 1:
        SET_BIT(ADCx->EOC_INT_CLR, (uint32_t)2 << ADC0_EOC_INT_CLR_EOC_INT_CLR_Pos);
        break;

    case 2:
        SET_BIT(ADCx->EOC_INT_CLR, (uint32_t)4 << ADC0_EOC_INT_CLR_EOC_INT_CLR_Pos);
        break;

    case 3:
        SET_BIT(ADCx->EOC_INT_CLR, (uint32_t)8 << ADC0_EOC_INT_CLR_EOC_INT_CLR_Pos);
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            SET_BIT(ADCx->WDT_INT_CLR, (uint32_t)virtualChannelMask << ADC0_WDT_INT_CLR_WDT_HI_INT_CLR_Pos);
        }
        else
        {
            SET_BIT(ADCx->WDT_INT_CLR, (uint32_t)virtualChannelMask << ADC0_WDT_INT_CLR_WDT_LO_INT_CLR_Pos);
        }
        break;
    }
}

/**
 * @brief clears the interrupt state of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param IT
 */
void ADC_clearInterruptOverflowStatus(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO 虚拟通道需要断言

    uint8_t temp = interruptTrigger / 3;

    switch (temp)
    {
    case 0:
        SET_BIT(ADCx->EOC_INT_OVF_CLR, (uint32_t)1 << ADC0_EOC_INT_OVF_CLR_EOC_INT_OVF_CLR_Pos);
        break;

    case 1:
        SET_BIT(ADCx->EOC_INT_OVF_CLR, (uint32_t)2 << ADC0_EOC_INT_OVF_CLR_EOC_INT_OVF_CLR_Pos);
        break;

    case 2:
        SET_BIT(ADCx->EOC_INT_OVF_CLR, (uint32_t)4 << ADC0_EOC_INT_OVF_CLR_EOC_INT_OVF_CLR_Pos);
        break;

    case 3:
        SET_BIT(ADCx->EOC_INT_OVF_CLR, (uint32_t)8 << ADC0_EOC_INT_OVF_CLR_EOC_INT_OVF_CLR_Pos);
        break;

    case 4:
        if (interruptTrigger == ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD)
        {
            SET_BIT(ADCx->WDT_INT_OVF_CLR, (uint32_t)virtualChannelMask << ADC0_WDT_INT_OVF_CLR_WDT_HI_INT_OVF_CLR_Pos);
        }
        else
        {
            SET_BIT(ADCx->WDT_INT_OVF_CLR, (uint32_t)virtualChannelMask << ADC0_WDT_INT_OVF_CLR_WDT_LO_INT_OVF_CLR_Pos);
        }
        break;
    }
}

/**
 * @brief
 *
 * @param ADCx
 * @param outMode
 */
void ADC_setAnalogWdgMode(ADC_Type *ADCx, uint16_t virtualChannel, ADC_AnalogWdgOutMode outMode)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->WDT_CTL, virtualChannel, (uint32_t)outMode << POSITION_VAL(virtualChannel));
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannelMask
 * @param thresholdDir
 */
void ADC_enableAnalogWdg(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_AnalogWdgThreshold thresholdDir)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO

    SET_BIT(ADCx->WDT_EVT_EN, (uint32_t)virtualChannelMask << thresholdDir);
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannelMask
 * @param thresholdDir
 */
void ADC_disableAnalogWdg(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_AnalogWdgThreshold thresholdDir)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO

    CLEAR_BIT(ADCx->WDT_EVT_EN, (uint32_t)virtualChannelMask << thresholdDir);
}

/**
 * @brief
 *
 * @param ADCx
 * @param eventNumber
 * @param event
 */
void ADC_selectAnalogWdgOutEvt2ETIMER(ADC_Type *ADCx, ADC_AnalogWdgEvtNum eventNumber, ADC_AnalogWdgEvt event)
{
    uint32_t tempPos  = ADC0_WDT_EVT_SEL_WDT2ETIM_EVT0_SEL_Pos + eventNumber * 4;
    uint32_t tempMask = (uint32_t)0xF << tempPos;

    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO

    MODIFY_REG(ADCx->WDT_EVT_SEL, tempMask, (uint32_t)event << tempPos);
}

void ADC_selectAnalogWdgOutEvt2XBAR(ADC_Type *ADCx, ADC_AnalogWdgEvtNum eventNumber, ADC_AnalogWdgEvt event)
{
    uint32_t tempPos  = ADC0_WDT_EVT_SEL_WDT2XBAR_EVT0_SEL_Pos + eventNumber * 4;
    uint32_t tempMask = (uint32_t)0xF << tempPos;

    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO

    MODIFY_REG(ADCx->WDT_EVT_SEL, tempMask, (uint32_t)event << tempPos);
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannelMask
 * @param thresholdDir
 */
void ADC_clearAnalogWdgThresholdStatus(ADC_Type *ADCx, uint16_t virtualChannelMask,
                                       ADC_AnalogWdgThreshold thresholdDir)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //TODO
    SET_BIT(ADCx->WDT_CLR, (uint32_t)virtualChannelMask << thresholdDir);
}

/**
 * @brief configure the watchdog upper and lower thresholds that specify the adc module
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 *      @arg ADC_VIRTUAL_CHANNEL0
 *      @arg ADC_VIRTUAL_CHANNEL1
 *      @arg ADC_VIRTUAL_CHANNEL2
 *      @arg ADC_VIRTUAL_CHANNEL3
 *      @arg ADC_VIRTUAL_CHANNEL4
 *      @arg ADC_VIRTUAL_CHANNEL5
 *      @arg ADC_VIRTUAL_CHANNEL6
 *      @arg ADC_VIRTUAL_CHANNEL7
 *      @arg ADC_VIRTUAL_CHANNEL8
 *      @arg ADC_VIRTUAL_CHANNEL9
 *      @arg ADC_VIRTUAL_CHANNEL10
 *      @arg ADC_VIRTUAL_CHANNEL11
 *      @arg ADC_VIRTUAL_CHANNEL12
 *      @arg ADC_VIRTUAL_CHANNEL13
 *      @arg ADC_VIRTUAL_CHANNEL14
 *      @arg ADC_VIRTUAL_CHANNEL15
 * @param highThreshold
 * @param lowThreshold
 */
void ADC_setAnalogWdgThreshold(ADC_Type *ADCx, uint16_t virtualChannel, uint16_t highThreshold, uint16_t lowThreshold)
{
    int32_t highTemp = (int16_t)(highThreshold) << 2;
    int32_t lowTemp  = (int16_t)(lowThreshold) << 2;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    MODIFY_REG(ADCx->WDT_LIMIT[POSITION_VAL(virtualChannel)].WDT_LIMIT,
               ADC0_WDT_LIMIT_WDT_LIMIT_SARC_WDT_LIMIT_HI_Msk |
               ADC0_WDT_LIMIT_WDT_LIMIT_SARC_WDT_LIMIT_LO_Msk,
               (uint32_t)((highTemp & 0xFFFF) << ADC0_WDT_LIMIT_WDT_LIMIT_SARC_WDT_LIMIT_HI_Pos) |
               (uint32_t)((lowTemp & 0xFFFF) << ADC0_WDT_LIMIT_WDT_LIMIT_SARC_WDT_LIMIT_LO_Pos));
}

/**
 * @brief
 *
 * @param ADCx
 * @param virtualChannelMask
 * @param thresholdDir
 * @return uint16_t 返回的16位数据中，每一位分别对应虚拟通道
 */
uint16_t ADC_getAnalogWdgThresholdStatus(ADC_Type *ADCx, ADC_AnalogWdgThreshold thresholdDir)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    return (uint16_t)READ_BIT(ADCx->WDT_STS,
                              (uint32_t)(ADC0_WDT_STS_WDT_LO_STS_Msk << thresholdDir) >> ADC0_WDT_STS_WDT_LO_STS_Pos);
}

/**
 * @brief enables the blanking function that specifies the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 */
void ADC_enableBlanking(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    SET_BIT(ADCx->BLK_CTL0, ADC0_BLK_CTL0_SARC_BLANKING_EN_Msk);
}

/**
 * @brief disable the blanking function that specifies the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 */
void ADC_disableBlanking(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    CLEAR_BIT(ADCx->BLK_CTL0, ADC0_BLK_CTL0_SARC_BLANKING_EN_Msk);
}

/**
 * @brief select the blanking trigger source that specifies the adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param trigger
 */
void ADC_selectBlankingTrigger(ADC_Type *ADCx, ADC_BlankingTrigger trigger)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->BLK_CTL0, ADC0_BLK_CTL0_SARC_BLANKING_TRIG_Msk,
               (uint32_t)trigger << ADC0_BLK_CTL0_SARC_BLANKING_TRIG_Pos);
}

/**
 * @brief sets the blanking window length of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param len
 */
void ADC_setBlankingWidth(ADC_Type *ADCx, uint16_t len)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->BLK_CTL1, ADC0_BLK_CTL1_SARC_BLANKING_LEN_Msk,
               (uint32_t)len << ADC0_BLK_CTL1_SARC_BLANKING_LEN_Pos);
}

/**
 * @brief sets the blanking trigger delay time for the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param delay
 */
void ADC_setBlankingTrigDelay(ADC_Type *ADCx, uint16_t delay)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    MODIFY_REG(ADCx->BLK_CTL1, ADC0_BLK_CTL1_SARC_BLANKING_TRIG_DELAY_Msk,
               (uint32_t)delay << ADC0_BLK_CTL1_SARC_BLANKING_TRIG_DELAY_Pos);
}

/**
 * @brief enables the offset calibration
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param offset  value s(15,2)
 */
void ADC_enabelCalOSOffset(ADC_Type *ADCx, int16_t offset)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    WRITE_REG(ADCx->CAL_OS, (offset << 2UL) | ADC0_CAL_OS_SARC_CAL_OS_EN_Msk);
}

/**
 * @brief disable the offset calibration
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 */
void ADC_disabelCalOSOffset(ADC_Type *ADCx)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    CLEAR_BIT(ADCx->CAL_OS, ADC0_CAL_OS_SARC_CAL_OS_EN_Msk);
}

/**
 * @brief enables the offset a preprocessing stage for the specified adc block virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannelMask
 */
void ADC_enabelPreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    SET_BIT(ADCx->PRE_OS_EN, virtualChannelMask);
}

/**
 * @brief disable the offset a preprocessing stage for the specified adc block virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannelMask
 */
void ADC_disablePreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    CLEAR_BIT(ADCx->PRE_OS_EN, virtualChannelMask);
}

/**
 * @brief enables the gain a preprocessing stage for the specified adc block virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannelMask
 */
void ADC_enablePreProcessGain(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    SET_BIT(ADCx->PRE_GAIN_EN, virtualChannelMask);
}

/**
 * @brief disable the gain a preprocessing stage for the specified adc block virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannelMask
 */
void ADC_disablePreProcessGain(ADC_Type *ADCx, uint16_t virtualChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_VIRTUAL_CHANNEL(virtualChannelMask));

    CLEAR_BIT(ADCx->PRE_GAIN_EN, virtualChannelMask);
}

/**
 * @brief sets the offset value that specifies the adc block virtual channel preprocessing.
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 * @param offset data type:the register sets the raw data to a 16 bit signed number and the last two decimal places
 *                 raw register range:0xA000~0x6003
 *                  after conversion the user can set the range:-6144 ~ 6144
 *
 */
void ADC_setPreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannel, int16_t offset)
{
    uint16_t offsetTemp = (uint16_t)(offset << 2);

    //todo 数据格式需要转换
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));
    assert_param(IS_ADC_PREPROCESS_OFFSET(offset));

    WRITE_REG(ADCx->PRE_OS[POSITION_VAL(virtualChannel)].PRE_OS, offsetTemp);
}

/**
 * @brief sets the gain value for the virtual channel of the specified adc block
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 * @param gain data type:S(15,12).
 *              data range:
 */
void ADC_setPreProcessGain(ADC_Type *ADCx, uint16_t virtualChannel, int16_t gain)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));
    // assert_param(IS_ADC_PREPROCESS_GAIN(gain));
    //todo 数据格式需要转换
    WRITE_REG(ADCx->PRE_GAIN[POSITION_VAL(virtualChannel)].PRE_GAIN, (uint32_t)gain);
}

/**
 * @brief enables filtering that specifies the adc virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 */
void ADC_enableVCFilter(ADC_Type *ADCx, uint16_t virtualChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    SET_BIT(ADCx->VC_CTL[POSITION_VAL(virtualChannel)].VC_CTL, ADC0_VC_CTL_VC_CTL_SARC_VC_FILTER_EN_Msk);
}

/**
 * @brief disable filtering that specifies the adc virtual channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 */
void ADC_disableVCFilter(ADC_Type *ADCx, uint16_t virtualChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));

    CLEAR_BIT(ADCx->VC_CTL[POSITION_VAL(virtualChannel)].VC_CTL, ADC0_VC_CTL_VC_CTL_SARC_VC_FILTER_EN_Msk);
}

/**
 * @brief enable the filtering function of the specified adc block filter channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannelMask
 */
void ADC_enableFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannelMask));

    SET_BIT(ADCx->FILTER_CTL, filterChannelMask);
}

/**
 * @brief disable the filtering function of the specified adc block filter channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannelMask
 */
void ADC_disableFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannelMask));

    CLEAR_BIT(ADCx->FILTER_CTL, filterChannelMask);
}

/**
 * @brief the map specifies the adc block virtual channel to the filter channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param virtualChannel
 * @param filterChannel
 */
void ADC_remapFilterChannel(ADC_Type *ADCx, uint16_t virtualChannel, uint8_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_VIRTUAL_CHANNEL(virtualChannel));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));

    MODIFY_REG(ADCx->VC_CTL[POSITION_VAL(virtualChannel)].VC_CTL,
               ADC0_VC_CTL_VC_CTL_SARC_VC_FILTER_CH_Msk,
               (uint32_t)POSITION_VAL(filterChannel) << ADC0_VC_CTL_VC_CTL_SARC_VC_FILTER_CH_Pos);
}

/**
 * @brief select the filter channel filtering type for the specified adc block
 *
 * @param ADCx
 * @param filterChannel
 * @param filterType
 */
void ADC_selectFilterType(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterType filterType)
{
    uint8_t channel2BitNum   = 2; /* the number of filter channels corresponding to register bits */
    uint8_t bitL2BitH_Offset = 1;
    uint8_t channelBitH      = 0; /* the filter channel corresponds to the register bit value H */
    uint8_t channelBitL      = 0; /* the filter channel corresponds to the register bit value L*/

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));

    channelBitL = POSITION_VAL(filterChannel) * channel2BitNum;
    channelBitH = channelBitL + bitL2BitH_Offset;

    MODIFY_REG(ADCx->FILTER_CTL, (uint32_t)(BIT_MASK(channelBitL) | BIT_MASK(channelBitH)) <<
               ADC0_FILTER_CTL_SARC_FILTER_TYPE_Pos,
               (uint32_t)filterType << channelBitL <<
               ADC0_FILTER_CTL_SARC_FILTER_TYPE_Pos);
}

/**
 * @brief clears the status of the filter channel of the specified adc block
 *
 * @param ADCx
 * @param filterChannelMask
 */
void ADC_clearFilterStatus(ADC_Type *ADCx, uint8_t filterChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannelMask));

    SET_BIT(ADCx->FILTER_CTL, (uint32_t)filterChannelMask << ADC0_FILTER_CTL_SARC_FILTER_STATE_CLR_Pos);
}

/**
 * @brief sets the coefficient of operation in non sliding average filtering mode for the specified adc block filter
 * channel
 *
 * @param ADCx
 * @param filterChannel
 * @param power pass in a value that is a power = n,that is the actual average number of times is 2^n ,n = power
 *              configure the scope:0x0 ~ 0xF.
 */
void ADC_setFilterNonAverCoeff(ADC_Type *ADCx, uint8_t filterChannel, uint8_t power)
{
    uint8_t channel2BitNum   = 4; /* the number of filter channels corresponding to register bits */
    uint8_t bitL2BitH_Offset = 3;
    uint8_t channelBitH      = 0; /* the filter channel corresponds to the register bit value H */
    uint8_t channelBitL      = 0; /* the filter channel corresponds to the register bit value L*/

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));
    assert_param(IS_ADC_NOAVER_COEFF(power));

    channelBitL = POSITION_VAL(filterChannel) * channel2BitNum;
    channelBitH = channelBitL + bitL2BitH_Offset;

    MODIFY_REG(ADCx->NOAVER_COEFF, BITS_MASK(channelBitL, channelBitH), (uint32_t)power << channelBitL);
}

/**
 * @brief sets the fir filtering factor for the specified adc block virtual channel
 *
 * @param ADCx
 * @param filterChannel
 * @param coeffAddr
 * @param coeff
 */
void ADC_setFilterFIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterFIR_CoeffAddr coeffAddr, uint16_t coeff)
{
    uint16_t bitPosOfFIRChannel = 21;

    //todo  滤波系数格式需要修改
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));
    assert_param(IS_ADC_PARAM_13BIT(coeff));

    /***
     * set the read write indication of the filter
     * select the address data for the operating filter coefficients
     * set the filter factor value
     * */
    MODIFY_REG(ADCx->FIR_COEFF, ADC0_FIR_COEFF_SARC_FIR_COEFF_RW_Msk |
               ADC0_FIR_COEFF_SARC_FIR_COEFF_ADDR_Msk |
               ADC0_FIR_COEFF_SARC_FIR_COEFF_Msk,
               (uint32_t)(POSITION_VAL(filterChannel) << bitPosOfFIRChannel) |
               (uint32_t)(coeffAddr << ADC0_FIR_COEFF_SARC_FIR_COEFF_ADDR_Pos) |
               (coeff & 0x1FFF));
}

/**
 * @brief obtain the fir factor for the filter channel of the specified adc block
 *
 * @param ADCx
 * @param filterChannel
 * @return uint16_t
 */
uint16_t ADC_getFilterFIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterFIR_CoeffAddr coeffAddr)
{
    uint16_t bitPosOfFIRChannel = 21;
    uint16_t ret = 0;

    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));

    MODIFY_REG(ADCx->FIR_COEFF, ADC0_FIR_COEFF_SARC_FIR_COEFF_RW_Msk |
               ADC0_FIR_COEFF_SARC_FIR_COEFF_ADDR_Msk,
               (uint32_t)(POSITION_VAL(filterChannel) << bitPosOfFIRChannel) |
               (uint32_t)(coeffAddr << ADC0_FIR_COEFF_SARC_FIR_COEFF_ADDR_Pos));

    ret = READ_BIT(ADCx->FIR_COEFF_BACK, ADC0_FIR_COEFF_BACK_SARC_FIR_RBACK_COEFF_Msk);

    return ret;
}

/**
 * @brief gets the fir coefficient valid state
 *
 * @param ADCx
 * @return FlagStatus
 */
bool ADC_getFilterFIRCoeffStatus(ADC_Type *ADCx)
{
    bool ret = false;

    assert_param(IS_ADC_PERIPH(ADCx));

    ret = READ_BIT(ADCx->FIR_COEFF_BACK, ADC0_FIR_COEFF_BACK_SARC_FIR_RBACK_VAL_Msk)
            ? true : false;

    return ret;
}

/**
 * @brief 设置滤波通道的FIR阶数
 *
 * @param ADCx
 * @param filterChannel
 * @param len
 */
void ADC_setFilterFIRLen(ADC_Type *ADCx, uint8_t filterChannel, uint8_t len)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    //todo

    MODIFY_REG(ADCx->FIR_LENGTH[POSITION_VAL(filterChannel)].FIR_LEN, ADC0_FIR_LENGTH_FIR_LEN_FIR_LEN_Msk, len);
}

/**
 * @brief sets the iir filtering factor for the filter channel of the specified adc block
 *
 * @param ADCx
 * @param filterChannel
 * @param coeff
 */
void ADC_setFilterIIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, uint16_t coeff)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_GET_FILTER_CHANNEL(filterChannel));
    assert_param(IS_ADC_PARAM_13BIT(coeff));

    //todo 数据格式有变化

    MODIFY_REG(ADCx->IIR_COEFF[POSITION_VAL(filterChannel)].IIR_COEFF,
               ADC0_IIR_COEFF_IIR_COEFF_SARC_IIR_COEFF_Msk,
               (coeff & 0x1FFF));
}

/**
 * @brief 选择ADC模块中指定的DMA通道的请求信号
 *
 * @param ADCx
 * @param adc2dmaChannel
 * @param src
 */
void ADC_enableDMARequest(ADC_Type *ADCx, ADC_DMAChannel adc2dmaChannel, ADC_DMARequest src)
{
    assert_param(IS_ADC_PERIPH(ADCx));

    switch (adc2dmaChannel)
    {
    case ADC_DMA_CHANNEL0:
        if (src < ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 失能DMA的FIFO请求模式 */
            CLEAR_BIT(ADCx->FIFO_DMA_CTL, ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_0_Msk);
            /* 选择非FIFO的请求源 */
            MODIFY_REG(ADCx->DMA_CTL, ADC0_DMA_CTL_SARC_DMA_CH_0_Msk,
                       (uint32_t)src << ADC0_DMA_CTL_SARC_DMA_CH_0_Pos);
        }
        else if (src == ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_0_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_0_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_0_Msk);
        }
        else if (src == ADC_DMA_REQUEST_FILTER_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_0_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_0_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_0_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_0_Msk);
        }
        break;

    case ADC_DMA_CHANNEL1:
        if (src < ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 失能DMA的FIFO请求模式 */
            CLEAR_BIT(ADCx->FIFO_DMA_CTL, ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_1_Msk);
            /* 选择非FIFO的请求源 */
            MODIFY_REG(ADCx->DMA_CTL, ADC0_DMA_CTL_SARC_DMA_CH_1_Msk,
                       (uint32_t)src << ADC0_DMA_CTL_SARC_DMA_CH_1_Pos);
        }
        else if (src == ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_1_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_1_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_1_Msk);
        }
        else if (src == ADC_DMA_REQUEST_FILTER_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_1_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_1_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_1_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_1_Msk);
        }
        break;

    case ADC_DMA_CHANNEL2:
        if (src < ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 失能DMA的FIFO请求模式 */
            CLEAR_BIT(ADCx->FIFO_DMA_CTL, ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_2_Msk);
            /* 选择非FIFO的请求源 */
            MODIFY_REG(ADCx->DMA_CTL, ADC0_DMA_CTL_SARC_DMA_CH_2_Msk,
                       (uint32_t)src << ADC0_DMA_CTL_SARC_DMA_CH_2_Pos);
        }
        else if (src == ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_2_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_2_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_2_Msk);
        }
        else if (src == ADC_DMA_REQUEST_FILTER_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_2_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_2_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_2_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_2_Msk);
        }
        break;

    case ADC_DMA_CHANNEL3:
        if (src < ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 失能DMA的FIFO请求模式 */
            CLEAR_BIT(ADCx->FIFO_DMA_CTL, ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_3_Msk);
            /* 选择非FIFO的请求源 */
            MODIFY_REG(ADCx->DMA_CTL, ADC0_DMA_CTL_SARC_DMA_CH_3_Msk,
                       (uint32_t)src << ADC0_DMA_CTL_SARC_DMA_CH_3_Pos);
        }
        else if (src == ADC_DMA_REQUEST_PRE_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_3_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_3_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_3_Msk);
        }
        else if (src == ADC_DMA_REQUEST_FILTER_RESULT_FIFO)
        {
            /* 使能DMA的FIFO请求模式，选择FIFO类型的请求源 */
            MODIFY_REG(ADCx->FIFO_DMA_CTL,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_3_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_3_Msk,
                       ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_EN_3_Msk | ADC0_FIFO_DMA_CTL_SARC_FIFO_DMA_CH_3_Msk);
        }
        break;
    }
}

/**
 * @brief enable the filtering function of the specified adc block filter channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannelMask
 */
void ADC_enablePreFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannelMask));

    SET_BIT(ADCx->PC_GRP[POSITION_VAL(filterChannelMask)].PC_CTL, POSITION_VAL(filterChannelMask));
}

/**
 * @brief disable the filtering function of the specified adc block filter channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannelMask
 */
void ADC_disablePreFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannelMask));

    CLEAR_BIT(ADCx->PC_GRP[POSITION_VAL(filterChannelMask)].PC_CTL, POSITION_VAL(filterChannelMask));
}

/**
 * @brief enables filtering that specifies the adc Preprocess  channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannel
 */
void ADC_enablePreFilter(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    SET_BIT(ADCx->PC_GRP[POSITION_VAL(filterChannel)].PC_CTL, ADC0_PC_GRP_PC_CTL_FLT_EN_Msk);
    SET_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_EN_Msk);
}

/**
 * @brief disable filtering that specifies the adc Preprocess  channel
 *
 * @param ADCx
 *      @arg ADC0
 *      @arg ADC1
 * @param filterChannel
 */
void ADC_disablePreFilter(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    CLEAR_BIT(ADCx->PC_GRP[POSITION_VAL(filterChannel)].PC_CTL, ADC0_PC_GRP_PC_CTL_FLT_EN_Msk);
    CLEAR_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_EN_Msk);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 * @param gain
 */
void ADC_setPreFilterIdataGain(ADC_Type *ADCx, uint16_t filterChannel, ADC_PreFilterInputDataGain gain)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));
    assert_param(gain <= ADC_PREFIL_INPUT_DATA_DIV4);

    MODIFY_REG(ADCx->PFC_GRP[POSITION_VAL(
                                 filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_IDAT_GAIN_ADJ_Msk,
               (uint32_t)gain << ADC0_PFC_GRP_PFC_CTL_PFLT_IDAT_GAIN_ADJ_Pos);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 * @param gain
 */
void ADC_setPreFilterOdataR(ADC_Type *ADCx, uint16_t filterChannel, ADC_PreFilterOutputDataGain gain)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));
    assert_param(gain <= ADC_PREFIL_OUTPUT_GAIN_127);

    MODIFY_REG(ADCx->PFC_GRP[POSITION_VAL(
                                 filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_R_ARG_Msk,
               (uint32_t)gain << ADC0_PFC_GRP_PFC_CTL_PFLT_R_ARG_Pos);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 */
void ADC_setPreFilterResultClip(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    SET_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_CLIP_Msk);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 */
void ADC_setPreFilterResultWrap(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    SET_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_ACC_OUT_WRAP_SEL_Msk);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 */
void ADC_setPreFilterClearIdataBuffer(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    SET_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_CLR_Msk);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 */
void ADC_setPreFilterRdyClearBuffer(ADC_Type *ADCx, uint16_t filterChannel)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));

    SET_BIT(ADCx->PFC_GRP[POSITION_VAL(filterChannel)].PFC_CTL, ADC0_PFC_GRP_PFC_CTL_PFLT_CLR_Msk);
}

/**
 * @brief
 *
 * @param ADCx
 * @param filterChannel
 * @param type
 */
void ADC_setPreFilterType(ADC_Type *ADCx, uint16_t filterChannel, ADC_FilterType type)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(IS_ADC_FILTER_CHANNEL(filterChannel));
    assert_param(type <= ADC_FILTER_TYPE_IIR);

    MODIFY_REG(ADCx->PFC_PARAM4,
               (ADC0_PFC_PARAM4_PFLT_TYPE_Msk |
                ADC0_PFC_PARAM4_PFLT_NUM_Msk),
               (type << ADC0_PFC_PARAM4_PFLT_TYPE_Pos) |
               (POSITION_VAL(filterChannel) << ADC0_PFC_PARAM4_PFLT_NUM_Pos)
               );
}

/**
 * @brief
 *
 * @param ADCx
 * @param p_cnt FIR: P=order+1 , Q=0
 * @param coeff
 */
void ADC_setPreFilterFIRCoeff(ADC_Type *ADCx, uint8_t p_cnt, uint16_t *coeff)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(p_cnt <= 8);

    uint32_t Addr;
    uint32_t i = 0;

    MODIFY_REG(ADCx->PFC_PARAM4,
               (ADC0_PFC_PARAM4_Q_ARG_Msk | ADC0_PFC_PARAM4_P_ARG_Msk),
               (p_cnt << ADC0_PFC_PARAM4_P_ARG_Pos));
    while (i < (p_cnt + 1))
    {
        Addr = (uint32_t)&ADCx->PFC_PARAM0 + (i / 2) * 0x4;
        if ((i % 2) == 0)
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_0_COEF_Msk, *coeff++);
        }
        else
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_1_COEF_Msk, *coeff++ << ADC0_PFC_PARAM0_PFLT_1_COEF_Pos);
        }
        i++;
    }

    SET_BIT(ADCx->PFC_PARAM4, ADC0_PFC_PARAM4_PFLT_RDY_Msk);
    while (READ_BIT(ADCx->PFC_PARAM4, ADC0_PFC_PARAM4_PFLT_RDY_Msk));
}

/**
 * @brief IIR: P=feedforword , Q=order
 *
 * @param ADCx
 * @param p_cnt
 * @param q_cnt     q_cnt < 4
 * @param pcoeff
 * @param qcoeff
 */
void ADC_setPreFilterIIRCoeff(ADC_Type *ADCx, uint8_t p_cnt, uint8_t q_cnt, uint16_t *pcoeff, uint16_t *qcoeff)
{
    assert_param(IS_ADC_PERIPH(ADCx));
    assert_param(p_cnt <= 5);
    assert_param(q_cnt <= 4);

    uint32_t Addr;
    uint32_t i = 0;

    MODIFY_REG(ADCx->PFC_PARAM4,
               (ADC0_PFC_PARAM4_Q_ARG_Msk | ADC0_PFC_PARAM4_P_ARG_Msk),
               (p_cnt << ADC0_PFC_PARAM4_P_ARG_Pos) | (q_cnt << ADC0_PFC_PARAM4_Q_ARG_Pos));
    while (i < p_cnt)
    {
        Addr = (uint32_t)&ADCx->PFC_PARAM0 + (i / 2) * 0x4;
        if ((i % 2) == 0)
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_0_COEF_Msk, *pcoeff++);
        }
        else
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_1_COEF_Msk, *pcoeff++ << ADC0_PFC_PARAM0_PFLT_1_COEF_Pos);
        }
        i++;
    }
    while (i < (p_cnt + q_cnt))
    {
        Addr = (uint32_t)&ADCx->PFC_PARAM0 + (i / 2) * 0x4;
        if ((i % 2) == 0)
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_0_COEF_Msk, *qcoeff++);
        }
        else
        {
            MODIFY_REG(REG32(Addr), ADC0_PFC_PARAM0_PFLT_1_COEF_Msk, *qcoeff++ << ADC0_PFC_PARAM0_PFLT_1_COEF_Pos);
        }
        i++;
    }

    SET_BIT(ADCx->PFC_PARAM4, ADC0_PFC_PARAM4_PFLT_RDY_Msk);
    while (READ_BIT(ADCx->PFC_PARAM4, ADC0_PFC_PARAM4_PFLT_RDY_Msk));
}

/******************* end program ***************************/
