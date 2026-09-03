/** @file et_ipcm_service.c @brief IPCM atomic commands and pre-clear event snapshots. */
#include "et_ipcm_service.h"
#include <stddef.h>
#include <string.h>

/**
 * @brief Decode an unaligned little-endian u16.
 * @param[in] data Two validated request bytes.
 * @note Has no hardware side effect.
 * @return Decoded value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8u));
}

/**
 * @brief Decode an unaligned little-endian u32.
 * @param[in] data Four validated request bytes.
 * @note Does not cast Wire storage to a native structure.
 * @return Decoded value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)read_u16(data) | ((uint32_t)read_u16(data + ET_IPCM_SERVICE_U16_BYTES) << 16u);
}

/**
 * @brief Encode a little-endian u16 into response storage.
 * @param[out] data Two writable bytes.
 * @param[in] value Value to encode.
 * @note The caller has checked response capacity.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & ET_IPCM_SERVICE_BYTE_MASK);
    data[1] = (uint8_t)(value >> 8u);
}

/**
 * @brief Encode a little-endian u32 into response storage.
 * @param[out] data Four writable bytes.
 * @param[in] value Value to encode.
 * @note The caller has checked response capacity.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    write_u16(data, (uint16_t)value);
    write_u16(data + ET_IPCM_SERVICE_U16_BYTES, (uint16_t)(value >> 16u));
}

/**
 * @brief Map own-Wrap status to the common command status.
 * @param[in] status Result of an IPCM action.
 * @note Preserves unsupported, invalid and busy outcomes.
 * @return ET status code.
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
        case ET_WRAP_STATUS_NO_RESOURCE:
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
 * @brief Latch a single mailbox event before any ACK, clear or release.
 * @param[in,out] slot Armed fixed-capacity capture slot.
 * @param[in] from_irq Nonzero only for a real IRQ Manager callback.
 * @note Reads bounded payload, then masks this source to avoid a level-IRQ storm;
 *       does not acknowledge or advance any Case. Polling never increments callback count.
 */
static void capture_once(et_ipcm_capture_slot_t *slot, uint8_t from_irq)
{
    et_ipcm_wrap_pending_snapshot_t pending;
    uint32_t expected;

    /* Phase 1: Observe live pending before modifying delivery or mailbox state. */
    if (slot->event.state != ET_IPCM_CAPTURE_WAITING)
    {
        return;
    }

    expected = 1u << slot->event.mailbox;

    if (et_ipcm_wrap_pending_snapshot_get(slot->ipcm_id, slot->event.endpoint, &pending) !=
        ET_WRAP_STATUS_OK)
    {
        slot->event.fault_flags |= ET_IPCM_SERVICE_FAULT_READ;
    }
    else if (((from_irq != 0u ? pending.masked_pending : pending.raw_pending) & expected) == 0u)
    {
        /* Shared vector callbacks without our pending bit are not IPCM events. */
        return;
    }
    else
    {
        slot->event.raw_status = pending.raw_pending;
        slot->event.masked_status = pending.masked_pending;
        slot->event.latched_events = pending.raw_pending & expected;
        slot->event.event_count = from_irq != 0u ? 1u : 0u;

        if (et_ipcm_wrap_payload_read(slot->ipcm_id, slot->event.mailbox, slot->event.payload,
                                      slot->event.length) != ET_WRAP_STATUS_OK)
        {
            slot->event.fault_flags |= ET_IPCM_SERVICE_FAULT_READ;
        }
    }

    /* Phase 2: Pause delivery without clearing Raw; PC owns the next atomic action. */
    if ((slot->irq_mode != 0u) &&
        (et_ipcm_wrap_irq_delivery_set(slot->ipcm_id, slot->event.mailbox, slot->event.endpoint,
                                       0u) != ET_WRAP_STATUS_OK))
    {
        slot->event.fault_flags |= ET_IPCM_SERVICE_FAULT_MASK;
    }

    slot->event.state =
        slot->event.fault_flags != 0u ? ET_IPCM_CAPTURE_FAULT : ET_IPCM_CAPTURE_READY;
}

/**
 * @brief Route a hardware interrupt to its single armed observation slot.
 * @param[in,out] context Slot owned by IPCM Service.
 * @param[in] irq_line Physical line supplied by IRQ Manager.
 * @param[in] route_events Logical endpoint set for this binding.
 * @note Contains no blocking wait, logging, protocol decoding or test oracle.
 */
