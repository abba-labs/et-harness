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


/* Define to prevent recursive inclusion ----------------------------------------------------*/
#ifndef __ET6X_I2C_H
#define __ET6X_I2C_H

#ifdef __cplusplus
extern "C" {
#endif

/* includes ---------------------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup I2C
 * @{
 */

/* Exported types -----------------------------------------------------------------------------*/

#define RX_UNDER_MASK                           I2C0_IC_RAW_INTR_STAT_RX_UNDER_Msk
#define RX_OVER_MASK                            I2C0_IC_RAW_INTR_STAT_RX_OVER_Msk
#define RX_FULL_MASK                            I2C0_IC_RAW_INTR_STAT_RX_FULL_Msk
#define TX_OVER_MASK                            I2C0_IC_RAW_INTR_STAT_TX_OVER_Msk
#define TX_EMPTY_MASK                           I2C0_IC_RAW_INTR_STAT_TX_EMPTY_Msk
#define RD_REQ_MASK                             I2C0_IC_RAW_INTR_STAT_RD_REQ_Msk
#define TX_ABRT_MASK                            I2C0_IC_RAW_INTR_STAT_TX_ABRT_Msk
#define RX_DONE_MASK                            I2C0_IC_RAW_INTR_STAT_RX_DONE_Msk
#define ACTIVITY_MASK                           I2C0_IC_RAW_INTR_STAT_ACTIVITY_Msk
#define STOP_DET_MASK                           I2C0_IC_RAW_INTR_STAT_STOP_DET_Msk
#define START_DET_MASK                          I2C0_IC_RAW_INTR_STAT_START_DET_Msk
#define GEN_CALL_MASK                           I2C0_IC_RAW_INTR_STAT_GEN_CALL_Msk
#define WR_REQ_MASK                             I2C0_IC_RAW_INTR_STAT_WR_REQ_Msk

#define I2C_FIFO_DEPTH                          16U

#define I2C_STAND_MODE_SPEED                    (100000U)
#define I2C_FAST_MODE_SPEED                     (400000)
#define I2C_FAST_MODE_PLUS_SPEED                (1000000)

#define I2C_STS_ACTIVITY                        BIT_MASK(0U)  //!< I2C Activity Status
#define I2C_STS_TFNF                            BIT_MASK(1U)  //!< Transmit FIFO Not Full
#define I2C_STS_TFE                             BIT_MASK(2U)  //!< Transmit FIFO Completely Empty
#define I2C_STS_RFNE                            BIT_MASK(3U)  //!< Receive FIFO Completely Full
#define I2C_STS_RFF                             BIT_MASK(4U)  //!< Transmit-data-ready
#define I2C_STS_MST_ACTIVITY                    BIT_MASK(5U)  //!< Master FSM Activity Status.
#define I2C_STS_SLV_ACTIVITY                    BIT_MASK(6U)  //!< Slave FSM Activity Status
#define I2C_STS_MST_HOLD_TX_FIFO_EMPTY          BIT_MASK(7U)  //!< Master holds the bus due to Tx FIFO is empty
#define I2C_STS_MST_HOLD_RX_FIFO_FULL           BIT_MASK(8U)  //!< Master holds the bus due to Rx FIFO is full
#define I2C_STS_SLV_HOLD_TX_FIFO_EMPTY          BIT_MASK(9U)  //!< Slave holds the bus due to Tx FIFO is empty
#define I2C_STS_SLV_HOLD_RX_FIFO_FULL           BIT_MASK(10U) //!< Slave holds the bus due to Rx FIFO is full
#define I2C_STS_SDA_STUCK_NOT_RECOVERED         BIT_MASK(11U) //!< SDA Stuck at low is not recovered after recovery
// mechanism.
#define I2C_STS_SLV_ISO_SAR_DATA_CLK_STRETCH    BIT_MASK(12U) //!< Slave holds the bus to isolate current RX FIFO data
// from next transfer related to another slave address.

#define WRITE_CMD_MASK                          (0U << I2C0_IC_DATA_CMD_CMD_Pos)
#define READ_CMD_MASK                           (1U << I2C0_IC_DATA_CMD_CMD_Pos)
#define LAST_BYTE                               1U


#define I2C_DATA_START_CMD                      (0U)
#define I2C_DATA_WRITE_CMD                      (0U << I2C0_IC_DATA_CMD_CMD_Pos)
#define I2C_DATA_READ_CMD                       (1U << I2C0_IC_DATA_CMD_CMD_Pos)
#define I2C_DATA_RESTART_CMD                    I2C0_IC_DATA_CMD_RESTART_Msk
#define I2C_DATA_STOP_CMD                       I2C0_IC_DATA_CMD_STOP_Msk

/* Exported constans --------------------------------------------------------------------------*/
typedef enum
{
    I2C_SLAVE_MODE  = 0,
    I2C_MASTER_MODE = 1
} I2C_Mode;

typedef enum
{
    I2C_ADDR_MODE_7BITS  = 0U,         //!< 7-bit address
    I2C_ADDR_MODE_10BITS = 1U          //!< 10-bit address
} I2C_AddressMode;

typedef enum
{
    I2C_FIFO_RX1    = 0U,          //!< Receive FIFO 1/16 full
    I2C_FIFO_RX2    = 1U,          //!< Receive FIFO 2/16 full
    I2C_FIFO_RX3    = 2U,          //!< Receive FIFO 3/16 full
    I2C_FIFO_RX4    = 3U,          //!< Receive FIFO 4/16 full
    I2C_FIFO_RX5    = 4U,          //!< Receive FIFO 5/16 full
    I2C_FIFO_RX6    = 5U,          //!< Receive FIFO 6/16 full
    I2C_FIFO_RX7    = 6U,          //!< Receive FIFO 7/16 full
    I2C_FIFO_RX8    = 7U,          //!< Receive FIFO 8/16 full
    I2C_FIFO_RX9    = 8U,          //!< Receive FIFO 9/16 full
    I2C_FIFO_RX10   = 9U,          //!< Receive FIFO 10/16 full
    I2C_FIFO_RX11   = 10U,         //!< Receive FIFO 11/16 full
    I2C_FIFO_RX12   = 11U,         //!< Receive FIFO 12/16 full
    I2C_FIFO_RX13   = 12U,         //!< Receive FIFO 13/16 full
    I2C_FIFO_RX14   = 13U,         //!< Receive FIFO 14/16 full
    I2C_FIFO_RX15   = 14U,         //!< Receive FIFO 15/16 full
    I2C_FIFO_RX16   = 15U,         //!< Receive FIFO full
    I2C_FIFO_RXFULL = 15U          //!< Receive FIFO full
} I2C_RxFIFOLevel;
typedef enum
{
    I2C_FIFO_TX1    = 0U,          //!< Transmit FIFO 1/16 full
    I2C_FIFO_TX2    = 1U,          //!< Transmit FIFO 2/16 full
    I2C_FIFO_TX3    = 2U,          //!< Transmit FIFO 3/16 full
    I2C_FIFO_TX4    = 3U,          //!< Transmit FIFO 4/16 full
    I2C_FIFO_TX5    = 4U,          //!< Transmit FIFO 5/16 full
    I2C_FIFO_TX6    = 5U,          //!< Transmit FIFO 6/16 full
    I2C_FIFO_TX7    = 6U,          //!< Transmit FIFO 7/16 full
    I2C_FIFO_TX8    = 7U,          //!< Transmit FIFO 8/16 full
    I2C_FIFO_TX9    = 8U,          //!< Transmit FIFO 9/16 full
    I2C_FIFO_TX10   = 9U,          //!< Transmit FIFO 10/16 full
    I2C_FIFO_TX11   = 10U,         //!< Transmit FIFO 11/16 full
    I2C_FIFO_TX12   = 11U,         //!< Transmit FIFO 12/16 full
    I2C_FIFO_TX13   = 12U,         //!< Transmit FIFO 13/16 full
    I2C_FIFO_TX14   = 13U,         //!< Transmit FIFO 14/16 full
    I2C_FIFO_TX15   = 14U,         //!< Transmit FIFO 15/16 full
    I2C_FIFO_TX16   = 15U,         //!< Transmit FIFO full
    I2C_FIFO_TXFULL = 15U          //!< Transmit FIFO full
} I2C_TxFIFOLevel;

void I2C_enableModule(I2C_Type *I2Cx);
void I2C_disableModule(I2C_Type *I2Cx);
void I2C_setFIFOInterruptLevel(I2C_Type *I2Cx, I2C_TxFIFOLevel txLevel, I2C_RxFIFOLevel rxLevel);
void I2C_getFIFOInterruptLevel(I2C_Type *I2Cx, I2C_TxFIFOLevel *txLevel, I2C_RxFIFOLevel *rxLevel);
I2C_TxFIFOLevel I2C_getTxFIFOStatus(I2C_Type *I2Cx);
I2C_RxFIFOLevel I2C_getRxFIFOStatus(I2C_Type *I2Cx);
void I2C_setTargetAddress(I2C_Type *I2Cx, uint16_t targetAddr);
void I2C_setOwnAddress(I2C_Type *I2Cx, uint16_t Addr);
bool I2C_isBusBusy(I2C_Type *I2Cx);
uint32_t I2C_getStatus(I2C_Type *I2Cx);
void I2C_setConfig(I2C_Type *I2Cx, I2C_Mode mode);
uint8_t I2C_getData(I2C_Type *I2Cx);
void I2C_putDataCmd(I2C_Type *I2Cx, uint8_t data, uint16_t cmd);
void I2C_setAddressMode(I2C_Type *I2Cx, I2C_AddressMode mode);
void I2C_initController(I2C_Type *I2Cx, uint32_t bitRate, uint8_t dutyCycle);
uint32_t I2C_getInterruptStatus(I2C_Type *I2Cx);
void I2C_clearInterruptStatus(I2C_Type *I2Cx, uint32_t intFlags);
void I2C_enableInterrupt(I2C_Type *I2Cx, uint32_t intFlags);
void I2C_disableInterrupt(I2C_Type *I2Cx, uint32_t intFlags);
void I2C_enableDMATransmit(I2C_Type *I2Cx);
void I2C_disableDMATransmit(I2C_Type *I2Cx);
void I2C_enableDMAReceive(I2C_Type *I2Cx);
void I2C_disableDMAReceive(I2C_Type *I2Cx);
void I2C_Slave_enableGenAck(I2C_Type *I2Cx);
void I2C_Slave_disableGenAck(I2C_Type *I2Cx);
void I2C_enableRestart(I2C_Type *I2Cx);
void I2C_disableRestart(I2C_Type *I2Cx);
void I2C_enableRxFifoFullHold(I2C_Type *I2Cx);
void I2C_disableRxFifoFullHold(I2C_Type *I2Cx);
void I2C_recoveryTransfer(I2C_Type *I2Cx);
void I2C_abortTransfer(I2C_Type *I2Cx);
void I2C_enableBusClear(I2C_Type *I2Cx);
void I2C_disableBusClear(I2C_Type *I2Cx);
void I2C_setSDAHoldTiming(I2C_Type *I2Cx, uint16_t rxTime, uint16_t txTime);

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /* __ET6X_I2C_H */
