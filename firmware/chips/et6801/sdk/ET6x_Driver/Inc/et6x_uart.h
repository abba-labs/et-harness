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

#ifndef __ET6x_UART_H
#define __ET6x_UART_H

#include "et6x.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup UART
 * @{
 */

/** @defgroup UART_Config_Constants UART Config Constants
 * @{
 */

/**
 * @brief The maximum Uart baud rate config.
 */
#define UART_BAUDRATE_MAX    (3000000)

/**
 * @}
 */


/** @defgroup UART_Public_Constants UART Public Constants
 * @{
 */

#define UART_FIFO_DEPTH                     (16)           /*!< UART FIFO Depth, can not change */
#define UART_LOW_POWER_SIR_BAUDRATE         (115200)       /*!< UART Baudrate in Low Power SIR mode, can not change */

/** @defgroup UART_IT_flag UART IRQ flag
 * @{
 */
#define UART_IT_NONE                        (0x0)
#define UART_IT_RECV_DATA_AVAILABLE_FLAG    (0x1UL << 0)
#define UART_IT_TRANS_DATA_EMPTY_FLAG       (0x1UL << 1)
#define UART_IT_MODEM_STATUS_FLAG           (0x1UL << 2)
#define UART_IT_CHAR_TIMEOUT_FLAG           (0x1UL << 3)
#define UART_IT_9BITS_ADDR_RESV_FLAG        (0x1UL << 4)
#define UART_IT_ERROR_FLAG                  (0x1UL << 5)
#define UART_IT_PROMGRAM_THRE_FLAG          (0x1UL << 6)
#define UART_IT_UART_NOFIFO_BUSY            (0x1UL << 7)

/**
 * @}
 */

/** @defgroup UART_status_Flag UART status Flag
 * @{
 */
#define UART_STA_BUSY_FLAG    (UART0_USR_BUSY_Msk)                 /*!< UART Busy Flag */
#define UART_STA_TFNF_FLAG    (UART0_USR_TFNF_Msk)                 /*!< Transmit FIFO Not Full Flag */
#define UART_STA_TFE_FLAG     (UART0_USR_TFE_Msk)                  /*!< Transmit FIFO Empty Flag */
#define UART_STA_RFNE_FLAG    (UART0_USR_RFNE_Msk)                 /*!< Receive FIFO Not Empty Flag */
#define UART_STA_RFF_FLAG     (UART0_USR_RFF_Msk)                  /*!< Receive FIFO Full Flag */
#define UART_STA_ALL \
        (UART0_USR_BUSY_Msk | UART0_USR_TFNF_Msk | UART0_USR_TFE_Msk | \
         UART0_USR_RFNE_Msk | UART0_USR_RFF_Msk)                                      /*!< All flag mask. For
                                                                                       * 'UART_getInterruptStatus' */

/**
 * @}
 */

/** @defgroup UART_Line_status_Flag UART Line status Flag
 * @{
 */
#define UART_LINE_STA_DR_FLAG           (UART0_LSR_DR_Msk)                  /*!< Data Ready bit */
#define UART_LINE_STA_OE_FLAG           (UART0_LSR_OE_Msk)                  /*!< Overrun error bit */
#define UART_LINE_STA_PE_FLAG           (UART0_LSR_PE_Msk)                  /*!< Parity Error bit */
#define UART_LINE_STA_FE_FLAG           (UART0_LSR_FE_Msk)                  /*!< Framing Error bit */
#define UART_LINE_STA_BI_FLAG           (UART0_LSR_BI_Msk)                  /*!< Break Interrupt bit */
#define UART_LINE_STA_THRE_FLAG         (UART0_LSR_THRE_Msk)                /*!< Transmit Holding Register Empty bit
                                                                             */
#define UART_LINE_STA_TEMT_FLAG         (UART0_LSR_TEMT_Msk)                /*!< Transmitter Empty bit */
#define UART_LINE_STA_REF_FLAG          (UART0_LSR_REF_Msk)                 /*!< Receiver FIFO Error bit */
#define UART_LINE_STA_ADDR_RCVD_FLAG    (UART0_LSR_ADDR_RCVD_Msk)           /*!< Address Received Bit */
#define UART_LINE_STA_ALL \
        (UART0_LSR_DR_Msk | \
         UART0_LSR_OE_Msk | \
         UART0_LSR_PE_Msk | \
         UART0_LSR_FE_Msk | \
         UART0_LSR_BI_Msk | \
         UART0_LSR_THRE_Msk | \
         UART0_LSR_TEMT_Msk | \
         UART0_LSR_REF_Msk | \
         UART0_LSR_ADDR_RCVD_Msk)                                                 /*!< All flag mask. For
                                                                                   * 'UART_getLineStatusFlag' */

/**
 * @}
 */

/**
 * @}
 */

/** @defgroup UART_Public_Macros UART Public Macros
 * @{
 */
#define UART_REG_LCR_DLS(__Val__) \
        (((__Val__) << UART0_LCR_DLS_Pos) \
         &UART0_LCR_DLS_Msk)                                                     /*!<  select the number of data bits
                                                                                  * per character */


#define UART_REG_TCR_XFER_MODE(__MODE__) \
        (((__MODE__) << UART0_TCR_XFER_MODE_Pos) \
         &UART0_TCR_XFER_MODE_Msk)

#define UART_REG_TAT_DE2RE(__TICK__)    (((__TICK__) << UART0_TAT_DE_TO_RE_Pos)&UART0_TAT_DE_TO_RE_Msk)

#define UART_REG_TAT_RE2DE(__TICK__)    (((__TICK__) << UART0_TAT_RE_TO_DE_Pos)&UART0_TAT_RE_TO_DE_Msk)


#define UART_REG_DET_DE_ASSERTION_TIME(__TICK__) \
        (((__TICK__) << UART0_DET_DE_ASSERTION_TIME_Pos) \
         &UART0_DET_DE_ASSERTION_TIME_Msk)

#define UART_REG_DET_DE_DEASSERTION_TIME(__TICK__) \
        (((__TICK__) << UART0_DET_DE_ASSERTION_TIME_Pos) \
         &UART0_DET_DE_ASSERTION_TIME_Msk)


#define UART_REG_FCR_TET_EMPTY             (0x0UL << UART0_FCR_TET_Pos)              /*!< THRE Interrupts source */
#define UART_REG_FCR_TET_2CHAR             (0x1UL << UART0_FCR_TET_Pos)
#define UART_REG_FCR_TET_1_4FULL           (0x2UL << UART0_FCR_TET_Pos)
#define UART_REG_FCR_TET_1_2FULL           (0x3UL << UART0_FCR_TET_Pos)

#define UART_REG_FCR_RT_1CHAR_IN_FIFO      (0x0UL << UART0_FCR_RT_Pos)               /*!< Received Data Available
                                                                                      * Interrupt source */
#define UART_REG_FCR_RT_1_4FULL            (0x1UL << UART0_FCR_RT_Pos)
#define UART_REG_FCR_RT_1_2FULL            (0x2UL << UART0_FCR_RT_Pos)
#define UART_REG_FCR_RT_2LESS_THAN_FIFO    (0x3UL << UART0_FCR_RT_Pos)


#define UART_REG_IIR_IID_MODEM_STA         (0x0UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_NO_INTERRUPT      (0x1UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_THR               (0x2UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_RECV_AVI          (0x4UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_RECV_LINE         (0x6UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_BUSY_DETECT       (0x7UL << UART0_IIR_IID_Pos)
#define UART_REG_IIR_IID_CHAR_TIMEOUT      (0xCUL << UART0_IIR_IID_Pos)

/** @brief  Reset UART.
 * @param  __HANDLE__: specifies the UART RegTypeDef Handle.
 * @retval None
 */
#define _DEF_UART_RESET(__HANDLE__) \
        (__HANDLE__->SRR = \
             (UART0_SRR_UR_Msk | UART0_SRR_RFR_Msk | UART0_SRR_XFR_Msk))

/** @brief Get Uart Status.
 * @param  __HuartInstance__: Pointer to Uartx Base addr
 * @param  __UartStaFlag__: must be one of @ref @ref UART status Flag
 * @retval flag status
 */
#define _DEF_UART_GET_UART_STATUS(__HuartInstance__, \
                                  __UartStaFlag__)     (READ_REG(__HuartInstance__->USR) &__UartStaFlag__)

