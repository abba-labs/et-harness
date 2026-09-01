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
#ifndef __ET6X_SDFM_H
#define __ET6X_SDFM_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/**
 * @addtogroup  SDFM
 * @brief sigma delta filter module
 * @{
 */
//*****************************************************************************
//
// Defines for the API.
//
//*****************************************************************************


//*****************************************************************************
//
//! Values that can be passed to all functions as the \e filterNumber
//! parameter.
//
//*****************************************************************************
typedef enum
{
    SDFM_FILTER_1 = 0, //!< Digital filter 1
    SDFM_FILTER_2 = 1, //!< Digital filter 2
    SDFM_FILTER_3 = 2, //!< Digital filter 3
    SDFM_FILTER_4 = 3  //!< Digital filter 4
} SDFM_FilterNumber;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setFilterType(),
//! SDFM_setComparatorFilterType() as the \e filterType parameter.
//
//*****************************************************************************
typedef enum
{
    //! Digital filter with SincFast structure.
    SDFM_FILTER_SINC_FAST,
    //! Digital filter with Sinc1 structure
    SDFM_FILTER_SINC_1,
    //! Digital filter with Sinc3 structure.
    SDFM_FILTER_SINC_2,
    //! Digital filter with Sinc4 structure.
    SDFM_FILTER_SINC_3
} SDFM_FilterType;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setOutputDataFormat(),as the
//! \e dataFormat parameter.
//
//*****************************************************************************
typedef enum
{
    //! Filter output is in 16 bits 2's complement format.
    SDFM_DATA_FORMAT_16_BIT = 0,
    //! Filter output is in 32 bits 2's complement format.
    SDFM_DATA_FORMAT_32_BIT = 1
} SDFM_OutputDataFormat;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setDataReadyInterruptSource(),as the
//! \e dataReadySource parameter.
//
//*****************************************************************************
typedef enum
{
    //! Data ready interrupt source is direct (non -FIFO).
    SDFM_DATA_READY_SOURCE_DIRECT = 0,
    //! Data ready interrupt source is FIFO.
    SDFM_DATA_READY_SOURCE_FIFO   = 1
} SDFM_DataReadyInterruptSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setPWMSyncSource(),as the
//! \e syncSource parameter.
//
//*****************************************************************************
typedef enum
{
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM0  = 0,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM1  = 1,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM2  = 2,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM3  = 3,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM4  = 4,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM5  = 5,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM6  = 6,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM7  = 7,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM8  = 8,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM9  = 9,   //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM10 = 10,  //!< SDFM sync source is PWM ADC trigger
    SDFM_SYNC_SRPWM_ADC_TRIGGER_NUM11 = 11,  //!< SDFM sync source is PWM ADC trigger
} SDFM_PWMSyncSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setFIFOClearOnSyncMode(),as the
//! \e fifoClearSyncMode parameter.
//
//*****************************************************************************
typedef enum
{
    //! SDFM FIFO buffer is not cleared on Sync signal
    SDFM_FIFO_NOT_CLEARED_ON_SYNC = 0,
    //! SDFM FIFO buffer is cleared on Sync signal
    SDFM_FIFO_CLEARED_ON_SYNC     = 1
} SDFM_FIFOClearSyncMode;

//*****************************************************************************
//
//! Values that can be passed to SDFM_setWaitForSyncClearMode(),as the
//! \e syncClearMode parameter.
//
//*****************************************************************************
typedef enum
{
    //! Wait for sync cleared using software.
    SDFM_MANUAL_CLEAR_WAIT_FOR_SYNC = 0,
    //! Wait for sync cleared automatically
    SDFM_AUTO_CLEAR_WAIT_FOR_SYNC   = 1
} SDFM_WaitForSyncClearMode;

//*****************************************************************************
//
//! Values that can be passed to SDFM_selectCompEventSource() as the
//! \e compEventNum parameter.
//
//*****************************************************************************
typedef enum
{
    SDFM_COMP_EVENT_1, //!< Selects CEVT1
    SDFM_COMP_EVENT_2  //!< Selects CEVT2
} SDFM_CompEventNumber;

//*****************************************************************************
//
//! Values that can be passed to SDFM_selectCompEventSource() as the
//! \e compEventSource parameter.
//
//*****************************************************************************
typedef enum
{
    SDFM_COMP_EVENT_SRC_COMPH1    = 0, //!< COMPH1 event is the source
    SDFM_COMP_EVENT_SRC_COMPH1_L1 = 1, //!< Either of COMPH1 or COMPL1 event
                                       //!< can be the source
    SDFM_COMP_EVENT_SRC_COMPH2    = 2, //!< COMPH2 event is the source
    SDFM_COMP_EVENT_SRC_COMPH2_L2 = 3, //!< Either of COMPH2 or COMPL2 event
                                       //!< can be the source
    SDFM_COMP_EVENT_SRC_COMPL1    = 0, //!< COMPL1 event is the source
    SDFM_COMP_EVENT_SRC_COMPL2    = 2  //!< COMPL2 event is the source
} SDFM_CompEventSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_selectClockSource() as the \e clkSource
//! parameter.
//
//*****************************************************************************
typedef enum
{
    //! Source is respective channel clock
    SDFM_CLK_SOURCE_CHANNEL_CLK,
    //! Source is SD1 channel clock is the source
    SDFM_CLK_SOURCE_SD1_CLK
} SDFM_ClockSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_selectCompEventHighSource() as the
//! \e source parameter.
//
//*****************************************************************************
typedef enum
{
    //! Comparator event high source is unfiltered event
    SDFM_COMPHOUT_SOURCE_COMPHIN = 0x0,
    //! Comparator event high source is filtered event
    SDFM_COMPHOUT_SOURCE_FILTER  = 0x1
} SDFM_CompEventHighSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_selectCompEventLowSource() as the
//! \e source parameter.
//
//*****************************************************************************
typedef enum
{
    //! Comparator event low source is unfiltered event
    SDFM_COMPLOUT_SOURCE_COMPLIN = 0x0,
    //! Comparator event low source is filtered event
    SDFM_COMPLOUT_SOURCE_FILTER  = 0x1
} SDFM_CompEventLowSource;

//*****************************************************************************
//
//! Values that can be passed to SDFM_configCompEventLowFilter() &
//! SDFM_configCompEventHighFilter() as the \e filterNumber.
//
//*****************************************************************************
typedef struct
{
    uint16_t sampleWindow; //!< Sample window size
    uint16_t threshold;    //!< Majority voting threshold
    uint16_t clkPrescale;  //!< Sample clock pre-scale
} SDFM_CompEventFilterConfig;

//*****************************************************************************
//
// Values that can be passed to SDFM_enableInterrupt and SDFM_disableInterrupt
// as intFlags parameter
//
//*****************************************************************************
#define SDFM_IT_CEVT1_MASK                0x00000001
#define SDFM_IT_CEVT2_MASK                0x00000002
#define SDFM_IT_MODULATOR_FAILURE_MASK    0x00000004
#define SDFM_IT_FIFO_OVERFLOW_MASK        0x00000008
#define SDFM_IT_FIFO_WRITE_MASK           0x00000010
#define SDFM_IT_FIFO_READ_MASK            0x00000020
#define SDFM_IT_DATA_READY_MASK           0x00000040

/**
 * @brief SDFM comparator configuration parameter
 *
 */
typedef struct __PACKED
{
    SDFM_FilterNumber config1_filterNumber;
    SDFM_FilterType   config1_filterType;
    uint8_t           config1_overSamplingRatio;
    uint16_t          config2_lowThreshold;
    uint16_t          config2_highThreshold;
    uint16_t          config3_zeroCrossThreshold;
    ControlStatus     zeroCrossThresholdEn;
} ComparatorConfigParam;

/**
 * @brief SDFM enhanced comparator configuration parameter
 *
 */
typedef struct __PACKED
{
    SDFM_FilterNumber filterConfig_filterNumber;
    SDFM_FilterType   filterConfig_filterType;
    uint8_t           filterConfig_overSamplingRatio;
    uint16_t          highThreshold1;
    uint16_t          highThreshold2;
    uint16_t          lowThreshold1;
    uint16_t          lowThreshold2;
    uint16_t          zeroCrossThreshold;
    ControlStatus     zeroCrossThresholdEn;
} enhancedComparatorConfigParam;

/**
 * @brief SDFM data filter configuration parameter
 *
 */
typedef struct
{
    SDFM_FilterNumber     config1_filterNumber;
    SDFM_FilterType       config1_filterType;
    uint16_t              config1_overSamplingRatio;
    SDFM_OutputDataFormat config2_dataFormat;
    ControlStatus         config2_FilterEn;
    uint16_t              config2_shiftValue;
} dataFilterConfigParam;

/**
 * @brief SDFM zero cross threshold configuration parameter
 *
 */
typedef struct __PACKED
{
    SDFM_FilterNumber config1_filterNumber;
    SDFM_FilterType   config1_filterType;
    uint8_t           config1_overSamplingRatio;
    uint16_t          config2_zeroCrossThreshold;
} zeroCrossThresholdConfigParam;

/**
 * @brief SDFM data filter FIFO configuration parameter
 *
 */
typedef struct
{
    SDFM_FilterNumber     config1_filterNumber;
    SDFM_FilterType       config1_filterType;
    uint16_t              config1_overSamplingRatio;
    SDFM_OutputDataFormat config2_DataRepresentation;
    ControlStatus         config2_FilterSwitch;
    uint16_t              config2_shiftValue;
    uint16_t              config2_fifoLevel;
} dataFilterFIFOConfigParam;


void SDFM_enableExternalReset(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableExternalReset(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableFIFOBuffer(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableFIFOBuffer(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getZeroCrossTripStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearZeroCrossTripStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableComparator(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableComparator(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_selectCompEventSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventNumber compEventNum,
                                SDFM_CompEventSource compEventSource);
void SDFM_setFilterType(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_FilterType filterType);
void SDFM_setFilterOverSamplingRatio(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t overSamplingRatio);
void SDFM_setOutputDataFormat(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_OutputDataFormat dataFormat);
void SDFM_setDataShiftValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t shiftValue);
void SDFM_setCompFilterHighThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t highThreshold1,
                                     uint16_t highThreshold2);
void SDFM_setCompFilterLowThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t lowThreshold1,
                                    uint16_t lowThreshold2);
void SDFM_setCompFilterZeroCrossThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                          uint16_t zeroCrossThreshold);
void SDFM_enableZeroCrossEdgeDetect(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableZeroCrossEdgeDetect(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
void SDFM_disableInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
void SDFM_setComparatorFilterType(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_FilterType filterType);
void SDFM_setCompFilterOverSamplingRatio(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint8_t overSamplingRatio);
uint32_t SDFM_getFilterData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getModulatorStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getNewFilterDataStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getFIFOOverflowStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getFIFOISRStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getIsrStatus(SDFM_Type *SDFM);
void SDFM_clearInterruptFlag(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
void SDFM_enableMainInterrupt(SDFM_Type *SDFM);
void SDFM_disableMainInterrupt(SDFM_Type *SDFM);
void SDFM_enableMainFilter(SDFM_Type *SDFM);
void SDFM_disableMainFilter(SDFM_Type *SDFM);
uint16_t SDFM_getFIFODataCount(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
uint16_t SDFM_getComparatorSincData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
uint32_t SDFM_getFIFOData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_setFIFOInterruptLevel(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t fifoLevel);
void SDFM_setDataReadyInterruptSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                      SDFM_DataReadyInterruptSource dataReadySource);
bool SDFM_getWaitForSyncStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearWaitForSyncFlag(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableWaitForSync(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableWaitForSync(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_setPWMSyncSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_PWMSyncSource syncSource);
void SDFM_setFIFOClearOnSyncMode(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                 SDFM_FIFOClearSyncMode fifoClearSyncMode);
void SDFM_setWaitForSyncClearMode(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                  SDFM_WaitForSyncClearMode syncClearMode);
void SDFM_selectClockSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_ClockSource clkSource);
void SDFM_selectCompEventHighSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventHighSource source);
void SDFM_selectCompEventLowSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventLowSource source);
void SDFM_initCompEventLowFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_initCompEventHighFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_lockCompEventFilterConfig(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                    ControlStatus SDFM_SDCOMPLOCK_SdcompctlEn, ControlStatus SDFM_SDCOMPLOCK_CompEn);
void SDFM_configComparator(SDFM_Type *SDFMx, ComparatorConfigParam *comparatorConfig);
void SDFM_configEnhancedComparator(SDFM_Type *SDFMx, enhancedComparatorConfigParam *enhancedComparatorConfig);
void SDFM_configDataFilter(SDFM_Type *SDFMx, dataFilterConfigParam *datafilterConfig);
void SDFM_configZeroCrossComparator(SDFM_Type *SDFMx, zeroCrossThresholdConfigParam *zeroCrossThresholdConfig);
void SDFM_configDataFilterFIFO(SDFM_Type *SDFMx, dataFilterFIFOConfigParam *dataFilterFIFOConfig);
void SDFM_configCompEventLowFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                   const SDFM_CompEventFilterConfig *config);
void SDFM_configCompEventHighFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                    const SDFM_CompEventFilterConfig *config);
void SDFM_setDataClockReverse(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, ControlStatus dataReverseEn,
                              ControlStatus clkReverseEn);
void SDFM_setDataFilterDecimationCountStartValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                                 uint16_t dataFilterDecimationCountStartValue);
void SDFM_setCompFilterDecimationCountStartValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                                 uint16_t compFilterDecimationCountStartValue);
uint16_t SDFM_getDataFilterDecimationValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
uint16_t SDFM_getCompFilterDecimationValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getCEVT2Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
bool SDFM_getCEVT1Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearMainInterrupt(SDFM_Type *SDFM);
bool SDFM_getMainInterruptStatus(SDFM_Type *SDFM);
void SDFM_setInterruptMask(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
void SDFM_clearInterruptMask(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
uint32_t SDFM_getInterruptStatusRaw(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
uint32_t SDFM_getInterruptStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableDMA(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableDMA(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableAck(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableAck(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableCEVT1(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableCEVT1(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_enableCEVT2(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_disableCEVT2(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearCEVT1Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearCEVT2Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);
void SDFM_clearAckFlagStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber);

void SDFM_clearInterruptStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);
void SDFM_forceInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /*__ET6x_SDFM_H */
