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

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __ET6X_SPI_H
#define __ET6X_SPI_H

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup SPI
 * @{
 */

/* Includes ------------------------------------------------------------------*/
#include "et6x.h"

/* SVD BAUDR stores an even divisor in bits [15:1]. */
#define SPI_CLOCK_DIVIDER_MIN       (1UL << SPI0_BAUDR_SCKDV_Pos)
#define SPI_CLOCK_DIVIDER_MAX       SPI0_BAUDR_SCKDV_Msk
/* Existing SDK hardware limits, shared by validation and runtime capabilities. */
/* ET6801 FPGA: 32 entries confirmed by TXFLR/SR at full on 2026-09-04.
 * FIFO capacity is independent of the SVD's four-bit threshold fields. */
#define SPI_MAX_FIFO_DEPTH          32U
#define SPI_MIN_FRAME_BITS          4U
#define SPI_MAX_FRAME_BITS          (SPI0_CTRLR0_DFS_Msk + 1U)

#define SPI_INTERRUPT_ALL \
        (SPI0_IMR_TXEIM_Msk | SPI0_IMR_TXOIM_Msk | SPI0_IMR_RXUIM_Msk | SPI0_IMR_RXOIM_Msk | \
         SPI0_IMR_RXFIM_Msk | SPI0_IMR_MSTIM_Msk)

/**
 * @brief SPI transfer protocol
 */
typedef enum
{
    SPI_PROT_POL0PHA0 = 0x0000U,
    SPI_PROT_POL0PHA1 = 0x0001U,
    SPI_PROT_POL1PHA0 = 0x0002U,
    SPI_PROT_POL1PHA1 = 0x0003U
} SPI_TransferProtocol;

/**
 * @brief SPI operating mode
 */
typedef enum
{
    SPI_SLAVE_MODE  = 0,
    SPI_MASTER_MODE = 1
} SPI_Mode;

/**
 * @brief SPI transfer mode
 */
typedef enum
{
    SPI_TRANSMIT_RECEIVE = 0x0,     /* NotApplicable in enhanced SPI operating mode */
    SPI_TRANSMIT         = 0x1,
    SPI_RECEIVE          = 0x2,
    SPI_EEPROM_READ      = 0x3      /* NotApplicable in enhanced SPI operating mode */
} SPI_TransferMode;

typedef struct __PACKED
{
    uint8_t              charLength;
    SPI_TransferProtocol protocol;
    SPI_Mode             workMode;
    SPI_TransferMode     transferMode;
    ControlStatus        slaveOutputEn;
    ControlStatus        CSToggleEn;
    uint32_t             bitRate;
    uint16_t             rxDataNum;
    uint32_t             rxSampleDly;
} SPI_Config;

/**
 * @brief SPI data endianess
 */
typedef enum
{
    SPI_DATA_LITTLE_ENDIAN = 0U,
    SPI_DATA_BIG_ENDIAN    = 1U
} SPI_endianess;


#define SPI_transmitByte(SPIx, txData)                                         \
        SPI_pollingNonFIFOTransaction(SPIx, 8U, txData)

#define SPI_transmit16Bits(SPIx, txData)                                       \
        SPI_pollingNonFIFOTransaction(SPIx, 16U, txData)

#define SPI_transmitNBytes(SPIx, txBuffer, numOfWords)                \
        SPI_pollingFIFOTransaction(SPIx, 8U, txBuffer, NULL, numOfWords)

#define SPI_transmitN16BitWord(SPIx, txBuffer, numOfWords)            \
        SPI_pollingFIFOTransaction(SPIx, 16U, txBuffer, NULL, numOfWords)

#define SPI_transmitNWordsWithCharLength(SPIx, charLength, txBuffer,           \
                                         numOfWords)                  \
        SPI_pollingFIFOTransaction(SPIx, charLength, txBuffer, NULL,     \
                                   numOfWords)

#define SPI_receiveByte(SPIx, dummyData)                                       \
        SPI_pollingNonFIFOTransaction(SPIx, 8U, dummyData)

