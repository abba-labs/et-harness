#include "et_protocol.h"

/**
 * @file et_protocol.c
 * @brief Non-blocking request engine with exact duplicate-response replay.
 */

#include <string.h>

#define ET_PROTOCOL_REQUEST_FLAGS_HASH_SHIFT 16u

#include "et_message.h"

/**
 * @brief Report whether an encoded response still has bytes waiting for transport TX.
 *
 * @param[in] protocol Protocol engine whose replay buffer and TX offset are queried.
 *
 * @note This is a read-only software-state query. It does not call the transport or change replay
 *       metadata.
 *
 * @return Nonzero when unsent response bytes remain, otherwise zero.
 */
static int response_pending(const et_protocol_t *protocol)
{
    return (protocol != NULL) && (protocol->last_response_valid != 0u) &&
           (protocol->pending_response_offset < protocol->last_response_length);
}

/**
 * @brief Dispatch one decoded request and encode its complete replayable ET-Frame response.
 *
 * @param[in,out] protocol Protocol engine that owns Service routing, work frame and TX storage.
 * @param[in] request_sequence Sequence value copied from the request frame.
 * @param[in] response_session_id Session identity to publish in the response frame.
 * @param[in] request Decoded Service request to dispatch.
 * @param[out] response_status Stable Service/protocol status encoded in the response.
 *
 * @note The Service is executed exactly once in this function. The resulting response is fully
 *       encoded into protocol-owned TX storage so later short writes or duplicate requests replay
 *       bytes instead of re-executing the command.
 *
 * @return Encoded ET-Frame length when a response is built successfully, otherwise zero.
 */
static size_t build_response(et_protocol_t *protocol, uint32_t request_sequence,
                             uint32_t response_session_id, const et_message_t *request,
                             uint16_t *response_status)
{
    et_frame_t *response = &protocol->work_frame;
    et_message_t response_message;
    uint8_t *body = &response->payload[ET_MESSAGE_HEADER_SIZE];
    uint16_t body_capacity = (uint16_t)(sizeof(response->payload) - ET_MESSAGE_HEADER_SIZE);
    uint16_t body_length = 0u;
    uint16_t status;
    uint16_t payload_length = 0u;
    size_t encoded_length = 0u;

    /* Phase 1: Execute the selected Service once and bound the returned response body. */
    status =
        et_service_dispatch(protocol->config.services, request, body, body_capacity, &body_length);

    if (body_length > body_capacity)
    {
        status = ET_STATUS_INTERNAL_ERROR;
        body_length = 0u;
        ++protocol->stats.parse_errors;
    }

    /* Phase 2: Encode the Service message, falling back to an empty INTERNAL_ERROR body if needed. */
    response_message.service_id = request->service_id;
    response_message.command_id = request->command_id;
    response_message.instance_id = request->instance_id;
    response_message.status = status;
    response_message.body = body;
    response_message.body_length = body_length;

    if (et_message_encode(&response_message, response->payload, sizeof(response->payload),
                          &payload_length) != 0)
    {
        response_message.status = ET_STATUS_INTERNAL_ERROR;
        response_message.body = NULL;
        response_message.body_length = 0u;
        status = ET_STATUS_INTERNAL_ERROR;

        if (et_message_encode(&response_message, response->payload, sizeof(response->payload),
                              &payload_length) != 0)
        {
            return 0u;
        }

        ++protocol->stats.parse_errors;
    }

    /* Phase 3: Wrap the encoded Service message in ET-Frame identity and seal it for replay. */
    response->message_type = ET_FRAME_TYPE_RESPONSE;
    response->flags = 0u;
    response->sequence = request_sequence;
    response->session_id = response_session_id;
    response->payload_length = payload_length;

    if (et_frame_encode(response, protocol->tx_frame, sizeof(protocol->tx_frame),
                        &encoded_length) != 0)
    {
        return 0u;
    }

    *response_status = status;

    return encoded_length;
}

/**
 * @brief Advance transmission of the cached response by as many bytes as the transport accepts.
 *
 * @param[in,out] protocol Protocol engine that owns replay bytes and pending TX offset.
 *
 * @note Short transport writes are normal and preserve the exact encoded response for a later poll.
 *       A transport that reports writing beyond the offered length is clamped and recorded as error.
 */
static void flush_pending_response(et_protocol_t *protocol)
{
    size_t remaining;
    size_t written;

    if (!response_pending(protocol))
    {
        return;
    }

    remaining = protocol->last_response_length - protocol->pending_response_offset;
    /* Short transport writes are retained and resumed on a later poll. */
    written = protocol->config.io.write(protocol->config.io.context,
                                        &protocol->tx_frame[protocol->pending_response_offset],
                                        remaining);

    if (written > remaining)
    {
        written = remaining;
        ++protocol->stats.parse_errors;
    }

    protocol->pending_response_offset += written;

    if (protocol->pending_response_offset == protocol->last_response_length)
    {
        ++protocol->stats.tx_frames;
    }
}

