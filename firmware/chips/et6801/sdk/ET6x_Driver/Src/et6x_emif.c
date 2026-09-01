/**
 * @file et6x_emif.c
 * @author aeg
 * @brief
 * @version 0.1
 * @date 2023-03-01
 *
 * @copyright Copyright (c) 2023
 *
 */

#include "et6x_emif.h"

/** @addtogroup ET6x_Driver
 * @{
 */

/** @defgroup EMIF EMIF
 * @brief EMIF module driver
 * @{
 */

/* Private typedef -----------------------------------------------------------*/
/* Private define ------------------------------------------------------------*/
/* Private macro -------------------------------------------------------------*/
/* default nor flash or sram configure value */
#define DEFALUT_NOR_SRAM_CYCLES_VALUE    (0x2B3CCU)
#define DEFALUT_NOR_SRAM_OPMODE_VALUE    (1U)
#define DEFALUT_NOR_SRAM_CMD_VALUE       (0U)

/* default nor flash or sram timing configure value */
#define DEFAULT_NOR_SRAM_T_RC            (0xCU)
#define DEFAULT_NOR_SRAM_T_WC            (0xCU)
#define DEFAULT_NOR_SRAM_T_CEOE          (0x3U)
#define DEFAULT_NOR_SRAM_T_WP            (0x6U)
#define DEFAULT_NOR_SRAM_T_PC            (0x2U)
#define DEFAULT_NOR_SRAM_T_TR            (0x1U)


/*! Parameter validity check for EMIF1 interrupt mask . */
#define IS_EMIF1_ITMASK(mask)                 \
        ((((mask)&EMIF1_IT_IF0_IF1_MASK) != 0) || \
         (((mask)&EMIF1_IT_IF0_MASK) != 0) ||     \
         (((mask)&EMIF1_IT_IF1_MASK) != 0) ||     \
         (((mask)&EMIF1_IT_ECC_MASK) != 0))

/*! Parameter validity check for EMIF1 ECC interrupt mask . */
#define IS_EMIF1_ECC_ITMASK(mask)                  \
        ((((mask)&EMIF1_IT_ECC_BLOCK_0_MASK) != 0) ||  \
         (((mask)&EMIF1_IT_ECC_BLOCK_1_MASK) != 0) ||  \
         (((mask)&EMIF1_IT_ECC_BLOCK_2_MASK) != 0) ||  \
         (((mask)&EMIF1_IT_ECC_BLOCK_3_MASK) != 0) ||  \
         (((mask)&EMIF1_IT_ECC_BLOCK_EX_MASK) != 0) || \
         (((mask)&EMIF1_IT_ECC_BLOCK_ABORT_MASK) != 0))
#define CHIP_BASE_ADDR_MASK    (0xFF000000U)

#define ADDR_1ST_CYCLE(AXI_ADDR)    (uint8_t)(AXI_ADDR)         /* 1st addressing cycle */
#define ADDR_2ND_CYCLE(AXI_ADDR)    (uint8_t)((AXI_ADDR) >> 8)  /* 2nd addressing cycle */
#define ADDR_3RD_CYCLE(AXI_ADDR)    (uint8_t)((AXI_ADDR) >> 13) /* 3rd addressing cycle */
#define ADDR_4TH_CYCLE(AXI_ADDR)    (uint8_t)((AXI_ADDR) >> 21) /* 4th addressing cycle */
#define ADDR_5TH_CYCLE(AXI_ADDR)    (uint8_t)((AXI_ADDR) >> 29) /* 5th addressing cycle */

#define ADDR_CYCLES_0           0U
#define ADDR_CYCLES_1           1U
#define ADDR_CYCLES_2           2U
#define ADDR_CYCLES_3           3U
#define ADDR_CYCLES_4           4U
#define ADDR_CYCLES_5           5U
#define ADDR_CYCLES_6           6U
#define ADDR_CYCLES_7           7U

#define READ_CMD_PHASE_ADDR     (0x00B18000U)
#define READ_CMD_DATA_ADDR      (0x00298000U)

#define WRITE_CMD_PHASE_ADDR    (0x00A08400U)
#define WRITE_CMD_DATA_ADDR     (0x00388000U)


/* CORESC module access key */
#define SW_ACCESS_KEY                            (0X7879A8A9U)

#define SMC_INF0_CHIP0_ADDR_MATCH_RESET          (0x000000F0U)
#define SMC_INF0_CHIP1_ADDR_MATCH_RESET          (0x000000F1U)
#define SMC_INF0_CHIP2_ADDR_MATCH_RESET          (0x000000F2U)
#define SMC_INF0_CHIP3_ADDR_MATCH_RESET          (0x000000F3U)
#define SMC_INF0_CHIP_ADDR_MASK_RESET            (0x000000FFU)

