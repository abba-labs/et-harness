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

#include "et6x.h"
#include "et6x_spi.h"
#include "et6x_qspi.h"

/* max number of data frames to be continuously received by QSPI */
#define MAX_NDF             (0xFFFFUL)
#define MAX_DUMMY_CYCLES    ((uint32_t)0X1F)
#define IS_DUMMY_CYCLES(cycles)              ((uint32_t)cycles < MAX_DUMMY_CYCLES)

#define _QSPI_GET_FLAG(__FLAG__)             (((QSPI->SR) & (__FLAG__)) == (__FLAG__))
#define IS_QSPI_INTERRUPT_FLGAS(flags)       ((flags &QSPI_INTERRUPT_ALL) != 0)
#define IS_APPLICABLE_ENHANCED_MODE(mode)    ((mode == SPI_TRANSMIT) || (mode == SPI_RECEIVE))

/*! Check if the SPI FIFO depth is valid */
#define IS_QSPI_FIFO_THRESHOLD(threshold)    (threshold <= QSPI_MAX_FIFO_DEPTH)


/**
 * @brief call this function to default assign value to initialization structure
 *
 * @param init pointer to initialization structure
 */
void QSPI_structInit(QSPI_Init_TypeDef *init)
{
    memset(init, 0x0, sizeof(QSPI_Init_TypeDef));
    init->dataFrameSize  = 0x7;
    init->transferMode   = SPI_EEPROM_READ;
    init->clkPolarity    = 0x0;
    init->clkPhase       = 0x0;
    init->clkDiv         = 0x64;
    init->transmitTL     = 16;
    init->receiveTL      = 16;
    init->instructionLen = INSTRCTION_8_BIT;
}

/**
 * @brief Initialization of QSPI interface,there are only one QSPI interface in ET6003
 *
 * @param init struct which Contains parameters to initialize
 * @return DRV_Status init operation ok or not
 */
DRV_Status QSPI_init(QSPI_Init_TypeDef *init)
{
    uint32_t tempReg = 0;

    assert_param(init != NULL);
    assert_param(IS_QSPI_FIFO_THRESHOLD(init->transmitTL));
    assert_param(IS_QSPI_FIFO_THRESHOLD(init->transmitSL));
    assert_param(IS_QSPI_FIFO_THRESHOLD(init->receiveTL));
    assert_param(init->readDataNum <= MAX_NDF);

    /* If the qspi is enabled, disable it by writing 0 to the SSI Enable register (SSIENR) */
    WRITE_REG(QSPI->SSIENR, 0);

    /* Set up the qspi control registers for the transfer; these registers can be set in any order */
    WRITE_REG(tempReg, (uint32_t)init->dataFrameSize << QSPI_CTRLR0_DFS_Pos);
    SET_BIT(tempReg, (uint32_t)init->transferMode << QSPI_CTRLR0_TMOD_Pos);
    SET_BIT(tempReg, (uint32_t)init->qspiFrameFormat << QSPI_CTRLR0_SPI_FRF_Pos);
    SET_BIT(tempReg, (uint32_t)init->clkPolarity << QSPI_CTRLR0_SCPOL_Pos);
    SET_BIT(tempReg, (uint32_t)init->clkPhase << QSPI_CTRLR0_SCPH_Pos);

    if (init->slaveSelectToggle)
    {
        SET_BIT(tempReg, QSPI_CTRLR0_SSTE_Msk);
    }
    else
    {
        CLEAR_BIT(tempReg, QSPI_CTRLR0_SSTE_Msk);
    }

    WRITE_REG(QSPI->CTRLR0, tempReg);
    WRITE_REG(QSPI->CTRLR1, init->readDataNum);

    /*  Write the Baud Rate Select Register (BAUDR) to set the baud rate for the transfer */
    WRITE_REG(QSPI->BAUDR, init->clkDiv);

    /* Write the Transmit and Receive FIFO Threshold Level registers */
    tempReg = (init->transmitSL << SPI0_TXFTLR_TXFTHR_Pos) | (init->transmitTL << SPI0_TXFTLR_TFT_Pos);
    WRITE_REG(QSPI->TXFTLR, tempReg);
    WRITE_REG(QSPI->RXFTLR, init->receiveTL);

    /* mask all interrupt */
    CLEAR_BIT(QSPI->IMR, QSPI_INTERRUPT_ALL);

    /* write SPI_CTRLR0 */
    tempReg = 0;
    assert_param(IS_DUMMY_CYCLES(init->dummyCycles));
    SET_BIT(tempReg, (uint32_t)init->dummyCycles << QSPI_SPI_CTRLR0_WAIT_CYCLES_Pos);
    SET_BIT(tempReg, (uint32_t)init->instructionLen << QSPI_SPI_CTRLR0_INST_L_Pos);
    SET_BIT(tempReg, (uint32_t)init->addrLen << QSPI_SPI_CTRLR0_ADDR_L_Pos);
    SET_BIT(tempReg, (uint32_t)init->transType);
    WRITE_REG(QSPI->SPI_CTRLR0, tempReg);

    WRITE_REG(QSPI->RX_SAMPLE_DELAY, init->rxSampleDelay);

    WRITE_REG(QSPI->SER, QSPI_SER_SER_Msk);
    /* enable spi */
    WRITE_REG(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);

//    NVIC_EnableIRQ((IRQn_Type)QSPI_IRQn);

    return DRV_OK;
}

