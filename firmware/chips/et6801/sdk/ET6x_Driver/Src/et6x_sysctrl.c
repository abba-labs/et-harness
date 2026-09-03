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

#include "et6x_sysctrl.h"

/**
 * @file et6x_sysctrl.c
 *
 */

/* SYSC Global Reset Key */
#define SYSC_GLOBAL_RESET_KEY    (0x45670123UL)
/* number of handshaking interface */
#define SYSC_MAX_AHBDMA_HSIF     (8U)
/*! Parameter validity check for AHBDMA peripheral  */
#define IS_AHBDMA_PERIPHERAL(x) \
        (((x) == AHBDMA0) || ((x) == AHBDMA1))

#define IS_SYSCTRL_INT_MASKS(intflag) \
        ((intflag) <= 0x7FFFUL)

/**
 * @brief Select SYSCNT module clock source
 *
 * @param clkSrc  struct @ref SYSCTRL_SYSCNTClockSource
 * -  CRG_CLKSRC_SYSCNT_OSC25M
 * -  CRG_CLKSRC_SYSCNT_XO25M
 */
void SYSCTRL_selectSYSCNTClockSource(SYSCTRL_SYSCNTClockSource clkSrc)
{
    assert_param(clkSrc <= SYSCTRL_SYSCNT_CLKSRC_XO25M);
    MODIFY_REG(SYSC->CLK_SCNT, SYSC_CLK_SCNT_SEL_IN_Msk, (uint32_t)clkSrc << SYSC_CLK_SCNT_SEL_IN_Pos);
}

/**
 * @brief get the clock frequency of SYSCNT
 *
 * @return uint32_t
 */
uint32_t SYSCTRL_getSYSCNTClock(void)
{
    /* osc25M and xo25M */
    return(25000000U);
}

/**
 * @brief System Global Software Reset
 *
 */
__attribute__((noreturn)) void SYSCTRL_performGlobalSoftReset(void)
{
    /* unlock sysc register access */
    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
    WRITE_REG(SYSC->SYSC2CRG, SYSC_GLOBAL_RESET_KEY);
    while (1);
    /* should not run here */
}

/**
 * @brief Try to find a idle DMA channel ready to be used
 *
 * @param AHBDMAx AHBDMA peripheral pointer
 * @return uint8_t DMAMUX_INTERFACE_INVALID if all channel busy, otherwise return the first idle channel
 */
uint8_t SYSCTRL_findDMAMuxFreeInterface(AHBDMA_Type *AHBDMAx)
{
    uint8_t  index = 0;
    uint32_t reg   = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));

    if (AHBDMAx == AHBDMA0)
    {
        reg = (uint32_t)&SYSC->DMA_A_MUX[0];
    }
    else
    {
        reg = (uint32_t)&SYSC->DMA_B_MUX[0];
    }
    for (index = 0; index < SYSC_MAX_AHBDMA_HSIF; index++)
    {
        if (DRV_IS_BIT_CLR(REG32(reg + OFT_REG32 * index), SYSC_DMA_A_MUX_DMA_A_EN_Msk))
        {
            return index;
        }
    }
    return DMAMUX_INTERFACE_INVALID;
}

/**
 * @brief Configure DMA Mux for AHBDMA
 *
 * @param AHBDMAx  AHBDMA peripheral pointer
 * @param interface  DMA interface index (0~7) refer to \e DMAMUX_INTERFACE0_xxxx
 * @param reqIdx  DMA request index  refer to enum #SYSCTRL_DMAReqIdx
 * @attention before configure the DMA interface, ahbdma channel should be idle and closed
 */
void SYSCTRL_configDMAMux(AHBDMA_Type *AHBDMAx, uint8_t interface, SYSCTRL_DMAReqIdx reqIdx)
{
    uint32_t reg        = 0;
    uint8_t  interface2 = 0;
    uint32_t temp       = 0;

    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(interface <= SYSC_MAX_AHBDMA_HSIF);
    assert_param(reqIdx <= DMAMUX_REQ_QSPI_RX);

    if (AHBDMAx == AHBDMA0)
    {
        reg        = (uint32_t)&SYSC->DMA_A_MUX[0];
        interface2 = interface;
    }
    else
    {
        reg        = (uint32_t)&SYSC->DMA_B_MUX[0];
        interface2 = interface + 8;
    }

    temp = OFT_REG32 * interface;
    reg += temp;


    CLEAR_BIT(REG32(reg), SYSC_DMA_A_MUX_DMA_A_EN_Msk);
    WRITE_REG(REG32(reg), (uint8_t)reqIdx);
    SET_BIT(REG32(reg), SYSC_DMA_A_MUX_DMA_A_EN_Msk);


    if ((reqIdx == DMAMUX_REQ_DAC0) ||
        (reqIdx == DMAMUX_REQ_DAC1) ||
        (reqIdx == DMAMUX_REQ_ACMP0H_DAC0) ||
        (reqIdx == DMAMUX_REQ_ACMP0L_DAC1) ||
        (reqIdx == DMAMUX_REQ_ACMP1H_DAC0) ||
        (reqIdx == DMAMUX_REQ_ACMP1L_DAC1) ||
        (reqIdx == DMAMUX_REQ_ACMP2H_DAC0) ||
        (reqIdx == DMAMUX_REQ_ACMP2L_DAC1) ||
        (reqIdx == DMAMUX_REQ_ACMP3H_DAC0) ||
        (reqIdx == DMAMUX_REQ_ACMP3L_DAC1))
    {
        SET_BIT(SYSC->DMA_MUX_MK, BIT_MASK(interface2));
    }
}

