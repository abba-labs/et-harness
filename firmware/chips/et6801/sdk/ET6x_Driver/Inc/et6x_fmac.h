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

#ifndef __ET6X_FMAC_H
#define __ET6X_FMAC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup FMAC
 * @{
 */

#define FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK                   FMAC_SR_Y_EMPTY_RPT_Msk
#define FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK                   FMAC_SR_X1_FULL_RPT_Msk
#define FMAC_STS_X1_BUFF_IS_OVERFLOW_FLAG_MASK               FMAC_SR_X1_OVFL_RPT_Msk
#define FMAC_STS_Y_BUFF_IS_UNDERFLOW_FLAG_MASK               FMAC_SR_Y_UNFL_RPT_Msk
#define FMAC_STS_ACCUMULATOR_DATA_IS_SAT_FLAG_MASK           FMAC_SR_SAT_RPT_Msk
#define FMAC_STS_OUTPUT_IS_NEGATIVE_WITH_OFFSET_FLAG_MASK    FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk

#define FMAC_IT_X1_BUFF_REQ_IT_MASK                          (1U << 0U)
#define FMAC_IT_Y_BUFF_REQ_IT_MASK                           (1U << 1U)
#define FMAC_IT_FIR_IIR_SAT_IT_MASK                          (1U << 2U)
#define FMAC_IT_X1_BUFF_OVERFLOW_IT_MASK                     (1U << 3U)
#define FMAC_IT_Y_BUFF_UNDERFLOW_IT_MASK                     (1U << 4U)
#define FMAC_IT_P_PARAM_ERR_IT_MASK                          (1U << 5U)
#define FMAC_IT_Q_PARAM_ERR_IT_MASK                          (1U << 6U)
#define FMAC_IT_R_PARAM_ERR_IT_MASK                          (1U << 7U)
#define FMAC_IT_X1_BUFF_LOAD_ERR_IT_MASK                     (1U << 8U)
#define FMAC_IT_X2_BUFF_LOAD_ERR_IT_MASK                     (1U << 9U)
#define FMAC_IT_Y_BUFF_STORE_ERR_IT_MASK                     (1U << 10U)

typedef enum
{
    FMAC_TRHD_1,
    FMAC_TRHD_2,
    FMAC_TRHD_4,
    FMAC_TRHD_8
} FMAC_BuffFIFOTrhd;

typedef enum
{
    FMAC_NO_OFFSET_AND_SAT,
    FMAC_ADD_OFFSET_AND_SAT_TO_12BIT,
    FMAC_ADD_OFFSET_AND_SAT_TO_16BIT
} FMAC_OutputDataMode;

typedef enum
{
    FMAC_LEFT_SHIFT_8,
    FMAC_LEFT_SHIFT_7,
    FMAC_LEFT_SHIFT_6,
    FMAC_LEFT_SHIFT_5,
    FMAC_LEFT_SHIFT_4,
    FMAC_LEFT_SHIFT_3,
    FMAC_LEFT_SHIFT_2,
    FMAC_LEFT_SHIFT_1,
    FMAC_NO_SHIFT,
    FMAC_RIGHT_SHIFT_1,
    FMAC_RIGHT_SHIFT_2,
    FMAC_RIGHT_SHIFT_3,
    FMAC_RIGHT_SHIFT_4,
    FMAC_RIGHT_SHIFT_5,
    FMAC_RIGHT_SHIFT_6,
    FMAC_RIGHT_SHIFT_7,
    FMAC_RIGHT_SHIFT_8
} FMAC_OutputDataShift;

typedef struct __PACKED
{
    uint8_t              X1_BuffBase;
    uint8_t              X1_BuffSize;
    FMAC_BuffFIFOTrhd    X1_BuffFIFOTrhd;
    uint8_t              X2_BuffBase;
    uint8_t              X2_BuffSize;
    uint8_t              Y_BuffBase;
    uint8_t              Y_BuffSize;
    FMAC_BuffFIFOTrhd    Y_BuffFIFOTrhd;
    ControlStatus        accumulatorWrapEn;
    FMAC_OutputDataMode  outputDataMode;
    ControlStatus        DMADataReadEn;
    ControlStatus        DMADataWriteEn;
    ControlStatus        clipEn;
    uint16_t             outputDataOffset;
    FMAC_OutputDataShift outputDataShift;
    ControlStatus        floatDataReadEn;
    ControlStatus        floatDataWriteEn;
} FMAC_ConfigParams;

void FMAC_config(FMAC_ConfigParams *config);
DRV_Status FMAC_loadX1Buff(int16_t *pInputData, uint32_t *pOutoutDataNum, uint8_t maxDataNum, uint32_t timeout);
DRV_Status FMAC_loadX2Buff(int16_t *pInputData, uint8_t dataNum, uint32_t timeout);
DRV_Status FMAC_IIR_loadX2Buff(int16_t *pInputCoeffA, uint8_t coeffANum, int16_t *pInputCoeffB,
                               uint8_t coeffBNum, uint32_t timeout);
DRV_Status FMAC_loadYBuff(int16_t *pInputData, uint8_t dataNum, uint32_t timeout);
DRV_Status FMAC_FIR_convolutionStart(int16_t *pInputData, int16_t *pOutoutData, uint32_t dataNum,
                                     uint32_t timeout);
DRV_Status FMAC_FIR_convolutionInterruptDMA(void);
DRV_Status FMAC_IIR_convolutionStart(int16_t *pInputData, int16_t *pOutoutData, uint8_t numStages, uint32_t dataNum,
                                     uint32_t timeout);
DRV_Status FMAC_IIR_convolutionInterruptDMA(uint8_t numStages);
DRV_Status FMAC_convolutionAppend(int16_t *pInputData, int16_t *pOutoutData, uint32_t dataNum, uint32_t timeout);

DRV_Status FMAC_loadX1BuffFloat(float *pInputData, uint32_t *pInputDataNum, uint8_t maxDataNum, uint32_t timeout);
DRV_Status FMAC_loadX2BuffFloat(float *pInputData, uint8_t dataNum, uint32_t timeout);
DRV_Status FMAC_IIR_loadX2BuffFloat(float *pInputCoeffA, uint8_t coeffANum, float *pInputCoeffB, uint8_t coeffBNum,
                                    uint32_t timeout);
DRV_Status FMAC_loadYBuffFloat(float *pInputData, uint8_t dataNum, uint32_t timeout);
DRV_Status FMAC_FIR_convolutionStartFloat(float *pInputData, float *pOutoutData, uint32_t dataNum, uint32_t timeout);
DRV_Status FMAC_IIR_convolutionStartFloat(float *pInputData, float *pOutoutData, uint8_t numStages, uint32_t dataNum,
                                          uint32_t timeout);
DRV_Status FMAC_convolutionAppendFloat(float *pInputData, float *pOutoutData, uint32_t dataNum, uint32_t timeout);
void FMAC_setFIFODataFloat(float data);
float FMAC_getFIFODataFloat(void);

void FMAC_setFIFOData(int16_t data);
int16_t FMAC_getFIFOData(void);
void FMAC_clearBuffZone(void);
bool FMAC_isFuncBusy(void);
uint8_t FMAC_getX1BuffSpareSpaceNum(void);
uint8_t FMAC_getYBuffUnreadDataNum(void);
uint32_t FMAC_getStatus(void);
void FMAC_enableInterrupt(uint32_t interruptMasks);
void FMAC_disableInterrupt(uint32_t interruptMasks);
void FMAC_forceInterrupt(uint32_t interruptMasks);
void FMAC_clearInterruptStatus(uint32_t interruptMasks);
uint32_t FMAC_getInterruptStatusRaw(void);
uint32_t FMAC_getInterruptStatus(void);
void FMAC_setInterruptMask(uint32_t interruptMasks);
void FMAC_clearInterruptMask(uint32_t interruptMasks);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

/******************** TEST DRIVER EXTENSION BEGIN ********************/

/** ET6801 FMAC configuration readback used only by validation firmware. */
typedef struct
{
    uint8_t x1Base;
    uint8_t x1Size;
    uint8_t x1FullWatermark;
    uint8_t x2Base;
    uint8_t x2Size;
    uint8_t yBase;
    uint8_t ySize;
    uint8_t yEmptyWatermark;
    uint8_t accumulatorWrapEnable;
    uint8_t outputDataMode;
    uint8_t dmaReadEnable;
    uint8_t dmaWriteEnable;
    uint8_t clipEnable;
    uint8_t floatInputEnable;
    uint8_t floatOutputEnable;
    uint8_t outputDataShift;
    uint16_t outputDataOffset;
} FMAC_TestConfigSnapshot;

/** Stop the active FMAC function by clearing PARAM.ENABLE. */
DRV_Status FMAC_testStopFunction(void);
/** Clear dynamic FMAC state and software-clearable conversion reports. */
DRV_Status FMAC_testClearDynamicState(uint32_t timeout);
/** Start one raw FMAC function with explicit P/Q parameters. */
DRV_Status FMAC_testStartFunction(uint8_t function, uint8_t pValue, uint8_t qValue);
/** Read the complete validation-relevant FMAC configuration. */
DRV_Status FMAC_testGetConfigSnapshot(FMAC_TestConfigSnapshot *snapshot);
/** Return the complete FMAC status register without dropping report bits. */
uint32_t FMAC_testGetStatusRaw(void);
/** Set only the FMAC DMA request gates while the function is idle. */
DRV_Status FMAC_testSetDMARequests(ControlStatus inputEnable, ControlStatus outputEnable);
/** Load exact signed fixed-point items into X1 without delayed Full polling. */
DRV_Status FMAC_testLoadX1(const int16_t *data, uint8_t count, uint32_t timeout);
/** Load exact IEEE754 Float32 items into X1. */
DRV_Status FMAC_testLoadX1Float(const float *data, uint8_t count, uint32_t timeout);
/** Load exact signed fixed-point feedforward and feedback coefficient segments. */
DRV_Status FMAC_testLoadX2(const int16_t *feedforward, uint8_t feedforwardCount,
                           const int16_t *feedback, uint8_t feedbackCount, uint32_t timeout);
/** Load exact signed fixed-point items into Y. */
DRV_Status FMAC_testLoadY(const int16_t *data, uint8_t count, uint32_t timeout);
/** Load exact IEEE754 Float32 items into Y. */
DRV_Status FMAC_testLoadYFloat(const float *data, uint8_t count, uint32_t timeout);
/** Perform one unchecked raw FIFO write for a natural boundary stimulus. */
void FMAC_testWriteFIFOUnchecked(uint32_t value);
/** Perform one unchecked raw FIFO read for a natural boundary stimulus. */
uint32_t FMAC_testReadFIFOUnchecked(void);
/** Read the selected FMAC interrupt-enable bits. */
uint32_t FMAC_testGetInterruptEnable(void);
/** Read the selected FMAC interrupt-mask bits. */
uint32_t FMAC_testGetInterruptMask(void);
/** Process one bounded stream and return target-local DWT cycle evidence. */
DRV_Status FMAC_testProcessTimed(uint8_t function, uint8_t pValue, uint8_t qValue,
                                 const void *source, void *destination, uint16_t count,
                                 ControlStatus useFloat, uint32_t timeout,
                                 uint32_t *acceptedCount, uint32_t *readCount,
                                 uint32_t *elapsedCycles);

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

#endif /* __ET6X_FMAC_H */
