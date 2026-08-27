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
 * ARISING IN ANY WAY  OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY
 * OF SUCH DAMAGE.
 */

/* Includes ------------------------------------------------------------------*/
#include "et6x_clb.h"

//*****************************************************************************
//
//! Set global enable.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables the CLB via global enable register.
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableCLB(CLB_TILE tile)
{
    SET_BIT(CLB->TILE_GRP[tile].LOAD_EN, CLB_TILE_GRP_LOAD_EN_GLBEN_Msk);
}

//*****************************************************************************
//
//! Clear global enable.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB via global enable register.
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableCLB(CLB_TILE tile)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].LOAD_EN, CLB_TILE_GRP_LOAD_EN_GLBEN_Msk);
}

//*****************************************************************************
//
//! Enable HLC NMI.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables the CLB HLC NMI.
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableNMI(CLB_TILE tile)
{
}

//*****************************************************************************
//
//! Disable HLC NMI.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB HLC NMI.
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableNMI(CLB_TILE tile)
{
}

//*****************************************************************************
//
//! Configure Clock Prescalar.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables and configures the CLB Clock Precalar.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configureClockPrescalar(CLB_TILE tile, uint16_t prescl)
{
    MODIFY_REG(CLB->TILE_GRP[tile].PRSTRB, CLB_TILE_GRP_PRSTRB_SIGSEL_Msk,
               (uint32_t)prescl << CLB_TILE_GRP_PRSTRB_SIGSEL_Pos);
}

//*****************************************************************************
//
//! Configures Clock Precalar Strobe Mode.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables and configures the CLB Clock Precalar Strobe Mode.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configureStrobeMode(CLB_TILE tile, uint16_t strb)
{
    MODIFY_REG(CLB->TILE_GRP[tile].PRSTRB, CLB_TILE_GRP_PRSTRB_MDSEL_Msk,
               (uint32_t)strb << CLB_TILE_GRP_PRSTRB_MDSEL_Pos);
}

//*****************************************************************************
//
//! Configures the general purpose SW release control value.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB SW Release input signal.
//! \param val is the value of the SW RLS control.
//!
//! This function configures the general purpose SW release control value.
//! The \e inID parameter can have one enumeration value from CLB_SWReleaseCtrl.
//!
//! \return None.
//
//*****************************************************************************
void CLB_writeSWReleaseControl(CLB_TILE tile, CLB_SWReleaseCtrl inID, bool val)
{
    MODIFY_REG(CLB->TILE_GRP[tile].SW, BIT_MASK(CLB_TILE_GRP_SW_RLS_CTRL_A_Pos + inID),
               (uint32_t)val << (CLB_TILE_GRP_SW_RLS_CTRL_A_Pos + inID));
}

//*****************************************************************************
//
//! Configures the general purpose SW gate control value.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB SW Release input signal.
//! \param val is the value of the SW GATE control.
//!
//! This function configures the general purpose SW release control value.
//! The \e inID parameter can have one enumeration value from CLB_SWGateCtrl.
//!
//! \return None.
//
//*****************************************************************************
void CLB_writeSWGateControl(CLB_TILE tile, CLB_SWGateCtrl inID, bool val)
{
    MODIFY_REG(CLB->TILE_GRP[tile].SW, BIT_MASK(CLB_TILE_GRP_SW_GATING_CTRL_A_Pos + inID),
               (uint32_t)val << (CLB_TILE_GRP_SW_GATING_CTRL_A_Pos + inID));
}

//*****************************************************************************
//
//! Configures Counter TAP Selects.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param miscCtrl is the value to represent counter tap selects.
//!        Generated by tool as \b TILEx_CFG_TAP_SELL.
//!
//! This function configures the counter tap selects.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configCounterTapSelects(CLB_TILE tile, uint32_t tapSel)
{
    WRITE_REG(CLB->TILE_GRP[tile].CNT_MATCH, tapSel);
}

//*****************************************************************************
//
//! Configures AOC (Asynchronous Output Conditioning) functions.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param aocID is the specified CLB tile AOC signal.
//! \param aocCfg is the value for the AOC signal function and input
//!        signal selections. Generated by tool as \b TILEx_OUTPUT_COND_CTR_n
//!        where n is the output number.
//!
//! This function configures the input signals and equations of the aoc LUT
//! corresponding to the /e aocID parameter.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configAOC(CLB_TILE tile, CLB_AOCs aocID, uint32_t aocCfg)
{
    volatile uint32_t *AOC_addr = &CLB->TILE_GRP[tile].AOC1 + aocID;

    WRITE_REG(*AOC_addr, aocCfg);
}

