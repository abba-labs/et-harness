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
#include "et6x_can.h"


/**
 * @brief Wrapper register access api
 *
 */
#define CAN_WR_FIELD32(REG, FIELD, VAL)    MODIFY_REG(REG, FIELD ## _Msk, (uint32_t)((VAL) << FIELD ## _Pos))
#define CAN_RD_FIELD32(REG, FIELD)         (READ_BIT(REG, FIELD ## _Msk) >> FIELD ## _Pos)

/**
 * @brief
 *
 */
#define IS_CAN_PERIPH(PERIPH) \
        (((PERIPH) == CAN0) || ((PERIPH) == CAN1) || ((PERIPH) == CAN2))

#define CAN_RWD_WDC_MAX        (0xFFU)
#define CAN_TDCR_TDCF_MAX      (0x7FU)
#define CAN_TDCR_TDCO_MAX      (0x7FU)
#define CAN_TSCC_TCP_MAX       (0xFU)
#define CAN_TOCC_TOP_MAX       (0xFFFFU)
#define CAN_NBTP_NSJW_MAX      (0x7FU)
#define CAN_NBTP_NTSEG2_MAX    (0x7FU)
#define CAN_NBTP_NTSEG1_MAX    (0xFFU)
#define CAN_NBTP_NBRP_MAX      (0x1FFU)
#define CAN_DBTP_DSJW_MAX      (0xFU)
#define CAN_DBTP_DTSEG2_MAX    (0xFU)
#define CAN_DBTP_DTSEG1_MAX    (0x1FU)
#define CAN_DBTP_DBRP_MAX      (0x1FU)
#define CAN_XIDAM_EIDM_MAX     (0x1FFFFFFFU)

#define CAN_CAN_MSG_MEM        (0x0U)


/**
 * @brief  Mask and shift for Tx Buffers elements.
 */
#define CAN_TX_BUFFER_ELEM_ID_SHIFT          (0U)
#define CAN_TX_BUFFER_ELEM_ID_MASK           (0x1FFFFFFFU)
#define CAN_TX_BUFFER_ELEM_RTR_SHIFT         (29U)
#define CAN_TX_BUFFER_ELEM_RTR_MASK          (0x20000000U)
#define CAN_TX_BUFFER_ELEM_XTD_SHIFT         (30U)
#define CAN_TX_BUFFER_ELEM_XTD_MASK          (0x40000000U)
#define CAN_TX_BUFFER_ELEM_ESI_SHIFT         (31U)
#define CAN_TX_BUFFER_ELEM_ESI_MASK          (0x80000000U)
#define CAN_TX_BUFFER_ELEM_DLC_SHIFT         (16U)
#define CAN_TX_BUFFER_ELEM_DLC_MASK          (0x000F0000U)
#define CAN_TX_BUFFER_ELEM_BRS_SHIFT         (20U)
#define CAN_TX_BUFFER_ELEM_BRS_MASK          (0x00100000U)
#define CAN_TX_BUFFER_ELEM_FDF_SHIFT         (21U)
#define CAN_TX_BUFFER_ELEM_FDF_MASK          (0x00200000U)
#define CAN_TX_BUFFER_ELEM_TSCE_SHIFT        (22U)
#define CAN_TX_BUFFER_ELEM_TSCE_MASK         (0x00400000U)
#define CAN_TX_BUFFER_ELEM_EFC_SHIFT         (23U)
#define CAN_TX_BUFFER_ELEM_EFC_MASK          (0x00800000U)
#define CAN_TX_BUFFER_ELEM_MM_SHIFT          (24U)
#define CAN_TX_BUFFER_ELEM_MM_MASK           (0xFF000000U)

/**
 * @brief  Mask and shift for Rx Buffers elements.
 */
#define CAN_RX_BUFFER_ELEM_ID_SHIFT          (0U)
#define CAN_RX_BUFFER_ELEM_ID_MASK           (0x1FFFFFFFU)
#define CAN_RX_BUFFER_ELEM_RTR_SHIFT         (29U)
#define CAN_RX_BUFFER_ELEM_RTR_MASK          (0x20000000U)
#define CAN_RX_BUFFER_ELEM_XTD_SHIFT         (30U)
#define CAN_RX_BUFFER_ELEM_XTD_MASK          (0x40000000U)
#define CAN_RX_BUFFER_ELEM_ESI_SHIFT         (31U)
#define CAN_RX_BUFFER_ELEM_ESI_MASK          (0x80000000U)
#define CAN_RX_BUFFER_ELEM_RXTS_SHIFT        (0U)
#define CAN_RX_BUFFER_ELEM_RXTS_MASK         (0x0000FFFFU)
#define CAN_RX_BUFFER_ELEM_DLC_SHIFT         (16U)
#define CAN_RX_BUFFER_ELEM_DLC_MASK          (0x000F0000U)
#define CAN_RX_BUFFER_ELEM_BRS_SHIFT         (20U)
#define CAN_RX_BUFFER_ELEM_BRS_MASK          (0x00100000U)
#define CAN_RX_BUFFER_ELEM_FDF_SHIFT         (21U)
#define CAN_RX_BUFFER_ELEM_FDF_MASK          (0x00200000U)
#define CAN_RX_BUFFER_ELEM_FIDX_SHIFT        (24U)
#define CAN_RX_BUFFER_ELEM_FIDX_MASK         (0x7F000000U)
#define CAN_RX_BUFFER_ELEM_ANMF_SHIFT        (31U)
#define CAN_RX_BUFFER_ELEM_ANMF_MASK         (0x80000000U)

/**
 * @brief  Mask and shift for Standard Message ID Filter Elements.
 */
#define CAN_STD_ID_FILTER_SFID2_SHIFT        (0U)
#define CAN_STD_ID_FILTER_SFID2_MASK         (0x000003FFU)
#define CAN_STD_ID_FILTER_SFID1_SHIFT        (16U)
#define CAN_STD_ID_FILTER_SFID1_MASK         (0x03FF0000U)
#define CAN_STD_ID_FILTER_SFEC_SHIFT         (27U)
#define CAN_STD_ID_FILTER_SFEC_MASK          (0x38000000U)
#define CAN_STD_ID_FILTER_SFT_SHIFT          (30U)
#define CAN_STD_ID_FILTER_SFT_MASK           (0xC0000000U)

/**
 * @brief  Extended Message ID Filter Element.
 */
#define CAN_EXT_ID_FILTER_EFID2_SHIFT        (0U)
#define CAN_EXT_ID_FILTER_EFID2_MASK         (0x1FFFFFFFU)
#define CAN_EXT_ID_FILTER_EFID1_SHIFT        (0U)
#define CAN_EXT_ID_FILTER_EFID1_MASK         (0x1FFFFFFFU)
#define CAN_EXT_ID_FILTER_EFEC_SHIFT         (29U)
#define CAN_EXT_ID_FILTER_EFEC_MASK          (0xE0000000U)
#define CAN_EXT_ID_FILTER_EFT_SHIFT          (30U)
#define CAN_EXT_ID_FILTER_EFT_MASK           (0xC0000000U)

/**
 * @brief  Mask and shift for Tx Event FIFO elements.
 */
#define CAN_TX_EVENT_FIFO_ELEM_ID_SHIFT      (0U)
#define CAN_TX_EVENT_FIFO_ELEM_ID_MASK       (0x1FFFFFFFU)
#define CAN_TX_EVENT_FIFO_ELEM_RTR_SHIFT     (29U)
#define CAN_TX_EVENT_FIFO_ELEM_RTR_MASK      (0x20000000U)
#define CAN_TX_EVENT_FIFO_ELEM_XTD_SHIFT     (30U)
#define CAN_TX_EVENT_FIFO_ELEM_XTD_MASK      (0x40000000U)
#define CAN_TX_EVENT_FIFO_ELEM_ESI_SHIFT     (31U)
#define CAN_TX_EVENT_FIFO_ELEM_ESI_MASK      (0x80000000U)

#define CAN_TX_EVENT_FIFO_ELEM_TXTS_SHIFT    (0U)
#define CAN_TX_EVENT_FIFO_ELEM_TXTS_MASK     (0x0000FFFFU)
#define CAN_TX_EVENT_FIFO_ELEM_DLC_SHIFT     (16U)
#define CAN_TX_EVENT_FIFO_ELEM_DLC_MASK      (0x000F0000U)
#define CAN_TX_EVENT_FIFO_ELEM_BRS_SHIFT     (20U)
#define CAN_TX_EVENT_FIFO_ELEM_BRS_MASK      (0x00100000U)
#define CAN_TX_EVENT_FIFO_ELEM_FDF_SHIFT     (21U)
#define CAN_TX_EVENT_FIFO_ELEM_FDF_MASK      (0x00200000U)
#define CAN_TX_EVENT_FIFO_ELEM_ET_SHIFT      (22U)
#define CAN_TX_EVENT_FIFO_ELEM_ET_MASK       (0x00C00000U)
#define CAN_TX_EVENT_FIFO_ELEM_MM_SHIFT      (24U)
#define CAN_TX_EVENT_FIFO_ELEM_MM_MASK       (0xFF000000U)


/**
 * @brief CAN TSU timebase prescaler value define
 *
 */
#define CAN_TSU_TBPRE_MIN_VALUE    (1U)   // Min allowed value for the Timebase Prescaler
#define CAN_TSU_TBPRE_MAX_VALUE    (256U) // Max allowed value for the Timebase Prescaler

/* ========================================================================== */
/*                            Global Variables                                */
/* ========================================================================== */

/**
 * @brief  Array that stores Data Size in bytes
 */
static uint32_t dataSize[16] =
{
    0,  1,  2,  3,  4,  5,  6, 7,
    8, 12, 16, 20, 24, 32, 48, 64
};

/**
 * @brief  Array that stores Element Size in words
 */
static uint32_t objSize[8] = { 4, 5, 6, 7, 8, 10, 14, 18 };


