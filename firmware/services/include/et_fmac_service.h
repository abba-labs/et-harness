#ifndef ET_FMAC_SERVICE_H
#define ET_FMAC_SERVICE_H

/**
 * @file et_fmac_service.h
 * @brief FMAC command contract and bounded per-instance runtime state.
 *
 * FMAC Service decodes atomic requests, calls only FMAC Wrap and records
 * hardware/IRQ facts. Test sequencing and PASS/FAIL remain on the PC.
 */

#include <stdint.h>

#include "et_fmac_wrap.h"
#include "et_irq_manager.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */
#include "et_resource_wrap.h"
#include "et_service_router.h"

#define ET_FMAC_SERVICE_ID 0x0107u
#define ET_FMAC_SERVICE_API_VERSION 1u
#define ET_FMAC_SERVICE_CAPABILITIES_SIZE 20u
#define ET_FMAC_SERVICE_CONFIG_BODY_SIZE 24u
#define ET_FMAC_SERVICE_CONFIG_SNAPSHOT_SIZE 16u
#define ET_FMAC_SERVICE_START_BODY_SIZE 4u
#define ET_FMAC_SERVICE_RESOURCE_BODY_SIZE 12u
#define ET_FMAC_SERVICE_COEFFICIENT_BODY_SIZE 24u
#define ET_FMAC_SERVICE_PROCESS_BODY_SIZE 24u
#define ET_FMAC_SERVICE_COUNT_RESPONSE_SIZE 4u
#define ET_FMAC_SERVICE_PROCESS_RESPONSE_SIZE 8u
#define ET_FMAC_SERVICE_TIMED_PROCESS_RESPONSE_SIZE 12u
#define ET_FMAC_SERVICE_STATUS_RESPONSE_SIZE 12u
#define ET_FMAC_SERVICE_SOURCE_BODY_SIZE 4u
#define ET_FMAC_SERVICE_IRQ_SNAPSHOT_SIZE 24u
#define ET_FMAC_SERVICE_RAW_VALUE_SIZE 4u
#define ET_FMAC_SERVICE_TIMEOUT_BUDGET 1000000u

/* Level request IRQs remain asserted while the related Buffer condition is true. */
#define ET_FMAC_SERVICE_AUTO_MASK_IRQS ET_FMAC_WRAP_IRQ_ALL

/* START request offsets for function and tap-count selection. */
#define ET_FMAC_SERVICE_START_FUNCTION_OFFSET 0u
#define ET_FMAC_SERVICE_START_FEEDFORWARD_OFFSET 1u
#define ET_FMAC_SERVICE_START_FEEDBACK_OFFSET 2u
#define ET_FMAC_SERVICE_START_RESERVED_OFFSET 3u

/* CONFIGURE request offsets. */
#define ET_FMAC_SERVICE_CONFIG_X1_START_OFFSET 0u
#define ET_FMAC_SERVICE_CONFIG_X1_SIZE_OFFSET 1u
#define ET_FMAC_SERVICE_CONFIG_X1_WATERMARK_OFFSET 2u
#define ET_FMAC_SERVICE_CONFIG_X2_START_OFFSET 3u
#define ET_FMAC_SERVICE_CONFIG_X2_SIZE_OFFSET 4u
#define ET_FMAC_SERVICE_CONFIG_Y_START_OFFSET 5u
#define ET_FMAC_SERVICE_CONFIG_Y_SIZE_OFFSET 6u
#define ET_FMAC_SERVICE_CONFIG_Y_WATERMARK_OFFSET 7u
#define ET_FMAC_SERVICE_CONFIG_FINAL_POLICY_OFFSET 8u
#define ET_FMAC_SERVICE_CONFIG_OUTPUT_MODE_OFFSET 9u
#define ET_FMAC_SERVICE_CONFIG_INTERNAL_CLIP_OFFSET 10u
#define ET_FMAC_SERVICE_CONFIG_FLOAT_INPUT_OFFSET 11u
#define ET_FMAC_SERVICE_CONFIG_FLOAT_OUTPUT_OFFSET 12u
#define ET_FMAC_SERVICE_CONFIG_SHIFT_OFFSET 13u
#define ET_FMAC_SERVICE_CONFIG_OUTPUT_OFFSET_OFFSET 14u
#define ET_FMAC_SERVICE_CONFIG_RESERVED_OFFSET 16u
#define ET_FMAC_SERVICE_CONFIG_RESERVED_SIZE 8u

