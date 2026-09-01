#ifndef ET_UART_SERVICE_H
#define ET_UART_SERVICE_H

/**
 * @file et_uart_service.h
 * @brief UART command contract and bounded per-instance runtime state.
 *
 * UART Service decodes PC commands, calls only UART Wrap and records bounded
 * capture/IRQ facts. Test vectors, assertions and multi-IP sequencing stay PC-side.
 */

#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_message.h"
#include "et_service_router.h"
#include "et_test_protocol_config.h"
#include "et_uart_wrap.h"

#define ET_UART_SERVICE_ID 0x0101u
#define ET_UART_SERVICE_BODY_CAPACITY (ET_TEST_PROTOCOL_MAX_PAYLOAD - ET_MESSAGE_HEADER_SIZE)
#define ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD 4u
#define ET_UART_SERVICE_MAX_WRITE_CHUNK                                                            \
    (ET_UART_SERVICE_BODY_CAPACITY - ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD)
#define ET_UART_SERVICE_MAX_READ_CHUNK ET_UART_SERVICE_BODY_CAPACITY
#define ET_UART_SERVICE_CAPTURE_CAPACITY 512u
#define ET_UART_SERVICE_NINE_BIT_CAPACITY 256u
#define ET_UART_SERVICE_RX_DRAIN_LIMIT 64u
/* Small stack chunk used while draining at most RX_DRAIN_LIMIT bytes. */
#define ET_UART_SERVICE_RX_DRAIN_CHUNK_SIZE 16u
#define ET_UART_SERVICE_SNAPSHOT_RESPONSE_SIZE 32u
#define ET_UART_SERVICE_STATUS_RESPONSE_SIZE 24u
#define ET_UART_SERVICE_IRQ_STATE_RESPONSE_SIZE 24u
#define ET_UART_SERVICE_MODEM_STATUS_RESPONSE_SIZE 16u
#define ET_UART_SERVICE_BUSY_DETECT_RESPONSE_SIZE 32u
#define ET_UART_SERVICE_SHADOW_FIFO_RESPONSE_SIZE 4u
#define ET_UART_SERVICE_FIFO_ACCESS_RESPONSE_SIZE 4u
#define ET_UART_SERVICE_FIFO_TX_READ_RESPONSE_SIZE 4u

/* Remaining fixed Wire body sizes, in bytes. */
#define ET_UART_SERVICE_CAPABILITIES_RESPONSE_SIZE 20u
#define ET_UART_SERVICE_DMA_ENDPOINT_REQUEST_SIZE 4u
#define ET_UART_SERVICE_DMA_ENDPOINT_RESPONSE_SIZE 8u
#define ET_UART_SERVICE_U32_BODY_SIZE ((uint16_t)sizeof(uint32_t))
#define ET_UART_SERVICE_INITIALIZE_REQUEST_SIZE 8u
#define ET_UART_SERVICE_COUNT_REQUEST_SIZE 8u
#define ET_UART_SERVICE_COUNT_RESPONSE_SIZE 4u
#define ET_UART_SERVICE_IRQ_CONFIG_REQUEST_SIZE 8u
#define ET_UART_SERVICE_NINE_BIT_HEADER_SIZE 8u
#define ET_UART_SERVICE_NINE_BIT_ITEM_SIZE ((uint16_t)sizeof(uint16_t))
#define ET_UART_SERVICE_WORD_OFFSET(index) ((uint16_t)((index) * sizeof(uint32_t)))

/* Fixed byte offsets shared by byte and 9-bit transfer request bodies. */
#define ET_UART_SERVICE_COUNT_OFFSET 0u
#define ET_UART_SERVICE_POLL_BUDGET_OFFSET 4u
#define ET_UART_SERVICE_DATA_OFFSET 4u
#define ET_UART_SERVICE_NINE_BIT_DATA_OFFSET 8u

