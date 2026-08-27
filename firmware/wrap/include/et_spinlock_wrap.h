#ifndef ET_SPINLOCK_WRAP_H
#define ET_SPINLOCK_WRAP_H

/**
 * @file et_spinlock_wrap.h
 * @brief Stable chip-independent SPINLOCK operations used by SPINLOCK Service.
 */

#include <stdint.h>

#include "et_wrap_status.h"

#define ET_SPINLOCK_WRAP_API_VERSION 1u

typedef uint16_t et_spinlock_id_t;

typedef enum
{
    ET_SPINLOCK_WRAP_MODE_ONE_STEP = 0u,
    ET_SPINLOCK_WRAP_MODE_TWO_STEP = 1u
} et_spinlock_wrap_mode_t;

typedef enum
{
    ET_SPINLOCK_WRAP_CLEAR_BATCH = 0u,
    ET_SPINLOCK_WRAP_CLEAR_GLOBAL = 1u
} et_spinlock_wrap_clear_scope_t;

#define ET_SPINLOCK_WRAP_CAP_ONE_STEP (1u << 0)
#define ET_SPINLOCK_WRAP_CAP_TWO_STEP (1u << 1)
#define ET_SPINLOCK_WRAP_CAP_BATCH_RELEASE (1u << 2)
#define ET_SPINLOCK_WRAP_CAP_GLOBAL_RELEASE (1u << 3)
#define ET_SPINLOCK_WRAP_CAP_CLEAR_KEY_PROTECTION (1u << 4)
#define ET_SPINLOCK_WRAP_CAP_PEER_JOB (1u << 5)
#define ET_SPINLOCK_WRAP_CAP_PEER_MASTER_MAPPING (1u << 6)
#define ET_SPINLOCK_WRAP_CAP_SHARED_STRESS (1u << 7)

typedef enum
{
    ET_SPINLOCK_WRAP_PEER_JOB_TRY_HOLD = 0u,
    ET_SPINLOCK_WRAP_PEER_JOB_BLOCKING_HOLD = 1u,
    ET_SPINLOCK_WRAP_PEER_JOB_RELEASE_ONCE = 2u,
    ET_SPINLOCK_WRAP_PEER_JOB_HOLD = 3u,
    ET_SPINLOCK_WRAP_PEER_JOB_STRESS = 4u
} et_spinlock_wrap_peer_job_type_t;

typedef enum
{
    ET_SPINLOCK_WRAP_PEER_JOB_IDLE = 0u,
    ET_SPINLOCK_WRAP_PEER_JOB_STARTED = 1u,
    ET_SPINLOCK_WRAP_PEER_JOB_WAITING = 2u,
    ET_SPINLOCK_WRAP_PEER_JOB_HOLDING = 3u,
    ET_SPINLOCK_WRAP_PEER_JOB_DONE = 4u,
    ET_SPINLOCK_WRAP_PEER_JOB_ABORTED = 5u,
    ET_SPINLOCK_WRAP_PEER_JOB_ERROR = 6u
} et_spinlock_wrap_peer_job_state_t;

typedef enum
{
    ET_SPINLOCK_WRAP_PEER_RESULT_NONE = 0u,
    ET_SPINLOCK_WRAP_PEER_RESULT_ACQUIRED = 1u,
    ET_SPINLOCK_WRAP_PEER_RESULT_BUSY = 2u,
    ET_SPINLOCK_WRAP_PEER_RESULT_RELEASED = 3u,
    ET_SPINLOCK_WRAP_PEER_RESULT_COMPLETED = 4u,
    ET_SPINLOCK_WRAP_PEER_RESULT_ABORTED = 5u,
    ET_SPINLOCK_WRAP_PEER_RESULT_ERROR = 6u
} et_spinlock_wrap_peer_result_t;

typedef enum
{
    ET_SPINLOCK_WRAP_PEER_CONTROL_RELEASE = 1u,
    ET_SPINLOCK_WRAP_PEER_CONTROL_ABORT = 2u
} et_spinlock_wrap_peer_control_t;

typedef struct
{
    uint32_t features;
    uint16_t resource_count;
    uint16_t process_id_count;
} et_spinlock_wrap_capabilities_t;

typedef struct
{
    uint8_t enabled;
    uint8_t mode;
    uint8_t reserved[2];
} et_spinlock_wrap_config_snapshot_t;

