#!/usr/bin/env python3
# Case知识的提取、检查、索引与整理确认入口。
# 职责：把当前Canonical事实交给Agent提炼，确认后才允许复用原始工作区。
# 边界：不执行硬件，不改Case正文，不生成长期JSON/ZIP或自动关闭问题。
# 依赖：既有Canonical报告、Markdown检查和文件事务。

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "pc"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from artifact_layout import publish_latest_report  # noqa: E402
from record_check import check_records  # noqa: E402
from record_model import LANES  # noqa: E402
from record_report import render_facts  # noqa: E402
from record_source import RecordInput, load_input  # noqa: E402
from record_store import current_root, record_root, refresh_index, working_root  # noqa: E402
from record_transaction import digest, file_lock, publish  # noqa: E402
from record_workspace import (  # noqa: E402
    RECEIPT,
    archive_workspace,
    environment_lock,
    review_workspace,
    seal_workspace,
    verify_publication,
)

from tools.reporting.generate_case_report import xlsx_bytes  # noqa: E402


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract facts and maintain Markdown Case knowledge"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("extract", "check", "index", "review", "archive"):
        command = commands.add_parser(name)
        if name == "archive":
            command.add_argument("--workspace", type=Path, required=True)
            command.add_argument(
                "--output",
                type=Path,
                required=True,
                help="fixed sibling recovery.zip (must not exist)",
            )
            continue
        command.add_argument("--chip", required=True)
        command.add_argument("--ip", required=True)
        if name in {"extract", "review"}:
            command.add_argument(
                "--source", type=Path, required=True, help="finalized Session directory"
            )
            command.add_argument("--lane", required=True, choices=sorted(LANES))
            command.add_argument("--manifest", type=Path)
        if name in {"extract", "check"}:
            command.add_argument("--case", action="append", default=[])
        if name == "extract":
            command.add_argument(
                "--key", action="append", default=[], help="exact measurement./observation. key"
            )
    return parser.parse_args(argv)


def _input(
    repository: Path, source: Path, *, chip: str, ip: str, lane: str, manifest: Path | None
) -> RecordInput:
    incoming = load_input(
        repository,
        source,
        ip=ip,
        lane=lane,
        work=working_root(repository, chip, ip),
        manifest=manifest
        or (source / "manifest.json" if (source / "manifest.json").is_file() else None),
    )
    root = record_root(repository, chip, ip)
    if incoming.chip != root.parent.name or incoming.ip != root.name:
        raise ValueError("requested chip/IP does not match the original Session")
    return incoming


def _source_files(incoming: RecordInput) -> dict[str, str]:
    files: dict[str, str] = {}
    for snapshots in incoming.cases.values():
        for snapshot in snapshots:
            files["session.json"] = snapshot.files["source/session.json"]
            for name, sha in snapshot.files.items():
                if name == "source/pytest.log":
                    files["pytest.log"] = sha
                elif name == "source/manifest.json":
                    files["manifest.json"] = sha
                elif name == "source/configuration.yaml":
                    files["config/run_config.snapshot.yaml"] = sha
                elif name == "source/result.json" and snapshot.result is not None:
                    files[f"cases/{snapshot.result['case_run_id']}/result.json"] = sha
                elif name.startswith("artifacts/"):
                    files[name.removeprefix("artifacts/")] = sha
    return files


