#include "et_framework_service.h"

/**
 * @file et_framework_service.c
 * @brief Decode framework commands and return identity/registry/protocol facts.
 */

#include <stddef.h>
#include <string.h>

#include "et_frame.h"

/**
 * @brief Encode one 16-bit value into an unaligned little-endian Framework Wire field.
 *
 * @param[out] data Two-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned response memory and does not modify Framework state.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & 0xffu);
    data[1] = (uint8_t)((value >> 8u) & 0xffu);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian Framework Wire field.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned response memory and does not modify Framework state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & 0xffu);
    data[1] = (uint8_t)((value >> 8u) & 0xffu);
    data[2] = (uint8_t)((value >> 16u) & 0xffu);
    data[3] = (uint8_t)((value >> 24u) & 0xffu);
}

/**
 * @brief Build the stable lowercase FNV-1a identity of the current Service registry.
 *
 * @param[in] router Service router whose ordered Service/instance pairs define registry identity.
 * @param[out] output Fixed-size lowercase hexadecimal hash string including terminator.
 *
 * @note Hash input is registry order plus little-endian Service/instance bytes only. No Service
 *       callback is invoked, so HELLO can identify registry composition without executing hardware.
 *
 * @return 0 when every registered descriptor is readable and the hash is produced.
 * @return -1 when the registry contains an invalid descriptor lookup.
 */
static int build_registry_hash(const et_service_router_t *router,
                               char output[ET_FRAMEWORK_REGISTRY_HASH_TEXT_SIZE])
{
    static const char digits[] = "0123456789abcdef";
    uint32_t hash = ET_FRAMEWORK_FNV1A_OFFSET_BASIS;
    uint16_t count;
    uint16_t index;
    uint8_t byte_index;
    const et_service_descriptor_t *descriptor;

    /* FNV-1a over ordered service/instance pairs gives PC a compact identity. */
    count = et_service_count(router);

    for (index = 0u; index < count; ++index)
    {
        descriptor = et_service_at(router, index);

        if (descriptor == NULL)
        {
            return -1;
        }

        for (byte_index = 0u; byte_index < sizeof(descriptor->service_id); ++byte_index)
        {
            hash ^= (uint8_t)(descriptor->service_id >> (byte_index * ET_FRAMEWORK_BITS_PER_BYTE));
            hash *= ET_FRAMEWORK_FNV1A_PRIME;
        }

        for (byte_index = 0u; byte_index < sizeof(descriptor->instance_id); ++byte_index)
        {
            hash ^= (uint8_t)(descriptor->instance_id >> (byte_index * ET_FRAMEWORK_BITS_PER_BYTE));
            hash *= ET_FRAMEWORK_FNV1A_PRIME;
        }
    }

    for (index = 0u; index < ET_FRAMEWORK_REGISTRY_HASH_DIGITS; ++index)
    {
        output[(ET_FRAMEWORK_REGISTRY_HASH_DIGITS - 1u) - index] =
            digits[hash & ET_FRAMEWORK_REGISTRY_HASH_NIBBLE_MASK];
        hash >>= ET_FRAMEWORK_BITS_PER_HEX_DIGIT;
    }

    output[ET_FRAMEWORK_REGISTRY_HASH_DIGITS] = '\0';

    return 0;
}

/**
 * @brief Append one uint8-length-prefixed UTF-8 string to a bounded Framework response.
 *
 * @param[out] output Response buffer receiving length byte and string data.
 * @param[in] capacity Total writable bytes in output.
 * @param[in,out] offset Current output cursor advanced after a successful append.
 * @param[in] value NUL-terminated string whose bytes are appended without the terminator.
 *
 * @note Length is bounded to UINT8_MAX by the Wire contract. Failure leaves the caller responsible
 *       for discarding any response being assembled; this helper performs no hardware action.
 *
 * @return 0 when the complete prefixed string fits and is appended.
 * @return -1 when pointers are invalid or the string exceeds Wire/capacity bounds.
 */
static int append_string(uint8_t *output, uint16_t capacity, uint16_t *offset, const char *value)
{
    size_t length;

    if ((output == NULL) || (offset == NULL) || (value == NULL))
    {
        return -1;
    }

    length = strlen(value);

    if ((length > UINT8_MAX) || ((size_t)*offset + sizeof(uint8_t) + length > capacity))
    {
        return -1;
    }

    output[(*offset)++] = (uint8_t)length;
    memcpy(&output[*offset], value, length);
    *offset = (uint16_t)(*offset + (uint16_t)length);

    return 0;
}