static void ipcm_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_ipcm_capture_slot_t *slot = (et_ipcm_capture_slot_t *)context;

    if ((slot == NULL) || (slot->irq_bound == 0u))
    {
        return;
    }

    if ((irq_line != slot->route.irq_line) || (route_events != slot->route.route_events))
    {
        slot->event.unexpected_count = 1u;
        slot->event.fault_flags |= ET_IPCM_SERVICE_FAULT_UNEXPECTED;

        return;
    }

    capture_once(slot, 1u);
}

/**
 * @brief Stop one capture with source-before-route teardown.
 * @param[in,out] slot Service-owned capture slot.
 * @note Preserves pending mailbox data and retained observations; retries keep ownership on failure.
 * @return ET status code.
 */
static uint16_t capture_abort(et_ipcm_capture_slot_t *slot)
{
    if (slot->irq_bound != 0u)
    {
        if ((et_ipcm_wrap_irq_delivery_set(slot->ipcm_id, slot->event.mailbox, slot->event.endpoint,
                                           0u) != ET_WRAP_STATUS_OK) ||
            (et_irq_manager_unbind(slot->irq_manager, slot->route.irq_line, ipcm_irq_callback,
                                   slot) != 0))
        {
            return ET_STATUS_INTERNAL_ERROR;
        }

        slot->irq_bound = 0u;
    }

    slot->event.state = ET_IPCM_CAPTURE_IDLE;

    return ET_STATUS_OK;
}

/**
 * @brief Arm one bounded capture session in IRQ or explicit polling mode.
 * @param[in,out] service IPCM instance owning all slots.
 * @param[in] request Validated ARM body.
 * @note Does not clear pending or send data. Duplicate ownership is rejected before source changes.
 * @return ET status code; unavailable observation capacity is NOT_SUPPORTED, not hardware absence.
 */
static uint16_t capture_arm(et_ipcm_service_t *service, const uint8_t *request)
{
    uint16_t slot_id = read_u16(request + ET_IPCM_SERVICE_ARM_SLOT);
    uint16_t endpoint = read_u16(request + ET_IPCM_SERVICE_ARM_ENDPOINT);
    uint16_t mailbox = read_u16(request + ET_IPCM_SERVICE_ARM_MAILBOX);
    uint16_t length = read_u16(request + ET_IPCM_SERVICE_ARM_LENGTH);
    uint8_t irq_mode = request[ET_IPCM_SERVICE_ARM_IRQ];
    et_ipcm_wrap_capabilities_t capabilities;
    et_ipcm_capture_slot_t *slot;
    uint32_t generation;
    uint32_t key;
    uint16_t index;
    uint16_t result;
    et_irq_route_t route;

    /* Phase 1: Validate identifiers, hardware capacity and exclusive slot ownership. */
    if ((slot_id >= ET_IPCM_SERVICE_CAPTURE_SLOTS) || (irq_mode > 1u) ||
        (request[ET_IPCM_SERVICE_ARM_STAGE] > ET_IPCM_SERVICE_STAGE_ACK) || (length == 0u))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    if (length > ET_IPCM_SERVICE_CAPTURE_BYTES)
    {
        return ET_STATUS_NOT_SUPPORTED;
    }

    if ((et_ipcm_wrap_capabilities_get(service->ipcm_id, &capabilities) != ET_WRAP_STATUS_OK) ||
        (mailbox >= capabilities.mailbox_count) || (length > capabilities.mailbox_payload_bytes) ||
        (et_ipcm_wrap_irq_route_get(service->ipcm_id, endpoint, &route) != ET_WRAP_STATUS_OK))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    slot = &service->slots[slot_id];

    for (index = 0u; index < ET_IPCM_SERVICE_CAPTURE_SLOTS; ++index)
    {
        if ((index != slot_id) && (service->slots[index].event.state != ET_IPCM_CAPTURE_IDLE) &&
            (service->slots[index].event.endpoint == endpoint) &&
            (service->slots[index].event.mailbox == mailbox))
        {
            return ET_STATUS_BUSY;
        }
    }

    result = capture_abort(slot);

    if (result != ET_STATUS_OK)
    {
        return result;
    }

    /* Phase 2: Publish session identity with source off, then bind and enable atomically. */
    if (et_ipcm_wrap_irq_delivery_set(service->ipcm_id, mailbox, endpoint, 0u) != ET_WRAP_STATUS_OK)
    {
        return ET_STATUS_INTERNAL_ERROR;
    }

    key = et_irq_manager_enter_critical();
    generation = slot->event.generation + 1u;
    (void)memset(&slot->event, 0, sizeof(slot->event));
    slot->event.generation = generation;
    slot->event.endpoint = endpoint;
    slot->event.mailbox = mailbox;
    slot->event.length = length;
    slot->event.stage = request[ET_IPCM_SERVICE_ARM_STAGE];
    slot->event.state = ET_IPCM_CAPTURE_WAITING;
    slot->irq_mode = irq_mode;
    slot->route = route;

    if (irq_mode != 0u)
    {
        slot->irq_bound = 1u;

        if (et_irq_manager_bind(slot->irq_manager, &slot->route, slot->irq_priority,
                                ipcm_irq_callback, slot) != 0)
        {
            /* Unbind also handles a failed bind retaining partial cleanup ownership. */
            result = ET_STATUS_INTERNAL_ERROR;
        }
        else if (et_ipcm_wrap_irq_delivery_set(service->ipcm_id, mailbox, endpoint, 1u) !=
                 ET_WRAP_STATUS_OK)
        {
            result = ET_STATUS_INTERNAL_ERROR;
        }
    }

    if (result != ET_STATUS_OK)
    {
        (void)capture_abort(slot);
    }

    et_irq_manager_exit_critical(key);

    return result;
}