/**
 * @brief Recognize the Framework request that is allowed to establish a protocol session.
 *
 * @param[in] protocol Protocol engine containing the configured session-open identity.
 * @param[in] request Decoded Service request to classify.
 *
 * @note The check compares only stable Service and Command identities and does not mutate session
 *       state or dispatch the request.
 *
 * @return Nonzero when request is the configured session-open command, otherwise zero.
 */
static int is_session_open_request(const et_protocol_t *protocol, const et_message_t *request)
{
    return ((request->service_id == protocol->config.session_open_service_id) &&
            (request->command_id == protocol->config.session_open_command_id));
}

/**
 * @brief Validate one complete request frame, enforce replay/session semantics and prepare response TX.
 *
 * @param[in,out] protocol Protocol engine whose session, replay metadata and statistics are updated.
 * @param[in] frame Complete CRC-valid ET-Frame produced by the streaming parser.
 *
 * @note Duplicate request identity is resolved before Service decoding so an exact retry replays the
 *       cached response and never executes the Service twice. Reused identity with changed payload is
 *       rejected as a parse error.
 */
static void handle_frame(et_protocol_t *protocol, const et_frame_t *frame)
{
    et_message_t request;
    uint32_t request_fingerprint;
    uint32_t response_session_id;
    size_t response_length;
    uint16_t response_status;
    int session_open_request;

    /* Phase 1: Reject non-request frames/flags and fingerprint request content for exact replay. */
    ++protocol->stats.rx_frames;

    if (frame->message_type != ET_FRAME_TYPE_REQUEST)
    {
        return;
    }

    if (frame->flags != 0u)
    {
        ++protocol->stats.parse_errors;

        return;
    }

    request_fingerprint = et_frame_crc32(frame->payload, frame->payload_length) ^
                          ((uint32_t)frame->flags << ET_PROTOCOL_REQUEST_FLAGS_HASH_SHIFT);

    /* Phase 2: Resolve duplicate identity before any command can be dispatched again. */
    if ((protocol->last_response_valid != 0u) &&
        (frame->sequence == protocol->last_request_sequence) &&
        (frame->session_id == protocol->last_request_session_id))
    {
        if (request_fingerprint == protocol->last_request_fingerprint)
        {
            if (protocol->pending_response_offset >= protocol->last_response_length)
            {
                protocol->pending_response_offset = 0u;
            }

            flush_pending_response(protocol);
            ++protocol->stats.duplicate_requests;
        }
        else
        {
            ++protocol->stats.parse_errors;
        }

        return;
    }

    /* Phase 3: Decode the Service request and establish the response session identity. */
    if (et_message_decode(frame->payload, frame->payload_length, &request) != 0)
    {
        ++protocol->stats.parse_errors;

        return;
    }

    session_open_request = is_session_open_request(protocol, &request);

    if (session_open_request)
    {
        if (frame->session_id == 0u)
        {
            ++protocol->stats.parse_errors;

            return;
        }

        response_session_id = frame->session_id;
    }
    else
    {
        if ((protocol->config.session_id == 0u) ||
            (frame->session_id != protocol->config.session_id))
        {
            return;
        }

        response_session_id = protocol->config.session_id;
    }

    /* Phase 4: Execute the command once and produce a complete replayable encoded response. */
    response_length =
        build_response(protocol, frame->sequence, response_session_id, &request, &response_status);

    if (response_length == 0u)
    {
        return;
    }

    /* Phase 5: Commit replay/session metadata before the first potentially short transport write. */
    protocol->last_request_sequence = frame->sequence;
    protocol->last_request_session_id = frame->session_id;
    protocol->last_request_fingerprint = request_fingerprint;
    protocol->last_response_length = response_length;
    protocol->pending_response_offset = 0u;
    protocol->last_response_valid = 1u;

    if (session_open_request && (response_status == ET_STATUS_OK))
    {
        protocol->config.session_id = frame->session_id;
    }

    flush_pending_response(protocol);
}

/**
 * @brief Initialize protocol parser, session configuration and transport callbacks.
 *
 * @param[out] protocol Protocol engine to initialize.
 * @param[in] config Service router, session identity and non-blocking IO callbacks.
 *
 * @note Initialization clears replay/statistics/parser state and copies callback configuration only.
 *       It does not read transport bytes or execute any Service command.
 *
 * @return 0 when the required Service router and IO callbacks are valid.
 * @return -1 when required pointers or callbacks are missing.
 */
