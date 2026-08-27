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
#include "et6x_interrupt.h"

void FMAC_IRQHandler(void);
void AES_IRQHandler(void);
void CRC_IRQHandler(void);
void CORDIC_IRQHandler(void);
void DMA0_TFR_IRQHandler(void);
void DMA0_BLOCK_IRQHandler(void);
void DMA0_SRCTRAN_IRQHandler(void);
void DMA0_DSTTRAN_IRQHandler(void);
void DMA0_ERROR_IRQHandler(void);
void DMA0_COMBINED_IRQHandler(void);
void DMA1_TFR_IRQHandler(void);
void DMA1_BLOCK_IRQHandler(void);
void DMA1_SRCTRAN_IRQHandler(void);
void DMA1_DSTTRAN_IRQHandler(void);
void DMA1_ERROR_IRQHandler(void);
void DMA1_COMBINED_IRQHandler(void);
void WDG0_IRQHandler(void);
void WDG1_IRQHandler(void);
void LIN0_FUNC_IRQHandler(void);
void LIN0_ERR_IRQHandler(void);
void LIN1_FUNC_IRQHandler(void);
void LIN1_ERR_IRQHandler(void);
void UART0_IRQHandler(void);
void UART1_IRQHandler(void);
void UART2_IRQHandler(void);
void UART3_IRQHandler(void);
void UART4_IRQHandler(void);
void UART5_IRQHandler(void);
void UART6_IRQHandler(void);
void UART7_IRQHandler(void);
void I2C0_IRQHandler(void);
void I2C1_IRQHandler(void);
void I2C2_IRQHandler(void);
void SPI0_IRQHandler(void);
void SPI1_IRQHandler(void);
void SPI2_IRQHandler(void);
void SPI3_IRQHandler(void);
void CAN0_INT0_IRQHandler(void);
void CAN0_INT1_IRQHandler(void);
void CAN0_DMU_IRQHandler(void);
void CAN1_INT0_IRQHandler(void);
void CAN1_INT1_IRQHandler(void);
void CAN1_DMU_IRQHandler(void);
void CAN2_INT0_IRQHandler(void);
void CAN2_INT1_IRQHandler(void);
void CAN2_DMU_IRQHandler(void);
void CAN_ECC_IRQHandler(void);
void IPCM0_IRQHandler(void);
void IPCM1_IRQHandler(void);
void IPCM2_IRQHandler(void);
void IPCM3_IRQHandler(void);
void IPCM4_IRQHandler(void);
void IPCM5_IRQHandler(void);
void IPCM6_IRQHandler(void);
void IPCM7_IRQHandler(void);
void IPCM8_IRQHandler(void);
void IPCM9_IRQHandler(void);
void IPCM10_IRQHandler(void);
void IPCM11_IRQHandler(void);
void IPCM12_IRQHandler(void);
void IPCM13_IRQHandler(void);
void IPCM14_IRQHandler(void);
void IPCM15_IRQHandler(void);
void GPIOA_COMBINT_IRQHandler(void);
void GPIOB_COMBINT_IRQHandler(void);
void GPIOC_COMBINT_IRQHandler(void);
void GPIOD_COMBINT_IRQHandler(void);
void GPIOE_COMBINT_IRQHandler(void);
void GPIOF_COMBINT_IRQHandler(void);
void GPIOG_COMBINT_IRQHandler(void);
void GPIOH_COMBINT_IRQHandler(void);
void GPIOI_COMBINT_IRQHandler(void);
void PBUS1_TIMEOUT_IRQHandler(void);
void PBUS2_TIMEOUT_IRQHandler(void);
void HBUS1_TIMEOUT_IRQHandler(void);
void HBUS2_TIMEOUT_IRQHandler(void);
void HBUS3_TIMEOUT_IRQHandler(void);
void GPIOE_0_IRQHandler(void);
void GPIOE_1_IRQHandler(void);
void GPIOE_2_IRQHandler(void);
void GPIOE_3_IRQHandler(void);
void GPIOE_4_IRQHandler(void);
void GPIOE_5_IRQHandler(void);
void GPIOE_6_IRQHandler(void);
void GPIOE_7_IRQHandler(void);
void GPIOE_8_IRQHandler(void);
void GPIOE_9_IRQHandler(void);
void GPIOE_10_IRQHandler(void);
void GPIOE_11_IRQHandler(void);
void GPIOE_12_IRQHandler(void);
void GPIOE_13_IRQHandler(void);
void GPIOE_14_IRQHandler(void);
void GPIOE_15_IRQHandler(void);
void EFC1_IRQHandler(void);
void EFC2_IRQHandler(void);
void PBUS3_TIMEOUT_IRQHandler(void);
void QSPI_IRQHandler(void);
void SRAM0_ECC_SERR_IRQHandler(void);
void SRAM0_ECC_MERR_IRQHandler(void);
void SRAM1_ECC_SERR_IRQHandler(void);
void SRAM1_ECC_MERR_IRQHandler(void);
void CORE2PERI_TIMEOUT_IRQHandler(void);
void PERI2CORE_TIMEOUT_IRQHandler(void);
void CPU0_M7_MISC_IRQHandler(void);
void CPU1_M7_MISC_IRQHandler(void);
void ACMP0_IRQHandler(void);
void ACMP1_IRQHandler(void);
void ACMP2_IRQHandler(void);
void ACMP3_IRQHandler(void);
void ACMP4_IRQHandler(void);
void ACMP5_IRQHandler(void);
void ACMP6_IRQHandler(void);
void ACMP7_IRQHandler(void);
void ACMP8_IRQHandler(void);
void ACMP9_IRQHandler(void);
void ACMP10_IRQHandler(void);
void DAC0_IRQHandler(void);
void DAC1_IRQHandler(void);
void ADC0_EVTINT_IRQHandler(void);
void ADC0_INT0_IRQHandler(void);
void ADC0_INT1_IRQHandler(void);
void ADC0_INT2_IRQHandler(void);
void ADC0_INT3_IRQHandler(void);
void ADC1_EVTINT_IRQHandler(void);
void ADC1_INT0_IRQHandler(void);
void ADC1_INT1_IRQHandler(void);
void ADC1_INT2_IRQHandler(void);
void ADC1_INT3_IRQHandler(void);
void ADC2_EVTINT_IRQHandler(void);
void ADC2_INT0_IRQHandler(void);
void ADC2_INT1_IRQHandler(void);
void ADC2_INT2_IRQHandler(void);
void ADC2_INT3_IRQHandler(void);
void QEP0_IRQHandler(void);
void QEP1_IRQHandler(void);
void QEP2_IRQHandler(void);
void QEP3_IRQHandler(void);
void QEP4_IRQHandler(void);
void QEP5_IRQHandler(void);
void SDFM0_ERR_IRQHandler(void);
void SDFM0_DR0_IRQHandler(void);
void SDFM0_DR1_IRQHandler(void);
void SDFM0_DR2_IRQHandler(void);
void SDFM0_DR3_IRQHandler(void);
void SDFM1_ERR_IRQHandler(void);
void SDFM1_DR0_IRQHandler(void);
void SDFM1_DR1_IRQHandler(void);
void SDFM1_DR2_IRQHandler(void);
void SDFM1_DR3_IRQHandler(void);
void SDFM2_ERR_IRQHandler(void);
void SDFM2_DR0_IRQHandler(void);
void SDFM2_DR1_IRQHandler(void);
void SDFM2_DR2_IRQHandler(void);
void SDFM2_DR3_IRQHandler(void);
void SDFM3_ERR_IRQHandler(void);
void SDFM3_DR0_IRQHandler(void);
void SDFM3_DR1_IRQHandler(void);
void SDFM3_DR2_IRQHandler(void);
void SDFM3_DR3_IRQHandler(void);
void STIMER0_IRQHandler(void);
void STIMER1_IRQHandler(void);
void STIMER2_IRQHandler(void);
void STIMER3_IRQHandler(void);
void STIMER4_IRQHandler(void);
void STIMER5_IRQHandler(void);
void ETIMER0_IRQHandler(void);
void ETIMER1_IRQHandler(void);
void ETIMER2_IRQHandler(void);
void ETIMER3_IRQHandler(void);
void ETIMER4_IRQHandler(void);
void ETIMER5_IRQHandler(void);
void ETIMER6_IRQHandler(void);
void ETIMER7_IRQHandler(void);
void ETIMER8_IRQHandler(void);
void ETIMER9_IRQHandler(void);
void ETIMER10_IRQHandler(void);
void ETIMER11_IRQHandler(void);
void SRPWM0_IRQHandler(void);
void SRPWM1_IRQHandler(void);
void SRPWM2_IRQHandler(void);
void SRPWM3_IRQHandler(void);
void SRPWM4_IRQHandler(void);
void SRPWM5_IRQHandler(void);
void SRPWM6_IRQHandler(void);
void SRPWM7_IRQHandler(void);
void SRPWM8_IRQHandler(void);
void SRPWM9_IRQHandler(void);
void SRPWM10_IRQHandler(void);
void SRPWM11_IRQHandler(void);
void SRPWM12_IRQHandler(void);
void SRPWM13_IRQHandler(void);
void SRPWM14_IRQHandler(void);
void SRPWM15_IRQHandler(void);
void SRPWM16_IRQHandler(void);
void SRPWM17_IRQHandler(void);
void SYSC_IRQHandler(void);
void CORE2CORE_IRQHandler(void);
void XBAR_INT0_IRQHandler(void);
void XBAR_INT1_IRQHandler(void);
void XBAR_INT2_IRQHandler(void);
void XBAR_INT3_IRQHandler(void);
void XBAR_INT4_IRQHandler(void);
void XBAR_INT5_IRQHandler(void);
void CLB_INT0_IRQHandler(void);
void CLB_INT1_IRQHandler(void);
void CLB_INT2_IRQHandler(void);
void CLB_INT3_IRQHandler(void);
void CLB_INT4_IRQHandler(void);
void CLB_INT5_IRQHandler(void);

