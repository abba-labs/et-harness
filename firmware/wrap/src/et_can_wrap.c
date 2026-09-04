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
