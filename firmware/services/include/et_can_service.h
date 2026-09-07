#ifndef ET_CAN_SERVICE_H
#define ET_CAN_SERVICE_H

/** @file et_can_service.h @brief CAN command envelope; no chip or bus defaults. */
#include "et_service_router.h"
#include "et_can_wrap.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */

/** Public CAN Service identity, independent of controller and external box identity. */
#define ET_CAN_SERVICE_ID 0x010Cu
/** Request body has one instance byte followed by little-endian unsigned words. */
#define ET_CAN_REQUEST_PREFIX_BYTES 1u
#define ET_CAN_WIRE_WORD_BYTES 4u
#define ET_CAN_IDENTITY_WORDS 2u
#define ET_CAN_PHASE_WORDS 4u
#define ET_CAN_TIMING_WORDS 8u
#define ET_CAN_OPTIONS_WORDS 10u
#define ET_CAN_OPTION_LIMIT_WORDS 3u
/** Message RAM configuration has 24 named u32 fields, limits have seven. */
#define ET_CAN_RAM_LAYOUT_WORDS 24u
#define ET_CAN_RAM_LIMIT_WORDS 7u
/** Eleven existing Driver bus controls; independent count limits use two words. */
#define ET_CAN_BUS_CONFIG_WORDS 11u
#define ET_CAN_BUS_LIMIT_WORDS 2u
#define ET_CAN_BUS_LIMIT_TIMESTAMP 0u
#define ET_CAN_BUS_LIMIT_TIMEOUT 1u
/** Fixed frame envelopes: five TX words plus 64 bytes; eight RX words plus 64 bytes. */
#define ET_CAN_TX_WRITE_WORDS 21u
#define ET_CAN_RX_FRAME_WORDS 24u
#define ET_CAN_TX_STATUS_WORDS 7u
#define ET_CAN_TX_EVENT_STATUS_WORDS 5u
#define ET_CAN_TX_EVENT_WORDS 7u
/** Explicit event interpretation appends validity and TSU metadata to the old seven words. */
typedef enum
{
    ET_CAN_EVENT_INTERNAL_TIMESTAMP_VALID = ET_CAN_TX_EVENT_WORDS,
    ET_CAN_EVENT_TSU_CAPTURED,
    ET_CAN_EVENT_TSU_POINTER,
    ET_CAN_EVENT_DETAILS_WORDS
} et_can_event_details_word_t;
typedef enum
{
    ET_CAN_EVENT_FORMAT_MARKER_BITS = 0u,
    ET_CAN_EVENT_FORMAT_TSU_ENABLED,
    ET_CAN_EVENT_FORMAT_WORDS
} et_can_event_format_word_t;
/** TSU wire fields are logical values, not register positions. */
typedef enum
{
    ET_CAN_TSU_ENABLED = 0u,
    ET_CAN_TSU_EXTERNAL,
    ET_CAN_TSU_SOF,
    ET_CAN_TSU_DIVISOR,
    ET_CAN_TSU_CONFIG_WORDS
} et_can_tsu_config_word_t;
typedef enum
{
    ET_CAN_TSU_SLOTS = 0u,
    ET_CAN_TSU_INTERNAL_SUPPORT,
    ET_CAN_TSU_SOF_SUPPORT,
    ET_CAN_TSU_LIMITS_WORDS
} et_can_tsu_limits_word_t;
typedef enum
{
    ET_CAN_TSU_NEW = 0u,
    ET_CAN_TSU_LOST,
    ET_CAN_TSU_FLAGS_WORDS
} et_can_tsu_flags_word_t;
#define ET_CAN_RX_FIFO_STATUS_WORDS 5u
/** DMU queue totals followed by the hardware counter modulus. */
typedef enum
{
    ET_CAN_DMU_TX_ENQUEUED = 0u,
    ET_CAN_DMU_RX0_DEQUEUED,
    ET_CAN_DMU_RX1_DEQUEUED,
    ET_CAN_DMU_TX_EVENT_DEQUEUED,
    ET_CAN_DMU_COUNTER_MODULUS,
    ET_CAN_DMU_COUNTER_WORDS
} et_can_dmu_counter_word_t;
typedef enum
{
    ET_CAN_DMU_STATUS_ERRORS = 0u,
    ET_CAN_DMU_STATUS_ENABLED,
    ET_CAN_DMU_STATUS_TRANSFER_TIMESTAMP,
    ET_CAN_DMU_STATUS_WORDS
} et_can_dmu_status_word_t;
/** Image envelope is a byte count plus fixed CPU bytes; RX prepends a FIFO selector. */
#define ET_CAN_DMU_IMAGE_ENVELOPE_WORDS (1u + ET_CAN_DMU_IMAGE_WORDS)
#define ET_CAN_DMU_RX_IMAGE_REQUEST_WORDS (1u + ET_CAN_DMU_IMAGE_ENVELOPE_WORDS)
typedef enum
{
    ET_CAN_DMU_RX_INTERNAL_VALID = ET_CAN_RX_FRAME_WORDS,
    ET_CAN_DMU_RX_TSU_CAPTURED,
    ET_CAN_DMU_RX_TSU_POINTER,
    ET_CAN_DMU_RX_TRANSFERRED_VALID,
    ET_CAN_DMU_RX_TRANSFERRED_TIMESTAMP,
    ET_CAN_DMU_RX_IMAGE_RESPONSE_WORDS
} et_can_dmu_rx_image_word_t;
typedef enum
{
    ET_CAN_DMU_EVENT_TRANSFERRED_VALID = ET_CAN_EVENT_DETAILS_WORDS,
    ET_CAN_DMU_EVENT_TRANSFERRED_TIMESTAMP,
    ET_CAN_DMU_EVENT_IMAGE_RESPONSE_WORDS
} et_can_dmu_event_image_word_t;
/** Counter reload response contains real reads rather than a configured TOP value. */
typedef enum
{
    ET_CAN_COUNTER_RELOAD_BEFORE = 0u,
    ET_CAN_COUNTER_RELOAD_AFTER,
    ET_CAN_COUNTER_RELOAD_WORDS
} et_can_counter_reload_word_t;
/** Single hardware RAM watchdog snapshot, not a reload or latency measurement. */
typedef enum
{
    ET_CAN_RAM_WATCHDOG_LIMIT = 0u,
    ET_CAN_RAM_WATCHDOG_VALUE,
    ET_CAN_RAM_WATCHDOG_WORDS
} et_can_ram_watchdog_word_t;
#define ET_CAN_RX_SELECT_WORDS 2u
#define ET_CAN_RX_BITMAP_WORDS 2u
#define ET_CAN_RX_SELECT_SOURCE 0u
#define ET_CAN_RX_SELECT_INDEX 1u
#define ET_CAN_RX_BITMAP_LOW 0u
#define ET_CAN_RX_BITMAP_HIGH 1u
/** Two-word IRQ controls carry a source mask plus a Boolean, line or subset. */
#define ET_CAN_IRQ_CONTROL_WORDS 2u
/** RAM access selector carries offset/count/direction, followed by a fixed 64-word payload. */
typedef enum
{
    ET_CAN_RAM_ACCESS_OFFSET = 0u,
    ET_CAN_RAM_ACCESS_COUNT = 1u,
    ET_CAN_RAM_ACCESS_DESCENDING = 2u,
    ET_CAN_RAM_ACCESS_SELECT_WORDS
} et_can_ram_access_word_t;
#define ET_CAN_RAM_ACCESS_WRITE_WORDS (ET_CAN_RAM_ACCESS_SELECT_WORDS + ET_CAN_RAM_ACCESS_WORDS)
/** Public tx_field word order; DATA marks the start of 64 payload bytes. */
typedef enum
{
    ET_CAN_TX_FIELD_INDEX = 0u,
    ET_CAN_TX_FIELD_IDENTIFIER = 1u,
    ET_CAN_TX_FIELD_FLAGS = 2u,
    ET_CAN_TX_FIELD_DLC = 3u,
    ET_CAN_TX_FIELD_MARKER = 4u,
    ET_CAN_TX_FIELD_DATA = 5u,
} et_can_tx_field_word_t;

