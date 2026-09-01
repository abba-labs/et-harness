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
#include "et6x_crg.h"
#include "et6x_cortex.h"
/* Timeout value */
#define PLLLOCK_TIMEOUT_VALUE          (0xFFFFFFUL)

#define CRG_WDG_MAX_PRESCALER_VALUE    (63)

/**
 * @brief lock write reg to CRG register
 *
 */
void CRG_lockClockConfig(void)
{
    WRITE_REG(CRG->KEY_CTRL, 0x12345678);
}

/**
 * @brief unlock write reg to CRG register
 *
 */
void CRG_unlockClockConfig(void)
{
    WRITE_REG(CRG->KEY_CTRL, 0x7879a8a9);
}

/**
 * @brief Check System Clock Source from PLL
 *
 * @return FlagStatus
 */
FlagStatus CRG_isClockSrcPLL(void)
{
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        return SET;
    }
    return RESET;
}

/**
 * @brief  Configure PLL out
 * @param  [in] pllInitStruct PLL params to be setting
 * @param  [in] timeout  timeout for PLL stable
 * @retval DRV_Status:
 *           - DRV_OK:          Configure success.
 *           - DRV_ERROR:       Configure fail.
 */
DRV_Status CRG_setPLLConfig(const CRG_PLLConfigParam *pllInitStruct, uint32_t timeout)
{
    uint32_t continus_cnt = 0;

    if (!pllInitStruct)
    {
        return DRV_ERROR;
    }

    if (pllInitStruct->PLLRefInSrc > CRG_PLL_SOURCE_HSOSC)
    {
        return DRV_ERROR;
    }

    MODIFY_REG(CRG->PLLREF_CFG, CRG_PLLREF_CFG_CRG_PLL_REF_SEL_Msk,
               (uint32_t)pllInitStruct->PLLRefInSrc << CRG_PLLREF_CFG_CRG_PLL_REF_SEL_Pos);
    /* 1. set pll div  */
    MODIFY_REG(CRG->CFG0, CRG_CFG0_CRG_PLL_FBDIV_Msk,
               pllInitStruct->PLLFBDiv << CRG_CFG0_CRG_PLL_FBDIV_Pos);
//    MODIFY_REG(CRG->CFG1, CRG_PLL_CFG1_CRG_PLL_FRAC_Msk, pllInitStruct->PLLFrac << CRG_PLL_CFG1_CRG_PLL_FRAC_Pos);
    MODIFY_REG(CRG->CFG0, CRG_CFG0_CRG_PLL_POSTDIV1_Msk,
               pllInitStruct->PLLPostDiv1 << CRG_CFG0_CRG_PLL_POSTDIV1_Pos);
    MODIFY_REG(CRG->CFG0, CRG_CFG0_CRG_PLL_POSTDIV2_Msk,
               pllInitStruct->PLLPostDiv2 << CRG_CFG0_CRG_PLL_POSTDIV2_Pos);
//    MODIFY_REG(CRG->CFG0, CRG_CFG0_CRG_PLL_REFDIV_Msk,
//               pllInitStruct->PLLRefDiv << CRG_CFG0_CRG_PLL_REFDIV_Pos);

    /* 2. check pll new state */
    if (pllInitStruct->PLLState == CRG_PLL_OFF)
    {
        SET_BIT(CRG->CFG0, CRG_CFG0_CRG_PLL_PD_Msk);
    }
    else if (pllInitStruct->PLLState == CRG_PLL_BYPASS)
    {
        SET_BIT(CRG->CFG0, CRG_CFG0_CRG_PLL_BYPASS_Msk);
        SET_BIT(CRG->CFG0, CRG_CFG0_CRG_PLL_PD_Msk);
    }
    else
    {
        CLEAR_BIT(CRG->CFG0, CRG_CFG0_CRG_PLL_PD_Msk);
    }
    /* 3. Wait till PLLx is locked */
    if (pllInitStruct->PLLState != CRG_PLL_OFF)
    {
        do
        {
            /* clear clk lost record */
            SYSC->DIG_REC = 0x1F;
            DELAY_US(1);
            if (((SYSC->DIG_STS & SYSC_DIG_STS_PLL0_UNLOCK_STS_Msk) == RESET) &&
                ((SYSC->DIG_REC & SYSC_DIG_REC_PLL0_UNLOCK_REC_Msk) == RESET))
            {
                continus_cnt++;
                if (continus_cnt >= 5)
                {
                    return DRV_OK;
                }
            }
            else
            {
                continus_cnt = 0;
            }
        } while (--timeout > 0);
        return DRV_TIMEOUT;
    }
    return DRV_OK;
}

