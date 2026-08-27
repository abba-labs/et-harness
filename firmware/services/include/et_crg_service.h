#ifndef ET_CRG_SERVICE_H
#define ET_CRG_SERVICE_H

/** @file et_crg_service.h @brief CRG command contract. */

#include "et_service_router.h"

#define ET_CRG_SERVICE_ID 0x0012u
#define ET_CRG_SERVICE_INSTANCE_ID 0u
/** CLOCK_SET/RESET request: peripheral, instance, value/reserved, reserved. */
#define ET_CRG_SERVICE_REQUEST_SIZE 4u
#define ET_CRG_SERVICE_PERIPHERAL_OFFSET 0u
#define ET_CRG_SERVICE_INSTANCE_OFFSET 1u
#define ET_CRG_SERVICE_VALUE_OFFSET 2u
#define ET_CRG_SERVICE_RESERVED_OFFSET 3u

/* WDG clock request/response uses: logical WDG ID, source, divider, reserved. */
#define ET_CRG_SERVICE_WDG_CLOCK_REQUEST_SIZE 4u
#define ET_CRG_SERVICE_WDG_CLOCK_RESPONSE_SIZE 4u
#define ET_CRG_SERVICE_WDG_ID_OFFSET 0u
#define ET_CRG_SERVICE_WDG_SOURCE_OFFSET 1u
#define ET_CRG_SERVICE_WDG_DIVIDER_OFFSET 2u
#define ET_CRG_SERVICE_WDG_RESERVED_OFFSET 3u
#define ET_CRG_SERVICE_WDG_RESPONSE_SOURCE_OFFSET 0u
#define ET_CRG_SERVICE_WDG_RESPONSE_DIVIDER_OFFSET 1u
#define ET_CRG_SERVICE_WDG_RESPONSE_RESERVED_OFFSET 2u
#define ET_CRG_SERVICE_WDG_RESPONSE_RESERVED_SIZE 2u

typedef enum
{
    ET_CRG_COMMAND_CLOCK_SET = 0x0001u,
    ET_CRG_COMMAND_RESET = 0x0002u,
    ET_CRG_COMMAND_WDG_CLOCK_SET = 0x0003u,
    ET_CRG_COMMAND_WDG_CLOCK_GET = 0x0004u
} et_crg_command_t;

typedef struct
{
    et_service_descriptor_t descriptor;
} et_crg_service_t;

/** Initialize the single CRG command Service descriptor. */
int et_crg_service_init(et_crg_service_t *service);
/** Return the descriptor of an initialized CRG Service. */
const et_service_descriptor_t *et_crg_service_descriptor(const et_crg_service_t *service);

#endif