/* INITIALIZE request fields. */
#define ET_UART_SERVICE_INITIALIZE_BAUD_OFFSET 0u
#define ET_UART_SERVICE_INITIALIZE_DATA_BITS_OFFSET 4u
#define ET_UART_SERVICE_INITIALIZE_STOP_BITS_OFFSET 5u
#define ET_UART_SERVICE_INITIALIZE_PARITY_OFFSET 6u
#define ET_UART_SERVICE_INITIALIZE_RESERVED_OFFSET 7u

/* One-word value requests use one value byte followed by zero padding. */
#define ET_UART_SERVICE_VALUE_OFFSET 0u
#define ET_UART_SERVICE_VALUE_RESERVED_OFFSET 1u
#define ET_UART_SERVICE_VALUE_RESERVED_SIZE 3u

/* IRQ_CONFIG and NINE_BIT_CONFIG request fields. */
#define ET_UART_SERVICE_IRQ_MASK_OFFSET 0u
#define ET_UART_SERVICE_IRQ_ENABLED_REQUEST_OFFSET 4u
#define ET_UART_SERVICE_IRQ_PRIORITY_REQUEST_OFFSET 5u
#define ET_UART_SERVICE_IRQ_RESERVED_OFFSET 6u
#define ET_UART_SERVICE_IRQ_RESERVED_SIZE 2u
#define ET_UART_SERVICE_NINE_BIT_ENABLED_OFFSET 0u
#define ET_UART_SERVICE_NINE_BIT_RECEIVER_OFFSET 1u
#define ET_UART_SERVICE_NINE_BIT_ADDRESS_OFFSET 2u
#define ET_UART_SERVICE_NINE_BIT_RESERVED_OFFSET 3u

/* FIFO, modem, flow-control and test command byte fields. */
#define ET_UART_SERVICE_FIFO_ENABLED_OFFSET 0u
#define ET_UART_SERVICE_FIFO_TX_THRESHOLD_OFFSET 1u
#define ET_UART_SERVICE_FIFO_RX_THRESHOLD_OFFSET 2u
#define ET_UART_SERVICE_FIFO_DMA_MODE_OFFSET 3u
#define ET_UART_SERVICE_FLOW_ENABLED_OFFSET 0u
#define ET_UART_SERVICE_FLOW_OPTION1_OFFSET 1u
#define ET_UART_SERVICE_FLOW_OPTION2_OFFSET 2u
#define ET_UART_SERVICE_FLOW_RESERVED_OFFSET 3u
#define ET_UART_SERVICE_MODEM_RTS_OFFSET 0u
#define ET_UART_SERVICE_MODEM_DTR_OFFSET 1u
#define ET_UART_SERVICE_MODEM_RESERVED_OFFSET 2u
#define ET_UART_SERVICE_MODEM_RESERVED_SIZE 2u
#define ET_UART_SERVICE_SHADOW_RESERVED_OFFSET 3u
#define ET_UART_SERVICE_FIFO_RX_VALUE_OFFSET 0u
#define ET_UART_SERVICE_FIFO_RX_PARITY_OFFSET 1u
#define ET_UART_SERVICE_FIFO_RX_FRAMING_OFFSET 2u
#define ET_UART_SERVICE_FIFO_RX_RESERVED_OFFSET 3u

/* Canonical boolean values used by one-word command bodies. */
#define ET_UART_SERVICE_BOOLEAN_FALSE 0u
#define ET_UART_SERVICE_BOOLEAN_TRUE 1u

/* Bounded retry count for lock-free IRQ snapshot reads. */
#define ET_UART_SERVICE_SNAPSHOT_RETRIES 8u

/* CAPABILITIES_GET response word offsets. */
#define ET_UART_SERVICE_CAP_FEATURES_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_CAP_MIN_BAUD_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_CAP_MAX_BAUD_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_CAP_MAX_READ_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_CAP_MAX_WRITE_OFFSET ET_UART_SERVICE_WORD_OFFSET(4u)

