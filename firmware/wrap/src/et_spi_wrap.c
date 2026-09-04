/** @file et_spi_wrap.c @brief Translate SPI primitives into the selected SPI Driver. */
#include "et_spi_wrap.h"

#include <stddef.h>
#include "et6x_spi.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_spi_id_t id;
    SPI_Type *instance;
    et_irq_line_t irq_line;
} et_spi_mapping_t;

static const et_spi_mapping_t mappings[] = ET_CHIP_SPI_MAP_TABLE;

typedef struct
{
    uint32_t semantic, driver;
} et_spi_bit_mapping_t;
typedef struct
{
    uint32_t tx_mask, start_mask, start_shift, dma_tx_mask, dma_rx_mask;
} et_spi_snapshot_mapping_t;

static const uint32_t role_map[] = ET_CHIP_SPI_ROLE_MAP_TABLE;
static const uint32_t format_map[] = ET_CHIP_SPI_FORMAT_MAP_TABLE;
static const uint32_t clock_map[] = ET_CHIP_SPI_CLOCK_MAP_TABLE;
static const uint32_t transfer_map[] = ET_CHIP_SPI_TRANSFER_MAP_TABLE;
static const uint32_t cs_map[] = ET_CHIP_SPI_CS_MAP_TABLE;
static const et_spi_bit_mapping_t irq_map[] = ET_CHIP_SPI_IRQ_MAP_TABLE;
static const et_spi_bit_mapping_t status_map[] = ET_CHIP_SPI_STATUS_MAP_TABLE;
static const et_spi_snapshot_mapping_t snapshot_map = ET_CHIP_SPI_SNAPSHOT_MAP_TABLE;
static const et_spi_limits_t chip_limits = ET_CHIP_SPI_LIMIT_MAP_TABLE;

/** Compile-time array length, not a hardware instance assumption. */
#define ET_SPI_ARRAY_COUNT(value) (sizeof(value) / sizeof((value)[0]))

/**
 * @brief Resolve a public SPI identity without assuming physical numbering.
 * @param[in] id Logical SPI identity.
 * @return Selected Driver instance, or NULL for an unsupported identity.
 * @note Only immutable chip facts are inspected; no hardware is touched.
 */
static SPI_Type *find_instance(et_spi_id_t id)
{
    size_t index;

    for (index = 0u; index < sizeof(mappings) / sizeof(mappings[0]); ++index)
    {
        if (mappings[index].id == id)
        {
            return mappings[index].instance;
        }
    }

    return NULL;
}

/**
 * @brief Preserve the Driver outcome in the public Wrap status vocabulary.
 * @param[in] status Result of one Driver action.
 * @return Success, argument error, busy or I/O error.
 * @note No retry, reset or error-to-success conversion is performed.
 */
static et_wrap_status_t status_from_driver(DRV_Status status)
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
 * @brief Enable or disable one SPI instance.
 * @param[in] id Logical SPI identity.
 * @param[in] enabled Boolean module enable.
 * @return Success, invalid argument or unsupported instance.
 * @note Disable can discard queued frames; the caller owns sequencing and observations.
 */
et_wrap_status_t et_spi_wrap_set_enabled(et_spi_id_t id, uint8_t enabled)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (enabled != 0u)
    {
        SPI_enableModule(instance);
    }
    else
    {
        SPI_disableModule(instance);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reset both SPI FIFOs using the selected Driver operation.
 * @param[in] id Logical SPI identity.
 * @return Success or unsupported instance.
 * @note Discards queued TX/RX frames; it is not a complete IP or resource-pool reset.
 */
et_wrap_status_t et_spi_wrap_reset_fifo(et_spi_id_t id)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    SPI_resetFIFO(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Set an exact input-clock divisor while SPI is disabled.
 * @param[in] id Logical SPI identity.
 * @param[in] divider Requested divisor; representable values come from Capability.
 * @return Mapped Driver result or unsupported instance.
 * @note An enabled module returns BUSY; this action never resets FIFO.
 */
et_wrap_status_t et_spi_wrap_set_divider(et_spi_id_t id, uint32_t divider)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testSetDivider(instance, divider));
}

