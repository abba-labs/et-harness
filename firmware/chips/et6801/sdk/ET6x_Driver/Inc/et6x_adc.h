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

#ifndef __ET6X_ADC_H
#define __ET6X_ADC_H

#include "et6x.h"

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET6003_Driver
 * @{
 */

/** @addtogroup ADC
 * @{
 */

#define ADC_VIRTUAL_CHANNEL0            (0x0001)
#define ADC_VIRTUAL_CHANNEL1            (0x0002)
#define ADC_VIRTUAL_CHANNEL2            (0x0004)
#define ADC_VIRTUAL_CHANNEL3            (0x0008)
#define ADC_VIRTUAL_CHANNEL4            (0x0010)
#define ADC_VIRTUAL_CHANNEL5            (0x0020)
#define ADC_VIRTUAL_CHANNEL6            (0x0040)
#define ADC_VIRTUAL_CHANNEL7            (0x0080)
#define ADC_VIRTUAL_CHANNEL8            (0x0100)
#define ADC_VIRTUAL_CHANNEL9            (0x0200)
#define ADC_VIRTUAL_CHANNEL10           (0x0400)
#define ADC_VIRTUAL_CHANNEL11           (0x0800)
#define ADC_VIRTUAL_CHANNEL12           (0x1000)
#define ADC_VIRTUAL_CHANNEL13           (0x2000)
#define ADC_VIRTUAL_CHANNEL14           (0x4000)
#define ADC_VIRTUAL_CHANNEL15           (0x8000)
#define ADC_VIRTUAL_CHANNELALL          (0xFFFF)

#define ADC_ANALOG_CHANNEL0             (0x00000001)
#define ADC_ANALOG_CHANNEL1             (0x00000002)
#define ADC_ANALOG_CHANNEL2             (0x00000004)
#define ADC_ANALOG_CHANNEL3             (0x00000008)
#define ADC_ANALOG_CHANNEL4             (0x00000010)
#define ADC_ANALOG_CHANNEL5             (0x00000020)
#define ADC_ANALOG_CHANNEL6             (0x00000040)
#define ADC_ANALOG_CHANNEL7             (0x00000080)
#define ADC_ANALOG_CHANNEL8             (0x00000100)
#define ADC_ANALOG_CHANNEL9             (0x00000200)
#define ADC_ANALOG_CHANNEL10            (0x00000400)
#define ADC_ANALOG_CHANNEL11            (0x00000800)
#define ADC_ANALOG_CHANNEL12            (0x00001000)
#define ADC_ANALOG_CHANNEL13            (0x00002000)
#define ADC_ANALOG_CHANNEL14            (0x00004000)
#define ADC_ANALOG_CHANNEL15            (0x00008000)
#define ADC_ANALOG_CHANNEL16            (0x00010000)
#define ADC_ANALOG_CHANNEL17            (0x00020000)
#define ADC_ANALOG_CHANNEL18            (0x00040000)
#define ADC_ANALOG_CHANNEL19            (0x00080000)
#define ADC_ANALOG_CHANNEL20            (0x00100000)
#define ADC_ANALOG_CHANNEL21            (0x00200000)
#define ADC_ANALOG_CHANNEL22            (0x00300000)
#define ADC_ANALOG_CHANNEL23            (0x00400000)
#define ADC_ANALOG_CHANNEL24            (0x01000000)
#define ADC_ANALOG_CHANNEL25            (0x02000000)
#define ADC_ANALOG_CHANNEL26            (0x04000000)
#define ADC_ANALOG_CHANNEL27            (0x08000000)
#define ADC_ANALOG_CHANNEL28            (0x10000000)
#define ADC_ANALOG_CHANNEL29            (0x20000000)
#define ADC_ANALOG_CHANNEL30            (0x40000000)
#define ADC_ANALOG_CHANNEL31            (0x80000000)
#define ADC_ANALOG_CHANNELALL           (0xFFFFFFFF)

#define ADC_PREPROCESS_CHANNEL0         (0x0001)
#define ADC_PREPROCESS_CHANNEL1         (0x0002)
#define ADC_PREPROCESS_CHANNEL2         (0x0004)
#define ADC_PREPROCESS_CHANNEL3         (0x0008)
#define ADC_PREPROCESS_CHANNEL4         (0x0010)
#define ADC_PREPROCESS_CHANNEL5         (0x0020)
#define ADC_PREPROCESS_CHANNEL6         (0x0040)
#define ADC_PREPROCESS_CHANNEL7         (0x0080)
#define ADC_PREPROCESS_CHANNEL8         (0x0100)
#define ADC_PREPROCESS_CHANNEL9         (0x0200)
#define ADC_PREPROCESS_CHANNEL10        (0x0400)
#define ADC_PREPROCESS_CHANNEL11        (0x0800)
#define ADC_PREPROCESS_CHANNEL12        (0x1000)
#define ADC_PREPROCESS_CHANNEL13        (0x2000)
#define ADC_PREPROCESS_CHANNEL14        (0x4000)
#define ADC_PREPROCESS_CHANNEL15        (0x8000)
#define ADC_PREPROCESS_CHANNELALL       (0xFFFF)

#define ADC_FILTER_CHANNEL0             (0x0001)
#define ADC_FILTER_CHANNEL1             (0x0002)
#define ADC_FILTER_CHANNEL2             (0x0004)
#define ADC_FILTER_CHANNEL3             (0x0008)
#define ADC_FILTER_CHANNEL4             (0x0010)
#define ADC_FILTER_CHANNEL5             (0x0020)
#define ADC_FILTER_CHANNEL6             (0x0040)
#define ADC_FILTER_CHANNEL7             (0x0080)
#define ADC_FILTER_CHANNELALL           (0x00FF)


#define ADC_SAMPLE_STATUS_DONE          (0x10)
#define ADC_SAMPLE_STATUS_BUSY          (0x20)

#define ADC_VC_SAMPLE_STATUS_IDLE       (0x00)
#define ADC_VC_SAMPLE_STATUS_PENDING    (0x01)
#define ADC_VC_SAMPLE_STATUS_BUSY       (0x02)

typedef enum
{
    ADC_TRIGGER_MODE_CONTINUOUS = 0,   /*!< continuous trigger mode  */
    ADC_TRIGGER_MODE_ONE_SHOT   = 1    /*!< one-shot trigger mode  */
} ADC_TrigMode;

typedef enum
{
    ADC_TRIGGER_SRPWM0_SOC0  = 0,
    ADC_TRIGGER_SRPWM0_SOC1  = 1,
    ADC_TRIGGER_SRPWM1_SOC0  = 2,
    ADC_TRIGGER_SRPWM1_SOC1  = 3,
    ADC_TRIGGER_SRPWM2_SOC0  = 4,
    ADC_TRIGGER_SRPWM2_SOC1  = 5,
    ADC_TRIGGER_SRPWM3_SOC0  = 6,
    ADC_TRIGGER_SRPWM3_SOC1  = 7,
    ADC_TRIGGER_SRPWM4_SOC0  = 8,
    ADC_TRIGGER_SRPWM4_SOC1  = 9,
    ADC_TRIGGER_SRPWM5_SOC0  = 10,
    ADC_TRIGGER_SRPWM5_SOC1  = 11,
    ADC_TRIGGER_SRPWM6_SOC0  = 12,
    ADC_TRIGGER_SRPWM6_SOC1  = 13,
    ADC_TRIGGER_SRPWM7_SOC0  = 14,
    ADC_TRIGGER_SRPWM7_SOC1  = 15,
    ADC_TRIGGER_SRPWM8_SOC0  = 16,
    ADC_TRIGGER_SRPWM8_SOC1  = 17,
    ADC_TRIGGER_SRPWM9_SOC0  = 18,
    ADC_TRIGGER_SRPWM9_SOC1  = 19,
    ADC_TRIGGER_SRPWM10_SOC0 = 20,
    ADC_TRIGGER_SRPWM10_SOC1 = 21,
    ADC_TRIGGER_SRPWM11_SOC0 = 22,
    ADC_TRIGGER_SRPWM11_SOC1 = 23,
    ADC_TRIGGER_SRPWM12_SOC0 = 24,
    ADC_TRIGGER_SRPWM12_SOC1 = 25,
    ADC_TRIGGER_SRPWM13_SOC0 = 26,
    ADC_TRIGGER_SRPWM13_SOC1 = 27,
    ADC_TRIGGER_SRPWM14_SOC0 = 28,
    ADC_TRIGGER_SRPWM14_SOC1 = 29,
    ADC_TRIGGER_SRPWM15_SOC0 = 30,
    ADC_TRIGGER_SRPWM15_SOC1 = 31,
    ADC_TRIGGER_SRPWM16_SOC0 = 32,
    ADC_TRIGGER_SRPWM16_SOC1 = 33,
    ADC_TRIGGER_SRPWM17_SOC0 = 34,
    ADC_TRIGGER_SRPWM17_SOC1 = 35,

    ADC_TRIGGER_ETIMER0      = 36,
    ADC_TRIGGER_ETIMER1      = 37,
    ADC_TRIGGER_ETIMER2      = 38,
    ADC_TRIGGER_ETIMER3      = 39,
    ADC_TRIGGER_ETIMER4      = 40,
    ADC_TRIGGER_ETIMER5      = 41,
    ADC_TRIGGER_ETIMER6      = 42,
    ADC_TRIGGER_ETIMER7      = 43,
    ADC_TRIGGER_ETIMER8      = 44,
    ADC_TRIGGER_ETIMER9      = 45,
    ADC_TRIGGER_ETIMER10     = 46,
    ADC_TRIGGER_ETIMER11     = 47,

    ADC_TRIGGER_IPTEST       = 53,

    ADC_TRIGGER_ACMP0_H      = 54,
    ADC_TRIGGER_ACMP0_L      = 55,
    ADC_TRIGGER_ACMP1_H      = 56,
    ADC_TRIGGER_ACMP1_L      = 57,
    ADC_TRIGGER_ACMP2_H      = 58,
    ADC_TRIGGER_ACMP2_L      = 59,
    ADC_TRIGGER_ACMP3_H      = 60,
    ADC_TRIGGER_ACMP3_L      = 61,
    ADC_TRIGGER_ACMP4_H      = 62,
    ADC_TRIGGER_ACMP4_L      = 63,
    ADC_TRIGGER_ACMP5_H      = 64,
    ADC_TRIGGER_ACMP5_L      = 65,
    ADC_TRIGGER_ACMP6_H      = 66,
    ADC_TRIGGER_ACMP6_L      = 67,
    ADC_TRIGGER_ACMP7_H      = 68,
    ADC_TRIGGER_ACMP7_L      = 69,
    ADC_TRIGGER_ACMP8_H      = 70,
    ADC_TRIGGER_ACMP8_L      = 71,
    ADC_TRIGGER_ACMP9_H      = 72,
    ADC_TRIGGER_ACMP9_L      = 73,
    ADC_TRIGGER_ACMP10_H     = 74,
    ADC_TRIGGER_ACMP10_L     = 75,

    ADC_TRIGGER_STM0_OC0     = 76,
    ADC_TRIGGER_STM0_OC1     = 77,
    ADC_TRIGGER_STM0_OC2     = 78,
    ADC_TRIGGER_STM0_OC3     = 79,
    ADC_TRIGGER_STM1_OC0     = 80,
    ADC_TRIGGER_STM1_OC1     = 81,
    ADC_TRIGGER_STM1_OC2     = 82,
    ADC_TRIGGER_STM1_OC3     = 83,
    ADC_TRIGGER_STM2_OC0     = 84,
    ADC_TRIGGER_STM2_OC1     = 85,
    ADC_TRIGGER_STM2_OC2     = 86,
    ADC_TRIGGER_STM2_OC3     = 87,
    ADC_TRIGGER_STM3_OC0     = 88,
    ADC_TRIGGER_STM3_OC1     = 89,
    ADC_TRIGGER_STM3_OC2     = 90,
    ADC_TRIGGER_STM3_OC3     = 91,
    ADC_TRIGGER_STM4_OC0     = 92,
    ADC_TRIGGER_STM4_OC1     = 93,
    ADC_TRIGGER_STM4_OC2     = 94,
    ADC_TRIGGER_STM4_OC3     = 95,
    ADC_TRIGGER_STM5_OC0     = 96,
    ADC_TRIGGER_STM5_OC1     = 97,
    ADC_TRIGGER_STM5_OC2     = 98,
    ADC_TRIGGER_STM5_OC3     = 99,

    ADC_TRIGGER_XBAR_CLU0    = 100,    /* XBAR的CLU DATA？ */
    ADC_TRIGGER_XBAR_CLU1    = 101,
    ADC_TRIGGER_XBAR_CLU2    = 102,
    ADC_TRIGGER_XBAR_CLU3    = 103,

    ADC_TRIGGER_ADC0_EOC0    = 104,
    ADC_TRIGGER_ADC0_EOC1    = 105,
    ADC_TRIGGER_ADC1_EOC0    = 106,
    ADC_TRIGGER_ADC1_EOC1    = 107,
    ADC_TRIGGER_ADC2_EOC0    = 108,
    ADC_TRIGGER_ADC2_EOC1    = 109,

    ADC_TRIGGER_INXB         = 110,

    ADC_TRIGGER_NONE         = 111
} ADC_Trigger;
typedef enum
{
    ADC_RESULT_ALIGN_RIGHT = 0, /* 采用右对齐方式，对于滤波后结果，格式为U(12,0);对于预处理后结果，格式为S(15,0) */
    ADC_RESULT_ALIGN_LEFT  = 1  /* 采用左对齐方式，对于滤波后结果，格式为S(15,0);对于预处理后结果，格式为S(16,2) */
} ADC_ResultAlign;

typedef enum
{
    ADC_VC_PRIORITY_GRP_0 = 0,   /* first priority group */
    ADC_VC_PRIORITY_GRP_1 = 1,
    ADC_VC_PRIORITY_GRP_2 = 2,
    ADC_VC_PRIORITY_GRP_3 = 3
} ADC_VCPriorityGroup;

typedef enum
{
    ADC_PRIORITY_MODE_LOW_DISCARD = 0,   /* low priority tasks are discarded */
    ADC_PRIORITY_MODE_LOW_QUEUE   = 1    /* low priority tasks are queued for processing */
} ADC_PriorityMode;

typedef enum
{
    ADC_INT_TRIGGER_EOC0_EOC           = 0,
    ADC_INT_TRIGGER_EOC0_PRE_RESULT    = 1,
    ADC_INT_TRIGGER_EOC0_FILTER_RESULT = 2,
    ADC_INT_TRIGGER_EOC1_EOC           = 3,
    ADC_INT_TRIGGER_EOC1_PRE_RESULT    = 4,
    ADC_INT_TRIGGER_EOC1_FILTER_RESULT = 5,
    ADC_INT_TRIGGER_EOC2_EOC           = 6,
    ADC_INT_TRIGGER_EOC2_PRE_RESULT    = 7,
    ADC_INT_TRIGGER_EOC2_FILTER_RESULT = 8,
    ADC_INT_TRIGGER_EOC3_EOC           = 9,
    ADC_INT_TRIGGER_EOC3_PRE_RESULT    = 10,
    ADC_INT_TRIGGER_EOC3_FILTER_RESULT = 11,
    ADC_INT_TRIGGER_WDG_HIGH_THRESHOLD = 12,
    ADC_INT_TRIGGER_WDG_LOW_THRESHOLD  = 13
} ADC_IntTrigger;
typedef enum
{
    ADC_EOC_EVT_NUM_0 = 0,
    ADC_EOC_EVT_NUM_1 = 1
} ADC_EOCEventNum;
typedef enum
{
    ADC_EOC_EVT_SRC_VC0  = 0,
    ADC_EOC_EVT_SRC_VC1  = 1,
    ADC_EOC_EVT_SRC_VC2  = 2,
    ADC_EOC_EVT_SRC_VC3  = 3,
    ADC_EOC_EVT_SRC_VC4  = 4,
    ADC_EOC_EVT_SRC_VC5  = 5,
    ADC_EOC_EVT_SRC_VC6  = 6,
    ADC_EOC_EVT_SRC_VC7  = 7,
    ADC_EOC_EVT_SRC_VC8  = 8,
    ADC_EOC_EVT_SRC_VC9  = 9,
    ADC_EOC_EVT_SRC_VC10 = 10,
    ADC_EOC_EVT_SRC_VC11 = 11,
    ADC_EOC_EVT_SRC_VC12 = 12,
    ADC_EOC_EVT_SRC_VC13 = 13,
    ADC_EOC_EVT_SRC_VC14 = 14,
    ADC_EOC_EVT_SRC_VC15 = 15
} ADC_EOCEventSrc;
typedef enum
{
    ADC_EOC_PULSE_END_OF_SH_FALLING = 0, /* 采样保持窗口结束的下降沿 */
    ADC_EOC_PULSE_END_OF_CONV       = 1, /* 转换结束时刻 */
    ADC_EOC_PULSE_END_OF_SH_RISING  = 2  /* 采样保持窗口结束的上升沿 */
} ADC_EOCPulseMode;
typedef enum
{
    ADC_ANALOG_WDG_OUT_MODE_OS  = 0, /* one-shot */
    ADC_ANALOG_WDG_OUT_MODE_CBC = 1  /* CBC */
} ADC_AnalogWdgOutMode;
typedef enum
{
    ADC_ANALOG_WDG_THRESHOLD_LOW  = 0,
    ADC_ANALOG_WDG_THRESHOLD_HIGH = 16
} ADC_AnalogWdgThreshold;
typedef enum
{
    ADC_ANALOG_WDG_EVT_NUM_0 = 0,
    ADC_ANALOG_WDG_EVT_NUM_1 = 1,
    ADC_ANALOG_WDG_EVT_NUM_2 = 2,
    ADC_ANALOG_WDG_EVT_NUM_3 = 3
} ADC_AnalogWdgEvtNum;
typedef enum
{
    ADC_ANALOG_WDG_EVT_VC0  = 0,
    ADC_ANALOG_WDG_EVT_VC1  = 1,
    ADC_ANALOG_WDG_EVT_VC2  = 2,
    ADC_ANALOG_WDG_EVT_VC3  = 3,
    ADC_ANALOG_WDG_EVT_VC4  = 4,
    ADC_ANALOG_WDG_EVT_VC5  = 5,
    ADC_ANALOG_WDG_EVT_VC6  = 6,
    ADC_ANALOG_WDG_EVT_VC7  = 7,
    ADC_ANALOG_WDG_EVT_VC8  = 8,
    ADC_ANALOG_WDG_EVT_VC9  = 9,
    ADC_ANALOG_WDG_EVT_VC10 = 10,
    ADC_ANALOG_WDG_EVT_VC11 = 11,
    ADC_ANALOG_WDG_EVT_VC12 = 12,
    ADC_ANALOG_WDG_EVT_VC13 = 13,
    ADC_ANALOG_WDG_EVT_VC14 = 14,
    ADC_ANALOG_WDG_EVT_VC15 = 15
} ADC_AnalogWdgEvt;
typedef enum
{
    ADC0_BLANKING_TRIGGER_SRPWM_ROW0_COL0 = 0,    /** trigger source description from srpwm*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW0_COL1 = 1,    /* +------+--------------------+---------+---------+---------+*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW0_COL2 = 2,    /* |      | column0            | column1 | column2 | column3 |*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW0_COL3 = 3,    /* +------+--------------------+---------+---------+---------+*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW1_COL0 = 4,    /* | row0 | SRPWM0~11:trigger0 | Same    | Same    | Same    |*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW1_COL1 = 5,    /* |      | SRPWM0~11:trigger1 |         |         |         |*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW1_COL2 = 6,    /* +------+--------------------+---------+---------+---------+*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW1_COL3 = 7,    /* | row1 | Same               | Same    | Same    | Same    |*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW2_COL0 = 8,    /* +------+--------------------+---------+---------+---------+*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW2_COL1 = 9,    /* | row2 | Same               | Same    | Same    | Same    |*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW2_COL2 = 10,   /* +------+--------------------+---------+---------+---------+*/
    ADC0_BLANKING_TRIGGER_SRPWM_ROW2_COL3 = 11,
    ADC0_BLANKING_TRIGGER_ETIMER0         = 12,
    ADC0_BLANKING_TRIGGER_ETIMER1         = 13,
    ADC0_BLANKING_TRIGGER_ETIMER2         = 14
} ADC_BlankingTrigger;

typedef enum
{
    ADC_FILTER_TYPE_FIR                 = 0x0,
    ADC_FILTER_TYPE_IIR                 = 0x1,
    ADC_FILTER_TYPE_NON_SLIDING_AVERAGE = 0x2   /* Non Sliding Average Filtering */
} ADC_FilterType;

typedef enum
{
    ADC_FILTER_FIR_COEFF_ADDR0  = 0,
    ADC_FILTER_FIR_COEFF_ADDR1  = 1,
    ADC_FILTER_FIR_COEFF_ADDR2  = 2,
    ADC_FILTER_FIR_COEFF_ADDR3  = 3,
    ADC_FILTER_FIR_COEFF_ADDR4  = 4,
    ADC_FILTER_FIR_COEFF_ADDR5  = 5,
    ADC_FILTER_FIR_COEFF_ADDR6  = 6,
    ADC_FILTER_FIR_COEFF_ADDR7  = 7,
    ADC_FILTER_FIR_COEFF_ADDR8  = 8,
    ADC_FILTER_FIR_COEFF_ADDR9  = 9,
    ADC_FILTER_FIR_COEFF_ADDR10 = 10,
    ADC_FILTER_FIR_COEFF_ADDR11 = 11,
    ADC_FILTER_FIR_COEFF_ADDR12 = 12,
    ADC_FILTER_FIR_COEFF_ADDR13 = 13,
    ADC_FILTER_FIR_COEFF_ADDR14 = 14,
    ADC_FILTER_FIR_COEFF_ADDR15 = 15,
    ADC_FILTER_FIR_COEFF_ADDR16 = 16,
    ADC_FILTER_FIR_COEFF_ADDR17 = 17,
    ADC_FILTER_FIR_COEFF_ADDR18 = 18,
    ADC_FILTER_FIR_COEFF_ADDR19 = 19,
    ADC_FILTER_FIR_COEFF_ADDR20 = 20,
    ADC_FILTER_FIR_COEFF_ADDR21 = 21,
    ADC_FILTER_FIR_COEFF_ADDR22 = 22,
    ADC_FILTER_FIR_COEFF_ADDR23 = 23,
    ADC_FILTER_FIR_COEFF_ADDR24 = 24,
    ADC_FILTER_FIR_COEFF_ADDR25 = 25,
    ADC_FILTER_FIR_COEFF_ADDR26 = 26,
    ADC_FILTER_FIR_COEFF_ADDR27 = 27,
    ADC_FILTER_FIR_COEFF_ADDR28 = 28,
    ADC_FILTER_FIR_COEFF_ADDR29 = 29,
    ADC_FILTER_FIR_COEFF_ADDR30 = 30,
    ADC_FILTER_FIR_COEFF_ADDR31 = 31
} ADC_FilterFIR_CoeffAddr;/* FIR number of filter taps */

typedef enum
{
    ADC_DMA_CHANNEL0 = 0,
    ADC_DMA_CHANNEL1 = 1,
    ADC_DMA_CHANNEL2 = 2,
    ADC_DMA_CHANNEL3 = 3
} ADC_DMAChannel;
typedef enum
{
    /* the adc simulates the lower threshold before watchdog filtering*/
    ADC_DMA_REQUEST_EOC_VC0            = 0,
    ADC_DMA_REQUEST_EOC_VC1            = 1,
    ADC_DMA_REQUEST_EOC_VC2            = 2,
    ADC_DMA_REQUEST_EOC_VC3            = 3,
    ADC_DMA_REQUEST_EOC_VC4            = 4,
    ADC_DMA_REQUEST_EOC_VC5            = 5,
    ADC_DMA_REQUEST_EOC_VC6            = 6,
    ADC_DMA_REQUEST_EOC_VC7            = 7,
    ADC_DMA_REQUEST_EOC_VC8            = 8,
    ADC_DMA_REQUEST_EOC_VC9            = 9,
    ADC_DMA_REQUEST_EOC_VC10           = 10,
    ADC_DMA_REQUEST_EOC_VC11           = 11,
    ADC_DMA_REQUEST_EOC_VC12           = 12,
    ADC_DMA_REQUEST_EOC_VC13           = 13,
    ADC_DMA_REQUEST_EOC_VC14           = 14,
    ADC_DMA_REQUEST_EOC_VC15           = 15,
    /* 看门狗上下门限相或*/
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC0  = 16,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC1  = 17,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC2  = 18,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC3  = 19,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC4  = 20,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC5  = 21,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC6  = 22,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC7  = 23,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC8  = 24,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC9  = 25,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC10 = 26,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC11 = 27,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC12 = 28,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC13 = 29,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC14 = 30,
    ADC_DMA_REQUEST_WDG_THRESHOLD_VC15 = 31,
    /* 用户预处理后结果*/
    ADC_DMA_REQUEST_PRE_RESULT_VC0     = 32,
    ADC_DMA_REQUEST_PRE_RESULT_VC1     = 33,
    ADC_DMA_REQUEST_PRE_RESULT_VC2     = 34,
    ADC_DMA_REQUEST_PRE_RESULT_VC3     = 35,
    ADC_DMA_REQUEST_PRE_RESULT_VC4     = 36,
    ADC_DMA_REQUEST_PRE_RESULT_VC5     = 37,
    ADC_DMA_REQUEST_PRE_RESULT_VC6     = 38,
    ADC_DMA_REQUEST_PRE_RESULT_VC7     = 39,
    ADC_DMA_REQUEST_PRE_RESULT_VC8     = 40,
    ADC_DMA_REQUEST_PRE_RESULT_VC9     = 41,
    ADC_DMA_REQUEST_PRE_RESULT_VC10    = 42,
    ADC_DMA_REQUEST_PRE_RESULT_VC11    = 43,
    ADC_DMA_REQUEST_PRE_RESULT_VC12    = 44,
    ADC_DMA_REQUEST_PRE_RESULT_VC13    = 45,
    ADC_DMA_REQUEST_PRE_RESULT_VC14    = 46,
    ADC_DMA_REQUEST_PRE_RESULT_VC15    = 47,
    /* 滤波后结果 */
    ADC_DMA_REQUEST_FILTER_RESULT_VC0  = 48,
    ADC_DMA_REQUEST_FILTER_RESULT_VC1  = 49,
    ADC_DMA_REQUEST_FILTER_RESULT_VC2  = 50,
    ADC_DMA_REQUEST_FILTER_RESULT_VC3  = 51,
    ADC_DMA_REQUEST_FILTER_RESULT_VC4  = 52,
    ADC_DMA_REQUEST_FILTER_RESULT_VC5  = 53,
    ADC_DMA_REQUEST_FILTER_RESULT_VC6  = 54,
    ADC_DMA_REQUEST_FILTER_RESULT_VC7  = 55,
    ADC_DMA_REQUEST_FILTER_RESULT_VC8  = 56,
    ADC_DMA_REQUEST_FILTER_RESULT_VC9  = 57,
    ADC_DMA_REQUEST_FILTER_RESULT_VC10 = 58,
    ADC_DMA_REQUEST_FILTER_RESULT_VC11 = 59,
    ADC_DMA_REQUEST_FILTER_RESULT_VC12 = 60,
    ADC_DMA_REQUEST_FILTER_RESULT_VC13 = 61,
    ADC_DMA_REQUEST_FILTER_RESULT_VC14 = 62,
    ADC_DMA_REQUEST_FILTER_RESULT_VC15 = 63,
    /* FIFO请求模式 */
    ADC_DMA_REQUEST_PRE_RESULT_FIFO    = 64,
    ADC_DMA_REQUEST_FILTER_RESULT_FIFO = 65
} ADC_DMARequest;

typedef enum
{
    ADC_FIFO_WATERLINE_1  = 0,
    ADC_FIFO_WATERLINE_2  = 1,
    ADC_FIFO_WATERLINE_3  = 2,
    ADC_FIFO_WATERLINE_4  = 3,
    ADC_FIFO_WATERLINE_5  = 4,
    ADC_FIFO_WATERLINE_6  = 5,
    ADC_FIFO_WATERLINE_7  = 6,
    ADC_FIFO_WATERLINE_8  = 7,
    ADC_FIFO_WATERLINE_9  = 8,
    ADC_FIFO_WATERLINE_10 = 9,
    ADC_FIFO_WATERLINE_11 = 10,
    ADC_FIFO_WATERLINE_12 = 11,
    ADC_FIFO_WATERLINE_13 = 12,
    ADC_FIFO_WATERLINE_14 = 13,
    ADC_FIFO_WATERLINE_15 = 14,
    ADC_FIFO_WATERLINE_16 = 15
} ADC_FifoWaterLine;

typedef enum
{
    ADC_PREFIL_INPUT_DATA_X2   = 0,
    ADC_PREFIL_INPUT_DATA_X1   = 1,
    ADC_PREFIL_INPUT_DATA_DIV2 = 2,
    ADC_PREFIL_INPUT_DATA_DIV4 = 3
} ADC_PreFilterInputDataGain;

typedef enum
{
    ADC_PREFIL_OUTPUT_GAIN_1   = 0,
    ADC_PREFIL_OUTPUT_GAIN_2   = 1,
    ADC_PREFIL_OUTPUT_GAIN_4   = 2,
    ADC_PREFIL_OUTPUT_GAIN_8   = 3,
    ADC_PREFIL_OUTPUT_GAIN_16  = 4,
    ADC_PREFIL_OUTPUT_GAIN_32  = 5,
    ADC_PREFIL_OUTPUT_GAIN_64  = 6,
    ADC_PREFIL_OUTPUT_GAIN_127 = 7
} ADC_PreFilterOutputDataGain;

typedef struct __PACKED
{
    uint16_t        virtualChannelMask; /*!< the virtual channel number  */
    ADC_TrigMode    trigMode;           /*!< trigger mode  */
    ADC_Trigger     trigger;            /*!< trigger source selection  */
    uint16_t        sampleTime;         /* S/H 采样窗口 */
    ADC_ResultAlign preResultAlign;     /* 预处理后的结果对齐方式 */
    ADC_ResultAlign filterResultAlign;  /* 滤波后的结果对齐方式 */
    FunctionalState preFifoModeEn;
    FunctionalState filterFifoModeEn;
    uint8_t         preFifoDepth;
    uint8_t         filterFifoDepth;
} ADC_InitTypeDef;

void ADC_deinit(ADC_Type *ADCx);

/* basic sampling capabilities */
void ADC_initStruct(ADC_InitTypeDef *initStruct);
void ADC_init(ADC_Type *ADCx, ADC_InitTypeDef *initStruct);
void ADC_enable(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_disable(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_setVCPriorityGroup(ADC_Type *ADCx, uint16_t virtualChannel, ADC_VCPriorityGroup priority);
void ADC_setPriorityMode(ADC_Type *ADCx, ADC_PriorityMode priorityMode);
void ADC_remapSingleAC(ADC_Type *ADCx, uint16_t virtualChannel, uint32_t analogChannel);
bool ADC_isBusy(ADC_Type *ADCx);
uint32_t ADC_getVCSampleStatus(ADC_Type *ADCx);
void ADC_forceVC(ADC_Type *ADCx, uint16_t virtualChannelMask);

/* 采样结果 */
int16_t ADC_getPreResult(ADC_Type *ADCx, uint16_t virtualChannel);
int16_t ADC_getFilterResult(ADC_Type *ADCx, uint16_t virtualChannel);
bool ADC_getPreResultStatus(ADC_Type *ADCx, uint16_t virtualChannel);
bool ADC_getFilterResultStatus(ADC_Type *ADCx, uint16_t virtualChannel);
uint16_t ADC_S16D2toUint(int16_t data);
float ADC_S16D2toFloat(int16_t data);

//todo 校准函数，未做变化，需要回片后确认校准功能
/* calibration function */
void ADC_startCalibration(ADC_Type *ADCx);

/* EOC相关 */
void ADC_selectEOCOutEvent(ADC_Type *ADCx, ADC_EOCEventNum num, ADC_EOCEventSrc event);
void ADC_setEOCPulseMode(ADC_Type *ADCx, ADC_EOCPulseMode pulseMode);
void ADC_enableEOCDelay(ADC_Type *ADCx);
void ADC_disableEOCDelay(ADC_Type *ADCx);
void ADC_setEOCDelay(ADC_Type *ADCx, uint16_t delay);
bool ADC_isEOCAlarm(ADC_Type *ADCx);
uint8_t ADC_getEOCAlarmVCChannel(ADC_Type *ADCx);

/* trigger_2_sample */
uint16_t ADC_getTrig2SampleDelay(ADC_Type *ADCx, uint16_t virtualChannel);

/* interrupt functionality */
void ADC_enableInterrupt(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger);
void ADC_disableInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);
void ADC_maskInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);
void ADC_unmaskInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);
void ADC_forceInterrupt(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);
bool ADC_getInterruptStatus(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger);
bool ADC_getInterruptStatusRaw(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger);
bool ADC_getInterruptOverflowStatus(ADC_Type *ADCx, uint16_t virtualChannel, ADC_IntTrigger interruptTrigger);
void ADC_clearInterruptStatus(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);
void ADC_clearInterruptOverflowStatus(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_IntTrigger interruptTrigger);

