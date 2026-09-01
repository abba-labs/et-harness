#ifndef ET_DMA_WRAP_H
#define ET_DMA_WRAP_H

/**
 * @file et_dma_wrap.h
 * @brief Stable chip-neutral DMA driver contract used by DMA Service.
 *
 * The public types deliberately avoid ET chip SDK symbols.  A future chip
 * adapts these values inside et_dma_wrap.c without changing Service or PC
 * test code.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_DMA_WRAP_API_VERSION 1u
#define ET_DMA_WRAP_CONFIG_RESERVED_WORDS 4u
#define ET_DMA_WRAP_CAP_RESERVED_WORDS 4u
/** Deterministic priority used only by the public default-config helper. */
#define ET_DMA_WRAP_DEFAULT_PRIORITY 4u
/** Number of source/destination endpoint choices in the software-request map. */
#define ET_DMA_WRAP_HANDSHAKE_TARGET_COUNT 2u
/** Number of transfer/single/last software-request kinds. */
#define ET_DMA_WRAP_SOFTWARE_REQUEST_KIND_COUNT 3u
/** Number of raw/status/mask slots reported by the DMA interrupt snapshot. */
#define ET_DMA_WRAP_IRQ_SLOT_COUNT 5u
/** Number of per-channel capability words exposed by the DMA component block. */
#define ET_DMA_WRAP_COMPONENT_CHANNEL_PARAMETER_COUNT 8u

/** Stable indices used by et_dma_wrap_interrupt_snapshot_t arrays. */
typedef enum
{
    ET_DMA_WRAP_IRQ_SLOT_TRANSFER = 0u,
    ET_DMA_WRAP_IRQ_SLOT_BLOCK = 1u,
    ET_DMA_WRAP_IRQ_SLOT_SOURCE_TRANSACTION = 2u,
    ET_DMA_WRAP_IRQ_SLOT_DESTINATION_TRANSACTION = 3u,
    ET_DMA_WRAP_IRQ_SLOT_ERROR = 4u
} et_dma_wrap_irq_slot_t;

typedef uint8_t et_dma_wrap_controller_id_t;
typedef uint8_t et_dma_wrap_channel_id_t;

typedef enum
{
    ET_DMA_WRAP_CONTROLLER_0 = 0u,
    ET_DMA_WRAP_CONTROLLER_1 = 1u
} et_dma_wrap_controller_t;

typedef enum
{
    ET_DMA_WRAP_TRANSFER_MEMORY_TO_MEMORY = 0u,
    ET_DMA_WRAP_TRANSFER_MEMORY_TO_PERIPHERAL = 1u,
    ET_DMA_WRAP_TRANSFER_PERIPHERAL_TO_MEMORY = 2u,
    ET_DMA_WRAP_TRANSFER_PERIPHERAL_TO_PERIPHERAL = 3u
} et_dma_wrap_transfer_type_t;

typedef enum
{
    ET_DMA_WRAP_WIDTH_8_BITS = 0u,
    ET_DMA_WRAP_WIDTH_16_BITS = 1u,
    ET_DMA_WRAP_WIDTH_32_BITS = 2u
} et_dma_wrap_width_t;

typedef enum
{
    ET_DMA_WRAP_ADDRESS_INCREMENT = 0u,
    ET_DMA_WRAP_ADDRESS_DECREMENT = 1u,
    ET_DMA_WRAP_ADDRESS_FIXED = 2u
} et_dma_wrap_address_mode_t;

typedef enum
{
    ET_DMA_WRAP_BURST_1_ITEM = 0u,
    ET_DMA_WRAP_BURST_4_ITEMS = 1u,
    ET_DMA_WRAP_BURST_8_ITEMS = 2u,
    ET_DMA_WRAP_BURST_16_ITEMS = 3u,
    ET_DMA_WRAP_BURST_32_ITEMS = 4u,
    ET_DMA_WRAP_BURST_64_ITEMS = 5u,
    ET_DMA_WRAP_BURST_128_ITEMS = 6u,
    ET_DMA_WRAP_BURST_256_ITEMS = 7u
} et_dma_wrap_burst_t;