/**
 * @brief Copy a coherent retained event to a versioned Wire response.
 * @param[in] slot Fixed capture storage.
 * @param[out] response Validated response storage.
 * @note Called under the IRQ Manager critical section, with no hardware reads.
 * @return Encoded byte count; unfinished/faulted events never claim a valid payload.
 */
static uint16_t encode_event(const et_ipcm_capture_slot_t *slot, uint8_t *response)
{
    const et_ipcm_capture_event_t *event = &slot->event;
    uint16_t length = event->state == ET_IPCM_CAPTURE_READY ? event->length : 0u;

    write_u32(response + ET_IPCM_SERVICE_EVENT_GENERATION, event->generation);
    write_u32(response + ET_IPCM_SERVICE_EVENT_RAW, event->raw_status);
    write_u32(response + ET_IPCM_SERVICE_EVENT_MASKED, event->masked_status);
    write_u32(response + ET_IPCM_SERVICE_EVENT_LATCHED, event->latched_events);
    write_u32(response + ET_IPCM_SERVICE_EVENT_COUNT, event->event_count);
    write_u32(response + ET_IPCM_SERVICE_EVENT_UNEXPECTED, event->unexpected_count);
    write_u32(response + ET_IPCM_SERVICE_EVENT_OVERFLOW, event->overflow_count);
    write_u32(response + ET_IPCM_SERVICE_EVENT_FAULT, event->fault_flags);
    write_u16(response + ET_IPCM_SERVICE_EVENT_ENDPOINT, event->endpoint);
    write_u16(response + ET_IPCM_SERVICE_EVENT_MAILBOX, event->mailbox);
    write_u16(response + ET_IPCM_SERVICE_EVENT_LENGTH, length);
    write_u16(response + ET_IPCM_SERVICE_EVENT_STATE, event->state);
    write_u16(response + ET_IPCM_SERVICE_EVENT_STAGE, event->stage);
    (void)memcpy(response + ET_IPCM_SERVICE_EVENT_HEADER_SIZE, event->payload, length);

    return ET_IPCM_SERVICE_EVENT_HEADER_SIZE + length;
}

/**
 * @brief Execute one bounded polling step for each explicitly armed polling slot.
 * @param[in,out] context Initialized IPCM Service.
 * @note Returns immediately without pending data; PC owns deadline and abort. IRQ slots are never polled.
 */
static void ipcm_poll(void *context)
{
    et_ipcm_service_t *service = (et_ipcm_service_t *)context;
    uint16_t index;

    for (index = 0u; index < ET_IPCM_SERVICE_CAPTURE_SLOTS; ++index)
    {
        if (service->slots[index].irq_mode == 0u)
        {
            capture_once(&service->slots[index], 0u);
        }
    }
}

