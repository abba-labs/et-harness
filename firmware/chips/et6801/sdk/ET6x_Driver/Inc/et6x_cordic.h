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

#ifndef __ET6X_CORDIC_H
#define __ET6X_CORDIC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET6801_Driver
 * @{
 */

/**
 * @addtogroup  CORDIC
 * @{
 */

/**
 * @brief CORIDC status emuminations
 *
 */
#define CORDIC_STS_PM_IN_PARAM2_ERROR         CORDIC_STATUS_RPT_WR_ARG2_ERROR_RPT_Msk
#define CORDIC_STS_CALCULATE_COMPLETE         CORDIC_STATUS_RPT_RRDY_FLG_RPT_Msk
#define CORDIC_STS_ARG_PARAM_OVERFLOW         CORDIC_STATUS_RPT_WR_NARGS_OVF_RPT_Msk

/**
 * @brief CORDIC interrput flags
 *
 */
#define CORDIC_INT_FLAG_PM_IN_PARAM2_ERROR    0x4U
#define CORDIC_INT_FLAG_CALCULATE_COMPLETE    0x2U
#define CORDIC_INT_FLAG_ARG_PARAM_OVERFLOW    0x1U

/**
 * @brief CORDIC RPT_CORDIC_FLOAT2FIXED status flags
 *
 */
#define CORDIC_FLOAT2FIXED_UNDERFLOW_RPT      0x1U
#define CORDIC_FLOAT2FIXED_OVERFLOW_RPT       0x2U

typedef enum
{
    CORDIC_FUNCTION_SIN_COS               = 0U,
    CORDIC_FUNCTION_PHASE_MODULUS         = 1U,
    CORDIC_FUNCTION_ARCTAN                = 2U,
    CORDIC_FUNCTION_HYPERBOLIC_SIN_COS    = 3U,
    CORDIC_FUNCTION_HYPERBOLIC_ARCTANGENT = 4U,
    CORDIC_FUNCTION_EXP                   = 5U,
    CORDIC_FUNCTION_NATURAL_LOGARITHM     = 6U,
    CORDIC_FUNCTION_SQUAREROOT            = 7U,
    CORDIC_FUNCTION_TAN                   = 8U
} CORDIC_MathFunc;

/**
 * @brief  CORDIC arguments type definition
 *
 */
typedef enum
{
    CORDIC_ARG_INDEX1 = 0U, /*!< argument 1*/
    CORDIC_ARG_INDEX2 = 1U  /*!< argument 2*/
} CORDIC_ArgIndexTypeDef;

/**
 * @brief CORDIC result type definition
 *
 */
typedef enum
{
    CORDIC_ARG_RES_NUM1 = 0U,
    CORDIC_ARG_RES_NUM2 = 1U
} CORDIC_ArgResNum;

/**
 * @brief CORDIC data format
 *
 */
typedef enum
{
    CORDIC_DATA_FORMAT_BIT16 = 0U,
    CORDIC_DATA_FORMAT_BIT32 = 1U
} CORDIC_DataFormat;

/**
 * @brief CORDIC data format
 *
 */
typedef enum
{
    CORDIC_DATA_INPUT_RANGE_NORMAL = 0U,
    CORDIC_DATA_INPUT_RANGE_2PI    = 1U
} CORDIC_DataMode;

/**
 * @brief CORDIC work mode
 *
 */
typedef enum
{
    CORDIC_WORK_MODE_INTERRUPT     = 0U,
    CORDIC_WORK_MODE_POLLING       = 1U,
    CORDIC_WORK_MODE_ZERO_OVERHEAD = 2U
} CORDIC_WorkMode;

/**
 * @brief scale select
 * not take affect when math functions are sin,cos,phase,modulus
 */
typedef enum
{
    CORDIC_SCALE_0 = 0U,
    CORDIC_SCALE_1 = 1U,
    CORDIC_SCALE_2 = 2U,
    CORDIC_SCALE_3 = 3U,
    CORDIC_SCALE_4 = 4U,
    CORDIC_SCALE_5 = 5U,
    CORDIC_SCALE_6 = 6U,
    CORDIC_SCALE_7 = 7U
} CORDIC_Scale;

/**
 * @brief CORDIC Precision in Cycles Number
 *
 */
typedef enum
{
    CORDIC_PRECISIO_1 = 0U,
    CORDIC_PRECISIO_2 = 1U,
    CORDIC_PRECISIO_3 = 2U,
    CORDIC_PRECISIO_4 = 3U,
    CORDIC_PRECISIO_5 = 4U,
    CORDIC_PRECISIO_6 = 5U,
    CORDIC_PRECISIO_7 = 6U,
    CORDIC_PRECISIO_8 = 7U
} CORDIC_Precision;

/**
 * @brief CORDIC parameats
 *
 */
typedef struct __PACKED
{
    CORDIC_Scale      scale;      /* 对余弦 正弦 相位 幅度不生效。表示对输入变量1的X 做除 2的n次方 */
    CORDIC_DataFormat argDataFormat;
    CORDIC_DataFormat resDataFormat;
    CORDIC_ArgResNum  numberRead_HSinCos;
    CORDIC_ArgResNum  numberRead_PM;
    CORDIC_ArgResNum  numberRead_SinCos;
    CORDIC_DataMode   dataMode;
    CORDIC_WorkMode   workMode;
    uint8_t           precision;      /* 迭代周期数，最大配置值为7，实际迭代周期数为 +1，迭代次数为周期数 * 3 */
    ControlStatus     floatDataEn;
} CORDIC_InitParams;

/**
 * @brief set sin and cos CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setSincosArg(uint32_t data)
{
    WRITE_REG(CORDIC->SINCOS_CAL, data);
}

/**
 * @brief set sin and cos CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setSincosFloatArg(float *data)
{
    WRITE_REG(CORDIC->SINCOS_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set phase and modulus CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setPhaseModulusArg(uint32_t data)
{
    WRITE_REG(CORDIC->PM_CAL, data);
}

/**
 * @brief set phase and modulus CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setPhaseModulusFloatArg(float *data)
{
    WRITE_REG(CORDIC->PM_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set arctan CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setArctanArg(uint32_t data)
{
    WRITE_REG(CORDIC->ARCTAN_CAL, data);
}

/**
 * @brief set arctan CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setArctanFloatArg(float *data)
{
    WRITE_REG(CORDIC->ARCTAN_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set hyperbolic sin and hyperbolic cos CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setHcosineArg(uint32_t data)
{
    WRITE_REG(CORDIC->HSINCOS_CAL, data);
}

/**
 * @brief set hyperbolic sin and hyperbolic cos CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setHcosineFloatArg(float *data)
{
    WRITE_REG(CORDIC->HSINCOS_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set hyperbolic arctan CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setHArctanArg(uint32_t data)
{
    WRITE_REG(CORDIC->HARCTAN_CAL, data);
}

/**
 * @brief set hyperbolic arctan CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setHArctanFloatArg(float *data)
{
    WRITE_REG(CORDIC->HARCTAN_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set e^x CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setExpArg(uint32_t data)
{
    WRITE_REG(CORDIC->EX_CAL, data);
}

/**
 * @brief set e^x CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setExpFloatArg(float *data)
{
    WRITE_REG(CORDIC->EX_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set ln CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setLogArg(uint32_t data)
{
    WRITE_REG(CORDIC->LN_CAL, data);
}

/**
 * @brief set ln CORIDC float parameters
 *
 * @param data  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setLogFloatArg(float *data)
{
    WRITE_REG(CORDIC->LN_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set sqrt CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setSqrtArg(uint32_t data)
{
    WRITE_REG(CORDIC->SQRT_CAL, data);
}

/**
 * @brief set sqrt CORIDC float parameters
 *
 * @param arg  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setSqrtFloatArg(float *data)
{
    WRITE_REG(CORDIC->SQRT_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief set tan CORIDC parameters
 *
 * @param data  argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setTanArg(uint32_t data)
{
    WRITE_REG(CORDIC->TAN_CAL, data);
}

/**
 * @brief set tan CORIDC float parameters
 *
 * @param arg  float argument value
 * @return * void
 */
__STATIC_INLINE void CORDIC_setTanFloatArg(float *data)
{
    WRITE_REG(CORDIC->TAN_CAL, *(volatile uint32_t *)data);
}

/**
 * @brief get CORIDC calculation result 1
 *
 * @return * uint32_t
 */
__STATIC_INLINE uint32_t CORDIC_getResult1(void)
{
    return READ_REG(CORDIC->RES1_RPT);
}

/**
 * @brief get CORIDC calculation float result 1
 *
 * @return * uint32_t
 */
__STATIC_INLINE float CORDIC_getFloatResult1(void)
{
    return *(volatile const float *)(&CORDIC->RES1_RPT);
}

/**
 * @brief get CORIDC calculation result 2
 *
 * @return * uint32_t
 */
__STATIC_INLINE uint32_t CORDIC_getResult2(void)
{
    return READ_REG(CORDIC->RES2_RPT);
}

/**
 * @brief get CORIDC calculation float result 2
 *
 * @return * uint32_t
 */
__STATIC_INLINE float CORDIC_getFloatResult2(void)
{
    return *(volatile const float *)(&CORDIC->RES2_RPT);
}

/**
 * @brief calculate CORIDC sin and cos int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param cos   int cosine result value
 * @param sin   int sine result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteSincos(int32_t data, int32_t *cos, int32_t *sin)
{
    __disable_irq();
    WRITE_REG(CORDIC->SINCOS_CAL, data);
    *cos = READ_REG(CORDIC->RES1_RPT);
    *sin = READ_REG(CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC sin and cos float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param cos   float cosine result value
 * @param sin   float sine result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateSincosFloat(float *data, float *cos, float *sin)
{
    __disable_irq();
    WRITE_REG(CORDIC->SINCOS_CAL, *(volatile uint32_t *)data);
    *cos = *(volatile const float *)(&CORDIC->RES1_RPT);
    *sin = *(volatile const float *)(&CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC phase and module int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param phase   int phase result value
 * @param module   int module result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calcultePM(int32_t data, int32_t *phase, int32_t *module)
{
    __disable_irq();
    WRITE_REG(CORDIC->SINCOS_CAL, data);
    *phase  = READ_REG(CORDIC->RES1_RPT);
    *module = READ_REG(CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC phase and module float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param phase   float phase result value
 * @param module   float module result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculatePMFloat(float *data, float *phase, float *module)
{
    __disable_irq();
    WRITE_REG(CORDIC->PM_CAL, *(volatile uint32_t *)data);
    *phase  = *(volatile const float *)(&CORDIC->RES1_RPT);
    *module = *(volatile const float *)(&CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC cosh and sinh int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param cosh   int cosh result value
 * @param sinh   int sinh result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteHcosine(int32_t data, int32_t *cosh, int32_t *sinh)
{
    __disable_irq();
    WRITE_REG(CORDIC->HSINCOS_CAL, data);
    *cosh = READ_REG(CORDIC->RES1_RPT);
    *sinh = READ_REG(CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC cosh and sinh float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param cosh   float cosh result value
 * @param sinh   float sinh result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateHcosineFloat(float *data, float *cosh, float *sinh)
{
    __disable_irq();
    WRITE_REG(CORDIC->HSINCOS_CAL, *(volatile uint32_t *)data);
    *cosh = *(volatile const float *)(&CORDIC->RES1_RPT);
    *sinh = *(volatile const float *)(&CORDIC->RES2_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC arctan int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param arctan   int arctan result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteArctan(int32_t data, int32_t *arctan)
{
    __disable_irq();
    WRITE_REG(CORDIC->ARCTAN_CAL, data);
    *arctan = READ_REG(CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC arctan float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param arctan   float arctan result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateArctanFloat(float *data, float *arctan)
{
    __disable_irq();
    WRITE_REG(CORDIC->ARCTAN_CAL, *(volatile uint32_t *)data);
    *arctan = *(volatile const float *)(&CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC exp int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param exp   int exp result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteExp(int32_t data, int32_t *exp)
{
    __disable_irq();
    WRITE_REG(CORDIC->EX_CAL, data);
    *exp = READ_REG(CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC exp float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param exp   float exp result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateExpFloat(float *data, float *exp)
{
    __disable_irq();
    WRITE_REG(CORDIC->EX_CAL, *(volatile uint32_t *)data);
    *exp = *(volatile const float *)(&CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC ln int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param ln   int ln result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteLn(int32_t data, int32_t *ln)
{
    __disable_irq();
    WRITE_REG(CORDIC->LN_CAL, data);
    *ln = READ_REG(CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC ln float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param ln   float ln result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateLnFloat(float *data, float *ln)
{
    __disable_irq();
    WRITE_REG(CORDIC->LN_CAL, *(volatile uint32_t *)data);
    *ln = *(volatile const float *)(&CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC sqrt int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param sqrt   int sqrt result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteSqrt(int32_t data, int32_t *sqrt)
{
    __disable_irq();
    WRITE_REG(CORDIC->SQRT_CAL, data);
    *sqrt = READ_REG(CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC sqrt float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param sqrt   float sqrt result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateSqrtFloat(float *data, float *sqrt)
{
    __disable_irq();
    WRITE_REG(CORDIC->SQRT_CAL, *(volatile uint32_t *)data);
    *sqrt = *(volatile const float *)(&CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC tan int results, only available when operating in the zero-mode.
 *
 * @param data  int argument value
 * @param arctanh   int arctanh result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculteArctanh(int32_t data, int32_t *arctanh)
{
    __disable_irq();
    WRITE_REG(CORDIC->HARCTAN_CAL, data);
    *arctanh = READ_REG(CORDIC->RES1_RPT);
    __enable_irq();
}

/**
 * @brief calculate CORIDC arctanh float results, only available when operating in the zero-mode.
 *
 * @param data  float argument value
 * @param arctanh   float arctanh result value
 * @return * void
 */
__STATIC_INLINE void CORDIC_calculateArctanhFloat(float *data, float *arctanh)
{
    __disable_irq();
    WRITE_REG(CORDIC->HARCTAN_CAL, *(volatile uint32_t *)data);
    *arctanh = *(volatile const float *)(&CORDIC->RES1_RPT);
    __enable_irq();
}

/* Initialize Functions */
void CORDIC_initStruct(CORDIC_InitParams *initParams);
void CORDIC_init(CORDIC_InitParams *initParams);

/* Argument Functions */
void CORDIC_setFloatArg(float *data, CORDIC_MathFunc function);
void CORDIC_setArg(uint32_t data, CORDIC_MathFunc function);

/* Status Functions */
uint32_t CORDIC_getFloat2FixedStatus(void);
void CORDIC_clearFloat2FixedStatus(uint32_t statusMasks);
uint32_t CORDIC_getStatus(void);
void CORDIC_clearStatus(uint32_t statusMasks);
bool CORIDC_IsRReady(void);
uint32_t CORDIC_getCurrentArgNum(void);

/* Interrupt Functions */
void CORDIC_enableInterrupt(uint32_t interruptFlagMask);
void CORDIC_disableInterrupt(uint32_t interruptFlagMask);
void CORDIC_setInterruptMask(uint32_t interruptFlagMask);
void CORDIC_clearInterruptMask(uint32_t interruptFlagMask);
void CORDIC_forceInterrupt(uint32_t interruptFlagMask);
void CORDIC_clearInterruptStatus(uint32_t interruptFlagMask);
uint32_t CORDIC_getInterruptStatusRaw(void);
uint32_t CORDIC_getInterruptStatus(void);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/**
 * @brief Execute one bounded raw CORDIC transaction in zero-overhead mode.
 * @param function Selected mathematical function.
 * @param pArguments One or two raw input words.
 * @param argumentCount Number of raw input words.
 * @param pPrimary Receives RES1 raw data.
 * @param pSecondary Receives RES2 raw data.
 * @return DRV_OK on success, or DRV_PARAM_ERR for invalid arguments.
 * @note The prior PRIMASK state is restored exactly after the atomic window.
 */
DRV_Status CORDIC_testExecuteZeroOverhead(CORDIC_MathFunc function,
                                          const uint32_t *pArguments,
                                          uint32_t argumentCount,
                                          uint32_t *pPrimary,
                                          uint32_t *pSecondary);

/**
 * @brief Execute one bounded CORDIC transaction and return target-local cycles.
 * @param function Selected mathematical function.
 * @param pArguments One or two raw input words.
 * @param argumentCount Number of raw input words.
 * @param timeout Bounded result-ready polling budget.
 * @param pPrimary Receives RES1 raw data.
 * @param pSecondary Receives RES2 raw data.
 * @param pElapsedCycles Receives target-local DWT cycles.
 * @return DRV_OK on success, or a Driver error when validation/timing fails.
 * @note DWT and PRIMASK state are restored exactly after the measurement.
 */
DRV_Status CORDIC_testExecuteTimed(CORDIC_MathFunc function,
                                   const uint32_t *pArguments,
                                   uint32_t argumentCount,
                                   uint32_t timeout,
                                   uint32_t *pPrimary,
                                   uint32_t *pSecondary,
                                   uint32_t *pElapsedCycles);

/********************* TEST DRIVER EXTENSION END *********************/

#endif

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif  /*__ET6X_CORDIC_H */
