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
#include "et6x_aes.h"

#include <string.h>


static DRV_Status AES_pollStatusWithTimeout(uint32_t reg, uint32_t mask_bit, uint32_t timeout)
{
    uint32_t val = 0;

    for ( ; ;)
    {
        val = READ_REG(REG32(reg));
        if (val & mask_bit)
        {
            break;
        }
        if (--timeout <= 0)
        {
            val = READ_REG(REG32(reg));
            break;
        }
    }
    return (val & mask_bit)  ? DRV_OK : DRV_TIMEOUT;
}

/**
 * @brief
 *
 */
void AES_enableModule(void)
{
    SET_BIT(AES->WORK, AES_WORK_EN_Msk);
}

/**
 * @brief
 *
 */
void AES_disableModule(void)
{
    CLEAR_BIT(AES->WORK, AES_WORK_EN_Msk);
    AES_clearStatus(AES_STS_DATA_IN_REQ | AES_STS_DATA_OUT_REQ | AES_STS_COMPLETE);
}

/**
 * @brief
 *
 * @return true
 * @return false
 */
bool AES_isBusy(void)
{
    return (READ_REG(AES->RPT_AES_WORK) & AES_RPT_AES_WORK_BUSY_Msk) == AES_RPT_AES_WORK_BUSY_Msk;
}

/**
 * @brief
 *
 * @return uint8_t
 */
uint8_t AES_getStatus(void)
{
    return(READ_REG(AES->RPT_AES_STS) & 0x07);
}

/**
 * @brief
 *
 * @param stsFlags
 */
void AES_clearStatus(uint8_t stsFlags)
{
    WRITE_REG(AES->RPT_AES_STS, stsFlags);
}

/**
 * @brief
 *
 * @param length
 * @attention This function must be called before the AES_configureModule call
 */
void AES_setDataLength(uint64_t length)
{
    WRITE_REG(AES->DATA_SIZE0, (uint32_t)length);
    WRITE_REG(AES->DATA_SIZE1, (uint32_t)(length >> 32));
}

/**
 * @brief
 *
 * @return uint64_t
 */
uint64_t AES_getDataLength(void)
{
    return (uint64_t)READ_REG(AES->DATA_SIZE0) | ((uint64_t)READ_REG(AES->DATA_SIZE1) << 32);
}

/**
 * @brief
 *
 * @param key
 * @param keySize
 * @attention This function must be called after the AES_configureModule call
 */
void AES_setKey(const uint32_t key[], AES_KeySize keySize)
{
    WRITE_REG(AES->WORK_KEY0, (key[0U]));
    WRITE_REG(AES->WORK_KEY1, (key[1U]));
    WRITE_REG(AES->WORK_KEY2, (key[2U]));
    WRITE_REG(AES->WORK_KEY3, (key[3U]));
    if (keySize != AES_KEY_SIZE_128BIT)
    {
        WRITE_REG(AES->WORK_KEY4, (key[4U]));
        WRITE_REG(AES->WORK_KEY5, (key[5U]));
        WRITE_REG(AES->WORK_KEY6, (key[6U]));
        WRITE_REG(AES->WORK_KEY7, (key[7U]));
    }
}

/**
 * @brief
 *
 * @param iv
 * @attention This function must be called after the AES_configureModule call
 */
void AES_setInitializationVector(const uint32_t iv[])
{
    WRITE_REG(AES->WORK_IV0, (iv[0U]));
    WRITE_REG(AES->WORK_IV1, (iv[1U]));
    WRITE_REG(AES->WORK_IV2, (iv[2U]));
    WRITE_REG(AES->WORK_IV3, (iv[3U]));
}

/**
 * @brief
 *
 * @param iv
 */
void AES_readInitializationVector(uint32_t iv[])
{
    iv[0U] = (READ_REG(AES->WORK_IV0));
    iv[1U] = (READ_REG(AES->WORK_IV1));
    iv[2U] = (READ_REG(AES->WORK_IV2));
    iv[3U] = (READ_REG(AES->WORK_IV3));
}

