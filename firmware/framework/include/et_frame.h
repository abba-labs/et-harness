#ifndef ET_FRAME_H
#define ET_FRAME_H

/**
 * @file et_frame.h
 * @brief ET-Frame wire-format encoder and streaming parser.
 *
 * This layer validates framing, payload bounds and CRC32 only. Service and
 * command semantics are decoded by the message and router layers.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_test_protocol_config.h"

#define ET_FRAME_VERSION 1u
#define ET_FRAME_HEADER_SIZE 16u
#define ET_FRAME_TRAILER_SIZE 4u
#define ET_FRAME_MAGIC_SIZE 2u

/* ET-Frame V1 fixed header offsets; these values are part of the public Wire contract. */
#define ET_FRAME_MAGIC_FIRST_OFFSET 0u
#define ET_FRAME_MAGIC_SECOND_OFFSET 1u
#define ET_FRAME_VERSION_OFFSET 2u
#define ET_FRAME_MESSAGE_TYPE_OFFSET 3u
#define ET_FRAME_FLAGS_OFFSET 4u
#define ET_FRAME_PAYLOAD_LENGTH_OFFSET 6u
#define ET_FRAME_SEQUENCE_OFFSET 8u
#define ET_FRAME_SESSION_ID_OFFSET 12u

#define ET_FRAME_MAGIC_FIRST ((uint8_t)'E')
#define ET_FRAME_MAGIC_SECOND ((uint8_t)'T')
#define ET_FRAME_MAX_SIZE                                                                          \
    (ET_FRAME_HEADER_SIZE + ET_TEST_PROTOCOL_MAX_PAYLOAD + ET_FRAME_TRAILER_SIZE)

typedef enum
{
    ET_FRAME_TYPE_REQUEST = 1,  /**< PC-to-target request. */
    ET_FRAME_TYPE_RESPONSE = 2, /**< Target response using request identity. */
    ET_FRAME_TYPE_EVENT = 3     /**< Target-originated asynchronous event. */
} et_frame_type_t;

typedef enum
{
    ET_FRAME_PARSE_NONE = 0,
    ET_FRAME_PARSE_READY = 1,
    ET_FRAME_PARSE_DROPPED = 2
} et_frame_parse_result_t;

typedef struct
{
    uint8_t message_type;                          /**< One et_frame_type_t wire value. */
    uint16_t flags;                                /**< Wire flags preserved by this layer. */
    uint32_t sequence;                             /**< Request/response correlation sequence. */
    uint32_t session_id;                           /**< Active protocol session identity. */
    uint16_t payload_length;                       /**< Valid bytes in payload. */
    uint8_t payload[ET_TEST_PROTOCOL_MAX_PAYLOAD]; /**< Message bytes. */
} et_frame_t;

typedef struct
{
    size_t length;                     /**< Bytes currently buffered. */
    size_t expected_length;            /**< Complete frame size once header is known. */
    uint8_t buffer[ET_FRAME_MAX_SIZE]; /**< Bounded parser storage. */
} et_frame_parser_t;

/** Reset a parser to the magic-search state. */
void et_frame_parser_init(et_frame_parser_t *parser);
/** Consume one byte and report whether a valid frame or dropped data resulted. */
et_frame_parse_result_t et_frame_parser_push(et_frame_parser_t *parser, uint8_t byte,
                                             et_frame_t *frame);
/** Parse one complete frame already buffered without consuming a new byte. */
et_frame_parse_result_t et_frame_parser_drain(et_frame_parser_t *parser, et_frame_t *frame);

int et_frame_encode(const et_frame_t *frame, uint8_t *output, size_t capacity,
                    size_t *encoded_length);

/** Compute the protocol CRC32 over exactly length bytes. */
uint32_t et_frame_crc32(const uint8_t *data, size_t length);

#endif