# 仅Runner调用：生成当次事实摘要和可选Excel，建立待整理回执；绝不写长期Case文件。
def prepare_review(
    repository: Path,
    source: Path,
    *,
    chip: str,
    ip: str,
    lane: str,
    manifest: Path | None = None,
    write_report: bool = True,
) -> dict[str, object]:
    expected = current_root(repository, chip, ip)
    if source.absolute() != expected:
        raise ValueError(
            "review preparation may only write records/<CHIP>/<IP>/current; historical sources are read-only"
        )
    work = working_root(repository, chip, ip)
    with file_lock(work / "operation.lock"):
        receipt = None
        if (source / RECEIPT).exists():
            receipt = verify_publication(repository, source, require_review=False)
        incoming = _input(repository, source, chip=chip, ip=ip, lane=lane, manifest=manifest)
        model = dict(incoming.report_model)
        model["report_lane"] = lane
        report_data = xlsx_bytes(model) if write_report else None
        files = {
            "facts.md": render_facts(incoming),
            "test_report.xlsx": None,
            "specification.md": incoming.blobs[
                next(iter(incoming.cases.values()))[0].files["source/specification.md"]
            ],
        }
        count = publish(source, work / "run-output", files)
        hashes = {
            **_source_files(incoming),
            **{name: digest(data) for name, data in files.items() if data is not None},
        }
        if receipt is None or receipt["files"] != hashes:
            seal_workspace(
                repository,
                source,
                proofs={},
                expected_files=hashes,
                pending_review=True,
            )
        report = None
        if report_data is not None:
            report, changed = publish_latest_report(
                repository / "artifacts/reports", chip=chip, ip=ip, data=report_data
            )
            count += changed
        return {
            "operation": "prepare_review",
            "changed_files": count,
            "case_count": len(incoming.cases),
            "knowledge_review": "REVIEWED"
            if receipt and not receipt.get("pending_review") and receipt["files"] == hashes
            else "PENDING",
            "facts": str(source / "facts.md"),
            "report": str(report) if report is not None else None,
            "report_updated": write_report,
        }


# 显式调用即确认已逐Case提炼或核对无新知识；机器仅校验完整性，不验证人工结论。
def review_records(
    repository: Path, source: Path, *, chip: str, ip: str, lane: str, manifest: Path | None = None
) -> dict[str, object]:
    expected = current_root(repository, chip, ip)
    if source.absolute() != expected:
        raise ValueError(
            "review only releases records/<CHIP>/<IP>/current; use extract/check for historical sources"
        )
    work = working_root(repository, chip, ip)
    with environment_lock(repository), file_lock(work / "operation.lock"):
        verify_publication(repository, source, require_review=False, verify_knowledge=False)
        incoming = _input(repository, source, chip=chip, ip=ip, lane=lane, manifest=manifest)
        root = record_root(repository, chip, ip)
        checked = check_records(root, cases=tuple(incoming.cases))
        changed = refresh_index(root, work)
        proofs = {root.relative_to(repository).as_posix(): checked["files"]}
        review_workspace(repository, source, proofs=proofs)
        return {
            "operation": "review",
            "reviewed_cases": sorted(incoming.cases),
            "changed_index_files": changed,
            "knowledge_files_changed": 0,
            "note": "Explicitly reviewed; not a new test or automatic issue closure",
        }


def run_operation(args: argparse.Namespace, repository: Path) -> dict[str, object] | bytes:
    if args.command == "archive":
        with environment_lock(repository):
            return archive_workspace(repository, args.workspace, args.output)
    root = record_root(repository, args.chip, args.ip)
    if args.command == "review":
        return review_records(
            repository,
            args.source,
            chip=args.chip,
            ip=args.ip,
            lane=args.lane,
            manifest=args.manifest,
        )
    work = working_root(repository, args.chip, args.ip)
    with file_lock(work / "operation.lock"):
        if args.command != "index" and (work / "transaction.json").exists():
            raise RuntimeError(
                "unfinished index transaction; preserve it and recover before further edits"
            )
        if args.command == "extract":
            incoming = _input(
                repository,
                args.source,
                chip=args.chip,
                ip=args.ip,
                lane=args.lane,
                manifest=args.manifest,
            )
            return render_facts(incoming, cases=tuple(args.case), keys=tuple(args.key))
        if args.command == "index":
            return {"operation": "index", "changed_files": refresh_index(root, work)}
        check = check_records(root, cases=tuple(args.case))
        return {key: value for key, value in check.items() if key not in {"files", "titles"}}


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        result = run_operation(args, REPOSITORY_ROOT)
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Case knowledge maintenance failed: {exc}", file=sys.stderr)
        return 1
    if isinstance(result, bytes):
        print(result.decode("utf-8"), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