/**
 * @brief
 *
 * @param config
 */
void AES_configureModule(const AES_ConfigParams *config)
{
    uint32_t regVal;

    regVal = ((uint32_t)config->endianSel << AES_CRTL_ENDIAN_SEL_Pos) |
             ((uint32_t)config->FIFOModeEn << AES_CRTL_DMA_MODE_Pos) |
             ((uint32_t)config->paddingMode << AES_CRTL_PADDING_Pos) |
             ((uint32_t)config->direction << AES_CRTL_DIRECTION_Pos) |
             ((uint32_t)config->keySize << AES_CRTL_KEY_SIZE_Pos);
    MODIFY_REG(AES->CRTL, AES_CRTL_ENDIAN_SEL_Msk | AES_CRTL_DMA_MODE_Msk | AES_CRTL_KEY_SIZE_Msk |
               AES_CRTL_DIRECTION_Msk | AES_CRTL_PADDING_Msk, regVal);

    WRITE_REG(AES->WORK_MODE, config->opMode);

    if (config->opMode == AES_OPMODE_CTR)
    {
        WRITE_REG(AES->BLOCK_CNT, config->ctrCount);
    }
}

/**
 * @brief
 *
 * @param destArray
 * @param timeOut
 * @return bool
 */
bool AES_readDataBlocking(uint32_t destArray[], uint32_t timeOut)
{
    if (DRV_TIMEOUT == AES_pollStatusWithTimeout((uint32_t)(&AES->RPT_AES_STS), AES_STS_DATA_OUT_REQ, timeOut))
    {
        return false;
    }
    AES_clearStatus(AES_STS_DATA_OUT_REQ);
    destArray[0] = (READ_REG(AES->RESULT_DOUT0));
    destArray[1] = (READ_REG(AES->RESULT_DOUT1));
    destArray[2] = (READ_REG(AES->RESULT_DOUT2));
    destArray[3] = (READ_REG(AES->RESULT_DOUT3));
    return true;
}

/**
 * @brief
 *
 * @param srcArray
 * @param timeOut
 * @return bool
 */
bool AES_writeDataBlocking(const uint32_t srcArray[], uint32_t timeOut)
{
    if (DRV_TIMEOUT == AES_pollStatusWithTimeout((uint32_t)(&AES->RPT_AES_STS), AES_STS_DATA_IN_REQ, timeOut))
    {
        return false;
    }
    AES_clearStatus(AES_STS_DATA_IN_REQ);
    WRITE_REG(AES->DIN0, (srcArray[0]));
    WRITE_REG(AES->DIN1, (srcArray[1]));
    WRITE_REG(AES->DIN2, (srcArray[2]));
    WRITE_REG(AES->DIN3, (srcArray[3]));
    return true;
}

/**
 * @brief
 *
 * @param destArray
 * @param timeOut
 * @return bool
 */
bool AES_readDataNonBlocking(uint32_t destArray[])
{
    if (DRV_TIMEOUT == AES_pollStatusWithTimeout((uint32_t)(&AES->RPT_AES_STS), AES_STS_DATA_OUT_REQ, 1))
    {
        return false;
    }
    AES_clearStatus(AES_STS_DATA_OUT_REQ);
    destArray[0] = (READ_REG(AES->RESULT_DOUT0));
    destArray[1] = (READ_REG(AES->RESULT_DOUT1));
    destArray[2] = (READ_REG(AES->RESULT_DOUT2));
    destArray[3] = (READ_REG(AES->RESULT_DOUT3));
    return true;
}

/**
 * @brief
 *
 * @param srcArray
 * @param timeOut
 * @return bool
 */
bool AES_writeDataNonBlocking(const uint32_t srcArray[])
{
    if (DRV_TIMEOUT == AES_pollStatusWithTimeout((uint32_t)(&AES->RPT_AES_STS), AES_STS_DATA_IN_REQ, 1))
    {
        return false;
    }
    AES_clearStatus(AES_STS_DATA_IN_REQ);
    WRITE_REG(AES->DIN0, (srcArray[0]));
    WRITE_REG(AES->DIN1, (srcArray[1]));
    WRITE_REG(AES->DIN2, (srcArray[2]));
    WRITE_REG(AES->DIN3, (srcArray[3]));
    return true;
}

