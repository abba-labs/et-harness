#ifndef ET_CAN_WRAP_H
#define ET_CAN_WRAP_H

/** @file et_can_wrap.h @brief Chip-neutral, non-waiting CAN controller primitives. */
#include <stdint.h>
#include "et_wrap_status.h"

/** Logical controller identity from Capability; never an external CAN-box channel. */
typedef uint16_t et_can_id_t;

/** Actual time-quanta counts and prescaler; hardware minus-one encoding is private. */
typedef struct
{
    uint32_t prescaler;
    uint32_t segment1;
    uint32_t segment2;
    uint32_t sjw;
} et_can_bit_timing_t;

/** Arbitration and data-phase timing are independent, including when BRS is disabled. */
typedef struct
{
    et_can_bit_timing_t nominal;
    et_can_bit_timing_t data;
} et_can_timing_t;

/** Inclusive limits in the same physical units as et_can_timing_t. */
typedef struct
{
    et_can_bit_timing_t nominal_max;
    et_can_bit_timing_t data_max;
} et_can_timing_limits_t;

/** Immutable revision and endian identities read from the selected controller. */
typedef struct
{
    uint32_t revision;
    uint32_t endian;
} et_can_identity_t;

/** Independent core controls; all Boolean fields require exactly zero or one. */
typedef struct
{
    uint32_t fd_enabled;
    uint32_t brs_enabled;
    uint32_t automatic_retry;
    uint32_t tx_pause;
    uint32_t edge_filter;
    uint32_t protocol_exception;
    uint32_t tdc_enabled;
    uint32_t tdc_offset_cycles;
    uint32_t tdc_filter_cycles;
    uint32_t ram_watchdog_cycles;
} et_can_options_t;

/** Hardware limits in controller clock cycles, not PC polling or timeout budgets. */
typedef struct
{
    uint32_t tdc_offset_cycles;
    uint32_t tdc_filter_cycles;
    uint32_t ram_watchdog_cycles;
} et_can_option_limits_t;

et_wrap_status_t et_can_wrap_get_identity(et_can_id_t id, et_can_identity_t *identity);
et_wrap_status_t et_can_wrap_set_initializing(et_can_id_t id, uint8_t initializing);
et_wrap_status_t et_can_wrap_get_initializing(et_can_id_t id, uint8_t *initializing);
et_wrap_status_t et_can_wrap_get_timing_limits(et_can_id_t id, et_can_timing_limits_t *limits);
et_wrap_status_t et_can_wrap_set_timing(et_can_id_t id, const et_can_timing_t *timing);
et_wrap_status_t et_can_wrap_get_timing(et_can_id_t id, et_can_timing_t *timing);
et_wrap_status_t et_can_wrap_set_options(et_can_id_t id, const et_can_options_t *options);
et_wrap_status_t et_can_wrap_get_options(et_can_id_t id, et_can_options_t *options);
et_wrap_status_t et_can_wrap_get_option_limits(et_can_id_t id, et_can_option_limits_t *limits);

/** Message RAM byte offsets and counts; never physical CPU addresses.
 * Disabled count-bearing regions use count zero. Dedicated RX storage has no
 * hardware count field and reserves the published rx_buffer_count maximum.
 * Payload capacities are bytes; queue and overwrite fields are Boolean.
 */
typedef struct
{
    uint32_t std_offset;
    uint32_t std_count;
    uint32_t ext_offset;
    uint32_t ext_count;
    uint32_t tx_offset;
    uint32_t tx_buffer_count;
    uint32_t tx_fifo_count;
    uint32_t tx_queue;
    uint32_t tx_payload_bytes;
    uint32_t event_offset;
    uint32_t event_count;
    uint32_t event_watermark;
    uint32_t rx0_offset;
    uint32_t rx0_count;
    uint32_t rx0_watermark;
    uint32_t rx0_overwrite;
    uint32_t rx1_offset;
    uint32_t rx1_count;
    uint32_t rx1_watermark;
    uint32_t rx1_overwrite;
    uint32_t rx_buffer_offset;
    uint32_t rx_buffer_payload_bytes;
    uint32_t rx0_payload_bytes;
    uint32_t rx1_payload_bytes;
} et_can_ram_layout_t;

/** Architectural region maxima, not a default test layout. */
typedef struct
{
    uint32_t ram_bytes;
    uint32_t std_count;
    uint32_t ext_count;
    uint32_t tx_count;
    uint32_t rx_fifo_count;
    uint32_t event_count;
    uint32_t rx_buffer_count;
} et_can_ram_limits_t;

et_wrap_status_t et_can_wrap_get_ram_limits(et_can_id_t id, et_can_ram_limits_t *limits);
et_wrap_status_t et_can_wrap_set_ram_layout(et_can_id_t id, const et_can_ram_layout_t *layout);
et_wrap_status_t et_can_wrap_get_ram_layout(et_can_id_t id, et_can_ram_layout_t *layout);

#endif