static void CAN_writeProtectedRegAccessUnlock(CAN_Type *CANx);
static void CAN_writeProtectedRegAccessLock(CAN_Type *CANx);
static uint32_t CAN_getDataSize(uint32_t dlc);
static void CAN_readMsg(uint32_t baseAddr, uint32_t elemAddr, CAN_RxBufElement *elem);
static void CAN_writeMsg(uint32_t baseAddr, uint32_t elemAddr, const CAN_TxBufElement *elem);

/* ========================================================================== */
/*                          Function Definitions                              */
/* ========================================================================== */

/**
 * @brief This API will return flexible data rate operation status
 *          CAN module.
 *
 * @return uint32_t Returns TRUE if flexible data rate operation
 *                          is enabled. Else returns FALSE.
 */
uint32_t CAN_isFDOpEnable(CAN_Type *CANx)
{
    uint32_t regVal = 0U;

    assert_param(IS_CAN_PERIPH(CANx));

    if (CANx == CAN0)
    {
        regVal = CAN_RD_FIELD32(CAN_MISC0->MISC_STATUS, CAN_MISC0_MISC_STATUS_TTCAN_CCE);
    }
    else
    {
        regVal = CAN_RD_FIELD32(CAN_MISC1->MISC_STATUS, CAN_MISC0_MISC_STATUS_TTCAN_CCE);
    }
    return regVal;
}

/**
 * @brief   This API will set CAN module mode of operation.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   mode            Mode of operation.
 *                          Refer enum #CAN_OperationMode.
 */
void CAN_setOpMode(CAN_Type *CANx, uint32_t mode)
{
    assert_param(IS_CAN_PERIPH(CANx));
    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_INIT, mode);
}

/**
 * @brief   This API will return CAN module mode of operation.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  mode            Mode of operation.
 *                          Refer enum #CAN_OperationMode.
 */
uint32_t CAN_getOpMode(CAN_Type *CANx)
{
    assert_param(IS_CAN_PERIPH(CANx));
    return CAN_RD_FIELD32(CANx->CCCR, CAN0_CCCR_INIT);
}

/**
 * @brief   This API will initialize CAN module.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   initParams     Initialization parameters.
 *                         Refer struct #CAN_InitParams.
 *
 * @return  int32_t        Initialization status.
 */
int32_t CAN_init(CAN_Type *CANx, const CAN_InitParams *initParams)
{
    int32_t  status;
    uint32_t regVal;

    assert_param(IS_CAN_PERIPH(CANx));
    /**/
    CAN_writeProtectedRegAccessUnlock(CANx);

    regVal = READ_REG(CANx->CCCR);

    CAN_WR_FIELD32(regVal, CAN0_CCCR_FDOE, initParams->fdMode);
    CAN_WR_FIELD32(regVal, CAN0_CCCR_BRSE, initParams->brsEnable);
    CAN_WR_FIELD32(regVal, CAN0_CCCR_TXP, initParams->txpEnable);
    CAN_WR_FIELD32(regVal, CAN0_CCCR_EFBI, initParams->efbi);
    CAN_WR_FIELD32(regVal, CAN0_CCCR_PXHD, initParams->pxhddisable);
    CAN_WR_FIELD32(regVal, CAN0_CCCR_DAR, initParams->darEnable);

    WRITE_REG(CANx->CCCR, regVal);

    if ((CAN_TDCR_TDCF_MAX >= initParams->tdcConfig.tdcf) &&
        (CAN_TDCR_TDCO_MAX >= initParams->tdcConfig.tdco) &&
        (CAN_RWD_WDC_MAX >= initParams->wdcPreload))
    {
        /* Configure Transceiver Delay Compensation */
        CAN_WR_FIELD32(CANx->TDCR, CAN0_TDCR_TDCF, initParams->tdcConfig.tdcf);
        CAN_WR_FIELD32(CANx->TDCR, CAN0_TDCR_TDCO, initParams->tdcConfig.tdco);
        /* Configure MSG RAM watchdog counter preload value */
        CAN_WR_FIELD32(CANx->RWD, CAN0_RWD_WDC, initParams->wdcPreload);
        /* Enable/Disable Transceiver Delay Compensation */
        CAN_WR_FIELD32(CANx->DBTP, CAN0_DBTP_TDC, initParams->tdcEnable);

        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    CAN_writeProtectedRegAccessLock(CANx);

    return status;
}

/**
 * @brief   This API will configure CAN module.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   configParams   configuration parameters.
 *                         Refer struct #CAN_ConfigParams.
 *
 * @return  int32_t        Configuration status.
 */
int32_t CAN_config(CAN_Type *CANx, const CAN_ConfigParams *configParams)
{
    int32_t status;

    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);

    /* Configure CAN control registers */
    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_MON, configParams->monEnable);
    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_ASM, configParams->asmEnable);
    /* Configure Global Filter */
    CAN_WR_FIELD32(CANx->GFC, CAN0_GFC_RRFE, configParams->filterConfig.rrfe);
    CAN_WR_FIELD32(CANx->GFC, CAN0_GFC_RRFS, configParams->filterConfig.rrfs);
    CAN_WR_FIELD32(CANx->GFC, CAN0_GFC_ANFE, configParams->filterConfig.anfe);
    CAN_WR_FIELD32(CANx->GFC, CAN0_GFC_ANFS, configParams->filterConfig.anfs);

    if ((CAN_TSCC_TCP_MAX >= configParams->tsPrescalar) &&
        (CAN_TOCC_TOP_MAX >= configParams->timeoutPreload))
    {
        /* Configure Time-stamp counter */
        CAN_WR_FIELD32(CANx->TSCC, CAN0_TSCC_TSS, configParams->tsSelect);
        CAN_WR_FIELD32(CANx->TSCC, CAN0_TSCC_TCP, (configParams->tsPrescalar - 1U));
        /* Configure Time-out counter */
        CAN_WR_FIELD32(CANx->TOCC, CAN0_TOCC_TOS, configParams->timeoutSelect);
        CAN_WR_FIELD32(CANx->TOCC, CAN0_TOCC_TOP, configParams->timeoutPreload);
        /* Enable Time-out counter */
        CAN_WR_FIELD32(CANx->TOCC, CAN0_TOCC_ETOC, configParams->timeoutCntEnable);
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }

    CAN_writeProtectedRegAccessLock(CANx);

    return status;
}

/**
 * @brief   This API will configure CAN ECC.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   configParams   configuration parameters.
 *                         Refer struct #CAN_ConfigParams.
 *
 */
void CAN_eccConfig(CAN_Type *CANx, const CAN_ECCConfigParams *configParams)
{
    assert_param(IS_CAN_PERIPH(CANx));

    MODIFY_REG(SYSC->ECCEN, SYSC_ECCEN_SYSC_MTTCAN_ECC_EN_Msk,
               (uint32_t)(configParams->enable << SYSC_ECCEN_SYSC_MTTCAN_ECC_EN_Pos));
    if (CANx == CAN0)
    {
        MODIFY_REG(CAN_MISC0->MISC_CTRL, CAN_MISC0_MISC_CTRL_TTCAN_DIS_MORD_Msk,
                   (uint32_t)(configParams->enableRdModWr << CAN_MISC0_MISC_CTRL_TTCAN_DIS_MORD_Pos));
    }
    else
    {
        MODIFY_REG(CAN_MISC1->MISC_CTRL, CAN_MISC0_MISC_CTRL_TTCAN_DIS_MORD_Msk,
                   (uint32_t)(configParams->enableRdModWr << CAN_MISC0_MISC_CTRL_TTCAN_DIS_MORD_Pos));
    }
}

/**
 * @brief
 *
 * @param CANx
 * @param configParams
 * @return int32_t
 */
int32_t CAN_setBitTime(CAN_Type *CANx, const CAN_BitTimingParams *configParams)
{
    int32_t status;

    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);

    if ((CAN_NBTP_NSJW_MAX >= configParams->nomSynchJumpWidth) &&
        (CAN_NBTP_NTSEG2_MAX >= configParams->nomTimeSeg2) &&
        (CAN_NBTP_NTSEG1_MAX >= configParams->nomTimeSeg1) &&
        (CAN_NBTP_NBRP_MAX >= configParams->nomRatePrescalar))
    {
        CAN_WR_FIELD32(CANx->NBTP, CAN0_NBTP_NSJW, configParams->nomSynchJumpWidth);
        CAN_WR_FIELD32(CANx->NBTP, CAN0_NBTP_NTSEG2, configParams->nomTimeSeg2);
        CAN_WR_FIELD32(CANx->NBTP, CAN0_NBTP_NTSEG1, configParams->nomTimeSeg1);
        CAN_WR_FIELD32(CANx->NBTP, CAN0_NBTP_NBRP, configParams->nomRatePrescalar);

        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    if (DRV_OK == status)
    {
        if ((CAN_DBTP_DSJW_MAX >= configParams->dataSynchJumpWidth) &&
            (CAN_DBTP_DTSEG2_MAX >= configParams->dataTimeSeg2) &&
            (CAN_DBTP_DTSEG1_MAX >= configParams->dataTimeSeg1) &&
            (CAN_DBTP_DBRP_MAX >= configParams->dataRatePrescalar))
        {
            CAN_WR_FIELD32(CANx->DBTP, CAN0_DBTP_DSJW, configParams->dataSynchJumpWidth);
            CAN_WR_FIELD32(CANx->DBTP, CAN0_DBTP_DTSEG2, configParams->dataTimeSeg2);
            CAN_WR_FIELD32(CANx->DBTP, CAN0_DBTP_DTSEG1, configParams->dataTimeSeg1);
            CAN_WR_FIELD32(CANx->DBTP, CAN0_DBTP_DBRP, configParams->dataRatePrescalar);
            status = DRV_OK;
        }
        else
        {
            status = DRV_ERROR;
        }
    }

    CAN_writeProtectedRegAccessLock(CANx);
    return status;
}

/**
 * @brief   This API will configure Different sections of Message RAM.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   msgRAMConfigParams
 *                         Message RAM Configuration parameters.
 *                         Refer struct #CAN_MsgRAMConfigParams.
 *
 * @return  int32_t        Configuration Status.
 */