/**
 * @brief
 *
 * @param srcArray
 * @param destArray
 * @param dataLength
 * @param timeOut
 * @return bool
 * @attention  for AES encryption, padding is force to added in output buffer.
 *             The output buffer is 16 bytes larger than the input buffer
 */
bool AES_processData(const uint32_t srcArray[], uint32_t destArray[], uint64_t dataLength,
                     uint32_t timeOut)
{
    bool     status = false;
    uint32_t count  = 0;

    for (count = 0U; count < ((dataLength + 15U) / 16U); count++)
    {
        status = AES_writeDataBlocking(srcArray + (count * 4U), timeOut);
        if (!status)
        {
            break;
        }
        status = AES_readDataBlocking(destArray + (count * 4U), timeOut);
        if (!status)
        {
            break;
        }
    }
    /* check for encryption padding block read in  ECB and CBC mdoe */
    if ((READ_BIT(AES->CRTL, AES_CRTL_DIRECTION_Msk) == AES_DIRECTION_ENCRYPTION) &&
        (READ_BIT(AES->CRTL, AES_CRTL_PADDING_Msk) != 0) &&
        (READ_BIT(AES->WORK_MODE, AES_WORK_MODE_MODE_Msk) != AES_OPMODE_CTR))
    {
        status = AES_readDataBlocking(destArray + (count * 4U), timeOut);
        AES_clearStatus(AES_STS_COMPLETE);
    }
    return status;
}

/**
 * @brief
 *
 * @param intFlags
 */
void AES_enableInterrupt(uint32_t intFlags)
{
    SET_BIT(AES->INT_EN, intFlags);
}

/**
 * @brief
 *
 * @param intFlags
 */
void AES_disableInterrupt(uint32_t intFlags)
{
    CLEAR_BIT(AES->INT_EN, intFlags);
}

/**
 * @brief
 *
 * @param intFlags
 */
void AES_setInterruptMask(uint32_t intFlags)
{
    SET_BIT(AES->INT_MASK, intFlags);
}

/**
 * @brief
 *
 * @param intFlags
 */
void AES_clearInterruptMask(uint32_t intFlags)
{
    CLEAR_BIT(AES->INT_MASK, intFlags);
}

/**
 * @brief force AES interrupt
 *
 * @param ITmasks: AES interrupt masks
 */
void AES_forceInterrupt(uint32_t ITmasks)
{
    SET_BIT(AES->INT_FORCE_IND, ITmasks);
}

/**
 * @brief
 *
 * @param intFlags
 * @return true
 * @return false
 */
bool AES_getInterruptStatus(uint32_t intFlags)
{
    return(READ_BIT(AES->RPT_AES_INT_STATUS, intFlags) == intFlags);
}

/**
 * @brief
 *
 * @return uint32_t
 */
uint32_t AES_getAllInterruptStatus(void)
{
    return(READ_REG(AES->RPT_AES_INT_STATUS));
}

/**
 * @brief
 *
 * @param intFlags
 * @return true
 * @return false
 */
bool AES_getInterruptStatusRaw(uint32_t intFlags)
{
    return(READ_BIT(AES->RPT_AES_INT_RAW, intFlags) == intFlags);
}

/**
 * @brief Clear AES module interrupt flag
 *
 * @param intFlags
 */
void AES_clearInterruptStatus(uint32_t intFlags)
{
    SET_BIT(AES->INT_CLR, intFlags);
}

/**
 * @brief
 *
 * @param reqFlags
 */
void AES_enableDMARequest(uint32_t reqFlags)
{
    SET_BIT(AES->DMA, reqFlags);
}

/**
 * @brief
 *
 * @param reqFlags
 */
