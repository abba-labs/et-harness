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

#ifndef __ET6X_ETIMER_H
#define __ET6X_ETIMER_H

#include "et6x.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup ETIMER
 * @{
 */

/* Exported constants --------------------------------------------------------*/

/** @defgroup ETIMER_Channel
 * @{
 */

#define ETIMER_CHANNEL_0      (0x0001UL)
#define ETIMER_CHANNEL_1      (0x0002UL)
#define ETIMER_CHANNEL_2      (0x0004UL)
#define ETIMER_CHANNEL_3      (0x0008UL)
#define ETIMER_CHANNEL_4      (0x0010UL)
#define ETIMER_CHANNEL_5      (0x0020UL)
#define ETIMER_CHANNEL_6      (0x0040UL)
#define ETIMER_CHANNEL_7      (0x0080UL)
#define ETIMER_CHANNEL_8      (0x0100UL)
#define ETIMER_CHANNEL_9      (0x0200UL)
#define ETIMER_CHANNEL_10     (0x0400UL)
#define ETIMER_CHANNEL_11     (0x0800UL)
#define ETIMER_CHANNEL_12     (0x1000UL)
#define ETIMER_CHANNEL_13     (0x2000UL)
#define ETIMER_CHANNEL_ALL    (0x3FFFUL)

#define ETIMER_CHANNEL_NUM    (14UL)

/**
 * @}
 */
/** @defgroup ETIMER_DB_ChannelGroup
 * @{
 */

#define ETIMER_CHANNEL_GROUP0    (0x0000UL)
#define ETIMER_CHANNEL_GROUP1    (0x0001UL)
#define ETIMER_CHANNEL_GROUP2    (0x0002UL)
#define ETIMER_CHANNEL_GROUP3    (0x0003UL)
#define ETIMER_CHANNEL_GROUP4    (0x0004UL)
#define ETIMER_CHANNEL_GROUP5    (0x0005UL)
#define ETIMER_CHANNEL_GROUP6    (0x0006UL)

/**
 * @}
 */
/** @defgroup ETIMER_DMA_Channel
 * @{
 */
typedef enum
{
    ETIMER_DMA_CHANNEL0 = 0x00U,
    ETIMER_DMA_CHANNEL1 = 0x01U,
    ETIMER_DMA_CHANNEL2 = 0x02U,
    ETIMER_DMA_CHANNEL3 = 0x03U
} ETIMER_DMAChannel;

/**
 * @}
 */

/** @defgroup ETIMER_Channel_For_DMA
 * @{
 */
typedef enum
{
    ETIMER_DMA_REQUEST_ETIMER0_CAP_EVT0  = 0x00U,
    ETIMER_DMA_REQUEST_ETIMER0_CAP_EVT1  = 0x01U,
    ETIMER_DMA_REQUEST_ETIMER0_CAP_EVT2  = 0x02U,
    ETIMER_DMA_REQUEST_ETIMER0_CAP_EVT3  = 0x03U,
    ETIMER_DMA_REQUEST_ETIMER1_CAP_EVT0  = 0x04U,
    ETIMER_DMA_REQUEST_ETIMER1_CAP_EVT1  = 0x05U,
    ETIMER_DMA_REQUEST_ETIMER1_CAP_EVT2  = 0x06U,
    ETIMER_DMA_REQUEST_ETIMER1_CAP_EVT3  = 0x07U,
    ETIMER_DMA_REQUEST_ETIMER2_CAP_EVT0  = 0x08U,
    ETIMER_DMA_REQUEST_ETIMER2_CAP_EVT1  = 0x09U,
    ETIMER_DMA_REQUEST_ETIMER2_CAP_EVT2  = 0x0AU,
    ETIMER_DMA_REQUEST_ETIMER2_CAP_EVT3  = 0x0BU,
    ETIMER_DMA_REQUEST_ETIMER3_CAP_EVT0  = 0x0CU,
    ETIMER_DMA_REQUEST_ETIMER3_CAP_EVT1  = 0x0DU,
    ETIMER_DMA_REQUEST_ETIMER3_CAP_EVT2  = 0x0EU,
    ETIMER_DMA_REQUEST_ETIMER3_CAP_EVT3  = 0x0FU,
    ETIMER_DMA_REQUEST_ETIMER4_CAP_EVT0  = 0x10U,
    ETIMER_DMA_REQUEST_ETIMER4_CAP_EVT1  = 0x11U,
    ETIMER_DMA_REQUEST_ETIMER4_CAP_EVT2  = 0x12U,
    ETIMER_DMA_REQUEST_ETIMER4_CAP_EVT3  = 0x13U,
    ETIMER_DMA_REQUEST_ETIMER5_CAP_EVT0  = 0x14U,
    ETIMER_DMA_REQUEST_ETIMER5_CAP_EVT1  = 0x15U,
    ETIMER_DMA_REQUEST_ETIMER5_CAP_EVT2  = 0x16U,
    ETIMER_DMA_REQUEST_ETIMER5_CAP_EVT3  = 0x17U,
    ETIMER_DMA_REQUEST_ETIMER6_CAP_EVT0  = 0x18U,
    ETIMER_DMA_REQUEST_ETIMER6_CAP_EVT1  = 0x19U,
    ETIMER_DMA_REQUEST_ETIMER6_CAP_EVT2  = 0x1AU,
    ETIMER_DMA_REQUEST_ETIMER6_CAP_EVT3  = 0x1BU,
    ETIMER_DMA_REQUEST_ETIMER7_CAP_EVT0  = 0x1CU,
    ETIMER_DMA_REQUEST_ETIMER7_CAP_EVT1  = 0x1DU,
    ETIMER_DMA_REQUEST_ETIMER7_CAP_EVT2  = 0x1EU,
    ETIMER_DMA_REQUEST_ETIMER7_CAP_EVT3  = 0x1FU,
    ETIMER_DMA_REQUEST_ETIMER8_CAP_EVT0  = 0x20U,
    ETIMER_DMA_REQUEST_ETIMER8_CAP_EVT1  = 0x21U,
    ETIMER_DMA_REQUEST_ETIMER8_CAP_EVT2  = 0x22U,
    ETIMER_DMA_REQUEST_ETIMER8_CAP_EVT3  = 0x23U,
    ETIMER_DMA_REQUEST_ETIMER9_CAP_EVT0  = 0x24U,
    ETIMER_DMA_REQUEST_ETIMER9_CAP_EVT1  = 0x25U,
    ETIMER_DMA_REQUEST_ETIMER9_CAP_EVT2  = 0x26U,
    ETIMER_DMA_REQUEST_ETIMER9_CAP_EVT3  = 0x27U,
    ETIMER_DMA_REQUEST_ETIMER10_CAP_EVT0 = 0x28U,
    ETIMER_DMA_REQUEST_ETIMER10_CAP_EVT1 = 0x29U,
    ETIMER_DMA_REQUEST_ETIMER10_CAP_EVT2 = 0x2AU,
    ETIMER_DMA_REQUEST_ETIMER10_CAP_EVT3 = 0x2BU,
    ETIMER_DMA_REQUEST_ETIMER11_CAP_EVT0 = 0x2CU,
    ETIMER_DMA_REQUEST_ETIMER11_CAP_EVT1 = 0x2DU,
    ETIMER_DMA_REQUEST_ETIMER11_CAP_EVT2 = 0x2EU,
    ETIMER_DMA_REQUEST_ETIMER11_CAP_EVT3 = 0x2FU,
    ETIMER_DMA_REQUEST_ETIMER12_CAP_EVT0 = 0x30U,
    ETIMER_DMA_REQUEST_ETIMER12_CAP_EVT1 = 0x31U,
    ETIMER_DMA_REQUEST_ETIMER12_CAP_EVT2 = 0x32U,
    ETIMER_DMA_REQUEST_ETIMER12_CAP_EVT3 = 0x33U,
    ETIMER_DMA_REQUEST_ETIMER13_CAP_EVT0 = 0x34U,
    ETIMER_DMA_REQUEST_ETIMER13_CAP_EVT1 = 0x35U,
    ETIMER_DMA_REQUEST_ETIMER13_CAP_EVT2 = 0x36U,
    ETIMER_DMA_REQUEST_ETIMER13_CAP_EVT3 = 0x37U
} ETIMER_DMARequest;

/**
 * @}
 */

/** @defgroup ETIMER_Clock_Division
 * @{
 */
typedef enum
{
    ETIMER_CLK_DIV1  = 0x00U, /* clock divides by 1 */
    ETIMER_CLK_DIV2  = 0x01U, /* clock divides by 2 */
    ETIMER_CLK_DIV4  = 0x03U, /* clock divides by 4 */
    ETIMER_CLK_DIV8  = 0x07U, /* clock divides by 8 */
    ETIMER_CLK_DIV16 = 0x0FU, /* clock divides by 16 */
    ETIMER_CLK_DIV32 = 0x1FU, /* clock divides by 32 */
    ETIMER_CLK_DIV64 = 0x3FU  /* clock divides by 64 */
} ETIMER_ClkDiv;

/**
 * @}
 */

/** @defgroup ETIMER_Output_Compare_Polarity
 * @{
 */
typedef enum
{
    ETIMER_OCPOLARITY_NORMAL = 0x00U, /* the output is normal polarity */
    ETIMER_OCPOLARITY_INVERT = 0x01U  /* invert the polarity of the output */
} ETIMER_OCPolarity;

/**
 * @}
 */

/** @defgroup ETIMER_Compare_Mode
 * @{
 */
typedef enum
{
    ETIMER_COMPAREMODE_COMPAREA        = 0x00U,  /* single comparison mode：only support compareA */
    ETIMER_COMPAREMODE_COMPARE_A_AND_B = 0x01U   /* dual comparison mode */
} ETIMER_CompareMode;

/**
 * @}
 */

/** @defgroup ETIMER_Cap_Clock_Division
 * @{
 */
typedef enum
{
    ETIMER_CAP_CLK_DIV1  = 0x00U,   /* clock divides by 1 */
    ETIMER_CAP_CLK_DIV2  = 0x01U,   /* clock divides by 2 */
    ETIMER_CAP_CLK_DIV4  = 0x02U,   /* clock divides by 4 */
    ETIMER_CAP_CLK_DIV6  = 0x03U,   /* clock divides by 6 */
    ETIMER_CAP_CLK_DIV8  = 0x04U,   /* clock divides by 8 */
    ETIMER_CAP_CLK_DIV10 = 0x05U,   /* clock divides by 10 */
    ETIMER_CAP_CLK_DIV12 = 0x06U,   /* clock divides by 12 */
    ETIMER_CAP_CLK_DIV14 = 0x07U,   /* clock divides by 14 */
    ETIMER_CAP_CLK_DIV16 = 0x08U,   /* clock divides by 16 */
    ETIMER_CAP_CLK_DIV18 = 0x09U,   /* clock divides by 18 */
    ETIMER_CAP_CLK_DIV20 = 0x0AU,   /* clock divides by 20 */
    ETIMER_CAP_CLK_DIV22 = 0x0BU,   /* clock divides by 22 */
    ETIMER_CAP_CLK_DIV24 = 0x0CU,   /* clock divides by 24 */
    ETIMER_CAP_CLK_DIV26 = 0x0DU,   /* clock divides by 26 */
    ETIMER_CAP_CLK_DIV28 = 0x0EU,   /* clock divides by 28 */
    ETIMER_CAP_CLK_DIV30 = 0x0FU,   /* clock divides by 30 */
    ETIMER_CAP_CLK_DIV32 = 0x10U,   /* clock divides by 32 */
    ETIMER_CAP_CLK_DIV34 = 0x11U,   /* clock divides by 34 */
    ETIMER_CAP_CLK_DIV36 = 0x12U,   /* clock divides by 36 */
    ETIMER_CAP_CLK_DIV38 = 0x13U,   /* clock divides by 38 */
    ETIMER_CAP_CLK_DIV40 = 0x14U,   /* clock divides by 40 */
    ETIMER_CAP_CLK_DIV42 = 0x15U,   /* clock divides by 42 */
    ETIMER_CAP_CLK_DIV44 = 0x16U,   /* clock divides by 44 */
    ETIMER_CAP_CLK_DIV46 = 0x17U,   /* clock divides by 46 */
    ETIMER_CAP_CLK_DIV48 = 0x18U,   /* clock divides by 48 */
    ETIMER_CAP_CLK_DIV50 = 0x19U,   /* clock divides by 50 */
    ETIMER_CAP_CLK_DIV52 = 0x1AU,   /* clock divides by 52 */
    ETIMER_CAP_CLK_DIV54 = 0x1BU,   /* clock divides by 54 */
    ETIMER_CAP_CLK_DIV56 = 0x1CU,   /* clock divides by 56 */
    ETIMER_CAP_CLK_DIV58 = 0x1DU,   /* clock divides by 58 */
    ETIMER_CAP_CLK_DIV60 = 0x1EU,   /* clock divides by 60 */
    ETIMER_CAP_CLK_DIV62 = 0x1FU    /* clock divides by 62 */
} ETIMER_CapClkDiv;

/**
 * @}
 */

/** @defgroup ETIMER_Input_Capture_Blanking_Trigger
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_BLANKING_TRIGGER_SW    = 0x00U,   /* software events as a capture blanking trigger source */
    ETIMER_CAPTURE_BLANKING_TRIGGER_PIT   = 0x01U,   /* PITIMER as a capture blanking trigger source */
    ETIMER_CAPTURE_BLANKING_TRIGGER_SRPWM = 0x02U    /* SRPWM as a capture blanking trigger source */
} ETIMER_CaptureBlankingTrigger;

