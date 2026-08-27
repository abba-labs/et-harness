#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "et_frame.h"

static int encode_frame(
    uint32_t sequence,
    uint8_t *output,
    size_t capacity,
    size_t *length)
{
    et_frame_t frame;

    (void)memset(&frame, 0, sizeof(frame));
    frame.message_type = ET_FRAME_TYPE_REQUEST;
    frame.sequence = sequence;
    frame.session_id = 0x12345678u;
    frame.payload_length = 1u;
    frame.payload[0] = (uint8_t)sequence;
    return et_frame_encode(&frame, output, capacity, length);
}

int main(void)
{
    et_frame_parser_t parser;
    et_frame_t decoded;
    uint8_t first[ET_FRAME_MAX_SIZE];
    uint8_t second[ET_FRAME_MAX_SIZE];
    size_t first_length = 0u;
    size_t second_length = 0u;

    if ((encode_frame(1u, first, sizeof(first), &first_length) != 0) ||
        (encode_frame(2u, second, sizeof(second), &second_length) != 0) ||
        ((first_length + second_length) > sizeof(parser.buffer))) {
        return 10;
    }

    et_frame_parser_init(&parser);
    (void)memcpy(parser.buffer, first, first_length);
    (void)memcpy(&parser.buffer[first_length], second, second_length);
    parser.length = first_length + second_length;
    parser.expected_length = 0u;

    if ((et_frame_parser_drain(&parser, &decoded) !=
         ET_FRAME_PARSE_READY) ||
        (decoded.sequence != 1u) ||
        (parser.length != second_length)) {
        return 11;
    }
    if ((et_frame_parser_drain(&parser, &decoded) !=
         ET_FRAME_PARSE_READY) ||
        (decoded.sequence != 2u) ||
        (parser.length != 0u)) {
        return 12;
    }
    if (et_frame_parser_drain(&parser, &decoded) !=
        ET_FRAME_PARSE_NONE) {
        return 13;
    }

    (void)printf("frame_buffered_drain=PASS\n");
    return 0;
}
