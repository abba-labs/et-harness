#ifndef ET_CAN_WRAP_H
#define ET_CAN_WRAP_H

/** @file et_can_wrap.h @brief Chip-neutral, non-waiting CAN controller primitives. */
#include <stdint.h>
#include "et_wrap_status.h"

/** Logical controller identity from Capability; never an external CAN-box channel. */
typedef uint16_t et_can_id_t;

/** Actual time-quanta counts and prescaler; hardware minus-one encoding is private. */
typedef struct
{
    uint32_t prescaler;
    uint32_t segment1;
    uint32_t segment2;
    uint32_t sjw;
} et_can_bit_timing_t;

/** Arbitration and data-phase timing are independent, including when BRS is disabled. */
typedef struct
{
    et_can_bit_timing_t nominal;
    et_can_bit_timing_t data;
} et_can_timing_t;

/** Inclusive limits in the same physical units as et_can_timing_t. */
typedef struct
{
    et_can_bit_timing_t nominal_max;
    et_can_bit_timing_t data_max;
} et_can_timing_limits_t;

/** Immutable revision and endian identities read from the selected controller. */
typedef struct
{
    uint32_t revision;
    uint32_t endian;
} et_can_identity_t;

/** Independent core controls; all Boolean fields require exactly zero or one. */
typedef struct
{
    uint32_t fd_enabled;
    uint32_t brs_enabled;
    uint32_t automatic_retry;
    uint32_t tx_pause;
    uint32_t edge_filter;
    uint32_t protocol_exception;
    uint32_t tdc_enabled;
    uint32_t tdc_offset_cycles;
    uint32_t tdc_filter_cycles;
    uint32_t ram_watchdog_cycles;
} et_can_options_t;

/** Hardware limits in controller clock cycles, not PC polling or timeout budgets. */
typedef struct
{
    uint32_t tdc_offset_cycles;
    uint32_t tdc_filter_cycles;
    uint32_t ram_watchdog_cycles;
} et_can_option_limits_t;

et_wrap_status_t et_can_wrap_get_identity(et_can_id_t id, et_can_identity_t *identity);
et_wrap_status_t et_can_wrap_set_initializing(et_can_id_t id, uint8_t initializing);
et_wrap_status_t et_can_wrap_get_initializing(et_can_id_t id, uint8_t *initializing);
et_wrap_status_t et_can_wrap_get_timing_limits(et_can_id_t id, et_can_timing_limits_t *limits);
et_wrap_status_t et_can_wrap_set_timing(et_can_id_t id, const et_can_timing_t *timing);
et_wrap_status_t et_can_wrap_get_timing(et_can_id_t id, et_can_timing_t *timing);
et_wrap_status_t et_can_wrap_set_options(et_can_id_t id, const et_can_options_t *options);
et_wrap_status_t et_can_wrap_get_options(et_can_id_t id, et_can_options_t *options);
et_wrap_status_t et_can_wrap_get_option_limits(et_can_id_t id, et_can_option_limits_t *limits);

/** Message RAM byte offsets and counts; never physical CPU addresses.
 * Disabled count-bearing regions use count zero. Dedicated RX storage has no
 * hardware count field and reserves the published rx_buffer_count maximum.
 * Payload capacities are bytes; queue and overwrite fields are Boolean.
 */
typedef struct
{
    uint32_t std_offset;
    uint32_t std_count;
    uint32_t ext_offset;
    uint32_t ext_count;
    uint32_t tx_offset;
    uint32_t tx_buffer_count;
    uint32_t tx_fifo_count;
    uint32_t tx_queue;
    uint32_t tx_payload_bytes;
    uint32_t event_offset;
    uint32_t event_count;
    uint32_t event_watermark;
    uint32_t rx0_offset;
    uint32_t rx0_count;
    uint32_t rx0_watermark;
    uint32_t rx0_overwrite;
    uint32_t rx1_offset;
    uint32_t rx1_count;
    uint32_t rx1_watermark;
    uint32_t rx1_overwrite;
    uint32_t rx_buffer_offset;
    uint32_t rx_buffer_payload_bytes;
    uint32_t rx0_payload_bytes;
    uint32_t rx1_payload_bytes;
} et_can_ram_layout_t;

/** Architectural region maxima, not a default test layout. */
typedef struct
{
    uint32_t ram_bytes;
    uint32_t std_count;
    uint32_t ext_count;
    uint32_t tx_count;
    uint32_t rx_fifo_count;
    uint32_t event_count;
    uint32_t rx_buffer_count;
} et_can_ram_limits_t;

