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

/* includes -------------------------------------------------------------------*/
#include "et6x_dac.h"
#include "et6x_crg.h"
#include "et6x_sysctrl.h"

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/

/*! Parameter validity check for DAC peripheral  */
#define IS_DAC_ALL_PERIPH(DACx)    ((DACx == DAC0) || (DACx == DAC1))

#define DAC0_HOLD_MASK    (1U)
#define DAC1_HOLD_MASK    (2U)

/**
 * @brief Config trigger mode
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @param config DAC initial structure pointer
 */
void DAC_configTriggerMode(DAC_Type *DACx, DAC_TriggerConfig *config)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    MODIFY_REG(DACx->TRG_SET,
               DAC0_TRG_SET_DAC_LDMOD_Msk | DAC0_TRG_SET_DAC_TRG_MASK_Msk | DAC0_TRG_SET_DAC_TRG_POLR_Msk | DAC0_TRG_SET_DAC_TRGEN_Msk,
               (uint32_t)config->shadowLoadEn << DAC0_TRG_SET_DAC_LDMOD_Pos |
               (uint32_t)config->triggerMask << DAC0_TRG_SET_DAC_TRG_MASK_Pos |
               (uint32_t)config->triggerInvertEn << DAC0_TRG_SET_DAC_TRG_POLR_Pos |
               (uint32_t)config->triggerEn << DAC0_TRG_SET_DAC_TRGEN_Pos);

    WRITE_REG(DACx->TRG_DLY, config->triggerDelay & DAC0_TRG_DLY_DAC_TRG_DLY_Msk);
}

/**
 * @brief Config output
 *
 * @param DACx  DAC peripheral [DAC0~DAC1]
 * @param config DAC output config structure pointer
 */
void DAC_configOutput(DAC_Type *DACx, DAC_OutputConfig *config)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    MODIFY_REG(DACx->TRG_SET,
               DAC0_TRG_SET_DAC_TDAT_SEL_Msk | DAC0_TRG_SET_DAC_OUT_DAT_FMAT_SEL_Msk | DAC0_TRG_SET_DAC_OUT_RVRS_SEL_Msk,
               (uint32_t)config->srcSel << DAC0_TRG_SET_DAC_TDAT_SEL_Pos |
               (uint32_t)config->outputFormat << DAC0_TRG_SET_DAC_OUT_DAT_FMAT_SEL_Pos |
               (uint32_t)config->outputDataReverseEn << DAC0_TRG_SET_DAC_OUT_RVRS_SEL_Pos);
}

/**
 * @brief Sets the DAC Reference Voltage
 *
 * @param DACx DAC peripheral [DAC0~DAC1]
 * @param source Reference voltage select, VDAC or VREF
 * @attention if reference voltage select VREF, should call \b SYSCTRL_enableAnalogReferenceInternal enable VREF
 *
 */
void DAC_setReferenceVoltage(DAC_Type *DACx, DAC_ReferenceVoltage source)
{
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    if (DACx == DAC0)
    {
        MODIFY_REG(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC0_REF_SEL_Msk,
                   (uint32_t)source << SYSC_AFE_DAC_D2A_BDAC0_REF_SEL_Pos);
    }
    else
    {
        MODIFY_REG(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC1_REF_SEL_Msk,
                   (uint32_t)source << SYSC_AFE_DAC_D2A_BDAC1_REF_SEL_Pos);
    }
}

/**
 * @brief Sets DAC trigger source
 *
 * @param DACx DAC peripheral [DAC0~DAC1]
 * @param source trigger source ref to DAC_TRIGGER_SEL_xxxx
 */
void DAC_setTriggerSource(DAC_Type *DACx, DAC_TriggerSel source)
{
    uint32_t tempReg = 0;

    assert_param(IS_DAC_ALL_PERIPH(DACx));

    tempReg = READ_REG(DACx->TRG_SET);

    CLEAR_BIT(DACx->TRG_SET, DAC0_TRG_SET_DAC_TRGEN_Msk);
    WRITE_REG(DACx->TRG_SEL, (uint32_t)source << DAC0_TRG_SEL_DAC_TRG_SEL_Pos);
    if ((tempReg & DAC0_TRG_SET_DAC_TRGEN_Msk) != 0)
    {
        SET_BIT(DACx->TRG_SET, DAC0_TRG_SET_DAC_TRGEN_Msk);
    }
}