/**
 * @brief Set the actual number of Controller receive frames.
 * @param[in] id Logical SPI identity.
 * @param[in] frame_count Positive frame count, not a register encoding.
 * @return Mapped Driver result or unsupported instance.
 * @note The Driver owns encoding and rejects an enabled module without resetting FIFO.
 */
et_wrap_status_t et_spi_wrap_set_frame_count(et_spi_id_t id, uint32_t frame_count)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testSetFrameCount(instance, frame_count));
}

/**
 * @brief Select or release the SPI hardware chip select.
 * @param[in] id Logical SPI identity.
 * @param[in] selected Boolean selection request, not a GPIO output level.
 * @return Mapped Driver result or unsupported instance.
 * @note Selection does not reconfigure SPI or clear queued FIFO data.
 */
et_wrap_status_t et_spi_wrap_set_cs_selected(et_spi_id_t id, uint8_t selected)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testSelectCS(instance, selected));
}

/**
 * @brief Attempt one normal FIFO write without waiting for bus progress.
 * @param[in] id Logical SPI identity.
 * @param[in] frame One frame value; hardware retains its configured valid bits.
 * @param[out] written One when accepted, zero when not ready.
 * @return Mapped Driver result or unsupported instance.
 * @note FIFO acceptance is not serial completion. No destructive error-status read is made.
 */
et_wrap_status_t et_spi_wrap_try_write_frame(et_spi_id_t id, uint32_t frame, uint8_t *written)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testTryWriteFrame(instance, frame, written));
}

/**
 * @brief Attempt one normal FIFO read without waiting for incoming data.
 * @param[in] id Logical SPI identity.
 * @param[out] frame Received value, or zero when FIFO is empty.
 * @param[out] received One when a frame was read, otherwise zero.
 * @return Mapped Driver result or unsupported instance.
 * @note Consumes at most one RX frame; does not read or clear error status.
 */
et_wrap_status_t et_spi_wrap_try_read_frame(et_spi_id_t id, uint32_t *frame, uint8_t *received)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testTryReadFrame(instance, frame, received));
}

/**
 * @brief Write one FIFO frame without a fullness guard for error stimulation.
 * @param[in] id Logical SPI identity.
 * @param[in] frame Stimulus frame value.
 * @return Mapped Driver result or unsupported instance.
 * @note May cause a real FIFO overflow; this is not the normal transmit operation.
 */
et_wrap_status_t et_spi_wrap_test_fifo_write_once(et_spi_id_t id, uint32_t frame)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testWriteFIFOOnce(instance, frame));
}

/**
 * @brief Read one FIFO frame without an emptiness guard for error stimulation.
 * @param[in] id Logical SPI identity.
 * @param[out] frame Value returned by the hardware read.
 * @return Mapped Driver result or unsupported instance.
 * @note May cause a real FIFO underflow; it does not synthesize an error flag.
 */
et_wrap_status_t et_spi_wrap_test_fifo_read_once(et_spi_id_t id, uint32_t *frame)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testReadFIFOOnce(instance, frame));
}

/**
 * @brief Configure independent SPI TX and RX DMA requests.
 * @param[in] id Logical SPI identity.
 * @param[in] tx_enabled Boolean TX request enable.
 * @param[in] rx_enabled Boolean RX request enable.
 * @param[in] tx_threshold TX request threshold in frames.
 * @param[in] rx_threshold RX request threshold encoding in frames; request at threshold plus one.
 * @return Mapped Driver result or unsupported instance.
 * @note Only the SPI request source changes. No DMA channel or other IP is configured.
 */
et_wrap_status_t et_spi_wrap_configure_dma(et_spi_id_t id, uint8_t tx_enabled, uint8_t rx_enabled,
                                           uint8_t tx_threshold, uint8_t rx_threshold)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(
        SPI_testConfigureDMA(instance, tx_enabled, rx_enabled, tx_threshold, rx_threshold));
}

