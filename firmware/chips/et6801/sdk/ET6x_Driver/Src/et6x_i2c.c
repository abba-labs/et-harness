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
#include "et6x_i2c.h"
#include "et6x_cortex.h"
#include "et6x_crg.h"

/**
 * @addtogroup ET3101_Driver
 * @{
 */

/**
 * @defgroup I2C I2C
 * @brief I2C Driver Library
 * @{
 */

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/

/*! Parameter validity check for I2C peripheral  */
#define IS_I2C_PERIPH(I2Cx)    ((I2Cx == I2C0) || (I2Cx == I2C1) || (I2Cx == I2C2))

#define IS_I2C_IT_MASKS(intFlags) \
        ((intFlags & (RX_UNDER_MASK | RX_OVER_MASK | RX_FULL_MASK | TX_OVER_MASK |     \
                      TX_EMPTY_MASK | RD_REQ_MASK | TX_ABRT_MASK | RX_DONE_MASK |      \
                      ACTIVITY_MASK | STOP_DET_MASK | START_DET_MASK | GEN_CALL_MASK | \
                      WR_REQ_MASK)) != 0)

#define IS_I2C_BITRATE(bitRate)             (bitRate <= I2C_FAST_MODE_PLUS_SPEED)

#define IS_I2C_DUTYCYCLE(duty)              (duty <= 99)

#define IS_I2C_FIFO_THRESHOLD(threshold)    ((threshold >= 0) && (threshold <= I2C_MAX_FIFO_DEPTH))

#define IS_I2C_SLAVE_ADDR(addr)             (addr <= 0x7fU)

#define I2C_MIN_SS_SCL_LOW_TIME     4700U
#define I2C_MIN_FS_SCL_LOW_TIME     1300U
#define I2C_MIN_FSP_SCL_LOW_TIME    500U

#define I2C_STAND_SPEED_MODE        1U
#define I2C_FAST_SPEED_MODE         2U

/**
 * @brief Enables the I2C module.
 *
 * @param I2Cx
 */
void I2C_enableModule(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    SET_BIT(I2Cx->IC_ENABLE, I2C0_IC_ENABLE_ENABLE_Msk);
}

/**
 * @brief Disables the I2C module.
 *
 * @param I2Cx
 */
void I2C_disableModule(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    CLEAR_BIT(I2Cx->IC_ENABLE, I2C0_IC_ENABLE_ENABLE_Msk);
}

/**
 * @brief Sets the FIFO level at which interrupts are generated.
 *
 * @param base
 * @param txLevel
 * @param rxLevel
 */
void I2C_setFIFOInterruptLevel(I2C_Type *I2Cx, I2C_TxFIFOLevel txLevel, I2C_RxFIFOLevel rxLevel)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    WRITE_REG(I2Cx->IC_RX_TL, (uint32_t)rxLevel);
    WRITE_REG(I2Cx->IC_TX_TL, (uint32_t)txLevel);
}

/**
 * @brief Gets the FIFO level at which interrupts are generated.
 *
 * @param I2Cx
 * @param txLevel
 * @param rxLevel
 */
void I2C_getFIFOInterruptLevel(I2C_Type *I2Cx, I2C_TxFIFOLevel *txLevel, I2C_RxFIFOLevel *rxLevel)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    *txLevel = (I2C_TxFIFOLevel)READ_REG(I2Cx->IC_RX_TL);
    *rxLevel = (I2C_RxFIFOLevel)READ_REG(I2Cx->IC_TX_TL);
}

/**
 * @brief Get the transmit FIFO status
 *
 * @param I2Cx
 * @return I2C_TxFIFOLevel
 */
I2C_TxFIFOLevel I2C_getTxFIFOStatus(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    return (I2C_TxFIFOLevel)READ_REG(I2Cx->IC_TXFLR);
}

/**
 * @brief Get the receive FIFO status
 *
 * @param I2Cx
 * @return I2C_RxFIFOLevel
 */
I2C_RxFIFOLevel I2C_getRxFIFOStatus(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    return (I2C_RxFIFOLevel)READ_REG(I2Cx->IC_RXFLR);
}

/**
 * @brief Sets the address that the I2C Controller places on the bus.
 *
 * @param I2Cx
 * @param targetAddr
 */
void I2C_setTargetAddress(I2C_Type *I2Cx, uint16_t targetAddr)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    WRITE_REG(I2Cx->IC_TAR, targetAddr);
}

/**
 * @brief Sets the own address for this I2C module.
 *
 * @param I2Cx
 * @param Addr
 */
