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

#include "et6x_xbar.h"
#include <et6x.h>

// in XBAR, all signals input is 4x1mux out
#define CH_NUM_PER_GRP             4
// in XBAR, max 16 grp in one mux config register
#define MAX_MUX_GRP_IN_MUXREG      16
// Input filter windows max delay
#define MAX_FILTER_WND_SIZE        0x3FF
// INXB  channel configure
#define MAX_INXB_SRC_IN_CH         84
#define MAX_INXB_OUTPUT_CH         16
#define MAX_INXB_OUTPUT_IRQ_CH     4
#define INXB_OUTPUT_ALL_CH_MASK    BITS_WID_MASK(MAX_INXB_OUTPUT_CH)
// PFXB  channel configure
#define MAX_PFXB_SRC_IN_CH         128
#define MAX_PFXB_OUTPUT_CH         12
#define PFXB_OUTPUT_ALL_CH_MASK    BITS_WID_MASK(MAX_PFXB_OUTPUT_CH)

// ETXB  channel configure
#define MAX_ETXB_SRC_IN_CH         128
#define MAX_ETXB_OUTPUT_CH         14
#define ETXB_OUTPUT_ALL_CH_MASK    BITS_WID_MASK(MAX_ETXB_OUTPUT_CH)
// OPXB  channel configure
#define MAX_OPXB_SRC_IN_CH         128
#define MAX_OPXB_OUTPUT_CH         14
#define OPXB_OUTPUT_ALL_CH_MASK    BITS_WID_MASK(MAX_OPXB_OUTPUT_CH)
#define MAX_OPXB_SW_IN_CH          4
// CLU configure
#define MAX_CLU_OUTPUT_CH          4
// Misc signal input configure
#define MAX_FAULT_SRC_NUM          18
#define MAX_STIM_CORE_NUM          2
// CIXB  channel configure
#define MAX_CIXB_SRC_IN_CH         84
#define MAX_CIXB_OUTPUT_CH         16
// CBXB  channel configure
#define MAX_CBXB_SRC_IN_CH         128
#define MAX_CBXB_OUTPUT_CH         14
// COXB  channel configure
#define MAX_COXB_SRC_IN_CH         128
#define MAX_COXB_OUTPUT_CH         14

/*******************************************************************************
 * INXB
 ******************************************************************************/