void (* vectorTable[INTERRUPT_MAX_IRQN])(void);

__attribute__((noreturn)) void Interrupt_defaultHandler(void)
{
    for ( ; ;)
    {
    }
}

void FMAC_IRQHandler(void)
{
    vectorTable[FMAC_IRQn + 16]();
}

void AES_IRQHandler(void)
{
    vectorTable[AES_IRQn + 16]();
}

void CRC_IRQHandler(void)
{
    vectorTable[CRC_IRQn + 16]();
}

void CORDIC_IRQHandler(void)
{
    vectorTable[CORDIC_IRQn + 16]();
}

void DMA0_TFR_IRQHandler(void)
{
    vectorTable[DMA0_TFR_IRQn + 16]();
}

void DMA0_BLOCK_IRQHandler(void)
{
    vectorTable[DMA0_BLOCK_IRQn + 16]();
}

void DMA0_SRCTRAN_IRQHandler(void)
{
    vectorTable[DMA0_SRCTRAN_IRQn + 16]();
}

void DMA0_DSTTRAN_IRQHandler(void)
{
    vectorTable[DMA0_DSTTRAN_IRQn + 16]();
}

void DMA0_ERROR_IRQHandler(void)
{
    vectorTable[DMA0_ERROR_IRQn + 16]();
}

