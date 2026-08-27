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
#include "et6x_acmp.h"

/**
 * @addtogroup ET3101_Driver
 * @{
 */

/**
 * @defgroup ACMP ACMP
 * @brief Analog Comparator Driver Library
 * @{
 */
/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/*! Parameter validity check for ACMP peripheral  */
#define IS_ACMP_PERIPHERAL(x) \
        (((x) == ACMP0) ||        \
         ((x) == ACMP1) ||        \
         ((x) == ACMP2) ||        \
         ((x) == ACMP3))

/*! Parameter validity check for ACMP channel */
#define IS_ACMP_CHANNEL(ch)      \
        (((ch) == ACMP_CHANNEL_H) || \
         ((ch) == ACMP_CHANNEL_L))

/*! Parameter validity check for ACMP positive input signal */
#define IS_ACMP_INPUT(input)                 \
        (((input) == ACMP_INPUT_MUX_SELECT_0) || \
         ((input) == ACMP_INPUT_MUX_SELECT_1) || \
         ((input) == ACMP_INPUT_MUX_SELECT_2) || \
         ((input) == ACMP_INPUT_MUX_SELECT_3) || \
         ((input) == ACMP_INPUT_MUX_SELECT_4) || \
         ((input) == ACMP_INPUT_MUX_SELECT_5))

/*! Parameter validity check for ACMP negative input signal */
#define IS_ACMP_REF(input)                 \
        (((input) == ACMP_REF_MUX_DAC) ||   \
         ((input) == ACMP_REF_MUX_SELECT_0) || \
         ((input) == ACMP_REF_MUX_SELECT_1) || \
         ((input) == ACMP_REF_MUX_SELECT_2))


/*! Parameter validity check for ACMP hysteresis value */
#define IS_ACMP_HYSTERESIS_VALUE(val)    \
        (((val) == HYSTERESIS_VALUE_0MV) ||  \
         ((val) == HYSTERESIS_VALUE_7MV) ||  \
         ((val) == HYSTERESIS_VALUE_14MV) || \
         ((val) == HYSTERESIS_VALUE_23MV) || \
         ((val) == HYSTERESIS_VALUE_36MV) || \
         ((val) == HYSTERESIS_VALUE_43MV) || \
         ((val) == HYSTERESIS_VALUE_52MV) || \
         ((val) == HYSTERESIS_VALUE_62MV))


/*! Parameter validity check for ACMP blanking width */
#define IS_ACMP_BLK_WIDTH(width)       ((width) <= BLK_WIDTH_MAX)

/*! Parameter validity check for ACMP filter width */
#define IS_ACMP_FILTER_WIDTH(width)    ((width) <= FILTER_WIDTH_MAX)

/*! Parameter validity check for ACMP IT mask */
#define IS_ACMP_IT_MASK(mask)          (((mask)&ACMP_IT_ALL_MASK) != 0)

/*! Parameter validity check for ACMP DAC trigger select */
#define IS_ACMP_DAC_TRIGGER_SEL(SEL) \
        ((SEL == ACMP_DAC_TRIGGER_SEL_SW) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_STIM) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_ETIM) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_SRPWM) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_SELF_TX_DONE) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_ACOMP) || \
         (SEL == ACMP_DAC_TRIGGER_SEL_DMA))

/*! Parameter validity check for ACMP DAC trigger delay */
#define IS_ACMP_DAC_TRIGGER_DLY(delay)    (delay <= TRIGGER_DLY_MAX)

/*! Parameter validity check for ACMP DAC load mode */
#define IS_ACMP_DAC_LoadMode(LOADMODE) \
        ((LOADMODE == ACMP_DAC_LOADMODE_IMMEDIATE) || \
         (LOADMODE == ACMP_DAC_LOADMODE_SHADOW))

/*! Parameter validity check for ACMP DAC reference */
#define IS_ACMP_DAC_REF(REF)      ((REF == ACMP_DAC_REF_PAD) || (REF == ACMP_DAC_REF_LDO))

/*! Parameter validity check for ACMP DAC data width */
#define IS_ACMP_DAC_DATA(data)    (data <= 0xFFFFU)

/*! channel A and channel B position in analog set register */
#define CMP0_ANA_SET_POS            (0U)
#define CMP1_ANA_SET_POS            (16U)

/*! offset adjust mask */
#define OFFSET_ADJ_MSK              (0x1FFFU)

/*! gain adjust mask */
#define GAIN_ADJ_MSK                (0x7FFU)

/* ADC input enable mask */
#define ADC_A3_INPUT_ENABLE_MASK    (1U << 5U)
#define ADC_B1_INPUT_ENABLE_MASK    (1U << 6U)
#define ADC_C1_INPUT_ENABLE_MASK    (1U << 7U)

/* Private macro -------------------------------------------------------------*/
/* Private variables ---------------------------------------------------------*/
/* Private function prototypes -----------------------------------------------*/
/* Exported functions --------------------------------------------------------*/

/**
 * @brief Enable ACMP
 *
 * @param ACMPx  select ACMP device
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel  select channel in ACMP
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_enableModule(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP0_OUTEN_Msk);
        SET_BIT(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP0_EN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP1_OUTEN_Msk);
        SET_BIT(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP1_EN_Msk);
    }
}

/**
 * @brief Disable ACMP
 *
 * @param ACMPx  select ACMP device
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel  select channel in ACMP
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_disableModule(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP0_OUTEN_Msk);
        CLEAR_BIT(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP0_EN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP1_OUTEN_Msk);
        CLEAR_BIT(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP1_EN_Msk);
    }
}

/**
 * @brief Configure the comparator of the ACMP module
 *
 * @param ACMPx  select ACMP device
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel  select channel in ACMP
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param config  Pointer to the configuration structure \b ACMP_Comparator
 *
 */
