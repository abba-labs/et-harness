/**
 * @file et_spinlock_service.c
 * @brief Decode stable SPINLOCK commands and call only SPINLOCK Wrap operations.
 */

#include "et_spinlock_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/**
 * @brief Read one little-endian 16-bit Wire value.
 * @param[in] data Two readable Wire bytes.
 * @note This helper has no hardware side effect.
 * @return Decoded value.
 */
static uint16_t read_u16(const uint8_t *data)
{
    return (uint16_t)((uint16_t)data[0] | ((uint16_t)data[1] << 8u));
}

/**
 * @brief Read one little-endian 32-bit Wire value.
 * @param[in] data Four readable Wire bytes.
 * @note This helper has no hardware side effect.
 * @return Decoded value.
 */
static uint32_t read_u32(const uint8_t *data)
{
    return (uint32_t)data[0] | ((uint32_t)data[1] << 8u) | ((uint32_t)data[2] << 16u) |
           ((uint32_t)data[3] << 24u);
}

/**
 * @brief Write one little-endian 16-bit Wire value.
 * @param[out] data Two writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This helper writes only caller-owned response storage.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Write one little-endian 32-bit Wire value.
 * @param[out] data Four writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This helper writes only caller-owned response storage.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
    data[2] = (uint8_t)((value >> 16u) & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
    data[3] = (uint8_t)((value >> 24u) & ET_SPINLOCK_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Check one reserved Wire range for zero-filled forward-compatibility bytes.
 * @param[in] data First reserved byte.
 * @param[in] size Number of reserved bytes.
 * @note The caller validates the enclosing request length first.
 * @return Nonzero when all bytes are zero, otherwise zero.
 */
static uint8_t bytes_are_zero(const uint8_t *data, uint16_t size)
{
    uint16_t index;

    for (index = 0u; index < size; ++index)
    {
        if (data[index] != 0u)
        {
            return 0u;
        }
    }

    return 1u;
}

/**
 * @brief Translate one SPINLOCK Wrap result into the stable protocol status.
 * @param[in] status SPINLOCK Wrap status.
 * @note A bounded acquire timeout is reported as BUSY to the PC Driver.
 * @return Stable ET protocol status.
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
        case ET_WRAP_STATUS_TIMEOUT:
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
 * @brief Dispatch one validated SPINLOCK command to the matching Wrap operation.
 * @param[in,out] context SPINLOCK Service retained by the Router.
 * @param[in] command_id Stable SPINLOCK command identifier.
 * @param[in] request_body Optional request body.
 * @param[in] request_length Number of valid request bytes.
 * @param[out] response_body Caller-owned response storage.
 * @param[in] response_capacity Available response bytes.
 * @param[out] response_length Number of response bytes produced.
 * @note The handler contains no Case oracle and calls only SPINLOCK Wrap.
 * @return Stable ET protocol status.
 */