/* interface control value for different memory medium */
#define SMC_INF0_CTRL_SRAM                       (0U)
#define SMC_INF0_CTRL_PSRAM                      (0U)
#define SMC_INF0_CTRL_NOR_FLASH                  (0U)
#define SMC_INF0_CTRL_NAND_FLASH_WITH_SRAM_IF    (0U)
#define SMC_INF1_NAND_FLASH_WITH_MUX_AD          (0U)

/* SMC chip select match offset value */
#define SMC_CS_MATCH_OFFSET                      24U

/* SMC chip address align value */
#define SMC_CS_ADDRESS_ALIGN                     0x00FFFFFFU



/**
 * @brief Enable EMIF memory access
 *
 * @param emif_interface: EMIF0 or EMIF1
 */
void EMIF_MemAccessEnable(uint8_t emif_interface)
{
    if (emif_interface == 0)
    {
        SET_BIT(SYSC->EMIF_2, SYSC_EMIF_2_SYSC_EMIF0_EN_Msk);
    }
    else
    {
        SET_BIT(SYSC->EMIF_2, SYSC_EMIF_2_SYSC_EMIF1_EN_Msk);
    }
}

/**
 * @brief Configure EMIF address mode
 *
 * @param addr_mode: EMIF1_ADDR_MODE_ADDR_ONLY or EMIF1_ADDR_MODE_ADDR_BA
 */
void EMIF1_AddrMode_Config(EMIF1_ADDR_Mode_Typedef addr_mode)
{
    if (addr_mode == EMIF1_ADDR_MODE_ADDR_ONLY)
    {
        CLEAR_BIT(SYSC->EMIF_2, SYSC_EMIF_2_SC_EMIF_ADDR_MODE_Msk);
    }
    else
    {
        SET_BIT(SYSC->EMIF_2, SYSC_EMIF_2_SC_EMIF_ADDR_MODE_Msk);
    }
}

/**
 * @brief Configure EMIF address match
 *
 * @param cs: EMIF1_CS0 ~ EMIF1_CS3
 * @note:   emif1_cs[2:0] <-> emif_cs_n[3:1] <--> iolist : CS[4:2]
 */
void EMIF1_AddrMatch_Config(EMIF1_CS_Typedef cs, uint8_t addr, uint8_t addrmask)
{
    switch (cs)
    {
    case EMIF1_CS0:
        MODIFY_REG(SYSC->EMIF_0, SYSC_EMIF_0_SC_EMIF_CHIP1_ADDR_MASK_Msk,
                   ((uint32_t)addrmask << SYSC_EMIF_0_SC_EMIF_CHIP1_ADDR_MASK_Pos));
        MODIFY_REG(SYSC->EMIF_0, SYSC_EMIF_0_SC_EMIF_CHIP1_ADDR_MATCH_Msk,
                   ((uint32_t)addr << SYSC_EMIF_0_SC_EMIF_CHIP1_ADDR_MATCH_Pos));
        break;

    case EMIF1_CS1:
        MODIFY_REG(SYSC->EMIF_0, SYSC_EMIF_0_SC_EMIF_CHIP2_ADDR_MASK_Msk,
                   ((uint32_t)addrmask << SYSC_EMIF_0_SC_EMIF_CHIP2_ADDR_MASK_Pos));
        MODIFY_REG(SYSC->EMIF_0, SYSC_EMIF_0_SC_EMIF_CHIP2_ADDR_MATCH_Msk,
                   ((uint32_t)addr << SYSC_EMIF_0_SC_EMIF_CHIP2_ADDR_MATCH_Pos));
        break;

    case EMIF1_CS2:
        MODIFY_REG(SYSC->EMIF_1, SYSC_EMIF_1_SC_EMIF_CHIP3_ADDR_MASK_Msk,
                   ((uint32_t)addrmask << SYSC_EMIF_1_SC_EMIF_CHIP3_ADDR_MASK_Pos));
        MODIFY_REG(SYSC->EMIF_1, SYSC_EMIF_1_SC_EMIF_CHIP3_ADDR_MATCH_Msk,
                   ((uint32_t)addr << SYSC_EMIF_1_SC_EMIF_CHIP3_ADDR_MATCH_Pos));
        break;

    default:
        break;
    }
}

/**
 * @brief Init nor flash or sram timing configuration structure
 *
 * @param timing
 */
