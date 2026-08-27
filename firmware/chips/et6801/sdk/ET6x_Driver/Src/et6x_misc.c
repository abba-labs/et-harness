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
#include "et6x_misc.h"

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/

/**
 *
 * @brief Enables ECC check and correction for the selected SRAM bank.
 *  This function enables ECC check and correction for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 */
void MISC_SRAM_ECC_Enable(SRAMCTL_Type *SRAMx)
{
    SET_BIT(SRAMx->AXI2SRAM_CTRL, SRAMCTL0_AXI2SRAM_CTRL_ECC_CHK_EN_Msk);
}

/**
 *
 * @brief Disables ECC check and correction for the selected SRAM bank.
 *  This function disables ECC check and correction for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 */
void MISC_SRAM_ECC_Disable(SRAMCTL_Type *SRAMx)
{
    CLEAR_BIT(SRAMx->AXI2SRAM_CTRL, SRAMCTL0_AXI2SRAM_CTRL_ECC_CHK_EN_Msk);
}

/**
 *
 * @brief Configures ECC check and correction for the selected SRAM bank.
 *  This function configures the ECC check and correction settings for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param config is the configuration structure for the SRAM bank
 *
 */
void MISC_SRAM_ECC_Config(SRAMCTL_Type *SRAMx, MISC_SRAM_Config_Typedef *config)
{
    MODIFY_REG(SRAMx->AXI2SRAM_CTRL,
               SRAMCTL0_AXI2SRAM_CTRL_BRESP_WITH_ECC_EN_Msk | SRAMCTL0_AXI2SRAM_CTRL_RRESP_WITH_ECC_EN_Msk | SRAMCTL0_AXI2SRAM_CTRL_SERR_CORRECTION_EN_Msk,
               (uint32_t)config->brespEccEn << SRAMCTL0_AXI2SRAM_CTRL_BRESP_WITH_ECC_EN_Pos |
               (uint32_t)config->rrespEccEn << SRAMCTL0_AXI2SRAM_CTRL_RRESP_WITH_ECC_EN_Pos |
               (uint32_t)config->EccErrCorrectionEn << SRAMCTL0_AXI2SRAM_CTRL_SERR_CORRECTION_EN_Pos);
}

/**
 *
 * @brief Enables ECC error injection for the selected SRAM bank.
 *  This function enables ECC error injection for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 */
void MISC_SRAM_ECC_errInject(SRAMCTL_Type *SRAMx)
{
    SET_BIT(SRAMx->AXI2SRAM_CTRL, SRAMCTL0_AXI2SRAM_CTRL_RDATA_ERR_INJECT_Msk);
}

/**
 *
 * @brief Enables low power mode for the selected SRAM bank.
 *  This function enables low power mode for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 */
void MISC_SRAM_LP_Enable(SRAMCTL_Type *SRAMx)
{
    SET_BIT(SRAMx->AXI2SRAM_LP_CTRL,
            SRAMCTL0_AXI2SRAM_LP_CTRL_RAM_LS_LP_EN_Msk | SRAMCTL0_AXI2SRAM_LP_CTRL_AXI2SRAM_LP_EN_Msk);
}

/**
 *
 * @brief Disables low power mode for the selected SRAM bank.
 *  This function disables low power mode for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 */
void MISC_SRAM_LP_Disable(SRAMCTL_Type *SRAMx)
{
    CLEAR_BIT(SRAMx->AXI2SRAM_LP_CTRL,
              SRAMCTL0_AXI2SRAM_LP_CTRL_RAM_LS_LP_EN_Msk | SRAMCTL0_AXI2SRAM_LP_CTRL_AXI2SRAM_LP_EN_Msk);
}

/**
 *
 * @brief Gets ECC error status for the selected SRAM bank.
 *  This function gets the ECC error status for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 * @return uint32_t The ECC error status
 */
uint32_t MISC_SRAM_ECC_GetStatus(SRAMCTL_Type *SRAMx)
{
    return READ_REG(SRAMx->ECC_ERR_STATE);
}

/**
 *
 * @brief Clears ECC error status for the selected SRAM bank.
 *  This function clears the ECC error status for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to clear the status for
 * @param clearMasks is the mask of the ECC error status bits to clear
 *
 */
