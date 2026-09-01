#include <stdio.h>
#include <string.h>

#include "et_frame.h"
#include "et_message.h"
#include "et_protocol.h"
#include "et_service_router.h"

typedef struct {
    uint8_t rx[ET_FRAME_MAX_SIZE];
    size_t rx_length;
    size_t rx_offset;
    uint8_t tx[ET_FRAME_MAX_SIZE * 2u];
    size_t tx_length;
    size_t max_write;
} test_io_t;

typedef struct {
    uint32_t calls;
} test_service_t;

static size_t test_read(void *context, uint8_t *data, size_t capacity)
{
    test_io_t *io = (test_io_t *)context;
    size_t remaining = io->rx_length - io->rx_offset;
    size_t count = (remaining < capacity) ? remaining : capacity;

    if (count != 0u) {
        memcpy(data, &io->rx[io->rx_offset], count);
        io->rx_offset += count;
    }
    return count;
}

static size_t test_write(
    void *context,
    const uint8_t *data,
    size_t length)
{
    test_io_t *io = (test_io_t *)context;
    size_t count = length;

    if ((io->max_write != 0u) && (count > io->max_write)) {
        count = io->max_write;
    }
    if (count > (sizeof(io->tx) - io->tx_length)) {
        count = sizeof(io->tx) - io->tx_length;
    }
    if (count != 0u) {
        memcpy(&io->tx[io->tx_length], data, count);
        io->tx_length += count;
    }
    return count;
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
    test_service_t *service = (test_service_t *)context;

    ++service->calls;
    *response_length = 0u;
    if (command_id == 1u) {
        return (request_length == 0u)
            ? ET_STATUS_OK
            : ET_STATUS_INVALID_PARAM;
    }
    if (command_id == 2u) {
        if (request_length > response_capacity) {
            return ET_STATUS_INVALID_PARAM;
        }
        memcpy(response_body, request_body, request_length);
        *response_length = request_length;
        return ET_STATUS_OK;
    }
    if (command_id == 3u) {
        static const uint8_t detail[] = {
            (uint8_t)'b',
            (uint8_t)'a',
            (uint8_t)'d'
        };
        if (response_capacity < sizeof(detail)) {
            return ET_STATUS_INTERNAL_ERROR;
        }
        memcpy(response_body, detail, sizeof(detail));
        *response_length = (uint16_t)sizeof(detail);
        return ET_STATUS_INVALID_PARAM;
    }
    if (command_id == 4u) {
        return ET_STATUS_OK;
    }
    return ET_STATUS_INVALID_COMMAND;
}

static int encode_request(
    test_io_t *io,
    uint32_t sequence,
    uint32_t session_id,
    uint16_t command_id,
    const uint8_t *body,
    uint16_t body_length)
{
    et_frame_t frame;
    et_message_t message;
    uint16_t payload_length;

    memset(&frame, 0, sizeof(frame));
    memset(&message, 0, sizeof(message));
    frame.message_type = ET_FRAME_TYPE_REQUEST;
    frame.sequence = sequence;
    frame.session_id = session_id;
    message.command_id = command_id;
    message.body = body;
    message.body_length = body_length;
    if ((et_message_encode(
             &message,
             frame.payload,
             sizeof(frame.payload),
             &payload_length) != 0) ||
        ((frame.payload_length = payload_length),
         et_frame_encode(
             &frame,
             io->rx,
             sizeof(io->rx),
             &io->rx_length) != 0)) {
        return -1;
    }
    io->rx_offset = 0u;
    return 0;
}

static int decode_response(
    const test_io_t *io,
    et_frame_t *frame,
    et_message_t *message)
{
    et_frame_parser_t parser;
    et_frame_parse_result_t result = ET_FRAME_PARSE_NONE;
    size_t index;

    et_frame_parser_init(&parser);
    for (index = 0u; index < io->tx_length; ++index) {
        result = et_frame_parser_push(&parser, io->tx[index], frame);
        if (result == ET_FRAME_PARSE_READY) {
            break;
        }
    }
    return ((result == ET_FRAME_PARSE_READY) &&
            (et_message_decode(
                 frame->payload,
                 frame->payload_length,
                 message) == 0))
        ? 0
        : -1;
}

