/**
 * @file et_aes_wrap.c
 * @brief Implement the stable AES Wrap contract through the selected AES Driver.
 *
 * This file intentionally contains no register access. All hardware access
 * is performed through et6x_aes.h, while byte packing stays at this boundary.
 */
#include "et_aes_wrap.h"

#include <limits.h>
#include <string.h>

#include "et6x_aes.h"
#include "et_chip_wrap_config.h"

/* Canonical four-byte word positions and shifts used only by the AES boundary codec. */
enum
{
    ET_AES_WRAP_BYTE_INDEX_0 = 0u,
    ET_AES_WRAP_BYTE_INDEX_1 = 1u,
    ET_AES_WRAP_BYTE_INDEX_2 = 2u,
    ET_AES_WRAP_BYTE_INDEX_3 = 3u,
    ET_AES_WRAP_BYTE_SHIFT_1 = 8u,
    ET_AES_WRAP_BYTE_SHIFT_2 = 16u,
    ET_AES_WRAP_BYTE_SHIFT_3 = 24u
};

typedef struct
{
    et_aes_id_t aes_id;
    IRQn_Type irq;
    uint32_t feature_flags;
    uint32_t hardware_data_length_bits;
    uint32_t max_process_bytes;
    uint32_t max_output_bytes;
    uint8_t key_size_mask;
    uint8_t mode_mask;
    uint8_t padding_mask;
    uint8_t endian_mask;
    uint8_t dma_mode_mask;
    uint8_t irq_event_mask;
    uint8_t irq_transfer_supported;
    uint8_t driver_dma_fifo_value;
    uint8_t driver_dma_register_value;
} et_aes_wrap_mapping_t;

typedef struct
{
    et_aes_wrap_config_t config;
    uint8_t enabled;
    uint8_t configured;
} et_aes_wrap_state_t;

static const et_aes_wrap_mapping_t aes_mappings[] = ET_CHIP_AES_MAP_TABLE;
static et_aes_wrap_state_t aes_states[sizeof(aes_mappings) / sizeof(aes_mappings[0])];

/**
 * @brief Resolve one stable logical AES instance to chip-private mapping and bounded local state.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] mapping Optional chip mapping pointer for the selected instance.
 * @param[out] state Optional bounded Wrap-state pointer paired with the selected instance.
 *
 * @note This helper reads static Chip Config/Wrap state only and does not access AES hardware.
 *
 * @return ET_WRAP_STATUS_OK when aes_id is mapped.
 * @return ET_WRAP_STATUS_NOT_SUPPORTED when the logical instance is absent on this chip.
 */
static et_wrap_status_t map_aes(et_aes_id_t aes_id, const et_aes_wrap_mapping_t **mapping,
                                et_aes_wrap_state_t **state)
{
    size_t index;

    for (index = 0u; index < (sizeof(aes_mappings) / sizeof(aes_mappings[0])); ++index)
    {
        if (aes_mappings[index].aes_id == aes_id)
        {
            if (mapping != NULL)
            {
                *mapping = &aes_mappings[index];
            }

            if (state != NULL)
            {
                *state = &aes_states[index];
            }

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Validate one complete chip-neutral AES configuration against the selected chip mapping.
 *
 * @param[in] config Versioned AES Wrap configuration supplied by the Service.
 * @param[in] mapping Selected-chip static capabilities and Driver translation facts.
 *
 * @note Validation rejects unsupported enum values, reserved bytes and invalid CTR padding before any
 *       Driver configuration is built or hardware is touched.
 *
 * @return Nonzero when the complete configuration is valid, otherwise zero.
 */
static uint8_t config_is_valid(const et_aes_wrap_config_t *config,
                               const et_aes_wrap_mapping_t *mapping)
{
    if ((config == NULL) || (mapping == NULL) ||
        (config->struct_size != (uint16_t)sizeof(*config)) ||
        (config->api_version != ET_AES_WRAP_API_VERSION) ||
        (config->direction > ET_AES_WRAP_DIRECTION_DECRYPT) ||
        (config->key_size > ET_AES_WRAP_KEY_256) || (config->mode > ET_AES_WRAP_MODE_CTR) ||
        (config->padding > ET_AES_WRAP_PADDING_PKCS7) ||
        (config->endian > ET_AES_WRAP_ENDIAN_BIG) ||
        (config->dma_transfer_mode > ET_AES_WRAP_DMA_REGISTER) || (config->reserved[0] != 0u) ||
        (config->reserved[1] != 0u))
    {
        return 0u;
    }

    if (((mapping->key_size_mask & (1u << config->key_size)) == 0u) ||
        ((mapping->mode_mask & (1u << config->mode)) == 0u) ||
        ((mapping->padding_mask & (1u << config->padding)) == 0u) ||
        ((mapping->endian_mask & (1u << config->endian)) == 0u) ||
        ((mapping->dma_mode_mask & (1u << config->dma_transfer_mode)) == 0u))
    {
        return 0u;
    }

    /* The stable Wrap contract permits padding only for ECB and CBC. */
    if ((config->mode == ET_AES_WRAP_MODE_CTR) && (config->padding != ET_AES_WRAP_PADDING_NONE))
    {
        return 0u;
    }

    return 1u;
}

/**
 * @brief Decode one canonical little-endian 32-bit AES boundary word.
 *
 * @param[in] data Four canonical boundary bytes.
 *
 * @note This helper only performs byte packing and does not access AES hardware.
 *
 * @return Decoded 32-bit word.
 */
static uint32_t load_le32(const uint8_t *data)
{
    return (uint32_t)data[ET_AES_WRAP_BYTE_INDEX_0] |
           ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_1] << ET_AES_WRAP_BYTE_SHIFT_1) |
           ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_2] << ET_AES_WRAP_BYTE_SHIFT_2) |
           ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_3] << ET_AES_WRAP_BYTE_SHIFT_3);
}

