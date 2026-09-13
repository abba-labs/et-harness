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

import yaml
from artifact_layout import (
    DEFAULT_RECORDS_ROOT,
    capture_source_identity,
    target_chip,
    utc_timestamp,
    write_manifest,
)
from maintain_test_records import prepare_review
from record_store import current_root, record_root
from record_transaction import json_object, safe_name, safe_path
from record_workspace import (
    RECEIPT,
    KnowledgeReviewPending,
    environment_lock,
    prepare_workspace,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
for _import_root in (REPOSITORY_ROOT, REPOSITORY_ROOT / "pc"):
    if str(_import_root) not in sys.path:
        sys.path.insert(0, str(_import_root))
from et_test_platform.results.case_report import iter_canonical_results  # noqa: E402
from et_test_platform.scheduling.run_context import (  # noqa: E402
    case_dir_name,
    execution_slot,
    filesystem_execution_key,
    stable_case_run_id,
)

FORMAL_CASE_ROOT = REPOSITORY_ROOT / "pc/et_test_platform/test_cases"
DOCUMENT_ROOT = REPOSITORY_ROOT / "test_case_doc"

# 独立运行的默认Run Config；Pipeline运行仍以自身快照为准，不读该文件。
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "run_config.yaml"
REPORT_TOOL = REPOSITORY_ROOT / "tools/reporting/generate_case_report.py"
VALIDATE_PC = REPOSITORY_ROOT / "tools/validate_pc.py"
DEFAULT_OUTPUT_ROOT = DEFAULT_RECORDS_ROOT
ARTIFACT_RECORDS_ROOT = DEFAULT_RECORDS_ROOT


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
        help="canonical records root, or fixed records/CHIP/IP/current within pipeline",
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
        help=("explicitly skip Excel update; facts.md and publication.json are still required"),
    )
    parser.add_argument(
        "--within-pipeline",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    # 总软件门禁只在人工明确要求时执行，不由每次IP运行自动触发。
    parser.add_argument(
        "--software-preflight",
        action="store_true",
        help="run the full software gate (tools/validate_pc.py) before this IP run",
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
    if not normalized or normalized.startswith("_") or not normalized.replace("_", "").isalnum():
        raise ValueError(f"invalid IP name: {value!r}")
    return normalized


# Reject direct invocations that try to scatter Formal Case output outside records.
def _validated_output_root(value: str) -> Path:
    output_root = Path(value).resolve()
    allowed_root = ARTIFACT_RECORDS_ROOT.resolve()
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


# 独立运行时补齐Run Config中的工具环境变量，使调试器等Case与Pipeline运行等价。
# 只导出已配置的非空取值；不覆盖调用者已经显式设置的环境。
def _tool_environment(config_path: Path) -> dict[str, str]:
    if not config_path.is_file():
        return {}
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    tools = ((payload.get("environment") or {}).get("tools")) or {}
    debug = ((payload.get("dut") or {}).get("debug")) or {}
    exported: dict[str, str] = {}
    jlink = (tools.get("jlink") or {}).get("executable")
    if isinstance(jlink, str) and jlink.strip():
        exported["ET_TOOL_JLINK_EXECUTABLE"] = jlink
    probe = debug.get("probe_serial")
    if probe is not None and str(probe).strip():
        exported["ET_DUT_DEBUG_PROBE_SERIAL"] = str(probe)
    return exported


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


# 校验Session已终结且exitstatus与pytest退出码一致；不读取任何Case Result。
def _require_finalized_session(session: dict[str, object], *, pytest_exit: int) -> None:
    if session.get("finished_at") in {None, ""}:
        raise ValueError("canonical session is not finalized")
    if session.get("exitstatus") != pytest_exit:
        raise ValueError("canonical session exitstatus does not match pytest exit code")


# 把Session记录的selected_executions展开为期望的(case_id, parameter_id)重数；不做路径校验。
def _expected_executions(session: dict[str, object]) -> Counter[tuple[str, str | None]]:
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
    return expected


# 校验单个Case Result的身份、目录形状和状态，返回其(case_id, parameter_id)计数键。
def _canonical_case_key(
    result_path: Path,
    result: dict[str, object],
    *,
    run_dir: Path,
    run_id: object,
    seen_keys: set[tuple[str, str]],
) -> tuple[str, str | None]:
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
    slot_parameter = parameter_id if isinstance(parameter_id, str) else None
    try:
        expected_case = case_dir_name(case_id)
        expected_slot = execution_slot(slot_parameter)
        expected_run = stable_case_run_id(case_id, slot_parameter)
        fs_key = filesystem_execution_key(case_id, slot_parameter)
    except ValueError as exc:
        raise ValueError(f"canonical case identity is invalid: {result_path}") from exc
    expected_path = run_dir / "cases" / expected_case / expected_slot / "result.json"
    if result_path.resolve() != expected_path.resolve():
        raise ValueError(
            f"canonical result path does not match nested layout: {result_path}; "
            f"expected path cases/{expected_case}/{expected_slot}/result.json"
        )
    if result.get("case_run_id") != expected_run:
        raise ValueError(f"canonical case_run_id does not match its directory: {result_path}")
    if expected_slot.casefold() == "artifacts" or fs_key in seen_keys:
        raise ValueError(f"canonical case identity is invalid: {result_path}")
    seen_keys.add(fs_key)
    if status not in {"PASS", "FAIL", "SKIP", "EVIDENCE_MISSING"}:
        raise ValueError(f"canonical case status is invalid: {result_path}")
    return case_id.lower(), parameter_id


# 校验一次pytest运行的Session与每个参数execution结果一一闭合；不重新判断IP业务结果。
def _validate_canonical_run(run_dir: Path, *, pytest_exit: int) -> bool:
    session = _load_json_object(run_dir / "session.json", label="canonical session")
    _require_finalized_session(session, pytest_exit=pytest_exit)
    expected = _expected_executions(session)

    layout, case_results = iter_canonical_results(run_dir / "cases")
    if layout != "nested" and case_results:
        raise ValueError(
            "Formal current must use nested cases/<CASE_ID>/<SLOT>/result.json; "
            f"found {layout} layout under {run_dir / 'cases'}"
        )

    actual: Counter[tuple[str, str | None]] = Counter()
    evidence_complete = True
    seen_keys: set[tuple[str, str]] = set()
    run_id = session.get("run_id")
    for result_path in case_results:
        result = _load_json_object(result_path, label="canonical case result")
        key = _canonical_case_key(
            result_path, result, run_dir=run_dir, run_id=run_id, seen_keys=seen_keys
        )
        actual[key] += 1
        evidence_complete = evidence_complete and result.get("status") != "EVIDENCE_MISSING"

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
    return exit_code


# 按需运行总软件门禁；默认不在每个IP运行时重复执行。
def _run_software_preflight(*, requested: bool) -> int:
    if not requested:
        return 0
    print("Running canonical software preflight...")
    exit_code = _run([sys.executable, str(VALIDATE_PC)])
    if exit_code != 0:
        print(f"Software preflight failed with exit code {exit_code}.")
    return exit_code


# 从本轮Pipeline复制身份与配置到独立IP现场，之后公共阶段复用不影响IP事实。
def _pipeline_snapshot(
    args: argparse.Namespace, chip: str, source_revision: str, manifest: dict[str, object]
) -> bytes | None:
    if not args.within_pipeline:
        return None
    pipeline_root = current_root(REPOSITORY_ROOT, chip, "_PIPELINE")
    if args.manifest is None or args.manifest.absolute() != pipeline_root / "manifest.json":
        raise ValueError("pipeline invocation requires its original manifest")
    parent = json_object(safe_path(pipeline_root, "manifest.json").read_bytes())
    if parent.get("source_revision") != source_revision or parent.get("status") != "RUNNING":
        raise ValueError("pipeline manifest source/state does not match this invocation")
    manifest["pipeline_run_id"] = parent["run_id"]
    snapshot = parent.get("configuration_snapshot")
    if isinstance(snapshot, str):
        configuration = safe_path(pipeline_root, snapshot).read_bytes()
        manifest["configuration_snapshot"] = "config/run_config.snapshot.yaml"
        manifest["configuration_sha256"] = parent["configuration_sha256"]
        return configuration
    return None


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

    preflight_exit = _run_software_preflight(requested=bool(args.software_preflight))
    if preflight_exit != 0:
        return preflight_exit

    output_root = _validated_output_root(args.output_root)
    chip = target_chip(Path(args.bench), args.target)
    run_dir = current_root(REPOSITORY_ROOT, chip, ip)
    expected_output = run_dir if args.within_pipeline else ARTIFACT_RECORDS_ROOT.resolve()
    if output_root != expected_output:
        raise ValueError("Formal output must use the fixed records chip/IP current workspace")
    standalone_manifest: dict[str, object] = {
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
    configuration = _pipeline_snapshot(args, chip, source_revision, standalone_manifest)
    prepare_workspace(REPOSITORY_ROOT, run_dir)
    if configuration is not None:
        (run_dir / "config").mkdir()
        (run_dir / "config/run_config.snapshot.yaml").write_bytes(configuration)
    write_manifest(run_dir, standalone_manifest)
    artifact_run_dir = run_dir
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
    os.environ.update(
        {
            name: value
            for name, value in _tool_environment(DEFAULT_CONFIG_PATH).items()
            if name not in os.environ
        }
    )
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
    # HELLO chip_id is often lowercase; destination identity is already safe_name().upper().
    if safe_name(_session_chip(run_dir)).upper() != chip:
        print(
            "Actual Session chip differs from the Bench evidence destination; raw files retained."
        )
        return _finish_standalone_run(artifact_run_dir, standalone_manifest, pytest_exit or 2)
    _finish_standalone_run(artifact_run_dir, standalone_manifest, pytest_exit or canonical_exit)
    print("Preparing current facts and report for Case knowledge review...")
    try:
        prepared = prepare_review(
            REPOSITORY_ROOT,
            run_dir,
            chip=chip,
            ip=ip,
            lane=args.lane,
            manifest=run_dir / "manifest.json",
            write_report=not args.no_report,
        )
        facts_path = run_dir / "facts.md"
        publication_path = run_dir / RECEIPT
        if not facts_path.is_file() or not publication_path.is_file():
            raise ValueError("review preparation did not produce facts.md and publication.json")
        if not args.no_report:
            report_value = prepared.get("report")
            if not report_value:
                raise ValueError("review preparation did not produce the Excel report")
            report_path = Path(str(report_value))
            _validate_report_output(report_path)
            print(f"Latest report: {report_path}")
        else:
            print(
                "Report disabled: latest Excel retained and NOT UPDATED for this run; "
                "facts.md and publication.json were still written."
            )
    except (OSError, ValueError, RuntimeError, KeyError, zipfile.BadZipFile) as exc:
        print(
            "Review preparation failed; Case session exists but publication/report was not sealed."
        )
        print(f"Raw workspace retained: {exc}")
        return pytest_exit or canonical_exit or 2

    print(f"Case knowledge: {record_root(REPOSITORY_ROOT, chip, ip)}")
    print(
        "Knowledge review is pending; humans may start the next run, "
        "Agent must review before the next Agent task."
    )
    return pytest_exit or canonical_exit


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
