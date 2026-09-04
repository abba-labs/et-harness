#ifndef ET_SPI_WRAP_H
#define ET_SPI_WRAP_H

/** @file et_spi_wrap.h @brief Chip-neutral, non-waiting SPI primitive operations. */
#include <stdint.h>
#include "et_wrap_status.h"
#include "et_irq_types.h"

/** Logical identity supplied by the caller and resolved by the chip mapping. */
typedef uint16_t et_spi_id_t;

/** Public option values are translated through chip tables, not register casts. */
enum
{
    ET_SPI_TARGET = 0u,
    ET_SPI_CONTROLLER = 1u
};
enum
{
    ET_SPI_MOTOROLA = 0u,
    ET_SPI_TI = 1u,
    ET_SPI_MICROWIRE = 2u
};
enum
{
    ET_SPI_MODE0 = 0u,
    ET_SPI_MODE1,
    ET_SPI_MODE2,
    ET_SPI_MODE3
};
enum
{
    ET_SPI_TX_RX = 0u,
    ET_SPI_TX_ONLY,
    ET_SPI_RX_ONLY,
    ET_SPI_EEPROM_READ
};
enum
{
    ET_SPI_CS_AUTO = 0u,
    ET_SPI_CS_HOLD,
    ET_SPI_CS_TOGGLE
};

/** Stable interrupt sources; actual IMR/ISR bit positions remain chip facts. */
enum
{
    ET_SPI_IRQ_TX_EMPTY = 1u << 0,
    ET_SPI_IRQ_TX_OVERFLOW = 1u << 1,
    ET_SPI_IRQ_RX_UNDERFLOW = 1u << 2,
    ET_SPI_IRQ_RX_OVERFLOW = 1u << 3,
    ET_SPI_IRQ_RX_FULL = 1u << 4,
    ET_SPI_IRQ_COLLISION = 1u << 5,
    ET_SPI_IRQ_ALL = (1u << 6) - 1u
};

enum
{
    ET_SPI_STATUS_BUSY = 1u << 0,
    ET_SPI_STATUS_TX_NOT_FULL = 1u << 1,
    ET_SPI_STATUS_TX_EMPTY = 1u << 2,
    ET_SPI_STATUS_RX_NOT_EMPTY = 1u << 3,
    ET_SPI_STATUS_RX_FULL = 1u << 4,
    ET_SPI_STATUS_TARGET_TX_ERROR = 1u << 5,
    ET_SPI_STATUS_COLLISION = 1u << 6
};

/** Counts are frames, delay is input-clock cycles; every Boolean must be 0/1. */
typedef struct
{
    uint32_t role, frame_format, clock_mode, transfer_mode;
    uint32_t frame_bits, frame_count, divider, cs_policy;
    uint32_t target_output_enabled, loopback, rx_sample_delay;
    uint32_t control_bits, sequential, transmit, handshake;
    uint32_t reserved;
} et_spi_config_t;

typedef struct
{
    uint32_t frame_bits_min, frame_bits_max, fifo_depth;
    uint32_t divider_min, divider_max, frame_count_max, rx_delay_max;
} et_spi_limits_t;

/** Inclusive programmable thresholds, independent of physical FIFO capacity. */
typedef struct
{
    uint32_t tx_irq_max, rx_irq_max, tx_start_max, dma_tx_max, dma_rx_max;
} et_spi_fifo_limits_t;

/** No read-clear status appears in this non-destructive view. */
typedef struct
{
    uint32_t enabled, selected, tx_level, rx_level;
    uint32_t tx_threshold, rx_threshold, start_threshold;
    uint32_t irq_raw, irq_status, irq_enabled;
    uint32_t dma_tx_enabled, dma_rx_enabled, dma_tx_threshold, dma_rx_threshold;
} et_spi_snapshot_t;

et_wrap_status_t et_spi_wrap_get_limits(et_spi_id_t id, et_spi_limits_t *limits);
et_wrap_status_t et_spi_wrap_get_fifo_limits(et_spi_id_t id, et_spi_fifo_limits_t *limits);
et_wrap_status_t et_spi_wrap_configure(et_spi_id_t id, const et_spi_config_t *config);
et_wrap_status_t et_spi_wrap_get_config(et_spi_id_t id, et_spi_config_t *config);
et_wrap_status_t et_spi_wrap_set_loopback(et_spi_id_t id, uint8_t enabled);
et_wrap_status_t et_spi_wrap_set_fifo_thresholds(et_spi_id_t id, uint8_t tx, uint8_t rx,
                                                 uint8_t start);
et_wrap_status_t et_spi_wrap_get_snapshot(et_spi_id_t id, et_spi_snapshot_t *snapshot);
et_wrap_status_t et_spi_wrap_read_error_status(et_spi_id_t id, uint32_t *raw, uint32_t *flags);
et_wrap_status_t et_spi_wrap_set_irq_enabled(et_spi_id_t id, uint32_t sources, uint8_t enabled);
et_wrap_status_t et_spi_wrap_clear_irq(et_spi_id_t id, uint32_t sources);
et_wrap_status_t et_spi_wrap_get_irq_route(et_spi_id_t id, et_irq_route_t *route);
et_wrap_status_t et_spi_wrap_get_dma_endpoint(et_spi_id_t id, uintptr_t *address);

et_wrap_status_t et_spi_wrap_set_enabled(et_spi_id_t id, uint8_t enabled);
et_wrap_status_t et_spi_wrap_reset_fifo(et_spi_id_t id);
et_wrap_status_t et_spi_wrap_set_divider(et_spi_id_t id, uint32_t divider);
et_wrap_status_t et_spi_wrap_set_frame_count(et_spi_id_t id, uint32_t frame_count);
et_wrap_status_t et_spi_wrap_set_cs_selected(et_spi_id_t id, uint8_t selected);
et_wrap_status_t et_spi_wrap_try_write_frame(et_spi_id_t id, uint32_t frame, uint8_t *written);
et_wrap_status_t et_spi_wrap_try_read_frame(et_spi_id_t id, uint32_t *frame, uint8_t *received);
et_wrap_status_t et_spi_wrap_test_fifo_write_once(et_spi_id_t id, uint32_t frame);
et_wrap_status_t et_spi_wrap_test_fifo_read_once(et_spi_id_t id, uint32_t *frame);
et_wrap_status_t et_spi_wrap_configure_dma(et_spi_id_t id, uint8_t tx_enabled, uint8_t rx_enabled,
                                           uint8_t tx_threshold, uint8_t rx_threshold);

#endif
