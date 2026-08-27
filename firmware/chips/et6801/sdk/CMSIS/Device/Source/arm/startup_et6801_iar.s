;******************** (C) COPYRIGHT 2025 ETMCU ********************
;* File Name          : startup_et6801.s
;* Author             : MCD Application Team
;* Version            : V1.1.2
;* Date               : 02-Nov-2022
;* Description        : ET6001 devices vector table for MDK-ARM toolchain. 
;*                      This module performs:
;*                      - Set the initial SP
;*                      - Set the initial PC == Reset_Handler
;*                      - Set the vector table entries with the exceptions ISR address
;*                      - Branches to __main in the C library (which eventually
;*                        calls main()).
;*                      After Reset the CortexM7 processor is in Thread mode,
;*                      priority is Privileged, and the Stack is set to Main.
;* <<< Use Configuration Wizard in Context Menu >>>   
;*******************************************************************************
; 
;* Redistribution and use in source and binary forms, with or without modification,
;* are permitted provided that the following conditions are met:
;*   1. Redistributions of source code must retain the above copyright notice,
;*      this list of conditions and the following disclaimer.
;*   2. Redistributions in binary form must reproduce the above copyright notice,
;*      this list of conditions and the following disclaimer in the documentation
;*      and/or other materials provided with the distribution.
;*   3. Neither the name of ETMCU nor the names of its contributors
;*      may be used to endorse or promote products derived from this software
;*      without specific prior written permission.
;*
;* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
;* AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
;* IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
;* DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
;* FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
;* DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
;* SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
;* CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
;* OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
;* OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
; 
;*******************************************************************************

; Copyright 2024 Watech Electronics
; All rights reserved.
;
; SPDX-License-Identifier: BSD-3-Clause
;

; Vector Table Mapped to Address 0 at Reset

                MODULE  ?cstartup

                ;; Forward declaration of sections.
                SECTION CSTACK:DATA:NOROOT(3)

                SECTION .intvec:CODE:NOROOT(2)

                EXTERN  __iar_program_start
                EXTERN  SystemInit
                PUBLIC   __vector_table
//                PUBLIC   __vector_table_0x1c
                PUBLIC   __Vectors
                PUBLIC   __Vectors_End
                PUBLIC   __Vectors_Size

                DATA

