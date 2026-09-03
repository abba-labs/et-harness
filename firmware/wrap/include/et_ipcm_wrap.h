#ifndef ET_IPCM_WRAP_H
#define ET_IPCM_WRAP_H

/** @file et_ipcm_wrap.h @brief Chip-neutral mailbox actions, with no test policy. */
#include <stdint.h>
#include "et_irq_types.h"
#include "et_wrap_status.h"

typedef uint16_t et_ipcm_id_t;

/** Stable configuration version and logical-set width; not hardware counts. */
#define ET_IPCM_WRAP_API_VERSION 1u
#define ET_IPCM_WRAP_ENDPOINT_BITS 32u
#define ET_IPCM_WRAP_CONFIG_RESERVED_WORDS 2u

typedef enum
{
    ET_IPCM_WRAP_ACK_MANUAL = 0u,
    ET_IPCM_WRAP_ACK_AUTO = 1u
} et_ipcm_wrap_ack_mode_t;

typedef enum
{
    ET_IPCM_WRAP_LINK_SINGLE = 0u,
    ET_IPCM_WRAP_LINK_CHAIN = 1u
} et_ipcm_wrap_link_mode_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint16_t first_mailbox;
    uint16_t mailbox_count; /**< Total members including first_mailbox. */
    uint32_t source_endpoints;
    uint32_t destination_endpoints;
    uint32_t irq_enabled_endpoints;
    uint8_t ack_mode;
    uint8_t link_mode;
    uint16_t reserved16;
    uint32_t reserved[ET_IPCM_WRAP_CONFIG_RESERVED_WORDS];
} et_ipcm_wrap_config_t;

typedef struct
{
    uint16_t mailbox_count;
    uint16_t channel_count;
    uint16_t data_word_count;
    uint16_t mailbox_payload_bytes;
} et_ipcm_wrap_capabilities_t;

typedef struct
{
    uint32_t source_endpoints;
    uint32_t destination_endpoints;
    uint32_t irq_enabled_endpoints;
    uint8_t ack_mode;
    uint8_t link_mode;
} et_ipcm_wrap_mailbox_snapshot_t;

typedef struct
{
    uint32_t raw_pending;
    uint32_t masked_pending;
} et_ipcm_wrap_pending_snapshot_t;

et_wrap_status_t et_ipcm_wrap_capabilities_get(et_ipcm_id_t ipcm_id,
                                               et_ipcm_wrap_capabilities_t *capabilities);
et_wrap_status_t et_ipcm_wrap_configure(et_ipcm_id_t ipcm_id, const et_ipcm_wrap_config_t *config);
et_wrap_status_t et_ipcm_wrap_mailbox_release(et_ipcm_id_t ipcm_id, uint16_t first, uint16_t count);
et_wrap_status_t et_ipcm_wrap_mailbox_snapshot_get(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                                   et_ipcm_wrap_mailbox_snapshot_t *snapshot);
et_wrap_status_t et_ipcm_wrap_pending_snapshot_get(et_ipcm_id_t ipcm_id, uint16_t endpoint,
                                                   et_ipcm_wrap_pending_snapshot_t *snapshot);
et_wrap_status_t et_ipcm_wrap_payload_write(et_ipcm_id_t ipcm_id, uint16_t first, uint16_t count,
                                            const uint8_t *data, uint16_t length);
et_wrap_status_t et_ipcm_wrap_payload_read(et_ipcm_id_t ipcm_id, uint16_t mailbox, uint8_t *data,
                                           uint16_t length);
et_wrap_status_t et_ipcm_wrap_message_send(et_ipcm_id_t ipcm_id, uint16_t mailbox);
et_wrap_status_t et_ipcm_wrap_ack_send(et_ipcm_id_t ipcm_id, uint16_t mailbox);
et_wrap_status_t et_ipcm_wrap_interrupt_clear(et_ipcm_id_t ipcm_id, uint16_t mailbox);
et_wrap_status_t et_ipcm_wrap_destination_release(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                                  uint16_t endpoint);
et_wrap_status_t et_ipcm_wrap_irq_delivery_set(et_ipcm_id_t ipcm_id, uint16_t mailbox,
                                               uint16_t endpoint, uint8_t enabled);
et_wrap_status_t et_ipcm_wrap_irq_route_get(et_ipcm_id_t ipcm_id, uint16_t endpoint,
                                            et_irq_route_t *route);

/** Peer control storage budget in bytes; not the tested hardware payload capacity. */
#define ET_IPCM_WRAP_PEER_BYTES 512u
typedef enum
{
    ET_IPCM_PEER_IDLE = 0u,
    ET_IPCM_PEER_QUEUED = 1u,
    ET_IPCM_PEER_DONE = 2u,
    ET_IPCM_PEER_CANCELLED = 3u
} et_ipcm_peer_state_t;
typedef struct
{
    uint32_t sequence;
    uint32_t executor_identity;
    uint32_t heartbeat;
    uint16_t state;
    uint16_t status;
    uint16_t length;
    uint8_t data[ET_IPCM_WRAP_PEER_BYTES];
} et_ipcm_wrap_peer_result_t;
et_wrap_status_t et_ipcm_wrap_peer_submit(et_ipcm_id_t ipcm_id, uint16_t command,
                                          const uint8_t *data, uint16_t length, uint32_t *sequence);
et_wrap_status_t et_ipcm_wrap_peer_result(et_ipcm_id_t ipcm_id, et_ipcm_wrap_peer_result_t *result);
et_wrap_status_t et_ipcm_wrap_peer_cancel(et_ipcm_id_t ipcm_id, uint32_t *sequence);

#endif
