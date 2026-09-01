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
#include "et6x_ahbdma.h"

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/

/* Private macro -------------------------------------------------------------*/
/*! Parameter validity check for AHBDMA peripheral . */
#define IS_AHBDMA_PERIPHERAL(x) \
        (((x) == AHBDMA0) || ((x) == AHBDMA1))

/*! Parameter validity check for AHBDMA channel . */
#define IS_AHBDMA_CHANNEL(ch) \
        (((ch) == AHBDMA_CH_0) || \
         ((ch) == AHBDMA_CH_1) || \
         ((ch) == AHBDMA_CH_2) || \
         ((ch) == AHBDMA_CH_3) || \
         ((ch) == AHBDMA_CH_4) || \
         ((ch) == AHBDMA_CH_5) || \
         ((ch) == AHBDMA_CH_6) || \
         ((ch) == AHBDMA_CH_7))

/*! Parameter validity check for AHBDMA interrupt mask . */
#define IS_AHBDMA_ITMASK(mask) \
        ((((mask)&AHBDMA_IT_TFR_MASK) != 0) || \
         (((mask)&AHBDMA_IT_BLOCK_MASK) != 0) || \
         (((mask)&AHBDMA_IT_SRCTRAN_MASK) != 0) || \
         (((mask)&AHBDMA_IT_DSTTRAN_MASK) != 0) || \
         (((mask)&AHBDMA_IT_ERR_MASK) != 0))

/*! Parameter validity check for AHBDMA peripheral IF mask . */
#define IS_AHBDMA_PERIP_IF(peripIF) \
        ((peripIF) == AHBDMA_IF_0) || \
        ((peripIF) == AHBDMA_IF_1) || \
        ((peripIF) == AHBDMA_IF_2) || \
        ((peripIF) == AHBDMA_IF_3) || \
        ((peripIF) == AHBDMA_IF_4) || \
        ((peripIF) == AHBDMA_IF_5) || \
        ((peripIF) == AHBDMA_IF_6) || \
        ((peripIF) == AHBDMA_IF_7)

#define AHBDMA_TIMEOUT    (1000000U)

#define OFFSET(TYPE, MEMBER)    ((uint32_t)(&(((TYPE *)0)->MEMBER)))

#define AHBDMA_CH_CTL_INIT_VALUE_L    (0x00304801U)
#define AHBDMA_CH_CTL_INIT_VALUE_H    (0x2U)
#define AHBDMA_CH_CFG_INIT_VALUE_L    (0x00000EE0U)
#define AHBDMA_CH_CFG_INIT_VALUE_H    (0x4U)

/* ENABLE / DISABLE Channel*/
#define CH_ENABLE_WE_OFFSET           (0x101U)
#define CH_DISABLE_WE_OFFSET          (0x100U)
#define AHBDMA_CH_WE_ENABLE(ch)     (CH_ENABLE_WE_OFFSET << ch)
#define AHBDMA_CH_WE_DISABLE(ch)    (CH_DISABLE_WE_OFFSET << ch)

/* ENABLE / DISABLE IT Channel*/
#define CH_ENABLE_IT_WE_OFFSET     (0x101U)
#define CH_DISABLE_IT_WE_OFFSET    (0x100U)
#define AHBDMA_CH_IT_WE_ENABLE(ch)     (CH_ENABLE_IT_WE_OFFSET << ch)
#define AHBDMA_CH_IT_WE_DISABLE(ch)    (CH_DISABLE_IT_WE_OFFSET << ch)

#define MAX_GATHER_SCATTER_COUNT       (0xFFFU)
#define MAX_GATHER_SCATTER_INTERVAL    (0xFFFFFU)

/*! Parameter validity check for AHBDMA transfer size . */
#define IS_AHBDMA_TR_SIZE(size)    ((size) <= AHBDMA_MAX_BLOCK_TR_SIZE)

/*! Parameter validity check for AHBDMA transfer width . */
#define IS_AHBDMA_TR_WIDTH(width) \
        (((width) == AHBDMA_BITS_8) || ((width) == AHBDMA_BITS_16) || ((width) == AHBDMA_BITS_32))

/*! Parameter validity check for AHBDMA transfer direction . */
#define IS_AHBDMA_TR_DIRECTION(dir) \
        (((dir) == AHBDMA_INCREMENTAL) || ((dir) == AHBDMA_DECREMENTAL) || ((dir) == AHBDMA_FIXED))

/*! Parameter validity check for AHBDMA burst transfer items */
#define IS_AHBDMA_TR_BURST_ITERMS(items) \
        (((items) == AHBDMA_BURST_DATA_ITEMS_1) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_4) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_8) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_16) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_32) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_64) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_128) || \
         ((items) == AHBDMA_BURST_DATA_ITEMS_256))

/*! Parameter validity check for AHBDMA transfer type */
#define IS_AHBDMA_TR_TYPE(type) \
        (((type) == AHBDMA_MEM_TO_MEM) || \
         ((type) == AHBDMA_MEM_TO_PER) || \
         ((type) == AHBDMA_PER_TO_MEM) || \
         ((type) == AHBDMA_PER_TO_PER))

/*! Parameter validity check for AHBDMA transfer channel priority */
#define IS_AHBDMA_TR_PRIORITY(prior) \
        (((prior) == AHBDMA_CH_PRIORITY_0) || \
         ((prior) == AHBDMA_CH_PRIORITY_1) || \
         ((prior) == AHBDMA_CH_PRIORITY_2) || \
         ((prior) == AHBDMA_CH_PRIORITY_3) || \
         ((prior) == AHBDMA_CH_PRIORITY_4) || \
         ((prior) == AHBDMA_CH_PRIORITY_5) || \
         ((prior) == AHBDMA_CH_PRIORITY_6) || \
         ((prior) == AHBDMA_CH_PRIORITY_7))

/*! Parameter validity check for AHBDMA transfer fifo mode */
#define IS_AHBDMA_TR_FIFO_MODE(mode) \
        (((mode) == AHBDMA_FIFO_SINGLE) || ((mode) == AHBDMA_FIFO_HALF_DEPTH))

/*! Parameter validity check for AHBDMA multi transfer type */
#define IS_AHBDMA_MULTI_TR_TYPE(type) \
        (((type) == AHBDMA_CONTIGUOUS) || \
         ((type) == AHBDMA_RELOAD) || \
         ((type) == AHBDMA_LINKED_LIST))

/*! Parameter validity check for AHBDMA gather/scatter count */
#define IS_AHBDMA_GATHER_SCATTER_COUNT(count)          ((count) <= MAX_GATHER_SCATTER_COUNT)

/*! Parameter validity check for AHBDMA gather/scatter Interval */
#define IS_AHBDMA_GATHER_SCATTER_INTERVAL(interval)    ((interval) <= MAX_GATHER_SCATTER_INTERVAL)



/* Private variables ---------------------------------------------------------*/
/* Private function prototypes -----------------------------------------------*/
/* Exported functions --------------------------------------------------------*/

/**
 * @brief Enable AHBDMA device
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return DRV_Status
 * DRV_OK: enable success or have been enabled
 */
DRV_Status AHBDMA_enableModule(AHBDMA_Type *AHBDMAx)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    /* avoid re-enabling AHBDMA device */
    if (READ_BIT(AHBDMAx->DMACFGREG, AHBDMA0_DMACFGREG_DMA_EN_Msk) != 0)
    {
        return DRV_OK;
    }

    SET_BIT(AHBDMAx->DMACFGREG, AHBDMA0_DMACFGREG_DMA_EN_Msk);
    return DRV_OK;
}

/**
 * @brief Disable AHBDMA device
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return DRV_Status
 * DRV_OK: disable success
 * DRV_TIMEOUT: disable failed because of DMA transfer dost not end during timeout time
 */
DRV_Status AHBDMA_disableModule(AHBDMA_Type *AHBDMAx)
{
    uint32_t timeout = AHBDMA_TIMEOUT;
    uint32_t i;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (i = 0; i < AHBDMA_NUM_CHANNELS; i++)
    {
        AHBDMA_disableChannel(AHBDMAx, i);
        AHBDMA_clearInterruptChannel(AHBDMAx, i,
                                     AHBDMA_IT_TFR_MASK | AHBDMA_IT_BLOCK_MASK | AHBDMA_IT_SRCTRAN_MASK |
                                     AHBDMA_IT_DSTTRAN_MASK | AHBDMA_IT_ERR_MASK);
    }
    CLEAR_BIT(AHBDMAx->DMACFGREG, AHBDMA0_DMACFGREG_DMA_EN_Msk);
    while (timeout != 0U && (READ_BIT(AHBDMAx->DMACFGREG, AHBDMA0_DMACFGREG_DMA_EN_Msk) != 0))
    {
        timeout--;
    }


    if (timeout == 0)
    {
        return DRV_TIMEOUT;
    }

    return DRV_OK;
}

/**
 * @brief Enable channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @return DRV_Status
 * DRV_OK: enable success or have been enabled
 */
DRV_Status AHBDMA_enableChannel(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    /* avoid reenable, need a test */
    if ((READ_REG(AHBDMAx->CHENREG) & BIT_MASK(ch)) != 0)
    {
        return DRV_OK;
    }

    WRITE_REG(AHBDMAx->CHENREG, AHBDMA_CH_WE_ENABLE(ch));
    return DRV_OK;
}

/**
 * @brief Disable channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @return DRV_Status
 * DRV_OK: disable success
 * DRV_TIMEOUT: disable failed because of DMA transfer dost not end during timeout time
 */
DRV_Status AHBDMA_disableChannel(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    uint32_t timeout = AHBDMA_TIMEOUT;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    WRITE_REG(AHBDMAx->CHENREG, AHBDMA_CH_WE_DISABLE(ch));
    while (timeout != 0 && (READ_REG(AHBDMAx->CHENREG) & BIT_MASK(ch)) != 0)
    {
        timeout--;
    }

    if (timeout == 0)
    {
        return DRV_TIMEOUT;
    }

    return DRV_OK;
}

/**
 * @brief init channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param init  channel initialized parameter structure
 * @param ch  AHBDMA channel
 */
