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
#include "et6x_uart.h"
#include "et6x_crg.h"

#if defined(FPGA_VERSION)
#define UART_SYS_CLOCK_HZ              (25000000)
#else
#define UART_SYS_CLOCK_HZ              (CRG_getAPB3Clock())

#endif
#define UART_TX_BLOCK_TIMEOUT          (0x8000)
#define DIVISOR_LATCH_PRECISION_NUM    (32)


/* function declare ------------------------------------------------------------*/


/* Private macros ------------------------------------------------------------*/


/** @brief Calculate the UART divisor(double) corresponding to the baud rate .
 * @param  __PCLK__: Uart clock in hz
 * @param  __BAUD__: Uart baudRate
 * @retval divisor
 */
#define _DEF_UART_DIV_SAMPLING(__PCLK__, __BAUD__)    ((double)__PCLK__ / (__BAUD__ << 4))


/** @brief Determine whether the Uart address is incorrect.
 * @param  _INSTANCE_: Uart Address
 * @retval TUre/False
 */
#define IS_UART_INSTANCE(_INSTANCE_) \
        ((_INSTANCE_ == UART0) || (_INSTANCE_ == UART1) || (_INSTANCE_ == UART2) || (_INSTANCE_ == UART3))

/* Private variables ---------------------------------------------------------*/

/* Private function prototypes -----------------------------------------------*/

/** @defgroup UART_Public_Functions UART Public Functions
 * @brief Uart Driver Public Function
 * @{
 */

/**
 * @brief UARTx receive all data(Less than or equal to 8bits) in FIFO, Common interface in Normal/RS485/RS232/SIR
 *         and 9bits RCVR HW modes. UARTx RCVR_FIFO must enable before use this interface.
 * @param UARTx: UART Instance. UARTx Base addr
 * @param data: Pointer receive data buffer(u8 data elements)
 * @param  sizeMax: size of receive data buffer (u8 data elements).Receive element cnts must below to this size.
 * @retval Receive FIFO data(Less than or equal to 8bits) counts
 */
uint16_t UART_receiveWithFIFO(UART_Type *UARTx, uint8_t *data, uint16_t sizeMax)
{
    uint16_t rxCnt       = 0;
    uint16_t rxFIFOLevel = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(sizeMax != 0);

    rxFIFOLevel = (uint16_t)READ_REG(UARTx->RFL);
    if (rxFIFOLevel > sizeMax)
    {
        rxFIFOLevel = sizeMax;
    }

    while (rxFIFOLevel != rxCnt)
    {
        data[rxCnt] = (uint8_t)READ_REG(UARTx->RBR);
        rxCnt++;
    }

    return rxCnt;
}

/**
 * @brief UARTx recieve all data(9bits) in FIFO, this interface is for 9-bit RCVR SW modes.UARTx RCVR_FIFO must enable
 *         before use this interface
 * @param UARTx: UART Instance. UARTx Base addr
 * @param data: Pointer receive data buffer(u16 data elements)
 * @param  sizeMax: size of receive data buffer (u16 data elements).Receive element cnts must below to this size.
 * @retval Receive FIFO data(9bits) counts
 */
uint16_t UART_receiveWithFIFO9BIT(UART_Type *UARTx, uint16_t *data, uint16_t sizeMax)
{
    uint16_t rxCnt       = 0;
    uint16_t rxFIFOLevel = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(sizeMax != 0);

    rxFIFOLevel = (uint16_t)READ_REG(UARTx->RFL);
    if (rxFIFOLevel > sizeMax)
    {
        rxFIFOLevel = sizeMax;
    }

    while (rxFIFOLevel != rxCnt)
    {
        data[rxCnt] = (uint16_t)READ_REG(UARTx->RBR);
        rxCnt++;
    }

    return rxCnt;
}

/**
 * @brief  UARTx recieve data, Common interface in Normal/RS485/RS232/SIR/9Bit modes.
 * @note   When UARTx FIFO is disable, only can recieve one data.When UARTx is working in 9 bit RCVR SW mode,
 *          the receive data is handled as a set of u16. And return counts will indicate the number of u16.
 * @param  UARTx: Pointer to UARTx Base addr
 * @param  data: Pointer to receive data buffer (u8 or u16 data elements).
 * @param  sizeMax: size of receive data buffer (u8 or u16 data elements).Receive element cnts must below to this size.
 * @retval Receive element cnts
 */
uint16_t UART_receive(UART_Type *UARTx, void *data, uint16_t elementSizeMax)
{
    uint16_t rxCnt  = 0;
    uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(elementSizeMax != 0);

    tmpReg = READ_REG(UARTx->LCR_EXT);
    if ((tmpReg & (UART0_LCR_EXT_ADDR_MATCH_Msk | UART0_LCR_EXT_DLS_E_Msk)) == UART0_LCR_EXT_DLS_E_Msk)
    {
        rxCnt = UART_receiveWithFIFO9BIT(UARTx, (uint16_t *)data, elementSizeMax);
    }
    else
    {
        rxCnt = UART_receiveWithFIFO(UARTx, (uint8_t *)data, elementSizeMax);
    }

    return rxCnt;
}

/**
 * @brief UARTx Transmit all data(Less than or equal to 8bits) to FIFO, Common interface in Normal/RS485/RS232/SIR
 *        and 9Bit Transmit HW modes. UARTx XMIT_FIFO must enable before use this interface
 * @param UARTx: UART Instance. UARTx Base addr
 * @param data: Pointer transmit data buffer(u8 data elements)
 * @param size: size of transmit data buffer (u8 data elements)
 * @param transType: If Transmit FIFO is full, will return transmit cnts when transType is UART_NON_BLOCK_TRANSMIT_FIFO.
 *         And will waiting for transmit fifo is not full when transType is UART_BLOCK_TRANSMIT_FIFO(User can change
 * Timeout
 *         By UART_TX_BLOCK_TIMEOUT)
 * @retval Transmit data(Less than or equal to 8bits) counts
 */
uint16_t UART_transmitWithFIFO(UART_Type *UARTx, uint8_t *data, uint16_t size, UART_TransType transType)
{
    uint16_t sendCnt    = 0;
    uint16_t tmpTimeout = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(size != 0);

    if (transType == UART_BLOCK_TRANSMIT_FIFO)
    {
        while (size != sendCnt)
        {
            /* wating for transmit fifo not full */
            tmpTimeout = 0;
            while (_DEF_UART_GET_UART_STATUS(UARTx, UART_STA_TFNF_FLAG) == 0)
            {
                if (tmpTimeout++ == UART_TX_BLOCK_TIMEOUT)
                {
                    return sendCnt;
                }
            }

            WRITE_REG(UARTx->THR, data[sendCnt]);
            sendCnt++;
        }
    }
    else if (transType == UART_NON_BLOCK_TRANSMIT_FIFO)
    {
        while (size != sendCnt)
        {
            /* if transmit fifo is full, return cnt */
            if (_DEF_UART_GET_UART_STATUS(UARTx, UART_STA_TFNF_FLAG) == 0)
            {
                return sendCnt;
            }

            WRITE_REG(UARTx->THR, data[sendCnt]);
            sendCnt++;
        }
    }

    return sendCnt;
}

