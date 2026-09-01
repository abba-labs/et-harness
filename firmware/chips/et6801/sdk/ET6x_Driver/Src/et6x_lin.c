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
#include "et6x_lin.h"

#define IS_LIN_PERIPH(PERIPH)    (((PERIPH) == LIN0) || ((PERIPH) == LIN1))
#define IS_LIN_ID_FILTER(FILTER) \
        (((FILTER) == LIN_ID_FILTER_0) || \
         ((FILTER) == LIN_ID_FILTER_1) || \
         ((FILTER) == LIN_ID_FILTER_2) || \
         ((FILTER) == LIN_ID_FILTER_3) || \
         ((FILTER) == LIN_ID_FILTER_4) || \
         ((FILTER) == LIN_ID_FILTER_5) || \
         ((FILTER) == LIN_ID_FILTER_6) || \
         ((FILTER) == LIN_ID_FILTER_7) || \
         ((FILTER) == LIN_ID_FILTER_8) || \
         ((FILTER) == LIN_ID_FILTER_9) || \
         ((FILTER) == LIN_ID_FILTER_10) || \
         ((FILTER) == LIN_ID_FILTER_11) || \
         ((FILTER) == LIN_ID_FILTER_12) || \
         ((FILTER) == LIN_ID_FILTER_13) || \
         ((FILTER) == LIN_ID_FILTER_14) || \
         ((FILTER) == LIN_ID_FILTER_15))

#define LIN_CLK    (25000000UL)     /* SYSCLK */

/**
 * @brief Enables the LIN module.
 *  In LIN mode, the transmit and receive pin control functionality isenabled.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_enableModule(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->EN, LIN0_EN_LIN_EN_Msk);
}

/**
 * @brief Disable the LIN module.
 *  in LIN mode, the transmit and receive pin control functionality is disabled.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_disableModule(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    CLEAR_BIT(LINx->EN, LIN0_EN_LIN_EN_Msk);
}

/**
 * @brief Set LIN mode
 * In LIN mode, this function sets the mode of the LIN mode to either
 * responder or commander.
 *
 * @param base is the LIN module base address
 * @param mode is the desired mode (responder or commander)
 *
 * @return None.
 */
void LIN_setLINMode(LIN_Type *LINx, LIN_LINMode mode)
{
    assert_param(IS_LIN_PERIPH(LINx));

    if (mode == LIN_MODE_MASTER)
    {
        SET_BIT(LINx->MODE, LIN0_MODE_MODE_Msk);
    }
    else
    {
        CLEAR_BIT(LINx->MODE, LIN0_MODE_MODE_Msk);
    }
}

/**
 * @brief Set Baud Rate
 *  In LIN and SCI mode, this function is used to set the baudrate values.
 *
 * @param LINx is the LIN module LINx address
 * @param baudrate is the 16-bit integer value
 *
 * AUTOBAUD_VAL = (SYSCLOCK) / (baudrate)
 *
 * @return None.
 */
void LIN_setBaudRate(LIN_Type *LINx, uint32_t baudrate)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->AUTOBAUD_VAL, LIN0_AUTOBAUD_VAL_BAUD_VAL_Msk, (LIN_CLK) / baudrate);
}

/**
 * @brief Enable Automatic Baudrate Adjustment
 *  In LIN mode, this function enables the automatic baudrate adjustment
 *  mode during the detection of the Synch Field.
 *
 * @param LINx is the LIN module LINx address
 *
 * @note The baudrate selection register will be updated automatically by a
 *  responder node if this mode is enabled.
 *
 * @return None.
 */
void LIN_enableAutomaticBaudrate(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Enable automatic baudrate adjustment */
    SET_BIT(LINx->AUTOBAUD_EN, LIN0_AUTOBAUD_EN_AUTOBAUD_EN_Msk);
}

/**
 * @brief Disable Automatic Baudrate Adjustment
 *  In LIN mode, this function disables the automatic baudrate adjustment
 *  mode during the detection of the Synch Field. This results in a fixed
 *  baud rate.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_disableAutomaticBaudrate(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Disable automatic baudrate adjustment */
    CLEAR_BIT(LINx->AUTOBAUD_EN, LIN0_AUTOBAUD_EN_AUTOBAUD_EN_Msk);
}

/**
 * @brief Soft Automatic Baudrate Sync Request
 *  In LIN mode, this function requests the LIN Slave node to perform a soft
 *  automatic baudrate synchronization.
 *
 * @param LINx is the LIN module LINx address
 * @note Initiated by software, automatically cleared by hardware upon synchronization completion
 *
 * @return None.
 */
void LIN_softAutoBaudSyncRequest(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->AUTOBAUD_REQ, LIN0_AUTOBAUD_REQ_AUTOBAUD_REQ_Msk);
}