/** Public rx_field word order; DATA marks the start of 64 payload bytes. */
typedef enum
{
    ET_CAN_RX_FIELD_IDENTIFIER = 0u,
    ET_CAN_RX_FIELD_FLAGS = 1u,
    ET_CAN_RX_FIELD_DLC = 2u,
    ET_CAN_RX_FIELD_TIMESTAMP = 3u,
    ET_CAN_RX_FIELD_FILTER_INDEX = 4u,
    ET_CAN_RX_FIELD_NONMATCHING = 5u,
    ET_CAN_RX_FIELD_DATA_LENGTH = 6u,
    ET_CAN_RX_FIELD_INDEX = 7u,
    ET_CAN_RX_FIELD_DATA = 8u,
} et_can_rx_field_word_t;

/** Public TX request/completion/FIFO status word order. */
typedef enum
{
    ET_CAN_TX_STATUS_PENDING = 0u,
    ET_CAN_TX_STATUS_COMPLETED = 1u,
    ET_CAN_TX_STATUS_CANCELLED = 2u,
    ET_CAN_TX_STATUS_FREE_COUNT = 3u,
    ET_CAN_TX_STATUS_GET_INDEX = 4u,
    ET_CAN_TX_STATUS_PUT_INDEX = 5u,
    ET_CAN_TX_STATUS_FULL = 6u,
} et_can_tx_status_word_t;

