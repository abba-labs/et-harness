"""Compile the actual CRC Service and header with IRQ/Wrap boundary doubles.

These tests execute the production command dispatcher. The IRQ Manager and
peripheral Wrap are doubles: this is not an NVIC, target-build or HIL result.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "firmware").is_dir())

WRAP_HEADER = r"""
#ifndef ET_CRC_WRAP_H
#define ET_CRC_WRAP_H
#include <stdint.h>
typedef uint16_t et_crc_id_t;
typedef int et_wrap_status_t;
enum { ET_WRAP_STATUS_OK, ET_WRAP_STATUS_INVALID_ARGUMENT, ET_WRAP_STATUS_STATE_ERROR,
       ET_WRAP_STATUS_NOT_SUPPORTED, ET_WRAP_STATUS_BUSY, ET_WRAP_STATUS_NO_RESOURCE,
       ET_WRAP_STATUS_TIMEOUT };
#define ET_CRC_WRAP_MODE_CRC8 8u
#define ET_CRC_WRAP_MODE_CRC16 16u
#define ET_CRC_WRAP_MODE_CRC32 32u
#define ET_CRC_WRAP_API_VERSION 1u
#define ET_CRC_WRAP_MAX_BURST_ITEMS 9u
#define ET_CRC_WRAP_MAX_CALCULATE_BYTES 4096u
#define ET_CRC_WRAP_IRQ_ALL 7u
typedef struct {
    uint16_t struct_size, api_version;
    et_crc_id_t crc_id;
    uint8_t mode, ref_in, ref_out, byte_swap, auto_length_reload, result_check;
    uint8_t xor_out, fifo_threshold;
    uint32_t polynomial, initial_value;
} et_crc_wrap_config_t;
typedef struct { uint32_t raw, status; } et_crc_wrap_irq_snapshot_t;
extern unsigned wrap_calls;
/* Every legacy Wrap call is an explicit boundary double, never a hardware result. */
#define WRAP_STUB(name) static int name(et_crc_id_t id, ...) { \
    (void)id; ++wrap_calls; return ET_WRAP_STATUS_NOT_SUPPORTED; }
WRAP_STUB(et_crc_wrap_irq_snapshot_get)
WRAP_STUB(et_crc_wrap_irq_clear)
WRAP_STUB(et_crc_wrap_irq_disable)
WRAP_STUB(et_crc_wrap_get_irq_route)
WRAP_STUB(et_crc_wrap_irq_enable)
WRAP_STUB(et_crc_wrap_calculate)
WRAP_STUB(et_crc_wrap_data_length_get)
WRAP_STUB(et_crc_wrap_test_calculate_timed)
WRAP_STUB(et_crc_wrap_get_fifo_threshold_max)
WRAP_STUB(et_crc_wrap_enable)
WRAP_STUB(et_crc_wrap_disable)
WRAP_STUB(et_crc_wrap_configure)
WRAP_STUB(et_crc_wrap_data_length_set)
WRAP_STUB(et_crc_wrap_result_get)
WRAP_STUB(et_crc_wrap_check_value_set)
WRAP_STUB(et_crc_wrap_fifo_status_get)
WRAP_STUB(et_crc_wrap_irq_mask)
WRAP_STUB(et_crc_wrap_irq_unmask)
WRAP_STUB(et_crc_wrap_irq_force)
WRAP_STUB(et_crc_wrap_test_input_write)
WRAP_STUB(et_crc_wrap_test_input_burst_32)
#endif
"""

IRQ_HEADER = r"""
#ifndef ET_IRQ_MANAGER_H
#define ET_IRQ_MANAGER_H
#include <stdint.h>
#define ET_FRAMEWORK_MAX_IRQ_BINDINGS 8u
typedef uint32_t et_irq_line_t;
typedef struct { et_irq_line_t irq_line; uint32_t events; } et_irq_route_t;
typedef void (*et_irq_callback_t)(void *, et_irq_line_t, uint32_t);
typedef struct {
    et_irq_line_t irq_line;
    et_irq_callback_t callback;
    void *context;
    uint32_t route_events;
    uint8_t priority, in_use, cleanup_progress, cleanup_required;
} et_irq_binding_t;
typedef struct {
    et_irq_binding_t bindings[ET_FRAMEWORK_MAX_IRQ_BINDINGS];
    uint32_t cleanup_fault_count;
} et_irq_manager_t;
uint32_t et_irq_manager_enter_critical(void);
void et_irq_manager_exit_critical(uint32_t key);
int et_irq_manager_bind(et_irq_manager_t *, const et_irq_route_t *, uint8_t, et_irq_callback_t, void *);
int et_irq_manager_unbind(et_irq_manager_t *, et_irq_line_t, et_irq_callback_t, void *);
#endif
"""

ROUTER_HEADER = r"""
#ifndef ET_SERVICE_ROUTER_H
#define ET_SERVICE_ROUTER_H
#include <stdint.h>
typedef struct {
    uint16_t service_id, instance_id;
    void *context;
    uint16_t (*handle)(void *, uint16_t, const uint8_t *, uint16_t, uint8_t *, uint16_t, uint16_t *);
    void (*poll)(void *);
} et_service_descriptor_t;
#endif
"""

HARNESS = r"""
#include <assert.h>
#include <stdlib.h>
#include <string.h>
unsigned wrap_calls;
static unsigned unbind_calls, critical_depth;
static int fail_unbind;
#include "et_crc_service.c"

