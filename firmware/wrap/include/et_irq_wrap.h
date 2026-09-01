#ifndef ET_IRQ_WRAP_H
#define ET_IRQ_WRAP_H

/**
 * @file et_irq_wrap.h
 * @brief Stable bridge for vector registration, NVIC state and PRIMASK.
 *
 * This Wrap contains no IP-specific callbacks. IRQ Manager supplies physical
 * lines and installs its common trampoline through this interface.
 */

#include <stdint.h>

#include "et_irq_types.h"
#include "et_wrap_status.h"

#define ET_IRQ_WRAP_API_VERSION 1u

typedef void (*et_irq_wrap_handler_t)(void);

/** Initialize chip interrupt-controller support. */
et_wrap_status_t et_irq_wrap_init(void);
/** Register one parameterless vector handler for a physical line. */
et_wrap_status_t et_irq_wrap_register(et_irq_line_t irq_line, et_irq_wrap_handler_t handler);
/** Remove the handler registered for a physical line. */
et_wrap_status_t et_irq_wrap_unregister(et_irq_line_t irq_line);
/** Set NVIC priority after validating the physical line. */
et_wrap_status_t et_irq_wrap_set_priority(et_irq_line_t irq_line, uint8_t priority);
/** Clear pending NVIC state for a physical line. */
et_wrap_status_t et_irq_wrap_clear_pending(et_irq_line_t irq_line);
/** Enable one physical NVIC line. */
et_wrap_status_t et_irq_wrap_enable(et_irq_line_t irq_line);
/** Disable one physical NVIC line. */
et_wrap_status_t et_irq_wrap_disable(et_irq_line_t irq_line);
/** Read the currently active physical vector line. */
et_wrap_status_t et_irq_wrap_get_active_line(et_irq_line_t *irq_line);
/** Disable maskable interrupts and return prior PRIMASK. */
uint32_t et_irq_wrap_enter_critical(void);
/** Restore a prior PRIMASK value. */
void et_irq_wrap_exit_critical(uint32_t previous_primask);

#endif
