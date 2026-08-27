#ifndef ET_AES_SERVICE_H
#define ET_AES_SERVICE_H

/**
 * @file et_aes_service.h
 * @brief AES Service command IDs and bounded per-instance runtime state.
 *
 * AES Service returns hardware facts only. Resource lookup is limited to
 * trusted Resource Wrap handles; no test case or final verdict is retained.
 */

#include <stdint.h>

#include "et_aes_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_resource_wrap.h"
#include "et_service_router.h"

#define ET_AES_SERVICE_ID 0x0103u
#define ET_AES_SERVICE_API_VERSION 1u
#define ET_AES_SERVICE_CAPABILITIES_SIZE 32u

/* Wire body sizes defined by the public AES command contract, in bytes. */
#define ET_AES_SERVICE_CONFIG_REQUEST_SIZE 12u
#define ET_AES_SERVICE_KEY_REQUEST_SIZE 36u
#define ET_AES_SERVICE_IV_BODY_SIZE ET_AES_WRAP_BLOCK_SIZE
#define ET_AES_SERVICE_LENGTH_BODY_SIZE 8u
#define ET_AES_SERVICE_PROCESS_REQUEST_SIZE 20u
#define ET_AES_SERVICE_STATUS_RESPONSE_SIZE 8u
#define ET_AES_SERVICE_IRQ_SNAPSHOT_RESPONSE_SIZE 28u
#define ET_AES_SERVICE_PROCESS_RESPONSE_SIZE 12u
#define ET_AES_SERVICE_IRQ_TRANSFER_STATUS_RESPONSE_SIZE 24u
#define ET_AES_SERVICE_TIMED_RESPONSE_SIZE 16u

/* Fixed field offsets in the AES process/resource request body. */
#define ET_AES_SERVICE_SOURCE_HANDLE_OFFSET 0u
#define ET_AES_SERVICE_SOURCE_OFFSET_OFFSET 4u
#define ET_AES_SERVICE_DESTINATION_HANDLE_OFFSET 8u
#define ET_AES_SERVICE_DESTINATION_OFFSET_OFFSET 12u
#define ET_AES_SERVICE_LOGICAL_LENGTH_OFFSET 16u

/* Fixed AES CONFIGURE body offsets. */
#define ET_AES_SERVICE_CONFIG_DIRECTION_OFFSET 0u
#define ET_AES_SERVICE_CONFIG_KEY_SIZE_OFFSET 1u
#define ET_AES_SERVICE_CONFIG_MODE_OFFSET 2u
#define ET_AES_SERVICE_CONFIG_PADDING_OFFSET 3u
#define ET_AES_SERVICE_CONFIG_ENDIAN_OFFSET 4u
#define ET_AES_SERVICE_CONFIG_DMA_MODE_OFFSET 5u
#define ET_AES_SERVICE_CONFIG_RESERVED_OFFSET 6u
#define ET_AES_SERVICE_CONFIG_COUNTER_OFFSET 8u

/* Fixed AES KEY_SET body offsets and the zero-tail rule for a 128-bit key. */
#define ET_AES_SERVICE_KEY_SIZE_OFFSET 0u
#define ET_AES_SERVICE_KEY_RESERVED_OFFSET 1u
#define ET_AES_SERVICE_KEY_RESERVED_SIZE 3u
#define ET_AES_SERVICE_KEY_MATERIAL_OFFSET 4u
#define ET_AES_SERVICE_KEY_128_TAIL_OFFSET                                                         \
    (ET_AES_SERVICE_KEY_MATERIAL_OFFSET + ET_AES_WRAP_KEY_128_BYTES)
#define ET_AES_SERVICE_KEY_128_TAIL_SIZE ET_AES_WRAP_KEY_128_BYTES

/* Common one-word request size and response word offsets. */
#define ET_AES_SERVICE_U32_BODY_SIZE ((uint16_t)sizeof(uint32_t))
#define ET_AES_SERVICE_WORD_OFFSET(index) ((uint16_t)((index) * sizeof(uint32_t)))

/* Byte fields following the first word in STATUS/PROCESS responses. */
#define ET_AES_SERVICE_PROCESS_BUSY_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)
#define ET_AES_SERVICE_PROCESS_DATA_IN_OFFSET (ET_AES_SERVICE_PROCESS_BUSY_OFFSET + 1u)
#define ET_AES_SERVICE_PROCESS_DATA_OUT_OFFSET (ET_AES_SERVICE_PROCESS_BUSY_OFFSET + 2u)
#define ET_AES_SERVICE_PROCESS_FINISH_OFFSET (ET_AES_SERVICE_PROCESS_BUSY_OFFSET + 3u)
#define ET_AES_SERVICE_PROCESS_RESERVED_OFFSET ET_AES_SERVICE_WORD_OFFSET(2u)

/* Two complete blocks are carried by the pair-only Test Driver Extension command. */
#define ET_AES_SERVICE_BLOCK_PAIR_SIZE (2u * ET_AES_WRAP_BLOCK_SIZE)