/**
 * @brief Find LCM in dividers
 *
 * @param diva
 * @param divb
 * @param divc
 * @return uint32_t
 */
static uint32_t CRG_calcBusClkLCM(uint8_t diva, uint8_t divb, uint8_t divc)
{
    uint8_t max = 0;

    max = (diva > divb) ? diva : divb;
    max = (divc > max) ? divc : max;

    do
    {
        if ((max % diva == 0) && (max % divb == 0) && (max % divc == 0))
        {
            break;
        }
        max++;
    } while (1);

    return max;
}

/**
 * @brief  Configure BUS and CPU Clock Div
 * @param  [in] clkInitStruct Clock Div params to be setting
 * @retval DRV_Status:
 *           - DRV_OK:          Configure success.
 *           - DRV_ERROR:       Configure fail.
 */
DRV_Status CRG_setClockDivConfig(const CRG_ClockConfigParam *clkInitStruct)
{
    uint32_t i = 0;

    if (!clkInitStruct)
    {
        return DRV_ERROR;
    }
    /* 1. PLL0 domain sub clk select */
//    MODIFY_REG(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_CLK_CAN_CORE_Msk,
//               (uint32_t)clkInitStruct->CANCLKSrcSel << CRG_PLLCLK_CFG0_CRG_SEL_CLK_CAN_CORE_Pos);

//    /* 2. PLL0 domain sub clk div */
//    MODIFY_REG(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_DIV_CAN_CORE_Msk,
//               (uint32_t)clkInitStruct->CANCLKDivider << CRG_PLLCLK_CFG0_CRG_DIV_CAN_CORE_Pos);
//    MODIFY_REG(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_DIV_PBUS3_Msk,
//               (uint32_t)clkInitStruct->APB3CLKDivider << CRG_PLLCLK_CFG0_CRG_DIV_PBUS3_Pos);

//    MODIFY_REG(CRG->PLLCLK_CFG1, CRG_PLLCLK_CFG1_CRG_DIV_EFC_Msk,
//               (uint32_t)clkInitStruct->EFCCLKDivider << CRG_PLLCLK_CFG1_CRG_DIV_EFC_Pos);

    MODIFY_REG(CRG->PLLCLK_CFG1, CRG_PLLCLK_CFG1_CRG_DIV_APB_Msk,
               (uint32_t)clkInitStruct->APBCLKDivider << CRG_PLLCLK_CFG1_CRG_DIV_APB_Pos);

    MODIFY_REG(CRG->PLLCLK_CFG1, CRG_PLLCLK_CFG1_CRG_DIV_SARC_ADC_Msk,
               (uint32_t)clkInitStruct->ADDACLKDivider << CRG_PLLCLK_CFG1_CRG_DIV_SARC_ADC_Pos);

    MODIFY_REG(CRG->PLLCLK_CFG1, CRG_PLLCLK_CFG1_CRG_DIV_BUS_Msk,
               (uint32_t)clkInitStruct->BUSCLKDivider << CRG_PLLCLK_CFG1_CRG_DIV_BUS_Pos);

    /* calc lcm */
    i = CRG_calcBusClkLCM(clkInitStruct->APBCLKDivider + 1, clkInitStruct->ADDACLKDivider + 1,
                          clkInitStruct->EFCCLKDivider + 1) - 1;

    /* 3. update LCM */
    MODIFY_REG(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_DIV_BUS_LCM_Msk, i << CRG_PLLCLK_CFG0_CRG_DIV_BUS_LCM_Pos);

    /* 4. update PLL0 div */
    SET_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_DIV_PLL_UPDATE_Msk);
    for (i = 0; i < 0xF; i++)
    {
    }
    CLEAR_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_DIV_PLL_UPDATE_Msk);
    return DRV_OK;
}

