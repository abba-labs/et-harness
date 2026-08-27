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
#include "et6x_sdfm.h"

#define SDFM_FILTER_INTERRUPT_STEP    7U

#define IS_SDFM_ALL_PERIPH(PERIPH)             (((PERIPH) == SDFM0) || ((PERIPH) == SDFM1))
#define IS_SDFM_SHIFT_VALUE(value)             (value < 32U)
#define IS_INTERRUPT_MASKS(masks) \
        ((masks & (SDFM_IT_CEVT1_MASK | \
                   SDFM_IT_CEVT2_MASK | \
                   SDFM_IT_MODULATOR_FAILURE_MASK | \
                   SDFM_IT_FIFO_OVERFLOW_MASK | \
                   SDFM_IT_FIFO_WRITE_MASK | \
                   SDFM_IT_FIFO_READ_MASK | \
                   SDFM_IT_DATA_READY_MASK)) != 0)
#define IS_CMP_OVERSAMPLING_RATIO(ratio)       (ratio < 32U)
#define IS_DATA_OVERSAMPLING_RATIO(ratio)      (ratio < 256U)
#define IS_SDFM_CLK_PRESCALE(clkPrescale)      (clkPrescale < 1024)
#define IS_SDFM_SAMPLE_WINDOW(sampleWindow)    (sampleWindow < 32U)
#define IS_SDFM_THRESHOLD(threshold)           (threshold < 32U)
#define IS_SDFM_FIFO_THRESHOLD(fifo)           (fifo <= 16U)

/**
 *
 * @brief Enable external reset
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function enables data filter to be reset by an external source (PWM
 * compare output).
 *
 */
void SDFM_enableExternalReset(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_SDSYNCEN_Msk);
}

/**
 *
 * @brief Disable external reset
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function disables data filter from being reset by an external source
 * (PWM compare output).
 *
 */
void SDFM_disableExternalReset(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_SDSYNCEN_Msk);
}

/**
 *
 * @brief Enable filter
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function enables the filter specified by the \b filterNumber variable.
 *
 */
void SDFM_enableFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_FEN_Msk);
}

/**
 *
 * @brief Disable filter
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function disables the filter specified by the \b filterNumber
 * variable.
 *
 */
void SDFM_disableFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_FEN_Msk);
}

/**
 *
 * @brief Enable FIFO buffer
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function enables the filter FIFO buffer specified by the
 * \b filterNumber variable.
 *
 */
void SDFM_enableFIFOBuffer(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_FFEN_Msk);
}

/**
 *
 * @brief Disable FIFO buffer
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function disables the filter FIFO buffer specified by the
 * \b filterNumber variable.
 *
 */
void SDFM_disableFIFOBuffer(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_FFEN_Msk);
}

/**
 *
 * @brief Return the Zero Cross Trip status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the Zero Cross Trip status for the filter
 * specified by filterNumber variable.
 *
 * @return \b true if Comparator filter output >= High-level threshold (Z)
 *         \b false if Comparator filter output < High-level threshold (Z)
 *
 */
bool SDFM_getZeroCrossTripStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_HZ_RPT_Msk) != 0;
}

/**
 *
 * @brief Clear the Zero Cross Trip status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 *  This function clears the Zero Cross Trip status for the filter
 *  specified by filterNumber variable.
 *
 */
void SDFM_clearZeroCrossTripStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDCLRSTS, SDFM0_SDCHNX_GRP_SDCLRSTS_HZ_CLR_Msk);
}

/**
 *
 * @brief Enable Comparator.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 *  This function enables the Comparator for the selected filter.
 *
 */
void SDFM_enableComparator(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEN_Msk);
}

/**
 *
 * @brief Disable Comparator.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 *  This function disables the Comparator for the selected filter.
 *
 */
void SDFM_disableComparator(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEN_Msk);
}

/**
 *
 * @brief Selects Comparator Event Source.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param compEventNum is the event number
 * @param compEventSource is the event source
 *
 *  This function selects the comparator event source. Valid values for
 * \b compEventNum are:
 * - SDFM_COMP_EVENT_1 - Selects comparator event 1
 * - SDFM_COMP_EVENT_2 - Selects comparator event 2
 * Valid values for \b SDFM_COMP_EVENT_1 are:
 * - SDFM_COMP_EVENT_SRC_COMPH1 - COMPH1 event is the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPH1_L1 - Either of COMPH1 or COMPL1 event can be
 *                                   the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPH2 - COMPH2 event is the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPH2_L2 - Either of COMPH2 or COMPL2 event can be
 *                                   the source for selected event
 *
 * Valid values for \b SDFM_COMP_EVENT_2 are:
 * - SDFM_COMP_EVENT_SRC_COMPL1 - COMPL1 event is the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPH1_L1 - Either of COMPH1 or COMPL1 event can be
 *                                   the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPL2 - COMPL2 event is the source for selected event
 * - SDFM_COMP_EVENT_SRC_COMPH2_L2 - Either of COMPH2 or COMPL2 event can be
 *                                   the source for selected event
 *
 */
void SDFM_selectCompEventSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventNumber compEventNum,
                                SDFM_CompEventSource compEventSource)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    if (compEventNum == SDFM_COMP_EVENT_1)
    {
        MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCPARM, SDFM0_SDCHNX_GRP_SDCPARM_CEVT1SEL_Msk,
                   (uint32_t)compEventSource << SDFM0_SDCHNX_GRP_SDCPARM_CEVT1SEL_Pos);
    }
    else
    {
        MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCPARM, SDFM0_SDCHNX_GRP_SDCPARM_CEVT2SEL_Msk,
                   (uint32_t)compEventSource << SDFM0_SDCHNX_GRP_SDCPARM_CEVT2SEL_Pos);
    }
}

