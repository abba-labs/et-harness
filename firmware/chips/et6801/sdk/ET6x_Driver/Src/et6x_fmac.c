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
#include "et6x_fmac.h"

#include <string.h>

/* Private typedef -----------------------------------------------------------*/

typedef enum
{
    FMAC_LOAD_X1_BUFF    = 1,
    FMAC_LOAD_X2_BUFF    = 2,
    FMAC_LOAD_Y_BUFF     = 3,
    FMAC_FIR_CONVOLUTION = 4,
    FMAC_IIR_CONVOLUTION = 5
} FMAC_Func;

/* Private define ------------------------------------------------------------*/

/*! Parameter validity check for DAC peripheral  */
#define IS_FMAC_INT_MASK(mask) \
        ((mask & (FMAC_IT_X1_BUFF_REQ_IT_MASK | \
                  FMAC_IT_Y_BUFF_REQ_IT_MASK | \
                  FMAC_IT_FIR_IIR_SAT_IT_MASK | \
                  FMAC_IT_X1_BUFF_OVERFLOW_IT_MASK | \
                  FMAC_IT_Y_BUFF_UNDERFLOW_IT_MASK | \
                  FMAC_IT_P_PARAM_ERR_IT_MASK | \
                  FMAC_IT_Q_PARAM_ERR_IT_MASK | \
                  FMAC_IT_R_PARAM_ERR_IT_MASK | \
                  FMAC_IT_X1_BUFF_LOAD_ERR_IT_MASK | \
                  FMAC_IT_X2_BUFF_LOAD_ERR_IT_MASK | \
                  FMAC_IT_Y_BUFF_STORE_ERR_IT_MASK)) != 0)

/**
 * @brief internal function select
 *
 * @param func
 * @param P
 * @param Q
 */
static void FMAC_selectFunc(FMAC_Func func, uint8_t P, uint8_t Q)
{
    uint32_t regVal;

    regVal = ((uint32_t)P << FMAC_PARAM_P_Pos) |
             ((uint32_t)Q << FMAC_PARAM_Q_Pos) |
             ((uint32_t)func << FMAC_PARAM_FUNC_Pos) |
             FMAC_PARAM_ENABLE_Msk;

    MODIFY_REG(FMAC->PARAM, FMAC_PARAM_FUNC_Msk | FMAC_PARAM_ENABLE_Msk | FMAC_PARAM_P_Msk | FMAC_PARAM_Q_Msk, regVal);
}

/**
 * @brief FMAC configuration
 *
 * @param config
 */
void FMAC_config(FMAC_ConfigParams *config)
{
    uint32_t regVal;

    regVal = ((uint32_t)config->X1_BuffBase << FMAC_X1_BUF_X1_BASE_Pos) |
             ((uint32_t)config->X1_BuffSize << FMAC_X1_BUF_X1_BUF_SIZE_Pos) |
             ((uint32_t)config->X1_BuffFIFOTrhd << FMAC_X1_BUF_X1_FULL_WM_Pos);
    WRITE_REG(FMAC->X1_BUF, regVal);

    regVal = ((uint32_t)config->X2_BuffBase << FMAC_X2_BUF_X2_BASE_Pos) |
             ((uint32_t)config->X2_BuffSize << FMAC_X2_BUF_X2_BUF_SIZE_Pos);
    WRITE_REG(FMAC->X2_BUF, regVal);

    regVal = ((uint32_t)config->Y_BuffBase << FMAC_Y_BUF_Y_BASE_Pos) |
             ((uint32_t)config->Y_BuffSize << FMAC_Y_BUF_Y_BUF_SIZE_Pos) |
             ((uint32_t)config->Y_BuffFIFOTrhd << FMAC_Y_BUF_Y_EMPTY_WM_Pos);
    WRITE_REG(FMAC->Y_BUF, regVal);

    regVal = ((uint32_t)config->accumulatorWrapEn << FMAC_CR_ACC_OUT_WRAP_SEL_Pos) |
             ((uint32_t)config->outputDataMode << FMAC_CR_DAT_OUT_SEL_Pos) |
             ((uint32_t)config->DMADataReadEn << FMAC_CR_DMA_REN_Pos) |
             ((uint32_t)config->DMADataWriteEn << FMAC_CR_DMA_WEN_Pos) |
             ((uint32_t)config->clipEn << FMAC_CR_CLIPEN_Pos) |
             ((uint32_t)config->floatDataReadEn << FMAC_CR_FLOAT2FIXED_IN_SEL_Pos) |
             ((uint32_t)config->floatDataWriteEn << FMAC_CR_FIXED2FLOAT_O_SEL_Pos);
    MODIFY_REG(FMAC->CR, (FMAC_CR_ACC_OUT_WRAP_SEL_Msk | FMAC_CR_DAT_OUT_SEL_Msk | FMAC_CR_DMA_REN_Msk |
                          FMAC_CR_DMA_WEN_Msk | FMAC_CR_CLIPEN_Msk |
                          FMAC_CR_FLOAT2FIXED_IN_SEL_Msk | FMAC_CR_FIXED2FLOAT_O_SEL_Msk), regVal);

    regVal = ((uint32_t)config->outputDataOffset << FMAC_OUT_CR_OFT_Pos) |
             ((uint32_t)config->outputDataShift << FMAC_OUT_CR_SH_Pos);
    WRITE_REG(FMAC->OUT_CR, regVal);
}

