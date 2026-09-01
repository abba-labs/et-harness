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

#ifndef __ET6x_WAG_H
#define __ET6x_WAG_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"


/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup WAG
 * @{
 */

/**
 * @brief  WAG Load Mode
 */
typedef enum
{
    WAG_LOADMODE_SHADOW,
    WAG_LOADMODE_DIRECT
} WAG_LoadMode;

/**
 * @brief  WAG Output Hold Mode
 */
typedef enum
{
    WAG_OUTPUTHOLD_VALUE_REG,    /*!< WAG output hold value from register. */
    WAG_OUTPUTHOLD_VALUE_CURRENT /*!< WAG output hold value from current output. */
} WAG_OutputHoldMode;

/**
 * @brief  WAG Trigger Mode
 */
typedef enum
{
    WAG_TRIGGERMODE_SW, /*!< WAG trigger source software. */
    WAG_TRIGGERMODE_HW  /*!< WAG trigger source hardware. */
} WAG_TriggerMode;

/**
 * @brief  WAG Output Wave Type
 */
typedef enum
{
    WAG_WAVETYPE_STATIC,
    WAG_WAVETYPE_SQUARE,
    WAG_WAVETYPE_RAMP,
    WAG_WAVETYPE_TRIANGLE,
    WAG_WAVETYPE_SINE
} WAG_WaveType;

/**
 * @brief  WAG Output Mode
 */
typedef enum
{
    WAG_OUTPUTMODE_ONCE,      /*!< Output a period of waveform. */
    WAG_OUTPUTMODE_CONTINOUS  /*!< Output continuous waveform. */
} WAG_OutputMode;

/**
 * @brief  WAG Ramp Wave Mode
 */
typedef enum
{
    WAG_RAMP_WAVE_DECREMENT,
    WAG_RAMP_WAVE_INCREMENT
} WAG_RampWaveMode;

/**
 * @brief  WAG Triangle Start Direction
 */
typedef enum
{
    WAG_TRIANGLE_WAVE_START_L_THRD, /*!< Triangle wave start from low threshold. */
    WAG_TRIANGLE_WAVE_START_H_THRD  /*!< Triangle wave start from high threshold. */
} WAG_TriangleStartDir;

/**
 * @brief  WAG Config Structure Definition
 */
typedef struct __PACKED
{
    uint16_t             prescaler;
    WAG_WaveType         waveType;
    uint8_t              cordicIterationCycle;
    WAG_LoadMode         loadmode;
    WAG_TriggerMode      startTriggerMode;
    WAG_TriggerMode      stopTriggerMode;
    ControlStatus        startTriggerInvertEn;
    ControlStatus        stopTriggerInvertEn;
    WAG_TriangleStartDir triangleStartDirSel;
    WAG_OutputMode       triangleWaveOutputMode;
    WAG_RampWaveMode     rampWaveMode;
    WAG_OutputMode       squareWaveOutputMode;
    WAG_LoadMode         staticWaveLoadMode;
} WAG_ConfigParam;

void WAG_enableModule(void);
void WAG_disableModule(void);

/* WAG DMA request */
void WAG_enableDMARequest(void);
void WAG_disableDMARequest(void);

/* common static param configure */
void WAG_config(WAG_ConfigParam *config);

/* triangle wave dynamic configure */
void WAG_setTriangleUpStep(uint16_t value);
void WAG_setTriangleDownStep(uint16_t value);
void WAG_setTriangleHThrd(uint16_t value);
void WAG_setTriangleLThrd(uint16_t value);

/* ramp wave dynamic configure */
void WAG_setRampUpStep(uint16_t value);
void WAG_setRampDownStep(uint16_t value);
void WAG_setRampHThrd(uint16_t value);
void WAG_setRampLThrd(uint16_t value);

/* sine wave dynamic configure */
void WAG_setSineFrq(uint16_t value);
void WAG_setSinePhase(uint16_t value);
void WAG_setSineAmplitudeShift(uint16_t value);
void WAG_setSineRangeScale(uint16_t value);
void WAG_setSineAmplitudeScale(uint16_t value);
void WAG_setStaticWaveAmplitude(uint16_t value);

/* square wave dynamic configure */
void WAG_setSquareRangeH(uint16_t value);
void WAG_setSquareRangeL(uint16_t value);
void WAG_enableGlobalLoad(void);
void WAG_disableGlobalLoad(void);
void WAG_setTriggerDelay(uint16_t triggerDelay);
void WAG_configOutputHold(uint16_t codeValue, WAG_OutputHoldMode holdMode);
void WAG_startTriggerStartSingle(void);
void WAG_startTriggerStopSingle(void);
void WAG_setR03LoadReady(void);
bool WAG_isR03LoadComplete(void);
uint16_t WAG_getStatus(void);

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif
