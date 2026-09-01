#include "et_irq_wrap.h"

/**
 * @file et_irq_wrap.c
 * @brief Selected-chip vector-table and NVIC adaptation for the common IRQ Manager.
 */

#include "et6x_interrupt.h"

/* ARM exception numbers 0..15 precede external NVIC IRQ lines. */
#define ET_IRQ_EXCEPTION_OFFSET 16u
#define ET_IRQ_LINE_COUNT ((uint32_t)INTERRUPT_MAX_IRQN - ET_IRQ_EXCEPTION_OFFSET)

static uint8_t irq_wrap_initialized;

/**
 * @brief Validate one stable external IRQ line against the selected NVIC range.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 *
 * @note ARM exception numbers are excluded by construction; this helper performs no vector-table or
 *       NVIC hardware operation.
 *
 * @return ET_WRAP_STATUS_OK when irq_line is a valid external line.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is outside the selected-chip range.
 */
static et_wrap_status_t validate_line(et_irq_line_t irq_line)
{
    return ((uint32_t)irq_line < ET_IRQ_LINE_COUNT) ? ET_WRAP_STATUS_OK
                                                    : ET_WRAP_STATUS_INVALID_ARGUMENT;
}

/**
 * @brief Initialize the selected chip vector table exactly once.
 *
 * @note Vector relocation/initialization is protected by a global interrupt critical section so an
 *       interrupt cannot enter while the table is being established. No external line is enabled.
 *
 * @return ET_WRAP_STATUS_OK after initialization or when initialization was already completed.
 */