/**
 * @brief load X1 buff
 *
 * @param pInputData
 * @param pInputDataNum
 * @param maxDataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadX1Buff(int16_t *pInputData, uint32_t *pInputDataNum, uint8_t maxDataNum, uint32_t timeout)
{
    uint32_t dataNum = 0;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X1_BUFF, maxDataNum, 0U);
    while (maxDataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
        dataNum++;
        if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
        {
            *pInputDataNum = dataNum;
            return DRV_OK;
        }
    }

    *pInputDataNum = dataNum;

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }
    return DRV_OK;
}

/**
 * @brief load X1 buff float
 *
 * @param pInputData
 * @param pInputDataNum
 * @param maxDataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadX1BuffFloat(float *pInputData, uint32_t *pInputDataNum, uint8_t maxDataNum, uint32_t timeout)
{
    uint32_t dataNum = 0;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X1_BUFF, maxDataNum, 0U);
    while (maxDataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
        dataNum++;
        if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
        {
            *pInputDataNum = dataNum;
            return DRV_OK;
        }
    }

    *pInputDataNum = dataNum;

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }
    return DRV_OK;
}

/**
 * @brief load X2 buff
 *
 * @param pInputData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadX2Buff(int16_t *pInputData, uint8_t dataNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X2_BUFF, dataNum, 0U);

    while (dataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    return DRV_OK;
}

/**
 * @brief load X2 buff float
 *
 * @param pInputData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadX2BuffFloat(float *pInputData, uint8_t dataNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X2_BUFF, dataNum, 0U);

    while (dataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    return DRV_OK;
}

/**
 * @brief load X2 buff for IIR
 *
 * @param pInputCoeffA
 * @param coeffANum
 * @param pInputCoeffB
 * @param coeffBNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_IIR_loadX2Buff(int16_t *pInputCoeffA, uint8_t coeffANum, int16_t *pInputCoeffB,
                               uint8_t coeffBNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X2_BUFF, coeffBNum, coeffANum);

    while (coeffBNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputCoeffB++);
    }

    while (coeffANum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputCoeffA++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    return DRV_OK;
}

/**
 * @brief load X2 buff for IIR float
 *
 * @param pInputCoeffA
 * @param coeffANum
 * @param pInputCoeffB
 * @param coeffBNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_IIR_loadX2BuffFloat(float *pInputCoeffA, uint8_t coeffANum, float *pInputCoeffB,
                                    uint8_t coeffBNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_X2_BUFF, coeffBNum, coeffANum);

    while (coeffBNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputCoeffB++);
    }

    while (coeffANum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputCoeffA++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    return DRV_OK;
}

/**
 * @brief load Y buff
 *
 * @param pInputData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadYBuff(int16_t *pInputData, uint8_t dataNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_Y_BUFF, dataNum, 0U);

    while (dataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    CLEAR_BIT(FMAC->PARAM, FMAC_PARAM_ENABLE_Msk);
    return DRV_OK;
}

/**
 * @brief load Y buff
 *
 * @param pInputData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_loadYBuffFloat(float *pInputData, uint8_t dataNum, uint32_t timeout)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_LOAD_Y_BUFF, dataNum, 0U);

    while (dataNum--)
    {
        WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
    }

    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    CLEAR_BIT(FMAC->PARAM, FMAC_PARAM_ENABLE_Msk);
    return DRV_OK;
}

/**
 * @brief start FIR convolution
 *
 * @param pInputData
 * @param pOutoutData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_FIR_convolutionStart(int16_t *pInputData, int16_t *pOutoutData, uint32_t dataNum,
                                     uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_FIR_CONVOLUTION,
                    ((READ_REG(FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos), 0U);

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }

            WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = (int16_t)READ_REG(FMAC->FIFO_DATA);
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

/**
 * @brief start FIR convolution float
 *
 * @param pInputData
 * @param pOutoutData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_FIR_convolutionStartFloat(float *pInputData, float *pOutoutData, uint32_t dataNum,
                                          uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_FIR_CONVOLUTION,
                    ((READ_REG(FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos), 0U);

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }

            WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = *(float *)&FMAC->FIFO_DATA;
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

/**
 * @brief FIR convolution DMA and interrupt configuration
 *
 * @return DRV_Status
 */
