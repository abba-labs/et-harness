/**
 * @file et_stimer_wrap.c
 * @brief Stable STIMER operations implemented only through the STIMER Chip Driver.
 */

#include "et_stimer_wrap.h"

#include <stddef.h>

#include "et6x_stimer.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_stimer_id_t logical_id;
    STIMER_Type *driver_instance;
    et_irq_line_t irq_line;
    uint32_t features;
    uint8_t emergency_index;
    uint8_t emergency_source_id;
    uint8_t emergency_trigger_group;
    uint8_t reserved8;
    uint32_t emergency_source_mask;
} et_stimer_wrap_mapping_t;

static const et_stimer_wrap_mapping_t stimer_mappings[] = ET_CHIP_STIMER_MAP_TABLE;

#define ET_STIMER_WRAP_INSTANCE_COUNT                                                              \
    ((uint8_t)(sizeof(stimer_mappings) / sizeof(stimer_mappings[0])))

/**
 * @brief Resolve one stable logical STIMER identifier.
 * @param[in] stimer_id Stable logical identifier.
 * @note This lookup has no hardware side effect.
 * @return Immutable mapping or NULL when unsupported.
 */
static const et_stimer_wrap_mapping_t *find_mapping(et_stimer_id_t stimer_id)
{
    size_t index;

    for (index = 0u; index < (size_t)ET_STIMER_WRAP_INSTANCE_COUNT; ++index)
    {
        if (stimer_mappings[index].logical_id == stimer_id)
        {
            return &stimer_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Validate one complete public STIMER configuration.
 * @param[in] config Public configuration.
 * @note This helper validates stable syntax only.
 * @return Nonzero when every stable field is valid.
 */
static int config_is_valid(const et_stimer_wrap_config_t *config)
{
    if ((config == NULL) || (config->struct_size < ET_STIMER_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_STIMER_WRAP_API_VERSION) ||
        (config->mode > ET_STIMER_WRAP_MODE_FREE_RUN) ||
        (config->load_mode > ET_STIMER_WRAP_LOAD_SHADOW) || (config->period_ticks == 0u) ||
        (config->prescaler_divider == 0u))
    {
        return 0;
    }

    return 1;
}

/**
 * @brief Validate one nonempty published IRQ source mask.
 * @param[in] sources Stable source mask.
 * @note Unknown and empty masks fail closed.
 * @return Nonzero when valid.
 */
static int irq_sources_are_valid(uint32_t sources)
{
    return (sources != 0u) && ((sources & ~ET_STIMER_WRAP_IRQ_ALL) == 0u);
}

/**
 * @brief Return stable STIMER capabilities for one logical instance.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] capabilities Destination capability snapshot.
 * @note Capability values describe the selected Driver mapping only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_capabilities_get(et_stimer_id_t stimer_id,
                                                 et_stimer_wrap_capabilities_t *capabilities)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    capabilities->features = mapping->features;
    capabilities->maximum_period_ticks = ET_STIMER_WRAP_MAX_PERIOD;
    capabilities->maximum_prescaler_divider = ET_STIMER_WRAP_MAX_PRESCALER;
    capabilities->compare_channel_count = ET_STIMER_WRAP_COMPARE_CHANNEL_COUNT;
    capabilities->instance_count = ET_STIMER_WRAP_INSTANCE_COUNT;
    capabilities->irq_sources = ET_STIMER_WRAP_IRQ_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply one complete STIMER configuration.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] config Public configuration.
 * @note Period and compare Driver gaps are resolved by isolated Test Driver Extensions.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_configure(et_stimer_id_t stimer_id,
                                          const et_stimer_wrap_config_t *config)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (config == NULL) || (config->stimer_id != stimer_id) ||
        (config_is_valid(config) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_setEmulationMode(mapping->driver_instance, (STIMER_EmulationMode)config->mode);
    STIMER_setLoadMode(mapping->driver_instance, (STIMER_LoadMode)config->load_mode);
    STIMER_setPreScaler(mapping->driver_instance, config->prescaler_divider);

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    if (STIMER_testSetPeriod32(mapping->driver_instance, config->period_ticks) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Select STIMER behavior while the CPU is halted by a debugger.
 * @param[in] stimer_id Stable logical STIMER identifier.
 * @param[in] policy Public CPU Halt policy.
 * @note This function calls only the STIMER Chip Driver; it does not control the debugger.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_debug_halt_policy_set(et_stimer_id_t stimer_id, uint8_t policy)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (policy > ET_STIMER_WRAP_DEBUG_HALT_RUN_FREE))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (policy == ET_STIMER_WRAP_DEBUG_HALT_PAUSE)
    {
        STIMER_enableCPUHalt(mapping->driver_instance);
    }
    else
    {
        STIMER_disableCPUHalt(mapping->driver_instance);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Start one STIMER count process.
 * @param[in] stimer_id Stable logical identifier.
 * @note This action does not clear the current count.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_start(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_startTimer(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Stop one STIMER count process.
 * @param[in] stimer_id Stable logical identifier.
 * @note This action leaves the current count observable.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_stop(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_stopTimer(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Pause one STIMER while retaining its count.
 * @param[in] stimer_id Stable logical identifier.
 * @note Resume is a separate atomic action.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_pause(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_pauseTimer(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resume one paused STIMER.
 * @param[in] stimer_id Stable logical identifier.
 * @note This action does not reload or clear the count.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_resume(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_resumeTimer(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear one STIMER counter through the Driver pulse action.
 * @param[in] stimer_id Stable logical identifier.
 * @note The configured lifecycle state remains unchanged.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_clear(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_resetTimerCount(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reload one STIMER with its configured period.
 * @param[in] stimer_id Stable logical identifier.
 * @note The Driver owns the hardware load pulse.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_reload(et_stimer_id_t stimer_id)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_reloadTimerCounter(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read one live 32-bit STIMER count.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] count Destination count.
 * @note Reading does not latch or clear the timer.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_live_count_get(et_stimer_id_t stimer_id, uint32_t *count)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *count = STIMER_getTimerCount(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Latch and read one 32-bit STIMER count.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] count Destination latched count.
 * @note Every call issues a new Driver latch action.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_latched_count_get(et_stimer_id_t stimer_id, uint32_t *count)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *count = (uint32_t)STIMER_getTimerCountLatch(mapping->driver_instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read all published STIMER runtime status bits.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] status Destination status mask.
 * @note Reading preserves all status bits.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_status_get(et_stimer_id_t stimer_id, uint32_t *status)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (status == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    /*
     * STM_STATUS_RPT is read-to-clear. Capture it once in the Chip Driver and
     * only then translate the raw snapshot into the stable public status mask.
     */
    *status = STIMER_testGetStatusSnapshot(mapping->driver_instance) & ET_STIMER_WRAP_STATUS_ALL;
#else
    (void)mapping;
    *status = 0u;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure one 32-bit compare threshold.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] channel Stable zero-based compare channel.
 * @param[in] threshold Hardware compare threshold.
 * @note The isolated Test Driver Extension fixes the legacy register selection bug.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_compare_set(et_stimer_id_t stimer_id, uint8_t channel,
                                            uint32_t threshold)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (channel >= ET_STIMER_WRAP_COMPARE_CHANNEL_COUNT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return (STIMER_testLoadCompare32(mapping->driver_instance, (STIMER_CounterCompareModule)channel,
                                     threshold) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
#else
    (void)stimer_id;
    (void)channel;
    (void)threshold;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Configure one event-output pulse width in STIMER clock cycles.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] event Exactly one published Compare or Overflow event bit.
 * @param[in] width_cycles Pulse width in STIMER clock cycles.
 * @note The Chip Driver translates public cycle count to the local register encoding.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_event_pulse_width_set(et_stimer_id_t stimer_id, uint32_t event,
                                                      uint16_t width_cycles)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (event == 0u) || ((event & ET_STIMER_WRAP_IRQ_ALL) != event) ||
        ((event & (event - 1u)) != 0u) ||
        (width_cycles < ET_STIMER_WRAP_MIN_EVENT_PULSE_WIDTH_CYCLES) ||
        (width_cycles > ET_STIMER_WRAP_MAX_EVENT_PULSE_WIDTH_CYCLES))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return (STIMER_testSetEventPulseWidth(mapping->driver_instance, event, width_cycles) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
#else
    (void)stimer_id;
    (void)event;
    (void)width_cycles;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Select one STIMER event as the hardware DMA request source.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] event Exactly one published Compare or Overflow event bit.
 * @note The public event value is translated explicitly to the current Chip Driver selector.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_dma_request_select(et_stimer_id_t stimer_id, uint32_t event)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);
    uint32_t driver_request;

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (event)
    {
        case ET_STIMER_WRAP_IRQ_COMPARE0:
        {
            driver_request = STIMER_DMA_REQ_COMPARE_EVT0;
            break;
        }

        case ET_STIMER_WRAP_IRQ_COMPARE1:
        {
            driver_request = STIMER_DMA_REQ_COMPARE_EVT1;
            break;
        }

        case ET_STIMER_WRAP_IRQ_COMPARE2:
        {
            driver_request = STIMER_DMA_REQ_COMPARE_EVT2;
            break;
        }

        case ET_STIMER_WRAP_IRQ_COMPARE3:
        {
            driver_request = STIMER_DMA_REQ_COMPARE_EVT3;
            break;
        }

        case ET_STIMER_WRAP_IRQ_OVERFLOW:
        {
            driver_request = STIMER_DMA_REQ_COUNT_OVERFLOW;
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    STIMER_selectDMARequest(mapping->driver_instance, driver_request);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure one logical emergency source for STIMER capture.
 * @param[in] stimer_id Stable logical STIMER identifier.
 * @param[in] source_id Stable logical source selected by the chip mapping.
 * @param[in] trigger_group Stable logical emergency trigger group.
 * @note Source masks and physical routing remain isolated in chip config and
 *       the STIMER Chip Driver Extension.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_emergency_capture_configure(et_stimer_id_t stimer_id,
                                                            uint8_t source_id,
                                                            uint8_t trigger_group)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((mapping->features & ET_STIMER_WRAP_FEATURE_EMERGENCY_CAPTURE) == 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((source_id != mapping->emergency_source_id) ||
        (trigger_group != mapping->emergency_trigger_group))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return (STIMER_testConfigureEmergencyCapture(mapping->driver_instance, mapping->emergency_index,
                                                 trigger_group,
                                                 mapping->emergency_source_mask) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
#else
    (void)source_id;
    (void)trigger_group;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Read the system-level emergency STIMER count capture.
 * @param[in] stimer_id Stable logical STIMER identifier.
 * @param[out] count Destination for the captured count.
 * @note The selected chip exposes this endpoint as read-only; no register is
 *       cleared by the read.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_emergency_capture_get(et_stimer_id_t stimer_id, uint32_t *count)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((mapping->features & ET_STIMER_WRAP_FEATURE_EMERGENCY_CAPTURE) == 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return (STIMER_testGetEmergencyCapture(mapping->emergency_index, count) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
#else
    *count = 0u;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Disable one logical emergency capture route.
 * @param[in] stimer_id Stable logical STIMER identifier.
 * @param[in] source_id Stable logical source selected by the chip mapping.
 * @param[in] trigger_group Stable logical emergency trigger group.
 * @note The selected chip capture register is read-only; clearing disables
 *       its source route and the next accepted trigger replaces the value.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_emergency_capture_clear(et_stimer_id_t stimer_id, uint8_t source_id,
                                                        uint8_t trigger_group)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((mapping->features & ET_STIMER_WRAP_FEATURE_EMERGENCY_CAPTURE) == 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((source_id != mapping->emergency_source_id) ||
        (trigger_group != mapping->emergency_trigger_group))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return (STIMER_testClearEmergencyCapture(mapping->emergency_index, trigger_group) == DRV_OK)
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
#else
    (void)source_id;
    (void)trigger_group;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Resolve a logical STIMER to its physical IRQ route.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] route Destination route.
 * @note This lookup does not configure NVIC.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_get_irq_route(et_stimer_id_t stimer_id, et_irq_route_t *route)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = mapping->irq_line;
    route->reserved = 0u;
    route->route_events = ET_STIMER_WRAP_IRQ_ALL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note NVIC binding remains owned by the Service IRQ Manager.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_enable(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_enableInterrupt(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note Existing Raw state is preserved until explicit clear.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_disable(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_disableInterrupt(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note Raw state remains observable while masked.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_mask(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_setInterruptMask(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note Source enable state remains unchanged.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_unmask(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_clearInterruptMask(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note Force proves the IRQ control path, not natural timer generation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_force(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_forceInterrupt(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected STIMER IRQ sources.
 * @param[in] stimer_id Stable logical identifier.
 * @param[in] sources Nonempty published source mask.
 * @note This action clears only the selected source bits.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_clear(et_stimer_id_t stimer_id, uint32_t sources)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);

    if ((mapping == NULL) || (irq_sources_are_valid(sources) == 0))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    STIMER_clearInterruptStatus(mapping->driver_instance, sources);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read STIMER Raw and effective IRQ states.
 * @param[in] stimer_id Stable logical identifier.
 * @param[out] snapshot Destination hardware snapshot.
 * @note Reading does not clear any source.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_stimer_wrap_irq_snapshot_get(et_stimer_id_t stimer_id,
                                                 et_stimer_wrap_irq_snapshot_t *snapshot)
{
    const et_stimer_wrap_mapping_t *mapping = find_mapping(stimer_id);
    uint32_t source;

    if ((mapping == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    snapshot->raw = 0u;
    snapshot->status = 0u;

    for (source = 1u; source <= ET_STIMER_WRAP_IRQ_OVERFLOW; source <<= 1u)
    {
        if (STIMER_getInterruptStatusRaw(mapping->driver_instance, source))
        {
            snapshot->raw |= source;
        }

        if (STIMER_getInterruptStatus(mapping->driver_instance, source))
        {
            snapshot->status |= source;
        }
    }

    return ET_WRAP_STATUS_OK;
}
