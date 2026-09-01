# J-Link DebugController 无硬件测试。
#
# 职责：验证固定 Halt/Resume 命令、参数边界和 Artifact 日志行为。
# 边界：不启动真实 J-Link，不连接探针，也不操作真实 CPU。
# 依赖：pytest、subprocess替身和公共 JLinkDebugController。

from __future__ import annotations

from types import SimpleNamespace

from et_test_platform.programmers import DebugController, JLinkDebugController


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