DRV_Status FMAC_FIR_convolutionInterruptDMA(void)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_FIR_CONVOLUTION,
                    ((READ_REG(FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos), 0U);

    return DRV_OK;
}

/**
 * @brief start IIR convolution
 *
 * @param pInputData
 * @param pOutoutData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_IIR_convolutionStart(int16_t *pInputData, int16_t *pOutoutData, uint8_t numStages, uint32_t dataNum,
                                     uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_IIR_CONVOLUTION,
                    ((READ_REG(
                          FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos) - numStages,
                    numStages);

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = (int16_t)READ_REG(FMAC->FIFO_DATA);
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

/**
 * @brief start IIR convolution
 *
 * @param pInputData
 * @param pOutoutData
 * @param dataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_IIR_convolutionStartFloat(float *pInputData, float *pOutoutData, uint8_t numStages, uint32_t dataNum,
                                          uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_IIR_CONVOLUTION,
                    ((READ_REG(
                          FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos) - numStages,
                    numStages);

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = *(float *)&FMAC->FIFO_DATA;
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

/**
 * @brief IIR convolution DMA and interrupt configuration
 *
 * @return DRV_Status
 */
DRV_Status FMAC_IIR_convolutionInterruptDMA(uint8_t numStages)
{
    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc(FMAC_IIR_CONVOLUTION,
                    ((READ_REG(
                          FMAC->X2_BUF) & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos) - numStages,
                    numStages);
    return DRV_OK;
}

/**
 * @brief FIR and IIR convolution data append
 *
 * @param pInputData
 * @param pInputDataNum
 * @param maxInputDataNum
 * @param pOutoutData
 * @param pOutoutDataNum
 * @param maxOutoutDataNum
 * @param timeout
 * @return DRV_Status
 */
DRV_Status FMAC_convolutionAppend(int16_t *pInputData, int16_t *pOutoutData, uint32_t dataNum, uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            WRITE_REG(FMAC->FIFO_DATA, (uint32_t)*pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = (int16_t)READ_REG(FMAC->FIFO_DATA);
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

DRV_Status FMAC_convolutionAppendFloat(float *pInputData, float *pOutoutData, uint32_t dataNum, uint32_t timeout)
{
    uint32_t inputNum  = dataNum;
    uint32_t outputNum = dataNum;

    while (1)
    {
        while (inputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)pInputData++);
            inputNum--;
        }

        while (outputNum != 0)
        {
            if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0)
            {
                if (timeout-- == 0)
                {
                    return DRV_TIMEOUT;
                }
                break;
            }
            *pOutoutData++ = *(float *)&FMAC->FIFO_DATA;
            outputNum--;
        }

        if ((inputNum == 0) && (outputNum == 0))
        {
            break;
        }
    }
    return DRV_OK;
}

