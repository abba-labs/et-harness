#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "et_irq_manager.h"
#include "et_irq_wrap.h"

static uint32_t disable_calls;
static uint32_t clear_calls;
static uint32_t unregister_calls;
static uint32_t register_calls;
static uint8_t fail_disable_once;
static uint8_t fail_clear_once;
static uint8_t fail_unregister_once;
static uint8_t fail_register_once;

static void reset_stub_state(void)
{
    disable_calls = 0u;
    clear_calls = 0u;
    unregister_calls = 0u;
    register_calls = 0u;
    fail_disable_once = 0u;
    fail_clear_once = 0u;
    fail_unregister_once = 0u;
    fail_register_once = 0u;
}

et_wrap_status_t et_irq_wrap_init(void)
{
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_register(
    et_irq_line_t irq_line,
    et_irq_wrap_handler_t handler)
{
    (void)irq_line;
    (void)handler;
    ++register_calls;
    if (fail_register_once != 0u) {
        fail_register_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_unregister(et_irq_line_t irq_line)
{
    (void)irq_line;
    ++unregister_calls;
    if (fail_unregister_once != 0u) {
        fail_unregister_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_set_priority(
    et_irq_line_t irq_line,
    uint8_t priority)
{
    (void)irq_line;
    (void)priority;
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_clear_pending(et_irq_line_t irq_line)
{
    (void)irq_line;
    ++clear_calls;
    if (fail_clear_once != 0u) {
        fail_clear_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_enable(et_irq_line_t irq_line)
{
    (void)irq_line;
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_disable(et_irq_line_t irq_line)
{
    (void)irq_line;
    ++disable_calls;
    if (fail_disable_once != 0u) {
        fail_disable_once = 0u;
        return ET_WRAP_STATUS_IO_ERROR;
    }
    return ET_WRAP_STATUS_OK;
}

et_wrap_status_t et_irq_wrap_get_active_line(et_irq_line_t *irq_line)
{
    if (irq_line != NULL) {
        *irq_line = 0u;
    }
    return ET_WRAP_STATUS_NOT_SUPPORTED;
}

uint32_t et_irq_wrap_enter_critical(void)
{
    return 0u;
}

void et_irq_wrap_exit_critical(uint32_t previous_primask)
{
    (void)previous_primask;
}

static void callback(
    void *context,
    et_irq_line_t irq_line,
    uint32_t route_events)
{
    (void)context;
    (void)irq_line;
    (void)route_events;
}

static int bind_one(
    et_irq_manager_t *manager,
    et_irq_line_t line,
    void *context)
{
    et_irq_route_t route;

    (void)memset(&route, 0, sizeof(route));
    route.irq_line = line;
    route.route_events = 1u;
    return et_irq_manager_bind(manager, &route, 3u, callback, context);
}

static int test_unbind_resumes_first_unfinished_step(void)
{
    et_irq_manager_t manager;
    uint32_t context = 1u;

    reset_stub_state();
    et_irq_manager_init(&manager);
    if ((et_irq_manager_activate(&manager) != 0) ||
        (bind_one(&manager, 7u, &context) != 0)) {
        return 10;
    }
    reset_stub_state();
    fail_clear_once = 1u;
    if (et_irq_manager_unbind(
            &manager, 7u, callback, &context) == 0) {
        return 11;
    }
    if ((manager.bindings[0].in_use == 0u) ||
        (manager.bindings[0].cleanup_progress !=
         ET_IRQ_CLEANUP_DISABLED) ||
        (disable_calls != 1u) || (clear_calls != 1u) ||
        (unregister_calls != 0u) ||
        (et_irq_manager_cleanup_fault_count(&manager) != 1u)) {
        return 12;
    }
    if (et_irq_manager_unbind(
            &manager, 7u, callback, &context) != 0) {
        return 13;
    }
    if ((manager.bindings[0].in_use != 0u) ||
        (disable_calls != 1u) || (clear_calls != 2u) ||
        (unregister_calls != 1u)) {
        return 14;
    }
    return (et_irq_manager_deactivate(&manager) == 0) ? 0 : 15;
}

static int test_deactivate_keeps_active_manager_until_retry(void)
{
    et_irq_manager_t manager;
    uint32_t context_a = 1u;
    uint32_t context_b = 2u;

    reset_stub_state();
    et_irq_manager_init(&manager);
    if ((et_irq_manager_activate(&manager) != 0) ||
        (bind_one(&manager, 11u, &context_a) != 0) ||
        (bind_one(&manager, 12u, &context_b) != 0)) {
        return 20;
    }
    reset_stub_state();
    fail_unregister_once = 1u;
    if (et_irq_manager_deactivate(&manager) == 0) {
        return 21;
    }
    if ((manager.bindings[0].cleanup_progress !=
         (ET_IRQ_CLEANUP_DISABLED |
          ET_IRQ_CLEANUP_PENDING_CLEARED)) ||
        (et_irq_manager_cleanup_fault_count(&manager) != 1u)) {
        return 22;
    }
    if (et_irq_manager_deactivate(&manager) != 0) {
        return 23;
    }
    if ((disable_calls != 2u) || (clear_calls != 2u) ||
        (unregister_calls != 3u)) {
        return 24;
    }
    return 0;
}

static int test_bind_rollback_failure_is_observable(void)
{
    et_irq_manager_t manager;
    uint32_t context = 1u;

    reset_stub_state();
    et_irq_manager_init(&manager);
    if (et_irq_manager_activate(&manager) != 0) {
        return 30;
    }
    fail_register_once = 1u;
    fail_clear_once = 1u;
    if (bind_one(&manager, 17u, &context) == 0) {
        return 31;
    }
    if ((et_irq_manager_cleanup_fault_count(&manager) != 1u) ||
        (manager.bindings[0].in_use == 0u) ||
        (manager.bindings[0].cleanup_required == 0u) ||
        (manager.bindings[0].cleanup_progress !=
         ET_IRQ_CLEANUP_DISABLED)) {
        return 32;
    }
    if (et_irq_manager_dispatch(&manager, 17u) == 0) {
        return 33;
    }
    if (et_irq_manager_unbind(
            &manager, 17u, callback, &context) != 0) {
        return 34;
    }
    if (manager.bindings[0].in_use != 0u) {
        return 35;
    }
    return (et_irq_manager_deactivate(&manager) == 0) ? 0 : 36;
}

int main(void)
{
    int result;

    result = test_unbind_resumes_first_unfinished_step();
    if (result != 0) {
        (void)printf("unbind_retry=%d\n", result);
        return result;
    }
    result = test_deactivate_keeps_active_manager_until_retry();
    if (result != 0) {
        (void)printf("deactivate_retry=%d\n", result);
        return result;
    }
    result = test_bind_rollback_failure_is_observable();
    if (result != 0) {
        (void)printf("bind_rollback=%d\n", result);
        return result;
    }
    (void)printf("irq_manager_reliability=PASS\n");
    return 0;
}
