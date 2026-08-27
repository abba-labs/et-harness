#ifndef ET_UART_WRAP_H
#define ET_UART_WRAP_H

/**
 * @file et_uart_wrap.h
 * @brief Stable chip-independent UART Driver contract.
 *
 * Services use logical IDs and versioned structures from this header. Chip
 * SDK handles, registers and enum values remain private to et_uart_wrap.c.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_UART_WRAP_API_VERSION 1u
#define ET_UART_WRAP_HANDLE_WORDS 8u
#define ET_UART_WRAP_MIN_BAUDRATE 1200u
#define ET_UART_WRAP_MIN_DATA_BITS 5u
#define ET_UART_WRAP_MAX_DATA_BITS 8u
#define ET_UART_WRAP_NINE_BIT_VALUE_MAX 0x01ffu
#define ET_UART_WRAP_CONFIG_RESERVED_WORDS 8u
#define ET_UART_WRAP_CAP_RESERVED_WORDS 8u
#define ET_UART_WRAP_IRQ_RESERVED_WORDS 2u
#define ET_UART_WRAP_RESULT_RESERVED_WORDS 4u
#define ET_UART_WRAP_SNAPSHOT_RESERVED_WORDS 4u
#define ET_UART_WRAP_STATUS_RESERVED_WORDS 4u
#define ET_UART_WRAP_MODEM_STATUS_RESERVED_WORDS 2u

/** Stable logical UART instance identifier. */
typedef uint16_t et_uart_id_t;

/** Common parity selection shared with the PC UART Driver. */
typedef enum
{
    ET_UART_WRAP_PARITY_NONE = 0u,
    ET_UART_WRAP_PARITY_EVEN = 1u,
    ET_UART_WRAP_PARITY_ODD = 2u,
    ET_UART_WRAP_PARITY_STICK_ZERO = 3u,
    ET_UART_WRAP_PARITY_STICK_ONE = 4u
} et_uart_wrap_parity_t;

/* Wire values are shared with the PC driver.  Value 2 remains accepted as
 * legacy two-stop configuration for data widths above five bits. */
/** Common UART DMA operating mode. */
typedef enum
{
    ET_UART_WRAP_STOP_BITS_1 = 1u,
    ET_UART_WRAP_STOP_BITS_1_5 = 2u,
    ET_UART_WRAP_STOP_BITS_2 = 3u
} et_uart_wrap_stop_bits_t;

typedef enum
{
    ET_UART_WRAP_DMA_DISABLED = 0u,
    ET_UART_WRAP_DMA_SINGLE = 1u,
    ET_UART_WRAP_DMA_MULTI = 2u
} et_uart_wrap_dma_mode_t;

/** Normalized interrupt-event facts returned by the Wrap. */
typedef enum
{
    ET_UART_WRAP_TXFIFO_THRESHOLD_0 = 0u,
    ET_UART_WRAP_TXFIFO_THRESHOLD_2 = 2u,
    ET_UART_WRAP_TXFIFO_THRESHOLD_4 = 4u,
    ET_UART_WRAP_TXFIFO_THRESHOLD_8 = 8u
} et_uart_wrap_tx_fifo_threshold_t;

typedef enum
{
    ET_UART_WRAP_RXFIFO_THRESHOLD_1 = 1u,
    ET_UART_WRAP_RXFIFO_THRESHOLD_4 = 4u,
    ET_UART_WRAP_RXFIFO_THRESHOLD_8 = 8u,
    ET_UART_WRAP_RXFIFO_THRESHOLD_14 = 14u
} et_uart_wrap_rx_fifo_threshold_t;

typedef enum
{
    ET_UART_WRAP_NINE_BIT_RECEIVER_SOFTWARE = 0u,
    ET_UART_WRAP_NINE_BIT_RECEIVER_HARDWARE = 1u
} et_uart_wrap_nine_bit_receiver_mode_t;

typedef enum
{
    ET_UART_WRAP_NINE_BIT_TRANSMITTER_HARDWARE = 0u,
    ET_UART_WRAP_NINE_BIT_TRANSMITTER_SOFTWARE = 1u
} et_uart_wrap_nine_bit_transmitter_mode_t;

