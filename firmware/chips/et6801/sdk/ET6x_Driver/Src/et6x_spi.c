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

#define IS_SPI_CHAR_LENGTH(length)       ((length) <= SPI_MAX_FRAME_BITS && (length) >= SPI_MIN_FRAME_BITS)
#define IS_SPI_INTERRUPT_FLGAS(flags)    ((flags &SPI_INTERRUPT_ALL) != 0)

/*! Check if the SPI FIFO depth is valid */
#define IS_SPI_FIFO_THRESHOLD(threshold)    ((threshold) < SPI_MAX_FIFO_DEPTH)

#define IS_SPI_TRANSMIT_MODE(MODE) \
        (((MODE) == SPI_TRANSMIT) || \
         ((MODE) == SPI_RECEIVE) || \
         ((MODE) == SPI_EEPROM_READ) || \
         ((MODE) == SPI_TRANSMIT_RECEIVE))

#define IS_SPI_BAUDRATE(BAUDRATE)    (((BAUDRATE) > 0U) && ((BAUDRATE) <= 50000000U))

/**
 * @brief Quantize a requested maximum bitrate to an even SVD divider.
 * @param bitRate Requested maximum SCLK frequency in Hz.
 * @return Legal divisor or zero when the request cannot be represented.
 * @note Round upward without overflowing inputClock + bitRate; never overspeed.
 */
static uint32_t spi_baud_divider(uint32_t bitRate)
{
    uint32_t inputClock;
    uint32_t divider;

    if (!IS_SPI_BAUDRATE(bitRate))
    {
        return 0U;
    }
    inputClock = CRG_getAPB3Clock();
    if (inputClock == 0U)
    {
        return 0U;
    }
    divider = inputClock / bitRate;
    if (inputClock % bitRate != 0U)
    {
        ++divider;
    }
    if (divider < SPI_CLOCK_DIVIDER_MIN)
    {
        divider = SPI_CLOCK_DIVIDER_MIN;
    }
    if (divider > SPI_CLOCK_DIVIDER_MAX)
    {
        return 0U;
    }
    if ((divider & SPI0_BAUDR_RSVD_BAUDR_0_Msk) != 0U)
    {
        ++divider;
    }
    return divider;
}

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
    assert_param(num != 0U);

    if (num == 0U)
    {
        return;
    }

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
 * @param txLevel Transmit FIFO interrupt threshold (0 through SPI_MAX_FIFO_DEPTH - 1)
 * @param rxLevel Receive FIFO interrupt threshold (0 through SPI_MAX_FIFO_DEPTH - 1)
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

    assert_param(txLevel != NULL);
    *txLevel = (uint8_t)((READ_REG(SPIx->TXFTLR) & SPI0_TXFTLR_TXFTHR_Msk) >> SPI0_TXFTLR_TXFTHR_Pos);
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
    uint32_t   divider;
    FlagStatus reenable = RESET;

    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_TRANSMIT_MODE(config->transferMode));
    assert_param(IS_SPI_BAUDRATE(config->bitRate));
    assert_param(IS_SPI_CHAR_LENGTH(config->charLength));

    /* Reject zero even when assertions are disabled; do not partly reconfigure. */
    divider = spi_baud_divider(config->bitRate);
    if (divider == 0U)
    {
        return;
    }

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

    WRITE_REG(SPIx->BAUDR, divider);

    /* Set up control1,only in SPI_RECEIVE mode or SPI_EEPROM_READ mode */
    WRITE_REG(SPIx->CTRLR1, config->rxDataNum);

    /* mask all interrupt */
    CLEAR_BIT(SPIx->IMR, SPI_INTERRUPT_ALL);

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

    tempReg = spi_baud_divider(bitRate);
    if (tempReg == 0U)
    {
        return;
    }

    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
        WRITE_REG(SPIx->BAUDR, tempReg);
        SET_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        WRITE_REG(SPIx->BAUDR, tempReg);
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
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_FIFO_THRESHOLD(level));
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
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    assert_param(IS_SPI_FIFO_THRESHOLD(level));
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

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
/******************** TEST DRIVER EXTENSION BEGIN ********************/
/**
 * @brief Configure disabled SPI using exact values instead of implicit defaults.
 * @param SPIx SPI peripheral.
 * @param config Fully specified configuration; Boolean fields must be zero or one.
 * @return DRV_OK, DRV_PARAM_ERR or DRV_BUSY without writes on rejection.
 * @note Does not enable SPI, select CS, change IRQ/DMA masks or query another IP clock.
 */
