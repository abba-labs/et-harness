#include "et_service_router.h"

/**
 * @file et_service_router.c
 * @brief Bounded registry lookup and Service command dispatch.
 */

#include <stddef.h>
#include <string.h>

/**
 * @brief Find one registered Service descriptor by stable Service and instance identity.
 *
 * @param[in] router Service router whose bounded registry is searched.
 * @param[in] service_id Stable Service identifier.
 * @param[in] instance_id Stable logical Service instance identifier.
 *
 * @note This helper performs a read-only linear lookup over the small static registry. It does not
 *       call any Service handler or mutate registration state.
 *
 * @return Pointer to the matching descriptor, or NULL when no matching registration exists.
 */
static const et_service_descriptor_t *find_service(const et_service_router_t *router,
                                                   uint16_t service_id, uint16_t instance_id)
{
    uint16_t index;

    if (router == NULL)
    {
        return NULL;
    }

    for (index = 0u; index < router->count; ++index)
    {
        if ((router->items[index].service_id == service_id) &&
            (router->items[index].instance_id == instance_id))
        {
            return &router->items[index];
        }
    }

    return NULL;
}

/**
 * @brief Reset a Service router to an empty bounded registry.
 *
 * @param[out] router Service router whose visible descriptor count is reset.
 *
 * @note Only the active count is cleared because stale array elements are unreachable until a later
 *       registration overwrites them. No Service cleanup callback is invoked.
 */
void et_service_router_init(et_service_router_t *router)
{
    if (router != NULL)
    {
        router->count = 0u;
    }
}

/**
 * @brief Register one unique Service descriptor in bounded startup order.
 *
 * @param[in,out] router Service router that owns the copied descriptor.
 * @param[in] descriptor Fully initialized descriptor to register.
 *
 * @note Registration copies descriptor metadata only and never initializes hardware. Duplicate
 *       Service/instance identities are rejected so dispatch remains deterministic.
 *
 * @return 0 when the descriptor is registered successfully.
 * @return -1 when the descriptor is invalid, duplicate or the static registry is full.
 */
int et_service_register(et_service_router_t *router, const et_service_descriptor_t *descriptor)
{
    /* Duplicate service/instance identities are rejected at startup. */
    if ((router == NULL) || (descriptor == NULL) || (descriptor->handle == NULL) ||
        (router->count >= ET_FRAMEWORK_MAX_SERVICES) ||
        (find_service(router, descriptor->service_id, descriptor->instance_id) != NULL))
    {
        return -1;
    }

    router->items[router->count++] = *descriptor;

    return 0;
}

/**
 * @brief Dispatch one decoded request to the matching registered Service handler.
 *
 * @param[in] router Service router used for descriptor lookup.
 * @param[in] request Decoded Service request with stable Service/instance identity.
 * @param[out] response_body Caller-owned buffer for the Service response body.
 * @param[in] response_capacity Available bytes in response_body.
 * @param[out] response_length Number of response-body bytes produced by the Service handler.
 *
 * @note The router performs identity lookup and bounded handoff only. Command semantics, hardware
 *       execution and response contents remain owned by the selected Service.
 *
 * @return Stable ET status returned by validation, lookup or the selected Service handler.
 */
uint16_t et_service_dispatch(const et_service_router_t *router, const et_message_t *request,
                             uint8_t *response_body, uint16_t response_capacity,
                             uint16_t *response_length)
{
    const et_service_descriptor_t *service;

    if ((router == NULL) || (request == NULL) || (response_body == NULL) ||
        (response_length == NULL) || (request->status != ET_STATUS_OK))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;
    service = find_service(router, request->service_id, request->instance_id);

    if (service == NULL)
    {
        return ET_STATUS_INVALID_SERVICE;
    }

    return service->handle(service->context, request->command_id, request->body,
                           request->body_length, response_body, response_capacity, response_length);
}

/**
 * @brief Invoke each registered Service's optional deferred polling hook once.
 *
 * @param[in,out] router Service router whose descriptors are polled in registration order.
 *
 * @note Poll callbacks execute in cooperative thread context and may advance Service-local async
 *       state. The router does not interpret returned hardware facts or perform final assertions.
 */
void et_service_router_poll(et_service_router_t *router)
{
    uint16_t index;

    if (router == NULL)
    {
        return;
    }

    for (index = 0u; index < router->count; ++index)
    {
        if (router->items[index].poll != NULL)
        {
            router->items[index].poll(router->items[index].context);
        }
    }
}

/**
 * @brief Roll back the registry to a previously recorded descriptor count.
 *
 * @param[in,out] router Service router whose tail registrations are discarded.
 * @param[in] count Previous valid descriptor count to restore.
 *
 * @note Rolled-back descriptor storage is zeroed so stale callbacks or contexts cannot later be
 *       inspected. This is registration rollback only; it does not deinitialize Service hardware.
 *
 * @return 0 when the registry is truncated successfully.
 * @return -1 when router is NULL or count is greater than the current registry count.
 */
int et_service_router_truncate(et_service_router_t *router, uint16_t count)
{
    if ((router == NULL) || (count > router->count))
    {
        return -1;
    }

    /* Clear rolled-back descriptors so stale callbacks cannot be inspected. */
    if (count < router->count)
    {
        (void)memset(&router->items[count], 0,
                     (size_t)(router->count - count) * sizeof(router->items[0]));
    }

    router->count = count;

    return 0;
}

/**
 * @brief Return the number of currently registered Service descriptors.
 *
 * @param[in] router Service router whose registry count is queried.
 *
 * @note This is a read-only registry query and does not invoke any Service callback.
 *
 * @return Current descriptor count, or zero when router is NULL.
 */
uint16_t et_service_count(const et_service_router_t *router)
{
    return (router == NULL) ? 0u : router->count;
}

/**
 * @brief Return one Service descriptor by stable registration order.
 *
 * @param[in] router Service router that owns the descriptor array.
 * @param[in] index Zero-based registry index to inspect.
 *
 * @note The returned pointer aliases router-owned storage and remains valid only while the
 *       registration at that index remains active.
 *
 * @return Pointer to the requested descriptor, or NULL when router/index is invalid.
 */
const et_service_descriptor_t *et_service_at(const et_service_router_t *router, uint16_t index)
{
    if ((router == NULL) || (index >= router->count))
    {
        return NULL;
    }

    return &router->items[index];
}