/**
 * @brief set FIFO data
 *
 * @return int16_t
 */
void FMAC_setFIFOData(int16_t data)
{
    WRITE_REG(FMAC->FIFO_DATA, (uint32_t)data);
}

void FMAC_setFIFODataFloat(float data)
{
    float data_temp = data;

    WRITE_REG(FMAC->FIFO_DATA, *(uint32_t *)&data_temp);
}

/**
 * @brief get FIFO data
 *
 * @return int16_t
 */
int16_t FMAC_getFIFOData(void)
{
    return (int16_t)READ_REG(FMAC->FIFO_DATA);
}

float FMAC_getFIFODataFloat(void)
{
    return *(float *)&FMAC->FIFO_DATA;
}

/**
 * @brief clear buff zone
 *
 */
void FMAC_clearBuffZone(void)
{
    SET_BIT(FMAC->CR, FMAC_CR_CLR_Msk);
}

/**
 * @brief get function busy status
 *
 * @return true
 * @return false
 */
bool FMAC_isFuncBusy(void)
{
    if ((READ_REG(FMAC->PARAM) & FMAC_PARAM_ENABLE_Msk) != 0)
    {
        return true;
    }
    else
    {
        return false;
    }
}

/**
 * @brief get X1 buff spare space number
 *
 * @return uint8_t
 */
uint8_t FMAC_getX1BuffSpareSpaceNum(void)
{
    return (uint8_t)(READ_BIT(FMAC->SR, FMAC_SR_X1_SPARE_NUM_RPT_Msk) >> FMAC_SR_X1_SPARE_NUM_RPT_Pos);
}

/**
 * @brief get Y buff spare space number
 *
 * @return uint8_t
 */
uint8_t FMAC_getYBuffUnreadDataNum(void)
{
    return (uint8_t)(READ_BIT(FMAC->SR, FMAC_SR_Y_UNRD_NUM_RPT_Msk) >> FMAC_SR_Y_UNRD_NUM_RPT_Pos);
}

/**
 * @brief get FMAC status
 *
 * @return uint32_t
 */
uint32_t FMAC_getStatus(void)
{
    uint32_t masks;

    masks = READ_REG(FMAC->SR) & (FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK |
                                  FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK |
                                  FMAC_STS_X1_BUFF_IS_OVERFLOW_FLAG_MASK |
                                  FMAC_STS_Y_BUFF_IS_UNDERFLOW_FLAG_MASK |
                                  FMAC_STS_ACCUMULATOR_DATA_IS_SAT_FLAG_MASK |
                                  FMAC_STS_OUTPUT_IS_NEGATIVE_WITH_OFFSET_FLAG_MASK |
                                  FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk);
    return masks;
}

/**
 * @brief enable interrupt
 *
 * @param interruptMasks
 */
void FMAC_enableInterrupt(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    SET_BIT(FMAC->INT_EN, interruptMasks);
}

/**
 * @brief disable interrupt
 *
 * @param interruptMasks
 */
void FMAC_disableInterrupt(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    CLEAR_BIT(FMAC->INT_EN, interruptMasks);
}

/**
 * @brief force interrupt
 *
 * @param interruptMasks
 */
void FMAC_forceInterrupt(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    SET_BIT(FMAC->INT_FORCE_IND, interruptMasks);
}

/**
 * @brief clear interrupt status
 *
 * @param interruptMasks
 */
void FMAC_clearInterruptStatus(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    SET_BIT(FMAC->INT_CLR, interruptMasks);
}

/**
 * @brief get interrupt raw status
 *
 * @return uint32_t
 */
uint32_t FMAC_getInterruptStatusRaw(void)
{
    return READ_REG(FMAC->INT_RAW_RPT);
}

/**
 * @brief get interrupt status
 *
 * @return uint32_t
 */
uint32_t FMAC_getInterruptStatus(void)
{
    return READ_REG(FMAC->INT_STATUS_RPT);
}

/**
 * @brief set interrupt masks
 *
 * @param interruptMasks
 */
void FMAC_setInterruptMask(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    SET_BIT(FMAC->INT_MASK, interruptMasks);
}