/**
 * @brief Encode HELLO identity containing protocol version, chip/build and Service registry hash.
 *
 * @param[in] service Framework Service providing immutable identity and router facts.
 * @param[out] response Caller-owned response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] length Number of HELLO response bytes produced.
 *
 * @note HELLO reports only immutable/application and registry facts. Building it does not change
 *       session state; protocol commits a session only after the final HELLO status is successful.
 *
 * @return ET_STATUS_OK when the complete identity fits; otherwise ET_STATUS_INTERNAL_ERROR.
 */
static uint16_t build_hello(const et_framework_service_t *service, uint8_t *response,
                            uint16_t capacity, uint16_t *length)
{
    uint16_t offset = 0u;
    char registry_hash[ET_FRAMEWORK_REGISTRY_HASH_TEXT_SIZE];

    if (capacity < ET_FRAMEWORK_VERSION_FIELD_SIZE)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    if (build_registry_hash(service->router, registry_hash) != 0)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u16(&response[offset], ET_FRAME_VERSION);
    offset += ET_FRAMEWORK_VERSION_FIELD_SIZE;

    if ((append_string(response, capacity, &offset, service->config.chip_id) != 0) ||
        (append_string(response, capacity, &offset, service->config.firmware_build_id) != 0) ||
        (append_string(response, capacity, &offset, registry_hash) != 0))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *length = offset;

    return ET_STATUS_OK;
}

/**
 * @brief Encode protocol version and current Firmware build identity.
 *
 * @param[in] service Framework Service providing immutable build identity.
 * @param[out] response Caller-owned response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] length Number of VERSION_GET response bytes produced.
 *
 * @note This function reads immutable configuration only and does not change protocol/session state.
 *
 * @return ET_STATUS_OK when the response fits; otherwise ET_STATUS_INTERNAL_ERROR.
 */
static uint16_t build_version(const et_framework_service_t *service, uint8_t *response,
                              uint16_t capacity, uint16_t *length)
{
    uint16_t offset = 0u;

    if (capacity < ET_FRAMEWORK_VERSION_FIELD_SIZE)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u16(response, ET_FRAME_VERSION);
    offset = ET_FRAMEWORK_VERSION_FIELD_SIZE;

    if (append_string(response, capacity, &offset, service->config.firmware_build_id) != 0)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    *length = offset;

    return ET_STATUS_OK;
}

/**
 * @brief Encode all currently registered Service/instance identities in router order.
 *
 * @param[in] service Framework Service that references the common Service router.
 * @param[out] response Caller-owned response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] length Number of SERVICE_LIST response bytes produced.
 *
 * @note Registry order is preserved exactly so host-side identity/hash reasoning sees the same
 *       stable ordering. No Service callback is invoked while the list is built.
 *
 * @return ET_STATUS_OK when every descriptor fits and is readable; otherwise INTERNAL_ERROR.
 */
static uint16_t build_service_list(const et_framework_service_t *service, uint8_t *response,
                                   uint16_t capacity, uint16_t *length)
{
    uint16_t count;
    uint16_t index;
    uint16_t offset = ET_FRAMEWORK_VERSION_FIELD_SIZE;
    const et_service_descriptor_t *descriptor;

    count = et_service_count(service->router);

    if ((size_t)capacity <
        (ET_FRAMEWORK_VERSION_FIELD_SIZE + ((size_t)count * ET_FRAMEWORK_SERVICE_LIST_ENTRY_SIZE)))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u16(response, count);

    for (index = 0u; index < count; ++index)
    {
        descriptor = et_service_at(service->router, index);

        if (descriptor == NULL)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        write_u16(&response[offset], descriptor->service_id);
        write_u16(&response[offset + sizeof(uint16_t)], descriptor->instance_id);
        offset += ET_FRAMEWORK_SERVICE_LIST_ENTRY_SIZE;
    }

    *length = offset;

    return ET_STATUS_OK;
}

/**
 * @brief Encode protocol reliability counters used by host-side diagnostics.
 *
 * @param[in] service Framework Service that references immutable protocol statistics.
 * @param[out] response Caller-owned response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] length Number of STATISTICS_GET response bytes produced.
 *
 * @note The counters are observations only. Reading them does not clear statistics or change protocol state.
 *
 * @return ET_STATUS_OK when statistics are available and response capacity is sufficient.
 * @return ET_STATUS_INTERNAL_ERROR when statistics or response capacity are unavailable.
 */