/**
 * @brief Configure PLL0 Fout Clock Source Select
 *
 * @param clkInitStruct
 * @return DRV_Status
 */
DRV_Status CRG_setClockOutSource(CRG_ClockSource source)
{
    assert_param(source <= CRG_CLKSRC_PLL_FOUT);

    /* pll source select */
    MODIFY_REG(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk,
               (uint32_t)source << CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Pos);

    return DRV_OK;
}

/**
 * @brief  CRG Peripheral SoftReset Assert
 * @param  periph: Peripheral Number. Such as CRG_SRST_SRPWM0
 * @retval Void
 */
static void CRG_PeriphReset_Assert(CRG_Peripherals periph)
{
    uint32_t reg_addr = 0;

    assert_param(periph <= CRG_PERIPH_SRPWMCOM);

    reg_addr = (uint32_t)(&CRG->SRST0) + (periph / BITS_DWORD) * OFT_REG32;
    CLEAR_BIT(REG32(reg_addr), BIT_MASK(periph % BITS_DWORD));
}

/**
 * @brief  CRG Peripheral SoftReset Dessert
 * @param  periph: Peripheral Number. Such as CRG_SRST_SPWM0
 * @note   default, only few modules dessert reset when power up.
 *         if want this module work, must call this function to dessert reset
 * @retval Void
 */
static void CRG_PeriphReset_Dessert(CRG_Peripherals periph)
{
    uint32_t reg_addr = 0;

    assert_param(periph <= CRG_PERIPH_SRPWMCOM);

    reg_addr = (uint32_t)(&CRG->SRST0) + (periph / BITS_DWORD) * OFT_REG32;
    SET_BIT(REG32(reg_addr), BIT_MASK(periph % BITS_DWORD));
}

/**
 * @brief Software Reset Modules
 *
 * @param periph Module Reset Index
 */
void CRG_resetPeripheral(CRG_Peripherals periph)
{
    uint32_t dly = 0;

    CRG_PeriphReset_Assert(periph);
    for (dly = 0; dly < 0xFFFF; dly++)
    {
    }
    CRG_PeriphReset_Dessert(periph);
}

/**
 * @brief  CRG Peripheral Clock Enable
 *
 * @param periph   Peripheral index in struct CRG_Peripherals
 */
void CRG_enablePeripheral(CRG_Peripherals periph)
{
    uint32_t reg_addr = 0;

    assert_param(periph <= CRG_PERIPH_SRPWMCOM);

    reg_addr = (uint32_t)(&CRG->GTEN0) + (periph / BITS_DWORD) * OFT_REG32;
    SET_BIT(REG32(reg_addr), BIT_MASK(periph % BITS_DWORD));
}

/**
 * @brief  CRG Peripheral Clock Disable
 *
 * @param periph   Peripheral index in struct CRG_Peripherals
 */
void CRG_disablePeripheral(CRG_Peripherals periph)
{
    uint32_t reg_addr = 0;

    assert_param(periph <= CRG_PERIPH_SRPWMCOM);

    reg_addr = (uint32_t)(&CRG->GTEN0) + (periph / BITS_DWORD) * OFT_REG32;
    CLEAR_BIT(REG32(reg_addr), BIT_MASK(periph % BITS_DWORD));
}

