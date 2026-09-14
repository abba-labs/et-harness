"""Execute all production CRC P1 bodies against a strict wire/target boundary.

Uses the existing source-definition loader, production CRC models, validation,
codec, driver, recorder and fixture definitions. Target/CRG/Resource/registry and
hardware timing are explicit doubles. This is NOT a package-integration, MCU or
HIL test. The fixed input/command ledger below is independent of _p1_vectors.
"""
from __future__ import annotations

import ast
import inspect
import itertools
import json
import os
import struct
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.framework_validation.unit.drivers.crc.test_crc_reference_isolated import (
    PACKAGE, build_namespace, load_definitions,
)

NS = build_namespace()
NS.update(replace=replace, asdict=asdict)
NS["case_id_from_item"] = lambda item: "_".join(item.originalname.split("_")[1:4])
load_definitions(NS, "test_cases/crc/_support.py", {"make_crc_pattern"})
for _path in ("test_cases/crc/_p1_vectors.py", "test_cases/crc/_p1_evidence.py"):
    load_definitions(NS, _path)
load_definitions(NS, "test_cases/crc/conftest.py", {"crc_p1_evidence"})
load_definitions(NS, "test_cases/crc/test_crc_p1.py")
Command, Mode, Event, Xor = (NS[name] for name in ("CrcCommand", "CrcMode", "CrcIrqEvent", "CrcXorOut"))
CASES = {name: value for name, value in NS.items() if name.startswith("test_crc_p1_")}


def case_id(name):
    return "_".join(name.split("_")[1:4])


def nodes():
    result = []
    for name, fn in CASES.items():
        parameters = [{}]
        for mark in getattr(fn, "pytestmark", ()):
            if mark.name != "parametrize":
                continue
            names, values = mark.args[:2]
            names = (names,) if isinstance(names, str) else names
            rows = [dict(zip(names, (value,) if len(names) == 1 else value, strict=True)) for value in values]
            parameters = [{**before, **after} for before, after in itertools.product(parameters, rows)]
        result.extend((name, row) for row in parameters)
    return result


NODES = nodes()


def original_inputs(key, params):
    """Literal original wire fields and payload recipes, not the new vector factory."""
    width, flags, xor, threshold, poly, seed = 32, 4, 0, 1, 0x04C11DB7, 0xFFFFFFFF
    payloads = [bytes(range(1, 33))]
    if key == "crc_p1_001":
        poly = params["polynomial"]
    elif key == "crc_p1_002":
        seed = params["initial_value"]
    elif key == "crc_p1_003":
        width = int(params["mode"])
        flags = 4 * params["byte_swap"]
        poly, seed = (0x1021, 0xFFFF) if width == 16 else (0x04C11DB7, 0xFFFFFFFF)
        payloads = [bytes.fromhex("1122438415a637c8")]
    elif key == "crc_p1_004":
        poly, flags = 0x1EDC6F41, 4 + params["ref_in"]
    elif key == "crc_p1_005":
        width, poly, seed, flags = 16, 0x1021, 0xC6C6, 5 + 2 * params["ref_out"]
        payloads = [bytes(range(1, 16))]
    elif key == "crc_p1_006":
        width, poly, seed, flags, xor = 16, 0x3D65, 0, 7, int(params["xor_out"])
        payloads = [bytes(range(1, 8))]
    elif key == "crc_p1_007":
        width = int(params["mode"])
        poly, seed = (0x1021, 0xFFFF) if width == 16 else (0x04C11DB7, 0xFFFFFFFF)
        length = params["length_bytes"]
        payloads = [NS["make_crc_pattern"](length, seed=0x70000000 + length)]
    elif key == "crc_p1_008":
        flags = 12
        payloads = [NS["make_crc_pattern"](64, seed=value) for value in (0xA1, 0xA2)]
    elif key in {"crc_p1_009", "crc_p1_010"}:
        poly, flags, xor = 0x1EDC6F41, 23, 1
        payloads = [bytes(range(1, 8))]
    elif key == "crc_p1_012":
        payloads = [bytes(range(1, 9))]
    elif key in {"crc_p1_013", "crc_p1_014", "crc_p1_015"}:
        width, poly, seed, flags, payloads = 8, 7, 255, 0, []
    elif key == "crc_p1_016":
        payloads = []
    elif key == "crc_p1_018":
        width, poly, seed, flags, payloads = 8, 7, 255, 3, [bytes(range(1, 8))]
    else:
        raise AssertionError(key)
    return (width, flags, xor, threshold, poly, seed), payloads


