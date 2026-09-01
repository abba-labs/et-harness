# Firmware R330任务导航回归。
# 职责：锁定IP Service/Wrap任务在开发前读取R330并执行严格源码质量门禁。
# 边界：只编译Task Context，不执行业务Case、Firmware或硬件。
# 依赖：Task Context编译器、模块画像和规则Owner目录。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[5]
COMPILER = ROOT / "tools" / "governance" / "compile_task_context.py"


def _load_compiler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("r330_task_context_compiler", COMPILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Task Context compiler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_r330_route(context: dict[str, object]) -> None:
    must_read = context["must_read"]
    rule_owners = context["rule_owners"]
    validation = context["validation"]
    assert isinstance(must_read, list)
    assert isinstance(rule_owners, list)
    assert isinstance(validation, list)

    paths = {entry["path"] for entry in must_read}
    owners = {entry["owner_id"] for entry in rule_owners}
    assert "report/design/rules/R330_firmware_c_style.md" in paths
    assert "firmware_c_style" in owners
    assert any("check_firmware_c_quality.py --strict-magic" in command for command in validation)


# IP Service任务必须在写代码前获得R330正文和严格语义数字专项门禁。
def test_ip_service_task_routes_r330_before_development() -> None:
    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="DMA-SERVICE-R330-001",
        intent="维护DMA Firmware Service",
        modules=["ip-package"],
        changes=["service"],
        ip="dma",
        lanes=["firmware"],
    )

    _assert_r330_route(context)


# IP Wrap任务除Wrap/芯片边界外，同样必须在开发前获得R330正文和严格门禁。
def test_ip_wrap_task_routes_r330_before_development() -> None:
    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="UART-WRAP-R330-001",
        intent="维护UART Firmware Wrap",
        modules=["ip-package"],
        changes=["wrap"],
        ip="uart",
        chip="et6801",
        lanes=["firmware"],
    )

    _assert_r330_route(context)