static uint16_t build_statistics(const et_framework_service_t *service, uint8_t *response,
                                 uint16_t capacity, uint16_t *length)
{
    if ((service->protocol_stats == NULL) || (capacity < ET_FRAMEWORK_STATISTICS_RESPONSE_SIZE))
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    write_u32(&response[ET_FRAMEWORK_STATISTICS_RX_FRAMES_OFFSET],
              service->protocol_stats->rx_frames);
    write_u32(&response[ET_FRAMEWORK_STATISTICS_TX_FRAMES_OFFSET],
              service->protocol_stats->tx_frames);
    write_u32(&response[ET_FRAMEWORK_STATISTICS_PARSE_ERRORS_OFFSET],
              service->protocol_stats->parse_errors);
    write_u32(&response[ET_FRAMEWORK_STATISTICS_DUPLICATE_REQUESTS_OFFSET],
              service->protocol_stats->duplicate_requests);
    *length = ET_FRAMEWORK_STATISTICS_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Validate the common Framework request envelope and dispatch one published command.
 *
 * @param[in,out] context Framework Service context retained by the common router.
 * @param[in] command_id Stable Framework command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response-body storage.
 * @param[in] response_capacity Available response-body bytes.
 * @param[out] response_length Number of response-body bytes produced.
 *
 * @note Framework commands expose protocol/identity/registry facts only. The handler does not execute
 *       Feature IP hardware actions or decide test PASS/FAIL.
 *
 * @return Stable ET status for envelope validation, command selection or response construction.
 */
static uint16_t framework_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                                 uint16_t request_length, uint8_t *response_body,
                                 uint16_t response_capacity, uint16_t *response_length)
{
    et_framework_service_t *service = (et_framework_service_t *)context;

    /* Phase 1: Validate the common router envelope before inspecting any command body. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 2: Enforce each command's fixed request contract and build its factual response. */
    switch (command_id)
    {
        case ET_FRAMEWORK_COMMAND_HELLO:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return build_hello(service, response_body, response_capacity, response_length);
        }

        case ET_FRAMEWORK_COMMAND_ECHO:
        {
            if (request_length > response_capacity)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (request_length != 0u)
            {
                memcpy(response_body, request_body, request_length);
            }

            *response_length = request_length;

            return ET_STATUS_OK;
        }

        case ET_FRAMEWORK_COMMAND_VERSION_GET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return build_version(service, response_body, response_capacity, response_length);
        }

        case ET_FRAMEWORK_COMMAND_SERVICE_LIST:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return build_service_list(service, response_body, response_capacity, response_length);
        }

        case ET_FRAMEWORK_COMMAND_STATISTICS_GET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return build_statistics(service, response_body, response_capacity, response_length);
        }

        case ET_FRAMEWORK_COMMAND_RESET_REASON_GET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (service->config.reset_reason_supported == 0u)
            {
                return ET_STATUS_NOT_SUPPORTED;
            }

            if (response_capacity < ET_FRAMEWORK_RESET_REASON_RESPONSE_SIZE)
            {
                return ET_STATUS_INTERNAL_ERROR;
            }

            write_u32(response_body, service->config.reset_reason);
            *response_length = ET_FRAMEWORK_RESET_REASON_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize the Framework Service from immutable Application and Runtime facts.
 *
 * @param[out] service Framework Service instance whose descriptor is initialized.
 * @param[in] config Chip/build/reset identity owned by the Application.
 * @param[in] router Service router used for HELLO hash and SERVICE_LIST observations.
 * @param[in] protocol_stats Protocol counters exposed through STATISTICS_GET.
 *
 * @note Initialization copies/references software facts only and does not touch transport or Feature
 *       hardware. The router/statistics pointers must remain valid for the Service lifetime.
 *
 * @return 0 when required identity and Runtime dependencies are valid.
 * @return -1 when any required pointer or identity string is missing.
 */
int et_framework_service_init(et_framework_service_t *service,
                              const et_framework_service_config_t *config,
                              const et_service_router_t *router,
                              const et_protocol_stats_t *protocol_stats)
{
    if ((service == NULL) || (config == NULL) || (router == NULL) || (protocol_stats == NULL) ||
        (config->chip_id == NULL) || (config->firmware_build_id == NULL))
    {
        return -1;
    }

    memset(service, 0, sizeof(*service));
    service->config = *config;
    service->router = router;
    service->protocol_stats = protocol_stats;
    service->descriptor.service_id = ET_FRAMEWORK_SERVICE_ID;
    service->descriptor.instance_id = ET_FRAMEWORK_INSTANCE_ID;
    service->descriptor.context = service;
    service->descriptor.handle = framework_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the Framework descriptor registered with the common Service Router.
 *
 * @param[in] service Initialized Framework Service instance.
 *
 * @note The returned pointer aliases Service-owned storage and does not change Framework state.
 *
 * @return Pointer to the immutable descriptor, or NULL when service is NULL.
 */
const et_service_descriptor_t *
et_framework_service_descriptor(const et_framework_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}
