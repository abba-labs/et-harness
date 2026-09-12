# ET6801 Core1 Peer Mailbox只读诊断。
# 职责：显式选择J-Link，读取两次mailbox并在独立固定工作区保存现场。
# 边界：只发mem32；不烧录、不改Pipeline现场，不替代Formal Case结论。
# 依赖：J-Link、Core0选择脚本、R500工作区锁与原子发布工具。

from __future__ import annotations

import argparse
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from record_transaction import atomic_write, file_lock, json_bytes, safe_path
from record_workspace import environment_lock, prepare_workspace, seal_workspace

REPOSITORY = Path(__file__).resolve().parents[2]
OUTPUT = "artifacts/records/_DIAGNOSTICS/IPCM_PEER_MAILBOX/current/peer_mailbox.json"
MAILBOX = 0x20440000
MAGIC = 0x45544331
READY = 1
CORE_INDEX = 2
WORD_LINE = re.compile(r"(?im)^([0-9A-Fa-f]{8})\s*=\s*((?:[0-9A-Fa-f]{8}\s+)+)")


def _word(text: str, address: int) -> int:
    for match in WORD_LINE.finditer(text):
        base = int(match.group(1), 16)
        words = match.group(2).split()
        limit = base + len(words) * 4
        if base <= address < limit and (address - base) % 4 == 0:
            return int(words[(address - base) // 4], 16)
    raise RuntimeError(f"J-Link readback missing 0x{address:08X}")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _samples(argv: list[str], stage: Path) -> list[str]:
    texts: list[str] = []
    outputs: list[bytes] = []
    errors: list[bytes] = []
    for index in range(2):
        if index:
            time.sleep(0.1)
        try:
            sample = subprocess.run(
                argv,
                cwd=str(REPOSITORY),
                capture_output=True,
                check=False,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            outputs.append(exc.stdout or b"")
            errors.append(exc.stderr or b"")
            raise RuntimeError(f"J-Link sample {index + 1} timed out after 30s") from exc
        else:
            outputs.append(sample.stdout)
            errors.append(sample.stderr)
        finally:
            # 每次采样立即落盘，第二次启动失败也不能丢失第一次的输出。
            atomic_write(
                safe_path(stage, "peer_mailbox.stdout.log"), b"\n--- sample ---\n".join(outputs)
            )
            atomic_write(
                safe_path(stage, "peer_mailbox.stderr.log"), b"\n--- sample ---\n".join(errors)
            )
        if sample.returncode != 0:
            raise RuntimeError(f"J-Link sample {index + 1} exit {sample.returncode}")
        texts.append(sample.stdout.decode("utf-8", errors="replace"))
    return texts


def _probe(args: argparse.Namespace, output: Path) -> int:
    stage = prepare_workspace(REPOSITORY, output.parent)
    run_id = str(uuid.uuid4())
    manifest: dict[str, object] = {
        "schema": "et-artifact-run/v1",
        "run_id": run_id,
        "started_at": _timestamp(),
        "finished_at": None,
        "status": "RUNNING",
        "exit_code": None,
        "chip_id": "ET6801",
        "lane": "diagnostic",
        "source_revision": None,
        "source_dirty": None,
        "label": args.label,
    }
    atomic_write(safe_path(stage, "manifest.json"), json_bytes(manifest))
    payload: dict[str, object] = {
        "run_id": run_id,
        "label": args.label,
        "ready": False,
        "error": None,
        "magic": None,
        "state": None,
        "core_index": None,
        "heartbeat": None,
        "heartbeat_samples": [],
    }
    exit_code = 1
    try:
        command_file = safe_path(stage, "peer_mailbox.jlink")
        atomic_write(command_file, b"exec DisableAutoUpdateFW\nmem32 0x20440000, 4\nexit\n")
        script = REPOSITORY / "firmware/chips/et6801/core1_peer/debug/core0_select.JLinkScript"
        argv = [
            args.jlink,
            "-NoGui",
            "1",
            "-Device",
            "Cortex-M7",
            "-If",
            "JTAG",
            "-Speed",
            "1000",
            "-AutoConnect",
            "1",
            "-JLinkScriptFile",
            str(script),
            "-JTAGConf",
            "-1,-1",
            "-SelectEmuBySN",
            args.serial,
            "-CommanderScript",
            str(command_file),
        ]
        texts = _samples(argv, stage)
        if any("Cortex-M7 identified" not in text for text in texts):
            raise RuntimeError("Cortex-M7 not identified in both samples")
        magic, state, core_index, heartbeat = (
            _word(texts[-1], MAILBOX + offset) for offset in (0, 4, 8, 12)
        )
        previous = _word(texts[0], MAILBOX + 12)
        progress = 0 < ((heartbeat - previous) & 0xFFFFFFFF) < 0x80000000
        ready = magic == MAGIC and state == READY and core_index == CORE_INDEX and progress
        payload.update(
            {
                "magic": f"0x{magic:08X}",
                "state": state,
                "core_index": core_index,
                "heartbeat": heartbeat,
                "heartbeat_samples": [previous, heartbeat],
                "ready": ready,
            }
        )
        exit_code = 0 if ready else 2
    except (OSError, RuntimeError, ValueError) as exc:
        payload["error"] = str(exc)
    payload["exit_code"] = exit_code
    atomic_write(output, json_bytes(payload))
    manifest.update(
        {
            "finished_at": _timestamp(),
            "status": "PASS" if exit_code == 0 else "FAIL",
            "exit_code": exit_code,
        }
    )
    atomic_write(safe_path(stage, "manifest.json"), json_bytes(manifest))
    # 失败诊断保持未发布以保留现场；只有成功、完整的诊断才可在下一次复用。
    if exit_code == 0:
        seal_workspace(REPOSITORY, stage, proofs={}, routine_success=True)
    print(json_bytes(payload).decode("utf-8"))
    return exit_code


# 校验人工确认和固定诊断路径后持锁采样；现场不完整或设备失败均返回非零。
def main() -> int:
    parser = argparse.ArgumentParser(description="Read Core1 peer mailbox (read-only).")
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jlink", default=r"C:\Keil_v5\ARM\Segger\JLink.exe")
    parser.add_argument("--serial", required=True)
    parser.add_argument("--confirm-hardware-actions", action="store_true")
    args = parser.parse_args()
    if not args.confirm_hardware_actions:
        parser.error("explicit manual hardware confirmation is required")
    if not re.fullmatch(r"[1-9][0-9]*", args.serial):
        parser.error("an explicit positive J-Link serial is required")
    try:
        output = safe_path(REPOSITORY, OUTPUT)
        if args.output.absolute() != output:
            raise ValueError(
                f"standalone diagnostic output must be {OUTPUT}; Pipeline writes are forbidden"
            )
        with (
            environment_lock(REPOSITORY),
            file_lock(output.parent.parent / "_maintenance/probe.lock"),
        ):
            return _probe(args, output)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Peer mailbox diagnostic failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