et_wrap_status_t et_can_wrap_get_ram_limits(et_can_id_t id, et_can_ram_limits_t *limits);
et_wrap_status_t et_can_wrap_set_ram_layout(et_can_id_t id, const et_can_ram_layout_t *layout);
et_wrap_status_t et_can_wrap_get_ram_layout(et_can_id_t id, et_can_ram_layout_t *layout);

/** Stable timestamp sources; not raw register selectors. */
typedef enum
{
    ET_CAN_TIMESTAMP_DISABLED = 0u,
    ET_CAN_TIMESTAMP_INTERNAL = 1u,
    ET_CAN_TIMESTAMP_EXTERNAL = 2u,
    ET_CAN_TIMESTAMP_SOURCE_COUNT
} et_can_timestamp_source_t;

/** A timeout may run continuously or be gated by one hardware FIFO. */
typedef enum
{
    ET_CAN_TIMEOUT_CONTINUOUS = 0u,
    ET_CAN_TIMEOUT_TX_EVENT = 1u,
    ET_CAN_TIMEOUT_RX0 = 2u,
    ET_CAN_TIMEOUT_RX1 = 3u,
    ET_CAN_TIMEOUT_SOURCE_COUNT
} et_can_timeout_source_t;

/** Stable global non-matching-frame policy, independent of individual ID filters. */
typedef enum
{
    ET_CAN_UNMATCHED_RX0 = 0u,
    ET_CAN_UNMATCHED_RX1 = 1u,
    ET_CAN_UNMATCHED_REJECT = 2u,
    ET_CAN_UNMATCHED_POLICY_COUNT
} et_can_unmatched_policy_t;

/** Loopback controls are separate from INIT; disabled exits MON loopback isolation. */
typedef enum
{
    ET_CAN_LOOPBACK_DISABLED = 0u,
    ET_CAN_LOOPBACK_INTERNAL = 1u,
    ET_CAN_LOOPBACK_EXTERNAL = 2u
} et_can_loopback_t;

/** One complete existing Driver configuration group, with explicit physical timer units. */
typedef struct
{
    uint32_t monitor;
    uint32_t restricted;
    uint32_t timestamp_divisor;
    uint32_t timestamp_source;
    uint32_t timeout_source;
    uint32_t timeout_period;
    uint32_t timeout_enabled;
    uint32_t reject_remote_ext;
    uint32_t reject_remote_std;
    uint32_t unmatched_ext;
    uint32_t unmatched_std;
} et_can_bus_config_t;

/** Timer count limits; source selectors are the public enums above. */
typedef struct
{
    uint32_t timestamp_divisor;
    uint32_t timeout_period;
} et_can_bus_limits_t;

et_wrap_status_t et_can_wrap_set_bus_config(et_can_id_t id, const et_can_bus_config_t *config);
et_wrap_status_t et_can_wrap_get_bus_config(et_can_id_t id, et_can_bus_config_t *config);
et_wrap_status_t et_can_wrap_get_bus_limits(et_can_id_t id, et_can_bus_limits_t *limits);
et_wrap_status_t et_can_wrap_set_loopback(et_can_id_t id, et_can_loopback_t mode);
et_wrap_status_t et_can_wrap_get_loopback(et_can_id_t id, et_can_loopback_t *mode);

/** CAN-FD protocol maximum payload and four-bit DLC; these are not chip RAM capacities. */
#define ET_CAN_FRAME_DATA_BYTES 64u
#define ET_CAN_FRAME_DLC_MAX 15u

/** Public frame flags, independent of physical Message RAM bit positions. */
typedef enum
{
    ET_CAN_FRAME_EXTENDED = 1u,
    ET_CAN_FRAME_REMOTE = 2u,
    ET_CAN_FRAME_FD = 4u,
    ET_CAN_FRAME_BRS = 8u,
    ET_CAN_FRAME_ESI = 16u,
    ET_CAN_FRAME_STORE_EVENT = 32u,
    ET_CAN_FRAME_CAPTURE_TIME = 64u
} et_can_frame_flag_t;

/** Complete transmit frame. Valid data length is derived from DLC, FD and Remote. */
typedef struct
{
    uint32_t identifier;
    uint32_t flags;
    uint32_t dlc;
    uint32_t marker;
    uint8_t data[ET_CAN_FRAME_DATA_BYTES];
} et_can_tx_frame_t;