/**
 *
 * @brief Set filter type.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param filterType is the filter type or structure.
 *
 * This function sets the filter type or structure to be used as specified by
 * filterType for the selected filter number as specified by filterNumber.
 *
 */
void SDFM_setFilterType(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_FilterType filterType)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDDFPARM, SDFM0_SDCHNX_GRP_SDDFPARM_MFST_Msk,
               (uint32_t)filterType << SDFM0_SDCHNX_GRP_SDDFPARM_MFST_Pos);
}

/**
 *
 * @brief Set data filter over sampling ratio.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param overSamplingRatio is the data filter over sampling ratio.
 *
 * This function sets the filter oversampling ratio for the filter specified
 * by the filterNumber variable.Valid values for the variable
 * overSamplingRatio are 0 to 255 inclusive. The actual oversampling ratio
 * will be this value plus one.
 *
 */
void SDFM_setFilterOverSamplingRatio(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t overSamplingRatio)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_DATA_OVERSAMPLING_RATIO(overSamplingRatio));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDDFPARM, SDFM0_SDCHNX_GRP_SDDFPARM_DOSR_Msk,
               (uint32_t)overSamplingRatio << SDFM0_SDCHNX_GRP_SDDFPARM_DOSR_Pos);
}

/**
 *
 * @brief Set the output data format
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param dataFormat is the output data format.
 *
 * This function sets the output data format for the filter specified by
 * filterNumber.
 *
 */
void SDFM_setOutputDataFormat(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_OutputDataFormat dataFormat)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDDPARM, SDFM0_SDCHNX_GRP_SDDPARM_DR_Msk,
               (uint32_t)dataFormat << SDFM0_SDCHNX_GRP_SDDPARM_DR_Pos);
}

/**
 *
 * @brief Set data shift value.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param shiftValue is the data shift value.
 *
 * This function sets the shift value for the 16 bit 2's complement data
 * format. The valid maximum value for shiftValue is 10.
 *
 * \b Note: Use this function with 16 bit 2's complement data format only.
 *
 */
void SDFM_setDataShiftValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t shiftValue)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_SDFM_SHIFT_VALUE(shiftValue));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDDPARM, SDFM0_SDCHNX_GRP_SDDPARM_SH_Msk,
               (uint32_t)shiftValue << SDFM0_SDCHNX_GRP_SDDPARM_SH_Pos);
}

/**
 *
 * @brief Set Filter output high-level threshold.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param highThreshold is the high-level threshold 1 & 2.
 *
 * This function sets the unsigned high-level threshold value for the
 * Comparator filter output. If the output value of the filter exceeds
 * highThreshold and interrupt generation is enabled, an interrupt will be
 * issued. The param \b highThreshold takes both high threshold 1 & 2 values.
 * The upper 16-bits represent the high threshold 2 value while lower 16-bits
 * represent the threshold 1 values.
 *
 */
void SDFM_setCompFilterHighThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t highThreshold1,
                                     uint16_t highThreshold2)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    WRITE_REG(SDFMx->SDCHNX_GRP[filterNumber].SDFLTXCMPH, (uint32_t)highThreshold1 << SDFM0_SDCHNX_GRP_SDFLTXCMPH_HLT_VAL_Pos |
              (uint32_t)highThreshold2 << SDFM0_SDCHNX_GRP_SDFLTXCMPH_HLT2_VAL_Pos);
}

/**
 *
 * @brief Set Filter output low-level threshold.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param lowThreshold is the low-level threshold
 *
 * This function sets the unsigned low-level threshold value 1 or 2 for the
 * Comparator filter output. If the output value of the filter gets below
 * lowThreshold and interrupt generation is enabled, an interrupt will be
 * issued. The param \b lowThreshold takes both low threshold 1 & 2 values.
 * The upper 16-bits represent the low threshold 2 value while lower 16-bits
 * represent the threshold 1 values.
 *
 */
void SDFM_setCompFilterLowThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t lowThreshold1,
                                    uint16_t lowThreshold2)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    WRITE_REG(SDFMx->SDCHNX_GRP[filterNumber].SDFLTXCMPL, (uint32_t)lowThreshold1 << SDFM0_SDCHNX_GRP_SDFLTXCMPL_LLT_VAL_Pos |
              (uint32_t)lowThreshold2 << SDFM0_SDCHNX_GRP_SDFLTXCMPL_LLT2_VAL_Pos);
}

/**
 *
 * @brief Set Filter output zero-cross threshold.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param zeroCrossThreshold is the zero-cross threshold.
 *
 * This function sets the unsigned zero-cross threshold value for the
 * Comparator filter output.
 *
 */
void SDFM_setCompFilterZeroCrossThreshold(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                          uint16_t zeroCrossThreshold)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    WRITE_REG(SDFMx->SDCHNX_GRP[filterNumber].SDFLTXCMPHZ, zeroCrossThreshold);
}

/**
 *
 * @brief Enable zero-cross Edge detect mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function enables Zero Cross Edge detection.
 *
 */
void SDFM_enableZeroCrossEdgeDetect(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_HZEN_Msk);
}

/**
 *
 * @brief Disable zero-cross Edge detect mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function disables Zero Cross Edge detection.
 *
 */
void SDFM_disableZeroCrossEdgeDetect(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_HZEN_Msk);
}