typedef enum
{
    ET_UART_WRAP_IRQ_RX_READY = 1u << 0,
    ET_UART_WRAP_IRQ_TX_READY = 1u << 1,
    ET_UART_WRAP_IRQ_ERROR = 1u << 2,
    ET_UART_WRAP_IRQ_RX_IDLE = 1u << 3,
    ET_UART_WRAP_IRQ_OTHER = 1u << 4,
    ET_UART_WRAP_IRQ_MODEM_STATUS = 1u << 5,
    ET_UART_WRAP_IRQ_ADDRESS_RECEIVED = 1u << 6,
    ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY = 1u << 7,
    ET_UART_WRAP_IRQ_BUSY = 1u << 8
} et_uart_wrap_irq_flags_t;

/** Normalized line-status facts sampled from UART hardware. */
typedef enum
{
    ET_UART_WRAP_LINE_DATA_READY = 1u << 0,
    ET_UART_WRAP_LINE_OVERRUN = 1u << 1,
    ET_UART_WRAP_LINE_PARITY_ERROR = 1u << 2,
    ET_UART_WRAP_LINE_FRAMING_ERROR = 1u << 3,
    ET_UART_WRAP_LINE_BREAK = 1u << 4,
    ET_UART_WRAP_LINE_TX_HOLDING_EMPTY = 1u << 5,
    ET_UART_WRAP_LINE_TX_EMPTY = 1u << 6,
    ET_UART_WRAP_LINE_RX_FIFO_ERROR = 1u << 7,
    ET_UART_WRAP_LINE_ADDRESS_RECEIVED = 1u << 8
} et_uart_wrap_line_flags_t;

/** Error-only subset of line-status facts. */
typedef enum
{
    ET_UART_WRAP_ERROR_OVERRUN = 1u << 0,
    ET_UART_WRAP_ERROR_PARITY = 1u << 1,
    ET_UART_WRAP_ERROR_FRAMING = 1u << 2,
    ET_UART_WRAP_ERROR_BREAK = 1u << 3,
    ET_UART_WRAP_ERROR_RX_FIFO = 1u << 4
} et_uart_wrap_error_flags_t;

/** Normalized UART occupancy and busy-state facts. */
typedef enum
{
    ET_UART_WRAP_STATE_BUSY = 1u << 0,
    ET_UART_WRAP_STATE_TX_NOT_FULL = 1u << 1,
    ET_UART_WRAP_STATE_TX_EMPTY = 1u << 2,
    ET_UART_WRAP_STATE_RX_NOT_EMPTY = 1u << 3,
    ET_UART_WRAP_STATE_RX_FULL = 1u << 4
} et_uart_wrap_state_flags_t;

typedef enum
{
    ET_UART_WRAP_MODEM_INPUT_CTS = 1u << 0,
    ET_UART_WRAP_MODEM_INPUT_DSR = 1u << 1,
    ET_UART_WRAP_MODEM_INPUT_RI = 1u << 2,
    ET_UART_WRAP_MODEM_INPUT_DCD = 1u << 3
} et_uart_wrap_modem_input_flags_t;

typedef enum
{
    ET_UART_WRAP_MODEM_OUTPUT_RTS = 1u << 0,
    ET_UART_WRAP_MODEM_OUTPUT_DTR = 1u << 1
} et_uart_wrap_modem_output_flags_t;

typedef enum
{
    ET_UART_WRAP_CAP_RX_POLLING = 1u << 0,
    ET_UART_WRAP_CAP_TX_POLLING = 1u << 1,
    ET_UART_WRAP_CAP_RX_IRQ = 1u << 2,
    ET_UART_WRAP_CAP_TX_IRQ = 1u << 3,
    ET_UART_WRAP_CAP_RX_DMA = 1u << 4,
    ET_UART_WRAP_CAP_TX_DMA = 1u << 5,
    ET_UART_WRAP_CAP_FIFO = 1u << 6,
    ET_UART_WRAP_CAP_LOOPBACK = 1u << 7,
    ET_UART_WRAP_CAP_FLOW_CONTROL = 1u << 8,
    ET_UART_WRAP_CAP_BREAK = 1u << 9,
    ET_UART_WRAP_CAP_NINE_BIT = 1u << 10,
    ET_UART_WRAP_CAP_MODEM = 1u << 11,
    ET_UART_WRAP_CAP_HALT = 1u << 12,
    ET_UART_WRAP_CAP_SOFTWARE_RESET = 1u << 13,
    ET_UART_WRAP_CAP_SHADOW = 1u << 14,
    ET_UART_WRAP_CAP_FIFO_ACCESS = 1u << 15
} et_uart_wrap_capability_flags_t;

