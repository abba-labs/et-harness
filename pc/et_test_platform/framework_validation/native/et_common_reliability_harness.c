#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "et_frame.h"
#include "et_message.h"
#include "et_protocol.h"
#include "et_resource_wrap.h"
#include "et_service_router.h"

#define TEST_SERVICE_ID 0x1234u
#define TEST_SESSION_ID 0x10203040u
#define TEST_RESPONSE_BODY_SIZE 16u
#define TEST_RESPONSE_FRAME_SIZE \
    (ET_FRAME_HEADER_SIZE + ET_MESSAGE_HEADER_SIZE + \
     TEST_RESPONSE_BODY_SIZE + ET_FRAME_TRAILER_SIZE)

typedef struct {
    uint8_t input[256];
    size_t input_length;
    size_t input_offset;
    uint8_t output[512];
    size_t output_length;
    size_t write_limit;
    uint32_t executions;
    uint8_t response_overwrite_violation;
} test_io_t;

static int encode_request(
    uint32_t sequence,
    uint16_t command_id,
    uint8_t *output,
    size_t capacity,
    size_t *length)
{
    et_frame_t frame;
    et_message_t message;
    uint16_t payload_length = 0u;

    (void)memset(&frame, 0, sizeof(frame));
    (void)memset(&message, 0, sizeof(message));
    message.service_id = TEST_SERVICE_ID;
    message.command_id = command_id;
    message.instance_id = 0u;
    message.status = ET_STATUS_OK;
    if (et_message_encode(
            &message,
            frame.payload,
            sizeof(frame.payload),
            &payload_length) != 0) {
        return -1;
    }
    frame.message_type = ET_FRAME_TYPE_REQUEST;
    frame.sequence = sequence;
    frame.session_id = TEST_SESSION_ID;
    frame.payload_length = payload_length;
    return et_frame_encode(&frame, output, capacity, length);
}

static int test_frame_resync_preserves_following_magic(void)
{
    et_frame_parser_t parser;
    et_frame_t decoded;
    et_frame_t outer;
    uint8_t inner[ET_FRAME_MAX_SIZE];
    uint8_t third[ET_FRAME_MAX_SIZE];
    uint8_t corrupted[ET_FRAME_MAX_SIZE];
    size_t inner_length = 0u;
    size_t third_length = 0u;
    size_t corrupted_length = 0u;
    size_t index;
    uint32_t ready_after_corrupted = 0u;
    uint32_t ready_after_third = 0u;
    uint16_t payload_length;

    if ((encode_request(2u, 0x20u, inner, sizeof(inner), &inner_length) != 0) ||
        (encode_request(3u, 0x30u, third, sizeof(third), &third_length) != 0)) {
        return 10;
    }

    (void)memset(&outer, 0, sizeof(outer));
    outer.message_type = ET_FRAME_TYPE_REQUEST;
    outer.sequence = 1u;
    outer.session_id = TEST_SESSION_ID;
    outer.payload[0] = 0xa5u;
    outer.payload[1] = 0x5au;
    outer.payload[2] = 0x11u;
    (void)memcpy(&outer.payload[3], inner, inner_length);
    payload_length = (uint16_t)(3u + inner_length);
    outer.payload_length = payload_length;
    if (et_frame_encode(
            &outer,
            corrupted,
            sizeof(corrupted),
            &corrupted_length) != 0) {
        return 11;
    }
    corrupted[corrupted_length - 1u] ^= 0x80u;

    et_frame_parser_init(&parser);
    for (index = 0u; index < corrupted_length; ++index) {
        if (et_frame_parser_push(
                &parser, corrupted[index], &decoded) ==
            ET_FRAME_PARSE_READY) {
            ++ready_after_corrupted;
            if (decoded.sequence != 2u) {
                return 12;
            }
        }
    }
    if (ready_after_corrupted != 1u) {
        return 13;
    }

    for (index = 0u; index < third_length; ++index) {
        if (et_frame_parser_push(
                &parser, third[index], &decoded) ==
            ET_FRAME_PARSE_READY) {
            ++ready_after_third;
            if (decoded.sequence != 3u) {
                return 14;
            }
        }
    }
    return (ready_after_third == 1u) ? 0 : 15;
}