/**
 * @brief Decode a Driver enum through its selected chip table.
 * @param[in] value Driver enum value.
 * @param[in] table Ordered public-to-Driver mapping.
 * @param[in] count Number of entries.
 * @return Public enum or UINT32_MAX when no mapping exists.
 * @note Unknown hardware settings are not silently mapped to defaults.
 */
static uint32_t decode_enum(uint32_t value, const uint32_t *table, size_t count)
{
    size_t index;

    for (index = 0u; index < count; ++index)
    {
        if (table[index] == value)
        {
            return (uint32_t)index;
        }
    }

    return UINT32_MAX;
}

/**
 * @brief Translate independent bits through chip-selected semantic pairs.
 * @param[in] value Input mask.
 * @param[in] table Public and Driver mask pairs.
 * @param[in] count Number of pairs.
 * @param[in] to_driver Nonzero selects public-to-Driver direction.
 * @return Translated mask.
 * @note Does not access hardware; mutations validate public bits first.
 */
static uint32_t translate_bits(uint32_t value, const et_spi_bit_mapping_t *table, size_t count,
                               uint8_t to_driver)
{
    size_t index;
    uint32_t result = 0u;

    for (index = 0u; index < count; ++index)
    {
        uint32_t input = to_driver != 0u ? table[index].semantic : table[index].driver;
        uint32_t output = to_driver != 0u ? table[index].driver : table[index].semantic;

        if ((value & input) != 0u)
        {
            result |= output;
        }
    }

    return result;
}

/**
 * @brief Return static programmable limits of the selected SPI.
 * @param[in] id Logical instance.
 * @param[out] limits Chip ranges, not test coverage.
 * @return Success, invalid pointer or unsupported identity.
 * @note RX delay range is writable width, not proof of physical delay effectiveness.
 */
et_wrap_status_t et_spi_wrap_get_limits(et_spi_id_t id, et_spi_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = chip_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply complete explicit settings to a disabled SPI.
 * @param[in] id Logical instance.
 * @param[in] config Public configuration with reserved word zero.
 * @return Mapped Driver result; invalid enums never reach hardware.
 * @note No implicit enable, CS selection, resource reset or cross-IP action.
 */
et_wrap_status_t et_spi_wrap_configure(et_spi_id_t id, const et_spi_config_t *config)
{
    SPI_Type *instance = find_instance(id);
    SPI_TestConfig decoded;

    /* Phase 1: Validate all table indexes before mapping public options. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (config == NULL || config->reserved != 0u || config->role >= ET_SPI_ARRAY_COUNT(role_map) ||
        config->frame_format >= ET_SPI_ARRAY_COUNT(format_map) ||
        config->clock_mode >= ET_SPI_ARRAY_COUNT(clock_map) ||
        config->transfer_mode >= ET_SPI_ARRAY_COUNT(transfer_map) ||
        config->cs_policy >= ET_SPI_ARRAY_COUNT(cs_map))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Translate the complete settings; Driver checks hardware limits. */
    decoded.role = role_map[config->role];
    decoded.format = format_map[config->frame_format];
    decoded.clockMode = clock_map[config->clock_mode];
    decoded.transferMode = transfer_map[config->transfer_mode];
    decoded.csPolicy = cs_map[config->cs_policy];
    decoded.frameBits = config->frame_bits;
    decoded.frameCount = config->frame_count;
    decoded.divider = config->divider;
    decoded.outputEnabled = config->target_output_enabled;
    decoded.loopback = config->loopback;
    decoded.rxDelay = config->rx_sample_delay;
    decoded.controlBits = config->control_bits;
    decoded.sequential = config->sequential;
    decoded.transmit = config->transmit;
    decoded.handshake = config->handshake;

    return status_from_driver(SPI_testConfigureStopped(instance, &decoded));
}

/**
 * @brief Read and translate current hardware settings without a cached echo.
 * @param[in] id Logical instance.
 * @param[out] config Decoded hardware settings.
 * @return Mapped Driver result or unsupported enum representation.
 * @note Reads neither FIFO data nor read-clear status.
 */
et_wrap_status_t et_spi_wrap_get_config(et_spi_id_t id, et_spi_config_t *config)
{
    SPI_Type *instance = find_instance(id);
    SPI_TestConfig decoded;
    DRV_Status status;

    /* Phase 1: Obtain the Driver's non-destructive hardware readback. */
    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = SPI_testGetConfig(instance, &decoded);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    /* Phase 2: Convert enums through mappings and preserve numeric facts. */
    config->role = decode_enum(decoded.role, role_map, ET_SPI_ARRAY_COUNT(role_map));
    config->frame_format = decode_enum(decoded.format, format_map, ET_SPI_ARRAY_COUNT(format_map));
    config->clock_mode = decode_enum(decoded.clockMode, clock_map, ET_SPI_ARRAY_COUNT(clock_map));
    config->transfer_mode =
        decode_enum(decoded.transferMode, transfer_map, ET_SPI_ARRAY_COUNT(transfer_map));
    config->cs_policy = decode_enum(decoded.csPolicy, cs_map, ET_SPI_ARRAY_COUNT(cs_map));
    config->frame_bits = decoded.frameBits;
    config->frame_count = decoded.frameCount;
    config->divider = decoded.divider;
    config->target_output_enabled = decoded.outputEnabled;
    config->loopback = decoded.loopback;
    config->rx_sample_delay = decoded.rxDelay;
    config->control_bits = decoded.controlBits;
    config->sequential = decoded.sequential;
    config->transmit = decoded.transmit;
    config->handshake = decoded.handshake;
    config->reserved = 0u;

    if (config->role == UINT32_MAX || config->frame_format == UINT32_MAX ||
        config->clock_mode == UINT32_MAX || config->transfer_mode == UINT32_MAX ||
        config->cs_policy == UINT32_MAX)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read FIFO, IRQ and DMA request facts without consuming error status.
 * @param[in] id Logical instance.
 * @param[out] snapshot Non-destructive facts.
 * @return Mapped Driver status.
 * @note BUSY and read-clear errors are deliberately absent from this view.
 */
et_wrap_status_t et_spi_wrap_get_snapshot(et_spi_id_t id, et_spi_snapshot_t *snapshot)
{
    SPI_Type *instance = find_instance(id);
    SPI_TestSnapshot raw;
    DRV_Status status;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = SPI_testGetSnapshot(instance, &raw);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    snapshot->enabled = raw.enabled;
    snapshot->selected = raw.selected;
    snapshot->tx_level = raw.tx_level;
    snapshot->rx_level = raw.rx_level;
    snapshot->tx_threshold = raw.tx_thresholds & snapshot_map.tx_mask;
    snapshot->start_threshold =
        (raw.tx_thresholds & snapshot_map.start_mask) >> snapshot_map.start_shift;
    snapshot->rx_threshold = raw.rx_threshold;
    snapshot->irq_raw = translate_bits(raw.irq_raw, irq_map, ET_SPI_ARRAY_COUNT(irq_map), 0u);
    snapshot->irq_status = translate_bits(raw.irq_status, irq_map, ET_SPI_ARRAY_COUNT(irq_map), 0u);
    snapshot->irq_enabled =
        translate_bits(raw.irq_enabled, irq_map, ET_SPI_ARRAY_COUNT(irq_map), 0u);
    snapshot->dma_tx_enabled = (raw.dma_enabled & snapshot_map.dma_tx_mask) != 0u;
    snapshot->dma_rx_enabled = (raw.dma_enabled & snapshot_map.dma_rx_mask) != 0u;
    snapshot->dma_tx_threshold = raw.dma_tx_threshold;
    snapshot->dma_rx_threshold = raw.dma_rx_threshold;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read destructive hardware status exactly once.
 * @param[in] id Logical instance.
 * @param[out] raw First raw value for evidence.
 * @param[out] flags Stable flags from that same read.
 * @return Mapped Driver result.
 * @note Consumes read-clear errors; subsequent reads are separate observations.
 */
et_wrap_status_t et_spi_wrap_read_error_status(et_spi_id_t id, uint32_t *raw, uint32_t *flags)
{
    SPI_Type *instance = find_instance(id);
    DRV_Status status;

    if (raw == NULL || flags == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = SPI_testReadStatus(instance, raw);

    if (status != DRV_OK)
    {
        return status_from_driver(status);
    }

    *flags = translate_bits(*raw, status_map, ET_SPI_ARRAY_COUNT(status_map), 0u);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or mask selected SPI interrupt sources.
 * @param[in] id Logical instance.
 * @param[in] sources Public source mask.
 * @param[in] enabled Boolean unmask request.
 * @return Success, invalid input or unsupported instance.
 * @note Changes only SPI masks; IRQ Manager owns NVIC and vector binding.
 */
et_wrap_status_t et_spi_wrap_set_irq_enabled(et_spi_id_t id, uint32_t sources, uint8_t enabled)
{
    SPI_Type *instance = find_instance(id);
    uint32_t mask;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (enabled > 1u || (sources & ~ET_SPI_IRQ_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    mask = translate_bits(sources, irq_map, ET_SPI_ARRAY_COUNT(irq_map), 1u);

    if (enabled != 0u)
    {
        SPI_enableInterrupt(instance, mask);
    }
    else
    {
        SPI_disableInterrupt(instance, mask);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge selected SPI interrupt sources.
 * @param[in] id Logical instance.
 * @param[in] sources Public source mask.
 * @return Success, invalid mask or unsupported instance.
 * @note Level sources remain active until their FIFO condition is removed.
 */
et_wrap_status_t et_spi_wrap_clear_irq(et_spi_id_t id, uint32_t sources)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((sources & ~ET_SPI_IRQ_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    SPI_clearInterruptStatus(instance,
                             translate_bits(sources, irq_map, ET_SPI_ARRAY_COUNT(irq_map), 1u));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve the private physical IRQ route for a logical SPI.
 * @param[in] id Logical instance.
 * @param[out] route Route consumed only by Service-to-IRQ-Manager binding.
 * @return Success, invalid output or unsupported instance.
 * @note No IRQ binding occurs here and no physical IRQ number is sent to PC.
 */
et_wrap_status_t et_spi_wrap_get_irq_route(et_spi_id_t id, et_irq_route_t *route)
{
    size_t index;

    if (route == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < ET_SPI_ARRAY_COUNT(mappings); ++index)
    {
        if (mappings[index].id == id)
        {
            route->irq_line = mappings[index].irq_line;
            route->reserved = 0u;
            route->route_events = ET_SPI_IRQ_ALL;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Change internal loopback while SPI is disabled.
 * @param[in] id Logical instance.
 * @param[in] enabled Boolean loopback request.
 * @return Mapped Driver result or unsupported instance.
 * @note No implicit FIFO reset; target still needs external SCLK/CS.
 */
et_wrap_status_t et_spi_wrap_set_loopback(et_spi_id_t id, uint8_t enabled)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testSetLoopbackStopped(instance, enabled));
}

/**
 * @brief Set independent TX IRQ, RX IRQ and TX-start thresholds.
 * @param[in] id Logical instance.
 * @param[in] tx TX IRQ threshold in frames.
 * @param[in] rx RX IRQ threshold, asserted at rx plus one.
 * @param[in] start TX starts when level is greater than start.
 * @return Mapped Driver result or unsupported instance.
 * @note May change live IRQ conditions; never drains FIFO or reads SR.
 */
et_wrap_status_t et_spi_wrap_set_fifo_thresholds(et_spi_id_t id, uint8_t tx, uint8_t rx,
                                                 uint8_t start)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testSetFIFOThresholds(instance, tx, rx, start));
}

/**
 * @brief Resolve the SPI data endpoint for an independent DMA Driver.
 * @param[in] id Logical instance.
 * @param[out] address Peripheral bus address.
 * @return Mapped Driver result or unsupported instance.
 * @note No DMA channel is configured and no peripheral data is read.
 */
et_wrap_status_t et_spi_wrap_get_dma_endpoint(et_spi_id_t id, uintptr_t *address)
{
    SPI_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return status_from_driver(SPI_testGetDMAEndpoint(instance, address));
}