/* CAPABILITIES_GET response offsets. */
#define ET_AES_SERVICE_CAP_API_VERSION_OFFSET 0u
#define ET_AES_SERVICE_CAP_STRUCT_SIZE_OFFSET 2u
#define ET_AES_SERVICE_CAP_FEATURE_FLAGS_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)
#define ET_AES_SERVICE_CAP_BLOCK_SIZE_OFFSET ET_AES_SERVICE_WORD_OFFSET(2u)
#define ET_AES_SERVICE_CAP_LENGTH_BITS_OFFSET ET_AES_SERVICE_WORD_OFFSET(3u)
#define ET_AES_SERVICE_CAP_MAX_PROCESS_OFFSET ET_AES_SERVICE_WORD_OFFSET(4u)
#define ET_AES_SERVICE_CAP_MAX_OUTPUT_OFFSET ET_AES_SERVICE_WORD_OFFSET(5u)
#define ET_AES_SERVICE_CAP_KEY_MASK_OFFSET 24u
#define ET_AES_SERVICE_CAP_MODE_MASK_OFFSET 25u
#define ET_AES_SERVICE_CAP_PADDING_MASK_OFFSET 26u
#define ET_AES_SERVICE_CAP_ENDIAN_MASK_OFFSET 27u
#define ET_AES_SERVICE_CAP_DMA_MASK_OFFSET 28u
#define ET_AES_SERVICE_CAP_IRQ_MASK_OFFSET 29u
#define ET_AES_SERVICE_CAP_IRQ_TRANSFER_OFFSET 30u
#define ET_AES_SERVICE_CAP_TIMED_OFFSET 31u

/* STATUS_GET response byte offsets. */
#define ET_AES_SERVICE_STATUS_BUSY_OFFSET 0u
#define ET_AES_SERVICE_STATUS_DATA_IN_OFFSET 1u
#define ET_AES_SERVICE_STATUS_DATA_OUT_OFFSET 2u
#define ET_AES_SERVICE_STATUS_FINISH_OFFSET 3u
#define ET_AES_SERVICE_STATUS_RESERVED_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)

/* IRQ_SNAPSHOT_GET response word offsets. */
#define ET_AES_SERVICE_IRQ_SNAPSHOT_RAW_OFFSET ET_AES_SERVICE_WORD_OFFSET(0u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_STATUS_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_LATCHED_OFFSET ET_AES_SERVICE_WORD_OFFSET(2u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_EVENT_COUNT_OFFSET ET_AES_SERVICE_WORD_OFFSET(3u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_UNEXPECTED_COUNT_OFFSET ET_AES_SERVICE_WORD_OFFSET(4u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_OVERFLOW_COUNT_OFFSET ET_AES_SERVICE_WORD_OFFSET(5u)
#define ET_AES_SERVICE_IRQ_SNAPSHOT_GENERATION_OFFSET ET_AES_SERVICE_WORD_OFFSET(6u)

/* IRQ_TRANSFER_STATUS_GET response word offsets. */
#define ET_AES_SERVICE_IRQ_TRANSFER_STATE_OFFSET ET_AES_SERVICE_WORD_OFFSET(0u)
#define ET_AES_SERVICE_IRQ_TRANSFER_INPUT_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)
#define ET_AES_SERVICE_IRQ_TRANSFER_OUTPUT_OFFSET ET_AES_SERVICE_WORD_OFFSET(2u)
#define ET_AES_SERVICE_IRQ_TRANSFER_PRODUCED_OFFSET ET_AES_SERVICE_WORD_OFFSET(3u)
#define ET_AES_SERVICE_IRQ_TRANSFER_FAULT_OFFSET ET_AES_SERVICE_WORD_OFFSET(4u)
#define ET_AES_SERVICE_IRQ_TRANSFER_BLOCK_COUNT_OFFSET ET_AES_SERVICE_WORD_OFFSET(5u)

/* TIMED_PROCESS response word offsets. */
#define ET_AES_SERVICE_TIMED_CYCLES_OFFSET ET_AES_SERVICE_WORD_OFFSET(0u)
#define ET_AES_SERVICE_TIMED_PRODUCED_OFFSET ET_AES_SERVICE_WORD_OFFSET(1u)
#define ET_AES_SERVICE_TIMED_MEASURED_OFFSET ET_AES_SERVICE_WORD_OFFSET(2u)
#define ET_AES_SERVICE_TIMED_STATUS_OFFSET ET_AES_SERVICE_WORD_OFFSET(3u)
/* Bit meanings packed into the TIMED_PROCESS status word. */
#define ET_AES_SERVICE_TIMED_STATUS_BUSY (1u << 0)
#define ET_AES_SERVICE_TIMED_STATUS_DATA_IN (1u << 1)
#define ET_AES_SERVICE_TIMED_STATUS_DATA_OUT (1u << 2)
#define ET_AES_SERVICE_TIMED_STATUS_FINISH (1u << 3)

/* Bounded polling budget used only while disabling an active IRQ session. */
#define ET_AES_SERVICE_DISABLE_IRQ_SETTLE_BUDGET 1000000u