/**
 * @brief Set Checksum Type
 *  In LIN mode only, this function sets the checksum type. The type
 *  parameter can be one of the following two values:
 * - LIN_CHECKSUM_CLASSIC  - Checksum Classic
 * - LIN_CHECKSUM_ENHANCED - Checksum Enhanced
 *
 * @param LINx is the LIN module LINx address
 * @param type is the checksum type
 *
 * @return None.
 */
void LIN_setChecksumType(LIN_Type *LINx, LIN_ChecksumType type)
{
    assert_param(LINx == LIN0 || LINx == LIN1);

    if (type == LIN_CHECKSUM_ENHANCED)
    {
        SET_BIT(LINx->CHKSUM, LIN0_CHKSUM_CHECKSUM_MODE_Msk);
    }
    else
    {
        CLEAR_BIT(LINx->CHKSUM, LIN0_CHKSUM_CHECKSUM_MODE_Msk);
    }
}

/**
 * @brief Set Sync Break Extend and Delimiter
 *  In LIN mode only, this function sets the 4-bit sync break extend value
 *  and the 1-bit sync delimiter compare value.
 *
 * @param LINx is the LIN module LINx address
 * @param syncBreak is the sync break extend value
 * @param delimiter is the sync delimiter value
 *
 * The break parameter can be a value between 0 to 7. Details:
 * - 0 - Sync Break has 13 T-bit
 * - 1 - Sync Break has 14 T-bit
 * - ...
 * - 15 - Sync Break has 28 T-bits
 *
 * The delimiter parameter can be a value between 1 to 4. Details:
 * - 0 - Delimiter has 1 T-bit
 * - 1 - Delimiter has 2 T-bits
 *
 * @return None.
 */
void LIN_setSyncFields(LIN_Type *LINx, uint16_t syncBreak, uint16_t delimiter)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(syncBreak < 16U);

    if (READ_REG(LINx->MODE) != 0)
    {
        WRITE_REG(LINx->MST_SYNCBREAK_SEL, syncBreak);
    }
    else
    {
        WRITE_REG(LINx->SLV_SYNCBREAK_SEL, syncBreak);
    }

    WRITE_REG(LINx->DELIMITER_LEN, delimiter);
}

/**
 * @brief Set Slave Sync Break
 *  In LIN mode only, this function sets the slave sync break extend value.
 * - 0 - Slave Sync Break at least 10 bit
 * - 1 - Slave Sync Break at least 11 bit
 *
 * @param LINx is the LIN module LINx address
 * @param syncBreak is the sync break extend value
 *
 * @return None.
 */
void LIN_setSlaveSyncFields(LIN_Type *LINx, LIN_SlvSyncBreakSel syncBreak)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->SLV_SYNCBREAK_SEL, LIN0_SLV_SYNCBREAK_SEL_SLV_SYNCBREAK_SEL_Msk,
               ((uint32_t)syncBreak << LIN0_SLV_SYNCBREAK_SEL_SLV_SYNCBREAK_SEL_Pos));
}

/**
 * @brief Set frame space length
 *  In LIN mode only, this function sets the frame space length. send data byte break and slave task response break
 * - 0 - Slave Sync Break at least 10 bit
 * - 1 - Slave Sync Break at least 11 bit
 *
 * @param LINx is the LIN module LINx address
 * @param rsp_space is the response space select
 * @param byte_space is the byte space select
 *
 * @return None.
 */
void LIN_setSpaceLen(LIN_Type *LINx, LIN_rspSpaceSel rsp_space, LIN_byteSpaceSel byte_space)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->SPACE_LEN, LIN0_SPACE_LEN_RSP_SPACE_SEL_Msk | LIN0_SPACE_LEN_BYTE_SPACE_SEL_Msk,
               ((uint32_t)rsp_space << LIN0_SPACE_LEN_RSP_SPACE_SEL_Pos) |
               ((uint32_t)byte_space << LIN0_SPACE_LEN_BYTE_SPACE_SEL_Pos));
}

/**
 * @brief Generate Parity Identifier
 *  In LIN mode, this function generates the identifier parity bits and
 *  appends them to the identifier.
 *
 * @param identifier is the LIN header ID byte
 *
 * @note An ID must be generated with parity before header generation in
 *  LIN commander mode.
 *
 * @return Returns the identifier appended with parity bits.
 */
uint16_t LIN_generateParityID(uint16_t identifier)
{
    uint16_t p0, p1, parityIdentifier;

    /* Calculate parity bits and generate updated identifier */
    p0 = ((identifier & LIN_ID0) ^ ((identifier & LIN_ID1) >> 1U) ^
          ((identifier & LIN_ID2) >> 2U) ^ ((identifier & LIN_ID4) >> 4U));
    p1 = !(((identifier & LIN_ID1) >> 1U) ^ ((identifier & LIN_ID3) >> 3U) ^
           ((identifier & LIN_ID4) >> 4U) ^ ((identifier & LIN_ID5) >> 5U));
    parityIdentifier = (uint16_t)(identifier | (((uint16_t)p0 << 6U) | ((uint16_t)p1 << 7U)));

    return(parityIdentifier);
}