/**
 * @}
 */

/** @defgroup ETIMER_Input_Capture_Input_Source
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_INPUT_SRC_INXB0                                    = 0x00U,   /* GPIO as a capture input source */
    ETIMER_CAPTURE_INPUT_SRC_INXB1                                    = 0x01U,   /* ACMP as a capture input source */
    ETIMER_CAPTURE_INPUT_SRC_INXB2                                    = 0x02U,   /* XBAR as a capture input source*/
    ETIMER_CAPTURE_INPUT_SRC_INXB3                                    = 0x03U,
    ETIMER_CAPTURE_INPUT_SRC_INXB4                                    = 0x04U,
    ETIMER_CAPTURE_INPUT_SRC_INXB5                                    = 0x05U,
    ETIMER_CAPTURE_INPUT_SRC_INXB6                                    = 0x06U,
    ETIMER_CAPTURE_INPUT_SRC_INXB7                                    = 0x07U,
    ETIMER_CAPTURE_INPUT_SRC_INXB8                                    = 0x08U,
    ETIMER_CAPTURE_INPUT_SRC_INXB9                                    = 0x09U,
    ETIMER_CAPTURE_INPUT_SRC_INXB10                                   = 0x0AU,
    ETIMER_CAPTURE_INPUT_SRC_INXB11                                   = 0x0BU,
    ETIMER_CAPTURE_INPUT_SRC_INXB12                                   = 0x0CU,
    ETIMER_CAPTURE_INPUT_SRC_INXB13                                   = 0x0DU,
    ETIMER_CAPTURE_INPUT_SRC_INXB14                                   = 0x0EU,
    ETIMER_CAPTURE_INPUT_SRC_INXB15                                   = 0x0FU,
    ETIMER_CAPTURE_INPUT_SRC_OPXB0                                    = 0x10U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB1                                    = 0x11U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB2                                    = 0x12U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB3                                    = 0x13U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB4                                    = 0x14U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB5                                    = 0x15U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB6                                    = 0x16U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB7                                    = 0x17U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB8                                    = 0x18U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB9                                    = 0x19U,
    ETIMER_CAPTURE_INPUT_SRC_OPXB10                                   = 0x1AU,
    ETIMER_CAPTURE_INPUT_SRC_OPXB11                                   = 0x1BU,
    ETIMER_CAPTURE_INPUT_SRC_CLU0                                     = 0x1CU,
    ETIMER_CAPTURE_INPUT_SRC_CLU1                                     = 0x1DU,
    ETIMER_CAPTURE_INPUT_SRC_CLU2                                     = 0x1EU,
    ETIMER_CAPTURE_INPUT_SRC_CLU3                                     = 0x1FU,
    ETIMER_CAPTURE_INPUT_SRC_UART0_RX                                 = 0x20U,
    ETIMER_CAPTURE_INPUT_SRC_UART1_RX                                 = 0x21U,
    ETIMER_CAPTURE_INPUT_SRC_UART2_RX                                 = 0x22U,
    ETIMER_CAPTURE_INPUT_SRC_UART3_RX                                 = 0x23U,
    ETIMER_CAPTURE_INPUT_SRC_UART4_RX                                 = 0x24U,
    ETIMER_CAPTURE_INPUT_SRC_UART5_RX                                 = 0x25U,
    ETIMER_CAPTURE_INPUT_SRC_UART6_RX                                 = 0x26U,
    ETIMER_CAPTURE_INPUT_SRC_UART7_RX                                 = 0x27U,
    ETIMER_CAPTURE_INPUT_SRC_LIN0_RX                                  = 0x28U,
    ETIMER_CAPTURE_INPUT_SRC_LIN1_RX                                  = 0x29U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM0_A                                 = 0x2AU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM1_A                                 = 0x2BU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM2_A                                 = 0x2CU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM3_A                                 = 0x2DU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM4_A                                 = 0x2EU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM5_A                                 = 0x2FU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM6_A                                 = 0x30U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM7_A                                 = 0x31U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM8_A                                 = 0x32U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM9_A                                 = 0x33U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM10_A                                = 0x34U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM11_A                                = 0x35U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM12_A                                = 0x36U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM13_A                                = 0x37U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM14_A                                = 0x38U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM15_A                                = 0x39U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM16_A                                = 0x3AU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM17_A                                = 0x3BU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM0_B                                 = 0x3CU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM1_B                                 = 0x3DU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM2_B                                 = 0x3EU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM3_B                                 = 0x3FU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM4_B                                 = 0x40U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM5_B                                 = 0x41U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM6_B                                 = 0x42U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM7_B                                 = 0x43U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM8_B                                 = 0x44U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM9_B                                 = 0x45U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM10_B                                = 0x46U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM11_B                                = 0x47U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM12_B                                = 0x48U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM13_B                                = 0x49U,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM14_B                                = 0x4AU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM15_B                                = 0x4BU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM16_B                                = 0x4CU,
    ETIMER_CAPTURE_INPUT_SRC_SRPWM17_B                                = 0x4DU,
    ETIMER_CAPTURE_INPUT_SRC_ETIM0_PWM                                = 0x4EU,
    ETIMER_CAPTURE_INPUT_SRC_ETIM1_PWM                                = 0x4FU,
    ETIMER_CAPTURE_INPUT_SRC_ETIM2_PWM                                = 0x50U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM3_PWM                                = 0x51U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM4_PWM                                = 0x52U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM5_PWM                                = 0x53U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM6_PWM                                = 0x54U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM7_PWM                                = 0x55U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM8_PWM                                = 0x56U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM9_PWM                                = 0x57U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM10_PWM                               = 0x58U,
    ETIMER_CAPTURE_INPUT_SRC_ETIM11_PWM                               = 0x59U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP0_H                                  = 0x5AU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP1_H                                  = 0x5BU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP2_H                                  = 0x5CU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP3_H                                  = 0x5DU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP4_H                                  = 0x5EU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP5_H                                  = 0x5FU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP6_H                                  = 0x60U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP7_H                                  = 0x61U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP8_H                                  = 0x62U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP9_H                                  = 0x63U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP10_H                                 = 0x64U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP0_L                                  = 0x65U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP1_L                                  = 0x66U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP2_L                                  = 0x67U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP3_L                                  = 0x68U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP4_L                                  = 0x69U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP5_L                                  = 0x6AU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP6_L                                  = 0x6BU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP7_L                                  = 0x6CU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP8_L                                  = 0x6DU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP9_L                                  = 0x6EU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP10_L                                 = 0x6FU,
    ETIMER_CAPTURE_INPUT_SRC_ACMP0_H_OR_L                             = 0x70U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP1_H_OR_L                             = 0x71U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP2_H_OR_L                             = 0x72U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP3_H_OR_L                             = 0x73U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP4_H_OR_L                             = 0x74U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP5_H_OR_L                             = 0x75U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP6_H_OR_L                             = 0x76U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP7_H_OR_L                             = 0x77U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP8_H_OR_L                             = 0x78U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP9_H_OR_L                             = 0x79U,
    ETIMER_CAPTURE_INPUT_SRC_ACMP10_H_OR_L                            = 0x7AU,
    ETIMER_CAPTURE_INPUT_SRC_ADC0_CAP_EVT0                            = 0x7BU,
    ETIMER_CAPTURE_INPUT_SRC_ADC0_CAP_EVT1                            = 0x7CU,
    ETIMER_CAPTURE_INPUT_SRC_ADC0_CAP_EVT2                            = 0x7DU,
    ETIMER_CAPTURE_INPUT_SRC_ADC0_CAP_EVT3                            = 0x7EU,
    ETIMER_CAPTURE_INPUT_SRC_ADC1_CAP_EVT0                            = 0x7FU,
    ETIMER_CAPTURE_INPUT_SRC_ADC1_CAP_EVT1                            = 0x80U,
    ETIMER_CAPTURE_INPUT_SRC_ADC1_CAP_EVT2                            = 0x81U,
    ETIMER_CAPTURE_INPUT_SRC_ADC1_CAP_EVT3                            = 0x82U,
    ETIMER_CAPTURE_INPUT_SRC_ADC2_CAP_EVT0                            = 0x83U,
    ETIMER_CAPTURE_INPUT_SRC_ADC2_CAP_EVT1                            = 0x84U,
    ETIMER_CAPTURE_INPUT_SRC_ADC2_CAP_EVT2                            = 0x85U,
    ETIMER_CAPTURE_INPUT_SRC_ADC2_CAP_EVT3                            = 0x86U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL0_CAP_EVT0                       = 0x87U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL1_CAP_EVT0                       = 0x88U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL2_CAP_EVT0                       = 0x89U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL3_CAP_EVT0                       = 0x8AU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL0_CAP_EVT1                       = 0x8BU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL1_CAP_EVT1                       = 0x8CU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL2_CAP_EVT1                       = 0x8DU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL3_CAP_EVT1                       = 0x8EU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL0_COMPZ                          = 0x8FU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL1_COMPZ                          = 0x90U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL2_COMPZ                          = 0x91U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL3_COMPZ                          = 0x92U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL0_CAP_EVT0                       = 0x93U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL1_CAP_EVT0                       = 0x94U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL2_CAP_EVT0                       = 0x95U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL3_CAP_EVT0                       = 0x96U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL0_CAP_EVT1                       = 0x97U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL1_CAP_EVT1                       = 0x98U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL2_CAP_EVT1                       = 0x99U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL3_CAP_EVT1                       = 0x9AU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL0_COMPZ                          = 0x9BU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL1_COMPZ                          = 0x9CU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL2_COMPZ                          = 0x9DU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL3_COMPZ                          = 0x9EU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL0_CAP_EVT0                       = 0x9FU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL1_CAP_EVT0                       = 0xA0U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL2_CAP_EVT0                       = 0xA1U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL3_CAP_EVT0                       = 0xA2U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL0_CAP_EVT1                       = 0xA3U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL1_CAP_EVT1                       = 0xA4U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL2_CAP_EVT1                       = 0xA5U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL3_CAP_EVT1                       = 0xA6U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL0_COMPZ                          = 0xA7U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL1_COMPZ                          = 0xA8U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL2_COMPZ                          = 0xA9U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL3_COMPZ                          = 0xAAU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL0_CAP_EVT0                       = 0xABU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL1_CAP_EVT0                       = 0xACU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL2_CAP_EVT0                       = 0xADU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL3_CAP_EVT0                       = 0xAEU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL0_CAP_EVT1                       = 0xAFU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL1_CAP_EVT1                       = 0xB0U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL2_CAP_EVT1                       = 0xB1U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL3_CAP_EVT1                       = 0xB2U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL0_COMPZ                          = 0xB3U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL1_COMPZ                          = 0xB4U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL2_COMPZ                          = 0xB5U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL3_COMPZ                          = 0xB6U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL0_CAP_EVT0_OR_SDFM0_FL0_CAP_EVT1 = 0xB7U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL1_CAP_EVT0_OR_SDFM0_FL1_CAP_EVT1 = 0xB8U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL2_CAP_EVT0_OR_SDFM0_FL2_CAP_EVT1 = 0xB9U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM0_FL3_CAP_EVT0_OR_SDFM0_FL3_CAP_EVT1 = 0xBAU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL0_CAP_EVT0_OR_SDFM1_FL0_CAP_EVT1 = 0xBBU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL1_CAP_EVT0_OR_SDFM1_FL1_CAP_EVT1 = 0xBCU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL2_CAP_EVT0_OR_SDFM1_FL2_CAP_EVT1 = 0xBDU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM1_FL3_CAP_EVT0_OR_SDFM1_FL3_CAP_EVT1 = 0xBEU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL0_CAP_EVT0_OR_SDFM2_FL0_CAP_EVT1 = 0xBFU,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL1_CAP_EVT0_OR_SDFM2_FL1_CAP_EVT1 = 0xC0U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL2_CAP_EVT0_OR_SDFM2_FL2_CAP_EVT1 = 0xC1U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM2_FL3_CAP_EVT0_OR_SDFM2_FL3_CAP_EVT1 = 0xC2U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL0_CAP_EVT0_OR_SDFM3_FL0_CAP_EVT1 = 0xC3U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL1_CAP_EVT0_OR_SDFM3_FL1_CAP_EVT1 = 0xC4U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL2_CAP_EVT0_OR_SDFM3_FL2_CAP_EVT1 = 0xC5U,
    ETIMER_CAPTURE_INPUT_SRC_SDFM3_FL3_CAP_EVT0_OR_SDFM3_FL3_CAP_EVT1 = 0xC6U,
    ETIMER_CAPTURE_INPUT_SRC_CLB0_OUT14                               = 0xC7U,
    ETIMER_CAPTURE_INPUT_SRC_CLB1_OUT14                               = 0xC8U,
    ETIMER_CAPTURE_INPUT_SRC_CLB2_OUT14                               = 0xC9U,
    ETIMER_CAPTURE_INPUT_SRC_CLB3_OUT14                               = 0xCAU,
    ETIMER_CAPTURE_INPUT_SRC_CLB4_OUT14                               = 0xCBU,
    ETIMER_CAPTURE_INPUT_SRC_CLB5_OUT14                               = 0xCCU,
    ETIMER_CAPTURE_INPUT_SRC_CLB0_OUT15                               = 0xCDU,
    ETIMER_CAPTURE_INPUT_SRC_CLB1_OUT15                               = 0xCEU,
    ETIMER_CAPTURE_INPUT_SRC_CLB2_OUT15                               = 0xCFU,
    ETIMER_CAPTURE_INPUT_SRC_CLB3_OUT15                               = 0xD0U,
    ETIMER_CAPTURE_INPUT_SRC_CLB4_OUT15                               = 0xD1U,
    ETIMER_CAPTURE_INPUT_SRC_CLB5_OUT15                               = 0xD2U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_0                              = 0xD3U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_1                              = 0xD4U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_2                              = 0xD5U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_3                              = 0xD6U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_4                              = 0xD7U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_5                              = 0xD8U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_6                              = 0xD9U,
    ETIMER_CAPTURE_INPUT_SRC_GPIO_ETIM_7                              = 0xDAU
} ETIMER_CaptureInputSrc;