void ACMP_configComparator(ACMP_Type *ACMPx, uint8_t channel, ACMP_Comparator *config)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_INPUT(config->cmpPositiveInputSelect));
    assert_param(IS_ACMP_REF(config->cmpNegativeInputSelect));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP0_RVRS_Msk,
                   (uint32_t)config->digitalOutputPolarityReverseEn << ACMP0_CMP_DIG_SET_CMP0_RVRS_Pos);
        MODIFY_REG(ACMPx->CMP_ANA_SET,
                   (ACMP0_CMP_ANA_SET_CMP0_IN_SEL_Msk | ACMP0_CMP_ANA_SET_CMP0_REF_SEL_Msk |
                    ACMP0_CMP_ANA_SET_CMP0_INV_SEL_Msk),
                   ((uint32_t)config->cmpNegativeInputSelect << ACMP0_CMP_ANA_SET_CMP0_REF_SEL_Pos) |
                   ((uint32_t)config->cmpPositiveInputSelect << ACMP0_CMP_ANA_SET_CMP0_IN_SEL_Pos) |
                   ((uint32_t)config->analogOutputPolarityReverseEn << ACMP0_CMP_ANA_SET_CMP0_INV_SEL_Pos));
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_ASYNCHEN_Msk, (uint32_t)config->asyncPathEn << ACMP0_CTL_ASYNCHEN_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->CMP_DIG_SET, ACMP0_CMP_DIG_SET_CMP1_RVRS_Msk,
                   (uint32_t)config->digitalOutputPolarityReverseEn << ACMP0_CMP_DIG_SET_CMP1_RVRS_Pos);
        MODIFY_REG(ACMPx->CMP_ANA_SET,
                   (ACMP0_CMP_ANA_SET_CMP1_IN_SEL_Msk | ACMP0_CMP_ANA_SET_CMP1_REF_SEL_Msk |
                    ACMP0_CMP_ANA_SET_CMP1_INV_SEL_Msk),
                   ((uint32_t)config->cmpNegativeInputSelect << ACMP0_CMP_ANA_SET_CMP1_REF_SEL_Pos) |
                   ((uint32_t)config->cmpPositiveInputSelect << ACMP0_CMP_ANA_SET_CMP1_IN_SEL_Pos) |
                   ((uint32_t)config->analogOutputPolarityReverseEn << ACMP0_CMP_ANA_SET_CMP1_INV_SEL_Pos));
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_ASYNCLEN_Msk, (uint32_t)config->asyncPathEn << ACMP0_CTL_ASYNCLEN_Pos);
    }
}

/**
 * @brief Output configuration
 *
 * @param ACMPx  select ACMP device
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel  select channel in ACMP
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param config Pointer to the configuration structure ACMP_TripOut
 *      - ctripOut XBAR (GPIO)
 *      - ctrip PWM
 */
void ACMP_configOutputs(ACMP_Type *ACMPx, uint8_t channel, ACMP_TripOut *config)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_CTRIPOUTHSEL_Msk, (uint32_t)config->ctripOut << ACMP0_CTL_CTRIPOUTHSEL_Pos);
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_CTRIPHSEL_Msk, (uint32_t)config->ctrip << ACMP0_CTL_CTRIPHSEL_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_CTRIPOUTLSEL_Msk, (uint32_t)config->ctripOut << ACMP0_CTL_CTRIPOUTLSEL_Pos);
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_CTRIPLSEL_Msk, (uint32_t)config->ctrip << ACMP0_CTL_CTRIPLSEL_Pos);
    }
}

/**
 * @brief Get ACMP output status
 *
 * @param ACMPx  select ACMP device
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @return uint32_t  all interrupt status masks
 */
uint32_t ACMP_getStatus(ACMP_Type *ACMPx)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    return READ_BIT(ACMPx->INT_STATUS_RPT, ACMP_IT_ALL_MASK);
}

/**
 * @brief Sets the configuration for the internal comparator DACs.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param config Pointer to the configuration structure for the DAC
 */