/**
 * @brief UARTx Transmit all data(9bits) to FIFO, Common interface in 9Bit Transmit SW mode. UARTx XMIT_FIFO must
 *         enable before use this interface
 * @param UARTx: UART Instance. UARTx Base addr
 * @param data: Pointer transmit data buffer(u16 data elements)
 * @param size: size of transmit data buffer (u16 data elements)
 * @param transType: If Transmit FIFO is full, will return transmit cnts when transType is UART_NON_BLOCK_TRANSMIT_FIFO.
 *         And will waiting for transmit fifo is not full when transType is UART_BLOCK_TRANSMIT_FIFO(User can change
 * Timeout
 *         By UART_TX_BLOCK_TIMEOUT)
 * @retval Transmit data(9bits u16 data elements) counts
 */
uint16_t UART_transmitWithFIFO9BIT(UART_Type *UARTx, uint16_t *data, uint16_t size, UART_TransType transType)
{
    uint16_t sendCnt    = 0;
    uint16_t tmpTimeout = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(size != 0);

    if (transType == UART_BLOCK_TRANSMIT_FIFO)
    {
        while (size != sendCnt)
        {
            /* wating for transmit fifo not full */
            tmpTimeout = 0;
            while (_DEF_UART_GET_UART_STATUS(UARTx, UART_STA_TFNF_FLAG) == 0)
            {
                if (tmpTimeout++ == UART_TX_BLOCK_TIMEOUT)
                {
                    return sendCnt;
                }
            }

            WRITE_REG(UARTx->THR, data[sendCnt]);
            sendCnt++;
        }
    }
    else if (transType == UART_NON_BLOCK_TRANSMIT_FIFO)
    {
        while (size != sendCnt)
        {
            /* if transmit fifo is full, return cnt */
            if (_DEF_UART_GET_UART_STATUS(UARTx, UART_STA_TFNF_FLAG) == 0)
            {
                return sendCnt;
            }

            WRITE_REG(UARTx->THR, data[sendCnt]);
            sendCnt++;
        }
    }

    return sendCnt;
}

/**
 * @brief  UARTx transmit data, Common interface in Normal/RS485/RS232/SIR/9Bit modes.
 * @note   When UARTx is working in 8 bitsmode ,the sent data is handled as a set of u8.In this case, size must
 *         indicate the number of u8 provided through data.
 *         When UARTx is working in 9 bits XMIT SW mode ,the sent data is handled as a set of u16.In this case, size
 *         must indicate the number of u16 provided through data.
 *         When transType is UART_BLOCK_TRANSMIT_FIFO, data will be transmit until send_counts equal to size.If TX FIFO
 *         is full, UARTx will be blocked for FIFO is not full.
 *         When transType is UART_NON_BLOCK_TRANSMIT_FIFO, will try to send data until FIFO is full, so maybe sendcouts
 *         will below to size.
 * @param  UARTx: Pointer to UARTx Base addr
 * @param  data: Pointer to data buffer (u8 or u16 data elements).
 * @param  size:  Amount of data elements (u8 or u16) to be sent
 * @param  transType: If Transmit FIFO is full, will return transmit cnt when transType is UART_NON_BLOCK_TRANSMIT_FIFO.
 *         And will waiting for transmit fifo is not full when transType is UART_BLOCK_TRANSMIT_FIFO.
 * @retval Send element cnts
 */
uint16_t UART_transmit(UART_Type *UARTx, void *data, uint16_t size, UART_TransType transType)
{
    uint16_t sendCnt = 0;
    uint32_t tmpReg  = 0;

    assert_param(UARTx != NULL);
    assert_param(data != NULL);
    assert_param(size != 0);

    tmpReg = READ_REG(UARTx->LCR_EXT);

    /* Judge if 9-bits Manual mode */
    if ((tmpReg & (UART0_LCR_EXT_TRANSMIT_MODE_Msk | UART0_LCR_EXT_DLS_E_Msk)) == \
        (UART0_LCR_EXT_TRANSMIT_MODE_Msk | UART0_LCR_EXT_DLS_E_Msk))
    {
        sendCnt = UART_transmitWithFIFO9BIT(UARTx, data, size, transType);
    }
    else
    {
        sendCnt = UART_transmitWithFIFO(UARTx, data, size, transType);
    }


    return sendCnt;
}

/**
 * @brief wait uart transmit FIFO empty
 * @param UARTx: Pointer to UARTx Base addr
 * @timeout: timeout count
 * @retval Driver status, DRV_OK or DRV_TIMEOUT
 */
DRV_Status UART_waitTransmitDone(UART_Type *UARTx, uint32_t timeout)
{
    assert_param(UARTx != NULL);

    do
    {
        if (_DEF_UART_GET_UART_STATUS(UARTx, UART_STA_TFE_FLAG) == UART_STA_TFE_FLAG)
        {
            return DRV_OK;
        }
    }while (timeout-- > 0);
    return DRV_TIMEOUT;
}

/**
 * @brief Set Uart baudrate
 * @param UARTx: Pointer to UARTx Base addr
 * @baudRate: Target baud rate. Must below UART_BAUDRATE_MAX
 * @retval Driver status
 */
DRV_Status UART_setBaudrate(UART_Type *UARTx, uint32_t baudRate)
{
    double   divisor          = 0.0;
    uint16_t divisor_int      = 0;
    double   divisor_fraction = 0;
    uint32_t tmpReg           = 0;

    assert_param(UARTx != NULL);

    if (baudRate > UART_BAUDRATE_MAX)
    {
        return DRV_PARAM_ERR;
    }
    if (baudRate == 0)
    {
        return DRV_PARAM_ERR;
    }

    divisor          = _DEF_UART_DIV_SAMPLING(UART_SYS_CLOCK_HZ, baudRate);
    divisor_int      = (uint16_t)divisor;
    divisor_fraction = (double)(divisor - divisor_int) * DIVISOR_LATCH_PRECISION_NUM;

    if (divisor_fraction >= DIVISOR_LATCH_PRECISION_NUM)
    {
        return DRV_PARAM_ERR;
    }

    /* Enable Divisior Latch Register Access */
    SET_BIT(UARTx->LCR, UART0_LCR_DLAB_Msk);

    tmpReg = divisor_int & 0xFFU;
    WRITE_REG(UARTx->DLL, tmpReg);
    tmpReg = (divisor_int >> 8) & 0xFFU;
    WRITE_REG(UARTx->DLH, tmpReg);
    tmpReg = (uint32_t)divisor_fraction;
    WRITE_REG(UARTx->DLF, tmpReg);

    /* Divisior Latch Register Only Can Be Written LCR_DLAB Is Set */
    CLEAR_BIT(UARTx->LCR, UART0_LCR_DLAB_Msk);

    return DRV_OK;
}

/**
 * @brief Get Uart RCVR FIFO cnt
 * @param UARTx: Pointer to UARTx Base addr
 * @retval RCVR FIFO Cnt
 */
uint16_t UART_getRxFIFOStatus(UART_Type *UARTx)
{
    return (uint16_t)READ_REG(UARTx->RFL);
}

/**
 * @brief Get Uart XMIT FIFO cnt
 * @param UARTx: Pointer to UARTx Base addr
 * @retval XMIT FIFO Cnt
 */
uint16_t UART_getTxFIFOStatus(UART_Type *UARTx)
{
    return (uint16_t)READ_REG(UARTx->TFL);
}

/**
 * @brief Configure the UART peripheral. Not support SIRmode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param wordLength: Only support less than or equal to 8bits
 * @param stopBits: 1.5 stop bits when wordLength is 5bits, else 2 stop bit
 * @param parity: Uart parity
 * @retval Config status
 */
