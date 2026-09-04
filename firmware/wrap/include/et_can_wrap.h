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

/** Stable timestamp sources; not raw register selectors. */
typedef enum
{
    ET_CAN_TIMESTAMP_DISABLED = 0u,
    ET_CAN_TIMESTAMP_INTERNAL = 1u,
    ET_CAN_TIMESTAMP_EXTERNAL = 2u,
    ET_CAN_TIMESTAMP_SOURCE_COUNT
} et_can_timestamp_source_t;

/** A timeout may run continuously or be gated by one hardware FIFO. */
typedef enum
{
    ET_CAN_TIMEOUT_CONTINUOUS = 0u,
    ET_CAN_TIMEOUT_TX_EVENT = 1u,
    ET_CAN_TIMEOUT_RX0 = 2u,
    ET_CAN_TIMEOUT_RX1 = 3u,
    ET_CAN_TIMEOUT_SOURCE_COUNT
} et_can_timeout_source_t;

/** Stable global non-matching-frame policy, independent of individual ID filters. */
typedef enum
{
    ET_CAN_UNMATCHED_RX0 = 0u,
    ET_CAN_UNMATCHED_RX1 = 1u,
    ET_CAN_UNMATCHED_REJECT = 2u,
    ET_CAN_UNMATCHED_POLICY_COUNT
} et_can_unmatched_policy_t;

/** Loopback controls are separate from INIT; disabled exits MON loopback isolation. */
typedef enum
{
    ET_CAN_LOOPBACK_DISABLED = 0u,
    ET_CAN_LOOPBACK_INTERNAL = 1u,
    ET_CAN_LOOPBACK_EXTERNAL = 2u
} et_can_loopback_t;

/** One complete existing Driver configuration group, with explicit physical timer units. */
typedef struct
{
    uint32_t monitor;
    uint32_t restricted;
    uint32_t timestamp_divisor;
    uint32_t timestamp_source;
    uint32_t timeout_source;
    uint32_t timeout_period;
    uint32_t timeout_enabled;
    uint32_t reject_remote_ext;
    uint32_t reject_remote_std;
    uint32_t unmatched_ext;
    uint32_t unmatched_std;
} et_can_bus_config_t;

/** Timer count limits; source selectors are the public enums above. */
typedef struct
{
    uint32_t timestamp_divisor;
    uint32_t timeout_period;
} et_can_bus_limits_t;

et_wrap_status_t et_can_wrap_set_bus_config(et_can_id_t id, const et_can_bus_config_t *config);
et_wrap_status_t et_can_wrap_get_bus_config(et_can_id_t id, et_can_bus_config_t *config);
et_wrap_status_t et_can_wrap_get_bus_limits(et_can_id_t id, et_can_bus_limits_t *limits);
et_wrap_status_t et_can_wrap_set_loopback(et_can_id_t id, et_can_loopback_t mode);
et_wrap_status_t et_can_wrap_get_loopback(et_can_id_t id, et_can_loopback_t *mode);

#endif