int32_t CAN_msgRAMConfig(CAN_Type *CANx, const CAN_MsgRAMConfigParams *msgRAMConfigParams)
{
    int32_t  status;
    uint32_t elemNum = 0U;

    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);

    /* Configure Message Filters section */
    if (0U != msgRAMConfigParams->lss)
    {
        CAN_WR_FIELD32(CANx->SIDFC,
                       CAN0_SIDFC_FLSSA,
                       (msgRAMConfigParams->flssa >> 2U));
        CAN_WR_FIELD32(CANx->SIDFC,
                       CAN0_SIDFC_LSS,
                       msgRAMConfigParams->lss);
    }
    if (0U != msgRAMConfigParams->lse)
    {
        CAN_WR_FIELD32(CANx->XIDFC,
                       CAN0_XIDFC_FLESA,
                       (msgRAMConfigParams->flesa >> 2U));
        CAN_WR_FIELD32(CANx->XIDFC,
                       CAN0_XIDFC_LSE,
                       msgRAMConfigParams->lse);
    }
    /* Configure Rx FIFO 0 section */
    if (0U != msgRAMConfigParams->rxFIFO0size)
    {
        CAN_WR_FIELD32(CANx->RXF0C,
                       CAN0_RXF0C_F0SA,
                       (msgRAMConfigParams->rxFIFO0startAddr >> 2U));
        CAN_WR_FIELD32(CANx->RXF0C,
                       CAN0_RXF0C_F0S,
                       msgRAMConfigParams->rxFIFO0size);
        CAN_WR_FIELD32(CANx->RXF0C,
                       CAN0_RXF0C_F0WM,
                       msgRAMConfigParams->rxFIFO0waterMark);
        CAN_WR_FIELD32(CANx->RXF0C,
                       CAN0_RXF0C_F0OM,
                       msgRAMConfigParams->rxFIFO0OpMode);
        /* Configure Rx FIFO0 elements size */
        CAN_WR_FIELD32(CANx->RXESC,
                       CAN0_RXESC_F0DS,
                       msgRAMConfigParams->rxFIFO0ElemSize);
    }
    /* Configure Rx FIFO 1 section */
    if (0U != msgRAMConfigParams->rxFIFO1size)
    {
        CAN_WR_FIELD32(CANx->RXF1C,
                       CAN0_RXF1C_F1SA,
                       (msgRAMConfigParams->rxFIFO1startAddr >> 2U));
        CAN_WR_FIELD32(CANx->RXF1C,
                       CAN0_RXF1C_F1S,
                       msgRAMConfigParams->rxFIFO1size);
        CAN_WR_FIELD32(CANx->RXF1C,
                       CAN0_RXF1C_F1WM,
                       msgRAMConfigParams->rxFIFO1waterMark);
        CAN_WR_FIELD32(CANx->RXF1C,
                       CAN0_RXF1C_F1OM,
                       msgRAMConfigParams->rxFIFO1OpMode);
        /* Configure Rx FIFO1 elements size */
        CAN_WR_FIELD32(CANx->RXESC,
                       CAN0_RXESC_F1DS,
                       msgRAMConfigParams->rxFIFO1ElemSize);
    }
    /* Configure Rx Buffer Start Address */
    CAN_WR_FIELD32(CANx->RXBC,
                   CAN0_RXBC_RBSA,
                   (msgRAMConfigParams->rxBufStartAddr >> 2U));
    /* Configure Rx Buffer elements size */
    CAN_WR_FIELD32(CANx->RXESC,
                   CAN0_RXESC_RBDS,
                   msgRAMConfigParams->rxBufElemSize);
    /* Configure Tx Event FIFO section */
    if (0U != msgRAMConfigParams->txEventFIFOSize)
    {
        CAN_WR_FIELD32(CANx->TXEFC,
                       CAN0_TXEFC_EFSA,
                       (msgRAMConfigParams->txEventFIFOStartAddr >> 2U));
        CAN_WR_FIELD32(CANx->TXEFC,
                       CAN0_TXEFC_EFS,
                       msgRAMConfigParams->txEventFIFOSize);
        CAN_WR_FIELD32(CANx->TXEFC,
                       CAN0_TXEFC_EFWM,
                       msgRAMConfigParams->txEventFIFOWaterMark);
    }
    /* Configure Tx Buffer and FIFO/Q section */
    elemNum = msgRAMConfigParams->txBufNum + msgRAMConfigParams->txFIFOSize;
    if ((CAN_TX_BUFFER_MAX >= elemNum) &&
        ((0U != msgRAMConfigParams->txBufNum) ||
         (0U != msgRAMConfigParams->txFIFOSize)))
    {
        CAN_WR_FIELD32(CANx->TXBC,
                       CAN0_TXBC_TBSA,
                       (msgRAMConfigParams->txStartAddr >> 2U));
        CAN_WR_FIELD32(CANx->TXBC,
                       CAN0_TXBC_NDTB,
                       msgRAMConfigParams->txBufNum);
        CAN_WR_FIELD32(CANx->TXBC,
                       CAN0_TXBC_TFQS,
                       msgRAMConfigParams->txFIFOSize);
        CAN_WR_FIELD32(CANx->TXBC,
                       CAN0_TXBC_TFQM,
                       msgRAMConfigParams->txBufMode);
        /* Configure Tx Buffer/FIFO0/FIFO1 elements size */
        CAN_WR_FIELD32(CANx->TXESC,
                       CAN0_TXESC_TBDS,
                       msgRAMConfigParams->txBufElemSize);
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }

    CAN_writeProtectedRegAccessLock(CANx);

    return status;
}

/**
 * @brief   This API will configure Extended ID AND Mask.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   idMask         Configuration parameters for CAN Extended Id mask.
 *                         This value is 29 bit wide.
 *
 * @return  int32_t        Extended ID AND Mask configuration status.
 */
int32_t CAN_setExtIDAndMask(CAN_Type *CANx, uint32_t idMask)
{
    int32_t status;

    assert_param(IS_CAN_PERIPH(CANx));

    if (CAN_XIDAM_EIDM_MAX >= idMask)
    {
        CAN_writeProtectedRegAccessUnlock(CANx);

        CAN_WR_FIELD32(CANx->XIDAM,
                       CAN0_XIDAM_EIDM,
                       idMask);

        CAN_writeProtectedRegAccessLock(CANx);
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    return status;
}

/**
 * @brief   This API is used to write Tx message to message RAM.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   memType         Part of message ram to which given message to write.
 *                          Refer enum #CAN_MemType.
 * @param   bufNum          Buffer  number where message to write.
 *                          This parameter will ignored if memType is FIFO/Q.
 * @param   elem            Message Object.
 *                          Refer struct #CAN_TxBufElement.
 */
void CAN_writeMsgRam(CAN_Type               *CANx,
                     uint32_t               memType,
                     uint32_t               bufNum,
                     const CAN_TxBufElement *elem)
{
    uint32_t startAddr = 0U, elemSize = 0U, elemAddr = 0U;
    uint32_t idx = 0U, enableMod = 0U;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if ((uint32_t)CAN_MEM_TYPE_BUF == memType)
    {
        idx       = bufNum;
        enableMod = 1U;
    }
    if ((uint32_t)CAN_MEM_TYPE_FIFO == memType)
    {
        idx       = CAN_RD_FIELD32(CANx->TXFQS, CAN0_TXFQS_TFQPI);
        enableMod = 1U;
    }
    if (1U == enableMod)
    {
        startAddr = CAN_RD_FIELD32(CANx->TXBC,
                                   CAN0_TXBC_TBSA);
        elemSize = CAN_RD_FIELD32(CANx->TXESC,
                                  CAN0_TXESC_TBDS);
        startAddr = (uint32_t)(startAddr << 2U);
        elemSize  = CAN_getMsgObjSize(elemSize);
        elemSize *= 4U;
        elemAddr  = startAddr + (elemSize * idx);
        elemAddr += CAN_CAN_MSG_MEM;
        CAN_writeMsg((uint32_t)CANx, elemAddr, elem);
    }
}

/**
 * @brief This API will set Tx Buffer Add Request
 *
 * @param CANx Pointer to the CAN peripheral.
 * @param bufNum Tx Buffer number for which request is to be added.
 *
 * @return DRV_OK if the message was successfully added to the buffer.
 * @return DRV_ERROR if the buffer number is invalid.
 *
 * @note The function assumes that the CAN peripheral is already initialized
 * and the transmit buffer is not full.
 *
 * @note The function also assumes that the CCE bit in the TXBAR register is '0'
 * and does not need to be reverted.
 */
int32_t CAN_txBufAddReq(CAN_Type *CANx, uint32_t bufNum)
{
    int32_t  status;
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (CAN_TX_BUFFER_MAX > bufNum)
    {
        regVal  = READ_REG(CANx->TXBAR);
        regVal |= ((uint32_t)1U << bufNum);

        // For writing to TXBAR CCE bit should be '0'. This need not be
        // reverted because for other qualified writes this is locked state
        // and can't be written.
        CAN_writeProtectedRegAccessLock(CANx);
        WRITE_REG(CANx->TXBAR, regVal);

        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    return status;
}

/**
 * @brief This API get New Data Message Status.
 *
 * @param CANx  Pointer to the CAN peripheral.
 * @param newDataStatus  Rx Buffer new data status.
 */
void CAN_getNewDataStatus(CAN_Type            *CANx,
                          CAN_RxNewDataStatus *newDataStatus)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    newDataStatus->statusLow  = READ_REG(CANx->NDAT1);
    newDataStatus->statusHigh = READ_REG(CANx->NDAT2);
}

/**
 * @brief   This API clear New Data Message Status.
 *
 * @param   CANx            Pointer to the CAN peripheral.
 * @param   newDataStatus
 *                          Rx Buffer new data status.
 *                          Refer struct #CAN_RxNewDataStatus.
 */
void CAN_clearNewDataStatus(CAN_Type                  *CANx,
                            const CAN_RxNewDataStatus *newDataStatus)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    WRITE_REG(CANx->NDAT1, newDataStatus->statusLow);
    WRITE_REG(CANx->NDAT2, newDataStatus->statusHigh);
}

