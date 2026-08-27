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
#ifndef __ET6X_AES_H__
#define __ET6X_AES_H__

#ifdef __cplusplus
extern "C" {
#endif


#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/**
 * @addtogroup  AES
 * @{
 */

//*****************************************************************************
//
// Interrupt flags for use with AES_enableInterrupt(), AES_disableInterrupt(),
// AES_clearInterruptStatus() & AES_getInterruptStatus() functions.
//
//*****************************************************************************
#define AES_INT_OUTPUT_CONFLICT       0x00000001U    //!< Data in register not read away, new encryption process start
#define AES_INT_KEY_MISSING           0x00000002U    //!< Key parameter missing
#define AES_INT_IV_MISSING            0x00000004U    //!< IV parameter missing
#define AES_INT_COMPLETE              0x00000008U    //!< Encryption/decryption process complete
#define AES_INT_INCOMPLETE_DISABLE    0x00000010U    //!< Disable AES when It's still Working
#define AES_INT_DATA_IN_REQ           0x00000020U    //!< Request for data in
#define AES_INT_DATA_OUT_REQ          0x00000040U    //!< Request for data out

//*****************************************************************************
//
// Defines that can be used for enabling and disabling DMA requests in the
// AES_enableDMARequest() and AES_disableDMARequest() functions.
//
//*****************************************************************************
#define AES_DMA_EN_DATA_IN     0x00000001U   //!<Enable DMA for data i/p request
#define AES_DMA_EN_DATA_OUT    0x00000002U   //!<Enable DMA for data o/p request

//*****************************************************************************
//
// Status flags for use with AES_getStatus() and AES_clearStatus() functions.
// used in block poll mode
//
//*****************************************************************************
#define AES_STS_COMPLETE        0x00000001U   //!< Request for data in
#define AES_STS_DATA_IN_REQ     0x00000002U   //!< Request for data out
#define AES_STS_DATA_OUT_REQ    0x00000004U   //!< Report Encryption/decryption process complete


typedef enum
{
    AES_KEY_SIZE_128BIT,      //!< Select 128-bit key
    AES_KEY_SIZE_256BIT       //!< Select 256-bit key
} AES_KeySize;

typedef enum
{
    AES_DIRECTION_ENCRYPTION,
    AES_DIRECTION_DECRYPTION
} AES_Direction;

typedef enum
{
    AES_NO_PADDING,             //!< no padding mode
    AES_PADDING_ZERO,           //!< zero padding mode
    AES_PADDING_PKCS7           //!< pkcs#7 padding mode
} AES_PaddingMode;

typedef enum
{
    AES_OPMODE_ECB,         //!< Select ECB mode
    AES_OPMODE_CBC,         //!< Select CBC mode
    AES_OPMODE_CTR          //!< Select CTR mode
} AES_OpMode;

typedef enum
{
    AES_ENDIAN_SMALL,
    AES_ENDIAN_BIG
} AES_EndianSel;


typedef struct
{
    AES_KeySize     keySize;
    AES_Direction   direction;
    AES_PaddingMode paddingMode;
    AES_OpMode      opMode;
    uint32_t        ctrCount;
    ControlStatus   FIFOModeEn;
    AES_EndianSel   endianSel;
} AES_ConfigParams;

void AES_enableModule(void);
void AES_disableModule(void);
bool AES_isBusy(void);
uint8_t AES_getStatus(void);
void AES_clearStatus(uint8_t stsFlags);

void AES_setDataLength(uint64_t length);
uint64_t AES_getDataLength(void);
void AES_setKey(const uint32_t key[], AES_KeySize keySize);
void AES_setInitializationVector(const uint32_t iv[]);
void AES_readInitializationVector(uint32_t iv[]);
void AES_configureModule(const AES_ConfigParams *config);

bool AES_readDataBlocking(uint32_t destArray[], uint32_t timeOut);
bool AES_writeDataBlocking(const uint32_t srcArray[], uint32_t timeOut);
bool AES_processData(const uint32_t srcArray[], uint32_t destArray[], uint64_t dataLength, uint32_t timeOut);
bool AES_readDataNonBlocking(uint32_t destArray[]);
bool AES_writeDataNonBlocking(const uint32_t srcArray[]);

void AES_enableInterrupt(uint32_t intFlags);
void AES_disableInterrupt(uint32_t intFlags);
void AES_setInterruptMask(uint32_t intFlags);
void AES_forceInterrupt(uint32_t ITmasks);
void AES_clearInterruptMask(uint32_t intFlags);
bool AES_getInterruptStatus(uint32_t intFlags);
uint32_t AES_getAllInterruptStatus(void);
bool AES_getInterruptStatusRaw(uint32_t intFlags);
void AES_clearInterruptStatus(uint32_t intFlags);

void AES_enableDMARequest(uint32_t reqFlags);
void AES_disableDMARequest(uint32_t reqFlags);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * Execute a bounded number of complete AES blocks and return target-local
 * DWT cycles. The caller supplies staging buffers owned by the caller.
 * This extension reports facts only and does not interpret a test result.
 */
DRV_Status AES_testProcessBlocksTimed(
    const uint32_t *srcArray,
    uint32_t *destArray,
    uint32_t blockCount,
    uint32_t timeout,
    uint32_t *elapsedCycles);

/** Return raw and effective AES interrupt source snapshots without polling. */
DRV_Status AES_testGetInterruptSnapshot(
    uint32_t *rawStatus,
    uint32_t *effectiveStatus);

/**
 * Write one input register block without waiting for DATA_IN_REQ.
 * This is limited to negative tests that must deliberately violate the
 * normal input handshake to stimulate an AES hardware error source.
 */
DRV_Status AES_testWriteInputBlock(const uint32_t srcArray[4]);

/**
 * Accept two blocks through the normal input handshake without consuming the
 * first result before the second block. This provides the historical ET6801
 * stimulus for the AES output-conflict interrupt source.
 */
DRV_Status AES_testWriteInputBlockPair(
    const uint32_t firstArray[4],
    const uint32_t secondArray[4],
    uint32_t timeout);

/**
 * Accept one block through the normal input handshake and disable AES
 * immediately afterwards. This provides one deterministic stimulus for the
 * AES incomplete-disable interrupt source.
 */
DRV_Status AES_testWriteInputBlockThenDisable(
    const uint32_t srcArray[4],
    uint32_t timeout);

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

#endif // __ET6X_AES_H__
