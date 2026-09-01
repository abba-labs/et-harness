#include "et_frame.h"

/**
 * @file et_frame.c
 * @brief Allocation-free ET-Frame codec with byte-stream resynchronization.
 */

#include <string.h>

#define ET_FRAME_BYTE_BITS 8u
#define ET_FRAME_CRC32_INITIAL 0xffffffffu
#define ET_FRAME_CRC32_POLYNOMIAL 0xedb88320u
#define ET_FRAME_CRC32_XOR_OUT 0xffffffffu

/**
 * @brief Decode one little-endian 16-bit ET-Frame Wire field.
 *
 * @param[in] data Two bytes containing the Wire field.
 *
 * @note This helper only reads caller-owned memory and does not validate frame boundaries.
 *
 * @return Decoded 16-bit value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8u);
}

/**
 * @brief Decode one little-endian 32-bit ET-Frame Wire field.
 *
 * @param[in] data Four bytes containing the Wire field.
 *
 * @note This helper only reads caller-owned memory and does not validate frame boundaries.
 *
 * @return Decoded 32-bit value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Encode one 16-bit value using the ET-Frame little-endian Wire representation.
 *
 * @param[out] data Two-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned memory and does not alter parser state.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & 0xffu);
    data[1] = (uint8_t)((value >> 8u) & 0xffu);
}

/**
 * @brief Encode one 32-bit value using the ET-Frame little-endian Wire representation.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Value to encode.
 *
 * @note This helper only writes caller-owned memory and does not alter parser state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & 0xffu);
    data[1] = (uint8_t)((value >> 8u) & 0xffu);
    data[2] = (uint8_t)((value >> 16u) & 0xffu);
    data[3] = (uint8_t)((value >> 24u) & 0xffu);
}

/**
 * @brief Validate one message-type value against the ET-Frame V1 public contract.
 *
 * @param[in] message_type Candidate Wire message type.
 *
 * @note This is a pure contract check and does not read parser state or hardware.
 *
 * @return Nonzero for REQUEST, RESPONSE or EVENT; otherwise zero.
 */
static int valid_message_type(uint8_t message_type)
{
    return (message_type == ET_FRAME_TYPE_REQUEST) || (message_type == ET_FRAME_TYPE_RESPONSE) ||
           (message_type == ET_FRAME_TYPE_EVENT);
}

/**
 * @brief Validate the currently buffered fixed header before trusting variable frame length.
 *
 * @param[in] parser Parser containing the candidate fixed header.
 *
 * @note Validation checks magic, version, public message type and payload bound only. It does not
 *       validate CRC because the complete frame may not yet be buffered.
 *
 * @return Nonzero when the fixed header is complete and valid, otherwise zero.
 */
static int parser_header_valid(const et_frame_parser_t *parser)
{
    uint16_t payload_length;

    if ((parser == NULL) || (parser->length < ET_FRAME_HEADER_SIZE))
    {
        return 0;
    }

    payload_length = read_u16(&parser->buffer[ET_FRAME_PAYLOAD_LENGTH_OFFSET]);

    return (parser->buffer[ET_FRAME_MAGIC_FIRST_OFFSET] == ET_FRAME_MAGIC_FIRST) &&
           (parser->buffer[ET_FRAME_MAGIC_SECOND_OFFSET] == ET_FRAME_MAGIC_SECOND) &&
           (parser->buffer[ET_FRAME_VERSION_OFFSET] == ET_FRAME_VERSION) &&
           valid_message_type(parser->buffer[ET_FRAME_MESSAGE_TYPE_OFFSET]) &&
           (payload_length <= ET_TEST_PROTOCOL_MAX_PAYLOAD);
}

/**
 * @brief Recompute the complete buffered-frame length from a validated fixed header.
 *
 * @param[in,out] parser Parser whose expected_length field is updated.
 *
 * @note expected_length is cleared before validation so malformed or incomplete headers never
 *       leave a stale prior-frame length active.
 */
static void parser_rebuild_expected(et_frame_parser_t *parser)
{
    uint16_t payload_length;

    parser->expected_length = 0u;

    if (parser_header_valid(parser) == 0)
    {
        return;
    }

    payload_length = read_u16(&parser->buffer[ET_FRAME_PAYLOAD_LENGTH_OFFSET]);
    parser->expected_length = ET_FRAME_HEADER_SIZE + (size_t)payload_length + ET_FRAME_TRAILER_SIZE;
}