/* analog watch dog */
void ADC_setAnalogWdgMode(ADC_Type *ADCx, uint16_t virtualChannel, ADC_AnalogWdgOutMode outMode);
void ADC_enableAnalogWdg(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_AnalogWdgThreshold thresholdDir);
void ADC_disableAnalogWdg(ADC_Type *ADCx, uint16_t virtualChannelMask, ADC_AnalogWdgThreshold thresholdDir);
void ADC_selectAnalogWdgOutEvt2ETIMER(ADC_Type *ADCx, ADC_AnalogWdgEvtNum eventNumber, ADC_AnalogWdgEvt event);
void ADC_selectAnalogWdgOutEvt2XBAR(ADC_Type *ADCx, ADC_AnalogWdgEvtNum eventNumber, ADC_AnalogWdgEvt event);
void ADC_setAnalogWdgThreshold(ADC_Type *ADCx, uint16_t virtualChannel, uint16_t highThreshold,
                               uint16_t lowThreshold);
void ADC_clearAnalogWdgThresholdStatus(ADC_Type *ADCx, uint16_t virtualChannelMask,
                                       ADC_AnalogWdgThreshold thresholdDir);
uint16_t ADC_getAnalogWdgThresholdStatus(ADC_Type *ADCx, ADC_AnalogWdgThreshold thresholdDir);

