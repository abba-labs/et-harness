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

#include "et6x_dualcore.h"
#include "et6x_crg.h"
#include "et6x_sysctrl.h"


/**
 * @brief Get current core ID
 *
 * @return CORE_ID
 * core0: 1
 * core1: 2
 */
CORE_ID DUALCORE_getCurrentCoreId(void)
{
    return READ_REG(EPPB->CORE_INDEX);
}

/**
 * @brief start core1 from start addr
 *
 * @param start_addr: core1 start address
 */
void DUALCORE_startCore1(uint32_t start_addr)
{
    /* unlock register */
    SYSC_unlockCriticalRegs();

    /* set CORE1 start address */
    WRITE_REG(SYSC->CPU1_BTADDR, start_addr);

    /* config reset */
    SET_BIT(SYSC->CPU, SYSC_CPU_CPU1_REQ_RST_MODE_Msk);

    uint32_t dly = 0;

    CLEAR_BIT(CRG->SRST0, BIT_MASK(25));//CRG_SRST_CPU1
    for (dly = 0; dly < 0xFFFF; dly++)
    {
    }
    SET_BIT(CRG->SRST0, BIT_MASK(25));//CRG_SRST_CPU1
    /* start core1 */
    CLEAR_BIT(SYSC->CPU_WAIT, SYSC_CPU_WAIT_SYSC_CPU1_WAIT_Msk);

    /* lock register */
    SYSC_lockCriticalRegs();
}
