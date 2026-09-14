/** @file et_can_service.c @brief Decode bounded CAN actions and return raw facts. */
#include "et_can_service.h"
#include <limits.h>
#include <stddef.h>
#include <string.h>

/**
 * @brief Translate a CAN Wrap result to the existing ET status vocabulary.
 * @param[in] status Result of the requested primitive.
 * @return Existing protocol status; unmet initialization precondition is BUSY.
 * @note No retry, reset or recovery is hidden in error conversion.
 */
static uint16_t status_from_wrap(et_wrap_status_t status)
{
    switch (status)
    {
        case ET_WRAP_STATUS_OK:
        {
            return ET_STATUS_OK;
        }

        case ET_WRAP_STATUS_INVALID_ARGUMENT:
        {
            return ET_STATUS_INVALID_PARAM;
        }

        case ET_WRAP_STATUS_NOT_SUPPORTED:
        {
            return ET_STATUS_NOT_SUPPORTED;
        }

        case ET_WRAP_STATUS_STATE_ERROR:
        case ET_WRAP_STATUS_BUSY:
        {
            return ET_STATUS_BUSY;
        }

        default:
        {
            return ET_STATUS_INTERNAL_ERROR;
        }
    }
}

/**
 * @brief Decode one little-endian word without aligned pointer casts.
 * @param[in] data Four validated request bytes.
 * @return Unsigned decoded field.
 * @note Pure codec, called after exact body length validation.
 */
static uint32_t read_word(const uint8_t *data)
{
    uint32_t value = 0u;
    uint16_t index;

    for (index = 0u; index < ET_CAN_WIRE_WORD_BYTES; ++index)
    {
        value |= (uint32_t)data[index] << (index * CHAR_BIT);
    }

    return value;
}

/**
 * @brief Encode one little-endian word without depending on host structure layout.
 * @param[out] data Four validated response bytes.
 * @param[in] value Actual field value.
 * @note Does not access hardware or interpret register meanings.
 */
static void write_word(uint8_t *data, uint32_t value)
{
    uint16_t index;

    for (index = 0u; index < ET_CAN_WIRE_WORD_BYTES; ++index)
    {
        data[index] = (uint8_t)(value >> (index * CHAR_BIT));
    }
}

/********************************** IRQ Capture Management **********************************/

/**
 * @brief Copy or reset the independent DMU evidence generation.
 * @param[in,out] service DMU session owner.
 * @param[in] reset Nonzero resets evidence only while unbound.
 * @param[out] words Nine-word output, unused for reset.
 * @return OK, BUSY or generation overflow failure.
 * @note Bounded critical section protects ISR-owned fields; no peripheral writes.
 */
static et_wrap_status_t dmu_event_access(et_can_service_t *service, uint8_t reset, uint32_t *words)
{
    uint32_t key = et_irq_manager_enter_critical();
    uint32_t index;

    if (reset != 0u)
    {
        if (service->dmu_bound != 0u ||
            service->dmu_event[ET_CAN_IRQ_EVENT_GENERATION] == UINT32_MAX)
        {
            et_irq_manager_exit_critical(key);

            return service->dmu_bound != 0u ? ET_WRAP_STATUS_BUSY : ET_WRAP_STATUS_IO_ERROR;
        }

        ++service->dmu_event[ET_CAN_IRQ_EVENT_GENERATION];

        for (index = 0u; index < ET_CAN_DMU_EVENT_WORDS; ++index)
        {
            if (index != ET_CAN_IRQ_EVENT_GENERATION)
            {
                service->dmu_event[index] = 0u;
            }
        }

        service->dmu_event[ET_CAN_DMU_EVENT_INSTANCE] = UINT32_MAX;
    }
    else
    {
        for (index = 0u; index < ET_CAN_DMU_EVENT_WORDS; ++index)
        {
            words[index] = service->dmu_event[index];
        }
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Saturate an DMU counter and retain overflow diagnostics.
 * @param[in,out] service DMU evidence owner.
 * @param[in] field Counter index in the fixed evidence array.
 * @note Called only in bounded IRQ context; does not affect controller IRQ evidence.
 */
static void increment_dmu_counter(et_can_service_t *service, uint32_t field)
{
    if (service->dmu_event[field] != UINT32_MAX)
    {
        ++service->dmu_event[field];

        return;
    }

    service->dmu_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_OVERFLOW;

    if (service->dmu_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT] != UINT32_MAX)
    {
        ++service->dmu_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT];
    }
}

/**
 * @brief Preserve the first read-clearing DMU error observation on the real DMU IRQ.
 * @param[in,out] context Owning CAN Service.
 * @param[in] irq_line Actual dispatched line.
 * @param[in] route_events Registered public error sources.
 * @note Reads enables before consuming DMUIR once, then disables delivered sources.
 */
static void can_dmu_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_can_service_t *service = (et_can_service_t *)context;
    et_can_dmu_status_t snapshot;
    uint32_t enabled, active, watched;

    if (service == NULL || service->dmu_bound == 0u)
    {
        return;
    }

    if (et_can_wrap_get_dmu_irq(service->can_id, &enabled) != ET_WRAP_STATUS_OK ||
        et_can_wrap_consume_dmu_status(service->can_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        service->dmu_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
        (void)et_can_wrap_set_dmu_irq(service->can_id, ET_CAN_DMU_ERROR_ALL, 0u);

        return;
    }

    active = snapshot.errors & enabled;

    if (active == 0u)
    {
        return;
    }

    watched = active & route_events & service->dmu_watched;

    if (irq_line != service->dmu_route.irq_line || active != watched)
    {
        increment_dmu_counter(service, ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT);
        service->dmu_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_UNEXPECTED;
    }

    if (watched != 0u && irq_line == service->dmu_route.irq_line)
    {
        if (service->dmu_event[ET_CAN_IRQ_EVENT_COUNT] == 0u)
        {
            service->dmu_event[ET_CAN_IRQ_EVENT_RAW_STATUS] = snapshot.errors;
            service->dmu_event[ET_CAN_IRQ_EVENT_MASKED_STATUS] = active;
        }

        service->dmu_event[ET_CAN_IRQ_EVENT_LATCHED_EVENTS] |= watched;
        service->dmu_event[ET_CAN_DMU_EVENT_INSTANCE] = service->can_id;
        increment_dmu_counter(service, ET_CAN_IRQ_EVENT_COUNT);
    }

    if (et_can_wrap_set_dmu_irq(service->can_id, active, 0u) != ET_WRAP_STATUS_OK)
    {
        service->dmu_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
    }
}

/**
 * @brief Observe whether a failed bind retained this exact DMU ownership record.
 * @param[in] service DMU session whose bind returned an error.
 * @return Nonzero only when Manager still owns this callback, context and line.
 * @note Read-only bounded inspection of public Manager storage under its critical section;
 *       never edits bindings or performs physical IRQ cleanup outside Manager.
 */
static uint8_t dmu_binding_retained(const et_can_service_t *service)
{
    uint32_t key = et_irq_manager_enter_critical();
    uint32_t index;
    uint8_t retained = 0u;

    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        const et_irq_binding_t *binding = &service->irq_manager->bindings[index];

        if (binding->in_use != 0u && binding->callback == can_dmu_callback &&
            binding->context == service && binding->irq_line == service->dmu_route.irq_line)
        {
            retained = 1u;
            break;
        }
    }

    et_irq_manager_exit_critical(key);

    return retained;
}

/**
 * @brief Disable owned DMU sources before releasing the independent IRQ route.
 * @param[in,out] service Session owner.
 * @return OK or shutdown failure; failed cleanup retains ownership for retry.
 * @note Does not consume raw errors or erase captured evidence.
 */
static et_wrap_status_t stop_dmu_capture(et_can_service_t *service)
{
    if (service->dmu_watched == 0u)
    {
        return ET_WRAP_STATUS_OK;
    }

    if (et_can_wrap_set_dmu_irq(service->can_id, service->dmu_watched, 0u) != ET_WRAP_STATUS_OK ||
        (service->dmu_bound != 0u &&
         et_irq_manager_unbind(service->irq_manager, service->dmu_route.irq_line, can_dmu_callback,
                               service) != 0))
    {
        service->dmu_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;

        return ET_WRAP_STATUS_IO_ERROR;
    }

    service->dmu_bound = 0u;
    service->dmu_watched = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Start one fresh DMU error capture, rejecting stale raw errors.
 * @param[in,out] service Session owner.
 * @param[in] sources Nonempty public error mask.
 * @return OK, invalid mask, stale/busy state or setup failure.
 * @note No speculative W1C: one pre-bind consuming read must show zero errors.
 */
static et_wrap_status_t start_dmu_capture(et_can_service_t *service, uint32_t sources)
{
    et_wrap_status_t status;
    et_can_dmu_status_t raw;
    uint32_t enabled;

    if (service->dmu_bound != 0u || service->dmu_watched != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    status = et_can_wrap_get_dmu_route(service->can_id, sources, &service->dmu_route);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = et_can_wrap_get_dmu_irq(service->can_id, &enabled);

    if (status != ET_WRAP_STATUS_OK || enabled != 0u)
    {
        return status != ET_WRAP_STATUS_OK ? status : ET_WRAP_STATUS_BUSY;
    }

    status = et_can_wrap_consume_dmu_status(service->can_id, &raw);

    if (status != ET_WRAP_STATUS_OK || raw.errors != 0u)
    {
        return status != ET_WRAP_STATUS_OK ? status : ET_WRAP_STATUS_BUSY;
    }

    status = dmu_event_access(service, 1u, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    service->dmu_watched = sources;
    service->dmu_bound = 1u;

    if (et_irq_manager_bind(service->irq_manager, &service->dmu_route, service->irq_priority,
                            can_dmu_callback, service) != 0)
    {
        service->dmu_bound = dmu_binding_retained(service);
        status = ET_WRAP_STATUS_IO_ERROR;
    }
    else
    {
        status = et_can_wrap_set_dmu_irq(service->can_id, sources, 1u);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)stop_dmu_capture(service);
    }

    return status;
}

/**
 * @brief Execute one bounded DMU test access or independent IRQ session action.
 * @param[in,out] service Selected controller session.
 * @param[in] command Validated command ID.
 * @param[in] body Exact-length request.
 * @param[out] response Capacity-checked response.
 * @return Own Wrap or session status.
 * @note ISR evidence reads never re-read DMUIR, preserving its first decisive value.
 */
static et_wrap_status_t execute_dmu_test_command(et_can_service_t *service, uint16_t command,
                                                 const uint8_t *body, uint8_t *response)
{
    uint32_t words[ET_CAN_DMU_EVENT_WORDS], value, write, index;
    et_wrap_status_t status;

    switch (command)
    {
        case ET_CAN_COMMAND_DMU_WORD_ACCESS:
        {
            write = read_word(&body[ET_CAN_DMU_ACCESS_WRITE * ET_CAN_WIRE_WORD_BYTES]);
            value = read_word(&body[ET_CAN_DMU_ACCESS_VALUE * ET_CAN_WIRE_WORD_BYTES]);

            if (write > 1u || (write == 0u && value != 0u))
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            status = et_can_wrap_access_dmu_word(
                service->can_id, (et_can_dmu_element_t)read_word(body),
                read_word(&body[ET_CAN_DMU_ACCESS_WORD_INDEX * ET_CAN_WIRE_WORD_BYTES]),
                (uint8_t)write, &value);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, value);
            }

            return status;
        }

        case ET_CAN_COMMAND_DMU_CAPTURE_START:
        {
            return start_dmu_capture(service, read_word(body));
        }

        case ET_CAN_COMMAND_DMU_CAPTURE_STOP:
        {
            return stop_dmu_capture(service);
        }

        default:
        {
            status = dmu_event_access(service, 0u, words);

            if (status == ET_WRAP_STATUS_OK)
            {
                for (index = 0u; index < ET_CAN_DMU_EVENT_WORDS; ++index)
                {
                    write_word(&response[index * ET_CAN_WIRE_WORD_BYTES], words[index]);
                }
            }

            return status;
        }
    }
}

/**
 * @brief Copy or reset the independent ECC evidence generation.
 * @param[in,out] service ECC session owner.
 * @param[in] reset Nonzero resets evidence only while unbound.
 * @param[out] words Nine-word output, unused for reset.
 * @return OK, BUSY or generation overflow failure.
 * @note Bounded critical section protects ISR-owned fields; no peripheral writes.
 */
static et_wrap_status_t ecc_event_access(et_can_service_t *service, uint8_t reset, uint32_t *words)
{
    uint32_t key = et_irq_manager_enter_critical();
    uint32_t index;

    if (reset != 0u)
    {
        if (service->ecc_bound != 0u ||
            service->ecc_event[ET_CAN_IRQ_EVENT_GENERATION] == UINT32_MAX)
        {
            et_irq_manager_exit_critical(key);

            return service->ecc_bound != 0u ? ET_WRAP_STATUS_BUSY : ET_WRAP_STATUS_IO_ERROR;
        }

        ++service->ecc_event[ET_CAN_IRQ_EVENT_GENERATION];

        for (index = 0u; index < ET_CAN_ECC_EVENT_WORDS; ++index)
        {
            if (index != ET_CAN_IRQ_EVENT_GENERATION)
            {
                service->ecc_event[index] = 0u;
            }
        }

        service->ecc_event[ET_CAN_ECC_EVENT_INSTANCE] = UINT32_MAX;
    }
    else
    {
        for (index = 0u; index < ET_CAN_ECC_EVENT_WORDS; ++index)
        {
            words[index] = service->ecc_event[index];
        }
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Saturate an ECC counter and retain overflow diagnostics.
 * @param[in,out] service ECC evidence owner.
 * @param[in] field Counter index in the fixed evidence array.
 * @note Called only in bounded IRQ context; does not affect controller IRQ evidence.
 */
static void increment_ecc_counter(et_can_service_t *service, uint32_t field)
{
    if (service->ecc_event[field] != UINT32_MAX)
    {
        ++service->ecc_event[field];

        return;
    }

    service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_OVERFLOW;

    if (service->ecc_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT] != UINT32_MAX)
    {
        ++service->ecc_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT];
    }
}

/**
 * @brief Capture this instance's actual ECC sources on a possibly shared IRQ.
 * @param[in,out] context CAN Service owning the registered route.
 * @param[in] irq_line Physical line dispatched by IRQ Manager.
 * @param[in] route_events ECC sources assigned to this session.
 * @note Bounded ISR reads own status and masks active sources; raw remains for explicit PC clear.
 */