/**
 * @brief Recover parser alignment after malformed bytes by retaining the earliest possible magic.
 *
 * @param[in,out] parser Parser whose buffered prefix is compacted or discarded.
 *
 * @note This function mutates only parser-owned storage. A trailing first-magic byte is preserved
 *       because the second magic byte may arrive in the next transport read.
 */
static void parser_resync(et_frame_parser_t *parser)
{
    size_t index;
    size_t remaining;

    /* Preserve the earliest possible next magic instead of dropping the chunk. */
    for (index = 1u; index + 1u < parser->length; ++index)
    {
        if ((parser->buffer[index] == ET_FRAME_MAGIC_FIRST) &&
            (parser->buffer[index + 1u] == ET_FRAME_MAGIC_SECOND))
        {
            remaining = parser->length - index;
            (void)memmove(parser->buffer, &parser->buffer[index], remaining);
            parser->length = remaining;
            parser_rebuild_expected(parser);

            return;
        }
    }

    /* A trailing 'E' may be the first byte of magic split across reads. */
    if ((parser->length > 0u) && (parser->buffer[parser->length - 1u] == ET_FRAME_MAGIC_FIRST))
    {
        parser->buffer[ET_FRAME_MAGIC_FIRST_OFFSET] = ET_FRAME_MAGIC_FIRST;
        parser->length = 1u;
    }
    else
    {
        parser->length = 0u;
    }

    parser->expected_length = 0u;
}

/**
 * @brief Remove one processed frame while preserving already-buffered trailing bytes.
 *
 * @param[in,out] parser Parser whose leading bytes are consumed.
 * @param[in] consumed Number of leading bytes to remove.
 *
 * @note Remaining bytes are moved to offset zero and expected_length is rebuilt so a second frame
 *       already present in the same transport chunk can be parsed without being reread.
 */
static void parser_consume(et_frame_parser_t *parser, size_t consumed)
{
    size_t remaining;

    if ((parser == NULL) || (consumed > parser->length))
    {
        return;
    }

    remaining = parser->length - consumed;

    if (remaining != 0u)
    {
        (void)memmove(parser->buffer, &parser->buffer[consumed], remaining);
    }

    parser->length = remaining;
    parser_rebuild_expected(parser);
}

/**
 * @brief Parse buffered bytes, recover malformed input and emit at most one complete frame.
 *
 * @param[in,out] parser Streaming parser that owns buffered Wire bytes.
 * @param[out] frame Decoded frame produced when a complete CRC-valid frame is available.
 * @param[in] dropped Existing malformed-input indication carried from the push path.
 *
 * @note One call may discard malformed prefixes and continue searching the same buffer for a later
 *       valid frame. A READY result consumes only that complete frame and preserves trailing bytes.
 *
 * @return ET_FRAME_PARSE_READY when one valid frame is emitted.
 * @return ET_FRAME_PARSE_DROPPED when malformed input was discarded without a ready frame.
 * @return ET_FRAME_PARSE_NONE when more bytes are required and no malformed input was dropped.
 */
