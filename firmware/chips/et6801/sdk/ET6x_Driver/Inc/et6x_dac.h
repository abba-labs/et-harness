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

/* Define to prevent recursive inclusion ----------------------------------------------------*/
#ifndef __ET6X_DAC_H
#define __ET6X_DAC_H

#ifdef __cplusplus
extern "C" {
#endif

/* includes ---------------------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup DAC
 * @{
 */

/* Exported types -----------------------------------------------------------------------------*/

/**
 * @brief DAC Ref Source enumeration
 */
typedef enum
{
    DAC_REFSEL_PAD       = 0,              /*!< DAC Reference to IOPAD */
    DAC_REFSEL_INNER_LDO = 1               /*!< DAC Reference to inner Vref */
} DAC_ReferenceVoltage;

/**
 * @brief DAC Trigger Source enumeration
 * @note when dac trigger source selected as follow:
 * DAC_TRIGGER_SEL_STIM
 * DAC_TRIGGER_SEL_ETIM
 * DAC_TRIGGER_SEL_SPWM
 * DAC_TRIGGER_SEL_SELF_TX_DONE
 * DAC_TRIGGER_SEL_ACOMP
 * DAC load mode should select [DAC_LOAD_MODE_SHADOW]
 */
typedef enum
{
    DAC_OUTPUT_DIRECT,
    DAC_OUTPUT_INVERTED
} DAC_OutputFormat;

typedef enum
{
    DAC_SRC_SEL_REG,   /*!< DAC data load from register   */
    DAC_SRC_SEL_WAG    /*!< DAC data load from WAG module */
} DAC_SrcSel;

/**
 * @brief DAC Init structure definition
 */
typedef struct
{
    ControlStatus shadowLoadEn;
    MaskStatus    triggerMask;                       /* Specifies the dac trigger mask */
    ControlStatus triggerInvertEn;                   /* Enable or disable invert trigger signal polarity */
    ControlStatus triggerEn;                         /* Specifies the dac trigger enable */
    uint8_t       triggerDelay;                      /* Specifies the dac trigger delay time */
} DAC_TriggerConfig;

typedef struct
{
    DAC_OutputFormat outputFormat;
    DAC_SrcSel       srcSel;
    ControlStatus    outputDataReverseEn;
} DAC_OutputConfig;

/**
 * @brief Values that can be passed to DAC_setTriggerSource() as the \e mode parameter.
 */
typedef enum
{
    DAC_TRIGGER_SEL_SW           = 0,      /*!< DAC trigger Source Software */
    DAC_TRIGGER_SEL_STIMER       = 1,      /*!< DAC trigger Source PIT Timer*/
    DAC_TRIGGER_SEL_ETIM         = 2,      /*!< DAC trigger Source ETimer */
    DAC_TRIGGER_SEL_SRPWM        = 3,      /*!< DAC trigger Source SrPWM Sync Signal to DAC */
    DAC_TRIGGER_SEL_SELF_TX_DONE = 4,      /*!< DAC trigger Source by self tx done */
    DAC_TRIGGER_SEL_DMA          = 7       /*!< DAC trigger Source DMA */
} DAC_TriggerSel;

/* Exported constant --------------------------------------------------------------------*/

/* Exported macro  ----------------------------------------------------------------------*/
/* Exported functions  ------------------------------------------------------------------*/

/* DAC configuration *********************************************************************/

void DAC_configTriggerMode(DAC_Type *DACx, DAC_TriggerConfig *config);
void DAC_configOutput(DAC_Type *DACx, DAC_OutputConfig *config);
void DAC_setReferenceVoltage(DAC_Type *DACx, DAC_ReferenceVoltage source);
void DAC_setTriggerSource(DAC_Type *DACx, DAC_TriggerSel source);
void DAC_setValue(DAC_Type *DACx, uint16_t value);
uint16_t DAC_getValue(DAC_Type *DACx);
void DAC_enableOutput(DAC_Type *DACx);
void DAC_disableOutput(DAC_Type *DACx);
void DAC_SWTrigger(DAC_Type *DACx);
FlagStatus DAC_getTrigRepeatStatus(DAC_Type *DACx);
void DAC_clearTrigRepeatStatus(DAC_Type *DACx);
FlagStatus DAC_getTransferStatus(DAC_Type *DACx);
void DAC_clearTransferStatus(DAC_Type *DACx);
void DAC_enableInterrupt(DAC_Type *DACx);
void DAC_disableInterrupt(DAC_Type *DACx);
void DAC_clearInterruptStatus(DAC_Type *DACx);
ITStatus DAC_getInterruptStatus(DAC_Type *DACx);
void DAC_enableDMA(DAC_Type *DACx);
void DAC_disableDMA(DAC_Type *DACx);
void DAC_enableSWHold(DAC_Type *DACx);
void DAC_disableSWHold(DAC_Type *DACx);
void DAC_enableHWHold(DAC_Type *DACx);
void DAC_disableHWHold(DAC_Type *DACx);
void DAC_setOffsetTrim(DAC_Type *DACx, uint16_t nValue);
uint16_t DAC_getOffsetTrim(DAC_Type *DACx);
void DAC_setGainADJ(DAC_Type *DACx, uint16_t value);
uint16_t DAC_getGainADJ(DAC_Type *DACx);

#ifdef __cplusplus
}
#endif

/**
 * @}
 */

/**
 * @}
 */

#endif /* __ET6X_DAC_H */
