"""Isolated execution of production CRC source and the reference Case.

Loads the actual model/codec/validation/driver/fixture definitions unchanged,
without importing the unrelated platform packages. Target, CRG, Resource and
recording are explicit boundary doubles. This does NOT validate package imports,
TargetClient/Transport, canonical report integration, or physical CRC hardware.
"""
from __future__ import annotations

import ast
import hashlib
import json
import struct
import sys
import types
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "firmware").is_dir())
PACKAGE = ROOT / "pc/et_test_platform"


class ProtocolError(RuntimeError):
    pass


class ConfigurationError(RuntimeError):
    pass


# An identity marker, not a fabricated physical CRG peripheral number.
CrgPeripheral = SimpleNamespace(CRC=object())


class CrgBoundary:
    def __init__(self, target):
        self.target = target

    def reset(self, peripheral, *, instance):
        assert peripheral is CrgPeripheral.CRC
        self.target.action("crg", instance)


class ResourceBoundary:
    def __init__(self, target):
        self.target = target

    def reset(self):
        self.target.action("pool")

    def create(self, size, alignment=4):
        assert alignment == 4 and size == len(self.target.payload)
        self.target.action("create", size, alignment)
        return SimpleNamespace(handle=1, address=0x20001000, size=size)

    def write(self, resource, data, offset=0):
        assert resource.address == 0x20001000 and offset == 0
        assert data == self.target.payload
        self.target.action("write", bytes(data))


def record_boundary(record, *, key, value, source, endpoint):
    record("et_observation", {"key": key, "value": value, "source": source, "endpoint": endpoint})


def write_boundary(path, payload):
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def load_definitions(namespace, relative, names=None):
    path = PACKAGE / relative
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if names is not None:
            name = getattr(node, "name", None)
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                name = getattr(node.targets[0], "id", None)
            if name not in names:
                continue
        selected.append(node)
    tree.body = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected]
    exec(compile(ast.fix_missing_locations(tree), str(path), "exec"), namespace)


def build_namespace():
    module = types.ModuleType("_crc_reference_isolated_source")
    sys.modules[module.__name__] = module
    ns = module.__dict__
    ns.update(
        dataclass=dataclass, IntEnum=IntEnum, IntFlag=IntFlag, struct=struct,
        Callable=Callable, Iterator=Iterator, contextmanager=contextmanager,
        ProtocolError=ProtocolError, ConfigurationError=ConfigurationError,
        UnsupportedCapability=ConfigurationError, pytest=pytest, hashlib=hashlib,
        CrgPeripheral=CrgPeripheral, CrgDriver=CrgBoundary, ResourceDriver=ResourceBoundary,
        CRG_SERVICE_ID=0x12, RESOURCE_SERVICE_ID=0x10, RESOURCE_INSTANCE_ID=0,
        record_observation=record_boundary, write_json_result=write_boundary,
    )
    for path in ("drivers/crc/models.py", "drivers/crc/contract.py",
                 "drivers/crc/codec.py", "drivers/crc/validation.py", "drivers/crc/driver.py"):
        load_definitions(ns, path)
    load_definitions(ns, "test_cases/crc/_support.py", {
        "crc_width_mask", "reflect_bits", "calculate_crc_reference", "require_crc_runtime_capability",
    })
    load_definitions(ns, "scheduling/crc_evidence.py")
    load_definitions(ns, "test_cases/crc/conftest.py", {"crc0", "crc_reference_evidence"})
    load_definitions(ns, "test_cases/crc/test_crc_p0.py", {
        "_P0_MODE_VECTORS", "test_crc_p0_002_mode_reference_vectors",
    })
    return ns


NS = build_namespace()
VECTORS = NS["_P0_MODE_VECTORS"]
Driver = NS["CrcDriver"]
RecordedDriver = NS["RecordedCrcDriver"]
Command = NS["CrcCommand"]
case_body = NS["test_crc_p0_002_mode_reference_vectors"]


class TargetBoundary:
    def __init__(self, payload=b"", expected=0, fault=None):
        self.payload, self.expected, self.fault = payload, expected, fault
        self.calls = []
        self.configuration_body = None

    def action(self, name, *args):
        self.calls.append((name, args))
        if self.fault == name:
            raise RuntimeError(name)

    def request(self, service_id, command_id, *, instance_id=0, body=b"", retry_safe=False, timeout_s=None):
        assert service_id == 0x102
        command = Command(command_id)
        self.action(command.name.lower(), instance_id, bytes(body), retry_safe, timeout_s)
        if command is Command.CONTEXT_RESET:
            assert body == b"" and retry_safe is False
            data = b"bad" if self.fault == "malformed_context" else b""
        elif command is Command.CAPABILITIES_GET:
            data = struct.pack("<HHIBBBBI", 1, 16, (1 << 22) - 1, 7, 7, 8, 1, 4096)
        elif command is Command.CONFIGURE:
            self.configuration_body = body
            data = b""
        elif command is Command.CALCULATE:
            assert body == struct.pack("<QI", 0x20001000, len(self.payload))
            value = self.expected ^ int(self.fault == "wrong_result")
            data = struct.pack("<II", value, int(self.fault == "remaining"))
        elif command is Command.RESULT_GET:
            data = struct.pack("<I", self.expected ^ int(self.fault == "wrong_readback"))
        elif command in {Command.ENABLE, Command.DISABLE}:
            assert body == b""
            data = b""
        else:
            raise AssertionError(f"Unexpected command: {command}")
        return SimpleNamespace(body=data), None


def start_crc_fixture(target, records, declared=("crc0",)):
    session = SimpleNamespace(shouldstop=False)
    request = SimpleNamespace(session=session)
    framework = SimpleNamespace(
        target_client=target,
        runtime_services=[SimpleNamespace(service_id=s, instance_id=0) for s in (0x102, 0x12, 0x10)],
    )
    capabilities = SimpleNamespace(instances=lambda ip: declared)
    resource = ResourceBoundary(target)
    generator = NS["crc0"].__wrapped__(request, framework, capabilities, resource, lambda k, v: records.append((k, v)))
    return next(generator), resource, generator, session


def finish(generator):
    with pytest.raises(StopIteration):
        next(generator)


@pytest.mark.parametrize("vector", VECTORS, ids=("crc8", "crc16", "crc32"))
def test_reference_case_executes_original_vector_and_keeps_observations(vector, tmp_path):
    config, payload, expected = vector
    target = TargetBoundary(payload, expected)
    records = []
    crc, resource, lifetime, _ = start_crc_fixture(target, records)
    evidence = NS["crc_reference_evidence"].__wrapped__(
        crc, config, payload, expected, tmp_path, lambda k, v: records.append((k, v)),
    )
    next(evidence)
    case_body(crc, resource, config, payload, expected)
    finish(evidence)
    finish(lifetime)
    observed = {v["key"]: v["value"] for k, v in records if k == "et_observation"}
    assert observed == {"actual_crc": expected, "remaining_input_count": 0, "result_readback": expected}
    report = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert report["actual"] == report["pc_expected"] == report["fixed_expected"] == expected
    assert report["result_readback"] == expected and report["remaining_input_count"] == 0
    assert report["payload_sha256"] == hashlib.sha256(payload).hexdigest()
    # Independent expected wire fields from the unchanged historical vectors.
    flags = 3 if config.mode.value == 8 else 7
    xor_out = 1 if config.mode.value == 32 else 0
    assert target.configuration_body == struct.pack(
        "<BBBBII", config.mode.value, flags, xor_out, 1, config.polynomial, config.initial_value,
    )
    names = [name for name, _ in target.calls]
    critical = [n for n in names if n != "capabilities_get"]
    assert critical == ["crg", "context_reset", "pool", "create", "write", "enable", "configure",
                        "calculate", "result_get", "disable", "pool"]


@pytest.mark.parametrize("fault", ("wrong_result", "remaining", "wrong_readback"))
@pytest.mark.parametrize("vector", VECTORS, ids=("crc8", "crc16", "crc32"))
def test_each_decisive_error_fails_and_retains_actual_values(fault, vector, tmp_path):
    config, payload, expected = vector
    target = TargetBoundary(payload, expected, fault)
    records = []
    crc, resource, lifetime, _ = start_crc_fixture(target, records)
    evidence = NS["crc_reference_evidence"].__wrapped__(
        crc, config, payload, expected, tmp_path, lambda k, v: records.append((k, v)),
    )
    next(evidence)
    with pytest.raises(AssertionError):
        case_body(crc, resource, config, payload, expected)
    assert len([1 for k, _ in records if k == "et_observation"]) == 3
    finish(evidence)
    finish(lifetime)
    report = json.loads(next(tmp_path.glob("*.json")).read_text())
    assert report["actual"] == (expected ^ int(fault == "wrong_result"))
    assert report["remaining_input_count"] == int(fault == "remaining")
    assert report["result_readback"] == (expected ^ int(fault == "wrong_readback"))


@pytest.mark.parametrize("fault,last", (("crg", "crg"), ("context_reset", "context_reset"),
                                       ("pool", "pool"), ("malformed_context", "context_reset")))
def test_reset_failure_never_continues_configuring_or_clears_pool_in_teardown(fault, last):
    records = []
    target = TargetBoundary(fault=fault)
    crc, _, lifetime, session = start_crc_fixture(target, records)
    crc._mode = NS["CrcMode"].CRC32
    crc._max_calculate_bytes = 4096
    with pytest.raises(RuntimeError):
        crc.reset()
    assert target.calls[-1][0] == last
    pool_calls = sum(n == "pool" for n, _ in target.calls)
    assert not crc.reset_completed
    assert crc._mode is None and crc._max_calculate_bytes is None
    finish(lifetime)
    assert session.shouldstop
    assert sum(n == "pool" for n, _ in target.calls) == pool_calls
    assert all(n not in {"enable", "configure", "calculate"} for n, _ in target.calls)


def test_missing_crc0_never_falls_back():
    target = TargetBoundary()
    with pytest.raises(ConfigurationError):
        start_crc_fixture(target, [], declared=("crc1",))
    assert target.calls == []


def test_cleanup_failure_is_not_suppressed_and_pool_is_not_released():
    target = TargetBoundary()
    crc, _, lifetime, session = start_crc_fixture(target, [])
    crc.reset()
    target.fault = "disable"
    with pytest.raises(RuntimeError, match="disable"):
        next(lifetime)
    assert session.shouldstop
    assert sum(n == "pool" for n, _ in target.calls) == 1


def test_observer_does_not_claim_an_unread_result():
    target = TargetBoundary()
    crc = RecordedDriver(target, 0, lambda *args: None)
    assert crc.calculation is None and crc.readback is None
    assert target.calls == []


def test_source_shape_no_hidden_test_and_small_case():
    tree = ast.parse((PACKAGE / "test_cases/crc/test_crc_p0.py").read_text())
    case = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == case_body.__name__)
    body_start = case.body[0].lineno
    lines = (PACKAGE / "test_cases/crc/test_crc_p0.py").read_text().splitlines()
    code_lines = [line for line in lines[body_start - 1:case.end_lineno]
                  if line.strip() and not line.lstrip().startswith("#")]
    assert len(code_lines) <= 20
    assert len([n for n in ast.walk(case) if isinstance(n, ast.Assert)]) == 4
    assert not any(isinstance(n, (ast.With, ast.Try)) for n in ast.walk(case))
    assert [int(c) for c in Command] == list(range(1, 22))
