#include "et_irq_manager.h"

/**
 * @file et_irq_manager.c
 * @brief Retry-safe IRQ ownership, teardown and common-vector dispatch.
 */

#include <stddef.h>
#include <string.h>

#include "et_irq_wrap.h"

static et_irq_manager_t *active_manager;

/**
 * @brief Record one IRQ cleanup failure using a saturating manager-owned counter.
 *
 * @param[in,out] manager IRQ manager whose cleanup evidence is updated.
 *
 * @note The counter saturates at UINT32_MAX so repeated cleanup faults never wrap and masquerade as
 *       a smaller failure count. This helper does not touch interrupt hardware.
 */
static void note_cleanup_fault(et_irq_manager_t *manager)
{
    if ((manager != NULL) && (manager->cleanup_fault_count != UINT32_MAX))
    {
        ++manager->cleanup_fault_count;
    }
}

/**
 * @brief Complete retry-safe physical teardown for one manager-owned IRQ line.
 *
 * @param[in,out] manager IRQ manager that owns cleanup evidence.
 * @param[in,out] owner Binding that represents the physical line owner being cleaned.
 *
 * @note Teardown order is disable -> clear pending -> unregister. Each completed hardware step is
 *       persisted in cleanup_progress so a later retry resumes at the first unfinished operation.
 *
 * @return 0 only when every physical cleanup step is complete.
 * @return -1 for invalid ownership or when a hardware cleanup step fails.
 */
static int cleanup_irq_line(et_irq_manager_t *manager, et_irq_binding_t *owner)
{
    if ((manager == NULL) || (owner == NULL) || (owner->in_use == 0u))
    {
        return -1;
    }

    /* Each successful step is retained so a retry cannot redo unsafe work. */
    owner->cleanup_required = 1u;

    if ((owner->cleanup_progress & ET_IRQ_CLEANUP_DISABLED) == 0u)
    {
        if (et_irq_wrap_disable(owner->irq_line) != ET_WRAP_STATUS_OK)
        {
            note_cleanup_fault(manager);

            return -1;
        }

        owner->cleanup_progress |= ET_IRQ_CLEANUP_DISABLED;
    }

    if ((owner->cleanup_progress & ET_IRQ_CLEANUP_PENDING_CLEARED) == 0u)
    {
        if (et_irq_wrap_clear_pending(owner->irq_line) != ET_WRAP_STATUS_OK)
        {
            note_cleanup_fault(manager);

            return -1;
        }

        owner->cleanup_progress |= ET_IRQ_CLEANUP_PENDING_CLEARED;
    }

    if ((owner->cleanup_progress & ET_IRQ_CLEANUP_UNREGISTERED) == 0u)
    {
        if (et_irq_wrap_unregister(owner->irq_line) != ET_WRAP_STATUS_OK)
        {
            note_cleanup_fault(manager);

            return -1;
        }

        owner->cleanup_progress |= ET_IRQ_CLEANUP_UNREGISTERED;
    }

    return (owner->cleanup_progress == ET_IRQ_CLEANUP_COMPLETE) ? 0 : -1;
}

/**
 * @brief Dispatch the currently active physical IRQ through the published common manager.
 *
 * @note This callback executes from the chip vector path. It only resolves the active physical line
 *       through IRQ Wrap and forwards it to manager dispatch; Service callbacks remain bounded by R320.
 */
static void et_irq_common_entry(void)
{
    et_irq_line_t irq_line;

    /* Chip vector table enters here; Manager resolves the Service callback. */
    if ((active_manager != NULL) && (et_irq_wrap_get_active_line(&irq_line) == ET_WRAP_STATUS_OK))
    {
        (void)et_irq_manager_dispatch(active_manager, irq_line);
    }
}

/**
 * @brief Reset one IRQ manager's software-owned binding and fault state.
 *
 * @param[out] manager IRQ manager to reset.
 *
 * @note This function clears software state only. It does not disable, clear or unregister any
 *       physical interrupt line and therefore must be used before hardware ownership is acquired.
 */
