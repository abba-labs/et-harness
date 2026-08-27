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

#ifndef __ET6x_MISC_H
#define __ET6x_MISC_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup MISC
 * @{
 */

/**
 * @brief  SRAM bank ECC configuration structure.
 */
typedef struct
{
    ControlStatus brespEccEn;
    ControlStatus rrespEccEn;
    ControlStatus EccErrCorrectionEn;
} MISC_SRAM_Config_Typedef;

/**
 * @brief  SRAM bank ECC counter type.
 */
typedef enum
{
    MISC_SRAM_BANK_1BIT_ERR_CNT,
    MISC_SRAM_BANK_2BIT_ERR_CNT,
    MISC_SRAM_BANK_CORRECT_CNT,
    MISC_SRAM_BANK_CORRECT_ABONDON_CNT
} MISC_SRAM_CntType_Typedef;

typedef enum
{
    MISC_SRAM_BANK0,
    MISC_SRAM_BANK1,
} MISC_SRAM_Bank_Typedef;

void MISC_SRAM_ECC_Enable(SRAMCTL_Type *SRAMx);
void MISC_SRAM_ECC_Disable(SRAMCTL_Type *SRAMx);
void MISC_SRAM_ECC_Config(SRAMCTL_Type *SRAMx, MISC_SRAM_Config_Typedef *config);
void MISC_SRAM_ECC_errInject(SRAMCTL_Type *SRAMx);
void MISC_SRAM_LP_Enable(SRAMCTL_Type *SRAMx);
void MISC_SRAM_LP_Disable(SRAMCTL_Type *SRAMx);
uint32_t MISC_SRAM_ECC_GetStatus(SRAMCTL_Type *SRAMx);
void MISC_SRAM_ECC_ClearStatus(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, uint32_t clearMasks);
uint32_t MISC_SRAM_ECC1BIT_GetErrAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank);
uint32_t MISC_SRAM_ECC2BIT_GetErrAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank);
uint32_t MISC_SRAM_ECC1BIT_CorrectionAddress(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank);
uint8_t MISC_SRAM_ECC_GetErrCnt(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, MISC_SRAM_CntType_Typedef type);
void MISC_SRAM_ECC1BIT_SetThreshold(SRAMCTL_Type *SRAMx, MISC_SRAM_Bank_Typedef bank, uint8_t threshold);
void MISC_ITEnable(SRAMCTL_Type *SRAMx, uint32_t ITmasks);
void MISC_ITDisable(SRAMCTL_Type *SRAMx, uint32_t ITmasks);
void MISC_ITClear(SRAMCTL_Type *SRAMx, uint32_t ITmasks);
uint32_t MISC_GetITRawStatus(SRAMCTL_Type *SRAMx);
uint32_t MISC_GetITStatus(SRAMCTL_Type *SRAMx);
void MISC_ITMask(SRAMCTL_Type *SRAMx, uint32_t ITmasks);
void MISC_ITUnmask(SRAMCTL_Type *SRAMx, uint32_t ITmasks);

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif

#endif  /* __ET6x_MISC_H */