//*****************************************************************************
//
//! Enable CLB lock.
//!
//!
//! This function enables the lock bit of the lock register. The lock can only
//! be set once and can only be cleared by a device reset.
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableLock(void)
{
    //
    // Setting the lock bit requires key 0x5A5A to be written at the same time
    //
    WRITE_REG(CLB->LOCK, CLB_LOCK_KEY_Msk);
}

//*****************************************************************************
//
//! Write value to address.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param address is the address of CLB internal memory.
//! \param value is the value to write to specified address.
//!
//! This function writes the specified value to CLB internal memory.
//!
//! \return None.
//
//*****************************************************************************
static void CLB_writeInterface(CLB_TILE tile, uint32_t address, uint32_t value)
{
    WRITE_REG(CLB->TILE_GRP[tile].LOAD_ADDR, address);
    WRITE_REG(CLB->TILE_GRP[tile].LOAD_DATA, value);
    SET_BIT(CLB->TILE_GRP[tile].LOAD_EN, CLB_TILE_GRP_LOAD_EN_LOAD_EN_Msk);
}

//*****************************************************************************
//
//! Select input filter type.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//! \param filterType is the selected type of filter applied to the input.
//!
//! This function configures the filter selection for the specified input.
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//! The \e filterType parameter can have one enumeration value from
//! CLB_FilterType.
//!
//! \return None.
//
//*****************************************************************************
void CLB_selectInputFilter(CLB_TILE tile, CLB_Inputs inID, CLB_FilterType filterType)
{
    MODIFY_REG(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_INPUT_FLT_EDGE_A_Msk << 2 * (uint32_t)inID,
               (uint32_t)filterType << 2 * (uint32_t)inID);
}

//*****************************************************************************
//
//! Enables synchronization of an input signal.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//!
//! This function enables synchronization on the specified input signal.
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableSynchronization(CLB_TILE tile, CLB_Inputs inID)
{
    SET_BIT(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_INPUT_FLT_SYNC_A_Msk << inID);
}

//*****************************************************************************
//
//! Disables synchronization of an input signal.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//!
//! This function disables synchronization on the specified input signal.
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableSynchronization(CLB_TILE tile, CLB_Inputs inID)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_INPUT_FLT_SYNC_A_Msk << inID);
}

//*****************************************************************************
//
//! Configures the general purpose input mux.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//! \param gpMuxCfg is the mux selection for the general purpose input mux.
//!
//! This function configures the general purpose input mux. The \e gpMuxCfg
//! parameter can select either the use of an external input signal
//! (\b CLB_GP_IN_MUX_EXTERNAL) or the use of the corresponding CLB_GP_REG bit
//! as an input (\b CLB_GP_IN_MUX_GP_REG).
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//!
//! \sa CLB_setGPREG() to write to the CLB_GP_REG.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configGPInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_GPInputMux gpMuxCfg)
{
    MODIFY_REG(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_SW_IN_SEL_A_Msk << inID, (uint32_t)gpMuxCfg << inID);
}

//*****************************************************************************
//
//! Sets the CLB_GP_REG register value.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param gpRegVal is the value to be written to CLB_GP_REG.
//!
//! This function writes to the CLB_GP_REG register. When the general purpose
//! input mux is configured to use CLB_GP_REG, each bit in \e gpRegVal
//! corresponds to an input signal (bit 0 to Input 0, bit 1 to Input 1, and
//! so on).
//!
//! \sa CLB_configGPInputMux() to select the CLB_GP_REG as the source for
//! an input signal.
//!
//! \return None.
//
//*****************************************************************************
void CLB_setGPREG(CLB_TILE tile, uint32_t gpRegVal)
{
    WRITE_REG(CLB->TILE_GRP[tile].SW, gpRegVal);
}

//*****************************************************************************
//
//! Gets the CLB_GP_REG register value.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function writes to the CLB_GP_REG register. When the general purpose
//! input mux is configured to use CLB_GP_REG, each bit in \e gpRegVal
//! corresponds to an input signal (bit 0 to Input 0, bit 1 to Input 1, and
//! so on).
//!
//! \sa CLB_configGPInputMux() to select the CLB_GP_REG as the source for
//! an input signal.
//!
//! \return CLB_GP_REG value.
//
//*****************************************************************************
uint32_t CLB_getGPREG(CLB_TILE tile)
{
    return READ_REG(CLB->TILE_GRP[tile].SW);
}

