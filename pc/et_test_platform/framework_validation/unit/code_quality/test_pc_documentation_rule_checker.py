# Framework Validation测试模块。
#
# 职责：验证test_pc_documentation_rule_checker 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[5]
CHECKER_PATH = REPOSITORY_ROOT / "tools" / "quality" / "check_pc_documentation_rules.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("et_pc_documentation_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PC documentation checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _codes(checker: ModuleType, path: Path, root: Path) -> set[str]:
    return {item.code for item in checker.check_file(path, repository_root=root)}


def test_documentation_checker_accepts_explicit_module_and_driver_contract(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/driver.py",
        "# DMA 单 IP Driver。\n"
        "#\n"
        "# 职责：提供 DMA 稳定业务 API。\n"
        "# 边界：不调用其他 IP Driver，不读取 Bench。\n"
        "# 依赖：仅依赖本 IP Codec、Model 与 TargetClient。\n\n"
        "# 封装一个 DMA Service Instance 的稳定操作，不承担跨 IP 编排。\n"
        "class DmaDriver:\n"
        "    # 启动已配置通道；不等待传输完成，Target 拒绝或超时按平台异常上抛。\n"
        "    def start(self, channel: int) -> None:\n"
        "        del channel\n",
    )

    assert checker.check_file(path, repository_root=tmp_path) == []


def test_documentation_checker_rejects_english_module_and_generated_api_doc(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/clients/target.py",
        "# Target client.\n\n"
        "# Transport request client with stable request behavior.\n"
        "class TargetClient:\n"
        "    # Execute ``open`` while preserving this module's documented responsibility boundary.\n"
        "    def open(self) -> None:\n"
        "        return None\n",
    )

    assert {"ETDOC101", "ETDOC102", "ETDOC202", "ETDOC203", "ETDOC205"} <= _codes(
        checker, path, tmp_path
    )


def test_documentation_checker_rejects_runtime_fact_template(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/scheduling/run_context.py",
        "# 运行上下文。\n"
        "#\n"
        "# 职责：记录测试运行元数据。\n"
        "# 边界：不执行硬件命令。\n"
        "# 依赖：仅依赖文件系统。\n\n"
        "# 提供 platform version 对应的运行时测试上下文事实；不拥有最终业务断言。\n"
        "def platform_version() -> str:\n"
        "    return 'test'\n",
    )

    assert "ETDOC203" in _codes(checker, path, tmp_path)


def test_documentation_checker_rejects_module_without_explicit_boundaries(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/core/errors.py",
        "# 平台错误类型，供 PC 控制面统一使用。\n",
    )

    assert "ETDOC102" in _codes(checker, path, tmp_path)


# 验证Formal Case模块也必须提供中文职责边界，函数说明仍由Case专用门禁负责。
def test_documentation_checker_checks_formal_case_module_header(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/test_uart_p0.py",
        "# UART P0 cases.\n\ndef test_uart_p0() -> None:\n    pass\n",
    )

    assert {"ETDOC101", "ETDOC102"} <= _codes(checker, path, tmp_path)


# 验证Framework Validation模块也受中文模块头约束，但不把测试函数当成公共运行时API。
def test_documentation_checker_checks_validation_module_header_only(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/framework_validation/unit/communication/test_protocol.py",
        "# 协议单元测试。\n"
        "#\n"
        "# 职责：验证协议编解码合同。\n"
        "# 边界：不执行真实设备通信。\n"
        "# 依赖：仅依赖pytest和被测协议模块。\n\n"
        "def test_protocol() -> None:\n    pass\n",
    )

    assert checker.check_file(path, repository_root=tmp_path) == []
