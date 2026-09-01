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

#ifndef __ET6x_LIN_H
#define __ET6x_LIN_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup LIN
 * @{
 */

/**
 * @brief Useful defines used within the driver functions. Not intended for use by application code.
 */

/* The IO DFT Enable Key */
#define LIN_IO_DFT_KEY               (0xAU)  /* LIN IO DFT Key */
/* LIN Wakeup Signal Key */
#define LIN_WAKEUP_KEY               (0xF0U) /* LIN Wakeup Key */

/* LIN Parity ID Masks */
#define LIN_ID0                      (0x1U)  /* LIN Parity ID0 Mask */
#define LIN_ID1                      (0x2U)  /* LIN Parity ID1 Mask */
#define LIN_ID2                      (0x4U)  /* LIN Parity ID2 Mask */
#define LIN_ID3                      (0x8U)  /* LIN Parity ID3 Mask */
#define LIN_ID4                      (0x10U) /* LIN Parity ID4 Mask */
#define LIN_ID5                      (0x20U) /* LIN Parity ID5 Mask */

/* LIN WORK MODE STATUS */
#define LIN_INITAL_STATE             (0x1U) /* LIN work status in initial state */
#define LIN_NORMAL_STATE             (0x2U) /* LIN work status in normal state */
#define LIN_SLEEP_STATE              (0x4U) /* LIN work status in sleep state */

/**
 * @brief Definitions for the intFlags parameter of LIN_enableFuncInterrupt(), LIN_disableFuncInterrupt(),
 * LIN_clearFuncInterruptStatus(), LIN_getFuncInterruptStatus().
 */
#define LIN_FUNC_INT_ALL             (0x000000FFU)        /* function interrupt full mask */
#define LIN_FUNC_INT_SYNC_DONE       (0x00000001U)        /* function interrupt Synchronization done */
#define LIN_FUNC_INT_HEAD_TX_DONE    (0x00000002U)        /* function interrupt head transmit done */
#define LIN_FUNC_INT_HEAD_RX_DONE    (0x00000004U)        /* function interrupt head receive done */
#define LIN_FUNC_INT_RSP_TX_DONE     (0x00000008U)        /* function interrupt response transmit done */
#define LIN_FUNC_INT_RSP_RX_DONE     (0x00000010U)        /* function interrupt response receive done */
#define LIN_FUNC_INT_WAKEUP          (0x00000020U)        /* function interrupt wakeup signal */
#define LIN_FUNC_INT_SLEEP           (0x00000040U)        /* function interrupt sleep signal */
#define LIN_FUNC_INT_ABORT           (0x00000080U)        /* function interrupt frame transmit stop signal */

/**
 * @brief Definitions for the intFlags parameter of LIN_enableErrorInterrupt(), LIN_disableErrorInterrupt(),
 * LIN_clearErrorInterruptStatus(), LIN_getErrorInterruptStatus().
 */
#define LIN_ERR_INT_ALL              (0x000000FFU)        /* Error interrupt full mask */
#define LIN_ERR_INT_HEAD_ERR         (0x00000001U)        /* frame head detection Error interrupt */
#define LIN_ERR_INT_RSP_ERR          (0x00000002U)        /* frame response detection error interrupt */
#define LIN_ERR_INT_ID_PARITY_ERR    (0x00000004U)        /* frame head ID parity error interrupt */
#define LIN_ERR_INT_CHECKSUM_ERR     (0x00000008U)        /* frame response checksum error interrupt */
#define LIN_ERR_INT_TIMEOUT_ERR      (0x00000010U)        /* frame response timeout error interrupt */
#define LIN_ERR_INT_OVERSAMP_ERR     (0x00000020U)        /* frame signal oversampling error interrupt */
#define LIN_ERR_INT_STUCK_ERR        (0x00000040U)        /* frame signal stuck error interrupt */
#define LIN_ERR_INT_COLLISION_ERR    (0x00000080U)        /* online data detect collision error interrupt */

/**
 * @brief Definitions for the ID filter parameter of LIN_setMessageFiltering().
 */
#define LIN_ID_FILTER_0              (0x0001U)  /* ID Filter 0 */
#define LIN_ID_FILTER_1              (0x0002U)  /* ID Filter 1 */
#define LIN_ID_FILTER_2              (0x0004U)  /* ID Filter 2 */
#define LIN_ID_FILTER_3              (0x0008U)  /* ID Filter 3 */
#define LIN_ID_FILTER_4              (0x0010U)  /* ID Filter 4 */
#define LIN_ID_FILTER_5              (0x0020U)  /* ID Filter 5 */
#define LIN_ID_FILTER_6              (0x0040U)  /* ID Filter 6 */
#define LIN_ID_FILTER_7              (0x0080U)  /* ID Filter 7 */
#define LIN_ID_FILTER_8              (0x0100U)  /* ID Filter 8 */
#define LIN_ID_FILTER_9              (0x0200U)  /* ID Filter 9 */
#define LIN_ID_FILTER_10             (0x0400U)  /* ID Filter 10 */
#define LIN_ID_FILTER_11             (0x0800U)  /* ID Filter 11 */
#define LIN_ID_FILTER_12             (0x1000U)  /* ID Filter 12 */
#define LIN_ID_FILTER_13             (0x2000U)  /* ID Filter 13 */
#define LIN_ID_FILTER_14             (0x4000U)  /* ID Filter 14 */
#define LIN_ID_FILTER_15             (0x8000U)  /* ID Filter 15 */

/**
 * @brief Definitions for the parity and checksum error inject parameter of LIN_setParityInject() and
 * LIN_setChecksumInject().
 */
typedef enum
{
    LIN_ERROR_INJECT_NONE            = 0U, /* parity and checksum error inject none */
    LIN_ERROR_INJECT_RECIVE          = 1U, /* Recive error inject */
    LIN_ERROR_INJECT_TRANSMIT        = 2U, /* Transmit error inject */
    LIN_ERROR_INJECT_RECIVE_TRANSMIT = 3U  /* Recive and Transmit error inject */
} LIN_ParityChecksumErrInject;

/**
 * @brief Slave Sync Break Select
 */
typedef enum
{
    LIN_SLV_SYNCBREAK_10BIT = 0U,    /* Slave Sync Break at least 10 bit */
    LIN_SLV_SYNCBREAK_11BIT = 1U     /* Slave Sync Break at least 11 bit */
} LIN_SlvSyncBreakSel;

/**
 * @brief Response Space Select
 */
typedef enum
{
    LIN_RSP_SPACE_NO    = 0U, /* Response Space None */
    LIN_RSP_SPACE_1BIT  = 1U, /* Response Space 1 */
    LIN_RSP_SPACE_2BIT  = 2U, /* Response Space 2 */
    LIN_RSP_SPACE_4BIT  = 3U, /* Response Space 3 */
    LIN_RSP_SPACE_8BIT  = 4U, /* Response Space 8 */
    LIN_RSP_SPACE_16BIT = 5U, /* Response Space 16 */
    LIN_RSP_SPACE_18BIT = 4U, /* Response Space 18 */
    LIN_RSP_SPACE_24BIT = 5U  /* Response Space 24 */
} LIN_rspSpaceSel;

/**
 * @brief Byte Space Select
 */
typedef enum
{
    LIN_BYTE_SPACE_NO   = 0U,  /* Byte Space None */
    LIN_BYTE_SPACE_1BIT = 1U,  /* Byte Space 1 */
    LIN_BYTE_SPACE_2BIT = 2U,  /* Byte Space 2 */
    LIN_BYTE_SPACE_3BIT = 3U   /* Byte Space 4 */
} LIN_byteSpaceSel;

/**
 * @brief The following are defines for the \b mode parameter of the LIN_setCommMode() function.
 */
typedef enum
{
    /* Use the length indicated in the LENGTH field of the LIN DATA_LEN register */
    LIN_COMM_LIN_USELENGTHVAL = 0x0000U,

    /* Use ID4 and ID5 to convey the length */
    LIN_COMM_LIN_ID4ID5LENCTL = 0x0001U
} LIN_CommMode;

/**
 * @brief The following are defines for the \b mode parameter of the LIN_setLINMode() function.
 */
typedef enum
{
    LIN_MODE_SLAVE = 0x0U, /* The node is in slave mode */
    LIN_MODE_MASTER        /* The node is in master mode */
} LIN_LINMode;


/**
 * @brief The following are defines for the \b type parameter of the LIN_setMessageFiltering() function.
 */
typedef enum
{
    LIN_MSG_FILTER_ID_LIST_MODE = 0x0U,        /* LIN Message ID List Filtering: Response is made only when the received
                                                * ID completely matches the filter ID */
    LIN_MSG_FILTER_ID_MASK_MODE = 0x1U         /* LIN Message ID Mask Filtering: The received ID is ANDed with the mask
                                                * ID first, and then compared with the filter ID for a match before
                                                * making a response */
} LIN_MessageFilter;

/**
 * @brief The following are defines for the \b type parameter of the LIN_setChecksumType() function.
 */
typedef enum
{
    LIN_CHECKSUM_CLASSIC  = 0x0U,    /* Checksum Classic */
    LIN_CHECKSUM_ENHANCED = 0x1U     /* Checksum Enhanced */
} LIN_ChecksumType;

/**
 * @brief LIN ID Filter Configuration Structure
 */
typedef struct __PACKED
{
    uint16_t         dataLength;
    LIN_ChecksumType checksumMode;   /* false: Checksum Classic, true: Checksum Enhanced */
    ControlStatus    rsp_Transmit;   /* true: Response Transmit, false: Response Receive */
    uint16_t         maskId;
    uint16_t         filterId;
} LIN_IDFilterConfig;

/* Configuration */
void LIN_enableModule(LIN_Type *LINx);
void LIN_disableModule(LIN_Type *LINx);
void LIN_setLINMode(LIN_Type *LINx, LIN_LINMode mode);
void LIN_setBaudRate(LIN_Type *LINx, uint32_t baudrate);
void LIN_enableAutomaticBaudrate(LIN_Type *LINx);
void LIN_disableAutomaticBaudrate(LIN_Type *LINx);
void LIN_softAutoBaudSyncRequest(LIN_Type *LINx);
void LIN_setChecksumType(LIN_Type *LINx, LIN_ChecksumType type);
void LIN_setSyncFields(LIN_Type *LINx, uint16_t syncBreak, uint16_t delimiter);
void LIN_setSlaveSyncFields(LIN_Type *LINx, LIN_SlvSyncBreakSel syncBreak);
void LIN_setSpaceLen(LIN_Type *LINx, LIN_rspSpaceSel rsp_space, LIN_byteSpaceSel byte_space);
uint16_t LIN_generateParityID(uint16_t identifier);
void LIN_setIDByte(LIN_Type *LINx, uint16_t identifier);
uint16_t LIN_getRxIdentifier(LIN_Type *LINx);
void LIN_setFrameLength(LIN_Type *LINx, uint16_t length);
void LIN_setCommMode(LIN_Type *LINx, LIN_CommMode mode);
void LIN_softSendHeadRequest(LIN_Type *LINx);
void LIN_softFrameRepTransmit(LIN_Type *LINx);
void LIN_softFrameRspReceive(LIN_Type *LINx);
void LIN_setParityInject(LIN_Type *LINx, LIN_ParityChecksumErrInject parity);
void LIN_setChecksumInject(LIN_Type *LINx, LIN_ParityChecksumErrInject checksum);
uint16_t LIN_getOPStatus(LIN_Type *LINx);
uint16_t LIN_getSlaveTransByteCountRPT(LIN_Type *LINx);

/*  Power management */
void LIN_enterSleep(LIN_Type *LINx, uint8_t sleeptime);
void LIN_sendWakeupSignal(LIN_Type *LINx);
void LIN_enterWakeup(LIN_Type *LINx, uint8_t waketime);
void LIN_enterTimeOut(LIN_Type *LINx, uint8_t value);
void LIN_enableLowPowerBypass(LIN_Type *LINx);

/* filter ID */
void LIN_enableIDFilterBypass(LIN_Type *LINx);
void LIN_setIDFilter(LIN_Type *LINx, uint32_t ID_Filter, LIN_MessageFilter type);
void LIN_enableIDFilter(LIN_Type *LINx, uint32_t ID_Filter);
void LIN_disableIDFilter(LIN_Type *LINx, uint32_t ID_Filter);
uint16_t LIN_getIDFilterMatchRPT(LIN_Type *LINx);
bool LIN_isRxMatch(LIN_Type *LINx, uint32_t ID_Filter);
void LIN_initIDFilterStruct(LIN_IDFilterConfig *pConfig);
void LIN_initIDFilter(LIN_Type *LINx, uint32_t ID_Filter, LIN_IDFilterConfig *pConfig);

/* Function interrupt */
void LIN_enableFuncInterrupt(LIN_Type *LINx, uint32_t intFlags);
void LIN_disableFuncInterrupt(LIN_Type *LINx, uint32_t intFlags);
void LIN_clearFuncInterruptStatus(LIN_Type *LINx, uint32_t intFlags);
uint32_t LIN_getFuncInterruptStatus(LIN_Type *LINx);

/* Error interrupt */
void LIN_enableErrorInterrupt(LIN_Type *LINx, uint32_t intFlags);
void LIN_disableErrorInterrupt(LIN_Type *LINx, uint32_t intFlags);
void LIN_clearErrorInterruptStatus(LIN_Type *LINx, uint32_t intFlags);
uint32_t LIN_getErrorInterruptStatus(LIN_Type *LINx);

/* loopback */
void LIN_enableIntLoopback(LIN_Type *LINx);
void LIN_disableIntLoopback(LIN_Type *LINx);

/* Init module */
void LIN_initModule(LIN_Type *LINx);
void LIN_sendData(LIN_Type *LINx, uint8_t *data);
void LIN_getData(LIN_Type *LINx, uint8_t * const data);


//*****************************************************************************
//
// Close the Doxygen group.
//! @}
//
//*****************************************************************************

//*****************************************************************************
//
// Mark the end of the C bindings section for C++ compilers.
//
//*****************************************************************************

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /* __ET6x_LIN_H */
