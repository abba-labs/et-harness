/** @file et_spi_service.c @brief Decode bounded SPI actions and preserve ISR evidence. */
#include "et_spi_service.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

static et_wrap_status_t event_access(et_spi_service_t *service, uint8_t reset, uint32_t *words);

/**
 * @brief Translate the own Wrap status to the existing protocol.
 * @param[in] status Result of one SPI action.
 * @return Stable ET status without changing the failure meaning.
 * @note No retry or recovery is performed.
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
 * @brief Decode a u32 without unaligned loads.
 * @param[in] data Four validated little-endian bytes.
 * @return Decoded value.
 * @note This pure codec never touches hardware.
 */
static uint32_t read_word(const uint8_t *data)
{
    uint32_t value = 0u;
    uint16_t index;

    for (index = 0u; index < ET_SPI_WIRE_WORD_BYTES; ++index)
    {
        value |= (uint32_t)data[index] << (index * CHAR_BIT);
    }

    return value;
}

/**
 * @brief Encode one u32 without host layout assumptions.
 * @param[out] data Four validated output bytes.
 * @param[in] value Unsigned field value.
 * @note Called only after output capacity validation.
 */
static void write_word(uint8_t *data, uint32_t value)
{
    uint16_t index;

    for (index = 0u; index < ET_SPI_WIRE_WORD_BYTES; ++index)
    {
        data[index] = (uint8_t)(value >> (index * CHAR_BIT));
    }
}

/**
 * @brief Saturate a Service-owned counter and preserve overflow evidence.
 * @param[in,out] service Capture evidence owner.
 * @param[in,out] counter Counter being incremented.
 * @note ISR or critical-section context only; no hardware access.
 */
static void increment_counter(et_spi_service_t *service, volatile uint32_t *counter)
{
    if (*counter != UINT32_MAX)
    {
        ++*counter;

        return;
    }

    service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_OVERFLOW;

    if (service->event.overflow_count != UINT32_MAX)
    {
        ++service->event.overflow_count;
    }
}

/**
 * @brief Latch active SPI sources without draining FIFO or consuming read-clear SR.
 * @param[in,out] context SPI Service storage.
 * @param[in] irq_line Delivered private physical route.
 * @param[in] route_events Public events routed to this callback.
 * @note ISR context; fixed work only. Mask active sources to prevent level storms.
 */
static void spi_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_spi_service_t *service = (et_spi_service_t *)context;
    et_spi_snapshot_t snapshot;
    uint32_t active;

    /* Phase 1: Read only non-destructive facts and ignore inactive shared routes. */
    if (et_spi_wrap_get_snapshot(service->spi_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_IO;
        (void)et_spi_wrap_set_irq_enabled(service->spi_id, ET_SPI_IRQ_ALL, 0u);

        return;
    }

    active = snapshot.irq_status;

    if (active == 0u)
    {
        return;
    }

    /* Phase 2: Preserve evidence before masking; PC owns FIFO drain and explicit clear. */
    if (service->event.event_count == 0u)
    {
        service->event.raw_status = snapshot.irq_raw;
        service->event.masked_status = active;
    }

    service->event.latched_events |= active;
    increment_counter(service, &service->event.event_count);

    if (irq_line != service->route.irq_line ||
        (active & ~(route_events & service->watched_sources)) != 0u)
    {
        increment_counter(service, &service->event.unexpected_count);
        service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_UNEXPECTED;
    }

    if (et_spi_wrap_set_irq_enabled(service->spi_id, active, 0u) != ET_WRAP_STATUS_OK)
    {
        service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_IO;
    }
}

/**
 * @brief Stop IRQ delivery in source-before-route order.
 * @param[in,out] service Capture owner.
 * @return Own Wrap error or I/O error if unbinding remains incomplete.
 * @note Evidence is retained; a failed unbind keeps ownership for a later retry.
 */