/**
 * @brief Select Watchdog module clock source
 *
 * @param Wdg  WDG0 or WDG1
 * @param clkSrc  struct @ref CRG_WDGCLKSRCTypeDef
 * @param clkDiv  only valid when clkSrc is APB1
 *                range: [0~63]
 * @attention before configure clock source ,should deinit WDGx module
 */
void CRG_selectWDGClockSource(WDG_Type *WDGx, CRG_WDGClockSource clkSrc, uint8_t clkDiv)
{
    assert_param((WDGx == WDG0) || (WDGx == WDG1));
    assert_param(clkSrc <= CRG_WDG_CLKSRC_APB1);
    assert_param(clkDiv <= CRG_WDG_MAX_PRESCALER_VALUE);

    if (WDGx == WDG0)
    {
        MODIFY_REG(CRG->PLLCLK_CFG3, CRG_PLLCLK_CFG3_CRG_WDG0_SEL_Msk,
                   (uint32_t)clkSrc << CRG_PLLCLK_CFG3_CRG_WDG0_SEL_Pos);
    }
    else if (WDGx == WDG1)
    {
        MODIFY_REG(CRG->PLLCLK_CFG3, CRG_PLLCLK_CFG3_CRG_WDG1_SEL_Msk,
                   (uint32_t)clkSrc << CRG_PLLCLK_CFG3_CRG_WDG1_SEL_Pos);
    }
    if (clkSrc == CRG_WDG_CLKSRC_APB1)
    {
        if (WDGx == WDG0)
        {
            MODIFY_REG(CRG->PLLCLK_CFG3, CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk,
                       (uint32_t)clkDiv << CRG_PLLCLK_CFG3_CRG_WDG0_STB_Pos);
        }
        else if (WDGx == WDG1)
        {
            MODIFY_REG(CRG->PLLCLK_CFG3, CRG_PLLCLK_CFG3_CRG_WDG1_STB_Msk,
                       (uint32_t)clkDiv << CRG_PLLCLK_CFG3_CRG_WDG1_STB_Pos);
        }
    }
}

/**
 * @brief Get PLL CLK out
 *
 * @return uint32_t
 */
static uint32_t CRG_getPllFOut(void)
{
    uint32_t pll0fout = 0, pllfbdiv = 1, pllrefdiv = 1, pllpostdiv1 = 1, pllpostdiv2 = 1;

    /* Get PLL Fout Sel -------------------------------------------------------*/
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
//        pllfbdiv    = (CRG->PLL.CFG0 & CRG_PLL_CFG0_CRG_PLL_FBDIV_Msk) >> CRG_PLL_CFG0_CRG_PLL_FBDIV_Pos;
//        pllpostdiv1 = (CRG->PLL.CFG0 & CRG_PLL_CFG0_CRG_PLL_POSTDIV1_Msk) >> CRG_PLL_CFG0_CRG_PLL_POSTDIV1_Pos;
//        pllpostdiv2 = (CRG->PLL.CFG0 & CRG_PLL_CFG0_CRG_PLL_POSTDIV2_Msk) >> CRG_PLL_CFG0_CRG_PLL_POSTDIV2_Pos;
//        pllrefdiv   = (CRG->PLL.CFG0 & CRG_PLL_CFG0_CRG_PLL_REFDIV_Msk) >> CRG_PLL_CFG0_CRG_PLL_REFDIV_Pos;
        /* not considered to used gpio pll ref source case  */
        pll0fout = (HSOSC_VALUE / pllrefdiv) * pllfbdiv / pllpostdiv1 / pllpostdiv2 / 2;
    }
    else
    {
        pll0fout = HSOSC_VALUE;
    }
    return pll0fout;
}

/**
 * @brief
 *
 * @return uint32_t
 */
uint32_t CRG_getCPUClock(void)
{
    uint32_t cpuclk = 0, regVal = 0;

#if defined(FPGA_VERSION)
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        cpuclk = (uint32_t)(HSOSC_VALUE * 2);  // 50MHz;
    }
    else
    {
        cpuclk = HSOSC_VALUE;
    }
