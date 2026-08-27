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

#include "et6x_gpio.h"
#include "et6x_crg.h"


#define GPIO_MAX_PIN_IDX      (15)
#define REG_WIDTH_IN_BYTES    (4)
#define GPIO_MAX_SAMP_DIV     (255)
#define GPIO_REG_BASE_SIZE    (0x1000)

#define IS_GPIO_ALL_PERIPH(GPIOx) \
        ((GPIOx == GPIOA) || (GPIOx == GPIOB) || \
         (GPIOx == GPIOC) || (GPIOx == GPIOD) || \
         (GPIOx == GPIOE) || (GPIOx == GPIOF) || \
         (GPIOx == GPIOG) || (GPIOx == GPIOH))

/**
 * @brief Fill param to IOC_Init_TypeDef struct to default value
 *
 * @param cfg point to IOC_Init_TypeDef struct to initial
 */
void GPIO_initPadConfigStruct(IOC_Init_TypeDef *cfg)
{
    assert_param(cfg != NULL);

    cfg->pull = IOC_PULL_DOWN;
    cfg->scht = IOC_SCHT_DISABLE;
    cfg->ds   = IOC_DS_LEVEL_0;
    cfg->dir  = IOC_DIR_IN_OUT;
}

/**
 * @brief   IOC configure for PAD attribute
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @param cfg    pin initial param such as mode, ds, dir, pull, scht .
 * @return DRV_Status
 */
DRV_Status GPIO_setPadConfig(GPIO_PinNumber pin_number, IOC_Init_TypeDef *cfg)
{
    __IO uint32_t ioc_reg = 0,
                  idx     = 0,
                  temp    = 0;

    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));
    assert_param(cfg->ds <= IOC_DS_LEVEL_3);
    assert_param(cfg->dir <= IOC_DIR_IN_OUT);
    assert_param(cfg->pull <= IOC_PULL_UP);
    assert_param(cfg->scht <= IOC_SCHT_ENABLE);

    idx  = ((uint32_t)GPIOx - (uint32_t)GPIOA) / GPIO_REG_BASE_SIZE;
    temp = (idx > 0) ? idx * 7 * REG_WIDTH_IN_BYTES: 0;

    ioc_reg = (uint32_t)&IOMUX->GPIOA_IE_GROUP0 + temp;

    // DIR
    if (cfg->dir == IOC_DIR_IN_OUT)
    {
        SET_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
    }
    else
    {
        CLEAR_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
    }
    ioc_reg += REG_WIDTH_IN_BYTES;
    // SCHT
    if (cfg->scht == IOC_SCHT_ENABLE)
    {
        SET_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
    }
    else
    {
        CLEAR_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
    }
    ioc_reg += REG_WIDTH_IN_BYTES;
    // PULLUP
    if (cfg->pull == IOC_PULL_UP)
    {
        SET_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
    }
    else if (cfg->pull == IOC_PULL_DOWN)
    {
        SET_BIT(REG32(ioc_reg + REG_WIDTH_IN_BYTES), (uint32_t)pin_mask);
    }
    else
    {
        CLEAR_BIT(REG32(ioc_reg), (uint32_t)pin_mask);
        CLEAR_BIT(REG32(ioc_reg + REG_WIDTH_IN_BYTES), (uint32_t)pin_mask);
    }
    // DS
    ioc_reg += REG_WIDTH_IN_BYTES * 2;
    temp     = 0;
    for (idx = 0; idx <= GPIO_MAX_PIN_IDX; idx++)
    {
        if (DRV_IS_BIT_SET(pin_mask, BIT_MASK(idx)))
        {
            temp |= ((uint32_t)cfg->ds << idx * 2);
        }
    }
    REG32(ioc_reg) |= temp;

    return DRV_OK;
}

/**
 * @brief     IOC configure for Pin AF Mode
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @param mode functional mode ,available mappings are supplied in <tt>ex6x_pinmap.h</tt>
 * @return DRV_Status
 */
