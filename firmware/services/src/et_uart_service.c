#include "et_uart_service.h"

/**
 * @file et_uart_service.c
 * @brief Decode UART commands, manage bounded capture and return UART facts.
 *
 * Interrupt context only captures normalized evidence and bounded RX data.
 * Multi-command sequencing and all final assertions remain in the PC Case.
 */

#include <limits.h>
#include <stddef.h>
#include <string.h>

#include "et_message.h"

/********************************** Wire Helpers **********************************/

/**
 * @brief Decode one unaligned little-endian 32-bit UART Wire field.
 *
 * @param[in] data Four request bytes containing the encoded value.
 *
 * @note This helper reads caller-owned Wire memory only and has no UART hardware or Service-state side effect.
 *
 * @return Decoded 32-bit value.
 */

static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Decode one unaligned little-endian 16-bit UART Wire field.
 *
 * @param[in] data Two request bytes containing the encoded value.
 *
 * @note This helper performs byte assembly only and does not access UART hardware.
 *
 * @return Decoded 16-bit value.
 */

static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian UART Wire field.
 *
 * @param[out] data Four-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note Only caller-owned response memory is modified; UART hardware and Service state are untouched.
 */

static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Encode one 16-bit value into an unaligned little-endian UART Wire field.
 *
 * @param[out] data Two-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note Only caller-owned response memory is modified; no UART operation is issued.
 */

static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one 64-bit value into two canonical little-endian UART Wire words.
 *
 * @param[out] data Eight-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note The helper composes two 32-bit Wire writes and assigns no address semantics to the value.
 */

static void write_u64(uint8_t *data, uint64_t value)
{
    write_u32(data, (uint32_t)value);
    write_u32(&data[4], (uint32_t)(value >> 32u));
}

/**
 * @brief Verify that one reserved UART Wire region contains only zero bytes.
 *
 * @param[in] data Reserved request bytes to inspect.
 * @param[in] length Number of bytes to validate.
 *
 * @note Rejecting nonzero reserved bytes prevents this Firmware from silently accepting a future Wire extension.
 *
 * @return Nonzero when every inspected byte is zero, otherwise zero.
 */

static uint8_t bytes_are_zero(const uint8_t *data, uint16_t length)
{
    uint16_t index;

    for (index = 0u; index < length; ++index)
    {
        if (data[index] != 0u)
        {
            return 0u;
        }
    }

    return 1u;
}

/**
 * @brief Normalize one UART Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status Chip-neutral UART Wrap status to translate.
 *
 * @note Selected-chip Driver status values never cross the Service boundary through this helper.
 *
 * @return Stable ET status corresponding to the supplied Wrap status.
 */

static uint16_t status_from_wrap(et_wrap_status_t status)
{
    switch (status)
    {
        case ET_WRAP_STATUS_OK:
        {
            return ET_STATUS_OK;
        }

        case ET_WRAP_STATUS_INVALID_ARGUMENT:
        case ET_WRAP_STATUS_STATE_ERROR:
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_BUSY:
        case ET_WRAP_STATUS_NO_RESOURCE:
        case ET_WRAP_STATUS_TIMEOUT:
        {
            return ET_STATUS_BUSY;
        }

        default:
        {
            return ET_STATUS_INTERNAL_ERROR;
        }
    }
}

/********************************** IRQ Mapping **********************************/

/**
 * @brief Translate stable UART Wire interrupt bits into normalized UART Wrap events.
 *
 * @param[in] wire_flags Stable interrupt-source mask received from the PC command contract.
 *
 * @note This is pure namespace translation; it neither enables an interrupt nor touches IRQ Manager state.
 *
 * @return Normalized UART Wrap event mask represented by the supported Wire bits.
 */

static uint32_t irq_wire_to_wrap(uint32_t wire_flags)
{
    uint32_t wrap_flags = 0u;

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_RX_READY) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_RX_READY;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_TX_READY) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_TX_READY;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_LINE_ERROR) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_ERROR;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_MODEM_STATUS) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_MODEM_STATUS;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_TIMEOUT) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_RX_IDLE;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_BUSY) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_BUSY;
    }

    if ((wire_flags & ET_UART_SERVICE_IRQ_WIRE_NINE_BIT) != 0u)
    {
        wrap_flags |= ET_UART_WRAP_IRQ_ADDRESS_RECEIVED;
    }

    return wrap_flags;
}

/**
 * @brief Translate normalized UART Wrap interrupt events into stable Wire interrupt bits.
 *
 * @param[in] wrap_flags Normalized UART Wrap interrupt-event mask.
 *
 * @note The conversion is used for evidence reporting only and does not acknowledge or mask hardware sources.
 *
 * @return Stable UART Wire interrupt mask represented by the normalized events.
 */

static uint32_t irq_wrap_to_wire(uint32_t wrap_flags)
{
    uint32_t wire_flags = 0u;

    if ((wrap_flags & ET_UART_WRAP_IRQ_RX_READY) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_RX_READY;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_TX_READY) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_TX_READY;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_ERROR) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_LINE_ERROR;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_MODEM_STATUS) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_MODEM_STATUS;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_RX_IDLE) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_TIMEOUT;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_BUSY) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_BUSY;
    }

    if ((wrap_flags & ET_UART_WRAP_IRQ_ADDRESS_RECEIVED) != 0u)
    {
        wire_flags |= ET_UART_SERVICE_IRQ_WIRE_NINE_BIT;
    }

    return wire_flags;
}

/********************************** Threshold Mapping **********************************/

/**
 * @brief Validate one requested TX FIFO threshold and preserve its stable Wrap value.
 *
 * @param[in] wire_threshold TX threshold received on the stable command contract.
 * @param[out] wrap_threshold Validated UART Wrap TX threshold.
 *
 * @note Service validates the public enumeration only; selected-chip SDK mapping remains in UART Wrap.
 *
 * @return ET_WRAP_STATUS_OK for a supported threshold, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_tx_threshold(uint8_t wire_threshold, uint8_t *wrap_threshold)
{
    if (wrap_threshold == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (wire_threshold)
    {
        case ET_UART_WRAP_TXFIFO_THRESHOLD_0:
        {
            *wrap_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_0;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_2:
        {
            *wrap_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_2;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_4:
        {
            *wrap_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_4;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_8:
        {
            *wrap_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_8;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Validate one requested RX FIFO threshold and preserve its stable Wrap value.
 *
 * @param[in] wire_threshold RX threshold received on the stable command contract.
 * @param[out] wrap_threshold Validated UART Wrap RX threshold.
 *
 * @note Service validates the public enumeration only; selected-chip SDK mapping remains in UART Wrap.
 *
 * @return ET_WRAP_STATUS_OK for a supported threshold, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_rx_threshold(uint8_t wire_threshold, uint8_t *wrap_threshold)
{
    if (wrap_threshold == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (wire_threshold)
    {
        case ET_UART_WRAP_RXFIFO_THRESHOLD_1:
        {
            *wrap_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_1;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_4:
        {
            *wrap_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_4;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_8:
        {
            *wrap_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_8;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_14:
        {
            *wrap_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_14;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/********************************** Transfer Helpers **********************************/

/**
 * @brief Drain currently available stale UART RX data with a fixed Service-owned bound.
 *
 * @param[in,out] service Initialized UART Service whose Wrap handle is read.
 *
 * @note The function never spins until the FIFO is empty indefinitely: it performs at most ET_UART_SERVICE_RX_DRAIN_LIMIT bounded reads and returns BUSY if stale data persists.
 *
 * @return UART Wrap status, or ET_WRAP_STATUS_BUSY when the bounded drain limit is exhausted.
 */

static et_wrap_status_t flush_rx_bounded(et_uart_service_t *service)
{
    uint8_t scratch[ET_UART_SERVICE_RX_DRAIN_CHUNK_SIZE];
    et_uart_wrap_io_result_t result;
    et_wrap_status_t status;
    uint32_t drain;

    for (drain = 0u; drain < ET_UART_SERVICE_RX_DRAIN_LIMIT; ++drain)
    {
        status = et_uart_wrap_read(&service->handle, scratch, sizeof(scratch), &result);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status;
        }

        if (result.transferred == 0u)
        {
            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_BUSY;
}

/********************************** IRQ and Capture Management **********************************/

static void uart_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events);

/**
 * @brief Mark UART IRQ evidence as being updated by advancing its seqlock generation.
 *
 * @param[in,out] service UART Service whose callback-owned evidence is about to change.
 *
 * @note The odd generation is only the write-side marker; callers provide the required IRQ or critical-section synchronization.
 */

static void uart_irq_evidence_begin(et_uart_service_t *service)
{
    ++service->irq_result_generation;
}

/**
 * @brief Publish completion of one UART IRQ evidence update by advancing its generation.
 *
 * @param[in,out] service UART Service whose evidence update has completed.
 *
 * @note The resulting even generation lets thread context reject torn snapshots without blocking the ISR.
 */

static void uart_irq_evidence_end(et_uart_service_t *service)
{
    ++service->irq_result_generation;
}

/**
 * @brief Mark bounded UART capture state as being updated.
 *
 * @param[in,out] service UART Service whose capture state/data is about to change.
 *
 * @note This is the capture seqlock write-side marker and does not enter a critical section itself.
 */

static void uart_capture_update_begin(et_uart_service_t *service)
{
    ++service->capture_generation;
}

/**
 * @brief Publish completion of one bounded UART capture update.
 *
 * @param[in,out] service UART Service whose capture update has completed.
 *
 * @note The even generation is consumed by CAPTURE_GET to detect a coherent state/data snapshot.
 */

static void uart_capture_update_end(et_uart_service_t *service)
{
    ++service->capture_generation;
}

/**
 * @brief Publish the UART capture lifecycle counters atomically from thread context.
 *
 * @param[in,out] service UART Service whose capture lifecycle is updated.
 * @param[in] active New capture-active flag.
 * @param[in] expected Requested total capture byte count.
 * @param[in] received Currently stored capture byte count.
 *
 * @note IRQ Manager critical protection brackets the capture seqlock update; this helper does not enable, disable or drain UART hardware.
 */

static void uart_store_capture_state(et_uart_service_t *service, uint8_t active, uint16_t expected,
                                     uint16_t received)
{
    uint32_t key;

    if (service == NULL)
    {
        return;
    }

    key = et_irq_manager_enter_critical();
    uart_capture_update_begin(service);
    service->capture_active = active;
    service->capture_expected = expected;
    service->capture_received = received;
    uart_capture_update_end(service);
    et_irq_manager_exit_critical(key);
}

/**
 * @brief Clear all callback-owned UART IRQ evidence atomically from thread context.
 *
 * @param[in,out] service UART Service whose pending/active/counter/error evidence is reset.
 *
 * @note Only Service-local evidence is cleared; UART peripheral pending state and IRQ routing are not changed here.
 */

static void uart_clear_irq_evidence(et_uart_service_t *service)
{
    uint32_t key;

    if (service == NULL)
    {
        return;
    }

    key = et_irq_manager_enter_critical();
    uart_irq_evidence_begin(service);
    service->irq_pending_mask = 0u;
    service->irq_active_mask = 0u;
    service->irq_event_count = 0u;
    service->irq_overflow_count = 0u;
    service->irq_fault_count = 0u;
    service->latched_error_flags = 0u;
    uart_irq_evidence_end(service);
    et_irq_manager_exit_critical(key);
}

/**
 * @brief Record one bounded UART IRQ maintenance failure without wrapping the diagnostic count.
 *
 * @param[in,out] service UART Service that owns the managed IRQ session.
 *
 * @note This helper is safe for callback use: it updates only fixed Service evidence and performs no blocking hardware recovery.
 */

static void uart_note_irq_fault(et_uart_service_t *service)
{
    if (service == NULL)
    {
        return;
    }

    uart_irq_evidence_begin(service);

    if (service->irq_fault_count != UINT32_MAX)
    {
        ++service->irq_fault_count;
    }

    uart_irq_evidence_end(service);
}

/**
 * @brief Reconcile requested UART interrupt ownership with capture-owned and suppressed sources.
 *
 * @param[in,out] service Initialized UART Service whose hardware interrupt mask and tracked applied mask are reconciled.
 *
 * @note The desired mask is the union of explicit PC requests and active capture sources minus one-shot suppressed events. Changes occur under IRQ Manager critical protection and failed enables roll back any disable performed in the same call.
 *
 * @return ET_WRAP_STATUS_OK when hardware and tracked mask agree, otherwise a Wrap error with best-effort rollback.
 */

static et_wrap_status_t uart_apply_irq_mask(et_uart_service_t *service)
{
    uint32_t desired;
    uint32_t disable_mask;
    uint32_t enable_mask;
    uint32_t key;
    et_wrap_status_t status;

    if ((service == NULL) || (service->initialized == 0u))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 1: Compute desired capture plus PC interrupt ownership under one critical section. */
    key = et_irq_manager_enter_critical();
    desired = irq_wire_to_wrap(service->irq_enabled_mask) & ~service->irq_suppressed_wrap_mask;

    if (service->capture_active != 0u)
    {
        desired |= ET_UART_SERVICE_CAPTURE_IRQ_EVENTS;
    }

    disable_mask = service->irq_applied_wrap_mask & ~desired;
    enable_mask = desired & ~service->irq_applied_wrap_mask;

    /* Phase 2: Remove sources no longer owned before exposing any newly requested source. */
    if (disable_mask != 0u)
    {
        status = et_uart_wrap_disable_interrupts(&service->handle, disable_mask);

        if (status != ET_WRAP_STATUS_OK)
        {
            et_irq_manager_exit_critical(key);

            return status;
        }

        service->irq_applied_wrap_mask &= ~disable_mask;
    }

    /* Phase 3: Publish and enable new sources, rolling back this transaction if enable fails. */
    if (enable_mask != 0u)
    {
        /* Publish before enabling a level source: TX-empty may preempt inside
         * the Driver call and must be able to mask its one-shot observation. */
        service->irq_applied_wrap_mask |= enable_mask;
        status = et_uart_wrap_enable_interrupts(&service->handle, enable_mask);

        if (status != ET_WRAP_STATUS_OK)
        {
            service->irq_applied_wrap_mask &= ~enable_mask;

            if (disable_mask != 0u)
            {
                service->irq_applied_wrap_mask |= disable_mask;

                if (et_uart_wrap_enable_interrupts(&service->handle, disable_mask) !=
                    ET_WRAP_STATUS_OK)
                {
                    service->irq_applied_wrap_mask &= ~disable_mask;
                    et_irq_manager_exit_critical(key);

                    return ET_WRAP_STATUS_IO_ERROR;
                }
            }

            et_irq_manager_exit_critical(key);

            return status;
        }
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Change managed UART IRQ priority while preserving route ownership and applied sources.
 *
 * @param[in,out] service UART Service owning the current route, priority and applied source mask.
 * @param[in] priority Requested IRQ Manager priority.
 *
 * @note When a route is already bound, sources are quiesced before unbind/rebind. Any bind or reapply failure attempts to reconstruct the previous priority, binding and hardware source state rather than leaking ownership.
 *
 * @return ET_WRAP_STATUS_OK when the requested priority is active; otherwise BUSY/IO/Wrap status describing the failed transition.
 */

static et_wrap_status_t uart_rebind_irq_priority(et_uart_service_t *service, uint8_t priority)
{
    uint8_t old_priority;
    uint32_t old_applied;
    et_wrap_status_t status;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (service->irq_priority == priority)
    {
        return ET_WRAP_STATUS_OK;
    }

    /* Phase 1: Preserve the previous priority, binding and hardware source ownership. */
    old_priority = service->irq_priority;

    if (service->irq_bound == 0u)
    {
        service->irq_priority = priority;

        return ET_WRAP_STATUS_OK;
    }

    old_applied = service->irq_applied_wrap_mask;

    /* Phase 2: Quiesce applied peripheral sources before changing the CPU route. */
    if (old_applied != 0u)
    {
        status = et_uart_wrap_disable_interrupts(&service->handle, old_applied);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status;
        }

        service->irq_applied_wrap_mask = 0u;
    }

    if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line, uart_irq_callback,
                              service) != 0)
    {
        if (old_applied != 0u)
        {
            service->irq_applied_wrap_mask = old_applied;

            if (et_uart_wrap_enable_interrupts(&service->handle, old_applied) != ET_WRAP_STATUS_OK)
            {
                service->irq_applied_wrap_mask = 0u;

                return ET_WRAP_STATUS_IO_ERROR;
            }
        }

        return ET_WRAP_STATUS_IO_ERROR;
    }

    service->irq_bound = 0u;

    /* Phase 3: Bind the requested priority; reconstruct the old route if the bind fails. */
    if (et_irq_manager_bind(service->irq_manager, &service->irq_route, priority, uart_irq_callback,
                            service) != 0)
    {
        service->irq_bound = (et_irq_manager_bind(service->irq_manager, &service->irq_route,
                                                  old_priority, uart_irq_callback, service) == 0)
                                 ? 1u
                                 : 0u;
        service->irq_priority = old_priority;

        if ((service->irq_bound != 0u) && (old_applied != 0u))
        {
            service->irq_applied_wrap_mask = old_applied;

            if (et_uart_wrap_enable_interrupts(&service->handle, old_applied) != ET_WRAP_STATUS_OK)
            {
                service->irq_applied_wrap_mask = 0u;

                return ET_WRAP_STATUS_IO_ERROR;
            }
        }

        return ET_WRAP_STATUS_BUSY;
    }

    /* Phase 4: Reapply desired UART sources and rollback the complete route on failure. */
    service->irq_bound = 1u;
    service->irq_priority = priority;
    status = uart_apply_irq_mask(service);

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                    uart_irq_callback, service);
        service->irq_bound = (et_irq_manager_bind(service->irq_manager, &service->irq_route,
                                                  old_priority, uart_irq_callback, service) == 0)
                                 ? 1u
                                 : 0u;
        service->irq_priority = old_priority;
        service->irq_applied_wrap_mask = 0u;

        if ((service->irq_bound != 0u) && (uart_apply_irq_mask(service) != ET_WRAP_STATUS_OK))
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }

        return status;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Drain one currently available RX batch into the bounded Service capture buffer.
 *
 * @param[in,out] service UART Service that owns capture state, storage and the initialized Wrap handle.
 *
 * @note This callback helper performs one non-blocking Wrap read for the remaining requested bytes. Invalid transfer counts or read failures close capture and record an IRQ maintenance fault; it never waits for more data.
 */

static void uart_capture_drain(et_uart_service_t *service)
{
    et_uart_wrap_io_result_t result;
    uint16_t remaining;

    if ((service == NULL) || (service->capture_active == 0u))
    {
        return;
    }

    uart_capture_update_begin(service);
    remaining = (uint16_t)(service->capture_expected - service->capture_received);

    if ((remaining == 0u) ||
        (et_uart_wrap_read(&service->handle, &service->capture[service->capture_received],
                           remaining, &result) != ET_WRAP_STATUS_OK) ||
        (result.transferred > remaining))
    {
        service->capture_active = 0u;
        uart_note_irq_fault(service);
    }
    else
    {
        service->capture_received = (uint16_t)(service->capture_received + result.transferred);

        if (service->capture_received == service->capture_expected)
        {
            service->capture_active = 0u;
        }
    }

    uart_capture_update_end(service);
}

/**
 * @brief Capture normalized UART IRQ, error and optional RX-capture evidence without blocking.
 *
 * @param[in,out] context UART Service registered as IRQ callback context.
 * @param[in] irq_line Physical IRQ line reported by IRQ Manager.
 * @param[in] route_events Normalized route event mask associated with the binding.
 *
 * @note This function executes in interrupt context. It snapshots UART facts, latches bounded evidence, drains at most one available capture batch, suppresses TX-ready after one observation, clears only the sampled interrupt state and never performs a PC test verdict or retry loop.
 */

static void uart_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_uart_service_t *service = (et_uart_service_t *)context;
    et_uart_wrap_irq_status_t irq_status;
    uint32_t wire_events;
    uint8_t capture_was_active;

    (void)irq_line;
    (void)route_events;

    /* Phase 1: Reject stale callback entry before reading UART state. */
    if ((service == NULL) || (service->initialized == 0u) || (service->irq_bound == 0u))
    {
        return;
    }

    /* Phase 2: Snapshot normalized interrupt and line/error facts before acknowledgement. */
    if (et_uart_wrap_get_interrupt_status(&service->handle, &irq_status) != ET_WRAP_STATUS_OK)
    {
        uart_note_irq_fault(service);

        return;
    }

    wire_events = irq_wrap_to_wire(irq_status.interrupt_flags) & service->irq_enabled_mask;
    uart_irq_evidence_begin(service);
    service->latched_error_flags |= irq_status.error_flags;

    if (wire_events != 0u)
    {
        service->irq_pending_mask |= wire_events;
        service->irq_active_mask = wire_events;

        if (service->irq_event_count != UINT32_MAX)
        {
            ++service->irq_event_count;
        }
        else if (service->irq_overflow_count != UINT32_MAX)
        {
            ++service->irq_overflow_count;
        }
    }

    uart_irq_evidence_end(service);

    /* Phase 3: Drain one available capture batch while the pre-clear RX evidence is still valid. */
    capture_was_active = service->capture_active;

    if ((capture_was_active != 0u) &&
        ((irq_status.interrupt_flags & ET_UART_SERVICE_CAPTURE_IRQ_EVENTS) != 0u))
    {
        uart_capture_drain(service);
    }

    /* Phase 4: Suppress level-like TX-ready after one observation, then clear exactly the sampled IRQ state. */
    if ((wire_events & ET_UART_SERVICE_IRQ_WIRE_TX_READY) != 0u)
    {
        if (et_uart_wrap_disable_interrupts(&service->handle, ET_UART_WRAP_IRQ_TX_READY) ==
            ET_WRAP_STATUS_OK)
        {
            service->irq_applied_wrap_mask &= ~ET_UART_WRAP_IRQ_TX_READY;
            service->irq_suppressed_wrap_mask |= ET_UART_WRAP_IRQ_TX_READY;
        }
        else
        {
            uart_note_irq_fault(service);
        }
    }

    if (et_uart_wrap_clear_interrupts(&service->handle) != ET_WRAP_STATUS_OK)
    {
        uart_note_irq_fault(service);
    }

    /* Phase 5: Remove capture-owned sources after a capture completes or aborts. */
    if ((capture_was_active != 0u) && (service->capture_active == 0u) &&
        (uart_apply_irq_mask(service) != ET_WRAP_STATUS_OK))
    {
        uart_note_irq_fault(service);
    }
}

/**
 * @brief Stop the active UART capture and remove capture-owned interrupt requirements.
 *
 * @param[in,out] service UART Service whose capture lifecycle and applied IRQ mask are changed.
 *
 * @note Capture state is cleared before hardware reconciliation; if the IRQ-mask update fails, the prior capture counters are restored and the previous desired mask is reapplied best-effort.
 *
 * @return ET_WRAP_STATUS_OK when capture is cancelled or UART is idle, otherwise the IRQ-mask reconciliation error.
 */

static et_wrap_status_t uart_cancel_capture(et_uart_service_t *service)
{
    uint8_t old_active;
    uint16_t old_expected;
    uint16_t old_received;
    et_wrap_status_t status;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    old_active = service->capture_active;
    old_expected = service->capture_expected;
    old_received = service->capture_received;
    uart_store_capture_state(service, 0u, 0u, 0u);

    if (service->initialized == 0u)
    {
        return ET_WRAP_STATUS_OK;
    }

    status = uart_apply_irq_mask(service);

    if (status != ET_WRAP_STATUS_OK)
    {
        uart_store_capture_state(service, old_active, old_expected, old_received);
        (void)uart_apply_irq_mask(service);
    }

    return status;
}

/********************************** Lifecycle and FIFO/DMA State **********************************/

/**
 * @brief Release all UART Service runtime ownership and return the instance to deterministic idle state.
 *
 * @param[in,out] service UART Service whose interrupts, route, Wrap handle, capture and cached configuration state are torn down.
 *
 * @note Cleanup order is peripheral interrupt sources, IRQ Manager binding, then UART Wrap deinitialization. A failed hardware or unbind step stops teardown so ownership is not falsely reported as released; successful teardown resets all Service-local defaults/evidence.
 *
 * @return ET_WRAP_STATUS_OK when the Service is fully idle, otherwise the first cleanup error.
 */

