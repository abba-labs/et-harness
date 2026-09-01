/**
 * @file et_crc_wrap.c
 * @brief Implement the stable CRC Wrap contract through the selected CRC Driver.
 *
 * Register access is intentionally absent from this layer. Missing validation
 * features are supplied only by the isolated CRC Test Driver Extension.
 */
#include "et_crc_wrap.h"

#include <stddef.h>

#include "et6x_crc.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_crc_id_t crc_id;
    et_irq_line_t irq_line;
    uint8_t fifo_threshold_max;
} et_crc_wrap_mapping_t;

static const et_crc_wrap_mapping_t crc_mappings[] = ET_CHIP_CRC_MAP_TABLE;

/**
 * @brief Resolve one stable logical CRC instance through the selected chip mapping table.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 *
 * @note This helper reads compile-time Chip Config facts only. It does not access CRC hardware or
 *       mutate Wrap state.
 *
 * @return Pointer to the matching chip mapping, or NULL when crc_id is unsupported.
 */
static const et_crc_wrap_mapping_t *find_crc_mapping(et_crc_id_t crc_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(crc_mappings) / sizeof(crc_mappings[0])); ++index)
    {
        if (crc_mappings[index].crc_id == crc_id)
        {
            return &crc_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Validate that one stable logical CRC instance exists on the selected chip.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 *
 * @note This is a mapping-table query only and does not access CRC hardware.
 *
 * @return Nonzero when crc_id is mapped, otherwise zero.
 */
static uint8_t crc_id_is_valid(et_crc_id_t crc_id)
{
    return (uint8_t)(find_crc_mapping(crc_id) != NULL);
}

/**
 * @brief Validate one chip-neutral CRC width/mode identifier.
 *
 * @param[in] mode Stable CRC8, CRC16 or CRC32 mode value.
 *
 * @note Validation is intentionally independent of the selected SDK enum values and has no hardware
 *       side effect.
 *
 * @return Nonzero when mode is a published CRC Wrap mode, otherwise zero.
 */
static uint8_t mode_is_valid(uint8_t mode)
{
    return (uint8_t)((mode == ET_CRC_WRAP_MODE_CRC8) || (mode == ET_CRC_WRAP_MODE_CRC16) ||
                     (mode == ET_CRC_WRAP_MODE_CRC32));
}

/**
 * @brief Return the legal polynomial/seed/check-value bit mask for one CRC width.
 *
 * @param[in] mode Stable CRC width/mode identifier.
 *
 * @note Callers validate mode before using this mask. The helper only derives a public-width fact and
 *       does not read CRC hardware.
 *
 * @return UINT8_MAX for CRC8, UINT16_MAX for CRC16, otherwise UINT32_MAX.
 */
static uint32_t mode_value_mask(uint8_t mode)
{
    if (mode == ET_CRC_WRAP_MODE_CRC8)
    {
        return UINT8_MAX;
    }

    if (mode == ET_CRC_WRAP_MODE_CRC16)
    {
        return UINT16_MAX;
    }

    return UINT32_MAX;
}

/**
 * @brief Normalize one selected CRC Driver status into the stable Wrap status namespace.
 *
 * @param[in] status CRC Driver status returned by the selected chip SDK.
 *
 * @note This helper performs status translation only and does not access CRC hardware.
 *
 * @return Stable Wrap status corresponding to the Driver result.
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

    if (status == DRV_TIMEOUT)
    {
        return ET_WRAP_STATUS_TIMEOUT;
    }

    return ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Validate one versioned chip-neutral CRC configuration before Driver translation.
 *
 * @param[in] crc_id Stable logical CRC instance that must own the configuration.
 * @param[in] config Versioned CRC Wrap configuration supplied by the caller.
 *
 * @note Validation rejects unsupported Boolean/options, per-chip FIFO limits and values wider than
 *       the selected CRC mode. It never truncates polynomial/seed values and does not configure hardware.
 *
 * @return ET_WRAP_STATUS_OK when the complete configuration is valid.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when the envelope or any field is invalid/unsupported.
 */
static et_wrap_status_t validate_config(et_crc_id_t crc_id, const et_crc_wrap_config_t *config)
{
    const et_crc_wrap_mapping_t *mapping = find_crc_mapping(crc_id);
    uint32_t value_mask;

    if ((config == NULL) || (mapping == NULL) ||
        (config->struct_size < ET_CRC_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_CRC_WRAP_API_VERSION) || (config->crc_id != crc_id) ||
        (mode_is_valid(config->mode) == 0u) || (config->xor_out > ET_CRC_WRAP_XOR_ONES) ||
        (config->ref_in > 1u) || (config->ref_out > 1u) || (config->auto_length_reload > 1u) ||
        (config->byte_swap > 1u) || (config->result_check > 1u) ||
        (config->fifo_threshold > mapping->fifo_threshold_max) ||
        ((config->mode == ET_CRC_WRAP_MODE_CRC8) && (config->byte_swap != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    value_mask = mode_value_mask(config->mode);

    if (((config->polynomial & ~value_mask) != 0u) || ((config->initial_value & ~value_mask) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable the mapped CRC hardware module.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 *
 * @note This function changes CRC module-enable hardware through the selected Driver. It does not
 *       configure polynomial, input data or interrupt routing.
 *
 * @return ET_WRAP_STATUS_OK when the mapped module is enabled.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when crc_id is unsupported.
 */
et_wrap_status_t et_crc_wrap_enable(et_crc_id_t crc_id)
{
    if (crc_id_is_valid(crc_id) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_enableModule();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return the selected-chip maximum CRC FIFO threshold without exposing an SDK constant.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] maximum_threshold Maximum supported FIFO threshold for the mapped instance.
 *
 * @note This function reads compile-time Chip Config facts only and does not access CRC hardware.
 *
 * @return ET_WRAP_STATUS_OK when the mapping/output pointer is valid.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when crc_id or maximum_threshold is invalid.
 */
et_wrap_status_t et_crc_wrap_get_fifo_threshold_max(et_crc_id_t crc_id, uint8_t *maximum_threshold)
{
    const et_crc_wrap_mapping_t *mapping = find_crc_mapping(crc_id);

    if ((mapping == NULL) || (maximum_threshold == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *maximum_threshold = mapping->fifo_threshold_max;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable the mapped CRC hardware module.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 *
 * @note This function changes CRC module-enable hardware only. Existing configuration/state is not
 *       reinterpreted or converted into a test result.
 *
 * @return ET_WRAP_STATUS_OK when the mapped module is disabled.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when crc_id is unsupported.
 */
et_wrap_status_t et_crc_wrap_disable(et_crc_id_t crc_id)
{
    if (crc_id_is_valid(crc_id) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_disableModule();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate and apply one complete chip-neutral CRC configuration through the Driver.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] config Versioned chip-neutral CRC configuration.
 *
 * @note All public fields are validated before any Driver type/value is constructed. A successful
 *       call changes CRC configuration hardware but does not enable/disable the module automatically.
 *
 * @return ET_WRAP_STATUS_OK when the configuration is valid and applied.
 * @return Stable validation error when the public configuration is invalid.
 */
et_wrap_status_t et_crc_wrap_configure(et_crc_id_t crc_id, const et_crc_wrap_config_t *config)
{
    CRC_ConfigParams driver_config;
    et_wrap_status_t status;

    status = validate_config(crc_id, config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Translate only after the complete common configuration is validated. */
    driver_config.mode = (config->mode == ET_CRC_WRAP_MODE_CRC32)   ? CRC_MODE_CRC32
                         : (config->mode == ET_CRC_WRAP_MODE_CRC16) ? CRC_MODE_CRC16
                                                                    : CRC_MODE_CRC8;
    driver_config.refIn = config->ref_in ? ENABLE : DISABLE;
    driver_config.refOut = config->ref_out ? ENABLE : DISABLE;
    driver_config.xorOut = config->xor_out ? ALL_ONE : ALL_ZERO;
    driver_config.autoLengthReloadEn = config->auto_length_reload ? ENABLE : DISABLE;
    driver_config.byteswapEn = config->byte_swap ? ENABLE : DISABLE;
    driver_config.resultCheckEn = config->result_check ? ENABLE : DISABLE;
    driver_config.polynomial = config->polynomial;
    driver_config.fifoThreshold = config->fifo_threshold;
    driver_config.initialValue = config->initial_value;
    CRC_config(&driver_config);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Calculate one bounded CRC value using the width-specific selected Driver API.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] mode CRC8/CRC16/CRC32 input-width mode.
 * @param[in] source_address Source memory address containing input bytes.
 * @param[in] length_bytes Number of input bytes included in the calculation.
 * @param[in] timeout_budget Nonzero bounded Driver polling budget.
 * @param[out] result Canonical 32-bit result; narrower CRC values are zero-extended.
 *
 * @note Address overflow/alignment and maximum length are validated before hardware execution. This
 *       function performs the CRC hardware calculation only and does not decide expected-vs-actual PASS/FAIL.
 *
 * @return Stable Wrap status for validation or selected Driver calculation outcome.
 */
et_wrap_status_t et_crc_wrap_calculate(et_crc_id_t crc_id, uint8_t mode, uintptr_t source_address,
                                       uint32_t length_bytes, uint32_t timeout_budget,
                                       uint32_t *result)
{
    DRV_Status driver_status;
    uint16_t result16;
    uint8_t result8;

    /* Phase 1: Validate logical instance, mode, source range, width alignment and bounded execution. */
    if ((crc_id_is_valid(crc_id) == 0u) || (mode_is_valid(mode) == 0u) ||
        (source_address == (uintptr_t)0u) || (result == NULL) || (length_bytes == 0u) ||
        (length_bytes > ET_CRC_WRAP_MAX_CALCULATE_BYTES) || (timeout_budget == 0u) ||
        ((source_address + (uintptr_t)length_bytes) < source_address) ||
        ((mode == ET_CRC_WRAP_MODE_CRC16) && ((source_address & 1u) != 0u)) ||
        ((mode == ET_CRC_WRAP_MODE_CRC32) && ((source_address & (sizeof(uint32_t) - 1u)) != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Dispatch to the exact-width Driver path without changing public result representation. */
    if (mode == ET_CRC_WRAP_MODE_CRC32)
    {
        driver_status =
            CRC_calculate32((uint32_t *)source_address, length_bytes, result, timeout_budget);
    }
    else if (mode == ET_CRC_WRAP_MODE_CRC16)
    {
        driver_status =
            CRC_calculate16((uint16_t *)source_address, length_bytes, &result16, timeout_budget);

        if (driver_status == DRV_OK)
        {
            *result = result16;
        }
    }
    else
    {
        driver_status =
            CRC_calculate8((uint8_t *)source_address, length_bytes, &result8, timeout_budget);

        if (driver_status == DRV_OK)
        {
            *result = result8;
        }
    }

    /* Phase 3: Normalize the Driver outcome after any successful narrow-result zero extension. */
    return status_from_driver(driver_status);
}

/**
 * @brief Read the current CRC hardware result into the canonical 32-bit representation.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] result Current CRC hardware result.
 *
 * @note This is a hardware read only; it does not clear CRC state or interpret correctness.
 *
 * @return ET_WRAP_STATUS_OK when the result is read.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when crc_id/result is invalid.
 */
et_wrap_status_t et_crc_wrap_result_get(et_crc_id_t crc_id, uint32_t *result)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *result = CRC_getResult();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Convert public input length in bytes to the selected Driver LENGTH transaction count.
 *
 * @param[in] mode Stable CRC input-width mode.
 * @param[in] length_bytes Public input length in bytes.
 *
 * @note CRC32/CRC16 Driver LENGTH counts width-sized transactions; a trailing partial word is counted
 *       as individual byte input. This helper only performs arithmetic and does not program hardware.
 *
 * @return Driver input-transaction count corresponding to length_bytes and mode.
 */
static uint32_t length_bytes_to_input_count(uint8_t mode, uint32_t length_bytes)
{
    uint32_t width_bytes;

    if (mode == ET_CRC_WRAP_MODE_CRC32)
    {
        width_bytes = sizeof(uint32_t);
    }
    else if (mode == ET_CRC_WRAP_MODE_CRC16)
    {
        width_bytes = sizeof(uint16_t);
    }
    else
    {
        width_bytes = 1u;
    }

    return (length_bytes / width_bytes) + (length_bytes % width_bytes);
}

/**
 * @brief Validate one nonempty normalized CRC interrupt-source mask.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Stable CRC Wrap interrupt-source bits.
 *
 * @note Validation accepts only published Wrap bits and performs no Driver/hardware action.
 *
 * @return ET_WRAP_STATUS_OK when instance and source mask are valid.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT otherwise.
 */
static et_wrap_status_t validate_irq_sources(et_crc_id_t crc_id, uint32_t source_bits)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (source_bits == 0u) ||
        ((source_bits & ~ET_CRC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate stable CRC Wrap interrupt-source bits to selected Driver mask bits.
 *
 * @param[in] source_bits Stable CRC Wrap interrupt-source mask.
 *
 * @note The mapping is pure value translation. Callers validate source_bits before using it to
 *       change CRC interrupt hardware.
 *
 * @return Selected Driver interrupt mask corresponding to source_bits.
 */
static uint32_t irq_sources_to_driver(uint32_t source_bits)
{
    uint32_t driver_bits = 0u;

    if ((source_bits & ET_CRC_WRAP_IRQ_BUS_ERROR) != 0u)
    {
        driver_bits |= CRC_INT_BUS_ERR;
    }

    if ((source_bits & ET_CRC_WRAP_IRQ_LENGTH_ERROR) != 0u)
    {
        driver_bits |= CRC_INT_LENGTH_ERR;
    }

    if ((source_bits & ET_CRC_WRAP_IRQ_CHECK_ERROR) != 0u)
    {
        driver_bits |= CRC_INT_CHECK_ERR;
    }

    return driver_bits;
}

/**
 * @brief Translate selected Driver raw/status bits back to stable CRC Wrap sources.
 *
 * @param[in] driver_bits CRC Driver interrupt bits read from hardware.
 *
 * @note This helper normalizes observations only and does not clear or mask interrupt hardware.
 *
 * @return Stable CRC Wrap interrupt-source mask corresponding to driver_bits.
 */
static uint32_t irq_sources_from_driver(uint32_t driver_bits)
{
    uint32_t source_bits = 0u;

    if ((driver_bits & CRC_INT_BUS_ERR) != 0u)
    {
        source_bits |= ET_CRC_WRAP_IRQ_BUS_ERROR;
    }

    if ((driver_bits & CRC_INT_LENGTH_ERR) != 0u)
    {
        source_bits |= ET_CRC_WRAP_IRQ_LENGTH_ERROR;
    }

    if ((driver_bits & CRC_INT_CHECK_ERR) != 0u)
    {
        source_bits |= ET_CRC_WRAP_IRQ_CHECK_ERROR;
    }

    return source_bits;
}

/**
 * @brief Program CRC hardware input length from a public byte length and input-width mode.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] mode Stable CRC input-width mode.
 * @param[in] length_bytes Public input length in bytes.
 *
 * @note This function changes the CRC Driver LENGTH register using the Driver transaction-count
 *       convention; it does not feed input data or start a software test flow.
 *
 * @return ET_WRAP_STATUS_OK when length is programmed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/mode is invalid.
 */
et_wrap_status_t et_crc_wrap_data_length_set(et_crc_id_t crc_id, uint8_t mode,
                                             uint32_t length_bytes)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (mode_is_valid(mode) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_setDataLength(length_bytes_to_input_count(mode, length_bytes));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current CRC Driver input-transaction count.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] remaining_input_count Remaining Driver input-transaction count.
 *
 * @note This is a hardware read only; the returned count follows the selected Driver LENGTH
 *       convention rather than being converted back to bytes.
 *
 * @return ET_WRAP_STATUS_OK when the count is read.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/output is invalid.
 */
et_wrap_status_t et_crc_wrap_data_length_get(et_crc_id_t crc_id, uint32_t *remaining_input_count)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (remaining_input_count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *remaining_input_count = CRC_getDataLength();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program the CRC hardware check value after width validation.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] mode Stable CRC width/mode identifier.
 * @param[in] value Check value constrained to the selected CRC width.
 *
 * @note This function changes CRC check/compare hardware configuration only. Values that would be
 *       truncated by the selected width are rejected.
 *
 * @return ET_WRAP_STATUS_OK when the check value is programmed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/mode/value is invalid.
 */
et_wrap_status_t et_crc_wrap_check_value_set(et_crc_id_t crc_id, uint8_t mode, uint32_t value)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (mode_is_valid(mode) == 0u) ||
        ((value & ~mode_value_mask(mode)) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_setCheckValue(value);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read normalized CRC FIFO overflow status.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] overflow Canonical 0/1 FIFO overflow observation.
 *
 * @note This function reads CRC FIFO status hardware and does not clear overflow or other interrupt state.
 *
 * @return ET_WRAP_STATUS_OK when the status is read.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/output is invalid.
 */
et_wrap_status_t et_crc_wrap_fifo_status_get(et_crc_id_t crc_id, uint8_t *overflow)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (overflow == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *overflow = CRC_isFIFOOverflow() ? 1u : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return the managed physical IRQ route for one logical CRC instance.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] route Stable route containing physical line and normalized CRC event mask.
 *
 * @note This function exposes Chip Config route facts only and does not register/enable the IRQ line.
 *
 * @return ET_WRAP_STATUS_OK when the mapping is available.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/output is invalid.
 */
et_wrap_status_t et_crc_wrap_get_irq_route(et_crc_id_t crc_id, et_irq_route_t *route)
{
    const et_crc_wrap_mapping_t *mapping = find_crc_mapping(crc_id);

    if ((mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = mapping->irq_line;
    route->reserved = 0u;
    route->route_events = ET_CRC_WRAP_IRQ_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected normalized CRC interrupt sources in CRC hardware.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function changes CRC peripheral interrupt-source enable state only. NVIC routing remains
 *       owned by IRQ Manager/IRQ Wrap.
 *
 * @return ET_WRAP_STATUS_OK when the sources are enabled, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_enable(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_enableInterrupt(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected normalized CRC interrupt sources in CRC hardware.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function changes CRC peripheral interrupt-source enable state only and does not unbind
 *       the CPU IRQ route.
 *
 * @return ET_WRAP_STATUS_OK when the sources are disabled, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_disable(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_disableInterrupt(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask selected normalized CRC interrupt sources.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function changes CRC peripheral mask hardware only and does not disable the source or
 *       CPU IRQ line.
 *
 * @return ET_WRAP_STATUS_OK when the sources are masked, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_mask(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_setInterruptMask(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask selected normalized CRC interrupt sources.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function changes CRC peripheral mask hardware only. Source enable and NVIC routing are
 *       separate responsibilities.
 *
 * @return ET_WRAP_STATUS_OK when the sources are unmasked, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_unmask(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_clearInterruptMask(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force selected normalized CRC interrupt sources for verification.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function deliberately changes CRC force/indication hardware for validation. It does not
 *       synthesize host-side PASS/FAIL or bypass the owning Service's evidence capture.
 *
 * @return ET_WRAP_STATUS_OK when the sources are forced, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_force(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_forceInterrupt(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected normalized CRC interrupt sources.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_bits Nonempty stable CRC interrupt-source mask.
 *
 * @note This function acknowledges CRC peripheral interrupt status only. Source enable/mask and CPU
 *       IRQ route ownership remain unchanged.
 *
 * @return ET_WRAP_STATUS_OK when the sources are cleared, otherwise INVALID_ARGUMENT.
 */
et_wrap_status_t et_crc_wrap_irq_clear(et_crc_id_t crc_id, uint32_t source_bits)
{
    if (validate_irq_sources(crc_id, source_bits) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRC_clearInterrupt(irq_sources_to_driver(source_bits));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Snapshot normalized raw and enabled/latched CRC interrupt facts without clearing them.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[out] snapshot Normalized raw and status interrupt masks.
 *
 * @note Both hardware observations are read before returning and neither source is acknowledged or
 *       modified by this function.
 *
 * @return ET_WRAP_STATUS_OK when the snapshot is captured.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when instance/output is invalid.
 */
et_wrap_status_t et_crc_wrap_irq_snapshot_get(et_crc_id_t crc_id,
                                              et_crc_wrap_irq_snapshot_t *snapshot)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Read both facts before returning; this function does not clear sources. */
    snapshot->raw = irq_sources_from_driver(CRC_getInterruptStatusRawAll());
    snapshot->status = irq_sources_from_driver(CRC_getInterruptStatusAll());

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Write one CRC input value using an explicitly requested bus access width.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] access_width Stable 8/16/32-bit access-width selector.
 * @param[in] value Value to write; narrow accesses reject values that would be truncated.
 *
 * @note This validation-only operation is available only with isolated Test Driver Extensions. The
 *       requested bus access width is preserved so hardware behavior can be observed accurately.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_crc_wrap_test_input_write(et_crc_id_t crc_id, uint8_t access_width,
                                              uint32_t value)
{
    if (crc_id_is_valid(crc_id) == 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((access_width == ET_CRC_WRAP_ACCESS_8) && ((value & ~((uint32_t)UINT8_MAX)) == 0u))
    {
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

        return status_from_driver(CRC_testWriteInput8((uint8_t)value));
#else

        return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
    }

    if ((access_width == ET_CRC_WRAP_ACCESS_16) && ((value & ~((uint32_t)UINT16_MAX)) == 0u))
    {
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

        return status_from_driver(CRC_testWriteInput16((uint16_t)value));
#else

        return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
    }

    if (access_width == ET_CRC_WRAP_ACCESS_32)
    {
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

        return status_from_driver(CRC_testWriteInput32(value));
#else

        return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
    }

    return ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Execute one bounded 32-bit CRC input burst through the isolated Test Driver Extension.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] values Array of 32-bit input items.
 * @param[in] count Number of input items, bounded by ET_CRC_WRAP_MAX_BURST_ITEMS.
 * @param[in] checkpoint_count Item count at which an intermediate result is observed.
 * @param[out] checkpoint_result CRC result observed at the requested checkpoint.
 * @param[out] final_result CRC result after the complete burst.
 * @param[out] overflow Raw FIFO overflow observation returned by the Test Driver.
 *
 * @note The target-local burst/timing remains inside the CRC Test Driver; Wrap only validates stable
 *       arguments and forwards returned hardware observations unchanged.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_crc_wrap_test_input_burst_32(et_crc_id_t crc_id, const uint32_t *values,
                                                 uint32_t count, uint32_t checkpoint_count,
                                                 uint32_t *checkpoint_result,
                                                 uint32_t *final_result, uint32_t *overflow)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (values == NULL) || (count == 0u) ||
        (count > ET_CRC_WRAP_MAX_BURST_ITEMS) || (checkpoint_count > count) ||
        (checkpoint_result == NULL) || (final_result == NULL) || (overflow == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return status_from_driver(CRC_testWriteInput32Burst(values, count, checkpoint_count,
                                                        checkpoint_result, final_result, overflow));
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Calculate a bounded timed CRC32 hardware operation through the Test Driver Extension.
 *
 * @param[in] crc_id Stable logical CRC instance identifier.
 * @param[in] source_address Aligned source address containing the input bytes.
 * @param[in] length_bytes Nonzero bounded input length in bytes.
 * @param[in] timeout_budget Nonzero bounded Driver polling budget.
 * @param[out] result CRC32 hardware result.
 * @param[out] elapsed_cycles Target-local cycle observation from first input write through result read.
 *
 * @note Timing boundaries are implemented in the selected CRC Test Driver so Wrap does not invent a
 *       software timing surrogate. The function returns observation facts only, never a performance verdict.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_crc_wrap_test_calculate_timed(et_crc_id_t crc_id, uintptr_t source_address,
                                                  uint32_t length_bytes, uint32_t timeout_budget,
                                                  uint32_t *result, uint32_t *elapsed_cycles)
{
    if ((crc_id_is_valid(crc_id) == 0u) || (source_address == (uintptr_t)0u) ||
        ((source_address & (sizeof(uint32_t) - 1u)) != 0u) || (length_bytes == 0u) ||
        (length_bytes > ET_CRC_WRAP_MAX_CALCULATE_BYTES) || (timeout_budget == 0u) ||
        (result == NULL) || (elapsed_cycles == NULL) ||
        ((source_address + (uintptr_t)length_bytes) < source_address))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return status_from_driver(CRC_testCalculate32Timed(
        (const uint32_t *)source_address, length_bytes, timeout_budget, result, elapsed_cycles));
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}