/** @brief Get Uart Line Status.
 * @param  __HuartInstance__: Pointer to Uartx Base addr
 * @param  __UartLineFlag__: must be one of @ref UART Line status Flag
 * @retval flag status
 */
#define _DEF_UART_GET_LINE_STATUS(__HuartInstance__, \
                                  __UartLineFlag__)    (READ_REG(__HuartInstance__->LSR) &__UartLineFlag__)

#define _DEF_UART_DTR_ASSERT(__HuartInstance__) \
        (SET_BIT(__HuartInstance__->MCR, \
                 UART0_MCR_DTR_Msk))
#define _DEF_UART_DTR_DEASSERT(__HuartInstance__) \
        (CLEAR_BIT(__HuartInstance__->MCR, \
                   UART0_MCR_DTR_Msk))

#define _DEF_UART_RTS_ASSERT(__HuartInstance__) \
        (SET_BIT(__HuartInstance__->MCR, \
                 UART0_MCR_RTS_Msk))
#define _DEF_UART_RTS_DEASSERT(__HuartInstance__) \
        (CLEAR_BIT(__HuartInstance__->MCR, \
                   UART0_MCR_RTS_Msk))

#define _DEF_UART_RECV_ONE_ELEMENT(__HuartInstance__)    (READ_REG(__HuartInstance__->RBR))

