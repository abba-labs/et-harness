#ifndef ET_DMA_SERVICE_H
#define ET_DMA_SERVICE_H

/**
 * @file et_dma_service.h
 * @brief DMA command IDs and bounded controller/session ownership state.
 *
 * DMA Service owns only DMA controller/channel lifecycle and one managed IRQ
 * session. Cross-IP address, endpoint, route and lease decisions belong to PC.
 */

#include <stdint.h>

#include "et_dma_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_service_router.h"

#define ET_DMA_SERVICE_ID 0x0100u
#define ET_DMA_SERVICE_MAX_ROUTES 5u
#define ET_DMA_SERVICE_MAX_CHANNELS 32u

/* Wire body sizes defined by the public DMA command contract, in bytes. */
#define ET_DMA_SERVICE_CONFIG_REQUEST_SIZE 64u
#define ET_DMA_SERVICE_LLI_V1_REQUEST_SIZE 76u
#define ET_DMA_SERVICE_LLI_V2_REQUEST_SIZE 80u
#define ET_DMA_SERVICE_CAPABILITIES_RESPONSE_SIZE 20u
#define ET_DMA_SERVICE_CHANNEL_STATUS_RESPONSE_SIZE 8u
#define ET_DMA_SERVICE_TIMING_RESPONSE_SIZE 8u
#define ET_DMA_SERVICE_COMPONENT_RESPONSE_SIZE 48u
#define ET_DMA_SERVICE_INTERRUPT_RESPONSE_SIZE 64u
#define ET_DMA_SERVICE_CHANNEL_SNAPSHOT_RESPONSE_SIZE 52u

/* Both source and destination handshake modes occupy the low two bits. */
#define ET_DMA_SERVICE_HANDSHAKE_CONFIG_MASK 0x03u
/* All normalized DMA events accepted by IRQ commands. */
#define ET_DMA_SERVICE_ALL_IRQ_EVENTS                                                              \
    (ET_DMA_WRAP_IRQ_TRANSFER | ET_DMA_WRAP_IRQ_BLOCK | ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION |       \
     ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION | ET_DMA_WRAP_IRQ_ERROR)

/* Fixed CHANNEL_CONFIGURE request offsets. */
#define ET_DMA_SERVICE_CONFIG_CHANNEL_OFFSET 0u
#define ET_DMA_SERVICE_CONFIG_TRANSFER_TYPE_OFFSET 1u
#define ET_DMA_SERVICE_CONFIG_PRIORITY_OFFSET 2u
#define ET_DMA_SERVICE_CONFIG_SOURCE_WIDTH_OFFSET 3u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_WIDTH_OFFSET 4u
#define ET_DMA_SERVICE_CONFIG_SOURCE_ADDRESS_MODE_OFFSET 5u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_ADDRESS_MODE_OFFSET 6u
#define ET_DMA_SERVICE_CONFIG_SOURCE_BURST_OFFSET 7u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_BURST_OFFSET 8u
#define ET_DMA_SERVICE_CONFIG_FIFO_MODE_OFFSET 9u
#define ET_DMA_SERVICE_CONFIG_SOURCE_INTERFACE_OFFSET 10u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_INTERFACE_OFFSET 11u
#define ET_DMA_SERVICE_CONFIG_SOURCE_UPDATE_MODE_OFFSET 12u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_UPDATE_MODE_OFFSET 13u
#define ET_DMA_SERVICE_CONFIG_SOURCE_HANDSHAKE_OFFSET 14u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_HANDSHAKE_OFFSET 15u
#define ET_DMA_SERVICE_CONFIG_SOURCE_ADDRESS_OFFSET 16u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_ADDRESS_OFFSET 24u
#define ET_DMA_SERVICE_CONFIG_TRANSFER_COUNT_OFFSET 32u
#define ET_DMA_SERVICE_CONFIG_FLAGS_OFFSET 36u
#define ET_DMA_SERVICE_CONFIG_LINKED_LIST_OFFSET 40u
#define ET_DMA_SERVICE_CONFIG_SOURCE_GATHER_INTERVAL_OFFSET 48u
#define ET_DMA_SERVICE_CONFIG_SOURCE_GATHER_COUNT_OFFSET 52u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_SCATTER_INTERVAL_OFFSET 56u
#define ET_DMA_SERVICE_CONFIG_DESTINATION_SCATTER_COUNT_OFFSET 60u