/**
 * @brief clear interrupt masks
 *
 * @param interruptMasks
 */
void FMAC_clearInterruptMask(uint32_t interruptMasks)
{
    assert_param(IS_FMAC_INT_MASK(interruptMasks));

    CLEAR_BIT(FMAC->INT_MASK, interruptMasks);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

enum
{
    FMAC_TEST_FUNCTION_LOAD_X1 = 1u,
    FMAC_TEST_FUNCTION_LOAD_X2 = 2u,
    FMAC_TEST_FUNCTION_LOAD_Y = 3u,
    FMAC_TEST_FUNCTION_FIR = 4u,
    FMAC_TEST_FUNCTION_IIR = 5u,
    FMAC_TEST_FUNCTION_MAX = FMAC_TEST_FUNCTION_IIR
};

#define FMAC_TEST_W1C_STATUS_MASK                                                            \
    (FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk | FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk)

/**
 * @brief Wait until the current FMAC initialization function completes.
 * @param timeout Maximum number of status polls.
 * @return DRV_OK when idle, otherwise DRV_TIMEOUT.
 */
static DRV_Status FMAC_testWaitIdle(uint32_t timeout)
{
    while (FMAC_isFuncBusy())
    {
        if (timeout-- == 0u)
        {
            return DRV_TIMEOUT;
        }
    }

    return DRV_OK;
}

/**
 * @brief Stop the active FMAC function by clearing PARAM.ENABLE.
 * @return DRV_OK after the hardware enable bit is cleared.
 */
DRV_Status FMAC_testStopFunction(void)
{
    CLEAR_BIT(FMAC->PARAM, FMAC_PARAM_ENABLE_Msk);

    return FMAC_isFuncBusy() ? DRV_BUSY : DRV_OK;
}

/**
 * @brief Clear dynamic FMAC state and software-clearable conversion reports.
 * @param timeout Maximum number of CR.CLR completion polls.
 * @note ET6801 keeps a conversion report asserted while its live hardware
 *       condition remains present.  The caller must first submit a normal
 *       conversion before this W1C clear can take effect.
 * @return DRV_OK when the clear command completes, otherwise DRV_TIMEOUT.
 */
DRV_Status FMAC_testClearDynamicState(uint32_t timeout)
{
    SET_BIT(FMAC->CR, FMAC_CR_CLR_Msk);

    while ((READ_REG(FMAC->CR) & FMAC_CR_CLR_Msk) != 0u)
    {
        if (timeout-- == 0u)
        {
            return DRV_TIMEOUT;
        }
    }

    WRITE_REG(FMAC->SR, FMAC_TEST_W1C_STATUS_MASK);

    return DRV_OK;
}

/**
 * @brief Start one raw FMAC function with explicit P/Q parameters.
 * @param function Hardware function selector in the documented range 1 through 5.
 * @param pValue Hardware P parameter.
 * @param qValue Hardware Q parameter.
 * @return DRV_OK when accepted, otherwise DRV_PARAM_ERR or DRV_BUSY.
 */
DRV_Status FMAC_testStartFunction(uint8_t function, uint8_t pValue, uint8_t qValue)
{
    if ((function == 0u) || (function > FMAC_TEST_FUNCTION_MAX))
    {
        return DRV_PARAM_ERR;
    }

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    FMAC_selectFunc((FMAC_Func)function, pValue, qValue);

    return DRV_OK;
}

/**
 * @brief Read the complete validation-relevant FMAC configuration.
 * @param snapshot Destination for decoded configuration fields.
 * @return DRV_OK on success or DRV_PARAM_ERR for a null destination.
 */
DRV_Status FMAC_testGetConfigSnapshot(FMAC_TestConfigSnapshot *snapshot)
{
    uint32_t control;
    uint32_t outputControl;
    uint32_t x1;
    uint32_t x2;
    uint32_t y;

    if (snapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    x1 = READ_REG(FMAC->X1_BUF);
    x2 = READ_REG(FMAC->X2_BUF);
    y = READ_REG(FMAC->Y_BUF);
    control = READ_REG(FMAC->CR);
    outputControl = READ_REG(FMAC->OUT_CR);

    snapshot->x1Base = (uint8_t)((x1 & FMAC_X1_BUF_X1_BASE_Msk) >> FMAC_X1_BUF_X1_BASE_Pos);
    snapshot->x1Size = (uint8_t)((x1 & FMAC_X1_BUF_X1_BUF_SIZE_Msk) >> FMAC_X1_BUF_X1_BUF_SIZE_Pos);
    snapshot->x1FullWatermark =
        (uint8_t)((x1 & FMAC_X1_BUF_X1_FULL_WM_Msk) >> FMAC_X1_BUF_X1_FULL_WM_Pos);
    snapshot->x2Base = (uint8_t)((x2 & FMAC_X2_BUF_X2_BASE_Msk) >> FMAC_X2_BUF_X2_BASE_Pos);
    snapshot->x2Size = (uint8_t)((x2 & FMAC_X2_BUF_X2_BUF_SIZE_Msk) >> FMAC_X2_BUF_X2_BUF_SIZE_Pos);
    snapshot->yBase = (uint8_t)((y & FMAC_Y_BUF_Y_BASE_Msk) >> FMAC_Y_BUF_Y_BASE_Pos);
    snapshot->ySize = (uint8_t)((y & FMAC_Y_BUF_Y_BUF_SIZE_Msk) >> FMAC_Y_BUF_Y_BUF_SIZE_Pos);
    snapshot->yEmptyWatermark =
        (uint8_t)((y & FMAC_Y_BUF_Y_EMPTY_WM_Msk) >> FMAC_Y_BUF_Y_EMPTY_WM_Pos);
    snapshot->accumulatorWrapEnable =
        (uint8_t)((control & FMAC_CR_ACC_OUT_WRAP_SEL_Msk) != 0u);
    snapshot->outputDataMode =
        (uint8_t)((control & FMAC_CR_DAT_OUT_SEL_Msk) >> FMAC_CR_DAT_OUT_SEL_Pos);
    snapshot->dmaReadEnable = (uint8_t)((control & FMAC_CR_DMA_REN_Msk) != 0u);
    snapshot->dmaWriteEnable = (uint8_t)((control & FMAC_CR_DMA_WEN_Msk) != 0u);
    snapshot->clipEnable = (uint8_t)((control & FMAC_CR_CLIPEN_Msk) != 0u);
    snapshot->floatInputEnable = (uint8_t)((control & FMAC_CR_FLOAT2FIXED_IN_SEL_Msk) != 0u);
    snapshot->floatOutputEnable = (uint8_t)((control & FMAC_CR_FIXED2FLOAT_O_SEL_Msk) != 0u);
    snapshot->outputDataShift =
        (uint8_t)((outputControl & FMAC_OUT_CR_SH_Msk) >> FMAC_OUT_CR_SH_Pos);
    snapshot->outputDataOffset =
        (uint16_t)((outputControl & FMAC_OUT_CR_OFT_Msk) >> FMAC_OUT_CR_OFT_Pos);

    return DRV_OK;
}

/** @brief Return all FMAC status bits for validation-only decoding. */
uint32_t FMAC_testGetStatusRaw(void)
{
    return READ_REG(FMAC->SR);
}

/**
 * @brief Set only FMAC DMA request gates while idle.
 * @param inputEnable Input/write DMA request gate.
 * @param outputEnable Output/read DMA request gate.
 * @return DRV_OK on success, DRV_PARAM_ERR for invalid values or DRV_BUSY while active.
 */
DRV_Status FMAC_testSetDMARequests(ControlStatus inputEnable, ControlStatus outputEnable)
{
    uint32_t value;

    if (((inputEnable != DISABLE) && (inputEnable != ENABLE)) ||
        ((outputEnable != DISABLE) && (outputEnable != ENABLE)))
    {
        return DRV_PARAM_ERR;
    }

    if (FMAC_isFuncBusy())
    {
        return DRV_BUSY;
    }

    value = ((uint32_t)inputEnable << FMAC_CR_DMA_WEN_Pos) |
            ((uint32_t)outputEnable << FMAC_CR_DMA_REN_Pos);
    MODIFY_REG(FMAC->CR, FMAC_CR_DMA_WEN_Msk | FMAC_CR_DMA_REN_Msk, value);

    return DRV_OK;
}

/** @brief Load exact signed fixed-point items into X1. */
DRV_Status FMAC_testLoadX1(const int16_t *data, uint8_t count, uint32_t timeout)
{
    uint8_t index;

    if ((data == NULL) || (count == 0u) || FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    FMAC_selectFunc(FMAC_LOAD_X1_BUFF, count, 0u);

    for (index = 0u; index < count; ++index)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)(uint16_t)data[index]);
    }

    return FMAC_testWaitIdle(timeout);
}