//*****************************************************************************
//
//! Configures the local input mux.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//! \param localMuxCfg is the mux selection for the local input mux.
//!
//! This function configures the local input mux for the specified input
//! signal.
//!
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//! The \e localMuxCfg parameter can have one enumeration value from
//! CLB_LocalInputMux.
//!
//! \note The local input mux options' peripheral sources depend on which
//! instance of the CLB (\e base) you are using. For example, for CLB1 the
//! EPWM signal selections come from EPWM1 but for CLB2 they come from EPWM2.
//! See your technical reference manual for details.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configLocalInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_LocalInputMux localMuxCfg)
{
    if (inID < CLB_IN4)
    {
        MODIFY_REG(CLB->TILE_GRP[tile].LCL_MUX,
                   CLB_TILE_GRP_LCL_MUX_SEL_A_Msk << inID * CLB_TILE_GRP_LCL_MUX_SEL_B_Pos,
                   (uint32_t)localMuxCfg << inID * CLB_TILE_GRP_LCL_MUX_SEL_B_Pos);
    }
    else
    {
        MODIFY_REG(CLB->TILE_GRP[tile].LCL_MUX_SEL,
                   CLB_TILE_GRP_LCL_MUX_SEL_E_Msk << (inID - CLB_IN4) * CLB_TILE_GRP_LCL_MUX_SEL_F_Pos,
                   (uint32_t)localMuxCfg << (inID - CLB_IN4) * CLB_TILE_GRP_LCL_MUX_SEL_F_Pos);
    }
}

//*****************************************************************************
//
//! Configures the global input mux.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param inID is the specified CLB tile input signal.
//! \param globalMuxCfg is the mux selection for the global input mux.
//!
//! This function configures the global input mux for the specified input
//! signal.
//! The \e inID parameter can have one enumeration value from CLB_Inputs.
//! The \e globalMuxCfg parameter can have one enumeration value from
//! CLB_GlobalInputMux.
//!
//! \note The global input mux options' peripheral sources depend on which
//! instance of the CLB (\e base) you are using. For example, for CLB1 the
//! EPWM signal selections come from EPWM1 but for CLB2 they come from EPWM2.
//! See your technical reference manual for details.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configGlobalInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_GlobalInputMux globalMuxCfg)
{
    if (inID < CLB_IN4)
    {
        MODIFY_REG(CLB->TILE_GRP[tile].GLB_MUX,
                   CLB_TILE_GRP_GLB_MUX_SEL_A_Msk << inID * CLB_TILE_GRP_GLB_MUX_SEL_B_Pos,
                   (uint32_t)globalMuxCfg << inID * CLB_TILE_GRP_GLB_MUX_SEL_B_Pos);
    }
    else
    {
        MODIFY_REG(CLB->TILE_GRP[tile].GLB_MUX_SEL,
                   CLB_TILE_GRP_GLB_MUX_SEL_E_Msk << (inID - CLB_IN4) * CLB_TILE_GRP_GLB_MUX_SEL_F_Pos,
                   (uint32_t)globalMuxCfg << (inID - CLB_IN4) * CLB_TILE_GRP_GLB_MUX_SEL_F_Pos);
    }
}

//*****************************************************************************
//
//! Controls the output enable.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param outputMask is a mask of the outputs to be enabled.
//! \param enable is a switch to decide if the CLB outputs need to be enabled
//!  or not.
//!
//! This function is used to enable and disable CLB outputs by writing a mask
//! to CLB_OUT_EN. Each bit corresponds to a CLB output. When a bit is 1, the
//! corresponding output is enabled; when a bit is 0, the output is disabled.
//!
//! The \e outputMask parameter takes a logical OR of any of the CLB_OUTPUT_0x
//! values that correspond to the CLB OUTPUT ENABLE for the respective outputs.
//! The \e enable parameter can have one of the values from:
//! false: Disable the respective CLB outputs
//! true: Enable the respective CLB outputs
//!
//! \note Note that the 8 CLB outputs are replicated to create more output
//!  paths. See your technical reference manual for more details.
//!  If no further modifications are expected, then it is advised to set the
//!  block writes bit of the MISC_ACCESS_CTRL Register. This will prevent
//!  accidental writes.
//!
//! \return None.
//
//*****************************************************************************
void CLB_setOutputMask(CLB_TILE tile, uint32_t outputMask, bool enable)
{
    if (enable == true)
    {
        SET_BIT(CLB->TILE_GRP[tile].OUT, outputMask);
    }
    else
    {
        CLEAR_BIT(CLB->TILE_GRP[tile].OUT, outputMask);
    }
}

//*****************************************************************************
//
//! Reads the interrupt tag register.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! \return Returns the value in the interrupt tag register which is a 6-bit
//!         constant set by the HLC.
//
//*****************************************************************************
uint16_t CLB_getInterruptTag(CLB_TILE tile)
{
    return (uint16_t)READ_REG(CLB->TILE_GRP[tile].INT_TAG_RPT);
}

