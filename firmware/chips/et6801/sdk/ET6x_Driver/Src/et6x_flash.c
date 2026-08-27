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


#include "et6x_flash.h"

#define FLASH_MAX_TIMEOUT              (0x10000000UL)
#define FLASH_SEC_INC_SIZE             (FLASH_SECTOR_SIZE / FLASH_ALIGN_SIZE)

/* FLASH Keys */
#define PFLASH_KEY1                    0x01234567
#define PFLASH_KEY2                    0x89ABCDEF

#define DFLASH_REG_KEY1                0x0123CDEF
#define DFLASH_REG_KEY2                0x89AB4567
#define DFLASH_NVR_KEY1                0xCDEF0123
#define DFLASH_NVR_KEY2                0x456789AB

#define PFLASH_BANK_NUM                (2)
#define MAX_FLASH_REDUNDANCY_SECTOR    (2)


#define ROUND_DOWN(x, align)      ((uint32_t)(x) & ~(uint32_t)(align - 1))
#define ROUND_UP(x, align)        ((uint32_t)((uint32_t)(x) + (align - 1)) & ~(uint32_t)(align - 1))

#define IS_PFLASH_ADDR(addr)      (addr >= 0x08000000 && addr <= 0x080FFFFF)
#define IS_DFLASH_ADDR(addr)      (addr >= 0x10000000 && addr <= 0x1001FFFF)
#define IS_RDN_SECTOR_IDX(num)    (num == FLASH_SECTOR_RDN_IDX0 || num == FLASH_SECTOR_RDN_IDX1)


/*! Parameter validity check for FLASH peripheral  */
#define IS_FLASH_PERIPHERAL(x) \
        (((x) == PFLASH) ||        \
         ((x) == DFLASH))

/**
 * @brief  FLASH SUB type
 */
typedef enum
{
    FLASH_SUB_CMD_NVR_CFG,
    FLASH_SUB_CMD_NVR,
    FLASH_SUB_CMD_RDN,
    FLASH_SUB_CMD_MAIN,
    FLASH_SUB_CMD_MAIN_RDN,
    FLASH_SUB_CMD_MAIN_RDN_NVR
} FLASH_SUB_CMD_TypeDef;

/**
 * @brief  FLASH CMD type
 */
typedef enum
{
    FLASH_CMD_WRITE,
    FLASH_CMD_SEC_ERASE,
    FLASH_CMD_SEC_RETRY_ERASE,
    FLASH_CMD_BLOCK_ERASE,
    FLASH_CMD_BLOCK_RETRY_ERASE,
    FLASH_CMD_CHIP_ERASE,
    FLASH_CMD_NORMAL_READ,
    FLASH_CMD_RECALL_READ,
    FLASH_CMD_VREAD0,
    FLASH_CMD_VREAD1,
    FLASH_CMD_VREAD1_FOR_SECTOR,
    FLASH_CMD_VREAD1_FOR_BLOCK,
    FLASH_CMD_VREAD,
    FLASH_CMD_SREAD0,
    FLASH_CMD_SREAD1
} FLASH_CMD_TypeDef;


/**
 * @brief unlock flash register
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return
 */
DRV_Status FLASH_unlockRegister(FLASH_Type *FLASHx)
{
    uint32_t timeOutCount = 0;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    /* Unlock the FLASH register */
    if (READ_BIT(FLASHx->EFC_WPFLG, PFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk))
    {
        if (FLASHx == DFLASH)
        {
            WRITE_REG(FLASHx->EFC_REG_KEY1, DFLASH_REG_KEY1);
            WRITE_REG(FLASHx->EFC_REG_KEY2, DFLASH_REG_KEY2);
        }
        else
        {
            WRITE_REG(FLASHx->EFC_REG_KEY1, PFLASH_KEY1);
            WRITE_REG(FLASHx->EFC_REG_KEY2, PFLASH_KEY2);
        }

        /* wait clear */
        while (READ_BIT(FLASHx->EFC_WPFLG, PFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk))
        {
            timeOutCount++;
            if (timeOutCount >= FLASH_MAX_TIMEOUT)
            {
                return DRV_TIMEOUT;
            }
        }
    }
    MODIFY_REG(DFLASH->EFC_DFLASH_EXTEND.EFC_TIMING_PARA12, DFLASH_EFC_TIMING_PARA12_EFC_TMH_Msk, 5);
    return DRV_OK;
}

/**
 * @brief unlock nvr zone register
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return
 */
