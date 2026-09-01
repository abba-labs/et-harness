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

#ifndef __ET6X_SYSCTRL_H
#define __ET6X_SYSCTRL_H

#include "et6x.h"

#ifdef __cplusplus
extern "C"
{
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup SYSCTRL
 * @{
 */

/**
 * @brief  DMA Handshaking interface enum
 */
#define DMAMUX_INTERFACE0           (0)            /*!< DMAMUX Handshaking interface 0 */
#define DMAMUX_INTERFACE1           (1)            /*!< DMAMUX Handshaking interface 1 */
#define DMAMUX_INTERFACE2           (2)            /*!< DMAMUX Handshaking interface 2 */
#define DMAMUX_INTERFACE3           (3)            /*!< DMAMUX Handshaking interface 3 */
#define DMAMUX_INTERFACE4           (4)            /*!< DMAMUX Handshaking interface 4 */
#define DMAMUX_INTERFACE5           (5)            /*!< DMAMUX Handshaking interface 5 */
#define DMAMUX_INTERFACE6           (6)            /*!< DMAMUX Handshaking interface 6 */
#define DMAMUX_INTERFACE7           (7)            /*!< DMAMUX Handshaking interface 7 */
#define DMAMUX_INTERFACE_INVALID    (0xFF)         /*!< Invalid DMAMUX interface       */

/**
 * @brief  SYSCNT Clock Source Select
 */
typedef enum
{
    SYSCTRL_SYSCNT_CLKSRC_OSC25M = 0x00U,     /*!< osc 25MHz */
    SYSCTRL_SYSCNT_CLKSRC_XO25M  = 0x01U      /*!< xo 25MHz */
} SYSCTRL_SYSCNTClockSource;

/**
 * @brief  DMA Request Mode Select
 */
typedef enum
{
    DMAMUX_REQ_MODE_BURST  = 0x00U, /*!< default mode */
    DMAMUX_REQ_MODE_SINGLE = 0x01U  /*!< single mode */
} SYSCTRL_DMAReqMode;

/**
 * @brief  DMA Request Source Select
 */
typedef enum
{
    DMAMUX_REQ_CRC = 0,
    DMAMUX_REQ_FMAC_RD,
    DMAMUX_REQ_FMAC_WR,
    DMAMUX_REQ_SDFM0_0,
    DMAMUX_REQ_SDFM0_1,
    DMAMUX_REQ_SDFM0_2,
    DMAMUX_REQ_SDFM0_3,
    DMAMUX_REQ_SDFM1_0,
    DMAMUX_REQ_SDFM1_1,
    DMAMUX_REQ_SDFM1_2,
    DMAMUX_REQ_SDFM1_3,
    DMAMUX_REQ_SDFM2_0,
    DMAMUX_REQ_SDFM2_1,
    DMAMUX_REQ_SDFM2_2,
    DMAMUX_REQ_SDFM2_3,
    DMAMUX_REQ_SDFM3_0,
    DMAMUX_REQ_SDFM3_1,
    DMAMUX_REQ_SDFM3_2,
    DMAMUX_REQ_SDFM3_3,
    DMAMUX_REQ_EPWM0,
    DMAMUX_REQ_EPWM1,
    DMAMUX_REQ_EPWM2,
    DMAMUX_REQ_EPWM3,
    DMAMUX_REQ_EPWM4,
    DMAMUX_REQ_EPWM5,
    DMAMUX_REQ_EPWM6,
    DMAMUX_REQ_EPWM7,
    DMAMUX_REQ_EPWM8,
    DMAMUX_REQ_EPWM9,
    DMAMUX_REQ_EPWM10,
    DMAMUX_REQ_EPWM11,
    DMAMUX_REQ_EPWM12,
    DMAMUX_REQ_EPWM13,
    DMAMUX_REQ_EPWM14,
    DMAMUX_REQ_EPWM15,
    DMAMUX_REQ_EPWM16,
    DMAMUX_REQ_EPWM17,
    /* reserved */
    DMAMUX_REQ_ETIMER0 = 55,
    DMAMUX_REQ_ETIMER1,
    DMAMUX_REQ_ETIMER2,
    DMAMUX_REQ_ETIMER3,
    DMAMUX_REQ_ETIMER4,
    DMAMUX_REQ_ETIMER5,
    DMAMUX_REQ_ETIMER6,
    DMAMUX_REQ_ETIMER7,
    DMAMUX_REQ_ETIMER8,
    DMAMUX_REQ_ETIMER9,
    DMAMUX_REQ_ETIMER10,
    DMAMUX_REQ_ETIMER11,
    DMAMUX_REQ_ADC0_0,
    DMAMUX_REQ_ADC0_1,
    DMAMUX_REQ_ADC0_2,
    DMAMUX_REQ_ADC0_3,
    DMAMUX_REQ_ADC0EVT,
    DMAMUX_REQ_ADC1_0,
    DMAMUX_REQ_ADC1_1,
    DMAMUX_REQ_ADC1_2,
    DMAMUX_REQ_ADC1_3,
    DMAMUX_REQ_ADC1EVT,
    DMAMUX_REQ_ADC2_0,
    DMAMUX_REQ_ADC2_1,
    DMAMUX_REQ_ADC2_2,
    DMAMUX_REQ_ADC2_3,
    DMAMUX_REQ_ADC2EVT,
    DMAMUX_REQ_ACMP0H_DAC0,
    DMAMUX_REQ_ACMP0L_DAC1,
    DMAMUX_REQ_ACMP1H_DAC0,
    DMAMUX_REQ_ACMP1L_DAC1,
    DMAMUX_REQ_ACMP2H_DAC0,
    DMAMUX_REQ_ACMP2L_DAC1,
    DMAMUX_REQ_ACMP3H_DAC0,
    DMAMUX_REQ_ACMP3L_DAC1,
    DMAMUX_REQ_ACMP4H_DAC0,
    DMAMUX_REQ_ACMP4L_DAC1,
    DMAMUX_REQ_ACMP5H_DAC0,
    DMAMUX_REQ_ACMP5L_DAC1,
    DMAMUX_REQ_ACMP6H_DAC0,
    DMAMUX_REQ_ACMP6L_DAC1,
    DMAMUX_REQ_ACMP7H_DAC0,
    DMAMUX_REQ_ACMP7L_DAC1,
    DMAMUX_REQ_ACMP8H_DAC0,
    DMAMUX_REQ_ACMP8L_DAC1,
    DMAMUX_REQ_ACMP9H_DAC0,
    DMAMUX_REQ_ACMP9L_DAC1,
    DMAMUX_REQ_ACMP10H_DAC0,
    DMAMUX_REQ_ACMP10L_DAC1,
    DMAMUX_REQ_STIMER0,
    DMAMUX_REQ_STIMER1,
    DMAMUX_REQ_STIMER2,
    DMAMUX_REQ_STIMER3,
    DMAMUX_REQ_STIMER4,
    DMAMUX_REQ_STIMER5,
    DMAMUX_REQ_DAC0,
    DMAMUX_REQ_DAC1,
    DMAMUX_REQ_AES_WR,
    DMAMUX_REQ_AES_RD,
    DMAMUX_REQ_WAG,
    DMAMUX_REQ_XINT0,
    DMAMUX_REQ_XINT1,
    DMAMUX_REQ_XINT2,
    DMAMUX_REQ_XINT3,
    DMAMUX_REQ_XINT4,
    DMAMUX_REQ_CLB0_INT,
    DMAMUX_REQ_CLB1_INT,
    DMAMUX_REQ_CLB2_INT,
    DMAMUX_REQ_CLB3_INT,
    DMAMUX_REQ_CLB4_INT,
    DMAMUX_REQ_CLB5_INT,
    DMAMUX_REQ_LIN0_TX,
    DMAMUX_REQ_LIN0_RX,
    DMAMUX_REQ_LIN1_TX,
    DMAMUX_REQ_LIN1_RX,
    /* reserved */
    DMAMUX_REQ_UART0_TX = 192,
    DMAMUX_REQ_UART0_RX,
    DMAMUX_REQ_UART1_TX,
    DMAMUX_REQ_UART1_RX,
    DMAMUX_REQ_UART2_TX,
    DMAMUX_REQ_UART2_RX,
    DMAMUX_REQ_UART3_TX,
    DMAMUX_REQ_UART3_RX,
    DMAMUX_REQ_UART4_TX,
    DMAMUX_REQ_UART4_RX,
    DMAMUX_REQ_UART5_TX,
    DMAMUX_REQ_UART5_RX,
    DMAMUX_REQ_UART6_TX,
    DMAMUX_REQ_UART6_RX,
    DMAMUX_REQ_UART7_TX,
    DMAMUX_REQ_UART7_RX,
    DMAMUX_REQ_I2C0_TX,
    DMAMUX_REQ_I2C0_RX,
    DMAMUX_REQ_I2C1_TX,
    DMAMUX_REQ_I2C1_RX,
    DMAMUX_REQ_I2C2_TX,
    DMAMUX_REQ_I2C2_RX,
    DMAMUX_REQ_SPI0_TX,
    DMAMUX_REQ_SPI0_RX,
    DMAMUX_REQ_SPI1_TX,
    DMAMUX_REQ_SPI1_RX,
    DMAMUX_REQ_SPI2_TX,
    DMAMUX_REQ_SPI2_RX,
    DMAMUX_REQ_SPI3_TX,
    DMAMUX_REQ_SPI3_RX,
    DMAMUX_REQ_CAN0_TX,
    DMAMUX_REQ_CAN0_RX,
    DMAMUX_REQ_CAN1_TX,
    DMAMUX_REQ_CAN1_RX,
    DMAMUX_REQ_CAN2_TX,
    DMAMUX_REQ_CAN2_RX,
    DMAMUX_REQ_QSPI_TX,
    DMAMUX_REQ_QSPI_RX
} SYSCTRL_DMAReqIdx;

/**
 * @brief System fault interrupt source definition
 * @note
 */
//*****************************************************************************
//
// Interrupt flags for use with SYSCTRL_enableInterrupt(), SYSCTRL_disableInterrupt(),
// SYSCTRL_clearInterruptStatus() & SYSCTRL_getInterruptStatus() functions.
//
//*****************************************************************************

#define SYSCTRL_INT_ERR_OSC25M_LOST       0x00000001U     //!< osc 25MHz lost
#define SYSCTRL_INT_ERR_XO25M_LOST        0x00000002U     //!< xo 25MHz lost
#define SYSCTRL_INT_ERR_PLL0_LOST         0x00000004U     //!< pll0 lost
#define SYSCTRL_INT_ERR_PLL0_UNLOCK       0x00000008U     //!< pll0 unlock
#define SYSCTRL_INT_ERR_PMU_BORH          0x00000010U     //!< pmu borh
#define SYSCTRL_INT_ERR_PMU_BORH_WARN     0x00000020U     //!< pmu borh warn
#define SYSCTRL_INT_ERR_PMU_OVRH          0x00000040U     //!< pmu ovrh
#define SYSCTRL_INT_ERR_PMU_BORL          0x00000080U     //!< pmu borl
#define SYSCTRL_INT_ERR_PMU_BORL_WARN     0x00000100U     //!< pmu borl warn
#define SYSCTRL_INT_ERR_PMU_OVRL          0x00000200U     //!< pmu power over voltage
#define SYSCTRL_INT_ERR_PMU_SYSLDO_OCP    0x00000400U     //!< pmu sysldo ocp
#define SYSCTRL_INT_ERR_TSD               0x00000800U     //!< tsensor over temperature
#define SYSCTRL_INT_ERR_TSD_WARN          0x00001000U     //!< tsensor warn


/**
 * @brief Analog PinMux configuration
 *  analog pinmux definitions format:
 *  \e SYSCTL_PINMUX_[pin_name]_MUX_[muxed_adc_signal]_[muxed_acmp_signal]
 *  SYSCTL_PINMUX: prefix
 *  pin_name: pin name, reference to datasheet 4.1 section
 *  MUX : connect character
 *  muxed_adc_signal   analog signal name after muxed select
 *  muxed_acmp_signal  analog signal name after muxed select
 *                     acmp signal format: CMPx_HPy_HNz_LPy_LNz   x= 1,2,3 y=0,1,2,3,4,5 z=0,1,2
 *
 */
//*****************************************************************************
//
// Analog PinMux select for use SYSCTRL_selectAnalogPinMux()
//
//*****************************************************************************

#define SYSCTL_PINMUX_C3_MUX_C3                                 0x00000001U
#define SYSCTL_PINMUX_C6_MUX_C6                                 0x00000002U
#define SYSCTL_PINMUX_B1_MUX_B1                                 0x00000004U
#define SYSCTL_PINMUX_C7_MUX_C7                                 0x00000008U
#define SYSCTL_PINMUX_C0_MUX_C0                                 0x00000010U
#define SYSCTL_PINMUX_A8_B0_C11_MUX_A8_CMP3_HP4_LP4             0x00000020U
#define SYSCTL_PINMUX_A4_B8_C14_MUX_A4_CMP1_HP0_LP0             0x00000040U
#define SYSCTL_PINMUX_C8_MUX_C8                                 0x00000080U
#define SYSCTL_PINMUX_C10_MUX_C10                               0x00000100U
#define SYSCTL_PINMUX_C11_MUX_C11                               0x00000200U
#define SYSCTL_PINMUX_A3_C5_MUX_A3_CMP2_HP5_LP5                 0x00000400U
#define SYSCTL_PINMUX_A5_MUX_A5_CMP1_HP5_LP5                    0x00000800U   /*!< 80pin:17 128pin:28 144pin:28 */
#define SYSCTL_PINMUX_A15_B9_C7_MUX_B9                          0x00001000U
#define SYSCTL_PINMUX_A15_B9_C7_MUX_C7                          0x00002000U
#define SYSCTL_PINMUX_A4_B8_C14_MUX_B8_CMP1_HP0_LP0             0x00004000U
#define SYSCTL_PINMUX_A4_B8_C14_MUX_C14_CMP3_HP3_HN0_LP3_LN0    0x00008000U
#define SYSCTL_PINMUX_C14_MUX_C14_CMP3_HP3_HN0_LP3_LN0          0x00010200U
#define SYSCTL_PINMUX_B0_C11_MUX_B0_CMP1_HP4_LP4                0x00010400U
#define SYSCTL_PINMUX_A8_B0_C11_MUX_B0_CMP1_HP4_LP4             0x00020001U
#define SYSCTL_PINMUX_A8_B0_C11_MUX_C11_CMP1_HP4_LP4            0x00020002U
#define SYSCTL_PINMUX_A7_C3_MUX_C3                              0x00020004U
#define SYSCTL_PINMUX_B2_C6_MUX_C6                              0x00020008U
#define SYSCTL_PINMUX_A10_B1_C10_MUX_B1                         0x00020010U
#define SYSCTL_PINMUX_A3_B9_C7_MUX_C7                           0x00020020U
#define SYSCTL_PINMUX_A11_B10_C0_MUX_C0                         0x00020040U
#define SYSCTL_PINMUX_A8_MUX_A8_CMP3_HP4_LP4                    0x00020080U
#define SYSCTL_PINMUX_A4_B8_MUX_A4_CMP1_HP0_LP0                 0x00020100U
#define SYSCTL_PINMUX_B4_C8_MUX_C8                              0x00020200U
#define SYSCTL_PINMUX_A10_B1_C10_MUX_C10                        0x00020400U
#define SYSCTL_PINMUX_B0_C11_MUX_C11_CMP1_HP4_LP4               0x00020800U
#define SYSCTL_PINMUX_A3_B9_C7_MUX_A3_CMP2_HP5_LP5              0x00021000U
#define SYSCTL_PINMUX_A5_2_MUX_A5_CMP1_HP5_LP5                  0x00022000U   /*!< 100pin:35 128pin:45 144pin:50 */
#define SYSCTL_PINMUX_A3_B9_C7_MUX_B9                           0x00024000U
#define SYSCTL_PINMUX_A4_B8_MUX_B8_CMP1_HP0_LP0                 0x00028000U


/**
 * @brief  Analog Reference value Definition, used for DAC reference and ACMP DAC reference
 *
 */
#define SYSCTRL_ANALOG_REF_2P5     0x00
#define SYSCTRL_ANALOG_REF_1P65    0x01


/* SYSC Keys */
#define SYSC_LOCK_KEY      0x00123456
#define SYSC_UNLOCK_KEY    0x12345678

/**
 * @brief Unlocks the system control registers to allow modifications.
 *
 * This function writes the predefined unlock key to the system control lock register,
 * permitting changes to protected system control registers.
 */
static inline void SYSC_unlockCriticalRegs(void)
{
    WRITE_REG(SYSC->NV, SYSC_UNLOCK_KEY);
}

/**
 * @brief Locks the system control registers to prevent unintended modifications.
 *
 * This function writes the predefined lock key to the system control lock register,
 * ensuring that protected system control registers cannot be altered until unlocked.
 */
static inline void SYSC_lockCriticalRegs(void)
{
    WRITE_REG(SYSC->NV, SYSC_LOCK_KEY);
}

void SYSCTRL_selectSYSCNTClockSource(SYSCTRL_SYSCNTClockSource clkSrc);
uint32_t SYSCTRL_getSYSCNTClock(void);
void SYSCTRL_performGlobalSoftReset(void);

uint8_t SYSCTRL_findDMAMuxFreeInterface(AHBDMA_Type *AHBDMAx);
void SYSCTRL_configDMAMux(AHBDMA_Type *AHBDMAx, uint8_t interface, SYSCTRL_DMAReqIdx reqIdx);
void SYSCTRL_configDMAMuxReqMode(AHBDMA_Type *AHBDMAx, uint8_t interface, SYSCTRL_DMAReqMode mode);
void SYSCTRL_freeDMAMuxInterface(AHBDMA_Type *AHBDMAx, uint8_t interface);

/* Flash functions */
void SYSCTRL_configFLASHDeepPowerDown(uint32_t flash_idx, bool isPowerDown);
uint8_t SYSCTRL_getFLASHOTAMode(void);
uint8_t SYSCTRL_getFLASHBankSwapMode(void);
void SYSCTRL_configFLASHOTAMode(bool enable);
void SYSCTRL_configFLASHBankSwapMode(bool enable);

/* Interrupt Functions */
void SYSCTRL_enableInterrupt(uint32_t intFlags);
void SYSCTRL_disableInterrupt(uint32_t intFlags);
void SYSCTRL_clearInterruptStatus(uint32_t intFlags);
uint32_t SYSCTRL_getInterruptStatus(uint32_t intFlags);
uint32_t SYSCTRL_getInterruptStatusRaw(uint32_t intFlags);
void SYSCTRL_setInterruptMask(uint32_t intFlags);
void SYSCTRL_clearInterruptMask(uint32_t intFlags);

/* Analog System */
void SYSCTRL_enableAnalogReferenceInternal(uint16_t reference);
void SYSCTRL_disableAnalogReferenceInternal(void);

void SYSCTRL_selectAnalogPinMux(uint32_t select);

/* Tsensor config */
void SYSCTRL_enableTemperatureSensor(void);
void SYSCTRL_disableTemperatureSensor(void);


/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif
#endif /*__ET6X_SYSCTRL_H */