void ACMP_configDAC(ACMP_Type *ACMPx, uint8_t channel, ACMP_DAC_Config *config)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_DAC_LoadMode(config->loadMode));
    assert_param(IS_ACMP_DAC_TRIGGER_SEL(config->triggerSel));
    assert_param(IS_ACMP_DAC_TRIGGER_DLY(config->triggerDelay));
    assert_param(IS_ACMP_DAC_REF(config->dacRefSelect));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->DAC_TRG_POLR, ACMP0_DAC_TRG_POLR_CMPC_DAC0_TRG_POLR_Msk,
                   (uint32_t)config->triggerInvertEn << ACMP0_DAC_TRG_POLR_CMPC_DAC0_TRG_POLR_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_MASK, ACMP0_DAC_TRG_MASK_CMPC_DAC0_TRG_MASK_Msk,
                   (uint32_t)config->triggerMask << ACMP0_DAC_TRG_MASK_CMPC_DAC0_TRG_MASK_Pos);
        MODIFY_REG(ACMPx->DAC_LDMOD, ACMP0_DAC_LDMOD_CMPC_DAC0_LDMOD_Msk,
                   (uint32_t)config->loadMode << ACMP0_DAC_LDMOD_CMPC_DAC0_LDMOD_Pos);
        MODIFY_REG(ACMPx->DAC_TRGEN, ACMP0_DAC_TRGEN_CMPC_DAC0_TRGEN_Msk,
                   (uint32_t)config->triggerEn << ACMP0_DAC_TRGEN_CMPC_DAC0_TRGEN_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Msk,
                   (uint32_t)config->triggerSel << ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_DLY, ACMP0_DAC_TRG_DLY_CMPC_DAC0_TRG_DLY_Msk,
                   (uint32_t)config->triggerDelay << ACMP0_DAC_TRG_DLY_CMPC_DAC0_TRG_DLY_Pos);
        MODIFY_REG(ACMPx->DAC_PRM,
                   ACMP0_DAC_PRM_DAC0_OUT_DAT_FMAT_SEL_Msk | ACMP0_DAC_PRM_DAC0_TDAT_SEL_Msk | ACMP0_DAC_PRM_DAC0_OUT_RVRS_SEL_Msk,
                   ((uint32_t)config->dacOutputReverseEn << ACMP0_DAC_PRM_DAC0_OUT_RVRS_SEL_Pos) |
                   ((uint32_t)config->outputFormat << ACMP0_DAC_PRM_DAC0_OUT_DAT_FMAT_SEL_Pos) |
                   ((uint32_t)config->tdatSel << ACMP0_DAC_PRM_DAC0_TDAT_SEL_Pos));
        MODIFY_REG(ACMPx->HRAMP_PRM0,
                   ACMP0_HRAMP_PRM0_DACSOURCE_Msk,
                   ((uint32_t)config->dacsrcSel << ACMP0_HRAMP_PRM0_DACSOURCE_Pos));
        MODIFY_REG(ACMPx->CMP_ANA_SET,
                   ACMP0_CMP_ANA_SET_CMPC_DAC0_EN_Msk | ACMP0_CMP_ANA_SET_CMPC_DAC0_REF_SEL_Msk,
                   ((uint32_t)config->dacToCmpEn << ACMP0_CMP_ANA_SET_CMPC_DAC0_EN_Pos) |
                   ((uint32_t)config->dacRefSelect << ACMP0_CMP_ANA_SET_CMPC_DAC0_REF_SEL_Pos));
    }
    else
    {
        MODIFY_REG(ACMPx->DAC_TRG_POLR, ACMP0_DAC_TRG_POLR_CMPC_DAC1_TRG_POLR_Msk,
                   (uint32_t)config->triggerInvertEn << ACMP0_DAC_TRG_POLR_CMPC_DAC1_TRG_POLR_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_MASK, ACMP0_DAC_TRG_MASK_CMPC_DAC1_TRG_MASK_Msk,
                   (uint32_t)config->triggerMask << ACMP0_DAC_TRG_MASK_CMPC_DAC1_TRG_MASK_Pos);
        MODIFY_REG(ACMPx->DAC_LDMOD, ACMP0_DAC_LDMOD_CMPC_DAC1_LDMOD_Msk,
                   (uint32_t)config->loadMode << ACMP0_DAC_LDMOD_CMPC_DAC1_LDMOD_Pos);
        MODIFY_REG(ACMPx->DAC_TRGEN, ACMP0_DAC_TRGEN_CMPC_DAC1_TRGEN_Msk,
                   (uint32_t)config->triggerEn << ACMP0_DAC_TRGEN_CMPC_DAC1_TRGEN_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Msk,
                   (uint32_t)config->triggerSel << ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Pos);
        MODIFY_REG(ACMPx->DAC_TRG_DLY, ACMP0_DAC_TRG_DLY_CMPC_DAC1_TRG_DLY_Msk,
                   (uint32_t)config->triggerDelay << ACMP0_DAC_TRG_DLY_CMPC_DAC1_TRG_DLY_Pos);
        MODIFY_REG(ACMPx->DAC_PRM,
                   ACMP0_DAC_PRM_DAC1_OUT_DAT_FMAT_SEL_Msk | ACMP0_DAC_PRM_DAC1_TDAT_SEL_Msk | ACMP0_DAC_PRM_DAC1_OUT_RVRS_SEL_Msk,
                   ((uint32_t)config->dacOutputReverseEn << ACMP0_DAC_PRM_DAC1_OUT_RVRS_SEL_Pos) |
                   ((uint32_t)config->outputFormat << ACMP0_DAC_PRM_DAC1_OUT_DAT_FMAT_SEL_Pos) |
                   ((uint32_t)config->tdatSel << ACMP0_DAC_PRM_DAC1_TDAT_SEL_Pos));
        MODIFY_REG(ACMPx->LRAMP_PRM0,
                   ACMP0_LRAMP_PRM0_DACSOURCE_Msk,
                   ((uint32_t)config->dacsrcSel << ACMP0_LRAMP_PRM0_DACSOURCE_Pos));
        MODIFY_REG(ACMPx->CMP_ANA_SET,
                   ACMP0_CMP_ANA_SET_CMPC_DAC1_EN_Msk | ACMP0_CMP_ANA_SET_CMPC_DAC1_REF_SEL_Msk,
                   ((uint32_t)config->dacToCmpEn << ACMP0_CMP_ANA_SET_CMPC_DAC1_EN_Pos) |
                   ((uint32_t)config->dacRefSelect << ACMP0_CMP_ANA_SET_CMPC_DAC1_REF_SEL_Pos));
    }
}

/**
 * @brief  Sets the value of the internal DAC for the specified channel.This function sets the value of the internal
 * Digital-to-Analog Converter (DAC)
 *  for the specified channel of the Analog Comparator (ACMP) module.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param data The 16-bit data value to set for the DAC.
 */
void ACMP_setDACValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t data)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_DAC_DATA(data));

    if (channel == ACMP_CHANNEL_H)
    {
        WRITE_REG(ACMPx->DAC0_TDAT, data);
    }
    else
    {
        WRITE_REG(ACMPx->DAC1_TDAT, data);
    }
}

/**
 * @brief This function clears the latch of the digital filter for the specified channel of the Analog Comparator (ACMP)
 * module.
 * It first checks if the provided ACMP peripheral is valid
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_clearFilterLatch(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_HLATCHCLR_Msk);
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_HLATCHCLR_Msk);
    }
    else
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_LLATCHCLR_Msk);
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_LLATCHCLR_Msk);
    }
}

/**
 * @brief Initializes the digital filter
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_initFilter(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPL_FILINIT_Msk);
    }
    else
    {
        SET_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPH_FILINIT_Msk);
    }
}

/**
 * @brief Sets the ramp generator direct.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param dir The ramp generator direction.
 *      - ACMP_RAMP_DIR_UP
 *      - ACMP_RAMP_DIR_DOWN
 */
void ACMP_setRampDir(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_Direction dir)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_DIR_Msk,
                   (uint32_t)dir << ACMP0_HRAMP_PRM0_DIR_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_DIR_Msk,
                   (uint32_t)dir << ACMP0_LRAMP_PRM0_DIR_Pos);
    }
}

/**
 * @brief Sets the ramp generator xtrig.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param trig The ramp generator trigger source.
 *      - ACMP_RAMP_TRIG_EXTERNAL
 *      - ACMP_RAMP_TRIG_OTHERRAMP_TRIGOFF
 */
void ACMP_setRampTrigSel(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_xTrigSel trig)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_XTRIG_Msk,
                   (uint32_t)trig << ACMP0_HRAMP_PRM0_XTRIG_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_XTRIG_Msk,
                   (uint32_t)trig << ACMP0_LRAMP_PRM0_XTRIG_Pos);
    }
}

/**
 * @brief Sets the ramp generator clock prescale value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The 12-bit prescale value to set for the ramp generator clock.
 */
void ACMP_setRampClkPrescale(ACMP_Type *ACMPx, uint8_t channel, uint16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_CLKPRESCALE_Msk,
                   (uint32_t)value << ACMP0_HRAMP_PRM0_CLKPRESCALE_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_CLKPRESCALE_Msk,
                   (uint32_t)value << ACMP0_LRAMP_PRM0_CLKPRESCALE_Pos);
    }
}

/**
 * @brief Sets the ramp generator maximum reference value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The 16-bit value to set as the maximum reference for the ramp generator.
 */
void ACMP_setMaxRampValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        WRITE_REG(ACMPx->HRAMP_PRM2, value);
    }
    else
    {
        WRITE_REG(ACMPx->LRAMP_PRM2, value);
    }
}

