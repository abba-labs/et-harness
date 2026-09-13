# ET6801 Core1 Peer Mailbox 只读诊断入口。
# 职责：经官方 J-Link + Core0 AP 脚本读取 AXI_SRAM1 mailbox 的 magic/state/core_index/heartbeat，判断 Peer 是否 Ready。
# 边界：只读（mem32），不烧录、不写寄存器、不启动 Core；不替代 Formal Case 或部署验证。
# 依赖：已安装的 J-Link 与 firmware/chips/et6801/core1_peer/debug/core0_select.JLinkScript。
#
# 用途：IPCM Case 执行前确认 Peer Ready。只读 mem32，不是烧录或编程路径；
# 部署约束见 test_case_doc/ipcm/ET6801_ipcm.md §6.1.1。

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Core1 peer mailbox (read-only).")
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--jlink", default=r"C:\Keil_v5\ARM\Segger\JLink.exe")
    parser.add_argument("--serial", default="-1")
    args = parser.parse_args()

    stage = args.output.parent
    stage.mkdir(parents=True, exist_ok=True)
    command_file = stage / f"{args.label}.jlink"
    stdout = stage / f"{args.label}.stdout.log"
    stderr = stage / f"{args.label}.stderr.log"
    script = REPOSITORY / "firmware/chips/et6801/core1_peer/debug/core0_select.JLinkScript"
    command_file.write_text(
        "exec DisableAutoUpdateFW\nmem32 0x20440000, 4\nexit\n",
        encoding="ascii",
    )
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
    ]
    if args.serial:
        argv.extend(["-SelectEmuBySN", args.serial])
    argv.extend(["-CommanderScript", str(command_file)])
    completed = subprocess.run(argv, cwd=str(REPOSITORY), capture_output=True, check=False)
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    text = completed.stdout.decode("utf-8", errors="replace")
    payload = {
        "label": args.label,
        "exit_code": completed.returncode,
        "magic": None,
        "state": None,
        "core_index": None,
        "heartbeat": None,
        "ready": False,
        "error": None,
    }
    try:
        if completed.returncode != 0:
            raise RuntimeError(f"J-Link exit {completed.returncode}")
        if "Cortex-M7 identified" not in text:
            raise RuntimeError("Cortex-M7 not identified")
        magic = _word(text, MAILBOX)
        state = _word(text, MAILBOX + 4)
        core_index = _word(text, MAILBOX + 8)
        heartbeat = _word(text, MAILBOX + 12)
        payload.update(
            {
                "magic": f"0x{magic:08X}",
                "state": state,
                "core_index": core_index,
                "heartbeat": heartbeat,
                "ready": (
                    magic == MAGIC
                    and state == READY
                    and core_index == CORE_INDEX
                    and heartbeat != 0
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001 - probe must always write JSON
        payload["error"] = str(exc)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 1
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if payload["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