/** @brief Load exact IEEE754 Float32 items into X1. */
DRV_Status FMAC_testLoadX1Float(const float *data, uint8_t count, uint32_t timeout)
{
    uint8_t index;
    uint32_t raw;

    if ((data == NULL) || (count == 0u) || FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    FMAC_selectFunc(FMAC_LOAD_X1_BUFF, count, 0u);

    for (index = 0u; index < count; ++index)
    {
        (void)memcpy(&raw, &data[index], sizeof(raw));
        WRITE_REG(FMAC->FIFO_DATA, raw);
    }

    return FMAC_testWaitIdle(timeout);
}

/** @brief Load exact signed fixed-point coefficient segments into X2. */
DRV_Status FMAC_testLoadX2(const int16_t *feedforward, uint8_t feedforwardCount,
                           const int16_t *feedback, uint8_t feedbackCount, uint32_t timeout)
{
    uint8_t index;

    if ((feedforward == NULL) || (feedforwardCount == 0u) ||
        ((feedbackCount != 0u) && (feedback == NULL)) || FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    FMAC_selectFunc(FMAC_LOAD_X2_BUFF, feedforwardCount, feedbackCount);

    for (index = 0u; index < feedforwardCount; ++index)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)(uint16_t)feedforward[index]);
    }

    for (index = 0u; index < feedbackCount; ++index)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)(uint16_t)feedback[index]);
    }

    return FMAC_testWaitIdle(timeout);
}