void DMA0_COMBINED_IRQHandler(void)
{
    vectorTable[DMA0_COMBINED_IRQn + 16]();
}

void DMA1_TFR_IRQHandler(void)
{
    vectorTable[DMA1_TFR_IRQn + 16]();
}

void DMA1_BLOCK_IRQHandler(void)
{
    vectorTable[DMA1_BLOCK_IRQn + 16]();
}

void DMA1_SRCTRAN_IRQHandler(void)
{
    vectorTable[DMA1_SRCTRAN_IRQn + 16]();
}

void DMA1_DSTTRAN_IRQHandler(void)
{
    vectorTable[DMA1_DSTTRAN_IRQn + 16]();
}

void DMA1_ERROR_IRQHandler(void)
{
    vectorTable[DMA1_ERROR_IRQn + 16]();
}

void DMA1_COMBINED_IRQHandler(void)
{
    vectorTable[DMA1_COMBINED_IRQn + 16]();
}

void WDG0_IRQHandler(void)
{
    vectorTable[WDG0_IRQn + 16]();
}

void WDG1_IRQHandler(void)
{
    vectorTable[WDG1_IRQn + 16]();
}

void LIN0_FUNC_IRQHandler(void)
{
    vectorTable[LIN0_FUNC_IRQn + 16]();
}

void LIN0_ERR_IRQHandler(void)
{
    vectorTable[LIN0_ERR_IRQn + 16]();
}

void LIN1_FUNC_IRQHandler(void)
{
    vectorTable[LIN1_FUNC_IRQn + 16]();
}

void LIN1_ERR_IRQHandler(void)
{
    vectorTable[LIN1_ERR_IRQn + 16]();
}

