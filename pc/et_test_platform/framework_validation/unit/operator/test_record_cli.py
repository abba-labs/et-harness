# Case知识命令的端到端无硬件回归。
# 职责：验证当前事实准备、显式整理确认、只读检查和报告开关。
# 边界：工具不生成或改写人工Case知识，不操作硬件。
# 依赖：pytest和合成Canonical Session。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_source import make_session
from .test_record_store import make_knowledge


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    module = importlib.import_module("maintain_test_records")
    monkeypatch.setattr(module, "REPOSITORY_ROOT", tmp_path)
    return module


def current_session(tmp_path: Path) -> Path:
    source = importlib.import_module("record_source")
    original = make_session(source, tmp_path)
    current = tmp_path / "artifacts/runs/current/tests/crc"
    current.parent.mkdir(parents=True)
    original.rename(current)
    return current


# 测试方法：准备真实形状结果两次；通过条件：原始字节不变，只生成当前摘要/报告，不建长期记录。
def test_preparation_does_not_create_long_term_records(cli: ModuleType, tmp_path: Path) -> None:
    current = current_session(tmp_path)
    raw = {p.relative_to(current): p.read_bytes() for p in current.rglob("*") if p.is_file()}
    kwargs = {"chip": "ET6801", "ip": "crc", "lane": "fpga"}
    assert cli.prepare_review(tmp_path, current, **kwargs)["knowledge_review"] == "PENDING"
    second = cli.prepare_review(tmp_path, current, **kwargs)
    assert second["changed_files"] == 0
    assert not (tmp_path / "artifacts/records").exists()
    assert (current / "facts.md").is_file() and (current / "test_report.xlsx").is_file()
    assert not list(current.rglob("*.zip"))
    assert all((current / name).read_bytes() == value for name, value in raw.items())


# 测试方法：PASS后先只读check，再显式review；通过条件：check不解锁，review才放行且不改知识。
def test_review_requires_curated_knowledge_and_is_explicit(cli: ModuleType, tmp_path: Path) -> None:
    workspace = importlib.import_module("record_workspace")
    current = current_session(tmp_path)
    kwargs = {"chip": "ET6801", "ip": "crc", "lane": "fpga"}
    cli.prepare_review(tmp_path, current, **kwargs)
    with pytest.raises(ValueError, match="knowledge directory"):
        cli.review_records(tmp_path, current, **kwargs)
    path = make_knowledge(tmp_path)
    before = path.read_bytes()
    assert cli.main(["check", "--chip", "ET6801", "--ip", "crc"]) == 0
    with pytest.raises(workspace.KnowledgeReviewPending):
        workspace.prepare_workspace(tmp_path, current)
    cli.review_records(tmp_path, current, **kwargs)
    workspace.verify_publication(tmp_path, current)
    receipt = (current / "publication.json").read_bytes()
    cli.review_records(tmp_path, current, **kwargs)
    assert receipt == (current / "publication.json").read_bytes()
    assert path.read_bytes() == before
    assert cli.prepare_review(tmp_path, current, **kwargs)["knowledge_review"] == "REVIEWED"
    workspace.prepare_workspace(tmp_path, current)
    assert list(current.iterdir()) == [] and path.read_bytes() == before


# 测试方法：人工知识仍标问题未关闭，而本次Result是PASS；通过条件：工具不自动关闭或覆盖问题。
def test_first_pass_does_not_close_existing_issue(cli: ModuleType, tmp_path: Path) -> None:
    current = current_session(tmp_path)
    path = make_knowledge(tmp_path)
    before = path.read_bytes()
    kwargs = {"chip": "ET6801", "ip": "crc", "lane": "fpga"}
    cli.prepare_review(tmp_path, current, **kwargs)
    cli.review_records(tmp_path, current, **kwargs)
    assert path.read_bytes() == before
    assert "未关闭" in path.read_text(encoding="utf-8")