/**
 *
 * @brief Enable SDFM interrupts.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param intFlags is the interrupt source.
 *
 * This function enables the low threshold , high threshold or modulator
 * failure interrupt as determined by intFlags for the filter specified
 * by filterNumber.
 * Valid values for intFlags are:
 *  SDFM_MODULATOR_FAILURE_INTERRUPT
 *  SDFM_LOW_LEVEL_THRESHOLD_INTERRUPT
 *  SDFM_HIGH_LEVEL_THRESHOLD_INTERRUPT
 *  SDFM_FIFO_INTERRUPT
 *  SDFM_FIFO_OVERFLOW_INTERRUPT
 *  SDFM_DATA_FILTER_ACKNOWLEDGE_INTERRUPT
 *
 */
void SDFM_enableInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_INTERRUPT_MASKS(interruptMasks));

    SET_BIT(SDFMx->INT_EN, (uint32_t)interruptMasks << filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 *
 * @brief Disable SDFM interrupts.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param intFlags is the interrupt source.
 *
 * This function disables the low threshold , high threshold or modulator
 * failure interrupt as determined by intFlags for the filter
 * specified by filterNumber.
 * Valid values for intFlags are:
 *  SDFM_MODULATOR_FAILURE_INTERRUPT
 *  SDFM_LOW_LEVEL_THRESHOLD_INTERRUPT
 *  SDFM_HIGH_LEVEL_THRESHOLD_INTERRUPT
 *  SDFM_FIFO_INTERRUPT
 *  SDFM_FIFO_OVERFLOW_INTERRUPT
 *  SDFM_DATA_FILTER_ACKNOWLEDGE_INTERRUPT
 *
 */
void SDFM_disableInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_INTERRUPT_MASKS(interruptMasks));

    CLEAR_BIT(SDFMx->INT_EN, (uint32_t)interruptMasks << filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 *
 * @brief Set the comparator filter type.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param filterType is the comparator filter type or structure.
 *
 * This function sets the Comparator filter type or structure to be used as
 * specified by filterType for the selected filter number as specified by
 * filterNumber.
 *
 */
void SDFM_setComparatorFilterType(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_FilterType filterType)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCPARM, SDFM0_SDCHNX_GRP_SDCPARM_CFST_Msk,
               (uint32_t)filterType << SDFM0_SDCHNX_GRP_SDCPARM_CFST_Pos);
}

/**
 *
 * @brief Set Comparator filter over sampling ratio.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param overSamplingRatio is the comparator filter over sampling ration.
 *
 * This function sets the comparator filter oversampling ratio for the filter
 * specified by the filterNumber.Valid values for the variable
 * overSamplingRatio are 0 to 31 inclusive.
 * The actual oversampling ratio will be this value plus one.
 *
 */
void SDFM_setCompFilterOverSamplingRatio(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint8_t overSamplingRatio)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_CMP_OVERSAMPLING_RATIO(overSamplingRatio));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCPARM, SDFM0_SDCHNX_GRP_SDCPARM_COSR_Msk,
               (uint32_t)overSamplingRatio << SDFM0_SDCHNX_GRP_SDCPARM_COSR_Pos);
}

/**
 *
 * @brief Get the filter data output.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the latest data filter output. Depending on the
 * filter data output format selected, the valid value will be the lower 16
 * bits or the whole 32 bits of the returned value.
 *
 * @return Returns the latest data filter output.
 */
uint32_t SDFM_getFilterData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return(SDFMx->SDCHNX_GRP[filterNumber].FIFO_DATA);
}

/**
 *
 * @brief Get the Modulator status.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the Modulator status.
 *
 * @return \b true if the Modulator is operating normally
 *         \b false if the Modulator has failed
 *
 */
bool SDFM_getModulatorStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return (READ_BIT(SDFMx->INT_RAW_RPT, SDFM_IT_MODULATOR_FAILURE_MASK) << filterNumber) != 0;
}

/**
 *
 * @brief Check if new Filter data is available.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns new filter data status.
 *
 * @return Returns \b true if new filter data is available
 *         Returns \b false if no new filter data is available
 *
 */
bool SDFM_getNewFilterDataStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_AF_RPT_Msk) != 0;
}

/**
 *
 * @brief Check if FIFO buffer is overflowed.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the status of the FIFO buffer overflow for the given
 * filter value.
 *
 * @return Returns \b true if FIFO buffer is overflowed
 *         Returns \b false if FIFO buffer is not overflowed
 *
 */
bool SDFM_getFIFOOverflowStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return (READ_BIT(SDFMx->INT_RAW_RPT, SDFM_IT_FIFO_OVERFLOW_MASK) << filterNumber) != 0;
}

/**
 *
 * @brief Check FIFO buffer interrupt status.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the status of the FIFO buffer interrupt for the given
 * filter.
 *
 * @return Returns \b true if FIFO buffer interrupt has occurred.
 *         Returns \b false if FIFO buffer interrupt has not occurred.
 *
 */
bool SDFM_getFIFOISRStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return (READ_BIT(SDFMx->INT_RAW_RPT, (SDFM_IT_FIFO_WRITE_MASK | SDFM_IT_FIFO_READ_MASK)) << filterNumber) != 0;
}

/**
 *
 * @brief Get pending interrupt.
 *
 * @param SDFMx is the base address of the SDFM module
 *
 * This function returns any pending interrupt status.
 *
 * @return Returns \b true if there is a pending interrupt.
 *         Returns \b false if no interrupt is pending.
 *
 */
bool SDFM_getIsrStatus(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_REG(SDFMx->INT_STATUS_RPT) != 0;
}

/**
 *
 * @brief Clear pending flags.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param flag is the SDFM status
 *
 * This function clears the specified pending interrupt flag.
 * Valid values are
 *
 */
void SDFM_clearInterruptFlag(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_INTERRUPT_MASKS(interruptMasks));

    SET_BIT(SDFMx->INT_CLR, (uint32_t)interruptMasks << filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 *
 * @brief Enable main interrupt.
 *
 * @param SDFMx is the base address of the SDFM module
 *
 * This function enables the main SDFM interrupt.
 *
 */
void SDFM_enableMainInterrupt(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDMEN, SDFM0_SDMEN_MIE_Msk);
}