void UART0_IRQHandler(void)
{
    vectorTable[UART0_IRQn + 16]();
}

void UART1_IRQHandler(void)
{
    vectorTable[UART1_IRQn + 16]();
}

void UART2_IRQHandler(void)
{
    vectorTable[UART2_IRQn + 16]();
}

void UART3_IRQHandler(void)
{
    vectorTable[UART3_IRQn + 16]();
}

void UART4_IRQHandler(void)
{
    vectorTable[UART4_IRQn + 16]();
}

void UART5_IRQHandler(void)
{
    vectorTable[UART5_IRQn + 16]();
}

void I2C0_IRQHandler(void)
{
    vectorTable[I2C0_IRQn + 16]();
}

void I2C1_IRQHandler(void)
{
    vectorTable[I2C1_IRQn + 16]();
}

void I2C2_IRQHandler(void)
{
    vectorTable[I2C2_IRQn + 16]();
}

void SPI0_IRQHandler(void)
{
    vectorTable[SPI0_IRQn + 16]();
}

void SPI1_IRQHandler(void)
{
    vectorTable[SPI1_IRQn + 16]();
}

void SPI2_IRQHandler(void)
{
    vectorTable[SPI2_IRQn + 16]();
}

void SPI3_IRQHandler(void)
{
    vectorTable[SPI3_IRQn + 16]();
}

void CAN0_INT0_IRQHandler(void)
{
    vectorTable[CAN0_INT0_IRQn + 16]();
}

void CAN0_INT1_IRQHandler(void)
{
    vectorTable[CAN0_INT1_IRQn + 16]();
}

void CAN0_DMU_IRQHandler(void)
{
    vectorTable[CAN0_DMU_IRQn + 16]();
}

void CAN1_INT0_IRQHandler(void)
{
    vectorTable[CAN1_INT0_IRQn + 16]();
}

void CAN1_INT1_IRQHandler(void)
{
    vectorTable[CAN1_INT1_IRQn + 16]();
}

void CAN1_DMU_IRQHandler(void)
{
    vectorTable[CAN1_DMU_IRQn + 16]();
}

void CAN2_INT0_IRQHandler(void)
{
    vectorTable[CAN2_INT0_IRQn + 16]();
}

void CAN2_INT1_IRQHandler(void)
{
    vectorTable[CAN2_INT1_IRQn + 16]();
}

void CAN2_DMU_IRQHandler(void)
{
    vectorTable[CAN2_DMU_IRQn + 16]();
}

void CAN_ECC_IRQHandler(void)
{
    vectorTable[CAN_ECC_IRQn + 16]();
}

void IPCM0_IRQHandler(void)
{
    vectorTable[IPCM0_IRQn + 16]();
}

void IPCM1_IRQHandler(void)
{
    vectorTable[IPCM1_IRQn + 16]();
}

void IPCM2_IRQHandler(void)
{
    vectorTable[IPCM2_IRQn + 16]();
}

void IPCM3_IRQHandler(void)
{
    vectorTable[IPCM3_IRQn + 16]();
}

void IPCM4_IRQHandler(void)
{
    vectorTable[IPCM4_IRQn + 16]();
}

void IPCM5_IRQHandler(void)
{
    vectorTable[IPCM5_IRQn + 16]();
}

void IPCM6_IRQHandler(void)
{
    vectorTable[IPCM6_IRQn + 16]();
}

void IPCM7_IRQHandler(void)
{
    vectorTable[IPCM7_IRQn + 16]();
}

void IPCM8_IRQHandler(void)
{
    vectorTable[IPCM8_IRQn + 16]();
}

void IPCM9_IRQHandler(void)
{
    vectorTable[IPCM9_IRQn + 16]();
}

void IPCM10_IRQHandler(void)
{
    vectorTable[IPCM10_IRQn + 16]();
}

void IPCM11_IRQHandler(void)
{
    vectorTable[IPCM11_IRQn + 16]();
}

void IPCM12_IRQHandler(void)
{
    vectorTable[IPCM12_IRQn + 16]();
}

void IPCM13_IRQHandler(void)
{
    vectorTable[IPCM13_IRQn + 16]();
}

void IPCM14_IRQHandler(void)
{
    vectorTable[IPCM14_IRQn + 16]();
}

void IPCM15_IRQHandler(void)
{
    vectorTable[IPCM15_IRQn + 16]();
}