typedef enum
{
    ET_DMA_WRAP_FIFO_SINGLE = 0u,
    ET_DMA_WRAP_FIFO_HALF_DEPTH = 1u
} et_dma_wrap_fifo_mode_t;

typedef enum
{
    ET_DMA_WRAP_UPDATE_CONTIGUOUS = 0u,
    ET_DMA_WRAP_UPDATE_RELOAD = 1u,
    ET_DMA_WRAP_UPDATE_LINKED_LIST = 2u
} et_dma_wrap_update_mode_t;

/** DMA request source for one channel endpoint. */
typedef enum
{
    ET_DMA_WRAP_HANDSHAKE_HARDWARE = 0u,
    ET_DMA_WRAP_HANDSHAKE_SOFTWARE = 1u
} et_dma_wrap_handshake_mode_t;

/** Active level used when an endpoint selects hardware handshaking. */
typedef enum
{
    ET_DMA_WRAP_HANDSHAKE_ACTIVE_HIGH = 0u,
    ET_DMA_WRAP_HANDSHAKE_ACTIVE_LOW = 1u
} et_dma_wrap_handshake_polarity_t;

/** Source or destination endpoint selected by a software request. */
typedef enum
{
    ET_DMA_WRAP_HANDSHAKE_TARGET_SOURCE = 0u,
    ET_DMA_WRAP_HANDSHAKE_TARGET_DESTINATION = 1u
} et_dma_wrap_handshake_target_t;

/** Software request register family selected for one endpoint. */
typedef enum
{
    ET_DMA_WRAP_SOFTWARE_REQUEST_TRANSFER = 0u,
    ET_DMA_WRAP_SOFTWARE_REQUEST_SINGLE = 1u,
    ET_DMA_WRAP_SOFTWARE_REQUEST_LAST = 2u
} et_dma_wrap_software_request_kind_t;

typedef enum
{
    ET_DMA_WRAP_CONFIG_SOURCE_GATHER = 1u << 0,
    ET_DMA_WRAP_CONFIG_DESTINATION_SCATTER = 1u << 1,
    ET_DMA_WRAP_CONFIG_INITIAL_DONE = 1u << 2
} et_dma_wrap_config_flags_t;

typedef enum
{
    ET_DMA_WRAP_IRQ_TRANSFER = 1u << 0,
    ET_DMA_WRAP_IRQ_BLOCK = 1u << 1,
    ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION = 1u << 2,
    ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION = 1u << 3,
    ET_DMA_WRAP_IRQ_ERROR = 1u << 4
} et_dma_wrap_irq_flags_t;

typedef enum
{
    ET_DMA_WRAP_CAP_MEMORY_TO_MEMORY = 1u << 0,
    ET_DMA_WRAP_CAP_MEMORY_TO_PERIPHERAL = 1u << 1,
    ET_DMA_WRAP_CAP_PERIPHERAL_TO_MEMORY = 1u << 2,
    ET_DMA_WRAP_CAP_PERIPHERAL_TO_PERIPHERAL = 1u << 3,
    ET_DMA_WRAP_CAP_SUSPEND_RESUME = 1u << 4,
    ET_DMA_WRAP_CAP_INTERRUPTS = 1u << 5,
    ET_DMA_WRAP_CAP_RELOAD = 1u << 6,
    ET_DMA_WRAP_CAP_SOURCE_GATHER = 1u << 7,
    ET_DMA_WRAP_CAP_DESTINATION_SCATTER = 1u << 8,
    ET_DMA_WRAP_CAP_LINKED_LIST = 1u << 9,
    ET_DMA_WRAP_CAP_ATOMIC_CHANNEL_MASK_START = 1u << 10,
    ET_DMA_WRAP_CAP_SOFTWARE_HANDSHAKE = 1u << 11,
    ET_DMA_WRAP_CAP_HANDSHAKE_MODE = 1u << 12,
    ET_DMA_WRAP_CAP_HANDSHAKE_POLARITY = 1u << 13,
    ET_DMA_WRAP_CAP_TARGET_CYCLE_TIMING = 1u << 14
} et_dma_wrap_capability_flags_t;

