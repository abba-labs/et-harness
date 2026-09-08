#!/usr/bin/env python3
# 固定芯片/IP测试档案的唯一维护入口。
# 职责：串行执行增量更新、只读检查、显式归档和预览优先的保护释放。
# 边界：不执行硬件测试，不删除历史Run，不允许手工覆盖原始结果。
# 依赖：标准库、Canonical报告模型及记录工具组件。

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT / "pc") not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT / "pc"))

from record_archive import create_archive, prepare_prune  # noqa: E402
from record_check import check_records, load_checked_evidence  # noqa: E402
from record_model import LANES, MAX_IP_BYTES  # noqa: E402
from record_source import RecordInput, load_input  # noqa: E402
from record_store import (  # noqa: E402
    case_markdown,
    derived_files,
    prepare_update,
    publish_update,
    record_root,
    report_enabled,
    working_root,
)
from record_transaction import file_lock, recover, safe_path  # noqa: E402
from record_workspace import archive_workspace, environment_lock  # noqa: E402


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Maintain bounded chip/IP Case evidence records")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("update", "check", "archive", "prune"):
        command = commands.add_parser(name)
        command.add_argument("--chip", required=name != "archive")
        command.add_argument("--ip", required=name != "archive")
        if name == "update":
            command.add_argument(
                "--source", type=Path, required=True, help="finalized Session directory"
            )
            command.add_argument("--lane", required=True, choices=sorted(LANES))
            command.add_argument("--manifest", type=Path, help="original pipeline manifest")
            command.add_argument("--no-report", action="store_true", help="skip Excel only")
            command.add_argument(
                "--protect-case",
                action="append",
                default=[],
                help="protect selected baseline/acceptance Case evidence",
            )
        elif name == "archive":
            command.add_argument("--output", type=Path, required=True, help="new milestone .zip")
            command.add_argument(
                "--workspace", type=Path, help="interrupted fixed current workspace"
            )
        elif name == "check":
            command.add_argument(
                "--refresh-views",
                action="store_true",
                help="explicitly rebuild only derived views after validating raw evidence",
            )
        elif name == "prune":
            command.add_argument("--archive", type=Path, required=True)
            command.add_argument("--case", action="append", required=True)
            command.add_argument(
                "--execute", action="store_true", help="release covered protected snapshots"
            )
    args = parser.parse_args(argv)
    if args.command == "archive" and (
        (args.workspace is not None and (args.chip or args.ip))
        or (args.workspace is None and not (args.chip and args.ip))
    ):
        parser.error("archive requires either --workspace or both --chip and --ip")
    return args


def _summary(check: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in check.items() if key not in {"files", "snapshots"}}


# 仅供Runner封存工作目录使用；不改变Canonical或对外台账Schema。
def _publication(incoming: RecordInput, relative: str) -> dict[str, object]:
    proofs: dict[str, list[str]] = {}
    files: dict[str, str] = {}
    for case, snapshots in incoming.cases.items():
        proofs[case] = [snapshot.identity for snapshot in snapshots]
        for snapshot in snapshots:
            files["session.json"] = snapshot.files["source/session.json"]
            for name, sha in snapshot.files.items():
                if name == "source/pytest.log":
                    files["pytest.log"] = sha
                elif name == "source/result.json" and snapshot.result is not None:
                    files[f"cases/{snapshot.result['case_run_id']}/result.json"] = sha
                elif name.startswith("artifacts/"):
                    files[name.removeprefix("artifacts/")] = sha
    return {"_proofs": {relative: proofs}, "_source_files": files}


# Pipeline和CLI复用同一入口；先恢复未完成事务，再检查旧记录，最后原子发布增量。
def update_records(
    repository: Path,
    source: Path,
    *,
    chip: str,
    ip: str,
    lane: str,
    manifest: Path | None = None,
    protect_cases: tuple[str, ...] = (),
    write_report: bool = True,
) -> dict[str, object]:
    root = record_root(repository, chip, ip)
    work = working_root(repository, chip, ip)
    with file_lock(work / "operation.lock"):
        recover(root, work)
        if root.exists() and any(root.iterdir()):
            check_records(root)
        incoming = load_input(repository, source, ip=ip, lane=lane, work=work, manifest=manifest)
        if incoming.chip != root.parent.name or incoming.ip != root.name:
            raise ValueError("requested chip/IP does not match the original Session")
        _, files = prepare_update(
            root, incoming, protect_cases=protect_cases, write_report=write_report
        )
        count = publish_update(root, work, files, validate=lambda: check_records(root))
        return {
            "operation": "update",
            "changed_files": count,
            **_summary(check_records(root)),
            **_publication(incoming, root.relative_to(repository).as_posix()),
        }


def run_operation(args: argparse.Namespace, repository: Path) -> dict[str, object]:
    if args.command == "update":
        return update_records(
            repository,
            args.source,
            chip=args.chip,
            ip=args.ip,
            lane=args.lane,
            manifest=args.manifest,
            protect_cases=tuple(args.protect_case),
            write_report=not args.no_report,
        )
    if args.command == "archive" and args.workspace is not None:
        with environment_lock(repository):
            return archive_workspace(repository, args.workspace, args.output)
    root = record_root(repository, args.chip, args.ip)
    work = working_root(repository, args.chip, args.ip)
    with file_lock(work / "operation.lock"):
        if (work / "transaction.json").exists():
            raise RuntimeError(
                "unfinished record transaction; run update to recover before inspection"
            )
        if args.command == "check":
            if args.refresh_views:
                _, records = load_checked_evidence(root)
                files = {
                    **derived_files(root, records, write_report=report_enabled(root)),
                    **{
                        f"cases/{case}.md": case_markdown(root, record)
                        for case, record in records.items()
                    },
                }
                publish_update(root, work, files, validate=lambda: check_records(root))
            return _summary(check_records(root))
        if args.command == "archive":
            result = create_archive(root, args.output, work)
            return {
                "operation": "archive",
                "archive": result["archive"],
                "sha256": result["sha256"],
            }
        archive = safe_path(args.archive.parent, args.archive.name)
        if archive.stat().st_size > MAX_IP_BYTES + 1024 * 1024:
            raise ValueError("archive exceeds capacity")
        plan, files = prepare_prune(root, archive.read_bytes(), work, args.case)
        plan["executed"] = args.execute
        if args.execute:
            publish_update(root, work, files, validate=lambda: check_records(root))
            plan["check"] = _summary(check_records(root))
        return plan


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        result = run_operation(args, REPOSITORY_ROOT)
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Record maintenance failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {key: value for key, value in result.items() if not key.startswith("_")},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
