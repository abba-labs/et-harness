#include "et_uart_wrap.h"

/**
 * @file et_uart_wrap.c
 * @brief Map stable UART API types and operations to the selected chip UART Driver.
 *
 * The Wrap performs validation/normalization only and contains no test-case or
 * cross-IP orchestration logic.
 */

#include <string.h>

#include "et6x_uart.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    UART_Type *uart;
    et_uart_id_t uart_id;
    uint8_t initialized;
    uint8_t last_snapshot_valid;
    uint16_t reserved16;
    uint32_t last_interrupt_status;
} et_uart_wrap_private_t;

typedef struct
{
    et_uart_id_t uart_id;
    UART_Type *instance;
    IRQn_Type irq;
    uint32_t feature_flags;
    uint32_t min_baudrate;
    uint32_t max_baudrate;
    uint32_t max_read_size;
    uint32_t max_write_size;
} et_uart_wrap_mapping_t;

typedef struct
{
    uint32_t line_rx_fifo_error;
    uint32_t modem_cts;
    uint32_t modem_dsr;
    uint32_t modem_ri;
    uint32_t modem_dcd;
    uint32_t modem_dcts;
    uint32_t modem_ddsr;
    uint32_t modem_teri;
    uint32_t modem_ddcd;
    uint32_t modem_rts;
    uint32_t modem_dtr;
} et_uart_wrap_status_masks_t;

static const et_uart_wrap_mapping_t uart_mappings[] = ET_CHIP_UART_MAP_TABLE;
static const et_uart_wrap_status_masks_t uart_status_masks = ET_CHIP_UART_STATUS_MASKS;

/* Logical ID, Driver instance and physical IRQ remain chip-private here. */

_Static_assert(sizeof(et_uart_wrap_private_t) <= sizeof(et_uart_wrap_handle_t),
               "ET_UART_WRAP_HANDLE_WORDS is too small");

/**
 * @brief View opaque UART Wrap storage as its private selected-Driver state.
 *
 * @param[in,out] handle Opaque public handle storage to reinterpret.
 *
 * @note The helper performs a representation cast only; callers remain responsible for validating initialization before dereferencing hardware state.
 *
 * @return Pointer to private UART Wrap state occupying the same storage.
 */

static et_uart_wrap_private_t *private_handle(et_uart_wrap_handle_t *handle)
{
    return (et_uart_wrap_private_t *)handle;
}

/**
 * @brief Resolve one stable logical UART ID to the selected Driver instance.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[out] uart Selected Driver instance pointer.
 *
 * @note Only compile-time Chip Config mapping data is read; no UART register or mutable Wrap state is accessed.
 *
 * @return ET_WRAP_STATUS_OK for a mapped instance, NOT_SUPPORTED when absent, or INVALID_ARGUMENT for a NULL output.
 */