void AES_disableDMARequest(uint32_t reqFlags)
{
    CLEAR_BIT(AES->DMA, reqFlags);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* Keep timing instrumentation isolated from the production Driver API. */
DRV_Status AES_testProcessBlocksTimed(
    const uint32_t *srcArray,
    uint32_t *destArray,
    uint32_t blockCount,
    uint32_t timeout,
    uint32_t *elapsedCycles)
{
    uint32_t index;
    uint32_t startCycles;
    uint32_t previousDemcr;
    uint32_t previousDwtCtrl;

    if ((srcArray == NULL) || (destArray == NULL) ||
        (blockCount == 0U) || (blockCount > 257U) ||
        (timeout == 0U) || (elapsedCycles == NULL))
    {
        return DRV_PARAM_ERR;
    }
    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0U)
    {
        return DRV_ERROR;
    }

    previousDemcr = CoreDebug->DEMCR;
    previousDwtCtrl = DWT->CTRL;
    CoreDebug->DEMCR = previousDemcr | CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL = previousDwtCtrl | DWT_CTRL_CYCCNTENA_Msk;
    startCycles = DWT->CYCCNT;
    for (index = 0U; index < blockCount; ++index)
    {
        if (!AES_writeDataBlocking(&srcArray[index * 4U], timeout) ||
            !AES_readDataBlocking(&destArray[index * 4U], timeout))
        {
            DWT->CTRL = previousDwtCtrl;
            CoreDebug->DEMCR = previousDemcr;
            return DRV_TIMEOUT;
        }
    }
    *elapsedCycles = DWT->CYCCNT - startCycles;
    DWT->CTRL = previousDwtCtrl;
    CoreDebug->DEMCR = previousDemcr;
    return DRV_OK;
}

DRV_Status AES_testGetInterruptSnapshot(
    uint32_t *rawStatus,
    uint32_t *effectiveStatus)
{
    if ((rawStatus == NULL) || (effectiveStatus == NULL))
    {
        return DRV_PARAM_ERR;
    }
    *rawStatus = READ_REG(AES->RPT_AES_INT_RAW);
    *effectiveStatus = READ_REG(AES->RPT_AES_INT_STATUS);
    return DRV_OK;
}

DRV_Status AES_testWriteInputBlock(const uint32_t srcArray[4])
{
    if (srcArray == NULL)
    {
        return DRV_PARAM_ERR;
    }

    WRITE_REG(AES->DIN0, srcArray[0]);
    WRITE_REG(AES->DIN1, srcArray[1]);
    WRITE_REG(AES->DIN2, srcArray[2]);
    WRITE_REG(AES->DIN3, srcArray[3]);
    return DRV_OK;
}

DRV_Status AES_testWriteInputBlockPair(
    const uint32_t firstArray[4],
    const uint32_t secondArray[4],
    uint32_t timeout)
{
    if ((firstArray == NULL) || (secondArray == NULL) || (timeout == 0U))
    {
        return DRV_PARAM_ERR;
    }

    /*
     * Accept both blocks through the documented input handshake, but do not
     * consume the first output before the second block is accepted. This is
     * the sequence used by the ET6801 historical functional test to create
     * the OUTPUT_CONFLICT condition. A raw second write can happen before the
     * first result becomes pending and therefore is not a valid stimulus.
     */
    if (!AES_writeDataBlocking(firstArray, timeout))
    {
        return DRV_TIMEOUT;
    }

    if (!AES_writeDataBlocking(secondArray, timeout))
    {
        return DRV_TIMEOUT;
    }

    return DRV_OK;
}

DRV_Status AES_testWriteInputBlockThenDisable(
    const uint32_t srcArray[4],
    uint32_t timeout)
{
    if ((srcArray == NULL) || (timeout == 0U))
    {
        return DRV_PARAM_ERR;
    }

    /*
     * Complete the input handshake before disabling so the peripheral is
     * known to have started work; a raw register write alone is too early and
     * does not deterministically create INCOMPLETE_DISABLE.
     */
    if (!AES_writeDataBlocking(srcArray, timeout))
    {
        return DRV_TIMEOUT;
    }

    AES_disableModule();

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif
