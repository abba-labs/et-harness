#include "et_control_uart.h"

/**
 * @file et_control_uart.c
 * @brief UART protocol transport with short ISR work and ring-buffer handoff.
 */

#include <string.h>

#define ET_CONTROL_UART_SCRATCH_SIZE 32u

/**
 * @brief Drain available UART RX bytes into the bounded protocol receive ring.
 *
 * @param[in,out] transport Control UART transport that owns the UART handle and RX ring.
 *
 * @note This function reads UART hardware in bounded scratch chunks. Ring overflow is recorded in
 *       transport statistics; ET-Frame parsing is deliberately left to thread context.
 */
static void receive_from_port(et_control_uart_t *transport)
{
    uint8_t scratch[ET_CONTROL_UART_SCRATCH_SIZE];
    et_uart_wrap_io_result_t result;
    et_wrap_status_t status;
    size_t received;
    size_t stored;

    /* Drain in bounded chunks; ring overflow is recorded rather than blocking ISR. */
    do
    {
        status = et_uart_wrap_read(&transport->uart, scratch, sizeof(scratch), &result);

        if (status != ET_WRAP_STATUS_OK)
        {
            ++transport->stats.port_errors;
            break;
        }

        received = (size_t)result.transferred;
        stored = et_ring_buffer_write(&transport->rx_ring, scratch, received);
        transport->stats.rx_bytes += (uint32_t)stored;
        transport->stats.rx_overflow_bytes += (uint32_t)(received - stored);
    } while ((received == sizeof(scratch)) && (et_ring_buffer_space(&transport->rx_ring) > 0u));
}

/**
 * @brief Advance bounded control UART transmission from the protocol transmit ring.
 *
 * @param[in,out] transport Control UART transport that owns the UART handle and TX ring.
 *
 * @note This function may write UART hardware. It peeks before each write so a short hardware
 *       transfer removes only bytes that the UART actually accepted.
 */
static void transmit_to_port(et_control_uart_t *transport)
{
    uint8_t scratch[ET_CONTROL_UART_SCRATCH_SIZE];
    et_uart_wrap_io_result_t result;
    et_wrap_status_t status;
    size_t available;
    size_t transmitted;

    /* Peek first so a short hardware write consumes only committed bytes. */
    do
    {
        available = et_ring_buffer_peek(&transport->tx_ring, scratch, sizeof(scratch));

        if (available == 0u)
        {
            break;
        }

        status = et_uart_wrap_write(&transport->uart, scratch, available, &result);

        if (status != ET_WRAP_STATUS_OK)
        {
            ++transport->stats.port_errors;
            break;
        }

        transmitted = (size_t)result.transferred;

        if (transmitted > available)
        {
            transmitted = available;
        }

        (void)et_ring_buffer_discard(&transport->tx_ring, transmitted);
        transport->stats.tx_bytes += (uint32_t)transmitted;
    } while ((transmitted == available) && (available != 0u));
}

/**
 * @brief Build the UART interrupt-source mask required by the selected RX mode.
 *
 * @param[in] transport Control UART transport whose immutable configuration selects the RX mode.
 *
 * @note This helper only derives a normalized Wrap mask and does not access UART or NVIC hardware.
 *
 * @return UART Wrap interrupt-source mask for the dedicated control channel.
 */
static uint32_t control_uart_interrupt_mask(const et_control_uart_t *transport)
{
    uint32_t mask = ET_UART_WRAP_IRQ_ERROR;

    if (transport->config.rx_mode == ET_CONTROL_UART_MODE_IRQ)
    {
        mask |= ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_RX_IDLE;
    }

    return mask;
}

/**
 * @brief Capture bounded control UART receive and error facts from interrupt context.
 *
 * @param[in,out] context Control UART transport registered as the IRQ callback context.
 * @param[in] irq_line Physical IRQ line reported by the IRQ manager.
 * @param[in] route_events Normalized route events reported by the IRQ manager.
 *
 * @note This callback executes in interrupt context and must remain bounded. It may read and clear
 *       UART interrupt state and move RX bytes into the ring, but it never parses ET-Frames.
 */