static et_wrap_status_t map_uart(et_uart_id_t uart_id, UART_Type **uart)
{
    size_t index;

    if (uart == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < (sizeof(uart_mappings) / sizeof(uart_mappings[0])); ++index)
    {
        if (uart_mappings[index].uart_id == uart_id)
        {
            *uart = uart_mappings[index].instance;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Resolve one stable logical UART ID to its selected physical IRQ line.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[out] irq Selected CMSIS IRQ line.
 *
 * @note This is a Chip Config lookup only and does not bind, enable or acknowledge the CPU interrupt.
 *
 * @return ET_WRAP_STATUS_OK for a mapped route, NOT_SUPPORTED when absent, or INVALID_ARGUMENT for a NULL output.
 */

static et_wrap_status_t map_uart_irq(et_uart_id_t uart_id, IRQn_Type *irq)
{
    size_t index;

    if (irq == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    for (index = 0u; index < (sizeof(uart_mappings) / sizeof(uart_mappings[0])); ++index)
    {
        if (uart_mappings[index].uart_id == uart_id)
        {
            *irq = uart_mappings[index].irq;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Find the selected chip capability/mapping record for one logical UART.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 *
 * @note The returned record contains compile-time capability/limit/route facts only; no hardware is read.
 *
 * @return Pointer to the mapping record, or NULL when the logical UART is unsupported.
 */

static const et_uart_wrap_mapping_t *find_uart_mapping(et_uart_id_t uart_id)
{
    size_t index;

    for (index = 0u; index < (sizeof(uart_mappings) / sizeof(uart_mappings[0])); ++index)
    {
        if (uart_mappings[index].uart_id == uart_id)
        {
            return &uart_mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Translate a validated stable UART data width to the selected Driver word-length enum.
 *
 * @param[in] bits Validated public data width from five through eight bits.
 *
 * @note Callers validate the range before invoking this direct table translation; no hardware is accessed.
 *
 * @return Selected Driver word-length enumeration.
 */

static UART_WordLength map_word_length(uint8_t bits)
{
    static const UART_WordLength map[] = {UART_WORDLENGTH_5B, UART_WORDLENGTH_6B,
                                          UART_WORDLENGTH_7B, UART_WORDLENGTH_8B};

    return map[bits - ET_UART_WRAP_MIN_DATA_BITS];
}

/**
 * @brief Translate a validated stable UART parity selection to the selected Driver enum.
 *
 * @param[in] parity Validated public parity enumeration.
 *
 * @note Callers validate the public range first; this helper performs value translation only.
 *
 * @return Selected Driver parity enumeration.
 */

static UART_ParityBit map_parity(uint8_t parity)
{
    static const UART_ParityBit map[] = {UART_PARITY_NONE, UART_PARITY_EVEN, UART_PARITY_ODD,
                                         UART_PARITY_STICK_0, UART_PARITY_STICK_1};

    return map[parity];
}

/**
 * @brief Normalize one selected UART Driver result into the stable Wrap status namespace.
 *
 * @param[in] status UART Driver status returned by the selected SDK.
 *
 * @note No hardware access occurs; this is the only status-namespace translation used by UART Wrap operations.
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

        case DRV_INVALID:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }

        default:
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }
    }
}

/**
 * @brief Validate the public stop-bit/data-width relationship and translate it to the Driver enum.
 *
 * @param[in] bits Stable stop-bit selection.
 * @param[in] data_bits Stable data width used to validate 1.5/2-stop restrictions.
 * @param[out] stop_bits Selected Driver stop-bit enumeration.
 *
 * @note The 1.5-stop form is accepted only for 5-bit words and the 2-stop form only for wider supported words, matching the public contract without touching hardware.
 *
 * @return ET_WRAP_STATUS_OK for a valid combination, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_stop_bits(uint8_t bits, uint8_t data_bits, UART_StopBit *stop_bits)
{
    if (stop_bits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (bits == ET_UART_WRAP_STOP_BITS_1)
    {
        *stop_bits = UART_STOPBITS_1;

        return ET_WRAP_STATUS_OK;
    }

    if ((bits == ET_UART_WRAP_STOP_BITS_1_5) && (data_bits == ET_UART_WRAP_MIN_DATA_BITS))
    {
        *stop_bits = UART_STOPBITS_1_5_WORDLENGTH_5B;

        return ET_WRAP_STATUS_OK;
    }

    if ((bits == ET_UART_WRAP_STOP_BITS_2) && (data_bits > ET_UART_WRAP_MIN_DATA_BITS) &&
        (data_bits <= ET_UART_WRAP_MAX_DATA_BITS))
    {
        *stop_bits = UART_STOPBITS_2;

        return ET_WRAP_STATUS_OK;
    }

    return ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Translate one stable UART DMA request mode into the selected Driver enum.
 *
 * @param[in] mode Stable disabled/single/multi DMA mode.
 * @param[out] dma_mode Selected Driver DMA mode.
 *
 * @note This helper configures no DMA controller and performs value translation only.
 *
 * @return ET_WRAP_STATUS_OK for a supported mode, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_dma_mode(uint8_t mode, UART_DMAMode *dma_mode)
{
    if (dma_mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (mode)
    {
        case ET_UART_WRAP_DMA_DISABLED:
        {
            *dma_mode = UART_DMA_DISABLE;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_DMA_SINGLE:
        {
            *dma_mode = UART_DMA_SINGLE_MODE;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_DMA_MULTI:
        {
            *dma_mode = UART_DMA_MULTI_MODE;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate one stable TX FIFO threshold to the selected Driver enum.
 *
 * @param[in] threshold Stable TX FIFO threshold.
 * @param[out] driver_threshold Selected Driver TX threshold.
 *
 * @note Only published threshold values are accepted and no UART register is written.
 *
 * @return ET_WRAP_STATUS_OK for a supported threshold, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_tx_fifo_threshold(uint8_t threshold,
                                              UART_TXFIFOThreshold *driver_threshold)
{
    if (driver_threshold == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (threshold)
    {
        case ET_UART_WRAP_TXFIFO_THRESHOLD_0:
        {
            *driver_threshold = UART_TXFIFO_THRESHOLD_0BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_2:
        {
            *driver_threshold = UART_TXFIFO_THRESHOLD_2BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_4:
        {
            *driver_threshold = UART_TXFIFO_THRESHOLD_4BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_TXFIFO_THRESHOLD_8:
        {
            *driver_threshold = UART_TXFIFO_THRESHOLD_8BYTES;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Translate one stable RX FIFO threshold to the selected Driver enum.
 *
 * @param[in] threshold Stable RX FIFO threshold.
 * @param[out] driver_threshold Selected Driver RX threshold.
 *
 * @note Only published threshold values are accepted and no UART register is written.
 *
 * @return ET_WRAP_STATUS_OK for a supported threshold, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_rx_fifo_threshold(uint8_t threshold,
                                              UART_RXFIFOThreshold *driver_threshold)
{
    if (driver_threshold == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    switch (threshold)
    {
        case ET_UART_WRAP_RXFIFO_THRESHOLD_1:
        {
            *driver_threshold = UART_RXFIFO_THRESHOLD_1BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_4:
        {
            *driver_threshold = UART_RXFIFO_THRESHOLD_4BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_8:
        {
            *driver_threshold = UART_RXFIFO_THRESHOLD_8BYTES;

            return ET_WRAP_STATUS_OK;
        }

        case ET_UART_WRAP_RXFIFO_THRESHOLD_14:
        {
            *driver_threshold = UART_RXFIFO_THRESHOLD_14BYTES;

            return ET_WRAP_STATUS_OK;
        }

        default:
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }
}

/**
 * @brief Validate and translate one versioned public UART 9-bit configuration to Driver fields.
 *
 * @param[in] config Versioned chip-neutral 9-bit configuration.
 * @param[out] driver_config Selected Driver 9-bit configuration.
 *
 * @note This helper only builds Driver values after validating the public envelope/Boolean/mode fields; enabling 9-bit hardware is performed by the caller.
 *
 * @return ET_WRAP_STATUS_OK for a translatable configuration, otherwise ET_WRAP_STATUS_INVALID_ARGUMENT.
 */

static et_wrap_status_t map_nine_bit_config(const et_uart_wrap_nine_bit_config_t *config,
                                            UART_9BIT_ConfigParams *driver_config)
{
    if ((config == NULL) || (driver_config == NULL) || (config->struct_size < sizeof(*config)) ||
        (config->api_version != ET_UART_WRAP_API_VERSION) || (config->enabled > 1u) ||
        (config->receiver_mode > ET_UART_WRAP_NINE_BIT_RECEIVER_HARDWARE) ||
        (config->transmitter_mode > ET_UART_WRAP_NINE_BIT_TRANSMITTER_SOFTWARE))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    driver_config->RCVRMatchAddress = config->receiver_match_address;
    driver_config->XMITSelfAddress = config->transmitter_self_address;
    driver_config->receiveMode_9Bit =
        (config->receiver_mode == ET_UART_WRAP_NINE_BIT_RECEIVER_HARDWARE) ? UART_9BIT_RCVR_HW
                                                                           : UART_9BIT_RCVR_SW;
    driver_config->tranmitMode_9Bit =
        (config->transmitter_mode == ET_UART_WRAP_NINE_BIT_TRANSMITTER_SOFTWARE)
            ? UART_9BIT_XMIT_SW
            : UART_9BIT_XMIT_HW;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate normalized UART Wrap interrupt events into selected Driver interrupt bits.
 *
 * @param[in] flags Normalized UART Wrap interrupt-event mask.
 *
 * @note This pure mapping includes RX/TX/error/timeout/modem/9-bit/programmable-empty/busy sources; it neither enables nor clears hardware.
 *
 * @return Selected Driver interrupt mask represented by the normalized events.
 */

static uint32_t map_irq_flags_to_chip(uint32_t flags)
{
    /* Phase 1: Accumulate ordinary RX/TX/error/timeout/modem sources in the selected Driver namespace. */
    uint32_t chip_flags = UART_IT_NONE;

    if ((flags & ET_UART_WRAP_IRQ_RX_READY) != 0u)
    {
        chip_flags |= UART_IT_RECV_DATA_AVAILABLE_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_TX_READY) != 0u)
    {
        chip_flags |= UART_IT_TRANS_DATA_EMPTY_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_ERROR) != 0u)
    {
        chip_flags |= UART_IT_ERROR_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_RX_IDLE) != 0u)
    {
        chip_flags |= UART_IT_CHAR_TIMEOUT_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_MODEM_STATUS) != 0u)
    {
        chip_flags |= UART_IT_MODEM_STATUS_FLAG;
    }

    /* Phase 2: Add validation/extended 9-bit, programmable-empty and busy sources. */
    if ((flags & ET_UART_WRAP_IRQ_ADDRESS_RECEIVED) != 0u)
    {
        chip_flags |= UART_IT_9BITS_ADDR_RESV_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY) != 0u)
    {
        chip_flags |= UART_IT_PROMGRAM_THRE_FLAG;
    }

    if ((flags & ET_UART_WRAP_IRQ_BUSY) != 0u)
    {
        chip_flags |= UART_IT_UART_NOFIFO_BUSY;
    }

    return chip_flags;
}

/**
 * @brief Translate a selected Driver interrupt mask into normalized UART Wrap events.
 *
 * @param[in] chip_status Driver interrupt bits captured from UART hardware.
 *
 * @note Known sources are mapped explicitly; a nonzero unrecognized Driver condition is preserved as ET_UART_WRAP_IRQ_OTHER instead of being silently dropped.
 *
 * @return Normalized UART Wrap interrupt-event mask.
 */

static uint32_t map_irq_flags_mask_from_chip(uint32_t chip_status)
{
    /* Phase 1: Normalize known ordinary Driver interrupt bits into stable Wrap events. */
    uint32_t flags = 0u;

    if ((chip_status & UART_IT_RECV_DATA_AVAILABLE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_RX_READY;
    }

    if ((chip_status & UART_IT_TRANS_DATA_EMPTY_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_TX_READY;
    }

    if ((chip_status & UART_IT_ERROR_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_ERROR;
    }

    if ((chip_status & UART_IT_CHAR_TIMEOUT_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_RX_IDLE;
    }

    if ((chip_status & UART_IT_MODEM_STATUS_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_MODEM_STATUS;
    }

    /* Phase 2: Normalize extended sources and preserve any otherwise-unknown nonzero status. */
    if ((chip_status & UART_IT_9BITS_ADDR_RESV_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_ADDRESS_RECEIVED;
    }

    if ((chip_status & UART_IT_PROMGRAM_THRE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY;
    }

    if ((chip_status & UART_IT_UART_NOFIFO_BUSY) != 0u)
    {
        flags |= ET_UART_WRAP_IRQ_BUSY;
    }

    return (flags == 0u) && (chip_status != UART_IT_NONE) ? ET_UART_WRAP_IRQ_OTHER : flags;
}

/**
 * @brief Normalize active selected-Driver interrupt state into UART Wrap events.
 *
 * @param[in] chip_status Driver interrupt state to normalize.
 *
 * @note This wrapper intentionally delegates to the bounded mask translator so active and sampled interrupt namespaces stay identical.
 *
 * @return Normalized UART Wrap interrupt-event mask.
 */

static uint32_t map_irq_flags_from_chip(uint32_t chip_status)
{
    return map_irq_flags_mask_from_chip(chip_status);
}

/**
 * @brief Normalize selected Driver UART line-status bits into stable Wrap line facts.
 *
 * @param[in] chip_status Raw selected-Driver line-status value.
 *
 * @note The RX-FIFO-error bit comes from selected Chip Config status masks while all public result bits remain chip-neutral. Hardware is not modified.
 *
 * @return Stable UART Wrap line-status mask.
 */

static uint32_t map_line_flags_from_chip(uint32_t chip_status)
{
    /* Phase 1: Normalize receive/error and transmitter-empty line-status facts. */
    uint32_t flags = 0u;

    if ((chip_status & UART_LINE_STA_DR_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_DATA_READY;
    }

    if ((chip_status & UART_LINE_STA_OE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_OVERRUN;
    }

    if ((chip_status & UART_LINE_STA_PE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_PARITY_ERROR;
    }

    if ((chip_status & UART_LINE_STA_FE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_FRAMING_ERROR;
    }

    if ((chip_status & UART_LINE_STA_BI_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_BREAK;
    }

    if ((chip_status & UART_LINE_STA_THRE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_TX_HOLDING_EMPTY;
    }

    if ((chip_status & UART_LINE_STA_TEMT_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_TX_EMPTY;
    }

    /* Phase 2: Add chip-mapped FIFO-error and 9-bit address observations. */
    if ((chip_status & uart_status_masks.line_rx_fifo_error) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_RX_FIFO_ERROR;
    }

    if ((chip_status & UART_LINE_STA_ADDR_RCVD_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_LINE_ADDRESS_RECEIVED;
    }

    return flags;
}

/**
 * @brief Extract the stable UART error-only subset from selected Driver line status.
 *
 * @param[in] chip_status Raw selected-Driver line-status value.
 *
 * @note Overrun/parity/framing/break/RX-FIFO-error facts are normalized without clearing the sampled hardware state.
 *
 * @return Stable UART Wrap error mask.
 */

static uint32_t map_error_flags_from_chip(uint32_t chip_status)
{
    /* Phase 1: Collect core overrun/parity/framing/break error facts. */
    uint32_t flags = 0u;

    if ((chip_status & UART_LINE_STA_OE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_ERROR_OVERRUN;
    }

    if ((chip_status & UART_LINE_STA_PE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_ERROR_PARITY;
    }

    if ((chip_status & UART_LINE_STA_FE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_ERROR_FRAMING;
    }

    if ((chip_status & UART_LINE_STA_BI_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_ERROR_BREAK;
    }

    /* Phase 2: Add the selected-chip RX FIFO error bit to the stable error subset. */
    if ((chip_status & uart_status_masks.line_rx_fifo_error) != 0u)
    {
        flags |= ET_UART_WRAP_ERROR_RX_FIFO;
    }

    return flags;
}

/**
 * @brief Normalize selected Driver UART occupancy/busy bits into stable runtime-state facts.
 *
 * @param[in] chip_status Raw selected-Driver UART status value.
 *
 * @note The result describes hardware state only and does not imply command success, readiness polling or a test verdict.
 *
 * @return Stable UART Wrap runtime-state mask.
 */

static uint32_t map_state_flags_from_chip(uint32_t chip_status)
{
    /* Phase 1: Normalize transmitter busy/not-full/empty state. */
    uint32_t flags = 0u;

    if ((chip_status & UART_STA_BUSY_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_STATE_BUSY;
    }

    if ((chip_status & UART_STA_TFNF_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_STATE_TX_NOT_FULL;
    }

    if ((chip_status & UART_STA_TFE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_STATE_TX_EMPTY;
    }

    /* Phase 2: Normalize receiver nonempty/full occupancy state. */
    if ((chip_status & UART_STA_RFNE_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_STATE_RX_NOT_EMPTY;
    }

    if ((chip_status & UART_STA_RFF_FLAG) != 0u)
    {
        flags |= ET_UART_WRAP_STATE_RX_FULL;
    }

    return flags;
}

/**
 * @brief Validate one opaque UART handle and return its initialized private state.
 *
 * @param[in,out] handle Opaque UART Wrap handle to validate.
 * @param[out] private Pointer to the private handle state on success.
 *
 * @note The helper performs no peripheral access; it centralizes the state guard used before every handle-bound UART operation.
 *
 * @return ET_WRAP_STATUS_OK for an initialized handle, STATE_ERROR for an idle handle, or INVALID_ARGUMENT for NULL inputs.
 */

static et_wrap_status_t require_initialized(et_uart_wrap_handle_t *handle,
                                            et_uart_wrap_private_t **private)
{
    if ((handle == NULL) || (private == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *private = private_handle(handle);

    return ((*private)->initialized != 0u) ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Initialize one versioned bounded-I/O result envelope to deterministic success/zero defaults.
 *
 * @param[out] result UART I/O result structure to initialize.
 *
 * @note Only caller-owned result memory is written; no transfer or UART hardware access occurs.
 */

static void init_io_result(et_uart_wrap_io_result_t *result)
{
    memset(result, 0, sizeof(*result));
    result->struct_size = (uint16_t)sizeof(*result);
    result->api_version = ET_UART_WRAP_API_VERSION;
    result->status = ET_WRAP_STATUS_OK;
}

/**
 * @brief Return selected-chip UART limits/features in the stable capability structure.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[out] capabilities Versioned capability structure to populate.
 *
 * @note Base feature/limit facts come from Chip Config. Shadow/FIFO-access capability bits are augmented from the target-local component snapshot because those implementation options are runtime-visible hardware facts; no feature is enabled by this query.
 *
 * @return ET_WRAP_STATUS_OK when capabilities are returned, INVALID_ARGUMENT for NULL output, or NOT_SUPPORTED for an unknown UART ID.
 */

et_wrap_status_t et_uart_wrap_get_capabilities(et_uart_id_t uart_id,
                                               et_uart_wrap_capabilities_t *capabilities)
{
    const et_uart_wrap_mapping_t *mapping;
    UART_Type *uart;

    if (capabilities == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 1: Resolve compile-time capability/limit facts for the logical UART. */
    mapping = find_uart_mapping(uart_id);

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    uart = mapping->instance;
    memset(capabilities, 0, sizeof(*capabilities));
    capabilities->struct_size = (uint16_t)sizeof(*capabilities);
    capabilities->api_version = ET_UART_WRAP_API_VERSION;
    capabilities->feature_flags = mapping->feature_flags;
    /* Phase 2: Augment runtime-visible implementation options from the target component snapshot. */
    {
        UART_TestComponentSnapshot_TypeDef component;

        if (UART_testGetComponentSnapshot(uart, &component) == DRV_OK)
        {
            if ((component.componentParameter & UART_TEST_CPR_SHADOW_Msk) != 0u)
            {
                capabilities->feature_flags |= ET_UART_WRAP_CAP_SHADOW;
            }

            if ((component.componentParameter & UART_TEST_CPR_FIFO_ACCESS_Msk) != 0u)
            {
                capabilities->feature_flags |= ET_UART_WRAP_CAP_FIFO_ACCESS;
            }
        }
    }

    /* Phase 3: Publish stable limits after feature discovery is complete. */
    capabilities->min_baudrate = mapping->min_baudrate;
    capabilities->max_baudrate = mapping->max_baudrate;
    capabilities->max_read_size = mapping->max_read_size;
    capabilities->max_write_size = mapping->max_write_size;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve the trusted selected-Driver TX or RX data endpoint used when PC configures DMA.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[in] endpoint Stable TX or RX DMA endpoint selector.
 * @param[out] address Resolved target-local data-register address.
 *
 * @note The address is obtained through the UART Test Driver boundary rather than hard-coded in common Wrap. This function does not configure UART DMA requests or the DMA controller.
 *
 * @return ET_WRAP_STATUS_OK for a resolved endpoint, INVALID_ARGUMENT for bad selector/output, NOT_SUPPORTED for unknown UART, or IO_ERROR on Driver failure.
 */

et_wrap_status_t et_uart_wrap_get_dma_endpoint_address(et_uart_id_t uart_id, uint8_t endpoint,
                                                       uintptr_t *address)
{
    UART_Type *uart;

    if (address == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    *address = 0u;

    if (map_uart(uart_id, &uart) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (endpoint == ET_UART_WRAP_DMA_ENDPOINT_TX)
    {
        return (UART_testGetTxDMAEndpointAddress(uart, address) == DRV_OK)
                   ? ET_WRAP_STATUS_OK
                   : ET_WRAP_STATUS_IO_ERROR;
    }
    else if (endpoint == ET_UART_WRAP_DMA_ENDPOINT_RX)
    {
        return (UART_testGetRxDMAEndpointAddress(uart, address) == DRV_OK)
                   ? ET_WRAP_STATUS_OK
                   : ET_WRAP_STATUS_IO_ERROR;
    }
    else
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }
}

/**
 * @brief Resolve normalized UART interrupt ownership to one physical selected-chip IRQ route.
 *
 * @param[in] uart_id Stable logical UART instance identifier.
 * @param[in] interrupt_flags Nonempty normalized UART event mask to associate with the route.
 * @param[out] route Physical IRQ line plus unchanged normalized route events.
 *
 * @note Route facts come from selected Chip Config only. The function does not bind IRQ Manager, set NVIC priority or enable UART interrupt sources.
 *
 * @return ET_WRAP_STATUS_OK for a valid mapped route, INVALID_ARGUMENT for an invalid event/output envelope, or NOT_SUPPORTED for an unmapped UART.
 */

et_wrap_status_t et_uart_wrap_get_irq_route(et_uart_id_t uart_id, uint32_t interrupt_flags,
                                            et_irq_route_t *route)
{
    UART_Type *uart;
    IRQn_Type irq;
    const uint32_t supported = ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_TX_READY |
                               ET_UART_WRAP_IRQ_ERROR | ET_UART_WRAP_IRQ_RX_IDLE |
                               ET_UART_WRAP_IRQ_MODEM_STATUS | ET_UART_WRAP_IRQ_ADDRESS_RECEIVED |
                               ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY | ET_UART_WRAP_IRQ_BUSY;

    if ((route == NULL) || (interrupt_flags == 0u) || ((interrupt_flags & ~supported) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((map_uart(uart_id, &uart) != ET_WRAP_STATUS_OK) ||
        (map_uart_irq(uart_id, &irq) != ET_WRAP_STATUS_OK))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    (void)uart;
    route->irq_line = (et_irq_line_t)irq;
    route->reserved = 0u;
    route->route_events = interrupt_flags;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate one versioned UART configuration, configure the selected Driver and publish an initialized opaque handle.
 *
 * @param[out] handle Opaque UART Wrap handle to initialize.
 * @param[in] config Versioned chip-neutral UART configuration.
 *
 * @note All public fields/options and logical mapping are validated before Driver configuration. The handle is zeroed before construction and again on Driver failure; initialization configures baud/format with DMA and interrupts disabled but does not bind IRQ Manager.
 *
 * @return ET_WRAP_STATUS_OK on initialized hardware/handle, otherwise validation, mapping or IO error.
 */

et_wrap_status_t et_uart_wrap_init(et_uart_wrap_handle_t *handle,
                                   const et_uart_wrap_config_t *config)
{
    et_uart_wrap_private_t *private;
    UART_ConfigParams uart_config;
    UART_StopBit stop_bits;
    UART_Type *uart;
    et_wrap_status_t status;

    /* Phase 1: Validate the versioned public UART envelope before constructing Driver values. */
    if ((handle == NULL) || (config == NULL) ||
        (config->struct_size < ET_UART_WRAP_CONFIG_V1_MIN_SIZE) ||
        (config->api_version != ET_UART_WRAP_API_VERSION) || (config->baudrate == 0u) ||
        (config->data_bits < ET_UART_WRAP_MIN_DATA_BITS) ||
        (config->data_bits > ET_UART_WRAP_MAX_DATA_BITS) ||
        (config->parity > ET_UART_WRAP_PARITY_STICK_ONE) ||
        ((config->stop_bits != ET_UART_WRAP_STOP_BITS_1) &&
         (config->stop_bits != ET_UART_WRAP_STOP_BITS_2) &&
         (config->stop_bits != ET_UART_WRAP_STOP_BITS_1_5)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (config->flags != 0u)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    /* Phase 2: Resolve the selected instance and build the opaque handle plus Driver configuration. */
    status = map_uart(config->uart_id, &uart);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(handle, 0, sizeof(*handle));
    private = private_handle(handle);
    private->uart = uart;
    private->uart_id = config->uart_id;
    private->last_snapshot_valid = 0u;
    private->last_interrupt_status = UART_IT_NONE;

    UART_initConfigParams(&uart_config);
    uart_config.baudRate = config->baudrate;
    uart_config.wordLength = map_word_length(config->data_bits);
    status = map_stop_bits(config->stop_bits, config->data_bits, &stop_bits);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    uart_config.stopBits = stop_bits;
    uart_config.parity = map_parity(config->parity);
    uart_config.DMAMode = UART_DMA_DISABLE;
    uart_config.irqEnableFlag = UART_IT_NONE;

    /* Phase 3: Configure UART hardware with DMA/interrupts disabled and publish initialized state only on success. */
    if (UART_config(private->uart, &uart_config) != DRV_OK)
    {
        memset(handle, 0, sizeof(*handle));

        return ET_WRAP_STATUS_IO_ERROR;
    }

    private->initialized = 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Quiesce UART interrupt state, software-reset the peripheral and invalidate the opaque handle.
 *
 * @param[in,out] handle Opaque UART Wrap handle to release.
 *
 * @note An already-idle handle is deterministically zeroed and succeeds. Active teardown disables every UART source used by the contract, clears sampled busy indication, performs Driver software reset and clears the handle only after reset succeeds.
 *
 * @return ET_WRAP_STATUS_OK when the handle is idle/invalidated, INVALID_ARGUMENT for NULL handle, or mapped Driver reset error.
 */

et_wrap_status_t et_uart_wrap_deinit(et_uart_wrap_handle_t *handle)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if (handle == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    private = private_handle(handle);

    /* Phase 1: Make already-idle teardown deterministic without touching hardware. */
    if (private->initialized == 0u)
    {
        memset(handle, 0, sizeof(*handle));

        return ET_WRAP_STATUS_OK;
    }

    /* Phase 2: Quiesce every contract-owned UART interrupt source before reset. */
    UART_disableInterrupt(private->uart,
                          UART_IT_RECV_DATA_AVAILABLE_FLAG | UART_IT_TRANS_DATA_EMPTY_FLAG |
                              UART_IT_CHAR_TIMEOUT_FLAG | UART_IT_ERROR_FLAG |
                              UART_IT_MODEM_STATUS_FLAG | UART_IT_9BITS_ADDR_RESV_FLAG |
                              UART_IT_PROMGRAM_THRE_FLAG | UART_IT_UART_NOFIFO_BUSY);
    UART_clearInterruptStatus(private->uart, UART_IT_UART_NOFIFO_BUSY);
    /* Phase 3: Reset UART hardware and invalidate the opaque handle only after reset succeeds. */
    status = map_driver_status(UART_performSoftwareReset(private->uart));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(handle, 0, sizeof(*handle));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable selected normalized UART interrupt sources through the selected Driver.
 *
 * @param[in,out] handle Initialized UART handle whose peripheral sources are enabled.
 * @param[in] interrupt_flags Nonempty supported normalized interrupt mask.
 *
 * @note Only UART peripheral source enable state changes; IRQ Manager/NVIC ownership remains outside Wrap. Unknown or unmappable event bits are rejected.
 *
 * @return ET_WRAP_STATUS_OK on hardware enable, or state/argument error.
 */

et_wrap_status_t et_uart_wrap_enable_interrupts(et_uart_wrap_handle_t *handle,
                                                uint32_t interrupt_flags)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);
    uint32_t chip_flags;

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    chip_flags = map_irq_flags_to_chip(interrupt_flags);

    if ((interrupt_flags == 0u) ||
        ((interrupt_flags & ~(ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_TX_READY |
                              ET_UART_WRAP_IRQ_ERROR | ET_UART_WRAP_IRQ_RX_IDLE |
                              ET_UART_WRAP_IRQ_MODEM_STATUS | ET_UART_WRAP_IRQ_ADDRESS_RECEIVED |
                              ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY | ET_UART_WRAP_IRQ_BUSY)) !=
         0u) ||
        (chip_flags == UART_IT_NONE))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    UART_enableInterrupt(private->uart, chip_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable selected normalized UART interrupt sources through the selected Driver.
 *
 * @param[in,out] handle Initialized UART handle whose peripheral sources are disabled.
 * @param[in] interrupt_flags Nonempty supported normalized interrupt mask.
 *
 * @note Only UART peripheral source enable state changes; the CPU route is not unbound and unknown event bits are rejected.
 *
 * @return ET_WRAP_STATUS_OK on hardware disable, or state/argument error.
 */

et_wrap_status_t et_uart_wrap_disable_interrupts(et_uart_wrap_handle_t *handle,
                                                 uint32_t interrupt_flags)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);
    uint32_t chip_flags;

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    chip_flags = map_irq_flags_to_chip(interrupt_flags);

    if ((interrupt_flags == 0u) ||
        ((interrupt_flags & ~(ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_TX_READY |
                              ET_UART_WRAP_IRQ_ERROR | ET_UART_WRAP_IRQ_RX_IDLE |
                              ET_UART_WRAP_IRQ_MODEM_STATUS | ET_UART_WRAP_IRQ_ADDRESS_RECEIVED |
                              ET_UART_WRAP_IRQ_PROGRAMMABLE_TX_EMPTY | ET_UART_WRAP_IRQ_BUSY)) !=
         0u) ||
        (chip_flags == UART_IT_NONE))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    UART_disableInterrupt(private->uart, chip_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Snapshot normalized UART interrupt/line/error facts and retain the exact Driver clear token in the handle.
 *
 * @param[in,out] handle Initialized UART handle whose last sampled clear token is updated.
 * @param[out] irq_status Versioned normalized interrupt snapshot.
 *
 * @note The target-local Test Driver captures resolved interrupt status and line status coherently. The raw Driver interruptStatus is cached only so a later clear operation acknowledges exactly this sampled state; no source is cleared here.
 *
 * @return ET_WRAP_STATUS_OK for a captured snapshot, otherwise argument/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_get_interrupt_status(et_uart_wrap_handle_t *handle,
                                                   et_uart_wrap_irq_status_t *irq_status)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;
    UART_TestInterruptSnapshot_TypeDef driver_snapshot;

    if (irq_status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 1: Validate handle state and initialize the versioned normalized snapshot. */
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(irq_status, 0, sizeof(*irq_status));
    irq_status->struct_size = (uint16_t)sizeof(*irq_status);
    irq_status->api_version = ET_UART_WRAP_API_VERSION;
    /* Phase 2: Capture one target-local interrupt/line snapshot without clearing hardware. */
    status = map_driver_status(UART_testGetInterruptSnapshot(private->uart, &driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    irq_status->interrupt_flags = map_irq_flags_from_chip(driver_snapshot.resolvedInterruptStatus);
    irq_status->event_flags = irq_status->interrupt_flags;
    irq_status->line_flags = map_line_flags_from_chip(driver_snapshot.lineStatus);
    irq_status->error_flags = map_error_flags_from_chip(driver_snapshot.lineStatus);
    /* Phase 3: Retain the exact Driver clear token for the subsequent acknowledge operation. */
    private->last_interrupt_status = driver_snapshot.interruptStatus;
    private->last_snapshot_valid = 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge exactly the UART interrupt state retained by the previous snapshot.
 *
 * @param[in,out] handle Initialized UART handle containing the last sampled Driver clear token.
 *
 * @note Clear is rejected until get_interrupt_status has produced a valid token. After the Driver clear, the token is invalidated so a stale snapshot cannot be cleared twice.
 *
 * @return ET_WRAP_STATUS_OK when the sampled state is acknowledged, STATE_ERROR without a valid snapshot, or handle validation error.
 */

et_wrap_status_t et_uart_wrap_clear_interrupts(et_uart_wrap_handle_t *handle)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (private->last_snapshot_valid == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    UART_clearInterruptStatus(private->uart, private->last_interrupt_status);
    private->last_interrupt_status = UART_IT_NONE;
    private->last_snapshot_valid = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read currently available UART FIFO bytes once without owning retry policy.
 *
 * @param[in,out] handle Initialized UART handle whose RX FIFO is consumed.
 * @param[out] data Destination buffer for available bytes.
 * @param[in] capacity Maximum bytes accepted by the destination.
 * @param[out] result Versioned one-shot transfer result.
 *
 * @note Capacity is bounded to the Driver's uint16_t interface and UART_receiveWithFIFO drains only the current FIFO level. The function does not wait for the requested capacity to arrive.
 *
 * @return ET_WRAP_STATUS_OK with transferred count (including zero), or argument/state error.
 */

et_wrap_status_t et_uart_wrap_read(et_uart_wrap_handle_t *handle, uint8_t *data, size_t capacity,
                                   et_uart_wrap_io_result_t *result)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;
    uint16_t limited_capacity;

    if ((data == NULL) || (capacity == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    init_io_result(result);
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        result->status = status;

        return status;
    }

    limited_capacity = (capacity > UINT16_MAX) ? UINT16_MAX : (uint16_t)capacity;
    result->transferred = UART_receiveWithFIFO(private->uart, data, limited_capacity);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Attempt one atomic UART byte write only when the transmitter is completely empty.
 *
 * @param[in,out] handle Initialized UART handle whose TX FIFO may be written.
 * @param[in] data Source byte buffer.
 * @param[in] length Available source bytes.
 * @param[out] result Versioned one-shot transfer result.
 *
 * @note This strict atomic helper checks TEMT and intentionally offers exactly one byte to the non-blocking FIFO Driver; a busy transmitter returns WOULD_BLOCK with zero transfer. Multi-byte best-effort writes use et_uart_wrap_write_partial instead.
 *
 * @return ET_WRAP_STATUS_OK with transfer/WOULD_BLOCK facts, or argument/state error.
 */

et_wrap_status_t et_uart_wrap_write(et_uart_wrap_handle_t *handle, const uint8_t *data,
                                    size_t length, et_uart_wrap_io_result_t *result)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if ((data == NULL) || (length == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    init_io_result(result);
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        result->status = status;

        return status;
    }

    if (UART_getLineStatusFlag(private->uart, UART_LINE_STA_TEMT_FLAG) == 0u)
    {
        result->flags = ET_UART_WRAP_RESULT_WOULD_BLOCK;

        return ET_WRAP_STATUS_OK;
    }

    result->transferred =
        UART_transmitWithFIFO(private->uart, (uint8_t *)data, 1u, UART_NON_BLOCK_TRANSMIT_FIFO);

    if (result->transferred > length)
    {
        result->transferred = (uint32_t)length;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Offer as many UART bytes as hardware accepts in one non-blocking Driver call.
 *
 * @param[in,out] handle Initialized UART handle whose TX FIFO is written.
 * @param[in] data Source byte buffer.
 * @param[in] length Number of source bytes offered.
 * @param[out] result Versioned one-shot transfer result.
 *
 * @note Length is bounded to the Driver's uint16_t interface. The Driver may accept fewer bytes than offered; Wrap clamps any impossible over-report and owns no retry loop.
 *
 * @return ET_WRAP_STATUS_OK with the accepted-byte count, or argument/state error.
 */

et_wrap_status_t et_uart_wrap_write_partial(et_uart_wrap_handle_t *handle, const uint8_t *data,
                                            size_t length, et_uart_wrap_io_result_t *result)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;
    uint16_t limited_length;

    if ((data == NULL) || (length == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    init_io_result(result);
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        result->status = status;

        return status;
    }

    limited_length = (length > UINT16_MAX) ? UINT16_MAX : (uint16_t)length;
    result->transferred =
        UART_transmit(private->uart, (void *)data, limited_length, UART_NON_BLOCK_TRANSMIT_FIFO);

    if (result->transferred > limited_length)
    {
        result->transferred = limited_length;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Trigger the target-local UART busy-detect validation sequence and return raw recovery facts.
 *
 * @param[in,out] handle Initialized UART handle exercised by the Test Driver.
 * @param[out] result Versioned busy-detect observation structure.
 *
 * @note The isolated Test Driver owns the precise hardware trigger/observation/clear/recovery sequence. Wrap only normalizes its result fields and never converts them into a PASS/FAIL verdict.
 *
 * @return ET_WRAP_STATUS_OK for returned facts, otherwise argument/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_trigger_busy_detect(et_uart_wrap_handle_t *handle,
                                                  et_uart_wrap_busy_detect_result_t *result)
{
    et_uart_wrap_private_t *private;
    UART_TestBusyDetectResult_TypeDef driver_result;
    et_wrap_status_t status;

    if (result == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_driver_status(UART_testTriggerBusyDetect(private->uart, &driver_result));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(result, 0, sizeof(*result));
    result->struct_size = (uint16_t)sizeof(*result);
    result->api_version = ET_UART_WRAP_API_VERSION;
    result->pre_trigger_usr = driver_result.preTriggerUsr;
    result->observed_iir = driver_result.observedIir;
    result->observed_usr = driver_result.observedUsr;
    result->trigger_count = driver_result.triggerCount;
    result->busy_observed = driver_result.busyObserved;
    result->interrupt_observed = driver_result.interruptObserved;
    result->cleared = driver_result.cleared;
    result->recovered = driver_result.recovered;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure target-local shadow FIFO state and return the applied hardware facts.
 *
 * @param[in,out] handle Initialized UART handle exercised by the Test Driver.
 * @param[in] enabled Requested shadow FIFO enable state.
 * @param[in] tx_threshold Stable TX threshold.
 * @param[in] rx_threshold Stable RX threshold.
 * @param[out] state Versioned applied shadow FIFO state.
 *
 * @note Stable thresholds are translated before hardware access. The Test Driver performs the validation-only shadow-register operation; Wrap reports the applied state without test verdicts.
 *
 * @return ET_WRAP_STATUS_OK for applied facts, otherwise validation/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_shadow_fifo_config(et_uart_wrap_handle_t *handle, uint8_t enabled,
                                                 uint8_t tx_threshold, uint8_t rx_threshold,
                                                 et_uart_wrap_shadow_fifo_state_t *state)
{
    et_uart_wrap_private_t *private;
    UART_TXFIFOThreshold driver_tx;
    UART_RXFIFOThreshold driver_rx;
    UART_TestShadowFIFOState_TypeDef driver_state;
    et_wrap_status_t status;

    if (state == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_tx_fifo_threshold(tx_threshold, &driver_tx);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_rx_fifo_threshold(rx_threshold, &driver_rx);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_driver_status(
        UART_testConfigureShadowFIFO(private->uart, enabled, driver_tx, driver_rx, &driver_state));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(state, 0, sizeof(*state));
    state->struct_size = (uint16_t)sizeof(*state);
    state->api_version = ET_UART_WRAP_API_VERSION;
    state->enabled = driver_state.enabled;
    state->tx_threshold = driver_state.txThreshold;
    state->rx_threshold = driver_state.rxThreshold;
    state->fifo_access = driver_state.fifoAccess;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or disable the target-local direct FIFO access mode and report the applied state.
 *
 * @param[in,out] handle Initialized UART handle exercised by the Test Driver.
 * @param[in] enabled Requested canonical Boolean state.
 * @param[out] active Applied FIFO-access state returned by hardware.
 *
 * @note This is an isolated validation extension; it changes UART FIFO-access hardware only and does not perform normal TX/RX traffic.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_fifo_access_set(et_uart_wrap_handle_t *handle, uint8_t enabled,
                                              uint8_t *active)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if ((active == NULL) || (enabled > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(UART_testSetFIFOAccess(private->uart, enabled, active));
}

/**
 * @brief Read one byte through the target-local direct TX FIFO validation path.
 *
 * @param[in,out] handle Initialized UART handle exercised by the Test Driver.
 * @param[out] value Byte observed through direct TX FIFO access.
 *
 * @note The Test Driver owns the hardware-specific FIFO-access semantics; this function performs no host-side interpretation.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_fifo_tx_read(et_uart_wrap_handle_t *handle, uint8_t *value)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(UART_testReadTxFIFO(private->uart, value));
}

/**
 * @brief Inject one RX FIFO byte plus parity/framing metadata through the validation path.
 *
 * @param[in,out] handle Initialized UART handle exercised by the Test Driver.
 * @param[in] value Byte injected into the RX FIFO path.
 * @param[in] parity_error Canonical Boolean parity-error metadata.
 * @param[in] framing_error Canonical Boolean framing-error metadata.
 *
 * @note This deliberately changes validation-only FIFO hardware state; parity/framing metadata must be Boolean and the result remains a raw Driver status, not a verdict.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_fifo_rx_write(et_uart_wrap_handle_t *handle, uint8_t value,
                                            uint8_t parity_error, uint8_t framing_error)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if ((parity_error > 1u) || (framing_error > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(
        UART_testWriteRxFIFO(private->uart, value, parity_error, framing_error));
}

/**
 * @brief Read stable UART component identity plus current status/FIFO-level observations.
 *
 * @param[in,out] handle Initialized UART handle used for target-local snapshot reads.
 * @param[out] snapshot Versioned component/status snapshot.
 *
 * @note Component and status snapshots are obtained through separate Test Driver reads, then copied into chip-neutral fields. No sampled status is cleared or interpreted as PASS/FAIL.
 *
 * @return ET_WRAP_STATUS_OK for returned facts, otherwise argument/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_get_snapshot(et_uart_wrap_handle_t *handle,
                                           et_uart_wrap_snapshot_t *snapshot)
{
    et_uart_wrap_private_t *private;
    UART_TestComponentSnapshot_TypeDef driver_snapshot;
    UART_TestStatusSnapshot_TypeDef status_snapshot;
    et_wrap_status_t status;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 1: Read stable component identity/implementation facts. */
    status = map_driver_status(UART_testGetComponentSnapshot(private->uart, &driver_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 2: Read current UART/FIFO status and publish both snapshots in chip-neutral fields. */
    status = map_driver_status(UART_testGetStatusSnapshot(private->uart, &status_snapshot));

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->struct_size = (uint16_t)sizeof(*snapshot);
    snapshot->api_version = ET_UART_WRAP_API_VERSION;
    snapshot->component_parameter = driver_snapshot.componentParameter;
    snapshot->component_version = driver_snapshot.componentVersion;
    snapshot->component_type = driver_snapshot.componentType;
    snapshot->scratch = driver_snapshot.scratch;
    snapshot->uart_status = status_snapshot.uartStatus;
    snapshot->line_status = status_snapshot.lineStatus;
    snapshot->tx_fifo_level = status_snapshot.txFifoLevel;
    snapshot->rx_fifo_level = status_snapshot.rxFifoLevel;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Issue the selected Driver UART software-reset operation for an initialized handle.
 *
 * @param[in,out] handle Initialized UART handle whose peripheral is reset.
 *
 * @note This function resets UART hardware only; it intentionally does not rebuild Service IRQ/capture ownership, which is why Service reset commands use the full reset-to-idle path.
 *
 * @return Mapped Driver reset status or handle-state error.
 */

et_wrap_status_t et_uart_wrap_software_reset(et_uart_wrap_handle_t *handle)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(UART_performSoftwareReset(private->uart));
}

/**
 * @brief Enable or disable UART internal loopback through the target-local Test Driver.
 *
 * @param[in,out] handle Initialized UART handle whose loopback state is changed.
 * @param[in] enabled Canonical Boolean loopback state.
 *
 * @note Only UART internal loopback hardware changes; external pin routing and peer traffic remain outside Wrap.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_loopback(et_uart_wrap_handle_t *handle, uint8_t enabled)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return map_driver_status(UART_testSetLoopback(private->uart, enabled));
}

/**
 * @brief Validate and apply UART FIFO enable plus TX/RX threshold configuration.
 *
 * @param[in,out] handle Initialized UART handle whose FIFO configuration changes.
 * @param[in] config Versioned stable FIFO configuration.
 *
 * @note Stable threshold values are translated before calling the Test Driver. This function does not choose or modify UART DMA mode; Service coordinates the dependency when required.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_configure_fifo(et_uart_wrap_handle_t *handle,
                                             const et_uart_wrap_fifo_config_t *config)
{
    et_uart_wrap_private_t *private;
    UART_TXFIFOThreshold tx_threshold;
    UART_RXFIFOThreshold rx_threshold;
    et_wrap_status_t status;

    if ((config == NULL) ||
        (config->struct_size < offsetof(et_uart_wrap_fifo_config_t, reserved)) ||
        (config->api_version != ET_UART_WRAP_API_VERSION) || (config->enabled > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = map_tx_fifo_threshold(config->tx_threshold, &tx_threshold);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_rx_fifo_threshold(config->rx_threshold, &rx_threshold);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(
        UART_testConfigureFIFO(private->uart, config->enabled, tx_threshold, rx_threshold));
}

/**
 * @brief Return one normalized UART line/FIFO/error/runtime-state snapshot.
 *
 * @param[in,out] handle Initialized UART handle used for the status read.
 * @param[out] status Versioned normalized UART status facts.
 *
 * @note The Test Driver provides one raw status snapshot; Wrap maps interrupt, line, error and occupancy bits plus FIFO levels without clearing them or producing a test verdict.
 *
 * @return ET_WRAP_STATUS_OK for returned facts, otherwise argument/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_get_status(et_uart_wrap_handle_t *handle,
                                         et_uart_wrap_status_t *status)
{
    et_uart_wrap_private_t *private;
    UART_TestStatusSnapshot_TypeDef driver_snapshot;
    et_wrap_status_t wrap_status;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 1: Validate handle state and obtain one raw target-local status snapshot. */
    wrap_status = require_initialized(handle, &private);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    wrap_status = map_driver_status(UART_testGetStatusSnapshot(private->uart, &driver_snapshot));

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    /* Phase 2: Normalize interrupt, line, error, occupancy and FIFO-level facts without clearing them. */
    memset(status, 0, sizeof(*status));
    status->struct_size = (uint16_t)sizeof(*status);
    status->api_version = ET_UART_WRAP_API_VERSION;
    status->interrupt_flags = map_irq_flags_from_chip(driver_snapshot.interruptStatus);
    status->line_status = map_line_flags_from_chip(driver_snapshot.lineStatus);
    status->error_flags = map_error_flags_from_chip(driver_snapshot.lineStatus);
    status->state_flags = map_state_flags_from_chip(driver_snapshot.uartStatus);
    status->fifo_flags =
        status->state_flags & (ET_UART_WRAP_STATE_TX_NOT_FULL | ET_UART_WRAP_STATE_TX_EMPTY |
                               ET_UART_WRAP_STATE_RX_NOT_EMPTY | ET_UART_WRAP_STATE_RX_FULL);
    status->tx_fifo_level = driver_snapshot.txFifoLevel;
    status->rx_fifo_level = driver_snapshot.rxFifoLevel;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Assert or release continuous UART break generation.
 *
 * @param[in,out] handle Initialized UART handle whose break state changes.
 * @param[in] enabled Canonical Boolean break state.
 *
 * @note The target-local Test Driver changes only UART break-generation hardware; no timing or peer observation is performed here.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_break(et_uart_wrap_handle_t *handle, uint8_t enabled)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return map_driver_status(UART_testSetBreak(private->uart, enabled));
}

/**
 * @brief Halt or resume UART transmission through the selected Driver feature.
 *
 * @param[in,out] handle Initialized UART handle whose transfer engine is halted/resumed.
 * @param[in] enabled Canonical Boolean selecting halt or resume.
 *
 * @note This changes UART transfer hardware synchronously and does not modify Service capture/IRQ ownership or wait for a PC-observed condition.
 *
 * @return ET_WRAP_STATUS_OK after halt/resume, or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_halt(et_uart_wrap_handle_t *handle, uint8_t enabled)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (enabled != 0u)
    {
        UART_haltTransmission(private->uart);
    }
    else
    {
        UART_resumeTransmission(private->uart);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate stable DMA/FIFO thresholds and configure UART DMA request generation.
 *
 * @param[in,out] handle Initialized UART handle whose DMA request mode changes.
 * @param[in] dma_mode Stable disabled/single/multi UART DMA mode.
 * @param[in] tx_threshold Stable TX threshold.
 * @param[in] rx_threshold Stable RX threshold.
 *
 * @note The function configures UART-side DMA request behavior only. It never allocates/configures a DMA channel; Service/PC own cross-IP sequencing.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_dma_mode(et_uart_wrap_handle_t *handle, uint8_t dma_mode,
                                           uint8_t tx_threshold, uint8_t rx_threshold)
{
    et_uart_wrap_private_t *private;
    UART_DMAMode driver_mode;
    UART_TXFIFOThreshold driver_tx;
    UART_RXFIFOThreshold driver_rx;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_dma_mode(dma_mode, &driver_mode);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_tx_fifo_threshold(tx_threshold, &driver_tx);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = map_rx_fifo_threshold(rx_threshold, &driver_rx);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    return map_driver_status(UART_configDMA(private->uart, driver_mode, driver_tx, driver_rx));
}

/**
 * @brief Apply one validated UART 9-bit receiver/transmitter/address configuration.
 *
 * @param[in,out] handle Initialized UART handle whose 9-bit mode changes.
 * @param[in] config Versioned stable 9-bit configuration.
 *
 * @note Public configuration is translated before hardware access. Disabling uses the Test Driver enable control directly; enabling programs the Driver 9-bit fields first and then activates the mode.
 *
 * @return Mapped Driver status or validation/state error.
 */

et_wrap_status_t et_uart_wrap_configure_nine_bit(et_uart_wrap_handle_t *handle,
                                                 const et_uart_wrap_nine_bit_config_t *config)
{
    et_uart_wrap_private_t *private;
    UART_9BIT_ConfigParams driver_config;
    et_wrap_status_t status;

    status = map_nine_bit_config(config, &driver_config);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (config->enabled == 0u)
    {
        return map_driver_status(UART_testSetNineBitEnabled(private->uart, 0u));
    }

    UART_config9BitMode(private->uart, &driver_config);

    return map_driver_status(UART_testSetNineBitEnabled(private->uart, 1u));
}

/**
 * @brief Read currently available 9-bit UART FIFO values once without retry policy.
 *
 * @param[in,out] handle Initialized UART handle whose RX FIFO is consumed.
 * @param[out] data Destination array for 9-bit values stored in uint16_t elements.
 * @param[in] capacity Maximum number of values accepted.
 * @param[out] result Versioned one-shot transfer result.
 *
 * @note Capacity is bounded to uint16_t and the selected Driver drains only current FIFO content. Wrap does not wait for the requested number of values.
 *
 * @return ET_WRAP_STATUS_OK with transferred count, or argument/state error.
 */

et_wrap_status_t et_uart_wrap_read_nine_bit(et_uart_wrap_handle_t *handle, uint16_t *data,
                                            size_t capacity, et_uart_wrap_io_result_t *result)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;
    uint16_t limited_capacity;

    if ((data == NULL) || (capacity == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    init_io_result(result);
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        result->status = status;

        return status;
    }

    limited_capacity = (capacity > UINT16_MAX) ? UINT16_MAX : (uint16_t)capacity;
    result->transferred = UART_receiveWithFIFO9BIT(private->uart, data, limited_capacity);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Offer bounded 9-bit UART values to the TX FIFO in one non-blocking Driver call.
 *
 * @param[in,out] handle Initialized UART handle whose TX FIFO is written.
 * @param[in] data Source array of uint16_t elements carrying 9-bit values.
 * @param[in] length Number of values offered.
 * @param[out] result Versioned one-shot transfer result.
 *
 * @note Length is bounded to uint16_t and partial acceptance is a normal observation. Value-range validation is owned by the Service command before this low-level transfer.
 *
 * @return ET_WRAP_STATUS_OK with transferred count, or argument/state error.
 */

et_wrap_status_t et_uart_wrap_write_nine_bit(et_uart_wrap_handle_t *handle, const uint16_t *data,
                                             size_t length, et_uart_wrap_io_result_t *result)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;
    uint16_t limited_length;

    if ((data == NULL) || (length == 0u) || (result == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    init_io_result(result);
    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        result->status = status;

        return status;
    }

    limited_length = (length > UINT16_MAX) ? UINT16_MAX : (uint16_t)length;
    result->transferred = UART_transmitWithFIFO9BIT(private->uart, (uint16_t *)data, limited_length,
                                                    UART_NON_BLOCK_TRANSMIT_FIFO);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or disable the selected Driver's supported UART hardware flow-control mode.
 *
 * @param[in,out] handle Initialized UART handle whose flow-control state changes.
 * @param[in] enabled Canonical Boolean hardware-flow-control state.
 *
 * @note Only the single flow-control capability represented by the common contract is toggled. Pin routing and unsupported flow-control variants remain outside this function.
 *
 * @return ET_WRAP_STATUS_OK after the hardware toggle, or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_flow_control(et_uart_wrap_handle_t *handle, uint8_t enabled)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (enabled != 0u)
    {
        UART_enableHWFlowMode(private->uart);
    }
    else
    {
        UART_disableHWFlowMode(private->uart);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Drive stable UART RTS and DTR modem-control outputs through the selected Driver.
 *
 * @param[in,out] handle Initialized UART handle whose modem outputs change.
 * @param[in] control Versioned RTS/DTR control structure.
 *
 * @note The public envelope and Boolean fields are validated before driving signals. No modem input is sampled and no GPIO/IOMUX operation is performed here.
 *
 * @return ET_WRAP_STATUS_OK after both outputs are applied, or validation/state error.
 */

et_wrap_status_t et_uart_wrap_set_modem_control(et_uart_wrap_handle_t *handle,
                                                const et_uart_wrap_modem_control_t *control)
{
    et_uart_wrap_private_t *private;
    et_wrap_status_t status;

    if ((control == NULL) ||
        (control->struct_size < offsetof(et_uart_wrap_modem_control_t, reserved)) ||
        (control->api_version != ET_UART_WRAP_API_VERSION) || (control->rts_asserted > 1u) ||
        (control->dtr_asserted > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = require_initialized(handle, &private);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    UART_setRTSSign(private->uart, (control->rts_asserted != 0u) ? SET : RESET);
    UART_setDTRSign(private->uart, (control->dtr_asserted != 0u) ? SET : RESET);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Return normalized UART modem input, delta, output and raw status facts.
 *
 * @param[in,out] handle Initialized UART handle used for the status snapshot.
 * @param[out] status Versioned normalized modem status structure.
 *
 * @note The Test Driver supplies one status/control snapshot. Selected-chip bit masks from Chip Config are translated to stable CTS/DSR/RI/DCD and RTS/DTR flags while raw modem status is retained for evidence; hardware is not cleared.
 *
 * @return ET_WRAP_STATUS_OK for returned modem facts, otherwise argument/state/Driver error.
 */

et_wrap_status_t et_uart_wrap_get_modem_status(et_uart_wrap_handle_t *handle,
                                               et_uart_wrap_modem_status_t *status)
{
    et_uart_wrap_private_t *private;
    UART_TestStatusSnapshot_TypeDef driver_snapshot;
    et_wrap_status_t wrap_status;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    wrap_status = require_initialized(handle, &private);

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    /* Phase 1: Capture one target-local modem/status snapshot before translating any bits. */
    wrap_status = map_driver_status(UART_testGetStatusSnapshot(private->uart, &driver_snapshot));

    if (wrap_status != ET_WRAP_STATUS_OK)
    {
        return wrap_status;
    }

    memset(status, 0, sizeof(*status));
    status->struct_size = (uint16_t)sizeof(*status);
    status->api_version = ET_UART_WRAP_API_VERSION;

    /* Phase 2: Normalize modem input and delta observations through selected Chip Config masks. */
    if ((driver_snapshot.modemStatus & uart_status_masks.modem_cts) != 0u)
    {
        status->input_flags |= ET_UART_WRAP_MODEM_INPUT_CTS;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_dsr) != 0u)
    {
        status->input_flags |= ET_UART_WRAP_MODEM_INPUT_DSR;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_ri) != 0u)
    {
        status->input_flags |= ET_UART_WRAP_MODEM_INPUT_RI;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_dcd) != 0u)
    {
        status->input_flags |= ET_UART_WRAP_MODEM_INPUT_DCD;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_dcts) != 0u)
    {
        status->delta_flags |= ET_UART_WRAP_MODEM_INPUT_CTS;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_ddsr) != 0u)
    {
        status->delta_flags |= ET_UART_WRAP_MODEM_INPUT_DSR;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_teri) != 0u)
    {
        status->delta_flags |= ET_UART_WRAP_MODEM_INPUT_RI;
    }

    if ((driver_snapshot.modemStatus & uart_status_masks.modem_ddcd) != 0u)
    {
        status->delta_flags |= ET_UART_WRAP_MODEM_INPUT_DCD;
    }

    /* Phase 3: Normalize modem output state and retain raw modem status as evidence. */
    if ((driver_snapshot.modemControl & uart_status_masks.modem_rts) != 0u)
    {
        status->output_flags |= ET_UART_WRAP_MODEM_OUTPUT_RTS;
    }

    if ((driver_snapshot.modemControl & uart_status_masks.modem_dtr) != 0u)
    {
        status->output_flags |= ET_UART_WRAP_MODEM_OUTPUT_DTR;
    }

    status->raw_status = driver_snapshot.modemStatus;

    return ET_WRAP_STATUS_OK;
}