/**
 * @brief Encode one 32-bit AES word into canonical little-endian boundary bytes.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Word to encode.
 *
 * @note This helper only performs byte packing and does not access AES hardware.
 */
static void store_le32(uint8_t *data, uint32_t value)
{
    data[ET_AES_WRAP_BYTE_INDEX_0] = (uint8_t)value;
    data[ET_AES_WRAP_BYTE_INDEX_1] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_1);
    data[ET_AES_WRAP_BYTE_INDEX_2] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_2);
    data[ET_AES_WRAP_BYTE_INDEX_3] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_3);
}

/**
 * @brief Decode one canonical big-endian 32-bit AES boundary word.
 *
 * @param[in] data Four canonical boundary bytes.
 *
 * @note This helper only performs byte packing and does not access AES hardware.
 *
 * @return Decoded 32-bit word.
 */
static uint32_t load_be32(const uint8_t *data)
{
    return ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_0] << ET_AES_WRAP_BYTE_SHIFT_3) |
           ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_1] << ET_AES_WRAP_BYTE_SHIFT_2) |
           ((uint32_t)data[ET_AES_WRAP_BYTE_INDEX_2] << ET_AES_WRAP_BYTE_SHIFT_1) |
           (uint32_t)data[ET_AES_WRAP_BYTE_INDEX_3];
}

/**
 * @brief Encode one 32-bit AES word into canonical big-endian boundary bytes.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Word to encode.
 *
 * @note This helper only performs byte packing and does not access AES hardware.
 */
static void store_be32(uint8_t *data, uint32_t value)
{
    data[ET_AES_WRAP_BYTE_INDEX_0] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_3);
    data[ET_AES_WRAP_BYTE_INDEX_1] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_2);
    data[ET_AES_WRAP_BYTE_INDEX_2] = (uint8_t)(value >> ET_AES_WRAP_BYTE_SHIFT_1);
    data[ET_AES_WRAP_BYTE_INDEX_3] = (uint8_t)value;
}

/**
 * @brief Decode one canonical AES word using the active public endian selection.
 *
 * @param[in] data Four canonical boundary bytes.
 * @param[in] endian Stable AES endian selector.
 *
 * @note Endian handling remains at the Wrap boundary so selected Driver values never leak publicly.
 *
 * @return Decoded 32-bit word.
 */
static uint32_t load_word(const uint8_t *data, uint8_t endian)
{
    return (endian == ET_AES_WRAP_ENDIAN_BIG) ? load_be32(data) : load_le32(data);
}

/**
 * @brief Encode one AES word using the active public endian selection.
 *
 * @param[out] data Four-byte destination field.
 * @param[in] value Word to encode.
 * @param[in] endian Stable AES endian selector.
 *
 * @note This helper changes only caller-owned boundary bytes and does not access AES hardware.
 */
static void store_word(uint8_t *data, uint32_t value, uint8_t endian)
{
    if (endian == ET_AES_WRAP_ENDIAN_BIG)
    {
        store_be32(data, value);
    }
    else
    {
        store_le32(data, value);
    }
}

/**
 * @brief Pack one canonical 16-byte AES block into selected-Driver word representation.
 *
 * @param[in] bytes Canonical block bytes.
 * @param[out] words Driver-facing block words.
 * @param[in] endian Active stable AES endian selector.
 *
 * @note Packing is deterministic boundary translation only and performs no Driver call.
 */
static void bytes_to_words(const uint8_t bytes[ET_AES_WRAP_BLOCK_SIZE],
                           uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK], uint8_t endian)
{
    uint32_t index;

    for (index = 0u; index < ET_AES_WRAP_WORDS_PER_BLOCK; ++index)
    {
        words[index] = load_word(&bytes[index * ET_AES_WRAP_WORD_SIZE_BYTES], endian);
    }
}

/**
 * @brief Align a partial final big-endian input word to the Driver's least-significant-byte convention.
 *
 * @param[in,out] words Driver-facing block words to adjust.
 * @param[in] valid_bytes Number of valid source bytes in the partial block.
 * @param[in] endian Active stable AES endian selector.
 *
 * @note Adjustment is required only for partial big-endian final words and changes caller-owned staging
 *       data only; no AES hardware is accessed.
 */
static void align_partial_input_word(uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK],
                                     uint32_t valid_bytes, uint8_t endian)
{
    uint32_t remainder = valid_bytes % ET_AES_WRAP_WORD_SIZE_BYTES;
    uint32_t word_index;

    if ((remainder == 0u) || (endian != ET_AES_WRAP_ENDIAN_BIG))
    {
        return;
    }

    word_index = valid_bytes / ET_AES_WRAP_WORD_SIZE_BYTES;
    words[word_index] >>= (ET_AES_WRAP_WORD_SIZE_BYTES - remainder) * CHAR_BIT;
}

