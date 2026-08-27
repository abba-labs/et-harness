/*
 * Copyright (c) 2025, Chengdu ET Microelectronics Co., Ltd.
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

#ifndef __ET6X_PINMAP_H__
#define __ET6X_PINMAP_H__



#define GPIO10_MODE_GPIO10                     (0)                              //GPIO10
#define GPIO10_MODE_SRPWM5_A                   (1)                              //GPIO10
#define GPIO10_MODE_EMIF0_CAS_n                (2)                              //GPIO10
#define GPIO10_MODE_ADCSOCBO                   (3)                              //GPIO10
#define GPIO10_MODE_QEP0_A                     (5)                              //GPIO10
#define GPIO10_MODE_UART3_TX                   (6)                              //GPIO10
#define GPIO10_MODE_SDFM3_CLK1                 (7)                              //GPIO10
#define GPIO10_MODE_CANFD1_RX                  (9)                              //GPIO10
#define GPIO10_MODE_CLB_OUTXBAR4               (10)                             //GPIO10
#define GPIO10_MODE_TRACED9                    (11)                             //GPIO10
#define GPIO10_MODE_QSPI_IO0                   (13)                             //GPIO10
#define GPIO10_MODE_ECAP3                      (14)                             //GPIO10
#define GPIO10_MODE_TESTPIN0                   (15)                             //GPIO10

#define GPIO11_MODE_GPIO11                     (0)                              //GPIO11
#define GPIO11_MODE_SRPWM5_B                   (1)                              //GPIO11
#define GPIO11_MODE_UART3_RX                   (2)                              //GPIO11
#define GPIO11_MODE_OUTXBAR6                   (3)                              //GPIO11
#define GPIO11_MODE_QEP0_B                     (5)                              //GPIO11
#define GPIO11_MODE_UART3_RX_BK                (6)                              //GPIO11
#define GPIO11_MODE_SDFM3_DATA1                (7)                              //GPIO11
#define GPIO11_MODE_TESTPIN1                   (11)                             //GPIO11
#define GPIO11_MODE_QSPI_IO1                   (13)                             //GPIO11
#define GPIO11_MODE_ECAP4                      (14)                             //GPIO11
#define GPIO11_MODE_PMBUS0_ALERT_n             (15)                             //GPIO11

#define GPIO12_MODE_GPIO12                     (0)                              //GPIO12
#define GPIO12_MODE_SRPWM6_A                   (1)                              //GPIO12
#define GPIO12_MODE_CLB_OUTXBAR5               (2)                              //GPIO12
#define GPIO12_MODE_ADCSOCAO                   (3)                              //GPIO12
#define GPIO12_MODE_QEP0_STROBE                (5)                              //GPIO12
#define GPIO12_MODE_UART2_TX                   (6)                              //GPIO12
#define GPIO12_MODE_SDFM3_CLK2                 (7)                              //GPIO12
#define GPIO12_MODE_EMIF0_A1                   (9)                              //GPIO12
#define GPIO12_MODE_UART0_TX                   (10)                             //GPIO12
#define GPIO12_MODE_CANFD1_TX                  (11)                             //GPIO12
#define GPIO12_MODE_QSPI_IO2                   (13)                             //GPIO12
#define GPIO12_MODE_ECAP5                      (14)                             //GPIO12
#define GPIO12_MODE_PMBUS0_CTL_n               (15)                             //GPIO12

#define GPIO13_MODE_GPIO13                     (0)                              //GPIO13
#define GPIO13_MODE_SRPWM6_B                   (1)                              //GPIO13
#define GPIO13_MODE_CLB_OUTXBAR6               (2)                              //GPIO13
#define GPIO13_MODE_QEP4_STROBE                (3)                              //GPIO13
#define GPIO13_MODE_QEP0_INDEX                 (5)                              //GPIO13
#define GPIO13_MODE_UART2_RX                   (6)                              //GPIO13
#define GPIO13_MODE_SDFM3_DATA2                (7)                              //GPIO13
#define GPIO13_MODE_EMIF0_CS0_n                (9)                              //GPIO13
#define GPIO13_MODE_UART0_RX                   (10)                             //GPIO13
#define GPIO13_MODE_CANFD1_RX                  (11)                             //GPIO13
#define GPIO13_MODE_QSPI_IO3                   (13)                             //GPIO13
#define GPIO13_MODE_ECAP6                      (14)                             //GPIO13
#define GPIO13_MODE_PMBUS0_SDA                 (15)                             //GPIO13

#define GPIO14_MODE_GPIO14                     (0)                              //GPIO14
#define GPIO14_MODE_SRPWM7_A                   (1)                              //GPIO14
#define GPIO14_MODE_UART3_TX                   (2)                              //GPIO14
#define GPIO14_MODE_QEP4_INDEX                 (3)                              //GPIO14
#define GPIO14_MODE_LIN0_TX                    (5)                              //GPIO14
#define GPIO14_MODE_OUTXBAR2                   (6)                              //GPIO14
#define GPIO14_MODE_OUTXBAR7                   (7)                              //GPIO14
#define GPIO14_MODE_UART4_TX                   (9)                              //GPIO14
#define GPIO14_MODE_UART7_TX                   (10)                             //GPIO14
#define GPIO14_MODE_TESTPIN2                   (11)                             //GPIO14
#define GPIO14_MODE_QSPI_CLK                   (13)                             //GPIO14
#define GPIO14_MODE_EMIF0_D17                  (14)                             //GPIO14
#define GPIO14_MODE_PMBUS0_SCL                 (15)                             //GPIO14

#define GPIO15_MODE_GPIO15                     (0)                              //GPIO15
#define GPIO15_MODE_SRPWM7_B                   (1)                              //GPIO15
#define GPIO15_MODE_UART3_RX                   (2)                              //GPIO15
#define GPIO15_MODE_LIN0_RX                    (5)                              //GPIO15
#define GPIO15_MODE_OUTXBAR3                   (6)                              //GPIO15
#define GPIO15_MODE_CLB_OUTXBAR7               (7)                              //GPIO15
#define GPIO15_MODE_UART4_RX                   (9)                              //GPIO15
#define GPIO15_MODE_UART7_RX                   (10)                             //GPIO15
#define GPIO15_MODE_QEP4_A                     (11)                             //GPIO15
#define GPIO15_MODE_TESTPIN3                   (13)                             //GPIO15
#define GPIO15_MODE_ECAP7                      (14)                             //GPIO15
#define GPIO15_MODE_EMIF0_DQM2                 (15)                             //GPIO15

#define GPIO16_MODE_GPIO16                     (0)                              //GPIO16
#define GPIO16_MODE_SPI0_MOSI                  (1)                              //GPIO16
#define GPIO16_MODE_OUTXBAR6                   (3)                              //GPIO16
#define GPIO16_MODE_SRPWM8_A                   (5)                              //GPIO16
#define GPIO16_MODE_SDFM0_DATA1                (7)                              //GPIO16
#define GPIO16_MODE_CANFD1_TX                  (10)                             //GPIO16
#define GPIO16_MODE_QEP4_B                     (11)                             //GPIO16

#define GPIO17_MODE_GPIO17                     (0)                              //GPIO17
#define GPIO17_MODE_SPI0_MISO                  (1)                              //GPIO17
#define GPIO17_MODE_OUTXBAR7                   (3)                              //GPIO17
#define GPIO17_MODE_SRPWM8_B                   (5)                              //GPIO17
#define GPIO17_MODE_SDFM0_CLK1                 (7)                              //GPIO17
#define GPIO17_MODE_CANFD1_RX                  (10)                             //GPIO17
#define GPIO17_MODE_QEP4_STROBE                (11)                             //GPIO17

#define GPIO18_MODE_GPIO18                     (0)                              //GPIO18
#define GPIO18_MODE_SPI0_CLK                   (1)                              //GPIO18
#define GPIO18_MODE_UART3_TX                   (2)                              //GPIO18
#define GPIO18_MODE_CANFD0_RX                  (3)                              //GPIO18
#define GPIO18_MODE_SRPWM9_A                   (5)                              //GPIO18
#define GPIO18_MODE_SDFM0_DATA2                (7)                              //GPIO18
#define GPIO18_MODE_CANFD1_RX                  (9)                              //GPIO18
#define GPIO18_MODE_EMIF0_CS2_n                (10)                             //GPIO18
#define GPIO18_MODE_QEP4_INDEX                 (11)                             //GPIO18

#define GPIO22_MODE_GPIO22                     (0)                              //GPIO22
#define GPIO22_MODE_QEP0_STROBE                (1)                              //GPIO22
#define GPIO22_MODE_UART3_TX                   (3)                              //GPIO22
#define GPIO22_MODE_SRPWM11_A                  (5)                              //GPIO22
#define GPIO22_MODE_SPI1_CLK                   (6)                              //GPIO22
#define GPIO22_MODE_SDFM0_DATA4                (7)                              //GPIO22
#define GPIO22_MODE_CANFD1_TX                  (9)                              //GPIO22
#define GPIO22_MODE_EMIF0_RAS_n                (10)                             //GPIO22
#define GPIO22_MODE_SPI2_CLK                   (14)                             //GPIO22

#define GPIO19_MODE_GPIO19                     (0)                              //GPIO19
#define GPIO19_MODE_SPI0_CS_n                  (1)                              //GPIO19
#define GPIO19_MODE_UART3_RX                   (2)                              //GPIO19
#define GPIO19_MODE_CANFD0_TX                  (3)                              //GPIO19
#define GPIO19_MODE_SRPWM9_B                   (5)                              //GPIO19
#define GPIO19_MODE_SDFM0_CLK2                 (7)                              //GPIO19
#define GPIO19_MODE_CANFD1_TX                  (9)                              //GPIO19
#define GPIO19_MODE_EMIF0_CS3_n                (10)                             //GPIO19

#define GPIO20_MODE_GPIO20                     (0)                              //GPIO20
#define GPIO20_MODE_QEP0_A                     (1)                              //GPIO20
#define GPIO20_MODE_SRPWM10_A                  (5)                              //GPIO20
#define GPIO20_MODE_SDFM0_DATA3                (7)                              //GPIO20
#define GPIO20_MODE_CANFD2_TX                  (9)                              //GPIO20
#define GPIO20_MODE_EMIF0_BA0                  (10)                             //GPIO20
#define GPIO20_MODE_CANFD1_TX                  (11)                             //GPIO20
#define GPIO20_MODE_SPI2_MOSI                  (14)                             //GPIO20

#define GPIO21_MODE_GPIO21                     (0)                              //GPIO21
#define GPIO21_MODE_QEP0_B                     (1)                              //GPIO21
#define GPIO21_MODE_SRPWM10_B                  (5)                              //GPIO21
#define GPIO21_MODE_SDFM0_CLK3                 (7)                              //GPIO21
#define GPIO21_MODE_CANFD2_RX                  (9)                              //GPIO21
#define GPIO21_MODE_EMIF0_BA1                  (10)                             //GPIO21
#define GPIO21_MODE_CANFD1_RX                  (11)                             //GPIO21
#define GPIO21_MODE_SPI2_MISO                  (14)                             //GPIO21

#define GPIO95_MODE_GPIO95                     (0)                              //GPIO95
#define GPIO95_MODE_EMIF0_DQM3                 (2)                              //GPIO95
#define GPIO95_MODE_SRPWM7_A                   (3)                              //GPIO95
#define GPIO95_MODE_QEP0_INDEX                 (5)                              //GPIO95
#define GPIO95_MODE_SDFM3_DATA4                (7)                              //GPIO95
#define GPIO95_MODE_EMIF0_D17                  (14)                             //GPIO95

#define GPIO8_MODE_GPIO8                       (0)                              //GPIO8
#define GPIO8_MODE_SRPWM4_A                    (1)                              //GPIO8
#define GPIO8_MODE_EMIF0_RAS_n                 (2)                              //GPIO8
#define GPIO8_MODE_ADCSOCAO                    (3)                              //GPIO8
#define GPIO8_MODE_QEP2_STROBE                 (5)                              //GPIO8
#define GPIO8_MODE_UART2_TX                    (6)                              //GPIO8
#define GPIO8_MODE_CLB_OUTXBAR3                (7)                              //GPIO8
#define GPIO8_MODE_CANFD1_TX                   (9)                              //GPIO8

#define GPIO9_MODE_GPIO9                       (0)                              //GPIO9
#define GPIO9_MODE_SRPWM4_B                    (1)                              //GPIO9
#define GPIO9_MODE_UART3_TX                    (2)                              //GPIO9
#define GPIO9_MODE_OUTXBAR5                    (3)                              //GPIO9
#define GPIO9_MODE_QEP2_INDEX                  (5)                              //GPIO9
#define GPIO9_MODE_UART2_RX                    (6)                              //GPIO9

#define GPIO100_MODE_GPIO100                   (0)                              //GPIO100
#define GPIO100_MODE_SRPWM15_A                 (1)                              //GPIO100
#define GPIO100_MODE_EMIF0_A10                 (2)                              //GPIO100
#define GPIO100_MODE_QEP2_STROBE               (5)                              //GPIO100
#define GPIO100_MODE_SDFM2_DATA2               (6)                              //GPIO100

#define GPIO23_MODE_GPIO23                     (0)                              //GPIO23
#define GPIO23_MODE_QEP0_INDEX                 (1)                              //GPIO23
#define GPIO23_MODE_UART3_RX                   (3)                              //GPIO23
#define GPIO23_MODE_SRPWM11_B                  (5)                              //GPIO23
#define GPIO23_MODE_SPI1_CS_n                  (6)                              //GPIO23
#define GPIO23_MODE_SDFM0_CLK4                 (7)                              //GPIO23
#define GPIO23_MODE_CANFD1_RX                  (9)                              //GPIO23
#define GPIO23_MODE_EMIF0_CAS_n                (10)                             //GPIO23
#define GPIO23_MODE_SPI2_CS_n                  (14)                             //GPIO23

#define C4_GPIO109_MODE_GPIO109                (0)                              //C4_GPIO109
#define C4_GPIO109_MODE_QEP0_INDEX             (1)                              //C4_GPIO109
#define C4_GPIO109_MODE_SRPWM9_A               (2)                              //C4_GPIO109
#define C4_GPIO109_MODE_SPI0_CS_n              (3)                              //C4_GPIO109
#define C4_GPIO109_MODE_UART7_TX               (5)                              //C4_GPIO109
#define C4_GPIO109_MODE_OUTXBAR0               (11)                             //C4_GPIO109
#define C4_GPIO109_MODE_SDFM0_CLK3             (15)                             //C4_GPIO109

#define C3_GPIO110_MODE_GPIO110                (0)                              //C3_GPIO110
#define C3_GPIO110_MODE_EMIF0_A11              (1)                              //C3_GPIO110
#define C3_GPIO110_MODE_SRPWM9_B               (2)                              //C3_GPIO110
#define C3_GPIO110_MODE_EMIF0_WE_n             (3)                              //C3_GPIO110
#define C3_GPIO110_MODE_UART7_RX               (5)                              //C3_GPIO110
#define C3_GPIO110_MODE_OUTXBAR1               (11)                             //C3_GPIO110

#define GPIO33_MODE_GPIO33                     (0)                              //GPIO33
#define GPIO33_MODE_I2C0_SCL                   (1)                              //GPIO33
#define GPIO33_MODE_EMIF0_RNW                  (2)                              //GPIO33
#define GPIO33_MODE_SPI0_MISO                  (3)                              //GPIO33
#define GPIO33_MODE_QEP3_B                     (5)                              //GPIO33
#define GPIO33_MODE_CLB_OUTXBAR1               (7)                              //GPIO33
#define GPIO33_MODE_EMIF0_BA0                  (9)                              //GPIO33
#define GPIO33_MODE_ECAP1                      (14)                             //GPIO33
#define GPIO33_MODE_SPI3_CS_n                  (15)                             //GPIO33

#define GPIO34_MODE_GPIO34                     (0)                              //GPIO34
#define GPIO34_MODE_OUTXBAR0                   (1)                              //GPIO34
#define GPIO34_MODE_EMIF0_CS2_n                (2)                              //GPIO34
#define GPIO34_MODE_SPI0_CLK                   (3)                              //GPIO34
#define GPIO34_MODE_QEP3_STROBE                (5)                              //GPIO34
#define GPIO34_MODE_I2C1_SDA                   (6)                              //GPIO34
#define GPIO34_MODE_CLB_OUTXBAR2               (7)                              //GPIO34
#define GPIO34_MODE_EMIF0_BA1                  (9)                              //GPIO34
#define GPIO34_MODE_UART7_TX                   (10)                             //GPIO34
#define GPIO34_MODE_SRPWM17_A                  (11)                             //GPIO34
#define GPIO34_MODE_UART2_TX                   (13)                             //GPIO34

#define GPIO35_MODE_GPIO35                     (0)                              //GPIO35
#define GPIO35_MODE_UART2_RX                   (1)                              //GPIO35
#define GPIO35_MODE_EMIF0_CS3_n                (2)                              //GPIO35
#define GPIO35_MODE_SPI0_CS_n                  (3)                              //GPIO35
#define GPIO35_MODE_QEP3_INDEX                 (5)                              //GPIO35
#define GPIO35_MODE_I2C1_SCL                   (6)                              //GPIO35
#define GPIO35_MODE_CLB_OUTXBAR3               (7)                              //GPIO35
#define GPIO35_MODE_EMIF0_A0                   (9)                              //GPIO35
#define GPIO35_MODE_UART7_RX                   (10)                             //GPIO35
#define GPIO35_MODE_SRPWM17_B                  (11)                             //GPIO35
#define GPIO35_MODE_UART2_RX_BK                (13)                             //GPIO35

#define GPIO29_MODE_GPIO29                     (0)                              //GPIO29
#define GPIO29_MODE_UART2_TX                   (1)                              //GPIO29
#define GPIO29_MODE_EMIF0_SDCKE                (2)                              //GPIO29
#define GPIO29_MODE_UART0_TX                   (3)                              //GPIO29
#define GPIO29_MODE_OUTXBAR5                   (5)                              //GPIO29
#define GPIO29_MODE_QEP2_B                     (6)                              //GPIO29
#define GPIO29_MODE_SDFM1_CLK3                 (7)                              //GPIO29
#define GPIO29_MODE_EMIF0_CS3_n                (9)                              //GPIO29
#define GPIO29_MODE_SRPWM14_B                  (13)                             //GPIO29

#define GPIO28_MODE_GPIO28                     (0)                              //GPIO28
#define GPIO28_MODE_UART2_RX                   (1)                              //GPIO28
#define GPIO28_MODE_EMIF0_CS4_n                (2)                              //GPIO28
#define GPIO28_MODE_UART0_RX                   (3)                              //GPIO28
#define GPIO28_MODE_OUTXBAR4                   (5)                              //GPIO28
#define GPIO28_MODE_QEP2_A                     (6)                              //GPIO28
#define GPIO28_MODE_SDFM1_DATA3                (7)                              //GPIO28
#define GPIO28_MODE_EMIF0_CS2_n                (9)                              //GPIO28
#define GPIO28_MODE_SRPWM14_A                  (13)                             //GPIO28

#define TDI_MODE_TDI                           (0)                              //TDI
#define TDI_MODE_GPIO118                       (1)                              //TDI
#define TDI_MODE_SRPWM6_A                      (2)                              //TDI
#define TDI_MODE_SPI0_MOSI                     (3)                              //TDI
#define TDI_MODE_OUTXBAR3                      (5)                              //TDI
#define TDI_MODE_UART2_RX                      (6)                              //TDI
#define TDI_MODE_UART1_TX                      (7)                              //TDI
#define TDI_MODE_I2C0_SDA                      (9)                              //TDI
#define TDI_MODE_SPI2_CLK                      (10)                             //TDI
#define TDI_MODE_PMBUS0_SDA                    (15)                             //TDI

#define TDO_SWO_MODE_TDO_SWO                   (0)                              //TDO_SWO
#define TDO_SWO_MODE_GPIO119                   (1)                              //TDO_SWO
#define TDO_SWO_MODE_SRPWM6_B                  (2)                              //TDO_SWO
#define TDO_SWO_MODE_EMIF0_A11                 (3)                              //TDO_SWO
#define TDO_SWO_MODE_OUTXBAR4                  (5)                              //TDO_SWO
#define TDO_SWO_MODE_UART2_TX                  (6)                              //TDO_SWO
#define TDO_SWO_MODE_UART1_RX                  (7)                              //TDO_SWO
#define TDO_SWO_MODE_I2C0_SCL                  (9)                              //TDO_SWO
#define TDO_SWO_MODE_SPI2_CS_n                 (10)                             //TDO_SWO
#define TDO_SWO_MODE_PMBUS0_SCL                (15)                             //TDO_SWO

#define GPIO30_MODE_GPIO30                     (0)                              //GPIO30
#define GPIO30_MODE_CANFD0_RX                  (1)                              //GPIO30
#define GPIO30_MODE_EMIF0_CLK                  (2)                              //GPIO30
#define GPIO30_MODE_CANFD1_RX                  (3)                              //GPIO30
#define GPIO30_MODE_OUTXBAR6                   (5)                              //GPIO30
#define GPIO30_MODE_QEP2_STROBE                (6)                              //GPIO30
#define GPIO30_MODE_SDFM1_DATA4                (7)                              //GPIO30
#define GPIO30_MODE_EMIF0_CS4_n                (9)                              //GPIO30
#define GPIO30_MODE_SRPWM15_A                  (13)                             //GPIO30
#define GPIO30_MODE_SPI3_MOSI                  (15)                             //GPIO30

#define SWDIO_TMS_MODE_SWDIO_TMS               (0)                              //SWDIO_TMS
#define SWDIO_TMS_MODE_GPIO122                 (1)                              //SWDIO_TMS

#define SWCLK_TCK_MODE_SWCLK_TCK               (0)                              //SWCLK_TCK
#define SWCLK_TCK_MODE_GPIO121                 (1)                              //SWCLK_TCK

#define GPIO26_MODE_GPIO26                     (0)                              //GPIO26
#define GPIO26_MODE_OUTXBAR2                   (1)                              //GPIO26
#define GPIO26_MODE_QEP1_INDEX                 (2)                              //GPIO26
#define GPIO26_MODE_OUTXBAR2_BK                (5)                              //GPIO26
#define GPIO26_MODE_SPI1_CLK                   (6)                              //GPIO26
#define GPIO26_MODE_SDFM1_DATA2                (7)                              //GPIO26
#define GPIO26_MODE_PMBUS0_ALERT_n             (9)                              //GPIO26
#define GPIO26_MODE_EMIF0_DQM2                 (10)                             //GPIO26
#define GPIO26_MODE_SRPWM13_A                  (13)                             //GPIO26

#define GPIO36_MODE_GPIO36                     (0)                              //GPIO36
#define GPIO36_MODE_UART2_TX                   (1)                              //GPIO36
#define GPIO36_MODE_EMIF0_WAIT                 (2)                              //GPIO36
#define GPIO36_MODE_CANFD0_RX                  (6)                              //GPIO36
#define GPIO36_MODE_CLB_OUTXBAR4               (7)                              //GPIO36
#define GPIO36_MODE_EMIF0_A1                   (9)                              //GPIO36
#define GPIO36_MODE_CANFD1_RX                  (10)                             //GPIO36
#define GPIO36_MODE_SDFM0_DATA1                (13)                             //GPIO36
#define GPIO36_MODE_EMIF0_WE_n                 (14)                             //GPIO36

#define GPIO37_MODE_GPIO37                     (0)                              //GPIO37
#define GPIO37_MODE_OUTXBAR1                   (1)                              //GPIO37
#define GPIO37_MODE_EMIF0_OE_n                 (2)                              //GPIO37
#define GPIO37_MODE_SRPWM17_A                  (3)                              //GPIO37
#define GPIO37_MODE_CANFD0_TX                  (6)                              //GPIO37
#define GPIO37_MODE_CLB_OUTXBAR5               (7)                              //GPIO37
#define GPIO37_MODE_EMIF0_A2                   (9)                              //GPIO37
#define GPIO37_MODE_CANFD1_TX                  (10)                             //GPIO37
#define GPIO37_MODE_SDFM0_DATA2                (13)                             //GPIO37
#define GPIO37_MODE_EMIF0_D24                  (14)                             //GPIO37

#define GPIO38_MODE_GPIO38                     (0)                              //GPIO38
#define GPIO38_MODE_EMIF0_A0                   (2)                              //GPIO38
#define GPIO38_MODE_SRPWM17_B                  (3)                              //GPIO38
#define GPIO38_MODE_UART0_TX                   (5)                              //GPIO38
#define GPIO38_MODE_UART3_TX                   (6)                              //GPIO38
#define GPIO38_MODE_CLB_OUTXBAR6               (7)                              //GPIO38
#define GPIO38_MODE_EMIF0_A3                   (9)                              //GPIO38
#define GPIO38_MODE_CANFD1_TX                  (10)                             //GPIO38
#define GPIO38_MODE_SDFM0_DATA3                (13)                             //GPIO38
#define GPIO38_MODE_EMIF0_CS2_n                (14)                             //GPIO38

#define GPIO39_MODE_GPIO39                     (0)                              //GPIO39
#define GPIO39_MODE_EMIF0_A1                   (2)                              //GPIO39
#define GPIO39_MODE_UART0_RX                   (5)                              //GPIO39
#define GPIO39_MODE_UART3_RX                   (6)                              //GPIO39
#define GPIO39_MODE_CLB_OUTXBAR7               (7)                              //GPIO39
#define GPIO39_MODE_EMIF0_A4                   (9)                              //GPIO39
#define GPIO39_MODE_CANFD1_RX                  (10)                             //GPIO39
#define GPIO39_MODE_SDFM0_DATA4                (13)                             //GPIO39

#define GPIO40_MODE_GPIO40                     (0)                              //GPIO40
#define GPIO40_MODE_EMIF0_A2                   (2)                              //GPIO40
#define GPIO40_MODE_SRPWM12_A                  (3)                              //GPIO40
#define GPIO40_MODE_CANFD2_RX                  (5)                              //GPIO40
#define GPIO40_MODE_I2C1_SDA                   (6)                              //GPIO40
#define GPIO40_MODE_SDFM3_CLK3                 (7)                              //GPIO40
#define GPIO40_MODE_CLB_OUTXBAR0               (10)                             //GPIO40
#define GPIO40_MODE_SDFM1_CLK1                 (13)                             //GPIO40

#define GPIO41_MODE_GPIO41                     (0)                              //GPIO41
#define GPIO41_MODE_EMIF0_A3                   (2)                              //GPIO41
#define GPIO41_MODE_SRPWM12_B                  (3)                              //GPIO41
#define GPIO41_MODE_CANFD2_TX                  (5)                              //GPIO41
#define GPIO41_MODE_I2C1_SCL                   (6)                              //GPIO41
#define GPIO41_MODE_SDFM3_DATA3                (7)                              //GPIO41
#define GPIO41_MODE_CLB_OUTXBAR1               (10)                             //GPIO41
#define GPIO41_MODE_SDFM1_DATA1                (13)                             //GPIO41

#define GPIO48_MODE_GPIO48                     (0)                              //GPIO48
#define GPIO48_MODE_OUTXBAR2                   (1)                              //GPIO48
#define GPIO48_MODE_EMIF0_A8                   (2)                              //GPIO48
#define GPIO48_MODE_UART2_TX                   (6)                              //GPIO48
#define GPIO48_MODE_SDFM0_DATA1                (7)                              //GPIO48
#define GPIO48_MODE_SDFM1_CLK2                 (13)                             //GPIO48

#define GPIO120_MODE_GPIO120                   (0)                              //GPIO120
#define GPIO120_MODE_ERRORSTS                  (1)                              //GPIO120
#define GPIO120_MODE_EMIF0_SDCKE               (2)                              //GPIO120
#define GPIO120_MODE_XCLKOUT                   (3)                              //GPIO120
#define GPIO120_MODE_OUTXBAR0                  (5)                              //GPIO120
#define GPIO120_MODE_SDFM1_CLK1                (13)                             //GPIO120

#define GPIO49_MODE_GPIO49                     (0)                              //GPIO49
#define GPIO49_MODE_OUTXBAR3                   (1)                              //GPIO49
#define GPIO49_MODE_EMIF0_A9                   (2)                              //GPIO49
#define GPIO49_MODE_UART2_RX                   (6)                              //GPIO49
#define GPIO49_MODE_SDFM0_CLK1                 (7)                              //GPIO49
#define GPIO49_MODE_EMIF0_A5                   (9)                              //GPIO49
#define GPIO49_MODE_SDFM1_DATA1                (13)                             //GPIO49

#define GPIO50_MODE_GPIO50                     (0)                              //GPIO50
#define GPIO50_MODE_QEP0_A                     (1)                              //GPIO50
#define GPIO50_MODE_EMIF0_A10                  (2)                              //GPIO50
#define GPIO50_MODE_SRPWM14_A                  (3)                              //GPIO50
#define GPIO50_MODE_SPI2_MOSI                  (6)                              //GPIO50
#define GPIO50_MODE_SDFM0_DATA2                (7)                              //GPIO50
#define GPIO50_MODE_EMIF0_A6                   (9)                              //GPIO50
#define GPIO50_MODE_UART6_TX                   (10)                             //GPIO50
#define GPIO50_MODE_QSPI_IO0                   (11)                             //GPIO50
#define GPIO50_MODE_SDFM1_DATA2                (13)                             //GPIO50
#define GPIO50_MODE_ECAP2                      (14)                             //GPIO50

#define GPIO51_MODE_GPIO51                     (0)                              //GPIO51
#define GPIO51_MODE_QEP0_B                     (1)                              //GPIO51
#define GPIO51_MODE_EMIF0_A11                  (2)                              //GPIO51
#define GPIO51_MODE_SRPWM14_B                  (3)                              //GPIO51
#define GPIO51_MODE_SPI2_MISO                  (6)                              //GPIO51
#define GPIO51_MODE_SDFM0_CLK2                 (7)                              //GPIO51
#define GPIO51_MODE_EMIF0_A7                   (9)                              //GPIO51
#define GPIO51_MODE_UART6_RX                   (10)                             //GPIO51
#define GPIO51_MODE_QSPI_IO1                   (11)                             //GPIO51
#define GPIO51_MODE_SDFM1_DATA3                (13)                             //GPIO51
#define GPIO51_MODE_ECAP3                      (14)                             //GPIO51

#define GPIO52_MODE_GPIO52                     (0)                              //GPIO52
#define GPIO52_MODE_QEP0_STROBE                (1)                              //GPIO52
#define GPIO52_MODE_EMIF0_A12                  (2)                              //GPIO52
#define GPIO52_MODE_SRPWM15_A                  (3)                              //GPIO52
#define GPIO52_MODE_SPI2_CLK                   (6)                              //GPIO52
#define GPIO52_MODE_SDFM0_DATA3                (7)                              //GPIO52
#define GPIO52_MODE_EMIF0_A8                   (9)                              //GPIO52
#define GPIO52_MODE_QSPI_IO2                   (11)                             //GPIO52
#define GPIO52_MODE_SDFM1_DATA4                (13)                             //GPIO52
#define GPIO52_MODE_ECAP4                      (14)                             //GPIO52

#define GPIO53_MODE_GPIO53                     (0)                              //GPIO53
#define GPIO53_MODE_QEP0_INDEX                 (1)                              //GPIO53
#define GPIO53_MODE_EMIF0_D31                  (2)                              //GPIO53
#define GPIO53_MODE_SPI2_CS_n                  (6)                              //GPIO53
#define GPIO53_MODE_SDFM0_CLK3                 (7)                              //GPIO53
#define GPIO53_MODE_EMIF0_A9                   (9)                              //GPIO53
#define GPIO53_MODE_QSPI_IO3                   (11)                             //GPIO53
#define GPIO53_MODE_SDFM0_CLK1                 (13)                             //GPIO53
#define GPIO53_MODE_ECAP5                      (14)                             //GPIO53

#define GPIO54_MODE_GPIO54                     (0)                              //GPIO54
#define GPIO54_MODE_SPI0_MOSI                  (1)                              //GPIO54
#define GPIO54_MODE_EMIF0_D30                  (2)                              //GPIO54
#define GPIO54_MODE_QEP1_A                     (5)                              //GPIO54
#define GPIO54_MODE_UART3_TX                   (6)                              //GPIO54
#define GPIO54_MODE_SDFM0_DATA4                (7)                              //GPIO54
#define GPIO54_MODE_EMIF0_A10                  (9)                              //GPIO54
#define GPIO54_MODE_QSPI_CLK                   (11)                             //GPIO54
#define GPIO54_MODE_SDFM0_CLK2                 (13)                             //GPIO54
#define GPIO54_MODE_ECAP6                      (14)                             //GPIO54

#define GPIO55_MODE_GPIO55                     (0)                              //GPIO55
#define GPIO55_MODE_SPI0_MISO                  (1)                              //GPIO55
#define GPIO55_MODE_EMIF0_D29                  (2)                              //GPIO55
#define GPIO55_MODE_SRPWM15_B                  (3)                              //GPIO55
#define GPIO55_MODE_QEP1_B                     (5)                              //GPIO55
#define GPIO55_MODE_UART3_RX                   (6)                              //GPIO55
#define GPIO55_MODE_SDFM0_CLK4                 (7)                              //GPIO55
#define GPIO55_MODE_EMIF0_D0                   (9)                              //GPIO55
#define GPIO55_MODE_QSPI_CS_n                  (11)                             //GPIO55
#define GPIO55_MODE_SDFM0_CLK3                 (13)                             //GPIO55
#define GPIO55_MODE_ECAP7                      (14)                             //GPIO55

#define GPIO56_MODE_GPIO56                     (0)                              //GPIO56
#define GPIO56_MODE_SPI0_CLK                   (1)                              //GPIO56
#define GPIO56_MODE_EMIF0_D28                  (2)                              //GPIO56
#define GPIO56_MODE_SRPWM16_A                  (3)                              //GPIO56
#define GPIO56_MODE_QEP1_STROBE                (5)                              //GPIO56
#define GPIO56_MODE_SDFM1_DATA1                (7)                              //GPIO56
#define GPIO56_MODE_EMIF0_D1                   (9)                              //GPIO56
#define GPIO56_MODE_I2C0_SDA                   (10)                             //GPIO56
#define GPIO56_MODE_UART0_TX                   (11)                             //GPIO56
#define GPIO56_MODE_SDFM0_CLK4                 (13)                             //GPIO56

#define GPIO57_MODE_GPIO57                     (0)                              //GPIO57
#define GPIO57_MODE_SPI0_CS_n                  (1)                              //GPIO57
#define GPIO57_MODE_EMIF0_D27                  (2)                              //GPIO57
#define GPIO57_MODE_SRPWM16_B                  (3)                              //GPIO57
#define GPIO57_MODE_QEP1_INDEX                 (5)                              //GPIO57
#define GPIO57_MODE_SDFM1_CLK1                 (7)                              //GPIO57
#define GPIO57_MODE_EMIF0_D2                   (9)                              //GPIO57
#define GPIO57_MODE_I2C0_SCL                   (10)                             //GPIO57
#define GPIO57_MODE_UART0_RX                   (11)                             //GPIO57
#define GPIO57_MODE_SDFM2_DATA3                (13)                             //GPIO57

#define GPIO58_MODE_GPIO58                     (0)                              //GPIO58
#define GPIO58_MODE_SPI0_MOSI                  (1)                              //GPIO58
#define GPIO58_MODE_EMIF0_D26                  (2)                              //GPIO58
#define GPIO58_MODE_SRPWM7_A                   (3)                              //GPIO58
#define GPIO58_MODE_OUTXBAR0                   (5)                              //GPIO58
#define GPIO58_MODE_SPI1_CLK                   (6)                              //GPIO58
#define GPIO58_MODE_SDFM1_DATA2                (7)                              //GPIO58
#define GPIO58_MODE_EMIF0_D3                   (9)                              //GPIO58
#define GPIO58_MODE_ECAP0                      (10)                             //GPIO58
#define GPIO58_MODE_CANFD0_RX                  (11)                             //GPIO58
#define GPIO58_MODE_SDFM1_CLK2                 (13)                             //GPIO58
#define GPIO58_MODE_SPI0_MOSI_BK               (15)                             //GPIO58

#define GPIO59_MODE_GPIO59                     (0)                              //GPIO59
#define GPIO59_MODE_SRPWM4_A                   (1)                              //GPIO59
#define GPIO59_MODE_EMIF0_D25                  (2)                              //GPIO59
#define GPIO59_MODE_SRPWM7_B                   (3)                              //GPIO59
#define GPIO59_MODE_OUTXBAR1                   (5)                              //GPIO59
#define GPIO59_MODE_SPI1_CS_n                  (6)                              //GPIO59
#define GPIO59_MODE_SDFM1_CLK2                 (7)                              //GPIO59
#define GPIO59_MODE_EMIF0_D4                   (9)                              //GPIO59
#define GPIO59_MODE_ECAP1                      (10)                             //GPIO59
#define GPIO59_MODE_CANFD0_TX                  (11)                             //GPIO59
#define GPIO59_MODE_SDFM1_CLK3                 (13)                             //GPIO59
#define GPIO59_MODE_SPI0_MISO                  (15)                             //GPIO59

#define GPIO60_MODE_GPIO60                     (0)                              //GPIO60
#define GPIO60_MODE_SRPWM2_B                   (1)                              //GPIO60
#define GPIO60_MODE_EMIF0_D24                  (2)                              //GPIO60
#define GPIO60_MODE_OUTXBAR2                   (5)                              //GPIO60
#define GPIO60_MODE_SPI1_MOSI                  (6)                              //GPIO60
#define GPIO60_MODE_SDFM1_DATA3                (7)                              //GPIO60
#define GPIO60_MODE_EMIF0_D5                   (9)                              //GPIO60
#define GPIO60_MODE_ECAP2                      (10)                             //GPIO60
#define GPIO60_MODE_SDFM1_CLK4                 (13)                             //GPIO60
#define GPIO60_MODE_SPI0_CLK                   (15)                             //GPIO60

#define GPIO99_MODE_GPIO99                     (0)                              //GPIO99
#define GPIO99_MODE_I2C0_SCL                   (1)                              //GPIO99
#define GPIO99_MODE_SRPWM17_B                  (2)                              //GPIO99
#define GPIO99_MODE_QEP2_B                     (5)                              //GPIO99
#define GPIO99_MODE_SDFM2_CLK1                 (6)                              //GPIO99

#define GPIO61_MODE_GPIO61                     (0)                              //GPIO61
#define GPIO61_MODE_SRPWM16_B                  (1)                              //GPIO61
#define GPIO61_MODE_EMIF0_D23                  (2)                              //GPIO61
#define GPIO61_MODE_OUTXBAR3                   (5)                              //GPIO61
#define GPIO61_MODE_SPI1_MISO                  (6)                              //GPIO61
#define GPIO61_MODE_SDFM1_CLK3                 (7)                              //GPIO61
#define GPIO61_MODE_EMIF0_D6                   (9)                              //GPIO61
#define GPIO61_MODE_ECAP3                      (10)                             //GPIO61
#define GPIO61_MODE_TESTPIN0                   (13)                             //GPIO61
#define GPIO61_MODE_CANFD0_RX                  (14)                             //GPIO61
#define GPIO61_MODE_SPI0_CS_n                  (15)                             //GPIO61

#define GPIO62_MODE_GPIO62                     (0)                              //GPIO62
#define GPIO62_MODE_UART2_RX                   (1)                              //GPIO62
#define GPIO62_MODE_EMIF0_D22                  (2)                              //GPIO62
#define GPIO62_MODE_SRPWM16_A                  (3)                              //GPIO62
#define GPIO62_MODE_QEP2_A                     (5)                              //GPIO62
#define GPIO62_MODE_CANFD0_RX                  (6)                              //GPIO62
#define GPIO62_MODE_SDFM1_DATA4                (7)                              //GPIO62
#define GPIO62_MODE_EMIF0_D7                   (9)                              //GPIO62
#define GPIO62_MODE_ECAP4                      (10)                             //GPIO62
#define GPIO62_MODE_UART0_RX                   (11)                             //GPIO62
#define GPIO62_MODE_TESTPIN1                   (13)                             //GPIO62
#define GPIO62_MODE_CANFD0_TX                  (14)                             //GPIO62

#define GPIO63_MODE_GPIO63                     (0)                              //GPIO63
#define GPIO63_MODE_UART2_TX                   (1)                              //GPIO63
#define GPIO63_MODE_EMIF0_D21                  (2)                              //GPIO63
#define GPIO63_MODE_SRPWM8_A                   (3)                              //GPIO63
#define GPIO63_MODE_QEP2_B                     (5)                              //GPIO63
#define GPIO63_MODE_CANFD0_TX                  (6)                              //GPIO63
#define GPIO63_MODE_SDFM1_CLK4                 (7)                              //GPIO63
#define GPIO63_MODE_EMIF0_RNW                  (9)                              //GPIO63
#define GPIO63_MODE_EMIF0_BA0                  (10)                             //GPIO63
#define GPIO63_MODE_UART0_TX                   (11)                             //GPIO63
#define GPIO63_MODE_SDFM0_DATA1                (13)                             //GPIO63
#define GPIO63_MODE_OUTXBAR8                   (14)                             //GPIO63
#define GPIO63_MODE_SPI1_MOSI                  (15)                             //GPIO63

#define GPIO64_MODE_GPIO64                     (0)                              //GPIO64
#define GPIO64_MODE_EMIF0_D20                  (2)                              //GPIO64
#define GPIO64_MODE_SRPWM8_B                   (3)                              //GPIO64
#define GPIO64_MODE_QEP2_STROBE                (5)                              //GPIO64
#define GPIO64_MODE_UART2_RX                   (6)                              //GPIO64
#define GPIO64_MODE_EMIF0_WAIT                 (9)                              //GPIO64
#define GPIO64_MODE_EMIF0_BA1                  (10)                             //GPIO64
#define GPIO64_MODE_TESTPIN2                   (11)                             //GPIO64
#define GPIO64_MODE_SDFM0_CLK1                 (13)                             //GPIO64
#define GPIO64_MODE_OUTXBAR9                   (14)                             //GPIO64
#define GPIO64_MODE_SPI1_MISO                  (15)                             //GPIO64

#define GPIO65_MODE_GPIO65                     (0)                              //GPIO65
#define GPIO65_MODE_EMIF0_D19                  (2)                              //GPIO65
#define GPIO65_MODE_SRPWM9_A                   (3)                              //GPIO65
#define GPIO65_MODE_QEP2_INDEX                 (5)                              //GPIO65
#define GPIO65_MODE_UART2_TX                   (6)                              //GPIO65
#define GPIO65_MODE_SRPWM3_A                   (7)                              //GPIO65
#define GPIO65_MODE_EMIF0_WE_n                 (9)                              //GPIO65
#define GPIO65_MODE_TESTPIN3                   (11)                             //GPIO65
#define GPIO65_MODE_SDFM0_DATA2                (13)                             //GPIO65
#define GPIO65_MODE_OUTXBAR10                  (14)                             //GPIO65
#define GPIO65_MODE_SPI1_CLK                   (15)                             //GPIO65

#define GPIO66_MODE_GPIO66                     (0)                              //GPIO66
#define GPIO66_MODE_QEP5_B                     (1)                              //GPIO66
#define GPIO66_MODE_EMIF0_D18                  (2)                              //GPIO66
#define GPIO66_MODE_SRPWM9_B                   (3)                              //GPIO66
#define GPIO66_MODE_I2C1_SDA                   (6)                              //GPIO66
#define GPIO66_MODE_SRPWM3_B                   (7)                              //GPIO66
#define GPIO66_MODE_EMIF0_OE_n                 (9)                              //GPIO66
#define GPIO66_MODE_SDFM0_CLK2                 (13)                             //GPIO66
#define GPIO66_MODE_OUTXBAR11                  (14)                             //GPIO66
#define GPIO66_MODE_SPI1_CS_n                  (15)                             //GPIO66

#define GPIO44_MODE_GPIO44                     (0)                              //GPIO44
#define GPIO44_MODE_SPI3_MISO                  (1)                              //GPIO44
#define GPIO44_MODE_EMIF0_A4                   (2)                              //GPIO44
#define GPIO44_MODE_CANFD2_RX                  (3)                              //GPIO44
#define GPIO44_MODE_SDFM2_CLK4                 (6)                              //GPIO44
#define GPIO44_MODE_UART1_TX                   (7)                              //GPIO44
#define GPIO44_MODE_CLB_OUTXBAR5               (10)                             //GPIO44
#define GPIO44_MODE_UART6_TX                   (11)                             //GPIO44
#define GPIO44_MODE_OUTXBAR8                   (15)                             //GPIO44

#define GPIO45_MODE_GPIO45                     (0)                              //GPIO45
#define GPIO45_MODE_SPI3_CS_n                  (1)                              //GPIO45
#define GPIO45_MODE_EMIF0_A5                   (2)                              //GPIO45
#define GPIO45_MODE_CANFD2_TX                  (3)                              //GPIO45
#define GPIO45_MODE_SDFM2_DATA4                (6)                              //GPIO45
#define GPIO45_MODE_UART1_RX                   (7)                              //GPIO45
#define GPIO45_MODE_CLB_OUTXBAR6               (10)                             //GPIO45
#define GPIO45_MODE_UART6_RX                   (11)                             //GPIO45
#define GPIO45_MODE_OUTXBAR9                   (15)                             //GPIO45

#define GPIO32_MODE_GPIO32                     (0)                              //GPIO32
#define GPIO32_MODE_I2C0_SDA                   (1)                              //GPIO32
#define GPIO32_MODE_EMIF0_CS0_n                (2)                              //GPIO32
#define GPIO32_MODE_SPI0_MOSI                  (3)                              //GPIO32
#define GPIO32_MODE_QEP3_A                     (5)                              //GPIO32
#define GPIO32_MODE_LIN1_TX                    (6)                              //GPIO32
#define GPIO32_MODE_CLB_OUTXBAR0               (7)                              //GPIO32
#define GPIO32_MODE_EMIF0_OE_n                 (9)                              //GPIO32
#define GPIO32_MODE_I2C0_SCL                   (10)                             //GPIO32
#define GPIO32_MODE_UART5_TX                   (11)                             //GPIO32
#define GPIO32_MODE_ECAP0                      (14)                             //GPIO32
#define GPIO32_MODE_SPI3_CLK                   (15)                             //GPIO32

#define GPIO101_MODE_GPIO101                   (0)                              //GPIO101
#define GPIO101_MODE_EMIF0_A11                 (1)                              //GPIO101
#define GPIO101_MODE_SRPWM8_A                  (2)                              //GPIO101
#define GPIO101_MODE_AUXCLKIN                  (3)                              //GPIO101
#define GPIO101_MODE_SDFM1_CLK2                (7)                              //GPIO101

#define GPIO125_XTAL_OUT_MODE_GPIO125          (0)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_SRPWM5_B         (2)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_SPI3_CS_n        (3)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_OUTXBAR2         (5)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_UART3_RX         (6)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_CANFD1_RX        (7)                              //GPIO125_XTAL_OUT
#define GPIO125_XTAL_OUT_MODE_PMBUS0_CTL_n     (15)                             //GPIO125_XTAL_OUT

#define GPIO123_MODE_GPIO123                   (0)                              //GPIO123

#define GPIO124_XTAL_IN_MODE_GPIO124           (0)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_SRPWM5_A          (2)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_SPI3_MISO         (3)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_OUTXBAR1          (5)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_UART3_TX          (6)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_CANFD1_TX         (7)                              //GPIO124_XTAL_IN
#define GPIO124_XTAL_IN_MODE_PMBUS0_ALERT_n    (15)                             //GPIO124_XTAL_IN

#define GPIO27_MODE_GPIO27                     (0)                              //GPIO27
#define GPIO27_MODE_OUTXBAR3                   (1)                              //GPIO27
#define GPIO27_MODE_QEP1_STROBE                (2)                              //GPIO27
#define GPIO27_MODE_OUTXBAR3_BK                (5)                              //GPIO27
#define GPIO27_MODE_SPI1_CS_n                  (6)                              //GPIO27
#define GPIO27_MODE_SDFM1_CLK2                 (7)                              //GPIO27
#define GPIO27_MODE_PMBUS0_CTL_n               (9)                              //GPIO27
#define GPIO27_MODE_EMIF0_DQM3                 (10)                             //GPIO27
#define GPIO27_MODE_SRPWM13_B                  (13)                             //GPIO27

#define GPIO97_MODE_GPIO97                     (0)                              //GPIO97
#define GPIO97_MODE_EMIF0_BA0                  (2)                              //GPIO97
#define GPIO97_MODE_SRPWM7_B                   (3)                              //GPIO97
#define GPIO97_MODE_QEP1_INDEX                 (5)                              //GPIO97
#define GPIO97_MODE_SPI2_CS_n                  (6)                              //GPIO97
#define GPIO97_MODE_SDFM3_CLK4                 (7)                              //GPIO97
#define GPIO97_MODE_UART7_TX                   (9)                              //GPIO97

#define GPIO46_MODE_GPIO46                     (0)                              //GPIO46
#define GPIO46_MODE_SRPWM3_A                   (1)                              //GPIO46
#define GPIO46_MODE_EMIF0_A6                   (2)                              //GPIO46
#define GPIO46_MODE_SRPWM13_A                  (3)                              //GPIO46
#define GPIO46_MODE_UART1_RX                   (5)                              //GPIO46
#define GPIO46_MODE_UART2_RX                   (6)                              //GPIO46
#define GPIO46_MODE_SDFM2_CLK4                 (7)                              //GPIO46
#define GPIO46_MODE_OUTXBAR10                  (15)                             //GPIO46

#define GPIO47_MODE_GPIO47                     (0)                              //GPIO47
#define GPIO47_MODE_SRPWM3_B                   (1)                              //GPIO47
#define GPIO47_MODE_EMIF0_A7                   (2)                              //GPIO47
#define GPIO47_MODE_SRPWM13_B                  (3)                              //GPIO47
#define GPIO47_MODE_UART1_TX                   (5)                              //GPIO47
#define GPIO47_MODE_UART2_TX                   (6)                              //GPIO47
#define GPIO47_MODE_SDFM3_CLK3                 (7)                              //GPIO47
#define GPIO47_MODE_OUTXBAR11                  (15)                             //GPIO47

#define GPIO42_MODE_GPIO42                     (0)                              //GPIO42
#define GPIO42_MODE_SRPWM13_A                  (3)                              //GPIO42
#define GPIO42_MODE_QEP3_A                     (5)                              //GPIO42
#define GPIO42_MODE_I2C0_SDA                   (6)                              //GPIO42
#define GPIO42_MODE_SDFM3_CLK4                 (7)                              //GPIO42
#define GPIO42_MODE_SDFM2_CLK4                 (9)                              //GPIO42
#define GPIO42_MODE_CLB_OUTXBAR4               (10)                             //GPIO42
#define GPIO42_MODE_UART0_TX                   (11)                             //GPIO42
#define GPIO42_MODE_UART2_TX                   (15)                             //GPIO42

#define GPIO43_MODE_GPIO43                     (0)                              //GPIO43
#define GPIO43_MODE_SRPWM13_B                  (3)                              //GPIO43
#define GPIO43_MODE_QEP3_B                     (5)                              //GPIO43
#define GPIO43_MODE_I2C0_SCL                   (6)                              //GPIO43
#define GPIO43_MODE_SDFM3_DATA4                (7)                              //GPIO43
#define GPIO43_MODE_SDFM3_CLK3                 (9)                              //GPIO43
#define GPIO43_MODE_CLB_OUTXBAR5               (10)                             //GPIO43
#define GPIO43_MODE_UART0_RX                   (11)                             //GPIO43
#define GPIO43_MODE_UART2_RX                   (15)                             //GPIO43

#define GPIO67_MODE_GPIO67                     (0)                              //GPIO67
#define GPIO67_MODE_UART5_TX                   (1)                              //GPIO67
#define GPIO67_MODE_EMIF0_D17                  (2)                              //GPIO67
#define GPIO67_MODE_SRPWM16_A                  (3)                              //GPIO67
#define GPIO67_MODE_LIN1_TX                    (5)                              //GPIO67
#define GPIO67_MODE_SDFM0_DATA3                (13)                             //GPIO67

#define GPIO68_MODE_GPIO68                     (0)                              //GPIO68
#define GPIO68_MODE_UART5_RX                   (1)                              //GPIO68
#define GPIO68_MODE_EMIF0_D16                  (2)                              //GPIO68
#define GPIO68_MODE_SRPWM16_B                  (3)                              //GPIO68
#define GPIO68_MODE_LIN1_RX                    (5)                              //GPIO68
#define GPIO68_MODE_SDFM0_CLK3                 (13)                             //GPIO68

#define GPIO69_MODE_GPIO69                     (0)                              //GPIO69
#define GPIO69_MODE_SRPWM0_A                   (1)                              //GPIO69
#define GPIO69_MODE_EMIF0_D15                  (2)                              //GPIO69
#define GPIO69_MODE_SRPWM10_A                  (3)                              //GPIO69
#define GPIO69_MODE_I2C1_SCL                   (6)                              //GPIO69
#define GPIO69_MODE_ECAP5                      (10)                             //GPIO69
#define GPIO69_MODE_SDFM0_DATA4                (13)                             //GPIO69
#define GPIO69_MODE_TRACED0                    (14)                             //GPIO69
#define GPIO69_MODE_SPI2_MOSI                  (15)                             //GPIO69

#define GPIO70_MODE_GPIO70                     (0)                              //GPIO70
#define GPIO70_MODE_SRPWM0_B                   (1)                              //GPIO70
#define GPIO70_MODE_EMIF0_D14                  (2)                              //GPIO70
#define GPIO70_MODE_SRPWM10_B                  (3)                              //GPIO70
#define GPIO70_MODE_CANFD0_RX                  (5)                              //GPIO70
#define GPIO70_MODE_UART3_TX                   (6)                              //GPIO70
#define GPIO70_MODE_UART1_TX                   (7)                              //GPIO70
#define GPIO70_MODE_CANFD1_RX                  (9)                              //GPIO70
#define GPIO70_MODE_ECAP6                      (10)                             //GPIO70
#define GPIO70_MODE_SDFM0_CLK4                 (13)                             //GPIO70
#define GPIO70_MODE_TRACED1                    (14)                             //GPIO70
#define GPIO70_MODE_SPI2_MISO                  (15)                             //GPIO70

#define GPIO71_MODE_GPIO71                     (0)                              //GPIO71
#define GPIO71_MODE_EMIF0_D13                  (2)                              //GPIO71
#define GPIO71_MODE_SRPWM11_A                  (3)                              //GPIO71
#define GPIO71_MODE_CANFD0_TX                  (5)                              //GPIO71
#define GPIO71_MODE_UART3_RX                   (6)                              //GPIO71
#define GPIO71_MODE_UART1_RX                   (7)                              //GPIO71
#define GPIO71_MODE_CANFD1_TX                  (9)                              //GPIO71
#define GPIO71_MODE_ECAP7                      (10)                             //GPIO71
#define GPIO71_MODE_SDFM2_DATA1                (13)                             //GPIO71
#define GPIO71_MODE_TRACED2                    (14)                             //GPIO71
#define GPIO71_MODE_SPI2_CLK                   (15)                             //GPIO71

#define GPIO72_MODE_GPIO72                     (0)                              //GPIO72
#define GPIO72_MODE_QEP5_STROBE                (1)                              //GPIO72
#define GPIO72_MODE_EMIF0_D12                  (2)                              //GPIO72
#define GPIO72_MODE_SRPWM11_B                  (3)                              //GPIO72
#define GPIO72_MODE_OUTXBAR7                   (5)                              //GPIO72
#define GPIO72_MODE_UART0_TX                   (6)                              //GPIO72
#define GPIO72_MODE_QEP1_INDEX                 (7)                              //GPIO72
#define GPIO72_MODE_CANFD2_RX                  (9)                              //GPIO72
#define GPIO72_MODE_CANFD1_TX                  (11)                             //GPIO72
#define GPIO72_MODE_SDFM2_CLK1                 (13)                             //GPIO72
#define GPIO72_MODE_TRACED3                    (14)                             //GPIO72
#define GPIO72_MODE_SPI2_CS_n                  (15)                             //GPIO72

#define GPIO73_MODE_GPIO73                     (0)                              //GPIO73
#define GPIO73_MODE_QEP5_INDEX                 (1)                              //GPIO73
#define GPIO73_MODE_EMIF0_D11                  (2)                              //GPIO73
#define GPIO73_MODE_XCLKOUT                    (3)                              //GPIO73
#define GPIO73_MODE_OUTXBAR5                   (5)                              //GPIO73
#define GPIO73_MODE_UART0_RX                   (6)                              //GPIO73
#define GPIO73_MODE_SRPWM4_B                   (7)                              //GPIO73
#define GPIO73_MODE_CANFD2_TX                  (9)                              //GPIO73
#define GPIO73_MODE_SDFM3_DATA4                (10)                             //GPIO73
#define GPIO73_MODE_CANFD1_RX                  (11)                             //GPIO73
#define GPIO73_MODE_SDFM1_DATA2                (13)                             //GPIO73
#define GPIO73_MODE_TRACECLK                   (14)                             //GPIO73
#define GPIO73_MODE_QEP1_B                     (15)                             //GPIO73

#define GPIO74_MODE_GPIO74                     (0)                              //GPIO74
#define GPIO74_MODE_SRPWM7_A                   (1)                              //GPIO74
#define GPIO74_MODE_EMIF0_D10                  (2)                              //GPIO74
#define GPIO74_MODE_QEP4_A                     (6)                              //GPIO74
#define GPIO74_MODE_CANFD1_TX                  (9)                              //GPIO74
#define GPIO74_MODE_SDFM0_DATA4                (10)                             //GPIO74
#define GPIO74_MODE_SDFM1_CLK2                 (13)                             //GPIO74
#define GPIO74_MODE_UART6_TX                   (14)                             //GPIO74
#define GPIO74_MODE_QSPI_IO0                   (15)                             //GPIO74

#define GPIO75_MODE_GPIO75                     (0)                              //GPIO75
#define GPIO75_MODE_SRPWM7_B                   (1)                              //GPIO75
#define GPIO75_MODE_EMIF0_D9                   (2)                              //GPIO75
#define GPIO75_MODE_QEP4_B                     (6)                              //GPIO75
#define GPIO75_MODE_SPI3_CLK                   (7)                              //GPIO75
#define GPIO75_MODE_CANFD1_RX                  (9)                              //GPIO75
#define GPIO75_MODE_CLB_OUTXBAR7               (10)                             //GPIO75
#define GPIO75_MODE_SDFM1_DATA3                (13)                             //GPIO75
#define GPIO75_MODE_UART6_RX                   (14)                             //GPIO75
#define GPIO75_MODE_QSPI_IO1                   (15)                             //GPIO75

#define GPIO76_MODE_GPIO76                     (0)                              //GPIO76
#define GPIO76_MODE_SRPWM8_A                   (1)                              //GPIO76
#define GPIO76_MODE_EMIF0_D8                   (2)                              //GPIO76
#define GPIO76_MODE_QEP4_STROBE                (6)                              //GPIO76
#define GPIO76_MODE_SDFM2_CLK1                 (7)                              //GPIO76
#define GPIO76_MODE_SDFM3_DATA4                (10)                             //GPIO76
#define GPIO76_MODE_SDFM1_CLK3                 (13)                             //GPIO76
#define GPIO76_MODE_UART1_TX                   (14)                             //GPIO76
#define GPIO76_MODE_QSPI_IO2                   (15)                             //GPIO76

#define GPIO77_MODE_GPIO77                     (0)                              //GPIO77
#define GPIO77_MODE_SRPWM8_B                   (1)                              //GPIO77
#define GPIO77_MODE_EMIF0_D7                   (2)                              //GPIO77
#define GPIO77_MODE_QEP4_INDEX                 (6)                              //GPIO77
#define GPIO77_MODE_SDFM2_DATA1                (7)                              //GPIO77
#define GPIO77_MODE_SDFM0_DATA4                (10)                             //GPIO77
#define GPIO77_MODE_SDFM1_DATA4                (13)                             //GPIO77
#define GPIO77_MODE_UART1_RX                   (14)                             //GPIO77
#define GPIO77_MODE_QSPI_IO3                   (15)                             //GPIO77

#define GPIO78_MODE_GPIO78                     (0)                              //GPIO78
#define GPIO78_MODE_SRPWM9_A                   (1)                              //GPIO78
#define GPIO78_MODE_EMIF0_D6                   (2)                              //GPIO78
#define GPIO78_MODE_QEP1_A                     (6)                              //GPIO78
#define GPIO78_MODE_SDFM2_CLK2                 (7)                              //GPIO78
#define GPIO78_MODE_SDFM1_CLK1                 (9)                              //GPIO78
#define GPIO78_MODE_SDFM3_DATA4                (10)                             //GPIO78
#define GPIO78_MODE_SDFM1_CLK4                 (13)                             //GPIO78
#define GPIO78_MODE_UART6_TX                   (14)                             //GPIO78
#define GPIO78_MODE_QSPI_CLK                   (15)                             //GPIO78

#define GPIO79_MODE_GPIO79                     (0)                              //GPIO79
#define GPIO79_MODE_SRPWM9_B                   (1)                              //GPIO79
#define GPIO79_MODE_EMIF0_D5                   (2)                              //GPIO79
#define GPIO79_MODE_ERRORSTS                   (5)                              //GPIO79
#define GPIO79_MODE_QEP1_B                     (6)                              //GPIO79
#define GPIO79_MODE_SDFM2_DATA2                (7)                              //GPIO79
#define GPIO79_MODE_SDFM1_DATA1                (13)                             //GPIO79
#define GPIO79_MODE_UART6_RX                   (14)                             //GPIO79
#define GPIO79_MODE_QSPI_CS_n                  (15)                             //GPIO79

#define GPIO98_MODE_GPIO98                     (0)                              //GPIO98
#define GPIO98_MODE_I2C0_SDA                   (1)                              //GPIO98
#define GPIO98_MODE_SRPWM17_A                  (2)                              //GPIO98
#define GPIO98_MODE_QEP2_A                     (5)                              //GPIO98
#define GPIO98_MODE_SDFM2_DATA1                (6)                              //GPIO98
#define GPIO98_MODE_UART7_RX                   (9)                              //GPIO98

#define GPIO80_MODE_GPIO80                     (0)                              //GPIO80
#define GPIO80_MODE_SRPWM10_A                  (1)                              //GPIO80
#define GPIO80_MODE_EMIF0_D4                   (2)                              //GPIO80
#define GPIO80_MODE_ERRORSTS                   (5)                              //GPIO80
#define GPIO80_MODE_QEP1_STROBE                (6)                              //GPIO80
#define GPIO80_MODE_SDFM2_CLK3                 (7)                              //GPIO80
#define GPIO80_MODE_SDFM0_DATA4                (10)                             //GPIO80
#define GPIO80_MODE_SDFM1_CLK1                 (13)                             //GPIO80

#define GPIO81_MODE_GPIO81                     (0)                              //GPIO81
#define GPIO81_MODE_SRPWM10_B                  (1)                              //GPIO81
#define GPIO81_MODE_EMIF0_D3                   (2)                              //GPIO81
#define GPIO81_MODE_QEP1_INDEX                 (6)                              //GPIO81
#define GPIO81_MODE_SDFM2_DATA3                (7)                              //GPIO81

#define GPIO82_MODE_GPIO82                     (0)                              //GPIO82
#define GPIO82_MODE_SRPWM11_A                  (1)                              //GPIO82
#define GPIO82_MODE_EMIF0_D2                   (2)                              //GPIO82
#define GPIO82_MODE_UART4_TX                   (5)                              //GPIO82
#define GPIO82_MODE_SDFM2_CLK2                 (14)                             //GPIO82

#define GPIO83_MODE_GPIO83                     (0)                              //GPIO83
#define GPIO83_MODE_SRPWM11_B                  (1)                              //GPIO83
#define GPIO83_MODE_EMIF0_D1                   (2)                              //GPIO83
#define GPIO83_MODE_UART4_RX                   (5)                              //GPIO83
#define GPIO83_MODE_SDFM2_DATA2                (14)                             //GPIO83

#define GPIO25_MODE_GPIO25                     (0)                              //GPIO25
#define GPIO25_MODE_OUTXBAR1                   (1)                              //GPIO25
#define GPIO25_MODE_QEP1_B                     (2)                              //GPIO25
#define GPIO25_MODE_UART5_RX                   (3)                              //GPIO25
#define GPIO25_MODE_LIN1_RX                    (5)                              //GPIO25
#define GPIO25_MODE_SPI1_MISO                  (6)                              //GPIO25
#define GPIO25_MODE_SDFM1_CLK1                 (7)                              //GPIO25
#define GPIO25_MODE_PMBUS0_SDA                 (9)                              //GPIO25
#define GPIO25_MODE_EMIF0_DQM1                 (10)                             //GPIO25
#define GPIO25_MODE_QEP4_B                     (11)                             //GPIO25
#define GPIO25_MODE_SRPWM12_B                  (13)                             //GPIO25

#define GPIO84_MODE_GPIO84                     (0)                              //GPIO84
#define GPIO84_MODE_SRPWM11_B                  (1)                              //GPIO84
#define GPIO84_MODE_EMIF0_D1                   (2)                              //GPIO84
#define GPIO84_MODE_EMIF0_CS4_n                (3)                              //GPIO84
#define GPIO84_MODE_UART2_TX                   (5)                              //GPIO84
#define GPIO84_MODE_QEP5_A                     (6)                              //GPIO84
#define GPIO84_MODE_LIN1_TX                    (7)                              //GPIO84
#define GPIO84_MODE_SDFM2_DATA2                (9)                              //GPIO84
#define GPIO84_MODE_OUTXBAR8                   (10)                             //GPIO84
#define GPIO84_MODE_UART0_TX                   (11)                             //GPIO84
#define GPIO84_MODE_SDFM2_CLK2                 (13)                             //GPIO84
#define GPIO84_MODE_TRACED4                    (14)                             //GPIO84
#define GPIO84_MODE_UART5_TX                   (15)                             //GPIO84

#define GPIO85_MODE_GPIO85                     (0)                              //GPIO85
#define GPIO85_MODE_SRPWM12_A                  (1)                              //GPIO85
#define GPIO85_MODE_EMIF0_D0                   (2)                              //GPIO85
#define GPIO85_MODE_UART2_RX                   (5)                              //GPIO85
#define GPIO85_MODE_QEP5_B                     (6)                              //GPIO85
#define GPIO85_MODE_SDFM2_DATA1                (7)                              //GPIO85
#define GPIO85_MODE_QEP1_STROBE                (9)                              //GPIO85
#define GPIO85_MODE_OUTXBAR9                   (10)                             //GPIO85
#define GPIO85_MODE_UART0_RX                   (11)                             //GPIO85
#define GPIO85_MODE_SDFM2_DATA3                (13)                             //GPIO85
#define GPIO85_MODE_TRACED5                    (14)                             //GPIO85
#define GPIO85_MODE_EMIF0_DQM2                 (15)                             //GPIO85

#define GPIO86_MODE_GPIO86                     (0)                              //GPIO86
#define GPIO86_MODE_SRPWM12_B                  (1)                              //GPIO86
#define GPIO86_MODE_EMIF0_A13                  (2)                              //GPIO86
#define GPIO86_MODE_EMIF0_CAS_n                (3)                              //GPIO86
#define GPIO86_MODE_UART3_TX                   (5)                              //GPIO86
#define GPIO86_MODE_QEP5_STROBE                (6)                              //GPIO86
#define GPIO86_MODE_LIN1_RX                    (7)                              //GPIO86
#define GPIO86_MODE_UART5_RX                   (9)                              //GPIO86
#define GPIO86_MODE_OUTXBAR10                  (10)                             //GPIO86
#define GPIO86_MODE_SDFM2_CLK3                 (13)                             //GPIO86
#define GPIO86_MODE_TRACED6                    (14)                             //GPIO86

#define GPIO87_MODE_GPIO87                     (0)                              //GPIO87
#define GPIO87_MODE_SRPWM13_A                  (1)                              //GPIO87
#define GPIO87_MODE_EMIF0_A14                  (2)                              //GPIO87
#define GPIO87_MODE_EMIF0_RAS_n                (3)                              //GPIO87
#define GPIO87_MODE_UART3_RX                   (5)                              //GPIO87
#define GPIO87_MODE_QEP5_INDEX                 (6)                              //GPIO87
#define GPIO87_MODE_EMIF0_DQM3                 (9)                              //GPIO87
#define GPIO87_MODE_OUTXBAR11                  (10)                             //GPIO87
#define GPIO87_MODE_SDFM2_DATA4                (13)                             //GPIO87
#define GPIO87_MODE_TRACED7                    (14)                             //GPIO87

#define GPIO31_MODE_GPIO31                     (0)                              //GPIO31
#define GPIO31_MODE_CANFD0_TX                  (1)                              //GPIO31
#define GPIO31_MODE_EMIF0_WE_n                 (2)                              //GPIO31
#define GPIO31_MODE_CANFD1_TX                  (3)                              //GPIO31
#define GPIO31_MODE_OUTXBAR7                   (5)                              //GPIO31
#define GPIO31_MODE_QEP2_INDEX                 (6)                              //GPIO31
#define GPIO31_MODE_SDFM1_CLK4                 (7)                              //GPIO31
#define GPIO31_MODE_EMIF0_RNW                  (9)                              //GPIO31
#define GPIO31_MODE_I2C0_SDA                   (10)                             //GPIO31
#define GPIO31_MODE_SRPWM15_B                  (13)                             //GPIO31
#define GPIO31_MODE_SPI3_MISO                  (15)                             //GPIO31

#define GPIO24_MODE_GPIO24                     (0)                              //GPIO24
#define GPIO24_MODE_OUTXBAR0                   (1)                              //GPIO24
#define GPIO24_MODE_QEP1_A                     (2)                              //GPIO24
#define GPIO24_MODE_UART5_TX                   (3)                              //GPIO24
#define GPIO24_MODE_LIN1_TX                    (5)                              //GPIO24
#define GPIO24_MODE_SPI1_MOSI                  (6)                              //GPIO24
#define GPIO24_MODE_SDFM1_DATA1                (7)                              //GPIO24
#define GPIO24_MODE_PMBUS0_SCL                 (9)                              //GPIO24
#define GPIO24_MODE_EMIF0_DQM0                 (10)                             //GPIO24
#define GPIO24_MODE_SRPWM12_A                  (13)                             //GPIO24

#define GPIO0_MODE_GPIO0                       (0)                              //GPIO0
#define GPIO0_MODE_SRPWM0_A                    (1)                              //GPIO0
#define GPIO0_MODE_CLB_OUTXBAR0                (5)                              //GPIO0
#define GPIO0_MODE_I2C0_SDA                    (6)                              //GPIO0
#define GPIO0_MODE_EMIF0_A13                   (9)                              //GPIO0
#define GPIO0_MODE_TRACED8                     (11)                             //GPIO0

#define GPIO1_MODE_GPIO1                       (0)                              //GPIO1
#define GPIO1_MODE_SRPWM0_B                    (1)                              //GPIO1
#define GPIO1_MODE_CLB_OUTXBAR1                (5)                              //GPIO1
#define GPIO1_MODE_I2C0_SCL                    (6)                              //GPIO1
#define GPIO1_MODE_EMIF0_A14                   (9)                              //GPIO1
#define GPIO1_MODE_TRACED9                     (11)                             //GPIO1

#define GPIO2_MODE_GPIO2                       (0)                              //GPIO2
#define GPIO2_MODE_SRPWM1_A                    (1)                              //GPIO2
#define GPIO2_MODE_SRPWM0_A                    (3)                              //GPIO2
#define GPIO2_MODE_OUTXBAR0                    (5)                              //GPIO2
#define GPIO2_MODE_I2C1_SDA                    (6)                              //GPIO2
#define GPIO2_MODE_UART0_TX                    (7)                              //GPIO2
#define GPIO2_MODE_EMIF0_A15                   (9)                              //GPIO2
#define GPIO2_MODE_TRACED10                    (11)                             //GPIO2
#define GPIO2_MODE_ECAP0                       (14)                             //GPIO2

#define GPIO3_MODE_GPIO3                       (0)                              //GPIO3
#define GPIO3_MODE_SRPWM1_B                    (1)                              //GPIO3
#define GPIO3_MODE_OUTXBAR1                    (2)                              //GPIO3
#define GPIO3_MODE_SRPWM0_B                    (3)                              //GPIO3
#define GPIO3_MODE_OUTXBAR1_BK                 (5)                              //GPIO3
#define GPIO3_MODE_I2C1_SCL                    (6)                              //GPIO3
#define GPIO3_MODE_UART0_RX                    (7)                              //GPIO3
#define GPIO3_MODE_TRACED11                    (11)                             //GPIO3
#define GPIO3_MODE_ECAP1                       (14)                             //GPIO3

#define GPIO4_MODE_GPIO4                       (0)                              //GPIO4
#define GPIO4_MODE_SRPWM2_A                    (1)                              //GPIO4
#define GPIO4_MODE_SYNCOUT                     (3)                              //GPIO4
#define GPIO4_MODE_OUTXBAR2                    (5)                              //GPIO4
#define GPIO4_MODE_CANFD0_TX                   (6)                              //GPIO4
#define GPIO4_MODE_CANFD1_TX                   (9)                              //GPIO4
#define GPIO4_MODE_TRACED8                     (11)                             //GPIO4
#define GPIO4_MODE_ECAP2                       (14)                             //GPIO4

#define GPIO5_MODE_GPIO5                       (0)                              //GPIO5
#define GPIO5_MODE_SRPWM2_B                    (1)                              //GPIO5
#define GPIO5_MODE_OUTXBAR2                    (3)                              //GPIO5
#define GPIO5_MODE_CLB_OUTXBAR2                (5)                              //GPIO5
#define GPIO5_MODE_CANFD0_RX                   (6)                              //GPIO5
#define GPIO5_MODE_CANFD1_RX                   (9)                              //GPIO5

#define GPIO6_MODE_GPIO6                       (0)                              //GPIO6
#define GPIO6_MODE_SRPWM3_A                    (1)                              //GPIO6
#define GPIO6_MODE_OUTXBAR3                    (2)                              //GPIO6
#define GPIO6_MODE_SYNCOUT                     (3)                              //GPIO6
#define GPIO6_MODE_QEP2_A                      (5)                              //GPIO6
#define GPIO6_MODE_CANFD2_TX                   (6)                              //GPIO6
#define GPIO6_MODE_LIN0_TX                     (7)                              //GPIO6
#define GPIO6_MODE_EMIF0_DQM0                  (9)                              //GPIO6
#define GPIO6_MODE_UART4_TX                    (10)                             //GPIO6
#define GPIO6_MODE_CANFD1_TX                   (11)                             //GPIO6

#define GPIO7_MODE_GPIO7                       (0)                              //GPIO7
#define GPIO7_MODE_SRPWM3_B                    (1)                              //GPIO7
#define GPIO7_MODE_OUTXBAR4                    (3)                              //GPIO7
#define GPIO7_MODE_QEP2_B                      (5)                              //GPIO7
#define GPIO7_MODE_CANFD2_RX                   (6)                              //GPIO7
#define GPIO7_MODE_LIN0_RX                     (7)                              //GPIO7
#define GPIO7_MODE_EMIF0_DQM1                  (9)                              //GPIO7
#define GPIO7_MODE_UART4_RX                    (10)                             //GPIO7
#define GPIO7_MODE_CANFD1_RX                   (11)                             //GPIO7

#define GPIO88_MODE_GPIO88                     (0)                              //GPIO88
#define GPIO88_MODE_SRPWM13_B                  (1)                              //GPIO88
#define GPIO88_MODE_EMIF0_A15                  (2)                              //GPIO88
#define GPIO88_MODE_EMIF0_DQM0                 (3)                              //GPIO88
#define GPIO88_MODE_EMIF0_DQM1                 (9)                              //GPIO88
#define GPIO88_MODE_SDFM2_CLK4                 (13)                             //GPIO88

#define GPIO89_MODE_GPIO89                     (0)                              //GPIO89
#define GPIO89_MODE_SRPWM14_A                  (1)                              //GPIO89
#define GPIO89_MODE_EMIF0_A16                  (2)                              //GPIO89
#define GPIO89_MODE_EMIF0_DQM1                 (3)                              //GPIO89
#define GPIO89_MODE_UART7_TX                   (6)                              //GPIO89
#define GPIO89_MODE_SDFM0_DATA3                (7)                              //GPIO89
#define GPIO89_MODE_EMIF0_CAS_n                (9)                              //GPIO89
#define GPIO89_MODE_UART6_TX                   (10)                             //GPIO89
#define GPIO89_MODE_TRACED12                   (11)                             //GPIO89
#define GPIO89_MODE_SDFM3_DATA1                (13)                             //GPIO89
#define GPIO89_MODE_UART0_TX                   (14)                             //GPIO89
#define GPIO89_MODE_SPI3_CS_n                  (15)                             //GPIO89

#define GPIO90_MODE_GPIO90                     (0)                              //GPIO90
#define GPIO90_MODE_SRPWM14_B                  (1)                              //GPIO90
#define GPIO90_MODE_EMIF0_A17                  (2)                              //GPIO90
#define GPIO90_MODE_EMIF0_DQM2                 (3)                              //GPIO90
#define GPIO90_MODE_UART7_RX                   (6)                              //GPIO90
#define GPIO90_MODE_SDFM0_CLK3                 (7)                              //GPIO90
#define GPIO90_MODE_EMIF0_RAS_n                (9)                              //GPIO90
#define GPIO90_MODE_UART6_RX                   (10)                             //GPIO90
#define GPIO90_MODE_TRACED13                   (11)                             //GPIO90
#define GPIO90_MODE_SDFM3_CLK1                 (13)                             //GPIO90
#define GPIO90_MODE_UART0_RX                   (14)                             //GPIO90
#define GPIO90_MODE_SPI3_CLK                   (15)                             //GPIO90

#define GPIO91_MODE_GPIO91                     (0)                              //GPIO91
#define GPIO91_MODE_SRPWM15_A                  (1)                              //GPIO91
#define GPIO91_MODE_EMIF0_A18                  (2)                              //GPIO91
#define GPIO91_MODE_EMIF0_DQM3                 (3)                              //GPIO91
#define GPIO91_MODE_UART7_TX                   (5)                              //GPIO91
#define GPIO91_MODE_I2C0_SDA                   (6)                              //GPIO91
#define GPIO91_MODE_SDFM3_DATA2                (7)                              //GPIO91
#define GPIO91_MODE_EMIF0_DQM2                 (9)                              //GPIO91
#define GPIO91_MODE_PMBUS0_SCL                 (10)                             //GPIO91
#define GPIO91_MODE_TRACED14                   (11)                             //GPIO91
#define GPIO91_MODE_CLB_OUTXBAR0               (14)                             //GPIO91
#define GPIO91_MODE_SPI3_MOSI                  (15)                             //GPIO91

#define GPIO92_MODE_GPIO92                     (0)                              //GPIO92
#define GPIO92_MODE_SRPWM15_B                  (1)                              //GPIO92
#define GPIO92_MODE_EMIF0_A19                  (2)                              //GPIO92
#define GPIO92_MODE_EMIF0_BA1                  (3)                              //GPIO92
#define GPIO92_MODE_UART7_RX                   (5)                              //GPIO92
#define GPIO92_MODE_I2C0_SCL                   (6)                              //GPIO92
#define GPIO92_MODE_SDFM3_CLK2                 (7)                              //GPIO92
#define GPIO92_MODE_EMIF0_DQM0                 (9)                              //GPIO92
#define GPIO92_MODE_PMBUS0_SDA                 (10)                             //GPIO92
#define GPIO92_MODE_TRACED15                   (11)                             //GPIO92
#define GPIO92_MODE_QSPI_CS_n                  (13)                             //GPIO92
#define GPIO92_MODE_CLB_OUTXBAR1               (14)                             //GPIO92
#define GPIO92_MODE_SPI3_MISO                  (15)                             //GPIO92

#define GPIO93_MODE_GPIO93                     (0)                              //GPIO93
#define GPIO93_MODE_SRPWM16_A                  (1)                              //GPIO93
#define GPIO93_MODE_EMIF0_BA0                  (3)                              //GPIO93
#define GPIO93_MODE_SDFM3_DATA3                (7)                              //GPIO93
#define GPIO93_MODE_PMBUS0_ALERT_n             (10)                             //GPIO93
#define GPIO93_MODE_UART1_TX                   (13)                             //GPIO93
#define GPIO93_MODE_CLB_OUTXBAR2               (14)                             //GPIO93
#define GPIO93_MODE_SPI3_CLK                   (15)                             //GPIO93

#define GPIO94_MODE_GPIO94                     (0)                              //GPIO94
#define GPIO94_MODE_SRPWM16_B                  (1)                              //GPIO94
#define GPIO94_MODE_SDFM3_CLK3                 (7)                              //GPIO94
#define GPIO94_MODE_EMIF0_BA1                  (9)                              //GPIO94
#define GPIO94_MODE_PMBUS0_CTL_n               (10)                             //GPIO94
#define GPIO94_MODE_UART1_RX                   (13)                             //GPIO94
#define GPIO94_MODE_CLB_OUTXBAR3               (14)                             //GPIO94
#define GPIO94_MODE_SPI3_CS_n                  (15)                             //GPIO94

#define GPIO96_MODE_GPIO96                     (0)                              //GPIO96
#define GPIO96_MODE_SPI0_MOSI                  (1)                              //GPIO96
#define GPIO96_MODE_EMIF0_BA1                  (2)                              //GPIO96
#define GPIO96_MODE_SRPWM8_A                   (3)                              //GPIO96
#define GPIO96_MODE_QEP1_A                     (5)                              //GPIO96
#define GPIO96_MODE_SPI2_MOSI                  (6)                              //GPIO96
#define GPIO96_MODE_SDFM3_CLK4                 (7)                              //GPIO96
#define GPIO96_MODE_SDFM0_DATA1                (9)                              //GPIO96
#define GPIO96_MODE_EMIF0_D24                  (14)                             //GPIO96

#define GPIO102_MODE_GPIO102                   (0)                              //GPIO102
#define GPIO102_MODE_QEP0_A                    (1)                              //GPIO102
#define GPIO102_MODE_SRPWM8_B                  (2)                              //GPIO102
#define GPIO102_MODE_SPI0_MOSI                 (3)                              //GPIO102

#define GPIO103_MODE_GPIO103                   (0)                              //GPIO103
#define GPIO103_MODE_QEP0_STROBE               (1)                              //GPIO103
#define GPIO103_MODE_SRPWM16_A                 (2)                              //GPIO103
#define GPIO103_MODE_UART3_TX                  (3)                              //GPIO103
#define GPIO103_MODE_SRPWM11_A                 (5)                              //GPIO103
#define GPIO103_MODE_SPI1_CLK                  (6)                              //GPIO103
#define GPIO103_MODE_SDFM0_DATA4               (7)                              //GPIO103
#define GPIO103_MODE_CANFD1_TX                 (9)                              //GPIO103
#define GPIO103_MODE_EMIF0_RAS_n               (10)                             //GPIO103
#define GPIO103_MODE_SPI2_CLK                  (14)                             //GPIO103

#define GPIO104_MODE_GPIO104                   (0)                              //GPIO104
#define GPIO104_MODE_QEP0_INDEX                (1)                              //GPIO104
#define GPIO104_MODE_SRPWM16_B                 (2)                              //GPIO104
#define GPIO104_MODE_UART3_RX                  (3)                              //GPIO104
#define GPIO104_MODE_SRPWM11_B                 (5)                              //GPIO104
#define GPIO104_MODE_SPI1_CS_n                 (6)                              //GPIO104
#define GPIO104_MODE_SDFM0_CLK4                (7)                              //GPIO104
#define GPIO104_MODE_CANFD1_RX                 (9)                              //GPIO104
#define GPIO104_MODE_EMIF0_CAS_n               (10)                             //GPIO104
#define GPIO104_MODE_SPI2_CS_n                 (14)                             //GPIO104

#define GPIO105_MODE_GPIO105                   (0)                              //GPIO105
#define GPIO105_MODE_OUTXBAR0                  (1)                              //GPIO105
#define GPIO105_MODE_QEP1_A                    (2)                              //GPIO105
#define GPIO105_MODE_SRPWM17_A                 (3)                              //GPIO105
#define GPIO105_MODE_LIN1_TX                   (5)                              //GPIO105
#define GPIO105_MODE_SPI1_MOSI                 (6)                              //GPIO105
#define GPIO105_MODE_SDFM1_DATA1               (7)                              //GPIO105
#define GPIO105_MODE_PMBUS0_SCL                (9)                              //GPIO105
#define GPIO105_MODE_EMIF0_DQM0                (10)                             //GPIO105
#define GPIO105_MODE_UART5_TX                  (11)                             //GPIO105
#define GPIO105_MODE_SRPWM12_A                 (13)                             //GPIO105

#define GPIO106_MODE_GPIO106                   (0)                              //GPIO106
#define GPIO106_MODE_OUTXBAR1                  (1)                              //GPIO106
#define GPIO106_MODE_QEP1_B                    (2)                              //GPIO106
#define GPIO106_MODE_SRPWM17_B                 (3)                              //GPIO106
#define GPIO106_MODE_LIN1_RX                   (5)                              //GPIO106
#define GPIO106_MODE_SPI1_MISO                 (6)                              //GPIO106
#define GPIO106_MODE_SDFM1_CLK1                (7)                              //GPIO106
#define GPIO106_MODE_PMBUS0_SDA                (9)                              //GPIO106
#define GPIO106_MODE_EMIF0_DQM1                (10)                             //GPIO106
#define GPIO106_MODE_UART5_RX                  (11)                             //GPIO106
#define GPIO106_MODE_SRPWM12_B                 (13)                             //GPIO106

#define GPIO107_MODE_GPIO107                   (0)                              //GPIO107
#define GPIO107_MODE_OUTXBAR2                  (1)                              //GPIO107
#define GPIO107_MODE_QEP1_INDEX                (2)                              //GPIO107
#define GPIO107_MODE_SPI0_MISO                 (3)                              //GPIO107
#define GPIO107_MODE_OUTXBAR2_BK               (5)                              //GPIO107
#define GPIO107_MODE_SPI1_CLK                  (6)                              //GPIO107
#define GPIO107_MODE_SDFM2_DATA1               (7)                              //GPIO107
#define GPIO107_MODE_PMBUS0_ALERT_n            (9)                              //GPIO107
#define GPIO107_MODE_EMIF0_DQM2                (10)                             //GPIO107
#define GPIO107_MODE_SDFM1_DATA2               (11)                             //GPIO107
#define GPIO107_MODE_SRPWM13_A                 (13)                             //GPIO107
#define GPIO107_MODE_SRPWM7_B                  (15)                             //GPIO107

#define GPIO108_MODE_GPIO108                   (0)                              //GPIO108
#define GPIO108_MODE_OUTXBAR3                  (1)                              //GPIO108
#define GPIO108_MODE_QEP1_STROBE               (2)                              //GPIO108
#define GPIO108_MODE_SPI0_CLK                  (3)                              //GPIO108
#define GPIO108_MODE_OUTXBAR3_BK               (5)                              //GPIO108
#define GPIO108_MODE_SPI1_CS_n                 (6)                              //GPIO108
#define GPIO108_MODE_SDFM1_CLK2                (7)                              //GPIO108
#define GPIO108_MODE_PMBUS0_CTL_n              (9)                              //GPIO108
#define GPIO108_MODE_EMIF0_DQM3                (10)                             //GPIO108
#define GPIO108_MODE_SRPWM13_B                 (13)                             //GPIO108
#define GPIO108_MODE_SDFM0_DATA3               (15)                             //GPIO108

#define GPIO111_MODE_GPIO111                   (0)                              //GPIO111
#define GPIO111_MODE_QEP5_STROBE               (1)                              //GPIO111
#define GPIO111_MODE_SRPWM7_A                  (2)                              //GPIO111
#define GPIO111_MODE_SDFM3_DATA4               (6)                              //GPIO111
#define GPIO111_MODE_UART5_TX                  (9)                              //GPIO111
#define GPIO111_MODE_LIN1_TX                   (10)                             //GPIO111

#define GPIO112_MODE_GPIO112                   (0)                              //GPIO112
#define GPIO112_MODE_CANFD0_RX                 (1)                              //GPIO112
#define GPIO112_MODE_EMIF0_CLK                 (2)                              //GPIO112
#define GPIO112_MODE_CANFD1_RX                 (3)                              //GPIO112
#define GPIO112_MODE_OUTXBAR6                  (5)                              //GPIO112
#define GPIO112_MODE_QEP2_STROBE               (6)                              //GPIO112
#define GPIO112_MODE_SDFM1_DATA4               (7)                              //GPIO112
#define GPIO112_MODE_EMIF0_CS4_n               (9)                              //GPIO112
#define GPIO112_MODE_SRPWM15_A                 (13)                             //GPIO112
#define GPIO112_MODE_SPI3_MOSI                 (15)                             //GPIO112

#define GPIO113_MODE_GPIO113                   (0)                              //GPIO113
#define GPIO113_MODE_UART2_RX                  (1)                              //GPIO113
#define GPIO113_MODE_EMIF0_CS4_n               (2)                              //GPIO113
#define GPIO113_MODE_CANFD0_RX                 (3)                              //GPIO113
#define GPIO113_MODE_OUTXBAR4                  (5)                              //GPIO113
#define GPIO113_MODE_QEP2_A                    (6)                              //GPIO113
#define GPIO113_MODE_SDFM1_DATA3               (7)                              //GPIO113
#define GPIO113_MODE_EMIF0_CS2_n               (9)                              //GPIO113
#define GPIO113_MODE_I2C1_SDA                  (10)                             //GPIO113
#define GPIO113_MODE_SPI2_MISO                 (11)                             //GPIO113
#define GPIO113_MODE_SRPWM14_A                 (13)                             //GPIO113
#define GPIO113_MODE_LIN0_TX                   (14)                             //GPIO113
#define GPIO113_MODE_EMIF0_D12                 (15)                             //GPIO113

#define GPIO114_MODE_GPIO114                   (0)                              //GPIO114
#define GPIO114_MODE_UART2_TX                  (1)                              //GPIO114
#define GPIO114_MODE_EMIF0_SDCKE               (2)                              //GPIO114
#define GPIO114_MODE_SPI3_CLK                  (3)                              //GPIO114
#define GPIO114_MODE_OUTXBAR5                  (5)                              //GPIO114
#define GPIO114_MODE_QEP2_B                    (6)                              //GPIO114
#define GPIO114_MODE_SDFM1_CLK3                (7)                              //GPIO114
#define GPIO114_MODE_EMIF0_CS3_n               (9)                              //GPIO114
#define GPIO114_MODE_SRPWM14_B                 (13)                             //GPIO114
#define GPIO114_MODE_EMIF0_D13                 (15)                             //GPIO114

#define GPIO115_MODE_GPIO115                   (0)                              //GPIO115
#define GPIO115_MODE_CANFD0_TX                 (1)                              //GPIO115
#define GPIO115_MODE_EMIF0_WE_n                (2)                              //GPIO115
#define GPIO115_MODE_CANFD1_TX                 (3)                              //GPIO115
#define GPIO115_MODE_OUTXBAR7                  (5)                              //GPIO115
#define GPIO115_MODE_QEP2_INDEX                (6)                              //GPIO115
#define GPIO115_MODE_SDFM1_CLK4                (7)                              //GPIO115
#define GPIO115_MODE_EMIF0_RNW                 (9)                              //GPIO115
#define GPIO115_MODE_I2C0_SDA                  (10)                             //GPIO115
#define GPIO115_MODE_SPI3_CS_n                 (11)                             //GPIO115
#define GPIO115_MODE_SRPWM15_B                 (13)                             //GPIO115
#define GPIO115_MODE_LIN1_TX                   (14)                             //GPIO115
#define GPIO115_MODE_SPI3_MISO                 (15)                             //GPIO115

#define GPIO116_MODE_GPIO116                   (0)                              //GPIO116
#define GPIO116_MODE_I2C0_SDA                  (1)                              //GPIO116
#define GPIO116_MODE_EMIF0_CS0_n               (2)                              //GPIO116
#define GPIO116_MODE_SPI0_MOSI                 (3)                              //GPIO116
#define GPIO116_MODE_QEP3_A                    (5)                              //GPIO116
#define GPIO116_MODE_LIN1_TX                   (6)                              //GPIO116
#define GPIO116_MODE_CLB_OUTXBAR0              (7)                              //GPIO116
#define GPIO116_MODE_EMIF0_OE_n                (9)                              //GPIO116
#define GPIO116_MODE_I2C0_SCL                  (10)                             //GPIO116
#define GPIO116_MODE_UART5_TX                  (11)                             //GPIO116
#define GPIO116_MODE_SPI3_CLK                  (15)                             //GPIO116

#define GPIO117_MODE_GPIO117                   (0)                              //GPIO117
#define GPIO117_MODE_QEP5_INDEX                (1)                              //GPIO117
#define GPIO117_MODE_SRPWM7_B                  (2)                              //GPIO117
#define GPIO117_MODE_SDFM3_CLK4                (6)                              //GPIO117



#endif /* __ET6X_PINMAP_H__ */