DRV_Status SPI_testConfigureStopped(SPI_Type *SPIx, const SPI_TestConfig *config)
{
    uint32_t control;
    uint32_t mask;

    /* Phase 1: Validate every field before any configuration register write. */
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || config == NULL)
    {
        return DRV_PARAM_ERR;
    }
    if (config->role > SPI_MASTER_MODE || config->format > SPI_TEST_FORMAT_MICROWIRE ||
        config->clockMode > SPI_PROT_POL1PHA1 || !IS_SPI_TRANSMIT_MODE(config->transferMode) ||
        !IS_SPI_CHAR_LENGTH(config->frameBits) || config->frameCount == 0U ||
        config->frameCount > SPI_TEST_FRAME_COUNT_MAX || config->divider < SPI_CLOCK_DIVIDER_MIN ||
        config->divider > SPI_CLOCK_DIVIDER_MAX ||
        (config->divider & SPI0_BAUDR_RSVD_BAUDR_0_Msk) != 0U ||
        config->csPolicy > SPI_TEST_CS_TOGGLE || config->outputEnabled > 1U ||
        config->loopback > 1U || config->rxDelay > SPI0_RX_SAMPLE_DELAY_RSD_Msk ||
        config->controlBits == 0U || config->controlBits > SPI_MAX_FRAME_BITS ||
        config->sequential > 1U || config->transmit > 1U || config->handshake > 1U)
    {
        return DRV_PARAM_ERR;
    }
    /* SSTE only has meaning for Motorola with CPHA=0. Reject ignored requests. */
    if (config->csPolicy == SPI_TEST_CS_TOGGLE &&
        (config->format != SPI_TEST_FORMAT_MOTOROLA ||
         (config->clockMode != SPI_PROT_POL0PHA0 && config->clockMode != SPI_PROT_POL1PHA0)))
    {
        return DRV_PARAM_ERR;
    }
    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U)
    {
        return DRV_BUSY;
    }

    /* Phase 2: Encode only the documented fields; preserve reserved bits. */
    mask = SPI0_CTRLR0_DFS_Msk | SPI0_CTRLR0_FRF_Msk | SPI0_CTRLR0_SCPH_Msk |
           SPI0_CTRLR0_SCPOL_Msk | SPI0_CTRLR0_TMOD_Msk | SPI0_CTRLR0_SLV_OE_Msk |
           SPI0_CTRLR0_SRL_Msk | SPI0_CTRLR0_SSTE_Msk | SPI0_CTRLR0_CFS_Msk |
           SPI0_CTRLR0_SPI_SOFT_MODE_Msk | SPI0_CTRLR0_SSI_IS_MST_Msk;
    control = ((config->frameBits - 1U) << SPI0_CTRLR0_DFS_Pos) |
              (config->format << SPI0_CTRLR0_FRF_Pos) |
              (config->clockMode << SPI0_CTRLR0_SCPH_Pos) |
              (config->transferMode << SPI0_CTRLR0_TMOD_Pos) |
              (config->role << SPI0_CTRLR0_SSI_IS_MST_Pos) |
              ((config->controlBits - 1U) << SPI0_CTRLR0_CFS_Pos);
    control |= config->outputEnabled == 0U ? SPI0_CTRLR0_SLV_OE_Msk : 0U;
    control |= config->loopback != 0U ? SPI0_CTRLR0_SRL_Msk : 0U;
    control |= config->csPolicy == SPI_TEST_CS_HOLD ? SPI0_CTRLR0_SPI_SOFT_MODE_Msk : 0U;
    control |= config->csPolicy == SPI_TEST_CS_TOGGLE ? SPI0_CTRLR0_SSTE_Msk : 0U;
    MODIFY_REG(SPIx->CTRLR0, mask, control);
    WRITE_REG(SPIx->CTRLR1, config->frameCount - 1U);
    WRITE_REG(SPIx->BAUDR, config->divider);
    MODIFY_REG(SPIx->RX_SAMPLE_DELAY, SPI0_RX_SAMPLE_DELAY_RSD_Msk, config->rxDelay);
    MODIFY_REG(SPIx->MWCR, SPI0_MWCR_MWMOD_Msk | SPI0_MWCR_MDD_Msk | SPI0_MWCR_MHS_Msk,
               (config->sequential << SPI0_MWCR_MWMOD_Pos) |
               (config->transmit << SPI0_MWCR_MDD_Pos) |
               (config->handshake << SPI0_MWCR_MHS_Pos));
    return DRV_OK;
}