/**
 * @}
 */

/** @defgroup ETIMER_Input_Capture_Edge
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_EDGE_RISING  = 0x00U,    /* the rising edge of the gpio acts as the trigger edge */
    ETIMER_CAPTURE_EDGE_FALLING = 0x01U     /* the falling edge of the gpio acts as the trigger edge */
} ETIMER_CaptureEdge;

/**
 * @}
 */
/** @defgroup ETIMER_Input_Capture_Time_Stamp_Mode
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_TIMESTAMP_MODE_ABSOLUTE = 0x00U,
    ETIMER_CAPTURE_TIMESTAMP_MODE_RELATIVE = 0x01U
} ETIMER_CaptureTimeStampMode;

/**
 * @}
 */


/** @defgroup ETIMER_Input_Capture_Mode
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_MODE_EVT0_CONTINUOUS = 0U,
    ETIMER_CAPTURE_MODE_EVT1_CONTINUOUS = 4U,
    ETIMER_CAPTURE_MODE_EVT2_CONTINUOUS = 8U,
    ETIMER_CAPTURE_MODE_EVT3_CONTINUOUS = 12U,
    ETIMER_CAPTURE_MODE_EVT0_ONE_SHOT   = 2U,
    ETIMER_CAPTURE_MODE_EVT1_ONE_SHOT   = 6U,
    ETIMER_CAPTURE_MODE_EVT2_ONE_SHOT   = 10U,
    ETIMER_CAPTURE_MODE_EVT3_ONE_SHOT   = 14U
} ETIMER_CaptureMode;

/**
 * @}
 */