/**
 * @brief Set FIFO interrupt thresholds for transmit and receive
 *
 * @param txLevel Transmit FIFO interrupt threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 * @param rxLevel Receive FIFO interrupt threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 *
 * @note Threshold values are checked by IS_SPI_FIFO_THRESHOLD macro to ensure they are less than SPI_MAX_FIFO_DEPTH
 */
void QSPI_setFIFOInterruptLevel(uint8_t txLevel, uint8_t rxLevel)
{
    assert_param(IS_QSPI_FIFO_THRESHOLD(txLevel));
    assert_param(IS_QSPI_FIFO_THRESHOLD(rxLevel));

    MODIFY_REG(QSPI->TXFTLR, QSPI_TXFTLR_TFT_Msk, (uint32_t)txLevel << QSPI_TXFTLR_TFT_Pos);
    MODIFY_REG(QSPI->RXFTLR, QSPI_RXFTLR_RFT_Msk, (uint32_t)rxLevel << QSPI_RXFTLR_RFT_Pos);
}

/**
 * @brief get FIFO interrupt level
 *
 * @param txLevel Transmit FIFO interrupt threshold
 * @param rxLevel Receive FIFO interrupt threshold
 */
void QSPI_getFIFOInterruptLevel(uint8_t *txLevel, uint8_t *rxLevel)
{
    *txLevel = (uint8_t)READ_REG(QSPI->TXFTLR);
    *rxLevel = (uint8_t)READ_REG(QSPI->RXFTLR);
}

/**
 * @brief Set Transfer start FIFO level
 *
 * @param startLevel Transfer start FIFO threshold (valid range: 0 to SPI_MAX_FIFO_DEPTH)
 *
 * @note Threshold values are checked by IS_SPI_FIFO_THRESHOLD macro to ensure they are less than SPI_MAX_FIFO_DEPTH
 */
void QSPI_setTansferStartFIFOLevel(uint8_t startLevel)
{
    assert_param(IS_QSPI_FIFO_THRESHOLD(startLevel));

    MODIFY_REG(QSPI->TXFTLR, QSPI_TXFTLR_TXFTHR_Msk, (uint32_t)startLevel << QSPI_TXFTLR_TXFTHR_Pos);
}

/**
 * @brief get FIFO interrupt level
 *
 * @param txLevel Transmit FIFO interrupt threshold
 * @param rxLevel Receive FIFO interrupt threshold
 */
void QSPI_getTansferStartFIFOLevel(SPI_Type *SPIx, uint8_t *txLevel)
{
    *txLevel = (uint8_t)(READ_REG(SPIx->TXFTLR) & QSPI_TXFTLR_TXFTHR_Msk >> QSPI_TXFTLR_TXFTHR_Pos);
}

/**
 * @brief reset fifo
 *
 */
void QSPI_resetFIFO(void)
{
    if (READ_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
        SET_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
    }
}

/**
 * @brief transmit instruction address
 *
 * @param instruction
 * @param address
 * @note not Applicable in SPI_TRANSMIT_RECEIVE and SPI_EEPROM_READ mode
 * @return DRV_Status return transmit ok or error
 */
