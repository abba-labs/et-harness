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
#include "et6x_wag.h"

#define WAG_MAX_PRESCALER                 (4095)
#define WAG_MAX_CORDIC_ITERATION_CYCLE    (0x1FUL)


/**
 * @brief Enable the WAG module
 */
void WAG_enableModule(void)
{
    SET_BIT(WAG->EN, WAG_EN_WAG_EN_Msk);
}

/**
 * @brief Disable the WAG module
 */
void WAG_disableModule(void)
{
    CLEAR_BIT(WAG->EN, WAG_EN_WAG_EN_Msk);
}

/**
 * @brief Enable the WAG DMA request
 */
void WAG_enableDMARequest(void)
{
    SET_BIT(WAG->DMA_EN, WAG_DMA_EN_WAG_DMA_EN_Msk);
}

/**
 * @brief Disable the WAG DMA request
 */
void WAG_disableDMARequest(void)
{
    CLEAR_BIT(WAG->DMA_EN, WAG_DMA_EN_WAG_DMA_EN_Msk);
}

/**
 * @brief Configures the WAG module parameters.
 *
 * This function configures the parameters of the WAG module using the provided
 * configuration structure. It ensures that the parameters are within the allowable
 * range and writes them to the corresponding registers of the WAG module.
 *
 * @param config A pointer to the WAG_ConfigParam structure containing the parameters
 *               to be configured. The structure includes:
 *               - prescaler: The prescaler value for the WAG module clock.
 *               - cordicIterationCycle: The number of CORDIC iteration cycles.
 *               - loadmode: The load mode for the WAG module.
 *               - startTriggerMode: The start trigger mode.
 *               - stopTriggerMode: The stop trigger mode.
 *               - startTriggerInvertEn: Enable/disable start trigger inversion.
 *               - stopTriggerInvertEn: Enable/disable stop trigger inversion.
 *               - waveType: The type of waveform to generate.
 *               - staticWaveLoadMode: The load mode for static wave (if applicable).
 *               - squareWaveOutputMode: The output mode for square wave (if applicable).
 *               - rampWaveMode: The mode for ramp wave (if applicable).
 *               - triangleStartDirSel: The start direction for triangle wave (if applicable).
 *               - triangleWaveOutputMode: The output mode for triangle wave (if applicable).
 */
void WAG_config(WAG_ConfigParam *config)
{
    assert_param(config->prescaler <= WAG_MAX_PRESCALER);
    assert_param(config->cordicIterationCycle <= WAG_MAX_CORDIC_ITERATION_CYCLE);

    WRITE_REG(WAG->CLK_DIV_PARA, (uint32_t)config->prescaler << WAG_CLK_DIV_PARA_WAG_CLK_DIV_PARA_Pos);
    WRITE_REG(WAG->CORDIC_CTRL0, (uint32_t)config->cordicIterationCycle << WAG_CORDIC_CTRL0_CORDIC_NOI_Pos);
    WRITE_REG(WAG->RLOAD_MODE, (uint32_t)config->loadmode << WAG_RLOAD_MODE_WAG_RLOAD_MODE_Pos);
    WRITE_REG(WAG->TRIG_SEL, ((uint32_t)config->startTriggerMode << WAG_TRIG_SEL_WAG_TRIG_ON_SEL_Pos) |
              ((uint32_t)config->stopTriggerMode << WAG_TRIG_SEL_WAG_TRIG_OFF_SEL_Pos));
    WRITE_REG(WAG->TRIG_PULSE_INV,
              ((uint32_t)config->startTriggerInvertEn << WAG_TRIG_PULSE_INV_WAG_TRIG_ON_PULSE_INV_Pos) |
              ((uint32_t)config->stopTriggerInvertEn << WAG_TRIG_PULSE_INV_WAG_TRIG_OFF_PULSE_INV_Pos));
    WRITE_REG(WAG->WAVE_SEL, (uint32_t)config->waveType << WAG_WAVE_SEL_WAG_WAVE_SEL_Pos);

    switch (config->waveType)
    {
    case WAG_WAVETYPE_STATIC:
        WRITE_REG(WAG->STAWAVE_LOAD_MODE,
                  (uint32_t)config->staticWaveLoadMode << WAG_STAWAVE_LOAD_MODE_WAG_STAWAVE_LOAD_MODE_Pos);
        break;

    case WAG_WAVETYPE_SQUARE:
        WRITE_REG(WAG->SQURWAVE_MODE,
                  (uint32_t)config->squareWaveOutputMode << WAG_SQURWAVE_MODE_WAG_SQURWAVE_MODE_Pos);
        break;

    case WAG_WAVETYPE_RAMP:
        WRITE_REG(WAG->RAMP_DIR, (uint32_t)config->rampWaveMode << WAG_RAMP_DIR_WAG_RAMP_DIR_Pos);
        break;

    case WAG_WAVETYPE_TRIANGLE:
        WRITE_REG(WAG->TRIWAVE_DIR, (uint32_t)config->triangleStartDirSel << WAG_TRIWAVE_DIR_WAG_TRIWAVE_DIR_Pos);
        WRITE_REG(WAG->TRIWAVE_MODE, (uint32_t)config->triangleWaveOutputMode << WAG_TRIWAVE_MODE_WAG_TRIWAVE_MODE_Pos);
        break;

    case WAG_WAVETYPE_SINE:
        break;
    }
}

/**
 * @brief Set the triangle wave rising step
 *
 * @param value The rising step value of the triangle wave
 * @note The value is 0~4095
 */
void WAG_setTriangleUpStep(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_HR1_Msk, (uint32_t)value << WAG_R1_WAG_HR1_Pos);
}

/**
 * @brief Set the triangle wave falling step
 *
 * @param value The falling step value of the triangle wave
 * @note The value is 0~4095
 */
void WAG_setTriangleDownStep(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_LR1_Msk, (uint32_t)value << WAG_R1_WAG_LR1_Pos);
}

/**
 * @brief Set the triangle wave high threshold
 *
 * @param value The high threshold value of the triangle wave
 * @note The value is 0~4095
 */
void WAG_setTriangleHThrd(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_HR2_Msk, (uint32_t)value << WAG_R2_WAG_HR2_Pos);
}

/**
 * @brief Set the triangle wave low threshold
 *
 * @param value The low threshold value of the triangle wave
 * @note The value is 0~4095
 */
void WAG_setTriangleLThrd(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_LR2_Msk, (uint32_t)value << WAG_R2_WAG_LR2_Pos);
}

/**
 * @brief Set the ramp wave rising step
 *
 * @param value The rising step value of the ramp wave
 * @note The value is 0~4095
 */
void WAG_setRampUpStep(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_HR1_Msk, (uint32_t)value << WAG_R1_WAG_HR1_Pos);
}

/**
 * @brief Set the ramp wave falling step
 *
 * @param value The falling step value of the ramp wave
 * @note The value is 0~4095
 */
void WAG_setRampDownStep(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_LR1_Msk, (uint32_t)value << WAG_R1_WAG_LR1_Pos);
}

/**
 * @brief Set the high threshold of the ramp wave
 *
 * @param value The high threshold value of the ramp wave
 * @note The value is 0~4095
 */
void WAG_setRampHThrd(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_HR2_Msk, (uint32_t)value << WAG_R2_WAG_HR2_Pos);
}

/**
 * @brief Set the low threshold of the ramp wave
 *
 * @param value The low threshold value of the ramp wave
 * @note The value is 0~4095
 */
void WAG_setRampLThrd(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_LR2_Msk, (uint32_t)value << WAG_R2_WAG_LR2_Pos);
}

/**
 * @brief Set the frequency of the sine wave
 *
 * @param value The frequency value of the sine wave
 * @note Actual frequency calculations：system_clock(200M) / (prescaler + 1) / 4096 * value (HZ)
 */
void WAG_setSineFrq(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_HR1_Msk, (uint32_t)value << WAG_R1_WAG_HR1_Pos);
}

/**
 * @brief Set the phase of the sine wave
 *
 * @param value The phase value of the sine wave
 * @note The value is 0~4095.  correspondence to 0° ~ 360°
 */
void WAG_setSinePhase(uint16_t value)
{
    MODIFY_REG(WAG->R1, WAG_R1_WAG_LR1_Msk, (uint32_t)value << WAG_R1_WAG_LR1_Pos);
}

/**
 * @brief Set the amplitude shift of the sine wave
 *
 * @param value The dc component of the sine wave output superposition
 * @note The value is 0~4095. correspondence to 0 ~ Verf.
 *       y = Output_sine_wave + value.
 */
void WAG_setSineAmplitudeShift(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_HR2_Msk, (uint32_t)value << WAG_R2_WAG_HR2_Pos);
}

/**
 * @brief Set the range scale of the sine wave
 *
 * @param value The output range of the sine wave amplitude
 * @note The value is (0~ 2047) / K. K is about 1.6.
 *        Output_sine_wave = value * sin(ωx + φ) + 2048 >> N
 */
void WAG_setSineRangeScale(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_LR2_Msk, (uint32_t)value << WAG_R2_WAG_LR2_Pos);
}

/**
 * @brief Set the amplitude scale of the sine wave
 *
 * @param value The amplitude scale value of the sine wave
 * @note The value is 0 ~ 12. correspondence to 0 ~ Verf / 2.
 *       Output_sine_wave = A * sin(ωx + φ) + 2048 >> value.
 */
void WAG_setSineAmplitudeScale(uint16_t value)
{
    MODIFY_REG(WAG->R3, WAG_R3_WAG_SINWAVE_OFFSET_SH_Msk, (uint32_t)value << WAG_R3_WAG_SINWAVE_OFFSET_SH_Pos);
}

/**
 * @brief Set the amplitude of the static wave
 *
 * @param value The amplitude value of the static wave
 * @note The value is 0 ~ 4095. correspondence to 0 ~ Verf.
 */
void WAG_setStaticWaveAmplitude(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_LR2_Msk, (uint32_t)value << WAG_R2_WAG_LR2_Pos);
}

/**
 * @brief Set the high range of the square wave
 *
 * @param value The high range value of the square wave
 * @note The value is 0 ~ 4095. correspondence to 0 ~ Verf.
 */
void WAG_setSquareRangeH(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_HR2_Msk, (uint32_t)value << WAG_R2_WAG_HR2_Pos);
}

/**
 * @brief Set the low range of the square wave
 *
 * @param value The low range value of the square wave
 * @note The value is 0 ~ 4095. correspondence to 0 ~ Verf.
 */
void WAG_setSquareRangeL(uint16_t value)
{
    MODIFY_REG(WAG->R2, WAG_R2_WAG_LR2_Msk, (uint32_t)value << WAG_R2_WAG_LR2_Pos);
}

/**
 * @brief Enables the global load for the WAG peripheral.
 */
void WAG_enableGlobalLoad(void)
{
    SET_BIT(WAG->LOAD_EN, WAG_LOAD_EN_WAG_LOAD_EN_Msk);
}

/**
 * @brief Disables the global load for the WAG peripheral.
 */
void WAG_disableGlobalLoad(void)
{
    CLEAR_BIT(WAG->LOAD_EN, WAG_LOAD_EN_WAG_LOAD_EN_Msk);
}

/**
 * @brief Sets the trigger delay for the WAG (Waveform Generation) module.
 *
 * @param triggerDelay The delay value to be set, in the range of 0 to 255.
 */
void WAG_setTriggerDelay(uint16_t triggerDelay)
{
    WRITE_REG(WAG->R0, (uint32_t)triggerDelay << WAG_R0_WAG_R0_Pos);
}

/**
 * @brief Configures the output hold mode for the WAG (Waveform Generation) module.
 *
 * @param codeValue The code value to be set, in the range of 0 ~ 4095.
 * @param holdMode The hold mode to be set, selected from the WAG_OutputHoldMode enum.
 */
void WAG_configOutputHold(uint16_t codeValue, WAG_OutputHoldMode holdMode)
{
    WRITE_REG(WAG->DATA_IN, (uint32_t)codeValue << WAG_DATA_IN_WAG_DATA_IN_Pos);
    WRITE_REG(WAG->HOLD_MODE_SEL, (uint32_t)holdMode << WAG_HOLD_MODE_SEL_WAG_HOLD_MODE_SEL_Pos);
}

/**
 * @brief Starts the trigger for the WAG (Waveform Generation) module.
 */
void WAG_startTriggerStartSingle(void)
{
    SET_BIT(WAG->SOFT_TRIG, WAG_SOFT_TRIG_WAG_SOFT_TRIG_ON_Msk);
}

/**
 * @brief Stops the trigger for the WAG (Waveform Generation) module.
 */
void WAG_startTriggerStopSingle(void)
{
    SET_BIT(WAG->SOFT_TRIG, WAG_SOFT_TRIG_WAG_SOFT_TRIG_OFF_Msk);
}

/**
 * @brief Sets the R0~R3 registers load ready single when global load is enable.
 *
 * @note When global load is enabled, R0~R3 registers load ready single need be set to notice HW
 */
void WAG_setR03LoadReady(void)
{
    SET_BIT(WAG->R3, WAG_R3_WAG_R3_Msk);
}

/**
 * @brief Checks if the R0~R3 registers load is complete when global load is enabled.
 *
 * This function checks the status of the WAG_R3_WAG_R3_Msk bit in the WAG->R3 register.
 * When the global load is enabled, the R0 ~ R3 registers are loaded at the same time.
 * This function returns true if the load is complete (WAG_R3_WAG_R3_Msk bit is cleared),
 * indicating that the R0~R3 registers have been loaded into the hardware.
 *
 * @return bool - Returns true if the R0~R3 registers load is complete, false otherwise.
 */
bool WAG_isR03LoadComplete(void)
{
    return (bool)(READ_BIT(WAG->R3, WAG_R3_WAG_R3_Msk) == 0);
}

/**
 * @brief Reads the status register of the WAG (Waveform Generation) module.
 *
 * @return uint16_t - The status of the WAG module.
 */
uint16_t WAG_getStatus(void)
{
    return (uint16_t)READ_REG(WAG->STATUS);
}