void MISC_SRAM_ECC_ClearStatus(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, uint32_t clearMasks)
{
    if (bank == MISC_SRAM_BANK0)
    {
        SET_BIT(SRAMx->BANK0_STATE_CLR, clearMasks);
    }
    else
    {
        SET_BIT(SRAMx->BANK1_STATE_CLR, clearMasks);
    }
}

/**
 *
 * @brief Gets ECC 1-bit error address for the selected SRAM bank.
 *  This function gets the ECC 1-bit error address for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to get the error address for
 *
 * @return uint32_t The ECC 1-bit error address
 */
uint32_t MISC_SRAM_ECC1BIT_GetErrAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank)
{
    if (bank == MISC_SRAM_BANK0)
    {
        return READ_REG(SRAMx->BANK0_ECC_SERR_ADDR);
    }
    else
    {
        return READ_REG(SRAMx->BANK1_ECC_SERR_ADDR);
    }
}

/**
 *
 * @brief Gets ECC 2-bit error address for the selected SRAM bank.
 *  This function gets the ECC 2-bit error address for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to get the error address for
 *
 * @return uint32_t The ECC 2-bit error address
 */
uint32_t MISC_SRAM_ECC2BIT_GetErrAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank)
{
    if (bank == MISC_SRAM_BANK0)
    {
        return READ_REG(SRAMx->BANK0_ECC_MERR_ADDR);
    }
    else
    {
        return READ_REG(SRAMx->BANK1_ECC_MERR_ADDR);
    }
}

/**
 *
 * @brief Gets ECC 1-bit error correction address for the selected SRAM bank.
 *  This function gets the ECC 1-bit error correction address for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to get the correction address for
 *
 * @return uint32_t The ECC 1-bit error correction address
 */
uint32_t MISC_SRAM_ECC1BIT_CorrectionAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank)
{
    if (bank == MISC_SRAM_BANK0)
    {
        return READ_REG(SRAMx->BANK0_CORRECTION_CUR_ADDR);
    }
    else
    {
        return READ_REG(SRAMx->BANK1_CORRECTION_CUR_ADDR);
    }
}

/**
 *
 * @brief Gets ECC error count for the selected SRAM bank.
 *  This function gets the ECC error count for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to get the count for
 * @param type is the type of ECC error count to get
 *
 * @return uint8_t The ECC error count
 */
uint8_t MISC_SRAM_ECC_GetErrCnt(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, MISC_SRAM_CntType_Typedef type)
{
    uint8_t cnt = 0;

    if (bank == MISC_SRAM_BANK0)
    {
        if (type == MISC_SRAM_BANK_1BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK0_ECC_ERR_CNT,
                         SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_SERR_CNT_Msk) >>
                SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_SERR_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK0_ECC_ERR_CNT,
                         SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_MERR_CNT_Msk) >>
                SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_MERR_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK0_ECC_ERR_CNT,
                         SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_ERR_CORRECTION_CNT_Msk) >>
                SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_ERR_CORRECTION_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK0_ECC_ERR_CNT,
                         SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_ERR_ABONDON_CNT_Msk) >>
                SRAMCTL0_BANK0_ECC_ERR_CNT_BANK0_ECC_ERR_ABONDON_CNT_Pos;
        }
    }
    else
    {
        if (type == MISC_SRAM_BANK_1BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK1_ECC_ERR_CNT,
                         SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_SERR_CNT_Msk) >>
                SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_SERR_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK1_ECC_ERR_CNT,
                         SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_MERR_CNT_Msk) >>
                SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_MERR_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK1_ECC_ERR_CNT,
                         SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_ERR_CORRECTION_CNT_Msk) >>
                SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_ERR_CORRECTION_CNT_Pos;
        }
        else if (type == MISC_SRAM_BANK_2BIT_ERR_CNT)
        {
            cnt =
                READ_BIT(SRAMx->BANK1_ECC_ERR_CNT,
                         SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_ERR_ABONDON_CNT_Msk) >>
                SRAMCTL0_BANK1_ECC_ERR_CNT_BANK1_ECC_ERR_ABONDON_CNT_Pos;
        }
    }

    return cnt;
}