/**
 * @brief Set the DAC Shadow Output Value
 *
 * @param DACx  DAC peripheral [DAC0~DAC1]
 * @param value 12-bit code to be loaded into the active value register
 */
void DAC_setValue(DAC_Type *DACx, uint16_t value)
{
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    WRITE_REG(DACx->TDAT, value);
}

/**
 * @brief Get the DAC Shadow Output Value
 *
 * @param DACx DAC peripheral [DAC0~DAC1]
 * @return uint16_t Returns the DAC shadow output value.
 */
uint16_t DAC_getValue(DAC_Type *DACx)
{
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    return (uint16_t)(READ_REG(DACx->TDAT) & DAC0_TDAT_DAC_TDAT_Msk);
}

/**
 * @brief Enable the DAC Output
 *
 * @param DACx  DAC peripheral [DAC0~DAC1]
 */
void DAC_enableOutput(DAC_Type *DACx)
{
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    if (DACx == DAC0)
    {
        SET_BIT(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC0_EN_Msk);
    }
    else
    {
        SET_BIT(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC1_EN_Msk);
    }
}

/**
 * @brief Disable the DAC Output
 *
 * @param DACx  DAC peripheral [DAC0~DAC1]
 */
void DAC_disableOutput(DAC_Type *DACx)
{
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    if (DACx == DAC0)
    {
        CLEAR_BIT(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC0_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SYSC->AFE_DAC, SYSC_AFE_DAC_D2A_BDAC1_EN_Msk);
    }
}

/**
 * @brief Software trigger the specified DAC
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_SWTrigger(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* software trigger */
    SET_BIT(DACx->TRG_SET, DAC0_TRG_SET_DAC_SWTRG_Msk);
}

/**
 * @brief Get trigger signal repeat report status
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @return FlagStatus
 *         SET: DAC trigger repeat occurs
 *         RESET: DAC trigger repeat does not occur
 */
FlagStatus DAC_getTrigRepeatStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac get repeat status */

    if (READ_BIT(DACx->TRG_REPT_RPT, DAC0_TRG_REPT_RPT_TRG_REPT_RPT_Msk) != 0)
    {
        return SET;
    }
    else
    {
        return RESET;
    }
}

/**
 * @brief Clear the specified DAC repeat status
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_clearTrigRepeatStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* Clear repeat status */
    WRITE_REG(DACx->TRG_REPT_RPT, DAC0_TRG_REPT_RPT_TRG_REPT_RPT_Msk);
}

/**
 * @brief Get the specified DAC txd end report
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @return FlagStatus if SET, DAC is Transferred Done
 */
FlagStatus DAC_getTransferStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac get txd end status */
    if (READ_BIT(DACx->TXDN_RPT, DAC0_TXDN_RPT_DAC_TXDN_RPT_Msk) != 0)
    {
        return SET;
    }
    else
    {
        return RESET;
    }
}

/**
 * @brief Clear the specified DAC txd end report
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_clearTransferStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* Clear tx done status */
    WRITE_REG(DACx->TXDN_RPT, DAC0_TXDN_RPT_DAC_TXDN_RPT_Msk);
}

/**
 * @brief Enable the specified DAC interrupt
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_enableInterrupt(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* enable interrupt */
    SET_BIT(DACx->INT_EN, DAC0_INT_EN_DAC_INT_EN_Msk);
}

/**
 * @brief Disable the specified DAC interrupt
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_disableInterrupt(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* enable/disable interrupt */
    CLEAR_BIT(DACx->INT_EN, DAC0_INT_EN_DAC_INT_EN_Msk);
}

/**
 * @brief Enable or disable the specified DAC interrupt
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_clearInterruptStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* clear interrupt flag */
    SET_BIT(DACx->INT_CLR, DAC0_INT_CLR_DAC_INT_CLR_Msk);
}

/**
 * @brief Get the specified DAC interrupt status
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @return ITStatus
 *         SET: DAC interrupt occurs
 *         RESET: DAC interrupt does not occur
 */
