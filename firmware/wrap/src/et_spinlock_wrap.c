/**
 * @file et_spinlock_wrap.c
 * @brief Implement stable SPINLOCK operations through the selected Driver.
 */

#include "et_spinlock_wrap.h"

#include <stddef.h>

#include "et6x_spinlock.h"
#include "et_chip_wrap_config.h"

#include "et_core1_image.h"

typedef struct
{
    et_spinlock_id_t spinlock_id;
    uint32_t features;
    uint16_t resource_count;
    uint16_t process_id_count;
} et_spinlock_wrap_mapping_t;

static const et_spinlock_wrap_mapping_t spinlock_mappings[] = ET_CHIP_SPINLOCK_MAP_TABLE;

/**
 * @brief Resolve one stable SPINLOCK instance through the selected chip table.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @note This lookup has no hardware side effect.
 * @return Matching mapping or NULL when unsupported.
 */
static const et_spinlock_wrap_mapping_t *find_mapping(et_spinlock_id_t spinlock_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(spinlock_mappings) / sizeof(spinlock_mappings[0])); ++index)
    {
        if (spinlock_mappings[index].spinlock_id == spinlock_id)
        {
            return &spinlock_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Translate one stable SPINLOCK mode to the selected Driver value.
 * @param[in] mode Stable ONE_STEP or TWO_STEP mode.
 * @note The caller validates the mode before translation.
 * @return Selected Driver mode.
 */
static uint32_t mode_to_driver(uint8_t mode)
{
    return (mode == ET_SPINLOCK_WRAP_MODE_ONE_STEP) ? SPINLOCK_FAST_MODE : SPINLOCK_NORMAL_MODE;
}

/**
 * @brief Translate one selected Driver status into the stable Wrap namespace.
 * @param[in] status Selected Driver result.
 * @note This helper has no hardware side effect.
 * @return Stable Wrap status.
 */
static et_wrap_status_t status_from_driver(DRV_Status status)
{
    switch (status)
    {
        case DRV_OK:
        {
            return ET_WRAP_STATUS_OK;
        }

        case DRV_TIMEOUT:
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        case DRV_BUSY:
        {
            return ET_WRAP_STATUS_BUSY;
        }

        case DRV_PARAM_ERR:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        default:
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }
    }
}

/**
 * @brief Return normalized runtime capability facts for one mapped instance.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] capabilities Destination capability snapshot.
 * @note This reads compile-time chip facts only.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_capabilities_get(et_spinlock_id_t spinlock_id,
                                                   et_spinlock_wrap_capabilities_t *capabilities)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);

    if ((mapping == NULL) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    capabilities->features = mapping->features;
    capabilities->resource_count = mapping->resource_count;
    capabilities->process_id_count = mapping->process_id_count;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure only module enable and mode without implicit resource clear.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] enabled Normalized module enable state.
 * @param[in] mode Stable ONE_STEP or TWO_STEP mode.
 * @note This calls only the selected SPINLOCK Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_configure(et_spinlock_id_t spinlock_id, uint8_t enabled,
                                            uint8_t mode)
{
    if ((find_mapping(spinlock_id) == NULL) || (enabled > 1u) ||
        (mode > ET_SPINLOCK_WRAP_MODE_TWO_STEP))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(SPINLOCK_testConfigure(enabled, mode_to_driver(mode)));
}

/**
 * @brief Read normalized module enable and mode state.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] snapshot Destination configuration snapshot.
 * @note Reading does not modify resource ownership.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_config_snapshot_get(et_spinlock_id_t spinlock_id,
                                                      et_spinlock_wrap_config_snapshot_t *snapshot)
{
    uint32_t enabled;
    uint32_t mode;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testGetConfig(&enabled, &mode);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    snapshot->enabled = (uint8_t)enabled;
    snapshot->mode = (mode == SPINLOCK_FAST_MODE) ? ET_SPINLOCK_WRAP_MODE_ONE_STEP
                                                  : ET_SPINLOCK_WRAP_MODE_TWO_STEP;
    snapshot->reserved[0] = 0u;
    snapshot->reserved[1] = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return the hardware owner identity used by this execution entity.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] master_id Destination stable owner value.
 * @note This reads no SPINLOCK ownership register.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_local_master_id_get(et_spinlock_id_t spinlock_id,
                                                      uint16_t *master_id)
{
    uint32_t driver_master_id;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (master_id == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testGetCurrentMasterId(&driver_master_id);

    if ((status != DRV_OK) || (driver_master_id > UINT16_MAX))
    {
        return (status == DRV_OK) ? ET_WRAP_STATUS_IO_ERROR : status_from_driver(status);
    }

    *master_id = (uint16_t)driver_master_id;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Try once through the Driver's bounded acquire path.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] resource_id Target resource.
 * @param[in] process_id Two-step Process ID; ignored by one-step mode.
 * @note The active hardware mode selects the matching Driver operation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_resource_acquire_try(et_spinlock_id_t spinlock_id,
                                                       uint16_t resource_id, uint16_t process_id)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);
    et_spinlock_wrap_config_snapshot_t config;

    if ((mapping == NULL) || (resource_id >= mapping->resource_count) ||
        (process_id >= mapping->process_id_count) ||
        (et_spinlock_wrap_config_snapshot_get(spinlock_id, &config) != ET_WRAP_STATUS_OK) ||
        (config.enabled == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (config.mode == ET_SPINLOCK_WRAP_MODE_ONE_STEP)
    {
        return status_from_driver(SPINLOCK_fastAcquireTry(resource_id));
    }

    return status_from_driver(SPINLOCK_acquireTry(resource_id, process_id));
}

/**
 * @brief Release one resource through the operation matching the active mode.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] resource_id Target resource.
 * @param[in] process_id Two-step Process ID; ignored by one-step mode.
 * @note Release does not perform any global clear.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_resource_release(et_spinlock_id_t spinlock_id,
                                                   uint16_t resource_id, uint16_t process_id)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);
    et_spinlock_wrap_config_snapshot_t config;

    if ((mapping == NULL) || (resource_id >= mapping->resource_count) ||
        (process_id >= mapping->process_id_count) ||
        (et_spinlock_wrap_config_snapshot_get(spinlock_id, &config) != ET_WRAP_STATUS_OK))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (config.mode == ET_SPINLOCK_WRAP_MODE_ONE_STEP)
    {
        SPINLOCK_fastRelease(resource_id);
    }
    else
    {
        SPINLOCK_release(resource_id, process_id);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read both side-effect-free resource flag banks.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] snapshot Destination flag snapshot.
 * @note This operation cannot acquire a free resource.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_flag_snapshot_get(et_spinlock_id_t spinlock_id,
                                                    et_spinlock_wrap_flag_snapshot_t *snapshot)
{
    SPINLOCK_TestFlagSnapshot driver_snapshot;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testGetFlagSnapshot(&driver_snapshot);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    snapshot->flags_low = driver_snapshot.flagsLow;
    snapshot->flags_high = driver_snapshot.flagsHigh;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read safe normalized state for one resource.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] resource_id Target resource.
 * @param[out] snapshot Destination resource snapshot.
 * @note Owner information is read only when a side-effect-free flag proves Locked.
 * @return Stable Wrap status.
 */
et_wrap_status_t
et_spinlock_wrap_resource_snapshot_get(et_spinlock_id_t spinlock_id, uint16_t resource_id,
                                       et_spinlock_wrap_resource_snapshot_t *snapshot)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);
    SPINLOCK_TestResourceSnapshot driver_snapshot;
    DRV_Status status;

    if ((mapping == NULL) || (snapshot == NULL) || (resource_id >= mapping->resource_count))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testGetResourceSnapshot(resource_id, &driver_snapshot);

    if ((status != DRV_OK) || (driver_snapshot.masterId > UINT16_MAX) ||
        (driver_snapshot.processId > UINT16_MAX))
    {
        return (status == DRV_OK) ? ET_WRAP_STATUS_IO_ERROR : status_from_driver(status);
    }

    snapshot->locked = (uint8_t)driver_snapshot.locked;
    snapshot->owner_valid = (uint8_t)driver_snapshot.ownerValid;
    snapshot->process_id_valid = (uint8_t)driver_snapshot.processIdValid;
    snapshot->reserved = 0u;
    snapshot->master_id = (uint16_t)driver_snapshot.masterId;
    snapshot->process_id = (uint16_t)driver_snapshot.processId;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Release all resources owned by the current hardware Master.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @note This calls only the selected SPINLOCK Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_batch_release(et_spinlock_id_t spinlock_id)
{
    if (find_mapping(spinlock_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    SPINLOCK_batchReleaseAll();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Release all SPINLOCK resources for recovery and Case isolation.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @note This calls only the selected SPINLOCK Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_global_release(et_spinlock_id_t spinlock_id)
{
    if (find_mapping(spinlock_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    SPINLOCK_globalReleaseAll();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Probe clear-key protection without publishing chip authorization values.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] scope Stable batch or global scope.
 * @param[in] authorized Nonzero requests the selected Driver's valid key.
 * @note The selected Driver owns all chip-specific key values.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_clear_key_probe(et_spinlock_id_t spinlock_id, uint8_t scope,
                                                  uint8_t authorized)
{
    SPINLOCK_TestClearScope driver_scope;

    if ((find_mapping(spinlock_id) == NULL) || (scope > ET_SPINLOCK_WRAP_CLEAR_GLOBAL) ||
        (authorized > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    driver_scope = (scope == ET_SPINLOCK_WRAP_CLEAR_BATCH) ? SPINLOCK_TEST_CLEAR_BATCH
                                                           : SPINLOCK_TEST_CLEAR_GLOBAL;

    return status_from_driver(SPINLOCK_testClearProbe(driver_scope, authorized));
}

/**
 * @brief Read whether the independently deployed peer execution entity is ready.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] ready Nonzero when the selected Driver reports a ready peer.
 * @note This calls only the selected SPINLOCK Driver and publishes no chip address.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_peer_ready_get(et_spinlock_id_t spinlock_id, uint8_t *ready)
{
    uint32_t driver_ready;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (ready == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testPeerReady(&driver_ready);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    *ready = (uint8_t)driver_ready;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Boot Core1 on demand from the embedded peer firmware image.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @note The cross-IP bring-up lives in the SPINLOCK Chip Driver test extension;
 *       this Wrap only forwards the embedded image and maps the Driver status.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_peer_boot(et_spinlock_id_t spinlock_id)
{
    DRV_Status status;

    if (find_mapping(spinlock_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testBootPeer(g_core1_image, ET_CORE1_IMAGE_SIZE);

    return status_from_driver(status);
}

/**
 * @brief Read the peer execution entity's verified hardware Master ID.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] master_id Hardware Master ID reported by the selected Driver.
 * @note This calls only the selected SPINLOCK Driver and validates the stable field width.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_peer_master_id_get(et_spinlock_id_t spinlock_id,
                                                     uint16_t *master_id)
{
    uint32_t driver_master_id;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (master_id == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testGetPeerMasterId(&driver_master_id);

    if ((status != DRV_OK) || (driver_master_id > UINT16_MAX))
    {
        return (status == DRV_OK) ? ET_WRAP_STATUS_IO_ERROR : status_from_driver(status);
    }

    *master_id = (uint16_t)driver_master_id;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Submit one chip-independent asynchronous peer job.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] config Stable job type, lock mode, resource and bounded-loop configuration.
 * @note The selected Driver owns the peer transport and chip-specific execution mapping.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_peer_job_start(et_spinlock_id_t spinlock_id,
                                                 const et_spinlock_wrap_peer_job_config_t *config)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);
    SPINLOCK_TestPeerJobConfig driver_config;

    if ((mapping == NULL) || (config == NULL) ||
        (config->job_type > ET_SPINLOCK_WRAP_PEER_JOB_STRESS) ||
        (config->mode > ET_SPINLOCK_WRAP_MODE_TWO_STEP) ||
        (config->resource_id >= mapping->resource_count) ||
        (config->process_id >= mapping->process_id_count) || (config->reserved != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    driver_config.jobType = config->job_type;
    driver_config.mode = mode_to_driver(config->mode);
    driver_config.resourceId = config->resource_id;
    driver_config.processId = config->process_id;
    driver_config.loopCount = config->loop_count;

    return status_from_driver(SPINLOCK_testPeerJobStart(&driver_config));
}

/**
 * @brief Read stable state, result and progress for the current peer job.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] snapshot Chip-independent peer job state, result and progress counters.
 * @note This calls only the selected SPINLOCK Driver and validates all narrowed fields.
 * @return Stable Wrap status.
 */
et_wrap_status_t
et_spinlock_wrap_peer_job_snapshot_get(et_spinlock_id_t spinlock_id,
                                       et_spinlock_wrap_peer_job_snapshot_t *snapshot)
{
    SPINLOCK_TestPeerJobSnapshot driver_snapshot;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testPeerJobGetSnapshot(&driver_snapshot);

    if ((status != DRV_OK) || (driver_snapshot.state > UINT8_MAX) ||
        (driver_snapshot.result > UINT8_MAX) || (driver_snapshot.masterId > UINT16_MAX))
    {
        return (status == DRV_OK) ? ET_WRAP_STATUS_IO_ERROR : status_from_driver(status);
    }

    snapshot->state = (uint8_t)driver_snapshot.state;
    snapshot->result = (uint8_t)driver_snapshot.result;
    snapshot->master_id = (uint16_t)driver_snapshot.masterId;
    snapshot->enter_count = driver_snapshot.enterCount;
    snapshot->completed_count = driver_snapshot.completedCount;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Request release or abort for the active peer job.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] control Stable release or abort control value.
 * @note The selected Driver owns the active peer job state transition.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_peer_job_control(et_spinlock_id_t spinlock_id, uint8_t control)
{
    if ((find_mapping(spinlock_id) == NULL) ||
        ((control != ET_SPINLOCK_WRAP_PEER_CONTROL_RELEASE) &&
         (control != ET_SPINLOCK_WRAP_PEER_CONTROL_ABORT)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(SPINLOCK_testPeerJobControl((SPINLOCK_TestPeerControl)control));
}

/**
 * @brief Reset the shared stress counters owned by the selected Driver.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @note The selected Driver owns shared-memory placement and visibility barriers.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_shared_stress_reset(et_spinlock_id_t spinlock_id)
{
    if (find_mapping(spinlock_id) == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(SPINLOCK_testSharedStressReset());
}

/**
 * @brief Run the local execution entity's bounded shared-counter stress loop.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in] resource_id Stable Resource identifier used for mutual exclusion.
 * @param[in] loop_count Number of bounded critical-section iterations.
 * @param[out] completed_count Number of iterations completed by the local entity.
 * @note The selected Driver owns the critical section and shared-memory barriers.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_local_stress_run(et_spinlock_id_t spinlock_id,
                                                   uint16_t resource_id, uint32_t loop_count,
                                                   uint32_t *completed_count)
{
    const et_spinlock_wrap_mapping_t *mapping = find_mapping(spinlock_id);

    if ((mapping == NULL) || (resource_id >= mapping->resource_count) || (loop_count == 0u) ||
        (completed_count == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return status_from_driver(
        SPINLOCK_testLocalStressRun(resource_id, loop_count, completed_count));
}

/**
 * @brief Read the shared counter and critical-section violation facts.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[out] snapshot Chip-independent shared stress result snapshot.
 * @note The selected Driver owns shared-memory placement and visibility barriers.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_spinlock_wrap_shared_snapshot_get(et_spinlock_id_t spinlock_id,
                                                      et_spinlock_wrap_shared_snapshot_t *snapshot)
{
    SPINLOCK_TestSharedSnapshot driver_snapshot;
    DRV_Status status;

    if ((find_mapping(spinlock_id) == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = SPINLOCK_testSharedStressGetSnapshot(&driver_snapshot);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    snapshot->shared_counter = driver_snapshot.sharedCounter;
    snapshot->violation_count = driver_snapshot.violationCount;

    return ET_WRAP_STATUS_OK;
}