/* Packed handshake selector bits inside the two handshake bytes. */
#define ET_DMA_SERVICE_HANDSHAKE_MODE_MASK (1u << 0)
#define ET_DMA_SERVICE_HANDSHAKE_POLARITY_MASK (1u << 1)
#define ET_DMA_SERVICE_HANDSHAKE_POLARITY_SHIFT 1u

/* Common one-word request body and coherent IRQ result read budget. */
#define ET_DMA_SERVICE_U32_BODY_SIZE ((uint16_t)sizeof(uint32_t))
#define ET_DMA_SERVICE_IRQ_RESULT_RESPONSE_SIZE 16u
#define ET_DMA_SERVICE_IRQ_RESULT_SNAPSHOT_ATTEMPTS 3u
#define ET_DMA_SERVICE_IRQ_CONFIG_REQUEST_SIZE 8u
#define ET_DMA_SERVICE_IRQ_CONFIG_RESPONSE_SIZE 8u
#define ET_DMA_SERVICE_INTERRUPT_CONTROL_REQUEST_SIZE 8u
#define ET_DMA_SERVICE_FREE_CHANNEL_RESPONSE_SIZE 4u

/* One-word channel/view requests use one value byte followed by zero padding. */
#define ET_DMA_SERVICE_SINGLE_VALUE_OFFSET 0u
#define ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_OFFSET 1u
#define ET_DMA_SERVICE_SINGLE_VALUE_RESERVED_SIZE 3u

/* Fixed field offsets used by the IRQ and LLI command bodies. */
#define ET_DMA_SERVICE_IRQ_EVENTS_OFFSET 0u
#define ET_DMA_SERVICE_IRQ_CHANNEL_OFFSET 4u
#define ET_DMA_SERVICE_IRQ_PRIORITY_OFFSET 5u
#define ET_DMA_SERVICE_IRQ_RESERVED_OFFSET 6u
#define ET_DMA_SERVICE_IRQ_RESERVED_SIZE 2u
#define ET_DMA_SERVICE_IRQ_RESPONSE_EVENTS_OFFSET 0u
#define ET_DMA_SERVICE_IRQ_RESPONSE_ROUTE_COUNT_OFFSET 4u
#define ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_OFFSET 5u
#define ET_DMA_SERVICE_IRQ_RESPONSE_RESERVED_SIZE 3u
#define ET_DMA_SERVICE_LLI_DESCRIPTOR_OFFSET ET_DMA_SERVICE_CONFIG_REQUEST_SIZE
#define ET_DMA_SERVICE_LLI_LAST_FLAG_OFFSET 72u
#define ET_DMA_SERVICE_LLI_RESERVED_OFFSET 73u
#define ET_DMA_SERVICE_LLI_RESERVED_SIZE 7u

/* SOFTWARE_HANDSHAKE_REQUEST_SET byte fields. */
#define ET_DMA_SERVICE_SOFTWARE_CHANNEL_OFFSET 0u
#define ET_DMA_SERVICE_SOFTWARE_TARGET_OFFSET 1u
#define ET_DMA_SERVICE_SOFTWARE_REQUEST_OFFSET 2u
#define ET_DMA_SERVICE_SOFTWARE_ACTIVE_OFFSET 3u