static uint16_t spinlock_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                                uint16_t request_length, uint8_t *response_body,
                                uint16_t response_capacity, uint16_t *response_length)
{
    et_spinlock_service_t *service = (et_spinlock_service_t *)context;
    et_spinlock_wrap_capabilities_t capabilities;
    et_spinlock_wrap_config_snapshot_t config;
    et_spinlock_wrap_flag_snapshot_t flags;
    et_spinlock_wrap_resource_snapshot_t resource;
    et_spinlock_wrap_peer_job_config_t peer_job_config;
    et_spinlock_wrap_peer_job_snapshot_t peer_job_snapshot;
    et_spinlock_wrap_shared_snapshot_t shared_snapshot;
    et_wrap_status_t wrap_status;
    uint32_t loop_count;
    uint32_t completed_count;
    uint16_t master_id;
    uint16_t resource_id;
    uint16_t process_id;
    uint8_t peer_ready;

    /* Phase 1: Validate the common Router envelope and reset the response length. */
    if ((service == NULL) || (response_length == NULL) ||
        ((request_length != 0u) && (request_body == NULL)))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 2: Validate the selected Wire body, call only SPINLOCK Wrap and encode facts. */
    switch (command_id)
    {
        case ET_SPINLOCK_COMMAND_CAPABILITIES_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_CAPABILITIES_SIZE) ||
                (et_spinlock_wrap_capabilities_get(service->spinlock_id, &capabilities) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u16(&response_body[ET_SPINLOCK_SERVICE_CAPS_API_VERSION_OFFSET],
                      ET_SPINLOCK_SERVICE_API_VERSION);
            write_u16(&response_body[ET_SPINLOCK_SERVICE_CAPS_STRUCT_SIZE_OFFSET],
                      ET_SPINLOCK_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_SPINLOCK_SERVICE_CAPS_FEATURES_OFFSET],
                      capabilities.features);
            write_u16(&response_body[ET_SPINLOCK_SERVICE_CAPS_RESOURCE_COUNT_OFFSET],
                      capabilities.resource_count);
            write_u16(&response_body[ET_SPINLOCK_SERVICE_CAPS_PROCESS_COUNT_OFFSET],
                      capabilities.process_id_count);
            *response_length = ET_SPINLOCK_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_CONFIGURE:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_CONFIG_SIZE) ||
                (bytes_are_zero(&request_body[ET_SPINLOCK_SERVICE_CONFIG_RESERVED_OFFSET],
                                ET_SPINLOCK_SERVICE_CONFIG_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_spinlock_wrap_configure(
                service->spinlock_id, request_body[ET_SPINLOCK_SERVICE_CONFIG_ENABLED_OFFSET],
                request_body[ET_SPINLOCK_SERVICE_CONFIG_MODE_OFFSET]));
        }

        case ET_SPINLOCK_COMMAND_CONFIG_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_CONFIG_SNAPSHOT_SIZE) ||
                (et_spinlock_wrap_config_snapshot_get(service->spinlock_id, &config) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            response_body[ET_SPINLOCK_SERVICE_CONFIG_ENABLED_OFFSET] = config.enabled;
            response_body[ET_SPINLOCK_SERVICE_CONFIG_MODE_OFFSET] = config.mode;
            response_body[ET_SPINLOCK_SERVICE_CONFIG_RESERVED_OFFSET] = 0u;
            response_body[ET_SPINLOCK_SERVICE_CONFIG_RESERVED_OFFSET + 1u] = 0u;
            *response_length = ET_SPINLOCK_SERVICE_CONFIG_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_LOCAL_MASTER_ID_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_MASTER_ID_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_spinlock_wrap_local_master_id_get(service->spinlock_id, &master_id);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u16(response_body, master_id);
            *response_length = ET_SPINLOCK_SERVICE_MASTER_ID_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_RESOURCE_ACQUIRE_TRY:
        case ET_SPINLOCK_COMMAND_RESOURCE_RELEASE:
        {
            if (request_length != ET_SPINLOCK_SERVICE_RESOURCE_REQUEST_SIZE)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            resource_id = read_u16(&request_body[ET_SPINLOCK_SERVICE_RESOURCE_ID_OFFSET]);
            process_id = read_u16(&request_body[ET_SPINLOCK_SERVICE_PROCESS_ID_OFFSET]);
            wrap_status = (command_id == ET_SPINLOCK_COMMAND_RESOURCE_ACQUIRE_TRY)
                              ? et_spinlock_wrap_resource_acquire_try(service->spinlock_id,
                                                                      resource_id, process_id)
                              : et_spinlock_wrap_resource_release(service->spinlock_id, resource_id,
                                                                  process_id);

            return status_from_wrap(wrap_status);
        }

        case ET_SPINLOCK_COMMAND_FLAG_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_FLAG_SNAPSHOT_SIZE) ||
                (et_spinlock_wrap_flag_snapshot_get(service->spinlock_id, &flags) !=
                 ET_WRAP_STATUS_OK))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            write_u32(&response_body[ET_SPINLOCK_SERVICE_FLAGS_LOW_OFFSET], flags.flags_low);
            write_u32(&response_body[ET_SPINLOCK_SERVICE_FLAGS_HIGH_OFFSET], flags.flags_high);
            *response_length = ET_SPINLOCK_SERVICE_FLAG_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_RESOURCE_SNAPSHOT_GET:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_RESOURCE_ID_SIZE) ||
                (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_RESOURCE_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            resource_id = read_u16(request_body);
            wrap_status = et_spinlock_wrap_resource_snapshot_get(service->spinlock_id, resource_id,
                                                                 &resource);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_LOCKED_OFFSET] = resource.locked;
            response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_OWNER_VALID_OFFSET] = resource.owner_valid;
            response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_PROCESS_VALID_OFFSET] =
                resource.process_id_valid;
            response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_RESERVED_OFFSET] = 0u;
            write_u16(&response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_MASTER_ID_OFFSET],
                      resource.master_id);
            write_u16(&response_body[ET_SPINLOCK_SERVICE_SNAPSHOT_PROCESS_ID_OFFSET],
                      resource.process_id);
            *response_length = ET_SPINLOCK_SERVICE_RESOURCE_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_BATCH_RELEASE:
        case ET_SPINLOCK_COMMAND_GLOBAL_RELEASE:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = (command_id == ET_SPINLOCK_COMMAND_BATCH_RELEASE)
                              ? et_spinlock_wrap_batch_release(service->spinlock_id)
                              : et_spinlock_wrap_global_release(service->spinlock_id);

            return status_from_wrap(wrap_status);
        }

        case ET_SPINLOCK_COMMAND_CLEAR_KEY_PROBE:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_CLEAR_PROBE_SIZE) ||
                (bytes_are_zero(&request_body[ET_SPINLOCK_SERVICE_CLEAR_RESERVED_OFFSET],
                                ET_SPINLOCK_SERVICE_CLEAR_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_spinlock_wrap_clear_key_probe(
                service->spinlock_id, request_body[ET_SPINLOCK_SERVICE_CLEAR_SCOPE_OFFSET],
                request_body[ET_SPINLOCK_SERVICE_CLEAR_AUTHORIZED_OFFSET]));
        }

        case ET_SPINLOCK_COMMAND_PEER_STATUS_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_PEER_STATUS_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_spinlock_wrap_peer_ready_get(service->spinlock_id, &peer_ready);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            master_id = 0u;

            if (peer_ready != 0u)
            {
                wrap_status = et_spinlock_wrap_peer_master_id_get(service->spinlock_id, &master_id);

                if (wrap_status != ET_WRAP_STATUS_OK)
                {
                    return status_from_wrap(wrap_status);
                }
            }

            response_body[ET_SPINLOCK_SERVICE_PEER_READY_OFFSET] = peer_ready;
            response_body[ET_SPINLOCK_SERVICE_PEER_STATUS_RESERVED_OFFSET] = 0u;
            write_u16(&response_body[ET_SPINLOCK_SERVICE_PEER_MASTER_ID_OFFSET], master_id);
            *response_length = ET_SPINLOCK_SERVICE_PEER_STATUS_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_PEER_JOB_START:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_PEER_JOB_CONFIG_SIZE) ||
                (bytes_are_zero(&request_body[ET_SPINLOCK_SERVICE_PEER_JOB_RESERVED_OFFSET],
                                ET_SPINLOCK_SERVICE_PEER_JOB_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            peer_job_config.job_type = request_body[ET_SPINLOCK_SERVICE_PEER_JOB_TYPE_OFFSET];
            peer_job_config.mode = request_body[ET_SPINLOCK_SERVICE_PEER_JOB_MODE_OFFSET];
            peer_job_config.resource_id =
                read_u16(&request_body[ET_SPINLOCK_SERVICE_PEER_JOB_RESOURCE_OFFSET]);
            peer_job_config.process_id =
                read_u16(&request_body[ET_SPINLOCK_SERVICE_PEER_JOB_PROCESS_OFFSET]);
            peer_job_config.reserved = 0u;
            peer_job_config.loop_count =
                read_u32(&request_body[ET_SPINLOCK_SERVICE_PEER_JOB_LOOP_COUNT_OFFSET]);

            return status_from_wrap(
                et_spinlock_wrap_peer_job_start(service->spinlock_id, &peer_job_config));
        }

        case ET_SPINLOCK_COMMAND_PEER_JOB_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_PEER_JOB_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status =
                et_spinlock_wrap_peer_job_snapshot_get(service->spinlock_id, &peer_job_snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            response_body[ET_SPINLOCK_SERVICE_PEER_SNAPSHOT_STATE_OFFSET] = peer_job_snapshot.state;
            response_body[ET_SPINLOCK_SERVICE_PEER_SNAPSHOT_RESULT_OFFSET] =
                peer_job_snapshot.result;
            write_u16(&response_body[ET_SPINLOCK_SERVICE_PEER_SNAPSHOT_MASTER_OFFSET],
                      peer_job_snapshot.master_id);
            write_u32(&response_body[ET_SPINLOCK_SERVICE_PEER_SNAPSHOT_ENTER_COUNT_OFFSET],
                      peer_job_snapshot.enter_count);
            write_u32(&response_body[ET_SPINLOCK_SERVICE_PEER_SNAPSHOT_COMPLETED_COUNT_OFFSET],
                      peer_job_snapshot.completed_count);
            *response_length = ET_SPINLOCK_SERVICE_PEER_JOB_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_PEER_JOB_CONTROL:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_PEER_CONTROL_SIZE) ||
                (bytes_are_zero(&request_body[ET_SPINLOCK_SERVICE_PEER_CONTROL_RESERVED_OFFSET],
                                ET_SPINLOCK_SERVICE_PEER_CONTROL_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_spinlock_wrap_peer_job_control(
                service->spinlock_id, request_body[ET_SPINLOCK_SERVICE_PEER_CONTROL_OFFSET]));
        }

        case ET_SPINLOCK_COMMAND_SHARED_STRESS_RESET:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            return status_from_wrap(et_spinlock_wrap_shared_stress_reset(service->spinlock_id));
        }

        case ET_SPINLOCK_COMMAND_LOCAL_STRESS_RUN:
        {
            if ((request_length != ET_SPINLOCK_SERVICE_LOCAL_STRESS_REQUEST_SIZE) ||
                (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_LOCAL_STRESS_RESPONSE_SIZE) ||
                (bytes_are_zero(&request_body[ET_SPINLOCK_SERVICE_STRESS_RESERVED_OFFSET],
                                ET_SPINLOCK_SERVICE_STRESS_RESERVED_SIZE) == 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            resource_id = read_u16(&request_body[ET_SPINLOCK_SERVICE_STRESS_RESOURCE_OFFSET]);
            loop_count = read_u32(&request_body[ET_SPINLOCK_SERVICE_STRESS_LOOP_COUNT_OFFSET]);
            wrap_status = et_spinlock_wrap_local_stress_run(service->spinlock_id, resource_id,
                                                            loop_count, &completed_count);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_SPINLOCK_SERVICE_STRESS_COMPLETED_COUNT_OFFSET],
                      completed_count);
            *response_length = ET_SPINLOCK_SERVICE_LOCAL_STRESS_RESPONSE_SIZE;

            return ET_STATUS_OK;
        }

        case ET_SPINLOCK_COMMAND_SHARED_SNAPSHOT_GET:
        {
            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_SPINLOCK_SERVICE_SHARED_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status =
                et_spinlock_wrap_shared_snapshot_get(service->spinlock_id, &shared_snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_SPINLOCK_SERVICE_SHARED_COUNTER_OFFSET],
                      shared_snapshot.shared_counter);
            write_u32(&response_body[ET_SPINLOCK_SERVICE_SHARED_VIOLATION_COUNT_OFFSET],
                      shared_snapshot.violation_count);
            *response_length = ET_SPINLOCK_SERVICE_SHARED_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one SPINLOCK Service without touching SPINLOCK hardware.
 * @param[out] service Application-owned Service storage.
 * @param[in] spinlock_id Stable logical SPINLOCK instance identifier.
 * @param[in,out] irq_manager Common IRQ Manager required by the Service factory contract.
 * @param[in] irq_priority Board-selected IRQ priority; SPINLOCK has no IRQ and does not use it.
 * @note Initialization creates only bounded software state and a descriptor.
 * @return Zero on success, otherwise minus one.
 */
