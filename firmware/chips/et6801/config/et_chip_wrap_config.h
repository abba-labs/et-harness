#ifndef ET6801_CHIP_WRAP_CONFIG_H
#define ET6801_CHIP_WRAP_CONFIG_H

/**
 * @file et_chip_wrap_config.h
 * @brief ET6801 compile-time facts consumed by the common Wrap layer.
 *
 * This file contains data only: logical IDs, selected SDK objects, capability
 * limits and physical routes. Common Wrap code consumes the tables below and
 * must not depend on ET6801 instance names or topology.
 *
 * Development rules:
 * 1. Keep exactly one section per IP, ordered as capability constants then
 *    final mapping tables or mapping objects.
 * 2. Add only compile-time chip facts consumed by a common Wrap implementation.
 * 3. Do not add functions, mutable state, test flow, Service/Wire facts, board
 *    routes, runtime branches, raw physical addresses or one-use aliases.
 * 4. A new chip provides the same ET_CHIP_* mapping contracts in its own
 *    config directory; existing Wrap source must remain unchanged.
 *
 * Fact-source priority:
 * 1. Reuse the selected ET6801 SDK enum or macro whenever it exists.
 * 2. Reuse generated CMSIS/SVD symbols when the public Driver omits a fact.
 * 3. Define a named local constant only when neither source exposes the fact;
 *    its comment must identify the source, meaning, unit and consumer field.
 */

/* -------------------------------------------------------------------------- */
/* UART                                                                       */
/* -------------------------------------------------------------------------- */

#define ET_CHIP_UART_FEATURE_FLAGS \
    (ET_UART_WRAP_CAP_RX_POLLING | ET_UART_WRAP_CAP_TX_POLLING | \
     ET_UART_WRAP_CAP_RX_IRQ | ET_UART_WRAP_CAP_TX_IRQ | \
     ET_UART_WRAP_CAP_RX_DMA | ET_UART_WRAP_CAP_TX_DMA | \
     ET_UART_WRAP_CAP_FIFO | ET_UART_WRAP_CAP_LOOPBACK | \
     ET_UART_WRAP_CAP_FLOW_CONTROL | ET_UART_WRAP_CAP_BREAK | \
     ET_UART_WRAP_CAP_NINE_BIT | ET_UART_WRAP_CAP_MODEM | \
     ET_UART_WRAP_CAP_HALT | ET_UART_WRAP_CAP_SOFTWARE_RESET)

/*
 * ET6801 public UART APIs use uint16_t transfer lengths. The minimum baudrate
 * is the stable Wrap contract; the maximum comes directly from et6x_uart.h.
 * Field order: min baudrate, max baudrate, max read bytes, max write bytes.
 */
#define ET_CHIP_UART_LIMITS \
    ET_UART_WRAP_MIN_BAUDRATE, UART_BAUDRATE_MAX, UINT16_MAX, UINT16_MAX

/* Stable logical IDs consumed by et_uart_wrap_mapping_t.uart_id. */
enum
{
    ET6801_UART_LOGICAL_0 = 0u,
    ET6801_UART_LOGICAL_1 = 1u,
    ET6801_UART_LOGICAL_2 = 2u
};

/*
 * Field order: logical ID, SDK Driver instance, CMSIS IRQ, Feature flags,
 * then ET_CHIP_UART_LIMITS.
 */
#define ET_CHIP_UART_MAP_TABLE \
    {{ET6801_UART_LOGICAL_0, UART0, UART0_IRQn, ET_CHIP_UART_FEATURE_FLAGS, \
      ET_CHIP_UART_LIMITS}, \
     {ET6801_UART_LOGICAL_1, UART1, UART1_IRQn, ET_CHIP_UART_FEATURE_FLAGS, \
      ET_CHIP_UART_LIMITS}, \
     {ET6801_UART_LOGICAL_2, UART2, UART2_IRQn, ET_CHIP_UART_FEATURE_FLAGS, \
      ET_CHIP_UART_LIMITS}}

/* Driver status-mask order matches et_uart_wrap_status_masks_t. */
#define ET_CHIP_UART_STATUS_MASKS \
    {UART0_LSR_RFE_Msk, UART0_MSR_CTS_Msk, UART0_MSR_DSR_Msk, \
     UART0_MSR_RI_Msk, UART0_MSR_DCD_Msk, UART0_MSR_DCTS_Msk, \
     UART0_MSR_DDSR_Msk, UART0_MSR_TERI_Msk, UART0_MSR_DDCD_Msk, \
     UART0_MCR_RTS_Msk, UART0_MCR_DTR_Msk}

/* -------------------------------------------------------------------------- */
/* GPIO / IOMUX                                                               */
/* -------------------------------------------------------------------------- */

