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

#ifndef __ET6x_CLB_H
#define __ET6x_CLB_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET6003_Driver
 * @{
 */

/** @addtogroup CLB
 * @{
 */


//*****************************************************************************
//
// Address offsets from LOGICCFG to LOGICCTL and DATAEXCH register memory maps
//
//*****************************************************************************
#define CLB_LOGICCTL    0x0100U
#define CLB_DATAEXCH    0x0180U

//*****************************************************************************
//
// Address offsets for CLB-internal memory space
//
//*****************************************************************************
#define CLB_ADDR_COUNTER_0_LOAD      0x0U
#define CLB_ADDR_COUNTER_1_LOAD      0x1U
#define CLB_ADDR_COUNTER_2_LOAD      0x2U

#define CLB_ADDR_COUNTER_0_MATCH1    0x4U
#define CLB_ADDR_COUNTER_1_MATCH1    0x5U
#define CLB_ADDR_COUNTER_2_MATCH1    0x6U

#define CLB_ADDR_COUNTER_0_MATCH2    0x8U
#define CLB_ADDR_COUNTER_1_MATCH2    0x9U
#define CLB_ADDR_COUNTER_2_MATCH2    0xAU

#define CLB_ADDR_HLC_R0              0xCU
#define CLB_ADDR_HLC_R1              0xDU
#define CLB_ADDR_HLC_R2              0xEU
#define CLB_ADDR_HLC_R3              0xFU

#define CLB_ADDR_HLC_BASE            0x20U
#define CLB_NUM_HLC_INSTR            31U

//*****************************************************************************
//
// PUSH/PULL FIFO size (32-bit registers)
//
//*****************************************************************************
#define CLB_FIFO_SIZE    4U

//*****************************************************************************
//
// Key to enable writes to the CLB registers
//
//*****************************************************************************
#define CLB_LOCK_KEY    0x5A5AU

//*****************************************************************************
//
// Shift and masks needed by the API for Input selection
//
//*****************************************************************************
#define CLB_LCL_MUX_SEL_MISC_INPUT_SEL_M       0x20U
#define CLB_LCL_MUX_SEL_MISC_INPUT_SEL_S       28U
#define CLB_LCL_MUX_SEL_MISC_INPUT_SEL_BITM    (uint32_t)1U

//*****************************************************************************
//
//! Values that can be passed to control the CLB output enable signal. It can
//! be passed to CLB_setOutputMask() as the \e outputMask parameter.
//
//*****************************************************************************
#define CLB_OUTPUT_00    0x00000001U //!< Mask for CLB OUTPUT ENABLE/DISABLE 0
#define CLB_OUTPUT_01    0x00000002U //!< Mask for CLB OUTPUT ENABLE/DISABLE 1
#define CLB_OUTPUT_02    0x00000004U //!< Mask for CLB OUTPUT ENABLE/DISABLE 2
#define CLB_OUTPUT_03    0x00000008U //!< Mask for CLB OUTPUT ENABLE/DISABLE 3
#define CLB_OUTPUT_04    0x00000010U //!< Mask for CLB OUTPUT ENABLE/DISABLE 4
#define CLB_OUTPUT_05    0x00000020U //!< Mask for CLB OUTPUT ENABLE/DISABLE 5
#define CLB_OUTPUT_06    0x00000040U //!< Mask for CLB OUTPUT ENABLE/DISABLE 6
#define CLB_OUTPUT_07    0x00000080U //!< Mask for CLB OUTPUT ENABLE/DISABLE 7
#define CLB_OUTPUT_08    0x00000100U //!< Mask for CLB OUTPUT ENABLE/DISABLE 8
#define CLB_OUTPUT_09    0x00000200U //!< Mask for CLB OUTPUT ENABLE/DISABLE 9
#define CLB_OUTPUT_10    0x00000400U //!< Mask for CLB OUTPUT ENABLE/DISABLE 10
#define CLB_OUTPUT_11    0x00000800U //!< Mask for CLB OUTPUT ENABLE/DISABLE 11
#define CLB_OUTPUT_12    0x00001000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 12
#define CLB_OUTPUT_13    0x00002000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 13
#define CLB_OUTPUT_14    0x00004000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 14
#define CLB_OUTPUT_15    0x00008000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 15
#define CLB_OUTPUT_16    0x00010000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 16
#define CLB_OUTPUT_17    0x00020000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 17
#define CLB_OUTPUT_18    0x00040000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 18
#define CLB_OUTPUT_19    0x00080000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 19
#define CLB_OUTPUT_20    0x00100000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 20
#define CLB_OUTPUT_21    0x00200000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 21
#define CLB_OUTPUT_22    0x00400000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 22
#define CLB_OUTPUT_23    0x00800000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 23
#define CLB_OUTPUT_24    0x01000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 24
#define CLB_OUTPUT_25    0x02000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 25
#define CLB_OUTPUT_26    0x04000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 26
#define CLB_OUTPUT_27    0x08000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 27
#define CLB_OUTPUT_28    0x10000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 28
#define CLB_OUTPUT_29    0x20000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 29
#define CLB_OUTPUT_30    0x40000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 30
#define CLB_OUTPUT_31    0x80000000U //!< Mask for CLB OUTPUT ENABLE/DISABLE 31

//*****************************************************************************
//
//! Values that can be passed to select CLB input signal
//
//*****************************************************************************
typedef enum
{
    CLB_IN0 = 0,                    //!< Input 0
    CLB_IN1 = 1,                    //!< Input 1
    CLB_IN2 = 2,                    //!< Input 2
    CLB_IN3 = 3,                    //!< Input 3
    CLB_IN4 = 4,                    //!< Input 4
    CLB_IN5 = 5,                    //!< Input 5
    CLB_IN6 = 6,                    //!< Input 6
    CLB_IN7 = 7                     //!< Input 7
} CLB_Inputs;

//*****************************************************************************
//
//! Values that can be passed to select CLB output signal. It can be passed to
//! CLB_configOutputLUT() as the \e outID parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_OUT0 = 0,                   //!< Output 0
    CLB_OUT1 = 1,                   //!< Output 1
    CLB_OUT2 = 2,                   //!< Output 2
    CLB_OUT3 = 3,                   //!< Output 3
    CLB_OUT4 = 4,                   //!< Output 4
    CLB_OUT5 = 5,                   //!< Output 5
    CLB_OUT6 = 6,                   //!< Output 6
    CLB_OUT7 = 7                    //!< Output 7
} CLB_Outputs;