//*****************************************************************************
//
//! Clears the interrupt tag register.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function clears the interrupt tag register, setting it to 0.
//!
//! \return None.
//
//*****************************************************************************
void CLB_clearInterruptTag(CLB_TILE tile)
{
    WRITE_REG(CLB->TILE_GRP[tile].INT_TAG_RPT, CLB_TILE_GRP_INT_TAG_RPT_VALUE_Msk);
}

//*****************************************************************************
//
//! Selects LUT4 inputs.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param lut4In0 is the value for LUT4 input signal 0. Generated by tool as
//!        \b TILEx_CFG_LUT4_IN0.
//! \param lut4In1 is the value for LUT4 input signal 1. Generated by tool as
//!        \b TILEx_CFG_LUT4_IN1.
//! \param lut4In2 is the value for LUT4 input signal 2. Generated by tool as
//!        \b TILEx_CFG_LUT4_IN2.
//! \param lut4In3 is the value for LUT4 input signal 3. Generated by tool as
//!        \b TILEx_CFG_LUT4_IN3.
//!
//! This function configures the LUT4 block's input signals.
//!
//! \return None.
//
//*****************************************************************************
void CLB_selectLUT4Inputs(CLB_TILE tile, uint32_t lut4In0, uint32_t lut4In1, uint32_t lut4In2, uint32_t lut4In3)
{
    WRITE_REG(CLB->TILE_GRP[tile].LUT4_IN0, lut4In0);
    WRITE_REG(CLB->TILE_GRP[tile].LUT4_IN1, lut4In1);
    WRITE_REG(CLB->TILE_GRP[tile].LUT4_IN2, lut4In2);
    WRITE_REG(CLB->TILE_GRP[tile].LUT4_IN3, lut4In3);
}

//*****************************************************************************
//
//! Configures LUT4 functions.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param lut4Fn10 is the equation value for LUT4 blocks 0 and 1. Generated by
//!        tool as \b TILEx_CFG_LUT4_FN10.
//! \param lut4Fn2 is the equation value for LUT4 block2. Generated by tool as
//!        \b TILEx_CFG_LUT4_FN2.
//!
//! This function configures the LUT4 block's equations.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configLUT4Function(CLB_TILE tile, uint32_t lut4Fn10, uint32_t lut4Fn2)
{
    WRITE_REG(CLB->TILE_GRP[tile].LUT4, lut4Fn10);
    WRITE_REG(CLB->TILE_GRP[tile].LUT4_FUNC, lut4Fn2);
}

//*****************************************************************************
//
//! Selects FSM inputs.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param external0 is the value for FSM external 0 input. Generated by tool
//!        as \b TILEx_CFG_FSM_EXT_IN0.
//! \param external1 is the value for FSM external 1 input. Generated by tool
//!        as \b TILEx_CFG_FSM_EXT_IN1.
//! \param extra0 is the value for FSM extra 0 input. Generated by tool
//!        as \b TILEx_CFG_FSM_EXTRA_IN0.
//! \param extra1 is the value for FSM extra 1 input. Generated by tool
//!        as \b TILEx_CFG_FSM_EXTRA_IN1.
//!
//! This function configures the FSM block's external inputs and extra external
//! inputs.
//!
//! \return None.
//
//*****************************************************************************
void CLB_selectFSMInputs(CLB_TILE tile, uint32_t external0, uint32_t external1, uint32_t extra0, uint32_t extra1)
{
    WRITE_REG(CLB->TILE_GRP[tile].FSM_EXT_IN0, external0);
    WRITE_REG(CLB->TILE_GRP[tile].FSM_EXT_IN1, external1);
    WRITE_REG(CLB->TILE_GRP[tile].FSM_EXTRA_IN0, extra0);
    WRITE_REG(CLB->TILE_GRP[tile].FSM_EXTRA_IN1, extra1);
}

//*****************************************************************************
//
//! Configures FSM LUT function.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param fsmLutFn10 is the value for FSM 0 & FSM 1 LUT function. Generated
//!        by tool as \b TILEx_CFG_FSM_LUT_FN10.
//! \param fsmLutFn2 is the value for FSM 2 LUT function. Generated by tool as
//!        \b TILEx_CFG_FSM_LUT_FN2.
//!
//! This function configures the FSM block's LUT equations.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configFSMLUTFunction(CLB_TILE tile, uint32_t fsmLutFn10, uint32_t fsmLutFn2)
{
    WRITE_REG(CLB->TILE_GRP[tile].FSM_OUT, fsmLutFn10);
    WRITE_REG(CLB->TILE_GRP[tile].FSM_OUT_FUNC, fsmLutFn2);
}

