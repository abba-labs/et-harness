/** @file et_can_wrap.c @brief Translate CAN primitives without register or cross-IP access. */
#include "et_can_wrap.h"

#include <stddef.h>
#include "et6x_can.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_can_id_t id;
    CAN_Type *instance;
} et_can_mapping_t;

static const et_can_mapping_t mappings[] = ET_CHIP_CAN_MAP_TABLE;
static const et_can_timing_limits_t timing_limits = ET_CHIP_CAN_TIMING_LIMIT_MAP_TABLE;
static const et_can_option_limits_t option_limits = ET_CHIP_CAN_OPTION_LIMIT_MAP_TABLE;

/**
 * @brief Resolve the requested logical controller from immutable chip facts.
 * @param[in] id Public CAN controller identity.
 * @return Driver instance, or NULL when the logical identity is not mapped.
 * @note Performs no MMIO and never falls back to another controller.
 */
static CAN_Type *find_instance(et_can_id_t id)
{
    size_t index;

    for (index = 0u; index < sizeof(mappings) / sizeof(mappings[0]); ++index)
    {
        if (mappings[index].id == id)
        {
            return mappings[index].instance;
        }
    }

    return NULL;
}

/**
 * @brief Read controller revision and endian identities through the CAN Driver.
 * @param[in] id Logical controller identity.
 * @param[out] identity Actual hardware identities, not cached configuration.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note Does not reset hardware, consume receive data or clear protocol errors.
 */
