#include "et_resource_service.h"

/**
 * @file et_resource_service.c
 * @brief Decode bounded resource commands and call Resource Wrap only.
 */

#include <stddef.h>
#include <string.h>

#include "et_message.h"
#include "et_resource_wrap.h"

/**
 * @brief Decode one unaligned little-endian 32-bit Resource Wire field.
 *
 * @param[in] data Four bytes containing the encoded value.
 *
 * @note This helper only reads caller-owned request memory and does not validate Resource handles.
 *
 * @return Decoded 32-bit value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian Resource Wire field.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned response memory and does not change Resource state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Encode one 64-bit value into an unaligned little-endian Resource Wire field.
 *
 * @param[out] data Eight-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note Encoding is composed from two canonical 32-bit writes and does not dereference value as an
 *       address or perform any Resource operation.
 */
static void write_u64(uint8_t *data, uint64_t value)
{
    write_u32(data, (uint32_t)value);
    write_u32(&data[sizeof(uint32_t)], (uint32_t)(value >> (sizeof(uint32_t) * 8u)));
}

/**
 * @brief Convert one Resource Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status Resource Wrap status returned by a bounded Resource operation.
 *
 * @note This helper translates status values only and does not access memory pools or Resource state.
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
 * @brief Decode one Resource command and perform exactly one bounded Resource Wrap action.
 *
 * @param[in,out] context Resource Service context retained by the common router.
 * @param[in] command_id Stable Resource command identifier.
 * @param[in] request_body Resource command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response-body storage.
 * @param[in] response_capacity Available response-body bytes.
 * @param[out] response_length Number of response-body bytes produced.
 *
 * @note CREATE owns one explicit rollback: if a new handle cannot be resolved after creation, the
 *       handle is destroyed before failure is returned. All other branches perform one Resource Wrap
 *       action and never execute Feature IP behavior or final test assertions.
 *
 * @return Stable ET status for payload validation, command selection or Resource Wrap execution.
 */
static uint16_t resource_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                                uint16_t request_length, uint8_t *response_body,
                                uint16_t response_capacity, uint16_t *response_length)
{
    et_resource_handle_t handle;
    et_resource_wrap_info_t info;
    et_wrap_status_t status;
    void *address;
    uint32_t size;

    (void)context;

    /* Phase 1: Validate router-owned response storage and the optional request-body pointer. */
    if ((response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 2: Validate each command's fixed Wire contract before invoking Resource Wrap. */
    switch (command_id)
    {
        case ET_RESOURCE_COMMAND_RESET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_resource_wrap_reset());
        }

        case ET_RESOURCE_COMMAND_CREATE:
        {
            if ((request_length != ET_RESOURCE_SERVICE_CREATE_REQUEST_SIZE) ||
                (response_capacity < ET_RESOURCE_SERVICE_CREATE_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_resource_wrap_create(
                read_u32(request_body), read_u32(&request_body[ET_RESOURCE_SERVICE_OFFSET_FIELD]),
                &handle);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            /* Resolve the new handle immediately so CREATE returns its trusted address/size facts. */
            status = et_resource_wrap_resolve(handle, &address, &size);

            if (status != ET_WRAP_STATUS_OK)
            {
                /* CREATE is transactional: never expose a handle whose facts could not be resolved. */
                if (et_resource_wrap_destroy(handle) != ET_WRAP_STATUS_OK)
                {
                    return ET_STATUS_INTERNAL_ERROR;
                }

                return status_from_wrap(status);
            }

            write_u32(response_body, handle);
            write_u32(&response_body[ET_RESOURCE_SERVICE_OFFSET_FIELD], size);
            write_u64(&response_body[ET_RESOURCE_SERVICE_SIZE_FIELD], (uint64_t)(uintptr_t)address);
            *response_length = ET_RESOURCE_SERVICE_CREATE_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_RESOURCE_COMMAND_WRITE:
        {
            if (request_length < ET_RESOURCE_SERVICE_WRITE_HEADER_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_resource_wrap_write(
                read_u32(request_body), read_u32(&request_body[ET_RESOURCE_SERVICE_OFFSET_FIELD]),
                &request_body[ET_RESOURCE_SERVICE_DATA_FIELD],
                (uint32_t)request_length - ET_RESOURCE_SERVICE_WRITE_HEADER_SIZE));
        }

        case ET_RESOURCE_COMMAND_READ:
        {
            if (request_length != ET_RESOURCE_SERVICE_READ_REQUEST_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            size = read_u32(&request_body[ET_RESOURCE_SERVICE_SIZE_FIELD]);

            if ((size > response_capacity) || (size > UINT16_MAX))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_resource_wrap_read(
                read_u32(request_body), read_u32(&request_body[ET_RESOURCE_SERVICE_OFFSET_FIELD]),
                response_body, size);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            *response_length = (uint16_t)size;

            return ET_STATUS_OK;
        }

        case ET_RESOURCE_COMMAND_FILL:
        {
            if (request_length != ET_RESOURCE_SERVICE_FILL_REQUEST_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_resource_wrap_fill(
                read_u32(request_body), read_u32(&request_body[ET_RESOURCE_SERVICE_OFFSET_FIELD]),
                request_body[ET_RESOURCE_SERVICE_FILL_VALUE_FIELD],
                read_u32(&request_body[ET_RESOURCE_SERVICE_SIZE_FIELD])));
        }

        case ET_RESOURCE_COMMAND_INFO_GET:
        {
            if ((request_length != ET_RESOURCE_SERVICE_HANDLE_SIZE) ||
                (response_capacity < ET_RESOURCE_SERVICE_INFO_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            handle = read_u32(request_body);
            status = et_resource_wrap_get_info(handle, &info);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            status = et_resource_wrap_resolve(handle, &address, &size);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(response_body, info.size);
            write_u32(&response_body[ET_RESOURCE_SERVICE_OFFSET_FIELD], info.alignment);
            write_u64(&response_body[ET_RESOURCE_SERVICE_SIZE_FIELD], (uint64_t)(uintptr_t)address);
            *response_length = ET_RESOURCE_SERVICE_INFO_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize Resource Wrap ownership and publish the singleton Resource Service descriptor.
 *
 * @param[out] service Resource Service instance whose router descriptor is initialized.
 *
 * @note Resource Wrap initialization establishes the bounded software Resource pool used by later
 *       commands; no Feature IP peripheral is configured by this Service initialization.
 *
 * @return 0 when Resource Wrap and the Service descriptor initialize successfully.
 * @return -1 when service is NULL or Resource Wrap initialization fails.
 */
int et_resource_service_init(et_resource_service_t *service)
{
    if ((service == NULL) || (et_resource_wrap_init() != ET_WRAP_STATUS_OK))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->descriptor.service_id = ET_RESOURCE_SERVICE_ID;
    service->descriptor.instance_id = ET_RESOURCE_SERVICE_INSTANCE_ID;
    service->descriptor.context = service;
    service->descriptor.handle = resource_handle;

    return 0;
}

/**
 * @brief Return the Resource descriptor registered with the common Service Router.
 *
 * @param[in] service Initialized Resource Service instance.
 *
 * @note The returned pointer aliases Service-owned storage and does not change Resource pool state.
 *
 * @return Pointer to the immutable descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_resource_service_descriptor(const et_resource_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}