typedef enum
{
    ET_UART_WRAP_RESULT_WOULD_BLOCK = 1u << 0
} et_uart_wrap_result_flags_t;

typedef enum
{
    ET_UART_WRAP_DMA_ENDPOINT_TX = 0u,
    ET_UART_WRAP_DMA_ENDPOINT_RX = 1u
} et_uart_wrap_dma_endpoint_t;

/** Versioned initialization configuration; reserved fields must be zero. */
typedef struct
{
    uint16_t struct_size; /**< Caller-visible structure size. */
    uint16_t api_version; /**< Must equal ET_UART_WRAP_API_VERSION. */
    et_uart_id_t uart_id; /**< Logical UART instance. */
    uint16_t reserved16;
    uint32_t baudrate;   /**< Requested baud in bit/s. */
    uint32_t flags;      /**< Reserved options; unknown bits are rejected. */
    uint32_t timeout_us; /**< Reserved timing hint; PC owns operation deadline. */
    uint8_t data_bits;   /**< Data width accepted by selected hardware. */
    uint8_t stop_bits;   /**< One et_uart_wrap_stop_bits_t wire value. */
    uint8_t parity;      /**< One et_uart_wrap_parity_t value. */
    uint8_t reserved8;
    uint32_t reserved[ET_UART_WRAP_CONFIG_RESERVED_WORDS];
} et_uart_wrap_config_t;

#define ET_UART_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_uart_wrap_config_t, reserved))

/** Runtime capabilities reported for one logical UART instance. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t feature_flags;
    uint32_t min_baudrate;
    uint32_t max_baudrate;
    uint32_t max_read_size;
    uint32_t max_write_size;
    uint32_t reserved[ET_UART_WRAP_CAP_RESERVED_WORDS];
} et_uart_wrap_capabilities_t;

/** One coherent normalized interrupt snapshot. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t interrupt_flags;
    uint32_t event_flags;
    uint32_t line_flags;
    uint32_t error_flags;
    uint32_t reserved[ET_UART_WRAP_IRQ_RESERVED_WORDS];
} et_uart_wrap_irq_status_t;

/** Result of one bounded non-blocking read or write operation. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    int32_t status;
    uint32_t reserved_status;
    uint32_t transferred;
    uint32_t flags;
    uint32_t reserved[ET_UART_WRAP_RESULT_RESERVED_WORDS];
} et_uart_wrap_io_result_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t component_parameter;
    uint32_t component_version;
    uint32_t component_type;
    uint32_t scratch;
    uint32_t uart_status;
    uint32_t line_status;
    uint16_t tx_fifo_level;
    uint16_t rx_fifo_level;
    uint32_t reserved[ET_UART_WRAP_SNAPSHOT_RESERVED_WORDS];
} et_uart_wrap_snapshot_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint8_t enabled;
    uint8_t tx_threshold;
    uint8_t rx_threshold;
    uint8_t reserved8;
    uint32_t reserved[ET_UART_WRAP_CONFIG_RESERVED_WORDS];
} et_uart_wrap_fifo_config_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint8_t enabled;
    uint8_t receiver_mode;
    uint8_t transmitter_mode;
    uint8_t receiver_match_address;
    uint8_t transmitter_self_address;
    uint8_t reserved8[3];
    uint32_t reserved[ET_UART_WRAP_CONFIG_RESERVED_WORDS];
} et_uart_wrap_nine_bit_config_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t interrupt_flags;
    uint32_t line_status;
    uint32_t fifo_flags;
    uint32_t error_flags;
    uint32_t state_flags;
    uint16_t tx_fifo_level;
    uint16_t rx_fifo_level;
    uint32_t reserved[ET_UART_WRAP_STATUS_RESERVED_WORDS];
} et_uart_wrap_status_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t input_flags;
    uint32_t delta_flags;
    uint32_t output_flags;
    uint32_t raw_status;
    uint32_t reserved[ET_UART_WRAP_MODEM_STATUS_RESERVED_WORDS];
} et_uart_wrap_modem_status_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint8_t rts_asserted;
    uint8_t dtr_asserted;
    uint16_t reserved16;
    uint32_t reserved[ET_UART_WRAP_CONFIG_RESERVED_WORDS];
} et_uart_wrap_modem_control_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t pre_trigger_usr;
    uint32_t observed_iir;
    uint32_t observed_usr;
    uint32_t trigger_count;
    uint8_t busy_observed;
    uint8_t interrupt_observed;
    uint8_t cleared;
    uint8_t recovered;
} et_uart_wrap_busy_detect_result_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint8_t enabled;
    uint8_t tx_threshold;
    uint8_t rx_threshold;
    uint8_t fifo_access;
} et_uart_wrap_shadow_fifo_state_t;

/** Opaque storage for one initialized chip UART Driver handle. */
typedef struct
{
    uintptr_t opaque[ET_UART_WRAP_HANDLE_WORDS];
} et_uart_wrap_handle_t;