typedef enum
{
    ET_DMA_WRAP_ACCESS_NORMAL = 0u,
    ET_DMA_WRAP_ACCESS_ACC = 1u
} et_dma_wrap_access_view_t;

/** Stable chip-neutral channel configuration consumed by DMA Service. */
typedef struct
{
    uint16_t struct_size;                      /**< Caller-visible structure size. */
    uint16_t api_version;                      /**< Must equal ET_DMA_WRAP_API_VERSION. */
    et_dma_wrap_controller_id_t controller_id; /**< Logical controller. */
    et_dma_wrap_channel_id_t channel_id;       /**< Logical channel. */
    uint8_t transfer_type;                     /**< One et_dma_wrap_transfer_type_t value. */
    uint8_t priority;                          /**< Hardware channel priority. */
    uintptr_t source_address;                  /**< Trusted source address. */
    uintptr_t destination_address;             /**< Trusted destination address. */
    uint32_t transfer_count;                   /**< Transfer items, not bytes. */
    uint8_t source_width;                      /**< Source item width. */
    uint8_t destination_width;                 /**< Destination item width. */
    uint8_t source_address_mode;               /**< Source address update behavior. */
    uint8_t destination_address_mode;          /**< Destination address update behavior. */
    uint8_t source_burst;                      /**< Source burst length. */
    uint8_t destination_burst;                 /**< Destination burst length. */
    uint8_t fifo_mode;                         /**< FIFO single/half-depth selection. */
    uint8_t source_interface;                  /**< Source handshake interface number. */
    uint8_t destination_interface;             /**< Destination handshake interface number. */
    uint8_t source_update_mode;                /**< Source contiguous/reload/LLI mode. */
    uint8_t destination_update_mode;           /**< Destination contiguous/reload/LLI mode. */
    uint8_t source_handshake_mode;             /**< Hardware or software source request. */
    uint8_t destination_handshake_mode;        /**< Hardware or software destination request. */
    uint8_t source_handshake_polarity;         /**< Active level for source request. */
    uint8_t destination_handshake_polarity;    /**< Active level for destination request. */
    uintptr_t linked_list_address;             /**< Trusted aligned next descriptor address. */
    uint32_t source_gather_interval;           /**< Source gather stride in items. */
    uint32_t source_gather_count;              /**< Items per source gather group. */
    uint32_t destination_scatter_interval;     /**< Destination scatter stride in items. */
    uint32_t destination_scatter_count;        /**< Items per destination scatter group. */
    uint32_t flags;                            /**< Optional et_dma_wrap_config_flags_t features. */
    uint32_t reserved[ET_DMA_WRAP_CONFIG_RESERVED_WORDS]; /**< Must be zero. */
} et_dma_wrap_config_t;

#define ET_DMA_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_dma_wrap_config_t, reserved))

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t feature_flags;
    uint16_t channel_count;
    uint16_t max_transfer_count;
    uint32_t max_gather_scatter_interval;
    uint32_t max_gather_scatter_count;
    uint32_t reserved[ET_DMA_WRAP_CAP_RESERVED_WORDS];
} et_dma_wrap_capabilities_t;

typedef struct
{
    uint8_t is_free;
    uint8_t fifo_empty;
    uint16_t reserved16;
    uint32_t interrupt_flags;
} et_dma_wrap_channel_status_t;

typedef struct
{
    uint32_t transfer_channels;
    uint32_t block_channels;
    uint32_t source_transaction_channels;
    uint32_t destination_transaction_channels;
    uint32_t error_channels;
} et_dma_wrap_interrupt_status_t;

typedef struct
{
    uint32_t dma_id;
    uint32_t component_id;
    uint32_t channel_params[ET_DMA_WRAP_COMPONENT_CHANNEL_PARAMETER_COUNT];
    uint32_t multi_block_params;
    uint32_t max_block_size_params;
} et_dma_wrap_component_snapshot_t;

