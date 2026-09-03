# J-Link DebugController 无硬件测试。
#
# 职责：验证固定 Halt/Resume 命令、参数边界和 Artifact 日志行为。
# 边界：不启动真实 J-Link，不连接探针，也不操作真实 CPU。
# 依赖：pytest、subprocess替身和公共 JLinkDebugController。

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.core.errors import TransportError
from et_test_platform.programmers import DebugController, HaltSampleSpec, JLinkDebugController


# 地址是虚拟测试输入，不绑定任一芯片；Fixture不访问真实探针。
@pytest.fixture
def sampler(tmp_path):
    executable = tmp_path / "JLink.exe"
    executable.write_bytes(b"tool")
    return JLinkDebugController(
        executable=executable,
        device="test-core",
        interface="JTAG",
        speed_khz=1000,
        probe_serial="123",
        artifact_dir=tmp_path,
    )


# 严格按本次命令中的mem32生成响应；测试可改变状态或删除读数以模拟故障。
def sample_output(command: str, *, halted: bool = True, resumed: bool = True) -> bytes:
    lines = []
    sampling = "halt" in command.splitlines()
    after_go = False
    counter = 10
    for line in command.splitlines():
        if line == "go":
            after_go = True
        if line.startswith("mem32 "):
            _, address, count = line.split()
            assert count == "1"
            value = counter
            if int(address, 16) == 0x1000:
                value = 0 if (after_go and resumed) or not sampling or not halted else 2
            lines.append(f"{int(address, 16):08X} = {value:08X}")
            counter += 1
    return ("\r\n".join(lines) + "\r\n").encode()


# 完整采样只使用一个会话，四次状态证明采样窗口停核，结束后状态证明CPU恢复。
def test_halted_samples_are_read_before_go(sampler, monkeypatch):
    commands = []

    def run(arguments, **kwargs):
        command = Path(arguments[arguments.index("-CommandFile") + 1]).read_text()
        commands.append(command)
        assert kwargs["timeout"] == 10.25
        return SimpleNamespace(returncode=0, stdout=sample_output(command), stderr=b"")

    monkeypatch.setattr("et_test_platform.programmers.debugger.subprocess.run", run)
    result = sampler.sample_while_halted(HaltSampleSpec(0x1000, 2, (0x2000, 0x2004)), 0.25)
    assert len(commands) == 1
    assert commands[0].count("halt\n") == 1
    assert "Sleep 250" in commands[0]
    assert commands[0].endswith("go\nmem32 0x00001000 1\nexit\n")
    assert result.before == (11, 12)
    assert result.after == (15, 16)
    assert result.halt_status == (2, 2, 2, 2)
    assert result.resumed_status == 0
    assert result.interval_s == 0.25


# 无效配置在执行任何工具命令之前被拒绝，不能把开放字符串拼进Commander脚本。
@pytest.mark.parametrize(
    "spec,duration",
    [
        (HaltSampleSpec(0x1001, 2, (0x2000,)), 0.2),
        (HaltSampleSpec(0x1000, 0, (0x2000,)), 0.2),
        (HaltSampleSpec(0x1000, 2, ()), 0.2),
        (HaltSampleSpec(0x1000, 2, (-4,)), 0.2),
        (HaltSampleSpec(0x1000, 2, (True,)), 0.2),
        (HaltSampleSpec(0x1000, 2, (0x2000,)), float("nan")),
        (HaltSampleSpec(0x1000, 2, (0x2000,)), 0),
    ],
)
def test_halted_sample_rejects_invalid_input(sampler, spec, duration, monkeypatch):
    monkeypatch.setattr(
        "et_test_platform.programmers.debugger.subprocess.run",
        lambda *args, **kwargs: pytest.fail("must not execute"),
    )
    with pytest.raises(ValueError):
        sampler.sample_while_halted(spec, duration)


# 状态不符、读数缺失、工具失败与中断都保留原始错误，并尝试一次确认式恢复。
@pytest.mark.parametrize(
    "fault", ["running", "missing", "not_resumed", "exit", "timeout", "interrupt"]
)
def test_halted_sample_failures_recover_without_resampling(sampler, monkeypatch, fault):
    commands = []

    def run(arguments, **kwargs):
        command = Path(arguments[arguments.index("-CommandFile") + 1]).read_text()
        commands.append(command)
        if len(commands) == 1:
            if fault == "timeout":
                raise subprocess.TimeoutExpired(arguments, kwargs["timeout"])
            if fault == "interrupt":
                raise KeyboardInterrupt()
            output = sample_output(
                command, halted=fault != "running", resumed=fault != "not_resumed"
            )
            if fault == "missing":
                output = output.split(b"\r\n", 1)[1]
            return SimpleNamespace(
                returncode=1 if fault == "exit" else 0, stdout=output, stderr=b""
            )
        return SimpleNamespace(returncode=0, stdout=sample_output(command), stderr=b"")

    monkeypatch.setattr("et_test_platform.programmers.debugger.subprocess.run", run)
    with pytest.raises(KeyboardInterrupt if fault == "interrupt" else TransportError):
        sampler.sample_while_halted(HaltSampleSpec(0x1000, 2, (0x2000,)), 0.25)
    assert len(commands) == 2
    assert commands[1] == "go\nmem32 0x00001000 1\nexit\n"


# 恢复失败不会盖掉最初的采样错误，也不会进入重试循环。
def test_halted_sample_preserves_recovery_failure(sampler, monkeypatch):
    monkeypatch.setattr(
        "et_test_platform.programmers.debugger.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=b"", stderr=b"lost"),
    )
    with pytest.raises(TransportError) as caught:
        sampler.sample_while_halted(HaltSampleSpec(0x1000, 2, (0x2000,)), 0.25)
    assert "resume recovery also failed" in caught.value.__notes__[0]


# 验证控制器只生成受控halt/go/hold脚本，并把工具输出保存在调用方Artifact目录。
def test_jlink_debug_controller_emits_controlled_debug_actions(tmp_path, monkeypatch) -> None:
    executable = tmp_path / "JLink.exe"
    executable.write_bytes(b"tool")
    invocations: list[list[str]] = []

    def run(arguments, **kwargs):
        del kwargs
        invocations.append(list(arguments))
        return SimpleNamespace(returncode=0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr("et_test_platform.programmers.debugger.subprocess.run", run)
    controller = JLinkDebugController(
        executable=executable,
        device="Cortex-M7",
        interface="JTAG",
        speed_khz=1000,
        probe_serial="123",
        artifact_dir=tmp_path / "artifacts",
    )

    assert isinstance(controller, DebugController)

    halted = controller.halt()
    resumed = controller.resume()
    held = controller.hold_for(0.25)

    assert (tmp_path / "artifacts/debug_01_halt.jlink").read_text(encoding="ascii") == (
        "halt\nexit\n"
    )
    assert (tmp_path / "artifacts/debug_02_resume.jlink").read_text(encoding="ascii") == (
        "go\nexit\n"
    )
    assert (tmp_path / "artifacts/debug_03_hold.jlink").read_text(encoding="ascii") == (
        "halt\nSleep 250\ngo\nexit\n"
    )
    assert halted.stdout_path.read_bytes() == b"ok"
    assert resumed.action == "resume"
    assert held.action == "hold"
    assert held.requested_hold_s == 0.25
    assert all("-ExitOnError" in invocation for invocation in invocations)
    assert all(
        invocation[invocation.index("-JTAGConf") + 1] == "-1,-1" for invocation in invocations
    )
    assert all("-SelectEmuBySN" in invocation for invocation in invocations)