/**
 * @brief Set ID Byte
 *  In LIN mode, this function sets the message ID byte. In commander mode,
 *  writing to this ID initiates a header transmission. In responder task, this
 *  ID is used for message filtering .
 *
 * @param LINx is the LIN module LINx address
 * @param identifier is the LIN header ID byte
 *
 * @return None.
 */
void LIN_setIDByte(LIN_Type *LINx, uint16_t identifier)
{
    assert_param(IS_LIN_PERIPH(LINx));

    WRITE_REG(LINx->TX_ID, identifier);
}

/**
 * @brief Get last received identifier
 *  In LIN mode only, this function gets the last received identifier.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return Returns the Received Identifier.
 */
uint16_t LIN_getRxIdentifier(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    return (uint16_t)READ_BIT(LINx->RX_ID, LIN0_RX_ID_RX_ID_Msk);
}

/**
 * @brief Set LIN Frame Length
 *  In LIN mode only, this function sets the number of bytes in the response
 *  field.
 *
 * @param LINx is the LIN module LINx address
 * @param length is the number of bytes.
 *
 * The length parameter must be in a range between 1 and 8.
 *
 * @return None.
 */
void LIN_setFrameLength(LIN_Type *LINx, uint16_t length)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param((length > 0U) && (length < 9U));

    /* Clear and set frame length value */
    CLEAR_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_MODE_Msk);
    MODIFY_REG(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_Msk, ((uint32_t)(length - 1) << LIN0_DATA_LEN_DATA_LEN_Pos));
}

/**
 * @brief Set LIN communication mode
 *  In LIN mode only, this function is used to choose how the length of data is
 *  conveyed. This choice relates to the version of LIN being used. The mode
 *  parameter can have one of two values:
 *  - LIN_COMM_LIN_USELENGTHVAL will use the length set with the
 *    LIN_setFrameLength() function.
 *  - LIN_COMM_LIN_ID4ID5LENCTL will use ID4 and ID5 for length control.
 *  - [ID5,ID4] = 00 -> 2byte
 *  - [ID5,ID4] = 01 -> 2byte
 *  - [ID5,ID4] = 10 -> 4byte
 *  - [ID5,ID4] = 11 -> 8byte
 *
 * @param LINx is the LIN module LINx address
 * @param mode is the selected communication mode
 *
 * @return None.
 */
void LIN_setCommMode(LIN_Type *LINx, LIN_CommMode mode)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Write communication mode selection to the appropriate bit */
    if (mode == LIN_COMM_LIN_ID4ID5LENCTL)
    {
        SET_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_MODE_Msk);
    }
    else
    {
        CLEAR_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_MODE_Msk);
    }
}

/**
 * @brief Send LIN head request
 *  In LIN mode only, this function is used to send a head request.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_softSendHeadRequest(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->HEAD_REQ, LIN0_HEAD_REQ_HEAD_REQ_Msk);
}

/**
 * @brief Soft Frame Rep Transmit
 *  In LIN mode only, this function is the slave node responds with the frame ID to
 *  perform transmission action after receiving the frame header.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_softFrameRepTransmit(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->RSP_REQ, LIN0_RSP_REQ_RSP_REQ_Msk);
    SET_BIT(LINx->RSP_TRANSMIT, LIN0_RSP_TRANSMIT_RSP_TRANSMIT_Msk);
}

/**
 * @brief Soft Frame Rsp Receive
 *  In LIN mode only, this function is the slave node receives the frame response.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_softFrameRspReceive(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->RSP_REQ, LIN0_RSP_REQ_RSP_REQ_Msk);
    CLEAR_BIT(LINx->RSP_TRANSMIT, LIN0_RSP_TRANSMIT_RSP_TRANSMIT_Msk);
}

/**
 * @brief Enter LIN Sleep Mode.
 *  In LIN mode, this function puts the LIN module into a low-power, sleep
 *  mode. This can also be called to forcefully enter sleep when there is no
 *  activity on the bus.
 *
 * @param LINx is the LIN module LINx address
 * @param sleeptime is the sleep time in number of sec
 * sleeptime : 0 --- 4s
 * sleeptime : 1 --- 5s
 * ...
 * sleeptime : 7 --- 10s
 *
 * @note If this function is called while the receiver is actively receiving
 *  data and the wakeup interrupt is disabled, then the module will delay
 *  sleep mode from being entered until completion of reception.
 *
 * @return None.
 */
void LIN_enterSleep(LIN_Type *LINx, uint8_t sleeptime)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param((sleeptime >= 0U) && (sleeptime <= 7U));

    MODIFY_REG(LINx->SLEEP, LIN0_SLEEP_SLEEP_TIME_Msk, ((uint32_t)sleeptime << LIN0_SLEEP_SLEEP_TIME_Pos));
    SET_BIT(LINx->SLEEP, LIN0_SLEEP_SLEEP_EN_Msk);
}