static et_wrap_status_t stop_capture(et_spi_service_t *service)
{
    et_wrap_status_t status = et_spi_wrap_set_irq_enabled(service->spi_id, ET_SPI_IRQ_ALL, 0u);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (service->bound != 0u)
    {
        if (et_irq_manager_unbind(service->irq_manager, service->route.irq_line, spi_irq_callback,
                                  service) != 0)
        {
            service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_IO;

            return ET_WRAP_STATUS_IO_ERROR;
        }

        service->bound = 0u;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Start one explicit capture session through the existing IRQ Manager.
 * @param[in,out] service Capture owner.
 * @param[in] sources Nonzero public source mask.
 * @return Success or the actual failed setup result.
 * @note Resets software evidence and binds only; PC owns source masks and hardware clear.
 */
static et_wrap_status_t start_capture(et_spi_service_t *service, uint32_t sources)
{
    et_wrap_status_t status;
    size_t index;
    uint32_t key;

    /* Phase 1: Reject rebinds and reset only the Service-owned evidence. */
    if (sources == 0u || (sources & ~ET_SPI_IRQ_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (service->bound != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    status = event_access(service, 1u, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = et_spi_wrap_get_irq_route(service->spi_id, &service->route);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    service->watched_sources = sources;

    /* Phase 2: Bind without consuming the Raw/Status stimulus prepared by PC.
     * Delivery may start immediately; never re-enable a source masked by the ISR. */
    if (et_irq_manager_bind(service->irq_manager, &service->route, service->irq_priority,
                            spi_irq_callback, service) != 0)
    {
        /* A failed bind may reserve nothing, or retain a partially-created route.
         * Inspect only this callback's published ownership; never change Manager storage. */
        key = et_irq_manager_enter_critical();

        for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
        {
            const et_irq_binding_t *binding = &service->irq_manager->bindings[index];

            if (binding->in_use != 0u && binding->irq_line == service->route.irq_line &&
                binding->callback == spi_irq_callback && binding->context == service)
            {
                service->bound = 1u;
                break;
            }
        }

        et_irq_manager_exit_critical(key);
        service->event.fault_flags |= ET_SPI_CAPTURE_FAULT_IO;

        (void)stop_capture(service);

        return ET_WRAP_STATUS_IO_ERROR;
    }

    service->bound = 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Copy or reset fixed ISR evidence atomically.
 * @param[in,out] service Capture owner.
 * @param[in] reset Nonzero requests a reset while unbound.
 * @param[out] words Eight public event words for a read, unused for a reset.
 * @return Success, busy or overflow when generation cannot advance.
 * @note Reset does not touch hardware; it starts a new software evidence generation.
 */
static et_wrap_status_t event_access(et_spi_service_t *service, uint8_t reset, uint32_t *words)
{
    uint32_t key;

    if (reset != 0u && service->bound != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    key = et_irq_manager_enter_critical();

    if (reset != 0u)
    {
        if (service->event.generation == UINT32_MAX)
        {
            et_irq_manager_exit_critical(key);

            return ET_WRAP_STATUS_IO_ERROR;
        }

        ++service->event.generation;
        service->event.raw_status = 0u;
        service->event.masked_status = 0u;
        service->event.latched_events = 0u;
        service->event.event_count = 0u;
        service->event.unexpected_count = 0u;
        service->event.overflow_count = 0u;
        service->event.fault_flags = 0u;
    }
    else
    {
        words[ET_SPI_EVENT_RAW_STATUS] = service->event.raw_status;
        words[ET_SPI_EVENT_MASKED_STATUS] = service->event.masked_status;
        words[ET_SPI_EVENT_LATCHED_EVENTS] = service->event.latched_events;
        words[ET_SPI_EVENT_EVENT_COUNT] = service->event.event_count;
        words[ET_SPI_EVENT_UNEXPECTED_COUNT] = service->event.unexpected_count;
        words[ET_SPI_EVENT_OVERFLOW_COUNT] = service->event.overflow_count;
        words[ET_SPI_EVENT_GENERATION] = service->event.generation;
        words[ET_SPI_EVENT_FAULT_FLAGS] = service->event.fault_flags;
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Decode or read back the full public configuration.
 * @param[in] id Logical SPI instance.
 * @param[in] write Nonzero applies settings; zero queries hardware.
 * @param[in] input Sixteen decoded request fields when writing.
 * @param[out] output Sixteen readback fields when querying.
 * @return Own Wrap result.
 * @note Wire order is explicit and independent of C structure padding.
 */
static et_wrap_status_t config_access(et_spi_id_t id, uint8_t write, const uint32_t *input,
                                      uint32_t *output)
{
    et_spi_config_t config;
    et_wrap_status_t status;

    /* Phase 1: Decode the complete write envelope before the own Wrap call. */
    if (write != 0u)
    {
        config.role = input[ET_SPI_CONFIG_ROLE];
        config.frame_format = input[ET_SPI_CONFIG_FRAME_FORMAT];
        config.clock_mode = input[ET_SPI_CONFIG_CLOCK_MODE];
        config.transfer_mode = input[ET_SPI_CONFIG_TRANSFER_MODE];
        config.cs_policy = input[ET_SPI_CONFIG_CS_POLICY];
        config.frame_bits = input[ET_SPI_CONFIG_FRAME_BITS];
        config.frame_count = input[ET_SPI_CONFIG_FRAME_COUNT];
        config.divider = input[ET_SPI_CONFIG_DIVIDER];
        config.target_output_enabled = input[ET_SPI_CONFIG_TARGET_OUTPUT_ENABLED];
        config.loopback = input[ET_SPI_CONFIG_LOOPBACK];
        config.rx_sample_delay = input[ET_SPI_CONFIG_RX_SAMPLE_DELAY];
        config.control_bits = input[ET_SPI_CONFIG_CONTROL_BITS];
        config.sequential = input[ET_SPI_CONFIG_SEQUENTIAL];
        config.transmit = input[ET_SPI_CONFIG_TRANSMIT];
        config.handshake = input[ET_SPI_CONFIG_HANDSHAKE];
        config.reserved = input[ET_SPI_CONFIG_RESERVED];

        return et_spi_wrap_configure(id, &config);
    }

    /* Phase 2: Encode actual hardware readback, never the prior request. */
    status = et_spi_wrap_get_config(id, &config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    output[ET_SPI_CONFIG_ROLE] = config.role;
    output[ET_SPI_CONFIG_FRAME_FORMAT] = config.frame_format;
    output[ET_SPI_CONFIG_CLOCK_MODE] = config.clock_mode;
    output[ET_SPI_CONFIG_TRANSFER_MODE] = config.transfer_mode;
    output[ET_SPI_CONFIG_CS_POLICY] = config.cs_policy;
    output[ET_SPI_CONFIG_FRAME_BITS] = config.frame_bits;
    output[ET_SPI_CONFIG_FRAME_COUNT] = config.frame_count;
    output[ET_SPI_CONFIG_DIVIDER] = config.divider;
    output[ET_SPI_CONFIG_TARGET_OUTPUT_ENABLED] = config.target_output_enabled;
    output[ET_SPI_CONFIG_LOOPBACK] = config.loopback;
    output[ET_SPI_CONFIG_RX_SAMPLE_DELAY] = config.rx_sample_delay;
    output[ET_SPI_CONFIG_CONTROL_BITS] = config.control_bits;
    output[ET_SPI_CONFIG_SEQUENTIAL] = config.sequential;
    output[ET_SPI_CONFIG_TRANSMIT] = config.transmit;
    output[ET_SPI_CONFIG_HANDSHAKE] = config.handshake;
    output[ET_SPI_CONFIG_RESERVED] = config.reserved;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Serialize non-destructive FIFO and IRQ facts.
 * @param[in] id Logical SPI identity.
 * @param[out] output Fourteen public words.
 * @return Own Wrap result.
 * @note Does not read SR, FIFO data or interrupt acknowledge registers.
 */
static et_wrap_status_t encode_snapshot(et_spi_id_t id, uint32_t *output)
{
    et_spi_snapshot_t snapshot;
    et_wrap_status_t status = et_spi_wrap_get_snapshot(id, &snapshot);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    output[0] = snapshot.enabled;
    output[1] = snapshot.selected;
    output[2] = snapshot.tx_level;
    output[3] = snapshot.rx_level;
    output[4] = snapshot.tx_threshold;
    output[5] = snapshot.rx_threshold;
    output[6] = snapshot.start_threshold;
    output[7] = snapshot.irq_raw;
    output[8] = snapshot.irq_status;
    output[9] = snapshot.irq_enabled;
    output[10] = snapshot.dma_tx_enabled;
    output[11] = snapshot.dma_rx_enabled;
    output[12] = snapshot.dma_tx_threshold;
    output[13] = snapshot.dma_rx_threshold;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Serialize the chip's programmable ranges.
 * @param[in] id Logical SPI identity.
 * @param[out] output Seven unsigned range facts.
 * @return Own Wrap result.
 * @note Ranges are not feature coverage and not a substitute for capability YAML.
 */
static et_wrap_status_t encode_limits(et_spi_id_t id, uint32_t *output)
{
    et_spi_limits_t limits;
    et_wrap_status_t status = et_spi_wrap_get_limits(id, &limits);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    output[0] = limits.frame_bits_min;
    output[1] = limits.frame_bits_max;
    output[2] = limits.fifo_depth;
    output[3] = limits.divider_min;
    output[4] = limits.divider_max;
    output[5] = limits.frame_count_max;
    output[6] = limits.rx_delay_max;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute one bounded command using only own Wrap and IRQ binding.
 * @param[in,out] service Selected SPI Service.
 * @param[in] command Valid command table index.
 * @param[in] input Validated request words.
 * @param[out] output Response words initialized by the caller.
 * @return Actual Wrap or capture operation result.
 * @note No polling, cross-IP setup, test sequence or PASS/FAIL decision is present.
 */
static et_wrap_status_t execute_command(et_spi_service_t *service, uint16_t command,
                                        const uint32_t *input, uint32_t *output)
{
    et_spi_id_t id = service->spi_id;
    uint8_t count = 0u;
    uintptr_t address = 0u;
    et_wrap_status_t status;

    /* Phase 1: Reject narrowing before converting public u32 values to Boolean/byte arguments. */
    switch (command)
    {
        case ET_SPI_COMMAND_ENABLE_SET:
        case ET_SPI_COMMAND_CS_SET:
        case ET_SPI_COMMAND_LOOPBACK_SET:
        {
            {
                if (input[0] > 1u)
                {
                    return ET_WRAP_STATUS_INVALID_ARGUMENT;
                }

                break;
            }
        }

        case ET_SPI_COMMAND_FIFO_THRESHOLDS_SET:
        {
            {
                if (input[0] > UINT8_MAX || input[1] > UINT8_MAX ||
                    input[ET_SPI_START_THRESHOLD] > UINT8_MAX)
                {
                    return ET_WRAP_STATUS_INVALID_ARGUMENT;
                }

                break;
            }
        }

        case ET_SPI_COMMAND_DMA_CONFIGURE:
        {
            {
                if (input[0] > 1u || input[1] > 1u || input[ET_SPI_DMA_TX_THRESHOLD] > UINT8_MAX ||
                    input[ET_SPI_DMA_RX_THRESHOLD] > UINT8_MAX)
                {
                    return ET_WRAP_STATUS_INVALID_ARGUMENT;
                }

                break;
            }
        }

        case ET_SPI_COMMAND_IRQ_MASK_SET:
        {
            {
                if (input[1] > 1u)
                {
                    return ET_WRAP_STATUS_INVALID_ARGUMENT;
                }

                break;
            }
        }

        default:
        {
            break;
        }
            {
            }
    }

    /* Phase 2: Invoke exactly the requested action and publish only its raw result. */
    switch (command)
    {
        case ET_SPI_COMMAND_LIMITS_GET:
        {
            return encode_limits(id, output);
        }

        case ET_SPI_COMMAND_FIFO_LIMITS_GET:
        {
            et_spi_fifo_limits_t limits;
            et_wrap_status_t status = et_spi_wrap_get_fifo_limits(id, &limits);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status;
            }

            /* Wire order: TX IRQ, RX IRQ, TX start, TX DMA, RX DMA maxima. */
            output[ET_SPI_FIFO_LIMIT_TX_IRQ] = limits.tx_irq_max;
            output[ET_SPI_FIFO_LIMIT_RX_IRQ] = limits.rx_irq_max;
            output[ET_SPI_FIFO_LIMIT_TX_START] = limits.tx_start_max;
            output[ET_SPI_FIFO_LIMIT_DMA_TX] = limits.dma_tx_max;
            output[ET_SPI_FIFO_LIMIT_DMA_RX] = limits.dma_rx_max;

            return ET_WRAP_STATUS_OK;
        }

        case ET_SPI_COMMAND_CONFIGURE:
        {
            return config_access(id, 1u, input, output);
        }

        case ET_SPI_COMMAND_CONFIG_GET:
        {
            return config_access(id, 0u, input, output);
        }

        case ET_SPI_COMMAND_ENABLE_SET:
        {
            return et_spi_wrap_set_enabled(id, (uint8_t)input[0]);
        }

        case ET_SPI_COMMAND_FIFO_RESET:
        {
            return et_spi_wrap_reset_fifo(id);
        }

        case ET_SPI_COMMAND_DIVIDER_SET:
        {
            return et_spi_wrap_set_divider(id, input[0]);
        }

        case ET_SPI_COMMAND_FRAME_COUNT_SET:
        {
            return et_spi_wrap_set_frame_count(id, input[0]);
        }

        case ET_SPI_COMMAND_CS_SET:
        {
            return et_spi_wrap_set_cs_selected(id, (uint8_t)input[0]);
        }

        case ET_SPI_COMMAND_LOOPBACK_SET:
        {
            return et_spi_wrap_set_loopback(id, (uint8_t)input[0]);
        }

        case ET_SPI_COMMAND_FIFO_THRESHOLDS_SET:
        {
            return et_spi_wrap_set_fifo_thresholds(id, (uint8_t)input[0], (uint8_t)input[1],
                                                   (uint8_t)input[ET_SPI_START_THRESHOLD]);
        }

        case ET_SPI_COMMAND_SNAPSHOT_GET:
        {
            return encode_snapshot(id, output);
        }

        case ET_SPI_COMMAND_ERROR_STATUS_READ:
        {
            return et_spi_wrap_read_error_status(id, &output[0], &output[1]);
        }

        case ET_SPI_COMMAND_WRITE_FRAME:
        {
            status = et_spi_wrap_try_write_frame(id, input[0], &count);
            output[0] = count;

            return status;
        }

        case ET_SPI_COMMAND_READ_FRAME:
        {
            status = et_spi_wrap_try_read_frame(id, &output[1], &count);
            output[0] = count;

            return status;
        }

        case ET_SPI_COMMAND_TEST_FIFO_WRITE_ONCE:
        {
            return et_spi_wrap_test_fifo_write_once(id, input[0]);
        }

        case ET_SPI_COMMAND_TEST_FIFO_READ_ONCE:
        {
            return et_spi_wrap_test_fifo_read_once(id, &output[0]);
        }

        case ET_SPI_COMMAND_DMA_CONFIGURE:
        {
            return et_spi_wrap_configure_dma(id, (uint8_t)input[0], (uint8_t)input[1],
                                             (uint8_t)input[ET_SPI_DMA_TX_THRESHOLD],
                                             (uint8_t)input[ET_SPI_DMA_RX_THRESHOLD]);
        }

        case ET_SPI_COMMAND_DMA_ENDPOINT_GET:
        {
            status = et_spi_wrap_get_dma_endpoint(id, &address);
            output[0] = (uint32_t)address;
            output[1] = (uint32_t)((uint64_t)address >> (ET_SPI_WIRE_WORD_BYTES * CHAR_BIT));

            return status;
        }

        case ET_SPI_COMMAND_IRQ_MASK_SET:
        {
            return et_spi_wrap_set_irq_enabled(id, input[0], (uint8_t)input[1]);
        }

        case ET_SPI_COMMAND_IRQ_CLEAR:
        {
            return et_spi_wrap_clear_irq(id, input[0]);
        }

        case ET_SPI_COMMAND_IRQ_CAPTURE_START:
        {
            return start_capture(service, input[0]);
        }

        case ET_SPI_COMMAND_IRQ_CAPTURE_STOP:
        {
            return stop_capture(service);
        }

        case ET_SPI_COMMAND_IRQ_EVENT_GET:
        {
            return event_access(service, 0u, output);
        }

        case ET_SPI_COMMAND_IRQ_EVENT_RESET:
        {
            return event_access(service, 1u, output);
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
            {
            }
    }
}

/**
 * @brief Validate one complete envelope before allowing a SPI action.
 * @param[in,out] context Initialized Service storage.
 * @param[in] command_id Public command ID.
 * @param[in] request_body Instance prefix and fixed words.
 * @param[in] request_length Exact body byte count.
 * @param[out] response_body Output storage, optional for empty replies.
 * @param[in] response_capacity Output byte capacity.
 * @param[out] response_length Zero on error; exact success size otherwise.
 * @return Existing protocol status.
 * @note Length, destination capacity and logical identity are checked before hardware mutation.
 */
static uint16_t spi_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    /* Public Wire word counts follow the command enum, not register layouts. */
    static const uint8_t request_words[ET_SPI_COMMAND_COUNT] = ET_SPI_REQUEST_WORD_COUNTS;
    static const uint8_t response_words[ET_SPI_COMMAND_COUNT] = ET_SPI_RESPONSE_WORD_COUNTS;
    uint32_t input[ET_SPI_MAX_WIRE_WORDS] = {0u};
    uint32_t output[ET_SPI_MAX_WIRE_WORDS] = {0u};
    uint16_t index, size;
    et_wrap_status_t status;
    et_spi_service_t *service = (et_spi_service_t *)context;

    /* Phase 1: Validate all external pointers and exact sizes before any own Wrap call. */
    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (command_id >= ET_SPI_COMMAND_COUNT)
    {
        return ET_STATUS_INVALID_COMMAND;
    }

    size = response_words[command_id] * ET_SPI_WIRE_WORD_BYTES;

    if (service == NULL || request_body == NULL ||
        request_length !=
            ET_SPI_REQUEST_PREFIX_SIZE + request_words[command_id] * ET_SPI_WIRE_WORD_BYTES ||
        request_body[0] != service->spi_id || response_capacity < size ||
        (size != 0u && response_body == NULL))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Decode bounded fields, execute once and publish only on success. */
    for (index = 0u; index < request_words[command_id]; ++index)
    {
        input[index] =
            read_word(&request_body[ET_SPI_REQUEST_PREFIX_SIZE + index * ET_SPI_WIRE_WORD_BYTES]);
    }

    status = execute_command(service, command_id, input, output);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status_from_wrap(status);
    }

    for (index = 0u; index < response_words[command_id]; ++index)
    {
        write_word(&response_body[index * ET_SPI_WIRE_WORD_BYTES], output[index]);
    }

    *response_length = size;

    return ET_STATUS_OK;
}

/**
 * @brief Initialize descriptor storage without configuring hardware.
 * @param[out] service Application-owned storage.
 * @param[in] spi_id Logical identity encoded by the instance byte.
 * @param[in,out] irq_manager Existing common IRQ Manager.
 * @param[in] irq_priority Board-selected interrupt priority.
 * @return Zero on success, minus one for invalid constructor inputs.
 * @note Construction performs no reset, clock setup, source enable or binding.
 */
int et_spi_service_init(et_spi_service_t *service, et_spi_id_t spi_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if (service == NULL || irq_manager == NULL || spi_id > UINT8_MAX)
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->spi_id = spi_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_SPI_SERVICE_ID;
    service->descriptor.instance_id = spi_id;
    service->descriptor.context = service;
    service->descriptor.handle = spi_handle;

    return 0;
}

/**
 * @brief Expose the immutable router descriptor.
 * @param[in] service Initialized Service storage.
 * @return Descriptor pointer or NULL.
 * @note No device or software state is changed.
 */
const et_service_descriptor_t *et_spi_service_descriptor(const et_spi_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct one SPI descriptor through the existing static factory contract.
 * @param[out] storage Application-owned SPI Service memory.
 * @param[in] instance_id Logical SPI identity.
 * @param[in] context Common IRQ dependencies and board priority.
 * @param[out] descriptor Initialized descriptor for router registration.
 * @return Zero on success, otherwise minus one.
 * @note No SPI reset, configuration, clock change or IRQ binding occurs here.
 */
int et_spi_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_spi_service_t *service = (et_spi_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_spi_service_init(service, (et_spi_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_spi_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