# These are original device actions with the approved reset sequence substituted.
# Read-only capability discovery is allowed to move; all other requests are ordered.
PREFIX = "crg context_reset pool "
BASE = "create write enable configure "
TAIL = " disable pool"
LEDGER = {
    **{f"crc_p1_{n:03}": PREFIX + BASE + "calculate" + TAIL for n in range(1, 7)},
    "crc_p1_007": PREFIX + BASE + "data_length_set data_length_get calculate" + TAIL,
    "crc_p1_008": PREFIX + "create create write write enable configure data_length_set calculate calculate" + TAIL,
    "crc_p1_009": PREFIX + BASE + "irq_clear check_value_set calculate irq_snapshot_get" + TAIL,
    "crc_p1_010": PREFIX + BASE + "irq_clear irq_enable irq_unmask irq_snapshot_get check_value_set calculate irq_snapshot_get" + TAIL,
    "crc_p1_012": PREFIX + "enable configure fifo_status_get test_input_burst_32 disable pool create write enable configure calculate" + TAIL,
    "crc_p1_013": PREFIX + "enable configure irq_clear irq_enable irq_unmask irq_snapshot_get irq_force irq_snapshot_get irq_clear irq_disable irq_snapshot_get irq_force irq_snapshot_get irq_clear" + TAIL,
    "crc_p1_014": PREFIX + "enable configure irq_clear irq_enable irq_mask irq_snapshot_get irq_force irq_snapshot_get irq_clear irq_snapshot_get" + TAIL,
    "crc_p1_015": PREFIX + "enable configure irq_clear irq_enable irq_mask irq_snapshot_get irq_force irq_snapshot_get irq_clear irq_unmask irq_force irq_snapshot_get" + TAIL,
    "crc_p1_016": PREFIX + "enable configure irq_clear irq_enable irq_unmask irq_snapshot_get data_length_set test_input_write irq_snapshot_get" + TAIL,
    "crc_p1_018": PREFIX + "enable configure irq_clear irq_enable irq_unmask data_length_set irq_snapshot_get test_input_write irq_snapshot_get data_length_set test_input_write irq_snapshot_get disable pool create write enable configure calculate" + TAIL,
}
ASSERT_COUNTS = dict(zip(LEDGER, (2, 2, 2, 2, 3, 3, 3, 4, 3, 4, 4, 4, 6, 6, 3, 8), strict=True))


class P1Target:
    """Closed command set with stateful errors; never a permissive MagicMock."""
    def __init__(self, key, params, mutation=None, fail_action=None):
        self.key, self.params = key, params
        self.config_words, self.payloads = original_inputs(key, params)
        self.calls, self.memory, self.seen = [], {}, {}
        self.written = 0
        self.mutation, self.fail_action = mutation, fail_action
        self.counter, self.raw, self.effective = 99, 7, 7
        self.enabled_sources, self.masked, self.last_event, self.last_raw = 7, 0, 7, 7
        self.remaining, self.check = 0, None
        self.config = None
        self.enabled = False

    def action(self, name, *args):
        self.calls.append((name, args))
        if name == self.fail_action:
            raise RuntimeError(name)
        if name == "crg":
            self.raw = self.effective = self.enabled_sources = 0
            self.config, self.enabled = None, False
        if name == "pool":
            self.memory.clear()

    def signal(self, event):
        self.raw |= event
        active = event & self.enabled_sources & ~self.masked
        self.effective = self.raw & self.enabled_sources & ~self.masked
        if active:
            self.counter += 1
            self.last_raw, self.last_event = self.raw, active
            self.raw &= ~active
            self.effective &= ~active

    def request(self, service_id, command_id, *, instance_id=0, body=b"", retry_safe=False, timeout_s=None):
        assert service_id == 0x102 and instance_id == 0
        command = Command(command_id)
        name = command.name.lower()
        self.action(name, bytes(body))
        self.seen[name] = self.seen.get(name, 0) + 1
        data, fmt, fields = b"", None, None
        if command is Command.CONTEXT_RESET:
            assert not body and not retry_safe
            self.counter = self.last_event = self.last_raw = 0
        elif command is Command.CAPABILITIES_GET:
            data = struct.pack("<HHIBBBBI", 1, 16, (1 << 22) - 1, 7, 7, 8, 1, 4096)
        elif command is Command.ENABLE:
            self.enabled = True
        elif command is Command.DISABLE:
            self.enabled, self.enabled_sources = False, 0
        elif command is Command.CONFIGURE:
            assert self.enabled
            assert struct.unpack("<BBBBII", body) == self.config_words
            width, flags, xor, threshold, poly, seed = self.config_words
            self.config = NS["CrcConfig"](
                Mode(width), poly, seed, bool(flags & 1), bool(flags & 2), bool(flags & 4),
                bool(flags & 8), bool(flags & 16), Xor(xor), threshold,
            )
        elif command is Command.CALCULATE:
            address, size = struct.unpack("<QI", body)
            assert self.enabled and self.config is not None
            payload = self.memory[address]
            assert size == len(payload)
            value = NS["calculate_crc_reference"](self.config, payload)
            self.last_result = value
            if self.config.result_check and self.check != value:
                self.signal(4)
            fmt, fields = "<II", [value, self.remaining if self.config.auto_length_reload else 0]
        elif command is Command.RESULT_GET:
            fmt, fields = "<I", [self.last_result]
        elif command is Command.DATA_LENGTH_SET:
            size, = struct.unpack("<I", body)
            width = int(self.config.mode) // 8
            self.remaining = size // width + size % width
        elif command is Command.DATA_LENGTH_GET:
            fmt, fields = "<I", [self.remaining]
        elif command is Command.CHECK_VALUE_SET:
            self.check, = struct.unpack("<I", body)
        elif command is Command.FIFO_STATUS_GET:
            fmt, fields = "<B3x", [0]
        elif command is Command.TEST_INPUT_BURST_32:
            items = struct.unpack("<BBH9I", body)
            assert items == (7, 0, 0, *((0x12345678,) * 7), 0, 0)
            fmt, fields = "<BBHIIB3s", [7, 0, 0, 0, 0, 1, b"\0\0\0"]
        elif command is Command.IRQ_SNAPSHOT_GET:
            fmt, fields = "<IIIII", [self.raw, self.effective, self.counter, self.last_event, self.last_raw]
        elif command in {Command.IRQ_CLEAR, Command.IRQ_ENABLE, Command.IRQ_DISABLE,
                         Command.IRQ_MASK, Command.IRQ_UNMASK, Command.IRQ_FORCE}:
            event, = struct.unpack("<I", body)
            if command is Command.IRQ_CLEAR:
                self.raw &= ~event
                self.effective &= ~event
            elif command is Command.IRQ_ENABLE:
                self.enabled_sources |= event
            elif command is Command.IRQ_DISABLE:
                self.enabled_sources &= ~event
            elif command is Command.IRQ_MASK:
                self.masked |= event
            elif command is Command.IRQ_UNMASK:
                self.masked &= ~event
            else:
                self.signal(event)
        elif command is Command.TEST_INPUT_WRITE:
            width, value = struct.unpack("<B3xI", body)
            assert value == (0x12 if width == 8 else 0x12345678)
            if width > int(self.config.mode):
                self.signal(1)
            elif self.remaining == 0:
                self.signal(2)
            else:
                self.remaining -= 1
        else:
            raise AssertionError(f"Unexpected production command: {command}")
        if fields is not None:
            if self.mutation and self.mutation[:2] == (name, self.seen[name]):
                index, replacement = self.mutation[2:]
                fields[index] = replacement(fields[index]) if callable(replacement) else replacement
            data = struct.pack(fmt, *fields)
        return SimpleNamespace(body=data), None


class MemoryBoundary:
    def __init__(self, target):
        self.target = target

    def reset(self):
        self.target.action("pool")

    def create(self, size, alignment=4):
        assert alignment == 4
        address = 0x20001000 + 0x100 * len(self.target.memory)
        self.target.action("create", size, alignment)
        self.target.memory[address] = bytes(size)
        return SimpleNamespace(address=address, size=size, handle=address)

    def write(self, resource, data, offset=0):
        assert offset == 0 and resource.size == len(data)
        assert data == self.target.payloads[self.target.written]
        self.target.written += 1
        self.target.action("write", bytes(data))
        self.target.memory[resource.address] = bytes(data)


