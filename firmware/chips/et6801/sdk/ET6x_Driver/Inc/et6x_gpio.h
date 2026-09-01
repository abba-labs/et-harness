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

#ifndef __ET6X_GPIO_H
#define __ET6X_GPIO_H

#include "et6x.h"
#include "et6x_pinmap.h"

#ifdef __cplusplus
extern "C"
{
#endif

/** @addtogroup ET6801_Driver
 * @{
 */

/** @addtogroup GPIO
 * @{
 */

/**
 * @brief GPIO DIR enumeration
 */

#define GPIO_BASE    GPIOA_BASE

/**
 * @brief Pin Definition Enumeration
 */
typedef enum
{
    /* GPIOA Group */
    GPIO0,
    GPIO1,
    GPIO2,
    GPIO3,
    GPIO4,
    GPIO5,
    GPIO6,
    GPIO7,
    GPIO8,
    GPIO9,
    GPIO10,
    GPIO11,
    GPIO12,
    GPIO13,
    GPIO14,
    GPIO15,
    /* GPIOB Group */
    GPIO16,
    GPIO17,
    GPIO18,
    GPIO19,
    GPIO20,
    GPIO21,
    GPIO22,
    GPIO23,
    GPIO24,
    GPIO25,
    GPIO26,
    GPIO27,
    GPIO28,
    GPIO29,
    GPIO30,
    GPIO31,
    /* GPIOC Group */
    GPIO32,
    GPIO33,
    GPIO34,
    GPIO35,
    GPIO36,
    GPIO37,
    GPIO38,
    GPIO39,
    GPIO40,
    GPIO41,
    GPIO42,
    GPIO43,
    GPIO44,
    GPIO45,
    GPIO46,
    GPIO47,
    /* GPIOD Group */
    GPIO48,
    GPIO49,
    GPIO50,
    GPIO51,
    GPIO52,
    GPIO53,
    GPIO54,
    GPIO55,
    GPIO56,
    GPIO57,
    GPIO58,
    GPIO59,
    GPIO60,
    GPIO61,
    GPIO62,
    GPIO63,
    /* GPIOE Group */
    GPIO64,
    GPIO65,
    GPIO66,
    GPIO67,
    GPIO68,
    GPIO69,
    GPIO70,
    GPIO71,
    GPIO72,
    GPIO73,
    GPIO74,
    GPIO75,
    GPIO76,
    GPIO77,
    GPIO78,
    GPIO79,
    /* GPIOF Group */
    GPIO80,
    GPIO81,
    GPIO82,
    GPIO83,
    GPIO84,
    GPIO85,
    GPIO86,
    GPIO87,
    GPIO88,
    GPIO89,
    GPIO90,
    GPIO91,
    GPIO92,
    GPIO93,
    GPIO94,
    GPIO95,
    /* GPIOG Group */
    GPIO96,
    GPIO97,
    GPIO98,
    GPIO99,
    GPIO100,
    GPIO101,
    GPIO102,
    GPIO103,
    GPIO104,
    GPIO105,
    GPIO106,
    GPIO107,
    GPIO108,
    GPIO109,
    GPIO110,
    GPIO111,
    GPIO112,
    GPIO113,
    /* GPIOH Group */
    GPIO114,
    GPIO115,
    GPIO116,
    GPIO117,
    GPIO118, // TDI
    GPIO119, // TDO_SWO
    GPIO120,
    GPIO121, //SWCLK_TCK
    GPIO122, //SWDIO_TMS
    GPIO124, //XTAL_IN
    GPIO125  //XTAL_OUT
} GPIO_PinNumber;

typedef enum
{
    GPIO_DIR_IN  = 0x01,        /*!< GPIO Dir Input Only  */
    GPIO_DIR_OUT = 0x00         /*!< GPIO Dir Output Only */
} GPIO_DIR_TypeDef;

/**
 * @brief GPIO Interrupt type enumeration
 */
typedef enum
{
    GPIO_INT_TYPE_LEVEL = 0x00,      /*!< GPIO Interrupt type level  */
    GPIO_INT_TYPE_EDGE  = 0x01       /*!< GPIO Interrupt type edge  */
} GPIO_INT_TYPE_TypeDef;

/**
 * @brief GPIO Interrupt polarity enumeration
 */
typedef enum
{
    GPIO_INT_POL_HIGH_RISING = 0x00,     /*!< GPIO Interrupt polarity high level  or rising edge */
    GPIO_INT_POL_LOW_FALLING = 0x01      /*!< GPIO Interrupt polarity low level or falling edge  */
} GPIO_INT_POL_TypeDef;

/**
 * @brief GPIO Debounce mode enumeration
 */
typedef enum
{
    GPIO_DB_EDGE_SINGLE = 0x00,     /*!< GPIO debounce single edge filter */
    GPIO_DB_EDGE_DOUBLE = 0x01      /*!< GPIO debounce double edge filter */
} GPIO_DB_MODE_TypeDef;

/**
 * @brief GPIO Debounce single edge polarity enumeration
 */
typedef enum
{
    GPIO_DB_POL_HIGH = 0x00,    /*!< GPIO debounce high level glitch filter */
    GPIO_DB_POL_LOW  = 0x01     /*!< GPIO debounce low  level glitch filter */
} GPIO_DB_POL_TypeDef;

/**
 * @brief IOC Filter prescaler group enumeration
 *
 */
typedef enum
{
    IOC_FILTER_GPIOA_0,         /*!< IOC Filter prescaler group GPIOA_0 */
    IOC_FILTER_GPIOA_1,         /*!< IOC Filter prescaler group GPIOA_1 */
    IOC_FILTER_GPIOB_0,         /*!< IOC Filter prescaler group GPIOB_0 */
    IOC_FILTER_GPIOB_1,         /*!< IOC Filter prescaler group GPIOB_1 */
    IOC_FILTER_GPIOC_0,         /*!< IOC Filter prescaler group GPIOC_0 */
    IOC_FILTER_GPIOC_1,         /*!< IOC Filter prescaler group GPIOC_1 */
    IOC_FILTER_GPIOD_0,         /*!< IOC Filter prescaler group GPIOD_0 */
    IOC_FILTER_GPIOD_1,         /*!< IOC Filter prescaler group GPIOD_1 */
    IOC_FILTER_GPIOE_0,         /*!< IOC Filter prescaler group GPIOE_0 */
    IOC_FILTER_GPIOE_1,         /*!< IOC Filter prescaler group GPIOE_1 */
    IOC_FILTER_GPIOF_0,         /*!< IOC Filter prescaler group GPIOF_0 */
    IOC_FILTER_GPIOF_1,         /*!< IOC Filter prescaler group GPIOF_1 */
    IOC_FILTER_GPIOG_0,         /*!< IOC Filter prescaler group GPIOG_0 */
    IOC_FILTER_GPIOG_1,         /*!< IOC Filter prescaler group GPIOG_1 */
    IOC_FILTER_GPIOH_0,         /*!< IOC Filter prescaler group GPIOH_0 */
    IOC_FILTER_GPIOH_1          /*!< IOC Filter prescaler group GPIOH_1 */
} IOC_FilterGroup;

/**
 * @brief IO Drive Strength enumeration
 */
typedef enum
{
    IOC_DS_LEVEL_0 = 0x00,     /*!< IO drive strength level very low */
    IOC_DS_LEVEL_1 = 0x01,     /*!< IO drive strength level low */
    IOC_DS_LEVEL_2 = 0x02,     /*!< IO drive strength level medium */
    IOC_DS_LEVEL_3 = 0x03      /*!< IO drive strength level High */
} IOC_DS_LEVEL_TypeDef;

/**
 * @brief IO pull-up pull-down configure enumeration
 */
typedef enum
{
    IOC_PULL_NONE = 0x00,                 /*!< IO pull none */
    IOC_PULL_DOWN = 0x01,                 /*!< IO pull down */
    IOC_PULL_UP   = 0x02,                 /*!< IO pull up */
} IOC_PULL_MODE_TypeDef;

/**
 * @brief IO schmitt trigger enable
 */
typedef enum
{
    IOC_SCHT_DISABLE = DISABLE,     /*!< IO schmitt trigger disable */
    IOC_SCHT_ENABLE  = ENABLE       /*!< IO schmitt trigger enable  */
} IOC_SCHT_MODE_TypeDef;

/**
 * @brief IOC DIR enumeration
 */
typedef enum
{
    IOC_DIR_IN_OUT = 0x01,     /*!< GPIO Dir Input and Out  */
    IOC_DIR_OUT    = 0x00      /*!< GPIO Dir Output Only    */
} IOC_DIR_TypeDef;

/**
 * @brief GPIO input filter qualification mode enumeration
 */
typedef enum
{
    GPIO_QUAL_SYNC,                     /*!< Synchronization to SYSCLK */
    GPIO_QUAL_3SAMPLE,                  /*!< Qualified with 3 samples  */
    GPIO_QUAL_6SAMPLE,                  /*!< Qualified with 6 samples  */
    GPIO_QUAL_ASYNC                     /*!< No synchronization  */
} IOC_GPIOInputFilterMode;

//todo: 为了给FPGA测试不报错用的，后续删除
typedef enum
{
    IOC_AF_MODE_0  = 0,   /*!< IO alternative function mode 0  */
    IOC_AF_MODE_1  = 1,   /*!< IO alternative function mode 1  */
    IOC_AF_MODE_2  = 2,   /*!< IO alternative function mode 2  */
    IOC_AF_MODE_3  = 3,   /*!< IO alternative function mode 3  */
    IOC_AF_MODE_4  = 4,   /*!< IO alternative function mode 4  */
    IOC_AF_MODE_5  = 5,   /*!< IO alternative function mode 5  */
    IOC_AF_MODE_6  = 6,   /*!< IO alternative function mode 6  */
    IOC_AF_MODE_7  = 7,   /*!< IO alternative function mode 7  */
    IOC_AF_MODE_9  = 9,   /*!< IO alternative function mode 9  */
    IOC_AF_MODE_10 = 10,  /*!< IO alternative function mode 10 */
    IOC_AF_MODE_11 = 11,  /*!< IO alternative function mode 11 */
    IOC_AF_MODE_13 = 13,  /*!< IO alternative function mode 13 */
    IOC_AF_MODE_14 = 14,  /*!< IO alternative function mode 14 */
} IOC_AF_MODE_TypeDef;

/**
 * @brief GPIO Pin mask define
 */
#define GPIO_PIN_00     0x0001  /*!< GPIO pin 0 */
#define GPIO_PIN_01     0x0002  /*!< GPIO pin 1 */
#define GPIO_PIN_02     0x0004  /*!< GPIO pin 2 */
#define GPIO_PIN_03     0x0008  /*!< GPIO pin 3 */
#define GPIO_PIN_04     0x0010  /*!< GPIO pin 4 */
#define GPIO_PIN_05     0x0020  /*!< GPIO pin 5 */
#define GPIO_PIN_06     0x0040  /*!< GPIO pin 6 */
#define GPIO_PIN_07     0x0080  /*!< GPIO pin 7 */
#define GPIO_PIN_08     0x0100  /*!< GPIO pin 8 */
#define GPIO_PIN_09     0x0200  /*!< GPIO pin 9 */
#define GPIO_PIN_10     0x0400  /*!< GPIO pin 10 */
#define GPIO_PIN_11     0x0800  /*!< GPIO pin 11 */
#define GPIO_PIN_12     0x1000  /*!< GPIO pin 12 */
#define GPIO_PIN_13     0x2000  /*!< GPIO pin 13 */
#define GPIO_PIN_14     0x4000  /*!< GPIO pin 14 */
#define GPIO_PIN_15     0x8000  /*!< GPIO pin 15 */
#define GPIO_PIN_ALL    0xFFFF  /*!< GPIO pin all */

/**
 * @brief IOC init struct definition
 */
typedef struct
{
    IOC_DS_LEVEL_TypeDef  ds;         /*!< Pad drive strength level       */
    IOC_PULL_MODE_TypeDef pull;       /*!< Pad pull up/down ctrl          */
    IOC_SCHT_MODE_TypeDef scht;       /*!< Pad schmitt trigger enable     */
    IOC_DIR_TypeDef       dir;        /*!< Pad input enable               */
} IOC_Init_TypeDef;

/**
 * @brief GPIO interrupt configure
 */
typedef struct
{
    GPIO_INT_TYPE_TypeDef mode;        /*!< Pin interrupt mode: level or edge */
    GPIO_INT_POL_TypeDef  polarity;    /*!< Pin interrupt polarity: high/low; rasing/falling */
} GPIO_INT_Config_TypeDef;

/**
 * @brief GPIO Debounce configure
 */
typedef struct
{
    GPIO_DB_MODE_TypeDef mode;        /*!< GPIO debounce mode: single edge or double edge */
    GPIO_DB_POL_TypeDef  polarity;    /*!< GPIO debounce polarity: high or low */
} GPIO_DB_Init_TypeDef;

/* IOC Config Function */
void GPIO_initPadConfigStruct(IOC_Init_TypeDef *cfg);
DRV_Status GPIO_setPadConfig(GPIO_PinNumber pin_number, IOC_Init_TypeDef *cfg);
DRV_Status GPIO_setPinConfig(GPIO_PinNumber pin_number, uint8_t mode);

/* GPIO Control Function */
DRV_Status GPIO_resetPort(GPIO_Type *GPIOx);
DRV_Status GPIO_setPortDirectionMode(GPIO_PinNumber pin_number, GPIO_DIR_TypeDef dir);

/* GPIO Operation Function */
FlagStatus GPIO_readPin(GPIO_PinNumber pin_number);
DRV_Status GPIO_writePin(GPIO_PinNumber pin_number, FlagStatus bitval);
DRV_Status GPIO_togglePin(GPIO_PinNumber pin_number);
DRV_Status GPIO_togglePinAtomic(GPIO_PinNumber pin_number);
uint16_t GPIO_getPortPins(GPIO_Type *GPIOx);
DRV_Status GPIO_setPortPins(GPIO_Type *GPIOx, uint16_t portval);
DRV_Status GPIO_setPortPinsMasked(GPIO_Type *GPIOx, uint16_t bits_set_mask, uint16_t bits_clr_mask);
DRV_Status GPIO_writePinAtomic(GPIO_PinNumber pin_number, FlagStatus bitval);

/* GPIO Interrupt Function */
DRV_Status GPIO_setInterruptType(GPIO_PinNumber pin_number, GPIO_INT_Config_TypeDef *int_config);
DRV_Status GPIO_enableInterrupt(GPIO_PinNumber pin_number);
DRV_Status GPIO_disableInterrupt(GPIO_PinNumber pin_number);
DRV_Status GPIO_clearInterruptStatus(GPIO_PinNumber pin_number);
ITStatus GPIO_getInterruptStatus(GPIO_PinNumber pin_number);

/* GPIO Input filter Configure Function */
DRV_Status GPIO_setFilterSampDiv(IOC_FilterGroup filter_group, uint32_t samp_div);
DRV_Status GPIO_setFilterMode(GPIO_PinNumber pin_number, IOC_GPIOInputFilterMode filter_mode);

/**
 * @brief Sets the specified GPIO pin to high.
 *
 * @param pin_number    The number enumerated in the enumeration type
 *
 */
static __INLINE void GPIO_setPinHigh(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);
    SET_BIT(GPIOx->DATAOUT, pin_mask);
}

/**
 * @brief Clears the specified GPIO pin to low.
 *
 * @param pin_number    The number enumerated in the enumeration type
 *
 */
static __INLINE void GPIO_setPinLow(GPIO_PinNumber pin_number)
{
    GPIO_Type *GPIOx;
    uint32_t  pin_mask;

    GPIOx    = (GPIO_Type *)(GPIO_BASE + ((pin_number << 8) & 0xf000));
    pin_mask = BIT_MASK(pin_number & 0x0f);
    CLEAR_BIT(GPIOx->DATAOUT, pin_mask);
}

/**
 * @}
 */

/**
 * @}
 */
#ifdef __cplusplus
}
#endif
#endif /*__ET6X_GPIO_H */
