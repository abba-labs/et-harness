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

/* include -----------------------------------------------------------*/
#include "et6x_cordic.h"

/* typedef -----------------------------------------------------------*/
/* macro -------------------------------------------------------------*/
/* variables ---------------------------------------------------------*/
/* function prototypes -----------------------------------------------*/
/* Private functions ---------------------------------------------------------*/

/**
 * @brief Initialize the CORDIC_InitParams structure with default values.
 *
 * @param initParams  CORDIC initialization parameters
 * @return * void
 */
void CORDIC_initStruct(CORDIC_InitParams *initParams)
{
    initParams->scale              = CORDIC_SCALE_0;
    initParams->argDataFormat      = CORDIC_DATA_FORMAT_BIT32;
    initParams->resDataFormat      = CORDIC_DATA_FORMAT_BIT32;
    initParams->numberRead_HSinCos = CORDIC_ARG_RES_NUM2;
    initParams->numberRead_PM      = CORDIC_ARG_RES_NUM2;
    initParams->numberRead_SinCos  = CORDIC_ARG_RES_NUM2;
    initParams->dataMode           = CORDIC_DATA_INPUT_RANGE_NORMAL;
    initParams->workMode           = CORDIC_WORK_MODE_INTERRUPT;
    initParams->precision          = CORDIC_PRECISIO_8;
    initParams->floatDataEn        = DISABLE;
}

/**
 * @brief Initialize the CORDIC module with the specified parameters
 *
 * @param initParams  CORDIC initialization parameters
 * @return * void
 */
void CORDIC_init(CORDIC_InitParams *initParams)
{
    MODIFY_REG(CORDIC->CTRL0, CORDIC_CTRL0_CORDIC_SCALE_Msk |
               CORDIC_CTRL0_CORDIC_ARGSIZE_Msk | CORDIC_CTRL0_CORDIC_RESSIZE_Msk |
               CORDIC_CTRL0_CORDIC_HSINCOS_NRES_Msk | CORDIC_CTRL0_CORDIC_PM_NRES_Msk |
               CORDIC_CTRL0_CORDIC_SINCOS_NRES_Msk | CORDIC_CTRL0_CORDIC_DMODE_Msk |
               CORDIC_CTRL0_CORDIC_WORK_MODE_Msk | CORDIC_CTRL0_CORDIC_NOI_Msk |
               CORDIC_CTRL0_CORDIC_FMODE_Msk,
               ((uint32_t)initParams->scale << CORDIC_CTRL0_CORDIC_SCALE_Pos) |
               ((uint32_t)initParams->argDataFormat << CORDIC_CTRL0_CORDIC_ARGSIZE_Pos) |
               ((uint32_t)initParams->resDataFormat << CORDIC_CTRL0_CORDIC_RESSIZE_Pos) |
               ((uint32_t)initParams->numberRead_HSinCos << CORDIC_CTRL0_CORDIC_HSINCOS_NRES_Pos) |
               ((uint32_t)initParams->numberRead_PM << CORDIC_CTRL0_CORDIC_PM_NRES_Pos) |
               ((uint32_t)initParams->numberRead_SinCos << CORDIC_CTRL0_CORDIC_SINCOS_NRES_Pos) |
               ((uint32_t)initParams->dataMode << CORDIC_CTRL0_CORDIC_DMODE_Pos) |
               ((uint32_t)initParams->workMode << CORDIC_CTRL0_CORDIC_WORK_MODE_Pos) |
               ((uint32_t)initParams->precision << CORDIC_CTRL0_CORDIC_NOI_Pos) |
               ((uint32_t)initParams->floatDataEn << CORDIC_CTRL0_CORDIC_FMODE_Pos));
}

/**
 * @brief Set floating-point parameters for all mathematical functions.
 *
 * @param data  float argument value
 * @param function  mathematical function
 * @return * void
 */