def finish(generator):
    with pytest.raises(StopIteration):
        next(generator)


def start(name, params, tmp_path, mutation=None, fail_action=None):
    key = case_id(name)
    target = P1Target(key, params, mutation, fail_action)
    records, resource = [], MemoryBoundary(target)
    record = lambda key, value: records.append((key, value))
    node = SimpleNamespace(originalname=name, callspec=SimpleNamespace(params=params))
    request = SimpleNamespace(node=node, session=SimpleNamespace(shouldstop=False))
    framework = SimpleNamespace(target_client=target, runtime_services=[
        SimpleNamespace(service_id=s, instance_id=0) for s in (0x102, 0x12, 0x10)
    ])
    capability = SimpleNamespace(instances=lambda ip: ("crc0",))
    lifetime = NS["crc0"].__wrapped__(request, framework, capability, resource, record)
    driver = next(lifetime)
    evidence = NS["crc_p1_evidence"].__wrapped__(request, driver, tmp_path, record)
    next(evidence)
    return target, driver, resource, lifetime, evidence, records, request


def invoke(name, params, driver, resource):
    arguments = {"crc0": driver, **params}
    if "resource_driver" in inspect.signature(CASES[name]).parameters:
        arguments["resource_driver"] = resource
    CASES[name](**arguments)


@pytest.mark.parametrize("name,params", NODES, ids=[f"{n}-{i}" for i, (n, _) in enumerate(NODES)])
def test_every_node_keeps_original_inputs_commands_and_records(name, params, tmp_path):
    target, driver, resource, lifetime, evidence, records, _ = start(name, params, tmp_path)
    invoke(name, params, driver, resource)
    before = len(target.calls)
    finish(evidence)
    assert len(target.calls) == before, "Evidence must not read or mutate hardware"
    finish(lifetime)
    actual = [name for name, _ in target.calls if name != "capabilities_get"]
    assert actual == LEDGER[case_id(name)].split()
    assert target.written == len(target.payloads)
    report = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert report["case_id"] == case_id(name) and report["instance"] == "crc0"
    assert report["calculations"] == [asdict(value) for value in driver.calculations]
    assert report["irq_snapshots"] == [asdict(value) for value in driver.irq_snapshots]
    assert report["config"]["polynomial"] == target.config_words[4]
    assert any(k == "crc_p1_result" for k, _ in records)


# Every original assert is retained structurally; each normal parameter executes.
def test_case_counts_parameters_assertions_and_no_hidden_operations():
    assert len(CASES) == 16 and len(NODES) == 33
    expected_counts = (3, 3, 4, 2, 2, 2, 6, 1, 1, 1, 1, 3, 1, 1, 1, 1)
    assert tuple(sum(case_id(name) == key for name, _ in NODES) for key in LEDGER) == expected_counts
    text = (PACKAGE / "test_cases/crc/test_crc_p1.py").read_text(encoding="utf-8")
    tree, lines = ast.parse(text), text.splitlines()
    exceptions = {"crc_p1_015": 21, "crc_p1_018": 31}
    for fn in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        key = case_id(fn.name)
        assert sum(isinstance(n, ast.Assert) for n in ast.walk(fn)) == ASSERT_COUNTS[key]
        assert not any(isinstance(n, (ast.With, ast.Try, ast.AsyncFunctionDef)) for n in ast.walk(fn))
        assert ast.unparse(fn.body[0]) == "crc_handle = crc0"
        assert ast.unparse(fn.body[1]) == "crc_handle.reset()"
        count = sum(bool(line.strip()) and not line.lstrip().startswith("#") for line in lines[fn.body[0].lineno - 1:fn.end_lineno])
        assert count <= exceptions.get(key, 20)
        assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id in {"record_property", "record_observation", "write_json_result"}
                       for n in ast.walk(fn))


MUTATIONS = []
for key in LEDGER:
    if key not in {"crc_p1_013", "crc_p1_014", "crc_p1_015", "crc_p1_016"}:
        MUTATIONS.append((key, ("calculate", 1, 0, lambda value: value ^ 1)))
    if key in {"crc_p1_001", "crc_p1_002", "crc_p1_003", "crc_p1_004", "crc_p1_005", "crc_p1_006", "crc_p1_007", "crc_p1_008", "crc_p1_012", "crc_p1_018"}:
        MUTATIONS.append((key, ("calculate", 1, 1, lambda value: value + 1)))
MUTATIONS += [
    ("crc_p1_007", ("data_length_get", 1, 0, lambda x: x + 1)),
    ("crc_p1_008", ("calculate", 2, 0, lambda x: x ^ 1)),
    ("crc_p1_008", ("calculate", 2, 1, 0)),
    ("crc_p1_009", ("irq_snapshot_get", 1, 0, 4)),
    ("crc_p1_009", ("irq_snapshot_get", 1, 1, 4)),
    ("crc_p1_012", ("fifo_status_get", 1, 0, 1)),
    ("crc_p1_012", ("test_input_burst_32", 1, 5, 0)),
    ("crc_p1_013", ("irq_snapshot_get", 4, 2, 2)),
]
for key, index, event in (("crc_p1_010", 2, 4), ("crc_p1_013", 2, 1), ("crc_p1_015", 3, 2), ("crc_p1_016", 2, 2), ("crc_p1_018", 3, 1)):
    MUTATIONS.extend((key, ("irq_snapshot_get", index, field, 0)) for field in (2, 3, 4))
for key in ("crc_p1_014", "crc_p1_015"):
    MUTATIONS.extend((key, ("irq_snapshot_get", 2, field, value)) for field, value in ((0, 0), (1, 1), (2, 1)))
MUTATIONS.extend(("crc_p1_014", ("irq_snapshot_get", 3, field, 1)) for field in (0, 1, 2))
MUTATIONS.extend(("crc_p1_018", ("irq_snapshot_get", 2, field, 1)) for field in (0, 1, 2))


@pytest.mark.parametrize("key,mutation", MUTATIONS)
def test_decisive_wrong_facts_fail_and_survive_teardown(key, mutation, tmp_path):
    name, params = next((name, p) for name, p in NODES if case_id(name) == key)
    target, driver, resource, lifetime, evidence, records, _ = start(name, params, tmp_path, mutation)
    with pytest.raises(AssertionError):
        invoke(name, params, driver, resource)
    finish(evidence)
    finish(lifetime)
    report = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert report["calculations"] == [asdict(value) for value in driver.calculations]
    assert report["irq_snapshots"] == [asdict(value) for value in driver.irq_snapshots]
    assert "status" not in report or not isinstance(report["status"], str)
    assert "verdict" not in report


@pytest.mark.parametrize("fault", ("crg", "context_reset", "pool", "enable", "configure", "calculate"))
def test_start_or_execution_failure_never_manufactures_a_result(fault, tmp_path):
    name, params = NODES[0]
    target, driver, resource, lifetime, evidence, _, request = start(name, params, tmp_path, fail_action=fault)
    with pytest.raises(RuntimeError, match=fault):
        invoke(name, params, driver, resource)
    finish(evidence)
    # Only the requested operation fails; cleanup can run after an execution error.
    target.fail_action = None
    finish(lifetime)
    report = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert report["calculations"] == [] and "actual" not in report
    if fault in {"crg", "context_reset", "pool"}:
        assert request.session.shouldstop
        assert not any(n == "configure" for n, _ in target.calls)


def test_test_failure_and_cleanup_failure_are_both_visible(tmp_path):
    name, params = NODES[0]
    parts = start(name, params, tmp_path, ("calculate", 1, 0, lambda v: v ^ 1))
    target, driver, resource, lifetime, evidence, _, request = parts
    with pytest.raises(AssertionError):
        invoke(name, params, driver, resource)
    finish(evidence)
    pools = sum(n == "pool" for n, _ in target.calls)
    target.fail_action = "disable"
    with pytest.raises(RuntimeError, match="disable"):
        next(lifetime)
    assert request.session.shouldstop
    assert sum(n == "pool" for n, _ in target.calls) == pools
    assert next(tmp_path.glob("*.json")).exists()


def test_real_pytest_fixture_graph_runs_all_33_p1_nodes(tmp_path):
    """Actual pytest setup/call/teardown of production bodies; platform imports are NOT covered."""
    shim = tmp_path / "test_selected.py"
    shim.write_text('''from pathlib import Path
from types import SimpleNamespace
import pytest
from et_test_platform.framework_validation.unit.drivers.crc.test_crc_p1_batch_isolated import NS, CASES, P1Target, MemoryBoundary, case_id
globals().update(CASES)
pytestmark = NS["pytestmark"]
crc0 = NS["crc0"]
crc_p1_evidence = NS["crc_p1_evidence"]
@pytest.fixture
def boundary(request):
    params = dict(request.node.callspec.params) if hasattr(request.node, "callspec") else {}
    return P1Target(case_id(request.node.originalname), params)
@pytest.fixture
def framework_communication(boundary):
    return SimpleNamespace(target_client=boundary, runtime_services=[SimpleNamespace(service_id=s, instance_id=0) for s in (0x102, 0x12, 0x10)])
@pytest.fixture
def target_capabilities():
    return SimpleNamespace(instances=lambda ip: ("crc0",))
@pytest.fixture
def resource_driver(boundary):
    return MemoryBoundary(boundary)
@pytest.fixture
def et_artifact_dir(tmp_path):
    return tmp_path
''', encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(PACKAGE.parent), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", str(shim), "--confcutdir", str(tmp_path)], cwd=tmp_path, env=env, text=True, capture_output=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "33 passed" in result.stdout


OBSERVATION_KEYS = {
    **{f"crc_p1_{n:03}": {"actual_crc", "remaining_input_count"} for n in range(1, 7)},
    "crc_p1_007": {"actual_crc", "remaining_input_count", "programmed_input_count"},
    "crc_p1_008": {"first_actual_crc", "first_remaining_input_count", "second_actual_crc", "second_remaining_input_count"},
    "crc_p1_009": {"actual_crc", "check_error_raw", "check_error_status"},
    "crc_p1_010": {"actual_crc", "check_error_raw", "check_error_status", "isr_latched_event", "isr_last_raw"},
    "crc_p1_012": {"overflow_before", "overflow_after", "recovery_actual_crc", "recovery_remaining_input_count"},
    "crc_p1_013": {"delivered_isr_event", "delivered_isr_last_raw", "disabled_force_raw"},
    "crc_p1_014": {"raw_before_clear", "status_before_clear", "raw_after_clear", "status_after_clear"},
    "crc_p1_015": {"masked_raw_status", "masked_effective_status", "unmasked_raw_status", "unmasked_effective_status", "unmasked_isr_event", "unmasked_isr_last_raw"},
    "crc_p1_016": {"irq_raw_status", "irq_status", "isr_latched_event", "isr_last_raw"},
    "crc_p1_018": {"legal_bus_error_raw", "legal_bus_error_status", "irq_raw_status", "irq_status", "isr_latched_event", "isr_last_raw", "recovery_actual_crc", "recovery_remaining_input_count"},
}


@pytest.mark.parametrize("name,params", NODES)
def test_original_canonical_observation_keys_remain(name, params, tmp_path):
    target, driver, resource, lifetime, evidence, records, _ = start(name, params, tmp_path)
    invoke(name, params, driver, resource)
    finish(evidence)
    finish(lifetime)
    observations = [value for key, value in records if key == "et_observation"]
    assert OBSERVATION_KEYS[case_id(name)] <= {item["key"] for item in observations}
    assert all(item["source"] == "dut" and item["endpoint"] for item in observations)


@pytest.mark.parametrize("vector", NS["_P0_MODE_VECTORS"])
def test_existing_p0_reference_observations_are_unchanged(vector):
    config, payload, expected = vector
    target = P1Target("crc_p1_001", {"polynomial": config.polynomial})
    flags = int(config.ref_in) | (int(config.ref_out) << 1) | (int(config.byte_swap) << 2)
    target.config_words = (int(config.mode), flags, int(config.xor_out), config.fifo_threshold, config.polynomial, config.initial_value)
    target.payloads = [payload]
    records = []
    driver = NS["RecordedCrcDriver"](target, 0, lambda k, v: records.append((k, v)))
    NS["test_crc_p0_002_mode_reference_vectors"](driver, MemoryBoundary(target), config, payload, expected)
    observed = {v["key"]: v["value"] for k, v in records if k == "et_observation"}
    assert observed == {"actual_crc": expected, "remaining_input_count": 0, "result_readback": expected}
    assert len(driver.calculations) == 1