/**
 * @brief   This API is used to read received message from Message RAM.
 *
 * @param   CANx            Pointer to the CAN peripheral.
 * @param   memType         Part of message ram to which given message to write.
 *                          Refer enum #CAN_MemType.
 * @param   bufNum          Buffer  number from where message is to read.
 *                          This parameter will ignored if memType is FIFO/Q.
 *  @param  fifoNum         FIFOs number from where message is to read.
 *                          Refer enum #CAN_RxFIFONum.
 *                          This parameter will ignored if memType is buffer.
 * @param   elem            Message Object.
 *                          Refer struct #CAN_RxBufElement.
 */
void CAN_readMsgRam(CAN_Type         *CANx,
                    uint32_t         memType,
                    uint32_t         bufNum,
                    uint32_t         fifoNum,
                    CAN_RxBufElement *elem)
{
    uint32_t startAddr = 0U, elemSize = 0U, elemAddr = 0U;
    uint32_t enableMod = 0U, idx = 0U;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if ((uint32_t)CAN_MEM_TYPE_BUF == memType)
    {
        startAddr = CAN_RD_FIELD32(CANx->RXBC,
                                   CAN0_RXBC_RBSA);
        elemSize = CAN_RD_FIELD32(CANx->RXESC,
                                  CAN0_RXESC_RBDS);
        idx       = bufNum;
        enableMod = 1U;
    }
    if ((uint32_t)CAN_MEM_TYPE_FIFO == memType)
    {
        switch (fifoNum)
        {
        case CAN_RX_FIFO_NUM_0:
            startAddr = CAN_RD_FIELD32(CANx->RXF0C,
                                       CAN0_RXF0C_F0SA);
            elemSize = CAN_RD_FIELD32(CANx->RXESC,
                                      CAN0_RXESC_F0DS);
            idx = CAN_RD_FIELD32(CANx->RXF0S,
                                 CAN0_RXF0S_F0GI);
            enableMod = 1U;
            break;

        case CAN_RX_FIFO_NUM_1:
            startAddr = CAN_RD_FIELD32(CANx->RXF1C,
                                       CAN0_RXF1C_F1SA);
            elemSize = CAN_RD_FIELD32(CANx->RXESC,
                                      CAN0_RXESC_F1DS);
            idx = CAN_RD_FIELD32(CANx->RXF1S,
                                 CAN0_RXF1S_F1GI);
            enableMod = 1U;
            break;

        default:
            /* Invalid option */
            break;
        }
    }
    if (1U == enableMod)
    {
        startAddr = (uint32_t)(startAddr << 2U);
        elemSize  = CAN_getMsgObjSize(elemSize);
        elemSize *= 4U;
        elemAddr  = startAddr + (elemSize * idx);
        elemAddr += CAN_CAN_MSG_MEM;
        CAN_readMsg((uint32_t)CANx, elemAddr, elem);
    }
}

/**
 * @brief   This API will read the High Priority message object from Message RAM.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   elem           Message Object.
 *                         Refer struct #CAN_RxBufElement.
 *
 */
void CAN_readHighPriorityMsgRam(CAN_Type *CANx, CAN_RxBufElement *elem)
{
    CAN_HighPriorityMsgInfo hpm;
    uint32_t                startAddr = 0U, elemSize = 0U, elemAddr = 0U;
    uint32_t                enableMod = 0U, idx = 0U;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_getHighPriorityMsgStatus(CANx, &hpm);

    switch ((hpm.msi) % 2U)
    {
    case CAN_RX_FIFO_NUM_0:
        startAddr = CAN_RD_FIELD32(CANx->RXF0C,
                                   CAN0_RXF0C_F0SA);
        elemSize = CAN_RD_FIELD32(CANx->RXESC,
                                  CAN0_RXESC_F0DS);
        enableMod = 1U;
        break;

    case CAN_RX_FIFO_NUM_1:
        startAddr = CAN_RD_FIELD32(CANx->RXF1C,
                                   CAN0_RXF1C_F1SA);
        elemSize = CAN_RD_FIELD32(CANx->RXESC,
                                  CAN0_RXESC_F1DS);
        enableMod = 1U;
        break;

    default:
        /* Invalid option */
        break;
    }
    if (1U == enableMod)
    {
        idx       = hpm.bufIdx;
        startAddr = (uint32_t)(startAddr << 2U);
        elemSize  = CAN_getMsgObjSize(elemSize);
        elemSize *= 4U;
        elemAddr  = startAddr + (elemSize * idx);
        elemAddr += CAN_CAN_MSG_MEM;
        CAN_readMsg((uint32_t)CANx, elemAddr, elem);
    }
}

/**
 * @brief   This API is used to read from Tx Event FIFO.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   txEventElem     Tx Event FIFO Message Object.
 *                          Refer struct #CAN_TxEventFIFOElement.
 *
 */
void CAN_readTxEventFIFO(CAN_Type               *CANx,
                         CAN_TxEventFIFOElement *txEventElem)
{
    uint32_t startAddr = 0U, elemSize = 0U, elemAddr = 0U, baseAddr = 0U;
    uint32_t idx = 0U, regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    baseAddr = (uint32_t)CANx - 0x4000U;

    startAddr = CAN_RD_FIELD32(CANx->TXEFC,
                               CAN0_TXEFC_EFSA);
    elemSize = CAN_TX_EVENT_FIFO_SIZE_WORDS;
    idx      = CAN_RD_FIELD32(CANx->TXEFS,
                              CAN0_TXEFS_EFGI);

    startAddr = (uint32_t)(startAddr << 2U);
    elemSize *= 4U;
    elemAddr  = startAddr + (elemSize * idx);
    elemAddr += CAN_CAN_MSG_MEM;

    regVal          = READ_REG(REG32(baseAddr + elemAddr));
    txEventElem->id = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_ID_MASK)
                                 >> CAN_TX_EVENT_FIFO_ELEM_ID_SHIFT);
    txEventElem->rtr = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_RTR_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_RTR_SHIFT);
    txEventElem->xtd = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_XTD_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_XTD_SHIFT);
    txEventElem->esi = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_ESI_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_ESI_SHIFT);
    elemAddr         += 4U;
    regVal            = READ_REG(REG32(baseAddr + elemAddr));
    txEventElem->txts = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_TXTS_MASK)
                                   >> CAN_TX_EVENT_FIFO_ELEM_TXTS_SHIFT);
    txEventElem->dlc = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_DLC_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_DLC_SHIFT);
    txEventElem->brs = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_BRS_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_BRS_SHIFT);
    txEventElem->fdf = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_FDF_MASK)
                                  >> CAN_TX_EVENT_FIFO_ELEM_FDF_SHIFT);
    txEventElem->et = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_ET_MASK)
                                 >> CAN_TX_EVENT_FIFO_ELEM_ET_SHIFT);
    txEventElem->mm = (uint32_t)((regVal & CAN_TX_EVENT_FIFO_ELEM_MM_MASK)
                                 >> CAN_TX_EVENT_FIFO_ELEM_MM_SHIFT);
}

/**
 * @brief   This API is used to add Extended Message ID Filter Element.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   filtNum        Filter  number.
 * @param   elem           Filter Object.
 *                         Refer struct #CAN_ExtMsgIDFilterElement.
 *
 */
void CAN_addStdMsgIDFilter(CAN_Type                        *CANx,
                           uint32_t                        filtNum,
                           const CAN_StdMsgIDFilterElement *elem)
{
    uint32_t startAddr, elemAddr, regVal, totalFilt, baseAddr;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    baseAddr = (uint32_t)CANx - 0x4000U;
    //
    // Check that the filter number does not exceed the number
    // of standard filters set during initialization
    //
    totalFilt = CAN_RD_FIELD32(CANx->SIDFC,
                               CAN0_SIDFC_LSS);
    assert_param(filtNum <= totalFilt);

    startAddr = CAN_RD_FIELD32(CANx->SIDFC,
                               CAN0_SIDFC_FLSSA);
    startAddr = (uint32_t)(startAddr << 2U);
    elemAddr  = startAddr + (filtNum * CAN_STD_ID_FILTER_SIZE_WORDS * 4U);
    elemAddr += CAN_CAN_MSG_MEM;

    regVal  = 0U;
    regVal |= (uint32_t)(elem->sfid2 << CAN_STD_ID_FILTER_SFID2_SHIFT);
    regVal |= (uint32_t)(elem->sfid1 << CAN_STD_ID_FILTER_SFID1_SHIFT);
    regVal |= (uint32_t)(elem->sfec << CAN_STD_ID_FILTER_SFEC_SHIFT);
    regVal |= (uint32_t)(elem->sft << CAN_STD_ID_FILTER_SFT_SHIFT);
    WRITE_REG(REG32(baseAddr + elemAddr), regVal);
}

/**
 * @brief   This API is used to add Extended Message ID Filter Element.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   filtNum        Filter  number.
 * @param   elem           Filter Object.
 *                         Refer struct #CAN_ExtMsgIDFilterElement.
 *
 */
void CAN_addExtMsgIDFilter(CAN_Type                        *CANx,
                           uint32_t                        filtNum,
                           const CAN_ExtMsgIDFilterElement *elem)
{
    uint32_t startAddr, elemAddr, regVal, totalFilt, baseAddr;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));
    baseAddr = (uint32_t)CANx - 0x4000U;
    //
    // Check that the filter number does not exceed the number
    // of extended filters set during initialization
    //
    totalFilt = CAN_RD_FIELD32(CANx->XIDFC,
                               CAN0_XIDFC_LSE);
    assert_param(filtNum <= totalFilt);

    startAddr = CAN_RD_FIELD32(CANx->XIDFC,
                               CAN0_XIDFC_FLESA);
    startAddr = (uint32_t)(startAddr << 2U);
    elemAddr  = startAddr + (filtNum * CAN_EXT_ID_FILTER_SIZE_WORDS * 4U);
    elemAddr += CAN_CAN_MSG_MEM;

    regVal  = 0U;
    regVal |= (uint32_t)(elem->efid1 << CAN_EXT_ID_FILTER_EFID1_SHIFT);
    regVal |= (uint32_t)(elem->efec << CAN_EXT_ID_FILTER_EFEC_SHIFT);
    WRITE_REG(REG32(baseAddr + elemAddr), regVal);

    elemAddr += 4U;
    regVal    = 0U;
    regVal   |= (uint32_t)(elem->efid2 << CAN_EXT_ID_FILTER_EFID2_SHIFT);
    regVal   |= (uint32_t)(elem->eft << CAN_EXT_ID_FILTER_EFT_SHIFT);
    WRITE_REG(REG32(baseAddr + elemAddr), regVal);
}