/**
 * @brief Unpack one selected-Driver AES result block into canonical boundary bytes.
 *
 * @param[in] words Driver-facing result words.
 * @param[out] bytes Canonical block-byte destination.
 * @param[in] endian Active stable AES endian selector.
 *
 * @note Unpacking is deterministic boundary translation only and performs no Driver call.
 */
static void words_to_bytes(const uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK],
                           uint8_t bytes[ET_AES_WRAP_BLOCK_SIZE], uint8_t endian)
{
    uint32_t index;

    for (index = 0u; index < ET_AES_WRAP_WORDS_PER_BLOCK; ++index)
    {
        store_word(&bytes[index * ET_AES_WRAP_WORD_SIZE_BYTES], words[index], endian);
    }
}

/**
 * @brief Translate and apply one already-validated stable AES configuration to the selected Driver.
 *
 * @param[in] config Stable AES configuration owned by Wrap state.
 * @param[in] mapping Selected-chip Driver translation facts.
 *
 * @note This helper directly changes AES configuration hardware. Validation must be completed by the
 *       caller first; Chip Config owns FIFO/register-mode translation into Driver field semantics.
 */
static void apply_driver_config(const et_aes_wrap_config_t *config,
                                const et_aes_wrap_mapping_t *mapping)
{
    AES_ConfigParams driver_config;

    driver_config.keySize = (AES_KeySize)config->key_size;
    driver_config.direction = (AES_Direction)config->direction;
    driver_config.paddingMode = (AES_PaddingMode)config->padding;
    driver_config.opMode = (AES_OpMode)config->mode;
    driver_config.ctrCount = config->ctr_counter;
    /* Chip Config owns translation into the selected Driver's field semantics. */
    driver_config.FIFOModeEn = (config->dma_transfer_mode == ET_AES_WRAP_DMA_FIFO)
                                   ? (ControlStatus)mapping->driver_dma_fifo_value
                                   : (ControlStatus)mapping->driver_dma_register_value;
    driver_config.endianSel = (AES_EndianSel)config->endian;
    AES_configureModule(&driver_config);
}

/**
 * @brief Normalize one selected AES Driver status into the stable Wrap status namespace.
 *
 * @param[in] status AES Driver status returned by the selected chip SDK.
 *
 * @note This helper performs status translation only and does not access AES hardware.
 *
 * @return Stable Wrap status corresponding to the Driver result.
 */
static et_wrap_status_t driver_status(DRV_Status status)
{
    if (status == DRV_OK)
    {
        return ET_WRAP_STATUS_OK;
    }

    if (status == DRV_PARAM_ERR)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (status == DRV_TIMEOUT)
    {
        return ET_WRAP_STATUS_TIMEOUT;
    }

    if (status == DRV_BUSY)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    return ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Return stable runtime AES capabilities from selected-chip mapping facts.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] capabilities Versioned capability structure populated for the caller.
 *
 * @note Capability values come from Chip Config/Wrap compile-time facts rather than Service guesses.
 *       Test-extension feature bits are exposed only when those Driver extensions are compiled.
 *
 * @return ET_WRAP_STATUS_OK when capabilities are returned.
 * @return Stable mapping/argument error when aes_id or capabilities is invalid.
 */
et_wrap_status_t et_aes_wrap_get_capabilities(et_aes_id_t aes_id,
                                              et_aes_wrap_capabilities_t *capabilities)
{
    const et_aes_wrap_mapping_t *mapping;
    et_wrap_status_t status;

    if (capabilities == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_aes(aes_id, &mapping, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    (void)memset(capabilities, 0, sizeof(*capabilities));
    capabilities->struct_size = (uint16_t)sizeof(*capabilities);
    capabilities->api_version = ET_AES_WRAP_API_VERSION;
    capabilities->feature_flags = mapping->feature_flags;
    capabilities->block_size_bytes = ET_AES_WRAP_BLOCK_SIZE;
    capabilities->hardware_data_length_bits = mapping->hardware_data_length_bits;
    capabilities->max_process_bytes = mapping->max_process_bytes;
    capabilities->max_process_output_bytes = mapping->max_output_bytes;
    capabilities->key_size_mask = mapping->key_size_mask;
    capabilities->mode_mask = mapping->mode_mask;
    capabilities->padding_mask = mapping->padding_mask;
    capabilities->endian_mask = mapping->endian_mask;
    capabilities->dma_mode_mask = mapping->dma_mode_mask;
    capabilities->irq_event_mask = mapping->irq_event_mask;
    capabilities->irq_transfer_supported = mapping->irq_transfer_supported;
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    capabilities->feature_flags |= ET_AES_WRAP_CAP_TIMED_PROCESS | ET_AES_WRAP_CAP_TEST_EXTENSIONS;
    capabilities->timed_process_supported = 1u;
#endif

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable the selected AES module and reset cached configuration validity.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 *
 * @note This function changes AES module-enable hardware only. Clock/security ownership remains
 *       outside Wrap; local configured state is cleared so callers must configure after enable.
 *
 * @return ET_WRAP_STATUS_OK when AES is enabled, otherwise the stable mapping error.
 */
et_wrap_status_t et_aes_wrap_enable(et_aes_id_t aes_id)
{
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_enableModule();
    state->enabled = 1u;
    state->configured = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable the selected AES module and invalidate all cached Wrap configuration state.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 *
 * @note This function changes AES module-enable hardware and clears bounded local state so stale
 *       configuration cannot be reused after disable.
 *
 * @return ET_WRAP_STATUS_OK when AES is disabled, otherwise the stable mapping error.
 */
et_wrap_status_t et_aes_wrap_disable(et_aes_id_t aes_id)
{
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_disableModule();
    (void)memset(state, 0, sizeof(*state));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate, apply and cache one stable AES configuration atomically at the Wrap boundary.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] config Versioned chip-neutral AES configuration.
 *
 * @note AES must already be enabled. After validation the selected Driver is configured and an exact
 *       copy is cached because Driver data-length ordering may require reapplying it later.
 *
 * @return ET_WRAP_STATUS_OK when configuration is applied and cached.
 * @return Stable mapping/argument error when state or configuration is invalid.
 */
et_wrap_status_t et_aes_wrap_configure(et_aes_id_t aes_id, const et_aes_wrap_config_t *config)
{
    const et_aes_wrap_mapping_t *mapping;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;

    status = map_aes(aes_id, &mapping, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((state->enabled == 0u) || (config_is_valid(config, mapping) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    apply_driver_config(config, mapping);
    state->config = *config;
    state->configured = 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program one canonical 128-bit or 256-bit AES key using configured endian packing.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] key Canonical key bytes supplied by the caller.
 * @param[in] key_size Stable key-size selector that must match active configuration.
 *
 * @note Key bytes are packed into temporary Driver words only after configured-state/key-size
 *       validation. The key is written to AES hardware and is never retained in Wrap state.
 *
 * @return ET_WRAP_STATUS_OK when the key is programmed, otherwise the stable validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_set_key(et_aes_id_t aes_id, const uint8_t *key, uint8_t key_size)
{
    uint32_t words[ET_AES_WRAP_KEY_MAX_WORDS] = {0u};
    uint32_t key_bytes;
    uint32_t index;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;

    status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((key == NULL) || (state->configured == 0u) || (key_size > ET_AES_WRAP_KEY_256) ||
        (key_size != state->config.key_size))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    key_bytes =
        (key_size == ET_AES_WRAP_KEY_256) ? ET_AES_WRAP_KEY_256_BYTES : ET_AES_WRAP_KEY_128_BYTES;

    for (index = 0u; index < (key_bytes / ET_AES_WRAP_WORD_SIZE_BYTES); ++index)
    {
        words[index] = load_word(&key[index * ET_AES_WRAP_WORD_SIZE_BYTES], state->config.endian);
    }

    AES_setKey(words, (AES_KeySize)key_size);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program one canonical 16-byte initialization vector using configured endian packing.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] iv Canonical 16-byte IV.
 *
 * @note The IV is packed into temporary Driver words and written to AES hardware only when a stable
 *       configuration is active; Wrap does not retain a duplicate IV copy.
 *
 * @return ET_WRAP_STATUS_OK when the IV is programmed, otherwise the stable validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_set_iv(et_aes_id_t aes_id, const uint8_t iv[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;

    status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((iv == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(iv, words, state->config.endian);
    AES_setInitializationVector(words);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current AES initialization vector into canonical boundary bytes.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] iv Canonical 16-byte IV destination.
 *
 * @note This function reads AES hardware and unpacks Driver words according to active stable endian
 *       configuration. It does not change the hardware IV.
 *
 * @return ET_WRAP_STATUS_OK when the IV is read, otherwise the stable validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_get_iv(et_aes_id_t aes_id, uint8_t iv[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;

    status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((iv == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    AES_readInitializationVector(words);
    words_to_bytes(words, iv, state->config.endian);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program the selected AES hardware data-length field without truncating public length.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] length_bytes Requested AES data length in bytes.
 *
 * @note Hardware width is taken from Chip Config. The selected Driver requires DATA_LENGTH before
 *       CONFIGURE, so a cached stable configuration is reapplied after programming length.
 *
 * @return ET_WRAP_STATUS_OK when data length is programmed.
 * @return Stable mapping/argument error when AES is disabled or length exceeds hardware width.
 */
et_wrap_status_t et_aes_wrap_set_data_length(et_aes_id_t aes_id, uint64_t length_bytes)
{
    const et_aes_wrap_mapping_t *mapping;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, &mapping, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((state->enabled == 0u) || (mapping->hardware_data_length_bits == 0u) ||
        (mapping->hardware_data_length_bits > (sizeof(uint64_t) * CHAR_BIT)) ||
        ((mapping->hardware_data_length_bits < (sizeof(uint64_t) * CHAR_BIT)) &&
         (length_bytes >= ((uint64_t)1u << mapping->hardware_data_length_bits))))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    AES_setDataLength(length_bytes);

    /*
     * The selected Driver requires DATA_LENGTH before CONFIGURE. Reapply the
     * cached stable configuration here so callers never depend on that private
     * Driver ordering rule.
     */
    if (state->configured != 0u)
    {
        apply_driver_config(&state->config, mapping);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the Driver-reported AES remaining/configured data length.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] length_bytes Current AES hardware data-length value in bytes.
 *
 * @note This is a hardware observation only and does not alter cached configuration or AES state.
 *
 * @return ET_WRAP_STATUS_OK when length is read, otherwise the stable validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_get_data_length(et_aes_id_t aes_id, uint64_t *length_bytes)
{
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((length_bytes == NULL) || (state->enabled == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *length_bytes = AES_getDataLength();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Compute exact AES output capacity required by active direction, mode and padding.
 *
 * @param[in] length_bytes Input length in bytes.
 * @param[in] direction Stable encrypt/decrypt selector.
 * @param[in] mode Stable ECB/CBC/CTR mode selector.
 * @param[in] padding Stable padding selector.
 *
 * @note This is a pure sizing helper. CTR/decrypt preserve input length, while padded block-mode
 *       encryption rounds to complete hardware blocks according to the public contract.
 *
 * @return Required output length in bytes.
 */
static uint32_t output_length_for(uint32_t length_bytes, uint8_t direction, uint8_t mode,
                                  uint8_t padding)
{
    if (mode == ET_AES_WRAP_MODE_CTR)
    {
        return length_bytes;
    }

    if (direction == ET_AES_WRAP_DIRECTION_DECRYPT)
    {
        return length_bytes;
    }

    if (padding == ET_AES_WRAP_PADDING_PKCS7)
    {
        return ((length_bytes / ET_AES_WRAP_BLOCK_SIZE) + 1u) * ET_AES_WRAP_BLOCK_SIZE;
    }

    return ((length_bytes + (ET_AES_WRAP_BLOCK_SIZE - 1u)) / ET_AES_WRAP_BLOCK_SIZE) *
           ET_AES_WRAP_BLOCK_SIZE;
}

/**
 * @brief Process one bounded AES buffer through complete hardware blocks and canonical staging bytes.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source Canonical input bytes.
 * @param[out] destination Caller-owned output buffer.
 * @param[in] length_bytes Number of input bytes.
 * @param[in] destination_capacity Available output bytes.
 * @param[out] produced_bytes Exact output byte count produced by active mode/padding.
 *
 * @note This function performs synchronous AES hardware I/O with a fixed timeout budget. Tail staging
 *       preserves canonical endian behavior; it returns raw execution outcome only and never compares
 *       ciphertext/plaintext with a golden result.
 *
 * @return ET_WRAP_STATUS_OK when the complete buffer is processed.
 * @return Stable mapping/argument/timeout error when state, capacity, block rules or hardware fail.
 */
et_wrap_status_t et_aes_wrap_process(et_aes_id_t aes_id, const uint8_t *source,
                                     uint8_t *destination, uint32_t length_bytes,
                                     uint32_t destination_capacity, uint32_t *produced_bytes)
{
    uint8_t src_block[ET_AES_WRAP_BLOCK_SIZE];
    uint8_t dst_block[ET_AES_WRAP_BLOCK_SIZE];
    uint32_t src_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    uint32_t dst_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    uint32_t blocks;
    uint32_t output_bytes;
    uint32_t index;
    uint32_t offset;
    uint32_t copy_bytes;
    uint32_t output_copy_bytes;
    const et_aes_wrap_mapping_t *mapping;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;

    /* Phase 1: Validate configured state, public buffer bounds and active block/padding rules. */
    status = map_aes(aes_id, &mapping, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((source == NULL) || (destination == NULL) || (produced_bytes == NULL) ||
        (state->configured == 0u) || (length_bytes == 0u) ||
        (length_bytes > mapping->max_process_bytes) ||
        (destination_capacity > mapping->max_output_bytes))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    output_bytes = output_length_for(length_bytes, state->config.direction, state->config.mode,
                                     state->config.padding);

    if ((state->config.padding == ET_AES_WRAP_PADDING_NONE) &&
        (length_bytes % ET_AES_WRAP_BLOCK_SIZE != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((state->config.direction == ET_AES_WRAP_DIRECTION_DECRYPT) &&
        (length_bytes % ET_AES_WRAP_BLOCK_SIZE != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (destination_capacity < output_bytes)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Program hardware length, then stream each complete/partial staged block synchronously. */
    blocks = (length_bytes + (ET_AES_WRAP_BLOCK_SIZE - 1u)) / ET_AES_WRAP_BLOCK_SIZE;
    {
        et_wrap_status_t length_status = et_aes_wrap_set_data_length(aes_id, length_bytes);

        if (length_status != ET_WRAP_STATUS_OK)
        {
            return length_status;
        }
    }

    for (index = 0u; index < blocks; ++index)
    {
        offset = index * ET_AES_WRAP_BLOCK_SIZE;
        copy_bytes = length_bytes - offset;

        if (copy_bytes > ET_AES_WRAP_BLOCK_SIZE)
        {
            copy_bytes = ET_AES_WRAP_BLOCK_SIZE;
        }

        (void)memset(src_block, 0, sizeof(src_block));
        (void)memcpy(src_block, &source[offset], copy_bytes);
        bytes_to_words(src_block, src_words, state->config.endian);
        align_partial_input_word(src_words, copy_bytes, state->config.endian);

        if (!AES_writeDataBlocking(src_words, ET_AES_WRAP_TIMEOUT_BUDGET) ||
            !AES_readDataBlocking(dst_words, ET_AES_WRAP_TIMEOUT_BUDGET))
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        words_to_bytes(dst_words, dst_block, state->config.endian);
        output_copy_bytes = ET_AES_WRAP_BLOCK_SIZE;

        if ((state->config.mode == ET_AES_WRAP_MODE_CTR) && (copy_bytes < output_copy_bytes))
        {
            output_copy_bytes = copy_bytes;
        }

        (void)memcpy(&destination[offset], dst_block, output_copy_bytes);
    }

    /* Phase 3: Collect PKCS7 full-block tail when required and publish exact produced length. */
    if ((state->config.direction == ET_AES_WRAP_DIRECTION_ENCRYPT) &&
        (state->config.mode != ET_AES_WRAP_MODE_CTR) &&
        (state->config.padding == ET_AES_WRAP_PADDING_PKCS7) &&
        ((length_bytes % ET_AES_WRAP_BLOCK_SIZE) == 0u))
    {
        if (!AES_readDataBlocking(dst_words, ET_AES_WRAP_TIMEOUT_BUDGET))
        {
            return ET_WRAP_STATUS_TIMEOUT;
        }

        words_to_bytes(dst_words, dst_block, state->config.endian);
        (void)memcpy(&destination[blocks * ET_AES_WRAP_BLOCK_SIZE], dst_block,
                     ET_AES_WRAP_BLOCK_SIZE);
    }

    *produced_bytes = output_bytes;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Submit one canonical AES input block through the nonblocking Driver path.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] block Canonical 16-byte input block.
 *
 * @note This function writes AES hardware without waiting for completion and is intended for bounded
 *       IRQ/local sessions owned by Service. It requires active configured state.
 *
 * @return Stable Wrap status for mapping/state validation or Driver write result.
 */
et_wrap_status_t et_aes_wrap_block_write(et_aes_id_t aes_id,
                                         const uint8_t block[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((block == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(block, words, state->config.endian);

    return AES_writeDataNonBlocking(words) ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_BUSY;
}

/**
 * @brief Submit one canonical AES input block using the Driver's bounded blocking write path.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] block Canonical 16-byte input block.
 *
 * @note This function waits only up to ET_AES_WRAP_TIMEOUT_BUDGET for hardware input acceptance and
 *       does not read the corresponding output block.
 *
 * @return ET_WRAP_STATUS_OK when the block is accepted, timeout or validation error otherwise.
 */
et_wrap_status_t et_aes_wrap_block_write_wait(et_aes_id_t aes_id,
                                              const uint8_t block[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((block == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(block, words, state->config.endian);

    return AES_writeDataBlocking(words, ET_AES_WRAP_TIMEOUT_BUDGET) ? ET_WRAP_STATUS_OK
                                                                    : ET_WRAP_STATUS_TIMEOUT;
}

/**
 * @brief Write one canonical block through the isolated direct-input Test Driver Extension.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] block Canonical 16-byte input block.
 *
 * @note This validation-only operation is compiled only with Test Driver Extensions and returns raw
 *       Driver execution status; no test verdict is produced by Wrap.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_aes_wrap_block_write_direct(et_aes_id_t aes_id,
                                                const uint8_t block[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((block == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(block, words, state->config.endian);
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return driver_status(AES_testWriteInputBlock(words));
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Write two canonical blocks through the isolated paired direct-input Test Driver path.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] first First canonical 16-byte block.
 * @param[in] second Second canonical 16-byte block.
 *
 * @note Both blocks are packed before the Test Driver call so the validation path observes one exact
 *       paired hardware operation. No host-side success criterion is evaluated here.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_aes_wrap_block_write_pair_direct(et_aes_id_t aes_id,
                                                     const uint8_t first[ET_AES_WRAP_BLOCK_SIZE],
                                                     const uint8_t second[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t first_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    uint32_t second_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((first == NULL) || (second == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(first, first_words, state->config.endian);
    bytes_to_words(second, second_words, state->config.endian);
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)

    return driver_status(
        AES_testWriteInputBlockPair(first_words, second_words, ET_AES_WRAP_TIMEOUT_BUDGET));
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Write one canonical block and exercise the validation-only disable-during-input path.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] block Canonical 16-byte input block.
 *
 * @note This Test Driver Extension intentionally changes AES hardware state as part of a negative/
 *       maintenance validation path. Wrap returns only the Driver fact and does not interpret the result.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_aes_wrap_block_write_disable_direct(et_aes_id_t aes_id,
                                                        const uint8_t block[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((block == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    bytes_to_words(block, words, state->config.endian);
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    status = driver_status(AES_testWriteInputBlockThenDisable(words, ET_AES_WRAP_TIMEOUT_BUDGET));

    if (status == ET_WRAP_STATUS_OK)
    {
        state->enabled = 0u;
        state->configured = 0u;
    }

    return status;
#else

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}

/**
 * @brief Read one available AES output block and convert it to canonical boundary bytes.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] block Canonical 16-byte output block.
 *
 * @note This is a nonblocking hardware result read. The function returns BUSY when output is not yet
 *       available and does not spin or decide whether the block is correct.
 *
 * @return ET_WRAP_STATUS_OK when a block is read; BUSY or validation/mapping error otherwise.
 */
et_wrap_status_t et_aes_wrap_block_read(et_aes_id_t aes_id, uint8_t block[ET_AES_WRAP_BLOCK_SIZE])
{
    uint32_t words[ET_AES_WRAP_WORDS_PER_BLOCK];
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((block == NULL) || (state->configured == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (!AES_readDataNonBlocking(words))
    {
        return ET_WRAP_STATUS_BUSY;
    }

    words_to_bytes(words, block, state->config.endian);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Snapshot normalized AES busy/data-request/finish/IRQ hardware status.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] snapshot Normalized AES status snapshot.
 *
 * @note This function reads AES hardware only and does not acknowledge any interrupt/status source.
 *
 * @return ET_WRAP_STATUS_OK when the snapshot is captured, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_get_status(et_aes_id_t aes_id, et_aes_wrap_status_snapshot_t *snapshot)
{
    uint8_t status_bits;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((snapshot == NULL) || (state->enabled == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status_bits = AES_getStatus();
    snapshot->busy = AES_isBusy() ? 1u : 0u;
    snapshot->data_in_request = (status_bits & AES_STS_DATA_IN_REQ) != 0u ? 1u : 0u;
    snapshot->data_out_request = (status_bits & AES_STS_DATA_OUT_REQ) != 0u ? 1u : 0u;
    snapshot->finish = (status_bits & AES_STS_COMPLETE) != 0u ? 1u : 0u;
    snapshot->irq_status = AES_getAllInterruptStatus();

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected public AES status bits through the selected Driver.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] status_bits Nonempty subset of ET_AES_WRAP_STATUS_ALL.
 *
 * @note This function acknowledges AES status hardware only. It does not alter IRQ enable/mask state
 *       or Service evidence ownership.
 *
 * @return ET_WRAP_STATUS_OK when selected status bits are cleared, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_clear_status(et_aes_id_t aes_id, uint8_t status_bits)
{
    et_aes_wrap_state_t *state;
    et_wrap_status_t status = map_aes(aes_id, NULL, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((state->enabled == 0u) || (status_bits == 0u) ||
        ((status_bits & ~ET_AES_WRAP_STATUS_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    AES_clearStatus(status_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one nonempty normalized AES interrupt-source mask against selected-chip capability.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Stable AES interrupt-source bits requested by the caller.
 * @param[out] mapping Optional selected-chip mapping returned for subsequent Driver action.
 *
 * @note This helper performs capability/argument validation only and does not change AES IRQ hardware.
 *
 * @return ET_WRAP_STATUS_OK when the source mask is valid and supported; stable error otherwise.
 */
static et_wrap_status_t validate_irq(et_aes_id_t aes_id, uint32_t source_bits,
                                     const et_aes_wrap_mapping_t **mapping)
{
    const et_aes_wrap_mapping_t *local_mapping;
    et_wrap_status_t status = map_aes(aes_id, &local_mapping, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((source_bits == 0u) || ((source_bits & ~ET_AES_WRAP_IRQ_ALL) != 0u) ||
        ((source_bits & ~local_mapping->irq_event_mask) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping != NULL)
    {
        *mapping = local_mapping;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected normalized AES interrupt sources in AES hardware.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function changes AES peripheral interrupt-source enable state only. NVIC/route ownership
 *       remains with IRQ Manager/IRQ Wrap.
 *
 * @return ET_WRAP_STATUS_OK when sources are enabled, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_enable(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_enableInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected normalized AES interrupt sources in AES hardware.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function changes AES peripheral interrupt-source enable state only and does not unbind
 *       the CPU IRQ route.
 *
 * @return ET_WRAP_STATUS_OK when sources are disabled, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_disable(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_disableInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Mask selected normalized AES interrupt sources.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function changes AES peripheral interrupt mask hardware only; source enable and NVIC
 *       route ownership are unchanged.
 *
 * @return ET_WRAP_STATUS_OK when sources are masked, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_mask(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_setInterruptMask(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Unmask selected normalized AES interrupt sources.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function changes AES peripheral interrupt mask hardware only and does not enable sources
 *       or CPU routing.
 *
 * @return ET_WRAP_STATUS_OK when sources are unmasked, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_unmask(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_clearInterruptMask(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Force selected normalized AES interrupt sources for validation.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function deliberately changes AES force/indication hardware. It returns only hardware
 *       execution facts and does not synthesize a test verdict.
 *
 * @return ET_WRAP_STATUS_OK when sources are forced, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_force(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_forceInterrupt(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear selected normalized AES interrupt sources.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source_bits Nonempty supported AES interrupt-source mask.
 *
 * @note This function acknowledges AES peripheral interrupt status only. Enable/mask and CPU route
 *       ownership remain unchanged.
 *
 * @return ET_WRAP_STATUS_OK when sources are cleared, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_clear(et_aes_id_t aes_id, uint32_t source_bits)
{
    et_wrap_status_t status = validate_irq(aes_id, source_bits, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    AES_clearInterruptStatus(source_bits);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Snapshot normalized raw and effective AES interrupt hardware facts without clearing them.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] snapshot Raw and status interrupt observations.
 *
 * @note This function reads AES interrupt hardware only and performs no acknowledge/mask/enable action.
 *
 * @return ET_WRAP_STATUS_OK when the snapshot is captured, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_irq_snapshot_get(et_aes_id_t aes_id,
                                              et_aes_wrap_irq_snapshot_t *snapshot)
{
    et_wrap_status_t status = map_aes(aes_id, NULL, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    status = driver_status(AES_testGetInterruptSnapshot(&snapshot->raw, &snapshot->status));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }
#else
    snapshot->raw = 0u;
    snapshot->status = AES_getAllInterruptStatus();
#endif

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return the managed physical IRQ route and supported event mask for one logical AES instance.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[out] route Stable route for IRQ Manager binding.
 *
 * @note This function exposes Chip Config route facts only and does not register/enable the physical line.
 *
 * @return ET_WRAP_STATUS_OK when route is available, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_get_irq_route(et_aes_id_t aes_id, et_irq_route_t *route)
{
    const et_aes_wrap_mapping_t *mapping;
    et_wrap_status_t status = map_aes(aes_id, &mapping, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (route == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    route->irq_line = (et_irq_line_t)mapping->irq;
    route->reserved = 0u;
    route->route_events = mapping->irq_event_mask;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure selected AES DMA request directions in AES hardware.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] request_bits Stable input/output DMA request mask; zero disables both directions.
 *
 * @note This function changes AES peripheral DMA-request enable state only. It does not configure a
 *       DMA controller or SYSCTRL DMAMUX route.
 *
 * @return ET_WRAP_STATUS_OK when request state is applied, otherwise validation/mapping error.
 */
et_wrap_status_t et_aes_wrap_dma_request_set(et_aes_id_t aes_id, uint32_t request_bits)
{
    et_wrap_status_t status = map_aes(aes_id, NULL, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((request_bits & ~ET_AES_WRAP_DMA_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((request_bits & ET_AES_WRAP_DMA_INPUT) != 0u)
    {
        AES_enableDMARequest(AES_DMA_EN_DATA_IN);
    }
    else
    {
        AES_disableDMARequest(AES_DMA_EN_DATA_IN);
    }

    if ((request_bits & ET_AES_WRAP_DMA_OUTPUT) != 0u)
    {
        AES_enableDMARequest(AES_DMA_EN_DATA_OUT);
    }
    else
    {
        AES_disableDMARequest(AES_DMA_EN_DATA_OUT);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute one target-local timed AES process through the isolated Test Driver Extension.
 *
 * @param[in] aes_id Stable logical AES instance identifier.
 * @param[in] source Canonical input bytes.
 * @param[out] destination Caller-owned output buffer.
 * @param[in] length_bytes Number of input bytes.
 * @param[in] destination_capacity Available output bytes.
 * @param[out] produced_bytes Exact output byte count returned by the Test Driver.
 * @param[out] elapsed_cycles Target-local elapsed cycle observation.
 *
 * @note This function validates the same stable process bounds as the normal path, programs hardware
 *       length, then delegates timing boundaries to the Test Driver. It returns observations only and
 *       never evaluates a performance requirement.
 *
 * @return Stable Wrap status for validation/Test Driver execution, or NOT_SUPPORTED without extensions.
 */
et_wrap_status_t et_aes_wrap_process_timed(et_aes_id_t aes_id, const uint8_t *source,
                                           uint8_t *destination, uint32_t length_bytes,
                                           uint32_t destination_capacity, uint32_t *produced_bytes,
                                           uint32_t *elapsed_cycles)
{
#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)
    uint8_t source_block[ET_AES_WRAP_BLOCK_SIZE];
    uint8_t destination_block[ET_AES_WRAP_BLOCK_SIZE];
    uint32_t source_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    uint32_t destination_words[ET_AES_WRAP_WORDS_PER_BLOCK];
    uint32_t block_count;
    uint32_t block_index;
    uint32_t block_offset;
    uint32_t block_cycles;
    uint32_t output_bytes;
    const et_aes_wrap_mapping_t *mapping;
    et_aes_wrap_state_t *state;
    et_wrap_status_t status;
    DRV_Status driver_result;

    /* Phase 1: Validate the bounded, block-aligned timing contract before hardware access. */
    status = map_aes(aes_id, &mapping, &state);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if ((source == NULL) || (destination == NULL) || (produced_bytes == NULL) ||
        (elapsed_cycles == NULL) || (state->configured == 0u) || (length_bytes == 0u) ||
        (length_bytes > mapping->max_process_bytes) ||
        (destination_capacity > mapping->max_output_bytes))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((state->config.padding != ET_AES_WRAP_PADDING_NONE) ||
        ((length_bytes % ET_AES_WRAP_BLOCK_SIZE) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    output_bytes = output_length_for(length_bytes, state->config.direction, state->config.mode,
                                     state->config.padding);

    if (destination_capacity < output_bytes)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = et_aes_wrap_set_data_length(aes_id, length_bytes);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 2: Time each complete hardware block and preserve canonical byte ordering at the boundary. */
    block_count = length_bytes / ET_AES_WRAP_BLOCK_SIZE;
    *elapsed_cycles = 0u;

    for (block_index = 0u; block_index < block_count; ++block_index)
    {
        block_offset = block_index * ET_AES_WRAP_BLOCK_SIZE;
        (void)memcpy(source_block, &source[block_offset], sizeof(source_block));
        bytes_to_words(source_block, source_words, state->config.endian);
        driver_result = AES_testProcessBlocksTimed(source_words, destination_words, 1u,
                                                   ET_AES_WRAP_TIMEOUT_BUDGET, &block_cycles);

        if (driver_result != DRV_OK)
        {
            return driver_status(driver_result);
        }

        words_to_bytes(destination_words, destination_block, state->config.endian);
        (void)memcpy(&destination[block_offset], destination_block, sizeof(destination_block));
        *elapsed_cycles += block_cycles;
    }

    /* Phase 3: Publish exact execution facts without applying a performance verdict. */
    *produced_bytes = output_bytes;

    return ET_WRAP_STATUS_OK;
#else
    (void)aes_id;
    (void)source;
    (void)destination;
    (void)length_bytes;
    (void)destination_capacity;
    (void)produced_bytes;
    (void)elapsed_cycles;

    return ET_WRAP_STATUS_NOT_SUPPORTED;
#endif
}