static void control_uart_irq_handler(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_control_uart_t *transport = (et_control_uart_t *)context;
    et_uart_wrap_irq_status_t status;

    (void)irq_line;
    (void)route_events;

    if ((transport == NULL) || (transport->opened == 0u))
    {
        return;
    }

    if (et_uart_wrap_get_interrupt_status(&transport->uart, &status) != ET_WRAP_STATUS_OK)
    {
        ++transport->stats.port_errors;

        return;
    }

    /* ISR records/moves bounded facts only; frame parsing remains in main loop. */
    if ((status.interrupt_flags & ET_UART_WRAP_IRQ_RX_READY) != 0u)
    {
        receive_from_port(transport);
    }

    if ((status.interrupt_flags & ET_UART_WRAP_IRQ_RX_IDLE) != 0u)
    {
        transport->rx_idle_pending = 1u;
    }

    if ((status.interrupt_flags & (ET_UART_WRAP_IRQ_ERROR | ET_UART_WRAP_IRQ_OTHER)) != 0u)
    {
        (void)et_uart_wrap_clear_interrupts(&transport->uart);
        ++transport->stats.port_errors;
    }
}

/**
 * @brief Read already-buffered control UART bytes through the ET Protocol IO adapter.
 *
 * @param[in,out] context Control UART transport used as the protocol IO context.
 * @param[out] data Destination buffer that receives bytes removed from the RX ring.
 * @param[in] capacity Maximum number of bytes that may be copied to data.
 *
 * @note This adapter consumes only the software RX ring and does not access UART hardware.
 *
 * @return Number of bytes copied from the RX ring.
 */
static size_t protocol_read(void *context, uint8_t *data, size_t capacity)
{
    et_control_uart_t *transport = (et_control_uart_t *)context;

    return et_ring_buffer_read(&transport->rx_ring, data, capacity);
}

/**
 * @brief Queue ET Protocol response bytes and kick bounded control UART transmission.
 *
 * @param[in,out] context Control UART transport used as the protocol IO context.
 * @param[in] data Protocol bytes to queue for transmission.
 * @param[in] length Number of bytes requested for transmission.
 *
 * @note The complete message is accepted only when the TX ring has enough space. A successful
 *       queue operation may immediately write UART hardware through transmit_to_port().
 *
 * @return Number of bytes queued, or zero when the complete message cannot be accepted.
 */
static size_t protocol_write(void *context, const uint8_t *data, size_t length)
{
    et_control_uart_t *transport = (et_control_uart_t *)context;
    size_t written;

    if (et_ring_buffer_space(&transport->tx_ring) < length)
    {
        return 0u;
    }

    written = et_ring_buffer_write(&transport->tx_ring, data, length);
    transmit_to_port(transport);

    return written;
}

/**
 * @brief Initialize software-owned control UART transport state from immutable configuration.
 *
 * @param[out] transport Control UART transport instance to initialize.
 * @param[in] config Board-selected UART, GPIO, IRQ and ring-buffer configuration.
 *
 * @note This function initializes rings and local ownership state only. It does not configure GPIO,
 *       UART or interrupt-controller hardware; those side effects begin in et_control_uart_open().
 *
 * @return 0 when the configuration and ring storage are valid.
 * @return -1 when required pointers, modes or ring-buffer storage are invalid.
 */
