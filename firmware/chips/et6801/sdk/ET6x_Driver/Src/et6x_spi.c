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

#include "et6x_spi.h"
#include "et6x_crg.h"

#define IS_SPI_ALL_PERIPH(PERIPH) \
        (((PERIPH) == SPI0) || \
         ((PERIPH) == SPI1) || \
         ((PERIPH) == SPI2) || \
         ((PERIPH) == SPI3))

#define IS_SPI_CHAR_LENGTH(length)       (length <= 16 && length >= 4)
#define IS_SPI_INTERRUPT_FLGAS(flags)    ((flags &SPI_INTERRUPT_ALL) != 0)

/*! Maximum FIFO depth */
#define SPI_MAX_FIFO_DEPTH    16U
/*! Check if the SPI FIFO depth is valid */
#define IS_SPI_FIFO_THRESHOLD(threshold)    (threshold <= SPI_MAX_FIFO_DEPTH)

#define IS_SPI_TRANSMIT_MODE(MODE) \
        (((MODE) == SPI_TRANSMIT) || \
         ((MODE) == SPI_RECEIVE) || \
         ((MODE) == SPI_EEPROM_READ) || \
         ((MODE) == SPI_TRANSMIT_RECEIVE))

#define IS_SPI_BAUDRATE(BAUDRATE)    ((BAUDRATE <= 50000000))

/**
 * @brief enable module
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 */
void SPI_enableModule(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
}

/**
 * @brief disable module
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 */
void SPI_disableModule(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
}

/**
 * @brief set data length
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param charLength character length [4~16]
 */
void SPI_setcharLength(SPI_Type *SPIx, uint16_t charLength)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_CHAR_LENGTH(charLength));

    charLength = charLength - 1;

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        MODIFY_REG(SPIx->CTRLR0, SPI0_CTRLR0_DFS_Msk, (uint32_t)charLength << SPI0_CTRLR0_DFS_Pos);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        MODIFY_REG(SPIx->CTRLR0, SPI0_CTRLR0_DFS_Msk, (uint32_t)charLength << SPI0_CTRLR0_DFS_Pos);
    }
}

/**
 * @brief set the selected chip signal to retain LOW
 *
 * @param SPIx SPI peripheral [SPI0~SPI2]
 */
void SPI_setCSLow(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        SET_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SPI_SOFT_MODE_Msk);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        SET_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SPI_SOFT_MODE_Msk);
    }
}

/**
 * @brief set the selected chip signal to retain HIGH
 *
 * @param SPIx SPI peripheral [SPI0~SPI2]
 */
void SPI_setCSHigh(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        CLEAR_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SPI_SOFT_MODE_Msk);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SPI_SOFT_MODE_Msk);
    }
}

/**
 * @brief Configure frame number to Receive when Transmit mode is SPI_RECEIVE or SPI_EEPROM_READ
 *
 * @param SPIx SPI peripheral [SPI0~SPI2]
 * @param num number of frames to receive
 */
void SPI_configFrameNum(SPI_Type *SPIx, uint16_t num)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(num <= 0xFFFFU);

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        WRITE_REG(SPIx->CTRLR1, num - 1);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        WRITE_REG(SPIx->CTRLR1, num - 1);
    }
}

/**
 * @brief Configure Transfer mode
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param mode transfer mode
 */
void SPI_configTransMode(SPI_Type *SPIx, SPI_TransferMode mode)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_TRANSMIT_MODE(mode));

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        MODIFY_REG(SPIx->CTRLR0, SPI0_CTRLR0_TMOD_Msk, (uint32_t)(mode << SPI0_CTRLR0_TMOD_Pos));
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        MODIFY_REG(SPIx->CTRLR0, SPI0_CTRLR0_TMOD_Msk, (uint32_t)(mode << SPI0_CTRLR0_TMOD_Pos));
    }
}

/**
 * @brief reset fifo
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 */
void SPI_resetFIFO(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
}

/**
 * @brief Set FIFO interrupt thresholds for transmit and receive
 *
 * @param SPIx Pointer to SPI peripheral
 * @param txLevel Transmit FIFO interrupt threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 * @param rxLevel Receive FIFO interrupt threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 *
 * @note Threshold values are checked by IS_SPI_FIFO_THRESHOLD macro to ensure they are less than SPI_MAX_FIFO_DEPTH
 */