void GPIOA_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOA_COMBINT_IRQn + 16]();
}

void GPIOB_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOB_COMBINT_IRQn + 16]();
}

void GPIOC_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOC_COMBINT_IRQn + 16]();
}

void GPIOD_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOD_COMBINT_IRQn + 16]();
}

void GPIOE_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOE_COMBINT_IRQn + 16]();
}

void GPIOF_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOF_COMBINT_IRQn + 16]();
}

void GPIOG_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOG_COMBINT_IRQn + 16]();
}

void GPIOH_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOH_COMBINT_IRQn + 16]();
}

void GPIOI_COMBINT_IRQHandler(void)
{
    vectorTable[GPIOI_COMBINT_IRQn + 16]();
}

void PBUS1_TIMEOUT_IRQHandler(void)
{
    vectorTable[PBUS1_TIMEOUT_IRQn + 16]();
}

void PBUS2_TIMEOUT_IRQHandler(void)
{
    vectorTable[PBUS2_TIMEOUT_IRQn + 16]();
}

void HBUS1_TIMEOUT_IRQHandler(void)
{
    vectorTable[HBUS1_TIMEOUT_IRQn + 16]();
}

void HBUS2_TIMEOUT_IRQHandler(void)
{
    vectorTable[HBUS2_TIMEOUT_IRQn + 16]();
}

void HBUS3_TIMEOUT_IRQHandler(void)
{
    vectorTable[HBUS3_TIMEOUT_IRQn + 16]();
}

void GPIOE_0_IRQHandler(void)
{
    vectorTable[GPIOE_0_IRQn + 16]();
}

void GPIOE_1_IRQHandler(void)
{
    vectorTable[GPIOE_1_IRQn + 16]();
}

void GPIOE_2_IRQHandler(void)
{
    vectorTable[GPIOE_2_IRQn + 16]();
}

void GPIOE_3_IRQHandler(void)
{
    vectorTable[GPIOE_3_IRQn + 16]();
}

void GPIOE_4_IRQHandler(void)
{
    vectorTable[GPIOE_4_IRQn + 16]();
}

void GPIOE_5_IRQHandler(void)
{
    vectorTable[GPIOE_5_IRQn + 16]();
}

void GPIOE_6_IRQHandler(void)
{
    vectorTable[GPIOE_6_IRQn + 16]();
}

void GPIOE_7_IRQHandler(void)
{
    vectorTable[GPIOE_7_IRQn + 16]();
}

void GPIOE_8_IRQHandler(void)
{
    vectorTable[GPIOE_8_IRQn + 16]();
}

void GPIOE_9_IRQHandler(void)
{
    vectorTable[GPIOE_9_IRQn + 16]();
}

void GPIOE_10_IRQHandler(void)
{
    vectorTable[GPIOE_10_IRQn + 16]();
}

void GPIOE_11_IRQHandler(void)
{
    vectorTable[GPIOE_11_IRQn + 16]();
}

void GPIOE_12_IRQHandler(void)
{
    vectorTable[GPIOE_12_IRQn + 16]();
}

void GPIOE_13_IRQHandler(void)
{
    vectorTable[GPIOE_13_IRQn + 16]();
}

void GPIOE_14_IRQHandler(void)
{
    vectorTable[GPIOE_14_IRQn + 16]();
}

void GPIOE_15_IRQHandler(void)
{
    vectorTable[GPIOE_15_IRQn + 16]();
}

void EFC1_IRQHandler(void)
{
    vectorTable[EFC1_IRQn + 16]();
}

void EFC2_IRQHandler(void)
{
    vectorTable[EFC2_IRQn + 16]();
}

void PBUS3_TIMEOUT_IRQHandler(void)
{
    vectorTable[PBUS3_TIMEOUT_IRQn + 16]();
}

void QSPI_IRQHandler(void)
{
    vectorTable[QSPI_IRQn + 16]();
}

void SRAM0_ECC_SERR_IRQHandler(void)
{
    vectorTable[SRAM0_ECC_SERR_IRQn + 16]();
}

void SRAM0_ECC_MERR_IRQHandler(void)
{
    vectorTable[SRAM0_ECC_MERR_IRQn + 16]();
}

void SRAM1_ECC_SERR_IRQHandler(void)
{
    vectorTable[SRAM1_ECC_SERR_IRQn + 16]();
}

