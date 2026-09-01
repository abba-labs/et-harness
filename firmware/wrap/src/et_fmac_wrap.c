/**
 * @file et_fmac_wrap.c
 * @brief Implement the stable FMAC Wrap contract through the selected FMAC Driver.
 *
 * This layer never accesses FMAC registers. Missing validation primitives are
 * supplied by the isolated FMAC Test Driver Extension.
 */

#include "et_fmac_wrap.h"

#include <string.h>

#include "et6x_fmac.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_fmac_id_t fmac_id;
    IRQn_Type irq;
    uint32_t feature_flags;
    uint16_t max_transfer_items;
    uint8_t logical_address_bits;
    uint8_t max_feedforward_taps;
    uint8_t max_feedback_taps;
    uint8_t watermark_mask;
    uint8_t output_mode_mask;
    uint8_t shift_mask_width;
    uint16_t irq_source_mask;
    uint8_t fir_first_valid_output_index;
    uint8_t iir_first_valid_output_index;
    uint32_t clear_timeout_budget;
} et_fmac_wrap_mapping_t;

static const et_fmac_wrap_mapping_t fmac_mappings[] = ET_CHIP_FMAC_MAP_TABLE;

/**
 * @brief Resolve one logical FMAC instance through Chip Config.
 * @param[in] fmac_id Stable logical FMAC instance identifier.
 * @note This helper reads immutable mapping facts only and performs no hardware access.
 * @return Matching immutable mapping, or NULL when unsupported.
 */
