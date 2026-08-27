#ifndef ET_WDG_SERVICE_H
#define ET_WDG_SERVICE_H

/**
 * @file et_wdg_service.h
 * @brief WDG Wire contract and bounded firmware runtime state.
 */

#include <stdint.h>

#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_service_router.h"
#include "et_wdg_wrap.h"

#define ET_WDG_SERVICE_ID 0x0105u
#define ET_WDG_SERVICE_API_VERSION 1u
#define ET_WDG_SERVICE_WIRE_BYTE_MASK 0xffu

#define ET_WDG_SERVICE_CAPABILITIES_SIZE 20u
#define ET_WDG_SERVICE_CONFIG_SIZE 16u
#define ET_WDG_SERVICE_STATUS_SIZE 8u
#define ET_WDG_SERVICE_MASK_SIZE 4u
#define ET_WDG_SERVICE_IRQ_SNAPSHOT_SIZE 20u
#define ET_WDG_SERVICE_RECORD_SIZE 4u

#define ET_WDG_SERVICE_CAPS_API_VERSION_OFFSET 0u
#define ET_WDG_SERVICE_CAPS_STRUCT_SIZE_OFFSET 2u
#define ET_WDG_SERVICE_CAPS_FEATURES_OFFSET 4u
#define ET_WDG_SERVICE_CAPS_MAX_RELOAD_OFFSET 8u
#define ET_WDG_SERVICE_CAPS_MAX_WINDOW_OFFSET 12u
#define ET_WDG_SERVICE_CAPS_MODE_MASK_OFFSET 16u
#define ET_WDG_SERVICE_CAPS_WORK_MODE_MASK_OFFSET 17u
#define ET_WDG_SERVICE_CAPS_IRQ_SOURCES_OFFSET 18u
#define ET_WDG_SERVICE_CAPS_INSTANCE_COUNT_OFFSET 19u

#define ET_WDG_SERVICE_CONFIG_RELOAD_OFFSET 0u
#define ET_WDG_SERVICE_CONFIG_WINDOW_LOW_OFFSET 4u
#define ET_WDG_SERVICE_CONFIG_WINDOW_HIGH_OFFSET 8u
#define ET_WDG_SERVICE_CONFIG_MODE_OFFSET 12u
#define ET_WDG_SERVICE_CONFIG_WORK_MODE_OFFSET 13u
#define ET_WDG_SERVICE_CONFIG_RESET_ENABLE_OFFSET 14u
#define ET_WDG_SERVICE_CONFIG_HALT_PAUSE_OFFSET 15u

#define ET_WDG_SERVICE_STATUS_ENABLED_OFFSET 0u
#define ET_WDG_SERVICE_STATUS_RESERVED_OFFSET 1u
#define ET_WDG_SERVICE_STATUS_RESERVED_SIZE 3u
#define ET_WDG_SERVICE_STATUS_COUNTER_OFFSET 4u

#define ET_WDG_SERVICE_IRQ_RAW_OFFSET 0u
#define ET_WDG_SERVICE_IRQ_STATUS_OFFSET 4u
#define ET_WDG_SERVICE_IRQ_LATCHED_OFFSET 8u
#define ET_WDG_SERVICE_IRQ_EVENT_COUNT_OFFSET 12u
#define ET_WDG_SERVICE_IRQ_LAST_RAW_OFFSET 16u

#define ET_WDG_SERVICE_RECORD_RESET_OFFSET 0u
#define ET_WDG_SERVICE_RECORD_INTERRUPT_OFFSET 1u
#define ET_WDG_SERVICE_RECORD_RESERVED_OFFSET 2u
#define ET_WDG_SERVICE_RECORD_RESERVED_SIZE 2u

typedef enum
{
    ET_WDG_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_WDG_COMMAND_UNLOCK = 0x0002u,
    ET_WDG_COMMAND_LOCK = 0x0003u,
    ET_WDG_COMMAND_CONFIGURE = 0x0004u,
    ET_WDG_COMMAND_CONFIG_GET = 0x0005u,
    ET_WDG_COMMAND_ENABLE = 0x0006u,
    ET_WDG_COMMAND_DISABLE = 0x0007u,
    ET_WDG_COMMAND_FEED = 0x0008u,
    ET_WDG_COMMAND_STATUS_GET = 0x0009u,
    ET_WDG_COMMAND_MODULE_RESET = 0x000au,
    ET_WDG_COMMAND_IRQ_ENABLE = 0x000bu,
    ET_WDG_COMMAND_IRQ_DISABLE = 0x000cu,
    ET_WDG_COMMAND_IRQ_MASK = 0x000du,
    ET_WDG_COMMAND_IRQ_UNMASK = 0x000eu,
    ET_WDG_COMMAND_IRQ_FORCE = 0x000fu,
    ET_WDG_COMMAND_IRQ_CLEAR = 0x0010u,
    ET_WDG_COMMAND_IRQ_SNAPSHOT_GET = 0x0011u,
    ET_WDG_COMMAND_RECORD_GET = 0x0012u,
    ET_WDG_COMMAND_RECORD_CLEAR = 0x0013u
} et_wdg_command_t;

typedef struct
{
    et_wdg_id_t wdg_id;
    uint8_t configured;
    uint8_t irq_bound;
    uint8_t irq_priority;
    uint8_t reserved8;
    uint32_t irq_enabled_sources;
    volatile uint32_t irq_event_count;
    volatile uint32_t irq_latched_sources;
    volatile uint32_t irq_last_raw;
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_route;
    et_service_descriptor_t descriptor;
} et_wdg_service_t;

int et_wdg_service_init(et_wdg_service_t *service, et_wdg_id_t wdg_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_wdg_service_descriptor(const et_wdg_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_wdg_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