void I2C_setOwnAddress(I2C_Type *I2Cx, uint16_t Addr)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    WRITE_REG(I2Cx->IC_SAR, Addr);
    SET_BIT(I2Cx->IC_ENABLE, I2C0_IC_ENABLE_IC_SAR_EN_Msk);
}

/**
 * @brief Indicates whether or not the I2C bus is busy.
 *
 * @param I2Cx
 * @return true
 * @return false
 */
bool I2C_isBusBusy(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    if (READ_BIT(I2Cx->IC_STATUS, I2C0_IC_STATUS_ACTIVITY_Msk) != 0)
    {
        return true;
    }
    else
    {
        return false;
    }
}

/**
 * @brief Gets the current I2C module status.
 *
 * @param I2Cx
 * @return uint16_t The current module status, enumerated as a bit field of
 * I2C_STS_ACTIVITY                     -  I2C Activity Status
 * I2C_STS_TFNF                         -  Transmit FIFO Not Full
 * I2C_STS_TFE                          -  Transmit FIFO Completely Empty
 * I2C_STS_RFNE                         -  Receive FIFO Completely Full
 * I2C_STS_RFF                          -  Transmit-data-ready
 * I2C_STS_MST_ACTIVITY                 -  Master FSM Activity Status.
 * I2C_STS_SLV_ACTIVITY                 -  Slave FSM Activity Status
 * I2C_STS_MST_HOLD_TX_FIFO_EMPTY       -  Master holds the bus due to Tx FIFO is empty
 * I2C_STS_MST_HOLD_RX_FIFO_FULL        -  Master holds the bus due to Rx FIFO is full
 * I2C_STS_SLV_HOLD_TX_FIFO_EMPTY       -  Slave holds the bus due to Tx FIFO is empty
 * I2C_STS_SLV_HOLD_RX_FIFO_FULL        -  Slave holds the bus due to Rx FIFO is full
 * I2C_STS_SDA_STUCK_NOT_RECOVERED      -  SDA Stuck at low is not recovered after recovery mechanism.
 * I2C_STS_SLV_ISO_SAR_DATA_CLK_STRETCH -  Slave holds the bus to isolate current RX FIFO data from next transfer
 * related to another slave address.
 */
uint32_t I2C_getStatus(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    return READ_REG(I2Cx->IC_STATUS);
}

/**
 * @brief set master or slave
 *
 * @param I2Cx
 * @param mode
 */
void I2C_setConfig(I2C_Type *I2Cx, I2C_Mode mode)
{
    if (mode == I2C_MASTER_MODE)
    {
        SET_BIT(I2Cx->IC_CON, I2C0_IC_CON_MASTER_MODE_Msk);
        SET_BIT(I2Cx->IC_CON, I2C0_IC_CON_IC_SLAVE_DISABLE_Msk);
    }
    else
    {
        CLEAR_BIT(I2Cx->IC_CON, I2C0_IC_CON_MASTER_MODE_Msk);
        CLEAR_BIT(I2Cx->IC_CON, I2C0_IC_CON_IC_SLAVE_DISABLE_Msk);
    }
}

//*****************************************************************************
//
//! Receives a byte that has been sent to the I2C.
//!
//! \param base is the base address of the I2C instance used.
//!
//! This function reads a byte of data from the I2C Data Receive Register.
//!
//! \return Returns the byte received from by the I2C cast as an uint16_t.
//
//*****************************************************************************

/**
 * @brief Receives a byte that has been sent to the I2C.
 *
 * @param I2Cx
 * @return uint8_t
 */
uint8_t I2C_getData(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    return (uint8_t)READ_REG(I2Cx->IC_DATA_CMD);
}

/**
 * @brief Transmits a byte from the I2C.
 *
 * @param I2Cx
 * @param data
 * @param cmd
 */
void I2C_putDataCmd(I2C_Type *I2Cx, uint8_t data, uint16_t cmd)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    WRITE_REG(I2Cx->IC_DATA_CMD, (uint32_t)data | cmd);
}

/**
 * @brief Sets the addressing mode to either 7-bit or 10-bit.
 *
 * @param I2Cx
 * @param mode
 */
void I2C_setAddressMode(I2C_Type *I2Cx, I2C_AddressMode mode)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    MODIFY_REG(I2Cx->IC_CON, I2C0_IC_CON_IC_10BITADDR_MASTER_Msk,
               (uint32_t)mode << I2C0_IC_CON_IC_10BITADDR_MASTER_Pos);
    MODIFY_REG(I2Cx->IC_CON, I2C0_IC_CON_IC_10BITADDR_SLAVE_Msk, (uint32_t)mode << I2C0_IC_CON_IC_10BITADDR_SLAVE_Pos);

    MODIFY_REG(I2Cx->IC_TAR, I2C0_IC_TAR_IC_10BITADDR_MASTER_Msk,
               (uint32_t)mode << I2C0_IC_TAR_IC_10BITADDR_MASTER_Pos);
}