typedef struct
{
    uint32_t raw[ET_DMA_WRAP_IRQ_SLOT_COUNT];
    uint32_t status[ET_DMA_WRAP_IRQ_SLOT_COUNT];
    uint32_t mask[ET_DMA_WRAP_IRQ_SLOT_COUNT];
    uint32_t combined_status;
} et_dma_wrap_interrupt_snapshot_t;

typedef struct
{
    uint32_t source_address;
    uint32_t destination_address;
    uint32_t linked_list_address;
    uint32_t control_low;
    uint32_t control_high;
    uint32_t config_low;
    uint32_t config_high;
    uint32_t source_gather;
    uint32_t destination_scatter;
    uint32_t source_burst;      /**< Stable source burst selector read from hardware. */
    uint32_t destination_burst; /**< Stable destination burst selector read from hardware. */
    uint32_t block_size;        /**< Stable programmed block transfer count. */
    uint32_t fifo_mode;         /**< Stable FIFO policy selector read from hardware. */
} et_dma_wrap_channel_snapshot_t;

/** Fill a complete, backward-compatible DMA configuration with safe defaults. */
et_wrap_status_t et_dma_wrap_get_default_config(et_dma_wrap_config_t *config);
/** Report capabilities actually implemented by this Wrap and chip Driver. */
et_wrap_status_t et_dma_wrap_get_capabilities(et_dma_wrap_controller_id_t controller_id,
                                              et_dma_wrap_capabilities_t *capabilities);
/** Enable one logical DMA controller. */
et_wrap_status_t et_dma_wrap_enable_controller(et_dma_wrap_controller_id_t controller_id);
/** Disable one logical DMA controller. */
et_wrap_status_t et_dma_wrap_disable_controller(et_dma_wrap_controller_id_t controller_id);
/** Validate and translate one chip-neutral configuration into the chip Driver. */
et_wrap_status_t et_dma_wrap_configure_channel(const et_dma_wrap_config_t *config);
/** Stop and return one channel to the unconfigured state. */
et_wrap_status_t et_dma_wrap_deconfigure_channel(et_dma_wrap_controller_id_t controller_id,
                                                 et_dma_wrap_channel_id_t channel_id);
/** Enable one previously configured DMA channel. */
et_wrap_status_t et_dma_wrap_start_channel(et_dma_wrap_controller_id_t controller_id,
                                           et_dma_wrap_channel_id_t channel_id);
/** Start every channel selected by channel_mask with one Driver register write. */
et_wrap_status_t et_dma_wrap_start_channels(et_dma_wrap_controller_id_t controller_id,
                                            uint32_t channel_mask);
/** Assert or clear one typed source/destination software handshake request. */
et_wrap_status_t
et_dma_wrap_set_software_handshake_request(et_dma_wrap_controller_id_t controller_id,
                                           et_dma_wrap_channel_id_t channel_id, uint8_t target,
                                           uint8_t request_kind, uint8_t active);
/** Stop one active channel and leave its configuration available. */
et_wrap_status_t et_dma_wrap_stop_channel(et_dma_wrap_controller_id_t controller_id,
                                          et_dma_wrap_channel_id_t channel_id);
/** Suspend one active channel at a hardware-defined safe boundary. */
et_wrap_status_t et_dma_wrap_suspend_channel(et_dma_wrap_controller_id_t controller_id,
                                             et_dma_wrap_channel_id_t channel_id);
/** Resume one previously suspended channel. */
et_wrap_status_t et_dma_wrap_resume_channel(et_dma_wrap_controller_id_t controller_id,
                                            et_dma_wrap_channel_id_t channel_id);
/** Return the first currently free channel. */
et_wrap_status_t et_dma_wrap_find_free_channel(et_dma_wrap_controller_id_t controller_id,
                                               et_dma_wrap_channel_id_t *channel_id);
/** Read normalized free/FIFO/interrupt facts for one channel. */
et_wrap_status_t et_dma_wrap_get_channel_status(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                et_dma_wrap_channel_status_t *status);
/** Enable selected normalized interrupt sources for one channel. */
et_wrap_status_t et_dma_wrap_enable_interrupts(et_dma_wrap_controller_id_t controller_id,
                                               et_dma_wrap_channel_id_t channel_id,
                                               uint32_t interrupt_flags);
/** Disable selected normalized interrupt sources for one channel. */
et_wrap_status_t et_dma_wrap_disable_interrupts(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t interrupt_flags);
/** Read per-source channel masks for one controller. */
et_wrap_status_t et_dma_wrap_get_interrupt_status(et_dma_wrap_controller_id_t controller_id,
                                                  et_dma_wrap_interrupt_status_t *status);
/** Clear selected interrupt sources for one channel. */
et_wrap_status_t et_dma_wrap_clear_interrupts(et_dma_wrap_controller_id_t controller_id,
                                              et_dma_wrap_channel_id_t channel_id,
                                              uint32_t interrupt_flags);
/** Apply or remove hardware masks for selected channel interrupt sources. */
et_wrap_status_t et_dma_wrap_set_interrupt_mask(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t interrupt_flags, uint8_t enabled);
/** Resolve requested split DMA events into bounded physical IRQ routes. */
et_wrap_status_t et_dma_wrap_get_irq_routes(et_dma_wrap_controller_id_t controller_id,
                                            uint32_t requested_events, et_irq_route_t *routes,
                                            uint8_t route_capacity, uint8_t *route_count);
/** Resolve requested events to the controller combined IRQ route. */
et_wrap_status_t et_dma_wrap_get_combined_irq_route(et_dma_wrap_controller_id_t controller_id,
                                                    uint32_t requested_events,
                                                    et_irq_route_t *route);
/** Read pending normalized events for one channel without clearing them. */
et_wrap_status_t et_dma_wrap_get_pending_events(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t *pending_events);
/** Read immutable DMA component capability registers through selected view. */
et_wrap_status_t et_dma_wrap_get_component_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                    uint8_t access_view,
                                                    et_dma_wrap_component_snapshot_t *snapshot);
/** Read raw/status/mask interrupt registers as one coherent snapshot. */
et_wrap_status_t et_dma_wrap_get_interrupt_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                    et_dma_wrap_interrupt_snapshot_t *snapshot);
/** Read one channel register snapshot without changing transfer state. */
et_wrap_status_t et_dma_wrap_get_channel_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                  et_dma_wrap_channel_id_t channel_id,
                                                  et_dma_wrap_channel_snapshot_t *snapshot);
/** Initialize one trusted linked-list descriptor from common configuration. */
et_wrap_status_t et_dma_wrap_init_lli_descriptor(const et_dma_wrap_config_t *config,
                                                 uintptr_t descriptor_address, uint8_t is_last);
/**
 * @brief Start one DMA channel and return its target-local timing origin.
 * @param controller_id Stable logical DMA controller identifier.
 * @param channel_id Channel to start; it must already be configured.
 * @param start_cycles Receives the DWT value sampled immediately before the
 *        chip Driver enables the channel.
 * @return Normalized Wrap status. No elapsed-time interpretation is performed.
 * @note Available only when ET_ENABLE_TEST_DRIVER_EXTENSIONS is enabled.
 */
et_wrap_status_t et_dma_wrap_start_channel_timed(et_dma_wrap_controller_id_t controller_id,
                                                 et_dma_wrap_channel_id_t channel_id,
                                                 uint32_t *start_cycles);
/**
 * @brief Read elapsed DWT cycles from a previously captured timing origin.
 * @param start_cycles Value returned by et_dma_wrap_start_channel_timed().
 * @param elapsed_cycles Receives wrap-safe unsigned elapsed cycles.
 * @return Normalized Wrap status.
 * @note The caller defines the end boundary by choosing when this API is called.
 */
et_wrap_status_t et_dma_wrap_get_elapsed_cycles(uint32_t start_cycles, uint32_t *elapsed_cycles);

#endif
