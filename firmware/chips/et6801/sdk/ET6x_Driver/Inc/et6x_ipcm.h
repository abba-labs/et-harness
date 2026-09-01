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

#ifndef __ET6x_IPCM_H
#define __ET6x_IPCM_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** addtogroup ET6001_Driver
 * @{
 */

/** addtogroup IPCM
 * @{
 */

/* IPCM inital structure */
typedef struct
{
    uint32_t srcChanID;     /* source channel ID */
    uint32_t dstChanID;     /* destination channel ID */
    uint32_t mboxID;        /* selected mail box ID */
    uint32_t mode;          /* transfer mode */
    uint32_t linkedMboxNum; /* linked mail box number, used only when [mode] is [AUTO_LINK] or [AUTO_ACK_LINK] */
} IPCM_InitTypeDef;

/* IPCM channel channel index */
#define IPCM_CH_0                 (0U)
#define IPCM_CH_1                 (1U)
#define IPCM_CH_2                 (2U)
#define IPCM_CH_3                 (3U)
#define IPCM_CH_4                 (4U)
#define IPCM_CH_5                 (5U)
#define IPCM_CH_6                 (6U)
#define IPCM_CH_7                 (7U)
#define IPCM_CH_8                 (8U)
#define IPCM_CH_9                 (9U)
#define IPCM_CH_10                (10U)
#define IPCM_CH_11                (11U)
#define IPCM_CH_12                (12U)
#define IPCM_CH_13                (13U)
#define IPCM_CH_14                (14U)
#define IPCM_CH_15                (15U)

/* IPCM mailbox index */
#define MAILBOX0                  (0U)
#define MAILBOX1                  (1U)
#define MAILBOX2                  (2U)
#define MAILBOX3                  (3U)
#define MAILBOX4                  (4U)
#define MAILBOX5                  (5U)
#define MAILBOX6                  (6U)
#define MAILBOX7                  (7U)
#define MAILBOX8                  (8U)
#define MAILBOX9                  (9U)
#define MAILBOX10                 (10U)
#define MAILBOX11                 (11U)
#define MAILBOX12                 (12U)
#define MAILBOX13                 (13U)
#define MAILBOX14                 (14U)
#define MAILBOX15                 (15U)

/* IPCM transfer acknowage mode */
#define MANUAL_ACK                (0U)
#define AUTO_ACK                  (1U)
#define AUTO_LINK                 (2U)
#define AUTO_ACK_LINK             (3U)

/* IPCM mailbox number */
#define MAILBOX_NUM               (16U)

/* IPCM channel number */
#define IPCM_CH_NUM               (16U)

/* IPCM mailbox data register numner */
#define MAILBOX_DR_NUM            (7U)

/* IPCM mailbox data register size in bytes */
#define MAILBOX_DR_SIZE           (28U)

/* IPCM the maximum linked mailbox number */
#define MAILBOX_LINKED_MAX_NUM    (15U)

void IPCM_mailboxInit(const IPCM_InitTypeDef *init);
void IPCM_mailboxDeInit(const IPCM_InitTypeDef *init);
void IPCM_mailboxStructInit(IPCM_InitTypeDef *init);
void IPCM_sendData(uint32_t mboxID, void *data, uint32_t size);
void IPCM_receiveData(uint32_t mboxID, void *data, uint32_t size);
void IPCM_updateAckData(uint32_t mboxID, void *data, uint32_t size);
void IPCM_sendDataLinked(uint32_t mboxID, void *data, uint32_t size);
void IPCM_clearDestination(uint32_t mboxID, uint32_t chanID);
uint32_t IPCM_getMailboxInterrupt(uint32_t chanID);
void IPCM_clearMailboxInterruptAndSendAck(uint32_t mboxID);
void IPCM_clearMailboxInterrupt(uint32_t mboxID);


/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif  /* __ET6x_IPCM_H */