void AHBDMA_initChannel(AHBDMA_Type *AHBDMAx, const AHBDMA_Ch_Init_TypeDef *init, uint32_t ch)
{
    uint32_t reg     = 0;
    uint32_t srcAddr = init->sar;
    uint32_t dstAddr = init->dar;
    uint32_t llpAddr = init->llp;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_TR_SIZE(init->blkTfrSize));
    assert_param(IS_AHBDMA_TR_WIDTH(init->srcTrWidth));
    assert_param(IS_AHBDMA_TR_WIDTH(init->dstTrWidth));
    assert_param(IS_AHBDMA_TR_DIRECTION(init->srcAddressInc));
    assert_param(IS_AHBDMA_TR_DIRECTION(init->dstAddressInc));
    assert_param(IS_AHBDMA_TR_BURST_ITERMS(init->srcBurstDataItemsNum));
    assert_param(IS_AHBDMA_TR_BURST_ITERMS(init->dstBurstDataItemsNum));
    assert_param(IS_AHBDMA_TR_TYPE(init->tfrType));
    assert_param(IS_AHBDMA_TR_PRIORITY(init->prior));
    assert_param(IS_AHBDMA_TR_FIFO_MODE(init->fifoMode));
    assert_param(IS_AHBDMA_PERIP_IF(init->srcPer));
    assert_param(IS_AHBDMA_PERIP_IF(init->dstPer));
    assert_param(IS_AHBDMA_GATHER_SCATTER_INTERVAL(init->srcGatherInterval));
    assert_param(IS_AHBDMA_GATHER_SCATTER_COUNT(init->srcGatherCount));
    assert_param(IS_AHBDMA_GATHER_SCATTER_INTERVAL(init->dstScatterInterval));
    assert_param(IS_AHBDMA_GATHER_SCATTER_COUNT(init->dstScatterCount));

    if (srcAddr < RAMITCM_BASE + RAMITCM_SIZE)
    {
        srcAddr += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if (((srcAddr >= RAMDTCM_BASE) && (srcAddr < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        srcAddr += DCTM_CORE0_TO_DMA_OFFSET;
    }

    if (dstAddr < RAMITCM_BASE + RAMITCM_SIZE)
    {
        dstAddr += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if (((dstAddr >= RAMDTCM_BASE) && (dstAddr < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        dstAddr += DCTM_CORE0_TO_DMA_OFFSET;
    }

    if (((uint32_t)llpAddr > RAMITCM_BASE) && ((uint32_t)llpAddr < RAMITCM_BASE + RAMITCM_SIZE))
    {
        llpAddr += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if ((((uint32_t)llpAddr >= RAMDTCM_BASE) && ((uint32_t)llpAddr < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        llpAddr += DCTM_CORE0_TO_DMA_OFFSET;
    }

    WRITE_REG(AHBDMAx->CH[ch].SAR, srcAddr);
    WRITE_REG(AHBDMAx->CH[ch].DAR, dstAddr);
    WRITE_REG(AHBDMAx->CH[ch].LLP, llpAddr);

    reg = (uint32_t)init->srcTrWidth << AHBDMA0_CH_CTLL_SRC_TR_WIDTH_Pos |
          (uint32_t)init->dstTrWidth << AHBDMA0_CH_CTLL_DST_TR_WIDTH_Pos |
          (uint32_t)init->srcAddressInc << AHBDMA0_CH_CTLL_SINC_Pos |
          (uint32_t)init->dstAddressInc << AHBDMA0_CH_CTLL_DINC_Pos |
          (uint32_t)init->srcBurstDataItemsNum << AHBDMA0_CH_CTLL_SRC_MSIZE_Pos |
          (uint32_t)init->dstBurstDataItemsNum << AHBDMA0_CH_CTLL_DEST_MSIZE_Pos |
          (uint32_t)init->srcGatherEn << AHBDMA0_CH_CTLL_SRC_GATHER_EN_Pos |
          (uint32_t)init->dstScatterEn << AHBDMA0_CH_CTLL_DST_SCATTER_EN_Pos |
          (uint32_t)init->tfrType << AHBDMA0_CH_CTLL_TT_FC_Pos |
          (uint32_t)init->dstLLPEn << AHBDMA0_CH_CTLL_LLP_DST_EN_Pos |
          (uint32_t)init->srcLLPEn << AHBDMA0_CH_CTLL_LLP_SRC_EN_Pos;

    MODIFY_REG(AHBDMAx->CH[ch].CTLL, AHBDMA0_CH_CTLL_SRC_TR_WIDTH_Msk | AHBDMA0_CH_CTLL_DST_TR_WIDTH_Msk |
               AHBDMA0_CH_CTLL_SINC_Msk | AHBDMA0_CH_CTLL_DINC_Msk | AHBDMA0_CH_CTLL_SRC_MSIZE_Msk |
               AHBDMA0_CH_CTLL_DEST_MSIZE_Msk | AHBDMA0_CH_CTLL_SRC_GATHER_EN_Msk |
               AHBDMA0_CH_CTLL_DST_SCATTER_EN_Msk | AHBDMA0_CH_CTLL_TT_FC_Msk |
               AHBDMA0_CH_CTLL_LLP_DST_EN_Msk | AHBDMA0_CH_CTLL_LLP_SRC_EN_Msk, reg);

    reg = (uint32_t)init->blkTfrSize << AHBDMA0_CH_CTLH_BLOCK_TS_Pos |
          (uint32_t)init->wbDoneEn << AHBDMA0_CH_CTLH_DONE_Pos;

    MODIFY_REG(AHBDMAx->CH[ch].CTLH, AHBDMA0_CH_CTLH_BLOCK_TS_Msk | AHBDMA0_CH_CTLH_DONE_Msk, reg);

    reg = (uint32_t)init->prior << AHBDMA0_CH_CFGL_CH_PRIOR_Pos |
          (uint32_t)init->srcReloadEn << AHBDMA0_CH_CFGL_RELOAD_SRC_Pos |
          (uint32_t)init->dstReloadEn << AHBDMA0_CH_CFGL_RELOAD_DST_Pos;
    WRITE_REG(AHBDMAx->CH[ch].CFGL, reg);

    reg = (uint32_t)init->fifoMode << AHBDMA0_CH_CFGH_FIFO_MODE_Pos |
          (uint32_t)init->srcPer << AHBDMA0_CH_CFGH_SRC_PER_Pos |
          (uint32_t)init->dstPer << AHBDMA0_CH_CFGH_DEST_PER_Pos;
    WRITE_REG(AHBDMAx->CH[ch].CFGH, reg);


    WRITE_REG(AHBDMAx->CH[ch].SGR, init->srcGatherCount << AHBDMA0_CH_SGR_SGC_Pos |
              init->srcGatherInterval << AHBDMA0_CH_SGR_SGI_Pos);
    WRITE_REG(AHBDMAx->CH[ch].DSR, init->dstScatterCount << AHBDMA0_CH_DSR_DSC_Pos |
              init->dstScatterInterval << AHBDMA0_CH_DSR_DSI_Pos);
}

/**
 * @brief Deinit channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @return DRV_Status
 * DRV_OK: deinit success
 * DRV_TIMEOUT: deinit failed because of DMA transfer dost not end during timeout time
 */
DRV_Status AHBDMA_deInitChannel(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    if (AHBDMA_disableChannel(AHBDMAx, ch) != DRV_OK)
    {
        return DRV_ERROR;
    }

    WRITE_REG(AHBDMAx->CH[ch].SAR, 0U);
    WRITE_REG(AHBDMAx->CH[ch].DAR, 0U);
    WRITE_REG(AHBDMAx->CH[ch].LLP, 0U);
    WRITE_REG(AHBDMAx->CH[ch].CTLL, AHBDMA_CH_CTL_INIT_VALUE_L);
    WRITE_REG(AHBDMAx->CH[ch].CTLH, AHBDMA_CH_CTL_INIT_VALUE_H);
    WRITE_REG(AHBDMAx->CH[ch].CFGL, AHBDMA_CH_CFG_INIT_VALUE_L);
    WRITE_REG(AHBDMAx->CH[ch].CFGH, AHBDMA_CH_CFG_INIT_VALUE_H);
    WRITE_REG(AHBDMAx->CH[ch].SGR, 0U);
    WRITE_REG(AHBDMAx->CH[ch].DSR, 0U);
    return DRV_OK;
}

/**
 * @brief Init the channel initial structure
 *
 * @param init  channel initialized parameter structure
 */
void AHBDMA_initChannelStruct(AHBDMA_Ch_Init_TypeDef *init)
{
    init->sar                  = 0x0U;
    init->dar                  = 0x0U;
    init->srcTrWidth           = AHBDMA_BITS_8;
    init->dstTrWidth           = AHBDMA_BITS_8;
    init->srcAddressInc        = AHBDMA_INCREMENTAL;
    init->dstAddressInc        = AHBDMA_INCREMENTAL;
    init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstScatterEn         = DISABLE;
    init->srcGatherEn          = DISABLE;
    init->tfrType              = AHBDMA_PER_TO_PER;
    init->dstLLPEn             = DISABLE;
    init->srcLLPEn             = DISABLE;
    init->blkTfrSize           = 0x2U;
    init->wbDoneEn             = DISABLE;
    init->prior                = AHBDMA_CH_PRIORITY_7;
    init->srcReloadEn          = DISABLE;
    init->dstReloadEn          = DISABLE;
    init->fifoMode             = AHBDMA_FIFO_SINGLE;
    init->srcPer               = AHBDMA_IF_MEM;
    init->dstPer               = AHBDMA_IF_MEM;
    init->llp                  = 0x0U;
    init->srcGatherInterval    = 0x0U;
    init->srcGatherCount       = 0x0U;
    init->dstScatterInterval   = 0x0U;
    init->dstScatterCount      = 0x0U;
}

/**
 * @brief Suspend channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 */
void AHBDMA_suspendChannel(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    SET_BIT(AHBDMAx->CH[ch].CFGL, AHBDMA0_CH_CFGL_CH_SUSP_Msk);
}

/**
 * @brief Resume channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 */
void AHBDMA_resumeChannel(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    CLEAR_BIT(AHBDMAx->CH[ch].CFGL, AHBDMA0_CH_CFGL_CH_SUSP_Msk);
}

/**
 * @brief Find a free channel
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * AHBDMA_CH_ERR: No free channel
 * channel ID: The free channel ID
 */
uint32_t AHBDMA_findFreeChannel(AHBDMA_Type *AHBDMAx)
{
    uint32_t i;
    uint32_t ch = AHBDMA_CH_ERR;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (i = 0; i < AHBDMA_NUM_CHANNELS; i++)
    {
        if ((READ_REG(AHBDMAx->CHENREG) & BIT_MASK(i)) == 0)
        {
            ch = i;
            break;
        }
    }

    return ch;
}

/**
 * @brief Return specified AXIDMA transfer channel is free or not
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AXIDMA transfer channel index
 * @return true  channel is under a transfer
 * @return false  channel is not initialized or have completed tansfer
 */
bool AHBDMA_isChannelFree(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    if ((READ_REG(AHBDMAx->CHENREG) & BIT_MASK(ch)) == 0)
    {
        return true;
    }
    else
    {
        return false;
    }
}

/**
 * @brief Judge channel fifo is empty or not
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @return true  channel fifo is empty
 * @return false  channel fifo is not empty
 */
bool AHBDMA_isChannelFifoEmpty(AHBDMA_Type *AHBDMAx, uint32_t ch)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    return(READ_BIT(AHBDMAx->CH[ch].CFGL, AHBDMA0_CH_CFGL_FIFO_EMPTY_Msk) != 0);
}

/**
 * @brief Get default settings for m2m mode, single-block transmitting mode
 *
 * @param init  channel initialized parameter structure
 * @param srcAddress  source address
 * @param dstAddress  destination address
 * @param size  transfer size for single block
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setDefaultM2M(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size)
{
    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_INCREMENTAL;
    init->dstAddressInc = AHBDMA_INCREMENTAL;

    if ((size >= 1) && (size <= 3))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    }
    else if ((size >= 4) && (size <= 7))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_4;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_4;
    }
    else if ((size >= 8) && (size <= 15))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_8;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_8;
    }
    else if ((size >= 16) && (size <= 31))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_16;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_16;
    }
    else if ((size >= 32) && (size <= 63))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_32;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_32;
    }
    else if ((size >= 64) && (size <= 127))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_64;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_64;
    }
    else if ((size >= 128) && (size <= 255))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_128;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_128;
    }
    else
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_256;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_256;
    }

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;           //single BLOCK is not suitable
    init->tfrType      = AHBDMA_MEM_TO_MEM;
    init->dstLLPEn     = DISABLE;
    init->srcLLPEn     = DISABLE;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = DISABLE;

    init->prior              = AHBDMA_CH_PRIORITY_4;
    init->srcReloadEn        = DISABLE;
    init->dstReloadEn        = DISABLE;
    init->fifoMode           = AHBDMA_FIFO_SINGLE;
    init->srcPer             = AHBDMA_IF_MEM;
    init->dstPer             = AHBDMA_IF_MEM;
    init->llp                = 0U;
    init->srcGatherInterval  = 0x0U;
    init->srcGatherCount     = 0x0U;
    init->dstScatterInterval = 0x0U;
    init->dstScatterCount    = 0x0U;
    return DRV_OK;
}

/**
 * @brief Get default settings for m2p mode, single-block transmitting mode
 *
 * @param init  channel initialized parameter structure
 * @param srcAddress  source address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size for single block
 * @param dstPeripIF  destination peripheral channel
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setDefaultM2P(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t dstPeripIF)
{
    assert_param(IS_AHBDMA_PERIP_IF(dstPeripIF));

    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_INCREMENTAL;
    init->dstAddressInc = AHBDMA_FIXED;

    init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_MEM_TO_PER;
    init->dstLLPEn     = DISABLE;
    init->srcLLPEn     = DISABLE;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = DISABLE;

    init->prior              = AHBDMA_CH_PRIORITY_4;
    init->srcReloadEn        = DISABLE;
    init->dstReloadEn        = DISABLE;
    init->fifoMode           = AHBDMA_FIFO_SINGLE;
    init->srcPer             = AHBDMA_IF_MEM;
    init->dstPer             = dstPeripIF;
    init->llp                = 0U;
    init->srcGatherInterval  = 0x0U;
    init->srcGatherCount     = 0x0U;
    init->dstScatterInterval = 0x0U;
    init->dstScatterCount    = 0x0U;
    return DRV_OK;
}

/**
 * @brief Get default settings for p2m mode, single-block transmitting mode
 *
 * @param init  channel initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation address
 * @param srcPeripIF  source peripheral channel index
 * @param size  transfer size for single block
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setDefaultP2M(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t srcPeripIF)
{
    assert_param(IS_AHBDMA_PERIP_IF(srcPeripIF));

    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_FIXED;
    init->dstAddressInc = AHBDMA_INCREMENTAL;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_PER_TO_MEM;

    init->dstLLPEn   = DISABLE;
    init->srcLLPEn   = DISABLE;
    init->blkTfrSize = (uint16_t)size;
    init->wbDoneEn   = DISABLE;

    init->prior              = AHBDMA_CH_PRIORITY_4;
    init->srcReloadEn        = DISABLE;
    init->dstReloadEn        = DISABLE;
    init->fifoMode           = AHBDMA_FIFO_SINGLE;
    init->srcPer             = srcPeripIF;
    init->dstPer             = AHBDMA_IF_MEM;
    init->llp                = 0U;
    init->srcGatherInterval  = 0x0U;
    init->srcGatherCount     = 0x0U;
    init->dstScatterInterval = 0x0U;
    init->dstScatterCount    = 0x0U;
    return DRV_OK;
}

/**
 * @brief Get default settings for p2p mode, single-block transmitting mode
 *
 * @param init  channel initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size
 * @param srcPeripIF  source peripheral channel
 * @param dstPeripIF  destination peripheral channel
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setDefaultP2P(AHBDMA_Ch_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                uint32_t size, uint8_t srcPeripIF, uint8_t dstPeripIF)
{
    assert_param(IS_AHBDMA_PERIP_IF(srcPeripIF));
    assert_param(IS_AHBDMA_PERIP_IF(dstPeripIF));

    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_FIXED;
    init->dstAddressInc = AHBDMA_FIXED;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_PER_TO_PER;

    init->dstLLPEn   = DISABLE;
    init->srcLLPEn   = DISABLE;
    init->blkTfrSize = (uint16_t)size;
    init->wbDoneEn   = DISABLE;

    init->prior              = AHBDMA_CH_PRIORITY_4;
    init->srcReloadEn        = DISABLE;
    init->dstReloadEn        = DISABLE;
    init->fifoMode           = AHBDMA_FIFO_SINGLE;
    init->srcPer             = srcPeripIF;
    init->dstPer             = dstPeripIF;
    init->llp                = 0U;
    init->srcGatherInterval  = 0x0U;
    init->srcGatherCount     = 0x0U;
    init->dstScatterInterval = 0x0U;
    init->dstScatterCount    = 0x0U;
    return DRV_OK;
}

/**
 * @brief Multi-Block transfer parameter set
 *
 * @param init  channel initialized parameter structure
 * @param sarUpdateMethod  SAR register update metheod in multi transfer
 * @param darUpdateMethod  DAR register update metheod in multi transfer
 * @param llp  link-list pointer
 * @return DRV_Status
 * DRV_OK: success
 * DRV_INVALID: sarUpdateMethod and darUpdateMethod do match
 */
DRV_Status AHBDMA_setMultiBlock(AHBDMA_Ch_Init_TypeDef *init, uint8_t sarUpdateMethod, uint8_t darUpdateMethod,
                                uint32_t llp)
{
    assert_param(IS_AHBDMA_MULTI_TR_TYPE(sarUpdateMethod));
    assert_param(IS_AHBDMA_MULTI_TR_TYPE(darUpdateMethod));

    init->llp = (uint32_t)llp & AHBDMA0_CH_LLP_LOC_Msk;

    if ((sarUpdateMethod == AHBDMA_CONTIGUOUS) && (darUpdateMethod == AHBDMA_CONTIGUOUS))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = DISABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_CONTIGUOUS) && (darUpdateMethod == AHBDMA_RELOAD))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = ENABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_RELOAD) && (darUpdateMethod == AHBDMA_CONTIGUOUS))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = ENABLE;
        init->dstReloadEn = DISABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_RELOAD) && (darUpdateMethod == AHBDMA_RELOAD))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = ENABLE;
        init->dstReloadEn = ENABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_CONTIGUOUS) && (darUpdateMethod == AHBDMA_LINKED_LIST))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = ENABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = DISABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_RELOAD) && (darUpdateMethod == AHBDMA_LINKED_LIST))
    {
        init->srcLLPEn    = DISABLE;
        init->dstLLPEn    = ENABLE;
        init->srcReloadEn = ENABLE;
        init->dstReloadEn = DISABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_LINKED_LIST) && (darUpdateMethod == AHBDMA_CONTIGUOUS))
    {
        init->srcLLPEn    = ENABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = DISABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_LINKED_LIST) && (darUpdateMethod == AHBDMA_RELOAD))
    {
        init->srcLLPEn    = ENABLE;
        init->dstLLPEn    = DISABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = ENABLE;
    }
    else if ((sarUpdateMethod == AHBDMA_LINKED_LIST) && (darUpdateMethod == AHBDMA_LINKED_LIST))
    {
        init->srcLLPEn    = ENABLE;
        init->dstLLPEn    = ENABLE;
        init->srcReloadEn = DISABLE;
        init->dstReloadEn = DISABLE;
    }
    else
    {
        return DRV_INVALID;
    }

    return DRV_OK;
}

