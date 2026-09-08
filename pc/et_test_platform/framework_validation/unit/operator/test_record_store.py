# Case证据维护的无硬件回归。
# 职责：验证部分更新、来源隔离、计数、保护、容量及固定文件布局。
# 边界：使用合成结果，不形成芯片测试结论。
# 依赖：标准库、pytest和记录工具。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    return importlib.import_module("record_store")


def incoming(
    store: ModuleType,
    run: int,
    *,
    status: str = "PASS",
    parameter: str = "a",
    lane: str = "fpga",
    case: str = "TEST_P0_001",
    source_revision: str | None = None,
) -> object:
    model = importlib.import_module("record_model")
    source = importlib.import_module("record_source")
    session = {
        "schema_version": 1,
        "run_id": f"run-{run}",
        "chip_id": "CHIP",
        "target_id": "dut",
        "source_revision": source_revision or f"source-{run}",
        "source_dirty": False,
        "spec_sha256": store.digest(b"synthetic method"),
        "finished_at": f"2026-09-08T01:{run:02d}:00Z",
        "exitstatus": 0 if status == "PASS" else 1,
    }
    selection = {
        "case_id": case.lower(),
        "parameter_id": parameter,
        "method": "Read and compare.",
        "pass_criteria": "Exact equality.",
    }
    result = {
        "schema_version": 1,
        "run_id": session["run_id"],
        "case_run_id": f"case-{run}",
        "case_id": case.lower(),
        "ip_id": "test",
        "parameter_id": parameter,
        "status": status,
        "observations": [],
        "artifacts": {},
    }
    data = {
        "source/session.json": store.json_bytes(session),
        "source/result.json": store.json_bytes(result),
        "source/specification.md": b"synthetic method",
    }
    blobs = {store.digest(value): value for value in data.values()}
    snapshot = model.Snapshot(
        lane,
        session,
        result,
        selection,
        {name: store.digest(value) for name, value in data.items()},
        f"tmp/run-{run}",
    )
    return source.RecordInput("CHIP", "TEST", {case: [snapshot]}, blobs)


def update(store: ModuleType, repository: Path, value: object) -> tuple[Path, int]:
    root = store.record_root(repository, "CHIP", "TEST")
    work = store.working_root(repository, "CHIP", "TEST")
    _, files = store.prepare_update(root, value)
    return root, store.publish_update(root, work, files)


# 测试方法：逆字典序添加参数再读回JSON；通过条件：生成的Markdown/Excel仍逐字一致。
def test_multiple_parameter_view_is_stable_after_json_roundtrip(
    store: ModuleType, tmp_path: Path
) -> None:
    checker = importlib.import_module("record_check")
    update(store, tmp_path, incoming(store, 1, parameter="z"))
    root, _ = update(store, tmp_path, incoming(store, 2, parameter="a"))
    assert checker.check_records(root)["status"] == "PASS"


# 测试方法：依次更新两个参数，再重导同一执行；通过条件：未测参数不变且重复导入无写入。
def test_partial_update_preserves_unexecuted_parameter_and_is_idempotent(
    store: ModuleType, tmp_path: Path
) -> None:
    update(store, tmp_path, incoming(store, 1))
    root, _ = update(store, tmp_path, incoming(store, 2, parameter="b"))
    before = {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }
    _, count = update(store, tmp_path, incoming(store, 2, parameter="b"))
    assert count == 0
    assert before == {
        path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()
    }
    view = store.build_view(store.load_records(root)[0])
    assert [row["source_revision"] for row in view["executions"]] == ["source-1", "source-2"]
    assert {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir()} == {
        "cases",
        "evidence",
    }


# 测试方法：FAIL后PASS；通过条件：当前状态更新为PASS，失败原始字节仍可校验。
def test_failure_evidence_is_protected_after_recovery(store: ModuleType, tmp_path: Path) -> None:
    failed = incoming(store, 1, status="FAIL")
    update(store, tmp_path, failed)
    root, _ = update(store, tmp_path, incoming(store, 2))
    records, blobs = store.load_records(root)
    record = records["TEST_P0_001"]
    assert len(record.payload["protected"]) == 2
    assert record.payload["protected"][0]["result"]["status"] == "FAIL"
    assert store.build_view(records)["executions"][0]["status"] == "PASS"
    assert set(failed.blobs) <= set(blobs["TEST_P0_001"])


# 测试方法：只复测Case1；通过条件：Case2文档和证据字节均不改变。
def test_update_does_not_touch_other_cases_or_manual_analysis(
    store: ModuleType, tmp_path: Path
) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    update(store, tmp_path, incoming(store, 1, case="TEST_P0_002"))
    path = root / "cases/TEST_P0_001.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n人工分析：保留此句。\n", encoding="utf-8")
    before = (root / "cases/TEST_P0_002.md").read_bytes()
    update(store, tmp_path, incoming(store, 2, status="FAIL"))
    assert (root / "cases/TEST_P0_002.md").read_bytes() == before
    assert "人工分析：保留此句。" in path.read_text(encoding="utf-8")


# 测试方法：以旧Run和冲突内容更新；通过条件：拒绝倒退或同身份改写。
def test_rejects_older_and_conflicting_evidence(store: ModuleType, tmp_path: Path) -> None:
    update(store, tmp_path, incoming(store, 2))
    with pytest.raises(ValueError, match="older evidence"):
        update(store, tmp_path, incoming(store, 1))
    with pytest.raises(ValueError, match="conflicting content"):
        update(store, tmp_path, incoming(store, 2, status="FAIL"))


# 测试方法：同Case分别导入FPGA和SIL；通过条件：结果并列而非互相覆盖。
def test_lanes_remain_separate(store: ModuleType, tmp_path: Path) -> None:
    update(store, tmp_path, incoming(store, 1, status="FAIL"))
    root, _ = update(store, tmp_path, incoming(store, 2, lane="sil"))
    rows = store.build_view(store.load_records(root)[0])["executions"]
    assert {(row["lane"], row["status"]) for row in rows} == {("fpga", "FAIL"), ("sil", "PASS")}


# 测试方法：降低测试用容量上限；通过条件：更新拒绝，已发布数据保持原样。
def test_capacity_failure_keeps_existing_files(
    store: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    before = (root / "results.json").read_bytes()
    monkeypatch.setattr(store, "MAX_CASE_BYTES", 1)
    with pytest.raises(ValueError, match="capacity|exceeds"):
        update(store, tmp_path, incoming(store, 2))
    assert (root / "results.json").read_bytes() == before


# 测试方法：删除附件包和修改Canonical摘要；通过条件：缺失与不一致均被拒绝。
def test_corrupt_evidence_is_not_silently_replaced(store: ModuleType, tmp_path: Path) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    path = root / "evidence/TEST_P0_001.json"
    payload = store.json_object(path.read_bytes())
    next(iter(payload["executions"].values()))["latest"]["result"]["status"] = "FAIL"
    next(iter(payload["executions"].values()))["status_counts"] = {"FAIL": 1}
    path.write_bytes(store.json_bytes(payload))
    with pytest.raises(ValueError, match="Result bytes"):
        store.load_records(root)


# 测试方法：连续20轮通过；通过条件：目录和文件数量固定，累计次数增加。
def test_repeated_passes_keep_fixed_file_count(store: ModuleType, tmp_path: Path) -> None:
    for run in range(1, 21):
        root, _ = update(store, tmp_path, incoming(store, run))
    assert len([path for path in root.rglob("*") if path.is_file()]) == 6
    row = store.build_view(store.load_records(root)[0])["executions"][0]
    assert row["attempts"] == 20
    assert row["status_counts"] == {"PASS": 20}


# 测试方法：同一源码和现象连续失败20次；通过条件：只保留一个历史复现，次数完整增加。
def test_repeated_identical_failures_do_not_grow_protection(
    store: ModuleType, tmp_path: Path
) -> None:
    for run in range(1, 21):
        root, _ = update(
            store, tmp_path, incoming(store, run, status="FAIL", source_revision="baseline")
        )
    record = store.load_records(root)[0]["TEST_P0_001"]
    assert len(record.payload["protected"]) == 1
    assert store.build_view({"TEST_P0_001": record})["executions"][0]["status_counts"] == {
        "FAIL": 20
    }


# 测试方法：失败、恢复通过、再次通过；通过条件：首次恢复通过和原失败均仍受保护。
def test_first_recovery_pass_is_retained(store: ModuleType, tmp_path: Path) -> None:
    update(store, tmp_path, incoming(store, 1, status="FAIL"))
    update(store, tmp_path, incoming(store, 2))
    root, _ = update(store, tmp_path, incoming(store, 3))
    protected = store.load_records(root)[0]["TEST_P0_001"].payload["protected"]
    assert [(item["session"]["run_id"], item["result"]["status"]) for item in protected] == [
        ("run-1", "FAIL"),
        ("run-2", "PASS"),
    ]


# 测试方法：显式保护基线后更新；通过条件：旧PASS仍可追溯，不能保护本次未选Case。
def test_explicit_baseline_protection(store: ModuleType, tmp_path: Path) -> None:
    root = store.record_root(tmp_path, "CHIP", "TEST")
    work = store.working_root(tmp_path, "CHIP", "TEST")
    value = incoming(store, 1)
    _, files = store.prepare_update(root, value, protect_cases=("TEST_P0_001",))
    store.publish_update(root, work, files)
    update(store, tmp_path, incoming(store, 2))
    assert (
        store.load_records(root)[0]["TEST_P0_001"].payload["protected"][0]["session"]["run_id"]
        == "run-1"
    )
    with pytest.raises(ValueError, match="selected in this input"):
        store.prepare_update(root, value, protect_cases=("TEST_P0_999",))


# 测试方法：篡改累计计数或JSON重复键；通过条件：拒绝含糊或内部不一致的结果。
def test_invalid_counters_and_duplicate_json_are_rejected(
    store: ModuleType, tmp_path: Path
) -> None:
    root, _ = update(store, tmp_path, incoming(store, 1))
    path = root / "evidence/TEST_P0_001.json"
    payload = store.json_object(path.read_bytes())
    entry = next(iter(payload["executions"].values()))
    entry["status_counts"] = {"FAIL": 1}
    path.write_bytes(store.json_bytes(payload))
    with pytest.raises(ValueError, match="not represented"):
        store.load_records(root)
    with pytest.raises(ValueError, match="duplicate JSON key"):
        store.json_object(b'{"value":{"status":"PASS","status":"FAIL"}}')
