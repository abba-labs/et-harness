# 通用 Debugger Halt/Resume 控制接口与 J-Link Adapter。
#
# 职责：提供真实调试器暂停/恢复的芯片中立动作，并保存每次工具调用的时间和日志证据。
# 边界：不选择 DUT Feature、不执行烧录/擦除/复位、不解释 IP 状态，也不形成 PASS/FAIL。
# 依赖：仅依赖标准库、显式 Bench 配置和调用方提供的 Artifact 目录。

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..core.errors import TransportError


# 表示一次真实调试器动作及其独立时间线；日志路径位于当前 Case Artifact 目录。
@dataclass(frozen=True, slots=True)
class DebugAction:
    action: str
    started_s: float
    completed_s: float
    stdout_path: Path
    stderr_path: Path
    requested_hold_s: float | None = None


# 定义 Formal Case 可依赖的最小调试控制语义；实现不得把软件等待冒充 Debugger Halt。
@runtime_checkable
class DebugController(Protocol):
    # 返回稳定探针和目标身份，供 Case Evidence 关联真实调试刺激；不得启动工具进程。
    @property
    def identity(self) -> str: ...

    # 通过真实调试探针暂停目标 CPU，并返回工具执行时间线与日志位置。
    def halt(self) -> DebugAction: ...

    # 通过真实调试探针恢复目标 CPU，并返回工具执行时间线与日志位置。
    def resume(self) -> DebugAction: ...

    # 在同一调试会话内暂停目标指定时长并恢复，避免探针断开改变CPU暂停状态。
    def hold_for(self, duration_s: float) -> DebugAction: ...


# 通过 J-Link Commander 的固定 Halt/Go 命令实现公共 DebugController，不执行其他动作。
class JLinkDebugController:
    def __init__(
        self,
        *,
        executable: str | Path,
        device: str,
        interface: str,
        speed_khz: int,
        probe_serial: str | None,
        artifact_dir: str | Path,
        command_timeout_s: float = 10.0,
    ) -> None:
        self._executable = Path(executable)
        self._device = device
        self._interface = interface
        self._speed_khz = speed_khz
        self._probe_serial = probe_serial
        self._artifact_dir = Path(artifact_dir)
        self._command_timeout_s = command_timeout_s
        self._action_index = 0
        if (
            not device
            or not interface
            or speed_khz <= 0
            or command_timeout_s <= 0
            or not self._executable.is_file()
        ):
            raise ValueError("J-Link debugger configuration is incomplete or invalid")

    # 返回由工具路径、调试设备和探针序列号组成的稳定身份；不启动 J-Link 进程。
    @property
    def identity(self) -> str:
        serial = self._probe_serial or "auto"
        return f"jlink:{self._device}:{serial}"

    # 使用固定 halt 命令暂停 CPU；不执行 reset、loadfile、erase 或任何内存写入。
    def halt(self) -> DebugAction:
        return self._run_action("halt", "halt")

    # 使用固定 go 命令恢复 CPU；不执行 reset、loadfile、erase 或任何内存写入。
    def resume(self) -> DebugAction:
        return self._run_action("resume", "go")

    # 在一个J-Link Commander会话内完成Halt、保持和Go，保证暂停状态不会因进程退出丢失。
    def hold_for(self, duration_s: float) -> DebugAction:
        if duration_s <= 0.0:
            raise ValueError("debug hold duration must be positive")

        duration_ms = max(1, round(duration_s * 1000.0))
        return self._run_action(
            "hold",
            f"halt\nSleep {duration_ms}\ngo",
            requested_hold_s=duration_s,
            execution_timeout_s=self._command_timeout_s + duration_s,
        )

    # 生成受控命令文件并执行一次 J-Link Commander；失败时保留完整日志并明确上抛。
    def _run_action(
        self,
        action: str,
        command: str,
        *,
        requested_hold_s: float | None = None,
        execution_timeout_s: float | None = None,
    ) -> DebugAction:
        self._action_index += 1
        self._artifact_dir.mkdir(parents=True, exist_ok=True)
        stem = f"debug_{self._action_index:02d}_{action}"
        command_path = self._artifact_dir / f"{stem}.jlink"
        stdout_path = self._artifact_dir / f"{stem}.stdout.log"
        stderr_path = self._artifact_dir / f"{stem}.stderr.log"
        command_path.write_text(f"{command}\nexit\n", encoding="ascii")

        arguments = [
            str(self._executable),
            "-Device",
            self._device,
            "-If",
            self._interface,
            "-Speed",
            str(self._speed_khz),
            "-JTAGConf",
            "-1,-1",
            "-AutoConnect",
            "1",
            "-ExitOnError",
            "1",
            "-CommandFile",
            str(command_path),
        ]
        if self._probe_serial:
            arguments.extend(("-SelectEmuBySN", self._probe_serial))

        started_s = time.monotonic()
        try:
            completed = subprocess.run(
                arguments,
                check=False,
                capture_output=True,
                timeout=execution_timeout_s or self._command_timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            stdout_path.write_bytes(exc.stdout or b"")
            stderr_path.write_bytes(exc.stderr or b"")
            raise TransportError(f"J-Link {action} command failed to execute: {exc}") from exc
        except OSError as exc:
            raise TransportError(f"J-Link {action} command failed to execute: {exc}") from exc
        completed_s = time.monotonic()
        stdout_path.write_bytes(completed.stdout)
        stderr_path.write_bytes(completed.stderr)
        if completed.returncode != 0:
            raise TransportError(
                f"J-Link {action} command failed with exit code {completed.returncode}; "
                f"see {stdout_path.name} and {stderr_path.name}"
            )

        return DebugAction(
            action=action,
            started_s=started_s,
            completed_s=completed_s,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            requested_hold_s=requested_hold_s,
        )


__all__ = ["DebugAction", "DebugController", "JLinkDebugController"]