/** Actual TX requests, completions, cancellations and FIFO/Queue indices. */
typedef struct
{
    uint32_t pending;
    uint32_t completed;
    uint32_t cancelled;
    uint32_t free_count;
    uint32_t get_index;
    uint32_t put_index;
    uint32_t full;
} et_can_tx_status_t;

/** Actual receive FIFO state; querying does not acknowledge or clear lost status. */
typedef struct
{
    uint32_t fill;
    uint32_t get_index;
    uint32_t put_index;
    uint32_t full;
    uint32_t lost;
} et_can_rx_fifo_status_t;

/** Stable receive storage selector, separate from the buffer index. */
typedef enum
{
    ET_CAN_RX_BUFFER = 0u,
    ET_CAN_RX_FIFO0 = 1u,
    ET_CAN_RX_FIFO1 = 2u
} et_can_rx_source_t;

/** A received element and its observed storage index. data_length reflects slot truncation. */
typedef struct
{
    uint32_t identifier;
    uint32_t flags;
    uint32_t dlc;
    uint32_t timestamp;
    uint32_t filter_index;
    uint32_t nonmatching;
    uint32_t data_length;
    uint32_t index;
    uint8_t data[ET_CAN_FRAME_DATA_BYTES];
} et_can_rx_frame_t;

/** Independent new-data bitmaps for dedicated RX buffers, not PC observation state. */
typedef struct
{
    uint32_t low;
    uint32_t high;
} et_can_rx_buffer_status_t;

et_wrap_status_t et_can_wrap_write_tx(et_can_id_t id, uint32_t index,
                                      const et_can_tx_frame_t *frame);
et_wrap_status_t et_can_wrap_request_tx(et_can_id_t id, uint32_t mask);
et_wrap_status_t et_can_wrap_get_tx_status(et_can_id_t id, et_can_tx_status_t *status);
et_wrap_status_t et_can_wrap_get_rx_fifo_status(et_can_id_t id, uint32_t fifo,
                                                et_can_rx_fifo_status_t *status);
et_wrap_status_t et_can_wrap_read_rx(et_can_id_t id, et_can_rx_source_t source, uint32_t index,
                                     et_can_rx_frame_t *frame);
et_wrap_status_t et_can_wrap_ack_rx_fifo(et_can_id_t id, uint32_t fifo, uint32_t index);
et_wrap_status_t et_can_wrap_get_rx_buffer_status(et_can_id_t id,
                                                  et_can_rx_buffer_status_t *status);
et_wrap_status_t et_can_wrap_ack_rx_buffers(et_can_id_t id,
                                            const et_can_rx_buffer_status_t *status);

/** Public matching operations; unsupported format/type pairs are rejected. */
typedef enum
{
    ET_CAN_FILTER_RANGE = 0u,
    ET_CAN_FILTER_DUAL = 1u,
    ET_CAN_FILTER_MASK = 2u,
    ET_CAN_FILTER_RANGE_NO_MASK = 3u,
    ET_CAN_FILTER_DISABLED = 4u
} et_can_filter_type_t;

/** Acceptance destination/event, not a hardware register encoding. */
typedef enum
{
    ET_CAN_FILTER_ACTION_DISABLED = 0u,
    ET_CAN_FILTER_ACTION_FIFO0 = 1u,
    ET_CAN_FILTER_ACTION_FIFO1 = 2u,
    ET_CAN_FILTER_ACTION_REJECT = 3u,
    ET_CAN_FILTER_ACTION_PRIORITY = 4u,
    ET_CAN_FILTER_ACTION_PRIORITY_FIFO0 = 5u,
    ET_CAN_FILTER_ACTION_PRIORITY_FIFO1 = 6u,
    ET_CAN_FILTER_ACTION_BUFFER = 7u
} et_can_filter_action_t;

/** ID2 is upper bound/second ID/mask. BUFFER uses ID1 and buffer_index only;
 * type must be RANGE and ID2 zero because matching is exact and type is ignored.
 * Timestamp/debug-buffer encodings are not part of this basic filter operation.
 */
typedef struct
{
    uint32_t type;
    uint32_t action;
    uint32_t id1;
    uint32_t id2;
    uint32_t buffer_index;
} et_can_filter_t;

et_wrap_status_t et_can_wrap_set_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        const et_can_filter_t *filter);
et_wrap_status_t et_can_wrap_get_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        et_can_filter_t *filter);
et_wrap_status_t et_can_wrap_set_extended_mask(et_can_id_t id, uint32_t mask);
et_wrap_status_t et_can_wrap_get_extended_mask(et_can_id_t id, uint32_t *mask);

#endif