DRV_Status UART_setLineConfig(UART_Type *UARTx, UART_WordLength wordLength, \
                              UART_StopBit stopBits, UART_ParityBit parity)
{
    uint32_t tempReg = 0;

    assert_param(UARTx != NULL);

    /* Check Uart init Param */
    if ((wordLength != UART_WORDLENGTH_5B) && \
        (wordLength != UART_WORDLENGTH_6B) && \
        (wordLength != UART_WORDLENGTH_7B) && \
        (wordLength != UART_WORDLENGTH_8B))
    {
        return DRV_PARAM_ERR;
    }

    if ((stopBits != UART_STOPBITS_1) && \
        (stopBits != UART_STOPBITS_2) && \
        (stopBits != UART_STOPBITS_1_5_WORDLENGTH_5B))
    {
        return DRV_PARAM_ERR;
    }

    if ((parity != UART_PARITY_NONE) && \
        (parity != UART_PARITY_EVEN) && \
        (parity != UART_PARITY_ODD) && \
        (parity != UART_PARITY_STICK_0) && \
        (parity != UART_PARITY_STICK_1))
    {
        return DRV_PARAM_ERR;
    }

    CLEAR_BIT(tempReg, (UART0_LCR_SP_Msk | UART0_LCR_PEN_Msk | \
                        UART0_LCR_EPS_Msk | UART0_LCR_STOP_Msk | UART0_LCR_DLS_Msk));
    tempReg  = READ_REG(UARTx->LCR);
    tempReg |= (uint32_t)stopBits | (uint32_t)parity | (uint32_t)wordLength;

    WRITE_REG(UARTx->LCR, tempReg);

    return DRV_OK;
}

/**
 * @brief Config RTS(Request To Send) status in HWFlow mode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param Vailed: Assert Status, SET to Assert/RESET to DeAssert
 * @retval Void
 */
void UART_setRTSSign(UART_Type *UARTx, FlagStatus signAssert)
{
    if (signAssert == SET)
    {
        _DEF_UART_RTS_ASSERT(UARTx);
    }
    else
    {
        _DEF_UART_RTS_DEASSERT(UARTx);
    }
}

/**
 * @brief Config DTR(data Terminal Ready) status in HWFlow mode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param signAssert: Assert Status, SET to Assert/RESET to DeAssert
 * @retval Void
 */
void UART_setDTRSign(UART_Type *UARTx, FlagStatus signAssert)
{
    if (signAssert == SET)
    {
        _DEF_UART_DTR_ASSERT(UARTx);
    }
    else
    {
        _DEF_UART_DTR_DEASSERT(UARTx);
    }
}

/**
 * @brief Enable SIRmode, In this mode, wordLength/Stop bits/ParityBit Config inoperative.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval Config status
 */
DRV_Status UART_enableSIRMode(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    SET_BIT(UARTx->MCR, UART0_MCR_SIRE_Msk);
    return DRV_OK;
}

/**
 * @brief Disable SIRmode.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval Config status
 */
DRV_Status UART_disableSIRMode(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    CLEAR_BIT(UARTx->MCR, UART0_MCR_SIRE_Msk);
    CLEAR_REG(UARTx->LPDLL);
    CLEAR_REG(UARTx->LPDLH);
    return DRV_OK;
}

/**
 * @brief Disable SIR lowPower mode.Uaer must enable SIRmode first.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval Config status
 */
DRV_Status UART_configSIRLowPowerMode(UART_Type *UARTx)
{
    double   divisor     = 0.0;
    uint16_t divisor_int = 0;
    uint32_t tmpReg      = 0;

    assert_param(UARTx != NULL);

    /* baudRate Must Be 115200 In Low Power SIR Mode */
    divisor     = _DEF_UART_DIV_SAMPLING(UART_SYS_CLOCK_HZ, UART_LOW_POWER_SIR_BAUDRATE);
    divisor_int = (uint16_t)divisor;

    tmpReg = divisor_int & 0xFFU;
    WRITE_REG(UARTx->LPDLL, tmpReg);
    tmpReg = (divisor_int >> 8) & 0xFFU;
    WRITE_REG(UARTx->LPDLH, tmpReg);

    return DRV_OK;
}

/**
 * @brief This is used to cause a break condition to be transmitted to the receiving device.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_sendBreak(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    SET_BIT(UARTx->LCR, UART0_LCR_BC_Msk);
}

/**
 * @brief Halt Uart transmit.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_haltTransmission(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    WRITE_REG(UARTx->HTX, UART0_HTX_HTX_Msk);
}

/**
 * @brief Continue Uart transmit.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_resumeTransmission(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    CLEAR_REG(UARTx->HTX);
}

/**
 * @brief Trigger 9bit Uart transmit addr. Only be used When 9Bit XMIT Hw Mode is enable.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_triggerAddressSend(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    SET_BIT(UARTx->LCR_EXT, UART0_LCR_EXT_SEND_ADDR_Msk);
}

/**
 * @brief Set 9bit Uart Transmit ADDR. Only be used When 9Bit XMIT Hw Mode is enable.
 * @param UARTx: Pointer to UARTx Base addr
 * @param XMITAddr: 9bit Mode Uart Transmit ADDR
 * @retval void
 */
void UART_setTransferAddress(UART_Type *UARTx, uint8_t XMITAddr)
{
    assert_param(UARTx != NULL);

    WRITE_REG(UARTx->TAR, XMITAddr);
}

/**
 * @brief Set 9bit Uart receive ADDR. Only be used when 9Bit RCVR Hw Mode is enable.
 * @param UARTx: Pointer to UARTx Base addr
 * @param RCVRAddr: 9bit Mode Uart Receive ADDR
 * @retval void
 */
void UART_setReceiveAddress(UART_Type *UARTx, uint8_t RCVRAddr)
{
    assert_param(UARTx != NULL);

    WRITE_REG(UARTx->RAR, RCVRAddr);
}

/**
 * @brief init the UART 9 Bit mode. Not support SIRmode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param uart9Bit: Pointer to uart9Bit priv cfg(UART_9BIT_ConfigParams)
 * @retval void
 */
void UART_config9BitMode(UART_Type *UARTx, UART_9BIT_ConfigParams *uart9Bit)
{
    uint32_t regTemp = 0;

    assert_param(UARTx != NULL);
    assert_param(uart9Bit != NULL);

    regTemp = UART0_LCR_EXT_DLS_E_Msk | uart9Bit->receiveMode_9Bit | uart9Bit->tranmitMode_9Bit;
    WRITE_REG(UARTx->LCR_EXT, regTemp);

    if (uart9Bit->receiveMode_9Bit == UART_9BIT_RCVR_HW)
    {
        UART_setReceiveAddress(UARTx, uart9Bit->RCVRMatchAddress);
    }

    if (uart9Bit->tranmitMode_9Bit == UART_9BIT_XMIT_HW)
    {
        UART_setTransferAddress(UARTx, uart9Bit->XMITSelfAddress);
    }
}

/**
 * @brief Config RS485 RE Assert turn to DE assert time(uart clock) and DE Assert turn to RE assert time(uart clock),
 *         Only be used in RS485 Half Duplex mode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param DEAssertLevel: DE sign assert time(uart clock).
 * @param REAssertLevel: RE sign assert time(uart clock).
 * @retval void
 */
void UART_setTATTiming(UART_Type *UARTx, uint32_t DE2ReTurnAroundTime, \
                       uint32_t RE2DeTurnAroundTime)
{
    assert_param(UARTx != NULL);

    CLEAR_REG(UARTx->TAT);
    WRITE_REG(UARTx->TAT, (UART_REG_TAT_DE2RE((uint32_t)DE2ReTurnAroundTime) | \
                           UART_REG_TAT_RE2DE((uint32_t)RE2DeTurnAroundTime)));
}