void SRAM1_ECC_MERR_IRQHandler(void)
{
    vectorTable[SRAM1_ECC_MERR_IRQn + 16]();
}

void CORE2PERI_TIMEOUT_IRQHandler(void)
{
    vectorTable[CORE2PERI_TIMEOUT_IRQn + 16]();
}

void PERI2CORE_TIMEOUT_IRQHandler(void)
{
    vectorTable[PERI2CORE_TIMEOUT_IRQn + 16]();
}

void CPU0_M7_MISC_IRQHandler(void)
{
    vectorTable[CPU0_MISC_IRQn + 16]();
}

void CPU1_M7_MISC_IRQHandler(void)
{
    vectorTable[CPU1_MISC_IRQn + 16]();
}

void ACMP0_IRQHandler(void)
{
    vectorTable[ACMP0_IRQn + 16]();
}

void ACMP1_IRQHandler(void)
{
    vectorTable[ACMP1_IRQn + 16]();
}

void ACMP2_IRQHandler(void)
{
    vectorTable[ACMP2_IRQn + 16]();
}

void ACMP3_IRQHandler(void)
{
    vectorTable[ACMP3_IRQn + 16]();
}

void ACMP4_IRQHandler(void)
{
    vectorTable[ACMP4_IRQn + 16]();
}

void ACMP5_IRQHandler(void)
{
    vectorTable[ACMP5_IRQn + 16]();
}

void ACMP6_IRQHandler(void)
{
    vectorTable[ACMP6_IRQn + 16]();
}

void ACMP7_IRQHandler(void)
{
    vectorTable[ACMP7_IRQn + 16]();
}

void ACMP8_IRQHandler(void)
{
    vectorTable[ACMP8_IRQn + 16]();
}

void ACMP9_IRQHandler(void)
{
    vectorTable[ACMP9_IRQn + 16]();
}

void ACMP10_IRQHandler(void)
{
    vectorTable[ACMP10_IRQn + 16]();
}

void DAC0_IRQHandler(void)
{
    vectorTable[DAC0_IRQn + 16]();
}

void DAC1_IRQHandler(void)
{
    vectorTable[DAC1_IRQn + 16]();
}

void ADC0_EVTINT_IRQHandler(void)
{
    vectorTable[ADC0_EVTINT_IRQn + 16]();
}

void ADC0_INT0_IRQHandler(void)
{
    vectorTable[ADC0_INT0_IRQn + 16]();
}

void ADC0_INT1_IRQHandler(void)
{
    vectorTable[ADC0_INT1_IRQn + 16]();
}

void ADC0_INT2_IRQHandler(void)
{
    vectorTable[ADC0_INT2_IRQn + 16]();
}

void ADC0_INT3_IRQHandler(void)
{
    vectorTable[ADC0_INT3_IRQn + 16]();
}

void ADC1_EVTINT_IRQHandler(void)
{
    vectorTable[ADC1_EVTINT_IRQn + 16]();
}

void ADC1_INT0_IRQHandler(void)
{
    vectorTable[ADC1_INT0_IRQn + 16]();
}

void ADC1_INT1_IRQHandler(void)
{
    vectorTable[ADC1_INT1_IRQn + 16]();
}

void ADC1_INT2_IRQHandler(void)
{
    vectorTable[ADC1_INT2_IRQn + 16]();
}

void ADC1_INT3_IRQHandler(void)
{
    vectorTable[ADC1_INT3_IRQn + 16]();
}

void ADC2_EVTINT_IRQHandler(void)
{
    vectorTable[ADC2_EVTINT_IRQn + 16]();
}

void ADC2_INT0_IRQHandler(void)
{
    vectorTable[ADC2_INT0_IRQn + 16]();
}

void ADC2_INT1_IRQHandler(void)
{
    vectorTable[ADC2_INT1_IRQn + 16]();
}

void ADC2_INT2_IRQHandler(void)
{
    vectorTable[ADC2_INT2_IRQn + 16]();
}

void ADC2_INT3_IRQHandler(void)
{
    vectorTable[ADC2_INT3_IRQn + 16]();
}

void QEP0_IRQHandler(void)
{
    vectorTable[QEP0_IRQn + 16]();
}

void QEP1_IRQHandler(void)
{
    vectorTable[QEP1_IRQn + 16]();
}

void QEP2_IRQHandler(void)
{
    vectorTable[QEP2_IRQn + 16]();
}

