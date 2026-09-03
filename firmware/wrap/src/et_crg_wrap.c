/** @file et_crg_wrap.c @brief Implement the stable CRG Wrap API. */
#include "et_crg_wrap.h"

#include <stddef.h>

#include "et6x_crg.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    uint8_t peripheral;
    uint8_t instance_id;
    uint8_t chip_peripheral_id;
} et_crg_mapping_t;

static const et_crg_mapping_t peripheral_map[] = ET_CHIP_CRG_MAP_TABLE;

static const uint8_t syscnt_clock_map[] = ET_CHIP_CRG_SYSCNT_MAP_TABLE;

/**
 * @brief Check whether the chip exposes the requested logical counter clock.
 * @param[in] instance_id Logical counter instance.
 * @return Nonzero when the static map contains the instance.
 * @note Read-only map lookup; no clock or reset action is performed.
 */
static uint8_t has_syscnt_clock(uint8_t instance_id)
{
    size_t index;

    for (index = 0u; index < sizeof(syscnt_clock_map) / sizeof(syscnt_clock_map[0]); ++index)
    {
        if (syscnt_clock_map[index] == instance_id)
        {
            return 1u;
        }
    }

    return 0u;
}

/**
 * @brief Change one system counter clock gate without asserting any reset.
 * @param[in] instance_id Logical counter instance from Chip Config.
 * @param[in] enabled Boolean gate state.
 * @return Stable argument, support or execution status.
 * @note Unlocks CRG only around the Driver write; other gates remain unchanged.
 */
