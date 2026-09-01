#include "system_et6x.h"
#include "et6x_cortex.h"
// #include "et6x_crg.h"

#define FLASH_FRQ_33M_LVL     0
#define FLASH_FRQ_50M_LVL     1
#define FLASH_FRQ_100M_LVL    2

/**
 * @brief PLL Reference Input Configure
 *
 * The chip by default uses the external crystal oscillator as the input of the PLL clock source,
 * and the default frequency of the crystal oscillator is 25 MHz.
 * If a crystal oscillator with a different frequency is used in the hardware design,
 * it is necessary to redefine it.!!!
 */
#define HSXO_VALUE            25000000U /*!< Value of the HSXO oscillator in Hz */


/**
 * @brief  CPU Clock Configuration
 * @note  default CPU Clock is 300MHz, unmask macro CPU_200M will change to 200MHz
 *
 */
//#define CPU_200M

// const static CRG_PLLConfigParam pllInit =
// {
//     CRG_PLL_SOURCE_HSXO, //  PLLRefInSrc
//     CRG_PLL_ON,          //  PLLState
//     0x18,                //  PLLFBDiv
//     0x01,                //  PLLPostDiv1
//     0x01,                //  PLLPostDiv2
// };

// const static CRG_ClockConfigParam clkInit =
// {
//     0x01,              // CPUCLKDivider         //300M
//     0x02,              // BUSCLKDivider         //200M
//     0x01,              // APBCLKDivider         //100M
//     0x05,              // APB3CLKDivider        //100M
//     0x03,              // EFCCLKDivider         //50M
//     0x0e,              // CANCLKDivider         //40M
//     0x02,              // ADDACLKDivider        //66.67M
//     0x01,              // CLBCLKDivider         //100M
//     0x02,              // LINCLKDivider         //50M
//     0x00,              // SRPWMCLKDivider       //200M
//     0x00,              // CANCLKSrcSel          //PLLFout
// };


const uint32_t flashTrimParam[3][13] =
{
// 33m
    {
        0x82010af3, 0x08c05700, 0x01180118, 0x00020118, 0x11801b69, 0x000006da, 0x00006da6, 0x000890fb, 0x000890fb,
        0x03004e20, 0x000003ee, 0x000002bd, 0x4020b203
    },
// 50m
    {
        0x230310d5, 0x0d609511, 0x01c101c1, 0x110601c1, 0x1a502921, 0x00000a4f, 0x0000a47d, 0x000db7b8, 0x010db7b8,
        0x06004e20, 0x000003ee, 0x00000423, 0x10310d06
    },
// 100m
    {
        0x4703211a, 0x1a812b22, 0x03830383, 0x220a0383, 0x34a05243, 0x00001495, 0x000148fb, 0x001b7740, 0x011b7740,
        0x0a004e20, 0x000003ee, 0x0000083d, 0x2072250b
    }
};


/* Timeout value */
#define PLLLOCK_TIMEOUT    (3000) /* Timeout value */

/************************* Miscellaneous Configuration ************************/

/*!< Uncomment the following line if you need to relocate your vector Table in
 *   Internal SRAM. */
/* #define VECT_TAB_SRAM */
#define VECT_TAB_OFFSET    0x0 /*!< Vector Table base offset field.
                                *    This value must be a multiple of 0x200. */
/******************************************************************************/


/* This variable is updated in three ways:
 *  1) by calling CMSIS function SystemCoreClockUpdate()
 *  2) by calling HAL API function HAL_RCC_GetHCLKFreq()
 *  3) each time HAL_RCC_ClockConfig() is called to configure the system clock frequency
 *     Note: If you use this function to configure the system clock; then there
 *           is no need to call the 2 first functions listed above, since SystemCoreClock
 *           variable is updated automatically.
 */
uint32_t SystemCoreClock = 25000000;


/**
 * @brief  Setup the microcontroller system
 *         Initialize the Embedded Flash Interface, the PLL and update the
 *         SystemFrequency variable.
 * @param  None
 * @retval None
 */

/* ================   CRGCFG   ================ */

/**
 * @brief Provide an overview of the purpose and functionality of the peripheral: crg_cfg (CRGCFG)
 */
#ifdef __cplusplus
#define   __I        volatile          /*!< Defines 'read only' permissions */
#else
#define   __I        volatile const    /*!< Defines 'read only' permissions */
#endif
#define     __O      volatile          /*!< Defines 'write only' permissions */
#define     __IO     volatile          /*!< Defines 'read / write' permissions */

/* following defines should be used for structure members */
#define     __IM     volatile const      /*! Defines 'read only' structure member permissions */
#define     __OM     volatile            /*! Defines 'write only' structure member permissions */
#define     __IOM    volatile            /*! Defines 'read / write' structure member permissions */

static void SystemClock_Config(void)
{
    // CRG_unlockClockConfig();
    // /* Configure PLL */
    // if (CRG_setPLLConfig((const CRG_PLLConfigParam *)&pllInit, HSXO_VALUE, PLLLOCK_TIMEOUT) == DRV_OK)
    // {
    //     /* Configure CPU, BUS, Peripherals Clock  dividers  */
    //     if (CRG_setClockDivConfig((const CRG_ClockConfigParam *)&clkInit) != DRV_OK)
    //     {
    //         while (1);
    //     }
    //     /* Select PLL Fout Source */
    //     if (CRG_setClockOutSource(CRG_CLKSRC_PLL_FOUT) != DRV_OK)
    //     {
    //         while (1);
    //     }
    // }
    // else
    // {
    //     while (1);
    // }
    // CRG_lockClockConfig();
}

/**
 * @brief PFlash and DFlash Timing trim param load  depend on FLash Clock
 *  when efc clk switch to higher clock,  trim load first, then switch efc clk(tck_len_trc, tMS, tRC, tACC)
 *  when efc clk switch to lower clock,  switch efc clc, then load timing trim(tMS, tACC, tRC, tck_len_trc)
 * @param level  FLASH_FRQ_25M_LVL, FLASH_FRQ_50M_LVL, FLASH_FRQ_75M_LVL, FLASH_FRQ_100M_LVL
 */
static void SystemFlash_TrimLoad(uint8_t level)
{
    // uint8_t  index      = 0;
    // uint32_t reg_addr   = (uint32_t)(&DFLASH->EFC_DFLASH_EXTEND.EFC_TIMING_PARA0);
    // uint32_t *paramArry = (uint32_t *)flashTrimParam[level][0];

    // if (level > FLASH_FRQ_100M_LVL)
    // {
    //     return;
    // }
    // /* unlock reg */
    // if (READ_BIT(DFLASH->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk))
    // {
    //     /* unlock */
    //     DFLASH->EFC_REG_KEY1 = 0x0123CDEF;
    //     DFLASH->EFC_REG_KEY2 = 0x89AB4567;
    //     /* wait clear */
    //     while (READ_BIT(DFLASH->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk));
    // }
    // for (index = 0; index < 13; index++)
    // {
    //     /* code */
    //     if (index == 10)
    //     {
    //         continue;
    //     }
    //     WRITE_REG(REG32(reg_addr + index * 4), (uint32_t)*(paramArry + index));
    // }
    // /* lock reg */
    // SET_BIT(DFLASH->EFC_WPFLG, DFLASH_EFC_WPFLG_EFC_REG_WRPROT_FLG_Msk);
}

void SystemInit(void)
{
    /* Enable Global Interrupt Mask */
    __enable_irq();
    /* FPU settings ------------------------------------------------------------*/
#if (__FPU_PRESENT == 1) && (__FPU_USED == 1)
    SCB->CPACR |= ((3UL << 10 * 2) | (3UL << 11 * 2));  /* set CP10 and CP11 Full Access */
#endif

#if defined(FPGA_VERSION)
#else
    /* Switch System Clock to PLL source */
    if ((CRG_isClockSrcPLL() != SET) || (HSXO_VALUE != 25000000U))
    {
        /* Select PLL Fout Source */
        if (CRG_setClockOutSource(CRG_CLKSRC_OSC25M) != DRV_OK)
        {
            while (1);
        }
        DELAY_US(10);
        /* NOTICE: calling sequence of below two functions cannot be changed!!! */
        /* FLASH_FRQ_xxM_LVL should match EFC Clock configured by EFCCLKDivider  */
        SystemFlash_TrimLoad(FLASH_FRQ_50M_LVL);
        /* switch to PLL Clock */
        SystemClock_Config();
    }
#endif
    // /* deassert modules reset */
    // CRG_unlockClockConfig();
    // CRG->SRST3 = 0xFFFFFFFF;
    // CRG->SRST2 = 0xFFFFFFFF;
    // CRG->SRST0 = 0xFFFFFFFF;
    // CRG->SRST1 = 0xFFFFFFFF;
    // CRG_lockClockConfig();
    // /* Remap Vector Table if needed */
}

/**
 * @brief  Update SystemCoreClock variable according to Clock Register Values.
 *         The SystemCoreClock variable contains the core clock (HCLK), it can
 *         be used by the user application to setup the SysTick timer or configure
 *         other parameters.
 *
 * @note   Each time the core clock (HCLK) changes, this function must be called
 *         to update SystemCoreClock variable value. Otherwise, any configuration
 *         based on this variable will be incorrect.
 *
 */
void SystemCoreClockUpdate(void)
{
#if !defined(FPGA_VERSION)
    SystemCoreClock = CRG_getCPUClock();
#else
    SystemCoreClock = 25000000; /* 25MHz */
#endif
}

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