void SPI_setFIFOInterruptLevel(SPI_Type *SPIx, uint8_t txLevel, uint8_t rxLevel)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_FIFO_THRESHOLD(txLevel));
    assert_param(IS_SPI_FIFO_THRESHOLD(rxLevel));

    MODIFY_REG(SPIx->TXFTLR, SPI0_TXFTLR_TFT_Msk, (uint32_t)txLevel << SPI0_TXFTLR_TFT_Pos);
    MODIFY_REG(SPIx->RXFTLR, SPI0_RXFTLR_RFT_Msk, (uint32_t)rxLevel << SPI0_RXFTLR_RFT_Pos);
}

/**
 * @brief get FIFO interrupt level
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param txLevel Transmit FIFO interrupt threshold
 * @param rxLevel Receive FIFO interrupt threshold
 */
void SPI_getFIFOInterruptLevel(SPI_Type *SPIx, uint8_t *txLevel, uint8_t *rxLevel)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    *txLevel = (uint8_t)READ_REG(SPIx->TXFTLR);
    *rxLevel = (uint8_t)READ_REG(SPIx->RXFTLR);
}

/**
 * @brief Set Transfer start FIFO level
 *
 * @param SPIx Pointer to SPI peripheral
 * @param startLevel Transfer start FIFO threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 *
 * @note Threshold values are checked by IS_SPI_FIFO_THRESHOLD macro to ensure they are less than SPI_MAX_FIFO_DEPTH
 */
void SPI_setTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t startLevel)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_FIFO_THRESHOLD(startLevel));

    MODIFY_REG(SPIx->TXFTLR, SPI0_TXFTLR_TXFTHR_Msk, (uint32_t)startLevel << SPI0_TXFTLR_TXFTHR_Pos);
}

/**
 * @brief get FIFO interrupt level
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param txLevel Transmit FIFO interrupt threshold
 * @param rxLevel Receive FIFO interrupt threshold
 */
void SPI_getTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t *txLevel)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    *txLevel = (uint8_t)(READ_REG(SPIx->TXFTLR) & SPI0_TXFTLR_TXFTHR_Msk >> SPI0_TXFTLR_TXFTHR_Pos);
}

/**
 * @brief get transmit data num in TX FIFO
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return SPI TxFIFO Level
 */
uint8_t SPI_getTxFIFOStatus(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    return (uint8_t)READ_REG(SPIx->TXFLR);
}

/**
 * @brief get received data num in RX FIFO
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return SPI RxFIFO Level
 */
uint8_t SPI_getRxFIFOStatus(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    return (uint8_t)READ_REG(SPIx->RXFLR);
}

/**
 * @brief get spi is busy or not
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return true if SPI is busy, false otherwise
 */
bool SPI_isBusy(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    return READ_BIT(SPIx->SR, SPI0_SR_BUSY_Msk) != 0;
}

/**
 * @brief write data in non-blocking mode
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param data Data to be written
 */
void SPI_writeDataNonBlocking(SPI_Type *SPIx, uint16_t data)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    WRITE_REG(SPIx->DR[0], data);
    while ((SPIx->SR & 0x05) != 0x04);
}

/**
 * @brief read data in non-blocking mode
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return uint16_t Data read from SPI DR register
 */
uint16_t SPI_readDataNonBlocking(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    return (uint16_t)READ_REG(SPIx->DR[0]);
}

/**
 * @brief write data in blocking mode with FIFO status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param data Data to be written
 */
void SPI_writeDataBlockingFIFO(SPI_Type *SPIx, uint16_t data)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    while (SPI_getTxFIFOStatus(SPIx) == SPI_MAX_FIFO_DEPTH)
    {
    }

    WRITE_REG(SPIx->DR[0], data);
    while ((SPIx->SR & SPI0_SR_TFNF_Msk) != SPI0_SR_TFNF_Msk);
}

/**
 * @brief  read data in blocking mode with FIFO status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return uint16_t Data read from SPI DR register
 */
uint16_t SPI_readDataBlockingFIFO(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    while (SPI_getRxFIFOStatus(SPIx) == 0U)
    {
    }

    return (uint16_t)READ_REG(SPIx->DR[0]);
}

/**
 * @brief write data in blocking mode with register status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param data Data to be written
 */
void SPI_writeDataBlockingNonFIFO(SPI_Type *SPIx, uint16_t data)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    while (READ_BIT(SPIx->SR, SPI0_SR_TFNF_Msk) == 0U)
    {
    }

    WRITE_REG(SPIx->DR[0], data);
    while ((SPIx->SR & 0x05) != 0x04);
}

