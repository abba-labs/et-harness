/** @file et_can_service.c @brief Decode bounded CAN actions and return raw facts. */
#include "et_can_service.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

/**
 * @brief Translate a CAN Wrap result to the existing ET status vocabulary.
 * @param[in] status Result of the requested primitive.
 * @return Existing protocol status; unmet initialization precondition is BUSY.
 * @note No retry, reset or recovery is hidden in error conversion.
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
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_STATE_ERROR:
        case ET_WRAP_STATUS_BUSY:
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
 * @brief Decode one little-endian word without aligned pointer casts.
 * @param[in] data Four validated request bytes.
 * @return Unsigned decoded field.
 * @note Pure codec, called after exact body length validation.
 */
static uint32_t read_word(const uint8_t *data)
{
    uint32_t value = 0u;
    uint16_t index;

    for (index = 0u; index < ET_CAN_WIRE_WORD_BYTES; ++index)
    {
        value |= (uint32_t)data[index] << (index * CHAR_BIT);
    }

    return value;
}

/**
 * @brief Encode one little-endian word without depending on host structure layout.
 * @param[out] data Four validated response bytes.
 * @param[in] value Actual field value.
 * @note Does not access hardware or interpret register meanings.
 */
static void write_word(uint8_t *data, uint32_t value)
{
    uint16_t index;

    for (index = 0u; index < ET_CAN_WIRE_WORD_BYTES; ++index)
    {
        data[index] = (uint8_t)(value >> (index * CHAR_BIT));
    }
}

/********************************** IRQ Capture Management **********************************/

/**
 * @brief Saturate one callback-owned counter and preserve overflow evidence.
 * @param[in,out] service CAN Service that owns the fixed event snapshot.
 * @param[in,out] counter Counter to increment.
 * @note Called only from IRQ context or an IRQ Manager critical section.
 */
static void increment_irq_counter(et_can_service_t *service, volatile uint32_t *counter)
{
    if (*counter != UINT32_MAX)
    {
        ++*counter;

        return;
    }

    service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_OVERFLOW;

    if (service->irq_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT] != UINT32_MAX)
    {
        ++service->irq_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT];
    }
}

/**
 * @brief Copy or reset fixed CAN IRQ evidence under one short critical section.
 * @param[in,out] service CAN Service evidence owner.
 * @param[in] reset Nonzero starts a new empty generation while no route is bound.
 * @param[out] words Eight output words for a read; unused for reset.
 * @return OK, BUSY, INVALID_ARGUMENT or IO_ERROR.
 * @note Reset changes Service storage only; CAN pending state is cleared by a separate command.
 */