//*****************************************************************************
//
//! Values that can be passed to select CLB AOC signal. It can be passed to
//! CLB_configAOC() as the \e aocID parameter.
//! AOC is the Asynchronous Output Conditioning block.
//
//*****************************************************************************
typedef enum
{
    CLB_AOC0 = 0,                   //!< AOC 0
    CLB_AOC1 = 1,                   //!< AOC 1
    CLB_AOC2 = 2,                   //!< AOC 2
    CLB_AOC3 = 3,                   //!< AOC 3
    CLB_AOC4 = 4,                   //!< AOC 4
    CLB_AOC5 = 5,                   //!< AOC 5
    CLB_AOC6 = 6,                   //!< AOC 6
    CLB_AOC7 = 7                    //!< AOC 7
} CLB_AOCs;

//*****************************************************************************
//
//! Values that can be passed to set/clear CLB SW release signals. It can
//! be passed to CLB_writeSWReleaseControl() as the \e inID parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_SW_RLS_CTRL0 = 0,           //!< SW RLS CTRL 0
    CLB_SW_RLS_CTRL1 = 1,           //!< SW RLS CTRL 1
    CLB_SW_RLS_CTRL2 = 2,           //!< SW RLS CTRL 2
    CLB_SW_RLS_CTRL3 = 3,           //!< SW RLS CTRL 3
    CLB_SW_RLS_CTRL4 = 4,           //!< SW RLS CTRL 4
    CLB_SW_RLS_CTRL5 = 5,           //!< SW RLS CTRL 5
    CLB_SW_RLS_CTRL6 = 6,           //!< SW RLS CTRL 6
    CLB_SW_RLS_CTRL7 = 7            //!< SW RLS CTRL 7
} CLB_SWReleaseCtrl;

//*****************************************************************************
//
//! Values that can be passed to set/clear CLB SW release signals. It can
//! be passed to CLB_writeSWGateControl() as the \e inID parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_SW_GATE_CTRL0 = 0,           //!< SW GATE CTRL 0
    CLB_SW_GATE_CTRL1 = 1,           //!< SW GATE CTRL 1
    CLB_SW_GATE_CTRL2 = 2,           //!< SW GATE CTRL 2
    CLB_SW_GATE_CTRL3 = 3,           //!< SW GATE CTRL 3
    CLB_SW_GATE_CTRL4 = 4,           //!< SW GATE CTRL 4
    CLB_SW_GATE_CTRL5 = 5,           //!< SW GATE CTRL 5
    CLB_SW_GATE_CTRL6 = 6,           //!< SW GATE CTRL 6
    CLB_SW_GATE_CTRL7 = 7            //!< SW GATE CTRL 7
} CLB_SWGateCtrl;

//*****************************************************************************
//
//! Values that can be passed to select CLB counter. It can be passed to
//! CLB_configCounterLoadMatch() as the \e counterID parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_CTR0 = 0,                   //!< Counter 0
    CLB_CTR1 = 1,                   //!< Counter 1
    CLB_CTR2 = 2                    //!< Counter 2
} CLB_Counters;

//*****************************************************************************
//
//! Values that can be passed to CLB_getRegister() as the \e registerID
//! parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_REG_HLC_R0,  //!< HLC R0 register
    CLB_REG_HLC_R1,  //!< HLC R1 register
    CLB_REG_HLC_R2,  //!< HLC R2 register
    CLB_REG_HLC_R3,  //!< HLC R3 register
    CLB_REG_CTR_C0,  //!< Counter 0 register
    CLB_REG_CTR_C1,  //!< Counter 1 register
    CLB_REG_CTR_C2   //!< Counter 2 register
} CLB_Register;

//*****************************************************************************
//
//! Values that can be passed to CLB_selectInputFilter() as the \e filterType
//! parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_FILTER_NONE         = 0,    //!< No filtering
    CLB_FILTER_RISING_EDGE  = 1,    //!< Rising edge detect
    CLB_FILTER_FALLING_EDGE = 2,    //!< Falling edge detect
    CLB_FILTER_ANY_EDGE     = 3     //!< Any edge detect
} CLB_FilterType;