void QEP3_IRQHandler(void)
{
    vectorTable[QEP3_IRQn + 16]();
}

void QEP4_IRQHandler(void)
{
    vectorTable[QEP4_IRQn + 16]();
}

void QEP5_IRQHandler(void)
{
    vectorTable[QEP5_IRQn + 16]();
}

void SDFM0_ERR_IRQHandler(void)
{
    vectorTable[SDFM0_ERR_IRQn + 16]();
}

void SDFM0_DR0_IRQHandler(void)
{
    vectorTable[SDFM0_DR0_IRQn + 16]();
}

void SDFM0_DR1_IRQHandler(void)
{
    vectorTable[SDFM0_DR1_IRQn + 16]();
}

void SDFM0_DR2_IRQHandler(void)
{
    vectorTable[SDFM0_DR2_IRQn + 16]();
}

void SDFM0_DR3_IRQHandler(void)
{
    vectorTable[SDFM0_DR3_IRQn + 16]();
}

void SDFM1_ERR_IRQHandler(void)
{
    vectorTable[SDFM1_ERR_IRQn + 16]();
}

void SDFM1_DR0_IRQHandler(void)
{
    vectorTable[SDFM1_DR0_IRQn + 16]();
}

void SDFM1_DR1_IRQHandler(void)
{
    vectorTable[SDFM1_DR1_IRQn + 16]();
}

void SDFM1_DR2_IRQHandler(void)
{
    vectorTable[SDFM1_DR2_IRQn + 16]();
}

void SDFM1_DR3_IRQHandler(void)
{
    vectorTable[SDFM1_DR3_IRQn + 16]();
}

void SDFM2_ERR_IRQHandler(void)
{
    vectorTable[SDFM2_ERR_IRQn + 16]();
}

void SDFM2_DR0_IRQHandler(void)
{
    vectorTable[SDFM2_DR0_IRQn + 16]();
}

void SDFM2_DR1_IRQHandler(void)
{
    vectorTable[SDFM2_DR1_IRQn + 16]();
}

void SDFM2_DR2_IRQHandler(void)
{
    vectorTable[SDFM2_DR2_IRQn + 16]();
}

void SDFM2_DR3_IRQHandler(void)
{
    vectorTable[SDFM2_DR3_IRQn + 16]();
}

void SDFM3_ERR_IRQHandler(void)
{
    vectorTable[SDFM3_ERR_IRQn + 16]();
}

void SDFM3_DR0_IRQHandler(void)
{
    vectorTable[SDFM3_DR0_IRQn + 16]();
}

void SDFM3_DR1_IRQHandler(void)
{
    vectorTable[SDFM3_DR1_IRQn + 16]();
}

void SDFM3_DR2_IRQHandler(void)
{
    vectorTable[SDFM3_DR2_IRQn + 16]();
}

void SDFM3_DR3_IRQHandler(void)
{
    vectorTable[SDFM3_DR3_IRQn + 16]();
}

void STIMER0_IRQHandler(void)
{
    vectorTable[STIMER0_IRQn + 16]();
}

void STIMER1_IRQHandler(void)
{
    vectorTable[STIMER1_IRQn + 16]();
}

void STIMER2_IRQHandler(void)
{
    vectorTable[STIMER2_IRQn + 16]();
}

void STIMER3_IRQHandler(void)
{
    vectorTable[STIMER3_IRQn + 16]();
}

void STIMER4_IRQHandler(void)
{
    vectorTable[STIMER4_IRQn + 16]();
}

void STIMER5_IRQHandler(void)
{
    vectorTable[STIMER5_IRQn + 16]();
}

void ETIMER0_IRQHandler(void)
{
    vectorTable[ETIMER0_IRQn + 16]();
}

void ETIMER1_IRQHandler(void)
{
    vectorTable[ETIMER1_IRQn + 16]();
}

void ETIMER2_IRQHandler(void)
{
    vectorTable[ETIMER2_IRQn + 16]();
}

void ETIMER3_IRQHandler(void)
{
    vectorTable[ETIMER3_IRQn + 16]();
}

void ETIMER4_IRQHandler(void)
{
    vectorTable[ETIMER4_IRQn + 16]();
}

void ETIMER5_IRQHandler(void)
{
    vectorTable[ETIMER5_IRQn + 16]();
}

void ETIMER6_IRQHandler(void)
{
    vectorTable[ETIMER6_IRQn + 16]();
}

