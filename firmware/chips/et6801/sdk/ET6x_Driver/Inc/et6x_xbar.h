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

#ifndef __ET6X_XBAR_H
#define __ET6X_XBAR_H

#include "et6x.h"

#ifdef __cplusplus
extern "C"
{
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup XBAR
 * @{
 */
/* ===================================================================================================================*/
/* ================                         XBAR Input Source  Declarations                          ================ */
/* ===================================================================================================================*/


/**
 * @brief Input XBAR  Source enumeration
 */
typedef enum
{
    INXB_SRC_GPIOA_GPIO0,   /*!< Input XBAR Source GPIOA~GPIOE */
    INXB_SRC_GPIOA_GPIO1,
    INXB_SRC_GPIOA_GPIO2,
    INXB_SRC_GPIOA_GPIO3,
    INXB_SRC_GPIOA_GPIO4,
    INXB_SRC_GPIOA_GPIO5,
    INXB_SRC_GPIOA_GPIO6,
    INXB_SRC_GPIOA_GPIO7,
    INXB_SRC_GPIOA_GPIO8,
    INXB_SRC_GPIOA_GPIO9,
    INXB_SRC_GPIOA_GPIO10,
    INXB_SRC_GPIOA_GPIO11,
    INXB_SRC_GPIOA_GPIO12,
    INXB_SRC_GPIOA_GPIO13,
    INXB_SRC_GPIOA_GPIO14,
    INXB_SRC_GPIOB_GPIO15,
    INXB_SRC_GPIOB_GPIO16,
    INXB_SRC_GPIOB_GPIO17,
    INXB_SRC_GPIOB_SWCLK,
    INXB_SRC_GPIOB_SWDIO,
    INXB_SRC_GPIOB_GPIO20,
    INXB_SRC_GPIOB_GPIO21,
    INXB_SRC_GPIOB_GPIO22,
    INXB_SRC_GPIOB_GPIO23,
    INXB_SRC_GPIOB_GPIO24,
    INXB_SRC_GPIOB_GPIO25,
    INXB_SRC_GPIOB_GPIO26,
    INXB_SRC_GPIOB_GPIO27,
    INXB_SRC_GPIOB_GPIO28,
    INXB_SRC_GPIOB_GPIO29,
    INXB_SRC_GPIOB_GPIO30,
    INXB_SRC_GPIOB_GPIO31,
    INXB_SRC_GPIOC_GPIO32,
    INXB_SRC_GPIOC_GPIO33,
    INXB_SRC_GPIOC_GPIO34,
    INXB_SRC_GPIOC_GPIO35,
    // INXB_SRC_GPIOC_GPIO36,
    INXB_SRC_GPIOC_GPIO37,
    // INXB_SRC_GPIOC_GPIO38,
    INXB_SRC_GPIOC_GPIO39,
    INXB_SRC_GPIOC_GPIO40,
    INXB_SRC_GPIOC_GPIO41,
    INXB_SRC_GPIOC_GPIO42,
    INXB_SRC_GPIOC_GPIO43,
    INXB_SRC_GPIOC_GPIO44,
    INXB_SRC_GPIOC_GPIO45,
    INXB_SRC_GPIOC_GPIO46,
    INXB_SRC_GPIOC_GPIO47,
    INXB_SRC_GPIOC_GPIO48,
    INXB_SRC_GPIOC_GPIO49,
    INXB_SRC_GPIOD_GPIO50,
    INXB_SRC_GPIOD_GPIO51,
    INXB_SRC_GPIOD_GPIO52,
    INXB_SRC_GPIOD_GPIO53,
    INXB_SRC_GPIOD_GPIO54,
    INXB_SRC_GPIOD_GPIO55,
    INXB_SRC_GPIOD_GPIO56,
    INXB_SRC_GPIOD_GPIO57,
    INXB_SRC_GPIOD_GPIO58,
    INXB_SRC_GPIOD_GPIO59,
    INXB_SRC_GPIOD_GPIO60,
    INXB_SRC_GPIOD_GPIO61,
    INXB_SRC_GPIOD_GPIO62,
    INXB_SRC_GPIOD_GPIO63,
    INXB_SRC_GPIOD_GPIO64,
    INXB_SRC_GPIOD_GPIO65,
    INXB_SRC_GPIOE_GPIO66,
    INXB_SRC_GPIOE_GPIO67,
    INXB_SRC_GPIOE_GPIO68,
    INXB_SRC_GPIOE_GPIO69,
    INXB_SRC_GPIOE_GPIO70,
    INXB_SRC_GPIOE_GPIO71,
    INXB_SRC_GPIOE_GPIO72,
    INXB_SRC_GPIOE_GPIO73,
    INXB_SRC_GPIOE_GPIO74,
    INXB_SRC_GPIOE_GPIO75,
    INXB_SRC_GPIOE_GPIO76,
    INXB_SRC_GPIOE_GPIO77,
    INXB_SRC_GPIOE_GPIO78,
    INXB_SRC_GPIOE_GPIO79,
    INXB_SRC_GPIOE_GPIO80,
    INXB_SRC_GPIOE_GPIO81
} XBAR_INXB_SRC_TypeDef;             /*!< 80 channel input */

/**
 * @brief SrPWM Fault and SrPWM Sync XBAR Source enumeration
 */
typedef enum
{
    PFXB_SRC_MUX00_CMP_EVT0 = 0,
    PFXB_SRC_MUX00_CMP_EVT0_OR_EVT1,
    PFXB_SRC_MUX00_ADCA_EVT0,
    PFXB_SRC_MUX00_RESERVED,
    PFXB_SRC_MUX01_CMP_EVT1,
    PFXB_SRC_MUX01_INPUTXBAR0,
    PFXB_SRC_MUX01_ADCA_EVT1,
    PFXB_SRC_MUX01_ETIMOUT0,
    PFXB_SRC_MUX02_CMP_EVT2,
    PFXB_SRC_MUX02_CMP_EVT2_OR_EVT3,
    PFXB_SRC_MUX02_ADCA_EVT2,
    PFXB_SRC_MUX02_RESERVED,
    PFXB_SRC_MUX03_CMP_EVT3,
    PFXB_SRC_MUX03_INPUTXBAR1,
    PFXB_SRC_MUX03_ADCA_EVT3,
    PFXB_SRC_MUX03_ETIMOUT1,
    PFXB_SRC_MUX04_CMP_EVT4,
    PFXB_SRC_MUX04_CMP_EVT4_OR_EVT5,
    PFXB_SRC_MUX04_ADCB_EVT0,
    PFXB_SRC_MUX04_RESERVED,
    PFXB_SRC_MUX05_CMP_EVT5,
    PFXB_SRC_MUX05_INPUTXBAR2,
    PFXB_SRC_MUX05_ADCB_EVT1,
    PFXB_SRC_MUX05_ETIMOUT2,
    PFXB_SRC_MUX06_CMP_EVT6,
    PFXB_SRC_MUX06_CMP_EVT6_OR_EVT7,
    PFXB_SRC_MUX06_ADCB_EVT2,
    PFXB_SRC_MUX06_RESERVED,
    PFXB_SRC_MUX07_CMP_EVT7,
    PFXB_SRC_MUX07_INPUTXBAR3,
    PFXB_SRC_MUX07_ADCB_EVT3,
    PFXB_SRC_MUX07_ETIMOUT3,
    PFXB_SRC_MUX08_RESERVED,
    PFXB_SRC_MUX08_RESERVED1,
    PFXB_SRC_MUX08_ADCC_EVT0,
    PFXB_SRC_MUX08_RESERVED2,
    PFXB_SRC_MUX09_RESERVED,
    PFXB_SRC_MUX09_INPUTXBAR4,
    PFXB_SRC_MUX09_ADCC_EVT1,
    PFXB_SRC_MUX09_ETIMOUT4,
    PFXB_SRC_MUX10_RESERVED,
    PFXB_SRC_MUX10_ADCSOCAO,
    PFXB_SRC_MUX10_ADCC_EVT2,
    PFXB_SRC_MUX10_RESERVED1,
    PFXB_SRC_MUX11_RESERVED,
    PFXB_SRC_MUX11_INPUTXBAR5,
    PFXB_SRC_MUX11_ADCC_EVT3,
    PFXB_SRC_MUX11_RESERVED1,
    PFXB_SRC_MUX12_ERRORSTS,
    PFXB_SRC_MUX12_RESERVED,
    PFXB_SRC_MUX12_FLASH_ERR,
    PFXB_SRC_MUX12_RESERVED1,
    PFXB_SRC_MUX13_EXTSYNCOUT,
    PFXB_SRC_MUX13_INPUTXBAR6,
    PFXB_SRC_MUX13_CPU_HALT,
    PFXB_SRC_MUX13_RESERVED,
    PFXB_SRC_MUX14_RESERVED,
    PFXB_SRC_MUX14_ADCSOCBO,
    PFXB_SRC_MUX14_SYS_ERR,
    PFXB_SRC_MUX14_RESERVED1,
    PFXB_SRC_MUX15_RESERVED,
    PFXB_SRC_MUX15_INPUTXBAR7,
    PFXB_SRC_MUX15_PT_ERR,
    PFXB_SRC_MUX15_ETIMOUT5,
    PFXB_SRC_MUX16_SD0FLT0_EVT0,
    PFXB_SRC_MUX16_SD0FLT0_EVT0_OR_EVT1,
    PFXB_SRC_MUX16_RESERVED,
    PFXB_SRC_MUX16_RESERVED1,
    PFXB_SRC_MUX17_SD0FLT0_EVT1,
    PFXB_SRC_MUX17_INPUTXBAR8,
    PFXB_SRC_MUX17_RESERVED,
    PFXB_SRC_MUX17_ETIMOUT6,
    PFXB_SRC_MUX18_SD0FLT1_EVT0,
    PFXB_SRC_MUX18_SD0FLT1_EVT0_OR_EVT1,
    PFXB_SRC_MUX18_RESERVED,
    PFXB_SRC_MUX18_RESERVED1,
    PFXB_SRC_MUX19_SD0FLT1_EVT1,
    PFXB_SRC_MUX19_INPUTXBAR9,
    PFXB_SRC_MUX19_RESERVED,
    PFXB_SRC_MUX19_ETIMOUT7,
    PFXB_SRC_MUX20_SD0FLT2_EVT0,
    PFXB_SRC_MUX20_SD0FLT2_EVT0_OR_EVT1,
    PFXB_SRC_MUX20_RESERVED,
    PFXB_SRC_MUX20_RESERVED1,
    PFXB_SRC_MUX21_SD0FLT2_EVT1,
    PFXB_SRC_MUX21_INPUTXBAR10,
    PFXB_SRC_MUX21_RESERVED,
    PFXB_SRC_MUX21_ETIMOUT8,
    PFXB_SRC_MUX22_SD0FLT3_EVT0,
    PFXB_SRC_MUX22_SD0FLT3_EVT0_OR_EVT1,
    PFXB_SRC_MUX22_RESERVED,
    PFXB_SRC_MUX22_RESERVED1,
    PFXB_SRC_MUX23_SD0FLT3_EVT1,
    PFXB_SRC_MUX23_INPUTXBAR11,
    PFXB_SRC_MUX23_RESERVED,
    PFXB_SRC_MUX23_ETIMOUT9,
    PFXB_SRC_MUX24_SD1FLT0_EVT0,
    PFXB_SRC_MUX24_SD1FLT0_EVT0_OR_EVT1,
    PFXB_SRC_MUX24_SRPWM_XBAR_SYNC0,
    PFXB_SRC_MUX24_RESERVED,
    PFXB_SRC_MUX25_SD1FLT0_EVT1,
    PFXB_SRC_MUX25_INPUTXBAR12,
    PFXB_SRC_MUX25_RESERVED,
    PFXB_SRC_MUX25_ETIMOUT10,
    PFXB_SRC_MUX26_SD1FLT1_EVT0,
    PFXB_SRC_MUX26_SD1FLT1_EVT0_OR_EVT1,
    PFXB_SRC_MUX26_SRPWM_XBAR_SYNC1,
    PFXB_SRC_MUX26_RESERVED,
    PFXB_SRC_MUX27_SD1FLT1_EVT1,
    PFXB_SRC_MUX27_INPUTXBAR13,
    PFXB_SRC_MUX27_RESERVED,
    PFXB_SRC_MUX27_ETIMOUT11,
    PFXB_SRC_MUX28_SD1FLT2_EVT0,
    PFXB_SRC_MUX28_SD1FLT2_EVT0_OR_EVT1,
    PFXB_SRC_MUX28_SRPWM_XBAR_SYNC2,
    PFXB_SRC_MUX28_RESERVED,
    PFXB_SRC_MUX29_SD1FLT2_EVT1,
    PFXB_SRC_MUX29_INPUTXBAR14,
    PFXB_SRC_MUX29_RESERVED,
    PFXB_SRC_MUX29_ETIMOUT12,
    PFXB_SRC_MUX30_SD1FLT3_EVT0,
    PFXB_SRC_MUX30_SD1FLT3_EVT0_OR_EVT1,
    PFXB_SRC_MUX30_SRPWM_XBAR_SYNC3,
    PFXB_SRC_MUX30_RESERVED,
    PFXB_SRC_MUX31_SD1FLT3_EVT1,
    PFXB_SRC_MUX31_INPUTXBAR15,
    PFXB_SRC_MUX31_ERRORSTS,
    PFXB_SRC_MUX31_ETIMOUT13
} XBAR_PFXB_SRC_TypeDef;             /*!< 32x4channel input */

/**
 * @brief ETIMER Trigger XBAR  Source enumeration
 */
typedef enum
{
    ETXB_SRC_MUX00_CMP_EVT0 = 0,
    ETXB_SRC_MUX00_CMP_EVT0_OR_EVT1,
    ETXB_SRC_MUX00_ADCA_EVT0,
    ETXB_SRC_MUX00_RESERVED,
    ETXB_SRC_MUX01_CMP_EVT1,
    ETXB_SRC_MUX01_INPUTXBAR0,
    ETXB_SRC_MUX01_ADCA_EVT1,
    ETXB_SRC_MUX01_RESERVED,
    ETXB_SRC_MUX02_CMP_EVT2,
    ETXB_SRC_MUX02_CMP_EVT2_OR_EVT3,
    ETXB_SRC_MUX02_ADCA_EVT2,
    ETXB_SRC_MUX02_RESERVED,
    ETXB_SRC_MUX03_CMP_EVT3,
    ETXB_SRC_MUX03_INPUTXBAR1,
    ETXB_SRC_MUX03_ADCA_EVT3,
    ETXB_SRC_MUX03_RESERVED,
    ETXB_SRC_MUX04_CMP_EVT4,
    ETXB_SRC_MUX04_CMP_EVT4_OR_EVT5,
    ETXB_SRC_MUX04_ADCB_EVT0,
    ETXB_SRC_MUX04_RESERVED,
    ETXB_SRC_MUX05_CMP_EVT5,
    ETXB_SRC_MUX05_INPUTXBAR2,
    ETXB_SRC_MUX05_ADCB_EVT1,
    ETXB_SRC_MUX05_RESERVED,
    ETXB_SRC_MUX06_CMP_EVT6,
    ETXB_SRC_MUX06_CMP_EVT6_OR_EVT7,
    ETXB_SRC_MUX06_ADCB_EVT2,
    ETXB_SRC_MUX06_RESERVED,
    ETXB_SRC_MUX07_CMP_EVT7,
    ETXB_SRC_MUX07_INPUTXBAR3,
    ETXB_SRC_MUX07_ADCB_EVT3,
    ETXB_SRC_MUX07_RESERVED,
    ETXB_SRC_MUX08_RESERVED,
    ETXB_SRC_MUX08_RESERVED1,
    ETXB_SRC_MUX08_ADCC_EVT0,
    ETXB_SRC_MUX08_RESERVED2,
    ETXB_SRC_MUX09_RESERVED,
    ETXB_SRC_MUX09_INPUTXBAR4,
    ETXB_SRC_MUX09_ADCC_EVT1,
    ETXB_SRC_MUX09_RESERVED1,
    ETXB_SRC_MUX10_RESERVED,
    ETXB_SRC_MUX10_RESERVED1,
    ETXB_SRC_MUX10_ADCC_EVT2,
    ETXB_SRC_MUX10_RESERVED2,
    ETXB_SRC_MUX11_RESERVED,
    ETXB_SRC_MUX11_INPUTXBAR5,
    ETXB_SRC_MUX11_ADCC_EVT3,
    ETXB_SRC_MUX11_RESERVED1,
    ETXB_SRC_MUX12_ERRORSTS,
    ETXB_SRC_MUX12_RESERVED,
    ETXB_SRC_MUX12_FLASH_ERR,
    ETXB_SRC_MUX12_RESERVED1,
    ETXB_SRC_MUX13_EXTSYNCOUT,
    ETXB_SRC_MUX13_INPUTXBAR6,
    ETXB_SRC_MUX13_CPU_HALT,
    ETXB_SRC_MUX13_RESERVED,
    ETXB_SRC_MUX14_RESERVED,
    ETXB_SRC_MUX14_CFG_ETXB_SWx,
    ETXB_SRC_MUX14_SYS_ERR,
    ETXB_SRC_MUX14_RESERVED1,
    ETXB_SRC_MUX15_RESERVED,
    ETXB_SRC_MUX15_INPUTXBAR7,
    ETXB_SRC_MUX15_PT_ERR,
    ETXB_SRC_MUX15_RESERVED1,
    ETXB_SRC_MUX16_SD0FLT0_EVT0,
    ETXB_SRC_MUX16_SD0FLT0_EVT0_OR_EVT1,
    ETXB_SRC_MUX16_RESERVED,
    ETXB_SRC_MUX16_RESERVED1,
    ETXB_SRC_MUX17_SD0FLT0_EVT1,
    ETXB_SRC_MUX17_INPUTXBAR8,
    ETXB_SRC_MUX17_RESERVED,
    ETXB_SRC_MUX17_RESERVED1,
    ETXB_SRC_MUX18_SD0FLT1_EVT0,
    ETXB_SRC_MUX18_SD0FLT1_EVT0_OR_EVT1,
    ETXB_SRC_MUX18_RESERVED,
    ETXB_SRC_MUX18_RESERVED1,
    ETXB_SRC_MUX19_SD0FLT1_EVT1,
    ETXB_SRC_MUX19_INPUTXBAR9,
    ETXB_SRC_MUX19_RESERVED,
    ETXB_SRC_MUX19_RESERVED1,
    ETXB_SRC_MUX20_SD0FLT2_EVT0,
    ETXB_SRC_MUX20_SD0FLT2_EVT0_OR_EVT1,
    ETXB_SRC_MUX20_RESERVED,
    ETXB_SRC_MUX20_RESERVED1,
    ETXB_SRC_MUX21_SD0FLT2_EVT1,
    ETXB_SRC_MUX21_INPUTXBAR10,
    ETXB_SRC_MUX21_RESERVED,
    ETXB_SRC_MUX21_RESERVED1,
    ETXB_SRC_MUX22_SD0FLT3_EVT0,
    ETXB_SRC_MUX22_SD0FLT3_EVT0_OR_EVT1,
    ETXB_SRC_MUX22_RESERVED,
    ETXB_SRC_MUX22_RESERVED1,
    ETXB_SRC_MUX23_SD0FLT3_EVT1,
    ETXB_SRC_MUX23_INPUTXBAR11,
    ETXB_SRC_MUX23_RESERVED,
    ETXB_SRC_MUX23_RESERVED1,
    ETXB_SRC_MUX24_SD1FLT0_EVT0,
    ETXB_SRC_MUX24_SD1FLT0_EVT0_OR_EVT1,
    ETXB_SRC_MUX24_RESERVED,
    ETXB_SRC_MUX24_RESERVED1,
    ETXB_SRC_MUX25_SD1FLT0_EVT1,
    ETXB_SRC_MUX25_INPUTXBAR12,
    ETXB_SRC_MUX25_RESERVED,
    ETXB_SRC_MUX25_RESERVED1,
    ETXB_SRC_MUX26_SD1FLT1_EVT0,
    ETXB_SRC_MUX26_SD1FLT1_EVT0_OR_EVT1,
    ETXB_SRC_MUX26_RESERVED,
    ETXB_SRC_MUX26_RESERVED1,
    ETXB_SRC_MUX27_SD1FLT1_EVT1,
    ETXB_SRC_MUX27_INPUTXBAR13,
    ETXB_SRC_MUX27_RESERVED,
    ETXB_SRC_MUX27_RESERVED1,
    ETXB_SRC_MUX28_SD1FLT2_EVT0,
    ETXB_SRC_MUX28_SD1FLT2_EVT0_OR_EVT1,
    ETXB_SRC_MUX28_RESERVED,
    ETXB_SRC_MUX28_RESERVED1,
    ETXB_SRC_MUX29_SD1FLT2_EVT1,
    ETXB_SRC_MUX29_INPUTXBAR14,
    ETXB_SRC_MUX29_RESERVED,
    ETXB_SRC_MUX29_RESERVED1,
    ETXB_SRC_MUX30_SD1FLT3_EVT0,
    ETXB_SRC_MUX30_SD1FLT3_EVT0_OR_EVT1,
    ETXB_SRC_MUX30_CFG_ETXB_SWx,
    ETXB_SRC_MUX30_RESERVED,
    ETXB_SRC_MUX31_SD1FLT3_EVT1,
    ETXB_SRC_MUX31_INPUTXBAR15,
    ETXB_SRC_MUX31_ERRORSTS,
    ETXB_SRC_MUX31_RESERVED
} XBAR_ETXB_SRC_TypeDef;                    /*!< 32x4 channel input */


/**
 * @brief Output XBAR  Source enumeration
 */
typedef enum
{
    OPXB_SRC_MUX00_CMP_OUT0 = 0,
    OPXB_SRC_MUX00_CMP_OUT0_OR_OUT1,
    OPXB_SRC_MUX00_ADCA_EVT0,
    OPXB_SRC_MUX00_RESERVED,
    OPXB_SRC_MUX01_CMP_OUT1,
    OPXB_SRC_MUX01_INPUTXBAR0,
    OPXB_SRC_MUX01_ADCA_EVT1,
    OPXB_SRC_MUX01_ETIMOUT0,
    OPXB_SRC_MUX02_CMP_OUT2,
    OPXB_SRC_MUX02_CMP_OUT2_OR_OUT3,
    OPXB_SRC_MUX02_ADCA_EVT2,
    OPXB_SRC_MUX02_RESERVED,
    OPXB_SRC_MUX03_CMP_OUT3,
    OPXB_SRC_MUX03_INPUTXBAR1,
    OPXB_SRC_MUX03_ADCA_EVT3,
    OPXB_SRC_MUX03_ETIMOUT1,
    OPXB_SRC_MUX04_CMP_OUT4,
    OPXB_SRC_MUX04_CMP_OUT4_OR_OUT5,
    OPXB_SRC_MUX04_ADCB_EVT0,
    OPXB_SRC_MUX04_RESERVED,
    OPXB_SRC_MUX05_CMP_OUT5,
    OPXB_SRC_MUX05_INPUTXBAR2,
    OPXB_SRC_MUX05_ADCB_EVT1,
    OPXB_SRC_MUX05_ETIMOUT2,
    OPXB_SRC_MUX06_CMP_OUT6,
    OPXB_SRC_MUX06_CMP_OUT6_OR_OUT7,
    OPXB_SRC_MUX06_ADCB_EVT2,
    OPXB_SRC_MUX06_RESERVED,
    OPXB_SRC_MUX07_CMP_OUT7,
    OPXB_SRC_MUX07_INPUTXBAR3,
    OPXB_SRC_MUX07_ADCB_EVT3,
    OPXB_SRC_MUX07_ETIMOUT3,
    OPXB_SRC_MUX08_RESERVED,
    OPXB_SRC_MUX08_CFG_OPXB_SWx,
    OPXB_SRC_MUX08_ADCC_EVT0,
    OPXB_SRC_MUX08_RESERVED1,
    OPXB_SRC_MUX09_RESERVED,
    OPXB_SRC_MUX09_INPUTXBAR4,
    OPXB_SRC_MUX09_ADCC_EVT1,
    OPXB_SRC_MUX09_ETIMOUT4,
    OPXB_SRC_MUX10_RESERVED,
    OPXB_SRC_MUX10_ADCSOCAO,
    OPXB_SRC_MUX10_ADCC_EVT2,
    OPXB_SRC_MUX10_RESERVED1,
    OPXB_SRC_MUX11_RESERVED,
    OPXB_SRC_MUX11_INPUTXBAR5,
    OPXB_SRC_MUX11_ADCC_EVT3,
    OPXB_SRC_MUX11_RESERVED1,
    OPXB_SRC_MUX12_ERRORSTS,
    OPXB_SRC_MUX12_CFG_OPXB_SWx,
    OPXB_SRC_MUX12_FLASH_ERR,
    OPXB_SRC_MUX12_RESERVED,
    OPXB_SRC_MUX13_EXTSYNCOUT,
    OPXB_SRC_MUX13_INPUTXBAR6,
    OPXB_SRC_MUX13_CPU_HALT,
    OPXB_SRC_MUX13_RESERVED,
    OPXB_SRC_MUX14_RESERVED,
    OPXB_SRC_MUX14_ADCSOCBO,
    OPXB_SRC_MUX14_SYS_ERR,
    OPXB_SRC_MUX14_RESERVED1,
    OPXB_SRC_MUX15_RESERVED,
    OPXB_SRC_MUX15_INPUTXBAR7,
    OPXB_SRC_MUX15_PT_ERR,
    OPXB_SRC_MUX15_ETIMOUT5,
    OPXB_SRC_MUX16_SD0FLT0_EVT0,
    OPXB_SRC_MUX16_SD0FLT0_EVT0_OR_EVT1,
    OPXB_SRC_MUX16_STM0_OC0,
    OPXB_SRC_MUX16_RESERVED,
    OPXB_SRC_MUX17_SD0FLT0_EVT1,
    OPXB_SRC_MUX17_INPUTXBAR8,
    OPXB_SRC_MUX17_STM0_OC1,
    OPXB_SRC_MUX17_ETIMOUT6,
    OPXB_SRC_MUX18_SD0FLT1_EVT0,
    OPXB_SRC_MUX18_SD0FLT1_EVT0_OR_EVT1,
    OPXB_SRC_MUX18_STM0_OC2,
    OPXB_SRC_MUX18_RESERVED,
    OPXB_SRC_MUX19_SD0FLT1_EVT1,
    OPXB_SRC_MUX19_INPUTXBAR9,
    OPXB_SRC_MUX19_STM0_OC3,
    OPXB_SRC_MUX19_ETIMOUT7,
    OPXB_SRC_MUX20_SD0FLT2_EVT0,
    OPXB_SRC_MUX20_SD0FLT2_EVT0_OR_EVT1,
    OPXB_SRC_MUX20_STM1_OC0,
    OPXB_SRC_MUX20_RESERVED,
    OPXB_SRC_MUX21_SD0FLT2_EVT1,
    OPXB_SRC_MUX21_INPUTXBAR10,
    OPXB_SRC_MUX21_STM1_OC1,
    OPXB_SRC_MUX21_ETIMOUT8,
    OPXB_SRC_MUX22_SD0FLT3_EVT0,
    OPXB_SRC_MUX22_SD0FLT3_EVT0_OR_EVT1,
    OPXB_SRC_MUX22_STM1_OC2,
    OPXB_SRC_MUX22_RESERVED,
    OPXB_SRC_MUX23_SD0FLT3_EVT1,
    OPXB_SRC_MUX23_INPUTXBAR11,
    OPXB_SRC_MUX23_STM1_OC3,
    OPXB_SRC_MUX23_ETIMOUT9,
    OPXB_SRC_MUX24_SD1FLT0_EVT0,
    OPXB_SRC_MUX24_SD1FLT0_EVT0_OR_EVT1,
    OPXB_SRC_MUX24_SRPWM_XBAR_SYNC0,
    OPXB_SRC_MUX24_INPUTXBAR_CLU2OUT0,
    OPXB_SRC_MUX25_SD1FLT0_EVT1,
    OPXB_SRC_MUX25_INPUTXBAR12,
    OPXB_SRC_MUX25_RESERVED,
    OPXB_SRC_MUX25_ETIMOUT10,
    OPXB_SRC_MUX26_SD1FLT1_EVT0,
    OPXB_SRC_MUX26_SD1FLT1_EVT0_OR_EVT1,
    OPXB_SRC_MUX26_SRPWM_XBAR_SYNC1,
    OPXB_SRC_MUX26_INPUTXBAR_CLU2OUT1,
    OPXB_SRC_MUX27_SD1FLT1_EVT1,
    OPXB_SRC_MUX27_INPUTXBAR13,
    OPXB_SRC_MUX27_RESERVED,
    OPXB_SRC_MUX27_ETIMOUT11,
    OPXB_SRC_MUX28_SD1FLT2_EVT0,
    OPXB_SRC_MUX28_SD1FLT2_EVT0_OR_EVT1,
    OPXB_SRC_MUX28_SRPWM_XBAR_SYNC2,
    OPXB_SRC_MUX28_INPUTXBAR_CLU2OUT2,
    OPXB_SRC_MUX29_SD1FLT2_EVT1,
    OPXB_SRC_MUX29_INPUTXBAR14,
    OPXB_SRC_MUX29_RESERVED,
    OPXB_SRC_MUX29_ETIMOUT12,
    OPXB_SRC_MUX30_SD1FLT3_EVT0,
    OPXB_SRC_MUX30_SD1FLT3_EVT0_OR_EVT1,
    OPXB_SRC_MUX30_SRPWM_XBAR_SYNC3,
    OPXB_SRC_MUX30_INPUTXBAR_CLU2OUT3,
    OPXB_SRC_MUX31_SD1FLT3_EVT1,
    OPXB_SRC_MUX31_INPUTXBAR15,
    OPXB_SRC_MUX31_ERRORSTS,
    OPXB_SRC_MUX31_ETIMOUT13
} XBAR_OPXB_SRC_TypeDef;                   /*!< 32x4 channel input */

/* ================================================================================================================== */
/* ================                                   Enum Declarations                               =============== */
/* ================================================================================================================== */

/**
 * @brief XBAR Input Signal Edge trigger type enumeration
 */
typedef enum
{
    XBAR_DSEL_MUX_OUT      = 0x00,       /*!< Select Signal after MUX out              */
    XBAR_DSEL_LATCHED_HI   = 0x01,       /*!< Select Signal after Latched High level   */
    XBAR_DSEL_EDGE_RISING  = 0x02,       /*!< Select Signal after Latched Rising       */
    XBAR_DSEL_EDGE_FALLING = 0x03        /*!< Select Signal after Latched Falling      */
} XBAR_OUT_DSEL_TypeDef;

/**
 * @brief XBAR OPXB Output Signal mode type enumeration
 */
typedef enum
{
    XBAR_OPXB_OEMOD_VALID     = 0x00,          /*!< output always valid                      */
    XBAR_OPXB_OEMOD_PWM_OE    = 0x01,          /*!< if input signal include etimer pwm out signal,
                                                *   output select etimer pwm oe signal as EN signal */
    XBAR_OPXB_OEMOD_TRI_STATE = 0x02,          /*!< output always tri-state       */
    XBAR_OPXB_OEMOD_VALID1    = 0x03           /*!< same as  XBAR_OPXB_OEMOD_VALID           */
} XBAR_OPXB_OEMOD_TypeDef;

/**
 * @brief XBAR INXB Output channel for interrupt mask enumeration
 */
typedef enum
{
    XBAR_INXB_OUTPUT_CH12_IRQ0 = 0x01,          /*!< INXB output channel 12 for generate irq 0   */
    XBAR_INXB_OUTPUT_CH13_IRQ1 = 0x02,          /*!< INXB output channel 13 for generate irq 1   */
    XBAR_INXB_OUTPUT_CH14_IRQ2 = 0x04,          /*!< INXB output channel 14 for generate irq 2   */
    XBAR_INXB_OUTPUT_CH15_IRQ3 = 0x08           /*!< INXB output channel 15 for generate irq 3   */
} XBAR_INXB_IRQ_TypeDef;


/**
 * @brief XBAR CLU module enumeration
 */
typedef enum
{
    XBAR_CLU_XCSA = 0x00,          /*!< XBAR CLU2ADC  */
    XBAR_CLU_XCET = 0x01,          /*!< XBAR CLU2ETIMER */
    XBAR_CLU_XCOX = 0x02           /*!< XBAR CLU2OutputXBAR */
} XBAR_CLU_TypeDef;

/**
 * @brief XBAR CLU out edge type enumeration
 */
typedef enum
{
    XBAR_CLU_EDGE_RISE    = 0x01,       /*!< XBAR CLU out edge Rise */
    XBAR_CLU_EDGE_FALLING = 0x02,       /*!< XBAR CLU out edge Falling  */
    XBAR_CLU_EDGE_BOTH    = 0x03        /*!< XBAR CLU out edge both Rise and Falling */
} XBAR_CLU_EDGE_TypeDef;

/**
 * @brief XBAR CLU logic unit type enumeration
 */
typedef enum
{
    XBAR_CLU_ANDOR = 0x00,           /*!< XBAR CLU logic unit AND-OR */
    XBAR_CLU_ORXOR,                  /*!< XBAR CLU logic unit OR-XOR  */
    XBAR_CLU_4INAND,                 /*!< XBAR CLU logic unit 4 Input AND */
    XBAR_CLU_SRLATCH,                /*!< XBAR CLU logic unit S-R Latch */
    XBAR_CLU_1INDFF,                 /*!< XBAR CLU logic unit 1 Input Set-Reset flip-flop */
    XBAR_CLU_2INDFF,                 /*!< XBAR CLU logic unit 2 Input Set-Reset flip-flop */
    XBAR_CLU_JKFF,                   /*!< XBAR CLU logic unit J-K flip-flop */
    XBAR_CLU_LATCH                   /*!< XBAR CLU logic unit Set-Reset Latch */
} XBAR_CLU_UNIT_TypeDef;

/**
 * @brief XBAR Fault Source type enumeration
 */
typedef enum
{
    XBAR_FAULT_PWR_TEMP_WARN        = 0x00001,
    XBAR_FAULT_PWR_POWER_ERR        = 0x00002,
    XBAR_FAULT_PWR_PWR_OCP_WARN     = 0x00004,
    XBAR_FAULT_PWR_POR_UV_WARN      = 0x00008,
    XBAR_FAULT_SYS_CLOCK_FAULT      = 0x00010,
    XBAR_FAULT_SYS_CPU_BUS_ERR      = 0x00020,
    XBAR_FAULT_SYS_BUS_TIMEOUT      = 0x00040,
    XBAR_FAULT_SYS_CAN_ECC_ERR      = 0x00080,
    XBAR_FAULT_SYS_SRAM_ECC_ERR     = 0x00100,
    XBAR_FAULT_SYS_CPU_ECC_ERR      = 0x00200,
    XBAR_FAULT_SYS_CPU_LOCKUP       = 0x00400,
    XBAR_FAULT_SYS_CPU_RST_REC      = 0x00800,
    XBAR_FAULT_SYS_WDG1_REQ_REC     = 0x01000,
    XBAR_FAULT_SYS_WDG0_REQ_REC     = 0x02000,
    XBAR_FAULT_FLASH_DFLASH_BUS_ERR = 0x04000,
    XBAR_FAULT_FLASH_DFLASH_ECC_ERR = 0x08000,
    XBAR_FAULT_FLASH_PFLASH_BUS_ERR = 0x10000,
    XBAR_FAULT_FLASH_PFLASH_ECC_ERR = 0x20000             /*!< XBAR Fault source PFlash ECC Error */
} XBAR_FALUT_SRC_TypeDef;

/**
 * @brief XBAR CLB Input XBAR Source type enumeration
 */
enum CIXB_SRC
{
    CIXB_SRC_GPIO0,
    CIXB_SRC_GPIO1,
    CIXB_SRC_GPIO2,
    CIXB_SRC_GPIO3,
    CIXB_SRC_GPIO4,
    CIXB_SRC_GPIO5,
    CIXB_SRC_GPIO6,
    CIXB_SRC_GPIO7,
    CIXB_SRC_GPIO8,
    CIXB_SRC_GPIO9,
    CIXB_SRC_GPIO10,
    CIXB_SRC_GPIO11,
    CIXB_SRC_GPIO12,
    CIXB_SRC_GPIO13,
    CIXB_SRC_GPIO14,
    CIXB_SRC_GPIO15,
    CIXB_SRC_GPIO16,
    CIXB_SRC_GPIO17,
    CIXB_SRC_GPIO18,  //SWCLK
    CIXB_SRC_GPIO19,  //SWDIO
    CIXB_SRC_GPIO20,
    CIXB_SRC_GPIO21,
    CIXB_SRC_GPIO22,
    CIXB_SRC_GPIO23,
    CIXB_SRC_GPIO24,
    CIXB_SRC_GPIO25,
    CIXB_SRC_GPIO26,
    CIXB_SRC_GPIO27,
    CIXB_SRC_GPIO28,
    CIXB_SRC_GPIO29,
    CIXB_SRC_GPIO30,
    CIXB_SRC_GPIO31,
    CIXB_SRC_GPIO32,
    CIXB_SRC_GPIO33,
    CIXB_SRC_GPIO34,
    CIXB_SRC_GPIO35,
    // CIXB_SRC_GPIO36,
    CIXB_SRC_GPIO37,
    // CIXB_SRC_GPIO38,
    CIXB_SRC_GPIO39,
    CIXB_SRC_GPIO40,
    CIXB_SRC_GPIO41,
    CIXB_SRC_GPIO42,
    CIXB_SRC_GPIO43,
    CIXB_SRC_GPIO44,
    CIXB_SRC_GPIO45,
    CIXB_SRC_GPIO46,
    CIXB_SRC_GPIO47,
    CIXB_SRC_GPIO48,
    CIXB_SRC_GPIO49,
    CIXB_SRC_GPIO50,
    CIXB_SRC_GPIO51,
    CIXB_SRC_GPIO52,
    CIXB_SRC_GPIO53,
    CIXB_SRC_GPIO54,
    CIXB_SRC_GPIO55,
    CIXB_SRC_GPIO56,
    CIXB_SRC_GPIO57,
    CIXB_SRC_GPIO58,
    CIXB_SRC_GPIO59,
    CIXB_SRC_GPIO60,
    CIXB_SRC_GPIO61,
    CIXB_SRC_GPIO62,
    CIXB_SRC_GPIO63,
    CIXB_SRC_GPIO64,
    CIXB_SRC_GPIO65,
    CIXB_SRC_GPIO66,
    CIXB_SRC_GPIO67,
    CIXB_SRC_GPIO68,
    CIXB_SRC_GPIO69,
    CIXB_SRC_GPIO70,
    CIXB_SRC_GPIO71,
    CIXB_SRC_GPIO72,
    CIXB_SRC_GPIO73,
    CIXB_SRC_GPIO74,
    CIXB_SRC_GPIO75,
    CIXB_SRC_GPIO76,
    CIXB_SRC_GPIO77,
    CIXB_SRC_GPIO78,
    CIXB_SRC_GPIO79,
    CIXB_SRC_GPIO80,
    CIXB_SRC_GPIO81
};             /*!< 80 channel input */

/**
 * @brief XBAR CLB Output XBAR Source type enumeration
 */
enum COXB_SRC
{
    COXB_SRC_CLB0_OUT0 = 0,
    COXB_SRC_OUTXBAR0  = 1,
    COXB_SRC_CLB0_OUT1 = 4,
    COXB_SRC_OUTXBAR1  = 5,
    COXB_SRC_CLB0_OUT2 = 8,
    COXB_SRC_OUTXBAR2  = 9,
    COXB_SRC_CLB0_OUT3 = 12,
    COXB_SRC_OUTXBAR3  = 13,
    COXB_SRC_CLB0_OUT4 = 16,
    COXB_SRC_OUTXBAR4  = 17,
    COXB_SRC_CLB0_OUT5 = 20,
    COXB_SRC_OUTXBAR5  = 21,
    COXB_SRC_CLB0_OUT6 = 24,
    COXB_SRC_OUTXBAR6  = 25,
    COXB_SRC_CLB0_OUT7 = 28,
    COXB_SRC_OUTXBAR7  = 29,
    COXB_SRC_CLB1_OUT0 = 32,
    COXB_SRC_OUTXBAR8  = 33,
    COXB_SRC_CLB1_OUT1 = 36,
    COXB_SRC_OUTXBAR9  = 37,
    COXB_SRC_CLB1_OUT2 = 40,
    COXB_SRC_OUTXBAR10 = 41,
    COXB_SRC_CLB1_OUT3 = 44,
    COXB_SRC_OUTXBAR11 = 45,
    COXB_SRC_CLB1_OUT4 = 48,
    COXB_SRC_OUTXBAR12 = 49,
    COXB_SRC_CLB1_OUT5 = 52,
    COXB_SRC_OUTXBAR13 = 53,
    COXB_SRC_CLB1_OUT6 = 56,
    COXB_SRC_CLB1_OUT7 = 60,
    COXB_SRC_CLB2_OUT0 = 64,
    COXB_SRC_CLB2_OUT1 = 68,
    COXB_SRC_CLB2_OUT2 = 72,
    COXB_SRC_CLB2_OUT3 = 76,
    COXB_SRC_CLB2_OUT4 = 80,
    COXB_SRC_CLB2_OUT5 = 84,
    COXB_SRC_CLB2_OUT6 = 88,
    COXB_SRC_CLB2_OUT7 = 92,
    COXB_SRC_CLB3_OUT0 = 96,
    COXB_SRC_CLB3_OUT1 = 100,
    COXB_SRC_CLB3_OUT2 = 104,
    COXB_SRC_CLB3_OUT3 = 108,
    COXB_SRC_CLB3_OUT4 = 112,
    COXB_SRC_CLB3_OUT5 = 116,
    COXB_SRC_CLB3_OUT6 = 120,
    COXB_SRC_CLB3_OUT7 = 124,
};

/**
 * @brief XBAR STIMER Emergency Fault Signal output type enumeration
 */
typedef enum
{
    XBAR_STIM_EG_FAULT_SIG0 = 0x0,
    XBAR_STIM_EG_FAULT_SIG1 = 0x1
} XBAR_STIM_EF_SIG_TypeDef;

/**
 * @brief XBAR STIMER Emergency Fault Signal output target STIMER enumerationn
 */
typedef enum
{
    XBAR_STIM0 = 0x0,
    XBAR_STIM1 = 0x1
} XBAR_STIM_IDX_TypeDef;



/*====================================================================================================================*/
/* ================                                    Struct  Declarations                  =========================*/
/*====================================================================================================================*/

/**
 * @brief XBAR out param configure
 */
typedef struct
{
    XBAR_OUT_DSEL_TypeDef   outDsel;            /*!< Single input filter enable or disable, default: disable */
    ControlStatus           outPolarInvertEn;   /*!< Single output polar reversal, default: disable */
    ControlStatus           outPulseStretchEn;  /*!< Single output pulse stretch,  default: disable */
    XBAR_OPXB_OEMOD_TypeDef outOEmode;          /*!< Single output enable mode */
} XBAR_OutCfg_TypeDef;

/**
 * @brief CLU Parameters Configure
 */
typedef struct
{
    XBAR_CLU_EDGE_TypeDef edgeType;                 /*!< CLU output edge trigger type, default: rise edge */
    ControlStatus         invertEn;                 /*!< CLU output invert enable or disable, default: disable */
    ControlStatus         bypassEn;                 /*!< CLU output bypass enable or disable, default: disable */
    ControlStatus         outEn;                    /*!< CLU output enable or disable, default: low level */
    XBAR_CLU_UNIT_TypeDef cluType;                  /*!< CLU logic unit type, default: AND-OR */
} XBAR_CLU_Cfg_TypeDef;

/**
 * @brief INXB Input Mask Struct
 */
typedef struct
{
    uint32_t chBitMsk[4];                 /*!< Single input source bit mask struct,  bit0~83 valid */
} XBAR_InChMsk_TypeDef;


/*====================================================================================================================*/
/* ================                                 Interface  Declarations                  =========================*/
/*====================================================================================================================*/
#define _XBAR_REG_WR_LOCK()      do { XBAR->KEY = 0; } while (0)
#define _XBAR_REG_WR_UNLOCK()    do { XBAR->KEY = 0x5a5a; } while (0)

/* Common Interface */
DRV_Status XBAR_initInputChMsk(XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_addInputSource(XBAR_InChMsk_TypeDef *in_ch_mask, uint8_t ch_idx);

/* INXB Interface */
DRV_Status XBAR_INXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_INXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_INXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_INXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_INXB_clearOutputLatch(uint16_t out_ch_mask);
FlagStatus XBAR_INXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_INXB_getOutputStatus(bool latched);
DRV_Status XBAR_INXB_enableInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask);
DRV_Status XBAR_INXB_disableInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask);
DRV_Status XBAR_INXB_setInterruptMask(XBAR_INXB_IRQ_TypeDef it_channel_mask);
DRV_Status XBAR_INXB_clearInterruptMask(XBAR_INXB_IRQ_TypeDef it_channel_mask);
DRV_Status XBAR_INXB_forceTriggerInterrupt(XBAR_INXB_IRQ_TypeDef it_channel_mask);
DRV_Status XBAR_INXB_clearInterruptStatus(XBAR_INXB_IRQ_TypeDef it_channel_mask);
ITStatus XBAR_INXB_getChInterruptStatus(XBAR_INXB_IRQ_TypeDef itchannel);
ITStatus XBAR_INXB_getChInterruptRawStatus(XBAR_INXB_IRQ_TypeDef itchannel);
uint8_t XBAR_INXB_getInterruptStatus(void);
uint8_t XBAR_INXB_getInterruptRawStatus(void);


/* PFXB Interface */
DRV_Status XBAR_PFXB_setMuxConfig(uint32_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_PFXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_PFXB_enableOutputMux(uint32_t out_ch_mask);
DRV_Status XBAR_PFXB_disableOutputMux(uint32_t out_ch_mask);
DRV_Status XBAR_PFXB_clearOutputLatch(uint32_t out_ch_mask);
FlagStatus XBAR_PFXB_getOutputChStatus(uint32_t out_ch, bool latched);
uint32_t XBAR_PFXB_getOutputStatus(bool latched);

/* ETXB Interface */
DRV_Status XBAR_ETXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_ETXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_ETXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_ETXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_ETXB_clearOutputLatch(uint16_t out_ch_mask);
DRV_Status XBAR_ETXB_setSoftwareInput(uint16_t out_ch_mask);
DRV_Status XBAR_ETXB_clearSoftwareInput(uint16_t out_ch_mask);
FlagStatus XBAR_ETXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_ETXB_getOutputStatus(bool latched);


/* OPXB Interface */
DRV_Status XBAR_OPXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_OPXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_OPXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_OPXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_OPXB_clearOutputLatch(uint16_t out_ch_mask);
DRV_Status XBAR_OPXB_setSoftwareInput(uint16_t out_ch_mask);
DRV_Status XBAR_OPXB_clearSoftwareInput(uint16_t out_ch_mask);
FlagStatus XBAR_OPXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_OPXB_getOutputStatus(bool latched);

/* CLU Interface */
DRV_Status XBAR_CLU_setConfig(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask, XBAR_CLU_Cfg_TypeDef *cfg);
DRV_Status XBAR_CLU_enableInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
DRV_Status XBAR_CLU_disableInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
DRV_Status XBAR_CLU_setInterruptMask(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
DRV_Status XBAR_CLU_clearInterruptMask(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
DRV_Status XBAR_CLU_forceTriggerInterrupt(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
DRV_Status XBAR_CLU_clearInterruptStatus(XBAR_CLU_TypeDef clu_type, uint8_t out_ch_mask);
ITStatus XBAR_CLU_getChInterruptStatus(XBAR_CLU_TypeDef clu_type, uint8_t channel);
ITStatus XBAR_CLU_getChInterruptRawStatus(XBAR_CLU_TypeDef clu_type, uint8_t channel);
uint8_t XBAR_CLU_getInterruptStatus(XBAR_CLU_TypeDef clu_type);
uint8_t XBAR_CLU_getInterruptRawStatus(XBAR_CLU_TypeDef clu_type);

/* Fault Interface */
DRV_Status XBAR_selectFaultMux(uint32_t fault_src_mask);
void XBAR_resetFaultMux(void);

/* STIMER Emergecy fault trigger source select and reset  */
DRV_Status XBAR_selectStimerEFSingalOutput(XBAR_STIM_IDX_TypeDef    stim_idx,
                                           XBAR_STIM_EF_SIG_TypeDef stim_es_sig,
                                           uint32_t                 fault_src_mask);
void XBAR_resetStimerEFSignalOutput(XBAR_STIM_IDX_TypeDef stim_idx, XBAR_STIM_EF_SIG_TypeDef stim_es_sig);

/* CLB Input XBAR Interface */
DRV_Status XBAR_CIXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_CIXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_CIXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_CIXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_CIXB_clearOutputLatch(uint16_t out_ch_mask);
FlagStatus XBAR_CIXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_CIXB_getOutputStatus(bool latched);

/* CLB XBAR Interface */
DRV_Status XBAR_CBXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_CBXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_CBXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_CBXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_CBXB_clearOutputLatch(uint16_t out_ch_mask);
FlagStatus XBAR_CBXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_CBXB_getOutputStatus(bool latched);

/* CLB Output XBAR Interface */
DRV_Status XBAR_COXB_setMuxConfig(uint16_t out_ch_mask, XBAR_InChMsk_TypeDef *in_ch_mask);
DRV_Status XBAR_COXB_initOutputChannel(XBAR_OutCfg_TypeDef *cfg, uint16_t out_ch_mask);
DRV_Status XBAR_COXB_enableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_COXB_disableOutputMux(uint16_t out_ch_mask);
DRV_Status XBAR_COXB_clearOutputLatch(uint16_t out_ch_mask);
FlagStatus XBAR_COXB_getOutputChStatus(uint16_t out_ch, bool latched);
uint32_t XBAR_COXB_getOutputStatus(bool latched);


/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif
#endif /*__ET6X_XBAR_H */