void et_irq_manager_init(et_irq_manager_t *manager)
{
    if (manager != NULL)
    {
        (void)memset(manager, 0, sizeof(*manager));
    }
}

/**
 * @brief Publish one IRQ manager as the process-wide common dispatch owner.
 *
 * @param[in,out] manager IRQ manager to activate.
 *
 * @note Publication is protected by the IRQ Wrap critical section. A second distinct manager is
 *       rejected so chip vector dispatch always has one unambiguous owner.
 *
 * @return 0 when manager becomes or already is the active owner.
 * @return -1 when manager is NULL or another manager is already active.
 */
int et_irq_manager_activate(et_irq_manager_t *manager)
{
    uint32_t key;

    if (manager == NULL)
    {
        return -1;
    }

    key = et_irq_wrap_enter_critical();

    if ((active_manager != NULL) && (active_manager != manager))
    {
        et_irq_wrap_exit_critical(key);

        return -1;
    }

    active_manager = manager;
    et_irq_wrap_exit_critical(key);

    return 0;
}

/**
 * @brief Release all manager bindings and remove the common dispatch owner.
 *
 * @param[in,out] manager Active IRQ manager to deactivate.
 *
 * @note Shared physical lines are cleaned exactly once. If a physical teardown step fails, all
 *       binding state and completed cleanup_progress are retained so a later call can resume safely.
 *
 * @return 0 when every owned physical line is cleaned and manager publication is removed.
 * @return -1 when ownership is invalid or any physical cleanup operation remains incomplete.
 */
int et_irq_manager_deactivate(et_irq_manager_t *manager)
{
    size_t index;
    size_t previous;
    uint32_t key;

    /* Phase 1: Enter the critical section only for the currently published manager. */
    if (manager == NULL)
    {
        return -1;
    }

    key = et_irq_wrap_enter_critical();

    if (active_manager != manager)
    {
        et_irq_wrap_exit_critical(key);

        return -1;
    }

    /* Phase 2: Clean each distinct shared physical line exactly once. */
    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        et_irq_binding_t *binding = &manager->bindings[index];
        uint8_t first_for_line = 1u;

        if (binding->in_use == 0u)
        {
            continue;
        }

        for (previous = 0u; previous < index; ++previous)
        {
            if ((manager->bindings[previous].in_use != 0u) &&
                (manager->bindings[previous].irq_line == binding->irq_line))
            {
                first_for_line = 0u;
                break;
            }
        }

        if (first_for_line == 0u)
        {
            continue;
        }

        if (cleanup_irq_line(manager, binding) != 0)
        {
            /* Keep bindings, active_manager and completed progress so a
             * later deactivation retries only the unfinished hardware step. */
            et_irq_wrap_exit_critical(key);

            return -1;
        }
    }

    /* Phase 3: Clear software ownership only after every physical line teardown succeeds. */
    (void)memset(manager->bindings, 0, sizeof(manager->bindings));
    active_manager = NULL;
    et_irq_wrap_exit_critical(key);

    return 0;
}

/**
 * @brief Enter the platform interrupt critical section.
 *
 * @note The returned key captures the prior platform interrupt state and must be passed unchanged to
 *       et_irq_manager_exit_critical().
 *
 * @return Platform restore key produced by IRQ Wrap.
 */
uint32_t et_irq_manager_enter_critical(void)
{
    return et_irq_wrap_enter_critical();
}

/**
 * @brief Restore the platform interrupt state saved by a prior critical-section entry.
 *
 * @param[in] key Restore key returned by et_irq_manager_enter_critical().
 *
 * @note This function directly restores platform interrupt state through IRQ Wrap and must be paired
 *       with the matching entry call.
 */
void et_irq_manager_exit_critical(uint32_t key)
{
    et_irq_wrap_exit_critical(key);
}