/**
 * @brief Set source gather transfer parameter
 *
 * @param init  LLI initialized parameter structure
 * @param gatherInterval  source gather interval
 * @param gatherCount  source gather count
 * @param status  ENABLE or DISABLE source gather transfer
 */
void AHBDMA_setSourceGather(AHBDMA_Ch_Init_TypeDef *init, uint32_t gatherInterval, uint32_t gatherCount,
                            ControlStatus status)
{
    assert_param(IS_AHBDMA_GATHER_SCATTER_INTERVAL(gatherInterval));
    assert_param(IS_AHBDMA_GATHER_SCATTER_COUNT(gatherCount));

    if (status == ENABLE)
    {
        init->srcGatherEn       = ENABLE;
        init->srcGatherCount    = gatherCount;
        init->srcGatherInterval = gatherInterval;
    }
    else
    {
        init->srcGatherEn       = DISABLE;
        init->srcGatherCount    = gatherCount;
        init->srcGatherInterval = gatherInterval;
    }
}

/**
 * @brief Set source gather transfer parameter
 *
 * @param init  LLI initialized parameter structure
 * @param scatterInterval  source gather interval
 * @param scatterCount  source gather count
 * @param status  ENABLE or DISABLE source gather transfer
 */
void AHBDMA_setDestinationScatter(AHBDMA_Ch_Init_TypeDef *init, uint32_t scatterInterval,
                                  uint32_t scatterCount, ControlStatus status)
{
    assert_param(IS_AHBDMA_GATHER_SCATTER_INTERVAL(scatterInterval));
    assert_param(IS_AHBDMA_GATHER_SCATTER_COUNT(scatterCount));

    if (status == ENABLE)
    {
        init->dstScatterEn       = ENABLE;
        init->dstScatterCount    = scatterCount;
        init->dstScatterInterval = scatterInterval;
    }
    else
    {
        init->dstScatterEn       = DISABLE;
        init->dstScatterCount    = scatterCount;
        init->dstScatterInterval = scatterInterval;
    }
}