/* Capture and IRQ-state response offsets. */
#define ET_UART_SERVICE_CAPTURE_ACTIVE_OFFSET 0u
#define ET_UART_SERVICE_CAPTURE_EXPECTED_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_CAPTURE_RECEIVED_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_IRQ_ENABLED_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_IRQ_PENDING_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_IRQ_ACTIVE_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_IRQ_EVENT_COUNT_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_IRQ_OVERFLOW_COUNT_OFFSET ET_UART_SERVICE_WORD_OFFSET(4u)
#define ET_UART_SERVICE_IRQ_FAULT_COUNT_OFFSET ET_UART_SERVICE_WORD_OFFSET(5u)

/* SNAPSHOT_GET and STATUS_GET response word offsets. */
#define ET_UART_SERVICE_SNAPSHOT_COMPONENT_PARAMETER_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_SNAPSHOT_COMPONENT_VERSION_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_SNAPSHOT_COMPONENT_TYPE_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_SNAPSHOT_SCRATCH_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_SNAPSHOT_UART_STATUS_OFFSET ET_UART_SERVICE_WORD_OFFSET(4u)
#define ET_UART_SERVICE_SNAPSHOT_LINE_STATUS_OFFSET ET_UART_SERVICE_WORD_OFFSET(5u)
#define ET_UART_SERVICE_SNAPSHOT_TX_LEVEL_OFFSET ET_UART_SERVICE_WORD_OFFSET(6u)
#define ET_UART_SERVICE_SNAPSHOT_RX_LEVEL_OFFSET ET_UART_SERVICE_WORD_OFFSET(7u)
#define ET_UART_SERVICE_STATUS_LINE_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_STATUS_FIFO_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_STATUS_TX_LEVEL_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_STATUS_RX_LEVEL_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_STATUS_ERROR_OFFSET ET_UART_SERVICE_WORD_OFFSET(4u)
#define ET_UART_SERVICE_STATUS_STATE_OFFSET ET_UART_SERVICE_WORD_OFFSET(5u)

/* MODEM_STATUS_GET and BUSY_DETECT_TRIGGER response word offsets. */
#define ET_UART_SERVICE_MODEM_INPUT_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_MODEM_DELTA_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_MODEM_OUTPUT_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_MODEM_RAW_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_BUSY_PRE_TRIGGER_OFFSET ET_UART_SERVICE_WORD_OFFSET(0u)
#define ET_UART_SERVICE_BUSY_IIR_OFFSET ET_UART_SERVICE_WORD_OFFSET(1u)
#define ET_UART_SERVICE_BUSY_USR_OFFSET ET_UART_SERVICE_WORD_OFFSET(2u)
#define ET_UART_SERVICE_BUSY_TRIGGER_COUNT_OFFSET ET_UART_SERVICE_WORD_OFFSET(3u)
#define ET_UART_SERVICE_BUSY_OBSERVED_OFFSET ET_UART_SERVICE_WORD_OFFSET(4u)
#define ET_UART_SERVICE_BUSY_IRQ_OBSERVED_OFFSET ET_UART_SERVICE_WORD_OFFSET(5u)
#define ET_UART_SERVICE_BUSY_CLEARED_OFFSET ET_UART_SERVICE_WORD_OFFSET(6u)
#define ET_UART_SERVICE_BUSY_RECOVERED_OFFSET ET_UART_SERVICE_WORD_OFFSET(7u)

/* Small byte responses are zero-filled before writing these meaningful fields. */
#define ET_UART_SERVICE_SMALL_VALUE_OFFSET 0u
#define ET_UART_SERVICE_SHADOW_ENABLED_OFFSET 0u
#define ET_UART_SERVICE_SHADOW_TX_THRESHOLD_OFFSET 1u
#define ET_UART_SERVICE_SHADOW_RX_THRESHOLD_OFFSET 2u