/**
 *
 * @brief Sets ECC 1-bit error threshold for the selected SRAM bank.
 *  This function sets the ECC 1-bit error threshold for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param bank is the SRAM bank to set the threshold for
 * @param threshold is the ECC 1-bit error threshold to set
 *
 */
void MISC_SRAM_ECC1BIT_SetThreshold(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, uint8_t threshold)
{
    if (bank == MISC_SRAM_BANK0)
    {
        MODIFY_REG(SRAMx->ECC_SERR_THRESHOLD, SRAMCTL0_ECC_SERR_THRESHOLD_BANK0_ECC_SERR_THRESHOLD_Msk,
                   (uint32_t)threshold << SRAMCTL0_ECC_SERR_THRESHOLD_BANK0_ECC_SERR_THRESHOLD_Pos);
    }
    else
    {
        MODIFY_REG(SRAMx->ECC_SERR_THRESHOLD, SRAMCTL0_ECC_SERR_THRESHOLD_BANK1_ECC_SERR_THRESHOLD_Msk,
                   (uint32_t)threshold << SRAMCTL0_ECC_SERR_THRESHOLD_BANK1_ECC_SERR_THRESHOLD_Pos);
    }
}

/**
 *
 * @brief Enables bank ECC interrupts for the selected SRAM bank.
 *  This function enables bank ECC interrupts for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param ITmasks is the mask of bank ECC interrupts to enable
 *
 */
void MISC_ITEnable(SRAMCTL_Type *SRAMx, uint32_t ITmasks)
{
    SET_BIT(SRAMx->INT_EN, ITmasks);
}

/**
 *
 * @brief Disables bank ECC interrupts for the selected SRAM bank.
 *  This function disables bank ECC interrupts for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param ITmasks is the mask of bank ECC interrupts to disable
 *
 */
void MISC_ITDisable(SRAMCTL_Type *SRAMx, uint32_t ITmasks)
{
    CLEAR_BIT(SRAMx->INT_EN, ITmasks);
}

/**
 *
 * @brief Clears bank ECC interrupts for the selected SRAM bank.
 *  This function clears bank ECC interrupts for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param ITmasks is the mask of bank ECC interrupts to clear
 *
 */
void MISC_ITClear(SRAMCTL_Type *SRAMx, uint32_t ITmasks)
{
    SET_BIT(SRAMx->INT_CLR, ITmasks);
}

/**
 *
 * @brief Gets raw bank ECC interrupt status for the selected SRAM bank.
 *  This function gets raw bank ECC interrupt status for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 * @return uint32_t The raw bank ECC interrupt status
 *
 */
uint32_t MISC_GetITRawStatus(SRAMCTL_Type *SRAMx)
{
    return READ_REG(SRAMx->INT_RAW_RPT);
}

/**
 *
 * @brief Gets masked bank ECC interrupt status for the selected SRAM bank.
 *  This function gets masked bank ECC interrupt status for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 *
 * @return uint32_t The masked SRAM interrupt status
 *
 */
uint32_t MISC_GetITStatus(SRAMCTL_Type *SRAMx)
{
    return READ_REG(SRAMx->INT_STATUS_RPT);
}

/**
 *
 * @brief Masks bank ECC interrupts for the selected SRAM bank.
 *  This function masks bank ECC interrupts for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param ITmasks is the mask of bank ECC interrupts to mask
 *
 */
void MISC_ITMask(SRAMCTL_Type *SRAMx, uint32_t ITmasks)
{
    SET_BIT(SRAMx->INT_MASK, ITmasks);
}

/**
 *
 * @brief Unmasks bank ECC interrupts for the selected SRAM bank.
 *  This function unmasks bank ECC interrupts for the selected SRAM bank.
 *
 * @param SRAMx is the base address of the SRAM module
 * @param ITmasks is the mask of bank ECC interrupts to unmask
 *
 */
void MISC_ITUnmask(SRAMCTL_Type *SRAMx, uint32_t ITmasks)
{
    CLEAR_BIT(SRAMx->INT_MASK, ITmasks);
}

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
