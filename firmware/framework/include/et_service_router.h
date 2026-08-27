#ifndef ET_SERVICE_ROUTER_H
#define ET_SERVICE_ROUTER_H

/**
 * @file et_service_router.h
 * @brief Static Service registry and message dispatch boundary.
 *
 * The router performs identity lookup and calls one Service handler. It does
 * not know IP semantics and does not evaluate test results.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_message.h"
#include "et_test_protocol_config.h"

typedef uint16_t (*et_service_handle_fn)(void *context, uint16_t command_id,
                                         const uint8_t *request_body, uint16_t request_length,
                                         uint8_t *response_body, uint16_t response_capacity,
                                         uint16_t *response_length);

/** Optional non-blocking background progress hook for one Service. */
typedef void (*et_service_poll_fn)(void *context);

/** Immutable Service identity plus its command and polling entry points. */
typedef struct
{
    uint16_t service_id;         /**< Stable service identity. */
    uint16_t instance_id;        /**< Stable logical IP instance. */
    void *context;               /**< Service-owned runtime state. */
    et_service_handle_fn handle; /**< Required synchronous command handler. */
    et_service_poll_fn poll;     /**< Optional bounded background handler. */
} et_service_descriptor_t;

typedef struct
{
    et_service_descriptor_t items[ET_FRAMEWORK_MAX_SERVICES];
    uint16_t count; /**< Number of valid descriptors in registration order. */
} et_service_router_t;

/** Reset the registry to empty. */
void et_service_router_init(et_service_router_t *router);

/** Register one unique service/instance pair by copying its descriptor. */
int et_service_register(et_service_router_t *router, const et_service_descriptor_t *descriptor);

/** Route one decoded request and return an et_status_t wire value. */
uint16_t et_service_dispatch(const et_service_router_t *router, const et_message_t *request,
                             uint8_t *response_body, uint16_t response_capacity,
                             uint16_t *response_length);

/** Call each registered non-NULL Service poll hook once. */
void et_service_router_poll(et_service_router_t *router);
/** Roll registration count back to a prior checkpoint. */
int et_service_router_truncate(et_service_router_t *router, uint16_t count);

/** Return the number of registered descriptors. */
uint16_t et_service_count(const et_service_router_t *router);

/** Return one descriptor by registration index, or NULL when out of range. */
const et_service_descriptor_t *et_service_at(const et_service_router_t *router, uint16_t index);

#endif
