/** @file et_can_wrap.c @brief Translate CAN primitives without register or cross-IP access. */
#include "et_can_wrap.h"

#include <stddef.h>
#include <limits.h>
#include <string.h>
#include "et6x_can.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_can_id_t id;
    CAN_Type *instance;
    et_irq_line_t irq_lines[ET_CAN_IRQ_LINE_COUNT];
} et_can_mapping_t;

typedef struct
{
    uint32_t public_event;
    uint32_t driver_event;
} et_can_irq_mapping_t;

static const et_can_mapping_t mappings[] = ET_CHIP_CAN_MAP_TABLE;
static const et_can_irq_mapping_t irq_mappings[] = ET_CHIP_CAN_IRQ_MAP_TABLE;
static const et_can_timing_limits_t timing_limits = ET_CHIP_CAN_TIMING_LIMIT_MAP_TABLE;
static const et_can_option_limits_t option_limits = ET_CHIP_CAN_OPTION_LIMIT_MAP_TABLE;

/**
 * @brief Resolve the requested logical controller from immutable chip facts.
 * @param[in] id Public CAN controller identity.
 * @return Driver instance, or NULL when the logical identity is not mapped.
 * @note Performs no MMIO and never falls back to another controller.
 */
static const et_can_mapping_t *find_mapping(et_can_id_t id)
{
    size_t index;

    for (index = 0u; index < sizeof(mappings) / sizeof(mappings[0]); ++index)
    {
        if (mappings[index].id == id)
        {
            return &mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Resolve only the selected controller instance.
 * @param[in] id Public logical controller identity.
 * @return Driver instance, or NULL when no exact mapping exists.
 * @note Route metadata stays private to find_mapping().
 */
static CAN_Type *find_instance(et_can_id_t id)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    return mapping == NULL ? NULL : mapping->instance;
}

/**
 * @brief Translate an event mask between public and Driver namespaces.
 * @param[in] mask Source namespace mask.
 * @param[in] to_driver Nonzero maps public events to Driver events.
 * @return Mask in the requested destination namespace.
 * @note Unknown bits are ignored only after callers have validated the public mask.
 */
static uint32_t translate_irq_events(uint32_t mask, uint8_t to_driver)
{
    uint32_t result = 0u;
    size_t index;

    for (index = 0u; index < sizeof(irq_mappings) / sizeof(irq_mappings[0]); ++index)
    {
        uint32_t source =
            to_driver != 0u ? irq_mappings[index].public_event : irq_mappings[index].driver_event;
        uint32_t target =
            to_driver != 0u ? irq_mappings[index].driver_event : irq_mappings[index].public_event;

        if ((mask & source) != 0u)
        {
            result |= target;
        }
    }

    return result;
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

static const uint32_t timestamp_sources[] = ET_CHIP_CAN_TIMESTAMP_MAP_TABLE;
static const uint32_t timeout_sources[] = ET_CHIP_CAN_TIMEOUT_MAP_TABLE;
static const uint32_t unmatched_policies[] = ET_CHIP_CAN_UNMATCHED_MAP_TABLE;
static const et_can_bus_limits_t bus_limits = ET_CHIP_CAN_BUS_LIMIT_MAP_TABLE;

/**
 * @brief Decode one private Driver selector through its public-order map.
 * @param[in] values Chip mapping entries in public enum order.
 * @param[in] count Mapping length.
 * @param[in] value Actual Driver value.
 * @param[out] result Public enum value on success.
 * @return One for a mapped value, zero otherwise.
 * @note Does not replace unknown hardware values with defaults.
 */
static int selector_from_driver(const uint32_t *values, size_t count, uint32_t value,
                                uint32_t *result)
{
    size_t index;

    for (index = 0u; index < count; ++index)
    {
        if (values[index] == value)
        {
            *result = (uint32_t)index;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Set operating, global acceptance and timer parameters through the existing Driver.
 * @param[in] id Logical controller.
 * @param[in] config Explicit public controls; timestamp divisor is an actual count.
 * @return OK or an argument, state, unsupported-instance or Driver error.
 * @note INIT is required; no loopback, RAM layout or bit-timing changes are hidden here.
 */
et_wrap_status_t et_can_wrap_set_bus_config(et_can_id_t id, const et_can_bus_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_ConfigParams driver;

    /* Phase 1: Reject every unsupported selector and count before any Driver write. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((config == NULL) || (config->monitor > 1u) || (config->restricted > 1u) ||
        (config->timeout_enabled > 1u) || (config->reject_remote_ext > 1u) ||
        (config->reject_remote_std > 1u) || (config->timestamp_divisor == 0u) ||
        (config->timestamp_divisor > bus_limits.timestamp_divisor) ||
        (config->timeout_period > bus_limits.timeout_period) ||
        (config->timestamp_source >= ET_CAN_TIMESTAMP_SOURCE_COUNT) ||
        (config->timeout_source >= ET_CAN_TIMEOUT_SOURCE_COUNT) ||
        (config->unmatched_ext >= ET_CAN_UNMATCHED_POLICY_COUNT) ||
        (config->unmatched_std >= ET_CAN_UNMATCHED_POLICY_COUNT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Translate only this Driver group, preserving independent configuration. */
    driver.monEnable = config->monitor;
    driver.asmEnable = config->restricted;
    driver.tsPrescalar = config->timestamp_divisor;
    driver.tsSelect = timestamp_sources[config->timestamp_source];
    driver.timeoutSelect = timeout_sources[config->timeout_source];
    driver.timeoutPreload = config->timeout_period;
    driver.timeoutCntEnable = config->timeout_enabled;
    driver.filterConfig.rrfe = config->reject_remote_ext;
    driver.filterConfig.rrfs = config->reject_remote_std;
    driver.filterConfig.anfe = unmatched_policies[config->unmatched_ext];
    driver.filterConfig.anfs = unmatched_policies[config->unmatched_std];

    return CAN_config(instance, &driver) == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read back current bus configuration without reading error counters.
 * @param[in] id Logical controller.
 * @param[out] config Actual decoded configuration.
 * @return OK, invalid argument, unsupported instance or unknown Driver selector.
 * @note No request cache, FIFO acknowledgement, reset or mode changes are used.
 */
et_wrap_status_t et_can_wrap_get_bus_config(et_can_id_t id, et_can_bus_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_ConfigParams driver;

    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetConfig(instance, &driver);
    config->monitor = driver.monEnable;
    config->restricted = driver.asmEnable;
    config->timestamp_divisor = driver.tsPrescalar;

    if (!selector_from_driver(timestamp_sources,
                              sizeof(timestamp_sources) / sizeof(timestamp_sources[0]),
                              driver.tsSelect, &config->timestamp_source))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!selector_from_driver(timeout_sources, sizeof(timeout_sources) / sizeof(timeout_sources[0]),
                              driver.timeoutSelect, &config->timeout_source))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    config->timeout_period = driver.timeoutPreload;
    config->timeout_enabled = driver.timeoutCntEnable;
    config->reject_remote_ext = driver.filterConfig.rrfe;
    config->reject_remote_std = driver.filterConfig.rrfs;

    if (!selector_from_driver(unmatched_policies,
                              sizeof(unmatched_policies) / sizeof(unmatched_policies[0]),
                              driver.filterConfig.anfe, &config->unmatched_ext))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!selector_from_driver(unmatched_policies,
                              sizeof(unmatched_policies) / sizeof(unmatched_policies[0]),
                              driver.filterConfig.anfs, &config->unmatched_std))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish actual timer count limits for the selected controller.
 * @param[in] id Logical controller.
 * @param[out] limits Actual timestamp divisor and timeout reload maxima.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Read-only chip facts; no bus configuration or timer start.
 */
et_wrap_status_t et_can_wrap_get_bus_limits(et_can_id_t id, et_can_bus_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = bus_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Select disabled, internal or external loopback while already in INIT.
 * @param[in] id Logical controller.
 * @param[in] mode Stable public mode; internal uses MON to isolate external traffic.
 * @return OK, invalid mode, unsupported instance or unmet INIT precondition.
 * @note Exiting internal loopback also clears MON; does not start the controller.
 */
et_wrap_status_t et_can_wrap_set_loopback(et_can_id_t id, et_can_loopback_t mode)
{
    CAN_Type *instance = find_instance(id);

    if ((mode != ET_CAN_LOOPBACK_DISABLED) && (mode != ET_CAN_LOOPBACK_INTERNAL) &&
        (mode != ET_CAN_LOOPBACK_EXTERNAL))
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

    CAN_enbaleLpbkMode(instance,
                       mode == ET_CAN_LOOPBACK_EXTERNAL ? CAN_LPBK_MODE_EXTERNAL
                                                        : CAN_LPBK_MODE_INTERNAL,
                       mode != ET_CAN_LOOPBACK_DISABLED);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Query effective loopback state independently from any prior mode request.
 * @param[in] id Logical controller.
 * @param[out] mode Actual disabled, internal or external state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Reads through the CAN Driver; does not require INIT or change MON.
 */
et_wrap_status_t et_can_wrap_get_loopback(et_can_id_t id, et_can_loopback_t *mode)
{
    CAN_Type *instance = find_instance(id);
    CAN_LpbkMode driver_mode;
    uint32_t enabled;

    if (mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetLoopback(instance, &enabled, &driver_mode);
    *mode = enabled == 0u                           ? ET_CAN_LOOPBACK_DISABLED
            : driver_mode == CAN_LPBK_MODE_INTERNAL ? ET_CAN_LOOPBACK_INTERNAL
                                                    : ET_CAN_LOOPBACK_EXTERNAL;

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

static const uint32_t rx_fifo_numbers[] = ET_CHIP_CAN_RX_FIFO_MAP_TABLE;

/** Private SDK message packing facts; public frames never contain shifted identifiers. */
typedef struct
{
    uint32_t standard_id_shift;
    uint32_t standard_id_max;
    uint32_t extended_id_max;
    uint32_t basic_marker_max;
} et_can_frame_mapping_t;

static const et_can_frame_mapping_t frame_mapping = ET_CHIP_CAN_FRAME_MAP_TABLE;

/**
 * @brief Validate protocol fields before converting to the existing SDK TX element.
 * @param[in] frame Public unshifted frame and explicit control flags.
 * @param[out] element Driver-format header and payload on success.
 * @return One for a supported basic element; zero without hardware access otherwise.
 * @note Wide-marker mode is not implied by an oversized basic marker.
 */
static int encode_tx_element(const et_can_tx_frame_t *frame, CAN_TxBufElement *element)
{
    const uint32_t allowed_flags = ET_CAN_FRAME_EXTENDED | ET_CAN_FRAME_REMOTE | ET_CAN_FRAME_FD |
                                   ET_CAN_FRAME_BRS | ET_CAN_FRAME_ESI | ET_CAN_FRAME_STORE_EVENT |
                                   ET_CAN_FRAME_CAPTURE_TIME;
    size_t index;

    if ((frame == NULL) || (frame->flags & ~allowed_flags) || (frame->dlc > ET_CAN_FRAME_DLC_MAX) ||
        (frame->marker > frame_mapping.basic_marker_max))
    {
        return 0;
    }

    (void)memset(element, 0, sizeof(*element));
    element->xtd = (frame->flags & ET_CAN_FRAME_EXTENDED) != 0u;
    element->rtr = (frame->flags & ET_CAN_FRAME_REMOTE) != 0u;
    element->fdf = (frame->flags & ET_CAN_FRAME_FD) != 0u;
    element->brs = (frame->flags & ET_CAN_FRAME_BRS) != 0u;
    element->esi = (frame->flags & ET_CAN_FRAME_ESI) != 0u;

    if ((frame->identifier >
         (element->xtd ? frame_mapping.extended_id_max : frame_mapping.standard_id_max)) ||
        (element->fdf && element->rtr) || (!element->fdf && (element->brs || element->esi)))
    {
        return 0;
    }

    element->id =
        element->xtd ? frame->identifier : frame->identifier << frame_mapping.standard_id_shift;
    element->dlc = frame->dlc;
    element->mm = frame->marker;
    element->efc = (frame->flags & ET_CAN_FRAME_STORE_EVENT) != 0u;
    element->tx_tsce = (frame->flags & ET_CAN_FRAME_CAPTURE_TIME) != 0u;

    for (index = 0u; index < ET_CAN_FRAME_DATA_BYTES; ++index)
    {
        element->data[index] = frame->data[index];
    }

    return 1;
}

/**
 * @brief Prepare one allocated TX element without requesting transmission.
 * @param[in] id Logical controller.
 * @param[in] index Dedicated buffer or current FIFO/Queue put index.
 * @param[in] frame Explicit protocol frame; unused payload bytes are ignored by the Driver.
 * @return OK or an argument, busy, state, unsupported-instance or Driver error.
 * @note Checks actual RAM configuration and pending state; no polling or implicit reset.
 */
et_wrap_status_t et_can_wrap_write_tx(et_can_id_t id, uint32_t index,
                                      const et_can_tx_frame_t *frame)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_TxFIFOStatus fifo;
    CAN_TxBufElement element;
    uint32_t capacity;
    uint32_t total;

    /* Phase 1: Validate the public frame and independently read the allocated slot. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (!encode_tx_element(frame, &element))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    total = config.txBufNum + config.txFIFOSize;

    if ((total > ram_limits.tx_count) || (index >= total) ||
        (index >= sizeof(uint32_t) * CHAR_BIT) ||
        !payload_from_driver(config.txBufElemSize, &capacity) ||
        (CAN_testGetPayloadSize(element.dlc, element.fdf, element.rtr) > capacity))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    {
        const et_can_ram_region_t region = {
            config.txStartAddr, total * CAN_getMsgObjSize(config.txBufElemSize) * sizeof(uint32_t)};

        if (!ram_regions_valid(&region, 1u))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }
    }

    /* Phase 2: Protect hardware-owned pending/queued slots; acceptance is not completion. */
    if ((CAN_getTxBufReqPend(instance) & (1u << index)) != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (index >= config.txBufNum)
    {
        CAN_getTxFIFOQueStatus(instance, &fifo);

        if ((fifo.fifoFull != 0u) || (index != fifo.putIdx))
        {
            return ET_WRAP_STATUS_BUSY;
        }
    }

    if (element.fdf && !CAN_isFDOpEnable(instance))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    CAN_writeMsgRam(instance, CAN_MEM_TYPE_BUF, index, &element);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Request one or more prepared buffers using one atomic Driver write.
 * @param[in] id Logical controller.
 * @param[in] mask Nonzero bitmap of allocated TX buffers.
 * @return OK or invalid mask, state, busy or unsupported-instance result.
 * @note Does not populate frames, poll completion or retry a request.
 */
et_wrap_status_t et_can_wrap_request_tx(et_can_id_t id, uint32_t mask)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    uint32_t total;
    uint32_t allowed;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    total = config.txBufNum + config.txFIFOSize;

    if ((total == 0u) || (total > ram_limits.tx_count) || (total > sizeof(mask) * CHAR_BIT))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    allowed = total == sizeof(mask) * CHAR_BIT ? UINT32_MAX : (1u << total) - 1u;

    if ((mask == 0u) || ((mask & ~allowed) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) == CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if ((CAN_getTxBufReqPend(instance) & mask) != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    CAN_testRequestTxMask(instance, mask);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read TX request/completion/cancellation and FIFO state.
 * @param[in] id Logical controller.
 * @param[out] status Independent hardware status fields.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not clear completion bits or consume TX events.
 */
et_wrap_status_t et_can_wrap_get_tx_status(et_can_id_t id, et_can_tx_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_TxFIFOStatus fifo;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getTxFIFOQueStatus(instance, &fifo);
    status->pending = CAN_getTxBufReqPend(instance);
    status->completed = CAN_getTxBufTransmissionStatus(instance);
    status->cancelled = CAN_txBufCancellationStatus(instance);
    status->free_count = fifo.freeLvl;
    status->get_index = fifo.getIdx;
    status->put_index = fifo.putIdx;
    status->full = fifo.fifoFull;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read actual TX Event FIFO occupancy without consuming an event.
 * @param[in] id Logical controller.
 * @param[out] status Fill, indices, full and lost facts from one Driver sample.
 * @return OK or an argument, unsupported-instance or invalid-hardware-state error.
 * @note A full or lost indication is an observation, not a test verdict.
 */
et_wrap_status_t et_can_wrap_get_tx_event_status(et_can_id_t id, et_can_tx_event_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_TxEventFIFOStatus actual;
    uint32_t count;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    CAN_getTxEventFIFOStatus(instance, &actual);
    count = config.txEventFIFOSize;

    /* Validate every Driver field before publishing a coherent public snapshot. */
    if ((count > ram_limits.event_count) || (actual.fillLvl > count) || (actual.fifoFull > 1u) ||
        (actual.eleLost > 1u) ||
        ((count == 0u) && ((actual.fillLvl != 0u) || (actual.getIdx != 0u) ||
                           (actual.putIdx != 0u) || (actual.fifoFull != 0u))) ||
        ((count != 0u) && ((actual.getIdx >= count) || (actual.putIdx >= count))))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    status->fill = actual.fillLvl;
    status->get_index = actual.getIdx;
    status->put_index = actual.putIdx;
    status->full = actual.fifoFull;
    status->lost = actual.eleLost;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current TX Event FIFO head through the existing CAN Driver.
 * @param[in] id Logical controller.
 * @param[out] event Actual event metadata and current hardware Get Index.
 * @return OK or an argument, empty FIFO, bad layout or unsupported-instance error.
 * @note The event remains owned by hardware until et_can_wrap_ack_tx_event is called.
 */
et_wrap_status_t et_can_wrap_read_tx_event(et_can_id_t id, et_can_tx_event_t *event)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_TxEventFIFOElement actual;
    et_can_tx_event_status_t status;
    et_can_ram_region_t region;
    et_wrap_status_t result;
    uint32_t count;

    if (event == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    /* Phase 1: Confirm a configured, non-empty and in-range hardware FIFO head. */
    result = et_can_wrap_get_tx_event_status(id, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if (status.fill == 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    count = config.txEventFIFOSize;
    region.offset = config.txEventFIFOStartAddr;
    region.length = count * CAN_TX_EVENT_FIFO_SIZE_WORDS * sizeof(uint32_t);

    if ((count == 0u) || !ram_regions_valid(&region, 1u))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Read exactly the current head; no hidden acknowledge or polling follows. */
    (void)memset(&actual, 0, sizeof(actual));
    CAN_readTxEventFIFO(instance, &actual);

    if ((actual.xtd > 1u) || (actual.rtr > 1u) || (actual.esi > 1u) || (actual.brs > 1u) ||
        (actual.fdf > 1u) || (actual.dlc > ET_CAN_FRAME_DLC_MAX) ||
        ((actual.et != ET_CAN_TX_EVENT_TRANSMITTED) &&
         (actual.et != ET_CAN_TX_EVENT_TRANSMITTED_AFTER_CANCEL)) ||
        (actual.id > frame_mapping.extended_id_max) ||
        ((actual.xtd == 0u) &&
         ((((actual.id >> frame_mapping.standard_id_shift) << frame_mapping.standard_id_shift) !=
           actual.id) ||
          ((actual.id >> frame_mapping.standard_id_shift) > frame_mapping.standard_id_max))))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    event->identifier = actual.xtd ? actual.id : actual.id >> frame_mapping.standard_id_shift;
    event->flags = (actual.xtd ? ET_CAN_FRAME_EXTENDED : 0u) |
                   (actual.rtr ? ET_CAN_FRAME_REMOTE : 0u) | (actual.fdf ? ET_CAN_FRAME_FD : 0u) |
                   (actual.brs ? ET_CAN_FRAME_BRS : 0u) | (actual.esi ? ET_CAN_FRAME_ESI : 0u);
    event->dlc = actual.dlc;
    event->timestamp = actual.txts;
    event->event_type = actual.et;
    event->marker = actual.mm;
    event->index = status.get_index;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge the current TX Event FIFO head through the CAN Driver.
 * @param[in] id Logical controller.
 * @param[in] index Get Index returned by the preceding status or event read.
 * @return OK or an argument, empty/stale index, unsupported-instance or Driver error.
 * @note The current hardware status closes the SDK boundary-check gap before the write.
 */
et_wrap_status_t et_can_wrap_ack_tx_event(et_can_id_t id, uint32_t index)
{
    CAN_Type *instance = find_instance(id);
    et_can_tx_event_status_t status;
    et_wrap_status_t result;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    result = et_can_wrap_get_tx_event_status(id, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if ((status.fill == 0u) || (index != status.get_index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return CAN_writeTxEventFIFOAck(instance, index) == DRV_OK ? ET_WRAP_STATUS_OK
                                                              : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read one selected receive FIFO without acknowledging entries.
 * @param[in] id Logical controller.
 * @param[in] fifo Public FIFO index.
 * @param[out] status Actual fill, get, put, full and lost status.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, reset or read protocol error counters.
 */
et_wrap_status_t et_can_wrap_get_rx_fifo_status(et_can_id_t id, uint32_t fifo,
                                                et_can_rx_fifo_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxFIFOStatus driver;

    if ((status == NULL) || (fifo >= sizeof(rx_fifo_numbers) / sizeof(rx_fifo_numbers[0])))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    driver.num = rx_fifo_numbers[fifo];
    CAN_getRxFIFOStatus(instance, &driver);
    status->fill = driver.fillLvl;
    status->get_index = driver.getIdx;
    status->put_index = driver.putIdx;
    status->full = driver.fifoFull;
    status->lost = driver.msgLost;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read dedicated-buffer new-data status without clearing it.
 * @param[in] id Logical controller.
 * @param[out] status Actual low and high new-data bitmaps.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No buffer data is consumed and no acknowledgement is issued.
 */
et_wrap_status_t et_can_wrap_get_rx_buffer_status(et_can_id_t id, et_can_rx_buffer_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxNewDataStatus driver;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getNewDataStatus(instance, &driver);
    status->low = driver.statusLow;
    status->high = driver.statusHigh;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge explicit dedicated-buffer new-data bits.
 * @param[in] id Logical controller.
 * @param[in] status Caller-selected low/high masks, not an implicit clear-all.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not change filters, data bytes or receive FIFO state.
 */
et_wrap_status_t et_can_wrap_ack_rx_buffers(et_can_id_t id, const et_can_rx_buffer_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxNewDataStatus driver;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    driver.statusLow = status->low;
    driver.statusHigh = status->high;
    CAN_clearNewDataStatus(instance, &driver);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge the current head of a nonempty receive FIFO.
 * @param[in] id Logical controller.
 * @param[in] fifo Public FIFO index.
 * @param[in] index Previously observed head index, preventing accidental acknowledgement drift.
 * @return OK or invalid index, empty FIFO, unsupported instance or Driver error.
 * @note Acknowledges exactly one head; no bulk draining or polling is performed.
 */
et_wrap_status_t et_can_wrap_ack_rx_fifo(et_can_id_t id, uint32_t fifo, uint32_t index)
{
    et_can_rx_fifo_status_t status;
    et_wrap_status_t result = et_can_wrap_get_rx_fifo_status(id, fifo, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if (status.fill == 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (index != status.get_index)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return CAN_writeRxFIFOAck(find_instance(id), rx_fifo_numbers[fifo], index) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read one available RX element without acknowledging it.
 * @param[in] id Logical controller.
 * @param[in] source Dedicated buffer, FIFO0 or FIFO1.
 * @param[in] index Dedicated-buffer index; must be zero for FIFO head reads.
 * @param[out] frame Observed header, valid stored bytes and selected storage index.
 * @return OK, invalid selector/index, empty storage, bad layout or unsupported instance.
 * @note No polling or automatic acknowledgement; a short slot returns only stored bytes.
 */
et_wrap_status_t et_can_wrap_read_rx(et_can_id_t id, et_can_rx_source_t source, uint32_t index,
                                     et_can_rx_frame_t *frame)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_RxBufElement element;
    et_can_rx_fifo_status_t fifo_status;
    et_can_rx_buffer_status_t buffer_status;
    et_wrap_status_t result;
    uint32_t fifo = 0u;
    uint32_t driver_size;
    uint32_t offset;
    uint32_t capacity;
    uint32_t mem_type;
    uint32_t data_length;
    size_t byte;

    /* Phase 1: Resolve an available hardware-owned element and its actual RAM slot. */
    if ((frame == NULL) || ((source != ET_CAN_RX_BUFFER) && (source != ET_CAN_RX_FIFO0) &&
                            (source != ET_CAN_RX_FIFO1)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);

    if (source == ET_CAN_RX_BUFFER)
    {
        const uint32_t word_bits = sizeof(uint32_t) * CHAR_BIT;
        uint32_t active;

        if ((index >= ram_limits.rx_buffer_count) || (index >= word_bits + word_bits))
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        result = et_can_wrap_get_rx_buffer_status(id, &buffer_status);

        if (result != ET_WRAP_STATUS_OK)
        {
            return result;
        }

        active = index < word_bits ? buffer_status.low : buffer_status.high;

        if ((active & (1u << (index % word_bits))) == 0u)
        {
            return ET_WRAP_STATUS_BUSY;
        }

        driver_size = config.rxBufElemSize;
        offset = config.rxBufStartAddr;
        mem_type = CAN_MEM_TYPE_BUF;
    }
    else
    {
        if (index != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        fifo = source == ET_CAN_RX_FIFO0 ? 0u : 1u;
        result = et_can_wrap_get_rx_fifo_status(id, fifo, &fifo_status);

        if (result != ET_WRAP_STATUS_OK)
        {
            return result;
        }

        if (fifo_status.fill == 0u)
        {
            return ET_WRAP_STATUS_BUSY;
        }

        index = fifo_status.get_index;

        if (index >= (fifo == 0u ? config.rxFIFO0size : config.rxFIFO1size))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }

        driver_size = fifo == 0u ? config.rxFIFO0ElemSize : config.rxFIFO1ElemSize;
        offset = fifo == 0u ? config.rxFIFO0startAddr : config.rxFIFO1startAddr;
        mem_type = CAN_MEM_TYPE_FIFO;
    }

    /* Phase 2: Bound the physical slot before the Driver reads Message RAM. */
    if (!payload_from_driver(driver_size, &capacity))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    {
        const uint32_t stride = CAN_getMsgObjSize(driver_size) * sizeof(uint32_t);
        const et_can_ram_region_t region = {offset + index * stride, stride};

        if (!ram_regions_valid(&region, 1u))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }
    }

    (void)memset(&element, 0, sizeof(element));
    CAN_readMsgRam(instance, mem_type, index, rx_fifo_numbers[fifo], &element);
    data_length = CAN_testGetPayloadSize(element.dlc, element.fdf, element.rtr);

    /* Phase 3: Publish actual metadata and stored bytes, keeping acknowledgement explicit. */
    (void)memset(frame, 0, sizeof(*frame));
    frame->identifier = element.xtd ? element.id : element.id >> frame_mapping.standard_id_shift;
    frame->flags = (element.xtd ? ET_CAN_FRAME_EXTENDED : 0u) |
                   (element.rtr ? ET_CAN_FRAME_REMOTE : 0u) | (element.fdf ? ET_CAN_FRAME_FD : 0u) |
                   (element.brs ? ET_CAN_FRAME_BRS : 0u) | (element.esi ? ET_CAN_FRAME_ESI : 0u);
    frame->dlc = element.dlc;
    frame->timestamp = element.rxts;
    frame->filter_index = element.fidx;
    frame->nonmatching = element.anmf;
    frame->data_length = data_length < capacity ? data_length : capacity;
    frame->index = index;

    for (byte = 0u; byte < frame->data_length; ++byte)
    {
        frame->data[byte] = (uint8_t)element.data[byte];
    }

    return ET_WRAP_STATUS_OK;
}

static const uint32_t standard_filter_types[] = ET_CHIP_CAN_STD_FILTER_MAP_TABLE;
static const uint32_t extended_filter_types[] = ET_CHIP_CAN_EXT_FILTER_MAP_TABLE;
static const uint32_t filter_actions[] = ET_CHIP_CAN_FILTER_ACTION_MAP_TABLE;
static const uint32_t filter_sizes[] = ET_CHIP_CAN_FILTER_SIZE_MAP_TABLE;

/**
 * @brief Validate an allocated filter location against the actual RAM layout.
 * @param[in] instance Resolved CAN Driver instance.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Filter index, not byte offset.
 * @return One when the complete element is inside the configured list and RAM.
 * @note Guards a corrupted layout without resetting it or guessing an address.
 */
static int filter_location_valid(CAN_Type *instance, uint32_t extended, uint32_t index)
{
    CAN_MsgRAMConfigParams layout;
    uint32_t count;
    et_can_ram_region_t region;

    CAN_testGetMsgRAMConfig(instance, &layout);
    count = extended ? layout.lse : layout.lss;

    if ((index >= count) || (count > (extended ? ram_limits.ext_count : ram_limits.std_count)))
    {
        return 0;
    }

    region.offset = extended ? layout.flesa : layout.flssa;
    region.length = count * filter_sizes[extended];

    return ram_regions_valid(&region, 1u);
}

/**
 * @brief Check public filter semantics before writing a RAM element.
 * @param[in] extended Validated frame format selector.
 * @param[in] filter Public operation and identifiers.
 * @return One for representable semantics, zero otherwise.
 * @note Dedicated Buffer mode is exact ID matching; debug/timestamp bits are excluded.
 */
static int filter_values_valid(uint32_t extended, const et_can_filter_t *filter)
{
    uint32_t maximum = extended ? frame_mapping.extended_id_max : frame_mapping.standard_id_max;
    const uint32_t *types = extended ? extended_filter_types : standard_filter_types;

    if ((filter->type > ET_CAN_FILTER_DISABLED) || (filter->action > ET_CAN_FILTER_ACTION_BUFFER) ||
        (filter->id1 > maximum) || (filter->id2 > maximum) || (types[filter->type] == UINT32_MAX))
    {
        return 0;
    }

    if (filter->action == ET_CAN_FILTER_ACTION_BUFFER)
    {
        return (filter->type == ET_CAN_FILTER_RANGE) && (filter->id2 == 0u) &&
               (filter->buffer_index < ram_limits.rx_buffer_count);
    }

    if (filter->buffer_index != 0u)
    {
        return 0;
    }

    if (((filter->type == ET_CAN_FILTER_RANGE) || (filter->type == ET_CAN_FILTER_RANGE_NO_MASK)) &&
        (filter->id2 < filter->id1))
    {
        return 0;
    }

    return 1;
}

/**
 * @brief Program one existing filter slot through the CAN Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Slot within the configured list.
 * @param[in] filter Explicit matching operation and destination.
 * @return OK or an argument, mapping or initialization error.
 * @note Requires INIT; does not resize lists, clear other entries or start CAN.
 */
et_wrap_status_t et_can_wrap_set_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        const et_can_filter_t *filter)
{
    CAN_Type *instance = find_instance(id);
    CAN_StdMsgIDFilterElement standard;
    CAN_ExtMsgIDFilterElement ext;
    uint32_t second;

    /* Phase 1: Reject malformed selectors and locations before any RAM write. */
    if ((filter == NULL) || (extended > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (!filter_values_valid(extended, filter) || !filter_location_valid(instance, extended, index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Map semantic Buffer index separately from the ordinary second ID. */
    second = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? filter->buffer_index : filter->id2;

    if (extended != 0u)
    {
        ext.efid1 = filter->id1;
        ext.efid2 = second;
        ext.efec = filter_actions[filter->action];
        ext.eft = extended_filter_types[filter->type];
        CAN_addExtMsgIDFilter(instance, index, &ext);
    }
    else
    {
        standard.sfid1 = filter->id1;
        standard.sfid2 = second;
        standard.sfec = filter_actions[filter->action];
        standard.sft = standard_filter_types[filter->type];
        CAN_addStdMsgIDFilter(instance, index, &standard);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read actual filter RAM and translate its basic acceptance semantics.
 * @param[in] id Logical CAN controller.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Slot within the current list.
 * @param[out] filter Independently decoded RAM contents.
 * @return OK or an argument, mapping, Driver or unrepresentable-format error.
 * @note Does not return the last SET; timestamp/debug-buffer forms require another API.
 */
et_wrap_status_t et_can_wrap_get_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        et_can_filter_t *filter)
{
    CAN_Type *instance = find_instance(id);
    CAN_StdMsgIDFilterElement standard;
    CAN_ExtMsgIDFilterElement ext;
    uint32_t type;
    uint32_t action;
    uint32_t second;
    const uint32_t *types;

    /* Phase 1: Validate the location and read only the requested RAM element. */
    if ((filter == NULL) || (extended > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (!filter_location_valid(instance, extended, index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (extended != 0u)
    {
        if (CAN_testGetExtMsgIDFilter(instance, index, &ext) != DRV_OK)
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }

        filter->id1 = ext.efid1;
        second = ext.efid2;
        type = ext.eft;
        action = ext.efec;
        types = extended_filter_types;
    }
    else
    {
        if (CAN_testGetStdMsgIDFilter(instance, index, &standard) != DRV_OK)
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }

        filter->id1 = standard.sfid1;
        second = standard.sfid2;
        type = standard.sft;
        action = standard.sfec;
        types = standard_filter_types;
    }

    /* Phase 2: Decode actual selectors; never silently discard unsupported Buffer bits. */
    if (!selector_from_driver(types, sizeof(standard_filter_types) / sizeof(types[0]), type,
                              &filter->type) ||
        !selector_from_driver(filter_actions, sizeof(filter_actions) / sizeof(filter_actions[0]),
                              action, &filter->action))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    filter->buffer_index = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? second : 0u;
    filter->id2 = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? 0u : second;

    if ((filter->action == ET_CAN_FILTER_ACTION_BUFFER) &&
        (filter->buffer_index >= ram_limits.rx_buffer_count))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program the extended acceptance AND mask via the existing CAN Driver.
 * @param[in] id Logical controller.
 * @param[in] mask Public unshifted extended identifier mask.
 * @return OK or an argument, state or Driver error.
 * @note Requires INIT and does not change individual filters or global acceptance.
 */
et_wrap_status_t et_can_wrap_set_extended_mask(et_can_id_t id, uint32_t mask)
{
    CAN_Type *instance = find_instance(id);

    if (mask > frame_mapping.extended_id_max)
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

    return CAN_setExtIDAndMask(instance, mask) == DRV_OK ? ET_WRAP_STATUS_OK
                                                         : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read the extended acceptance AND mask without changing controller state.
 * @param[in] id Logical controller.
 * @param[out] mask Actual unshifted mask from hardware.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No cached requests, filter rewrites or receive acknowledgements.
 */
et_wrap_status_t et_can_wrap_get_extended_mask(et_can_id_t id, uint32_t *mask)
{
    CAN_Type *instance = find_instance(id);

    if (mask == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *mask = CAN_getExtIDANDMask(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the CAN Driver High Priority Message status once.
 * @param[in] id Logical CAN controller.
 * @param[out] status Public storage, filter-list and index facts.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR.
 * @note Does not read Message RAM, acknowledge FIFO data or clear High Priority IRQ.
 */
et_wrap_status_t et_can_wrap_get_high_priority_status(et_can_id_t id,
                                                      et_can_high_priority_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_HighPriorityMsgInfo actual;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getHighPriorityMsgStatus(instance, &actual);

    /* Reject reserved Driver values instead of exporting corrupt status as a valid event. */
    if ((actual.msi > ET_CAN_HIGH_PRIORITY_FIFO1) || (actual.filterList > 1u))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    status->buffer_index = actual.bufIdx;
    status->storage = actual.msi;
    status->filter_index = actual.filterIdx;
    status->extended_filter = actual.filterList;

    return ET_WRAP_STATUS_OK;
}

static const uint32_t protocol_errors[] = ET_CHIP_CAN_ERROR_MAP_TABLE;
static const uint32_t protocol_activities[] = ET_CHIP_CAN_ACTIVITY_MAP_TABLE;

/**
 * @brief Consume protocol and error-counter observations exactly once each.
 * @param[in] id Logical controller.
 * @param[out] status Decoded first observations, never a cached expected state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note PSR then ECR are read in order; read-clear flags are consumed, with no retry.
 *       These are consecutive hardware samples, not a simultaneous atomic snapshot.
 */
et_wrap_status_t et_can_wrap_consume_protocol_status(et_can_id_t id,
                                                     et_can_protocol_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_ProtocolStatus protocol;
    CAN_ErrCntStatus counters;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    /* Phase 1: Consume each read-clear register once through the own Driver. */
    CAN_getProtocolStatus(instance, &protocol);
    CAN_getErrCounters(instance, &counters);

    /* Phase 2: Map symbolic encodings and copy explicit observations without retries. */
    if ((selector_from_driver(protocol_errors, sizeof(protocol_errors) / sizeof(protocol_errors[0]),
                              protocol.lastErrCode, &status->last_error) == 0) ||
        (selector_from_driver(protocol_errors, sizeof(protocol_errors) / sizeof(protocol_errors[0]),
                              protocol.dlec, &status->data_last_error) == 0) ||
        (selector_from_driver(protocol_activities,
                              sizeof(protocol_activities) / sizeof(protocol_activities[0]),
                              protocol.act, &status->activity) == 0))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status->error_passive = protocol.errPassive;
    status->warning = protocol.warningStatus;
    status->bus_off = protocol.busOffStatus;
    status->received_esi = protocol.resi;
    status->received_brs = protocol.rbrs;
    status->received_fd = protocol.rfdf;
    status->protocol_exception = protocol.pxe;
    status->tdc_position = protocol.tdcv;
    status->tx_error_count = counters.transErrLogCnt;
    status->rx_error_count = counters.recErrCnt;
    status->rx_error_passive = counters.rpStatus;
    status->error_log_count = counters.canErrLogCnt;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current timestamp counter without resetting it.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_timestamp(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getTSCounterVal(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the timeout counter without reloading or changing its source.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_timeout_counter(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getTOCounterVal(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read clock-stop acknowledgement; do not claim that the external clock stopped.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_clock_stop_ack(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getClockStopAck(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reset the timestamp counter through one existing Driver action.
 * @param[in] id Logical controller.
 * @return OK or NOT_SUPPORTED.
 * @note No extra delay or readback; a running counter may advance before the next query.
 */
et_wrap_status_t et_can_wrap_reset_timestamp(et_can_id_t id)
{
    CAN_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_resetTSCounter(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Request or withdraw CAN clock stop without waiting for acknowledgement.
 * @param[in] id Logical controller.
 * @param[in] requested Boolean request, not an assumed final state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note The PC separately observes acknowledgement and restores INIT after withdrawal.
 */
et_wrap_status_t et_can_wrap_set_clock_stop(et_can_id_t id, uint8_t requested)
{
    CAN_Type *instance = find_instance(id);

    if (requested > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_addClockStopRequest(instance, requested);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or mask selected CAN interrupt sources through the own Driver.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @param[in] enabled Boolean source-enable request.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes IE only; IRQ Manager owns NVIC and vector binding.
 */
et_wrap_status_t et_can_wrap_set_irq_enabled(et_can_id_t id, uint32_t sources, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if ((enabled > 1u) || ((sources & ~ET_CAN_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_enableIntr(instance, translate_irq_events(sources, 1u), enabled);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Route selected CAN sources to controller interrupt line 0 or 1.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @param[in] line Stable controller-local line selector.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes ILS only and does not enable the source, controller line or NVIC route.
 */
et_wrap_status_t et_can_wrap_select_irq_line(et_can_id_t id, uint32_t sources,
                                             et_can_irq_line_t line)
{
    CAN_Type *instance = find_instance(id);

    if (((sources & ~ET_CAN_IRQ_ALL) != 0u) || (line >= ET_CAN_IRQ_LINE_COUNT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_selectIntrLine(instance, translate_irq_events(sources, 1u),
                       line == ET_CAN_IRQ_LINE0 ? CAN_INTR_LINE_NUM_0 : CAN_INTR_LINE_NUM_1);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or disable one controller-local interrupt output line.
 * @param[in] id Logical controller identity.
 * @param[in] line Stable controller-local line selector.
 * @param[in] enabled Boolean line-enable request.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes ILE only; physical NVIC ownership remains in IRQ Manager.
 */
et_wrap_status_t et_can_wrap_set_irq_line_enabled(et_can_id_t id, et_can_irq_line_t line,
                                                  uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if ((line >= ET_CAN_IRQ_LINE_COUNT) || (enabled > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_enableIntrLine(
        instance, line == ET_CAN_IRQ_LINE0 ? CAN_INTR_LINE_NUM_0 : CAN_INTR_LINE_NUM_1, enabled);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read current pending, source-enable, line-selection and line-enable facts.
 * @param[in] id Logical controller identity.
 * @param[out] snapshot Four non-destructive public interrupt observations.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note IR is read once; the Driver extension separately reads IE, ILS and ILE once each.
 */
et_wrap_status_t et_can_wrap_get_irq_snapshot(et_can_id_t id, et_can_irq_snapshot_t *snapshot)
{
    CAN_Type *instance = find_instance(id);
    uint32_t enabled;
    uint32_t line_selection;
    uint32_t line_enabled;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    snapshot->raw_status = translate_irq_events(CAN_getIntrStatus(instance), 0u);
    CAN_testGetInterruptConfig(instance, &enabled, &line_selection, &line_enabled);
    snapshot->enabled_sources = translate_irq_events(enabled, 0u);
    snapshot->line1_sources = translate_irq_events(line_selection, 0u);
    snapshot->enabled_lines = line_enabled & CAN_INTR_LINE_EN_MASK;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear exactly the selected CAN pending sources.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Level conditions may assert again until the owning FIFO or protocol condition is removed.
 */
et_wrap_status_t et_can_wrap_clear_irq(et_can_id_t id, uint32_t sources)
{
    CAN_Type *instance = find_instance(id);

    if ((sources & ~ET_CAN_IRQ_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_clearIntrStatus(instance, translate_irq_events(sources, 1u));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one controller-local line to its private physical IRQ route.
 * @param[in] id Logical controller identity.
 * @param[in] line Stable controller-local line selector.
 * @param[in] events Nonzero public events owned by this route.
 * @param[out] route Route consumed only by Service-to-IRQ-Manager binding.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No source, ILE or NVIC state is changed and no physical IRQ is exposed to PC.
 */
et_wrap_status_t et_can_wrap_get_irq_route(et_can_id_t id, et_can_irq_line_t line, uint32_t events,
                                           et_irq_route_t *route)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    if ((route == NULL) || (line >= ET_CAN_IRQ_LINE_COUNT) || (events == 0u) ||
        ((events & ~ET_CAN_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    route->irq_line = mapping->irq_lines[line];
    route->reserved = 0u;
    route->route_events = events;

    return ET_WRAP_STATUS_OK;
}
