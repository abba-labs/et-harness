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
#ifndef __ET6X_CAN_H
#define __ET6X_CAN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET6801_Driver
 * @{
 */

/**
 * @addtogroup  CAN
 * @{
 */

/* ========================================================================== */
/*                           Macros & Typedefs                                */
/* ========================================================================== */


/**
 * @brief  Maximum Number of Rx Buffers.
 */
#define CAN_RX_BUFFER_MAX               (64U)

/**
 * @brief  Maximum Number of Tx Buffers.
 */
#define CAN_TX_BUFFER_MAX               (32U)

/**
 * @brief  Macro for standard Message ID filter.
 */
#define CAN_STD_ID_FILTER_SIZE_WORDS    (1U)

/**
 * @brief  Macro for extended Message ID filter.
 */
#define CAN_EXT_ID_FILTER_SIZE_WORDS    (2U)

/**
 * @brief  Macro for Tx Event FIFO element size.
 */
#define CAN_TX_EVENT_FIFO_SIZE_WORDS    (2U)

/**
 * @brief  Maximum payload supported by CAN-FD protocol in bytes.
 */
#define CAN_MAX_PAYLOAD_BYTES           (64U)

/**
 * @brief  Macro for Interrupt Line enable mask.
 */
#define CAN_INTR_LINE_EN_MASK           ((CAN0_ILE_EINT0_Msk | CAN0_ILE_EINT1_Msk))

/**
 * @brief  Macro defines mask for all the interrupts status for CAN.
 */
#define CAN_INTR_MASK_ALL \
        (CAN0_IR_RF0N_Msk |                               \
         CAN0_IR_RF0W_Msk |                              \
         CAN0_IR_RF0F_Msk |                              \
         CAN0_IR_RF0L_Msk |                              \
         CAN0_IR_RF1N_Msk |                              \
         CAN0_IR_RF1W_Msk |                              \
         CAN0_IR_RF1F_Msk |                              \
         CAN0_IR_RF1L_Msk |                              \
         CAN0_IR_HPM_Msk |                               \
         CAN0_IR_TC_Msk |                                \
         CAN0_IR_TCF_Msk |                               \
         CAN0_IR_TFE_Msk |                               \
         CAN0_IR_TEFN_Msk |                              \
         CAN0_IR_TEFW_Msk |                              \
         CAN0_IR_TEFF_Msk |                              \
         CAN0_IR_TEFL_Msk |                              \
         CAN0_IR_TSW_Msk |                               \
         CAN0_IR_MRAF_Msk |                              \
         CAN0_IR_TOO_Msk |                               \
         CAN0_IR_DRX_Msk |                               \
         CAN0_IR_BEC_Msk |                               \
         CAN0_IR_BEU_Msk |                               \
         CAN0_IR_ELO_Msk |                               \
         CAN0_IR_EP_Msk |                                \
         CAN0_IR_EW_Msk |                                \
         CAN0_IR_BO_Msk |                                \
         CAN0_IR_WDI_Msk |                               \
         CAN0_IR_PEA_Msk |                               \
         CAN0_IR_PED_Msk |                               \
         CAN0_IR_ARA_Msk)

/**
 * @brief Macro defines mask for all the interrupts mask  for CAN DMU.
 *        enable all DMU interrupts (without writing to reserved bits)
 */
#define CAN_DMU_INTR_MASK_ALL               (0x7f3fff7fU)

/**
 * @brief Macro defines for DMU element base address
 *
 */
#define CAN_DMU_TX_ELEMENT_BASE_ADDRESS     (0x200U)
/**< DMU TX  Element base address */
#define CAN_DMU_RX0_ELEMENT_BASE_ADDRESS    (0x280U)
/**< DMU RX0 Element base address*/
#define CAN_DMU_RX1_ELEMENT_BASE_ADDRESS    (0x300U)
/**< DMU DMU RX1 Element base address */
#define CAN_DMU_TXE_ELEMENT_BASE_ADDRESS    (0x380U)
/**< DMU TXE Element base address */

//*****************************************************************************
//
// These macro definitions are used to specify Standard Filter Types to
// set the sft values of the struct CAN_StdMsgIDFilterElement
// used as a parameter in the function CAN_addStdMsgIDFilter()
//
//*****************************************************************************

#define CAN_STDFILT_RANGE       (0U)
/**< Range Filter from SFID1 to SFID2 */
#define CAN_STDFILT_DUAL        (1U)
/**< Dual ID Filter for SFID1 or SFID2 */
#define CAN_STDFILT_CLASSIC     (2U)
/**< Classic Filter: SFID1 = filter, SFID2 = mask */
#define CAN_STDFILT_DISABLED    (3U)
/**< Filter Element Disabled */

//*****************************************************************************
//
// These macro definitions are used to specify Standard Filter Element
// Configurations to set the sfec values of the struct CAN_StdMsgIDFilterElement
// used as a parameter in the function CAN_addStdMsgIDFilter()
//
//*****************************************************************************

#define CAN_STDFILTEC_DISABLE      (0U)
/**< Filter Element Disabled */
#define CAN_STDFILTEC_FIFO0        (1U)
/**< Store in RX FIFO 0 if filter matches */
#define CAN_STDFILTEC_FIFO1        (2U)
/**< Store in RX FIFO 1 if filter matches */
#define CAN_STDFILTEC_REJECT       (3U)
/**< Reject ID if filter matches */
#define CAN_STDFILTEC_PRI          (4U)
/**< Set priority if filter matches */
#define CAN_STDFILTEC_PRI_FIFO0    (5U)
/**< Set priority and store in RX FIFO 0 if filter matches */
#define CAN_STDFILTEC_PRI_FIFO1    (6U)
/**< Set priority and store in RX FIFO 1 if filter matches */
#define CAN_STDFILTEC_RXBUFF       (7U)
/**< Store in RX Buffer */

/**
 * @brief CAN non-matching frames
 *
 */
#define CAN_ACCEPT_IN_RX_FIFO0       (0U) /*!< Accept in Rx FIFO 0 */
#define CAN_ACCEPT_IN_RX_FIFO1       (1U) /*!< Accept in Rx FIFO 1 */
#define CAN_REJECT                   (2U) /*!< Reject              */

/**
 * @brief CAN FIFO operation mode
 *
 */
#define CAN_RX_FIFO_BLOCKING         (0U) /*!< Rx FIFO blocking mode  */
#define CAN_RX_FIFO_OVERWRITE        (1U) /*!< Rx FIFO overwrite mode */

/**
 * @brief  CAN Operation Mode
 *
 */
#define CAN_NOMAL_OPERATION          (0U) /*!< Normal CAN operation             */
#define CAN_RESTRICTED_OPERATION     (1U) /*!< Restricted Operation Mode active */

/**
 * @brief CAN reject remote frames
 *
 */
#define CAN_FILTER_REMOTE            (0U) /*!< Filter remote frames     */
#define CAN_REJECT_REMOTE            (1U) /*!< Reject all remote frames */

/**
 * @brief CAN timestamp
 *
 */
#define CAN_TIMESTAMP_NONE           (0U) /*!< Timestamp counter value always 0x0000                */
#define CAN_TIMESTAMP_INTERNAL       (1U) /*!< Timestamp counter value incremented according to TCP */
#define CAN_TIMESTAMP_EXTERNAL       (2U) /*!< External timestamp counter value used                */

/**
 * @brief CAN timeout operation
 *
 */
#define CAN_TIMEOUT_CONTINUOUS       (0U) /*!< Timeout continuous operation        */
#define CAN_TIMEOUT_TX_EVENT_FIFO    (1U) /*!< Timeout controlled by Tx Event FIFO */
#define CAN_TIMEOUT_RX_FIFO0         (2U) /*!< Timeout controlled by Rx FIFO 0     */
#define CAN_TIMEOUT_RX_FIFO1         (3U) /*!< Timeout controlled by Rx FIFO 1     */

/**
 * @brief CAN Enable Timeout Counte
 *
 */
#define CAN_TIMEOUT_DISABLE          (0U) /*!< Timeout continuous operation        */
#define CAN_TIMEOUT_ENABLE           (1U) /*!< Timeout controlled by Tx Event FIFO */

/**
 * @brief CAN Tx FIFO/Queue Mode
 *
 */
#define CAN_TX_FIFO_OPERATION        (0U) /*!< FIFO mode  */
#define CAN_TX_QUEUE_OPERATION       (1U) /*!< Queue mode */

/**
 * @brief Bit Rate Switch Enable
 * Note: When CAN FD operation is disabled FDOE = 0, BRSE is not evaluated
 */
#define CAN_BRS_DISABLE              (0U) /*!<  CAN frames transmitted/received without bit rate switching  */
#define CAN_BRS_ENABLE               (1U) /*!<  CAN frames transmitted/received with bit rate switching     */

/**
 * @brief CAN Operation Mode
 *
 */
#define CAN_CLASSIC_CAN              (0U) /*!< Frame transmitted/received in Classic CAN format */
#define CAN_FD_CAN                   (1U) /*!< Frame transmitted/received in FDCAN format       */


/**
 *@brief CAN Data Length Code
 *
 */
#define CAN_DLC_BYTES_0        (0x00U) /*!< 0 bytes data field  */
#define CAN_DLC_BYTES_1        (0x01U) /*!< 1 bytes data field  */
#define CAN_DLC_BYTES_2        (0x02U) /*!< 2 bytes data field  */
#define CAN_DLC_BYTES_3        (0x03U) /*!< 3 bytes data field  */
#define CAN_DLC_BYTES_4        (0x04U) /*!< 4 bytes data field  */
#define CAN_DLC_BYTES_5        (0x05U) /*!< 5 bytes data field  */
#define CAN_DLC_BYTES_6        (0x06U) /*!< 6 bytes data field  */
#define CAN_DLC_BYTES_7        (0x07U) /*!< 7 bytes data field  */
#define CAN_DLC_BYTES_8        (0x08U) /*!< 8 bytes data field  */
#define CAN_DLC_BYTES_12       (0x09U) /*!< 12 bytes data field */
#define CAN_DLC_BYTES_16       (0x0AU) /*!< 16 bytes data field */
#define CAN_DLC_BYTES_20       (0x0BU) /*!< 20 bytes data field */
#define CAN_DLC_BYTES_24       (0x0CU) /*!< 24 bytes data field */
#define CAN_DLC_BYTES_32       (0x0DU) /*!< 32 bytes data field */
#define CAN_DLC_BYTES_48       (0x0EU) /*!< 48 bytes data field */
#define CAN_DLC_BYTES_64       (0x0FU) /*!< 64 bytes data field */

/**
 * @brief CAN ID Type
 *
 */
#define CAN_STANDARD_ID        (0U) /*!< Standard ID element */
#define CAN_EXTENDED_ID        (1U) /*!< Extended ID element */

/**
 * @brief CAN Frame Type
 *
 */
#define CAN_DATA_FRAME         (0U) /*!< Data frame   */
#define CAN_REMOTE_FRAME       (1U) /*!< Remote frame */

/**
 * @brief CAN Error State Indicator
 *
 */
#define CAN_ESI_ACTIVE         (0U) /*!< Transmitting node is error active  */
#define CAN_ESI_PASSIVE        (1U) /*!< Transmitting node is error passive */

/**
 * @brief CAN Event FIFO control
 *
 */
#define CAN_NO_TX_EVENTS       (0U) /*!< Do not store Tx events */
#define CAN_STORE_TX_EVENTS    (1U) /*!< Store Tx events        */

/**
 *  @brief    Enum to select the CAN interrupt lines
 */
typedef enum
{
    CAN_INTR_LINE_NUM_0 = 0U,
    /**< CAN interrupt line 0 */
    CAN_INTR_LINE_NUM_1 = 1U
                          /**< CAN interrupt line 1 */
} CAN_IntrLineNum;

/**
 *  @brief    Enum to represent the CAN Identifier Type
 */
typedef enum
{
    CAN_ID_TYPE_11_BIT = 0U,
    /**< 11bit CAN Identifier */
    CAN_ID_TYPE_29_BIT = 1U
                         /**< 29bit CAN Identifier */
} CAN_IdType;

typedef enum
{
    CAN_OPERATION_MODE_NORMAL  = 0U,       //!< CAN normal mode
    CAN_OPERATION_MODE_SW_INIT = 1U        //!< CAN SW initialization mode
} CAN_OperationMode;


/**
 * @brief Structure for CAN Transmitter Delay Compensation parameters.
 */
typedef struct
{
    uint32_t tdcf;

    /**< Transmitter Delay Compensation Filter Window Length
     *   Range:[0x0-0x7F]
     */
    uint32_t tdco;

    /**< Transmitter Delay Compensation Offset
     *   Range:[0x0-0x7F]
     */
} CAN_TDCConfig;

/**
 * @brief Structure for CAN Global Filter Configuration parameters.
 */
typedef struct
{
    uint32_t rrfe;

    /**< Reject Remote Frames Extended
     *   0 = Filter remote frames with 29-bit extended IDs
     *   1 = Reject all remote frames with 29-bit extended IDs
     */
    uint32_t rrfs;

    /**< Reject Remote Frames Standard
     *   0 = Filter remote frames with 11-bit standard IDs
     *   1 = Reject all remote frames with 11-bit standard IDs
     */
    uint32_t anfe;

    /**< Accept Non-matching Frames Extended
     *   0 = Accept in Rx FIFO 0
     *   1 = Accept in Rx FIFO 1
     *   others = Reject
     */
    uint32_t anfs;

    /**< Accept Non-matching Frames Standard
     *   0 = Accept in Rx FIFO 0
     *   1 = Accept in Rx FIFO 1
     *   others = Reject
     */
} CAN_GlobalFiltConfig;

/**
 * @brief Structure for CAN ECC configuration parameters.
 */
typedef struct
{
    uint32_t enable;

    /**< Enable/disable ECC
     *   0 = Disable ECC
     *   1 = Enable ECC
     */
    uint32_t enableRdModWr;

    /**< Enable/disable Read Modify Write operation
     *   0 = Disable Read Modify Write operation
     *   1 = Enable Read Modify Write operation
     */
} CAN_ECCConfigParams;

/**
 * @brief  Structure for bit timing calculation.
 *         Bit timing related to data phase will be valid only in case where
 *         CAN is put in CAN-FD mode and will be '0' otherwise.
 */
typedef struct
{
    uint32_t nomRatePrescalar;

    /**< Nominal Baud Rate Pre-scaler
     *   Range:[0x0-0x1FF]
     */
    uint32_t nomTimeSeg1;

    /**< Nominal Time segment before sample point
     *   Range:[0x0-0xFF]
     */
    uint32_t nomTimeSeg2;

    /**< Nominal Time segment after sample point
     *   Range:[0x0-0x7F]
     */
    uint32_t nomSynchJumpWidth;

    /**< Nominal (Re)Synchronization Jump Width
     *   Range:[0x0-0x7F]
     */
    uint32_t dataRatePrescalar;

    /**< Data Baud Rate Pre-scaler
     *   Range:[0x0-0x1F]
     */
    uint32_t dataTimeSeg1;

    /**< Data Time segment before sample point
     *   Range:[0x0-0x1F]
     */
    uint32_t dataTimeSeg2;

    /**< Data Time segment after sample point
     *   Range:[0x0-0xF]
     */
    uint32_t dataSynchJumpWidth;

    /**< Data (Re)Synchronization Jump Width
     *   Range:[0x0-0xF]
     */
} CAN_BitTimingParams;


/**
 * @brief  Structure for CAN Message RAM Configuration Parameters.
 *         Message RAM can contain following sections:
 *         Standard ID filters, Extended ID filters, TX FIFO(or TX Q),
 *         TX Buffers, TX EventFIFO, RX FIFO0, RX FIFO1, RX Buffer.
 *         Note: If particular section in the RAM is not used then it's size
 *         should be initialized to '0'
 *         (Number of buffers in case of Tx/Rx buffer).
 */
typedef struct
{
    uint32_t flssa;
    /**< Standard ID Filter List Start Address */
    uint32_t lss;

    /**< List Size: Standard ID
     *   0 = No standard Message ID filter
     *   1-127 = Number of standard Message ID filter elements
     *   others = Values greater than 128 are interpreted as 128
     */
    uint32_t flesa;
    /**< Extended ID Filter List Start Address */
    uint32_t lse;

    /**< List Size: Extended ID
     *   0 = No standard Message ID filter
     *   1-64 = Number of standard Message ID filter elements
     *   others = Values greater than 64 are interpreted as 64
     */
    uint32_t txStartAddr;
    /**< Tx Buffers Start Address */
    uint32_t txBufNum;

    /**< Number of Dedicated Transmit Buffers
     *   0 = No Dedicated Tx Buffers
     *   1-32 = Number of Dedicated Tx Buffers
     *   others = Values greater than 32 are interpreted as 32
     */
    uint32_t txFIFOSize;

    /**< Transmit FIFO/Queue Size
     *   0 = No Tx FIFO/Queue
     *   1-32 = Number of Tx Buffers used for Tx FIFO/Queue
     *   others = Values greater than 32 are interpreted as 32
     */
    uint32_t txBufMode;

    /**< Tx FIFO/Queue Mode
     *   0 = Tx FIFO operation
     *   1 = Tx Queue operation
     */
    uint32_t txBufElemSize;
    /**< Tx Buffer Element Size */
    uint32_t txEventFIFOStartAddr;
    /**< Tx Event FIFO Start Address */
    uint32_t txEventFIFOSize;

    /**< Event FIFO Size
     *   0 = Tx Event FIFO disabled
     *   1-32 = Number of Tx Event FIFO elements
     *   others = Values greater than 32 are interpreted as 32
     */
    uint32_t txEventFIFOWaterMark;

    /**< Tx Event FIFO Watermark
     *   0 = Watermark interrupt disabled
     *   1-32 = Level for Tx Event FIFO watermark interrupt
     *   others = Watermark interrupt disabled
     */
    uint32_t rxFIFO0startAddr;
    /**< Rx FIFO0 Start Address */
    uint32_t rxFIFO0size;

    /**< Rx FIFO0 Size
     *   0 = No Rx FIFO
     *   1-64 = Number of Rx FIFO elements
     *   others = Values greater than 64 are interpreted as 64
     */
    uint32_t rxFIFO0waterMark;

    /**< Rx FIFO0 Watermark
     *   0 = Watermark interrupt disabled
     *   1-63 = Level for Rx FIFO 0 watermark interrupt
     *   others = Watermark interrupt disabled
     */
    uint32_t rxFIFO0OpMode;

    /**< Rx FIFO0 Operation Mode
     *   0 = FIFO blocking mode
     *   1 = FIFO overwrite mode
     */
    uint32_t rxFIFO1startAddr;
    /**< Rx FIFO1 Start Address */
    uint32_t rxFIFO1size;

    /**< Rx FIFO1 Size
     *   0 = No Rx FIFO
     *   1-64 = Number of Rx FIFO elements
     *   others = Values greater than 64 are interpreted as 64
     */
    uint32_t rxFIFO1waterMark;

    /**< Rx FIFO1 Watermark
     *   0 = Watermark interrupt disabled
     *   1-63 = Level for Rx FIFO 1 watermark interrupt
     *   others = Watermark interrupt disabled
     */
    uint32_t rxFIFO1OpMode;

    /**< Rx FIFO1 Operation Mode
     *   0 = FIFO blocking mode
     *   1 = FIFO overwrite mode
     */
    uint32_t rxBufStartAddr;
    /**< Rx Buffer Start Address */
    uint32_t rxBufElemSize;
    /**< Rx Buffer Element Size */
    uint32_t rxFIFO0ElemSize;
    /**< Rx FIFO0 Element Size */
    uint32_t rxFIFO1ElemSize;
    /**< Rx FIFO1 Element Size */
} CAN_MsgRAMConfigParams;

/**
 * @brief  Structure for CAN initialization parameters.
 */
typedef struct
{
    uint32_t      fdMode;

    /**< FD Operation Enable
     *   0 = FD operation disabled
     *   1 = FD operation enabled
     */
    uint32_t      brsEnable;

    /**< Bit Rate Switch Enable
     *   This is valid only when opMode = 1.
     *   0 = Bit rate switching for transmissions disabled
     *   1 = Bit rate switching for transmissions enabled
     */
    uint32_t      txpEnable;

    /**< Transmit Pause
     *   0 = Transmit pause disabled
     *   1 = Transmit pause enabled
     */
    uint32_t      efbi;

    /**< FEdge Filtering during Bus Integration
     *   0 = Edge filtering disabled
     *   1 = Two consecutive dominant tq required to detect an edge for
     *       hard synchronization
     */
    uint32_t      pxhddisable;

    /**< Protocol Exception Handling Disable
     *   0 = Protocol exception handling enabled
     *   1 = Protocol exception handling disabled
     */
    uint32_t      darEnable;

    /**< Disable Automatic Retransmission
     *   0 = Automatic retransmission of messages not transmitted successfully
     *       enabled
     *   1 = Automatic retransmission disabled
     */
    uint32_t      wdcPreload;

    /**< Start value of the Message RAM Watchdog Counter
     *   Range:[0x0-0xFF]
     */
    CAN_TDCConfig tdcConfig;

    /**< Transmitter Delay Compensation parameters.
     *   Refer struct #CAN_TDCConfig.
     */
    uint32_t      tdcEnable;

    /**< Transmitter Delay Compensation Enable
     *   0 = Transmitter Delay Compensation is disabled
     *   1 = Transmitter Delay Compensation is enabled
     */
} CAN_InitParams;


/**
 * @brief Structure for CAN configuration parameters.
 */
typedef struct
{
    uint32_t             monEnable;

    /**< Bus Monitoring Mode
     *   0 = Bus Monitoring Mode is disabled
     *   1 = Bus Monitoring Mode is enabled
     */
    uint32_t             asmEnable;

    /**< Restricted Operation Mode
     *   0 = Normal CAN operation
     *   1 = Restricted Operation Mode active
     *   This mode should not be combined with test modes.
     */
    uint32_t             tsPrescalar;

    /**< Timestamp Counter Prescaler, expressed as the actual divisor.
     *   Range:[1-16]; TSCC.TCP stores this value minus one.
     */
    uint32_t             tsSelect;

    /**< Timestamp source selection.
     *   00= Timestamp counter value always 0x0000
     *   01= Timestamp counter value incremented according to tsPrescalar
     *   10= External timestamp counter value used
     *   11= Same as “00”
     */
    uint32_t             timeoutSelect;

    /**< Time-out counter source select.
     *   Refer enum #CAN_TimeOutSelect.
     */
    uint32_t             timeoutPreload;

    /**< Start value of the Timeout Counter (down-counter).
     *   The Timeout Counter is decremented in multiples of CAN bit times [1-16]
     *   depending on the configuration of the tsPrescalar.
     *   Range:[0x0-0xFFFF]
     */
    uint32_t             timeoutCntEnable;

    /**< Time-out Counter Enable
     *   0 = Time-out Counter is disabled
     *   1 = Time-out Counter is enabled
     */
    CAN_GlobalFiltConfig filterConfig;

    /**< Global Filter Configuration parameters.
     *    Refer struct #CAN_GlobalFiltConfig.
     */
} CAN_ConfigParams;

/**
 * @brief  Structure for CAN error logging counters status.
 */
typedef struct
{
    uint32_t transErrLogCnt;
    /**< Transmit Error Counter */
    uint32_t recErrCnt;
    /**< Receive Error Counter */
    uint32_t rpStatus;

    /**< Receive Error Passive
     *   0 = The Receive Error Counter is below the error passive level(128)
     *   1 = The Receive Error Counter has reached the error passive level(128)
     */
    uint32_t canErrLogCnt;
    /**< CAN Error Logging */
} CAN_ErrCntStatus;

/**
 * @brief  Structure for CAN protocol status.
 */
typedef struct
{
    uint32_t lastErrCode;

    /**< Last Error Code
     *   Refer enum #CAN_ErrCode
     */
    uint32_t act;

    /**< Activity - Monitors the module’s CAN communication state.
     *   refer enum #CAN_ComState
     */
    uint32_t errPassive;

    /**< Error Passive
     *   0 = The M_CAN is in the Error_Active state
     *   1 = The M_CAN is in the Error_Passive state
     */
    uint32_t warningStatus;

    /**< Warning Status
     *   0 = Both error counters are below the Error_Warning limit of 96
     *   1 = At least one of error counter has reached the Error_Warning
     *       limit of 96
     */
    uint32_t busOffStatus;

    /**< Bus_Off Status
     *   0 = The M_CAN is not Bus_Off
     *   1 = The M_CAN is in Bus_Off state
     */
    uint32_t dlec;

    /**< Data Phase Last Error Code
     *   Refer enum #CAN_ErrCode
     */
    uint32_t resi;

    /**< ESI flag of last received CAN FD Message
     *   0 = Last received CAN FD message did not have its ESI flag set
     *   1 = Last received CAN FD message had its ESI flag set
     */
    uint32_t rbrs;

    /**< BRS flag of last received CAN FD Message
     *   0 = Last received CAN FD message did not have its BRS flag set
     *   1 = TLast received CAN FD message had its BRS flag set
     */
    uint32_t rfdf;

    /**< Received a CAN FD Message
     *   0 = Since this bit was reset by the CPU, no CAN FD message has been
     *       received
     *   1 = Message in CAN FD format with FDF flag set has been received
     */
    uint32_t pxe;

    /**< Protocol Exception Event
     *   0 = No protocol exception event occurred since last read access
     *   1 = Protocol exception event occurred
     */
    uint32_t tdcv;
    /**< Transmitter Delay Compensation Value */
} CAN_ProtocolStatus;

/**
 * @brief  Structure for CAN new data flag for Rx buffer.
 */
typedef struct
{
    uint32_t statusLow;
    /**< New data flag for Rx buffer no. 0 to 31 */
    uint32_t statusHigh;
    /**< New data flag for Rx buffer no. 32 to 63 */
} CAN_RxNewDataStatus;

/**
 * @brief  Structure for CAN Rx FIFO Status.
 */
typedef struct
{
    uint32_t num;

    /**< Rx FIFO number
     *   Refer enum #CAN_RxFIFONum
     */
    uint32_t fillLvl;
    /**< Rx FIFO Fill Level */
    uint32_t getIdx;
    /**< Rx FIFO Get Index */
    uint32_t putIdx;
    /**< Rx FIFO Put Index */
    uint32_t fifoFull;

    /**< Rx FIFO Full
     *   0 = Rx FIFO not full
     *   1 = Rx FIFO full
     */
    uint32_t msgLost;
    /**< Rx FIFO Message Lost */
} CAN_RxFIFOStatus;

/**
 * @brief  Structure for CAN Tx FIFO Status.
 */
typedef struct
{
    uint32_t freeLvl;
    /**< Tx FIFO Free Level */
    uint32_t getIdx;

    /**< Tx FIFO Get Index
     *   Read as zero when Tx Queue operation is configured.
     */
    uint32_t putIdx;
    /**< Tx FIFO/Queue Put Index */
    uint32_t fifoFull;

    /**< Tx FIFO/Queue Full
     *   0 = Tx FIFO/Queue not full
     *   1 = Tx FIFO/Queue full
     */
} CAN_TxFIFOStatus;

/**
 * @brief  Structure for CAN Tx Event FIFO Status.
 */
typedef struct
{
    uint32_t fillLvl;
    /**< Event FIFO Fill Level */
    uint32_t getIdx;
    /**< Event FIFO Gut Index */
    uint32_t putIdx;
    /**< Event FIFO Put Index */
    uint32_t fifoFull;

    /**< Event FIFO Full
     *   0 = Tx Event FIFO not full
     *   1 = Tx Event FIFO full
     */
    uint32_t eleLost;

    /**< Tx Event FIFO Element Lost
     *   0 = No Tx Event FIFO element lost
     *   1 = Tx Event FIFO element lost, also set after write attempt to
     *       Tx Event FIFO of size zero.
     */
} CAN_TxEventFIFOStatus;

/**
 * @brief  Structure for CAN High Priority Message.
 */
typedef struct
{
    uint32_t bufIdx;

    /**< Buffer Index
     *   Only valid when MSI[1] = ‘1’.
     */
    uint32_t msi;

    /**< Message Storage Indicator
     *   MSI[1:0]
     *       00  = No FIFO selected
     *       01  = FIFO message lost
     *       10  = Message stored in FIFO 0
     *       11  = Message stored in FIFO 1
     */
    uint32_t filterIdx;
    /**< Filter Index */
    uint32_t filterList;

    /**< Indicates the filter list of the matching filter element
     *   0 = Standard Filter List
     *   1 = Extended Filter List
     */
} CAN_HighPriorityMsgInfo;

/**
 * @brief  Structure for CAN Tx Buffer element.
 */
typedef struct
{
    uint32_t id;
    /**< Identifier */
    uint32_t rtr;

    /**< Remote Transmission Request
     *   0 = Transmit data frame
     *   1 = Transmit remote frame
     */
    uint32_t xtd;

    /**< Extended Identifier
     *   0 = 11-bit standard identifier
     *   1 = 29-bit extended identifier
     */
    uint32_t esi;

    /**< Error State Indicator
     *   0 = ESI bit in CAN FD format depends only on error passive flag
     *   1 = ESI bit in CAN FD format transmitted recessive
     */
    uint32_t dlc;

    /**< Data Length Code
     *   0-8  = CAN + CAN FD: transmit frame has 0-8 data bytes
     *   9-15 = CAN: transmit frame has 8 data bytes
     *   9-15 = CAN FD: transmit frame has 12/16/20/24/32/48/64 data bytes
     */
    uint32_t brs;

    /**< Bit Rat Switching
     *   0 = CAN FD frames transmitted without bit rate switching
     *   1 = CAN FD frames transmitted with bit rate switching
     */
    uint32_t fdf;

    /**< FD Format
     *   0 = Frame transmitted in Classic CAN format
     *   1 = Frame transmitted in CAN FD format
     */
    uint32_t tx_tsce;

    /**< TX Message TimeStamp capture enable
     *   0 = TX Message TimeStamp capture disable
     *   1 = TX Message TimeStamp capture enable
     */
    uint32_t efc;

    /**< Event FIFO Control
     *   0 = Don’t store Tx events
     *   1 = Store Tx events
     */
    uint32_t mm;
    /**< Message Marker */
    uint16_t data[CAN_MAX_PAYLOAD_BYTES];

    /**< Data bytes.
     *   Only first dlc number of bytes are valid.
     */
} CAN_TxBufElement;

/**
 * @brief  Structure for CAN Rx Buffer element.
 */
typedef struct
{
    uint32_t id;
    /**< Identifier */
    uint32_t rtr;

    /**< Remote Transmission Request
     *   0 = Received frame is a data frame
     *   1 = Received frame is a remote frame
     */
    uint32_t xtd;

    /**< Extended Identifier
     *   0 = 11-bit standard identifier
     *   1 = 29-bit extended identifier
     */
    uint32_t esi;

    /**< Error State Indicator
     *   0 = Transmitting node is error active
     *   1 = Transmitting node is error passive
     */
    uint32_t rxts;
    /**< Rx Timestamp */
    uint32_t dlc;

    /**< Data Length Code
     *   0-8  = CAN + CAN FD: received frame has 0-8 data bytes
     *   9-15 = CAN: received frame has 8 data bytes
     *   9-15 = CAN FD: received frame has 12/16/20/24/32/48/64 data bytes
     */
    uint32_t brs;

    /**< Bit Rat Switching
     *   0 = Frame received without bit rate switching
     *   1 = Frame received with bit rate switching
     */
    uint32_t fdf;

    /**< FD Format
     *   0 = Standard frame format
     *   1 = CAN FD frame format (new DLC-coding and CRC)
     */
    uint32_t fidx;
    /**< Filter Index */
    uint32_t anmf;

    /**< Accepted Non-matching Frame
     *   0 = Received frame matching filter index FIDX
     *   1 = Received frame did not match any Rx filter element
     */
    uint16_t data[CAN_MAX_PAYLOAD_BYTES];

    /**< Data bytes.
     *   Only first dlc number of bytes are valid.
     */
} CAN_RxBufElement;

/**
 * @brief  Structure for CAN Tx Event FIFO element.
 */
typedef struct
{
    uint32_t id;
    /**< Identifier */
    uint32_t rtr;

    /**< Remote Transmission Request
     *   0 = Data frame transmitted
     *   1 = Remote frame transmitted
     */
    uint32_t xtd;

    /**< Extended Identifier
     *   0 = 11-bit standard identifier
     *   1 = 29-bit extended identifier
     */
    uint32_t esi;

    /**< Error State Indicator
     *   0 = Transmitting node is error active
     *   1 = Transmitting node is error passive
     */
    uint32_t txts;
    /**< Tx Timestamp */
    uint32_t dlc;

    /**< Data Length Code
     *   0-8  = CAN + CAN FD: frame with 0-8 data bytes transmitted
     *   9-15 = CAN: frame with 8 data bytes transmitted
     *   9-15 = CAN FD: frame with 12/16/20/24/32/48/64 data bytes transmitted
     */
    uint32_t brs;

    /**< Bit Rat Switching
     *   0 = Frame transmitted without bit rate switching
     *   1 = Frame transmitted with bit rate switching
     */
    uint32_t fdf;

    /**< FD Format
     *   0 = Standard frame format
     *   1 = CAN FD frame format (new DLC-coding and CRC)
     */
    uint32_t et;

    /**< Event Type
     *   00 = Reserved
     *   01 = Tx event
     *   10 = Transmission in spite of cancellation
     *        (always set for transmissions in DAR mode)
     *   11 = Reserved
     */
    uint32_t mm;
    /**< Message Marker */
} CAN_TxEventFIFOElement;

/**
 * @brief  Structure for CAN Standard Message ID Filter Element.
 */
typedef struct
{
    uint32_t sfid2;
    /**< Standard Filter ID 2 */
    uint32_t sfid1;
    /**< Standard Filter ID 1 */
    uint32_t sfec;

    /**< Standard Filter Element Configuration (macros defined for each value)
     *   000 = Disable filter element                               (CAN_STDFILTEC_DISABLE)
     *   001 = Store in Rx FIFO 0 if filter matches                 (CAN_STDFILTEC_FIFO0)
     *   010 = Store in Rx FIFO 1 if filter matches                 (CAN_STDFILTEC_FIFO1)
     *   011 = Reject ID if filter matches                          (CAN_STDFILTEC_REJECT)
     *   100 = Set priority if filter matches                       (CAN_STDFILTEC_PRI)
     *   101 = Set priority and store in FIFO 0 if filter matches   (CAN_STDFILTEC_PRI_FIFO0)
     *   110 = Set priority and store in FIFO 1 if filter matches   (CAN_STDFILTEC_PRI_FIFO1)
     *   111 = Store into Rx Buffer or as debug message,            (CAN_STDFILTEC_RXBUFF)
     *         configuration of SFT[1:0] ignored.
     *   If SFEC = “100”, “101”, or “110” a match sets high priority
     *   message event is generated.
     */
    uint32_t sft;

    /**< Standard Filter Type (macros defined for each value)
     *   00 = Range filter from SFID1 to SFID2 (SFID2 ≥ SFID1)  (CAN_STDFILT_RANGE)
     *   01 = Dual ID filter for SFID1 or SFID2                 (CAN_STDFILT_DUAL)
     *   10 = Classic filter: SFID1 = filter, SFID2 = mask      (CAN_STDFILT_CLASSIC)
     *   11 = Filter element disabled                           (CAN_STDFILT_DISABLED)
     */
} CAN_StdMsgIDFilterElement;

/**
 * @brief  Structure for CAN Extended Message ID Filter Element.
 */
typedef struct
{
    uint32_t efid1;
    /**< Extended Filter ID 1 */
    uint32_t efec;

    /**< Extended Filter Element Configuration
     *   000 = Disable filter element
     *   001 = Store in Rx FIFO 0 if filter matches
     *   010 = Store in Rx FIFO 1 if filter matches
     *   011 = Reject ID if filter matches
     *   100 = Set priority if filter matches
     *   101 = Set priority and store in FIFO 0 if filter matches
     *   110 = Set priority and store in FIFO 1 if filter matches
     *   111 = Store into Rx Buffer or as debug message,
     *         configuration of SFT[1:0] ignored.
     *   If EFEC = “100”, “101”, or “110” a match sets high priority
     *   message event is generated.
     */
    uint32_t efid2;
    /**< Extended Filter ID 2 */
    uint32_t eft;

    /**< Extended Filter Type
     *   00 = Range filter from EFID1 to EFID2 (EFID2 ≥ EFID1)
     *   01 = Dual ID filter for EFID1 or EFID2
     *   10 = Classic filter: EFID1 = filter, EFID2 = mask
     *   11 = Range filter from EFID1 to EFID2 (EFID2 ≥ EFID1),
     *        XIDAM mask not applied
     */
} CAN_ExtMsgIDFilterElement;

/**
 * @brief  Structure for CAN TSU configuration parameters.
 */
typedef struct
{
    uint32_t enable;

    /**< Enable/disable TSU unit
     *   0 = Disable TSU
     *   1 = Enable TSU
     */
    uint32_t tbcs;

    /**< time base counter select
     *   0 = select internal time base counter
     *   1 = select external time base counter
     */
    uint32_t scp;

    /**< select capture position
     *   0 = capture timestamp at EOF
     *   1 = capture timestamp at SOF
     */
    uint32_t tbPrescalar;

    /**< Timebase Counter Prescaler.
     *   Range:[1~256]
     */
} CAN_TSUConfigParams;

/**
 *  @brief    Enum to represent the CAN Message RAM type.
 */
typedef enum
{
    CAN_MEM_TYPE_BUF  = 0U,
    /**< CAN Msg RAM buffers */
    CAN_MEM_TYPE_FIFO = 1U
                        /**< CAN Msg RAM FIFO/Queue */
} CAN_MemType;

/**
 *  @brief    Enum to represent the CAN Rx FIFO number
 */
typedef enum
{
    CAN_RX_FIFO_NUM_0 = 0U,
    /**< CAN Rx FIFO 0 */
    CAN_RX_FIFO_NUM_1 = 1U
                        /**< CAN Rx FIFO 1 */
} CAN_RxFIFONum;

/**
 *  @brief    Enum to represent FIFO/Buffer element Size
 */
typedef enum
{
    CAN_ELEM_SIZE_8BYTES  = 0U,
    /**< 8 byte data field */
    CAN_ELEM_SIZE_12BYTES = 1U,
    /**< 12 byte data field */
    CAN_ELEM_SIZE_16BYTES = 2U,
    /**< 16 byte data field */
    CAN_ELEM_SIZE_20BYTES = 3U,
    /**< 20 byte data field */
    CAN_ELEM_SIZE_24BYTES = 4U,
    /**< 24 byte data field */
    CAN_ELEM_SIZE_32BYTES = 5U,
    /**< 32 byte data field */
    CAN_ELEM_SIZE_48BYTES = 6U,
    /**< 48 byte data field */
    CAN_ELEM_SIZE_64BYTES = 7U
                            /**< 64 byte data field */
} CAN_ElemSize;

/**
 *  @brief    Enum to represent the CAN time-out counter configuration
 */
typedef enum
{
    CAN_TIMEOUT_SELECT_CONT          = 0U,
    /**< Continuous operation Mode */
    CAN_TIMEOUT_SELECT_TX_EVENT_FIFO = 1U,
    /**< Timeout controlled by Tx Event FIFO */
    CAN_TIMEOUT_SELECT_RX_FIFO0      = 2U,
    /**< Timeout controlled by Rx FIFO 0 */
    CAN_TIMEOUT_SELECT_RX_FIFO1      = 3U
                                       /**< Timeout controlled by Rx FIFO 1 */
} CAN_TimeOutSelect;

/**
 * @brief  Enum for CAN interrupts.
 */
typedef enum
{
    CAN_INTR_SRC_RX_FIFO0_NEW_MSG       = CAN0_IR_RF0N_Msk,
    /**< Rx FIFO 0 New Message interrupt */
    CAN_INTR_SRC_RX_FIFO0_WATERMARK     = CAN0_IR_RF0W_Msk,
    /**< Rx FIFO 0 Watermark Reached interrupt */
    CAN_INTR_SRC_RX_FIFO0_FULL          = CAN0_IR_RF0F_Msk,
    /**< Rx FIFO 0 Full interrupt */
    CAN_INTR_SRC_RX_FIFO0_MSG_LOST      = CAN0_IR_RF0L_Msk,
    /**< Rx FIFO 0 Message Lost interrupt */
    CAN_INTR_SRC_RX_FIFO1_NEW_MSG       = CAN0_IR_RF1N_Msk,
    /**< Rx FIFO 1 New Message interrupt */
    CAN_INTR_SRC_RX_FIFO1_WATERMARK     = CAN0_IR_RF1W_Msk,
    /**< Rx FIFO 1 Watermark Reached interrupt */
    CAN_INTR_SRC_RX_FIFO1_FULL          = CAN0_IR_RF1F_Msk,
    /**< Rx FIFO 1 Full interrupt */
    CAN_INTR_SRC_RX_FIFO1_MSG_LOST      = CAN0_IR_RF1L_Msk,
    /**< Rx FIFO 1 Message Lost interrupt */
    CAN_INTR_SRC_HIGH_PRIO_MSG          = CAN0_IR_HPM_Msk,
    /**< High Priority Message interrupt */
    CAN_INTR_SRC_TRANS_COMPLETE         = CAN0_IR_TC_Msk,
    /**< Transmission Completed interrupt */
    CAN_INTR_SRC_TRANS_CANCEL_FINISH    = CAN0_IR_TCF_Msk,
    /**< Transmission Cancellation Finished interrupt */
    CAN_INTR_SRC_TX_FIFO_EMPTY          = CAN0_IR_TFE_Msk,
    /**< Tx FIFO Empty interrupt */
    CAN_INTR_SRC_TX_EVT_FIFO_NEW_ENTRY  = CAN0_IR_TEFN_Msk,
    /**< Tx Event FIFO New Entry interrupt */
    CAN_INTR_SRC_TX_EVT_FIFO_WATERMARK  = CAN0_IR_TEFW_Msk,
    /**< Tx Event FIFO Watermark Reached interrupt */
    CAN_INTR_SRC_TX_EVT_FIFO_FULL       = CAN0_IR_TEFF_Msk,
    /**< Tx Event FIFO Full interrupt */
    CAN_INTR_SRC_TX_EVT_FIFO_ELEM_LOST  = CAN0_IR_TEFL_Msk,
    /**< Tx Event FIFO Element Lost interrupt */
    CAN_INTR_SRC_TIMESTAMP_WRAPAROUND   = CAN0_IR_TSW_Msk,
    /**< Timestamp Wraparound interrupt */
    CAN_INTR_SRC_MSG_RAM_ACCESS_FAILURE = CAN0_IR_MRAF_Msk,
    /**< Message RAM Access Failure interrupt */
    CAN_INTR_SRC_TIMEOUT                = CAN0_IR_TOO_Msk,
    /**< Timeout Occurred interrupt */
    CAN_INTR_SRC_DEDICATED_RX_BUFF_MSG  = CAN0_IR_DRX_Msk,
    /**< Message stored to Dedicated Rx Buffer interrupt */
    CAN_INTR_SRC_BIT_ERR_CORRECTED      = CAN0_IR_BEC_Msk,
    /**< Bit Error Corrected interrupt */
    CAN_INTR_SRC_BIT_ERR_UNCORRECTED    = CAN0_IR_BEU_Msk,
    /**< Bit Error Uncorrected interrupt */
    CAN_INTR_SRC_ERR_LOG_OVRFLW         = CAN0_IR_ELO_Msk,
    /**< Error Logging Overflow interrupt */
    CAN_INTR_SRC_ERR_PASSIVE            = CAN0_IR_EP_Msk,
    /**< Error Passive interrupt */
    CAN_INTR_SRC_WARNING_STATUS         = CAN0_IR_EW_Msk,
    /**< Warning Status interrupt */
    CAN_INTR_SRC_BUS_OFF_STATUS         = CAN0_IR_BO_Msk,
    /**< Bus_Off Status interrupt */
    CAN_INTR_SRC_WATCHDOG               = CAN0_IR_WDI_Msk,
    /**< Watchdog Interrupt interrupt */
    CAN_INTR_SRC_PROTOCOL_ERR_ARB       = CAN0_IR_PEA_Msk,
    /**< Protocol Error in Arbitration Phase interrupt */
    CAN_INTR_SRC_PROTOCOL_ERR_DATA      = CAN0_IR_PED_Msk,
    /**< Protocol Error in Data Phase interrupt */
    CAN_INTR_SRC_RES_ADDR_ACCESS        = CAN0_IR_ARA_Msk
                                          /**< Access to Reserved Address interrupt */
} CAN_IntrSrc;


/**
 *  @brief    Enum for CAN DMU Rx Request type
 */
typedef enum
{
    CAN_DMU_REQ_RX0R = 0U,
    /**< Rx FIFO 0 Service Request line of DMU */
    CAN_DMU_REQ_RX1R = 1U,
    /**< Rx FIFO 1 Service Request line of DMU */
    CAN_DMU_REQ_TXER = 2U
                       /**< Tx Event Service Request line of DMU */
} CAN_DMURxRequest;

/**
 *  @brief    Enum to select the CAN Loopback mode
 */
typedef enum
{
    CAN_LPBK_MODE_INTERNAL = 0U,

    /**< Internal Loop Back Mode
     *   This mode can be used for hot self-test and this mode will not
     *   affect bus state.
     */
    CAN_LPBK_MODE_EXTERNAL = 1U

                             /**< External Loop Back Mode
                              *   In this mode, CAN the M_CAN treats its own
                              **transmitted messages as
                              *   received messages and stores them (if they
                              **pass acceptance filtering)
                              *   into an Rx Buffer or an Rx FIFO.
                              *   This mode will affect bus state
                              */
} CAN_LpbkMode;



uint32_t CAN_isFDOpEnable(CAN_Type *CANx);
void CAN_setOpMode(CAN_Type *CANx, uint32_t mode);
uint32_t CAN_getOpMode(CAN_Type *CANx);
int32_t CAN_init(CAN_Type *CANx, const CAN_InitParams *initParams);
int32_t CAN_config(CAN_Type *CANx, const CAN_ConfigParams *configParams);
void CAN_eccConfig(CAN_Type *CANx, const CAN_ECCConfigParams *configParams);
int32_t CAN_setBitTime(CAN_Type *CANx, const CAN_BitTimingParams *configParams);
int32_t CAN_msgRAMConfig(CAN_Type *CANx, const CAN_MsgRAMConfigParams *msgRAMConfigParams);
int32_t CAN_setExtIDAndMask(CAN_Type *CANx, uint32_t idMask);
void CAN_writeMsgRam(CAN_Type               *CANx,
                     uint32_t               memType,
                     uint32_t               bufNum,
                     const CAN_TxBufElement *elem);
int32_t CAN_txBufAddReq(CAN_Type *CANx, uint32_t bufNum);
void CAN_getNewDataStatus(CAN_Type            *CANx,
                          CAN_RxNewDataStatus *newDataStatus);
void CAN_clearNewDataStatus(CAN_Type                  *CANx,
                            const CAN_RxNewDataStatus *newDataStatus);
void CAN_readMsgRam(CAN_Type         *CANx,
                    uint32_t         memType,
                    uint32_t         bufNum,
                    uint32_t         fifoNum,
                    CAN_RxBufElement *elem);
void CAN_readHighPriorityMsgRam(CAN_Type *CANx, CAN_RxBufElement *elem);
void CAN_readTxEventFIFO(CAN_Type               *CANx,
                         CAN_TxEventFIFOElement *txEventElem);
void CAN_addStdMsgIDFilter(CAN_Type                        *CANx,
                           uint32_t                        filtNum,
                           const CAN_StdMsgIDFilterElement *elem);
void CAN_addExtMsgIDFilter(CAN_Type                        *CANx,
                           uint32_t                        filtNum,
                           const CAN_ExtMsgIDFilterElement *elem);
void CAN_enbaleLpbkMode(CAN_Type *CANx,
                        uint32_t lpbkMode,
                        uint32_t enable);
void CAN_getErrCounters(CAN_Type         *CANx,
                        CAN_ErrCntStatus *errCounter);
void CAN_getProtocolStatus(CAN_Type           *CANx,
                           CAN_ProtocolStatus *protStatus);
void CAN_enableIntr(CAN_Type *CANx, uint32_t intrMask, uint32_t enable);

void CAN_selectIntrLine(CAN_Type *CANx,
                        uint32_t intrMask,
                        uint32_t lineNum);
uint32_t CAN_getIntrLineSelectStatus(CAN_Type *CANx);
void CAN_enableIntrLine(CAN_Type *CANx,
                        uint32_t lineNum,
                        uint32_t enable);
uint32_t CAN_getIntrStatus(CAN_Type *CANx);
void CAN_clearIntrStatus(CAN_Type *CANx, uint32_t intrMask);
void CAN_getHighPriorityMsgStatus(CAN_Type                *CANx,
                                  CAN_HighPriorityMsgInfo *hpm);
void CAN_getRxFIFOStatus(CAN_Type         *CANx,
                         CAN_RxFIFOStatus *fifoStatus);
int32_t CAN_writeRxFIFOAck(CAN_Type *CANx,
                           uint32_t fifoNum,
                           uint32_t idx);

void CAN_getTxFIFOQueStatus(CAN_Type         *CANx,
                            CAN_TxFIFOStatus *fifoStatus);
uint32_t CAN_getTxBufReqPend(CAN_Type *CANx);
int32_t CAN_txBufCancellationReq(CAN_Type *CANx, uint32_t buffNum);
uint32_t CAN_getTxBufTransmissionStatus(CAN_Type *CANx);
uint32_t CAN_txBufCancellationStatus(CAN_Type *CANx);
int32_t CAN_txBufTransIntrEnable(CAN_Type *CANx,
                                 uint32_t bufNum,
                                 uint32_t enable);
int32_t CAN_getTxBufCancellationIntrEnable(CAN_Type *CANx,
                                           uint32_t bufNum,
                                           uint32_t enable);
void CAN_getTxEventFIFOStatus(CAN_Type              *CANx,
                              CAN_TxEventFIFOStatus *fifoStatus);
void CAN_addClockStopRequest(CAN_Type *CANx, uint32_t enable);
int32_t CAN_writeTxEventFIFOAck(CAN_Type *CANx, uint32_t idx);
uint32_t CAN_getClockStopAck(CAN_Type *CANx);
uint32_t CAN_getRxPinState(CAN_Type *CANx);
void CAN_setTxPinState(CAN_Type *CANx, uint32_t state);
uint32_t CAN_getTxPinState(CAN_Type *CANx);
uint32_t CAN_getTSCounterVal(CAN_Type *CANx);
uint32_t CAN_getClkStopAck(CAN_Type *CANx);
void CAN_getBitTime(CAN_Type *CANx, CAN_BitTimingParams *configParams);
void CAN_resetTSCounter(CAN_Type *CANx);
uint32_t CAN_getTOCounterVal(CAN_Type *CANx);
uint32_t CAN_getEndianVal(CAN_Type *CANx);
uint32_t CAN_getExtIDANDMask(CAN_Type *CANx);
uint32_t CAN_getMsgObjSize(uint32_t elemSize);

void CAN_enableDMUIntr(CAN_Type *CANx, uint32_t intrMask, uint32_t enable);
void CAN_enableDMUTransferTS(CAN_Type *CANx, uint32_t enable);
int32_t CAN_configTSU(CAN_Type *CANx, const CAN_TSUConfigParams *configParams);
void CAN_setDMURxRequest(CAN_Type *CANx, CAN_DMURxRequest Request);
void CAN_copyMsgToBuffer(const CAN_TxBufElement *elem, uint32_t *buffer);
void CAN_copyBufferToMsg(uint32_t *buffer, CAN_RxBufElement *elem);


/**
 * @}
 */

/**
 * @}
 */

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/
/* PSR.LEC/DLEC encodings; 7 means no change since the previous read. */
typedef enum
{
    CAN_TEST_ERROR_NONE = 0U,
    CAN_TEST_ERROR_STUFF = 1U,
    CAN_TEST_ERROR_FORM = 2U,
    CAN_TEST_ERROR_ACK = 3U,
    CAN_TEST_ERROR_BIT1 = 4U,
    CAN_TEST_ERROR_BIT0 = 5U,
    CAN_TEST_ERROR_CRC = 6U,
    CAN_TEST_ERROR_UNCHANGED = 7U
} CAN_TestErrorCode;

/* PSR.ACT reports synchronization, idle, receiver or transmitter activity. */
typedef enum
{
    CAN_TEST_ACTIVITY_SYNCHRONIZING = 0U,
    CAN_TEST_ACTIVITY_IDLE = 1U,
    CAN_TEST_ACTIVITY_RECEIVER = 2U,
    CAN_TEST_ACTIVITY_TRANSMITTER = 3U
} CAN_TestActivity;
/** ET6801 Message RAM aperture: driver uses CANx - 0x4000, UT5 tests 16 KiB. */
#define CAN_TEST_MSG_RAM_BYTES (0x4000U)
/** Access aligned words only within this controller's Message RAM, while INIT is set.
 * Optional input writes each word; optional output reads it before the write.
 * Descending changes visit order, not the ascending-offset array layout.
 * The primitive performs no pattern generation, comparison, retry or verdict.
 */
int32_t CAN_testAccessRAMWords(CAN_Type *CANx, uint32_t offset, uint32_t count,
                               const uint32_t *input, uint32_t *output, uint32_t descending);
/** Message RAM R0/T0 stores standard ID in ID[28:18], extended ID in ID[28:0]. */
#define CAN_TEST_STANDARD_ID_SHIFT (18U)
#define CAN_TEST_STANDARD_ID_MAX (0x7FFU)
#define CAN_TEST_EXTENDED_ID_MAX (0x1FFFFFFFU)
/** Basic TX element stores an eight-bit marker; wide-marker mode is a separate operation. */
#define CAN_TEST_BASIC_MARKER_MAX (0xFFU)
/** Read protocol payload length; FD and Remote selectors use existing SDK values. */
uint32_t CAN_testGetPayloadSize(uint32_t dlc, uint32_t fd, uint32_t remote);
/** Write one atomic TXBAR request mask; caller validates allocated-buffer membership. */
void CAN_testRequestTxMask(CAN_Type *CANx, uint32_t mask);
/** TX RAM has two header words followed by the configured payload capacity. */
#define CAN_TEST_TX_HEADER_WORDS (2U)
/** Read one allocated TX RAM element without starting, cancelling or acknowledging it. */
int32_t CAN_testReadTxBuffer(CAN_Type *CANx, uint32_t index, CAN_TxBufElement *element);
/** Controller architectural maxima; field widths alone also encode reserved values. */
#define CAN_TEST_STD_FILTER_MAX (128U)
#define CAN_TEST_EXT_FILTER_MAX (64U)
#define CAN_TEST_RX_FIFO_MAX (64U)
#define CAN_TEST_TX_EVENT_MAX (32U)
/** Read exact RAM configuration; offsets are bytes, not absolute addresses. */
void CAN_testGetMsgRAMConfig(CAN_Type *CANx, CAN_MsgRAMConfigParams *config);
/** Read operating mode, global acceptance and timestamp/timeout configuration. */
void CAN_testGetConfig(CAN_Type *CANx, CAN_ConfigParams *config);
/** Read TEST/LBCK and MON controls without changing controller state. */
void CAN_testGetLoopback(CAN_Type *CANx, uint32_t *enabled, CAN_LpbkMode *mode);
/** Read the controller revision without altering configuration or status. */
uint32_t CAN_testGetRevision(CAN_Type *CANx);
/** Read the actual core initialization controls, including watchdog and TDC. */
void CAN_testGetInitConfig(CAN_Type *CANx, CAN_InitParams *initParams);
/** M_CAN extended EFT=3 bypasses XIDAM; standard SFT=3 instead disables the entry. */
#define CAN_TEST_EXTFILT_RANGE_NO_MASK (3U)
/** Read one configured filter from Message RAM, without writing acceptance state. */
int32_t CAN_testGetStdMsgIDFilter(CAN_Type *CANx, uint32_t index, CAN_StdMsgIDFilterElement *element);
int32_t CAN_testGetExtMsgIDFilter(CAN_Type *CANx, uint32_t index, CAN_ExtMsgIDFilterElement *element);
/** Read IE, ILS and ILE once each without consuming IR. */
void CAN_testGetInterruptConfig(CAN_Type *CANx, uint32_t *enabled, uint32_t *lineSelection,
                                uint32_t *lineEnabled);
/** Change/read CCE only; caller must already hold INIT. No timing writes. */
int32_t CAN_testConfigurationAccess(CAN_Type *CANx, uint32_t enable, uint32_t *actual);
/** Write NBTP without automatically opening CCE, allowing hardware protection observation. */
int32_t CAN_testWriteNominalTiming(CAN_Type *CANx, const CAN_BitTimingParams *timing);
/** Select CCCR.NISO in INIT while preserving CCE; non-NULL actual selects read only. */
int32_t CAN_testNonIsoAccess(CAN_Type *CANx, uint32_t enable, uint32_t *actual);
/** M_TTCAN 3.3.0 sections 2.4.3/2.4.4: T1/E1B bits 15:8 carry MM[15:8]. */
#define CAN_TEST_MARKER_HIGH_MASK (0x0000FF00U)
#define CAN_TEST_MARKER_BITS_BASIC (8U)
#define CAN_TEST_MARKER_BITS_WIDE (16U)
/** E1B bit 4 reports captured TSU timestamp; bits 3:0 select TS0..15. */
#define CAN_TEST_EVENT_TSC_MASK (0x10U)
#define CAN_TEST_EVENT_POINTER_MASK (0x0FU)
typedef struct
{
    uint32_t internalTimestampValid;
    uint32_t tsuCaptured;
    uint32_t tsuPointer;
} CAN_TestEventMetadata;
/** Effective marker width is wide when either WMM or UTSU is set. */
void CAN_testGetEventFormat(CAN_Type *CANx, uint32_t *markerBits, uint32_t *tsuEnabled);
/** Require INIT, preserve CCE, and explicitly configure both WMM and UTSU. */
int32_t CAN_testSetEventFormat(CAN_Type *CANx, uint32_t markerBits, uint32_t tsuEnabled);
/** Write one non-pending allocated TX slot, preserving the complete wide marker. */
int32_t CAN_testWriteTxElement(CAN_Type *CANx, uint32_t index, const CAN_TxBufElement *element);
/** Decode E1A/E1B using actual format; invalid internal timestamp/pointer fields are zero. */
void CAN_testReadTxEvent(CAN_Type *CANx, CAN_TxEventFIFOElement *element,
                         CAN_TestEventMetadata *metadata);
/** Continuous timeout only: read old count, write TOCV once, immediately read actual count. */
int32_t CAN_testReloadTimeout(CAN_Type *CANx, uint32_t *before, uint32_t *after);
/** Internal timestamp only: read, single reset write, read; no IRQ clear or polling. */
int32_t CAN_testResetTimestampSnapshot(CAN_Type *CANx, uint32_t *before, uint32_t *after);
/** TSU access uses only the explicitly mapped TS0, never guessed TS2..15 addresses. */
/** ET6801 SVD TSS2.NTSG: encodings 0..2 mean 4, 8, 16 slots; 3 is reserved. */
#define CAN_TEST_TSU_SLOT_ENCODING_MAX (2U)
#define CAN_TEST_TSU_MIN_SLOTS (4U)
int32_t CAN_testSetTsu(CAN_Type *CANx, const CAN_TSUConfigParams *config);
void CAN_testGetTsu(CAN_Type *CANx, CAN_TSUConfigParams *config);
int32_t CAN_testGetTsuLimits(CAN_Type *CANx, uint32_t *slots, uint32_t *internal, uint32_t *sof);
void CAN_testGetTsuFlags(CAN_Type *CANx, uint32_t *newFlags, uint32_t *lostFlags);
uint32_t CAN_testGetTsuTimebase(CAN_Type *CANx);
uint32_t CAN_testConsumeTsuSlot0(CAN_Type *CANx);
/********************* TEST DRIVER EXTENSION END *********************/
#endif

#ifdef __cplusplus
}
#endif

#endif /* __ET6X_CAN_H */