/**
 *
 * @brief Disable main interrupt.
 *
 * @param SDFMx is the base address of the SDFM module
 *
 * This function disables the main SDFM interrupt.
 *
 */
void SDFM_disableMainInterrupt(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDMEN, SDFM0_SDMEN_MIE_Msk);
}

/**
 *
 * @brief Enable main filter.
 *
 * @param SDFMx is the base address of the SDFM module
 *
 * This function enables main filter.
 *
 */
void SDFM_enableMainFilter(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDMEN, SDFM0_SDMEN_MFE_Msk);
}

/**
 *
 * @brief Disable main filter.
 *
 * @param SDFMx is the base address of the SDFM module
 *
 * This function disables main filter.
 *
 */
void SDFM_disableMainFilter(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDMEN, SDFM0_SDMEN_MFE_Msk);
}

/**
 *
 * @brief Return the FIFO data count
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the FIFO data count.
 *
 * @return Returns the number of data words available in FIFO buffer.
 *
 */
uint16_t SDFM_getFIFODataCount(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return (uint16_t)(READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_SDFFST_RPT_Msk) >>
                      SDFM0_SDCHNX_GRP_SDSTS_SDFFST_RPT_Pos);
}

/**
 *
 * @brief Return the Comparator sinc filter data
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the Comparator sinc filter data output.
 *
 * @return Returns the Comparator sinc filter data output.
 *
 */
uint16_t SDFM_getComparatorSincData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return (uint16_t)READ_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCDATA);
}

/**
 *
 * @brief Return the FIFO data
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the latest FIFO data.
 *
 * @return Returns the latest FIFO data.
 *
 * \note Discard the upper 16 bits if the output data format is 16bits.
 *
 */
uint32_t SDFM_getFIFOData(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return(SDFMx->SDCHNX_GRP[filterNumber].FIFO_DATA);
}

/**
 *
 * @brief Set the FIFO interrupt level.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param fifoLevel is the FIFO interrupt level.
 *
 * This function sets the FIFO interrupt level. Interrupt is generated when
 * the FIFO buffer word count gets to or exceeds the value of \b fifoLevel.
 * Maximum value for \b fifoLevel is 16.
 *
 */
void SDFM_setFIFOInterruptLevel(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint16_t fifoLevel)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_SDFM_FIFO_THRESHOLD(fifoLevel));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDFIFOCTL, SDFM0_SDCHNX_GRP_SDFIFOCTL_SDFFIL_Msk,
               (uint32_t)fifoLevel << SDFM0_SDCHNX_GRP_SDFIFOCTL_SDFFIL_Pos);
}

/**
 *
 * @brief Set data ready interrupt source.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param dataReadySource is the data ready interrupt source.
 *
 * This function sets the data ready interrupt source.
 * Valid values for \b dataReadySource:
 *   - SDFM_DATA_READY_SOURCE_DIRECT - Direct data ready
 *   - SDFM_DATA_READY_SOURCE_FIFO  - FIFO data ready.
 *
 */
void SDFM_setDataReadyInterruptSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                      SDFM_DataReadyInterruptSource dataReadySource)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDFIFOCTL, SDFM0_SDCHNX_GRP_SDFIFOCTL_DRINTSEL_Msk,
               (uint32_t)dataReadySource << SDFM0_SDCHNX_GRP_SDFIFOCTL_DRINTSEL_Pos);
}

/**
 *
 * @brief Get the wait-for-sync event status.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function returns the Wait-for-Sync event status.
 *
 * @return Returns \b true if sync event has occurred.
 *         Returns \b false if sync event has not occurred.
 *
 */
bool SDFM_getWaitForSyncStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_WTSYNFLG_RPT_Msk) != 0;
}

/**
 *
 * @brief Clear the Wait-for-sync event status.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function clears the Wait-for-sync event status.
 *
 */
void SDFM_clearWaitForSyncFlag(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDCLRSTS, SDFM0_SDCHNX_GRP_SDCLRSTS_WTSYNCLR_Msk);
}

/**
 *
 * @brief Enable wait for sync mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function enables the wait for sync mode. Data to FIFO will be written
 * only after PWM sync event.
 *
 */
void SDFM_enableWaitForSync(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_WTSYNCEN_Msk);
}

/**
 *
 * @brief Disable wait for sync mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 *
 * This function disables the wait for sync mode. Data to FIFO will be written
 * every Data ready event.
 *
 */
void SDFM_disableWaitForSync(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_WTSYNCEN_Msk);
}

/**
 *
 * @brief Set the PWM sync mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param syncSource is the PWM sync source.
 *
 * This function sets the PWM sync source for the specific SDFM filter. Valid
 * values for syncSource are SDFM_SYNC_PWMx_CMPy. Where x ranges from 1 to 8
 * Representing PWM1 to PWM8 respectively and y ranges from A to D
 * representing PWM comparators A to D.
 *
 */
void SDFM_setPWMSyncSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_PWMSyncSource syncSource)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    WRITE_REG(SDFMx->SDCHNX_GRP[filterNumber].SDSYNC, (uint32_t)syncSource << SDFM0_SDCHNX_GRP_SDSYNC_SYNCSEL_Pos);
}

/**
 *
 * @brief Set FIFO clear on sync mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param fifoClearSyncMode is the FIFO clear on sync mode.
 *
 * This function sets the FIFO clear mode for the specified filter when a sync
 * happens depending on the value of fifoClearSyncMode.
 * Valid values for fifoClearSyncMode are:
 *  - SDFM_FIFO_NOT_clearED_ON_SYNC - FIFO is not cleared on sync.
 *  - SDFM_FIFO_clearED_ON_SYNC - FIFO is cleared on sync.
 *
 */