//*****************************************************************************
//
//! Values that can be passed to CLB_configGPInputMux() as the \e gpMuxCfg
//! parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_GP_IN_MUX_EXTERNAL = 0,     //!< Use external input path
    CLB_GP_IN_MUX_GP_REG   = 1      //!< Use CLB_GP_REG bit value as input
} CLB_GPInputMux;

//*****************************************************************************
//
//! Values that can be passed to CLB_configLocalInputMux() as the
//! \e localMuxCfg parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_LOCAL_IN_MUX_GLOBAL_IN        = 0,     //!< Global input mux selection
    CLB_LOCAL_IN_MUX_EPWM_DCAEVT1     = 1,     //!< EPWMx DCAEVT1
    CLB_LOCAL_IN_MUX_EPWM_DCAEVT2     = 2,     //!< EPWMx DCAEVT2
    CLB_LOCAL_IN_MUX_EPWM_DCBEVT1     = 3,     //!< EPWMx DCBEVT1
    CLB_LOCAL_IN_MUX_EPWM_DCBEVT2     = 4,     //!< EPWMx DCBEVT2
    CLB_LOCAL_IN_MUX_EPWM_DCAH        = 5,     //!< EPWMx DCAH
    CLB_LOCAL_IN_MUX_EPWM_DCAL        = 6,     //!< EPWMx DCAL
    CLB_LOCAL_IN_MUX_EPWM_DCBH        = 7,     //!< EPWMx DCBH
    CLB_LOCAL_IN_MUX_EPWM_DCBL        = 8,     //!< EPWMx DCBL
    CLB_LOCAL_IN_MUX_EPWM_OST         = 9,     //!< EPWMx OST
    CLB_LOCAL_IN_MUX_EPWM_CBC         = 10,    //!< EPWMx CBC
    CLB_LOCAL_IN_MUX_ECAP_ECAPIN      = 11,    //!< ECAPx ECAPIN
    CLB_LOCAL_IN_MUX_ETIM_PWMOUT      = 12,    //!< ECAPx ETIM PWM OUT
    CLB_LOCAL_IN_MUX_ECAP_ETIM_OUT_EN = 13,    //!< ECAPx ETIM_OUT_EN
    CLB_LOCAL_IN_MUX_ECAP_CEVT1       = 14,    //!< ECAPx CEVT1
    CLB_LOCAL_IN_MUX_ECAP_CEVT2       = 15,    //!< ECAPx CEVT2
    CLB_LOCAL_IN_MUX_ECAP_CEVT3       = 16,    //!< ECAPx CEVT3
    CLB_LOCAL_IN_MUX_ECAP_CEVT4       = 17,    //!< ECAPx CEVT4
    CLB_LOCAL_IN_MUX_EQEP_EQEPA       = 18,    //!< EQEPx EQEPA
    CLB_LOCAL_IN_MUX_EQEP_EQEPB       = 19,    //!< EQEPx EQEPB
    CLB_LOCAL_IN_MUX_EQEP_EQEPI       = 20,    //!< EQEPx EQEPI
    CLB_LOCAL_IN_MUX_EQEP_EQEPS       = 21,    //!< EQEPx EQEPS
    CLB_LOCAL_IN_MUX_CPU1_HALT        = 24,    //!< CPU1.HALT
    CLB_LOCAL_IN_MUX_SPIM_TXD         = 25,    //!< SPIM_TXD
    CLB_LOCAL_IN_MUX_SPISCLK          = 26,    //!< SPIS Sclk IN
    CLB_LOCAL_IN_MUX_SPIS_RXD         = 27,    //!< SPIS RXD
    CLB_LOCAL_IN_MUX_SPIS_SS_IN_N     = 28,    //!< SPIS CS
    CLB_LOCAL_IN_MUX_SCI_TX           = 29,    //!< SCI TX
    CLB_LOCAL_IN_MUX_SPIPOCI_OUT      = 30,    //!< SPIPOCI(OUT)
    CLB_LOCAL_IN_MUX_CLB_PSCLK        = 31,    //!< CLB prescaled clock
    CLB_LOCAL_IN_MUX_EPWM4A           = 32,    //!< EPWM4A (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM4A_OE        = 33,    //!< EPWM4A trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM4B           = 34,    //!< EPWM4B (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM4B_OE        = 35,    //!< EPWM4B trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM5A           = 36,    //!< EPWM5A (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM5A_OE        = 37,    //!< EPWM5A trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM5B           = 38,    //!< EPWM5B (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM5B_OE        = 39,    //!< EPWM5B trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM6A           = 40,    //!< EPWM6A (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM6A_OE        = 41,    //!< EPWM6A trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM6B           = 42,    //!< EPWM6B (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM6B_OE        = 43,    //!< EPWM6B trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM7A           = 44,    //!< EPWM7A (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM7A_OE        = 45,    //!< EPWM7A trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM7B           = 46,    //!< EPWM7B (CLB 1-4)
    CLB_LOCAL_IN_MUX_EPWM7B_OE        = 47,    //!< EPWM7B trip output (CLB 1-4)
    CLB_LOCAL_IN_MUX_INPUT1           = 48,    //!< CLBINPUTXBAR INPUT1
    CLB_LOCAL_IN_MUX_INPUT2           = 49,    //!< CLBINPUTXBAR INPUT2
    CLB_LOCAL_IN_MUX_INPUT3           = 50,    //!< CLBINPUTXBAR INPUT3
    CLB_LOCAL_IN_MUX_INPUT4           = 51,    //!< CLBINPUTXBAR INPUT4
    CLB_LOCAL_IN_MUX_INPUT5           = 52,    //!< CLBINPUTXBAR INPUT5
    CLB_LOCAL_IN_MUX_INPUT6           = 53,    //!< CLBINPUTXBAR INPUT6
    CLB_LOCAL_IN_MUX_INPUT7           = 54,    //!< CLBINPUTXBAR INPUT7
    CLB_LOCAL_IN_MUX_INPUT8           = 55,    //!< CLBINPUTXBAR INPUT8
    CLB_LOCAL_IN_MUX_INPUT9           = 56,    //!< CLBINPUTXBAR INPUT9
    CLB_LOCAL_IN_MUX_INPUT10          = 57,    //!< CLBINPUTXBAR INPUT10
    CLB_LOCAL_IN_MUX_INPUT11          = 58,    //!< CLBINPUTXBAR INPUT11
    CLB_LOCAL_IN_MUX_INPUT12          = 59,    //!< CLBINPUTXBAR INPUT12
    CLB_LOCAL_IN_MUX_INPUT13          = 60,    //!< CLBINPUTXBAR INPUT13
    CLB_LOCAL_IN_MUX_INPUT14          = 61,    //!< CLBINPUTXBAR INPUT14
    CLB_LOCAL_IN_MUX_INPUT15          = 62,    //!< CLBINPUTXBAR INPUT15
    CLB_LOCAL_IN_MUX_INPUT16          = 63     //!< CLBINPUTXBAR INPUT16
} CLB_LocalInputMux;