void EMIF1_NOR_SRAM_timingConfig_StructInit(EMIF1_NOR_SRAM_timingConfig_Typedef *timing)
{
    timing->t_rc    = DEFAULT_NOR_SRAM_T_RC;
    timing->t_wc    = DEFAULT_NOR_SRAM_T_WC;
    timing->t_ceoe  = DEFAULT_NOR_SRAM_T_CEOE;
    timing->t_wp    = DEFAULT_NOR_SRAM_T_WP;
    timing->t_pc    = DEFAULT_NOR_SRAM_T_PC;
    timing->t_tr    = DEFAULT_NOR_SRAM_T_TR;
    timing->we_time = WE_2_CYCLES_DELAY;
}

/**
 * @brief Init nor flash or sram mode configuration structure
 *
 * @param mode
 */
void EMIF1_NOR_SRAM_modeConfig_StructInit(EMIF1_NOR_SRAM_modeConfig_Typedef *mode)
{
    mode->mw          = EMIF1_NOR_SRAM_16_BITS;
    mode->rd_sync     = EMIF1_RW_ASYNC;
    mode->rd_bl       = EMIF1_1_BEAT;
    mode->wr_sync     = EMIF1_RW_ASYNC;
    mode->wr_bl       = EMIF1_1_BEAT;
    mode->baa         = EMIF1_BAA_HIGH;
    mode->adv         = EMIF1_ADV_HIGH;
    mode->bls_tim     = CS_TIMING;
    mode->burst_align = BURSTS_CROSS_ADDRESS_BOUNDARY;
}

/**
 * @brief Init nor flash or sram command configuration structure
 *
 * @param cmd
 */
void EMIF1_ALL_cmdConfig_StructInit(EMIF1_ALL_cmdConfig_Typedef *cmd)
{
    cmd->addr19to0 = 0x0;
    cmd->set_cre   = EMIF1_CRE_LOW;
    cmd->cmd_type  = UPDATEREGS_AXI;
    cmd->chip_nmbr = MEMIF1_CS2;
}

/**
 * @brief Config nor flash or sram configuration structure
 *
 * @param config
 */
void EMIF1_NOR_SRAM_Config(EMIF1_NOR_SRAM_Config_Typedef *config)
{
    uint32_t reg;

    reg = (uint32_t)config->timing.t_rc << EMIF1_SET_CYCLES_set_t0_Pos |
          (uint32_t)config->timing.t_wc << EMIF1_SET_CYCLES_set_t1_Pos |
          (uint32_t)config->timing.t_ceoe << EMIF1_SET_CYCLES_set_t2_Pos |
          (uint32_t)config->timing.t_wp << EMIF1_SET_CYCLES_set_t3_Pos |
          (uint32_t)config->timing.t_pc << EMIF1_SET_CYCLES_set_t4_Pos |
          (uint32_t)config->timing.t_tr << EMIF1_SET_CYCLES_set_t5_Pos |
          (uint32_t)config->timing.we_time << EMIF1_SET_CYCLES_set_t6_Pos;
    WRITE_REG(EMIF1->SET_CYCLES, reg);

    reg = (uint32_t)config->mode.mw << EMIF1_SET_OPMODE_set_mw_Pos |
          (uint32_t)config->mode.rd_sync << EMIF1_SET_OPMODE_set_rd_sync_Pos |
          (uint32_t)config->mode.rd_bl << EMIF1_SET_OPMODE_set_rd_bl_Pos |
          (uint32_t)config->mode.wr_sync << EMIF1_SET_OPMODE_set_wr_sync_Pos |
          (uint32_t)config->mode.wr_bl << EMIF1_SET_OPMODE_set_wr_bl_Pos |
          (uint32_t)config->mode.baa << EMIF1_SET_OPMODE_set_baa_Pos |
          (uint32_t)config->mode.adv << EMIF1_SET_OPMODE_set_adv_Pos |
          (uint32_t)config->mode.bls_tim << EMIF1_SET_OPMODE_set_bls_time_Pos |
          (uint32_t)config->mode.burst_align << EMIF1_SET_OPMODE_set_burst_align_Pos;
    WRITE_REG(EMIF1->SET_OPMODE, reg);

    reg = config->cmd.addr19to0 << EMIF1_DIRECT_CMD_addr_19_to_0_Pos |
          (uint32_t)config->cmd.set_cre << EMIF1_DIRECT_CMD_set_cre_Pos |
          (uint32_t)config->cmd.cmd_type << EMIF1_DIRECT_CMD_cmd_type_Pos |
          (uint32_t)config->cmd.chip_nmbr << EMIF1_DIRECT_CMD_chip_nmbr_Pos;
    WRITE_REG(EMIF1->DIRECT_CMD, reg);
}

/**
 * @brief Deconfig nor flash or sram configuration
 *
 * @param config
 */