int et_control_uart_init(et_control_uart_t *transport, const et_control_uart_config_t *config)
{
    if ((transport == NULL) || (config == NULL) || (config->irq_manager == NULL) ||
        (config->rx_mode == ET_CONTROL_UART_MODE_DMA) ||
        (config->tx_mode == ET_CONTROL_UART_MODE_DMA) ||
        (config->tx_mode == ET_CONTROL_UART_MODE_IRQ) ||
        (config->rx_mode > ET_CONTROL_UART_MODE_DMA) ||
        (config->tx_mode > ET_CONTROL_UART_MODE_DMA) ||
        (et_ring_buffer_init(&transport->rx_ring, config->rx_storage, config->rx_capacity) != 0) ||
        (et_ring_buffer_init(&transport->tx_ring, config->tx_storage, config->tx_capacity) != 0))
    {
        return -1;
    }

    transport->config = *config;
    (void)memset(&transport->uart, 0, sizeof(transport->uart));
    (void)memset(&transport->stats, 0, sizeof(transport->stats));
    transport->opened = 0u;
    transport->uart_initialized = 0u;
    transport->irq_bound = 0u;
    transport->irq_enabled = 0u;
    transport->rx_idle_pending = 0u;

    return 0;
}

/**
 * @brief Configure the dedicated control UART and acquire its managed IRQ ownership.
 *
 * @param[in,out] transport Initialized control UART transport to open.
 *
 * @note This function configures board GPIO routes, initializes UART hardware, binds the IRQ route
 *       and enables UART interrupt sources. Failures after UART initialization roll back through
 *       et_control_uart_close().
 *
 * @return 0 when UART hardware and required IRQ ownership are active.
 * @return -1 when configuration, route binding or interrupt enable fails.
 */
int et_control_uart_open(et_control_uart_t *transport)
{
    uint32_t interrupt_mask;

    /* Phase 1: Validate ownership and initialize the board-selected UART hardware path. */
    if ((transport == NULL) || (transport->opened != 0u))
    {
        return -1;
    }

    if ((et_gpio_wrap_configure(&transport->config.tx_gpio) != ET_WRAP_STATUS_OK) ||
        (et_gpio_wrap_configure(&transport->config.rx_gpio) != ET_WRAP_STATUS_OK) ||
        (et_uart_wrap_init(&transport->uart, &transport->config.uart) != ET_WRAP_STATUS_OK))
    {
        return -1;
    }

    transport->uart_initialized = 1u;
    interrupt_mask = control_uart_interrupt_mask(transport);

    /* Phase 2: Resolve and bind the logical control UART route before enabling its source. */
    if (et_uart_wrap_get_irq_route(transport->config.uart.uart_id, interrupt_mask,
                                   &transport->irq_route) != ET_WRAP_STATUS_OK)
    {
        (void)et_control_uart_close(transport);

        return -1;
    }

    if (et_irq_manager_bind(transport->config.irq_manager, &transport->irq_route,
                            transport->config.irq_priority, control_uart_irq_handler,
                            transport) != 0)
    {
        (void)et_control_uart_close(transport);

        return -1;
    }

    transport->irq_bound = 1u;
    transport->opened = 1u;
    /* Publish cleanup ownership before a level-sensitive enable call. */
    transport->irq_enabled = 1u;

    /* Phase 3: Enable the UART source only after cleanup ownership is fully published. */
    if (et_uart_wrap_enable_interrupts(&transport->uart, interrupt_mask) != ET_WRAP_STATUS_OK)
    {
        transport->opened = 0u;
        (void)et_control_uart_close(transport);

        return -1;
    }

    return 0;
}

/**
 * @brief Release control UART interrupt ownership and return the transport to idle state.
 *
 * @param[in,out] transport Control UART transport whose acquired resources must be released.
 *
 * @note Cleanup is performed in reverse ownership order: disable the UART source, unbind the route,
 *       then deinitialize UART hardware. A cleanup failure is reported and retained in statistics;
 *       later ownership stages are not falsely marked as released.
 *
 * @return 0 when every owned resource is released or was already idle.
 * @return -1 when the transport is invalid or a hardware/IRQ cleanup operation fails.
 */
