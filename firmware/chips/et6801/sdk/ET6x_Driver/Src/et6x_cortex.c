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
#include "et6x_cortex.h"
#include "et6x_crg.h"
#include "system_et6x.h"


/**
 * @addtogroup ET3101_Driver
 * @{
 */

/**
 * @defgroup MISC MISC
 * @brief Misc Driver Library
 * @{
 */
static volatile uint32_t SYSCNT_clk = 12500000;

/*  ==============================================================================
 ##### Syscnt #####
 #####============================================================================== */

/**
 * @brief set counter value of SYSCNT
 */
void SYSCNT_setValue(uint64_t SyscntValue)
{
    CLEAR_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk);
    /* low 32 bit */
    WRITE_REG(SYSCNT_CTRL->CNTCVL, (uint32_t)(0xFFFFFFFF & SyscntValue));
    /* high 32 bit */
    WRITE_REG(SYSCNT_CTRL->CNTCVU, (uint32_t)((((uint64_t)0xFFFFFFFF << 32) & SyscntValue) >> 32));
    SET_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk);
}

/**
 * @brief set halt mode of SYSCNT when debug
 */
void SYSCNT_enableDebugHalt(void)
{
    SET_BIT(SYSC->SCNT, SYSC_SCNT_HALT_MODE_EN_Msk);
    SET_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_HDBG_Msk);
}

/**
 * @brief unset halt mode of SYSCNT when debug
 */
void SYSCNT_disableDebugHalt(void)
{
    CLEAR_BIT(SYSC->SCNT, SYSC_SCNT_HALT_MODE_EN_Msk);
    CLEAR_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_HDBG_Msk);
}

/**
 * @brief Get Debug halt status
 *
 * @return Actual CNTSR.DBGH status, not the configured CNTCR.HDBG policy.
 */
bool SYSCNT_getDebugHaltStatus(void)
{
    if (SYSCNT_CTRL->CNTSR & SYSCNT_CTRL_CNTSR_DBGH_Msk)
    {
        return true;
    }
    return false;
}

/**
 * @brief Get current counter value from SYSCNT RO region
 *
 * @return current counter value in uint64
 */
uint64_t SYSCNT_getCurrentVal(void)
{
    return ((uint64_t)SYSCNT_RO->CNTCVU << 32) | SYSCNT_RO->CNTCVL;
}

/**
 * @brief Start the SYSCNT counter
 *
 * This function initializes the SYSCNT counter and starts it.
 *
 */
void SYSCNT_start(void)
{
//    SYSCNT_clk = CRG_getSYSCNTClock();
    WRITE_REG(SYSCNT_CTRL->CNTFID0, SYSCNT_clk);
    SYSCNT_setValue(0);
    /* enable syscnt */
    SET_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk);
}

/**
 * @brief stop syscnt, count will not increased
 *
 */
void SYSCNT_stop(void)
{
    CLEAR_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk);
}

/**
 * @brief The time delay function of syscnt, in milliseconds
 *
 * @param ms millisecond value
 *
 */
void SYSCNT_delay(uint32_t ms)
{
    uint64_t start;
    uint64_t ref;

    SYSCNT_setValue(0);
    start = SYSCNT_getCurrentVal();
    ref   = ((uint64_t)SYSCNT_clk / 1000) * ms;
    while (SYSCNT_getCurrentVal() - start < ref);
}

#if defined(__ICCARM__)
/* IAR */
#pragma optimize=none
void arm_cm_delay_asm(uint32_t delay)
{
    __asm volatile (
        "loop:              \n"
        "    subs r0, r0, #1\n"
        "    cmp r0, #0     \n"
        "    bne loop       \n"
        :
        : "r" (delay)
        : "r0", "cc"
        );
}

#elif defined(__CC_ARM)
/* MDK ARMCC*/
#pragma push
#pragma O0
__ASM void arm_cm_delay_asm(uint32_t delay)
{
    subs r0, # 1
    // cppcheck-suppress uninitvar
    cmp r0, # 0
    bne arm_cm_delay_asm
    bx lr
}

#pragma pop

#elif defined(__ARMCC_VERSION) && (__ARMCC_VERSION >= 6010050)
/* ARM Clang */
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-parameter"
void arm_cm_delay_asm(uint32_t delay) __attribute__((optnone))
{
loop:
    __ASM goto volatile (
        " subs r0, r0, #1      \n"
        " cmp r0, #0      \n"
        " bne %l[loop]    \n"
        :                                         /* Outputs */
        :                                         /* Inputs */
        : "r0", "r1", "ip", "lr", "memory", "cc"  /* Clobbers */
        : loop);
}

#pragma clang diagnostic pop

#elif defined(__GNUC__)
/* GCC */
#pragma GCC push_options
#pragma GCC optimize ("O0")
void arm_cm_delay_asm(uint32_t delay)
{
loop:
    __ASM goto volatile (
        " subs r0, r0, #1      \n"
        " cmp r0, #0      \n"
        " bne %l[loop]    \n"
        :                                         /* Outputs */
        :                                         /* Inputs */
        : "r0", "r1", "ip", "lr", "memory", "cc"  /* Clobbers */
        : loop);
}