/**
 * @brief Decode hardware configuration without reading data or error registers.
 * @param SPIx SPI peripheral.
 * @param config Output decoded settings, including reset values outside valid setup ranges.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note Readback is not a cached echo; unsupported combined CS bits return UNKNOWN policy.
 */
DRV_Status SPI_testGetConfig(SPI_Type *SPIx, SPI_TestConfig *config)
{
    uint32_t control;
    uint32_t microwire;
    uint32_t cs;
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || config == NULL)
    {
        return DRV_PARAM_ERR;
    }
    control = READ_REG(SPIx->CTRLR0);
    microwire = READ_REG(SPIx->MWCR);
    config->role = (control & SPI0_CTRLR0_SSI_IS_MST_Msk) >> SPI0_CTRLR0_SSI_IS_MST_Pos;
    config->format = (control & SPI0_CTRLR0_FRF_Msk) >> SPI0_CTRLR0_FRF_Pos;
    config->clockMode = (control & (SPI0_CTRLR0_SCPH_Msk | SPI0_CTRLR0_SCPOL_Msk)) >> SPI0_CTRLR0_SCPH_Pos;
    config->transferMode = (control & SPI0_CTRLR0_TMOD_Msk) >> SPI0_CTRLR0_TMOD_Pos;
    config->frameBits = ((control & SPI0_CTRLR0_DFS_Msk) >> SPI0_CTRLR0_DFS_Pos) + 1U;
    config->frameCount = (READ_REG(SPIx->CTRLR1) & SPI0_CTRLR1_NDF_Msk) + 1U;
    config->divider = READ_REG(SPIx->BAUDR) & SPI0_BAUDR_SCKDV_Msk;
    config->outputEnabled = (control & SPI0_CTRLR0_SLV_OE_Msk) == 0U;
    config->loopback = (control & SPI0_CTRLR0_SRL_Msk) != 0U;
    config->rxDelay = READ_REG(SPIx->RX_SAMPLE_DELAY) & SPI0_RX_SAMPLE_DELAY_RSD_Msk;
    config->controlBits = ((control & SPI0_CTRLR0_CFS_Msk) >> SPI0_CTRLR0_CFS_Pos) + 1U;
    config->sequential = (microwire & SPI0_MWCR_MWMOD_Msk) != 0U;
    config->transmit = (microwire & SPI0_MWCR_MDD_Msk) != 0U;
    config->handshake = (microwire & SPI0_MWCR_MHS_Msk) != 0U;
    cs = control & (SPI0_CTRLR0_SPI_SOFT_MODE_Msk | SPI0_CTRLR0_SSTE_Msk);
    config->csPolicy = cs == 0U ? SPI_TEST_CS_AUTO :
                       cs == SPI0_CTRLR0_SPI_SOFT_MODE_Msk ? SPI_TEST_CS_HOLD :
                       cs == SPI0_CTRLR0_SSTE_Msk ? SPI_TEST_CS_TOGGLE : SPI_TEST_CS_UNKNOWN;
    return DRV_OK;
}

/**
 * @brief Change loopback without a hidden disable/re-enable FIFO reset.
 * @param SPIx SPI peripheral.
 * @param enabled Boolean internal loopback enable.
 * @return DRV_OK, DRV_PARAM_ERR or DRV_BUSY.
 * @note Module must already be disabled; target mode still needs external clock and CS.
 */
DRV_Status SPI_testSetLoopbackStopped(SPI_Type *SPIx, uint8_t enabled)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || enabled > 1U)
    {
        return DRV_PARAM_ERR;
    }
    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U)
    {
        return DRV_BUSY;
    }
    if (enabled != 0U)
    {
        SPI_enableLoopback(SPIx);
    }
    else
    {
        SPI_disableLoopback(SPIx);
    }
    return DRV_OK;
}

/**
 * @brief Validate all three FIFO thresholds before updating any of them.
 * @param SPIx SPI peripheral.
 * @param tx TX IRQ threshold in frames.
 * @param rx RX IRQ threshold; assertion starts at rx plus one frames.
 * @param start TX start threshold; transfer starts above this level.
 * @return DRV_OK or DRV_PARAM_ERR without partial updates.
 * @note May change live level conditions; does not drain FIFO or touch SR.
 */
DRV_Status SPI_testSetFIFOThresholds(SPI_Type *SPIx, uint8_t tx, uint8_t rx, uint8_t start)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || !IS_SPI_FIFO_THRESHOLD(tx) ||
        !IS_SPI_FIFO_THRESHOLD(rx) || !IS_SPI_FIFO_THRESHOLD(start))
    {
        return DRV_PARAM_ERR;
    }
    SPI_setFIFOInterruptLevel(SPIx, tx, rx);
    SPI_setTansferStartFIFOLevel(SPIx, start);
    return DRV_OK;
}

/**
 * @brief Obtain the data-register bus address for an independently configured DMA.
 * @param SPIx SPI peripheral.
 * @param address Output DMA peripheral endpoint address.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note Returns an address only; no data, status or clear register is accessed.
 */
DRV_Status SPI_testGetDMAEndpoint(SPI_Type *SPIx, uintptr_t *address)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || address == NULL)
    {
        return DRV_PARAM_ERR;
    }
    *address = (uintptr_t)&SPIx->DR[0];
    return DRV_OK;
}
/**
 * @brief Set the exact SVD clock divider without using another IP clock API.
 * @param SPIx SPI peripheral.
 * @param divider Even divisor, 2 through 65534.
 * @return DRV_OK, DRV_PARAM_ERR or DRV_BUSY; rejected inputs do not write.
 * @note The module must be disabled. This action does not select CS or enable SPI.
 */
DRV_Status SPI_testSetDivider(SPI_Type *SPIx, uint32_t divider)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || divider < SPI_CLOCK_DIVIDER_MIN ||
        divider > SPI_CLOCK_DIVIDER_MAX || (divider & SPI0_BAUDR_RSVD_BAUDR_0_Msk) != 0U)
    {
        return DRV_PARAM_ERR;
    }
    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U)
    {
        return DRV_BUSY;
    }
    WRITE_REG(SPIx->BAUDR, divider);
    return DRV_OK;
}

/**
 * @brief Configure a real frame count, including the full 65536-frame boundary.
 * @param SPIx SPI peripheral.
 * @param frameCount Actual number of received frames, not encoded NDF.
 * @return DRV_OK, DRV_PARAM_ERR or DRV_BUSY.
 * @note Does not silently disable an active module or destroy its queued frames.
 */
DRV_Status SPI_testSetFrameCount(SPI_Type *SPIx, uint32_t frameCount)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || frameCount == 0U || frameCount > SPI_TEST_FRAME_COUNT_MAX)
    {
        return DRV_PARAM_ERR;
    }
    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U)
    {
        return DRV_BUSY;
    }
    WRITE_REG(SPIx->CTRLR1, frameCount - 1U);
    return DRV_OK;
}

/**
 * @brief Select or release the integrated hardware CS without toggling SSIENR.
 * @param SPIx SPI peripheral.
 * @param selected Boolean hardware selection.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note SER is not a GPIO output level; SOFT_MODE remains a separate configuration.
 */
DRV_Status SPI_testSelectCS(SPI_Type *SPIx, uint8_t selected)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || selected > 1U)
    {
        return DRV_PARAM_ERR;
    }
    MODIFY_REG(SPIx->SER, SPI0_SER_SER_Msk, selected != 0U ? SPI0_SER_SER_Msk : 0U);
    return DRV_OK;
}

/**
 * @brief Configure independent TX/RX DMA requests and frame thresholds.
 * @param SPIx SPI peripheral.
 * @param txEnabled Boolean TX request enable.
 * @param rxEnabled Boolean RX request enable.
 * @param txLevel TX request threshold in frames.
 * @param rxLevel RX request threshold encoding; request begins at level plus one.
 * @return DRV_OK or DRV_PARAM_ERR, with no writes on invalid input.
 * @note Only SPI request generation is affected; no DMA controller is configured.
 */
DRV_Status SPI_testConfigureDMA(SPI_Type *SPIx, uint8_t txEnabled, uint8_t rxEnabled,
                               uint8_t txLevel, uint8_t rxLevel)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || txEnabled > 1U || rxEnabled > 1U ||
        !IS_SPI_FIFO_THRESHOLD(txLevel) || !IS_SPI_FIFO_THRESHOLD(rxLevel))
    {
        return DRV_PARAM_ERR;
    }
    /* Stop requests before changing watermarks; publish both directions last. */
    SPI_disableDMA(SPIx);
    SPI_setDMATransmitDataLevel(SPIx, txLevel);
    SPI_setDMARecevieDataLevel(SPIx, rxLevel);
    MODIFY_REG(SPIx->DMACR, SPI0_DMACR_TDMAE_Msk | SPI0_DMACR_RDMAE_Msk,
               (txEnabled != 0U ? SPI0_DMACR_TDMAE_Msk : 0U) |
               (rxEnabled != 0U ? SPI0_DMACR_RDMAE_Msk : 0U));
    return DRV_OK;
}

/**
 * @brief Read configuration, FIFO levels and IRQ state without consuming errors.
 * @param SPIx SPI peripheral.
 * @param snapshot Output hardware readback, not a saved configuration echo.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note SR, DR and all interrupt-clear registers are deliberately excluded.
 */
DRV_Status SPI_testGetSnapshot(SPI_Type *SPIx, SPI_TestSnapshot *snapshot)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || snapshot == NULL)
    {
        return DRV_PARAM_ERR;
    }
    snapshot->control = READ_REG(SPIx->CTRLR0);
    snapshot->frame_count = (READ_REG(SPIx->CTRLR1) & SPI0_CTRLR1_NDF_Msk) + 1U;
    snapshot->enabled = READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U;
    snapshot->selected = READ_BIT(SPIx->SER, SPI0_SER_SER_Msk) != 0U;
    snapshot->divider = READ_REG(SPIx->BAUDR) & SPI0_BAUDR_SCKDV_Msk;
    snapshot->rx_sample_delay = READ_REG(SPIx->RX_SAMPLE_DELAY) & SPI0_RX_SAMPLE_DELAY_RSD_Msk;
    snapshot->tx_level = SPI_getTxFIFOStatus(SPIx);
    snapshot->rx_level = SPI_getRxFIFOStatus(SPIx);
    snapshot->tx_thresholds = READ_REG(SPIx->TXFTLR);
    snapshot->rx_threshold = READ_REG(SPIx->RXFTLR) & SPI0_RXFTLR_RFT_Msk;
    snapshot->irq_raw = READ_REG(SPIx->RISR) & SPI_INTERRUPT_ALL;
    snapshot->irq_status = SPI_getInterruptStatus(SPIx) & SPI_INTERRUPT_ALL;
    snapshot->irq_enabled = READ_REG(SPIx->IMR) & SPI_INTERRUPT_ALL;
    snapshot->dma_enabled = READ_REG(SPIx->DMACR);
    snapshot->dma_tx_threshold = READ_REG(SPIx->DMATDLR);
    snapshot->dma_rx_threshold = READ_REG(SPIx->DMARDLR);
    return DRV_OK;
}