/** Public TX Event FIFO status word order. */
typedef enum
{
    ET_CAN_TX_EVENT_STATUS_FILL = 0u,
    ET_CAN_TX_EVENT_STATUS_GET_INDEX = 1u,
    ET_CAN_TX_EVENT_STATUS_PUT_INDEX = 2u,
    ET_CAN_TX_EVENT_STATUS_FULL = 3u,
    ET_CAN_TX_EVENT_STATUS_LOST = 4u,
} et_can_tx_event_status_word_t;

/** Public TX Event FIFO element word order; unrelated to Message RAM bit positions. */
typedef enum
{
    ET_CAN_TX_EVENT_IDENTIFIER = 0u,
    ET_CAN_TX_EVENT_FLAGS = 1u,
    ET_CAN_TX_EVENT_DLC = 2u,
    ET_CAN_TX_EVENT_TIMESTAMP = 3u,
    ET_CAN_TX_EVENT_TYPE = 4u,
    ET_CAN_TX_EVENT_MARKER = 5u,
    ET_CAN_TX_EVENT_INDEX = 6u,
} et_can_tx_event_word_t;

/** Public RX FIFO fill/indices/full/lost word order. */
typedef enum
{
    ET_CAN_RX_FIFO_FILL = 0u,
    ET_CAN_RX_FIFO_GET_INDEX = 1u,
    ET_CAN_RX_FIFO_PUT_INDEX = 2u,
    ET_CAN_RX_FIFO_FULL = 3u,
    ET_CAN_RX_FIFO_LOST = 4u,
} et_can_rx_fifo_word_t;

