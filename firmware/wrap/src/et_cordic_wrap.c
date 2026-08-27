/**
 * @file et_cordic_wrap.c
 * @brief Implement the stable CORDIC Wrap through the selected CORDIC Driver.
 */

#include "et_cordic_wrap.h"

#include <stddef.h>

#include "et6x_cordic.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_cordic_id_t cordic_id;
    et_irq_line_t irq_line;
    uint32_t features;
    uint16_t function_mask;
    uint8_t maximum_scale;
    uint8_t maximum_precision_cycles;
    uint8_t driver_dma_work_mode;
} et_cordic_wrap_mapping_t;

static const et_cordic_wrap_mapping_t cordic_mappings[] = ET_CHIP_CORDIC_MAP_TABLE;

/**
 * @brief Resolve a stable CORDIC ID through the selected chip table.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @note This mapping lookup has no hardware side effect.
 * @return Matching mapping, or NULL when the instance is unsupported.
 */
static const et_cordic_wrap_mapping_t *find_mapping(et_cordic_id_t cordic_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(cordic_mappings) / sizeof(cordic_mappings[0])); ++index)
    {
        if (cordic_mappings[index].cordic_id == cordic_id)
        {
            return &cordic_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Validate one stable mathematical function identifier.
 * @param[in] function Stable CORDIC function value.
 * @note This validation has no hardware side effect.
 * @return Nonzero when the function is valid, otherwise zero.
 */
static uint8_t function_is_valid(uint8_t function)
{
    return (uint8_t)(function <= ET_CORDIC_WRAP_FUNCTION_TAN);
}

/**
 * @brief Validate one stable result-count value.
 * @param[in] count Requested logical result count.
 * @note This validation has no hardware side effect.
 * @return Nonzero when count is one or two, otherwise zero.
 */
static uint8_t result_count_is_valid(uint8_t count)
{
    return (uint8_t)((count == ET_CORDIC_WRAP_RESULT_ONE) || (count == ET_CORDIC_WRAP_RESULT_TWO));
}

/**
 * @brief Translate a stable width into the selected Driver enum.
 * @param[in] width Stable 16-bit or 32-bit width.
 * @note The caller validates width before translation.
 * @return Selected Driver data-format value.
 */
static CORDIC_DataFormat width_to_driver(uint8_t width)
{
    return (width == ET_CORDIC_WRAP_WIDTH_16) ? CORDIC_DATA_FORMAT_BIT16 : CORDIC_DATA_FORMAT_BIT32;
}

/**
 * @brief Translate a stable result count into the selected Driver enum.
 * @param[in] count Stable one-result or two-result value.
 * @note The caller validates count before translation.
 * @return Selected Driver result-count value.
 */
static CORDIC_ArgResNum result_count_to_driver(uint8_t count)
{
    return (count == ET_CORDIC_WRAP_RESULT_ONE) ? CORDIC_ARG_RES_NUM1 : CORDIC_ARG_RES_NUM2;
}

/**
 * @brief Translate stable status bits into selected Driver masks.
 * @param[in] status Stable CORDIC status bits.
 * @note Unknown bits are rejected by the public caller before translation.
 * @return Selected Driver status mask.
 */
static uint32_t status_to_driver(uint32_t status)
{
    uint32_t driver_status = 0u;

    if ((status & ET_CORDIC_WRAP_STATUS_ARG_OVERFLOW) != 0u)
    {
        driver_status |= CORDIC_STS_ARG_PARAM_OVERFLOW;
    }

    if ((status & ET_CORDIC_WRAP_STATUS_COMPLETE) != 0u)
    {
        driver_status |= CORDIC_STS_CALCULATE_COMPLETE;
    }

    if ((status & ET_CORDIC_WRAP_STATUS_PM_ARG2_ERROR) != 0u)
    {
        driver_status |= CORDIC_STS_PM_IN_PARAM2_ERROR;
    }

    return driver_status;
}

/**
 * @brief Translate selected Driver status masks into stable status bits.
 * @param[in] driver_status Raw selected Driver status mask.
 * @note Unknown Driver bits are intentionally ignored.
 * @return Stable CORDIC status bits.
 */
static uint32_t status_from_driver(uint32_t driver_status)
{
    uint32_t status = 0u;

    if ((driver_status & CORDIC_STS_ARG_PARAM_OVERFLOW) != 0u)
    {
        status |= ET_CORDIC_WRAP_STATUS_ARG_OVERFLOW;
    }

    if ((driver_status & CORDIC_STS_CALCULATE_COMPLETE) != 0u)
    {
        status |= ET_CORDIC_WRAP_STATUS_COMPLETE;
    }

    if ((driver_status & CORDIC_STS_PM_IN_PARAM2_ERROR) != 0u)
    {
        status |= ET_CORDIC_WRAP_STATUS_PM_ARG2_ERROR;
    }

    return status;
}

/**
 * @brief Translate stable IRQ bits into selected Driver masks.
 * @param[in] sources Stable CORDIC IRQ source bits.
 * @note Unknown bits are rejected by the public caller before translation.
 * @return Selected Driver IRQ mask.
 */
static uint32_t irq_to_driver(uint32_t sources)
{
    uint32_t driver_sources = 0u;

    if ((sources & ET_CORDIC_WRAP_IRQ_ARG_OVERFLOW) != 0u)
    {
        driver_sources |= CORDIC_INT_FLAG_ARG_PARAM_OVERFLOW;
    }

    if ((sources & ET_CORDIC_WRAP_IRQ_CALCULATION_COMPLETE) != 0u)
    {
        driver_sources |= CORDIC_INT_FLAG_CALCULATE_COMPLETE;
    }

    if ((sources & ET_CORDIC_WRAP_IRQ_PM_ARG2_ERROR) != 0u)
    {
        driver_sources |= CORDIC_INT_FLAG_PM_IN_PARAM2_ERROR;
    }

    return driver_sources;
}

/**
 * @brief Translate selected Driver IRQ masks into stable IRQ bits.
 * @param[in] driver_sources Raw selected Driver IRQ mask.
 * @note Unknown Driver bits are intentionally ignored.
 * @return Stable CORDIC IRQ source bits.
 */
static uint32_t irq_from_driver(uint32_t driver_sources)
{
    uint32_t sources = 0u;

    if ((driver_sources & CORDIC_INT_FLAG_ARG_PARAM_OVERFLOW) != 0u)
    {
        sources |= ET_CORDIC_WRAP_IRQ_ARG_OVERFLOW;
    }

    if ((driver_sources & CORDIC_INT_FLAG_CALCULATE_COMPLETE) != 0u)
    {
        sources |= ET_CORDIC_WRAP_IRQ_CALCULATION_COMPLETE;
    }

    if ((driver_sources & CORDIC_INT_FLAG_PM_IN_PARAM2_ERROR) != 0u)
    {
        sources |= ET_CORDIC_WRAP_IRQ_PM_ARG2_ERROR;
    }

    return sources;
}

/**
 * @brief Validate one complete stable CORDIC configuration.
 * @param[in] mapping Selected chip mapping for the logical instance.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] config Versioned public configuration.
 * @note Validation completes before any hardware access.
 * @return ET_WRAP_STATUS_OK or ET_WRAP_STATUS_INVALID_ARGUMENT.
 */
static et_wrap_status_t validate_config(const et_cordic_wrap_mapping_t *mapping,
                                        et_cordic_id_t cordic_id,
                                        const et_cordic_wrap_config_t *config)
{
    size_t reserved_index;

    if ((mapping == NULL) || (config == NULL) ||
        (config->struct_size < ET_CORDIC_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_CORDIC_WRAP_API_VERSION) || (config->cordic_id != cordic_id) ||
        (config->numeric_mode > ET_CORDIC_WRAP_NUMERIC_FLOAT32) ||
        ((config->argument_width != ET_CORDIC_WRAP_WIDTH_16) &&
         (config->argument_width != ET_CORDIC_WRAP_WIDTH_32)) ||
        ((config->result_width != ET_CORDIC_WRAP_WIDTH_16) &&
         (config->result_width != ET_CORDIC_WRAP_WIDTH_32)) ||
        (config->input_range > ET_CORDIC_WRAP_RANGE_DIRECT_ANGLE) ||
        (config->scale > mapping->maximum_scale) || (config->precision_cycles == 0u) ||
        (config->precision_cycles > mapping->maximum_precision_cycles) ||
        (result_count_is_valid(config->sincos_result_count) == 0u) ||
        (result_count_is_valid(config->phase_modulus_result_count) == 0u) ||
        (result_count_is_valid(config->hsincos_result_count) == 0u) ||
        (config->work_mode > ET_CORDIC_WRAP_WORK_DMA) || (config->reserved8[0] != 0u) ||
        (config->reserved8[1] != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (reserved_index = 0u; reserved_index < ET_CORDIC_WRAP_CONFIG_RESERVED_WORDS;
         ++reserved_index)
    {
        if (config->reserved[reserved_index] != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return normalized runtime capability facts for one mapped instance.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] capabilities Destination capability snapshot.
 * @note This reads compile-time chip facts only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_capabilities_get(et_cordic_id_t cordic_id,
                                                 et_cordic_wrap_capabilities_t *capabilities)
{
    const et_cordic_wrap_mapping_t *mapping = find_mapping(cordic_id);
    size_t reserved_index;

    if ((mapping == NULL) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    capabilities->features = mapping->features;
    capabilities->function_mask = mapping->function_mask;
    capabilities->maximum_scale = mapping->maximum_scale;
    capabilities->maximum_precision_cycles = mapping->maximum_precision_cycles;
    capabilities->irq_sources = ET_CORDIC_WRAP_IRQ_ALL;

    for (reserved_index = 0u;
         reserved_index < (sizeof(capabilities->reserved) / sizeof(capabilities->reserved[0]));
         ++reserved_index)
    {
        capabilities->reserved[reserved_index] = 0u;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply one complete public CORDIC configuration.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] config Versioned public configuration.
 * @note This calls only the selected CORDIC Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_configure(et_cordic_id_t cordic_id,
                                          const et_cordic_wrap_config_t *config)
{
    const et_cordic_wrap_mapping_t *mapping = find_mapping(cordic_id);
    CORDIC_InitParams driver_config;
    et_wrap_status_t status = validate_config(mapping, cordic_id, config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    CORDIC_initStruct(&driver_config);
    driver_config.scale = (CORDIC_Scale)config->scale;
    driver_config.argDataFormat = width_to_driver(config->argument_width);
    driver_config.resDataFormat = width_to_driver(config->result_width);
    driver_config.numberRead_HSinCos = result_count_to_driver(config->hsincos_result_count);
    driver_config.numberRead_PM = result_count_to_driver(config->phase_modulus_result_count);
    driver_config.numberRead_SinCos = result_count_to_driver(config->sincos_result_count);
    driver_config.dataMode = (config->input_range == ET_CORDIC_WRAP_RANGE_NORMALIZED)
                                 ? CORDIC_DATA_INPUT_RANGE_NORMAL
                                 : CORDIC_DATA_INPUT_RANGE_2PI;
    driver_config.workMode = (config->work_mode == ET_CORDIC_WRAP_WORK_DMA)
                                 ? (CORDIC_WorkMode)mapping->driver_dma_work_mode
                                 : (CORDIC_WorkMode)config->work_mode;
    driver_config.precision = (uint8_t)(config->precision_cycles - 1u);
    driver_config.floatDataEn =
        (config->numeric_mode == ET_CORDIC_WRAP_NUMERIC_FLOAT32) ? ENABLE : DISABLE;
    CORDIC_init(&driver_config);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Submit one raw argument to a selected mathematical function.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] function Stable mathematical function identifier.
 * @param[in] raw_value Uninterpreted hardware input word.
 * @note Raw codec interpretation remains outside the Wrap.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_argument_submit(et_cordic_id_t cordic_id, uint8_t function,
                                                uint32_t raw_value)
{
    if ((find_mapping(cordic_id) == NULL) || (function_is_valid(function) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_setArg(raw_value, (CORDIC_MathFunc)function);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read both raw CORDIC result words.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] primary Destination for the primary raw result.
 * @param[out] secondary Destination for the secondary raw result.
 * @note This function does not interpret the result codec.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_result_get(et_cordic_id_t cordic_id, uint32_t *primary,
                                           uint32_t *secondary)
{
    if ((find_mapping(cordic_id) == NULL) || (primary == NULL) || (secondary == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *primary = CORDIC_getResult1();
    *secondary = CORDIC_getResult2();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read all stable CORDIC status sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] status Destination for stable status bits.
 * @note Reading does not clear W1C status.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_status_get(et_cordic_id_t cordic_id, uint32_t *status)
{
    if ((find_mapping(cordic_id) == NULL) || (status == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *status = status_from_driver(CORDIC_getStatus());

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected stable CORDIC W1C status sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] status Nonempty stable status mask.
 * @note Only CORDIC-owned W1C status is changed.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_status_clear(et_cordic_id_t cordic_id, uint32_t status)
{
    if ((find_mapping(cordic_id) == NULL) || (status == 0u) ||
        ((status & ~ET_CORDIC_WRAP_STATUS_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_clearStatus(status_to_driver(status));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current hardware argument-count state.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] count Destination for the raw argument count.
 * @note Reading does not submit or consume arguments.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_argument_count_get(et_cordic_id_t cordic_id, uint32_t *count)
{
    if ((find_mapping(cordic_id) == NULL) || (count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *count = CORDIC_getCurrentArgNum();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read stable float-to-fixed conversion status bits.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] status Destination for conversion status bits.
 * @note Reading does not clear conversion status.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_conversion_status_get(et_cordic_id_t cordic_id, uint32_t *status)
{
    if ((find_mapping(cordic_id) == NULL) || (status == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *status = CORDIC_getFloat2FixedStatus() & ET_CORDIC_WRAP_CONVERSION_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected float-to-fixed conversion status bits.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] status Nonempty stable conversion status mask.
 * @note Only CORDIC-owned conversion status is changed.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_conversion_status_clear(et_cordic_id_t cordic_id, uint32_t status)
{
    if ((find_mapping(cordic_id) == NULL) || (status == 0u) ||
        ((status & ~ET_CORDIC_WRAP_CONVERSION_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_clearFloat2FixedStatus(status);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve the selected logical instance to its physical IRQ route.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] route Destination stable IRQ route.
 * @note This mapping lookup does not configure NVIC.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_get_irq_route(et_cordic_id_t cordic_id, et_irq_route_t *route)
{
    const et_cordic_wrap_mapping_t *mapping = find_mapping(cordic_id);

    if ((mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = mapping->irq_line;
    route->reserved = 0u;
    route->route_events = ET_CORDIC_WRAP_IRQ_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note NVIC binding remains owned by the Service IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_enable(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_enableInterrupt(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note NVIC binding remains owned by the Service IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_disable(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_disableInterrupt(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note Raw source facts remain available after masking.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_mask(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_setInterruptMask(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note Enable state is not changed by this operation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_unmask(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_clearInterruptMask(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note This operation is intended for deterministic IRQ-path validation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_force(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_forceInterrupt(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected stable CORDIC IRQ sources.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] sources Nonempty stable IRQ source mask.
 * @note Other IRQ source bits are preserved.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_clear(et_cordic_id_t cordic_id, uint32_t sources)
{
    if ((find_mapping(cordic_id) == NULL) || (sources == 0u) ||
        ((sources & ~ET_CORDIC_WRAP_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CORDIC_clearInterruptStatus(irq_to_driver(sources));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read raw and effective stable IRQ states.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[out] snapshot Destination hardware IRQ snapshot.
 * @note This function does not report software delivery evidence.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_irq_snapshot_get(et_cordic_id_t cordic_id,
                                                 et_cordic_wrap_irq_snapshot_t *snapshot)
{
    if ((find_mapping(cordic_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    snapshot->raw = irq_from_driver(CORDIC_getInterruptStatusRaw());
    snapshot->status = irq_from_driver(CORDIC_getInterruptStatus());

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute one bounded zero-overhead raw transaction.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] function Stable mathematical function identifier.
 * @param[in] arguments One or two raw input words.
 * @param[in] argument_count Number of raw input words.
 * @param[out] primary Destination for primary raw result.
 * @param[out] secondary Destination for secondary raw result.
 * @note The selected Test Driver Extension owns the atomic hardware window.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_cordic_wrap_zero_overhead_execute(et_cordic_id_t cordic_id, uint8_t function,
                                                      const uint32_t *arguments,
                                                      uint8_t argument_count, uint32_t *primary,
                                                      uint32_t *secondary)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    if ((find_mapping(cordic_id) == NULL) || (function_is_valid(function) == 0u) ||
        (arguments == NULL) || (primary == NULL) || (secondary == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CORDIC_testExecuteZeroOverhead((CORDIC_MathFunc)function, arguments, argument_count,
                                       primary, secondary) != DRV_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
#else
    (void)cordic_id;
    (void)function;
    (void)arguments;
    (void)argument_count;
    (void)primary;
    (void)secondary;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Execute one bounded CORDIC transaction and return target-local cycles.
 * @param[in] cordic_id Stable logical CORDIC instance identifier.
 * @param[in] function Stable mathematical function identifier.
 * @param[in] arguments One or two raw input words.
 * @param[in] argument_count Number of raw input words.
 * @param[in] timeout Bounded result-ready polling budget.
 * @param[out] primary Destination for primary raw result.
 * @param[out] secondary Destination for secondary raw result.
 * @param[out] elapsed_cycles Destination for target-local cycle count.
 * @note Only the selected CORDIC Chip Driver Test Extension performs timing.
 * @return Stable Wrap status for the timed Driver operation.
 */
et_wrap_status_t et_cordic_wrap_execute_timed(et_cordic_id_t cordic_id, uint8_t function,
                                              const uint32_t *arguments, uint8_t argument_count,
                                              uint32_t timeout, uint32_t *primary,
                                              uint32_t *secondary, uint32_t *elapsed_cycles)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    if ((find_mapping(cordic_id) == NULL) || (function_is_valid(function) == 0u) ||
        (arguments == NULL) || (timeout == 0u) || (primary == NULL) || (secondary == NULL) ||
        (elapsed_cycles == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CORDIC_testExecuteTimed((CORDIC_MathFunc)function, arguments, argument_count, timeout,
                                primary, secondary, elapsed_cycles) != DRV_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
#else
    (void)cordic_id;
    (void)function;
    (void)arguments;
    (void)argument_count;
    (void)timeout;
    (void)primary;
    (void)secondary;
    (void)elapsed_cycles;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}
