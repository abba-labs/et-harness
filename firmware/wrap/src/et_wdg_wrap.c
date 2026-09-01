/**
 * @file et_wdg_wrap.c
 * @brief Implement the stable WDG Wrap contract through the selected WDG Driver.
 */

#include "et_wdg_wrap.h"

#include <stddef.h>
#include <string.h>

#include "et6x_wdg.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_wdg_id_t wdg_id;
    WDG_Type *driver_instance;
    et_irq_line_t irq_line;
    uint32_t features;
    uint32_t maximum_reload_count;
    uint32_t maximum_window_count;
} et_wdg_wrap_mapping_t;

static const et_wdg_wrap_mapping_t wdg_mappings[] = ET_CHIP_WDG_MAP_TABLE;

/**
 * @brief Resolve one stable watchdog instance through the chip mapping table.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note This helper reads compile-time facts only and does not touch hardware.
 * @return Matching mapping or NULL when unsupported.
 */
static const et_wdg_wrap_mapping_t *find_mapping(et_wdg_id_t wdg_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(wdg_mappings) / sizeof(wdg_mappings[0])); ++index)
    {
        if (wdg_mappings[index].wdg_id == wdg_id)
        {
            return &wdg_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Validate one versioned public watchdog configuration.
 * @param[in] mapping Selected chip mapping.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] config Public watchdog configuration.
 * @note Validation completes before any hardware mutation.
 * @return Stable Wrap validation status.
 */
static et_wrap_status_t validate_config(const et_wdg_wrap_mapping_t *mapping, et_wdg_id_t wdg_id,
                                        const et_wdg_wrap_config_t *config)
{
    size_t index;

    if ((mapping == NULL) || (config == NULL) ||
        (config->struct_size < ET_WDG_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_WDG_WRAP_API_VERSION) || (config->wdg_id != wdg_id) ||
        (config->mode > ET_WDG_WRAP_MODE_INDEPENDENT) ||
        (config->work_mode > ET_WDG_WRAP_WORK_SAME_ROUND_IRQ_RESET) ||
        (config->reset_enable > 1u) || (config->halt_pause_enable > 1u) ||
        (config->reload_count == 0u) || (config->reload_count > mapping->maximum_reload_count) ||
        (config->window_low_count > config->window_high_count) ||
        (config->window_high_count > config->reload_count) ||
        (config->window_high_count > mapping->maximum_window_count))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < ET_WDG_WRAP_CONFIG_RESERVED_WORDS; ++index)
    {
        if (config->reserved[index] != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return normalized runtime watchdog capability facts.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] capabilities Destination capability snapshot.
 * @note This reads compile-time chip facts only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_capabilities_get(et_wdg_id_t wdg_id,
                                              et_wdg_wrap_capabilities_t *capabilities)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    capabilities->features = mapping->features;
    capabilities->maximum_reload_count = mapping->maximum_reload_count;
    capabilities->maximum_window_count = mapping->maximum_window_count;
    capabilities->mode_mask =
        (uint8_t)((1u << ET_WDG_WRAP_MODE_WINDOW) | (1u << ET_WDG_WRAP_MODE_INDEPENDENT));
    capabilities->work_mode_mask = (uint8_t)((1u << ET_WDG_WRAP_WORK_ROUND1_IRQ_ROUND2_RESET) |
                                             (1u << ET_WDG_WRAP_WORK_SAME_ROUND_IRQ_RESET));
    capabilities->irq_sources = ET_WDG_WRAP_IRQ_ALL;
    capabilities->instance_count = (uint8_t)(sizeof(wdg_mappings) / sizeof(wdg_mappings[0]));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unlock protected watchdog configuration registers.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note This changes only the selected watchdog lock state.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_unlock(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_unlock(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Lock protected watchdog configuration registers.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note This changes only the selected watchdog lock state.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_lock(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_lock(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply one complete chip-neutral watchdog configuration.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] config Versioned public configuration.
 * @note The caller owns lock/unlock and enable/disable sequencing.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_configure(et_wdg_id_t wdg_id, const et_wdg_wrap_config_t *config)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);
    et_wrap_status_t status = validate_config(mapping, wdg_id, config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    WDG_setWatchdogReloadValue(mapping->driver_instance, config->reload_count);
    WDG_setWatchdogWindowValue(mapping->driver_instance, config->window_low_count,
                               config->window_high_count);

    if (config->mode == ET_WDG_WRAP_MODE_WINDOW)
    {
        WDG_enableWindowedWatchdog(mapping->driver_instance);
    }
    else
    {
        WDG_disableWindowedWatchdog(mapping->driver_instance);
    }

    WDG_setWatchdogWorkMode(mapping->driver_instance, (WDG_workMode)config->work_mode);
    WDG_setWatchdogMode(mapping->driver_instance,
                        (config->reset_enable != 0u) ? WD_MODE_INTERRUPT_RESET : WD_MODE_INTERRUPT);

    if (config->halt_pause_enable != 0u)
    {
        WDG_enableWatchdogInHalt(mapping->driver_instance);
    }
    else
    {
        WDG_disableWatchdogInHalt(mapping->driver_instance);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read one complete watchdog configuration through the Test Driver Extension.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] config Destination public configuration.
 * @note This query does not change watchdog state.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_config_get(et_wdg_id_t wdg_id, et_wdg_wrap_config_t *config)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);
    WDG_TestConfigSnapshot snapshot;

    if ((mapping == NULL) || (config == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (WDG_testGetConfiguration(mapping->driver_instance, &snapshot) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_WDG_WRAP_API_VERSION;
    config->wdg_id = wdg_id;
    config->mode =
        (snapshot.window_mode != 0u) ? ET_WDG_WRAP_MODE_WINDOW : ET_WDG_WRAP_MODE_INDEPENDENT;
    config->work_mode = snapshot.work_mode;
    config->reset_enable = snapshot.reset_enable;
    config->halt_pause_enable = snapshot.halt_pause_enable;
    config->reload_count = snapshot.reload;
    config->window_low_count = snapshot.window_low;
    config->window_high_count = snapshot.window_high;

    return ET_WRAP_STATUS_OK;
#else
    (void)wdg_id;
    (void)config;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Enable the selected watchdog counter.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note This starts or resumes the watchdog hardware counter.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_enable(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_enableWatchdog(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable the selected watchdog counter.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note This prevents new natural watchdog events.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_disable(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_disableWatchdog(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Issue one watchdog feed request.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note The hardware counter observation remains a separate query.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_feed(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_serviceWatchdog(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read enable and current-counter hardware facts.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] status Destination status snapshot.
 * @note This query does not clear watchdog events.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_status_get(et_wdg_id_t wdg_id, et_wdg_wrap_status_t *status)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (status == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status->enabled = WDG_isWatchdogEnabled(mapping->driver_instance) ? 1u : 0u;
    (void)memset(status->reserved, 0, sizeof(status->reserved));
    status->counter = WDG_getWatchdogCounterValue(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reset only the selected watchdog module through its own Driver.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @note The selected Driver owns its peripheral reset sequence.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_module_reset(et_wdg_id_t wdg_id)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (WDG_testResetModule(mapping->driver_instance) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve a logical watchdog to its physical IRQ route.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] route Destination IRQ route.
 * @note This lookup does not configure NVIC.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_get_irq_route(et_wdg_id_t wdg_id, et_irq_route_t *route)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = mapping->irq_line;
    route->reserved = 0u;
    route->route_events = ET_WDG_WRAP_IRQ_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable the watchdog IRQ source.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note NVIC binding remains owned by the Service IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_enable(et_wdg_id_t wdg_id, uint32_t sources)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_enableInterrupt(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable the watchdog IRQ source.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note Existing raw state is preserved until explicitly cleared.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_disable(et_wdg_id_t wdg_id, uint32_t sources)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_disableInterrupt(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask effective watchdog IRQ delivery.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note Raw state remains observable while masked.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_mask(et_wdg_id_t wdg_id, uint32_t sources)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_maskInterrupt(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask effective watchdog IRQ delivery.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note Source enable state is unchanged.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_unmask(et_wdg_id_t wdg_id, uint32_t sources)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_unmaskInterrupt(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force the watchdog IRQ source through the Test Driver Extension.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note This validates the IRQ control path, not natural timeout generation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_force(et_wdg_id_t wdg_id, uint32_t sources)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return (WDG_testForceInterrupt(mapping->driver_instance) == DRV_OK) ? ET_WRAP_STATUS_OK
                                                                        : ET_WRAP_STATUS_IO_ERROR;
#else
    (void)wdg_id;
    (void)sources;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Clear the watchdog IRQ source.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] sources Must equal the published timeout source.
 * @note This writes the selected watchdog clear pulse only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_clear(et_wdg_id_t wdg_id, uint32_t sources)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (sources != ET_WDG_WRAP_IRQ_TIMEOUT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    WDG_clearInterruptStatus(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read raw and effective watchdog IRQ states.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] snapshot Destination hardware IRQ snapshot.
 * @note Reading does not clear either state.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_irq_snapshot_get(et_wdg_id_t wdg_id,
                                              et_wdg_wrap_irq_snapshot_t *snapshot)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    snapshot->raw =
        (WDG_getRawInterruptStatus(mapping->driver_instance) == SET) ? ET_WDG_WRAP_IRQ_TIMEOUT : 0u;
    snapshot->status =
        (WDG_getInterruptStatus(mapping->driver_instance) == SET) ? ET_WDG_WRAP_IRQ_TIMEOUT : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read persistent watchdog reset and interrupt records.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[out] snapshot Destination persistent-record snapshot.
 * @note Reading does not clear either record.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_record_get(et_wdg_id_t wdg_id, et_wdg_wrap_record_snapshot_t *snapshot)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    snapshot->reset = WDG_getWatchdogResetStatus(mapping->driver_instance) ? 1u : 0u;
    snapshot->interrupt = WDG_getWatchdogInterruptRecordStatus(mapping->driver_instance) ? 1u : 0u;
    snapshot->reserved[0] = 0u;
    snapshot->reserved[1] = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected persistent watchdog records.
 * @param[in] wdg_id Stable logical watchdog identifier.
 * @param[in] records Nonempty published record mask.
 * @note Reset and interrupt records use distinct Driver clear actions.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_wdg_wrap_record_clear(et_wdg_id_t wdg_id, uint32_t records)
{
    const et_wdg_wrap_mapping_t *mapping = find_mapping(wdg_id);

    if ((mapping == NULL) || (records == 0u) || ((records & ~ET_WDG_WRAP_RECORD_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((records & ET_WDG_WRAP_RECORD_RESET) != 0u)
    {
        WDG_clearWatchdogResetStatus(mapping->driver_instance);
    }

    if ((records & ET_WDG_WRAP_RECORD_INTERRUPT) != 0u)
    {
        WDG_clearWatchdogInterruptRecordStatus(mapping->driver_instance);
    }

    return ET_WRAP_STATUS_OK;
}
