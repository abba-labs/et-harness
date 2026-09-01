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
#ifndef __ET6X_QSPI_H
#define __ET6X_QSPI_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"
#include "et6x_spi.h"

/*! Maximum FIFO depth */
#define QSPI_MAX_FIFO_DEPTH    32U

/** @addtogroup ET6001_Driver
 * @{
 */

/* Transmit FIFO Empty Interrupt */
/* Transmit FIFO Empty Interrupt */
/* Receive FIFO Underflow Interrupt */
/* Receive FIFO Overflow Interrupt */
/* Receive FIFO Full Interrupt */
/* Receive FIFO Full Interrupt */
/* Transmit FIFO Underflow Interrupt */
/* Transmit Error Interrupt */
#define QSPI_INTERRUPT_ALL    \
        (QSPI_IMR_TXEIM_Msk | \
         QSPI_IMR_TXOIM_Msk | \
         QSPI_IMR_RXUIM_Msk | \
         QSPI_IMR_RXOIM_Msk | \
         QSPI_IMR_RXFIM_Msk | \
         QSPI_IMR_MSTIM_Msk | \
         QSPI_IMR_TXUIM_Msk | \
         QSPI_IMR_SPITEM_Msk)

/**
 * @brief choose QSPI transmit data in 1 line,2 lines or 4 lines
 *
 */
typedef enum
{
    STD_SPI_FRF  = 0x0,
    DUAL_SPI_FRF = 0x1,
    QUAD_SPI_FRF = 0x2
} QSPI_FRAME_FORMAT_TypeDef;

/**
 * @brief Dual/Quad mode instruction length in bits.
 *
 */
typedef enum
{
    INSTRCTION_0_BIT  = 0x0,
    INSTRCTION_4_BIT  = 0x1,
    INSTRCTION_8_BIT  = 0x2,
    INSTRCTION_16_BIT = 0x3,
} QSPI_INSTRUCTION_BITS_TypeDef;

/**
 * @brief bits of Address to be transmitted
 *
 */
typedef enum
{
    ADDR_0_BIT  = 0x0,
    ADDR_4_BIT  = 0x1,
    ADDR_8_BIT  = 0x2,
    ADDR_12_BIT = 0x3,
    ADDR_16_BIT = 0x4,
    ADDR_20_BIT = 0x5,
    ADDR_24_BIT = 0x6,
    ADDR_28_BIT = 0x7,
    ADDR_32_BIT = 0x8,
    ADDR_36_BIT = 0x9,
    ADDR_40_BIT = 0xa,
    ADDR_44_BIT = 0xb,
    ADDR_48_BIT = 0xc,
    ADDR_52_BIT = 0xd,
    ADDR_56_BIT = 0xe,
    ADDR_60_BIT = 0xf
} QSPI_ADDRESS_BITS_TypeDef;

/**
 * @brief QSPI state
 *
 */
typedef enum
{
    QSPI_BUSY              = 0x1 << QSPI_SR_BUSY_Pos,
    TRANSMIT_FIFO_NOT_FULL = 0x1 << QSPI_SR_TFNF_Pos,
    TRANSMIT_FIFO_EMPTY    = 0x1 << QSPI_SR_TFE_Pos,
    RECEIVE_FIFO_NOT_EMPTY = 0x1 << QSPI_SR_RFNE_Pos,
    RECEIVE_FIFO_FULL      = 0x1 << QSPI_SR_RFF_Pos,
    DATA_COLLISION_ERROR   = 0x1 << QSPI_SR_DCOL_Pos
} QSPI_STATE_TypeDef;

/**
 * @brief Selects whether DW_apb_ssi will transmit
 *        instruction/address either in Standard SPI mode or the SPI
 *        mode selected in CTRLR0.SPI_FRF field. 00 - Instruction
 *        and Address will be sent in Standard SPI
 *
 */
typedef enum
{
    INSTRCTION_STANDARD_ADDRESS_STANDARD = 0x0,
    INSTRCTION_STANDARD_ADDRESS_FRF      = 0x1,
    INSTRCTION_FRF_ADDRESS_FRF           = 0x2
} QSPI_INSTRCTION_ADDRESS_MODE_TypeDef;

/**
 * @brief
 *
 */
typedef enum
{
    DATA_FRAME_SIZE_8_BIT  = 0x7,
    DATA_FRAME_SIZE_16_BIT = 0xf,
    DATA_FRAME_SIZE_24_BIT = 0x17,
    DATA_FRAME_SIZE_32_BIT = 0x1f
} SPI_DATA_FRAMESIZE_TypeDef;

/**
 * @brief XIP Mode bits length
 *
 */
typedef enum
{
    XIP_MBL_2  = 0x0,
    XIP_MBL_4  = 0x1,
    XIP_MBL_8  = 0x2,
    XIP_MBL_16 = 0x3
} SPI_XIP_MBL_TypeDef;


/**
 * @brief  QSPI Configuration Structure definition
 */