static size_t test_read(void *context, uint8_t *data, size_t capacity)
{
    test_io_t *io = (test_io_t *)context;
    size_t remaining;
    size_t copied;

    if ((io == NULL) || (data == NULL) ||
        (io->input_offset >= io->input_length)) {
        return 0u;
    }
    remaining = io->input_length - io->input_offset;
    copied = (remaining < capacity) ? remaining : capacity;
    (void)memcpy(data, &io->input[io->input_offset], copied);
    io->input_offset += copied;
    return copied;
}

static size_t test_write(
    void *context,
    const uint8_t *data,
    size_t length)
{
    test_io_t *io = (test_io_t *)context;
    size_t written;

    if ((io == NULL) || (data == NULL)) {
        return 0u;
    }
    written = (length < io->write_limit) ? length : io->write_limit;
    if (written > (sizeof(io->output) - io->output_length)) {
        written = sizeof(io->output) - io->output_length;
    }
    (void)memcpy(&io->output[io->output_length], data, written);
    io->output_length += written;
    return written;
}

static uint16_t test_service_handle(
    void *context,
    uint16_t command_id,
    const uint8_t *request_body,
    uint16_t request_length,
    uint8_t *response_body,
    uint16_t response_capacity,
    uint16_t *response_length)
{
    test_io_t *io = (test_io_t *)context;
    uint16_t index;

    (void)request_body;
    if ((io == NULL) || (request_length != 0u) ||
        (response_body == NULL) || (response_length == NULL) ||
        (response_capacity < TEST_RESPONSE_BODY_SIZE)) {
        return ET_STATUS_INVALID_PARAM;
    }
    if ((io->executions == 1u) &&
        (io->output_length < TEST_RESPONSE_FRAME_SIZE)) {
        io->response_overwrite_violation = 1u;
    }
    ++io->executions;
    for (index = 0u; index < TEST_RESPONSE_BODY_SIZE; ++index) {
        response_body[index] = (uint8_t)(command_id + index);
    }
    *response_length = TEST_RESPONSE_BODY_SIZE;
    return ET_STATUS_OK;
}

static int test_protocol_keeps_one_response_owner(void)
{
    et_protocol_t protocol;
    et_protocol_config_t config;
    et_service_router_t router;
    et_service_descriptor_t descriptor;
    et_frame_parser_t parser;
    et_frame_t decoded;
    test_io_t io;
    size_t first_length = 0u;
    size_t second_length = 0u;
    size_t poll;
    size_t index;
    uint32_t responses = 0u;

    (void)memset(&io, 0, sizeof(io));
    io.write_limit = 3u;
    if (encode_request(
            11u,
            0x41u,
            io.input,
            sizeof(io.input),
            &first_length) != 0) {
        return 20;
    }
    if (encode_request(
            12u,
            0x42u,
            &io.input[first_length],
            sizeof(io.input) - first_length,
            &second_length) != 0) {
        return 21;
    }
    io.input_length = first_length + second_length;

    et_service_router_init(&router);
    (void)memset(&descriptor, 0, sizeof(descriptor));
    descriptor.service_id = TEST_SERVICE_ID;
    descriptor.instance_id = 0u;
    descriptor.context = &io;
    descriptor.handle = test_service_handle;
    if (et_service_register(&router, &descriptor) != 0) {
        return 22;
    }

    (void)memset(&config, 0, sizeof(config));
    config.session_id = TEST_SESSION_ID;
    config.session_open_service_id = 0xffffu;
    config.session_open_command_id = 0xffffu;
    config.services = &router;
    config.io.context = &io;
    config.io.read = test_read;
    config.io.write = test_write;
    if (et_protocol_init(&protocol, &config) != 0) {
        return 23;
    }

    for (poll = 0u; poll < 512u; ++poll) {
        (void)et_protocol_poll(&protocol);
        if ((io.executions == 2u) &&
            (io.output_length == (2u * TEST_RESPONSE_FRAME_SIZE))) {
            break;
        }
    }
    if ((io.executions != 2u) ||
        (io.response_overwrite_violation != 0u) ||
        (io.output_length != (2u * TEST_RESPONSE_FRAME_SIZE))) {
        return 24;
    }

    et_frame_parser_init(&parser);
    for (index = 0u; index < io.output_length; ++index) {
        if (et_frame_parser_push(
                &parser, io.output[index], &decoded) ==
            ET_FRAME_PARSE_READY) {
            ++responses;
            if ((decoded.message_type != ET_FRAME_TYPE_RESPONSE) ||
                ((responses == 1u) && (decoded.sequence != 11u)) ||
                ((responses == 2u) && (decoded.sequence != 12u))) {
                return 25;
            }
        }
    }
    return (responses == 2u) ? 0 : 26;
}