/** Word positions in the public bus-configuration tuple, unrelated to register bits. */
typedef enum
{
    ET_CAN_BUS_MONITOR = 0u,
    ET_CAN_BUS_RESTRICTED = 1u,
    ET_CAN_BUS_TIMESTAMP_DIVISOR = 2u,
    ET_CAN_BUS_TIMESTAMP_SOURCE = 3u,
    ET_CAN_BUS_TIMEOUT_SOURCE = 4u,
    ET_CAN_BUS_TIMEOUT_PERIOD = 5u,
    ET_CAN_BUS_TIMEOUT_ENABLED = 6u,
    ET_CAN_BUS_REJECT_REMOTE_EXT = 7u,
    ET_CAN_BUS_REJECT_REMOTE_STD = 8u,
    ET_CAN_BUS_UNMATCHED_EXT = 9u,
    ET_CAN_BUS_UNMATCHED_STD = 10u,
} et_can_bus_word_t;
/** Public byte offsets and region controls; not CMSIS register positions. */
typedef enum
{
    ET_CAN_RAM_STD_OFFSET = 0u,
    ET_CAN_RAM_STD_COUNT = 1u,
    ET_CAN_RAM_EXT_OFFSET = 2u,
    ET_CAN_RAM_EXT_COUNT = 3u,
    ET_CAN_RAM_TX_OFFSET = 4u,
    ET_CAN_RAM_TX_BUFFER_COUNT = 5u,
    ET_CAN_RAM_TX_FIFO_COUNT = 6u,
    ET_CAN_RAM_TX_QUEUE = 7u,
    ET_CAN_RAM_TX_PAYLOAD_BYTES = 8u,
    ET_CAN_RAM_EVENT_OFFSET = 9u,
    ET_CAN_RAM_EVENT_COUNT = 10u,
    ET_CAN_RAM_EVENT_WATERMARK = 11u,
    ET_CAN_RAM_RX0_OFFSET = 12u,
    ET_CAN_RAM_RX0_COUNT = 13u,
    ET_CAN_RAM_RX0_WATERMARK = 14u,
    ET_CAN_RAM_RX0_OVERWRITE = 15u,
    ET_CAN_RAM_RX1_OFFSET = 16u,
    ET_CAN_RAM_RX1_COUNT = 17u,
    ET_CAN_RAM_RX1_WATERMARK = 18u,
    ET_CAN_RAM_RX1_OVERWRITE = 19u,
    ET_CAN_RAM_RX_BUFFER_OFFSET = 20u,
    ET_CAN_RAM_RX_BUFFER_PAYLOAD_BYTES = 21u,
    ET_CAN_RAM_RX0_PAYLOAD_BYTES = 22u,
    ET_CAN_RAM_RX1_PAYLOAD_BYTES = 23u,
} et_can_ram_word_t;

/** Word positions of the seven hardware region maxima. */
typedef enum
{
    ET_CAN_RAM_LIMIT_RAM_BYTES = 0u,
    ET_CAN_RAM_LIMIT_STD_COUNT = 1u,
    ET_CAN_RAM_LIMIT_EXT_COUNT = 2u,
    ET_CAN_RAM_LIMIT_TX_COUNT = 3u,
    ET_CAN_RAM_LIMIT_RX_FIFO_COUNT = 4u,
    ET_CAN_RAM_LIMIT_EVENT_COUNT = 5u,
    ET_CAN_RAM_LIMIT_RX_BUFFER_COUNT = 6u,
} et_can_ram_limit_word_t;
/** Word positions in the limits response are independent from the options tuple. */
#define ET_CAN_LIMIT_TDC_OFFSET 0u
#define ET_CAN_LIMIT_TDC_FILTER 1u
#define ET_CAN_LIMIT_RAM_WATCHDOG 2u

/** Word positions of independent core controls, matching the public options contract. */
typedef enum
{
    ET_CAN_OPTION_FD = 0u,
    ET_CAN_OPTION_BRS = 1u,
    ET_CAN_OPTION_RETRY = 2u,
    ET_CAN_OPTION_TX_PAUSE = 3u,
    ET_CAN_OPTION_EDGE_FILTER = 4u,
    ET_CAN_OPTION_PROTOCOL_EXCEPTION = 5u,
    ET_CAN_OPTION_TDC = 6u,
    ET_CAN_OPTION_TDC_OFFSET = 7u,
    ET_CAN_OPTION_TDC_FILTER = 8u,
    ET_CAN_OPTION_RAM_WATCHDOG = 9u
} et_can_option_word_t;

/** Word positions within each timing phase; values are actual positive counts. */
typedef enum
{
    ET_CAN_TIMING_PRESCALER = 0u,
    ET_CAN_TIMING_SEGMENT1 = 1u,
    ET_CAN_TIMING_SEGMENT2 = 2u,
    ET_CAN_TIMING_SJW = 3u
} et_can_timing_word_t;

