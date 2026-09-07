/** @file et_can_wrap.c @brief Translate CAN primitives without register or cross-IP access. */
#include "et_can_wrap.h"

#include <stddef.h>
#include <limits.h>
#include <string.h>
#include "et6x_can.h"
#include "et_chip_wrap_config.h"

typedef struct
{
    et_can_id_t id;
    CAN_Type *instance;
    et_irq_line_t irq_lines[ET_CAN_IRQ_LINE_COUNT];
    et_irq_line_t ecc_irq;
    et_irq_line_t dmu_irq;
} et_can_mapping_t;

typedef struct
{
    uint32_t public_event;
    uint32_t driver_event;
} et_can_irq_mapping_t;

static const et_can_mapping_t mappings[] = ET_CHIP_CAN_MAP_TABLE;
static const et_can_irq_mapping_t irq_mappings[] = ET_CHIP_CAN_IRQ_MAP_TABLE;
static const et_can_timing_limits_t timing_limits = ET_CHIP_CAN_TIMING_LIMIT_MAP_TABLE;
static const et_can_option_limits_t option_limits = ET_CHIP_CAN_OPTION_LIMIT_MAP_TABLE;
static const CAN_TestDmuElement dmu_elements[] = ET_CHIP_CAN_DMU_ELEMENT_MAP_TABLE;
static const CAN_DMURxRequest dmu_requests[] = ET_CHIP_CAN_DMU_REQUEST_MAP_TABLE;
static const et_can_irq_mapping_t dmu_errors[] = ET_CHIP_CAN_DMU_ERROR_MAP_TABLE;

/**
 * @brief Resolve the requested logical controller from immutable chip facts.
 * @param[in] id Public CAN controller identity.
 * @return Driver instance, or NULL when the logical identity is not mapped.
 * @note Performs no MMIO and never falls back to another controller.
 */
static const et_can_mapping_t *find_mapping(et_can_id_t id)
{
    size_t index;

    for (index = 0u; index < sizeof(mappings) / sizeof(mappings[0]); ++index)
    {
        if (mappings[index].id == id)
        {
            return &mappings[index];
        }
    }

    return NULL;
}

/**
 * @brief Resolve only the selected controller instance.
 * @param[in] id Public logical controller identity.
 * @return Driver instance, or NULL when no exact mapping exists.
 * @note Route metadata stays private to find_mapping().
 */
static CAN_Type *find_instance(et_can_id_t id)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    return mapping == NULL ? NULL : mapping->instance;
}

/**
 * @brief Access exactly one word in a named test aperture.
 * @param[in] id Logical controller.
 * @param[in] element Named DMU element, never an arbitrary address.
 * @param[in] word_index Word offset bounded by the own Driver aperture.
 * @param[in] write Boolean direction; illegal hardware directions are intentional.
 * @param[in,out] value Written word or actual readback; reads may consume hardware state.
 * @return OK, invalid request or unsupported controller.
 * @note No retry, hidden sequence, reset or IRQ acknowledgement.
 */
