#include "et_services.h"

/**
 * @file et_services.c
 * @brief Transactional startup registration for all compiled Services.
 */

#include <stddef.h>
#include <stdint.h>

/**
 * @brief Validate one manifest Service group before any storage address is calculated.
 *
 * @param[in] group Static Service-group declaration to validate.
 *
 * @note The overflow check ensures storage_count * storage_stride can be addressed safely before the
 *       common registrar performs byte-pointer arithmetic. No Service factory or hardware is called.
 *
 * @return Nonzero when the complete group storage/factory contract is valid, otherwise zero.
 */
static int service_group_is_valid(const et_service_group_t *group)
{
    if ((group == NULL) || (group->instance_ids == NULL) || (group->instance_count == 0u) ||
        (group->storage == NULL) || (group->storage_count < group->instance_count) ||
        (group->storage_stride == 0u) || (group->create == NULL))
    {
        return 0;
    }

    if (group->storage_stride > (SIZE_MAX / group->storage_count))
    {
        return 0;
    }

    return 1;
}

/**
 * @brief Create and register every logical instance declared by one IP-owned Service group.
 *
 * @param[in] group Valid static Service-group declaration.
 * @param[in,out] irq_manager Common IRQ manager passed to each IP factory.
 * @param[in,out] router Service router that receives each initialized descriptor.
 * @param[in,out] registered_count Counter incremented after each successful registration.
 *
 * @note Each IP factory initializes caller-owned static storage only. The common registrar knows no
 *       IP-specific state layout beyond storage_stride and stops at the first failed factory/register.
 *
 * @return 0 when every instance in the group is initialized and registered.
 * @return -1 when group/dependencies are invalid or any factory/registration operation fails.
 */
static int register_service_group(const et_service_group_t *group, et_irq_manager_t *irq_manager,
                                  et_service_router_t *router, size_t *registered_count)
{
    et_service_factory_context_t context;
    const et_service_descriptor_t *descriptor;
    uint8_t *storage;
    size_t index;

    if ((service_group_is_valid(group) == 0) || (irq_manager == NULL) || (router == NULL) ||
        (registered_count == NULL))
    {
        return -1;
    }

    context.irq_manager = irq_manager;
    context.irq_priority = group->irq_priority;
    storage = (uint8_t *)group->storage;

    for (index = 0u; index < group->instance_count; ++index)
    {
        descriptor = NULL;

        if ((group->create(&storage[index * group->storage_stride], group->instance_ids[index],
                           &context, &descriptor) != 0) ||
            (descriptor == NULL) || (et_service_register(router, descriptor) != 0))
        {
            return -1;
        }

        ++(*registered_count);
    }

    return 0;
}

/**
 * @brief Transactionally initialize and register every Framework and manifest-declared Service.
 *
 * @param[out] services Aggregate storage for mandatory Framework Services and visible IP count.
 * @param[in] config Framework configuration, IRQ manager and Application Service-group manifest.
 * @param[in,out] router Common Service router receiving all descriptors.
 * @param[in] protocol_stats Protocol statistics exposed by the Framework Service.
 *
 * @note A router-count checkpoint is captured before any registration. Any failure truncates the
 *       router back to that checkpoint so partial startup cannot expose a mixed Service registry.
 *
 * @return 0 when mandatory Services and every manifest group are registered successfully.
 * @return -1 when configuration/registration fails; router visibility is rolled back atomically.
 */
int et_services_register_all(et_services_t *services, const et_services_config_t *config,
                             et_service_router_t *router, const et_protocol_stats_t *protocol_stats)
{
    uint16_t checkpoint;
    size_t group_index;

    /* Phase 1: Validate dependencies and capture the pre-registration router checkpoint. */
    if ((services == NULL) || (config == NULL) || (router == NULL) || (protocol_stats == NULL) ||
        (config->irq_manager == NULL) || ((config->group_count != 0u) && (config->groups == NULL)))
    {
        return -1;
    }

    checkpoint = et_service_count(router);
    services->ip_service_count = 0u;

    /* Phase 2: Register mandatory common Services before optional IP groups. */
    if ((et_framework_service_init(&services->framework, &config->framework, router,
                                   protocol_stats) != 0) ||
        (et_service_register(router, et_framework_service_descriptor(&services->framework)) != 0) ||
        (et_resource_service_init(&services->resource) != 0) ||
        (et_service_register(router, et_resource_service_descriptor(&services->resource)) != 0) ||
        (et_crg_service_init(&services->crg) != 0) ||
        (et_service_register(router, et_crg_service_descriptor(&services->crg)) != 0) ||
        (et_sysctrl_service_init(&services->sysctrl) != 0) ||
        (et_service_register(router, et_sysctrl_service_descriptor(&services->sysctrl)) != 0))
    {
        goto rollback;
    }

    /* Phase 3: Register Application-declared repeated IP groups through the common factory path. */
    for (group_index = 0u; group_index < config->group_count; ++group_index)
    {
        if (register_service_group(&config->groups[group_index], config->irq_manager, router,
                                   &services->ip_service_count) != 0)
        {
            goto rollback;
        }
    }

    return 0;

rollback:
    /* Phase 4: Remove every descriptor published after the startup checkpoint. */
    services->ip_service_count = 0u;
    (void)et_service_router_truncate(router, checkpoint);

    return -1;
}
