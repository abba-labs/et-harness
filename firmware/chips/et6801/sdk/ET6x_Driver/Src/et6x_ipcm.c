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

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