void SDFM_setFIFOClearOnSyncMode(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                 SDFM_FIFOClearSyncMode fifoClearSyncMode)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_FFSYNCLREN_Msk,
               (uint32_t)fifoClearSyncMode << SDFM0_SDCHNX_GRP_SDEN_FFSYNCLREN_Pos);
}

/**
 *
 * @brief Set Wait-for-sync clear mode.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param syncClearMode is the wait-for-sync clear mode.
 *
 * This function sets the Wait-For-sync clear mode depending on the value of
 * syncClearMode.
 * Valid values for syncClearMode are:
 *   - SDFM_MANUAL_clear_WAIT_FOR_SYNC - Wait-for-sync flag is cleared by
 *                                       invoking SDFM_clearWaitForSyncFlag().
 *   - SDFM_AUTO_clear_WAIT_FOR_SYNC   - Wait-for-sync flag is cleared
 *                                       automatically on FIFO interrupt.
 *
 */
void SDFM_setWaitForSyncClearMode(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                  SDFM_WaitForSyncClearMode syncClearMode)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_WTSCLREN_Msk,
               (uint32_t)syncClearMode << SDFM0_SDCHNX_GRP_SDEN_WTSCLREN_Pos);
}

/**
 * @brief Selects clock source for SDFM channels.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param clkSource is the clock source
 *
 * This function selects the clock for SDFM module filter channels.
 * Valid values for clkSource are:
 *   - SDFM_CLK_SOURCE_CHANNEL_CLK - Respective channel's clk is the source
 *   - SDFM_CLK_SOURCE_SD1_CLK     - Filter 1 clock is the source
 *
 */
void SDFM_selectClockSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                            SDFM_ClockSource clkSource)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCTLPARM, SDFM0_SDCHNX_GRP_SDCTLPARM_SDCLKSEL_Msk,
               (uint32_t)clkSource << SDFM0_SDCHNX_GRP_SDCTLPARM_SDCLKSEL_Pos);
}

/**
 * @brief Selects comparator event High source
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param source is the comparator event High source
 */
void SDFM_selectCompEventHighSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventHighSource source)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCOMPXCTL, SDFM0_SDCHNX_GRP_SDCOMPXCTL_CEVT2DIGFILTSEL_Msk,
               (uint32_t)source << SDFM0_SDCHNX_GRP_SDCOMPXCTL_CEVT2DIGFILTSEL_Pos);
}

/**
 * @brief Selects comparator event low source
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param source is the comparator event low source
 */
void SDFM_selectCompEventLowSource(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, SDFM_CompEventLowSource source)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCOMPXCTL, SDFM0_SDCHNX_GRP_SDCOMPXCTL_CEVT1DIGFILTSEL_Msk,
               (uint32_t)source << SDFM0_SDCHNX_GRP_SDCOMPXCTL_CEVT1DIGFILTSEL_Pos);
}

/**
 * @brief Initializes Comparator Event Low Filter.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 */
void SDFM_initCompEventLowFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCTL, SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT1_FILINIT_Msk);
}

/**
 * @brief Initializes Comparator Event High Filter.
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 */
void SDFM_initCompEventHighFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCTL, SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT2_FILINIT_Msk);
}

/**
 * @brief Lock Comparator Event Filter Configurations
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param SDFM_SDCOMPLOCK_SdcompctlEn  Locks write access to SDCOMPCTL register
 * @param SDFM_SDCOMPLOCK_CompEn Locks write access to SDCOMPxFILCTL & SDCOMPxFILCLKCTL register
 */
void SDFM_lockCompEventFilterConfig(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                    ControlStatus SDFM_SDCOMPLOCK_SdcompctlEn, ControlStatus SDFM_SDCOMPLOCK_CompEn)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCOMPXLOCK,
               SDFM0_SDCHNX_GRP_SDCOMPXLOCK_SDCOMP1CTL_Msk | SDFM0_SDCHNX_GRP_SDCOMPXLOCK_COMP_Msk,
               (uint32_t)SDFM_SDCOMPLOCK_SdcompctlEn << SDFM0_SDCHNX_GRP_SDCOMPXLOCK_COMP_Pos |
               (uint32_t)SDFM_SDCOMPLOCK_CompEn << SDFM0_SDCHNX_GRP_SDCOMPXLOCK_SDCOMP1CTL_Pos);
}

/**
 * @brief  Configures SDFM comparator for filter config & threshold values
 *
 * @param SDFMx is the base address of the SDFM module
 * @param comparatorConfig is the filter number, filter type & over sampling ratio,
 *                                  high-level and low-level threshold 1 values,
 *                                  zero-cross threshold value.
 */
void SDFM_configComparator(SDFM_Type *SDFMx, ComparatorConfigParam *comparatorConfig)
{
    SDFM_FilterNumber filter;
    uint8_t           ratio;
    SDFM_FilterType   filterType;

    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    filter     = comparatorConfig->config1_filterNumber;
    ratio      = comparatorConfig->config1_overSamplingRatio;
    filterType = comparatorConfig->config1_filterType;

    SDFM_setComparatorFilterType(SDFMx, filter, filterType);

    SDFM_setCompFilterOverSamplingRatio(SDFMx, filter, ratio);

    SDFM_setCompFilterHighThreshold(SDFMx, filter, (uint16_t)comparatorConfig->config2_highThreshold, 0U);

    SDFM_setCompFilterLowThreshold(SDFMx, filter, (uint16_t)comparatorConfig->config2_lowThreshold, 0U);

    if (comparatorConfig->zeroCrossThresholdEn)
    {
        SDFM_setCompFilterZeroCrossThreshold(SDFMx, filter, comparatorConfig->config3_zeroCrossThreshold);
        SDFM_enableZeroCrossEdgeDetect(SDFMx, filter);
    }
}

/**
 * @brief Configure SDFM enhanced comparator for filter config & threshold values
 *
 * @param SDFMx is the base address of the SDFM module
 * @param enhancedComparatorConfig is the filter number, filter type & over sampling ratio,
 *                                  high-level and low-level threshold 1 values,
 *                                  high-level and low-level threshold 2 values,
 *                                  zero-cross threshold value.
 */
void SDFM_configEnhancedComparator(SDFM_Type *SDFMx, enhancedComparatorConfigParam *enhancedComparatorConfig)
{
    SDFM_FilterNumber filter;
    uint8_t           ratio;
    SDFM_FilterType   filterType;

    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    filter     = enhancedComparatorConfig->filterConfig_filterNumber;
    ratio      = enhancedComparatorConfig->filterConfig_overSamplingRatio;
    filterType = enhancedComparatorConfig->filterConfig_filterType;

    SDFM_setComparatorFilterType(SDFMx, filter, filterType);

    SDFM_setCompFilterOverSamplingRatio(SDFMx, filter, ratio);

    SDFM_setCompFilterHighThreshold(SDFMx, filter, enhancedComparatorConfig->highThreshold1,
                                    enhancedComparatorConfig->highThreshold2);

    SDFM_setCompFilterLowThreshold(SDFMx, filter, enhancedComparatorConfig->lowThreshold1,
                                   enhancedComparatorConfig->lowThreshold2);

    if (enhancedComparatorConfig->zeroCrossThresholdEn)
    {
        SDFM_setCompFilterZeroCrossThreshold(SDFMx, filter, enhancedComparatorConfig->zeroCrossThreshold);
        SDFM_enableZeroCrossEdgeDetect(SDFMx, filter);
    }
}

/**
 * @brief Configure SDFM data filter
 *
 * @param SDFMx  is the base address of the SDFM module
 * @param datafilterConfig is the filter number, filter type and over sampling ratio configuration,
 *                         and filter switch, data representation and data shift values configuration
 */
void SDFM_configDataFilter(SDFM_Type *SDFMx, dataFilterConfigParam *datafilterConfig)
{
    SDFM_FilterNumber filter;
    uint16_t          ratio;
    SDFM_FilterType   filterType;

    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    filter     = datafilterConfig->config1_filterNumber;
    ratio      = datafilterConfig->config1_overSamplingRatio;
    filterType = datafilterConfig->config1_filterType;

    SDFM_setFilterType(SDFMx, filter, filterType);

    SDFM_setFilterOverSamplingRatio(SDFMx, filter, ratio);

    if (datafilterConfig->config2_FilterEn)
    {
        SDFM_enableFilter(SDFMx, filter);
    }
    else
    {
        SDFM_disableFilter(SDFMx, filter);
    }

    SDFM_setOutputDataFormat(SDFMx, filter, datafilterConfig->config2_dataFormat);

    if (datafilterConfig->config2_dataFormat == SDFM_DATA_FORMAT_16_BIT)
    {
        SDFM_setDataShiftValue(SDFMx, filter, datafilterConfig->config2_shiftValue);
    }
}

/**
 * @brief Configure SDFM comparator Zero Cross threshold
 *
 * @param SDFMx is the base address of the SDFM module
 * @param zeroCrossThresholdConfig  is the filter number, filter type and over sampling ratio
 *                                  and zero cross threshold value.
 */
void SDFM_configZeroCrossComparator(SDFM_Type *SDFMx, zeroCrossThresholdConfigParam *zeroCrossThresholdConfig)
{
    SDFM_FilterNumber filter;
    uint8_t           ratio;
    SDFM_FilterType   filterType;

    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    filter     = zeroCrossThresholdConfig->config1_filterNumber;
    ratio      = zeroCrossThresholdConfig->config1_overSamplingRatio;
    filterType = zeroCrossThresholdConfig->config1_filterType;

    SDFM_setComparatorFilterType(SDFMx, filter, filterType);

    SDFM_setCompFilterOverSamplingRatio(SDFMx, filter, ratio);

    SDFM_setCompFilterZeroCrossThreshold(SDFMx, filter, zeroCrossThresholdConfig->config2_zeroCrossThreshold);
}

/**
 * @brief Configure SDFM data filter FIFO
 *
 * @param SDFMx is the base address of the SDFM module
 * @param dataFilterFIFOConfig  is the filter number, filter type and over sampling ratio
 *               configuration; data representation and data shift values and FIFO level configuration.
 */
void SDFM_configDataFilterFIFO(SDFM_Type *SDFMx, dataFilterFIFOConfigParam *dataFilterFIFOConfig)
{
    SDFM_FilterNumber filter;
    uint16_t          ratio;
    SDFM_FilterType   filterType;

    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    filter     = dataFilterFIFOConfig->config1_filterNumber;
    ratio      = dataFilterFIFOConfig->config1_overSamplingRatio;
    filterType = dataFilterFIFOConfig->config1_filterType;

    SDFM_setFilterType(SDFMx, filter, filterType);

    SDFM_setFilterOverSamplingRatio(SDFMx, filter, ratio);

    if (dataFilterFIFOConfig->config2_FilterSwitch)
    {
        SDFM_enableFilter(SDFMx, filter);
    }
    else
    {
        SDFM_disableFilter(SDFMx, filter);
    }

    SDFM_setOutputDataFormat(SDFMx, filter, dataFilterFIFOConfig->config2_DataRepresentation);

    if (dataFilterFIFOConfig->config2_DataRepresentation == SDFM_DATA_FORMAT_16_BIT)
    {
        SDFM_setDataShiftValue(SDFMx, filter, dataFilterFIFOConfig->config2_shiftValue);
    }

    SDFM_setFIFOInterruptLevel(SDFMx, filter, dataFilterFIFOConfig->config2_fifoLevel);
    SDFM_enableFIFOBuffer(SDFMx, filter);
}

/**
 * @brief Configure Comparator Event Low Filter
 *
 * @param SDFMx is the base address of the SDFM module.
 * @param filterNumber is the filter number.
 * @param config is the comparator event high source
 */
void SDFM_configCompEventLowFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                   const SDFM_CompEventFilterConfig *config)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_SDFM_CLK_PRESCALE(config->clkPrescale));
    assert_param(IS_SDFM_SAMPLE_WINDOW(config->sampleWindow));
    assert_param(IS_SDFM_THRESHOLD(config->threshold));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCTL,
               SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT1_SAMPWIN_Msk | SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT1_THRESH_Msk,
               (uint32_t)config->sampleWindow << SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT1_SAMPWIN_Pos |
               (uint32_t)config->threshold << SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT1_THRESH_Pos);

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCLKCTL, SDFM0_SDCHNX_GRP_EVTFLTCLKCTL_CEVT1_CLKPRESCALE_Msk,
               (uint32_t)config->clkPrescale << SDFM0_SDCHNX_GRP_EVTFLTCLKCTL_CEVT1_CLKPRESCALE_Pos);
}

/**
 * @brief Configure Comparator Event High Filter
 *
 * @param SDFMx is the base address of the SDFM module.
 * @param filterNumber is the filter number.
 * @param config is the comparator event high source
 */
void SDFM_configCompEventHighFilter(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                    const SDFM_CompEventFilterConfig *config)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_SDFM_CLK_PRESCALE(config->clkPrescale));
    assert_param(IS_SDFM_SAMPLE_WINDOW(config->sampleWindow));
    assert_param(IS_SDFM_THRESHOLD(config->threshold));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCTL,
               SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT2_SAMPWIN_Msk | SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT2_THRESH_Msk,
               (uint32_t)config->sampleWindow << SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT2_SAMPWIN_Pos |
               (uint32_t)config->threshold << SDFM0_SDCHNX_GRP_EVTFLTCTL_CEVT2_THRESH_Pos);

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].EVTFLTCLKCTL, SDFM0_SDCHNX_GRP_EVTFLTCLKCTL_CEVT2_CLKPRESCALE_Msk,
               (uint32_t)config->clkPrescale << SDFM0_SDCHNX_GRP_EVTFLTCLKCTL_CEVT2_CLKPRESCALE_Pos);
}

/**
 * @brief set data and clock signal reverse
 *
 * @param SDFMx        Pointer to the SDFM_Type structure that contains the configuration registers.
 * @param filterNumber The number of the filter to configure.
 * @param dataReverseEn The reverse state of the data signal. Can be ENABLE or DISABLE.
 * @param clkReverseEn  The reverse state of the clock signal. Can be ENABLE or DISABLE.
 */
void SDFM_setDataClockReverse(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, ControlStatus dataReverseEn,
                              ControlStatus clkReverseEn)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCTLPARM,
               SDFM0_SDCHNX_GRP_SDCTLPARM_SDDATA_RVS_Msk | SDFM0_SDCHNX_GRP_SDCTLPARM_SDCLK_RVS_Msk,
               (uint32_t)dataReverseEn << SDFM0_SDCHNX_GRP_SDCTLPARM_SDCLK_RVS_Pos |
               (uint32_t)clkReverseEn << SDFM0_SDCHNX_GRP_SDCTLPARM_SDCLKSEL_Pos);
}

/**
 * @brief set data filter decimation count start value
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param dataFilterDecimationCountStartValue
 */
void SDFM_setDataFilterDecimationCountStartValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                                 uint16_t dataFilterDecimationCountStartValue)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDDFPARM, SDFM0_SDCHNX_GRP_SDDFPARM_DFDSV_Msk,
               (uint32_t)dataFilterDecimationCountStartValue << SDFM0_SDCHNX_GRP_SDDFPARM_DFDSV_Pos);
}

/**
 * @brief set comparator filter decimation count start value
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param compFilterDecimationCountStartValue
 */
void SDFM_setCompFilterDecimationCountStartValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber,
                                                 uint16_t compFilterDecimationCountStartValue)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    MODIFY_REG(SDFMx->SDCHNX_GRP[filterNumber].SDCPARM, SDFM0_SDCHNX_GRP_SDCPARM_CFDSV_Msk,
               (uint32_t)compFilterDecimationCountStartValue << SDFM0_SDCHNX_GRP_SDCPARM_CFDSV_Pos);
}

/**
 * @brief get data filter decimation current value
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return uint16_t
 */
uint16_t SDFM_getDataFilterDecimationValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS,
                    SDFM0_SDCHNX_GRP_SDSTS_MSF_DCNT_RPT_Msk) >>
           SDFM0_SDCHNX_GRP_SDSTS_MSF_DCNT_RPT_Pos;
}

/**
 * @brief get comparator filter decimation count current value
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return uint16_t
 */
uint16_t SDFM_getCompFilterDecimationValue(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_CSF_DCNT_RPT_Msk) >>
           SDFM0_SDCHNX_GRP_SDSTS_CSF_DCNT_RPT_Pos;
}

/**
 * @brief get CEVT2 status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return Returns \b true if event2 has occurred.
 *         Returns \b false if event2 has not occurred.
 *
 */