/**
 * @}
 */

/** @defgroup UART_Exported_Types UART Exported Types
 * @{
 */

/**
 * @brief UARTEx_Word_Length UART Word Length
 */

typedef enum
{
    UART_WORDLENGTH_5B = UART_REG_LCR_DLS(0),   /*!< 5-bit long UART frame */
    UART_WORDLENGTH_6B = UART_REG_LCR_DLS(1),   /*!< 6-bit long UART frame */
    UART_WORDLENGTH_7B = UART_REG_LCR_DLS(2),   /*!< 7-bit long UART frame */
    UART_WORDLENGTH_8B = UART_REG_LCR_DLS(3),   /*!< 8-bit long UART frame */
} UART_WordLength;

/**
 * @brief UART_Stop_Bits   UART Number of Stop Bits
 */
typedef enum
{
    UART_STOPBITS_1                 = 0x00000000U,          /*!< UART frame with 1 stop bit    */
    UART_STOPBITS_1_5_WORDLENGTH_5B = UART0_LCR_STOP_Msk,   /*!< only when UART frame is 5-bit, else 2 stop bit */
    UART_STOPBITS_2                 = UART0_LCR_STOP_Msk,   /*!< UART frame with 2 stop bits */
} UART_StopBit;

/**
 * @brief UART_Parity  UART Parity
 */
typedef enum
{
    /*!< No parity   */
    UART_PARITY_NONE    = (0x00000000U),
    /*!< Even parity */
    UART_PARITY_EVEN    = (0x00000000U | UART0_LCR_PEN_Msk | UART0_LCR_EPS_Msk),
    /*!< Odd parity  */
    UART_PARITY_ODD     = (0x00000000U | UART0_LCR_PEN_Msk),
    /*!< Logic 0 parity */
    UART_PARITY_STICK_0 = (UART0_LCR_SP_Msk | UART0_LCR_PEN_Msk | UART0_LCR_EPS_Msk),
    /*!< Logic 1 parity */
    UART_PARITY_STICK_1 = (UART0_LCR_SP_Msk | UART0_LCR_PEN_Msk | 0x00000000U)
} UART_ParityBit;

typedef enum
{
    UART_HWFLOW_DISABLE = 0,
    UART_HWFLOW_ENABLE  = 1,
} UART_HwFlowCtrl;


typedef enum
{
    UART_DMA_DISABLE     = 0,
    UART_DMA_SINGLE_MODE = 1,
    UART_DMA_MULTI_MODE  = 2,
} UART_DMAMode;

/**
 * @brief UART_Parity  UART Parity
 */
