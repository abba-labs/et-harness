/**
 * @file et_dma_wrap.c
 * @brief DMA Wrap-to-Driver translation only.
 *
 * This file performs validation and value mapping.  It owns no test-case
 * state, does not operate another IP, and never decides PASS or FAIL.
 */
#include "et_dma_wrap.h"

#include <limits.h>
#include <string.h>

#include "et6x_ahbdma.h"
#include "et_chip_wrap_config.h"

#define ET_DMA_WRAP_KNOWN_CONFIG_FLAGS                                                             \
    (ET_DMA_WRAP_CONFIG_SOURCE_GATHER | ET_DMA_WRAP_CONFIG_DESTINATION_SCATTER |                   \
     ET_DMA_WRAP_CONFIG_INITIAL_DONE)
#define ET_DMA_WRAP_KNOWN_IRQ_FLAGS                                                                \
    (ET_DMA_WRAP_IRQ_TRANSFER | ET_DMA_WRAP_IRQ_BLOCK | ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION |       \
     ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION | ET_DMA_WRAP_IRQ_ERROR)

/* One selected chip supplies only data; the Wrap keeps one generic algorithm. */
typedef struct
{
    et_dma_wrap_controller_id_t controller_id;
    AHBDMA_Type *instance;
    AHBDMA_Type *alternate_instance;
    uint32_t feature_flags;
    uint16_t channel_count;
    uint8_t interface_count;
    uint8_t max_priority;
    uint32_t max_transfer_count;
    uint32_t max_gather_scatter_interval;
    uint32_t max_gather_scatter_count;
    et_irq_line_t transfer_irq;
    et_irq_line_t block_irq;
    et_irq_line_t source_transaction_irq;
    et_irq_line_t destination_transaction_irq;
    et_irq_line_t error_irq;
    et_irq_line_t combined_irq;
} et_dma_wrap_mapping_t;

static const et_dma_wrap_mapping_t dma_mappings[] = ET_CHIP_DMA_MAP_TABLE;

/**
 * @brief Normalize one selected AHB-DMA Driver status into the chip-neutral Wrap namespace.
 *
 * @param[in] status Driver status returned by an AHB-DMA operation.
 *
 * @note This helper performs value translation only and does not access DMA hardware.
 *
 * @return Stable Wrap status corresponding to the Driver result.
 */
static et_wrap_status_t map_driver_status(DRV_Status status)
{
    switch (status)
    {
        case DRV_OK:
        {
            return ET_WRAP_STATUS_OK;
        }

        case DRV_PARAM_ERR:
        case DRV_INVALID:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        case DRV_TIMEOUT:
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        case DRV_BUSY:
        {
            return ET_WRAP_STATUS_BUSY;
        }

        case DRV_ERROR:
        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Resolve one logical DMA controller to its selected-chip mapping record.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 *
 * @note Mapping data comes from the selected Chip Config DMA table and is read-only; no peripheral access occurs.
 *
 * @return Mapping record for the controller, or NULL when unsupported.
 */
static const et_dma_wrap_mapping_t *
find_controller_mapping(et_dma_wrap_controller_id_t controller_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(dma_mappings) / sizeof(dma_mappings[0])); ++index)
    {
        if (dma_mappings[index].controller_id == controller_id)
        {
            return &dma_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Resolve one logical DMA controller to its selected Driver peripheral object.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[out] controller Receives the selected Driver peripheral pointer.
 *
 * @note This helper resolves compile-time Chip Config data only and does not read or write the peripheral.
 *
 * @return ET_WRAP_STATUS_OK when mapped, ET_WRAP_STATUS_NOT_SUPPORTED for an unknown controller, or INVALID_ARGUMENT for a NULL output.
 */
static et_wrap_status_t map_controller(et_dma_wrap_controller_id_t controller_id,
                                       AHBDMA_Type **controller)
{
    const et_dma_wrap_mapping_t *mapping;

    if (controller == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        *controller = NULL;

        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *controller = mapping->instance;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one logical DMA channel against the selected controller capability.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Candidate logical channel identifier.
 *
 * @note Channel count comes from Chip Config/Driver capability data; no channel register is read.
 *
 * @return ET_WRAP_STATUS_OK for an in-range channel, NOT_SUPPORTED for an unknown controller, or INVALID_ARGUMENT for an out-of-range channel.
 */
static et_wrap_status_t validate_channel(et_dma_wrap_controller_id_t controller_id,
                                         et_dma_wrap_channel_id_t channel_id)
{
    const et_dma_wrap_mapping_t *mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (channel_id >= mapping->channel_count)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate stable DMA transfer width to Driver encoding and required address alignment.
 *
 * @param[in] width Stable DMA Wrap width value.
 * @param[out] driver_width Receives the selected Driver width enum value.
 * @param[out] alignment Receives required byte alignment for the corresponding address.
 *
 * @note This is pure value translation and does not program DMA hardware.
 *
 * @return ET_WRAP_STATUS_OK for a supported width, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_width(uint8_t width, uint8_t *driver_width, uint32_t *alignment)
{
    if ((driver_width == NULL) || (alignment == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (width)
    {
        case ET_DMA_WRAP_WIDTH_8_BITS:
        {
            *driver_width = AHBDMA_BITS_8;
            *alignment = 1u;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_WIDTH_16_BITS:
        {
            *driver_width = AHBDMA_BITS_16;
            *alignment = sizeof(uint16_t);

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_WIDTH_32_BITS:
        {
            *driver_width = AHBDMA_BITS_32;
            *alignment = sizeof(uint32_t);

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate one stable DMA address-update mode into the selected Driver encoding.
 *
 * @param[in] mode Stable increment/decrement/fixed address mode.
 * @param[out] driver_mode Receives the selected Driver address-update value.
 *
 * @note This helper performs value translation only and has no hardware side effect.
 *
 * @return ET_WRAP_STATUS_OK for a supported mode, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_address_mode(uint8_t mode, uint8_t *driver_mode)
{
    if (driver_mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (mode)
    {
        case ET_DMA_WRAP_ADDRESS_INCREMENT:
        {
            *driver_mode = AHBDMA_INCREMENTAL;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_ADDRESS_DECREMENT:
        {
            *driver_mode = AHBDMA_DECREMENTAL;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_ADDRESS_FIXED:
        {
            *driver_mode = AHBDMA_FIXED;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Validate and translate one stable DMA burst-length selector for the Driver.
 *
 * @param[in] burst Stable burst selector from one through 256 items.
 * @param[out] driver_burst Receives the selected Driver burst encoding.
 *
 * @note Stable and selected Driver encodings intentionally match for the supported burst range; no hardware access occurs.
 *
 * @return ET_WRAP_STATUS_OK for a supported burst, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_burst(uint8_t burst, uint8_t *driver_burst)
{
    if (driver_burst == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (burst > ET_DMA_WRAP_BURST_256_ITEMS)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *driver_burst = burst;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate one stable DMA transfer topology into the selected Driver encoding.
 *
 * @param[in] transfer_type Stable memory/peripheral source-destination topology.
 * @param[out] driver_transfer_type Receives the selected Driver transfer-type value.
 *
 * @note This is pure value translation and does not configure a channel.
 *
 * @return ET_WRAP_STATUS_OK for a supported topology, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_transfer_type(uint8_t transfer_type, uint8_t *driver_transfer_type)
{
    if (driver_transfer_type == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (transfer_type)
    {
        case ET_DMA_WRAP_TRANSFER_MEMORY_TO_MEMORY:
        {
            *driver_transfer_type = AHBDMA_MEM_TO_MEM;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_TRANSFER_MEMORY_TO_PERIPHERAL:
        {
            *driver_transfer_type = AHBDMA_MEM_TO_PER;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_TRANSFER_PERIPHERAL_TO_MEMORY:
        {
            *driver_transfer_type = AHBDMA_PER_TO_MEM;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_TRANSFER_PERIPHERAL_TO_PERIPHERAL:
        {
            *driver_transfer_type = AHBDMA_PER_TO_PER;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate one stable DMA FIFO policy into the selected Driver encoding.
 *
 * @param[in] fifo_mode Stable FIFO single/half-depth policy.
 * @param[out] driver_fifo_mode Receives the selected Driver FIFO mode.
 *
 * @note This helper changes caller-owned configuration data only, not hardware.
 *
 * @return ET_WRAP_STATUS_OK for a supported policy, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_fifo_mode(uint8_t fifo_mode, uint8_t *driver_fifo_mode)
{
    if (driver_fifo_mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (fifo_mode)
    {
        case ET_DMA_WRAP_FIFO_SINGLE:
        {
            *driver_fifo_mode = AHBDMA_FIFO_SINGLE;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_FIFO_HALF_DEPTH:
        {
            *driver_fifo_mode = AHBDMA_FIFO_HALF_DEPTH;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate one stable DMA multi-block update mode into the selected Driver encoding.
 *
 * @param[in] update_mode Stable contiguous/reload/linked-list mode.
 * @param[out] driver_update_mode Receives the selected Driver multi-block mode.
 *
 * @note The helper does not dereference or program the linked-list pointer.
 *
 * @return ET_WRAP_STATUS_OK for a supported mode, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_update_mode(uint8_t update_mode, uint8_t *driver_update_mode)
{
    if (driver_update_mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (update_mode)
    {
        case ET_DMA_WRAP_UPDATE_CONTIGUOUS:
        {
            *driver_update_mode = AHBDMA_CONTIGUOUS;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_UPDATE_RELOAD:
        {
            *driver_update_mode = AHBDMA_RELOAD;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_UPDATE_LINKED_LIST:
        {
            *driver_update_mode = AHBDMA_LINKED_LIST;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate stable hardware/software DMA handshake selection into the Driver test-extension encoding.
 *
 * @param[in] mode Stable DMA handshake mode.
 * @param[out] driver_mode Receives the selected Driver handshake selector.
 *
 * @note This helper performs translation only; channel CFGL is changed later by the Driver configuration call.
 *
 * @return ET_WRAP_STATUS_OK for a supported mode, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_handshake_mode(uint8_t mode, uint8_t *driver_mode)
{
    if (driver_mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (mode)
    {
        case ET_DMA_WRAP_HANDSHAKE_HARDWARE:
        {
            *driver_mode = AHBDMA_TEST_HS_HARDWARE;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_HANDSHAKE_SOFTWARE:
        {
            *driver_mode = AHBDMA_TEST_HS_SOFTWARE;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate stable DMA handshake active level into the selected Driver test-extension encoding.
 *
 * @param[in] polarity Stable active-high/active-low selector.
 * @param[out] driver_polarity Receives the selected Driver polarity value.
 *
 * @note This helper performs value translation only and has no hardware side effect.
 *
 * @return ET_WRAP_STATUS_OK for a supported polarity, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_handshake_polarity(uint8_t polarity, uint8_t *driver_polarity)
{
    if (driver_polarity == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (polarity)
    {
        case ET_DMA_WRAP_HANDSHAKE_ACTIVE_HIGH:
        {
            *driver_polarity = AHBDMA_TEST_HS_ACTIVE_HIGH;

            return ET_WRAP_STATUS_OK;
        }

        case ET_DMA_WRAP_HANDSHAKE_ACTIVE_LOW:
        {
            *driver_polarity = AHBDMA_TEST_HS_ACTIVE_LOW;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Resolve a stable source/destination software-request kind to the selected Driver register selector.
 *
 * @param[in] target Stable source or destination endpoint selector.
 * @param[in] request_kind Stable transfer/single/last request kind.
 * @param[out] driver_request_type Receives the selected Driver software-request selector.
 *
 * @note The bounded lookup table selects a Driver register family only; no request bit is asserted here.
 *
 * @return ET_WRAP_STATUS_OK for a valid target/kind pair, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_software_request_type(uint8_t target, uint8_t request_kind,
                                                  uint32_t *driver_request_type)
{
    static const uint32_t request_types[ET_DMA_WRAP_HANDSHAKE_TARGET_COUNT]
                                       [ET_DMA_WRAP_SOFTWARE_REQUEST_KIND_COUNT] = {
                                           {AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_TRANSFER,
                                            AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_SINGLE,
                                            AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_LAST},
                                           {AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_TRANSFER,
                                            AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_SINGLE,
                                            AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_LAST}};

    if ((driver_request_type == NULL) || (target > ET_DMA_WRAP_HANDSHAKE_TARGET_DESTINATION) ||
        (request_kind > ET_DMA_WRAP_SOFTWARE_REQUEST_LAST))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *driver_request_type = request_types[target][request_kind];

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate a nonempty stable DMA event mask into selected Driver interrupt-mask bits.
 *
 * @param[in] interrupt_flags Stable DMA Wrap interrupt event bits.
 * @param[out] driver_flags Receives the selected Driver interrupt mask.
 *
 * @note This helper validates and translates event bits only; enabling, disabling or clearing hardware occurs in the caller.
 *
 * @return ET_WRAP_STATUS_OK for a valid nonempty mask, otherwise INVALID_ARGUMENT.
 */
static et_wrap_status_t map_interrupt_flags(uint32_t interrupt_flags, uint32_t *driver_flags)
{
    uint32_t mapped = 0u;

    /* Step 1: Validate the output pointer and reject empty or unknown stable event bits. */
    if (driver_flags == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *driver_flags = 0u;

    if ((interrupt_flags == 0u) || ((interrupt_flags & ~ET_DMA_WRAP_KNOWN_IRQ_FLAGS) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Step 2: Accumulate the selected Driver mask for every requested stable event. */
    if ((interrupt_flags & ET_DMA_WRAP_IRQ_TRANSFER) != 0u)
    {
        mapped |= AHBDMA_IT_TFR_MASK;
    }

    if ((interrupt_flags & ET_DMA_WRAP_IRQ_BLOCK) != 0u)
    {
        mapped |= AHBDMA_IT_BLOCK_MASK;
    }

    if ((interrupt_flags & ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION) != 0u)
    {
        mapped |= AHBDMA_IT_SRCTRAN_MASK;
    }

    if ((interrupt_flags & ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION) != 0u)
    {
        mapped |= AHBDMA_IT_DSTTRAN_MASK;
    }

    if ((interrupt_flags & ET_DMA_WRAP_IRQ_ERROR) != 0u)
    {
        mapped |= AHBDMA_IT_ERR_MASK;
    }

    *driver_flags = mapped;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read effective DMA interrupt status for one channel across all five event banks.
 *
 * @param[in] controller Selected AHB-DMA Driver peripheral object.
 * @param[in] channel_id Logical channel whose STATUS-bank bits are observed.
 *
 * @note The selected Driver reads STATUSTFR/STATUSBLOCK/STATUSSRCTRAN/STATUSDSTTRAN/STATUSERR. This function does not clear pending state.
 *
 * @return Stable DMA Wrap event mask currently visible in the effective STATUS banks for the channel.
 */
static uint32_t get_channel_interrupt_flags(AHBDMA_Type *controller,
                                            et_dma_wrap_channel_id_t channel_id)
{
    uint32_t channel_mask = 1u << channel_id;
    uint32_t flags = 0u;

    if ((AHBDMA_getTfrInterruptChannelMask(controller) & channel_mask) != 0u)
    {
        flags |= ET_DMA_WRAP_IRQ_TRANSFER;
    }

    if ((AHBDMA_getBlockInterruptChannelMask(controller) & channel_mask) != 0u)
    {
        flags |= ET_DMA_WRAP_IRQ_BLOCK;
    }

    if ((AHBDMA_getSrctranInterruptChannelMask(controller) & channel_mask) != 0u)
    {
        flags |= ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION;
    }

    if ((AHBDMA_getDsttranInterruptChannelMask(controller) & channel_mask) != 0u)
    {
        flags |= ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION;
    }

    if ((AHBDMA_getErrInterruptChannelMask(controller) & channel_mask) != 0u)
    {
        flags |= ET_DMA_WRAP_IRQ_ERROR;
    }

    return flags;
}

/**
 * @brief Read raw DMA interrupt-source state for one channel through the Driver diagnostic snapshot.
 *
 * @param[in] controller Selected AHB-DMA Driver peripheral object.
 * @param[in] channel_id Logical channel whose RAW-bank bits are observed.
 * @param[out] flags Receives normalized stable event bits.
 *
 * @note The Driver test snapshot reads RAW event banks without clearing them; this helper only normalizes the selected channel bits.
 *
 * @return ET_WRAP_STATUS_OK on a valid snapshot, otherwise a normalized argument/Driver error.
 */
static et_wrap_status_t get_channel_raw_interrupt_flags(AHBDMA_Type *controller,
                                                        et_dma_wrap_channel_id_t channel_id,
                                                        uint32_t *flags)
{
    AHBDMA_TestInterruptSnapshot_TypeDef snapshot;
    uint32_t channel_mask;
    et_wrap_status_t status;

    if ((controller == NULL) || (flags == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *flags = 0u;
    status = map_driver_status(AHBDMA_testGetInterruptSnapshot(controller, &snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    channel_mask = 1u << channel_id;

    if ((snapshot.raw[ET_DMA_WRAP_IRQ_SLOT_TRANSFER] & channel_mask) != 0u)
    {
        *flags |= ET_DMA_WRAP_IRQ_TRANSFER;
    }

    if ((snapshot.raw[ET_DMA_WRAP_IRQ_SLOT_BLOCK] & channel_mask) != 0u)
    {
        *flags |= ET_DMA_WRAP_IRQ_BLOCK;
    }

    if ((snapshot.raw[ET_DMA_WRAP_IRQ_SLOT_SOURCE_TRANSACTION] & channel_mask) != 0u)
    {
        *flags |= ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION;
    }

    if ((snapshot.raw[ET_DMA_WRAP_IRQ_SLOT_DESTINATION_TRANSACTION] & channel_mask) != 0u)
    {
        *flags |= ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION;
    }

    if ((snapshot.raw[ET_DMA_WRAP_IRQ_SLOT_ERROR] & channel_mask) != 0u)
    {
        *flags |= ET_DMA_WRAP_IRQ_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate the versioned DMA Wrap configuration envelope before field translation.
 *
 * @param[in] config Caller-provided chip-neutral DMA configuration.
 *
 * @note Only pointer, API version and minimum structure size are checked here; chip limits and field relationships are validated by later translation.
 *
 * @return ET_WRAP_STATUS_OK for a supported envelope, INVALID_ARGUMENT for NULL, or NOT_SUPPORTED for an incompatible version/size.
 */
static et_wrap_status_t validate_config_header(const et_dma_wrap_config_t *config)
{
    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((config->api_version != ET_DMA_WRAP_API_VERSION) ||
        (config->struct_size < ET_DMA_WRAP_CONFIG_V1_MIN_SIZE))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one chip-neutral DMA configuration and build the selected Driver channel structure.
 *
 * @param[in] config Versioned DMA Wrap configuration to translate.
 * @param[out] driver_config Selected Driver channel configuration populated from validated fields.
 *
 * @note This helper enforces Chip Config limits, 32-bit Driver addressability and width alignment, then configures only caller-owned Driver structures through Driver helper APIs. It does not write a DMA channel register.
 *
 * @return ET_WRAP_STATUS_OK when the Driver configuration is built, otherwise a normalized validation/Driver status.
 */
static et_wrap_status_t build_driver_config(const et_dma_wrap_config_t *config,
                                            AHBDMA_Ch_Init_TypeDef *driver_config)
{
    const et_dma_wrap_mapping_t *mapping;
    uint32_t source_alignment;
    uint32_t destination_alignment;
    uint8_t source_update_mode;
    uint8_t destination_update_mode;
    et_wrap_status_t status;
    DRV_Status driver_status;

    /* Phase 1: Validate pointers, selected-chip limits and Driver addressability constraints. */
    if ((config == NULL) || (driver_config == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    mapping = find_controller_mapping(config->controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((config->transfer_count == 0u) || (config->transfer_count > mapping->max_transfer_count) ||
        (config->priority > mapping->max_priority) ||
        (config->source_interface >= mapping->interface_count) ||
        (config->destination_interface >= mapping->interface_count) ||
        ((config->flags & ~ET_DMA_WRAP_KNOWN_CONFIG_FLAGS) != 0u) ||
        (config->source_gather_count > mapping->max_gather_scatter_count) ||
        (config->destination_scatter_count > mapping->max_gather_scatter_count) ||
        (config->source_gather_interval > mapping->max_gather_scatter_interval) ||
        (config->destination_scatter_interval > mapping->max_gather_scatter_interval) ||
        (config->source_address > (uintptr_t)UINT32_MAX) ||
        (config->destination_address > (uintptr_t)UINT32_MAX) ||
        (config->linked_list_address > (uintptr_t)UINT32_MAX) ||
        ((config->linked_list_address != 0u) &&
         ((config->linked_list_address & (sizeof(uint32_t) - 1u)) != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Initialize the Driver structure and validate width-derived address alignment. */
    AHBDMA_initChannelStruct(driver_config);
    status = map_width(config->source_width, &driver_config->srcTrWidth, &source_alignment);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status =
        map_width(config->destination_width, &driver_config->dstTrWidth, &destination_alignment);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (((config->source_address & (source_alignment - 1u)) != 0u) ||
        ((config->destination_address & (destination_alignment - 1u)) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 3: Translate address, burst, topology, FIFO and multi-block update semantics. */
    status = map_address_mode(config->source_address_mode, &driver_config->srcAddressInc);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_address_mode(config->destination_address_mode, &driver_config->dstAddressInc);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_burst(config->source_burst, &driver_config->srcBurstDataItemsNum);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_burst(config->destination_burst, &driver_config->dstBurstDataItemsNum);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_transfer_type(config->transfer_type, &driver_config->tfrType);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_fifo_mode(config->fifo_mode, &driver_config->fifoMode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_update_mode(config->source_update_mode, &source_update_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_update_mode(config->destination_update_mode, &destination_update_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 4: Populate scalar Driver fields and derive multi-block/gather/scatter control fields. */
    driver_config->sar = (uint32_t)config->source_address;
    driver_config->dar = (uint32_t)config->destination_address;
    driver_config->blkTfrSize = (uint16_t)config->transfer_count;
    driver_config->prior = config->priority;
    driver_config->srcPer = config->source_interface;
    driver_config->dstPer = config->destination_interface;
    driver_config->wbDoneEn =
        ((config->flags & ET_DMA_WRAP_CONFIG_INITIAL_DONE) != 0u) ? ENABLE : DISABLE;

    driver_status = AHBDMA_setMultiBlock(driver_config, source_update_mode, destination_update_mode,
                                         (uint32_t)config->linked_list_address);
    status = map_driver_status(driver_status);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_setSourceGather(
        driver_config, config->source_gather_interval, config->source_gather_count,
        ((config->flags & ET_DMA_WRAP_CONFIG_SOURCE_GATHER) != 0u) ? ENABLE : DISABLE);
    AHBDMA_setDestinationScatter(
        driver_config, config->destination_scatter_interval, config->destination_scatter_count,
        ((config->flags & ET_DMA_WRAP_CONFIG_DESTINATION_SCATTER) != 0u) ? ENABLE : DISABLE);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Fill one complete DMA Wrap configuration with deterministic portable defaults.
 *
 * @param[out] config Caller-owned configuration structure to initialize.
 *
 * @note Defaults describe a one-item memory-to-memory transfer and do not query or configure DMA hardware.
 *
 * @return ET_WRAP_STATUS_OK on success, or INVALID_ARGUMENT when config is NULL.
 */
et_wrap_status_t et_dma_wrap_get_default_config(et_dma_wrap_config_t *config)
{
    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(config, 0, sizeof(*config));
    config->struct_size = (uint16_t)sizeof(*config);
    config->api_version = ET_DMA_WRAP_API_VERSION;
    config->controller_id = ET_DMA_WRAP_CONTROLLER_0;
    config->channel_id = 0u;
    config->transfer_type = ET_DMA_WRAP_TRANSFER_MEMORY_TO_MEMORY;
    config->priority = ET_DMA_WRAP_DEFAULT_PRIORITY;
    config->transfer_count = 1u;
    config->source_width = ET_DMA_WRAP_WIDTH_8_BITS;
    config->destination_width = ET_DMA_WRAP_WIDTH_8_BITS;
    config->source_address_mode = ET_DMA_WRAP_ADDRESS_INCREMENT;
    config->destination_address_mode = ET_DMA_WRAP_ADDRESS_INCREMENT;
    config->source_burst = ET_DMA_WRAP_BURST_1_ITEM;
    config->destination_burst = ET_DMA_WRAP_BURST_1_ITEM;
    config->fifo_mode = ET_DMA_WRAP_FIFO_SINGLE;
    config->source_update_mode = ET_DMA_WRAP_UPDATE_CONTIGUOUS;
    config->destination_update_mode = ET_DMA_WRAP_UPDATE_CONTIGUOUS;
    config->source_handshake_mode = ET_DMA_WRAP_HANDSHAKE_HARDWARE;
    config->destination_handshake_mode = ET_DMA_WRAP_HANDSHAKE_HARDWARE;
    config->source_handshake_polarity = ET_DMA_WRAP_HANDSHAKE_ACTIVE_HIGH;
    config->destination_handshake_polarity = ET_DMA_WRAP_HANDSHAKE_ACTIVE_HIGH;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return selected-chip DMA limits and supported feature flags for one logical controller.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[out] capabilities Caller-owned capability structure to populate.
 *
 * @note Capability facts come from selected Chip Config and generated/Driver constants; no DMA register is read.
 *
 * @return ET_WRAP_STATUS_OK when mapped, NOT_SUPPORTED for an unknown controller, or INVALID_ARGUMENT for a NULL output.
 */
et_wrap_status_t et_dma_wrap_get_capabilities(et_dma_wrap_controller_id_t controller_id,
                                              et_dma_wrap_capabilities_t *capabilities)
{
    const et_dma_wrap_mapping_t *mapping;

    if (capabilities == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(capabilities, 0, sizeof(*capabilities));
    mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    capabilities->struct_size = (uint16_t)sizeof(*capabilities);
    capabilities->api_version = ET_DMA_WRAP_API_VERSION;
    capabilities->feature_flags = mapping->feature_flags;
    capabilities->channel_count = mapping->channel_count;
    capabilities->max_transfer_count = mapping->max_transfer_count;
    capabilities->max_gather_scatter_interval = mapping->max_gather_scatter_interval;
    capabilities->max_gather_scatter_count = mapping->max_gather_scatter_count;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable one logical DMA controller through the selected Driver.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 *
 * @note The Driver sets DMACFGREG.DMA_EN when not already enabled.
 *
 * @return Normalized Wrap status from controller mapping and Driver enable.
 */
et_wrap_status_t et_dma_wrap_enable_controller(et_dma_wrap_controller_id_t controller_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_enableModule(controller));
}

/**
 * @brief Disable one logical DMA controller through the selected Driver.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 *
 * @note The selected Driver disables every channel, clears their interrupt sources, clears DMA_EN and polls for disable completion with a bounded timeout.
 *
 * @return Normalized Wrap status, including TIMEOUT when the Driver cannot complete module disable.
 */
et_wrap_status_t et_dma_wrap_disable_controller(et_dma_wrap_controller_id_t controller_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_disableModule(controller));
}

/**
 * @brief Validate, translate and program one DMA channel from the stable Wrap configuration.
 *
 * @param[in] config Versioned chip-neutral DMA configuration.
 *
 * @note The selected Driver writes channel address/control/configuration registers and owns target-local TCM-to-DMA address translation. Handshake fields are programmed afterward; a handshake failure deinitializes the channel before returning.
 *
 * @return ET_WRAP_STATUS_OK on successful configuration, BUSY for a non-free channel, or a normalized validation/Driver error.
 */
et_wrap_status_t et_dma_wrap_configure_channel(const et_dma_wrap_config_t *config)
{
    AHBDMA_Ch_Init_TypeDef driver_config;
    AHBDMA_Type *controller;
    uint8_t source_handshake_mode;
    uint8_t destination_handshake_mode;
    uint8_t source_handshake_polarity;
    uint8_t destination_handshake_polarity;
    et_wrap_status_t status;

    /* Phase 1: Validate the versioned envelope, controller/channel mapping and free-channel precondition. */
    status = validate_config_header(config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_controller(config->controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(config->controller_id, config->channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (!AHBDMA_isChannelFree(controller, config->channel_id))
    {
        return ET_WRAP_STATUS_BUSY;
    }

    /* Phase 2: Build Driver channel fields and translate both endpoint handshake policies. */
    status = build_driver_config(config, &driver_config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_handshake_mode(config->source_handshake_mode, &source_handshake_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_handshake_mode(config->destination_handshake_mode, &destination_handshake_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_handshake_polarity(config->source_handshake_polarity, &source_handshake_polarity);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_handshake_polarity(config->destination_handshake_polarity,
                                    &destination_handshake_polarity);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 3: Program channel registers, then program handshake fields with rollback on failure. */
    AHBDMA_initChannel(controller, &driver_config, config->channel_id);
    status = map_driver_status(AHBDMA_testConfigureChannelHandshake(
        controller, config->channel_id, source_handshake_mode, destination_handshake_mode,
        source_handshake_polarity, destination_handshake_polarity));

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)AHBDMA_deInitChannel(controller, config->channel_id);

        return status;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable DMA interrupt sources, clear pending events and deinitialize one logical channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to return to Driver idle state.
 *
 * @note This function changes DMA hardware: all known channel interrupt sources are disabled/cleared before Driver deinitialization.
 *
 * @return Normalized Wrap status from mapping, validation and Driver deinitialization.
 */
et_wrap_status_t et_dma_wrap_deconfigure_channel(et_dma_wrap_controller_id_t controller_id,
                                                 et_dma_wrap_channel_id_t channel_id)
{
    AHBDMA_Type *controller;
    uint32_t driver_flags;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_interrupt_flags(ET_DMA_WRAP_KNOWN_IRQ_FLAGS, &driver_flags);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_disableChannelInterrupt(controller, channel_id, driver_flags);
    AHBDMA_clearInterruptChannel(controller, channel_id, driver_flags);

    return map_driver_status(AHBDMA_deInitChannel(controller, channel_id));
}

/**
 * @brief Enable one previously configured logical DMA channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to start.
 *
 * @note The selected Driver writes the channel-enable register and treats an already-enabled channel as success.
 *
 * @return Normalized Wrap status from mapping, validation and Driver enable.
 */
et_wrap_status_t et_dma_wrap_start_channel(et_dma_wrap_controller_id_t controller_id,
                                           et_dma_wrap_channel_id_t channel_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_enableChannel(controller, channel_id));
}

/**
 * @brief Start one configured DMA channel and return the DWT cycle origin sampled immediately before Driver enable.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to start.
 * @param[out] start_cycles Receives the target-local DWT cycle value sampled before channel enable.
 *
 * @note The selected Driver test extension enables the trace/cycle-count bits if available and then samples DWT immediately before AHBDMA_enableChannel(). It does not restore those enable bits. No elapsed-time threshold is interpreted here.
 *
 * @return Normalized Wrap status, or NOT_SUPPORTED when test Driver extensions are unavailable.
 */
et_wrap_status_t et_dma_wrap_start_channel_timed(et_dma_wrap_controller_id_t controller_id,
                                                 et_dma_wrap_channel_id_t channel_id,
                                                 uint32_t *start_cycles)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    if (start_cycles == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    /* Driver owns the indivisible DWT-sample then channel-enable sequence. */
    return map_driver_status(AHBDMA_testStartChannelTimed(controller, channel_id, start_cycles));
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Read unsigned target-local DWT cycles elapsed from a previously captured DMA timing origin.
 *
 * @param[in] start_cycles DWT origin returned by et_dma_wrap_start_channel_timed().
 * @param[out] elapsed_cycles Receives current DWT minus start_cycles using wrap-safe unsigned subtraction.
 *
 * @note This call only samples the DWT counter; the caller defines the measurement end boundary and the PC owns any timing verdict.
 *
 * @return Normalized Wrap status, or NOT_SUPPORTED when test Driver extensions are unavailable.
 */
et_wrap_status_t et_dma_wrap_get_elapsed_cycles(uint32_t start_cycles, uint32_t *elapsed_cycles)
{
    if (elapsed_cycles == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    /* Return the raw target cycle fact; thresholds belong to the PC Case. */
    return map_driver_status(AHBDMA_testGetElapsedCycles(start_cycles, elapsed_cycles));
#else
    (void)start_cycles;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Start a validated nonempty DMA channel mask with one selected Driver CHENREG write.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_mask Channels to enable atomically.
 *
 * @note The mask is constrained to the Chip Config channel count before the Driver test extension writes channel bits and their write-enable bits together.
 *
 * @return Normalized Wrap status for mapping, mask validation or Driver execution.
 */
et_wrap_status_t et_dma_wrap_start_channels(et_dma_wrap_controller_id_t controller_id,
                                            uint32_t channel_mask)
{
    const et_dma_wrap_mapping_t *mapping;
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((channel_mask == 0u) || (mapping->channel_count > (sizeof(channel_mask) * CHAR_BIT)) ||
        ((mapping->channel_count < (sizeof(channel_mask) * CHAR_BIT)) &&
         ((channel_mask & ~((1u << mapping->channel_count) - 1u)) != 0u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_testEnableChannelsByMask(controller, channel_mask));
}

/**
 * @brief Assert or clear one typed DMA software-handshake request through the selected Driver.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical DMA channel whose request bit is changed.
 * @param[in] target Stable source/destination endpoint selector.
 * @param[in] request_kind Stable transfer/single/last request kind.
 * @param[in] active Canonical 0/1 value selecting clear/assert.
 *
 * @note The selected Driver writes exactly one of REQSRC/REQDST/SGLRQSRC/SGLRQDST/LSTSRC/LSTDST with the channel write-enable bit.
 *
 * @return Normalized Wrap status for validation, mapping or Driver execution.
 */
et_wrap_status_t
et_dma_wrap_set_software_handshake_request(et_dma_wrap_controller_id_t controller_id,
                                           et_dma_wrap_channel_id_t channel_id, uint8_t target,
                                           uint8_t request_kind, uint8_t active)
{
    AHBDMA_Type *controller;
    uint32_t driver_request_type;
    et_wrap_status_t status;

    if (active > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_software_request_type(target, request_kind, &driver_request_type);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_testSetSoftwareHandshakeRequest(
        controller, channel_id, driver_request_type, (active != 0u) ? ENABLE : DISABLE));
}

/**
 * @brief Disable one active DMA channel while retaining its programming state.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to stop.
 *
 * @note The selected Driver clears the channel-enable bit and polls it with a bounded timeout; channel configuration is not deinitialized here.
 *
 * @return Normalized Wrap status, including TIMEOUT when channel disable does not complete.
 */
et_wrap_status_t et_dma_wrap_stop_channel(et_dma_wrap_controller_id_t controller_id,
                                          et_dma_wrap_channel_id_t channel_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(AHBDMA_disableChannel(controller, channel_id));
}

/**
 * @brief Request suspension of one active DMA channel without discarding its configuration.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to suspend.
 *
 * @note This function changes channel hardware through the selected Driver suspend operation and does not poll for a higher-level test condition.
 *
 * @return ET_WRAP_STATUS_OK after a valid Driver suspend request, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_suspend_channel(et_dma_wrap_controller_id_t controller_id,
                                             et_dma_wrap_channel_id_t channel_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_suspendChannel(controller, channel_id);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resume one previously suspended DMA channel through the selected Driver.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to resume.
 *
 * @note This function changes channel hardware only; Service lifecycle ownership remains outside the Wrap.
 *
 * @return ET_WRAP_STATUS_OK after a valid Driver resume request, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_resume_channel(et_dma_wrap_controller_id_t controller_id,
                                            et_dma_wrap_channel_id_t channel_id)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_resumeChannel(controller, channel_id);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Ask the selected Driver for one currently free DMA channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[out] channel_id Receives the first free channel identifier.
 *
 * @note This is a hardware-state observation; it does not reserve or configure the returned channel.
 *
 * @return ET_WRAP_STATUS_OK when a free channel is found, NO_RESOURCE when none exists, or mapping/argument status.
 */
et_wrap_status_t et_dma_wrap_find_free_channel(et_dma_wrap_controller_id_t controller_id,
                                               et_dma_wrap_channel_id_t *channel_id)
{
    AHBDMA_Type *controller;
    uint32_t free_channel;
    et_wrap_status_t status;

    if (channel_id == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *channel_id = 0u;
    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    free_channel = AHBDMA_findFreeChannel(controller);

    if (free_channel == AHBDMA_CH_ERR)
    {
        return ET_WRAP_STATUS_NO_RESOURCE;
    }

    *channel_id = (et_dma_wrap_channel_id_t)free_channel;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read normalized free, FIFO-empty and raw interrupt facts for one DMA channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to observe.
 * @param[out] status Caller-owned normalized channel-status structure.
 *
 * @note Free/FIFO facts come from Driver channel state while interrupt_flags are derived from the Driver RAW interrupt snapshot. No pending event is cleared.
 *
 * @return ET_WRAP_STATUS_OK for a complete observation, otherwise a normalized mapping/validation/Driver status.
 */
et_wrap_status_t et_dma_wrap_get_channel_status(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                et_dma_wrap_channel_status_t *status)
{
    AHBDMA_Type *controller;
    et_wrap_status_t wrap_status;

    /* Phase 1: Validate output storage and resolve the logical controller/channel. */
    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(status, 0, sizeof(*status));
    wrap_status = map_controller(controller_id, &controller);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    wrap_status = validate_channel(controller_id, channel_id);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    /* Phase 2: Read channel state and normalize RAW interrupt-source evidence. */
    status->is_free = AHBDMA_isChannelFree(controller, channel_id) ? 1u : 0u;
    status->fifo_empty = AHBDMA_isChannelFifoEmpty(controller, channel_id) ? 1u : 0u;
    wrap_status = get_channel_raw_interrupt_flags(controller, channel_id, &status->interrupt_flags);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected normalized DMA interrupt sources for one channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel whose source mask is changed.
 * @param[in] interrupt_flags Nonempty stable DMA event mask.
 *
 * @note The Driver writes the corresponding MASK event banks and sets the channel INT_EN bit; CPU IRQ routing remains owned by IRQ Manager.
 *
 * @return ET_WRAP_STATUS_OK on success, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_enable_interrupts(et_dma_wrap_controller_id_t controller_id,
                                               et_dma_wrap_channel_id_t channel_id,
                                               uint32_t interrupt_flags)
{
    AHBDMA_Type *controller;
    uint32_t driver_flags;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_interrupt_flags(interrupt_flags, &driver_flags);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_enableChannelInterrupt(controller, channel_id, driver_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected normalized DMA interrupt sources for one channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel whose source mask is changed.
 * @param[in] interrupt_flags Nonempty stable DMA event mask.
 *
 * @note The Driver clears the corresponding MASK event-bank enables and the channel INT_EN bit; pending RAW source bits are not cleared by this operation.
 *
 * @return ET_WRAP_STATUS_OK on success, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_disable_interrupts(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t interrupt_flags)
{
    AHBDMA_Type *controller;
    uint32_t driver_flags;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_interrupt_flags(interrupt_flags, &driver_flags);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_disableChannelInterrupt(controller, channel_id, driver_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read effective per-event DMA STATUS channel masks for one controller.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[out] status Caller-owned structure receiving transfer/block/source/destination/error channel masks.
 *
 * @note The selected Driver reads STATUS event banks rather than RAW banks; this function performs no clear or mask update.
 *
 * @return ET_WRAP_STATUS_OK when the controller is mapped and status is populated, otherwise argument/mapping status.
 */
et_wrap_status_t et_dma_wrap_get_interrupt_status(et_dma_wrap_controller_id_t controller_id,
                                                  et_dma_wrap_interrupt_status_t *status)
{
    AHBDMA_Type *controller;
    et_wrap_status_t wrap_status;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(status, 0, sizeof(*status));
    wrap_status = map_controller(controller_id, &controller);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    status->transfer_channels = AHBDMA_getTfrInterruptChannelMask(controller);
    status->block_channels = AHBDMA_getBlockInterruptChannelMask(controller);
    status->source_transaction_channels = AHBDMA_getSrctranInterruptChannelMask(controller);
    status->destination_transaction_channels = AHBDMA_getDsttranInterruptChannelMask(controller);
    status->error_channels = AHBDMA_getErrInterruptChannelMask(controller);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected normalized DMA interrupt-source bits for one channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel whose pending events are acknowledged.
 * @param[in] interrupt_flags Nonempty stable DMA event mask to clear.
 *
 * @note The Driver writes the event-specific CLEAR registers. Source enable/mask ownership is not changed.
 *
 * @return ET_WRAP_STATUS_OK on success, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_clear_interrupts(et_dma_wrap_controller_id_t controller_id,
                                              et_dma_wrap_channel_id_t channel_id,
                                              uint32_t interrupt_flags)
{
    AHBDMA_Type *controller;
    uint32_t driver_flags;
    et_wrap_status_t status;

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_interrupt_flags(interrupt_flags, &driver_flags);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AHBDMA_clearInterruptChannel(controller, channel_id, driver_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or disable selected DMA interrupt-source mask bits for one channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel whose event mask is changed.
 * @param[in] interrupt_flags Nonempty stable DMA event mask.
 * @param[in] enabled Canonical 1 to enable Driver interrupt sources, 0 to disable them.
 *
 * @note This operation delegates to the same Driver enable/disable interrupt APIs used by managed IRQ ownership and therefore also updates the channel INT_EN bit.
 *
 * @return ET_WRAP_STATUS_OK on success, otherwise mapping/argument validation status.
 */
et_wrap_status_t et_dma_wrap_set_interrupt_mask(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t interrupt_flags, uint8_t enabled)
{
    AHBDMA_Type *controller;
    uint32_t driver_flags;
    et_wrap_status_t status;

    /* Phase 1: Validate the canonical enable flag, controller, channel and stable event mask. */
    if ((enabled != 0u) && (enabled != 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_interrupt_flags(interrupt_flags, &driver_flags);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 2: Apply the selected Driver interrupt-source enable or disable operation. */
    if (enabled != 0u)
    {
        AHBDMA_enableChannelInterrupt(controller, channel_id, driver_flags);
    }
    else
    {
        AHBDMA_disableChannelInterrupt(controller, channel_id, driver_flags);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Append one DMA physical IRQ route and its normalized event bit to a bounded caller array.
 *
 * @param[in,out] routes Caller-owned route array.
 * @param[in] route_capacity Maximum route entries available.
 * @param[in,out] route_count Current count, advanced after a successful append.
 * @param[in] irq_line Physical IRQ line from selected Chip Config.
 * @param[in] event Stable DMA event bit associated with the route.
 *
 * @note This helper only writes caller-owned route metadata and does not bind or enable the IRQ line.
 *
 * @return ET_WRAP_STATUS_OK when appended, or NO_RESOURCE when the array is full.
 */
static et_wrap_status_t append_irq_route(et_irq_route_t *routes, uint8_t route_capacity,
                                         uint8_t *route_count, et_irq_line_t irq_line,
                                         uint32_t event)
{
    if (*route_count >= route_capacity)
    {
        return ET_WRAP_STATUS_NO_RESOURCE;
    }

    routes[*route_count].irq_line = irq_line;
    routes[*route_count].reserved = 0u;
    routes[*route_count].route_events = event;
    ++(*route_count);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve requested DMA event bits to their selected-chip split physical IRQ routes.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] requested_events Nonempty stable DMA event mask.
 * @param[out] routes Caller-owned array receiving one route per requested split event.
 * @param[in] route_capacity Maximum route entries available.
 * @param[out] route_count Number of routes produced.
 *
 * @note Route lines come from selected Chip Config DMA mapping data. This function constructs metadata only and never calls NVIC or IRQ Manager.
 *
 * @return ET_WRAP_STATUS_OK when all requested routes fit, otherwise argument, capability or capacity status.
 */
et_wrap_status_t et_dma_wrap_get_irq_routes(et_dma_wrap_controller_id_t controller_id,
                                            uint32_t requested_events, et_irq_route_t *routes,
                                            uint8_t route_capacity, uint8_t *route_count)
{
    const et_dma_wrap_mapping_t *mapping;
    et_wrap_status_t status;

    /* Phase 1: Validate request/output capacity and resolve the selected-chip route mapping. */
    if ((routes == NULL) || (route_count == NULL) || (route_capacity == 0u) ||
        (requested_events == 0u) || ((requested_events & ~ET_DMA_WRAP_KNOWN_IRQ_FLAGS) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *route_count = 0u;
    mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

#define APPEND_DMA_ROUTE(flag, line)                                                               \
    do                                                                                             \
    {                                                                                              \
        if ((requested_events & (flag)) != 0u)                                                     \
        {                                                                                          \
            status = append_irq_route(routes, route_capacity, route_count, line, flag);            \
            if (status != ET_WRAP_STATUS_OK)                                                       \
            {                                                                                      \
                return status;                                                                     \
            }                                                                                      \
        }                                                                                          \
    } while (0)

    /* Phase 2: Append one physical route for each requested normalized split event. */
    APPEND_DMA_ROUTE(ET_DMA_WRAP_IRQ_TRANSFER, mapping->transfer_irq);
    APPEND_DMA_ROUTE(ET_DMA_WRAP_IRQ_BLOCK, mapping->block_irq);
    APPEND_DMA_ROUTE(ET_DMA_WRAP_IRQ_SOURCE_TRANSACTION, mapping->source_transaction_irq);
    APPEND_DMA_ROUTE(ET_DMA_WRAP_IRQ_DESTINATION_TRANSACTION, mapping->destination_transaction_irq);
    APPEND_DMA_ROUTE(ET_DMA_WRAP_IRQ_ERROR, mapping->error_irq);
#undef APPEND_DMA_ROUTE

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve a normalized DMA event mask to the selected controller combined IRQ route.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] requested_events Nonempty stable DMA event mask associated with the route.
 * @param[out] route Caller-owned route metadata to populate.
 *
 * @note The physical line is a Chip Config fact; this helper does not bind, enable or clear any interrupt source.
 *
 * @return ET_WRAP_STATUS_OK when mapped, otherwise argument or capability status.
 */
et_wrap_status_t et_dma_wrap_get_combined_irq_route(et_dma_wrap_controller_id_t controller_id,
                                                    uint32_t requested_events,
                                                    et_irq_route_t *route)
{
    const et_dma_wrap_mapping_t *mapping;

    if ((route == NULL) || (requested_events == 0u) ||
        ((requested_events & ~ET_DMA_WRAP_KNOWN_IRQ_FLAGS) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    mapping = find_controller_mapping(controller_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    route->irq_line = mapping->combined_irq;
    route->reserved = 0u;
    route->route_events = requested_events;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read currently effective DMA STATUS events for one logical channel.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to observe.
 * @param[out] pending_events Receives normalized event bits visible in the Driver STATUS banks.
 *
 * @note Despite the historical helper name, this path reads effective STATUS banks via Driver channel-mask APIs, not the RAW interrupt snapshot, and does not clear any source.
 *
 * @return ET_WRAP_STATUS_OK for a valid observation, otherwise mapping/validation status.
 */
et_wrap_status_t et_dma_wrap_get_pending_events(et_dma_wrap_controller_id_t controller_id,
                                                et_dma_wrap_channel_id_t channel_id,
                                                uint32_t *pending_events)
{
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    if (pending_events == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *pending_events = 0u;
    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    *pending_events = get_channel_interrupt_flags(controller, channel_id);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read immutable DMA component-identification and capability registers through the selected access view.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] access_view Normal or ACC diagnostic access view.
 * @param[out] snapshot Caller-owned normalized component snapshot.
 *
 * @note Normal and ACC peripheral objects come from Chip Config. The Driver test extension only reads identification/parameter registers; no channel state changes.
 *
 * @return ET_WRAP_STATUS_OK for a supported view, otherwise argument, capability or Driver status.
 */
et_wrap_status_t et_dma_wrap_get_component_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                    uint8_t access_view,
                                                    et_dma_wrap_component_snapshot_t *snapshot)
{
    AHBDMA_TestComponentSnapshot_TypeDef driver_snapshot;
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    /* Phase 1: Validate output storage and select the normal or ACC Driver access view. */
    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(snapshot, 0, sizeof(*snapshot));

    if (access_view == ET_DMA_WRAP_ACCESS_NORMAL)
    {
        status = map_controller(controller_id, &controller);
    }
    else if (access_view == ET_DMA_WRAP_ACCESS_ACC)
    {
        const et_dma_wrap_mapping_t *mapping = find_controller_mapping(controller_id);

        if ((mapping == NULL) || (mapping->alternate_instance == NULL))
        {
            status = ET_WRAP_STATUS_NOT_SUPPORTED;
        }
        else
        {
            controller = mapping->alternate_instance;
            status = ET_WRAP_STATUS_OK;
        }
    }
    else
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 2: Read immutable Driver component facts and normalize them into the public snapshot. */
    status = map_driver_status(AHBDMA_testGetComponentSnapshot(controller, &driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    snapshot->dma_id = driver_snapshot.dmaId;
    snapshot->component_id = driver_snapshot.componentId;
    (void)memcpy(snapshot->channel_params, driver_snapshot.channelParams,
                 sizeof(snapshot->channel_params));
    snapshot->multi_block_params = driver_snapshot.multiBlockParams;
    snapshot->max_block_size_params = driver_snapshot.maxBlockSizeParams;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read raw, effective-status, mask and combined DMA interrupt registers as one diagnostic snapshot.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[out] snapshot Caller-owned normalized interrupt snapshot.
 *
 * @note The Driver test extension performs register reads only and does not acknowledge or mask an interrupt.
 *
 * @return ET_WRAP_STATUS_OK for a complete snapshot, otherwise mapping/argument/Driver status.
 */
et_wrap_status_t et_dma_wrap_get_interrupt_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                    et_dma_wrap_interrupt_snapshot_t *snapshot)
{
    AHBDMA_TestInterruptSnapshot_TypeDef driver_snapshot;
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(snapshot, 0, sizeof(*snapshot));
    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_driver_status(AHBDMA_testGetInterruptSnapshot(controller, &driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    (void)memcpy(snapshot->raw, driver_snapshot.raw, sizeof(snapshot->raw));
    (void)memcpy(snapshot->status, driver_snapshot.status, sizeof(snapshot->status));
    (void)memcpy(snapshot->mask, driver_snapshot.mask, sizeof(snapshot->mask));
    snapshot->combined_status = driver_snapshot.combinedStatus;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read all programming registers of one logical DMA channel for diagnostics.
 *
 * @param[in] controller_id Stable logical DMA controller identifier.
 * @param[in] channel_id Logical channel to observe.
 * @param[out] snapshot Caller-owned normalized channel-register snapshot.
 *
 * @note The Driver test extension reads SAR/DAR/LLP/CTL/CFG/gather/scatter registers only and does not alter transfer state.
 *
 * @return ET_WRAP_STATUS_OK for a complete snapshot, otherwise mapping/validation/Driver status.
 */
et_wrap_status_t et_dma_wrap_get_channel_snapshot(et_dma_wrap_controller_id_t controller_id,
                                                  et_dma_wrap_channel_id_t channel_id,
                                                  et_dma_wrap_channel_snapshot_t *snapshot)
{
    AHBDMA_TestChannelSnapshot_TypeDef driver_snapshot;
    AHBDMA_Type *controller;
    et_wrap_status_t status;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(snapshot, 0, sizeof(*snapshot));
    status = map_controller(controller_id, &controller);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = validate_channel(controller_id, channel_id);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status =
        map_driver_status(AHBDMA_testGetChannelSnapshot(controller, channel_id, &driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    snapshot->source_address = driver_snapshot.sar;
    snapshot->destination_address = driver_snapshot.dar;
    snapshot->linked_list_address = driver_snapshot.llp;
    snapshot->control_low = driver_snapshot.ctlLow;
    snapshot->control_high = driver_snapshot.ctlHigh;
    snapshot->config_low = driver_snapshot.cfgLow;
    snapshot->config_high = driver_snapshot.cfgHigh;
    snapshot->source_gather = driver_snapshot.sourceGather;
    snapshot->destination_scatter = driver_snapshot.destinationScatter;
    snapshot->source_burst = driver_snapshot.sourceBurst;
    snapshot->destination_burst = driver_snapshot.destinationBurst;
    snapshot->block_size = driver_snapshot.blockSize;
    snapshot->fifo_mode = driver_snapshot.fifoMode;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Encode one trusted DMA linked-list descriptor from the chip-neutral configuration.
 *
 * @param[in] config Versioned DMA Wrap configuration used to derive descriptor control fields.
 * @param[in] descriptor_address Trusted, aligned target address where the Driver descriptor is written.
 * @param[in] is_last Canonical 0/1 flag selecting final-descriptor semantics.
 *
 * @note This function validates 32-bit Driver addressability, builds a Driver channel configuration, copies descriptor-relevant fields and writes the descriptor through AHBDMA_initLLI(). It does not start a DMA channel.
 *
 * @return ET_WRAP_STATUS_OK when the descriptor is initialized, otherwise normalized validation/Driver status.
 */
et_wrap_status_t et_dma_wrap_init_lli_descriptor(const et_dma_wrap_config_t *config,
                                                 uintptr_t descriptor_address, uint8_t is_last)
{
    AHBDMA_Ch_Init_TypeDef channel_config;
    AHBDMA_LLI_Init_TypeDef lli_config;
    AHBDMA_LLI_TypeDef *descriptor;
    et_wrap_status_t status;

    /* Phase 1: Validate the versioned configuration, descriptor address and last-descriptor flag. */
    status = validate_config_header(config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((descriptor_address > (uintptr_t)UINT32_MAX) ||
        ((descriptor_address & (sizeof(uint32_t) - 1u)) != 0u) ||
        ((is_last != 0u) && (is_last != 1u)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Reuse the validated Driver channel configuration as the descriptor source of truth. */
    status = build_driver_config(config, &channel_config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 3: Copy descriptor-relevant Driver fields and write the trusted target descriptor. */
    AHBDMA_initLLIStruct(&lli_config);
    lli_config.sar = channel_config.sar;
    lli_config.dar = channel_config.dar;
    lli_config.intEn = ENABLE;
    lli_config.srcTrWidth = channel_config.srcTrWidth;
    lli_config.dstTrWidth = channel_config.dstTrWidth;
    lli_config.srcAddressInc = channel_config.srcAddressInc;
    lli_config.dstAddressInc = channel_config.dstAddressInc;
    lli_config.srcBurstDataItemsNum = channel_config.srcBurstDataItemsNum;
    lli_config.dstBurstDataItemsNum = channel_config.dstBurstDataItemsNum;
    lli_config.dstScatterEn = channel_config.dstScatterEn;
    lli_config.srcGatherEn = channel_config.srcGatherEn;
    lli_config.tfrType = channel_config.tfrType;
    lli_config.dstLLPEn = channel_config.dstLLPEn;
    lli_config.srcLLPEn = channel_config.srcLLPEn;
    lli_config.blkTfrSize = channel_config.blkTfrSize;
    lli_config.wbDoneEn = channel_config.wbDoneEn;
    descriptor = (AHBDMA_LLI_TypeDef *)descriptor_address;
    AHBDMA_initLLI(descriptor, &lli_config, is_last != 0u, (uint32_t)config->linked_list_address);

    return ET_WRAP_STATUS_OK;
}
