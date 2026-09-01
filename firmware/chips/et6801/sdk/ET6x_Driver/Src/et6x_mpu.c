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
#include "et6x_mpu.h"

/**
 * @addtogroup ET3101_Driver
 * @{
 */

/**
 * @defgroup MPU MPU
 * @brief Memory Protect unit Driver Library
 * @{
 */

/*! Parameter validity check for MPU region number */
#define IS_MPU_REGION_NUMBER(num)           ((num) <= MPU_REGION_NUMBER15)

/*! Parameter validity check for MPU base address number */
#define IS_MPU_REGION_BASE_ADDRESS(addr)    (((addr) & 0xF) == 0)

/*! Parameter validity check for MPU access */
#define IS_MPU_REGION_ACCESS(access) \
        (((access) == MPU_AP_NO_ACCESS) ||         \
         ((access) == MPU_AP_PRIV_RW) ||           \
         ((access) == MPU_AP_PRIV_RW_UNPRIV_RO) || \
         ((access) == MPU_AP_FULL_ACCESS) ||       \
         ((access) == MPU_AP_PRIV_RO) ||           \
         ((access) == MPU_AP_PRIV_UNPRIV_RO))

/*! Parameter validity check for MPU type extension field */
#define IS_MPU_REGION_TYPE_EXTENSION_FIELD(field) \
        (((field) == MPU_TEX_TYPE0) || \
         ((field) == MPU_TEX_TYPE1) || \
         ((field) == MPU_TEX_TYPE2))

/*! Parameter validity check for MPU region size */
#define IS_MPU_REGION_TYPE_REGION_SIZE(size) \
        (((size) == MPU_REGION_SIZE_32B) ||   \
         ((size) == MPU_REGION_SIZE_64B) ||   \
         ((size) == MPU_REGION_SIZE_128B) ||  \
         ((size) == MPU_REGION_SIZE_256B) ||  \
         ((size) == MPU_REGION_SIZE_512B) ||  \
         ((size) == MPU_REGION_SIZE_1KB) ||   \
         ((size) == MPU_REGION_SIZE_2KB) ||   \
         ((size) == MPU_REGION_SIZE_4KB) ||   \
         ((size) == MPU_REGION_SIZE_8KB) ||   \
         ((size) == MPU_REGION_SIZE_16KB) ||  \
         ((size) == MPU_REGION_SIZE_32KB) ||  \
         ((size) == MPU_REGION_SIZE_64KB) ||  \
         ((size) == MPU_REGION_SIZE_128KB) || \
         ((size) == MPU_REGION_SIZE_256KB) || \
         ((size) == MPU_REGION_SIZE_512KB) || \
         ((size) == MPU_REGION_SIZE_1MB) ||   \
         ((size) == MPU_REGION_SIZE_2MB) ||   \
         ((size) == MPU_REGION_SIZE_4MB) ||   \
         ((size) == MPU_REGION_SIZE_8MB) ||   \
         ((size) == MPU_REGION_SIZE_16MB) ||  \
         ((size) == MPU_REGION_SIZE_32MB) ||  \
         ((size) == MPU_REGION_SIZE_64MB) ||  \
         ((size) == MPU_REGION_SIZE_128MB) || \
         ((size) == MPU_REGION_SIZE_256MB) || \
         ((size) == MPU_REGION_SIZE_512MB) || \
         ((size) == MPU_REGION_SIZE_1GB) ||   \
         ((size) == MPU_REGION_SIZE_2GB) ||   \
         ((size) == MPU_REGION_SIZE_4GB))

/*! Parameter validity check for MPU region mode */
#define IS_MPU_REGION_CONTROL_MODE(mode) \
        (((mode) == MPU_MODE_HFNMI_PRIVDEF_NONE) || \
         ((mode) == MPU_MODE_HARDFAULT_NMI) ||      \
         ((mode) == MPU_MODE_PRIV_DEFAULT) ||       \
         ((mode) == MPU_MODE_HFNMI_PRIVDEF))

