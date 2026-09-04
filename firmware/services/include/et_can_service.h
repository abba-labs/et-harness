#ifndef ET_CAN_SERVICE_H
#define ET_CAN_SERVICE_H

/** @file et_can_service.h @brief CAN command envelope; no chip or bus defaults. */
#include "et_service_router.h"
#include "et_can_wrap.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */

/** Public CAN Service identity, independent of controller and external box identity. */
#define ET_CAN_SERVICE_ID 0x010Cu
/** Request body has one instance byte followed by little-endian unsigned words. */
#define ET_CAN_REQUEST_PREFIX_BYTES 1u
#define ET_CAN_WIRE_WORD_BYTES 4u
#define ET_CAN_IDENTITY_WORDS 2u
#define ET_CAN_PHASE_WORDS 4u
#define ET_CAN_TIMING_WORDS 8u
#define ET_CAN_OPTIONS_WORDS 10u
#define ET_CAN_OPTION_LIMIT_WORDS 3u
/** Word positions in the limits response are independent from the options tuple. */
#define ET_CAN_LIMIT_TDC_OFFSET 0u
#define ET_CAN_LIMIT_TDC_FILTER 1u
#define ET_CAN_LIMIT_RAM_WATCHDOG 2u

/** Word positions of independent core controls, matching the public options contract. */
typedef enum
{
    ET_CAN_OPTION_FD = 0u,
    ET_CAN_OPTION_BRS = 1u,
    ET_CAN_OPTION_RETRY = 2u,
    ET_CAN_OPTION_TX_PAUSE = 3u,
    ET_CAN_OPTION_EDGE_FILTER = 4u,
    ET_CAN_OPTION_PROTOCOL_EXCEPTION = 5u,
    ET_CAN_OPTION_TDC = 6u,
    ET_CAN_OPTION_TDC_OFFSET = 7u,
    ET_CAN_OPTION_TDC_FILTER = 8u,
    ET_CAN_OPTION_RAM_WATCHDOG = 9u
} et_can_option_word_t;

/** Word positions within each timing phase; values are actual positive counts. */
typedef enum
{
    ET_CAN_TIMING_PRESCALER = 0u,
    ET_CAN_TIMING_SEGMENT1 = 1u,
    ET_CAN_TIMING_SEGMENT2 = 2u,
    ET_CAN_TIMING_SJW = 3u
} et_can_timing_word_t;

typedef enum
{
    ET_CAN_COMMAND_IDENTITY_GET = 0u,
    ET_CAN_COMMAND_INITIALIZING_SET = 1u,
    ET_CAN_COMMAND_INITIALIZING_GET = 2u,
    ET_CAN_COMMAND_TIMING_LIMITS_GET = 3u,
    ET_CAN_COMMAND_TIMING_SET = 4u,
    ET_CAN_COMMAND_TIMING_GET = 5u,
    ET_CAN_COMMAND_OPTIONS_SET = 6u,
    ET_CAN_COMMAND_OPTIONS_GET = 7u,
    ET_CAN_COMMAND_OPTION_LIMITS_GET = 8u,
    ET_CAN_COMMAND_COUNT
} et_can_command_t;

/** No cached configuration or test state; all reads return current hardware facts. */
typedef struct
{
    et_can_id_t can_id;
    et_service_descriptor_t descriptor;
} et_can_service_t;

int et_can_service_init(et_can_service_t *service, et_can_id_t can_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_can_service_descriptor(const et_can_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_can_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