/**
 * @brief   This API will enable/disable Loop Back Test Mode for CAN module.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   lpbkMode       Loopback mode for CAN.
 *                         @ref CAN_LpbkMode.
 * @param   enable         Loop Back Mode is enabled if it is TRUE.
 *                         Loop Back Mode is disabled  if it is FALSE.
 *
 * @note    This API can be called only when CAN module is in Software
 *          Initialization mode of operation.
 */
void CAN_enbaleLpbkMode(CAN_Type *CANx,
                        uint32_t lpbkMode,
                        uint32_t enable)
{
    CAN_writeProtectedRegAccessUnlock(CANx);

    // Check the arguments.
    assert_param(IS_CAN_PERIPH(CANx));

    if (1 == enable)
    {
        CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_TEST, 0x1U);
        CAN_WR_FIELD32(CANx->TEST,
                       CAN0_TEST_LBCK,
                       enable);
        if ((uint32_t)CAN_LPBK_MODE_INTERNAL == lpbkMode)
        {
            CAN_WR_FIELD32(CANx->CCCR,
                           CAN0_CCCR_MON,
                           0x1U);
        }
    }
    else
    {
        CAN_WR_FIELD32(CANx->TEST,
                       CAN0_TEST_LBCK,
                       enable);
        CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_TEST, 0x0U);
        if ((uint32_t)CAN_LPBK_MODE_INTERNAL == lpbkMode)
        {
            CAN_WR_FIELD32(CANx->CCCR,
                           CAN0_CCCR_MON,
                           0x0U);
        }
    }
    CAN_writeProtectedRegAccessLock(CANx);
}

/**
 * @brief   This API will return error counter status for CAN module.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   errCounter     Error Counter Status.
 *                         Refer struct #CAN_ErrCntStatus.
 *
 */
void CAN_getErrCounters(CAN_Type         *CANx,
                        CAN_ErrCntStatus *errCounter)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    errCounter->transErrLogCnt = CAN_RD_FIELD32(CANx->ECR,
                                                CAN0_ECR_TEC);
    errCounter->recErrCnt = CAN_RD_FIELD32(CANx->ECR,
                                           CAN0_ECR_REC);
    errCounter->rpStatus = CAN_RD_FIELD32(CANx->ECR,
                                          CAN0_ECR_RP);
    errCounter->canErrLogCnt = CAN_RD_FIELD32(CANx->ECR,
                                              CAN0_ECR_CEL);
}

/**
 * @brief   This API will return protocol status for CAN module.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   protStatus     Protocol Status.
 *                         Refer struct #CAN_ProtocolStatus.
 *
 */
void CAN_getProtocolStatus(CAN_Type           *CANx,
                           CAN_ProtocolStatus *protStatus)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    regVal = READ_REG(CANx->PSR);
    protStatus->lastErrCode   = CAN_RD_FIELD32(regVal, CAN0_PSR_LEC);
    protStatus->act           = CAN_RD_FIELD32(regVal, CAN0_PSR_ACT);
    protStatus->errPassive    = CAN_RD_FIELD32(regVal, CAN0_PSR_EP);
    protStatus->warningStatus = CAN_RD_FIELD32(regVal, CAN0_PSR_EW);
    protStatus->busOffStatus  = CAN_RD_FIELD32(regVal, CAN0_PSR_BO);
    protStatus->dlec          = CAN_RD_FIELD32(regVal, CAN0_PSR_DLEC);
    protStatus->resi          = CAN_RD_FIELD32(regVal, CAN0_PSR_RESI);
    protStatus->rbrs          = CAN_RD_FIELD32(regVal, CAN0_PSR_RBRS);
    protStatus->rfdf          = CAN_RD_FIELD32(regVal, CAN0_PSR_RFDF);
    protStatus->pxe           = CAN_RD_FIELD32(regVal, CAN0_PSR_PXE);
    protStatus->tdcv          = CAN_RD_FIELD32(regVal, CAN0_PSR_TDCV);
}

/**
 * @brief   This API is used to enable/disable interrupts.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   intrMask       Interrupts to enable.
 *                         Refer enum #CAN_IntrSrc.
 * @param   enable         Interrupt is enabled if it is TRUE.
 *                         Interrupt is disabled  if it is FALSE.
 */
void CAN_enableIntr(CAN_Type *CANx, uint32_t intrMask, uint32_t enable)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (1 == enable)
    {
        regVal  = READ_REG(CANx->IE);
        regVal |= intrMask;
        WRITE_REG(CANx->IE, regVal);
    }
    else
    {
        regVal  = READ_REG(CANx->IE);
        regVal &= ~intrMask;
        WRITE_REG(CANx->IE, regVal);
    }
}

/**
 * @brief   This API is used to select interrupt line.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   intrMask       Interrupt Number for which interrupt
 *                         line is to be selected. Refer enum #CAN_IntrSrc.
 * @param   lineNum        Interrupt Line to select.
 *                         Refer enum #CAN_IntrLineNum,
 */
void CAN_selectIntrLine(CAN_Type *CANx,
                        uint32_t intrMask,
                        uint32_t lineNum)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if ((uint32_t)CAN_INTR_LINE_NUM_0 == lineNum)
    {
        regVal  = READ_REG(CANx->ILS);
        regVal &= ~intrMask;
        WRITE_REG(CANx->ILS, regVal);
    }
    else
    {
        regVal  = READ_REG(CANx->ILS);
        regVal |= intrMask;
        WRITE_REG(CANx->ILS, regVal);
    }
}

/**
 * @brief   This API is used to get interrupt line selected for each interrupt.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  uint32_t       Interrupt Line Select Status.
 */
uint32_t CAN_getIntrLineSelectStatus(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(READ_REG(CANx->ILS));
}

/**
 * @brief   This API is used to enable/disable selected interrupt line.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   lineNum        Interrupt Line to select.
 *                         Refer enum #CAN_IntrLineNum,
 * @param   enable         Interrupt Line is enabled if it is 1.
 *                         Interrupt Line is disabled  if it is 0.
 *
 */
void CAN_enableIntrLine(CAN_Type *CANx,
                        uint32_t lineNum,
                        uint32_t enable)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    lineNum &= CAN_INTR_LINE_EN_MASK;
    regVal   = READ_REG(CANx->ILE);
    regVal  &= ~((uint32_t)0x1U << lineNum);
    regVal  |= (uint32_t)(enable << lineNum);
    WRITE_REG(CANx->ILE, regVal);
}

/**
 * @brief   This API will return interrupt status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  uint32_t       Interrupt Status.
 */
uint32_t CAN_getIntrStatus(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(READ_REG(CANx->IR));
}

/**
 * @brief   This API is used to clear the interrupt status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   intrMask       Interrupts to clear status.
 *
 * @return  None.
 */
void CAN_clearIntrStatus(CAN_Type *CANx, uint32_t intrMask)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    WRITE_REG(CANx->IR, intrMask);
}

/**
 * @brief   This API will return High Priority Message Status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   hpm            High Priority Message Status.
 *                         Refer struct #CAN_HighPriorityMsgInfo.
 *
 */
void CAN_getHighPriorityMsgStatus(CAN_Type                *CANx,
                                  CAN_HighPriorityMsgInfo *hpm)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    hpm->bufIdx = CAN_RD_FIELD32(CANx->HPMS,
                                 CAN0_HPMS_BIDX);
    hpm->msi = CAN_RD_FIELD32(CANx->HPMS,
                              CAN0_HPMS_MSI);
    hpm->filterIdx = CAN_RD_FIELD32(CANx->HPMS,
                                    CAN0_HPMS_FIDX);
    hpm->filterList = CAN_RD_FIELD32(CANx->HPMS,
                                     CAN0_HPMS_FLST);
}

/**
 * @brief   This API will Rx FIFO status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   fifoStatus     Rx FIFO Status.
 *                         Refer struct #CAN_RxFIFOStatus.
 */
void CAN_getRxFIFOStatus(CAN_Type         *CANx,
                         CAN_RxFIFOStatus *fifoStatus)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    switch (fifoStatus->num)
    {
    case CAN_RX_FIFO_NUM_0:
        regVal = READ_REG(CANx->RXF0S);
        fifoStatus->fillLvl  = CAN_RD_FIELD32(regVal, CAN0_RXF0S_F0FL);
        fifoStatus->getIdx   = CAN_RD_FIELD32(regVal, CAN0_RXF0S_F0GI);
        fifoStatus->putIdx   = CAN_RD_FIELD32(regVal, CAN0_RXF0S_F0PI);
        fifoStatus->fifoFull = CAN_RD_FIELD32(regVal, CAN0_RXF0S_F0F);
        fifoStatus->msgLost  = CAN_RD_FIELD32(regVal, CAN0_RXF0S_RF0L);
        break;

    case CAN_RX_FIFO_NUM_1:
        regVal = READ_REG(CANx->RXF1S);
        fifoStatus->fillLvl  = CAN_RD_FIELD32(regVal, CAN0_RXF1S_F1FL);
        fifoStatus->getIdx   = CAN_RD_FIELD32(regVal, CAN0_RXF1S_F1GI);
        fifoStatus->putIdx   = CAN_RD_FIELD32(regVal, CAN0_RXF1S_F1PI);
        fifoStatus->fifoFull = CAN_RD_FIELD32(regVal, CAN0_RXF1S_F1F);
        fifoStatus->msgLost  = CAN_RD_FIELD32(regVal, CAN0_RXF1S_RF1L);
        break;

    default:
        /* Invalid option */
        break;
    }
}