int et_protocol_init(et_protocol_t *protocol, const et_protocol_config_t *config)
{
    if ((protocol == NULL) || (config == NULL) || (config->services == NULL) ||
        (config->io.read == NULL) || (config->io.write == NULL))
    {
        return -1;
    }

    (void)memset(protocol, 0, sizeof(*protocol));
    protocol->config = *config;
    et_frame_parser_init(&protocol->parser);

    return 0;
}

/**
 * @brief Advance pending TX, buffered-frame parsing, transport RX and request dispatch once.
 *
 * @param[in,out] protocol Protocol engine to poll from cooperative thread context.
 *
 * @note A pending response always blocks new request execution until its exact bytes are fully sent.
 *       Parser trailing bytes are drained before asking the transport for more input so progress does
 *       not depend on a future UART byte.
 *
 * @return Number of newly read chunk bytes consumed by the streaming parser during this poll.
 */
size_t et_protocol_poll(et_protocol_t *protocol)
{
    size_t consumed = 0u;
    et_frame_parse_result_t result;

    /* Phase 1: Finish cached response transmission before accepting another command. */
    if (protocol == NULL)
    {
        return 0u;
    }

    flush_pending_response(protocol);

    if (response_pending(protocol))
    {
        return 0u;
    }

    /* Phase 2: Drain a complete trailing frame already buffered by the previous parser pass. */
    result = et_frame_parser_drain(&protocol->parser, &protocol->work_frame);

    if (result == ET_FRAME_PARSE_READY)
    {
        handle_frame(protocol, &protocol->work_frame);

        return 0u;
    }

    if (result == ET_FRAME_PARSE_DROPPED)
    {
        ++protocol->stats.parse_errors;
    }

    /* Phase 3: Refill the bounded RX chunk only after every previous chunk byte was consumed. */
    if (protocol->rx_chunk_offset >= protocol->rx_chunk_length)
    {
        protocol->rx_chunk_length = protocol->config.io.read(
            protocol->config.io.context, protocol->rx_chunk, sizeof(protocol->rx_chunk));

        if (protocol->rx_chunk_length > sizeof(protocol->rx_chunk))
        {
            protocol->rx_chunk_length = sizeof(protocol->rx_chunk);
            ++protocol->stats.parse_errors;
        }

        protocol->rx_chunk_offset = 0u;
    }

    /* Phase 4: Feed bytes in stream order and stop when a newly built response needs TX service. */
    while (protocol->rx_chunk_offset < protocol->rx_chunk_length)
    {
        result =
            et_frame_parser_push(&protocol->parser, protocol->rx_chunk[protocol->rx_chunk_offset],
                                 &protocol->work_frame);
        ++protocol->rx_chunk_offset;
        ++consumed;

        if (result == ET_FRAME_PARSE_READY)
        {
            handle_frame(protocol, &protocol->work_frame);

            if (response_pending(protocol))
            {
                break;
            }
        }
        else if (result == ET_FRAME_PARSE_DROPPED)
        {
            ++protocol->stats.parse_errors;
        }
    }

    /* Phase 5: Release fully consumed chunk bookkeeping while preserving any parser partial frame. */
    if (protocol->rx_chunk_offset >= protocol->rx_chunk_length)
    {
        protocol->rx_chunk_offset = 0u;
        protocol->rx_chunk_length = 0u;
    }

    return consumed;
}

/**
 * @brief Discard only partial receive state after an external idle/truncation decision.
 *
 * @param[in,out] protocol Protocol engine whose parser and current RX chunk are reset.
 *
 * @note Replay metadata, session identity, statistics and pending response state are intentionally
 *       preserved. No transport or peripheral hardware is reset.
 */
void et_protocol_reset_rx(et_protocol_t *protocol)
{
    if (protocol != NULL)
    {
        et_frame_parser_init(&protocol->parser);
        protocol->rx_chunk_offset = 0u;
        protocol->rx_chunk_length = 0u;
    }
}

/**
 * @brief Report whether the streaming parser currently owns a partial frame.
 *
 * @param[in] protocol Protocol engine whose parser occupancy is queried.
 *
 * @note This is a read-only parser-state query and does not consume or resynchronize bytes.
 *
 * @return Nonzero when parser length is nonzero, otherwise zero.
 */
int et_protocol_rx_incomplete(const et_protocol_t *protocol)
{
    return ((protocol != NULL) && (protocol->parser.length != 0u));
}

/**
 * @brief Return immutable protocol reliability counters.
 *
 * @param[in] protocol Protocol engine whose statistics are requested.
 *
 * @note The returned pointer aliases protocol-owned storage and no parser, session or transport state
 *       is changed.
 *
 * @return Pointer to protocol statistics, or NULL when protocol is NULL.
 */
const et_protocol_stats_t *et_protocol_stats(const et_protocol_t *protocol)
{
    return (protocol == NULL) ? NULL : &protocol->stats;
}