//*****************************************************************************
//
//! Configures FSM next state.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param nextState0 is the value for FSM 0's next state. Generated by tool as
//!        \b TILEx_CFG_FSM_NEXT_STATE_0.
//! \param nextState1 is the value for FSM 1's next state. Generated by tool as
//!        \b TILEx_CFG_FSM_NEXT_STATE_1.
//! \param nextState2 is the value for FSM 2's next state. Generated by tool as
//!        \b TILEx_CFG_FSM_NEXT_STATE_2.
//!
//! This function configures the FSM's next state equation.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configFSMNextState(CLB_TILE tile, uint32_t nextState0, uint32_t nextState1, uint32_t nextState2)
{
    WRITE_REG(CLB->TILE_GRP[tile].FSM1_NS, nextState0);
    WRITE_REG(CLB->TILE_GRP[tile].FSM2_NS, nextState1);
    WRITE_REG(CLB->TILE_GRP[tile].FSM3_NS, nextState2);
}

//*****************************************************************************
//
//! Selects Counter inputs.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param reset is the value for counter's reset inputs. Generated by tool as
//!        \b TILEx_CFG_COUNTER_RESET.
//! \param event is the value for counter's event inputs. Generated by tool as
//!        \b TILEx_CFG_COUNTER_EVENT.
//! \param mode0 is the value for counter's mode 0 inputs. Generated by tool as
//!        \b TILEx_CFG_COUNTER_MODE_0.
//! \param mode1 is the value for counter's mode 1 inputs. Generated by tool as
//!        \b TILEx_CFG_COUNTER_MODE_1.
//!
//! This function selects the input signals to the counter block.
//!
//! \return None.
//
//*****************************************************************************
void CLB_selectCounterInputs(CLB_TILE tile, uint32_t reset, uint32_t event, uint32_t mode0, uint32_t mode1)
{
    WRITE_REG(CLB->TILE_GRP[tile].CNT_RST, reset);
    WRITE_REG(CLB->TILE_GRP[tile].CNT_EVT, event);
    WRITE_REG(CLB->TILE_GRP[tile].CNT_MODE0, mode0);
    WRITE_REG(CLB->TILE_GRP[tile].CNT_MODE1, mode1);
}

//*****************************************************************************
//
//! Configures Counter and FSM modes.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param miscCtrl is the value to represent counter and FSM modes.
//!        Generated by tool as \b TILEx_CFG_MISC_CONTROL.
//!
//! This function configures the counter mode, particularly add/shift, load
//! modes. The function also configures whether the FSM should use state inputs
//! or an extra external input.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configMiscCtrlModes(CLB_TILE tile, uint32_t miscCtrl)
{
    WRITE_REG(CLB->TILE_GRP[tile].MISC_CTRL, miscCtrl);
}

//*****************************************************************************
//
//! Configures Output LUT functions.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param outID is the specified CLB tile output signal.
//! \param outputCfg is the value for the output LUT signal function and input
//!        signal selections. Generated by tool as \b TILEx_CFG_OUTLUT_n where
//!        n is the output number.
//!
//! This function configures the input signals and equations of the output LUT
//! corresponding to the /e outID parameter.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configOutputLUT(CLB_TILE tile, CLB_Outputs outID, uint32_t outputCfg)
{
    volatile uint32_t *OUTLUT_addr = &CLB->TILE_GRP[tile].OUTLUT1 + outID;

    WRITE_REG(*OUTLUT_addr, outputCfg);
}

//*****************************************************************************
//
//! Configures HLC event selection.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param eventSel is the value for HLC event selection. Generated by tool as
//!        \b TILEx_HLC_EVENT_SEL.
//!
//! This function configures the event selection for the High Level Controller.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configHLCEventSelect(CLB_TILE tile, uint32_t eventSel)
{
    WRITE_REG(CLB->TILE_GRP[tile].HLC_EVT, eventSel);
}

//*****************************************************************************
//
//! Program HLC instruction.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param instructionNum is the index into the HLC instruction memory. For
//!        example, a value of 0 corresponds to instruction 0 of event 0,
//!        a value of 1 corresponds to instruction 1 of event 0, and so on up
//!        to a value of 31 which corresponds to instruction 7 of event 3.
//! \param instruction is the instruction to be programmed. Generated by tool
//!        as \b TILEx_HLCINSTR_n where n is the instruction number.
//!
//! This function configures the CLB internal memory corresponding to the
//! specified HLC instruction number with the given instruction.
//!
//! \return None.
//
//*****************************************************************************
void CLB_programHLCInstruction(CLB_TILE tile, uint32_t instructionNum, uint32_t instruction)
{
    assert_param(instructionNum < 32U);

    CLB_writeInterface(tile, CLB_ADDR_HLC_BASE + instructionNum, instruction);
//    CLB_writeInterface(tile, instructionNum, instruction);
}