uint32_t et_irq_manager_enter_critical(void) { return critical_depth++; }
void et_irq_manager_exit_critical(uint32_t key) { assert(critical_depth == key + 1); critical_depth = key; }
int et_irq_manager_bind(et_irq_manager_t *m, const et_irq_route_t *r, uint8_t p,
                        et_irq_callback_t cb, void *ctx) {
    (void)m; (void)r; (void)p; (void)cb; (void)ctx; return -1;
}
int et_irq_manager_unbind(et_irq_manager_t *m, et_irq_line_t line, et_irq_callback_t cb, void *ctx) {
    unsigned i;
    ++unbind_calls;
    if (fail_unbind) return -1;
    for (i = 0; i < ET_FRAMEWORK_MAX_IRQ_BINDINGS; ++i) {
        et_irq_binding_t *b = &m->bindings[i];
        if (b->in_use && b->irq_line == line && b->callback == cb && b->context == ctx) {
            memset(b, 0, sizeof(*b)); return 0;
        }
    }
    return -1;
}
static void unrelated_callback(void *c, et_irq_line_t l, uint32_t e) { (void)c; (void)l; (void)e; }
static void dirty(et_crc_service_t *s) {
    s->enabled = 1; s->configured = 1; s->mode = 32; s->irq_bound = 1;
    s->irq_enabled_sources = 7; s->irq_event_count = 91;
    s->irq_last_event = 4; s->irq_last_raw = 7; s->irq_route.irq_line = 10;
}
static void bind_slot(et_irq_manager_t *m, unsigned index, et_irq_callback_t cb, void *ctx) {
    m->bindings[index].in_use = 1; m->bindings[index].callback = cb;
    m->bindings[index].context = ctx; m->bindings[index].irq_line = 10;
}
static uint16_t dispatch(et_crc_service_t *s, uint16_t size) {
    uint8_t body[1] = {0}; uint8_t response[32] = {0}; uint16_t used = 99;
    uint16_t result = s->descriptor.handle(s, ET_CRC_COMMAND_CONTEXT_RESET,
        body, size, response, sizeof(response), &used);
    assert(used == 0); return result;
}
static void assert_clean(const et_crc_service_t *s, const et_service_descriptor_t *d,
                         const et_irq_manager_t *m) {
    assert(!s->enabled && !s->configured && !s->mode && !s->irq_bound);
    assert(!s->irq_enabled_sources && !s->irq_event_count && !s->irq_last_event && !s->irq_last_raw);
    assert(s->crc_id == 2 && s->irq_priority == 5 && s->irq_manager == m);
    assert(memcmp(&s->descriptor, d, sizeof(*d)) == 0);
    assert(!wrap_calls && !critical_depth);
}
int main(int argc, char **argv) {
    et_crc_service_t selected, other, before;
    et_irq_manager_t manager;
    et_service_descriptor_t descriptor;
    int scenario;
    assert(argc == 2); scenario = atoi(argv[1]);
    memset(&manager, 0, sizeof(manager));
    assert(et_crc_service_init(&selected, 2, &manager, 5) == 0);
    assert(et_crc_service_init(&other, 3, &manager, 6) == 0);
    descriptor = selected.descriptor;
    dirty(&selected); dirty(&other);
    bind_slot(&manager, 0, crc_irq_callback, &selected);
    bind_slot(&manager, 1, crc_irq_callback, &other);
    bind_slot(&manager, 2, unrelated_callback, &selected);
    if (scenario == 1) {
        /* A failed setup may retain a Manager entry with no local bound flag. */
        selected.irq_bound = 0;
        manager.bindings[0].cleanup_required = 1;
    }
    if (scenario == 2) {
        fail_unbind = 1; before = selected;
        assert(dispatch(&selected, 0) == ET_STATUS_INTERNAL_ERROR);
        assert(memcmp(&selected, &before, sizeof(selected)) == 0);
        assert(manager.bindings[0].in_use && unbind_calls == 1);
    } else if (scenario == 3) {
        before = selected;
        assert(dispatch(&selected, 1) == ET_STATUS_INVALID_PARAM);
        assert(memcmp(&selected, &before, sizeof(selected)) == 0);
        assert(!unbind_calls && manager.bindings[0].in_use);
    } else if (scenario == 4) {
        selected.irq_manager = NULL; before = selected;
        assert(dispatch(&selected, 0) == ET_STATUS_INTERNAL_ERROR);
        assert(memcmp(&selected, &before, sizeof(selected)) == 0);
        assert(!unbind_calls);
    } else {
        if (scenario == 5) memset(&manager.bindings[0], 0, sizeof(manager.bindings[0]));
        assert(dispatch(&selected, 0) == ET_STATUS_OK);
        assert_clean(&selected, &descriptor, &manager);
        assert(!manager.bindings[0].in_use);
        assert(unbind_calls == (scenario == 5 ? 0u : 1u));
        /* A second empty reset must remain safe without touching another owner. */
        assert(dispatch(&selected, 0) == ET_STATUS_OK);
        assert_clean(&selected, &descriptor, &manager);
    }
    assert(manager.bindings[1].in_use && manager.bindings[2].in_use);
    assert(other.irq_event_count == 91 && other.irq_enabled_sources == 7);
    assert(!wrap_calls && !critical_depth);
    return 0;
}
"""


@pytest.fixture(scope="module")
def crc_reset_native(tmp_path_factory):
    compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not compiler:
        pytest.skip("native C compiler is not available")
    work = tmp_path_factory.mktemp("crc_context_reset")
    headers = {
        "et_crc_wrap.h": WRAP_HEADER,
        "et_irq_manager.h": IRQ_HEADER,
        "et_service_router.h": ROUTER_HEADER,
        "et_service_factory.h": '#include "et_irq_manager.h"\n'
        'typedef struct { et_irq_manager_t *irq_manager; uint8_t irq_priority; } '
        'et_service_factory_context_t;\n',
        "et_message.h": 'enum { ET_STATUS_OK, ET_STATUS_INVALID_PARAM, ET_STATUS_NOT_SUPPORTED, '
        'ET_STATUS_BUSY, ET_STATUS_INTERNAL_ERROR, ET_STATUS_INVALID_COMMAND };\n',
    }
    for name, text in headers.items():
        (work / name).write_text(text, encoding="utf-8")
    source = work / "test.c"
    source.write_text(HARNESS, encoding="utf-8")
    binary = work / "crc_reset"
    subprocess.run(
        [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", str(source),
         "-I", str(ROOT / "firmware/services/src"),
         "-I", str(ROOT / "firmware/services/include"), "-I", str(work),
         "-o", str(binary)], check=True, capture_output=True, text=True, timeout=30,
    )
    return binary


@pytest.mark.parametrize("scenario", range(6), ids=(
    "owned_binding", "retained_binding", "unbind_failure", "malformed_body",
    "missing_manager", "already_unbound",
))
def test_crc_context_reset_native(crc_reset_native, scenario):
    subprocess.run([str(crc_reset_native), str(scenario)], check=True, timeout=10)