ITStatus DAC_getInterruptStatus(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* get interrupt flag */
    if (READ_BIT(DACx->INT_STATUS_RPT, DAC0_INT_STATUS_RPT_DAC_INT_STATUS_RPT_Msk) != 0)
    {
        return SET;
    }
    else
    {
        return RESET;
    }
}

/**
 * @brief Enable the specified DAC DMA handshake
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_enableDMA(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* enable/disable interrupt */
    SET_BIT(DACx->HDSK_EN, DAC0_HDSK_EN_DAC_HDSK_EN_Msk);
}

/**
 * @brief Disable the specified DAC DMA handshake
 *
 * @note Calling this function only when DMA channel is in idle state.
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_disableDMA(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* Disable interrupt */
    CLEAR_BIT(DACx->HDSK_EN, DAC0_HDSK_EN_DAC_HDSK_EN_Msk);
}

/**
 * @brief Enable dac output software hold functionality
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_enableSWHold(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
    if (DACx == DAC0)
    {
        SET_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_SW_HOLD_EN_Pos);
    }
    else
    {
        SET_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_SW_HOLD_EN_Pos);
    }
    WRITE_REG(SYSC->NV, SYSC_LOCK_KEY);
}

/**
 * @brief Disable dac output software hold functionality
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 */
void DAC_disableSWHold(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
    if (DACx == DAC0)
    {
        CLEAR_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_SW_HOLD_EN_Pos);
    }
    else
    {
        CLEAR_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_SW_HOLD_EN_Pos);
    }
    WRITE_REG(SYSC->NV, SYSC_LOCK_KEY);
}

/**
 * @brief Enable dac output software hold functionality
 *
 * @param DACx
 */
void DAC_enableHWHold(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
    if (DACx == DAC0)
    {
        CLEAR_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_MASK_Pos);
        SET_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_IND_Pos);
    }
    else
    {
        CLEAR_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_MASK_Pos);
        SET_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_IND_Pos);
    }
    WRITE_REG(SYSC->NV, SYSC_LOCK_KEY);
}

/**
 * @brief Disable dac output hardware hold functionality
 *
 * @param DACx
 */
void DAC_disableHWHold(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));
    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
    if (DACx == DAC0)
    {
        SET_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_MASK_Pos);
        CLEAR_BIT(SYSC->SYSC2DACC, DAC0_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_IND_Pos);
    }
    else
    {
        SET_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_MASK_Pos);
        CLEAR_BIT(SYSC->SYSC2DACC, DAC1_HOLD_MASK << SYSC_SYSC2DACC_HW_HOLD_IND_Pos);
    }
    WRITE_REG(SYSC->NV, SYSC_LOCK_KEY);
}

/**
 * @brief Set the spedified DAC os adjust value
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @param value offset value for DAC calibration
 */
void DAC_setOffsetTrim(DAC_Type *DACx, uint16_t value)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac set offset adjust value */
    WRITE_REG(DACx->OS_ADJ, (uint32_t)value & DAC0_OS_ADJ_DAC_OS_ADJ_Msk);
}

/**
 * @brief Get the specified DAC os adjust value
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @return uint16_t offset adjust value
 */
uint16_t DAC_getOffsetTrim(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac get offset adjust value */
    return (uint16_t)READ_REG(DACx->OS_ADJ);
}

/**
 * @brief Set the specified DAC gain adjust value
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @param value gain value for DAC calibration
 */
void DAC_setGainADJ(DAC_Type *DACx, uint16_t value)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac set gain adjust value */
    WRITE_REG(DACx->GAIN_ADJ, value & DAC0_GAIN_ADJ_DAC_GAIN_ADJ_Msk);
}

/**
 * @brief Get the specified DAC gain adjust value
 *
 * @param DACx select DAC device [DAC0 ~ DAC1]
 * @return uint16_t gain adjust value
 */
uint16_t DAC_getGainADJ(DAC_Type *DACx)
{
    /* Check the parameters */
    assert_param(IS_DAC_ALL_PERIPH(DACx));

    /* dac get gain adjust value */
    return (uint16_t)READ_REG(DACx->GAIN_ADJ);
}