/*
 * Field order: stable logical pin, SDK physical pin, SDK GPIO mux value,
 * stable alternate-function ID, SDK alternate-function mux value.
 * Logical GPIO IDs intentionally reuse the selected SDK GPIO pin symbols.
 */
#define ET_CHIP_GPIO_MAP_TABLE \
    {{GPIO8, GPIO8, GPIO8_MODE_GPIO8, \
      ET_GPIO_FUNCTION_UART_TX, GPIO8_MODE_UART2_TX}, \
     {GPIO9, GPIO9, GPIO9_MODE_GPIO9, \
      ET_GPIO_FUNCTION_UART_RX, GPIO9_MODE_UART2_RX}, \
     {GPIO12, GPIO12, GPIO12_MODE_GPIO12, \
      ET_GPIO_FUNCTION_UART_TX, GPIO12_MODE_UART0_TX}, \
     {GPIO13, GPIO13, GPIO13_MODE_GPIO13, \
      ET_GPIO_FUNCTION_UART_RX, GPIO13_MODE_UART0_RX}, \
     {GPIO44, GPIO44, GPIO44_MODE_GPIO44, \
      ET_GPIO_FUNCTION_UART_TX, GPIO44_MODE_UART1_TX}, \
     {GPIO45, GPIO45, GPIO45_MODE_GPIO45, \
      ET_GPIO_FUNCTION_UART_RX, GPIO45_MODE_UART1_RX}}

/* -------------------------------------------------------------------------- */
/* DMA                                                                        */
/* -------------------------------------------------------------------------- */

#define ET_CHIP_DMA_FEATURE_FLAGS \
    (ET_DMA_WRAP_CAP_MEMORY_TO_MEMORY | \
     ET_DMA_WRAP_CAP_MEMORY_TO_PERIPHERAL | \
     ET_DMA_WRAP_CAP_PERIPHERAL_TO_MEMORY | \
     ET_DMA_WRAP_CAP_PERIPHERAL_TO_PERIPHERAL | \
     ET_DMA_WRAP_CAP_SUSPEND_RESUME | ET_DMA_WRAP_CAP_INTERRUPTS | \
     ET_DMA_WRAP_CAP_RELOAD | ET_DMA_WRAP_CAP_SOURCE_GATHER | \
     ET_DMA_WRAP_CAP_DESTINATION_SCATTER | ET_DMA_WRAP_CAP_LINKED_LIST | \
     ET_DMA_WRAP_CAP_ATOMIC_CHANNEL_MASK_START | \
     ET_DMA_WRAP_CAP_SOFTWARE_HANDSHAKE | \
     ET_DMA_WRAP_CAP_HANDSHAKE_MODE | \
     ET_DMA_WRAP_CAP_HANDSHAKE_POLARITY | \
     ET_DMA_WRAP_CAP_TARGET_CYCLE_TIMING)

/* Stable DMA controller IDs shared by DMA, SYSCTRL and CRG mapping tables. */
enum
{
    ET6801_DMA_LOGICAL_0 = 0u,
    ET6801_DMA_LOGICAL_1 = 1u
};

/*
 * All limits are selected SDK facts. Gather/scatter maxima are obtained from
 * the CMSIS field masks and positions generated from the ET6801 SVD.
 * Field order: channel count, DMAMUX interface count, maximum priority,
 * maximum transfer count, maximum gather/scatter interval and item count.
 */
#define ET_CHIP_DMA_LIMITS \
    AHBDMA_NUM_CHANNELS, (DMAMUX_INTERFACE7 + 1u), AHBDMA_CH_PRIORITY_7, \
        AHBDMA_MAX_BLOCK_TR_SIZE, \
        (AHBDMA0_CH_SGR_SGI_Msk >> AHBDMA0_CH_SGR_SGI_Pos), \
        (AHBDMA0_CH_SGR_SGC_Msk >> AHBDMA0_CH_SGR_SGC_Pos)

/*
 * Field order: stable controller ID, normal/ACC SDK instances, Feature flags,
 * ET_CHIP_DMA_LIMITS, five split CMSIS IRQ routes and the combined IRQ route.
 */
#define ET_CHIP_DMA_MAP_TABLE \
    {{ET6801_DMA_LOGICAL_0, AHBDMA0, AHBDMA0_ACC, ET_CHIP_DMA_FEATURE_FLAGS, \
      ET_CHIP_DMA_LIMITS, \
      DMA0_TFR_IRQn, DMA0_BLOCK_IRQn, DMA0_SRCTRAN_IRQn, \
      DMA0_DSTTRAN_IRQn, DMA0_ERROR_IRQn, DMA0_COMBINED_IRQn}, \
     {ET6801_DMA_LOGICAL_1, AHBDMA1, AHBDMA1_ACC, ET_CHIP_DMA_FEATURE_FLAGS, \
      ET_CHIP_DMA_LIMITS, \
      DMA1_TFR_IRQn, DMA1_BLOCK_IRQn, DMA1_SRCTRAN_IRQn, \
      DMA1_DSTTRAN_IRQn, DMA1_ERROR_IRQn, DMA1_COMBINED_IRQn}}