#define SPI_receiveNBytes(SPIx, rxBuffer, numOfWords)                 \
        SPI_pollingFIFOTransaction(SPIx, 8U, NULL, rxBuffer, numOfWords)

#define SPI_receiveN16BitWord(SPIx, rxBuffer, numOfWords)             \
        SPI_pollingFIFOTransaction(SPIx, 16U, NULL, rxBuffer, numOfWords)

#define SPI_receiveNWordsWithcharLength(SPIx, charLength, rxBuffer,            \
                                        numOfWords)                   \
        SPI_pollingFIFOTransaction(SPIx, charLength, NULL, rxBuffer,       \
                                   numOfWords)
/* basic configure */
void SPI_initStruct(SPI_Config *cfg);
void SPI_setConfig(SPI_Type *SPIx, SPI_Config *config);
void SPI_configFrameNum(SPI_Type *SPIx, uint16_t num);
void SPI_configTransMode(SPI_Type *SPIx, SPI_TransferMode mode);
void SPI_setcharLength(SPI_Type *SPIx, uint16_t charLength);
void SPI_setCSLow(SPI_Type *SPIx);
void SPI_setCSHigh(SPI_Type *SPIx);
void SPI_setBaudRate(SPI_Type *SPIx, uint32_t bitRate);
bool SPI_isBusy(SPI_Type *SPIx);
void SPI_enableLoopback(SPI_Type *SPIx);
void SPI_disableLoopback(SPI_Type *SPIx);
void SPI_enableModule(SPI_Type *SPIx);
void SPI_disableModule(SPI_Type *SPIx);

/* write/read */
void SPI_writeDataNonBlocking(SPI_Type *SPIx, uint16_t data);
uint16_t SPI_readDataNonBlocking(SPI_Type *SPIx);
void SPI_writeDataBlockingFIFO(SPI_Type *SPIx, uint16_t data);
uint16_t SPI_readDataBlockingFIFO(SPI_Type *SPIx);
void SPI_writeDataBlockingNonFIFO(SPI_Type *SPIx, uint16_t data);
uint16_t SPI_readDataBlockingNonFIFO(SPI_Type *SPIx);
void SPI_transmit24Bits(SPI_Type *SPIx, uint32_t data);
void SPI_transmit32Bits(SPI_Type *SPIx, uint32_t data);
uint16_t SPI_receive16Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData);
uint32_t SPI_receive24Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData);
uint32_t SPI_receive32Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData);
uint16_t SPI_pollingNonFIFOTransaction(SPI_Type *SPIx, uint16_t charLength, uint16_t data);
void SPI_pollingFIFOTransaction(SPI_Type *SPIx, uint16_t charLength, void *pTxBuffer, void *pRxBuffer,
                                uint16_t numOfWords);

/* fifo */
void SPI_resetFIFO(SPI_Type *SPIx);
void SPI_setTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t startLevel);
void SPI_getTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t *txLevel);
void SPI_setFIFOInterruptLevel(SPI_Type *SPIx, uint8_t txLevel, uint8_t rxLevel);
void SPI_getFIFOInterruptLevel(SPI_Type *SPIx, uint8_t *txLevel, uint8_t *rxLevel);
uint8_t SPI_getTxFIFOStatus(SPI_Type *SPIx);
uint8_t SPI_getRxFIFOStatus(SPI_Type *SPIx);

/* interrupt */
void SPI_enableInterrupt(SPI_Type *SPIx, uint32_t intFlags);
void SPI_disableInterrupt(SPI_Type *SPIx, uint32_t intFlags);
uint32_t SPI_getInterruptStatus(SPI_Type *SPIx);
void SPI_clearInterruptStatus(SPI_Type *SPIx, uint32_t intFlags);

/* DMA */
void SPI_setDMATransmitDataLevel(SPI_Type *SPIx, uint8_t level);
void SPI_setDMARecevieDataLevel(SPI_Type *SPIx, uint8_t level);
void SPI_enableDMA(SPI_Type *SPIx);
void SPI_disableDMA(SPI_Type *SPIx);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/
/* SVD BAUDR is an even divider; CTRLR1 stores frame count minus one. */
#define SPI_TEST_FRAME_COUNT_MAX   (SPI0_CTRLR1_NDF_Msk + 1UL)

