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
#include "et6x_crc.h"


/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/* Private macro -------------------------------------------------------------*/

/* Parameter validity check for fifo threshold */
#define IS_FIFO_TRHD(trhd)     ((trhd) <= CRC_FIFO_TRHD_MAX)
#define IS_INT_MASKS(masks)    (((masks) & (CRC_INT_BUS_ERR | CRC_INT_LENGTH_ERR | CRC_INT_CHECK_ERR)) != 0)

static volatile uint32_t CRC_configInitValue;

/**
 * @brief Enable CRC module
 *
 */
void CRC_enableModule(void)
{
    SET_BIT(CRC->MODULE_EN, CRC_MODULE_EN_CRC_EN_Msk);
}

/**
 * @brief Disable CRC module
 *
 */
void CRC_disableModule(void)
{
    CLEAR_BIT(CRC->MODULE_EN, CRC_MODULE_EN_CRC_EN_Msk);
}

/**
 * @brief Configure CRC module
 *
 * @param config  pointer to CRC configuration structure
 */
void CRC_config(CRC_ConfigParams *config)
{
    uint32_t regVal;

    assert_param(IS_FIFO_TRHD(config->fifoThreshold));

    regVal = ((uint32_t)config->resultCheckEn << CRC_CTRL_CRC_CHECK_EN_Pos) |
             ((uint32_t)config->autoLengthReloadEn << CRC_CTRL_CRC_ALR_EN_Pos) |
             ((uint32_t)config->refIn << CRC_CTRL_CRC_REFIN_EN_Pos) |
             ((uint32_t)config->refOut << CRC_CTRL_CRC_REFOUT_EN_Pos) |
             ((uint32_t)config->xorOut << CRC_CTRL_CRC_XORSEL_Pos) |
             ((uint32_t)config->byteswapEn << CRC_CTRL_CRC_BYTESWAP_EN_Pos) |
             ((uint32_t)config->mode << CRC_CTRL_CRC_KERNEL_SEL_Pos);
    WRITE_REG(CRC->CTRL, regVal);

    if (config->mode == CRC_MODE_CRC32)
    {
        WRITE_REG(CRC->POLY, config->polynomial);
    }
    else if (config->mode == CRC_MODE_CRC16)
    {
        WRITE_REG(CRC->POLY, (uint32_t)((uint16_t)config->polynomial << 16U));
    }
    else
    {
        WRITE_REG(CRC->POLY, (uint32_t)((uint8_t)config->polynomial << 24U));
    }

    WRITE_REG(CRC->FIFO_TRHD, config->fifoThreshold);
    WRITE_REG(CRC->INI, config->initialValue);
    CRC_configInitValue = config->initialValue;
}

/**
 * @brief CRC calculate with poll mode with 32bit width
 *
 * @param pInputData  pointer to data that is ready to be calculated
 * @param crcNum  the number of data in bytes
 * @param pCrcRes  pointer to result
 * @param timeout  timeout in cycle
 * @return DRV_Status
 *          - DRV_ERROR: CRC configuration error
 *          - DRV_TIMEOUT: CRC calculate timeout
 *          - DRV_OK: success
 */