/* -------------------------------------------------------------------------- */
/* SYSCTRL / DMAMUX                                                           */
/* -------------------------------------------------------------------------- */

/* SDK exposes interfaces 0..7; the count is the last interface plus one. */
#define ET_CHIP_SYSCTRL_DMA_LIMITS (DMAMUX_INTERFACE7 + 1u)

/* Field order: stable DMA controller ID, SDK instance, DMAMUX interface count. */
#define ET_CHIP_SYSCTRL_DMA_MAP_TABLE \
    {{ET6801_DMA_LOGICAL_0, AHBDMA0, ET_CHIP_SYSCTRL_DMA_LIMITS}, \
     {ET6801_DMA_LOGICAL_1, AHBDMA1, ET_CHIP_SYSCTRL_DMA_LIMITS}}

/* -------------------------------------------------------------------------- */
/* CRG                                                                        */
/* -------------------------------------------------------------------------- */

/*
 * The CRG Driver enum omits UART2 and its UART values lag the generated SVD
 * positions by one. These named ET6801 constants combine the SDK group base
 * with generated CMSIS bit positions. They are consumed only by
 * et_crg_wrap_mapping_t.driver_peripheral and keep that fallback fact out of
 * the common Wrap source.
 */
#define ET6801_CRG_PERIPHERAL_UART0 \
    (CRG_PERIPH_CAN0 + CRG_GTEN1_CRG_CLK_GTEN_UART0_Pos)
#define ET6801_CRG_PERIPHERAL_UART1 \
    (CRG_PERIPH_CAN0 + CRG_GTEN1_CRG_CLK_GTEN_UART1_Pos)
#define ET6801_CRG_PERIPHERAL_UART2 \
    (CRG_PERIPH_CAN0 + CRG_GTEN1_CRG_CLK_GTEN_UART2_Pos)

/*
 * The SDK CRG_PERIPH_CORDIC selector points at CRG group 2, while generated
 * CMSIS places the CPU0 CORDIC clock and reset in GTEN0/SRST0 bit 20. Use the
 * generated field position so the common CRG Wrap targets the real instance.
 */
#define ET6801_CRG_PERIPHERAL_CORDIC0 CRG_GTEN0_CRG_CLK_GTEN_CORDIC0_Pos

/*
 * Field order: stable peripheral type, logical instance, SDK CRG selector.
 */
#define ET_CHIP_CRG_MAP_TABLE \
    {{ET_CRG_WRAP_PERIPHERAL_UART, ET6801_UART_LOGICAL_0, \
      ET6801_CRG_PERIPHERAL_UART0}, \
     {ET_CRG_WRAP_PERIPHERAL_UART, ET6801_UART_LOGICAL_1, \
      ET6801_CRG_PERIPHERAL_UART1}, \
     {ET_CRG_WRAP_PERIPHERAL_UART, ET6801_UART_LOGICAL_2, \
      ET6801_CRG_PERIPHERAL_UART2}, \
      {ET_CRG_WRAP_PERIPHERAL_DMA, ET6801_DMA_LOGICAL_0, CRG_PERIPH_AHBDMA0}, \
      {ET_CRG_WRAP_PERIPHERAL_DMA, ET6801_DMA_LOGICAL_1, CRG_PERIPH_AHBDMA1}, \
      {ET_CRG_WRAP_PERIPHERAL_AES, ET6801_AES_LOGICAL_0, CRG_PERIPH_AES}, \
      {ET_CRG_WRAP_PERIPHERAL_FMAC, ET6801_FMAC_LOGICAL_0, CRG_PERIPH_FMAC}, \
      {ET_CRG_WRAP_PERIPHERAL_CORDIC, ET6801_CORDIC_LOGICAL_0, \
       ET6801_CRG_PERIPHERAL_CORDIC0}, \
      {ET_CRG_WRAP_PERIPHERAL_CRC, ET6801_CRC_LOGICAL_0, CRG_PERIPH_CRC}, \
      {ET_CRG_WRAP_PERIPHERAL_STIMER, ET6801_STIMER_LOGICAL_0, CRG_PERIPH_STM0}, \
      {ET_CRG_WRAP_PERIPHERAL_STIMER, ET6801_STIMER_LOGICAL_1, CRG_PERIPH_STM1}, \
      {ET_CRG_WRAP_PERIPHERAL_WDG, ET6801_WDG_LOGICAL_0, CRG_PERIPH_WDG0}, \
      {ET_CRG_WRAP_PERIPHERAL_WDG, ET6801_WDG_LOGICAL_1, CRG_PERIPH_WDG1}, \
      {ET_CRG_WRAP_PERIPHERAL_IPCM, 0u, CRG_PERIPH_IPCM}}

