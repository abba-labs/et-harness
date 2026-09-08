#!/usr/bin/env python3
# Run one Formal IP package and generate its human-review report after pytest finishes.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from uuid import uuid4

from artifact_layout import (
    DEFAULT_RUNS_ROOT,
    capture_source_identity,
    create_current_directory,
    utc_timestamp,
    write_manifest,
)
from maintain_test_records import prepare_review
from record_store import record_root
from record_workspace import (
    KnowledgeReviewPending,
    environment_lock,
    prepare_workspace,
    seal_pipeline,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FORMAL_CASE_ROOT = REPOSITORY_ROOT / "pc/et_test_platform/test_cases"
DOCUMENT_ROOT = REPOSITORY_ROOT / "test_case_doc"
REPORT_TOOL = REPOSITORY_ROOT / "tools/reporting/generate_case_report.py"
VALIDATE_PC = REPOSITORY_ROOT / "tools/validate_pc.py"
DEFAULT_OUTPUT_ROOT = DEFAULT_RUNS_ROOT
ARTIFACT_RUNS_ROOT = DEFAULT_RUNS_ROOT


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one registered Formal IP package and generate its review report."
    )
    parser.add_argument("--ip", required=True, help="IP package name, for example crc")
    parser.add_argument("--bench", required=True, help="bench topology YAML path")
    parser.add_argument("--target", default="dut", help="logical target name in the bench")
    parser.add_argument("--lane", required=True, choices=("sil", "fpga", "hil"))
    parser.add_argument("--manifest", type=Path, help=argparse.SUPPRESS)
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="canonical runs root, or fixed current/tests/IP directory within pipeline",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="additional pytest argument; repeat for multiple arguments",
    )
    parser.add_argument(
        "--level",
        action="append",
        choices=("P0", "P1", "P2", "P3"),
        default=[],
        help="Formal Case level to include; repeat for multiple levels",
    )
    parser.add_argument(
        "--include-case",
        action="append",
        default=[],
        help="stable Case ID to include; repeat for multiple IDs",
    )
    parser.add_argument(
        "--exclude-case",
        action="append",
        default=[],
        help="stable Case ID to exclude; repeat for multiple IDs",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="run pytest without generating the Excel review report",
    )
    parser.add_argument(
        "--within-pipeline",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--source-revision", help=argparse.SUPPRESS)
    parser.add_argument(
        "--source-state",
        choices=("clean", "dirty"),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def _normalize_ip(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or not normalized.replace("_", "").isalnum():
        raise ValueError(f"invalid IP name: {value!r}")
    return normalized


# Reject direct invocations that try to scatter Formal Case output outside artifacts/runs.
def _validated_output_root(value: str) -> Path:
    output_root = Path(value).resolve()
    allowed_root = ARTIFACT_RUNS_ROOT.resolve()
    try:
        output_root.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError(f"output root must stay inside {allowed_root}") from exc
    return output_root


def _validate_pytest_args(values: Sequence[str]) -> tuple[str, ...]:
    # 只开放测试选择和输出精简参数，平台插件、Bench、Target 与产物路径仍由运行器唯一控制。
    flag_options = {"-x", "--exitfirst", "-q", "--quiet", "-v", "--verbose"}
    value_options = {"-k", "-m", "--maxfail", "--tb"}
    normalized = tuple(str(value) for value in values)
    index = 0
    while index < len(normalized):
        argument = normalized[index]
        if argument in flag_options:
            index += 1
            continue
        if argument in value_options:
            if index + 1 >= len(normalized):
                raise ValueError(f"pytest argument {argument!r} requires a value")
            index += 2
            continue
        if any(argument.startswith(f"{option}=") for option in value_options):
            index += 1
            continue
        raise ValueError(
            f"unsupported pytest argument {argument!r}; only Case/marker selection, "
            "maxfail, traceback and verbosity options are allowed"
        )
    return normalized


# 把结构化等级和稳定Case ID转换成受控的pytest选择表达式，禁止配置注入任意参数。
def _selection_pytest_args(
    *,
    levels: Sequence[str],
    include_cases: Sequence[str],
    exclude_cases: Sequence[str],
) -> tuple[str, ...]:
    safe_case = re.compile(r"^[a-z0-9_]+$")
    for case_id in (*include_cases, *exclude_cases):
        if not safe_case.fullmatch(case_id):
            raise ValueError(f"invalid stable Case ID: {case_id!r}")

    clauses: list[str] = []
    if levels:
        clauses.append("(" + " or ".join(level.lower() for level in levels) + ")")
    if include_cases:
        clauses.append("(" + " or ".join(include_cases) + ")")
    if exclude_cases:
        clauses.append("not (" + " or ".join(exclude_cases) + ")")
    return ("-k", " and ".join(clauses)) if clauses else ()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _session_chip(run_dir: Path) -> str:
    session_path = run_dir / "session.json"
    if not session_path.is_file():
        return "ET"
    try:
        payload = json.loads(session_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return "ET"
    if not isinstance(payload, dict):
        return "ET"
    value = payload.get("chip_id") or payload.get("chip")
    return str(value).strip() if value else "ET"


def _pytest_command(
    *,
    ip: str,
    bench: str,
    target: str,
    run_dir: Path,
    pytest_args: Sequence[str],
    source_revision: str | None = None,
    source_dirty: bool = False,
    spec_sha256: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(FORMAL_CASE_ROOT / ip),
        "--et-hardware",
        "--et-bench",
        bench,
        "--et-target",
        target,
        "--et-artifact-dir",
        str(run_dir),
    ]
    if source_revision:
        command.extend(("--et-source-revision", source_revision))
    if source_dirty:
        command.append("--et-source-dirty")
    if spec_sha256:
        command.extend(("--et-spec-sha256", spec_sha256))
    command.extend(pytest_args)
    return command


def _report_command(*, document: Path, run_dir: Path, output: Path, chip: str) -> list[str]:
    return [
        sys.executable,
        str(REPORT_TOOL),
        "--document",
        str(document),
        "--results",
        str(run_dir),
        "--output",
        str(output),
        "--chip",
        chip,
    ]


def _run(command: Sequence[str], *, log_path: Path | None = None) -> int:
    if log_path is None:
        completed = subprocess.run(command, cwd=REPOSITORY_ROOT, check=False)
        return int(completed.returncode)
    with (
        log_path.open("w", encoding="utf-8") as stream,
        subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        ) as process,
    ):
        if process.stdout is None:
            raise RuntimeError("pytest did not expose stdout")
        for line in process.stdout:
            print(line, end="")
            stream.write(line)
            stream.flush()
        return int(process.wait())


def _load_json_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not readable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


# 校验一次pytest运行的Session与每个参数execution结果一一闭合；不重新判断IP业务结果。
def _validate_canonical_run(run_dir: Path, *, pytest_exit: int) -> bool:
    session = _load_json_object(run_dir / "session.json", label="canonical session")
    if session.get("finished_at") in {None, ""}:
        raise ValueError("canonical session is not finalized")
    if session.get("exitstatus") != pytest_exit:
        raise ValueError("canonical session exitstatus does not match pytest exit code")
    selection = session.get("selection")
    if not isinstance(selection, dict):
        raise ValueError("canonical session is missing the selected execution set")
    selected = selection.get("selected_executions")
    if not isinstance(selected, list):
        raise ValueError("canonical session selected_executions must be a list")

    expected: Counter[tuple[str, str | None]] = Counter()
    for execution in selected:
        if not isinstance(execution, dict) or not isinstance(execution.get("case_id"), str):
            raise ValueError("canonical session contains an invalid selected execution")
        parameter_id = execution.get("parameter_id")
        if parameter_id is not None and not isinstance(parameter_id, str):
            raise ValueError("canonical session contains an invalid parameter_id")
        expected[(str(execution["case_id"]).lower(), parameter_id)] += 1

    actual: Counter[tuple[str, str | None]] = Counter()
    evidence_complete = True
    run_id = session.get("run_id")
    case_results = sorted((run_dir / "cases").glob("*/result.json"))
    for result_path in case_results:
        result = _load_json_object(result_path, label="canonical case result")
        case_id = result.get("case_id")
        parameter_id = result.get("parameter_id")
        status = result.get("status")
        if (
            not isinstance(case_id, str)
            or parameter_id is not None
            and not isinstance(parameter_id, str)
        ):
            raise ValueError(f"canonical case identity is invalid: {result_path}")
        if result.get("run_id") != run_id:
            raise ValueError(f"canonical case run_id does not match session: {result_path}")
        if result.get("case_run_id") != result_path.parent.name:
            raise ValueError(f"canonical case_run_id does not match its directory: {result_path}")
        if status not in {"PASS", "FAIL", "SKIP", "EVIDENCE_MISSING"}:
            raise ValueError(f"canonical case status is invalid: {result_path}")
        actual[(case_id.lower(), parameter_id)] += 1
        evidence_complete = evidence_complete and status != "EVIDENCE_MISSING"

    if actual != expected:
        raise ValueError(
            "canonical case results do not match selected executions: "
            f"expected={dict(expected)!r}, actual={dict(actual)!r}"
        )
    return evidence_complete


# Excel工具返回成功后仍校验真实文件，避免空文件或缺失文件把Pipeline误报为PASS。
def _validate_report_output(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"review report was not generated correctly: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if (
                archive.testzip() is not None
                or not {
                    "[Content_Types].xml",
                    "xl/workbook.xml",
                }
                <= names
            ):
                raise ValueError(f"review report is not a valid XLSX container: {path}")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError(f"review report is not a valid XLSX container: {path}") from exc


def _finish_standalone_run(
    artifact_run_dir: Path | None,
    manifest: dict[str, object] | None,
    exit_code: int,
) -> int:
    if artifact_run_dir is None or manifest is None:
        return exit_code
    manifest.update(
        {
            "finished_at": utc_timestamp(),
            "status": "PASS" if exit_code == 0 else "FAIL",
            "exit_code": exit_code,
        }
    )
    write_manifest(artifact_run_dir, manifest)
    try:
        seal_pipeline(REPOSITORY_ROOT, artifact_run_dir, successful=exit_code == 0)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Workspace retained without reuse permission: {exc}")
        manifest.update({"status": "FAIL", "exit_code": exit_code or 2})
        write_manifest(artifact_run_dir, manifest)
        return exit_code or 2
    return exit_code


def _run_software_preflight(*, within_pipeline: bool) -> int:
    if within_pipeline:
        return 0
    print("Running canonical software preflight...")
    exit_code = _run([sys.executable, str(VALIDATE_PC)])
    if exit_code != 0:
        print(f"Software preflight failed with exit code {exit_code}.")
    return exit_code


def _execute_ip(args: argparse.Namespace) -> int:
    ip = _normalize_ip(args.ip)
    pytest_args = (
        *_selection_pytest_args(
            levels=args.level,
            include_cases=args.include_case,
            exclude_cases=args.exclude_case,
        ),
        *_validate_pytest_args(args.pytest_arg),
    )
    case_root = FORMAL_CASE_ROOT / ip
    document = DOCUMENT_ROOT / ip / f"{ip}.md"
    if not case_root.is_dir():
        raise FileNotFoundError(f"Formal Case package not found: {case_root}")
    if not document.is_file():
        raise FileNotFoundError(f"Case specification document not found: {document}")

    if (args.source_revision is None) != (args.source_state is None):
        raise ValueError("source revision and source state must be supplied together")
    if args.source_revision is None:
        source_revision, source_dirty = capture_source_identity(REPOSITORY_ROOT)
    else:
        source_revision = str(args.source_revision)
        source_dirty = args.source_state == "dirty"

    preflight_exit = _run_software_preflight(within_pipeline=bool(args.within_pipeline))
    if preflight_exit != 0:
        return preflight_exit

    output_root = _validated_output_root(args.output_root)
    artifact_run_dir: Path | None = None
    standalone_manifest: dict[str, object] | None = None
    if args.within_pipeline:
        if args.manifest is None:
            raise ValueError("pipeline invocation requires its original manifest")
        run_dir = prepare_workspace(REPOSITORY_ROOT, output_root)
    else:
        artifact_run_dir = create_current_directory(REPOSITORY_ROOT, output_root)
        run_dir = artifact_run_dir / "tests" / ip
        run_dir.mkdir(parents=True, exist_ok=False)
        standalone_manifest = {
            "schema": "et-artifact-run/v1",
            "run_id": str(uuid4()),
            "run_name": f"{ip}_formal_cases",
            "target_kind": {"sil": "renode", "fpga": "fpga", "hil": "silicon"}[args.lane],
            "source_revision": source_revision,
            "source_dirty": source_dirty,
            "started_at": utc_timestamp(),
            "finished_at": None,
            "status": "RUNNING",
        }
        write_manifest(artifact_run_dir, standalone_manifest)
    pytest_command = _pytest_command(
        ip=ip,
        bench=args.bench,
        target=args.target,
        run_dir=run_dir,
        pytest_args=pytest_args,
        source_revision=source_revision,
        source_dirty=source_dirty,
        spec_sha256=_file_sha256(document),
    )

    print(f"Run artifacts: {run_dir}")
    print("Starting pytest...")
    pytest_exit = _run(pytest_command, log_path=run_dir / "pytest.log")

    if not (run_dir / "session.json").is_file():
        print("Canonical session.json was not produced; review report was not generated.")
        return _finish_standalone_run(
            artifact_run_dir,
            standalone_manifest,
            pytest_exit or 2,
        )

    try:
        evidence_complete = _validate_canonical_run(run_dir, pytest_exit=pytest_exit)
    except ValueError as exc:
        print(f"Canonical result validation failed: {exc}")
        evidence_complete = False

    canonical_exit = 0 if evidence_complete else 2
    chip = _session_chip(run_dir)
    print("Preparing current facts and report for Case knowledge review...")
    try:
        prepared = prepare_review(
            REPOSITORY_ROOT,
            run_dir,
            chip=chip,
            ip=ip,
            lane=args.lane,
            manifest=args.manifest
            or (artifact_run_dir / "manifest.json" if artifact_run_dir else None),
            write_report=not args.no_report,
        )
        if not args.no_report:
            report_path = Path(str(prepared["report"]))
            _validate_report_output(report_path)
            print(f"Latest report: {report_path}")
        else:
            print("Report disabled: latest Excel retained and NOT UPDATED for this run.")
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print(f"Review preparation failed; raw workspace retained: {exc}")
        return _finish_standalone_run(
            artifact_run_dir,
            standalone_manifest,
            pytest_exit or canonical_exit or 2,
        )

    print(f"Case knowledge: {record_root(REPOSITORY_ROOT, chip, ip)}")
    print("Knowledge review is pending; current raw files cannot be overwritten before review.")
    return _finish_standalone_run(
        artifact_run_dir,
        standalone_manifest,
        pytest_exit or canonical_exit,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.within_pipeline:
            return _execute_ip(args)
        with environment_lock(REPOSITORY_ROOT):
            return _execute_ip(args)
    except KnowledgeReviewPending as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