/**
 * @brief Gets the ramp generator maximum reference value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return maxvalue The maximum reference value for the ramp generator.
 */
uint16_t ACMP_getMaxRampValue(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->HRAMP_STS1,
                                   ACMP0_HRAMP_STS1_MAXREFA_RPT_Msk) >> ACMP0_HRAMP_STS1_MAXREFA_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->LRAMP_STS1,
                                   ACMP0_LRAMP_STS1_MAXREFA_RPT_Msk) >> ACMP0_LRAMP_STS1_MAXREFA_RPT_Pos);
    }
}

/**
 * @brief Sets the ramp generator decrement value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The 16-bit value to set as the decrement value for the ramp generator.
 */
void ACMP_setRampDecValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        WRITE_REG(ACMPx->HRAMP_PRM1, value);
    }
    else
    {
        WRITE_REG(ACMPx->LRAMP_PRM1, value);
    }
}

/**
 * @brief Gets the ramp generator decrement value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return stepvalue The current decrement value of the ramp generator.
 */
uint16_t ACMP_getRampDecValue(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->HRAMP_STS1,
                                   ACMP0_HRAMP_STS1_DECVALA_RPT_Msk) >> ACMP0_HRAMP_STS1_DECVALA_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->LRAMP_STS1,
                                   ACMP0_LRAMP_STS1_DECVALA_RPT_Msk) >> ACMP0_LRAMP_STS1_DECVALA_RPT_Pos);
    }
}

/**
 * @brief Sets the ramp generator delay value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The load selection.
 */
void ACMP_selectRampLoad(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_LoadSel value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_LOADSEL_Msk, (uint32_t)value << ACMP0_HRAMP_PRM0_LOADSEL_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_LOADSEL_Msk, (uint32_t)value << ACMP0_LRAMP_PRM0_LOADSEL_Pos);
    }
}

/**
 * @brief Sets the ramp generator delay value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The 13-bit value to set as the delay for the ramp generator.
 */
void ACMP_setRampDelayValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_DLYS_Msk, (uint32_t)value << ACMP0_HRAMP_PRM0_DLYS_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_DLYS_Msk, (uint32_t)value << ACMP0_LRAMP_PRM0_DLYS_Pos);
    }
}

/**
 * @brief Select the rampsts load.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value The load selection.
 */
uint16_t ACMP_getRampDelayValue(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->HRAMP_STS0, ACMP0_HRAMP_STS0_DLYA_RPT_Msk) >> ACMP0_HRAMP_STS0_DLYA_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->LRAMP_STS0, ACMP0_LRAMP_STS0_DLYA_RPT_Msk) >> ACMP0_LRAMP_STS0_DLYA_RPT_Pos);
    }
}

/**
 * @brief Configures sync source for comparator
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param syncSource The synchronization source to set for the comparator.
 *      - ACMP_DAC_TRIGGER_SEL_SW
 *      - ACMP_DAC_TRIGGER_SEL_STIM
 *      - ACMP_DAC_TRIGGER_SEL_ETIM
 *      - ACMP_DAC_TRIGGER_SEL_SRPWM
 *      - ACMP_DAC_TRIGGER_SEL_SELF_TX_DONE
 *      - ACMP_DAC_TRIGGER_SEL_ACOMP
 *      - ACMP_DAC_TRIGGER_SEL_DMA
 */
void ACMP_configureSyncSource(ACMP_Type *ACMPx, uint8_t channel, uint16_t syncSource)
{
    uint32_t trg_en;
    uint32_t trg_mask;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_DAC_TRIGGER_SEL(syncSource));

    if (channel == ACMP_CHANNEL_H)
    {
        if (((READ_REG(ACMPx->DAC_TRG_MASK) & ACMP0_DAC_TRG_MASK_CMPC_DAC0_TRG_MASK_Msk) == 0) ||
            ((READ_REG(ACMPx->DAC_TRGEN) & ACMP0_DAC_TRGEN_CMPC_DAC0_TRGEN_Msk) != 0))
        {
            trg_en   = ACMPx->DAC_TRGEN;
            trg_mask = ACMPx->DAC_TRG_MASK;
            MODIFY_REG(ACMPx->DAC_TRG_MASK, ACMP0_DAC_TRG_MASK_CMPC_DAC0_TRG_MASK_Msk,
                       (uint32_t)MASKED << ACMP0_DAC_TRG_MASK_CMPC_DAC0_TRG_MASK_Pos);
            MODIFY_REG(ACMPx->DAC_TRGEN, ACMP0_DAC_TRGEN_CMPC_DAC0_TRGEN_Msk,
                       (uint32_t)DISABLE << ACMP0_DAC_TRGEN_CMPC_DAC0_TRGEN_Pos);
            MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Msk,
                       (uint32_t)syncSource << ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Pos);
            WRITE_REG(ACMPx->DAC_TRGEN, trg_en);
            WRITE_REG(ACMPx->DAC_TRG_MASK, trg_mask);
        }
        else
        {
            MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Msk,
                       (uint32_t)syncSource << ACMP0_DAC_TRG_SEL_CMPC_DAC0_TRG_SEL_Pos);
        }
    }
    else
    {
        if (((READ_REG(ACMPx->DAC_TRG_MASK) & ACMP0_DAC_TRG_MASK_CMPC_DAC1_TRG_MASK_Msk) == 0) ||
            ((READ_REG(ACMPx->DAC_TRGEN) & ACMP0_DAC_TRGEN_CMPC_DAC1_TRGEN_Msk) != 0))
        {
            trg_en   = ACMPx->DAC_TRGEN;
            trg_mask = ACMPx->DAC_TRG_MASK;
            MODIFY_REG(ACMPx->DAC_TRG_MASK, ACMP0_DAC_TRG_MASK_CMPC_DAC1_TRG_MASK_Msk,
                       (uint32_t)MASKED << ACMP0_DAC_TRG_MASK_CMPC_DAC1_TRG_MASK_Pos);
            MODIFY_REG(ACMPx->DAC_TRGEN, ACMP0_DAC_TRGEN_CMPC_DAC1_TRGEN_Msk,
                       (uint32_t)DISABLE << ACMP0_DAC_TRGEN_CMPC_DAC1_TRGEN_Pos);
            MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Msk,
                       (uint32_t)syncSource << ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Pos);
            WRITE_REG(ACMPx->DAC_TRGEN, trg_en);
            WRITE_REG(ACMPx->DAC_TRG_MASK, trg_mask);
        }
        else
        {
            MODIFY_REG(ACMPx->DAC_TRG_SEL, ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Msk,
                       (uint32_t)syncSource << ACMP0_DAC_TRG_SEL_CMPC_DAC1_TRG_SEL_Pos);
        }
    }
}

