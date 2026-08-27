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

#ifndef __ET6x_CRC_H
#define __ET6x_CRC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup CRC
 * @{
 */

/* CRC interrupt status masks */
//*****************************************************************************
//
// Interrupt flags for use with CRC_enableInterrupt(), CRC_disableInterrupt(),
// CRC_clearInterrupt() & CRC_getInterruptStatusAll() functions.
//
//*****************************************************************************
#define CRC_INT_BUS_ERR       CRC_INT_EN_CRC_BEF_INT_EN_Msk    //!< Bus error Interrupt
#define CRC_INT_LENGTH_ERR    CRC_INT_EN_CRC_LEF_INT_EN_Msk    //!< length error Interrupt
#define CRC_INT_CHECK_ERR     CRC_INT_EN_CRC_CMF_INT_EN_Msk    //!< crc check result error Interrupt

/* the maximum of FIFO threshold */
#define CRC_FIFO_TRHD_MAX     8U

/**
 * @brief CRC kernel select
 *
 */
typedef enum
{
    CRC_MODE_CRC32,
    CRC_MODE_CRC16,
    CRC_MODE_CRC8
} CRC_WorkMode;

/**
 * @brief CRC result XOR type
 *
 */
typedef enum
{
    ALL_ZERO,
    ALL_ONE
} CRC_XOROut;

/**
 * @brief CRC configuration structure
 *
 */
typedef struct __PACKED
{
    CRC_WorkMode  mode;
    ControlStatus refIn;
    ControlStatus refOut;
    CRC_XOROut    xorOut;
    ControlStatus autoLengthReloadEn;
    ControlStatus byteswapEn;
    ControlStatus resultCheckEn;
    uint32_t      polynomial;
    /**< fifo threshold value set, default value is 8, maximin value is 8 */
    uint8_t       fifoThreshold;
    uint32_t      initialValue;
} CRC_ConfigParams;

void CRC_enableModule(void);
void CRC_disableModule(void);
void CRC_config(CRC_ConfigParams *config);
DRV_Status CRC_calculate32(uint32_t *pInputData, uint32_t crcNum, uint32_t *pCrcRes, uint32_t timeout);
DRV_Status CRC_calculate16(uint16_t *pInputData, uint32_t crcNum, uint16_t *pCrcRes, uint32_t timeout);
DRV_Status CRC_calculate8(uint8_t *pInputData, uint32_t crcNum, uint8_t *pCrcRes, uint32_t timeout);
void CRC_setDataLength(uint32_t length);
uint32_t CRC_getDataLength(void);
uint32_t CRC_getResult(void);
void CRC_setCheckValue(uint32_t value);
bool CRC_isFIFOOverflow(void);
void CRC_enableInterrupt(uint32_t ITmasks);
void CRC_disableInterrupt(uint32_t ITmasks);
void CRC_clearInterrupt(uint32_t ITmasks);
void CRC_forceInterrupt(uint32_t ITmasks);
uint32_t CRC_getInterruptStatusRawAll(void);
uint32_t CRC_getInterruptStatusAll(void);
void CRC_setInterruptMask(uint32_t ITmasks);
void CRC_clearInterruptMask(uint32_t ITmasks);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Write one 8-bit item to the CRC input register.
 * @param value Input item written with one byte access.
 * @return DRV_OK after the write is issued.
 */
DRV_Status CRC_testWriteInput8(uint8_t value);

/**
 * @brief Write one 16-bit item to the CRC input register.
 * @param value Input item written with one half-word access.
 * @return DRV_OK after the write is issued.
 */
DRV_Status CRC_testWriteInput16(uint16_t value);

/**
 * @brief Write one 32-bit item to the CRC input register.
 * @param value Input item written with one word access.
 * @return DRV_OK after the write is issued.
 */
DRV_Status CRC_testWriteInput32(uint32_t value);

/**
 * @brief Write a bounded 32-bit input burst and return observation facts.
 * @param pValues Pointer to the input words
 * @param count Number of words, from 1 to 9
 * @param checkpointCount Number of completed writes before checkpoint read;
 *        zero reads the initial result before the first write
 * @param pCheckpointResult Pointer used to return the checkpoint result
 * @param pFinalResult Pointer used to return the result after all writes
 * @param pOverflow Pointer used to return the FIFO overflow state
 * @return DRV_OK on success or DRV_PARAM_ERR for invalid arguments.
 * @note The writes execute without protocol gaps so FIFO timing Features can
 *       be observed. This function returns facts and does not judge them.
 */
DRV_Status CRC_testWriteInput32Burst(
    const uint32_t *pValues,
    uint32_t count,
    uint32_t checkpointCount,
    uint32_t *pCheckpointResult,
    uint32_t *pFinalResult,
    uint32_t *pOverflow);

/**
 * @brief Calculate CRC32 and return target-local DWT cycle evidence.
 * @param pInputData Pointer to the input byte range, aligned to 32 bits
 * @param lengthBytes Number of input bytes
 * @param timeout Timeout budget used by the bounded hardware polling loop
 * @param pCrcRes Pointer used to return the CRC result
 * @param pElapsedCycles Pointer used to return elapsed target cycles
 * @return DRV_OK on success, DRV_PARAM_ERR for invalid arguments,
 *         DRV_ERROR when CRC32 or DWT cycle counting is unavailable, and
 *         DRV_TIMEOUT when the bounded hardware wait expires.
 * @note The measured interval begins immediately before the first CRC input
 *       write and ends immediately after reading the result register.
 */
DRV_Status CRC_testCalculate32Timed(
    const uint32_t *pInputData,
    uint32_t lengthBytes,
    uint32_t timeout,
    uint32_t *pCrcRes,
    uint32_t *pElapsedCycles);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /* __ET6x_CRC_H */