static const et_fmac_wrap_mapping_t *find_mapping(et_fmac_id_t fmac_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(fmac_mappings) / sizeof(fmac_mappings[0])); ++index)
    {
        if (fmac_mappings[index].fmac_id == fmac_id)
        {
            return &fmac_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Translate one FMAC Driver result to the stable Wrap status namespace.
 * @param[in] status Selected-chip Driver status.
 * @note Driver-specific status values never escape this Wrap translation boundary.
 * @return Equivalent stable Wrap status.
 */
static et_wrap_status_t status_from_driver(DRV_Status status)
{
    if (status == DRV_OK)
    {
        return ET_WRAP_STATUS_OK;
    }

    if (status == DRV_PARAM_ERR)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (status == DRV_BUSY)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (status == DRV_TIMEOUT)
    {
        return ET_WRAP_STATUS_TIMEOUT;
    }

    return ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Translate an element-count watermark to the selected Driver encoding.
 * @param[in] watermark Stable public watermark value.
 * @param[out] driver_watermark Selected Driver encoding.
 * @note Translation performs no hardware access.
 * @return ET_WRAP_STATUS_OK when supported, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */
static et_wrap_status_t translate_watermark(uint8_t watermark, FMAC_BuffFIFOTrhd *driver_watermark)
{
    if (driver_watermark == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (watermark)
    {
        case ET_FMAC_WRAP_WATERMARK_1:
        {
            *driver_watermark = FMAC_TRHD_1;
            break;
        }

        case ET_FMAC_WRAP_WATERMARK_2:
        {
            *driver_watermark = FMAC_TRHD_2;
            break;
        }

        case ET_FMAC_WRAP_WATERMARK_4:
        {
            *driver_watermark = FMAC_TRHD_4;
            break;
        }

        case ET_FMAC_WRAP_WATERMARK_8:
        {
            *driver_watermark = FMAC_TRHD_8;
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate one Driver watermark encoding to its public element count.
 * @param[in] driver_watermark Selected Driver encoding.
 * @note Unknown encodings map to zero and are never inferred.
 * @return Public watermark value, or zero for an invalid encoding.
 */
static uint8_t watermark_from_driver(uint8_t driver_watermark)
{
    static const uint8_t values[] = {
        ET_FMAC_WRAP_WATERMARK_1,
        ET_FMAC_WRAP_WATERMARK_2,
        ET_FMAC_WRAP_WATERMARK_4,
        ET_FMAC_WRAP_WATERMARK_8,
    };

    if (driver_watermark >= (sizeof(values) / sizeof(values[0])))
    {
        return 0u;
    }

    return values[driver_watermark];
}

/**
 * @brief Validate a complete chip-neutral FMAC configuration.
 * @param[in] mapping Selected-chip immutable limits.
 * @param[in] config Public configuration envelope.
 * @note Validation rejects unsupported public values before Driver translation.
 * @return ET_WRAP_STATUS_OK when valid, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */
static et_wrap_status_t validate_config(const et_fmac_wrap_mapping_t *mapping,
                                        const et_fmac_wrap_config_t *config)
{
    FMAC_BuffFIFOTrhd driver_watermark;
    uint16_t logical_limit;

    if ((mapping == NULL) || (config == NULL) ||
        (config->struct_size < ET_FMAC_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_FMAC_WRAP_API_VERSION) ||
        (config->fmac_id != mapping->fmac_id) || (config->x1_size == 0u) ||
        (config->x2_size == 0u) || (config->y_size == 0u) ||
        (config->final_policy > ET_FMAC_WRAP_FINAL_WRAP) ||
        (config->output_mode > ET_FMAC_WRAP_OUTPUT_SAT16) || (config->internal_clip > 1u) ||
        (config->float_input > 1u) || (config->float_output > 1u) ||
        (config->output_shift > ET_FMAC_WRAP_SHIFT_RIGHT7) || (config->reserved[0] != 0u) ||
        (config->reserved[1] != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((translate_watermark(config->x1_full_watermark, &driver_watermark) != ET_WRAP_STATUS_OK) ||
        (translate_watermark(config->y_empty_watermark, &driver_watermark) != ET_WRAP_STATUS_OK))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    logical_limit = (uint16_t)(1u << mapping->logical_address_bits);

    if (((uint16_t)config->x1_start + config->x1_size > logical_limit) ||
        ((uint16_t)config->x2_start + config->x2_size > logical_limit) ||
        ((uint16_t)config->y_start + config->y_size > logical_limit))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return stable runtime capabilities for one logical FMAC instance.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] capabilities Versioned public capability envelope.
 * @note Values originate from selected-chip mapping facts, not register probing.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_get_capabilities(et_fmac_id_t fmac_id,
                                               et_fmac_wrap_capabilities_t *capabilities)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(capabilities, 0, sizeof(*capabilities));
    capabilities->struct_size = (uint16_t)sizeof(*capabilities);
    capabilities->api_version = ET_FMAC_WRAP_API_VERSION;
    capabilities->feature_flags = mapping->feature_flags;
    capabilities->max_transfer_items = mapping->max_transfer_items;
    capabilities->logical_address_bits = mapping->logical_address_bits;
    capabilities->max_feedforward_taps = mapping->max_feedforward_taps;
    capabilities->max_feedback_taps = mapping->max_feedback_taps;
    capabilities->watermark_mask = mapping->watermark_mask;
    capabilities->output_mode_mask = mapping->output_mode_mask;
    capabilities->shift_mask_width = mapping->shift_mask_width;
    capabilities->irq_source_mask = mapping->irq_source_mask;
    capabilities->fir_first_valid_output_index = mapping->fir_first_valid_output_index;
    capabilities->iir_first_valid_output_index = mapping->iir_first_valid_output_index;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate and apply one complete FMAC quasi-static configuration.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] config Versioned chip-neutral configuration.
 * @note All hardware changes are delegated to the selected FMAC Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_configure(et_fmac_id_t fmac_id, const et_fmac_wrap_config_t *config)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);
    FMAC_ConfigParams driver_config;
    FMAC_BuffFIFOTrhd x1_watermark;
    FMAC_BuffFIFOTrhd y_watermark;
    et_wrap_status_t status;

    status = validate_config(mapping, config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (FMAC_isFuncBusy())
    {
        return ET_WRAP_STATUS_BUSY;
    }

    (void)translate_watermark(config->x1_full_watermark, &x1_watermark);
    (void)translate_watermark(config->y_empty_watermark, &y_watermark);
    (void)memset(&driver_config, 0, sizeof(driver_config));
    driver_config.X1_BuffBase = config->x1_start;
    driver_config.X1_BuffSize = config->x1_size;
    driver_config.X1_BuffFIFOTrhd = x1_watermark;
    driver_config.X2_BuffBase = config->x2_start;
    driver_config.X2_BuffSize = config->x2_size;
    driver_config.Y_BuffBase = config->y_start;
    driver_config.Y_BuffSize = config->y_size;
    driver_config.Y_BuffFIFOTrhd = y_watermark;
    driver_config.accumulatorWrapEn =
        (config->final_policy == ET_FMAC_WRAP_FINAL_WRAP) ? ENABLE : DISABLE;
    driver_config.outputDataMode = (FMAC_OutputDataMode)config->output_mode;
    driver_config.DMADataReadEn = DISABLE;
    driver_config.DMADataWriteEn = DISABLE;
    driver_config.clipEn = (config->internal_clip != 0u) ? ENABLE : DISABLE;
    driver_config.outputDataOffset = config->output_offset;
    driver_config.outputDataShift = (FMAC_OutputDataShift)config->output_shift;
    driver_config.floatDataReadEn = (config->float_input != 0u) ? ENABLE : DISABLE;
    driver_config.floatDataWriteEn = (config->float_output != 0u) ? ENABLE : DISABLE;
    FMAC_config(&driver_config);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read all public FMAC configuration fields through the Driver extension.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] snapshot Public configuration snapshot.
 * @note The Test Driver Extension owns register-level observation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_config_snapshot_get(et_fmac_id_t fmac_id,
                                                  et_fmac_wrap_config_snapshot_t *snapshot)
{
    FMAC_TestConfigSnapshot driver_snapshot;
    et_wrap_status_t status;

    if ((find_mapping(fmac_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = status_from_driver(FMAC_testGetConfigSnapshot(&driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    (void)memset(snapshot, 0, sizeof(*snapshot));
    snapshot->struct_size = (uint16_t)sizeof(*snapshot);
    snapshot->api_version = ET_FMAC_WRAP_API_VERSION;
    snapshot->fmac_id = fmac_id;
    snapshot->x1_start = driver_snapshot.x1Base;
    snapshot->x1_size = driver_snapshot.x1Size;
    snapshot->x1_full_watermark = watermark_from_driver(driver_snapshot.x1FullWatermark);
    snapshot->x2_start = driver_snapshot.x2Base;
    snapshot->x2_size = driver_snapshot.x2Size;
    snapshot->y_start = driver_snapshot.yBase;
    snapshot->y_size = driver_snapshot.ySize;
    snapshot->y_empty_watermark = watermark_from_driver(driver_snapshot.yEmptyWatermark);
    snapshot->final_policy = driver_snapshot.accumulatorWrapEnable;
    snapshot->output_mode = driver_snapshot.outputDataMode;
    snapshot->internal_clip = driver_snapshot.clipEnable;
    snapshot->float_input = driver_snapshot.floatInputEnable;
    snapshot->float_output = driver_snapshot.floatOutputEnable;
    snapshot->output_shift = driver_snapshot.outputDataShift;
    snapshot->output_offset = driver_snapshot.outputDataOffset;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Start one FMAC initialization or filtering function.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] function Public FMAC function selector.
 * @param[in] feedforward_taps Feedforward tap count.
 * @param[in] feedback_taps Feedback tap count.
 * @note Function execution is delegated to the selected Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_start(et_fmac_id_t fmac_id, uint8_t function,
                                    uint8_t feedforward_taps, uint8_t feedback_taps)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (function < ET_FMAC_WRAP_FUNCTION_LOAD_X1) ||
        (function > ET_FMAC_WRAP_FUNCTION_IIR) || (feedforward_taps == 0u) ||
        (feedforward_taps > mapping->max_feedforward_taps) ||
        (feedback_taps > mapping->max_feedback_taps) ||
        ((function != ET_FMAC_WRAP_FUNCTION_IIR) && (feedback_taps != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(FMAC_testStartFunction(function, feedforward_taps, feedback_taps));
}

/**
 * @brief Start one FMAC test transaction without rejecting raw P/Q values.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] function Public FMAC function selector.
 * @param[in] feedforward_taps Raw P parameter used as hardware stimulus.
 * @param[in] feedback_taps Raw Q parameter used as hardware stimulus.
 * @note This interface exists only to observe natural hardware parameter-error sources.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_start_unchecked(et_fmac_id_t fmac_id, uint8_t function,
                                              uint8_t feedforward_taps, uint8_t feedback_taps)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || ((mapping->feature_flags & ET_FMAC_WRAP_CAP_TEST_EXTENSIONS) == 0u) ||
        (function < ET_FMAC_WRAP_FUNCTION_LOAD_X1) || (function > ET_FMAC_WRAP_FUNCTION_IIR))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(FMAC_testStartFunction(function, feedforward_taps, feedback_taps));
}

/**
 * @brief Stop the active FMAC function.
 * @param[in] fmac_id Stable logical instance identifier.
 * @note This operation changes only the selected FMAC instance.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_stop(et_fmac_id_t fmac_id)
{
    if (find_mapping(fmac_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(FMAC_testStopFunction());
}

/**
 * @brief Clear dynamic FMAC state without inventing a configuration baseline.
 * @param[in] fmac_id Stable logical instance identifier.
 * @note Quasi-static configuration remains owned by the caller.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_clear(et_fmac_id_t fmac_id)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(FMAC_testClearDynamicState(mapping->clear_timeout_budget));
}

/**
 * @brief Load an exact bounded fixed-point or Float32 sequence into X1.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] data Caller-owned input items.
 * @param[in] count Number of items.
 * @param[in] use_float Nonzero selects Float32 items; zero selects fixed-point items.
 * @param[in] timeout_budget Driver polling budget.
 * @note No data-format conversion is performed by Wrap.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_x1_preload(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                         uint8_t use_float, uint32_t timeout_budget)
{
    if ((find_mapping(fmac_id) == NULL) || (data == NULL) || (count == 0u) || (use_float > 1u) ||
        (timeout_budget == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (use_float != 0u)
    {
        return status_from_driver(FMAC_testLoadX1Float((const float *)data, count, timeout_budget));
    }

    return status_from_driver(FMAC_testLoadX1((const int16_t *)data, count, timeout_budget));
}

/**
 * @brief Load exact feedforward and optional feedback coefficient segments into X2.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] feedforward Caller-owned feedforward coefficients.
 * @param[in] feedforward_count Feedforward item count.
 * @param[in] feedback Optional caller-owned feedback coefficients.
 * @param[in] feedback_count Feedback item count.
 * @param[in] timeout_budget Driver polling budget.
 * @note Coefficients are passed unchanged to the selected Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_coefficients_load(et_fmac_id_t fmac_id, const int16_t *feedforward,
                                                uint8_t feedforward_count, const int16_t *feedback,
                                                uint8_t feedback_count, uint32_t timeout_budget)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (feedforward == NULL) || (feedforward_count == 0u) ||
        (feedforward_count > mapping->max_feedforward_taps) ||
        (feedback_count > mapping->max_feedback_taps) ||
        ((feedback_count != 0u) && (feedback == NULL)) || (timeout_budget == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(
        FMAC_testLoadX2(feedforward, feedforward_count, feedback, feedback_count, timeout_budget));
}

/**
 * @brief Load an exact bounded fixed-point or Float32 sequence into Y.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] data Caller-owned output-history items.
 * @param[in] count Number of items.
 * @param[in] use_float Nonzero selects Float32 items; zero selects fixed-point items.
 * @param[in] timeout_budget Driver polling budget.
 * @note No data-format conversion is performed by Wrap.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_y_preload(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                        uint8_t use_float, uint32_t timeout_budget)
{
    if ((find_mapping(fmac_id) == NULL) || (data == NULL) || (count == 0u) || (use_float > 1u) ||
        (timeout_budget == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (use_float != 0u)
    {
        return status_from_driver(FMAC_testLoadYFloat((const float *)data, count, timeout_budget));
    }

    return status_from_driver(FMAC_testLoadY((const int16_t *)data, count, timeout_budget));
}

/**
 * @brief Write as many requested stream items as the current X1 state can accept.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] data Caller-owned stream items.
 * @param[in] count Maximum requested item count.
 * @param[in] use_float Nonzero selects Float32 items; zero selects fixed-point items.
 * @param[out] accepted_count Number of items accepted by hardware.
 * @note A successful partial transfer is reported through accepted_count.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_stream_write(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                           uint8_t use_float, uint32_t *accepted_count)
{
    uint32_t index;

    if ((find_mapping(fmac_id) == NULL) || (data == NULL) || (count == 0u) || (use_float > 1u) ||
        (accepted_count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *accepted_count = 0u;

    for (index = 0u; index < count; ++index)
    {
        if ((FMAC_getStatus() & FMAC_STS_X1_BUFF_IS_FULL_FLAG_MASK) != 0u)
        {
            break;
        }

        if (use_float != 0u)
        {
            FMAC_setFIFODataFloat(((const float *)data)[index]);
        }
        else
        {
            FMAC_setFIFOData(((const int16_t *)data)[index]);
        }

        ++(*accepted_count);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read as many requested stream items as the current Y state exposes.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] data Caller-owned destination storage.
 * @param[in] count Maximum requested item count.
 * @param[in] use_float Nonzero selects Float32 items; zero selects fixed-point items.
 * @param[out] read_count Number of items returned by hardware.
 * @note A successful partial transfer is reported through read_count.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_stream_read(et_fmac_id_t fmac_id, void *data, uint8_t count,
                                          uint8_t use_float, uint32_t *read_count)
{
    uint32_t index;

    if ((find_mapping(fmac_id) == NULL) || (data == NULL) || (count == 0u) || (use_float > 1u) ||
        (read_count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *read_count = 0u;

    for (index = 0u; index < count; ++index)
    {
        if ((FMAC_getStatus() & FMAC_STS_Y_BUFF_IS_EMPTY_FLAG_MASK) != 0u)
        {
            break;
        }

        if (use_float != 0u)
        {
            ((float *)data)[index] = FMAC_getFIFODataFloat();
        }
        else
        {
            ((int16_t *)data)[index] = FMAC_getFIFOData();
        }

        ++(*read_count);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Perform one unchecked raw FIFO write for natural Overflow stimulus.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] raw_value Raw item bits written without capacity pre-check.
 * @note Register access remains isolated in the selected Test Driver Extension.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_data_write_one_unchecked(et_fmac_id_t fmac_id, uint32_t raw_value)
{
    if (find_mapping(fmac_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_testWriteFIFOUnchecked(raw_value);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Perform one unchecked raw FIFO read for natural Underflow stimulus.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] raw_value Raw item bits returned without availability pre-check.
 * @note Register access remains isolated in the selected Test Driver Extension.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_data_read_one_unchecked(et_fmac_id_t fmac_id, uint32_t *raw_value)
{
    if ((find_mapping(fmac_id) == NULL) || (raw_value == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *raw_value = FMAC_testReadFIFOUnchecked();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read stable FMAC status fields without clearing sticky reports.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] snapshot Public hardware status snapshot.
 * @note Observation has no intentional clear side effect.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_status_get(et_fmac_id_t fmac_id,
                                         et_fmac_wrap_status_snapshot_t *snapshot)
{
    uint32_t raw;

    if ((find_mapping(fmac_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    raw = FMAC_testGetStatusRaw();
    (void)memset(snapshot, 0, sizeof(*snapshot));
    snapshot->active = (uint8_t)FMAC_isFuncBusy();
    snapshot->x1_spare_count =
        (uint8_t)((raw & FMAC_SR_X1_SPARE_NUM_RPT_Msk) >> FMAC_SR_X1_SPARE_NUM_RPT_Pos);
    snapshot->y_unread_count =
        (uint8_t)((raw & FMAC_SR_Y_UNRD_NUM_RPT_Msk) >> FMAC_SR_Y_UNRD_NUM_RPT_Pos);
    snapshot->x1_full = (uint8_t)((raw & FMAC_SR_X1_FULL_RPT_Msk) != 0u);
    snapshot->y_empty = (uint8_t)((raw & FMAC_SR_Y_EMPTY_RPT_Msk) != 0u);
    snapshot->x1_overflow = (uint8_t)((raw & FMAC_SR_X1_OVFL_RPT_Msk) != 0u);
    snapshot->y_underflow = (uint8_t)((raw & FMAC_SR_Y_UNFL_RPT_Msk) != 0u);
    snapshot->accumulator_saturation = (uint8_t)((raw & FMAC_SR_SAT_RPT_Msk) != 0u);
    snapshot->negative_after_offset = (uint8_t)((raw & FMAC_SR_ADD_OFT_IS_NEG_RPT_Msk) != 0u);
    snapshot->float_to_q15_overflow = (uint8_t)((raw & FMAC_SR_FLOAT2FIXED_OVF_RPT_Msk) != 0u);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve the selected FMAC instance to its physical IRQ route.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] route Common IRQ Manager route.
 * @note The route comes from selected-chip mapping facts only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_get_irq_route(et_fmac_id_t fmac_id, et_irq_route_t *route)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = (et_irq_line_t)mapping->irq;
    route->reserved = 0u;
    route->route_events = mapping->irq_source_mask;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one nonempty public FMAC interrupt-source mask.
 * @param[in] mapping Selected-chip immutable source mask.
 * @param[in] source_bits Public source bits requested by the caller.
 * @note Validation performs no hardware access.
 * @return Nonzero when every requested bit is supported, otherwise zero.
 */
static uint8_t irq_bits_are_valid(const et_fmac_wrap_mapping_t *mapping, uint32_t source_bits)
{
    return (uint8_t)((mapping != NULL) && (source_bits != 0u) &&
                     ((source_bits & ~mapping->irq_source_mask) == 0u));
}

/**
 * @brief Enable selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note IRQ routing remains owned by Service and IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_enable(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_enableInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note IRQ routing remains owned by Service and IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_disable(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_disableInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note This changes only the FMAC source mask through Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_mask(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_setInterruptMask(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note This changes only the FMAC source mask through Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_unmask(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_clearInterruptMask(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note Force is a validation stimulus delegated to Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_force(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_forceInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected FMAC IRQ sources.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] source_bits Nonempty public source mask.
 * @note Only explicitly requested sources are acknowledged.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_clear(et_fmac_id_t fmac_id, uint32_t source_bits)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if (irq_bits_are_valid(mapping, source_bits) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    FMAC_clearInterruptStatus(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read raw and effective FMAC IRQ state.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[out] snapshot Raw and effective public interrupt facts.
 * @note Observation does not intentionally clear interrupt state.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_irq_snapshot_get(et_fmac_id_t fmac_id,
                                               et_fmac_wrap_irq_snapshot_t *snapshot)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    snapshot->raw = FMAC_getInterruptStatusRaw() & mapping->irq_source_mask;
    snapshot->status = FMAC_getInterruptStatus() & mapping->irq_source_mask;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Set FMAC input/output DMA request gates while idle.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] request_bits Public input/output request-gate mask; zero disables both.
 * @note This does not configure DMA controller channels or another IP.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_dma_request_set(et_fmac_id_t fmac_id, uint32_t request_bits)
{
    if ((find_mapping(fmac_id) == NULL) || ((request_bits & ~ET_FMAC_WRAP_DMA_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(FMAC_testSetDMARequests(
        ((request_bits & ET_FMAC_WRAP_DMA_INPUT) != 0u) ? ENABLE : DISABLE,
        ((request_bits & ET_FMAC_WRAP_DMA_OUTPUT) != 0u) ? ENABLE : DISABLE));
}

/**
 * @brief Process one bounded FMAC stream and return target-local cycle evidence.
 * @param[in] fmac_id Stable logical instance identifier.
 * @param[in] function Public FIR or IIR function selector.
 * @param[in] feedforward_taps Public P parameter.
 * @param[in] feedback_taps Public Q parameter.
 * @param[in] source Caller-owned Q15 or Float32 input array.
 * @param[out] destination Caller-owned Q15 or Float32 output array.
 * @param[in] count Number of input and output items.
 * @param[in] use_float Nonzero selects Float32; zero selects Q15.
 * @param[in] timeout_budget Maximum target-side no-progress polls.
 * @param[out] accepted_count Number of input items accepted.
 * @param[out] read_count Number of output items read.
 * @param[out] elapsed_cycles Target-local DWT cycle delta.
 * @note The selected FMAC Driver extension owns the indivisible timing window.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_fmac_wrap_process_timed(et_fmac_id_t fmac_id, uint8_t function,
                                            uint8_t feedforward_taps, uint8_t feedback_taps,
                                            const void *source, void *destination, uint16_t count,
                                            uint8_t use_float, uint32_t timeout_budget,
                                            uint32_t *accepted_count, uint32_t *read_count,
                                            uint32_t *elapsed_cycles)
{
    const et_fmac_wrap_mapping_t *mapping = find_mapping(fmac_id);

    if ((mapping == NULL) || (source == NULL) || (destination == NULL) || (count == 0u) ||
        (use_float > 1u) || (accepted_count == NULL) || (read_count == NULL) ||
        (elapsed_cycles == NULL) ||
        ((mapping->feature_flags & ET_FMAC_WRAP_CAP_TIMED_PROCESS) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(
        FMAC_testProcessTimed(function, feedforward_taps, feedback_taps, source, destination, count,
                              (use_float != 0u) ? ENABLE : DISABLE, timeout_budget, accepted_count,
                              read_count, elapsed_cycles));
}