//*****************************************************************************
//
//! Set HLC registers.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param r0Init is the value to write to HLC register R0. Generated by tool
//!        as \b TILEx_HLC_R0_INIT.
//! \param r1Init is the value to write to HLC register R1. Generated by tool
//!        as \b TILEx_HLC_R1_INIT.
//! \param r2Init is the value to write to HLC register R2. Generated by tool
//!        as \b TILEx_HLC_R2_INIT.
//! \param r3Init is the value to write to HLC register R3. Generated by tool
//!        as \b TILEx_HLC_R3_INIT.
//!
//! This function configures the CLB internal memory corresponding to the HLC
//! registers R0-R3 with the specified values.
//!
//! \return None.
//
//*****************************************************************************
void CLB_setHLCRegisters(CLB_TILE tile, uint32_t r0Init, uint32_t r1Init, uint32_t r2Init, uint32_t r3Init)
{
    CLB_writeInterface(tile, CLB_ADDR_HLC_R0, r0Init);
    CLB_writeInterface(tile, CLB_ADDR_HLC_R1, r1Init);
    CLB_writeInterface(tile, CLB_ADDR_HLC_R2, r2Init);
    CLB_writeInterface(tile, CLB_ADDR_HLC_R3, r3Init);
}

//*****************************************************************************
//
//! Get HLC or counter register values.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param registerID is the internal register from which to read. Can be
//!        either an HLC register (\b CLB_REG_HLC_Rn) or a counter value
//!        (\b CLB_REG_CTR_Cn).
//!
//! \return Returns the value in the specified HLC register or counter.
//
//*****************************************************************************
uint32_t CLB_getRegister(CLB_TILE tile, CLB_Register registerID)
{
}

//*****************************************************************************
//
//! Get output status.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! \return Returns the output status of various components within the CLB tile
//!         such as a counter match or LUT output. Use the \b CLB_DBG_OUT_*
//!         masks from <tt>hw_clb.h</tt> to decode the bits.
//
//*****************************************************************************
uint32_t CLB_getOutputStatus(CLB_TILE tile)
{
}

//*****************************************************************************
//
//! Enable CLB Pipeline Mode.
//!
//! \param base is the base address of a CLB tile's logic config register.

//! This function enables the CLB Pipeline Mode
//!
//! \return None.
//
//*****************************************************************************
void CLB_enablePipelineMode(CLB_TILE tile)
{
    SET_BIT(CLB->TILE_GRP[tile].LOAD_EN, CLB_TILE_GRP_LOAD_EN_PIPELINE_EN_Msk);
}

//*****************************************************************************
//
//! Disable CLB Pipeline Mode.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB Pipeline Mode.
//!
//! \return None.
//
//*****************************************************************************
void CLB_disablePipelineMode(CLB_TILE tile)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].LOAD_EN, CLB_TILE_GRP_LOAD_EN_PIPELINE_EN_Msk);
}

//*****************************************************************************
//
//! Disable CLB Output Mask Updates.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB Output Mask updates
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableOutputMaskUpdates(CLB_TILE tile)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].SPITRANS, CLB_TILE_GRP_SPITRANS_BLKEN_Msk);
}

//*****************************************************************************
//
//! Enable CLB Output Mask Updates.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables the CLB Output Mask updates
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableOutputMaskUpdates(CLB_TILE tile)
{
    SET_BIT(CLB->TILE_GRP[tile].SPITRANS, CLB_TILE_GRP_SPITRANS_BLKEN_Msk);
}

//*****************************************************************************
//
//! Enable Input Pipeline Mode.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables the CLB Input Pipeline mode
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableInputPipelineMode(CLB_TILE tile, CLB_Inputs inID)
{
    SET_BIT(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_INPUT_FLT_PIPE_A_Msk << (uint32_t)inID);
}

//*****************************************************************************
//
//! Disable Input Pipeline Mode.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB Input Pipeline mode
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableInputPipelineMode(CLB_TILE tile, CLB_Inputs inID)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].INPUT_FLT, CLB_TILE_GRP_INPUT_FLT_PIPE_A_Msk << (uint32_t)inID);
}

//*****************************************************************************
//
//! Disable SPI RX Buffer Access.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function disables the CLB SPI RX Buffer access
//!
//! \return None.
//
//*****************************************************************************
void CLB_disableSPIBufferAccess(CLB_TILE tile)
{
    CLEAR_BIT(CLB->TILE_GRP[tile].SPITRANS, CLB_TILE_GRP_SPITRANS_EN_Msk);
}

