# Unified non-hardware software validation for local use and CI.

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATHS = (
    "tools/runner",
    "tools/governance",
    "tools/quality",
    "tools/reporting",
    "tools/firmware/materialize_keil_validation_record.py",
    "tools/validate_pc.py",
    "pc/et_test_platform",
)
UNIT_TEST_ROOT = "pc/et_test_platform/framework_validation/unit"
FORMAL_CASE_ROOT = "pc/et_test_platform/test_cases"
FIRMWARE_RECORD_TOOL = REPOSITORY_ROOT / "tools/firmware/materialize_keil_validation_record.py"
REPORT_TOOL = REPOSITORY_ROOT / "tools/reporting/generate_case_report.py"
TASK_CONTEXT_TOOL = REPOSITORY_ROOT / "tools/governance/compile_task_context.py"
TASK_CONTEXT_PATH = REPOSITORY_ROOT / "project-governance/runtime/current_task_context.json"
GENERATED_SCOPE_PREFIXES = ("artifacts/runs/", "artifacts/reports/", "artifacts/records/")


# 发现全部芯片 Firmware Manifest；新增芯片不需要修改公共验证入口。
def firmware_manifests() -> tuple[Path, ...]:

    manifests = tuple(sorted((REPOSITORY_ROOT / "firmware/chips").glob("*/project.yaml")))
    if not manifests:
        raise FileNotFoundError("no firmware/chips/*/project.yaml manifests found")
    return manifests


# 发现全部已注册 Formal IP 文档；新增 IP 后不修改统一报告门禁。
def formal_case_documents() -> tuple[Path, ...]:

    documents = tuple(
        REPOSITORY_ROOT / "test_case_doc" / package.name / f"{package.name}.md"
        for package in sorted((REPOSITORY_ROOT / FORMAL_CASE_ROOT).iterdir())
        if package.is_dir() and (package / "case_registry.py").is_file()
    )
    missing = tuple(path for path in documents if not path.is_file())
    if missing:
        raise FileNotFoundError(f"registered Formal IP document missing: {missing}")
    return documents


def _run(label: str, command: Sequence[str]) -> None:
    print(f"\n== {label} ==")
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


# 返回当前工作树中需要Task Context解释的源码或文档变化。
def _source_worktree_changes() -> tuple[str, ...]:

    completed = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "-c",
            "core.quotepath=false",
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        normalized = value.replace("\\", "/")
        if not normalized.startswith(GENERATED_SCOPE_PREFIXES):
            paths.append(normalized)
    return tuple(sorted(set(paths)))


# 当前源码任务必须存在Task Context，并把新鲜度和实际Diff范围检查纳入同一软件门禁。
def _validate_current_task_context(python: str) -> None:

    if not TASK_CONTEXT_PATH.is_file():
        changed_paths = _source_worktree_changes()
        if changed_paths:
            raise RuntimeError(
                "source changes require a compiled Task Context before software validation: "
                + ", ".join(changed_paths)
            )
        print("\n== Current task context ==")
        print("Task Context not present; clean repository has no task scope to validate.")
        return

    _run(
        "Current task context freshness",
        [python, str(TASK_CONTEXT_TOOL), "check", "--context", str(TASK_CONTEXT_PATH)],
    )
    _run(
        "Current task context scope",
        [
            python,
            str(TASK_CONTEXT_TOOL),
            "scope-check",
            "--context",
            str(TASK_CONTEXT_PATH),
        ],
    )


# 对本次实际变化的Firmware文件执行严格语义数字门禁，避免新代码重新引入魔鬼数字。
def _validate_changed_firmware_quality(python: str, change_base: str | None) -> None:
    command = [
        python,
        str(REPOSITORY_ROOT / "tools/quality/check_firmware_c_quality.py"),
        "--strict-magic",
    ]
    if change_base:
        command.extend(("--base-ref", change_base))
    _run("Firmware C quality / changed files / strict semantic numbers", command)