/**
 * @brief read data in blocking mode with register status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @return uint16_t Data read from SPI DR register
 */
uint16_t SPI_readDataBlockingNonFIFO(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    while (READ_BIT(SPIx->SR, SPI0_SR_RFNE_Msk) == 0U)
    {
    }

    return (uint16_t)READ_REG(SPIx->DR[0]);
}

/**
 * @brief set spi configuration
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param config SPI configuration
 */
void SPI_setConfig(SPI_Type *SPIx, SPI_Config *config)
{
    uint32_t   tempReg  = 0;
    FlagStatus reenable = RESET;

    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_TRANSMIT_MODE(config->transferMode));
    assert_param(IS_SPI_BAUDRATE(config->bitRate));
    assert_param(IS_SPI_CHAR_LENGTH(config->charLength));

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        reenable = SET;
    }

    SET_BIT(tempReg, (uint32_t)(config->charLength - 1) << SPI0_CTRLR0_DFS_Pos);
    SET_BIT(tempReg, (uint32_t)config->protocol << SPI0_CTRLR0_SCPH_Pos);
    SET_BIT(tempReg, (uint32_t)config->transferMode << SPI0_CTRLR0_TMOD_Pos);
    SET_BIT(tempReg, (uint32_t)config->slaveOutputEn << SPI0_CTRLR0_SLV_OE_Pos);
    SET_BIT(tempReg, (uint32_t)config->CSToggleEn << SPI0_CTRLR0_SSTE_Pos);
    SET_BIT(tempReg, (uint32_t)config->workMode << SPI0_CTRLR0_SSI_IS_MST_Pos);
    WRITE_REG(SPIx->CTRLR0, tempReg);

    WRITE_REG(SPIx->SER, SPI0_SER_SER_Msk);

    tempReg = CRG_getAPB3Clock() / config->bitRate;
    if ((tempReg >= 2) && (tempReg <= 65534))
    {
        WRITE_REG(SPIx->BAUDR, tempReg);
    }

    /* Set up control1,only in SPI_RECEIVE mode or SPI_EEPROM_READ mode */
    WRITE_REG(SPIx->CTRLR1, config->rxDataNum);

    /* mask all interrupt */
    CLEAR_BIT(SPIx->IMR, (uint32_t)0x3F);

    /* if master receive data */
    WRITE_REG(SPIx->RX_SAMPLE_DELAY, config->rxSampleDly);

    if (reenable == SET)
    {
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
}

/**
 * @brief set spi baud rate
 *
 * @param SPIx SPI peripheral [SPI0~SPI2]
 * @param bitRate SPI baud rate
 */
void SPI_setBaudRate(SPI_Type *SPIx, uint32_t bitRate)
{
    uint32_t tempReg = 0;

    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_BAUDRATE(bitRate));

    tempReg = CRG_getAPB3Clock() / bitRate;

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        if ((tempReg >= 2) && (tempReg <= 65534))
        {
            WRITE_REG(SPIx->BAUDR, tempReg);
        }
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        if ((tempReg >= 2) && (tempReg <= 65534))
        {
            WRITE_REG(SPIx->BAUDR, tempReg);
        }
    }
}

/**
 * @brief enable interrupt
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param intFlags
 * SPI0_IMR_RSVD_IMR_Msk
 * SPI0_IMR_MSTIM_Msk
 * SPI0_IMR_RXFIM_Msk
 * SPI0_IMR_RXOIM_Msk
 * SPI0_IMR_RXUIM_Msk
 * SPI0_IMR_TXOIM_Msk
 * SPI0_IMR_TXEIM_Msk
 */
void SPI_enableInterrupt(SPI_Type *SPIx, uint32_t intFlags)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_INTERRUPT_FLGAS(intFlags));

    SET_BIT(SPIx->IMR, intFlags);
}

/**
 * @brief disable interrupt
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param intFlags parameters are the same as those used in SPI_enableInterrupt.
 */
void SPI_disableInterrupt(SPI_Type *SPIx, uint32_t intFlags)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_INTERRUPT_FLGAS(intFlags));

    CLEAR_BIT(SPIx->IMR, intFlags);
}

/**
 * @brief get interrupt status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 *
 * @return uint32_t Interrupt status register value
 */
uint32_t SPI_getInterruptStatus(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    return READ_REG(SPIx->ISR);
}

/**
 * @brief clear interrupt status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param intFlags parameters are the same as those used in SPI_enableInterrupt.
 */
void SPI_clearInterruptStatus(SPI_Type *SPIx, uint32_t intFlags)
{
    uint32_t tempReg = 0;

    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_INTERRUPT_FLGAS(intFlags));

    if ((intFlags & SPI0_IMR_TXOIM_Msk) != 0)
    {
        tempReg = READ_REG(SPIx->TXEICR);
    }
    if ((intFlags & SPI0_IMR_RXOIM_Msk) != 0)
    {
        tempReg = READ_REG(SPIx->RXOICR);
    }
    if ((intFlags & SPI0_IMR_RXUIM_Msk) != 0)
    {
        tempReg = READ_REG(SPIx->RXUICR);
    }
    if ((intFlags & SPI0_IMR_MSTIM_Msk) != 0)
    {
        tempReg = READ_REG(SPIx->MSTICR);
    }
    if ((intFlags & SPI0_IMR_TXEIM_Msk) != 0)
    {
        /* auto cleared by hardware when write data to tx fifo */
    }
    if ((intFlags & SPI0_IMR_RXFIM_Msk) != 0)
    {
        /* auto cleared by hardware when read data from rx fifo */
    }
    UNUSED(tempReg);
}

/**
 * @brief set Transmit Data Level.
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param level Transmit Data Level.
 */
void SPI_setDMATransmitDataLevel(SPI_Type *SPIx, uint8_t level)
{
    IS_SPI_FIFO_THRESHOLD(level);
    WRITE_REG(SPIx->DMATDLR, level);
}

/**
 * @brief set Transmit Data Level.
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param level Transmit Data Level.
 */
void SPI_setDMARecevieDataLevel(SPI_Type *SPIx, uint8_t level)
{
    IS_SPI_FIFO_THRESHOLD(level);
    WRITE_REG(SPIx->DMARDLR, level);
}

/**
 * @brief enable DMA interface
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 */
void SPI_enableDMA(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    SET_BIT(SPIx->DMACR, SPI0_DMACR_RDMAE_Msk | SPI0_DMACR_TDMAE_Msk);
}

/**
 * @brief disable DMA interface
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 */
void SPI_disableDMA(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    CLEAR_BIT(SPIx->DMACR, SPI0_DMACR_RDMAE_Msk | SPI0_DMACR_TDMAE_Msk);
}

/**
 * @brief transmit 24bits data with 8bits length data
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param data 24bits data to transmit
 */
void SPI_transmit24Bits(SPI_Type *SPIx, uint32_t data)
{
    uint16_t i;
    uint16_t rxBuffer[3];
    uint16_t txBuffer[3];

    for (i = 0U; i < 3U; i++)
    {
        rxBuffer[i] = 0U;
    }

    txBuffer[0] = (uint16_t)(data >> 16U);
    txBuffer[1] = (uint16_t)(data) >> 8U;
    txBuffer[2] = (uint16_t)(data) & 0x00FFU;

    SPI_pollingFIFOTransaction(SPIx, 8U, txBuffer, rxBuffer, 3U);
}

/**
 * @brief transmit 32bits data with 16bits length data
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param data 32bits data to transmit
 */
void SPI_transmit32Bits(SPI_Type *SPIx, uint32_t data)
{
    uint16_t i;
    uint16_t txBuffer[2];
    uint16_t rxBuffer[2];

    for (i = 0U; i < 2U; i++)
    {
        rxBuffer[i] = 0U;
    }

    txBuffer[0] = (uint16_t)(data >> 16U);
    txBuffer[1] = (uint16_t)(data);

    SPI_pollingFIFOTransaction(SPIx, 16U, txBuffer, rxBuffer, 2U);
}

/**
 * @brief receive 16bit with 8bit length data
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param endianness Data endianess
 * @param dummyData Dummy data to send
 * @return uint16_t
 */
uint16_t SPI_receive16Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData)
{
    uint16_t i;
    uint16_t txBuffer[2];
    uint16_t rxBuffer[2];
    uint16_t rxData = 0U;

    for (i = 0U; i < 2U; i++)
    {
        txBuffer[i] = dummyData;
        rxBuffer[i] = 0U;
    }

    SPI_pollingFIFOTransaction(SPIx, 8U, txBuffer, rxBuffer, 2U);

    if (endianness == SPI_DATA_LITTLE_ENDIAN)
    {
        rxData = (uint16_t)(rxBuffer[1] << 8) | rxBuffer[0];
    }
    else
    {
        rxData = (uint16_t)(rxBuffer[0] << 8) | rxBuffer[1];
    }

    return(rxData);
}

/**
 * @brief receive 24bit with 8bit length data
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param endianness Data endianess
 * @param dummyData Dummy data to send
 * @return uint32_t 24bits data received
 */
uint32_t SPI_receive24Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData)
{
    uint16_t i;
    uint16_t txBuffer[3];
    uint16_t rxBuffer[3];
    uint32_t rxData = 0;

    for (i = 0U; i < 3U; i++)
    {
        txBuffer[i] = dummyData;
        rxBuffer[i] = 0U;
    }

    SPI_pollingFIFOTransaction(SPIx, 8U, txBuffer, rxBuffer, 3U);

    if (endianness == SPI_DATA_LITTLE_ENDIAN)
    {
        rxData = ((uint32_t)rxBuffer[2] << 16) |
                 ((uint32_t)rxBuffer[1] << 8) |
                 (uint32_t)rxBuffer[0];
    }
    else
    {
        rxData = ((uint32_t)rxBuffer[0] << 16) |
                 ((uint32_t)rxBuffer[1] << 8) |
                 (uint32_t)rxBuffer[2];
    }

    return(rxData);
}

/**
 * @brief receive 32bit with 8bit length data
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param endianness Data endianess
 * @param dummyData Dummy data to send
 * @return uint32_t 32bits data received
 */
uint32_t SPI_receive32Bits(SPI_Type *SPIx, SPI_endianess endianness, uint16_t dummyData)
{
    uint16_t i;
    uint16_t txBuffer[4];
    uint16_t rxBuffer[4];
    uint32_t rxData = 0U;

    for (i = 0U; i < 4U; i++)
    {
        txBuffer[i] = dummyData;
        rxBuffer[i] = 0U;
    }

    SPI_pollingFIFOTransaction(SPIx, 8U, txBuffer, rxBuffer, 4U);

    if (endianness == SPI_DATA_LITTLE_ENDIAN)
    {
        rxData = ((uint32_t)rxBuffer[3] << 24U) |
                 ((uint32_t)rxBuffer[2] << 16U) |
                 ((uint32_t)rxBuffer[1] << 8U) |
                 (uint32_t)rxBuffer[0];
    }
    else
    {
        rxData = ((uint32_t)rxBuffer[0] << 24U) |
                 ((uint32_t)rxBuffer[1] << 16U) |
                 ((uint32_t)rxBuffer[2] << 8U) |
                 (uint32_t)rxBuffer[3];
    }

    return(rxData);
}

/**
 * @brief transmit and receive 1 data in polling mode with register status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param charLength Character length [8~16]
 * @param data Data to transmit
 * @return uint16_t Data received
 */
uint16_t SPI_pollingNonFIFOTransaction(SPI_Type *SPIx, uint16_t charLength, uint16_t data)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_CHAR_LENGTH(charLength));

    SPI_setcharLength(SPIx, charLength);

    SPI_writeDataBlockingNonFIFO(SPIx, data);
    return SPI_readDataBlockingNonFIFO(SPIx);
}

/**
 * @brief transmit and receive [numOfWords] data in polling mode with register status
 *
 * @param SPIx SPI peripheral [SPI0~SPI3]
 * @param charLength Character length [8~16]
 * @param pTxBuffer Transmit buffer pointer
 * @param pRxBuffer Receive buffer pointer
 * @param numOfWords Number of words to transmit/receive
 */
void SPI_pollingFIFOTransaction(SPI_Type *SPIx, uint16_t charLength, void *pTxBuffer, void *pRxBuffer,
                                uint16_t numOfWords)
{
    uint16_t numOfSixteenWords = numOfWords / (uint16_t)SPI_MAX_FIFO_DEPTH;
    uint16_t remainingWords    = numOfWords % (uint16_t)SPI_MAX_FIFO_DEPTH;
    uint16_t count             = 0;
    uint16_t i            = 0;
    uint16_t txBuffer_pos = 0;
    uint16_t rxBuffer_pos = 0;

    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_CHAR_LENGTH(charLength));

    SPI_setcharLength(SPIx, charLength);

    SPI_resetFIFO(SPIx);

    if (charLength > 8)
    {
        while (count < numOfSixteenWords)
        {
            for (i = 0; i < SPI_MAX_FIFO_DEPTH; i++)
            {
                SPI_writeDataBlockingFIFO(SPIx, *((uint16_t *)pTxBuffer + txBuffer_pos));
                txBuffer_pos++;
            }

            while (SPI_getRxFIFOStatus(SPIx) < SPI_MAX_FIFO_DEPTH)
            {
            }

            if (pRxBuffer != NULL)
            {
                for (i = 0; i < SPI_MAX_FIFO_DEPTH; i++)
                {
                    *((uint16_t *)pRxBuffer + rxBuffer_pos) = SPI_readDataBlockingFIFO(SPIx);
                    rxBuffer_pos++;
                }
            }
            count++;
        }

        for (i = 0; i < remainingWords; i++)
        {
            SPI_writeDataBlockingFIFO(SPIx, *((uint16_t *)pTxBuffer + txBuffer_pos));
            txBuffer_pos++;
        }

        while (SPI_getRxFIFOStatus(SPIx) < remainingWords)
        {
        }

        if (pRxBuffer != NULL)
        {
            for (i = 0; i < remainingWords; i++)
            {
                *((uint16_t *)pRxBuffer + rxBuffer_pos) = SPI_readDataBlockingFIFO(SPIx);
                rxBuffer_pos++;
            }
        }
    }
    else
    {
        while (count < numOfSixteenWords)
        {
            for (i = 0; i < (uint16_t)SPI_MAX_FIFO_DEPTH; i++)
            {
                SPI_writeDataBlockingFIFO(SPIx, *((uint8_t *)pTxBuffer + txBuffer_pos));
                txBuffer_pos++;
            }

            while (SPI_getRxFIFOStatus(SPIx) < SPI_MAX_FIFO_DEPTH)
            {
            }

            if (pRxBuffer != NULL)
            {
                for (i = 1U; i <= SPI_MAX_FIFO_DEPTH; i++)
                {
                    *((uint8_t *)pRxBuffer + rxBuffer_pos) = (uint8_t)SPI_readDataBlockingFIFO(SPIx);
                    rxBuffer_pos++;
                }
            }
            count++;
        }

        for (i = 0U; i < remainingWords; i++)
        {
            SPI_writeDataBlockingFIFO(SPIx, *((uint8_t *)pTxBuffer + txBuffer_pos));
            txBuffer_pos++;
        }

        while (SPI_getRxFIFOStatus(SPIx) < remainingWords)
        {
        }

        if (pRxBuffer != NULL)
        {
            for (i = 0; i < remainingWords; i++)
            {
                *((uint8_t *)pRxBuffer + rxBuffer_pos) = (uint8_t)SPI_readDataBlockingFIFO(SPIx);
                rxBuffer_pos++;
            }
        }
    }
    SPI_resetFIFO(SPIx);
}

/**
 * @brief Enables the loopback mode for the SPI interface.
 *
 * In loopback mode, the transmitted data is internally connected to the receiver input,
 * allowing for testing and debugging without the need for an external device.
 *
 * @param SPIx  Pointer to the SPI peripheral, where x can be 0, 1, 2, or 3 to select the SPI peripheral.
 *
 * @note This function should be called only when the SPI interface is disabled.
 *
 */
void SPI_enableLoopback(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    SET_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SRL_Msk);
}

/**
 * @brief Disables the loopback mode for the SPI interface.
 *
 * In loopback mode, the transmitted data is internally connected to the receiver input,
 * allowing for testing and debugging without the need for an external device.
 *
 * @param SPIx  Pointer to the SPI peripheral, where x can be 0, 1, 2, or 3 to select the SPI peripheral.
 *
 * @note This function should be called only when the SPI interface is disabled.
 *
 */
void SPI_disableLoopback(SPI_Type *SPIx)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));

    CLEAR_BIT(SPIx->CTRLR0, SPI0_CTRLR0_SRL_Msk);
}

/**
 * @brief Initializes the SPI configuration structure
 *
 * @param cfg Pointer to the SPI configuration structure
 *
 * @note This function is used to initialize each member variable of the SPI configuration structure
 *
 */
void SPI_initStruct(SPI_Config *cfg)
{
    cfg->charLength    = 8;
    cfg->workMode      = SPI_MASTER_MODE;
    cfg->transferMode  = SPI_TRANSMIT_RECEIVE;
    cfg->protocol      = SPI_PROT_POL0PHA0;
    cfg->bitRate       = 1000000;
    cfg->slaveOutputEn = DISABLE;
    cfg->CSToggleEn    = DISABLE;
    cfg->rxDataNum     = 0;
    cfg->rxSampleDly   = 0;
}
