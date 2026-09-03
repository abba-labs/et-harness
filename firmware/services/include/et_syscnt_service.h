#ifndef ET_SYSCNT_SERVICE_H
#define ET_SYSCNT_SERVICE_H

/** @file et_syscnt_service.h @brief Atomic counter command envelope and descriptor. */
#include "et_service_router.h"
#include "et_syscnt_wrap.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */

/** Public SYSCNT Service identity; command numbers are local to this Service. */
#define ET_SYSCNT_SERVICE_ID 0x010Au

/** Request envelope: instance byte followed by the command's little-endian value. */
#define ET_SYSCNT_REQUEST_ID_OFFSET 0u
#define ET_SYSCNT_REQUEST_VALUE_OFFSET 1u
#define ET_SYSCNT_REQUEST_EMPTY_SIZE 1u
#define ET_SYSCNT_REQUEST_BYTE_SIZE 2u
#define ET_SYSCNT_REQUEST_WORD_SIZE 5u
#define ET_SYSCNT_REQUEST_COUNT_SIZE 9u

/** Response sizes in bytes, from the public SYSCNT Wire contract. */
#define ET_SYSCNT_RESPONSE_EMPTY_SIZE 0u
#define ET_SYSCNT_RESPONSE_WORD_SIZE 4u
#define ET_SYSCNT_RESPONSE_COUNT_SIZE 8u
#define ET_SYSCNT_RESPONSE_CAPABILITIES_SIZE 8u
#define ET_SYSCNT_RESPONSE_CONTROL_SIZE 8u
#define ET_SYSCNT_RESPONSE_SAMPLE_SIZE 24u

/** Capability payload: flags:u32 followed by four width/view bytes. */
#define ET_SYSCNT_CAP_FLAGS_OFFSET 0u
#define ET_SYSCNT_CAP_BITS_OFFSET 4u
#define ET_SYSCNT_CAP_VIEWS_OFFSET 5u
#define ET_SYSCNT_CAP_REFERENCE_BITS_OFFSET 6u
#define ET_SYSCNT_CAP_WORD_BITS_OFFSET 7u

/** Control payload: three Booleans/enums, reserved zero byte, then frequency ID. */
#define ET_SYSCNT_CONTROL_ENABLE_OFFSET 0u
#define ET_SYSCNT_CONTROL_POLICY_OFFSET 1u
#define ET_SYSCNT_CONTROL_HALTED_OFFSET 2u
#define ET_SYSCNT_CONTROL_RESERVED_OFFSET 3u
#define ET_SYSCNT_CONTROL_FREQUENCY_OFFSET 4u

/** Three consecutive u64 raw counts; no converted time or test verdict. */
#define ET_SYSCNT_SAMPLE_BEFORE_OFFSET 0u
#define ET_SYSCNT_SAMPLE_COUNT_OFFSET 8u
#define ET_SYSCNT_SAMPLE_AFTER_OFFSET 16u

typedef enum
{
    ET_SYSCNT_COMMAND_CAPABILITIES_GET = 0u,
    ET_SYSCNT_COMMAND_ENABLE_SET = 1u,
    ET_SYSCNT_COMMAND_VALUE_LOAD = 2u,
    ET_SYSCNT_COMMAND_COUNT_GET = 3u,
    ET_SYSCNT_COMMAND_CONTROL_GET = 4u,
    ET_SYSCNT_COMMAND_HALT_POLICY_SET = 5u,
    ET_SYSCNT_COMMAND_FREQUENCY_ID_SET = 6u,
    ET_SYSCNT_COMMAND_REFERENCE_SAMPLE_GET = 7u,
    ET_SYSCNT_COMMAND_REFERENCE_ENABLE_SET = 8u,
    ET_SYSCNT_COMMAND_COUNT
} et_syscnt_command_t;

typedef struct
{
    et_syscnt_id_t syscnt_id;
    et_service_descriptor_t descriptor;
} et_syscnt_service_t;

int et_syscnt_service_init(et_syscnt_service_t *service, et_syscnt_id_t syscnt_id,
                           et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_syscnt_service_descriptor(const et_syscnt_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_syscnt_service_create(void *storage, uint16_t instance_id,
                             const et_service_factory_context_t *context,
                             const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */

#endif