#pragma GCC pop_options

#else
#error "Unsupported compiler"
#endif

/**
 * @brief delay function implementation by CoreSight DWT
 *
 * @param us
 * @attention before using this function, call SystemCoreClockUpdate() before
 */
void DWT_delay_us(uint32_t us)
{
    /* Covert microseconds to CPU ticks */
    uint64_t ticks = (uint64_t)((uint64_t)(us) * SystemCoreClock) / 1000000U;

    /* Make sure the ticks cannot over the max supported range */
    assert_param(ticks <= UINT32_MAX);

#if (__CM_CMSIS_VERSION >= 0x60000) /* CMSIS above 6.0.0 */
    DCB->DEMCR |= DCB_DEMCR_TRCENA_Msk;
#else
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
#endif
    /* Cycle counter not supported on this device. */
    assert_param(!(DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk));

    /* Clear the cycle counter */
    DWT->CYCCNT = 0U;
    /* Enable the cycle counter */
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    while (DWT->CYCCNT < ticks);

    /* Disable the cycle counter */
    DWT->CTRL &= ~DWT_CTRL_CYCCNTENA_Msk;
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/

/* Only enable bits borrowed by this diagnostic are restored on release. */
static uint8_t syscnt_test_reference_owned;
static uint32_t syscnt_test_saved_trace_enable;
static uint32_t syscnt_test_saved_cycle_enable;

/**
 * @brief Change EN without changing the count or frequency identification.
 * @param[in] enabled Boolean counter enable.
 * @return DRV_OK or DRV_PARAM_ERR for a non-Boolean input.
 */
DRV_Status SYSCNT_testSetEnabled(uint8_t enabled)
{
    if (enabled > 1u)
    {
        return DRV_PARAM_ERR;
    }

    MODIFY_REG(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk,
               enabled ? SYSCNT_CTRL_CNTCR_EN_Msk : 0u);
    return DRV_OK;
}

/**
 * @brief Load both count words while stopped and leave the counter stopped.
 * @param[in] value Full 64-bit counter value.
 * @return DRV_BUSY if EN is set, otherwise DRV_OK.
 * @note The low word is staged before the upper-word write commits the load.
 */
DRV_Status SYSCNT_testLoadStopped(uint64_t value)
{
    if (READ_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk) != 0u)
    {
        return DRV_BUSY;
    }

    WRITE_REG(SYSCNT_CTRL->CNTCVL, (uint32_t)value);
    WRITE_REG(SYSCNT_CTRL->CNTCVU, (uint32_t)(value >> SYSCNT_TEST_WORD_BITS));
    return DRV_OK;
}

/**
 * @brief Read a coherent 64-bit value from either counter window.
 * @param[in] view Control or read-only register view.
 * @param[out] value Updated only after matching high-word reads.
 * @return DRV_OK, DRV_PARAM_ERR, or DRV_BUSY when all bounded attempts tear.
 */
DRV_Status SYSCNT_testReadCount(SYSCNT_TestView view, uint64_t *value)
{
    uint32_t high_before;
    uint32_t low;
    uint32_t high_after;
    uint32_t attempt;

    if ((value == NULL) ||
        ((view != SYSCNT_TEST_VIEW_CONTROL) && (view != SYSCNT_TEST_VIEW_READ)))
    {
        return DRV_PARAM_ERR;
    }

    /* Volatile high/low/high loads detect a carry between separate bus reads. */
    for (attempt = 0u; attempt < SYSCNT_TEST_READ_ATTEMPTS; ++attempt)
    {
        if (view == SYSCNT_TEST_VIEW_CONTROL)
        {
            high_before = READ_REG(SYSCNT_CTRL->CNTCVU);
            low = READ_REG(SYSCNT_CTRL->CNTCVL);
            high_after = READ_REG(SYSCNT_CTRL->CNTCVU);
        }
        else
        {
            high_before = READ_REG(SYSCNT_RO->CNTCVU);
            low = READ_REG(SYSCNT_RO->CNTCVL);
            high_after = READ_REG(SYSCNT_RO->CNTCVU);
        }

        if (high_before == high_after)
        {
            *value = ((uint64_t)high_after << SYSCNT_TEST_WORD_BITS) | low;
            return DRV_OK;
        }
    }

    return DRV_BUSY;
}

/**
 * @brief Read configured policy, actual debug halt status and frequency ID.
 * @param[out] control Raw field snapshot; the frequency ID is not a measurement.
 * @return DRV_OK or DRV_PARAM_ERR for a null output.
 */
DRV_Status SYSCNT_testGetControl(SYSCNT_TestControl *control)
{
    uint32_t value;

    if (control == NULL)
    {
        return DRV_PARAM_ERR;
    }

    value = READ_REG(SYSCNT_CTRL->CNTCR);
    control->enabled = (value & SYSCNT_CTRL_CNTCR_EN_Msk) != 0u;
    control->halt_enabled = (value & SYSCNT_CTRL_CNTCR_HDBG_Msk) != 0u;
    control->debug_halted = READ_BIT(SYSCNT_CTRL->CNTSR, SYSCNT_CTRL_CNTSR_DBGH_Msk) != 0u;
    control->frequency_id_hz = READ_REG(SYSCNT_CTRL->CNTFID0);
    return DRV_OK;
}