DRV_Status GPIO_setPinConfig(GPIO_PinNumber pin_number, uint8_t mode)
{
    __IO uint32_t ioc_reg = 0,
                  idx     = 0,
                  temp    = 0;

    GPIO_Type *GPIOx;

    GPIOx = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));
    assert_param(mode <= 15);

    idx  = ((uint32_t)GPIOx - (uint32_t)GPIOA) / GPIO_REG_BASE_SIZE;
    temp = idx * 7 * REG_WIDTH_IN_BYTES;

    ioc_reg = (uint32_t)&IOMUX->GPIOA_MODE_SEL_GROUP0 + temp;

    // MODE
    idx      = pin_number & 0x0f;
    ioc_reg += (idx / 8) * REG_WIDTH_IN_BYTES;
    idx      = (idx % 8) * 4;
    MODIFY_REG(REG32(ioc_reg), (uint32_t)0x0F << idx, (uint32_t)mode << idx);

    return DRV_OK;
}

/**
 * @brief Set GPIO Group direction to Output
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @param dir This parameter can be GPIO_DIR_IN_OUT or GPIO_DIR_OUT
 * @return DRV_Status
 */
DRV_Status GPIO_setPortDirectionMode(GPIO_PinNumber pin_number, GPIO_DIR_TypeDef dir)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    if (dir == GPIO_DIR_OUT)
    {
        WRITE_REG(GPIOx->OUTENSET, pin_mask);
    }
    else
    {
        WRITE_REG(GPIOx->OUTENCLR, pin_mask);
    }

    return DRV_OK;
}

/**
 * @brief  Read Bit Value on a GPIO pin
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return FlagStatus
 */
FlagStatus GPIO_readPin(GPIO_PinNumber pin_number)
{
    GPIO_Type  *GPIOx;
    uint32_t   pin_mask;
    FlagStatus status = RESET;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + (pin_number << 8 & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);


    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    status = ((READ_REG(GPIOx->DATA) & (pin_mask)) != 0) ? SET : RESET;
    return status;
}

/**
 * @brief Write Bit value to GPIO pin
 *
 * @param pin_number GPIO pin number
 * @param bitval SET or RESET value
 * @return DRV_Status
 */
DRV_Status GPIO_writePin(GPIO_PinNumber pin_number, FlagStatus bitval)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    if (bitval == SET)
    {
        SET_BIT(GPIOx->DATAOUT, pin_mask);
    }
    else
    {
        CLEAR_BIT(GPIOx->DATAOUT, pin_mask);
    }

    return DRV_OK;
}

/**
 * @brief  write GPIO pin with atomic access operation
 *
 * @param pin_number GPIO pin number
 * @param bitval SET or RESET value
 * @return DRV_Status
 */
DRV_Status GPIO_writePinAtomic(GPIO_PinNumber pin_number, FlagStatus bitval)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;
    uint8_t   mask_low = 0, mask_high = 0;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + (pin_number << 8 & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    mask_low  = (uint8_t)(pin_mask & 0x00FF);
    mask_high = (uint8_t)((pin_mask & 0xFF00) >> 8);

    if (bitval == RESET)
    {
        pin_mask = 0;
    }

    if (mask_low != 0)
    {
        WRITE_REG(GPIOx->MASKLOWBYTE[mask_low], (uint8_t)pin_mask);
    }
    if (mask_high != 0)
    {
        WRITE_REG(GPIOx->MASKHIGHBYTE[mask_high], (uint16_t)(pin_mask & 0xFF00));
    }
    return DRV_OK;
}

/**
 * @brief Read GPIO value on a Port
 *
 * @param GPIOx  Select the GPIO portSelect the GPIO port   [GPIOA~GPIOE]
 * @return uint16_t
 */
uint16_t GPIO_getPortPins(GPIO_Type *GPIOx)
{
    uint32_t reg_val = 0;

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    reg_val = READ_REG(GPIOx->DATA);
    return (uint16_t)(reg_val);
}

/**
 * @brief  Write GPIO value to Port
 *
 * @param GPIOx  Select the GPIO portSelect the GPIO port [GPIOA~GPIOE]
 * @param portval   value write to GPIO port
 * @return DRV_Status
 */
DRV_Status GPIO_setPortPins(GPIO_Type *GPIOx, uint16_t portval)
{
    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    WRITE_REG(GPIOx->DATAOUT, portval);

    return DRV_OK;
}

/**
 * @brief  Set GPIO port with Masked access operation
 *
 * @param GPIOx  Select the GPIO port  [GPIOA~GPIOE]
 * @param bits_set_mask   Bits Mask to Set  for example 0x8070  GPIOx_4/5/6/15 set to 1
 * @param bits_clr_mask   Bits Msk to Clear for example 0x1007  GPIOx_0/1/2/12 set to 0
 * @return DRV_Status
 */
DRV_Status GPIO_setPortPinsMasked(GPIO_Type *GPIOx, uint16_t bits_set_mask, uint16_t bits_clr_mask)
{
    uint8_t mask_low = 0, mask_high = 0;

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    mask_low  = (uint8_t)((uint16_t)(bits_set_mask | bits_clr_mask) & 0x00FF);
    mask_high = (uint8_t)((uint16_t)(((bits_set_mask | bits_clr_mask) & 0xFF00) >> 8));

    if (mask_low != 0)
    {
        WRITE_REG(GPIOx->MASKLOWBYTE[mask_low], (uint8_t)bits_set_mask);
    }
    if (mask_high != 0)
    {
        WRITE_REG(GPIOx->MASKHIGHBYTE[mask_high], (uint16_t)(bits_set_mask & 0xFF00));
    }

    return DRV_OK;
}

/**
 * @brief configure GPIO Interrupt type and polarity
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @param int_config   param for interrupt type and polarity
 * @return DRV_Status
 */
DRV_Status GPIO_setInterruptType(GPIO_PinNumber pin_number, GPIO_INT_Config_TypeDef *int_config)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(int_config != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    if (int_config->mode == GPIO_INT_TYPE_LEVEL)
    {
        WRITE_REG(GPIOx->INTTYPECLR, pin_mask);
    }
    else
    {
        WRITE_REG(GPIOx->INTTYPESET, pin_mask);
    }

    if (int_config->polarity == GPIO_INT_POL_LOW_FALLING)
    {
        WRITE_REG(GPIOx->INTPOLCLR, pin_mask);
    }
    else
    {
        WRITE_REG(GPIOx->INTPOLSET, pin_mask);
    }

    return DRV_OK;
}

/**
 * @brief Enable GPIO Interrupt
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return DRV_Status
 */
DRV_Status GPIO_enableInterrupt(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    WRITE_REG(GPIOx->INTENSET, pin_mask);

    return DRV_OK;
}

/**
 * @brief Disable GPIO Interrupt
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return DRV_Status
 */
DRV_Status GPIO_disableInterrupt(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    WRITE_REG(GPIOx->INTENCLR, pin_mask);

    return DRV_OK;
}

/**
 * @brief Clear GPIO Interrupt Status
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return DRV_Status
 */
DRV_Status GPIO_clearInterruptStatus(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    WRITE_REG(GPIOx->INTCLEAR, pin_mask);
    return DRV_OK;
}

/**
 * @brief  Get GPIO Pin Interrupt Status
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return ITStatus
 */
ITStatus GPIO_getInterruptStatus(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;
    uint16_t  temp   = 0;
    ITStatus  status = RESET;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    temp   = (uint16_t)READ_REG(GPIOx->INTSTATUS);
    status = ((temp & pin_mask) == 0) ? RESET : SET;
    return status;
}

/**
 * @brief Configure GPIO Input Filter Sample Div
 *
 * @param filter_group  GPIO filter group \b IOC_FilterGroup
 * @param samp_div      GPIO filter sample div, The configuration value range is from 0 to 255
 *  - samp_div: 0 ~ div1
 *  - samp_div: 1 ~ div2
 *  - samp_div: 2 ~ div4
 *  ...
 *  - samp_div: 255 ~ div510
 * @return DRV_Status
 */
