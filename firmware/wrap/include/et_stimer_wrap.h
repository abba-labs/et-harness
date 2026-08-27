#ifndef ET_STIMER_WRAP_H
#define ET_STIMER_WRAP_H

/**
 * @file et_stimer_wrap.h
 * @brief Stable chip-independent system-timer operations used by STIMER Service.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_STIMER_WRAP_API_VERSION 1u
#define ET_STIMER_WRAP_CONFIG_RESERVED_WORDS 4u

typedef uint16_t et_stimer_id_t;

typedef enum
{
    ET_STIMER_WRAP_MODE_ONE_SHOT = 0u,
    ET_STIMER_WRAP_MODE_FREE_RUN = 1u
} et_stimer_wrap_mode_t;

typedef enum
{
    ET_STIMER_WRAP_LOAD_IMMEDIATE = 0u,
    ET_STIMER_WRAP_LOAD_SHADOW = 1u
} et_stimer_wrap_load_mode_t;

#define ET_STIMER_WRAP_FEATURE_START_STOP (1u << 0)
#define ET_STIMER_WRAP_FEATURE_PERIOD (1u << 1)
#define ET_STIMER_WRAP_FEATURE_PRESCALER (1u << 2)
#define ET_STIMER_WRAP_FEATURE_ONE_SHOT (1u << 3)
#define ET_STIMER_WRAP_FEATURE_FREE_RUN (1u << 4)
#define ET_STIMER_WRAP_FEATURE_CLEAR (1u << 5)
#define ET_STIMER_WRAP_FEATURE_PAUSE_RESUME (1u << 6)
#define ET_STIMER_WRAP_FEATURE_LOAD_MODE (1u << 7)
#define ET_STIMER_WRAP_FEATURE_LATCH (1u << 8)
#define ET_STIMER_WRAP_FEATURE_COMPARE (1u << 9)
#define ET_STIMER_WRAP_FEATURE_INTERRUPTS (1u << 10)
#define ET_STIMER_WRAP_FEATURE_STATUS (1u << 11)
#define ET_STIMER_WRAP_FEATURE_EVENT_PULSE_WIDTH (1u << 12)
#define ET_STIMER_WRAP_FEATURE_DMA_REQUEST (1u << 13)
#define ET_STIMER_WRAP_FEATURE_DEBUG_HALT (1u << 14)
#define ET_STIMER_WRAP_FEATURE_EMERGENCY_CAPTURE (1u << 15)

/* CPU Halt期间STIMER的稳定运行策略。 */
typedef enum
{
    ET_STIMER_WRAP_DEBUG_HALT_PAUSE = 0u,
    ET_STIMER_WRAP_DEBUG_HALT_RUN_FREE = 1u
} et_stimer_wrap_debug_halt_policy_t;

#define ET_STIMER_WRAP_IRQ_COMPARE0 (1u << 0)
#define ET_STIMER_WRAP_IRQ_COMPARE1 (1u << 1)
#define ET_STIMER_WRAP_IRQ_COMPARE2 (1u << 2)
#define ET_STIMER_WRAP_IRQ_COMPARE3 (1u << 3)
#define ET_STIMER_WRAP_IRQ_OVERFLOW (1u << 4)
#define ET_STIMER_WRAP_IRQ_ALL                                                                     \
    (ET_STIMER_WRAP_IRQ_COMPARE0 | ET_STIMER_WRAP_IRQ_COMPARE1 | ET_STIMER_WRAP_IRQ_COMPARE2 |     \
     ET_STIMER_WRAP_IRQ_COMPARE3 | ET_STIMER_WRAP_IRQ_OVERFLOW)

#define ET_STIMER_WRAP_STATUS_COMPARE0_VALUE_ERROR (1u << 0)
#define ET_STIMER_WRAP_STATUS_COMPARE1_VALUE_ERROR (1u << 1)
#define ET_STIMER_WRAP_STATUS_COMPARE2_VALUE_ERROR (1u << 2)
#define ET_STIMER_WRAP_STATUS_COMPARE3_VALUE_ERROR (1u << 3)
#define ET_STIMER_WRAP_STATUS_OVERFLOW (1u << 4)
#define ET_STIMER_WRAP_STATUS_COMPARE0_REPEAT (1u << 5)
#define ET_STIMER_WRAP_STATUS_COMPARE1_REPEAT (1u << 6)
#define ET_STIMER_WRAP_STATUS_COMPARE2_REPEAT (1u << 7)
#define ET_STIMER_WRAP_STATUS_COMPARE3_REPEAT (1u << 8)
#define ET_STIMER_WRAP_STATUS_ALL ((1u << 9) - 1u)