void CORDIC_setFloatArg(float *data, CORDIC_MathFunc function)
{
    uint32_t temp = *(volatile uint32_t *)data;

    switch (function)
    {
    case CORDIC_FUNCTION_SIN_COS:
        WRITE_REG(CORDIC->SINCOS_CAL, temp);
        break;

    case CORDIC_FUNCTION_PHASE_MODULUS:
        WRITE_REG(CORDIC->PM_CAL, temp);
        break;

    case CORDIC_FUNCTION_ARCTAN:
        WRITE_REG(CORDIC->ARCTAN_CAL, temp);
        break;

    case CORDIC_FUNCTION_HYPERBOLIC_SIN_COS:
        WRITE_REG(CORDIC->HSINCOS_CAL, temp);
        break;

    case CORDIC_FUNCTION_HYPERBOLIC_ARCTANGENT:
        WRITE_REG(CORDIC->HARCTAN_CAL, temp);
        break;

    case CORDIC_FUNCTION_EXP:
        WRITE_REG(CORDIC->EX_CAL, temp);
        break;

    case CORDIC_FUNCTION_NATURAL_LOGARITHM:
        WRITE_REG(CORDIC->LN_CAL, temp);
        break;

    case CORDIC_FUNCTION_SQUAREROOT:
        WRITE_REG(CORDIC->SQRT_CAL, temp);
        break;

    case CORDIC_FUNCTION_TAN:
        WRITE_REG(CORDIC->TAN_CAL, temp);
        break;
    }
}

/**
 * @brief Set integer arguments for all mathematical functions.
 *
 * @param data  argument value
 * @param function  mathematical function
 * @return * void
 */
void CORDIC_setArg(uint32_t data, CORDIC_MathFunc function)
{
    switch (function)
    {
    case CORDIC_FUNCTION_SIN_COS:
        WRITE_REG(CORDIC->SINCOS_CAL, data);
        break;

    case CORDIC_FUNCTION_PHASE_MODULUS:
        WRITE_REG(CORDIC->PM_CAL, data);
        break;

    case CORDIC_FUNCTION_ARCTAN:
        WRITE_REG(CORDIC->ARCTAN_CAL, data);
        break;

    case CORDIC_FUNCTION_HYPERBOLIC_SIN_COS:
        WRITE_REG(CORDIC->HSINCOS_CAL, data);
        break;

    case CORDIC_FUNCTION_HYPERBOLIC_ARCTANGENT:
        WRITE_REG(CORDIC->HARCTAN_CAL, data);
        break;

    case CORDIC_FUNCTION_EXP:
        WRITE_REG(CORDIC->EX_CAL, data);
        break;

    case CORDIC_FUNCTION_NATURAL_LOGARITHM:
        WRITE_REG(CORDIC->LN_CAL, data);
        break;

    case CORDIC_FUNCTION_SQUAREROOT:
        WRITE_REG(CORDIC->SQRT_CAL, data);
        break;

    case CORDIC_FUNCTION_TAN:
        WRITE_REG(CORDIC->TAN_CAL, data);
        break;
    }
}

/**
 * @brief Get CORDIC status
 *
 * @return * uint32_t This parameter can be a value of @ref CORDIC_STATUS_xxxx
 */
uint32_t CORDIC_getStatus(void)
{
    return READ_REG(CORDIC->STATUS_RPT);
}

/**
 * @brief clear CORDIC status
 *
 * @param statusMasks This parameter can be a value of @ref CORDIC_STATUS_xxxx
 * @return * void
 */
void CORDIC_clearStatus(uint32_t statusMasks)
{
    WRITE_REG(CORDIC->STATUS_RPT, statusMasks);
}

/**
 * @brief check whether CORDIC result is valid
 *
 * @return true  ready
 * @return false  not ready
 */
