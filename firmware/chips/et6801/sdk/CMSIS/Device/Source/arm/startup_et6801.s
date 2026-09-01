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

; Amount of memory (in bytes) allocated for Stack
; Tailor this value to your application needs
; <h> Stack Configuration
;   <o> Stack Size (in Bytes) <0x0-0xFFFFFFFF:8>
; </h>

Stack_Size      EQU     0x00000800

                AREA    STACK, NOINIT, READWRITE, ALIGN=3
Stack_Mem       SPACE   Stack_Size
__initial_sp


; <h> Heap Configuration
;   <o>  Heap Size (in Bytes) <0x0-0xFFFFFFFF:8>
; </h>

Heap_Size       EQU     0x00000200

                AREA    HEAP, NOINIT, READWRITE, ALIGN=3
__heap_base
Heap_Mem        SPACE   Heap_Size
__heap_limit

                PRESERVE8
                THUMB


; Vector Table Mapped to Address 0 at Reset
                AREA    RESET, DATA, READONLY
                EXPORT  __Vectors
                EXPORT  __Vectors_End
                EXPORT  __Vectors_Size

__Vectors       DCD     __initial_sp               ; Top of Stack
                DCD     Reset_Handler              ; Reset Handler
                DCD     NMI_Handler                ; NMI Handler
                DCD     HardFault_Handler          ; Hard Fault Handler
                DCD     MemManage_Handler          ; MPU Fault Handler
                DCD     BusFault_Handler           ; Bus Fault Handler
                DCD     UsageFault_Handler         ; Usage Fault Handler
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

__Vectors_Size  EQU  __Vectors_End - __Vectors

                AREA    |.text|, CODE, READONLY

; Reset handler
Reset_Handler   PROC
                EXPORT  Reset_Handler             [WEAK]
                IMPORT  SystemInit
                IMPORT  __main

                LDR     R0, =__Vectors
                LDR     R1, =0xE000ED08 ;*VTOR register
                STR     R0,[R1]
                ;* C routines are likely to be called. Setup the stack now
                LDR     SP,=__initial_sp

                LDR     R0, =SystemInit
                BLX     R0
                LDR     R0, =__main
                BX      R0
                ENDP

; Dummy Exception Handlers (infinite loops which can be modified)
Default_Handler PROC
                EXPORT  NMI_Handler                                   [WEAK]
                EXPORT  HardFault_Handler                             [WEAK]
                EXPORT  MemManage_Handler                             [WEAK]
                EXPORT  BusFault_Handler                              [WEAK]
                EXPORT  UsageFault_Handler                            [WEAK]
                EXPORT  SVC_Handler                                   [WEAK]
                EXPORT  DebugMon_Handler                              [WEAK]
                EXPORT  OS_CPU_PendSVHandler                          [WEAK]
                EXPORT  SysTick_Handler                               [WEAK]