static et_wrap_status_t irq_event_access(et_can_service_t *service, uint8_t reset, uint32_t *words)
{
    uint32_t key;
    uint16_t index;

    if ((service == NULL) || ((reset == 0u) && (words == NULL)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((reset != 0u) && (service->bound_lines != 0u))
    {
        return ET_WRAP_STATUS_BUSY;
    }

    key = et_irq_manager_enter_critical();

    if (reset != 0u)
    {
        if (service->irq_event[ET_CAN_IRQ_EVENT_GENERATION] == UINT32_MAX)
        {
            et_irq_manager_exit_critical(key);

            return ET_WRAP_STATUS_IO_ERROR;
        }

        ++service->irq_event[ET_CAN_IRQ_EVENT_GENERATION];

        for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
        {
            if (index != ET_CAN_IRQ_EVENT_GENERATION)
            {
                service->irq_event[index] = 0u;
            }
        }
    }
    else
    {
        for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
        {
            words[index] = service->irq_event[index];
        }
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Capture one bounded CAN interrupt observation and suppress active sources.
 * @param[in,out] context CAN Service registered with IRQ Manager.
 * @param[in] irq_line Physical line delivered by IRQ Manager.
 * @param[in] route_events Public source subset assigned to this route.
 * @note ISR work is fixed: one snapshot, fixed counters and one source-mask operation.
 */
static void can_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_can_service_t *service = (et_can_service_t *)context;
    et_can_irq_snapshot_t snapshot;
    uint32_t active;

    if ((service == NULL) || (service->bound_lines == 0u))
    {
        return;
    }

    if (et_can_wrap_get_irq_snapshot(service->can_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
        (void)et_can_wrap_set_irq_enabled(service->can_id, service->watched_sources, 0u);

        return;
    }

    active =
        snapshot.raw_status & snapshot.enabled_sources & route_events & service->watched_sources;

    if (active == 0u)
    {
        return;
    }

    /* Preserve the first raw/masked view and accumulate every observed semantic source. */
    if (service->irq_event[ET_CAN_IRQ_EVENT_COUNT] == 0u)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_RAW_STATUS] = snapshot.raw_status;
        service->irq_event[ET_CAN_IRQ_EVENT_MASKED_STATUS] = active;
    }

    service->irq_event[ET_CAN_IRQ_EVENT_LATCHED_EVENTS] |= active;
    increment_irq_counter(service, &service->irq_event[ET_CAN_IRQ_EVENT_COUNT]);

    if (((irq_line != service->irq_routes[ET_CAN_IRQ_LINE0].irq_line) &&
         (irq_line != service->irq_routes[ET_CAN_IRQ_LINE1].irq_line)) ||
        ((active & ~route_events) != 0u))
    {
        increment_irq_counter(service, &service->irq_event[ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT]);
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_UNEXPECTED;
    }

    /* A pending level remains visible for explicit PC clear, while masking prevents an IRQ storm. */
    if (et_can_wrap_set_irq_enabled(service->can_id, active, 0u) != ET_WRAP_STATUS_OK)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
    }
}

/**
 * @brief Stop a managed CAN IRQ capture in source-before-route order.
 * @param[in,out] service CAN Service that owns the active session.
 * @return OK or the first cleanup failure.
 * @note Evidence is retained. Ownership is cleared only after both physical routes are released.
 */
static et_wrap_status_t stop_irq_capture(et_can_service_t *service)
{
    et_wrap_status_t result = ET_WRAP_STATUS_OK;
    et_can_irq_line_t line;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (et_can_wrap_set_irq_enabled(service->can_id, service->watched_sources, 0u) !=
        ET_WRAP_STATUS_OK)
    {
        result = ET_WRAP_STATUS_IO_ERROR;
    }

    for (line = ET_CAN_IRQ_LINE0; line < ET_CAN_IRQ_LINE_COUNT; ++line)
    {
        uint8_t line_bit = (uint8_t)(1u << line);

        if ((service->bound_lines & line_bit) == 0u)
        {
            continue;
        }

        if (et_can_wrap_set_irq_line_enabled(service->can_id, line, 0u) != ET_WRAP_STATUS_OK)
        {
            result = ET_WRAP_STATUS_IO_ERROR;
        }

        if (et_irq_manager_unbind(service->irq_manager, service->irq_routes[line].irq_line,
                                  can_irq_callback, service) != 0)
        {
            service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
            result = ET_WRAP_STATUS_IO_ERROR;
        }
        else
        {
            service->bound_lines &= (uint8_t)~line_bit;
        }
    }

    if (service->bound_lines == 0u)
    {
        service->watched_sources = 0u;
        service->line1_sources = 0u;
    }

    return result;
}

/**
 * @brief Start one explicit CAN interrupt capture using up to two routed lines.
 * @param[in,out] service CAN Service that owns the session.
 * @param[in] sources Nonzero public source mask.
 * @param[in] line1_sources Subset of sources routed to controller line 1.
 * @return OK or the exact setup/rollback failure.
 * @note Setup order is clear, select, bind, line-enable, source-enable; rollback is reversed.
 */
static et_wrap_status_t start_irq_capture(et_can_service_t *service, uint32_t sources,
                                          uint32_t line1_sources)
{
    uint32_t route_events[ET_CAN_IRQ_LINE_COUNT];
    et_can_irq_line_t line;
    et_wrap_status_t status;

    if ((service == NULL) || (sources == 0u) || ((sources & ~ET_CAN_IRQ_ALL) != 0u) ||
        ((line1_sources & ~sources) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (service->bound_lines != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    /* Phase 1: Validate software ownership and start a new empty evidence generation. */
    status = irq_event_access(service, 1u, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    route_events[ET_CAN_IRQ_LINE0] = sources & ~line1_sources;
    route_events[ET_CAN_IRQ_LINE1] = line1_sources;
    service->watched_sources = sources;
    service->line1_sources = line1_sources;

    /* Phase 2: Clear stale state and publish the complete line selection before any route can fire. */
    status = et_can_wrap_set_irq_enabled(service->can_id, sources, 0u);

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_clear_irq(service->can_id, sources);
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_select_irq_line(service->can_id, sources, ET_CAN_IRQ_LINE0);
    }

    if ((status == ET_WRAP_STATUS_OK) && (line1_sources != 0u))
    {
        status = et_can_wrap_select_irq_line(service->can_id, line1_sources, ET_CAN_IRQ_LINE1);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        service->watched_sources = 0u;
        service->line1_sources = 0u;

        return status;
    }

    /* Phase 3: Bind and enable only lines that own at least one requested semantic source. */
    for (line = ET_CAN_IRQ_LINE0; line < ET_CAN_IRQ_LINE_COUNT; ++line)
    {
        uint8_t line_bit = (uint8_t)(1u << line);

        if (route_events[line] == 0u)
        {
            continue;
        }

        status = et_can_wrap_get_irq_route(service->can_id, line, route_events[line],
                                           &service->irq_routes[line]);

        if ((status != ET_WRAP_STATUS_OK) ||
            (et_irq_manager_bind(service->irq_manager, &service->irq_routes[line],
                                 service->irq_priority, can_irq_callback, service) != 0))
        {
            (void)stop_irq_capture(service);

            return status == ET_WRAP_STATUS_OK ? ET_WRAP_STATUS_IO_ERROR : status;
        }

        service->bound_lines |= line_bit;
        status = et_can_wrap_set_irq_line_enabled(service->can_id, line, 1u);

        if (status != ET_WRAP_STATUS_OK)
        {
            (void)stop_irq_capture(service);

            return status;
        }
    }

    /* Phase 4: Expose peripheral sources only after every required route is operational. */
    status = et_can_wrap_set_irq_enabled(service->can_id, sources, 1u);

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)stop_irq_capture(service);
    }

    return status;
}

/**
 * @brief Execute CAN interrupt configuration, observation and managed-capture commands.
 * @param[in,out] service CAN Service selected by the request prefix.
 * @param[in] command Validated IRQ command.
 * @param[in] body Validated request words after the instance prefix.
 * @param[out] response Capacity-checked response storage when required.
 * @return Own Wrap or IRQ-session result.
 * @note No test stimulus, polling or PASS/FAIL decision is hidden here.
 */
static et_wrap_status_t execute_irq_command(et_can_service_t *service, uint16_t command,
                                            const uint8_t *body, uint8_t *response)
{
    et_can_irq_snapshot_t snapshot;
    et_wrap_status_t status;
    uint32_t words[ET_CAN_IRQ_EVENT_WORDS];
    uint32_t sources;
    uint32_t value;
    uint16_t index;

    /* Phase 1: Route direct source/line controls while no managed capture owns them. */
    switch (command)
    {
        case ET_CAN_COMMAND_IRQ_MASK_SET:
        {
            sources = read_word(body);
            value = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (value > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            if (service->bound_lines != 0u)
            {
                return ET_WRAP_STATUS_BUSY;
            }

            return et_can_wrap_set_irq_enabled(service->can_id, sources, (uint8_t)value);
        }

        case ET_CAN_COMMAND_IRQ_LINE_SELECT_SET:
        {
            sources = read_word(body);
            value = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (value >= ET_CAN_IRQ_LINE_COUNT)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            if (service->bound_lines != 0u)
            {
                return ET_WRAP_STATUS_BUSY;
            }

            return et_can_wrap_select_irq_line(service->can_id, sources, (et_can_irq_line_t)value);
        }

        case ET_CAN_COMMAND_IRQ_SNAPSHOT_GET:
        {
            /* Phase 2: Return a non-destructive hardware view independent of callback evidence. */
            status = et_can_wrap_get_irq_snapshot(service->can_id, &snapshot);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_RAW * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.raw_status);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.enabled_sources);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_LINE1 * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.line1_sources);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_LINES_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.enabled_lines);
            }

            return status;
        }

        case ET_CAN_COMMAND_IRQ_CLEAR:
        {
            return et_can_wrap_clear_irq(service->can_id, read_word(body));
        }

        case ET_CAN_COMMAND_IRQ_CAPTURE_START:
        {
            return start_irq_capture(service, read_word(body),
                                     read_word(&body[ET_CAN_WIRE_WORD_BYTES]));
        }

        case ET_CAN_COMMAND_IRQ_CAPTURE_STOP:
        {
            return stop_irq_capture(service);
        }

        case ET_CAN_COMMAND_IRQ_EVENT_GET:
        {
            /* Phase 3: Copy only fixed Service evidence under its IRQ critical section. */
            status = irq_event_access(service, 0u, words);

            if (status == ET_WRAP_STATUS_OK)
            {
                for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
                {
                    write_word(&response[index * ET_CAN_WIRE_WORD_BYTES], words[index]);
                }
            }

            return status;
        }

        case ET_CAN_COMMAND_IRQ_EVENT_RESET:
        {
            return irq_event_access(service, 1u, NULL);
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Decode the four named physical timing counts of one CAN phase.
 * @param[in] body Validated phase payload.
 * @param[out] phase Public configuration, with no chip encodings.
 * @note Only copies PC parameters; it does not select a bitrate or defaults.
 */
static void decode_phase(const uint8_t *body, et_can_bit_timing_t *phase)
{
    phase->prescaler = read_word(&body[ET_CAN_TIMING_PRESCALER * ET_CAN_WIRE_WORD_BYTES]);
    phase->segment1 = read_word(&body[ET_CAN_TIMING_SEGMENT1 * ET_CAN_WIRE_WORD_BYTES]);
    phase->segment2 = read_word(&body[ET_CAN_TIMING_SEGMENT2 * ET_CAN_WIRE_WORD_BYTES]);
    phase->sjw = read_word(&body[ET_CAN_TIMING_SJW * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode one timing phase in the public field order.
 * @param[out] body Validated phase response storage.
 * @param[in] phase Actual readback or declared representable maxima.
 * @note No hidden unit conversion occurs in the Service.
 */
static void encode_phase(uint8_t *body, const et_can_bit_timing_t *phase)
{
    write_word(&body[ET_CAN_TIMING_PRESCALER * ET_CAN_WIRE_WORD_BYTES], phase->prescaler);
    write_word(&body[ET_CAN_TIMING_SEGMENT1 * ET_CAN_WIRE_WORD_BYTES], phase->segment1);
    write_word(&body[ET_CAN_TIMING_SEGMENT2 * ET_CAN_WIRE_WORD_BYTES], phase->segment2);
    write_word(&body[ET_CAN_TIMING_SJW * ET_CAN_WIRE_WORD_BYTES], phase->sjw);
}

/**
 * @brief Decode the complete public core option tuple.
 * @param[in] body Validated option bytes.
 * @param[out] options Caller-owned chip-neutral values.
 * @note No defaults or hardware changes occur in this codec.
 */
static void decode_options(const uint8_t *body, et_can_options_t *options)
{
    options->fd_enabled = read_word(&body[ET_CAN_OPTION_FD * ET_CAN_WIRE_WORD_BYTES]);
    options->brs_enabled = read_word(&body[ET_CAN_OPTION_BRS * ET_CAN_WIRE_WORD_BYTES]);
    options->automatic_retry = read_word(&body[ET_CAN_OPTION_RETRY * ET_CAN_WIRE_WORD_BYTES]);
    options->tx_pause = read_word(&body[ET_CAN_OPTION_TX_PAUSE * ET_CAN_WIRE_WORD_BYTES]);
    options->edge_filter = read_word(&body[ET_CAN_OPTION_EDGE_FILTER * ET_CAN_WIRE_WORD_BYTES]);
    options->protocol_exception =
        read_word(&body[ET_CAN_OPTION_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_enabled = read_word(&body[ET_CAN_OPTION_TDC * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_offset_cycles =
        read_word(&body[ET_CAN_OPTION_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_filter_cycles =
        read_word(&body[ET_CAN_OPTION_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES]);
    options->ram_watchdog_cycles =
        read_word(&body[ET_CAN_OPTION_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode independently observed core options.
 * @param[out] body Validated output storage.
 * @param[in] options Actual hardware readback.
 * @note Pure serialization; bit interpretation belongs to the Driver and Wrap.
 */
static void encode_options(uint8_t *body, const et_can_options_t *options)
{
    write_word(&body[ET_CAN_OPTION_FD * ET_CAN_WIRE_WORD_BYTES], options->fd_enabled);
    write_word(&body[ET_CAN_OPTION_BRS * ET_CAN_WIRE_WORD_BYTES], options->brs_enabled);
    write_word(&body[ET_CAN_OPTION_RETRY * ET_CAN_WIRE_WORD_BYTES], options->automatic_retry);
    write_word(&body[ET_CAN_OPTION_TX_PAUSE * ET_CAN_WIRE_WORD_BYTES], options->tx_pause);
    write_word(&body[ET_CAN_OPTION_EDGE_FILTER * ET_CAN_WIRE_WORD_BYTES], options->edge_filter);
    write_word(&body[ET_CAN_OPTION_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES],
               options->protocol_exception);
    write_word(&body[ET_CAN_OPTION_TDC * ET_CAN_WIRE_WORD_BYTES], options->tdc_enabled);
    write_word(&body[ET_CAN_OPTION_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES],
               options->tdc_offset_cycles);
    write_word(&body[ET_CAN_OPTION_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES],
               options->tdc_filter_cycles);
    write_word(&body[ET_CAN_OPTION_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES],
               options->ram_watchdog_cycles);
}

/**
 * @brief Decode the complete public Message RAM tuple.
 * @param[in] body Validated RAM request bytes.
 * @param[out] layout Explicit region parameters owned by the caller.
 * @note No defaults, allocation or hardware access occur here.
 */
static void decode_ram_layout(const uint8_t *body, et_can_ram_layout_t *layout)
{
    layout->std_offset = read_word(&body[ET_CAN_RAM_STD_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->std_count = read_word(&body[ET_CAN_RAM_STD_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->ext_offset = read_word(&body[ET_CAN_RAM_EXT_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->ext_count = read_word(&body[ET_CAN_RAM_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_offset = read_word(&body[ET_CAN_RAM_TX_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_buffer_count = read_word(&body[ET_CAN_RAM_TX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_fifo_count = read_word(&body[ET_CAN_RAM_TX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_queue = read_word(&body[ET_CAN_RAM_TX_QUEUE * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_payload_bytes =
        read_word(&body[ET_CAN_RAM_TX_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_offset = read_word(&body[ET_CAN_RAM_EVENT_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_count = read_word(&body[ET_CAN_RAM_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_watermark = read_word(&body[ET_CAN_RAM_EVENT_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_offset = read_word(&body[ET_CAN_RAM_RX0_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_count = read_word(&body[ET_CAN_RAM_RX0_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_watermark = read_word(&body[ET_CAN_RAM_RX0_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_overwrite = read_word(&body[ET_CAN_RAM_RX0_OVERWRITE * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_offset = read_word(&body[ET_CAN_RAM_RX1_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_count = read_word(&body[ET_CAN_RAM_RX1_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_watermark = read_word(&body[ET_CAN_RAM_RX1_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_overwrite = read_word(&body[ET_CAN_RAM_RX1_OVERWRITE * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx_buffer_offset =
        read_word(&body[ET_CAN_RAM_RX_BUFFER_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx_buffer_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX_BUFFER_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX0_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX1_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode actual RAM configuration in the declared word order.
 * @param[out] body Validated response storage.
 * @param[in] layout Independent hardware configuration readback.
 * @note Does not present configuration requests as observed values.
 */
static void encode_ram_layout(uint8_t *body, const et_can_ram_layout_t *layout)
{
    write_word(&body[ET_CAN_RAM_STD_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->std_offset);
    write_word(&body[ET_CAN_RAM_STD_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->std_count);
    write_word(&body[ET_CAN_RAM_EXT_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->ext_offset);
    write_word(&body[ET_CAN_RAM_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->ext_count);
    write_word(&body[ET_CAN_RAM_TX_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->tx_offset);
    write_word(&body[ET_CAN_RAM_TX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->tx_buffer_count);
    write_word(&body[ET_CAN_RAM_TX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->tx_fifo_count);
    write_word(&body[ET_CAN_RAM_TX_QUEUE * ET_CAN_WIRE_WORD_BYTES], layout->tx_queue);
    write_word(&body[ET_CAN_RAM_TX_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->tx_payload_bytes);
    write_word(&body[ET_CAN_RAM_EVENT_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->event_offset);
    write_word(&body[ET_CAN_RAM_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->event_count);
    write_word(&body[ET_CAN_RAM_EVENT_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->event_watermark);
    write_word(&body[ET_CAN_RAM_RX0_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->rx0_offset);
    write_word(&body[ET_CAN_RAM_RX0_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->rx0_count);
    write_word(&body[ET_CAN_RAM_RX0_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->rx0_watermark);
    write_word(&body[ET_CAN_RAM_RX0_OVERWRITE * ET_CAN_WIRE_WORD_BYTES], layout->rx0_overwrite);
    write_word(&body[ET_CAN_RAM_RX1_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->rx1_offset);
    write_word(&body[ET_CAN_RAM_RX1_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->rx1_count);
    write_word(&body[ET_CAN_RAM_RX1_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->rx1_watermark);
    write_word(&body[ET_CAN_RAM_RX1_OVERWRITE * ET_CAN_WIRE_WORD_BYTES], layout->rx1_overwrite);
    write_word(&body[ET_CAN_RAM_RX_BUFFER_OFFSET * ET_CAN_WIRE_WORD_BYTES],
               layout->rx_buffer_offset);
    write_word(&body[ET_CAN_RAM_RX_BUFFER_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx_buffer_payload_bytes);
    write_word(&body[ET_CAN_RAM_RX0_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx0_payload_bytes);
    write_word(&body[ET_CAN_RAM_RX1_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx1_payload_bytes);
}

/**
 * @brief Handle the three RAM commands without test sequencing.
 * @param[in] id Logical controller identity.
 * @param[in] command Validated RAM command identifier.
 * @param[in] body Validated request following the instance prefix.
 * @param[out] response Output storage, nullable for SET.
 * @return Own Wrap status.
 * @note Only calls the CAN Wrap; no resource or GPIO calls.
 */
static et_wrap_status_t execute_ram_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_can_ram_layout_t layout;
    et_can_ram_limits_t limits;
    et_wrap_status_t status;

    if (command == ET_CAN_COMMAND_RAM_LAYOUT_SET)
    {
        decode_ram_layout(body, &layout);

        return et_can_wrap_set_ram_layout(id, &layout);
    }

    if (command == ET_CAN_COMMAND_RAM_LAYOUT_GET)
    {
        status = et_can_wrap_get_ram_layout(id, &layout);

        if (status == ET_WRAP_STATUS_OK)
        {
            encode_ram_layout(response, &layout);
        }

        return status;
    }

    status = et_can_wrap_get_ram_limits(id, &limits);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_RAM_LIMIT_RAM_BYTES * ET_CAN_WIRE_WORD_BYTES],
                   limits.ram_bytes);
        write_word(&response[ET_CAN_RAM_LIMIT_STD_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.std_count);
        write_word(&response[ET_CAN_RAM_LIMIT_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.ext_count);
        write_word(&response[ET_CAN_RAM_LIMIT_TX_COUNT * ET_CAN_WIRE_WORD_BYTES], limits.tx_count);
        write_word(&response[ET_CAN_RAM_LIMIT_RX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.rx_fifo_count);
        write_word(&response[ET_CAN_RAM_LIMIT_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.event_count);
        write_word(&response[ET_CAN_RAM_LIMIT_RX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.rx_buffer_count);
    }

    return status;
}

/**
 * @brief Decode the complete existing Driver bus configuration group.
 * @param[in] body Validated words after the instance prefix.
 * @param[out] config Explicit public parameters, without defaults.
 * @note Pure codec; no other IP or test orchestration.
 */
static void decode_bus_config(const uint8_t *body, et_can_bus_config_t *config)
{
    config->monitor = read_word(&body[ET_CAN_BUS_MONITOR * ET_CAN_WIRE_WORD_BYTES]);
    config->restricted = read_word(&body[ET_CAN_BUS_RESTRICTED * ET_CAN_WIRE_WORD_BYTES]);
    config->timestamp_divisor =
        read_word(&body[ET_CAN_BUS_TIMESTAMP_DIVISOR * ET_CAN_WIRE_WORD_BYTES]);
    config->timestamp_source =
        read_word(&body[ET_CAN_BUS_TIMESTAMP_SOURCE * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_source = read_word(&body[ET_CAN_BUS_TIMEOUT_SOURCE * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_period = read_word(&body[ET_CAN_BUS_TIMEOUT_PERIOD * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_enabled = read_word(&body[ET_CAN_BUS_TIMEOUT_ENABLED * ET_CAN_WIRE_WORD_BYTES]);
    config->reject_remote_ext =
        read_word(&body[ET_CAN_BUS_REJECT_REMOTE_EXT * ET_CAN_WIRE_WORD_BYTES]);
    config->reject_remote_std =
        read_word(&body[ET_CAN_BUS_REJECT_REMOTE_STD * ET_CAN_WIRE_WORD_BYTES]);
    config->unmatched_ext = read_word(&body[ET_CAN_BUS_UNMATCHED_EXT * ET_CAN_WIRE_WORD_BYTES]);
    config->unmatched_std = read_word(&body[ET_CAN_BUS_UNMATCHED_STD * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode independently read bus configuration.
 * @param[out] body Validated output storage.
 * @param[in] config Actual Wrap readback.
 * @note Does not synthesize observations from requests.
 */
static void encode_bus_config(uint8_t *body, const et_can_bus_config_t *config)
{
    write_word(&body[ET_CAN_BUS_MONITOR * ET_CAN_WIRE_WORD_BYTES], config->monitor);
    write_word(&body[ET_CAN_BUS_RESTRICTED * ET_CAN_WIRE_WORD_BYTES], config->restricted);
    write_word(&body[ET_CAN_BUS_TIMESTAMP_DIVISOR * ET_CAN_WIRE_WORD_BYTES],
               config->timestamp_divisor);
    write_word(&body[ET_CAN_BUS_TIMESTAMP_SOURCE * ET_CAN_WIRE_WORD_BYTES],
               config->timestamp_source);
    write_word(&body[ET_CAN_BUS_TIMEOUT_SOURCE * ET_CAN_WIRE_WORD_BYTES], config->timeout_source);
    write_word(&body[ET_CAN_BUS_TIMEOUT_PERIOD * ET_CAN_WIRE_WORD_BYTES], config->timeout_period);
    write_word(&body[ET_CAN_BUS_TIMEOUT_ENABLED * ET_CAN_WIRE_WORD_BYTES], config->timeout_enabled);
    write_word(&body[ET_CAN_BUS_REJECT_REMOTE_EXT * ET_CAN_WIRE_WORD_BYTES],
               config->reject_remote_ext);
    write_word(&body[ET_CAN_BUS_REJECT_REMOTE_STD * ET_CAN_WIRE_WORD_BYTES],
               config->reject_remote_std);
    write_word(&body[ET_CAN_BUS_UNMATCHED_EXT * ET_CAN_WIRE_WORD_BYTES], config->unmatched_ext);
    write_word(&body[ET_CAN_BUS_UNMATCHED_STD * ET_CAN_WIRE_WORD_BYTES], config->unmatched_std);
}

/**
 * @brief Execute bus configuration and loopback primitives only.
 * @param[in] id Logical controller.
 * @param[in] command Validated command in the bus action group.
 * @param[in] body Validated input following the instance prefix.
 * @param[out] response Validated output, nullable for SET.
 * @return Own Wrap result.
 * @note No polling, defaults, cross-IP initialization or Case verdicts.
 */
static et_wrap_status_t execute_bus_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_can_bus_config_t config;
    et_can_bus_limits_t limits;
    et_can_loopback_t mode;
    et_wrap_status_t status;
    uint32_t requested;

    switch (command)
    {
        case ET_CAN_COMMAND_BUS_CONFIG_SET:
        {
            decode_bus_config(body, &config);

            return et_can_wrap_set_bus_config(id, &config);
        }

        case ET_CAN_COMMAND_BUS_CONFIG_GET:
        {
            status = et_can_wrap_get_bus_config(id, &config);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_bus_config(response, &config);
            }

            return status;
        }

        case ET_CAN_COMMAND_LOOPBACK_SET:
        {
            requested = read_word(body);

            if (requested > ET_CAN_LOOPBACK_EXTERNAL)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_set_loopback(id, (et_can_loopback_t)requested);
        }

        case ET_CAN_COMMAND_LOOPBACK_GET:
        {
            status = et_can_wrap_get_loopback(id, &mode);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, (uint32_t)mode);
            }

            return status;
        }

        default:
        {
            status = et_can_wrap_get_bus_limits(id, &limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_BUS_LIMIT_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                           limits.timestamp_divisor);
                write_word(&response[ET_CAN_BUS_LIMIT_TIMEOUT * ET_CAN_WIRE_WORD_BYTES],
                           limits.timeout_period);
            }

            return status;
        }
    }
}

/**
 * @brief Decode one fixed-size TX element after full envelope validation.
 * @param[in] body Validated index, header and payload bytes.
 * @param[out] frame Public frame; payload is copied byte-for-byte.
 * @note Does not populate RAM or issue a transmit request.
 */
static void decode_tx_frame(const uint8_t *body, et_can_tx_frame_t *frame)
{
    frame->identifier = read_word(&body[ET_CAN_TX_FIELD_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES]);
    frame->flags = read_word(&body[ET_CAN_TX_FIELD_FLAGS * ET_CAN_WIRE_WORD_BYTES]);
    frame->dlc = read_word(&body[ET_CAN_TX_FIELD_DLC * ET_CAN_WIRE_WORD_BYTES]);
    frame->marker = read_word(&body[ET_CAN_TX_FIELD_MARKER * ET_CAN_WIRE_WORD_BYTES]);
    (void)memcpy(frame->data, &body[ET_CAN_TX_FIELD_DATA * ET_CAN_WIRE_WORD_BYTES],
                 ET_CAN_FRAME_DATA_BYTES);
}

/**
 * @brief Encode the observed RX header and fixed-capacity byte envelope.
 * @param[out] body Validated response storage.
 * @param[in] frame Actual frame; data_length marks the valid stored bytes.
 * @note Does not acknowledge the element or compare it with expected data.
 */
static void encode_rx_frame(uint8_t *body, const et_can_rx_frame_t *frame)
{
    write_word(&body[ET_CAN_RX_FIELD_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES], frame->identifier);
    write_word(&body[ET_CAN_RX_FIELD_FLAGS * ET_CAN_WIRE_WORD_BYTES], frame->flags);
    write_word(&body[ET_CAN_RX_FIELD_DLC * ET_CAN_WIRE_WORD_BYTES], frame->dlc);
    write_word(&body[ET_CAN_RX_FIELD_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES], frame->timestamp);
    write_word(&body[ET_CAN_RX_FIELD_FILTER_INDEX * ET_CAN_WIRE_WORD_BYTES], frame->filter_index);
    write_word(&body[ET_CAN_RX_FIELD_NONMATCHING * ET_CAN_WIRE_WORD_BYTES], frame->nonmatching);
    write_word(&body[ET_CAN_RX_FIELD_DATA_LENGTH * ET_CAN_WIRE_WORD_BYTES], frame->data_length);
    write_word(&body[ET_CAN_RX_FIELD_INDEX * ET_CAN_WIRE_WORD_BYTES], frame->index);
    (void)memcpy(&body[ET_CAN_RX_FIELD_DATA * ET_CAN_WIRE_WORD_BYTES], frame->data,
                 ET_CAN_FRAME_DATA_BYTES);
}

/**
 * @brief Execute one TX preparation, request or status query.
 * @param[in] id Logical controller.
 * @param[in] command One validated TX command.
 * @param[in] body Validated request after the instance prefix.
 * @param[out] response Storage required only by status queries.
 * @return Own Wrap status.
 * @note Preparing a frame never implies starting or waiting for transmission.
 */
static et_wrap_status_t execute_tx_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                           uint8_t *response)
{
    et_can_tx_frame_t frame;
    et_can_tx_status_t status;
    et_wrap_status_t result;

    if (command == ET_CAN_COMMAND_TX_WRITE)
    {
        decode_tx_frame(body, &frame);

        return et_can_wrap_write_tx(
            id, read_word(&body[ET_CAN_TX_FIELD_INDEX * ET_CAN_WIRE_WORD_BYTES]), &frame);
    }

    if (command == ET_CAN_COMMAND_TX_REQUEST)
    {
        return et_can_wrap_request_tx(id, read_word(body));
    }

    result = et_can_wrap_get_tx_status(id, &status);

    if (result == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_TX_STATUS_PENDING * ET_CAN_WIRE_WORD_BYTES], status.pending);
        write_word(&response[ET_CAN_TX_STATUS_COMPLETED * ET_CAN_WIRE_WORD_BYTES],
                   status.completed);
        write_word(&response[ET_CAN_TX_STATUS_CANCELLED * ET_CAN_WIRE_WORD_BYTES],
                   status.cancelled);
        write_word(&response[ET_CAN_TX_STATUS_FREE_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   status.free_count);
        write_word(&response[ET_CAN_TX_STATUS_GET_INDEX * ET_CAN_WIRE_WORD_BYTES],
                   status.get_index);
        write_word(&response[ET_CAN_TX_STATUS_PUT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                   status.put_index);
        write_word(&response[ET_CAN_TX_STATUS_FULL * ET_CAN_WIRE_WORD_BYTES], status.full);
    }

    return result;
}

/**
 * @brief Execute a receive FIFO, buffer or frame primitive.
 * @param[in] id Logical controller.
 * @param[in] command Validated receive-group command.
 * @param[in] body Validated source/index or bitmap fields.
 * @param[out] response Validated output storage when the command returns facts.
 * @return Own Wrap status.
 * @note Reads and acknowledgements remain separate commands; no draining loops or verdicts.
 */
static et_wrap_status_t execute_rx_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                           uint8_t *response)
{
    et_can_rx_frame_t frame;
    et_can_rx_fifo_status_t fifo;
    et_can_rx_buffer_status_t buffers;
    et_wrap_status_t result;
    uint32_t source;

    switch (command)
    {
        case ET_CAN_COMMAND_RX_READ:
        {
            /* Step 1: Decode one explicit storage selector and return the observed element. */
            source = read_word(&body[ET_CAN_RX_SELECT_SOURCE * ET_CAN_WIRE_WORD_BYTES]);

            if (source > ET_CAN_RX_FIFO1)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            result = et_can_wrap_read_rx(
                id, (et_can_rx_source_t)source,
                read_word(&body[ET_CAN_RX_SELECT_INDEX * ET_CAN_WIRE_WORD_BYTES]), &frame);

            if (result == ET_WRAP_STATUS_OK)
            {
                encode_rx_frame(response, &frame);
            }

            return result;
        }

        case ET_CAN_COMMAND_RX_FIFO_ACK:
        {
            /* Step 2: Acknowledgement is a separate caller-requested write, never a read side effect. */
            return et_can_wrap_ack_rx_fifo(
                id, read_word(&body[ET_CAN_RX_SELECT_SOURCE * ET_CAN_WIRE_WORD_BYTES]),
                read_word(&body[ET_CAN_RX_SELECT_INDEX * ET_CAN_WIRE_WORD_BYTES]));
        }

        case ET_CAN_COMMAND_RX_BUFFER_ACK:
        {
            buffers.low = read_word(&body[ET_CAN_RX_BITMAP_LOW * ET_CAN_WIRE_WORD_BYTES]);
            buffers.high = read_word(&body[ET_CAN_RX_BITMAP_HIGH * ET_CAN_WIRE_WORD_BYTES]);

            return et_can_wrap_ack_rx_buffers(id, &buffers);
        }

        case ET_CAN_COMMAND_RX_BUFFER_STATUS_GET:
        {
            result = et_can_wrap_get_rx_buffer_status(id, &buffers);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_RX_BITMAP_LOW * ET_CAN_WIRE_WORD_BYTES], buffers.low);
                write_word(&response[ET_CAN_RX_BITMAP_HIGH * ET_CAN_WIRE_WORD_BYTES], buffers.high);
            }

            return result;
        }

        default:
        {
            result = et_can_wrap_get_rx_fifo_status(id, read_word(body), &fifo);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_RX_FIFO_FILL * ET_CAN_WIRE_WORD_BYTES], fifo.fill);
                write_word(&response[ET_CAN_RX_FIFO_GET_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           fifo.get_index);
                write_word(&response[ET_CAN_RX_FIFO_PUT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           fifo.put_index);
                write_word(&response[ET_CAN_RX_FIFO_FULL * ET_CAN_WIRE_WORD_BYTES], fifo.full);
                write_word(&response[ET_CAN_RX_FIFO_LOST * ET_CAN_WIRE_WORD_BYTES], fifo.lost);
            }

            return result;
        }
    }
}

/**
 * @brief Decode one filter action and encode only independently read values.
 * @param[in] id Logical CAN controller.
 * @param[in] command Validated filter-group command.
 * @param[in] body Validated request words after instance prefix.
 * @param[out] response Validated response storage, nullable for writes.
 * @return Own Wrap result without assigning any Case verdict.
 * @note No filter defaults, iteration across lists, or other IP operations.
 */
static et_wrap_status_t execute_filter_command(et_can_id_t id, uint16_t command,
                                               const uint8_t *body, uint8_t *response)
{
    et_can_filter_t filter;
    et_can_high_priority_status_t high_priority;
    et_wrap_status_t status;
    uint32_t mask;
    const uint8_t *config;

    if (command == ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET)
    {
        status = et_can_wrap_get_high_priority_status(id, &high_priority);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_HIGH_PRIORITY_BUFFER_INDEX * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.buffer_index);
            write_word(&response[ET_CAN_HIGH_PRIORITY_STORAGE * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.storage);
            write_word(&response[ET_CAN_HIGH_PRIORITY_FILTER_INDEX * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.filter_index);
            write_word(&response[ET_CAN_HIGH_PRIORITY_EXTENDED_FILTER * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.extended_filter);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_EXTENDED_MASK_SET)
    {
        return et_can_wrap_set_extended_mask(id, read_word(body));
    }

    if (command == ET_CAN_COMMAND_EXTENDED_MASK_GET)
    {
        status = et_can_wrap_get_extended_mask(id, &mask);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(response, mask);
        }

        return status;
    }

    /* Phase 1: Decode an explicit SET tuple; no hardware-encoded Buffer bitfields. */
    if (command == ET_CAN_COMMAND_FILTER_SET)
    {
        config = &body[ET_CAN_FILTER_SELECT_WORDS * ET_CAN_WIRE_WORD_BYTES];
        filter.type = read_word(&config[ET_CAN_FILTER_FIELD_TYPE * ET_CAN_WIRE_WORD_BYTES]);
        filter.action = read_word(&config[ET_CAN_FILTER_FIELD_ACTION * ET_CAN_WIRE_WORD_BYTES]);
        filter.id1 = read_word(&config[ET_CAN_FILTER_FIELD_ID1 * ET_CAN_WIRE_WORD_BYTES]);
        filter.id2 = read_word(&config[ET_CAN_FILTER_FIELD_ID2 * ET_CAN_WIRE_WORD_BYTES]);
        filter.buffer_index =
            read_word(&config[ET_CAN_FILTER_FIELD_BUFFER * ET_CAN_WIRE_WORD_BYTES]);

        return et_can_wrap_set_filter(id, read_word(body), read_word(&body[ET_CAN_WIRE_WORD_BYTES]),
                                      &filter);
    }

    /* Phase 2: Serialize only successful actual RAM readback, never the request. */
    status = et_can_wrap_get_filter(id, read_word(body), read_word(&body[ET_CAN_WIRE_WORD_BYTES]),
                                    &filter);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_FILTER_FIELD_TYPE * ET_CAN_WIRE_WORD_BYTES], filter.type);
        write_word(&response[ET_CAN_FILTER_FIELD_ACTION * ET_CAN_WIRE_WORD_BYTES], filter.action);
        write_word(&response[ET_CAN_FILTER_FIELD_ID1 * ET_CAN_WIRE_WORD_BYTES], filter.id1);
        write_word(&response[ET_CAN_FILTER_FIELD_ID2 * ET_CAN_WIRE_WORD_BYTES], filter.id2);
        write_word(&response[ET_CAN_FILTER_FIELD_BUFFER * ET_CAN_WIRE_WORD_BYTES],
                   filter.buffer_index);
    }

    return status;
}

/**
 * @brief Execute protocol consume or one scalar timer/clock action.
 * @param[in] id Logical controller.
 * @param[in] command Validated command.
 * @param[in] body Exact decoded request storage.
 * @param[out] response Capacity-checked response storage.
 * @return Own Wrap status, with no retry after consuming read-clear state.
 * @note No loop, cross-IP initialization, event capture or Case verdict is performed.
 */
static et_wrap_status_t execute_status_command(et_can_id_t id, uint16_t command,
                                               const uint8_t *body, uint8_t *response)
{
    et_wrap_status_t status;
    et_can_protocol_status_t protocol;
    uint32_t value;

    /* Phase 1: State-changing and read-clear operations are performed once. */
    if (command == ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME)
    {
        status = et_can_wrap_consume_protocol_status(id, &protocol);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_PROTOCOL_LAST_ERROR * ET_CAN_WIRE_WORD_BYTES],
                       protocol.last_error);
            write_word(&response[ET_CAN_PROTOCOL_ACTIVITY * ET_CAN_WIRE_WORD_BYTES],
                       protocol.activity);
            write_word(&response[ET_CAN_PROTOCOL_ERROR_PASSIVE * ET_CAN_WIRE_WORD_BYTES],
                       protocol.error_passive);
            write_word(&response[ET_CAN_PROTOCOL_WARNING * ET_CAN_WIRE_WORD_BYTES],
                       protocol.warning);
            write_word(&response[ET_CAN_PROTOCOL_BUS_OFF * ET_CAN_WIRE_WORD_BYTES],
                       protocol.bus_off);
            write_word(&response[ET_CAN_PROTOCOL_DATA_LAST_ERROR * ET_CAN_WIRE_WORD_BYTES],
                       protocol.data_last_error);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_ESI * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_esi);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_BRS * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_brs);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_FD * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_fd);
            write_word(&response[ET_CAN_PROTOCOL_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES],
                       protocol.protocol_exception);
            write_word(&response[ET_CAN_PROTOCOL_TDC_POSITION * ET_CAN_WIRE_WORD_BYTES],
                       protocol.tdc_position);
            write_word(&response[ET_CAN_PROTOCOL_TX_ERROR_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.tx_error_count);
            write_word(&response[ET_CAN_PROTOCOL_RX_ERROR_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.rx_error_count);
            write_word(&response[ET_CAN_PROTOCOL_RX_ERROR_PASSIVE * ET_CAN_WIRE_WORD_BYTES],
                       protocol.rx_error_passive);
            write_word(&response[ET_CAN_PROTOCOL_ERROR_LOG_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.error_log_count);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_TIMESTAMP_RESET)
    {
        return et_can_wrap_reset_timestamp(id);
    }

    if (command == ET_CAN_COMMAND_CLOCK_STOP_SET)
    {
        value = read_word(body);

        if (value > 1u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        return et_can_wrap_set_clock_stop(id, (uint8_t)value);
    }

    /* Phase 2: Select one nondestructive read and serialize only its successful result. */
    switch (command)
    {
        case ET_CAN_COMMAND_TIMESTAMP_GET:
        {
            status = et_can_wrap_get_timestamp(id, &value);
            break;
        }

        case ET_CAN_COMMAND_TIMEOUT_COUNTER_GET:
        {
            status = et_can_wrap_get_timeout_counter(id, &value);
            break;
        }

        case ET_CAN_COMMAND_CLOCK_STOP_ACK_GET:
        {
            status = et_can_wrap_get_clock_stop_ack(id, &value);
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(response, value);
    }

    return status;
}

/**
 * @brief Execute one validated basic CAN command through the own Wrap.
 * @param[in,out] service Selected CAN Service and managed IRQ state.
 * @param[in] command Public command number.
 * @param[in] body Validated payload after the instance prefix.
 * @param[out] response Validated output storage, nullable for writes.
 * @return Own Wrap status without performing retry or test assertions.
 * @note All configuration queries read hardware independently of prior requests.
 */
static et_wrap_status_t execute_command(et_can_service_t *service, uint16_t command,
                                        const uint8_t *body, uint8_t *response)
{
    et_can_id_t id = service->can_id;
    et_wrap_status_t status;
    et_can_identity_t identity;
    et_can_timing_t timing;
    et_can_timing_limits_t limits;
    et_can_options_t options;
    et_can_option_limits_t option_limits;
    uint8_t initializing;
    uint32_t requested;

    if ((command >= ET_CAN_COMMAND_IRQ_MASK_SET) && (command <= ET_CAN_COMMAND_IRQ_EVENT_RESET))
    {
        return execute_irq_command(service, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME) &&
        (command <= ET_CAN_COMMAND_CLOCK_STOP_ACK_GET))
    {
        return execute_status_command(id, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_FILTER_SET) && (command <= ET_CAN_COMMAND_EXTENDED_MASK_GET)) ||
        (command == ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET))
    {
        return execute_filter_command(id, command, body, response);
    }

    /* RAM commands form one own-IP codec group; no orchestration is hidden here. */
    if ((command >= ET_CAN_COMMAND_RAM_LIMITS_GET) && (command <= ET_CAN_COMMAND_RAM_LAYOUT_GET))
    {
        return execute_ram_command(id, command, body, response);
    }

    /* Phase 1: Decode state-changing requests without inventing missing parameters. */
    if ((command >= ET_CAN_COMMAND_TX_WRITE) && (command <= ET_CAN_COMMAND_TX_STATUS_GET))
    {
        return execute_tx_command(id, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_RX_FIFO_STATUS_GET) && (command <= ET_CAN_COMMAND_RX_BUFFER_ACK))
    {
        return execute_rx_command(id, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_BUS_CONFIG_SET) && (command <= ET_CAN_COMMAND_BUS_LIMITS_GET))
    {
        return execute_bus_command(id, command, body, response);
    }

    switch (command)
    {
        case ET_CAN_COMMAND_INITIALIZING_SET:
        {
            requested = read_word(body);

            if (requested > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_set_initializing(id, (uint8_t)requested);
        }

        case ET_CAN_COMMAND_TIMING_SET:
        {
            decode_phase(body, &timing.nominal);
            decode_phase(&body[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES], &timing.data);

            return et_can_wrap_set_timing(id, &timing);
        }

        case ET_CAN_COMMAND_OPTIONS_SET:
        {
            decode_options(body, &options);

            return et_can_wrap_set_options(id, &options);
        }

        default:
        {
            break;
        }
    }

    /* Phase 2: Query the requested facts and publish only successful readbacks. */
    switch (command)
    {
        case ET_CAN_COMMAND_IDENTITY_GET:
        {
            status = et_can_wrap_get_identity(id, &identity);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, identity.revision);
                write_word(&response[ET_CAN_WIRE_WORD_BYTES], identity.endian);
            }

            return status;
        }

        case ET_CAN_COMMAND_INITIALIZING_GET:
        {
            status = et_can_wrap_get_initializing(id, &initializing);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, initializing);
            }

            return status;
        }

        case ET_CAN_COMMAND_TIMING_LIMITS_GET:
        {
            status = et_can_wrap_get_timing_limits(id, &limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_phase(response, &limits.nominal_max);
                encode_phase(&response[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES],
                             &limits.data_max);
            }

            return status;
        }

        case ET_CAN_COMMAND_TIMING_GET:
        {
            status = et_can_wrap_get_timing(id, &timing);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_phase(response, &timing.nominal);
                encode_phase(&response[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES], &timing.data);
            }

            return status;
        }

        case ET_CAN_COMMAND_OPTIONS_GET:
        {
            status = et_can_wrap_get_options(id, &options);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_options(response, &options);
            }

            return status;
        }

        case ET_CAN_COMMAND_OPTION_LIMITS_GET:
        {
            status = et_can_wrap_get_option_limits(id, &option_limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_LIMIT_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.tdc_offset_cycles);
                write_word(&response[ET_CAN_LIMIT_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.tdc_filter_cycles);
                write_word(&response[ET_CAN_LIMIT_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.ram_watchdog_cycles);
            }

            return status;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Validate the complete CAN envelope before invoking a primitive.
 * @param[in,out] context Initialized CAN descriptor storage.
 * @param[in] command_id Public command number.
 * @param[in] request_body Request bytes including the logical instance prefix.
 * @param[in] request_length Exact request byte count.
 * @param[out] response_body Storage for requested facts, nullable for write commands.
 * @param[in] response_capacity Available output capacity in bytes.
 * @param[out] response_length Actual size, zero for every error.
 * @return Existing ET protocol status.
 * @note Malformed bodies never reach hardware; polling and final verdict stay on PC.
 */
static uint16_t can_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    /* Unlisted entries have no words; named indices prevent command-order drift. */
    static const uint8_t input_words[ET_CAN_COMMAND_COUNT] = {
        [ET_CAN_COMMAND_INITIALIZING_SET] = 1u,
        [ET_CAN_COMMAND_TIMING_SET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_OPTIONS_SET] = ET_CAN_OPTIONS_WORDS,
        [ET_CAN_COMMAND_RAM_LAYOUT_SET] = ET_CAN_RAM_LAYOUT_WORDS,
        [ET_CAN_COMMAND_BUS_CONFIG_SET] = ET_CAN_BUS_CONFIG_WORDS,
        [ET_CAN_COMMAND_LOOPBACK_SET] = 1u,
        [ET_CAN_COMMAND_TX_WRITE] = ET_CAN_TX_WRITE_WORDS,
        [ET_CAN_COMMAND_TX_REQUEST] = 1u,
        [ET_CAN_COMMAND_RX_FIFO_STATUS_GET] = 1u,
        [ET_CAN_COMMAND_RX_READ] = ET_CAN_RX_SELECT_WORDS,
        [ET_CAN_COMMAND_RX_FIFO_ACK] = ET_CAN_RX_SELECT_WORDS,
        [ET_CAN_COMMAND_RX_BUFFER_ACK] = ET_CAN_RX_BITMAP_WORDS,
        [ET_CAN_COMMAND_FILTER_SET] = ET_CAN_FILTER_SET_WORDS,
        [ET_CAN_COMMAND_FILTER_GET] = ET_CAN_FILTER_SELECT_WORDS,
        [ET_CAN_COMMAND_EXTENDED_MASK_SET] = 1u,
        [ET_CAN_COMMAND_CLOCK_STOP_SET] = 1u,
        [ET_CAN_COMMAND_IRQ_MASK_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_IRQ_LINE_SELECT_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_IRQ_CLEAR] = 1u,
        [ET_CAN_COMMAND_IRQ_CAPTURE_START] = ET_CAN_IRQ_CONTROL_WORDS};
    static const uint8_t output_words[ET_CAN_COMMAND_COUNT] = {
        [ET_CAN_COMMAND_IDENTITY_GET] = ET_CAN_IDENTITY_WORDS,
        [ET_CAN_COMMAND_INITIALIZING_GET] = 1u,
        [ET_CAN_COMMAND_TIMING_LIMITS_GET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_TIMING_GET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_OPTIONS_GET] = ET_CAN_OPTIONS_WORDS,
        [ET_CAN_COMMAND_OPTION_LIMITS_GET] = ET_CAN_OPTION_LIMIT_WORDS,
        [ET_CAN_COMMAND_RAM_LIMITS_GET] = ET_CAN_RAM_LIMIT_WORDS,
        [ET_CAN_COMMAND_RAM_LAYOUT_GET] = ET_CAN_RAM_LAYOUT_WORDS,
        [ET_CAN_COMMAND_BUS_CONFIG_GET] = ET_CAN_BUS_CONFIG_WORDS,
        [ET_CAN_COMMAND_LOOPBACK_GET] = 1u,
        [ET_CAN_COMMAND_BUS_LIMITS_GET] = ET_CAN_BUS_LIMIT_WORDS,
        [ET_CAN_COMMAND_TX_STATUS_GET] = ET_CAN_TX_STATUS_WORDS,
        [ET_CAN_COMMAND_RX_FIFO_STATUS_GET] = ET_CAN_RX_FIFO_STATUS_WORDS,
        [ET_CAN_COMMAND_RX_READ] = ET_CAN_RX_FRAME_WORDS,
        [ET_CAN_COMMAND_RX_BUFFER_STATUS_GET] = ET_CAN_RX_BITMAP_WORDS,
        [ET_CAN_COMMAND_FILTER_GET] = ET_CAN_FILTER_CONFIG_WORDS,
        [ET_CAN_COMMAND_EXTENDED_MASK_GET] = 1u,
        [ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME] = ET_CAN_PROTOCOL_STATUS_WORDS,
        [ET_CAN_COMMAND_TIMESTAMP_GET] = 1u,
        [ET_CAN_COMMAND_TIMEOUT_COUNTER_GET] = 1u,
        [ET_CAN_COMMAND_CLOCK_STOP_ACK_GET] = 1u,
        [ET_CAN_COMMAND_IRQ_SNAPSHOT_GET] = ET_CAN_IRQ_SNAPSHOT_WORDS,
        [ET_CAN_COMMAND_IRQ_EVENT_GET] = ET_CAN_IRQ_EVENT_WORDS,
        [ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET] = ET_CAN_HIGH_PRIORITY_STATUS_WORDS};
    et_can_service_t *service = (et_can_service_t *)context;
    uint16_t output_bytes;
    et_wrap_status_t status;

    /* Phase 1: Validate command identity and all buffer bounds before decoding. */
    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (command_id >= ET_CAN_COMMAND_COUNT)
    {
        return ET_STATUS_INVALID_COMMAND;
    }

    output_bytes = output_words[command_id] * ET_CAN_WIRE_WORD_BYTES;

    if ((service == NULL) || (request_body == NULL) ||
        (request_length !=
         ET_CAN_REQUEST_PREFIX_BYTES + input_words[command_id] * ET_CAN_WIRE_WORD_BYTES) ||
        (request_body[0] != service->can_id) || (response_capacity < output_bytes) ||
        ((output_bytes != 0u) && (response_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute one action and publish the contract length only on success. */
    status = execute_command(service, command_id, &request_body[ET_CAN_REQUEST_PREFIX_BYTES],
                             response_body);

    if (status == ET_WRAP_STATUS_OK)
    {
        *response_length = output_bytes;
    }

    return status_from_wrap(status);
}

/**
 * @brief Initialize static Service metadata without touching the CAN controller.
 * @param[out] service Application-owned storage.
 * @param[in] can_id Logical controller identity representable by the instance byte.
 * @param[in,out] irq_manager Required factory dependency; no IRQ binding occurs here.
 * @param[in] irq_priority Board-selected priority used by explicit managed IRQ capture.
 * @return Zero on success, minus one for invalid descriptor inputs.
 * @note Does not enable clocks, configure GPIO, initialize CAN or allocate resources.
 */
int et_can_service_init(et_can_service_t *service, et_can_id_t can_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL) || (can_id > UINT8_MAX))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->can_id = can_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_CAN_SERVICE_ID;
    service->descriptor.instance_id = can_id;
    service->descriptor.context = service;
    service->descriptor.handle = can_handle;

    return 0;
}

/**
 * @brief Return the initialized descriptor without transferring ownership.
 * @param[in] service Application-owned storage.
 * @return Descriptor pointer or NULL for a null Service.
 * @note Performs no state or hardware mutation.
 */
const et_service_descriptor_t *et_can_service_descriptor(const et_can_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct a CAN Service through the existing factory contract.
 * @param[out] storage Application-owned Service memory.
 * @param[in] instance_id Logical CAN identity.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Registered command descriptor.
 * @return Zero on success, otherwise minus one.
 * @note No CAN initialization or IRQ activation is performed by registration.
 */
int et_can_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_can_service_t *service = (et_can_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_can_service_init(service, (et_can_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_can_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