__vector_table
                DCD     sfe(CSTACK)                         ; Top of Stack
                DCD     Reset_Handler                       ; Reset Handler
                DCD     NMI_Handler                         ; NMI Handler
                DCD     HardFault_Handler                   ; Hard Fault Handler
                DCD     MemManage_Handler                   ; MPU Fault Handler
                DCD     BusFault_Handler                    ; Bus Fault Handler
                DCD     UsageFault_Handler                  ; Usage Fault Handler
                DCD     0x12                          ; Reserved
                DCD     0x34                          ; Reserved
                DCD     0                          ; Reserved
                DCD     0                          ; Reserved
                DCD     SVC_Handler                ; SVCall Handler
                DCD     DebugMon_Handler           ; Debug Monitor Handler
                DCD     0                          ; Reserved
                DCD     OS_CPU_PendSVHandler      ; PendSV Handler
                DCD     SysTick_Handler            ; SysTick Handler
                ; External Interrupts
                DCD     0
                DCD     0
                DCD     FMAC_IRQHandler
                DCD     AES_IRQHandler
                DCD     CRC_IRQHandler
                DCD     CORDIC_IRQHandler
                DCD     DMA0_TFR_IRQHandler
                DCD     DMA0_BLOCK_IRQHandler
                DCD     DMA0_SRCTRAN_IRQHandler
                DCD     DMA0_DSTTRAN_IRQHandler
                DCD     DMA0_ERROR_IRQHandler
                DCD     DMA0_COMBINED_IRQHandler
                DCD     DMA1_TFR_IRQHandler
                DCD     DMA1_BLOCK_IRQHandler
                DCD     DMA1_SRCTRAN_IRQHandler
                DCD     DMA1_DSTTRAN_IRQHandler
                DCD     DMA1_ERROR_IRQHandler
                DCD     DMA1_COMBINED_IRQHandler
                DCD     WDG0_IRQHandler
                DCD     WDG1_IRQHandler
                DCD     LIN0_FUNC_IRQHandler
                DCD     LIN0_ERR_IRQHandler
                DCD     LIN1_FUNC_IRQHandler
                DCD     LIN1_ERR_IRQHandler
                DCD     UART0_IRQHandler
                DCD     UART1_IRQHandler
                DCD     UART2_IRQHandler
                DCD     UART3_IRQHandler
                DCD     UART4_IRQHandler
                DCD     UART5_IRQHandler
                DCD     UART6_IRQHandler
                DCD     UART7_IRQHandler
                DCD     I2C0_IRQHandler
                DCD     I2C1_IRQHandler
                DCD     I2C2_IRQHandler
                DCD     SPI0_IRQHandler
                DCD     SPI1_IRQHandler
                DCD     SPI2_IRQHandler
                DCD     SPI3_IRQHandler
                DCD     CAN0_INT0_IRQHandler
                DCD     CAN0_INT1_IRQHandler
                DCD     CAN0_DMU_IRQHandler
                DCD     CAN1_INT0_IRQHandler
                DCD     CAN1_INT1_IRQHandler
                DCD     CAN1_DMU_IRQHandler
                DCD     CAN2_INT0_IRQHandler
                DCD     CAN2_INT1_IRQHandler
                DCD     CAN2_DMU_IRQHandler
                DCD     CAN_ECC_IRQHandler
                DCD     IPCM0_IRQHandler
                DCD     IPCM1_IRQHandler
                DCD     IPCM2_IRQHandler
                DCD     IPCM3_IRQHandler
                DCD     IPCM4_IRQHandler
                DCD     IPCM5_IRQHandler
                DCD     IPCM6_IRQHandler
                DCD     IPCM7_IRQHandler
                DCD     IPCM8_IRQHandler
                DCD     IPCM9_IRQHandler
                DCD     IPCM10_IRQHandler
                DCD     IPCM11_IRQHandler
                DCD     IPCM12_IRQHandler
                DCD     IPCM13_IRQHandler
                DCD     IPCM14_IRQHandler
                DCD     IPCM15_IRQHandler
                DCD     GPIOA_COMBINT_IRQHandler
                DCD     GPIOB_COMBINT_IRQHandler
                DCD     GPIOC_COMBINT_IRQHandler
                DCD     GPIOD_COMBINT_IRQHandler
                DCD     GPIOE_COMBINT_IRQHandler
                DCD     GPIOF_COMBINT_IRQHandler
                DCD     GPIOG_COMBINT_IRQHandler
                DCD     GPIOH_COMBINT_IRQHandler
                DCD     GPIOI_COMBINT_IRQHandler
                DCD     PBUS1_TIMEOUT_IRQHandler
                DCD     PBUS2_TIMEOUT_IRQHandler
                DCD     HBUS1_TIMEOUT_IRQHandler
                DCD     HBUS2_TIMEOUT_IRQHandler
                DCD     HBUS3_TIMEOUT_IRQHandler
                DCD     GPIOE_0_IRQHandler
                DCD     GPIOE_1_IRQHandler
                DCD     GPIOE_2_IRQHandler
                DCD     GPIOE_3_IRQHandler
                DCD     GPIOE_4_IRQHandler
                DCD     GPIOE_5_IRQHandler
                DCD     GPIOE_6_IRQHandler
                DCD     GPIOE_7_IRQHandler
                DCD     GPIOE_8_IRQHandler
                DCD     GPIOE_9_IRQHandler
                DCD     GPIOE_10_IRQHandler
                DCD     GPIOE_11_IRQHandler
                DCD     GPIOE_12_IRQHandler
                DCD     GPIOE_13_IRQHandler
                DCD     GPIOE_14_IRQHandler
                DCD     GPIOE_15_IRQHandler
                DCD     EFC1_IRQHandler
                DCD     EFC2_IRQHandler
                DCD     PBUS3_TIMEOUT_IRQHandler
                DCD     QSPI_IRQHandler
                DCD     SRAM0_ECC_SERR_IRQHandler
                DCD     SRAM0_ECC_MERR_IRQHandler
                DCD     SRAM1_ECC_SERR_IRQHandler
                DCD     SRAM1_ECC_MERR_IRQHandler
                DCD     CORE2PERI_TIMEOUT_IRQHandler
                DCD     PERI2CORE_TIMEOUT_IRQHandler
                DCD     CPU0_M7_MISC_IRQHandler
                DCD     CPU1_M7_MISC_IRQHandler
                DCD     ACMP0_IRQHandler
                DCD     ACMP1_IRQHandler
                DCD     ACMP2_IRQHandler
                DCD     ACMP3_IRQHandler
                DCD     ACMP4_IRQHandler
                DCD     ACMP5_IRQHandler
                DCD     ACMP6_IRQHandler
                DCD     ACMP7_IRQHandler
                DCD     ACMP8_IRQHandler
                DCD     ACMP9_IRQHandler
                DCD     ACMP10_IRQHandler
                DCD     DAC0_IRQHandler
                DCD     DAC1_IRQHandler
                DCD     ADC0_EVTINT_IRQHandler
                DCD     ADC0_INT0_IRQHandler
                DCD     ADC0_INT1_IRQHandler
                DCD     ADC0_INT2_IRQHandler
                DCD     ADC0_INT3_IRQHandler
                DCD     ADC1_EVTINT_IRQHandler
                DCD     ADC1_INT0_IRQHandler
                DCD     ADC1_INT1_IRQHandler
                DCD     ADC1_INT2_IRQHandler
                DCD     ADC1_INT3_IRQHandler
                DCD     ADC2_EVTINT_IRQHandler
                DCD     ADC2_INT0_IRQHandler
                DCD     ADC2_INT1_IRQHandler
                DCD     ADC2_INT2_IRQHandler
                DCD     ADC2_INT3_IRQHandler
                DCD     QEP0_IRQHandler
                DCD     QEP1_IRQHandler
                DCD     QEP2_IRQHandler
                DCD     QEP3_IRQHandler
                DCD     QEP4_IRQHandler
                DCD     QEP5_IRQHandler
                DCD     SDFM0_ERR_IRQHandler
                DCD     SDFM0_DR0_IRQHandler
                DCD     SDFM0_DR1_IRQHandler
                DCD     SDFM0_DR2_IRQHandler
                DCD     SDFM0_DR3_IRQHandler
                DCD     SDFM1_ERR_IRQHandler
                DCD     SDFM1_DR0_IRQHandler
                DCD     SDFM1_DR1_IRQHandler
                DCD     SDFM1_DR2_IRQHandler
                DCD     SDFM1_DR3_IRQHandler
                DCD     SDFM2_ERR_IRQHandler
                DCD     SDFM2_DR0_IRQHandler
                DCD     SDFM2_DR1_IRQHandler
                DCD     SDFM2_DR2_IRQHandler
                DCD     SDFM2_DR3_IRQHandler
                DCD     SDFM3_ERR_IRQHandler
                DCD     SDFM3_DR0_IRQHandler
                DCD     SDFM3_DR1_IRQHandler
                DCD     SDFM3_DR2_IRQHandler
                DCD     SDFM3_DR3_IRQHandler
                DCD     STIMER0_IRQHandler
                DCD     STIMER1_IRQHandler
                DCD     STIMER2_IRQHandler
                DCD     STIMER3_IRQHandler
                DCD     STIMER4_IRQHandler
                DCD     STIMER5_IRQHandler
                DCD     ETIMER0_IRQHandler
                DCD     ETIMER1_IRQHandler
                DCD     ETIMER2_IRQHandler
                DCD     ETIMER3_IRQHandler
                DCD     ETIMER4_IRQHandler
                DCD     ETIMER5_IRQHandler
                DCD     ETIMER6_IRQHandler
                DCD     ETIMER7_IRQHandler
                DCD     ETIMER8_IRQHandler
                DCD     ETIMER9_IRQHandler
                DCD     ETIMER10_IRQHandler
                DCD     ETIMER11_IRQHandler
                DCD     SRPWM0_IRQHandler
                DCD     SRPWM1_IRQHandler
                DCD     SRPWM2_IRQHandler
                DCD     SRPWM3_IRQHandler
                DCD     SRPWM4_IRQHandler
                DCD     SRPWM5_IRQHandler
                DCD     SRPWM6_IRQHandler
                DCD     SRPWM7_IRQHandler
                DCD     SRPWM8_IRQHandler
                DCD     SRPWM9_IRQHandler
                DCD     SRPWM10_IRQHandler
                DCD     SRPWM11_IRQHandler
                DCD     SRPWM12_IRQHandler
                DCD     SRPWM13_IRQHandler
                DCD     SRPWM14_IRQHandler
                DCD     SRPWM15_IRQHandler
                DCD     SRPWM16_IRQHandler
                DCD     SRPWM17_IRQHandler
                DCD     SYSC_IRQHandler
                DCD     CORE2CORE_IRQHandler
                DCD     XBAR_INT0_IRQHandler
                DCD     XBAR_INT1_IRQHandler
                DCD     XBAR_INT2_IRQHandler
                DCD     XBAR_INT3_IRQHandler
                DCD     XBAR_INT4_IRQHandler
                DCD     XBAR_INT5_IRQHandler
                DCD     CLB_INT0_IRQHandler
                DCD     CLB_INT1_IRQHandler
                DCD     CLB_INT2_IRQHandler
                DCD     CLB_INT3_IRQHandler
                DCD     CLB_INT4_IRQHandler
                DCD     CLB_INT5_IRQHandler