static void can_ecc_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_can_service_t *service = (et_can_service_t *)context;
    et_can_ecc_snapshot_t snapshot;
    uint32_t active, watched;

    if (service == NULL || service->ecc_bound == 0u)
    {
        return;
    }

    /* Phase 1: Shared-line dispatch is not itself evidence of a local ECC event. */
    if (et_can_wrap_get_ecc_snapshot(service->can_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
        (void)et_can_wrap_set_ecc_masked(service->can_id, ET_CAN_ECC_ALL, 1u);

        return;
    }

    active = snapshot.raw & snapshot.status & snapshot.enabled & ~snapshot.masked;

    if (active == 0u)
    {
        return;
    }

    watched = active & route_events & service->ecc_watched;

    if (irq_line != service->ecc_route.irq_line || active != watched)
    {
        increment_ecc_counter(service, ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT);
        service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_UNEXPECTED;
    }

    /* Phase 2: Preserve first raw/status, accumulate real events and suppress a level storm. */
    if (watched != 0u && irq_line == service->ecc_route.irq_line)
    {
        if (service->ecc_event[ET_CAN_IRQ_EVENT_COUNT] == 0u)
        {
            service->ecc_event[ET_CAN_IRQ_EVENT_RAW_STATUS] = snapshot.raw;
            service->ecc_event[ET_CAN_IRQ_EVENT_MASKED_STATUS] = snapshot.status;
        }

        service->ecc_event[ET_CAN_IRQ_EVENT_LATCHED_EVENTS] |= watched;
        service->ecc_event[ET_CAN_ECC_EVENT_INSTANCE] = service->can_id;
        increment_ecc_counter(service, ET_CAN_IRQ_EVENT_COUNT);
    }

    if (et_can_wrap_set_ecc_masked(service->can_id, active, 1u) != ET_WRAP_STATUS_OK)
    {
        service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
    }
}

/**
 * @brief Observe whether a failed bind retained this exact ECC ownership record.
 * @param[in] service ECC session whose bind returned an error.
 * @return Nonzero only when Manager still owns this callback, context and line.
 * @note Read-only bounded inspection of public Manager storage under its critical section;
 *       never edits bindings or performs physical IRQ cleanup outside Manager.
 */
static uint8_t ecc_binding_retained(const et_can_service_t *service)
{
    uint32_t key = et_irq_manager_enter_critical();
    uint32_t index;
    uint8_t retained = 0u;

    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        const et_irq_binding_t *binding = &service->irq_manager->bindings[index];

        if (binding->in_use != 0u && binding->callback == can_ecc_callback &&
            binding->context == service && binding->irq_line == service->ecc_route.irq_line)
        {
            retained = 1u;
            break;
        }
    }

    et_irq_manager_exit_critical(key);

    return retained;
}

/**
 * @brief Disable ECC sources before releasing the owned shared-line route.
 * @param[in,out] service ECC session owner.
 * @return OK or cleanup failure, retaining ownership for retry on failure.
 * @note Raw and callback evidence are retained; a failed source shutdown prevents unbinding.
 */
static et_wrap_status_t stop_ecc_capture(et_can_service_t *service)
{
    et_wrap_status_t masked, disabled;

    if (service->ecc_watched == 0u)
    {
        return ET_WRAP_STATUS_OK;
    }

    masked = et_can_wrap_set_ecc_masked(service->can_id, service->ecc_watched, 1u);
    disabled = et_can_wrap_set_ecc_enabled(service->can_id, service->ecc_watched, 0u);

    if (masked != ET_WRAP_STATUS_OK || disabled != ET_WRAP_STATUS_OK)
    {
        service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;

        return ET_WRAP_STATUS_IO_ERROR;
    }

    if (service->ecc_bound != 0u &&
        et_irq_manager_unbind(service->irq_manager, service->ecc_route.irq_line, can_ecc_callback,
                              service) != 0)
    {
        service->ecc_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;

        return ET_WRAP_STATUS_IO_ERROR;
    }

    service->ecc_bound = 0u;
    service->ecc_watched = 0u;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Start a fresh ECC capture with selected sources enabled but still masked.
 * @param[in,out] service CAN Service session owner.
 * @param[in] sources Nonempty public ECC sources.
 * @return OK or setup/rollback failure.
 * @note Clear stale watched raw before binding; PC must explicitly unmask for delivery.
 */
static et_wrap_status_t start_ecc_capture(et_can_service_t *service, uint32_t sources)
{
    et_wrap_status_t status;

    if (sources == 0u || (sources & ~ET_CAN_ECC_ALL) != 0u)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (service->ecc_bound != 0u || service->ecc_watched != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    /* Phase 1: Resolve facts and empty evidence before changing any source. */
    status = et_can_wrap_get_ecc_route(service->can_id, sources, &service->ecc_route);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = ecc_event_access(service, 1u, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    service->ecc_watched = sources;
    status = et_can_wrap_set_ecc_masked(service->can_id, sources, 1u);

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_set_ecc_enabled(service->can_id, sources, 0u);
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_clear_ecc(service->can_id, sources);
    }

    /* Phase 2: Preserve ownership even if Manager bind leaves a cleanup-pending slot. */
    if (status == ET_WRAP_STATUS_OK)
    {
        service->ecc_bound = 1u;

        if (et_irq_manager_bind(service->irq_manager, &service->ecc_route, service->irq_priority,
                                can_ecc_callback, service) != 0)
        {
            service->ecc_bound = ecc_binding_retained(service);
            status = ET_WRAP_STATUS_IO_ERROR;
        }
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_set_ecc_enabled(service->can_id, sources, 1u);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)stop_ecc_capture(service);
    }

    return status;
}

/**
 * @brief Execute exactly one validated ECC control or evidence operation.
 * @param[in,out] service Selected CAN Service.
 * @param[in] command Public ECC command ID.
 * @param[in] body Exact-length request words.
 * @param[out] response Capacity-validated output storage.
 * @return Own Wrap or session status.
 * @note No polling, stimulus sequence, RAM injection or final test decision.
 */
static et_wrap_status_t execute_ecc_command(et_can_service_t *service, uint16_t command,
                                            const uint8_t *body, uint8_t *response)
{
    uint32_t sources, value, index;
    uint32_t words[ET_CAN_ECC_EVENT_WORDS];
    et_can_ecc_snapshot_t snapshot;
    et_wrap_status_t status;

    /* Phase 1: Decode independent mutations; Boolean validation precedes narrowing. */
    switch (command)
    {
        case ET_CAN_COMMAND_ECC_ENABLE_SET:
        case ET_CAN_COMMAND_ECC_MASK_SET:
        {
            sources = read_word(body);
            value = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (value > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return command == ET_CAN_COMMAND_ECC_ENABLE_SET
                       ? et_can_wrap_set_ecc_enabled(service->can_id, sources, (uint8_t)value)
                       : et_can_wrap_set_ecc_masked(service->can_id, sources, (uint8_t)value);
        }

        case ET_CAN_COMMAND_ECC_FORCE:
        {
            return et_can_wrap_force_ecc(service->can_id, read_word(body));
        }

        case ET_CAN_COMMAND_ECC_CLEAR:
        {
            return et_can_wrap_clear_ecc(service->can_id, read_word(body));
        }

        case ET_CAN_COMMAND_ECC_CAPTURE_START:
        {
            return start_ecc_capture(service, read_word(body));
        }

        case ET_CAN_COMMAND_ECC_CAPTURE_STOP:
        {
            return stop_ecc_capture(service);
        }

        case ET_CAN_COMMAND_ECC_EVENT_RESET:
        {
            return ecc_event_access(service, 1u, NULL);
        }

        default:
        {
            break;
        }
    }

    /* Phase 2: Encode actual facts only after a successful snapshot operation. */
    if (command == ET_CAN_COMMAND_ECC_SNAPSHOT_GET)
    {
        status = et_can_wrap_get_ecc_snapshot(service->can_id, &snapshot);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_ECC_RAW * ET_CAN_WIRE_WORD_BYTES], snapshot.raw);
            write_word(&response[ET_CAN_ECC_STATUS * ET_CAN_WIRE_WORD_BYTES], snapshot.status);
            write_word(&response[ET_CAN_ECC_ENABLED * ET_CAN_WIRE_WORD_BYTES], snapshot.enabled);
            write_word(&response[ET_CAN_ECC_MASKED * ET_CAN_WIRE_WORD_BYTES], snapshot.masked);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_ECC_EVENT_GET)
    {
        status = ecc_event_access(service, 0u, words);

        if (status == ET_WRAP_STATUS_OK)
        {
            for (index = 0u; index < ET_CAN_ECC_EVENT_WORDS; ++index)
            {
                write_word(&response[index * ET_CAN_WIRE_WORD_BYTES], words[index]);
            }
        }

        return status;
    }

    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

/**
 * @brief Saturate one callback-owned counter and preserve overflow evidence.
 * @param[in,out] service CAN Service that owns the fixed event snapshot.
 * @param[in,out] counter Counter to increment.
 * @note Called only from IRQ context or an IRQ Manager critical section.
 */
static void increment_irq_counter(et_can_service_t *service, volatile uint32_t *counter)
{
    if (*counter != UINT32_MAX)
    {
        ++*counter;

        return;
    }

    service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_OVERFLOW;

    if (service->irq_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT] != UINT32_MAX)
    {
        ++service->irq_event[ET_CAN_IRQ_EVENT_OVERFLOW_COUNT];
    }
}

/**
 * @brief Copy or reset fixed CAN IRQ evidence under one short critical section.
 * @param[in,out] service CAN Service evidence owner.
 * @param[in] reset Nonzero starts a new empty generation while no route is bound.
 * @param[out] words Eight output words for a read; unused for reset.
 * @return OK, BUSY, INVALID_ARGUMENT or IO_ERROR.
 * @note Reset changes Service storage only; CAN pending state is cleared by a separate command.
 */
static et_wrap_status_t irq_event_access(et_can_service_t *service, uint8_t reset, uint32_t *words)
{
    uint32_t key;
    uint16_t index;

    if ((service == NULL) || ((reset == 0u) && (words == NULL)))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((reset != 0u) && (service->bound_lines != 0u))
    {
        return ET_WRAP_STATUS_BUSY;
    }

    key = et_irq_manager_enter_critical();

    if (reset != 0u)
    {
        if (service->irq_event[ET_CAN_IRQ_EVENT_GENERATION] == UINT32_MAX)
        {
            et_irq_manager_exit_critical(key);

            return ET_WRAP_STATUS_IO_ERROR;
        }

        ++service->irq_event[ET_CAN_IRQ_EVENT_GENERATION];
        service->irq_line_events[ET_CAN_IRQ_LINE0] = 0u;
        service->irq_line_events[ET_CAN_IRQ_LINE1] = 0u;

        for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
        {
            if (index != ET_CAN_IRQ_EVENT_GENERATION)
            {
                service->irq_event[index] = 0u;
            }
        }
    }
    else
    {
        for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
        {
            words[index] = service->irq_event[index];
        }
    }

    et_irq_manager_exit_critical(key);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Capture one bounded CAN interrupt observation and suppress active sources.
 * @param[in,out] context CAN Service registered with IRQ Manager.
 * @param[in] irq_line Physical line delivered by IRQ Manager.
 * @param[in] route_events Public source subset assigned to this route.
 * @note ISR work is fixed: one snapshot, fixed counters and one source-mask operation.
 */
static void can_irq_callback(void *context, et_irq_line_t irq_line, uint32_t route_events)
{
    et_can_service_t *service = (et_can_service_t *)context;
    et_can_irq_snapshot_t snapshot;
    uint32_t active;

    if ((service == NULL) || (service->bound_lines == 0u))
    {
        return;
    }

    if (et_can_wrap_get_irq_snapshot(service->can_id, &snapshot) != ET_WRAP_STATUS_OK)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
        (void)et_can_wrap_set_irq_enabled(service->can_id, service->watched_sources, 0u);

        return;
    }

    active =
        snapshot.raw_status & snapshot.enabled_sources & route_events & service->watched_sources;

    if (active == 0u)
    {
        return;
    }

    /* Preserve the first raw/masked view and accumulate every observed semantic source. */
    if (service->irq_event[ET_CAN_IRQ_EVENT_COUNT] == 0u)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_RAW_STATUS] = snapshot.raw_status;
        service->irq_event[ET_CAN_IRQ_EVENT_MASKED_STATUS] = active;
    }

    service->irq_event[ET_CAN_IRQ_EVENT_LATCHED_EVENTS] |= active;
    increment_irq_counter(service, &service->irq_event[ET_CAN_IRQ_EVENT_COUNT]);

    /* Attribute sources to the delivered physical line, not merely to the requested ILS value. */
    if (irq_line == service->irq_routes[ET_CAN_IRQ_LINE0].irq_line)
    {
        service->irq_line_events[ET_CAN_IRQ_LINE0] |= active;
    }

    if (irq_line == service->irq_routes[ET_CAN_IRQ_LINE1].irq_line)
    {
        service->irq_line_events[ET_CAN_IRQ_LINE1] |= active;
    }

    /* active already excludes sources outside route_events; only the physical line is checked here. */
    if ((irq_line != service->irq_routes[ET_CAN_IRQ_LINE0].irq_line) &&
        (irq_line != service->irq_routes[ET_CAN_IRQ_LINE1].irq_line))
    {
        increment_irq_counter(service, &service->irq_event[ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT]);
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_UNEXPECTED;
    }

    /* A pending level remains visible for explicit PC clear, while masking prevents an IRQ storm. */
    if (et_can_wrap_set_irq_enabled(service->can_id, active, 0u) != ET_WRAP_STATUS_OK)
    {
        service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
    }
}

/**
 * @brief Stop a managed CAN IRQ capture in source-before-route order.
 * @param[in,out] service CAN Service that owns the active session.
 * @return OK or the first cleanup failure.
 * @note Evidence is retained. Ownership is cleared only after both physical routes are released.
 */
static et_wrap_status_t stop_irq_capture(et_can_service_t *service)
{
    et_wrap_status_t result = ET_WRAP_STATUS_OK;
    et_can_irq_line_t line;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (et_can_wrap_set_irq_enabled(service->can_id, service->watched_sources, 0u) !=
        ET_WRAP_STATUS_OK)
    {
        result = ET_WRAP_STATUS_IO_ERROR;
    }

    for (line = ET_CAN_IRQ_LINE0; line < ET_CAN_IRQ_LINE_COUNT; ++line)
    {
        uint8_t line_bit = (uint8_t)(1u << line);

        if ((service->bound_lines & line_bit) == 0u)
        {
            continue;
        }

        if (et_can_wrap_set_irq_line_enabled(service->can_id, line, 0u) != ET_WRAP_STATUS_OK)
        {
            result = ET_WRAP_STATUS_IO_ERROR;
        }

        if (et_irq_manager_unbind(service->irq_manager, service->irq_routes[line].irq_line,
                                  can_irq_callback, service) != 0)
        {
            service->irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] |= ET_CAN_IRQ_FAULT_IO;
            result = ET_WRAP_STATUS_IO_ERROR;
        }
        else
        {
            service->bound_lines &= (uint8_t)~line_bit;
        }
    }

    if (service->bound_lines == 0u)
    {
        service->watched_sources = 0u;
        service->line1_sources = 0u;
    }

    return result;
}