/**
 * @brief Send LIN wakeup signal
 *  In LIN mode, this function sends the LIN wakeup signal to terminate
 *  the sleep mode of any LIN node connected to the bus.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_sendWakeupSignal(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    WRITE_REG(LINx->WAKEUP_REQ, LIN0_WAKEUP_REQ_WAKEUP_REQ_Msk);
}

/**
 * @brief Enter LIN Wakeup Mode
 *  In LIN mode, this function puts the LIN module into a low-power, wakeup
 *  mode. This can also be called to forcefully enter wakeup when there is no
 *  activity on the bus.
 *
 * @param LINx is the LIN module LINx address
 * @param waketime is the wakeup time in number of time
 * waketime : 0 --- 250us
 * waketime : 1 --- 500us
 * waketime : 2 --- 2ms
 * waketime : 3 --- 5ms
 *
 * @return None.
 */
void LIN_enterWakeup(LIN_Type *LINx, uint8_t waketime)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->WAKEUP, LIN0_WAKEUP_MST_WAKEUP_TIME_Msk, ((uint32_t)waketime << LIN0_WAKEUP_MST_WAKEUP_TIME_Pos));
    SET_BIT(LINx->WAKEUP, LIN0_WAKEUP_WAKEUP_EN_Msk);
}

/**
 * @brief Enter LIN Timeout Mode
 *  In LIN mode, this function used for timeout configuration.
 *  For the master node, timeout occurs in cases such as no slave response, slave responding too late,
 *  or the response not being completed within the maximum frame time slot.
 *  For the slave node, timeout occurs when the software does not set the rsp_req for a long time after
 *  receiving a frame and needing to respond, or when the slave does not receive the frame header from
 *  the master node within 150ms after sending a valid wake-up signal.
 *
 * @param LINx is the LIN module LINx address
 * @param value is the timeout value
 * value : 0 --- 100bit ->  boaudrate
 * value : 1 --- 120bit
 * value : 2 --- 150bit
 * value : 3 --- 200bit
 *
 * @return None.
 */
void LIN_enterTimeOut(LIN_Type *LINx, uint8_t value)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->TIMEOUT, LIN0_TIMEOUT_TIMEOUT_VAL_Msk, ((uint32_t)value << LIN0_TIMEOUT_TIMEOUT_VAL_Pos));
    SET_BIT(LINx->TIMEOUT, LIN0_TIMEOUT_TIMEOUT_EN_Msk);
}

/**
 * @brief Enable LIN Low Power Bypass
 *  In LIN mode, this function enables the low power bypass mode.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_enableLowPowerBypass(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->LP_BYPASS, LIN0_LP_BYPASS_LP_BYPASS_Msk);
}

/**
 * @brief Set LIN Parity Error Injection
 *  In LIN mode, this function sets the parity error injection.
 *
 * @param LINx is the LIN module LINx address
 * @param parity is the parity error injection type
 * parity : LIN_ERROR_INJECT_NONE  - No parity error injection
 * parity : LIN_ERROR_INJECT_RECIVE  - Receive Parity error injection
 * parity : LIN_ERROR_INJECT_TRANSMIT  - Transmit parity error injection
 * parity : LIN_ERROR_INJECT_RECIVE_TRANSMIT  - Receive and Transmit parity error injection
 *
 * @return None.
 */
void LIN_setParityInject(LIN_Type *LINx, LIN_ParityChecksumErrInject parity)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->ERR_INJECT, LIN0_ERR_INJECT_PARITY_INJECT_Msk, parity);
}

/**
 * @brief Set LIN Checksum Error Injection
 *  In LIN mode, this function sets the checksum error injection.
 *
 * @param LINx is the LIN module LINx address
 * @param parity is the parity error injection type
 * parity : LIN_ERROR_INJECT_NONE  - No checksum error injection
 * parity : LIN_ERROR_INJECT_RECIVE  - Receive Checksum error injection
 * parity : LIN_ERROR_INJECT_TRANSMIT  - Transmit checksum error injection
 * parity : LIN_ERROR_INJECT_RECIVE_TRANSMIT  - Receive and Transmit checksum error injection
 *
 * @return None.
 */
void LIN_setChecksumInject(LIN_Type *LINx, LIN_ParityChecksumErrInject checksum)
{
    assert_param(IS_LIN_PERIPH(LINx));

    MODIFY_REG(LINx->ERR_INJECT, LIN0_ERR_INJECT_CHECKSUM_INJECT_Msk,
               ((uint32_t)checksum << LIN0_ERR_INJECT_CHECKSUM_INJECT_Pos));
}

/**
 * @brief Get LIN Operation Status
 *  In LIN mode, this function gets the operation status.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return The operation status.
 *  - LIN_INITAL_STATE
 *  - LIN_NORMAL_STATE
 *  - LIN_SLEEP_STATE
 */
uint16_t LIN_getOPStatus(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    return (uint16_t)(READ_REG(LINx->OP_STATUS));
}

