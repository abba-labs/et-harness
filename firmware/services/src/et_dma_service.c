/**
 * @file et_dma_service.c
 * @brief Decode DMA protocol bodies, execute DMA Wrap operations and return facts.
 *
 * Cross-IP address, endpoint, route and resource ownership is resolved by the
 * trusted PC control plane.  This Service remains static, bounded and limited
 * to DMA-local lifecycle and managed IRQ state.
 */
#include "et_dma_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Decode one unaligned little-endian 32-bit DMA Wire field.
 *
 * @param[in] data Four request bytes containing the encoded value.
 *
 * @note This helper reads caller-owned Wire memory only and does not access DMA hardware.
 *
 * @return Decoded 32-bit value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Decode one unaligned little-endian 64-bit DMA Wire field.
 *
 * @param[in] data Eight request bytes containing the encoded value.
 *
 * @note The helper composes two canonical 32-bit Wire reads and assigns no address semantics itself.
 *
 * @return Decoded 64-bit value.
 */
static uint64_t read_u64(const uint8_t *data)
{
    return (uint64_t)read_u32(data) | ((uint64_t)read_u32(&data[4]) << 32u);
}

/**
 * @brief Verify that one reserved DMA Wire region contains only zero bytes.
 *
 * @param[in] data Reserved request bytes to inspect.
 * @param[in] length Number of reserved bytes to validate.
 *
 * @note Rejecting nonzero reserved bytes prevents older Firmware from silently accepting a future Wire extension.
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
 * @brief Encode one 16-bit value into an unaligned little-endian DMA Wire field.
 *
 * @param[out] data Two-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note This helper writes caller-owned response memory only and has no DMA hardware side effect.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode one 32-bit value into an unaligned little-endian DMA Wire field.
 *
 * @param[out] data Four-byte response field to populate.
 * @param[in] value Value to encode.
 *
 * @note This helper writes caller-owned response memory only and does not change Service state.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)value;
    data[1] = (uint8_t)(value >> 8u);
    data[2] = (uint8_t)(value >> 16u);
    data[3] = (uint8_t)(value >> 24u);
}

/**
 * @brief Normalize one DMA Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status Chip-neutral DMA Wrap status to translate.
 *
 * @note Driver-specific status values never cross the Service boundary through this helper.
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

/**
 * @brief Increment one DMA evidence counter without allowing unsigned wraparound.
 *
 * @param[in,out] value Counter to increment while it remains below UINT32_MAX.
 *
 * @note Saturation preserves monotonic IRQ diagnostics; callers provide the required ISR or critical-section context.
 */
static void increment_saturating(volatile uint32_t *value)
{
    if ((value != NULL) && (*value != UINT32_MAX))
    {
        ++(*value);
    }
}

/**
 * @brief Build the valid DMA channel bit mask from the runtime controller capability.
 *
 * @param[in] service DMA Service instance that owns the discovered channel count.
 *
 * @note The full-width case avoids an undefined 32-bit shift while exposing only channels reported by DMA Wrap.
 *
 * @return Bit mask of channels valid for this Service instance, or zero for an invalid/empty instance.
 */
static uint32_t channel_limit_mask(const et_dma_service_t *service)
{
    if ((service == NULL) || (service->channel_count == 0u))
    {
        return 0u;
    }

    if (service->channel_count >= ET_DMA_SERVICE_MAX_CHANNELS)
    {
        return UINT32_MAX;
    }

    return (1u << service->channel_count) - 1u;
}

/**
 * @brief Check whether one channel identifier belongs to the current DMA Service instance.
 *
 * @param[in] service DMA Service instance providing the runtime channel count.
 * @param[in] channel Candidate logical channel identifier.
 *
 * @note This is a read-only Service-state check and does not inspect DMA hardware.
 *
 * @return Nonzero when the channel is in range, otherwise zero.
 */
static uint8_t channel_is_valid(const et_dma_service_t *service, uint8_t channel)
{
    return (uint8_t)((service != NULL) && (channel < service->channel_count));
}

/**
 * @brief Decode one CHANNEL_CONFIGURE body into a chip-neutral DMA Wrap configuration.
 *
 * @param[in] service DMA Service instance providing controller and channel capability context.
 * @param[in] body Fixed CHANNEL_CONFIGURE Wire body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] config DMA Wrap configuration populated from validated Wire fields.
 *
 * @note Wire addresses are decoded as 64-bit values and rejected if target uintptr_t cannot represent them. The helper does not program DMA hardware.
 *
 * @return 0 when the request is decoded successfully, otherwise -1.
 */
static int decode_config(et_dma_service_t *service, const uint8_t *body, uint16_t length,
                         et_dma_wrap_config_t *config)
{
    uint64_t source;
    uint64_t destination;
    uint64_t linked_list;
    uintptr_t source_address;
    uintptr_t destination_address;
    uintptr_t linked_list_address;

    /* Phase 1: Validate the fixed Wire envelope and channel/handshake selectors. */
    if ((service == NULL) || (body == NULL) || (config == NULL) ||
        (length != ET_DMA_SERVICE_CONFIG_REQUEST_SIZE) ||
        ((body[ET_DMA_SERVICE_CONFIG_SOURCE_HANDSHAKE_OFFSET] &
          ~ET_DMA_SERVICE_HANDSHAKE_CONFIG_MASK) != 0u) ||
        ((body[ET_DMA_SERVICE_CONFIG_DESTINATION_HANDSHAKE_OFFSET] &
          ~ET_DMA_SERVICE_HANDSHAKE_CONFIG_MASK) != 0u) ||
        (channel_is_valid(service, body[ET_DMA_SERVICE_CONFIG_CHANNEL_OFFSET]) == 0u))
    {
        return -1;
    }

    /* Phase 2: Decode 64-bit Wire addresses and reject target-pointer truncation. */
    source = read_u64(&body[ET_DMA_SERVICE_CONFIG_SOURCE_ADDRESS_OFFSET]);
    destination = read_u64(&body[ET_DMA_SERVICE_CONFIG_DESTINATION_ADDRESS_OFFSET]);
    linked_list = read_u64(&body[ET_DMA_SERVICE_CONFIG_LINKED_LIST_OFFSET]);
    source_address = (uintptr_t)source;
    destination_address = (uintptr_t)destination;
    linked_list_address = (uintptr_t)linked_list;

    if (((uint64_t)source_address != source) || ((uint64_t)destination_address != destination) ||
        ((uint64_t)linked_list_address != linked_list))
    {
        return -1;
    }

    /* Phase 3: Start from the Wrap-owned deterministic baseline configuration. */
    if (et_dma_wrap_get_default_config(config) != ET_WRAP_STATUS_OK)
    {
        return -1;
    }

    /* Phase 4: Overlay validated Wire fields onto the chip-neutral Wrap configuration. */
    config->controller_id = service->controller_id;
    config->channel_id = body[ET_DMA_SERVICE_CONFIG_CHANNEL_OFFSET];
    config->transfer_type = body[ET_DMA_SERVICE_CONFIG_TRANSFER_TYPE_OFFSET];
    config->priority = body[ET_DMA_SERVICE_CONFIG_PRIORITY_OFFSET];
    config->source_width = body[ET_DMA_SERVICE_CONFIG_SOURCE_WIDTH_OFFSET];
    config->destination_width = body[ET_DMA_SERVICE_CONFIG_DESTINATION_WIDTH_OFFSET];
    config->source_address_mode = body[ET_DMA_SERVICE_CONFIG_SOURCE_ADDRESS_MODE_OFFSET];
    config->destination_address_mode = body[ET_DMA_SERVICE_CONFIG_DESTINATION_ADDRESS_MODE_OFFSET];
    config->source_burst = body[ET_DMA_SERVICE_CONFIG_SOURCE_BURST_OFFSET];
    config->destination_burst = body[ET_DMA_SERVICE_CONFIG_DESTINATION_BURST_OFFSET];
    config->fifo_mode = body[ET_DMA_SERVICE_CONFIG_FIFO_MODE_OFFSET];
    config->source_interface = body[ET_DMA_SERVICE_CONFIG_SOURCE_INTERFACE_OFFSET];
    config->destination_interface = body[ET_DMA_SERVICE_CONFIG_DESTINATION_INTERFACE_OFFSET];
    config->source_update_mode = body[ET_DMA_SERVICE_CONFIG_SOURCE_UPDATE_MODE_OFFSET];
    config->destination_update_mode = body[ET_DMA_SERVICE_CONFIG_DESTINATION_UPDATE_MODE_OFFSET];
    config->source_handshake_mode = (uint8_t)((body[ET_DMA_SERVICE_CONFIG_SOURCE_HANDSHAKE_OFFSET] &
                                               ET_DMA_SERVICE_HANDSHAKE_MODE_MASK) != 0u);
    config->source_handshake_polarity =
        (uint8_t)((body[ET_DMA_SERVICE_CONFIG_SOURCE_HANDSHAKE_OFFSET] &
                   ET_DMA_SERVICE_HANDSHAKE_POLARITY_MASK) >>
                  ET_DMA_SERVICE_HANDSHAKE_POLARITY_SHIFT);
    config->destination_handshake_mode =
        (uint8_t)((body[ET_DMA_SERVICE_CONFIG_DESTINATION_HANDSHAKE_OFFSET] &
                   ET_DMA_SERVICE_HANDSHAKE_MODE_MASK) != 0u);
    config->destination_handshake_polarity =
        (uint8_t)((body[ET_DMA_SERVICE_CONFIG_DESTINATION_HANDSHAKE_OFFSET] &
                   ET_DMA_SERVICE_HANDSHAKE_POLARITY_MASK) >>
                  ET_DMA_SERVICE_HANDSHAKE_POLARITY_SHIFT);
    config->source_address = source_address;
    config->destination_address = destination_address;
    config->transfer_count = read_u32(&body[ET_DMA_SERVICE_CONFIG_TRANSFER_COUNT_OFFSET]);
    config->flags = read_u32(&body[ET_DMA_SERVICE_CONFIG_FLAGS_OFFSET]);
    config->linked_list_address = linked_list_address;
    config->source_gather_interval =
        read_u32(&body[ET_DMA_SERVICE_CONFIG_SOURCE_GATHER_INTERVAL_OFFSET]);
    config->source_gather_count = read_u32(&body[ET_DMA_SERVICE_CONFIG_SOURCE_GATHER_COUNT_OFFSET]);
    config->destination_scatter_interval =
        read_u32(&body[ET_DMA_SERVICE_CONFIG_DESTINATION_SCATTER_INTERVAL_OFFSET]);
    config->destination_scatter_count =
        read_u32(&body[ET_DMA_SERVICE_CONFIG_DESTINATION_SCATTER_COUNT_OFFSET]);

    return 0;
}

/**
 * @brief Mark DMA IRQ evidence as being updated by advancing the generation counter.
 *
 * @param[in,out] service DMA Service instance whose callback-visible evidence is about to change.
 *
 * @note The odd generation value is the write side of a bounded seqlock; this helper does not enter a critical section itself.
 */
static void result_write_begin(et_dma_service_t *service)
{
    ++service->result_generation;
}

/**
 * @brief Publish completion of one DMA IRQ evidence update by advancing the generation counter.
 *
 * @param[in,out] service DMA Service instance whose evidence update has completed.
 *
 * @note The resulting even generation lets thread context detect a coherent snapshot; callers own synchronization context.
 */
static void result_write_end(et_dma_service_t *service)
{
    ++service->result_generation;
}

/**
 * @brief Clear all managed DMA IRQ evidence while the caller owns synchronization.
 *
 * @param[in,out] service DMA Service instance whose IRQ evidence is reset.
 *
 * @note The caller must already exclude concurrent thread-side access as required; only Service-local evidence is modified.
 */
static void clear_result_locked(et_dma_service_t *service)
{
    result_write_begin(service);
    service->irq_result.latched_events = 0u;
    service->irq_result.irq_count = 0u;
    service->irq_result.unexpected_count = 0u;
    service->irq_result.overflow_count = 0u;
    result_write_end(service);
}

/**
 * @brief Clear managed DMA IRQ evidence atomically from thread context.
 *
 * @param[in,out] service DMA Service instance whose IRQ evidence is reset.
 *
 * @note IRQ Manager critical protection brackets the seqlock update; DMA hardware pending state is not cleared here.
 */
static void clear_result(et_dma_service_t *service)
{
    uint32_t key = et_irq_manager_enter_critical();
    clear_result_locked(service);
    et_irq_manager_exit_critical(key);
}

/**
 * @brief Invalidate all Service-owned DMA timing evidence for an abandoned or closed transfer.
 *
 * @param[in,out] service DMA Service instance whose timing state is invalidated.
 *
 * @note IRQ Manager critical protection prevents a callback from publishing stale timing while the armed/complete/cycle fields are cleared. DMA hardware is not stopped here.
 */
static void clear_timing_state(et_dma_service_t *service)
{
    uint32_t key;

    if (service == NULL)
    {
        return;
    }

    key = et_irq_manager_enter_critical();
    service->timing_armed = 0u;
    service->timing_complete = 0u;
    service->timing_start_cycles = 0u;
    service->timing_elapsed_cycles = 0u;
    et_irq_manager_exit_critical(key);
}

/**
 * @brief Select the per-channel status mask associated with one normalized DMA event.
 *
 * @param[in] status DMA Wrap interrupt-status snapshot containing all event-bank channel masks.
 * @param[in] event One normalized DMA interrupt event bit.
 *
 * @note This helper only selects data from an existing snapshot and performs no hardware read or clear.
 *
 * @return Channel mask for the requested event, or zero for invalid input/event.
 */
static uint32_t interrupt_channels(const et_dma_wrap_interrupt_status_t *status, uint32_t event)
{
    if (status == NULL)
    {
        return 0u;
    }

    switch (event)
    {
        case ET_DMA_WRAP_IRQ_TRANSFER:
        {
            return status->transfer_channels;
        }

        case ET_DMA_WRAP_IRQ_BLOCK:
        {
            return status->block_channels;
        }

        case ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION:
        {
            return status->source_transaction_channels;
        }

        case ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION:
        {
            return status->destination_transaction_channels;
        }

        case ET_DMA_WRAP_IRQ_ERROR:
        {
            return status->error_channels;
        }

        default:
        {
            return 0u;
        }
    }
}

/**
 * @brief Quiesce the owned DMA IRQ sources after a callback observation failure and record diagnostic evidence.
 *
 * @param[in,out] service DMA Service instance owning the active managed IRQ session.
 *
 * @note This helper is bounded for IRQ context. It attempts DMA-source disable and clear, updates Service-local unexpected/overflow evidence, and does not unbind IRQ Manager routes.
 */
static void record_irq_observation_fault(et_dma_service_t *service)
{
    et_wrap_status_t disable_status;
    et_wrap_status_t clear_status;
    uint8_t maintenance_failed;

    if (service == NULL)
    {
        return;
    }

    disable_status = et_dma_wrap_disable_interrupts(service->controller_id, service->irq_channel,
                                                    service->enabled_events);
    clear_status = et_dma_wrap_clear_interrupts(service->controller_id, service->irq_channel,
                                                service->enabled_events);
    maintenance_failed =
        (uint8_t)((disable_status != ET_WRAP_STATUS_OK) || (clear_status != ET_WRAP_STATUS_OK));

    if (disable_status == ET_WRAP_STATUS_OK)
    {
        service->irq_hardware_enabled = 0u;
    }

    result_write_begin(service);
    increment_saturating(&service->irq_result.unexpected_count);

    if (maintenance_failed != 0u)
    {
        increment_saturating(&service->irq_result.overflow_count);
    }

    result_write_end(service);
}

/**
 * @brief Capture bounded DMA interrupt and optional transfer-timing evidence for one managed session.
 *
 * @param[in,out] context DMA Service instance registered as the IRQ callback context.
 * @param[in] irq_line Physical IRQ line reported by IRQ Manager.
 * @param[in] route_events Normalized event bits owned by the route that invoked the callback.
 *
 * @note This function executes in interrupt context. It snapshots status, clears observed sources on reporting channels, publishes bounded evidence, and never waits for transfer completion or decides PASS/FAIL.
 */
static void dma_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    static const uint32_t events[] = {
        ET_DMA_WRAP_IRQ_TRANSFER, ET_DMA_WRAP_IRQ_BLOCK, ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION,
        ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION, ET_DMA_WRAP_IRQ_ERROR};
    et_dma_service_t *service = (et_dma_service_t *)context;
    et_dma_wrap_interrupt_status_t status;
    uint32_t matched = 0u;
    uint32_t unexpected = 0u;
    uint32_t event_channels;
    uint32_t configured_bit;
    uint32_t allowed_channels;
    uint32_t timing_elapsed = 0u;
    uint8_t event_index;
    uint8_t channel;
    uint8_t timing_valid = 0u;

    (void)irq_line;

    /* Phase 1: Reject stale callback entry before observing DMA state. */
    if ((service == NULL) || (service->irq_enabled == 0u))
    {
        return;
    }

    /*
     * Sample the end boundary before reading or clearing DMA status. The value
     * therefore represents channel enable through managed IRQ callback entry.
     */

    /* Phase 2: Capture the optional timing end boundary before status is read or cleared. */
    if ((service->timing_armed != 0u) &&
        (et_dma_wrap_get_elapsed_cycles(service->timing_start_cycles, &timing_elapsed) ==
         ET_WRAP_STATUS_OK))
    {
        timing_valid = 1u;
    }

    /* Phase 3: Snapshot effective DMA event-bank channel masks for this callback. */
    if (et_dma_wrap_get_interrupt_status(service->controller_id, &status) != ET_WRAP_STATUS_OK)
    {
        record_irq_observation_fault(service);

        return;
    }

    configured_bit = 1u << service->irq_channel;
    allowed_channels = channel_limit_mask(service);

    /* Phase 4: Match route-owned events and acknowledge every reporting channel source. */
    for (event_index = 0u; event_index < (uint8_t)(sizeof(events) / sizeof(events[0]));
         ++event_index)
    {
        uint32_t event = events[event_index];

        if (((route_events & event) == 0u) || ((service->enabled_events & event) == 0u))
        {
            continue;
        }

        event_channels = interrupt_channels(&status, event) & allowed_channels;

        if ((event_channels & configured_bit) != 0u)
        {
            matched |= event;
        }

        if ((event_channels & ~configured_bit) != 0u)
        {
            unexpected = 1u;
        }

        for (channel = 0u; channel < service->channel_count; ++channel)
        {
            if ((event_channels & (1u << channel)) != 0u)
            {
                if (et_dma_wrap_clear_interrupts(service->controller_id, channel, event) !=
                    ET_WRAP_STATUS_OK)
                {
                    /* Record the clear failure and continue acknowledging remaining sources. */
                    result_write_begin(service);
                    increment_saturating(&service->irq_result.overflow_count);
                    result_write_end(service);
                }
            }
        }
    }

    /* Phase 5: Publish matched, unexpected and optional transfer-timing evidence. */
    result_write_begin(service);

    if (matched != 0u)
    {
        service->irq_result.latched_events |= matched;
        increment_saturating(&service->irq_result.irq_count);
    }

    if (((matched & ET_DMA_WRAP_IRQ_TRANSFER) != 0u) && (service->timing_armed != 0u) &&
        (service->timing_channel == service->irq_channel) && (timing_valid != 0u))
    {
        /* Publish timing evidence only for the armed channel's transfer event. */
        service->timing_elapsed_cycles = timing_elapsed;
        service->timing_complete = 1u;
        service->timing_armed = 0u;
    }

    if ((matched == 0u) || (unexpected != 0u))
    {
        increment_saturating(&service->irq_result.unexpected_count);
    }

    result_write_end(service);
}

/**
 * @brief Clear Service ownership metadata for a fully released DMA IRQ session.
 *
 * @param[in,out] service DMA Service instance whose route/source ownership is reset.
 *
 * @note This helper changes software ownership only; callers must disable hardware sources and unbind routes before invoking it.
 */
static void reset_irq_session(et_dma_service_t *service)
{
    service->irq_enabled = 0u;
    service->irq_hardware_enabled = 0u;
    service->irq_combined = 0u;
    service->irq_channel = 0u;
    service->irq_priority = 0u;
    service->enabled_events = 0u;
    service->route_count = 0u;
    service->route_bound_mask = 0u;
    (void)memset(service->routes, 0, sizeof(service->routes));
}

/**
 * @brief Attempt to unbind every IRQ Manager route owned by the current DMA session.
 *
 * @param[in,out] service DMA Service instance containing route bindings and their ownership mask.
 *
 * @note Successfully released route bits are cleared immediately while failed bindings remain recorded so cleanup cannot masquerade as complete.
 *
 * @return 0 when every owned route is released, otherwise -1.
 */
static int unbind_managed_routes(et_dma_service_t *service)
{
    uint8_t index;
    int failed = 0;

    for (index = 0u; index < service->route_count; ++index)
    {
        uint8_t bit = (uint8_t)(1u << index);

        if ((service->route_bound_mask & bit) == 0u)
        {
            continue;
        }

        if (et_irq_manager_unbind(service->irq_manager, service->routes[index].irq_line,
                                  dma_irq_callback, service) == 0)
        {
            service->route_bound_mask &= (uint8_t)~bit;
        }
        else
        {
            failed = 1;
        }
    }

    return failed ? -1 : 0;
}

/**
 * @brief Disable and clear all normalized DMA interrupt sources on every valid channel before a new managed session.
 *
 * @param[in] service DMA Service instance providing controller ID and runtime channel count.
 *
 * @note This function changes DMA interrupt hardware but does not bind CPU routes or publish Service IRQ ownership.
 *
 * @return ET_WRAP_STATUS_OK when every channel is quiesced, otherwise the first DMA Wrap failure.
 */
static et_wrap_status_t prepare_managed_irq_hardware(et_dma_service_t *service)
{
    et_wrap_status_t status;
    uint8_t channel;

    for (channel = 0u; channel < service->channel_count; ++channel)
    {
        status = et_dma_wrap_disable_interrupts(service->controller_id, channel,
                                                ET_DMA_SERVICE_ALL_IRQ_EVENTS);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status;
        }

        status = et_dma_wrap_clear_interrupts(service->controller_id, channel,
                                              ET_DMA_SERVICE_ALL_IRQ_EVENTS);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status;
        }
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate, bind and enable one split-route or combined-route managed DMA IRQ session.
 *
 * @param[in,out] service DMA Service instance that will own route, source and evidence state.
 * @param[in] body Fixed IRQ configuration request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] response Caller-owned IRQ configuration response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 * @param[in] combined Nonzero to request the controller combined route; zero to resolve split routes.
 *
 * @note Stale hardware is quiesced before ownership is published. Service state is established before routes/sources can invoke the callback, and binding/source-enable failures attempt bounded rollback.
 *
 * @return Stable ET status for validation, capability, route binding or DMA-source enable results.
 */