/* Capture framing and the UART-local IRQ sources used while capture is armed. */
#define ET_UART_SERVICE_CAPTURE_HEADER_SIZE 12u
#define ET_UART_SERVICE_CAPTURE_IRQ_EVENTS (ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_RX_IDLE)
#define ET_UART_SERVICE_IRQ_WRAP_ALL                                                               \
    (ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_TX_READY | ET_UART_WRAP_IRQ_ERROR |              \
     ET_UART_WRAP_IRQ_RX_IDLE | ET_UART_WRAP_IRQ_MODEM_STATUS |                                    \
     ET_UART_WRAP_IRQ_ADDRESS_RECEIVED | ET_UART_WRAP_IRQ_BUSY)

/* Stable UART IRQ bits carried on the Wire; they are independent of SDK masks. */
#define ET_UART_SERVICE_IRQ_WIRE_RX_READY (1u << 0)
#define ET_UART_SERVICE_IRQ_WIRE_TX_READY (1u << 1)
#define ET_UART_SERVICE_IRQ_WIRE_LINE_ERROR (1u << 2)
#define ET_UART_SERVICE_IRQ_WIRE_MODEM_STATUS (1u << 3)
#define ET_UART_SERVICE_IRQ_WIRE_TIMEOUT (1u << 4)
#define ET_UART_SERVICE_IRQ_WIRE_BUSY (1u << 5)
#define ET_UART_SERVICE_IRQ_WIRE_NINE_BIT (1u << 6)
#define ET_UART_SERVICE_IRQ_WIRE_ALLOWED                                                           \
    (ET_UART_SERVICE_IRQ_WIRE_RX_READY | ET_UART_SERVICE_IRQ_WIRE_TX_READY |                       \
     ET_UART_SERVICE_IRQ_WIRE_LINE_ERROR | ET_UART_SERVICE_IRQ_WIRE_MODEM_STATUS |                 \
     ET_UART_SERVICE_IRQ_WIRE_TIMEOUT | ET_UART_SERVICE_IRQ_WIRE_BUSY |                            \
     ET_UART_SERVICE_IRQ_WIRE_NINE_BIT)

typedef enum
{
    ET_UART_COMMAND_CAPABILITIES_GET = 0x0001u, /**< Read runtime UART facts. */
    ET_UART_COMMAND_DMA_ENDPOINT_GET = 0x0002u, /**< Resolve trusted DMA endpoint. */
    ET_UART_COMMAND_DMA_ENABLE_SET = 0x0003u,   /**< Enable or disable UART DMA request. */
    ET_UART_COMMAND_INITIALIZE = 0x0004u,       /**< Apply one complete UART configuration. */
    ET_UART_COMMAND_DEINITIALIZE = 0x0005u,     /**< Release UART and managed IRQ state. */
    ET_UART_COMMAND_WRITE = 0x0006u,            /**< Perform one bounded byte write. */
    ET_UART_COMMAND_READ_EXACT = 0x0007u,       /**< Read currently available bytes. */
    ET_UART_COMMAND_CAPTURE_START = 0x0008u,    /**< Arm bounded IRQ receive capture. */
    ET_UART_COMMAND_CAPTURE_GET = 0x0009u,      /**< Read capture progress/data facts. */
    ET_UART_COMMAND_CAPTURE_CANCEL = 0x000au,   /**< Stop and clear active capture. */
    /* Deprecated: PC composes atomic capture/write/read operations. */
    ET_UART_COMMAND_EXCHANGE = 0x000bu,
    ET_UART_COMMAND_SNAPSHOT_GET = 0x000cu,
    ET_UART_COMMAND_SOFTWARE_RESET = 0x000du,
    ET_UART_COMMAND_LOOPBACK_SET = 0x000eu,
    ET_UART_COMMAND_FIFO_CONFIG = 0x000fu,
    ET_UART_COMMAND_STATUS_GET = 0x0010u,
    ET_UART_COMMAND_IRQ_CONFIG = 0x0011u,
    ET_UART_COMMAND_IRQ_STATE_GET = 0x0012u,
    ET_UART_COMMAND_BREAK_SET = 0x0013u,
    ET_UART_COMMAND_HALT_SET = 0x0014u,
    ET_UART_COMMAND_DMA_MODE_SET = 0x0015u,
    ET_UART_COMMAND_NINE_BIT_CONFIG = 0x0016u,
    ET_UART_COMMAND_WRITE_9BIT = 0x0017u,
    ET_UART_COMMAND_READ_9BIT = 0x0018u,
    ET_UART_COMMAND_FLOW_CONTROL_SET = 0x0019u,
    ET_UART_COMMAND_MODEM_CONTROL_SET = 0x001au,
    ET_UART_COMMAND_MODEM_STATUS_GET = 0x001bu,
    ET_UART_COMMAND_WRITE_PARTIAL = 0x001cu,
    ET_UART_COMMAND_BUSY_DETECT_TRIGGER = 0x001du,
    ET_UART_COMMAND_SHADOW_FIFO_CONFIG = 0x001eu,
    ET_UART_COMMAND_FIFO_ACCESS_SET = 0x001fu,
    ET_UART_COMMAND_FIFO_TX_READ = 0x0020u,
    ET_UART_COMMAND_FIFO_RX_WRITE = 0x0021u
} et_uart_command_t;