/**
 * @brief Config RS485 RE/DE sign assert time(uart clock).
 * @param UARTx: Pointer to UARTx Base addr
 * @param DEAssertLevel: DE sign assert time(uart clock).
 * @param REAssertLevel: RE sign assert time(uart clock).
 * @retval void
 */
void UART_setDETTiming(UART_Type *UARTx, uint32_t DEAssertTime, uint32_t DEDeAssertTime)
{
    assert_param(UARTx != NULL);

    CLEAR_REG(UARTx->DET);
    WRITE_REG(UARTx->DET, (UART_REG_DET_DE_ASSERTION_TIME((uint32_t)DEAssertTime) | \
                           UART_REG_DET_DE_DEASSERTION_TIME((uint32_t)DEDeAssertTime)));
}

/**
 * @brief Config RS485 RE/DE sign assert level.
 * @param UARTx: Pointer to UARTx Base addr
 * @param DEAssertLevel: DE sign assert level
 * @param REAssertLevel: RE sign assert level
 * @retval void
 */
void UART_RS485_DEREPolarityConfig(UART_Type *UARTx, UART_RS485_DEPolarity DEAssertLevel, \
                                   UART_RS485_REPolarity REAssertLevel)
{
    assert_param(UARTx != NULL);

    MODIFY_REG(UARTx->TCR, (UART0_TCR_DE_POL_Msk | UART0_TCR_RE_POL_Msk), \
               ((uint32_t)DEAssertLevel | (uint32_t)REAssertLevel));
}

/**
 * @brief Set RS485 RE sign status.SET to assert, Reset to deassert.
 * @param UARTx: Pointer to UARTx Base addr
 * @param RESignStatus: RE sign status
 * @retval void
 */
void UART_RS485_setDESign(UART_Type *UARTx, RS485AssertType DESignStatus)
{
    assert_param(UARTx != NULL);

    if (DESignStatus == ASSERT)
    {
        SET_BIT(UARTx->DE_EN, UART0_DE_EN_DE_ENABLE_Msk);
    }
    else
    {
        CLEAR_BIT(UARTx->DE_EN, UART0_DE_EN_DE_ENABLE_Msk);
    }
}

/**
 * @brief Set RS485 RE sign status.SET to assert, Reset to deassert.
 * @param UARTx: Pointer to UARTx Base addr
 * @param RESignStatus: RE sign status
 * @retval void
 */
void UART_RS485_setRESign(UART_Type *UARTx, RS485AssertType RESignStatus)
{
    assert_param(UARTx != NULL);

    if (RESignStatus == ASSERT)
    {
        SET_BIT(UARTx->RE_EN, UART0_RE_EN_RE_ENABLE_Msk);
    }
    else
    {
        CLEAR_BIT(UARTx->RE_EN, UART0_RE_EN_RE_ENABLE_Msk);
    }
}

uint16_t UART_RS485_transfer(UART_Type *UARTx, uint8_t *data, uint16_t size)
{
    uint16_t ret;

    UART_RS485_setRESign(UARTx, DEASSERT);
    UART_RS485_setDESign(UARTx, ASSERT);
    ret = UART_transmitWithFIFO(UARTx, data, size, UART_BLOCK_TRANSMIT_FIFO);
    UART_RS485_setDESign(UARTx, DEASSERT);
    UART_RS485_setRESign(UARTx, ASSERT);

    return ret;
}

uint16_t UART_RS485_receive(UART_Type *UARTx, uint8_t *data, uint16_t size)
{
    uint16_t ret;

    UART_RS485_setRESign(UARTx, ASSERT);
    UART_RS485_setDESign(UARTx, DEASSERT);
    ret = UART_receiveWithFIFO(UARTx, data, size);

    return ret;
}

/**
 * @brief Configure the UART RS485 Type: 1.Full Duplex(RS422) 2.Half Duplex in software 3.Half Duplex in hardware
 * @param UARTx: Pointer to UARTx Base addr
 * @param RS485Type: RS485 Type(UART_RS485_Mode)
 * @retval void
 */
DRV_Status UART_RS485_setTransferMode(UART_Type *UARTx, UART_RS485_Mode RS485Type)
{
    assert_param(UARTx != NULL);

    if ((RS485Type != UART_RS485_FULL_DUPLEX) && \
        (RS485Type != UART_RS485_HALF_DUPLEX_SW) && \
        (RS485Type != UART_RS485_HALF_DUPLEX_HW))
    {
        return DRV_PARAM_ERR;
    }

    SET_BIT(UARTx->TCR, UART0_TCR_RS485_EN_Msk);

    MODIFY_REG(UARTx->TCR, UART0_TCR_XFER_MODE_Msk, RS485Type);

    return DRV_OK;
}

/**
 * @brief Configure the UART peripheral. Not support SIRmode.
 * @param UARTx: Pointer to UARTx Base addr
 * @param RS485Cfg: Pointer to RS485 priv cfg(UART_RS485_ConfigParams)
 * @retval Driver status
 */
DRV_Status UART_RS485_config(UART_Type *UARTx, UART_RS485_ConfigParams *RS485Cfg)
{
    assert_param(UARTx != NULL);
    assert_param(RS485Cfg != NULL);

    UART_RS485_setTransferMode(UARTx, RS485Cfg->RS485Type);
    UART_RS485_DEREPolarityConfig(UARTx, RS485Cfg->DEAssertLevel, RS485Cfg->REAssertLevel);
    UART_setDETTiming(UARTx, RS485Cfg->DEAssertTime, RS485Cfg->DEDeAssertTime);

    if (RS485Cfg->RS485Type != UART_RS485_FULL_DUPLEX)
    {
        UART_setTATTiming(UARTx, RS485Cfg->DE2RETurnAroundTime, RS485Cfg->RE2DETurnAroundTime);
    }

    return DRV_OK;
}

/**
 * @brief Get UARTx interrupt Flag, Only return the highest level interrupt
 * @param UARTx: Pointer to UARTx Base addr
 * @retval UART IRQ flag in et6x_uart.h
 */
uint32_t UART_getInterruptStatus(UART_Type *UARTx)
{
    uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);

    tmpReg = (READ_REG(UARTx->IIR) & UART0_IIR_IID_Msk);

    switch (tmpReg)
    {
    case UART_REG_IIR_IID_MODEM_STA:
        return UART_IT_MODEM_STATUS_FLAG;

    case UART_REG_IIR_IID_NO_INTERRUPT:
        return UART_IT_NONE;

    case UART_REG_IIR_IID_THR:
        return UART_IT_TRANS_DATA_EMPTY_FLAG;

    case UART_REG_IIR_IID_RECV_AVI:
        return UART_IT_RECV_DATA_AVAILABLE_FLAG;

    case UART_REG_IIR_IID_RECV_LINE:
        return UART_IT_ERROR_FLAG;

    /* This interrupt is used when FIFO is disable, and user try to write when Uart is busy */
    case UART_REG_IIR_IID_BUSY_DETECT:
        return UART_IT_UART_NOFIFO_BUSY;

    case UART_REG_IIR_IID_CHAR_TIMEOUT:
        return UART_IT_CHAR_TIMEOUT_FLAG;
    }

    return UART_IT_NONE;
}

/**
 * @brief Get UARTx interrupt Flag, Only return the highest level interrupt
 * @param UARTx: Pointer to UARTx Base addr
 * @param uartLineFlag: must be one of @ref UART Line status Flag
 * @retval UART IRQ flag in et6x_uart.h
 */
