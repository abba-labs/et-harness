#ifndef ET_CRC_WRAP_H
#define ET_CRC_WRAP_H

/**
 * @file et_crc_wrap.h
 * @brief Stable, chip-independent CRC operations used by CRC Service.
 *
 * The public interface contains no concrete-chip SDK types. The implementation maps
 * logical IDs, modes and IRQ sources to the selected chip CRC Driver.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

/** Version of et_crc_wrap_config_t fields understood by this Wrap. */
#define ET_CRC_WRAP_API_VERSION 1u
/** Reserved words kept for compatible configuration growth. */
#define ET_CRC_WRAP_CONFIG_RESERVED_WORDS 4u
/** Maximum byte length accepted by one bounded synchronous calculation. */
#define ET_CRC_WRAP_MAX_CALCULATE_BYTES 4096u
/** Maximum word count accepted by the validation-only burst extension. */
#define ET_CRC_WRAP_MAX_BURST_ITEMS 9u

/** Stable logical CRC instance identifier; it is not a register address. */
typedef uint16_t et_crc_id_t;

/** Logical CRC polynomial width. Values intentionally equal the bit width. */
typedef enum
{
    ET_CRC_WRAP_MODE_CRC8 = 8u,
    ET_CRC_WRAP_MODE_CRC16 = 16u,
    ET_CRC_WRAP_MODE_CRC32 = 32u
} et_crc_wrap_mode_t;

/** Final XOR selection supported by the common CRC configuration. */
typedef enum
{
    ET_CRC_WRAP_XOR_ZERO = 0u,
    ET_CRC_WRAP_XOR_ONES = 1u
} et_crc_wrap_xor_t;

/** Access width used by the validation-only typed input operation. */
typedef enum
{
    ET_CRC_WRAP_ACCESS_8 = 8u,
    ET_CRC_WRAP_ACCESS_16 = 16u,
    ET_CRC_WRAP_ACCESS_32 = 32u
} et_crc_wrap_access_width_t;

/** Stable CRC IRQ source bits exposed to Service and PC. */
#define ET_CRC_WRAP_IRQ_BUS_ERROR (1u << 0)
#define ET_CRC_WRAP_IRQ_LENGTH_ERROR (1u << 1)
#define ET_CRC_WRAP_IRQ_CHECK_ERROR (1u << 2)
#define ET_CRC_WRAP_IRQ_ALL                                                                        \
    (ET_CRC_WRAP_IRQ_BUS_ERROR | ET_CRC_WRAP_IRQ_LENGTH_ERROR | ET_CRC_WRAP_IRQ_CHECK_ERROR)

/** Hardware IRQ state normalized to stable logical source bits. */
typedef struct
{
    uint32_t raw;    /**< Raw source state before interrupt masking. */
    uint32_t status; /**< Effective source state after interrupt masking. */
} et_crc_wrap_irq_snapshot_t;

/**
 * Versioned CRC configuration shared by all supported chip families.
 *
 * Boolean members accept only 0 or 1. Polynomial and initial_value must fit
 * the selected mode width. Reserved fields must be zero-initialized by callers.
 */
typedef struct
{
    uint16_t struct_size;       /**< Total caller-visible structure size. */
    uint16_t api_version;       /**< Must equal ET_CRC_WRAP_API_VERSION. */
    et_crc_id_t crc_id;         /**< Target logical CRC instance. */
    uint8_t mode;               /**< One et_crc_wrap_mode_t value. */
    uint8_t ref_in;             /**< Reflect each input item when set. */
    uint8_t ref_out;            /**< Reflect the final result when set. */
    uint8_t xor_out;            /**< One et_crc_wrap_xor_t value. */
    uint8_t auto_length_reload; /**< Reload LENGTH automatically when set. */
    uint8_t byte_swap;          /**< Enable input byte swapping when supported. */
    uint8_t result_check;       /**< Enable comparison against CHECK. */
    uint8_t fifo_threshold;     /**< Hardware FIFO threshold in input items. */
    uint8_t reserved8;
    uint32_t polynomial;    /**< Polynomial limited by selected mode width. */
    uint32_t initial_value; /**< Initial seed limited by selected mode width. */
    uint32_t reserved[ET_CRC_WRAP_CONFIG_RESERVED_WORDS];
} et_crc_wrap_config_t;

#define ET_CRC_WRAP_CONFIG_V1_MIN_SIZE ((uint16_t)offsetof(et_crc_wrap_config_t, reserved))

/** Enable the selected CRC module. */
et_wrap_status_t et_crc_wrap_enable(et_crc_id_t crc_id);
/** Return the selected instance's maximum supported FIFO threshold. */
et_wrap_status_t et_crc_wrap_get_fifo_threshold_max(et_crc_id_t crc_id, uint8_t *maximum_threshold);
/** Disable the selected CRC module. Active configuration becomes unusable. */
et_wrap_status_t et_crc_wrap_disable(et_crc_id_t crc_id);

/**
 * @brief Validate and apply one complete CRC configuration.
 * @param crc_id Stable logical CRC instance identifier.
 * @param config Versioned common configuration; not retained by the Wrap.
 * @return ET_WRAP_STATUS_OK on success, otherwise a normalized argument or I/O error.
 */
et_wrap_status_t et_crc_wrap_configure(et_crc_id_t crc_id, const et_crc_wrap_config_t *config);

/**
 * @brief Calculate CRC over one bounded memory range using the active mode.
 * @param crc_id Stable logical CRC instance identifier.
 * @param mode Active CRC width; determines source alignment and result width.
 * @param source_address Start address of readable input bytes.
 * @param length_bytes Input length in bytes, from 1 through the configured maximum.
 * @param timeout_budget Bounded Driver polling budget; must be nonzero.
 * @param result Receives the zero-extended CRC result.
 * @return Normalized Wrap status. The input buffer is never modified.
 */
et_wrap_status_t et_crc_wrap_calculate(et_crc_id_t crc_id, uint8_t mode, uintptr_t source_address,
                                       uint32_t length_bytes, uint32_t timeout_budget,
                                       uint32_t *result);

/** Read the current hardware result without starting a new calculation. */
et_wrap_status_t et_crc_wrap_result_get(et_crc_id_t crc_id, uint32_t *result);

/**
 * @brief Program the expected data length using a byte-oriented public value.
 * @param length_bytes Input length in bytes; converted to hardware input items.
 */
et_wrap_status_t et_crc_wrap_data_length_set(et_crc_id_t crc_id, uint8_t mode,
                                             uint32_t length_bytes);

/** Read the remaining hardware input-item count, not a byte count. */
et_wrap_status_t et_crc_wrap_data_length_get(et_crc_id_t crc_id, uint32_t *remaining_input_count);

/** Program the comparison value after checking it fits the active CRC width. */
et_wrap_status_t et_crc_wrap_check_value_set(et_crc_id_t crc_id, uint8_t mode, uint32_t value);

/** Read the FIFO overflow fact as 0 or 1 without clearing it. */
et_wrap_status_t et_crc_wrap_fifo_status_get(et_crc_id_t crc_id, uint8_t *overflow);

/** Resolve the logical CRC instance to its chip-specific physical IRQ route. */
et_wrap_status_t et_crc_wrap_get_irq_route(et_crc_id_t crc_id, et_irq_route_t *route);

/** Enable selected logical CRC interrupt sources. */
et_wrap_status_t et_crc_wrap_irq_enable(et_crc_id_t crc_id, uint32_t source_bits);
/** Disable selected logical CRC interrupt sources. */
et_wrap_status_t et_crc_wrap_irq_disable(et_crc_id_t crc_id, uint32_t source_bits);
/** Mask selected sources while preserving their enable state. */
et_wrap_status_t et_crc_wrap_irq_mask(et_crc_id_t crc_id, uint32_t source_bits);
/** Remove the mask from selected enabled sources. */
et_wrap_status_t et_crc_wrap_irq_unmask(et_crc_id_t crc_id, uint32_t source_bits);
/** Force selected sources for deterministic IRQ-path validation. */
et_wrap_status_t et_crc_wrap_irq_force(et_crc_id_t crc_id, uint32_t source_bits);
/** Clear selected raw/pending CRC interrupt sources. */
et_wrap_status_t et_crc_wrap_irq_clear(et_crc_id_t crc_id, uint32_t source_bits);
/** Read raw and effective IRQ states in one normalized snapshot. */
et_wrap_status_t et_crc_wrap_irq_snapshot_get(et_crc_id_t crc_id,
                                              et_crc_wrap_irq_snapshot_t *snapshot);

/**
 * @brief Write exactly one CRC input item using an explicit access width.
 * @note Available only when ET_ENABLE_TEST_DRIVER_EXTENSIONS is enabled.
 */
et_wrap_status_t et_crc_wrap_test_input_write(et_crc_id_t crc_id, uint8_t access_width,
                                              uint32_t value);

/**
 * @brief Execute a bounded target-local 32-bit input burst.
 * @note Available only when ET_ENABLE_TEST_DRIVER_EXTENSIONS is enabled.
 */
et_wrap_status_t et_crc_wrap_test_input_burst_32(et_crc_id_t crc_id, const uint32_t *values,
                                                 uint32_t count, uint32_t checkpoint_count,
                                                 uint32_t *checkpoint_result,
                                                 uint32_t *final_result, uint32_t *overflow);

/**
 * @brief Calculate CRC32 and return target-local DWT cycle evidence.
 * @param length_bytes Number of measured input bytes.
 * @param elapsed_cycles Receives unsigned DWT cycles from first input write
 *        through result read. The Wrap does not interpret this value.
 * @note Available only when ET_ENABLE_TEST_DRIVER_EXTENSIONS is enabled.
 */
et_wrap_status_t et_crc_wrap_test_calculate_timed(et_crc_id_t crc_id, uintptr_t source_address,
                                                  uint32_t length_bytes, uint32_t timeout_budget,
                                                  uint32_t *result, uint32_t *elapsed_cycles);

#endif