typedef enum
{
    /*!< No parity   */
    UART_MODE_NORMAL         = (0 << 0UL),

    /*!< IrDA 1.0 SIR Protocol, In this mode,
     * UART Begins with a start bit,
     * Followd by 8 data bits, end with at
     * least ont bit and without
     * parity bit.Trying to adjust the number
     * of data bits sent or enable
     * parity has no effect.BaudRate in this
     * mode is 9.6K to 115.2K,
     * Auto Flow Control is also disabled
     * */
    UART_MODE_IrDA1_0_SIR    = (1 << 0UL),

    /*!< IrDA 1.0 SIR Protocol, Low power
     * mode, The BaudRate must be 115.2K,
     * Auto Flow Control is also disabled
     * */
    UART_MODE_IrDA1_0_LP_SIR = (2 << 0UL),

    /*!< RS485 Mode, In this mode UART has
     * four signs: TX;RX;DE;RE. User can
     * change config in AdvancedInit->RS485 */
    UART_MODE_RS485          = (1 << 2UL),

    UART_MODE_9BIT           = (1 << 3UL),

    /*!< Loopback mode that enables greater
     * testing of Modem Control and Auto
     * Flow Control features(Loopback support
     * in IrDA SIR mode is available) */
    UART_MODE_LOOPBACK       = (1 << 4UL)
} UART_WorkMode;

typedef enum
{
    UART_TXFIFO_THRESHOLD_0BYTES = 0,
    UART_TXFIFO_THRESHOLD_2BYTES = UART_REG_FCR_TET_2CHAR,
    UART_TXFIFO_THRESHOLD_4BYTES = UART_REG_FCR_TET_1_4FULL,
    UART_TXFIFO_THRESHOLD_8BYTES = UART_REG_FCR_TET_1_2FULL,
} UART_TXFIFOThreshold;

typedef enum
{
    UART_RXFIFO_THRESHOLD_1BYTES  = 0,
    UART_RXFIFO_THRESHOLD_4BYTES  = UART_REG_FCR_RT_1_4FULL,
    UART_RXFIFO_THRESHOLD_8BYTES  = UART_REG_FCR_RT_1_2FULL,
    UART_RXFIFO_THRESHOLD_14BYTES = UART_REG_FCR_RT_2LESS_THAN_FIFO,
} UART_RXFIFOThreshold;

/**
 * @brief RS485 Mode Init Structure definition
 */

typedef enum
{
    UART_RS485_FULL_DUPLEX    = UART_REG_TCR_XFER_MODE(0),

    UART_RS485_HALF_DUPLEX_SW = UART_REG_TCR_XFER_MODE(1),

    UART_RS485_HALF_DUPLEX_HW = UART_REG_TCR_XFER_MODE(2),
} UART_RS485_Mode;

typedef enum
{
    UART_RS485_DE_ACTIVE_LOW  = 0x00000000U,
    UART_RS485_DE_ACTIVE_HIGH = UART0_TCR_DE_POL_Msk,
} UART_RS485_DEPolarity;

typedef enum
{
    UART_RS485_RE_ACTIVE_LOW  = 0x00000000U,
    UART_RS485_RE_ACTIVE_HIGH = UART0_TCR_RE_POL_Msk,
} UART_RS485_REPolarity;

typedef struct __PACKED
{
    UART_RS485_Mode       RS485Type;

    UART_RS485_DEPolarity DEAssertLevel;
    UART_RS485_REPolarity REAssertLevel;

    uint16_t              DEAssertTime;        /*!< There is a default cfg xxx, Or user can set to zero */
    uint16_t              DEDeAssertTime;      /*!< There is a default cfg xxx, Or user can set to zero */

    uint16_t              DE2RETurnAroundTime; /*!< There is a default cfg xxx, Or user can set to zero */
    uint16_t              RE2DETurnAroundTime; /*!< There is a default cfg xxx, Or user can set to zero */
} UART_RS485_ConfigParams;

typedef enum
{
    DEASSERT = 0,
    ASSERT   = !DEASSERT
} RS485AssertType;

typedef enum
{
    UART_9BIT_RCVR_SW = 0,
    UART_9BIT_RCVR_HW = UART0_LCR_EXT_ADDR_MATCH_Msk,
} UART_9BIT_ReceiveMode;

typedef enum
{
    UART_9BIT_XMIT_HW = 0,
    UART_9BIT_XMIT_SW = UART0_LCR_EXT_TRANSMIT_MODE_Msk,        /*!< In this Mode, User should Transmit addr
                                                                 * by 'UART_Send9BitAddrAuto', and address' 9th
                                                                 * bit is set to 1, data's 9th bit is set to 0.*/
} UART_9BIT_TransmitMode;


typedef struct __PACKED
{
    uint8_t                RCVRMatchAddress;
    uint8_t                XMITSelfAddress;
    UART_9BIT_ReceiveMode  receiveMode_9Bit;
    UART_9BIT_TransmitMode tranmitMode_9Bit;
} UART_9BIT_ConfigParams;


/**
 * @brief  UART Advanced Features initialization structure definition
 */
typedef union __PACKED
{
    UART_RS485_ConfigParams RS485;
    UART_9BIT_ConfigParams  uart9Bit;
} UART_AdvFeatureConfig;

/**
 * @brief UART Init Structure definition
 */
typedef struct __PACKED
{
    uint32_t              baudRate;

    UART_WordLength       wordLength;

    UART_StopBit          stopBits;

    UART_ParityBit        parity;

    UART_WorkMode         mode;

    UART_DMAMode          DMAMode;

    uint32_t              irqEnableFlag;

    UART_HwFlowCtrl       hwFlowCtl;

    /*!< Specifies the TXFIFO threshold level.
     * This parameter can be a value of @ref UART_TXFIFOThreshold.
     */
    UART_TXFIFOThreshold  TXFIFOThreshold;

    /*!< Specifies the RXFIFO threshold level.
     * This parameter can be a value of @ref UART_RXFIFOThreshold.
     */
    UART_RXFIFOThreshold  RXFIFOThreshold;
    UART_AdvFeatureConfig advancedInit;
} UART_ConfigParams;

/**
 * @brief  HAL UART Error Code structure definition
 */
typedef enum
{
    UART_ERROR_NONE = 0x00U,         /*!< No error            */
    UART_ERROR_PE   = 0x01U,         /*!< Parity error        */
    UART_ERROR_NE   = 0x02U,         /*!< Noise error         */
    UART_ERROR_FE   = 0x04U,         /*!< frame error         */
    UART_ERROR_ORE  = 0x08U,         /*!< Overrun error       */
    UART_ERROR_DMA  = 0x10U          /*!< DMA transfer error  */
} UART_ErrorType;


typedef enum
{
    UART_BLOCK_TRANSMIT_FIFO     = 0,
    UART_NON_BLOCK_TRANSMIT_FIFO = 1,
} UART_TransType;

/**
 * @}
 */


/** @addtogroup UART_Public_Functions
 * @{
 */

/********* Basic interface *********/
DRV_Status UART_performSoftwareReset(UART_Type *UARTx);
void UART_initConfigParams(UART_ConfigParams *init);
DRV_Status UART_config(UART_Type *Instance, UART_ConfigParams *init);
DRV_Status UART_setBaudrate(UART_Type *UARTx, uint32_t baudRate);
DRV_Status UART_setLineConfig(UART_Type *UARTx, UART_WordLength wordLength, UART_StopBit stopBits,
                              UART_ParityBit parity);

/************** Tx&Rx **************/
uint16_t UART_receive(UART_Type *UARTx, void *data, uint16_t elementSizeMax);
uint16_t UART_transmit(UART_Type *UARTx, void *data, uint16_t size, UART_TransType transType);
DRV_Status UART_waitTransmitDone(UART_Type *UARTx, uint32_t timeout);
uint16_t UART_getRxFIFOStatus(UART_Type *UARTx);
uint16_t UART_getTxFIFOStatus(UART_Type *UARTx);

uint16_t UART_receiveWithFIFO(UART_Type *UARTx, uint8_t *data, uint16_t sizeMax);
uint16_t UART_receiveWithFIFO9BIT(UART_Type *UARTx, uint16_t *data, uint16_t sizeMax);
uint16_t UART_transmitWithFIFO(UART_Type *UARTx, uint8_t *data, uint16_t size, UART_TransType transType);
uint16_t UART_transmitWithFIFO9BIT(UART_Type *UARTx, uint16_t *data, uint16_t size, UART_TransType transType);