/**
 * @brief Sets the comparator hysteresis settings.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value hysteresis value to set for the comparator.
 *      - HYSTERESIS_VALUE_0MV
 *      - HYSTERESIS_VALUE_7MV
 *      - HYSTERESIS_VALUE_14MV
 *      - HYSTERESIS_VALUE_23MV
 *      - HYSTERESIS_VALUE_36MV
 *      - HYSTERESIS_VALUE_43MV
 *      - HYSTERESIS_VALUE_52MV
 *      - HYSTERESIS_VALUE_62MV
 * @param dir The direction of the hysteresis
 *      - ACMP_HYSTERESIS_UP
 *      - ACMP_HYSTERESIS_DOWN
 */
void ACMP_setHysteresis(ACMP_Type *ACMPx, uint8_t channel, ACMP_HysteresisValue value, ACMP_HysteresisDirection dir)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_HYSTERESIS_VALUE(value));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP0_HYST_Msk | ACMP0_CMP_ANA_SET_CMP0_HYS_SEL_Msk,
                   ((uint32_t)value <<
                    ACMP0_CMP_ANA_SET_CMP0_HYST_Pos) | ((uint32_t)dir << ACMP0_CMP_ANA_SET_CMP0_HYS_SEL_Pos));
    }
    else
    {
        MODIFY_REG(ACMPx->CMP_ANA_SET, ACMP0_CMP_ANA_SET_CMP1_HYST_Msk | ACMP0_CMP_ANA_SET_CMP1_HYS_SEL_Msk,
                   ((uint32_t)value <<
                    ACMP0_CMP_ANA_SET_CMP1_HYST_Pos) | ((uint32_t)dir << ACMP0_CMP_ANA_SET_CMP1_HYS_SEL_Pos));
    }
}

/**
 * @brief Enables reset of comparator digital filter output latch on SYNC
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_enableLatchResetOnSYNC(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_TRIG_SRC_CLR_LEN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_TRIG_SRC_CLR_HEN_Msk);
    }
}

/**
 * @brief Disables reset of comparator digital filter output latch on SYNC
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_disableLatchResetOnSYNC(ACMP_Type *ACMPx, uint8_t channel)
{
    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_TRIG_SRC_CLR_LEN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_TRIG_SRC_CLR_HEN_Msk);
    }
}

/**
 * @brief Sets the ePWM module blanking signal that holds trip in reset.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param blankingWidth The width of the blanking signal. the range is 0~0xFFFF.
 * @param blankingDelay The delay of the blanking signal. the range is 0~0xFFFF.
 */
void ACMP_configBlanking(ACMP_Type *ACMPx, uint8_t channel, uint16_t blankingWidth, uint16_t blankingDelay)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));
    assert_param(IS_ACMP_BLK_WIDTH(blankingWidth));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->BLK_PRM0, ACMP0_BLK_PRM0_HWDTH_Msk,
                   (uint32_t)blankingWidth << ACMP0_BLK_PRM0_HWDTH_Pos);
        MODIFY_REG(ACMPx->BLK_PRM1, ACMP0_BLK_PRM1_HDLY_Msk,
                   (uint32_t)blankingDelay << ACMP0_BLK_PRM1_HDLY_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->BLK_PRM0, ACMP0_BLK_PRM0_LWDTH_Msk,
                   (uint32_t)blankingWidth << ACMP0_BLK_PRM0_LWDTH_Pos);
        MODIFY_REG(ACMPx->BLK_PRM1, ACMP0_BLK_PRM1_LDLY_Msk,
                   (uint32_t)blankingDelay << ACMP0_BLK_PRM1_LDLY_Pos);
    }
}

/**
 * @brief Enables an ePWM blanking signal to hold trip in reset.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_enableBlanking(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->CMP_BLK_SET, ACMP0_CMP_BLK_SET_CMP0_BLKEN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->CMP_BLK_SET, ACMP0_CMP_BLK_SET_CMP1_BLKEN_Msk);
    }
}

/**
 * @brief Disables an ePWM blanking signal from holding trip in reset.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_disableBlanking(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->CMP_BLK_SET, ACMP0_CMP_BLK_SET_CMP0_BLKEN_Msk);
        // CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_HSYNCCLREN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->CMP_BLK_SET, ACMP0_CMP_BLK_SET_CMP1_BLKEN_Msk);
        // CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_LSYNCCLREN_Msk);
    }
}

/**
 * @brief Enables an ePWM blanking signal to hold trip in reset.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_setBlankingHold(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_HSYNCCLREN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->CTL, ACMP0_CTL_LSYNCCLREN_Msk);
    }
}

/**
 * @brief Disables an ePWM blanking signal from holding trip in reset.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_clearBlankingHold(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_HSYNCCLREN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->CTL, ACMP0_CTL_LSYNCCLREN_Msk);
    }
}

/**
 * @brief Configures the digital filter of the high comparator.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param filterInputSel The input source for the digital filter.
 *      - ACMP_FILTER_INPUT_ACMP_OUT
 *      - ACMP_FILTER_INPUT_0
 *      - ACMP_FILTER_INPUT_1
 *      - ACMP_FILTER_INPUT_2
 *      - ACMP_FILTER_INPUT_3
 *      - ACMP_FILTER_INPUT_4
 *      - ACMP_FILTER_INPUT_5
 *      - ACMP_FILTER_INPUT_6
 * @param samplePrescale The prescale value for the sample clock. the range is 0~0xFFFFFF (24bit).
 * @param sampleWindow The window size for the digital filter. the range is 0~0x1F (5bit).
 * @param threshold The threshold value for the digital filter. the range is 0~0x1F (5bit).
 */