#else
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        cpuclk = (uint32_t)(CRG_getPllFOut() / 2);  //300MHz;
    }
    else
    {
        cpuclk = HSOSC_VALUE;
    }
#endif
    regVal = READ_REG(CRG->PLLCLK_CFG2);
    cpuclk = cpuclk / (((regVal & CRG_PLLCLK_CFG1_CRG_DIV_BUS_Msk) >> CRG_PLLCLK_CFG1_CRG_DIV_BUS_Pos) + 1);

    return cpuclk;
}

/**
 * @brief
 *
 * @return uint32_t
 */
uint32_t CRG_getBUSClock(void)
{
    uint32_t busclk = 0, regVal = 0;

    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        busclk = CRG_getPllFOut() / 3;
    }
    else
    {
        busclk = CRG_getPllFOut();
    }
    regVal = READ_REG(CRG->PLLCLK_CFG1);
    busclk = busclk / (((regVal & CRG_PLLCLK_CFG1_CRG_DIV_BUS_Msk) >> CRG_PLLCLK_CFG1_CRG_DIV_BUS_Pos) + 1);
    return busclk;
}

/**
 * @brief Get APBBUS Clock Frequency(RTC/WDG/STIM/PTIM)
 *
 * @return uint32_t ABPBus3 Clock Frequency
 */
uint32_t CRG_getAPBClock(void)
{
    uint32_t apbClk = 0, regVal = 0;

#if defined(FPGA_VERSION)
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        apbClk = (uint32_t)(HSOSC_VALUE * 2);
    }
    else
    {
        apbClk = (uint32_t)(HSOSC_VALUE);
    }
    UNUSED(regVal);
#else
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        apbClk = CRG_getBUSClock();
    }
    else
    {
        apbClk = (uint32_t)(HSOSC_VALUE);
    }
    regVal = READ_REG(CRG->PLLCLK_CFG1);
    apbClk = apbClk / (((regVal & CRG_PLLCLK_CFG1_CRG_DIV_APB_Msk) >> CRG_PLLCLK_CFG1_CRG_DIV_APB_Pos) + 1);
#endif
    return apbClk;
}

/**
 * @brief Get ABPBus3 Clock Frequency(UART/I2C/SPI)
 *
 * @return uint32_t ABPBus3 Clock Frequency
 */
uint32_t CRG_getAPB3Clock(void)
{
    uint32_t apbClk = 0, regVal = 0;

#if defined(FPGA_VERSION)
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        apbClk = (uint32_t)(HSOSC_VALUE * 2);
    }
    else
    {
        apbClk = (uint32_t)(HSOSC_VALUE);
    }
    UNUSED(regVal);
#else
    if (READ_BIT(CRG->PLLCLK_CFG0, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        apbClk = CRG_getBUSClock();
    }
    else
    {
        apbClk = (uint32_t)(HSOSC_VALUE);
    }
    regVal = READ_REG(CRG->PLLCLK_CFG0);
    apbClk = apbClk / (((regVal & CRG_PLLCLK_CFG0_CRG_DIV_PBUS3_Msk) >> CRG_PLLCLK_CFG0_CRG_DIV_PBUS3_Pos) + 1);
#endif
    return apbClk;
}

/**
 * @brief Get CAN Core Clock Frequency
 *
 * @return uint32_t
 */
uint32_t CRG_getCANClock(void)
{
    uint32_t canClk = 0, regVal = 0;

    regVal = READ_REG(CRG->PLLCLK_CFG0);
#if defined(FPGA_VERSION)
    UNUSED(regVal);
    canClk = 40000000U;
#else
    if (READ_BIT(regVal, CRG_PLLCLK_CFG0_CRG_SEL_OSC25M_PLL_Msk) != 0)
    {
        if (regVal & CRG_PLLCLK_CFG0_CRG_SEL_CLK_CAN_CORE_Msk)
        {
            canClk = CRG_getCPUClock();
        }
        else
        {
            canClk = CRG_getBUSClock();
        }
    }
    else
    {
        canClk = HSOSC_VALUE;
    }
    canClk = canClk / (((regVal & CRG_PLLCLK_CFG0_CRG_DIV_CAN_CORE_Msk) >> CRG_PLLCLK_CFG0_CRG_DIV_CAN_CORE_Pos) + 1);
#endif
    return canClk;
}

