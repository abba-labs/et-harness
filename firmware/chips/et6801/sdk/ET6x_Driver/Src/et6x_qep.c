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

#include "et6x_qep.h"

#define IS_QEP_PERIPH(PERIPH)                (((PERIPH) == QEP0) || ((PERIPH) == QEP1))

#define IS_QEP_INIT_MODE(MODE)               (((MODE) & 0xfffff0ffU) == 0U)

#define IS_QEP_COMPARE_PULSE_WIDTH(WIDTH)    (((WIDTH) < 0x1001U) & ((WIDTH) != 0U))

#define IS_QEP_LACTCH_MODE(MODE)             (((MODE) & 0xffffff8bU) == 0U)

#define IS_QEP_CLEAR_STATUS_FLAG(FLAG)       (((FLAG) & 0x71U) == 0U)
#define  IS_QEP_FILTER_LEN(LEN)              ((LEN) < 0x400U)

/**
 * @brief enable the eqep module
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_enableModule(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_QPEN_Msk);
}

/**
 * @brief disable the eqep module
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_disableModule(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_QPEN_Msk);
}

/**
 * @brief Enables the eQEP module edge-capture unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_enableCapture(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->CTRL2, QEP0_CTRL2_CFG2CAP_EN_Msk);
}

/**
 * @brief disables the eQEP module edge-capture unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_disableCapture(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->CTRL2, QEP0_CTRL2_CFG2CAP_EN_Msk);
}

/**
 * @brief Enables the eQEP module unit timer.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param period \e period is period value at which a unit time-out interrupt is set.
 */
void QEP_enableUnitTimer(QEP_Type *QEPx, uint32_t period)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    WRITE_REG(QEPx->UPRD, period);

    SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2UT_EN_Msk);
}

/**
 * @brief disables the eQEP module unit timer.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_disableUnitTimer(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2UT_EN_Msk);
}

/**
 * @brief Loads the eQEP module unit timer period as number of SYSCLK cycles.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param period \e period is period value at which a unit time-out interrupt is set.
 */
void QEP_loadUnitTimer(QEP_Type *QEPx, uint32_t period)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    WRITE_REG(QEPx->UPRD, period);
}

/**
 * @brief Configures eQEP module's quadrature decoder unit.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 *  - QEP0
 *  - QEP1
 * @param config The \e config parameter provides the configuration of the decoder and is the logical OR of several
 * values:
 *  - specify if both rising and falling edges should be counted or just rising edges, by the following options:
 *      \b QEP_CONFIG_2X_RESOLUTION or
 *      \b QEP_CONFIG_1X_RESOLUTION
 *  - specify if quadrature signals are being provided on QEPA and QEPB, if a direction signal and a clock are being
 * provided,
 * or if the direction should be hard-wired for a single direction with QEPA used for input, by the following options:
 *      \b QEP_CONFIG_QUADRATURE, or
 *      \b QEP_CONFIG_CLOCK_DIR,  or
 *      \b QEP_CONFIG_UP_COUNT    or
 *      \b QEP_CONFIG_DOWN_COUNT
 *  - specify if the signals provided on QEPA and QEPB should be swapped before being processed, by the following
 * options:
 *      \b QEP_CONFIG_NO_SWAP or
 *      \b QEP_CONFIG_SWAP
 *  - specify if the gating of the index pulse should be enabled or disabled, by the following options:
 *      \b QEP_CONFIG_IGATE_DISABLE or
 *      \b QEP_CONFIG_IGATE_ENABLE
 */
void QEP_setDecoderConfig(QEP_Type *QEPx, uint32_t config)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    config &= (QEP0_CTRL1_CFG2DEC_SWAP_Msk | QEP0_CTRL1_CFG2DEC_XCR_Msk |
               QEP0_CTRL1_CFG2DEC_QSRC_Msk | QEP0_CTRL1_CFG2DEC_IGATE_Msk);

    MODIFY_REG(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_SWAP_Msk | QEP0_CTRL1_CFG2DEC_XCR_Msk |
               QEP0_CTRL1_CFG2DEC_QSRC_Msk | QEP0_CTRL1_CFG2DEC_IGATE_Msk,
               config);
}