/** @defgroup ETIMER_Input_Capture_Type
 * @{
 */
typedef enum
{
    ETIMER_CAPTURE_MODE_PERIOD         = 0x00U,   /* period as the capture type */
    ETIMER_CAPTURE_MODE_POSITIVE_PULSE = 0x01U,   /* positive pulse width as the capture type */
    ETIMER_CAPTURE_MODE_NEGATIVE_PULSE = 0x02U,   /* negative pulse width as the capture type */
    ETIMER_CAPTURE_MODE_RISING_EDGE    = 0x03U,   /* rising edge as the capture type */
    ETIMER_CAPTURE_MODE_FALLING_EDGE   = 0x04U    /* falling edge as the capture type */
} ETIMER_CaptureType;

/**
 * @}
 */

/** @defgroup ETIMER_Interrupt_Sources
 * @{
 */

#define ETIMER_INT_PWM_FAULT_ONE_SHOT    ((uint32_t)1 << 0)
#define ETIMER_INT_PWM_FAULT_CBC         ((uint32_t)1 << 1)
#define ETIMER_INT_FAULT_OVERFLOW        ((uint32_t)1 << 2)
#define ETIMER_INT_COMPAB_CFG_ERR        ((uint32_t)1 << 3)
#define ETIMER_INT_COMPA                 ((uint32_t)1 << 4)
#define ETIMER_INT_COMPB                 ((uint32_t)1 << 5)
#define ETIMER_INT_PERIOD                ((uint32_t)1 << 6)
#define ETIMER_INT_COUNTER_OVERFLOW      ((uint32_t)1 << 7)
#define ETIMER_INT_CAP_EVT0              ((uint32_t)1 << 8)
#define ETIMER_INT_CAP_EVT1              ((uint32_t)1 << 9)
#define ETIMER_INT_CAP_EVT2              ((uint32_t)1 << 10)
#define ETIMER_INT_CAP_EVT3              ((uint32_t)1 << 11)