//*****************************************************************************
//
//! Initializes the I2C Controller.
//!
//! \param base is the base address of the I2C instance used.
//! \param sysclkHz is the rate of the clock supplied to the I2C module
//! (SYSCLK) in Hz.
//! \param bitRate is the rate of the controller clock signal, SCL.
//! \param dutyCycle is duty cycle of the SCL signal.
//!
//! This function initializes operation of the I2C Controller by configuring the
//! bus speed for the controller. Note that the I2C module \b must be put into
//! reset before calling this function. You can do this with the function
//! I2C_disableModule().
//!
//! A programmable prescaler in the I2C module divides down the input clock
//! (rate specified by \e sysclkHz) to produce the module clock (calculated to
//! be around 10 MHz in this function). That clock is then divided down further
//! to configure the SCL signal to run at the rate specified by \e bitRate. The
//! \e dutyCycle parameter determines the percentage of time high and time low
//! on the clock signal. The valid values are \b I2C_DUTYCYCLE_33 for 33% and
//! \b I2C_DUTYCYCLE_50 for 50%.
//!
//! The peripheral clock is the system clock.  This value is returned by
//! SysCtl_getClock(), or it can be explicitly hard coded if it is
//! constant and known (to save the code/execution overhead of a call to
//! SysCtl_getClock()).
//!
//! \return None.
//
//*****************************************************************************
void I2C_initController(I2C_Type *I2Cx, uint32_t bitRate, uint8_t dutyCycle)
{
    uint32_t period = 0;
    uint32_t scl_l_cnt = 0, scl_h_cnt = 0;
    uint32_t speed_mode = 0;

    assert_param(IS_I2C_PERIPH(I2Cx));
    assert_param(IS_I2C_BITRATE(bitRate));
    assert_param(IS_I2C_DUTYCYCLE(dutyCycle));

    /* calibration speed */
    period = CRG_getAPB3Clock() / bitRate;
    if (bitRate <= I2C_STAND_MODE_SPEED)
    {
        speed_mode = I2C_STAND_SPEED_MODE;
        scl_l_cnt  = I2C_MIN_SS_SCL_LOW_TIME / (1000000000 / CRG_getAPB3Clock());
        scl_h_cnt  = period - scl_l_cnt - 16;
        scl_l_cnt  = scl_l_cnt - 1;
        if (scl_l_cnt < 9)
        {
            scl_l_cnt = 9;
        }
        if (scl_h_cnt < 13)
        {
            scl_l_cnt = 13;
        }
        WRITE_REG(I2Cx->IC_SS_SCL_HCNT, (scl_h_cnt + scl_l_cnt) * dutyCycle / 100U);
        WRITE_REG(I2Cx->IC_SS_SCL_LCNT, (scl_h_cnt + scl_l_cnt) * (100U - dutyCycle) / 100U);
    }
    else if ((bitRate <= I2C_FAST_MODE_SPEED) && (bitRate > I2C_STAND_MODE_SPEED))
    {
        speed_mode = I2C_FAST_SPEED_MODE;
        scl_l_cnt  = I2C_MIN_FS_SCL_LOW_TIME / (1000000000 / CRG_getAPB3Clock());
        scl_h_cnt  = period - scl_l_cnt - 16;
        scl_l_cnt  = scl_l_cnt - 1;
        if (scl_l_cnt < 9)
        {
            scl_l_cnt = 9;
        }
        if (scl_h_cnt < 13)
        {
            scl_l_cnt = 13;
        }
        WRITE_REG(I2Cx->IC_FS_SCL_HCNT, (scl_h_cnt + scl_l_cnt) * dutyCycle / 100U);
        WRITE_REG(I2Cx->IC_FS_SCL_LCNT, (scl_h_cnt + scl_l_cnt) * (100U - dutyCycle) / 100U);
    }
    else if ((bitRate <= I2C_FAST_MODE_PLUS_SPEED) && (bitRate > I2C_FAST_MODE_SPEED))
    {
        speed_mode = I2C_FAST_SPEED_MODE;
        scl_l_cnt  = I2C_MIN_FSP_SCL_LOW_TIME / (1000000000 / CRG_getAPB3Clock());
        scl_h_cnt  = period - scl_l_cnt - 16;
        scl_l_cnt  = scl_l_cnt - 1;
        if (scl_l_cnt < 9)
        {
            scl_l_cnt = 9;
        }
        if (scl_h_cnt < 13)
        {
            scl_l_cnt = 13;
        }
        WRITE_REG(I2Cx->IC_FS_SCL_HCNT, (scl_h_cnt + scl_l_cnt) * dutyCycle / 100U);
        WRITE_REG(I2Cx->IC_FS_SCL_LCNT, (scl_h_cnt + scl_l_cnt) * (100U - dutyCycle) / 100U);
    }
    MODIFY_REG(I2Cx->IC_CON, I2C0_IC_CON_SPEED_Msk, speed_mode << I2C0_IC_CON_SPEED_Pos);
    WRITE_REG(I2Cx->IC_INTR_MASK, 0U);
}