/**
 * @brief Configure INXB Input Mux
 * total of 16 channels of output, each channel of output can choose 80 input channel after every 4 choose 1 mux, that
 * is,
 * total 20 mux groups
 *
 * @param out_ch_mask   Which Output channel for mux input
 * @param in_ch_mask    Which Input channel input to mux for 4 chose 1
 * 4 channels a group, take effect on the last mux. For example, if in_ch_mask is xxxx_0b0111_xxxx, ch2 selected
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint8_t  och = 0, ch = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;

    assert_param(in_ch_mask != NULL);

    /* calc mux_grp according to in_ch_mask */

    for (och = 0; och < MAX_INXB_OUTPUT_CH; och++)
    {
        /* output ch 0~15 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_INXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* NOTICE: mux en will set according to input source mask auto */
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))  ///BIT_MASK
                {
                    mux_grp = ch / CH_NUM_PER_GRP;
                    /* mux channel 00/01/10/11 4sel1 */
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4sel1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~20 */
                        /* MUX 4sel1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    /* MUX_EN set save to temp */
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->INXB_GRP[och].INXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->INXB_GRP[och].INXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->INXB_GRP[och].INXB_ENB, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure INXB Input Channel Paramater
 *
 * @param cfg
 * - outDsel  output signal type select
 * - outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_INXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 15 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->INXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->INXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->INXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_INXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief  Enable output
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_enableOutputMux(uint16_t out_ch_mask)
{
    SET_BIT(XBAR->INXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_disableOutputMux(uint16_t out_ch_mask)
{
    CLEAR_BIT(XBAR->INXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Clear output latch status
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_clearOutputLatch(uint16_t out_ch_mask)
{
    SET_BIT(XBAR->INXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get output channel status
 *
 * @param out_ch  output channel 0~15
 * @param  latched  get latched status or real-time status
 * @return FlagStatus
 */
FlagStatus XBAR_INXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_INXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->INXB_RPT, BIT_MASK(out_ch << 16));
    }
    else
    {
        val = READ_BIT(XBAR->INXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR INXB Output All Channel Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_INXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->INXB_RPT) & XBAR_INXB_RPT_INXB_LAT_RPT_Msk) >> XBAR_INXB_RPT_INXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->INXB_RPT) & XBAR_INXB_RPT_INXB_OUT_RPT_Msk;
    }

    return val;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_enableInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    SET_BIT(XBAR->INXB_INT_EN, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_disableInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    CLEAR_BIT(XBAR->INXB_INT_EN, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_setInterruptMask(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    SET_BIT(XBAR->INXB_INT_MASK, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_clearInterruptMask(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    CLEAR_BIT(XBAR->INXB_INT_MASK, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_forceTriggerInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    SET_BIT(XBAR->INXB_INT_FORCE_IND, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask  @ref XBAR_INXB_IRQ_TypeDef
 * @return DRV_Status
 */
DRV_Status XBAR_INXB_clearInterruptStatus(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));
    SET_BIT(XBAR->INXB_INT_CLR, (uint32_t)(it_channel_mask));
    return DRV_OK;
}

/**
 * @brief
 *
 * @param it_channel_mask  ch0~4
 * @return DRV_Status
 */
ITStatus XBAR_INXB_getChInterruptStatus(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    uint32_t val    = 0;
    ITStatus status = RESET;

    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));

    val    = READ_BIT(XBAR->INXB_INT_STATUS_RPT, it_channel_mask);
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief
 *
 * @param it_channel_mask
 * @return DRV_Status
 */
ITStatus XBAR_INXB_getChInterruptRawStatus(XBAR_INXB_IRQ_TypeDef it_channel_mask)
{
    uint32_t val    = 0;
    ITStatus status = RESET;

    assert_param(it_channel_mask <= BITS_WID_MASK(MAX_INXB_OUTPUT_IRQ_CH));

    val    = READ_BIT(XBAR->INXB_INT_RAW_RPT, it_channel_mask);
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief  Get INXB Interrupt Status
 *
 * @return uint8_t INXB int status(4bit)
 */
uint8_t XBAR_INXB_getInterruptStatus(void)
{
    uint32_t val = 0;

    val = READ_REG(XBAR->INXB_INT_STATUS_RPT);
    return (uint8_t)val;
}

/**
 * @brief Get INXB Interrupt Raw Status
 *
 * @return uint8_t INXB raw int status(4bit)
 */
uint8_t XBAR_INXB_getInterruptRawStatus(void)
{
    uint32_t val = 0;

    val = READ_REG(XBAR->INXB_INT_RAW_RPT);
    return (uint8_t)val;
}

/*******************************************************************************
 * PFXB
 ******************************************************************************/

/**
 * @brief Configures PWM Fault XBAR output MUX
 *
 * @param out_ch_mask
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_PFXB_setMuxConfig(uint32_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint8_t  och = 0, ch = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_PFXB_OUTPUT_CH));
    /* calc mux_grp according to in_ch_mask */

    for (och = 0; och < MAX_PFXB_OUTPUT_CH; och++)
    {
        /* output ch 0~17 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_PFXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp     = ch / CH_NUM_PER_GRP;
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4 chose 1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~31 */
                        /* MUX 4 chose 1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->PFXB_GRP[och].PFXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->PFXB_GRP[och].PFXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->PFXB_GRP[och].PFXB_ENB0, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure PFXB Input Channel Paramater
 *
 * @param cfg
 * - outDsel  output signal type select
 * - outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_PFXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_PFXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 15 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->PFXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->PFXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->PFXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_PFXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief Enable output
 *
 * @param out_ch_mask  ch0~ch16 mask
 * @return DRV_Status
 */
DRV_Status XBAR_PFXB_enableOutputMux(uint32_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_PFXB_OUTPUT_CH));
    SET_BIT(XBAR->PFXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask  ch0~ch16 mask
 * @return DRV_Status
 */
DRV_Status XBAR_PFXB_disableOutputMux(uint32_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_PFXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->PFXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Clear output latch status
 *
 * @param out_ch_mask  ch0~ch16 mask
 * @return DRV_Status
 */
DRV_Status XBAR_PFXB_clearOutputLatch(uint32_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_PFXB_OUTPUT_CH));
    SET_BIT(XBAR->PFXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get XBAR PFXB Output Channel Latch Status
 *
 * @param out_ch  channel number 0~16
 * @param latched
 * @return FlagStatus
 */
FlagStatus XBAR_PFXB_getOutputChStatus(uint32_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_PFXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->PFXB_RPT1, BIT_MASK(out_ch << XBAR_PFXB_RPT1_PFXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->PFXB_RPT0, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR PFXB Output All Channel Latch Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_PFXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->PFXB_RPT1) & XBAR_PFXB_RPT1_PFXB_LAT_RPT_Msk) >> XBAR_PFXB_RPT1_PFXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->PFXB_RPT0) & XBAR_PFXB_RPT0_PFXB_OUT_RPT_Msk;
    }

    return val;
}

/*******************************************************************************
 * ETXB
 ******************************************************************************/
/**
 * @brief Configures ETIMER XBAR output MUX
 *
 * @param out_ch_mask
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;
    uint8_t  och = 0, ch = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    /* calc mux_grp according to in_ch_mask */
    for (och = 0; och < MAX_ETXB_OUTPUT_CH; och++)
    {
        /* output ch 0~11 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_ETXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp     = ch / CH_NUM_PER_GRP;
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4 chose 1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~31 */
                        /* MUX 4 chose 1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->ETXB_GRP[och].ETXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->ETXB_GRP[och].ETXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->ETXB_GRP[och].ETXB_ENB, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure ETXB Input Channel Paramater
 *
 * @param cfg
 * - outDsel  output signal type select
 * - outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_ETXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 13 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->ETXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->ETXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->ETXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_ETXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief Enable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_enableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    SET_BIT(XBAR->ETXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_disableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->ETXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Clear output latch status
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_clearOutputLatch(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    SET_BIT(XBAR->ETXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Set Software Trigger input
 *
 * @param sw_in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_setSoftwareInput(uint16_t sw_in_ch_mask)
{
    assert_param(sw_in_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    SET_BIT(XBAR->ETXB_SW, sw_in_ch_mask);

    return DRV_OK;
}

/**
 * @brief  Clear Software Trigger input
 *
 * @param sw_in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_ETXB_clearSoftwareInput(uint16_t sw_in_ch_mask)
{
    assert_param(sw_in_ch_mask <= BITS_WID_MASK(MAX_ETXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->ETXB_SW, sw_in_ch_mask);

    return DRV_OK;
}

/**
 * @brief  Get XBAR ETXB Output Channel Latch Status
 *
 * @param out_ch  ch0~ch11
 * @param latched
 * @return FlagStatus
 */
FlagStatus XBAR_ETXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_ETXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->ETXB_RPT, BIT_MASK(out_ch << XBAR_ETXB_RPT_ETXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->ETXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR ETXB Output All Channel Latch Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_ETXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->ETXB_RPT) & XBAR_ETXB_RPT_ETXB_LAT_RPT_Msk) >> XBAR_ETXB_RPT_ETXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->ETXB_RPT) & XBAR_ETXB_RPT_ETXB_OUT_RPT_Msk;
    }

    return val;
}

/*******************************************************************************
 * OPXB
 ******************************************************************************/
/**
 * @brief Configure OPXB Input Mux
 *
 * @param out_ch_mask   Which Output channel for mux input
 * @param in_ch_mask    Which Input channel input to mux for 4 chose 1
 * @attention  every 4 input channels, if all 4 channels are masked, the last one takes effect
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;
    uint8_t  och = 0, ch = 0;

    assert_param(in_ch_mask != NULL);

    /* calc mux_grp according to in_ch_mask */
    for (och = 0; och < MAX_OPXB_OUTPUT_CH; och++)
    {
        /* output ch 0~15 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_OPXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp = ch / CH_NUM_PER_GRP;
                    /* mux channel 00/01/10/11 4sel1 */
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~9 */
                        /* MUX 4sel1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 9~18 */
                        /* MUX 4sel1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->OPXB_GRP[och].OPXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->OPXB_GRP[och].OPXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->OPXB_GRP[och].OPXB_ENB0, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure OPXB Input Channel Paramater
 *
 * @param cfg
 * - outDsel  output signal type select
 * - outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_OPXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 13 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->OPXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->OPXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->OPXB_OUTPOL, BIT_MASK(ch));
            }
            if (cfg->outPulseStretchEn)
            {
                SET_BIT(XBAR->OPXB_EXPEN, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->OPXB_EXPEN, BIT_MASK(ch));
            }
            MODIFY_REG(XBAR->OPXB_OEMOD, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outOEmode << ch * 2);
        }
    } // end of for (uint8_t ch = 0; ch < MAX_OPXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief  Enable output
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_enableOutputMux(uint16_t out_ch_mask)
{
    SET_BIT(XBAR->OPXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_disableOutputMux(uint16_t out_ch_mask)
{
    CLEAR_BIT(XBAR->OPXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Clear output latch status
 *
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_clearOutputLatch(uint16_t out_ch_mask)
{
    SET_BIT(XBAR->OPXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get output channel latch status
 *
 * @param out_ch  output channel 0~15
 * @param latched latch or not latch
 * @return FlagStatus SET or RESET
 */
FlagStatus XBAR_OPXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_OPXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->OPXB_RPT, BIT_MASK(out_ch << XBAR_OPXB_RPT_OPXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->OPXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR OPXB Output All Channel Latch Status
 *
 * @param latched latch or not latch
 * @return status with all channel
 */
uint32_t XBAR_OPXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->OPXB_RPT) & XBAR_OPXB_RPT_OPXB_LAT_RPT_Msk) >> XBAR_OPXB_RPT_OPXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->OPXB_RPT) & XBAR_OPXB_RPT_OPXB_OUT_RPT_Msk;
    }

    return val;
}

/**
 * @brief  Set Software Trigger input
 *
 * @param sw_in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_setSoftwareInput(uint16_t sw_in_ch_mask)
{
    assert_param(sw_in_ch_mask <= BITS_WID_MASK(MAX_OPXB_OUTPUT_CH));
    SET_BIT(XBAR->OPXB_SW, sw_in_ch_mask);

    return DRV_OK;
}

/**
 * @brief  Clear Software Trigger input
 *
 * @param sw_in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_OPXB_clearSoftwareInput(uint16_t sw_in_ch_mask)
{
    assert_param(sw_in_ch_mask <= BITS_WID_MASK(MAX_OPXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->OPXB_SW, sw_in_ch_mask);

    return DRV_OK;
}

/*******************************************************************************
 * CLU
 ******************************************************************************/
/**
 * @brief  Configure edgeType, invertEn, bypassEn, outEn, clu_type
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask  max 4ch ->0x0F    0x03  : ch0~1
 * @param cfg
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_setConfig(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask, XBAR_CLU_Cfg_TypeDef *cfg)
{
    uint32_t reg_addr = 0, reg_val = 0;
    uint8_t  edge_type_bits_width = 2;
    uint8_t  clu_type_bits_width  = 3;
    uint8_t  och = 0;

    assert_param(cfg != NULL);
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));

    reg_addr = (uint32_t)(&XBAR->XCSA) + (uint8_t)clu_type * OFT_REG32;
    for (och = 0; och < CH_NUM_PER_GRP; och++)
    {
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_val |= ((uint32_t)cfg->edgeType << (XBAR_XCSA_XCSA_INTEDG_SEL_Pos + och * edge_type_bits_width)) |
                       ((uint32_t)cfg->invertEn << (XBAR_XCSA_XCSA_LCPOL_Pos + och)) |
                       ((uint32_t)cfg->bypassEn << (XBAR_XCSA_XCSA_LCBPS_Pos + och)) |
                       ((uint32_t)cfg->outEn << (XBAR_XCSA_XCSA_LCEN_Pos + och)) |
                       ((uint32_t)cfg->cluType << (XBAR_XCSA_XCSA_MODE_Pos + och * clu_type_bits_width));
        }
    }
    WRITE_REG(REG32(reg_addr), reg_val);
    return DRV_OK;
}

/**
 * @brief Enable CLU interrupt
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_enableInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    SET_BIT(XBAR->CLU_INT_EN, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief Disable CLU interrupt
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_disableInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    CLEAR_BIT(XBAR->CLU_INT_EN, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief Set CLU interrupt mask
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_setInterruptMask(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    SET_BIT(XBAR->CLU_INT_MASK, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief Clear CLU interrupt mask
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_clearInterruptMask(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    CLEAR_BIT(XBAR->CLU_INT_MASK, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief force trigger CLU Interrupt Status
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_forceTriggerInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    SET_BIT(XBAR->CLU_INT_FORCE_IND, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief Clear CLU Interrupt Status
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param out_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CLU_clearInterruptStatus(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask)
{
    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CLU_OUTPUT_CH));
    SET_BIT(XBAR->CLU_INT_CLR, (uint32_t)(out_ch_mask << ((uint32_t)clu_type * CH_NUM_PER_GRP)));
    return DRV_OK;
}

/**
 * @brief Get CLU Interrupt Status
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param channel  ch0~4
 * @return DRV_Status
 */
ITStatus XBAR_CLU_getChInterruptStatus(XBAR_CLU_TypeDef clu_type, uint8_t channel)
{
    uint32_t val    = 0;
    ITStatus status = RESET;

    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(channel <= MAX_CLU_OUTPUT_CH);

    val    = READ_BIT(XBAR->CLU_INT_STATUS_RPT, BIT_MASK(channel + (uint32_t)clu_type * CH_NUM_PER_GRP));
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get CLU Interrupt Raw Status
 *
 * @param clu_type
 * -  XBAR_CLU_XCSA
 * -  XBAR_CLU_XCET
 * -  XBAR_CLU_XCOX
 * @param channel
 * @return DRV_Status
 */
ITStatus XBAR_CLU_getChInterruptRawStatus(XBAR_CLU_TypeDef clu_type, uint8_t channel)
{
    uint32_t val    = 0;
    ITStatus status = RESET;

    assert_param(clu_type <= XBAR_CLU_XCOX);
    assert_param(channel <= MAX_CLU_OUTPUT_CH);


    val    = READ_BIT(XBAR->CLU_INT_RAW_RPT, BIT_MASK(channel + (uint32_t)clu_type * CH_NUM_PER_GRP));
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief  Get CLU Interrupt Status
 *
 * @param clu_type ref to enum XBAR_CLU_TypeDef
 * @return uint8_t clu int status(4bit)
 */
uint8_t XBAR_CLU_getInterruptStatus(XBAR_CLU_TypeDef clu_type)
{
    uint32_t val = 0;

    assert_param(clu_type <= XBAR_CLU_XCOX);


    val = READ_BIT(XBAR->CLU_INT_STATUS_RPT,
                   BITS_MASK((uint32_t)clu_type * CH_NUM_PER_GRP, 3 + (uint32_t)clu_type * CH_NUM_PER_GRP));
    val = val >> (uint32_t)clu_type * CH_NUM_PER_GRP;
    return (uint8_t)val;
}

/**
 * @brief Get CLU Interrupt Raw Status
 *
 * @param clu_type ref to enum XBAR_CLU_TypeDef
 * @return uint8_t clu raw int status(4bit)
 */
uint8_t XBAR_CLU_getInterruptRawStatus(XBAR_CLU_TypeDef clu_type)
{
    uint32_t val = 0;

    assert_param(clu_type <= XBAR_CLU_XCOX);

    val = READ_BIT(XBAR->CLU_INT_RAW_RPT,
                   BITS_MASK((uint32_t)clu_type * CH_NUM_PER_GRP, 3 + (uint32_t)clu_type * CH_NUM_PER_GRP));
    val = val >> (uint32_t)clu_type * CH_NUM_PER_GRP;
    return (uint8_t)val;
}

/**
 * @brief  Add input channel source to in_ch_mask struct
 *
 * @param in_ch_mask Pointer to in_ch_mask, input channel mask initialized by XBAR_initInputChMsk
 * @param ch_idx  XBAR input channel index
 * @return DRV_Status
 * @attention in_ch_mask should be reset before start a new input channels add in
 */
DRV_Status XBAR_addInputSource(XBAR_InChMsk_TypeDef *in_ch_mask, uint8_t ch_idx)
{
    uint8_t idx = 0, offset = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(ch_idx <= MAX_PFXB_SRC_IN_CH);

    idx    = ch_idx / BITS_DWORD;
    offset = ch_idx % BITS_DWORD;
    in_ch_mask->chBitMsk[idx] |= BIT_MASK(offset);

    return DRV_OK;
}

/**
 * @brief Reset struct XBAR_InChMsk_TypeDef for add source next
 *
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_initInputChMsk(XBAR_InChMsk_TypeDef *in_ch_mask)
{
    assert_param(in_ch_mask != NULL);

    in_ch_mask->chBitMsk[0] = 0;
    in_ch_mask->chBitMsk[1] = 0;
    in_ch_mask->chBitMsk[2] = 0;
    in_ch_mask->chBitMsk[3] = 0;
    return DRV_OK;
}

/**
 * @brief select input fault signal source
 *
 * @param fault_src_mask  ref to enum  XBAR_FALUT_SRC_TypeDef
 * @return DRV_Status
 */
DRV_Status XBAR_selectFaultMux(uint32_t fault_src_mask)
{
    assert_param(fault_src_mask <= BITS_WID_MASK(MAX_FAULT_SRC_NUM));
    SET_BIT(XBAR->FAULT_EN, (uint32_t)(fault_src_mask));
    return DRV_OK;
}

/**
 * @brief reset fault signal mux selection, all fault signal in disabled
 *
 */
void XBAR_resetFaultMux(void)
{
    WRITE_REG(XBAR->FAULT_EN, 0);
}

/**
 * @brief XBAR Stimer Emergency Stop Signal source select and enable
 *
 * @param stim_idx  reference to stimer index
 * @param stim_es_sig stimer emergency signal source
 * @param fault_src_mask  ref to enum  XBAR_FALUT_SRC_TypeDef
 * @return DRV_Status
 */
DRV_Status XBAR_selectStimerEFSingalOutput(XBAR_STIM_IDX_TypeDef stim_idx, XBAR_STIM_EF_SIG_TypeDef stim_es_sig,
                                           uint32_t fault_src_mask)
{
    uint32_t reg_addr = 0;

    assert_param(stim_idx < MAX_STIM_CORE_NUM);
    assert_param(stim_es_sig <= XBAR_STIM_EG_FAULT_SIG1);
    assert_param(fault_src_mask <= BITS_WID_MASK(MAX_FAULT_SRC_NUM));

    reg_addr = (uint32_t)(&XBAR->STM0ERG0_EN) + stim_idx * OFT_REG32 * 2 + stim_es_sig * OFT_REG32;
    SET_BIT(REG32(reg_addr), (uint32_t)(fault_src_mask));
    return DRV_OK;
}

/**
 * @brief  XBAR Stimer Emergency Stop Signal source select disable
 *
 * @param stim_idx reference to stimer index
 * @param stim_es_sig  stimer emergency signal source
 * @return DRV_Status
 */
void XBAR_resetStimerEFSignalOutput(XBAR_STIM_IDX_TypeDef stim_idx, XBAR_STIM_EF_SIG_TypeDef stim_es_sig)
{
    uint32_t reg_addr = 0;

    assert_param(stim_idx < MAX_STIM_CORE_NUM);
    assert_param(stim_es_sig <= XBAR_STIM_EG_FAULT_SIG1);

    reg_addr = (uint32_t)(&XBAR->STM0ERG0_EN) + stim_idx * OFT_REG32 * 2 + stim_es_sig * OFT_REG32;
    WRITE_REG(REG32(reg_addr), 0);
}

/*******************************************************************************
 * CLB Input XBAR
 ******************************************************************************/
/**
 * @brief
 *
 * @param out_ch_mask
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CIXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;
    uint8_t  och = 0, ch = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CIXB_OUTPUT_CH));
    /* calc mux_grp according to in_ch_mask */
    for (och = 0; och < MAX_CIXB_OUTPUT_CH; och++)
    {
        /* output ch 0~11 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_CIXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp     = ch / CH_NUM_PER_GRP;
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4 chose 1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~31 */
                        /* MUX 4 chose 1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->CIXB_GRP[och].CIXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->CIXB_GRP[och].CIXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->CIXB_GRP[och].CIXB_ENB, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure CIXB Input Channel Paramater
 *
 * @param cfg
 * @arg outDsel  output signal type select
 * @arg outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_CIXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_CIXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 13 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->CIXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->CIXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->CIXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_CIXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief Enable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CIXB_enableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CIXB_OUTPUT_CH));
    SET_BIT(XBAR->CIXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CIXB_disableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CIXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->CIXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Clear output latch status
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CIXB_clearOutputLatch(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CIXB_OUTPUT_CH));
    SET_BIT(XBAR->CIXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get XBAR CIXB Output Channel Latch Status
 *
 * @param out_ch  ch0~ch11
 * @param latched
 * @return FlagStatus
 */
FlagStatus XBAR_CIXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_PFXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->CIXB_RPT, BIT_MASK(out_ch << XBAR_CIXB_RPT_CIXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->CIXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR CIXB Output All Channel Latch Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_CIXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->CIXB_RPT) & XBAR_CIXB_RPT_CIXB_LAT_RPT_Msk) >> XBAR_CIXB_RPT_CIXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->CIXB_RPT) & XBAR_CIXB_RPT_CIXB_OUT_RPT_Msk;
    }

    return val;
}