/**
 * @}
 */

/** @defgroup ETIMER_Fault_Out_Polarity
 * @{
 */
typedef enum
{
    ETIMER_FAULT_OUT_POLARITY_LOW  = 0x00U,   /* fault output low */
    ETIMER_FAULT_OUT_POLARITY_HIGH = 0x01U    /* fault output high*/
} ETIMER_FaultOutPolarity;

/**
 * @}
 */

/** @defgroup ETIMER_Fault_Mode
 * @{
 */
typedef enum
{
    ETIMER_FAULT_MODE_CBC = 0x00U,   /* the exception pattern is cycle by cycle */
    ETIMER_FAULT_MODE_OS  = 0x01U    /* the exception pattern is one shot  */
} ETIMER_FaultMode;

/**
 * @}
 */

/** @defgroup ETIMER_Fault_Trigger
 * @{
 */
typedef enum
{
    ETIMER_FAULT_TRIGGER_SW   = 0x00U,   /* software as a trigger for an abnormal pattern */
    ETIMER_FAULT_TRIGGER_XBAR = 0x01U    /* xbar as a trigger for an abnormal pattern */
} ETIMER_FaultTrigger;

/**
 * @}
 */

/** @defgroup ETIMER_SyncOutEvent
 * @{
 */
typedef enum
{
    ETIMER_SYNCOUT_EVENT_SW       = 0x00U,   /* the software signal acts as a synchronization source for the output */
    ETIMER_SYNCOUT_EVENT_PERIOD   = 0x01U,   /* etimer's periodic events are used as a synchronization source for the
                                              * output */
    ETIMER_SYNCOUT_EVENT_DISABLED = 0x02U
} ETIMER_SyncOutEvent;