et_wrap_status_t et_can_wrap_get_identity(et_can_id_t id, et_can_identity_t *identity)
{
    CAN_Type *instance = find_instance(id);

    if (identity == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    identity->revision = CAN_testGetRevision(instance);
    identity->endian = CAN_getEndianVal(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Request initialization or bus operation without polling for acknowledgement.
 * @param[in] id Logical controller identity.
 * @param[in] initializing Boolean request to stop bus operation for configuration.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note Changes the CAN initialization request only; PC owns the bounded state wait.
 */
et_wrap_status_t et_can_wrap_set_initializing(et_can_id_t id, uint8_t initializing)
{
    CAN_Type *instance = find_instance(id);

    if (initializing > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_setOpMode(instance,
                  initializing != 0u ? CAN_OPERATION_MODE_SW_INIT : CAN_OPERATION_MODE_NORMAL);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Sample the actual controller initialization state once.
 * @param[in] id Logical controller identity.
 * @param[out] initializing One when hardware reports initialization mode.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note No wait, clock configuration or reset is hidden in this query.
 */
et_wrap_status_t et_can_wrap_get_initializing(et_can_id_t id, uint8_t *initializing)
{
    CAN_Type *instance = find_instance(id);

    if (initializing == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *initializing = (CAN_getOpMode(instance) == CAN_OPERATION_MODE_SW_INIT) ? 1u : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish the selected chip's representable timing counts.
 * @param[in] id Logical controller identity.
 * @param[out] limits Inclusive maxima; every minimum count is one.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note These are encoding limits, not a guarantee of a physical bus bitrate.
 */
et_wrap_status_t et_can_wrap_get_timing_limits(et_can_id_t id, et_can_timing_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = timing_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Check positive physical timing counts before any Driver mutation.
 * @param[in] timing Requested phase timing.
 * @param[in] maximum Corresponding inclusive chip encoding limits.
 * @return One for representable timing with SJW no greater than either segment.
 * @note This is argument validation, not bitrate selection or a test assertion.
 */
static uint8_t timing_is_valid(const et_can_bit_timing_t *timing,
                               const et_can_bit_timing_t *maximum)
{
    return (timing->prescaler > 0u) && (timing->prescaler <= maximum->prescaler) &&
           (timing->segment1 > 0u) && (timing->segment1 <= maximum->segment1) &&
           (timing->segment2 > 0u) && (timing->segment2 <= maximum->segment2) &&
           (timing->sjw > 0u) && (timing->sjw <= maximum->sjw) &&
           (timing->sjw <= timing->segment1) && (timing->sjw <= timing->segment2);
}

/**
 * @brief Configure arbitration and data timing using actual counts.
 * @param[in] id Logical controller identity.
 * @param[in] timing Complete positive timing counts for both phases.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED, STATE_ERROR or IO_ERROR.
 * @note Requires initialization mode; it never stops an active bus implicitly.
 */
et_wrap_status_t et_can_wrap_set_timing(et_can_id_t id, const et_can_timing_t *timing)
{
    CAN_Type *instance = find_instance(id);
    CAN_BitTimingParams encoded;

    if ((timing == NULL) || (timing_is_valid(&timing->nominal, &timing_limits.nominal_max) == 0u) ||
        (timing_is_valid(&timing->data, &timing_limits.data_max) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* The SDK timing structure uses register encodings; the public API never does. */
    encoded.nomRatePrescalar = timing->nominal.prescaler - 1u;
    encoded.nomTimeSeg1 = timing->nominal.segment1 - 1u;
    encoded.nomTimeSeg2 = timing->nominal.segment2 - 1u;
    encoded.nomSynchJumpWidth = timing->nominal.sjw - 1u;
    encoded.dataRatePrescalar = timing->data.prescaler - 1u;
    encoded.dataTimeSeg1 = timing->data.segment1 - 1u;
    encoded.dataTimeSeg2 = timing->data.segment2 - 1u;
    encoded.dataSynchJumpWidth = timing->data.sjw - 1u;

    return CAN_setBitTime(instance, &encoded) == DRV_OK ? ET_WRAP_STATUS_OK
                                                        : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read back both timing phases and convert to actual positive counts.
 * @param[in] id Logical controller identity.
 * @param[out] timing Actual configured timing, independent of the request object.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Reads timing configuration only; protocol status and FIFO state are untouched.
 */
et_wrap_status_t et_can_wrap_get_timing(et_can_id_t id, et_can_timing_t *timing)
{
    CAN_Type *instance = find_instance(id);
    CAN_BitTimingParams encoded;

    if (timing == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getBitTime(instance, &encoded);
    timing->nominal.prescaler = encoded.nomRatePrescalar + 1u;
    timing->nominal.segment1 = encoded.nomTimeSeg1 + 1u;
    timing->nominal.segment2 = encoded.nomTimeSeg2 + 1u;
    timing->nominal.sjw = encoded.nomSynchJumpWidth + 1u;
    timing->data.prescaler = encoded.dataRatePrescalar + 1u;
    timing->data.segment1 = encoded.dataTimeSeg1 + 1u;
    timing->data.segment2 = encoded.dataTimeSeg2 + 1u;
    timing->data.sjw = encoded.dataSynchJumpWidth + 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish the representable TDC and RAM watchdog cycle limits.
 * @param[in] id Logical CAN identity.
 * @param[out] limits Inclusive maxima in controller cycles.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note These hardware limits are not default test configuration or execution budgets.
 */
et_wrap_status_t et_can_wrap_get_option_limits(et_can_id_t id, et_can_option_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = option_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure independent CAN core options using the existing CAN initializer.
 * @param[in] id Logical CAN identity.
 * @param[in] options Complete options supplied by the caller.
 * @return OK or an explicit parameter, state, unsupported or Driver execution error.
 * @note Requires INIT; preserves bit timing, filters and Message RAM layout.
 */
et_wrap_status_t et_can_wrap_set_options(et_can_id_t id, const et_can_options_t *options)
{
    CAN_Type *instance = find_instance(id);
    CAN_InitParams config;

    /* Phase 1: Validate all fields before the SDK can change protected registers. */
    if ((options == NULL) || (options->fd_enabled > 1u) || (options->brs_enabled > 1u) ||
        (options->automatic_retry > 1u) || (options->tx_pause > 1u) ||
        (options->edge_filter > 1u) || (options->protocol_exception > 1u) ||
        (options->tdc_enabled > 1u) ||
        (options->tdc_offset_cycles > option_limits.tdc_offset_cycles) ||
        (options->tdc_filter_cycles > option_limits.tdc_filter_cycles) ||
        (options->ram_watchdog_cycles > option_limits.ram_watchdog_cycles))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Translate positive public semantics to the SDK's disable controls. */
    config.fdMode = options->fd_enabled;
    config.brsEnable = options->brs_enabled;
    config.darEnable = options->automatic_retry == 0u;
    config.txpEnable = options->tx_pause;
    config.efbi = options->edge_filter;
    config.pxhddisable = options->protocol_exception == 0u;
    config.tdcEnable = options->tdc_enabled;
    config.tdcConfig.tdco = options->tdc_offset_cycles;
    config.tdcConfig.tdcf = options->tdc_filter_cycles;
    config.wdcPreload = options->ram_watchdog_cycles;

    return CAN_init(instance, &config) == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read back CAN core options independently of any previous request.
 * @param[in] id Logical CAN identity.
 * @param[out] options Actual core controls and cycle values.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not consume LEC, IRQ sources, FIFO entries or transmit events.
 */
et_wrap_status_t et_can_wrap_get_options(et_can_id_t id, et_can_options_t *options)
{
    CAN_Type *instance = find_instance(id);
    CAN_InitParams config;

    if (options == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetInitConfig(instance, &config);
    options->fd_enabled = config.fdMode;
    options->brs_enabled = config.brsEnable;
    options->automatic_retry = config.darEnable == 0u;
    options->tx_pause = config.txpEnable;
    options->edge_filter = config.efbi;
    options->protocol_exception = config.pxhddisable == 0u;
    options->tdc_enabled = config.tdcEnable;
    options->tdc_offset_cycles = config.tdcConfig.tdco;
    options->tdc_filter_cycles = config.tdcConfig.tdcf;
    options->ram_watchdog_cycles = config.wdcPreload;

    return ET_WRAP_STATUS_OK;
}

/** One allowed payload byte capacity and its private SDK encoding. */
typedef struct
{
    uint32_t bytes;
    uint32_t driver_value;
} et_can_payload_mapping_t;

static const et_can_payload_mapping_t payload_mappings[] = ET_CHIP_CAN_PAYLOAD_MAP_TABLE;
static const et_can_ram_limits_t ram_limits = ET_CHIP_CAN_RAM_LIMIT_MAP_TABLE;

/** A half-open occupied interval inside CAN Message RAM, expressed only in bytes. */
typedef struct
{
    uint32_t offset;
    uint32_t length;
} et_can_ram_region_t;

/**
 * @brief Translate a public payload capacity to the existing SDK element encoding.
 * @param[in] bytes Payload capacity in bytes, without the message header.
 * @param[out] value SDK encoding on success.
 * @return One when supported, zero without modifying hardware otherwise.
 * @note Does not choose a fallback payload capacity.
 */
static int payload_to_driver(uint32_t bytes, uint32_t *value)
{
    size_t index;

    for (index = 0u; index < sizeof(payload_mappings) / sizeof(payload_mappings[0]); ++index)
    {
        if (payload_mappings[index].bytes == bytes)
        {
            *value = payload_mappings[index].driver_value;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Decode a real SDK element encoding to the public byte capacity.
 * @param[in] value Actual hardware encoding from the CAN Driver.
 * @param[out] bytes Public capacity on success.
 * @return One when mapped, zero for an unknown encoding.
 * @note No cached configuration is used.
 */
static int payload_from_driver(uint32_t value, uint32_t *bytes)
{
    size_t index;

    for (index = 0u; index < sizeof(payload_mappings) / sizeof(payload_mappings[0]); ++index)
    {
        if (payload_mappings[index].driver_value == value)
        {
            *bytes = payload_mappings[index].bytes;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Validate occupied regions before any configuration reaches hardware.
 * @param[in] regions Complete list of requested byte intervals.
 * @param[in] count Number of intervals in the local array.
 * @return One for aligned, bounded, non-overlapping regions; zero otherwise.
 * @note Empty regions do not reserve memory; offsets still require legal alignment.
 */
static int ram_regions_valid(const et_can_ram_region_t *regions, size_t count)
{
    size_t index;
    size_t other;

    for (index = 0u; index < count; ++index)
    {
        if ((regions[index].offset % sizeof(uint32_t) != 0u) ||
            (regions[index].offset >= ram_limits.ram_bytes) ||
            (regions[index].length > ram_limits.ram_bytes - regions[index].offset))
        {
            return 0;
        }

        for (other = 0u; other < index; ++other)
        {
            if ((regions[index].length != 0u) && (regions[other].length != 0u) &&
                (regions[index].offset < regions[other].offset + regions[other].length) &&
                (regions[other].offset < regions[index].offset + regions[index].length))
            {
                return 0;
            }
        }
    }

    return 1;
}

/**
 * @brief Publish hardware region limits without selecting a test layout.
 * @param[in] id Logical CAN controller.
 * @param[out] limits Architectural counts and byte aperture.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No reset or Message RAM access is performed.
 */
et_wrap_status_t et_can_wrap_get_ram_limits(et_can_id_t id, et_can_ram_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = ram_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure one complete RAM layout through the CAN Driver only.
 * @param[in] id Logical controller.
 * @param[in] layout Explicit byte offsets, counts, capacities and FIFO policies.
 * @return OK, INVALID_ARGUMENT, STATE_ERROR, NOT_SUPPORTED or IO_ERROR.
 * @note INIT is required. Validation precedes all writes; no RAM contents are initialized.
 */
et_wrap_status_t et_can_wrap_set_ram_layout(et_can_id_t id, const et_can_ram_layout_t *layout)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    /* Phase 1: Check instance, architectural counts and payload encodings without writes. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((layout == NULL) || (layout->std_count > ram_limits.std_count) ||
        (layout->ext_count > ram_limits.ext_count) ||
        (layout->tx_buffer_count > ram_limits.tx_count) ||
        (layout->tx_fifo_count > ram_limits.tx_count) ||
        (layout->tx_buffer_count + layout->tx_fifo_count > ram_limits.tx_count) ||
        (layout->rx0_count > ram_limits.rx_fifo_count) ||
        (layout->rx1_count > ram_limits.rx_fifo_count) ||
        (layout->event_count > ram_limits.event_count) ||
        (layout->rx0_watermark > layout->rx0_count) ||
        (layout->rx1_watermark > layout->rx1_count) ||
        (layout->event_watermark > layout->event_count) || (layout->tx_queue > 1u) ||
        (layout->rx0_overwrite > 1u) || (layout->rx1_overwrite > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (!payload_to_driver(layout->tx_payload_bytes, &config.txBufElemSize) ||
        !payload_to_driver(layout->rx0_payload_bytes, &config.rxFIFO0ElemSize) ||
        !payload_to_driver(layout->rx1_payload_bytes, &config.rxFIFO1ElemSize) ||
        !payload_to_driver(layout->rx_buffer_payload_bytes, &config.rxBufElemSize))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Check actual occupied byte spans; register widths are not memory bounds. */
    {
        const et_can_ram_region_t regions[] = {
            {layout->std_offset,
             layout->std_count * CAN_STD_ID_FILTER_SIZE_WORDS * sizeof(uint32_t)},
            {layout->ext_offset,
             layout->ext_count * CAN_EXT_ID_FILTER_SIZE_WORDS * sizeof(uint32_t)},
            {layout->tx_offset, (layout->tx_buffer_count + layout->tx_fifo_count) *
                                    CAN_getMsgObjSize(config.txBufElemSize) * sizeof(uint32_t)},
            {layout->event_offset,
             layout->event_count * CAN_TX_EVENT_FIFO_SIZE_WORDS * sizeof(uint32_t)},
            {layout->rx0_offset,
             layout->rx0_count * CAN_getMsgObjSize(config.rxFIFO0ElemSize) * sizeof(uint32_t)},
            {layout->rx1_offset,
             layout->rx1_count * CAN_getMsgObjSize(config.rxFIFO1ElemSize) * sizeof(uint32_t)},
            {layout->rx_buffer_offset, ram_limits.rx_buffer_count *
                                           CAN_getMsgObjSize(config.rxBufElemSize) *
                                           sizeof(uint32_t)}};

        if (!ram_regions_valid(regions, sizeof(regions) / sizeof(regions[0])))
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 3: Translate a fully validated layout and execute one own-Driver operation. */
    config.flssa = layout->std_offset;
    config.lss = layout->std_count;
    config.flesa = layout->ext_offset;
    config.lse = layout->ext_count;
    config.txStartAddr = layout->tx_offset;
    config.txBufNum = layout->tx_buffer_count;
    config.txFIFOSize = layout->tx_fifo_count;
    config.txBufMode = layout->tx_queue ? CAN_TX_QUEUE_OPERATION : CAN_TX_FIFO_OPERATION;
    config.txEventFIFOStartAddr = layout->event_offset;
    config.txEventFIFOSize = layout->event_count;
    config.txEventFIFOWaterMark = layout->event_watermark;
    config.rxFIFO0startAddr = layout->rx0_offset;
    config.rxFIFO0size = layout->rx0_count;
    config.rxFIFO0waterMark = layout->rx0_watermark;
    config.rxFIFO0OpMode = layout->rx0_overwrite ? CAN_RX_FIFO_OVERWRITE : CAN_RX_FIFO_BLOCKING;
    config.rxFIFO1startAddr = layout->rx1_offset;
    config.rxFIFO1size = layout->rx1_count;
    config.rxFIFO1waterMark = layout->rx1_watermark;
    config.rxFIFO1OpMode = layout->rx1_overwrite ? CAN_RX_FIFO_OVERWRITE : CAN_RX_FIFO_BLOCKING;
    config.rxBufStartAddr = layout->rx_buffer_offset;

    return CAN_msgRAMConfig(instance, &config) == DRV_OK ? ET_WRAP_STATUS_OK
                                                         : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read every RAM configuration field independently from hardware.
 * @param[in] id Logical controller.
 * @param[out] layout Actual offsets, counts, capacities and FIFO policies.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR for unknown size encoding.
 * @note Does not read or acknowledge queued messages and does not rely on Service state.
 */
et_wrap_status_t et_can_wrap_get_ram_layout(et_can_id_t id, et_can_ram_layout_t *layout)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    if (layout == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    layout->std_offset = config.flssa;
    layout->std_count = config.lss;
    layout->ext_offset = config.flesa;
    layout->ext_count = config.lse;
    layout->tx_offset = config.txStartAddr;
    layout->tx_buffer_count = config.txBufNum;
    layout->tx_fifo_count = config.txFIFOSize;
    layout->tx_queue = config.txBufMode;

    if (!payload_from_driver(config.txBufElemSize, &layout->tx_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    layout->event_offset = config.txEventFIFOStartAddr;
    layout->event_count = config.txEventFIFOSize;
    layout->event_watermark = config.txEventFIFOWaterMark;
    layout->rx0_offset = config.rxFIFO0startAddr;
    layout->rx0_count = config.rxFIFO0size;
    layout->rx0_watermark = config.rxFIFO0waterMark;
    layout->rx0_overwrite = config.rxFIFO0OpMode;
    layout->rx1_offset = config.rxFIFO1startAddr;
    layout->rx1_count = config.rxFIFO1size;
    layout->rx1_watermark = config.rxFIFO1waterMark;
    layout->rx1_overwrite = config.rxFIFO1OpMode;
    layout->rx_buffer_offset = config.rxBufStartAddr;

    if (!payload_from_driver(config.rxBufElemSize, &layout->rx_buffer_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!payload_from_driver(config.rxFIFO0ElemSize, &layout->rx0_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!payload_from_driver(config.rxFIFO1ElemSize, &layout->rx1_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}