//*****************************************************************************
//
//! Values that can be passed to CLB_configGlobalInputMux() as the
//! \e globalMuxCfg parameter.
//
//*****************************************************************************
typedef enum
{
    CLB_GLOBAL_IN_MUX_EPWM0A                  = 0,    //!< EPWM0A
    CLB_GLOBAL_IN_MUX_EPWM0A_OE               = 1,    //!< EPWM0A trip output
    CLB_GLOBAL_IN_MUX_EPWM0B                  = 2,    //!< EPWM0B
    CLB_GLOBAL_IN_MUX_EPWM0B_OE               = 3,    //!< EPWM0B trip output
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_ZERO          = 4,    //!< EPWM0 TBCTR = Zero
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_PRD           = 5,    //!< EPWM0 TBCTR = TBPRD
    CLB_GLOBAL_IN_MUX_EPWM0_CTRDIR            = 6,    //!< EPWM0 CTRDIR
    CLB_GLOBAL_IN_MUX_EPWM0_TBCLK             = 7,    //!< EPWM0 RESERVED
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_CMPA          = 8,    //!< EPWM0 TBCTR = CMPA
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_CMPB          = 9,    //!< EPWM0 TBCTR = CMPB
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_CMPC          = 10,   //!< EPWM0 TBCTR = CMPC
    CLB_GLOBAL_IN_MUX_EPWM0_CTR_CMPD          = 11,   //!< EPWM0 TBCTR = CMPD
    CLB_GLOBAL_IN_MUX_EPWM0A_AQ               = 12,   //!< EPWM0A AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM0B_AQ               = 13,   //!< EPWM0B AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM0A_DB               = 14,   //!< EPWM0A DB submodule output
    CLB_GLOBAL_IN_MUX_EPWM0B_DB               = 15,   //!< EPWM0B DB submodule output

    CLB_GLOBAL_IN_MUX_EPWM1A                  = 16,   //!< EPWM1A
    CLB_GLOBAL_IN_MUX_EPWM1A_OE               = 17,   //!< EPWM1A trip output
    CLB_GLOBAL_IN_MUX_EPWM1B                  = 18,   //!< EPWM1B
    CLB_GLOBAL_IN_MUX_EPWM1B_OE               = 19,   //!< EPWM1B trip output
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_ZERO          = 20,   //!< EPWM1 TBCTR = Zero
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_PRD           = 21,   //!< EPWM1 TBCTR = TBPRD
    CLB_GLOBAL_IN_MUX_EPWM1_CTRDIR            = 22,   //!< EPWM1 CTRDIR
    CLB_GLOBAL_IN_MUX_EPWM1_TBCLK             = 23,   //!< EPWM1 TBCLK
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_CMPA          = 24,   //!< EPWM1 TBCTR = CMPA
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_CMPB          = 25,   //!< EPWM1 TBCTR = CMPB
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_CMPC          = 26,   //!< EPWM1 TBCTR = CMPC
    CLB_GLOBAL_IN_MUX_EPWM1_CTR_CMPD          = 27,   //!< EPWM1 TBCTR = CMPD
    CLB_GLOBAL_IN_MUX_EPWM1A_AQ               = 28,   //!< EPWM1A AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM1B_AQ               = 29,   //!< EPWM1B AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM1A_DB               = 30,   //!< EPWM1A DB submodule output
    CLB_GLOBAL_IN_MUX_EPWM1B_DB               = 31,   //!< EPWM1B DB submodule output

    CLB_GLOBAL_IN_MUX_EPWM2A                  = 32,   //!< EPWM2A
    CLB_GLOBAL_IN_MUX_EPWM2A_OE               = 33,   //!< EPWM2A trip output
    CLB_GLOBAL_IN_MUX_EPWM2B                  = 34,   //!< EPWM2B
    CLB_GLOBAL_IN_MUX_EPWM2B_OE               = 35,   //!< EPWM2B trip output
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_ZERO          = 36,   //!< EPWM2 TBCTR = Zero
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_PRD           = 37,   //!< EPWM2 TBCTR = TBPRD
    CLB_GLOBAL_IN_MUX_EPWM2_CTRDIR            = 38,   //!< EPWM2 CTRDIR
    CLB_GLOBAL_IN_MUX_EPWM2_TBCLK             = 39,   //!< EPWM2 TBCLK
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_CMPA          = 40,   //!< EPWM2 TBCTR = CMPA
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_CMPB          = 41,   //!< EPWM2 TBCTR = CMPB
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_CMPC          = 42,   //!< EPWM2 TBCTR = CMPC
    CLB_GLOBAL_IN_MUX_EPWM2_CTR_CMPD          = 43,   //!< EPWM2 TBCTR = CMPD
    CLB_GLOBAL_IN_MUX_EPWM2A_AQ               = 44,   //!< EPWM2A AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM2B_AQ               = 45,   //!< EPWM2B AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM2A_DB               = 46,   //!< EPWM2A DB submodule output
    CLB_GLOBAL_IN_MUX_EPWM2B_DB               = 47,   //!< EPWM2B DB submodule output

    CLB_GLOBAL_IN_MUX_EPWM3A                  = 48,   //!< EPWM3A
    CLB_GLOBAL_IN_MUX_EPWM3A_OE               = 49,   //!< EPWM3A trip output
    CLB_GLOBAL_IN_MUX_EPWM3B                  = 50,   //!< EPWM3B
    CLB_GLOBAL_IN_MUX_EPWM3B_OE               = 51,   //!< EPWM3B trip output
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_ZERO          = 52,   //!< EPWM3 TBCTR = Zero
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_PRD           = 53,   //!< EPWM3 TBCTR = TBPRD
    CLB_GLOBAL_IN_MUX_EPWM3_CTRDIR            = 54,   //!< EPWM3 CTRDIR
    CLB_GLOBAL_IN_MUX_EPWM3_TBCLK             = 55,   //!< EPWM3 TBCLK
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_CMPA          = 56,   //!< EPWM3 TBCTR = CMPA
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_CMPB          = 57,   //!< EPWM3 TBCTR = CMPB
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_CMPC          = 58,   //!< EPWM3 TBCTR = CMPC
    CLB_GLOBAL_IN_MUX_EPWM3_CTR_CMPD          = 59,   //!< EPWM3 TBCTR = CMPD
    CLB_GLOBAL_IN_MUX_EPWM3A_AQ               = 60,   //!< EPWM3A AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM3B_AQ               = 61,   //!< EPWM3B AQ submodule output
    CLB_GLOBAL_IN_MUX_EPWM3A_DB               = 62,   //!< EPWM3A DB submodule output
    CLB_GLOBAL_IN_MUX_EPWM3B_DB               = 63,   //!< EPWM3B DB submodule output

    CLB_GLOBAL_IN_MUX_CLB_AUXSIG0             = 64,   //!< CLB X-BAR AUXSIG0
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG1             = 65,   //!< CLB X-BAR AUXSIG1
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG2             = 66,   //!< CLB X-BAR AUXSIG2
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG3             = 67,   //!< CLB X-BAR AUXSIG3
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG4             = 68,   //!< CLB X-BAR AUXSIG4
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG5             = 69,   //!< CLB X-BAR AUXSIG5
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG6             = 70,   //!< CLB X-BAR AUXSIG6
    CLB_GLOBAL_IN_MUX_CLB_AUXSIG7             = 71,   //!< CLB X-BAR AUXSIG7

    CLB_GLOBAL_IN_MUX_CLB1_OUT16              = 72,   //!< CLB1 OUT16
    CLB_GLOBAL_IN_MUX_CLB1_OUT17              = 73,   //!< CLB1 OUT17
    CLB_GLOBAL_IN_MUX_CLB1_OUT18              = 74,   //!< CLB1 OUT18
    CLB_GLOBAL_IN_MUX_CLB1_OUT19              = 75,   //!< CLB1 OUT19
    CLB_GLOBAL_IN_MUX_CLB1_OUT20              = 76,   //!< CLB1 OUT20
    CLB_GLOBAL_IN_MUX_CLB1_OUT21              = 77,   //!< CLB1 OUT21
    CLB_GLOBAL_IN_MUX_CLB1_OUT22              = 78,   //!< CLB1 OUT22
    CLB_GLOBAL_IN_MUX_CLB1_OUT23              = 79,   //!< CLB1 OUT23

    CLB_GLOBAL_IN_MUX_CLB2_OUT16              = 80,   //!< CLB2 OUT16
    CLB_GLOBAL_IN_MUX_CLB2_OUT17              = 81,   //!< CLB2 OUT17
    CLB_GLOBAL_IN_MUX_CLB2_OUT18              = 82,   //!< CLB2 OUT18
    CLB_GLOBAL_IN_MUX_CLB2_OUT19              = 83,   //!< CLB2 OUT19
    CLB_GLOBAL_IN_MUX_CLB2_OUT20              = 84,   //!< CLB2 OUT20
    CLB_GLOBAL_IN_MUX_CLB2_OUT21              = 85,   //!< CLB2 OUT21
    CLB_GLOBAL_IN_MUX_CLB2_OUT22              = 86,   //!< CLB2 OUT22
    CLB_GLOBAL_IN_MUX_CLB2_OUT23              = 87,   //!< CLB2 OUT23

    CLB_GLOBAL_IN_MUX_CLB3_OUT16              = 88,   //!< CLB3 OUT16
    CLB_GLOBAL_IN_MUX_CLB3_OUT17              = 89,   //!< CLB3 OUT17
    CLB_GLOBAL_IN_MUX_CLB3_OUT18              = 90,   //!< CLB3 OUT18
    CLB_GLOBAL_IN_MUX_CLB3_OUT19              = 91,   //!< CLB3 OUT19
    CLB_GLOBAL_IN_MUX_CLB3_OUT20              = 92,   //!< CLB3 OUT20
    CLB_GLOBAL_IN_MUX_CLB3_OUT21              = 93,   //!< CLB3 OUT21
    CLB_GLOBAL_IN_MUX_CLB3_OUT22              = 94,   //!< CLB3 OUT22
    CLB_GLOBAL_IN_MUX_CLB3_OUT23              = 95,   //!< CLB3 OUT23

    CLB_GLOBAL_IN_MUX_CLB4_OUT16              = 96,   //!< CLB4 OUT16
    CLB_GLOBAL_IN_MUX_CLB4_OUT17              = 97,   //!< CLB4 OUT17
    CLB_GLOBAL_IN_MUX_CLB4_OUT18              = 98,   //!< CLB4 OUT18
    CLB_GLOBAL_IN_MUX_CLB4_OUT19              = 99,   //!< CLB4 OUT19
    CLB_GLOBAL_IN_MUX_CLB4_OUT20              = 100,  //!< CLB4 OUT20
    CLB_GLOBAL_IN_MUX_CLB4_OUT21              = 101,  //!< CLB4 OUT21
    CLB_GLOBAL_IN_MUX_CLB4_OUT22              = 102,  //!< CLB4 OUT22
    CLB_GLOBAL_IN_MUX_CLB4_OUT23              = 103,  //!< CLB4 OUT23

    CLB_GLOBAL_IN_MUX_SPI1_SPICLK             = 120,  //!< SPI1 SPICLK OUT
    CLB_GLOBAL_IN_MUX_SPI1_SPIPOCI_CONTROLLER = 121,  //!< SPI1 SPIPOCI Controller IN
    CLB_GLOBAL_IN_MUX_SPI1_SPIPTE             = 122,  //!< SPI1 SPIPTE OUT
    CLB_GLOBAL_IN_MUX_SPI2_SPICLK             = 123,  //!< SPI2 SPICLK OUT
    CLB_GLOBAL_IN_MUX_SPI2_SPIPOCI_CONTROLLER = 124,  //!< SPI2 SPIPOCI Controller IN
    CLB_GLOBAL_IN_MUX_SPI2_SPIPTE             = 125,  //!< SPI2 SPIPTE OUT
} CLB_GlobalInputMux;