/*
 * CRG owns the WDG clock source and divider. The divider is the encoded
 * six-bit APB1 prescaler field from generated CMSIS, not a WDG register fact.
 */
#define ET6801_CRG_WDG_DIVIDER_MAX \
    ((uint8_t)(CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk >> CRG_PLLCLK_CFG3_CRG_WDG0_STB_Pos))

#define ET_CHIP_CRG_WDG_CLOCK_MAP_TABLE \
    {{ET6801_WDG_LOGICAL_0, WDG0, ET6801_CRG_WDG_DIVIDER_MAX}, \
     {ET6801_WDG_LOGICAL_1, WDG1, ET6801_CRG_WDG_DIVIDER_MAX}}

/* -------------------------------------------------------------------------- */
/* CPU owner / NMI                                                           */
/* -------------------------------------------------------------------------- */

enum
{
    ET6801_CPU_LOGICAL_0 = 0u,
    ET6801_CPU_LOGICAL_1 = 1u
};

/* Field order: stable CPU identity and generated CMSIS CPU register block. */
#define ET_CHIP_CPU_NMI_MAP_TABLE \
    {{ET6801_CPU_LOGICAL_0, CPU0}, \
     {ET6801_CPU_LOGICAL_1, CPU1}}

/* -------------------------------------------------------------------------- */
/* SPINLOCK                                                                   */
/* -------------------------------------------------------------------------- */

#define ET_CHIP_SPINLOCK_FEATURE_FLAGS                                                             \
    (ET_SPINLOCK_WRAP_CAP_ONE_STEP | ET_SPINLOCK_WRAP_CAP_TWO_STEP |                               \
     ET_SPINLOCK_WRAP_CAP_BATCH_RELEASE | ET_SPINLOCK_WRAP_CAP_GLOBAL_RELEASE |                    \
     ET_SPINLOCK_WRAP_CAP_CLEAR_KEY_PROTECTION | ET_SPINLOCK_WRAP_CAP_PEER_JOB |                    \
     ET_SPINLOCK_WRAP_CAP_PEER_MASTER_MAPPING | ET_SPINLOCK_WRAP_CAP_SHARED_STRESS)

enum
{
    ET6801_SPINLOCK_LOGICAL_0 = 0u,
    /* The generated CMSIS register array is the authoritative SVD resource count. */
    ET6801_SPINLOCK_RESOURCE_COUNT =
        sizeof(((SPINLOCK_Type *)0)->SL_LOCK_INFO_ARRAY) /
        sizeof(((SPINLOCK_Type *)0)->SL_LOCK_INFO_ARRAY[0]),
    /* The generated PROCESS_ID field mask is the authoritative SVD value range. */
    ET6801_SPINLOCK_PROCESS_ID_COUNT =
        (SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk >>
         SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos) +
        1u
};

/*
 * Field order: stable logical ID, Feature flags, SDK resource count and SDK
 * Process-ID count. Clear-key values remain private to the selected Driver.
 */
#define ET_CHIP_SPINLOCK_MAP_TABLE                                                                 \
    {                                                                                              \
        {                                                                                          \
            ET6801_SPINLOCK_LOGICAL_0, ET_CHIP_SPINLOCK_FEATURE_FLAGS,                             \
                ET6801_SPINLOCK_RESOURCE_COUNT, ET6801_SPINLOCK_PROCESS_ID_COUNT                   \
        }                                                                                          \
    }

/* -------------------------------------------------------------------------- */
/* CRC                                                                        */
/* -------------------------------------------------------------------------- */

/* Stable singleton logical ID consumed by et_crc_wrap_mapping_t.crc_id. */
enum
{
    ET6801_CRC_LOGICAL_0 = 0u
};

/*
 * Field order: singleton logical CRC ID, generated CMSIS IRQ route and the
 * SDK Driver's maximum FIFO threshold.
 */
#define ET_CHIP_CRC_MAP_TABLE \
    {{ET6801_CRC_LOGICAL_0, CRC_IRQn, CRC_FIFO_TRHD_MAX}}

/* -------------------------------------------------------------------------- */
/* AES                                                                        */
/* -------------------------------------------------------------------------- */