/* 9-bit Data Transfer */
void UART_triggerAddressSend(UART_Type *UARTx);
void UART_setTransferAddress(UART_Type *UARTx, uint8_t XMITAddr);
void UART_setReceiveAddress(UART_Type *UARTx, uint8_t RCVRAddr);
void UART_config9BitMode(UART_Type *UARTx, UART_9BIT_ConfigParams *uart9Bit);

/************* Interrupt *************/
uint32_t UART_getInterruptStatus(UART_Type *UARTx);
uint32_t UART_getLineStatusFlag(UART_Type *UARTx, uint32_t uartLineFlag);
void UART_clearInterruptStatus(UART_Type *UARTx, uint32_t uartInterruptFlag);
void UART_enableInterrupt(UART_Type *UARTx, uint32_t uartInterruptFlag);
void UART_disableInterrupt(UART_Type *UARTx, uint32_t uartInterruptFlag);

/******* Hardware flow control *******/
void UART_enableHWFlowMode(UART_Type *UARTx);
void UART_disableHWFlowMode(UART_Type *UARTx);
void UART_setRTSSign(UART_Type *UARTx, FlagStatus signAssert);
void UART_setDTRSign(UART_Type *UARTx, FlagStatus signAssert);

/*************** RS485 ***************/
DRV_Status UART_RS485_config(UART_Type *UARTx, UART_RS485_ConfigParams *RS485Cfg);
uint16_t UART_RS485_transfer(UART_Type *UARTx, uint8_t *data, uint16_t size);
uint16_t UART_RS485_receive(UART_Type *UARTx, uint8_t *data, uint16_t size);
void UART_setTATTiming(UART_Type *UARTx, uint32_t DE2RETurnAroundTime, uint32_t RE2DETurnAroundTime);
void UART_setDETTiming(UART_Type *UARTx, uint32_t DEAssertTime, uint32_t DEDeAssertTime);
void UART_RS485_DEREPolarityConfig(UART_Type *UARTx, UART_RS485_DEPolarity DEAssertLevel,
                                   UART_RS485_REPolarity REAssertLevel);
void UART_RS485_setDESign(UART_Type *UARTx, RS485AssertType DeSignStatus);
void UART_RS485_setRESign(UART_Type *UARTx, RS485AssertType ReSignStatus);
DRV_Status UART_RS485_setTransferMode(UART_Type *UARTx, UART_RS485_Mode RS485Type);

/*************** Others **************/
DRV_Status UART_enableSIRMode(UART_Type *UARTx);
DRV_Status UART_disableSIRMode(UART_Type *UARTx);
DRV_Status UART_configSIRLowPowerMode(UART_Type *UARTx);
void UART_haltTransmission(UART_Type *UARTx);
void UART_resumeTransmission(UART_Type *UARTx);

DRV_Status UART_configDMA(UART_Type *UARTx, UART_DMAMode DMAMode,
                          UART_TXFIFOThreshold TXFIFOThreshold,
                          UART_RXFIFOThreshold RXFIFOThreshold);
void UART_sendBreak(UART_Type *UARTx);

/**
 * @}
 */

/**
 * @}
 */

/**
 * @}
 */

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Get the UART transmit DMA endpoint address for validation firmware.
 * @param UARTx Pointer to UARTx base address
 * @param address Pointer used to return the endpoint address
 * @return DRV_Status
 */
DRV_Status UART_testGetTxDMAEndpointAddress(UART_Type *UARTx,
                                            uintptr_t *address);

/**
 * @brief Get the UART receive DMA endpoint address for validation firmware.
 * @param UARTx Pointer to UARTx base address
 * @param address Pointer used to return the endpoint address
 * @return DRV_Status
 */
DRV_Status UART_testGetRxDMAEndpointAddress(UART_Type *UARTx,
                                            uintptr_t *address);

typedef struct
{
    uint32_t componentParameter;
    uint32_t componentVersion;
    uint32_t componentType;
    uint32_t scratch;
} UART_TestComponentSnapshot_TypeDef;

typedef struct
{
    uint32_t interruptStatus;
    uint32_t lineStatus;
    uint32_t modemStatus;
    uint32_t modemControl;
    uint32_t uartStatus;
    uint16_t txFifoLevel;
    uint16_t rxFifoLevel;
} UART_TestStatusSnapshot_TypeDef;

