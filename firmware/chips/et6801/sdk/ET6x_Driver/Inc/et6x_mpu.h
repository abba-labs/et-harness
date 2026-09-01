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
#ifndef __ET6X_MPU_H
#define __ET6X_MPU_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "et6x.h"

/** @addtogroup ET6003_Driver
 * @{
 */

/** @addtogroup MPU
 * @{
 */

/*  ==============================================================================
 ##### MPU Operation #####
 #####============================================================================== */
#define MPU_REGION_NUMBER0                (0x00U)        /* MPU region number 0 */
#define MPU_REGION_NUMBER1                (0x01U)        /* MPU region number 1 */
#define MPU_REGION_NUMBER2                (0x02U)        /* MPU region number 2 */
#define MPU_REGION_NUMBER3                (0x03U)        /* MPU region number 3 */
#define MPU_REGION_NUMBER4                (0x04U)        /* MPU region number 4 */
#define MPU_REGION_NUMBER5                (0x05U)        /* MPU region number 5 */
#define MPU_REGION_NUMBER6                (0x06U)        /* MPU region number 6 */
#define MPU_REGION_NUMBER7                (0x07U)        /* MPU region number 7 */
#define MPU_REGION_NUMBER8                (0x08U)        /* MPU region number 8 */
#define MPU_REGION_NUMBER9                (0x09U)        /* MPU region number 9 */
#define MPU_REGION_NUMBER10               (0x0AU)        /* MPU region number 10 */
#define MPU_REGION_NUMBER11               (0x0BU)        /* MPU region number 11 */
#define MPU_REGION_NUMBER12               (0x0CU)        /* MPU region number 12 */
#define MPU_REGION_NUMBER13               (0x0DU)        /* MPU region number 13 */
#define MPU_REGION_NUMBER14               (0x0EU)        /* MPU region number 14 */
#define MPU_REGION_NUMBER15               (0x0FU)        /* MPU region number 15 */


#define MPU_REGION_SIZE_32B               ARM_MPU_REGION_SIZE_32B   /* MPU region size is 32 bytes */
#define MPU_REGION_SIZE_64B               ARM_MPU_REGION_SIZE_64B   /* MPU region size is 64 bytes */
#define MPU_REGION_SIZE_128B              ARM_MPU_REGION_SIZE_128B  /* MPU region size is 128 bytes */
#define MPU_REGION_SIZE_256B              ARM_MPU_REGION_SIZE_256B  /* MPU region size is 256 bytes */
#define MPU_REGION_SIZE_512B              ARM_MPU_REGION_SIZE_512B  /* MPU region size is 512 bytes */
#define MPU_REGION_SIZE_1KB               ARM_MPU_REGION_SIZE_1KB   /* MPU region size is 1K bytes */
#define MPU_REGION_SIZE_2KB               ARM_MPU_REGION_SIZE_2KB   /* MPU region size is 2K bytes */
#define MPU_REGION_SIZE_4KB               ARM_MPU_REGION_SIZE_4KB   /* MPU region size is 4K bytes */
#define MPU_REGION_SIZE_8KB               ARM_MPU_REGION_SIZE_8KB   /* MPU region size is 8K bytes */
#define MPU_REGION_SIZE_16KB              ARM_MPU_REGION_SIZE_16KB  /* MPU region size is 16K bytes */
#define MPU_REGION_SIZE_32KB              ARM_MPU_REGION_SIZE_32KB  /* MPU region size is 32K bytes */
#define MPU_REGION_SIZE_64KB              ARM_MPU_REGION_SIZE_64KB  /* MPU region size is 64K bytes */
#define MPU_REGION_SIZE_128KB             ARM_MPU_REGION_SIZE_128KB /* MPU region size is 128K bytes */
#define MPU_REGION_SIZE_256KB             ARM_MPU_REGION_SIZE_256KB /* MPU region size is 256K bytes */
#define MPU_REGION_SIZE_512KB             ARM_MPU_REGION_SIZE_512KB /* MPU region size is 512K bytes */
#define MPU_REGION_SIZE_1MB               ARM_MPU_REGION_SIZE_1MB   /* MPU region size is 1M bytes */
#define MPU_REGION_SIZE_2MB               ARM_MPU_REGION_SIZE_2MB   /* MPU region size is 2M bytes */
#define MPU_REGION_SIZE_4MB               ARM_MPU_REGION_SIZE_4MB   /* MPU region size is 4M bytes */
#define MPU_REGION_SIZE_8MB               ARM_MPU_REGION_SIZE_8MB   /* MPU region size is 8M bytes */
#define MPU_REGION_SIZE_16MB              ARM_MPU_REGION_SIZE_16MB  /* MPU region size is 16M bytes */
#define MPU_REGION_SIZE_32MB              ARM_MPU_REGION_SIZE_32MB  /* MPU region size is 32M bytes */
#define MPU_REGION_SIZE_64MB              ARM_MPU_REGION_SIZE_64MB  /* MPU region size is 64M bytes */
#define MPU_REGION_SIZE_128MB             ARM_MPU_REGION_SIZE_128MB /* MPU region size is 128M bytes */
#define MPU_REGION_SIZE_256MB             ARM_MPU_REGION_SIZE_256MB /* MPU region size is 256M bytes */
#define MPU_REGION_SIZE_512MB             ARM_MPU_REGION_SIZE_512MB /* MPU region size is 512M bytes */
#define MPU_REGION_SIZE_1GB               ARM_MPU_REGION_SIZE_1GB   /* MPU region size is 1G bytes */
#define MPU_REGION_SIZE_2GB               ARM_MPU_REGION_SIZE_2GB   /* MPU region size is 2G bytes */
#define MPU_REGION_SIZE_4GB               ARM_MPU_REGION_SIZE_4GB   /* MPU region size is 4G bytes */