static et_wrap_status_t uart_reset_to_idle(et_uart_service_t *service)
{
    et_wrap_status_t status;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 1: Quiesce peripheral interrupt sources while the current handle is still valid. */
    if ((service->initialized != 0u) && (service->irq_applied_wrap_mask != 0u))
    {
        status = et_uart_wrap_disable_interrupts(&service->handle, service->irq_applied_wrap_mask);

        if (status != ET_WRAP_STATUS_OK)
        {
            uart_note_irq_fault(service);

            return status;
        }

        service->irq_applied_wrap_mask = 0u;
    }

    /* Phase 2: Release the IRQ Manager route only after UART sources are disabled. */
    if (service->irq_bound != 0u)
    {
        if (et_irq_manager_unbind(service->irq_manager, service->irq_route.irq_line,
                                  uart_irq_callback, service) != 0)
        {
            uart_note_irq_fault(service);

            return ET_WRAP_STATUS_IO_ERROR;
        }

        service->irq_bound = 0u;
        (void)memset(&service->irq_route, 0, sizeof(service->irq_route));
        service->irq_priority = service->default_irq_priority;
    }

    /* Phase 3: Deinitialize/reset UART hardware after callback ownership is gone. */
    if (service->initialized != 0u)
    {
        status = et_uart_wrap_deinit(&service->handle);

        if (status != ET_WRAP_STATUS_OK)
        {
            uart_note_irq_fault(service);

            return status;
        }

        service->initialized = 0u;
    }

    /* Phase 4: Rebuild deterministic Service-local defaults and clear stale evidence. */
    (void)memset(&service->handle, 0, sizeof(service->handle));
    (void)memset(&service->irq_route, 0, sizeof(service->irq_route));
    service->irq_priority = service->default_irq_priority;

    uart_store_capture_state(service, 0u, 0u, 0u);
    service->irq_enabled_mask = 0u;
    service->irq_suppressed_wrap_mask = 0u;
    uart_clear_irq_evidence(service);
    service->fifo_enabled = 1u;
    service->fifo_tx_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_8;
    service->fifo_rx_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_1;
    service->dma_mode = ET_UART_WRAP_DMA_DISABLED;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply one FIFO-enable/threshold/DMA-mode tuple to UART hardware in dependency-safe order.
 *
 * @param[in,out] service Initialized UART Service whose Wrap handle is configured.
 * @param[in] enabled Requested FIFO enable state.
 * @param[in] tx_threshold Validated TX FIFO threshold.
 * @param[in] rx_threshold Validated RX FIFO threshold.
 * @param[in] dma_mode Requested UART DMA request mode.
 *
 * @note DMA cannot remain enabled while FIFO is disabled. Disable transitions clear DMA mode before FIFO disable; enable transitions configure FIFO before programming DMA mode. This helper does not commit cached Service fields.
 *
 * @return UART Wrap status from the hardware update, or INVALID_ARGUMENT for an inconsistent tuple.
 */

static et_wrap_status_t uart_write_fifo_dma_hardware(et_uart_service_t *service, uint8_t enabled,
                                                     uint8_t tx_threshold, uint8_t rx_threshold,
                                                     uint8_t dma_mode)
{
    et_uart_wrap_fifo_config_t config;
    et_wrap_status_t status;

    if ((service == NULL) || (enabled > 1u) || (dma_mode > ET_UART_WRAP_DMA_MULTI) ||
        ((enabled == 0u) && (dma_mode != ET_UART_WRAP_DMA_DISABLED)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(&config, 0, sizeof(config));
    config.struct_size = (uint16_t)sizeof(config);
    config.api_version = ET_UART_WRAP_API_VERSION;
    config.enabled = enabled;
    config.tx_threshold = tx_threshold;
    config.rx_threshold = rx_threshold;

    if (enabled == 0u)
    {
        status = et_uart_wrap_set_dma_mode(&service->handle, ET_UART_WRAP_DMA_DISABLED,
                                           tx_threshold, rx_threshold);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status;
        }

        return et_uart_wrap_configure_fifo(&service->handle, &config);
    }

    status = et_uart_wrap_configure_fifo(&service->handle, &config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return et_uart_wrap_set_dma_mode(&service->handle, dma_mode, tx_threshold, rx_threshold);
}

/**
 * @brief Apply FIFO/DMA hardware state transactionally and commit Service cache only on success.
 *
 * @param[in,out] service Initialized UART Service whose cached FIFO/DMA state is updated.
 * @param[in] enabled Requested FIFO enable state.
 * @param[in] tx_threshold Validated TX threshold.
 * @param[in] rx_threshold Validated RX threshold.
 * @param[in] dma_mode Requested UART DMA request mode.
 *
 * @note The previous tuple is retained before hardware programming. A failed update attempts a full hardware rollback; cached Service fields change only after success, and rollback failure is promoted to IO_ERROR.
 *
 * @return ET_WRAP_STATUS_OK on committed state, otherwise the update error or IO_ERROR when rollback also fails.
 */

static et_wrap_status_t uart_apply_fifo_dma_state(et_uart_service_t *service, uint8_t enabled,
                                                  uint8_t tx_threshold, uint8_t rx_threshold,
                                                  uint8_t dma_mode)
{
    et_wrap_status_t status;
    et_wrap_status_t rollback;
    uint8_t old_enabled;
    uint8_t old_tx;
    uint8_t old_rx;
    uint8_t old_mode;

    if ((service == NULL) || (service->initialized == 0u))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    old_enabled = service->fifo_enabled;
    old_tx = service->fifo_tx_threshold;
    old_rx = service->fifo_rx_threshold;
    old_mode = service->dma_mode;
    status = uart_write_fifo_dma_hardware(service, enabled, tx_threshold, rx_threshold, dma_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        rollback = uart_write_fifo_dma_hardware(service, old_enabled, old_tx, old_rx, old_mode);

        return (rollback == ET_WRAP_STATUS_OK) ? status : ET_WRAP_STATUS_IO_ERROR;
    }

    service->fifo_enabled = enabled;
    service->fifo_tx_threshold = tx_threshold;
    service->fifo_rx_threshold = rx_threshold;
    service->dma_mode = dma_mode;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Issue one bounded non-blocking 9-bit UART write and validate the returned transfer count.
 *
 * @param[in,out] service Initialized UART Service whose Wrap handle performs the write.
 * @param[in] data Array of validated 9-bit values.
 * @param[in] length Number of values offered in this atomic write.
 * @param[out] transferred_out Number of values accepted by hardware.
 *
 * @note The helper owns no retry/poll policy despite the command carrying a PC-side poll budget; it reports only the one Wrap operation's transfer fact.
 *
 * @return ET_WRAP_STATUS_OK when the one-shot result is valid, otherwise validation/Wrap/IO error.
 */

static et_wrap_status_t write_nine_bit_once(et_uart_service_t *service, const uint16_t *data,
                                            uint32_t length, uint32_t *transferred_out)
{
    et_uart_wrap_io_result_t result;
    et_wrap_status_t status;

    if ((service == NULL) || (data == NULL) || (length == 0u) || (transferred_out == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = et_uart_wrap_write_nine_bit(&service->handle, data, length, &result);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (result.transferred > length)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    *transferred_out = result.transferred;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Issue one bounded non-blocking 9-bit UART read and validate the returned transfer count.
 *
 * @param[in,out] service Initialized UART Service whose Wrap handle performs the read.
 * @param[out] data Caller-provided array receiving 9-bit values.
 * @param[in] length Maximum values accepted by the array.
 * @param[out] transferred_out Number of values read from hardware.
 *
 * @note The helper owns no retry loop; zero or partial transfer remains an observation for the PC control plane.
 *
 * @return ET_WRAP_STATUS_OK when the one-shot result is valid, otherwise validation/Wrap/IO error.
 */

static et_wrap_status_t read_nine_bit_once(et_uart_service_t *service, uint16_t *data,
                                           uint32_t length, uint32_t *transferred_out)
{
    et_uart_wrap_io_result_t result;
    et_wrap_status_t status;

    if ((service == NULL) || (data == NULL) || (length == 0u) || (transferred_out == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = et_uart_wrap_read_nine_bit(&service->handle, data, length, &result);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (result.transferred > length)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    *transferred_out = result.transferred;

    return ET_WRAP_STATUS_OK;
}

/********************************** Command Helpers **********************************/

/**
 * @brief Validate chip-independent UART baud, data-width, parity and stop-bit relationships.
 *
 * @param[in] config Versioned UART Wrap configuration decoded by the Service.
 *
 * @note Only stable public constraints are checked here. Chip baud limits and Driver enum translation remain owned by UART Wrap/Chip Config.
 *
 * @return Nonzero for a valid public line configuration, otherwise zero.
 */

static int uart_line_config_is_valid(const et_uart_wrap_config_t *config)
{
    if ((config == NULL) || (config->baudrate == 0u) ||
        (config->data_bits < ET_UART_WRAP_MIN_DATA_BITS) ||
        (config->data_bits > ET_UART_WRAP_MAX_DATA_BITS) ||
        (config->parity > ET_UART_WRAP_PARITY_STICK_ONE))
    {
        return 0;
    }

    if (config->stop_bits == ET_UART_WRAP_STOP_BITS_1)
    {
        return 1;
    }

    if (config->stop_bits == ET_UART_WRAP_STOP_BITS_1_5)
    {
        return config->data_bits == ET_UART_WRAP_MIN_DATA_BITS;
    }

    if (config->stop_bits == ET_UART_WRAP_STOP_BITS_2)
    {
        return config->data_bits >= (ET_UART_WRAP_MIN_DATA_BITS + 1u);
    }

    return 0;
}

/**
 * @brief Decode one INITIALIZE command and establish a clean UART Service/IRQ session.
 *
 * @param[in,out] service UART Service instance to reset, initialize and bind.
 * @param[in] request_body Fixed UART initialization Wire body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note Initialization first tears down any previous session, then initializes UART Wrap, resolves the route and binds IRQ Manager before publishing initialized FIFO/DMA defaults. Any intermediate failure returns the Service to idle best-effort.
 *
 * @return Stable ET status for payload validation, Wrap initialization, route resolution or binding.
 */

static uint16_t handle_initialize(et_uart_service_t *service, const uint8_t *request_body,
                                  uint16_t request_length)
{
    et_uart_wrap_config_t config;
    et_wrap_status_t status;

    /* Phase 1: Validate and decode the complete stable UART line configuration. */
    if ((request_length != ET_UART_SERVICE_INITIALIZE_REQUEST_SIZE) ||
        (request_body[ET_UART_SERVICE_INITIALIZE_RESERVED_OFFSET] != 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    (void)memset(&config, 0, sizeof(config));
    config.struct_size = (uint16_t)sizeof(config);
    config.api_version = ET_UART_WRAP_API_VERSION;
    config.uart_id = service->uart_id;
    config.baudrate = read_u32(&request_body[ET_UART_SERVICE_INITIALIZE_BAUD_OFFSET]);
    config.data_bits = request_body[ET_UART_SERVICE_INITIALIZE_DATA_BITS_OFFSET];
    config.stop_bits = request_body[ET_UART_SERVICE_INITIALIZE_STOP_BITS_OFFSET];
    config.parity = request_body[ET_UART_SERVICE_INITIALIZE_PARITY_OFFSET];

    if (uart_line_config_is_valid(&config) == 0)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Tear down any prior session before constructing the new Wrap handle. */
    status = uart_reset_to_idle(service);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Configure UART hardware, resolve its route and bind managed callback ownership. */
    status = et_uart_wrap_init(&service->handle, &config);

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)uart_reset_to_idle(service);

        return status_from_wrap(status);
    }

    service->initialized = 1u;
    status = et_uart_wrap_get_irq_route(service->uart_id, ET_UART_SERVICE_IRQ_WRAP_ALL,
                                        &service->irq_route);

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)uart_reset_to_idle(service);

        return status_from_wrap(status);
    }

    service->irq_route.route_events = ET_UART_SERVICE_IRQ_WRAP_ALL;

    if (et_irq_manager_bind(service->irq_manager, &service->irq_route, service->irq_priority,
                            uart_irq_callback, service) != 0)
    {
        (void)uart_reset_to_idle(service);

        return ET_STATUS_INTERNAL_ERROR;
    }

    /* Phase 4: Publish deterministic FIFO/DMA defaults only after the route is owned. */
    service->irq_bound = 1u;
    service->fifo_enabled = 1u;
    service->fifo_tx_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_8;
    service->fifo_rx_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_1;
    service->dma_mode = ET_UART_WRAP_DMA_DISABLED;

    return ET_STATUS_OK;
}

/**
 * @brief Return one coherent bounded snapshot of UART capture lifecycle and captured bytes.
 *
 * @param[in] service Initialized UART Service whose seqlock-protected capture is observed.
 * @param[in] request_length Expected zero-length command body.
 * @param[out] response_body Response storage receiving capture header and bytes.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note A bounded seqlock retry copies capture data only when the generation is stable/even. The function never blocks waiting for more RX data and returns BUSY if a coherent snapshot cannot be obtained within the retry bound.
 *
 * @return ET_STATUS_OK for a coherent snapshot, INVALID_PARAM/INTERNAL_ERROR for invalid state, or BUSY after bounded retries.
 */

static uint16_t handle_capture_get(et_uart_service_t *service, uint16_t request_length,
                                   uint8_t *response_body, uint16_t response_capacity,
                                   uint16_t *response_length)
{
    uint32_t before;
    uint32_t after;
    uint32_t retry;
    uint8_t active;
    uint16_t expected;
    uint16_t received;
    uint16_t required;

    /* Phase 1: Validate command state before entering the bounded seqlock read. */
    if ((request_length != 0u) || (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Copy one candidate capture snapshot only while generation is stable and even. */
    for (retry = 0u; retry < ET_UART_SERVICE_SNAPSHOT_RETRIES; ++retry)
    {
        before = service->capture_generation;

        if ((before & 1u) != 0u)
        {
            continue;
        }

        active = service->capture_active;
        expected = service->capture_expected;
        received = service->capture_received;

        if (received > ET_UART_SERVICE_CAPTURE_CAPACITY)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        required = (uint16_t)(ET_UART_SERVICE_CAPTURE_HEADER_SIZE + received);

        if (response_capacity < required)
        {
            return ET_STATUS_INVALID_PARAM;
        }

        if (received != 0u)
        {
            (void)memcpy(&response_body[ET_UART_SERVICE_CAPTURE_HEADER_SIZE], service->capture,
                         received);
        }

        after = service->capture_generation;

        /* Phase 3: Encode capture metadata only after the data copy is proven coherent. */
        if ((before == after) && ((after & 1u) == 0u))
        {
            (void)memset(response_body, 0, ET_UART_SERVICE_CAPTURE_HEADER_SIZE);
            response_body[ET_UART_SERVICE_CAPTURE_ACTIVE_OFFSET] = active;
            write_u32(&response_body[ET_UART_SERVICE_CAPTURE_EXPECTED_OFFSET], expected);
            write_u32(&response_body[ET_UART_SERVICE_CAPTURE_RECEIVED_OFFSET], received);
            *response_length = required;

            return ET_STATUS_OK;
        }
    }

    return ET_STATUS_BUSY;
}

/**
 * @brief Apply one explicit UART IRQ source/priority configuration transaction with rollback.
 *
 * @param[in,out] service Initialized UART Service owning IRQ source, priority and evidence state.
 * @param[in] request_body Fixed IRQ_CONFIG Wire body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note The complete prior session is saved before priority or source changes. Pending evidence is cleared for the new configuration, suppressed one-shot sources are reopened, and any hardware apply failure restores prior masks/evidence/priority best-effort under IRQ Manager critical protection.
 *
 * @return Stable ET status for validation, priority rebinding or hardware source reconciliation.
 */

static uint16_t handle_irq_config(et_uart_service_t *service, const uint8_t *request_body,
                                  uint16_t request_length)
{
    uint32_t wire_mask;
    uint32_t old_mask;
    uint32_t new_mask;
    uint8_t old_priority;
    uint32_t old_pending;
    uint32_t old_active;
    uint32_t old_suppressed;
    uint32_t configured_wrap_mask;
    et_wrap_status_t status;

    if ((request_length != ET_UART_SERVICE_IRQ_CONFIG_REQUEST_SIZE) ||
        (bytes_are_zero(&request_body[ET_UART_SERVICE_IRQ_RESERVED_OFFSET],
                        ET_UART_SERVICE_IRQ_RESERVED_SIZE) == 0u) ||
        (request_body[ET_UART_SERVICE_IRQ_ENABLED_REQUEST_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
        (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 1: Validate the requested stable source mask and preserve the complete old session. */
    wire_mask = read_u32(&request_body[ET_UART_SERVICE_IRQ_MASK_OFFSET]);

    if (((wire_mask & ~ET_UART_SERVICE_IRQ_WIRE_ALLOWED) != 0u) ||
        ((request_body[ET_UART_SERVICE_IRQ_ENABLED_REQUEST_OFFSET] != 0u) && (wire_mask == 0u)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Save all mutable session fields before changing the IRQ route. */
    old_mask = service->irq_enabled_mask;
    old_priority = service->irq_priority;
    old_pending = service->irq_pending_mask;
    old_active = service->irq_active_mask;
    old_suppressed = service->irq_suppressed_wrap_mask;
    configured_wrap_mask = irq_wire_to_wrap(wire_mask);
    new_mask = (request_body[ET_UART_SERVICE_IRQ_ENABLED_REQUEST_OFFSET] != 0u)
                   ? (old_mask | wire_mask)
                   : (old_mask & ~wire_mask);

    /* Phase 2: Move route priority before exposing the new peripheral source ownership. */
    status = uart_rebind_irq_priority(service,
                                      request_body[ET_UART_SERVICE_IRQ_PRIORITY_REQUEST_OFFSET]);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Publish the new source set and reconcile hardware while callbacks are excluded. */
    {
        uint32_t critical_key = et_irq_manager_enter_critical();

        uart_irq_evidence_begin(service);
        service->irq_pending_mask = 0u;
        service->irq_active_mask = 0u;
        uart_irq_evidence_end(service);
        service->irq_enabled_mask = new_mask;
        service->irq_suppressed_wrap_mask &= ~configured_wrap_mask;
        status = uart_apply_irq_mask(service);
        et_irq_manager_exit_critical(critical_key);
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_OK;
    }

    /* Phase 4: Restore prior source/evidence/priority state if hardware reconciliation fails. */
    {
        uint32_t critical_key = et_irq_manager_enter_critical();

        service->irq_enabled_mask = old_mask;
        service->irq_suppressed_wrap_mask = old_suppressed;
        uart_irq_evidence_begin(service);
        service->irq_pending_mask = old_pending;
        service->irq_active_mask = old_active;
        uart_irq_evidence_end(service);
        (void)uart_rebind_irq_priority(service, old_priority);
        (void)uart_apply_irq_mask(service);
        et_irq_manager_exit_critical(critical_key);
    }

    return status_from_wrap(status);
}

/**
 * @brief Return one coherent bounded snapshot of callback-owned UART IRQ evidence.
 *
 * @param[in] service Initialized UART Service whose evidence is observed.
 * @param[in] request_length Expected zero-length command body.
 * @param[out] response_body Response storage for source masks and counters.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note The seqlock retry prevents torn counter/mask reads without disabling the IRQ for the whole copy; no hardware status is acknowledged here.
 *
 * @return ET_STATUS_OK for a coherent snapshot, INVALID_PARAM for invalid envelope/state, or BUSY after bounded retries.
 */

static uint16_t handle_irq_state_get(et_uart_service_t *service, uint16_t request_length,
                                     uint8_t *response_body, uint16_t response_capacity,
                                     uint16_t *response_length)
{
    uint32_t before;
    uint32_t after;
    uint32_t retry;
    uint32_t enabled_mask;
    uint32_t pending_mask;
    uint32_t active_mask;
    uint32_t event_count;
    uint32_t overflow_count;
    uint32_t fault_count;

    /* Phase 1: Validate response capacity and initialized Service state. */
    if ((request_length != 0u) || (response_capacity < ET_UART_SERVICE_IRQ_STATE_RESPONSE_SIZE) ||
        (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Read all callback-owned masks/counters under the bounded evidence seqlock. */
    for (retry = 0u; retry < ET_UART_SERVICE_SNAPSHOT_RETRIES; ++retry)
    {
        before = service->irq_result_generation;

        if ((before & 1u) != 0u)
        {
            continue;
        }

        enabled_mask = service->irq_enabled_mask;
        pending_mask = service->irq_pending_mask;
        active_mask = service->irq_active_mask;
        event_count = service->irq_event_count;
        overflow_count = service->irq_overflow_count;
        fault_count = service->irq_fault_count;
        after = service->irq_result_generation;

        /* Phase 3: Encode only a generation-stable IRQ evidence snapshot. */
        if ((before == after) && ((after & 1u) == 0u))
        {
            write_u32(&response_body[ET_UART_SERVICE_IRQ_ENABLED_OFFSET], enabled_mask);
            write_u32(&response_body[ET_UART_SERVICE_IRQ_PENDING_OFFSET], pending_mask);
            write_u32(&response_body[ET_UART_SERVICE_IRQ_ACTIVE_OFFSET], active_mask);
            write_u32(&response_body[ET_UART_SERVICE_IRQ_EVENT_COUNT_OFFSET], event_count);
            write_u32(&response_body[ET_UART_SERVICE_IRQ_OVERFLOW_COUNT_OFFSET], overflow_count);
            write_u32(&response_body[ET_UART_SERVICE_IRQ_FAULT_COUNT_OFFSET], fault_count);
            *response_length = ET_UART_SERVICE_IRQ_STATE_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }
    }

    return ET_STATUS_BUSY;
}

/**
 * @brief Decode and apply one UART 9-bit address-mode configuration.
 *
 * @param[in,out] service Initialized UART Service whose Wrap handle is configured.
 * @param[in] request_body Fixed 9-bit configuration Wire body.
 * @param[in] request_length Number of valid request-body bytes.
 *
 * @note The stable Wire address is constrained to the selected hardware's 8-bit match/self-address field; receiver mode is chosen from the public Boolean and transmitter mode remains the Service-defined software mode.
 *
 * @return Stable ET status for payload validation or UART Wrap configuration.
 */

static uint16_t handle_nine_bit_config(et_uart_service_t *service, const uint8_t *request_body,
                                       uint16_t request_length)
{
    et_uart_wrap_nine_bit_config_t config;
    uint16_t address;

    if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
        (request_body[ET_UART_SERVICE_NINE_BIT_ENABLED_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
        (request_body[ET_UART_SERVICE_NINE_BIT_RECEIVER_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
        (request_body[ET_UART_SERVICE_NINE_BIT_RESERVED_OFFSET] != 0u) ||
        (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    address = read_u16(&request_body[ET_UART_SERVICE_NINE_BIT_ADDRESS_OFFSET]);

    if (address > UINT8_MAX)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    (void)memset(&config, 0, sizeof(config));
    config.struct_size = (uint16_t)sizeof(config);
    config.api_version = ET_UART_WRAP_API_VERSION;
    config.enabled = request_body[ET_UART_SERVICE_NINE_BIT_ENABLED_OFFSET];
    config.receiver_mode = (request_body[ET_UART_SERVICE_NINE_BIT_RECEIVER_OFFSET] != 0u)
                               ? ET_UART_WRAP_NINE_BIT_RECEIVER_HARDWARE
                               : ET_UART_WRAP_NINE_BIT_RECEIVER_SOFTWARE;
    config.transmitter_mode = ET_UART_WRAP_NINE_BIT_TRANSMITTER_SOFTWARE;
    config.receiver_match_address = (uint8_t)address;
    config.transmitter_self_address = (uint8_t)address;

    return status_from_wrap(et_uart_wrap_configure_nine_bit(&service->handle, &config));
}

/**
 * @brief Decode one bounded 9-bit write request and return the one-shot transferred count.
 *
 * @param[in,out] service UART Service providing scratch storage and the initialized Wrap handle.
 * @param[in] request_body Header plus packed 16-bit 9-bit values.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Response storage for transferred count.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note Every value is validated against the 9-bit maximum before hardware access. The PC-supplied poll budget is validated as nonzero but Firmware still performs exactly one bounded Wrap write and does not own retry sequencing.
 *
 * @return Stable ET status for Wire/value validation or the one-shot 9-bit write.
 */

static uint16_t handle_write_nine_bit(et_uart_service_t *service, const uint8_t *request_body,
                                      uint16_t request_length, uint8_t *response_body,
                                      uint16_t response_capacity, uint16_t *response_length)
{
    uint32_t count;
    uint32_t max_polls;
    uint32_t transferred;
    uint16_t index;
    et_wrap_status_t status;

    /* Phase 1: Validate the packed request envelope, item count and nonzero PC poll budget. */
    if ((request_length < ET_UART_SERVICE_NINE_BIT_HEADER_SIZE) ||
        (response_capacity < ET_UART_SERVICE_COUNT_RESPONSE_SIZE) || (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    count = read_u32(request_body);
    max_polls = read_u32(&request_body[ET_UART_SERVICE_POLL_BUDGET_OFFSET]);

    if ((count == 0u) || (count > ET_UART_SERVICE_NINE_BIT_CAPACITY) || (max_polls == 0u) ||
        (count > (((uint32_t)request_length - ET_UART_SERVICE_NINE_BIT_HEADER_SIZE) /
                  ET_UART_SERVICE_NINE_BIT_ITEM_SIZE)) ||
        ((uint32_t)request_length !=
         (ET_UART_SERVICE_NINE_BIT_HEADER_SIZE + (count * ET_UART_SERVICE_NINE_BIT_ITEM_SIZE))))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Decode every packed item and reject values outside the 9-bit hardware contract. */
    for (index = 0u; index < (uint16_t)count; ++index)
    {
        service->nine_bit[index] =
            read_u16(&request_body[ET_UART_SERVICE_NINE_BIT_DATA_OFFSET +
                                   ((uint16_t)index * ET_UART_SERVICE_NINE_BIT_ITEM_SIZE)]);

        if (service->nine_bit[index] > ET_UART_WRAP_NINE_BIT_VALUE_MAX)
        {
            return ET_STATUS_INVALID_PARAM;
        }
    }

    /* Phase 3: Perform one non-blocking Wrap write and return only its transferred-count fact. */
    status = write_nine_bit_once(service, service->nine_bit, count, &transferred);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    write_u32(response_body, transferred);
    *response_length = ET_UART_SERVICE_COUNT_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Decode one bounded 9-bit read request and return currently available values.
 *
 * @param[in,out] service UART Service providing scratch storage and the initialized Wrap handle.
 * @param[in] request_body Fixed count/poll-budget request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Response storage receiving packed 16-bit values.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response byte length.
 *
 * @note The function validates requested capacity and nonzero PC poll budget, performs one non-blocking Wrap read, verifies every returned value is 9-bit and leaves retry policy to the PC.
 *
 * @return Stable ET status for validation, one-shot read, or invalid hardware-returned value.
 */

static uint16_t handle_read_nine_bit(et_uart_service_t *service, const uint8_t *request_body,
                                     uint16_t request_length, uint8_t *response_body,
                                     uint16_t response_capacity, uint16_t *response_length)
{
    uint32_t count;
    uint32_t max_polls;
    uint32_t transferred;
    uint16_t index;
    et_wrap_status_t status;

    /* Phase 1: Validate requested item count, response capacity and nonzero PC poll budget. */
    if ((request_length != ET_UART_SERVICE_COUNT_REQUEST_SIZE) || (service->initialized == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    count = read_u32(request_body);
    max_polls = read_u32(&request_body[ET_UART_SERVICE_POLL_BUDGET_OFFSET]);

    if ((count == 0u) || (count > ET_UART_SERVICE_NINE_BIT_CAPACITY) ||
        (count > ((uint32_t)response_capacity / ET_UART_SERVICE_NINE_BIT_ITEM_SIZE)) ||
        (max_polls == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Perform one non-blocking Wrap read into bounded Service scratch storage. */
    status = read_nine_bit_once(service, service->nine_bit, count, &transferred);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Validate and encode only the 9-bit values actually returned by hardware. */
    for (index = 0u; index < (uint16_t)transferred; ++index)
    {
        if (service->nine_bit[index] > ET_UART_WRAP_NINE_BIT_VALUE_MAX)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        write_u16(&response_body[(uint16_t)index * ET_UART_SERVICE_NINE_BIT_ITEM_SIZE],
                  service->nine_bit[index]);
    }

    *response_length = (uint16_t)(transferred * ET_UART_SERVICE_NINE_BIT_ITEM_SIZE);

    return ET_STATUS_OK;
}

/********************************** Command Dispatch **********************************/

/**
 * @brief Dispatch UART discovery, lifecycle, DMA-endpoint and direct byte-transfer commands.
 *
 * @param[in,out] service UART Service whose lifecycle/FIFO-DMA state or Wrap handle may change.
 * @param[in] command_id Stable UART command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note Each branch performs one atomic UART operation/fact query. WRITE/READ commands validate PC poll budgets but do not loop in Firmware; INVALID_COMMAND is returned only so the next UART category can inspect the same command ID.
 *
 * @return Stable ET status for a handled transport command, or ET_STATUS_INVALID_COMMAND for another category.
 */

static uint16_t handle_transport_commands(et_uart_service_t *service, uint16_t command_id,
                                          const uint8_t *request_body, uint16_t request_length,
                                          uint8_t *response_body, uint16_t response_capacity,
                                          uint16_t *response_length)
{
    et_uart_wrap_capabilities_t capabilities;
    et_uart_wrap_io_result_t io_result;
    et_wrap_status_t status;
    uintptr_t address;
    uint32_t requested;
    uint32_t max_polls;
    uint16_t data_length;

    /* Phase 1: Serve discovery and trusted DMA endpoint facts without requiring initialization. */
    if (command_id == ET_UART_COMMAND_CAPABILITIES_GET)
    {
        if ((request_length != 0u) ||
            (response_capacity < ET_UART_SERVICE_CAPABILITIES_RESPONSE_SIZE))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_get_capabilities(service->uart_id, &capabilities);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u32(&response_body[ET_UART_SERVICE_CAP_FEATURES_OFFSET], capabilities.feature_flags);
        write_u32(&response_body[ET_UART_SERVICE_CAP_MIN_BAUD_OFFSET], capabilities.min_baudrate);
        write_u32(&response_body[ET_UART_SERVICE_CAP_MAX_BAUD_OFFSET], capabilities.max_baudrate);
        write_u32(&response_body[ET_UART_SERVICE_CAP_MAX_READ_OFFSET], capabilities.max_read_size);
        write_u32(&response_body[ET_UART_SERVICE_CAP_MAX_WRITE_OFFSET],
                  capabilities.max_write_size);
        *response_length = ET_UART_SERVICE_CAPABILITIES_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_DMA_ENDPOINT_GET)
    {
        if ((request_length != ET_UART_SERVICE_DMA_ENDPOINT_REQUEST_SIZE) ||
            (response_capacity < ET_UART_SERVICE_DMA_ENDPOINT_RESPONSE_SIZE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_get_dma_endpoint_address(
            service->uart_id, request_body[ET_UART_SERVICE_VALUE_OFFSET], &address);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u64(response_body, (uint64_t)address);
        *response_length = ET_UART_SERVICE_DMA_ENDPOINT_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_DMA_ENABLE_SET)
    {
        uint8_t enabled;
        uint8_t dma_mode;

        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        enabled = (request_body[ET_UART_SERVICE_VALUE_OFFSET] != 0u) ? 1u : service->fifo_enabled;
        dma_mode = (request_body[ET_UART_SERVICE_VALUE_OFFSET] != 0u) ? ET_UART_WRAP_DMA_MULTI
                                                                      : ET_UART_WRAP_DMA_DISABLED;

        return status_from_wrap(uart_apply_fifo_dma_state(
            service, enabled, service->fifo_tx_threshold, service->fifo_rx_threshold, dma_mode));
    }

    /* Phase 2: Route lifecycle construction/teardown through the single Service ownership paths. */
    if (command_id == ET_UART_COMMAND_INITIALIZE)
    {
        return handle_initialize(service, request_body, request_length);
    }

    if (command_id == ET_UART_COMMAND_DEINITIALIZE)
    {
        if (request_length != 0u)
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(uart_reset_to_idle(service));
    }

    /* Phase 3: Execute byte transfers as one bounded non-blocking Wrap operation per command. */
    if (command_id == ET_UART_COMMAND_WRITE)
    {
        if ((request_length <= ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD) ||
            (response_capacity < ET_UART_SERVICE_COUNT_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        max_polls = read_u32(request_body);
        data_length = (uint16_t)(request_length - ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD);

        if ((max_polls == 0u) || (data_length > ET_UART_SERVICE_MAX_WRITE_CHUNK))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_write_partial(
            &service->handle, &request_body[ET_UART_SERVICE_DATA_OFFSET], data_length, &io_result);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        if (io_result.transferred > data_length)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        write_u32(response_body, io_result.transferred);
        *response_length = ET_UART_SERVICE_COUNT_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_WRITE_PARTIAL)
    {
        if ((request_length == 0u) || (request_length > ET_UART_SERVICE_BODY_CAPACITY) ||
            (response_capacity < ET_UART_SERVICE_COUNT_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status =
            et_uart_wrap_write_partial(&service->handle, request_body, request_length, &io_result);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        if (io_result.transferred > request_length)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        write_u32(response_body, io_result.transferred);
        *response_length = ET_UART_SERVICE_COUNT_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_READ_EXACT)
    {
        if ((request_length != ET_UART_SERVICE_COUNT_REQUEST_SIZE) || (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        requested = read_u32(request_body);
        max_polls = read_u32(&request_body[ET_UART_SERVICE_POLL_BUDGET_OFFSET]);

        if ((requested == 0u) || (requested > ET_UART_SERVICE_MAX_READ_CHUNK) ||
            (requested > response_capacity) || (requested > UINT16_MAX) || (max_polls == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_read(&service->handle, response_body, requested, &io_result);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        if (io_result.transferred > requested)
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        *response_length = (uint16_t)io_result.transferred;

        return ET_STATUS_OK;
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Dispatch UART capture, snapshot, status, FIFO and managed IRQ observation commands.
 *
 * @param[in,out] service UART Service whose capture/IRQ/FIFO state may change.
 * @param[in] command_id Stable UART command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note Capture start flushes stale RX before publishing ownership; software reset deliberately routes through the single full Service teardown path. STATUS_GET prefers error facts latched before interrupt clear, preserving evidence for PC assertions.
 *
 * @return Stable ET status for a handled observation command, or ET_STATUS_INVALID_COMMAND for another category.
 */

static uint16_t handle_observation_commands(et_uart_service_t *service, uint16_t command_id,
                                            const uint8_t *request_body, uint16_t request_length,
                                            uint8_t *response_body, uint16_t response_capacity,
                                            uint16_t *response_length)
{
    et_uart_wrap_snapshot_t snapshot;
    et_uart_wrap_status_t uart_status;
    et_wrap_status_t status;
    uint32_t requested;

    /* Phase 1: Manage bounded capture lifecycle and capture-owned interrupt sources. */
    if (command_id == ET_UART_COMMAND_CAPTURE_START)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) || (service->initialized == 0u) ||
            (service->capture_active != 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        requested = read_u32(request_body);

        if ((requested == 0u) || (requested > ET_UART_SERVICE_CAPTURE_CAPACITY))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = flush_rx_bounded(service);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        uart_store_capture_state(service, 1u, (uint16_t)requested, 0u);
        status = uart_apply_irq_mask(service);

        if (status != ET_WRAP_STATUS_OK)
        {
            uart_store_capture_state(service, 0u, 0u, 0u);
            (void)uart_apply_irq_mask(service);

            return status_from_wrap(status);
        }

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_CAPTURE_GET)
    {
        return handle_capture_get(service, request_length, response_body, response_capacity,
                                  response_length);
    }

    if (command_id == ET_UART_COMMAND_CAPTURE_CANCEL)
    {
        if (request_length != 0u)
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(uart_cancel_capture(service));
    }

    if (command_id == ET_UART_COMMAND_EXCHANGE)
    {
        if ((request_length <= ET_UART_SERVICE_WRITE_REQUEST_OVERHEAD) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return ET_STATUS_NOT_SUPPORTED;
    }

    /* Phase 2: Return target-local component/status observations and atomic reset/loopback/FIFO actions. */
    if (command_id == ET_UART_COMMAND_SNAPSHOT_GET)
    {
        if ((request_length != 0u) ||
            (response_capacity < ET_UART_SERVICE_SNAPSHOT_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_get_snapshot(&service->handle, &snapshot);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_COMPONENT_PARAMETER_OFFSET],
                  snapshot.component_parameter);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_COMPONENT_VERSION_OFFSET],
                  snapshot.component_version);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_COMPONENT_TYPE_OFFSET],
                  snapshot.component_type);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_SCRATCH_OFFSET], snapshot.scratch);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_UART_STATUS_OFFSET],
                  snapshot.uart_status);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_LINE_STATUS_OFFSET],
                  snapshot.line_status);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_TX_LEVEL_OFFSET], snapshot.tx_fifo_level);
        write_u32(&response_body[ET_UART_SERVICE_SNAPSHOT_RX_LEVEL_OFFSET], snapshot.rx_fifo_level);
        *response_length = ET_UART_SERVICE_SNAPSHOT_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_SOFTWARE_RESET)
    {
        if ((request_length != 0u) || (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        /* reset_to_idle owns the single peripheral reset and teardown path. */
        return status_from_wrap(uart_reset_to_idle(service));
    }

    if (command_id == ET_UART_COMMAND_LOOPBACK_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(et_uart_wrap_set_loopback(
            &service->handle, request_body[ET_UART_SERVICE_VALUE_OFFSET]));
    }

    if (command_id == ET_UART_COMMAND_FIFO_CONFIG)
    {
        uint8_t tx_threshold;
        uint8_t rx_threshold;

        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_FIFO_ENABLED_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FIFO_DMA_MODE_OFFSET] > ET_UART_WRAP_DMA_MULTI) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status =
            map_tx_threshold(request_body[ET_UART_SERVICE_FIFO_TX_THRESHOLD_OFFSET], &tx_threshold);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        status =
            map_rx_threshold(request_body[ET_UART_SERVICE_FIFO_RX_THRESHOLD_OFFSET], &rx_threshold);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        return status_from_wrap(uart_apply_fifo_dma_state(
            service, request_body[ET_UART_SERVICE_FIFO_ENABLED_OFFSET], tx_threshold, rx_threshold,
            request_body[ET_UART_SERVICE_FIFO_DMA_MODE_OFFSET]));
    }

    /* Phase 3: Return normalized status and managed IRQ evidence without creating a verdict. */
    if (command_id == ET_UART_COMMAND_STATUS_GET)
    {
        if ((request_length != 0u) || (response_capacity < ET_UART_SERVICE_STATUS_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_get_status(&service->handle, &uart_status);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u32(&response_body[ET_UART_SERVICE_STATUS_LINE_OFFSET], uart_status.line_status);
        write_u32(&response_body[ET_UART_SERVICE_STATUS_FIFO_OFFSET], uart_status.fifo_flags);
        write_u32(&response_body[ET_UART_SERVICE_STATUS_TX_LEVEL_OFFSET],
                  uart_status.tx_fifo_level);
        write_u32(&response_body[ET_UART_SERVICE_STATUS_RX_LEVEL_OFFSET],
                  uart_status.rx_fifo_level);

        /* Prefer the pre-clear error evidence captured by IRQ/capture
         * callbacks; otherwise report the current Wrap-owned field. */
        if (service->latched_error_flags != 0u)
        {
            uart_status.error_flags = service->latched_error_flags;
        }

        write_u32(&response_body[ET_UART_SERVICE_STATUS_ERROR_OFFSET], uart_status.error_flags);
        write_u32(&response_body[ET_UART_SERVICE_STATUS_STATE_OFFSET], uart_status.state_flags);
        *response_length = ET_UART_SERVICE_STATUS_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_IRQ_CONFIG)
    {
        return handle_irq_config(service, request_body, request_length);
    }

    if (command_id == ET_UART_COMMAND_IRQ_STATE_GET)
    {
        return handle_irq_state_get(service, request_length, response_body, response_capacity,
                                    response_length);
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Dispatch optional UART break, halt, DMA, 9-bit, flow-control and modem feature commands.
 *
 * @param[in,out] service Initialized UART Service whose selected feature state or hardware may change.
 * @param[in] command_id Stable UART feature command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note Only public combinations implemented by the Wrap are accepted; unsupported flow-control options are rejected rather than guessed. Every branch remains a single-IP operation with no external pin or peer orchestration.
 *
 * @return Stable ET status for a handled feature command, or ET_STATUS_INVALID_COMMAND for another category.
 */

static uint16_t handle_feature_commands(et_uart_service_t *service, uint16_t command_id,
                                        const uint8_t *request_body, uint16_t request_length,
                                        uint8_t *response_body, uint16_t response_capacity,
                                        uint16_t *response_length)
{
    et_uart_wrap_io_result_t io_result;
    et_uart_wrap_modem_control_t modem_control;
    et_uart_wrap_modem_status_t modem_status;
    et_wrap_status_t status;

    /* Phase 1: Handle scalar break/halt/DMA-mode feature toggles with strict Boolean/enumeration validation. */
    if (command_id == ET_UART_COMMAND_BREAK_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(
            et_uart_wrap_set_break(&service->handle, request_body[ET_UART_SERVICE_VALUE_OFFSET]));
    }

    if (command_id == ET_UART_COMMAND_HALT_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        return status_from_wrap(
            et_uart_wrap_set_halt(&service->handle, request_body[ET_UART_SERVICE_VALUE_OFFSET]));
    }

    if (command_id == ET_UART_COMMAND_DMA_MODE_SET)
    {
        uint8_t fifo_enabled;

        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_WRAP_DMA_MULTI) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        fifo_enabled = (request_body[ET_UART_SERVICE_VALUE_OFFSET] == ET_UART_WRAP_DMA_DISABLED)
                           ? service->fifo_enabled
                           : 1u;

        return status_from_wrap(uart_apply_fifo_dma_state(
            service, fifo_enabled, service->fifo_tx_threshold, service->fifo_rx_threshold,
            request_body[ET_UART_SERVICE_VALUE_OFFSET]));
    }

    /* Phase 2: Route 9-bit configuration and one-shot transfers through their bounded helpers. */
    if (command_id == ET_UART_COMMAND_NINE_BIT_CONFIG)
    {
        return handle_nine_bit_config(service, request_body, request_length);
    }

    if (command_id == ET_UART_COMMAND_WRITE_9BIT)
    {
        return handle_write_nine_bit(service, request_body, request_length, response_body,
                                     response_capacity, response_length);
    }

    if (command_id == ET_UART_COMMAND_READ_9BIT)
    {
        return handle_read_nine_bit(service, request_body, request_length, response_body,
                                    response_capacity, response_length);
    }

    /* Phase 3: Apply only supported flow/modem controls and return raw modem observations. */
    if (command_id == ET_UART_COMMAND_FLOW_CONTROL_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_FLOW_ENABLED_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FLOW_OPTION1_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FLOW_OPTION2_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FLOW_RESERVED_OFFSET] != 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        if ((request_body[ET_UART_SERVICE_FLOW_OPTION1_OFFSET] != 0u) ||
            (request_body[ET_UART_SERVICE_FLOW_OPTION2_OFFSET] != 0u))
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        return status_from_wrap(et_uart_wrap_set_flow_control(
            &service->handle, request_body[ET_UART_SERVICE_FLOW_ENABLED_OFFSET]));
    }

    if (command_id == ET_UART_COMMAND_MODEM_CONTROL_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_MODEM_RTS_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_MODEM_DTR_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_MODEM_RESERVED_OFFSET],
                            ET_UART_SERVICE_MODEM_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        (void)memset(&modem_control, 0, sizeof(modem_control));
        modem_control.struct_size = (uint16_t)sizeof(modem_control);
        modem_control.api_version = ET_UART_WRAP_API_VERSION;
        modem_control.rts_asserted = request_body[ET_UART_SERVICE_MODEM_RTS_OFFSET];
        modem_control.dtr_asserted = request_body[ET_UART_SERVICE_MODEM_DTR_OFFSET];

        return status_from_wrap(et_uart_wrap_set_modem_control(&service->handle, &modem_control));
    }

    if (command_id == ET_UART_COMMAND_MODEM_STATUS_GET)
    {
        if ((request_length != 0u) ||
            (response_capacity < ET_UART_SERVICE_MODEM_STATUS_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_get_modem_status(&service->handle, &modem_status);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u32(&response_body[ET_UART_SERVICE_MODEM_INPUT_OFFSET], modem_status.input_flags);
        write_u32(&response_body[ET_UART_SERVICE_MODEM_DELTA_OFFSET], modem_status.delta_flags);
        write_u32(&response_body[ET_UART_SERVICE_MODEM_OUTPUT_OFFSET], modem_status.output_flags);
        write_u32(&response_body[ET_UART_SERVICE_MODEM_RAW_OFFSET], modem_status.raw_status);
        *response_length = ET_UART_SERVICE_MODEM_STATUS_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Dispatch isolated UART Test Driver Extension commands for busy and FIFO validation.
 *
 * @param[in,out] service Initialized UART Service whose Wrap Test Driver path is exercised.
 * @param[in] command_id Stable UART validation command identifier.
 * @param[in] request_body Optional validation command body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Response storage for raw validation facts.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note These branches expose selected target-local validation hooks only. Firmware returns applied state/observations and never turns busy/FIFO evidence into a test verdict.
 *
 * @return Stable ET status for a handled validation command, or ET_STATUS_INVALID_COMMAND otherwise.
 */

static uint16_t handle_validation_commands(et_uart_service_t *service, uint16_t command_id,
                                           const uint8_t *request_body, uint16_t request_length,
                                           uint8_t *response_body, uint16_t response_capacity,
                                           uint16_t *response_length)
{
    et_uart_wrap_busy_detect_result_t busy_detect;
    et_uart_wrap_shadow_fifo_state_t shadow_fifo_state;
    et_wrap_status_t status;
    uint8_t fifo_active;
    uint8_t fifo_value;

    /* Phase 1: Execute target-local busy-detect validation and return all observed recovery facts. */
    if (command_id == ET_UART_COMMAND_BUSY_DETECT_TRIGGER)
    {
        if ((request_length != 0u) ||
            (response_capacity < ET_UART_SERVICE_BUSY_DETECT_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_trigger_busy_detect(&service->handle, &busy_detect);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        write_u32(&response_body[ET_UART_SERVICE_BUSY_PRE_TRIGGER_OFFSET],
                  busy_detect.pre_trigger_usr);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_IIR_OFFSET], busy_detect.observed_iir);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_USR_OFFSET], busy_detect.observed_usr);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_TRIGGER_COUNT_OFFSET],
                  busy_detect.trigger_count);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_OBSERVED_OFFSET], busy_detect.busy_observed);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_IRQ_OBSERVED_OFFSET],
                  busy_detect.interrupt_observed);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_CLEARED_OFFSET], busy_detect.cleared);
        write_u32(&response_body[ET_UART_SERVICE_BUSY_RECOVERED_OFFSET], busy_detect.recovered);
        *response_length = ET_UART_SERVICE_BUSY_DETECT_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    /* Phase 2: Exercise shadow FIFO and direct FIFO-access validation paths without host verdicts. */
    if (command_id == ET_UART_COMMAND_SHADOW_FIFO_CONFIG)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (response_capacity < ET_UART_SERVICE_SHADOW_FIFO_RESPONSE_SIZE) ||
            (request_body[ET_UART_SERVICE_SHADOW_RESERVED_OFFSET] != 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_shadow_fifo_config(
            &service->handle, request_body[ET_UART_SERVICE_FIFO_ENABLED_OFFSET],
            request_body[ET_UART_SERVICE_FIFO_TX_THRESHOLD_OFFSET],
            request_body[ET_UART_SERVICE_FIFO_RX_THRESHOLD_OFFSET], &shadow_fifo_state);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        (void)memset(response_body, 0, ET_UART_SERVICE_SHADOW_FIFO_RESPONSE_SIZE);
        response_body[ET_UART_SERVICE_SHADOW_ENABLED_OFFSET] = shadow_fifo_state.enabled;
        response_body[ET_UART_SERVICE_SHADOW_TX_THRESHOLD_OFFSET] = shadow_fifo_state.tx_threshold;
        response_body[ET_UART_SERVICE_SHADOW_RX_THRESHOLD_OFFSET] = shadow_fifo_state.rx_threshold;
        *response_length = ET_UART_SERVICE_SHADOW_FIFO_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_FIFO_ACCESS_SET)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (response_capacity < ET_UART_SERVICE_FIFO_ACCESS_RESPONSE_SIZE) ||
            (request_body[ET_UART_SERVICE_VALUE_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (bytes_are_zero(&request_body[ET_UART_SERVICE_VALUE_RESERVED_OFFSET],
                            ET_UART_SERVICE_VALUE_RESERVED_SIZE) == 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_fifo_access_set(
            &service->handle, request_body[ET_UART_SERVICE_VALUE_OFFSET], &fifo_active);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        (void)memset(response_body, 0, ET_UART_SERVICE_FIFO_ACCESS_RESPONSE_SIZE);
        response_body[ET_UART_SERVICE_SMALL_VALUE_OFFSET] = fifo_active;
        *response_length = ET_UART_SERVICE_FIFO_ACCESS_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    if (command_id == ET_UART_COMMAND_FIFO_TX_READ)
    {
        if ((request_length != 0u) ||
            (response_capacity < ET_UART_SERVICE_FIFO_TX_READ_RESPONSE_SIZE) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_fifo_tx_read(&service->handle, &fifo_value);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        (void)memset(response_body, 0, ET_UART_SERVICE_FIFO_TX_READ_RESPONSE_SIZE);
        response_body[ET_UART_SERVICE_SMALL_VALUE_OFFSET] = fifo_value;
        *response_length = ET_UART_SERVICE_FIFO_TX_READ_RESPONSE_SIZE;

        return ET_STATUS_OK;
    }

    /* Phase 3: Inject only explicitly requested RX FIFO validation data/error metadata. */
    if (command_id == ET_UART_COMMAND_FIFO_RX_WRITE)
    {
        if ((request_length != ET_UART_SERVICE_U32_BODY_SIZE) ||
            (request_body[ET_UART_SERVICE_FIFO_RX_PARITY_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FIFO_RX_FRAMING_OFFSET] > ET_UART_SERVICE_BOOLEAN_TRUE) ||
            (request_body[ET_UART_SERVICE_FIFO_RX_RESERVED_OFFSET] != 0u) ||
            (service->initialized == 0u))
        {
            return ET_STATUS_INVALID_PARAM;
        }

        status = et_uart_wrap_fifo_rx_write(&service->handle,
                                            request_body[ET_UART_SERVICE_FIFO_RX_VALUE_OFFSET],
                                            request_body[ET_UART_SERVICE_FIFO_RX_PARITY_OFFSET],
                                            request_body[ET_UART_SERVICE_FIFO_RX_FRAMING_OFFSET]);

        return status_from_wrap(status);
    }

    return ET_STATUS_INVALID_COMMAND;
}

/**
 * @brief Validate the common UART Service envelope and route one command category in fixed order.
 *
 * @param[in,out] context UART Service retained by the common Service Router.
 * @param[in] command_id Stable UART command identifier.
 * @param[in] request_body Optional command body received from ET-Frame.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Encoded response length.
 *
 * @note Category handlers use INVALID_COMMAND only as internal fall-through. The first category that owns the command returns its exact status; no command is executed by more than one category.
 *
 * @return Stable ET status from the matching UART command category.
 */

static uint16_t uart_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                            uint16_t request_length, uint8_t *response_body,
                            uint16_t response_capacity, uint16_t *response_length)
{
    et_uart_service_t *service = (et_uart_service_t *)context;
    uint16_t status;

    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 1: Try normal discovery/lifecycle/transport ownership first. */
    status = handle_transport_commands(service, command_id, request_body, request_length,
                                       response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    /* Phase 2: Fall through only INVALID_COMMAND to observation and optional feature ownership. */
    status = handle_observation_commands(service, command_id, request_body, request_length,
                                         response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    status = handle_feature_commands(service, command_id, request_body, request_length,
                                     response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    /* Phase 3: Leave isolated validation-extension commands as the final UART category. */
    return handle_validation_commands(service, command_id, request_body, request_length,
                                      response_body, response_capacity, response_length);
}

/********************************** Public Service Interface **********************************/

/**
 * @brief Initialize one UART Service descriptor and deterministic software-owned defaults without configuring hardware.
 *
 * @param[out] service Application-owned storage for one UART Service instance.
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[in] irq_manager Common IRQ Manager dependency retained by the Service.
 * @param[in] capture_irq_priority Board-selected default UART IRQ priority.
 *
 * @note Initialization first confirms that the logical UART is supported, then clears only Service storage and builds the router descriptor. UART peripheral/IRQ hardware remains untouched until a later INITIALIZE command.
 *
 * @return 0 when the Service descriptor is initialized, otherwise -1 for invalid dependencies or unsupported UART ID.
 */

int et_uart_service_init(et_uart_service_t *service, uint16_t uart_id,
                         et_irq_manager_t *irq_manager, uint8_t capture_irq_priority)
{
    et_uart_wrap_capabilities_t capabilities;

    if ((service == NULL) || (irq_manager == NULL) ||
        (et_uart_wrap_get_capabilities(uart_id, &capabilities) != ET_WRAP_STATUS_OK))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->uart_id = uart_id;
    service->irq_manager = irq_manager;
    service->irq_priority = capture_irq_priority;
    service->default_irq_priority = capture_irq_priority;
    service->fifo_enabled = 1u;
    service->fifo_tx_threshold = ET_UART_WRAP_TXFIFO_THRESHOLD_8;
    service->fifo_rx_threshold = ET_UART_WRAP_RXFIFO_THRESHOLD_1;
    service->dma_mode = ET_UART_WRAP_DMA_DISABLED;
    service->descriptor.service_id = ET_UART_SERVICE_ID;
    service->descriptor.instance_id = uart_id;
    service->descriptor.context = service;
    service->descriptor.handle = uart_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the router descriptor owned by one initialized UART Service.
 *
 * @param[in] service UART Service whose descriptor is requested.
 *
 * @note The returned pointer aliases Service-owned storage and does not access UART hardware or IRQ Manager.
 *
 * @return Pointer to the Service descriptor, or NULL when service is NULL.
 */

const et_service_descriptor_t *et_uart_service_descriptor(const et_uart_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Adapt the generic Service-factory contract to the UART Service initializer.
 *
 * @param[out] storage Factory-provided storage for one UART Service instance.
 * @param[in] instance_id Stable logical UART instance identifier from the manifest.
 * @param[in] context Common factory dependencies including IRQ Manager and default priority.
 * @param[out] descriptor Created UART descriptor returned to the common registrar.
 *
 * @note This factory performs no UART feature action; it only validates common dependencies, calls et_uart_service_init() and exposes the resulting descriptor.
 *
 * @return 0 when one descriptor is created successfully, otherwise -1.
 */

int et_uart_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_uart_service_t *service = (et_uart_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_uart_service_init(service, instance_id, context->irq_manager, context->irq_priority) !=
        0)
    {
        return -1;
    }

    *descriptor = et_uart_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