__Vectors_End

__Vectors       EQU      __vector_table
__Vectors_Size  EQU      __Vectors_End - __Vectors


                THUMB


; Reset handler
                PUBWEAK Reset_Handler
                SECTION .text:CODE:NOROOT:REORDER(2)
Reset_Handler
                CPSID    I                                   ; Mask interrupts
VTOR            EQU      0xE000ED08
                LDR      R0, =VTOR
                LDR      R1, =__Vectors                      ; Set VTOR
                STR      R1, [R0]
                LDR      R2, [R1]
                MSR      MSP, R2                             ; Set MSP
                LDR      R0, =SystemInit
                BLX      R0
                CPSIE    I                                   ; Unmask interrupts
                LDR      R0, =__iar_program_start
                BX       R0

;
; Macro to define default exception/interrupt handlers.
; Default handler are weak symbols calling driver handlers.
; Users can re-define the symbols to implement their own exception/interrupt handlers.
;
Set_Default_Handler MACRO Handler_Name, DriverHandler_Name
                PUBWEAK Handler_Name
                PUBWEAK DriverHandler_Name
                SECTION .text:CODE:REORDER:NOROOT(2)
Handler_Name
                LDR      R0, =DriverHandler_Name
                BX       R0
                ENDM

; Default exception/interrupt handler
                Set_Default_Handler  NMI_Handler, NMI_DriverHandler
                Set_Default_Handler  HardFault_Handler, HardFault_DriverHandler
                Set_Default_Handler  MemManage_Handler, MemManage_DriverHandler
                Set_Default_Handler  BusFault_Handler, BusFault_DriverHandler
                Set_Default_Handler  UsageFault_Handler, UsageFault_DriverHandler
                Set_Default_Handler  SVC_Handler, SVC_DriverHandler
                Set_Default_Handler  DebugMon_Handler, DebugMon_DriverHandler
                Set_Default_Handler  OS_CPU_PendSVHandler, OS_CPU_PendSV_DriverHandler
                Set_Default_Handler  SysTick_Handler, SysTick_DriverHandler

                Set_Default_Handler  FMAC_IRQHandler, AES_IRQHandler
                Set_Default_Handler  CRC_IRQHandler, CORDIC_IRQHandler
                Set_Default_Handler  DMA0_TFR_IRQHandler, DMA0_BLOCK_IRQHandler
                Set_Default_Handler  DMA0_SRCTRAN_IRQHandler, DMA0_DSTTRAN_IRQHandler
                Set_Default_Handler  DMA0_ERROR_IRQHandler, DMA0_COMBINED_IRQHandler
                Set_Default_Handler  DMA1_TFR_IRQHandler, DMA1_BLOCK_IRQHandler
                Set_Default_Handler  DMA1_SRCTRAN_IRQHandler, DMA1_DSTTRAN_IRQHandler
                Set_Default_Handler  DMA1_ERROR_IRQHandler, DMA1_COMBINED_IRQHandler
                Set_Default_Handler  WDG0_IRQHandler, WDG1_IRQHandler
                Set_Default_Handler  LIN0_FUNC_IRQHandler, LIN0_ERR_IRQHandler
                Set_Default_Handler  LIN1_FUNC_IRQHandler, LIN1_ERR_IRQHandler
                Set_Default_Handler  UART0_IRQHandler, UART1_IRQHandler
                Set_Default_Handler  UART2_IRQHandler, UART3_IRQHandler
                Set_Default_Handler  UART4_IRQHandler, UART5_IRQHandler
                Set_Default_Handler  UART6_IRQHandler, UART7_IRQHandler
                Set_Default_Handler  I2C0_IRQHandler, I2C1_IRQHandler
                Set_Default_Handler  I2C2_IRQHandler, SPI0_IRQHandler
                Set_Default_Handler  SPI1_IRQHandler, SPI2_IRQHandler
                Set_Default_Handler  SPI3_IRQHandler, CAN0_INT0_IRQHandler
                Set_Default_Handler  CAN0_INT1_IRQHandler, CAN0_DMU_IRQHandler
                Set_Default_Handler  CAN1_INT0_IRQHandler, CAN1_INT1_IRQHandler
                Set_Default_Handler  CAN1_DMU_IRQHandler, CAN2_INT0_IRQHandler
                Set_Default_Handler  CAN2_INT1_IRQHandler, CAN2_DMU_IRQHandler, CAN_ECC_IRQHandler
                Set_Default_Handler  IPCM0_IRQHandler, IPCM1_IRQHandler
                Set_Default_Handler  IPCM2_IRQHandler, IPCM3_IRQHandler
                Set_Default_Handler  IPCM4_IRQHandler, IPCM5_IRQHandler
                Set_Default_Handler  IPCM6_IRQHandler, IPCM7_IRQHandler
                Set_Default_Handler  IPCM8_IRQHandler, IPCM9_IRQHandler
                Set_Default_Handler  IPCM10_IRQHandler, IPCM11_IRQHandler
                Set_Default_Handler  IPCM12_IRQHandler, IPCM13_IRQHandler
                Set_Default_Handler  IPCM14_IRQHandler, IPCM15_IRQHandler
                Set_Default_Handler  GPIOA_COMBINT_IRQHandler, GPIOB_COMBINT_IRQHandler
                Set_Default_Handler  GPIOC_COMBINT_IRQHandler, GPIOD_COMBINT_IRQHandler
                Set_Default_Handler  GPIOE_COMBINT_IRQHandler, GPIOF_COMBINT_IRQHandler
                Set_Default_Handler  GPIOG_COMBINT_IRQHandler, GPIOH_COMBINT_IRQHandler
                Set_Default_Handler  GPIOI_COMBINT_IRQHandler, PBUS1_TIMEOUT_IRQHandler
                Set_Default_Handler  PBUS2_TIMEOUT_IRQHandler, HBUS1_TIMEOUT_IRQHandler
                Set_Default_Handler  HBUS2_TIMEOUT_IRQHandler, HBUS3_TIMEOUT_IRQHandler
                Set_Default_Handler  GPIOE_0_IRQHandler, GPIOE_1_IRQHandler
                Set_Default_Handler  GPIOE_2_IRQHandler, GPIOE_3_IRQHandler
                Set_Default_Handler  GPIOE_4_IRQHandler, GPIOE_5_IRQHandler
                Set_Default_Handler  GPIOE_6_IRQHandler, GPIOE_7_IRQHandler
                Set_Default_Handler  GPIOE_8_IRQHandler, GPIOE_9_IRQHandler
                Set_Default_Handler  GPIOE_10_IRQHandler, GPIOE_11_IRQHandler
                Set_Default_Handler  GPIOE_12_IRQHandler, GPIOE_13_IRQHandler
                Set_Default_Handler  GPIOE_14_IRQHandler, GPIOE_15_IRQHandler
                Set_Default_Handler  EFC0_IRQHandler, EFC1_IRQHandler
                Set_Default_Handler  PBUS3_TIMEOUT_IRQHandler, QSPI_IRQHandler
                Set_Default_Handler  SRAM0_ECC_SERR_IRQHandler, SRAM0_ECC_MERR_IRQHandler
                Set_Default_Handler  SRAM1_ECC_SERR_IRQHandler, SRAM1_ECC_MERR_IRQHandler
                Set_Default_Handler  CORE2PERI_TIMEOUT_IRQHandler, PERI2CORE_TIMEOUT_IRQHandler
                Set_Default_Handler  CPU0_M7_MISC_IRQHandler, CPU1_M7_MISC_IRQHandler
                Set_Default_Handler  ACMP0_IRQHandler, ACMP1_IRQHandler
                Set_Default_Handler  ACMP2_IRQHandler, ACMP3_IRQHandler
                Set_Default_Handler  ACMP4_IRQHandler, ACMP5_IRQHandler
                Set_Default_Handler  ACMP6_IRQHandler, ACMP7_IRQHandler
                Set_Default_Handler  ACMP8_IRQHandler, ACMP9_IRQHandler
                Set_Default_Handler  ACMP10_IRQHandler, DAC0_IRQHandler
                Set_Default_Handler  DAC1_IRQHandler, ADC0_EVTINT_IRQHandler
                Set_Default_Handler  ADC0_INT0_IRQHandler, ADC0_INT1_IRQHandler
                Set_Default_Handler  ADC0_INT2_IRQHandler, ADC0_INT3_IRQHandler
                Set_Default_Handler  ADC1_EVTINT_IRQHandler, ADC1_INT0_IRQHandler
                Set_Default_Handler  ADC1_INT1_IRQHandler, ADC1_INT2_IRQHandler
                Set_Default_Handler  ADC1_INT3_IRQHandler, QEP0_IRQHandler
                Set_Default_Handler  QEP1_IRQHandler, QEP2_IRQHandler
                Set_Default_Handler  QEP3_IRQHandler, QEP4_IRQHandler
                Set_Default_Handler  QEP5_IRQHandler, SDFM0_ERR_IRQHandler
                Set_Default_Handler  SDFM0_DR0_IRQHandler, SDFM0_DR1_IRQHandler
                Set_Default_Handler  SDFM0_DR2_IRQHandler, SDFM0_DR3_IRQHandler
                Set_Default_Handler  SDFM1_ERR_IRQHandler, SDFM1_DR0_IRQHandler
                Set_Default_Handler  SDFM1_DR1_IRQHandler, SDFM1_DR2_IRQHandler
                Set_Default_Handler  SDFM1_DR3_IRQHandler, SDFM2_ERR_IRQHandler
                Set_Default_Handler  SDFM2_DR0_IRQHandler, SDFM2_DR1_IRQHandler
                Set_Default_Handler  SDFM2_DR2_IRQHandler, SDFM2_DR3_IRQHandler
                Set_Default_Handler  SDFM3_ERR_IRQHandler, SDFM3_DR0_IRQHandler
                Set_Default_Handler  SDFM3_DR1_IRQHandler, SDFM3_DR2_IRQHandler
                Set_Default_Handler  SDFM3_DR3_IRQHandler, STIMER0_IRQHandler
                Set_Default_Handler  STIMER1_IRQHandler, STIMER2_IRQHandler
                Set_Default_Handler  STIMER3_IRQHandler, STIMER4_IRQHandler
                Set_Default_Handler  STIMER5_IRQHandler, ETIMER0_IRQHandler
                Set_Default_Handler  ETIMER1_IRQHandler, ETIMER2_IRQHandler
                Set_Default_Handler  ETIMER3_IRQHandler, ETIMER4_IRQHandler
                Set_Default_Handler  ETIMER5_IRQHandler, ETIMER6_IRQHandler
                Set_Default_Handler  ETIMER7_IRQHandler, ETIMER8_IRQHandler
                Set_Default_Handler  ETIMER9_IRQHandler, ETIMER10_IRQHandler
                Set_Default_Handler  ETIMER11_IRQHandler, SRPWM0_IRQHandler
                Set_Default_Handler  SRPWM1_IRQHandler, SRPWM2_IRQHandler
                Set_Default_Handler  SRPWM3_IRQHandler, SRPWM4_IRQHandler
                Set_Default_Handler  SRPWM5_IRQHandler, SRPWM6_IRQHandler
                Set_Default_Handler  SRPWM7_IRQHandler, SRPWM8_IRQHandler
                Set_Default_Handler  SRPWM9_IRQHandler, SRPWM10_IRQHandler
                Set_Default_Handler  SRPWM11_IRQHandler, SRPWM12_IRQHandler
                Set_Default_Handler  SRPWM13_IRQHandler, SRPWM14_IRQHandler
                Set_Default_Handler  SRPWM15_IRQHandler, SRPWM16_IRQHandler
                Set_Default_Handler  SRPWM17_IRQHandler, SYSC_IRQHandler
                Set_Default_Handler  CORE2CORE_IRQHandler, XBAR_INT0_IRQHandler
                Set_Default_Handler  XBAR_INT1_IRQHandler, XBAR_INT2_IRQHandler
                Set_Default_Handler  XBAR_INT3_IRQHandler, XBAR_INT4_IRQHandler
                Set_Default_Handler  XBAR_INT5_IRQHandler, CLB_INT0_IRQHandler
                Set_Default_Handler  CLB_INT1_IRQHandler, CLB_INT2_IRQHandler
                Set_Default_Handler  CLB_INT3_IRQHandler, CLB_INT4_IRQHandler
                Set_Default_Handler  CLB_INT5_IRQHandler