static et_frame_parse_result_t parser_process(et_frame_parser_t *parser, et_frame_t *frame,
                                              int dropped)
{
    uint16_t payload_length;
    uint32_t expected_crc;
    uint32_t actual_crc;

    if ((parser == NULL) || (frame == NULL))
    {
        return ET_FRAME_PARSE_DROPPED;
    }

    /* Phase 1: Establish valid magic/header alignment before trusting variable frame length. */
    for (;;)
    {
        if ((parser->length >= ET_FRAME_MAGIC_SIZE) &&
            ((parser->buffer[ET_FRAME_MAGIC_FIRST_OFFSET] != ET_FRAME_MAGIC_FIRST) ||
             (parser->buffer[ET_FRAME_MAGIC_SECOND_OFFSET] != ET_FRAME_MAGIC_SECOND)))
        {
            parser_resync(parser);
            dropped = 1;

            if (parser->length < ET_FRAME_MAGIC_SIZE)
            {
                return ET_FRAME_PARSE_DROPPED;
            }

            continue;
        }

        if (parser->expected_length == 0u)
        {
            if (parser->length < ET_FRAME_HEADER_SIZE)
            {
                return dropped ? ET_FRAME_PARSE_DROPPED : ET_FRAME_PARSE_NONE;
            }

            if (parser_header_valid(parser) == 0)
            {
                parser_resync(parser);
                dropped = 1;

                if (parser->length < ET_FRAME_HEADER_SIZE)
                {
                    return ET_FRAME_PARSE_DROPPED;
                }

                continue;
            }

            parser_rebuild_expected(parser);
        }

        if (parser->length < parser->expected_length)
        {
            return dropped ? ET_FRAME_PARSE_DROPPED : ET_FRAME_PARSE_NONE;
        }

        /* Phase 2: Validate CRC before exposing any decoded header or payload fields. */
        expected_crc = read_u32(&parser->buffer[parser->expected_length - ET_FRAME_TRAILER_SIZE]);
        actual_crc =
            et_frame_crc32(parser->buffer, parser->expected_length - ET_FRAME_TRAILER_SIZE);

        if (expected_crc != actual_crc)
        {
            parser_resync(parser);
            dropped = 1;

            if (parser->length == 0u)
            {
                return ET_FRAME_PARSE_DROPPED;
            }

            continue;
        }

        /* Phase 3: Decode the validated frame, then consume exactly its bytes from the parser. */
        payload_length = read_u16(&parser->buffer[ET_FRAME_PAYLOAD_LENGTH_OFFSET]);
        frame->message_type = parser->buffer[ET_FRAME_MESSAGE_TYPE_OFFSET];
        frame->flags = read_u16(&parser->buffer[ET_FRAME_FLAGS_OFFSET]);
        frame->sequence = read_u32(&parser->buffer[ET_FRAME_SEQUENCE_OFFSET]);
        frame->session_id = read_u32(&parser->buffer[ET_FRAME_SESSION_ID_OFFSET]);
        frame->payload_length = payload_length;

        if (payload_length > 0u)
        {
            (void)memcpy(frame->payload, &parser->buffer[ET_FRAME_HEADER_SIZE], payload_length);
        }

        parser_consume(parser, parser->expected_length);

        return ET_FRAME_PARSE_READY;
    }
}

/**
 * @brief Reset streaming parser indices without clearing fixed parser storage.
 *
 * @param[out] parser Parser to reset to the empty state.
 *
 * @note Buffered bytes remain physically present but become unreachable because length and
 *       expected_length are cleared.
 */
void et_frame_parser_init(et_frame_parser_t *parser)
{
    if (parser != NULL)
    {
        parser->length = 0u;
        parser->expected_length = 0u;
    }
}

/**
 * @brief Append one Wire byte and advance the bounded streaming ET-Frame parser.
 *
 * @param[in,out] parser Parser that receives the new byte.
 * @param[in] byte Next transport byte in stream order.
 * @param[out] frame Destination frame populated when parsing reaches READY.
 *
 * @note Bytes before the first magic prefix are ignored without allocating storage. Parser overflow
 *       attempts resynchronization before falling back to a complete parser reset.
 *
 * @return Streaming parse result after consuming the supplied byte.
 */
et_frame_parse_result_t et_frame_parser_push(et_frame_parser_t *parser, uint8_t byte,
                                             et_frame_t *frame)
{
    int dropped = 0;

    if ((parser == NULL) || (frame == NULL))
    {
        return ET_FRAME_PARSE_DROPPED;
    }

    if ((parser->length == 0u) && (byte != ET_FRAME_MAGIC_FIRST))
    {
        return ET_FRAME_PARSE_NONE;
    }

    if (parser->length >= ET_FRAME_MAX_SIZE)
    {
        parser_resync(parser);
        dropped = 1;

        if (parser->length >= ET_FRAME_MAX_SIZE)
        {
            et_frame_parser_init(parser);
        }
    }

    parser->buffer[parser->length++] = byte;

    return parser_process(parser, frame, dropped);
}

/**
 * @brief Re-run parsing when a prior READY frame left complete trailing bytes buffered.
 *
 * @param[in,out] parser Parser that may already contain another complete frame.
 * @param[out] frame Destination frame populated when trailing data yields READY.
 *
 * @note No new transport byte is appended; only already-buffered parser state is processed.
 *
 * @return Streaming parse result for the currently buffered trailing data.
 */
