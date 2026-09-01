#ifndef ET_RESOURCE_SERVICE_H
#define ET_RESOURCE_SERVICE_H

/**
 * @file et_resource_service.h
 * @brief Commands for bounded target-memory resources owned by the PC session.
 *
 * Resource Service only decodes requests and delegates allocation-free storage
 * operations to Resource Wrap.
 */

#include "et_service_router.h"

#define ET_RESOURCE_SERVICE_ID 0x0010u
#define ET_RESOURCE_SERVICE_INSTANCE_ID 0u
/** Frozen Resource Wire sizes. */
#define ET_RESOURCE_SERVICE_HANDLE_SIZE 4u
#define ET_RESOURCE_SERVICE_CREATE_REQUEST_SIZE 8u
#define ET_RESOURCE_SERVICE_CREATE_RESPONSE_SIZE 16u
#define ET_RESOURCE_SERVICE_WRITE_HEADER_SIZE 8u
#define ET_RESOURCE_SERVICE_READ_REQUEST_SIZE 12u
#define ET_RESOURCE_SERVICE_FILL_REQUEST_SIZE 13u
#define ET_RESOURCE_SERVICE_INFO_RESPONSE_SIZE 16u
/** Frozen Resource Wire field offsets. */
#define ET_RESOURCE_SERVICE_OFFSET_FIELD 4u
#define ET_RESOURCE_SERVICE_SIZE_FIELD 8u
#define ET_RESOURCE_SERVICE_DATA_FIELD 8u
#define ET_RESOURCE_SERVICE_FILL_VALUE_FIELD 12u

typedef enum
{
    ET_RESOURCE_COMMAND_RESET = 0x0001u,
    ET_RESOURCE_COMMAND_CREATE = 0x0002u,
    ET_RESOURCE_COMMAND_WRITE = 0x0003u,
    ET_RESOURCE_COMMAND_READ = 0x0004u,
    ET_RESOURCE_COMMAND_FILL = 0x0005u,
    ET_RESOURCE_COMMAND_INFO_GET = 0x0006u
} et_resource_command_t;

typedef struct
{
    et_service_descriptor_t descriptor;
} et_resource_service_t;

/** Initialize the single Resource Service descriptor. */
int et_resource_service_init(et_resource_service_t *service);
/** Return the descriptor of an initialized Resource Service. */
const et_service_descriptor_t *et_resource_service_descriptor(const et_resource_service_t *service);

#endif