//*****************************************************************************
//
//! Enable SPI RX Buffer Access.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function enables the CLB SPI RX Buffer access
//!
//! \return None.
//
//*****************************************************************************
void CLB_enableSPIBufferAccess(CLB_TILE tile)
{
    SET_BIT(CLB->TILE_GRP[tile].SPITRANS, CLB_TILE_GRP_SPITRANS_EN_Msk);
}

//*****************************************************************************
//
//! Configures SPI RX Buffer Load Signal event selection.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param eventSel is the value for HLC event selection. Generated by tool as
//!        \b TILEx_SPI_BUF_EVENT_SEL.
//!
//! This function configures the event selection for the SPI RX Buffer.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configSPIBufferLoadSignal(CLB_TILE tile, uint16_t eventSel)
{
    MODIFY_REG(CLB->TILE_GRP[tile].SPITRANS_DATA, CLB_TILE_GRP_SPITRANS_DATA_VLD_SEL_Msk,
               (uint32_t)eventSel << CLB_TILE_GRP_SPITRANS_DATA_VLD_SEL_Pos);
}

//*****************************************************************************
//
//! Configures SPI Export HLC R0 Shift value.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param shiftVal is the value for SPI export HLC R0 bit range selection.
//!
//! This function configures the SPI Export HLC R0 Shift value.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configSPIBufferShift(CLB_TILE tile, uint16_t shiftVal)
{
    MODIFY_REG(CLB->TILE_GRP[tile].SPITRANS_DATA, CLB_TILE_GRP_SPITRANS_DATA_SEL_Msk,
               (uint32_t)shiftVal << CLB_TILE_GRP_SPITRANS_DATA_SEL_Pos);
}

//*****************************************************************************
//
//! Configures Counter load and match.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param counterID is the specified counter unit.
//! \param load is the value for counter's load mode. Generated by tool as
//!        \b TILEx_COUNTER_n_LOAD_VAL where n is the counter number.
//! \param match1 is the value for counter's match 1. Generated by tool as
//!        \b TILEx_COUNTER_n_MATCH1_VAL where n is the counter number.
//! \param match2 is the value for counter's match 2. Generated by tool as
//!        \b TILEx_COUNTER_n_MATCH2_VAL where n is the counter number.
//!
//! This function configures the CLB internal memory corresponding to the
//! counter block's load and match values.
//!
//! \return None.
//
//*****************************************************************************
void CLB_configCounterLoadMatch(CLB_TILE tile, CLB_Counters counterID, uint32_t load, uint32_t match1, uint32_t match2)
{
    switch (counterID)
    {
    case CLB_CTR0:
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_0_LOAD, load);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_0_MATCH1, match1);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_0_MATCH2, match2);
        break;

    case CLB_CTR1:
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_1_LOAD, load);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_1_MATCH1, match1);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_1_MATCH2, match2);
        break;

    case CLB_CTR2:
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_2_LOAD, load);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_2_MATCH1, match1);
        CLB_writeInterface(tile, CLB_ADDR_COUNTER_2_MATCH2, match2);
        break;

    default:
        //
        // Invalid counterID value
        //
        break;
    }
}

//*****************************************************************************
//
//! Clear FIFO registers.
//!
//! \param base is the base address of a CLB tile's logic config register.
//!
//! This function clears the PUSH/PULL FIFOs as well as its pointers.
//!
//! \return None.
//
//*****************************************************************************
void CLB_clearFIFOs(CLB_TILE tile)
{
    WRITE_REG(CLB->TILE_GRP[tile].PULL_A, 0U);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_B, 0U);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_C, 0U);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_D, 0U);
    WRITE_REG(CLB->TILE_GRP[tile].BUF_PTR, 0U);
}

//*****************************************************************************
//
//! Configure the FIFO registers.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param pullData[] is a pointer to an array of bytes which needs to be
//! written into the FIFO. The 0th FIFO data is in the 0th index.
//!
//! This function writes to the PULL FIFO. This also clears the FIFOs and
//! its pointer using the CLB_clearFIFOs() API prior to writing to
//! the FIFO.
//!
//! \return None.
//
//*****************************************************************************
void CLB_writeFIFOs(CLB_TILE tile, const uint32_t pullData[])
{
    //
    // Clear the FIFO and pointer
    //
    CLB_clearFIFOs(tile);

    //
    // Write data into the FIFO.
    //
    WRITE_REG(CLB->TILE_GRP[tile].PULL_A, pullData[0U]);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_B, pullData[1U]);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_C, pullData[2U]);
    WRITE_REG(CLB->TILE_GRP[tile].PULL_D, pullData[3U]);
}