#define ET_STIMER_WRAP_COMPARE_CHANNEL_COUNT 4u
#define ET_STIMER_WRAP_MAX_PERIOD UINT32_MAX
#define ET_STIMER_WRAP_MAX_PRESCALER UINT16_MAX
#define ET_STIMER_WRAP_MIN_EVENT_PULSE_WIDTH_CYCLES 1u
#define ET_STIMER_WRAP_MAX_EVENT_PULSE_WIDTH_CYCLES 256u

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    et_stimer_id_t stimer_id;
    uint8_t mode;
    uint8_t load_mode;
    uint16_t prescaler_divider;
    uint32_t period_ticks;
    uint32_t reserved[ET_STIMER_WRAP_CONFIG_RESERVED_WORDS];
} et_stimer_wrap_config_t;

#define ET_STIMER_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_stimer_wrap_config_t, reserved))

typedef struct
{
    uint32_t features;
    uint32_t maximum_period_ticks;
    uint16_t maximum_prescaler_divider;
    uint8_t compare_channel_count;
    uint8_t instance_count;
    uint32_t irq_sources;
} et_stimer_wrap_capabilities_t;

typedef struct
{
    uint32_t live_count;
    uint32_t latched_count;
} et_stimer_wrap_count_snapshot_t;

typedef struct
{
    uint32_t raw;
    uint32_t status;
} et_stimer_wrap_irq_snapshot_t;

et_wrap_status_t et_stimer_wrap_capabilities_get(et_stimer_id_t stimer_id,
                                                 et_stimer_wrap_capabilities_t *capabilities);
et_wrap_status_t et_stimer_wrap_configure(et_stimer_id_t stimer_id,
                                          const et_stimer_wrap_config_t *config);
et_wrap_status_t et_stimer_wrap_debug_halt_policy_set(et_stimer_id_t stimer_id, uint8_t policy);
et_wrap_status_t et_stimer_wrap_start(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_stop(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_pause(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_resume(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_clear(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_reload(et_stimer_id_t stimer_id);
et_wrap_status_t et_stimer_wrap_live_count_get(et_stimer_id_t stimer_id, uint32_t *count);
et_wrap_status_t et_stimer_wrap_latched_count_get(et_stimer_id_t stimer_id, uint32_t *count);
et_wrap_status_t et_stimer_wrap_status_get(et_stimer_id_t stimer_id, uint32_t *status);
et_wrap_status_t et_stimer_wrap_compare_set(et_stimer_id_t stimer_id, uint8_t channel,
                                            uint32_t threshold);
et_wrap_status_t et_stimer_wrap_event_pulse_width_set(et_stimer_id_t stimer_id, uint32_t event,
                                                      uint16_t width_cycles);
et_wrap_status_t et_stimer_wrap_dma_request_select(et_stimer_id_t stimer_id, uint32_t event);
et_wrap_status_t et_stimer_wrap_emergency_capture_configure(et_stimer_id_t stimer_id,
                                                            uint8_t source_id,
                                                            uint8_t trigger_group);
et_wrap_status_t et_stimer_wrap_emergency_capture_get(et_stimer_id_t stimer_id, uint32_t *count);
et_wrap_status_t et_stimer_wrap_emergency_capture_clear(et_stimer_id_t stimer_id, uint8_t source_id,
                                                        uint8_t trigger_group);
et_wrap_status_t et_stimer_wrap_get_irq_route(et_stimer_id_t stimer_id, et_irq_route_t *route);
et_wrap_status_t et_stimer_wrap_irq_enable(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_disable(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_mask(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_unmask(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_force(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_clear(et_stimer_id_t stimer_id, uint32_t sources);
et_wrap_status_t et_stimer_wrap_irq_snapshot_get(et_stimer_id_t stimer_id,
                                                 et_stimer_wrap_irq_snapshot_t *snapshot);

#endif