/**
 * @brief Perform one explicit, destructive SR read.
 * @param SPIx SPI peripheral.
 * @param status Output first SR value, including TXE/DCOL and normal status bits.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note Reading this register acknowledges TXE/DCOL; callers must keep this value.
 */
DRV_Status SPI_testReadStatus(SPI_Type *SPIx, uint32_t *status)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || status == NULL)
    {
        return DRV_PARAM_ERR;
    }
    *status = READ_REG(SPIx->SR);
    return DRV_OK;
}

/**
 * @brief Accept at most one frame using the FIFO level, without waiting for SCLK.
 * @param SPIx SPI peripheral.
 * @param frame Input frame; the configured DFS selects valid bits.
 * @param written Output zero when disabled/full, otherwise one accepted FIFO entry.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note FIFO acceptance is not serial completion. No SR read consumes error flags.
 */
DRV_Status SPI_testTryWriteFrame(SPI_Type *SPIx, uint32_t frame, uint8_t *written)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || written == NULL)
    {
        return DRV_PARAM_ERR;
    }
    *written = 0U;
    if (READ_BIT(SPIx->SSIENR, SPI0_SSIENR_SSIC_EN_Msk) != 0U &&
        SPI_getTxFIFOStatus(SPIx) < SPI_MAX_FIFO_DEPTH)
    {
        WRITE_REG(SPIx->DR[0], frame);
        *written = 1U;
    }
    return DRV_OK;
}

/**
 * @brief Read at most one available frame; empty FIFO is not read speculatively.
 * @param SPIx SPI peripheral.
 * @param frame Output received frame; zero when no data is available.
 * @param received Output actual count, zero or one.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note No polling, SR read, or synthetic underflow is hidden in normal reception.
 */
DRV_Status SPI_testTryReadFrame(SPI_Type *SPIx, uint32_t *frame, uint8_t *received)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || frame == NULL || received == NULL)
    {
        return DRV_PARAM_ERR;
    }
    *received = 0U;
    *frame = 0U;
    if (SPI_getRxFIFOStatus(SPIx) != 0U)
    {
        *frame = READ_REG(SPIx->DR[0]);
        *received = 1U;
    }
    return DRV_OK;
}

/**
 * @brief Write one FIFO entry even when TX is full, for explicit error stimulus.
 * @param SPIx SPI peripheral.
 * @param frame Input frame.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note Deliberately bypasses the normal FIFO capacity guard; does not wait.
 */
DRV_Status SPI_testWriteFIFOOnce(SPI_Type *SPIx, uint32_t frame)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx))
    {
        return DRV_PARAM_ERR;
    }
    WRITE_REG(SPIx->DR[0], frame);
    return DRV_OK;
}

/**
 * @brief Read one FIFO entry even when RX is empty, for explicit underflow stimulus.
 * @param SPIx SPI peripheral.
 * @param frame Output bus read value; not valid received data when FIFO was empty.
 * @return DRV_OK or DRV_PARAM_ERR.
 * @note Deliberately bypasses the normal FIFO occupancy guard; does not read SR.
 */
DRV_Status SPI_testReadFIFOOnce(SPI_Type *SPIx, uint32_t *frame)
{
    assert_param(IS_SPI_ALL_PERIPH(SPIx));
    if (!IS_SPI_ALL_PERIPH(SPIx) || frame == NULL)
    {
        return DRV_PARAM_ERR;
    }
    *frame = READ_REG(SPIx->DR[0]);
    return DRV_OK;
}
/********************* TEST DRIVER EXTENSION END *********************/
#endif