/* Driver FRF encodings, not Wire values. TI/Microwire protocol qualification is pending. */
typedef enum
{
    SPI_TEST_FORMAT_MOTOROLA = 0U,
    SPI_TEST_FORMAT_TI = 1U,
    SPI_TEST_FORMAT_MICROWIRE = 2U
} SPI_TestFormat;

typedef enum
{
    SPI_TEST_CS_AUTO = 0U,
    SPI_TEST_CS_HOLD = 1U,
    SPI_TEST_CS_TOGGLE = 2U,
    SPI_TEST_CS_UNKNOWN = UINT32_MAX
} SPI_TestCSPolicy;

/* Exact settings: count is a number of frames; outputEnabled is not SLV_OE. */
typedef struct
{
    uint32_t role;
    uint32_t format;
    uint32_t clockMode;
    uint32_t transferMode;
    uint32_t frameBits;
    uint32_t frameCount;
    uint32_t divider;
    uint32_t csPolicy;
    uint32_t outputEnabled;
    uint32_t loopback;
    uint32_t rxDelay;
    uint32_t controlBits;
    uint32_t sequential;
    uint32_t transmit;
    uint32_t handshake;
} SPI_TestConfig;

DRV_Status SPI_testConfigureStopped(SPI_Type *SPIx, const SPI_TestConfig *config);
DRV_Status SPI_testGetConfig(SPI_Type *SPIx, SPI_TestConfig *config);
DRV_Status SPI_testSetLoopbackStopped(SPI_Type *SPIx, uint8_t enabled);
DRV_Status SPI_testSetFIFOThresholds(SPI_Type *SPIx, uint8_t tx, uint8_t rx, uint8_t start);
DRV_Status SPI_testGetDMAEndpoint(SPI_Type *SPIx, uintptr_t *address);

/* Raw readback for the chip adapter. Reading this view never consumes SR/DR/ICR. */
typedef struct
{
    uint32_t control;
    uint32_t frame_count;
    uint32_t enabled;
    uint32_t selected;
    uint32_t divider;
    uint32_t rx_sample_delay;
    uint32_t tx_level;
    uint32_t rx_level;
    uint32_t tx_thresholds;
    uint32_t rx_threshold;
    uint32_t irq_raw;
    uint32_t irq_status;
    uint32_t irq_enabled;
    uint32_t dma_enabled;
    uint32_t dma_tx_threshold;
    uint32_t dma_rx_threshold;
} SPI_TestSnapshot;

/* Configuration-only actions reject an enabled module instead of clearing FIFO. */
DRV_Status SPI_testSetDivider(SPI_Type *SPIx, uint32_t divider);
DRV_Status SPI_testSetFrameCount(SPI_Type *SPIx, uint32_t frameCount);
DRV_Status SPI_testSelectCS(SPI_Type *SPIx, uint8_t selected);
DRV_Status SPI_testConfigureDMA(SPI_Type *SPIx, uint8_t txEnabled, uint8_t rxEnabled,
                               uint8_t txLevel, uint8_t rxLevel);
DRV_Status SPI_testGetSnapshot(SPI_Type *SPIx, SPI_TestSnapshot *snapshot);
/* Explicit SR read: consumes TXE/DCOL read-clear flags. */
DRV_Status SPI_testReadStatus(SPI_Type *SPIx, uint32_t *status);
/* Normal FIFO actions return 0/1 transferred frame; no wait and no SR read. */
DRV_Status SPI_testTryWriteFrame(SPI_Type *SPIx, uint32_t frame, uint8_t *written);
DRV_Status SPI_testTryReadFrame(SPI_Type *SPIx, uint32_t *frame, uint8_t *received);
/* No FIFO guard: intentionally produce overflow/underflow stimuli. */
DRV_Status SPI_testWriteFIFOOnce(SPI_Type *SPIx, uint32_t frame);
DRV_Status SPI_testReadFIFOOnce(SPI_Type *SPIx, uint32_t *frame);
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

#endif /* __ET6X_SPI_H */