/**
 * @brief   This API will write Rx FIFO Acknowledgement.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @param   fifoNum         FIFO Number.
 * @param   idx             Rx FIFO Acknowledge Index
 *
 * @return  status          Acknowledgement Status.
 */
int32_t CAN_writeRxFIFOAck(CAN_Type *CANx,
                           uint32_t fifoNum,
                           uint32_t idx)
{
    int32_t  status;
    uint32_t size;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    switch (fifoNum)
    {
    case CAN_RX_FIFO_NUM_0:
        size = CAN_RD_FIELD32(CANx->RXF0C,
                              CAN0_RXF0C_F0S);
        if (size >= idx)
        {
            CAN_WR_FIELD32(CANx->RXF0A,
                           CAN0_RXF0A_F0AI,
                           idx);
            status = DRV_OK;
        }
        else
        {
            status = DRV_ERROR;
        }
        break;

    case CAN_RX_FIFO_NUM_1:
        size = CAN_RD_FIELD32(CANx->RXF1C,
                              CAN0_RXF1C_F1S);
        if (size >= idx)
        {
            CAN_WR_FIELD32(CANx->RXF1A,
                           CAN0_RXF1A_F1AI,
                           idx);
            status = DRV_OK;
        }
        else
        {
            status = DRV_ERROR;
        }
        break;

    default:
        status = DRV_ERROR;
        break;
    }

    return status;
}

/**
 * @brief   This API will Tx FIFO status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   fifoStatus     Tx FIFO Status.
 *                         @ref CAN_TxFIFOStatus.
 *
 * @return  None.
 */
void CAN_getTxFIFOQueStatus(CAN_Type         *CANx,
                            CAN_TxFIFOStatus *fifoStatus)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    regVal = READ_REG(CANx->TXFQS);
    fifoStatus->freeLvl  = CAN_RD_FIELD32(regVal, CAN0_TXFQS_TFFL);
    fifoStatus->getIdx   = CAN_RD_FIELD32(regVal, CAN0_TXFQS_TFGI);
    fifoStatus->putIdx   = CAN_RD_FIELD32(regVal, CAN0_TXFQS_TFQPI);
    fifoStatus->fifoFull = CAN_RD_FIELD32(regVal, CAN0_TXFQS_TFQF);
}

/**
 * @brief   This API will return Tx Buffer Request Pending status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  status         Tx Buffer Request Pending status.
 */
uint32_t CAN_getTxBufReqPend(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(READ_REG(CANx->TXBRP));
}

/**
 * @brief   This API will set Tx Buffer Cancellation Request.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   buffNum        Tx Buffer number for which request is to be added.
 *
 * @return  int32_t        Configuration Status.
 */
int32_t CAN_txBufCancellationReq(CAN_Type *CANx, uint32_t buffNum)
{
    int32_t  status;
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (CAN_TX_BUFFER_MAX > buffNum)
    {
        regVal  = READ_REG(CANx->TXBCR);
        regVal |= ((uint32_t)1U << buffNum);

        // For writing to TXBCR CCE bit should be '0'. This need not be
        // reverted because for other qualified writes this is locked state
        // and can't be written.
        CAN_writeProtectedRegAccessLock(CANx);
        WRITE_REG(CANx->TXBCR, regVal);

        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    return status;
}

/**
 * @brief   This API will return Tx Buffer Transmission Occurred status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  uint32_t       Tx Buffer Transmission Occurred status.
 */
uint32_t CAN_getTxBufTransmissionStatus(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(READ_REG(CANx->TXBTO));
}

/**
 * @brief   This API will return Transmit Buffer Cancellation Finished status.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 *
 * @return  uint32_t       Transmit Buffer Cancellation Finished status.
 */
uint32_t CAN_txBufCancellationStatus(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(READ_REG(CANx->TXBCF));
}

/**
 * @brief   This API is used to enable/disable Tx Buffer Transmission Interrupt.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   bufNum          Buffer number for which interrupt is to enable.
 * @param   enable          Interrupt is enabled if it is TRUE.
 *                          Interrupt is disabled  if it is FALSE.
 *
 * @return  int32_t          Configuration status.
 */
int32_t CAN_txBufTransIntrEnable(CAN_Type *CANx,
                                 uint32_t bufNum,
                                 uint32_t enable)
{
    int32_t  status;
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (CAN_TX_BUFFER_MAX > bufNum)
    {
        if (1 == enable)
        {
            regVal  = READ_REG(CANx->TXBTIE);
            regVal |= ((uint32_t)1U << bufNum);
            WRITE_REG(CANx->TXBTIE, regVal);
        }
        else
        {
            regVal  = READ_REG(CANx->TXBTIE);
            regVal &= ~((uint32_t)0x1U << bufNum);
            WRITE_REG(CANx->TXBTIE, regVal);
        }
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    return status;
}

/**
 * @brief   This API is used to enable/disable Tx Buffer Cancellation Finished
 *          Interrupt.
 *
 * @param   CANx           Pointer to the CAN peripheral.
 * @param   bufNum         Buffer number for which interrupt is to enable.
 * @param   enable          Interrupt is enabled if it is TRUE.
 *                          Interrupt is disabled  if it is FALSE.
 * @return  int32_t          Configuration status.
 */
int32_t CAN_getTxBufCancellationIntrEnable(CAN_Type *CANx,
                                           uint32_t bufNum,
                                           uint32_t enable)
{
    int32_t  status;
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (CAN_TX_BUFFER_MAX > bufNum)
    {
        if (1 == enable)
        {
            regVal  = READ_REG(CANx->TXBCIE);
            regVal |= ((uint32_t)0x1U << bufNum);
            WRITE_REG(CANx->TXBCIE, regVal);
        }
        else
        {
            regVal  = READ_REG(CANx->TXBCIE);
            regVal &= ~((uint32_t)0x1U << bufNum);
            WRITE_REG(CANx->TXBCIE, regVal);
        }
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }
    return status;
}

/**
 * @brief   This API will Tx Event FIFO status.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 * @param   fifoStatus      Tx Event FIFO Status.
 *                          @ref CAN_TxEventFIFOStatus.
 */
void CAN_getTxEventFIFOStatus(CAN_Type              *CANx,
                              CAN_TxEventFIFOStatus *fifoStatus)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    regVal = READ_REG(CANx->TXEFS);
    fifoStatus->fillLvl  = CAN_RD_FIELD32(regVal, CAN0_TXEFS_EFFL);
    fifoStatus->getIdx   = CAN_RD_FIELD32(regVal, CAN0_TXEFS_EFGI);
    fifoStatus->putIdx   = CAN_RD_FIELD32(regVal, CAN0_TXEFS_EFPI);
    fifoStatus->fifoFull = CAN_RD_FIELD32(regVal, CAN0_TXEFS_EFF);
    fifoStatus->eleLost  = CAN_RD_FIELD32(regVal, CAN0_TXEFS_TEFL);
}

/**
 * @brief   This API add clock stop request for CAN module to put it in
 *          power down mode.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 * @param   enable          Add CLock Stop Request.
 *                          Adds Clock Clock stop Request is TRUE otherwise
 *                          removes it.
 */
void CAN_addClockStopRequest(CAN_Type *CANx, uint32_t enable)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (1 == enable)
    {
        CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_CSR, 0x1U);
    }
    else
    {
        CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_CSR, 0x0U);
    }
}

/**
 * @brief   This API will write Event FIFO Acknowledge Index.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 * @param   idx             Event FIFO Acknowledge Index
 *
 * @return  int32_t         Acknowledgement Status.
 */
int32_t CAN_writeTxEventFIFOAck(CAN_Type *CANx, uint32_t idx)
{
    int32_t  status;
    uint32_t size;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    size = CAN_RD_FIELD32(CANx->TXEFC,
                          CAN0_TXEFC_EFS);
    if (size >= idx)
    {
        CAN_WR_FIELD32(CANx->TXEFA,
                       CAN0_TXEFA_EFAI,
                       idx);
        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }

    return status;
}

/* ========================================================================== */
/*                          Advance Functions                                 */
/* ========================================================================== */

/**
 * @brief   This API get clock stop acknowledgement for CAN module.
 *          It return whether CAN is power down mode or not.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  uint32_t        Return Clock Stop Acknowledgement status.
 *                          Return '1' if module is set in power down mode else
 *                          returns '0'.
 */
uint32_t CAN_getClockStopAck(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->CCCR, CAN0_CCCR_CSR));
}

/**
 * @brief   This API will return Rx pin state of CAN module.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  state           CAN Rx Pin State.
 *                          0= The CAN bus is dominant
 *                          1= The CAN bus is recessive
 */
uint32_t CAN_getRxPinState(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->TEST, CAN0_TEST_RX));
}

/**
 * @brief   This API will set Tx pin state of CAN module.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 * @param   state           CAN Tx Pin State.
 *                          00= Reset value
 *                          01= Sample Point can be monitored at tx pin
 *                          10= The CAN bus is dominant
 *                          11= The CAN bus is recessive
 *                          other= It will treated as 11.
 */
void CAN_setTxPinState(CAN_Type *CANx, uint32_t state)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);

    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_TEST, 0x1U);
    CAN_WR_FIELD32(CANx->TEST, CAN0_TEST_TX, state);

    CAN_writeProtectedRegAccessLock(CANx);
}

/**
 * @brief   This API will return Tx pin state of CAN module.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  state           CAN Tx Pin State.
 *                          00= Reset value
 *                          01= Sample Point can be monitored at tx pin
 *                          10= The CAN bus is dominant
 *                          11= The CAN bus is recessive
 */
uint32_t CAN_getTxPinState(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->TEST, CAN0_TEST_TX));
}

/**
 * @brief   This API will return current timestamp counter value.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  uint32_t   Current Timestamp counter value.
 */
uint32_t CAN_getTSCounterVal(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->TSCV, CAN0_TSCV_TSC));
}

/**
 * @brief   This API will return clock stop acknowledgement
 *          for CAN module.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  uint32_t        Clock Stop Acknowledge
 *                          0= No clock stop acknowledged
 *                          1= M_CAN may be set in power down
 */
uint32_t CAN_getClkStopAck(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->CCCR, CAN0_CCCR_CSA));
}

/**
 * @brief   This API will get the configured bit timings for CAN module.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 * @param   configParams    Configuration parameters for CAN bit timing.
 *                          @ref CAN_BitTimingParams.
 *
 * @return  None.
 */
void CAN_getBitTime(CAN_Type            *CANx,
                    CAN_BitTimingParams *configParams)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    configParams->nomSynchJumpWidth = CAN_RD_FIELD32(CANx->NBTP,
                                                     CAN0_NBTP_NSJW);
    configParams->nomTimeSeg2 = CAN_RD_FIELD32(CANx->NBTP,
                                               CAN0_NBTP_NTSEG2);
    configParams->nomTimeSeg1 = CAN_RD_FIELD32(CANx->NBTP,
                                               CAN0_NBTP_NTSEG1);
    configParams->nomRatePrescalar = CAN_RD_FIELD32(CANx->NBTP,
                                                    CAN0_NBTP_NBRP);

    configParams->dataSynchJumpWidth = CAN_RD_FIELD32(CANx->DBTP,
                                                      CAN0_DBTP_DSJW);
    configParams->dataTimeSeg2 = CAN_RD_FIELD32(CANx->DBTP,
                                                CAN0_DBTP_DTSEG2);
    configParams->dataTimeSeg1 = CAN_RD_FIELD32(CANx->DBTP,
                                                CAN0_DBTP_DTSEG1);
    configParams->dataRatePrescalar = CAN_RD_FIELD32(CANx->DBTP,
                                                     CAN0_DBTP_DBRP);
}

/**
 * @brief   This API will reset timestamp counter value.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 */
void CAN_resetTSCounter(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_WR_FIELD32(CANx->TSCV, CAN0_TSCV_TSC, 0x0U);
}

/**
 * @brief   This API will return current time-out counter value.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  uint32_t   Current Time-out counter value.
 */
uint32_t CAN_getTOCounterVal(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->TOCV, CAN0_TOCV_TOC));
}

/**
 * @brief   This function return endianness value of CAN module.
 *
 * @return  uint32_t       Endianness value. (0x87654321)
 */
uint32_t CAN_getEndianVal(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->ENDN, CAN0_ENDN_ETV));
}

/**
 * @brief   This API will get the configured Extended ID AND Mask.
 *
 * @param   CANx   Pointer to the CAN peripheral.
 *
 * @return  idMask   Extended ID AND Mask.
 */
uint32_t CAN_getExtIDANDMask(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    return(CAN_RD_FIELD32(CANx->XIDAM, CAN0_XIDAM_EIDM));
}

/* ========================================================================== */
/*                          Internal Functions                                */
/* ========================================================================== */

static void CAN_writeProtectedRegAccessUnlock(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_CCE, 0x1U);
}

static void CAN_writeProtectedRegAccessLock(CAN_Type *CANx)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_WR_FIELD32(CANx->CCCR, CAN0_CCCR_CCE, 0x0U);
}

static void CAN_readMsg(uint32_t         baseAddr,
                        uint32_t         elemAddr,
                        CAN_RxBufElement *elem)
{
    uint32_t regVal = 0U, loopCnt = 0U;

    baseAddr -= 0x4000U;

    regVal   = READ_REG(REG32(baseAddr + elemAddr));
    elem->id = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ID_MASK)
                          >> CAN_RX_BUFFER_ELEM_ID_SHIFT);
    elem->rtr = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_RTR_MASK)
                           >> CAN_RX_BUFFER_ELEM_RTR_SHIFT);
    elem->xtd = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_XTD_MASK)
                           >> CAN_RX_BUFFER_ELEM_XTD_SHIFT);
    elem->esi = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ESI_MASK)
                           >> CAN_RX_BUFFER_ELEM_ESI_SHIFT);

    elemAddr  += 4U;
    regVal     = READ_REG(REG32(baseAddr + elemAddr));
    elem->rxts = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_RXTS_MASK)
                            >> CAN_RX_BUFFER_ELEM_RXTS_SHIFT);
    elem->dlc = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_DLC_MASK)
                           >> CAN_RX_BUFFER_ELEM_DLC_SHIFT);
    elem->brs = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_BRS_MASK)
                           >> CAN_RX_BUFFER_ELEM_BRS_SHIFT);
    elem->fdf = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_FDF_MASK)
                           >> CAN_RX_BUFFER_ELEM_FDF_SHIFT);
    elem->fidx = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_FIDX_MASK)
                            >> CAN_RX_BUFFER_ELEM_FIDX_SHIFT);
    elem->anmf = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ANMF_MASK)
                            >> CAN_RX_BUFFER_ELEM_ANMF_SHIFT);
    elemAddr += 4U;

    loopCnt = 0U;
    /* Reading words from message RAM and forming payload bytes out of it */
    while ((4U <= (CAN_getDataSize(elem->dlc) - loopCnt)) &&
           (0U != (CAN_getDataSize(elem->dlc) - loopCnt)))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal = READ_REG(REG32(baseAddr + elemAddr));
        elem->data[loopCnt]        = (uint16_t)(regVal & 0x000000FFU);
        elem->data[(loopCnt + 1U)] = (uint16_t)((regVal & 0x0000FF00U) >> 8U);
        elem->data[(loopCnt + 2U)] = (uint16_t)((regVal & 0x00FF0000U) >> 16U);
        elem->data[(loopCnt + 3U)] = (uint16_t)((regVal & 0xFF000000U) >> 24U);
        elemAddr += 4U;
        loopCnt  += 4U;
    }
    /* Reading remaining bytes from message RAM */
    if (0U < (CAN_getDataSize(elem->dlc) - loopCnt))
    {
        assert_param((loopCnt + 2U) < CAN_MAX_PAYLOAD_BYTES);
        regVal = READ_REG(REG32(baseAddr + elemAddr));
        elem->data[loopCnt]        = (uint16_t)(regVal & 0x000000FFU);
        elem->data[(loopCnt + 1U)] = (uint16_t)((regVal & 0x0000FF00U) >> 8U);
        elem->data[(loopCnt + 2U)] = (uint16_t)((regVal & 0x00FF0000U) >> 16U);
    }
}

static void CAN_writeMsg(uint32_t               baseAddr,
                         uint32_t               elemAddr,
                         const CAN_TxBufElement *elem)
{
    uint32_t regVal = 0, loopCnt = 0U;


    baseAddr -= 0x4000U;

    regVal  = 0U;
    regVal |= (((uint32_t)(elem->id << CAN_TX_BUFFER_ELEM_ID_SHIFT)) |
               ((uint32_t)(elem->rtr << CAN_TX_BUFFER_ELEM_RTR_SHIFT)) |
               ((uint32_t)(elem->xtd << CAN_TX_BUFFER_ELEM_XTD_SHIFT)) |
               ((uint32_t)(elem->esi << CAN_TX_BUFFER_ELEM_ESI_SHIFT)));
    WRITE_REG(REG32(baseAddr + elemAddr), regVal);
    elemAddr += 4U;

    regVal  = 0U;
    regVal |= ((uint32_t)(elem->dlc << CAN_TX_BUFFER_ELEM_DLC_SHIFT)) |
              ((uint32_t)(elem->brs << CAN_TX_BUFFER_ELEM_BRS_SHIFT)) |
              ((uint32_t)(elem->fdf << CAN_TX_BUFFER_ELEM_FDF_SHIFT)) |
              ((uint32_t)(elem->tx_tsce << CAN_TX_BUFFER_ELEM_TSCE_SHIFT)) |
              ((uint32_t)(elem->efc << CAN_TX_BUFFER_ELEM_EFC_SHIFT)) |
              ((uint32_t)(elem->mm << CAN_TX_BUFFER_ELEM_MM_SHIFT));
    WRITE_REG(REG32(baseAddr + elemAddr), regVal);
    elemAddr += 4U;

    loopCnt = 0U;
    /* Framing words out of the payload bytes and writing it to message RAM */
    while ((4U <= (CAN_getDataSize(elem->dlc) - loopCnt)) &&
           (0U != (CAN_getDataSize(elem->dlc) - loopCnt)))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal  = 0U;
        regVal |= ((uint32_t)elem->data[loopCnt] |
                   ((uint32_t)elem->data[(loopCnt + 1U)] << 8U) |
                   ((uint32_t)elem->data[(loopCnt + 2U)] << 16U) |
                   ((uint32_t)elem->data[(loopCnt + 3U)] << 24U));
        WRITE_REG(REG32(baseAddr + elemAddr), regVal);
        elemAddr += 4U;
        loopCnt  += 4U;
    }

    /* Framing a word out of remaining payload bytes and writing it to
     * message RAM */
    if (0U < (CAN_getDataSize(elem->dlc) - loopCnt))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal  = 0U;
        regVal |= ((uint32_t)elem->data[loopCnt] |
                   ((uint32_t)elem->data[(loopCnt + 1U)] << 8U) |
                   ((uint32_t)elem->data[(loopCnt + 2U)] << 16U) |
                   ((uint32_t)elem->data[(loopCnt + 3U)] << 24U));
        WRITE_REG(REG32(baseAddr + elemAddr), regVal);
    }
}

static uint32_t CAN_getDataSize(uint32_t dlc)
{
    assert_param(dlc < 16U);
    return(dataSize[dlc]);
}

/**
 * @brief Get message object size
 *
 * @param elemSize Element Size
 * @return uint32_t message object size
 */
uint32_t CAN_getMsgObjSize(uint32_t elemSize)
{
    assert_param(elemSize < 8U);
    return(objSize[elemSize]);
}

/**
 * @brief Enable or disable the DMU interrupt
 *
 * @param CANx Transfer with TSU Time stamp
 * @param intrMask  Refer enum @ref #CAN_IntrSrc or #CAN_DMU_INTR_MASK_ALL
 * @param enable enable or disable
 */
void CAN_enableDMUIntr(CAN_Type *CANx, uint32_t intrMask, uint32_t enable)
{
    uint32_t regVal;

    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    if (1 == enable)
    {
        regVal  = READ_REG(CANx->DMUIE);
        regVal |= intrMask;
        WRITE_REG(CANx->DMUIE, regVal);
    }
    else
    {
        regVal  = READ_REG(CANx->DMUIE);
        regVal &= ~intrMask;
        WRITE_REG(CANx->DMUIE, regVal);
    }
}

/**
 * @brief configure for DMU  Transfer with TSU Time stamp
 *
 * @param CANx Pointer to the CAN peripheral.
 * @param enable enable or disable transfer with TSU time stamp
 * @attention CAN_ConfigParams.tsSelect must use External timestamp counter when enable DMU TTS
 */
void CAN_enableDMUTransferTS(CAN_Type *CANx, uint32_t enable)
{
    /* Check the arguments */
    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);
    if (1 == enable)
    {
        SET_BIT(CANx->CCCR, CAN0_CCCR_UTSU_Msk);
        SET_BIT(CANx->DMUC, 0x01U);
    }
    else
    {
        CLEAR_BIT(CANx->CCCR, CAN0_CCCR_UTSU_Msk);
    }
    CAN_writeProtectedRegAccessLock(CANx);
}

/**
 * @brief   This API will configure CAN TSU Unit.
 *
 * @param CANx Pointer to the CAN peripheral.
 * @param[in] configParams
 * @return int32_t
 * @attention CAN_ConfigParams.tsSelect must use External timestamp counter when config TSU
 */
int32_t CAN_configTSU(CAN_Type *CANx, const CAN_TSUConfigParams *configParams)
{
    int32_t status;

    assert_param(IS_CAN_PERIPH(CANx));

    CAN_writeProtectedRegAccessUnlock(CANx);

    /* Configure CAN TSU configure register */
    CAN_WR_FIELD32(CANx->TSCFG, CAN0_TSCFG_SCP, configParams->scp);
    CAN_WR_FIELD32(CANx->TSCFG, CAN0_TSCFG_TBCS, configParams->tbcs);

    if ((CAN_TSU_TBPRE_MAX_VALUE >= configParams->tbPrescalar) &&
        (CAN_TSU_TBPRE_MIN_VALUE <= configParams->tbPrescalar))
    {
        /* Configure Time-stamp counter */
        CAN_WR_FIELD32(CANx->TSCFG, CAN0_TSCFG_TBPRE, (configParams->tbPrescalar - 1U));
        /* Configure Time-out counter */
        CAN_WR_FIELD32(CANx->TSCFG, CAN0_TSCFG_TSUE, configParams->enable);

        status = DRV_OK;
    }
    else
    {
        status = DRV_ERROR;
    }

    CAN_writeProtectedRegAccessLock(CANx);

    return status;
}

/**
 * @brief Select DMU Rx Request type
 *
 * @param CANx Pointer to the CAN peripheral.
 * @param Request Refer enum @ref CAN_DMURxRequest
 */
void CAN_setDMURxRequest(CAN_Type *CANx, CAN_DMURxRequest Request)
{
    assert_param(IS_CAN_PERIPH(CANx));

    if (CANx == CAN0)
    {
        CAN_WR_FIELD32(CAN_MISC0->DMU_DMA_CFG, CAN_MISC0_DMU_DMA_CFG_DMU_DMA_RX_SEL, Request);
    }
    else
    {
        CAN_WR_FIELD32(CAN_MISC1->DMU_DMA_CFG, CAN_MISC0_DMU_DMA_CFG_DMU_DMA_RX_SEL, Request);
    }
}

/**
 * @brief Copy CAN_TxBufElement message to a buffer
 *
 * @param[in] elem  Message Object.
 *              Refer struct @ref CAN_TxBufElement.
 * @param[out] buffer buffer storeed message
 */
void CAN_copyMsgToBuffer(const CAN_TxBufElement *elem,
                         uint32_t               *buffer)
{
    uint32_t regVal = 0, loopCnt = 0U, elemAddr = 0;

    /* Check the arguments */
    assert_param(buffer != NULL);
    assert_param(elem != NULL);


    regVal  = 0U;
    regVal |= (((uint32_t)(elem->id << CAN_TX_BUFFER_ELEM_ID_SHIFT)) |
               ((uint32_t)(elem->rtr << CAN_TX_BUFFER_ELEM_RTR_SHIFT)) |
               ((uint32_t)(elem->xtd << CAN_TX_BUFFER_ELEM_XTD_SHIFT)) |
               ((uint32_t)(elem->esi << CAN_TX_BUFFER_ELEM_ESI_SHIFT)));
    *(buffer + elemAddr) = regVal;
    elemAddr            += 1U;

    regVal  = 0U;
    regVal |= ((uint32_t)(elem->dlc << CAN_TX_BUFFER_ELEM_DLC_SHIFT)) |
              ((uint32_t)(elem->brs << CAN_TX_BUFFER_ELEM_BRS_SHIFT)) |
              ((uint32_t)(elem->fdf << CAN_TX_BUFFER_ELEM_FDF_SHIFT)) |
              ((uint32_t)(elem->tx_tsce << CAN_TX_BUFFER_ELEM_TSCE_SHIFT)) |
              ((uint32_t)(elem->efc << CAN_TX_BUFFER_ELEM_EFC_SHIFT)) |
              ((uint32_t)(elem->mm << CAN_TX_BUFFER_ELEM_MM_SHIFT));
    *(buffer + elemAddr) = regVal;
    elemAddr            += 1U;

    loopCnt = 0U;
    /* Framing words out of the payload bytes and writing it to message RAM */
    while ((4U <= (CAN_getDataSize(elem->dlc) - loopCnt)) &&
           (0U != (CAN_getDataSize(elem->dlc) - loopCnt)))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal  = 0U;
        regVal |= ((uint32_t)elem->data[loopCnt] |
                   ((uint32_t)elem->data[(loopCnt + 1U)] << 8U) |
                   ((uint32_t)elem->data[(loopCnt + 2U)] << 16U) |
                   ((uint32_t)elem->data[(loopCnt + 3U)] << 24U));
        *(buffer + elemAddr) = regVal;
        elemAddr            += 1U;
        loopCnt += 4U;
    }

    /* Framing a word out of remaining payload bytes and writing it to
     * message RAM */
    if (0U < (CAN_getDataSize(elem->dlc) - loopCnt))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal  = 0U;
        regVal |= ((uint32_t)elem->data[loopCnt] |
                   ((uint32_t)elem->data[(loopCnt + 1U)] << 8U) |
                   ((uint32_t)elem->data[(loopCnt + 2U)] << 16U) |
                   ((uint32_t)elem->data[(loopCnt + 3U)] << 24U));
        *(buffer + elemAddr) = regVal;
    }
}

/**
 * @brief Copy message in buffer to CAN_RxBufElement structure element
 *
 * @param[in]  buffer buffer storeed message
 * @param[out] elem CAN_RxBufElement element
 */
void CAN_copyBufferToMsg(uint32_t *buffer, CAN_RxBufElement *elem)
{
    uint32_t regVal = 0U, loopCnt = 0U, elemAddr = 0;

    /* Check the arguments */
    assert_param(buffer != NULL);
    assert_param(elem != NULL);

    regVal   = *(buffer + elemAddr);
    elem->id = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ID_MASK)
                          >> CAN_RX_BUFFER_ELEM_ID_SHIFT);
    elem->rtr = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_RTR_MASK)
                           >> CAN_RX_BUFFER_ELEM_RTR_SHIFT);
    elem->xtd = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_XTD_MASK)
                           >> CAN_RX_BUFFER_ELEM_XTD_SHIFT);
    elem->esi = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ESI_MASK)
                           >> CAN_RX_BUFFER_ELEM_ESI_SHIFT);

    elemAddr  += 1U;
    regVal     = *(buffer + elemAddr);
    elem->rxts = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_RXTS_MASK)
                            >> CAN_RX_BUFFER_ELEM_RXTS_SHIFT);
    elem->dlc = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_DLC_MASK)
                           >> CAN_RX_BUFFER_ELEM_DLC_SHIFT);
    elem->brs = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_BRS_MASK)
                           >> CAN_RX_BUFFER_ELEM_BRS_SHIFT);
    elem->fdf = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_FDF_MASK)
                           >> CAN_RX_BUFFER_ELEM_FDF_SHIFT);
    elem->fidx = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_FIDX_MASK)
                            >> CAN_RX_BUFFER_ELEM_FIDX_SHIFT);
    elem->anmf = (uint32_t)((regVal & CAN_RX_BUFFER_ELEM_ANMF_MASK)
                            >> CAN_RX_BUFFER_ELEM_ANMF_SHIFT);
    elemAddr += 1U;

    loopCnt = 0U;
    /* Reading words from message RAM and forming payload bytes out of it */
    while ((4U <= (CAN_getDataSize(elem->dlc) - loopCnt)) &&
           (0U != (CAN_getDataSize(elem->dlc) - loopCnt)))
    {
        assert_param((loopCnt + 3U) < CAN_MAX_PAYLOAD_BYTES);
        regVal = *(buffer + elemAddr);
        elem->data[loopCnt]        = (uint16_t)(regVal & 0x000000FFU);
        elem->data[(loopCnt + 1U)] = (uint16_t)((regVal & 0x0000FF00U) >> 8U);
        elem->data[(loopCnt + 2U)] = (uint16_t)((regVal & 0x00FF0000U) >> 16U);
        elem->data[(loopCnt + 3U)] = (uint16_t)((regVal & 0xFF000000U) >> 24U);
        elemAddr += 1U;
        loopCnt  += 4U;
    }
    /* Reading remaining bytes from message RAM */
    if (0U < (CAN_getDataSize(elem->dlc) - loopCnt))
    {
        assert_param((loopCnt + 2U) < CAN_MAX_PAYLOAD_BYTES);
        regVal = *(buffer + elemAddr);
        elem->data[loopCnt]        = (uint16_t)(regVal & 0x000000FFU);
        elem->data[(loopCnt + 1U)] = (uint16_t)((regVal & 0x0000FF00U) >> 8U);
        elem->data[(loopCnt + 2U)] = (uint16_t)((regVal & 0x00FF0000U) >> 16U);
    }
}
