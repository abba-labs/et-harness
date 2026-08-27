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
#ifndef __ET6X_FLASH_H
#define __ET6X_FLASH_H

#ifdef __cplusplus
extern "C" {
#endif

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup FLASH
 * @{
 */
/* Includes ------------------------------------------------------------------*/
#include "et6x.h"

#define PFLASH0_START_ADDR                 (0x08000000UL)
#define DFLASH_START_ADDR                  (0x10000000UL)
#define PFLASH_SIZE                        (0x200000U)
#define PFLASH_SEC_NUM                     (1024UL)
#define DFLASH_SEC_NUM                     (128UL)
#define DFLASH_NVR_SEC_NUM                 (13UL)
#define FLASH_SECTOR_SIZE                  (0x800UL)
#define DFLASH_SECTOR_SIZE                 (0x400UL)
#define FLASH_ALIGN_SIZE                   (8UL)

/**
 * @brief EFC interrupt bit mask define
 *
 */
#define FLASH_IT_ERASE_DONE_MASK           0x00000001
#define FLASH_IT_RETRY_ERASE_DONE_MASK     0x00000002
#define FLASH_IT_VREAD_DONE_MASK           0x00000004
#define FLASH_IT_NVR_WR_DONE_MASK          0x00000008
#define FLASH_IT_WRP_ERR_MASK              0x00000010
#define FLASH_IT_PGS_ERR_MASK              0x00000020
#define FLASH_IT_RDP_ERR_MASK              0x00000040
#define FLASH_IT_STRB_ERR_MASK             0x00000080
#define FLASH_IT_INC_ERR_MASK              0x00000100
#define FLASH_IT_NVR_ECC_1BIT_ERR_MASK     0x00000200
#define FLASH_IT_NVR_ECC_2BIT_ERR_MASK     0x00000400
#define FLASH_IT_MAIN_ECC_1BIT_ERR_MASK    0x00000800
#define FLASH_IT_MAIN_ECC_2BIT_ERR_MASK    0x00001000
#define FLASH_IT_VREAD0_ERR_MASK           0x00002000
#define FLASH_IT_BOOT_TIMEOUT_MASK         0x00004000
#define FLASH_IT_GATING_APB_ERR_MASK       0x00008000
#define FLASH_IT_RST_APB_ERR_MASK          0x00010000
#define FLASH_IT_GATING_AXI_ERR_MASK       0x00020000
#define FLASH_IT_RST_AXI_ERR_MASK          0x00040000
#define FLASH_IT_AXIM_CMD_ERR_MASK         0x00080000
#define FLASH_IT_VREAD1_ERR_MASK           0x00100000
#define FLASH_IT_SETCFG_FAIL_MASK          0x00200000

/**
 * @brief EFC event status define
 *
 */
#define FLASH_DW_ERR_STATUS                0x00400000
#define FLASH_OPTION_READY_STATUS          0x00800000
#define FLASH_BANK_SWAP_STATUS             0x01000000


/**
 * @brief Flash zone type. DFLASH have two zones
 *
 */
typedef enum
{
    FLASH_ZONE_MAIN,
    FLASH_ZONE_NVR,
    FLASH_ZONE_NVR_CFG
} FLASH_Zone;

/**
 * @brief  Flash RDN sector Number. Each Flash has 2 redundant sectors
 */
typedef enum
{
    FLASH_SECTOR_RDN_IDX0,
    FLASH_SECTOR_RDN_IDX1
} FLASH_SectorRDNIdx;

/**
 * @brief  FLASH ECC error type
 */
typedef enum
{
    FLASH_ECC_1BIT_ERROR,
    FLASH_ECC_2BIT_ERROR,
    FLASH_ECC_MULT_BIT_ERROR
} FLASH_ECCErrorType;

/**
 * @brief  FLASH ECC Inject Init Struct
 */
typedef struct
{
    FLASH_Zone         sectorType;    /* ecc error inject sector type  */
    FLASH_ECCErrorType errorType;     /* ecc error type */
    uint16_t           eccInjectAddr; /* ecc error inject address, 8bytes align  */
} FLASH_ECCConfigParams;


DRV_Status FLASH_unlockRegister(FLASH_Type *FLASHx);
DRV_Status FLASH_lockRegister(FLASH_Type *FLASHx);

DRV_Status FLASH_enableWriteProtect(FLASH_Type *FLASHx);
DRV_Status FLASH_disableWriteProtect(FLASH_Type *FLASHx);

bool FLASH_isBusy(FLASH_Type *FLASHx);
DRV_Status FLASH_eraseChip(FLASH_Type *FLASHx);
DRV_Status FLASH_eraseSector(FLASH_Type *FLASHx, uint32_t sectorNum, bool retry);
DRV_Status FLASH_eraseBlock(FLASH_Type *FLASHx, uint32_t blockNum, bool retry);
DRV_Status FLASH_programming(FLASH_Type *FLASHx, uint64_t *addr, uint64_t *data, uint32_t len);

bool FLASH_isSectorBlank(FLASH_Type *FLASHx, uint32_t sectorNum);

/*Flash Redundancy status get and set */
bool FLASH_getRedundancySectorStatus(FLASH_Type *FLASHx, FLASH_SectorRDNIdx index, uint32_t *sectorNum);
DRV_Status FLASH_setRedundancySector(FLASH_Type *FLASHx, FLASH_SectorRDNIdx index, uint32_t sectorNum);

/* flash interrupt */
void FLASH_enableCache(FLASH_Type *FLASHx);
void FLASH_disableCache(FLASH_Type *FLASHx);
void FLASH_enableInterrupt(FLASH_Type *FLASHx, uint32_t ITmask);
void FLASH_disableInterrupt(FLASH_Type *FLASHx, uint32_t ITmask);
void FLASH_setInterruptMask(FLASH_Type *FLASHx, uint32_t ITmask);
void FLASH_clearInterruptStatus(FLASH_Type *FLASHx, uint32_t ITmask);
void FLASH_clearInterruptMask(FLASH_Type *FLASHx, uint32_t ITmask);
uint32_t FLASH_getInterruptStatus(FLASH_Type *FLASHx);

/* dflash nvr zone sector operation */
DRV_Status FLASH_unlockNVRRegister(FLASH_Type *FLASHx);
DRV_Status FLASH_lockNVRRegister(FLASH_Type *FLASHx);
DRV_Status FLASH_eraseNVRSector(uint32_t sectorNum, bool retry);
DRV_Status FLASH_programmingNVRSector(uint32_t addr, uint64_t *data, uint32_t len);
DRV_Status FLASH_readNVRSector(uint32_t addr, uint64_t *data, uint32_t len);

/* flash ECC operation  */
void FLASH_enableECC(FLASH_Type *FLASHx, FLASH_Zone area);
void FLASH_disableECC(FLASH_Type *FLASHx, FLASH_Zone area);
void FLASH_enableECCTest(FLASH_Type *FLASHx, FLASH_ECCConfigParams *eccErrorInit);
void FLASH_disableECCTest(FLASH_Type *FLASHx);

/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif

#endif /* __ET6X_EFLASH_H */
