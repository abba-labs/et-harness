/** @file et_crg_service.c @brief Decode CRG commands and call CRG Wrap only. */
#include "et_crg_service.h"

#include <stddef.h>
#include <string.h>

#include "et_crg_wrap.h"
#include "et_message.h"

/**
 * @brief Convert one CRG Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status CRG Wrap status returned by a chip-neutral hardware action.
 *
 * @note This helper translates status values only and does not access CRG hardware or Service state.
 *
 * @return Stable ET status corresponding to the supplied Wrap status.
 */
static uint16_t status_from_wrap(et_wrap_status_t status)
{
    switch (status)
    {
        case ET_WRAP_STATUS_OK:
        {
            return ET_STATUS_OK;
        }

        case ET_WRAP_STATUS_INVALID_ARGUMENT:
        case ET_WRAP_STATUS_STATE_ERROR:
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_BUSY:
        case ET_WRAP_STATUS_NO_RESOURCE:
        {
            return ET_STATUS_BUSY;
        }

        default:
        {
            return ET_STATUS_INTERNAL_ERROR;
        }
    }
}

/**
 * @brief Validate one fixed CRG request and execute exactly one CRG Wrap action.
 *
 * @param[in,out] context CRG Service context retained by the common router.
 * @param[in] command_id Stable CRG command identifier.
 * @param[in] request_body Fixed CRG command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Unused response-body storage supplied by the router.
 * @param[in] response_capacity Unused response-body capacity supplied by the router.
 * @param[out] response_length Number of response bytes produced by this command.
 *
 * @note CLOCK_SET and RESET directly change CRG hardware through CRG Wrap after fixed payload and
 *       reserved-byte validation. The Service owns no defaulting, polling loop or cross-IP action.
 *
 * @return Stable ET status describing payload validation, command selection or CRG Wrap execution.
 */
static uint16_t crg_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    (void)context;
    (void)response_body;
    (void)response_capacity;

    if ((response_length == NULL) || (request_length != ET_CRG_SERVICE_REQUEST_SIZE) ||
        (request_body == NULL))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 1: validate the fixed CRG request and reject reserved bytes. */

    /* Phase 2: dispatch exactly one CRG Owner action and encode readback when requested. */
    if (command_id == ET_CRG_COMMAND_CLOCK_SET)
    {
        if ((request_body[ET_CRG_SERVICE_VALUE_OFFSET] > 1u) ||
            (request_body[ET_CRG_SERVICE_RESERVED_OFFSET] != 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(
            et_crg_wrap_set_clock(request_body[ET_CRG_SERVICE_PERIPHERAL_OFFSET],
                                  request_body[ET_CRG_SERVICE_INSTANCE_OFFSET],
                                  request_body[ET_CRG_SERVICE_VALUE_OFFSET]));
    }

    if (command_id == ET_CRG_COMMAND_RESET)
    {
        if ((request_body[ET_CRG_SERVICE_VALUE_OFFSET] != 0u) ||
            (request_body[ET_CRG_SERVICE_RESERVED_OFFSET] != 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(et_crg_wrap_reset(request_body[ET_CRG_SERVICE_PERIPHERAL_OFFSET],
                                                  request_body[ET_CRG_SERVICE_INSTANCE_OFFSET]));
    }

    if (command_id == ET_CRG_COMMAND_WDG_CLOCK_SET)
    {
        if ((request_body[ET_CRG_SERVICE_WDG_SOURCE_OFFSET] > ET_CRG_WRAP_WDG_CLOCK_APB1) ||
            (request_body[ET_CRG_SERVICE_WDG_RESERVED_OFFSET] != 0u) ||
            ((request_body[ET_CRG_SERVICE_WDG_SOURCE_OFFSET] == ET_CRG_WRAP_WDG_CLOCK_HSOSC) &&
             (request_body[ET_CRG_SERVICE_WDG_DIVIDER_OFFSET] != 0u)))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(
            et_crg_wrap_set_wdg_clock(request_body[ET_CRG_SERVICE_WDG_ID_OFFSET],
                                      request_body[ET_CRG_SERVICE_WDG_SOURCE_OFFSET],
                                      request_body[ET_CRG_SERVICE_WDG_DIVIDER_OFFSET]));
    }

    if (command_id == ET_CRG_COMMAND_WDG_CLOCK_GET)
    {
        et_crg_wrap_wdg_clock_t clock;
        et_wrap_status_t wrap_status;

        if ((response_body == NULL) ||
            (response_capacity < ET_CRG_SERVICE_WDG_CLOCK_RESPONSE_SIZE) ||
            (request_body[ET_CRG_SERVICE_WDG_SOURCE_OFFSET] != 0u) ||
            (request_body[ET_CRG_SERVICE_WDG_DIVIDER_OFFSET] != 0u) ||
            (request_body[ET_CRG_SERVICE_WDG_RESERVED_OFFSET] != 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        wrap_status = et_crg_wrap_get_wdg_clock(request_body[ET_CRG_SERVICE_WDG_ID_OFFSET], &clock);

        if (wrap_status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(wrap_status);
        }

        response_body[ET_CRG_SERVICE_WDG_RESPONSE_SOURCE_OFFSET] = clock.source;
        response_body[ET_CRG_SERVICE_WDG_RESPONSE_DIVIDER_OFFSET] = clock.divider;
        (void)memset(&response_body[ET_CRG_SERVICE_WDG_RESPONSE_RESERVED_OFFSET], 0,
                     ET_CRG_SERVICE_WDG_RESPONSE_RESERVED_SIZE);
        *response_length = ET_CRG_SERVICE_WDG_CLOCK_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Initialize the singleton CRG Service descriptor without touching CRG hardware.
 *
 * @param[out] service CRG Service instance whose router descriptor is initialized.
 *
 * @note Initialization only clears Service-local state and binds the stable handler. Peripheral
 *       clocks and resets remain unchanged until a later PC command reaches crg_handle().
 *
 * @return 0 when the descriptor is initialized successfully.
 * @return -1 when service is NULL.
 */
int et_crg_service_init(et_crg_service_t *service)
{
    if (service == NULL)
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->descriptor.service_id = ET_CRG_SERVICE_ID;
    service->descriptor.instance_id = ET_CRG_SERVICE_INSTANCE_ID;
    service->descriptor.context = service;
    service->descriptor.handle = crg_handle;

    return 0;
}

/**
 * @brief Return the CRG descriptor registered with the common Service Router.
 *
 * @param[in] service Initialized CRG Service instance.
 *
 * @note The returned pointer aliases Service-owned storage and no hardware or Service state changes.
 *
 * @return Pointer to the immutable descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_crg_service_descriptor(const et_crg_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}