bool CORIDC_IsRReady(void)
{
    if (READ_BIT(CORDIC->STATUS_RPT, CORDIC_STATUS_RPT_RRDY_FLG_RPT_Msk))
    {
        /* clear flag */
        SET_BIT(CORDIC->STATUS_RPT, CORDIC_STATUS_RPT_RRDY_FLG_RPT_Msk);
        return true;
    }
    return false;
}

/**
 * @brief gets the count of the number of variables currently written
 *
 * @return * uint32_t
 */
uint32_t CORDIC_getCurrentArgNum(void)
{
    return READ_REG(CORDIC->WR_NARGS_CNT_RPT);
}

/**
 * @brief get CORDIC RPT_CORDIC_FLOAT2FIXED flow status
 *
 * @return * uint32_t This parameter can be a combination of @ref CORDIC_FLOAT2FIXED_xxxx
 */
uint32_t CORDIC_getFloat2FixedStatus(void)
{
    return READ_REG(CORDIC->RPT_CORDIC_FLOAT2FIXED);
}

/**
 * @brief clear CORDIC RPT_CORDIC_FLOAT2FIXED flow status
 *
 * @param statusMasks This parameter can be a combination of @ref CORDIC_FLOAT2FIXED_xxxx
 * @return * void
 */
void CORDIC_clearFloat2FixedStatus(uint32_t statusMasks)
{
    WRITE_REG(CORDIC->RPT_CORDIC_FLOAT2FIXED, statusMasks);
}

/**
 * @brief enable CORDIC interrupts
 *
 * @param interruptFlagMask
 * @return * void  This parameter can be a value of @ref CORDIC_INTERRUPT_FLAG_xxxx
 */
void CORDIC_enableInterrupt(uint32_t interruptFlagMask)
{
    SET_BIT(CORDIC->INT_EN, interruptFlagMask);
}

/**
 * @brief disable CORDIC interrupts
 *
 * @param interruptFlagMask
 * @return * void
 */
void CORDIC_disableInterrupt(uint32_t interruptFlagMask)
{
    CLEAR_BIT(CORDIC->INT_EN, interruptFlagMask);
}

/**
 * @brief set CORDIC interrupts mask
 *
 * @param interruptFlagMask
 * @return * void
 */
void CORDIC_setInterruptMask(uint32_t interruptFlagMask)
{
    SET_BIT(CORDIC->INT_MASK, interruptFlagMask);
}

/**
 * @brief clear CORDIC interrupts mask
 *
 * @param interruptFlagMask
 * @return * void
 */
void CORDIC_clearInterruptMask(uint32_t interruptFlagMask)
{
    CLEAR_BIT(CORDIC->INT_MASK, interruptFlagMask);
}

/**
 * @brief force trigger CORDIC interrupt
 *
 * @param interruptFlagMask
 * @return * void
 */
void CORDIC_forceInterrupt(uint32_t interruptFlagMask)
{
    SET_BIT(CORDIC->INT_FORCE_IND, interruptFlagMask);
}

/**
 * @brief clear CORDIC interrupts status
 *
 * @param interruptFlagMask
 * @return * void
 */
void CORDIC_clearInterruptStatus(uint32_t interruptFlagMask)
{
    SET_BIT(CORDIC->INT_CLR, interruptFlagMask);
}

/**
 * @brief get CORDIC interrupts raw status
 *
 * @return * uint32_t
 */
uint32_t CORDIC_getInterruptStatusRaw(void)
{
    return READ_REG(CORDIC->INT_RAW_RPT);
}

/**
 * @brief get CORDIC interrupts status
 *
 * @return * uint32_t
 */
uint32_t CORDIC_getInterruptStatus(void)
{
    return READ_REG(CORDIC->INT_STATUS_RPT);
}

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Execute one raw zero-overhead transaction while preserving PRIMASK.
 */
