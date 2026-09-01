#ifndef ET_CORDIC_WRAP_H
#define ET_CORDIC_WRAP_H

/**
 * @file et_cordic_wrap.h
 * @brief Stable, chip-independent CORDIC operations used by CORDIC Service.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_CORDIC_WRAP_API_VERSION 1u
#define ET_CORDIC_WRAP_CONFIG_RESERVED_WORDS 4u

typedef uint16_t et_cordic_id_t;

typedef enum
{
    ET_CORDIC_WRAP_FUNCTION_SINCOS = 0u,
    ET_CORDIC_WRAP_FUNCTION_PHASE_MODULUS = 1u,
    ET_CORDIC_WRAP_FUNCTION_ARCTAN = 2u,
    ET_CORDIC_WRAP_FUNCTION_HSINCOS = 3u,
    ET_CORDIC_WRAP_FUNCTION_ATANH = 4u,
    ET_CORDIC_WRAP_FUNCTION_EXP = 5u,
    ET_CORDIC_WRAP_FUNCTION_LN = 6u,
    ET_CORDIC_WRAP_FUNCTION_SQRT = 7u,
    ET_CORDIC_WRAP_FUNCTION_TAN = 8u
} et_cordic_wrap_function_t;

typedef enum
{
    ET_CORDIC_WRAP_NUMERIC_FIXED = 0u,
    ET_CORDIC_WRAP_NUMERIC_FLOAT32 = 1u
} et_cordic_wrap_numeric_mode_t;

typedef enum
{
    ET_CORDIC_WRAP_WIDTH_16 = 16u,
    ET_CORDIC_WRAP_WIDTH_32 = 32u
} et_cordic_wrap_width_t;

typedef enum
{
    ET_CORDIC_WRAP_RANGE_NORMALIZED = 0u,
    ET_CORDIC_WRAP_RANGE_DIRECT_ANGLE = 1u
} et_cordic_wrap_input_range_t;

typedef enum
{
    ET_CORDIC_WRAP_RESULT_ONE = 1u,
    ET_CORDIC_WRAP_RESULT_TWO = 2u
} et_cordic_wrap_result_count_t;

typedef enum
{
    ET_CORDIC_WRAP_WORK_INTERRUPT = 0u,
    ET_CORDIC_WRAP_WORK_POLLING = 1u,
    ET_CORDIC_WRAP_WORK_ZERO_OVERHEAD = 2u,
    ET_CORDIC_WRAP_WORK_DMA = 3u
} et_cordic_wrap_work_mode_t;

#define ET_CORDIC_WRAP_IRQ_ARG_OVERFLOW (1u << 0)
#define ET_CORDIC_WRAP_IRQ_CALCULATION_COMPLETE (1u << 1)
#define ET_CORDIC_WRAP_IRQ_PM_ARG2_ERROR (1u << 2)
#define ET_CORDIC_WRAP_IRQ_ALL                                                                     \
    (ET_CORDIC_WRAP_IRQ_ARG_OVERFLOW | ET_CORDIC_WRAP_IRQ_CALCULATION_COMPLETE |                   \
     ET_CORDIC_WRAP_IRQ_PM_ARG2_ERROR)

#define ET_CORDIC_WRAP_STATUS_ARG_OVERFLOW (1u << 0)
#define ET_CORDIC_WRAP_STATUS_COMPLETE (1u << 1)
#define ET_CORDIC_WRAP_STATUS_PM_ARG2_ERROR (1u << 2)
#define ET_CORDIC_WRAP_STATUS_ALL                                                                  \
    (ET_CORDIC_WRAP_STATUS_ARG_OVERFLOW | ET_CORDIC_WRAP_STATUS_COMPLETE |                         \
     ET_CORDIC_WRAP_STATUS_PM_ARG2_ERROR)

#define ET_CORDIC_WRAP_CONVERSION_UNDERFLOW (1u << 0)
#define ET_CORDIC_WRAP_CONVERSION_OVERFLOW (1u << 1)
#define ET_CORDIC_WRAP_CONVERSION_ALL                                                              \
    (ET_CORDIC_WRAP_CONVERSION_UNDERFLOW | ET_CORDIC_WRAP_CONVERSION_OVERFLOW)

#define ET_CORDIC_WRAP_CAP_FIXED (1u << 0)
#define ET_CORDIC_WRAP_CAP_FLOAT32 (1u << 1)
#define ET_CORDIC_WRAP_CAP_WIDTH_16 (1u << 2)
#define ET_CORDIC_WRAP_CAP_WIDTH_32 (1u << 3)
#define ET_CORDIC_WRAP_CAP_NORMALIZED_RANGE (1u << 4)
#define ET_CORDIC_WRAP_CAP_DIRECT_ANGLE_RANGE (1u << 5)
#define ET_CORDIC_WRAP_CAP_POLLING (1u << 6)
#define ET_CORDIC_WRAP_CAP_INTERRUPT (1u << 7)
#define ET_CORDIC_WRAP_CAP_ZERO_OVERHEAD (1u << 8)
#define ET_CORDIC_WRAP_CAP_DMA (1u << 9)
#define ET_CORDIC_WRAP_CAP_STATUS (1u << 10)
#define ET_CORDIC_WRAP_CAP_INTERRUPTS (1u << 11)

typedef struct
{
    uint32_t raw;
    uint32_t status;
} et_cordic_wrap_irq_snapshot_t;

typedef struct
{
    uint32_t features;
    uint16_t function_mask;
    uint8_t maximum_scale;
    uint8_t maximum_precision_cycles;
    uint8_t irq_sources;
    uint8_t reserved[3];
} et_cordic_wrap_capabilities_t;

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    et_cordic_id_t cordic_id;
    uint8_t numeric_mode;
    uint8_t argument_width;
    uint8_t result_width;
    uint8_t input_range;
    uint8_t scale;
    uint8_t precision_cycles;
    uint8_t sincos_result_count;
    uint8_t phase_modulus_result_count;
    uint8_t hsincos_result_count;
    uint8_t work_mode;
    uint8_t reserved8[2];
    uint32_t reserved[ET_CORDIC_WRAP_CONFIG_RESERVED_WORDS];
} et_cordic_wrap_config_t;

#define ET_CORDIC_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_cordic_wrap_config_t, reserved))

et_wrap_status_t et_cordic_wrap_capabilities_get(et_cordic_id_t cordic_id,
                                                 et_cordic_wrap_capabilities_t *capabilities);
et_wrap_status_t et_cordic_wrap_configure(et_cordic_id_t cordic_id,
                                          const et_cordic_wrap_config_t *config);
et_wrap_status_t et_cordic_wrap_argument_submit(et_cordic_id_t cordic_id, uint8_t function,
                                                uint32_t raw_value);
et_wrap_status_t et_cordic_wrap_result_get(et_cordic_id_t cordic_id, uint32_t *primary,
                                           uint32_t *secondary);
et_wrap_status_t et_cordic_wrap_status_get(et_cordic_id_t cordic_id, uint32_t *status);
et_wrap_status_t et_cordic_wrap_status_clear(et_cordic_id_t cordic_id, uint32_t status);
et_wrap_status_t et_cordic_wrap_argument_count_get(et_cordic_id_t cordic_id, uint32_t *count);
et_wrap_status_t et_cordic_wrap_conversion_status_get(et_cordic_id_t cordic_id, uint32_t *status);
et_wrap_status_t et_cordic_wrap_conversion_status_clear(et_cordic_id_t cordic_id, uint32_t status);
et_wrap_status_t et_cordic_wrap_get_irq_route(et_cordic_id_t cordic_id, et_irq_route_t *route);
et_wrap_status_t et_cordic_wrap_irq_enable(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_disable(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_mask(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_unmask(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_force(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_clear(et_cordic_id_t cordic_id, uint32_t sources);
et_wrap_status_t et_cordic_wrap_irq_snapshot_get(et_cordic_id_t cordic_id,
                                                 et_cordic_wrap_irq_snapshot_t *snapshot);
et_wrap_status_t et_cordic_wrap_zero_overhead_execute(et_cordic_id_t cordic_id, uint8_t function,
                                                      const uint32_t *arguments,
                                                      uint8_t argument_count, uint32_t *primary,
                                                      uint32_t *secondary);
et_wrap_status_t et_cordic_wrap_execute_timed(et_cordic_id_t cordic_id, uint8_t function,
                                              const uint32_t *arguments, uint8_t argument_count,
                                              uint32_t timeout, uint32_t *primary,
                                              uint32_t *secondary, uint32_t *elapsed_cycles);

#endif