# 用无硬件的空 Session 验证每个已注册 IP 都能生成有效 ZIP/XLSX 文件。
def _validate_case_report_export(python: str) -> None:
    with tempfile.TemporaryDirectory(prefix="et-case-report-") as directory:
        root = Path(directory)
        (root / "session.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "run_id": "software-gate",
                    "chip_id": "ET6801",
                    "finished_at": "software-gate",
                    "exitstatus": 0,
                }
            ),
            encoding="utf-8",
        )
        for document in formal_case_documents():
            output = root / f"software_gate_{document.stem}_report.xlsx"
            _run(
                f"Case report XLSX export: {document.stem}",
                [
                    python,
                    str(REPORT_TOOL),
                    "--document",
                    str(document),
                    "--results",
                    str(root),
                    "--output",
                    str(output),
                    "--chip",
                    "SOFTWARE_GATE",
                ],
            )
            if not output.is_file() or output.stat().st_size < 1024:
                raise RuntimeError(f"Case report XLSX was not generated correctly: {output}")
            if output.read_bytes()[:2] != b"PK":
                raise RuntimeError(f"Case report output is not a valid XLSX container: {output}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified non-hardware software validation.")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument(
        "--change-base",
        help="Git base revision used by the complete IP contract synchronization check",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    python = sys.executable
    quality_paths = [str(REPOSITORY_ROOT / item) for item in QUALITY_PATHS]
    try:
        _run("Python syntax", [python, "-m", "compileall", "-q", *quality_paths])
        _run("Ruff format", [python, "-m", "ruff", "format", "--check", *quality_paths])
        _run("Ruff lint", [python, "-m", "ruff", "check", *quality_paths])
        _run(
            "Agent rule governance traceability",
            [python, str(REPOSITORY_ROOT / "tools/quality/validate_rule_governance.py")],
        )
        _run(
            "Task context navigation governance",
            [
                python,
                str(REPOSITORY_ROOT / "tools/governance/compile_task_context.py"),
                "validate",
            ],
        )
        _validate_current_task_context(python)
        ip_change_command = [
            python,
            str(REPOSITORY_ROOT / "tools/quality/check_ip_change_rules.py"),
            "--all-chip-neutral",
        ]
        if args.change_base:
            ip_change_command.extend(("--base-ref", args.change_base))
        _run(
            "IP contract sync / full public chip-neutral rules",
            ip_change_command,
        )
        _run(
            "Public stable IP contract chip-neutrality",
            [python, str(REPOSITORY_ROOT / "tools/quality/check_public_ip_contracts.py")],
        )
        _run(
            "Chip IP adaptation contract completeness",
            [python, str(REPOSITORY_ROOT / "tools/quality/validate_chip_ip_docs.py")],
        )
        _run(
            "PC AST architecture rules",
            [
                python,
                str(REPOSITORY_ROOT / "tools/quality/check_pc_code_rules.py"),
                "--root",
                str(REPOSITORY_ROOT),
                *quality_paths,
            ],
        )
        _run(
            "PC documentation semantics",
            [
                python,
                str(REPOSITORY_ROOT / "tools/quality/check_pc_documentation_rules.py"),
                "--root",
                str(REPOSITORY_ROOT),
                str(REPOSITORY_ROOT / "pc/et_test_platform"),
            ],
        )
        _run(
            "Formal Case specification contract",
            [python, str(REPOSITORY_ROOT / "tools/quality/validate_case_docs.py")],
        )
        _run(
            "Formal Case specification implementation binding",
            [python, str(REPOSITORY_ROOT / "tools/quality/check_case_spec_implementation.py")],
        )
        _run(
            "Planning Case document contract",
            [python, str(REPOSITORY_ROOT / "tools/quality/validate_case_plans.py")],
        )
        _run(
            "Case human-review line grammar",
            [python, str(REPOSITORY_ROOT / "tools/quality/validate_case_method_contract.py")],
        )
        _run(
            "Formal Case orchestration rules",
            [
                python,
                str(REPOSITORY_ROOT / "tools/quality/check_case_orchestration_rules.py"),
                "--root",
                str(REPOSITORY_ROOT),
                str(REPOSITORY_ROOT / FORMAL_CASE_ROOT),
            ],
        )
        _run(
            "Firmware single-IP execution rules",
            [
                python,
                str(REPOSITORY_ROOT / "tools/quality/check_firmware_architecture_rules.py"),
                str(REPOSITORY_ROOT),
            ],
        )
        _run(
            "Firmware C format",
            [python, str(REPOSITORY_ROOT / "tools/quality/check_firmware_c_format.py")],
        )
        _run(
            "Firmware C quality / full tree",
            [
                python,
                str(REPOSITORY_ROOT / "tools/quality/check_firmware_c_quality.py"),
                "--all",
            ],
        )
        _validate_changed_firmware_quality(python, args.change_base)
        if not args.skip_tests:
            for manifest in firmware_manifests():
                _run(
                    f"Generated firmware project contract: {manifest.parent.name}",
                    [python, str(FIRMWARE_RECORD_TOOL), "--manifest", str(manifest)],
                )
            _run("PC unit / contract / native tests", [python, "-m", "pytest", UNIT_TEST_ROOT])
            _run(
                "Formal Case collection",
                [python, "-m", "pytest", "--collect-only", "-q", FORMAL_CASE_ROOT],
            )
            _validate_case_report_export(python)
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    except RuntimeError as error:
        print(f"Software validation failed: {error}", file=sys.stderr)
        return 1
    print("\nSoftware validation completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