static int run_protocol_until_idle(
    et_protocol_t *protocol,
    test_io_t *io)
{
    size_t iteration;

    for (iteration = 0u; iteration < 2000u; ++iteration) {
        (void)et_protocol_poll(protocol);
        if ((io->rx_offset == io->rx_length) &&
            (protocol->pending_response_offset >=
             protocol->last_response_length)) {
            return 0;
        }
    }
    return -1;
}

static int validate_protocol_behavior(void)
{
    static uint8_t large_body[2048];
    et_service_router_t router;
    et_service_descriptor_t descriptor;
    et_protocol_config_t config;
    et_protocol_t protocol;
    et_protocol_stats_t const *stats;
    et_frame_t response_frame;
    et_message_t response_message;
    test_service_t service;
    test_io_t io;
    uint32_t calls_before;
    size_t index;

    memset(&service, 0, sizeof(service));
    memset(&io, 0, sizeof(io));
    memset(&descriptor, 0, sizeof(descriptor));
    descriptor.context = &service;
    descriptor.handle = test_service_handle;
    et_service_router_init(&router);
    if (et_service_register(&router, &descriptor) != 0) {
        return -1;
    }

    memset(&config, 0, sizeof(config));
    config.session_open_command_id = 1u;
    config.services = &router;
    config.io.context = &io;
    config.io.read = test_read;
    config.io.write = test_write;
    if (et_protocol_init(&protocol, &config) != 0) {
        return -1;
    }

    if ((encode_request(
             &io,
             1u,
             0xa1b2c3d4u,
             1u,
             NULL,
             0u) != 0) ||
        (run_protocol_until_idle(&protocol, &io) != 0) ||
        (protocol.config.session_id != 0xa1b2c3d4u) ||
        (decode_response(
             &io,
             &response_frame,
             &response_message) != 0) ||
        (response_frame.session_id != 0xa1b2c3d4u) ||
        (response_message.status != ET_STATUS_OK)) {
        return -1;
    }

    for (index = 0u; index < sizeof(large_body); ++index) {
        large_body[index] = (uint8_t)(index & 0xffu);
    }
    io.tx_length = 0u;
    if ((encode_request(
             &io,
             2u,
             0xa1b2c3d4u,
             2u,
             large_body,
             (uint16_t)sizeof(large_body)) != 0) ||
        (run_protocol_until_idle(&protocol, &io) != 0) ||
        (et_protocol_rx_incomplete(&protocol) != 0) ||
        (decode_response(
             &io,
             &response_frame,
             &response_message) != 0) ||
        (response_message.body_length != sizeof(large_body)) ||
        (memcmp(
             response_message.body,
             large_body,
             sizeof(large_body)) != 0)) {
        return -1;
    }

    io.tx_length = 0u;
    if ((encode_request(
             &io,
             3u,
             0xa1b2c3d4u,
             3u,
             NULL,
             0u) != 0) ||
        (run_protocol_until_idle(&protocol, &io) != 0) ||
        (decode_response(
             &io,
             &response_frame,
             &response_message) != 0) ||
        (response_message.status != ET_STATUS_INVALID_PARAM) ||
        (response_message.body_length != 3u) ||
        (memcmp(response_message.body, "bad", 3u) != 0)) {
        return -1;
    }

    io.tx_length = 0u;
    io.max_write = 5u;
    calls_before = service.calls;
    if ((encode_request(
             &io,
             4u,
             0xa1b2c3d4u,
             4u,
             NULL,
             0u) != 0) ||
        (run_protocol_until_idle(&protocol, &io) != 0) ||
        (service.calls != calls_before + 1u)) {
        return -1;
    }
    io.tx_length = 0u;
    if ((io.rx_offset = 0u,
         run_protocol_until_idle(&protocol, &io) != 0) ||
        (service.calls != calls_before + 1u)) {
        return -1;
    }
    stats = et_protocol_stats(&protocol);
    if ((stats == NULL) || (stats->duplicate_requests != 1u)) {
        return -1;
    }
    return 0;
}

