#ifndef ET_AES_WRAP_H
#define ET_AES_WRAP_H

/**
 * @file et_aes_wrap.h
 * @brief Stable AES operations for the AES Service.
 *
 * The public contract uses canonical bytes and logical enums. Chip SDK types,
 * register addresses and physical IRQ numbers remain private to chip configuration.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_AES_WRAP_API_VERSION 1u
#define ET_AES_WRAP_BLOCK_SIZE 16u
#define ET_AES_WRAP_WORD_SIZE_BYTES ((uint32_t)sizeof(uint32_t))
#define ET_AES_WRAP_WORDS_PER_BLOCK (ET_AES_WRAP_BLOCK_SIZE / ET_AES_WRAP_WORD_SIZE_BYTES)
#define ET_AES_WRAP_KEY_128_BYTES 16u
#define ET_AES_WRAP_KEY_256_BYTES 32u
#define ET_AES_WRAP_KEY_MAX_WORDS (ET_AES_WRAP_KEY_256_BYTES / ET_AES_WRAP_WORD_SIZE_BYTES)
#define ET_AES_WRAP_TIMEOUT_BUDGET 1000000u
#define ET_AES_WRAP_MAX_PROCESS_BYTES 4096u
#define ET_AES_WRAP_MAX_OUTPUT_BYTES (ET_AES_WRAP_MAX_PROCESS_BYTES + ET_AES_WRAP_BLOCK_SIZE)
/** Canonical Boolean capability value for an implemented IRQ transfer path. */
#define ET_AES_WRAP_IRQ_TRANSFER_SUPPORTED 1u

/* Stable runtime Feature bits shared by Wrap capability and the AES wire contract. */
#define ET_AES_WRAP_CAP_MODULE_ENABLE (1u << 0)
#define ET_AES_WRAP_CAP_ENCRYPTION (1u << 1)
#define ET_AES_WRAP_CAP_DECRYPTION (1u << 2)
#define ET_AES_WRAP_CAP_KEY_128 (1u << 3)
#define ET_AES_WRAP_CAP_KEY_256 (1u << 4)
#define ET_AES_WRAP_CAP_ECB (1u << 5)
#define ET_AES_WRAP_CAP_CBC (1u << 6)
#define ET_AES_WRAP_CAP_CTR (1u << 7)
#define ET_AES_WRAP_CAP_PADDING (1u << 8)
#define ET_AES_WRAP_CAP_IV (1u << 9)
#define ET_AES_WRAP_CAP_CTR_COUNTER (1u << 10)
#define ET_AES_WRAP_CAP_STATUS (1u << 11)
#define ET_AES_WRAP_CAP_INTERRUPTS (1u << 12)
#define ET_AES_WRAP_CAP_DMA (1u << 13)
#define ET_AES_WRAP_CAP_CPU_REGISTER_PATH (1u << 14)
#define ET_AES_WRAP_CAP_DMA_FIFO_PATH (1u << 15)
#define ET_AES_WRAP_CAP_IRQ_TRANSFER (1u << 16)
#define ET_AES_WRAP_CAP_TIMED_PROCESS (1u << 17)
#define ET_AES_WRAP_CAP_TEST_EXTENSIONS (1u << 18)

typedef uint8_t et_aes_id_t;
typedef enum
{
    ET_AES_WRAP_DIRECTION_ENCRYPT = 0u,
    ET_AES_WRAP_DIRECTION_DECRYPT = 1u
} et_aes_direction_t;
typedef enum
{
    ET_AES_WRAP_KEY_128 = 0u,
    ET_AES_WRAP_KEY_256 = 1u
} et_aes_key_size_t;
typedef enum
{
    ET_AES_WRAP_MODE_ECB = 0u,
    ET_AES_WRAP_MODE_CBC = 1u,
    ET_AES_WRAP_MODE_CTR = 2u
} et_aes_mode_t;
typedef enum
{
    ET_AES_WRAP_PADDING_NONE = 0u,
    ET_AES_WRAP_PADDING_ZERO = 1u,
    ET_AES_WRAP_PADDING_PKCS7 = 2u
} et_aes_padding_t;
typedef enum
{
    ET_AES_WRAP_ENDIAN_LITTLE = 0u,
    ET_AES_WRAP_ENDIAN_BIG = 1u
} et_aes_endian_t;
typedef enum
{
    ET_AES_WRAP_DMA_FIFO = 0u,
    ET_AES_WRAP_DMA_REGISTER = 1u
} et_aes_dma_mode_t;

#define ET_AES_WRAP_IRQ_OUTPUT_CONFLICT (1u << 0)
#define ET_AES_WRAP_IRQ_KEY_MISSING (1u << 1)
#define ET_AES_WRAP_IRQ_IV_MISSING (1u << 2)
#define ET_AES_WRAP_IRQ_COMPLETE (1u << 3)
#define ET_AES_WRAP_IRQ_INCOMPLETE_DISABLE (1u << 4)
#define ET_AES_WRAP_IRQ_DATA_IN_REQ (1u << 5)
#define ET_AES_WRAP_IRQ_DATA_OUT_REQ (1u << 6)
#define ET_AES_WRAP_IRQ_ALL 0x7fu
#define ET_AES_WRAP_DMA_INPUT (1u << 0)
#define ET_AES_WRAP_DMA_OUTPUT (1u << 1)
#define ET_AES_WRAP_DMA_ALL 0x03u
#define ET_AES_WRAP_STATUS_FINISH (1u << 0)
#define ET_AES_WRAP_STATUS_DATA_IN_REQ (1u << 1)
#define ET_AES_WRAP_STATUS_DATA_OUT_REQ (1u << 2)
#define ET_AES_WRAP_STATUS_ALL                                                                     \
    (ET_AES_WRAP_STATUS_FINISH | ET_AES_WRAP_STATUS_DATA_IN_REQ | ET_AES_WRAP_STATUS_DATA_OUT_REQ)
/* Session-local fault facts; these never expose chip register addresses. */
#define ET_AES_WRAP_FAULT_LENGTH (1u << 30)
#define ET_AES_WRAP_FAULT_MAINTENANCE (1u << 31)

typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint8_t direction;
    uint8_t key_size;
    uint8_t mode;
    uint8_t padding;
    uint8_t endian;
    uint8_t dma_transfer_mode;
    uint8_t reserved[2];
    uint32_t ctr_counter;
} et_aes_wrap_config_t;

/** Runtime capabilities implemented by one logical AES instance. */
typedef struct
{
    uint16_t struct_size;
    uint16_t api_version;
    uint32_t feature_flags;
    uint32_t block_size_bytes;
    uint32_t hardware_data_length_bits;
    uint32_t max_process_bytes;
    uint32_t max_process_output_bytes;
    uint8_t key_size_mask;
    uint8_t mode_mask;
    uint8_t padding_mask;
    uint8_t endian_mask;
    uint8_t dma_mode_mask;
    uint8_t irq_event_mask;
    uint8_t irq_transfer_supported;
    uint8_t timed_process_supported;
} et_aes_wrap_capabilities_t;

typedef struct
{
    uint8_t busy;
    uint8_t data_in_request;
    uint8_t data_out_request;
    uint8_t finish;
    uint32_t irq_status;
} et_aes_wrap_status_snapshot_t;

typedef struct
{
    uint32_t raw;
    uint32_t status;
} et_aes_wrap_irq_snapshot_t;

et_wrap_status_t et_aes_wrap_get_capabilities(et_aes_id_t aes_id,
                                              et_aes_wrap_capabilities_t *capabilities);
et_wrap_status_t et_aes_wrap_enable(et_aes_id_t aes_id);
et_wrap_status_t et_aes_wrap_disable(et_aes_id_t aes_id);
et_wrap_status_t et_aes_wrap_configure(et_aes_id_t aes_id, const et_aes_wrap_config_t *config);
et_wrap_status_t et_aes_wrap_set_key(et_aes_id_t aes_id, const uint8_t *key, uint8_t key_size);
et_wrap_status_t et_aes_wrap_set_iv(et_aes_id_t aes_id, const uint8_t iv[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_get_iv(et_aes_id_t aes_id, uint8_t iv[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_set_data_length(et_aes_id_t aes_id, uint64_t length_bytes);
et_wrap_status_t et_aes_wrap_get_data_length(et_aes_id_t aes_id, uint64_t *length_bytes);
et_wrap_status_t et_aes_wrap_process(et_aes_id_t aes_id, const uint8_t *source,
                                     uint8_t *destination, uint32_t length_bytes,
                                     uint32_t destination_capacity, uint32_t *produced_bytes);
et_wrap_status_t et_aes_wrap_block_write(et_aes_id_t aes_id,
                                         const uint8_t block[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_block_write_wait(et_aes_id_t aes_id,
                                              const uint8_t block[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_block_write_direct(et_aes_id_t aes_id,
                                                const uint8_t block[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_block_write_pair_direct(et_aes_id_t aes_id,
                                                     const uint8_t first[ET_AES_WRAP_BLOCK_SIZE],
                                                     const uint8_t second[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t
et_aes_wrap_block_write_disable_direct(et_aes_id_t aes_id,
                                       const uint8_t block[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_block_read(et_aes_id_t aes_id, uint8_t block[ET_AES_WRAP_BLOCK_SIZE]);
et_wrap_status_t et_aes_wrap_get_status(et_aes_id_t aes_id,
                                        et_aes_wrap_status_snapshot_t *snapshot);
et_wrap_status_t et_aes_wrap_clear_status(et_aes_id_t aes_id, uint8_t status_bits);
et_wrap_status_t et_aes_wrap_irq_enable(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_disable(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_mask(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_unmask(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_force(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_clear(et_aes_id_t aes_id, uint32_t source_bits);
et_wrap_status_t et_aes_wrap_irq_snapshot_get(et_aes_id_t aes_id,
                                              et_aes_wrap_irq_snapshot_t *snapshot);
et_wrap_status_t et_aes_wrap_get_irq_route(et_aes_id_t aes_id, et_irq_route_t *route);
et_wrap_status_t et_aes_wrap_dma_request_set(et_aes_id_t aes_id, uint32_t request_bits);
et_wrap_status_t et_aes_wrap_process_timed(et_aes_id_t aes_id, const uint8_t *source,
                                           uint8_t *destination, uint32_t length_bytes,
                                           uint32_t destination_capacity, uint32_t *produced_bytes,
                                           uint32_t *elapsed_cycles);

#endif
