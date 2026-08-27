/** @file et_cpu_service.c @brief Decode CPU-owner commands and observe NMI events. */

#include "et_cpu_service.h"

#include <stddef.h>
#include <string.h>

#include "et_message.h"

/* The current test firmware has one active NMI vector owner per image. */
static et_cpu_service_t *active_nmi_service;

/**
 * @brief Write one little-endian 16-bit Wire value.
 * @param[out] data Two writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This helper writes only the fixed CPU Service response representation.
 */
static void write_u16(uint8_t *data, uint16_t value)
{
    data[0] = (uint8_t)(value & ET_CPU_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_CPU_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Write one little-endian 32-bit Wire value.
 * @param[out] data Four writable Wire bytes.
 * @param[in] value Value to encode.
 * @note This helper writes only the fixed CPU Service response representation.
 */
static void write_u32(uint8_t *data, uint32_t value)
{
    data[0] = (uint8_t)(value & ET_CPU_SERVICE_WIRE_BYTE_MASK);
    data[1] = (uint8_t)((value >> 8u) & ET_CPU_SERVICE_WIRE_BYTE_MASK);
    data[2] = (uint8_t)((value >> 16u) & ET_CPU_SERVICE_WIRE_BYTE_MASK);
    data[3] = (uint8_t)((value >> 24u) & ET_CPU_SERVICE_WIRE_BYTE_MASK);
}

/**
 * @brief Convert a CPU Wrap result into the stable ET protocol status namespace.
 *
 * @param[in] status CPU Wrap status returned by a normalized owner action.
 * @note This helper translates status values only and does not access CPU hardware or Service state.
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

        default:
        {
            return ET_STATUS_INTERNAL_ERROR;
        }
    }
}

/**
 * @brief Record one real CPU NMI vector delivery.
 *
 * @note The callback masks every source published by the CPU Driver after the first armed delivery,
 *       then increments bounded software evidence. It never identifies or clears a peer IP source.
 */
void NMI_Handler(void)
{
    if (active_nmi_service == NULL)
    {
        return;
    }

    /*
     * A level source can remain asserted until its owning IP Service runs. Mask all CPU-side
     * routes after the first delivery so NMI re-entry cannot starve the protocol thread.
     */
    if ((active_nmi_service->nmi_armed != 0u) &&
        (et_cpu_wrap_nmi_configure(active_nmi_service->cpu_id,
                                   active_nmi_service->supported_nmi_source_mask) ==
         ET_WRAP_STATUS_OK))
    {
        active_nmi_service->nmi_armed = 0u;
    }

    if (active_nmi_service->nmi_event_count != UINT32_MAX)
    {
        ++active_nmi_service->nmi_event_count;
    }
}

/**
 * @brief Encode one CPU-owner command after fixed payload validation.
 *
 * @param[in,out] context CPU Service retained by the router.
 * @param[in] command_id CPU-owner command identifier.
 * @param[in] request_body Borrowed ET-Frame body.
 * @param[in] request_length Body length.
 * @param[out] response_body Response storage.
 * @param[in] response_capacity Response capacity.
 * @param[out] response_length Produced response length.
 * @note The handler validates one fixed command body and calls only the CPU Wrap; cross-IP order is
 *       owned by the PC Case.
 * @return Stable ET protocol status.
 */
static uint16_t cpu_handle(void *context, uint16_t command_id, const uint8_t *request_body,
                           uint16_t request_length, uint8_t *response_body,
                           uint16_t response_capacity, uint16_t *response_length)
{
    et_cpu_service_t *service = (et_cpu_service_t *)context;

    if ((service == NULL) || (response_length == NULL))
    {
        return ET_STATUS_INVALID_PARAM;
    }

    *response_length = 0u;

    /* Phase 1: validate the common Service context and clear the response length. */

    /* Phase 2: dispatch one CPU-owner command to the matching Wrap operation. */
    switch (command_id)
    {
        case ET_CPU_COMMAND_CAPABILITIES_GET:
        {
            uint32_t source_mask;
            et_wrap_status_t wrap_status;

            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_CPU_SERVICE_CAPABILITIES_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_cpu_wrap_nmi_source_mask_get(service->cpu_id, &source_mask);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u16(&response_body[ET_CPU_SERVICE_CAPS_API_VERSION_OFFSET],
                      ET_CPU_SERVICE_API_VERSION);
            write_u16(&response_body[ET_CPU_SERVICE_CAPS_STRUCT_SIZE_OFFSET],
                      ET_CPU_SERVICE_CAPABILITIES_SIZE);
            write_u32(&response_body[ET_CPU_SERVICE_CAPS_NMI_SOURCE_MASK_OFFSET], source_mask);
            *response_length = ET_CPU_SERVICE_CAPABILITIES_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CPU_COMMAND_NMI_CONFIGURE:
        {
            uint32_t requested_mask;
            uint32_t source_mask;
            et_wrap_status_t wrap_status;

            if ((request_body == NULL) || (request_length != ET_CPU_SERVICE_CONFIG_SIZE) ||
                (request_body[ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_1_OFFSET] != 0u) ||
                (request_body[ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_2_OFFSET] != 0u) ||
                (request_body[ET_CPU_SERVICE_CONFIG_RESERVED_BYTE_3_OFFSET] != 0u))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            requested_mask = request_body[ET_CPU_SERVICE_CONFIG_MASK_OFFSET];
            wrap_status = et_cpu_wrap_nmi_source_mask_get(service->cpu_id, &source_mask);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            if ((requested_mask & ~source_mask) != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            /*
             * Publish the supported-mask and arm state before unmasking hardware. An NMI arriving
             * immediately after the Driver write can therefore quench its own CPU-side route.
             */
            service->supported_nmi_source_mask = source_mask;
            service->nmi_armed = ((requested_mask & source_mask) != source_mask) ? 1u : 0u;
            wrap_status = et_cpu_wrap_nmi_configure(service->cpu_id, requested_mask);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                service->nmi_armed = 0u;
            }

            return status_from_wrap(wrap_status);
        }

        case ET_CPU_COMMAND_NMI_SNAPSHOT_GET:
        {
            et_cpu_wrap_nmi_snapshot_t snapshot;
            et_wrap_status_t wrap_status;

            if ((request_length != 0u) || (response_body == NULL) ||
                (response_capacity < ET_CPU_SERVICE_SNAPSHOT_SIZE))
            {
                return ET_STATUS_INVALID_PARAM;
            }

            wrap_status = et_cpu_wrap_nmi_snapshot_get(service->cpu_id, &snapshot);

            if (wrap_status != ET_WRAP_STATUS_OK)
            {
                return status_from_wrap(wrap_status);
            }

            write_u32(&response_body[ET_CPU_SERVICE_SNAPSHOT_RAW_OFFSET], snapshot.source_raw);
            write_u32(&response_body[ET_CPU_SERVICE_SNAPSHOT_MASKED_OFFSET],
                      snapshot.source_masked);
            write_u32(&response_body[ET_CPU_SERVICE_SNAPSHOT_MASK_OFFSET], snapshot.nmi_mask);
            write_u32(&response_body[ET_CPU_SERVICE_SNAPSHOT_STATUS_OFFSET], snapshot.nmi_status);
            write_u32(&response_body[ET_CPU_SERVICE_SNAPSHOT_EVENT_COUNT_OFFSET],
                      service->nmi_event_count);
            *response_length = ET_CPU_SERVICE_SNAPSHOT_SIZE;

            return ET_STATUS_OK;
        }

        case ET_CPU_COMMAND_NMI_EVENT_CLEAR:
        {
            if (request_length != 0u)
            {
                return ET_STATUS_INVALID_PARAM;
            }

            service->nmi_event_count = 0u;

            return ET_STATUS_OK;
        }

        default:
        {
            return ET_STATUS_INVALID_COMMAND;
        }
    }
}

/**
 * @brief Initialize one CPU-owner Service descriptor and publish its NMI owner.
 *
 * @param[out] service Caller-owned Service storage.
 * @param[in] cpu_id Stable CPU identity.
 * @note This function only initializes the descriptor and publishes the single active NMI owner;
 *       it does not configure CPU hardware until a later command arrives.
 * @return 0 when initialized, otherwise -1.
 */
int et_cpu_service_init(et_cpu_service_t *service, et_cpu_id_t cpu_id)
{
    if (service == NULL)
    {
        return -1;
    }

    (void)memset(service, 0, sizeof(*service));
    service->cpu_id = cpu_id;
    service->descriptor.service_id = ET_CPU_SERVICE_ID;
    service->descriptor.instance_id = cpu_id;
    service->descriptor.context = service;
    service->descriptor.handle = cpu_handle;

    if (active_nmi_service == NULL)
    {
        active_nmi_service = service;
    }

    return 0;
}

/**
 * @brief Return the descriptor registered for one CPU-owner Service.
 *
 * @param[in] service Initialized Service storage.
 * @note The returned pointer aliases Service-owned storage and does not access CPU hardware.
 * @return Descriptor pointer, or NULL when service is NULL.
 */
const et_service_descriptor_t *et_cpu_service_descriptor(const et_cpu_service_t *service)
{
    return (service == NULL) ? NULL : &service->descriptor;
}

/**
 * @brief Create one CPU-owner Service through the Application manifest factory.
 *
 * @param[in,out] storage Caller-owned Service storage.
 * @param[in] instance_id Stable CPU identity.
 * @param[in] context Common factory context, unused by the CPU owner.
 * @param[out] descriptor Published descriptor pointer.
 * @note The factory only initializes Service-owned storage; CPU configuration remains command-driven.
 * @return 0 when creation succeeds, otherwise -1.
 */
int et_cpu_service_create(void *storage, uint16_t instance_id,
                          const et_service_factory_context_t *context,
                          const et_service_descriptor_t **descriptor)
{
    et_cpu_service_t *service = (et_cpu_service_t *)storage;

    (void)context;

    if ((service == NULL) || (descriptor == NULL) ||
        (et_cpu_service_init(service, instance_id) != 0))
    {
        return -1;
    }

    *descriptor = et_cpu_service_descriptor(service);

    return (*descriptor == NULL) ? -1 : 0;
}
