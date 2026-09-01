#ifndef ET_PROTOCOL_H
#define ET_PROTOCOL_H

/**
 * @file et_protocol.h
 * @brief Non-blocking ET-Frame request/response transaction engine.
 *
 * Protocol owns framing, session/sequence checks, duplicate replay and partial
 * transport progress. It delegates decoded commands to Service Router.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_frame.h"
#include "et_service_router.h"

typedef size_t (*et_protocol_read_fn)(void *context, uint8_t *data, size_t capacity);
/** Write up to length bytes and return the number accepted by the transport. */
typedef size_t (*et_protocol_write_fn)(void *context, const uint8_t *data, size_t length);

/*
 * read() and write() may complete fewer bytes than requested. Returning zero
 * means no progress is currently possible; the protocol retries later.
 */
typedef struct
{
    void *context;              /**< Transport-owned context. */
    et_protocol_read_fn read;   /**< Required non-blocking receive callback. */
    et_protocol_write_fn write; /**< Required non-blocking transmit callback. */
} et_protocol_io_t;

/** Monotonic protocol facts reported by Framework Service. */
typedef struct
{
    uint32_t rx_frames;          /**< Valid request frames accepted. */
    uint32_t tx_frames;          /**< Complete response frames transmitted. */
    uint32_t parse_errors;       /**< Dropped malformed or CRC-invalid frames. */
    uint32_t duplicate_requests; /**< Requests answered from replay cache. */
} et_protocol_stats_t;

typedef struct
{
    uint32_t session_id;              /**< Session required after open. */
    uint16_t session_open_service_id; /**< Service allowed before session match. */
    uint16_t session_open_command_id; /**< Command allowed before session match. */
    et_service_router_t *services;    /**< Initialized Service registry. */
    et_protocol_io_t io;              /**< Non-blocking transport callbacks. */
} et_protocol_config_t;

typedef struct
{
    et_protocol_config_t config;
    et_frame_parser_t parser;
    et_frame_t work_frame;
    et_protocol_stats_t stats;
    uint8_t rx_chunk[ET_TEST_PROTOCOL_RX_CHUNK_SIZE];
    uint8_t tx_frame[ET_FRAME_MAX_SIZE];
    size_t rx_chunk_length;            /**< Valid bytes in the current I/O chunk. */
    size_t rx_chunk_offset;            /**< Next byte consumed from the chunk. */
    uint32_t last_request_sequence;    /**< Identity of replay-cached request. */
    uint32_t last_request_session_id;  /**< Session of replay-cached request. */
    uint32_t last_request_fingerprint; /**< Payload fingerprint for duplicate safety. */
    size_t last_response_length;       /**< Valid bytes in cached response. */
    size_t pending_response_offset;    /**< Next cached response byte to transmit. */
    uint8_t last_response_valid;       /**< Cached response may be replayed. */
} et_protocol_t;

/** Initialize a stopped transaction engine over supplied transport and router. */
int et_protocol_init(et_protocol_t *protocol, const et_protocol_config_t *config);
/** Make one bounded progress pass; return total transport bytes moved. */
size_t et_protocol_poll(et_protocol_t *protocol);
/** Drop only receive parser/chunk state; replay state remains intact. */
void et_protocol_reset_rx(et_protocol_t *protocol);
/** Report whether an incomplete frame or receive chunk is buffered. */
int et_protocol_rx_incomplete(const et_protocol_t *protocol);
/** Return read-only cumulative protocol facts. */
const et_protocol_stats_t *et_protocol_stats(const et_protocol_t *protocol);

#endif
