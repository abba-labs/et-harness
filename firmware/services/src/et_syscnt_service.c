/** @file et_syscnt_service.c @brief Decode one counter action and encode raw facts. */
#include "et_syscnt_service.h"

#include <stddef.h>
#include <string.h>
#include <limits.h>

/**
 * @brief Translate Wrap result without losing busy or unsupported distinctions.
 * @param[in] status Own Wrap result.
 * @return Existing ET protocol status.
 * @note No hardware operation or retry occurs here.
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
 * @brief Decode one unsigned little-endian integer without alignment assumptions.
 * @param[in] data Validated source bytes.
 * @param[in] size Public field width, at most the u64 count size.
 * @return Decoded unsigned integer.
 * @note Called only after exact request-length validation.
 */
static uint64_t read_integer(const uint8_t *data, uint16_t size)
{
    uint64_t value = 0u;
    uint16_t index;

    for (index = 0u; index < size; ++index)
    {
        value |= (uint64_t)data[index] << (index * CHAR_BIT);
    }

    return value;
}

/**
 * @brief Encode an unsigned integer as little-endian bytes.
 * @param[out] data Validated response storage.
 * @param[in] value Raw integer to encode.
 * @param[in] size Field width, at most the u64 count size.
 * @note Response capacity is validated before any caller reaches this helper.
 */
static void write_integer(uint8_t *data, uint64_t value, uint16_t size)
{
    uint16_t index;

    for (index = 0u; index < size; ++index)
    {
        data[index] = (uint8_t)(value >> (index * CHAR_BIT));
    }
}

/**
 * @brief Execute a capability query and encode the public widths and action flags.
 * @param[in] id Logical counter identity.
 * @param[out] response Validated capability response storage.
 * @return Own Wrap result.
 * @note Reads static capability facts, not runtime test coverage.
 */
