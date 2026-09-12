/** @file et_etim_wrap.c @brief ETIM logical mapping through the own Chip Driver only. */
#include "et_etim_wrap.h"
#include <stddef.h>
#include "et6x_etimer.h"
#include "et_chip_wrap_config.h"
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
typedef struct
{
    et_etim_id_t logical;
    uint32_t physical;
    et_etim_timebase_t limits;
} etim_mapping_t;
typedef struct
{
    uint32_t semantic;
    uint32_t physical;
} etim_irq_mapping_t;
static const etim_mapping_t mappings[] = ET_CHIP_ETIM_MAP_TABLE;
static const ETIMER_TestEnable enable_map[] = ET_CHIP_ETIM_ENABLE_MAP_TABLE;
static const etim_irq_mapping_t irq_map[] = ET_CHIP_ETIM_IRQ_MAP_TABLE;
/**
 * @brief Find one explicitly mapped logical channel.
 * @param[in] id Logical channel identifier.
 * @note No hardware access or default instance fallback.
 * @return Immutable mapping or NULL for an unknown identifier.
 */
static const etim_mapping_t *find_mapping(et_etim_id_t id)
{
    size_t index;

    for (index = 0u; index < sizeof(mappings) / sizeof(mappings[0]); ++index)
    {
        if (mappings[index].logical == id)
        {
            return &mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Preserve Driver error categories at the public boundary.
 * @param[in] status Result returned by the own Chip Driver.
 * @note Does not retry, clear state or convert timeout to success.
 * @return Equivalent public status, or IO_ERROR for other Driver failures.
 */
static et_wrap_status_t from_driver(DRV_Status status)
{
    switch (status)
    {
        case DRV_OK:
        {
            return ET_WRAP_STATUS_OK;
        }

        case DRV_PARAM_ERR:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        case DRV_BUSY:
        {
            return ET_WRAP_STATUS_BUSY;
        }

        case DRV_TIMEOUT:
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Translate IRQ masks using the target's semantic mapping.
 * @param[in] mask Source mask in the selected input vocabulary.
 * @param[in] to_driver Nonzero selects semantic-to-physical translation.
 * @note Only mapped bits are returned; no registers are accessed.
 * @return Translated bit mask.
 */
static uint32_t irq_translate(uint32_t mask, int to_driver)
{
    uint32_t result = 0u;
    size_t index;

    for (index = 0u; index < sizeof(irq_map) / sizeof(irq_map[0]); ++index)
    {
        if ((mask & (to_driver ? irq_map[index].semantic : irq_map[index].physical)) != 0u)
        {
            result |= to_driver ? irq_map[index].physical : irq_map[index].semantic;
        }
    }

    return result;
}

/**
 * @brief Preserve count observations from either bounded pulse operation.
 * @param[in] physical Resolved SDK channel index.
 * @param[in] polls Maximum software sample count.
 * @param[out] observation Before and last hardware samples when available.
 * @param[in] clear Nonzero selects stopped-counter clearing.
 * @note Invalid input leaves output untouched; BUSY/TIMEOUT retain actual samples.
 * @return Translated Driver result without hidden retries.
 */
static et_wrap_status_t count_action(uint32_t physical, uint32_t polls,
                                     et_etim_count_observation_t *observation, int clear)
{
    ETIMER_TestCountObservation native;
    DRV_Status status;

    if (observation == NULL || polls == 0u || polls > ETIMER_TEST_MAX_COUNT_POLLS)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = clear ? ETIMER_testClearCount(physical, polls, &native)
                   : ETIMER_testLatchCount(physical, polls, &native);

    if (status != DRV_PARAM_ERR)
    {
        observation->before = native.before;
        observation->previous_latched = native.previousLatch;
        observation->latched = native.latched;
        observation->live = native.live;
        observation->polls = native.polls;
    }

    return from_driver(status);
}

/**
 * @brief Read the supported limits for one logical timer.
 * @param[in] id Logical timer channel identifier.
 * @param[out] caps Mapped limits and supported semantic IRQ sources.
 * @note No hardware action or implicit instance selection.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_capabilities_get(et_etim_id_t id, et_etim_capabilities_t *caps)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL || caps == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    caps->maximum_divider = mapping->limits.divider;
    caps->maximum_period_ticks = mapping->limits.period_ticks;
    caps->maximum_count_polls = ETIMER_TEST_MAX_COUNT_POLLS;
    caps->irq_sources = irq_translate(UINT32_MAX, 0);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure the timebase of one stopped timer.
 * @param[in] id Logical timer channel identifier.
 * @param[in] config Actual divider and full period in counter ticks.
 * @note Does not reset phase, enable paths or configure peer IPs.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_timebase_configure(et_etim_id_t id, const et_etim_timebase_t *config)
{
    const etim_mapping_t *mapping = find_mapping(id);
    ETIMER_TestTimeBase native;

    if (mapping == NULL || config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    native.divider = config->divider;
    native.periodTicks = config->period_ticks;

    return from_driver(ETIMER_testConfigureTimeBase(mapping->physical, &native));
}

/**
 * @brief Read the selected timer timebase.
 * @param[in] id Logical timer channel identifier.
 * @param[out] config Actual timebase readback.
 * @note No cached configuration is returned.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_timebase_get(et_etim_id_t id, et_etim_timebase_t *config)
{
    const etim_mapping_t *mapping = find_mapping(id);
    ETIMER_TestTimeBase native;
    DRV_Status status;

    if (mapping == NULL || config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = ETIMER_testGetTimeBase(mapping->physical, &native);

    if (status == DRV_OK)
    {
        config->divider = native.divider;
        config->period_ticks = native.periodTicks;
    }

    return from_driver(status);
}

/**
 * @brief Set one independent enable control.
 * @param[in] id Logical timer channel identifier.
 * @param[in] control Independent enable selector.
 * @param[in] enabled Boolean state to write.
 * @note Does not initialize or clear the channel.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_enable_set(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t enabled)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL || (unsigned)control >= ET_ETIM_ENABLE_COUNT || enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testSetEnable(mapping->physical, enable_map[control], enabled));
}

/**
 * @brief Read one independent enable control.
 * @param[in] id Logical timer channel identifier.
 * @param[in] control Independent enable selector.
 * @param[out] enabled Actual Boolean readback.
 * @note Only the selected hardware field is sampled.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_enable_get(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t *enabled)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL || (unsigned)control >= ET_ETIM_ENABLE_COUNT || enabled == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testGetEnable(mapping->physical, enable_map[control], enabled));
}

/**
 * @brief Read both counter endpoints without relatching.
 * @param[in] id Logical timer channel identifier.
 * @param[out] live Live hardware counter.
 * @param[out] latched Held hardware counter from the last latch.
 * @note Reads are sequential and not atomic.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_get(et_etim_id_t id, uint32_t *live, uint32_t *latched)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testReadCount(mapping->physical, live, latched));
}

/**
 * @brief Latch once with bounded freshness observation.
 * @param[in] id Logical timer channel identifier.
 * @param[in] polls Maximum count samples, not a clock deadline.
 * @param[out] observation Observed before and final hardware samples.
 * @note Caller owns a no-wrap/no-sync window; failures retain actual samples.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_latch(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return count_action(mapping->physical, polls, observation, 0);
}

/**
 * @brief Clear one stopped nonzero counter with bounded observation.
 * @param[in] id Logical timer channel identifier.
 * @param[in] polls Maximum count samples, not a clock deadline.
 * @param[out] observation Observed nonzero-to-zero transition or final failure samples.
 * @note Does not stop the counter; caller excludes concurrent synchronization.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_clear(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation)
{
    const etim_mapping_t *mapping = find_mapping(id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return count_action(mapping->physical, polls, observation, 1);
}

/**
 * @brief Configure independent IP source enable and mask fields.
 * @param[in] id Logical timer channel identifier.
 * @param[in] enabled Complete semantic source enable mask.
 * @param[in] masked Complete semantic source suppression mask.
 * @note Sequential writes only; session owner controls delivery during reconfiguration.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_configure(et_etim_id_t id, uint32_t enabled, uint32_t masked)
{
    const etim_mapping_t *mapping = find_mapping(id);
    uint32_t allowed = irq_translate(UINT32_MAX, 0);

    if (mapping == NULL || ((enabled | masked) & ~allowed) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testConfigureInterrupt(mapping->physical, irq_translate(enabled, 1),
                                                     irq_translate(masked, 1)));
}

/**
 * @brief Read and translate four independent IP IRQ endpoints.
 * @param[in] id Logical timer channel identifier.
 * @param[out] snapshot Independent enable, mask, raw and effective status samples.
 * @note Does not synthesize status or claim ISR delivery.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_snapshot_get(et_etim_id_t id, et_etim_irq_snapshot_t *snapshot)
{
    const etim_mapping_t *mapping = find_mapping(id);
    ETIMER_TestInterruptSnapshot native;
    DRV_Status status;

    if (mapping == NULL || snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = ETIMER_testGetInterrupt(mapping->physical, &native);

    if (status == DRV_OK)
    {
        snapshot->enabled = irq_translate(native.enabled, 0);
        snapshot->masked = irq_translate(native.masked, 0);
        snapshot->raw = irq_translate(native.raw, 0);
        snapshot->status = irq_translate(native.status, 0);
    }

    return from_driver(status);
}

/**
 * @brief Force exactly the selected IP interrupt sources.
 * @param[in] id Logical timer channel identifier.
 * @param[in] sources Nonempty semantic source mask.
 * @note Reports command issuance only; does not bind IRQs or fabricate completion.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_force(et_etim_id_t id, uint32_t sources)
{
    const etim_mapping_t *mapping = find_mapping(id);
    uint32_t allowed = irq_translate(UINT32_MAX, 0);

    if (mapping == NULL || sources == 0u || (sources & ~allowed) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testForceInterrupt(mapping->physical, irq_translate(sources, 1)));
}

/**
 * @brief Acknowledge exactly the selected IP interrupt sources.
 * @param[in] id Logical timer channel identifier.
 * @param[in] sources Nonempty semantic source mask.
 * @note Reports command issuance only; does not bind IRQs or fabricate completion.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_clear(et_etim_id_t id, uint32_t sources)
{
    const etim_mapping_t *mapping = find_mapping(id);
    uint32_t allowed = irq_translate(UINT32_MAX, 0);

    if (mapping == NULL || sources == 0u || (sources & ~allowed) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(ETIMER_testClearInterrupt(mapping->physical, irq_translate(sources, 1)));
}

#else
/**
 * @brief Read the supported limits for one logical timer.
 * @param[in] id Logical timer channel identifier.
 * @param[out] caps Mapped limits and supported semantic IRQ sources.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_capabilities_get(et_etim_id_t id, et_etim_capabilities_t *caps)
{
    (void)id;
    (void)caps;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Configure the timebase of one stopped timer.
 * @param[in] id Logical timer channel identifier.
 * @param[in] config Actual divider and full period in counter ticks.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_timebase_configure(et_etim_id_t id, const et_etim_timebase_t *config)
{
    (void)id;
    (void)config;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Read the selected timer timebase.
 * @param[in] id Logical timer channel identifier.
 * @param[out] config Actual timebase readback.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_timebase_get(et_etim_id_t id, et_etim_timebase_t *config)
{
    (void)id;
    (void)config;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Set one independent enable control.
 * @param[in] id Logical timer channel identifier.
 * @param[in] control Independent enable selector.
 * @param[in] enabled Boolean state to write.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_enable_set(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t enabled)
{
    (void)id;
    (void)control;
    (void)enabled;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Read one independent enable control.
 * @param[in] id Logical timer channel identifier.
 * @param[in] control Independent enable selector.
 * @param[out] enabled Actual Boolean readback.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_enable_get(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t *enabled)
{
    (void)id;
    (void)control;
    (void)enabled;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Read both counter endpoints without relatching.
 * @param[in] id Logical timer channel identifier.
 * @param[out] live Live hardware counter.
 * @param[out] latched Held hardware counter from the last latch.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_get(et_etim_id_t id, uint32_t *live, uint32_t *latched)
{
    (void)id;
    (void)live;
    (void)latched;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Latch once with bounded freshness observation.
 * @param[in] id Logical timer channel identifier.
 * @param[in] polls Maximum count samples, not a clock deadline.
 * @param[out] observation Observed before and final hardware samples.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_latch(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation)
{
    (void)id;
    (void)polls;
    (void)observation;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Clear one stopped nonzero counter with bounded observation.
 * @param[in] id Logical timer channel identifier.
 * @param[in] polls Maximum count samples, not a clock deadline.
 * @param[out] observation Observed nonzero-to-zero transition or final failure samples.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_count_clear(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation)
{
    (void)id;
    (void)polls;
    (void)observation;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Configure independent IP source enable and mask fields.
 * @param[in] id Logical timer channel identifier.
 * @param[in] enabled Complete semantic source enable mask.
 * @param[in] masked Complete semantic source suppression mask.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_configure(et_etim_id_t id, uint32_t enabled, uint32_t masked)
{
    (void)id;
    (void)enabled;
    (void)masked;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Read and translate four independent IP IRQ endpoints.
 * @param[in] id Logical timer channel identifier.
 * @param[out] snapshot Independent enable, mask, raw and effective status samples.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_snapshot_get(et_etim_id_t id, et_etim_irq_snapshot_t *snapshot)
{
    (void)id;
    (void)snapshot;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Force exactly the selected IP interrupt sources.
 * @param[in] id Logical timer channel identifier.
 * @param[in] sources Nonempty semantic source mask.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_force(et_etim_id_t id, uint32_t sources)
{
    (void)id;
    (void)sources;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Acknowledge exactly the selected IP interrupt sources.
 * @param[in] id Logical timer channel identifier.
 * @param[in] sources Nonempty semantic source mask.
 * @note Test Driver Extensions are disabled; no hardware is accessed.
 * @return Stable Wrap result; unsupported builds return NOT_SUPPORTED.
 */
et_wrap_status_t et_etim_wrap_irq_clear(et_etim_id_t id, uint32_t sources)
{
    (void)id;
    (void)sources;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

#endif