DRV_Status FLASH_unlockNVRRegister(FLASH_Type *FLASHx)
{
    uint32_t timeOutCount = 0;

    assert_param(FLASHx == DFLASH);
    /* unlock nvr write */
    if (READ_BIT(FLASHx->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_NVR_WRPROT_FLG_Msk))
    {
        /* unlock */
        WRITE_REG(FLASHx->EFC_NVR_KEY1, DFLASH_NVR_KEY1);
        WRITE_REG(FLASHx->EFC_NVR_KEY2, DFLASH_NVR_KEY2);
        /* wait clear */
        while (READ_BIT(FLASHx->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_NVR_WRPROT_FLG_Msk))
        {
            timeOutCount++;
            if (timeOutCount >= FLASH_MAX_TIMEOUT)
            {
                return DRV_TIMEOUT;
            }
        }
    }
    return DRV_OK;
}

/**
 * @brief lock nvr zone register
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return DRV_Status
 */
DRV_Status FLASH_lockNVRRegister(FLASH_Type *FLASHx)
{
    assert_param(FLASHx == DFLASH);
    /* lock nvr write */
    SET_BIT(FLASHx->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_NVR_WRPROT_FLG_Msk);
    return DRV_OK;
}

/**
 * @brief lock flash data write protect
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return DRV_Status
 */
DRV_Status FLASH_enableWriteProtect(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    /* Allow write operations to flash */
    CLEAR_BIT(FLASHx->EFC_CTRL, PFLASH_EFC_CTRL_EFC_WRITE_EN_Msk);

    return DRV_OK;
}

/**
 * @brief lock pflash register
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return DRV_Status
 */
DRV_Status FLASH_lockRegister(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));

    CLEAR_BIT(DFLASH->EFC_DFLASH_EXTEND.EFC_TIMING_PARA12, DFLASH_EFC_TIMING_PARA12_EFC_TMH_Msk);
    SET_BIT(FLASHx->EFC_WPFLG, PFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk);

    return DRV_OK;
}

/**
 * @brief unlock flash data write protect
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @return DRV_Status
 */
DRV_Status FLASH_disableWriteProtect(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));

    SET_BIT(FLASHx->EFC_CTRL, PFLASH_EFC_CTRL_EFC_WRITE_EN_Msk);

    return DRV_OK;
}

/**
 * @brief Wait for the operation to complete, and get the status when completed
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 */
bool FLASH_isBusy(FLASH_Type *FLASHx)
{
    uint32_t timeOut = 0;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    while (READ_REG(FLASHx->EFC_IND_STS) == 0)
    {
        if (timeOut > FLASH_MAX_TIMEOUT)
        {
            return true;
        }
        timeOut++;
    }

    return false;
}

/**
 * @brief Perform a chip erase,for the flash which needs to be operated
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 */
DRV_Status FLASH_eraseChip(FLASH_Type *FLASHx)
{
    uint32_t i;
    uint32_t cmd             = 0;
    uint32_t sector_replaced = 0;
    bool     status          = false;
    bool     rdn_status      = false;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));

    status = FLASH_isBusy(FLASHx);
    if (status != false)
    {
        return DRV_TIMEOUT;
    }
    /* check whether this is a redundancy sector is replaced */
    for (i = 0; i < MAX_FLASH_REDUNDANCY_SECTOR; i++)
    {
        rdn_status = FLASH_getRedundancySectorStatus(FLASHx, (FLASH_SectorRDNIdx)i, &sector_replaced);
        if (rdn_status)
        {
            break;
        }
    }

    if (!rdn_status)
    {
        SET_BIT(cmd, FLASH_SUB_CMD_MAIN << PFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    }
    else
    {
        SET_BIT(cmd, FLASH_SUB_CMD_MAIN_RDN << PFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    }

    SET_BIT(cmd, FLASH_CMD_CHIP_ERASE << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    WRITE_REG(FLASHx->EFC_IND_CMD, cmd);

    status = FLASH_isBusy(FLASHx);
    if (status)
    {
        return DRV_TIMEOUT;
    }
    return DRV_OK;
}

/**
 *
 * @brief Perform sector erase
 * @param FLASHx for the flash which needs to be operated
 * @param sectorNum sector number (0-511,when pflash; 0-127,when dflash)
 * @param retry use retry erase or not
 */
DRV_Status FLASH_eraseSector(FLASH_Type *FLASHx, uint32_t sectorNum, bool retry)
{
    uint32_t cmd  = 0;
    uint32_t addr = FLASH_SEC_INC_SIZE * sectorNum;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    if (FLASHx == DFLASH)
    {
        assert_param(sectorNum < DFLASH_SEC_NUM);
    }
    else
    {
        assert_param(sectorNum < PFLASH_SEC_NUM);
    }

    SET_BIT(cmd, FLASH_SUB_CMD_MAIN << PFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    if (retry)
    {
        SET_BIT(cmd, FLASH_CMD_SEC_RETRY_ERASE << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }
    else
    {
        SET_BIT(cmd, FLASH_CMD_SEC_ERASE << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }

    if (!FLASH_isBusy(FLASHx))
    {
        /* Set the last 16 bits to 0 and then add address */
        CLEAR_BIT(cmd, 0xFFFFUL);
        SET_BIT(cmd, addr);
        WRITE_REG(FLASHx->EFC_IND_CMD, cmd);
        if (FLASH_isBusy(FLASHx))
        {
            return DRV_TIMEOUT;
        }
    }
    return DRV_OK;
}

/**
 *
 * @brief Perform block erase
 * @param FLASHx for the flash which needs to be operated
 * @param blockNum block number (0-63,when pflash(2M); 0-3,when dflash(128K))
 * @param retry use retry erase or not
 */
DRV_Status FLASH_eraseBlock(FLASH_Type *FLASHx, uint32_t blockNum, bool retry)
{
    uint32_t cmd  = 0;
    uint32_t addr = 0;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    if (FLASHx == DFLASH)
    {
        addr = (0x8000UL / 8UL) * blockNum;
        //todo assert_param(sectorNum < DFLASH_SEC_NUM);
    }
    else
    {
        addr = (0x8000UL / 8UL) * blockNum;
        //todo assert_param(sectorNum < PFLASH_SEC_NUM);
    }

    SET_BIT(cmd, FLASH_SUB_CMD_MAIN << PFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    if (retry)
    {
        SET_BIT(cmd, FLASH_CMD_BLOCK_RETRY_ERASE << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }
    else
    {
        SET_BIT(cmd, FLASH_CMD_BLOCK_ERASE << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }

    if (!FLASH_isBusy(FLASHx))
    {
        /* Set the last 16 bits to 0 and then add address */
        CLEAR_BIT(cmd, 0xFFFFUL);
        SET_BIT(cmd, addr);
        WRITE_REG(FLASHx->EFC_IND_CMD, cmd);
        if (FLASH_isBusy(FLASHx))
        {
            return DRV_TIMEOUT;
        }
    }
    return DRV_OK;
}

/**
 * @brief Write dword to flash
 *
 * @param FLASHx          Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param addr            start address to write data, Addr must be align by 8
 * @param data            data to write to flash
 * @param len             write data length(dword),be careful not to exceed the data range in data
 * @return Operation success or fail
 *
 */
DRV_Status FLASH_programming(FLASH_Type *FLASHx, uint64_t *addr, uint64_t *data, uint32_t len)
{
    uint32_t i;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));

    if (!FLASH_isBusy(FLASHx))
    {
        for (i = 0; i < len; i++)
        {
            *(volatile uint64_t *)(addr + i) = *(data + i);
        }
        __DSB();
    }
    else
    {
        return DRV_TIMEOUT;
    }
    return DRV_OK;
}

/**
 * @brief Check whether flash sector is blank
 *
 * @param FLASHx Pointer to the FLASH peripheral.
 * @param sectorNum sector index
 * @return bool blank or not
 */
bool FLASH_isSectorBlank(FLASH_Type *FLASHx, uint32_t sectorNum)
{
    uint32_t cmd    = 0;
    uint32_t addr   = 0;
    bool     status = false;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    if (FLASHx == DFLASH)
    {
        assert_param(sectorNum < DFLASH_SEC_NUM);
    }
    else
    {
        assert_param(sectorNum < PFLASH_SEC_NUM);
    }
    addr = FLASH_SEC_INC_SIZE * sectorNum;
    /* enable interrupt report for get vread status */
    SET_BIT(FLASHx->EFC_INT_MASK, BIT_MASK(12));
    SET_BIT(FLASHx->EFC_INT_EN, BIT_MASK(12));
    SET_BIT(FLASHx->EFC_INT_CLR, BIT_MASK(12));

    SET_BIT(cmd, FLASH_SUB_CMD_MAIN << PFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    SET_BIT(cmd, FLASH_CMD_VREAD << PFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);

    if (!FLASH_isBusy(FLASHx))
    {
        /* Set the last 16 bits to 0 and then add address */
        CLEAR_BIT(cmd, 0xFFFFUL);
        SET_BIT(cmd, addr);
        WRITE_REG(FLASHx->EFC_IND_CMD, cmd);
        if (FLASH_isBusy(FLASHx))
        {
            return false;
        }
    }
    if (READ_REG(FLASHx->EFC_INT_RAW_RPT) & BIT_MASK(12))
    {
        status = false;
    }
    else
    {
        status = true;
    }
    CLEAR_BIT(FLASHx->EFC_INT_EN, BIT_MASK(12));
    CLEAR_BIT(FLASHx->EFC_INT_MASK, BIT_MASK(12));
    SET_BIT(FLASHx->EFC_INT_CLR, BIT_MASK(12));
    return status;
}

/**
 * @brief Enable cache of flash
 *
 * @param FLASHx  Pointer to the FLASH peripheral.
 *
 */
void FLASH_enableCache(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    SET_BIT(FLASHx->EFC_CACHE, PFLASH_EFC_CACHE_EFC_CACHE_EN_Msk);
}

/**
 * @brief Disable cache of flash
 *
 * @param FLASHx  Pointer to the FLASH peripheral.
 *
 */
void FLASH_disableCache(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    CLEAR_BIT(FLASHx->EFC_CACHE, PFLASH_EFC_CACHE_EFC_CACHE_EN_Msk);
}

/**
 * @brief Enable flash interrupt
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param ITmask         Interrupt type selection
 */
void FLASH_enableInterrupt(FLASH_Type *FLASHx, uint32_t ITmask)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    SET_BIT(FLASHx->EFC_INT_EN, ITmask);
}

/**
 * @brief Disable flash interrupt
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param ITmask Interrupt type selection
 */
void FLASH_disableInterrupt(FLASH_Type *FLASHx, uint32_t ITmask)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    CLEAR_BIT(FLASHx->EFC_INT_EN, ITmask);
}

/**
 * @brief mask flash interrupt
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param ITmask Interrupt type selection
 */
void FLASH_setInterruptMask(FLASH_Type *FLASHx, uint32_t ITmask)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    SET_BIT(FLASHx->EFC_INT_MASK, ITmask);
}

/**
 * @brief clear flash interrupt
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param ITmask Interrupt type selection
 */
void FLASH_clearInterruptMask(FLASH_Type *FLASHx, uint32_t ITmask)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    SET_BIT(FLASHx->EFC_INT_CLR, ITmask);
}

/**
 * @brief Get flash interrupt status
 *
 * @return uint32_t Interrupt type selection
 */
uint32_t FLASH_getInterruptStatus(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    return READ_REG(FLASHx->EFC_INT_STATUS_RPT);
}

/**
 * @brief Clear flash interrupt
 *
 * @param ITmask Interrupt type selection
 */
void FLASH_clearInterruptStatus(FLASH_Type *FLASHx, uint32_t ITmask)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    SET_BIT(FLASHx->EFC_INT_CLR, ITmask);
}

/**
 * @brief whether the rdn sector replaces unusable flash sector
 *
 * @param FLASHx controller of Corresponding pflash
 * @param index rdn sector number
 * @param sectorNum output parameter,if return value is EFC_RDN_REPLACE.
 * @return bool  false:rdn sector is not in use; true: rdn sector is in used
 */
bool FLASH_getRedundancySectorStatus(FLASH_Type *FLASHx, FLASH_SectorRDNIdx index, uint32_t *sectorNum)
{
    uint32_t enableMask    = PFLASH_EFC_RDN_EFC_RDN0_EN_Msk;
    uint32_t sectorNumMask = PFLASH_EFC_RDN_EFC_RDN0_SECNUM_Msk;
    uint32_t sectorNumPos  = PFLASH_EFC_RDN_EFC_RDN0_SECNUM_Pos;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    assert_param(IS_RDN_SECTOR_IDX(index));

    if (index == FLASH_SECTOR_RDN_IDX1)
    {
        enableMask    = PFLASH_EFC_RDN_EFC_RDN1_EN_Msk;
        sectorNumMask = PFLASH_EFC_RDN_EFC_RDN1_SECNUM_Msk;
        sectorNumPos  = PFLASH_EFC_RDN_EFC_RDN1_SECNUM_Pos;
    }

    if (READ_REG(FLASHx->EFC_RDN) & enableMask)
    {
        *sectorNum = (READ_REG(FLASHx->EFC_RDN) & sectorNumMask) >> sectorNumPos;
        return true;
    }

    return false;
}

/**
 * @brief  replace flash sector with redundancy sector
 *
 * @param FLASHx  controller of Corresponding pflash
 * @param index  the redundancy sector index (0 or 1)
 * @param sectorNum  the sector num to be replaced
 * @return DRV_Status  DRV_OK: success; DRV_ERROR: failure
 */
DRV_Status FLASH_setRedundancySector(FLASH_Type *FLASHx, FLASH_SectorRDNIdx index, uint32_t sectorNum)
{
    uint32_t msk = PFLASH_EFC_RDN_EFC_RDN0_EN_Msk;
    uint32_t sectorReplaceNum = 0;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    assert_param(IS_RDN_SECTOR_IDX(index));
    assert_param(sectorNum < (PFLASH_SEC_NUM * PFLASH_BANK_NUM));

    if (index == FLASH_SECTOR_RDN_IDX1)
    {
        msk = PFLASH_EFC_RDN_EFC_RDN1_EN_Msk;
    }

    if (FLASH_getRedundancySectorStatus(FLASHx, index, &sectorReplaceNum))
    {
        return DRV_ERROR;
    }

    SET_BIT(FLASHx->EFC_RDN, msk);

    if (index == FLASH_SECTOR_RDN_IDX1)
    {
        sectorNum = sectorNum << PFLASH_EFC_RDN_EFC_RDN1_SECNUM_Pos;
    }

    SET_BIT(FLASHx->EFC_RDN, sectorNum);

    return DRV_OK;
}

/**
 *
 * @brief Perform nvr sector erase
 * @param sectorNum sector number (0-11)
 * @param retry use retry erase or not
 *
 * @return DRV_Status  DRV_OK: success; DRV_ERROR: failure
 */
DRV_Status FLASH_eraseNVRSector(uint32_t sectorNum, bool retry)
{
    uint32_t cmd  = 0;
    uint32_t addr = FLASH_SEC_INC_SIZE * sectorNum;

    assert_param(sectorNum <= DFLASH_NVR_SEC_NUM);

    SET_BIT(cmd, FLASH_SUB_CMD_NVR << DFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    if (retry)
    {
        SET_BIT(cmd, FLASH_CMD_SEC_RETRY_ERASE << DFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }
    else
    {
        SET_BIT(cmd, FLASH_CMD_SEC_ERASE << DFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);
    }
    if (!FLASH_isBusy(DFLASH))
    {
        /* Set the last 16 bits to 0 and then add address */
        CLEAR_BIT(cmd, 0xFFFFUL);
        SET_BIT(cmd, addr);
        WRITE_REG(DFLASH->EFC_IND_CMD, cmd);
        if (FLASH_isBusy(DFLASH))
        {
            return DRV_TIMEOUT;
        }
    }
    else
    {
        return DRV_TIMEOUT;
    }
    return DRV_OK;
}

/**
 * @brief Write DoubleWord to dflash nvr sector
 *
 * @param addr            start address to write data,Address must be divisible by 8
 * @param data            data address
 * @param len             write data length(DoubleWord),be careful not to exceed the data range in dataAddr
 * @return Operation success or fail
 */
DRV_Status FLASH_programmingNVRSector(uint32_t addr, uint64_t *data, uint32_t len)
{
    uint32_t   i;
    uint32_t   cmd    = 0;
    DRV_Status status = DRV_OK;

    if ((addr % 8) != 0)
    {
        return DRV_ERROR;
    }
    {
        SET_BIT(cmd, FLASH_SUB_CMD_NVR << DFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);

        for (i = 0; i < len; i++)
        {
            if (FLASH_isBusy(DFLASH))
            {
                return DRV_TIMEOUT;
            }
            /* set last 16 bit to 0*/
            CLEAR_BIT(cmd, 0xFFFFUL);
            /* set write addr */
            SET_BIT(cmd, addr + i);

            WRITE_REG(DFLASH->EFC_IND_WD0, (uint32_t)(*(data + i)));
            WRITE_REG(DFLASH->EFC_IND_WD1, (uint32_t)((*(data + i)) >> 32));
            WRITE_REG(DFLASH->EFC_IND_CMD, cmd);
        }
    }
    return status;
}

/**
 * @brief Read DoubleWord from dflash nvr sector
 *
 * @param addr            start address to Read data,Address must be divisible by 8
 * @param data            Output parameter,which hold the data you read.
 * @param len             Read data length(DoubleWord),be careful not to exceed the data range in data
 * @return Operation success or fail
 */
DRV_Status FLASH_readNVRSector(uint32_t addr, uint64_t *data, uint32_t len)
{
    uint32_t cmd = 0;
    uint32_t i;


    cmd |= (FLASH_SUB_CMD_NVR << DFLASH_EFC_IND_CMD_EFC_INDCMD_SUBTYPE_Pos);
    cmd |= (FLASH_CMD_RECALL_READ << DFLASH_EFC_IND_CMD_EFC_INDCMD_TYPE_Pos);

    for (i = 0; i < len; i++)
    {
        /* set last 16 bit to 0*/
        cmd &= (0xFFFFU << 16);
        /* set write addr */
        cmd |= addr + i;

        if (FLASH_isBusy(DFLASH))
        {
            return DRV_TIMEOUT;
        }

        WRITE_REG(DFLASH->EFC_IND_CMD, cmd);
        if (FLASH_isBusy(DFLASH))
        {
            return DRV_TIMEOUT;
        }
        *(data + i) = READ_REG(DFLASH->EFC_IND_RD0) | (uint64_t)READ_REG(DFLASH->EFC_IND_RD1) << 32;
    }
    return DRV_OK;
}

/**
 * @brief Enable Flash ECC function
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param area  FLASH area
 * - FLASH_ZONE_MAIN
 * - FLASH_ZONE_NVR
 * - FLASH_ZONE_NVR_CFG
 */
void FLASH_enableECC(FLASH_Type *FLASHx, FLASH_Zone area)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    if (area == FLASH_ZONE_MAIN)
    {
        SET_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_MAIN_ECC_EN_Msk);
    }
    else if (area == FLASH_ZONE_NVR)
    {
        SET_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_NVR_ECC_EN_Msk);
    }
    else
    {
        SET_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_NVR_CFG_ECC_EN_Msk);
    }
}