uint32_t UART_getLineStatusFlag(UART_Type *UARTx, uint32_t uartLineFlag)
{
    return _DEF_UART_GET_LINE_STATUS(UARTx, uartLineFlag);
}

/**
 * @brief Clear UARTx interrupt flag, User must read RBR(RX FIFO) by self to clean
 *         UART_IT_RECV_DATA_AVAILABLE_FLAG & UART_IT_CHAR_TIMEOUT_FLAG
 * @param UARTx: Pointer to UARTx Base addr
 * @param uartInterruptFlag: UART IRQ flag in et6x_uart.h
 * @retval void
 */
void UART_clearInterruptStatus(UART_Type *UARTx, uint32_t uartInterruptFlag)
{
    __IO uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);

    switch (uartInterruptFlag)
    {
    case UART_IT_RECV_DATA_AVAILABLE_FLAG:
    case UART_IT_CHAR_TIMEOUT_FLAG:
        break;

    case UART_IT_TRANS_DATA_EMPTY_FLAG:
        tmpReg = READ_REG(UARTx->IIR);
        break;

    case UART_IT_MODEM_STATUS_FLAG:
        tmpReg = READ_REG(UARTx->MSR);
        break;

    case UART_IT_9BITS_ADDR_RESV_FLAG:
    case UART_IT_ERROR_FLAG:
        tmpReg = READ_REG(UARTx->LSR);
        break;

    case UART_IT_UART_NOFIFO_BUSY:
        tmpReg = READ_REG(UARTx->USR);
        break;
    }

    UNUSED(tmpReg);
}

/**
 * @brief Enable UARTx interrupt, User can select interrupt source by
 * @param UARTx: Pointer to UARTx Base addr
 * @param uartInterruptFlag: UART IRQ flag in et6x_uart.h
 * @retval void
 */
void UART_enableInterrupt(UART_Type *UARTx, uint32_t uartInterruptFlag)
{
    __IO uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);

    /* Divisior Latch Register Only Can Be Written LCR_DLAB Is Set */
    CLEAR_BIT(UARTx->LCR, UART0_LCR_DLAB_Msk);

    tmpReg = READ_REG(UARTx->IER);

    if (uartInterruptFlag & UART_IT_RECV_DATA_AVAILABLE_FLAG)
    {
        tmpReg |= UART0_IER_ERBFI_Msk;
    }

    if (uartInterruptFlag & UART_IT_TRANS_DATA_EMPTY_FLAG)
    {
        tmpReg |= UART0_IER_ETBEI_Msk;
    }


    if (uartInterruptFlag & UART_IT_MODEM_STATUS_FLAG)
    {
        tmpReg |= UART0_IER_EDSSI_Msk;
    }

    if (uartInterruptFlag & UART_IT_CHAR_TIMEOUT_FLAG)
    {
        tmpReg |= UART0_IER_ERBFI_Msk;
    }

    if (uartInterruptFlag & UART_IT_9BITS_ADDR_RESV_FLAG)
    {
        tmpReg |= UART0_IER_ELCOLR_Msk | UART0_IER_ELSI_Msk;
    }

    if (uartInterruptFlag & UART_IT_ERROR_FLAG)
    {
        tmpReg |= UART0_IER_ELCOLR_Msk | UART0_IER_ELSI_Msk;
    }

    if (uartInterruptFlag & UART_IT_PROMGRAM_THRE_FLAG)
    {
        tmpReg |= UART0_IER_PTIME_Msk;
    }

    WRITE_REG(UARTx->IER, tmpReg);

    /* clear Interrupt Flag */
    tmpReg = READ_REG(UARTx->MSR);
    tmpReg = READ_REG(UARTx->LSR);
    tmpReg = READ_REG(UARTx->IIR);
}

void UART_disableInterrupt(UART_Type *UARTx, uint32_t uartInterruptFlag)
{
    __IO uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);

    /* Divisor Latch Register Only Can Be Written LCR_DLAB Is Set */
    CLEAR_BIT(UARTx->LCR, UART0_LCR_DLAB_Msk);

    tmpReg = READ_REG(UARTx->IER);

    if (uartInterruptFlag & UART_IT_RECV_DATA_AVAILABLE_FLAG)
    {
        tmpReg &= ~(UART0_IER_ERBFI_Msk);
    }

    if (uartInterruptFlag & UART_IT_TRANS_DATA_EMPTY_FLAG)
    {
        tmpReg &= ~(UART0_IER_ETBEI_Msk);
    }


    if (uartInterruptFlag & UART_IT_MODEM_STATUS_FLAG)
    {
        tmpReg &= ~(UART0_IER_EDSSI_Msk);
    }

    if (uartInterruptFlag & UART_IT_CHAR_TIMEOUT_FLAG)
    {
        tmpReg &= ~(UART0_IER_ERBFI_Msk);
    }

    if (uartInterruptFlag & UART_IT_9BITS_ADDR_RESV_FLAG)
    {
        tmpReg &= ~(UART0_IER_ELCOLR_Msk | UART0_IER_ELSI_Msk);
    }

    if (uartInterruptFlag & UART_IT_ERROR_FLAG)
    {
        tmpReg &= ~(UART0_IER_ELCOLR_Msk | UART0_IER_ELSI_Msk);
    }

    if (uartInterruptFlag & UART_IT_PROMGRAM_THRE_FLAG)
    {
        tmpReg &= ~(UART0_IER_PTIME_Msk);
    }

    WRITE_REG(UARTx->IER, tmpReg);
}

/**
 * @brief Enable UARTx Hard-Ware flow ctrl.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_enableHWFlowMode(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    SET_BIT(UARTx->MCR, UART0_MCR_AFCE_Msk);
}

/**
 * @brief Disable UARTx Hard-Ware flow ctrl.
 * @param UARTx: Pointer to UARTx Base addr
 * @retval void
 */
void UART_disableHWFlowMode(UART_Type *UARTx)
{
    assert_param(UARTx != NULL);

    CLEAR_BIT(UARTx->MCR, UART0_MCR_AFCE_Msk);
}

DRV_Status UART_configDMA(UART_Type *UARTx, UART_DMAMode DMAMode, \
                          UART_TXFIFOThreshold TXFIFOThreshold,
                          UART_RXFIFOThreshold RXFIFOThreshold)
{
    uint32_t tmpReg = 0;

    assert_param(UARTx != NULL);

    /* Check Uart init Param */
    if ((TXFIFOThreshold != UART_TXFIFO_THRESHOLD_0BYTES) && \
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_2BYTES) && \
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_4BYTES) && \
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_8BYTES))
    {
        return DRV_PARAM_ERR;
    }

    if ((RXFIFOThreshold != UART_RXFIFO_THRESHOLD_1BYTES) && \
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_4BYTES) && \
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_8BYTES) && \
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_14BYTES))
    {
        return DRV_PARAM_ERR;
    }

    if ((DMAMode != UART_DMA_DISABLE) && \
        (DMAMode != UART_DMA_SINGLE_MODE) && \
        (DMAMode != UART_DMA_MULTI_MODE))
    {
        return DRV_PARAM_ERR;
    }

    tmpReg = UART0_FCR_FIFOE_Msk | TXFIFOThreshold | RXFIFOThreshold | \
             UART0_FCR_RFIFOR_Msk | UART0_FCR_XFIFOR_Msk;

    if (DMAMode == UART_DMA_MULTI_MODE)
    {
        tmpReg |= UART0_FCR_DMAM_Msk;
    }

    WRITE_REG(UARTx->FCR, tmpReg);

    return DRV_OK;
}