typedef enum
{
    ET_CAN_COMMAND_IDENTITY_GET = 0u,
    ET_CAN_COMMAND_INITIALIZING_SET = 1u,
    ET_CAN_COMMAND_INITIALIZING_GET = 2u,
    ET_CAN_COMMAND_TIMING_LIMITS_GET = 3u,
    ET_CAN_COMMAND_TIMING_SET = 4u,
    ET_CAN_COMMAND_TIMING_GET = 5u,
    ET_CAN_COMMAND_OPTIONS_SET = 6u,
    ET_CAN_COMMAND_OPTIONS_GET = 7u,
    ET_CAN_COMMAND_OPTION_LIMITS_GET = 8u,
    ET_CAN_COMMAND_RAM_LIMITS_GET = 9u,
    ET_CAN_COMMAND_RAM_LAYOUT_SET = 10u,
    ET_CAN_COMMAND_RAM_LAYOUT_GET = 11u,
    ET_CAN_COMMAND_BUS_CONFIG_SET = 12u,
    ET_CAN_COMMAND_BUS_CONFIG_GET = 13u,
    ET_CAN_COMMAND_LOOPBACK_SET = 14u,
    ET_CAN_COMMAND_LOOPBACK_GET = 15u,
    ET_CAN_COMMAND_BUS_LIMITS_GET = 16u,
    ET_CAN_COMMAND_TX_WRITE = 17u,
    ET_CAN_COMMAND_TX_REQUEST = 18u,
    ET_CAN_COMMAND_TX_STATUS_GET = 19u,
    ET_CAN_COMMAND_RX_FIFO_STATUS_GET = 20u,
    ET_CAN_COMMAND_RX_READ = 21u,
    ET_CAN_COMMAND_RX_FIFO_ACK = 22u,
    ET_CAN_COMMAND_RX_BUFFER_STATUS_GET = 23u,
    ET_CAN_COMMAND_RX_BUFFER_ACK = 24u,
    ET_CAN_COMMAND_FILTER_SET = 25u,
    ET_CAN_COMMAND_FILTER_GET = 26u,
    ET_CAN_COMMAND_EXTENDED_MASK_SET = 27u,
    ET_CAN_COMMAND_EXTENDED_MASK_GET = 28u,
    ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME = 29u,
    ET_CAN_COMMAND_TIMESTAMP_GET = 30u,
    ET_CAN_COMMAND_TIMESTAMP_RESET = 31u,
    ET_CAN_COMMAND_TIMEOUT_COUNTER_GET = 32u,
    ET_CAN_COMMAND_CLOCK_STOP_SET = 33u,
    ET_CAN_COMMAND_CLOCK_STOP_ACK_GET = 34u,
    ET_CAN_COMMAND_IRQ_MASK_SET = 35u,
    ET_CAN_COMMAND_IRQ_LINE_SELECT_SET = 36u,
    ET_CAN_COMMAND_IRQ_SNAPSHOT_GET = 37u,
    ET_CAN_COMMAND_IRQ_CLEAR = 38u,
    ET_CAN_COMMAND_IRQ_CAPTURE_START = 39u,
    ET_CAN_COMMAND_IRQ_CAPTURE_STOP = 40u,
    ET_CAN_COMMAND_IRQ_EVENT_GET = 41u,
    ET_CAN_COMMAND_IRQ_EVENT_RESET = 42u,
    ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET = 43u,
    ET_CAN_COMMAND_TX_EVENT_STATUS_GET = 44u,
    ET_CAN_COMMAND_TX_EVENT_READ = 45u,
    ET_CAN_COMMAND_TX_EVENT_ACK = 46u,
    ET_CAN_COMMAND_TX_READ = 47u,
    ET_CAN_COMMAND_TX_BUFFER_IRQ_SET = 48u,
    ET_CAN_COMMAND_IRQ_CAPTURE_PENDING = 49u,
    ET_CAN_COMMAND_IRQ_LINE_EVENTS_GET = 50u,
    ET_CAN_COMMAND_RAM_WORDS_READ = 51u,
    ET_CAN_COMMAND_RAM_WORDS_WRITE = 52u,
    ET_CAN_COMMAND_RAM_WORDS_EXCHANGE = 53u,
    /** Explicit configuration gate and attempted write; no implicit unlock. */
    ET_CAN_COMMAND_CONFIGURATION_WRITE_SET = 54u,
    ET_CAN_COMMAND_CONFIGURATION_WRITE_GET = 55u,
    ET_CAN_COMMAND_NOMINAL_TIMING_WRITE = 56u,
    ET_CAN_COMMAND_NON_ISO_SET = 57u,
    ET_CAN_COMMAND_NON_ISO_GET = 58u,
    ET_CAN_COMMAND_EVENT_FORMAT_SET = 59u,
    ET_CAN_COMMAND_EVENT_FORMAT_GET = 60u,
    ET_CAN_COMMAND_TX_EVENT_DETAILS_READ = 61u,
    ET_CAN_COMMAND_TIMEOUT_RELOAD = 62u,
    ET_CAN_COMMAND_TIMESTAMP_RESET_SNAPSHOT = 63u,
    ET_CAN_COMMAND_TSU_CONFIG_SET = 64u,
    ET_CAN_COMMAND_TSU_CONFIG_GET = 65u,
    ET_CAN_COMMAND_TSU_LIMITS_GET = 66u,
    ET_CAN_COMMAND_TSU_FLAGS_GET = 67u,
    ET_CAN_COMMAND_TSU_TIMEBASE_GET = 68u,
    ET_CAN_COMMAND_TSU_SLOT0_CONSUME = 69u,
    ET_CAN_COMMAND_ECC_ENABLE_SET = 70u,
    ET_CAN_COMMAND_ECC_MASK_SET = 71u,
    ET_CAN_COMMAND_ECC_FORCE = 72u,
    ET_CAN_COMMAND_ECC_CLEAR = 73u,
    ET_CAN_COMMAND_ECC_SNAPSHOT_GET = 74u,
    ET_CAN_COMMAND_ECC_CAPTURE_START = 75u,
    ET_CAN_COMMAND_ECC_CAPTURE_STOP = 76u,
    ET_CAN_COMMAND_ECC_EVENT_GET = 77u,
    ET_CAN_COMMAND_ECC_EVENT_RESET = 78u,
    ET_CAN_COMMAND_DMU_ENDPOINT_GET = 79u,
    ET_CAN_COMMAND_DMU_REQUEST_SET = 80u,
    ET_CAN_COMMAND_DMU_REQUEST_GET = 81u,
    ET_CAN_COMMAND_DMU_COUNTERS_GET = 82u,
    ET_CAN_COMMAND_DMU_STATUS_CONSUME = 83u,
    ET_CAN_COMMAND_DMU_TX_IMAGE_ENCODE = 84u,
    ET_CAN_COMMAND_DMU_RX_IMAGE_DECODE = 85u,
    ET_CAN_COMMAND_DMU_EVENT_IMAGE_DECODE = 86u,
    ET_CAN_COMMAND_DMU_WORD_ACCESS = 87u,
    ET_CAN_COMMAND_DMU_CAPTURE_START = 88u,
    ET_CAN_COMMAND_DMU_CAPTURE_STOP = 89u,
    ET_CAN_COMMAND_DMU_EVENT_GET = 90u,
    ET_CAN_COMMAND_DMU_TIMESTAMP_SET = 91u,
    ET_CAN_COMMAND_FILTER_SYNC_SET = 92u,
    ET_CAN_COMMAND_FILTER_SYNC_GET = 93u,
    ET_CAN_COMMAND_RX_TIMESTAMP_GET = 94u,
    ET_CAN_COMMAND_EXTERNAL_VECTOR_SET = 95u,
    ET_CAN_COMMAND_EXTERNAL_VECTOR_GET = 96u,
    ET_CAN_COMMAND_RAM_WATCHDOG_GET = 97u,
    ET_CAN_COMMAND_COUNT
} et_can_command_t;

