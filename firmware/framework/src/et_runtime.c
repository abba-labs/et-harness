#include "et_runtime.h"

/**
 * @file et_runtime.c
 * @brief Lifecycle wiring for common IRQ, Service and Protocol components.
 */

#include <stddef.h>
#include <string.h>

/**
 * @brief Compose the Runtime-owned IRQ manager, Service router and protocol state.
 *
 * @param[out] runtime Runtime instance to initialize.
 * @param[in] config Session-opening identity and transport IO configuration.
 *
 * @note Initialization activates common IRQ ownership before any Service can bind routes, then
 *       builds the Service router and protocol. Protocol initialization failure rolls the earlier
 *       IRQ activation back as one startup transaction. No protocol polling is started here.
 *
 * @return 0 when every Runtime component is initialized coherently.
 * @return -1 when required pointers are invalid or a component cannot be initialized.
 */
int et_runtime_init(et_runtime_t *runtime, const et_runtime_config_t *config)
{
    et_protocol_config_t protocol_config;

    /* Phase 1: Reset Runtime state and establish common IRQ ownership first. */
    if ((runtime == NULL) || (config == NULL))
    {
        return -1;
    }

    (void)memset(runtime, 0, sizeof(*runtime));
    et_irq_manager_init(&runtime->irqs);

    /* Activate IRQ ownership before any Service can later bind a route. */
    if (et_irq_manager_activate(&runtime->irqs) != 0)
    {
        return -1;
    }

    /* Phase 2: Build the Service registry before the protocol references it. */
    et_service_router_init(&runtime->services);

    (void)memset(&protocol_config, 0, sizeof(protocol_config));
    protocol_config.session_id = config->session_id;
    protocol_config.session_open_service_id = config->session_open_service_id;
    protocol_config.session_open_command_id = config->session_open_command_id;
    protocol_config.services = &runtime->services;
    protocol_config.io = config->io;

    /* Phase 3: Initialize protocol state and roll back IRQ ownership on failure. */
    if (et_protocol_init(&runtime->protocol, &protocol_config) != 0)
    {
        /* Roll back the earlier manager activation as one startup transaction. */
        (void)et_irq_manager_deactivate(&runtime->irqs);
        (void)memset(runtime, 0, sizeof(*runtime));

        return -1;
    }

    return 0;
}

/**
 * @brief Release Runtime ownership and clear all Runtime-local state.
 *
 * @param[in,out] runtime Runtime instance to deinitialize.
 *
 * @note The Runtime is marked stopped before IRQ ownership is deactivated. State is cleared only
 *       after deactivation succeeds so a failed cleanup is not hidden by zeroed ownership flags.
 *
 * @return 0 when Runtime IRQ ownership is released and local state is cleared.
 * @return -1 when runtime is NULL or IRQ manager deactivation fails.
 */
int et_runtime_deinit(et_runtime_t *runtime)
{
    if (runtime == NULL)
    {
        return -1;
    }

    runtime->started = 0u;

    if (et_irq_manager_deactivate(&runtime->irqs) != 0)
    {
        return -1;
    }

    (void)memset(runtime, 0, sizeof(*runtime));

    return 0;
}

/**
 * @brief Mark a fully configured Runtime ready for cooperative protocol polling.
 *
 * @param[in,out] runtime Runtime whose registered Services are ready to execute.
 *
 * @note This function changes Runtime state only. Transport hardware is opened by the Application
 *       before this call; starting is rejected until at least one Service descriptor is registered.
 *
 * @return 0 when Runtime polling is enabled.
 * @return -1 when runtime is invalid, already started or has no registered Services.
 */
int et_runtime_start(et_runtime_t *runtime)
{
    if ((runtime == NULL) || (runtime->started != 0u) ||
        (et_service_count(&runtime->services) == 0u))
    {
        return -1;
    }

    runtime->started = 1u;

    return 0;
}

/**
 * @brief Advance deferred Service work and protocol processing once.
 *
 * @param[in,out] runtime Started Runtime instance to poll.
 *
 * @note Service polling runs before protocol polling so deferred hardware facts can become visible
 *       before the next request is dispatched. This function is thread-context work, not ISR work.
 *
 * @return Number of protocol input bytes consumed during this poll, or zero when Runtime is idle.
 */
size_t et_runtime_poll(et_runtime_t *runtime)
{
    if ((runtime == NULL) || (runtime->started == 0u))
    {
        return 0u;
    }

    et_service_router_poll(&runtime->services);

    return et_protocol_poll(&runtime->protocol);
}

/**
 * @brief Reset only the Runtime protocol receive parser state.
 *
 * @param[in,out] runtime Runtime whose partial receive state should be discarded.
 *
 * @note Registered Services, IRQ ownership and protocol statistics remain intact. No transport or
 *       peripheral hardware is reset.
 */
void et_runtime_reset_rx(et_runtime_t *runtime)
{
    if (runtime != NULL)
    {
        et_protocol_reset_rx(&runtime->protocol);
    }
}

/**
 * @brief Report whether the Runtime currently owns an incomplete protocol frame.
 *
 * @param[in] runtime Runtime whose receive parser state is queried.
 *
 * @note This is a read-only parser-state query and does not consume input or alter the session.
 *
 * @return Nonzero when a partial frame is buffered, otherwise zero.
 */
int et_runtime_rx_incomplete(const et_runtime_t *runtime)
{
    return (runtime == NULL) ? 0 : et_protocol_rx_incomplete(&runtime->protocol);
}

/**
 * @brief Stop cooperative Runtime polling without destroying initialized components.
 *
 * @param[in,out] runtime Runtime to mark stopped.
 *
 * @note This function changes only the started flag. It does not close Application transport
 *       hardware or deactivate IRQ manager ownership; et_runtime_deinit() performs final cleanup.
 */
void et_runtime_stop(et_runtime_t *runtime)
{
    if (runtime != NULL)
    {
        runtime->started = 0u;
    }
}

/**
 * @brief Return the Runtime-owned Service router for registration or inspection.
 *
 * @param[in,out] runtime Runtime that owns the router.
 *
 * @note The returned pointer aliases Runtime storage and does not transfer ownership.
 *
 * @return Pointer to the Service router, or NULL when runtime is NULL.
 */
et_service_router_t *et_runtime_services(et_runtime_t *runtime)
{
    return (runtime == NULL) ? NULL : &runtime->services;
}

/**
 * @brief Return the Runtime-owned IRQ manager for Service route binding.
 *
 * @param[in,out] runtime Runtime that owns the IRQ manager.
 *
 * @note The returned pointer aliases Runtime storage and must not outlive the Runtime instance.
 *
 * @return Pointer to the IRQ manager, or NULL when runtime is NULL.
 */
et_irq_manager_t *et_runtime_irqs(et_runtime_t *runtime)
{
    return (runtime == NULL) ? NULL : &runtime->irqs;
}

/**
 * @brief Return immutable protocol counters owned by the Runtime.
 *
 * @param[in] runtime Runtime whose protocol statistics are requested.
 *
 * @note The returned pointer aliases protocol-owned state and no hardware or parser state is changed.
 *
 * @return Pointer to protocol statistics, or NULL when runtime is NULL.
 */
const et_protocol_stats_t *et_runtime_protocol_stats(const et_runtime_t *runtime)
{
    return (runtime == NULL) ? NULL : et_protocol_stats(&runtime->protocol);
}
