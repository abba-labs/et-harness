/** @file et_ipcm_wrap.c @brief IPCM semantic mapping and own-Driver calls only. */
#include "et_ipcm_wrap.h"
#include <stddef.h>
#include <string.h>
#include "et6x_ipcm.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_ipcm_id_t instance;
} et_ipcm_mapping_t;

typedef struct
{
    uint16_t endpoint;
    uint16_t channel;
    et_irq_line_t irq_line;
} et_ipcm_endpoint_mapping_t;

static const et_ipcm_mapping_t instances[] = ET_CHIP_IPCM_MAP_TABLE;
static const et_ipcm_endpoint_mapping_t endpoints[] = ET_CHIP_IPCM_ENDPOINT_MAP_TABLE;
static const uint32_t ack_modes[] = ET_CHIP_IPCM_ACK_MAP_TABLE;
static const uint32_t link_modes[] = ET_CHIP_IPCM_LINK_MAP_TABLE;

/**
 * @brief Check whether a logical controller is mapped on the selected chip.
 * @param[in] ipcm_id Logical controller identifier.
 * @note Reads immutable mapping data; does not initialize hardware.
 * @return Nonzero for a mapped controller.
 */
static int instance_exists(et_ipcm_id_t ipcm_id)
{
    size_t index;

    for (index = 0u; index < sizeof(instances) / sizeof(instances[0]); ++index)
    {
        if (instances[index].instance == ipcm_id)
        {
            return 1;
        }
    }

    return 0;
}

/**
 * @brief Resolve an event endpoint without exposing its physical channel to Service.
 * @param[in] endpoint Public logical event endpoint.
 * @note Does not configure NVIC or change an IRQ enable bit.
 * @return Mapping or NULL when the endpoint is unavailable.
 */
static const et_ipcm_endpoint_mapping_t *find_endpoint(uint16_t endpoint)
{
    size_t index;

    for (index = 0u; index < sizeof(endpoints) / sizeof(endpoints[0]); ++index)
    {
        if (endpoints[index].endpoint == endpoint)
        {
            return &endpoints[index];
        }
    }

    return NULL;
}

/**
 * @brief Translate a full endpoint set through the chip table, in either direction.
 * @param[in] input Logical or physical bit set.
 * @param[in] reverse Nonzero selects physical-to-logical translation.
 * @param[out] output Translated set, valid only on success.
 * @note Unknown bits fail rather than being silently discarded from hardware evidence.
 * @return Stable status indicating complete translation.
 */
static et_wrap_status_t translate_set(uint32_t input, uint8_t reverse, uint32_t *output)
{
    size_t index;
    uint32_t consumed = 0u;
    uint32_t result = 0u;

    for (index = 0u; index < sizeof(endpoints) / sizeof(endpoints[0]); ++index)
    {
        uint16_t from = reverse ? endpoints[index].channel : endpoints[index].endpoint;
        uint16_t to = reverse ? endpoints[index].endpoint : endpoints[index].channel;

        if ((from >= ET_IPCM_WRAP_ENDPOINT_BITS) || (to >= ET_IPCM_WRAP_ENDPOINT_BITS))
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }

        if ((input & (1u << from)) != 0u)
        {
            consumed |= 1u << from;
            result |= 1u << to;
        }
    }

    if (consumed != input)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *output = result;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate SDK execution results to the stable Wrap status namespace.
 * @param[in] status Own Driver result.
 * @note No errors are converted into successful hardware actions.
 * @return Stable Wrap status.
 */