NMI_Handler
HardFault_Handler
MemManage_Handler
BusFault_Handler
UsageFault_Handler
SVC_Handler
DebugMon_Handler
OS_CPU_PendSVHandler
SysTick_Handler
                EXPORT  FMAC_IRQHandler                     [WEAK]
                EXPORT  AES_IRQHandler                      [WEAK]
                EXPORT  CRC_IRQHandler                      [WEAK]
                EXPORT  CORDIC_IRQHandler                   [WEAK]
                EXPORT  DMA0_TFR_IRQHandler                 [WEAK]
                EXPORT  DMA0_BLOCK_IRQHandler               [WEAK]
                EXPORT  DMA0_SRCTRAN_IRQHandler             [WEAK]
                EXPORT  DMA0_DSTTRAN_IRQHandler             [WEAK]
                EXPORT  DMA0_ERROR_IRQHandler               [WEAK]
                EXPORT  DMA0_COMBINED_IRQHandler            [WEAK]
                EXPORT  DMA1_TFR_IRQHandler                 [WEAK]
                EXPORT  DMA1_BLOCK_IRQHandler               [WEAK]
                EXPORT  DMA1_SRCTRAN_IRQHandler             [WEAK]
                EXPORT  DMA1_DSTTRAN_IRQHandler             [WEAK]
                EXPORT  DMA1_ERROR_IRQHandler               [WEAK]
                EXPORT  DMA1_COMBINED_IRQHandler            [WEAK]
                EXPORT  WDG0_IRQHandler                     [WEAK]
                EXPORT  WDG1_IRQHandler                     [WEAK]
                EXPORT  LIN0_FUNC_IRQHandler                [WEAK]
                EXPORT  LIN0_ERR_IRQHandler                 [WEAK]
                EXPORT  LIN1_FUNC_IRQHandler                [WEAK]
                EXPORT  LIN1_ERR_IRQHandler                 [WEAK]
                EXPORT  UART0_IRQHandler                    [WEAK]
                EXPORT  UART1_IRQHandler                    [WEAK]
                EXPORT  UART2_IRQHandler                    [WEAK]
                EXPORT  UART3_IRQHandler                    [WEAK]
                EXPORT  UART4_IRQHandler                    [WEAK]
                EXPORT  UART5_IRQHandler                    [WEAK]
                EXPORT  UART6_IRQHandler                    [WEAK]
                EXPORT  UART7_IRQHandler                    [WEAK]
                EXPORT  I2C0_IRQHandler                     [WEAK]
                EXPORT  I2C1_IRQHandler                     [WEAK]
                EXPORT  I2C2_IRQHandler                     [WEAK]
                EXPORT  SPI0_IRQHandler                     [WEAK]
                EXPORT  SPI1_IRQHandler                     [WEAK]
                EXPORT  SPI2_IRQHandler                     [WEAK]
                EXPORT  SPI3_IRQHandler                     [WEAK]
                EXPORT  CAN0_INT0_IRQHandler                [WEAK]
                EXPORT  CAN0_INT1_IRQHandler                [WEAK]
                EXPORT  CAN0_DMU_IRQHandler                 [WEAK]
                EXPORT  CAN1_INT0_IRQHandler                [WEAK]
                EXPORT  CAN1_INT1_IRQHandler                [WEAK]
                EXPORT  CAN1_DMU_IRQHandler                 [WEAK]
                EXPORT  CAN2_INT0_IRQHandler                [WEAK]
                EXPORT  CAN2_INT1_IRQHandler                [WEAK]
                EXPORT  CAN2_DMU_IRQHandler                 [WEAK]
                EXPORT  CAN_ECC_IRQHandler                  [WEAK]
                EXPORT  IPCM0_IRQHandler                    [WEAK]
                EXPORT  IPCM1_IRQHandler                    [WEAK]
                EXPORT  IPCM2_IRQHandler                    [WEAK]
                EXPORT  IPCM3_IRQHandler                    [WEAK]
                EXPORT  IPCM4_IRQHandler                    [WEAK]
                EXPORT  IPCM5_IRQHandler                    [WEAK]
                EXPORT  IPCM6_IRQHandler                    [WEAK]
                EXPORT  IPCM7_IRQHandler                    [WEAK]
                EXPORT  IPCM8_IRQHandler                    [WEAK]
                EXPORT  IPCM9_IRQHandler                    [WEAK]
                EXPORT  IPCM10_IRQHandler                   [WEAK]
                EXPORT  IPCM11_IRQHandler                   [WEAK]
                EXPORT  IPCM12_IRQHandler                   [WEAK]
                EXPORT  IPCM13_IRQHandler                   [WEAK]
                EXPORT  IPCM14_IRQHandler                   [WEAK]
                EXPORT  IPCM15_IRQHandler                   [WEAK]
                EXPORT  GPIOA_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOB_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOC_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOD_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOE_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOF_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOG_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOH_COMBINT_IRQHandler            [WEAK]
                EXPORT  GPIOI_COMBINT_IRQHandler            [WEAK]
                EXPORT  PBUS1_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  PBUS2_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  HBUS1_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  HBUS2_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  HBUS3_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  GPIOE_0_IRQHandler                  [WEAK]
                EXPORT  GPIOE_1_IRQHandler                  [WEAK]
                EXPORT  GPIOE_2_IRQHandler                  [WEAK]
                EXPORT  GPIOE_3_IRQHandler                  [WEAK]
                EXPORT  GPIOE_4_IRQHandler                  [WEAK]
                EXPORT  GPIOE_5_IRQHandler                  [WEAK]
                EXPORT  GPIOE_6_IRQHandler                  [WEAK]
                EXPORT  GPIOE_7_IRQHandler                  [WEAK]
                EXPORT  GPIOE_8_IRQHandler                  [WEAK]
                EXPORT  GPIOE_9_IRQHandler                  [WEAK]
                EXPORT  GPIOE_10_IRQHandler                 [WEAK]
                EXPORT  GPIOE_11_IRQHandler                 [WEAK]
                EXPORT  GPIOE_12_IRQHandler                 [WEAK]
                EXPORT  GPIOE_13_IRQHandler                 [WEAK]
                EXPORT  GPIOE_14_IRQHandler                 [WEAK]
                EXPORT  GPIOE_15_IRQHandler                 [WEAK]
                EXPORT  EFC1_IRQHandler                     [WEAK]
                EXPORT  EFC2_IRQHandler                     [WEAK]
                EXPORT  PBUS3_TIMEOUT_IRQHandler            [WEAK]
                EXPORT  QSPI_IRQHandler                     [WEAK]
                EXPORT  SRAM0_ECC_SERR_IRQHandler           [WEAK]
                EXPORT  SRAM0_ECC_MERR_IRQHandler           [WEAK]
                EXPORT  SRAM1_ECC_SERR_IRQHandler           [WEAK]
                EXPORT  SRAM1_ECC_MERR_IRQHandler           [WEAK]
                EXPORT  CORE2PERI_TIMEOUT_IRQHandler        [WEAK]
                EXPORT  PERI2CORE_TIMEOUT_IRQHandler        [WEAK]
                EXPORT  CPU0_M7_MISC_IRQHandler             [WEAK]
                EXPORT  CPU1_M7_MISC_IRQHandler             [WEAK]
                EXPORT  ACMP0_IRQHandler                    [WEAK]
                EXPORT  ACMP1_IRQHandler                    [WEAK]
                EXPORT  ACMP2_IRQHandler                    [WEAK]
                EXPORT  ACMP3_IRQHandler                    [WEAK]
                EXPORT  ACMP4_IRQHandler                    [WEAK]
                EXPORT  ACMP5_IRQHandler                    [WEAK]
                EXPORT  ACMP6_IRQHandler                    [WEAK]
                EXPORT  ACMP7_IRQHandler                    [WEAK]
                EXPORT  ACMP8_IRQHandler                    [WEAK]
                EXPORT  ACMP9_IRQHandler                    [WEAK]
                EXPORT  ACMP10_IRQHandler                   [WEAK]
                EXPORT  DAC0_IRQHandler                     [WEAK]
                EXPORT  DAC1_IRQHandler                     [WEAK]
                EXPORT  ADC0_EVTINT_IRQHandler              [WEAK]
                EXPORT  ADC0_INT0_IRQHandler                [WEAK]
                EXPORT  ADC0_INT1_IRQHandler                [WEAK]
                EXPORT  ADC0_INT2_IRQHandler                [WEAK]
                EXPORT  ADC0_INT3_IRQHandler                [WEAK]
                EXPORT  ADC1_EVTINT_IRQHandler              [WEAK]
                EXPORT  ADC1_INT0_IRQHandler                [WEAK]
                EXPORT  ADC1_INT1_IRQHandler                [WEAK]
                EXPORT  ADC1_INT2_IRQHandler                [WEAK]
                EXPORT  ADC1_INT3_IRQHandler                [WEAK]
                EXPORT  ADC2_EVTINT_IRQHandler              [WEAK]
                EXPORT  ADC2_INT0_IRQHandler                [WEAK]
                EXPORT  ADC2_INT1_IRQHandler                [WEAK]
                EXPORT  ADC2_INT2_IRQHandler                [WEAK]
                EXPORT  ADC2_INT3_IRQHandler                [WEAK]
                EXPORT  QEP0_IRQHandler                     [WEAK]
                EXPORT  QEP1_IRQHandler                     [WEAK]
                EXPORT  QEP2_IRQHandler                     [WEAK]
                EXPORT  QEP3_IRQHandler                     [WEAK]
                EXPORT  QEP4_IRQHandler                     [WEAK]
                EXPORT  QEP5_IRQHandler                     [WEAK]
                EXPORT  SDFM0_ERR_IRQHandler                [WEAK]
                EXPORT  SDFM0_DR0_IRQHandler                [WEAK]
                EXPORT  SDFM0_DR1_IRQHandler                [WEAK]
                EXPORT  SDFM0_DR2_IRQHandler                [WEAK]
                EXPORT  SDFM0_DR3_IRQHandler                [WEAK]
                EXPORT  SDFM1_ERR_IRQHandler                [WEAK]
                EXPORT  SDFM1_DR0_IRQHandler                [WEAK]
                EXPORT  SDFM1_DR1_IRQHandler                [WEAK]
                EXPORT  SDFM1_DR2_IRQHandler                [WEAK]
                EXPORT  SDFM1_DR3_IRQHandler                [WEAK]
                EXPORT  SDFM2_ERR_IRQHandler                [WEAK]
                EXPORT  SDFM2_DR0_IRQHandler                [WEAK]
                EXPORT  SDFM2_DR1_IRQHandler                [WEAK]
                EXPORT  SDFM2_DR2_IRQHandler                [WEAK]
                EXPORT  SDFM2_DR3_IRQHandler                [WEAK]
                EXPORT  SDFM3_ERR_IRQHandler                [WEAK]
                EXPORT  SDFM3_DR0_IRQHandler                [WEAK]
                EXPORT  SDFM3_DR1_IRQHandler                [WEAK]
                EXPORT  SDFM3_DR2_IRQHandler                [WEAK]
                EXPORT  SDFM3_DR3_IRQHandler                [WEAK]
                EXPORT  STIMER0_IRQHandler                  [WEAK]
                EXPORT  STIMER1_IRQHandler                  [WEAK]
                EXPORT  STIMER2_IRQHandler                  [WEAK]
                EXPORT  STIMER3_IRQHandler                  [WEAK]
                EXPORT  STIMER4_IRQHandler                  [WEAK]
                EXPORT  STIMER5_IRQHandler                  [WEAK]
                EXPORT  ETIMER0_IRQHandler                  [WEAK]
                EXPORT  ETIMER1_IRQHandler                  [WEAK]
                EXPORT  ETIMER2_IRQHandler                  [WEAK]
                EXPORT  ETIMER3_IRQHandler                  [WEAK]
                EXPORT  ETIMER4_IRQHandler                  [WEAK]
                EXPORT  ETIMER5_IRQHandler                  [WEAK]
                EXPORT  ETIMER6_IRQHandler                  [WEAK]
                EXPORT  ETIMER7_IRQHandler                  [WEAK]
                EXPORT  ETIMER8_IRQHandler                  [WEAK]
                EXPORT  ETIMER9_IRQHandler                  [WEAK]
                EXPORT  ETIMER10_IRQHandler                 [WEAK]
                EXPORT  ETIMER11_IRQHandler                 [WEAK]
                EXPORT  SRPWM0_IRQHandler                   [WEAK]
                EXPORT  SRPWM1_IRQHandler                   [WEAK]
                EXPORT  SRPWM2_IRQHandler                   [WEAK]
                EXPORT  SRPWM3_IRQHandler                   [WEAK]
                EXPORT  SRPWM4_IRQHandler                   [WEAK]
                EXPORT  SRPWM5_IRQHandler                   [WEAK]
                EXPORT  SRPWM6_IRQHandler                   [WEAK]
                EXPORT  SRPWM7_IRQHandler                   [WEAK]
                EXPORT  SRPWM8_IRQHandler                   [WEAK]
                EXPORT  SRPWM9_IRQHandler                   [WEAK]
                EXPORT  SRPWM10_IRQHandler                  [WEAK]
                EXPORT  SRPWM11_IRQHandler                  [WEAK]
                EXPORT  SRPWM12_IRQHandler                  [WEAK]
                EXPORT  SRPWM13_IRQHandler                  [WEAK]
                EXPORT  SRPWM14_IRQHandler                  [WEAK]
                EXPORT  SRPWM15_IRQHandler                  [WEAK]
                EXPORT  SRPWM16_IRQHandler                  [WEAK]
                EXPORT  SRPWM17_IRQHandler                  [WEAK]
                EXPORT  SYSC_IRQHandler                     [WEAK]
                EXPORT  CORE2CORE_IRQHandler                [WEAK]
                EXPORT  XBAR_INT0_IRQHandler                [WEAK]
                EXPORT  XBAR_INT1_IRQHandler                [WEAK]
                EXPORT  XBAR_INT2_IRQHandler                [WEAK]
                EXPORT  XBAR_INT3_IRQHandler                [WEAK]
                EXPORT  XBAR_INT4_IRQHandler                [WEAK]
                EXPORT  XBAR_INT5_IRQHandler                [WEAK]
                EXPORT  CLB_INT0_IRQHandler                 [WEAK]
                EXPORT  CLB_INT1_IRQHandler                 [WEAK]
                EXPORT  CLB_INT2_IRQHandler                 [WEAK]
                EXPORT  CLB_INT3_IRQHandler                 [WEAK]
                EXPORT  CLB_INT4_IRQHandler                 [WEAK]
                EXPORT  CLB_INT5_IRQHandler                 [WEAK]

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

            B       .

            ENDP

            ALIGN

;*******************************************************************************
; User Stack and Heap initialization
;*******************************************************************************
            IF      :DEF:__MICROLIB

            EXPORT  __initial_sp
            EXPORT  __heap_base
            EXPORT  __heap_limit

            ELSE

            IMPORT  __use_two_region_memory
            EXPORT  __user_initial_stackheap

__user_initial_stackheap

            LDR     R0, =  Heap_Mem
            LDR     R1, =(Stack_Mem + Stack_Size)
            LDR     R2, = (Heap_Mem +  Heap_Size)
            LDR     R3, = Stack_Mem
            BX      LR

            ALIGN

            ENDIF
;*******************************************************************************
; Software Delay function
;*******************************************************************************

     END
;************************ (C) COPYRIGHT ETMCU *****END OF FILE*****