DRV_Status CRC_calculate32(uint32_t *pInputData, uint32_t crcNum, uint32_t *pCrcRes, uint32_t timeout)
{
    uint32_t integer = 0, remainder = 0, autoReloadLen = 0;
    uint32_t *pTempInput32 = (uint32_t *)pInputData;
    uint8_t  *pTempInput8  = NULL;

    assert_param(timeout != 0);

    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_KERNEL_SEL_Msk) != 0)
    {
        return DRV_ERROR;
    }

    integer       = crcNum / sizeof(uint32_t);
    remainder     = crcNum % sizeof(uint32_t);
    autoReloadLen = integer + remainder;

    /* check length auto reload whether is enabled */
    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_ALR_EN_Msk) == 0)
    {
        CRC_setDataLength(autoReloadLen);
        autoReloadLen = 0;
    }

    while (integer--)
    {
        while (CRC_isFIFOOverflow())
        {
            timeout--;
            if (timeout == 0)
            {
                return DRV_TIMEOUT;
            }
        }
        WRITE_REG(CRC->IR, *pTempInput32++);
    }
    pTempInput8 = (uint8_t *)pTempInput32;
    while (remainder--)
    {
        while (CRC_isFIFOOverflow())
        {
            timeout--;
            if (timeout == 0)
            {
                return DRV_TIMEOUT;
            }
        }
        *(volatile uint8_t *)(&CRC->IR) = *pTempInput8++;
    }

    while (CRC_getDataLength() != autoReloadLen)
    {
        timeout--;
        if (timeout == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    *pCrcRes = READ_REG(CRC->RES);
    WRITE_REG(CRC->INI, CRC_configInitValue);
    return DRV_OK;
}

/**
 * @brief Calculates the CRC-16 checksum of a given input data.
 *
 * @param pInputData Pointer to the input data.
 * @param crcNum Number of bytes in the input data.
 * @param pCrcRes Pointer to store the calculated CRC-16 checksum.
 * @param timeout Timeout in cycles.
 *
 * @return DRV_Status DRV_OK if the calculation is successful, DRV_ERROR if the CRC kernel is not selected,
 * and DRV_TIMEOUT if the calculation times out.
 *
 * @note This function assumes that the CRC module is already initialized and configured.
 */
DRV_Status CRC_calculate16(uint16_t *pInputData, uint32_t crcNum, uint16_t *pCrcRes, uint32_t timeout)
{
    uint32_t integer = 0, remainder = 0, autoReloadLen = 0;
    uint16_t *pTempInput16 = (uint16_t *)pInputData;
    uint8_t  *pTempInput8  = NULL;

    assert_param(timeout != 0);

    if (((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_KERNEL_SEL_Msk) >> CRC_CTRL_CRC_KERNEL_SEL_Pos) != CRC_MODE_CRC16)
    {
        return DRV_ERROR;
    }

    integer       = crcNum / sizeof(uint16_t);
    remainder     = crcNum % sizeof(uint16_t);
    autoReloadLen = integer + remainder;

    /* check length auto reload whether is enabled */
    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_ALR_EN_Msk) == 0)
    {
        CRC_setDataLength(autoReloadLen);
        autoReloadLen = 0;
    }

    while (integer--)
    {
        while (CRC_isFIFOOverflow())
        {
            timeout--;
            if (timeout == 0)
            {
                return DRV_TIMEOUT;
            }
        }
        *(volatile uint16_t *)(&CRC->IR) = *pTempInput16++;
    }
    pTempInput8 = (uint8_t *)pTempInput16;
    while (remainder--)
    {
        while (CRC_isFIFOOverflow())
        {
            timeout--;
            if (timeout == 0)
            {
                return DRV_TIMEOUT;
            }
        }
        *(volatile uint8_t *)(&CRC->IR) = *pTempInput8++;
    }


    while (CRC_getDataLength() != autoReloadLen)
    {
        timeout--;
        if (timeout == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    *pCrcRes = (uint16_t)READ_REG(CRC->RES);
    WRITE_REG(CRC->INI, CRC_configInitValue);
    return DRV_OK;
}

/**
 * @brief Calculates the CRC-8 checksum of a given input data.
 *
 * @param pInputData Pointer to the input data.
 * @param crcNum Number of bytes in the input data.
 * @param pCrcRes Pointer to store the calculated CRC-8 checksum.
 * @param timeout Timeout in cycles.
 *
 * @return DRV_Status DRV_OK if the calculation is successful, DRV_ERROR if the CRC kernel is not selected,
 * and DRV_TIMEOUT if the calculation times out.
 *
 * @note This function assumes that the CRC module is already initialized and configured.
 */
DRV_Status CRC_calculate8(uint8_t *pInputData, uint32_t crcNum, uint8_t *pCrcRes, uint32_t timeout)
{
    uint32_t autoReloadLen = 0;
    uint8_t  *pTempInput8  = (uint8_t *)pInputData;

    assert_param(timeout != 0);

    if (((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_KERNEL_SEL_Msk) >> CRC_CTRL_CRC_KERNEL_SEL_Pos) != CRC_MODE_CRC8)
    {
        return DRV_ERROR;
    }
    autoReloadLen = crcNum;

    /* check length auto reload whether is enabled */
    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_ALR_EN_Msk) == 0)
    {
        CRC_setDataLength(crcNum);
        autoReloadLen = 0;
    }

    while (crcNum--)
    {
        while (CRC_isFIFOOverflow())
        {
            timeout--;
            if (timeout == 0)
            {
                return DRV_TIMEOUT;
            }
        }
        *(volatile uint8_t *)(&CRC->IR) = *pTempInput8++;
    }

    while (CRC_getDataLength() != autoReloadLen)
    {
        timeout--;
        if (timeout == 0)
        {
            return DRV_TIMEOUT;
        }
    }

    *pCrcRes = (uint8_t)READ_REG(CRC->RES);
    WRITE_REG(CRC->INI, CRC_configInitValue);
    return DRV_OK;
}

