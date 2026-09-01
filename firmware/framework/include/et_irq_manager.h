#ifndef ET_IRQ_MANAGER_H
#define ET_IRQ_MANAGER_H

/**
 * @file et_irq_manager.h
 * @brief Common ownership and dispatch layer for dynamically bound IRQ routes.
 *
 * IP Services bind logical callbacks through this manager. Only IRQ Wrap owns
 * vector-table, NVIC priority, pending and enable operations.
 */

#include <stdint.h>

#include "et_irq_types.h"
#include "et_test_protocol_config.h"

#define ET_IRQ_CLEANUP_DISABLED (1u << 0)
#define ET_IRQ_CLEANUP_PENDING_CLEARED (1u << 1)
#define ET_IRQ_CLEANUP_UNREGISTERED (1u << 2)
#define ET_IRQ_CLEANUP_COMPLETE                                                                    \
    (ET_IRQ_CLEANUP_DISABLED | ET_IRQ_CLEANUP_PENDING_CLEARED | ET_IRQ_CLEANUP_UNREGISTERED)

typedef void (*et_irq_callback_t)(void *context, et_irq_line_t irq_line, uint32_t route_events);

/** One active IRQ route and the cleanup state required for safe unbinding. */
typedef struct
{
    et_irq_line_t irq_line;     /**< Physical vector line hidden from PC. */
    et_irq_callback_t callback; /**< Service-owned callback. */
    void *context;              /**< Callback context owned by Service. */
    uint32_t route_events;      /**< IP-local events routed by this line. */
    uint8_t priority;           /**< Board-selected NVIC priority. */
    uint8_t in_use;             /**< Binding slot contains a live route. */
    uint8_t cleanup_progress;   /**< Completed ET_IRQ_CLEANUP_* steps. */
    uint8_t cleanup_required;   /**< Cleanup is pending after a partial fault. */
} et_irq_binding_t;

typedef struct
{
    et_irq_binding_t bindings[ET_FRAMEWORK_MAX_IRQ_BINDINGS];
    uint32_t cleanup_fault_count; /**< Saturating teardown failure counter. */
} et_irq_manager_t;

/** Initialize empty binding storage without enabling hardware interrupts. */
void et_irq_manager_init(et_irq_manager_t *manager);
/** Activate the single manager used by the common IRQ trampoline. */
int et_irq_manager_activate(et_irq_manager_t *manager);
/** Deactivate the manager after all bindings have been released. */
int et_irq_manager_deactivate(et_irq_manager_t *manager);
/** Enter a short manager critical section and return the previous PRIMASK. */
uint32_t et_irq_manager_enter_critical(void);
/** Restore the PRIMASK returned by et_irq_manager_enter_critical(). */
void et_irq_manager_exit_critical(uint32_t key);
/** Return the number of incomplete IRQ cleanup operations. */
uint32_t et_irq_manager_cleanup_fault_count(const et_irq_manager_t *manager);
/** Bind, prioritize, clear and enable one physical IRQ route atomically. */
int et_irq_manager_bind(et_irq_manager_t *manager, const et_irq_route_t *route, uint8_t priority,
                        et_irq_callback_t callback, void *context);
/** Disable, clear and unregister one route owned by callback and context. */
int et_irq_manager_unbind(et_irq_manager_t *manager, et_irq_line_t irq_line,
                          et_irq_callback_t callback, void *context);
/** Dispatch one active vector line to its registered Service callback. */
int et_irq_manager_dispatch(et_irq_manager_t *manager, et_irq_line_t irq_line);

#endif