/* Snapshot response layout is derived from public Wrap array dimensions. */
#define ET_DMA_SERVICE_WIRE_WORD_SIZE ((uint16_t)sizeof(uint32_t))
#define ET_DMA_SERVICE_WORD_OFFSET(index) ((uint16_t)((index) * ET_DMA_SERVICE_WIRE_WORD_SIZE))
#define ET_DMA_SERVICE_CAP_FEATURES_OFFSET ET_DMA_SERVICE_WORD_OFFSET(0u)
#define ET_DMA_SERVICE_CAP_CHANNEL_COUNT_OFFSET 4u
#define ET_DMA_SERVICE_CAP_MAX_TRANSFER_OFFSET 6u
#define ET_DMA_SERVICE_CAP_MAX_INTERVAL_OFFSET ET_DMA_SERVICE_WORD_OFFSET(2u)
#define ET_DMA_SERVICE_CAP_MAX_COUNT_OFFSET ET_DMA_SERVICE_WORD_OFFSET(3u)
#define ET_DMA_SERVICE_CAP_IRQ_EVENTS_OFFSET ET_DMA_SERVICE_WORD_OFFSET(4u)
#define ET_DMA_SERVICE_TIMING_COMPLETE_OFFSET 0u
#define ET_DMA_SERVICE_TIMING_CHANNEL_OFFSET 1u
#define ET_DMA_SERVICE_TIMING_ELAPSED_OFFSET ET_DMA_SERVICE_WORD_OFFSET(1u)
#define ET_DMA_SERVICE_FREE_CHANNEL_ID_OFFSET 0u
#define ET_DMA_SERVICE_IRQ_RESULT_EVENTS_OFFSET ET_DMA_SERVICE_WORD_OFFSET(0u)
#define ET_DMA_SERVICE_IRQ_RESULT_COUNT_OFFSET ET_DMA_SERVICE_WORD_OFFSET(1u)
#define ET_DMA_SERVICE_IRQ_RESULT_UNEXPECTED_OFFSET ET_DMA_SERVICE_WORD_OFFSET(2u)
#define ET_DMA_SERVICE_IRQ_RESULT_OVERFLOW_OFFSET ET_DMA_SERVICE_WORD_OFFSET(3u)
#define ET_DMA_SERVICE_CHANNEL_STATUS_FREE_OFFSET 0u
#define ET_DMA_SERVICE_CHANNEL_STATUS_FIFO_EMPTY_OFFSET 1u
#define ET_DMA_SERVICE_CHANNEL_STATUS_RESERVED_OFFSET 2u
#define ET_DMA_SERVICE_CHANNEL_STATUS_RESERVED_SIZE 2u
#define ET_DMA_SERVICE_CHANNEL_STATUS_INTERRUPTS_OFFSET ET_DMA_SERVICE_WORD_OFFSET(1u)
#define ET_DMA_SERVICE_COMPONENT_DMA_ID_OFFSET ET_DMA_SERVICE_WORD_OFFSET(0u)
#define ET_DMA_SERVICE_COMPONENT_ID_OFFSET ET_DMA_SERVICE_WORD_OFFSET(1u)
#define ET_DMA_SERVICE_COMPONENT_CHANNELS_OFFSET (2u * ET_DMA_SERVICE_WIRE_WORD_SIZE)
#define ET_DMA_SERVICE_COMPONENT_MULTI_BLOCK_OFFSET                                                \
    (ET_DMA_SERVICE_COMPONENT_CHANNELS_OFFSET +                                                    \
     (ET_DMA_WRAP_COMPONENT_CHANNEL_PARAMETER_COUNT * ET_DMA_SERVICE_WIRE_WORD_SIZE))
#define ET_DMA_SERVICE_COMPONENT_MAX_BLOCK_OFFSET                                                  \
    (ET_DMA_SERVICE_COMPONENT_MULTI_BLOCK_OFFSET + ET_DMA_SERVICE_WIRE_WORD_SIZE)
#define ET_DMA_SERVICE_INTERRUPT_RAW_OFFSET 0u
#define ET_DMA_SERVICE_INTERRUPT_STATUS_OFFSET                                                     \
    (ET_DMA_WRAP_IRQ_SLOT_COUNT * ET_DMA_SERVICE_WIRE_WORD_SIZE)
#define ET_DMA_SERVICE_INTERRUPT_MASK_OFFSET                                                       \
    (2u * ET_DMA_WRAP_IRQ_SLOT_COUNT * ET_DMA_SERVICE_WIRE_WORD_SIZE)