DRV_Status QSPI_transmitInstAddr(uint32_t instruction, uint64_t address)
{
    uint8_t instruction_len = 0;
    uint8_t address_len     = 0;
    uint8_t transferMode    = 0;

    transferMode = READ_BIT(QSPI->CTRLR0, QSPI_CTRLR0_TMOD_Msk) >> QSPI_CTRLR0_TMOD_Pos;
    assert_param(IS_APPLICABLE_ENHANCED_MODE(transferMode));

    instruction_len = (READ_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_INST_L_Msk) >> QSPI_SPI_CTRLR0_INST_L_Pos);
    address_len     = (READ_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_ADDR_L_Msk) >> QSPI_SPI_CTRLR0_ADDR_L_Pos);
    if ((address_len | instruction_len) == 0)
    {
        return DRV_ERROR;
    }
    /* write  Instruction */
    if (instruction_len != INSTRCTION_0_BIT)
    {
        QSPI->DR[0] = instruction;
    }
    /* write  Address  */
    if (address_len != ADDR_0_BIT)
    {
        QSPI->DR[0] = (uint32_t)address;

        if (address_len > ADDR_32_BIT)
        {
            QSPI->DR[0] = (uint32_t)(address >> 32);
        }
    }
    return DRV_OK;
}

/**
 * @brief transmit in poll mode
 *
 * @param pData data you want to transmit
 * @param size transmit data size
 * @return DRV_Status return transmit ok or not
 */
DRV_Status QSPI_transmitData(void *pData, uint16_t size)
{
    uint32_t i = 0;

    assert_param(pData != NULL);
    assert_param(size != 0);

    if ((READ_BIT(QSPI->CTRLR0, QSPI_CTRLR0_DFS_Msk) >> QSPI_CTRLR0_DFS_Pos) == DATA_FRAME_SIZE_8_BIT)
    {
        for (i = 0; i < size; i++)
        {
            QSPI->DR[0] = ((uint8_t *)pData)[i];
            while (READ_BIT(QSPI->SR, QSPI_SR_TFNF_Msk) == 0);
        }
    }
    else if ((READ_BIT(QSPI->CTRLR0, QSPI_CTRLR0_DFS_Msk) >> QSPI_CTRLR0_DFS_Pos) == DATA_FRAME_SIZE_16_BIT)
    {
        for (i = 0; i < size; i++)
        {
            QSPI->DR[0] = ((uint16_t *)pData)[i];
            while (READ_BIT(QSPI->SR, QSPI_SR_TFNF_Msk) == 0);
        }
    }
    else
    {
        for (i = 0; i < size; i++)
        {
            QSPI->DR[0] = ((uint32_t *)pData)[i];
            while (READ_BIT(QSPI->SR, QSPI_SR_TFNF_Msk) == 0);
        }
    }

    return DRV_OK;
}

/**
 * @brief QSPI receive data in poll mode
 *
 * @param pData buffer to receive data
 * @param size receive data size
 * @return DRV_Status
 */
DRV_Status QSPI_receive(void *pData, uint16_t size)
{
    uint32_t i = 0;

    assert_param(pData != NULL);
    assert_param(size != 0);

    /* FIFO depth is 32 */
    if ((READ_BIT(QSPI->CTRLR0, QSPI_CTRLR0_DFS_Msk) >> QSPI_CTRLR0_DFS_Pos) == DATA_FRAME_SIZE_8_BIT)
    {
        uint8_t *p = (uint8_t *)pData;
        for (i = 0; i < size; i++)
        {
            while (!(QSPI->RXFLR > 0 && _QSPI_GET_FLAG(QSPI_SR_RFNE_Msk)));
            p[i] = (uint8_t)(QSPI->DR[0]);
        }
    }
    else if ((READ_BIT(QSPI->CTRLR0, QSPI_CTRLR0_DFS_Msk) >> QSPI_CTRLR0_DFS_Pos) == DATA_FRAME_SIZE_16_BIT)
    {
        uint16_t *p = (uint16_t *)pData;
        for (i = 0; i < size; i++)
        {
            while (!(QSPI->RXFLR > 0 && _QSPI_GET_FLAG(QSPI_SR_RFNE_Msk)));
            p[i] = (uint16_t)(QSPI->DR[0]);
        }
    }
    else
    {
        uint32_t *p = (uint32_t *)pData;
        for (i = 0; i < size; i++)
        {
            while (!(QSPI->RXFLR > 0 && _QSPI_GET_FLAG(QSPI_SR_RFNE_Msk)));
            p[i] = QSPI->DR[0];
        }
    }

    return DRV_OK;
}

/**
 * @brief Set the number of data frames to be continuously received by QSPI,
 *        when When TMOD = 10 or TMOD = 11
 *
 * @param number
 */
void QSPI_setReadDataNum(uint32_t number)
{
    assert_param(number <= MAX_NDF);
    WRITE_REG(QSPI->CTRLR1, number);
}

/**
 * @brief Set the number of bits of data transmitted by each DR and FIFO
 *
 * @param len can be any number in QSPI_DataLengthType
 */
void QSPI_setDataFrameSize(SPI_DATA_FRAMESIZE_TypeDef frameSize)
{
    /* clear SPI_FRF bits */
    CLEAR_BIT(QSPI->CTRLR0, QSPI_CTRLR0_DFS_Msk);

    /* set SPI_FRF bits */
    SET_BIT(QSPI->CTRLR0, (uint32_t)frameSize << QSPI_CTRLR0_DFS_Pos);
}

/**
 * @brief Set the mode of QSPI,include standard,Dual,Quad mode
 *
 * @param frameFormate
 */
void QSPI_setQSPIFrameFormat(QSPI_FRAME_FORMAT_TypeDef frameFormat)
{
    /* clear SPI_FRF bits */
    CLEAR_BIT(QSPI->CTRLR0, QSPI_CTRLR0_SPI_FRF_Msk);

    /* set SPI_FRF bits */
    SET_BIT(QSPI->CTRLR0, (uint32_t)frameFormat << QSPI_CTRLR0_SPI_FRF_Pos);
}

/**
 * @brief Number of wait cycles in Dual/Quad/Octal mode between control frames transmit and data reception
 *
 * @param dummyCycles This value is specified as number of SPI clock cycles
 */
void QSPI_setDummyCycles(uint32_t dummyCycles)
{
    assert_param(IS_DUMMY_CYCLES(dummyCycles));

    /* clear wait cycles bits */
    CLEAR_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_WAIT_CYCLES_Msk);

    /* set wait cycles bits */
    SET_BIT(QSPI->SPI_CTRLR0, dummyCycles << QSPI_SPI_CTRLR0_WAIT_CYCLES_Pos);
}

/**
 * @brief Dual/Quad/Octal mode instruction length in bits.
 *
 * @param len Length of instruction
 */
void QSPI_setInstructionSize(QSPI_INSTRUCTION_BITS_TypeDef len)
{
    /* clear instruction length bits */
    CLEAR_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_INST_L_Msk);

    /* set instruction length bits */
    SET_BIT(QSPI->SPI_CTRLR0, (uint32_t)len << QSPI_SPI_CTRLR0_INST_L_Pos);
}

/**
 * @brief Set the bits of Address to be transmitted Only after this set,
 *        much bits are programmed in to the FIFO, the transfer can begin.
 *
 * @param len Address bits to be set
 */
void QSPI_setAddressSize(QSPI_ADDRESS_BITS_TypeDef len)
{
    /* clear instruction length bits */
    CLEAR_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_ADDR_L_Msk);

    /* set instruction length bits */
    SET_BIT(QSPI->SPI_CTRLR0, (uint32_t)len << QSPI_SPI_CTRLR0_ADDR_L_Pos);
}

/**
 * @brief Selects whether QSPI will transmit instruction/address either in
 *        Standard SPI mode or the SPI mode selected in CTRLR0.SPI_FRF field. 00
 *        - Instruction and Address will be sent in Standard SPI Mode.
 *        01 - Instruction will be sent in Standard SPI Mode and Address will be
 *        sent in the mode specified by CTRLR0.SPI_FRF.10 - Both Instruction and
 *        Address will be sent in the mode specified by SPI_FRF. 11 - Reserved
 *
 * @param transType
 */
void QSPI_setInstructionAddressMode(QSPI_INSTRCTION_ADDRESS_MODE_TypeDef transType)
{
    /* clear address and instruction transfer format bits */
    CLEAR_BIT(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_TRANS_TYPE_Msk);

    /* set address and instruction transfer format bits */
    SET_BIT(QSPI->SPI_CTRLR0, transType);
}

/**
 * @brief Mask QSPI interrupt
 *
 * @param intType
 */
void QSPI_disableInterrupt(uint32_t intType)
{
    CLEAR_BIT(QSPI->IMR, intType);
}

/**
 * @brief Unmask QSPI interrupt
 *
 * @param intType
 */
void QSPI_enableInterrupt(uint32_t intType)
{
    SET_BIT(QSPI->IMR, intType);
}

/**
 * @brief clear interrupt status
 *
 * @param intFlags parameters are the same as those used in SPI_enableInterrupt.
 */
void QSPI_clearInterruptStatus(uint32_t intFlags)
{
    uint32_t tempReg = 0;

    assert_param(IS_QSPI_INTERRUPT_FLGAS(intFlags));

    if ((intFlags & (QSPI_IMR_TXOIM_Msk | QSPI_IMR_TXUIM_Msk)) != 0)
    {
        tempReg = READ_REG(QSPI->TXEICR);
    }
    if ((intFlags & QSPI_IMR_RXOIM_Msk) != 0)
    {
        tempReg = READ_REG(QSPI->RXOICR);
    }
    if ((intFlags & QSPI_IMR_RXUIM_Msk) != 0)
    {
        tempReg = READ_REG(QSPI->RXUICR);
    }
    if ((intFlags & QSPI_IMR_MSTIM_Msk) != 0)
    {
        tempReg = READ_REG(QSPI->MSTICR);
    }
    if ((intFlags & QSPI_IMR_SPITEM_Msk) != 0)
    {
        tempReg = READ_REG(QSPI->SPITECR);
    }
    if ((intFlags & QSPI_IMR_TXEIM_Msk) != 0)
    {
        /* auto cleared by hardware when write data to tx fifo */
    }
    if ((intFlags & QSPI_IMR_RXFIM_Msk) != 0)
    {
        /* auto cleared by hardware when read data from rx fifo */
    }
    UNUSED(tempReg);
}

/**
 * @brief open QSPI
 *
 */
void QSPI_enable(void)
{
    SET_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
}

/**
 * @brief Close QSPI
 *
 */
void QSPI_disable(void)
{
    CLEAR_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
}

/**
 * @brief Get the status of QSPI
 *
 * @return uint32_t
 */
uint32_t QSPI_getStatus(void)
{
    return QSPI->SR;
}

/**
 * @brief get spi is busy or not
 *
 * @return true if SPI is busy, false otherwise
 */
bool QSPI_isBusy(void)
{
    return READ_BIT(QSPI->SR, QSPI_SR_BUSY_Msk) != 0;
}

/**
 * @brief Get the status of the QSPI interrupts after they have been masked
 *
 * @return uint32_t
 */
uint32_t QSPI_getInterruptStatus(void)
{
    return QSPI->ISR;
}

/**
 * @brief Get the status of the DW_apb_ssi interrupts prior to masking
 *
 * @return uint32_t
 */
uint32_t QSPI_getRawInterruptStatus(void)
{
    return QSPI->RISR;
}

/**
 * @brief set Transmit Data Level.
 *
 * @param level Transmit Data Level.
 */
void QSPI_setDMATransmitDataLevel(uint8_t level)
{
    assert_param(IS_QSPI_FIFO_THRESHOLD(level));
    WRITE_REG(QSPI->DMATDLR, level);
}

/**
 * @brief set Transmit Data Level.
 *
 * @param level Transmit Data Level.
 */
void QSPI_setDMARecevieDataLevel(uint8_t level)
{
    assert_param(IS_QSPI_FIFO_THRESHOLD(level));
    WRITE_REG(QSPI->DMARDLR, level);
}

/**
 * @brief enable DMA interface
 *
 */
void QSPI_enableDMA(void)
{
    if (QSPI->SSIENR == 1)
    {
        WRITE_REG(QSPI->SSIENR, 0);
        SET_BIT(QSPI->DMACR, QSPI_DMACR_RDMAE_Msk | QSPI_DMACR_TDMAE_Msk);
        WRITE_REG(QSPI->SSIENR, 1);
    }
    else
    {
        SET_BIT(QSPI->DMACR, QSPI_DMACR_RDMAE_Msk | QSPI_DMACR_TDMAE_Msk);
    }
}

/**
 * @brief disable DMA interface
 *
 */