/**
 * @brief Gets the current I2C interrupt status.
 *
 * @param I2Cx
 * @return uint32_t
 * RX_UNDER_MASK
 * RX_OVER_MASK
 * RX_FULL_MASK
 * TX_OVER_MASK
 * TX_EMPTY_MASK
 * RD_REQ_MASK
 * TX_ABRT_MASK
 * RX_DONE_MASK
 * ACTIVITY_MASK
 * STOP_DET_MASK
 * START_DET_MASK
 * GEN_CALL_MASK
 * WR_REQ_MASK
 */
uint32_t I2C_getInterruptStatus(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    return READ_REG(I2Cx->IC_INTR_STAT);
}

//*****************************************************************************
//
//! Clears I2C interrupt sources.
//!
//! \param base is the base address of the I2C instance used.
//! \param intFlags is a bit mask of the interrupt sources to be cleared.
//!
//! The specified I2C interrupt sources are cleared, so that they no longer
//! assert.  This function must be called in the interrupt handler to keep the
//! interrupt from being triggered again immediately upon exit.
//!
//! The \e intFlags parameter has the same definition as the \e intFlags
//! parameter to I2C_enableInterrupt().
//!
//! \note \b I2C_INT_RXFF and \b I2C_INT_TXFF are associated with the I2C FIFO
//! interrupt vector. All others are associated with the I2C basic interrupt.
//!
//! \note Also note that some of the status flags returned by
//! I2C_getInterruptStatus() cannot be cleared by this function. Some may only
//! be cleared by hardware or a reset of the I2C module.
//!
//! \return None.
//
//*****************************************************************************
void I2C_clearInterruptStatus(I2C_Type *I2Cx, uint32_t intFlags)
{
    uint32_t val;

    assert_param(IS_I2C_PERIPH(I2Cx));
    assert_param(IS_I2C_IT_MASKS(intFlags));

    if ((intFlags & RX_UNDER_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_RX_UNDER);
    }
    if ((intFlags & RX_OVER_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_RX_OVER);
    }
    if ((intFlags & RX_FULL_MASK) != 0)
    {
// auto clear by hardware if rx is not full
    }
    if ((intFlags & TX_OVER_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_TX_OVER);
    }
    if ((intFlags & TX_EMPTY_MASK) != 0)
    {
// auto cleared by hardware when the buffer level goes above the threshold.
    }
    if ((intFlags & RD_REQ_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_RD_REQ);
    }
    if ((intFlags & TX_ABRT_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_TX_ABRT);
    }
    if ((intFlags & RX_DONE_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_RX_DONE);
    }
    if ((intFlags & ACTIVITY_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_ACTIVITY);
    }
    if ((intFlags & STOP_DET_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_STOP_DET);
    }
    if ((intFlags & START_DET_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_START_DET);
    }
    if ((intFlags & GEN_CALL_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_GEN_CALL);
    }
    if ((intFlags & WR_REQ_MASK) != 0)
    {
        val = READ_REG(I2Cx->IC_CLR_WR_REQ);
    }

    UNUSED(val);
}

/**
 * @brief unmask I2C interrupt masks
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 * @param intFlags: interrupt masks
 */
void I2C_enableInterrupt(I2C_Type *I2Cx, uint32_t intFlags)
{
    assert_param(IS_I2C_PERIPH(I2Cx));
    assert_param(IS_I2C_IT_MASKS(intFlags));

    SET_BIT(I2Cx->IC_INTR_MASK, intFlags);
}

/**
 * @brief unmask I2C interrupt masks
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 * @param intFlags: interrupt masks
 */
void I2C_disableInterrupt(I2C_Type *I2Cx, uint32_t intFlags)
{
    assert_param(IS_I2C_PERIPH(I2Cx));
    assert_param(IS_I2C_IT_MASKS(intFlags));

    CLEAR_BIT(I2Cx->IC_INTR_MASK, intFlags);
}