/**
 * @brief Start one explicit CAN interrupt capture using up to two routed lines.
 * @param[in,out] service CAN Service that owns the session.
 * @param[in] sources Nonzero public source mask.
 * @param[in] line1_sources Subset of sources routed to controller line 1.
 * @param[in] clear_pending Clear old Raw for a fresh session, or preserve it for pending delivery.
 * @return OK or the exact setup/rollback failure.
 * @note Setup order is clear, select, bind, line-enable, source-enable; rollback is reversed.
 */
static et_wrap_status_t start_irq_capture(et_can_service_t *service, uint32_t sources,
                                          uint32_t line1_sources, uint8_t clear_pending)
{
    uint32_t route_events[ET_CAN_IRQ_LINE_COUNT];
    et_can_irq_line_t line;
    et_wrap_status_t status;

    if ((service == NULL) || (sources == 0u) || ((sources & ~ET_CAN_IRQ_ALL) != 0u) ||
        ((line1_sources & ~sources) != 0u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (service->bound_lines != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    /* Phase 1: Validate software ownership and start a new empty evidence generation. */
    status = irq_event_access(service, 1u, NULL);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    route_events[ET_CAN_IRQ_LINE0] = sources & ~line1_sources;
    route_events[ET_CAN_IRQ_LINE1] = line1_sources;
    service->watched_sources = sources;
    service->line1_sources = line1_sources;

    /* Phase 2: Clear stale state and publish the complete line selection before any route can fire. */
    status = et_can_wrap_set_irq_enabled(service->can_id, sources, 0u);

    if ((status == ET_WRAP_STATUS_OK) && (clear_pending != 0u))
    {
        status = et_can_wrap_clear_irq(service->can_id, sources);
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        status = et_can_wrap_select_irq_line(service->can_id, sources, ET_CAN_IRQ_LINE0);
    }

    if ((status == ET_WRAP_STATUS_OK) && (line1_sources != 0u))
    {
        status = et_can_wrap_select_irq_line(service->can_id, line1_sources, ET_CAN_IRQ_LINE1);
    }

    if (status != ET_WRAP_STATUS_OK)
    {
        service->watched_sources = 0u;
        service->line1_sources = 0u;

        return status;
    }

    /* Phase 3: Bind and enable only lines that own at least one requested semantic source. */
    for (line = ET_CAN_IRQ_LINE0; line < ET_CAN_IRQ_LINE_COUNT; ++line)
    {
        uint8_t line_bit = (uint8_t)(1u << line);

        if (route_events[line] == 0u)
        {
            continue;
        }

        status = et_can_wrap_get_irq_route(service->can_id, line, route_events[line],
                                           &service->irq_routes[line]);

        if ((status != ET_WRAP_STATUS_OK) ||
            (et_irq_manager_bind(service->irq_manager, &service->irq_routes[line],
                                 service->irq_priority, can_irq_callback, service) != 0))
        {
            (void)stop_irq_capture(service);

            return status == ET_WRAP_STATUS_OK ? ET_WRAP_STATUS_IO_ERROR : status;
        }

        service->bound_lines |= line_bit;
        status = et_can_wrap_set_irq_line_enabled(service->can_id, line, 1u);

        if (status != ET_WRAP_STATUS_OK)
        {
            (void)stop_irq_capture(service);

            return status;
        }
    }

    /* Phase 4: Expose peripheral sources only after every required route is operational. */
    status = et_can_wrap_set_irq_enabled(service->can_id, sources, 1u);

    if (status != ET_WRAP_STATUS_OK)
    {
        (void)stop_irq_capture(service);
    }

    return status;
}

/**
 * @brief Execute CAN interrupt configuration, observation and managed-capture commands.
 * @param[in,out] service CAN Service selected by the request prefix.
 * @param[in] command Validated IRQ command.
 * @param[in] body Validated request words after the instance prefix.
 * @param[out] response Capacity-checked response storage when required.
 * @return Own Wrap or IRQ-session result.
 * @note No test stimulus, polling or PASS/FAIL decision is hidden here.
 */
static et_wrap_status_t execute_irq_command(et_can_service_t *service, uint16_t command,
                                            const uint8_t *body, uint8_t *response)
{
    et_can_irq_snapshot_t snapshot;
    et_wrap_status_t status;
    uint32_t words[ET_CAN_IRQ_EVENT_WORDS];
    uint32_t sources;
    uint32_t value;
    uint16_t index;
    uint32_t key;

    /* Phase 1: Route direct source/line controls while no managed capture owns them. */
    switch (command)
    {
        case ET_CAN_COMMAND_IRQ_MASK_SET:
        {
            sources = read_word(body);
            value = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (value > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            if (service->bound_lines != 0u)
            {
                return ET_WRAP_STATUS_BUSY;
            }

            return et_can_wrap_set_irq_enabled(service->can_id, sources, (uint8_t)value);
        }

        case ET_CAN_COMMAND_IRQ_LINE_SELECT_SET:
        {
            sources = read_word(body);
            value = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (value >= ET_CAN_IRQ_LINE_COUNT)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            if (service->bound_lines != 0u)
            {
                return ET_WRAP_STATUS_BUSY;
            }

            return et_can_wrap_select_irq_line(service->can_id, sources, (et_can_irq_line_t)value);
        }

        case ET_CAN_COMMAND_IRQ_SNAPSHOT_GET:
        {
            /* Phase 2: Return a non-destructive hardware view independent of callback evidence. */
            status = et_can_wrap_get_irq_snapshot(service->can_id, &snapshot);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_RAW * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.raw_status);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.enabled_sources);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_LINE1 * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.line1_sources);
                write_word(&response[ET_CAN_IRQ_SNAPSHOT_LINES_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           snapshot.enabled_lines);
            }

            return status;
        }

        case ET_CAN_COMMAND_IRQ_CLEAR:
        {
            return et_can_wrap_clear_irq(service->can_id, read_word(body));
        }

        case ET_CAN_COMMAND_IRQ_CAPTURE_START:
        {
            return start_irq_capture(service, read_word(body),
                                     read_word(&body[ET_CAN_WIRE_WORD_BYTES]), 1u);
        }

        case ET_CAN_COMMAND_IRQ_CAPTURE_PENDING:
        {
            /* Bind before unmasking; retain Raw so the hardware can deliver existing events. */
            return start_irq_capture(service, read_word(body),
                                     read_word(&body[ET_CAN_WIRE_WORD_BYTES]), 0u);
        }

        case ET_CAN_COMMAND_IRQ_LINE_EVENTS_GET:
        {
            key = et_irq_manager_enter_critical();

            for (index = 0u; index < ET_CAN_IRQ_LINE_COUNT; ++index)
            {
                write_word(&response[index * ET_CAN_WIRE_WORD_BYTES],
                           service->irq_line_events[index]);
            }

            et_irq_manager_exit_critical(key);

            return ET_WRAP_STATUS_OK;
        }

        case ET_CAN_COMMAND_IRQ_CAPTURE_STOP:
        {
            return stop_irq_capture(service);
        }

        case ET_CAN_COMMAND_IRQ_EVENT_GET:
        {
            /* Phase 3: Copy only fixed Service evidence under its IRQ critical section. */
            status = irq_event_access(service, 0u, words);

            if (status == ET_WRAP_STATUS_OK)
            {
                for (index = 0u; index < ET_CAN_IRQ_EVENT_WORDS; ++index)
                {
                    write_word(&response[index * ET_CAN_WIRE_WORD_BYTES], words[index]);
                }
            }

            return status;
        }

        case ET_CAN_COMMAND_IRQ_EVENT_RESET:
        {
            return irq_event_access(service, 1u, NULL);
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Decode the four named physical timing counts of one CAN phase.
 * @param[in] body Validated phase payload.
 * @param[out] phase Public configuration, with no chip encodings.
 * @note Only copies PC parameters; it does not select a bitrate or defaults.
 */
static void decode_phase(const uint8_t *body, et_can_bit_timing_t *phase)
{
    phase->prescaler = read_word(&body[ET_CAN_TIMING_PRESCALER * ET_CAN_WIRE_WORD_BYTES]);
    phase->segment1 = read_word(&body[ET_CAN_TIMING_SEGMENT1 * ET_CAN_WIRE_WORD_BYTES]);
    phase->segment2 = read_word(&body[ET_CAN_TIMING_SEGMENT2 * ET_CAN_WIRE_WORD_BYTES]);
    phase->sjw = read_word(&body[ET_CAN_TIMING_SJW * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode one timing phase in the public field order.
 * @param[out] body Validated phase response storage.
 * @param[in] phase Actual readback or declared representable maxima.
 * @note No hidden unit conversion occurs in the Service.
 */
static void encode_phase(uint8_t *body, const et_can_bit_timing_t *phase)
{
    write_word(&body[ET_CAN_TIMING_PRESCALER * ET_CAN_WIRE_WORD_BYTES], phase->prescaler);
    write_word(&body[ET_CAN_TIMING_SEGMENT1 * ET_CAN_WIRE_WORD_BYTES], phase->segment1);
    write_word(&body[ET_CAN_TIMING_SEGMENT2 * ET_CAN_WIRE_WORD_BYTES], phase->segment2);
    write_word(&body[ET_CAN_TIMING_SJW * ET_CAN_WIRE_WORD_BYTES], phase->sjw);
}

/**
 * @brief Decode the complete public core option tuple.
 * @param[in] body Validated option bytes.
 * @param[out] options Caller-owned chip-neutral values.
 * @note No defaults or hardware changes occur in this codec.
 */
static void decode_options(const uint8_t *body, et_can_options_t *options)
{
    options->fd_enabled = read_word(&body[ET_CAN_OPTION_FD * ET_CAN_WIRE_WORD_BYTES]);
    options->brs_enabled = read_word(&body[ET_CAN_OPTION_BRS * ET_CAN_WIRE_WORD_BYTES]);
    options->automatic_retry = read_word(&body[ET_CAN_OPTION_RETRY * ET_CAN_WIRE_WORD_BYTES]);
    options->tx_pause = read_word(&body[ET_CAN_OPTION_TX_PAUSE * ET_CAN_WIRE_WORD_BYTES]);
    options->edge_filter = read_word(&body[ET_CAN_OPTION_EDGE_FILTER * ET_CAN_WIRE_WORD_BYTES]);
    options->protocol_exception =
        read_word(&body[ET_CAN_OPTION_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_enabled = read_word(&body[ET_CAN_OPTION_TDC * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_offset_cycles =
        read_word(&body[ET_CAN_OPTION_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    options->tdc_filter_cycles =
        read_word(&body[ET_CAN_OPTION_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES]);
    options->ram_watchdog_cycles =
        read_word(&body[ET_CAN_OPTION_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode independently observed core options.
 * @param[out] body Validated output storage.
 * @param[in] options Actual hardware readback.
 * @note Pure serialization; bit interpretation belongs to the Driver and Wrap.
 */
static void encode_options(uint8_t *body, const et_can_options_t *options)
{
    write_word(&body[ET_CAN_OPTION_FD * ET_CAN_WIRE_WORD_BYTES], options->fd_enabled);
    write_word(&body[ET_CAN_OPTION_BRS * ET_CAN_WIRE_WORD_BYTES], options->brs_enabled);
    write_word(&body[ET_CAN_OPTION_RETRY * ET_CAN_WIRE_WORD_BYTES], options->automatic_retry);
    write_word(&body[ET_CAN_OPTION_TX_PAUSE * ET_CAN_WIRE_WORD_BYTES], options->tx_pause);
    write_word(&body[ET_CAN_OPTION_EDGE_FILTER * ET_CAN_WIRE_WORD_BYTES], options->edge_filter);
    write_word(&body[ET_CAN_OPTION_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES],
               options->protocol_exception);
    write_word(&body[ET_CAN_OPTION_TDC * ET_CAN_WIRE_WORD_BYTES], options->tdc_enabled);
    write_word(&body[ET_CAN_OPTION_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES],
               options->tdc_offset_cycles);
    write_word(&body[ET_CAN_OPTION_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES],
               options->tdc_filter_cycles);
    write_word(&body[ET_CAN_OPTION_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES],
               options->ram_watchdog_cycles);
}

/**
 * @brief Decode the complete public Message RAM tuple.
 * @param[in] body Validated RAM request bytes.
 * @param[out] layout Explicit region parameters owned by the caller.
 * @note No defaults, allocation or hardware access occur here.
 */
static void decode_ram_layout(const uint8_t *body, et_can_ram_layout_t *layout)
{
    layout->std_offset = read_word(&body[ET_CAN_RAM_STD_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->std_count = read_word(&body[ET_CAN_RAM_STD_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->ext_offset = read_word(&body[ET_CAN_RAM_EXT_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->ext_count = read_word(&body[ET_CAN_RAM_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_offset = read_word(&body[ET_CAN_RAM_TX_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_buffer_count = read_word(&body[ET_CAN_RAM_TX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_fifo_count = read_word(&body[ET_CAN_RAM_TX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_queue = read_word(&body[ET_CAN_RAM_TX_QUEUE * ET_CAN_WIRE_WORD_BYTES]);
    layout->tx_payload_bytes =
        read_word(&body[ET_CAN_RAM_TX_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_offset = read_word(&body[ET_CAN_RAM_EVENT_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_count = read_word(&body[ET_CAN_RAM_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->event_watermark = read_word(&body[ET_CAN_RAM_EVENT_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_offset = read_word(&body[ET_CAN_RAM_RX0_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_count = read_word(&body[ET_CAN_RAM_RX0_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_watermark = read_word(&body[ET_CAN_RAM_RX0_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_overwrite = read_word(&body[ET_CAN_RAM_RX0_OVERWRITE * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_offset = read_word(&body[ET_CAN_RAM_RX1_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_count = read_word(&body[ET_CAN_RAM_RX1_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_watermark = read_word(&body[ET_CAN_RAM_RX1_WATERMARK * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_overwrite = read_word(&body[ET_CAN_RAM_RX1_OVERWRITE * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx_buffer_offset =
        read_word(&body[ET_CAN_RAM_RX_BUFFER_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx_buffer_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX_BUFFER_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx0_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX0_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
    layout->rx1_payload_bytes =
        read_word(&body[ET_CAN_RAM_RX1_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode actual RAM configuration in the declared word order.
 * @param[out] body Validated response storage.
 * @param[in] layout Independent hardware configuration readback.
 * @note Does not present configuration requests as observed values.
 */
static void encode_ram_layout(uint8_t *body, const et_can_ram_layout_t *layout)
{
    write_word(&body[ET_CAN_RAM_STD_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->std_offset);
    write_word(&body[ET_CAN_RAM_STD_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->std_count);
    write_word(&body[ET_CAN_RAM_EXT_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->ext_offset);
    write_word(&body[ET_CAN_RAM_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->ext_count);
    write_word(&body[ET_CAN_RAM_TX_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->tx_offset);
    write_word(&body[ET_CAN_RAM_TX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->tx_buffer_count);
    write_word(&body[ET_CAN_RAM_TX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->tx_fifo_count);
    write_word(&body[ET_CAN_RAM_TX_QUEUE * ET_CAN_WIRE_WORD_BYTES], layout->tx_queue);
    write_word(&body[ET_CAN_RAM_TX_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->tx_payload_bytes);
    write_word(&body[ET_CAN_RAM_EVENT_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->event_offset);
    write_word(&body[ET_CAN_RAM_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->event_count);
    write_word(&body[ET_CAN_RAM_EVENT_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->event_watermark);
    write_word(&body[ET_CAN_RAM_RX0_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->rx0_offset);
    write_word(&body[ET_CAN_RAM_RX0_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->rx0_count);
    write_word(&body[ET_CAN_RAM_RX0_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->rx0_watermark);
    write_word(&body[ET_CAN_RAM_RX0_OVERWRITE * ET_CAN_WIRE_WORD_BYTES], layout->rx0_overwrite);
    write_word(&body[ET_CAN_RAM_RX1_OFFSET * ET_CAN_WIRE_WORD_BYTES], layout->rx1_offset);
    write_word(&body[ET_CAN_RAM_RX1_COUNT * ET_CAN_WIRE_WORD_BYTES], layout->rx1_count);
    write_word(&body[ET_CAN_RAM_RX1_WATERMARK * ET_CAN_WIRE_WORD_BYTES], layout->rx1_watermark);
    write_word(&body[ET_CAN_RAM_RX1_OVERWRITE * ET_CAN_WIRE_WORD_BYTES], layout->rx1_overwrite);
    write_word(&body[ET_CAN_RAM_RX_BUFFER_OFFSET * ET_CAN_WIRE_WORD_BYTES],
               layout->rx_buffer_offset);
    write_word(&body[ET_CAN_RAM_RX_BUFFER_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx_buffer_payload_bytes);
    write_word(&body[ET_CAN_RAM_RX0_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx0_payload_bytes);
    write_word(&body[ET_CAN_RAM_RX1_PAYLOAD_BYTES * ET_CAN_WIRE_WORD_BYTES],
               layout->rx1_payload_bytes);
}

/**
 * @brief Handle the three RAM commands without test sequencing.
 * @param[in] id Logical controller identity.
 * @param[in] command Validated RAM command identifier.
 * @param[in] body Validated request following the instance prefix.
 * @param[out] response Output storage, nullable for SET.
 * @return Own Wrap status.
 * @note Only calls the CAN Wrap; no resource or GPIO calls.
 */
static et_wrap_status_t execute_ram_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_can_ram_layout_t layout;
    et_can_ram_limits_t limits;
    et_wrap_status_t status;

    if (command == ET_CAN_COMMAND_RAM_LAYOUT_SET)
    {
        decode_ram_layout(body, &layout);

        return et_can_wrap_set_ram_layout(id, &layout);
    }

    if (command == ET_CAN_COMMAND_RAM_LAYOUT_GET)
    {
        status = et_can_wrap_get_ram_layout(id, &layout);

        if (status == ET_WRAP_STATUS_OK)
        {
            encode_ram_layout(response, &layout);
        }

        return status;
    }

    status = et_can_wrap_get_ram_limits(id, &limits);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_RAM_LIMIT_RAM_BYTES * ET_CAN_WIRE_WORD_BYTES],
                   limits.ram_bytes);
        write_word(&response[ET_CAN_RAM_LIMIT_STD_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.std_count);
        write_word(&response[ET_CAN_RAM_LIMIT_EXT_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.ext_count);
        write_word(&response[ET_CAN_RAM_LIMIT_TX_COUNT * ET_CAN_WIRE_WORD_BYTES], limits.tx_count);
        write_word(&response[ET_CAN_RAM_LIMIT_RX_FIFO_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.rx_fifo_count);
        write_word(&response[ET_CAN_RAM_LIMIT_EVENT_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.event_count);
        write_word(&response[ET_CAN_RAM_LIMIT_RX_BUFFER_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   limits.rx_buffer_count);
    }

    return status;
}

/**
 * @brief Decode the complete existing Driver bus configuration group.
 * @param[in] body Validated words after the instance prefix.
 * @param[out] config Explicit public parameters, without defaults.
 * @note Pure codec; no other IP or test orchestration.
 */
static void decode_bus_config(const uint8_t *body, et_can_bus_config_t *config)
{
    config->monitor = read_word(&body[ET_CAN_BUS_MONITOR * ET_CAN_WIRE_WORD_BYTES]);
    config->restricted = read_word(&body[ET_CAN_BUS_RESTRICTED * ET_CAN_WIRE_WORD_BYTES]);
    config->timestamp_divisor =
        read_word(&body[ET_CAN_BUS_TIMESTAMP_DIVISOR * ET_CAN_WIRE_WORD_BYTES]);
    config->timestamp_source =
        read_word(&body[ET_CAN_BUS_TIMESTAMP_SOURCE * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_source = read_word(&body[ET_CAN_BUS_TIMEOUT_SOURCE * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_period = read_word(&body[ET_CAN_BUS_TIMEOUT_PERIOD * ET_CAN_WIRE_WORD_BYTES]);
    config->timeout_enabled = read_word(&body[ET_CAN_BUS_TIMEOUT_ENABLED * ET_CAN_WIRE_WORD_BYTES]);
    config->reject_remote_ext =
        read_word(&body[ET_CAN_BUS_REJECT_REMOTE_EXT * ET_CAN_WIRE_WORD_BYTES]);
    config->reject_remote_std =
        read_word(&body[ET_CAN_BUS_REJECT_REMOTE_STD * ET_CAN_WIRE_WORD_BYTES]);
    config->unmatched_ext = read_word(&body[ET_CAN_BUS_UNMATCHED_EXT * ET_CAN_WIRE_WORD_BYTES]);
    config->unmatched_std = read_word(&body[ET_CAN_BUS_UNMATCHED_STD * ET_CAN_WIRE_WORD_BYTES]);
}

/**
 * @brief Encode independently read bus configuration.
 * @param[out] body Validated output storage.
 * @param[in] config Actual Wrap readback.
 * @note Does not synthesize observations from requests.
 */
static void encode_bus_config(uint8_t *body, const et_can_bus_config_t *config)
{
    write_word(&body[ET_CAN_BUS_MONITOR * ET_CAN_WIRE_WORD_BYTES], config->monitor);
    write_word(&body[ET_CAN_BUS_RESTRICTED * ET_CAN_WIRE_WORD_BYTES], config->restricted);
    write_word(&body[ET_CAN_BUS_TIMESTAMP_DIVISOR * ET_CAN_WIRE_WORD_BYTES],
               config->timestamp_divisor);
    write_word(&body[ET_CAN_BUS_TIMESTAMP_SOURCE * ET_CAN_WIRE_WORD_BYTES],
               config->timestamp_source);
    write_word(&body[ET_CAN_BUS_TIMEOUT_SOURCE * ET_CAN_WIRE_WORD_BYTES], config->timeout_source);
    write_word(&body[ET_CAN_BUS_TIMEOUT_PERIOD * ET_CAN_WIRE_WORD_BYTES], config->timeout_period);
    write_word(&body[ET_CAN_BUS_TIMEOUT_ENABLED * ET_CAN_WIRE_WORD_BYTES], config->timeout_enabled);
    write_word(&body[ET_CAN_BUS_REJECT_REMOTE_EXT * ET_CAN_WIRE_WORD_BYTES],
               config->reject_remote_ext);
    write_word(&body[ET_CAN_BUS_REJECT_REMOTE_STD * ET_CAN_WIRE_WORD_BYTES],
               config->reject_remote_std);
    write_word(&body[ET_CAN_BUS_UNMATCHED_EXT * ET_CAN_WIRE_WORD_BYTES], config->unmatched_ext);
    write_word(&body[ET_CAN_BUS_UNMATCHED_STD * ET_CAN_WIRE_WORD_BYTES], config->unmatched_std);
}

/**
 * @brief Execute bus configuration and loopback primitives only.
 * @param[in] id Logical controller.
 * @param[in] command Validated command in the bus action group.
 * @param[in] body Validated input following the instance prefix.
 * @param[out] response Validated output, nullable for SET.
 * @return Own Wrap result.
 * @note No polling, defaults, cross-IP initialization or Case verdicts.
 */
static et_wrap_status_t execute_bus_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_can_bus_config_t config;
    et_can_bus_limits_t limits;
    et_can_loopback_t mode;
    et_wrap_status_t status;
    uint32_t requested;

    switch (command)
    {
        case ET_CAN_COMMAND_BUS_CONFIG_SET:
        {
            decode_bus_config(body, &config);

            return et_can_wrap_set_bus_config(id, &config);
        }

        case ET_CAN_COMMAND_BUS_CONFIG_GET:
        {
            status = et_can_wrap_get_bus_config(id, &config);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_bus_config(response, &config);
            }

            return status;
        }

        case ET_CAN_COMMAND_LOOPBACK_SET:
        {
            requested = read_word(body);

            if (requested > ET_CAN_LOOPBACK_EXTERNAL)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_set_loopback(id, (et_can_loopback_t)requested);
        }

        case ET_CAN_COMMAND_LOOPBACK_GET:
        {
            status = et_can_wrap_get_loopback(id, &mode);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, (uint32_t)mode);
            }

            return status;
        }

        default:
        {
            status = et_can_wrap_get_bus_limits(id, &limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_BUS_LIMIT_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                           limits.timestamp_divisor);
                write_word(&response[ET_CAN_BUS_LIMIT_TIMEOUT * ET_CAN_WIRE_WORD_BYTES],
                           limits.timeout_period);
            }

            return status;
        }
    }
}

/**
 * @brief Decode one fixed-size TX element after full envelope validation.
 * @param[in] body Validated index, header and payload bytes.
 * @param[out] frame Public frame; payload is copied byte-for-byte.
 * @note Does not populate RAM or issue a transmit request.
 */
static void decode_tx_frame(const uint8_t *body, et_can_tx_frame_t *frame)
{
    frame->identifier = read_word(&body[ET_CAN_TX_FIELD_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES]);
    frame->flags = read_word(&body[ET_CAN_TX_FIELD_FLAGS * ET_CAN_WIRE_WORD_BYTES]);
    frame->dlc = read_word(&body[ET_CAN_TX_FIELD_DLC * ET_CAN_WIRE_WORD_BYTES]);
    frame->marker = read_word(&body[ET_CAN_TX_FIELD_MARKER * ET_CAN_WIRE_WORD_BYTES]);
    (void)memcpy(frame->data, &body[ET_CAN_TX_FIELD_DATA * ET_CAN_WIRE_WORD_BYTES],
                 ET_CAN_FRAME_DATA_BYTES);
}

/**
 * @brief Encode the observed RX header and fixed-capacity byte envelope.
 * @param[out] body Validated response storage.
 * @param[in] frame Actual frame; data_length marks the valid stored bytes.
 * @note Does not acknowledge the element or compare it with expected data.
 */
static void encode_rx_frame(uint8_t *body, const et_can_rx_frame_t *frame)
{
    write_word(&body[ET_CAN_RX_FIELD_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES], frame->identifier);
    write_word(&body[ET_CAN_RX_FIELD_FLAGS * ET_CAN_WIRE_WORD_BYTES], frame->flags);
    write_word(&body[ET_CAN_RX_FIELD_DLC * ET_CAN_WIRE_WORD_BYTES], frame->dlc);
    write_word(&body[ET_CAN_RX_FIELD_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES], frame->timestamp);
    write_word(&body[ET_CAN_RX_FIELD_FILTER_INDEX * ET_CAN_WIRE_WORD_BYTES], frame->filter_index);
    write_word(&body[ET_CAN_RX_FIELD_NONMATCHING * ET_CAN_WIRE_WORD_BYTES], frame->nonmatching);
    write_word(&body[ET_CAN_RX_FIELD_DATA_LENGTH * ET_CAN_WIRE_WORD_BYTES], frame->data_length);
    write_word(&body[ET_CAN_RX_FIELD_INDEX * ET_CAN_WIRE_WORD_BYTES], frame->index);
    (void)memcpy(&body[ET_CAN_RX_FIELD_DATA * ET_CAN_WIRE_WORD_BYTES], frame->data,
                 ET_CAN_FRAME_DATA_BYTES);
}

/**
 * @brief Execute one TX preparation, request or status query.
 * @param[in] id Logical controller.
 * @param[in] command One validated TX command.
 * @param[in] body Validated request after the instance prefix.
 * @param[out] response Storage required only by status queries.
 * @return Own Wrap status.
 * @note Preparing a frame never implies starting or waiting for transmission.
 */
static et_wrap_status_t execute_tx_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                           uint8_t *response)
{
    et_can_tx_frame_t frame;
    et_can_tx_status_t status;
    et_wrap_status_t result;

    if (command == ET_CAN_COMMAND_TX_WRITE)
    {
        decode_tx_frame(body, &frame);

        return et_can_wrap_write_tx(
            id, read_word(&body[ET_CAN_TX_FIELD_INDEX * ET_CAN_WIRE_WORD_BYTES]), &frame);
    }

    if (command == ET_CAN_COMMAND_TX_REQUEST)
    {
        return et_can_wrap_request_tx(id, read_word(body));
    }

    if (command == ET_CAN_COMMAND_TX_READ)
    {
        result = et_can_wrap_read_tx(id, read_word(body), &frame);

        if (result != ET_WRAP_STATUS_OK)
        {
            return result;
        }

        write_word(&response[ET_CAN_TX_FIELD_INDEX * ET_CAN_WIRE_WORD_BYTES], read_word(body));
        write_word(&response[ET_CAN_TX_FIELD_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES],
                   frame.identifier);
        write_word(&response[ET_CAN_TX_FIELD_FLAGS * ET_CAN_WIRE_WORD_BYTES], frame.flags);
        write_word(&response[ET_CAN_TX_FIELD_DLC * ET_CAN_WIRE_WORD_BYTES], frame.dlc);
        write_word(&response[ET_CAN_TX_FIELD_MARKER * ET_CAN_WIRE_WORD_BYTES], frame.marker);
        (void)memcpy(&response[ET_CAN_TX_FIELD_DATA * ET_CAN_WIRE_WORD_BYTES], frame.data,
                     ET_CAN_FRAME_DATA_BYTES);

        return ET_WRAP_STATUS_OK;
    }

    result = et_can_wrap_get_tx_status(id, &status);

    if (result == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_TX_STATUS_PENDING * ET_CAN_WIRE_WORD_BYTES], status.pending);
        write_word(&response[ET_CAN_TX_STATUS_COMPLETED * ET_CAN_WIRE_WORD_BYTES],
                   status.completed);
        write_word(&response[ET_CAN_TX_STATUS_CANCELLED * ET_CAN_WIRE_WORD_BYTES],
                   status.cancelled);
        write_word(&response[ET_CAN_TX_STATUS_FREE_COUNT * ET_CAN_WIRE_WORD_BYTES],
                   status.free_count);
        write_word(&response[ET_CAN_TX_STATUS_GET_INDEX * ET_CAN_WIRE_WORD_BYTES],
                   status.get_index);
        write_word(&response[ET_CAN_TX_STATUS_PUT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                   status.put_index);
        write_word(&response[ET_CAN_TX_STATUS_FULL * ET_CAN_WIRE_WORD_BYTES], status.full);
    }

    return result;
}

/**
 * @brief Execute one TX Event FIFO status, head read or acknowledgement primitive.
 * @param[in] id Logical controller.
 * @param[in] command Validated TX Event command.
 * @param[in] body Validated request after the instance prefix; used only by ACK.
 * @param[out] response Validated output storage for status and event reads.
 * @return Own Wrap status without polling, comparison or implicit acknowledgement.
 * @note Read and acknowledgement remain separate public commands.
 */
static et_wrap_status_t execute_tx_event_command(et_can_id_t id, uint16_t command,
                                                 const uint8_t *body, uint8_t *response)
{
    et_can_tx_event_status_t status;
    et_can_tx_event_t event;
    et_can_tx_event_details_t details;
    et_can_event_format_t format;
    et_wrap_status_t result;

    /* Phase 1: Select one explicit format, event read or acknowledge operation. */
    switch (command)
    {
        case ET_CAN_COMMAND_EVENT_FORMAT_SET:
        {
            format.marker_bits =
                read_word(&body[ET_CAN_EVENT_FORMAT_MARKER_BITS * ET_CAN_WIRE_WORD_BYTES]);
            format.tsu_enabled =
                read_word(&body[ET_CAN_EVENT_FORMAT_TSU_ENABLED * ET_CAN_WIRE_WORD_BYTES]);

            return et_can_wrap_set_event_format(id, &format);
        }

        case ET_CAN_COMMAND_EVENT_FORMAT_GET:
        {
            result = et_can_wrap_get_event_format(id, &format);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_EVENT_FORMAT_MARKER_BITS * ET_CAN_WIRE_WORD_BYTES],
                           format.marker_bits);
                write_word(&response[ET_CAN_EVENT_FORMAT_TSU_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           format.tsu_enabled);
            }

            return result;
        }

        case ET_CAN_COMMAND_TX_EVENT_STATUS_GET:
        {
            result = et_can_wrap_get_tx_event_status(id, &status);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_TX_EVENT_STATUS_FILL * ET_CAN_WIRE_WORD_BYTES],
                           status.fill);
                write_word(&response[ET_CAN_TX_EVENT_STATUS_GET_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           status.get_index);
                write_word(&response[ET_CAN_TX_EVENT_STATUS_PUT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           status.put_index);
                write_word(&response[ET_CAN_TX_EVENT_STATUS_FULL * ET_CAN_WIRE_WORD_BYTES],
                           status.full);
                write_word(&response[ET_CAN_TX_EVENT_STATUS_LOST * ET_CAN_WIRE_WORD_BYTES],
                           status.lost);
            }

            return result;
        }

        case ET_CAN_COMMAND_TX_EVENT_READ:
        case ET_CAN_COMMAND_TX_EVENT_DETAILS_READ:
        {
            if (command == ET_CAN_COMMAND_TX_EVENT_DETAILS_READ)
            {
                result = et_can_wrap_read_tx_event_details(id, &details);

                if (result == ET_WRAP_STATUS_OK)
                {
                    event = details.event;
                }
            }
            else
            {
                result = et_can_wrap_read_tx_event(id, &event);
            }

            /* Phase 2: Encode actual fields; invalid internal timestamp is explicitly marked. */
            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_TX_EVENT_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES],
                           event.identifier);
                write_word(&response[ET_CAN_TX_EVENT_FLAGS * ET_CAN_WIRE_WORD_BYTES], event.flags);
                write_word(&response[ET_CAN_TX_EVENT_DLC * ET_CAN_WIRE_WORD_BYTES], event.dlc);
                write_word(&response[ET_CAN_TX_EVENT_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                           event.timestamp);
                write_word(&response[ET_CAN_TX_EVENT_TYPE * ET_CAN_WIRE_WORD_BYTES],
                           event.event_type);
                write_word(&response[ET_CAN_TX_EVENT_MARKER * ET_CAN_WIRE_WORD_BYTES],
                           event.marker);
                write_word(&response[ET_CAN_TX_EVENT_INDEX * ET_CAN_WIRE_WORD_BYTES], event.index);

                if (command == ET_CAN_COMMAND_TX_EVENT_DETAILS_READ)
                {
                    write_word(
                        &response[ET_CAN_EVENT_INTERNAL_TIMESTAMP_VALID * ET_CAN_WIRE_WORD_BYTES],
                        details.internal_timestamp_valid);
                    write_word(&response[ET_CAN_EVENT_TSU_CAPTURED * ET_CAN_WIRE_WORD_BYTES],
                               details.tsu_captured);
                    write_word(&response[ET_CAN_EVENT_TSU_POINTER * ET_CAN_WIRE_WORD_BYTES],
                               details.tsu_pointer);
                }
            }

            return result;
        }

        case ET_CAN_COMMAND_TX_EVENT_ACK:
        {
            return et_can_wrap_ack_tx_event(id, read_word(body));
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Execute a receive FIFO, buffer or frame primitive.
 * @param[in] id Logical controller.
 * @param[in] command Validated receive-group command.
 * @param[in] body Validated source/index or bitmap fields.
 * @param[out] response Validated output storage when the command returns facts.
 * @return Own Wrap status.
 * @note Reads and acknowledgements remain separate commands; no draining loops or verdicts.
 */
static et_wrap_status_t execute_rx_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                           uint8_t *response)
{
    et_can_rx_frame_t frame;
    et_can_rx_fifo_status_t fifo;
    et_can_rx_buffer_status_t buffers;
    et_wrap_status_t result;
    uint32_t source;

    switch (command)
    {
        case ET_CAN_COMMAND_RX_READ:
        {
            /* Step 1: Decode one explicit storage selector and return the observed element. */
            source = read_word(&body[ET_CAN_RX_SELECT_SOURCE * ET_CAN_WIRE_WORD_BYTES]);

            if (source > ET_CAN_RX_FIFO1)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            result = et_can_wrap_read_rx(
                id, (et_can_rx_source_t)source,
                read_word(&body[ET_CAN_RX_SELECT_INDEX * ET_CAN_WIRE_WORD_BYTES]), &frame);

            if (result == ET_WRAP_STATUS_OK)
            {
                encode_rx_frame(response, &frame);
            }

            return result;
        }

        case ET_CAN_COMMAND_RX_FIFO_ACK:
        {
            /* Step 2: Acknowledgement is a separate caller-requested write, never a read side effect. */
            return et_can_wrap_ack_rx_fifo(
                id, read_word(&body[ET_CAN_RX_SELECT_SOURCE * ET_CAN_WIRE_WORD_BYTES]),
                read_word(&body[ET_CAN_RX_SELECT_INDEX * ET_CAN_WIRE_WORD_BYTES]));
        }

        case ET_CAN_COMMAND_RX_BUFFER_ACK:
        {
            buffers.low = read_word(&body[ET_CAN_RX_BITMAP_LOW * ET_CAN_WIRE_WORD_BYTES]);
            buffers.high = read_word(&body[ET_CAN_RX_BITMAP_HIGH * ET_CAN_WIRE_WORD_BYTES]);

            return et_can_wrap_ack_rx_buffers(id, &buffers);
        }

        case ET_CAN_COMMAND_RX_BUFFER_STATUS_GET:
        {
            result = et_can_wrap_get_rx_buffer_status(id, &buffers);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_RX_BITMAP_LOW * ET_CAN_WIRE_WORD_BYTES], buffers.low);
                write_word(&response[ET_CAN_RX_BITMAP_HIGH * ET_CAN_WIRE_WORD_BYTES], buffers.high);
            }

            return result;
        }

        default:
        {
            result = et_can_wrap_get_rx_fifo_status(id, read_word(body), &fifo);

            if (result == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_RX_FIFO_FILL * ET_CAN_WIRE_WORD_BYTES], fifo.fill);
                write_word(&response[ET_CAN_RX_FIFO_GET_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           fifo.get_index);
                write_word(&response[ET_CAN_RX_FIFO_PUT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           fifo.put_index);
                write_word(&response[ET_CAN_RX_FIFO_FULL * ET_CAN_WIRE_WORD_BYTES], fifo.full);
                write_word(&response[ET_CAN_RX_FIFO_LOST * ET_CAN_WIRE_WORD_BYTES], fifo.lost);
            }

            return result;
        }
    }
}

/**
 * @brief Decode one filter action and encode only independently read values.
 * @param[in] id Logical CAN controller.
 * @param[in] command Validated filter-group command.
 * @param[in] body Validated request words after instance prefix.
 * @param[out] response Validated response storage, nullable for writes.
 * @return Own Wrap result without assigning any Case verdict.
 * @note No filter defaults, iteration across lists, or other IP operations.
 */
static et_wrap_status_t execute_filter_command(et_can_id_t id, uint16_t command,
                                               const uint8_t *body, uint8_t *response)
{
    et_can_filter_t filter;
    et_can_high_priority_status_t high_priority;
    et_wrap_status_t status;
    uint32_t mask;
    const uint8_t *config;

    if (command == ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET)
    {
        status = et_can_wrap_get_high_priority_status(id, &high_priority);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_HIGH_PRIORITY_BUFFER_INDEX * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.buffer_index);
            write_word(&response[ET_CAN_HIGH_PRIORITY_STORAGE * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.storage);
            write_word(&response[ET_CAN_HIGH_PRIORITY_FILTER_INDEX * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.filter_index);
            write_word(&response[ET_CAN_HIGH_PRIORITY_EXTENDED_FILTER * ET_CAN_WIRE_WORD_BYTES],
                       high_priority.extended_filter);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_EXTENDED_MASK_SET)
    {
        return et_can_wrap_set_extended_mask(id, read_word(body));
    }

    if (command == ET_CAN_COMMAND_EXTENDED_MASK_GET)
    {
        status = et_can_wrap_get_extended_mask(id, &mask);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(response, mask);
        }

        return status;
    }

    /* Phase 1: Decode an explicit SET tuple; no hardware-encoded Buffer bitfields. */
    if (command == ET_CAN_COMMAND_FILTER_SET)
    {
        config = &body[ET_CAN_FILTER_SELECT_WORDS * ET_CAN_WIRE_WORD_BYTES];
        filter.type = read_word(&config[ET_CAN_FILTER_FIELD_TYPE * ET_CAN_WIRE_WORD_BYTES]);
        filter.action = read_word(&config[ET_CAN_FILTER_FIELD_ACTION * ET_CAN_WIRE_WORD_BYTES]);
        filter.id1 = read_word(&config[ET_CAN_FILTER_FIELD_ID1 * ET_CAN_WIRE_WORD_BYTES]);
        filter.id2 = read_word(&config[ET_CAN_FILTER_FIELD_ID2 * ET_CAN_WIRE_WORD_BYTES]);
        filter.buffer_index =
            read_word(&config[ET_CAN_FILTER_FIELD_BUFFER * ET_CAN_WIRE_WORD_BYTES]);

        return et_can_wrap_set_filter(id, read_word(body), read_word(&body[ET_CAN_WIRE_WORD_BYTES]),
                                      &filter);
    }

    /* Phase 2: Serialize only successful actual RAM readback, never the request. */
    status = et_can_wrap_get_filter(id, read_word(body), read_word(&body[ET_CAN_WIRE_WORD_BYTES]),
                                    &filter);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_FILTER_FIELD_TYPE * ET_CAN_WIRE_WORD_BYTES], filter.type);
        write_word(&response[ET_CAN_FILTER_FIELD_ACTION * ET_CAN_WIRE_WORD_BYTES], filter.action);
        write_word(&response[ET_CAN_FILTER_FIELD_ID1 * ET_CAN_WIRE_WORD_BYTES], filter.id1);
        write_word(&response[ET_CAN_FILTER_FIELD_ID2 * ET_CAN_WIRE_WORD_BYTES], filter.id2);
        write_word(&response[ET_CAN_FILTER_FIELD_BUFFER * ET_CAN_WIRE_WORD_BYTES],
                   filter.buffer_index);
    }

    return status;
}

/**
 * @brief Execute protocol consume or one scalar timer/clock action.
 * @param[in] id Logical controller.
 * @param[in] command Validated command.
 * @param[in] body Exact decoded request storage.
 * @param[out] response Capacity-checked response storage.
 * @return Own Wrap status, with no retry after consuming read-clear state.
 * @note No loop, cross-IP initialization, event capture or Case verdict is performed.
 */
static et_wrap_status_t execute_status_command(et_can_id_t id, uint16_t command,
                                               const uint8_t *body, uint8_t *response)
{
    et_wrap_status_t status;
    et_can_protocol_status_t protocol;
    uint32_t value;
    uint32_t after;

    /* Read both watchdog fields together without touching its counter or interrupt. */
    if (command == ET_CAN_COMMAND_RAM_WATCHDOG_GET)
    {
        status = et_can_wrap_get_ram_watchdog(id, &value, &after);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_RAM_WATCHDOG_LIMIT * ET_CAN_WIRE_WORD_BYTES], value);
            write_word(&response[ET_CAN_RAM_WATCHDOG_VALUE * ET_CAN_WIRE_WORD_BYTES], after);
        }

        return status;
    }

    /* Phase 1: State-changing and read-clear operations are performed once. */
    if ((command == ET_CAN_COMMAND_TIMEOUT_RELOAD) ||
        (command == ET_CAN_COMMAND_TIMESTAMP_RESET_SNAPSHOT))
    {
        status = command == ET_CAN_COMMAND_TIMEOUT_RELOAD
                     ? et_can_wrap_reload_timeout(id, &value, &after)
                     : et_can_wrap_reset_timestamp_snapshot(id, &value, &after);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_COUNTER_RELOAD_BEFORE * ET_CAN_WIRE_WORD_BYTES], value);
            write_word(&response[ET_CAN_COUNTER_RELOAD_AFTER * ET_CAN_WIRE_WORD_BYTES], after);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME)
    {
        status = et_can_wrap_consume_protocol_status(id, &protocol);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(&response[ET_CAN_PROTOCOL_LAST_ERROR * ET_CAN_WIRE_WORD_BYTES],
                       protocol.last_error);
            write_word(&response[ET_CAN_PROTOCOL_ACTIVITY * ET_CAN_WIRE_WORD_BYTES],
                       protocol.activity);
            write_word(&response[ET_CAN_PROTOCOL_ERROR_PASSIVE * ET_CAN_WIRE_WORD_BYTES],
                       protocol.error_passive);
            write_word(&response[ET_CAN_PROTOCOL_WARNING * ET_CAN_WIRE_WORD_BYTES],
                       protocol.warning);
            write_word(&response[ET_CAN_PROTOCOL_BUS_OFF * ET_CAN_WIRE_WORD_BYTES],
                       protocol.bus_off);
            write_word(&response[ET_CAN_PROTOCOL_DATA_LAST_ERROR * ET_CAN_WIRE_WORD_BYTES],
                       protocol.data_last_error);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_ESI * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_esi);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_BRS * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_brs);
            write_word(&response[ET_CAN_PROTOCOL_RECEIVED_FD * ET_CAN_WIRE_WORD_BYTES],
                       protocol.received_fd);
            write_word(&response[ET_CAN_PROTOCOL_PROTOCOL_EXCEPTION * ET_CAN_WIRE_WORD_BYTES],
                       protocol.protocol_exception);
            write_word(&response[ET_CAN_PROTOCOL_TDC_POSITION * ET_CAN_WIRE_WORD_BYTES],
                       protocol.tdc_position);
            write_word(&response[ET_CAN_PROTOCOL_TX_ERROR_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.tx_error_count);
            write_word(&response[ET_CAN_PROTOCOL_RX_ERROR_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.rx_error_count);
            write_word(&response[ET_CAN_PROTOCOL_RX_ERROR_PASSIVE * ET_CAN_WIRE_WORD_BYTES],
                       protocol.rx_error_passive);
            write_word(&response[ET_CAN_PROTOCOL_ERROR_LOG_COUNT * ET_CAN_WIRE_WORD_BYTES],
                       protocol.error_log_count);
        }

        return status;
    }

    if (command == ET_CAN_COMMAND_TIMESTAMP_RESET)
    {
        return et_can_wrap_reset_timestamp(id);
    }

    if (command == ET_CAN_COMMAND_CLOCK_STOP_SET)
    {
        value = read_word(body);

        if (value > 1u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        return et_can_wrap_set_clock_stop(id, (uint8_t)value);
    }

    /* Phase 2: Select one nondestructive read and serialize only its successful result. */
    switch (command)
    {
        case ET_CAN_COMMAND_TIMESTAMP_GET:
        {
            status = et_can_wrap_get_timestamp(id, &value);
            break;
        }

        case ET_CAN_COMMAND_TIMEOUT_COUNTER_GET:
        {
            status = et_can_wrap_get_timeout_counter(id, &value);
            break;
        }

        case ET_CAN_COMMAND_CLOCK_STOP_ACK_GET:
        {
            status = et_can_wrap_get_clock_stop_ack(id, &value);
            break;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(response, value);
    }

    return status;
}

/**
 * @brief Decode a bounded Message RAM read, write or per-word exchange.
 * @param[in] id Logical controller selected by the Service.
 * @param[in] command RAM access operation; never a pattern algorithm.
 * @param[in] body Capacity-checked selector and optional fixed word array.
 * @param[out] response Capacity-checked sampled-word array, nullable for writes.
 * @return Own Wrap status, or INVALID_ARGUMENT before malformed requests reach hardware.
 * @note No comparison, address-order planning, retry or test verdict is performed here.
 */
static et_wrap_status_t execute_ram_access(et_can_id_t id, uint16_t command, const uint8_t *body,
                                           uint8_t *response)
{
    uint32_t input[ET_CAN_RAM_ACCESS_WORDS];
    uint32_t output[ET_CAN_RAM_ACCESS_WORDS] = {0u};
    uint32_t offset = read_word(&body[ET_CAN_RAM_ACCESS_OFFSET * ET_CAN_WIRE_WORD_BYTES]);
    uint32_t count = read_word(&body[ET_CAN_RAM_ACCESS_COUNT * ET_CAN_WIRE_WORD_BYTES]);
    uint32_t descending = read_word(&body[ET_CAN_RAM_ACCESS_DESCENDING * ET_CAN_WIRE_WORD_BYTES]);
    uint32_t index;
    et_wrap_status_t status;

    /* Phase 1: Decode a bounded request completely before touching Message RAM. */
    if ((count == 0u) || (count > ET_CAN_RAM_ACCESS_WORDS) || (descending > 1u))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (command != ET_CAN_COMMAND_RAM_WORDS_READ)
    {
        for (index = 0u; index < ET_CAN_RAM_ACCESS_WORDS; ++index)
        {
            input[index] =
                read_word(&body[(ET_CAN_RAM_ACCESS_SELECT_WORDS + index) * ET_CAN_WIRE_WORD_BYTES]);

            if ((index >= count) && (input[index] != 0u))
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }
        }
    }

    /* Phase 2: One own-Wrap primitive; only the PC knows patterns or expected values. */
    status = et_can_wrap_access_ram(
        id, offset, count, command == ET_CAN_COMMAND_RAM_WORDS_READ ? NULL : input,
        command == ET_CAN_COMMAND_RAM_WORDS_WRITE ? NULL : output, (uint8_t)descending);

    /* Phase 3: Return sampled words and deterministic zero padding, never request echoes. */
    if ((status == ET_WRAP_STATUS_OK) && (command != ET_CAN_COMMAND_RAM_WORDS_WRITE))
    {
        for (index = 0u; index < ET_CAN_RAM_ACCESS_WORDS; ++index)
        {
            write_word(&response[index * ET_CAN_WIRE_WORD_BYTES], output[index]);
        }
    }

    return status;
}

/**
 * @brief Decode one TSU action and encode actual Wrap results.
 * @param[in] id Logical controller.
 * @param[in] command Validated TSU command.
 * @param[in] body Length-validated input words.
 * @param[out] response Capacity-validated output storage.
 * @return Own Wrap status; no local test verdict.
 * @note Consuming TS0 is separate from non-consuming timebase and flags reads.
 */
static et_wrap_status_t execute_tsu_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_can_tsu_config_t config;
    et_can_tsu_limits_t limits;
    et_can_rx_timestamp_t metadata;
    et_wrap_status_t status;
    uint32_t new_flags, lost_flags, value, extended;

    /* Phase 1: Select exactly one own-IP operation from the validated command. */
    switch (command)
    {
        case ET_CAN_COMMAND_EXTERNAL_VECTOR_SET:
        case ET_CAN_COMMAND_EXTERNAL_VECTOR_GET:
        {
            value = command == ET_CAN_COMMAND_EXTERNAL_VECTOR_SET ? read_word(body) : 0u;
            status = et_can_wrap_access_external_vector(
                id, command == ET_CAN_COMMAND_EXTERNAL_VECTOR_SET, &value);

            if (status == ET_WRAP_STATUS_OK && command == ET_CAN_COMMAND_EXTERNAL_VECTOR_GET)
            {
                write_word(response, value);
            }

            return status;
        }

        case ET_CAN_COMMAND_DMU_TIMESTAMP_SET:
        {
            value = read_word(body);

            return value > 1u ? ET_WRAP_STATUS_INVALID_ARGUMENT
                              : et_can_wrap_set_dmu_timestamp(id, (uint8_t)value);
        }

        case ET_CAN_COMMAND_FILTER_SYNC_SET:
        case ET_CAN_COMMAND_FILTER_SYNC_GET:
        {
            extended = read_word(body);
            value = command == ET_CAN_COMMAND_FILTER_SYNC_SET
                        ? read_word(&body[ET_CAN_FILTER_SELECT_WORDS * ET_CAN_WIRE_WORD_BYTES])
                        : 0u;

            if (extended > 1u || value > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            status = et_can_wrap_access_filter_sync(
                id, (uint8_t)extended, read_word(&body[ET_CAN_WIRE_WORD_BYTES]),
                command == ET_CAN_COMMAND_FILTER_SYNC_SET, &value);

            if (status == ET_WRAP_STATUS_OK && command == ET_CAN_COMMAND_FILTER_SYNC_GET)
            {
                write_word(response, value);
            }

            return status;
        }

        case ET_CAN_COMMAND_RX_TIMESTAMP_GET:
        {
            status = et_can_wrap_get_rx_timestamp(id, read_word(body), &metadata);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_RX_TIMESTAMP_INTERNAL_VALID * ET_CAN_WIRE_WORD_BYTES],
                           metadata.internal_valid);
                write_word(&response[ET_CAN_RX_TIMESTAMP_VALUE * ET_CAN_WIRE_WORD_BYTES],
                           metadata.timestamp);
                write_word(&response[ET_CAN_RX_TIMESTAMP_CAPTURED * ET_CAN_WIRE_WORD_BYTES],
                           metadata.captured);
                write_word(&response[ET_CAN_RX_TIMESTAMP_POINTER * ET_CAN_WIRE_WORD_BYTES],
                           metadata.pointer);
                write_word(&response[ET_CAN_RX_TIMESTAMP_INDEX * ET_CAN_WIRE_WORD_BYTES],
                           metadata.index);
            }

            return status;
        }

        case ET_CAN_COMMAND_TSU_CONFIG_SET:
        {
            config.enabled = read_word(&body[ET_CAN_TSU_ENABLED * ET_CAN_WIRE_WORD_BYTES]);
            config.external = read_word(&body[ET_CAN_TSU_EXTERNAL * ET_CAN_WIRE_WORD_BYTES]);
            config.sof = read_word(&body[ET_CAN_TSU_SOF * ET_CAN_WIRE_WORD_BYTES]);
            config.divisor = read_word(&body[ET_CAN_TSU_DIVISOR * ET_CAN_WIRE_WORD_BYTES]);

            return et_can_wrap_set_tsu(id, &config);
        }

        case ET_CAN_COMMAND_TSU_CONFIG_GET:
        {
            status = et_can_wrap_get_tsu(id, &config);

            /* Phase 2: Publish only actual successful reads; never echo request values. */
            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_TSU_ENABLED * ET_CAN_WIRE_WORD_BYTES], config.enabled);
                write_word(&response[ET_CAN_TSU_EXTERNAL * ET_CAN_WIRE_WORD_BYTES],
                           config.external);
                write_word(&response[ET_CAN_TSU_SOF * ET_CAN_WIRE_WORD_BYTES], config.sof);
                write_word(&response[ET_CAN_TSU_DIVISOR * ET_CAN_WIRE_WORD_BYTES], config.divisor);
            }

            return status;
        }

        case ET_CAN_COMMAND_TSU_LIMITS_GET:
        {
            status = et_can_wrap_get_tsu_limits(id, &limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_TSU_SLOTS * ET_CAN_WIRE_WORD_BYTES], limits.slots);
                write_word(&response[ET_CAN_TSU_INTERNAL_SUPPORT * ET_CAN_WIRE_WORD_BYTES],
                           limits.internal);
                write_word(&response[ET_CAN_TSU_SOF_SUPPORT * ET_CAN_WIRE_WORD_BYTES], limits.sof);
            }

            return status;
        }

        case ET_CAN_COMMAND_TSU_FLAGS_GET:
        {
            status = et_can_wrap_get_tsu_flags(id, &new_flags, &lost_flags);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_TSU_NEW * ET_CAN_WIRE_WORD_BYTES], new_flags);
                write_word(&response[ET_CAN_TSU_LOST * ET_CAN_WIRE_WORD_BYTES], lost_flags);
            }

            return status;
        }

        case ET_CAN_COMMAND_TSU_TIMEBASE_GET:
        case ET_CAN_COMMAND_TSU_SLOT0_CONSUME:
        {
            status =
                et_can_wrap_read_tsu_value(id, command == ET_CAN_COMMAND_TSU_SLOT0_CONSUME, &value);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, value);
            }

            return status;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Decode one DMU primitive and encode only actual CAN facts.
 * @param[in] id Logical CAN controller.
 * @param[in] command Validated DMU command ID.
 * @param[in] body Exact-length request words after the instance byte.
 * @param[out] response Validated response capacity, nullable for SET.
 * @return Own Wrap status without hidden recovery.
 * @note Never accesses DMA, acknowledges a queue or consumes DMU IRQ flags.
 */
static et_wrap_status_t execute_dmu_command(et_can_id_t id, uint16_t command, const uint8_t *body,
                                            uint8_t *response)
{
    et_wrap_status_t status;
    et_can_dmu_counters_t counters;
    et_can_dmu_status_t dmu_status;
    et_can_dmu_request_t request;
    uint32_t address;

    /* Phase 1: Execute an explicit selection or endpoint query. */
    switch (command)
    {
        case ET_CAN_COMMAND_DMU_REQUEST_SET:
        {
            return et_can_wrap_set_dmu_request(id, (et_can_dmu_request_t)read_word(body));
        }

        case ET_CAN_COMMAND_DMU_ENDPOINT_GET:
        {
            status =
                et_can_wrap_get_dmu_endpoint(id, (et_can_dmu_element_t)read_word(body), &address);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, address);
            }

            return status;
        }

        case ET_CAN_COMMAND_DMU_REQUEST_GET:
        {
            status = et_can_wrap_get_dmu_request(id, &request);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, request);
            }

            return status;
        }

        case ET_CAN_COMMAND_DMU_COUNTERS_GET:
        {
            break;
        }

        case ET_CAN_COMMAND_DMU_STATUS_CONSUME:
        {
            status = et_can_wrap_consume_dmu_status(id, &dmu_status);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_DMU_STATUS_ERRORS * ET_CAN_WIRE_WORD_BYTES],
                           dmu_status.errors);
                write_word(&response[ET_CAN_DMU_STATUS_ENABLED * ET_CAN_WIRE_WORD_BYTES],
                           dmu_status.enabled);
                write_word(&response[ET_CAN_DMU_STATUS_TRANSFER_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                           dmu_status.transfer_timestamp);
            }

            return status;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }

    /* Phase 2: Encode the single counter snapshot without sampling again. */
    status = et_can_wrap_get_dmu_counters(id, &counters);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_DMU_TX_ENQUEUED * ET_CAN_WIRE_WORD_BYTES],
                   counters.tx_enqueued);
        write_word(&response[ET_CAN_DMU_RX0_DEQUEUED * ET_CAN_WIRE_WORD_BYTES],
                   counters.rx0_dequeued);
        write_word(&response[ET_CAN_DMU_RX1_DEQUEUED * ET_CAN_WIRE_WORD_BYTES],
                   counters.rx1_dequeued);
        write_word(&response[ET_CAN_DMU_TX_EVENT_DEQUEUED * ET_CAN_WIRE_WORD_BYTES],
                   counters.tx_event_dequeued);
        write_word(&response[ET_CAN_DMU_COUNTER_MODULUS * ET_CAN_WIRE_WORD_BYTES],
                   counters.modulus);
    }

    return status;
}

/**
 * @brief Execute one bounded CPU image conversion through the own Wrap.
 * @param[in] id Logical controller supplying actual format facts.
 * @param[in] command Validated image operation.
 * @param[in] body Exact-size request after the instance prefix.
 * @param[out] response Exact-size response storage validated before execution.
 * @return Own Wrap status, or invalid argument for a reserved TX index.
 * @note No Resource handle, DMA action, virtual window or TSU slot is accessed here.
 */
static et_wrap_status_t execute_dmu_image_command(et_can_id_t id, uint16_t command,
                                                  const uint8_t *body, uint8_t *response)
{
    et_can_dmu_image_t image;
    et_can_tx_frame_t frame;
    et_can_dmu_rx_image_t rx;
    et_can_dmu_event_image_t event;
    et_wrap_status_t status;
    uint32_t index;
    const uint8_t *envelope = body;

    /* Phase 1: Encoding reuses the public TX envelope, with its unused index reserved zero. */
    if (command == ET_CAN_COMMAND_DMU_TX_IMAGE_ENCODE)
    {
        if (read_word(body) != 0u)
        {
            return ET_WRAP_STATUS_INVALID_ARGUMENT;
        }

        decode_tx_frame(body, &frame);
        status = et_can_wrap_encode_dmu_tx(id, &frame, &image);

        if (status == ET_WRAP_STATUS_OK)
        {
            write_word(response, image.byte_count);

            for (index = 0u; index < ET_CAN_DMU_IMAGE_WORDS; ++index)
            {
                write_word(&response[(index + 1u) * ET_CAN_WIRE_WORD_BYTES], image.words[index]);
            }
        }

        return status;
    }

    /* Phase 2: Copy raw words into aligned CPU storage; the Wrap validates count and padding. */
    if (command == ET_CAN_COMMAND_DMU_RX_IMAGE_DECODE)
    {
        envelope += ET_CAN_WIRE_WORD_BYTES;
    }

    image.byte_count = read_word(envelope);

    for (index = 0u; index < ET_CAN_DMU_IMAGE_WORDS; ++index)
    {
        image.words[index] = read_word(&envelope[(index + 1u) * ET_CAN_WIRE_WORD_BYTES]);
    }

    if (command == ET_CAN_COMMAND_DMU_RX_IMAGE_DECODE)
    {
        status = et_can_wrap_decode_dmu_rx(id, read_word(body), &image, &rx);

        if (status == ET_WRAP_STATUS_OK)
        {
            encode_rx_frame(response, &rx.frame);
            write_word(&response[ET_CAN_DMU_RX_INTERNAL_VALID * ET_CAN_WIRE_WORD_BYTES],
                       rx.internal_timestamp_valid);
            write_word(&response[ET_CAN_DMU_RX_TSU_CAPTURED * ET_CAN_WIRE_WORD_BYTES],
                       rx.tsu_captured);
            write_word(&response[ET_CAN_DMU_RX_TSU_POINTER * ET_CAN_WIRE_WORD_BYTES],
                       rx.tsu_pointer);
            write_word(&response[ET_CAN_DMU_RX_TRANSFERRED_VALID * ET_CAN_WIRE_WORD_BYTES],
                       rx.transferred_timestamp_valid);
            write_word(&response[ET_CAN_DMU_RX_TRANSFERRED_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                       rx.transferred_timestamp);
        }

        return status;
    }

    status = et_can_wrap_decode_dmu_event(id, &image, &event);

    if (status == ET_WRAP_STATUS_OK)
    {
        write_word(&response[ET_CAN_TX_EVENT_IDENTIFIER * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.identifier);
        write_word(&response[ET_CAN_TX_EVENT_FLAGS * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.flags);
        write_word(&response[ET_CAN_TX_EVENT_DLC * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.dlc);
        write_word(&response[ET_CAN_TX_EVENT_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.timestamp);
        write_word(&response[ET_CAN_TX_EVENT_TYPE * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.event_type);
        write_word(&response[ET_CAN_TX_EVENT_MARKER * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.marker);
        write_word(&response[ET_CAN_TX_EVENT_INDEX * ET_CAN_WIRE_WORD_BYTES],
                   event.details.event.index);
        write_word(&response[ET_CAN_EVENT_INTERNAL_TIMESTAMP_VALID * ET_CAN_WIRE_WORD_BYTES],
                   event.details.internal_timestamp_valid);
        write_word(&response[ET_CAN_EVENT_TSU_CAPTURED * ET_CAN_WIRE_WORD_BYTES],
                   event.details.tsu_captured);
        write_word(&response[ET_CAN_EVENT_TSU_POINTER * ET_CAN_WIRE_WORD_BYTES],
                   event.details.tsu_pointer);
        write_word(&response[ET_CAN_DMU_EVENT_TRANSFERRED_VALID * ET_CAN_WIRE_WORD_BYTES],
                   event.transferred_timestamp_valid);
        write_word(&response[ET_CAN_DMU_EVENT_TRANSFERRED_TIMESTAMP * ET_CAN_WIRE_WORD_BYTES],
                   event.transferred_timestamp);
    }

    return status;
}

/**
 * @brief Execute one validated CAN command through the own Wrap.
 * @param[in,out] service Selected CAN Service and managed IRQ state.
 * @param[in] command Public command number.
 * @param[in] body Validated payload after the instance prefix.
 * @param[out] response Validated output storage, nullable for writes.
 * @return Own Wrap status without performing retry or test assertions.
 * @note Configuration queries read hardware independently of prior requests.
 */
/**
 * @brief Reset managed software context, IRQ bindings, and captured events for this CAN instance.
 * @param[in,out] service Selected CAN Service and managed IRQ state.
 * @return OK or shutdown failure.
 * @note Releases IRQ Manager routes, zeroes active event records, and updates generations.
 */
static et_wrap_status_t handle_context_reset(et_can_service_t *service)
{
    et_wrap_status_t status;

    if (service == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    /* Phase 1: Stop active captures and unbind routes from the IRQ Manager. */
    status = stop_irq_capture(service);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = stop_ecc_capture(service);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = stop_dmu_capture(service);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 2: Reset event records under critical section, updating generations. */
    status = irq_event_access(service, 1u, NULL);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = ecc_event_access(service, 1u, NULL);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    status = dmu_event_access(service, 1u, NULL);
    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    /* Phase 3: Clear runtime flags. */
    service->watched_sources = 0u;
    service->line1_sources = 0u;
    service->bound_lines = 0u;
    service->ecc_watched = 0u;
    service->ecc_bound = 0u;
    service->dmu_watched = 0u;
    service->dmu_bound = 0u;

    return ET_WRAP_STATUS_OK;
}

static et_wrap_status_t execute_command(et_can_service_t *service, uint16_t command,
                                        const uint8_t *body, uint8_t *response)
{
    et_can_id_t id = service->can_id;
    et_wrap_status_t status;
    et_can_identity_t identity;
    et_can_timing_t timing;
    et_can_timing_limits_t limits;
    et_can_options_t options;
    et_can_option_limits_t option_limits;
    uint8_t initializing;
    uint32_t requested;

    if (command == ET_CAN_COMMAND_CONTEXT_RESET)
    {
        return handle_context_reset(service);
    }

    if (command >= ET_CAN_COMMAND_DMU_WORD_ACCESS && command <= ET_CAN_COMMAND_DMU_EVENT_GET)
    {
        return execute_dmu_test_command(service, command, body, response);
    }

    if (command == ET_CAN_COMMAND_DMU_STATUS_CONSUME && service->dmu_watched != 0u)
    {
        return ET_WRAP_STATUS_BUSY;
    }

    if (command >= ET_CAN_COMMAND_DMU_TX_IMAGE_ENCODE &&
        command <= ET_CAN_COMMAND_DMU_EVENT_IMAGE_DECODE)
    {
        return execute_dmu_image_command(id, command, body, response);
    }

    if (command >= ET_CAN_COMMAND_DMU_ENDPOINT_GET && command <= ET_CAN_COMMAND_DMU_STATUS_CONSUME)
    {
        return execute_dmu_command(id, command, body, response);
    }

    if (command >= ET_CAN_COMMAND_ECC_ENABLE_SET && command <= ET_CAN_COMMAND_ECC_EVENT_RESET)
    {
        return execute_ecc_command(service, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_TSU_CONFIG_SET) &&
         (command <= ET_CAN_COMMAND_TSU_SLOT0_CONSUME)) ||
        ((command >= ET_CAN_COMMAND_DMU_TIMESTAMP_SET) &&
         (command <= ET_CAN_COMMAND_EXTERNAL_VECTOR_GET)))
    {
        return execute_tsu_command(id, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_RAM_WORDS_READ) &&
        (command <= ET_CAN_COMMAND_RAM_WORDS_EXCHANGE))
    {
        return execute_ram_access(id, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_IRQ_MASK_SET) && (command <= ET_CAN_COMMAND_IRQ_EVENT_RESET)) ||
        (command == ET_CAN_COMMAND_IRQ_CAPTURE_PENDING) ||
        (command == ET_CAN_COMMAND_IRQ_LINE_EVENTS_GET))
    {
        return execute_irq_command(service, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME) &&
         (command <= ET_CAN_COMMAND_CLOCK_STOP_ACK_GET)) ||
        (command == ET_CAN_COMMAND_TIMEOUT_RELOAD) ||
        (command == ET_CAN_COMMAND_TIMESTAMP_RESET_SNAPSHOT) ||
        (command == ET_CAN_COMMAND_RAM_WATCHDOG_GET))
    {
        return execute_status_command(id, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_FILTER_SET) && (command <= ET_CAN_COMMAND_EXTENDED_MASK_GET)) ||
        (command == ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET))
    {
        return execute_filter_command(id, command, body, response);
    }

    if (((command >= ET_CAN_COMMAND_TX_EVENT_STATUS_GET) &&
         (command <= ET_CAN_COMMAND_TX_EVENT_ACK)) ||
        ((command >= ET_CAN_COMMAND_EVENT_FORMAT_SET) &&
         (command <= ET_CAN_COMMAND_TX_EVENT_DETAILS_READ)))
    {
        return execute_tx_event_command(id, command, body, response);
    }

    /* RAM commands form one own-IP codec group; no orchestration is hidden here. */
    if ((command >= ET_CAN_COMMAND_RAM_LIMITS_GET) && (command <= ET_CAN_COMMAND_RAM_LAYOUT_GET))
    {
        return execute_ram_command(id, command, body, response);
    }

    /* Phase 1: Decode state-changing requests without inventing missing parameters. */
    if (((command >= ET_CAN_COMMAND_TX_WRITE) && (command <= ET_CAN_COMMAND_TX_STATUS_GET)) ||
        (command == ET_CAN_COMMAND_TX_READ))
    {
        return execute_tx_command(id, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_RX_FIFO_STATUS_GET) && (command <= ET_CAN_COMMAND_RX_BUFFER_ACK))
    {
        return execute_rx_command(id, command, body, response);
    }

    if ((command >= ET_CAN_COMMAND_BUS_CONFIG_SET) && (command <= ET_CAN_COMMAND_BUS_LIMITS_GET))
    {
        return execute_bus_command(id, command, body, response);
    }

    switch (command)
    {
        case ET_CAN_COMMAND_CONFIGURATION_WRITE_SET:
        {
            requested = read_word(body);

            if (requested > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_configuration_access(id, (uint8_t)requested, NULL);
        }

        case ET_CAN_COMMAND_NON_ISO_SET:
        {
            requested = read_word(body);

            if (requested > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_non_iso_access(id, (uint8_t)requested, NULL);
        }

        case ET_CAN_COMMAND_NON_ISO_GET:
        {
            status = et_can_wrap_non_iso_access(id, 0u, &initializing);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, initializing);
            }

            return status;
        }

        case ET_CAN_COMMAND_CONFIGURATION_WRITE_GET:
        {
            status = et_can_wrap_configuration_access(id, 0u, &initializing);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, initializing);
            }

            return status;
        }

        case ET_CAN_COMMAND_NOMINAL_TIMING_WRITE:
        {
            decode_phase(body, &timing.nominal);

            return et_can_wrap_write_nominal_timing(id, &timing.nominal);
        }

        case ET_CAN_COMMAND_TX_BUFFER_IRQ_SET:
        {
            requested = read_word(&body[ET_CAN_WIRE_WORD_BYTES]);

            if (requested > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_set_tx_buffer_irq(id, read_word(body), (uint8_t)requested);
        }

        case ET_CAN_COMMAND_INITIALIZING_SET:
        {
            requested = read_word(body);

            if (requested > 1u)
            {
                return ET_WRAP_STATUS_INVALID_ARGUMENT;
            }

            return et_can_wrap_set_initializing(id, (uint8_t)requested);
        }

        case ET_CAN_COMMAND_TIMING_SET:
        {
            decode_phase(body, &timing.nominal);
            decode_phase(&body[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES], &timing.data);

            return et_can_wrap_set_timing(id, &timing);
        }

        case ET_CAN_COMMAND_OPTIONS_SET:
        {
            decode_options(body, &options);

            return et_can_wrap_set_options(id, &options);
        }

        default:
        {
            break;
        }
    }

    /* Phase 2: Query the requested facts and publish only successful readbacks. */
    switch (command)
    {
        case ET_CAN_COMMAND_IDENTITY_GET:
        {
            status = et_can_wrap_get_identity(id, &identity);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, identity.revision);
                write_word(&response[ET_CAN_WIRE_WORD_BYTES], identity.endian);
            }

            return status;
        }

        case ET_CAN_COMMAND_INITIALIZING_GET:
        {
            status = et_can_wrap_get_initializing(id, &initializing);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(response, initializing);
            }

            return status;
        }

        case ET_CAN_COMMAND_TIMING_LIMITS_GET:
        {
            status = et_can_wrap_get_timing_limits(id, &limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_phase(response, &limits.nominal_max);
                encode_phase(&response[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES],
                             &limits.data_max);
            }

            return status;
        }

        case ET_CAN_COMMAND_TIMING_GET:
        {
            status = et_can_wrap_get_timing(id, &timing);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_phase(response, &timing.nominal);
                encode_phase(&response[ET_CAN_PHASE_WORDS * ET_CAN_WIRE_WORD_BYTES], &timing.data);
            }

            return status;
        }

        case ET_CAN_COMMAND_OPTIONS_GET:
        {
            status = et_can_wrap_get_options(id, &options);

            if (status == ET_WRAP_STATUS_OK)
            {
                encode_options(response, &options);
            }

            return status;
        }

        case ET_CAN_COMMAND_OPTION_LIMITS_GET:
        {
            status = et_can_wrap_get_option_limits(id, &option_limits);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_word(&response[ET_CAN_LIMIT_TDC_OFFSET * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.tdc_offset_cycles);
                write_word(&response[ET_CAN_LIMIT_TDC_FILTER * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.tdc_filter_cycles);
                write_word(&response[ET_CAN_LIMIT_RAM_WATCHDOG * ET_CAN_WIRE_WORD_BYTES],
                           option_limits.ram_watchdog_cycles);
            }

            return status;
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Validate the complete CAN envelope before invoking a primitive.
 * @param[in,out] context Initialized CAN descriptor storage.
 * @param[in] command_id Public command number.
 * @param[in] request_body Request bytes including the logical instance prefix.
 * @param[in] request_length Exact request byte count.
 * @param[out] response_body Storage for requested facts, nullable for write commands.
 * @param[in] response_capacity Available output capacity in bytes.
 * @param[out] response_length Actual size, zero for every error.
 * @return Existing ET protocol status.
 * @note Malformed bodies never reach hardware; polling and final verdict stay on PC.
 */
static uint16_t can_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    /* Unlisted entries have no words; named indices prevent command-order drift. */
    static const uint8_t input_words[ET_CAN_COMMAND_COUNT] = {
        [ET_CAN_COMMAND_INITIALIZING_SET] = 1u,
        [ET_CAN_COMMAND_TIMING_SET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_OPTIONS_SET] = ET_CAN_OPTIONS_WORDS,
        [ET_CAN_COMMAND_RAM_LAYOUT_SET] = ET_CAN_RAM_LAYOUT_WORDS,
        [ET_CAN_COMMAND_BUS_CONFIG_SET] = ET_CAN_BUS_CONFIG_WORDS,
        [ET_CAN_COMMAND_DMU_ENDPOINT_GET] = 1u,
        [ET_CAN_COMMAND_DMU_WORD_ACCESS] = ET_CAN_DMU_ACCESS_WORDS,
        [ET_CAN_COMMAND_DMU_CAPTURE_START] = 1u,
        [ET_CAN_COMMAND_DMU_TIMESTAMP_SET] = 1u,
        [ET_CAN_COMMAND_FILTER_SYNC_SET] = ET_CAN_FILTER_SYNC_SET_WORDS,
        [ET_CAN_COMMAND_FILTER_SYNC_GET] = ET_CAN_FILTER_SELECT_WORDS,
        [ET_CAN_COMMAND_RX_TIMESTAMP_GET] = 1u,
        [ET_CAN_COMMAND_EXTERNAL_VECTOR_SET] = 1u,
        [ET_CAN_COMMAND_DMU_REQUEST_SET] = 1u,
        [ET_CAN_COMMAND_LOOPBACK_SET] = 1u,
        [ET_CAN_COMMAND_TX_WRITE] = ET_CAN_TX_WRITE_WORDS,
        [ET_CAN_COMMAND_TX_REQUEST] = 1u,
        [ET_CAN_COMMAND_RX_FIFO_STATUS_GET] = 1u,
        [ET_CAN_COMMAND_RX_READ] = ET_CAN_RX_SELECT_WORDS,
        [ET_CAN_COMMAND_RX_FIFO_ACK] = ET_CAN_RX_SELECT_WORDS,
        [ET_CAN_COMMAND_RX_BUFFER_ACK] = ET_CAN_RX_BITMAP_WORDS,
        [ET_CAN_COMMAND_FILTER_SET] = ET_CAN_FILTER_SET_WORDS,
        [ET_CAN_COMMAND_FILTER_GET] = ET_CAN_FILTER_SELECT_WORDS,
        [ET_CAN_COMMAND_EXTENDED_MASK_SET] = 1u,
        [ET_CAN_COMMAND_CLOCK_STOP_SET] = 1u,
        [ET_CAN_COMMAND_IRQ_MASK_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_IRQ_LINE_SELECT_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_IRQ_CLEAR] = 1u,
        [ET_CAN_COMMAND_IRQ_CAPTURE_START] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_IRQ_CAPTURE_PENDING] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_TX_EVENT_ACK] = 1u,
        [ET_CAN_COMMAND_TX_READ] = 1u,
        [ET_CAN_COMMAND_TX_BUFFER_IRQ_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_RAM_WORDS_READ] = ET_CAN_RAM_ACCESS_SELECT_WORDS,
        [ET_CAN_COMMAND_RAM_WORDS_WRITE] = ET_CAN_RAM_ACCESS_WRITE_WORDS,
        [ET_CAN_COMMAND_RAM_WORDS_EXCHANGE] = ET_CAN_RAM_ACCESS_WRITE_WORDS,
        [ET_CAN_COMMAND_CONFIGURATION_WRITE_SET] = 1u,
        [ET_CAN_COMMAND_NON_ISO_SET] = 1u,
        [ET_CAN_COMMAND_EVENT_FORMAT_SET] = ET_CAN_EVENT_FORMAT_WORDS,
        [ET_CAN_COMMAND_TSU_CONFIG_SET] = ET_CAN_TSU_CONFIG_WORDS,
        [ET_CAN_COMMAND_ECC_ENABLE_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_ECC_MASK_SET] = ET_CAN_IRQ_CONTROL_WORDS,
        [ET_CAN_COMMAND_ECC_FORCE] = 1u,
        [ET_CAN_COMMAND_ECC_CLEAR] = 1u,
        [ET_CAN_COMMAND_ECC_CAPTURE_START] = 1u,
        [ET_CAN_COMMAND_DMU_TX_IMAGE_ENCODE] = ET_CAN_TX_WRITE_WORDS,
        [ET_CAN_COMMAND_DMU_RX_IMAGE_DECODE] = ET_CAN_DMU_RX_IMAGE_REQUEST_WORDS,
        [ET_CAN_COMMAND_DMU_EVENT_IMAGE_DECODE] = ET_CAN_DMU_IMAGE_ENVELOPE_WORDS,
        [ET_CAN_COMMAND_NOMINAL_TIMING_WRITE] = ET_CAN_PHASE_WORDS};
    static const uint8_t output_words[ET_CAN_COMMAND_COUNT] = {
        [ET_CAN_COMMAND_IDENTITY_GET] = ET_CAN_IDENTITY_WORDS,
        [ET_CAN_COMMAND_INITIALIZING_GET] = 1u,
        [ET_CAN_COMMAND_TIMING_LIMITS_GET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_TIMING_GET] = ET_CAN_TIMING_WORDS,
        [ET_CAN_COMMAND_OPTIONS_GET] = ET_CAN_OPTIONS_WORDS,
        [ET_CAN_COMMAND_OPTION_LIMITS_GET] = ET_CAN_OPTION_LIMIT_WORDS,
        [ET_CAN_COMMAND_RAM_LIMITS_GET] = ET_CAN_RAM_LIMIT_WORDS,
        [ET_CAN_COMMAND_RAM_LAYOUT_GET] = ET_CAN_RAM_LAYOUT_WORDS,
        [ET_CAN_COMMAND_BUS_CONFIG_GET] = ET_CAN_BUS_CONFIG_WORDS,
        [ET_CAN_COMMAND_LOOPBACK_GET] = 1u,
        [ET_CAN_COMMAND_BUS_LIMITS_GET] = ET_CAN_BUS_LIMIT_WORDS,
        [ET_CAN_COMMAND_TX_STATUS_GET] = ET_CAN_TX_STATUS_WORDS,
        [ET_CAN_COMMAND_RX_FIFO_STATUS_GET] = ET_CAN_RX_FIFO_STATUS_WORDS,
        [ET_CAN_COMMAND_RX_READ] = ET_CAN_RX_FRAME_WORDS,
        [ET_CAN_COMMAND_RX_BUFFER_STATUS_GET] = ET_CAN_RX_BITMAP_WORDS,
        [ET_CAN_COMMAND_FILTER_GET] = ET_CAN_FILTER_CONFIG_WORDS,
        [ET_CAN_COMMAND_EXTENDED_MASK_GET] = 1u,
        [ET_CAN_COMMAND_PROTOCOL_STATUS_CONSUME] = ET_CAN_PROTOCOL_STATUS_WORDS,
        [ET_CAN_COMMAND_TIMESTAMP_GET] = 1u,
        [ET_CAN_COMMAND_TIMEOUT_COUNTER_GET] = 1u,
        [ET_CAN_COMMAND_CLOCK_STOP_ACK_GET] = 1u,
        [ET_CAN_COMMAND_IRQ_SNAPSHOT_GET] = ET_CAN_IRQ_SNAPSHOT_WORDS,
        [ET_CAN_COMMAND_IRQ_LINE_EVENTS_GET] = ET_CAN_IRQ_LINE_COUNT,
        [ET_CAN_COMMAND_RAM_WORDS_READ] = ET_CAN_RAM_ACCESS_WORDS,
        [ET_CAN_COMMAND_CONFIGURATION_WRITE_GET] = 1u,
        [ET_CAN_COMMAND_NON_ISO_GET] = 1u,
        [ET_CAN_COMMAND_EVENT_FORMAT_GET] = ET_CAN_EVENT_FORMAT_WORDS,
        [ET_CAN_COMMAND_TX_EVENT_DETAILS_READ] = ET_CAN_EVENT_DETAILS_WORDS,
        [ET_CAN_COMMAND_TIMEOUT_RELOAD] = ET_CAN_COUNTER_RELOAD_WORDS,
        [ET_CAN_COMMAND_TIMESTAMP_RESET_SNAPSHOT] = ET_CAN_COUNTER_RELOAD_WORDS,
        [ET_CAN_COMMAND_TSU_CONFIG_GET] = ET_CAN_TSU_CONFIG_WORDS,
        [ET_CAN_COMMAND_TSU_LIMITS_GET] = ET_CAN_TSU_LIMITS_WORDS,
        [ET_CAN_COMMAND_TSU_FLAGS_GET] = ET_CAN_TSU_FLAGS_WORDS,
        [ET_CAN_COMMAND_TSU_TIMEBASE_GET] = 1u,
        [ET_CAN_COMMAND_TSU_SLOT0_CONSUME] = 1u,
        [ET_CAN_COMMAND_ECC_SNAPSHOT_GET] = ET_CAN_ECC_SNAPSHOT_WORDS,
        [ET_CAN_COMMAND_DMU_ENDPOINT_GET] = 1u,
        [ET_CAN_COMMAND_DMU_REQUEST_GET] = 1u,
        [ET_CAN_COMMAND_DMU_COUNTERS_GET] = ET_CAN_DMU_COUNTER_WORDS,
        [ET_CAN_COMMAND_DMU_WORD_ACCESS] = 1u,
        [ET_CAN_COMMAND_DMU_EVENT_GET] = ET_CAN_DMU_EVENT_WORDS,
        [ET_CAN_COMMAND_FILTER_SYNC_GET] = 1u,
        [ET_CAN_COMMAND_RX_TIMESTAMP_GET] = ET_CAN_RX_TIMESTAMP_WORDS,
        [ET_CAN_COMMAND_EXTERNAL_VECTOR_GET] = 1u,
        [ET_CAN_COMMAND_RAM_WATCHDOG_GET] = ET_CAN_RAM_WATCHDOG_WORDS,
        [ET_CAN_COMMAND_DMU_STATUS_CONSUME] = ET_CAN_DMU_STATUS_WORDS,
        [ET_CAN_COMMAND_DMU_TX_IMAGE_ENCODE] = ET_CAN_DMU_IMAGE_ENVELOPE_WORDS,
        [ET_CAN_COMMAND_DMU_RX_IMAGE_DECODE] = ET_CAN_DMU_RX_IMAGE_RESPONSE_WORDS,
        [ET_CAN_COMMAND_DMU_EVENT_IMAGE_DECODE] = ET_CAN_DMU_EVENT_IMAGE_RESPONSE_WORDS,
        [ET_CAN_COMMAND_ECC_EVENT_GET] = ET_CAN_ECC_EVENT_WORDS,
        [ET_CAN_COMMAND_RAM_WORDS_EXCHANGE] = ET_CAN_RAM_ACCESS_WORDS,
        [ET_CAN_COMMAND_IRQ_EVENT_GET] = ET_CAN_IRQ_EVENT_WORDS,
        [ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET] = ET_CAN_HIGH_PRIORITY_STATUS_WORDS,
        [ET_CAN_COMMAND_TX_EVENT_STATUS_GET] = ET_CAN_TX_EVENT_STATUS_WORDS,
        [ET_CAN_COMMAND_TX_EVENT_READ] = ET_CAN_TX_EVENT_WORDS,
        [ET_CAN_COMMAND_TX_READ] = ET_CAN_TX_WRITE_WORDS};
    et_can_service_t *service = (et_can_service_t *)context;
    uint16_t output_bytes;
    et_wrap_status_t status;

    /* Phase 1: Validate command identity and all buffer bounds before decoding. */
    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (command_id >= ET_CAN_COMMAND_COUNT)
    {
        return ET_STATUS_INVALID_COMMAND;
    }

    output_bytes = output_words[command_id] * ET_CAN_WIRE_WORD_BYTES;

    if ((service == NULL) || (request_body == NULL) ||
        (request_length !=
         ET_CAN_REQUEST_PREFIX_BYTES + input_words[command_id] * ET_CAN_WIRE_WORD_BYTES) ||
        (request_body[0] != service->can_id) || (response_capacity < output_bytes) ||
        ((output_bytes != 0u) && (response_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute one action and publish the contract length only on success. */
    status = execute_command(service, command_id, &request_body[ET_CAN_REQUEST_PREFIX_BYTES],
                             response_body);

    if (status == ET_WRAP_STATUS_OK)
    {
        *response_length = output_bytes;
    }

    return status_from_wrap(status);
}

/**
 * @brief Initialize static Service metadata without touching the CAN controller.
 * @param[out] service Application-owned storage.
 * @param[in] can_id Logical controller identity representable by the instance byte.
 * @param[in,out] irq_manager Required factory dependency; no IRQ binding occurs here.
 * @param[in] irq_priority Board-selected priority used by explicit managed IRQ capture.
 * @return Zero on success, minus one for invalid descriptor inputs.
 * @note Does not enable clocks, configure GPIO, initialize CAN or allocate resources.
 */
int et_can_service_init(et_can_service_t *service, et_can_id_t can_id,
                        et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL) || (can_id > UINT8_MAX))
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->can_id = can_id;
    service->ecc_event[ET_CAN_ECC_EVENT_INSTANCE] = UINT32_MAX;
    service->dmu_event[ET_CAN_DMU_EVENT_INSTANCE] = UINT32_MAX;
    service->irq_manager = irq_manager;
    service->irq_priority = irq_priority;
    service->descriptor.service_id = ET_CAN_SERVICE_ID;
    service->descriptor.instance_id = can_id;
    service->descriptor.context = service;
    service->descriptor.handle = can_handle;

    return 0;
}

/**
 * @brief Return the initialized descriptor without transferring ownership.
 * @param[in] service Application-owned storage.
 * @return Descriptor pointer or NULL for a null Service.
 * @note Performs no state or hardware mutation.
 */
const et_service_descriptor_t *et_can_service_descriptor(const et_can_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct a CAN Service through the existing factory contract.
 * @param[out] storage Application-owned Service memory.
 * @param[in] instance_id Logical CAN identity.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Registered command descriptor.
 * @return Zero on success, otherwise minus one.
 * @note No CAN initialization or IRQ activation is performed by registration.
 */
int et_can_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_can_service_t *service = (et_can_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_can_service_init(service, (et_can_id_t)instance_id, context->irq_manager,
                            context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_can_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