typedef enum
{
    CLB_TILE1,
    CLB_TILE2,
    CLB_TILE3,
    CLB_TILE4
} CLB_TILE;

void CLB_enableCLB(CLB_TILE tile);
void CLB_disableCLB(CLB_TILE tile);
void CLB_enableNMI(CLB_TILE tile);
void CLB_disableNMI(CLB_TILE tile);
void CLB_configureClockPrescalar(CLB_TILE tile, uint16_t prescl);
void CLB_configureStrobeMode(CLB_TILE tile, uint16_t strb);
void CLB_writeSWReleaseControl(CLB_TILE tile, CLB_SWReleaseCtrl inID, bool val);
void CLB_writeSWGateControl(CLB_TILE tile, CLB_SWGateCtrl inID, bool val);
void CLB_configCounterTapSelects(CLB_TILE tile, uint32_t tapSel);
void CLB_configAOC(CLB_TILE tile, CLB_AOCs aocID, uint32_t aocCfg);
void CLB_enableLock(void);
void CLB_enableLock(void);
void CLB_selectInputFilter(CLB_TILE tile, CLB_Inputs inID, CLB_FilterType filterType);
void CLB_enableSynchronization(CLB_TILE tile, CLB_Inputs inID);
void CLB_disableSynchronization(CLB_TILE tile, CLB_Inputs inID);
void CLB_configGPInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_GPInputMux gpMuxCfg);
void CLB_setGPREG(CLB_TILE tile, uint32_t gpRegVal);
uint32_t CLB_getGPREG(CLB_TILE tile);
void CLB_configLocalInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_LocalInputMux localMuxCfg);
void CLB_configGlobalInputMux(CLB_TILE tile, CLB_Inputs inID, CLB_GlobalInputMux globalMuxCfg);
void CLB_setOutputMask(CLB_TILE tile, uint32_t outputMask, bool enable);
uint16_t CLB_getInterruptTag(CLB_TILE tile);
void CLB_clearInterruptTag(CLB_TILE tile);
void CLB_selectLUT4Inputs(CLB_TILE tile, uint32_t lut4In0, uint32_t lut4In1, uint32_t lut4In2, uint32_t lut4In3);
void CLB_configLUT4Function(CLB_TILE tile, uint32_t lut4Fn10, uint32_t lut4Fn2);
void CLB_selectFSMInputs(CLB_TILE tile, uint32_t external0, uint32_t external1, uint32_t extra0, uint32_t extra1);
void CLB_configFSMLUTFunction(CLB_TILE tile, uint32_t fsmLutFn10, uint32_t fsmLutFn2);
void CLB_configFSMNextState(CLB_TILE tile, uint32_t nextState0, uint32_t nextState1, uint32_t nextState2);
void CLB_selectCounterInputs(CLB_TILE tile, uint32_t reset, uint32_t event, uint32_t mode0, uint32_t mode1);
void CLB_configMiscCtrlModes(CLB_TILE tile, uint32_t miscCtrl);
void CLB_configOutputLUT(CLB_TILE tile, CLB_Outputs outID, uint32_t outputCfg);
void CLB_configHLCEventSelect(CLB_TILE tile, uint32_t eventSel);
void CLB_programHLCInstruction(CLB_TILE tile, uint32_t instructionNum, uint32_t instruction);
void CLB_setHLCRegisters(CLB_TILE tile, uint32_t r0Init, uint32_t r1Init, uint32_t r2Init, uint32_t r3Init);
uint32_t CLB_getRegister(CLB_TILE tile, CLB_Register registerID);
uint32_t CLB_getOutputStatus(CLB_TILE tile);
void CLB_enablePipelineMode(CLB_TILE tile);
void CLB_disablePipelineMode(CLB_TILE tile);
void CLB_disableOutputMaskUpdates(CLB_TILE tile);
void CLB_enableOutputMaskUpdates(CLB_TILE tile);
void CLB_enableInputPipelineMode(CLB_TILE tile, CLB_Inputs inID);
void CLB_disableInputPipelineMode(CLB_TILE tile, CLB_Inputs inID);
void CLB_disableSPIBufferAccess(CLB_TILE tile);
void CLB_enableSPIBufferAccess(CLB_TILE tile);
void CLB_configSPIBufferLoadSignal(CLB_TILE tile, uint16_t eventSel);
void CLB_configSPIBufferShift(CLB_TILE tile, uint16_t shiftVal);
void CLB_configCounterLoadMatch(CLB_TILE tile, CLB_Counters counterID, uint32_t load, uint32_t match1, uint32_t match2);
void CLB_clearFIFOs(CLB_TILE tile);
void CLB_writeFIFOs(CLB_TILE tile, const uint32_t pullData[]);
void CLB_readFIFOs(CLB_TILE tile, uint32_t pushData[]);