bool SDFM_getCEVT2Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_FLT_CEVT2_RPT_Msk) != 0;
}

/**
 * @brief get CEVT1 status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return Returns \b true if event1 has occurred.
 *         Returns \b false if event1 has not occurred.
 *
 */
bool SDFM_getCEVT1Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDSTS, SDFM0_SDCHNX_GRP_SDSTS_FLT_CEVT1_RPT_Msk) != 0;
}

/**
 * @brief clear main interrupt
 *
 * @param SDFMx is the base address of the SDFM module
 *
 */
void SDFM_clearMainInterrupt(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDMCLR, SDFM0_SDMCLR_MIF_CLR_Msk);
}

/**
 * @brief get main interrupt
 *
 * @param SDFMx is the base address of the SDFM module
 * @return Returns \b true if main interrupt event has occurred.
 *         Returns \b false if main interrupt event has not occurred.
 *
 */
bool SDFM_getMainInterruptStatus(SDFM_Type *SDFMx)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_BIT(SDFMx->SDMSTS, SDFM0_SDMSTS_MIF_RPT_Msk) != 0;
}

/**
 * @brief mask interrupt
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param interruptMasks ref to SDFM_IT_xxx is a bitmask specifying which interrupts to mask.
 *  Valid values for intterrupt are:
 *  SDFM_IT_CEVT1_MASK
 *  SDFM_IT_CEVT2_MASK
 *  SDFM_IT_MODULATOR_FAILURE_MASK
 *  SDFM_IT_FIFO_OVERFLOW_MASK
 *  SDFM_IT_FIFO_WRITE_MASK
 *  SDFM_IT_FIFO_READ_MASK
 *  SDFM_IT_DATA_READY_MASK
 */
void SDFM_setInterruptMask(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_INTERRUPT_MASKS(interruptMasks));

    SET_BIT(SDFMx->INT_MASK, (uint32_t)interruptMasks << (filterNumber * SDFM_FILTER_INTERRUPT_STEP));
}

/**
 * @brief unmask interrupt mask
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param interruptMasks ref to SDFM_IT_xxx
 *  Valid values for intterrupt are:
 *  SDFM_IT_CEVT1_MASK
 *  SDFM_IT_CEVT2_MASK
 *  SDFM_IT_MODULATOR_FAILURE_MASK
 *  SDFM_IT_FIFO_OVERFLOW_MASK
 *  SDFM_IT_FIFO_WRITE_MASK
 *  SDFM_IT_FIFO_READ_MASK
 *  SDFM_IT_DATA_READY_MASK
 */
void SDFM_clearInterruptMask(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->INT_MASK, (uint32_t)interruptMasks << (filterNumber * SDFM_FILTER_INTERRUPT_STEP));
}

/**
 * @brief get interrupt status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return uint32_t
 */
uint32_t SDFM_getInterruptStatusRaw(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_REG(SDFMx->INT_RAW_RPT) >> (filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 * @brief get interrupt status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @return uint32_t
 */
uint32_t SDFM_getInterruptStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    return READ_REG(SDFMx->INT_STATUS_RPT) >> (filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 * @brief enable DMA read and write
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_enableDMA(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_DMA_EN_Msk);
}

/**
 * @brief disable DMA comunication
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_disableDMA(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_DMA_EN_Msk);
}

/**
 * @brief enable filter ack
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_enableAck(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_AE_Msk);
}

/**
 * @brief disable filter ack
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_disableAck(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_AE_Msk);
}

/**
 * @brief enable CEVT1
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_enableCEVT1(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEVT1_EN_Msk);
}

/**
 * @brief disable CEVT1
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_disableCEVT1(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEVT1_EN_Msk);
}

/**
 * @brief enable CEVT2
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_enableCEVT2(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEVT2_EN_Msk);
}

/**
 * @brief disable CEVT2
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_disableCEVT2(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    CLEAR_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDEN, SDFM0_SDCHNX_GRP_SDEN_CEVT2_EN_Msk);
}

/**
 * @brief clear CEVT1 status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_clearCEVT1Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDCLRSTS, SDFM0_SDCHNX_GRP_SDCLRSTS_FLT_CEVT1_CLR_Msk);
}

/**
 * @brief  clear CEVT2 status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_clearCEVT2Status(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDCLRSTS, SDFM0_SDCHNX_GRP_SDCLRSTS_FLT_CEVT2_CLR_Msk);
}

/**
 * @brief clear ack flag status
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number
 */
void SDFM_clearAckFlagStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));

    SET_BIT(SDFMx->SDCHNX_GRP[filterNumber].SDCLRSTS, SDFM0_SDCHNX_GRP_SDCLRSTS_AF_CLR_Msk);
}

/**
 * @brief force trigger SDFM interrupt
 *
 * @param SDFMx is the base address of the SDFM module
 * @param filterNumber is the filter number.
 * @param interruptMasks  ref to SDFM_IT_xxxx
 */
void SDFM_forceInterrupt(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    assert_param(IS_SDFM_ALL_PERIPH(SDFMx));
    assert_param(IS_INTERRUPT_MASKS(interruptMasks));

    SET_BIT(SDFMx->INT_FORCE_IND, (uint32_t)interruptMasks << filterNumber * SDFM_FILTER_INTERRUPT_STEP);
}

/**
 * @brief cleaer SDFM interrupt
 *
 * @param SDFMx  is the base address of the SDFM module
 * @param filterNumber is the filter number
 * @param interruptMasks ref to SDFM_IT_xxxx
 */
void SDFM_clearInterruptStatus(SDFM_Type *SDFMx, SDFM_FilterNumber filterNumber, uint32_t interruptMasks)
{
    SDFM_clearInterruptFlag(SDFMx, filterNumber, interruptMasks);
}