#define ET_CHIP_AES_FEATURE_FLAGS \
    (ET_AES_WRAP_CAP_MODULE_ENABLE | ET_AES_WRAP_CAP_ENCRYPTION | \
     ET_AES_WRAP_CAP_DECRYPTION | ET_AES_WRAP_CAP_KEY_128 | \
     ET_AES_WRAP_CAP_KEY_256 | ET_AES_WRAP_CAP_ECB | \
     ET_AES_WRAP_CAP_CBC | ET_AES_WRAP_CAP_CTR | \
     ET_AES_WRAP_CAP_PADDING | ET_AES_WRAP_CAP_IV | \
     ET_AES_WRAP_CAP_CTR_COUNTER | ET_AES_WRAP_CAP_STATUS | \
     ET_AES_WRAP_CAP_INTERRUPTS | ET_AES_WRAP_CAP_DMA | \
     ET_AES_WRAP_CAP_CPU_REGISTER_PATH | \
     ET_AES_WRAP_CAP_DMA_FIFO_PATH | ET_AES_WRAP_CAP_IRQ_TRANSFER)

/*
 * ET6801 SVD exposes DATA_SIZE0[31:0] plus DATA_SIZE1[3:0]. Neither the
 * Driver nor CMSIS publishes their combined width, so this named constant
 * records the reviewed 36-bit hardware limit consumed by
 * et_aes_wrap_mapping_t.hardware_data_length_bits.
 */
enum
{
    ET6801_AES_LOGICAL_0 = 0u,
    ET6801_AES_DATA_LENGTH_BITS = 36u
};

/*
 * Field order: hardware length width, bounded common process/output limits,
 * supported key/mode/padding/endian/DMA masks, IRQ mask, IRQ-transfer support,
 * then SDK values for FIFO mode and register mode. ET6x AES uses DISABLE for
 * FIFO/fixed-address mode and ENABLE for register/wrap-address mode.
 */
#define ET_CHIP_AES_LIMITS \
    ET6801_AES_DATA_LENGTH_BITS, ET_AES_WRAP_MAX_PROCESS_BYTES, \
        ET_AES_WRAP_MAX_OUTPUT_BYTES, \
        ((1u << ET_AES_WRAP_KEY_128) | (1u << ET_AES_WRAP_KEY_256)), \
        ((1u << ET_AES_WRAP_MODE_ECB) | (1u << ET_AES_WRAP_MODE_CBC) | \
         (1u << ET_AES_WRAP_MODE_CTR)), \
        ((1u << ET_AES_WRAP_PADDING_NONE) | (1u << ET_AES_WRAP_PADDING_ZERO) | \
         (1u << ET_AES_WRAP_PADDING_PKCS7)), \
        ((1u << ET_AES_WRAP_ENDIAN_LITTLE) | (1u << ET_AES_WRAP_ENDIAN_BIG)), \
        ((1u << ET_AES_WRAP_DMA_FIFO) | (1u << ET_AES_WRAP_DMA_REGISTER)), \
        ET_AES_WRAP_IRQ_ALL, ET_AES_WRAP_IRQ_TRANSFER_SUPPORTED, DISABLE, ENABLE

/*
 * Field order: singleton logical AES ID, generated CMSIS IRQ, Feature flags,
 * then ET_CHIP_AES_LIMITS.
 */
#define ET_CHIP_AES_MAP_TABLE \
    {{ET6801_AES_LOGICAL_0, AES_IRQn, ET_CHIP_AES_FEATURE_FLAGS, \
      ET_CHIP_AES_LIMITS}}

/* -------------------------------------------------------------------------- */
/* FMAC                                                                       */
/* -------------------------------------------------------------------------- */

/*
 * Stable singleton ID and hardware limits consumed by et_fmac_wrap_mapping_t.
 * CR.CLR is a self-clearing SVD field; its bounded polling budget prevents a
 * following command from observing stale dynamic state.
 */
enum
{
    ET6801_FMAC_LOGICAL_0 = 0u,
    ET6801_FMAC_LOGICAL_ADDRESS_BITS = 8u,
    ET6801_FMAC_MAX_FEEDFORWARD_TAPS = UINT8_MAX,
    ET6801_FMAC_MAX_FEEDBACK_TAPS = UINT8_MAX,
    ET6801_FMAC_SHIFT_ENCODING_COUNT = 16u,
    ET6801_FMAC_CLEAR_TIMEOUT_BUDGET = 1000000u
};

/*
 * ET6801 exposes four element-count watermark encodings and 16 legal shift
 * encodings. Alignment remains explicitly unknown until target design evidence
 * closes the current FIR/IIR first-valid-output gaps.
 */
#define ET6801_FMAC_WATERMARK_MASK \
    ((1u << 0u) | (1u << 1u) | (1u << 2u) | (1u << 3u))
#define ET6801_FMAC_OUTPUT_MODE_MASK \
    ((1u << ET_FMAC_WRAP_OUTPUT_RAW) | (1u << ET_FMAC_WRAP_OUTPUT_SAT12) | \
     (1u << ET_FMAC_WRAP_OUTPUT_SAT16))