void QSPI_disableDMA(void)
{
    if (QSPI->SSIENR == 1)
    {
        WRITE_REG(QSPI->SSIENR, 0);
        CLEAR_BIT(QSPI->DMACR, QSPI_DMACR_RDMAE_Msk | QSPI_DMACR_TDMAE_Msk);
        WRITE_REG(QSPI->SSIENR, 1);
    }
    else
    {
        CLEAR_BIT(QSPI->DMACR, QSPI_DMACR_RDMAE_Msk | QSPI_DMACR_TDMAE_Msk);
    }
}

/**
 * @brief configure XIP
 *
 * @param conf struct which Contains parameters to initialize
 * @return DRV_Status init operation ok or not
 * @note must be used when the QSPI is disabled.
 */
DRV_Status QSPI_configXIP(XIP_conf_TypeDef *conf)
{
    uint32_t tempReg = 0;

    SET_BIT(tempReg, (uint32_t)conf->instructionEnable << QSPI_SPI_CTRLR0_XIP_INST_EN_Pos);
    SET_BIT(tempReg, (uint32_t)conf->continuousTransferEnable << QSPI_SPI_CTRLR0_SSIC_XIP_CONT_XFER_EN_Pos);
    SET_BIT(tempReg, (uint32_t)conf->modeBitLength << QSPI_SPI_CTRLR0_XIP_MBL_Pos);
    SET_BIT(tempReg, (uint32_t)conf->modeBitsEnable << QSPI_SPI_CTRLR0_XIP_MD_BIT_EN_Pos);
    SET_BIT(tempReg, QSPI_SPI_CTRLR0_XIP_DFS_HC_Msk);

    WRITE_REG(QSPI->SSIENR, 0);
    MODIFY_REG(QSPI->SPI_CTRLR0, QSPI_SPI_CTRLR0_XIP_INST_EN_Msk |
               QSPI_SPI_CTRLR0_SSIC_XIP_CONT_XFER_EN_Msk |
               QSPI_SPI_CTRLR0_XIP_MBL_Msk |
               QSPI_SPI_CTRLR0_XIP_MD_BIT_EN_Msk,
               tempReg);

    WRITE_REG(QSPI->XIP_MODE_BITS, conf->modeBitsVale);
    WRITE_REG(QSPI->SSIENR, 1);
    return DRV_OK;
}

/*!
 * @brief set INCR transfer code
 *
 * @param code: Specifies the INCR transfer code
 *
 */
void QSPI_setINCRTransferCode(uint16_t code)
{
    if (QSPI->SSIENR == 1)
    {
        WRITE_REG(QSPI->SSIENR, 0);
        WRITE_REG(QSPI->XIP_INCR_INST, code);
        WRITE_REG(QSPI->SSIENR, 1);
    }
    else
    {
        WRITE_REG(QSPI->XIP_INCR_INST, code);
    }
}

/*!
 * @brief set WRAP transfer code
 *
 * @param code: Specifies the WRAP transfer code
 *
 */
void QSPI_setWRAPTransferCode(uint16_t code)
{
    if (QSPI->SSIENR == 1)
    {
        WRITE_REG(QSPI->SSIENR, 0);
        WRITE_REG(QSPI->XIP_WRAP_INST, code);
        WRITE_REG(QSPI->SSIENR, 1);
    }
    else
    {
        WRITE_REG(QSPI->XIP_WRAP_INST, code);
    }
}

/**
 * @brief set the selected chip signal to retain LOW
 *
 */
void QSPI_setCSLow(void)
{
    if (READ_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
        SET_BIT(QSPI->CTRLR0, QSPI_CTRLR0_SPI_SOFT_MODE_Msk);
        SET_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        SET_BIT(QSPI->CTRLR0, QSPI_CTRLR0_SPI_SOFT_MODE_Msk);
    }
}

/**
 * @brief set the selected chip signal to retain HIGH
 *
 */
void QSPI_setCSHigh(void)
{
    if (READ_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk) != 0)
    {
        CLEAR_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
        CLEAR_BIT(QSPI->CTRLR0, QSPI_CTRLR0_SPI_SOFT_MODE_Msk);
        SET_BIT(QSPI->SSIENR, QSPI_SSIENR_SSIC_EN_Msk);
    }
    else
    {
        CLEAR_BIT(QSPI->CTRLR0, QSPI_CTRLR0_SPI_SOFT_MODE_Msk);
    }
}