/*! Parameter validity check for MPU instruction access state */
#define IS_MPU_INSTRUCTION_ACCESS(state) \
        (((state) == MPU_INSTRUCTION_ACCESS_ENABLE) || \
         ((state) == MPU_INSTRUCTION_ACCESS_DISABLE))

/*! Parameter validity check for MPU shareable access state */
#define IS_MPU_ACCESS_SHAREABLE(state) \
        (((state) == MPU_ACCESS_SHAREABLE) || \
         ((state) == MPU_ACCESS_NOT_SHAREABLE))

/*! Parameter validity check for MPU cacheable access state */
#define IS_MPU_ACCESS_CACHEABLE(state) \
        (((state) == MPU_ACCESS_CACHEABLE) || \
         ((state) == MPU_ACCESS_NOT_CACHEABLE))

/*! Parameter validity check for MPU bufferable access state */
#define IS_MPU_ACCESS_BUFFERABLE(state) \
        (((state) == MPU_ACCESS_BUFFERABLE) || \
         ((state) == MPU_ACCESS_NOT_BUFFERABLE))

#define IS_MPU_SUB_REGION_DISABLE(subregion)    ((subregion) < 0x00FFU)

/**
 * @brief setup a new mpu region
 *
 * @param init pointer to initial paramters
 */
void MPU_REGION_Init(const MPU_REGION_InitTypeDef *init)
{
    uint32_t rbar;
    uint32_t rasr;

    assert_param(IS_MPU_REGION_NUMBER(init->regionNumber));
    assert_param(IS_MPU_REGION_BASE_ADDRESS(init->regionBaseAddress));
    assert_param(IS_MPU_REGION_ACCESS(init->accessPermission));
    assert_param(IS_MPU_REGION_TYPE_EXTENSION_FIELD(init->typeExtField));
    assert_param(IS_MPU_REGION_TYPE_REGION_SIZE(init->regionSize));
    assert_param(IS_MPU_INSTRUCTION_ACCESS(init->disableExec));
    assert_param(IS_MPU_ACCESS_SHAREABLE(init->isShareable));
    assert_param(IS_MPU_ACCESS_CACHEABLE(init->isCacheable));
    assert_param(IS_MPU_ACCESS_BUFFERABLE(init->isBufferable));
    assert_param(IS_MPU_SUB_REGION_DISABLE(init->subRegionDisable));


    rbar = ARM_MPU_RBAR(init->regionNumber, init->regionBaseAddress);
    rasr = ARM_MPU_RASR(init->disableExec,
                        init->accessPermission,
                        init->typeExtField,
                        init->isShareable,
                        init->isCacheable,
                        init->isBufferable,
                        init->subRegionDisable,
                        init->regionSize);
    ARM_MPU_SetRegion(rbar, rasr);
}

/**
 * @brief Init MPU region intial structure
 *
 * @param init pointer to initial paramters
 */
void MPU_REGION_StructInit(MPU_REGION_InitTypeDef *init)
{
    init->regionNumber      = MPU_REGION_NUMBER0;
    init->regionBaseAddress = 0;
    init->disableExec       = MPU_INSTRUCTION_ACCESS_ENABLE;
    init->accessPermission  = ARM_MPU_AP_FULL;
    init->typeExtField      = MPU_TEX_TYPE0;
    init->isShareable       = MPU_ACCESS_SHAREABLE;
    init->isCacheable       = MPU_ACCESS_CACHEABLE;
    init->isBufferable      = MPU_ACCESS_BUFFERABLE;
    init->subRegionDisable  = 0;
    init->regionSize        = MPU_REGION_SIZE_32B;
}

/**
 * @brief Enable specified MPU region
 *
 * @param MPU_Control
 */
void MPU_Enable(uint32_t MPU_Control)
{
    assert_param(IS_MPU_REGION_CONTROL_MODE(MPU_Control));

    ARM_MPU_Enable(MPU_Control);
}

/**
 * @brief Disable specified MPU region
 *
 */
void MPU_Disable(void)
{
    ARM_MPU_Disable();
}

/**
 * @}
 */

/**
 * @}
 */

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