#define ET_CHIP_FMAC_FEATURE_FLAGS \
    (ET_FMAC_WRAP_CAP_FIXED_Q15 | ET_FMAC_WRAP_CAP_FLOAT_INPUT | \
     ET_FMAC_WRAP_CAP_FLOAT_OUTPUT | ET_FMAC_WRAP_CAP_FIR | ET_FMAC_WRAP_CAP_IIR | \
     ET_FMAC_WRAP_CAP_STREAM | ET_FMAC_WRAP_CAP_CLEAR | \
     ET_FMAC_WRAP_CAP_OUTPUT_POLICY | ET_FMAC_WRAP_CAP_STATUS | \
     ET_FMAC_WRAP_CAP_INTERRUPTS | ET_FMAC_WRAP_CAP_DMA_REQUEST | \
     ET_FMAC_WRAP_CAP_TIMED_PROCESS | ET_FMAC_WRAP_CAP_TEST_EXTENSIONS)

/*
 * Field order: logical ID, generated CMSIS IRQ, Feature flags, bounded transfer
 * size, logical address width, P/Q limits, option masks, legal shift width,
 * IRQ mask, the two explicitly unknown first-valid-output indices and the
 * bounded CR.CLR completion polling budget.
 */
#define ET_CHIP_FMAC_MAP_TABLE \
    {{ET6801_FMAC_LOGICAL_0, FMAC_IRQn, ET_CHIP_FMAC_FEATURE_FLAGS, \
      ET_FMAC_WRAP_MAX_TRANSFER_ITEMS, ET6801_FMAC_LOGICAL_ADDRESS_BITS, \
      ET6801_FMAC_MAX_FEEDFORWARD_TAPS, ET6801_FMAC_MAX_FEEDBACK_TAPS, \
      ET6801_FMAC_WATERMARK_MASK, ET6801_FMAC_OUTPUT_MODE_MASK, \
      ET6801_FMAC_SHIFT_ENCODING_COUNT, \
      ET_FMAC_WRAP_IRQ_ALL, ET_FMAC_WRAP_ALIGNMENT_UNKNOWN, ET_FMAC_WRAP_ALIGNMENT_UNKNOWN, \
      ET6801_FMAC_CLEAR_TIMEOUT_BUDGET}}

/* -------------------------------------------------------------------------- */
/* CORDIC                                                                     */
/* -------------------------------------------------------------------------- */

#define ET_CHIP_CORDIC_FEATURE_FLAGS                                                        \
    (ET_CORDIC_WRAP_CAP_FIXED | ET_CORDIC_WRAP_CAP_FLOAT32 |                               \
     ET_CORDIC_WRAP_CAP_WIDTH_16 | ET_CORDIC_WRAP_CAP_WIDTH_32 |                           \
     ET_CORDIC_WRAP_CAP_NORMALIZED_RANGE | ET_CORDIC_WRAP_CAP_DIRECT_ANGLE_RANGE |         \
     ET_CORDIC_WRAP_CAP_POLLING | ET_CORDIC_WRAP_CAP_INTERRUPT |                           \
     ET_CORDIC_WRAP_CAP_ZERO_OVERHEAD |                                                     \
     ET_CORDIC_WRAP_CAP_STATUS | ET_CORDIC_WRAP_CAP_INTERRUPTS)

/* All nine public SDK CORDIC function enumerators are supported. */
#define ET6801_CORDIC_FUNCTION_MASK ((1u << (CORDIC_FUNCTION_TAN + 1u)) - 1u)

enum
{
    ET6801_CORDIC_LOGICAL_0 = 0u,
    /*
     * SVD CTRL0.WORK_MODE保留DMA编码，但ET6801数字设计不实现DMA数据通路。
     * 保留编码仅用于兼容公共映射表，不得对外声明ET_CORDIC_WRAP_CAP_DMA。
     */
    ET6801_CORDIC_DRIVER_WORK_MODE_DMA = 3u
};

/* SDK precision enum stores the hardware encoding, which is cycles minus one. */
#define ET6801_CORDIC_MAXIMUM_PRECISION_CYCLES (CORDIC_PRECISIO_8 + 1u)

/*
 * Field order: stable logical ID, CMSIS IRQ, Feature flags, function mask,
 * maximum SDK Scale, maximum supported precision cycles, SDK DMA mode value.
 */
#define ET_CHIP_CORDIC_MAP_TABLE                                                        \
    {{ET6801_CORDIC_LOGICAL_0, CORDIC_IRQn, ET_CHIP_CORDIC_FEATURE_FLAGS,              \
      ET6801_CORDIC_FUNCTION_MASK, CORDIC_SCALE_7,                                    \
      ET6801_CORDIC_MAXIMUM_PRECISION_CYCLES, ET6801_CORDIC_DRIVER_WORK_MODE_DMA}}