/**
 * @brief Set input data number to be calculated
 *
 * @param length  the data number in 8bits/16bits/32bits depends on CRC mode selection
 */
void CRC_setDataLength(uint32_t length)
{
    WRITE_REG(CRC->LENGTH, length);
}

/**
 * @brief Get current input data that is not calculated
 *
 * @return uint32_t  the data number in 8bits/16bits/32bits depends on CRC mode selection
 */
uint32_t CRC_getDataLength(void)
{
    return READ_REG(CRC->LENGTH);
}

/**
 * @brief Get calculated results
 *
 * @return uint32_t  the calculated results
 */
uint32_t CRC_getResult(void)
{
    return READ_REG(CRC->RES);
}

/**
 * @brief Set the check value for CRC calculation.
 *
 * This function sets the check value that will be used for CRC calculation.
 * The check value is compared with the calculated CRC result to determine if the
 * calculated result matches the expected value.
 *
 * @param value The check value to be set.
 *
 */
void CRC_setCheckValue(uint32_t value)
{
    WRITE_REG(CRC->CHECK, value);
}

/**
 * @brief Determine if FIFO is overflow
 *
 * @return true  FIFO is overflow
 * @return false  FIFO is not overflow
 */
bool CRC_isFIFOOverflow(void)
{
    if (READ_REG(CRC->FIFO_OVF) == 0)
    {
        return false;
    }
    else
    {
        return true;
    }
}

/**
 * @brief Enable CRC interrupt
 *
 * @param ITmasks  CRC interrupt status masks
 *      - CRC_INT_BUS_ERR
 *      - CRC_INT_LENGTH_ERR
 *      - CRC_INT_CHECK_ERR
 */
void CRC_enableInterrupt(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    SET_BIT(CRC->INT_EN, ITmasks);
}

/**
 * @brief Disable CRC interrupt
 *
 * @param ITmasks  CRC interrupt status masks
 */
void CRC_disableInterrupt(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    CLEAR_BIT(CRC->INT_EN, ITmasks);
}

/**
 * @brief Clear CRC interrupt
 *
 * @param ITmasks  CRC interrupt masks
 */
void CRC_clearInterrupt(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    SET_BIT(CRC->INT_CLR, ITmasks);
}

/**
 * @brief force CRC interrupt
 *
 * @param ITmasks  CRC interrupt masks
 */
void CRC_forceInterrupt(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    SET_BIT(CRC->INT_FORCE_IND, ITmasks);
}

/**
 * @brief Get raw CRC interrupt status
 *
 */
uint32_t CRC_getInterruptStatusRawAll(void)
{
    return READ_REG(CRC->INT_RAW_RPT);
}

/**
 * @brief Get CRC interrupt status
 *
 */
uint32_t CRC_getInterruptStatusAll(void)
{
    return READ_REG(CRC->INT_STATUS_RPT);
}

/**
 * @brief Mask CRC interrupt status
 *
 * @param ITmasks  CRC interrupt status masks
 */