static int validate_encoded_frame(
    const uint8_t *encoded,
    size_t encoded_length,
    const et_frame_t *expected_frame,
    const et_message_t *expected_message)
{
    et_frame_parser_t parser;
    et_frame_t decoded_frame;
    et_message_t decoded_message;
    et_frame_parse_result_t result = ET_FRAME_PARSE_NONE;
    size_t index;

    et_frame_parser_init(&parser);
    for (index = 0u; index < encoded_length; ++index) {
        result = et_frame_parser_push(
            &parser,
            encoded[index],
            &decoded_frame);
    }
    if ((result != ET_FRAME_PARSE_READY) ||
        (decoded_frame.message_type != expected_frame->message_type) ||
        (decoded_frame.flags != expected_frame->flags) ||
        (decoded_frame.sequence != expected_frame->sequence) ||
        (decoded_frame.session_id != expected_frame->session_id) ||
        (et_message_decode(
             decoded_frame.payload,
             decoded_frame.payload_length,
             &decoded_message) != 0) ||
        (decoded_message.service_id != expected_message->service_id) ||
        (decoded_message.command_id != expected_message->command_id) ||
        (decoded_message.instance_id != expected_message->instance_id) ||
        (decoded_message.status != expected_message->status) ||
        (decoded_message.body_length != expected_message->body_length) ||
        ((decoded_message.body_length != 0u) &&
         (memcmp(
              decoded_message.body,
              expected_message->body,
              decoded_message.body_length) != 0))) {
        return -1;
    }
    return 0;
}

static int emit_vector(
    const char *name,
    et_frame_t *frame,
    const et_message_t *message)
{
    uint8_t encoded[ET_FRAME_MAX_SIZE];
    uint16_t payload_length;
    size_t encoded_length;
    size_t index;

    if ((et_message_encode(
             message,
             frame->payload,
             sizeof(frame->payload),
             &payload_length) != 0) ||
        ((frame->payload_length = payload_length),
         et_frame_encode(
             frame,
             encoded,
             sizeof(encoded),
             &encoded_length) != 0) ||
        (validate_encoded_frame(
             encoded,
             encoded_length,
             frame,
             message) != 0)) {
        return -1;
    }

    printf("%s=", name);
    for (index = 0u; index < encoded_length; ++index) {
        printf("%02x", encoded[index]);
    }
    printf("\n");
    return 0;
}

int main(void)
{
    static const uint8_t echo_body[] = {(uint8_t)'E', (uint8_t)'T'};
    et_frame_t frame;
    et_message_t message;

    memset(&frame, 0, sizeof(frame));
    memset(&message, 0, sizeof(message));
    frame.message_type = ET_FRAME_TYPE_REQUEST;
    frame.sequence = 1u;
    frame.session_id = 0xa1b2c3d4u;
    message.command_id = 1u;
    if (emit_vector(
            "framework_hello_request",
            &frame,
            &message) != 0) {
        return 1;
    }

    memset(&frame, 0, sizeof(frame));
    memset(&message, 0, sizeof(message));
    frame.message_type = ET_FRAME_TYPE_RESPONSE;
    frame.sequence = 2u;
    frame.session_id = 0x10203040u;
    message.command_id = 2u;
    message.body = echo_body;
    message.body_length = (uint16_t)sizeof(echo_body);
    if (emit_vector(
            "framework_echo_response",
            &frame,
            &message) != 0) {
        return 1;
    }
    return (validate_protocol_behavior() == 0) ? 0 : 2;
}