/**
 * @brief Enable I2Cx transmit DMA
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_enableDMATransmit(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    SET_BIT(I2Cx->IC_DMA_CR, I2C0_IC_DMA_CR_TDMAE_Msk);
}

/**
 * @brief Disable I2Cx transmit DMA
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_disableDMATransmit(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    CLEAR_BIT(I2Cx->IC_DMA_CR, I2C0_IC_DMA_CR_TDMAE_Msk);
}

/**
 * @brief Enable I2Cx receive DMA
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_enableDMAReceive(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    SET_BIT(I2Cx->IC_DMA_CR, I2C0_IC_DMA_CR_RDMAE_Msk);
}

/**
 * @brief Disable I2Cx receive DMA
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_disableDMAReceive(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    CLEAR_BIT(I2Cx->IC_DMA_CR, I2C0_IC_DMA_CR_RDMAE_Msk);
}

/**
 * @brief Enable the I2C slave ACK respond
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_Slave_enableGenAck(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    SET_BIT(I2Cx->IC_ACK_GENERAL_CALL, I2C0_IC_ACK_GENERAL_CALL_ACK_GEN_CALL_Msk);
}

/**
 * @brief Disable the I2C slave ACK respond
 *
 * @param I2Cx: select I2C device [I2C0 - I2C1]
 */
void I2C_Slave_disableGenAck(I2C_Type *I2Cx)
{
    assert_param(IS_I2C_PERIPH(I2Cx));

    CLEAR_BIT(I2Cx->IC_ACK_GENERAL_CALL, I2C0_IC_ACK_GENERAL_CALL_ACK_GEN_CALL_Msk);
}

/**
 * @brief Enable restart
 *
 * @param I2Cx
 */
void I2C_enableRestart(I2C_Type *I2Cx)
{
    SET_BIT(I2Cx->IC_CON, I2C0_IC_CON_IC_RESTART_EN_Msk);
}

/**
 * @brief Disable restart
 *
 * @param I2Cx
 */
void I2C_disableRestart(I2C_Type *I2Cx)
{
    CLEAR_BIT(I2Cx->IC_CON, I2C0_IC_CON_IC_RESTART_EN_Msk);
}

/**
 * @brief Enable receive FIFO full hold functionality
 *
 * @param I2Cx
 */
void I2C_enableRxFifoFullHold(I2C_Type *I2Cx)
{
    SET_BIT(I2Cx->IC_CON, I2C0_IC_CON_RX_FIFO_FULL_HLD_CTRL_Msk);
}

/**
 * @brief Disable receive FIFO full hold functionality
 *
 * @param I2Cx
 */
void I2C_disableRxFifoFullHold(I2C_Type *I2Cx)
{
    CLEAR_BIT(I2Cx->IC_CON, I2C0_IC_CON_RX_FIFO_FULL_HLD_CTRL_Msk);
}

/**
 * @brief Enable receive FIFO full hold functionality
 *
 * @param I2Cx
 */
void I2C_abortTransfer(I2C_Type *I2Cx)
{
    SET_BIT(I2Cx->IC_ENABLE, I2C0_IC_ENABLE_ABORT_Msk);
}

/**
 * @brief Enable  functionality
 *
 * @param I2Cx
 */
void I2C_recoveryTransfer(I2C_Type *I2Cx)
{
    SET_BIT(I2Cx->IC_ENABLE, I2C0_IC_ENABLE_SDA_STUCK_RECOVERY_ENABLE_Msk);
}

/**
 * @brief Enable bus clear functionality
 *
 * @param I2Cx
 */
void I2C_enableBusClear(I2C_Type *I2Cx)
{
    SET_BIT(I2Cx->IC_ENABLE, I2C0_IC_CON_BUS_CLEAR_FEATURE_CTRL_Msk);
}

/**
 * @brief Disable bus clear functionality
 *
 * @param I2Cx
 */
void I2C_disableBusClear(I2C_Type *I2Cx)
{
    CLEAR_BIT(I2Cx->IC_ENABLE, I2C0_IC_CON_BUS_CLEAR_FEATURE_CTRL_Msk);
}

/**
 * @brief Set SDA hold timing
 *
 * @param I2Cx
 */
void I2C_setSDAHoldTiming(I2C_Type *I2Cx, uint16_t rxTime, uint16_t txTime)
{
    WRITE_REG(I2Cx->IC_SDA_HOLD,
              ((uint32_t)rxTime <<
               I2C0_IC_SDA_HOLD_IC_SDA_RX_HOLD_Pos) | ((uint32_t)txTime << I2C0_IC_SDA_HOLD_IC_SDA_TX_HOLD_Pos));
}

/**
 * @}
 */

/**
 * @}
 */

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