/* blanking function  */
void ADC_enableBlanking(ADC_Type *ADCx);
void ADC_disableBlanking(ADC_Type *ADCx);
void ADC_selectBlankingTrigger(ADC_Type *ADCx, ADC_BlankingTrigger trigger);
void ADC_setBlankingWidth(ADC_Type *ADCx, uint16_t width);
void ADC_setBlankingTrigDelay(ADC_Type *ADCx, uint16_t delay);

/* calibration */
void ADC_enabelCalOSOffset(ADC_Type *ADCx, int16_t offset);
void ADC_disabelCalOSOffset(ADC_Type *ADCx);

/* preprocessing capabilities */
void ADC_enabelPreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_disablePreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_enablePreProcessGain(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_disablePreProcessGain(ADC_Type *ADCx, uint16_t virtualChannelMask);
void ADC_setPreProcessOffset(ADC_Type *ADCx, uint16_t virtualChannel, int16_t offset);
void ADC_setPreProcessGain(ADC_Type *ADCx, uint16_t virtualChannel, int16_t gain);

/* filtering function */
void ADC_enableVCFilter(ADC_Type *ADCx, uint16_t virtualChannel);
void ADC_disableVCFilter(ADC_Type *ADCx, uint16_t virtualChannel);
void ADC_enableFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask);
void ADC_disableFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask);
void ADC_remapFilterChannel(ADC_Type *ADCx, uint16_t virtualChannel, uint8_t filterChannel);
void ADC_selectFilterType(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterType filterType);
void ADC_clearFilterStatus(ADC_Type *ADCx, uint8_t filterChannelMask);
void ADC_setFilterNonAverCoeff(ADC_Type *ADCx, uint8_t filterChannel, uint8_t power);
void ADC_setFilterFIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterFIR_CoeffAddr coeffAddr, uint16_t coeff);
uint16_t ADC_getFilterFIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, ADC_FilterFIR_CoeffAddr coeffAddr);
bool ADC_getFilterFIRCoeffStatus(ADC_Type *ADCx);
void ADC_setFilterFIRLen(ADC_Type *ADCx, uint8_t filterChannel, uint8_t len);
void ADC_setFilterIIRCoeff(ADC_Type *ADCx, uint8_t filterChannel, uint16_t coeff);