void ACMP_configFilter(ACMP_Type *ACMPx, uint8_t channel, ACMP_DigitalFilterInpustSel filterInputSel,
                       uint32_t samplePrescale, uint16_t sampleWindow,
                       uint16_t threshold)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_H_FILTINSEL_Msk, (uint32_t)filterInputSel << ACMP0_CTL_H_FILTINSEL_Pos);
        MODIFY_REG(ACMPx->DGTFLT_CTL,
                   ACMP0_DGTFLT_CTL_CMPH_THRESH_Msk | ACMP0_DGTFLT_CTL_CMPH_SAMPWIN_Msk,
                   (uint32_t)threshold << ACMP0_DGTFLT_CTL_CMPH_THRESH_Pos |
                   (uint32_t)sampleWindow << ACMP0_DGTFLT_CTL_CMPH_SAMPWIN_Pos);
        MODIFY_REG(ACMPx->HDGTFLT_CLKCTL, ACMP0_HDGTFLT_CLKCTL_CMPH_CLKPRESCALE_Msk,
                   (uint32_t)samplePrescale << ACMP0_HDGTFLT_CLKCTL_CMPH_CLKPRESCALE_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->CTL, ACMP0_CTL_L_FILTINSEL_Msk, (uint32_t)filterInputSel << ACMP0_CTL_L_FILTINSEL_Pos);
        MODIFY_REG(ACMPx->DGTFLT_CTL,
                   ACMP0_DGTFLT_CTL_CMPL_THRESH_Msk | ACMP0_DGTFLT_CTL_CMPL_SAMPWIN_Msk,
                   (uint32_t)threshold << ACMP0_DGTFLT_CTL_CMPL_THRESH_Pos |
                   (uint32_t)sampleWindow << ACMP0_DGTFLT_CTL_CMPL_SAMPWIN_Pos);
        MODIFY_REG(ACMPx->LDGTFLT_CLKCTL, ACMP0_LDGTFLT_CLKCTL_CMPL_CLKPRESCALE_Msk,
                   (uint32_t)samplePrescale << ACMP0_LDGTFLT_CLKCTL_CMPL_CLKPRESCALE_Pos);
    }
}

/**
 * @brief Configures ramp parameters
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param maxRampVal The maximum value for the ramp generator. the range is 0~0xFFFF (16bit).
 * @param decrementVal The decrement value for the ramp generator. the range is 0~0xFFFF (16bit).
 * @param delayVal The delay value for the ramp generator. the range is 0~0x3FFF (13bit).
 */
void ACMP_configRamp(ACMP_Type *ACMPx, uint8_t channel, uint16_t maxRampVal, uint16_t decrementVal, uint16_t delayVal)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->HRAMP_PRM0, ACMP0_HRAMP_PRM0_DLYS_Msk, (uint32_t)delayVal << ACMP0_HRAMP_PRM0_DLYS_Pos);
        WRITE_REG(ACMPx->HRAMP_PRM1, ((uint32_t)decrementVal));
        WRITE_REG(ACMPx->HRAMP_PRM2, ((uint32_t)maxRampVal));
    }
    else
    {
        MODIFY_REG(ACMPx->LRAMP_PRM0, ACMP0_LRAMP_PRM0_DLYS_Msk, (uint32_t)delayVal << ACMP0_LRAMP_PRM0_DLYS_Pos);
        WRITE_REG(ACMPx->LRAMP_PRM1, ((uint32_t)decrementVal));
        WRITE_REG(ACMPx->LRAMP_PRM2, ((uint32_t)maxRampVal));
    }
}

/**
 * @brief Get ACMP error status
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @return errstatus  error status masks
 */
uint32_t ACMP_getErrorStatus(ACMP_Type *ACMPx)
{
    uint32_t status = ACMP_ERROR_STATUS_NONE;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (READ_BIT(ACMPx->COM_BLK_REPT_RPT, ACMP0_COM_BLK_REPT_RPT_CMP0_BLK_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_H_CMP_BLK_REPT;
    }
    if (READ_BIT(ACMPx->COM_BLK_REPT_RPT, ACMP0_COM_BLK_REPT_RPT_CMP1_BLK_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_L_CMP_BLK_REPT;
    }
    if (READ_BIT(ACMPx->DAC_TXDN_REPT_RPT, ACMP0_DAC_TXDN_REPT_RPT_CMPC_DAC0_TXDN_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_H_DAC_TXDN_REPT;
    }
    if (READ_BIT(ACMPx->DAC_TXDN_REPT_RPT, ACMP0_DAC_TXDN_REPT_RPT_CMPC_DAC1_TXDN_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_L_DAC_TXDN_REPT;
    }
    if (READ_BIT(ACMPx->DAC_TRG_REPT, ACMP0_DAC_TRG_REPT_CMPC_DAC0_TRG_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_H_DAC_TRG_REPT;
    }
    if (READ_BIT(ACMPx->DAC_TRG_REPT, ACMP0_DAC_TRG_REPT_CMPC_DAC1_TRG_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_L_DAC_TRG_REPT;
    }
    if (READ_BIT(ACMPx->DAC_DMAREQ_REPT, ACMP0_DAC_DMAREQ_REPT_CMPC_DAC0_DMAREQ_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_H_DAC_DMAREQ_REPT;
    }
    if (READ_BIT(ACMPx->DAC_DMAREQ_REPT, ACMP0_DAC_DMAREQ_REPT_CMPC_DAC1_DMAREQ_REPT_RPT_Msk) != 0)
    {
        status |= CHANNEL_L_DAC_DMAREQ_REPT;
    }

    return status;
}

/**
 * @brief Clear the error status of the specified ACMP channel
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param errorStatus  Error status mask, indicating which error status needs to be cleared
 *
 * This function clears the error status of the specified ACMP channel. The error status mask is used to indicate which
 * error status needs to be cleared.
 *
 * @note The caller should ensure that the ACMP peripheral is properly initialized before calling this function.
 */
void ACMP_clearErrorStatus(ACMP_Type *ACMPx, uint32_t errorStatus)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (errorStatus == 0)
    {
        return;
    }

    if ((errorStatus & CHANNEL_H_CMP_BLK_REPT) != 0)
    {
        SET_BIT(ACMPx->COM_BLK_REPT_RPT, ACMP0_COM_BLK_REPT_RPT_CMP0_BLK_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_L_CMP_BLK_REPT) != 0)
    {
        SET_BIT(ACMPx->COM_BLK_REPT_RPT, ACMP0_COM_BLK_REPT_RPT_CMP1_BLK_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_H_DAC_TXDN_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_TXDN_REPT_RPT, ACMP0_DAC_TXDN_REPT_RPT_CMPC_DAC0_TXDN_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_L_DAC_TXDN_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_TXDN_REPT_RPT, ACMP0_DAC_TXDN_REPT_RPT_CMPC_DAC1_TXDN_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_H_DAC_TRG_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_TRG_REPT, ACMP0_DAC_TRG_REPT_CMPC_DAC0_TRG_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_L_DAC_TRG_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_TRG_REPT, ACMP0_DAC_TRG_REPT_CMPC_DAC1_TRG_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_H_DAC_DMAREQ_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_DMAREQ_REPT, ACMP0_DAC_DMAREQ_REPT_CMPC_DAC0_DMAREQ_REPT_RPT_Msk);
    }
    if ((errorStatus & CHANNEL_L_DAC_DMAREQ_REPT) != 0)
    {
        SET_BIT(ACMPx->DAC_DMAREQ_REPT, ACMP0_DAC_DMAREQ_REPT_CMPC_DAC1_DMAREQ_REPT_RPT_Msk);
    }
}

/**
 * @brief Enable Filter for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_enableFilter(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPH_DGT_FLT_EN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPL_DGT_FLT_EN_Msk);
    }
}

/**
 * @brief Disable Filter for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_disableFilter(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPH_DGT_FLT_EN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->DGTFLT_CTL, ACMP0_DGTFLT_CTL_CMPL_DGT_FLT_EN_Msk);
    }
}

/**
 * @brief Gets the ramp generator clock counter value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return value return the ramp clk counter value (12bit)
 */
uint16_t ACMP_getRampClkCountValue(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->HRAMP_STS0,
                                   ACMP0_HRAMP_STS0_CLKCNT_RPT_Msk) >> ACMP0_HRAMP_STS0_CLKCNT_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->LRAMP_STS0,
                                   ACMP0_LRAMP_STS0_CLKCNT_RPT_Msk) >> ACMP0_LRAMP_STS0_CLKCNT_RPT_Pos);
    }
}

/**
 * @brief Gets the ramp generator counter value.
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return status return the ramp status
 */
uint16_t ACMP_getRampStatus(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->HRAMP_STS2, ACMP0_HRAMP_STS2_STS_RPT_Msk) >> ACMP0_HRAMP_STS2_STS_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->LRAMP_STS2, ACMP0_LRAMP_STS2_STS_RPT_Msk) >> ACMP0_LRAMP_STS2_STS_RPT_Pos);
    }
}

