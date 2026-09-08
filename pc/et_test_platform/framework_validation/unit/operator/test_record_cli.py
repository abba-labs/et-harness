# 维护命令的无硬件回归。
# 职责：验证更新入口、预览与执行分离、损坏目录拒绝更新和身份校验。
# 边界：使用合成输入，不运行Case或连接设备。
# 依赖：pytest和相邻数据工厂。

from __future__ import annotations

import importlib
from pathlib import Path
from types import ModuleType

import pytest

from .test_record_store import incoming, update


@pytest.fixture
def cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ModuleType:
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    module = importlib.import_module("maintain_test_records")
    monkeypatch.setattr(module, "REPOSITORY_ROOT", tmp_path)
    return module


# 测试方法：更新两次同一执行后检查；通过条件：首次发布、再次幂等且入口只写固定目录。
def test_cli_update_is_idempotent(
    cli: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = importlib.import_module("record_store")
    value = incoming(store, 1)
    monkeypatch.setattr(cli, "load_input", lambda *args, **kwargs: value)
    arguments = [
        "update",
        "--chip",
        "CHIP",
        "--ip",
        "TEST",
        "--source",
        str(tmp_path),
        "--lane",
        "fpga",
    ]
    assert cli.main(arguments) == 0
    result = cli.run_operation(cli._arguments(arguments), tmp_path)
    assert result["changed_files"] == 0
    assert cli.main(["check", "--chip", "CHIP", "--ip", "TEST"]) == 0


# 测试方法：从CLI归档后预览、执行释放；通过条件：预览不改变受保护快照，执行才释放。
def test_cli_prune_requires_execute(cli: ModuleType, tmp_path: Path) -> None:
    store = importlib.import_module("record_store")
    update(store, tmp_path, incoming(store, 1, status="FAIL"))
    root, _ = update(store, tmp_path, incoming(store, 2))
    common = ["--chip", "CHIP", "--ip", "TEST"]
    output = tmp_path / "milestone.zip"
    assert cli.main(["archive", *common, "--output", str(output)]) == 0
    arguments = ["prune", *common, "--archive", str(output), "--case", "TEST_P0_001"]
    before = (root / "evidence/TEST_P0_001.json").read_bytes()
    assert cli.main(arguments) == 0
    assert (root / "evidence/TEST_P0_001.json").read_bytes() == before
    assert cli.main([*arguments, "--execute"]) == 0
    assert store.load_records(root)[0]["TEST_P0_001"].payload["protected"] == []


# 测试方法：破坏当前索引后请求更新；通过条件：拒绝，不用新结果掩盖损坏。
def test_cli_rejects_damaged_existing_view(cli: ModuleType, tmp_path: Path) -> None:
    store = importlib.import_module("record_store")
    root, _ = update(store, tmp_path, incoming(store, 1))
    path = root / "results.json"
    path.write_bytes(b"damaged")
    assert (
        cli.main(
            [
                "update",
                "--chip",
                "CHIP",
                "--ip",
                "TEST",
                "--source",
                str(tmp_path),
                "--lane",
                "fpga",
            ]
        )
        == 1
    )
    assert path.read_bytes() == b"damaged"


# 测试方法：请求不同芯片目录；通过条件：Session身份不匹配时不发布结果。
def test_cli_rejects_wrong_chip(
    cli: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = importlib.import_module("record_store")
    monkeypatch.setattr(cli, "load_input", lambda *args, **kwargs: incoming(store, 1))
    assert (
        cli.main(
            [
                "update",
                "--chip",
                "OTHER",
                "--ip",
                "TEST",
                "--source",
                str(tmp_path),
                "--lane",
                "fpga",
            ]
        )
        == 1
    )
    assert not store.record_root(tmp_path, "OTHER", "TEST").exists()


# 测试方法：关闭再开启Excel并重复同一输入；通过条件：次数不变，JSON/MD始终存在。
def test_cli_report_toggle_preserves_records(
    cli: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = importlib.import_module("record_store")
    value = incoming(store, 1)
    monkeypatch.setattr(cli, "load_input", lambda *args, **kwargs: value)
    kwargs = {"chip": "CHIP", "ip": "TEST", "lane": "fpga"}
    cli.update_records(tmp_path, tmp_path, **kwargs)
    result = cli.update_records(tmp_path, tmp_path, **kwargs, write_report=False)
    root = store.record_root(tmp_path, "CHIP", "TEST")
    assert not (root / "test_report.xlsx").exists()
    assert (root / "results.json").is_file() and (root / "README.md").is_file()
    assert result["file_count"] == 5
    assert (
        cli.update_records(tmp_path, tmp_path, **kwargs, write_report=False)["changed_files"] == 0
    )
    cli.update_records(tmp_path, tmp_path, **kwargs)
    assert (root / "test_report.xlsx").is_file()
    view = store.build_view(store.load_records(root)[0])
    assert view["executions"][0]["attempts"] == 1


# 测试方法：真实样本导入后封存工作区；通过条件：全部原始文件都被发布证明覆盖。
def test_cli_returns_exact_workspace_proof(cli: ModuleType, tmp_path: Path) -> None:
    from .test_record_source import make_session

    source = importlib.import_module("record_source")
    workspace = importlib.import_module("record_workspace")
    run = make_session(source, tmp_path)
    current = tmp_path / "artifacts/runs/current/tests/crc"
    current.parent.mkdir(parents=True)
    run.rename(current)
    result = cli.update_records(tmp_path, current, chip="ET6801", ip="crc", lane="fpga")
    workspace.seal_workspace(
        tmp_path, current, proofs=result["_proofs"], expected_files=result["_source_files"]
    )
    workspace.verify_publication(tmp_path, current)


# 测试方法：CLI显式归档中断工作区；通过条件：现场保留且可以校验归档回执。
def test_cli_archives_interrupted_workspace(cli: ModuleType, tmp_path: Path) -> None:
    workspace = importlib.import_module("record_workspace")
    root = tmp_path / "artifacts/runs/current"
    root.mkdir(parents=True)
    (root / "pipeline.log").write_bytes(b"interrupted")
    output = tmp_path / "milestone.zip"
    assert cli.main(["archive", "--workspace", str(root), "--output", str(output)]) == 0
    workspace.verify_publication(tmp_path, root)
    assert (root / "pipeline.log").read_bytes() == b"interrupted"


# 测试方法：同时指定两种归档对象；通过条件：参数解析拒绝歧义。
def test_cli_rejects_ambiguous_archive(cli: ModuleType) -> None:
    with pytest.raises(SystemExit):
        cli._arguments(["archive", "--workspace", "current", "--chip", "CHIP", "--output", "a.zip"])


# 测试方法：显式重建损坏的派生文字；通过条件：原始证据和人工分析不变，完整检查恢复。
def test_cli_refreshes_only_derived_views(cli: ModuleType, tmp_path: Path) -> None:
    store = importlib.import_module("record_store")
    root, _ = update(store, tmp_path, incoming(store, 1))
    evidence = {path.name: path.read_bytes() for path in (root / "evidence").iterdir()}
    path = root / "cases/TEST_P0_001.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("## 当前测试", "## 损坏的旧视图")
        + "\n人工分析保留。\n",
        encoding="utf-8",
    )
    common = ["check", "--chip", "CHIP", "--ip", "TEST"]
    assert cli.main(common) == 1
    assert cli.main([*common, "--refresh-views"]) == 0
    assert "人工分析保留。" in path.read_text(encoding="utf-8")
    assert evidence == {path.name: path.read_bytes() for path in (root / "evidence").iterdir()}


# 测试方法：原始附件包损坏时请求重建；通过条件：拒绝，不能以派生重建绕过证据检查。
def test_cli_refresh_rejects_broken_raw_evidence(cli: ModuleType, tmp_path: Path) -> None:
    store = importlib.import_module("record_store")
    root, _ = update(store, tmp_path, incoming(store, 1))
    (root / "evidence/TEST_P0_001.zip").write_bytes(b"broken")
    before = (root / "results.json").read_bytes()
    assert cli.main(["check", "--chip", "CHIP", "--ip", "TEST", "--refresh-views"]) == 1
    assert (root / "results.json").read_bytes() == before