void UART_initConfigParams(UART_ConfigParams *init)
{
    memset(init, 0, sizeof(UART_ConfigParams));

    init->baudRate        = 9600;
    init->wordLength      = UART_WORDLENGTH_8B;
    init->stopBits        = UART_STOPBITS_1;
    init->parity          = UART_PARITY_NONE;
    init->mode            = UART_MODE_NORMAL;
    init->DMAMode         = UART_DMA_DISABLE;
    init->irqEnableFlag   = UART_IT_NONE;
    init->hwFlowCtl       = UART_HWFLOW_DISABLE;
    init->TXFIFOThreshold = UART_TXFIFO_THRESHOLD_8BYTES;
    init->RXFIFOThreshold = UART_RXFIFO_THRESHOLD_1BYTES;
}

DRV_Status UART_config(UART_Type *UARTx, UART_ConfigParams *init)
{
    DRV_Status rst = DRV_OK;

    assert_param(IS_UART_INSTANCE(UARTx));

    /* Reset the Peripheral */
    _DEF_UART_RESET(UARTx);

    if (init->mode & UART_MODE_9BIT)
    {
        UART_config9BitMode(UARTx, &init->advancedInit.uart9Bit);
    }

    if (init->mode & UART_MODE_IrDA1_0_SIR)
    {
        UART_enableSIRMode(UARTx);
    }

    if (init->hwFlowCtl == UART_HWFLOW_ENABLE)
    {
        UART_enableHWFlowMode(UARTx);
    }

    if (init->mode & UART_MODE_IrDA1_0_LP_SIR)
    {
        rst = UART_configSIRLowPowerMode(UARTx);
        if (rst != DRV_OK)
        {
            UART_performSoftwareReset(UARTx);
            return rst;
        }
    }
    else
    {
        rst = UART_setBaudrate(UARTx, init->baudRate);
        if (rst != DRV_OK)
        {
            UART_performSoftwareReset(UARTx);
            return rst;
        }
    }

    /* Communication config has no effect in SIR Mode */
    if ((init->mode != UART_MODE_IrDA1_0_SIR) && \
        (init->mode != UART_MODE_IrDA1_0_LP_SIR))
    {
        /* Set the UART Communication parameters */
        rst = UART_setLineConfig(UARTx, init->wordLength, init->stopBits, init->parity);
        if (rst != DRV_OK)
        {
            UART_performSoftwareReset(UARTx);
            return rst;
        }
    }

    rst = UART_configDMA(UARTx, init->DMAMode, init->TXFIFOThreshold, init->RXFIFOThreshold);
    if (rst != DRV_OK)
    {
        UART_performSoftwareReset(UARTx);
        return rst;
    }

    if (init->mode & UART_MODE_LOOPBACK)
    {
        SET_BIT(UARTx->MCR, UART0_MCR_LOOPBACK_Msk);
    }

    if (init->mode & UART_MODE_RS485)
    {
        UART_RS485_config(UARTx, &(init->advancedInit.RS485));
    }

    if (init->irqEnableFlag != UART_IT_NONE)
    {
        UART_enableInterrupt(UARTx, init->irqEnableFlag);
    }

    return rst;
}

DRV_Status UART_performSoftwareReset(UART_Type *UARTx)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    /* Reset the Peripheral */
    _DEF_UART_RESET(UARTx);

    return DRV_OK;
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Get the UART transmit DMA endpoint address for validation firmware.
 * @param UARTx Pointer to UARTx base address
 * @param address Pointer used to return the endpoint address
 * @return DRV_Status
 */
DRV_Status UART_testGetTxDMAEndpointAddress(UART_Type *UARTx,
                                            uintptr_t *address)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (address == NULL))
    {
        return DRV_PARAM_ERR;
    }

    *address = (uintptr_t)&UARTx->THR;
    return DRV_OK;
}

/**
 * @brief Get the UART receive DMA endpoint address for validation firmware.
 * @param UARTx Pointer to UARTx base address
 * @param address Pointer used to return the endpoint address
 * @return DRV_Status
 */
DRV_Status UART_testGetRxDMAEndpointAddress(UART_Type *UARTx,
                                            uintptr_t *address)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (address == NULL))
    {
        return DRV_PARAM_ERR;
    }

    *address = (uintptr_t)&UARTx->RBR;
    return DRV_OK;
}

/**
 * @brief Capture component identification and scratch state for validation.
 */
DRV_Status UART_testGetComponentSnapshot(
    UART_Type *UARTx,
    UART_TestComponentSnapshot_TypeDef *snapshot)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (snapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }

    snapshot->componentParameter = READ_REG(UARTx->CPR);
    snapshot->componentVersion = READ_REG(UARTx->UCV);
    snapshot->componentType = READ_REG(UARTx->CTR);
    snapshot->scratch = READ_REG(UARTx->SCR);
    return DRV_OK;
}

/**
 * @brief Capture interrupt, line, modem, FIFO and UART status for validation.
 */
DRV_Status UART_testGetStatusSnapshot(
    UART_Type *UARTx,
    UART_TestStatusSnapshot_TypeDef *snapshot)
{
    const uint32_t lineStatusMask =
        UART_LINE_STA_DR_FLAG |
        UART_LINE_STA_OE_FLAG |
        UART_LINE_STA_PE_FLAG |
        UART_LINE_STA_FE_FLAG |
        UART_LINE_STA_BI_FLAG |
        UART_LINE_STA_THRE_FLAG |
        UART_LINE_STA_TEMT_FLAG |
        UART0_LSR_RFE_Msk |
        UART_LINE_STA_ADDR_RCVD_FLAG;

    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (snapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }

    snapshot->interruptStatus = UART_getInterruptStatus(UARTx);
    snapshot->lineStatus = UART_getLineStatusFlag(UARTx, lineStatusMask);
    snapshot->modemStatus = READ_REG(UARTx->MSR);
    snapshot->modemControl = READ_REG(UARTx->MCR);
    snapshot->uartStatus = READ_REG(UARTx->USR);
    snapshot->txFifoLevel = UART_getTxFIFOStatus(UARTx);
    snapshot->rxFifoLevel = UART_getRxFIFOStatus(UARTx);
    return DRV_OK;
}

/**
 * @brief Capture and resolve one interrupt together with read-clear line state.
 */
DRV_Status UART_testGetInterruptSnapshot(
    UART_Type *UARTx,
    UART_TestInterruptSnapshot_TypeDef *snapshot)
{
    const uint32_t lineStatusMask =
        UART_LINE_STA_DR_FLAG |
        UART_LINE_STA_OE_FLAG |
        UART_LINE_STA_PE_FLAG |
        UART_LINE_STA_FE_FLAG |
        UART_LINE_STA_BI_FLAG |
        UART_LINE_STA_THRE_FLAG |
        UART_LINE_STA_TEMT_FLAG |
        UART0_LSR_RFE_Msk |
        UART_LINE_STA_ADDR_RCVD_FLAG;
    const uint32_t errorStatusMask =
        UART_LINE_STA_OE_FLAG |
        UART_LINE_STA_PE_FLAG |
        UART_LINE_STA_FE_FLAG |
        UART_LINE_STA_BI_FLAG |
        UART0_LSR_RFE_Msk;

    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (snapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }

    snapshot->interruptStatus = UART_getInterruptStatus(UARTx);
    snapshot->lineStatus = UART_getLineStatusFlag(UARTx, lineStatusMask);
    snapshot->resolvedInterruptStatus = snapshot->interruptStatus;

    if ((snapshot->lineStatus & UART_LINE_STA_ADDR_RCVD_FLAG) != 0U)
    {
        snapshot->resolvedInterruptStatus |= UART_IT_9BITS_ADDR_RESV_FLAG;
        if ((snapshot->interruptStatus == UART_IT_ERROR_FLAG) &&
            ((snapshot->lineStatus & errorStatusMask) == 0U))
        {
            snapshot->resolvedInterruptStatus &= ~UART_IT_ERROR_FLAG;
        }
    }

    return DRV_OK;
}

