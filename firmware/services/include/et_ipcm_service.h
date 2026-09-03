#ifndef ET_IPCM_SERVICE_H
#define ET_IPCM_SERVICE_H

/** @file et_ipcm_service.h @brief IPCM V1 Wire fields and bounded event capture. */
#include "et_ipcm_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_service_router.h"

/** Allocated IPCM service identity; existing IP service IDs are unchanged. */
#define ET_IPCM_SERVICE_ID 0x0109u
#define ET_IPCM_SERVICE_API_VERSION 1u
/** Software observation storage, not hardware mailbox/endpoint capacities. */
#define ET_IPCM_SERVICE_CAPTURE_SLOTS 4u
#define ET_IPCM_SERVICE_CAPTURE_BYTES 128u
/** Little-endian Wire widths and packed-body offsets; sizes are bytes. */
#define ET_IPCM_SERVICE_BYTE_MASK 0xffu
#define ET_IPCM_SERVICE_U16_BYTES 2u
#define ET_IPCM_SERVICE_U32_BYTES 4u
#define ET_IPCM_SERVICE_ID_SIZE 2u
#define ET_IPCM_SERVICE_PAIR_SIZE 4u
#define ET_IPCM_SERVICE_CAPS_SIZE 16u
#define ET_IPCM_SERVICE_CAPS_VERSION 0u
#define ET_IPCM_SERVICE_CAPS_SIZE_FIELD 2u
#define ET_IPCM_SERVICE_CAPS_MAILBOXES 4u
#define ET_IPCM_SERVICE_CAPS_CHANNELS 6u
#define ET_IPCM_SERVICE_CAPS_DATA_WORDS 8u
#define ET_IPCM_SERVICE_CAPS_PAYLOAD_BYTES 10u
#define ET_IPCM_SERVICE_CAPS_CAPTURE_SLOTS 12u
#define ET_IPCM_SERVICE_CAPS_CAPTURE_BYTES 14u
#define ET_IPCM_SERVICE_CONFIG_SIZE 20u
#define ET_IPCM_SERVICE_CONFIG_FIRST 0u
#define ET_IPCM_SERVICE_CONFIG_COUNT 2u
#define ET_IPCM_SERVICE_CONFIG_SOURCE 4u
#define ET_IPCM_SERVICE_CONFIG_DESTINATION 8u
#define ET_IPCM_SERVICE_CONFIG_IRQ 12u
#define ET_IPCM_SERVICE_CONFIG_ACK 16u
#define ET_IPCM_SERVICE_CONFIG_LINK 17u
#define ET_IPCM_SERVICE_CONFIG_RESERVED 18u
#define ET_IPCM_SERVICE_MAILBOX_SIZE 16u
#define ET_IPCM_SERVICE_MAILBOX_SOURCE 0u
#define ET_IPCM_SERVICE_MAILBOX_DESTINATION 4u
#define ET_IPCM_SERVICE_MAILBOX_IRQ 8u
#define ET_IPCM_SERVICE_MAILBOX_ACK 12u
#define ET_IPCM_SERVICE_MAILBOX_LINK 13u
#define ET_IPCM_SERVICE_MAILBOX_RESERVED 14u
#define ET_IPCM_SERVICE_PENDING_SIZE 8u
#define ET_IPCM_SERVICE_WRITE_HEADER_SIZE 6u
#define ET_IPCM_SERVICE_WRITE_FIRST 0u
#define ET_IPCM_SERVICE_WRITE_COUNT 2u
#define ET_IPCM_SERVICE_WRITE_LENGTH 4u
/** ARM = slot, endpoint, mailbox, valid length (u16), IRQ (u8), stage (u8). */
#define ET_IPCM_SERVICE_ARM_SIZE 10u
#define ET_IPCM_SERVICE_ARM_SLOT 0u
#define ET_IPCM_SERVICE_ARM_ENDPOINT 2u
#define ET_IPCM_SERVICE_ARM_MAILBOX 4u
#define ET_IPCM_SERVICE_ARM_LENGTH 6u
#define ET_IPCM_SERVICE_ARM_IRQ 8u
#define ET_IPCM_SERVICE_ARM_STAGE 9u
/** Caller-provided message/ACK identity; not an inferred hardware status bit. */
#define ET_IPCM_SERVICE_STAGE_MESSAGE 0u
#define ET_IPCM_SERVICE_STAGE_ACK 1u
/** Event header: eight u32 counters/sets plus five u16 identity/state fields. */
#define ET_IPCM_SERVICE_EVENT_HEADER_SIZE 42u
#define ET_IPCM_SERVICE_EVENT_GENERATION 0u
#define ET_IPCM_SERVICE_EVENT_RAW 4u
#define ET_IPCM_SERVICE_EVENT_MASKED 8u
#define ET_IPCM_SERVICE_EVENT_LATCHED 12u
#define ET_IPCM_SERVICE_EVENT_COUNT 16u
#define ET_IPCM_SERVICE_EVENT_UNEXPECTED 20u
#define ET_IPCM_SERVICE_EVENT_OVERFLOW 24u
#define ET_IPCM_SERVICE_EVENT_FAULT 28u
#define ET_IPCM_SERVICE_EVENT_ENDPOINT 32u
#define ET_IPCM_SERVICE_EVENT_MAILBOX 34u
#define ET_IPCM_SERVICE_EVENT_LENGTH 36u
#define ET_IPCM_SERVICE_EVENT_STATE 38u
#define ET_IPCM_SERVICE_EVENT_STAGE 40u
/** Capture faults are software execution facts, never hardware status bits. */
#define ET_IPCM_SERVICE_FAULT_READ (1u << 0)
#define ET_IPCM_SERVICE_FAULT_MASK (1u << 1)
#define ET_IPCM_SERVICE_FAULT_UNEXPECTED (1u << 2)
/** Peer result: ticket/state/status/length/reserved/executor/heartbeat, then bytes. */
#define ET_IPCM_SERVICE_PEER_HEADER_SIZE 20u
#define ET_IPCM_SERVICE_PEER_STATE_OFFSET 4u
#define ET_IPCM_SERVICE_PEER_STATUS_OFFSET 6u
#define ET_IPCM_SERVICE_PEER_LENGTH_OFFSET 8u
#define ET_IPCM_SERVICE_PEER_RESERVED_OFFSET 10u
#define ET_IPCM_SERVICE_PEER_EXECUTOR_OFFSET 12u
#define ET_IPCM_SERVICE_PEER_HEARTBEAT_OFFSET 16u