;
; Default exception/interrupt driver handlers are weak symbols with an endless loop,
; which will be overwritten by SDK driver handlers.
; Users can read the SDK driver handlers, 
; and learn how to write their own exception/interrupt handlers.
;

NMI_DriverHandler
HardFault_DriverHandler
MemManage_DriverHandler
BusFault_DriverHandler
UsageFault_DriverHandler
SVC_DriverHandler
DebugMon_DriverHandler
OS_CPU_PendSV_DriverHandler
SysTick_DriverHandler


FMAC_IRQHandler
AES_IRQHandler
CRC_IRQHandler
CORDIC_IRQHandler
DMA0_TFR_IRQHandler
DMA0_BLOCK_IRQHandler
DMA0_SRCTRAN_IRQHandler
DMA0_DSTTRAN_IRQHandler
DMA0_ERROR_IRQHandler
DMA0_COMBINED_IRQHandler
DMA1_TFR_IRQHandler
DMA1_BLOCK_IRQHandler
DMA1_SRCTRAN_IRQHandler
DMA1_DSTTRAN_IRQHandler
DMA1_ERROR_IRQHandler
DMA1_COMBINED_IRQHandler
WDG0_IRQHandler
WDG1_IRQHandler
LIN0_FUNC_IRQHandler
LIN0_ERR_IRQHandler
LIN1_FUNC_IRQHandler
LIN1_ERR_IRQHandler
UART0_IRQHandler
UART1_IRQHandler
UART2_IRQHandler
UART3_IRQHandler
UART4_IRQHandler
UART5_IRQHandler
UART6_IRQHandler
UART7_IRQHandler
I2C0_IRQHandler
I2C1_IRQHandler
I2C2_IRQHandler
SPI0_IRQHandler
SPI1_IRQHandler
SPI2_IRQHandler
SPI3_IRQHandler
CAN0_INT0_IRQHandler
CAN0_INT1_IRQHandler
CAN0_DMU_IRQHandler
CAN1_INT0_IRQHandler
CAN1_INT1_IRQHandler
CAN1_DMU_IRQHandler
CAN2_INT0_IRQHandler
CAN2_INT1_IRQHandler
CAN2_DMU_IRQHandler
CAN_ECC_IRQHandler
IPCM0_IRQHandler
IPCM1_IRQHandler
IPCM2_IRQHandler
IPCM3_IRQHandler
IPCM4_IRQHandler
IPCM5_IRQHandler
IPCM6_IRQHandler
IPCM7_IRQHandler
IPCM8_IRQHandler
IPCM9_IRQHandler
IPCM10_IRQHandler
IPCM11_IRQHandler
IPCM12_IRQHandler
IPCM13_IRQHandler
IPCM14_IRQHandler
IPCM15_IRQHandler
GPIOA_COMBINT_IRQHandler
GPIOB_COMBINT_IRQHandler
GPIOC_COMBINT_IRQHandler
GPIOD_COMBINT_IRQHandler
GPIOE_COMBINT_IRQHandler
GPIOF_COMBINT_IRQHandler
GPIOG_COMBINT_IRQHandler
GPIOH_COMBINT_IRQHandler
GPIOI_COMBINT_IRQHandler
PBUS1_TIMEOUT_IRQHandler
PBUS2_TIMEOUT_IRQHandler
HBUS1_TIMEOUT_IRQHandler
HBUS2_TIMEOUT_IRQHandler
HBUS3_TIMEOUT_IRQHandler
GPIOE_0_IRQHandler
GPIOE_1_IRQHandler
GPIOE_2_IRQHandler
GPIOE_3_IRQHandler
GPIOE_4_IRQHandler
GPIOE_5_IRQHandler
GPIOE_6_IRQHandler
GPIOE_7_IRQHandler
GPIOE_8_IRQHandler
GPIOE_9_IRQHandler
GPIOE_10_IRQHandler
GPIOE_11_IRQHandler
GPIOE_12_IRQHandler
GPIOE_13_IRQHandler
GPIOE_14_IRQHandler
GPIOE_15_IRQHandler
EFC1_IRQHandler
EFC2_IRQHandler
PBUS3_TIMEOUT_IRQHandler
QSPI_IRQHandler
SRAM0_ECC_SERR_IRQHandler
SRAM0_ECC_MERR_IRQHandler
SRAM1_ECC_SERR_IRQHandler
SRAM1_ECC_MERR_IRQHandler
CORE2PERI_TIMEOUT_IRQHandler
PERI2CORE_TIMEOUT_IRQHandler
CPU0_M7_MISC_IRQHandler
CPU1_M7_MISC_IRQHandler
ACMP0_IRQHandler
ACMP1_IRQHandler
ACMP2_IRQHandler
ACMP3_IRQHandler
ACMP4_IRQHandler
ACMP5_IRQHandler
ACMP6_IRQHandler
ACMP7_IRQHandler
ACMP8_IRQHandler
ACMP9_IRQHandler
ACMP10_IRQHandler
DAC0_IRQHandler
DAC1_IRQHandler
ADC0_EVTINT_IRQHandler
ADC0_INT0_IRQHandler
ADC0_INT1_IRQHandler
ADC0_INT2_IRQHandler
ADC0_INT3_IRQHandler
ADC1_EVTINT_IRQHandler
ADC1_INT0_IRQHandler
ADC1_INT1_IRQHandler
ADC1_INT2_IRQHandler
ADC1_INT3_IRQHandler
ADC2_EVTINT_IRQHandler
ADC2_INT0_IRQHandler
ADC2_INT1_IRQHandler
ADC2_INT2_IRQHandler
ADC2_INT3_IRQHandler
QEP0_IRQHandler
QEP1_IRQHandler
QEP2_IRQHandler
QEP3_IRQHandler
QEP4_IRQHandler
QEP5_IRQHandler
SDFM0_ERR_IRQHandler
SDFM0_DR0_IRQHandler
SDFM0_DR1_IRQHandler
SDFM0_DR2_IRQHandler
SDFM0_DR3_IRQHandler
SDFM1_ERR_IRQHandler
SDFM1_DR0_IRQHandler
SDFM1_DR1_IRQHandler
SDFM1_DR2_IRQHandler
SDFM1_DR3_IRQHandler
SDFM2_ERR_IRQHandler
SDFM2_DR0_IRQHandler
SDFM2_DR1_IRQHandler
SDFM2_DR2_IRQHandler
SDFM2_DR3_IRQHandler
SDFM3_ERR_IRQHandler
SDFM3_DR0_IRQHandler
SDFM3_DR1_IRQHandler
SDFM3_DR2_IRQHandler
SDFM3_DR3_IRQHandler
STIMER0_IRQHandler
STIMER1_IRQHandler
STIMER2_IRQHandler
STIMER3_IRQHandler
STIMER4_IRQHandler
STIMER5_IRQHandler
ETIMER0_IRQHandler
ETIMER1_IRQHandler
ETIMER2_IRQHandler
ETIMER3_IRQHandler
ETIMER4_IRQHandler
ETIMER5_IRQHandler
ETIMER6_IRQHandler
ETIMER7_IRQHandler
ETIMER8_IRQHandler
ETIMER9_IRQHandler
ETIMER10_IRQHandler
ETIMER11_IRQHandler
SRPWM0_IRQHandler
SRPWM1_IRQHandler
SRPWM2_IRQHandler
SRPWM3_IRQHandler
SRPWM4_IRQHandler
SRPWM5_IRQHandler
SRPWM6_IRQHandler
SRPWM7_IRQHandler
SRPWM8_IRQHandler
SRPWM9_IRQHandler
SRPWM10_IRQHandler
SRPWM11_IRQHandler
SRPWM12_IRQHandler
SRPWM13_IRQHandler
SRPWM14_IRQHandler
SRPWM15_IRQHandler
SRPWM16_IRQHandler
SRPWM17_IRQHandler
SYSC_IRQHandler
CORE2CORE_IRQHandler
XBAR_INT0_IRQHandler
XBAR_INT1_IRQHandler
XBAR_INT2_IRQHandler
XBAR_INT3_IRQHandler
XBAR_INT4_IRQHandler
XBAR_INT5_IRQHandler
CLB_INT0_IRQHandler
CLB_INT1_IRQHandler
CLB_INT2_IRQHandler
CLB_INT3_IRQHandler
CLB_INT4_IRQHandler
CLB_INT5_IRQHandler

                B        .


                END
                
                