typedef struct __PACKED
{
    QSPI_FRAME_FORMAT_TypeDef            qspiFrameFormat;         /* frame format */
    QSPI_INSTRUCTION_BITS_TypeDef        instructionLen;
    QSPI_ADDRESS_BITS_TypeDef            addrLen;
    QSPI_INSTRCTION_ADDRESS_MODE_TypeDef transType;

    SPI_TransferMode                     transferMode;      /* Transfer Mode,can be 00 - Transmit & Receive;
                                                             * 01 - Transmit Only; 10 - Receive Only;11 - EEPROM
                                                             * Read*/
    ControlStatus                        slaveSelectToggle; /* When clock phase (SCPH) set to 0, this register
                                                             * controls the behavior of the slave select line
                                                             * (ss_*_n) between data frames. */
    ControlStatus                        slaveOutputEnable; /*  */
    uint8_t                              dataFrameSize;     /* Specifies the SPI data size.This parameter can be
                                                             * a value of @ref SPI_Data_Size */
    uint8_t                              clkPolarity;       /* Specifies the serial clock steady state.This
                                                             * parameter
                                                             * can be a value of @ref SPI_Clock_Polarity */
    uint8_t                              clkPhase;          /* Specifies the clock active edge for the bit
                                                             * capture.
                                                             * This parameter can be a value of @ref
                                                             * SPI_Clock_Phase */
    uint8_t                              transmitTL;        /* Transmit FIFO Threshold. */
    uint8_t                              transmitSL;        /* Transfer start FIFO level. */
    uint8_t                              receiveTL;
    uint16_t                             clkDiv;            /* Specifies the Baud Rate prescaler value which will be
                                                             *            used to configure the transmit and receive SCK
                                                             * clock.
                                                             *            The communication clock is derived from the
                                                             * master
                                                             *            clock. The slave clock does not need to be
                                                             * set. */
    uint16_t                             readDataNum;
    uint32_t                             dummyCycles;
    uint32_t                             rxSampleDelay;
} QSPI_Init_TypeDef;

/**
 * @brief  QSPI Configuration Structure definition
 */
typedef struct __PACKED
{
    ControlStatus       continuousTransferEnable;
    SPI_XIP_MBL_TypeDef modeBitLength;
    ControlStatus       modeBitsEnable;
    uint16_t            modeBitsVale;
    ControlStatus       instructionEnable;
} XIP_conf_TypeDef;

/* basic configure */
void QSPI_enable(void);
void QSPI_disable(void);
void QSPI_setCSLow(void);
void QSPI_setCSHigh(void);
void QSPI_structInit(QSPI_Init_TypeDef *init);
DRV_Status QSPI_init(QSPI_Init_TypeDef *init);
void QSPI_setDummyCycles(uint32_t dummyCycles);
void QSPI_setQSPIFrameFormat(QSPI_FRAME_FORMAT_TypeDef frameFormate);
void QSPI_setDataFrameSize(SPI_DATA_FRAMESIZE_TypeDef frameSize);
void QSPI_setInstructionSize(QSPI_INSTRUCTION_BITS_TypeDef len);
void QSPI_setAddressSize(QSPI_ADDRESS_BITS_TypeDef len);
void QSPI_setInstructionAddressMode(QSPI_INSTRCTION_ADDRESS_MODE_TypeDef transType);
void QSPI_setReadDataNum(uint32_t number);
uint32_t QSPI_getStatus(void);
bool QSPI_isBusy(void);

/* transmit/receive */
DRV_Status QSPI_transmitInstAddr(uint32_t instruction, uint64_t address);
DRV_Status QSPI_transmitData(void *pData, uint16_t size);
DRV_Status QSPI_receive(void *pData, uint16_t size);

/* fifo */
void QSPI_setFIFOInterruptLevel(uint8_t txLevel, uint8_t rxLevel);
void QSPI_getFIFOInterruptLevel(uint8_t *txLevel, uint8_t *rxLevel);
void QSPI_setTansferStartFIFOLevel(uint8_t startLevel);
void QSPI_getTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t *txLevel);
void QSPI_resetFIFO(void);

/*interrupt */
void QSPI_disableInterrupt(uint32_t intType);
void QSPI_enableInterrupt(uint32_t intType);
uint32_t QSPI_getInterruptStatus(void);
uint32_t QSPI_getRawInterruptStatus(void);
void QSPI_clearInterruptStatus(uint32_t intFlags);

/* DMA */
void QSPI_setDMARecevieDataLevel(uint8_t level);
void QSPI_setDMATransmitDataLevel(uint8_t level);
void QSPI_enableDMA(void);
void QSPI_disableDMA(void);

/* XIP */
DRV_Status QSPI_configXIP(XIP_conf_TypeDef *conf);
void QSPI_setINCRTransferCode(uint16_t code);
void QSPI_setWRAPTransferCode(uint16_t code);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /* __ET6X_QSPI_H */
