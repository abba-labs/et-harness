#ifndef ET_ETIM_WRAP_H
#define ET_ETIM_WRAP_H
/** @file et_etim_wrap.h @brief Chip-neutral ETIM channel operations and observations. */
#include <stdint.h>
#include "et_wrap_status.h"
typedef uint16_t et_etim_id_t;
typedef enum
{
    ET_ETIM_ENABLE_MODULE,
    ET_ETIM_ENABLE_TIMER,
    ET_ETIM_ENABLE_PWM,
    ET_ETIM_ENABLE_CAPTURE,
    ET_ETIM_ENABLE_CAPTURE_LOAD,
    ET_ETIM_ENABLE_COUNT
} et_etim_enable_t;
typedef enum
{
    ET_ETIM_IRQ_FAULT_ONE_SHOT = 1u << 0,
    ET_ETIM_IRQ_FAULT_CBC = 1u << 1,
    ET_ETIM_IRQ_FAULT_OVERFLOW = 1u << 2,
    ET_ETIM_IRQ_COMPARE_ERROR = 1u << 3,
    ET_ETIM_IRQ_COMPARE_A = 1u << 4,
    ET_ETIM_IRQ_COMPARE_B = 1u << 5,
    ET_ETIM_IRQ_PERIOD = 1u << 6,
    ET_ETIM_IRQ_COUNTER_OVERFLOW = 1u << 7,
    ET_ETIM_IRQ_CAPTURE_1 = 1u << 8,
    ET_ETIM_IRQ_CAPTURE_2 = 1u << 9,
    ET_ETIM_IRQ_CAPTURE_3 = 1u << 10,
    ET_ETIM_IRQ_CAPTURE_4 = 1u << 11
} et_etim_irq_t;
typedef struct
{
    uint32_t divider;
    uint64_t period_ticks;
} et_etim_timebase_t;
typedef struct
{
    uint32_t maximum_divider;
    uint64_t maximum_period_ticks;
    uint32_t maximum_count_polls;
    uint32_t irq_sources;
} et_etim_capabilities_t;
typedef struct
{
    uint32_t before, previous_latched, latched, live, polls;
} et_etim_count_observation_t;
typedef struct
{
    uint32_t enabled, masked, raw, status;
} et_etim_irq_snapshot_t;
et_wrap_status_t et_etim_wrap_capabilities_get(et_etim_id_t id, et_etim_capabilities_t *caps);
et_wrap_status_t et_etim_wrap_timebase_configure(et_etim_id_t id, const et_etim_timebase_t *config);
et_wrap_status_t et_etim_wrap_timebase_get(et_etim_id_t id, et_etim_timebase_t *config);
et_wrap_status_t et_etim_wrap_enable_set(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t enabled);
et_wrap_status_t et_etim_wrap_enable_get(et_etim_id_t id, et_etim_enable_t control,
                                         uint32_t *enabled);
et_wrap_status_t et_etim_wrap_count_get(et_etim_id_t id, uint32_t *live, uint32_t *latched);
et_wrap_status_t et_etim_wrap_count_latch(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation);
et_wrap_status_t et_etim_wrap_count_clear(et_etim_id_t id, uint32_t polls,
                                          et_etim_count_observation_t *observation);
et_wrap_status_t et_etim_wrap_irq_configure(et_etim_id_t id, uint32_t enabled, uint32_t masked);
et_wrap_status_t et_etim_wrap_irq_snapshot_get(et_etim_id_t id, et_etim_irq_snapshot_t *snapshot);
et_wrap_status_t et_etim_wrap_irq_force(et_etim_id_t id, uint32_t sources);
et_wrap_status_t et_etim_wrap_irq_clear(et_etim_id_t id, uint32_t sources);
#endif