et_frame_parse_result_t et_frame_parser_drain(et_frame_parser_t *parser, et_frame_t *frame)
{
    return parser_process(parser, frame, 0);
}

/**
 * @brief Encode one complete ET-Frame V1 message into caller-owned Wire storage.
 *
 * @param[in] frame Stable frame fields and bounded payload to encode.
 * @param[out] output Destination Wire buffer.
 * @param[in] capacity Number of bytes available in output.
 * @param[out] encoded_length Complete encoded frame size in bytes.
 *
 * @note Header fields and payload are encoded first; CRC is calculated over exactly those bytes and
 *       appended last. The function mutates only caller-owned output storage.
 *
 * @return 0 when the frame is valid and fits in output.
 * @return -1 when pointers, message type, payload length or destination capacity are invalid.
 */
int et_frame_encode(const et_frame_t *frame, uint8_t *output, size_t capacity,
                    size_t *encoded_length)
{
    size_t total_length;
    uint32_t crc;

    /* Phase 1: Validate public frame semantics and derive the exact bounded Wire size. */
    if ((frame == NULL) || (output == NULL) || (encoded_length == NULL))
    {
        return -1;
    }

    if ((frame->payload_length > ET_TEST_PROTOCOL_MAX_PAYLOAD) ||
        !valid_message_type(frame->message_type))
    {
        return -1;
    }

    total_length = ET_FRAME_HEADER_SIZE + (size_t)frame->payload_length + ET_FRAME_TRAILER_SIZE;

    if (capacity < total_length)
    {
        return -1;
    }

    /* Phase 2: Encode fixed header and bounded payload using canonical little-endian fields. */
    output[ET_FRAME_MAGIC_FIRST_OFFSET] = ET_FRAME_MAGIC_FIRST;
    output[ET_FRAME_MAGIC_SECOND_OFFSET] = ET_FRAME_MAGIC_SECOND;
    output[ET_FRAME_VERSION_OFFSET] = ET_FRAME_VERSION;
    output[ET_FRAME_MESSAGE_TYPE_OFFSET] = frame->message_type;
    write_u16(&output[ET_FRAME_FLAGS_OFFSET], frame->flags);
    write_u16(&output[ET_FRAME_PAYLOAD_LENGTH_OFFSET], frame->payload_length);
    write_u32(&output[ET_FRAME_SEQUENCE_OFFSET], frame->sequence);
    write_u32(&output[ET_FRAME_SESSION_ID_OFFSET], frame->session_id);

    if (frame->payload_length > 0u)
    {
        (void)memcpy(&output[ET_FRAME_HEADER_SIZE], frame->payload, frame->payload_length);
    }

    /* Phase 3: Seal the encoded bytes with CRC and publish the final frame length. */
    crc = et_frame_crc32(output, total_length - ET_FRAME_TRAILER_SIZE);
    write_u32(&output[total_length - ET_FRAME_TRAILER_SIZE], crc);
    *encoded_length = total_length;

    return 0;
}

/**
 * @brief Calculate the reflected IEEE CRC32 used by ET-Frame V1.
 *
 * @param[in] data Wire bytes included in the CRC calculation.
 * @param[in] length Number of bytes to process.
 *
 * @note The implementation is allocation-free and deterministic. It does not read hardware CRC
 *       state and therefore produces the same golden result on every backend.
 *
 * @return Reflected IEEE CRC32 of data, or zero when data is NULL.
 */
uint32_t et_frame_crc32(const uint8_t *data, size_t length)
{
    uint32_t crc = ET_FRAME_CRC32_INITIAL;
    size_t index;
    uint8_t bit;

    if (data == NULL)
    {
        return 0u;
    }

    for (index = 0u; index < length; ++index)
    {
        crc ^= (uint32_t)data[index];

        for (bit = 0u; bit < ET_FRAME_BYTE_BITS; ++bit)
        {
            crc = (crc >> 1u) ^ ((crc & 1u) ? ET_FRAME_CRC32_POLYNOMIAL : 0u);
        }
    }

    return crc ^ ET_FRAME_CRC32_XOR_OUT;
}
