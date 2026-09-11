# 证据工作区体检入口。
# 职责：按芯片汇总各IP的current回执状态、目录布局与未记录残留，供整理与复用前检查。
# 边界：只读；不做review、不改现场、不判断测试结果对错。
# 依赖：仅标准库。
"""Audit records/<CHIP>/<IP>/current workspaces: layout, unrecorded dirs, review state.

Read-only. Useful before a regression round (confirm nothing blocks reuse) and at review
time (confirm the receipt covers every directory on disk).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
_UUID_LIKE = 36


def _is_uuid_dir(name: str) -> bool:
    return len(name) == _UUID_LIKE and name.count("-") == 4


def _audit_ip(current: Path) -> dict[str, object]:
    publication = current / "publication.json"
    if not publication.is_file():
        return {"receipt": False}
    receipt = json.loads(publication.read_text(encoding="utf-8"))
    recorded = set(receipt.get("directories", []))
    on_disk = {
        str(path.relative_to(current)).replace(os.sep, "/")
        for path in current.rglob("*")
        if path.is_dir()
    }
    cases = current / "cases"
    legacy = nested = 0
    if cases.is_dir():
        for child in cases.iterdir():
            if child.is_dir():
                if _is_uuid_dir(child.name):
                    legacy += 1
                else:
                    nested += 1
    return {
        "receipt": True,
        "legacy": legacy,
        "nested": nested,
        "unrecorded": len(on_disk - recorded),
        "pending_review": receipt.get("pending_review"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit records current workspaces.")
    parser.add_argument("--chip", required=True)
    parser.add_argument(
        "--recovery-zip",
        action="store_true",
        help="also report a sibling recovery.zip (blocks reuse until handled)",
    )
    args = parser.parse_args()

    base = REPOSITORY / "artifacts/records" / args.chip
    if not base.is_dir():
        raise SystemExit(f"no records for chip: {base}")

    for entry in sorted(p for p in base.iterdir() if p.is_dir()):
        current = entry / "current"
        row = _audit_ip(current) if current.is_dir() else {"receipt": False}
        if not row["receipt"]:
            print(f"{entry.name:<10} NO current/publication.json")
            continue
        line = (
            f"{entry.name:<10} legacy={row['legacy']:<4} nested={row['nested']:<4} "
            f"unrecorded={row['unrecorded']:<3} pending={row['pending_review']}"
        )
        if args.recovery_zip:
            line += f" recovery.zip={(entry / 'recovery.zip').exists()}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