/**
 * @brief Decode a complete stable mailbox configuration.
 * @param[in] request Validated CONFIGURE bytes.
 * @param[out] config Versioned own-Wrap arguments.
 * @note Reserved bytes are retained so the Wrap rejects malformed requests.
 */
static void decode_config(const uint8_t *request, et_ipcm_wrap_config_t *config)
{
    (void)memset(config, 0, sizeof(*config));
    config->struct_size = sizeof(*config);
    config->api_version = ET_IPCM_WRAP_API_VERSION;
    config->first_mailbox = read_u16(request + ET_IPCM_SERVICE_CONFIG_FIRST);
    config->mailbox_count = read_u16(request + ET_IPCM_SERVICE_CONFIG_COUNT);
    config->source_endpoints = read_u32(request + ET_IPCM_SERVICE_CONFIG_SOURCE);
    config->destination_endpoints = read_u32(request + ET_IPCM_SERVICE_CONFIG_DESTINATION);
    config->irq_enabled_endpoints = read_u32(request + ET_IPCM_SERVICE_CONFIG_IRQ);
    config->ack_mode = request[ET_IPCM_SERVICE_CONFIG_ACK];
    config->link_mode = request[ET_IPCM_SERVICE_CONFIG_LINK];
    config->reserved16 = read_u16(request + ET_IPCM_SERVICE_CONFIG_RESERVED);
}

/**
 * @brief Dispatch a validated IPCM command to own-Wrap actions or capture state.
 * @param[in,out] context Initialized IPCM Service.
 * @param[in] command_id Stable IPCM command ID.
 * @param[in] request Request bytes, NULL only for empty bodies.
 * @param[in] request_length Valid request byte count.
 * @param[out] response Caller-owned response storage.
 * @param[in] capacity Response capacity in bytes.
 * @param[out] response_length Produced byte count.
 * @note No reset of other IPs, hidden ACK, expected-data comparison or Case sequencing.
 * @return ET command status.
 */