typedef enum
{
    CSB_ALWAYS_0,
    CSB_COUNTER_0_MATCH2,
    CSB_COUNTER_0_ZERO,
    CSB_COUNTER_0_MATCH1,
    CSB_FSM_0_STATE_BIT_0,
    CSB_FSM_0_STATE_BIT_1,
    CSB_FSM_0_LUT_OUTPUT,
    CSB_LUT4_0_OUTPUT,
    CSB_ALWAYS_1,
    CSB_COUNTER_1_MATCH2,
    CSB_COUNTER_1_ZERO,
    CSB_COUNTER_1_MATCH1,
    CSB_FSM_1_STATE_BIT_0,
    CSB_FSM_1_STATE_BIT_1,
    CSB_FSM_1_LUT_OUTPUT,
    CSB_LUT4_1_OUTPUT,
    CSB_ALWAYS_CHAR_0,
    CSB_COUNTER_2_MATCH2,
    CSB_COUNTER_2_ZERO,
    CSB_COUNTER_2_MATCH1,
    CSB_FSM_2_STATE_BIT_0,
    CSB_FSM_2_STATE_BIT_1,
    CSB_FSM_2_LUT_OUTPUT,
    CSB_LUT4_2_OUTPUT,
    CSB_EXTERNAL_INPUT_0,
    CSB_EXTERNAL_INPUT_1,
    CSB_EXTERNAL_INPUT_2,
    CSB_EXTERNAL_INPUT_3,
    CSB_EXTERNAL_INPUT_4,
    CSB_EXTERNAL_INPUT_5,
    CSB_EXTERNAL_INPUT_6,
    CSB_EXTERNAL_INPUT_7
} CSB_Sel;