# 测试方法：关闭/开启当前Excel；通过条件：只改变当前派生文件，不创建长期报告和JSON副本。
def test_report_toggle_is_current_only(cli: ModuleType, tmp_path: Path) -> None:
    current = current_session(tmp_path)
    path = make_knowledge(tmp_path)
    before = path.read_bytes()
    kwargs = {"chip": "ET6801", "ip": "crc", "lane": "fpga"}
    cli.prepare_review(tmp_path, current, **kwargs, write_report=False)
    assert not (current / "test_report.xlsx").exists()
    cli.prepare_review(tmp_path, current, **kwargs, write_report=True)
    assert (current / "test_report.xlsx").is_file()
    cli.prepare_review(tmp_path, current, **kwargs, write_report=False)
    assert not (current / "test_report.xlsx").exists()
    assert path.read_bytes() == before
    assert not list(path.parent.parent.rglob("*.xlsx"))
    assert not list(path.parent.parent.rglob("*.json"))


# 测试方法：历史来源只提取，不允许准备/解锁；通过条件：历史字节和目录成员完全保留。
def test_historical_source_is_read_only(cli: ModuleType, tmp_path: Path) -> None:
    source = importlib.import_module("record_source")
    old = make_session(source, tmp_path)
    before = {p.relative_to(old): p.read_bytes() for p in old.rglob("*") if p.is_file()}
    assert (
        cli.main(
            [
                "extract",
                "--source",
                str(old),
                "--chip",
                "ET6801",
                "--ip",
                "crc",
                "--lane",
                "fpga",
                "--case",
                "CRC_P1_001",
            ]
        )
        == 0
    )
    for operation in (cli.prepare_review, cli.review_records):
        with pytest.raises(ValueError, match="historical"):
            operation(tmp_path, old, chip="ET6801", ip="crc", lane="fpga")
    assert before == {p.relative_to(old): p.read_bytes() for p in old.rglob("*") if p.is_file()}


# 测试方法：请求错误芯片、保留未绑定文件或篡改已封存来源；通过条件：停止，不掩盖现场。
@pytest.mark.parametrize("kind", ["chip", "unbound", "changed"])
def test_preparation_rejects_inconsistent_source(
    cli: ModuleType, tmp_path: Path, kind: str
) -> None:
    current = current_session(tmp_path)
    if kind == "changed":
        cli.prepare_review(tmp_path, current, chip="ET6801", ip="crc", lane="fpga")
        (current / "pytest.log").write_bytes(b"external edit")
    elif kind == "unbound":
        (current / "keep.txt").write_bytes(b"unbound")
    with pytest.raises(ValueError):
        cli.prepare_review(
            tmp_path, current, chip="OTHER" if kind == "chip" else "ET6801", ip="crc", lane="fpga"
        )
    if kind == "unbound":
        assert (current / "keep.txt").read_bytes() == b"unbound"
    if kind == "changed":
        assert (current / "pytest.log").read_bytes() == b"external edit"


# 测试方法：旧长期快照写命令和保护参数不再受理；通过条件：明确拒绝而不是静默继续生成包。
@pytest.mark.parametrize("command", ["update", "prune"])
def test_legacy_mutating_commands_are_retired(cli: ModuleType, command: str) -> None:
    with pytest.raises(SystemExit):
        cli._arguments([command, "--chip", "ET6801", "--ip", "crc"])


# 测试方法：索引发布被进程中断；通过条件：check不写入，显式index恢复事务且保留Case。
def test_explicit_index_recovers_interrupted_publication(cli: ModuleType, tmp_path: Path) -> None:
    transaction = importlib.import_module("record_transaction")
    path = make_knowledge(tmp_path)
    before = path.read_bytes()
    root = path.parent.parent
    work = cli.working_root(tmp_path, "ET6801", "crc")

    def interrupted() -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        transaction.publish(root, work, {"README.md": b"partial index"}, validate=interrupted)
    assert cli.main(["check", "--chip", "ET6801", "--ip", "crc"]) == 1
    assert (root / "README.md").read_bytes() == b"partial index"
    assert cli.main(["index", "--chip", "ET6801", "--ip", "crc"]) == 0
    assert "CRC_P1_001" in (root / "README.md").read_text(encoding="utf-8")
    assert not (work / "transaction.json").exists()
    assert path.read_bytes() == before