/*******************************************************************************
 * CBXB
 ******************************************************************************/
/**
 * @brief
 *
 * @param out_ch_mask
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_CBXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;
    uint8_t  och = 0, ch = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CBXB_OUTPUT_CH));
    /* calc mux_grp according to in_ch_mask */
    for (och = 0; och < MAX_CBXB_OUTPUT_CH; och++)
    {
        /* output ch 0~11 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_CBXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp     = ch / CH_NUM_PER_GRP;
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4 chose 1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~31 */
                        /* MUX 4 chose 1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->CBXB_GRP[och].CBXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->CBXB_GRP[och].CBXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->CBXB_GRP[och].CBXB_ENB, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure CBXB Input Channel Paramater
 *
 * @param cfg
 * @arg outDsel  output signal type select
 * @arg outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_CBXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_CBXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 13 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->CBXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->CBXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->CBXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_CBXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief Enable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CBXB_enableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CBXB_OUTPUT_CH));
    SET_BIT(XBAR->CBXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CBXB_disableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CBXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->CBXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Clear output latch status
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_CBXB_clearOutputLatch(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_CBXB_OUTPUT_CH));
    SET_BIT(XBAR->CBXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get XBAR CBXB Output Channel Latch Status
 *
 * @param out_ch  ch0~ch11
 * @param latched
 * @return FlagStatus
 */
FlagStatus XBAR_CBXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_PFXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->CBXB_RPT, BIT_MASK(out_ch << XBAR_CBXB_RPT_CBXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->CBXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR CBXB Output All Channel Latch Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_CBXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->CBXB_RPT) & XBAR_CBXB_RPT_CBXB_LAT_RPT_Msk) >> XBAR_CBXB_RPT_CBXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->CBXB_RPT) & XBAR_CBXB_RPT_CBXB_OUT_RPT_Msk;
    }

    return val;
}