/**
 * @brief Init LLI initial structure
 *
 * @param init  LLI initialized parameter structure
 */
void AHBDMA_initLLIStruct(AHBDMA_LLI_Init_TypeDef *init)
{
    init->sar                  = 0x0U;
    init->dar                  = 0x0U;
    init->intEn                = ENABLE;
    init->srcTrWidth           = AHBDMA_BITS_8;
    init->dstTrWidth           = AHBDMA_BITS_8;
    init->srcAddressInc        = AHBDMA_INCREMENTAL;
    init->dstAddressInc        = AHBDMA_INCREMENTAL;
    init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstScatterEn         = DISABLE;
    init->srcGatherEn          = DISABLE;
    init->tfrType              = AHBDMA_PER_TO_PER;
    init->dstLLPEn             = DISABLE;
    init->srcLLPEn             = DISABLE;
    init->blkTfrSize           = 0x2U;
    init->wbDoneEn             = DISABLE;
}

/**
 * @brief Init LINK-LIST item
 *
 * @param[in] init: LLI initialized parameter structure
 * @param[out] lli: Pointer to link-list item
 * @param[in] isLastLLI: whether is the last link-list item
 * @param[in] nextLLP Link-list item
 */
void AHBDMA_initLLI(AHBDMA_LLI_TypeDef *lli, const AHBDMA_LLI_Init_TypeDef *init, bool isLastLLI, uint32_t nextLLP)
{
    uint32_t      reg            = 0;
    uint32_t      srcAddr        = init->sar;
    uint32_t      dstAddr        = init->dar;
    ControlStatus srcLLPEnStatus = init->srcLLPEn;
    ControlStatus dstLLPEnStatus = init->dstLLPEn;

    assert_param(IS_AHBDMA_TR_SIZE(init->blkTfrSize));
    assert_param(IS_AHBDMA_TR_WIDTH(init->srcTrWidth));
    assert_param(IS_AHBDMA_TR_WIDTH(init->dstTrWidth));
    assert_param(IS_AHBDMA_TR_DIRECTION(init->srcAddressInc));
    assert_param(IS_AHBDMA_TR_DIRECTION(init->dstAddressInc));
    assert_param(IS_AHBDMA_TR_BURST_ITERMS(init->srcBurstDataItemsNum));
    assert_param(IS_AHBDMA_TR_BURST_ITERMS(init->dstBurstDataItemsNum));
    assert_param(IS_AHBDMA_TR_TYPE(init->tfrType));

    if (srcAddr < RAMITCM_BASE + RAMITCM_SIZE)
    {
        srcAddr += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if (((srcAddr >= RAMDTCM_BASE) && (srcAddr < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        srcAddr += DCTM_CORE0_TO_DMA_OFFSET;
    }

    if (dstAddr < RAMITCM_BASE + RAMITCM_SIZE)
    {
        dstAddr += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if (((dstAddr >= RAMDTCM_BASE) && (dstAddr < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        dstAddr += DCTM_CORE0_TO_DMA_OFFSET;
    }

    if (((uint32_t)nextLLP > RAMITCM_BASE) && ((uint32_t)nextLLP < RAMITCM_BASE + RAMITCM_SIZE))
    {
        nextLLP += ICTM_CORE0_TO_DMA_OFFSET;
    }
    else if ((((uint32_t)nextLLP >= RAMDTCM_BASE) && ((uint32_t)nextLLP < RAMDTCM_BASE + RAMDTCM_SIZE)))
    {
        nextLLP += DCTM_CORE0_TO_DMA_OFFSET;
    }

    lli->SAR = srcAddr;
    lli->DAR = dstAddr;

    if (isLastLLI != true)
    {
        lli->LLP = nextLLP & AHBDMA0_CH_LLP_LOC_Msk;
    }
    else
    {
        srcLLPEnStatus = DISABLE;
        dstLLPEnStatus = DISABLE;
        lli->LLP       = 0U;
    }

    reg = (uint32_t)init->intEn << AHBDMA0_CH_CTLL_INT_EN_Pos |
          (uint32_t)init->srcTrWidth << AHBDMA0_CH_CTLL_SRC_TR_WIDTH_Pos |
          (uint32_t)init->dstTrWidth << AHBDMA0_CH_CTLL_DST_TR_WIDTH_Pos |
          (uint32_t)init->srcAddressInc << AHBDMA0_CH_CTLL_SINC_Pos |
          (uint32_t)init->dstAddressInc << AHBDMA0_CH_CTLL_DINC_Pos |
          (uint32_t)init->srcBurstDataItemsNum << AHBDMA0_CH_CTLL_SRC_MSIZE_Pos |
          (uint32_t)init->dstBurstDataItemsNum << AHBDMA0_CH_CTLL_DEST_MSIZE_Pos |
          (uint32_t)init->srcGatherEn << AHBDMA0_CH_CTLL_SRC_GATHER_EN_Pos |
          (uint32_t)init->dstScatterEn << AHBDMA0_CH_CTLL_DST_SCATTER_EN_Pos |
          (uint32_t)init->tfrType << AHBDMA0_CH_CTLL_TT_FC_Pos |
          (uint32_t)dstLLPEnStatus << AHBDMA0_CH_CTLL_LLP_DST_EN_Pos |
          (uint32_t)srcLLPEnStatus << AHBDMA0_CH_CTLL_LLP_SRC_EN_Pos;
    lli->CTL_L = reg;

    reg = (uint32_t)init->blkTfrSize << AHBDMA0_CH_CTLH_BLOCK_TS_Pos |
          (uint32_t)init->wbDoneEn << AHBDMA0_CH_CTLH_DONE_Pos;
    lli->CTL_H = reg;
}

/**
 * @brief Get default settings for LLI M2M mode
 *
 * @param init  LLI initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size for single block
 * @param srcLLIUpdate  source LLI update
 * @param dstLLIUpdate  destination LLI update
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setLLIDefaultM2M(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate)
{
    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_INCREMENTAL;
    init->dstAddressInc = AHBDMA_INCREMENTAL;

    if ((size >= 1) && (size <= 3))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    }
    else if ((size >= 4) && (size <= 7))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    }
    else if ((size >= 8) && (size <= 15))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_8;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_8;
    }
    else if ((size >= 16) && (size <= 31))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_16;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_16;
    }
    else if ((size >= 32) && (size <= 63))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_32;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_32;
    }
    else if ((size >= 64) && (size <= 127))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_64;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_64;
    }
    else if ((size >= 128) && (size <= 255))
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_128;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_128;
    }
    else
    {
        init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_256;
        init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_256;
    }

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_MEM_TO_MEM;
    init->dstLLPEn     = dstLLIUpdate;
    init->srcLLPEn     = srcLLIUpdate;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = DISABLE;

    return DRV_OK;
}

/**
 * @brief Get default settings for LLI M2P mode
 *
 * @param init  LLI initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size for single block
 * @param srcLLIUpdate  source LLI update
 * @param dstLLIUpdate  destination LLI update
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setLLIDefaultM2P(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate)
{
    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_INCREMENTAL;
    init->dstAddressInc = AHBDMA_FIXED;

    init->srcBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;
    init->dstBurstDataItemsNum = AHBDMA_BURST_DATA_ITEMS_1;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_MEM_TO_PER;
    init->dstLLPEn     = dstLLIUpdate;
    init->srcLLPEn     = srcLLIUpdate;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = ENABLE;

    return DRV_OK;
}

/**
 * @brief Get default settings for LLI P2M mode
 *
 * @param init  LLI initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size for single block
 * @param srcLLIUpdate  source LLI update
 * @param dstLLIUpdate  destination LLI update
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setLLIDefaultP2M(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate)
{
    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_FIXED;
    init->dstAddressInc = AHBDMA_INCREMENTAL;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_PER_TO_MEM;
    init->dstLLPEn     = dstLLIUpdate;
    init->srcLLPEn     = srcLLIUpdate;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = ENABLE;

    return DRV_OK;
}

/**
 * @brief Get default settings for LLI P2P mode
 *
 * @param init  LLI initialized parameter structure
 * @param srcAddress  source peripheral address
 * @param dstAddress  destionation peripheral address
 * @param size  transfer size for single block
 * @param srcLLIUpdate  source LLI update
 * @param dstLLIUpdate  destination LLI update
 * @return DRV_Status
 * DRV_OK: success
 * DRV_PARAM_ERR: Fail because of transfer size is greater than the maximum or is zero
 */
DRV_Status AHBDMA_setLLIDefaultP2P(AHBDMA_LLI_Init_TypeDef *init, uint32_t srcAddress, uint32_t dstAddress,
                                   uint32_t size, ControlStatus srcLLIUpdate, ControlStatus dstLLIUpdate)
{
    if ((size > AHBDMA_MAX_BLOCK_TR_SIZE) || (size == 0U))
    {
        return DRV_PARAM_ERR;
    }

    init->sar = (uint32_t)srcAddress;
    init->dar = (uint32_t)dstAddress;

    init->srcTrWidth = AHBDMA_BITS_8;
    init->dstTrWidth = AHBDMA_BITS_8;

    init->srcAddressInc = AHBDMA_FIXED;
    init->dstAddressInc = AHBDMA_FIXED;

    init->srcGatherEn  = DISABLE;
    init->dstScatterEn = DISABLE;
    init->tfrType      = AHBDMA_PER_TO_PER;
    init->dstLLPEn     = dstLLIUpdate;
    init->srcLLPEn     = srcLLIUpdate;
    init->blkTfrSize   = (uint16_t)size;
    init->wbDoneEn     = ENABLE;

    return DRV_OK;
}

/**
 * @brief Enable AHBDMAx interrupt request for channel [ch]
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @param interruptMasks  DMA interrupt request masks
 */
void AHBDMA_enableChannelInterrupt(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_ITMASK(interruptMasks));

    if ((interruptMasks & AHBDMA_IT_TFR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKTFR, AHBDMA_CH_IT_WE_ENABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_BLOCK_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKBLOCK, AHBDMA_CH_IT_WE_ENABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_SRCTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKSRCTRAN, AHBDMA_CH_IT_WE_ENABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_DSTTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKDSTTRAN, AHBDMA_CH_IT_WE_ENABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_ERR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKERR, AHBDMA_CH_IT_WE_ENABLE(ch));
    }

    SET_BIT(AHBDMAx->CH[ch].CTLL, AHBDMA0_CH_CTLL_INT_EN_Msk);
}

/**
 * @brief Disable AHBDMAx interrupt request for channel [ch]
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel
 * @param interruptMasks  DMA interrupt request masks
 */
void AHBDMA_disableChannelInterrupt(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_ITMASK(interruptMasks));

    if ((interruptMasks & AHBDMA_IT_TFR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKTFR, AHBDMA_CH_IT_WE_DISABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_BLOCK_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKBLOCK, AHBDMA_CH_IT_WE_DISABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_SRCTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKSRCTRAN, AHBDMA_CH_IT_WE_DISABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_DSTTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKDSTTRAN, AHBDMA_CH_IT_WE_DISABLE(ch));
    }
    if ((interruptMasks & AHBDMA_IT_ERR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->MASKERR, AHBDMA_CH_IT_WE_DISABLE(ch));
    }

    CLEAR_BIT(AHBDMAx->CH[ch].CTLL, AHBDMA0_CH_CTLL_INT_EN_Msk);
}

/**
 * @brief Get channels that have transfer complete interrupt request
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * channel ID masks: The channel ID masks in transfer complete interrupt
 */
uint32_t AHBDMA_getTfrInterruptChannelMask(AHBDMA_Type *AHBDMAx)
{
    uint32_t ch;
    uint32_t ch_masks = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (ch = 0; ch < AHBDMA_NUM_CHANNELS; ch++)
    {
        if ((READ_REG(AHBDMAx->STATUSTFR) & BIT_MASK(ch)) != 0)
        {
            ch_masks |= BIT_MASK(ch);
        }
    }
    return ch_masks;
}

/**
 * @brief Get channels that have block transfer complete interrupt request
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * channel ID masks: The channel ID masks in block transfer complete interrupt
 */
uint32_t AHBDMA_getBlockInterruptChannelMask(AHBDMA_Type *AHBDMAx)
{
    uint32_t ch;
    uint32_t ch_masks = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (ch = 0; ch < AHBDMA_NUM_CHANNELS; ch++)
    {
        if ((READ_REG(AHBDMAx->STATUSBLOCK) & BIT_MASK(ch)) != 0)
        {
            ch_masks |= BIT_MASK(ch);
        }
    }
    return ch_masks;
}

/**
 * @brief Get channels that have source transfer complete interrupt request
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * channel ID masks: The channel ID masks in source transfer complete interrupt
 */
uint32_t AHBDMA_getSrctranInterruptChannelMask(AHBDMA_Type *AHBDMAx)
{
    uint32_t ch;
    uint32_t ch_masks = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (ch = 0; ch < AHBDMA_NUM_CHANNELS; ch++)
    {
        if ((READ_REG(AHBDMAx->STATUSSRCTRAN) & BIT_MASK(ch)) != 0)
        {
            ch_masks |= BIT_MASK(ch);
        }
    }
    return ch_masks;
}

/**
 * @brief  Get channels that have destionation transfer complete interrupt request
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * channel ID masks: The channel ID masks in destionation transfer complete interrupt
 */
uint32_t AHBDMA_getDsttranInterruptChannelMask(AHBDMA_Type *AHBDMAx)
{
    uint32_t ch;
    uint32_t ch_masks = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (ch = 0; ch < AHBDMA_NUM_CHANNELS; ch++)
    {
        if ((READ_REG(AHBDMAx->STATUSDSTTRAN) & BIT_MASK(ch)) != 0)
        {
            ch_masks |= BIT_MASK(ch);
        }
    }
    return ch_masks;
}

/**
 * @brief Get channels that have transfer error interrupt request
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @return uint32_t
 * channel ID masks: The channel ID masks in error transfer complete interrupt
 */
uint32_t AHBDMA_getErrInterruptChannelMask(AHBDMA_Type *AHBDMAx)
{
    uint32_t ch;
    uint32_t ch_masks = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    for (ch = 0; ch < AHBDMA_NUM_CHANNELS; ch++)
    {
        if ((READ_REG(AHBDMAx->STATUSERR) & BIT_MASK(ch)) != 0)
        {
            ch_masks |= BIT_MASK(ch);
        }
    }
    return ch_masks;
}

/**
 * @brief Clear AHBDMAx interrupt request for channel [ch]
 *
 * @param AHBDMAx  AHBDMA peripheral address
 * @param ch  AHBDMA channel ID
 * @param interruptMasks  DMA interrupt request masks
 */
void AHBDMA_clearInterruptChannel(AHBDMA_Type *AHBDMAx, uint32_t ch, uint32_t interruptMasks)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_ITMASK(interruptMasks));

    if ((interruptMasks & AHBDMA_IT_TFR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->CLEARTFR, BIT_MASK(ch));
    }
    if ((interruptMasks & AHBDMA_IT_BLOCK_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->CLEARBLOCK, BIT_MASK(ch));
    }
    if ((interruptMasks & AHBDMA_IT_SRCTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->CLEARSRCTRAN, BIT_MASK(ch));
    }
    if ((interruptMasks & AHBDMA_IT_DSTTRAN_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->CLEARDSTTRAN, BIT_MASK(ch));
    }
    if ((interruptMasks & AHBDMA_IT_ERR_MASK) != 0)
    {
        WRITE_REG(AHBDMAx->CLEARERR, BIT_MASK(ch));
    }
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

#define IS_AHBDMA_TEST_ACCESS_VIEW(x) \
        (IS_AHBDMA_PERIPHERAL(x) || \
         ((x) == AHBDMA0_ACC) || ((x) == AHBDMA1_ACC))

#define IS_AHBDMA_TEST_HANDSHAKE_MODE(mode) \
        (((mode) == AHBDMA_TEST_HS_HARDWARE) || \
         ((mode) == AHBDMA_TEST_HS_SOFTWARE))

#define IS_AHBDMA_TEST_HANDSHAKE_POLARITY(polarity) \
        (((polarity) == AHBDMA_TEST_HS_ACTIVE_HIGH) || \
         ((polarity) == AHBDMA_TEST_HS_ACTIVE_LOW))

#define IS_AHBDMA_TEST_SOFTWARE_REQUEST_TYPE(type) \
        (((type) == AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_TRANSFER) || \
         ((type) == AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_TRANSFER) || \
         ((type) == AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_SINGLE) || \
         ((type) == AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_SINGLE) || \
         ((type) == AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_LAST) || \
         ((type) == AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_LAST))

/**
 * @brief Enable selected channels with one atomic CHENREG write.
 */
DRV_Status AHBDMA_testEnableChannelsByMask(AHBDMA_Type *AHBDMAx, uint32_t channelMask)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    if ((channelMask == 0U) ||
        ((channelMask & ~AHBDMA0_CHENREG_CH_EN_Msk) != 0U))
    {
        return DRV_PARAM_ERR;
    }

    WRITE_REG(AHBDMAx->CHENREG,
              channelMask | (channelMask << AHBDMA0_CHENREG_CH_EN_WE_Pos));
    return DRV_OK;
}

/**
 * @brief Read the enabled-channel bits as one CHENREG snapshot.
 */
uint32_t AHBDMA_testGetEnabledChannels(AHBDMA_Type *AHBDMAx)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    return READ_REG(AHBDMAx->CHENREG) & AHBDMA0_CHENREG_CH_EN_Msk;
}

/**
 * @brief Configure endpoint handshake fields while preserving other CFGL bits.
 */
DRV_Status AHBDMA_testConfigureChannelHandshake(
    AHBDMA_Type *AHBDMAx,
    uint32_t ch,
    uint8_t srcHandshakeMode,
    uint8_t dstHandshakeMode,
    uint8_t srcHandshakePolarity,
    uint8_t dstHandshakePolarity)
{
    uint32_t fieldMask;
    uint32_t fieldValue;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_TEST_HANDSHAKE_MODE(srcHandshakeMode));
    assert_param(IS_AHBDMA_TEST_HANDSHAKE_MODE(dstHandshakeMode));
    assert_param(IS_AHBDMA_TEST_HANDSHAKE_POLARITY(srcHandshakePolarity));
    assert_param(IS_AHBDMA_TEST_HANDSHAKE_POLARITY(dstHandshakePolarity));

    if (!IS_AHBDMA_PERIPHERAL(AHBDMAx) ||
        !IS_AHBDMA_CHANNEL(ch) ||
        !IS_AHBDMA_TEST_HANDSHAKE_MODE(srcHandshakeMode) ||
        !IS_AHBDMA_TEST_HANDSHAKE_MODE(dstHandshakeMode) ||
        !IS_AHBDMA_TEST_HANDSHAKE_POLARITY(srcHandshakePolarity) ||
        !IS_AHBDMA_TEST_HANDSHAKE_POLARITY(dstHandshakePolarity))
    {
        return DRV_PARAM_ERR;
    }

    fieldMask = AHBDMA0_CH_CFGL_HS_SEL_SRC_Msk |
                AHBDMA0_CH_CFGL_HS_SEL_DST_Msk |
                AHBDMA0_CH_CFGL_SRC_HS_POL_Msk |
                AHBDMA0_CH_CFGL_DST_HS_POL_Msk;
    fieldValue = ((uint32_t)srcHandshakeMode << AHBDMA0_CH_CFGL_HS_SEL_SRC_Pos) |
                 ((uint32_t)dstHandshakeMode << AHBDMA0_CH_CFGL_HS_SEL_DST_Pos) |
                 ((uint32_t)srcHandshakePolarity << AHBDMA0_CH_CFGL_SRC_HS_POL_Pos) |
                 ((uint32_t)dstHandshakePolarity << AHBDMA0_CH_CFGL_DST_HS_POL_Pos);
    MODIFY_REG(AHBDMAx->CH[ch].CFGL, fieldMask, fieldValue);
    return DRV_OK;
}