/** @brief Load exact signed fixed-point items into Y. */
DRV_Status FMAC_testLoadY(const int16_t *data, uint8_t count, uint32_t timeout)
{
    uint8_t index;

    if ((data == NULL) || (count == 0u) || FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    FMAC_selectFunc(FMAC_LOAD_Y_BUFF, count, 0u);

    for (index = 0u; index < count; ++index)
    {
        WRITE_REG(FMAC->FIFO_DATA, (uint32_t)(uint16_t)data[index]);
    }

    return FMAC_testWaitIdle(timeout);
}

/** @brief Load exact IEEE754 Float32 items into Y. */
DRV_Status FMAC_testLoadYFloat(const float *data, uint8_t count, uint32_t timeout)
{
    uint8_t index;
    uint32_t raw;

    if ((data == NULL) || (count == 0u) || FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    FMAC_selectFunc(FMAC_LOAD_Y_BUFF, count, 0u);

    for (index = 0u; index < count; ++index)
    {
        (void)memcpy(&raw, &data[index], sizeof(raw));
        WRITE_REG(FMAC->FIFO_DATA, raw);
    }

    return FMAC_testWaitIdle(timeout);
}

/** @brief Perform one unchecked raw FIFO write. */
void FMAC_testWriteFIFOUnchecked(uint32_t value)
{
    WRITE_REG(FMAC->FIFO_DATA, value);
}

/** @brief Perform one unchecked raw FIFO read. */
uint32_t FMAC_testReadFIFOUnchecked(void)
{
    return READ_REG(FMAC->FIFO_DATA);
}

/** @brief Read the complete FMAC interrupt-enable register. */
uint32_t FMAC_testGetInterruptEnable(void)
{
    return READ_REG(FMAC->INT_EN) & FMAC_INT_EN_INT_EN_Msk;
}

/** @brief Read the complete FMAC interrupt-mask register. */
uint32_t FMAC_testGetInterruptMask(void)
{
    return READ_REG(FMAC->INT_MASK) & FMAC_INT_MASK_INT_MASK_Msk;
}

/**
 * @brief Process one bounded FMAC stream and return target-local DWT cycles.
 * @param function FIR or IIR hardware function selector.
 * @param pValue Hardware P parameter.
 * @param qValue Hardware Q parameter.
 * @param source Caller-owned Q15 or Float32 input array.
 * @param destination Caller-owned Q15 or Float32 output array.
 * @param count Number of input and output items.
 * @param useFloat Selects Float32 when ENABLE and Q15 when DISABLE.
 * @param timeout Maximum no-progress poll count.
 * @param acceptedCount Receives the number of input items accepted.
 * @param readCount Receives the number of output items returned.
 * @param elapsedCycles Receives the DWT delta from function start through final output read.
 * @return DRV_OK on completion, otherwise a stable Driver error.
 */
DRV_Status FMAC_testProcessTimed(uint8_t function, uint8_t pValue, uint8_t qValue,
                                 const void *source, void *destination, uint16_t count,
                                 ControlStatus useFloat, uint32_t timeout,
                                 uint32_t *acceptedCount, uint32_t *readCount,
                                 uint32_t *elapsedCycles)
{
    uint32_t previousDemcr;
    uint32_t previousDwtCtrl;
    uint32_t previousPrimask;
    uint32_t startCycles;
    uint32_t inputCount = 0u;
    uint32_t outputCount = 0u;
    uint32_t noProgressBudget = timeout;
    bool progressed;

    if ((source == NULL) || (destination == NULL) || (count == 0u) || (timeout == 0u) ||
        (acceptedCount == NULL) || (readCount == NULL) || (elapsedCycles == NULL) ||
        ((useFloat != DISABLE) && (useFloat != ENABLE)) ||
        ((function != FMAC_TEST_FUNCTION_FIR) && (function != FMAC_TEST_FUNCTION_IIR)) ||
        (pValue == 0u) || ((function == FMAC_TEST_FUNCTION_FIR) && (qValue != 0u)) ||
        FMAC_isFuncBusy())
    {
        return DRV_PARAM_ERR;
    }

    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0u)
    {
        return DRV_ERROR;
    }

    previousDemcr = CoreDebug->DEMCR;
    previousDwtCtrl = DWT->CTRL;
    previousPrimask = __get_PRIMASK();
    CoreDebug->DEMCR = previousDemcr | CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL = previousDwtCtrl | DWT_CTRL_CYCCNTENA_Msk;
    __disable_irq();

    startCycles = DWT->CYCCNT;
    FMAC_selectFunc((FMAC_Func)function, pValue, qValue);

    while ((inputCount < count) || (outputCount < count))
    {
        progressed = false;

        if ((inputCount < count) &&
            ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) == 0u))
        {
            if (useFloat == ENABLE)
            {
                FMAC_setFIFODataFloat(((const float *)source)[inputCount]);
            }
            else
            {
                FMAC_setFIFOData(((const int16_t *)source)[inputCount]);
            }

            ++inputCount;
            progressed = true;
        }

        if ((outputCount < count) &&
            ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) == 0u))
        {
            if (useFloat == ENABLE)
            {
                ((float *)destination)[outputCount] = FMAC_getFIFODataFloat();
            }
            else
            {
                ((int16_t *)destination)[outputCount] = FMAC_getFIFOData();
            }

            ++outputCount;
            progressed = true;
        }

        if (!progressed && (noProgressBudget-- == 0u))
        {
            (void)FMAC_testStopFunction();
            DWT->CTRL = previousDwtCtrl;
            CoreDebug->DEMCR = previousDemcr;

            if (previousPrimask == 0u)
            {
                __enable_irq();
            }

            *acceptedCount = inputCount;
            *readCount = outputCount;
            *elapsedCycles = 0u;

            return DRV_TIMEOUT;
        }
    }

    *elapsedCycles = DWT->CYCCNT - startCycles;
    *acceptedCount = inputCount;
    *readCount = outputCount;
    (void)FMAC_testStopFunction();
    DWT->CTRL = previousDwtCtrl;
    CoreDebug->DEMCR = previousDemcr;

    if (previousPrimask == 0u)
    {
        __enable_irq();
    }

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif
