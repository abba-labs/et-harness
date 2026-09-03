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

#include "et6x_ipcm.h"

/* example:
 *               CORE0 send msg to CORE1, manual ack mode
 *
 *           +-----------+  IPCMxSOURCE = 1  (set source channel)
 *           |           |  IPCMxMSET = 0  (enable mailbox interrupt)
 *           |           |  IPCMxDSET = 1  (set destination channel)
 *           |   CORE0   |  IPCMxDR0 = 0xda7a0000  (data payload)
 *           |           |  IPCMxSEND = 1  (trigger send)
 *           |           |
 *           +-----+-----+
 *               |
 *               |
 *               +-------------------+
 *                                   |
 *                                   |
 *                               +-----+-----+  read IPCMRIS1 (find mailbox x)
 *                               |           |  read IPCMxDR0 (read data payload)
 *                               |           |  update IPCMxDR0 = 0xda7a1111   (optional update date payload)
 *                               |   CORE1   |  IPCMxSEND = 2   (clear send interrupt and trigger ack interrupt)
 *                               |           |
 *                               |           |
 *                               +-----+-----+
 *                                   |
 *                                   |
 *               +-------------------+
 *               |
 *               |
 *               v
 *           +-----+-----+  read IPCMRIS0  (find mailbox x)
 *           |           |  read IPCMxDR0 (read ack  payload)
 *           |           |  IPCMxSEND = 0  (clear ack interrupt)
 *           |   CORE0   |
 *           |           |  IPCMxSOURCE = 0 (clear all IPCMx register)
 *           |           |
 *           +-----------+
 */

/* mailbox send direction set */
#define SEND_INACTIVE       (0U)
#define SEND_MSG_TO_DEST    (1U)
#define SEND_ACK_TO_SRC     (2U)

/* bits in a byte */
#define BYTE_WIDTH          (8U)

/*! Parameter validity check for IPCM mailbox ID */
#define IS_IPCM_MBOX_ID(id)    ((id) < MAILBOX_NUM)

/*! Parameter validity check for IPCM channel ID */
#define IS_IPCM_CH_ID(ch)      ((ch) < IPCM_CH_NUM)

/*! Parameter validity check for IPCM acknowage mode */
#define IS_IPCM_ACK_MODE(mode) \
        (((mode) == MANUAL_ACK) || \
         ((mode) == AUTO_ACK) ||   \
         ((mode) == AUTO_LINK) ||  \
         ((mode) == AUTO_ACK_LINK))

/*! Parameter validity check for IPCM linked mailbix number */
#define IS_IPCM_LINKED_MBOX_NUM(num)    ((num) <= MAILBOX_LINKED_MAX_NUM)

/**
 * @brief Set source channel ID in the specified mailbox
 *
 * @param chanID: channel ID in mailbox
 * @param mboxID: mailbox ID
 */
static void IPCM_setSource(uint32_t mboxID, uint32_t chanID)
{
    WRITE_REG(IPCM->MBOX[mboxID].SOURCE, BIT_MASK(chanID));
    WRITE_REG(IPCM->MBOX[mboxID].MSET, BIT_MASK(chanID));
}

/**
 * @brief Clear source register in the specified mailbox, then this mboxID is released
 *
 * @param chanID: channel ID in mailbox
 * @param mboxID: mailbox ID
 */
static void IPCM_clearSource(uint32_t mboxID)
{
    WRITE_REG(IPCM->MBOX[mboxID].SOURCE, 0U);
}

/**
 * @brief Set destination channel ID in mboxID in the specified mailbox
 *
 * @param chanID: channel ID in mailbox
 * @param mboxID: mailbox ID
 */
static void IPCM_setDestination(uint32_t mboxID, uint32_t chanID)
{
    WRITE_REG(IPCM->MBOX[mboxID].DSET, BIT_MASK(chanID));
    WRITE_REG(IPCM->MBOX[mboxID].MSET, BIT_MASK(chanID));
}

/**
 * @brief Set mboxID acknowage mode
 *
 * @param mboxID: mailbox ID
 * @param mode: transfer acknowage mode
 */
static void IPCM_setMode(uint32_t mboxID, uint32_t mode)
{
    WRITE_REG(IPCM->MBOX[mboxID].MODE, mode);
}

/**
 * @brief Init one mail box
 *
 * @param init: initial structure pointer for mailbox
 */
void IPCM_mailboxInit(const IPCM_InitTypeDef *init)
{
    uint32_t im;

    assert_param(IS_IPCM_MBOX_ID(init->mboxID));
    assert_param(IS_IPCM_CH_ID(init->srcChanID));
    assert_param(IS_IPCM_CH_ID(init->dstChanID));
    assert_param(IS_IPCM_ACK_MODE(init->mode));
    assert_param(IS_IPCM_LINKED_MBOX_NUM(init->linkedMboxNum));

    IPCM_setSource(init->mboxID, init->srcChanID);
    IPCM_setDestination(init->mboxID, init->dstChanID);
    IPCM_setMode(init->mboxID, init->mode);
    if ((init->mode & AUTO_LINK) != 0U)
    {
        for (im = init->mboxID + 1U; im < init->mboxID + init->linkedMboxNum; im++)
        {
            IPCM_setSource(im, init->srcChanID);
            IPCM_setDestination(im, init->dstChanID);
            IPCM_setMode(im, init->mode);
        }

        IPCM_setSource(init->mboxID + init->linkedMboxNum, init->srcChanID);
        IPCM_setDestination(init->mboxID + init->linkedMboxNum, init->dstChanID);
        IPCM_setMode(init->mboxID + init->linkedMboxNum, init->mode & ~AUTO_LINK);
    }
}

/**
 * @brief Deinit one mail box
 *
 * @param init: de-initial structure pointer for mailbox
 */
void IPCM_mailboxDeInit(const IPCM_InitTypeDef *init)
{
    uint32_t im;

    assert_param(IS_IPCM_MBOX_ID(init->mboxID));
    assert_param(IS_IPCM_CH_ID(init->srcChanID));
    assert_param(IS_IPCM_CH_ID(init->dstChanID));
    assert_param(IS_IPCM_ACK_MODE(init->mode));
    assert_param(IS_IPCM_LINKED_MBOX_NUM(init->linkedMboxNum));

    IPCM_clearSource(init->mboxID);
    if ((init->mode & AUTO_LINK) != 0U)
    {
        for (im = init->mboxID + 1U; im <= init->mboxID + init->linkedMboxNum; im++)
        {
            IPCM_clearSource(im);
        }
    }
}

/**
 * @brief Init initial structure for mailbox
 *
 * @param init: initial structure pointer for mailbox to initionalize
 */
void IPCM_mailboxStructInit(IPCM_InitTypeDef *init)
{
    init->srcChanID     = IPCM_CH_0;
    init->dstChanID     = IPCM_CH_1;
    init->mboxID        = MAILBOX0;
    init->mode          = MANUAL_ACK;
    init->linkedMboxNum = 0U;
}

/**
 * @brief Send message to destination channel
 *
 * @param mboxID: mailbox ID
 * @param data: pointer to data that is ready to transfer
 * @param size: message size by byte
 */
void IPCM_sendData(uint32_t mboxID, void *data, uint32_t size)
{
    uint32_t ir  = 0;
    uint32_t ib  = 0;
    uint32_t reg = 0;

    if (size > MAILBOX_DR_SIZE)
    {
        size = MAILBOX_DR_SIZE;
    }

    /* Data registers in IPCM can not be assigned align to  ,
     * so we must assign data register one by one. */

    while (size / sizeof(uint32_t) != 0)
    {
        WRITE_REG(IPCM->MBOX[mboxID].DR[ir], *((uint32_t *)data));
        ir++;
        data  = (uint8_t *)data + sizeof(uint32_t);
        size -= sizeof(uint32_t);
    }

    if (size % sizeof(uint32_t) != 0)
    {
        for (ib = 0; ib < size; ib++)
        {
            reg |= (uint32_t)(*((uint8_t *)data + ib)) << ib * BYTE_WIDTH;
        }
        WRITE_REG(IPCM->MBOX[mboxID].DR[ir], reg);
    }

    WRITE_REG(IPCM->MBOX[mboxID].SEND, SEND_MSG_TO_DEST);
}

/**
 * @brief Receive message from source channel
 *
 * @param mboxID: mailbox ID
 * @param data: pointer to memory buffer that is ready to revieve data
 * @param size: message size by byte
 */
void IPCM_receiveData(uint32_t mboxID, void *data, uint32_t size)
{
    uint32_t ir = 0;
    uint32_t ib = 0;

    if (size > MAILBOX_DR_SIZE)
    {
        size = MAILBOX_DR_SIZE;
    }

    while (size / sizeof(uint32_t) != 0)
    {
        *((uint32_t *)data) = READ_REG(IPCM->MBOX[mboxID].DR[ir]);
        ir++;
        data  = (uint8_t *)data + sizeof(uint32_t);
        size -= sizeof(uint32_t);
    }

    if (size % sizeof(uint32_t) != 0)
    {
        for (ib = 0; ib < size; ib++)
        {
            *((uint8_t *)data + ib) = (uint8_t)(READ_REG(IPCM->MBOX[mboxID].DR[ir]) >> ib * BYTE_WIDTH);
        }
    }
}

/**
 * @brief Update acknowledge to destination channel
 *
 * @param mboxID: mailbox ID
 * @param data: pointer to data that is ready to replace the old data
 * @param size: message size by byte
 */
void IPCM_updateAckData(uint32_t mboxID, void *data, uint32_t size)
{
    uint32_t ir  = 0;
    uint32_t ib  = 0;
    uint32_t reg = 0;

    if (size > MAILBOX_DR_SIZE)
    {
        size = MAILBOX_DR_SIZE;
    }

    while (size / sizeof(uint32_t) != 0)
    {
        WRITE_REG(IPCM->MBOX[mboxID].DR[ir], *((uint32_t *)data));
        ir++;
        data  = (uint8_t *)data + sizeof(uint32_t);
        size -= sizeof(uint32_t);
    }

    if (size % sizeof(uint32_t) != 0)
    {
        for (ib = 0; ib < size; ib++)
        {
            reg |= (uint32_t)(*((uint8_t *)data + ib)) << ib * BYTE_WIDTH;
        }
        WRITE_REG(IPCM->MBOX[mboxID].DR[ir], reg);
    }
}

/**
 * @brief Send message to destination channel
 *
 * @param mboxID: mailbox ID
 * @param data: pointer to data that is ready transfer
 * @param size: message size by byte
 */
void IPCM_sendDataLinked(uint32_t mboxID, void *data, uint32_t size)
{
    uint32_t ib  = 0;
    uint32_t ir  = 0;
    uint32_t reg = 0;
    uint32_t im  = mboxID;

    if (size > MAILBOX_DR_SIZE * (MAILBOX_NUM - mboxID))
    {
        size = MAILBOX_DR_SIZE * (MAILBOX_NUM - mboxID);
    }

    while ((size / MAILBOX_DR_SIZE) != 0)
    {
        for (ir = 0; ir < MAILBOX_DR_NUM; ir++)
        {
            WRITE_REG(IPCM->MBOX[im].DR[ir], *((uint32_t *)data));
            data  = (uint8_t *)data + sizeof(uint32_t);
            size -= sizeof(uint32_t);
        }
        im++;
        ir = 0;
    }

    while (size / sizeof(uint32_t) != 0)
    {
        WRITE_REG(IPCM->MBOX[im].DR[ir], *((uint32_t *)data));
        ir++;
        data  = (uint8_t *)data + sizeof(uint32_t);
        size -= sizeof(uint32_t);
    }

    if (size % sizeof(uint32_t) != 0)
    {
        for (ib = 0; ib < size; ib++)
        {
            reg |= (uint32_t)(*((uint8_t *)data + ib)) << ib * BYTE_WIDTH;
        }
        WRITE_REG(IPCM->MBOX[im].DR[ir], reg);
    }

    WRITE_REG(IPCM->MBOX[mboxID].SEND, SEND_MSG_TO_DEST);
}

/**
 * @brief Clear the destination channel ID in the specified mailbox
 *
 * @param chanID: channel ID in mailbox
 * @param mboxID: mailbox ID
 */
void IPCM_clearDestination(uint32_t mboxID, uint32_t chanID)
{
    assert_param(IS_IPCM_MBOX_ID(mboxID));
    assert_param(IS_IPCM_CH_ID(chanID));

    WRITE_REG(IPCM->MBOX[mboxID].DCLEAR, BIT_MASK(chanID));
    WRITE_REG(IPCM->MBOX[mboxID].MCLEAR, BIT_MASK(chanID));
}

/**
 * @brief Get mailbox ID with specified channel ID in ISR
 *
 * @param chanID: channel ID in mailbox
 */
uint32_t IPCM_getMailboxInterrupt(uint32_t chanID)
{
    uint32_t mboxID;

    assert_param(IS_IPCM_CH_ID(chanID));

    for (mboxID = 0; mboxID < MAILBOX_NUM; mboxID++)
    {
        if (READ_REG(IPCM->ISR[chanID].RIS) == BIT_MASK(mboxID))
        {
            break;
        }
    }
    if (mboxID == 16)
    {
        return 0xFFFFFFFF;
    }
    else
    {
        return mboxID;
    }
}

/**
 * @brief Clear mail box interrupt and send acknowledge
 *
 * @param mboxID: mailbox ID
 */
void IPCM_clearMailboxInterruptAndSendAck(uint32_t mboxID)
{
    assert_param(IS_IPCM_CH_ID(mboxID));

    WRITE_REG(IPCM->MBOX[mboxID].SEND, SEND_ACK_TO_SRC);
}

/**
 * @brief Clear mail box interrupt
 *
 * @param mboxID: mailbox ID
 */
void IPCM_clearMailboxInterrupt(uint32_t mboxID)
{
    assert_param(IS_IPCM_CH_ID(mboxID));

    WRITE_REG(IPCM->MBOX[mboxID].SEND, SEND_INACTIVE);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Read implemented mailbox, interrupt-channel and data-word counts.
 * @param pCapabilities: Output hardware counts, never caller expectations.
 * @retval DRV_OK or DRV_PARAM_ERR for a NULL output.
 */
DRV_Status IPCM_testGetCapabilities(IPCM_TestCapabilities *pCapabilities)
{
    uint32_t value;

    if (pCapabilities == NULL)
    {
        return DRV_PARAM_ERR;
    }

    value = READ_REG(IPCM->CFGSTAT);
    pCapabilities->mailboxCount =
        (value & IPCM_IPCMCFGSTAT_MAILBOXES_Msk) >> IPCM_IPCMCFGSTAT_MAILBOXES_Pos;
    pCapabilities->channelCount =
        (value & IPCM_IPCMCFGSTAT_INTERRUPTS_Msk) >> IPCM_IPCMCFGSTAT_INTERRUPTS_Pos;
    pCapabilities->dataWordCount =
        (value & IPCM_IPCMCFGSTAT_DATAWORDS_Msk) >> IPCM_IPCMCFGSTAT_DATAWORDS_Pos;
    return DRV_OK;
}

/** @brief Validate the whole contiguous range before any mailbox access. */
static uint32_t IPCM_testRangeIsValid(uint32_t first, uint32_t count)
{
    return (first < MAILBOX_NUM) && (count != 0U) && (count <= MAILBOX_NUM - first);
}

/**
 * @brief Configure a single mailbox or a complete, bounded linked chain.
 * @param first: First mailbox index.
 * @param count: Total member count, including the first mailbox.
 * @param source: Exactly one source channel bit.
 * @param destination: Nonempty destination channel set, excluding source.
 * @param mode: SDK MANUAL_ACK/AUTO_ACK/AUTO_LINK/AUTO_ACK_LINK.
 * @param irqEnable: Enabled channel subset of source and destination.
 * @retval DRV_OK or DRV_PARAM_ERR, with no writes for invalid arguments.
 */
DRV_Status IPCM_testConfigureMailboxes(uint32_t first, uint32_t count, uint32_t source,
                                      uint32_t destination, uint32_t mode, uint32_t irqEnable)
{
    uint32_t index;
    uint32_t validChannels = BIT_MASK(IPCM_CH_NUM) - 1U;

    if (!IPCM_testRangeIsValid(first, count) || !IS_IPCM_ACK_MODE(mode) ||
        (source == 0U) || ((source & (source - 1U)) != 0U) || (destination == 0U) ||
        ((source & destination) != 0U) || (((source | destination) & ~validChannels) != 0U) ||
        ((irqEnable & ~(source | destination)) != 0U) ||
        (((mode & AUTO_LINK) == 0U) && (count != 1U)))
    {
        return DRV_PARAM_ERR;
    }

    /* Reconfiguration is only allowed on idle mailboxes; never erase a pending message. */
    for (index = first; index < first + count; ++index)
    {
        if (READ_REG(IPCM->MBOX[index].SEND) != SEND_INACTIVE)
        {
            return DRV_BUSY;
        }
    }

    for (index = first; index < first + count; ++index)
    {
        WRITE_REG(IPCM->MBOX[index].SOURCE, source);
        WRITE_REG(IPCM->MBOX[index].DCLEAR, validChannels);
        WRITE_REG(IPCM->MBOX[index].DSET, destination);
        WRITE_REG(IPCM->MBOX[index].MCLEAR, validChannels);
        WRITE_REG(IPCM->MBOX[index].MSET, irqEnable);
        IPCM_setMode(index, (index + 1U == first + count) ? (mode & ~AUTO_LINK) : mode);
    }
    return DRV_OK;
}

/**
 * @brief Release precisely the requested mailboxes using the SDK SOURCE release action.
 * @param first: First mailbox index.
 * @param count: Total number of mailboxes.
 * @note No reset, synthetic zero readback or additional cleanup is performed.
 * @retval DRV_OK or DRV_PARAM_ERR.
 */
DRV_Status IPCM_testReleaseMailboxes(uint32_t first, uint32_t count)
{
    uint32_t index;

    if (!IPCM_testRangeIsValid(first, count))
    {
        return DRV_PARAM_ERR;
    }
    for (index = first; index < first + count; ++index)
    {
        IPCM_clearSource(index);
    }
    return DRV_OK;
}

/** @brief Read raw configuration without clearing pending state or acknowledging data. */
DRV_Status IPCM_testGetMailboxSnapshot(uint32_t mailbox, IPCM_TestMailboxSnapshot *pSnapshot)
{
    if (!IS_IPCM_MBOX_ID(mailbox) || (pSnapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }
    pSnapshot->source = READ_REG(IPCM->MBOX[mailbox].SOURCE);
    pSnapshot->destination = READ_REG(IPCM->MBOX[mailbox].DSTATUS);
    pSnapshot->mode = READ_REG(IPCM->MBOX[mailbox].MODE);
    pSnapshot->interruptEnable = READ_REG(IPCM->MBOX[mailbox].MSTATUS);
    pSnapshot->send = READ_REG(IPCM->MBOX[mailbox].SEND);
    return DRV_OK;
}

/** @brief Return whole Raw/Masked pending sets, including simultaneous mailbox bits. */
DRV_Status IPCM_testGetPendingSnapshot(uint32_t channel, IPCM_TestPendingSnapshot *pSnapshot)
{
    if (!IS_IPCM_CH_ID(channel) || (pSnapshot == NULL))
    {
        return DRV_PARAM_ERR;
    }
    pSnapshot->raw = READ_REG(IPCM->ISR[channel].RIS);
    pSnapshot->masked = READ_REG(IPCM->ISR[channel].MIS);
    return DRV_OK;
}

/**
 * @brief Write exact payload bytes, without starting transmission.
 * @param first: First mailbox index.
 * @param count: Configured chain member count.
 * @param pData: Byte-addressable source; no alignment requirement.
 * @param length: Nonzero valid byte count, never truncated.
 * @note Validate capacity and actual link bits before writing. Tail padding is zero.
 * @retval DRV_OK or DRV_PARAM_ERR.
 */
DRV_Status IPCM_testWritePayloadExact(uint32_t first, uint32_t count, const uint8_t *pData,
                                     uint32_t length)
{
    uint32_t offset;
    uint32_t byte;
    uint32_t value;
    uint32_t member;

    if (!IPCM_testRangeIsValid(first, count) || (pData == NULL) || (length == 0U) ||
        (length > count * MAILBOX_DR_SIZE))
    {
        return DRV_PARAM_ERR;
    }

    /* Caller-supplied capacity must agree with the configured chain topology. */
    for (member = 0U; member < count; ++member)
    {
        uint32_t linked = READ_REG(IPCM->MBOX[first + member].MODE) & AUTO_LINK;
        if ((member + 1U < count) ? (linked == 0U) : (linked != 0U))
        {
            return DRV_PARAM_ERR;
        }
    }

    for (offset = 0U; offset < length; offset += sizeof(uint32_t))
    {
        value = 0U;
        for (byte = 0U; (byte < sizeof(uint32_t)) && (offset + byte < length); ++byte)
        {
            value |= (uint32_t)pData[offset + byte] << (byte * BYTE_WIDTH);
        }
        WRITE_REG(IPCM->MBOX[first + offset / MAILBOX_DR_SIZE]
                      .DR[(offset % MAILBOX_DR_SIZE) / sizeof(uint32_t)], value);
    }
    return DRV_OK;
}

/** @brief Read exact bytes without ACK, clear, truncation or unaligned word accesses. */
DRV_Status IPCM_testReadPayloadExact(uint32_t mailbox, uint8_t *pData, uint32_t length)
{
    uint32_t offset;
    uint32_t byte;
    uint32_t value;

    if (!IS_IPCM_MBOX_ID(mailbox) || (pData == NULL) || (length == 0U) ||
        (length > MAILBOX_DR_SIZE))
    {
        return DRV_PARAM_ERR;
    }
    for (offset = 0U; offset < length; offset += sizeof(uint32_t))
    {
        value = READ_REG(IPCM->MBOX[mailbox].DR[offset / sizeof(uint32_t)]);
        for (byte = 0U; (byte < sizeof(uint32_t)) && (offset + byte < length); ++byte)
        {
            pData[offset + byte] = (uint8_t)(value >> (byte * BYTE_WIDTH));
        }
    }
    return DRV_OK;
}

/** @brief Trigger one destination message after payload preparation. */
DRV_Status IPCM_testSendMessage(uint32_t mailbox)
{
    if (!IS_IPCM_MBOX_ID(mailbox))
    {
        return DRV_PARAM_ERR;
    }
    WRITE_REG(IPCM->MBOX[mailbox].SEND, SEND_MSG_TO_DEST);
    return DRV_OK;
}

/** @brief Send explicit ACK in either MANUAL or AUTO mode; never release destination. */
DRV_Status IPCM_testSendAck(uint32_t mailbox)
{
    if (!IS_IPCM_MBOX_ID(mailbox))
    {
        return DRV_PARAM_ERR;
    }
    IPCM_clearMailboxInterruptAndSendAck(mailbox);
    return DRV_OK;
}

/** @brief Clear only message/ACK pending; do not release route or request ACK. */
DRV_Status IPCM_testClearPending(uint32_t mailbox)
{
    if (!IS_IPCM_MBOX_ID(mailbox))
    {
        return DRV_PARAM_ERR;
    }
    IPCM_clearMailboxInterrupt(mailbox);
    return DRV_OK;
}

/** @brief Release one destination through the existing SDK operation. */
DRV_Status IPCM_testReleaseDestination(uint32_t mailbox, uint32_t channel)
{
    if (!IS_IPCM_MBOX_ID(mailbox) || !IS_IPCM_CH_ID(channel))
    {
        return DRV_PARAM_ERR;
    }
    IPCM_clearDestination(mailbox, channel);
    return DRV_OK;
}

/** @brief Change only one channel's IRQ delivery, leaving Raw pending and routes intact. */
DRV_Status IPCM_testSetInterruptDelivery(uint32_t mailbox, uint32_t channel, uint32_t enabled)
{
    if (!IS_IPCM_MBOX_ID(mailbox) || !IS_IPCM_CH_ID(channel) || (enabled > 1U))
    {
        return DRV_PARAM_ERR;
    }
    if (enabled != 0U)
    {
        WRITE_REG(IPCM->MBOX[mailbox].MSET, BIT_MASK(channel));
    }
    else
    {
        WRITE_REG(IPCM->MBOX[mailbox].MCLEAR, BIT_MASK(channel));
    }
    return DRV_OK;
}

/* ET6801 shared AXI SRAM1 is outside both core stacks and the resource pool.
 * Both images keep D-cache disabled; DMB/DSB order publication, not cache maintenance.
 * The first four words retain the existing Core1 deployment readiness contract.
 * A separate IPCM tag rejects an old SPINLOCK peer at the same shared address. */
#define IPCM_TEST_PEER_MAGIC (0x45544331U)
#define IPCM_TEST_PEER_TAG (0x49504331U)
#define IPCM_TEST_PEER_READY (1U)
#define IPCM_TEST_PEER_MAILBOX ((volatile IPCM_TestPeerMailbox *)(uintptr_t)AXI_SRAM1_BASE)
typedef struct
{
    uint32_t magic, ready, coreId, heartbeat;
    uint32_t tag, sequence, completed, state, cancel;
    uint16_t command, requestLength, status, responseLength;
    uint8_t request[IPCM_TEST_PEER_BYTES];
    uint8_t response[IPCM_TEST_PEER_BYTES];
} IPCM_TestPeerMailbox;

/** @brief Require the IPCM peer identity; never accept readiness from another IP image. */
static uint32_t IPCM_testPeerAvailable(void)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    __DMB();
    return (m->magic == IPCM_TEST_PEER_MAGIC) && (m->ready == IPCM_TEST_PEER_READY) &&
           (m->tag == IPCM_TEST_PEER_TAG);
}

/** @brief Submit one bounded command body without waiting for Core1 execution. */
DRV_Status IPCM_testPeerSubmit(uint16_t command, const uint8_t *data, uint16_t length,
                               uint32_t *sequence)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    uint32_t next;
    uint16_t i;
    if ((sequence == NULL) || (length > IPCM_TEST_PEER_BYTES) || ((length != 0U) && (data == NULL)))
    {
        return DRV_PARAM_ERR;
    }
    if (!IPCM_testPeerAvailable() || (m->sequence != m->completed))
    {
        return DRV_ERROR;
    }
    next = m->sequence + 1U;
    if (next == 0U)
    {
        next = 1U;
    }
    m->command = command;
    m->requestLength = length;
    m->cancel = 0U;
    for (i = 0U; i < length; ++i)
    {
        m->request[i] = data[i];
    }
    __DMB();
    m->sequence = next;
    __DSB();
    *sequence = next;
    return DRV_OK;
}

/** @brief Read retained completion; queued responses never expose stale result bytes. */
DRV_Status IPCM_testPeerResult(IPCM_TestPeerResult *result)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    uint32_t state;
    uint16_t i;
    if ((result == NULL) || !IPCM_testPeerAvailable())
    {
        return DRV_ERROR;
    }
    state = m->sequence == m->completed ? m->state : IPCM_TEST_PEER_QUEUED;
    __DMB();
    result->state = state;
    result->sequence = m->sequence;
    result->coreId = m->coreId;
    result->heartbeat = m->heartbeat;
    result->status = 0U;
    result->length = 0U;
    if ((state == IPCM_TEST_PEER_DONE) || (state == IPCM_TEST_PEER_CANCELLED))
    {
        if ((m->completed != result->sequence) || (m->responseLength > IPCM_TEST_PEER_BYTES))
        {
            return DRV_ERROR;
        }
        result->status = m->status;
        result->length = m->responseLength;
        for (i = 0U; i < result->length; ++i)
        {
            result->data[i] = m->response[i];
        }
    }
    return DRV_OK;
}

/** @brief Request acknowledged Service cancellation, including a queued command. */
DRV_Status IPCM_testPeerCancel(uint32_t *sequence)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    if ((sequence == NULL) || !IPCM_testPeerAvailable())
    {
        return DRV_ERROR;
    }
    /* A cancellation owns a new sequence; a stale command cannot complete over it. */
    m->cancel = 1U;
    *sequence = m->sequence + 1U;
    if (*sequence == 0U)
    {
        *sequence = 1U;
    }
    __DMB();
    m->sequence = *sequence;
    __DSB();
    return DRV_OK;
}

/** @brief Publish peer readiness only after the core-local Service/IRQ manager is initialized. */
void IPCM_testPeerInitialize(uint32_t coreId)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    m->ready = 0U;
    __DMB();
    m->magic = IPCM_TEST_PEER_MAGIC;
    m->tag = IPCM_TEST_PEER_TAG;
    m->coreId = coreId;
    m->heartbeat = 0U;
    m->sequence = 0U;
    m->completed = 0U;
    m->cancel = 0U;
    m->state = IPCM_TEST_PEER_IDLE;
    m->requestLength = 0U;
    m->responseLength = 0U;
    __DMB();
    m->ready = IPCM_TEST_PEER_READY;
    __DSB();
}

/** @brief Core1 takes at most one command per poll; caller owns Service dispatch and cancellation. */
DRV_Status IPCM_testPeerTake(uint16_t *command, uint8_t *data, uint16_t *length, uint32_t *sequence,
                             uint32_t *cancel)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    uint16_t i;
    if ((command == NULL) || (data == NULL) || (length == NULL) || (sequence == NULL) ||
        (cancel == NULL))
    {
        return DRV_PARAM_ERR;
    }
    ++m->heartbeat;
    if (!IPCM_testPeerAvailable() || (m->sequence == m->completed))
    {
        return DRV_ERROR;
    }
    __DMB();
    *sequence = m->sequence;
    *cancel = m->cancel;
    *command = m->command;
    *length = m->requestLength;
    if (*length > IPCM_TEST_PEER_BYTES)
    {
        return DRV_ERROR;
    }
    for (i = 0U; i < *length; ++i)
    {
        data[i] = m->request[i];
    }
    __DMB();
    return (*sequence == m->sequence && m->ready != 0U) ? DRV_OK : DRV_ERROR;
}

/** @brief Publish an executed command only if it still owns the request sequence. */
DRV_Status IPCM_testPeerComplete(uint32_t sequence, uint16_t status, const uint8_t *data,
                                 uint16_t length, uint32_t cancelled)
{
    volatile IPCM_TestPeerMailbox *m = IPCM_TEST_PEER_MAILBOX;
    uint16_t i;
    if ((length > IPCM_TEST_PEER_BYTES) || ((length != 0U) && (data == NULL)))
    {
        return DRV_PARAM_ERR;
    }
    if (!IPCM_testPeerAvailable() || (sequence != m->sequence))
    {
        return DRV_ERROR;
    }
    for (i = 0U; i < length; ++i)
    {
        m->response[i] = data[i];
    }
    m->status = status;
    m->responseLength = length;
    m->state = cancelled ? IPCM_TEST_PEER_CANCELLED : IPCM_TEST_PEER_DONE;
    __DMB();
    m->completed = sequence;
    __DSB();
    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/
#endif

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