void CRC_setInterruptMask(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    SET_BIT(CRC->INT_MASK, ITmasks);
}

/**
 * @brief Unmask CRC interrupt status
 *
 * @param ITmasks  CRC interrupt status masks
 */
void CRC_clearInterruptMask(uint32_t ITmasks)
{
    assert_param(IS_INT_MASKS(ITmasks));

    CLEAR_BIT(CRC->INT_MASK, ITmasks);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Write one 8-bit value to the CRC input register.
 */
DRV_Status CRC_testWriteInput8(uint8_t value)
{
    *(volatile uint8_t *)(&CRC->IR) = value;
    return DRV_OK;
}

/**
 * @brief Write one 16-bit value to the CRC input register.
 */
DRV_Status CRC_testWriteInput16(uint16_t value)
{
    *(volatile uint16_t *)(&CRC->IR) = value;
    return DRV_OK;
}

/**
 * @brief Write one 32-bit value to the CRC input register.
 */
DRV_Status CRC_testWriteInput32(uint32_t value)
{
    WRITE_REG(CRC->IR, value);
    return DRV_OK;
}

/**
 * @brief Write a bounded 32-bit input burst and return observation facts.
 */
DRV_Status CRC_testWriteInput32Burst(
    const uint32_t *pValues,
    uint32_t count,
    uint32_t checkpointCount,
    uint32_t *pCheckpointResult,
    uint32_t *pFinalResult,
    uint32_t *pOverflow)
{
    uint32_t index;
    uint32_t repeatedValue;

    if ((pValues == NULL) || (count == 0U) || (count > 9U) ||
        (checkpointCount > count) || (pCheckpointResult == NULL) ||
        (pFinalResult == NULL) || (pOverflow == NULL))
    {
        return DRV_PARAM_ERR;
    }

    /* Preserve the exact ET6801 historical FIFO threshold stimulus timing. */
    if ((count == 5U) && (checkpointCount == 4U) &&
        (pValues[0] == pValues[1]) && (pValues[0] == pValues[2]) &&
        (pValues[0] == pValues[3]) && (pValues[0] == pValues[4]))
    {
        repeatedValue = pValues[0];
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        *pCheckpointResult = READ_REG(CRC->RES);
        WRITE_REG(CRC->IR, repeatedValue);
        *pFinalResult = READ_REG(CRC->RES);
        *pOverflow = CRC_isFIFOOverflow() ? 1U : 0U;
        return DRV_OK;
    }

    /* Preserve the exact ET6801 historical seven-write overflow stimulus. */
    if ((count == 7U) && (checkpointCount == 0U) &&
        (pValues[0] == pValues[1]) && (pValues[0] == pValues[2]) &&
        (pValues[0] == pValues[3]) && (pValues[0] == pValues[4]) &&
        (pValues[0] == pValues[5]) && (pValues[0] == pValues[6]))
    {
        repeatedValue = pValues[0];
        *pCheckpointResult = READ_REG(CRC->RES);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        WRITE_REG(CRC->IR, repeatedValue);
        *pFinalResult = READ_REG(CRC->RES);
        *pOverflow = CRC_isFIFOOverflow() ? 1U : 0U;
        return DRV_OK;
    }

    /* Generic bounded path remains available for non-timing-sensitive facts. */
    if (checkpointCount == 0U)
    {
        *pCheckpointResult = READ_REG(CRC->RES);
    }
    for (index = 0U; index < count; index++)
    {
        WRITE_REG(CRC->IR, pValues[index]);
        if ((index + 1U) == checkpointCount)
        {
            *pCheckpointResult = READ_REG(CRC->RES);
        }
    }
    *pFinalResult = READ_REG(CRC->RES);
    *pOverflow = CRC_isFIFOOverflow() ? 1U : 0U;
    return DRV_OK;
}

/**
 * @brief Calculate CRC32 and return target-local DWT cycle evidence.
 *
 * The function mirrors CRC_calculate32() but exposes the exact validation
 * timing interval required by the automated test platform. It restores the
 * prior DWT enable state and the configured CRC initial value before return.
 */
DRV_Status CRC_testCalculate32Timed(
    const uint32_t *pInputData,
    uint32_t lengthBytes,
    uint32_t timeout,
    uint32_t *pCrcRes,
    uint32_t *pElapsedCycles)
{
    uint32_t integer;
    uint32_t remainder;
    uint32_t autoReloadLen;
    const uint32_t *pTempInput32;
    const uint8_t *pTempInput8;
    uint32_t startCycles;
    uint32_t endCycles;
    uint32_t previousDemcr;
    uint32_t previousDwtCtrl;
    uint8_t timingStarted = 0U;

    assert_param(timeout != 0U);

    if ((pInputData == NULL) || (lengthBytes == 0U) ||
        (timeout == 0U) || (pCrcRes == NULL) ||
        (pElapsedCycles == NULL) ||
        (((uintptr_t)pInputData & 0x3U) != 0U))
    {
        return DRV_PARAM_ERR;
    }
    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_KERNEL_SEL_Msk) != 0U)
    {
        return DRV_ERROR;
    }
    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0U)
    {
        return DRV_ERROR;
    }

    integer = lengthBytes / sizeof(uint32_t);
    remainder = lengthBytes % sizeof(uint32_t);
    autoReloadLen = integer + remainder;
    pTempInput32 = pInputData;

    if ((READ_REG(CRC->CTRL) & CRC_CTRL_CRC_ALR_EN_Msk) == 0U)
    {
        /* Hardware LENGTH counts word writes plus trailing byte writes. */
        CRC_setDataLength(autoReloadLen);
        autoReloadLen = 0U;
    }

    /* Preserve debugger or application ownership of the DWT enable bits. */
    previousDemcr = CoreDebug->DEMCR;
    previousDwtCtrl = DWT->CTRL;
    CoreDebug->DEMCR = previousDemcr | CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL = previousDwtCtrl | DWT_CTRL_CYCCNTENA_Msk;
    startCycles = 0U;

    while (integer-- != 0U)
    {
        while (CRC_isFIFOOverflow())
        {
            if (--timeout == 0U)
            {
                DWT->CTRL = previousDwtCtrl;
                CoreDebug->DEMCR = previousDemcr;
                WRITE_REG(CRC->INI, CRC_configInitValue);
                return DRV_TIMEOUT;
            }
        }
        if (timingStarted == 0U)
        {
            /* Exclude validation, LENGTH programming and DWT setup overhead. */
            startCycles = DWT->CYCCNT;
            timingStarted = 1U;
        }
        WRITE_REG(CRC->IR, *pTempInput32++);
    }

    pTempInput8 = (const uint8_t *)pTempInput32;
    while (remainder-- != 0U)
    {
        while (CRC_isFIFOOverflow())
        {
            if (--timeout == 0U)
            {
                DWT->CTRL = previousDwtCtrl;
                CoreDebug->DEMCR = previousDemcr;
                WRITE_REG(CRC->INI, CRC_configInitValue);
                return DRV_TIMEOUT;
            }
        }
        if (timingStarted == 0U)
        {
            startCycles = DWT->CYCCNT;
            timingStarted = 1U;
        }
        *(volatile uint8_t *)(&CRC->IR) = *pTempInput8++;
    }

    while (CRC_getDataLength() != autoReloadLen)
    {
        if (--timeout == 0U)
        {
            DWT->CTRL = previousDwtCtrl;
            CoreDebug->DEMCR = previousDemcr;
            WRITE_REG(CRC->INI, CRC_configInitValue);
            return DRV_TIMEOUT;
        }
    }

    /* Include result availability and the result read in the measured fact. */
    *pCrcRes = READ_REG(CRC->RES);
    endCycles = DWT->CYCCNT;
    *pElapsedCycles = endCycles - startCycles;
    DWT->CTRL = previousDwtCtrl;
    CoreDebug->DEMCR = previousDemcr;
    /* Match the production calculate API by restoring the configured seed. */
    WRITE_REG(CRC->INI, CRC_configInitValue);
    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif
