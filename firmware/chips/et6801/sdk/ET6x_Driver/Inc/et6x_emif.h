/**
 * @file et6x_emif.h
 * @author aeg
 * @brief
 * @version 0.1
 * @date 2023-03-01
 *
 * @copyright Copyright (c) 2023
 *
 */

#ifndef __ET6X_EMIF_H
#define __ET6X_EMIF_H

#ifdef __cplusplus
extern "C" {
#endif

#include "et6x.h"

/**
 * @brief EMIF chip select
 *
 */
typedef enum
{
    EMIF1_CS0,
    EMIF1_CS1,
    EMIF1_CS2,
} EMIF1_CS_Typedef;

/**
 * @brief configure we_n and cs_n signal sync property
 *
 */
typedef enum
{
    WE_2_CYCLES_DELAY,
    WE_NO_DELAY_2_CYCLES
} EMIF1_SRAM_WE_Time_Typedef;

/**
 * @brief SRAM interface timing configuration struct
 *
 */
typedef struct
{
    uint8_t                    t_rc;       /* read cycle time, Minimum permitted value = 2 */
    uint8_t                    t_wc;       /* write cycle time, Minimum permitted value = 2 */
    uint8_t                    t_ceoe;     /* output enable delay time after chip assert, Minimum permitted value = 1 */
    uint8_t                    t_wp;       /* write pulse time, Minimum permitted value = 1 */
    uint8_t                    t_pc;       /* page cycle time, Minimum permitted value = 1 */
    uint8_t                    t_tr;       /* turn-around time, Minimum permitted value = 1 */
    EMIF1_SRAM_WE_Time_Typedef we_time;    /* we_n to occur 2 clock cycles after cs_n goes LOW, Minimum permitted value
                                            * = 1 */
} EMIF1_NOR_SRAM_timingConfig_Typedef;

typedef enum
{
    EMIF1_NOR_SRAM_REV,
    EMIF1_NOR_SRAM_16_BITS
} EMIF1_NOR_SRAM_Mem_Width_Typedef;

typedef enum
{
    EMIF1_ASYNC_READ,
    EMIF1_SYNC_READ
} EMIF1_NOR_SRAM_Rd_Sync_Typedef;

typedef enum
{
    EMIF1_1_BEAT,
    EMIF1_4_BEATS,
    EMIF1_8_BEATS,
    EMIF1_16_BEATS,
    EMIF1_32_BEATS,
    EMIF1_CONTINUOUS_BEATS
} EMIF1_NOR_SRAM_Rw_Bl_Typedef;

typedef enum
{
    EMIF1_RW_ASYNC,
    EMIF1_RW_SYNC
} EMIF1_NOR_SRAM_Rw_Sync_Typedef;

typedef enum
{
    EMIF1_BAA_HIGH,
    EMIF1_BAA_LOW
} EMIF1_NOR_SRAM_Baa_Typedef;

typedef enum
{
    EMIF1_ADV_HIGH,
    EMIF1_ADV_LOW
} EMIF1_NOR_SRAM_Adv_Typedef;

typedef enum
{
    CS_TIMING,
    WE_N_TIMING
} EMIF1_NOR_SRAM_Bls_Time_Typedef;

typedef enum
{
    BURSTS_CROSS_ADDRESS_BOUNDARY,
    BURST_ON_32_BEATS_BOUNDARY,
    BURST_ON_64_BEATS_BOUNDARY,
    BURST_ON_128_BEATS_BOUNDARY,
    BURST_ON_256_BEATS_BOUNDARY,
} EMIF1_NOR_SRAM_Burst_Align_Typedef;

/**
 * @brief SRAM interface op configuration struct
 *
 */
typedef struct
{
    EMIF1_NOR_SRAM_Mem_Width_Typedef   mw;
    EMIF1_NOR_SRAM_Rw_Sync_Typedef     rd_sync;
    EMIF1_NOR_SRAM_Rw_Bl_Typedef       rd_bl;
    EMIF1_NOR_SRAM_Rw_Sync_Typedef     wr_sync;
    EMIF1_NOR_SRAM_Rw_Bl_Typedef       wr_bl;
    EMIF1_NOR_SRAM_Baa_Typedef         baa;
    EMIF1_NOR_SRAM_Adv_Typedef         adv;
    EMIF1_NOR_SRAM_Bls_Time_Typedef    bls_tim;
    EMIF1_NOR_SRAM_Burst_Align_Typedef burst_align;
} EMIF1_NOR_SRAM_modeConfig_Typedef;

/**
 * @brief
 *
 */
typedef enum
{
    EMIF1_CRE_LOW,
    EMIF1_CRE_HIGH,
} EMIF1_ALL_Set_Cre_Typedef;


/**
 * @brief
 *
 */
typedef enum
{
    EMIF1_ADDR_MODE_ADDR_ONLY = 0,
    EMIF1_ADDR_MODE_ADDR_BA,    /* use ADDR and BA */
} EMIF1_ADDR_Mode_Typedef;

/**
 * @brief
 *
 */
typedef enum
{
    UPDATEREGS_AXI,
    MODEREG,
    UPDATEREGS,
    MODEREG_UPDATEREGS
} EMIF1_ALL_Cmd_Type_Typedef;

/**
 * @brief
 *
 */
typedef enum
{
    MEMIF1_CS2,
    MEMIF1_CS3,
    MEMIF1_CS4
} EMIF1_ALL_Chip_Nmbr_Typedef;


/**
 * @brief SRAM interface op configuration struct
 *
 */
typedef struct __PACKED
{
    uint32_t                    addr19to0;
    EMIF1_ALL_Set_Cre_Typedef   set_cre;
    EMIF1_ALL_Cmd_Type_Typedef  cmd_type;
    EMIF1_ALL_Chip_Nmbr_Typedef chip_nmbr;
} EMIF1_ALL_cmdConfig_Typedef;


/**
 * @brief NOR FLASH and SRAM configuration structure
 *
 */
typedef struct
{
    EMIF1_NOR_SRAM_timingConfig_Typedef timing;
    EMIF1_NOR_SRAM_modeConfig_Typedef   mode;
    EMIF1_ALL_cmdConfig_Typedef         cmd;
} EMIF1_NOR_SRAM_Config_Typedef;

/******************************************************************* */
typedef enum
{
    EMIF0_SDRAM_WIDTH_32_BITS,
    EMIF0_SDRAM_WIDTH_16_BITS,
    EMIF0_SDRAM_WIDTH_8_BITS,
} EMIF0_SDRAM_Width_Typedef;

typedef enum
{
    EMIF0_SDRAM_BANK_NUM_1,
    EMIF0_SDRAM_BANK_NUM_2,
    EMIF0_SDRAM_BANK_NUM_4,
} EMIF0_SDRAM_Bank_Num_Typedef;

typedef enum
{
    EMIF0_SDRAM_COLBITS_8,
    EMIF0_SDRAM_COLBITS_9,
    EMIF0_SDRAM_COLBITS_10,
    EMIF0_SDRAM_COLBITS_11,
} EMIF0_SDRAM_ColBits_Typedef;


typedef struct
{
    uint8_t t_wr;
    uint8_t t_rcar;
    uint8_t t_cas;
    uint8_t t_rcd; /* read or write delay */
    uint8_t t_rp;  /* row precharge time */
    uint8_t t_ras; /* t_ras >= t_rcd + t_cas + t_wp */
} EMIF0_SDRAM_TimingConfig_Typedef;

typedef struct
{
    uint16_t                     mode_reg;
    EMIF0_SDRAM_Width_Typedef    sdr_width;
    EMIF0_SDRAM_Bank_Num_Typedef bankNmbr;
    EMIF0_SDRAM_ColBits_Typedef  colbits;
} EMIF0_SDRAM_Config_Typedef;


#define EMIF0_SDRAM_MODE_WB_POS             9UL
#define EMIF0_SDRAM_MODE_CAS_LATENCY_POS    4UL
#define EMIF0_SDRAM_MODE_BT_POS             3UL
#define EMIF0_SDRAM_MODE_BURST_LEN_POS      0UL



/* EMIF1 interrupt mask */
#define EMIF1_IT_IF0_IF1_MASK            (EMIF1_MEM_CFG_SET_int_enable0_Msk | EMIF1_MEM_CFG_SET_int_enable1_Msk)
#define EMIF1_IT_IF0_MASK                (EMIF1_MEM_CFG_SET_int_enable0_Msk)
#define EMIF1_IT_IF1_MASK                (EMIF1_MEM_CFG_SET_int_enable1_Msk)
#define EMIF1_IT_ECC_MASK                (EMIF1_MEM_CFG_SET_ecc_int_enable1_Msk)

/* EMIF1 interrupt mask */
#define EMIF1_IT_ECC_BLOCK_0_MASK        (1U << 0U)
#define EMIF1_IT_ECC_BLOCK_1_MASK        (1U << 1U)
#define EMIF1_IT_ECC_BLOCK_2_MASK        (1U << 2U)
#define EMIF1_IT_ECC_BLOCK_3_MASK        (1U << 3U)
#define EMIF1_IT_ECC_BLOCK_EX_MASK       (1U << 4U)
#define EMIF1_IT_ECC_BLOCK_ABORT_MASK    (1U << 5U)


void EMIF1_NOR_SRAM_timingConfig_StructInit(EMIF1_NOR_SRAM_timingConfig_Typedef *timing);
void EMIF1_NOR_SRAM_modeConfig_StructInit(EMIF1_NOR_SRAM_modeConfig_Typedef *mode);
void EMIF1_ALL_cmdConfig_StructInit(EMIF1_ALL_cmdConfig_Typedef *cmd);
void EMIF1_NOR_SRAM_Config(EMIF1_NOR_SRAM_Config_Typedef *config);
void EMIF1_NOR_SRAM_DeConfig(void);

void EMIF1_ITEnable(uint32_t ITMasks);
void EMIF1_ITDisable(uint32_t ITMasks);
uint32_t EMIF1_GetITStatus(void);
void EMIF1_ClearITStatus(uint32_t IT_Clear);

void EMIF1_AddrMatch_Config(EMIF1_CS_Typedef cs, uint8_t addr, uint8_t addrmask);
void EMIF1_AddrMode_Config(EMIF1_ADDR_Mode_Typedef addr_mode);


void EMIF0_SDRAM_Config(EMIF0_SDRAM_Config_Typedef *config);
void EMIF0_SDRAM_TimingConfig(EMIF0_SDRAM_TimingConfig_Typedef *timing);
void EMIF0_SDRAM_RefreshRateConfig(uint16_t period, uint8_t max_ref_num);
void EMIF0_SDRAM_Enable(void);

//
void EMIF_MemAccessEnable(uint8_t emif_interface);



#ifdef __cplusplus
}
#endif

#endif  /* __ET6X_EMIF_H */