/**
 * @brief Configures DMAUX interface request trigger mode
 *
 * @param AHBDMAx  AHBDMA peripheral pointer
 * @param interface DMA interface index (0~7)  refer to @ref DMAMUX_INTERFACE0
 * @param mode  DMA request trigger mode , refer to @ref SYSCTRL_DMAReqMode
 */
void SYSCTRL_configDMAMuxReqMode(AHBDMA_Type *AHBDMAx, uint8_t interface, SYSCTRL_DMAReqMode mode)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(interface <= SYSC_MAX_AHBDMA_HSIF);
    if (AHBDMAx == AHBDMA0)
    {
        MODIFY_REG(SYSC->DMA_MUX_MK, BIT_MASK(interface), ((uint32_t)mode << interface));
    }
    else
    {
        MODIFY_REG(SYSC->DMA_MUX_MK, BIT_MASK(interface + 8), ((uint32_t)mode << (interface + 8)));
    }
}

/**
 * @brief Free DMA Mux channel for AHBDMA
 *
 * @param AHBDMAx  AHBDMA peripheral pointer
 * @param interface  DMA interface index (0~7)  refer to @ref DMAMUX_INTERFACE0
 */
void SYSCTRL_freeDMAMuxInterface(AHBDMA_Type *AHBDMAx, uint8_t interface)
{
    assert_param(IS_AHBDMA_PERIPHERAL(AHBDMAx));
    assert_param(interface <= SYSC_MAX_AHBDMA_HSIF);

    if (AHBDMAx == AHBDMA0)
    {
        CLEAR_BIT(SYSC->DMA_A_MUX[interface], SYSC_DMA_A_MUX_DMA_A_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SYSC->DMA_B_MUX[interface], SYSC_DMA_A_MUX_DMA_A_EN_Msk);
    }
}

/**
 * @brief   configure flash deep sleep mode
 *
 * @param flash_idx  0:PFLASH0 1:PFLASH1  2:DFLASH
 * @param isPowerDown true: deep power down mode， false : work mode
 */
void SYSCTRL_configFLASHDeepPowerDown(uint32_t flash_idx, bool isPowerDown)
{
    assert_param(flash_idx <= 2);
    if (isPowerDown)
    {
        SET_BIT(SYSC->EFC, BIT_MASK(flash_idx));
    }
    else
    {
        CLEAR_BIT(SYSC->EFC, BIT_MASK(flash_idx));
    }
}

/**
 * @brief Get Dual-Bank Flash OTA mode status
 *
 * @return uint8_t
 * - 0 pflash0 and pflash1 are combined into one
 * - 1 pflash0 and pflash1 serve as backup for each other
 */
uint8_t SYSCTRL_getFLASHOTAMode(void)
{
    if (READ_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk))
    {
        return 1;
    }
    return 0;
}

/**
 * @brief Get Dual-Bank Flash BANKSWAP mode status
 *
 * @return uint8_t
 * - 0 if OTA mode = 1, pflash0 is in using
 * - 1 if OTA mode = 1, pflash1 is in using
 */
uint8_t SYSCTRL_getFLASHBankSwapMode(void)
{
    if (READ_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk))
    {
        return 1;
    }
    return 0;
}

/**
 * @brief Configure Dual-Bank Flash OTA mode
 *
 * @param enable enable or disable OTA mode
 */
void SYSCTRL_configFLASHOTAMode(bool enable)
{
    if (enable)
    {
        SET_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk);
    }
    else
    {
        CLEAR_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk);
    }
}

/**
 * @brief Configure Dual-Bank Flash BANKSWAP mode
 *
 * @param enable  enable or disable BANKSWAP mode
 */
void SYSCTRL_configFLASHBankSwapMode(bool enable)
{
    if (enable)
    {
        SET_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk);
    }
    else
    {
        CLEAR_BIT(SYSC->FLS, SYSC_FLS_BANKSWAP_Msk);
    }
}

/**
 * @brief   Enables the specified interrupt sources in the SYSC interrupt controller.
 *
 * @param   intFlags  A bitmask of interrupt sources to enable. The bitmask should be created using the
 *                    @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note    This function does not check if the provided interrupt flags are valid. It is the caller's
 *          responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 * @return  None
 */
void SYSCTRL_enableInterrupt(uint32_t intFlags)
{
    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    SET_BIT(SYSC->INT_EN, intFlags);
}

/**
 * @brief Clears the interrupt status for the specified interrupt sources in the SYSC interrupt controller.
 *
 * @param intFlags A bitmask of interrupt sources to clear the status for. The bitmask should be created using the
 *                 @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note This function does not check if the provided interrupt flags are valid. It is the caller's
 *       responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 */
void SYSCTRL_clearInterruptStatus(uint32_t intFlags)
{
    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    SET_BIT(SYSC->INT_CLR, intFlags);
}

/**
 * @brief       Get the interrupt status from the SYSC interrupt controller.
 *
 * @param[in]   intFlags  A bitmask of interrupt sources to check. The bitmask should be created using the
 *                        @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note        This function does not check if the provided interrupt flags are valid. It is the caller's
 *              responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 * @return      The interrupt status. A bit set to 1 indicates that the corresponding interrupt source is
 *              active.
 */
uint32_t SYSCTRL_getInterruptStatus(uint32_t intFlags)
{
    uint32_t intStatus = 0;

    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    intStatus = READ_REG(SYSC->INT_STATUS_RPT) & intFlags;
    return intStatus;
}

/**
 * @brief Disables the specified interrupt sources in the SYSC interrupt controller.
 *
 * @param intFlags A bitmask of interrupt sources to disable. The bitmask should be created using the
 *                 @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note This function does not check if the provided interrupt flags are valid. It is the caller's
 *       responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 */
void SYSCTRL_disableInterrupt(uint32_t intFlags)
{
    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    CLEAR_BIT(SYSC->INT_EN, intFlags);
}

/**
 * @brief Clears the interrupt mask for the specified interrupt sources in the SYSC interrupt controller.
 *
 * @param intFlags A bitmask of interrupt sources to clear the mask for. The bitmask should be created using the
 *                 @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note This function does not check if the provided interrupt flags are valid. It is the caller's
 *       responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 * @see SYSCTRL_setInterruptMask
 * @see SYSCTRL_INT_ERR_OSC25M_LOST
 */
void SYSCTRL_clearInterruptMask(uint32_t intFlags)
{
    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    CLEAR_BIT(SYSC->INT_MASK, intFlags);
}

/**
 * @brief Sets the interrupt mask for the specified interrupt sources in the SYSC interrupt controller.
 *
 * @param intFlags A bitmask of interrupt sources to set the mask for. The bitmask should be created using the
 *                 @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note This function does not check if the provided interrupt flags are valid. It is the caller's
 *       responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 * @see SYSCTRL_clearInterruptMask
 * @see SYSCTRL_INT_ERR_OSC25M_LOST
 */
void SYSCTRL_setInterruptMask(uint32_t intFlags)
{
    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    SET_BIT(SYSC->INT_MASK, intFlags);
}

/**
 * @brief       Get the raw interrupt status from the SYSC interrupt controller.
 *
 * @param[in]   intFlags  A bitmask of interrupt sources to check. The bitmask should be created using the
 *                        @ref SYSCTRL_INT_ERR_OSC25M_LOST macro.
 *
 * @note        This function does not check if the provided interrupt flags are valid. It is the caller's
 *              responsibility to ensure that the provided interrupt flags are within the valid range.
 *
 * @return      The raw interrupt status. A bit set to 1 indicates that the corresponding interrupt source is
 *              active before masking.
 *
 * @see         SYSCTRL_INT_ERR_OSC25M_LOST
 */
uint32_t SYSCTRL_getInterruptStatusRaw(uint32_t intFlags)
{
    uint32_t intStatus = 0;

    assert_param(IS_SYSCTRL_INT_MASKS(intFlags));
    intStatus = READ_REG(SYSC->INT_RAW_RPT) & intFlags;
    return intStatus;
}

/**
 * @brief enable analog voltage reference selection to internal.
 *
 * @param reference  \e reference can be a combination of the following values:
 *  - \b SYSCTRL_ANALOG_REF_2P5  default value
 *  - \b SYSCTRL_ANALOG_REF_1P65
 */