typedef struct
{
    uint16_t uart_id;             /**< Stable logical UART instance ID. */
    uint8_t initialized;          /**< UART Wrap handle is active. */
    uint8_t capture_active;       /**< RX capture expects more data. */
    uint8_t irq_bound;            /**< Managed UART IRQ route is bound. */
    uint8_t irq_priority;         /**< Currently applied NVIC priority. */
    uint8_t default_irq_priority; /**< Board-selected default priority. */
    uint8_t reserved_priority;
    uint16_t capture_expected; /**< Requested capture bytes. */
    uint16_t capture_received; /**< Bytes currently stored in capture. */
    uint8_t fifo_enabled;      /**< Last applied FIFO enable state. */
    uint8_t fifo_tx_threshold; /**< Last applied TX FIFO threshold. */
    uint8_t fifo_rx_threshold; /**< Last applied RX FIFO threshold. */
    uint8_t dma_mode;          /**< Last applied UART DMA mode. */
    uint8_t reserved8[2];
    uint32_t irq_enabled_mask;               /**< PC-requested normalized source mask. */
    uint32_t irq_applied_wrap_mask;          /**< Sources currently enabled in hardware. */
    uint32_t irq_suppressed_wrap_mask;       /**< Temporarily suppressed noisy sources. */
    volatile uint32_t capture_generation;    /**< Seqlock generation for capture data. */
    volatile uint32_t irq_result_generation; /**< Seqlock generation for IRQ facts. */
    volatile uint32_t irq_pending_mask;      /**< Last pending normalized events. */
    volatile uint32_t irq_active_mask;       /**< Last active normalized events. */
    volatile uint32_t irq_event_count;       /**< Saturating managed callback count. */
    volatile uint32_t irq_overflow_count;    /**< Saturating capture overflow count. */
    volatile uint32_t irq_fault_count;       /**< Saturating IRQ maintenance failures. */
    volatile uint32_t latched_error_flags;   /**< Errors retained until explicit clear. */
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_route;
    et_uart_wrap_handle_t handle;
    uint8_t capture[ET_UART_SERVICE_CAPTURE_CAPACITY];
    uint16_t nine_bit[ET_UART_SERVICE_NINE_BIT_CAPACITY];
    et_service_descriptor_t descriptor;
} et_uart_service_t;

/** Initialize one UART Service without configuring UART hardware. */
int et_uart_service_init(et_uart_service_t *service, uint16_t uart_id,
                         et_irq_manager_t *irq_manager, uint8_t capture_irq_priority);
/** Return the router descriptor of an initialized UART Service. */
const et_service_descriptor_t *et_uart_service_descriptor(const et_uart_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/** Create one UART Service through the chip-neutral group registry contract. */
int et_uart_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
