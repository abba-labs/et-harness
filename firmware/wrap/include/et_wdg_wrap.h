#ifndef ET_WDG_WRAP_H
#define ET_WDG_WRAP_H

/**
 * @file et_wdg_wrap.h
 * @brief Stable chip-independent watchdog operations used by WDG Service.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_WDG_WRAP_API_VERSION 1u
#define ET_WDG_WRAP_CONFIG_RESERVED_WORDS 4u

typedef uint16_t et_wdg_id_t;

typedef enum
{
    ET_WDG_WRAP_MODE_WINDOW = 0u,
    ET_WDG_WRAP_MODE_INDEPENDENT = 1u
} et_wdg_wrap_mode_t;

typedef enum
{
    ET_WDG_WRAP_WORK_ROUND1_IRQ_ROUND2_RESET = 0u,
    ET_WDG_WRAP_WORK_SAME_ROUND_IRQ_RESET = 1u
} et_wdg_wrap_work_mode_t;

#define ET_WDG_WRAP_FEATURE_ENABLE (1u << 0)
#define ET_WDG_WRAP_FEATURE_FEED (1u << 1)
#define ET_WDG_WRAP_FEATURE_WINDOW (1u << 2)
#define ET_WDG_WRAP_FEATURE_RESET_OUTPUT (1u << 3)
#define ET_WDG_WRAP_FEATURE_WORK_MODE (1u << 4)
#define ET_WDG_WRAP_FEATURE_HALT_PAUSE (1u << 5)
#define ET_WDG_WRAP_FEATURE_LOCK (1u << 6)
#define ET_WDG_WRAP_FEATURE_MODULE_RESET (1u << 7)
#define ET_WDG_WRAP_FEATURE_INTERRUPTS (1u << 8)
#define ET_WDG_WRAP_FEATURE_PERSISTENT_RECORDS (1u << 9)
#define ET_WDG_WRAP_FEATURE_CONFIG_READBACK (1u << 10)

#define ET_WDG_WRAP_IRQ_TIMEOUT (1u << 0)
#define ET_WDG_WRAP_IRQ_ALL ET_WDG_WRAP_IRQ_TIMEOUT

#define ET_WDG_WRAP_RECORD_RESET (1u << 0)
#define ET_WDG_WRAP_RECORD_INTERRUPT (1u << 1)
#define ET_WDG_WRAP_RECORD_ALL (ET_WDG_WRAP_RECORD_RESET | ET_WDG_WRAP_RECORD_INTERRUPT)

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    et_wdg_id_t wdg_id;
    uint8_t mode;
    uint8_t work_mode;
    uint8_t reset_enable;
    uint8_t halt_pause_enable;
    uint32_t reload_count;
    uint32_t window_low_count;
    uint32_t window_high_count;
    uint32_t reserved[ET_WDG_WRAP_CONFIG_RESERVED_WORDS];
} et_wdg_wrap_config_t;

#define ET_WDG_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_wdg_wrap_config_t, reserved))

typedef struct
{
    uint32_t features;
    uint32_t maximum_reload_count;
    uint32_t maximum_window_count;
    uint8_t mode_mask;
    uint8_t work_mode_mask;
    uint8_t irq_sources;
    uint8_t instance_count;
} et_wdg_wrap_capabilities_t;

typedef struct
{
    uint8_t enabled;
    uint8_t reserved[3];
    uint32_t counter;
} et_wdg_wrap_status_t;

typedef struct
{
    uint32_t raw;
    uint32_t status;
} et_wdg_wrap_irq_snapshot_t;

typedef struct
{
    uint8_t reset;
    uint8_t interrupt;
    uint8_t reserved[2];
} et_wdg_wrap_record_snapshot_t;

et_wrap_status_t et_wdg_wrap_capabilities_get(et_wdg_id_t wdg_id,
                                              et_wdg_wrap_capabilities_t *capabilities);
et_wrap_status_t et_wdg_wrap_unlock(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_lock(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_configure(et_wdg_id_t wdg_id, const et_wdg_wrap_config_t *config);
et_wrap_status_t et_wdg_wrap_config_get(et_wdg_id_t wdg_id, et_wdg_wrap_config_t *config);
et_wrap_status_t et_wdg_wrap_enable(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_disable(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_feed(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_status_get(et_wdg_id_t wdg_id, et_wdg_wrap_status_t *status);
et_wrap_status_t et_wdg_wrap_module_reset(et_wdg_id_t wdg_id);
et_wrap_status_t et_wdg_wrap_get_irq_route(et_wdg_id_t wdg_id, et_irq_route_t *route);
et_wrap_status_t et_wdg_wrap_irq_enable(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_disable(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_mask(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_unmask(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_force(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_clear(et_wdg_id_t wdg_id, uint32_t sources);
et_wrap_status_t et_wdg_wrap_irq_snapshot_get(et_wdg_id_t wdg_id,
                                              et_wdg_wrap_irq_snapshot_t *snapshot);
et_wrap_status_t et_wdg_wrap_record_get(et_wdg_id_t wdg_id,
                                        et_wdg_wrap_record_snapshot_t *snapshot);
et_wrap_status_t et_wdg_wrap_record_clear(et_wdg_id_t wdg_id, uint32_t records);

#endif