/** Return normalized runtime capabilities for one UART instance. */
et_wrap_status_t et_uart_wrap_get_capabilities(et_uart_id_t uart_id,
                                               et_uart_wrap_capabilities_t *capabilities);
/** Resolve UART interrupt events to the chip-specific physical route. */
et_wrap_status_t et_uart_wrap_get_irq_route(et_uart_id_t uart_id, uint32_t interrupt_flags,
                                            et_irq_route_t *route);
/** Resolve a trusted UART data-register endpoint for DMA configuration. */
et_wrap_status_t et_uart_wrap_get_dma_endpoint_address(et_uart_id_t uart_id, uint8_t endpoint,
                                                       uintptr_t *address);
/** Validate configuration and initialize one opaque UART handle. */
et_wrap_status_t et_uart_wrap_init(et_uart_wrap_handle_t *handle,
                                   const et_uart_wrap_config_t *config);
/** Disable and release one initialized UART handle. */
et_wrap_status_t et_uart_wrap_deinit(et_uart_wrap_handle_t *handle);
/** Enable selected normalized UART interrupt sources. */
et_wrap_status_t et_uart_wrap_enable_interrupts(et_uart_wrap_handle_t *handle,
                                                uint32_t interrupt_flags);
/** Disable selected normalized UART interrupt sources. */
et_wrap_status_t et_uart_wrap_disable_interrupts(et_uart_wrap_handle_t *handle,
                                                 uint32_t interrupt_flags);
/** Read interrupt, event, line and error facts without a test verdict. */
et_wrap_status_t et_uart_wrap_get_interrupt_status(et_uart_wrap_handle_t *handle,
                                                   et_uart_wrap_irq_status_t *status);
/** Clear clearable UART interrupt/error state owned by the handle. */
et_wrap_status_t et_uart_wrap_clear_interrupts(et_uart_wrap_handle_t *handle);
/** Read available bytes without exceeding capacity; WOULD_BLOCK is explicit. */
et_wrap_status_t et_uart_wrap_read(et_uart_wrap_handle_t *handle, uint8_t *data, size_t capacity,
                                   et_uart_wrap_io_result_t *result);
/** Write as many bytes as hardware currently accepts. */
et_wrap_status_t et_uart_wrap_write(et_uart_wrap_handle_t *handle, const uint8_t *data,
                                    size_t length, et_uart_wrap_io_result_t *result);

/* Atomic feature operations.  Each function operates on one initialized
 * UART handle and maps only to the corresponding UART Driver API. */
et_wrap_status_t et_uart_wrap_get_snapshot(et_uart_wrap_handle_t *handle,
                                           et_uart_wrap_snapshot_t *snapshot);