/* Resource action request offsets. */
#define ET_FMAC_SERVICE_RESOURCE_HANDLE_OFFSET 0u
#define ET_FMAC_SERVICE_RESOURCE_OFFSET_OFFSET 4u
#define ET_FMAC_SERVICE_RESOURCE_COUNT_OFFSET 8u
#define ET_FMAC_SERVICE_RESOURCE_FORMAT_OFFSET 10u
#define ET_FMAC_SERVICE_RESOURCE_RESERVED_OFFSET 11u
#define ET_FMAC_SERVICE_DATA_FORMAT_Q15 0u
#define ET_FMAC_SERVICE_DATA_FORMAT_FLOAT32 1u

/* Coefficient-load request offsets for two independent Resource ranges. */
#define ET_FMAC_SERVICE_COEFF_FEEDFORWARD_HANDLE_OFFSET 0u
#define ET_FMAC_SERVICE_COEFF_FEEDFORWARD_OFFSET_OFFSET 4u
#define ET_FMAC_SERVICE_COEFF_FEEDFORWARD_COUNT_OFFSET 8u
#define ET_FMAC_SERVICE_COEFF_FEEDFORWARD_RESERVED_OFFSET 9u
#define ET_FMAC_SERVICE_COEFF_RESERVED_SIZE 3u
#define ET_FMAC_SERVICE_COEFF_FEEDBACK_HANDLE_OFFSET 12u
#define ET_FMAC_SERVICE_COEFF_FEEDBACK_OFFSET_OFFSET 16u
#define ET_FMAC_SERVICE_COEFF_FEEDBACK_COUNT_OFFSET 20u
#define ET_FMAC_SERVICE_COEFF_FEEDBACK_RESERVED_OFFSET 21u

/* One-shot process request offsets. */
#define ET_FMAC_SERVICE_PROCESS_FUNCTION_OFFSET 0u
#define ET_FMAC_SERVICE_PROCESS_FEEDFORWARD_OFFSET 1u
#define ET_FMAC_SERVICE_PROCESS_FEEDBACK_OFFSET 2u
#define ET_FMAC_SERVICE_PROCESS_FORMAT_OFFSET 3u
#define ET_FMAC_SERVICE_PROCESS_SOURCE_HANDLE_OFFSET 4u
#define ET_FMAC_SERVICE_PROCESS_SOURCE_OFFSET_OFFSET 8u
#define ET_FMAC_SERVICE_PROCESS_DESTINATION_HANDLE_OFFSET 12u
#define ET_FMAC_SERVICE_PROCESS_DESTINATION_OFFSET_OFFSET 16u
#define ET_FMAC_SERVICE_PROCESS_COUNT_OFFSET 20u
#define ET_FMAC_SERVICE_PROCESS_RESERVED_OFFSET 22u
#define ET_FMAC_SERVICE_PROCESS_RESERVED_SIZE 2u

/* PROCESS response offsets for observed input/output item counts. */
#define ET_FMAC_SERVICE_PROCESS_INPUT_COUNT_OFFSET 0u
#define ET_FMAC_SERVICE_PROCESS_OUTPUT_COUNT_OFFSET 4u

/* PROCESS_TIMED response offsets for counts and target-local DWT cycles. */
#define ET_FMAC_SERVICE_TIMED_INPUT_COUNT_OFFSET 0u
#define ET_FMAC_SERVICE_TIMED_OUTPUT_COUNT_OFFSET 4u
#define ET_FMAC_SERVICE_TIMED_CYCLES_OFFSET 8u