typedef struct
{
    uint32_t interruptStatus;
    uint32_t resolvedInterruptStatus;
    uint32_t lineStatus;
} UART_TestInterruptSnapshot_TypeDef;

typedef struct
{
    uint32_t preTriggerUsr;
    uint32_t observedIir;
    uint32_t observedUsr;
    uint32_t triggerCount;
    uint8_t busyObserved;
    uint8_t interruptObserved;
    uint8_t cleared;
    uint8_t recovered;
} UART_TestBusyDetectResult_TypeDef;

typedef struct
{
    uint8_t enabled;
    uint8_t txThreshold;
    uint8_t rxThreshold;
    uint8_t fifoAccess;
} UART_TestShadowFIFOState_TypeDef;

/* CPR capability bits consumed by the guarded validation APIs. */
#define UART_TEST_CPR_FIFO_STAT_Msk   UART0_CPR_FIFO_STAT_Msk
#define UART_TEST_CPR_FIFO_ACCESS_Msk UART0_CPR_FIFO_ACCESS_Msk
#define UART_TEST_CPR_SHADOW_Msk      UART0_CPR_SHADOW_Msk

/** @brief Capture component identification and scratch state for validation. */
DRV_Status UART_testGetComponentSnapshot(
    UART_Type *UARTx,
    UART_TestComponentSnapshot_TypeDef *snapshot);

/** @brief Capture interrupt, line, modem, FIFO and UART status for validation. */
DRV_Status UART_testGetStatusSnapshot(
    UART_Type *UARTx,
    UART_TestStatusSnapshot_TypeDef *snapshot);

/**
 * @brief Capture and resolve one interrupt together with read-clear line state.
 */
DRV_Status UART_testGetInterruptSnapshot(
    UART_Type *UARTx,
    UART_TestInterruptSnapshot_TypeDef *snapshot);

/** @brief Configure FIFO enable state and trigger levels for validation. */
DRV_Status UART_testConfigureFIFO(
    UART_Type *UARTx,
    uint8_t enabled,
    UART_TXFIFOThreshold TXFIFOThreshold,
    UART_RXFIFOThreshold RXFIFOThreshold);

/** @brief Set the UART internal loopback bit for validation. */
DRV_Status UART_testSetLoopback(UART_Type *UARTx, uint8_t enabled);

/** @brief Set or clear the UART break-control bit for validation. */
DRV_Status UART_testSetBreak(UART_Type *UARTx, uint8_t enabled);

/** @brief Enable or disable the UART 9-bit data-length extension. */
DRV_Status UART_testSetNineBitEnabled(UART_Type *UARTx, uint8_t enabled);

/**
 * @brief Atomically construct and recover one no-FIFO Busy Detect event.
 *
 * The operation is bounded.  It leaves the UART in the validation-safe
 * default FIFO state (enabled, reset asserted, TX threshold 0, RX threshold
 * 1) and restores the caller's line/interrupt configuration before returning.
 */
DRV_Status UART_testTriggerBusyDetect(
    UART_Type *UARTx,
    UART_TestBusyDetectResult_TypeDef *result);

/** @brief Configure SFE/SRT/STET and return the semantic trigger state. */
DRV_Status UART_testConfigureShadowFIFO(
    UART_Type *UARTx,
    uint8_t enabled,
    UART_TXFIFOThreshold TXFIFOThreshold,
    UART_RXFIFOThreshold RXFIFOThreshold,
    UART_TestShadowFIFOState_TypeDef *state);

/** @brief Enable or disable FAR FIFO access and return the FAR readback. */
DRV_Status UART_testSetFIFOAccess(
    UART_Type *UARTx,
    uint8_t enabled,
    uint8_t *active);

/** @brief Read one TX FIFO item through TFR in FAR access mode. */
DRV_Status UART_testReadTxFIFO(UART_Type *UARTx, uint8_t *value);

/** @brief Inject one RX FIFO item through RFW in FAR access mode. */
DRV_Status UART_testWriteRxFIFO(
    UART_Type *UARTx,
    uint8_t value,
    uint8_t parityError,
    uint8_t framingError);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

#ifdef __cplusplus
}
#endif

#endif /* __ET6x_UART_H */
