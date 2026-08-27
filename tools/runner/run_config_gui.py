#!/usr/bin/env python3
# 职责：用轻量级Tkinter界面编辑唯一的run_config.yaml，并复用正式Pipeline执行器。
# 边界：不管理IP/Case注册表，不实现编译、烧录、测试或报告业务逻辑。

from __future__ import annotations

import argparse
import copy
import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pipeline_profile import resolve_step_dependencies

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPOSITORY_ROOT / "run_config.yaml"
CONFIG_TEMPLATE = REPOSITORY_ROOT / "run_config.example.yaml"
GUI_SCHEMA = REPOSITORY_ROOT / "tools/runner/run_config_gui_schema.yaml"
PIPELINE_RUNNER = REPOSITORY_ROOT / "tools/runner/run_pipeline.py"
GUI_SCHEMA_ID = "et-run-config-gui/v1"
LOG_BATCH_INTERVAL_MS = 80
LOG_MAX_BATCH_ITEMS = 200
PIPELINE_STAGE_GROUPS = ("build", "deploy", "execute")
GENERIC_PIPELINE_STEPS = {"execute.run_tests", "execute.generate_report"}
REQUIRED_LABEL_COLOR = "#c00000"
NORMAL_LABEL_COLOR = "#202020"

# Bench中的稳定环境名映射到Run Config字段；设备环境名在运行时按配置结构生成。
BENCH_ENVIRONMENT_FIELDS = {
    "ET_TARGET_KIND": "target.kind",
    "ET_TARGET_LOGICAL_NAME": "target.logical_name",
    "ET_PIPELINE_PROFILE": "target.pipeline_profile",
    "ET_BENCH_PROFILE": "target.bench_profile",
    "ET_DUT_FIRMWARE_BUILD_ID": "dut.expected.firmware_build_id",
    "ET_DUT_SERIAL_PORT": "dut.control.port",
    "ET_DUT_SERIAL_BAUD": "dut.control.baudrate",
    "ET_TOOL_JLINK_EXECUTABLE": "environment.tools.jlink.executable",
    "ET_DUT_DEBUG_PROBE_SERIAL": "dut.debug.probe_serial",
}

# 图形组件延迟赋值，导入纯配置函数时不要求CI系统安装Tk。
tk: Any = None
ttk: Any = None
filedialog: Any = None
messagebox: Any = None


# 解析GUI入口参数；smoke-test只实例化窗口，不执行任何Pipeline或硬件动作。
def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edit and run the ET operator configuration.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="operator YAML configuration")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="create and destroy the GUI without showing it",
    )
    return parser.parse_args(argv)


# YAML读取集中在一个边界，避免GUI静默接受损坏或非Mapping配置。
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


# GUI元数据只定义字段展示方式，不复制run_pipeline.py中的配置合法性规则。
def _load_gui_schema(path: Path = GUI_SCHEMA) -> dict[str, Any]:
    payload = _read_yaml(path, label="GUI schema")
    if payload.get("schema") != GUI_SCHEMA_ID:
        raise RuntimeError(f"GUI schema must be {GUI_SCHEMA_ID!r}")
    tabs = payload.get("tabs")
    if not isinstance(tabs, list) or not tabs:
        raise RuntimeError("GUI schema tabs must be a non-empty list")
    _quick_actions(payload)
    return payload