/* IRQ snapshot response offsets for hardware and Service-owned evidence. */
#define ET_FMAC_SERVICE_IRQ_RAW_OFFSET 0u
#define ET_FMAC_SERVICE_IRQ_STATUS_OFFSET 4u
#define ET_FMAC_SERVICE_IRQ_LATCHED_OFFSET 8u
#define ET_FMAC_SERVICE_IRQ_EVENT_COUNT_OFFSET 12u
#define ET_FMAC_SERVICE_IRQ_ENABLED_OFFSET 16u
#define ET_FMAC_SERVICE_IRQ_MASKED_OFFSET 20u

/** Stable FMAC commands; existing numeric values are Wire-stable. */
typedef enum
{
    ET_FMAC_COMMAND_CAPABILITIES_GET = 0x0001u,
    ET_FMAC_COMMAND_CONFIGURE = 0x0002u,
    ET_FMAC_COMMAND_CONFIG_SNAPSHOT_GET = 0x0003u,
    ET_FMAC_COMMAND_START = 0x0004u,
    ET_FMAC_COMMAND_STOP = 0x0005u,
    ET_FMAC_COMMAND_CLEAR = 0x0006u,
    ET_FMAC_COMMAND_X1_PRELOAD = 0x0007u,
    ET_FMAC_COMMAND_COEFFICIENTS_LOAD = 0x0008u,
    ET_FMAC_COMMAND_Y_PRELOAD = 0x0009u,
    ET_FMAC_COMMAND_STREAM_WRITE = 0x000au,
    ET_FMAC_COMMAND_STREAM_READ = 0x000bu,
    ET_FMAC_COMMAND_DATA_WRITE_ONE_UNCHECKED = 0x000cu,
    ET_FMAC_COMMAND_DATA_READ_ONE_UNCHECKED = 0x000du,
    ET_FMAC_COMMAND_PROCESS = 0x000eu,
    ET_FMAC_COMMAND_STATUS_GET = 0x000fu,
    ET_FMAC_COMMAND_IRQ_ENABLE = 0x0010u,
    ET_FMAC_COMMAND_IRQ_DISABLE = 0x0011u,
    ET_FMAC_COMMAND_IRQ_MASK = 0x0012u,
    ET_FMAC_COMMAND_IRQ_UNMASK = 0x0013u,
    ET_FMAC_COMMAND_IRQ_FORCE = 0x0014u,
    ET_FMAC_COMMAND_IRQ_CLEAR = 0x0015u,
    ET_FMAC_COMMAND_IRQ_SNAPSHOT_GET = 0x0016u,
    ET_FMAC_COMMAND_DMA_REQUEST_SET = 0x0017u,
    ET_FMAC_COMMAND_PROCESS_TIMED = 0x0018u,
    ET_FMAC_COMMAND_START_UNCHECKED = 0x0019u,
    ET_FMAC_COMMAND_STATE_RESET = 0x001au
} et_fmac_command_t;

/** Runtime state retained by one FMAC Service instance. */
typedef struct
{
    et_fmac_id_t fmac_id;
    uint8_t configured;
    uint8_t irq_bound;
    uint8_t irq_priority;
    uint32_t irq_enabled_sources;
    uint32_t irq_masked_sources;
    volatile uint32_t irq_captured_raw;
    volatile uint32_t irq_captured_status;
    volatile uint32_t irq_latched_sources;
    volatile uint32_t irq_event_count;
    et_fmac_wrap_capabilities_t capabilities;
    et_irq_manager_t *irq_manager;
    et_irq_route_t irq_route;
    et_service_descriptor_t descriptor;
} et_fmac_service_t;

int et_fmac_service_init(et_fmac_service_t *service, et_fmac_id_t fmac_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_fmac_service_descriptor(const et_fmac_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
/** Create one FMAC Service through the common static Service factory. */
int et_fmac_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