/**
 * @brief Disable Flash ECC function
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1, DFLASH]
 * @param area  FLASH area
 * - FLASH_ZONE_MAIN
 * - FLASH_ZONE_NVR
 * - FLASH_ZONE_NVR_CFG
 */
void FLASH_disableECC(FLASH_Type *FLASHx, FLASH_Zone area)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    if (area == FLASH_ZONE_MAIN)
    {
        CLEAR_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_MAIN_ECC_EN_Msk);
    }
    else if (area == FLASH_ZONE_NVR)
    {
        CLEAR_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_NVR_ECC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_NVR_CFG_ECC_EN_Msk);
    }
}

/**
 * @brief Enable Manual ECC error injection
 *
 * @param FLASHx Flash peripheral[PFLASH0:1, DFLASH]
 * @param eccErrorInit   ECC error inject struct
 */
void FLASH_enableECCTest(FLASH_Type *FLASHx, FLASH_ECCConfigParams *eccErrorInit)
{
    uint32_t reg = 0;

    assert_param(IS_FLASH_PERIPHERAL(FLASHx));

    reg = READ_REG(FLASHx->EFC_ECC);
    MODIFY_REG(reg, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_TYPE_Msk,
               (uint32_t)eccErrorInit->errorType << PFLASH_EFC_ECC_EFC_ECC_ERRGEN_TYPE_Pos);
    MODIFY_REG(reg, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_ADDR_Msk,
               (uint32_t)eccErrorInit->eccInjectAddr << PFLASH_EFC_ECC_EFC_ECC_ERRGEN_ADDR_Pos);
    if (eccErrorInit->sectorType == FLASH_ZONE_NVR)
    {
        MODIFY_REG(reg, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_SEC_Msk,
                   0x01 << PFLASH_EFC_ECC_EFC_ECC_ERRGEN_SEC_Pos);
    }
    else
    {
        MODIFY_REG(reg, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_SEC_Msk,
                   0x03 << PFLASH_EFC_ECC_EFC_ECC_ERRGEN_SEC_Pos);
    }
    SET_BIT(reg, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_EN_Msk);
    WRITE_REG(FLASHx->EFC_ECC, reg);
}

/**
 * @brief Disable Manual ECC error injection
 *
 * @param FLASHx Flash peripheral[PFLASH0,PFLASH1,DFLASH]
 */
void FLASH_disableECCTest(FLASH_Type *FLASHx)
{
    assert_param(IS_FLASH_PERIPHERAL(FLASHx));
    CLEAR_BIT(FLASHx->EFC_ECC, PFLASH_EFC_ECC_EFC_ECC_ERRGEN_EN_Msk);
}