/**
 * @brief Configure FIFO enable state and trigger levels for validation.
 */
DRV_Status UART_testConfigureFIFO(
    UART_Type *UARTx,
    uint8_t enabled,
    UART_TXFIFOThreshold TXFIFOThreshold,
    UART_RXFIFOThreshold RXFIFOThreshold)
{
    uint32_t fifoControl;

    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u))
    {
        return DRV_PARAM_ERR;
    }
    if ((TXFIFOThreshold != UART_TXFIFO_THRESHOLD_0BYTES) &&
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_2BYTES) &&
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_4BYTES) &&
        (TXFIFOThreshold != UART_TXFIFO_THRESHOLD_8BYTES))
    {
        return DRV_PARAM_ERR;
    }
    if ((RXFIFOThreshold != UART_RXFIFO_THRESHOLD_1BYTES) &&
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_4BYTES) &&
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_8BYTES) &&
        (RXFIFOThreshold != UART_RXFIFO_THRESHOLD_14BYTES))
    {
        return DRV_PARAM_ERR;
    }

    fifoControl = (uint32_t)TXFIFOThreshold | (uint32_t)RXFIFOThreshold;
    if (enabled != 0u)
    {
        fifoControl |= UART0_FCR_FIFOE_Msk;
    }
    fifoControl |= UART0_FCR_RFIFOR_Msk | UART0_FCR_XFIFOR_Msk;
    WRITE_REG(UARTx->FCR, fifoControl);
    return DRV_OK;
}

/**
 * @brief Set the UART internal loopback bit for validation.
 */
DRV_Status UART_testSetLoopback(UART_Type *UARTx, uint8_t enabled)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u))
    {
        return DRV_PARAM_ERR;
    }
    if (enabled != 0u)
    {
        SET_BIT(UARTx->MCR, UART0_MCR_LOOPBACK_Msk);
    }
    else
    {
        CLEAR_BIT(UARTx->MCR, UART0_MCR_LOOPBACK_Msk);
    }
    return DRV_OK;
}

/**
 * @brief Set or clear the UART break-control bit for validation.
 */
DRV_Status UART_testSetBreak(UART_Type *UARTx, uint8_t enabled)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u))
    {
        return DRV_PARAM_ERR;
    }
    if (enabled != 0u)
    {
        SET_BIT(UARTx->LCR, UART0_LCR_BC_Msk);
    }
    else
    {
        CLEAR_BIT(UARTx->LCR, UART0_LCR_BC_Msk);
    }
    return DRV_OK;
}

/**
 * @brief Enable or disable the UART 9-bit data-length extension.
 */
DRV_Status UART_testSetNineBitEnabled(UART_Type *UARTx, uint8_t enabled)
{
    assert_param(IS_UART_INSTANCE(UARTx));

    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u))
    {
        return DRV_PARAM_ERR;
    }
    if (enabled != 0u)
    {
        SET_BIT(UARTx->LCR_EXT, UART0_LCR_EXT_DLS_E_Msk);
    }
    else
    {
        CLEAR_BIT(
            UARTx->LCR_EXT,
            UART0_LCR_EXT_DLS_E_Msk | UART0_LCR_EXT_SEND_ADDR_Msk);
    }
    return DRV_OK;
}

#define UART_TEST_BUSY_POLL_LIMIT (100000u)

/**
 * @brief Atomically construct and recover one no-FIFO Busy Detect event.
 *
 * Busy Detect is only defined for a FIFO-disabled UART.  The helper keeps the
 * trigger bounded, reads USR to clear the event, restores the caller's
 * line/interrupt state, and leaves the UART in the validation-safe default
 * FIFO state (enabled, reset asserted, TX threshold 0, RX threshold 1).
 */
DRV_Status UART_testTriggerBusyDetect(
    UART_Type *UARTx,
    UART_TestBusyDetectResult_TypeDef *result)
{
    uint32_t savedLcr;
    uint32_t savedIer;
    uint32_t poll;
    uint32_t iir;
    uint32_t usr;
    uint32_t clearUsr;
    uint8_t byte = 0xA5u;
    DRV_Status status = DRV_OK;

    assert_param(IS_UART_INSTANCE(UARTx));
    if ((!IS_UART_INSTANCE(UARTx)) || (result == NULL))
    {
        return DRV_PARAM_ERR;
    }

    (void)memset(result, 0, sizeof(*result));
    savedLcr = READ_REG(UARTx->LCR);
    savedIer = READ_REG(UARTx->IER);
    result->preTriggerUsr = READ_REG(UARTx->USR);

    /* Disable and reset both FIFOs before the single-byte trigger. */
    WRITE_REG(UARTx->FCR, UART0_FCR_RFIFOR_Msk | UART0_FCR_XFIFOR_Msk);
    WRITE_REG(UARTx->FCR, 0u);
    if (UART_transmit(UARTx, &byte, 1u, UART_NON_BLOCK_TRANSMIT_FIFO) != 1u)
    {
        status = DRV_TIMEOUT;
        goto restore;
    }

    for (poll = 0u; poll < UART_TEST_BUSY_POLL_LIMIT; ++poll)
    {
        usr = READ_REG(UARTx->USR);
        if ((usr & UART0_USR_BUSY_Msk) != 0u)
        {
            result->busyObserved = 1u;
            break;
        }
    }
    if (result->busyObserved == 0u)
    {
        status = DRV_TIMEOUT;
        goto restore;
    }

    /* UART_setLineConfig performs the guarded LCR write that triggers Busy. */
    (void)UART_setLineConfig(
        UARTx,
        UART_WORDLENGTH_8B,
        UART_STOPBITS_1,
        UART_PARITY_NONE);
    iir = READ_REG(UARTx->IIR);
    usr = READ_REG(UARTx->USR);
    result->observedIir = iir;
    result->observedUsr = usr;
    if ((iir & UART0_IIR_IID_Msk) == UART_REG_IIR_IID_BUSY_DETECT)
    {
        result->interruptObserved = 1u;
        result->triggerCount = 1u;
    }
    else
    {
        status = DRV_TIMEOUT;
    }

    /* The documented clear operation is a read of USR. */
    clearUsr = READ_REG(UARTx->USR);
    UNUSED(clearUsr);
    result->cleared =
        ((READ_REG(UARTx->IIR) & UART0_IIR_IID_Msk) !=
         UART_REG_IIR_IID_BUSY_DETECT) ? 1u : 0u;

    for (poll = 0u; poll < UART_TEST_BUSY_POLL_LIMIT; ++poll)
    {
        if ((READ_REG(UARTx->USR) & UART0_USR_BUSY_Msk) == 0u)
        {
            break;
        }
    }
    if (poll == UART_TEST_BUSY_POLL_LIMIT)
    {
        status = DRV_TIMEOUT;
    }

restore:
    /* FCR is a write-only command register (IIR is its read alias).  Do not
     * read it for save/restore.  End with an explicit known-good FIFO state:
     * enabled, both FIFOs reset, TX threshold 0, RX threshold 1. */
    WRITE_REG(
        UARTx->FCR,
        UART0_FCR_FIFOE_Msk | UART0_FCR_RFIFOR_Msk | UART0_FCR_XFIFOR_Msk);
    WRITE_REG(UARTx->LCR, savedLcr);
    WRITE_REG(UARTx->IER, savedIer);
    if (UART_waitTransmitDone(UARTx, UART_TEST_BUSY_POLL_LIMIT) == DRV_OK)
    {
        result->recovered = 1u;
    }
    else
    {
        status = DRV_TIMEOUT;
    }
    return status;
}