et_wrap_status_t et_crg_wrap_set_syscnt_clock(uint8_t instance_id, uint8_t enabled)
{
    DRV_Status result;

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (has_syscnt_clock(instance_id) == 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CRG_unlockClockConfig();
    result = CRG_testSetSYSCNTClock(enabled);
    CRG_lockClockConfig();

    return result == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read one system counter clock gate through its owning Driver.
 * @param[in] instance_id Logical counter instance.
 * @param[out] enabled Boolean hardware gate state.
 * @return Stable argument, support or execution status.
 * @note Does not access the counter, change the gate, or infer clock frequency.
 */
et_wrap_status_t et_crg_wrap_get_syscnt_clock(uint8_t instance_id, uint8_t *enabled)
{
    if (enabled == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (has_syscnt_clock(instance_id) == 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CRG_testGetSYSCNTClock(enabled) == DRV_OK ? ET_WRAP_STATUS_OK
                                                     : ET_WRAP_STATUS_STATE_ERROR;
}

typedef struct
{
    uint8_t wdg_id;
    WDG_Type *driver_instance;
    uint8_t maximum_divider;
} et_crg_wdg_clock_mapping_t;

static const et_crg_wdg_clock_mapping_t wdg_clock_map[] = ET_CHIP_CRG_WDG_CLOCK_MAP_TABLE;

/**
 * @brief Resolve one stable peripheral/instance pair to the selected CRG Driver selector.
 *
 * @param[in] peripheral Stable CRG peripheral type.
 * @param[in] instance_id Stable logical instance identifier within that peripheral type.
 * @param[out] chip_peripheral Selected chip Driver peripheral selector.
 *
 * @note This helper reads compile-time Chip Config mapping data only. It does not unlock CRG
 *       configuration or change clock/reset hardware state.
 *
 * @return ET_WRAP_STATUS_OK when a mapping exists.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the logical pair is absent on this chip.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when chip_peripheral is NULL.
 */
static et_wrap_status_t map_peripheral(uint8_t peripheral, uint8_t instance_id,
                                       CRG_Peripherals *chip_peripheral)
{
    size_t index;

    if (chip_peripheral == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < (sizeof(peripheral_map) / sizeof(peripheral_map[0])); ++index)
    {
        if ((peripheral_map[index].peripheral == peripheral) &&
            (peripheral_map[index].instance_id == instance_id))
        {
            *chip_peripheral = (CRG_Peripherals)peripheral_map[index].chip_peripheral_id;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Enable or disable the clock of one mapped peripheral instance.
 *
 * @param[in] peripheral Stable CRG peripheral type.
 * @param[in] instance_id Stable logical instance identifier.
 * @param[in] enabled Canonical Boolean selecting clock enable or disable.
 *
 * @note This function changes CRG clock-gating hardware. The CRG Driver lock is opened only around
 *       the selected enable/disable operation and is restored before returning.
 *
 * @return ET_WRAP_STATUS_OK when the mapped clock action is completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when enabled is not Boolean.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when no chip mapping exists for the logical instance.
 */
et_wrap_status_t et_crg_wrap_set_clock(uint8_t peripheral, uint8_t instance_id, uint8_t enabled)
{
    CRG_Peripherals chip_peripheral;
    et_wrap_status_t status;

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_peripheral(peripheral, instance_id, &chip_peripheral);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    CRG_unlockClockConfig();

    if (enabled != 0u)
    {
        CRG_enablePeripheral(chip_peripheral);
    }
    else
    {
        CRG_disablePeripheral(chip_peripheral);
    }

    CRG_lockClockConfig();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Pulse the Driver reset for one mapped peripheral instance.
 *
 * @param[in] peripheral Stable CRG peripheral type.
 * @param[in] instance_id Stable logical instance identifier.
 *
 * @note This function changes peripheral reset hardware through the CRG Driver. Configuration lock
 *       ownership is opened only for the reset operation and restored before returning.
 *
 * @return ET_WRAP_STATUS_OK when the mapped peripheral is reset.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when no chip mapping exists for the logical instance.
 */
et_wrap_status_t et_crg_wrap_reset(uint8_t peripheral, uint8_t instance_id)
{
    CRG_Peripherals chip_peripheral;
    et_wrap_status_t status;

    status = map_peripheral(peripheral, instance_id, &chip_peripheral);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    CRG_unlockClockConfig();
    CRG_resetPeripheral(chip_peripheral);
    CRG_lockClockConfig();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one logical WDG clock instance through the CRG chip map.
 *
 * @param[in] wdg_id Stable logical WDG instance identifier.
 * @return Matching CRG mapping, or NULL when the instance is not supported.
 *
 * @note The lookup reads chip configuration only and does not touch hardware.
 */
static const et_crg_wdg_clock_mapping_t *find_wdg_clock_mapping(uint8_t wdg_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(wdg_clock_map) / sizeof(wdg_clock_map[0])); ++index)
    {
        if (wdg_clock_map[index].wdg_id == wdg_id)
        {
            return &wdg_clock_map[index];
        }
    }

    return NULL;
}

/**
 * @brief Select one logical WDG clock source and divider through the CRG Driver.
 *
 * @param[in] wdg_id Stable logical WDG instance identifier.
 * @param[in] source Stable CRG WDG clock source value.
 * @param[in] divider Encoded APB1 divider; HSOSC requires zero.
 * @return Stable Wrap status for the CRG action.
 *
 * @note WDG Wrap is intentionally not called here. Clock ownership remains in
 *       CRG and the only hardware action is delegated to the CRG Driver.
 */
et_wrap_status_t et_crg_wrap_set_wdg_clock(uint8_t wdg_id, uint8_t source, uint8_t divider)
{
    const et_crg_wdg_clock_mapping_t *mapping = find_wdg_clock_mapping(wdg_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((source > (uint8_t)CRG_WDG_CLKSRC_APB1) || (divider > mapping->maximum_divider) ||
        ((source == (uint8_t)CRG_WDG_CLKSRC_HSOSC) && (divider != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CRG_unlockClockConfig();
    CRG_selectWDGClockSource(mapping->driver_instance, (CRG_WDGClockSource)source, divider);
    CRG_lockClockConfig();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read one logical WDG clock source and divider through the CRG Driver.
 *
 * @param[in] wdg_id Stable logical WDG instance identifier.
 * @param[out] clock Destination for source and encoded divider.
 * @return Stable Wrap status for the CRG readback.
 *
 * @note The readback uses the isolated CRG test-driver extension because the
 *       released SDK does not expose the source/divider fields separately.
 */
et_wrap_status_t et_crg_wrap_get_wdg_clock(uint8_t wdg_id, et_crg_wrap_wdg_clock_t *clock)
{
    const et_crg_wdg_clock_mapping_t *mapping = find_wdg_clock_mapping(wdg_id);
    CRG_TestWdgClockSnapshot snapshot;

    if ((mapping == NULL) || (clock == NULL))
    {
        return (mapping == NULL) ? ET_WRAP_STATUS_NOT_SUPPORTED : ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CRG_testGetWDGClockConfig(mapping->driver_instance, &snapshot) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    clock->source = snapshot.source;
    clock->divider = snapshot.divider;
    clock->reserved[0] = 0u;
    clock->reserved[1] = 0u;

    return ET_WRAP_STATUS_OK;
}