/**
 * @brief Configures eQEP module position counter unit.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 *  - QEP0
 *  - QEP1
 * @param mode
 *  - QEP_POSITION_RESET_IDX
 *  - QEP_POSITION_RESET_MAX_POS
 *  - QEP_POSITION_RESET_1ST_IDX
 *  - QEP_POSITION_RESET_UNIT_TIME_OUT
 * @param maxPosition \e maxPosition is the maximum value of the position counter
 * and is the value used to reset the position capture when moving in the reverse(negative) direction.
 * range :0x0 ~ 0xFFFFFFFF
 */
void QEP_setPositionCounterConfig(QEP_Type *QEPx, QEP_PositionResetMode mode, uint32_t maxPosition)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_PCRM_Msk,
               (uint32_t)mode << QEP0_CTRL1_CFG2PCCU_PCRM_Pos);

    WRITE_REG(QEPx->POSMAX, maxPosition);
}

/**
 * @brief Configures eQEP module edge-capture unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param capPrescaler capPrescaler is the prescaler setting of the eQEP capture timer clk.
 * @param evntPrescaler evntPrescaler is the prescaler setting of the unit position event frequency.
 */
void QEP_setCaptureConfig(QEP_Type *QEPx, QEP_CAPCLKPrescaler capPrescaler, QEP_UPEVNTPrescaler evntPrescaler)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->CTRL2, QEP0_CTRL2_CFG2CAP_CPPS_Msk |
               QEP0_CTRL2_CFG2CAP_UPPS_Msk,
               (uint32_t)capPrescaler << QEP0_CTRL2_CFG2CAP_CPPS_Pos |
               (uint32_t)evntPrescaler << QEP0_CTRL2_CFG2CAP_UPPS_Pos);
}

/**
 * @brief Set the quadrature mode adapter (QMA) module mode
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param qmaMode
 */
void QEP_setQMAModuleMode(QEP_Type *QEPx, QEP_QMAMode qmaMode)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    WRITE_REG(QEPx->QMACTRL, qmaMode);
}

/**
 * @brief Set the strobe input source of the eQEP module.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param strobeSrc
 */
void QEP_setStrobeSource(QEP_Type *QEPx, QEP_StrobeSource strobeSrc)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->INPUTSEL, QEP0_INPUTSEL_CFG2DEC_STROBESEL_Msk,
               (uint32_t)strobeSrc << QEP0_INPUTSEL_CFG2DEC_STROBESEL_Pos);
}

/**
 * @brief Selects the source for eQEPA/B/I signals
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param sourceConfig
 */
void QEP_selectSource(QEP_Type *QEPx, QEP_SourceSelect sourceConfig)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->INPUTSEL,
               QEP0_INPUTSEL_A_SEL_Msk | QEP0_INPUTSEL_B_SEL_Msk | QEP0_INPUTSEL_INDEX_SEL_Msk,
               ((uint32_t)sourceConfig.sourceA << QEP0_INPUTSEL_A_SEL_Pos) |
               ((uint32_t)sourceConfig.sourceB << QEP0_INPUTSEL_B_SEL_Pos) |
               ((uint32_t)sourceConfig.sourceIndex << QEP0_INPUTSEL_INDEX_SEL_Pos));
}

/**
 * @brief Sets the polarity of the eQEP module's input signals.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param invertQEPA is the flag to negate the QEPA input.
 * @param invertQEPB is the flag to negate the QEPA input.
 * @param invertIndex is the flag to negate the index input.
 * @param invertStrobe is the flag to negate the strobe input.
 */
void QEP_setInputPolarity(QEP_Type *QEPx, bool invertQEPA, bool invertQEPB, bool invertIndex, bool invertStrobe)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    /* Configure QEPA signal */
    if (invertQEPA)
    {
        SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_AP_Msk);
    }
    else
    {
        CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_AP_Msk);
    }

    /* Configure QEPB signal */
    if (invertQEPB)
    {
        SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_BP_Msk);
    }
    else
    {
        CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_BP_Msk);
    }

    /* Configure index signal */
    if (invertIndex)
    {
        SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_IP_Msk);
    }
    else
    {
        CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_IP_Msk);
    }

    /* Configure strobe signal */
    if (invertStrobe)
    {
        SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_SP_Msk);
    }
    else
    {
        CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_SP_Msk);
    }
}

