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

/* includes -------------------------------------------------------------------*/
#include "et6x_stimer.h"

#include "et6x_xbar.h"

#define MAX_PRESCALER_VALUE    (0xFFFFUL)
#define MAX_PEROD_VALUE        (0xFFFFFFFFFFFFFFFFULL)

#define IS_STIM_ALL_PERIPH(STIMx) \
        ((STIMx == STIMER0) || (STIMx == STIMER1))


#define IS_LOAD_MODE(LOADMODE) \
        ((LOADMODE == STIMER_LOADMODE_IMMEDIATELY) || \
         (LOADMODE == STIMER_LOADMODE_SHADOW))

#define IS_WORK_MODE(WORKMODE) \
        ((WORKMODE == STIMER_EMULATIONMODE_STOPATZERO) || \
         (WORKMODE == STIMER_EMULATIONMODE_RUNFREE))

/*! Parameter validity check for prescaler */
#define IS_PRESCALER_VALUE(prescaler)    (((prescaler) <= MAX_PRESCALER_VALUE) && ((prescaler) >= 1))
#define IS_PERIOD_VALUE(period)          (((period) <= MAX_PEROD_VALUE) && ((period) >= 1))
#define IS_STIMER_INTFLAG(flag)          (((flag)&STIMER_INT_FLAGS_ALL) != 0)
#define IS_STIMER_STS_FLAG(stsFlags)     (((stsFlags)&STIMER_STS_ALL) != 0)
#define IS_STIMER_DMA_REQ(req)           \
        ((req == STIMER_DMA_REQ_COMPARE_EVT0) || \
         (req == STIMER_DMA_REQ_COMPARE_EVT1) || \
         (req == STIMER_DMA_REQ_COMPARE_EVT2) || \
         (req == STIMER_DMA_REQ_COMPARE_EVT3) || \
         (req == STIMER_DMA_REQ_COUNT_OVERFLOW))

#define IS_STIMER_COUNTER_COMPARE_MODULE(mode) \
        ((mode == STIMER_COUNTER_COMPARE_0) || \
         (mode == STIMER_COUNTER_COMPARE_1) || \
         (mode == STIMER_COUNTER_COMPARE_2) || \
         (mode == STIMER_COUNTER_COMPARE_3))



/**
 * @brief Sets the emulation mode for the STIMER.
 *
 * This function sets the emulation mode for the STIMER. The emulation mode
 * determines how the STIMER behaves in different scenarios, such as continuous
 * counting or pausing.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param mode The emulation mode to be set for the STIMER. This parameter should
 * be a value from the STIMER_EmulationMode enumeration.
 *
 */
void STIMER_setEmulationMode(STIMER_Type *STIMx, STIMER_EmulationMode mode)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_WORK_MODE(mode));

    /* STM_SET the work mode bit */
    MODIFY_REG(STIMx->STM_SET, STIMER0_STM_SET_STM_CONT_R_Msk, (uint32_t)mode << STIMER0_STM_SET_STM_CONT_R_Pos);
}

/**
 * @brief Sets the load mode for the STIMER.
 *
 * This function sets the load mode for the STIMER. The load mode determines
 * when the timer period value is loaded into the counter register.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param mode The load mode to be set. This parameter should be a value from the STIMER_LoadMode enumeration.
 *
 */
void STIMER_setLoadMode(STIMER_Type *STIMx, STIMER_LoadMode mode)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_LOAD_MODE(mode));

    if (STIMER_LOADMODE_IMMEDIATELY == mode)
    {
        SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLD_R_Msk);
        CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk);
    }
    else
    {
        CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLD_R_Msk);
        SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk);
    }
}

/**
 * @brief Enables the specified interrupt flags in the STIMER peripheral.
 *
 * This function sets the specified interrupt flags in the STM_INT_EN register.
 * By enabling these interrupt flags, the corresponding interrupt requests will be generated.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags to be enabled. This parameter should be a value from the STIMER_INT_XXX
 * enumeration.
 *        - STIMER_INT_COMPARE_EVT0
 *        - STIMER_INT_COMPARE_EVT1
 *        - STIMER_INT_COMPARE_EVT2
 *        - STIMER_INT_COMPARE_EVT3
 *        - STIMER_INT_COUNT_OVERFLOW
 *        - STIMER_INT_FLAGS_ALL
 *
 */