/**
 * @brief Set only SYSCNT's HDBG policy; system halt routing is caller-owned.
 * @param[in] enabled Boolean pause-on-debug-halt policy.
 * @return DRV_OK or DRV_PARAM_ERR for a non-Boolean input.
 */
DRV_Status SYSCNT_testSetHaltPolicy(uint8_t enabled)
{
    if (enabled > 1u)
    {
        return DRV_PARAM_ERR;
    }

    MODIFY_REG(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_HDBG_Msk,
               enabled ? SYSCNT_CTRL_CNTCR_HDBG_Msk : 0u);
    return DRV_OK;
}

/**
 * @brief Write CNTFID0 while stopped without changing the physical clock.
 * @param[in] frequency_hz Nonzero frequency identification in Hz.
 * @return DRV_PARAM_ERR for zero, DRV_BUSY while running, otherwise DRV_OK.
 */
DRV_Status SYSCNT_testSetFrequencyId(uint32_t frequency_hz)
{
    if (frequency_hz == 0u)
    {
        return DRV_PARAM_ERR;
    }

    if (READ_BIT(SYSCNT_CTRL->CNTCR, SYSCNT_CTRL_CNTCR_EN_Msk) != 0u)
    {
        return DRV_BUSY;
    }

    WRITE_REG(SYSCNT_CTRL->CNTFID0, frequency_hz);
    return DRV_OK;
}

/**
 * @brief Acquire/release a free-running DWT reference without clearing CYCCNT.
 * @param[in] enabled Boolean acquisition request; repeated calls are idempotent.
 * @return DRV_OK, DRV_PARAM_ERR, or DRV_ERROR if cycle counting is unsupported.
 * @note Serialized diagnostics only. Other code must not reconfigure DWT during ownership.
 */
DRV_Status SYSCNT_testSetReferenceEnabled(uint8_t enabled)
{
    if (enabled > 1u)
    {
        return DRV_PARAM_ERR;
    }

    if (enabled == syscnt_test_reference_owned)
    {
        return DRV_OK;
    }

    if (enabled != 0u)
    {
        syscnt_test_saved_trace_enable = READ_BIT(CoreDebug->DEMCR, CoreDebug_DEMCR_TRCENA_Msk);
        SET_BIT(CoreDebug->DEMCR, CoreDebug_DEMCR_TRCENA_Msk);
        __DSB();
        __ISB();
        if (READ_BIT(DWT->CTRL, DWT_CTRL_NOCYCCNT_Msk) != 0u)
        {
            MODIFY_REG(CoreDebug->DEMCR, CoreDebug_DEMCR_TRCENA_Msk, syscnt_test_saved_trace_enable);
            return DRV_ERROR;
        }

        syscnt_test_saved_cycle_enable = READ_BIT(DWT->CTRL, DWT_CTRL_CYCCNTENA_Msk);
        SET_BIT(DWT->CTRL, DWT_CTRL_CYCCNTENA_Msk);
    }
    else
    {
        MODIFY_REG(DWT->CTRL, DWT_CTRL_CYCCNTENA_Msk, syscnt_test_saved_cycle_enable);
        MODIFY_REG(CoreDebug->DEMCR, CoreDebug_DEMCR_TRCENA_Msk, syscnt_test_saved_trace_enable);
    }

    syscnt_test_reference_owned = enabled;
    return DRV_OK;
}

/**
 * @brief Bracket one coherent SYSCNT read with two independent DWT reads.
 * @param[out] before Reference count before the SYSCNT read.
 * @param[out] count Coherent SYSCNT read-view count.
 * @param[out] after Reference count after the SYSCNT read.
 * @return DRV_OK, DRV_PARAM_ERR or DRV_BUSY if reference is not running/read tears.
 * @note No wait, reset or time conversion; PC owns interval and pass/fail decisions.
 */
DRV_Status SYSCNT_testSampleReference(uint32_t *before, uint64_t *count, uint32_t *after)
{
    uint32_t start;
    uint64_t value;
    DRV_Status status;

    if ((before == NULL) || (count == NULL) || (after == NULL))
    {
        return DRV_PARAM_ERR;
    }

    if ((syscnt_test_reference_owned == 0u) ||
        (READ_BIT(DWT->CTRL, DWT_CTRL_CYCCNTENA_Msk) == 0u) ||
        (READ_BIT(CoreDebug->DEMCR, CoreDebug_DEMCR_TRCENA_Msk) == 0u))
    {
        return DRV_BUSY;
    }

    start = READ_REG(DWT->CYCCNT);
    status = SYSCNT_testReadCount(SYSCNT_TEST_VIEW_READ, &value);
    if (status != DRV_OK)
    {
        return status;
    }

    *after = READ_REG(DWT->CYCCNT);
    *before = start;
    *count = value;
    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/
#endif