/**
 * @brief Sets the current encoder position.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param position \e position is the new position for the encoder.
 * range: 0x0 ~ 0xFFFFFFFF
 */
void QEP_setPosition(QEP_Type *QEPx, uint32_t position)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    WRITE_REG(QEPx->POSCNT, position);
}

/**
 * @brief Configures the mode in which the position counter is initialized.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param initMode The \e initMode parameter provides the mode as either
 *      \b QEP_INIT_DO_NOTHING (no action configured) or one of the following strobe events, index events,
 *                              or a logical OR of both a strobe event and an index event.
 *  - strobe events: specify which strobe event will initialize the position counter.
 *      \b QEP_INIT_RISING_STROBE or
 *      \b QEP_INIT_EDGE_DIR_STROBE
 *  - index events: specify which index event will initialize the position counter.
 *      \b QEP_INIT_RISING_INDEX or
 *      \b QEP_INIT_FALLING_INDEX
 */
void QEP_setPositionInitMode(QEP_Type *QEPx, uint16_t initMode)
{
    assert_param(IS_QEP_PERIPH(QEPx));
    assert_param(IS_QEP_INIT_MODE(initMode));

    MODIFY_REG(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_IEI_Msk | QEP0_CTRL1_CFG2PCCU_SEI_Msk,
               initMode);
}

/**
 * @brief Sets the software initialization of the encoder position counter.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param initialize initialize is a flag to specify if software initialization of the  position counter is enabled.
 */
void QEP_setSWPositionInit(QEP_Type *QEPx, bool initialize)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    if (initialize)
    {
        SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_SWI_Msk);
    }
    else
    {
        CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2PCCU_SWI_Msk);
    }
}

/**
 * @brief Sets the init value for the encoder position counter.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param position \e position is the value to be written to the position counter upon.initialization.
 */
void QEP_setInitialPosition(QEP_Type *QEPx, uint32_t position)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    WRITE_REG(QEPx->POSINIT, position);
}

/**
 * @brief Gets the current encoder position.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint32_t The current position of the encoder.
 */
uint32_t QEP_getPosition(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_REG(QEPx->POSCNT);
}

/**
 * @brief Gets the encoder capture period.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t The period count value between the last successive position events.
 *  range 0x0 ~ 0xFFFF
 */
uint16_t QEP_getCapturePeriod(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_BIT(QEPx->CAP_VAL, QEP0_CAP_VAL_CPRD_Msk) >> QEP0_CAP_VAL_CPRD_Pos;
}

/**
 * @brief Gets the encoder capture timer value.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t The capture timer value.
 *  range 0x0 ~ 0xFFFF
 */
uint16_t QEP_getCaptureTimer(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return (uint16_t)(READ_BIT(QEPx->CAP_VAL, QEP0_CAP_VAL_CCNT_Msk) >> QEP0_CAP_VAL_CCNT_Pos);
}

/**
 * @brief Gets the current direction of rotation.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return int16_t
 *      - Return 1 if moving in the forward direction
 *      - return -1 if moving in the reverse direction
 */
int16_t QEP_getDirection(QEP_Type *QEPx)
{
    int16_t direction;

    assert_param(IS_QEP_PERIPH(QEPx));

    if ((READ_BIT(QEPx->STS, QEP0_STS_DEC2CFG_STS_QDF_Msk)) != 0U)
    {
        direction = 1;
    }
    else
    {
        direction = -1;
    }

    return(direction);
}

/**
 * @brief Enables the eQEP module position-compare unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_enableCompare(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->CTRL2, QEP0_CTRL2_CFG2PCCU_CMP_EN_Msk);
}

/**
 * @brief Disables the eQEP module position-compare unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_disableCompare(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->CTRL2, QEP0_CTRL2_CFG2PCCU_CMP_EN_Msk);
}

/**
 * @brief Configures eQEP module position-compare unit.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param config
 * @param compareValue \e compareValue is the value to which the position count value is compared for a position-compare
 * event.
 * range:0x0 ~ 0xFFFFFFFF. actual value = compareValue + 1.
 * @param cycles The \e cycles is used to select the width of the sync output pulse.
 * The width of the resulting pulse will be \e cycles * 4 * the width of a SYSCLKOUT cycle.
 * The maximum width is 4096 * 4 * SYSCLKOUT cycles.
 */
