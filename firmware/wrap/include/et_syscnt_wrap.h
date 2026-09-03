#ifndef ET_SYSCNT_WRAP_H
#define ET_SYSCNT_WRAP_H

/** @file et_syscnt_wrap.h @brief Chip-neutral atomic system counter operations. */
#include <stdint.h>
#include "et_wrap_status.h"

typedef uint16_t et_syscnt_id_t;

/** Action capability bits; no Case policy or test verdict is encoded here. */
typedef enum
{
    ET_SYSCNT_CAP_ENABLE = 1u << 0,
    ET_SYSCNT_CAP_LOAD = 1u << 1,
    ET_SYSCNT_CAP_DUAL_VIEW = 1u << 2,
    ET_SYSCNT_CAP_FREQUENCY_ID = 1u << 3,
    ET_SYSCNT_CAP_HALT = 1u << 4,
    ET_SYSCNT_CAP_REFERENCE = 1u << 5
} et_syscnt_capability_t;

typedef enum
{
    ET_SYSCNT_VIEW_CONTROL = 0u,
    ET_SYSCNT_VIEW_READ = 1u
} et_syscnt_view_t;

typedef enum
{
    ET_SYSCNT_RUN_FREE = 0u,
    ET_SYSCNT_PAUSE = 1u
} et_syscnt_halt_policy_t;

typedef struct
{
    uint32_t feature_flags;
    uint8_t counter_bits;
    uint8_t read_view_mask;
    uint8_t reference_bits;
    uint8_t counter_word_bits;
} et_syscnt_capabilities_t;

typedef struct
{
    uint8_t enabled;
    uint8_t halt_policy;
    uint8_t debug_halted;
    uint32_t frequency_id_hz;
} et_syscnt_control_t;

typedef struct
{
    uint64_t reference_before;
    uint64_t count;
    uint64_t reference_after;
} et_syscnt_reference_sample_t;

et_wrap_status_t et_syscnt_wrap_get_capabilities(et_syscnt_id_t id, et_syscnt_capabilities_t *caps);
et_wrap_status_t et_syscnt_wrap_set_enabled(et_syscnt_id_t id, uint8_t enabled);
et_wrap_status_t et_syscnt_wrap_load_value(et_syscnt_id_t id, uint64_t value);
et_wrap_status_t et_syscnt_wrap_get_count(et_syscnt_id_t id, et_syscnt_view_t view,
                                          uint64_t *count);
et_wrap_status_t et_syscnt_wrap_get_control(et_syscnt_id_t id, et_syscnt_control_t *control);
et_wrap_status_t et_syscnt_wrap_set_halt_policy(et_syscnt_id_t id, et_syscnt_halt_policy_t policy);
et_wrap_status_t et_syscnt_wrap_set_frequency_id(et_syscnt_id_t id, uint32_t frequency_hz);
et_wrap_status_t et_syscnt_wrap_set_reference_enabled(et_syscnt_id_t id, uint8_t enabled);
et_wrap_status_t et_syscnt_wrap_sample_reference(et_syscnt_id_t id,
                                                 et_syscnt_reference_sample_t *sample);

#endif