DRV_Status GPIO_setFilterSampDiv(IOC_FilterGroup filter_group, uint32_t samp_div)
{
    __IO uint32_t ioc_reg = 0, temp = 0;
    uint32_t      offset;

    assert_param(samp_div <= GPIO_MAX_SAMP_DIV);

    offset  = (filter_group & 0x03) * 8;
    ioc_reg = (uint32_t)&IOMUX->FLT_DIV0 + (filter_group >> 2);

    temp = (REG32(ioc_reg) & ~(0xffU << offset)) | (samp_div << offset);

    WRITE_REG(REG32(ioc_reg), temp);

    return DRV_OK;
}

/**
 * @brief Configure GPIO Filter Mode
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @param filter_mode  GPIO input filter mode \b IOC_GPIOInputFilterMode
 * @return DRV_Status
 */
DRV_Status GPIO_setFilterMode(GPIO_PinNumber pin_number, IOC_GPIOInputFilterMode filter_mode)
{
    __IO uint32_t ioc_reg = 0,
                  idx     = 0,
                  temp    = 0;
    uint32_t offset;

    idx    = (pin_number >> 4) & 0x0f;
    offset = (pin_number & 0x0f) * 2;

    ioc_reg = (uint32_t)(&IOMUX->FLT_SEL0 + idx);

    temp = (REG32(ioc_reg) & ~(0x3U << offset)) | ((uint32_t)filter_mode << offset);

    WRITE_REG(REG32(ioc_reg), temp);

    return DRV_OK;
}

/**
 * @brief reset GPIO Module to default value
 *
 * @param GPIOx  Select the GPIO port  [GPIOA~GPIOE]
 * @return DRV_Status
 */
DRV_Status GPIO_resetPort(GPIO_Type *GPIOx)
{
    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    WRITE_REG(GPIOx->INTENCLR, 0xFFFF);
    WRITE_REG(GPIOx->INTTYPECLR, 0xFFFF);
    WRITE_REG(GPIOx->INTPOLCLR, 0xFFFF);
    WRITE_REG(GPIOx->OUTENCLR, 0xFFFF);

    return DRV_OK;
}

/**
 * @brief  Toggle pin output state  base on current pin state
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return DRV_Status
 */
DRV_Status GPIO_togglePin(GPIO_PinNumber pin_number)
{
    uint32_t val = 0;

    GPIO_Type *GPIOx;
    uint16_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = (uint16_t)BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    val = READ_REG(GPIOx->DATAOUT);

    if (val & pin_mask)
    {
        CLEAR_BIT(GPIOx->DATAOUT, pin_mask);
    }
    else
    {
        SET_BIT(GPIOx->DATAOUT, pin_mask);
    }

    return DRV_OK;
}

/**
 * @brief  Toggle pin output state with atomic access operation
 *
 * @param pin_number    The number enumerated in the enumeration type
 * @return DRV_Status
 */
DRV_Status GPIO_togglePinAtomic(GPIO_PinNumber pin_number)
{
    uint32_t val = 0;

    GPIO_Type *GPIOx;
    uint16_t  pin_mask;
    uint8_t   mask_low = 0, mask_high = 0;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = (uint16_t)BIT_MASK(pin_number & 0x0f);

    assert_param(GPIOx != NULL);
    assert_param(IS_GPIO_ALL_PERIPH(GPIOx));

    mask_low  = (uint8_t)(pin_mask & 0x00FF);
    mask_high = (uint8_t)((pin_mask & 0xFF00) >> 8);

    val = READ_REG(GPIOx->DATAOUT);

    if (val & pin_mask)
    {
        pin_mask = 0;
    }

    if (mask_low != 0)
    {
        WRITE_REG(GPIOx->MASKLOWBYTE[mask_low], (uint8_t)pin_mask);
    }
    if (mask_high != 0)
    {
        WRITE_REG(GPIOx->MASKHIGHBYTE[mask_high], (uint16_t)(pin_mask & 0xFF00));
    }

    return DRV_OK;
}