/**
 * @brief Set Interrupt Mask for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks, The following parameters can be combined and configured
 *      - ACMP_IT_NONE_MASK
 *      - CHANNEL_H_DAC_TXDN_IT_MASK
 *      - CHANNEL_L_DAC_TXDN_IT_MASK
 *      - CHANNEL_H_AFTER_FILTER_IT_MASK
 *      - CHANNEL_L_AFTER_FILTER_IT_MASK
 *      - CHANNEL_H_BEFORE_FILTER_IT_MASK
 *      - CHANNEL_L_BEFORE_FILTER_IT_MASK
 *      - ACMP_IT_ALL_MASK
 */
void ACMP_setInterruptMask(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    SET_BIT(ACMPx->INT_MASK, interruptMask);
}

/**
 * @brief Set Interrupt Mask for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks
 */
void ACMP_clearInterruptMask(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    CLEAR_BIT(ACMPx->INT_MASK, interruptMask);
}

/**
 * @brief Enable Interrupt for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks
 */
void ACMP_enableInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    SET_BIT(ACMPx->INT_EN, interruptMask);
}

/**
 * @brief Disable Interrupt for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks
 */
void ACMP_disableInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    CLEAR_BIT(ACMPx->INT_EN, interruptMask);
}

/**
 * @brief Force Interrupt for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks
 */
void ACMP_forceInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    SET_BIT(ACMPx->INT_FORCE_IND, interruptMask);
}

/**
 * @brief Clear IT for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param interruptMask  interrupt masks
 */
void ACMP_clearInterruptStatus(ACMP_Type *ACMPx, uint32_t interruptMask)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_IT_MASK(interruptMask));

    SET_BIT(ACMPx->INT_CLR, interruptMask);
}

/**
 * @brief Get IT mask for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @return uint32_t  interrupt masks
 */
uint32_t ACMP_getInterruptStatus(ACMP_Type *ACMPx)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    return READ_BIT(ACMPx->INT_STATUS_RPT, ACMP_IT_ALL_MASK);
}

/**
 * @brief Get IT RAW mask for ACMP
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @return uint32_t  interrupt masks
 */
uint32_t ACMP_getInterruptStatusRaw(ACMP_Type *ACMPx)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));

    return READ_BIT(ACMPx->INT_RAW_RPT, ACMP_IT_ALL_MASK);
}

/**
 * @brief Software trigger the specified DAC
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_SWTriggerDAC(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->DAC_SWTRG, ACMP0_DAC_SWTRG_CMPC_DAC0_SWTRG_Msk);
    }
    else
    {
        SET_BIT(ACMPx->DAC_SWTRG, ACMP0_DAC_SWTRG_CMPC_DAC1_SWTRG_Msk);
    }
}

/**
 * @brief Get the specified DAC txd end report
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return FlagStatus  the status of ACMP DAC output
 */
FlagStatus ACMP_getDACTransferStatus(ACMP_Type *ACMPx, uint8_t channel)
{
    FlagStatus eSta;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        eSta =
            ((READ_REG(ACMPx->DAC_TXDN_RPT) & ACMP0_DAC_TXDN_RPT_CMPC_DAC0_TXDN_RPT_Msk) != 0) ? SET : RESET;
        return eSta;
    }
    else
    {
        eSta =
            ((READ_REG(ACMPx->DAC_TXDN_RPT) & ACMP0_DAC_TXDN_RPT_CMPC_DAC1_TXDN_RPT_Msk) != 0) ? SET : RESET;
        return eSta;
    }
}

/**
 * @brief Clear the specified DAC txd end report
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_clearDACTransferStatus(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->DAC_TXDN_RPT, ACMP0_DAC_TXDN_RPT_CMPC_DAC0_TXDN_RPT_Msk);
    }
    else
    {
        SET_BIT(ACMPx->DAC_TXDN_RPT, ACMP0_DAC_TXDN_RPT_CMPC_DAC1_TXDN_RPT_Msk);
    }
}

/**
 * @brief Set the specified DAC offset adjust value
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value  ACMP DAC offset adjust value
 */