static et_wrap_status_t from_driver(DRV_Status status)
{
    switch (status)
    {
        case DRV_OK:
        {
            return ET_WRAP_STATUS_OK;
        }

        case DRV_PARAM_ERR:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        case DRV_BUSY:
        {
            return ET_WRAP_STATUS_BUSY;
        }

        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Read actual implemented controller capacities.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[out] capabilities Hardware counts and byte capacity.
 * @note Reads the Driver capability snapshot, never a cached Case expectation.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_capabilities_get(et_ipcm_id_t ipcm_id,
                                               et_ipcm_wrap_capabilities_t *capabilities)
{
    IPCM_TestCapabilities actual;
    DRV_Status status;

    if (!instance_exists(ipcm_id) || (capabilities == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = IPCM_testGetCapabilities(&actual);

    if (status != DRV_OK)
    {
        return from_driver(status);
    }

    if ((actual.mailboxCount > ET_IPCM_WRAP_ENDPOINT_BITS) ||
        (actual.channelCount > ET_IPCM_WRAP_ENDPOINT_BITS) ||
        (actual.dataWordCount > UINT16_MAX / sizeof(uint32_t)))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    capabilities->mailbox_count = (uint16_t)actual.mailboxCount;
    capabilities->channel_count = (uint16_t)actual.channelCount;
    capabilities->data_word_count = (uint16_t)actual.dataWordCount;
    capabilities->mailbox_payload_bytes = (uint16_t)(actual.dataWordCount * sizeof(uint32_t));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply a complete public mailbox or linked-chain configuration.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] config Versioned logical routing and mode configuration.
 * @note Changes only IPCM; clocks, reset, IRQ binding and Case sequencing remain caller-owned.
 * @return Stable Wrap status; malformed or unmapped sets fail before Driver execution.
 */
et_wrap_status_t et_ipcm_wrap_configure(et_ipcm_id_t ipcm_id, const et_ipcm_wrap_config_t *config)
{
    uint32_t source;
    uint32_t destination;
    uint32_t irq;
    uint32_t mode;
    size_t index;

    if (!instance_exists(ipcm_id) || (config == NULL) || (config->struct_size != sizeof(*config)) ||
        (config->api_version != ET_IPCM_WRAP_API_VERSION) ||
        (config->ack_mode > ET_IPCM_WRAP_ACK_AUTO) ||
        (config->link_mode > ET_IPCM_WRAP_LINK_CHAIN) || (config->reserved16 != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < ET_IPCM_WRAP_CONFIG_RESERVED_WORDS; ++index)
    {
        if (config->reserved[index] != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    if ((translate_set(config->source_endpoints, 0u, &source) != ET_WRAP_STATUS_OK) ||
        (translate_set(config->destination_endpoints, 0u, &destination) != ET_WRAP_STATUS_OK) ||
        (translate_set(config->irq_enabled_endpoints, 0u, &irq) != ET_WRAP_STATUS_OK))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    mode = ack_modes[config->ack_mode] | link_modes[config->link_mode];

    return from_driver(IPCM_testConfigureMailboxes(config->first_mailbox, config->mailbox_count,
                                                   source, destination, mode, irq));
}

/**
 * @brief Release only the requested mailbox range.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] first First mailbox.
 * @param[in] count Total members.
 * @note Does not reset the controller or synthesize cleared configuration.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_mailbox_release(et_ipcm_id_t ipcm_id, uint16_t first, uint16_t count)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testReleaseMailboxes(first, count));
}

/**
 * @brief Read a mailbox and translate physical channel sets to logical endpoints.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox index.
 * @param[out] snapshot Actual route, mode and IRQ-enable readback.
 * @note No pending state is cleared; hardware configuration is not inferred from requests.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_mailbox_snapshot_get(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                                   et_ipcm_wrap_mailbox_snapshot_t *snapshot)
{
    IPCM_TestMailboxSnapshot actual;
    DRV_Status status;

    if (!instance_exists(ipcm_id) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = IPCM_testGetMailboxSnapshot(mailbox, &actual);

    if (status != DRV_OK)
    {
        return from_driver(status);
    }

    if ((translate_set(actual.source, 1u, &snapshot->source_endpoints) != ET_WRAP_STATUS_OK) ||
        (translate_set(actual.destination, 1u, &snapshot->destination_endpoints) !=
         ET_WRAP_STATUS_OK) ||
        (translate_set(actual.interruptEnable, 1u, &snapshot->irq_enabled_endpoints) !=
         ET_WRAP_STATUS_OK))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    snapshot->ack_mode = (actual.mode & ack_modes[ET_IPCM_WRAP_ACK_AUTO]) ? ET_IPCM_WRAP_ACK_AUTO
                                                                          : ET_IPCM_WRAP_ACK_MANUAL;
    snapshot->link_mode = (actual.mode & link_modes[ET_IPCM_WRAP_LINK_CHAIN])
                              ? ET_IPCM_WRAP_LINK_CHAIN
                              : ET_IPCM_WRAP_LINK_SINGLE;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read complete live pending mailbox sets for one logical endpoint.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] endpoint Logical event endpoint.
 * @param[out] snapshot Raw and masked pending mailbox sets.
 * @note Read-only, not an event latch; caller must capture before clearing hardware.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_pending_snapshot_get(et_ipcm_id_t ipcm_id, uint16_t endpoint,
                                                   et_ipcm_wrap_pending_snapshot_t *snapshot)
{
    const et_ipcm_endpoint_mapping_t *mapping = find_endpoint(endpoint);
    IPCM_TestPendingSnapshot actual;
    DRV_Status status;

    if (!instance_exists(ipcm_id) || (mapping == NULL) || (snapshot == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = IPCM_testGetPendingSnapshot(mapping->channel, &actual);

    if (status != DRV_OK)
    {
        return from_driver(status);
    }

    snapshot->raw_pending = actual.raw;
    snapshot->masked_pending = actual.masked;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Prepare exact payload bytes without triggering SEND.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] first First mailbox in the configured chain.
 * @param[in] count Total configured members.
 * @param[in] data Byte-addressable source.
 * @param[in] length Valid bytes, with no silent truncation.
 * @note Writes only IPCM data registers through the own Driver.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_payload_write(et_ipcm_id_t ipcm_id, uint16_t first, uint16_t count,
                                            const uint8_t *data, uint16_t length)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testWritePayloadExact(first, count, data, length));
}

/**
 * @brief Read exact payload bytes without acknowledging them.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox holding the data.
 * @param[out] data Caller-owned byte buffer.
 * @param[in] length Valid byte count.
 * @note No ACK, release, clearing or payload comparison is performed.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_payload_read(et_ipcm_id_t ipcm_id, uint16_t mailbox, uint8_t *data,
                                           uint16_t length)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testReadPayloadExact(mailbox, data, length));
}

/**
 * @brief Trigger the prepared message toward its destinations.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox First mailbox of the message.
 * @note Executes SEND only; no polling, ACK or expected-data comparison.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_message_send(et_ipcm_id_t ipcm_id, uint16_t mailbox)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testSendMessage(mailbox));
}

/**
 * @brief Issue explicit ACK without changing MANUAL/AUTO selection.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox being acknowledged.
 * @note Does not release any destination or rewrite payload.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_ack_send(et_ipcm_id_t ipcm_id, uint16_t mailbox)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testSendAck(mailbox));
}

/**
 * @brief Clear the current message or ACK pending state only.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox to clear.
 * @note Does not trigger ACK or release destination routes.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_interrupt_clear(et_ipcm_id_t ipcm_id, uint16_t mailbox)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return from_driver(IPCM_testClearPending(mailbox));
}

/**
 * @brief Release precisely one logical destination endpoint.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox to update.
 * @param[in] endpoint Destination endpoint to release.
 * @note In AUTO mode the hardware may generate ACK; this wrapper does not generate one itself.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_destination_release(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                                  uint16_t endpoint)
{
    const et_ipcm_endpoint_mapping_t *mapping = find_endpoint(endpoint);

    if (!instance_exists(ipcm_id) || (mapping == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(IPCM_testReleaseDestination(mailbox, mapping->channel));
}

/**
 * @brief Change only the own-IP IRQ enable for one endpoint and mailbox.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] mailbox Mailbox to update.
 * @param[in] endpoint Event endpoint.
 * @param[in] enabled Canonical Boolean.
 * @note Raw pending is preserved; NVIC and route binding remain IRQ Manager-owned.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_irq_delivery_set(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                               uint16_t endpoint, uint8_t enabled)
{
    const et_ipcm_endpoint_mapping_t *mapping = find_endpoint(endpoint);

    if (!instance_exists(ipcm_id) || (mapping == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(IPCM_testSetInterruptDelivery(mailbox, mapping->channel, enabled));
}

/**
 * @brief Resolve a logical endpoint to an IRQ Manager route.
 * @param[in] ipcm_id Logical controller identifier.
 * @param[in] endpoint Event endpoint.
 * @param[out] route Physical route for internal Service binding only.
 * @note Does not register callbacks, touch NVIC or enable an interrupt source.
 * @return Stable Wrap status.
 */
et_wrap_status_t et_ipcm_wrap_irq_route_get(et_ipcm_id_t ipcm_id, uint16_t endpoint,
                                            et_irq_route_t *route)
{
    const et_ipcm_endpoint_mapping_t *mapping = find_endpoint(endpoint);

    if (!instance_exists(ipcm_id) || (mapping == NULL) || (route == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = mapping->irq_line;
    route->reserved = 0u;
    route->route_events = 1u << endpoint;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Queue one atomic command for the mapped IPCM peer executor.
 * @param[in] ipcm_id Logical controller.
 * @param[in] command IPCM local command selected by Service.
 * @param[in] data Encoded body; NULL only when empty.
 * @param[in] length Body byte length.
 * @param[out] sequence Peer execution ticket.
 * @note Does not execute the IP command locally or wait for the peer.
 * @return Stable submission status; errors never create a successful ticket.
 */
et_wrap_status_t et_ipcm_wrap_peer_submit(et_ipcm_id_t ipcm_id, uint16_t command,
                                          const uint8_t *data, uint16_t length, uint32_t *sequence)
{
    if (!instance_exists(ipcm_id) || (length > ET_IPCM_WRAP_PEER_BYTES))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(IPCM_testPeerSubmit(command, data, length, sequence));
}

/**
 * @brief Return peer execution state and an immutable completed response.
 * @param[in] ipcm_id Logical controller.
 * @param[out] result Peer identity, ticket, state and valid response bytes.
 * @note Queued/idle states contain no old response; hardware message data is not synthesized.
 * @return Stable status; a missing or wrong peer image is an execution error.
 */
et_wrap_status_t et_ipcm_wrap_peer_result(et_ipcm_id_t ipcm_id, et_ipcm_wrap_peer_result_t *result)
{
    IPCM_TestPeerResult native;
    et_wrap_status_t status;

    if (!instance_exists(ipcm_id) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = from_driver(IPCM_testPeerResult(&native));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (native.length > sizeof(result->data))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    switch (native.state)
    {
        case IPCM_TEST_PEER_IDLE:
        {
            result->state = ET_IPCM_PEER_IDLE;
            break;
        }

        case IPCM_TEST_PEER_QUEUED:
        {
            result->state = ET_IPCM_PEER_QUEUED;
            break;
        }

        case IPCM_TEST_PEER_DONE:
        {
            result->state = ET_IPCM_PEER_DONE;
            break;
        }

        case IPCM_TEST_PEER_CANCELLED:
        {
            result->state = ET_IPCM_PEER_CANCELLED;
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
            {
            }
    }

    result->sequence = native.sequence;
    result->executor_identity = native.coreId;
    result->heartbeat = native.heartbeat;
    result->status = native.status;
    result->length = native.length;
    (void)memcpy(result->data, native.data, native.length);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Ask the peer to cancel capture sessions through its own Service.
 * @param[in] ipcm_id Logical controller.
 * @param[out] sequence Cancellation ticket to await before a shared-IP reset.
 * @note Submission is not cancellation completion and cannot undo executed hardware writes.
 * @return Stable status; caller must query the returned ticket to confirm completion.
 */
et_wrap_status_t et_ipcm_wrap_peer_cancel(et_ipcm_id_t ipcm_id, uint32_t *sequence)
{
    if (!instance_exists(ipcm_id))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return from_driver(IPCM_testPeerCancel(sequence));
}