/**
 * @brief Get LIN Slave Transmitted Byte Count
 *  In LIN mode, this function gets the slave transmitted byte count.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return The slave transmitted byte count value ,the range 0~8
 */
uint16_t LIN_getSlaveTransByteCountRPT(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    return (uint16_t)(READ_REG(LINx->TRANS_BYTE_RPT));
}

/**
 * @brief Enable ID filter mode bypass
 *  In LIN mode, this function enables the ID filter mode bypass.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_enableIDFilterBypass(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->ID_FILTER_BYPASS, LIN0_ID_FILTER_BYPASS_ID_FILTER_BYPASS_Msk);
}

/**
 * @brief Set Message filtering Type
 *  In LIN mode, this function sets the message filtering type. The
 *  type parameter can be one of the following values:
 *  - LIN_MSG_FILTER_ID_LIST_MODE   - Filtering uses LIN message ID List
 *  - LIN_MSG_FILTER_ID_MASK_MODE   - Filtering uses LIN message ID Mask
 *
 * @param LINx is the LIN module LINx address
 * @param type is the mask filtering comparison type
 *
 * @return None.
 */
void LIN_setIDFilter(LIN_Type *LINx, uint32_t ID_Filter, LIN_MessageFilter type)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(IS_LIN_ID_FILTER(ID_Filter));

    MODIFY_REG(LINx->ID_FILTER_MASK_EN, ID_Filter, ((uint32_t)type << POSITION_VAL(ID_Filter)));
}

/**
 * @brief Enable ID filter mode
 *  In LIN mode, this function enables the ID filter mode.
 *
 * @param LINx is the LIN module LINx address
 * @param ID_Filter is the ID filter x to enable
 *
 * @return None.
 */
void LIN_enableIDFilter(LIN_Type *LINx, uint32_t ID_Filter)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(IS_LIN_ID_FILTER(ID_Filter));

    SET_BIT(LINx->ID_FILTER_EN, ID_Filter);
}

/**
 * @brief Disable ID filter mode
 *  In LIN mode, this function disables the ID filter mode.
 *
 * @param LINx is the LIN module LINx address
 * @param ID_Filter is the ID filter x
 *
 * @return None.
 */
void LIN_disableIDFilter(LIN_Type *LINx, uint32_t ID_Filter)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(IS_LIN_ID_FILTER(ID_Filter));

    CLEAR_BIT(LINx->ID_FILTER_EN, ID_Filter);
}

/**
 * @brief Get ID filter match register
 *  In LIN mode, this function gets the ID filter match register.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return uint16_t Indicates which filter x has successfully matched， the range is 0~15.
 *  if none of the filters match, return 0. the return value is the filter x.
 */
uint16_t LIN_getIDFilterMatchRPT(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    return (uint16_t)(READ_REG(LINx->ID_FILTER_MATCH));
}

/**
 * @brief Checks for Rx ID Match Received
 *  In LIN mode, this function checks if an ID is received with a RX match
 *  and no ID-parity error.
 *
 * @param LINx is the LIN module LINx address
 * @param ID_Filter is the ID filter x ：LIN_ID_FILTER_x
 *
 * @return Returns true if a valid ID is matched, else returns false.
 */
bool LIN_isRxMatch(LIN_Type *LINx, uint32_t ID_Filter)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(IS_LIN_ID_FILTER(ID_Filter));

    /* Read Rx ID flag and return status */
    return (READ_REG(LINx->ID_FILTER_MATCH) == POSITION_VAL(ID_Filter)) ? true : false;
}

/**
 * @brief Initialize ID filter structure
 *  In LIN mode, this function initializes the ID filter structure.
 *
 * @param pConfig is the pointer to the ID filter structure
 *
 * @return None.
 */
void LIN_initIDFilterStruct(LIN_IDFilterConfig *pConfig)
{
    pConfig->dataLength   = 0;
    pConfig->checksumMode = LIN_CHECKSUM_ENHANCED;
    pConfig->rsp_Transmit = DISABLE;
    pConfig->maskId       = 0x3F;
    pConfig->filterId     = 0x0000;
}

/**
 * @brief Config ID filter Group X
 *  In LIN mode, this function configures the ID filter.
 *
 * @param LINx is the LIN module LINx address
 * @param ID_Filter is the ID filter x ：LIN_ID_FILTER_x
 * @param pConfig is the pointer to the ID filter structure
 *
 * @return None.
 */
void LIN_initIDFilter(LIN_Type *LINx, uint32_t ID_Filter, LIN_IDFilterConfig *pConfig)
{
    assert_param(IS_LIN_PERIPH(LINx));
    assert_param(IS_LIN_ID_FILTER(ID_Filter));

    MODIFY_REG(LINx->ID_FILTER_REG[POSITION_VAL(ID_Filter)].ID_FILTER_REG,
               LIN0_ID_FILTER_REG_ID_FILTER_REG_FILTER_ID_Msk |
               LIN0_ID_FILTER_REG_ID_FILTER_REG_MASK_ID_Msk |
               LIN0_ID_FILTER_REG_ID_FILTER_REG_CHKSUM_MODE_Msk |
               LIN0_ID_FILTER_REG_ID_FILTER_REG_RSP_TRANSMIT_Msk |
               LIN0_ID_FILTER_REG_ID_FILTER_REG_DATA_LEN_Msk,
               ((uint32_t)pConfig->maskId << LIN0_ID_FILTER_REG_ID_FILTER_REG_MASK_ID_Pos |
                (uint32_t)pConfig->filterId << LIN0_ID_FILTER_REG_ID_FILTER_REG_FILTER_ID_Pos |
                (uint32_t)pConfig->checksumMode << LIN0_ID_FILTER_REG_ID_FILTER_REG_CHKSUM_MODE_Pos |
                (uint32_t)pConfig->rsp_Transmit << LIN0_ID_FILTER_REG_ID_FILTER_REG_RSP_TRANSMIT_Pos |
                (uint32_t)(pConfig->dataLength - 1) << LIN0_ID_FILTER_REG_ID_FILTER_REG_DATA_LEN_Pos));

    /* Enable ID filter group */
    SET_BIT(LINx->ID_FILTER_EN, ID_Filter);
}

/**
 * @brief Enable function interrupts
 *  In LIN mode, this function enables the interrupts for the specified
 *  interrupt sources.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be enabled.
 *
 * The intFlags parameter can be set to the following value to set
 * all the flag bits:
 * - LIN_INT_ALL     - All Interrupts
 *
 * To set individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_FUNC_INT_SYNC_DONE
 * - LIN_FUNC_INT_HEAD_TX_DONE
 * - LIN_FUNC_INT_HEAD_RX_DONE
 * - LIN_FUNC_INT_RSP_TX_DONE
 * - LIN_FUNC_INT_RSP_RX_DONE
 * - LIN_FUNC_INT_WAKEUP
 * - LIN_FUNC_INT_SLEEP
 * - LIN_FUNC_INT_ABORT
 *
 * @return None.
 */
void LIN_enableFuncInterrupt(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->FUNCTION_INT_EN, intFlags);
}

/**
 * @brief Disable function interrupts
 *  In LIN mode only, this function disables the interrupts for the specified
 *  interrupt sources.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be disabled.
 *
 * The intFlags parameter can be set to the following value to disable
 * all the flag bits:
 * - LIN_INT_ALL     - All Interrupts
 *
 * To disable individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_FUNC_INT_SYNC_DONE
 * - LIN_FUNC_INT_HEAD_TX_DONE
 * - LIN_FUNC_INT_HEAD_RX_DONE
 * - LIN_FUNC_INT_RSP_TX_DONE
 * - LIN_FUNC_INT_RSP_RX_DONE
 * - LIN_FUNC_INT_WAKEUP
 * - LIN_FUNC_INT_SLEEP
 * - LIN_FUNC_INT_ABORT
 *
 * @return None.
 */
void LIN_disableFuncInterrupt(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    CLEAR_BIT(LINx->FUNCTION_INT_EN, intFlags);
}

/**
 * @brief Clear interrupt status
 *  In LIN mode only, this function clears the specified status flags.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be cleared.
 *
 * The intFlags parameter can be set to the following value to clear
 * all the flag bits:
 * - LIN_INT_ALL     - All Interrupts
 *
 * To clear individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_FUNC_INT_SYNC_DONE
 * - LIN_FUNC_INT_HEAD_TX_DONE
 * - LIN_FUNC_INT_HEAD_RX_DONE
 * - LIN_FUNC_INT_RSP_TX_DONE
 * - LIN_FUNC_INT_RSP_RX_DONE
 * - LIN_FUNC_INT_WAKEUP
 * - LIN_FUNC_INT_SLEEP
 * - LIN_FUNC_INT_ABORT
 *
 * @return None.
 */
void LIN_clearFuncInterruptStatus(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Clear the status flags */
    SET_BIT(LINx->FUNCTION_INT_CLR, intFlags);
}

/**
 * @brief Get function interrupt status
 *  In LIN mode only, this function gets the specified status flags.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be get.
 *
 * @return uint32_t The interrupt status flags.
 * The intFlags parameter can be set to the following value to get
 * all the flag bits:
 * - LIN_INT_ALL     - All Interrupts
 * To get individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_FUNC_INT_SYNC_DONE
 * - LIN_FUNC_INT_HEAD_TX_DONE
 * - LIN_FUNC_INT_HEAD_RX_DONE
 * - LIN_FUNC_INT_RSP_TX_DONE
 * - LIN_FUNC_INT_RSP_RX_DONE
 * - LIN_FUNC_INT_WAKEUP
 * - LIN_FUNC_INT_SLEEP
 * - LIN_FUNC_INT_ABORT
 */