static uint16_t irq_enable(et_dma_service_t *service, const uint8_t *body, uint16_t length,
                           uint8_t *response, uint16_t capacity, uint16_t *response_length,
                           uint8_t combined)
{
    et_irq_route_t routes[ET_DMA_SERVICE_MAX_ROUTES];
    uint32_t events;
    uint32_t channel_bit;
    uint8_t channel;
    uint8_t priority;
    uint8_t route_count = 0u;
    uint8_t index;
    et_wrap_status_t status;

    /* Phase 1: Validate the fixed IRQ request and requested channel/event ownership. */
    if ((body == NULL) || (length != ET_DMA_SERVICE_IRQ_CONFIG_REQUEST_SIZE) ||
        (capacity < ET_DMA_SERVICE_IRQ_CONFIG_RESPONSE_SIZE) ||
        (bytes_are_zero(&body[ET_DMA_SERVICE_IRQ_RESERVED_OFFSET],
                        ET_DMA_SERVICE_IRQ_RESERVED_SIZE) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    events = read_u32(body);
    channel = body[ET_DMA_SERVICE_IRQ_CHANNEL_OFFSET];
    priority = body[ET_DMA_SERVICE_IRQ_PRIORITY_OFFSET];

    if ((events == 0u) || ((events & ~ET_DMA_SERVICE_ALL_IRQ_EVENTS) != 0u) ||
        (channel_is_valid(service, channel) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    channel_bit = 1u << channel;

    if ((service->controller_enabled == 0u) ||
        ((service->configured_channels & channel_bit) == 0u) || (service->active_channels != 0u))
    {
        return ET_STATUS_BUSY;
    }

    if (service->irq_enabled != 0u)
    {
        if ((events == service->enabled_events) && (channel == service->irq_channel) &&
            (priority == service->irq_priority) && (combined == service->irq_combined) &&
            (service->irq_hardware_enabled != 0u))
        {
            write_u32(&response[ET_DMA_SERVICE_IRQ_RESPONSE_EVENTS_OFFSET], events);
            response[ET_DMA_SERVICE_IRQ_RESPONSE_ROUTE_COUNT_OFFSET] = service->route_count;
            (void)memset(&response[ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_OFFSET], 0,
                         ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_SIZE);
            *response_length = ET_DMA_SERVICE_IRQ_CONFIG_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        return ET_STATUS_BUSY;
    }

    /* Phase 2: Resolve split or combined physical routes from DMA Wrap/Chip Config. */
    (void)memset(routes, 0, sizeof(routes));

    if (combined != 0u)
    {
        status = et_dma_wrap_get_combined_irq_route(service->controller_id, events, &routes[0]);
        route_count = (status == ET_WRAP_STATUS_OK) ? 1u : 0u;
    }
    else
    {
        status = et_dma_wrap_get_irq_routes(service->controller_id, events, routes,
                                            ET_DMA_SERVICE_MAX_ROUTES, &route_count);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Quiesce stale DMA source state before publishing a new managed session. */
    status = prepare_managed_irq_hardware(service);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 4: Publish complete Service ownership, then bind every resolved IRQ route. */
    service->irq_enabled = 1u;
    service->irq_hardware_enabled = 0u;
    service->irq_channel = channel;
    service->irq_priority = priority;
    service->irq_combined = combined;
    service->enabled_events = events;
    service->route_count = route_count;
    service->route_bound_mask = 0u;
    (void)memcpy(service->routes, routes, (size_t)route_count * sizeof(routes[0]));
    clear_result(service);

    for (index = 0u; index < route_count; ++index)
    {
        if (et_irq_manager_bind(service->irq_manager, &service->routes[index], priority,
                                dma_irq_callback, service) != 0)
        {
            if (unbind_managed_routes(service) == 0)
            {
                reset_irq_session(service);
            }

            return ET_STATUS_INTERNAL_ERROR;
        }

        service->route_bound_mask |= (uint8_t)(1u << index);
    }

    /* Phase 5: Enable the owned DMA source mask only after callback routes are installed. */
    status = et_dma_wrap_enable_interrupts(service->controller_id, channel, events);

    if (status != ET_WRAP_STATUS_OK)
    {
        if (unbind_managed_routes(service) == 0)
        {
            reset_irq_session(service);
        }

        return status_from_wrap(status);
    }

    service->irq_hardware_enabled = 1u;

    write_u32(&response[ET_DMA_SERVICE_IRQ_RESPONSE_EVENTS_OFFSET], events);
    response[ET_DMA_SERVICE_IRQ_RESPONSE_ROUTE_COUNT_OFFSET] = route_count;
    (void)memset(&response[ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_OFFSET], 0,
                 ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_SIZE);
    *response_length = ET_DMA_SERVICE_IRQ_CONFIG_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Disable the exact owned DMA IRQ source set and release its managed routes.
 *
 * @param[in,out] service DMA Service instance owning the active IRQ session.
 * @param[in] body Four-byte event mask that must equal the session-owned mask.
 * @param[in] length Number of valid request-body bytes.
 *
 * @note Hardware sources are disabled before remaining visible events are cleared and IRQ Manager routes are released. Software ownership is reset only after cleanup succeeds.
 *
 * @return Stable ET status for validation or cleanup outcome.
 */
static uint16_t irq_disable(et_dma_service_t *service, const uint8_t *body, uint16_t length)
{
    uint32_t events;
    uint32_t pending = 0u;
    et_wrap_status_t status;

    /* Phase 1: Validate the exact event mask owned by the active managed session. */
    if ((body == NULL) || (length != ET_DMA_SERVICE_U32_BODY_SIZE))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    events = read_u32(body);

    if (service->irq_enabled == 0u)
    {
        return ET_STATUS_OK;
    }

    if (events != service->enabled_events)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Disable DMA source delivery and clear any still-visible pending events. */
    if (service->irq_hardware_enabled != 0u)
    {
        status =
            et_dma_wrap_disable_interrupts(service->controller_id, service->irq_channel, events);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        service->irq_hardware_enabled = 0u;
    }

    status = et_dma_wrap_get_pending_events(service->controller_id, service->irq_channel, &pending);

    if ((status == ET_WRAP_STATUS_OK) && (pending != 0u))
    {
        status =
            et_dma_wrap_clear_interrupts(service->controller_id, service->irq_channel, pending);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    /* Phase 3: Release every IRQ Manager route before clearing software ownership. */
    if (unbind_managed_routes(service) != 0)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    reset_irq_session(service);

    return ET_STATUS_OK;
}

/**
 * @brief Encode one coherent snapshot of callback-owned DMA IRQ evidence.
 *
 * @param[in] service DMA Service instance containing the seqlock-protected evidence.
 * @param[out] response Caller-owned IRQ result response buffer.
 * @param[in] capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Thread context retries a bounded number of generation-stable reads and never disables interrupts merely to read evidence.
 *
 * @return ET_STATUS_OK for a coherent snapshot, ET_STATUS_BUSY after bounded contention, or ET_STATUS_INVALID_PARAM for insufficient capacity.
 */
static uint16_t write_irq_result(et_dma_service_t *service, uint8_t *response, uint16_t capacity,
                                 uint16_t *response_length)
{
    et_dma_irq_result_t snapshot;
    uint32_t before;
    uint32_t after;
    uint8_t attempt;

    if (capacity < ET_DMA_SERVICE_IRQ_RESULT_RESPONSE_SIZE)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    for (attempt = 0u; attempt < ET_DMA_SERVICE_IRQ_RESULT_SNAPSHOT_ATTEMPTS; ++attempt)
    {
        before = service->result_generation;

        if ((before & 1u) != 0u)
        {
            continue;
        }

        snapshot.latched_events = service->irq_result.latched_events;
        snapshot.irq_count = service->irq_result.irq_count;
        snapshot.unexpected_count = service->irq_result.unexpected_count;
        snapshot.overflow_count = service->irq_result.overflow_count;
        after = service->result_generation;

        if ((before == after) && ((after & 1u) == 0u))
        {
            write_u32(&response[ET_DMA_SERVICE_IRQ_RESULT_EVENTS_OFFSET], snapshot.latched_events);
            write_u32(&response[ET_DMA_SERVICE_IRQ_RESULT_COUNT_OFFSET], snapshot.irq_count);
            write_u32(&response[ET_DMA_SERVICE_IRQ_RESULT_UNEXPECTED_OFFSET],
                      snapshot.unexpected_count);
            write_u32(&response[ET_DMA_SERVICE_IRQ_RESULT_OVERFLOW_OFFSET],
                      snapshot.overflow_count);
            *response_length = ET_DMA_SERVICE_IRQ_RESULT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }
    }

    return ET_STATUS_BUSY;
}

/**
 * @brief Execute one single-channel lifecycle or status command under DMA Service ownership.
 *
 * @param[in,out] service DMA Service instance owning controller/channel lifecycle state.
 * @param[in] command_id Stable DMA channel command identifier.
 * @param[in] body Fixed one-word channel request body.
 * @param[in] length Number of valid request-body bytes.
 * @param[out] response Caller-owned status response buffer when required.
 * @param[in] capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Configured/active/timing Service state is committed only after the corresponding DMA Wrap operation succeeds; status reads may retire a channel observed free by hardware.
 *
 * @return Stable ET status for request validation, lifecycle conflicts, Wrap execution or status observation.
 */
static uint16_t handle_channel_command(et_dma_service_t *service, uint16_t command_id,
                                       const uint8_t *body, uint16_t length, uint8_t *response,
                                       uint16_t capacity, uint16_t *response_length)
{
    et_dma_wrap_channel_status_t channel_status;
    et_wrap_status_t status;
    uint8_t channel;
    uint32_t channel_bit;

    /* Step 1: Validate the fixed single-channel request envelope and channel ID. */
    if ((body == NULL) || (length != ET_DMA_SERVICE_U32_BODY_SIZE) ||
        (bytes_are_zero(&body[ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_OFFSET],
                        ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_SIZE) == 0u) ||
        (channel_is_valid(service, body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET]) == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    channel = body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET];
    channel_bit = 1u << channel;

    /* Step 2: Apply deconfigure/start/stop/suspend/resume with commit-after-Wrap state updates. */
    if (command_id == ET_DMA_COMMAND_CHANNEL_DECONFIGURE)
    {
        if ((service->irq_enabled != 0u) && (service->irq_channel == channel))
        {
            return ET_STATUS_BUSY;
        }

        if ((service->configured_channels & channel_bit) == 0u)
        {
            return ET_STATUS_OK;
        }

        status = et_dma_wrap_deconfigure_channel(service->controller_id, channel);

        if (status == ET_WRAP_STATUS_OK)
        {
            service->configured_channels &= ~channel_bit;
            service->active_channels &= ~channel_bit;

            if (service->timing_channel == channel)
            {
                clear_timing_state(service);
            }
        }

        return status_from_wrap(status);
    }

    if (command_id == ET_DMA_COMMAND_CHANNEL_START)
    {
        if ((service->controller_enabled == 0u) ||
            ((service->configured_channels & channel_bit) == 0u) ||
            ((service->active_channels & channel_bit) != 0u))
        {
            return ET_STATUS_BUSY;
        }

        status = et_dma_wrap_clear_interrupts(service->controller_id, channel,
                                              ET_DMA_SERVICE_ALL_IRQ_EVENTS);

        if (status != ET_WRAP_STATUS_OK)
        {
            return status_from_wrap(status);
        }

        status = et_dma_wrap_start_channel(service->controller_id, channel);

        if (status == ET_WRAP_STATUS_OK)
        {
            service->active_channels |= channel_bit;
        }

        return status_from_wrap(status);
    }

    if (command_id == ET_DMA_COMMAND_CHANNEL_STOP)
    {
        if (((service->configured_channels & channel_bit) == 0u) ||
            ((service->active_channels & channel_bit) == 0u))
        {
            return ET_STATUS_OK;
        }

        status = et_dma_wrap_stop_channel(service->controller_id, channel);

        if (status == ET_WRAP_STATUS_OK)
        {
            service->active_channels &= ~channel_bit;

            if (service->timing_channel == channel)
            {
                clear_timing_state(service);
            }
        }

        return status_from_wrap(status);
    }

    if ((command_id == ET_DMA_COMMAND_CHANNEL_SUSPEND) ||
        (command_id == ET_DMA_COMMAND_CHANNEL_RESUME))
    {
        if ((service->active_channels & channel_bit) == 0u)
        {
            return ET_STATUS_BUSY;
        }

        status = (command_id == ET_DMA_COMMAND_CHANNEL_SUSPEND)
                     ? et_dma_wrap_suspend_channel(service->controller_id, channel)
                     : et_dma_wrap_resume_channel(service->controller_id, channel);

        return status_from_wrap(status);
    }

    /* Step 3: Fall through to read and encode normalized channel status facts. */
    if (capacity < ET_DMA_SERVICE_CHANNEL_STATUS_RESPONSE_SIZE)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    status = et_dma_wrap_get_channel_status(service->controller_id, channel, &channel_status);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    if (channel_status.is_free != 0u)
    {
        service->active_channels &= ~channel_bit;
    }

    response[ET_DMA_SERVICE_CHANNEL_STATUS_FREE_OFFSET] = channel_status.is_free;
    response[ET_DMA_SERVICE_CHANNEL_STATUS_FIFO_EMPTY_OFFSET] = channel_status.fifo_empty;
    (void)memset(&response[ET_DMA_SERVICE_CHANNEL_STATUS_RESERVED_OFFSET], 0,
                 ET_DMA_SERVICE_CHANNEL_STATUS_RESERVED_SIZE);
    write_u32(&response[ET_DMA_SERVICE_CHANNEL_STATUS_INTERRUPTS_OFFSET],
              channel_status.interrupt_flags);
    *response_length = ET_DMA_SERVICE_CHANNEL_STATUS_RESPONSE_SIZE;

    return ET_STATUS_OK;
}

/**
 * @brief Encode one read-only DMA component, interrupt-bank or channel-register snapshot command.
 *
 * @param[in] service DMA Service instance providing the logical controller ID.
 * @param[in] command_id Stable DMA snapshot command identifier.
 * @param[in] request_body Snapshot-specific request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned snapshot response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Snapshot commands observe and encode Driver facts only; they do not clear interrupts, start channels or derive a test verdict.
 *
 * @return Stable ET status for validation, Wrap observation or unsupported command.
 */
static uint16_t handle_snapshot_command(et_dma_service_t *service, uint16_t command_id,
                                        const uint8_t *request_body, uint16_t request_length,
                                        uint8_t *response_body, uint16_t response_capacity,
                                        uint16_t *response_length)
{
    et_dma_wrap_component_snapshot_t component_snapshot;
    et_dma_wrap_interrupt_snapshot_t interrupt_snapshot;
    et_dma_wrap_channel_snapshot_t channel_snapshot;
    et_wrap_status_t status;
    uint8_t index;

    /* Step 1: Select the requested read-only DMA diagnostic snapshot family. */
    switch (command_id)
    {
        case ET_DMA_COMMAND_COMPONENT_SNAPSHOT_GET:
        {
            if ((request_length != ET_DMA_SERVICE_U32_BODY_SIZE) ||
                (response_capacity < ET_DMA_SERVICE_COMPONENT_RESPONSE_SIZE) ||
                (bytes_are_zero(&request_body[ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_OFFSET],
                                ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_dma_wrap_get_component_snapshot(
                service->controller_id, request_body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET],
                &component_snapshot);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(&response_body[ET_DMA_SERVICE_COMPONENT_DMA_ID_OFFSET],
                      component_snapshot.dma_id);
            write_u32(&response_body[ET_DMA_SERVICE_COMPONENT_ID_OFFSET],
                      component_snapshot.component_id);

            for (index = 0u; index < ET_DMA_WRAP_COMPONENT_CHANNEL_PARAMETER_COUNT; ++index)
            {
                write_u32(&response_body[ET_DMA_SERVICE_COMPONENT_CHANNELS_OFFSET +
                                         ((uint16_t)index * ET_DMA_SERVICE_WIRE_WORD_SIZE)],
                          component_snapshot.channel_params[index]);
            }

            write_u32(&response_body[ET_DMA_SERVICE_COMPONENT_MULTI_BLOCK_OFFSET],
                      component_snapshot.multi_block_params);
            write_u32(&response_body[ET_DMA_SERVICE_COMPONENT_MAX_BLOCK_OFFSET],
                      component_snapshot.max_block_size_params);
            *response_length = ET_DMA_SERVICE_COMPONENT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        /* Step 2: Encode interrupt-bank facts without clearing any observed source. */
        case ET_DMA_COMMAND_INTERRUPT_SNAPSHOT_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_DMA_SERVICE_INTERRUPT_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status =
                et_dma_wrap_get_interrupt_snapshot(service->controller_id, &interrupt_snapshot);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            for (index = 0u; index < ET_DMA_WRAP_IRQ_SLOT_COUNT; ++index)
            {
                write_u32(&response_body[ET_DMA_SERVICE_INTERRUPT_RAW_OFFSET +
                                         ((uint16_t)index * ET_DMA_SERVICE_WIRE_WORD_SIZE)],
                          interrupt_snapshot.raw[index]);
                write_u32(&response_body[ET_DMA_SERVICE_INTERRUPT_STATUS_OFFSET +
                                         ((uint16_t)index * ET_DMA_SERVICE_WIRE_WORD_SIZE)],
                          interrupt_snapshot.status[index]);
                write_u32(&response_body[ET_DMA_SERVICE_INTERRUPT_MASK_OFFSET +
                                         ((uint16_t)index * ET_DMA_SERVICE_WIRE_WORD_SIZE)],
                          interrupt_snapshot.mask[index]);
            }

            write_u32(&response_body[ET_DMA_SERVICE_INTERRUPT_COMBINED_OFFSET],
                      interrupt_snapshot.combined_status);
            *response_length = ET_DMA_SERVICE_INTERRUPT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_DMA_COMMAND_CHANNEL_SNAPSHOT_GET:
        {
            if ((request_length != ET_DMA_SERVICE_U32_BODY_SIZE) ||
                (response_capacity < ET_DMA_SERVICE_CHANNEL_SNAPSHOT_RESPONSE_SIZE) ||
                (bytes_are_zero(&request_body[ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_OFFSET],
                                ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_SIZE) == 0u) ||
                (channel_is_valid(service, request_body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET]) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_dma_wrap_get_channel_snapshot(
                service->controller_id, request_body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET],
                &channel_snapshot);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_SOURCE_OFFSET],
                      channel_snapshot.source_address);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_DESTINATION_OFFSET],
                      channel_snapshot.destination_address);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_LLI_OFFSET],
                      channel_snapshot.linked_list_address);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_CONTROL_LOW_OFFSET],
                      channel_snapshot.control_low);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_CONTROL_HIGH_OFFSET],
                      channel_snapshot.control_high);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_CONFIG_LOW_OFFSET],
                      channel_snapshot.config_low);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_CONFIG_HIGH_OFFSET],
                      channel_snapshot.config_high);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_SOURCE_GATHER_OFFSET],
                      channel_snapshot.source_gather);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_DESTINATION_SCATTER_OFFSET],
                      channel_snapshot.destination_scatter);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_SOURCE_BURST_OFFSET],
                      channel_snapshot.source_burst);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_DESTINATION_BURST_OFFSET],
                      channel_snapshot.destination_burst);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_BLOCK_SIZE_OFFSET],
                      channel_snapshot.block_size);
            write_u32(&response_body[ET_DMA_SERVICE_CHANNEL_FIFO_MODE_OFFSET],
                      channel_snapshot.fifo_mode);
            *response_length = ET_DMA_SERVICE_CHANNEL_SNAPSHOT_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch DMA controller lifecycle, channel configuration and basic channel commands.
 *
 * @param[in,out] service DMA Service instance owning controller and channel state.
 * @param[in] command_id Stable DMA command identifier.
 * @param[in] request_body Command request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer when required.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note The dispatcher returns ET_STATUS_INVALID_COMMAND only when the command belongs to another DMA category. Lifecycle state changes are committed after successful Wrap calls.
 *
 * @return Stable ET status for the handled command, or ET_STATUS_INVALID_COMMAND when not handled here.
 */