void ACMP_setDACOSADJ(ACMP_Type *ACMPx, uint8_t channel, int16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->DAC_OS_ADJ, ACMP0_DAC_OS_ADJ_CMPC_DAC0_OS_ADJ_Msk,
                   ((uint32_t)value & OFFSET_ADJ_MSK) << ACMP0_DAC_OS_ADJ_CMPC_DAC0_OS_ADJ_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->DAC_OS_ADJ, ACMP0_DAC_OS_ADJ_CMPC_DAC1_OS_ADJ_Msk,
                   ((uint32_t)value & OFFSET_ADJ_MSK) << ACMP0_DAC_OS_ADJ_CMPC_DAC1_OS_ADJ_Pos);
    }
}

/**
 * @brief Get the specified DAC os adjust value
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return int16_t  ACMP DAC offset adjust value
 */
int16_t ACMP_getDACOSADJ(ACMP_Type *ACMPx, uint8_t channel)
{
    int32_t val;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        val = (READ_REG(ACMPx->DAC_OS_ADJ) >> ACMP0_DAC_OS_ADJ_CMPC_DAC0_OS_ADJ_Pos) & OFFSET_ADJ_MSK;
    }
    else
    {
        val = (READ_REG(ACMPx->DAC_OS_ADJ) >> ACMP0_DAC_OS_ADJ_CMPC_DAC1_OS_ADJ_Pos) & OFFSET_ADJ_MSK;
    }
    return (int16_t)val;
}

/**
 * @brief Set the specified DAC gain adjust value
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @param value  ACMP DAC gain adjust value
 */
void ACMP_setDACGainADJ(ACMP_Type *ACMPx, uint8_t channel, int16_t value)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        MODIFY_REG(ACMPx->DAC_GAIN_ADJ, ACMP0_DAC_GAIN_ADJ_CMPC_DAC0_GAIN_ADJ_Msk,
                   ((uint32_t)value & GAIN_ADJ_MSK) << ACMP0_DAC_GAIN_ADJ_CMPC_DAC0_GAIN_ADJ_Pos);
    }
    else
    {
        MODIFY_REG(ACMPx->DAC_GAIN_ADJ, ACMP0_DAC_GAIN_ADJ_CMPC_DAC1_GAIN_ADJ_Msk,
                   ((uint32_t)value & GAIN_ADJ_MSK) << ACMP0_DAC_GAIN_ADJ_CMPC_DAC1_GAIN_ADJ_Pos);
    }
}

/**
 * @brief Get the specified DAC gain adjust value
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return int16_t  ACMP DAC gain adjust value
 */
int16_t ACMP_getDACGainADJ(ACMP_Type *ACMPx, uint8_t channel)
{
    int32_t val;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        val = (READ_REG(ACMPx->DAC_GAIN_ADJ) >> ACMP0_DAC_GAIN_ADJ_CMPC_DAC0_GAIN_ADJ_Pos) & GAIN_ADJ_MSK;
    }
    else
    {
        val = (READ_REG(ACMPx->DAC_GAIN_ADJ) >> ACMP0_DAC_GAIN_ADJ_CMPC_DAC1_GAIN_ADJ_Pos) & GAIN_ADJ_MSK;
    }
    return (int16_t)val;
}

/**
 * @brief Enable the specified DAC DMA handshake
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_enableDMA(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        SET_BIT(ACMPx->DAC_HDSK_EN, ACMP0_DAC_HDSK_EN_CMPC_DAC0_HDSK_EN_Msk);
    }
    else
    {
        SET_BIT(ACMPx->DAC_HDSK_EN, ACMP0_DAC_HDSK_EN_CMPC_DAC1_HDSK_EN_Msk);
    }
}

/**
 * @brief Disable the specified DAC DMA handshake
 *
 * @note Calling this function only when DMA channel is in idle state.
 * this function cause all comparing channel reset in whole ACMP module
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 */
void ACMP_disableDMA(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        CLEAR_BIT(ACMPx->DAC_HDSK_EN, ACMP0_DAC_HDSK_EN_CMPC_DAC0_HDSK_EN_Msk);
    }
    else
    {
        CLEAR_BIT(ACMPx->DAC_HDSK_EN, ACMP0_DAC_HDSK_EN_CMPC_DAC1_HDSK_EN_Msk);
    }
}

/**
 * @brief Gets the current value of the internal DAC
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return uint16_t  The current value of the internal DAC
 *
 * This function reads the value of the internal DAC for the specified ACMP channel.
 *
 * @note The caller should ensure that the ACMP peripheral is properly initialized before calling this function.
 */
uint16_t ACMP_getDACValue(ACMP_Type *ACMPx, uint8_t channel)
{
    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        return (uint16_t)(READ_BIT(ACMPx->DAC_TDAT,
                                   ACMP0_DAC_TDAT_HTDAT_LOAD_RPT_Msk) >> ACMP0_DAC_TDAT_HTDAT_LOAD_RPT_Pos);
    }
    else
    {
        return (uint16_t)(READ_BIT(ACMPx->DAC_TDAT,
                                   ACMP0_DAC_TDAT_LTDAT_LOAD_RPT_Msk) >> ACMP0_DAC_TDAT_LTDAT_LOAD_RPT_Pos);
    }
}

/**
 * @brief Gets the latch output value of comparator
 *
 * @param ACMPx Pointer to the ACMP peripheral instance.
 *      - ACMP0
 *      - ACMP1
 *      - ACMP2
 *      - ACMP3
 * @param channel The channel to configure
 *      - ACMP_CHANNEL_H
 *      - ACMP_CHANNEL_L
 * @return FlagStatus  The latch output status of comparator
 *
 * This function reads the latch output value of the comparator for the specified ACMP channel.
 *
 * @note The caller should ensure that the ACMP peripheral is properly initialized before calling this function.
 */
FlagStatus ACMP_getLatchStatus(ACMP_Type *ACMPx, uint8_t channel)
{
    FlagStatus eSta;

    assert_param(IS_ACMP_PERIPHERAL(ACMPx));
    assert_param(IS_ACMP_CHANNEL(channel));

    if (channel == ACMP_CHANNEL_H)
    {
        eSta =
            ((READ_BIT(ACMPx->STS, ACMP0_STS_HLATCH_RPT_Msk) >> ACMP0_STS_HLATCH_RPT_Pos) != 0) ? SET : RESET;
    }
    else
    {
        eSta =
            ((READ_BIT(ACMPx->STS, ACMP0_STS_LLATCH_RPT_Msk) >> ACMP0_STS_LLATCH_RPT_Pos) != 0) ? SET : RESET;
    }
    return eSta;
}

/**
 * @}
 */

/**
 * @}
 */

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