int et_spinlock_service_init(et_spinlock_service_t *service, et_spinlock_id_t spinlock_id,
                             et_irq_manager_t *irq_manager, uint8_t irq_priority)
{
    if ((service == NULL) || (irq_manager == NULL))
    {
        return -1;
    }

    (void)irq_priority;
    (void)memset(service, 0, sizeof(*service));
    service->spinlock_id = spinlock_id;
    service->descriptor.service_id = ET_SPINLOCK_SERVICE_ID;
    service->descriptor.instance_id = spinlock_id;
    service->descriptor.context = service;
    service->descriptor.handle = spinlock_handle;
    service->descriptor.poll = NULL;

    return 0;
}

/**
 * @brief Return the immutable descriptor of one initialized SPINLOCK Service.
 * @param[in] service Initialized SPINLOCK Service.
 * @note The descriptor aliases Service-owned storage.
 * @return Descriptor pointer or NULL when service is NULL.
 */
const et_service_descriptor_t *et_spinlock_service_descriptor(const et_spinlock_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/**
 * @brief Create one SPINLOCK Service through the generic factory contract.
 * @param[out] storage Caller-owned Service storage.
 * @param[in] instance_id Stable logical SPINLOCK instance identifier.
 * @param[in] context Common factory dependencies.
 * @param[out] descriptor Initialized descriptor.
 * @note Factory creation does not configure SPINLOCK hardware.
 * @return Zero on success, otherwise minus one.
 */
int et_spinlock_service_create(void *storage, uint16_t instance_id,
                               const et_service_factory_context_t *context,
                               const et_service_descriptor_t **descriptor)
{
    et_spinlock_service_t *service = (et_spinlock_service_t *)storage;

    if ((service == NULL) || (context == NULL) || (context->irq_manager == NULL) ||
        (descriptor == NULL))
    {
        return -1;
    }

    if (et_spinlock_service_init(service, (et_spinlock_id_t)instance_id, context->irq_manager,
                                 context->irq_priority) != 0)
    {
        return -1;
    }

    *descriptor = et_spinlock_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}

/* ET_PLATFORM_SERVICE_FACTORY_END */