static uint16_t handle_controller_commands(et_dma_service_t *service, uint16_t command_id,
                                           const uint8_t *request_body, uint16_t request_length,
                                           uint8_t *response_body, uint16_t response_capacity,
                                           uint16_t *response_length)
{
    et_dma_wrap_capabilities_t capabilities;
    et_dma_wrap_config_t config;
    et_wrap_status_t status;
    uint32_t channel_bit;

    /* Step 1: Route capability and controller lifecycle commands. */
    switch (command_id)
    {
        case ET_DMA_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_DMA_SERVICE_CAPABILITIES_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_dma_wrap_get_capabilities(service->controller_id, &capabilities);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(&response_body[ET_DMA_SERVICE_CAP_FEATURES_OFFSET],
                      capabilities.feature_flags);
            write_u16(&response_body[ET_DMA_SERVICE_CAP_CHANNEL_COUNT_OFFSET],
                      capabilities.channel_count);
            write_u16(&response_body[ET_DMA_SERVICE_CAP_MAX_TRANSFER_OFFSET],
                      capabilities.max_transfer_count);
            write_u32(&response_body[ET_DMA_SERVICE_CAP_MAX_INTERVAL_OFFSET],
                      capabilities.max_gather_scatter_interval);
            write_u32(&response_body[ET_DMA_SERVICE_CAP_MAX_COUNT_OFFSET],
                      capabilities.max_gather_scatter_count);
            write_u32(&response_body[ET_DMA_SERVICE_CAP_IRQ_EVENTS_OFFSET],
                      ET_DMA_SERVICE_ALL_IRQ_EVENTS);
            *response_length = ET_DMA_SERVICE_CAPABILITIES_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_DMA_COMMAND_CONTROLLER_ENABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (service->controller_enabled != 0u)
            {
                return ET_STATUS_OK;
            }

            status = et_dma_wrap_enable_controller(service->controller_id);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->controller_enabled = 1u;
            }

            return status_from_wrap(status);
        }

        case ET_DMA_COMMAND_CONTROLLER_DISABLE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if ((service->irq_enabled != 0u) || (service->configured_channels != 0u))
            {
                return ET_STATUS_BUSY;
            }

            if (service->controller_enabled == 0u)
            {
                return ET_STATUS_OK;
            }

            status = et_dma_wrap_disable_controller(service->controller_id);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->controller_enabled = 0u;
                service->active_channels = 0u;
                clear_timing_state(service);
            }

            return status_from_wrap(status);
        }

        /* Step 2: Decode and commit one channel configuration, then route basic channel operations. */
        case ET_DMA_COMMAND_CHANNEL_CONFIGURE:
        {
            if (service->controller_enabled == 0u)
            {
                return ET_STATUS_BUSY;
            }

            if (decode_config(service, request_body, request_length, &config) != 0)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            channel_bit = 1u << config.channel_id;

            if ((service->configured_channels & channel_bit) != 0u)
            {
                return ET_STATUS_BUSY;
            }

            status = et_dma_wrap_configure_channel(&config);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->configured_channels |= channel_bit;
                service->active_channels &= ~channel_bit;
            }

            return status_from_wrap(status);
        }

        case ET_DMA_COMMAND_CHANNEL_DECONFIGURE:
        case ET_DMA_COMMAND_CHANNEL_START:
        case ET_DMA_COMMAND_CHANNEL_STOP:
        case ET_DMA_COMMAND_CHANNEL_SUSPEND:
        case ET_DMA_COMMAND_CHANNEL_RESUME:
        case ET_DMA_COMMAND_CHANNEL_STATUS_GET:
        {
            return handle_channel_command(service, command_id, request_body, request_length,
                                          response_body, response_capacity, response_length);
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch DMA timed-start, timing observation, free-channel discovery and atomic multi-channel start commands.
 *
 * @param[in,out] service DMA Service instance owning channel and timing state.
 * @param[in] command_id Stable DMA timing/discovery command identifier.
 * @param[in] request_body Command request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer when required.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Timed start holds IRQ Manager critical protection across Driver start and Service timing-state publication so a short transfer callback cannot race the armed state. Deprecated wait commands remain unsupported.
 *
 * @return Stable ET status for the handled command, or ET_STATUS_INVALID_COMMAND when not handled here.
 */
static uint16_t handle_channel_timing_commands(et_dma_service_t *service, uint16_t command_id,
                                               const uint8_t *request_body, uint16_t request_length,
                                               uint8_t *response_body, uint16_t response_capacity,
                                               uint16_t *response_length)
{
    et_dma_wrap_channel_status_t channel_status;
    et_wrap_status_t status;
    uint8_t channel;
    uint32_t channel_mask;
    uint32_t channel_bit;
    uint32_t allowed_mask = channel_limit_mask(service);
    uint32_t irq_key;
    uint32_t start_cycles;

    /* Step 1: Route target-cycle timing and read-only timing/discovery commands. */
    switch (command_id)
    {
        case ET_DMA_COMMAND_CHANNEL_START_TIMED:
        {
            if ((request_body == NULL) || (request_length != ET_DMA_SERVICE_U32_BODY_SIZE) ||
                (bytes_are_zero(&request_body[ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_OFFSET],
                                ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_SIZE) == 0u) ||
                (channel_is_valid(service, request_body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET]) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            channel = request_body[ET_DMA_SERVICE_SINGLE_VALUE_OFFSET];
            channel_bit = 1u << channel;

            if ((service->controller_enabled == 0u) ||
                ((service->configured_channels & channel_bit) == 0u) ||
                ((service->active_channels & channel_bit) != 0u) || (service->irq_enabled == 0u) ||
                (service->irq_channel != channel) ||
                ((service->enabled_events & ET_DMA_WRAP_IRQ_TRANSFER) == 0u))
            {
                return ET_STATUS_BUSY;
            }

            status = et_dma_wrap_clear_interrupts(service->controller_id, channel,
                                                  ET_DMA_SERVICE_ALL_IRQ_EVENTS);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            /* Prevent a very short transfer callback from preceding state publish. */
            irq_key = et_irq_manager_enter_critical();
            status =
                et_dma_wrap_start_channel_timed(service->controller_id, channel, &start_cycles);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->timing_channel = channel;
                service->timing_start_cycles = start_cycles;
                service->timing_elapsed_cycles = 0u;
                service->timing_complete = 0u;
                service->timing_armed = 1u;
                service->active_channels |= channel_bit;
            }

            et_irq_manager_exit_critical(irq_key);

            return status_from_wrap(status);
        }

        case ET_DMA_COMMAND_TIMING_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_capacity < ET_DMA_SERVICE_TIMING_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            /* Copy callback-owned fields as one coherent response snapshot. */
            irq_key = et_irq_manager_enter_critical();
            (void)memset(response_body, 0, ET_DMA_SERVICE_TIMING_RESPONSE_SIZE);
            response_body[ET_DMA_SERVICE_TIMING_COMPLETE_OFFSET] = service->timing_complete;
            response_body[ET_DMA_SERVICE_TIMING_CHANNEL_OFFSET] = service->timing_channel;
            write_u32(&response_body[ET_DMA_SERVICE_TIMING_ELAPSED_OFFSET],
                      service->timing_elapsed_cycles);
            et_irq_manager_exit_critical(irq_key);
            *response_length = ET_DMA_SERVICE_TIMING_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_DMA_COMMAND_FREE_CHANNEL_FIND:
        {
            if ((request_length != 0u) ||
                (response_capacity < ET_DMA_SERVICE_FREE_CHANNEL_RESPONSE_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (channel = 0u; channel < service->channel_count; ++channel)
            {
                channel_bit = 1u << channel;

                if ((service->configured_channels & channel_bit) != 0u)
                {
                    continue;
                }

                status = et_dma_wrap_get_channel_status(service->controller_id, channel,
                                                        &channel_status);

                if ((status == ET_WRAP_STATUS_OK) && (channel_status.is_free != 0u))
                {
                    (void)memset(response_body, 0, ET_DMA_SERVICE_FREE_CHANNEL_RESPONSE_SIZE);
                    response_body[ET_DMA_SERVICE_FREE_CHANNEL_ID_OFFSET] = channel;
                    *response_length = ET_DMA_SERVICE_FREE_CHANNEL_RESPONSE_SIZE;

                    return ET_STATUS_OK;
                }
            }

            return ET_STATUS_BUSY;
        }

        /* Step 2: Validate and issue the atomic multi-channel start extension. */
        case ET_DMA_COMMAND_CHANNELS_START:
        {
            if (request_length != ET_DMA_SERVICE_U32_BODY_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            channel_mask = read_u32(request_body);

            if ((channel_mask == 0u) || ((channel_mask & ~allowed_mask) != 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if ((service->controller_enabled == 0u) ||
                ((channel_mask & ~service->configured_channels) != 0u) ||
                ((channel_mask & service->active_channels) != 0u))
            {
                return ET_STATUS_BUSY;
            }

            for (channel = 0u; channel < service->channel_count; ++channel)
            {
                if ((channel_mask & (1u << channel)) == 0u)
                {
                    continue;
                }

                status = et_dma_wrap_clear_interrupts(service->controller_id, channel,
                                                      ET_DMA_SERVICE_ALL_IRQ_EVENTS);

                if (status != ET_WRAP_STATUS_OK)
                {
                    return status_from_wrap(status);
                }
            }

            status = et_dma_wrap_start_channels(service->controller_id, channel_mask);

            if (status == ET_WRAP_STATUS_OK)
            {
                service->active_channels |= channel_mask;
            }

            return status_from_wrap(status);
        }

        case ET_DMA_COMMAND_CHANNEL_START_WAIT:
        case ET_DMA_COMMAND_CHANNELS_START_WAIT_ORDER:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Route read-only DMA snapshot command identifiers to the focused snapshot encoder.
 *
 * @param[in] service DMA Service instance providing controller context.
 * @param[in] command_id Stable DMA command identifier.
 * @param[in] request_body Command request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note This helper performs dispatch only and does not touch DMA hardware directly.
 *
 * @return Snapshot command status, or ET_STATUS_INVALID_COMMAND when the ID is outside this category.
 */
static uint16_t handle_snapshot_commands(et_dma_service_t *service, uint16_t command_id,
                                         const uint8_t *request_body, uint16_t request_length,
                                         uint8_t *response_body, uint16_t response_capacity,
                                         uint16_t *response_length)
{
    switch (command_id)
    {
        case ET_DMA_COMMAND_COMPONENT_SNAPSHOT_GET:
        {
            return handle_snapshot_command(service, command_id, request_body, request_length,
                                           response_body, response_capacity, response_length);
        }

        case ET_DMA_COMMAND_INTERRUPT_SNAPSHOT_GET:
        {
            return handle_snapshot_command(service, command_id, request_body, request_length,
                                           response_body, response_capacity, response_length);
        }

        case ET_DMA_COMMAND_CHANNEL_SNAPSHOT_GET:
        {
            return handle_snapshot_command(service, command_id, request_body, request_length,
                                           response_body, response_capacity, response_length);
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Dispatch DMA LLI, direct interrupt-control, managed IRQ and software-handshake commands.
 *
 * @param[in,out] service DMA Service instance owning controller, route and channel state.
 * @param[in] command_id Stable DMA advanced command identifier.
 * @param[in] request_body Command request body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer when required.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note LLI V2 writes only to a trusted target descriptor address through DMA Wrap; direct interrupt controls respect any active managed-session ownership, and software handshakes require an active channel.
 *
 * @return Stable ET status for the handled command, or ET_STATUS_INVALID_COMMAND when not handled here.
 */
static uint16_t handle_advanced_commands(et_dma_service_t *service, uint16_t command_id,
                                         const uint8_t *request_body, uint16_t request_length,
                                         uint8_t *response_body, uint16_t response_capacity,
                                         uint16_t *response_length)
{
    et_dma_wrap_config_t config;
    et_wrap_status_t status;
    uintptr_t descriptor_address;
    uint64_t descriptor_wire;
    uint8_t channel;
    uint32_t channel_bit;

    /* Step 1: Route LLI and direct interrupt-control operations. */
    switch (command_id)
    {
        case ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT:
        {
            if ((request_body == NULL) || (request_length != ET_DMA_SERVICE_LLI_V1_REQUEST_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT_V2:
        {
            if ((request_body == NULL) || (request_length != ET_DMA_SERVICE_LLI_V2_REQUEST_SIZE) ||
                (request_body[ET_DMA_SERVICE_LLI_LAST_FLAG_OFFSET] > 1u) ||
                (bytes_are_zero(&request_body[ET_DMA_SERVICE_LLI_RESERVED_OFFSET],
                                ET_DMA_SERVICE_LLI_RESERVED_SIZE) == 0u) ||
                (decode_config(service, request_body, ET_DMA_SERVICE_CONFIG_REQUEST_SIZE,
                               &config) != 0))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            descriptor_wire = read_u64(&request_body[ET_DMA_SERVICE_LLI_DESCRIPTOR_OFFSET]);
            descriptor_address = (uintptr_t)descriptor_wire;

            if ((descriptor_address == (uintptr_t)0u) ||
                ((uint64_t)descriptor_address != descriptor_wire))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_dma_wrap_init_lli_descriptor(
                &config, descriptor_address, request_body[ET_DMA_SERVICE_LLI_LAST_FLAG_OFFSET]));
        }

        case ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE:
        case ET_DMA_COMMAND_INTERRUPT_MASK_DISABLE:
        case ET_DMA_COMMAND_INTERRUPT_PENDING_CLEAR:
        {
            if ((request_body == NULL) ||
                (request_length != ET_DMA_SERVICE_INTERRUPT_CONTROL_REQUEST_SIZE) ||
                (request_body[ET_DMA_SERVICE_IRQ_PRIORITY_OFFSET] != 0u) ||
                (bytes_are_zero(&request_body[ET_DMA_SERVICE_IRQ_RESERVED_OFFSET],
                                ET_DMA_SERVICE_IRQ_RESERVED_SIZE) == 0u) ||
                (channel_is_valid(service, request_body[ET_DMA_SERVICE_IRQ_CHANNEL_OFFSET]) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (service->controller_enabled == 0u)
            {
                return ET_STATUS_BUSY;
            }

            channel = request_body[ET_DMA_SERVICE_IRQ_CHANNEL_OFFSET];

            if ((service->irq_enabled != 0u) &&
                ((channel != service->irq_channel) ||
                 (read_u32(&request_body[ET_DMA_SERVICE_IRQ_EVENTS_OFFSET]) !=
                  service->enabled_events)))
            {
                return ET_STATUS_BUSY;
            }

            if (command_id == ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE)
            {
                status = et_dma_wrap_set_interrupt_mask(
                    service->controller_id, channel,
                    read_u32(&request_body[ET_DMA_SERVICE_IRQ_EVENTS_OFFSET]), 1u);
            }
            else if (command_id == ET_DMA_COMMAND_INTERRUPT_MASK_DISABLE)
            {
                status = et_dma_wrap_set_interrupt_mask(
                    service->controller_id, channel,
                    read_u32(&request_body[ET_DMA_SERVICE_IRQ_EVENTS_OFFSET]), 0u);
            }
            else
            {
                status = et_dma_wrap_clear_interrupts(
                    service->controller_id, channel,
                    read_u32(&request_body[ET_DMA_SERVICE_IRQ_EVENTS_OFFSET]));
            }

            if ((status == ET_WRAP_STATUS_OK) && (service->irq_enabled != 0u) &&
                (command_id != ET_DMA_COMMAND_INTERRUPT_PENDING_CLEAR))
            {
                service->irq_hardware_enabled =
                    (command_id == ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE) ? 1u : 0u;
            }

            return status_from_wrap(status);
        }

        /* Step 2: Route managed IRQ ownership/evidence and software-handshake operations. */
        case ET_DMA_COMMAND_IRQ_ENABLE:
        {
            return irq_enable(service, request_body, request_length, response_body,
                              response_capacity, response_length, 0u);
        }

        case ET_DMA_COMMAND_IRQ_COMBINED_ENABLE:
        {
            return irq_enable(service, request_body, request_length, response_body,
                              response_capacity, response_length, 1u);
        }

        case ET_DMA_COMMAND_IRQ_DISABLE:
        {
            return irq_disable(service, request_body, request_length);
        }

        case ET_DMA_COMMAND_IRQ_RESULT_GET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return write_irq_result(service, response_body, response_capacity, response_length);
        }

        case ET_DMA_COMMAND_IRQ_RESULT_CLEAR:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            clear_result(service);

            return ET_STATUS_OK;
        }

        case ET_DMA_COMMAND_SOFTWARE_HANDSHAKE_REQUEST_SET:
        {
            if ((request_body == NULL) || (request_length != ET_DMA_SERVICE_U32_BODY_SIZE) ||
                (request_body[ET_DMA_SERVICE_SOFTWARE_TARGET_OFFSET] >
                 ET_DMA_WRAP_HANDSHAKE_TARGET_DESTINATION) ||
                (request_body[ET_DMA_SERVICE_SOFTWARE_REQUEST_OFFSET] >
                 ET_DMA_WRAP_SOFTWARE_REQUEST_LAST) ||
                (request_body[ET_DMA_SERVICE_SOFTWARE_ACTIVE_OFFSET] > 1u) ||
                (channel_is_valid(service, request_body[ET_DMA_SERVICE_SOFTWARE_CHANNEL_OFFSET]) ==
                 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            channel_bit = 1u << request_body[ET_DMA_SERVICE_SOFTWARE_CHANNEL_OFFSET];

            if ((service->active_channels & channel_bit) == 0u)
            {
                return ET_STATUS_BUSY;
            }

            return status_from_wrap(et_dma_wrap_set_software_handshake_request(
                service->controller_id, request_body[ET_DMA_SERVICE_SOFTWARE_CHANNEL_OFFSET],
                request_body[ET_DMA_SERVICE_SOFTWARE_TARGET_OFFSET],
                request_body[ET_DMA_SERVICE_SOFTWARE_REQUEST_OFFSET],
                request_body[ET_DMA_SERVICE_SOFTWARE_ACTIVE_OFFSET]));
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Validate one DMA Service request envelope and route it through the four command categories.
 *
 * @param[in,out] context DMA Service instance registered with the Service Router.
 * @param[in] command_id Stable DMA command identifier.
 * @param[in] request_body Request-body bytes, or NULL only for an empty body.
 * @param[in] request_length Number of valid request-body bytes.
 * @param[out] response_body Caller-owned response buffer.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 *
 * @note Category dispatch uses ET_STATUS_INVALID_COMMAND as the internal continue-search sentinel; the handler itself never calls another IP Service or decides PASS/FAIL.
 *
 * @return Stable ET status produced by the first matching DMA command category.
 */
static uint16_t dma_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    et_dma_service_t *service = (et_dma_service_t *)context;
    uint16_t status;

    /* Step 1: Validate the common Service Router envelope and reset response length. */
    if ((service == NULL) || (response_body == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Step 2: Search controller, timing, snapshot and advanced command categories in order. */
    status = handle_controller_commands(service, command_id, request_body, request_length,
                                        response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    status = handle_channel_timing_commands(service, command_id, request_body, request_length,
                                            response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    status = handle_snapshot_commands(service, command_id, request_body, request_length,
                                      response_body, response_capacity, response_length);

    if (status != ET_STATUS_INVALID_COMMAND)
    {
        return status;
    }

    return handle_advanced_commands(service, command_id, request_body, request_length,
                                    response_body, response_capacity, response_length);
}

/**
 * @brief Initialize one DMA Service descriptor and runtime capability state without touching DMA hardware.
 *
 * @param[out] service Caller-owned DMA Service storage to initialize.
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] irq_manager Common IRQ Manager used by later managed IRQ commands.
 *
 * @note Initialization queries DMA Wrap capabilities, clears Service state and installs the router descriptor; controller/channel hardware remains unchanged.
 *
 * @return 0 on successful initialization, otherwise -1.
 */
int et_dma_service_init(et_dma_service_t *service, et_dma_wrap_controller_id_t controller_id,
                        et_irq_manager_t *irq_manager)
{
    et_dma_wrap_capabilities_t capabilities;

    if ((service == NULL) || (irq_manager == NULL) ||
        (et_dma_wrap_get_capabilities(controller_id, &capabilities) != ET_WRAP_STATUS_OK) ||
        (capabilities.channel_count == 0u) ||
        (capabilities.channel_count > ET_DMA_SERVICE_MAX_CHANNELS))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->controller_id = controller_id;
    service->channel_count = (uint8_t)capabilities.channel_count;
    service->irq_manager = irq_manager;
    service->descriptor.service_id = ET_DMA_SERVICE_ID;
    service->descriptor.instance_id = controller_id;
    service->descriptor.context = service;
    service->descriptor.handle = dma_handle;

    return 0;
}

/**
 * @brief Return the Service Router descriptor of an initialized DMA Service instance.
 *
 * @param[in] service DMA Service instance whose descriptor is requested.
 *
 * @note This is a read-only pointer query and performs no hardware access.
 *
 * @return Descriptor pointer when service is non-NULL, otherwise NULL.
 */
const et_service_descriptor_t *et_dma_service_descriptor(const et_dma_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct one DMA Service instance through the chip-neutral Service factory contract.
 *
 * @param[out] storage Caller-provided storage for one et_dma_service_t instance.
 * @param[in] instance_id Stable logical DMA controller identifier from the application manifest.
 * @param[in] context Shared factory context providing the IRQ Manager.
 * @param[out] descriptor Receives the initialized Service Router descriptor.
 *
 * @note This adapter delegates to et_dma_service_init(); therefore creation queries capabilities but does not enable/configure DMA hardware.
 *
 * @return 0 when the Service and descriptor are created successfully, otherwise -1.
 */
int et_dma_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_dma_service_t *service = (et_dma_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_dma_service_init(service, (et_dma_wrap_controller_id_t)instance_id,
                            context->irq_manager) != 0)
    {
        return -1;
    }

    *descriptor = et_dma_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