typedef enum
{
    ET_IPCM_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_IPCM_COMMAND_CONFIGURE = 0x0002u,
    ET_IPCM_COMMAND_MAILBOX_RELEASE = 0x0003u,
    ET_IPCM_COMMAND_MAILBOX_SNAPSHOT_GET = 0x0004u,
    ET_IPCM_COMMAND_PENDING_SNAPSHOT_GET = 0x0005u,
    ET_IPCM_COMMAND_PAYLOAD_WRITE = 0x0006u,
    ET_IPCM_COMMAND_PAYLOAD_READ = 0x0007u,
    ET_IPCM_COMMAND_MESSAGE_SEND = 0x0008u,
    ET_IPCM_COMMAND_ACK_SEND = 0x0009u,
    ET_IPCM_COMMAND_INTERRUPT_CLEAR = 0x000au,
    ET_IPCM_COMMAND_DESTINATION_RELEASE = 0x000bu,
    ET_IPCM_COMMAND_CAPTURE_ARM = 0x0010u,
    ET_IPCM_COMMAND_CAPTURE_GET = 0x0011u,
    ET_IPCM_COMMAND_CAPTURE_ABORT = 0x0012u,
    ET_IPCM_COMMAND_STATE_RESET = 0x0013u,
    ET_IPCM_COMMAND_PEER_SUBMIT = 0x0020u,
    ET_IPCM_COMMAND_PEER_RESULT = 0x0021u,
    ET_IPCM_COMMAND_PEER_CANCEL = 0x0022u
} et_ipcm_command_t;

typedef enum
{
    ET_IPCM_CAPTURE_IDLE = 0u,
    ET_IPCM_CAPTURE_WAITING = 1u,
    ET_IPCM_CAPTURE_READY = 2u,
    ET_IPCM_CAPTURE_FAULT = 3u
} et_ipcm_capture_state_t;

typedef struct
{
    uint32_t generation;
    uint32_t raw_status;
    uint32_t masked_status;
    uint32_t latched_events;
    uint32_t event_count;
    uint32_t unexpected_count;
    uint32_t overflow_count;
    uint32_t fault_flags;
    uint16_t endpoint;
    uint16_t mailbox;
    uint16_t length;
    uint16_t state;
    uint16_t stage;
    uint8_t payload[ET_IPCM_SERVICE_CAPTURE_BYTES];
} et_ipcm_capture_event_t;

typedef struct
{
    et_ipcm_id_t ipcm_id;
    et_irq_manager_t *irq_manager;
    et_irq_route_t route;
    uint8_t irq_bound;
    uint8_t irq_mode;
    uint8_t irq_priority;
    et_ipcm_capture_event_t event;
} et_ipcm_capture_slot_t;

typedef struct
{
    et_ipcm_id_t ipcm_id;
    et_irq_manager_t *irq_manager;
    uint8_t irq_priority;
    et_ipcm_capture_slot_t slots[ET_IPCM_SERVICE_CAPTURE_SLOTS];
    et_service_descriptor_t descriptor;
} et_ipcm_service_t;

int et_ipcm_service_init(et_ipcm_service_t *service, et_ipcm_id_t ipcm_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_ipcm_service_descriptor(const et_ipcm_service_t *service);
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_ipcm_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