void QEP_setCompareConfig(QEP_Type *QEPx, QEP_CompareConfigParam config, uint32_t compareValue, uint16_t cycles)
{
    assert_param(IS_QEP_PERIPH(QEPx));
    assert_param(IS_QEP_COMPARE_PULSE_WIDTH(cycles));

    /* Set the compare match value */
    WRITE_REG(QEPx->POSCMP, compareValue);

    /* Set the shadow register settings and pulse width. */
    MODIFY_REG(QEPx->CTRL2, QEP0_CTRL2_CFG2PCCU_MTH_WID_Msk |
               QEP0_CTRL2_CFG2PCCU_MTH_PLR_Msk |
               QEP0_CTRL2_CFG2PCCU_CMP_LOAD_MD_Msk |
               QEP0_CTRL2_CFG2PCCU_CMP_SHDW_MD_Msk,
               ((uint32_t)config.shadowModeEn << QEP0_CTRL2_CFG2PCCU_CMP_SHDW_MD_Pos) |
               ((uint32_t)config.shadowSigSel << QEP0_CTRL2_CFG2PCCU_CMP_LOAD_MD_Pos) |
               ((uint32_t)config.Outputpolarity << QEP0_CTRL2_CFG2PCCU_MTH_PLR_Pos) |
               ((uint32_t)(cycles - 1) << QEP0_CTRL2_CFG2PCCU_MTH_WID_Pos));
    /* Set position compare sync-output mode. */
    MODIFY_REG(QEPx->CTRL1, QEP0_CTRL1_CFG2DEC_SOEN_Msk | QEP0_CTRL1_CFG2DEC_SPSEL_Msk,
               ((uint32_t)config.compareOutputEn << QEP0_CTRL1_CFG2DEC_SOEN_Pos) |
               ((uint32_t)config.compareOutputPinSel << QEP0_CTRL1_CFG2DEC_SPSEL_Pos));
}

/**
 * @brief Configures the position-compare unit's sync output pulse width.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param cycles \e cycles is the width of the pulse that can be generated on a position-compare event.
 * It is in units of 4 SYSCLKOUT cycles.
 * config range:1 ~ 4096;  actual range: 1 * 4*SYSCLKOUT ~ 4096 * 4* SYSCLKOUT
 * note: param \e cycles cannot write 0.
 */
void QEP_setComparePulseWidth(QEP_Type *QEPx, uint16_t cycles)
{
    assert_param(IS_QEP_PERIPH(QEPx));
    assert_param(IS_QEP_COMPARE_PULSE_WIDTH(cycles));

    MODIFY_REG(QEPx->CTRL2, QEP0_CTRL2_CFG2PCCU_MTH_WID_Msk,
               (uint32_t)(cycles - 1) << QEP0_CTRL2_CFG2PCCU_MTH_WID_Pos);
}

/**
 * @brief Enables the eQEP module watchdog timer.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param period \e period is watchdog period value at which a time-out will occur if no quadrature-clock event is
 * detected.
 */
void QEP_enableWatchdog(QEP_Type *QEPx, uint16_t period)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->WDG, QEP0_WDG_CFG2WDG_UPRD_Msk, (uint32_t)period << QEP0_WDG_CFG2WDG_UPRD_Pos);

    SET_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2WDG_EN_Msk);
}

/**
 * @brief disables the eQEP module watchdog timer.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 */
void QEP_disableWatchdog(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->CTRL1, QEP0_CTRL1_CFG2WDG_EN_Msk);
}

/**
 * @brief Sets the eQEP module watchdog timer value.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param value \e value is the value to be written to the watchdog timer.
 */
void QEP_setWatchdogTimerValue(QEP_Type *QEPx, uint16_t value)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->WDG, QEP0_WDG_WCNT_Msk, (uint32_t)value << QEP0_WDG_WCNT_Pos);
}

/**
 * @brief Gets the eQEP module watchdog timer value.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t Return the current watchdog timer value.
 */