/** Four non-destructive CAN interrupt-controller facts returned in this order. */
typedef enum
{
    ET_CAN_IRQ_SNAPSHOT_RAW = 0u,
    ET_CAN_IRQ_SNAPSHOT_ENABLED = 1u,
    ET_CAN_IRQ_SNAPSHOT_LINE1 = 2u,
    ET_CAN_IRQ_SNAPSHOT_LINES_ENABLED = 3u,
    ET_CAN_IRQ_SNAPSHOT_WORDS
} et_can_irq_snapshot_word_t;

/** Fixed callback-owned evidence; indexes are public Wire fields, not register positions. */
typedef enum
{
    ET_CAN_IRQ_EVENT_RAW_STATUS = 0u,
    ET_CAN_IRQ_EVENT_MASKED_STATUS = 1u,
    ET_CAN_IRQ_EVENT_LATCHED_EVENTS = 2u,
    ET_CAN_IRQ_EVENT_COUNT = 3u,
    ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT = 4u,
    ET_CAN_IRQ_EVENT_OVERFLOW_COUNT = 5u,
    ET_CAN_IRQ_EVENT_GENERATION = 6u,
    ET_CAN_IRQ_EVENT_FAULT_FLAGS = 7u,
    ET_CAN_IRQ_EVENT_WORDS
} et_can_irq_event_word_t;