uint32_t LIN_getFuncInterruptStatus(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Clear the status flags */
    return READ_REG(LINx->FUNC_INT_STATUS_RPT);
}

/**
 * @brief Enable Error interrupts
 *  In LIN mode, this function enables the interrupts for the specified
 *  interrupt sources.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be enabled.
 *
 * The intFlags parameter can be set to the following value to set
 * all the flag bits:
 * - LIN_ERR_INT_ALL     - All Interrupts
 *
 * To set individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_ERR_INT_ALL
 * - LIN_ERR_INT_HEAD_ERR
 * - LIN_ERR_INT_RSP_ERR
 * - LIN_ERR_INT_ID_PARITY_ERR
 * - LIN_ERR_INT_CHECKSUM_ERR
 * - LIN_ERR_INT_TIMEOUT_ERR
 * - LIN_ERR_INT_OVERSAMP_ERR
 * - LIN_ERR_INT_STUCK_ERR
 * - LIN_ERR_INT_COLLISION_ERR
 *
 * @return None.
 */
void LIN_enableErrorInterrupt(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->ERROR_INT_EN, intFlags);
}

/**
 * @brief Disable Error interrupts
 *  In LIN mode only, this function disables the interrupts for the specified
 *  interrupt sources.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be disabled.
 *
 * The intFlags parameter can be set to the following value to disable
 * all the flag bits:
 * - LIN_ERR_INT_ALL     - All Interrupts
 *
 * To disable individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_ERR_INT_HEAD_ERR
 * - LIN_ERR_INT_RSP_ERR
 * - LIN_ERR_INT_ID_PARITY_ERR
 * - LIN_ERR_INT_CHECKSUM_ERR
 * - LIN_ERR_INT_TIMEOUT_ERR
 * - LIN_ERR_INT_OVERSAMP_ERR
 * - LIN_ERR_INT_STUCK_ERR
 * - LIN_ERR_INT_COLLISION_ERR
 *
 * @return None.
 */
void LIN_disableErrorInterrupt(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    CLEAR_BIT(LINx->ERROR_INT_EN, intFlags);
}

/**
 * @brief Clear Error interrupt status
 *  In LIN mode only, this function clears the specified status flags.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be cleared.
 *
 * The intFlags parameter can be set to the following value to clear
 * all the flag bits:
 * - LIN_ERR_INT_ALL     - All Interrupts
 *
 * To clear individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_ERR_INT_HEAD_ERR
 * - LIN_ERR_INT_RSP_ERR
 * - LIN_ERR_INT_ID_PARITY_ERR
 * - LIN_ERR_INT_CHECKSUM_ERR
 * - LIN_ERR_INT_TIMEOUT_ERR
 * - LIN_ERR_INT_OVERSAMP_ERR
 * - LIN_ERR_INT_STUCK_ERR
 * - LIN_ERR_INT_COLLISION_ERR
 *
 * @return None.
 */
void LIN_clearErrorInterruptStatus(LIN_Type *LINx, uint32_t intFlags)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Clear the status flags */
    SET_BIT(LINx->ERROR_INT_CLR, intFlags);
}

/**
 * @brief Get Error interrupt status
 *  In LIN mode only, this function gets the specified status flags.
 *
 * @param LINx is the LIN module LINx address
 * @param intFlags is the bit mask of the interrupt sources to be get.
 *
 * @return uint32_t The interrupt status flags.
 *  The intFlags parameter can be set to the following value to get
 * all the flag bits:
 * - LIN_ERR_INT_ALL     - All Interrupts
 *  To get individual flags, the intFlags parameter can be the logical
 * OR of any of the following:
 * - LIN_ERR_INT_HEAD_ERR
 * - LIN_ERR_INT_RSP_ERR
 * - LIN_ERR_INT_ID_PARITY_ERR
 * - LIN_ERR_INT_CHECKSUM_ERR
 * - LIN_ERR_INT_TIMEOUT_ERR
 * - LIN_ERR_INT_OVERSAMP_ERR
 * - LIN_ERR_INT_STUCK_ERR
 * - LIN_ERR_INT_COLLISION_ERR
 */
uint32_t LIN_getErrorInterruptStatus(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    /* Clear the status flags */
    return READ_REG(LINx->ERROR_INT_STATUS_RPT);
}

/**
 * @brief Enable Internal Loopback mode for self test
 *  In LIN and SCI mode, this function enables the internal Loopback mode for
 *  self test.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_enableIntLoopback(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    SET_BIT(LINx->LOOP_TEST, LIN0_LOOP_TEST_LOOP_TEST_EN_Msk);
}

/**
 * @brief Disable Internal Loopback mode for self test
 *  In LIN and SCI mode, this function disables the internal Loopback mode for
 *  self test.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_disableIntLoopback(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    CLEAR_BIT(LINx->LOOP_TEST, LIN0_LOOP_TEST_LOOP_TEST_EN_Msk);
}

/**
 * @brief Initializes the LIN Driver
 *  This function initializes the LIN module.
 *
 * @param LINx is the LIN module LINx address
 *
 * @return None.
 */
