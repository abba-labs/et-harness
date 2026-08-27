# Framework Validation测试模块。
#
# 职责：验证Formal Case Evidence Checker对Snapshot覆盖风险的失败关闭行为。
# 边界：只解析临时Python源码，不执行真实Case、硬件或Artifact写入。
# 依赖：仅依赖pytest临时目录和被测Checker。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPOSITORY_ROOT = Path(__file__).parents[5]
CHECKER_PATH = REPOSITORY_ROOT / "tools" / "quality" / "check_case_spec_implementation.py"


def _load_checker() -> ModuleType:
    spec = importlib.util.spec_from_file_location("et_case_spec_checker", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Case specification implementation checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _codes(checker: ModuleType, path: Path) -> set[str]:
    return {violation.code for violation in checker.check_snapshot_writes(path)}


def _write_snapshot_helper(root: Path) -> None:
    _write(
        root,
        "evidence_helpers.py",
        "from et_test_platform.results.recorder import write_json_result\n\n"
        "def record_result(artifact_dir, case_id, **fields):\n"
        "    return write_json_result(artifact_dir / f'{case_id}.json', fields)\n",
    )


def test_checker_rejects_multiple_reachable_writes_to_same_snapshot(tmp_path: Path) -> None:
    checker = _load_checker()
    package = tmp_path / "aes"
    _write_snapshot_helper(package)
    path = _write(
        package,
        "test_aes_p1.py",
        "from .evidence_helpers import record_result\n\n"
        "def test_aes_p1_001(artifact_dir):\n"
        "    record_result(artifact_dir, 'aes_p1_001', before=1)\n"
        "    record_result(artifact_dir, 'aes_p1_001', after=0)\n",
    )

    assert "ETSPEC205" in _codes(checker, path)


def test_checker_rejects_loop_invariant_snapshot_target(tmp_path: Path) -> None:
    checker = _load_checker()
    package = tmp_path / "aes"
    _write_snapshot_helper(package)
    path = _write(
        package,
        "test_aes_p1.py",
        "from .evidence_helpers import record_result\n\n"
        "def test_aes_p1_002(artifact_dir):\n"
        "    for index in range(4):\n"
        "        record_result(artifact_dir, 'aes_p1_002', index=index)\n",
    )

    assert "ETSPEC206" in _codes(checker, path)


def test_checker_allows_loop_with_unique_snapshot_path(tmp_path: Path) -> None:
    checker = _load_checker()
    package = tmp_path / "crc"
    path = _write(
        package,
        "test_crc_p1.py",
        "from et_test_platform.results.recorder import write_json_result\n\n"
        "def test_crc_p1_001(artifact_dir):\n"
        "    for index in range(4):\n"
        "        write_json_result(artifact_dir / f'round_{index}.json', {'index': index})\n",
    )

    assert _codes(checker, path).isdisjoint({"ETSPEC205", "ETSPEC206"})


def test_checker_allows_mutually_exclusive_single_snapshot_publish(tmp_path: Path) -> None:
    checker = _load_checker()
    package = tmp_path / "uart"
    _write_snapshot_helper(package)
    path = _write(
        package,
        "test_uart_p1.py",
        "from .evidence_helpers import record_result\n\n"
        "def test_uart_p1_001(artifact_dir, use_peer):\n"
        "    if use_peer:\n"
        "        record_result(artifact_dir, 'uart_p1_001', route='peer')\n"
        "    else:\n"
        "        record_result(artifact_dir, 'uart_p1_001', route='loopback')\n",
    )

    assert "ETSPEC205" not in _codes(checker, path)


def test_checker_allows_one_final_snapshot(tmp_path: Path) -> None:
    checker = _load_checker()
    package = tmp_path / "dma"
    _write_snapshot_helper(package)
    path = _write(
        package,
        "test_dma_p1.py",
        "from .evidence_helpers import record_result\n\n"
        "def test_dma_p1_001(artifact_dir):\n"
        "    evidence = {'before': 1, 'after': 0}\n"
        "    record_result(artifact_dir, 'dma_p1_001', **evidence)\n",
    )

    assert _codes(checker, path).isdisjoint({"ETSPEC205", "ETSPEC206"})