/*******************************************************************************
 * COXB
 ******************************************************************************/
/**
 * @brief
 *
 * @param out_ch_mask
 * @param in_ch_mask
 * @return DRV_Status
 */
DRV_Status XBAR_COXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask)
{
    uint8_t  mux_grp     = 0;
    uint8_t  mux_grp_idx = 0;
    uint32_t reg_mux0_temp = 0, reg_mux1_temp = 0, reg_en_temp = 0;
    uint8_t  ch_grp = 0, ch_idx = 0;
    uint8_t  och = 0, ch = 0;

    assert_param(in_ch_mask != NULL);
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_COXB_OUTPUT_CH));
    /* calc mux_grp according to in_ch_mask */
    for (och = 0; och < MAX_COXB_OUTPUT_CH; och++)
    {
        /* output ch 0~11 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(och)))
        {
            reg_mux0_temp = 0;
            reg_mux1_temp = 0;
            /* get mux_grp from in_ch_mask */
            for (ch = 0; ch < MAX_COXB_SRC_IN_CH; ch++)
            {
                ch_grp = ch / BITS_DWORD;
                ch_idx = ch % BITS_DWORD;
                /* input ch masked */
                if (DRV_IS_BIT_SET(in_ch_mask->chBitMsk[ch_grp], BIT_MASK(ch_idx)))
                {
                    mux_grp     = ch / CH_NUM_PER_GRP;
                    mux_grp_idx = ch % CH_NUM_PER_GRP;
                    if (mux_grp < MAX_MUX_GRP_IN_MUXREG)
                    {
                        /* mux group 0~15 */
                        /* MUX 4 chose 1 select  */
                        reg_mux0_temp |= (uint32_t)(mux_grp_idx << mux_grp * 2);  /*2bit one mux */
                    }
                    else
                    {
                        /* mux group 16~31 */
                        /* MUX 4 chose 1 select */
                        reg_mux1_temp |= (uint32_t)(mux_grp_idx << (mux_grp - MAX_MUX_GRP_IN_MUXREG) * 2);
                    }
                    reg_en_temp |= (uint32_t)(1 << (mux_grp));
                }
            }
            WRITE_REG(XBAR->COXB_GRP[och].COXB_MUX0, reg_mux0_temp);
            WRITE_REG(XBAR->COXB_GRP[och].COXB_MUX1, reg_mux1_temp);
            WRITE_REG(XBAR->COXB_GRP[och].COXB_ENB, reg_en_temp);
        }  // end of if (out_ch_mask & BIT_MASK(och) != 0)
    }
    return DRV_OK;
}

/**
 * @brief Configure COXB Input Channel Paramater
 *
 * @param cfg
 * @arg outDsel  output signal type select
 * @arg outPolarInvertEn  output signal polar reversal Enable or Disable
 * @param out_ch_mask  output channel valid mask
 * @return DRV_Status
 */
DRV_Status XBAR_COXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask)
{
    uint8_t ch = 0;

    assert_param(cfg != NULL);

    for (ch = 0; ch < MAX_COXB_OUTPUT_CH; ch++)
    {
        /* ch 0 ~ 13 */
        if (DRV_IS_BIT_SET(out_ch_mask, BIT_MASK(ch)))
        {
            MODIFY_REG(XBAR->COXB_DSEL, (uint32_t)0x3 << ch * 2, (uint32_t)cfg->outDsel << ch * 2);
            if (cfg->outPolarInvertEn)
            {
                SET_BIT(XBAR->COXB_OUTPOL, BIT_MASK(ch));
            }
            else
            {
                CLEAR_BIT(XBAR->COXB_OUTPOL, BIT_MASK(ch));
            }
        }
    } // end of for (uint8_t ch = 0; ch < MAX_COXB_OUTPUT_CH; ch++)
    return DRV_OK;
}

/**
 * @brief Enable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_COXB_enableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_COXB_OUTPUT_CH));
    SET_BIT(XBAR->COXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Disable output
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_COXB_disableOutputMux(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_COXB_OUTPUT_CH));
    CLEAR_BIT(XBAR->COXB_OE, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief Clear output latch status
 *
 * @param out_ch_mask  ch0~ch11 mask
 * @return DRV_Status
 */
