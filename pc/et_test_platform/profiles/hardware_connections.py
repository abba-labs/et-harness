# 硬件连接配置的只读入口。
# 职责：只加载active环境，返回各IP的handle/GPIO，检查本Case的IO冲突。
# 边界：不操作硬件，不维护Pinmux目录，不全局占用IO。
# 依赖：标准库、PyYAML、Capability和平台配置异常。

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import yaml

from ..core.errors import ConfigurationError
from .capabilities import ChipCapabilities


# 保存当前环境中一个角色的逻辑实例和信号GPIO号；数据只读，不执行硬件配置。
@dataclass(frozen=True, slots=True)
class ConnectionEndpoint:
    handle: str
    gpio: Mapping[str, int]


# 仅包含当前生效环境的数据，不向调用方暴露另一套环境。
@dataclass(frozen=True, slots=True)
class HardwareConnections:
    lane: str
    ips: Mapping[str, Mapping[str, ConnectionEndpoint]]

    # 配置前选择本Case所用IP；允许跨Case复用，不允许本Case重复配置同一GPIO。
    def select(self, *ips: str) -> Mapping[str, Mapping[str, ConnectionEndpoint]]:

        if not ips or len(set(ips)) != len(ips):
            raise ConfigurationError("select requires non-empty, distinct IP names")
        selected: dict[str, Mapping[str, ConnectionEndpoint]] = {}
        occupied: dict[int, str] = {}

        # 占用表只在本次调用内有效，失败也不会污染下一次选择。
        for ip in ips:
            if ip not in self.ips:
                raise ConfigurationError(f"{ip!r} is not configured for {self.lane}")
            for role, endpoint in self.ips[ip].items():
                for signal, gpio in endpoint.gpio.items():
                    owner = f"{ip}.{role}.{signal}"
                    if gpio in occupied:
                        raise ConfigurationError(f"GPIO{gpio} conflict: {occupied[gpio]} / {owner}")
                    occupied[gpio] = owner
            selected[ip] = self.ips[ip]
        return MappingProxyType(selected)


# 防止重复active、IP或信号键被YAML静默覆盖。
class _UniqueLoader(yaml.SafeLoader):
    # 其余语法沿用SafeLoader，仅增加映射键检查。
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[str, object]:

        result: dict[str, object] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str) or not key.strip() or key in result:
                raise ConfigurationError(f"duplicate or invalid YAML key: {key!r}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


# 动态字典止于解析边界；拼错字段或残留旧字段直接报错。
def _mapping(value: object, name: str, keys: set[str] | None = None) -> dict[str, object]:

    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ConfigurationError(f"{name} must be a mapping with string keys")
    if keys is not None and set(value) != keys:
        raise ConfigurationError(f"{name} fields must be {sorted(keys)}; got {sorted(value)}")
    return value


# handle按Capability核对，GPIO保持整数；不靠名称猜测或硬编码芯片mux。
def _endpoint(value: object, ip: str, caps: ChipCapabilities) -> ConnectionEndpoint:

    raw = _mapping(value, f"{ip}.endpoint", {"handle", "gpio"})
    handle = raw["handle"]
    if not isinstance(handle, str) or handle not in caps.instances(ip):
        raise ConfigurationError(f"unknown Capability handle {ip}.{handle!r}")
    gpio = _mapping(raw["gpio"], f"{handle}.gpio")
    for signal, number in gpio.items():
        if type(number) is not int or number < 0:
            raise ConfigurationError(f"{handle}.{signal}: GPIO must be a non-negative integer")
    return ConnectionEndpoint(handle=handle, gpio=MappingProxyType(gpio))


# 默认从bench_topologies读取目标芯片文件；active唯一选区，expected_lane只核对目标。
def load_hardware_connections(
    profile_path: str | Path | None = None,
    *,
    capabilities: ChipCapabilities,
    expected_lane: str | None = None,
) -> HardwareConnections:

    path = (
        Path(profile_path)
        if profile_path is not None
        else Path(__file__).parent
        / "bench_topologies"
        / f"{capabilities.chip_id}_hardware_connections.yaml"
    )
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"cannot load hardware connections {path}: {exc}") from exc
    root = _mapping(raw, "connections", {"chip", "active", "fpga", "silicon"})
    if root["chip"] != capabilities.chip_id:
        raise ConfigurationError("hardware connection target chip mismatch")
    active = root["active"]
    if active not in ("fpga", "silicon"):
        raise ConfigurationError("active must be exactly one of fpga or silicon")
    if expected_lane is not None and expected_lane != active:
        raise ConfigurationError(f"active {active!r} does not match target {expected_lane!r}")

    # 固定读取root[active][ip][role]；不合并、不回退到另一环境。
    selected = _mapping(root[active], active)
    ips: dict[str, Mapping[str, ConnectionEndpoint]] = {}
    for ip, value in selected.items():
        if ip not in capabilities.ip_ids:
            raise ConfigurationError(f"unknown Capability IP {ip!r}")
        roles = _mapping(value, ip)
        if not roles:
            raise ConfigurationError(f"{ip} must contain at least one role")
        ips[ip] = MappingProxyType(
            {role: _endpoint(endpoint, ip, capabilities) for role, endpoint in roles.items()}
        )
    return HardwareConnections(lane=active, ips=MappingProxyType(ips))