typedef enum
{
    HLC_OPCODE_R0,
    HLC_OPCODE_R1,
    HLC_OPCODE_R2,
    HLC_OPCODE_R3,
    HLC_OPCODE_C0,
    HLC_OPCODE_C1,
    HLC_OPCODE_C2
} HLC_Reg;

typedef enum
{
    HLC_OPCODE_MOV,
    HLC_OPCODE_MOV_T1,
    HLC_OPCODE_MOV_T2,
    HLC_OPCODE_PUSH,
    HLC_OPCODE_PULL,
    HLC_OPCODE_ADD,
    HLC_OPCODE_SUB,
    HLC_OPCODE_INTR
} HLC_Opcode;

void CLB_disableLock(void);

uint32_t CLB_getInputLUT0(CSB_Sel A, CSB_Sel B, CSB_Sel C);
uint32_t CLB_getInputLUT1(CSB_Sel A, CSB_Sel B, CSB_Sel C);
uint32_t CLB_getInputLUT2(CSB_Sel A, CSB_Sel B, CSB_Sel C);
uint32_t CLB_getInputLUT3(CSB_Sel A, CSB_Sel B, CSB_Sel C);
uint32_t CLB_getOuputLUT(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3, uint8_t func);
uint32_t CLB_config3CSB(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3);
uint32_t CLB_config4CSB(CSB_Sel in1, CSB_Sel in2, CSB_Sel in3, CSB_Sel in4);
uint32_t CLB_getHLCInst(bool isLastInstr, HLC_Opcode opcode, HLC_Reg src, HLC_Reg des);

