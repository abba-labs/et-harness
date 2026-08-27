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
#ifndef __ET6X_INTERRUPT_H
#define __ET6X_INTERRUPT_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup INTERRUPT
 * @{
 */


#define INTERRUPT_MAX_IRQN    (226U + 1U)
void Interrupt_defaultHandler(void);

extern void (* vectorTable[INTERRUPT_MAX_IRQN])(void);


__STATIC_INLINE bool Interrupt_enableGlobal(void)
{
    __enable_irq();
    return true;
}

__STATIC_INLINE bool Interrupt_disableGlobal(void)
{
    __disable_irq();
    return true;
}

__STATIC_INLINE void Interrupt_initVectorTable(void)
{
    uint32_t i;

    for (i = 16U; i < 226U; i++)
    {
        vectorTable[i] = Interrupt_defaultHandler;
    }
}

__STATIC_INLINE void Interrupt_register(IRQn_Type interruptNumber, void (*handler)(void))
{
    vectorTable[interruptNumber + 16] = handler;
}

__STATIC_INLINE void Interrupt_unregister(IRQn_Type interruptNumber)
{
    vectorTable[interruptNumber + 16] = Interrupt_defaultHandler;
}

__STATIC_INLINE void Interrupt_enable(IRQn_Type interruptNumber)
{
    NVIC_EnableIRQ(interruptNumber);
}

__STATIC_INLINE void Interrupt_disable(IRQn_Type interruptNumber)
{
    NVIC_DisableIRQ(interruptNumber);
}

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /*__ET6X_INTERRUPT_H */