void EMIF1_NOR_SRAM_DeConfig(void)
{
    WRITE_REG(EMIF1->SET_CYCLES, DEFALUT_NOR_SRAM_CYCLES_VALUE);
    WRITE_REG(EMIF1->SET_OPMODE, DEFALUT_NOR_SRAM_OPMODE_VALUE);
    WRITE_REG(EMIF1->DIRECT_CMD, DEFALUT_NOR_SRAM_CMD_VALUE);
}

/**
 * @brief
 *
 * @param ITMasks
 */
void EMIF1_ITEnable(uint32_t ITMasks)
{
    assert_param(IS_EMIF1_ITMASK(ITMasks));

    SET_BIT(EMIF1->MEM_CFG_SET, ITMasks);
}

/**
 * @brief
 *
 * @param ITMasks
 */
void EMIF1_ITDisable(uint32_t ITMasks)
{
    assert_param(IS_EMIF1_ITMASK(ITMasks));

    SET_BIT(EMIF1->MEM_CFG_CLR, ITMasks);
}

uint32_t EMIF1_GetITStatus(void)
{
    uint32_t ITMasks = 0;

    if (DRV_IS_BIT_SET(EMIF1->MEMC_STATUS, EMIF1_MEMC_STATUS_int_status0_Msk))
    {
        ITMasks |= EMIF1_IT_IF0_MASK;
    }

    if (DRV_IS_BIT_SET(EMIF1->MEMC_STATUS, EMIF1_MEMC_STATUS_int_status1_Msk))
    {
        ITMasks |= EMIF1_IT_IF1_MASK;
    }

    if (DRV_IS_BIT_SET(EMIF1->MEMC_STATUS, EMIF1_MEMC_STATUS_raw_ecc_int1_Msk))
    {
        ITMasks |= EMIF1_IT_ECC_MASK;
    }

    return ITMasks;
}

/**
 * @brief
 *
 * @param config
 */
void EMIF0_SDRAM_Config(EMIF0_SDRAM_Config_Typedef *config)
{
    uint32_t reg;

    reg = (uint32_t)config->colbits << EMIF0_CFG_DMC_CR_cfg_colbits_Pos |
          (uint32_t)config->bankNmbr << EMIF0_CFG_DMC_CR_cfg_bank_num_Pos |
          (uint32_t)config->sdr_width << EMIF0_CFG_DMC_CR_cfg_sdr_width_Pos |
          (uint32_t)config->mode_reg << EMIF0_CFG_DMC_CR_cfg_sdr_mode_Pos;

    WRITE_REG(EMIF0->CFG_DMC_CR, reg);
}

/**
 * @brief
 *
 * @param timing
 */
void EMIF0_SDRAM_TimingConfig(EMIF0_SDRAM_TimingConfig_Typedef *timing)
{
    uint32_t reg;

    reg = (uint32_t)timing->t_rp << EMIF0_CFG_DMC_TR_cfg_sdr_trp_Pos |
          (uint32_t)timing->t_rcd << EMIF0_CFG_DMC_TR_cfg_sdr_trcd_Pos |
          (uint32_t)timing->t_wr << EMIF0_CFG_DMC_TR_cfg_sdr_twr_Pos |
          (uint32_t)timing->t_rcar << EMIF0_CFG_DMC_TR_cfg_sdr_trcar_Pos |
          (uint32_t)timing->t_cas << EMIF0_CFG_DMC_TR_cfg_sdr_cas_Pos |
          (uint32_t)timing->t_ras << EMIF0_CFG_DMC_TR_cfg_sdr_tras_Pos;
    WRITE_REG(EMIF0->CFG_DMC_TR, reg);
}

/**
 * @brief
 *
 * @param period
 * @param max_ref_num
 */
void EMIF0_SDRAM_RefreshRateConfig(uint16_t period, uint8_t max_ref_num)
{
    uint32_t reg;

    reg = (uint32_t)period << EMIF0_CFG_DMC_RCR_cfg_sdr_rfsh_Pos |
          (uint32_t)max_ref_num << EMIF0_CFG_DMC_RCR_cfg_sdr_rfmax_Pos;
    WRITE_REG(EMIF0->CFG_DMC_RCR, reg);
}

/**
 * @brief Enable EMIF0 SDRAM
 *
 */
void EMIF0_SDRAM_Enable(void)
{
    SET_BIT(EMIF0->CFG_DMC_CR, EMIF0_CFG_DMC_CR_cfg_sdr_en_Msk);
}

/**
 * @}
 */

/**
 * @}
 */

/************************ (C) COPYRIGHT ETMCU *****END OF FILE****/