void LIN_initModule(LIN_Type *LINx)
{
    assert_param(IS_LIN_PERIPH(LINx));

    LIN_disableModule(LINx);
    LIN_enableModule(LINx);

    /* Set LIN mode to Commander */
    LIN_setLINMode(LINx, LIN_MODE_MASTER);

    /* Enable Fixed baud rate mode */
    LIN_disableAutomaticBaudrate(LINx);

    /* Use the set frame length and not ID4/ID5 bits for length control */
    LIN_setCommMode(LINx, LIN_COMM_LIN_USELENGTHVAL);

    /* Use Enhanced Checksum */
    LIN_setChecksumType(LINx, LIN_CHECKSUM_ENHANCED);

    /* Message filtering uses responder task ID byte */
    LIN_setIDFilter(LINx, LIN_ID_FILTER_1, LIN_MSG_FILTER_ID_LIST_MODE);

    /* Disable Internal loopback for external communication */
    LIN_disableIntLoopback(LINx);

    /* Set Baud Rate Settings - 100MHz Device */
    LIN_setBaudRate(LINx, 20000U);

    /* Set response field to 1 byte */
    LIN_setFrameLength(LINx, 1U);

    /* Configure sync field */
    /* Sync break (13 + 5 = 18 Tbits) */
    /* Sync delimiter (1 + 3 = 4 Tbits) */
    LIN_setSyncFields(LINx, 5U, 3U);
}

/**
 * @brief Send Data
 *  In LIN mode, this function sends a block of data pointed to by 'data'.
 *  The number of data to transmit must be set with LIN_setFrameLength()
 *  before.
 *
 * @param LINx is the LIN module LINx address
 * @param data is the pointer to data to send
 *
 * @return None.
 */
void LIN_sendData(LIN_Type *LINx, uint8_t *data)
{
    __IO uint32_t lin_reg = 0;
    int16_t       i;
    int16_t       length;
    uint8_t       *pData;

    /* Check the arguments. */
    assert_param(IS_LIN_PERIPH(LINx));

    /* Get the length from the DATA_LEN register. */
    if (READ_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_MODE_Msk))
    {
        switch (READ_REG(LINx->TX_ID) & 0x30)
        {
        case 0x00:
        case 0x10:
            length = 2;
            break;

        case 0x20:
            length = 4;
            break;

        case 0x30:
            length = 8;
            break;

        default:
            length = 0;
            break;
        }
    }
    else
    {
        length = (uint16_t)READ_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_Msk) >> LIN0_DATA_LEN_DATA_LEN_Pos;
    }

    pData = data;

    /* 按顺序将数据字节写入到连续的内存空间中 */
    for (i = 0; i <= length && i < 8; i++)  // 最多处理8个字节（两个32位寄存器）
    {
        if (pData != 0U)
        {
            lin_reg = (uint32_t)(&LINx->SND_BUF_L + (i / 4));

            MODIFY_REG(REG32(lin_reg),
                       (LIN0_SND_BUF_L_SND_DATA1_Msk << ((uint32_t)(i % 4) * 8U)),
                       ((uint32_t)*pData << ((uint32_t)(i % 4) * 8U)));

            pData++;
        }
    }
}

/**
 * Read received data
 * In LIN mode only, this function reads a block of bytes and place it into
 * the data buffer pointed to by 'data'.
 *
 * @param LINx is the LIN module LINx address
 * @param data is the pointer to the data buffer
 *
 * @return None.
 */
void LIN_getData(LIN_Type *LINx, uint8_t * const data)
{
    uint16_t i;
    uint16_t length;
    uint8_t  *pData = data;
    uint32_t rcv_buf_l, rcv_buf_h;

    /* Check the arguments. */
    assert_param(IS_LIN_PERIPH(LINx));

    /* Get the length from the DATA_LEN register. */
    length = (uint16_t)READ_BIT(LINx->DATA_LEN, LIN0_DATA_LEN_DATA_LEN_Msk) >> LIN0_DATA_LEN_DATA_LEN_Pos;

    /* Read data only if buffer is not NULL */
    if (pData != 0U)
    {
        /* Read register values once */
        rcv_buf_l = READ_REG(LINx->RCV_BUF_L);
        rcv_buf_h = READ_REG(LINx->RCV_BUF_H);

        /* Extract and store data bytes with bitwise operations */
        for (i = 0U; i <= length && i < 8U; i++)
        {
            if (i < 4U)
            {
                *pData++ = (uint8_t)((rcv_buf_l >> (i * 8U)) & LIN0_RCV_BUF_L_RCV_DATA1_Msk);
            }
            else
            {
                *pData++ = (uint8_t)((rcv_buf_h >> ((i - 4U) * 8U)) & LIN0_RCV_BUF_L_RCV_DATA1_Msk);
            }
        }
    }
}
