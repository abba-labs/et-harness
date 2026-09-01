#ifndef ET_MESSAGE_H
#define ET_MESSAGE_H

/**
 * @file et_message.h
 * @brief Service-message header codec carried inside ET-Frame payloads.
 */

#include <stddef.h>
#include <stdint.h>

#define ET_MESSAGE_HEADER_SIZE 8u

/* Service-message fixed header offsets; these values are part of the public Wire contract. */
#define ET_MESSAGE_SERVICE_ID_OFFSET 0u
#define ET_MESSAGE_COMMAND_ID_OFFSET 2u
#define ET_MESSAGE_INSTANCE_ID_OFFSET 4u
#define ET_MESSAGE_STATUS_OFFSET 6u

typedef enum
{
    ET_STATUS_OK = 0u,
    ET_STATUS_INVALID_SERVICE = 1u,
    ET_STATUS_INVALID_COMMAND = 2u,
    ET_STATUS_INVALID_PARAM = 3u,
    ET_STATUS_NOT_SUPPORTED = 4u,
    ET_STATUS_BUSY = 5u,
    ET_STATUS_INTERNAL_ERROR = 6u
} et_status_t;

typedef struct
{
    uint16_t service_id;  /**< Stable IP or framework service identity. */
    uint16_t command_id;  /**< Service-local command identity. */
    uint16_t instance_id; /**< Logical IP instance selected by PC. */
    uint16_t status;      /**< et_status_t in responses; zero in requests. */
    const uint8_t *body;  /**< Borrowed body pointer; storage is not owned. */
    uint16_t body_length; /**< Valid body bytes after the fixed header. */
} et_message_t;

/** Decode a bounded payload without retaining ownership of its storage. */
int et_message_decode(const uint8_t *payload, uint16_t payload_length, et_message_t *message);

/** Encode one message and return the complete payload size. */
int et_message_encode(const et_message_t *message, uint8_t *payload, size_t capacity,
                      uint16_t *payload_length);

#endif