static uint16_t ipcm_handle(void *context, uint16_t command_id, const uint8_t *request,
                            uint16_t request_length, uint8_t *response, uint16_t capacity,
                            uint16_t *response_length)
{
    et_ipcm_service_t *service = (et_ipcm_service_t *)context;
    et_ipcm_wrap_capabilities_t capabilities;
    et_ipcm_wrap_config_t config;
    et_ipcm_wrap_mailbox_snapshot_t mailbox;
    et_ipcm_wrap_pending_snapshot_t pending;
    et_wrap_status_t status;
    uint16_t first;
    uint16_t second;
    uint16_t length;
    uint16_t index;
    uint16_t result;
    uint32_t key;

    /* Phase 1: Validate the common envelope before decoding any command field. */
    if ((service == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;
    first = request_length >= ET_IPCM_SERVICE_ID_SIZE ? read_u16(request) : 0u;
    second = request_length >= ET_IPCM_SERVICE_PAIR_SIZE
                 ? read_u16(request + ET_IPCM_SERVICE_ID_SIZE)
                 : 0u;

    /* Phase 2: Each branch validates exact lengths and performs only its requested action. */
    switch (command_id)
    {
        case ET_IPCM_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) || (response == NULL) ||
                (capacity < ET_IPCM_SERVICE_CAPS_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_ipcm_wrap_capabilities_get(service->ipcm_id, &capabilities);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            /* Eight consecutive u16 fields: version, size, HW counts, SW observation limits. */
            write_u16(response + ET_IPCM_SERVICE_CAPS_VERSION, ET_IPCM_SERVICE_API_VERSION);
            write_u16(response + ET_IPCM_SERVICE_CAPS_SIZE_FIELD, ET_IPCM_SERVICE_CAPS_SIZE);
            write_u16(response + ET_IPCM_SERVICE_CAPS_MAILBOXES, capabilities.mailbox_count);
            write_u16(response + ET_IPCM_SERVICE_CAPS_CHANNELS, capabilities.channel_count);
            write_u16(response + ET_IPCM_SERVICE_CAPS_DATA_WORDS, capabilities.data_word_count);
            write_u16(response + ET_IPCM_SERVICE_CAPS_PAYLOAD_BYTES,
                      capabilities.mailbox_payload_bytes);
            write_u16(response + ET_IPCM_SERVICE_CAPS_CAPTURE_SLOTS, ET_IPCM_SERVICE_CAPTURE_SLOTS);
            write_u16(response + ET_IPCM_SERVICE_CAPS_CAPTURE_BYTES, ET_IPCM_SERVICE_CAPTURE_BYTES);
            *response_length = ET_IPCM_SERVICE_CAPS_SIZE;

            return ET_STATUS_OK;
        }

        case ET_IPCM_COMMAND_CONFIGURE:
        {
            if (request_length != ET_IPCM_SERVICE_CONFIG_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            decode_config(request, &config);

            return status_from_wrap(et_ipcm_wrap_configure(service->ipcm_id, &config));
        }

        case ET_IPCM_COMMAND_MAILBOX_RELEASE:
        {
            if (request_length != ET_IPCM_SERVICE_PAIR_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_ipcm_wrap_mailbox_release(service->ipcm_id, first, second));
        }

        case ET_IPCM_COMMAND_MAILBOX_SNAPSHOT_GET:
        {
            if ((request_length != ET_IPCM_SERVICE_ID_SIZE) || (response == NULL) ||
                (capacity < ET_IPCM_SERVICE_MAILBOX_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_ipcm_wrap_mailbox_snapshot_get(service->ipcm_id, first, &mailbox);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(response + ET_IPCM_SERVICE_MAILBOX_SOURCE, mailbox.source_endpoints);
            write_u32(response + ET_IPCM_SERVICE_MAILBOX_DESTINATION,
                      mailbox.destination_endpoints);
            write_u32(response + ET_IPCM_SERVICE_MAILBOX_IRQ, mailbox.irq_enabled_endpoints);
            response[ET_IPCM_SERVICE_MAILBOX_ACK] = mailbox.ack_mode;
            response[ET_IPCM_SERVICE_MAILBOX_LINK] = mailbox.link_mode;
            write_u16(response + ET_IPCM_SERVICE_MAILBOX_RESERVED, 0u);
            *response_length = ET_IPCM_SERVICE_MAILBOX_SIZE;

            return ET_STATUS_OK;
        }

        case ET_IPCM_COMMAND_PENDING_SNAPSHOT_GET:
        {
            if ((request_length != ET_IPCM_SERVICE_ID_SIZE) || (response == NULL) ||
                (capacity < ET_IPCM_SERVICE_PENDING_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_ipcm_wrap_pending_snapshot_get(service->ipcm_id, first, &pending);

            if (status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(status);
            }

            write_u32(response, pending.raw_pending);
            write_u32(response + ET_IPCM_SERVICE_U32_BYTES, pending.masked_pending);
            *response_length = ET_IPCM_SERVICE_PENDING_SIZE;

            return ET_STATUS_OK;
        }

        case ET_IPCM_COMMAND_PAYLOAD_WRITE:
        {
            if (request_length < ET_IPCM_SERVICE_WRITE_HEADER_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            length = read_u16(request + ET_IPCM_SERVICE_WRITE_LENGTH);

            if (length != request_length - ET_IPCM_SERVICE_WRITE_HEADER_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_ipcm_wrap_payload_write(service->ipcm_id, first, second,
                                           request + ET_IPCM_SERVICE_WRITE_HEADER_SIZE, length));
        }

        case ET_IPCM_COMMAND_PAYLOAD_READ:
        {
            if ((request_length != ET_IPCM_SERVICE_PAIR_SIZE) || (response == NULL) ||
                (capacity < second))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            status = et_ipcm_wrap_payload_read(service->ipcm_id, first, response, second);

            if (status == ET_WRAP_STATUS_OK)
            {
                *response_length = second;
            }

            return status_from_wrap(status);
        }

        case ET_IPCM_COMMAND_MESSAGE_SEND:
        case ET_IPCM_COMMAND_ACK_SEND:
        case ET_IPCM_COMMAND_INTERRUPT_CLEAR:
        {
            if (request_length != ET_IPCM_SERVICE_ID_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            if (command_id == ET_IPCM_COMMAND_MESSAGE_SEND)
            {
                status = et_ipcm_wrap_message_send(service->ipcm_id, first);
            }
            else if (command_id == ET_IPCM_COMMAND_ACK_SEND)
            {
                status = et_ipcm_wrap_ack_send(service->ipcm_id, first);
            }
            else
            {
                status = et_ipcm_wrap_interrupt_clear(service->ipcm_id, first);
            }

            return status_from_wrap(status);
        }

        case ET_IPCM_COMMAND_DESTINATION_RELEASE:
        {
            if (request_length != ET_IPCM_SERVICE_PAIR_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(
                et_ipcm_wrap_destination_release(service->ipcm_id, first, second));
        }

        case ET_IPCM_COMMAND_CAPTURE_ARM:
        {
            if (request_length != ET_IPCM_SERVICE_ARM_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return capture_arm(service, request);
        }

        case ET_IPCM_COMMAND_CAPTURE_GET:
        {
            if ((request_length != ET_IPCM_SERVICE_ID_SIZE) ||
                (first >= ET_IPCM_SERVICE_CAPTURE_SLOTS) || (response == NULL) ||
                (capacity < ET_IPCM_SERVICE_EVENT_HEADER_SIZE + ET_IPCM_SERVICE_CAPTURE_BYTES))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            key = et_irq_manager_enter_critical();
            *response_length = encode_event(&service->slots[first], response);
            et_irq_manager_exit_critical(key);

            return ET_STATUS_OK;
        }

        case ET_IPCM_COMMAND_CAPTURE_ABORT:
        {
            if ((request_length != ET_IPCM_SERVICE_ID_SIZE) ||
                (first >= ET_IPCM_SERVICE_CAPTURE_SLOTS))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return capture_abort(&service->slots[first]);
        }

        case ET_IPCM_COMMAND_STATE_RESET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            for (index = 0u; index < ET_IPCM_SERVICE_CAPTURE_SLOTS; ++index)
            {
                result = capture_abort(&service->slots[index]);

                if (result != ET_STATUS_OK)
                {
                    return result;
                }
            }

            for (index = 0u; index < ET_IPCM_SERVICE_CAPTURE_SLOTS; ++index)
            {
                /* Keep generation monotonic across reset to distinguish stale observations. */
                uint32_t generation = service->slots[index].event.generation;
                (void)memset(&service->slots[index].event, 0, sizeof(service->slots[index].event));
                service->slots[index].event.generation = generation;
            }

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize software storage and the IPCM command descriptor.
 * @param[out] service Static Application-owned storage.
 * @param[in] ipcm_id Logical instance identity.
 * @param[in,out] irq_manager Active core-local IRQ Manager.
 * @param[in] irq_priority Board-selected priority for capture routes.
 * @note Does not reset, configure or enable hardware.
 * @return Zero on success, minus one for invalid storage/dependencies.
 */
int et_ipcm_service_init(et_ipcm_service_t *service, et_ipcm_id_t ipcm_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    uint16_t index;

    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->ipcm_id = ipcm_id;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_IPCM_SERVICE_ID;
    service->descriptor.instance_id = ipcm_id;
    service->descriptor.context = service;
    service->descriptor.handle = ipcm_handle;
    service->descriptor.poll = ipcm_poll;

    for (index = 0u; index < ET_IPCM_SERVICE_CAPTURE_SLOTS; ++index)
    {
        service->slots[index].ipcm_id = ipcm_id;
        service->slots[index].irq_manager = irq_manager;
        service->slots[index].irq_priority = irq_priority;
    }

    return 0;
}

/**
 * @brief Return a Service-owned immutable descriptor.
 * @param[in] service Initialized IPCM Service.
 * @note The descriptor lifetime is the Service lifetime.
 * @return Descriptor or NULL for invalid storage.
 */
const et_service_descriptor_t *et_ipcm_service_descriptor(const et_ipcm_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Register IPCM through the unchanged Application factory mechanism.
 * @param[out] storage Static IPCM Service storage.
 * @param[in] instance_id Logical instance.
 * @param[in] context IRQ Manager and priority dependencies.
 * @param[out] descriptor Published Service descriptor.
 * @note No Case logic or hardware initialization belongs to the factory.
 * @return Zero on success, minus one for invalid dependencies.
 */
int et_ipcm_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor)
{
    et_ipcm_service_t *service = (et_ipcm_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_ipcm_service_init(service, instance_id, context->irq_manager, context->irq_priority) !=
        0)
    {
        return -1;
    }

    *descriptor = et_ipcm_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