/**
 * @brief Assert or clear one named software handshake request.
 */
DRV_Status AHBDMA_testSetSoftwareHandshakeRequest(AHBDMA_Type *AHBDMAx, uint32_t ch,
                                                   uint32_t requestType, ControlStatus status)
{
    uint32_t requestBit;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    assert_param(IS_AHBDMA_TEST_SOFTWARE_REQUEST_TYPE(requestType));
    assert_param(IS_FUNCTIONAL_STATE(status));

    if (!IS_AHBDMA_PERIPHERAL(AHBDMAx) ||
        !IS_AHBDMA_CHANNEL(ch) ||
        !IS_AHBDMA_TEST_SOFTWARE_REQUEST_TYPE(requestType) ||
        !IS_FUNCTIONAL_STATE(status))
    {
        return DRV_PARAM_ERR;
    }

    requestBit = BIT_MASK(ch);
    switch (requestType)
    {
        case AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_TRANSFER:
            WRITE_REG(AHBDMAx->REQSRCREG,
                      (requestBit << AHBDMA0_REQSRCREG_SRC_REQ_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_REQSRCREG_SRC_REQ_Pos) : 0U));
            break;
        case AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_TRANSFER:
            WRITE_REG(AHBDMAx->REQDSTREG,
                      (requestBit << AHBDMA0_REQDSTREG_DST_REQ_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_REQDSTREG_DST_REQ_Pos) : 0U));
            break;
        case AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_SINGLE:
            WRITE_REG(AHBDMAx->SGLRQSRCREG,
                      (requestBit << AHBDMA0_SGLRQSRCREG_SRC_SGLREQ_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_SGLRQSRCREG_SRC_SGLREQ_Pos) : 0U));
            break;
        case AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_SINGLE:
            WRITE_REG(AHBDMAx->SGLRQDSTREG,
                      (requestBit << AHBDMA0_SGLRQDSTREG_DST_SGLREQ_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_SGLRQDSTREG_DST_SGLREQ_Pos) : 0U));
            break;
        case AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_LAST:
            WRITE_REG(AHBDMAx->LSTSRCREG,
                      (requestBit << AHBDMA0_LSTSRCREG_LSTSRC_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_LSTSRCREG_LSTSRC_Pos) : 0U));
            break;
        case AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_LAST:
            WRITE_REG(AHBDMAx->LSTDSTREG,
                      (requestBit << AHBDMA0_LSTDSTREG_LSTDST_WE_Pos) |
                      ((status == ENABLE) ?
                       (requestBit << AHBDMA0_LSTDSTREG_LSTDST_Pos) : 0U));
            break;
        default:
            return DRV_PARAM_ERR;
    }

    return DRV_OK;
}

