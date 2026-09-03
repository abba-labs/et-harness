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

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __ET6X_CORTEX_H
#define __ET6X_CORTEX_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup CORTEX
 * @{
 */

void SYSCNT_start(void);
void SYSCNT_stop(void);
void SYSCNT_delay(uint32_t ms);
void SYSCNT_enableDebugHalt(void);
void SYSCNT_disableDebugHalt(void);
bool SYSCNT_getDebugHaltStatus(void);
void SYSCNT_setValue(uint64_t SyscntValue);
uint64_t SYSCNT_getCurrentVal(void);
void DWT_delay_us(uint32_t us);

void arm_cm_delay_asm(uint32_t);

#define DELAY_NS(a)         arm_cm_delay_asm((a) * 17)
#define DELAY_US(a)         arm_cm_delay_asm((a) * (200 / 2))
#define DWT_delay_ms(ms)    DWT_delay_us(1000 * ms)

/**
 * @}
 */

/**
 * @}
 */

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* SYSCNT has two 32-bit words in each of its SVD register views. */
#define SYSCNT_TEST_WORD_BITS 32u
/* A torn read retries at most four times; failure never returns a fabricated count. */
#define SYSCNT_TEST_READ_ATTEMPTS 4u

typedef enum
{
    SYSCNT_TEST_VIEW_CONTROL = 0u,
    SYSCNT_TEST_VIEW_READ = 1u
} SYSCNT_TestView;

typedef struct
{
    uint8_t enabled;
    uint8_t halt_enabled;
    uint8_t debug_halted;
    uint32_t frequency_id_hz;
} SYSCNT_TestControl;

/* Atomic SYSCNT operations; external clock/halt routing stays caller-owned. */
DRV_Status SYSCNT_testSetEnabled(uint8_t enabled);
DRV_Status SYSCNT_testLoadStopped(uint64_t value);
DRV_Status SYSCNT_testReadCount(SYSCNT_TestView view, uint64_t *value);
DRV_Status SYSCNT_testGetControl(SYSCNT_TestControl *control);
DRV_Status SYSCNT_testSetHaltPolicy(uint8_t enabled);
DRV_Status SYSCNT_testSetFrequencyId(uint32_t frequency_hz);

/* Explicitly borrow the Cortex DWT reference; never reset CYCCNT. */
DRV_Status SYSCNT_testSetReferenceEnabled(uint8_t enabled);
DRV_Status SYSCNT_testSampleReference(uint32_t *before, uint64_t *count, uint32_t *after);

/********************* TEST DRIVER EXTENSION END *********************/
#endif

#ifdef __cplusplus
}
#endif

#endif /* __ET6X_CORTEX_H */