void STIMER_enableInterrupt(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    /* Enable the Interrupt */
    SET_BIT(STIMx->STM_INT_EN, intFlags);
}

/**
 * @brief Disables the specified interrupt flags in the STIMER peripheral.
 *
 * This function clears the specified interrupt flags in the STM_INT_EN register,
 * effectively disabling the corresponding interrupts.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags to be disabled. This parameter should be a value from the STIMER_INT_XXX
 * enumeration.
 *
 */
void STIMER_disableInterrupt(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    /* Disable the Interrupt */
    CLEAR_BIT(STIMx->STM_INT_EN, intFlags);
}

/**
 * @brief Sets the interrupt mask for the specified STIMER peripheral.
 *
 * This function unmasks the specified interrupt flags in the STM_INT_MASK register.
 * By unmasking these interrupt flags, the corresponding interrupts will be enabled.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags to be unmasked. This parameter should be a value from the STIMER_INT_XXX
 * enumeration.
 *
 */
void STIMER_setInterruptMask(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    /* unmask the Interrupt Mask */
    SET_BIT(STIMx->STM_INT_MASK, intFlags);
}

/**
 * @brief Clears the interrupt mask for the specified STIMER peripheral.
 *
 * This function unmasks the interrupt mask for the specified interrupt flags.
 * By unmasking the interrupt mask, the corresponding interrupt requests will be
 * processed by the STIMER.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags for which the interrupt mask needs to be cleared.
 *                  This parameter should be a value from the STIMER_INT_XXX enumeration.
 *
 */
void STIMER_clearInterruptMask(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    /* unmask the Interrupt Mask */
    CLEAR_BIT(STIMx->STM_INT_MASK, intFlags);
}

/**
 * @brief Returns the interrupt status for the specified interrupt flags.
 *
 * This function checks the interrupt status for the specified interrupt flags in the STIMER's interrupt status
 * register.
 * If the interrupt status for the specified flags is set, indicating an interrupt has occurred, the function returns
 * true.
 * Otherwise, it returns false.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags to check. This parameter should be a value from the STIMER_INT_XXX enumeration.
 *
 * @return bool
 *       \b true: if the interrupt status for the specified flags is set, indicating an interrupt has occurred.
 *       \b false: if the interrupt status for the specified flags is not set.
 */
bool STIMER_getInterruptStatus(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    return(READ_BIT(STIMx->STM_INT_STATUS_RPT, intFlags) == intFlags);
}

/**
 * @brief Returns the combined interrupt status for all STIMER interrupts.
 *
 * This function reads the interrupt status from the STM_INT_STATUS_RPT register
 * and returns the combined status of all STIMER interrupts. The status is masked
 * to only include the first 5 bits, as per the STIMER's documentation.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @return uint32_t The combined interrupt status for all STIMER interrupts.
 *         The returned value is masked to only include the first 5 bits.
 * @attention The function does not clear the interrupt status flags.
 */
uint32_t STIMER_getAllInterruptStatus(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    return(READ_REG(STIMx->STM_INT_STATUS_RPT) & BITS_WID_MASK(5));
}

/**
 * @brief Returns the raw interrupt status for the specified interrupt flags in the STIMER peripheral.
 *
 * This function checks the raw interrupt status for the specified interrupt flags in the STM_INT_RAW_RPT register.
 * If the interrupt status for the specified flags is set, indicating an interrupt has occurred, the function returns
 * true.
 * Otherwise, it returns false.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags for which the interrupt status needs to be checked. This parameter should be a
 * value from the STIMER_INT_XXX enumeration.
 *
 * @return true if the interrupt status for the specified flags is set, indicating an interrupt has occurred.
 * @return false if the interrupt status for the specified flags is not set.
 */
bool STIMER_getInterruptStatusRaw(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));

    return(READ_BIT(STIMx->STM_INT_RAW_RPT, intFlags) == intFlags);
}