void SYSCTRL_enableAnalogReferenceInternal(uint16_t reference)
{
    if (reference == SYSCTRL_ANALOG_REF_1P65)
    {
        SET_BIT(SYSC->AFE_REF_2P5, SYSC_AFE_REF_2P5_D2A_REF2P5_SEL_Msk);
    }
    SET_BIT(SYSC->AFE_REF_2P5, SYSC_AFE_REF_2P5_D2A_REF2P5_EN_Msk);
}

/**
 * @brief disable analog voltage reference selection to internal.
 *
 */
void SYSCTRL_disableAnalogReferenceInternal(void)
{
    CLEAR_BIT(SYSC->AFE_REF_2P5, SYSC_AFE_REF_2P5_D2A_REF2P5_EN_Msk);
}

/**
 * @brief select analog signal to analog pin
 *
 * @param select analog PinMux deinfes ref to /e SYSCTL_PINMUX_C3_MUX_xxxx
 */
void SYSCTRL_selectAnalogPinMux(uint32_t select)
{
    uint16_t reg_idx = 0, mask = 0;

    reg_idx = (uint16_t)(select >> 16);
    mask    = (uint16_t)(select);

    if (reg_idx > 2)
    {
        return;
    }
    if (reg_idx == 0)
    {
        SET_BIT(SYSC->AFE_MUX_1, mask);
    }
    else
    {
        SET_BIT(SYSC->AFE_MUX_2, ((uint32_t)mask << 16 * (reg_idx - 1)));
    }
    /* enable afe mux */
    if (READ_BIT(SYSC->AFE_MUX, SYSC_AFE_MUX_D2A_AFE_MUX_EN_Msk) == 0)
    {
        SET_BIT(SYSC->AFE_MUX, SYSC_AFE_MUX_D2A_AFE_MUX_EN_Msk);
    }
}

/**
 * @brief Enable temperature sensor to ADC analog pin
 *
 */
void SYSCTRL_enableTemperatureSensor(void)
{
    /* Tsensor enable，Tsensor connect ADC0_A13 analog IO */
    SET_BIT(SYSC->AFE_REF_GEN, SYSC_AFE_REF_GEN_D2A_AFE_TESTBUF_EN_Msk | SYSC_AFE_REF_GEN_D2A_AFE_TEMPSENSOR_EN_Msk);
}

/**
 * @brief Disable temperature sensor to ADC analog pin
 *
 */
void SYSCTRL_disableTemperatureSensor(void)
{
    /* Tsensor disable，Tsensor disconnect ADC0_A13 analog IO */
    CLEAR_BIT(SYSC->AFE_REF_GEN, SYSC_AFE_REF_GEN_D2A_AFE_TESTBUF_EN_Msk | SYSC_AFE_REF_GEN_D2A_AFE_TEMPSENSOR_EN_Msk);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/
/**
 * @brief Set the system counter debug-halt route only.
 * @param[in] enabled Boolean route enable.
 * @return DRV_OK or DRV_PARAM_ERR for a non-Boolean value.
 * @note Caller owns SYSC unlock/lock. Counter HDBG and CPU run control are not changed.
 */
DRV_Status SYSCTRL_testSetSYSCNTHaltRoute(uint8_t enabled)
{
    if (enabled > 1u)
    {
        return DRV_PARAM_ERR;
    }

    MODIFY_REG(SYSC->SCNT, SYSC_SCNT_HALT_MODE_EN_Msk,
               enabled != 0u ? SYSC_SCNT_HALT_MODE_EN_Msk : 0u);
    return DRV_OK;
}

/**
 * @brief Read actual counter routes from their owning system registers.
 * @param[out] routing Clock source and Boolean halt route.
 * @return DRV_OK or DRV_PARAM_ERR for a NULL destination.
 * @note Readback is not cached and does not infer physical clock frequency or CPU halt.
 */
DRV_Status SYSCTRL_testGetSYSCNTRouting(SYSCTRL_TestSyscntRouting *routing)
{
    if (routing == NULL)
    {
        return DRV_PARAM_ERR;
    }

    routing->source = (SYSCTRL_SYSCNTClockSource)
        ((READ_REG(SYSC->CLK_SCNT) & SYSC_CLK_SCNT_SEL_IN_Msk) >> SYSC_CLK_SCNT_SEL_IN_Pos);
    routing->halt_enabled = READ_BIT(SYSC->SCNT, SYSC_SCNT_HALT_MODE_EN_Msk) != 0u;
    return DRV_OK;
}
/********************* TEST DRIVER EXTENSION END *********************/
#endif
