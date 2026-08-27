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

#ifndef __ET6X_CRG_H
#define __ET6X_CRG_H

#include "et6x.h"

#ifdef __cplusplus
extern "C"
{
#endif

/** @addtogroup ET6003_Driver
 * @{
 */

/**
 * @addtogroup  CRG
 * @{
 */

/** @defgroup CRG_OSC_VALUES Oscillator Values adaptation
 * @ingroup CRG
 * @brief    Defines used to adapt values of different oscillators
 * @note     These values could be modified in the user environment according to
 *           HW set-up.
 * @{
 */
#if !defined(HSXO_VALUE)
#define HSXO_VALUE    25000000U /*!< Value of the HSXO oscillator in Hz */
#endif                       /* HSXO_VALUE */

#if !defined(HSOSC_VALUE)
#define HSOSC_VALUE    25000000U /*!< Value of the HSOSC oscillator in Hz */
#endif                        /* HSOSC_VALUE */


#define ERR_CLK    0xFFFFFFFFU

/**
 * @}
 */


/**
 * @brief PLL Source selection
 */
typedef enum
{
    CRG_PLL_SOURCE_HSXO  = 0x00U,   /*!< external crystal oscillator 25MHz */
    CRG_PLL_SOURCE_HSOSC = 0x01U,   /*!< internal osc25MHz */
    CRG_PLL_SOURCE_LSOSC = 0x03U,   /*!< internal osc 256KHz */
} CRG_PLLSource;

/**
 * @brief PLL State selection
 *
 */
#define CRG_PLL_OFF       ((uint32_t)0x00000000U)
#define CRG_PLL_ON        ((uint32_t)0x00000001U)
#define CRG_PLL_BYPASS    ((uint32_t)0x00000002U)

/** @addtogroup CRG
 * @{
 */
typedef struct
{
    /*!<  PLL input source select @ref CRG_PLLSource */
    uint32_t PLLRefInSrc;

    /*!< The new state of the PLL.
     *   This parameter can be a value of @ref CRG_PLL_State
     */
    uint32_t PLLState;

    /*!< PLLFBDiv: Division factor for PLL VCO input clock.
     * This parameter must be a number between Min_Data = 2 and Max_Data = 63
     */
    uint32_t PLLFBDiv;

    /*!< PLLFrac: Multiplication factor for PLL VCO output clock.
     * This parameter must be a number between Min_Data = 50 and Max_Data = 432
     */
    uint32_t PLLFrac;

    /*!< PLLPostDiv1: Division factor for PLL clock.
     * This parameter must be a value of 1~7
     */
    uint32_t PLLPostDiv1;

    /*!< PLLPostDiv2: Division factor for PLL clock..
     * This parameter must be a value of 1~7
     */
    uint32_t PLLPostDiv2;

    /*!< PLLRefDiv: Division factor for reference.
     * This parameter must be a number between Min_Data = 1 and Max_Data = 63
     */
    uint32_t PLLRefDiv;
} CRG_PLLConfigParam;

/**
 * @brief CRG_PLL0_Source PLL0 Clock Source
 */
typedef enum
{
    CRG_CLKSRC_OSC25M   = 0x00U,  /*!< */
    CRG_CLKSRC_PLL_FOUT = 0x01U,  /*!< */
} CRG_ClockSource;


/**
 * @brief CRG_WDG_CLK_Source WatchDog Clock Source Select
 */
typedef enum
{
    CRG_WDG_CLKSRC_HSOSC = 0x00U,  /*!< osc25MHz */
    CRG_WDG_CLKSRC_APB1  = 0x01U   /*!< Clock Bus APB1 */
} CRG_WDGClockSource;

/**
 * @brief CRG Peripheral Gate and Reset Ctrl
 */
typedef enum
{
    /* Group 0 */
    CRG_PERIPH_EFC0     = 0x00,
    CRG_PERIPH_EFC1     = 0x01,
    CRG_PERIPH_EFC2     = 0x02,
    CRG_PERIPH_WDG0     = 0x10,
    CRG_PERIPH_WDG1     = 0x11,
    CRG_PERIPH_STM0     = 0x12,
    CRG_PERIPH_STM1     = 0x13,
    CRG_PERIPH_XBAR     = 0x14,
    CRG_PERIPH_SYSCNT   = 0x15,
    /* Group 1 */
    CRG_PERIPH_CAN0     = 0x20,
    CRG_PERIPH_CAN1     = 0x21,
    CRG_PERIPH_UART0    = 0x22,
    CRG_PERIPH_UART1    = 0x23,
    CRG_PERIPH_IIC0     = 0x24,
    CRG_PERIPH_IIC1     = 0x25,
    CRG_PERIPH_SPIM0    = 0x26,
    CRG_PERIPH_SPIM1    = 0x27,
    CRG_PERIPH_SPIM2    = 0x28,
    CRG_PERIPH_SPIS0    = 0x29,
    CRG_PERIPH_GPIO0    = 0x2a,
    CRG_PERIPH_GPIO1    = 0x2b,
    CRG_PERIPH_GPIO2    = 0x2c,
    CRG_PERIPH_GPIO3    = 0x2d,
    CRG_PERIPH_GPIO4    = 0x2e,
    CRG_PERIPH_GPIO5    = 0x2f,
    CRG_PERIPH_AHBDMA0  = 0x30,
    CRG_PERIPH_AHBDMA1  = 0x31,
    /* Group 2 */
    /* Generated ET6801 CMSIS places CORDIC0 in GTEN0/SRST0 bit 20. */
    CRG_PERIPH_CORDIC   = CRG_GTEN0_CRG_CLK_GTEN_CORDIC0_Pos,
    /* Generated ET6801 CMSIS places CRC in GTEN1/SRST1 bit 22. */
    CRG_PERIPH_CRC      = BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_CRC_Pos,
    CRG_PERIPH_QEP0     = 0x42,
    CRG_PERIPH_QEP1     = 0x43,
    CRG_PERIPH_SDFM0    = 0x44,
    CRG_PERIPH_SDFM1    = 0x45,
    CRG_PERIPH_SDFM2    = 0x46,
    CRG_PERIPH_SDFM3    = 0x47,
    CRG_PERIPH_SDFM4    = 0x48,
    CRG_PERIPH_SDFM5    = 0x49,
    CRG_PERIPH_SDFM6    = 0x4a,
    CRG_PERIPH_SDFM7    = 0x4b,
    CRG_PERIPH_ADC0     = 0x4c,
    CRG_PERIPH_ADC1     = 0x4d,
    CRG_PERIPH_ADC2     = 0x4e,
    CRG_PERIPH_ACMP0    = 0x4f,
    CRG_PERIPH_ACMP1    = 0x50,
    CRG_PERIPH_ACMP2    = 0x51,
    CRG_PERIPH_ACMP3    = 0x52,
    CRG_PERIPH_DAC0     = 0x53,
    CRG_PERIPH_DAC1     = 0x54,
    CRG_PERIPH_ETIM     = 0x55,
    CRG_PERIPH_WAG      = 0x56,
    /* Group 3 */
    CRG_PERIPH_SRPWM0   = 0x60,
    CRG_PERIPH_SRPWM1   = 0x61,
    CRG_PERIPH_SRPWM2   = 0x62,
    CRG_PERIPH_SRPWM3   = 0x63,
    CRG_PERIPH_SRPWM4   = 0x64,
    CRG_PERIPH_SRPWM5   = 0x65,
    CRG_PERIPH_SRPWM6   = 0x66,
    CRG_PERIPH_SRPWM7   = 0x67,
    CRG_PERIPH_SRPWM8   = 0x68,
    CRG_PERIPH_SRPWM9   = 0x69,
    CRG_PERIPH_SRPWM10  = 0x6a,
    CRG_PERIPH_SRPWM11  = 0x6b,
    CRG_PERIPH_SRPWMCOM = 0x6c,
    /* Generated ET6801 CMSIS places AES/FMAC in GTEN1/SRST1 bits 24/23. */
    CRG_PERIPH_AES      = BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_AES_Pos,
    CRG_PERIPH_FMAC     = BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_FMAC_Pos
} CRG_Peripherals;



/**
 * @brief  CRG System, AHB and APB busses clock configuration structure definition
 */
typedef struct __PACKED
{
    /*!< The BUS clock (BUSCLK) divider. This clock is derived from the CPU clock (CPUCLK).
     *    This parameter can be a value of 1/2
     */
    uint8_t BUSCLKDivider;

    /*!< The APB clock (APBCLK) divider. This clock is derived from the bus clock (BUSCLK).
     *   This parameter can be a value of 1/2/4/6/8
     */
    uint8_t APBCLKDivider;

    /*!< The APB3 clock (APB3CLK) divider. This clock is derived from the bus clock
     * (BUSCLK).
     *  This parameter can be a value of 1/2
     * */
    uint8_t APB3CLKDivider;

    /*!< The EFC clock (EFCCLK) divider. This clock is derived from the BUS clock (BUSCLK).
     *    This parameter can be a value of 1/2
     */
    uint8_t EFCCLKDivider;

    /*!< The CAN clock (CANCLK) divider. This clock is derived from the PLL1 clock (PLL1CLK).
     *    This parameter can be a value of 2/3/4/5
     */
    uint8_t CANCLKDivider;

    /*!< The ADC DAC clock (ADDACLK) divider. This clock is derived from the PLL0 clock
     * (PLL0CLK).
     *   This parameter can be a value of 1/2/4/6/8/12
     * */
    uint8_t ADDACLKDivider;

    /*!< The AES clock (AESCLK) divider. This clock is derived from the PLL0 clock
     * (PLL0CLK).
     *   This parameter can be a value of 1/2/4/6/8/12
     * */
    uint8_t CANCLKSrcSel;
} CRG_ClockConfigParam;

void CRG_lockClockConfig(void);
void CRG_unlockClockConfig(void);

void CRG_resetPeripheral(CRG_Peripherals periph);
void CRG_enablePeripheral(CRG_Peripherals periph);
void CRG_disablePeripheral(CRG_Peripherals periph);

/* other peripheral clock source select */
void CRG_selectWDGClockSource(WDG_Type *WDGx, CRG_WDGClockSource clkSrc, uint8_t clkDiv);

/* PLL/BUS/Modules Clk Get */
uint32_t CRG_getCPUClock(void);
uint32_t CRG_getBUSClock(void);
uint32_t CRG_getAPBClock(void);
uint32_t CRG_getAPB3Clock(void);
uint32_t CRG_getCANClock(void);
uint32_t CRG_getWDGClock(WDG_Type *WDGx);

DRV_Status CRG_setClockDivConfig(const CRG_ClockConfigParam *clkInitStruct);
DRV_Status CRG_setPLLConfig(const CRG_PLLConfigParam *pllInitStruct, uint32_t timeout);
DRV_Status CRG_setClockOutSource(CRG_ClockSource source);
FlagStatus CRG_isClockSrcPLL(void);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Read the reviewed WDG clock source and encoded divider fields.
 * @note This test-only extension separates the source readback from the
 *       legacy CRG_getWDGClock frequency helper. It is not an SDK release API.
 */
typedef struct
{
    uint8_t source;
    uint8_t divider;
    uint8_t reserved[2];
} CRG_TestWdgClockSnapshot;

DRV_Status CRG_testGetWDGClockConfig(WDG_Type *WDGx, CRG_TestWdgClockSnapshot *snapshot);

/********************* TEST DRIVER EXTENSION END *********************/

#endif


/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /*__ET6X_CRG_H */
