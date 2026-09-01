#ifndef ET_CONTROL_UART_H
#define ET_CONTROL_UART_H

/**
 * @file et_control_uart.h
 * @brief Board-configured UART transport used exclusively by the PC protocol.
 *
 * Control UART owns transport GPIO setup, UART lifetime, RX/TX rings and its
 * protocol IRQ callback. It is infrastructure, not an IP test Service.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_gpio_wrap.h"
#include "et_irq_manager.h"
#include "et_protocol.h"
#include "et_ring_buffer.h"
#include "et_uart_wrap.h"

typedef enum
{
    ET_CONTROL_UART_MODE_POLLING = 0u, /**< CPU polls the UART Driver. */
    ET_CONTROL_UART_MODE_IRQ = 1u,     /**< IRQ moves bytes through rings. */
    ET_CONTROL_UART_MODE_DMA = 2u      /**< Reserved until transport DMA exists. */
} et_control_uart_mode_t;

/** Board-resolved transport configuration and caller-owned ring storage. */
typedef struct
{
    et_uart_wrap_config_t uart;    /**< Logical control UART configuration. */
    et_gpio_wrap_config_t tx_gpio; /**< Board TX pin/function selection. */
    et_gpio_wrap_config_t rx_gpio; /**< Board RX pin/function selection. */
    et_irq_manager_t *irq_manager; /**< Shared runtime IRQ manager. */
    uint8_t irq_priority;          /**< Board-selected control UART priority. */
    uint8_t rx_mode;               /**< One et_control_uart_mode_t value. */
    uint8_t tx_mode;               /**< One et_control_uart_mode_t value. */
    uint8_t reserved8;
    uint8_t *rx_storage; /**< Caller-owned RX ring storage. */
    size_t rx_capacity;  /**< Physical RX storage size. */
    uint8_t *tx_storage; /**< Caller-owned TX ring storage. */
    size_t tx_capacity;  /**< Physical TX storage size. */
} et_control_uart_config_t;

/** Cumulative transport facts; no field is a test verdict. */
typedef struct
{
    uint32_t rx_bytes;          /**< Bytes accepted from UART hardware. */
    uint32_t tx_bytes;          /**< Bytes committed to UART hardware. */
    uint32_t rx_overflow_bytes; /**< Bytes dropped because RX ring was full. */
    uint32_t port_errors;       /**< UART or transport maintenance failures. */
} et_control_uart_stats_t;

typedef struct
{
    et_control_uart_config_t config;
    et_uart_wrap_handle_t uart;
    et_irq_route_t irq_route;
    et_ring_buffer_t rx_ring;
    et_ring_buffer_t tx_ring;
    et_control_uart_stats_t stats;
    uint8_t opened;                   /**< Transport accepts protocol I/O. */
    uint8_t uart_initialized;         /**< UART Wrap handle is live. */
    uint8_t irq_bound;                /**< IRQ callback ownership is active. */
    uint8_t irq_enabled;              /**< UART RX-related sources are enabled. */
    volatile uint8_t rx_idle_pending; /**< IRQ reported an idle boundary. */
    uint8_t reserved8[3];
} et_control_uart_t;

/** Validate configuration and initialize software state without opening UART. */
int et_control_uart_init(et_control_uart_t *transport, const et_control_uart_config_t *config);
/** Configure board pins/UART and bind transport IRQ resources. */
int et_control_uart_open(et_control_uart_t *transport);
/** Disable transport IRQs, release bindings and deinitialize UART. */
int et_control_uart_close(et_control_uart_t *transport);
/** Make bounded polling-mode and queued-TX progress outside interrupt context. */
void et_control_uart_poll(et_control_uart_t *transport);
/** Atomically consume one RX-idle notification. */
int et_control_uart_take_rx_idle(et_control_uart_t *transport);
/** Build the non-blocking callbacks consumed by Protocol. */
et_protocol_io_t et_control_uart_protocol_io(et_control_uart_t *transport);
/** Return read-only cumulative transport facts. */
const et_control_uart_stats_t *et_control_uart_stats(const et_control_uart_t *transport);

#endif