DRV_Status XBAR_COXB_clearOutputLatch(uint16_t out_ch_mask)
{
    assert_param(out_ch_mask <= BITS_WID_MASK(MAX_COXB_OUTPUT_CH));
    SET_BIT(XBAR->COXB_LATCLR, out_ch_mask);
    return DRV_OK;
}

/**
 * @brief  Get XBAR COXB Output Channel Latch Status
 *
 * @param out_ch  ch0~ch11
 * @param latched
 * @return FlagStatus
 */
FlagStatus XBAR_COXB_getOutputChStatus(uint16_t out_ch, bool latched)
{
    FlagStatus status = RESET;
    uint32_t   val    = 0;

    assert_param(out_ch < MAX_PFXB_OUTPUT_CH);
    if (latched)
    {
        val = READ_BIT(XBAR->COXB_RPT, BIT_MASK(out_ch << XBAR_COXB_RPT_COXB_LAT_RPT_Pos));
    }
    else
    {
        val = READ_BIT(XBAR->COXB_RPT, BIT_MASK(out_ch));
    }
    status = (val != 0) ? SET : RESET;

    return status;
}

/**
 * @brief Get XBAR COXB Output All Channel Latch Status
 *
 * @param  latched  get latched status or real-time status
 * @return status with all channel
 */
uint32_t XBAR_COXB_getOutputStatus(bool latched)
{
    uint32_t val = 0;

    if (latched)
    {
        val = (READ_REG(XBAR->COXB_RPT) & XBAR_COXB_RPT_COXB_LAT_RPT_Msk) >> XBAR_COXB_RPT_COXB_LAT_RPT_Pos;
    }
    else
    {
        val = READ_REG(XBAR->COXB_RPT) & XBAR_COXB_RPT_COXB_OUT_RPT_Msk;
    }

    return val;
}