et_wrap_status_t et_can_wrap_access_dmu_word(et_can_id_t id, et_can_dmu_element_t element,
                                             uint32_t word_index, uint8_t write, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL || (uint32_t)element >= ET_CAN_DMU_ELEMENT_COUNT || write > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testAccessDmuWord(instance, dmu_elements[element], word_index, write, value) ==
                   DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Resolve the DMU's independent semantic IRQ route.
 * @param[in] id Logical controller.
 * @param[in] sources Nonempty public error mask.
 * @param[out] route Immutable physical route facts.
 * @return OK, invalid mask or unsupported instance.
 * @note No IRQ Manager or register access.
 */
et_wrap_status_t et_can_wrap_get_dmu_route(et_can_id_t id, uint32_t sources, et_irq_route_t *route)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    if (route == NULL || sources == 0u || (sources & ~ET_CAN_DMU_ERROR_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    route->irq_line = mapping->dmu_irq;
    route->reserved = 0u;
    route->route_events = sources;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Change selected DMU error interrupt enables.
 * @param[in] id Logical controller.
 * @param[in] sources Public error mask.
 * @param[in] enabled Boolean enable state.
 * @return OK, invalid argument or unsupported instance.
 * @note Only the own Driver writes DMUIE; raw errors are not consumed.
 */
et_wrap_status_t et_can_wrap_set_dmu_irq(et_can_id_t id, uint32_t sources, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);
    uint32_t index, mask = 0u;

    if ((sources & ~ET_CAN_DMU_ERROR_ALL) != 0u || enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    for (index = 0u; index < sizeof(dmu_errors) / sizeof(dmu_errors[0]); ++index)
    {
        if ((sources & dmu_errors[index].public_event) != 0u)
        {
            mask |= dmu_errors[index].driver_event;
        }
    }

    return CAN_testSetDmuIrq(instance, mask, enabled) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read actual enabled DMU error sources without consuming raw errors.
 * @param[in] id Logical controller.
 * @param[out] sources Public error enables.
 * @return OK, invalid output or unsupported instance.
 * @note One own Driver read; success/debug bits have no public error meaning.
 */
et_wrap_status_t et_can_wrap_get_dmu_irq(et_can_id_t id, uint32_t *sources)
{
    CAN_Type *instance = find_instance(id);
    uint32_t index, actual;

    if (sources == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    actual = CAN_testGetDmuIrq(instance);
    *sources = 0u;

    for (index = 0u; index < sizeof(dmu_errors) / sizeof(dmu_errors[0]); ++index)
    {
        if ((actual & dmu_errors[index].driver_event) != 0u)
        {
            *sources |= dmu_errors[index].public_event;
        }
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one named DMA endpoint through the own CAN Driver.
 * @param[in] id Logical controller.
 * @param[in] element Public virtual element selector.
 * @param[out] address DMA endpoint address, not a CPU access request.
 * @return OK, invalid argument, unsupported instance or Driver error.
 * @note No virtual-window access, queue advance or external DMA configuration.
 */
et_wrap_status_t et_can_wrap_get_dmu_endpoint(et_can_id_t id, et_can_dmu_element_t element,
                                              uint32_t *address)
{
    CAN_Type *instance = find_instance(id);

    if (address == NULL || (uint32_t)element >= ET_CAN_DMU_ELEMENT_COUNT)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testGetDmuEndpoint(instance, dmu_elements[element], address) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Set only protected DMU timestamp transfer selection.
 * @param[in] id Logical controller.
 * @param[in] enabled Strict Boolean.
 * @return OK, invalid argument, missing INIT/UTSU or unsupported instance.
 * @note Does not change UTSU, TSU configuration or the caller's original CCE permission.
 */
et_wrap_status_t et_can_wrap_set_dmu_timestamp(et_can_id_t id, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testSetDmuTimestamp(instance, enabled) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Access one allocated filter's timestamp capture selection.
 * @param[in] id Logical controller.
 * @param[in] extended Strict filter-list selector.
 * @param[in] index Allocated filter index.
 * @param[in] write Strict direction selector.
 * @param[in,out] enabled Requested Boolean for write, actual Boolean for read.
 * @return OK, invalid selector, unsupported controller or Driver precondition failure.
 * @note Only the own Driver handles SYNC fields; filter IDs and actions are preserved.
 */
et_wrap_status_t et_can_wrap_access_filter_sync(et_can_id_t id, uint8_t extended, uint32_t index,
                                                uint8_t write, uint32_t *enabled)
{
    CAN_Type *instance = find_instance(id);

    if (extended > 1u || write > 1u || enabled == NULL || (write && *enabled > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testAccessFilterSync(instance, extended, index, write, enabled) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read explicit timestamp metadata from the current nonempty RX FIFO head.
 * @param[in] id Logical controller.
 * @param[in] fifo Public FIFO selector.
 * @param[out] metadata Timestamp format, captured pointer and actual FIFO index.
 * @return OK, invalid selector, empty FIFO or invalid hardware layout.
 * @note Caller must stop competing consumers; no Ack, virtual window or TSU slot read.
 */
et_wrap_status_t et_can_wrap_get_rx_timestamp(et_can_id_t id, uint32_t fifo,
                                              et_can_rx_timestamp_t *metadata)
{
    CAN_Type *instance = find_instance(id);
    et_can_rx_fifo_status_t head;
    CAN_TestRxTimestamp actual;
    et_wrap_status_t status;

    if (fifo > 1u || metadata == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status = et_can_wrap_get_rx_fifo_status(id, fifo, &head);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    if (head.fill == 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (CAN_testGetRxTimestamp(instance, fifo == 0u ? CAN_RX_FIFO_NUM_0 : CAN_RX_FIFO_NUM_1,
                               head.get_index, &actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    metadata->internal_valid = actual.internalValid;
    metadata->timestamp = actual.timestamp;
    metadata->captured = actual.captured;
    metadata->pointer = actual.pointer;
    metadata->index = head.get_index;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Select exactly one CAN receive-side DMA request source.
 * @param[in] id Logical controller.
 * @param[in] request Public RX0/RX1/TX Event selector.
 * @return OK, invalid argument, unsupported instance or Driver error.
 * @note Changes only the CAN-owned request mux; caller must quiesce DMA first.
 */
et_wrap_status_t et_can_wrap_set_dmu_request(et_can_id_t id, et_can_dmu_request_t request)
{
    CAN_Type *instance = find_instance(id);

    if ((uint32_t)request >= ET_CAN_DMU_REQUEST_COUNT)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testSetDmuRxRequest(instance, dmu_requests[request]) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read and translate the actual receive-side DMA request selection.
 * @param[in] id Logical controller.
 * @param[out] request Actual selection, unchanged on failure.
 * @return OK, invalid argument, unsupported instance or invalid hardware state.
 * @note Does not return a SET cache or alter the mux/DMA channel.
 */
et_wrap_status_t et_can_wrap_get_dmu_request(et_can_id_t id, et_can_dmu_request_t *request)
{
    CAN_Type *instance = find_instance(id);
    CAN_DMURxRequest actual;
    uint32_t index;

    if (request == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_testGetDmuRxRequest(instance, &actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    for (index = 0u; index < ET_CAN_DMU_REQUEST_COUNT; ++index)
    {
        if (dmu_requests[index] == actual)
        {
            *request = (et_can_dmu_request_t)index;

            return ET_WRAP_STATUS_OK;
        }
    }

    return ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read actual successful queue operation totals from one Driver snapshot.
 * @param[in] id Logical controller.
 * @param[out] counters Enqueue/dequeue totals and counter modulus.
 * @return OK, invalid argument, unsupported instance or Driver error.
 * @note The read may consume counters; no reset write, IRQ read or queue acknowledgement.
 */
et_wrap_status_t et_can_wrap_get_dmu_counters(et_can_id_t id, et_can_dmu_counters_t *counters)
{
    CAN_Type *instance = find_instance(id);
    CAN_TestDmuCounters actual;

    if (counters == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_testGetDmuCounters(instance, &actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    counters->tx_enqueued = actual.txEnqueued;
    counters->rx0_dequeued = actual.rx0Dequeued;
    counters->rx1_dequeued = actual.rx1Dequeued;
    counters->tx_event_dequeued = actual.txEventDequeued;
    counters->modulus = actual.modulus;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Capture DMU error flags once and translate only documented error sources.
 * @param[in] id Logical CAN controller.
 * @param[out] status Actual errors followed by enable and timestamp controls.
 * @return OK, invalid argument, unsupported instance or Driver error.
 * @note Reads may consume target flags; no retry, clear write or virtual-window access.
 */
et_wrap_status_t et_can_wrap_consume_dmu_status(et_can_id_t id, et_can_dmu_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_TestDmuStatus actual;
    size_t index;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_testConsumeDmuStatus(instance, &actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    status->errors = 0u;

    for (index = 0u; index < sizeof(dmu_errors) / sizeof(dmu_errors[0]); ++index)
    {
        if ((actual.flags & dmu_errors[index].driver_event) != 0u)
        {
            status->errors |= dmu_errors[index].public_event;
        }
    }

    status->enabled = actual.enabled;
    status->transfer_timestamp = actual.transferTimestamp;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve a logical ECC session to its private physical route.
 * @param[in] id Logical CAN controller.
 * @param[in] sources Nonempty public ECC source mask.
 * @param[out] route Binding facts for the Service and IRQ Manager.
 * @return OK, invalid argument or unsupported instance.
 * @note Only immutable mapping is read; no NVIC or peripheral state changes.
 */
et_wrap_status_t et_can_wrap_get_ecc_route(et_can_id_t id, uint32_t sources, et_irq_route_t *route)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    if (route == NULL || sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    route->irq_line = mapping->ecc_irq;
    route->reserved = 0u;
    route->route_events = sources;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate ECC events between public semantics and own Driver symbols.
 * @param[in] sources Mask in the source namespace.
 * @param[in] to_driver Nonzero selects public-to-Driver translation.
 * @return Equivalent mask in the destination namespace.
 * @note No register access; callers validate unknown public bits before translation.
 */
static uint32_t translate_ecc_sources(uint32_t sources, uint8_t to_driver)
{
    uint32_t corrected = to_driver != 0u ? ET_CAN_ECC_CORRECTED : CAN_TEST_ECC_CORRECTED;
    uint32_t uncorrected = to_driver != 0u ? ET_CAN_ECC_UNCORRECTED : CAN_TEST_ECC_UNCORRECTED;
    uint32_t result = 0u;

    if ((sources & corrected) != 0u)
    {
        result |= to_driver != 0u ? CAN_TEST_ECC_CORRECTED : ET_CAN_ECC_CORRECTED;
    }

    if ((sources & uncorrected) != 0u)
    {
        result |= to_driver != 0u ? CAN_TEST_ECC_UNCORRECTED : ET_CAN_ECC_UNCORRECTED;
    }

    return result;
}

/**
 * @brief Enable or disable selected ECC interrupt sources through the own Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] sources Nonempty public ECC event mask.
 * @param[in] enabled Boolean source enable.
 * @return OK, invalid argument, unsupported instance or Driver failure.
 * @note Does not change masking, consume raw events or enable global RAM ECC.
 */
et_wrap_status_t et_can_wrap_set_ecc_enabled(et_can_id_t id, uint32_t sources, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if (sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u || enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testSetEccEnabled(instance, translate_ecc_sources(sources, 1u), enabled) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Mask or unmask selected ECC interrupt sources through the own Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] sources Nonempty public ECC event mask.
 * @param[in] masked Boolean interrupt masking.
 * @return OK, invalid argument, unsupported instance or Driver failure.
 * @note Masking preserves raw latches and does not bind or control a physical IRQ.
 */
et_wrap_status_t et_can_wrap_set_ecc_masked(et_can_id_t id, uint32_t sources, uint8_t masked)
{
    CAN_Type *instance = find_instance(id);

    if (sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u || masked > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testSetEccMasked(instance, translate_ecc_sources(sources, 1u), masked) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Force selected ECC interrupt latches through the own Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] sources Nonempty public ECC event mask.
 * @return OK, invalid argument, unsupported instance or Driver failure.
 * @note Can trigger an enabled IRQ; does not inject a real RAM bit error.
 */
et_wrap_status_t et_can_wrap_force_ecc(et_can_id_t id, uint32_t sources)
{
    CAN_Type *instance = find_instance(id);

    if (sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testForceEcc(instance, translate_ecc_sources(sources, 1u)) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Clear selected ECC interrupt latches through the own Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] sources Nonempty public ECC event mask.
 * @return OK, invalid argument, unsupported instance or Driver failure.
 * @note Preserves non-target raw sources and does not modify session evidence.
 */
et_wrap_status_t et_can_wrap_clear_ecc(et_can_id_t id, uint32_t sources)
{
    CAN_Type *instance = find_instance(id);

    if (sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testClearEcc(instance, translate_ecc_sources(sources, 1u)) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read current ECC raw, delivery status, enable and mask values.
 * @param[in] id Logical CAN controller.
 * @param[out] snapshot Actual values in the public ECC namespace.
 * @return OK, invalid argument, unsupported instance or Driver failure.
 * @note Independent non-consuming register observations, not an atomic ISR snapshot.
 */
et_wrap_status_t et_can_wrap_get_ecc_snapshot(et_can_id_t id, et_can_ecc_snapshot_t *snapshot)
{
    CAN_Type *instance = find_instance(id);
    CAN_TestEccSnapshot actual;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_testGetEccSnapshot(instance, &actual) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    snapshot->raw = translate_ecc_sources(actual.raw, 0u);
    snapshot->status = translate_ecc_sources(actual.status, 0u);
    snapshot->enabled = translate_ecc_sources(actual.enabled, 0u);
    snapshot->masked = translate_ecc_sources(actual.masked, 0u);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate an event mask between public and Driver namespaces.
 * @param[in] mask Source namespace mask.
 * @param[in] to_driver Nonzero maps public events to Driver events.
 * @return Mask in the requested destination namespace.
 * @note Unknown bits are ignored only after callers have validated the public mask.
 */
static uint32_t translate_irq_events(uint32_t mask, uint8_t to_driver)
{
    uint32_t result = 0u;
    size_t index;

    for (index = 0u; index < sizeof(irq_mappings) / sizeof(irq_mappings[0]); ++index)
    {
        uint32_t source =
            to_driver != 0u ? irq_mappings[index].public_event : irq_mappings[index].driver_event;
        uint32_t target =
            to_driver != 0u ? irq_mappings[index].driver_event : irq_mappings[index].public_event;

        if ((mask & source) != 0u)
        {
            result |= target;
        }
    }

    return result;
}

/**
 * @brief Read controller revision and endian identities through the CAN Driver.
 * @param[in] id Logical controller identity.
 * @param[out] identity Actual hardware identities, not cached configuration.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note Does not reset hardware, consume receive data or clear protocol errors.
 */
et_wrap_status_t et_can_wrap_get_identity(et_can_id_t id, et_can_identity_t *identity)
{
    CAN_Type *instance = find_instance(id);

    if (identity == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    identity->revision = CAN_testGetRevision(instance);
    identity->endian = CAN_getEndianVal(instance);

    return ET_WRAP_STATUS_OK;
}

static const uint32_t timestamp_sources[] = ET_CHIP_CAN_TIMESTAMP_MAP_TABLE;
static const uint32_t timeout_sources[] = ET_CHIP_CAN_TIMEOUT_MAP_TABLE;
static const uint32_t unmatched_policies[] = ET_CHIP_CAN_UNMATCHED_MAP_TABLE;
static const et_can_bus_limits_t bus_limits = ET_CHIP_CAN_BUS_LIMIT_MAP_TABLE;

/**
 * @brief Decode one private Driver selector through its public-order map.
 * @param[in] values Chip mapping entries in public enum order.
 * @param[in] count Mapping length.
 * @param[in] value Actual Driver value.
 * @param[out] result Public enum value on success.
 * @return One for a mapped value, zero otherwise.
 * @note Does not replace unknown hardware values with defaults.
 */
static int selector_from_driver(const uint32_t *values, size_t count, uint32_t value,
                                uint32_t *result)
{
    size_t index;

    for (index = 0u; index < count; ++index)
    {
        if (values[index] == value)
        {
            *result = (uint32_t)index;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Set operating, global acceptance and timer parameters through the existing Driver.
 * @param[in] id Logical controller.
 * @param[in] config Explicit public controls; timestamp divisor is an actual count.
 * @return OK or an argument, state, unsupported-instance or Driver error.
 * @note INIT is required; no loopback, RAM layout or bit-timing changes are hidden here.
 */
et_wrap_status_t et_can_wrap_set_bus_config(et_can_id_t id, const et_can_bus_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_ConfigParams driver;

    /* Phase 1: Reject every unsupported selector and count before any Driver write. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((config == NULL) || (config->monitor > 1u) || (config->restricted > 1u) ||
        (config->timeout_enabled > 1u) || (config->reject_remote_ext > 1u) ||
        (config->reject_remote_std > 1u) || (config->timestamp_divisor == 0u) ||
        (config->timestamp_divisor > bus_limits.timestamp_divisor) ||
        (config->timeout_period > bus_limits.timeout_period) ||
        (config->timestamp_source >= ET_CAN_TIMESTAMP_SOURCE_COUNT) ||
        (config->timeout_source >= ET_CAN_TIMEOUT_SOURCE_COUNT) ||
        (config->unmatched_ext >= ET_CAN_UNMATCHED_POLICY_COUNT) ||
        (config->unmatched_std >= ET_CAN_UNMATCHED_POLICY_COUNT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Translate only this Driver group, preserving independent configuration. */
    driver.monEnable = config->monitor;
    driver.asmEnable = config->restricted;
    driver.tsPrescalar = config->timestamp_divisor;
    driver.tsSelect = timestamp_sources[config->timestamp_source];
    driver.timeoutSelect = timeout_sources[config->timeout_source];
    driver.timeoutPreload = config->timeout_period;
    driver.timeoutCntEnable = config->timeout_enabled;
    driver.filterConfig.rrfe = config->reject_remote_ext;
    driver.filterConfig.rrfs = config->reject_remote_std;
    driver.filterConfig.anfe = unmatched_policies[config->unmatched_ext];
    driver.filterConfig.anfs = unmatched_policies[config->unmatched_std];

    return CAN_config(instance, &driver) == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read back current bus configuration without reading error counters.
 * @param[in] id Logical controller.
 * @param[out] config Actual decoded configuration.
 * @return OK, invalid argument, unsupported instance or unknown Driver selector.
 * @note No request cache, FIFO acknowledgement, reset or mode changes are used.
 */
et_wrap_status_t et_can_wrap_get_bus_config(et_can_id_t id, et_can_bus_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_ConfigParams driver;

    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetConfig(instance, &driver);
    config->monitor = driver.monEnable;
    config->restricted = driver.asmEnable;
    config->timestamp_divisor = driver.tsPrescalar;

    if (!selector_from_driver(timestamp_sources,
                              sizeof(timestamp_sources) / sizeof(timestamp_sources[0]),
                              driver.tsSelect, &config->timestamp_source))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!selector_from_driver(timeout_sources, sizeof(timeout_sources) / sizeof(timeout_sources[0]),
                              driver.timeoutSelect, &config->timeout_source))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    config->timeout_period = driver.timeoutPreload;
    config->timeout_enabled = driver.timeoutCntEnable;
    config->reject_remote_ext = driver.filterConfig.rrfe;
    config->reject_remote_std = driver.filterConfig.rrfs;

    if (!selector_from_driver(unmatched_policies,
                              sizeof(unmatched_policies) / sizeof(unmatched_policies[0]),
                              driver.filterConfig.anfe, &config->unmatched_ext))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!selector_from_driver(unmatched_policies,
                              sizeof(unmatched_policies) / sizeof(unmatched_policies[0]),
                              driver.filterConfig.anfs, &config->unmatched_std))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish actual timer count limits for the selected controller.
 * @param[in] id Logical controller.
 * @param[out] limits Actual timestamp divisor and timeout reload maxima.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Read-only chip facts; no bus configuration or timer start.
 */
et_wrap_status_t et_can_wrap_get_bus_limits(et_can_id_t id, et_can_bus_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = bus_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Select disabled, internal or external loopback while already in INIT.
 * @param[in] id Logical controller.
 * @param[in] mode Stable public mode; internal uses MON to isolate external traffic.
 * @return OK, invalid mode, unsupported instance or unmet INIT precondition.
 * @note Exiting internal loopback also clears MON; does not start the controller.
 */
et_wrap_status_t et_can_wrap_set_loopback(et_can_id_t id, et_can_loopback_t mode)
{
    CAN_Type *instance = find_instance(id);

    if ((mode != ET_CAN_LOOPBACK_DISABLED) && (mode != ET_CAN_LOOPBACK_INTERNAL) &&
        (mode != ET_CAN_LOOPBACK_EXTERNAL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    CAN_enbaleLpbkMode(instance,
                       mode == ET_CAN_LOOPBACK_EXTERNAL ? CAN_LPBK_MODE_EXTERNAL
                                                        : CAN_LPBK_MODE_INTERNAL,
                       mode != ET_CAN_LOOPBACK_DISABLED);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Query effective loopback state independently from any prior mode request.
 * @param[in] id Logical controller.
 * @param[out] mode Actual disabled, internal or external state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Reads through the CAN Driver; does not require INIT or change MON.
 */
et_wrap_status_t et_can_wrap_get_loopback(et_can_id_t id, et_can_loopback_t *mode)
{
    CAN_Type *instance = find_instance(id);
    CAN_LpbkMode driver_mode;
    uint32_t enabled;

    if (mode == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetLoopback(instance, &enabled, &driver_mode);
    *mode = enabled == 0u                           ? ET_CAN_LOOPBACK_DISABLED
            : driver_mode == CAN_LPBK_MODE_INTERNAL ? ET_CAN_LOOPBACK_INTERNAL
                                                    : ET_CAN_LOOPBACK_EXTERNAL;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Request initialization or bus operation without polling for acknowledgement.
 * @param[in] id Logical controller identity.
 * @param[in] initializing Boolean request to stop bus operation for configuration.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note Changes the CAN initialization request only; PC owns the bounded state wait.
 */
et_wrap_status_t et_can_wrap_set_initializing(et_can_id_t id, uint8_t initializing)
{
    CAN_Type *instance = find_instance(id);

    if (initializing > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_setOpMode(instance,
                  initializing != 0u ? CAN_OPERATION_MODE_SW_INIT : CAN_OPERATION_MODE_NORMAL);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Sample the actual controller initialization state once.
 * @param[in] id Logical controller identity.
 * @param[out] initializing One when hardware reports initialization mode.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note No wait, clock configuration or reset is hidden in this query.
 */
et_wrap_status_t et_can_wrap_get_initializing(et_can_id_t id, uint8_t *initializing)
{
    CAN_Type *instance = find_instance(id);

    if (initializing == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *initializing = (CAN_getOpMode(instance) == CAN_OPERATION_MODE_SW_INIT) ? 1u : 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish the selected chip's representable timing counts.
 * @param[in] id Logical controller identity.
 * @param[out] limits Inclusive maxima; every minimum count is one.
 * @return OK, NOT_SUPPORTED for an unmapped instance, or INVALID_ARGUMENT.
 * @note These are encoding limits, not a guarantee of a physical bus bitrate.
 */
et_wrap_status_t et_can_wrap_get_timing_limits(et_can_id_t id, et_can_timing_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = timing_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Check positive physical timing counts before any Driver mutation.
 * @param[in] timing Requested phase timing.
 * @param[in] maximum Corresponding inclusive chip encoding limits.
 * @return One for representable timing with SJW no greater than either segment.
 * @note This is argument validation, not bitrate selection or a test assertion.
 */
static uint8_t timing_is_valid(const et_can_bit_timing_t *timing,
                               const et_can_bit_timing_t *maximum)
{
    return (timing->prescaler > 0u) && (timing->prescaler <= maximum->prescaler) &&
           (timing->segment1 > 0u) && (timing->segment1 <= maximum->segment1) &&
           (timing->segment2 > 0u) && (timing->segment2 <= maximum->segment2) &&
           (timing->sjw > 0u) && (timing->sjw <= maximum->sjw) &&
           (timing->sjw <= timing->segment1) && (timing->sjw <= timing->segment2);
}

/**
 * @brief Configure arbitration and data timing using actual counts.
 * @param[in] id Logical controller identity.
 * @param[in] timing Complete positive timing counts for both phases.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED, STATE_ERROR or IO_ERROR.
 * @note Requires initialization mode; it never stops an active bus implicitly.
 */
et_wrap_status_t et_can_wrap_set_timing(et_can_id_t id, const et_can_timing_t *timing)
{
    CAN_Type *instance = find_instance(id);
    CAN_BitTimingParams encoded;

    if ((timing == NULL) || (timing_is_valid(&timing->nominal, &timing_limits.nominal_max) == 0u) ||
        (timing_is_valid(&timing->data, &timing_limits.data_max) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* The SDK timing structure uses register encodings; the public API never does. */
    encoded.nomRatePrescalar = timing->nominal.prescaler - 1u;
    encoded.nomTimeSeg1 = timing->nominal.segment1 - 1u;
    encoded.nomTimeSeg2 = timing->nominal.segment2 - 1u;
    encoded.nomSynchJumpWidth = timing->nominal.sjw - 1u;
    encoded.dataRatePrescalar = timing->data.prescaler - 1u;
    encoded.dataTimeSeg1 = timing->data.segment1 - 1u;
    encoded.dataTimeSeg2 = timing->data.segment2 - 1u;
    encoded.dataSynchJumpWidth = timing->data.sjw - 1u;

    return CAN_setBitTime(instance, &encoded) == DRV_OK ? ET_WRAP_STATUS_OK
                                                        : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read or set hardware configuration-write permission.
 * @param[in] id Logical controller.
 * @param[in] enabled Write request, ignored on a read.
 * @param[out] actual Non-NULL selects read, NULL selects write.
 * @return OK or argument/instance/state failure.
 * @note Does not enter INIT or configure timing implicitly.
 */
et_wrap_status_t et_can_wrap_configuration_access(et_can_id_t id, uint8_t enabled, uint8_t *actual)
{
    CAN_Type *instance = find_instance(id);
    uint32_t value;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_testConfigurationAccess(instance, enabled, actual == NULL ? NULL : &value) != DRV_OK)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (actual != NULL)
    {
        *actual = (uint8_t)value;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Select or read the CAN FD encoding format through the own Driver.
 * @param[in] id Logical controller identity.
 * @param[in] enabled Boolean Non-ISO selection, ignored for reads.
 * @param[out] actual Non-NULL selects read, NULL selects write.
 * @return OK or argument, instance or state failure.
 * @note Writes require INIT and do not send frames or change other CAN options.
 */
et_wrap_status_t et_can_wrap_non_iso_access(et_can_id_t id, uint8_t enabled, uint8_t *actual)
{
    CAN_Type *instance = find_instance(id);
    uint32_t value;

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_testNonIsoAccess(instance, enabled, actual == NULL ? NULL : &value) != DRV_OK)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (actual != NULL)
    {
        *actual = (uint8_t)value;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Attempt a nominal timing write while preserving the permission gate.
 * @param[in] id Logical controller.
 * @param[in] timing Four positive physical timing counts.
 * @return OK if issued, or argument/instance/state failure.
 * @note OK is not proof of acceptance; PC must independently read hardware timing.
 */
et_wrap_status_t et_can_wrap_write_nominal_timing(et_can_id_t id, const et_can_bit_timing_t *timing)
{
    CAN_Type *instance = find_instance(id);
    CAN_BitTimingParams encoded = {0};

    if ((timing == NULL) || (timing_is_valid(timing, &timing_limits.nominal_max) == 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    encoded.nomRatePrescalar = timing->prescaler - 1u;
    encoded.nomTimeSeg1 = timing->segment1 - 1u;
    encoded.nomTimeSeg2 = timing->segment2 - 1u;
    encoded.nomSynchJumpWidth = timing->sjw - 1u;

    return CAN_testWriteNominalTiming(instance, &encoded) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                    : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read back both timing phases and convert to actual positive counts.
 * @param[in] id Logical controller identity.
 * @param[out] timing Actual configured timing, independent of the request object.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Reads timing configuration only; protocol status and FIFO state are untouched.
 */
et_wrap_status_t et_can_wrap_get_timing(et_can_id_t id, et_can_timing_t *timing)
{
    CAN_Type *instance = find_instance(id);
    CAN_BitTimingParams encoded;

    if (timing == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getBitTime(instance, &encoded);
    timing->nominal.prescaler = encoded.nomRatePrescalar + 1u;
    timing->nominal.segment1 = encoded.nomTimeSeg1 + 1u;
    timing->nominal.segment2 = encoded.nomTimeSeg2 + 1u;
    timing->nominal.sjw = encoded.nomSynchJumpWidth + 1u;
    timing->data.prescaler = encoded.dataRatePrescalar + 1u;
    timing->data.segment1 = encoded.dataTimeSeg1 + 1u;
    timing->data.segment2 = encoded.dataTimeSeg2 + 1u;
    timing->data.sjw = encoded.dataSynchJumpWidth + 1u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Publish the representable TDC and RAM watchdog cycle limits.
 * @param[in] id Logical CAN identity.
 * @param[out] limits Inclusive maxima in controller cycles.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note These hardware limits are not default test configuration or execution budgets.
 */
et_wrap_status_t et_can_wrap_get_option_limits(et_can_id_t id, et_can_option_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = option_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure independent CAN core options using the existing CAN initializer.
 * @param[in] id Logical CAN identity.
 * @param[in] options Complete options supplied by the caller.
 * @return OK or an explicit parameter, state, unsupported or Driver execution error.
 * @note Requires INIT; preserves bit timing, filters and Message RAM layout.
 */
et_wrap_status_t et_can_wrap_set_options(et_can_id_t id, const et_can_options_t *options)
{
    CAN_Type *instance = find_instance(id);
    CAN_InitParams config;

    /* Phase 1: Validate all fields before the SDK can change protected registers. */
    if ((options == NULL) || (options->fd_enabled > 1u) || (options->brs_enabled > 1u) ||
        (options->automatic_retry > 1u) || (options->tx_pause > 1u) ||
        (options->edge_filter > 1u) || (options->protocol_exception > 1u) ||
        (options->tdc_enabled > 1u) ||
        (options->tdc_offset_cycles > option_limits.tdc_offset_cycles) ||
        (options->tdc_filter_cycles > option_limits.tdc_filter_cycles) ||
        (options->ram_watchdog_cycles > option_limits.ram_watchdog_cycles))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Translate positive public semantics to the SDK's disable controls. */
    config.fdMode = options->fd_enabled;
    config.brsEnable = options->brs_enabled;
    config.darEnable = options->automatic_retry == 0u;
    config.txpEnable = options->tx_pause;
    config.efbi = options->edge_filter;
    config.pxhddisable = options->protocol_exception == 0u;
    config.tdcEnable = options->tdc_enabled;
    config.tdcConfig.tdco = options->tdc_offset_cycles;
    config.tdcConfig.tdcf = options->tdc_filter_cycles;
    config.wdcPreload = options->ram_watchdog_cycles;

    return CAN_init(instance, &config) == DRV_OK ? ET_WRAP_STATUS_OK : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read back CAN core options independently of any previous request.
 * @param[in] id Logical CAN identity.
 * @param[out] options Actual core controls and cycle values.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not consume LEC, IRQ sources, FIFO entries or transmit events.
 */
et_wrap_status_t et_can_wrap_get_options(et_can_id_t id, et_can_options_t *options)
{
    CAN_Type *instance = find_instance(id);
    CAN_InitParams config;

    if (options == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetInitConfig(instance, &config);
    options->fd_enabled = config.fdMode;
    options->brs_enabled = config.brsEnable;
    options->automatic_retry = config.darEnable == 0u;
    options->tx_pause = config.txpEnable;
    options->edge_filter = config.efbi;
    options->protocol_exception = config.pxhddisable == 0u;
    options->tdc_enabled = config.tdcEnable;
    options->tdc_offset_cycles = config.tdcConfig.tdco;
    options->tdc_filter_cycles = config.tdcConfig.tdcf;
    options->ram_watchdog_cycles = config.wdcPreload;

    return ET_WRAP_STATUS_OK;
}

/** One allowed payload byte capacity and its private SDK encoding. */
typedef struct
{
    uint32_t bytes;
    uint32_t driver_value;
} et_can_payload_mapping_t;

static const et_can_payload_mapping_t payload_mappings[] = ET_CHIP_CAN_PAYLOAD_MAP_TABLE;
static const et_can_ram_limits_t ram_limits = ET_CHIP_CAN_RAM_LIMIT_MAP_TABLE;

/** A half-open occupied interval inside CAN Message RAM, expressed only in bytes. */
typedef struct
{
    uint32_t offset;
    uint32_t length;
} et_can_ram_region_t;

/**
 * @brief Translate a public payload capacity to the existing SDK element encoding.
 * @param[in] bytes Payload capacity in bytes, without the message header.
 * @param[out] value SDK encoding on success.
 * @return One when supported, zero without modifying hardware otherwise.
 * @note Does not choose a fallback payload capacity.
 */
static int payload_to_driver(uint32_t bytes, uint32_t *value)
{
    size_t index;

    for (index = 0u; index < sizeof(payload_mappings) / sizeof(payload_mappings[0]); ++index)
    {
        if (payload_mappings[index].bytes == bytes)
        {
            *value = payload_mappings[index].driver_value;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Decode a real SDK element encoding to the public byte capacity.
 * @param[in] value Actual hardware encoding from the CAN Driver.
 * @param[out] bytes Public capacity on success.
 * @return One when mapped, zero for an unknown encoding.
 * @note No cached configuration is used.
 */
static int payload_from_driver(uint32_t value, uint32_t *bytes)
{
    size_t index;

    for (index = 0u; index < sizeof(payload_mappings) / sizeof(payload_mappings[0]); ++index)
    {
        if (payload_mappings[index].driver_value == value)
        {
            *bytes = payload_mappings[index].bytes;

            return 1;
        }
    }

    return 0;
}

/**
 * @brief Validate occupied regions before any configuration reaches hardware.
 * @param[in] regions Complete list of requested byte intervals.
 * @param[in] count Number of intervals in the local array.
 * @return One for aligned, bounded, non-overlapping regions; zero otherwise.
 * @note Empty regions do not reserve memory; offsets still require legal alignment.
 */
static int ram_regions_valid(const et_can_ram_region_t *regions, size_t count)
{
    size_t index;
    size_t other;

    for (index = 0u; index < count; ++index)
    {
        if ((regions[index].offset % sizeof(uint32_t) != 0u) ||
            (regions[index].offset >= ram_limits.ram_bytes) ||
            (regions[index].length > ram_limits.ram_bytes - regions[index].offset))
        {
            return 0;
        }

        for (other = 0u; other < index; ++other)
        {
            if ((regions[index].length != 0u) && (regions[other].length != 0u) &&
                (regions[index].offset < regions[other].offset + regions[other].length) &&
                (regions[other].offset < regions[index].offset + regions[index].length))
            {
                return 0;
            }
        }
    }

    return 1;
}

/**
 * @brief Publish hardware region limits without selecting a test layout.
 * @param[in] id Logical CAN controller.
 * @param[out] limits Architectural counts and byte aperture.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No reset or Message RAM access is performed.
 */
et_wrap_status_t et_can_wrap_get_ram_limits(et_can_id_t id, et_can_ram_limits_t *limits)
{
    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (find_instance(id) == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *limits = ram_limits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Access only the selected controller's Message RAM through its test Driver.
 * @param[in] id Logical controller identity.
 * @param[in] offset Aligned byte offset within the published aperture.
 * @param[in] count Nonzero word count bounded by the Wire batch limit.
 * @param[in] input Optional ascending-offset words to write.
 * @param[out] output Optional words sampled before their corresponding writes.
 * @param[in] descending Boolean traversal direction; array indexing remains ascending.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED, STATE_ERROR or IO_ERROR.
 * @note No comparison, pattern generation or test orchestration is performed.
 */
et_wrap_status_t et_can_wrap_access_ram(et_can_id_t id, uint32_t offset, uint32_t count,
                                        const uint32_t *input, uint32_t *output, uint8_t descending)
{
    CAN_Type *instance = find_instance(id);

    if ((count == 0u) || (count > ET_CAN_RAM_ACCESS_WORDS) || (descending > 1u) ||
        ((input == NULL) && (output == NULL)) || (offset % sizeof(uint32_t) != 0u) ||
        (offset >= ram_limits.ram_bytes) ||
        (count > (ram_limits.ram_bytes - offset) / sizeof(uint32_t)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    return CAN_testAccessRAMWords(instance, offset, count, input, output, descending) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Configure one complete RAM layout through the CAN Driver only.
 * @param[in] id Logical controller.
 * @param[in] layout Explicit byte offsets, counts, capacities and FIFO policies.
 * @return OK, INVALID_ARGUMENT, STATE_ERROR, NOT_SUPPORTED or IO_ERROR.
 * @note INIT is required. Validation precedes all writes; no RAM contents are initialized.
 */
et_wrap_status_t et_can_wrap_set_ram_layout(et_can_id_t id, const et_can_ram_layout_t *layout)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    /* Phase 1: Check instance, architectural counts and payload encodings without writes. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((layout == NULL) || (layout->std_count > ram_limits.std_count) ||
        (layout->ext_count > ram_limits.ext_count) ||
        (layout->tx_buffer_count > ram_limits.tx_count) ||
        (layout->tx_fifo_count > ram_limits.tx_count) ||
        (layout->tx_buffer_count + layout->tx_fifo_count > ram_limits.tx_count) ||
        (layout->rx0_count > ram_limits.rx_fifo_count) ||
        (layout->rx1_count > ram_limits.rx_fifo_count) ||
        (layout->event_count > ram_limits.event_count) ||
        (layout->rx0_watermark > layout->rx0_count) ||
        (layout->rx1_watermark > layout->rx1_count) ||
        (layout->event_watermark > layout->event_count) || (layout->tx_queue > 1u) ||
        (layout->rx0_overwrite > 1u) || (layout->rx1_overwrite > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (!payload_to_driver(layout->tx_payload_bytes, &config.txBufElemSize) ||
        !payload_to_driver(layout->rx0_payload_bytes, &config.rxFIFO0ElemSize) ||
        !payload_to_driver(layout->rx1_payload_bytes, &config.rxFIFO1ElemSize) ||
        !payload_to_driver(layout->rx_buffer_payload_bytes, &config.rxBufElemSize))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 2: Check actual occupied byte spans; register widths are not memory bounds. */
    {
        const et_can_ram_region_t regions[] = {
            {layout->std_offset,
             layout->std_count * CAN_STD_ID_FILTER_SIZE_WORDS * sizeof(uint32_t)},
            {layout->ext_offset,
             layout->ext_count * CAN_EXT_ID_FILTER_SIZE_WORDS * sizeof(uint32_t)},
            {layout->tx_offset, (layout->tx_buffer_count + layout->tx_fifo_count) *
                                    CAN_getMsgObjSize(config.txBufElemSize) * sizeof(uint32_t)},
            {layout->event_offset,
             layout->event_count * CAN_TX_EVENT_FIFO_SIZE_WORDS * sizeof(uint32_t)},
            {layout->rx0_offset,
             layout->rx0_count * CAN_getMsgObjSize(config.rxFIFO0ElemSize) * sizeof(uint32_t)},
            {layout->rx1_offset,
             layout->rx1_count * CAN_getMsgObjSize(config.rxFIFO1ElemSize) * sizeof(uint32_t)},
            {layout->rx_buffer_offset, ram_limits.rx_buffer_count *
                                           CAN_getMsgObjSize(config.rxBufElemSize) *
                                           sizeof(uint32_t)}};

        if (!ram_regions_valid(regions, sizeof(regions) / sizeof(regions[0])))
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 3: Translate a fully validated layout and execute one own-Driver operation. */
    config.flssa = layout->std_offset;
    config.lss = layout->std_count;
    config.flesa = layout->ext_offset;
    config.lse = layout->ext_count;
    config.txStartAddr = layout->tx_offset;
    config.txBufNum = layout->tx_buffer_count;
    config.txFIFOSize = layout->tx_fifo_count;
    config.txBufMode = layout->tx_queue ? CAN_TX_QUEUE_OPERATION : CAN_TX_FIFO_OPERATION;
    config.txEventFIFOStartAddr = layout->event_offset;
    config.txEventFIFOSize = layout->event_count;
    config.txEventFIFOWaterMark = layout->event_watermark;
    config.rxFIFO0startAddr = layout->rx0_offset;
    config.rxFIFO0size = layout->rx0_count;
    config.rxFIFO0waterMark = layout->rx0_watermark;
    config.rxFIFO0OpMode = layout->rx0_overwrite ? CAN_RX_FIFO_OVERWRITE : CAN_RX_FIFO_BLOCKING;
    config.rxFIFO1startAddr = layout->rx1_offset;
    config.rxFIFO1size = layout->rx1_count;
    config.rxFIFO1waterMark = layout->rx1_watermark;
    config.rxFIFO1OpMode = layout->rx1_overwrite ? CAN_RX_FIFO_OVERWRITE : CAN_RX_FIFO_BLOCKING;
    config.rxBufStartAddr = layout->rx_buffer_offset;

    return CAN_msgRAMConfig(instance, &config) == DRV_OK ? ET_WRAP_STATUS_OK
                                                         : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read every RAM configuration field independently from hardware.
 * @param[in] id Logical controller.
 * @param[out] layout Actual offsets, counts, capacities and FIFO policies.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR for unknown size encoding.
 * @note Does not read or acknowledge queued messages and does not rely on Service state.
 */
et_wrap_status_t et_can_wrap_get_ram_layout(et_can_id_t id, et_can_ram_layout_t *layout)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    if (layout == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    layout->std_offset = config.flssa;
    layout->std_count = config.lss;
    layout->ext_offset = config.flesa;
    layout->ext_count = config.lse;
    layout->tx_offset = config.txStartAddr;
    layout->tx_buffer_count = config.txBufNum;
    layout->tx_fifo_count = config.txFIFOSize;
    layout->tx_queue = config.txBufMode;

    if (!payload_from_driver(config.txBufElemSize, &layout->tx_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    layout->event_offset = config.txEventFIFOStartAddr;
    layout->event_count = config.txEventFIFOSize;
    layout->event_watermark = config.txEventFIFOWaterMark;
    layout->rx0_offset = config.rxFIFO0startAddr;
    layout->rx0_count = config.rxFIFO0size;
    layout->rx0_watermark = config.rxFIFO0waterMark;
    layout->rx0_overwrite = config.rxFIFO0OpMode;
    layout->rx1_offset = config.rxFIFO1startAddr;
    layout->rx1_count = config.rxFIFO1size;
    layout->rx1_watermark = config.rxFIFO1waterMark;
    layout->rx1_overwrite = config.rxFIFO1OpMode;
    layout->rx_buffer_offset = config.rxBufStartAddr;

    if (!payload_from_driver(config.rxBufElemSize, &layout->rx_buffer_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!payload_from_driver(config.rxFIFO0ElemSize, &layout->rx0_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (!payload_from_driver(config.rxFIFO1ElemSize, &layout->rx1_payload_bytes))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    return ET_WRAP_STATUS_OK;
}

static const uint32_t rx_fifo_numbers[] = ET_CHIP_CAN_RX_FIFO_MAP_TABLE;

/** Private SDK message packing facts; public frames never contain shifted identifiers. */
typedef struct
{
    uint32_t standard_id_shift;
    uint32_t standard_id_max;
    uint32_t extended_id_max;
    uint32_t basic_marker_max;
} et_can_frame_mapping_t;

static const et_can_frame_mapping_t frame_mapping = ET_CHIP_CAN_FRAME_MAP_TABLE;

/**
 * @brief Validate protocol fields before converting to the existing SDK TX element.
 * @param[in] frame Public unshifted frame and explicit control flags.
 * @param[in] marker_bits Effective hardware marker width.
 * @param[out] element Driver-format header and payload on success.
 * @return One for a supported basic element; zero without hardware access otherwise.
 * @note Wide-marker mode is not implied by an oversized basic marker.
 */
static int encode_tx_element(const et_can_tx_frame_t *frame, uint32_t marker_bits,
                             CAN_TxBufElement *element)
{
    const uint32_t allowed_flags = ET_CAN_FRAME_EXTENDED | ET_CAN_FRAME_REMOTE | ET_CAN_FRAME_FD |
                                   ET_CAN_FRAME_BRS | ET_CAN_FRAME_ESI | ET_CAN_FRAME_STORE_EVENT |
                                   ET_CAN_FRAME_CAPTURE_TIME;
    size_t index;

    if ((frame == NULL) || (frame->flags & ~allowed_flags) || (frame->dlc > ET_CAN_FRAME_DLC_MAX) ||
        (frame->marker >
         (marker_bits == CAN_TEST_MARKER_BITS_WIDE ? UINT16_MAX : frame_mapping.basic_marker_max)))
    {
        return 0;
    }

    (void)memset(element, 0, sizeof(*element));
    element->xtd = (frame->flags & ET_CAN_FRAME_EXTENDED) != 0u;
    element->rtr = (frame->flags & ET_CAN_FRAME_REMOTE) != 0u;
    element->fdf = (frame->flags & ET_CAN_FRAME_FD) != 0u;
    element->brs = (frame->flags & ET_CAN_FRAME_BRS) != 0u;
    element->esi = (frame->flags & ET_CAN_FRAME_ESI) != 0u;

    if ((frame->identifier >
         (element->xtd ? frame_mapping.extended_id_max : frame_mapping.standard_id_max)) ||
        (element->fdf && element->rtr) || (!element->fdf && (element->brs || element->esi)))
    {
        return 0;
    }

    element->id =
        element->xtd ? frame->identifier : frame->identifier << frame_mapping.standard_id_shift;
    element->dlc = frame->dlc;
    element->mm = frame->marker;
    element->efc = (frame->flags & ET_CAN_FRAME_STORE_EVENT) != 0u;
    element->tx_tsce = (frame->flags & ET_CAN_FRAME_CAPTURE_TIME) != 0u;

    for (index = 0u; index < ET_CAN_FRAME_DATA_BYTES; ++index)
    {
        element->data[index] = frame->data[index];
    }

    return 1;
}

/**
 * @brief Encode one public frame into a bounded CPU-owned DMA image.
 * @param[in] id Logical controller whose actual element format is used.
 * @param[in] frame Explicit frame and payload.
 * @param[out] image Encoded bytes and actual length; unused envelope is zero.
 * @return OK, invalid argument, unsupported instance or Driver error.
 * @note No Message RAM, DMU window, DMA controller or transmit request is accessed.
 */
et_wrap_status_t et_can_wrap_encode_dmu_tx(et_can_id_t id, const et_can_tx_frame_t *frame,
                                           et_can_dmu_image_t *image)
{
    CAN_Type *instance = find_instance(id);
    CAN_TxBufElement element;
    uint32_t marker_bits;
    uint32_t tsu_enabled;
    uint32_t words;

    if (image == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetEventFormat(instance, &marker_bits, &tsu_enabled);

    if (!encode_tx_element(frame, marker_bits, &element))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    (void)memset(image, 0, sizeof(*image));

    if (CAN_testEncodeDmuTx(instance, &element, image->words, ET_CAN_DMU_IMAGE_WORDS, &words) !=
        DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    image->byte_count = words * sizeof(uint32_t);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Validate the bounded raw-image envelope before passing words to the own Driver.
 * @param[in] image CPU-owned bytes; padding must be zero.
 * @return Nonzero only for a nonempty word-aligned image within the software budget.
 * @note No chip element length is inferred here; the own Driver owns geometry checks.
 */
static int valid_dmu_image(const et_can_dmu_image_t *image)
{
    uint32_t index;

    if ((image == NULL) || (image->byte_count == 0u) ||
        (image->byte_count > ET_CAN_DMU_IMAGE_BYTES) ||
        (image->byte_count % sizeof(uint32_t) != 0u))
    {
        return 0;
    }

    for (index = image->byte_count / sizeof(uint32_t); index < ET_CAN_DMU_IMAGE_WORDS; ++index)
    {
        if (image->words[index] != 0u)
        {
            return 0;
        }
    }

    return 1;
}

/**
 * @brief Check decoded identifier alignment and protocol flag consistency.
 * @param[in] identifier Driver-native identifier encoding.
 * @param[in] extended Extended identifier flag.
 * @param[in] remote Remote frame flag.
 * @param[in] fd FD frame flag.
 * @param[in] brs Bit-rate switch flag.
 * @param[in] esi Error-state indicator flag.
 * @return Nonzero only for a valid Driver header.
 * @note Encoding facts are supplied by Chip Config; no raw image bits are decoded here.
 */
static int valid_dmu_header(uint32_t identifier, uint32_t extended, uint32_t remote, uint32_t fd,
                            uint32_t brs, uint32_t esi)
{
    return (extended <= 1u) && (remote <= 1u) && (fd <= 1u) && (brs <= 1u) && (esi <= 1u) &&
           !(fd && remote) && !(!fd && (brs || esi)) &&
           (identifier <= frame_mapping.extended_id_max) &&
           (extended ||
            ((((identifier >> frame_mapping.standard_id_shift)
               << frame_mapping.standard_id_shift) == identifier) &&
             ((identifier >> frame_mapping.standard_id_shift) <= frame_mapping.standard_id_max)));
}

/**
 * @brief Decode one already-copied RX image through the own Chip Driver.
 * @param[in] id Logical controller supplying actual format and FIFO geometry.
 * @param[in] fifo Public receive FIFO number.
 * @param[in] image Bounded copied DMA bytes.
 * @param[out] decoded Actual frame and explicit timestamp validity.
 * @return OK, invalid argument, unsupported instance or malformed-image error.
 * @note Does not read a FIFO, acknowledge it, consume TSU slots or operate DMA.
 */
et_wrap_status_t et_can_wrap_decode_dmu_rx(et_can_id_t id, uint32_t fifo,
                                           const et_can_dmu_image_t *image,
                                           et_can_dmu_rx_image_t *decoded)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxBufElement element;
    CAN_TestDmuRxMetadata metadata;
    uint32_t byte;

    if ((decoded == NULL) || (fifo >= sizeof(rx_fifo_numbers) / sizeof(rx_fifo_numbers[0])) ||
        !valid_dmu_image(image))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((CAN_testDecodeDmuRx(instance, rx_fifo_numbers[fifo], image->words,
                             image->byte_count / sizeof(uint32_t), &element,
                             &metadata) != DRV_OK) ||
        !valid_dmu_header(element.id, element.xtd, element.rtr, element.fdf, element.brs,
                          element.esi) ||
        (metadata.validPayloadBytes > ET_CAN_FRAME_DATA_BYTES))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    (void)memset(decoded, 0, sizeof(*decoded));
    decoded->frame.identifier =
        element.xtd ? element.id : element.id >> frame_mapping.standard_id_shift;
    decoded->frame.flags =
        (element.xtd ? ET_CAN_FRAME_EXTENDED : 0u) | (element.rtr ? ET_CAN_FRAME_REMOTE : 0u) |
        (element.fdf ? ET_CAN_FRAME_FD : 0u) | (element.brs ? ET_CAN_FRAME_BRS : 0u) |
        (element.esi ? ET_CAN_FRAME_ESI : 0u);
    decoded->frame.dlc = element.dlc;
    decoded->frame.timestamp = element.rxts;
    decoded->frame.filter_index = element.fidx;
    decoded->frame.nonmatching = element.anmf;
    decoded->frame.data_length = metadata.validPayloadBytes;
    decoded->frame.index = UINT32_MAX;

    for (byte = 0u; byte < metadata.validPayloadBytes; ++byte)
    {
        decoded->frame.data[byte] = (uint8_t)element.data[byte];
    }

    decoded->internal_timestamp_valid = metadata.internalTimestampValid;
    decoded->tsu_captured = metadata.tsuCaptured;
    decoded->tsu_pointer = metadata.tsuPointer;
    decoded->transferred_timestamp_valid = metadata.transferredTimestampValid;
    decoded->transferred_timestamp = metadata.transferredTimestamp;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Decode one already-copied TX event image using the actual target format.
 * @param[in] id Logical controller.
 * @param[in] image Bounded DMA bytes, not a pointer to a virtual window.
 * @param[out] decoded Event and explicit timestamp validity; no FIFO index is fabricated.
 * @return OK, invalid argument, unsupported instance or malformed-image error.
 * @note Only own-IP configuration reads occur; no live event or TSU slot is consumed.
 */
et_wrap_status_t et_can_wrap_decode_dmu_event(et_can_id_t id, const et_can_dmu_image_t *image,
                                              et_can_dmu_event_image_t *decoded)
{
    CAN_Type *instance = find_instance(id);
    CAN_TxEventFIFOElement event;
    CAN_TestEventMetadata metadata;
    uint32_t transferred_valid;
    uint32_t transferred_timestamp;

    if ((decoded == NULL) || !valid_dmu_image(image))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((CAN_testDecodeDmuEvent(instance, image->words, image->byte_count / sizeof(uint32_t),
                                &event, &metadata, &transferred_valid,
                                &transferred_timestamp) != DRV_OK) ||
        !valid_dmu_header(event.id, event.xtd, event.rtr, event.fdf, event.brs, event.esi) ||
        ((event.et != ET_CAN_TX_EVENT_TRANSMITTED) &&
         (event.et != ET_CAN_TX_EVENT_TRANSMITTED_AFTER_CANCEL)))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    (void)memset(decoded, 0, sizeof(*decoded));
    decoded->details.event.identifier =
        event.xtd ? event.id : event.id >> frame_mapping.standard_id_shift;
    decoded->details.event.flags =
        (event.xtd ? ET_CAN_FRAME_EXTENDED : 0u) | (event.rtr ? ET_CAN_FRAME_REMOTE : 0u) |
        (event.fdf ? ET_CAN_FRAME_FD : 0u) | (event.brs ? ET_CAN_FRAME_BRS : 0u) |
        (event.esi ? ET_CAN_FRAME_ESI : 0u);
    decoded->details.event.dlc = event.dlc;
    decoded->details.event.timestamp = event.txts;
    decoded->details.event.event_type = event.et;
    decoded->details.event.marker = event.mm;
    decoded->details.event.index = UINT32_MAX;
    decoded->details.internal_timestamp_valid = metadata.internalTimestampValid;
    decoded->details.tsu_captured = metadata.tsuCaptured;
    decoded->details.tsu_pointer = metadata.tsuPointer;
    decoded->transferred_timestamp_valid = transferred_valid;
    decoded->transferred_timestamp = transferred_timestamp;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Prepare one allocated TX element without requesting transmission.
 * @param[in] id Logical controller.
 * @param[in] index Allocated software-owned slot, including FIFO/Queue preload slots.
 * @param[in] frame Explicit protocol frame; unused payload bytes are ignored by the Driver.
 * @return OK or an argument, busy, state, unsupported-instance or Driver error.
 * @note Checks actual RAM configuration and pending state; no polling or implicit reset.
 */
et_wrap_status_t et_can_wrap_write_tx(et_can_id_t id, uint32_t index,
                                      const et_can_tx_frame_t *frame)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_TxFIFOStatus fifo;
    CAN_TxBufElement element;
    uint32_t capacity;
    uint32_t total;
    uint32_t marker_bits;
    uint32_t tsu_enabled;

    /* Phase 1: Validate the public frame and independently read the allocated slot. */
    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetEventFormat(instance, &marker_bits, &tsu_enabled);

    if (!encode_tx_element(frame, marker_bits, &element))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    total = config.txBufNum + config.txFIFOSize;

    if ((total > ram_limits.tx_count) || (index >= total) ||
        (index >= sizeof(uint32_t) * CHAR_BIT) ||
        !payload_from_driver(config.txBufElemSize, &capacity) ||
        (CAN_testGetPayloadSize(element.dlc, element.fdf, element.rtr) > capacity))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    {
        const et_can_ram_region_t region = {
            config.txStartAddr, total * CAN_getMsgObjSize(config.txBufElemSize) * sizeof(uint32_t)};

        if (!ram_regions_valid(&region, 1u))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }
    }

    /* Phase 2: Protect hardware-owned pending/queued slots; acceptance is not completion. */
    if ((CAN_getTxBufReqPend(instance) & (1u << index)) != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (index >= config.txBufNum)
    {
        CAN_getTxFIFOQueStatus(instance, &fifo);

        /* Batch preloading must not advance TXBAR; pending slots remain protected above. */
        if (fifo.fifoFull != 0u)
        {
            return ET_WRAP_STATUS_BUSY;
        }
    }

    if (element.fdf && !CAN_isFDOpEnable(instance))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    return CAN_testWriteTxElement(instance, index, &element) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                       : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Request one or more prepared buffers using one atomic Driver write.
 * @param[in] id Logical controller.
 * @param[in] mask Nonzero bitmap of allocated TX buffers.
 * @return OK or invalid mask, state, busy or unsupported-instance result.
 * @note Does not populate frames, poll completion or retry a request.
 */
et_wrap_status_t et_can_wrap_request_tx(et_can_id_t id, uint32_t mask)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    uint32_t total;
    uint32_t allowed;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);
    total = config.txBufNum + config.txFIFOSize;

    if ((total == 0u) || (total > ram_limits.tx_count) || (total > sizeof(mask) * CHAR_BIT))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    allowed = total == sizeof(mask) * CHAR_BIT ? UINT32_MAX : (1u << total) - 1u;

    if ((mask == 0u) || ((mask & ~allowed) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) == CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if ((CAN_getTxBufReqPend(instance) & mask) != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    CAN_testRequestTxMask(instance, mask);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read one prepared basic TX element through the own-IP Driver.
 * @param[in] id Logical controller.
 * @param[in] index Allocated software-owned TX slot.
 * @param[out] frame Actual header and payload; unused payload bytes are zero.
 * @return OK, BUSY, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR.
 * @note Does not request transmission, acknowledge a FIFO or use cached request data.
 */
et_wrap_status_t et_can_wrap_read_tx(et_can_id_t id, uint32_t index, et_can_tx_frame_t *frame)
{
    CAN_Type *instance = find_instance(id);
    CAN_TxBufElement element;
    size_t byte;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if ((frame == NULL) || (index >= ram_limits.tx_count) || (index >= sizeof(uint32_t) * CHAR_BIT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((CAN_getTxBufReqPend(instance) & (1u << index)) != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (CAN_testReadTxBuffer(instance, index, &element) != DRV_OK)
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    frame->identifier = element.xtd ? element.id : element.id >> frame_mapping.standard_id_shift;
    frame->flags = (element.xtd ? ET_CAN_FRAME_EXTENDED : 0u) |
                   (element.rtr ? ET_CAN_FRAME_REMOTE : 0u) | (element.fdf ? ET_CAN_FRAME_FD : 0u) |
                   (element.brs ? ET_CAN_FRAME_BRS : 0u) | (element.esi ? ET_CAN_FRAME_ESI : 0u) |
                   (element.efc ? ET_CAN_FRAME_STORE_EVENT : 0u) |
                   (element.tx_tsce ? ET_CAN_FRAME_CAPTURE_TIME : 0u);
    frame->dlc = element.dlc;
    frame->marker = element.mm;

    for (byte = 0u; byte < ET_CAN_FRAME_DATA_BYTES; ++byte)
    {
        frame->data[byte] = (uint8_t)element.data[byte];
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read TX request/completion/cancellation and FIFO state.
 * @param[in] id Logical controller.
 * @param[out] status Independent hardware status fields.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not clear completion bits or consume TX events.
 */
et_wrap_status_t et_can_wrap_get_tx_status(et_can_id_t id, et_can_tx_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_TxFIFOStatus fifo;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getTxFIFOQueStatus(instance, &fifo);
    status->pending = CAN_getTxBufReqPend(instance);
    status->completed = CAN_getTxBufTransmissionStatus(instance);
    status->cancelled = CAN_txBufCancellationStatus(instance);
    status->free_count = fifo.freeLvl;
    status->get_index = fifo.getIdx;
    status->put_index = fifo.putIdx;
    status->full = fifo.fifoFull;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read and validate TX Event occupancy with its current RAM configuration.
 * @param[in] instance Validated CAN Driver instance.
 * @param[out] config Current RAM configuration retained for the caller's bounds check.
 * @param[out] status Fill, indices, full and lost facts from one Driver sample.
 * @return OK or an argument, unsupported-instance or invalid-hardware-state error.
 * @note One command-local snapshot is shared; no persistent configuration cache is used.
 */
static et_wrap_status_t read_tx_event_status(CAN_Type *instance, CAN_MsgRAMConfigParams *config,
                                             et_can_tx_event_status_t *status)
{
    CAN_TxEventFIFOStatus actual;
    uint32_t count;
    CAN_testGetMsgRAMConfig(instance, config);
    CAN_getTxEventFIFOStatus(instance, &actual);
    count = config->txEventFIFOSize;

    /* Validate every Driver field before publishing a coherent public snapshot. */
    if ((count > ram_limits.event_count) || (actual.fillLvl > count) || (actual.fifoFull > 1u) ||
        (actual.eleLost > 1u) ||
        ((count == 0u) && ((actual.fillLvl != 0u) || (actual.getIdx != 0u) ||
                           (actual.putIdx != 0u) || (actual.fifoFull != 0u))) ||
        ((count != 0u) && ((actual.getIdx >= count) || (actual.putIdx >= count))))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    status->fill = actual.fillLvl;
    status->get_index = actual.getIdx;
    status->put_index = actual.putIdx;
    status->full = actual.fifoFull;
    status->lost = actual.eleLost;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read actual TX Event FIFO occupancy without consuming an event.
 * @param[in] id Logical controller.
 * @param[out] status Fill, indices, full and lost facts from the Driver.
 * @return OK or an argument, unsupported-instance or invalid-hardware-state error.
 * @note A full or lost indication is an observation, not a test verdict.
 */
et_wrap_status_t et_can_wrap_get_tx_event_status(et_can_id_t id, et_can_tx_event_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return read_tx_event_status(instance, &config, status);
}

/**
 * @brief Read the current TX Event FIFO head and its hardware format metadata.
 * @param[in] id Logical controller.
 * @param[out] event Actual event metadata and current hardware Get Index.
 * @param[out] metadata Actual timestamp validity and TSU pointer; NULL requires basic format.
 * @return OK or an argument, empty FIFO, bad layout or unsupported-instance error.
 * @note The event remains owned by hardware until et_can_wrap_ack_tx_event is called.
 */
static et_wrap_status_t read_tx_event(et_can_id_t id, et_can_tx_event_t *event,
                                      CAN_TestEventMetadata *metadata)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_TxEventFIFOElement actual;
    et_can_tx_event_status_t status;
    et_can_ram_region_t region;
    et_wrap_status_t result;
    uint32_t count;
    CAN_TestEventMetadata actual_metadata;

    if (event == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    /* Phase 1: Confirm a configured, non-empty and in-range hardware FIFO head. */
    result = read_tx_event_status(instance, &config, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if (status.fill == 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    count = config.txEventFIFOSize;
    region.offset = config.txEventFIFOStartAddr;
    region.length = count * CAN_TX_EVENT_FIFO_SIZE_WORDS * sizeof(uint32_t);

    if ((count == 0u) || !ram_regions_valid(&region, 1u))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Read exactly the current head; no hidden acknowledge or polling follows. */
    (void)memset(&actual, 0, sizeof(actual));
    CAN_testReadTxEvent(instance, &actual, &actual_metadata);

    if ((metadata == NULL) && (actual_metadata.internalTimestampValid == 0u))
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if ((actual.xtd > 1u) || (actual.rtr > 1u) || (actual.esi > 1u) || (actual.brs > 1u) ||
        (actual.fdf > 1u) || (actual.dlc > ET_CAN_FRAME_DLC_MAX) ||
        ((actual.et != ET_CAN_TX_EVENT_TRANSMITTED) &&
         (actual.et != ET_CAN_TX_EVENT_TRANSMITTED_AFTER_CANCEL)) ||
        (actual.id > frame_mapping.extended_id_max) ||
        ((actual.xtd == 0u) &&
         ((((actual.id >> frame_mapping.standard_id_shift) << frame_mapping.standard_id_shift) !=
           actual.id) ||
          ((actual.id >> frame_mapping.standard_id_shift) > frame_mapping.standard_id_max))))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    event->identifier = actual.xtd ? actual.id : actual.id >> frame_mapping.standard_id_shift;
    event->flags = (actual.xtd ? ET_CAN_FRAME_EXTENDED : 0u) |
                   (actual.rtr ? ET_CAN_FRAME_REMOTE : 0u) | (actual.fdf ? ET_CAN_FRAME_FD : 0u) |
                   (actual.brs ? ET_CAN_FRAME_BRS : 0u) | (actual.esi ? ET_CAN_FRAME_ESI : 0u);
    event->dlc = actual.dlc;
    event->timestamp = actual.txts;
    event->event_type = actual.et;
    event->marker = actual.mm;
    event->index = status.get_index;

    if (metadata != NULL)
    {
        *metadata = actual_metadata;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read an event using the original internal-timestamp contract.
 * @param[in] id Logical controller.
 * @param[out] event Actual event data.
 * @return OK or a read/format error.
 * @note Wide-marker/TSU format is rejected instead of fabricating a timestamp.
 */
et_wrap_status_t et_can_wrap_read_tx_event(et_can_id_t id, et_can_tx_event_t *event)
{
    return read_tx_event(id, event, NULL);
}

/**
 * @brief Read an event with explicit internal timestamp and TSU validity.
 * @param[in] id Logical controller.
 * @param[out] details Actual decoded event and validity metadata.
 * @return OK or an argument/read error.
 * @note Does not acknowledge the event or read a TSU timestamp register.
 */
et_wrap_status_t et_can_wrap_read_tx_event_details(et_can_id_t id,
                                                   et_can_tx_event_details_t *details)
{
    CAN_TestEventMetadata metadata;
    et_wrap_status_t status;

    if (details == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    status = read_tx_event(id, &details->event, &metadata);

    if (status == ET_WRAP_STATUS_OK)
    {
        details->internal_timestamp_valid = metadata.internalTimestampValid;
        details->tsu_captured = metadata.tsuCaptured;
        details->tsu_pointer = metadata.tsuPointer;
    }

    return status;
}

/**
 * @brief Select explicit marker width and TSU use through the own Driver.
 * @param[in] id Logical controller.
 * @param[in] format Width in bits and Boolean TSU use.
 * @return OK, invalid argument, unsupported instance or state error.
 * @note Requires INIT, preserves other options and does not configure the TSU itself.
 */
et_wrap_status_t et_can_wrap_set_event_format(et_can_id_t id, const et_can_event_format_t *format)
{
    CAN_Type *instance = find_instance(id);

    if ((format == NULL) ||
        ((format->marker_bits != CAN_TEST_MARKER_BITS_BASIC) &&
         (format->marker_bits != CAN_TEST_MARKER_BITS_WIDE)) ||
        (format->tsu_enabled > 1u) ||
        ((format->tsu_enabled != 0u) && (format->marker_bits != CAN_TEST_MARKER_BITS_WIDE)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testSetEventFormat(instance, format->marker_bits, format->tsu_enabled) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read the effective element format without changing controller state.
 * @param[in] id Logical controller.
 * @param[out] format Actual effective marker width and TSU enable.
 * @return OK, invalid argument or unsupported instance.
 * @note Reads configuration only; no event or timestamp is consumed.
 */
et_wrap_status_t et_can_wrap_get_event_format(et_can_id_t id, et_can_event_format_t *format)
{
    CAN_Type *instance = find_instance(id);

    if (format == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetEventFormat(instance, &format->marker_bits, &format->tsu_enabled);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Configure TSU through the own Driver, without selecting UTSU or entering INIT.
 * @param[in] id Logical controller.
 * @param[in] config Boolean options and actual divisor.
 * @return OK, invalid argument, unsupported instance or state error.
 * @note External timebase pins are not controlled here.
 */
et_wrap_status_t et_can_wrap_set_tsu(et_can_id_t id, const et_can_tsu_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_TSUConfigParams params;

    if ((config == NULL) || (config->enabled > 1u) || (config->external > 1u) ||
        (config->sof > 1u) || (config->divisor < 1u) || (config->divisor > ET_CAN_TSU_DIVISOR_MAX))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    params.enable = config->enabled;
    params.tbcs = config->external;
    params.scp = config->sof;
    params.tbPrescalar = config->divisor;

    return CAN_testSetTsu(instance, &params) == DRV_OK ? ET_WRAP_STATUS_OK
                                                       : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read actual TSU configuration without consuming captures.
 * @param[in] id Logical controller.
 * @param[out] config Actual hardware configuration.
 * @return OK, invalid argument or unsupported instance.
 * @note No cached configuration or implicit writes.
 */
et_wrap_status_t et_can_wrap_get_tsu(et_can_id_t id, et_can_tsu_config_t *config)
{
    CAN_Type *instance = find_instance(id);
    CAN_TSUConfigParams params;

    if (config == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetTsu(instance, &params);
    config->enabled = params.enable;
    config->external = params.tbcs;
    config->sof = params.scp;
    config->divisor = params.tbPrescalar;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read real synthesized TSU limits through the own Driver.
 * @param[in] id Logical controller.
 * @param[out] limits Slot count and internal/SOF support.
 * @return OK, invalid argument, unsupported instance or state error.
 * @note Invalid synthesis encodings fail closed, never assume eight slots.
 */
et_wrap_status_t et_can_wrap_get_tsu_limits(et_can_id_t id, et_can_tsu_limits_t *limits)
{
    CAN_Type *instance = find_instance(id);

    if (limits == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testGetTsuLimits(instance, &limits->slots, &limits->internal, &limits->sof) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read one non-consuming New/Lost hardware snapshot.
 * @param[in] id Logical controller.
 * @param[out] new_flags Actual New bitmap.
 * @param[out] lost_flags Actual Lost bitmap from the same snapshot.
 * @return OK, invalid argument or unsupported instance.
 * @note Does not read a timestamp slot or clear any flags.
 */
et_wrap_status_t et_can_wrap_get_tsu_flags(et_can_id_t id, uint32_t *new_flags,
                                           uint32_t *lost_flags)
{
    CAN_Type *instance = find_instance(id);

    if ((new_flags == NULL) || (lost_flags == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetTsuFlags(instance, new_flags, lost_flags);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read one TSU value through the own Chip Driver.
 * @param[in] id Logical controller.
 * @param[in] consume Zero selects active timebase, one consumes TS0.
 * @param[out] value Actual 32-bit hardware value.
 * @return OK, invalid argument or unsupported instance.
 * @note TS0 clears only its New/Lost in hardware; no retry or guessed slots.
 */
et_wrap_status_t et_can_wrap_read_tsu_value(et_can_id_t id, uint8_t consume, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if ((value == NULL) || (consume > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = consume != 0u ? CAN_testConsumeTsuSlot0(instance) : CAN_testGetTsuTimebase(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Access the controller's external vector through its own driver.
 * @param[in] id Logical controller.
 * @param[in] write Strict Boolean selecting write instead of read.
 * @param[in,out] value Input vector on write, actual hardware vector on read.
 * @return OK, invalid argument, unsupported instance or invalid state.
 * @note Writes require INIT and change the external vector, not TSU configuration.
 */
et_wrap_status_t et_can_wrap_access_external_vector(et_can_id_t id, uint8_t write, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if ((value == NULL) || (write > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testAccessExternalVector(instance, write, value) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read the actual RAM watchdog configuration and current counter.
 * @param[in] id Logical CAN controller.
 * @param[out] limit Actual configured watchdog cycles; zero means disabled.
 * @param[out] value Current hardware counter in CAN system clock cycles.
 * @return OK, invalid argument or unsupported instance.
 * @note One own-driver snapshot; no reload, IRQ clear or inferred response latency.
 */
et_wrap_status_t et_can_wrap_get_ram_watchdog(et_can_id_t id, uint32_t *limit, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if ((limit == NULL) || (value == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testGetRamWatchdog(instance, limit, value) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Acknowledge the current TX Event FIFO head through the CAN Driver.
 * @param[in] id Logical controller.
 * @param[in] index Get Index returned by the preceding status or event read.
 * @return OK or an argument, empty/stale index, unsupported-instance or Driver error.
 * @note The current hardware status closes the SDK boundary-check gap before the write.
 */
et_wrap_status_t et_can_wrap_ack_tx_event(et_can_id_t id, uint32_t index)
{
    CAN_Type *instance = find_instance(id);
    et_can_tx_event_status_t status;
    et_wrap_status_t result;

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    result = et_can_wrap_get_tx_event_status(id, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if ((status.fill == 0u) || (index != status.get_index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return CAN_writeTxEventFIFOAck(instance, index) == DRV_OK ? ET_WRAP_STATUS_OK
                                                              : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read one selected receive FIFO without acknowledging entries.
 * @param[in] id Logical controller.
 * @param[in] fifo Public FIFO index.
 * @param[out] status Actual fill, get, put, full and lost status.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, reset or read protocol error counters.
 */
et_wrap_status_t et_can_wrap_get_rx_fifo_status(et_can_id_t id, uint32_t fifo,
                                                et_can_rx_fifo_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxFIFOStatus driver;

    if ((status == NULL) || (fifo >= sizeof(rx_fifo_numbers) / sizeof(rx_fifo_numbers[0])))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    driver.num = rx_fifo_numbers[fifo];
    CAN_getRxFIFOStatus(instance, &driver);
    status->fill = driver.fillLvl;
    status->get_index = driver.getIdx;
    status->put_index = driver.putIdx;
    status->full = driver.fifoFull;
    status->lost = driver.msgLost;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read dedicated-buffer new-data status without clearing it.
 * @param[in] id Logical controller.
 * @param[out] status Actual low and high new-data bitmaps.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No buffer data is consumed and no acknowledgement is issued.
 */
et_wrap_status_t et_can_wrap_get_rx_buffer_status(et_can_id_t id, et_can_rx_buffer_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxNewDataStatus driver;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getNewDataStatus(instance, &driver);
    status->low = driver.statusLow;
    status->high = driver.statusHigh;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge explicit dedicated-buffer new-data bits.
 * @param[in] id Logical controller.
 * @param[in] status Caller-selected low/high masks, not an implicit clear-all.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not change filters, data bytes or receive FIFO state.
 */
et_wrap_status_t et_can_wrap_ack_rx_buffers(et_can_id_t id, const et_can_rx_buffer_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_RxNewDataStatus driver;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    driver.statusLow = status->low;
    driver.statusHigh = status->high;
    CAN_clearNewDataStatus(instance, &driver);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Acknowledge the current head of a nonempty receive FIFO.
 * @param[in] id Logical controller.
 * @param[in] fifo Public FIFO index.
 * @param[in] index Previously observed head index, preventing accidental acknowledgement drift.
 * @return OK or invalid index, empty FIFO, unsupported instance or Driver error.
 * @note Acknowledges exactly one head; no bulk draining or polling is performed.
 */
et_wrap_status_t et_can_wrap_ack_rx_fifo(et_can_id_t id, uint32_t fifo, uint32_t index)
{
    et_can_rx_fifo_status_t status;
    et_wrap_status_t result = et_can_wrap_get_rx_fifo_status(id, fifo, &status);

    if (result != ET_WRAP_STATUS_OK)
    {
        return result;
    }

    if (status.fill == 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (index != status.get_index)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return CAN_writeRxFIFOAck(find_instance(id), rx_fifo_numbers[fifo], index) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read one available RX element without acknowledging it.
 * @param[in] id Logical controller.
 * @param[in] source Dedicated buffer, FIFO0 or FIFO1.
 * @param[in] index Dedicated-buffer index; must be zero for FIFO head reads.
 * @param[out] frame Observed header, valid stored bytes and selected storage index.
 * @return OK, invalid selector/index, empty storage, bad layout or unsupported instance.
 * @note No polling or automatic acknowledgement; a short slot returns only stored bytes.
 */
et_wrap_status_t et_can_wrap_read_rx(et_can_id_t id, et_can_rx_source_t source, uint32_t index,
                                     et_can_rx_frame_t *frame)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;
    CAN_RxBufElement element;
    et_can_rx_fifo_status_t fifo_status;
    et_can_rx_buffer_status_t buffer_status;
    et_wrap_status_t result;
    uint32_t fifo = 0u;
    uint32_t driver_size;
    uint32_t offset;
    uint32_t capacity;
    uint32_t mem_type;
    uint32_t data_length;
    size_t byte;

    /* Phase 1: Resolve an available hardware-owned element and its actual RAM slot. */
    if ((frame == NULL) || ((source != ET_CAN_RX_BUFFER) && (source != ET_CAN_RX_FIFO0) &&
                            (source != ET_CAN_RX_FIFO1)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);

    if (source == ET_CAN_RX_BUFFER)
    {
        const uint32_t word_bits = sizeof(uint32_t) * CHAR_BIT;
        uint32_t active;

        if ((index >= ram_limits.rx_buffer_count) || (index >= word_bits + word_bits))
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        result = et_can_wrap_get_rx_buffer_status(id, &buffer_status);

        if (result != ET_WRAP_STATUS_OK)
        {
            return result;
        }

        active = index < word_bits ? buffer_status.low : buffer_status.high;

        if ((active & (1u << (index % word_bits))) == 0u)
        {
            return ET_WRAP_STATUS_BUSY;
        }

        driver_size = config.rxBufElemSize;
        offset = config.rxBufStartAddr;
        mem_type = CAN_MEM_TYPE_BUF;
    }
    else
    {
        if (index != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        fifo = source == ET_CAN_RX_FIFO0 ? 0u : 1u;
        result = et_can_wrap_get_rx_fifo_status(id, fifo, &fifo_status);

        if (result != ET_WRAP_STATUS_OK)
        {
            return result;
        }

        if (fifo_status.fill == 0u)
        {
            return ET_WRAP_STATUS_BUSY;
        }

        index = fifo_status.get_index;

        if (index >= (fifo == 0u ? config.rxFIFO0size : config.rxFIFO1size))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }

        driver_size = fifo == 0u ? config.rxFIFO0ElemSize : config.rxFIFO1ElemSize;
        offset = fifo == 0u ? config.rxFIFO0startAddr : config.rxFIFO1startAddr;
        mem_type = CAN_MEM_TYPE_FIFO;
    }

    /* Phase 2: Bound the physical slot before the Driver reads Message RAM. */
    if (!payload_from_driver(driver_size, &capacity))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    {
        const uint32_t stride = CAN_getMsgObjSize(driver_size) * sizeof(uint32_t);
        const et_can_ram_region_t region = {offset + index * stride, stride};

        if (!ram_regions_valid(&region, 1u))
        {
            return ET_WRAP_STATUS_STATE_ERROR;
        }
    }

    (void)memset(&element, 0, sizeof(element));
    CAN_readMsgRam(instance, mem_type, index, rx_fifo_numbers[fifo], &element);
    data_length = CAN_testGetPayloadSize(element.dlc, element.fdf, element.rtr);

    /* Phase 3: Publish actual metadata and stored bytes, keeping acknowledgement explicit. */
    (void)memset(frame, 0, sizeof(*frame));
    frame->identifier = element.xtd ? element.id : element.id >> frame_mapping.standard_id_shift;
    frame->flags = (element.xtd ? ET_CAN_FRAME_EXTENDED : 0u) |
                   (element.rtr ? ET_CAN_FRAME_REMOTE : 0u) | (element.fdf ? ET_CAN_FRAME_FD : 0u) |
                   (element.brs ? ET_CAN_FRAME_BRS : 0u) | (element.esi ? ET_CAN_FRAME_ESI : 0u);
    frame->dlc = element.dlc;
    frame->timestamp = element.rxts;
    frame->filter_index = element.fidx;
    frame->nonmatching = element.anmf;
    frame->data_length = data_length < capacity ? data_length : capacity;
    frame->index = index;

    for (byte = 0u; byte < frame->data_length; ++byte)
    {
        frame->data[byte] = (uint8_t)element.data[byte];
    }

    return ET_WRAP_STATUS_OK;
}

static const uint32_t standard_filter_types[] = ET_CHIP_CAN_STD_FILTER_MAP_TABLE;
static const uint32_t extended_filter_types[] = ET_CHIP_CAN_EXT_FILTER_MAP_TABLE;
static const uint32_t filter_actions[] = ET_CHIP_CAN_FILTER_ACTION_MAP_TABLE;
static const uint32_t filter_sizes[] = ET_CHIP_CAN_FILTER_SIZE_MAP_TABLE;

/**
 * @brief Validate an allocated filter location against the actual RAM layout.
 * @param[in] instance Resolved CAN Driver instance.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Filter index, not byte offset.
 * @return One when the complete element is inside the configured list and RAM.
 * @note Guards a corrupted layout without resetting it or guessing an address.
 */
static int filter_location_valid(CAN_Type *instance, uint32_t extended, uint32_t index)
{
    CAN_MsgRAMConfigParams layout;
    uint32_t count;
    et_can_ram_region_t region;

    CAN_testGetMsgRAMConfig(instance, &layout);
    count = extended ? layout.lse : layout.lss;

    if ((index >= count) || (count > (extended ? ram_limits.ext_count : ram_limits.std_count)))
    {
        return 0;
    }

    region.offset = extended ? layout.flesa : layout.flssa;
    region.length = count * filter_sizes[extended];

    return ram_regions_valid(&region, 1u);
}

/**
 * @brief Check public filter semantics before writing a RAM element.
 * @param[in] extended Validated frame format selector.
 * @param[in] filter Public operation and identifiers.
 * @return One for representable semantics, zero otherwise.
 * @note Dedicated Buffer mode is exact ID matching; debug/timestamp bits are excluded.
 */
static int filter_values_valid(uint32_t extended, const et_can_filter_t *filter)
{
    uint32_t maximum = extended ? frame_mapping.extended_id_max : frame_mapping.standard_id_max;
    const uint32_t *types = extended ? extended_filter_types : standard_filter_types;

    if ((filter->type > ET_CAN_FILTER_DISABLED) || (filter->action > ET_CAN_FILTER_ACTION_BUFFER) ||
        (filter->id1 > maximum) || (filter->id2 > maximum) || (types[filter->type] == UINT32_MAX))
    {
        return 0;
    }

    if (filter->action == ET_CAN_FILTER_ACTION_BUFFER)
    {
        return (filter->type == ET_CAN_FILTER_RANGE) && (filter->id2 == 0u) &&
               (filter->buffer_index < ram_limits.rx_buffer_count);
    }

    if (filter->buffer_index != 0u)
    {
        return 0;
    }

    if (((filter->type == ET_CAN_FILTER_RANGE) || (filter->type == ET_CAN_FILTER_RANGE_NO_MASK)) &&
        (filter->id2 < filter->id1))
    {
        return 0;
    }

    return 1;
}

/**
 * @brief Program one existing filter slot through the CAN Driver.
 * @param[in] id Logical CAN controller.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Slot within the configured list.
 * @param[in] filter Explicit matching operation and destination.
 * @return OK or an argument, mapping or initialization error.
 * @note Requires INIT; does not resize lists, clear other entries or start CAN.
 */
et_wrap_status_t et_can_wrap_set_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        const et_can_filter_t *filter)
{
    CAN_Type *instance = find_instance(id);
    CAN_StdMsgIDFilterElement standard;
    CAN_ExtMsgIDFilterElement ext;
    uint32_t second;

    /* Phase 1: Reject malformed selectors and locations before any RAM write. */
    if ((filter == NULL) || (extended > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (!filter_values_valid(extended, filter) || !filter_location_valid(instance, extended, index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    /* Phase 2: Map semantic Buffer index separately from the ordinary second ID. */
    second = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? filter->buffer_index : filter->id2;

    if (extended != 0u)
    {
        ext.efid1 = filter->id1;
        ext.efid2 = second;
        ext.efec = filter_actions[filter->action];
        ext.eft = extended_filter_types[filter->type];
        CAN_addExtMsgIDFilter(instance, index, &ext);
    }
    else
    {
        standard.sfid1 = filter->id1;
        standard.sfid2 = second;
        standard.sfec = filter_actions[filter->action];
        standard.sft = standard_filter_types[filter->type];
        CAN_addStdMsgIDFilter(instance, index, &standard);
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read actual filter RAM and translate its basic acceptance semantics.
 * @param[in] id Logical CAN controller.
 * @param[in] extended Zero for standard, one for extended.
 * @param[in] index Slot within the current list.
 * @param[out] filter Independently decoded RAM contents.
 * @return OK or an argument, mapping, Driver or unrepresentable-format error.
 * @note Does not return the last SET; timestamp/debug-buffer forms require another API.
 */
et_wrap_status_t et_can_wrap_get_filter(et_can_id_t id, uint32_t extended, uint32_t index,
                                        et_can_filter_t *filter)
{
    CAN_Type *instance = find_instance(id);
    CAN_StdMsgIDFilterElement standard;
    CAN_ExtMsgIDFilterElement ext;
    uint32_t type;
    uint32_t action;
    uint32_t second;
    const uint32_t *types;

    /* Phase 1: Validate the location and read only the requested RAM element. */
    if ((filter == NULL) || (extended > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (!filter_location_valid(instance, extended, index))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (extended != 0u)
    {
        if (CAN_testGetExtMsgIDFilter(instance, index, &ext) != DRV_OK)
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }

        filter->id1 = ext.efid1;
        second = ext.efid2;
        type = ext.eft;
        action = ext.efec;
        types = extended_filter_types;
    }
    else
    {
        if (CAN_testGetStdMsgIDFilter(instance, index, &standard) != DRV_OK)
        {
            return ET_WRAP_STATUS_IO_ERROR;
        }

        filter->id1 = standard.sfid1;
        second = standard.sfid2;
        type = standard.sft;
        action = standard.sfec;
        types = standard_filter_types;
    }

    /* Phase 2: Decode actual selectors; never silently discard unsupported Buffer bits. */
    if (!selector_from_driver(types, sizeof(standard_filter_types) / sizeof(types[0]), type,
                              &filter->type) ||
        !selector_from_driver(filter_actions, sizeof(filter_actions) / sizeof(filter_actions[0]),
                              action, &filter->action))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    filter->buffer_index = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? second : 0u;
    filter->id2 = filter->action == ET_CAN_FILTER_ACTION_BUFFER ? 0u : second;

    if ((filter->action == ET_CAN_FILTER_ACTION_BUFFER) &&
        (filter->buffer_index >= ram_limits.rx_buffer_count))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Program the extended acceptance AND mask via the existing CAN Driver.
 * @param[in] id Logical controller.
 * @param[in] mask Public unshifted extended identifier mask.
 * @return OK or an argument, state or Driver error.
 * @note Requires INIT and does not change individual filters or global acceptance.
 */
et_wrap_status_t et_can_wrap_set_extended_mask(et_can_id_t id, uint32_t mask)
{
    CAN_Type *instance = find_instance(id);

    if (mask > frame_mapping.extended_id_max)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    if (CAN_getOpMode(instance) != CAN_OPERATION_MODE_SW_INIT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    return CAN_setExtIDAndMask(instance, mask) == DRV_OK ? ET_WRAP_STATUS_OK
                                                         : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Read the extended acceptance AND mask without changing controller state.
 * @param[in] id Logical controller.
 * @param[out] mask Actual unshifted mask from hardware.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No cached requests, filter rewrites or receive acknowledgements.
 */
et_wrap_status_t et_can_wrap_get_extended_mask(et_can_id_t id, uint32_t *mask)
{
    CAN_Type *instance = find_instance(id);

    if (mask == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *mask = CAN_getExtIDANDMask(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the CAN Driver High Priority Message status once.
 * @param[in] id Logical CAN controller.
 * @param[out] status Public storage, filter-list and index facts.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR.
 * @note Does not read Message RAM, acknowledge FIFO data or clear High Priority IRQ.
 */
et_wrap_status_t et_can_wrap_get_high_priority_status(et_can_id_t id,
                                                      et_can_high_priority_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_HighPriorityMsgInfo actual;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_getHighPriorityMsgStatus(instance, &actual);

    /* Reject reserved Driver values instead of exporting corrupt status as a valid event. */
    if ((actual.msi > ET_CAN_HIGH_PRIORITY_FIFO1) || (actual.filterList > 1u))
    {
        return ET_WRAP_STATUS_IO_ERROR;
    }

    status->buffer_index = actual.bufIdx;
    status->storage = actual.msi;
    status->filter_index = actual.filterIdx;
    status->extended_filter = actual.filterList;

    return ET_WRAP_STATUS_OK;
}

static const uint32_t protocol_errors[] = ET_CHIP_CAN_ERROR_MAP_TABLE;
static const uint32_t protocol_activities[] = ET_CHIP_CAN_ACTIVITY_MAP_TABLE;

/**
 * @brief Consume protocol and error-counter observations exactly once each.
 * @param[in] id Logical controller.
 * @param[out] status Decoded first observations, never a cached expected state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note PSR then ECR are read in order; read-clear flags are consumed, with no retry.
 *       These are consecutive hardware samples, not a simultaneous atomic snapshot.
 */
et_wrap_status_t et_can_wrap_consume_protocol_status(et_can_id_t id,
                                                     et_can_protocol_status_t *status)
{
    CAN_Type *instance = find_instance(id);
    CAN_ProtocolStatus protocol;
    CAN_ErrCntStatus counters;

    if (status == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    /* Phase 1: Consume each read-clear register once through the own Driver. */
    CAN_getProtocolStatus(instance, &protocol);
    CAN_getErrCounters(instance, &counters);

    /* Phase 2: Map symbolic encodings and copy explicit observations without retries. */
    if ((selector_from_driver(protocol_errors, sizeof(protocol_errors) / sizeof(protocol_errors[0]),
                              protocol.lastErrCode, &status->last_error) == 0) ||
        (selector_from_driver(protocol_errors, sizeof(protocol_errors) / sizeof(protocol_errors[0]),
                              protocol.dlec, &status->data_last_error) == 0) ||
        (selector_from_driver(protocol_activities,
                              sizeof(protocol_activities) / sizeof(protocol_activities[0]),
                              protocol.act, &status->activity) == 0))
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    status->error_passive = protocol.errPassive;
    status->warning = protocol.warningStatus;
    status->bus_off = protocol.busOffStatus;
    status->received_esi = protocol.resi;
    status->received_brs = protocol.rbrs;
    status->received_fd = protocol.rfdf;
    status->protocol_exception = protocol.pxe;
    status->tdc_position = protocol.tdcv;
    status->tx_error_count = counters.transErrLogCnt;
    status->rx_error_count = counters.recErrCnt;
    status->rx_error_passive = counters.rpStatus;
    status->error_log_count = counters.canErrLogCnt;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the current timestamp counter without resetting it.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_timestamp(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getTSCounterVal(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read the timeout counter without reloading or changing its source.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_timeout_counter(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getTOCounterVal(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reload one continuous timeout and return adjacent actual count reads.
 * @param[in] id Logical controller.
 * @param[out] before Actual count before reload.
 * @param[out] after Actual count immediately after the Driver write.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or STATE_ERROR for a FIFO source.
 * @note No polling, IRQ clearing, implicit INIT transition or retry occurs.
 */
et_wrap_status_t et_can_wrap_reload_timeout(et_can_id_t id, uint32_t *before, uint32_t *after)
{
    CAN_Type *instance = find_instance(id);

    if ((before == NULL) || (after == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testReloadTimeout(instance, before, after) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                    : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Read clock-stop acknowledgement; do not claim that the external clock stopped.
 * @param[in] id Logical controller.
 * @param[out] value Actual single Driver readback.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Does not poll, consume FIFO entries or configure another IP.
 */
et_wrap_status_t et_can_wrap_get_clock_stop_ack(et_can_id_t id, uint32_t *value)
{
    CAN_Type *instance = find_instance(id);

    if (value == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    *value = CAN_getClockStopAck(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reset the timestamp counter through one existing Driver action.
 * @param[in] id Logical controller.
 * @return OK or NOT_SUPPORTED.
 * @note No extra delay or readback; a running counter may advance before the next query.
 */
et_wrap_status_t et_can_wrap_reset_timestamp(et_can_id_t id)
{
    CAN_Type *instance = find_instance(id);

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_resetTSCounter(instance);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Reset an internal timestamp with actual adjacent reads in one Driver action.
 * @param[in] id Logical controller.
 * @param[out] before Actual pre-reset value.
 * @param[out] after Actual post-reset value, not a constant zero.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or STATE_ERROR for a non-internal source.
 * @note Keeps the old reset API unchanged; no polling, retry or IRQ clearing occurs.
 */
et_wrap_status_t et_can_wrap_reset_timestamp_snapshot(et_can_id_t id, uint32_t *before,
                                                      uint32_t *after)
{
    CAN_Type *instance = find_instance(id);

    if ((before == NULL) || (after == NULL))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    return CAN_testResetTimestampSnapshot(instance, before, after) == DRV_OK
               ? ET_WRAP_STATUS_OK
               : ET_WRAP_STATUS_STATE_ERROR;
}

/**
 * @brief Request or withdraw CAN clock stop without waiting for acknowledgement.
 * @param[in] id Logical controller.
 * @param[in] requested Boolean request, not an assumed final state.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note The PC separately observes acknowledgement and restores INIT after withdrawal.
 */
et_wrap_status_t et_can_wrap_set_clock_stop(et_can_id_t id, uint8_t requested)
{
    CAN_Type *instance = find_instance(id);

    if (requested > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_addClockStopRequest(instance, requested);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or mask selected CAN interrupt sources through the own Driver.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @param[in] enabled Boolean source-enable request.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes IE only; IRQ Manager owns NVIC and vector binding.
 */
et_wrap_status_t et_can_wrap_set_irq_enabled(et_can_id_t id, uint32_t sources, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if ((enabled > 1u) || ((sources & ~ET_CAN_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_enableIntr(instance, translate_irq_events(sources, 1u), enabled);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable one allocated TX slot's transmission-complete event.
 * @param[in] id Logical controller identity.
 * @param[in] index Allocated dedicated or FIFO/Queue TX slot.
 * @param[in] enabled Boolean per-slot event enable.
 * @return OK, INVALID_ARGUMENT, NOT_SUPPORTED or IO_ERROR.
 * @note This is independent of the global CAN interrupt source and output line.
 */
et_wrap_status_t et_can_wrap_set_tx_buffer_irq(et_can_id_t id, uint32_t index, uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);
    CAN_MsgRAMConfigParams config;

    if (enabled > 1u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_testGetMsgRAMConfig(instance, &config);

    if ((index >= ram_limits.tx_count) || (index >= config.txBufNum + config.txFIFOSize))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    return CAN_txBufTransIntrEnable(instance, index, enabled) == DRV_OK ? ET_WRAP_STATUS_OK
                                                                        : ET_WRAP_STATUS_IO_ERROR;
}

/**
 * @brief Route selected CAN sources to controller interrupt line 0 or 1.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @param[in] line Stable controller-local line selector.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes ILS only and does not enable the source, controller line or NVIC route.
 */
et_wrap_status_t et_can_wrap_select_irq_line(et_can_id_t id, uint32_t sources,
                                             et_can_irq_line_t line)
{
    CAN_Type *instance = find_instance(id);

    if (((sources & ~ET_CAN_IRQ_ALL) != 0u) || (line >= ET_CAN_IRQ_LINE_COUNT))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_selectIntrLine(instance, translate_irq_events(sources, 1u),
                       line == ET_CAN_IRQ_LINE0 ? CAN_INTR_LINE_NUM_0 : CAN_INTR_LINE_NUM_1);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable or disable one controller-local interrupt output line.
 * @param[in] id Logical controller identity.
 * @param[in] line Stable controller-local line selector.
 * @param[in] enabled Boolean line-enable request.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note This changes ILE only; physical NVIC ownership remains in IRQ Manager.
 */
et_wrap_status_t et_can_wrap_set_irq_line_enabled(et_can_id_t id, et_can_irq_line_t line,
                                                  uint8_t enabled)
{
    CAN_Type *instance = find_instance(id);

    if ((line >= ET_CAN_IRQ_LINE_COUNT) || (enabled > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_enableIntrLine(
        instance, line == ET_CAN_IRQ_LINE0 ? CAN_INTR_LINE_NUM_0 : CAN_INTR_LINE_NUM_1, enabled);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Read current pending, source-enable, line-selection and line-enable facts.
 * @param[in] id Logical controller identity.
 * @param[out] snapshot Four non-destructive public interrupt observations.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note IR is read once; the Driver extension separately reads IE, ILS and ILE once each.
 */
et_wrap_status_t et_can_wrap_get_irq_snapshot(et_can_id_t id, et_can_irq_snapshot_t *snapshot)
{
    CAN_Type *instance = find_instance(id);
    uint32_t enabled;
    uint32_t line_selection;
    uint32_t line_enabled;

    if (snapshot == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    snapshot->raw_status = translate_irq_events(CAN_getIntrStatus(instance), 0u);
    CAN_testGetInterruptConfig(instance, &enabled, &line_selection, &line_enabled);
    snapshot->enabled_sources = translate_irq_events(enabled, 0u);
    snapshot->line1_sources = translate_irq_events(line_selection, 0u);
    snapshot->enabled_lines = line_enabled & CAN_INTR_LINE_EN_MASK;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear exactly the selected CAN pending sources.
 * @param[in] id Logical controller identity.
 * @param[in] sources Public semantic event mask.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note Level conditions may assert again until the owning FIFO or protocol condition is removed.
 */
et_wrap_status_t et_can_wrap_clear_irq(et_can_id_t id, uint32_t sources)
{
    CAN_Type *instance = find_instance(id);

    if ((sources & ~ET_CAN_IRQ_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (instance == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    CAN_clearIntrStatus(instance, translate_irq_events(sources, 1u));

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Resolve one controller-local line to its private physical IRQ route.
 * @param[in] id Logical controller identity.
 * @param[in] line Stable controller-local line selector.
 * @param[in] events Nonzero public events owned by this route.
 * @param[out] route Route consumed only by Service-to-IRQ-Manager binding.
 * @return OK, INVALID_ARGUMENT or NOT_SUPPORTED.
 * @note No source, ILE or NVIC state is changed and no physical IRQ is exposed to PC.
 */
et_wrap_status_t et_can_wrap_get_irq_route(et_can_id_t id, et_can_irq_line_t line, uint32_t events,
                                           et_irq_route_t *route)
{
    const et_can_mapping_t *mapping = find_mapping(id);

    if ((route == NULL) || (line >= ET_CAN_IRQ_LINE_COUNT) || (events == 0u) ||
        ((events & ~ET_CAN_IRQ_ALL) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (mapping == NULL)
    {
        return ET_WRAP_STATUS_NOT_SUPPORTED;
    }

    route->irq_line = mapping->irq_lines[line];
    route->reserved = 0u;
    route->route_events = events;

    return ET_WRAP_STATUS_OK;
}
