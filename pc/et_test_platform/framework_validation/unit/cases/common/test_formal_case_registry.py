# Formal Case显式注册表的软件合同测试。
#
# 职责：验证白名单的失败闭合、默认拒绝、IP归属和源码存在性。
# 边界：不启动真实pytest硬件会话、不构造Driver，也不访问设备。
# 依赖：仅依赖注册表公共模型、pytest收集对象最小替身和源码AST。

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from et_test_platform.scheduling.test_registry import (
    IpRegistration,
    RegistryError,
    discover_formal_case_ids,
    select_registered_cases,
    validate_ip_registry,
    validate_registered_case_ids,
)
from et_test_platform.test_cases.ip_registry import IP_REGISTRY

PROJECT_ROOT = Path(__file__).parents[6]
CASE_ROOT = PROJECT_ROOT / "pc" / "et_test_platform" / "test_cases"


class _FakeItem:
    def __init__(self, path: Path, function_name: str, ip_id: str) -> None:
        self.path = path
        self.name = function_name
        self.originalname = function_name
        self.nodeid = f"{path}::{function_name}"
        self._ip_id = ip_id

    def iter_markers(self, name: str):
        if name != "ip":
            return ()
        return (SimpleNamespace(args=(self._ip_id,), kwargs={}),)


# 注册表结构必须拒绝重复IP、重复Case以及错误的Case归属。
def test_ip_registry_rejects_ambiguous_or_misowned_entries() -> None:

    with pytest.raises(RegistryError, match="duplicate IP"):
        validate_ip_registry(
            (
                IpRegistration("uart", ("uart_p0_001",)),
                IpRegistration("uart", ("uart_p0_002",)),
            )
        )

    with pytest.raises(RegistryError, match="duplicate Case"):
        validate_ip_registry((IpRegistration("uart", ("uart_p0_001", "uart_p0_001")),))

    with pytest.raises(RegistryError, match="registered under IP"):
        validate_ip_registry((IpRegistration("uart", ("dma_p0_001",)),))


# 收集过滤必须保留已注册Case和非Formal测试，并取消未注册Case而不是标记SKIP。
def test_case_registry_is_default_deny_without_affecting_non_formal_tests(
    tmp_path: Path,
) -> None:

    case_root = tmp_path / "test_cases"
    registered = _FakeItem(
        case_root / "uart" / "test_uart_p0.py",
        "test_uart_p0_001_identity",
        "uart",
    )
    unregistered = _FakeItem(
        case_root / "uart" / "test_uart_p0.py",
        "test_uart_p0_002_reset",
        "uart",
    )
    unrelated = _FakeItem(
        tmp_path / "framework_validation" / "test_unit.py",
        "test_unit_behavior",
        "unit",
    )
    unregistered_ip = _FakeItem(
        case_root / "dma" / "test_dma_p0.py",
        "test_dma_p0_001_capabilities",
        "dma",
    )

    selection = select_registered_cases(
        cast(
            list[pytest.Item],
            [registered, unregistered, unrelated, unregistered_ip],
        ),
        (IpRegistration("uart", ("uart_p0_001",)),),
        case_root=case_root,
    )

    assert selection.selected == (registered, unrelated)
    assert selection.deselected == (unregistered, unregistered_ip)


# Case命名中的IP与ip(name) Marker不一致时必须在Fixture初始化前失败。
def test_case_registry_rejects_marker_mismatch(tmp_path: Path) -> None:

    case_root = tmp_path / "test_cases"
    item = _FakeItem(
        case_root / "uart" / "test_uart_p0.py",
        "test_uart_p0_001_identity",
        "dma",
    )

    with pytest.raises(RegistryError, match=r"declares ip\(dma\)"):
        select_registered_cases(
            cast(list[pytest.Item], [item]),
            (
                IpRegistration("uart", ("uart_p0_001",)),
                IpRegistration("dma", ()),
            ),
            case_root=case_root,
        )


# 当前显式白名单中的每个稳定Case ID都必须存在唯一源码实现。
def test_registered_case_ids_exist_in_formal_case_source() -> None:

    discovered_case_ids = discover_formal_case_ids(CASE_ROOT)
    validate_registered_case_ids(IP_REGISTRY, discovered_case_ids)
