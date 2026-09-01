#ifndef ET_SERVICES_H
#define ET_SERVICES_H

/**
 * @file et_services.h
 * @brief Startup-only registration of common and board-selected IP Services.
 */

#include <stddef.h>
#include <stdint.h>

#include "et_crg_service.h"
#include "et_framework_service.h"
#include "et_resource_service.h"
#include "et_service_factory.h"
#include "et_sysctrl_service.h"

typedef struct
{
    et_framework_service_config_t framework; /**< Firmware identity facts. */
    et_irq_manager_t *irq_manager;           /**< Shared runtime IRQ manager. */
    const et_service_group_t *groups;        /**< Board-selected repeated IP groups. */
    size_t group_count;                      /**< Number of entries in groups. */
} et_services_config_t;

typedef struct
{
    et_framework_service_t framework;
    et_resource_service_t resource;
    et_crg_service_t crg;
    et_sysctrl_service_t sysctrl;
    size_t ip_service_count; /**< Successfully registered repeated IP Services. */
} et_services_t;

/**
 * Register all configured Services as one transaction. On any failure the
 * router and visible instance counts are restored to their entry checkpoint.
 */
int et_services_register_all(et_services_t *services, const et_services_config_t *config,
                             et_service_router_t *router,
                             const et_protocol_stats_t *protocol_stats);

#endif