#define ET_DMA_SERVICE_INTERRUPT_COMBINED_OFFSET                                                   \
    (3u * ET_DMA_WRAP_IRQ_SLOT_COUNT * ET_DMA_SERVICE_WIRE_WORD_SIZE)

/* CHANNEL_SNAPSHOT_GET response word offsets. */
#define ET_DMA_SERVICE_CHANNEL_SOURCE_OFFSET ET_DMA_SERVICE_WORD_OFFSET(0u)
#define ET_DMA_SERVICE_CHANNEL_DESTINATION_OFFSET ET_DMA_SERVICE_WORD_OFFSET(1u)
#define ET_DMA_SERVICE_CHANNEL_LLI_OFFSET ET_DMA_SERVICE_WORD_OFFSET(2u)
#define ET_DMA_SERVICE_CHANNEL_CONTROL_LOW_OFFSET ET_DMA_SERVICE_WORD_OFFSET(3u)
#define ET_DMA_SERVICE_CHANNEL_CONTROL_HIGH_OFFSET ET_DMA_SERVICE_WORD_OFFSET(4u)
#define ET_DMA_SERVICE_CHANNEL_CONFIG_LOW_OFFSET ET_DMA_SERVICE_WORD_OFFSET(5u)
#define ET_DMA_SERVICE_CHANNEL_CONFIG_HIGH_OFFSET ET_DMA_SERVICE_WORD_OFFSET(6u)
#define ET_DMA_SERVICE_CHANNEL_SOURCE_GATHER_OFFSET ET_DMA_SERVICE_WORD_OFFSET(7u)
#define ET_DMA_SERVICE_CHANNEL_DESTINATION_SCATTER_OFFSET ET_DMA_SERVICE_WORD_OFFSET(8u)
#define ET_DMA_SERVICE_CHANNEL_SOURCE_BURST_OFFSET ET_DMA_SERVICE_WORD_OFFSET(9u)
#define ET_DMA_SERVICE_CHANNEL_DESTINATION_BURST_OFFSET ET_DMA_SERVICE_WORD_OFFSET(10u)
#define ET_DMA_SERVICE_CHANNEL_BLOCK_SIZE_OFFSET ET_DMA_SERVICE_WORD_OFFSET(11u)
#define ET_DMA_SERVICE_CHANNEL_FIFO_MODE_OFFSET ET_DMA_SERVICE_WORD_OFFSET(12u)

typedef enum
{
    ET_DMA_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_DMA_COMMAND_CONTROLLER_ENABLE = 0x0002u,
    ET_DMA_COMMAND_CONTROLLER_DISABLE = 0x0003u,
    ET_DMA_COMMAND_CHANNEL_CONFIGURE = 0x0004u,
    ET_DMA_COMMAND_CHANNEL_DECONFIGURE = 0x0005u,
    ET_DMA_COMMAND_CHANNEL_START = 0x0006u,
    ET_DMA_COMMAND_CHANNEL_STOP = 0x0007u,
    ET_DMA_COMMAND_CHANNEL_STATUS_GET = 0x0008u,
    ET_DMA_COMMAND_IRQ_ENABLE = 0x0009u,
    ET_DMA_COMMAND_IRQ_DISABLE = 0x000au,
    ET_DMA_COMMAND_IRQ_RESULT_GET = 0x000bu,
    ET_DMA_COMMAND_IRQ_RESULT_CLEAR = 0x000cu,
    ET_DMA_COMMAND_CHANNEL_SUSPEND = 0x000du,
    ET_DMA_COMMAND_CHANNEL_RESUME = 0x000eu,
    ET_DMA_COMMAND_FREE_CHANNEL_FIND = 0x000fu,
    ET_DMA_COMMAND_CHANNELS_START = 0x0010u,
    ET_DMA_COMMAND_COMPONENT_SNAPSHOT_GET = 0x0011u,
    ET_DMA_COMMAND_INTERRUPT_SNAPSHOT_GET = 0x0012u,
    ET_DMA_COMMAND_CHANNEL_SNAPSHOT_GET = 0x0013u,
    /* Deprecated: Resource Handle + Offset contract is no longer executed. */
    ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT = 0x0014u,
    ET_DMA_COMMAND_INTERRUPT_MASK_ENABLE = 0x0015u,
    ET_DMA_COMMAND_INTERRUPT_MASK_DISABLE = 0x0016u,
    ET_DMA_COMMAND_INTERRUPT_PENDING_CLEAR = 0x0017u,
    /* Deprecated synchronous handler. PC performs bounded polling instead. */
    ET_DMA_COMMAND_CHANNEL_START_WAIT = 0x0018u,
    ET_DMA_COMMAND_IRQ_COMBINED_ENABLE = 0x0019u,
    ET_DMA_COMMAND_SOFTWARE_HANDSHAKE_REQUEST_SET = 0x001au,
    /* Deprecated: CHENREG polling cannot prove completion order. */
    ET_DMA_COMMAND_CHANNELS_START_WAIT_ORDER = 0x001bu,
    ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT_V2 = 0x001cu,
    /** Start one configured channel and arm transfer-complete cycle capture. */
    ET_DMA_COMMAND_CHANNEL_START_TIMED = 0x001du,
    /** Read completion, channel and elapsed-cycle facts for the timed start. */
    ET_DMA_COMMAND_TIMING_SNAPSHOT_GET = 0x001eu
} et_dma_command_t;

typedef struct
{
    volatile uint32_t latched_events;   /**< Normalized DMA events observed. */
    volatile uint32_t irq_count;        /**< Saturating managed callback count. */
    volatile uint32_t unexpected_count; /**< Events outside requested mask/channel. */
    /* Kept on the wire; counts bounded IRQ maintenance failures. */
    volatile uint32_t overflow_count;
} et_dma_irq_result_t;

typedef struct
{
    et_dma_wrap_controller_id_t controller_id; /**< Logical DMA controller. */
    et_dma_wrap_channel_id_t irq_channel;      /**< Channel owned by managed IRQ session. */
    uint8_t irq_priority;                      /**< Board/command-selected NVIC priority. */
    uint8_t irq_enabled;                       /**< IRQ session owns callback bindings. */
    uint8_t irq_combined;         /**< Combined route is used instead of split routes. */
    uint8_t irq_hardware_enabled; /**< DMA source bits are enabled. */
    uint32_t enabled_events;      /**< Normalized events owned by the session. */
    et_irq_route_t routes[ET_DMA_SERVICE_MAX_ROUTES];
    uint8_t route_count;              /**< Number of valid routes in routes. */
    uint8_t route_bound_mask;         /**< Successfully bound route slots. */
    uint8_t controller_enabled;       /**< Controller lifecycle state. */
    uint8_t channel_count;            /**< Runtime channel capability. */
    uint32_t configured_channels;     /**< Service-owned channel configuration mask. */
    uint32_t active_channels;         /**< Channels started and not yet cleaned up. */
    uint8_t timing_channel;           /**< Channel owned by the active measurement. */
    volatile uint8_t timing_armed;    /**< Waiting for its transfer IRQ callback. */
    volatile uint8_t timing_complete; /**< Elapsed-cycle fact is valid. */
    uint8_t timing_reserved;
    volatile uint32_t timing_start_cycles;   /**< DWT origin captured at channel start. */
    volatile uint32_t timing_elapsed_cycles; /**< DWT cycles captured at callback entry. */
    volatile uint32_t result_generation;
    et_dma_irq_result_t irq_result;
    et_irq_manager_t *irq_manager;
    et_service_descriptor_t descriptor;
} et_dma_service_t;

/** Initialize one DMA controller Service without touching DMA hardware. */
int et_dma_service_init(et_dma_service_t *service, et_dma_wrap_controller_id_t controller_id,
                        et_irq_manager_t *irq_manager);
/** Return the router descriptor of an initialized DMA Service. */
const et_service_descriptor_t *et_dma_service_descriptor(const et_dma_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/** Create one DMA Service through the chip-neutral group registry contract. */
int et_dma_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
