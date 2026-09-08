# Canonical Session导入的真实报告模型回归。
# 职责：验证原始方法Hash、选中集合、附件保存和Lane来源约束。
# 边界：构造软件测试样本，不接触硬件或修改历史Run。
# 依赖：pytest、既有公共报告样本和记录导入模块。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from ..results.test_case_report import _result, _write_document


@pytest.fixture
def source(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    return importlib.import_module("record_source")


def make_session(source: ModuleType, repository: Path, *, missing: bool = False) -> Path:
    transaction = importlib.import_module("record_transaction")
    document = repository / "test_case_doc/crc/crc.md"
    document.parent.mkdir(parents=True)
    _write_document(document)
    run = repository / "artifacts/runs/synthetic"
    run.mkdir(parents=True)
    result = _result("CRC_P1_001", "PASS", measurements={"expected_crc": 1, "actual_crc": 1})
    result["ip_id"] = "crc"
    relative = f"cases/{result['case_run_id']}/trace.log"
    result["artifacts"] = {"trace": relative}
    session = {
        "schema_version": 1,
        "run_id": "run-1",
        "chip_id": "ET6801",
        "target_id": "dut",
        "finished_at": "2026-09-08T01:00:00Z",
        "exitstatus": 2 if missing else 0,
        "source_revision": "a" * 40,
        "source_dirty": False,
        "spec_sha256": source.digest(document.read_bytes()),
        "status_counts": {} if missing else {"PASS": 1},
        "selection": {
            "collected_count": 1,
            "selected_count": 1,
            "deselected_count": 0,
            "selected_case_ids": ["crc_p1_001"],
            "selected_executions": [{"case_id": "crc_p1_001", "parameter_id": None}],
        },
    }
    (run / "session.json").write_bytes(transaction.json_bytes(session))
    (run / "pytest.log").write_bytes(b"synthetic console\n")
    if not missing:
        case = run / "cases" / str(result["case_run_id"])
        case.mkdir(parents=True)
        (case / "result.json").write_bytes(transaction.json_bytes(result))
        (run / relative).write_bytes(b"trace bytes\n")
    return run


# 测试方法：通过真实报告模型导入合成Session；通过条件：方法和原始附件可按Hash完整取回。
def test_source_preserves_original_method_and_attachments(
    source: ModuleType, tmp_path: Path
) -> None:
    run = make_session(source, tmp_path)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    snapshot = incoming.cases["CRC_P1_001"][0]
    assert snapshot.status == "PASS"
    assert "执行DUT刺激" in snapshot.selection["method"]
    assert incoming.blobs[snapshot.files["source/pytest.log"]] == b"synthetic console\n"
    assert b"trace bytes\n" in incoming.blobs.values()
    assert snapshot.files["source/specification.md"] == snapshot.session["spec_sha256"]


# 测试方法：Session已终止但选中execution未执行；通过条件：不制造Result，显示NOT_EXECUTED。
def test_source_preserves_selected_missing_execution(source: ModuleType, tmp_path: Path) -> None:
    run = make_session(source, tmp_path, missing=True)
    incoming = source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")
    snapshot = incoming.cases["CRC_P1_001"][0]
    assert snapshot.result is None and snapshot.status == "NOT_EXECUTED"
    assert "source/result.json" not in snapshot.files


# 测试方法：篡改Selection计数或总结果计数；通过条件：导入拒绝不一致Session。
@pytest.mark.parametrize("field", ["selection", "status_counts"])
def test_source_rejects_inconsistent_counts(source: ModuleType, tmp_path: Path, field: str) -> None:
    run = make_session(source, tmp_path)
    transaction = importlib.import_module("record_transaction")
    path = run / "session.json"
    session = source.json_object(path.read_bytes())
    if field == "selection":
        session[field]["selected_count"] = 2
    else:
        session[field]["PASS"] = True
    path.write_bytes(transaction.json_bytes(session))
    with pytest.raises(ValueError, match="counts"):
        source.load_input(tmp_path, run, ip="crc", lane="fpga", work=tmp_path / "work")


# 测试方法：导入FPGA来源时声明HIL；通过条件：原Manifest冲突被拒绝。
def test_source_rejects_lane_conflict(source: ModuleType, tmp_path: Path) -> None:
    run = make_session(source, tmp_path)
    transaction = importlib.import_module("record_transaction")
    manifest = run / "manifest.json"
    manifest.write_bytes(
        transaction.json_bytes({"target_kind": "fpga", "source_revision": "a" * 40})
    )
    with pytest.raises(ValueError, match="Lane conflicts"):
        source.load_input(
            tmp_path, run, ip="crc", lane="hil", work=tmp_path / "work", manifest=manifest
        )


# 测试方法：Git只保留LF而当前文件有混合换行；通过条件：只有精确匹配旧Hash才恢复。
@pytest.mark.parametrize("damaged_hash", [False, True])
def test_source_recovers_only_exact_historical_line_endings(
    source: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, damaged_hash: bool
) -> None:
    path = tmp_path / "spec.md"
    current = b"# Current title\r\nUnchanged method\n"
    original = b"# Original title\r\nUnchanged method\n"
    path.write_bytes(current)
    monkeypatch.setattr(
        source.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=original.replace(b"\r\n", b"\n")
        ),
    )
    session = {
        "source_revision": "a" * 40,
        "spec_sha256": "0" * 64 if damaged_hash else source.digest(original),
    }
    if damaged_hash:
        with pytest.raises(ValueError, match="historical specification hash"):
            source._specification(tmp_path, path, session)
    else:
        assert source._specification(tmp_path, path, session) == original
    assert path.read_bytes() == current