/** ECC appends actual callback instance to the standard eight IRQ evidence words. */
#define ET_CAN_ECC_EVENT_INSTANCE ET_CAN_IRQ_EVENT_WORDS
#define ET_CAN_ECC_EVENT_WORDS (ET_CAN_IRQ_EVENT_WORDS + 1u)
/** DMU evidence uses the same field ordering, with independent storage and generation. */
#define ET_CAN_DMU_EVENT_INSTANCE ET_CAN_IRQ_EVENT_WORDS
#define ET_CAN_DMU_EVENT_WORDS (ET_CAN_IRQ_EVENT_WORDS + 1u)
typedef enum
{
    ET_CAN_DMU_ACCESS_ELEMENT = 0u,
    ET_CAN_DMU_ACCESS_WORD_INDEX,
    ET_CAN_DMU_ACCESS_WRITE,
    ET_CAN_DMU_ACCESS_VALUE,
    ET_CAN_DMU_ACCESS_WORDS
} et_can_dmu_access_word_t;
typedef enum
{
    ET_CAN_RX_TIMESTAMP_INTERNAL_VALID = 0u,
    ET_CAN_RX_TIMESTAMP_VALUE,
    ET_CAN_RX_TIMESTAMP_CAPTURED,
    ET_CAN_RX_TIMESTAMP_POINTER,
    ET_CAN_RX_TIMESTAMP_INDEX,
    ET_CAN_RX_TIMESTAMP_WORDS
} et_can_rx_timestamp_word_t;
typedef enum
{
    ET_CAN_ECC_RAW = 0u,
    ET_CAN_ECC_STATUS,
    ET_CAN_ECC_ENABLED,
    ET_CAN_ECC_MASKED,
    ET_CAN_ECC_SNAPSHOT_WORDS
} et_can_ecc_snapshot_word_t;

/** Service-local callback diagnostics; these are not CAN hardware interrupt sources. */
typedef enum
{
    ET_CAN_IRQ_FAULT_IO = (1u << 0),
    ET_CAN_IRQ_FAULT_UNEXPECTED = (1u << 1),
    ET_CAN_IRQ_FAULT_OVERFLOW = (1u << 2)
} et_can_irq_fault_t;

