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

#ifndef __ET6x_AHBDMA_H
#define __ET6x_AHBDMA_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"
#include "et6x_sysctrl.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup AHBDMA
 * @{
 */

/* AHBDMA TCM offset */
#define ICTM_CORE0_TO_DMA_OFFSET    (0x28000000U)
#define DCTM_CORE0_TO_DMA_OFFSET    (0x08400000U)

/* AHBDMA channel numbers */
#define AHBDMA_NUM_CHANNELS         (8)

/* AHBDMA error channel number */
#define AHBDMA_CH_ERR               (0xFFFFFFFFU)

/* AHBDMA channel select */
#define AHBDMA_CH_0                 (0U)
#define AHBDMA_CH_1                 (1U)
#define AHBDMA_CH_2                 (2U)
#define AHBDMA_CH_3                 (3U)
#define AHBDMA_CH_4                 (4U)
#define AHBDMA_CH_5                 (5U)
#define AHBDMA_CH_6                 (6U)
#define AHBDMA_CH_7                 (7U)

/* AHBDMA channel max block transfer size */
#define AHBDMA_MAX_BLOCK_TR_SIZE    (4096U - 1U)

/* AHBDMA channel transfer width */
/* Source or Destination Transfer Width is 8 bits */
#define AHBDMA_BITS_8                  0U
/* Source or Destination Transfer Width is 16 bits */
#define AHBDMA_BITS_16                 1U
/* Source or Destination Transfer Width is 32 bits */
#define AHBDMA_BITS_32                 2U

/* AHBDMA channel address increment direction */
#define AHBDMA_INCREMENTAL             0U
#define AHBDMA_DECREMENTAL             1U
#define AHBDMA_FIXED                   2U

/* AHBDMA channel burst transfer items number */
#define AHBDMA_BURST_DATA_ITEMS_1      (0U)
#define AHBDMA_BURST_DATA_ITEMS_4      (1U)
#define AHBDMA_BURST_DATA_ITEMS_8      (2U)
#define AHBDMA_BURST_DATA_ITEMS_16     (3U)
#define AHBDMA_BURST_DATA_ITEMS_32     (4U)
#define AHBDMA_BURST_DATA_ITEMS_64     (5U)
#define AHBDMA_BURST_DATA_ITEMS_128    (6U)
#define AHBDMA_BURST_DATA_ITEMS_256    (7U)

/* AHBDMA channel transfer type */
/* Transfer Type is memory to memory and Flow Controller is DMAC */
#define AHBDMA_MEM_TO_MEM       (0U)
/* Transfer Type is memory to peripheral and Flow Controller is DMAC*/
#define AHBDMA_MEM_TO_PER       (1U)
/* Transfer Type is peripheral to memory and Flow Controller is DMAC*/
#define AHBDMA_PER_TO_MEM       (2U)
/* Transfer Type is peripheral to peripheral and Flow Controller is DMAC*/
#define AHBDMA_PER_TO_PER       (3U)

/* AHBDMA channel transfer channel priority */
#define AHBDMA_CH_PRIORITY_0    (0U) /* The lowest priority */
#define AHBDMA_CH_PRIORITY_1    (1U)
#define AHBDMA_CH_PRIORITY_2    (2U)
#define AHBDMA_CH_PRIORITY_3    (3U)
#define AHBDMA_CH_PRIORITY_4    (4U)
#define AHBDMA_CH_PRIORITY_5    (5U)
#define AHBDMA_CH_PRIORITY_6    (6U)
#define AHBDMA_CH_PRIORITY_7    (7U) /* The highest priority */

/* AHBDMA channel FIFO mode select */
/* Space/data available for single AHB transfer of the specified transfer width */
#define AHBDMA_FIFO_SINGLE        (0U)

/**
 * Data available is greater than or
 * equal to half the fifo depth for destination transfers and
 * space available is greater than half the fifo depth for
 * source transfers. the exceptions are at the end of a burst
 * transaction request or at the end of a block transfer.
 */
#define AHBDMA_FIFO_HALF_DEPTH    (1U)

/* AHBDMA interrupt mask */
#define AHBDMA_IT_TFR_MASK        (0x01)
#define AHBDMA_IT_BLOCK_MASK      (0x02)
#define AHBDMA_IT_SRCTRAN_MASK    (0x04)
#define AHBDMA_IT_DSTTRAN_MASK    (0x08)
#define AHBDMA_IT_ERR_MASK        (0x10)

/* AHBDMA channel memory hardware interface */
#define AHBDMA_IF_MEM             (0U)

/* AHBDMA0 channel hardware interface */
#define AHBDMA_IF_0               (0U)
#define AHBDMA_IF_1               (1U)
#define AHBDMA_IF_2               (2U)
#define AHBDMA_IF_3               (3U)
#define AHBDMA_IF_4               (4U)
#define AHBDMA_IF_5               (5U)
#define AHBDMA_IF_6               (6U)
#define AHBDMA_IF_7               (7U)

/* AHBDMA channel multi trans type */
#define AHBDMA_CONTIGUOUS         0U
#define AHBDMA_RELOAD             1U
#define AHBDMA_LINKED_LIST        2U

/**
 * @brief AHBDMA channel init structure
 *
 */
typedef struct __PACKED
{
    uint32_t      sar;                          /* source address  */
    uint32_t      dar;                          /* destination address */
    uint8_t       srcTrWidth;                   /* source transfer width */
    uint8_t       dstTrWidth;                   /* destination transfer width */
    uint8_t       srcAddressInc;                /* source address incremental direction */
    uint8_t       dstAddressInc;                /* destination address incremental direction */
    uint8_t       srcBurstDataItemsNum;         /* source burst transfer data items number */
    uint8_t       dstBurstDataItemsNum;         /* destination burst transfer data items number */
    uint8_t       tfrType;                      /* transfer type in channel */
    ControlStatus dstLLPEn;                     /* destination LLP transfer enable or disable */
    ControlStatus srcLLPEn;                     /* source LLP transfer enable or disable */
    uint16_t      blkTfrSize;                   /* block transfer size */
    ControlStatus wbDoneEn;                     /* write back when transfer is done */
    uint8_t       prior;                        /* priority select */
    ControlStatus srcReloadEn;                  /* destination reload transfer enable or di */
    ControlStatus dstReloadEn;                  /* source reload transfer enable or disable */
    uint8_t       fifoMode;                     /* fifo mode in transfer */
    uint8_t       srcPer;                       /* source address DMA interface */
    uint8_t       dstPer;                       /* destination address DMA interface */
    uint32_t      llp;                          /* link-list pointer */
    ControlStatus srcGatherEn;                  /* source gather transfer enable or disable */
    uint32_t      srcGatherCount;               /* source gather transfer count value */
    uint32_t      srcGatherInterval;            /* source gather transfer interval value */
    ControlStatus dstScatterEn;                 /* destination scatter transfer enable or disable */
    uint32_t      dstScatterCount;              /* destination scatter transfer count value */
    uint32_t      dstScatterInterval;           /* destination scatter transfer interval value */
} AHBDMA_Ch_Init_TypeDef;

/**
 * @brief AHBDMA LLI register structure
 *
 */
typedef struct
{
    uint32_t SAR;               /* store source address register */
    uint32_t DAR;               /* store destination address register */
    uint32_t LLP;               /* store link-list pointer register */
    uint32_t CTL_L;             /* store transfer control low 32 register */
    uint32_t CTL_H;             /* store transfer control high 32 register */
    uint32_t SSTAT;             /* store source status register */
    uint32_t DSTAT;             /* store destination status register */
} AHBDMA_LLI_TypeDef;

/**
 * @brief AHBDMA LLI init structure, including all parameters to fill LLI register structure.
 * member <intEn> is added to control interrupt.
 *
 */
typedef struct __PACKED
{
    uint32_t      sar;                               /* source address  */
    uint32_t      dar;                               /* destination address */
    ControlStatus intEn;                             /* interrupt enable or disable */
    uint8_t       srcTrWidth;                        /* source transfer width */
    uint8_t       dstTrWidth;                        /* destination transfer width */
    uint8_t       srcAddressInc;                     /* source address incremental direction */
    uint8_t       dstAddressInc;                     /* destination address incremental direction */
    uint8_t       srcBurstDataItemsNum;              /* source burst transfer data items number */
    uint8_t       dstBurstDataItemsNum;              /* destination burst transfer data items number */
    ControlStatus dstScatterEn;                      /* source gather transfer enable or disable */
    ControlStatus srcGatherEn;                       /* destination scatter transfer enable or disable */
    uint8_t       tfrType;                           /* transfer type in channel */
    ControlStatus dstLLPEn;                          /* destination LLP transfer enable or disable */
    ControlStatus srcLLPEn;                          /* source LLP transfer enable or disable */
    uint16_t      blkTfrSize;                        /* block transfer size */
    ControlStatus wbDoneEn;                          /* write back when transfer is done */
    uint32_t      llp;                               /* link-list pointer */
} AHBDMA_LLI_Init_TypeDef;

DRV_Status AHBDMA_enableModule(AHBDMA_Type *AHBDMAx);
DRV_Status AHBDMA_disableModule(AHBDMA_Type *AHBDMAx);
void AHBDMA_initChannel(AHBDMA_Type *AHBDMAx, const AHBDMA_Ch_Init_TypeDef *init, uint32_t ch);
DRV_Status AHBDMA_deInitChannel(AHBDMA_Type *AHBDMAx, uint32_t ch);
void AHBDMA_initChannelStruct(AHBDMA_Ch_Init_TypeDef *init);
DRV_Status AHBDMA_enableChannel(AHBDMA_Type *AHBDMAx, uint32_t ch);
DRV_Status AHBDMA_disableChannel(AHBDMA_Type *AHBDMAx, uint32_t ch);

void AHBDMA_suspendChannel(AHBDMA_Type *AHBDMAx, uint32_t ch);
void AHBDMA_resumeChannel(AHBDMA_Type *AHBDMAx, uint32_t ch);
uint32_t AHBDMA_findFreeChannel(AHBDMA_Type *AHBDMAx);
bool AHBDMA_isChannelFree(AHBDMA_Type *AHBDMAx, uint32_t ch);
bool AHBDMA_isChannelFifoEmpty(AHBDMA_Type *AHBDMAx, uint32_t ch);
DRV_Status AHBDMA_setDefaultM2M(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size);
DRV_Status AHBDMA_setDefaultM2P(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t dstPeripIF);
DRV_Status AHBDMA_setDefaultP2M(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t srcPeripIF);
DRV_Status AHBDMA_setDefaultP2P(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t srcPeripIF, uint8_t dstPeripIF);
DRV_Status AHBDMA_setMultiBlock(AHBDMA_Ch_Init_TypeDef *init, uint8_t sarUpdateMethod,
                                uint8_t darUpdateMethod, uint32_t llp);
void AHBDMA_setSourceGather(AHBDMA_Ch_Init_TypeDef *init, uint32_t gatherInterval, uint32_t gatherCount,
                            ControlStatus status);
void AHBDMA_setDestinationScatter(AHBDMA_Ch_Init_TypeDef *init, uint32_t scatterInterval,
                                  uint32_t scatterCount, ControlStatus status);
void AHBDMA_initLLI(AHBDMA_LLI_TypeDef *lli, const AHBDMA_LLI_Init_TypeDef *init, bool isLastLLI, uint32_t nextLLP);
void AHBDMA_initLLIStruct(AHBDMA_LLI_Init_TypeDef *init);
DRV_Status AHBDMA_setLLIDefaultM2M(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate);
DRV_Status AHBDMA_setLLIDefaultM2P(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate);
DRV_Status AHBDMA_setLLIDefaultP2M(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate);
DRV_Status AHBDMA_setLLIDefaultP2P(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate);
void AHBDMA_enableChannelInterrupt(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks);
void AHBDMA_disableChannelInterrupt(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks);
uint32_t AHBDMA_getTfrInterruptChannelMask(AHBDMA_Type *AHBDMAx);
uint32_t AHBDMA_getBlockInterruptChannelMask(AHBDMA_Type *AHBDMAx);
uint32_t AHBDMA_getSrctranInterruptChannelMask(AHBDMA_Type *AHBDMAx);
uint32_t AHBDMA_getDsttranInterruptChannelMask(AHBDMA_Type *AHBDMAx);
uint32_t AHBDMA_getErrInterruptChannelMask(AHBDMA_Type *AHBDMAx);
void AHBDMA_clearInterruptChannel(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* AHBDMA test-driver handshake source selection and active polarity. */
#define AHBDMA_TEST_HS_HARDWARE        (0U)
#define AHBDMA_TEST_HS_SOFTWARE        (1U)
#define AHBDMA_TEST_HS_ACTIVE_HIGH     (0U)
#define AHBDMA_TEST_HS_ACTIVE_LOW      (1U)

/* AHBDMA test-driver software handshake request register selectors. */
#define AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_TRANSFER       (0U)
#define AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_TRANSFER  (1U)
#define AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_SINGLE         (2U)
#define AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_SINGLE    (3U)
#define AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_LAST           (4U)
#define AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_LAST      (5U)

typedef struct
{
    uint32_t dmaId;
    uint32_t componentId;
    uint32_t channelParams[AHBDMA_NUM_CHANNELS];
    uint32_t multiBlockParams;
    uint32_t maxBlockSizeParams;
} AHBDMA_TestComponentSnapshot_TypeDef;

typedef struct
{
    uint32_t raw[5];
    uint32_t status[5];
    uint32_t mask[5];
    uint32_t combinedStatus;
} AHBDMA_TestInterruptSnapshot_TypeDef;

typedef struct
{
    uint32_t sar;
    uint32_t dar;
    uint32_t llp;
    uint32_t ctlLow;
    uint32_t ctlHigh;
    uint32_t cfgLow;
    uint32_t cfgHigh;
    uint32_t sourceGather;
    uint32_t destinationScatter;
    uint32_t sourceBurst;
    uint32_t destinationBurst;
    uint32_t blockSize;
    uint32_t fifoMode;
} AHBDMA_TestChannelSnapshot_TypeDef;

/** @brief Enable selected channels with one atomic write for test diagnostics. */
DRV_Status AHBDMA_testEnableChannelsByMask(AHBDMA_Type *AHBDMAx, uint32_t channelMask);

/** @brief Read the enabled-channel mask for test diagnostics. */
uint32_t AHBDMA_testGetEnabledChannels(AHBDMA_Type *AHBDMAx);

/** @brief Configure endpoint handshake fields without changing other CFGL bits. */
DRV_Status AHBDMA_testConfigureChannelHandshake(
    AHBDMA_Type *AHBDMAx,
    uint32_t ch,
    uint8_t srcHandshakeMode,
    uint8_t dstHandshakeMode,
    uint8_t srcHandshakePolarity,
    uint8_t dstHandshakePolarity);

/** @brief Assert or clear one named software handshake request. */
DRV_Status AHBDMA_testSetSoftwareHandshakeRequest(AHBDMA_Type *AHBDMAx, uint32_t ch,
                                                   uint32_t requestType, ControlStatus status);

/** @brief Capture component identification and parameter registers. */
DRV_Status AHBDMA_testGetComponentSnapshot(AHBDMA_Type *AHBDMAx,
                                            AHBDMA_TestComponentSnapshot_TypeDef *snapshot);

/** @brief Capture raw, status, mask, and combined interrupt registers. */
DRV_Status AHBDMA_testGetInterruptSnapshot(AHBDMA_Type *AHBDMAx,
                                            AHBDMA_TestInterruptSnapshot_TypeDef *snapshot);

/** @brief Capture all channel registers for test diagnostics. */
DRV_Status AHBDMA_testGetChannelSnapshot(AHBDMA_Type *AHBDMAx, uint32_t ch,
                                          AHBDMA_TestChannelSnapshot_TypeDef *snapshot);

/**
 * @brief Capture a DWT start cycle and enable one DMA channel.
 * @param AHBDMAx DMA controller instance.
 * @param ch Channel number owned by the caller.
 * @param startCycles Receives the cycle value sampled immediately before the
 *        channel enable operation.
 * @return DRV_OK on success, DRV_PARAM_ERR for invalid arguments, or DRV_ERROR
 *         when the DWT cycle counter is not implemented.
 */
DRV_Status AHBDMA_testStartChannelTimed(
    AHBDMA_Type *AHBDMAx,
    uint32_t ch,
    uint32_t *startCycles);

/**
 * @brief Return elapsed DWT cycles from a previously captured start value.
 * @param startCycles Start value returned by AHBDMA_testStartChannelTimed().
 * @param elapsedCycles Receives wrap-safe unsigned elapsed cycles.
 * @return DRV_OK on success, DRV_PARAM_ERR for a NULL output pointer, or
 *         DRV_ERROR when the DWT cycle counter is not implemented.
 */
DRV_Status AHBDMA_testGetElapsedCycles(
    uint32_t startCycles,
    uint32_t *elapsedCycles);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

#ifdef __cplusplus
}
#endif

#endif /* __ET6x_AHBDMA_H */
