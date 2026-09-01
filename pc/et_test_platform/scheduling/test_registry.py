# Formal Case注册表的不可变模型和收集过滤。
#
# 职责：校验IP/Case白名单，并在pytest收集阶段区分已注册和未注册Case。
# 边界：不导入具体Case、不构造Driver、不访问Capability、Runtime Service或硬件。
# 依赖：仅依赖pytest收集对象和Python标准库。

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

_IP_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_]*$")
_CASE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^(?P<ip>[a-z][a-z0-9_]*?)_p(?P<level>[0-3])_(?P<number>[0-9]{3})$"
)
_CASE_FUNCTION_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^test_(?P<case_id>[a-z][a-z0-9_]*?_p[0-3]_[0-9]{3})(?:_|$)"
)


# 描述一个IP允许进入正式执行集合的稳定Case ID；对象创建后不可修改。
@dataclass(frozen=True, slots=True)
class IpRegistration:
    ip_id: str
    case_ids: tuple[str, ...]


# 保存一次pytest收集过滤结果；未注册项只会被取消收集，不会伪装为SKIP。
@dataclass(frozen=True, slots=True)
class RegistrySelection:
    selected: tuple[pytest.Item, ...]
    deselected: tuple[pytest.Item, ...]


# 表示注册表自身不一致；调用方必须在Fixture初始化前将其转换为收集错误。
class RegistryError(ValueError):
    pass


# 校验IP/Case命名、唯一性和归属关系；成功后返回按IP索引的不可变Case ID元组副本。
def validate_ip_registry(
    registrations: tuple[IpRegistration, ...],
) -> dict[str, tuple[str, ...]]:

    by_ip: dict[str, tuple[str, ...]] = {}
    all_case_ids: set[str] = set()

    # 逐IP检查命名、重复项和Case归属，避免字典覆盖隐藏重复注册。
    for registration in registrations:
        ip_id = registration.ip_id
        if _IP_ID_PATTERN.fullmatch(ip_id) is None:
            raise RegistryError(f"invalid IP registry ID: {ip_id!r}")
        if ip_id in by_ip:
            raise RegistryError(f"duplicate IP registry ID: {ip_id}")

        local_case_ids: set[str] = set()

        # 逐Case检查稳定ID及所属IP；Tuple保留重复项供校验，不静默去重。
        for case_id in registration.case_ids:
            match = _CASE_ID_PATTERN.fullmatch(case_id)
            if match is None:
                raise RegistryError(f"invalid Case registry ID: {case_id!r}")
            if match.group("ip") != ip_id:
                raise RegistryError(
                    f"Case {case_id} is registered under IP {ip_id}, expected {match.group('ip')}"
                )
            if case_id in local_case_ids or case_id in all_case_ids:
                raise RegistryError(f"duplicate Case registry ID: {case_id}")
            local_case_ids.add(case_id)
            all_case_ids.add(case_id)

        by_ip[ip_id] = registration.case_ids

    return by_ip


# 从pytest函数名提取平台稳定Case ID；参数化后缀不属于逻辑Case ID。
def case_id_from_item(item: pytest.Item) -> str:

    original_name = getattr(item, "originalname", None)
    function_name = original_name if isinstance(original_name, str) else item.name.split("[", 1)[0]
    match = _CASE_FUNCTION_PATTERN.match(function_name)
    if match is None:
        raise RegistryError(
            f"formal Case function does not follow the stable naming rule: {item.nodeid}"
        )
    return match.group("case_id")


# 读取Case唯一IP Marker；缺失、重复或参数非法都会在硬件Fixture初始化前失败。
def ip_id_from_item(item: pytest.Item) -> str:

    markers = tuple(item.iter_markers(name="ip"))
    if len(markers) != 1 or len(markers[0].args) != 1 or markers[0].kwargs:
        raise RegistryError(f"formal Case must declare exactly one ip(name) marker: {item.nodeid}")
    ip_id = markers[0].args[0]
    if not isinstance(ip_id, str) or _IP_ID_PATTERN.fullmatch(ip_id) is None:
        raise RegistryError(f"formal Case has invalid ip(name) marker: {item.nodeid}")
    return ip_id


# 按显式白名单过滤Formal Case，同时保持非Formal测试项目不受影响。
def select_registered_cases(
    items: list[pytest.Item],
    registrations: tuple[IpRegistration, ...],
    *,
    case_root: Path,
) -> RegistrySelection:

    registry = validate_ip_registry(registrations)
    registered_case_ids = {case_id for case_ids in registry.values() for case_id in case_ids}
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    resolved_case_root = case_root.resolve()
    collected_definitions: dict[str, set[tuple[Path, str]]] = {}

    # 收集期只读取名称和Marker；此阶段不请求Fixture，因此不会访问硬件。
    for item in items:
        item_path = Path(str(item.path)).resolve()
        if not item_path.is_relative_to(resolved_case_root):
            selected.append(item)
            continue

        case_id = case_id_from_item(item)
        marker_ip = ip_id_from_item(item)
        case_match = _CASE_ID_PATTERN.fullmatch(case_id)
        if case_match is None:
            raise RegistryError(f"invalid collected Case ID: {case_id}")
        if case_match.group("ip") != marker_ip:
            raise RegistryError(
                f"Case {case_id} declares ip({marker_ip}), expected ip({case_match.group('ip')})"
            )
        original_name = getattr(item, "originalname", None)
        definition_name = (
            original_name if isinstance(original_name, str) else item.name.split("[", 1)[0]
        )
        definitions = collected_definitions.setdefault(case_id, set())
        definitions.add((item_path, definition_name))
        if len(definitions) > 1:
            raise RegistryError(f"Case ID {case_id} is implemented by multiple functions")

        if marker_ip in registry and case_id in registered_case_ids:
            selected.append(item)
        else:
            deselected.append(item)

    return RegistrySelection(selected=tuple(selected), deselected=tuple(deselected))


# 校验所有显式注册ID都能在完整Case源码清单中找到，防止失效白名单静默存在。
def validate_registered_case_ids(
    registrations: tuple[IpRegistration, ...],
    discovered_case_ids: set[str],
) -> None:

    registry = validate_ip_registry(registrations)
    registered_case_ids = {case_id for case_ids in registry.values() for case_id in case_ids}
    missing = sorted(registered_case_ids - discovered_case_ids)
    if missing:
        raise RegistryError("registered Case IDs have no implementation: " + ", ".join(missing))


# 从Formal Case源码读取稳定ID并校验唯一性；不导入测试模块，也不触发Fixture或硬件访问。
def discover_formal_case_ids(case_root: Path) -> set[str]:

    locations: dict[str, list[str]] = {}

    # 扫描固定P级文件；只处理函数定义，Helper和Deferred模块不属于正式Case入口。
    for path in sorted(case_root.rglob("test_*_p*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

        # 逐函数提取稳定ID；不符合命名规则的test函数必须失败闭合。
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            match = _CASE_FUNCTION_PATTERN.match(node.name)
            if match is None:
                raise RegistryError(
                    "formal Case function does not follow the stable naming rule: "
                    f"{path}:{node.lineno}:{node.name}"
                )
            case_id = match.group("case_id")
            locations.setdefault(case_id, []).append(f"{path}:{node.lineno}")

    duplicates = {
        case_id: definitions for case_id, definitions in locations.items() if len(definitions) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{case_id} -> {', '.join(definitions)}"
            for case_id, definitions in sorted(duplicates.items())
        )
        raise RegistryError("Case IDs have multiple source implementations: " + details)

    return set(locations)