/** Protocol consume returns 15 explicit u32 observations; no C structure image is sent. */
#define ET_CAN_PROTOCOL_STATUS_WORDS 15u
typedef enum
{
    ET_CAN_PROTOCOL_LAST_ERROR = 0u,
    ET_CAN_PROTOCOL_ACTIVITY = 1u,
    ET_CAN_PROTOCOL_ERROR_PASSIVE = 2u,
    ET_CAN_PROTOCOL_WARNING = 3u,
    ET_CAN_PROTOCOL_BUS_OFF = 4u,
    ET_CAN_PROTOCOL_DATA_LAST_ERROR = 5u,
    ET_CAN_PROTOCOL_RECEIVED_ESI = 6u,
    ET_CAN_PROTOCOL_RECEIVED_BRS = 7u,
    ET_CAN_PROTOCOL_RECEIVED_FD = 8u,
    ET_CAN_PROTOCOL_PROTOCOL_EXCEPTION = 9u,
    ET_CAN_PROTOCOL_TDC_POSITION = 10u,
    ET_CAN_PROTOCOL_TX_ERROR_COUNT = 11u,
    ET_CAN_PROTOCOL_RX_ERROR_COUNT = 12u,
    ET_CAN_PROTOCOL_RX_ERROR_PASSIVE = 13u,
    ET_CAN_PROTOCOL_ERROR_LOG_COUNT = 14u,
} et_can_protocol_word_t;

/** Filter selector is extended/index; configuration adds type/action/ID1/ID2/Buffer index. */
#define ET_CAN_FILTER_SELECT_WORDS 2u
#define ET_CAN_FILTER_SYNC_SET_WORDS (ET_CAN_FILTER_SELECT_WORDS + 1u)
#define ET_CAN_FILTER_CONFIG_WORDS 5u
#define ET_CAN_FILTER_SET_WORDS (ET_CAN_FILTER_SELECT_WORDS + ET_CAN_FILTER_CONFIG_WORDS)
/** High Priority Message status returns four public semantic words. */
#define ET_CAN_HIGH_PRIORITY_STATUS_WORDS 4u
/** Word positions within the configuration, following the separate selector. */
typedef enum
{
    ET_CAN_FILTER_FIELD_TYPE = 0u,
    ET_CAN_FILTER_FIELD_ACTION = 1u,
    ET_CAN_FILTER_FIELD_ID1 = 2u,
    ET_CAN_FILTER_FIELD_ID2 = 3u,
    ET_CAN_FILTER_FIELD_BUFFER = 4u
} et_can_filter_field_t;

/** High Priority Message status response order; not the HPMS register layout. */
typedef enum
{
    ET_CAN_HIGH_PRIORITY_BUFFER_INDEX = 0u,
    ET_CAN_HIGH_PRIORITY_STORAGE = 1u,
    ET_CAN_HIGH_PRIORITY_FILTER_INDEX = 2u,
    ET_CAN_HIGH_PRIORITY_EXTENDED_FILTER = 3u
} et_can_high_priority_word_t;

/** No cached configuration or test state; all reads return current hardware facts. */
typedef struct
{
    et_can_id_t can_id;
    et_service_descriptor_t descriptor;
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_routes[ET_CAN_IRQ_LINE_COUNT];
    volatile uint32_t irq_event[ET_CAN_IRQ_EVENT_WORDS];
    /* Actual callback line attribution; reset together with the evidence generation. */
    volatile uint32_t irq_line_events[ET_CAN_IRQ_LINE_COUNT];
    uint32_t watched_sources;
    uint32_t line1_sources;
    uint8_t irq_priority;
    uint8_t bound_lines;
    et_irq_route_t ecc_route;
    volatile uint32_t ecc_event[ET_CAN_ECC_EVENT_WORDS];
    uint32_t ecc_watched;
    uint8_t ecc_bound;
    et_irq_route_t dmu_route;
    volatile uint32_t dmu_event[ET_CAN_DMU_EVENT_WORDS];
    uint32_t dmu_watched;
    uint8_t dmu_bound;
} et_can_service_t;

int et_can_service_init(et_can_service_t *service, et_can_id_t can_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_can_service_descriptor(const et_can_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_can_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
