#include "et_message.h"

/**
 * @file et_message.c
 * @brief Little-endian codec for the fixed Service message header.
 */

#include <limits.h>
#include <string.h>

/**
 * @brief Decode one little-endian 16-bit Service-message field.
 *
 * @param[in] data Two bytes containing one little-endian unsigned value.
 *
 * @note This helper only reads caller-owned memory and does not validate the surrounding message.
 *
 * @return Decoded 16-bit value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8u));
}

/**
 * @brief Encode one 16-bit value using the Service-message little-endian representation.
 *
 * @param[out] data Two-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned memory and does not change message length or state.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & 0xffu);
    data[1] = (uint8_t)((value >> 8u) & 0xffu);
}

/**
 * @brief Decode the fixed Service-message header and borrow its bounded body.
 *
 * @param[in] payload Complete Service-message payload received from ET-Frame.
 * @param[in] payload_length Number of valid bytes in payload.
 * @param[out] message Decoded message view whose body points into payload storage.
 *
 * @note The decoded body is not copied; message->body aliases the caller-owned payload. This
 *       function performs no Service dispatch and does not access hardware.
 *
 * @return 0 when the fixed header is present and decoded successfully.
 * @return -1 when required pointers are invalid or the payload is shorter than the header.
 */
int et_message_decode(const uint8_t *payload, uint16_t payload_length, et_message_t *message)
{
    if ((payload == NULL) || (message == NULL) || (payload_length < ET_MESSAGE_HEADER_SIZE))
    {
        return -1;
    }

    message->service_id = read_u16(&payload[ET_MESSAGE_SERVICE_ID_OFFSET]);
    message->command_id = read_u16(&payload[ET_MESSAGE_COMMAND_ID_OFFSET]);
    message->instance_id = read_u16(&payload[ET_MESSAGE_INSTANCE_ID_OFFSET]);
    message->status = read_u16(&payload[ET_MESSAGE_STATUS_OFFSET]);
    message->body = &payload[ET_MESSAGE_HEADER_SIZE];
    message->body_length = (uint16_t)(payload_length - ET_MESSAGE_HEADER_SIZE);

    return 0;
}

/**
 * @brief Encode one Service-message header followed by the caller-supplied body.
 *
 * @param[in] message Message fields and optional body to encode.
 * @param[out] payload Destination buffer for the encoded message.
 * @param[in] capacity Available bytes in payload.
 * @param[out] payload_length Total encoded payload length in bytes.
 *
 * @note The encoder copies the body into caller-owned payload storage only after validating total
 *       size against both capacity and the 16-bit ET-Frame payload-length boundary.
 *
 * @return 0 when the complete message is encoded successfully.
 * @return -1 when pointers/body ownership are invalid or the encoded message cannot fit.
 */
int et_message_encode(const et_message_t *message, uint8_t *payload, size_t capacity,
                      uint16_t *payload_length)
{
    size_t required;

    if ((message == NULL) || (payload == NULL) || (payload_length == NULL) ||
        ((message->body_length != 0u) && (message->body == NULL)))
    {
        return -1;
    }

    required = ET_MESSAGE_HEADER_SIZE + (size_t)message->body_length;

    if ((required > capacity) || (required > UINT16_MAX))
    {
        return -1;
    }

    write_u16(&payload[ET_MESSAGE_SERVICE_ID_OFFSET], message->service_id);
    write_u16(&payload[ET_MESSAGE_COMMAND_ID_OFFSET], message->command_id);
    write_u16(&payload[ET_MESSAGE_INSTANCE_ID_OFFSET], message->instance_id);
    write_u16(&payload[ET_MESSAGE_STATUS_OFFSET], message->status);

    if (message->body_length != 0u)
    {
        memcpy(&payload[ET_MESSAGE_HEADER_SIZE], message->body, message->body_length);
    }

    *payload_length = (uint16_t)required;

    return 0;
}