typedef struct
{
    uint32_t flags_low;
    uint32_t flags_high;
} et_spinlock_wrap_flag_snapshot_t;

typedef struct
{
    uint8_t locked;
    uint8_t owner_valid;
    uint8_t process_id_valid;
    uint8_t reserved;
    uint16_t master_id;
    uint16_t process_id;
} et_spinlock_wrap_resource_snapshot_t;

typedef struct
{
    uint8_t job_type;
    uint8_t mode;
    uint16_t resource_id;
    uint16_t process_id;
    uint16_t reserved;
    uint32_t loop_count;
} et_spinlock_wrap_peer_job_config_t;

typedef struct
{
    uint8_t state;
    uint8_t result;
    uint16_t master_id;
    uint32_t enter_count;
    uint32_t completed_count;
} et_spinlock_wrap_peer_job_snapshot_t;

typedef struct
{
    uint32_t shared_counter;
    uint32_t violation_count;
} et_spinlock_wrap_shared_snapshot_t;

et_wrap_status_t et_spinlock_wrap_capabilities_get(et_spinlock_id_t spinlock_id,
                                                   et_spinlock_wrap_capabilities_t *capabilities);
et_wrap_status_t et_spinlock_wrap_configure(et_spinlock_id_t spinlock_id, uint8_t enabled,
                                            uint8_t mode);
et_wrap_status_t et_spinlock_wrap_config_snapshot_get(et_spinlock_id_t spinlock_id,
                                                      et_spinlock_wrap_config_snapshot_t *snapshot);
et_wrap_status_t et_spinlock_wrap_local_master_id_get(et_spinlock_id_t spinlock_id,
                                                      uint16_t *master_id);
et_wrap_status_t et_spinlock_wrap_resource_acquire_try(et_spinlock_id_t spinlock_id,
                                                       uint16_t resource_id, uint16_t process_id);
et_wrap_status_t et_spinlock_wrap_resource_release(et_spinlock_id_t spinlock_id,
                                                   uint16_t resource_id, uint16_t process_id);
et_wrap_status_t et_spinlock_wrap_flag_snapshot_get(et_spinlock_id_t spinlock_id,
                                                    et_spinlock_wrap_flag_snapshot_t *snapshot);
et_wrap_status_t
et_spinlock_wrap_resource_snapshot_get(et_spinlock_id_t spinlock_id, uint16_t resource_id,
                                       et_spinlock_wrap_resource_snapshot_t *snapshot);
et_wrap_status_t et_spinlock_wrap_batch_release(et_spinlock_id_t spinlock_id);
et_wrap_status_t et_spinlock_wrap_global_release(et_spinlock_id_t spinlock_id);
et_wrap_status_t et_spinlock_wrap_clear_key_probe(et_spinlock_id_t spinlock_id, uint8_t scope,
                                                  uint8_t authorized);
et_wrap_status_t et_spinlock_wrap_peer_ready_get(et_spinlock_id_t spinlock_id, uint8_t *ready);
et_wrap_status_t et_spinlock_wrap_peer_master_id_get(et_spinlock_id_t spinlock_id,
                                                     uint16_t *master_id);
et_wrap_status_t et_spinlock_wrap_peer_job_start(et_spinlock_id_t spinlock_id,
                                                 const et_spinlock_wrap_peer_job_config_t *config);
et_wrap_status_t
et_spinlock_wrap_peer_job_snapshot_get(et_spinlock_id_t spinlock_id,
                                       et_spinlock_wrap_peer_job_snapshot_t *snapshot);
et_wrap_status_t et_spinlock_wrap_peer_job_control(et_spinlock_id_t spinlock_id, uint8_t control);
et_wrap_status_t et_spinlock_wrap_shared_stress_reset(et_spinlock_id_t spinlock_id);
et_wrap_status_t et_spinlock_wrap_local_stress_run(et_spinlock_id_t spinlock_id,
                                                   uint16_t resource_id, uint32_t loop_count,
                                                   uint32_t *completed_count);
et_wrap_status_t et_spinlock_wrap_shared_snapshot_get(et_spinlock_id_t spinlock_id,
                                                      et_spinlock_wrap_shared_snapshot_t *snapshot);

#endif