/* DMA */
void ADC_enableDMARequest(ADC_Type *ADCx, ADC_DMAChannel adc2dmaChannel, ADC_DMARequest src);

/* PREFilter */
void ADC_enablePreFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask);
void ADC_disablePreFilterChannel(ADC_Type *ADCx, uint8_t filterChannelMask);
void ADC_enablePreFilter(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_disablePreFilter(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_setPreFilterIdataGain(ADC_Type *ADCx, uint16_t filterChannel, ADC_PreFilterInputDataGain gain);
void ADC_setPreFilterOdataR(ADC_Type *ADCx, uint16_t filterChannel, ADC_PreFilterOutputDataGain gain);
void ADC_setPreFilterResultClip(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_setPreFilterResultWrap(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_setPreFilterClearIdataBuffer(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_setPreFilterRdyClearBuffer(ADC_Type *ADCx, uint16_t filterChannel);
void ADC_setPreFilterType(ADC_Type *ADCx, uint16_t filterChannel, ADC_FilterType type);
void ADC_setPreFilterFIRCoeff(ADC_Type *ADCx, uint8_t p_cnt, uint16_t *coeff);
void ADC_setPreFilterIIRCoeff(ADC_Type *ADCx, uint8_t p_cnt, uint8_t q_cnt, uint16_t *pcoeff, uint16_t *qcoeff);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif  /*__ET6X_ADC_H */

/* end  */