/* Event groups used by the bounded AES IRQ transfer state machine. */
#define ET_AES_SERVICE_IRQ_TRANSFER_REQUIRED                                                       \
    (ET_AES_WRAP_IRQ_DATA_IN_REQ | ET_AES_WRAP_IRQ_DATA_OUT_REQ | ET_AES_WRAP_IRQ_COMPLETE)
#define ET_AES_SERVICE_IRQ_REQUEST_EVENTS                                                          \
    (ET_AES_WRAP_IRQ_DATA_IN_REQ | ET_AES_WRAP_IRQ_DATA_OUT_REQ)
#define ET_AES_SERVICE_IRQ_TRANSFER_FAULT_EVENTS                                                   \
    (ET_AES_WRAP_IRQ_OUTPUT_CONFLICT | ET_AES_WRAP_IRQ_KEY_MISSING | ET_AES_WRAP_IRQ_IV_MISSING |  \
     ET_AES_WRAP_IRQ_INCOMPLETE_DISABLE)

typedef enum
{
    ET_AES_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_AES_COMMAND_ENABLE = 0x0002u,
    ET_AES_COMMAND_DISABLE = 0x0003u,
    ET_AES_COMMAND_CONFIGURE = 0x0004u,
    ET_AES_COMMAND_KEY_SET = 0x0005u,
    ET_AES_COMMAND_IV_SET = 0x0006u,
    ET_AES_COMMAND_IV_GET = 0x0007u,
    ET_AES_COMMAND_DATA_LENGTH_SET = 0x0008u,
    ET_AES_COMMAND_DATA_LENGTH_GET = 0x0009u,
    ET_AES_COMMAND_PROCESS = 0x000au,
    ET_AES_COMMAND_STATUS_GET = 0x000bu,
    ET_AES_COMMAND_STATUS_CLEAR = 0x000cu,
    ET_AES_COMMAND_IRQ_ENABLE = 0x000du,
    ET_AES_COMMAND_IRQ_DISABLE = 0x000eu,
    ET_AES_COMMAND_IRQ_MASK = 0x000fu,
    ET_AES_COMMAND_IRQ_UNMASK = 0x0010u,
    ET_AES_COMMAND_IRQ_FORCE = 0x0011u,
    ET_AES_COMMAND_IRQ_CLEAR = 0x0012u,
    ET_AES_COMMAND_IRQ_SNAPSHOT_GET = 0x0013u,
    ET_AES_COMMAND_DMA_REQUEST_SET = 0x0014u,
    ET_AES_COMMAND_IRQ_TRANSFER_START = 0x0015u,
    ET_AES_COMMAND_IRQ_TRANSFER_STATUS_GET = 0x0016u,
    ET_AES_COMMAND_IRQ_TRANSFER_ABORT = 0x0017u,
    ET_AES_COMMAND_TIMED_PROCESS = 0x0018u,
    ET_AES_COMMAND_BLOCK_WRITE = 0x0019u,
    ET_AES_COMMAND_BLOCK_READ = 0x001au,
    ET_AES_COMMAND_BLOCK_WRITE_DIRECT = 0x001bu,
    ET_AES_COMMAND_BLOCK_WRITE_PAIR_DIRECT = 0x001cu,
    ET_AES_COMMAND_BLOCK_WRITE_DISABLE_DIRECT = 0x001du
} et_aes_command_t;

typedef enum
{
    ET_AES_IRQ_TRANSFER_IDLE = 0u,
    ET_AES_IRQ_TRANSFER_ACTIVE = 1u,
    ET_AES_IRQ_TRANSFER_COMPLETE = 2u,
    ET_AES_IRQ_TRANSFER_ABORTED = 3u,
    ET_AES_IRQ_TRANSFER_FAULT = 4u
} et_aes_irq_transfer_state_t;

typedef struct
{
    et_aes_id_t aes_id;
    uint8_t enabled;
    uint8_t configured;
    uint8_t irq_bound;
    uint8_t irq_priority;
    uint32_t enabled_events;
    uint32_t masked_events;
    volatile uint32_t latched_events;
    volatile uint32_t event_count;
    volatile uint32_t unexpected_count;
    volatile uint32_t overflow_count;
    volatile uint32_t generation;
    uint8_t *irq_source;
    uint8_t *irq_destination;
    uint32_t irq_source_size;
    uint32_t irq_destination_size;
    uint32_t irq_logical_length;
    uint32_t irq_expected_bytes;
    uint32_t irq_input_offset;
    uint32_t irq_output_offset;
    uint32_t irq_produced_bytes;
    uint32_t irq_fault_flags;
    uint32_t irq_block_count;
    uint8_t irq_state;
    et_aes_wrap_config_t config;
    et_aes_wrap_capabilities_t capabilities;
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_route;
    et_service_descriptor_t descriptor;
} et_aes_service_t;

int et_aes_service_init(et_aes_service_t *service, et_aes_id_t aes_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority);

const et_service_descriptor_t *et_aes_service_descriptor(const et_aes_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/** Create one AES Service through the chip-neutral group registry contract. */
int et_aes_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