/**
 * @brief Capture component identification and parameter registers.
 */
DRV_Status AHBDMA_testGetComponentSnapshot(AHBDMA_Type *AHBDMAx,
                                            AHBDMA_TestComponentSnapshot_TypeDef *snapshot)
{
    assert_param(IS_AHBDMA_TEST_ACCESS_VIEW(AHBDMAx));
    if (!IS_AHBDMA_TEST_ACCESS_VIEW(AHBDMAx))
    {
        return DRV_PARAM_ERR;
    }
    if (snapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    snapshot->dmaId = READ_REG(AHBDMAx->DMAIDREG);
    snapshot->componentId = READ_REG(AHBDMAx->DMACOMPSID);
    snapshot->channelParams[0] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH0);
    snapshot->channelParams[1] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH1);
    snapshot->channelParams[2] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH2);
    snapshot->channelParams[3] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH3);
    snapshot->channelParams[4] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH4);
    snapshot->channelParams[5] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH5);
    snapshot->channelParams[6] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH6);
    snapshot->channelParams[7] = READ_REG(AHBDMAx->DMA_COMP_PARAMS_CH7);
    snapshot->multiBlockParams = READ_REG(AHBDMAx->DMA_COMP_PARAMS_MULTI_BLK);
    snapshot->maxBlockSizeParams = READ_REG(AHBDMAx->DMA_COMP_PARAMS_MAX_BLOCK_SIZE);
    return DRV_OK;
}