DRV_Status CORDIC_testExecuteZeroOverhead(CORDIC_MathFunc function,
                                          const uint32_t *pArguments,
                                          uint32_t argumentCount,
                                          uint32_t *pPrimary,
                                          uint32_t *pSecondary)
{
    uint32_t previousPrimask;

    if ((pArguments == NULL) || (pPrimary == NULL) || (pSecondary == NULL) ||
        (function > CORDIC_FUNCTION_TAN) || (argumentCount == 0U) ||
        (argumentCount > 2U) ||
        ((function == CORDIC_FUNCTION_PHASE_MODULUS) && (argumentCount != 2U)) ||
        ((function != CORDIC_FUNCTION_PHASE_MODULUS) && (argumentCount != 1U)))
    {
        return DRV_PARAM_ERR;
    }

    previousPrimask = __get_PRIMASK();
    __disable_irq();

    CORDIC_setArg(pArguments[0], function);

    if (argumentCount == 2U)
    {
        CORDIC_setArg(pArguments[1], function);
    }

    *pPrimary = CORDIC_getResult1();
    *pSecondary = CORDIC_getResult2();

    if (previousPrimask == 0U)
    {
        __enable_irq();
    }

    return DRV_OK;
}

/**
 * @brief Execute one bounded CORDIC transaction and return target-local cycles.
 *
 * The measured interval starts immediately before the first argument write and
 * ends after the result words are readable. Host transport and validation are
 * intentionally outside this Driver extension.
 */
DRV_Status CORDIC_testExecuteTimed(CORDIC_MathFunc function,
                                   const uint32_t *pArguments,
                                   uint32_t argumentCount,
                                   uint32_t timeout,
                                   uint32_t *pPrimary,
                                   uint32_t *pSecondary,
                                   uint32_t *pElapsedCycles)
{
    uint32_t previousDemcr;
    uint32_t previousDwtCtrl;
    uint32_t previousPrimask;
    uint32_t startCycles;
    uint32_t endCycles;

    if ((pArguments == NULL) || (pPrimary == NULL) || (pSecondary == NULL) ||
        (pElapsedCycles == NULL) || (timeout == 0U) || (function > CORDIC_FUNCTION_TAN) ||
        (argumentCount == 0U) || (argumentCount > 2U) ||
        ((function == CORDIC_FUNCTION_PHASE_MODULUS) && (argumentCount != 2U)) ||
        ((function != CORDIC_FUNCTION_PHASE_MODULUS) && (argumentCount != 1U)))
    {
        return DRV_PARAM_ERR;
    }

    if ((DWT->CTRL & DWT_CTRL_NOCYCCNT_Msk) != 0U)
    {
        return DRV_ERROR;
    }

    previousDemcr = CoreDebug->DEMCR;
    previousDwtCtrl = DWT->CTRL;
    previousPrimask = __get_PRIMASK();
    CoreDebug->DEMCR = previousDemcr | CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CTRL = previousDwtCtrl | DWT_CTRL_CYCCNTENA_Msk;
    __disable_irq();

    startCycles = DWT->CYCCNT;
    CORDIC_setArg(pArguments[0], function);
    if (argumentCount == 2U)
    {
        CORDIC_setArg(pArguments[1], function);
    }

    while ((READ_REG(CORDIC->STATUS_RPT) & CORDIC_STATUS_RPT_RRDY_FLG_RPT_Msk) == 0U)
    {
        if (--timeout == 0U)
        {
            DWT->CTRL = previousDwtCtrl;
            CoreDebug->DEMCR = previousDemcr;
            if (previousPrimask == 0U)
            {
                __enable_irq();
            }
            return DRV_TIMEOUT;
        }
    }

    *pPrimary = CORDIC_getResult1();
    *pSecondary = CORDIC_getResult2();
    endCycles = DWT->CYCCNT;
    *pElapsedCycles = endCycles - startCycles;

    DWT->CTRL = previousDwtCtrl;
    CoreDebug->DEMCR = previousDemcr;
    if (previousPrimask == 0U)
    {
        __enable_irq();
    }

    return DRV_OK;
}

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/******************* end  ***************************/