uint16_t QEP_getWatchdogTimerValue(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_BIT(QEPx->WDG, QEP0_WDG_WCNT_Msk) >> QEP0_WDG_WCNT_Pos;
}

/**
 * @brief Configures the quadrature modes in which the position count can be latched.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param latchMode This function configures the events on which the position count and several other registers can be
 * latched.
 * The \e latchMode parameter provides the mode as the logical OR of several values.
 *  - specify the event that latches the position counter.
 *      \b QEP_LATCH_CNT_READ_BY_CPU  or
 *      \b QEP_LATCH_UNIT_TIME_OUT
 *  - specify which strobe event will latch the position counter into the strobe position latch register.
 *      \b QEP_LATCH_RISING_INDEX or
 *      \b QEP_LATCH_FALLING_INDEX or
 *      \b QEP_LATCH_SW_INDEX_MARKER
 *  - specify which index event will latch the position counter into the index position latch register.
 *      \b QEP_LATCH_RISING_STROBE  or
 *      \b QEP_LATCH_EDGE_DIR_STROBE
 */
void QEP_setLatchMode(QEP_Type *QEPx, uint32_t latchMode)
{
    assert_param(IS_QEP_PERIPH(QEPx));
    assert_param(IS_QEP_LACTCH_MODE(latchMode));

    MODIFY_REG(QEPx->CTRL1,
               QEP0_CTRL1_CFG2CAP_QCLM_Msk | QEP0_CTRL1_CFG2PCCU_IEL_Msk | QEP0_CTRL1_CFG2PCCU_SEL_Msk,
               latchMode);
}

/**
 * @brief Gets the encoder position that was latched on an index event.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint32_t return The position count latched on an index event.
 */
uint32_t QEP_getIndexPositionLatch(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_REG(QEPx->POSILAT);
}

/**
 * @brief Gets the encoder position that was latched on a strobe event.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint32_t return The position count latched on a strobe event.
 */
uint32_t QEP_getStrobePositionLatch(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_REG(QEPx->POSSLAT);
}

/**
 * @brief Gets the encoder position that was latched on a unit time-out event.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint32_t return The position count latch register value.
 */
uint32_t QEP_getPositionLatch(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_REG(QEPx->POSLAT);
}

/**
 * @brief Gets the encoder capture timer latch.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t return The edge-capture timer latch value.
 */
uint16_t QEP_getCaptureTimerLatch(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_BIT(QEPx->CAP_LAT, QEP0_CAP_LAT_CAP2CFG_CCNTLAT_Msk) >> QEP0_CAP_LAT_CAP2CFG_CCNTLAT_Pos;
}

/**
 * @brief Gets the encoder capture period latch.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t return The edge-capture period latch value.
 */
uint16_t QEP_getCapturePeriodLatch(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return READ_BIT(QEPx->CAP_LAT, QEP0_CAP_LAT_CAP2CFG_CPRDLAT_Msk) >> QEP0_CAP_LAT_CAP2CFG_CPRDLAT_Pos;
}

/**
 * @brief Enables eQEP module interrupt sources.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_enableInterrupt(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->INT_EN, intFlags);
}

/**
 * @brief Disables eQEP module interrupt sources.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_disableInterrupt(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->INT_EN, intFlags);
}

/**
 * @brief Gets the current interrupt status.
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t Returned, as a bit field of the following values:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
uint16_t QEP_getInterruptStatus(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return (uint16_t)READ_REG(QEPx->INT_STATUS_RPT);
}

/**
 * @brief gets the interrupt raw status.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t Returned, as a bit field of the following values:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
uint16_t QEP_getInterruptRawStatus(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return (uint16_t)READ_REG(QEPx->INT_RAW_RPT);
}

/**
 * @brief Clears eQEP module interrupt sources.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_clearInterruptStatus(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->INT_CLR, intFlags);
}

/**
 * @brief Forces eQEP module interrupts.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_forceInterrupt(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->INT_FORCE_IND, intFlags);
}

/**
 * @brief Mask eQEP module interrupts.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1] pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_enableInterruptMask(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    SET_BIT(QEPx->INT_MASK, intFlags);
}

/**
 * @brief Unmask eQEP module interrupts.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1] pointer to QEP module instance, [EQP0~EQP1]
 * @param intFlags  The \e intFlags parameter can be any of the following values OR or together:
 *          \b QEP_INT_DIR_CHANGE - Quadrature direction change
 *          \b QEP_INT_PHASE_ERROR - Quadrature phase error
 *          \b QEP_INT_POS_CNT_ERROR - Position counter error
 *          \b QEP_INT_STROBE_EVNT_LATCH - Strobe event latch
 *          \b QEP_INT_INDEX_EVNT_LATCH - Index event latch
 *          \b QEP_INT_POS_COMP_READY - Position-compare ready
 *          \b QEP_INT_POS_COMP_MATCH - Position-compare match
 *          \b QEP_INT_UNDERFLOW - Position counter underflow
 *          \b QEP_INT_OVERFLOW - Position counter overflow
 *          \b QEP_INT_WATCHDOG - Watchdog time-out
 *          \b QEP_INT_UNIT_TIME_OUT - Unit time-out
 *          \b QEP_INT_QMA_ERROR - QMA error
 */
