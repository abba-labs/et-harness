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

/**
 * @mainpage ET6002 Low-level Driver Library
 * ET6002 Series is a feature-rich and high-performance digital-analog hybrid microcontrolher,
 * highly integrated with two 32-bit high-performance ARM Cortex-M7 cores, and working clock frequencies up to 300MHz;
 * It include 256KB on chip SRAM, 512KB embedded program Flash, and 128KB embedded data Flash.
 * ETMCU supply a full function  Driver Library for ET6002
 */

/** @addtogroup ET3101_Driver
 * @{
 */

/** @addtogroup COMMON
 * @{
 */

#ifndef __ET6x_H
#define __ET6x_H

#ifdef __cplusplus
extern "C"
{
#endif /* __cplusplus */

/** @addtogroup Library_configuration_section
 * @ingroup COMMON
 * @{
 */

/**
 * @brief ET6x Family
 */
#if !defined(ET6X)
#define ET6X
#define Et6XSDK_VERSION    0113
#endif /* ET6X */

/*  Tip: To avoid modifying this file each time you need to switch between these
 *      devices, you can define the device in your toolchain compiler preprocessor.
 */

/**
 * @}
 */

/** @addtogroup Device_Included
 * @ingroup COMMON
 * @{
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#if defined(ET6001)
#include "et6001.h"
#elif defined(ET6002)
#include "et6002.h"
#elif defined(ET3101)
#include "et3101.h"
#elif defined(ET6801)
#include "et6801.h"
#else
#error "Please select first the target ET6x device used in your application (in et6x.h file)"
#endif

/**
 * @}
 */

/** @addtogroup Exported_types
 * @ingroup COMMON
 * @{
 */
typedef enum
{
    RESET = 0,
    SET   = !RESET
} FlagStatus,
ITStatus;

typedef enum
{
    DISABLE = 0,
    ENABLE  = !DISABLE
} FunctionalState,
EventStatus, ControlStatus;
#define IS_FUNCTIONAL_STATE(STATE)    (((STATE) == DISABLE) || ((STATE) == ENABLE))

typedef enum
{
    ERROR   = 0,
    SUCCESS = !ERROR
} ErrorStatus;

typedef enum
{
    UNMASKED = 0,
    MASKED   = !UNMASKED
} MaskStatus;

/**
 * @brief  Driver Status structures definition
 */
typedef enum
{
    DRV_OK        = 0x00,
    DRV_ERROR     = 0x01,
    DRV_PARAM_ERR = 0x02,
    DRV_INVALID   = 0x03,
    DRV_TIMEOUT   = 0x04,
    DRV_BUSY      = 0x05
} DRV_Status;

/** @addtogroup Exported_macro
 * @ingroup COMMON
 * @{
 */

#define REG16(REG)                             (*(__IO uint16_t *)(REG))

#define REG32(REG)                             (*(__IO uint32_t *)(REG))

#define SET_BIT(REG, BIT)                      ((REG) |= (BIT))

#define CLEAR_BIT(REG, BIT)                    ((REG) &= ~(BIT))

#define READ_BIT(REG, BIT)                     ((REG)&(BIT))

#define CLEAR_REG(REG)                         ((REG) = (0x0))

#define WRITE_REG(REG, VAL)                    ((REG) = (VAL))

#define READ_REG(REG)                          (REG)

#define MODIFY_REG(REG, CLEARMASK, SETMASK)    WRITE_REG((REG), (((READ_REG(REG)) & (~(CLEARMASK))) | (SETMASK)))

#define POSITION_VAL(VAL)                      (__CLZ(__RBIT(VAL)))

#define BIT_MASK(x)                            ((uint32_t)((uint32_t)0x01U << (x)))

#define BITS_MASK(start, end)                  ((0xFFFFFFFFUL << (start)) & (0xFFFFFFFFUL >> (31U - (uint32_t)(end))))

#define BITS_WID_MASK(width)                   (0xFFFFFFFFUL >> (32U - (uint32_t)(width)))

#define GET_BITS(regval, start, end)           (((regval)&BITS_MASK((start), (end))) >> (start))

#define OFT_REG32     (4)

#define OFT_REG16     (2)

#define BITS_DWORD    (32)


/* Use of CMSIS compiler intrinsics for register exclusive access */
/* Atomic 32-bit register access macro to set one or several bits */
#define ATOMIC_SET_BIT(REG, BIT)                             \
        do {                                                       \
            uint32_t val;                                            \
            do {                                                     \
                val = __LDREXW((__IO uint32_t *)&(REG)) | (BIT);       \
            } while ((__STREXW(val, (__IO uint32_t *)&(REG))) != 0U); \
        } while (0)

/* Atomic 32-bit register access macro to clear one or several bits */
#define ATOMIC_CLEAR_BIT(REG, BIT)                           \
        do {                                                       \
            uint32_t val;                                            \
            do {                                                     \
                val = __LDREXW((__IO uint32_t *)&(REG)) & ~(BIT);      \
            } while ((__STREXW(val, (__IO uint32_t *)&(REG))) != 0U); \
        } while (0)

/* Atomic 32-bit register access macro to clear and set one or several bits */
#define ATOMIC_MODIFY_REG(REG, CLEARMSK, SETMASK)                          \
        do {                                                                     \
            uint32_t val;                                                          \
            do {                                                                   \
                val = (__LDREXW((__IO uint32_t *)&(REG)) & ~(CLEARMSK)) | (SETMASK); \
            } while ((__STREXW(val, (__IO uint32_t *)&(REG))) != 0U);               \
        } while (0)

/* Atomic 16-bit register access macro to set one or several bits */
#define ATOMIC_SETH_BIT(REG, BIT)                            \
        do {                                                       \
            uint16_t val;                                            \
            do {                                                     \
                val = __LDREXH((__IO uint16_t *)&(REG)) | (BIT);       \
            } while ((__STREXH(val, (__IO uint16_t *)&(REG))) != 0U); \
        } while (0)

/* Atomic 16-bit register access macro to clear one or several bits */
#define ATOMIC_CLEARH_BIT(REG, BIT)                          \
        do {                                                       \
            uint16_t val;                                            \
            do {                                                     \
                val = __LDREXH((__IO uint16_t *)&(REG)) & ~(BIT);      \
            } while ((__STREXH(val, (__IO uint16_t *)&(REG))) != 0U); \
        } while (0)

/* Atomic 16-bit register access macro to clear and set one or several bits */
#define ATOMIC_MODIFYH_REG(REG, CLEARMSK, SETMASK)                         \
        do {                                                                     \
            uint16_t val;                                                          \
            do {                                                                   \
                val = (__LDREXH((__IO uint16_t *)&(REG)) & ~(CLEARMSK)) | (SETMASK); \
            } while ((__STREXH(val, (__IO uint16_t *)&(REG))) != 0U);               \
        } while (0)


/* Exported macro ------------------------------------------------------------*/

/* Macro to get variable aligned on 32-bytes,needed for cache maintenance purpose */
#if defined(__GNUC__)     /* GNU Compiler */
#define ALIGN_32BYTES(buf)    buf __attribute__((aligned(32)))
#elif defined(__ICCARM__) /* IAR Compiler */
#define ALIGN_32BYTES(buf)    _Pragma("data_alignment=32") buf
#elif defined(__CC_ARM)   /* ARM Compiler */
#define ALIGN_32BYTES(buf)    __align(32) buf
#endif

/* Macro to get variable aligned on 4-bytes, for __ICCARM__ the directive "#pragma data_alignment=4" must be used
 * instead */
#if defined(__GNUC__) /* GNU Compiler */
#ifndef __ALIGN_END
#define __ALIGN_END    __attribute__((aligned(4)))
#endif /* __ALIGN_END */
#ifndef __ALIGN_BEGIN
#define __ALIGN_BEGIN
#endif /* __ALIGN_BEGIN */
#else
#ifndef __ALIGN_END
#define __ALIGN_END
#endif /* __ALIGN_END */
#ifndef __ALIGN_BEGIN
#if defined(__CC_ARM)     /* ARM Compiler */
#define __ALIGN_BEGIN    __align(4)
#elif defined(__ICCARM__) /* IAR Compiler */
#define __ALIGN_BEGIN
#endif /* __CC_ARM */
#endif /* __ALIGN_BEGIN */
#endif /* __GNUC__ */

#define DRV_IS_BIT_SET(REG, BIT)    (((REG)&(BIT)) != RESET)
#define DRV_IS_BIT_CLR(REG, BIT)    (((REG)&(BIT)) == RESET)

#define UNUSED(x)                   ((void)(x))

#ifdef USE_FULL_ASSERT
/* Exported functions ------------------------------------------------------- */
void assert_failed(uint8_t *file, uint32_t line);

#define assert_param(expr)    ((expr) ? (void)0 : assert_failed((uint8_t *)__FILE__, __LINE__))
#else
#define assert_param(expr)    ((void)0)
#endif

/**
 * @brief  __RAM_FUNC definition
 */
#if defined (__CC_ARM) || (defined (__ARMCC_VERSION) && (__ARMCC_VERSION >= 6010050))

/* ARM Compiler V4/V5 and V6
 * --------------------------
 * RAM functions are defined using the toolchain options.
 * Functions that are executed in RAM should reside in a separate source module.
 * Using the 'Options for File' dialog you can simply change the 'Code / Const'
 * area of a module to a memory space in physical RAM.
 * Available memory areas are declared in the 'Target' tab of the 'Options for Target'
 * dialog.
 */
#define __RAM_FUNC    __attribute__((section(".RamFunc")))

#elif defined (__ICCARM__)

/* IAR Compiler
 * ------------
 * RAM functions are defined using a specific toolchain attribute "@ramfunc".
 */
#define __RAM_FUNC    __attribute__((section(".RamFunc")))

#elif defined   (__GNUC__)

/* GNU Compiler
 * ------------
 * RAM functions are defined using a specific toolchain attribute
 * "__attribute__((section(".RamFunc")))".
 */
#define __RAM_FUNC    __attribute__((section(".RamFunc")))

#endif /* __CC_ARM */

/**
 * Compatible defined for other platforms
 *
 */
#define  EINT    __enable_irq()
#define  DINT    __disbale_irq()
#define  ERTM
#define  DRTM
#define  EALLOW
#define  EDIS
#define  ESTOP0

#define ISR_EXIT_BARRIER()    __DSB()

#ifndef __interrupt
#define __interrupt
#endif // !__interrupt

/**
 * @}
 */
/**
 * @}
 */

/**
 * @}
 */

#ifdef __cplusplus
}
#endif /* __cplusplus */

#endif /* __ET6X_H__ */