int et_control_uart_close(et_control_uart_t *transport)
{
    uint32_t interrupt_mask;

    if (transport == NULL)
    {
        return -1;
    }

    transport->opened = 0u;
    interrupt_mask = control_uart_interrupt_mask(transport);

    /* Phase 1: Quiesce the UART interrupt source before releasing shared IRQ routing. */
    if (transport->irq_enabled != 0u)
    {
        if (et_uart_wrap_disable_interrupts(&transport->uart, interrupt_mask) != ET_WRAP_STATUS_OK)
        {
            ++transport->stats.port_errors;

            return -1;
        }

        transport->irq_enabled = 0u;
    }

    /* Phase 2: Remove the IRQ callback only after the hardware source is disabled. */
    if (transport->irq_bound != 0u)
    {
        if (et_irq_manager_unbind(transport->config.irq_manager, transport->irq_route.irq_line,
                                  control_uart_irq_handler, transport) != 0)
        {
            ++transport->stats.port_errors;

            return -1;
        }

        transport->irq_bound = 0u;
    }

    /* Phase 3: Deinitialize UART hardware after no callback can observe the transport. */
    if (transport->uart_initialized != 0u)
    {
        if (et_uart_wrap_deinit(&transport->uart) != ET_WRAP_STATUS_OK)
        {
            ++transport->stats.port_errors;

            return -1;
        }

        transport->uart_initialized = 0u;
    }

    return 0;
}

/**
 * @brief Advance deferred control UART RX and TX work from thread context.
 *
 * @param[in,out] transport Open control UART transport to service.
 *
 * @note This function is intended for the cooperative main loop, not interrupt context. Polling RX
 *       is serviced only when selected by configuration; pending TX bytes are always advanced.
 */
void et_control_uart_poll(et_control_uart_t *transport)
{
    if ((transport == NULL) || (transport->opened == 0u))
    {
        return;
    }

    if (transport->config.rx_mode == ET_CONTROL_UART_MODE_POLLING)
    {
        receive_from_port(transport);
    }

    transmit_to_port(transport);
}

/**
 * @brief Atomically consume one receive-idle indication latched by the UART IRQ callback.
 *
 * @param[in,out] transport Control UART transport that owns the pending idle flag.
 *
 * @note The flag is read and cleared inside the IRQ manager critical section. This function does
 *       not read or clear UART hardware state.
 *
 * @return Nonzero when an RX-idle indication was pending, otherwise zero.
 */
int et_control_uart_take_rx_idle(et_control_uart_t *transport)
{
    uint32_t key;
    int pending;

    if (transport == NULL)
    {
        return 0;
    }

    key = et_irq_manager_enter_critical();
    pending = (transport->rx_idle_pending != 0u);
    transport->rx_idle_pending = 0u;
    et_irq_manager_exit_critical(key);

    return pending;
}

/**
 * @brief Build the ET Protocol IO adapter backed by the control UART transport.
 *
 * @param[in,out] transport Control UART transport stored as the adapter callback context.
 *
 * @note This function only constructs callback bindings and does not access UART hardware or rings.
 *
 * @return Protocol IO adapter containing the control UART read and write callbacks.
 */
et_protocol_io_t et_control_uart_protocol_io(et_control_uart_t *transport)
{
    et_protocol_io_t io;

    io.context = transport;
    io.read = protocol_read;
    io.write = protocol_write;

    return io;
}

/**
 * @brief Return the current control-channel transport counters.
 *
 * @param[in] transport Control UART transport whose counters are requested.
 *
 * @note The returned pointer aliases transport-owned storage and remains valid only while the
 *       transport object itself remains valid. No hardware state is read.
 *
 * @return Pointer to immutable transport counters, or NULL when transport is NULL.
 */
const et_control_uart_stats_t *et_control_uart_stats(const et_control_uart_t *transport)
{
    return (transport == NULL) ? NULL : &transport->stats;
}
