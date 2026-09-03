/** @file et_syscnt_wrap.c @brief Map system counter actions to the selected Driver. */
#include "et_syscnt_wrap.h"

#include <stddef.h>
#include "et6x_cortex.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_syscnt_id_t id;
    et_syscnt_capabilities_t capabilities;
} et_syscnt_mapping_t;

static const et_syscnt_mapping_t mappings[] = ET_CHIP_SYSCNT_MAP_TABLE;
static const SYSCNT_TestView views[] = ET_CHIP_SYSCNT_READ_VIEW_MAP_TABLE;

/**
 * @brief Find one explicitly mapped logical counter.
 * @param[in] id Public counter identity.
 * @return Mapping pointer or NULL when absent.
 * @note Reads immutable chip facts only; no hardware access.
 */
static const et_syscnt_mapping_t *find_mapping(et_syscnt_id_t id)
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
 * @brief Translate selected Driver status to the public Wrap vocabulary.
 * @param[in] status Driver result.
 * @return Argument, busy, success or I/O failure status without a Boolean collapse.
 * @note No retry or hardware action is hidden by this conversion.
 */
static et_wrap_status_t status_from_driver(DRV_Status status)
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

        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Return immutable counter capability facts.
 * @param[in] id Public counter identity.
 * @param[out] caps Supported actions and widths.
 * @return Argument, unsupported or success status.
 * @note Capability queries never enable clocks or touch the counter.
 */
et_wrap_status_t et_syscnt_wrap_get_capabilities(et_syscnt_id_t id, et_syscnt_capabilities_t *caps)
{
    const et_syscnt_mapping_t *mapping = find_mapping(id);

    if (caps == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *caps = mapping->capabilities;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or stop a mapped counter without loading a value.
 * @param[in] id Public counter identity.
 * @param[in] enabled Boolean counting state.
 * @return Mapped Driver status or unsupported identity.
 * @note Count, frequency identification and routing remain unchanged.
 */
et_wrap_status_t et_syscnt_wrap_set_enabled(et_syscnt_id_t id, uint8_t enabled)
{
    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testSetEnabled(enabled));
}

/**
 * @brief Load a stopped counter without implicitly enabling it.
 * @param[in] id Public counter identity.
 * @param[in] value Counter ticks to load.
 * @return Mapped Driver status; BUSY while counting.
 * @note No stop or baseline sequence is inserted on behalf of the Case.
 */
et_wrap_status_t et_syscnt_wrap_load_value(et_syscnt_id_t id, uint64_t value)
{
    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testLoadStopped(value));
}

/**
 * @brief Read one coherent counter value through a mapped register view.
 * @param[in] id Public counter identity.
 * @param[in] view Stable CONTROL or READ selector.
 * @param[out] count Counter ticks, unchanged on failure.
 * @return Mapped Driver status or invalid view.
 * @note Bounded consistency retries belong to the Driver, not this Wrap.
 */
et_wrap_status_t et_syscnt_wrap_get_count(et_syscnt_id_t id, et_syscnt_view_t view, uint64_t *count)
{
    if ((count == NULL) || ((view != ET_SYSCNT_VIEW_CONTROL) && (view != ET_SYSCNT_VIEW_READ)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testReadCount(views[view], count));
}

/**
 * @brief Read enable, halt policy, actual halt status and frequency identification.
 * @param[in] id Public counter identity.
 * @param[out] control Public control readback.
 * @return Mapped Driver status or invalid output.
 * @note Configured halt policy is never substituted for actual halt status.
 */
et_wrap_status_t et_syscnt_wrap_get_control(et_syscnt_id_t id, et_syscnt_control_t *control)
{
    SYSCNT_TestControl actual;
    DRV_Status status;

    if (control == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = SYSCNT_testGetControl(&actual);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    control->enabled = actual.enabled;
    control->halt_policy = actual.halt_enabled ? ET_SYSCNT_PAUSE : ET_SYSCNT_RUN_FREE;
    control->debug_halted = actual.debug_halted;
    control->frequency_id_hz = actual.frequency_id_hz;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Set only the counter's response to a debug halt request.
 * @param[in] id Public counter identity.
 * @param[in] policy Stable RUN_FREE or PAUSE policy.
 * @return Mapped Driver status or invalid policy.
 * @note System routing and actual CPU run control remain caller-owned.
 */
et_wrap_status_t et_syscnt_wrap_set_halt_policy(et_syscnt_id_t id, et_syscnt_halt_policy_t policy)
{
    if ((policy != ET_SYSCNT_RUN_FREE) && (policy != ET_SYSCNT_PAUSE))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testSetHaltPolicy(policy == ET_SYSCNT_PAUSE));
}

/**
 * @brief Register a frequency identifier while counting is disabled.
 * @param[in] id Public counter identity.
 * @param[in] frequency_hz Nonzero identification in Hz.
 * @return Mapped Driver status; BUSY while counting.
 * @note This is metadata, not a clock source or divider configuration.
 */
et_wrap_status_t et_syscnt_wrap_set_frequency_id(et_syscnt_id_t id, uint32_t frequency_hz)
{
    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testSetFrequencyId(frequency_hz));
}

/**
 * @brief Borrow or release a continuously running local reference counter.
 * @param[in] id Public counter identity.
 * @param[in] enabled Boolean reference ownership request.
 * @return Mapped Driver status or unsupported identity.
 * @note Reference count is not cleared; owned control bits are restored on release.
 */
et_wrap_status_t et_syscnt_wrap_set_reference_enabled(et_syscnt_id_t id, uint8_t enabled)
{
    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SYSCNT_testSetReferenceEnabled(enabled));
}

/**
 * @brief Take a reference-before/counter/reference-after raw sample.
 * @param[in] id Public counter identity.
 * @param[out] sample Raw ticks, updated only on successful sampling.
 * @return Mapped Driver status; BUSY if the reference was not acquired.
 * @note No waiting, clock calibration or pass/fail evaluation is performed.
 */
et_wrap_status_t et_syscnt_wrap_sample_reference(et_syscnt_id_t id,
                                                 et_syscnt_reference_sample_t *sample)
{
    uint32_t before;
    uint32_t after;
    uint64_t count;
    DRV_Status status;

    if (sample == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_mapping(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = SYSCNT_testSampleReference(&before, &count, &after);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    sample->reference_before = before;
    sample->count = count;
    sample->reference_after = after;

    return ET_WRAP_STATUS_OK;
}