//*****************************************************************************
//
//! Read FIFO registers.
//!
//! \param base is the base address of a CLB tile's logic config register.
//! \param pushData[] is a pointer to an array of bytes which needs to be
//! read from the FIFO.
//!
//! This function reads from the PUSH FIFO. The 0th FIFO data would be in
//! the 0th index.
//!
//! \return None.
//
//*****************************************************************************
void CLB_readFIFOs(CLB_TILE tile, uint32_t pushData[])
{
    //
    // Read data from the FIFO.
    //
    pushData[0U] = READ_REG(CLB->TILE_GRP[tile].PUSH_A_RPT);
    pushData[1U] = READ_REG(CLB->TILE_GRP[tile].PUSH_B_RPT);
    pushData[2U] = READ_REG(CLB->TILE_GRP[tile].PUSH_C_RPT);
    pushData[3U] = READ_REG(CLB->TILE_GRP[tile].PUSH_D_RPT);
}

void CLB_disableLock(void)
{
    //
    // Setting the lock bit requires key 0x5A5A to be written at the same time
    //
    WRITE_REG(CLB->LOCK, CLB_LOCK_KEY);
}

uint32_t CLB_getInputLUT0(CSB_Sel A, CSB_Sel B, CSB_Sel C)
{
    return (uint32_t)A << CLB_TILE_GRP_LUT4_IN0_SEL_A_Pos | (uint32_t)B <<
           CLB_TILE_GRP_LUT4_IN0_SEL_B_Pos | (uint32_t)C <<
           CLB_TILE_GRP_LUT4_IN0_SEL_C_Pos;
}

uint32_t CLB_getInputLUT1(CSB_Sel A, CSB_Sel B, CSB_Sel C)
{
    return (uint32_t)A << CLB_TILE_GRP_LUT4_IN1_SEL_A_Pos | (uint32_t)B <<
           CLB_TILE_GRP_LUT4_IN1_SEL_B_Pos | (uint32_t)C << CLB_TILE_GRP_LUT4_IN1_SEL_C_Pos;
}

uint32_t CLB_getInputLUT2(CSB_Sel A, CSB_Sel B, CSB_Sel C)
{
    return (uint32_t)A << CLB_TILE_GRP_LUT4_IN2_SEL_A_Pos | (uint32_t)B <<
           CLB_TILE_GRP_LUT4_IN2_SEL_B_Pos | (uint32_t)C << CLB_TILE_GRP_LUT4_IN2_SEL_C_Pos;
}

uint32_t CLB_getInputLUT3(CSB_Sel A, CSB_Sel B, CSB_Sel C)
{
    return (uint32_t)A << CLB_TILE_GRP_LUT4_IN3_SEL_A_Pos | (uint32_t)B <<
           CLB_TILE_GRP_LUT4_IN3_SEL_B_Pos | (uint32_t)C << CLB_TILE_GRP_LUT4_IN3_SEL_C_Pos;
}

uint32_t CLB_getOuputLUT(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3, uint8_t func)
{
    return (uint32_t)in1 << CLB_TILE_GRP_OUTLUT4_IN0_SEL_Pos | (uint32_t)in2 <<
           CLB_TILE_GRP_OUTLUT4_IN1_SEL_Pos | (uint32_t)in3 << CLB_TILE_GRP_OUTLUT4_IN2_SEL_Pos | (uint32_t)func <<
           CLB_TILE_GRP_OUTLUT4_FUNC_Pos;
}

uint32_t CLB_config3CSB(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3)
{
    return (uint32_t)in1 << CLB_TILE_GRP_LUT4_IN1_SEL_A_Pos | (uint32_t)in2 <<
           CLB_TILE_GRP_LUT4_IN1_SEL_B_Pos | (uint32_t)in3 << CLB_TILE_GRP_LUT4_IN1_SEL_C_Pos;
}

uint32_t CLB_config4CSB(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3, CSB_Sel in4)
{
    return (uint32_t)in1 << CLB_TILE_GRP_HLC_EVT_SEL_A_Pos | (uint32_t)in2 <<
           CLB_TILE_GRP_HLC_EVT_SEL_B_Pos | (uint32_t)in3 << CLB_TILE_GRP_HLC_EVT_SEL_C_Pos | (uint32_t)in4 <<
           CLB_TILE_GRP_HLC_EVT_SEL_D_Pos;
}

uint32_t CLB_getHLCInst(bool isLastInstr, HLC_Opcode opcode, HLC_Reg src, HLC_Reg des)
{
    return (uint32_t)isLastInstr << 11 | (uint32_t)opcode << 6 | (uint32_t)src << 3 | (uint32_t)des;
}