# 快捷动作只能选择现有Pipeline布尔阶段，不能携带命令、脚本或任意参数。
def _quick_actions(schema: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    raw_actions = schema.get("quick_actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise RuntimeError("GUI schema quick_actions must be a non-empty list")

    actions: list[dict[str, Any]] = []
    identifiers: set[str] = set()
    for raw in raw_actions:
        if not isinstance(raw, Mapping):
            raise RuntimeError("each GUI quick action must be a mapping")
        identifier = str(raw.get("id", "")).strip()
        label = str(raw.get("label", "")).strip()
        check_only = raw.get("check_only")
        selections = raw.get("select")
        preserve_selection = raw.get("preserve_selection", False)
        if not identifier or not label or identifier in identifiers:
            raise RuntimeError("GUI quick action id and label must be non-empty and unique")
        if not isinstance(check_only, bool) or not isinstance(preserve_selection, bool):
            raise RuntimeError(f"GUI quick action {identifier!r} has invalid boolean metadata")
        if not isinstance(selections, list) or not all(
            isinstance(item, str)
            and item.count(".") == 1
            and item.split(".", 1)[0] in PIPELINE_STAGE_GROUPS
            for item in selections
        ):
            raise RuntimeError(f"GUI quick action {identifier!r} has invalid Pipeline selections")
        if check_only and selections:
            raise RuntimeError(f"check-only GUI quick action {identifier!r} cannot select stages")
        identifiers.add(identifier)
        actions.append(
            {
                "id": identifier,
                "label": label,
                "check_only": check_only,
                "select": tuple(selections),
                "preserve_selection": preserve_selection,
            }
        )
    return tuple(actions)


def _get_dotted(payload: Mapping[str, Any], dotted: str) -> Any:
    current: Any = payload
    for segment in dotted.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            raise RuntimeError(f"configuration field is missing: {dotted}")
        current = current[segment]
    return current


def _set_dotted(payload: dict[str, Any], dotted: str, value: Any) -> None:
    segments = dotted.split(".")
    current: dict[str, Any] = payload
    for segment in segments[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            raise RuntimeError(f"configuration field is not a mapping: {dotted}")
        current = child
    current[segments[-1]] = value


def _config_relative_path(value: object, *, config_path: Path) -> Path:
    supplied = Path(str(value).strip())
    return (supplied if supplied.is_absolute() else config_path.parent / supplied).resolve()


# 当前Profile是动作可用性和动态必填字段的唯一来源，GUI不保存芯片动作表。
def _selected_profile(payload: Mapping[str, Any], *, config_path: Path) -> dict[str, Any]:
    profile_path = _config_relative_path(
        _get_dotted(payload, "target.pipeline_profile"), config_path=config_path
    )
    profile = _read_yaml(profile_path, label="pipeline profile")
    steps = profile.get("steps")
    if not isinstance(steps, Mapping):
        raise RuntimeError(f"pipeline profile steps must be a mapping: {profile_path}")
    return profile


def _selected_pipeline_steps(payload: Mapping[str, Any]) -> tuple[str, ...]:
    pipeline = _get_dotted(payload, "pipeline")
    if not isinstance(pipeline, Mapping):
        raise RuntimeError("configuration field pipeline must be a mapping")

    selected: list[str] = []
    for group_name in PIPELINE_STAGE_GROUPS:
        group = pipeline.get(group_name)
        if not isinstance(group, Mapping):
            raise RuntimeError(f"configuration field pipeline.{group_name} must be a mapping")
        selected.extend(
            f"{group_name}.{name}" for name, enabled in group.items() if enabled is True
        )
    return tuple(selected)


def _profile_steps(profile: Mapping[str, Any]) -> Mapping[str, Any]:
    steps = profile.get("steps")
    if not isinstance(steps, Mapping):
        raise RuntimeError("pipeline profile steps must be a mapping")
    return steps


# 通用测试/报告由Runner实现；构建和部署动作必须由当前Profile显式实现。
def _quick_action_supported(action: Mapping[str, Any], profile: Mapping[str, Any]) -> bool:
    implemented = set(_profile_steps(profile)) | GENERIC_PIPELINE_STEPS
    try:
        resolved = resolve_step_dependencies(profile, action["select"])
    except RuntimeError:
        return False
    return all(step in implemented for step in resolved)


def _selection_requires_code_check(payload: Mapping[str, Any], profile: Mapping[str, Any]) -> bool:
    if str(_get_dotted(payload, "target.kind")) == "renode":
        return False
    selected = set(_selected_pipeline_steps(payload))
    if "execute.run_tests" in selected:
        return True
    steps = _profile_steps(profile)
    return any(
        step in steps
        and isinstance(steps[step], Mapping)
        and bool(steps[step].get("hardware_action"))
        for step in selected
    )


# 单项动作只改Pipeline选择，不绕过唯一配置、Runner、Profile或硬件确认门禁。
def _apply_quick_action_preset(
    payload: Mapping[str, Any], action: Mapping[str, Any], profile: Mapping[str, Any]
) -> dict[str, Any]:
    updated = copy.deepcopy(dict(payload))
    if not _quick_action_supported(action, profile):
        raise RuntimeError(f"当前Pipeline Profile不支持“{action['label']}”")

    pipeline = _get_dotted(updated, "pipeline")
    if not isinstance(pipeline, dict):
        raise RuntimeError("configuration field pipeline must be a mapping")
    if not bool(action["preserve_selection"]):
        for group_name in PIPELINE_STAGE_GROUPS:
            group = pipeline.get(group_name)
            if not isinstance(group, dict):
                raise RuntimeError(f"configuration field pipeline.{group_name} must be a mapping")
            for field in group:
                group[field] = False
        pipeline["code_check"] = False
        for step in resolve_step_dependencies(profile, action["select"]):
            _set_dotted(updated, f"pipeline.{step}", True)

    pipeline["environment_check"] = True
    if _selection_requires_code_check(updated, profile):
        pipeline["code_check"] = True
    return updated


def _schema_required_fields(schema: Mapping[str, Any]) -> set[str]:
    return {
        str(field["path"])
        for tab in schema["tabs"]
        for group in tab.get("groups", [])
        for field in group.get("fields", [])
        if field.get("required") is True
    }


# 根据设备配置生成与Runner一致的环境名来源，供Bench占位符反查GUI字段。
def _environment_config_fields(payload: Mapping[str, Any]) -> dict[str, str]:
    fields = dict(BENCH_ENVIRONMENT_FIELDS)
    for section, prefix in (("companions", "ET_COMPANION"), ("instruments", "ET_INSTRUMENT")):
        devices = _get_dotted(payload, section)
        if not isinstance(devices, Mapping):
            continue
        for name, raw in devices.items():
            if not isinstance(raw, Mapping):
                continue
            device_prefix = f"{prefix}_{str(name).upper()}"
            if "profile" in raw:
                fields[f"{device_prefix}_PROFILE"] = f"{section}.{name}.profile"
            if "driver" in raw:
                fields[f"{device_prefix}_DRIVER"] = f"{section}.{name}.driver"
            for group_name in ("connection", "control"):
                group = raw.get(group_name)
                if not isinstance(group, Mapping):
                    continue
                for key in group:
                    fields[f"{device_prefix}_{str(key).upper()}"] = (
                        f"{section}.{name}.{group_name}.{key}"
                    )
    return fields


def _bench_required_fields(payload: Mapping[str, Any], *, config_path: Path) -> set[str]:
    bench_path = _config_relative_path(
        _get_dotted(payload, "target.bench_profile"), config_path=config_path
    )
    try:
        text = bench_path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise RuntimeError(f"cannot read Bench Profile {bench_path}: {exc}") from exc
    required_environment = tuple(dict.fromkeys(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)\}", text)))
    field_map = _environment_config_fields(payload)
    return {field_map[name] for name in required_environment if name in field_map}


def _enabled_device_required_fields(payload: Mapping[str, Any]) -> set[str]:
    required: set[str] = set()
    for section in ("companions", "instruments"):
        devices = _get_dotted(payload, section)
        if not isinstance(devices, Mapping):
            continue
        for name, raw in devices.items():
            if not isinstance(raw, Mapping) or raw.get("enabled") is not True:
                continue
            connection = raw.get("connection") or raw.get("control")
            if not isinstance(connection, Mapping):
                continue
            group_name = "connection" if isinstance(raw.get("connection"), Mapping) else "control"
            required.add(f"{section}.{name}.{group_name}.kind")
            kind = str(connection.get("kind", ""))
            if kind == "serial":
                required.add(f"{section}.{name}.{group_name}.port")
            elif kind == "visa":
                required.add(f"{section}.{name}.{group_name}.resource")
    return required


# 必填项由基础Schema、当前启用Profile阶段、Bench和启用设备共同确定。
def _required_config_fields(
    payload: Mapping[str, Any], schema: Mapping[str, Any], *, config_path: Path
) -> set[str]:
    required = _schema_required_fields(schema)
    profile = _selected_profile(payload, config_path=config_path)
    steps = _profile_steps(profile)
    for step in _selected_pipeline_steps(payload):
        action = steps.get(step)
        if not isinstance(action, Mapping):
            continue
        arguments = action.get("arguments", [])
        if not isinstance(arguments, list):
            raise RuntimeError(f"pipeline profile arguments for {step!r} must be a list")
        required.update(
            str(argument["from"])
            for argument in arguments
            if isinstance(argument, Mapping)
            and "from" in argument
            and argument.get("optional") is not True
        )
    if "execute.run_tests" in _selected_pipeline_steps(payload):
        required.update(_bench_required_fields(payload, config_path=config_path))
    if str(_get_dotted(payload, "dut.control.kind")) == "serial":
        required.add("dut.control.baudrate")
    required.update(_enabled_device_required_fields(payload))
    return required


def _missing_required_fields(payload: Mapping[str, Any], required: set[str]) -> list[str]:
    missing: list[str] = []
    for path in sorted(required):
        try:
            value = _get_dotted(payload, path)
        except RuntimeError:
            missing.append(path)
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(path)
    return missing


# 采用同目录临时文件原子替换，避免异常退出留下半写YAML。
def _write_yaml_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# 本地运行配置，由run_config_gui.bat维护；完整字段说明见run_config.example.yaml。\n"
        + yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True)
    )
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(temporary_name)
        raise


def _repository_relative(path: Path) -> str:
    return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()


# Profile选项从受控目录发现，GUI不硬编码芯片或板卡名称。
def _pipeline_profile_choices() -> list[str]:
    root = REPOSITORY_ROOT / "tools/profiles/pipeline"
    return [_repository_relative(path) for path in sorted(root.glob("*.yaml"))]


def _bench_profile_choices() -> list[str]:
    root = REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies"
    return [_repository_relative(path) for path in sorted(root.glob("*.yaml"))]


def _serial_port_choices(current: str = "") -> list[str]:
    from serial.tools import list_ports

    ports = sorted({str(item.device) for item in list_ports.comports()})
    if current and current not in ports:
        ports.insert(0, current)
    return ports


# GUI本身不判断字段是否合法；检查命令始终调用唯一正式Pipeline校验入口。
def _pipeline_command(config: Path, *, check_only: bool) -> list[str]:
    command = [sys.executable, str(PIPELINE_RUNNER), "--config", str(config)]
    if check_only:
        command.append("--check-only")
    return command


# 用于二次人工提示；最终硬件门禁仍由run_pipeline.py强制执行。
def _hardware_actions_selected(payload: Mapping[str, Any]) -> bool:
    target_kind = str(_get_dotted(payload, "target.kind"))
    if target_kind == "renode":
        return False
    fields = (
        "pipeline.deploy.bitfile",
        "pipeline.deploy.bootrom",
        "pipeline.deploy.firmware",
        "pipeline.execute.start_target",
        "pipeline.execute.run_tests",
    )
    return any(bool(_get_dotted(payload, field)) for field in fields)


# Tkinter界面类只负责展示、收集和调用正式Pipeline。
class RunConfigGui:
    # 构造配置编辑器；字段布局完全来自GUI Schema。
    def __init__(self, root: Any, config_path: Path) -> None:
        self.root = root
        self.config_path = config_path
        self.schema = _load_gui_schema()
        self.payload = _read_yaml(config_path, label="run configuration")
        self.variables: dict[str, tk.Variable] = {}
        self.field_types: dict[str, str] = {}
        self.field_labels: dict[str, Any] = {}
        self.field_label_text: dict[str, str] = {}
        self.quick_buttons: dict[str, Any] = {}
        self.operation_buttons: list[Any] = []
        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str | None] = queue.Queue()
        self._pending_log: list[str] = []
        self._refresh_after_id: str | None = None
        self._running = False

        root.title("ET 自动化测试平台 - 运行配置")
        root.geometry("1120x840")
        root.minsize(900, 650)
        self._build_layout()
        self._load_values()
        for variable in self.variables.values():
            variable.trace_add("write", self._schedule_dynamic_refresh)
        self._refresh_dynamic_state()

    # 顶部只展示当前配置文件；测试范围由注册表管理，不在此处重复展示或选择。
    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(12, 10, 12, 4))
        header.pack(fill="x")
        ttk.Label(
            header, text="ET 自动化测试运行配置", font=("Microsoft YaHei UI", 14, "bold")
        ).pack(side="left")
        ttk.Label(header, text="红色 * 为当前动作必填项", foreground=REQUIRED_LABEL_COLOR).pack(
            side="left", padx=18
        )
        ttk.Label(header, text=str(self.config_path), foreground="#555555").pack(side="right")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(4, 8))
        for tab in self.schema["tabs"]:
            self._add_tab(tab)

        log_frame = ttk.LabelFrame(self.root, text="运行输出", padding=6)
        log_frame.pack(fill="both", padx=12, pady=(0, 8))
        self.log = tk.Text(log_frame, height=9, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        quick_actions = ttk.LabelFrame(self.root, text="独立执行", padding=(10, 7))
        quick_actions.pack(fill="x", padx=12, pady=(0, 8))
        for action in _quick_actions(self.schema):
            button = ttk.Button(
                quick_actions,
                text=str(action["label"]),
                command=lambda action=action: self._quick_action_clicked(action),
            )
            button.pack(side="left", padx=(0, 8))
            self.quick_buttons[str(action["id"])] = button
            self.operation_buttons.append(button)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        actions.pack(fill="x")
        save_button = ttk.Button(actions, text="保存配置", command=self._save_clicked)
        save_button.pack(side="left")
        self.operation_buttons.append(save_button)
        self.run_button = ttk.Button(actions, text="开始完整流水线", command=self._run_clicked)
        self.run_button.pack(side="left", padx=8)
        self.operation_buttons.append(self.run_button)
        clear_button = ttk.Button(actions, text="清空日志", command=self._clear_log)
        clear_button.pack(side="left")
        self.operation_buttons.append(clear_button)
        ttk.Button(actions, text="退出", command=self._close).pack(side="right")
        self.status = tk.StringVar(value="就绪")
        ttk.Label(actions, textvariable=self.status).pack(side="right", padx=16)

    # 每个页签使用可滚动画布，避免增加字段后迫使用户调整窗口尺寸。
    def _add_tab(self, tab: Mapping[str, Any]) -> None:
        container = ttk.Frame(self.notebook)
        self.notebook.add(container, text=str(tab["label"]))
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        body = ttk.Frame(canvas, padding=10)
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        body.bind(
            "<Configure>",
            lambda _event, canvas=canvas: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event, canvas=canvas, window=window: canvas.itemconfigure(
                window, width=event.width
            ),
        )
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        for group in tab.get("groups", []):
            frame = ttk.LabelFrame(body, text=str(group["label"]), padding=10)
            frame.pack(fill="x", pady=(0, 10))
            for field in group.get("fields", []):
                self._add_field(frame, field)

    def _add_field(self, parent: ttk.Frame, field: Mapping[str, Any]) -> None:
        path = str(field["path"])
        field_type = str(field["type"])
        self.field_types[path] = field_type
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        label_text = str(field["label"])
        label = ttk.Label(row, text=label_text, width=28, anchor="w")
        label.pack(side="left")
        self.field_labels[path] = label
        self.field_label_text[path] = label_text

        if field_type == "bool":
            variable: tk.Variable = tk.BooleanVar()
            ttk.Checkbutton(row, variable=variable).pack(side="left")
        else:
            variable = tk.StringVar()
            if field_type == "choice":
                widget = ttk.Combobox(
                    row,
                    textvariable=variable,
                    values=[str(item) for item in field.get("choices", [])],
                    state="readonly",
                )
            elif field_type == "pipeline_profile":
                widget = ttk.Combobox(
                    row, textvariable=variable, values=_pipeline_profile_choices(), state="readonly"
                )
            elif field_type == "bench_profile":
                widget = ttk.Combobox(
                    row, textvariable=variable, values=_bench_profile_choices(), state="readonly"
                )
            elif field_type == "serial":
                widget = ttk.Combobox(row, textvariable=variable, values=_serial_port_choices())
            else:
                widget = ttk.Entry(row, textvariable=variable)
            widget.pack(side="left", fill="x", expand=True)
            if field_type in {"file", "directory", "directory_or_auto"}:
                ttk.Button(
                    row,
                    text="浏览...",
                    command=lambda path=path, field_type=field_type: self._browse(path, field_type),
                ).pack(side="left", padx=(8, 0))
            if field_type == "serial":
                ttk.Button(
                    row, text="刷新", command=lambda path=path: self._refresh_serial(path)
                ).pack(side="left", padx=(8, 0))
        self.variables[path] = variable

    def _load_values(self) -> None:
        for path, variable in self.variables.items():
            value = _get_dotted(self.payload, path)
            variable.set(value)

    # 高频输入只安排一次空闲刷新，避免每个按键都重复读取Profile造成界面卡顿。
    def _schedule_dynamic_refresh(self, *_args: object) -> None:
        if self._refresh_after_id is None:
            self._refresh_after_id = self.root.after(60, self._refresh_dynamic_state)

    def _preview_payload(self) -> dict[str, Any]:
        preview = copy.deepcopy(self.payload)
        for path, variable in self.variables.items():
            value: Any = variable.get()
            if self.field_types[path] == "bool":
                value = bool(value)
            elif self.field_types[path] == "integer":
                try:
                    value = int(str(value).strip())
                except ValueError:
                    value = str(value).strip()
            else:
                value = str(value).strip()
            _set_dotted(preview, path, value)
        return preview

    # 动态刷新只改变必填提示和动作可用性，不替代正式Runner校验。
    def _refresh_dynamic_state(self) -> None:
        self._refresh_after_id = None
        preview = self._preview_payload()
        profile: dict[str, Any] | None = None
        profile_error: str | None = None
        try:
            profile = _selected_profile(preview, config_path=self.config_path)
            required = _required_config_fields(preview, self.schema, config_path=self.config_path)
        except (OSError, RuntimeError, ValueError) as exc:
            required = _schema_required_fields(self.schema)
            profile_error = str(exc)

        for path, label in self.field_labels.items():
            is_required = path in required
            suffix = " *" if is_required else ""
            label.configure(
                text=self.field_label_text[path] + suffix,
                foreground=REQUIRED_LABEL_COLOR if is_required else NORMAL_LABEL_COLOR,
            )

        for action in _quick_actions(self.schema):
            supported = profile is not None and _quick_action_supported(action, profile)
            state = "normal" if supported and not self._running else "disabled"
            self.quick_buttons[str(action["id"])].configure(state=state)
        if profile_error and not self._running:
            self.status.set("Profile待完善：" + profile_error)

    def _browse(self, path: str, field_type: str) -> None:
        current = str(self.variables[path].get())
        initial = current if current and current != "auto" else str(REPOSITORY_ROOT)
        if field_type == "file":
            selected = filedialog.askopenfilename(initialdir=str(Path(initial).parent))
        else:
            selected = filedialog.askdirectory(initialdir=initial)
        if selected:
            selected_path = Path(selected).resolve()
            try:
                value = _repository_relative(selected_path)
            except ValueError:
                value = str(selected_path)
            self.variables[path].set(value)

    def _refresh_serial(self, path: str) -> None:
        current = str(self.variables[path].get())
        values = _serial_port_choices(current)
        for tab_id in self.notebook.tabs():
            tab = self.root.nametowidget(tab_id)
            for widget in self._walk_widgets(tab):
                if isinstance(widget, ttk.Combobox) and str(widget.cget("textvariable")) == str(
                    self.variables[path]
                ):
                    widget.configure(values=values)
        self.status.set(f"已发现 {len(values)} 个串口")

    def _walk_widgets(self, parent: tk.Misc):
        for child in parent.winfo_children():
            yield child
            yield from self._walk_widgets(child)

    # 收集时只做GUI类型转换；完整字段、依赖和Profile检查交给Pipeline。
    def _collect_payload(self) -> dict[str, Any]:
        for path, variable in self.variables.items():
            field_type = self.field_types[path]
            value: Any = variable.get()
            if field_type == "integer":
                try:
                    value = int(str(value).strip())
                except ValueError as exc:
                    raise RuntimeError(f"字段 {path} 必须是整数") from exc
            elif field_type == "bool":
                value = bool(value)
            else:
                value = str(value).strip()
            _set_dotted(self.payload, path, value)
        return self.payload

    def _save(self) -> bool:
        try:
            payload = self._collect_payload()
            _write_yaml_atomic(self.config_path, payload)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.root)
            return False
        self.status.set("配置已保存")
        return True

    def _save_clicked(self) -> None:
        if self._save():
            messagebox.showinfo("保存配置", "run_config.yaml 已安全保存。", parent=self.root)

    def _quick_action_clicked(self, action: Mapping[str, Any]) -> None:
        if self._running:
            messagebox.showwarning("任务运行中", "请等待当前任务结束。", parent=self.root)
            return
        try:
            payload = self._collect_payload()
            profile = _selected_profile(payload, config_path=self.config_path)
            self.payload = _apply_quick_action_preset(payload, action, profile)
            self._load_values()
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("动作不可用", str(exc), parent=self.root)
            return
        self._prepare_and_start(
            check_only=bool(action["check_only"]), action_label=str(action["label"])
        )

    def _run_clicked(self) -> None:
        self._prepare_and_start(check_only=False, action_label="完整流水线")

    def _prepare_and_start(self, *, check_only: bool, action_label: str) -> None:
        if not self._save():
            return
        try:
            required = _required_config_fields(
                self.payload, self.schema, config_path=self.config_path
            )
            missing = _missing_required_fields(self.payload, required)
        except (OSError, RuntimeError, ValueError) as exc:
            messagebox.showerror("配置不完整", str(exc), parent=self.root)
            return
        if missing:
            display_names = [
                f"- {self.field_label_text.get(path, path)} ({path})" for path in missing
            ]
            messagebox.showerror(
                "缺少必填配置",
                "当前动作缺少以下必填项：\n\n" + "\n".join(display_names),
                parent=self.root,
            )
            return
        if not check_only and _hardware_actions_selected(self.payload):
            if not bool(_get_dotted(self.payload, "pipeline.confirm_hardware_actions")):
                messagebox.showerror(
                    "硬件门禁未确认",
                    "已选择真实硬件动作，请先勾选“已确认本次真实硬件动作”。",
                    parent=self.root,
                )
                return
            if not messagebox.askyesno(
                "确认真实硬件动作",
                "本次运行将访问真实硬件，可能包含配置、烧录、复位或运行控制。\n\n"
                "确认硬件连接、镜像和恢复路径均已检查？",
                parent=self.root,
            ):
                return
        self._start_process(check_only=check_only, action_label=action_label)

    # 日志按批次写入Text控件，避免每一行反复切换控件状态导致长流程界面卡顿。
    def _append_log(self, text: str) -> None:
        self._pending_log.append(text)

    def _flush_log(self) -> None:
        if not self._pending_log:
            return
        text = "".join(self._pending_log)
        self._pending_log.clear()
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        if self._running:
            return
        self._pending_log.clear()
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.status.set("日志已清空")

    def _set_operation_state(self, *, running: bool) -> None:
        self._running = running
        for button in self.operation_buttons:
            button.configure(state="disabled" if running else "normal")
        if not running:
            self._refresh_dynamic_state()

    # 子线程只读取子进程输出，所有Tk控件更新仍在主线程完成。
    def _start_process(self, *, check_only: bool, action_label: str) -> None:
        if self._running:
            messagebox.showwarning("任务运行中", "请等待当前任务结束。", parent=self.root)
            return
        command = _pipeline_command(self.config_path, check_only=check_only)
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self._append_log(
            f"\n[ACTION] {action_label}\n[START] {started_at}\n"
            + "$ "
            + subprocess.list2cmdline(command)
            + "\n"
        )
        self.status.set(f"正在执行：{action_label}")
        self._set_operation_state(running=True)

        def worker() -> None:
            try:
                # 固定 Python 子进程的标准输出编码，避免 Windows 重定向管道使用本地代码页。
                child_environment = os.environ.copy()
                child_environment["PYTHONIOENCODING"] = "utf-8"
                self.process = subprocess.Popen(
                    command,
                    cwd=REPOSITORY_ROOT,
                    env=child_environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                )
                assert self.process.stdout is not None
                for line in self.process.stdout:
                    self.output_queue.put(line)
                self.output_queue.put(f"\n[EXIT] {self.process.wait()}\n")
            except OSError as exc:
                self.output_queue.put(f"\n[ERROR] {exc}\n")
            finally:
                self.output_queue.put(None)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, self._drain_output)

    def _drain_output(self) -> None:
        finished = False
        for _item_index in range(LOG_MAX_BATCH_ITEMS):
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                finished = True
            else:
                self._append_log(item)
        self._flush_log()
        if finished:
            return_code = self.process.returncode if self.process is not None else 2
            self.process = None
            finished_at = datetime.now().astimezone().isoformat(timespec="seconds")
            self._append_log(f"[FINISH] {finished_at}\n")
            self._flush_log()
            self._set_operation_state(running=False)
            self.status.set("执行完成" if return_code == 0 else f"执行失败：{return_code}")
            return
        self.root.after(LOG_BATCH_INTERVAL_MS, self._drain_output)

    def _close(self) -> None:
        if self._running:
            messagebox.showwarning("任务运行中", "请等待当前任务结束后退出。", parent=self.root)
            return
        self.root.destroy()


# 启动或无界面实例化GUI；smoke-test不会执行Pipeline或硬件动作。
def _launch_gui(config_path: Path, *, smoke_test: bool) -> int:
    global filedialog, messagebox, tk, ttk

    import tkinter as tk_module
    from tkinter import filedialog as filedialog_module
    from tkinter import messagebox as messagebox_module
    from tkinter import ttk as ttk_module

    tk = tk_module
    ttk = ttk_module
    filedialog = filedialog_module
    messagebox = messagebox_module
    root = tk.Tk()
    if smoke_test:
        root.withdraw()
    application = RunConfigGui(root, config_path)
    if smoke_test:
        root.update_idletasks()
        root.destroy()
        return 0
    root.protocol("WM_DELETE_WINDOW", application._close)
    root.mainloop()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config_path = Path(args.config).resolve()
    try:
        if not config_path.is_file():
            raise RuntimeError(f"operator configuration does not exist: {config_path}")
        if not CONFIG_TEMPLATE.is_file():
            raise RuntimeError(f"configuration template does not exist: {CONFIG_TEMPLATE}")
        return _launch_gui(config_path, smoke_test=bool(args.smoke_test))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