void QEP_disableInterruptMask(QEP_Type *QEPx, uint16_t intFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    CLEAR_BIT(QEPx->INT_MASK, intFlags);
}

/**
 * @brief Gets the encoder error indicator.
 * It is an error for both of the signals of the quadrature input to change at the same time.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return bool
 *      - Return \b true if an error has occurred
 *      - Return \b false otherwise.
 */
bool QEP_getError(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return(READ_BIT(QEPx->INT_RAW_RPT, QEP_INT_PHASE_ERROR) != 0U);
}

/**
 * @brief Get content of the eQEP module status register
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @return uint16_t The value it returns is an OR of the following values:
 *          \b QEP_STS_POS_CNT_ERROR  - Position counter error occurred
 *          \b QEP_STS_1ST_IDX_FLAG  - Set by the occurrence of the first index pulse
 *          \b QEP_STS_CAP_DIR_ERROR  - Direction change occurred between position capture events
 *          \b QEP_STS_CAP_OVRFLW_ERROR  - Overflow occurred in eQEP capture timer
 *          \b QEP_STS_DIR_LATCH  - If set, clockwise rotation occurred on last index event marker
 *          \b QEP_STS_DIR_FLAG  - If set, movement is clockwise rotation
 *          \b QEP_STS_DIR_ON_1ST_IDX  - If set, clockwise rotation (forward movement) occurred on the first index
 * event
 *          \b QEP_STS_UNIT_POS_EVNT  - Unit position event detected
 */
uint8_t QEP_getStatus(QEP_Type *QEPx)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    return (uint8_t)READ_REG(QEPx->STS);
}

/**
 * @brief Clears selected fields of the eQEP module status register
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param statusFlags This function clears the status register fields indicated by \e statusFlags.
 * The \e statusFlags parameter is the logical OR of any of the following:
 *          \b QEP_STS_1ST_IDX_FLAG  - Set by the occurrence of the first index pulse
 *          \b QEP_STS_CAP_DIR_ERROR  - Direction change occurred between position capture events
 *          \b QEP_STS_CAP_OVRFLW_ERROR  - Overflow occurred in eQEP capture timer
 *          \b QEP_STS_UNIT_POS_EVNT  - Unit position event detected
 */
void QEP_clearStatus(QEP_Type *QEPx, uint8_t statusFlags)
{
    assert_param(IS_QEP_PERIPH(QEPx));
    assert_param(IS_QEP_CLEAR_STATUS_FLAG(statusFlags));

    SET_BIT(QEPx->STS, statusFlags);
}

/**
 * @brief Set the emulation mode of the eQEP module.
 *
 * @param QEPx pointer to QEP module instance, [EQP0~EQP1]
 * @param emuMode
 */
void QEP_setEmulationMode(QEP_Type *QEPx, QEP_EmulationMode emuMode)
{
    assert_param(IS_QEP_PERIPH(QEPx));

    MODIFY_REG(QEPx->CTRL1, QEP0_CTRL1_FREESOFT_Msk,
               ((uint32_t)emuMode << QEP0_CTRL1_FREESOFT_Pos));
}

/******************* END ***************************/