/**
 * @brief Clears the interrupt status for the specified interrupt flags in the STIMER peripheral.
 *
 * This function clears the interrupt status for the specified interrupt flags in the STM_INT_CLR register.
 * By clearing these interrupt status flags, the corresponding interrupt requests are no longer pending.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags for which the interrupt status needs to be cleared. This parameter should be a
 * value from the STIMER_INT_XXX enumeration.
 *
 */
void STIMER_clearInterruptStatus(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));
    /* clear the Interrupt status */
    SET_BIT(STIMx->STM_INT_CLR, intFlags);
}

/**
 * @brief Forces the specified interrupt flags in the STIMER peripheral.
 *
 * This function sets the specified interrupt flags in the STM_INT_FORCE_IND register.
 * By forcing these interrupt flags, the corresponding interrupt requests are generated,
 * regardless of the interrupt status and mask settings.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param intFlags The interrupt flags to be forced. This parameter should be a value from the STIMER_INT_XXX
 * enumeration.
 *
 */
void STIMER_forceInterrupt(STIMER_Type *STIMx, uint32_t intFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_INTFLAG(intFlags));
    /* clear the Interrupt status */
    SET_BIT(STIMx->STM_INT_FORCE_IND, intFlags);
}

/**
 * @brief Selects the DMA request for the specified STIMER peripheral.
 *
 * This function sets the DMA request for the specified STIMER peripheral.
 * The DMA request is selected using the provided request parameter.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param request The DMA request to be selected. This parameter should be a value from the STIMER_DMA_REQ_XXX
 * enumeration.
 *
 */
void STIMER_selectDMARequest(STIMER_Type *STIMx, uint32_t request)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_DMA_REQ(request));
    /* clear the Interrupt status */
    WRITE_REG(STIMx->DMA_HD_MUX, request);
}

/**
 * @brief Enables the STIMER to pause counting when the CPU is halted.
 *
 * This function clears the STM_CPUHALT_MODE_R bit in the STM_SET register.
 * If this bit is cleared, the STIMER will pause counting when the CPU is halted.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 *
 */
void STIMER_enableCPUHalt(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_CPUHALT_MODE_R_Msk);
}

/**
 * @brief Loads a compare value into the specified counter compare module of the STIMER.
 *
 * This function sets the compare value for the specified counter compare module of the STIMER.
 * The compare value is loaded into the appropriate registers, and the compare operation is enabled.
 * The compare value is compared with the current timer count to generate an interrupt if they match.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param compModule The counter compare module to load the compare value into.
 * @param compCount The compare value to be loaded into the specified counter compare module.
 *
 */
void STIMER_loadCounterCompareValue(STIMER_Type *STIMx, STIMER_CounterCompareModule compModule, uint64_t compCount)
{
    uint32_t reg_base = 0;

    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_COUNTER_COMPARE_MODULE(compModule));

    reg_base = (uint32_t)&STIMx->STM_CPLD0 + (uint32_t)compModule * 16;

    /* STM_SET compare value */
    WRITE_REG(REG32(reg_base + 8), (uint32_t)compCount);
    WRITE_REG(REG32(reg_base + 4), (uint32_t)(compCount >> 32));
    /* load immediately */
    SET_BIT(REG32(reg_base), STIMER0_STM_CPLD0_STM_CPLD0_R_Msk);
}

/**
 * @brief Returns the status of a specified STIMER interrupt flag.
 *
 * This function checks the status of a specified interrupt flag in the STIMER's status register.
 * If the specified interrupt flag is set, indicating an interrupt has occurred, the function returns true.
 * Otherwise, it returns false.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param stsFlags The interrupt flag to check. This parameter should be a value from the STIMER_STS_XXX enumeration.
 * @return true if the specified interrupt flag is set, indicating an interrupt has occurred.
 * @return false if the specified interrupt flag is not set.
 */
bool STIMER_getStatus(STIMER_Type *STIMx, uint32_t stsFlags)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_STS_FLAG(stsFlags));
    return(READ_BIT(STIMx->STM_STATUS_RPT, stsFlags) == stsFlags);
}

/**
 * @brief Sets the period value for the STIMER.
 *
 * This function sets the period value for the STIMER. The period value determines
 * the duration for which the timer will count. The timer will reset to zero when
 * the count reaches the period value.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param period The period value to be set for the STIMER. The value should be a 64-bit unsigned integer.
 *               range[1~2^64-1]
 *
 */
void STIMER_setPeriod(STIMER_Type *STIMx, uint64_t period)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_PERIOD_VALUE(period));

    /* STM_SET the period value */
    period -= 1;
    WRITE_REG(STIMx->TCYC, (uint32_t)period);

    if (READ_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk) == 0)
    {
        SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLD_R_Msk);
        CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk);
    }
}

/**
 * @brief Sets the pre-scaler value for the STIMER.
 *
 * This function sets the pre-scaler value for the STIMER. The pre-scaler divides the
 * input clock frequency to produce the timer's count frequency. The pre-scaler value
 * should be set such that the timer's count frequency meets the desired requirements.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @param prescaler The pre-scaler value to be set. The value should be in the range of 1 to 65536.
 *
 * @attention The pre-scaler value is set by subtracting 1 from the provided value.
 *
 */
void STIMER_setPreScaler(STIMER_Type *STIMx, uint16_t prescaler)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_PRESCALER_VALUE(prescaler));

    /* STM_SET the prescaler value */
    WRITE_REG(STIMx->STM_PSCL, prescaler - 1);
}

/**
 * @brief Returns the current(latch) STIMER counter value.
 *
 * This function reads the current count value from the STIMER registers.
 * It locks the current count value to the register before reading it,
 * ensuring that the count value remains consistent during the read operation.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @return uint64_t The current count value of the STIMER.
 */
uint64_t STIMER_getTimerCountLatch(STIMER_Type *STIMx)
{
    uint64_t counter = 0;

    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    /* Lock the current count value to register */
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_CNTLK_R_Msk);

    /* Get the Counter Register value */
    counter = READ_REG(STIMx->CNT_RPT_LATCH);

    return counter;
}

/**
 * @brief Returns the lower 32 bits of the current STIMER counter value.
 *
 * This function reads the current(real time) count value from the STIMER low 32bit registers.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @return uint32_t The current count value of the STIMER.
 */
uint32_t STIMER_getTimerCount(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    /* Get the Counter Register value */
    return READ_REG(STIMx->CNT_RPT);
}

/**
 * @brief Resets the STIMER counter to zero.
 *
 * This function clears the STIMER counter by setting the STM_TCLR_R bit in the STM_SET register.
 * This action effectively resets the timer count to zero without stopping the timer.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not stop the timer. It only resets the counter to zero.
 */
void STIMER_resetTimerCount(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    /* Clear counter */
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLR_R_Msk);
}

/**
 * @brief Starts or restarts the STIMER count.
 *
 * This function sets the STM_TON bit in the STM_SET register, effectively
 * starting the STIMER count. It also clears the STM_THLT bit to ensure the
 * count continues.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not reset the timer counter.
 */
void STIMER_startTimer(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    /* STM_SET the ENABLE bit */
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TON_R_Msk);
    CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_THLT_R_Msk);
}

/**
 * @brief Pauses the STIMER count.
 *
 * This function sets the STM_THLT bit in the STM_SET register, effectively
 * pausing the STIMER count without stopping the timer.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not reset the timer counter.
 */
void STIMER_pauseTimer(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_THLT_R_Msk);
}

/**
 * @brief resume the STIMER count.
 *
 * This function clears the STM_THLT bit in the STM_SET register, effectively
 * resuming the STIMER count.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not reset the timer counter.
 */
void STIMER_resumeTimer(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_THLT_R_Msk);
}

/**
 * @brief Stops the STIMER count.
 *
 * This function clears the STM_TON bit in the STM_SET register, effectively
 * stopping the STIMER count.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not reset the timer counter.
 */
void STIMER_stopTimer(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TON_R_Msk);
}

/**
 * @brief Reloads the STIMER counter with the current period value.
 *
 * This function reloads the STIMER counter with the current period value.
 * It is useful when the timer needs to be reset to its original period without
 * stopping the timer.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @attention This function does not reset the timer counter. It only reloads
 * the counter with the current period value.
 */
void STIMER_reloadTimerCounter(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    CLEAR_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk);
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLD_R_Msk);
}

/**
 * @brief Returns the STIMER overflow status.
 *
 * This function checks the status of the STIMER_INT_COUNT_OVERFLOW interrupt.
 * If the interrupt is triggered, indicating an overflow has occurred, the function
 * returns true. Otherwise, it returns false.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 * @return true if an overflow has occurred, false otherwise.
 * @attention After calling this function, all status flags are cleared.
 */
bool STIMER_getTimerOverflowStatus(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    return STIMER_getStatus(STIMx, STIMER_INT_COUNT_OVERFLOW);
}

/**
 * @brief Disables the STIMER to pause counting when the CPU is halted.
 *
 * This function clears the STM_CPUHALT_MODE_R bit in the STM_SET register.
 * If this bit is cleared, the STIMER will continue counting when the CPU is halted.
 *
 * @param STIMx Pointer to the STIMER peripheral register structure.
 *
 */
void STIMER_disableCPUHalt(STIMER_Type *STIMx)
{
    /* Check the parameters */
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    /* set the STM_CPUHALT_MODE_R bit to disable CPU halt */
    SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_CPUHALT_MODE_R_Msk);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Set one ET6801 hardware-representable period without 64-bit truncation.
 *
 * @param STIMx STIMER module base.
 * @param period Period in timer ticks.
 * @return DRV_OK after writing the period and issuing immediate load when selected.
 * @return DRV_PARAM_ERR when period is zero.
 */
DRV_Status STIMER_testSetPeriod32(STIMER_Type *STIMx, uint32_t period)
{
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    if (period == 0U)
    {
        return DRV_PARAM_ERR;
    }

    WRITE_REG(STIMx->TCYC, period - 1U);

    if (READ_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_SHDW_UG_R_Msk) == 0U)
    {
        SET_BIT(STIMx->STM_SET, STIMER0_STM_SET_STM_TCLD_R_Msk);
    }

    return DRV_OK;
}

/**
 * @brief Load the correct 32-bit compare register for one ET6801 channel.
 *
 * @param STIMx STIMER module base.
 * @param compModule Compare channel.
 * @param compareValue Hardware compare threshold.
 * @return DRV_OK after the channel-specific load pulse is issued.
 */
DRV_Status STIMER_testLoadCompare32(STIMER_Type *STIMx,
                                    STIMER_CounterCompareModule compModule,
                                    uint32_t compareValue)
{
    volatile uint32_t *load_registers[] = {
        &STIMx->STM_CPLD0,
        &STIMx->STM_CPLD1,
        &STIMx->STM_CPLD2,
        &STIMx->STM_CPLD3,
    };
    volatile uint32_t *compare_registers[] = {
        &STIMx->OCWH0,
        &STIMx->OCWH1,
        &STIMx->OCWH2,
        &STIMx->OCWH3,
    };

    assert_param(IS_STIM_ALL_PERIPH(STIMx));
    assert_param(IS_STIMER_COUNTER_COMPARE_MODULE(compModule));

    WRITE_REG(*compare_registers[(uint32_t)compModule], compareValue);
    SET_BIT(*load_registers[(uint32_t)compModule], STIMER0_STM_CPLD0_STM_CPLD0_R_Msk);

    return DRV_OK;
}

/**
 * @brief Read the complete read-to-clear runtime status in one access.
 *
 * @param STIMx STIMER module base.
 * @return Raw STM_STATUS_RPT snapshot captured before hardware clears it.
 *
 * @attention The read consumes every asserted status bit. Callers must preserve
 *            the returned snapshot instead of reading individual bits again.
 */
uint32_t STIMER_testGetStatusSnapshot(STIMER_Type *STIMx)
{
    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    return READ_REG(STIMx->STM_STATUS_RPT);
}

/**
 * @brief Configure one ET6801 STIMER event pulse width.
 *
 * @param STIMx STIMER module base.
 * @param eventFlag One STIMER interrupt-source flag that identifies the event output.
 * @param widthCycles Pulse width in STIMER clock cycles, range 1 to 256.
 * @return DRV_OK after writing the selected width register.
 * @return DRV_PARAM_ERR when the source or width cannot be represented.
 *
 * @attention ET6801 stores pulse width as cycles minus one. This extension
 *            preserves the stable public cycle-count semantic at the Driver edge.
 */
DRV_Status STIMER_testSetEventPulseWidth(STIMER_Type *STIMx, uint32_t eventFlag,
                                         uint16_t widthCycles)
{
    volatile uint32_t *widthRegister;

    assert_param(IS_STIM_ALL_PERIPH(STIMx));

    if ((widthCycles < STIMER_TEST_EVENT_PULSE_WIDTH_MIN_CYCLES) ||
        (widthCycles > STIMER_TEST_EVENT_PULSE_WIDTH_MAX_CYCLES))
    {
        return DRV_PARAM_ERR;
    }

    switch (eventFlag)
    {
        case STIMER_INT_COMPARE_EVT0:
        {
            widthRegister = &STIMx->STM_OCWH0;
            break;
        }

        case STIMER_INT_COMPARE_EVT1:
        {
            widthRegister = &STIMx->STM_OCWH1;
            break;
        }

        case STIMER_INT_COMPARE_EVT2:
        {
            widthRegister = &STIMx->STM_OCWH2;
            break;
        }

        case STIMER_INT_COMPARE_EVT3:
        {
            widthRegister = &STIMx->STM_OCWH3;
            break;
        }

        case STIMER_INT_COUNT_OVERFLOW:
        {
            widthRegister = &STIMx->STM_OFWH;
            break;
        }

        default:
        {
            return DRV_PARAM_ERR;
        }
    }

    WRITE_REG(*widthRegister, (uint32_t)widthCycles - 1U);

    return DRV_OK;
}

/**
 * @brief Configure one ET6801 emergency source route for STIMER capture.
 *
 * The ET6801 SVD describes the ERG enable registers in XBAR and the captured
 * count in SYSC.  This test-only extension keeps that chip-specific pairing
 * below the public STIMER Wrap interface.
 */
DRV_Status STIMER_testConfigureEmergencyCapture(STIMER_Type *STIMx, uint8_t stimerIndex,
                                                uint8_t emergencySignal,
                                                uint32_t sourceMask)
{
    if ((STIMx != STIMER0) && (STIMx != STIMER1))
    {
        return DRV_PARAM_ERR;
    }

    if ((stimerIndex > 1U) || (emergencySignal > 1U) || (sourceMask == 0U) ||
        (sourceMask > XBAR_STM0ERG0_EN_STM0_ERGTRIG_0EN_Msk))
    {
        return DRV_PARAM_ERR;
    }

    if (((STIMx == STIMER0) && (stimerIndex != 0U)) ||
        ((STIMx == STIMER1) && (stimerIndex != 1U)))
    {
        return DRV_PARAM_ERR;
    }

    return XBAR_selectStimerEFSingalOutput((XBAR_STIM_IDX_TypeDef)stimerIndex,
                                           (XBAR_STIM_EF_SIG_TypeDef)emergencySignal,
                                           sourceMask);
}

/**
 * @brief Read one ET6801 read-only system emergency capture register.
 */
DRV_Status STIMER_testGetEmergencyCapture(uint8_t stimerIndex, uint32_t *count)
{
    if ((count == NULL) || (stimerIndex > 1U))
    {
        return DRV_PARAM_ERR;
    }

    if (stimerIndex == 0U)
    {
        *count = READ_REG(SYSC->STM0);
    }
    else
    {
        *count = READ_REG(SYSC->STM1);
    }

    return DRV_OK;
}

/**
 * @brief Disable one ET6801 emergency capture route.
 *
 * SYSC.STMx is read-only in the ET6801 SVD, therefore the only defined clear
 * action is disabling the corresponding XBAR route.  A subsequent accepted
 * trigger replaces the read-only captured value.
 */
DRV_Status STIMER_testClearEmergencyCapture(uint8_t stimerIndex, uint8_t emergencySignal)
{
    if ((stimerIndex > 1U) || (emergencySignal > 1U))
    {
        return DRV_PARAM_ERR;
    }

    XBAR_resetStimerEFSignalOutput((XBAR_STIM_IDX_TypeDef)stimerIndex,
                                    (XBAR_STIM_EF_SIG_TypeDef)emergencySignal);

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif
