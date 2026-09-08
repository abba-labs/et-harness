#!/usr/bin/env python3
# Execute the operator-selected pipeline without embedding chip-specific workflow logic.

from __future__ import annotations

import argparse
import hashlib
import locale
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any
from uuid import uuid4

import yaml
from artifact_layout import (
    capture_source_identity,
    create_current_directory,
    resolve_runs_root,
    utc_timestamp,
    write_manifest,
)
from et_test_platform.test_cases.ip_registry import IP_REGISTRY
from pipeline_profile import resolve_step_dependencies
from record_workspace import environment_lock, seal_pipeline

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPOSITORY_ROOT.parent
TOOLS_ROOT = REPOSITORY_ROOT / "tools"
RUN_IP_TESTS = TOOLS_ROOT / "runner/run_ip_tests.py"
VALIDATE_PC = TOOLS_ROOT / "validate_pc.py"
CONFIG_SCHEMA = "et-run-config/v1"
PROFILE_SCHEMA = "et-pipeline-profile/v1"
PIPELINE_STEPS = (
    "build.bootrom",
    "build.firmware",
    "deploy.bitfile",
    "deploy.bootrom",
    "deploy.firmware",
    "execute.start_target",
)


@dataclass(frozen=True, slots=True)
class PipelineContext:
    config_path: Path
    config: dict[str, Any]
    profile_path: Path
    profile: dict[str, Any]
    bench_path: Path
    output_root: Path
    environment: dict[str, str]


def _configured_python(context: PipelineContext) -> str:
    tools = _mapping(
        _mapping(context.config, "environment", field="environment"),
        "tools",
        field="environment.tools",
    )
    python = _mapping(tools, "python", field="environment.tools.python")
    value = _string(python, "executable", field="environment.tools.python.executable")
    if value == "auto":
        return sys.executable
    return str(
        _resolve_path(
            value,
            base=context.config_path.parent,
            field="environment.tools.python.executable",
            kind="file",
        )
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and execute one ET test pipeline.")
    parser.add_argument("--config", required=True, help="operator run_config.yaml path")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate configuration and local environment without running build or hardware steps",
    )
    return parser.parse_args(argv)


def _read_yaml(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise RuntimeError(f"cannot read {label} {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise RuntimeError(f"invalid YAML in {label} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} root must be a mapping: {path}")
    return payload


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# Keep committed manifests portable while the exact configuration remains in the snapshot.
def _portable_path_reference(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()
    except ValueError:
        return f"external:{path.name}"


# The runtime schema has no credentials; reject accidental secret-bearing extensions.
def _reject_sensitive_configuration(payload: object, *, field: str = "run_config") -> None:
    sensitive = {"password", "token", "secret", "api_key", "private_key", "credential"}
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in sensitive:
                raise RuntimeError(
                    f"sensitive configuration must not enter artifacts: {field}.{key}"
                )
            _reject_sensitive_configuration(value, field=f"{field}.{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _reject_sensitive_configuration(value, field=f"{field}[{index}]")


def _mapping(payload: Mapping[str, Any], key: str, *, field: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"configuration field {field!r} must be a mapping")
    return value


def _validate_keys(payload: Mapping[str, Any], allowed: set[str], *, field: str) -> None:
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise RuntimeError(f"configuration field {field!r} has unknown keys: {unexpected}")


def _sequence(payload: Mapping[str, Any], key: str, *, field: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"configuration field {field!r} must be a list")
    return value


def _boolean(payload: Mapping[str, Any], key: str, *, field: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise RuntimeError(f"configuration field {field!r} must be true or false")
    return value


def _string(payload: Mapping[str, Any], key: str, *, field: str, allow_empty: bool = False) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        suffix = "a string" if allow_empty else "a non-empty string"
        raise RuntimeError(f"configuration field {field!r} must be {suffix}")
    return value.strip()


def _resolve_path(value: str, *, base: Path, field: str, kind: str) -> Path:
    supplied = Path(value)
    path = supplied if supplied.is_absolute() else base / supplied
    path = path.resolve()
    if kind == "file" and not path.is_file():
        raise RuntimeError(f"configured file does not exist for {field!r}: {path}")
    if kind == "directory" and not path.is_dir():
        raise RuntimeError(f"configured directory does not exist for {field!r}: {path}")
    return path


def _lookup(payload: Mapping[str, Any], dotted: str) -> Any:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RuntimeError(
                f"configuration field {dotted!r} is required by the pipeline profile"
            )
        current = current[part]
    return current


def _enabled_step(pipeline: Mapping[str, Any], dotted: str) -> bool:
    current: Any = pipeline
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RuntimeError(f"pipeline field {dotted!r} is required")
        current = current[part]
    if not isinstance(current, bool):
        raise RuntimeError(f"pipeline field {dotted!r} must be true or false")
    return current


def _validate_device_entries(payload: Mapping[str, Any], section: str) -> None:
    devices = _mapping(payload, section, field=section)
    for name, raw in devices.items():
        if not str(name).replace("_", "").isalnum() or not isinstance(raw, Mapping):
            raise RuntimeError(f"{section}.{name} must be a named device mapping")
        enabled = raw.get("enabled")
        if not isinstance(enabled, bool):
            raise RuntimeError(f"{section}.{name}.enabled must be true or false")
        if not enabled:
            continue
        _string(raw, "type", field=f"{section}.{name}.type")
        connection = raw.get("connection") or raw.get("control")
        if not isinstance(connection, Mapping):
            raise RuntimeError(f"{section}.{name} needs connection or control settings")
        _string(connection, "kind", field=f"{section}.{name}.connection.kind")


def _bench_environment(config: Mapping[str, Any], config_path: Path) -> tuple[Path, dict[str, str]]:
    target = _mapping(config, "target", field="target")
    dut = _mapping(config, "dut", field="dut")
    control = _mapping(dut, "control", field="dut.control")
    expected = _mapping(dut, "expected", field="dut.expected")
    debug = _mapping(dut, "debug", field="dut.debug")
    tools = _mapping(
        _mapping(config, "environment", field="environment"),
        "tools",
        field="environment.tools",
    )
    jlink = _mapping(tools, "jlink", field="environment.tools.jlink")
    bench = _resolve_path(
        _string(target, "bench_profile", field="target.bench_profile"),
        base=config_path.parent,
        field="target.bench_profile",
        kind="file",
    )
    kind = _string(control, "kind", field="dut.control.kind")
    environment = {
        "ET_RUN_CONFIG": str(config_path),
        "ET_TARGET_KIND": _string(target, "kind", field="target.kind"),
        "ET_TARGET_LOGICAL_NAME": _string(target, "logical_name", field="target.logical_name"),
        "ET_PIPELINE_PROFILE": _string(target, "pipeline_profile", field="target.pipeline_profile"),
        "ET_BENCH_PROFILE": str(bench),
        "ET_DUT_FIRMWARE_BUILD_ID": _string(
            expected,
            "firmware_build_id",
            field="dut.expected.firmware_build_id",
            allow_empty=True,
        ),
        "ET_TOOL_JLINK_EXECUTABLE": _string(
            jlink,
            "executable",
            field="environment.tools.jlink.executable",
            allow_empty=True,
        ),
        "ET_DUT_DEBUG_PROBE_SERIAL": _string(
            debug,
            "probe_serial",
            field="dut.debug.probe_serial",
            allow_empty=True,
        ),
    }
    if kind == "serial":
        environment["ET_DUT_SERIAL_PORT"] = _string(
            control, "port", field="dut.control.port", allow_empty=True
        )
        baudrate = control.get("baudrate")
        if not isinstance(baudrate, int) or baudrate <= 0:
            raise RuntimeError("configuration field 'dut.control.baudrate' must be positive")
        environment["ET_DUT_SERIAL_BAUD"] = str(baudrate)
    environment.update(_logical_device_environment(config))
    return bench, environment


# 把启用设备的基础连接事实导出为稳定环境名，Bench仍负责把逻辑设备绑定到具体拓扑。
def _logical_device_environment(config: Mapping[str, Any]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for section, prefix in (("companions", "ET_COMPANION"), ("instruments", "ET_INSTRUMENT")):
        for name, raw in _mapping(config, section, field=section).items():
            if not raw["enabled"]:
                continue
            device_prefix = f"{prefix}_{str(name).upper()}"
            environment[f"{device_prefix}_TYPE"] = str(raw.get("type", ""))
            profile = raw.get("profile")
            if isinstance(profile, str) and profile:
                environment[f"{device_prefix}_PROFILE"] = profile
            for group_name in ("connection", "control"):
                group = raw.get(group_name)
                if not isinstance(group, Mapping):
                    continue
                for key, value in group.items():
                    if isinstance(value, (str, int, float, bool)):
                        environment[f"{device_prefix}_{str(key).upper()}"] = str(value)
            driver = raw.get("driver")
            if isinstance(driver, str) and driver:
                environment[f"{device_prefix}_DRIVER"] = driver
    return environment


def _required_bench_environment(bench: Path) -> tuple[str, ...]:
    text = bench.read_text(encoding="utf-8-sig")
    import re

    return tuple(dict.fromkeys(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", text)))


def _validate_serial_port(port: str) -> None:
    if not port:
        raise RuntimeError("dut.control.port must be filled before execute.run_tests is enabled")
    from serial.tools import list_ports

    available = {str(item.device).strip().upper() for item in list_ports.comports()}
    if port.upper() not in available:
        displayed = ", ".join(sorted(available)) if available else "none"
        raise RuntimeError(
            f"configured serial port {port!r} is absent; available ports: {displayed}"
        )


def _load_target_profile(
    config: Mapping[str, Any], config_path: Path
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    target = _mapping(config, "target", field="target")
    _validate_keys(
        target,
        {"kind", "logical_name", "pipeline_profile", "bench_profile"},
        field="target",
    )
    target_kind = _string(target, "kind", field="target.kind")
    if target_kind not in {"fpga", "silicon", "renode"}:
        raise RuntimeError("target.kind must be fpga, silicon or renode")
    profile_path = _resolve_path(
        _string(target, "pipeline_profile", field="target.pipeline_profile"),
        base=config_path.parent,
        field="target.pipeline_profile",
        kind="file",
    )
    profile = _read_yaml(profile_path, label="pipeline profile")
    if profile.get("schema") != PROFILE_SCHEMA:
        raise RuntimeError(f"pipeline profile schema must be {PROFILE_SCHEMA!r}")
    if profile.get("target_kind") != target_kind:
        raise RuntimeError("pipeline profile target_kind does not match target.kind")
    return target, profile_path, profile


def _validate_pipeline_selection(
    pipeline: Mapping[str, Any], profile: Mapping[str, Any], target_kind: str
) -> None:
    _validate_keys(
        pipeline,
        {
            "environment_check",
            "code_check",
            "confirm_hardware_actions",
            "build",
            "deploy",
            "execute",
        },
        field="pipeline",
    )
    _validate_keys(
        _mapping(pipeline, "build", field="pipeline.build"),
        {"bootrom", "firmware"},
        field="pipeline.build",
    )
    _validate_keys(
        _mapping(pipeline, "deploy", field="pipeline.deploy"),
        {"bitfile", "bootrom", "firmware"},
        field="pipeline.deploy",
    )
    _validate_keys(
        _mapping(pipeline, "execute", field="pipeline.execute"),
        {"start_target", "run_tests", "generate_report"},
        field="pipeline.execute",
    )
    for field in ("environment_check", "code_check", "confirm_hardware_actions"):
        _boolean(pipeline, field, field=f"pipeline.{field}")
    for step in PIPELINE_STEPS:
        _enabled_step(pipeline, step)
    run_tests = _enabled_step(pipeline, "execute.run_tests")
    if _enabled_step(pipeline, "execute.generate_report") and not run_tests:
        raise RuntimeError("execute.generate_report requires execute.run_tests")
    steps = _mapping(profile, "steps", field="pipeline_profile.steps")
    for step in PIPELINE_STEPS:
        if _enabled_step(pipeline, step) and step not in steps:
            raise RuntimeError(f"pipeline profile does not implement enabled step {step!r}")
    selected_steps = tuple(step for step in PIPELINE_STEPS if _enabled_step(pipeline, step))
    resolved_steps = resolve_step_dependencies(profile, selected_steps)
    missing_dependencies = [step for step in resolved_steps if step not in selected_steps]
    if missing_dependencies:
        raise RuntimeError(
            "pipeline selection is missing required step(s): " + ", ".join(missing_dependencies)
        )
    hardware_selected = run_tests or any(
        _enabled_step(pipeline, step) and bool(steps[step].get("hardware_action"))
        for step in PIPELINE_STEPS
        if step in steps
    )
    if target_kind != "renode" and hardware_selected and not pipeline["confirm_hardware_actions"]:
        raise RuntimeError("real hardware steps require pipeline.confirm_hardware_actions: true")
    constraints = profile.get("constraints", {})
    if not isinstance(constraints, Mapping):
        raise RuntimeError("pipeline_profile.constraints must be a mapping")
    groups = constraints.get("mutually_exclusive", [])
    if not isinstance(groups, list):
        raise RuntimeError("pipeline_profile.constraints.mutually_exclusive must be a list")
    for group in groups:
        if not isinstance(group, list):
            raise RuntimeError("each mutually_exclusive constraint must be a list")
        selected = [step for step in group if _enabled_step(pipeline, str(step))]
        if len(selected) > 1:
            raise RuntimeError("pipeline steps are mutually exclusive: " + ", ".join(selected))


def _validate_test_selection(test: Mapping[str, Any], *, run_tests: bool) -> None:
    _validate_keys(test, {"repeat", "stop_on_failure"}, field="test")
    if run_tests and not IP_REGISTRY:
        raise RuntimeError("Formal IP registry is empty")
    if not isinstance(test.get("repeat"), int) or test["repeat"] < 1:
        raise RuntimeError("test.repeat must be a positive integer")
    _boolean(test, "stop_on_failure", field="test.stop_on_failure")


def _validate_image_descriptors(config: Mapping[str, Any]) -> None:
    dut = _mapping(config, "dut", field="dut")
    _validate_keys(dut, {"sources", "images", "debug", "control", "expected"}, field="dut")
    sources = _mapping(dut, "sources", field="dut.sources")
    _validate_keys(sources, {"bootrom_project"}, field="dut.sources")
    images = _mapping(dut, "images", field="dut.images")
    _validate_keys(images, {"bitfile", "bootrom", "firmware"}, field="dut.images")
    for name in ("bitfile", "bootrom", "firmware"):
        descriptor = _mapping(images, name, field=f"dut.images.{name}")
        _validate_keys(descriptor, {"source", "path"}, field=f"dut.images.{name}")
        source = _string(descriptor, "source", field=f"dut.images.{name}.source")
        if source not in {"file", "build_output"}:
            raise RuntimeError(f"dut.images.{name}.source must be file or build_output")
        _string(descriptor, "path", field=f"dut.images.{name}.path", allow_empty=True)


def _load_context(config_path: Path) -> PipelineContext:
    # 统一入口只编排专用校验，避免把目标、流水线、设备和测试规则混在一个大函数内。
    config = _read_yaml(config_path, label="run configuration")
    if config.get("schema") != CONFIG_SCHEMA:
        raise RuntimeError(f"run configuration schema must be {CONFIG_SCHEMA!r}")
    _validate_keys(
        config,
        {
            "schema",
            "config",
            "target",
            "pipeline",
            "environment",
            "dut",
            "companions",
            "instruments",
            "test",
            "output",
        },
        field="root",
    )
    config_identity = _mapping(config, "config", field="config")
    _validate_keys(config_identity, {"name", "description"}, field="config")
    _string(config_identity, "name", field="config.name")
    _string(config_identity, "description", field="config.description", allow_empty=True)
    target, profile_path, profile = _load_target_profile(config, config_path)
    pipeline = _mapping(config, "pipeline", field="pipeline")
    environment = _mapping(config, "environment", field="environment")
    _validate_keys(environment, {"tools"}, field="environment")
    tools = _mapping(environment, "tools", field="environment.tools")
    _validate_keys(tools, {"python", "keil", "vivado", "jlink"}, field="environment.tools")
    python = _mapping(tools, "python", field="environment.tools.python")
    _validate_keys(python, {"executable"}, field="environment.tools.python")
    _string(python, "executable", field="environment.tools.python.executable")
    keil = _mapping(tools, "keil", field="environment.tools.keil")
    _validate_keys(keil, {"executable", "pack_root"}, field="environment.tools.keil")
    _string(keil, "executable", field="environment.tools.keil.executable", allow_empty=True)
    _string(keil, "pack_root", field="environment.tools.keil.pack_root", allow_empty=True)
    vivado = _mapping(tools, "vivado", field="environment.tools.vivado")
    _validate_keys(vivado, {"root"}, field="environment.tools.vivado")
    _string(vivado, "root", field="environment.tools.vivado.root", allow_empty=True)
    jlink = _mapping(tools, "jlink", field="environment.tools.jlink")
    _validate_keys(jlink, {"executable"}, field="environment.tools.jlink")
    _string(jlink, "executable", field="environment.tools.jlink.executable", allow_empty=True)
    _validate_image_descriptors(config)
    _validate_device_entries(config, "companions")
    _validate_device_entries(config, "instruments")
    test = _mapping(config, "test", field="test")
    _validate_pipeline_selection(pipeline, profile, str(target["kind"]))
    _validate_test_selection(test, run_tests=_enabled_step(pipeline, "execute.run_tests"))
    output = _mapping(config, "output", field="output")
    _validate_keys(output, {"root"}, field="output")
    output_value = _string(output, "root", field="output.root")
    output_root = resolve_runs_root(output_value, config_directory=config_path.parent)
    if output_root != (REPOSITORY_ROOT / "artifacts/runs").resolve():
        raise ValueError("Formal output.root must be auto or canonical artifacts/runs root")
    bench_path, bench_environment = _bench_environment(config, config_path)
    return PipelineContext(
        config_path, config, profile_path, profile, bench_path, output_root, bench_environment
    )


def _argument_value(context: PipelineContext, item: Mapping[str, Any]) -> str:
    if "from" in item:
        dotted = str(item["from"])
        raw = _lookup(context.config, dotted)
        if raw is None or str(raw).strip() == "":
            raise RuntimeError(f"configuration field {dotted!r} is required by an enabled step")
        value = str(raw)
        field = dotted
    elif "value" in item:
        value = str(item["value"])
        field = "pipeline profile literal"
    else:
        raise RuntimeError("pipeline profile argument needs 'from' or 'value'")

    kind = str(item.get("kind", "string"))
    if kind in {"file", "directory"}:
        base_name = str(item.get("base", "config"))
        bases = {
            "config": context.config_path.parent,
            "repository": REPOSITORY_ROOT,
            "project": PROJECT_ROOT,
        }
        if base_name not in bases:
            raise RuntimeError(f"unsupported pipeline profile path base: {base_name!r}")
        return str(_resolve_path(value, base=bases[base_name], field=field, kind=kind))
    if kind != "string":
        raise RuntimeError(f"unsupported pipeline profile argument kind: {kind!r}")
    return value


def _action_command(context: PipelineContext, step: str) -> list[str]:
    steps = _mapping(context.profile, "steps", field="pipeline_profile.steps")
    action = steps.get(step)
    if not isinstance(action, Mapping):
        raise RuntimeError(f"pipeline profile step {step!r} must be a mapping")
    script = _resolve_path(
        _string(action, "script", field=f"pipeline_profile.steps.{step}.script"),
        base=REPOSITORY_ROOT,
        field=f"pipeline_profile.steps.{step}.script",
        kind="file",
    )
    try:
        script.relative_to(TOOLS_ROOT)
    except ValueError as exc:
        raise RuntimeError("pipeline profile scripts must stay inside repository tools/") from exc
    if script.suffix.lower() != ".ps1":
        raise RuntimeError("pipeline profile currently accepts PowerShell scripts only")
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if powershell is None:
        raise RuntimeError(f"PowerShell is required by enabled step {step!r}")
    command = [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    arguments = action.get("arguments", [])
    if not isinstance(arguments, list):
        raise RuntimeError(f"pipeline profile step {step!r} arguments must be a list")
    for item in arguments:
        if not isinstance(item, Mapping):
            raise RuntimeError(f"pipeline profile step {step!r} contains an invalid argument")
        if "flag" in item:
            command.append(str(item["flag"]))
            continue
        option = item.get("option")
        if not isinstance(option, str) or not option:
            raise RuntimeError(f"pipeline profile step {step!r} argument needs an option")
        try:
            value = _argument_value(context, item)
        except RuntimeError:
            if item.get("optional") is True:
                continue
            raise
        command.extend((option, value))
    return command


def _validate_configured_devices(context: PipelineContext) -> None:
    for section in ("companions", "instruments"):
        devices = _mapping(context.config, section, field=section)
        for name, raw in devices.items():
            if not raw["enabled"]:
                continue
            connection = raw.get("connection") or raw.get("control")
            kind = str(connection["kind"])
            if kind == "serial":
                port = _string(
                    connection,
                    "port",
                    field=f"{section}.{name}.connection.port",
                    allow_empty=True,
                )
                _validate_serial_port(port)
            elif kind == "visa":
                _string(connection, "resource", field=f"{section}.{name}.connection.resource")
            elif kind in {"xilinx_jtag", "jtag", "tcpip", "usb"}:
                continue
            else:
                raise RuntimeError(f"unsupported connection kind for {section}.{name}: {kind!r}")


def _validate_environment(context: PipelineContext) -> None:
    pipeline = _mapping(context.config, "pipeline", field="pipeline")
    tools = _mapping(
        _mapping(context.config, "environment", field="environment"),
        "tools",
        field="environment.tools",
    )
    python = _mapping(tools, "python", field="environment.tools.python")
    python_executable = _string(
        python,
        "executable",
        field="environment.tools.python.executable",
    )
    if python_executable != "auto":
        _resolve_path(
            python_executable,
            base=context.config_path.parent,
            field="environment.tools.python.executable",
            kind="file",
        )
    for step in PIPELINE_STEPS:
        if _enabled_step(pipeline, step):
            _action_command(context, step)

    if _enabled_step(pipeline, "execute.run_tests"):
        missing = [
            name
            for name in _required_bench_environment(context.bench_path)
            if not context.environment.get(name, os.environ.get(name, "")).strip()
        ]
        if missing:
            raise RuntimeError(
                "DUT configuration does not satisfy Bench values: " + ", ".join(missing)
            )
        _validate_serial_port(context.environment.get("ET_DUT_SERIAL_PORT", ""))
        _validate_configured_devices(context)
    print("Environment check: ready")


# 为Windows PowerShell子进程提供自身的标准模块目录，避免继承PowerShell 7或Agent运行时模块。
def _windows_powershell_module_path(environment: Mapping[str, str]) -> str:
    user_profile = environment.get("USERPROFILE", "").strip()
    program_files = environment.get("PROGRAMFILES", "").strip()
    windows_root = environment.get("WINDIR", "").strip()
    if not user_profile or not program_files or not windows_root:
        raise RuntimeError("Windows PowerShell environment roots are incomplete")
    return os.pathsep.join(
        (
            str(PureWindowsPath(user_profile, "Documents", "WindowsPowerShell", "Modules")),
            str(PureWindowsPath(program_files, "WindowsPowerShell", "Modules")),
            str(PureWindowsPath(windows_root, "System32", "WindowsPowerShell", "v1.0", "Modules")),
        )
    )


# 选择子进程输出解码；Python遵循显式编码，厂商工具继续使用系统本地代码页。
def _child_output_encoding(
    command: Sequence[str],
    environment: Mapping[str, str],
) -> str:
    executable = Path(command[0]).name.lower()
    is_python = executable.startswith("python") or executable in {"py", "py.exe"}
    python_encoding = environment.get("PYTHONIOENCODING", "").partition(":")[0].strip()

    if is_python and python_encoding:
        return python_encoding

    return locale.getpreferredencoding(False)


def _run(
    command: Sequence[str],
    *,
    environment: Mapping[str, str],
    log_path: Path | None = None,
) -> int:
    process_environment = dict(os.environ)
    process_environment.update(environment)
    process_environment.setdefault("PYTHONUNBUFFERED", "1")
    executable = Path(command[0]).name.lower()
    if os.name == "nt" and executable in {"powershell", "powershell.exe"}:
        process_environment["PSModulePath"] = _windows_powershell_module_path(process_environment)
    if log_path is None:
        completed = subprocess.run(
            list(command),
            cwd=REPOSITORY_ROOT,
            env=process_environment,
            check=False,
        )
        return int(completed.returncode)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="") as stream:
        stream.write("\n$ " + subprocess.list2cmdline(list(command)) + "\n")
        stream.flush()
        process = subprocess.Popen(
            list(command),
            cwd=REPOSITORY_ROOT,
            env=process_environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=_child_output_encoding(command, process_environment),
            errors="replace",
            bufsize=1,
        )
        if process.stdout is None:
            raise RuntimeError("pipeline child process did not expose stdout")
        for line in process.stdout:
            print(line, end="")
            stream.write(line)
            stream.flush()
        return int(process.wait())


# 单机文件锁替代开发环境专用资源脚本；进程退出时操作系统自动释放锁。
def _pipeline_lock() -> AbstractContextManager[None]:
    return environment_lock(REPOSITORY_ROOT)


def _test_command(
    context: PipelineContext,
    ip: str,
    *,
    run_dir: Path,
    iteration: int,
    repeat_count: int = 1,
    source_revision: str = "unavailable",
    source_dirty: bool = False,
) -> list[str]:
    if repeat_count <= 0 or iteration <= 0 or iteration > repeat_count:
        raise ValueError("test iteration must be inside the configured repeat count")
    output_root = run_dir / "tests" / ip
    command = [
        _configured_python(context),
        str(RUN_IP_TESTS),
        "--ip",
        ip,
        "--bench",
        str(context.bench_path),
        "--target",
        _string(
            _mapping(context.config, "target", field="target"),
            "logical_name",
            field="target.logical_name",
        ),
        "--output-root",
        str(output_root),
        "--within-pipeline",
        "--lane",
        {"renode": "sil", "fpga": "fpga", "silicon": "hil"}[context.config["target"]["kind"]],
        "--manifest",
        str(run_dir / "manifest.json"),
        "--source-revision",
        source_revision,
        "--source-state",
        "dirty" if source_dirty else "clean",
    ]
    if not _enabled_step(
        _mapping(context.config, "pipeline", field="pipeline"), "execute.generate_report"
    ):
        command.append("--no-report")
    return command


def _seal_completed_pipeline(run_dir: Path, manifest: dict[str, object], *, exit_code: int) -> None:
    try:
        seal_pipeline(REPOSITORY_ROOT, run_dir, successful=exit_code == 0)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Workspace retained without reuse permission: {exc}")
        if exit_code == 0:
            manifest.update({"status": "FAIL", "exit_code": 2})
            write_manifest(run_dir, manifest)
            raise RuntimeError("pipeline publication is incomplete") from exc


def _execute(context: PipelineContext, *, check_only: bool) -> int:
    pipeline = _mapping(context.config, "pipeline", field="pipeline")
    identity = _mapping(context.config, "config", field="config")
    print(f"Run configuration: {identity['name']} - {identity['description']}")
    if check_only or pipeline["environment_check"]:
        _validate_environment(context)
    else:
        print("Environment check: skipped by configuration")
    if check_only:
        print("Pipeline check-only: PASS")
        return 0

    source_revision, source_dirty = capture_source_identity(REPOSITORY_ROOT)
    _reject_sensitive_configuration(context.config)
    run_dir = create_current_directory(REPOSITORY_ROOT, context.output_root)
    config_dir = run_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=False)
    config_snapshot = config_dir / "run_config.snapshot.yaml"
    config_snapshot.write_bytes(context.config_path.read_bytes())
    manifest = {
        "schema": "et-artifact-run/v1",
        "run_id": str(uuid4()),
        "configuration": _portable_path_reference(context.config_path),
        "configuration_sha256": _file_sha256(context.config_path),
        "configuration_snapshot": config_snapshot.relative_to(run_dir).as_posix(),
        "source_revision": source_revision,
        "source_dirty": source_dirty,
        "target_kind": context.config["target"]["kind"],
        "started_at": utc_timestamp(),
        "finished_at": None,
        "status": "RUNNING",
    }
    write_manifest(run_dir, manifest)
    context.environment["ET_ARTIFACT_RUN_DIR"] = str(run_dir)
    print(f"Artifact run: {run_dir}")
    pipeline_log = run_dir / "stages" / "pipeline" / "pipeline.log"

    exit_code = 2
    run_status = "FAIL"
    try:
        if pipeline["code_check"]:
            print("Running canonical software quality gate ...")
            exit_code = _run(
                [_configured_python(context), str(VALIDATE_PC)],
                environment=context.environment,
                log_path=pipeline_log,
            )
            if exit_code != 0:
                return exit_code

        for step in PIPELINE_STEPS:
            if not _enabled_step(pipeline, step):
                continue
            print(f"Running pipeline step: {step}")
            exit_code = _run(
                _action_command(context, step),
                environment=context.environment,
                log_path=pipeline_log,
            )
            if exit_code != 0:
                return exit_code

        if _enabled_step(pipeline, "execute.run_tests"):
            test = _mapping(context.config, "test", field="test")
            test_exit = 0
            for iteration in range(1, int(test["repeat"]) + 1):
                for registration in IP_REGISTRY:
                    ip = registration.ip_id
                    print(f"Running Formal IP tests: {ip} (round {iteration}/{test['repeat']})")
                    exit_code = _run(
                        _test_command(
                            context,
                            ip,
                            run_dir=run_dir,
                            iteration=iteration,
                            repeat_count=int(test["repeat"]),
                            source_revision=source_revision,
                            source_dirty=source_dirty,
                        ),
                        environment=context.environment,
                        log_path=pipeline_log,
                    )
                    if exit_code != 0:
                        test_exit = test_exit or exit_code
                        if test["stop_on_failure"]:
                            return exit_code
            if test_exit != 0:
                exit_code = test_exit
                return exit_code
        print("Configured pipeline: PASS")
        exit_code = 0
        run_status = "PASS"
        return 0
    finally:
        manifest["status"] = run_status
        manifest["exit_code"] = exit_code
        manifest["finished_at"] = utc_timestamp()
        write_manifest(run_dir, manifest)
        _seal_completed_pipeline(run_dir, manifest, exit_code=exit_code)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        context = _load_context(Path(args.config).resolve())
        with _pipeline_lock():
            return _execute(context, check_only=bool(args.check_only))
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
