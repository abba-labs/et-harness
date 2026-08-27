/** @file et_sysctrl_service.c @brief Decode SYSCTRL commands and call SYSCTRL Wrap only. */
#include "et_sysctrl_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"
#include "et_sysctrl_wrap.h"

/**
 * @brief Convert one SYSCTRL Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status SYSCTRL Wrap status returned by a chip-neutral hardware action.
 *
 * @note This helper translates status values only and does not access SYSCTRL hardware or Service state.
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
 * @brief Decode the V2 DMA request body and configure one trusted DMAMUX route.
 *
 * @param[in] request_body Fixed SYSCTRL V2 request body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note Successful validation changes DMAMUX routing hardware through SYSCTRL Wrap. The Service does
 *       not infer controller/interface defaults or perform any DMA transfer itself.
 *
 * @return Stable ET status describing payload validation or SYSCTRL Wrap execution.
 */
static uint16_t configure_dma_request_v2(const uint8_t *request_body, uint16_t request_length)
{
    if ((request_body == NULL) || (request_length != ET_SYSCTRL_DMA_REQUEST_V2_SIZE) ||
        (request_body[ET_SYSCTRL_DMA_RESERVED_OFFSET] != 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    return status_from_wrap(
        et_sysctrl_wrap_configure_dma_request(request_body[ET_SYSCTRL_DMA_CONTROLLER_OFFSET],
                                              request_body[ET_SYSCTRL_DMA_INTERFACE_OFFSET],
                                              request_body[ET_SYSCTRL_DMA_REQUEST_ID_OFFSET]));
}

/**
 * @brief Decode the DMA release body and release one trusted DMAMUX interface.
 *
 * @param[in] request_body Fixed SYSCTRL release request body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note Both reserved/request-id bytes are required to remain zero before SYSCTRL Wrap is allowed to
 *       modify DMAMUX hardware ownership.
 *
 * @return Stable ET status describing payload validation or SYSCTRL Wrap execution.
 */
static uint16_t release_dma_request(const uint8_t *request_body, uint16_t request_length)
{
    if ((request_body == NULL) || (request_length != ET_SYSCTRL_DMA_REQUEST_RELEASE_SIZE) ||
        (request_body[ET_SYSCTRL_DMA_REQUEST_ID_OFFSET] != 0u) ||
        (request_body[ET_SYSCTRL_DMA_RESERVED_OFFSET] != 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    return status_from_wrap(
        et_sysctrl_wrap_release_dma_request(request_body[ET_SYSCTRL_DMA_CONTROLLER_OFFSET],
                                            request_body[ET_SYSCTRL_DMA_INTERFACE_OFFSET]));
}

/**
 * @brief Dispatch one published SYSCTRL command without introducing cross-IP policy.
 *
 * @param[in,out] context SYSCTRL Service context retained by the common router.
 * @param[in] command_id Stable SYSCTRL command identifier.
 * @param[in] request_body Command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Unused response-body storage supplied by the router.
 * @param[in] response_capacity Unused response-body capacity supplied by the router.
 * @param[out] response_length Number of response bytes produced by this command.
 *
 * @note V1 DMA route configuration remains explicitly NOT_SUPPORTED. V2 configure/release commands
 *       may change DMAMUX hardware only through SYSCTRL Wrap; the Service never executes DMA actions.
 *
 * @return Stable ET status for request validation, command selection or SYSCTRL Wrap execution.
 */
static uint16_t sysctrl_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                               uint16_t request_length, uint8_t *response_body,
                               uint16_t response_capacity, uint16_t *response_length)
{
    (void)context;
    (void)response_body;
    (void)response_capacity;

    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (command_id == ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE)
    {
        if ((request_body == NULL) || (request_length != ET_SYSCTRL_DMA_REQUEST_V1_SIZE))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return ET_STATUS_NOT_SUPPORTED;
    }

    if (command_id == ET_SYSCTRL_COMMAND_DMA_REQUEST_RELEASE)
    {
        return release_dma_request(request_body, request_length);
    }

    if (command_id == ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE_V2)
    {
        return configure_dma_request_v2(request_body, request_length);
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Initialize the singleton SYSCTRL Service descriptor without touching hardware.
 *
 * @param[out] service SYSCTRL Service instance whose router descriptor is initialized.
 *
 * @note Initialization only clears Service-local state and binds the stable handler. DMAMUX state is
 *       unchanged until a later validated PC command reaches sysctrl_handle().
 *
 * @return 0 when the descriptor is initialized successfully.
 * @return -1 when service is NULL.
 */
int et_sysctrl_service_init(et_sysctrl_service_t *service)
{
    if (service == NULL)
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->descriptor.service_id = ET_SYSCTRL_SERVICE_ID;
    service->descriptor.instance_id = ET_SYSCTRL_SERVICE_INSTANCE_ID;
    service->descriptor.context = service;
    service->descriptor.handle = sysctrl_handle;

    return 0;
}

/**
 * @brief Return the SYSCTRL descriptor registered with the common Service Router.
 *
 * @param[in] service Initialized SYSCTRL Service instance.
 *
 * @note The returned pointer aliases Service-owned storage and no hardware or Service state changes.
 *
 * @return Pointer to the immutable descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_sysctrl_service_descriptor(const et_sysctrl_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}