/** Reset UART hardware while preserving the opaque handle identity. */
et_wrap_status_t et_uart_wrap_software_reset(et_uart_wrap_handle_t *handle);
/** Enable or disable UART internal loopback. */
et_wrap_status_t et_uart_wrap_set_loopback(et_uart_wrap_handle_t *handle, uint8_t enabled);
/** Apply FIFO enable state and TX/RX threshold configuration. */
et_wrap_status_t et_uart_wrap_configure_fifo(et_uart_wrap_handle_t *handle,
                                             const et_uart_wrap_fifo_config_t *config);
/** Read one coherent normalized UART status snapshot. */
et_wrap_status_t et_uart_wrap_get_status(et_uart_wrap_handle_t *handle,
                                         et_uart_wrap_status_t *status);
/** Assert or release continuous break generation. */
et_wrap_status_t et_uart_wrap_set_break(et_uart_wrap_handle_t *handle, uint8_t enabled);
/** Halt or resume UART transfers using the chip Driver feature. */
et_wrap_status_t et_uart_wrap_set_halt(et_uart_wrap_handle_t *handle, uint8_t enabled);
/** Configure UART DMA mode and FIFO thresholds without configuring DMA itself. */
et_wrap_status_t et_uart_wrap_set_dma_mode(et_uart_wrap_handle_t *handle, uint8_t dma_mode,
                                           uint8_t tx_threshold, uint8_t rx_threshold);
/** Apply one complete 9-bit address/data mode configuration. */
et_wrap_status_t et_uart_wrap_configure_nine_bit(et_uart_wrap_handle_t *handle,
                                                 const et_uart_wrap_nine_bit_config_t *config);
/** Read available 9-bit items into caller storage. */
et_wrap_status_t et_uart_wrap_read_nine_bit(et_uart_wrap_handle_t *handle, uint16_t *data,
                                            size_t capacity, et_uart_wrap_io_result_t *result);
/** Write bounded 9-bit items from caller storage. */
et_wrap_status_t et_uart_wrap_write_nine_bit(et_uart_wrap_handle_t *handle, const uint16_t *data,
                                             size_t length, et_uart_wrap_io_result_t *result);
/** Enable or disable automatic RTS/CTS flow control. */
et_wrap_status_t et_uart_wrap_set_flow_control(et_uart_wrap_handle_t *handle, uint8_t enabled);
/** Set UART modem output signals from normalized flags. */
et_wrap_status_t et_uart_wrap_set_modem_control(et_uart_wrap_handle_t *handle,
                                                const et_uart_wrap_modem_control_t *control);
/** Read normalized modem input, delta, output and raw status facts. */
et_wrap_status_t et_uart_wrap_get_modem_status(et_uart_wrap_handle_t *handle,
                                               et_uart_wrap_modem_status_t *status);
/** Execute one intentionally partial write for FIFO/back-pressure validation. */
et_wrap_status_t et_uart_wrap_write_partial(et_uart_wrap_handle_t *handle, const uint8_t *data,
                                            size_t length, et_uart_wrap_io_result_t *result);
/** Trigger and capture bounded busy-detect recovery evidence. */
et_wrap_status_t et_uart_wrap_trigger_busy_detect(et_uart_wrap_handle_t *handle,
                                                  et_uart_wrap_busy_detect_result_t *result);
/** Configure shadow FIFO registers and return the applied state. */
et_wrap_status_t et_uart_wrap_shadow_fifo_config(et_uart_wrap_handle_t *handle, uint8_t enabled,
                                                 uint8_t tx_threshold, uint8_t rx_threshold,
                                                 et_uart_wrap_shadow_fifo_state_t *state);
/** Enable or disable direct FIFO-access test mode and report active state. */
et_wrap_status_t et_uart_wrap_fifo_access_set(et_uart_wrap_handle_t *handle, uint8_t enabled,
                                              uint8_t *active);
/** Read one byte from the TX FIFO test-access path. */
et_wrap_status_t et_uart_wrap_fifo_tx_read(et_uart_wrap_handle_t *handle, uint8_t *value);
/** Inject one RX FIFO byte with optional parity/framing error tags. */
et_wrap_status_t et_uart_wrap_fifo_rx_write(et_uart_wrap_handle_t *handle, uint8_t value,
                                            uint8_t parity_error, uint8_t framing_error);

#endif
