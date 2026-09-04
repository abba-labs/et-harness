#ifndef ET_GPIO_SERVICE_H
#define ET_GPIO_SERVICE_H

/** @file et_gpio_service.h @brief Atomic logical signal mapping commands. */
#include "et_service_router.h"
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
#include "et_service_factory.h"
/* ET_PLATFORM_SERVICE_FACTORY_END */

/** Public GPIO support identity; the service itself has one logical instance. */
#define ET_GPIO_SERVICE_ID 0x0014u
/** Three u16LE fields from gpio.md; lengths and offsets are bytes. */
#define ET_GPIO_SERVICE_REQUEST_SIZE 6u
#define ET_GPIO_SERVICE_PIN_OFFSET 0u
#define ET_GPIO_SERVICE_FUNCTION_OFFSET 2u
#define ET_GPIO_SERVICE_INSTANCE_OFFSET 4u

typedef enum
{
    ET_GPIO_COMMAND_VALIDATE_SIGNAL = 1u,
    ET_GPIO_COMMAND_CONFIGURE_SIGNAL = 2u
} et_gpio_command_t;

typedef struct
{
    et_service_descriptor_t descriptor;
} et_gpio_service_t;

int et_gpio_service_init(et_gpio_service_t *service, uint16_t instance_id,
                         et_irq_manager_t *irq_manager, uint8_t irq_priority);
const et_service_descriptor_t *et_gpio_service_descriptor(const et_gpio_service_t *service);

/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
int et_gpio_service_create(void *storage, uint16_t instance_id,
                           const et_service_factory_context_t *context,
                           const et_service_descriptor_t **descriptor);
/* ET_PLATFORM_SERVICE_FACTORY_END */
#endif