static uint8_t UART_testTxThresholdBytes(UART_TXFIFOThreshold threshold)
{
    switch (threshold)
    {
    case UART_TXFIFO_THRESHOLD_0BYTES:
        return 0u;
    case UART_TXFIFO_THRESHOLD_2BYTES:
        return 2u;
    case UART_TXFIFO_THRESHOLD_4BYTES:
        return 4u;
    case UART_TXFIFO_THRESHOLD_8BYTES:
        return 8u;
    default:
        return 0xffu;
    }
}

static uint8_t UART_testRxThresholdBytes(UART_RXFIFOThreshold threshold)
{
    switch (threshold)
    {
    case UART_RXFIFO_THRESHOLD_1BYTES:
        return 1u;
    case UART_RXFIFO_THRESHOLD_4BYTES:
        return 4u;
    case UART_RXFIFO_THRESHOLD_8BYTES:
        return 8u;
    case UART_RXFIFO_THRESHOLD_14BYTES:
        return 14u;
    default:
        return 0xffu;
    }
}

static uint8_t UART_testTxThresholdFromRegister(uint32_t value)
{
    switch (value & UART0_STET_STET_Msk)
    {
    case 0u:
        return 0u;
    case 1u:
        return 2u;
    case 2u:
        return 4u;
    case 3u:
        return 8u;
    default:
        return 0xffu;
    }
}

static uint8_t UART_testRxThresholdFromRegister(uint32_t value)
{
    switch (value & UART0_SRT_SRT_Msk)
    {
    case 0u:
        return 1u;
    case 1u:
        return 4u;
    case 2u:
        return 8u;
    case 3u:
        return 14u;
    default:
        return 0xffu;
    }
}

/** @brief Configure SFE/SRT/STET when CPR declares the shadow feature. */
DRV_Status UART_testConfigureShadowFIFO(
    UART_Type *UARTx,
    uint8_t enabled,
    UART_TXFIFOThreshold TXFIFOThreshold,
    UART_RXFIFOThreshold RXFIFOThreshold,
    UART_TestShadowFIFOState_TypeDef *state)
{
    uint8_t txBytes;
    uint8_t rxBytes;

    assert_param(IS_UART_INSTANCE(UARTx));
    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u) || (state == NULL))
    {
        return DRV_PARAM_ERR;
    }
    if ((READ_REG(UARTx->CPR) & UART_TEST_CPR_SHADOW_Msk) == 0u)
    {
        return DRV_INVALID;
    }
    txBytes = UART_testTxThresholdBytes(TXFIFOThreshold);
    rxBytes = UART_testRxThresholdBytes(RXFIFOThreshold);
    if ((txBytes == 0xffu) || (rxBytes == 0xffu))
    {
        return DRV_PARAM_ERR;
    }

    WRITE_REG(UARTx->SFE, (enabled != 0u) ? UART0_SFE_SFE_Msk : 0u);
    WRITE_REG(
        UARTx->SRT,
        ((uint32_t)RXFIFOThreshold & UART0_FCR_RT_Msk) >> UART0_FCR_RT_Pos);
    WRITE_REG(
        UARTx->STET,
        ((uint32_t)TXFIFOThreshold & UART0_FCR_TET_Msk) >> UART0_FCR_TET_Pos);
    state->enabled =
        ((READ_REG(UARTx->SFE) & UART0_SFE_SFE_Msk) != 0u) ? 1u : 0u;
    state->txThreshold =
        UART_testTxThresholdFromRegister(READ_REG(UARTx->STET));
    state->rxThreshold =
        UART_testRxThresholdFromRegister(READ_REG(UARTx->SRT));
    if ((state->txThreshold == 0xffu) || (state->rxThreshold == 0xffu))
    {
        return DRV_TIMEOUT;
    }
    state->fifoAccess =
        ((READ_REG(UARTx->FAR) & UART0_FAR_FAR_Msk) != 0u) ? 1u : 0u;
    return DRV_OK;
}

/** @brief Enable or disable FAR FIFO access and return the FAR readback. */
DRV_Status UART_testSetFIFOAccess(
    UART_Type *UARTx,
    uint8_t enabled,
    uint8_t *active)
{
    assert_param(IS_UART_INSTANCE(UARTx));
    if ((!IS_UART_INSTANCE(UARTx)) || (enabled > 1u) || (active == NULL))
    {
        return DRV_PARAM_ERR;
    }
    if ((READ_REG(UARTx->CPR) & UART_TEST_CPR_FIFO_ACCESS_Msk) == 0u)
    {
        return DRV_INVALID;
    }
    WRITE_REG(UARTx->FAR, (enabled != 0u) ? UART0_FAR_FAR_Msk : 0u);
    *active =
        ((READ_REG(UARTx->FAR) & UART0_FAR_FAR_Msk) != 0u) ? 1u : 0u;
    return DRV_OK;
}

/** @brief Read one TX FIFO item through TFR in FAR access mode. */
DRV_Status UART_testReadTxFIFO(UART_Type *UARTx, uint8_t *value)
{
    assert_param(IS_UART_INSTANCE(UARTx));
    if ((!IS_UART_INSTANCE(UARTx)) || (value == NULL))
    {
        return DRV_PARAM_ERR;
    }
    if ((READ_REG(UARTx->CPR) & UART_TEST_CPR_FIFO_ACCESS_Msk) == 0u)
    {
        return DRV_INVALID;
    }
    if ((READ_REG(UARTx->FAR) & UART0_FAR_FAR_Msk) == 0u)
    {
        return DRV_BUSY;
    }
    *value = (uint8_t)(READ_REG(UARTx->TFR) & UART0_TFR_TFR_Msk);
    return DRV_OK;
}

/** @brief Inject one RX FIFO item through RFW in FAR access mode. */
DRV_Status UART_testWriteRxFIFO(
    UART_Type *UARTx,
    uint8_t value,
    uint8_t parityError,
    uint8_t framingError)
{
    uint32_t fifoWord;

    assert_param(IS_UART_INSTANCE(UARTx));
    if ((!IS_UART_INSTANCE(UARTx)) ||
        (parityError > 1u) || (framingError > 1u))
    {
        return DRV_PARAM_ERR;
    }
    if ((READ_REG(UARTx->CPR) & UART_TEST_CPR_FIFO_ACCESS_Msk) == 0u)
    {
        return DRV_INVALID;
    }
    if ((READ_REG(UARTx->FAR) & UART0_FAR_FAR_Msk) == 0u)
    {
        return DRV_BUSY;
    }
    fifoWord = (uint32_t)value;
    if (parityError != 0u)
    {
        fifoWord |= UART0_RFW_RFPE_Msk;
    }
    if (framingError != 0u)
    {
        fifoWord |= UART0_RFW_RFFE_Msk;
    }
    WRITE_REG(UARTx->RFW, fifoWord);
    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/**
 * @}
 */

/************************ (C) COPYRIGHT ETMCU *************END OF FILE****/
