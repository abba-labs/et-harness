#ifndef ET_SERVICE_FACTORY_H
#define ET_SERVICE_FACTORY_H

/**
 * @file et_service_factory.h
 * @brief Chip-neutral contract for registering repeated IP Service instances.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_irq_manager.h"
#include "et_service_router.h"

/** Sentinel priority for a Service group that does not own an IRQ route. */
#define ET_SERVICE_IRQ_PRIORITY_UNUSED 0u

/** Dependencies shared by all IP Service factories. */
typedef struct
{
    et_irq_manager_t *irq_manager; /**< Common IRQ ownership and dispatch manager. */
    uint8_t irq_priority;          /**< Board-selected default priority for this group. */
} et_service_factory_context_t;

/**
 * Initialize one IP Service in caller-owned storage and expose its descriptor.
 * The factory must not configure IP hardware or execute test behavior.
 */
typedef int (*et_service_factory_fn)(void *storage, uint16_t instance_id,
                                     const et_service_factory_context_t *context,
                                     const et_service_descriptor_t **descriptor);

/** Static, allocation-free description of one repeated IP Service group. */
typedef struct
{
    const uint16_t *instance_ids; /**< Board-selected logical instance IDs. */
    size_t instance_count;        /**< Number of requested Service instances. */
    void *storage;                /**< Caller-owned contiguous Service storage. */
    size_t storage_count;         /**< Number of elements available in storage. */
    size_t storage_stride;        /**< Size in bytes of one storage element. */
    uint8_t irq_priority;         /**< Board-selected default IRQ priority. */
    et_service_factory_fn create; /**< IP-owned thin factory function. */
} et_service_group_t;

#endif