/**
 * @}
 */

/** @defgroup ETIMER_ADC_DAC_ACMP_SyncOutEvent
 * @{
 */
typedef enum
{
    ETIMER_ADC_DAC_ACMP_SYNCOUT_EVENT_PERIOD      = 0x00U,
    ETIMER_ADC_DAC_ACMP_SYNCOUT_EVENT_ZERO        = 0x01U,
    ETIMER_ADC_DAC_ACMP_SYNCOUT_EVENT_CMPA        = 0x02U,
    ETIMER_ADC_DAC_ACMP_SYNCOUT_EVENT_CMPB        = 0x03U,
    ETIMER_ADC_DAC_ACMP_SYNCOUT_EVENT_COUNTER_EVT = 0x04U
} ETIMER_ADC_DAC_ACMP_SyncOutEvent;

/**
 * @}
 */

/** @defgroup ETIMER_DAC_ACMP_SyncOutSrc
 * @{
 */
typedef enum
{
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER0  = 0x00U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER1  = 0x01U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER2  = 0x02U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER3  = 0x03U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER4  = 0x04U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER5  = 0x05U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER6  = 0x06U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER7  = 0x07U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER8  = 0x08U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER9  = 0x09U,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER10 = 0x0AU,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER11 = 0x0BU,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER12 = 0x0CU,
    ETIMER_DAC_ACMP_SYNCOUT_SRC_ETIMER13 = 0x0DU
} ETIMER_DAC_ACMP_SyncOutSrc;

/**
 * @}
 */

/** @defgroup ETIMER_DACx
 * @{
 */
typedef enum
{
    ETIMER_DAC0 = 0x00U,
    ETIMER_DAC1 = 0x01U
} ETIMER_DACx;

/**
 * @}
 */

/** @defgroup ETIMER_ACMPx
 * @{
 */
typedef enum
{
    ETIMER_ACMP0_A = 0x00U,
    ETIMER_ACMP0_B = 0x01U,
    ETIMER_ACMP1_A = 0x02U,
    ETIMER_ACMP1_B = 0x03U,
    ETIMER_ACMP2_A = 0x04U,
    ETIMER_ACMP2_B = 0x05U,
    ETIMER_ACMP3_A = 0x06U,
    ETIMER_ACMP3_B = 0x07U
} ETIMER_ACMPx;

/**
 * @}
 */

/** @defgroup ETIMER_SyncOutSrc
 * @{
 */
typedef enum
{
    ETIMER_SYNCOUT_SRC_SRPWM0   = 0x00U,
    ETIMER_SYNCOUT_SRC_SRPWM1   = 0x01U,
    ETIMER_SYNCOUT_SRC_SRPWM2   = 0x02U,
    ETIMER_SYNCOUT_SRC_SRPWM3   = 0x03U,
    ETIMER_SYNCOUT_SRC_SRPWM4   = 0x04U,
    ETIMER_SYNCOUT_SRC_SRPWM5   = 0x05U,
    ETIMER_SYNCOUT_SRC_SRPWM6   = 0x06U,
    ETIMER_SYNCOUT_SRC_SRPWM7   = 0x07U,
    ETIMER_SYNCOUT_SRC_SRPWM8   = 0x08U,
    ETIMER_SYNCOUT_SRC_SRPWM9   = 0x09U,
    ETIMER_SYNCOUT_SRC_SRPWM10  = 0x0AU,
    ETIMER_SYNCOUT_SRC_SRPWM11  = 0x0BU,
    ETIMER_SYNCOUT_SRC_ETIMER0  = 0x0CU,
    ETIMER_SYNCOUT_SRC_ETIMER1  = 0x0DU,
    ETIMER_SYNCOUT_SRC_ETIMER2  = 0x0EU,
    ETIMER_SYNCOUT_SRC_ETIMER3  = 0x0FU,
    ETIMER_SYNCOUT_SRC_ETIMER4  = 0x10U,
    ETIMER_SYNCOUT_SRC_ETIMER5  = 0x11U,
    ETIMER_SYNCOUT_SRC_ETIMER6  = 0x12U,
    ETIMER_SYNCOUT_SRC_ETIMER7  = 0x13U,
    ETIMER_SYNCOUT_SRC_ETIMER8  = 0x14U,
    ETIMER_SYNCOUT_SRC_ETIMER9  = 0x15U,
    ETIMER_SYNCOUT_SRC_ETIMER10 = 0x16U,
    ETIMER_SYNCOUT_SRC_ETIMER11 = 0x17U,
    ETIMER_SYNCOUT_SRC_ETIMER12 = 0x18U,
    ETIMER_SYNCOUT_SRC_ETIMER13 = 0x19U
} ETIMER_SyncOutSrc;

/**
 * @}
 */

/** @defgroup ETIMER_SyncIn
 * @{
 */