/* -------------------------------------------------------------------------- */
/* WDG                                                                        */
/* -------------------------------------------------------------------------- */

/*
 * Capability flags describe the ET6801 hardware contract declared by the SVD.
 * A failed FPGA/HIL result remains a Case FAIL and must not be hidden by a
 * build-lane-specific capability mask.
 */
#define ET_CHIP_WDG_FEATURE_FLAGS                                                     \
    (ET_WDG_WRAP_FEATURE_ENABLE | ET_WDG_WRAP_FEATURE_FEED |                         \
     ET_WDG_WRAP_FEATURE_WINDOW | ET_WDG_WRAP_FEATURE_RESET_OUTPUT |                 \
     ET_WDG_WRAP_FEATURE_WORK_MODE | ET_WDG_WRAP_FEATURE_HALT_PAUSE |                \
     ET_WDG_WRAP_FEATURE_LOCK | ET_WDG_WRAP_FEATURE_MODULE_RESET |                   \
     ET_WDG_WRAP_FEATURE_INTERRUPTS | ET_WDG_WRAP_FEATURE_PERSISTENT_RECORDS |       \
     ET_WDG_WRAP_FEATURE_CONFIG_READBACK)

enum
{
    ET6801_WDG_LOGICAL_0 = 0u,
    ET6801_WDG_LOGICAL_1 = 1u
};

/*
 * ET6801 SVD defines 32-bit RELOAD/HIGH_THRESHOLD/LOW_THRESHOLD fields.
 * UINT32_MAX therefore expresses both public hardware limits without a local
 * duplicate value. Field order: logical ID, SDK instance, CMSIS IRQ,
 * Feature flags, maximum reload count and maximum window threshold.
 */
#define ET_CHIP_WDG_MAP_TABLE                                                        \
    {{ET6801_WDG_LOGICAL_0, WDG0, WDG0_IRQn, ET_CHIP_WDG_FEATURE_FLAGS,             \
      UINT32_MAX, UINT32_MAX},                                                       \
     {ET6801_WDG_LOGICAL_1, WDG1, WDG1_IRQn, ET_CHIP_WDG_FEATURE_FLAGS,             \
      UINT32_MAX, UINT32_MAX}}

/* -------------------------------------------------------------------------- */
/* STIMER                                                                     */
/* -------------------------------------------------------------------------- */

/*
 * ET6801 SVD exposes six STIMER instances, while the current SDK Driver
 * validates STIMER0/STIMER1 only.  Runtime publishes only Driver-supported
 * instances; the generated Capability file retains all hardware identities.
 */
#define ET_CHIP_STIMER_FEATURE_FLAGS                                                  \
    (ET_STIMER_WRAP_FEATURE_START_STOP | ET_STIMER_WRAP_FEATURE_PERIOD |             \
     ET_STIMER_WRAP_FEATURE_PRESCALER | ET_STIMER_WRAP_FEATURE_ONE_SHOT |            \
     ET_STIMER_WRAP_FEATURE_FREE_RUN | ET_STIMER_WRAP_FEATURE_CLEAR |                \
     ET_STIMER_WRAP_FEATURE_PAUSE_RESUME | ET_STIMER_WRAP_FEATURE_LOAD_MODE |        \
     ET_STIMER_WRAP_FEATURE_LATCH | ET_STIMER_WRAP_FEATURE_COMPARE |                 \
     ET_STIMER_WRAP_FEATURE_INTERRUPTS | ET_STIMER_WRAP_FEATURE_STATUS |             \
     ET_STIMER_WRAP_FEATURE_EVENT_PULSE_WIDTH | ET_STIMER_WRAP_FEATURE_DMA_REQUEST | \
     ET_STIMER_WRAP_FEATURE_DEBUG_HALT |                                           \
     ((ET6801_STIMER_EMERGENCY_SOURCE_MASK != 0u) ?                                  \
          ET_STIMER_WRAP_FEATURE_EMERGENCY_CAPTURE : 0u))

/*
 * ET6801 ERG source selection is a chip fact, not a Case or Service fact.
 * The SVD exposes the 23-bit XBAR ERG enable field, but the current board has
 * no approved safe source route yet.  Keep the default mask disabled so the
 * runtime Capability does not claim a hazardous or unverified route.  A board
 * bring-up may replace this value with one reviewed XBAR_FAULT_* SDK enum.
 */
enum
{
    /* No source is enabled until a board review approves a safe ERG route. */
    ET6801_STIMER_EMERGENCY_SOURCE_ID = 0u,
    ET6801_STIMER_EMERGENCY_TRIGGER_GROUP = 0u,
    ET6801_STIMER_EMERGENCY_SOURCE_MASK = 0u
};

