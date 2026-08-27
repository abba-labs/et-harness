#ifndef ET_CPU_SERVICE_H
#define ET_CPU_SERVICE_H

/** @file et_cpu_service.h @brief CPU-owner NMI Wire contract and event service. */

#include <stdint.h>

#include "et_cpu_wrap.h"
#include "et_service_factory.h"
#include "et_service_router.h"

#define ET_CPU_SERVICE_ID 0x0013u
#define ET_CPU_SERVICE_INSTANCE_ID 0u
#define ET_CPU_SERVICE_API_VERSION 1u
#define ET_CPU_SERVICE_WIRE_BYTE_MASK 0xffu

#define ET_CPU_SERVICE_CAPABILITIES_SIZE 8u
#define ET_CPU_SERVICE_CONFIG_SIZE 4u
#define ET_CPU_SERVICE_SNAPSHOT_SIZE 20u

#define ET_CPU_SERVICE_CAPS_API_VERSION_OFFSET 0u
#define ET_CPU_SERVICE_CAPS_STRUCT_SIZE_OFFSET 2u
#define ET_CPU_SERVICE_CAPS_NMI_SOURCE_MASK_OFFSET 4u

#define ET_CPU_SERVICE_CONFIG_MASK_OFFSET 0u
#define ET_CPU_SERVICE_CONFIG_RESERVED_OFFSET 1u
#define ET_CPU_SERVICE_CONFIG_RESERVED_SIZE 3u
#define ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_1_OFFSET 1u
#define ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_2_OFFSET 2u
#define ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_3_OFFSET 3u

#define ET_CPU_SERVICE_SNAPSHOT_RAW_OFFSET 0u
#define ET_CPU_SERVICE_SNAPSHOT_MASKED_OFFSET 4u
#define ET_CPU_SERVICE_SNAPSHOT_MASK_OFFSET 8u
#define ET_CPU_SERVICE_SNAPSHOT_STATUS_OFFSET 12u
#define ET_CPU_SERVICE_SNAPSHOT_EVENT_COUNT_OFFSET 16u

typedef enum
{
    ET_CPU_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_CPU_COMMAND_NMI_CONFIGURE = 0x0002u,
    ET_CPU_COMMAND_NMI_SNAPSHOT_GET = 0x0003u,
    ET_CPU_COMMAND_NMI_EVENT_CLEAR = 0x0004u
} et_cpu_command_t;

typedef struct
{
    et_cpu_id_t cpu_id;
    volatile uint32_t nmi_event_count;
    volatile uint32_t supported_nmi_source_mask;
    volatile uint8_t nmi_armed;
    et_service_descriptor_t descriptor;
} et_cpu_service_t;

/** Initialize one CPU-owner Service descriptor without changing CPU state. */
int et_cpu_service_init(et_cpu_service_t *service, et_cpu_id_t cpu_id);
/** Return the descriptor of an initialized CPU-owner Service. */
const et_service_descriptor_t *et_cpu_service_descriptor(const et_cpu_service_t *service);
/** Create one CPU-owner Service for the Application manifest. */
int et_cpu_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);

#endif