/**
 * @brief get the clock frequency of WDG
 *
 * @param WDGx WDG0 or WDG1
 * @return uint32_t
 */
uint32_t CRG_getWDGClock(WDG_Type *WDGx)
{
    uint32_t wdgClk = 0, regVal = 0;

    regVal = READ_REG(CRG->PLLCLK_CFG0);
#if defined(FPGA_VERSION)
    UNUSED(regVal);
    UNUSED(WDGx);
    wdgClk = HSOSC_VALUE;
#else
    if (WDGx == WDG0)
    {
        if (regVal & CRG_PLLCLK_CFG3_CRG_WDG0_SEL_Msk)
        {
            wdgClk = HSOSC_VALUE;
        }
        else
        {
            wdgClk = CRG_getAPBClock();
            wdgClk = wdgClk / (((regVal & CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk) >> CRG_PLLCLK_CFG3_CRG_WDG0_STB_Pos) + 1);
        }
    }
    else if (WDGx == WDG1)
    {
        if (regVal & CRG_PLLCLK_CFG3_CRG_WDG1_SEL_Msk)
        {
            wdgClk = HSOSC_VALUE;
        }
        else
        {
            wdgClk = CRG_getAPBClock();
            wdgClk = wdgClk / (((regVal & CRG_PLLCLK_CFG3_CRG_WDG1_STB_Msk) >> CRG_PLLCLK_CFG3_CRG_WDG1_STB_Pos) + 1);
        }
    }
#endif
    return wdgClk;
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Read the WDG source and divider fields from the CRG configuration register.
 * @param[in] WDGx WDG0 or WDG1 whose CRG clock selection is requested.
 * @param[out] snapshot Destination for source and encoded divider values.
 * @return DRV_OK on success, otherwise DRV_PARAM_ERR.
 * @note This extension deliberately reads PLLCLK_CFG3, the register written by
 *       CRG_selectWDGClockSource. It does not use the legacy frequency getter.
 */
DRV_Status CRG_testGetWDGClockConfig(WDG_Type *WDGx, CRG_TestWdgClockSnapshot *snapshot)
{
    uint32_t reg_val;

    if ((WDGx == NULL) || (snapshot == NULL) || ((WDGx != WDG0) && (WDGx != WDG1)))
    {
        return DRV_PARAM_ERR;
    }

    reg_val = READ_REG(CRG->PLLCLK_CFG3);

    if (WDGx == WDG0)
    {
        snapshot->source = (uint8_t)((reg_val & CRG_PLLCLK_CFG3_CRG_WDG0_SEL_Msk) >>
                                     CRG_PLLCLK_CFG3_CRG_WDG0_SEL_Pos);
        snapshot->divider = (uint8_t)((reg_val & CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk) >>
                                      CRG_PLLCLK_CFG3_CRG_WDG0_STB_Pos);
    }
    else
    {
        snapshot->source = (uint8_t)((reg_val & CRG_PLLCLK_CFG3_CRG_WDG1_SEL_Msk) >>
                                     CRG_PLLCLK_CFG3_CRG_WDG1_SEL_Pos);
        snapshot->divider = (uint8_t)((reg_val & CRG_PLLCLK_CFG3_CRG_WDG1_STB_Msk) >>
                                      CRG_PLLCLK_CFG3_CRG_WDG1_STB_Pos);
    }

    snapshot->reserved[0] = 0u;
    snapshot->reserved[1] = 0u;

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif
