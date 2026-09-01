#ifndef ET_FMAC_WRAP_H
#define ET_FMAC_WRAP_H

/**
 * @file et_fmac_wrap.h
 * @brief Stable, chip-independent FMAC operations used by FMAC Service.
 *
 * Public values describe FMAC semantics only. SDK types, register fields,
 * physical IRQ lines and selected-chip limits stay behind Chip Config.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_FMAC_WRAP_API_VERSION 1u
#define ET_FMAC_WRAP_CONFIG_RESERVED_WORDS 2u
#define ET_FMAC_WRAP_MAX_TRANSFER_ITEMS 255u
#define ET_FMAC_WRAP_ALIGNMENT_UNKNOWN UINT8_MAX

/* Stable capability bits published by every FMAC adaptation. */
#define ET_FMAC_WRAP_CAP_FIXED_Q15 (1u << 0)
#define ET_FMAC_WRAP_CAP_FLOAT_INPUT (1u << 1)
#define ET_FMAC_WRAP_CAP_FLOAT_OUTPUT (1u << 2)
#define ET_FMAC_WRAP_CAP_FIR (1u << 3)
#define ET_FMAC_WRAP_CAP_IIR (1u << 4)
#define ET_FMAC_WRAP_CAP_STREAM (1u << 5)
#define ET_FMAC_WRAP_CAP_CLEAR (1u << 6)
#define ET_FMAC_WRAP_CAP_OUTPUT_POLICY (1u << 7)
#define ET_FMAC_WRAP_CAP_STATUS (1u << 8)
#define ET_FMAC_WRAP_CAP_INTERRUPTS (1u << 9)
#define ET_FMAC_WRAP_CAP_DMA_REQUEST (1u << 10)
#define ET_FMAC_WRAP_CAP_TIMED_PROCESS (1u << 11)
#define ET_FMAC_WRAP_CAP_TEST_EXTENSIONS (1u << 12)

/** Stable logical FMAC instance identifier. */
typedef uint8_t et_fmac_id_t;

/** FMAC function selectors that have stable cross-chip semantics. */
typedef enum
{
    ET_FMAC_WRAP_FUNCTION_LOAD_X1 = 1u,
    ET_FMAC_WRAP_FUNCTION_LOAD_X2 = 2u,
    ET_FMAC_WRAP_FUNCTION_LOAD_Y = 3u,
    ET_FMAC_WRAP_FUNCTION_FIR = 4u,
    ET_FMAC_WRAP_FUNCTION_IIR = 5u
} et_fmac_wrap_function_t;

/** Public X1/Y watermark values are element counts, not Driver encodings. */
typedef enum
{
    ET_FMAC_WRAP_WATERMARK_1 = 1u,
    ET_FMAC_WRAP_WATERMARK_2 = 2u,
    ET_FMAC_WRAP_WATERMARK_4 = 4u,
    ET_FMAC_WRAP_WATERMARK_8 = 8u
} et_fmac_wrap_watermark_t;

/** Final Q15 overflow policy. */
typedef enum
{
    ET_FMAC_WRAP_FINAL_SATURATE = 0u,
    ET_FMAC_WRAP_FINAL_WRAP = 1u
} et_fmac_wrap_final_policy_t;

/** Output post-processing mode. */
typedef enum
{
    ET_FMAC_WRAP_OUTPUT_RAW = 0u,
    ET_FMAC_WRAP_OUTPUT_SAT12 = 1u,
    ET_FMAC_WRAP_OUTPUT_SAT16 = 2u
} et_fmac_wrap_output_mode_t;

/** Public shift codes map LEFT8 through RIGHT7 onto 0 through 15. */
typedef enum
{
    ET_FMAC_WRAP_SHIFT_LEFT8 = 0u,
    ET_FMAC_WRAP_SHIFT_LEFT7 = 1u,
    ET_FMAC_WRAP_SHIFT_LEFT6 = 2u,
    ET_FMAC_WRAP_SHIFT_LEFT5 = 3u,
    ET_FMAC_WRAP_SHIFT_LEFT4 = 4u,
    ET_FMAC_WRAP_SHIFT_LEFT3 = 5u,
    ET_FMAC_WRAP_SHIFT_LEFT2 = 6u,
    ET_FMAC_WRAP_SHIFT_LEFT1 = 7u,
    ET_FMAC_WRAP_SHIFT_NONE = 8u,
    ET_FMAC_WRAP_SHIFT_RIGHT1 = 9u,
    ET_FMAC_WRAP_SHIFT_RIGHT2 = 10u,
    ET_FMAC_WRAP_SHIFT_RIGHT3 = 11u,
    ET_FMAC_WRAP_SHIFT_RIGHT4 = 12u,
    ET_FMAC_WRAP_SHIFT_RIGHT5 = 13u,
    ET_FMAC_WRAP_SHIFT_RIGHT6 = 14u,
    ET_FMAC_WRAP_SHIFT_RIGHT7 = 15u
} et_fmac_wrap_shift_t;

/* Stable FMAC IRQ source bits. */
#define ET_FMAC_WRAP_IRQ_X1_WRITE_REQUEST (1u << 0)
#define ET_FMAC_WRAP_IRQ_Y_READ_REQUEST (1u << 1)
#define ET_FMAC_WRAP_IRQ_SATURATION (1u << 2)
#define ET_FMAC_WRAP_IRQ_X1_OVERFLOW (1u << 3)
#define ET_FMAC_WRAP_IRQ_Y_UNDERFLOW (1u << 4)
#define ET_FMAC_WRAP_IRQ_P_ERROR (1u << 5)
#define ET_FMAC_WRAP_IRQ_PQ_ERROR (1u << 6)
#define ET_FMAC_WRAP_IRQ_Q_ERROR (1u << 7)
#define ET_FMAC_WRAP_IRQ_X1_LOAD_ERROR (1u << 8)
#define ET_FMAC_WRAP_IRQ_X2_LOAD_ERROR (1u << 9)
#define ET_FMAC_WRAP_IRQ_Y_LOAD_ERROR (1u << 10)
#define ET_FMAC_WRAP_IRQ_ALL ((1u << 11) - 1u)

#define ET_FMAC_WRAP_DMA_INPUT (1u << 0)
#define ET_FMAC_WRAP_DMA_OUTPUT (1u << 1)
#define ET_FMAC_WRAP_DMA_ALL (ET_FMAC_WRAP_DMA_INPUT | ET_FMAC_WRAP_DMA_OUTPUT)

/** Versioned complete FMAC quasi-static configuration. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    et_fmac_id_t fmac_id;
    uint8_t x1_start;
    uint8_t x1_size;
    uint8_t x1_full_watermark;
    uint8_t x2_start;
    uint8_t x2_size;
    uint8_t y_start;
    uint8_t y_size;
    uint8_t y_empty_watermark;
    uint8_t final_policy;
    uint8_t output_mode;
    uint8_t internal_clip;
    uint8_t float_input;
    uint8_t float_output;
    uint8_t output_shift;
    uint16_t output_offset;
    uint32_t reserved[ET_FMAC_WRAP_CONFIG_RESERVED_WORDS];
} et_fmac_wrap_config_t;

#define ET_FMAC_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_fmac_wrap_config_t, reserved))

/** Runtime FMAC capabilities normalized to stable public semantics. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t feature_flags;
    uint16_t max_transfer_items;
    uint8_t logical_address_bits;
    uint8_t max_feedforward_taps;
    uint8_t max_feedback_taps;
    uint8_t watermark_mask;
    uint8_t output_mode_mask;
    uint8_t shift_mask_width;
    uint16_t irq_source_mask;
    uint8_t fir_first_valid_output_index;
    uint8_t iir_first_valid_output_index;
} et_fmac_wrap_capabilities_t;

/** FMAC configuration readback normalized to the public configuration fields. */
typedef et_fmac_wrap_config_t et_fmac_wrap_config_snapshot_t;

/** FMAC hardware state sampled without clearing sticky reports. */
typedef struct
{
    uint8_t active;
    uint8_t x1_spare_count;
    uint8_t y_unread_count;
    uint8_t x1_full;
    uint8_t y_empty;
    uint8_t x1_overflow;
    uint8_t y_underflow;
    uint8_t accumulator_saturation;
    uint8_t negative_after_offset;
    uint8_t float_to_q15_overflow;
    uint16_t reserved;
} et_fmac_wrap_status_snapshot_t;

/** Raw/effective IRQ snapshot from the selected FMAC instance. */
typedef struct
{
    uint32_t raw;
    uint32_t status;
} et_fmac_wrap_irq_snapshot_t;

et_wrap_status_t et_fmac_wrap_get_capabilities(et_fmac_id_t fmac_id,
                                               et_fmac_wrap_capabilities_t *capabilities);
et_wrap_status_t et_fmac_wrap_configure(et_fmac_id_t fmac_id, const et_fmac_wrap_config_t *config);
et_wrap_status_t et_fmac_wrap_config_snapshot_get(et_fmac_id_t fmac_id,
                                                  et_fmac_wrap_config_snapshot_t *snapshot);
et_wrap_status_t et_fmac_wrap_start(et_fmac_id_t fmac_id, uint8_t function,
                                    uint8_t feedforward_taps, uint8_t feedback_taps);
et_wrap_status_t et_fmac_wrap_start_unchecked(et_fmac_id_t fmac_id, uint8_t function,
                                              uint8_t feedforward_taps, uint8_t feedback_taps);
et_wrap_status_t et_fmac_wrap_stop(et_fmac_id_t fmac_id);
et_wrap_status_t et_fmac_wrap_clear(et_fmac_id_t fmac_id);
et_wrap_status_t et_fmac_wrap_x1_preload(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                         uint8_t use_float, uint32_t timeout_budget);
et_wrap_status_t et_fmac_wrap_coefficients_load(et_fmac_id_t fmac_id, const int16_t *feedforward,
                                                uint8_t feedforward_count, const int16_t *feedback,
                                                uint8_t feedback_count, uint32_t timeout_budget);
et_wrap_status_t et_fmac_wrap_y_preload(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                        uint8_t use_float, uint32_t timeout_budget);
et_wrap_status_t et_fmac_wrap_stream_write(et_fmac_id_t fmac_id, const void *data, uint8_t count,
                                           uint8_t use_float, uint32_t *accepted_count);
et_wrap_status_t et_fmac_wrap_stream_read(et_fmac_id_t fmac_id, void *data, uint8_t count,
                                          uint8_t use_float, uint32_t *read_count);
et_wrap_status_t et_fmac_wrap_data_write_one_unchecked(et_fmac_id_t fmac_id, uint32_t raw_value);
et_wrap_status_t et_fmac_wrap_data_read_one_unchecked(et_fmac_id_t fmac_id, uint32_t *raw_value);
et_wrap_status_t et_fmac_wrap_status_get(et_fmac_id_t fmac_id,
                                         et_fmac_wrap_status_snapshot_t *snapshot);
et_wrap_status_t et_fmac_wrap_get_irq_route(et_fmac_id_t fmac_id, et_irq_route_t *route);
et_wrap_status_t et_fmac_wrap_irq_enable(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_disable(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_mask(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_unmask(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_force(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_clear(et_fmac_id_t fmac_id, uint32_t source_bits);
et_wrap_status_t et_fmac_wrap_irq_snapshot_get(et_fmac_id_t fmac_id,
                                               et_fmac_wrap_irq_snapshot_t *snapshot);
et_wrap_status_t et_fmac_wrap_dma_request_set(et_fmac_id_t fmac_id, uint32_t request_bits);
et_wrap_status_t et_fmac_wrap_process_timed(et_fmac_id_t fmac_id, uint8_t function,
                                            uint8_t feedforward_taps, uint8_t feedback_taps,
                                            const void *source, void *destination, uint16_t count,
                                            uint8_t use_float, uint32_t timeout_budget,
                                            uint32_t *accepted_count, uint32_t *read_count,
                                            uint32_t *elapsed_cycles);

#endif