/**
 * @brief Capture raw, status, mask, and combined interrupt registers.
 */
DRV_Status AHBDMA_testGetInterruptSnapshot(AHBDMA_Type *AHBDMAx,
                                            AHBDMA_TestInterruptSnapshot_TypeDef *snapshot)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    if (!IS_AHBDMA_PERIPHERAL(AHBDMAx))
    {
        return DRV_PARAM_ERR;
    }
    if (snapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }

    snapshot->raw[0] = READ_REG(AHBDMAx->RAWTFR);
    snapshot->raw[1] = READ_REG(AHBDMAx->RAWBLOCK);
    snapshot->raw[2] = READ_REG(AHBDMAx->RAWSRCTRAN);
    snapshot->raw[3] = READ_REG(AHBDMAx->RAWDSTTRAN);
    snapshot->raw[4] = READ_REG(AHBDMAx->RAWERR);
    snapshot->status[0] = READ_REG(AHBDMAx->STATUSTFR);
    snapshot->status[1] = READ_REG(AHBDMAx->STATUSBLOCK);
    snapshot->status[2] = READ_REG(AHBDMAx->STATUSSRCTRAN);
    snapshot->status[3] = READ_REG(AHBDMAx->STATUSDSTTRAN);
    snapshot->status[4] = READ_REG(AHBDMAx->STATUSERR);
    snapshot->mask[0] = READ_REG(AHBDMAx->MASKTFR) & 0xffU;
    snapshot->mask[1] = READ_REG(AHBDMAx->MASKBLOCK) & 0xffU;
    snapshot->mask[2] = READ_REG(AHBDMAx->MASKSRCTRAN) & 0xffU;
    snapshot->mask[3] = READ_REG(AHBDMAx->MASKDSTTRAN) & 0xffU;
    snapshot->mask[4] = READ_REG(AHBDMAx->MASKERR) & 0xffU;
    snapshot->combinedStatus = READ_REG(AHBDMAx->STATUSINT);
    return DRV_OK;
}

/**
 * @brief Capture all channel registers for test diagnostics.
 */
DRV_Status AHBDMA_testGetChannelSnapshot(AHBDMA_Type *AHBDMAx, uint32_t ch,
                                         AHBDMA_TestChannelSnapshot_TypeDef *snapshot)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));
    if (!IS_AHBDMA_PERIPHERAL(AHBDMAx) ||
        (snapshot == NULL) || !IS_AHBDMA_CHANNEL(ch))
    {
        return DRV_PARAM_ERR;
    }

    snapshot->sar = READ_REG(AHBDMAx->CH[ch].SAR);
    snapshot->dar = READ_REG(AHBDMAx->CH[ch].DAR);
    snapshot->llp = READ_REG(AHBDMAx->CH[ch].LLP);
    snapshot->ctlLow = READ_REG(AHBDMAx->CH[ch].CTLL);
    snapshot->ctlHigh = READ_REG(AHBDMAx->CH[ch].CTLH);
    snapshot->cfgLow = READ_REG(AHBDMAx->CH[ch].CFGL);
    snapshot->cfgHigh = READ_REG(AHBDMAx->CH[ch].CFGH);
    snapshot->sourceGather = READ_REG(AHBDMAx->CH[ch].SGR);
    snapshot->destinationScatter = READ_REG(AHBDMAx->CH[ch].DSR);
    /* Test extension owns ET6801 register-field decoding; public layers receive stable semantics. */
    snapshot->sourceBurst =
        (snapshot->ctlLow & AHBDMA0_CH_CTLL_SRC_MSIZE_Msk) >> AHBDMA0_CH_CTLL_SRC_MSIZE_Pos;
    snapshot->destinationBurst =
        (snapshot->ctlLow & AHBDMA0_CH_CTLL_DEST_MSIZE_Msk) >> AHBDMA0_CH_CTLL_DEST_MSIZE_Pos;
    snapshot->blockSize =
        (snapshot->ctlHigh & AHBDMA0_CH_CTLH_BLOCK_TS_Msk) >> AHBDMA0_CH_CTLH_BLOCK_TS_Pos;
    snapshot->fifoMode =
        (snapshot->cfgHigh & AHBDMA0_CH_CFGH_FIFO_MODE_Msk) >> AHBDMA0_CH_CFGH_FIFO_MODE_Pos;
    return DRV_OK;
}

/**
 * @brief Start one channel and return the target-local DWT start cycle.
 *
 * DWT setup is completed before sampling. The sample is taken immediately
 * before AHBDMA_enableChannel() so configuration and protocol overhead are not
 * included in the measured transfer interval.
 */
DRV_Status AHBDMA_testStartChannelTimed(
    AHBDMA_Type *AHBDMAx,
    uint32_t ch,
    uint32_t *startCycles)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(IS_AHBDMA_CHANNEL(ch));

    if (!IS_AHBDMA_PERIPHERAL(AHBDMAx) ||
        !IS_AHBDMA_CHANNEL(ch) || (startCycles == NULL))
    {
        return DRV_PARAM_ERR;
    }
    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0U)
    {
        return DRV_ERROR;
    }

    /* Keep existing DWT state and only enable the trace/cycle-count bits. */
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    *startCycles = DWT->CYCCNT;
    return AHBDMA_enableChannel(AHBDMAx, ch);
}

/**
 * @brief Return elapsed target cycles from a previously captured start.
 *
 * Unsigned subtraction intentionally supports one DWT counter wrap. The
 * bounded DMA performance cases complete well within a second wrap.
 */
DRV_Status AHBDMA_testGetElapsedCycles(
    uint32_t startCycles,
    uint32_t *elapsedCycles)
{
    if (elapsedCycles == NULL)
    {
        return DRV_PARAM_ERR;
    }
    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0U)
    {
        return DRV_ERROR;
    }

    *elapsedCycles = DWT->CYCCNT - startCycles;
    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