// 输出3路LUT        BCD码       逻辑式满足则该BIT置1，例如
// 10进制       2路  1路   0路     i0 & i1 & i2     (i0 & i1) | (!i0 & i2)
// 0            0     0    0           0                    0
// 1            0     0    1           0                    0
// 2            0     1    0           0                    0
// 3            0     1    1           0                    1
// 4            1     0    0           0                    1
// 5            1     0    1           0                    0
// 6            1     1    0           0                    1
// 7            1     1    1           1                    1
//                                    0x80                  0xE8

//     输入4路LUT BCD码                逻辑式满足则该BIT置1，例如
// 10进制    3路    2路    1路    0路    !i0 & !i1 & !i2 & !i3    i0 & i1 & i2 & i3    (i0 | i1) & (i2 & i3)    !i0 & !i1 &!i2
// & i3
// 0          0      0      0      0              1                 0                             0                    0
// 1          0      0      0      1              0                 0                             0                    0
// 2          0      0      1      0              0                 0                             0                    0
// 3          0      0      1      1              0                 0                             0                    0
// 4          0      1      0      0              0                 0                             0                    0
// 5          0      1      0      1              0                 0                             0                    0
// 6          0      1      1      0              0                 0                             0                    0
// 7          0      1      1      1              0                 0                             0                    0
// 8          1      0      0      0              0                 0                             0                    0
// 9          1      0      0      1              0                 0                             0                    1
// 10         1      0      1      0              0                 0                             0                    0
// 11         1      0      1      1              0                 0                             0                    0
// 12         1      1      0      0              0                 0                             0                    0
// 13         1      1      0      1              0                 0                             1                    0
// 14         1      1      1      0              0                 0                             1                    0
// 15         1      1      1      1              0                 1                             1                    0
//                                          0x0001                0x8000                     0xe000
//                0x0100

//                  状态机 FSM
// 10进制        e1        e0        s1        s0          (~s0 & e0) | (s0 & (~e1))   (s0 ^ e1) & (!e0)
// 0             0         0         0         0                      0                         0
// 1             0         0         0         1                      1                         1
// 2             0         0         1         0                      0                         0
// 3             0         0         1         1                      1                         1
// 4             0         1         0         0                      1                         0
// 5             0         1         0         1                      1                         0
// 6             0         1         1         0                      1                         0
// 7             0         1         1         1                      1                         0
// 8             1         0         0         0                      0                         0
// 9             1         0         0         1                      0                         1
// 10            1         0         1         0                      0                         0
// 11            1         0         1         1                      0                         1
// 12            1         1         0         0                      1                         0
// 13            1         1         0         1                      0                         0
// 14            1         1         1         0                      1                         0
// 15            1         1         1         1                      0                         0
//                                                                 0x50fa                      0x50a
//                   FSM LUT
// 10进制        e1        e0       ex1       ex0           ((i2 & i0) | i1) | (((i0 & i1) | (!i0 & !i1)) & i3)    (xe0 |
// e1) | (!xe0 | e0)
// 0             0         0         0         0                      0
//                                                    0
// 1             0         0         0         1                      0
//                                                    0
// 2             0         0         1         0                      1
//                                                    0
// 3             0         0         1         1                      1
//                                                    0
// 4             0         1         0         0                      0
//                                                    0
// 5             0         1         0         1                      1
//                                                    0
// 6             0         1         1         0                      1
//                                                    0
// 7             0         1         1         1                      1
//                                                    0
// 8             1         0         0         0                      1
//                                                    0
// 9             1         0         0         1                      0
//                                                    1
// 10            1         0         1         0                      1
//                                                    1
// 11            1         0         1         1                      1
//                                                    1
// 12            1         1         0         0                      1
//                                                    0
// 13            1         1         0         1                      1
//                                                    1
// 14            1         1         1         0                      1
//                                                    1
// 15            1         1         1         1                      1
//                                                    1
//                                                                 0xfdec
//                                                  0xee00



//*****************************************************************************
//
// Close the Doxygen group.
//! @}
//
//*****************************************************************************

//*****************************************************************************
//
// Mark the end of the C bindings section for C++ compilers.
//
//*****************************************************************************

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif /* __ET6x_CLB_H */