static int test_resource_pool_generation_and_bounds(void)
{
    et_resource_handle_t first;
    et_resource_handle_t second;
    et_resource_wrap_info_t info;
    void *address;
    uint32_t resolved_size;
    uint8_t expected[16];
    uint8_t actual[16];
    uint32_t index;

    if (et_resource_wrap_init() != ET_WRAP_STATUS_OK) {
        return 30;
    }
    if (et_resource_wrap_create(16u, 4u, &first) !=
        ET_WRAP_STATUS_OK) {
        return 31;
    }
    for (index = 0u; index < sizeof(expected); ++index) {
        expected[index] = (uint8_t)(index * 17u + 3u);
    }
    if (et_resource_wrap_write(
            first, 0u, expected, sizeof(expected)) !=
        ET_WRAP_STATUS_OK) {
        return 32;
    }
    (void)memset(actual, 0, sizeof(actual));
    if ((et_resource_wrap_read(
             first, 0u, actual, sizeof(actual)) !=
         ET_WRAP_STATUS_OK) ||
        (memcmp(expected, actual, sizeof(expected)) != 0)) {
        return 33;
    }
    if ((et_resource_wrap_resolve(
             first, &address, &resolved_size) !=
         ET_WRAP_STATUS_OK) ||
        (resolved_size != sizeof(expected)) ||
        (et_resource_wrap_contains_range(
             (uintptr_t)address,
             sizeof(expected)) != ET_WRAP_STATUS_OK)) {
        return 34;
    }
    if ((et_resource_wrap_write(
             first, 15u, expected, 2u) !=
         ET_WRAP_STATUS_INVALID_ARGUMENT) ||
        (et_resource_wrap_get_info(first, &info) !=
         ET_WRAP_STATUS_OK) ||
        (info.size != sizeof(expected)) ||
        (info.alignment != 4u)) {
        return 35;
    }
    if (et_resource_wrap_reset() != ET_WRAP_STATUS_OK) {
        return 36;
    }
    if (et_resource_wrap_read(
            first, 0u, actual, sizeof(actual)) !=
        ET_WRAP_STATUS_INVALID_ARGUMENT) {
        return 37;
    }
    if ((et_resource_wrap_create(16u, 4u, &second) !=
         ET_WRAP_STATUS_OK) ||
        (second == first)) {
        return 38;
    }
    if (et_resource_wrap_fill(second, 0u, 0xa5u, 16u) !=
        ET_WRAP_STATUS_OK) {
        return 39;
    }
    return 0;
}

int main(void)
{
    int result;

    result = test_frame_resync_preserves_following_magic();
    if (result != 0) {
        (void)printf("frame_resync=%d\n", result);
        return result;
    }
    result = test_protocol_keeps_one_response_owner();
    if (result != 0) {
        (void)printf("response_owner=%d\n", result);
        return result;
    }
    result = test_resource_pool_generation_and_bounds();
    if (result != 0) {
        (void)printf("resource_pool=%d\n", result);
        return result;
    }
    (void)printf("common_reliability=PASS\n");
    return 0;
}
