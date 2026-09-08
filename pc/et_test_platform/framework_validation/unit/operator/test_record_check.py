# Markdown知识的静态边界回归。
# 职责：验证身份、适用版本、正文、链接和最小附件，不依赖原始ZIP。
# 边界：格式通过不等于根因或硬件结论通过。
# 依赖：pytest和合成知识工厂。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import make_knowledge


@pytest.fixture
def checker(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    return importlib.import_module("record_check")


# 测试方法：纯Markdown目录校验后追加带时间的认知修正；通过条件：保留旧判断且不需要JSON或ZIP。
def test_check_accepts_distilled_knowledge_and_corrections(
    checker: ModuleType, tmp_path: Path
) -> None:
    path = make_knowledge(tmp_path, finding="旧判断：原因可能是写保护，未证实。")
    before = path.read_bytes()
    path.write_bytes(
        before + "\n2026-09-08 15:10 CST 修正：新证据不支持旧判断，仍未关闭。\n".encode()
    )
    result = checker.check_records(path.parent.parent)
    assert result["case_count"] == 1
    assert result["legacy_count"] == 0
    assert "not root-cause" in result["check"]
    assert path.read_bytes().startswith(before)
    assert len(list(path.parent.parent.rglob("*.json"))) == 0


# 测试方法：分别破坏Case身份、芯片、Lane、版本、时间或正文；通过条件：明确拒绝。
@pytest.mark.parametrize(
    "old,new",
    [
        ("# CRC_P1_001", "# CRC_P1_002"),
        ("ET6801 /", "OTHER /"),
        ("/ FPGA", "/ 未知通道"),
        ("源码 aaaaaaaa（clean），bitstream版本未知。", "未标明。"),
        ("2026-09-08 15:00 CST", "未注明时间"),
        ("## 问题与处理\n\n", ""),
    ],
)
def test_check_rejects_missing_identity_and_context(
    checker: ModuleType, tmp_path: Path, old: str, new: str
) -> None:
    path = make_knowledge(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError):
        checker.check_records(path.parent.parent)


# 测试方法：请求不存在或旧机器Case；通过条件：不能作为已整理知识放行。
def test_explicit_check_requires_every_curated_case(checker: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    with pytest.raises(ValueError, match="missing Case"):
        checker.check_records(root, cases=("CRC_P1_999",))
    path.write_text("# CRC_P1_001\n<!-- ET_RECORD_AUTO_BEGIN -->\n", encoding="utf-8")
    assert checker.check_records(root)["legacy_count"] == 1
    with pytest.raises(ValueError, match="legacy"):
        checker.check_records(root, cases=("CRC_P1_001",))


# 测试方法：附件链接显式引用一个本Case文件；通过条件：只绑定这个附件，不复制旁边日志。
def test_check_binds_only_explicit_minimal_attachment(checker: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    asset = root / "attachments/CRC_P1_001/trace.txt"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"required trace")
    (asset.parent / "unused.log").write_bytes(b"not part of knowledge")
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n必要依据：[波形](../attachments/CRC_P1_001/trace.txt)\n",
        encoding="utf-8",
    )
    files = checker.check_records(root)["files"]
    assert set(files) == {"cases/CRC_P1_001.md", "attachments/CRC_P1_001/trace.txt"}


# 测试方法：缺失链接、缺失锚点或仓库外路径；通过条件：失败关闭，不访问外部文件。
@pytest.mark.parametrize(
    "link",
    ["missing.md", "../../../../../../outside.txt", "file:///etc/passwd", "reference.md#absent"],
)
def test_check_rejects_invalid_links(checker: ModuleType, tmp_path: Path, link: str) -> None:
    path = make_knowledge(tmp_path)
    (path.parent / "reference.md").write_text("# Reference\n", encoding="utf-8")
    path.write_text(path.read_text(encoding="utf-8") + f"\n[依据]({link})\n", encoding="utf-8")
    with pytest.raises(ValueError):
        checker.check_records(path.parent.parent, cases=("CRC_P1_001",))


# 测试方法：知识正文超出边界；通过条件：提示提炼，不自动截断。
def test_check_rejects_oversized_knowledge(checker: ModuleType, tmp_path: Path) -> None:
    path = make_knowledge(tmp_path, finding="x" * 17000)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="16 KiB"):
        checker.check_records(path.parent.parent)
    assert path.read_bytes() == before


# 测试方法：两个附件各自未超限但合计超限；通过条件：拒绝总量超限且不计重复链接两次。
def test_attachment_budget_is_per_case(
    checker: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = make_knowledge(tmp_path)
    root = path.parent.parent
    assets = root / "attachments/CRC_P1_001"
    assets.mkdir(parents=True)
    (assets / "a.txt").write_bytes(b"123456")
    (assets / "b.txt").write_bytes(b"123456")
    monkeypatch.setattr(checker, "MAX_ATTACHMENT_BYTES", 10)
    original = path.read_text(encoding="utf-8")
    link = "\n[依据](../attachments/CRC_P1_001/a.txt)\n"
    path.write_text(original + link * 2, encoding="utf-8")
    checker.check_records(root)
    path.write_text(original + link + link.replace("a.txt", "b.txt"), encoding="utf-8")
    with pytest.raises(ValueError, match="in total"):
        checker.check_records(root)
