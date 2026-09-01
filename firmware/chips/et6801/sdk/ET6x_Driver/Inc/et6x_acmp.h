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

#ifndef __ET6x_ACMP_H
#define __ET6x_ACMP_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup ACMP
 * @{
 */

/* ACMP channel select */
#define ACMP_CHANNEL_H    (0U)
#define ACMP_CHANNEL_L    (1U)

/* ACMP comparator trim offset value select */

#define TRIM_OFFSET_VAL_NEG_DIR_0MV        (0U)
#define TRIM_OFFSET_VAL_NEG_DIR_2MV        (1U)
#define TRIM_OFFSET_VAL_NEG_DIR_4MV        (2U)
#define TRIM_OFFSET_VAL_NEG_DIR_6MV        (3U)
#define TRIM_OFFSET_VAL_NEG_DIR_8MV        (4U)
#define TRIM_OFFSET_VAL_NEG_DIR_10MV       (5U)
#define TRIM_OFFSET_VAL_NEG_DIR_12MV       (6U)
#define TRIM_OFFSET_VAL_NEG_DIR_14MV       (7U)

#define TRIM_OFFSET_VAL_POS_DIR_0MV        (8U)
#define TRIM_OFFSET_VAL_POS_DIR_2MV        (9U)
#define TRIM_OFFSET_VAL_POS_DIR_4MV        (10U)
#define TRIM_OFFSET_VAL_POS_DIR_6MV        (11U)
#define TRIM_OFFSET_VAL_POS_DIR_8MV        (12U)
#define TRIM_OFFSET_VAL_POS_DIR_10MV       (13U)
#define TRIM_OFFSET_VAL_POS_DIR_12MV       (14U)
#define TRIM_OFFSET_VAL_POS_DIR_14MV       (15U)

/* ACMP trigger source blanking width select */
#define BLK_WIDTH_MAX                      (4095U)
#define BLK_WIDTH_MIN                      (1U)
#define BLK_WIDTH_NONE                     (0U)

/* ACMP error status */
#define ACMP_ERROR_STATUS_NONE             (0x00)
#define CHANNEL_H_CMP_BLK_REPT             (0x01)
#define CHANNEL_L_CMP_BLK_REPT             (0x02)
#define CHANNEL_H_DAC_TXDN_REPT            (0x04)
#define CHANNEL_L_DAC_TXDN_REPT            (0x08)
#define CHANNEL_H_DAC_TRG_REPT             (0x10)
#define CHANNEL_L_DAC_TRG_REPT             (0x20)
#define CHANNEL_H_DAC_DMAREQ_REPT          (0x40)
#define CHANNEL_L_DAC_DMAREQ_REPT          (0x80)

/* ACMP comparator result filter width select */
#define FILTER_WIDTH_MAX                   (0x3FFFU)
#define FILTER_WIDTH_MIN                   (1U)
#define FILTER_WIDTH_NONE                  (0U)

/* ACMP interrupt mask */
#define ACMP_IT_NONE_MASK                  (0x00)
#define CHANNEL_H_DAC_TXDN_IT_MASK         (0x01)
#define CHANNEL_L_DAC_TXDN_IT_MASK         (0x02)
#define CHANNEL_H_AFTER_FILTER_IT_MASK     (0x04)
#define CHANNEL_L_AFTER_FILTER_IT_MASK     (0x08)
#define CHANNEL_H_BEFORE_FILTER_IT_MASK    (0x10)
#define CHANNEL_L_BEFORE_FILTER_IT_MASK    (0x20)
#define ACMP_IT_ALL_MASK                   (0x3F)


typedef enum
{
    ACMP_HYST_RISING,
    ACMP_HYST_FALLING
} ACMP_HysteresisDirection;

/* ACMP positive input signal source select */
typedef enum
{
    ACMP_INPUT_MUX_SELECT_0,                 /*!< ACMP input src select 0 */
    ACMP_INPUT_MUX_SELECT_1,                 /*!< ACMP input src select 1 */
    ACMP_INPUT_MUX_SELECT_2,                 /*!< ACMP input src select 2 */
    ACMP_INPUT_MUX_SELECT_3,                 /*!< ACMP input src select 3 */
    ACMP_INPUT_MUX_SELECT_4,                 /*!< ACMP input src select 4 */
    ACMP_INPUT_MUX_SELECT_5                  /*!< ACMP input src select 5 */
} ACMP_InputSrcSelect;

/* ACMP negative reference signal source select */
typedef enum
{
    ACMP_REF_MUX_DAC,                 /*!< ACMP reference internal DAC */
    ACMP_REF_MUX_SELECT_0,            /*!< ACMP reference select 0     */
    ACMP_REF_MUX_SELECT_1,            /*!< ACMP reference select 1     */
    ACMP_REF_MUX_SELECT_2,            /*!< ACMP reference select 2     */
} ACMP_RefSrcSelect;

/* ACMP comparator hysteresis value select */
typedef enum
{
    HYSTERESIS_VALUE_0MV,
    HYSTERESIS_VALUE_7MV,
    HYSTERESIS_VALUE_14MV,
    HYSTERESIS_VALUE_23MV,
    HYSTERESIS_VALUE_36MV,
    HYSTERESIS_VALUE_43MV,
    HYSTERESIS_VALUE_52MV,
    HYSTERESIS_VALUE_62MV
} ACMP_HysteresisValue;

/** @defgroup ACMP_DacTriggerSel DAC trigger sel
 * @{
 */

/**
 * @brief Select dac trigger source
 *  The specific events of the peripheral module need to be configured in the corresponding peripheral module.
 *
 * @note when dac trigger is selected as follow: \n
 * DAC_TRIGGER_SEL_STIM
 * DAC_TRIGGER_SEL_ETIM
 * DAC_TRIGGER_SEL_SRPWM
 * DAC_TRIGGER_SEL_SELF_TX_DONE
 * DAC_TRIGGER_SEL_ACOMP
 * DAC load mode should be select [DAC_LODE_SHADOW] \n
 *
 */
typedef enum
{
    ACMP_DAC_TRIGGER_SEL_SW           = 0,   /*!< software trigger */
    ACMP_DAC_TRIGGER_SEL_STIM         = 1,   /*!< stimer trigger */
    ACMP_DAC_TRIGGER_SEL_ETIM         = 2,   /*!< etimer trigger */
    ACMP_DAC_TRIGGER_SEL_SRPWM        = 3,   /*!< srpwm trigger */
    ACMP_DAC_TRIGGER_SEL_SELF_TX_DONE = 4,   /*!< self tx done trigger */
    ACMP_DAC_TRIGGER_SEL_ACOMP        = 6,   /*!< acmp trigger */
    ACMP_DAC_TRIGGER_SEL_DMA          = 7    /*!< dma trigger */
} ACMP_TriggerSel;

/**
 * @}
 */

/* ACMP DAC trigger delay */
#define TRIGGER_DLY_MAX     (255U)
#define TRIGGER_DLY_MIN     (1U)
#define TRIGGER_DLY_NONE    (0U)

/**
 * @brief ACMP output and input src structure
 */
typedef struct
{
    ControlStatus       digitalOutputPolarityReverseEn;  /*!< reverse digital output polarity */
    ControlStatus       analogOutputPolarityReverseEn;   /*!< reverse analog output polarity */
    ACMP_InputSrcSelect cmpPositiveInputSelect;          /*!< select positive input source */
    ACMP_RefSrcSelect   cmpNegativeInputSelect;          /*!< select negative reference source */
    ControlStatus       asyncPathEn;                     /*!< enable asynchronous path */
} ACMP_Comparator;

/**
 * @brief ACMP trip source select
 */
typedef enum
{
    ACMP_TRIPSRC_ASYNC_COMP,    /*!< asynchronous comparator output */
    ACMP_TRIPSRC_SYNC_COMP,     /*!< synchronous comparator output  */
    ACMP_TRIPSRC_FILTER,        /*!< output of the digital filter   */
    ACMP_TRIPSRC_LATCH,         /*!< latched output of the digital filter */
} ACMP_TripSrcSel;

/* ACMP output target source select */
typedef struct
{
    ACMP_TripSrcSel ctripOut;   /*!< to XBAR */
    ACMP_TripSrcSel ctrip;      /*!< to QEP, XBAR, ETIMER, ADC */
} ACMP_TripOut;

/* ACMP digital filter input source select */
typedef enum
{
    ACMP_FILTER_INPUT_ACMP_OUT, /*!< The analog output of the current comparator is used as the input of the filter. */
    ACMP_FILTER_INPUT_0,        /*!< Select the external signal cmpc_filtin[0] as the input for the filter.  */
    ACMP_FILTER_INPUT_1,        /*!< Select the external signal cmpc_filtin[1] as the input for the filter.  */
    ACMP_FILTER_INPUT_2,        /*!< Select the external signal cmpc_filtin[2] as the input for the filter.  */
    ACMP_FILTER_INPUT_3,        /*!< Select the external signal cmpc_filtin[3] as the input for the filter.  */
    ACMP_FILTER_INPUT_4,        /*!< Select the external signal cmpc_filtin[4] as the input for the filter.  */
    ACMP_FILTER_INPUT_5,        /*!< Select the external signal cmpc_filtin[5] as the input for the filter.  */
    ACMP_FILTER_INPUT_6,        /*!< Select the external signal cmpc_filtin[6] as the input for the filter.  */
} ACMP_DigitalFilterInpustSel;

/**
 * @brief DAC Load Mode enumeration
 */
typedef enum
{
    ACMP_DAC_LOADMODE_IMMEDIATE,   /*!< DAC load mode immediate */
    ACMP_DAC_LOADMODE_SHADOW       /*!< DAC load mode shadow */
} ACMP_DAC_LoadMode;

/* ACMP DAC output data format */
typedef enum
{
    ACMP_DAC_OUTPUT_DIRECT,
    ACMP_DAC_OUTPUT_INVERTED
} ACMP_DAC_OutputDataFormat;

/* ACMP DAC data source select */
typedef enum
{
    ACMP_DAC_WAG_OUTPUT,
    ACMP_DAC_RAMP_OUTPUT
} ACMP_DAC_srcSel;

/* ACMP DAC TDAT select */
typedef enum
{
    ACMP_DAC_TDAT_REG,          /* DAC value input for DAC value register */
    ACMP_DAC_TDAT_EXTERNAL      /* DAC value input for WAG or RAMP module */
} ACMP_DAC_TDATSel;

/* ACMP DAC reference select */
typedef enum
{
    ACMP_DAC_REF_PAD,
    ACMP_DAC_REF_LDO
} ACMP_DAC_RefSel;

/* Acmp Ramp TRIG src */
typedef enum
{
    ACMP_RAMP_TRIG_EXTERNAL,
    ACMP_RAMP_TRIG_OTHERRAMP_TRIGOFF
} ACMP_RAMP_xTrigSel;

/* Acmp Ramp Direction */
typedef enum
{
    ACMP_RAMP_DIR_DOWN,
    ACMP_RAMP_DIR_UP
} ACMP_RAMP_Direction;

/* ACMP DAC referrence select */
typedef enum
{
    MAXREFA_LOAD,
    MAXREFS_LOAD
} ACMP_RAMP_LoadSel;

/**
 * @brief ACMP and DAC configuration structure
 */
typedef struct
{
    ACMP_DAC_LoadMode         loadMode;               /* Specifiies the dac load mode */
    MaskStatus                triggerMask;            /* Specifiies the dac trigger mask */
    ControlStatus             triggerInvertEn;        /* Enable or disable invert trigger signal polarity */
    ControlStatus             triggerEn;              /* Specifiies the dac trigger delay enable */
    ACMP_TriggerSel           triggerSel;             /* Specifies the dac trigger source */
    uint8_t                   triggerDelay;           /* Specifies the dac trigger delay time */
    ControlStatus             dacOutputReverseEn;
    ACMP_DAC_OutputDataFormat outputFormat;
    ACMP_DAC_srcSel           dacsrcSel;
    ACMP_DAC_TDATSel          tdatSel;
    ACMP_DAC_RefSel           dacRefSelect;           /* select DAC reference voltage */
    ControlStatus             dacToCmpEn;             /* Enable or disable internal dac output to comparator */
} ACMP_DAC_Config;

/**
 * @brief Comparator output event source event filter configuration structure
 */
typedef struct
{
    ControlStatus sampleAsInputEn;
    uint8_t       sampThresh;
    uint8_t       sampWindow;
    uint16_t      clkScale;
} ACMP_Filter_ConfigType;


void ACMP_enableModule(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_disableModule(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_configComparator(ACMP_Type *ACMPx, uint8_t channel, ACMP_Comparator *config);
void ACMP_configOutputs(ACMP_Type *ACMPx, uint8_t channel, ACMP_TripOut *config);
uint32_t ACMP_getStatus(ACMP_Type *ACMPx);
void ACMP_configDAC(ACMP_Type *ACMPx, uint8_t channel, ACMP_DAC_Config *config);
void ACMP_setDACValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t data);
uint16_t ACMP_getDACValue(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_configureSyncSource(ACMP_Type *ACMPx, uint8_t channel, uint16_t syncSource);
void ACMP_setHysteresis(ACMP_Type *ACMPx, uint8_t channel, ACMP_HysteresisValue value, ACMP_HysteresisDirection dir);
void ACMP_enableLatchResetOnSYNC(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_disableLatchResetOnSYNC(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_SWTriggerDAC(ACMP_Type *ACMPx, uint8_t channel);

/* Blanking */
void ACMP_configBlanking(ACMP_Type *ACMPx, uint8_t channel, uint16_t blankingWidth, uint16_t blankingDelay);
void ACMP_enableBlanking(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_disableBlanking(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_setBlankingHold(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_clearBlankingHold(ACMP_Type *ACMPx, uint8_t channel);

/* Digital Filter */
void ACMP_initFilter(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_clearFilterLatch(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_configFilter(ACMP_Type *ACMPx, uint8_t channel, ACMP_DigitalFilterInpustSel filterInputSel,
                       uint32_t samplePrescale, uint16_t sampleWindow,
                       uint16_t threshold);
void ACMP_enableFilter(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_disableFilter(ACMP_Type *ACMPx, uint8_t channel);

/* Ramp Generator */
void ACMP_configRamp(ACMP_Type *ACMPx, uint8_t channel, uint16_t maxRampVal, uint16_t decrementVal, uint16_t delayVal);
void ACMP_setRampClkPrescale(ACMP_Type *ACMPx, uint8_t channel, uint16_t value);
void ACMP_setRampTrigSel(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_xTrigSel trig);
void ACMP_setRampDir(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_Direction dir);
void ACMP_setMaxRampValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value);
uint16_t ACMP_getMaxRampValue(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_setRampDecValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value);
uint16_t ACMP_getRampDecValue(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_selectRampLoad(ACMP_Type *ACMPx, uint8_t channel, ACMP_RAMP_LoadSel value);
void ACMP_setRampDelayValue(ACMP_Type *ACMPx, uint8_t channel, uint16_t value);
uint16_t ACMP_getRampDelayValue(ACMP_Type *ACMPx, uint8_t channel);
uint16_t ACMP_getRampClkCountValue(ACMP_Type *ACMPx, uint8_t channel);
uint16_t ACMP_getRampStatus(ACMP_Type *ACMPx, uint8_t channel);

/* Status */
uint32_t ACMP_getErrorStatus(ACMP_Type *ACMPx);
void ACMP_clearErrorStatus(ACMP_Type *ACMPx, uint32_t errorStatus);
FlagStatus ACMP_getLatchStatus(ACMP_Type *ACMPx, uint8_t channel);
FlagStatus ACMP_getDACTransferStatus(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_clearDACTransferStatus(ACMP_Type *ACMPx, uint8_t channel);

/* Interrupt */
void ACMP_setInterruptMask(ACMP_Type *ACMPx, uint32_t interruptMask);
void ACMP_clearInterruptMask(ACMP_Type *ACMPx, uint32_t interruptMask);
void ACMP_enableInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask);
void ACMP_forceInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask);
void ACMP_disableInterrupt(ACMP_Type *ACMPx, uint32_t interruptMask);
void ACMP_clearInterruptStatus(ACMP_Type *ACMPx, uint32_t interruptMask);
uint32_t ACMP_getInterruptStatus(ACMP_Type *ACMPx);
uint32_t ACMP_getInterruptStatusRaw(ACMP_Type *ACMPx);

/* Calibration */
void ACMP_setDACOSADJ(ACMP_Type *ACMPx, uint8_t channel, int16_t value);
int16_t ACMP_getDACOSADJ(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_setDACGainADJ(ACMP_Type *ACMPx, uint8_t channel, int16_t value);
int16_t ACMP_getDACGainADJ(ACMP_Type *ACMPx, uint8_t channel);

/* DMA */
void ACMP_enableDMA(ACMP_Type *ACMPx, uint8_t channel);
void ACMP_disableDMA(ACMP_Type *ACMPx, uint8_t channel);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /*__ET3x_ACMP_H */
