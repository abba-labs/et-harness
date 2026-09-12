# Peer Mailbox诊断工作区回归。
# 职责：验证现场保护、失败日志、成功回执和显式路径限制。
# 边界：仅临时目录与进程替身，不访问J-Link或真实设备。
# 依赖：pytest和既有诊断及工作区模块。

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repository = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(repository / "tools/runner"))
    module = importlib.import_module("ipcm_peer_mailbox_probe")
    monkeypatch.setattr(module, "REPOSITORY", tmp_path)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module


def _args() -> argparse.Namespace:
    return argparse.Namespace(label="unit", serial="123", jlink="fake-jlink")


def _sample(heartbeat: int) -> subprocess.CompletedProcess:
    output = f"Cortex-M7 identified\n20440000 = 45544331 00000001 00000002 {heartbeat:08X}\n"
    return subprocess.CompletedProcess([], 0, output.encode(), b"")


# 测试方法：成功采样、复用、再篡改日志；通过条件：成功可复用，Hash变化时不再启动探针。
def test_peer_diagnostic_seals_success_and_rejects_changed_workspace(probe, monkeypatch) -> None:
    samples = iter([_sample(1), _sample(2), _sample(3), _sample(4)])
    calls = []

    def run(argv, **kwargs):
        assert argv[0] == "fake-jlink" and kwargs["timeout"] == 30
        calls.append(argv)
        return next(samples)

    monkeypatch.setattr(probe.subprocess, "run", run)
    output = probe.REPOSITORY / probe.OUTPUT
    assert probe._probe(_args(), output) == 0
    first = json.loads(output.read_text())["run_id"]
    assert probe._probe(_args(), output) == 0
    assert json.loads(output.read_text())["run_id"] != first
    assert (output.parent / "publication.json").is_file()
    (output.parent / "peer_mailbox.stdout.log").write_text("external change")
    with pytest.raises(ValueError, match="changed after publication"):
        probe._probe(_args(), output)
    assert len(calls) == 4


# 测试方法：第二次采样分别超时/启动失败；通过条件：保留首次输出、失败JSON，禁止下次复用。
@pytest.mark.parametrize(
    "failure", [subprocess.TimeoutExpired("fake", 30, output=b"partial"), OSError("missing probe")]
)
def test_peer_diagnostic_preserves_failed_samples(probe, monkeypatch, failure) -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 2:
            raise failure
        return _sample(7)

    monkeypatch.setattr(probe.subprocess, "run", run)
    output = probe.REPOSITORY / probe.OUTPUT
    assert probe._probe(_args(), output) == 1
    assert b"00000007" in (output.parent / "peer_mailbox.stdout.log").read_bytes()
    assert json.loads(output.read_text())["error"]
    assert not (output.parent / "publication.json").exists()
    with pytest.raises(ValueError, match="unpublished"):
        probe._probe(_args(), output)
    assert len(calls) == 2


# 测试方法：给出原Pipeline输出位置；通过条件：拒绝且不创建任何诊断现场。
def test_peer_cli_rejects_pipeline_output(probe, monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "probe",
            "--label",
            "unit",
            "--serial",
            "123",
            "--confirm-hardware-actions",
            "--output",
            str(
                probe.REPOSITORY
                / "artifacts/records/ET6801/_PIPELINE/current/stages/peer_mailbox.json"
            ),
        ],
    )
    assert probe.main() == 1
    assert not (probe.REPOSITORY / "artifacts").exists()