typedef enum
{
    ET6801_STIMER_LOGICAL_0 = 0u,
    ET6801_STIMER_LOGICAL_1 = 1u
} et6801_stimer_logical_id_t;

/*
 * ET6801 system-capture registers address STIMER0 and STIMER1 by these
 * physical indices.  Keep this chip fact out of the common Wrap interface.
 */
typedef enum
{
    ET6801_STIMER_SYSTEM_CAPTURE_INDEX_0 = 0u,
    ET6801_STIMER_SYSTEM_CAPTURE_INDEX_1 = 1u
} et6801_stimer_system_capture_index_t;

enum
{
    /* Reserved mapping byte required by the common positional table layout. */
    ET6801_STIMER_MAP_RESERVED = 0u
};

/*
 * Field order is fixed by et_stimer_wrap_mapping_t:
 * logical id, SDK instance, physical IRQ line, public Feature flags, and the
 * STIMER system index plus logical emergency source mapping consumed by the
 * STIMER Test Driver.
 */
#define ET_CHIP_STIMER_MAP_TABLE                                                      \
    {{ET6801_STIMER_LOGICAL_0, STIMER0, STIMER0_IRQn, ET_CHIP_STIMER_FEATURE_FLAGS,    \
      ET6801_STIMER_SYSTEM_CAPTURE_INDEX_0, ET6801_STIMER_EMERGENCY_SOURCE_ID,          \
      ET6801_STIMER_EMERGENCY_TRIGGER_GROUP, ET6801_STIMER_MAP_RESERVED,                \
      ET6801_STIMER_EMERGENCY_SOURCE_MASK},                                             \
     {ET6801_STIMER_LOGICAL_1, STIMER1, STIMER1_IRQn, ET_CHIP_STIMER_FEATURE_FLAGS,    \
      ET6801_STIMER_SYSTEM_CAPTURE_INDEX_1, ET6801_STIMER_EMERGENCY_SOURCE_ID,          \
      ET6801_STIMER_EMERGENCY_TRIGGER_GROUP, ET6801_STIMER_MAP_RESERVED,                \
      ET6801_STIMER_EMERGENCY_SOURCE_MASK}}

/* -------------------------------------------------------------------------- */
/* IPCM                                                                       */
/* -------------------------------------------------------------------------- */

/*
 * ET6801 has one IPCM controller. Field: public logical controller ID (unit: ID).
 * Endpoint fields: logical ID, SDK channel ID, generated CMSIS IRQ line.
 * This chip uses an identity endpoint mapping; Core ownership is supplied by
 * Execution Mapping, not inferred by the common Wrap. Counts come from CFGSTAT.
 */
#define ET_CHIP_IPCM_MAP_TABLE {{0u}}
#define ET_CHIP_IPCM_ENDPOINT_MAP_TABLE \
    {{IPCM_CH_0, IPCM_CH_0, IPCM0_IRQn}, \
     {IPCM_CH_1, IPCM_CH_1, IPCM1_IRQn}, \
     {IPCM_CH_2, IPCM_CH_2, IPCM2_IRQn}, \
     {IPCM_CH_3, IPCM_CH_3, IPCM3_IRQn}, \
     {IPCM_CH_4, IPCM_CH_4, IPCM4_IRQn}, \
     {IPCM_CH_5, IPCM_CH_5, IPCM5_IRQn}, \
     {IPCM_CH_6, IPCM_CH_6, IPCM6_IRQn}, \
     {IPCM_CH_7, IPCM_CH_7, IPCM7_IRQn}, \
     {IPCM_CH_8, IPCM_CH_8, IPCM8_IRQn}, \
     {IPCM_CH_9, IPCM_CH_9, IPCM9_IRQn}, \
     {IPCM_CH_10, IPCM_CH_10, IPCM10_IRQn}, \
     {IPCM_CH_11, IPCM_CH_11, IPCM11_IRQn}, \
     {IPCM_CH_12, IPCM_CH_12, IPCM12_IRQn}, \
     {IPCM_CH_13, IPCM_CH_13, IPCM13_IRQn}, \
     {IPCM_CH_14, IPCM_CH_14, IPCM14_IRQn}, \
     {IPCM_CH_15, IPCM_CH_15, IPCM15_IRQn}}

/* Ordered by the stable ACK and Link enums. Values are SDK MODE encodings. */
#define ET_CHIP_IPCM_ACK_MAP_TABLE {MANUAL_ACK, AUTO_ACK}
#define ET_CHIP_IPCM_LINK_MAP_TABLE {MANUAL_ACK, AUTO_LINK}

#endif
