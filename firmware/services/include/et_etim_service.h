#ifndef ET_ETIM_SERVICE_H
#define ET_ETIM_SERVICE_H

/** @file et_etim_service.h @brief ETIM basic command bodies and stateless channel service. */
#include <stdint.h>
#include "et_etim_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_service_router.h"

/* Stable ETIM Wire identity and byte sizes; owned by the public ETIM contract. */
#define ET_ETIM_SERVICE_ID 0x010Du
#define ET_ETIM_SERVICE_API_VERSION 1u
#define ET_ETIM_SERVICE_DETAIL_SIZE 4u
#define ET_ETIM_SERVICE_CAPABILITIES_SIZE 28u
#define ET_ETIM_SERVICE_TIMEBASE_SIZE 12u
#define ET_ETIM_SERVICE_TIMEBASE_RESPONSE_SIZE 16u
#define ET_ETIM_SERVICE_ENABLE_SIZE 4u
#define ET_ETIM_SERVICE_ENABLE_RESPONSE_SIZE 8u
#define ET_ETIM_SERVICE_COUNT_RESPONSE_SIZE 12u
#define ET_ETIM_SERVICE_OBSERVATION_SIZE 24u
#define ET_ETIM_SERVICE_IRQ_CONFIG_SIZE 8u
#define ET_ETIM_SERVICE_IRQ_SNAPSHOT_SIZE 20u
#define ET_ETIM_SERVICE_WORD_SIZE 4u

/* Request field offsets in bytes, independent of native structure alignment. */
#define ET_ETIM_SERVICE_PERIOD_OFFSET 4u
#define ET_ETIM_SERVICE_ENABLE_VALUE_OFFSET 1u
#define ET_ETIM_SERVICE_ENABLE_RESERVED_OFFSET 2u
#define ET_ETIM_SERVICE_MASKED_OFFSET 4u

/* Response field offsets in bytes, following the signed detail prefix. */
#define ET_ETIM_SERVICE_OBS_BEFORE_OFFSET 4u
#define ET_ETIM_SERVICE_OBS_PREVIOUS_OFFSET 8u
#define ET_ETIM_SERVICE_OBS_LATCHED_OFFSET 12u
#define ET_ETIM_SERVICE_OBS_LIVE_OFFSET 16u
#define ET_ETIM_SERVICE_OBS_POLLS_OFFSET 20u
#define ET_ETIM_SERVICE_COUNT_LIVE_OFFSET 4u
#define ET_ETIM_SERVICE_COUNT_LATCHED_OFFSET 8u
#define ET_ETIM_SERVICE_IRQ_ENABLED_OFFSET 4u
#define ET_ETIM_SERVICE_IRQ_MASKED_OFFSET 8u
#define ET_ETIM_SERVICE_IRQ_RAW_OFFSET 12u
#define ET_ETIM_SERVICE_IRQ_STATUS_OFFSET 16u

typedef enum
{
    ET_ETIM_COMMAND_CAPABILITIES_GET = 1u,
    ET_ETIM_COMMAND_TIMEBASE_CONFIGURE = 2u,
    ET_ETIM_COMMAND_TIMEBASE_GET = 3u,
    ET_ETIM_COMMAND_ENABLE_SET = 4u,
    ET_ETIM_COMMAND_ENABLE_GET = 5u,
    ET_ETIM_COMMAND_COUNT_GET = 6u,
    ET_ETIM_COMMAND_COUNT_LATCH = 7u,
    ET_ETIM_COMMAND_COUNT_CLEAR = 8u,
    ET_ETIM_COMMAND_IRQ_CONFIGURE = 9u,
    ET_ETIM_COMMAND_IRQ_SNAPSHOT_GET = 10u,
    ET_ETIM_COMMAND_IRQ_FORCE = 11u,
    ET_ETIM_COMMAND_IRQ_CLEAR = 12u
} et_etim_command_t;

typedef struct
{
    et_etim_id_t etim_id;
    et_service_descriptor_t descriptor;
} et_etim_service_t;

int et_etim_service_init(et_etim_service_t *service, et_etim_id_t etim_id,
                         et_irq_manager_t *irq_manager);
const et_service_descriptor_t *et_etim_service_descriptor(const et_etim_service_t *service);
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_etim_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */
#endif
