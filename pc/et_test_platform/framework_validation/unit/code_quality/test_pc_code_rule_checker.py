# Framework Validation测试模块。
#
# 职责：验证test_pc_code_rule_checker 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[5]
CHECKER_PATH = REPOSITORY_ROOT / "tools" / "quality" / "check_pc_code_rules.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("et_pc_rule_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PC rule checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _rules(checker: ModuleType, path: Path, root: Path) -> set[str]:
    return {violation.rule for violation in checker.check_file(path, repository_root=root)}


def test_checker_accepts_a_small_well_formed_driver(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/driver.py",
        "# DMA 单 IP Driver；不跨 IP，依赖本 IP Codec 和 TargetClient。\n\n"
        "# 提供 DMA 单 IP 稳定操作，不承担跨 IP 编排。\n"
        "class DmaDriver:\n"
        "    # 返回 DMA Channel 状态事实，不等待后续状态变化。\n"
        "    def status(self, channel: int) -> int:\n"
        "        return channel\n",
    )

    assert checker.check_file(path, repository_root=tmp_path) == []


def test_checker_allows_struct_calls_inside_codec(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/drivers/uart/codec.py",
        '"""UART codec."""\n\n'
        "import struct\n\n"
        "def encode(value: int) -> bytes:\n"
        "    return struct.pack('<I', value)\n",
    )

    assert "ETPC205" not in _rules(checker, path, tmp_path)


def test_checker_rejects_cross_ip_struct_assert_and_missing_annotations(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/driver.py",
        "from et_test_platform.drivers.uart import UartDriver\n"
        "import struct\n\n"
        "def configure(value):\n"
        "    assert value\n"
        "    return struct.pack('<I', value)\n",
    )

    assert {"ETPC001", "ETPC006", "ETPC205", "ETPC403", "ETPC410"} <= _rules(
        checker,
        path,
        tmp_path,
    )


def test_checker_rejects_driver_environment_and_pytest_dependencies(tmp_path: Path) -> None:
    checker = _load_checker()
    profile_driver = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/driver.py",
        '"""DMA Driver."""\nfrom et_test_platform.profiles.capabilities import ChipCapabilities\n',
    )
    pytest_driver = _write(
        tmp_path,
        "pc/et_test_platform/drivers/uart/driver.py",
        '"""UART Driver."""\nimport pytest\n',
    )

    assert "ETPC214" in _rules(checker, profile_driver, tmp_path)
    assert "ETPC214" in _rules(checker, pytest_driver, tmp_path)


def test_checker_rejects_model_codec_and_hidden_exception_failures(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    model = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/models.py",
        '"""DMA models."""\n\n'
        "class Config:\n"
        "    def encode(self) -> bytes:\n"
        "        return b''\n",
    )
    codec = _write(
        tmp_path,
        "pc/et_test_platform/drivers/dma/codec.py",
        '"""DMA codec."""\nfrom et_test_platform.clients.target import TargetClient\n',
    )
    vague = _write(
        tmp_path,
        "pc/et_test_platform/core/utils.py",
        '"""Bad utility module."""\n\n'
        "def run() -> None:\n"
        "    try:\n"
        "        raise RuntimeError\n"
        "    except Exception:\n"
        "        pass\n",
    )

    assert "ETPC202" in _rules(checker, model, tmp_path)
    assert "ETPC206" in _rules(checker, codec, tmp_path)
    assert {"ETPC401", "ETPC411"} <= _rules(checker, vague, tmp_path)


def test_checker_requires_readable_hardware_case_contract(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/test_uart_p2.py",
        '"""UART DMA Case."""\n'
        "import pytest\n"
        "from et_test_platform.drivers.uart.codec import encode\n\n"
        "pytestmark = pytest.mark.hardware\n\n"
        "# 测试 Feature：\n"
        "# UART DMA TX。\n"
        "def test_uart_dma_tx() -> None:\n"
        "    del encode\n",
    )

    assert {"ETPC104", "ETPC207"} <= _rules(checker, path, tmp_path)


def test_checker_rejects_missing_public_comment_and_resolver_driver_import(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    driver = _write(
        tmp_path,
        "pc/et_test_platform/drivers/resource/driver.py",
        '"""Resource Driver."""\n\ndef reset() -> None:\n    return None\n',
    )
    resolver = _write(
        tmp_path,
        "pc/et_test_platform/profiles/resolvers/dma_routes.py",
        '"""DMA Resolver."""\n'
        "from et_test_platform.drivers.dma import DMA_SERVICE_ID\n\n"
        "def resolve() -> int:\n"
        '    """Resolve a stable DMA route without hardware I/O."""\n'
        "    return DMA_SERVICE_ID\n",
    )

    assert "ETPC412" in _rules(checker, driver, tmp_path)
    assert "ETPC208" in _rules(checker, resolver, tmp_path)


def test_checker_rejects_case_protocol_import(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/test_busy.py",
        '"""UART busy Case."""\n'
        "from et_test_platform.communication.protocols.et_message import Status\n",
    )

    assert "ETPC207" in _rules(checker, path, tmp_path)
