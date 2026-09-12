# 流水线日志监视入口。
# 职责：等待指定Run的Manifest终态，兼容日志位置参数但不读取日志。
# 边界：只读Manifest，不触发部署、不改现场、不判断IP功能结果。
# 依赖：仅标准库。
#
# 仅精确Run ID的Manifest终态PASS且exit_code=0返回0；不根据旧日志PASS退出。

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


# 旧路径和旧Run的PASS都不能关闭当前等待；未知/未终止状态继续等待。
def _terminal_result(manifest: object, run_id: str) -> int | None:
    if not isinstance(manifest, dict) or manifest.get("schema") != "et-artifact-run/v1":
        return None
    if manifest.get("run_id") != run_id:
        return None
    finished = manifest.get("finished_at")
    if not isinstance(finished, str) or not finished or type(manifest.get("exit_code")) is not int:
        return None
    return 0 if manifest.get("status") == "PASS" and manifest["exit_code"] == 0 else 1


# 等待指定Run的明确终态；读取异常继续有界等待，超时或失败均返回非零。
def main() -> int:
    parser = argparse.ArgumentParser(description="Watch one pipeline log.")
    parser.add_argument(
        "log", type=Path, help="legacy diagnostic path; never used as a result source"
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout-s", type=float, default=1800.0)
    parser.add_argument("--interval-s", type=float, default=30.0)
    args = parser.parse_args()
    if args.timeout_s <= 0 or args.interval_s <= 0 or args.interval_s > 60:
        parser.error("timeout must be positive; interval must be in (0, 60]")

    deadline = time.monotonic() + args.timeout_s
    while time.monotonic() < deadline:
        try:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            manifest = None
        result = _terminal_result(manifest, args.run_id)
        if result is not None:
            print(f"{'DONE' if result == 0 else 'FAILED'}: {args.run_id}")
            return result
        time.sleep(args.interval_s)

    print(f"FAILED: no terminal result within {args.timeout_s:.0f}s")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