#define MPU_AP_NO_ACCESS                  ARM_MPU_AP_NONE                                   /* MPU access permission no
                                                                                             * access */
#define MPU_AP_PRIV_RW                    ARM_MPU_AP_PRIV                                   /* MPU access permission
                                                                                             * privileged access only */
#define MPU_AP_PRIV_RW_UNPRIV_RO          ARM_MPU_AP_URO                                    /* MPU access permission
                                                                                             * unprivileged access
                                                                                             * read-only */
#define MPU_AP_FULL_ACCESS                ARM_MPU_AP_FULL                                   /* MPU access permission
                                                                                             * full access */
#define MPU_AP_PRIV_RO                    ARM_MPU_AP_PRO                                    /* MPU access permission
                                                                                             * privileged access
                                                                                             * read-only */
#define MPU_AP_PRIV_UNPRIV_RO             ARM_MPU_AP_RO                                     /* MPU access permission
                                                                                             * privileged and
                                                                                             * unprivileged read-only
                                                                                             * access */

#define MPU_TEX_TYPE0                     (0x00U)                                           /* MPU TEX type 0 */
#define MPU_TEX_TYPE1                     (0x01U)                                           /* MPU TEX type 1 */
#define MPU_TEX_TYPE2                     (0x02U)                                           /* MPU TEX type 2 */

#define MPU_MODE_HFNMI_PRIVDEF_NONE       (0x00000000U)                                     /* HFNMIENA and PRIVDEFENA
                                                                                             * are 0 */
#define MPU_MODE_HARDFAULT_NMI            MPU_CTRL_HFNMIENA_Msk                             /* use the MPU for memory
                                                                                             * accesses by HardFault and
                                                                                             * NMI handlers only */
#define MPU_MODE_PRIV_DEFAULT             MPU_CTRL_PRIVDEFENA_Msk                           /* enables the default
                                                                                             * memory map as a
                                                                                             * background region for
                                                                                             * privileged access only */
#define MPU_MODE_HFNMI_PRIVDEF            (MPU_CTRL_HFNMIENA_Msk | MPU_CTRL_PRIVDEFENA_Msk) /* HFNMIENA and PRIVDEFENA
                                                                                             * are 1 */

#define MPU_INSTRUCTION_ACCESS_ENABLE     (0x00U)
#define MPU_INSTRUCTION_ACCESS_DISABLE    (0x01U)

#define MPU_ACCESS_SHAREABLE              (0x01U)
#define MPU_ACCESS_NOT_SHAREABLE          (0x00U)

#define MPU_ACCESS_CACHEABLE              (0x01U)
#define MPU_ACCESS_NOT_CACHEABLE          (0x00U)

#define MPU_ACCESS_BUFFERABLE             (0x01U)
#define MPU_ACCESS_NOT_BUFFERABLE         (0x00U)

typedef struct __PACKED
{
    uint8_t  regionNumber;      /* region number */
    uint32_t regionBaseAddress; /* region base address */
    uint8_t  disableExec;       /* Instruction access disable bit, 1= disable instruction fetches. */
    uint8_t  accessPermission;  /* Data access permissions, allows you to configure read/write access for User and
                                 * Privileged mode. */
    uint8_t  typeExtField;      /* Type extension field, allows you to configure memory access type, for example
                                 * strongly ordered, peripheral. */
    uint8_t  isShareable;       /* Region is shareable between multiple bus masters. */
    uint8_t  isCacheable;       /* Region is cacheable, i.e. its value may be kept in cache. */
    uint8_t  isBufferable;      /* Region is bufferable, i.e. using write-back caching. Cacheable but non-bufferable
                                 * regions use write-through policy. */
    uint8_t  subRegionDisable;  /* Sub-region disable field. */
    uint32_t regionSize;        /* Region size of the region to be configured, for example 4K, 8K. */
} MPU_REGION_InitTypeDef;

void MPU_REGION_Init(const MPU_REGION_InitTypeDef *init);
void MPU_REGION_StructInit(MPU_REGION_InitTypeDef *init);
void MPU_Enable(uint32_t MPU_Control);
void MPU_Disable(void);

/**
 * @}
 */

/**
 * @}
 */


#ifdef __cplusplus
}
#endif

#endif /* __ET6X_MPU_H */
