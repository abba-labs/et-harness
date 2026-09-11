# 流水线日志监视入口。
# 职责：轮询一个 pipeline 日志，命中成功/失败标志即退出，供人工或Agent等待部署结束。
# 边界：只读日志，不触发部署、不改现场、不判断 IP 功能结果。
# 依赖：仅标准库。
#
# 命中 "Configured pipeline: PASS" 返回 0；命中已知失败标志返回 1；超时返回 1。

from __future__ import annotations

import argparse
import time
from pathlib import Path

PASS_MARKER = "Configured pipeline: PASS"
FAIL_MARKERS = (
    "Core1 peer mailbox verification failed",
    "cannot reuse current workspace",
    "current workspace is unpublished",
    "Pipeline publication is incomplete",
    "XC7VX980T_VOLATILE_PROGRAM_FAIL",
    "ET6801_BOOTROM_KEIL_DEBUG_FAIL",
    "ET6801_FLASH_RUN_FAIL",
    "Keil Flash operation did not reach a terminal log result",
    "Traceback (most recent call last):",
)


def _body(log: Path) -> str:
    if not log.is_file():
        return ""
    return log.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch one pipeline log.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--timeout-s", type=float, default=1800.0)
    parser.add_argument("--interval-s", type=float, default=30.0)
    args = parser.parse_args()

    deadline = time.monotonic() + args.timeout_s
    while time.monotonic() < deadline:
        body = _body(args.log)
        if PASS_MARKER in body:
            print("DONE")
            return 0
        for marker in FAIL_MARKERS:
            if marker in body:
                print(f"FAILED: {marker}")
                return 1
        time.sleep(args.interval_s)

    print(f"FAILED: no terminal result within {args.timeout_s:.0f}s")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
