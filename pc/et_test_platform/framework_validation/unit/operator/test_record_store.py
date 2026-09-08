# Case知识索引的无硬件回归。
# 职责：验证索引幂等、人工正文保护和旧记录兼容边界。
# 边界：使用合成知识，不形成芯片验证结论。
# 依赖：标准库、pytest和知识工具。

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


def make_knowledge(
    repository: Path,
    *,
    case: str = "CRC_P1_001",
    chip: str = "ET6801",
    ip: str = "CRC",
    finding: str = "当前问题未关闭，尚无已验证修复。",
) -> Path:
    path = repository / f"artifacts/records/{chip}/{ip}/cases/{case}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# {case} — 合成知识\n\n"
        f"适用基线：{chip} / FPGA；源码 aaaaaaaa（clean），bitstream版本未知。\n\n"
        "整理时间：2026-09-08 15:00 CST。\n\n"
        f"## 问题与处理\n\n{finding}\n",
        encoding="utf-8",
    )
    return path


# 测试方法：重复更新索引20次；通过条件：Case字节和mtime均不变，无JSON/ZIP/计数副本。
def test_index_is_idempotent_and_never_rewrites_case(store: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    before = path.read_bytes(), path.stat().st_mtime_ns
    root = store.record_root(tmp_path, "ET6801", "crc")
    work = store.working_root(tmp_path, "ET6801", "crc")
    assert store.refresh_index(root, work) == 1
    for _ in range(20):
        assert store.refresh_index(root, work) == 0
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()} == {
        "README.md",
        "cases/CRC_P1_001.md",
    }


# 测试方法：索引外追加人工说明后新增Case；通过条件：人工说明及旧Case保持不变。
def test_index_preserves_manual_notes_and_other_cases(store: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    work = store.working_root(tmp_path, "ET6801", "crc")
    store.refresh_index(root, work)
    index = root / "README.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\n人工备注：不能删除。\n", encoding="utf-8"
    )
    before = path.read_bytes()
    make_knowledge(tmp_path, case="CRC_P1_002")
    store.refresh_index(root, work)
    assert path.read_bytes() == before
    assert "人工备注：不能删除。" in index.read_text(encoding="utf-8")
    assert "CRC_P1_002" in index.read_text(encoding="utf-8")


# 测试方法：旧自动记录与旧ZIP仍在目录中；通过条件：仅提示待迁移，不读写或复制旧证据。
def test_index_preserves_legacy_evidence_bytes(store: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    legacy = root / "cases/CRC_P1_002.md"
    legacy.write_text(
        "# CRC_P1_002\n" + store.BEGIN + "\n旧机器记录\n" + store.END, encoding="utf-8"
    )
    evidence = root / "evidence"
    evidence.mkdir()
    (evidence / "CRC_P1_002.zip").write_bytes(b"opaque old bytes")
    before = legacy.read_bytes(), (evidence / "CRC_P1_002.zip").read_bytes()
    store.refresh_index(root, store.working_root(tmp_path, "ET6801", "crc"))
    assert "另有1份旧自动记录待提炼" in (root / "README.md").read_text(encoding="utf-8")
    assert before == (legacy.read_bytes(), (evidence / "CRC_P1_002.zip").read_bytes())


# 测试方法：索引标记损坏；通过条件：拒绝替换，不吞掉已有人工内容。
def test_index_rejects_broken_markers(store: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    (root / "README.md").write_text("人工索引，不可自动覆盖", encoding="utf-8")
    with pytest.raises(ValueError, match="markers"):
        store.refresh_index(root, store.working_root(tmp_path, "ET6801", "crc"))
    assert (root / "README.md").read_text(encoding="utf-8") == "人工索引，不可自动覆盖"


# 测试方法：三份已审核样稿在隔离目录模拟五种贡献场景；通过条件：检查与索引不篡改知识。
@pytest.mark.parametrize("case", ["CAN_P0_001", "CAN_P1_020", "CAN_P2_003"])
def test_can_samples_support_distillation_without_legacy_packages(
    store: ModuleType, tmp_path: Path, case: str
) -> None:
    repository = Path(__file__).resolve().parents[5]
    source = repository / f"report/plans/20260908_case_knowledge_samples/{case.lower()}.md"
    original = source.read_bytes()
    path = make_knowledge(tmp_path, case=case, ip="CAN")
    path.write_text(
        original.decode("utf-8").replace(
            "../../../test_case_doc/", "../../../../../test_case_doc/"
        ),
        encoding="utf-8",
    )
    reference_root = tmp_path / "test_case_doc/can"
    reference_root.mkdir(parents=True)
    for name in ("can.md", "ET6801_can.md"):
        (reference_root / name).write_bytes((repository / "test_case_doc/can" / name).read_bytes())
    root = path.parent.parent
    work = store.working_root(tmp_path, "ET6801", "can")
    before = path.read_bytes()
    assert store.refresh_index(root, work) == 1  # 首次贡献。
    assert store.refresh_index(root, work) == 0  # 同输入重复。
    assert path.read_bytes() == before
    for addition in (
        "补证演练：新增观察仍需核对版本，原判断保留。",
        "修复演练：仅一个参数通过，覆盖不足，不能关闭原问题。",
        "修正演练：新证据推翻旧解释；保留旧判断及时间，不作为已验证根因。",
    ):
        before = path.read_bytes()
        path.write_bytes(before + f"\n2026-09-08 15:20 CST {addition}\n".encode())
        contributed = path.read_bytes()
        store.refresh_index(root, work)
        assert path.read_bytes() == contributed and contributed.startswith(before)
    assert source.read_bytes() == original
    assert not list(root.rglob("*.json")) and not list(root.rglob("*.zip"))