static et_wrap_status_t encode_capabilities(et_syscnt_id_t id, uint8_t *response)
{
    et_syscnt_capabilities_t caps;
    et_wrap_status_t status = et_syscnt_wrap_get_capabilities(id, &caps);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    write_integer(&response[ET_SYSCNT_CAP_FLAGS_OFFSET], caps.feature_flags,
                  ET_SYSCNT_RESPONSE_WORD_SIZE);
    response[ET_SYSCNT_CAP_BITS_OFFSET] = caps.counter_bits;
    response[ET_SYSCNT_CAP_VIEWS_OFFSET] = caps.read_view_mask;
    response[ET_SYSCNT_CAP_REFERENCE_BITS_OFFSET] = caps.reference_bits;
    response[ET_SYSCNT_CAP_WORD_BITS_OFFSET] = caps.counter_word_bits;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute a control query and encode its distinct fields.
 * @param[in] id Logical counter identity.
 * @param[out] response Validated control response storage.
 * @return Own Wrap result.
 * @note Policy, hardware halt state and frequency metadata remain separate.
 */
static et_wrap_status_t encode_control(et_syscnt_id_t id, uint8_t *response)
{
    et_syscnt_control_t control;
    et_wrap_status_t status = et_syscnt_wrap_get_control(id, &control);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    response[ET_SYSCNT_CONTROL_ENABLE_OFFSET] = control.enabled;
    response[ET_SYSCNT_CONTROL_POLICY_OFFSET] = control.halt_policy;
    response[ET_SYSCNT_CONTROL_HALTED_OFFSET] = control.debug_halted;
    response[ET_SYSCNT_CONTROL_RESERVED_OFFSET] = 0u;
    write_integer(&response[ET_SYSCNT_CONTROL_FREQUENCY_OFFSET], control.frequency_id_hz,
                  ET_SYSCNT_RESPONSE_WORD_SIZE);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Execute one bounded reference sample and encode three raw counters.
 * @param[in] id Logical counter identity.
 * @param[out] response Validated sample response storage.
 * @return Own Wrap result.
 * @note No sampling loop, time conversion or Case oracle is implemented here.
 */
static et_wrap_status_t encode_sample(et_syscnt_id_t id, uint8_t *response)
{
    et_syscnt_reference_sample_t sample;
    et_wrap_status_t status = et_syscnt_wrap_sample_reference(id, &sample);

    if (status != ET_WRAP_STATUS_OK)
    {
        return status;
    }

    write_integer(&response[ET_SYSCNT_SAMPLE_BEFORE_OFFSET], sample.reference_before,
                  ET_SYSCNT_RESPONSE_COUNT_SIZE);
    write_integer(&response[ET_SYSCNT_SAMPLE_COUNT_OFFSET], sample.count,
                  ET_SYSCNT_RESPONSE_COUNT_SIZE);
    write_integer(&response[ET_SYSCNT_SAMPLE_AFTER_OFFSET], sample.reference_after,
                  ET_SYSCNT_RESPONSE_COUNT_SIZE);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Decode a validated command and invoke exactly its own counter action.
 * @param[in] id Logical counter identity.
 * @param[in] command Command validated against the size tables.
 * @param[in] body Validated command request, including the instance byte.
 * @param[out] response Validated output storage; may be NULL for a write command.
 * @return Stable Wrap status for the selected action.
 * @note No implicit initialization, resource reset or cross-IP sequence is executed.
 */
static et_wrap_status_t execute_command(et_syscnt_id_t id, uint16_t command, const uint8_t *body,
                                        uint8_t *response)
{
    uint64_t count;
    et_wrap_status_t status;

    switch (command)
    {
        case ET_SYSCNT_COMMAND_CAPABILITIES_GET:
        {
            return encode_capabilities(id, response);
        }

        case ET_SYSCNT_COMMAND_ENABLE_SET:
        {
            return et_syscnt_wrap_set_enabled(id, body[ET_SYSCNT_REQUEST_VALUE_OFFSET]);
        }

        case ET_SYSCNT_COMMAND_VALUE_LOAD:
        {
            return et_syscnt_wrap_load_value(id, read_integer(&body[ET_SYSCNT_REQUEST_VALUE_OFFSET],
                                                              ET_SYSCNT_RESPONSE_COUNT_SIZE));
        }

        case ET_SYSCNT_COMMAND_COUNT_GET:
        {
            status = et_syscnt_wrap_get_count(
                id, (et_syscnt_view_t)body[ET_SYSCNT_REQUEST_VALUE_OFFSET], &count);

            if (status == ET_WRAP_STATUS_OK)
            {
                write_integer(response, count, ET_SYSCNT_RESPONSE_COUNT_SIZE);
            }

            return status;
        }

        case ET_SYSCNT_COMMAND_CONTROL_GET:
        {
            return encode_control(id, response);
        }

        case ET_SYSCNT_COMMAND_HALT_POLICY_SET:
        {
            return et_syscnt_wrap_set_halt_policy(
                id, (et_syscnt_halt_policy_t)body[ET_SYSCNT_REQUEST_VALUE_OFFSET]);
        }

        case ET_SYSCNT_COMMAND_FREQUENCY_ID_SET:
        {
            return et_syscnt_wrap_set_frequency_id(
                id, (uint32_t)read_integer(&body[ET_SYSCNT_REQUEST_VALUE_OFFSET],
                                           ET_SYSCNT_RESPONSE_WORD_SIZE));
        }

        case ET_SYSCNT_COMMAND_REFERENCE_SAMPLE_GET:
        {
            return encode_sample(id, response);
        }

        case ET_SYSCNT_COMMAND_REFERENCE_ENABLE_SET:
        {
            return et_syscnt_wrap_set_reference_enabled(id, body[ET_SYSCNT_REQUEST_VALUE_OFFSET]);
        }

        default:
        {
            return ET_WRAP_STATUS_NOT_SUPPORTED;
        }
    }
}

/**
 * @brief Validate one complete command envelope before executing hardware.
 * @param[in,out] context Initialized Service descriptor storage.
 * @param[in] command_id Public SYSCNT command number.
 * @param[in] request_body Request bytes, beginning with logical instance.
 * @param[in] request_length Exact request byte count.
 * @param[out] response_body Output storage for raw facts.
 * @param[in] response_capacity Available output bytes.
 * @param[out] response_length Success response size, zero on failure.
 * @return Existing ET status; malformed input never reaches the Wrap.
 * @note There is no asynchronous state, Case progression or retry in this handler.
 */
static uint16_t syscnt_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                              uint16_t request_length, uint8_t *response_body,
                              uint16_t response_capacity, uint16_t *response_length)
{
    /* Tables follow the contiguous public command enum, not chip register offsets. */
    static const uint8_t request_sizes[ET_SYSCNT_COMMAND_COUNT] = {
        ET_SYSCNT_REQUEST_EMPTY_SIZE, ET_SYSCNT_REQUEST_BYTE_SIZE,  ET_SYSCNT_REQUEST_COUNT_SIZE,
        ET_SYSCNT_REQUEST_BYTE_SIZE,  ET_SYSCNT_REQUEST_EMPTY_SIZE, ET_SYSCNT_REQUEST_BYTE_SIZE,
        ET_SYSCNT_REQUEST_WORD_SIZE,  ET_SYSCNT_REQUEST_EMPTY_SIZE, ET_SYSCNT_REQUEST_BYTE_SIZE};
    static const uint8_t response_sizes[ET_SYSCNT_COMMAND_COUNT] = {
        ET_SYSCNT_RESPONSE_CAPABILITIES_SIZE, ET_SYSCNT_RESPONSE_EMPTY_SIZE,
        ET_SYSCNT_RESPONSE_EMPTY_SIZE,        ET_SYSCNT_RESPONSE_COUNT_SIZE,
        ET_SYSCNT_RESPONSE_CONTROL_SIZE,      ET_SYSCNT_RESPONSE_EMPTY_SIZE,
        ET_SYSCNT_RESPONSE_EMPTY_SIZE,        ET_SYSCNT_RESPONSE_SAMPLE_SIZE,
        ET_SYSCNT_RESPONSE_EMPTY_SIZE};
    et_syscnt_service_t *service = (et_syscnt_service_t *)context;
    et_wrap_status_t status;

    /* Phase 1: Validate pointers and command before indexing fixed contract tables. */
    if (response_length == NULL)
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    if (command_id >= ET_SYSCNT_COMMAND_COUNT)
    {
        return ET_STATUS_INVALID_COMMAND;
    }

    if ((service == NULL) || (request_body == NULL) ||
        (request_length != request_sizes[command_id]) ||
        (request_body[ET_SYSCNT_REQUEST_ID_OFFSET] != service->syscnt_id) ||
        (response_capacity < response_sizes[command_id]) ||
        ((response_sizes[command_id] != 0u) && (response_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    /* Phase 2: Execute the single requested action; publish length only on success. */
    status = execute_command(service->syscnt_id, command_id, request_body, response_body);

    if (status == ET_WRAP_STATUS_OK)
    {
        *response_length = response_sizes[command_id];
    }

    return status_from_wrap(status);
}

/**
 * @brief Initialize a counter descriptor without changing hardware.
 * @param[out] service Application-owned Service storage.
 * @param[in] syscnt_id Logical identity representable by the public instance byte.
 * @param[in,out] irq_manager Factory dependency; no counter IRQ is allocated.
 * @param[in] irq_priority Unused common factory parameter.
 * @return Zero on success or minus one for invalid descriptor inputs.
 * @note No count, clock, reference or halt state is changed during registration.
 */
int et_syscnt_service_init(et_syscnt_service_t *service, et_syscnt_id_t syscnt_id,
                           et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL) || (syscnt_id > UINT8_MAX))
    {
        return -1;
    }

    (void)irq_priority;
    (void)memset(service, 0, sizeof(*service));
    service->syscnt_id = syscnt_id;
    service->descriptor.service_id = ET_SYSCNT_SERVICE_ID;
    service->descriptor.instance_id = syscnt_id;
    service->descriptor.context = service;
    service->descriptor.handle = syscnt_handle;

    return 0;
}

/**
 * @brief Return the initialized Service descriptor.
 * @param[in] service Application-owned initialized storage.
 * @return Descriptor alias, or NULL for a null Service.
 * @note No state or hardware change is made.
 */
const et_service_descriptor_t *et_syscnt_service_descriptor(const et_syscnt_service_t *service)
{
    return service == NULL ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Construct a counter Service through the existing platform factory.
 * @param[out] storage Application-owned Service memory.
 * @param[in] instance_id Logical counter identity.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Registered handler descriptor.
 * @return Zero on success, otherwise minus one.
 * @note Factory construction performs no counter initialization.
 */
int et_syscnt_service_create(void *storage, uint16_t instance_id,
                             const et_service_factory_context_t *context,
                             const et_service_descriptor_t **descriptor)
{
    et_syscnt_service_t *service = (et_syscnt_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_syscnt_service_init(service, (et_syscnt_id_t)instance_id, context->irq_manager,
                               context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_syscnt_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
