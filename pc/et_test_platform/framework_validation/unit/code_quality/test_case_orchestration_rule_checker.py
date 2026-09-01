# Framework Validation测试模块。
#
# 职责：验证Case编排规则Checker的诊断码和失败关闭行为。
# 边界：不作为平台运行时代码，不执行真实设备操作。
# 依赖：仅依赖pytest、临时测试源和被测Checker。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[5]
CHECKER_PATH = REPOSITORY_ROOT / "tools" / "quality" / "check_case_orchestration_rules.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("et_case_rule_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Case orchestration rule checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _codes(checker: ModuleType, path: Path) -> set[str]:
    return {violation.code for violation in checker.check_file(path)}


def test_checker_rejects_nested_subcase_that_hides_complete_lifecycle(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/test_matrix.py",
        '"""DMA matrix Case."""\n\n'
        "def test_matrix(resource, dma):\n"
        "    def run_subcase():\n"
        "        resource.create(8)\n"
        "        dma.configure(object())\n"
        "        dma.start(0)\n"
        "        actual = resource.read(object())\n"
        "        assert actual\n"
        "        dma.stop(0)\n"
        "    run_subcase()\n",
    )

    assert {"ETORCH201", "ETORCH202"} <= _codes(checker, path)


# Legacy cleanup factories remain parseable until their owning Case is migrated.
def test_checker_keeps_legacy_cleanup_factory_compatible_during_migration(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/test_cleanup.py",
        '"""DMA cleanup Case."""\n\n'
        "def test_cleanup(dma):\n"
        "    def cleanup_actions():\n"
        '        return (("stop", lambda: dma.stop(0)),)\n'
        "    assert cleanup_actions()\n",
    )

    assert checker.check_file(path) == []


# Legacy lifecycle scopes must not return after a Case has been migrated.
def test_checker_rejects_legacy_lifecycle_scope(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/test_loopback.py",
        '"""UART loopback Case."""\n\n'
        "def test_loopback(uart):\n"
        "    with uart.loopback_disable_on_exit(), uart.capture_mode():\n"
        "        uart.loopback_set(True)\n"
        "        uart.capture_start(4)\n"
        "        assert uart.capture_wait(4).complete\n",
    )

    assert "ETORCH214" in _codes(checker, path)


# Cleanup aggregation and expected exceptions are the only approved Case scopes.
def test_checker_allows_approved_formal_case_context_managers(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/test_approved_scopes.py",
        '"""UART approved scopes Case."""\n\n'
        "import pytest\n\n"
        "def test_approved_scopes(uart, case_cleanup_scope):\n"
        "    def cleanup_actions():\n"
        '        return (("reset", uart.reset),)\n'
        "    with case_cleanup_scope(cleanup_actions):\n"
        "        with pytest.raises(ValueError):\n"
        "            raise ValueError('expected')\n",
    )

    assert "ETORCH214" not in _codes(checker, path)


# Direct try/finally is the readable default for a linear cleanup sequence.
def test_checker_allows_direct_finally_cleanup_in_formal_case(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/test_cleanup.py",
        '"""DMA cleanup Case."""\n\n'
        "def test_cleanup(dma):\n"
        "    try:\n"
        "        dma.start(0)\n"
        "    finally:\n"
        "        dma.stop(0)\n"
        "        dma.deconfigure(0)\n",
    )

    assert "ETORCH206" not in _codes(checker, path)


def test_checker_rejects_helper_that_raises_case_specific_conclusion(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/uart_helpers.py",
        '"""UART helper."""\n\n'
        "def require_irq(state, *, case_id):\n"
        "    if not state:\n"
        "        raise RuntimeError(case_id)\n",
    )

    assert "ETORCH207" in _codes(checker, path)


def test_checker_rejects_helper_module_that_owns_multiple_ip_drivers(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/dma_peer.py",
        '"""Hidden cross-IP adapter."""\n'
        "from et_test_platform.drivers.dma import DmaDriver\n"
        "from et_test_platform.drivers.sysctrl import SysctrlDriver\n"
        "from et_test_platform.drivers.uart import UartDriver\n",
    )

    assert "ETORCH205" in _codes(checker, path)


def test_checker_rejects_target_client_import_in_case_layer(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/spi/test_transfer.py",
        '"""SPI transfer Case."""\nfrom et_test_platform.clients.target import TargetClient\n',
    )

    assert "ETORCH210" in _codes(checker, path)


def test_checker_rejects_direct_driver_construction_in_case_layer(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/spi/test_transfer.py",
        '"""SPI transfer Case."""\n'
        "from et_test_platform.drivers.spi import SpiDriver\n\n"
        "def test_transfer(target):\n"
        "    driver = SpiDriver(target)\n"
        "    del driver\n",
    )

    assert "ETORCH211" in _codes(checker, path)


def test_checker_allows_driver_aggregation_in_ip_local_support(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/_support.py",
        '"""DMA Case environment facts."""\n'
        "import pytest\n"
        "from et_test_platform.drivers.dma import DmaDriver\n"
        "from et_test_platform.drivers.sysctrl import SysctrlDriver\n"
        "from et_test_platform.drivers.uart import UartDriver\n\n"
        "def build_support(target):\n"
        "    if target is None:\n"
        "        pytest.skip('DMA service unavailable')\n"
        "    return DmaDriver(target), SysctrlDriver(target), UartDriver(target)\n",
    )

    assert checker.check_file(path) == []


def test_checker_rejects_hardware_workflow_in_ip_local_support(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/conftest.py",
        '"""DMA Case fixtures."""\n\n'
        "def dma_support(dma):\n"
        "    dma.configure(object())\n"
        "    dma.start(0)\n"
        "    return dma.wait_complete(0)\n",
    )

    assert "ETORCH212" in _codes(checker, path)


def test_checker_rejects_final_assert_in_ip_local_support(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/dma/_support.py",
        '"""DMA Case environment facts."""\n\n'
        "def require_support(capability):\n"
        "    assert capability\n",
    )

    assert "ETORCH213" in _codes(checker, path)


def test_checker_allows_small_single_observation_helper(tmp_path: Path) -> None:
    checker = _load_checker()
    path = _write(
        tmp_path,
        "pc/et_test_platform/test_cases/uart/uart_observation.py",
        '"""UART fact observation helper."""\n\n'
        "def observe_irq(handle):\n"
        "    return handle.irq_state_get()\n",
    )

    assert checker.check_file(path) == []