typedef enum
{
    ETIMER_SYNCIN_SRPMW0   = 0x00U,
    ETIMER_SYNCIN_SRPMW1   = 0x01U,
    ETIMER_SYNCIN_SRPMW2   = 0x02U,
    ETIMER_SYNCIN_SRPMW3   = 0x03U,
    ETIMER_SYNCIN_SRPMW4   = 0x04U,
    ETIMER_SYNCIN_SRPMW5   = 0x05U,
    ETIMER_SYNCIN_SRPMW6   = 0x06U,
    ETIMER_SYNCIN_SRPMW7   = 0x07U,
    ETIMER_SYNCIN_SRPMW8   = 0x08U,
    ETIMER_SYNCIN_SRPMW9   = 0x09U,
    ETIMER_SYNCIN_SRPMW10  = 0x0AU,
    ETIMER_SYNCIN_SRPMW11  = 0x0BU,
    ETIMER_SYNCIN_SRPMW12  = 0x0CU,
    ETIMER_SYNCIN_SRPMW13  = 0x0DU,
    ETIMER_SYNCIN_SRPMW14  = 0x0EU,
    ETIMER_SYNCIN_SRPMW15  = 0x0FU,
    ETIMER_SYNCIN_SRPMW16  = 0x10U,
    ETIMER_SYNCIN_SRPMW17  = 0x11U,
    ETIMER_SYNCIN_INXB0    = 0x12U,
    ETIMER_SYNCIN_INXB1    = 0x13U,
    ETIMER_SYNCIN_INXB2    = 0x14U,
    ETIMER_SYNCIN_INXB3    = 0x15U,
    ETIMER_SYNCIN_INXB4    = 0x16U,
    ETIMER_SYNCIN_INXB5    = 0x17U,
    ETIMER_SYNCIN_ETIMER0  = 0x18U,
    ETIMER_SYNCIN_ETIMER1  = 0x19U,
    ETIMER_SYNCIN_ETIMER2  = 0x1AU,
    ETIMER_SYNCIN_ETIMER3  = 0x1BU,
    ETIMER_SYNCIN_ETIMER4  = 0x1CU,
    ETIMER_SYNCIN_ETIMER5  = 0x1DU,
    ETIMER_SYNCIN_ETIMER6  = 0x1EU,
    ETIMER_SYNCIN_ETIMER7  = 0x1FU,
    ETIMER_SYNCIN_ETIMER8  = 0x20U,
    ETIMER_SYNCIN_ETIMER9  = 0x21U,
    ETIMER_SYNCIN_ETIMER10 = 0x22U,
    ETIMER_SYNCIN_ETIMER11 = 0x23U
} ETIMER_SyncIn;

/**
 * @}
 */

/** @defgroup ETIMER_DBOutputState
 * @{
 */
typedef enum
{
    ETIMER_DB_OUTPUT_STATE_NONE              = 0x00U,
    ETIMER_DB_OUTPUT_STATE_POS_OR_NEG_AFTER  = 0x01U,
    ETIMER_DB_OUTPUT_STATE_POS_OR_NEG_INVERT = 0x02U
} ETIMER_DBOutputState;

/**
 * @}
 */

#define ETIMER_IT_PWM_FAULT_ONE_SHOT    BIT_MASK(0)
#define ETIMER_IT_PWM_FAULT_CBC         BIT_MASK(1)
#define ETIMER_IT_FAULT_OVERFLOW        BIT_MASK(2)
#define ETIMER_IT_COMPAB_CFG_ERR        BIT_MASK(3)
#define ETIMER_IT_COMPA                 BIT_MASK(4)
#define ETIMER_IT_COMPB                 BIT_MASK(5)
#define ETIMER_IT_PERIOD                BIT_MASK(6)
#define ETIMER_IT_COUNTER_OVERFLOW      BIT_MASK(7)
#define ETIMER_IT_CAP_EVT0              BIT_MASK(8)
#define ETIMER_IT_CAP_EVT1              BIT_MASK(9)
#define ETIMER_IT_CAP_EVT2              BIT_MASK(10)
#define ETIMER_IT_CAP_EVT3              BIT_MASK(11)

/* Exported types ------------------------------------------------------------*/

/**
 * @brief ETIMER Time Base Init structure definition
 *
 */
typedef struct __PACKED
{
    uint32_t        channelMask;        /*!< specifies the etimer channel that needs to be initialized.
                                         *  this parameter can set multiple channels at the same time.
                                         *  This parameter can be a value of @ref ETIMER_Channel  */
    ETIMER_ClkDiv   prescaler;          /*!< Specifies the prescaler value used to divide the ETIMER clock.
                                         *  This parameter can be a value of @ref ETIMER_Clock_Division */
    uint32_t        period;             /*!< Specifies the period value to be loaded into the active
                                         *  Auto-Reload Register at the next update event.
                                         *  This parameter must be a number between 0x00000000 and 0xFFFFFFFF. */
    FunctionalState periodShadowEn;     /* whether to enable the shadow loading function for the period value the
                                         * default shadow loading time is the period value update*/

    uint32_t        phase;
} ETIMER_TimeBaseInitParam;
typedef struct __PACKED
{
    uint32_t           channelMask;     /*!< specifies the etimer channel that needs to be initialized.
                                         * this parameter can set multiple channels at the same time.
                                         * This parameter can be a value of @ref ETIMER_Channel  */
    uint32_t           compareA;        /*!< specifies the value of the comparison value A
                                         * This parameter must be a number between 0x00000000 and 0xFFFFFFFF  */
    uint32_t           compareB;        /*!< specifies the value of the comparison value B
                                         * This parameter must be a number between 0x00000000 and 0xFFFFFFFF  */
    FunctionalState    compareShadowEn;

    ETIMER_CompareMode compareMode;     /*!< specifies the mode of comparison
                                         * This parameter can be a value of @ref ETIMER_Compare_Mode*/
} ETIMER_OCInitParam;

typedef struct __PACKED
{
    uint16_t             risingDelay;
    uint16_t             fallingDelay;
    FunctionalState      selComplementChannel;
    FunctionalState      selRisingDelay;
    FunctionalState      selFallingDelay;
    ETIMER_DBOutputState selOutputState;
} ETIMER_AB_DBInitParam;

typedef struct __PACKED
{
    ETIMER_AB_DBInitParam a;
    ETIMER_AB_DBInitParam b;
} ETIMER_DBInitParam;
typedef struct __PACKED
{
    uint32_t                    channelMask;
    ETIMER_CapClkDiv            capPrescaler;
    ETIMER_CaptureInputSrc      capInputSrcSel;

    ETIMER_CaptureEdge          cap0EdgeSel;
    ETIMER_CaptureTimeStampMode cap0TimeStampMode;
    ETIMER_CaptureEdge          cap1EdgeSel;
    ETIMER_CaptureTimeStampMode cap1TimeStampMode;
    ETIMER_CaptureEdge          cap2EdgeSel;
    ETIMER_CaptureTimeStampMode cap2TimeStampMode;
    ETIMER_CaptureEdge          cap3EdgeSel;
    ETIMER_CaptureTimeStampMode cap3TimeStampMode;

    FunctionalState             capLoadEn;
    ETIMER_CaptureMode          capMode;     /* choose the capture mode whether to stop(one-shot) or wrap(continuous)
                                              * from the Event x after it occurred */

    /* filtering configuration */
    FunctionalState             filterInitNoZeroEn;
    uint8_t                     filterClkDiv;
    uint8_t                     filterThresh;
    uint8_t                     filterSampWindows;
} ETIMER_ICInitParam;

typedef struct __PACKED
{
    uint32_t                channelMask; /*!< specifies the etimer channel that needs to be initialized.
                                          * this parameter can set multiple channels at the same time.
                                          * This parameter can be a value of @ref ETIMER_Channel  */
    ETIMER_FaultOutPolarity polarity;    /*!< specifies the polarity of fault mode
                                          * This parameter can be a value of @ref ETIMER_Fault_Out_Polarity*/
    ETIMER_FaultMode        mode;        /*!< specifies fault mode
                                          * This parameter can be a value of @ref ETIMER_Fault_Mode*/
    ETIMER_FaultTrigger     trigger;     /*!< specifies the trigger source for the anomaly pattern
                                          * This parameter can be a value of @ref ETIMER_Fault_Trigger*/
} ETIMER_FaultInitParam;
/* function prototypes -----------------------------------------------*/
void ETIMER_deinit(void);

/* PWM */
void ETIMER_initTimeBaseStruct(ETIMER_TimeBaseInitParam *initStruct);
void ETIMER_initTimeBase(ETIMER_TimeBaseInitParam *init);
void ETIMER_initOCStruct(ETIMER_OCInitParam *initStruct);
void ETIMER_initOC(ETIMER_OCInitParam *init);
void ETIMER_initDBStruct(ETIMER_DBInitParam *initStruct);
void ETIMER_initDB(uint32_t channelGroup, ETIMER_DBInitParam *init);
void ETIMER_enable(uint32_t channelMask);
void ETIMER_disable(uint32_t channelMask);
void ETIMER_enableTimer(uint32_t channelMask);
void ETIMER_disableTimer(uint32_t channelMask);
void ETIMER_enablePWM(uint32_t channelMask);
void ETIMER_disablePWM(uint32_t channelMask);
void ETIMER_setPeriod(uint32_t channel, uint32_t period);
void ETIMER_setCompareA(uint32_t channel, uint32_t compare);
void ETIMER_setCompareB(uint32_t channel, uint32_t compare);
void ETIMER_confirmCompareShadow(uint32_t channel);
uint32_t ETIMER_getCount(uint32_t channel);
void ETIMER_clearCount(uint32_t channel);

/* interrupt */
void ETIMER_enableInterrupt(uint32_t channel, uint16_t interruptFlagMask);
void ETIMER_disableInterrupt(uint32_t channel, uint16_t interruptFlagMask);
void ETIMER_setInterruptMask(uint32_t channel, uint16_t interruptFlagMask);
void ETIMER_clearInterruptMask(uint32_t channel, uint16_t interruptFlagMask);
void ETIMER_forceInterrupt(uint32_t channel, uint16_t interruptFlagMask);
void ETIMER_clearInterruptStatus(uint32_t channel, uint16_t interruptFlagMask);
ITStatus ETIMER_getInterruptStatus(uint32_t channel, uint16_t interruptFlag);
ITStatus ETIMER_getInterruptStatusRaw(uint32_t channel, uint16_t interruptFlag);

/* capture */
void ETIMER_initICStruct(ETIMER_ICInitParam *initStruct);
void ETIMER_initIC(ETIMER_ICInitParam *init);
void ETIMER_enableCapture(uint32_t channelMask);
void ETIMER_disableCapture(uint32_t channelMask);
void ETIMER_enableCaptureFilter(uint32_t channelMask);
void ETIMER_disableCaptureFilter(uint32_t channelMask);
uint32_t ETIMER_getCaptureCnt0(uint32_t channel);
uint32_t ETIMER_getCaptureCnt1(uint32_t channel);
uint32_t ETIMER_getCaptureCnt2(uint32_t channel);
uint32_t ETIMER_getCaptureCnt3(uint32_t channel);
void ETIMER_resetCapture(uint32_t channel);

/* fault */
void ETIMER_initFaultStruct(ETIMER_FaultInitParam *initStruct);
void ETIMER_initFault(ETIMER_FaultInitParam *init);
void ETIMER_clearFault(uint32_t channel);
void ETIMER_forceInputFault(uint32_t channel, FlagStatus state);
void ETIMER_enableFault(uint32_t channel);
void ETIMER_disableFault(uint32_t channel);

/* event output */
void ETIMER_enableEventOut(uint32_t channelMask);
void ETIMER_disableEventOut(uint32_t channelMask);
void ETIMER_enableEventCntShadow(uint32_t channel);
void ETIMER_disableEventCntShadow(uint32_t channel);
void ETIMER_setEventValue(uint32_t channel, uint32_t cnt);

/* others */
void ETIMER_enableDMA(void);
void ETIMER_disableDMA(void);
void ETIMER_enableDMARequest(ETIMER_DMAChannel etimer2dmaChannel, ETIMER_DMARequest src);

/* sync */
void ETIMER_enableSyncIn(uint32_t channel);
void ETIMER_disableSyncIn(uint32_t channel);
void ETIMER_selectSyncIn(uint32_t channel, ETIMER_SyncIn syncSrc);
void ETIMER_forceSyncOutEvent(uint32_t channel);
void ETIMER_selectEventToETIMER(uint32_t channel, ETIMER_SyncOutEvent event);
void ETIMER_selectEventToADC_DAC_ACMP(uint32_t channel, ETIMER_ADC_DAC_ACMP_SyncOutEvent event);
void ETIMER_selectSyncToDAC(ETIMER_DACx dacNumber, ETIMER_DAC_ACMP_SyncOutSrc src);
void ETIMER_selectSyncToACMP(ETIMER_ACMPx acmpNumber, ETIMER_DAC_ACMP_SyncOutSrc src);
void ETIMER_selectSyncToXBAROrPin(ETIMER_SyncOutSrc syncSrc);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif  /*__ET6X_ETIMER_H */