/**
 * @brief Return the manager's accumulated physical IRQ cleanup-failure evidence.
 *
 * @param[in] manager IRQ manager whose cleanup counter is queried.
 *
 * @note This is a read-only software-state query; the counter is saturating and no hardware is read.
 *
 * @return Cleanup-failure count, or zero when manager is NULL.
 */
uint32_t et_irq_manager_cleanup_fault_count(const et_irq_manager_t *manager)
{
    return (manager == NULL) ? 0u : manager->cleanup_fault_count;
}

/**
 * @brief Claim one logical IRQ route and ensure its physical line is safely enabled.
 *
 * @param[in,out] manager Active IRQ manager that owns the binding table.
 * @param[in] route Stable logical-to-physical route and normalized event mask.
 * @param[in] priority Board-selected priority shared by every binding on the physical line.
 * @param[in] callback Service callback invoked when the route's physical line dispatches.
 * @param[in,out] context Caller-owned callback context retained by the binding.
 *
 * @note Bind first reserves software ownership, then configures a previously unused physical line in
 *       disable -> register -> priority -> clear -> enable order. Failure enters retry-safe cleanup.
 *
 * @return 0 when the route is newly bound or an identical binding already exists.
 * @return -1 for invalid ownership, conflicting bindings, full storage or hardware setup failure.
 */
int et_irq_manager_bind(et_irq_manager_t *manager, const et_irq_route_t *route, uint8_t priority,
                        et_irq_callback_t callback, void *context)
{
    size_t index;
    et_irq_binding_t *free_binding = NULL;
    uint8_t line_is_bound = 0u;
    uint32_t key;

    /* Phase 1: Validate manager ownership and inspect existing bindings under one critical section. */
    if ((manager == NULL) || (route == NULL) || (route->route_events == 0u) || (callback == NULL) ||
        (active_manager != manager))
    {
        return -1;
    }

    key = et_irq_wrap_enter_critical();

    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        et_irq_binding_t *binding = &manager->bindings[index];

        if (binding->in_use == 0u)
        {
            if (free_binding == NULL)
            {
                free_binding = binding;
            }

            continue;
        }

        if ((binding->cleanup_progress != 0u) || (binding->cleanup_required != 0u))
        {
            et_irq_wrap_exit_critical(key);

            return -1;
        }

        if ((binding->irq_line == route->irq_line) && (binding->callback == callback) &&
            (binding->context == context))
        {
            int same =
                ((binding->route_events == route->route_events) && (binding->priority == priority));
            et_irq_wrap_exit_critical(key);

            return same ? 0 : -1;
        }

        if (binding->irq_line == route->irq_line)
        {
            if (binding->priority != priority)
            {
                et_irq_wrap_exit_critical(key);

                return -1;
            }

            line_is_bound = 1u;
        }
    }

    if (free_binding == NULL)
    {
        et_irq_wrap_exit_critical(key);

        return -1;
    }

    /* Phase 2: Publish the logical binding before any new physical-line enable operation. */
    free_binding->irq_line = route->irq_line;
    free_binding->callback = callback;
    free_binding->context = context;
    free_binding->route_events = route->route_events;
    free_binding->priority = priority;
    free_binding->in_use = 1u;
    free_binding->cleanup_progress = 0u;
    free_binding->cleanup_required = 0u;

    /* Phase 3: Configure a previously unused physical line and roll back safely on failure. */
    if ((line_is_bound == 0u) &&
        ((et_irq_wrap_disable(route->irq_line) != ET_WRAP_STATUS_OK) ||
         (et_irq_wrap_register(route->irq_line, et_irq_common_entry) != ET_WRAP_STATUS_OK) ||
         (et_irq_wrap_set_priority(route->irq_line, priority) != ET_WRAP_STATUS_OK) ||
         (et_irq_wrap_clear_pending(route->irq_line) != ET_WRAP_STATUS_OK) ||
         (et_irq_wrap_enable(route->irq_line) != ET_WRAP_STATUS_OK)))
    {
        free_binding->cleanup_required = 1u;

        if (cleanup_irq_line(manager, free_binding) == 0)
        {
            (void)memset(free_binding, 0, sizeof(*free_binding));
        }

        et_irq_wrap_exit_critical(key);

        return -1;
    }

    et_irq_wrap_exit_critical(key);

    return 0;
}

/**
 * @brief Release one callback-owned logical route and tear down its physical line when last-used.
 *
 * @param[in,out] manager Active IRQ manager that owns the binding table.
 * @param[in] irq_line Physical line associated with the callback binding.
 * @param[in] callback Callback identity used to find the exact binding.
 * @param[in,out] context Caller-owned callback context used to find the exact binding.
 *
 * @note Shared physical hardware is cleaned only when this is the final binding on the line. Failed
 *       cleanup retains the target binding and progress so callers can retry idempotently.
 *
 * @return 0 when the logical binding is released successfully.
 * @return -1 when ownership/binding is invalid or final physical-line cleanup fails.
 */
int et_irq_manager_unbind(et_irq_manager_t *manager, et_irq_line_t irq_line,
                          et_irq_callback_t callback, void *context)
{
    size_t index;
    et_irq_binding_t *target = NULL;
    uint8_t line_still_bound = 0u;
    uint32_t key;

    /* Phase 1: Locate the exact callback binding and detect other users of the physical line. */
    if ((manager == NULL) || (callback == NULL) || (active_manager != manager))
    {
        return -1;
    }

    key = et_irq_wrap_enter_critical();

    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        et_irq_binding_t *binding = &manager->bindings[index];

        if ((binding->in_use != 0u) && (binding->irq_line == irq_line) &&
            (binding->callback == callback) && (binding->context == context))
        {
            target = binding;
            continue;
        }

        if ((binding->in_use != 0u) && (binding->irq_line == irq_line))
        {
            line_still_bound = 1u;
        }
    }

    if (target == NULL)
    {
        et_irq_wrap_exit_critical(key);

        return -1;
    }

    /* Phase 2: Tear down shared physical hardware only when no other logical binding needs it. */
    if ((line_still_bound == 0u) && (cleanup_irq_line(manager, target) != 0))
    {
        /* Keep the binding and cleanup_progress so an idempotent caller can
         * retry the first unfinished physical teardown step. */
        et_irq_wrap_exit_critical(key);

        return -1;
    }

    /* Phase 3: Remove logical ownership only after required physical cleanup is complete. */
    (void)memset(target, 0, sizeof(*target));
    et_irq_wrap_exit_critical(key);

    return 0;
}

/**
 * @brief Dispatch one physical IRQ line to every active logical binding on that shared line.
 *
 * @param[in,out] manager Active IRQ manager whose callbacks are dispatched.
 * @param[in] irq_line Physical IRQ line reported by the common vector entry.
 *
 * @note This function executes in interrupt context. Bindings undergoing cleanup are skipped so no
 *       callback can observe partially released ownership; each callback receives its route events.
 *
 * @return 0 when at least one active binding was dispatched.
 * @return -1 when manager ownership is invalid or no active binding matches irq_line.
 */
int et_irq_manager_dispatch(et_irq_manager_t *manager, et_irq_line_t irq_line)
{
    size_t index;
    int dispatched = 0;

    if ((manager == NULL) || (active_manager != manager))
    {
        return -1;
    }

    for (index = 0u; index < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++index)
    {
        et_irq_binding_t *binding = &manager->bindings[index];

        if ((binding->in_use != 0u) && (binding->cleanup_progress == 0u) &&
            (binding->cleanup_required == 0u) && (binding->irq_line == irq_line))
        {
            binding->callback(binding->context, irq_line, binding->route_events);
            dispatched = 1;
        }
    }

    return dispatched ? 0 : -1;
}
