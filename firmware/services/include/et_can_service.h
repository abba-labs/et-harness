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
#define ET_CAN_RX_FIFO_STATUS_WORDS 5u
#define ET_CAN_RX_SELECT_WORDS 2u
#define ET_CAN_RX_BITMAP_WORDS 2u
#define ET_CAN_RX_SELECT_SOURCE 0u
#define ET_CAN_RX_SELECT_INDEX 1u
#define ET_CAN_RX_BITMAP_LOW 0u
#define ET_CAN_RX_BITMAP_HIGH 1u
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

/** Public tx_status word order; DATA marks the start of 64 payload bytes. */
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

/** Public rx_fifo word order; DATA marks the start of 64 payload bytes. */
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
    ET_CAN_COMMAND_COUNT
} et_can_command_t;

/** No cached configuration or test state; all reads return current hardware facts. */
typedef struct
{
    et_can_id_t can_id;
    et_service_descriptor_t descriptor;
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