void ETIMER7_IRQHandler(void)
{
    vectorTable[ETIMER7_IRQn + 16]();
}

void ETIMER8_IRQHandler(void)
{
    vectorTable[ETIMER8_IRQn + 16]();
}

void ETIMER9_IRQHandler(void)
{
    vectorTable[ETIMER9_IRQn + 16]();
}

void ETIMER10_IRQHandler(void)
{
    vectorTable[ETIMER10_IRQn + 16]();
}

void ETIMER11_IRQHandler(void)
{
    vectorTable[ETIMER11_IRQn + 16]();
}

void SRPWM0_IRQHandler(void)
{
    vectorTable[SRPWM0_IRQn + 16]();
}

void SRPWM1_IRQHandler(void)
{
    vectorTable[SRPWM1_IRQn + 16]();
}

void SRPWM2_IRQHandler(void)
{
    vectorTable[SRPWM2_IRQn + 16]();
}

void SRPWM3_IRQHandler(void)
{
    vectorTable[SRPWM3_IRQn + 16]();
}

void SRPWM4_IRQHandler(void)
{
    vectorTable[SRPWM4_IRQn + 16]();
}

void SRPWM5_IRQHandler(void)
{
    vectorTable[SRPWM5_IRQn + 16]();
}

void SRPWM6_IRQHandler(void)
{
    vectorTable[SRPWM6_IRQn + 16]();
}

void SRPWM7_IRQHandler(void)
{
    vectorTable[SRPWM7_IRQn + 16]();
}

void SRPWM8_IRQHandler(void)
{
    vectorTable[SRPWM8_IRQn + 16]();
}

void SRPWM9_IRQHandler(void)
{
    vectorTable[SRPWM9_IRQn + 16]();
}

void SRPWM10_IRQHandler(void)
{
    vectorTable[SRPWM10_IRQn + 16]();
}

void SRPWM11_IRQHandler(void)
{
    vectorTable[SRPWM11_IRQn + 16]();
}

void SRPWM12_IRQHandler(void)
{
    vectorTable[SRPWM12_IRQn + 16]();
}

void SRPWM13_IRQHandler(void)
{
    vectorTable[SRPWM13_IRQn + 16]();
}

void SRPWM14_IRQHandler(void)
{
    vectorTable[SRPWM14_IRQn + 16]();
}

void SRPWM15_IRQHandler(void)
{
    vectorTable[SRPWM15_IRQn + 16]();
}

void SRPWM16_IRQHandler(void)
{
    vectorTable[SRPWM16_IRQn + 16]();
}

void SRPWM17_IRQHandler(void)
{
    vectorTable[SRPWM17_IRQn + 16]();
}

void SYSC_IRQHandler(void)
{
    vectorTable[SYSC_IRQn + 16]();
}

void CORE2CORE_IRQHandler(void)
{
    vectorTable[CORE2CORE_IRQn + 16]();
}

void XBAR_INT0_IRQHandler(void)
{
    vectorTable[XBAR_INT0_IRQn + 16]();
}

void XBAR_INT1_IRQHandler(void)
{
    vectorTable[XBAR_INT1_IRQn + 16]();
}

void XBAR_INT2_IRQHandler(void)
{
    vectorTable[XBAR_INT2_IRQn + 16]();
}

void XBAR_INT3_IRQHandler(void)
{
    vectorTable[XBAR_INT3_IRQn + 16]();
}

void XBAR_INT4_IRQHandler(void)
{
    vectorTable[XBAR_INT4_IRQn + 16]();
}

void XBAR_INT5_IRQHandler(void)
{
    vectorTable[XBAR_INT5_IRQn + 16]();
}

void CLB_INT0_IRQHandler(void)
{
    vectorTable[CLB_INT0_IRQn + 16]();
}

void CLB_INT1_IRQHandler(void)
{
    vectorTable[CLB_INT1_IRQn + 16]();
}

void CLB_INT2_IRQHandler(void)
{
    vectorTable[CLB_INT2_IRQn + 16]();
}

void CLB_INT3_IRQHandler(void)
{
    vectorTable[CLB_INT3_IRQn + 16]();
}

void CLB_INT4_IRQHandler(void)
{
    vectorTable[CLB_INT4_IRQn + 16]();
}

void CLB_INT5_IRQHandler(void)
{
    vectorTable[CLB_INT5_IRQn + 16]();
}