et_wrap_status_t et_irq_wrap_init(void)
{
    uint32_t previous_primask;

    if (irq_wrap_initialized != 0u)
    {
        return ET_WRAP_STATUS_OK;
    }

    /* Vector relocation/initialization must not race an interrupt entry. */
    previous_primask = et_irq_wrap_enter_critical();
    Interrupt_initVectorTable();
    irq_wrap_initialized = 1u;
    et_irq_wrap_exit_critical(previous_primask);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Register one callback on a validated external IRQ line.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 * @param[in] handler Callback entered by the selected chip interrupt Driver.
 *
 * @note This function modifies vector-table callback ownership only; it does not enable the NVIC
 *       line or configure a Feature IP interrupt source.
 *
 * @return ET_WRAP_STATUS_OK when the callback is registered.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT for an invalid line or NULL handler.
 */
et_wrap_status_t et_irq_wrap_register(et_irq_line_t irq_line, et_irq_wrap_handler_t handler)
{
    if (handler == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    Interrupt_register((IRQn_Type)irq_line, handler);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Remove the callback registered on one validated external IRQ line.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 *
 * @note This function changes vector-table callback ownership only and does not disable or clear the
 *       physical interrupt line; IRQ Manager controls teardown ordering.
 *
 * @return ET_WRAP_STATUS_OK when the callback is removed.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is invalid.
 */
et_wrap_status_t et_irq_wrap_unregister(et_irq_line_t irq_line)
{
    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    Interrupt_unregister((IRQn_Type)irq_line);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Apply one caller-selected NVIC priority to a validated external IRQ line.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 * @param[in] priority Priority value constrained by the selected Cortex NVIC width.
 *
 * @note This function changes NVIC priority hardware only. It does not enable the line or change
 *       Feature IP interrupt masks.
 *
 * @return ET_WRAP_STATUS_OK when priority is written successfully.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when line or priority is outside the supported range.
 */
et_wrap_status_t et_irq_wrap_set_priority(et_irq_line_t irq_line, uint8_t priority)
{
    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    if ((uint32_t)priority >= (1u << __NVIC_PRIO_BITS))
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    NVIC_SetPriority((IRQn_Type)irq_line, priority);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Clear the pending state of one validated external IRQ line.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 *
 * @note This function changes NVIC pending hardware only. It does not clear the originating Feature
 *       IP interrupt status, which remains the owning IP Wrap's responsibility.
 *
 * @return ET_WRAP_STATUS_OK when pending state is cleared.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is invalid.
 */
et_wrap_status_t et_irq_wrap_clear_pending(et_irq_line_t irq_line)
{
    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    NVIC_ClearPendingIRQ((IRQn_Type)irq_line);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Enable one validated external interrupt line through the selected Driver.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 *
 * @note This function changes physical interrupt-line enable state only. The owning Service must
 *       enable its Feature IP source separately and in the R320-defined order.
 *
 * @return ET_WRAP_STATUS_OK when the line is enabled.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is invalid.
 */
et_wrap_status_t et_irq_wrap_enable(et_irq_line_t irq_line)
{
    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    Interrupt_enable((IRQn_Type)irq_line);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable one validated external interrupt line through the selected Driver.
 *
 * @param[in] irq_line Stable external IRQ line identifier.
 *
 * @note This function changes physical interrupt-line enable state only. It does not clear pending
 *       state, unregister callbacks or disable a Feature IP source.
 *
 * @return ET_WRAP_STATUS_OK when the line is disabled.
 * @return ET_WRAP_STATUS_STATE_ERROR when vector-table initialization has not completed.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is invalid.
 */
et_wrap_status_t et_irq_wrap_disable(et_irq_line_t irq_line)
{
    if (irq_wrap_initialized == 0u)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    if (validate_line(irq_line) != ET_WRAP_STATUS_OK)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    Interrupt_disable((IRQn_Type)irq_line);

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Translate the active ARM exception number into a stable external IRQ line.
 *
 * @param[out] irq_line Stable external IRQ line corresponding to the current exception.
 *
 * @note This function is intended for interrupt context and reads IPSR only. ARM system exceptions
 *       and out-of-range values are rejected rather than exposed as external IRQ identities.
 *
 * @return ET_WRAP_STATUS_OK when the active exception is a valid external IRQ.
 * @return ET_WRAP_STATUS_STATE_ERROR when current context is not a supported external IRQ.
 * @return ET_WRAP_STATUS_INVALID_ARGUMENT when irq_line is NULL.
 */
et_wrap_status_t et_irq_wrap_get_active_line(et_irq_line_t *irq_line)
{
    uint32_t exception_number;

    if (irq_line == NULL)
    {
        return ET_WRAP_STATUS_INVALID_ARGUMENT;
    }

    exception_number = __get_IPSR();

    if (exception_number < ET_IRQ_EXCEPTION_OFFSET)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    exception_number -= ET_IRQ_EXCEPTION_OFFSET;

    if (exception_number >= ET_IRQ_LINE_COUNT)
    {
        return ET_WRAP_STATUS_STATE_ERROR;
    }

    *irq_line = (et_irq_line_t)exception_number;

    return ET_WRAP_STATUS_OK;
}

/**
 * @brief Disable global interrupts and capture the caller's previous PRIMASK state.
 *
 * @note This function changes global interrupt-mask hardware immediately. The returned key must be
 *       restored by et_irq_wrap_exit_critical() to preserve the caller's original mask state.
 *
 * @return Previous PRIMASK value to use as the restore key.
 */
uint32_t et_irq_wrap_enter_critical(void)
{
    uint32_t previous_primask = __get_PRIMASK();
    (void)Interrupt_disableGlobal();

    return previous_primask;
}

/**
 * @brief Restore global interrupt enable state captured before a critical section.
 *
 * @param[in] previous_primask Restore key returned by et_irq_wrap_enter_critical().
 *
 * @note Global interrupts are re-enabled only when they were enabled before entry; an already-masked
 *       caller remains masked after exit.
 */
void et_irq_wrap_exit_critical(uint32_t previous_primask)
{
    if (previous_primask == 0u)
    {
        (void)Interrupt_enableGlobal();
    }
}
