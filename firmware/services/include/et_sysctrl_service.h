#ifndef ET_SYSCTRL_SERVICE_H
#define ET_SYSCTRL_SERVICE_H

/** @file et_sysctrl_service.h @brief SYSCTRL command contract. */

#include "et_service_router.h"

#define ET_SYSCTRL_SERVICE_ID 0x0011u
#define ET_SYSCTRL_SERVICE_INSTANCE_ID 0u
#define ET_SYSCTRL_DMA_REQUEST_V1_SIZE 12u
#define ET_SYSCTRL_DMA_REQUEST_RELEASE_SIZE 4u
#define ET_SYSCTRL_DMA_REQUEST_V2_SIZE 4u
/** V2/RELEASE request byte offsets shared with the PC Wire codec. */
#define ET_SYSCTRL_DMA_CONTROLLER_OFFSET 0u
#define ET_SYSCTRL_DMA_INTERFACE_OFFSET 1u
#define ET_SYSCTRL_DMA_REQUEST_ID_OFFSET 2u
#define ET_SYSCTRL_DMA_RESERVED_OFFSET 3u

/** Counter routing request is instance, value, two zero reserved bytes. */
#define ET_SYSCTRL_SYSCNT_REQUEST_SIZE 4u
#define ET_SYSCTRL_SYSCNT_INSTANCE_OFFSET 0u
#define ET_SYSCTRL_SYSCNT_VALUE_OFFSET 1u
#define ET_SYSCTRL_SYSCNT_RESERVED0_OFFSET 2u
#define ET_SYSCTRL_SYSCNT_RESERVED1_OFFSET 3u
/** GET response is source, halt_enabled, two zero reserved bytes. */
#define ET_SYSCTRL_SYSCNT_RESPONSE_SIZE 4u
#define ET_SYSCTRL_SYSCNT_SOURCE_OFFSET 0u
#define ET_SYSCTRL_SYSCNT_HALT_OFFSET 1u

typedef enum
{
    /* Deprecated: Endpoint/Instance/Address semantics are no longer executed. */
    ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE = 0x0001u,
    ET_SYSCTRL_COMMAND_DMA_REQUEST_RELEASE = 0x0002u,
    ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE_V2 = 0x0003u,
    ET_SYSCTRL_COMMAND_SYSCNT_SOURCE_SET = 0x0004u,
    ET_SYSCTRL_COMMAND_SYSCNT_HALT_SET = 0x0005u,
    ET_SYSCTRL_COMMAND_SYSCNT_ROUTING_GET = 0x0006u
} et_sysctrl_command_t;

typedef struct
{
    et_service_descriptor_t descriptor;
} et_sysctrl_service_t;

/** Initialize the single SYSCTRL command Service descriptor. */
int et_sysctrl_service_init(et_sysctrl_service_t *service);
/** Return the descriptor of an initialized SYSCTRL Service. */
const et_service_descriptor_t *et_sysctrl_service_descriptor(const et_sysctrl_service_t *service);

#endif
