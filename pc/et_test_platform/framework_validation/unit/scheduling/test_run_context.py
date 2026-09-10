# Framework Validation测试模块。
#
# 职责：验证test_run_context 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import ast
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from et_test_platform.results.recorder import bind_result_artifact_sink, write_json_result
from et_test_platform.scheduling.run_context import (
    RunContext,
    case_evidence_sources,
    case_result_payload,
    record_evidence,
    record_observation,
    require_evidence,
)
from tools.runner.clean_generated_outputs import build_cleanup_plan, execute_cleanup


class _FakeItem:
    nodeid = "uart/test_case.py::test_case"
    user_properties: list[tuple[str, object]] = []


class _FakeReport:
    def __init__(self, *, failed: bool = False, skipped: bool = False) -> None:
        self.failed = failed
        self.skipped = skipped
        self.duration = 0.01
        self.longrepr = "phase error" if failed else "phase skipped"


class _FakeFramework:
    chip_id = "et6801"
    firmware_build_id = "build-test"
    registry_hash = "deadbeef"
    transport_identity = "fake:serial"


class _FakeMarker:
    args = ("uart",)
    kwargs: dict[str, object] = {}


class _FakeCallSpec:
    id = "uart1"


class _FormalFakeItem:
    nodeid = "uart/test_uart_p0.py::test_uart_p0_001_capabilities[uart1]"
    name = "test_uart_p0_001_capabilities[uart1]"
    originalname = "test_uart_p0_001_capabilities"
    callspec = _FakeCallSpec()
    user_properties = [
        ("evidence_sources", ["dut"]),
        ("transactions", 20),
        ("uart_result", "artifacts/uart_p0_001.json"),
    ]

    def iter_markers(self, *, name: str):
        return (_FakeMarker(),) if name == "ip" else ()


def _reports(*, setup=None, call=None, teardown=None) -> dict[str, object]:
    return {
        "setup": setup or _FakeReport(),
        "call": call or _FakeReport(),
        "teardown": teardown or _FakeReport(),
    }


# 通用清理不再接受runs；旧历史与Artifact骨架保持不变。
def test_generated_output_cleanup_preserves_artifact_layout(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    runs_root = repository_root / "artifacts" / "runs"
    reports_root = repository_root / "artifacts" / "reports"
    (repository_root / "tools" / "runner").mkdir(parents=True)
    runs_root.mkdir(parents=True)
    reports_root.mkdir(parents=True)
    (repository_root / "artifacts" / "README.md").write_text("artifact rules\n", encoding="utf-8")
    (runs_root / "run-one" / "result.json").parent.mkdir()
    (runs_root / "run-one" / "result.json").write_text("{}\n", encoding="utf-8")
    (runs_root / ".gitkeep").write_text("\n", encoding="utf-8")
    (reports_root / "keep.xlsx").write_bytes(b"report")

    with pytest.raises(ValueError, match="unknown cleanup scopes"):
        build_cleanup_plan(repository_root, ("runs",))
    plan = build_cleanup_plan(repository_root, ("caches",))
    assert plan == []
    execute_cleanup(plan)
    assert runs_root.is_dir()
    assert (runs_root / "run-one/result.json").read_text(encoding="utf-8") == "{}\n"
    assert (reports_root / "keep.xlsx").is_file()
    assert (repository_root / "artifacts" / "README.md").is_file()


# 缓存扫描必须跳过虚拟环境、第三方运行时和Artifact证据目录。
def test_generated_output_cleanup_cache_scope_is_bounded(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    (repository_root / "tools" / "runner").mkdir(parents=True)
    (repository_root / "artifacts").mkdir()
    (repository_root / "artifacts" / "README.md").write_text("artifact rules\n", encoding="utf-8")
    removable = repository_root / "pc" / "package" / "__pycache__"
    egg_info = repository_root / "pc" / "package" / "example.egg-info"
    excluded = repository_root / ".venv" / "package" / "__pycache__"
    artifact_cache = repository_root / "artifacts" / "runs" / "run-one" / "__pycache__"
    for directory in (removable, egg_info, excluded, artifact_cache):
        directory.mkdir(parents=True)
        (directory / "cached.pyc").write_bytes(b"cache")

    plan = build_cleanup_plan(repository_root, ("caches",))

    assert {entry.path for entry in plan} == {removable, egg_info}
    execute_cleanup(plan)
    assert not removable.exists()
    assert not egg_info.exists()
    assert excluded.is_dir()
    assert artifact_cache.is_dir()


# 固定工作区和维护事务不是可随意删除的临时文件；所有通用清理范围均须排除。
def test_cleanup_preserves_fixed_records_and_transaction_recovery(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    (root / "tools/runner").mkdir(parents=True)
    (root / "artifacts").mkdir()
    (root / "artifacts/README.md").write_text("artifact rules", encoding="utf-8")
    protected = (
        root / "artifacts/runs/current",
        root / "artifacts/records/CHIP/IP",
        root / "artifacts/records/CHIP/IP/current",
        root / "artifacts/records/CHIP/IP/_maintenance",
        root / "artifacts/runs/record-maintenance/CHIP_IP",
    )
    for directory in protected:
        (directory / "__pycache__").mkdir(parents=True)
        (directory / "__pycache__/unique.pyc").write_bytes(b"keep")
        (directory / "transaction.json").write_bytes(b"unique recovery data")
    ordinary = root / "tmp/ordinary"
    ordinary.mkdir(parents=True)
    (ordinary / "scratch").write_bytes(b"disposable")
    plan = build_cleanup_plan(root, ("reports", "tmp", "caches"))
    assert [entry.path for entry in plan] == [ordinary]
    execute_cleanup(plan)
    assert all((directory / "transaction.json").is_file() for directory in protected)


def test_case_result_requires_explicitly_registered_evidence(tmp_path: Path) -> None:
    item = _FakeItem()
    item.user_properties = [("required_evidence_sources", ["dut", "peer"])]
    result = case_result_payload(
        item=item,
        reports=_reports(),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-1",
        run_id="run-1",
    )

    assert result["required_evidence_sources"] == ["dut", "peer"]
    assert result["evidence_sources"] == []
    assert result["evidence_complete"] is False
    assert result["missing_evidence_sources"] == ["dut", "peer"]
    assert result["status"] == "EVIDENCE_MISSING"
    assert "missing required evidence" in str(result["error"])
    del tmp_path  # Keep the test signature compatible with pytest temp fixtures.


def test_case_result_passes_when_evidence_is_explicitly_registered() -> None:
    item = _FakeItem()
    item.user_properties = [
        ("required_evidence_sources", ["dut", "peer"]),
        ("evidence_sources", ["dut", "peer", "dut"]),
    ]
    result = case_result_payload(
        item=item,
        reports=_reports(),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-2",
        run_id="run-1",
    )

    assert result["required_evidence_sources"] == ["dut", "peer"]
    assert result["evidence_sources"] == ["dut", "peer"]
    assert result["evidence_complete"] is True
    assert result["missing_evidence_sources"] == []
    assert result["status"] == "PASS"


# Observation 对 PASS 和 FAIL 使用同一结构，并自动登记对应硬件证据源。
def test_record_observation_is_status_neutral_and_enters_case_result() -> None:
    item = _FakeItem()
    item.user_properties = []

    record_observation(
        lambda name, value: item.user_properties.append((name, value)),
        key="result_register",
        value=0x12345678,
        source="dut",
        endpoint="crc0",
    )
    result = case_result_payload(
        item=item,
        reports=_reports(),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-observation",
        run_id="run-1",
    )

    assert result["status"] == "PASS"
    assert result["evidence_sources"] == ["dut"]
    assert result["measurements"] == {}
    assert result["observations"] == [
        {
            "key": "result_register",
            "value": 0x12345678,
            "source": "dut",
            "device_id": "dut",
            "endpoint": "crc0",
            "artifacts": [],
        }
    ]


# 二进制硬件观测必须进入JSON原生Byte数组，报告层才能按bytes_hex稳定展示。
def test_record_observation_normalizes_binary_value_to_byte_array() -> None:
    item = _FakeItem()
    item.user_properties = []

    record_observation(
        lambda name, value: item.user_properties.append((name, value)),
        key="capture_data",
        value=b"\x12\xa5",
        source="dut",
        endpoint="UART_CAPTURE.DATA",
    )
    result = case_result_payload(
        item=item,
        reports=_reports(),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-binary-observation",
        run_id="run-1",
    )

    assert result["observations"][0]["value"] == [0x12, 0xA5]


# Canonical JSON边界必须拒绝无序、非有限和实现私有对象，不能静默转成字符串。
@pytest.mark.parametrize(
    "value,error_type",
    [
        ({1, 2}, TypeError),
        (math.nan, ValueError),
        (math.inf, ValueError),
        ({1: "non-string-key"}, TypeError),
        (object(), TypeError),
    ],
)
def test_write_json_result_rejects_noncanonical_values(
    tmp_path: Path,
    value: object,
    error_type: type[Exception],
) -> None:

    with pytest.raises(error_type):
        write_json_result(tmp_path / "invalid.json", {"value": value})

    assert not (tmp_path / "invalid.json").exists()


# Canonical JSON边界统一处理二进制和Tuple，重新读取后只能得到稳定JSON原生类型。
def test_write_json_result_normalizes_supported_boundary_values(tmp_path: Path) -> None:

    output = write_json_result(
        tmp_path / "canonical.json",
        {"payload": b"\x00\xff", "window": (1, 2), "path": Path("capture.bin")},
    )

    assert json.loads(output.read_text(encoding="utf-8")) == {
        "payload": [0, 255],
        "window": [1, 2],
        "path": "capture.bin",
    }


# 公共 recorder 生成的结构化 JSON 必须可被 canonical result 定位。
def test_write_json_result_can_bind_artifact_to_case_context(tmp_path: Path) -> None:
    recorded: list[Path] = []
    output = tmp_path / "measurement.json"

    with bind_result_artifact_sink(recorded.append):
        write_json_result(output, {"measurement_schema": "et.measurement.v1", "value": 1})

    assert recorded == [output.resolve()]


# 参数化 execution 即使复用同一个源文件名，也必须固化为互不覆盖的 Run-relative 附件。
def test_run_context_binds_reused_artifact_name_to_each_case_execution(tmp_path: Path) -> None:
    context = RunContext(tmp_path / "artifacts")
    source = context.artifact_dir / "shared.json"

    write_json_result(source, {"parameter": "first"})
    first = context.bind_case_artifact("case-first", source)
    assert not source.exists()
    write_json_result(source, {"parameter": "second"})
    second = context.bind_case_artifact("case-second", source)
    assert not source.exists()

    assert first == "cases/case-first/artifacts/shared.json"
    assert second == "cases/case-second/artifacts/shared.json"
    assert not Path(first).is_absolute()
    assert json.loads((context.artifact_dir / first).read_text(encoding="utf-8")) == {
        "parameter": "first"
    }
    assert json.loads((context.artifact_dir / second).read_text(encoding="utf-8")) == {
        "parameter": "second"
    }


# 源在 Session 根时，绑定必须留下 Case 副本并删除源，避免 seal 把残留当 extra。
def test_bind_case_artifact_unlinks_session_root_source(tmp_path: Path) -> None:
    context = RunContext(tmp_path / "artifacts")
    source = context.artifact_dir / "shared.json"
    write_json_result(source, {"parameter": "only"})

    relative = context.bind_case_artifact("case-root", source)
    bound = context.artifact_dir / relative

    assert relative == "cases/case-root/artifacts/shared.json"
    assert bound.is_file()
    assert json.loads(bound.read_text(encoding="utf-8")) == {"parameter": "only"}
    assert not source.exists()


# 已经位于本 Case artifacts 下的附件不得因再次绑定被删除。
def test_bind_case_artifact_keeps_source_already_under_case_artifacts(tmp_path: Path) -> None:
    context = RunContext(tmp_path / "artifacts")
    case_run_id = "case-bound"
    source = context.artifact_dir / "cases" / case_run_id / "artifacts" / "already.json"
    write_json_result(source, {"value": 1})

    relative = context.bind_case_artifact(case_run_id, source)

    assert relative == f"cases/{case_run_id}/artifacts/already.json"
    assert source.is_file()
    assert json.loads(source.read_text(encoding="utf-8")) == {"value": 1}


# teardown 会用已删除的 Session 根路径再次绑定；必须命中已固化副本而不是报源文件丢失。
def test_bind_case_artifact_rebinding_consumed_source_returns_existing_copy(
    tmp_path: Path,
) -> None:
    context = RunContext(tmp_path / "artifacts")
    source = context.artifact_dir / "shared.json"
    write_json_result(source, {"value": 1})
    first = context.bind_case_artifact("case-1", source)
    assert not source.exists()

    second = context.bind_case_artifact("case-1", source)

    assert first == second == "cases/case-1/artifacts/shared.json"
    assert (context.artifact_dir / first).is_file()


def test_run_context_rejects_artifact_outside_current_run(tmp_path: Path) -> None:
    context = RunContext(tmp_path / "artifacts")
    external = tmp_path / "external.json"
    write_json_result(external, {"value": 1})

    with pytest.raises(ValueError, match="inside the current run"):
        context.bind_case_artifact("case-external", external)


def test_external_observation_requires_stable_device_identity() -> None:
    with pytest.raises(ValueError, match="requires device_id"):
        record_observation(
            lambda *_: None,
            key="frequency_hz",
            value=1_000_000,
            source="instrument",
            endpoint="channel_1",
        )


def test_formal_case_result_uses_registry_identity_and_recorded_outputs() -> None:
    result = case_result_payload(
        item=_FormalFakeItem(),
        reports=_reports(),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-formal",
        run_id="run-1",
    )

    assert result["case_id"] == "uart_p0_001"
    assert result["feature"] == "uart_p0_001"
    assert result["ip_id"] == "uart"
    assert result["parameter_id"] == "uart1"
    assert result["parameters"] == {"parameter_id": "uart1"}
    assert result["measurements"] == {"transactions": 20}
    assert result["artifacts"] == {"uart_result": "artifacts/uart_p0_001.json"}


def test_case_result_setup_skip_remains_skip_even_without_evidence() -> None:
    item = _FakeItem()
    item.user_properties = [("required_evidence_sources", ["dut", "peer"])]
    result = case_result_payload(
        item=item,
        reports=_reports(setup=_FakeReport(skipped=True)),
        framework=None,
        target_id="dut",
        bench_path=None,
        case_run_id="case-3",
        run_id="run-1",
    )

    assert result["status"] == "SKIP"
    assert result["evidence_complete"] is False


# A Case may not claim peer evidence when it has no peer fixture.
def test_uart_case_without_peer_fixture_cannot_register_peer_evidence() -> None:

    case_path = Path(__file__).parents[3] / "test_cases" / "uart" / "test_uart_p1.py"
    tree = ast.parse(case_path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_uart_p1_"):
            continue
        arguments = {argument.arg for argument in node.args.args}
        if "uart_peer_handle" in arguments:
            continue
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            if not isinstance(call.func, ast.Name) or call.func.id != "record_evidence":
                continue
            sources = [
                value.value
                for value in call.args[1:]
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            ]
            if "peer" in sources:
                violations.append(node.name)
    assert violations == []


# All IP Cases import the common API; UART helpers must not redefine it.
def test_record_evidence_is_platform_common_api_without_uart_duplicate() -> None:

    run_context_path = Path(__file__).parents[3] / "scheduling" / "run_context.py"
    helper_path = Path(__file__).parents[3] / "test_cases" / "uart" / "uart_helpers.py"
    run_context = ast.parse(run_context_path.read_text(encoding="utf-8"))
    helper = ast.parse(helper_path.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "record_evidence"
        for node in run_context.body
    )
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "record_evidence"
        for node in helper.body
    )
    for filename in (
        "test_uart_p0.py",
        "test_uart_p1.py",
        "test_uart_p2.py",
        "test_uart_p3.py",
    ):
        case_path = Path(__file__).parents[3] / "test_cases" / "uart" / filename
        tree = ast.parse(case_path.read_text(encoding="utf-8"))
        common_import = any(
            isinstance(node, ast.ImportFrom)
            and node.level == 3
            and node.module == "scheduling.run_context"
            and any(alias.name == "record_evidence" for alias in node.names)
            for node in tree.body
        )
        helper_import = any(
            isinstance(node, ast.ImportFrom)
            and node.level == 1
            and node.module == "uart_helpers"
            and any(alias.name == "record_evidence" for alias in node.names)
            for node in tree.body
        )
        assert common_import, f"{case_path.name} must import common evidence API"
        assert not helper_import, f"{case_path.name} must not use UART-local API"


def test_record_evidence_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unsupported evidence source"):
        record_evidence(lambda *_: None, "scope")


def test_require_evidence_rejects_unknown_source() -> None:
    with pytest.raises(ValueError, match="unsupported evidence source"):
        require_evidence(lambda *_: None, "scope")


def test_case_result_preserves_call_and_teardown_failures() -> None:
    item = _FakeItem()
    item.user_properties = []
    result = case_result_payload(
        item=item,
        reports=_reports(
            call=_FakeReport(failed=True),
            teardown=_FakeReport(failed=True),
        ),
        framework=_FakeFramework(),
        target_id="dut",
        bench_path=None,
        case_run_id="case-multi-failure",
        run_id="run-1",
    )

    assert result["status"] == "FAIL"
    assert "[call] phase error" in result["error"]
    assert "[teardown] phase error" in result["error"]


def test_case_evidence_sources_does_not_count_unknown_source() -> None:
    item = _FakeItem()
    item.user_properties = [("evidence_sources", ["dut", "scope", "peer"])]
    assert case_evidence_sources(item) == ["dut", "peer"]


def test_observer_is_a_supported_runtime_evidence_source() -> None:
    item = _FakeItem()
    item.user_properties = [("evidence_sources", ["observer"])]

    assert case_evidence_sources(item) == ["observer"]


def test_session_uses_first_available_target_metadata_without_fabrication(
    tmp_path: Path,
) -> None:
    context = RunContext(tmp_path / "artifacts")
    context.write_case_result(
        "case-4",
        {
            "chip_id": "et6801",
            "firmware_build_id": "build-test",
            "registry_hash": "deadbeef",
            "target_id": "dut",
            "bench_path": "bench.yaml",
            "bench_sha256": "hash",
            "config_hash": "hash",
            "transport_identity": "fake:serial",
            "bitstream_id": None,
            "device_identity": None,
        },
    )
    context.write_session(exitstatus=0)
    session = json.loads((tmp_path / "artifacts" / "session.json").read_text(encoding="utf-8"))

    assert session["chip_id"] == "et6801"
    assert session["firmware_build_id"] == "build-test"
    assert session["registry_hash"] == "deadbeef"
    assert session["config_hash"] == "hash"
    assert session["bitstream_id"] is None
    assert session["device_identity"] is None
    assert session["platform_version"] in {"unpackaged", "0.1.0"}


def test_run_context_records_runner_source_identity(tmp_path: Path) -> None:
    config = SimpleNamespace(
        option=SimpleNamespace(
            et_artifact_dir=str(tmp_path / "artifacts"),
            et_source_revision="abc123",
            et_source_dirty=True,
            et_spec_sha256="deadbeef",
        )
    )

    context = RunContext.from_config(config)
    assert context is not None
    context.write_session(exitstatus=0)
    session = json.loads(context.session_path.read_text(encoding="utf-8"))

    assert session["source_revision"] == "abc123"
    assert session["source_dirty"] is True
    assert session["spec_sha256"] == "deadbeef"


def test_case_result_identity_is_owned_by_run_context(tmp_path: Path) -> None:
    context = RunContext(tmp_path / "artifacts")

    context.write_case_result(
        "actual-case-run",
        {
            "run_id": "stale-run",
            "case_run_id": "stale-case-run",
            "status": "PASS",
        },
    )
    result = json.loads(
        (tmp_path / "artifacts" / "cases" / "actual-case-run" / "result.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["run_id"] == context.run_id
    assert result["case_run_id"] == "actual-case-run"


# The opt-in plugin must persist one run and one result per collected Case.
def test_pytest_plugin_writes_pass_and_skip_case_evidence(tmp_path: Path) -> None:

    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "import pytest\n"
        "def test_pass():\n"
        "    pass\n"
        "@pytest.mark.skip(reason='fixture unavailable')\n"
        "def test_skip():\n"
        "    raise AssertionError\n",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    project_pc = Path(__file__).parents[4]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_pc)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(test_file),
        "-p",
        "et_test_platform.pytest_plugin",
        "--et-artifact-dir",
        str(artifact_dir),
    ]
    completed = subprocess.run(
        command,
        cwd=project_pc.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    session = json.loads((artifact_dir / "session.json").read_text(encoding="utf-8"))
    assert session["schema_version"] == 1
    assert session["run_id"]
    result_files = sorted((artifact_dir / "cases").glob("*/result.json"))
    assert len(result_files) == 2
    results = [json.loads(path.read_text(encoding="utf-8")) for path in result_files]
    assert {result["status"] for result in results} == {"PASS", "SKIP"}
    assert all(result["run_id"] == session["run_id"] for result in results)
    assert all(result["case_run_id"] for result in results)
    assert all(result["evidence_sources"] == [] for result in results)


# 插件必须在下一组参数覆盖共享源文件前，为每个 execution 固化独立附件。
def test_plugin_preserves_parameterized_artifacts_and_relative_references(tmp_path: Path) -> None:

    test_file = tmp_path / "test_parameterized_artifact.py"
    test_file.write_text(
        "import pytest\n"
        "from pathlib import Path\n"
        "from et_test_platform.results.recorder import write_json_result\n"
        "@pytest.mark.parametrize('value', [1, 2], ids=['first', 'second'])\n"
        "def test_parameterized(value, pytestconfig, record_property):\n"
        "    root = Path(pytestconfig.getoption('et_artifact_dir'))\n"
        "    output = write_json_result(root / 'shared.json', {'value': value})\n"
        "    record_property('sample_result', str(output))\n",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    project_pc = Path(__file__).parents[4]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_pc)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_file),
            "-p",
            "et_test_platform.pytest_plugin",
            "--et-artifact-dir",
            str(artifact_dir),
        ],
        cwd=project_pc.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

    result_files = sorted((artifact_dir / "cases").glob("*/result.json"))
    results = [json.loads(path.read_text(encoding="utf-8")) for path in result_files]
    assert {result["parameter_id"] for result in results} == {"first", "second"}
    for result in results:
        references = set(result["artifacts"].values())
        assert len(references) == 1
        reference = references.pop()
        assert not Path(str(reference)).is_absolute()
        assert ".." not in Path(str(reference)).parts
        payload = json.loads((artifact_dir / str(reference)).read_text(encoding="utf-8"))
        expected = 1 if result["parameter_id"] == "first" else 2
        assert payload == {"value": expected}
    assert not (artifact_dir / "shared.json").exists()


# Normal unit runs must not create result files unless explicitly opted in.
def test_plugin_is_noop_without_artifact_option(tmp_path: Path) -> None:

    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_pass():\n    pass\n", encoding="utf-8")
    artifact_dir = tmp_path / "artifacts"
    project_pc = Path(__file__).parents[4]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_pc)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_file),
            "-p",
            "et_test_platform.pytest_plugin",
        ],
        cwd=project_pc.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not artifact_dir.exists()


# Setup/teardown failures must still produce final FAIL Case results.
def test_pytest_plugin_records_setup_and_teardown_failures(tmp_path: Path) -> None:

    test_file = tmp_path / "test_failure_phases.py"
    test_file.write_text(
        "import pytest\n"
        "@pytest.fixture\n"
        "def fail_setup():\n"
        "    raise RuntimeError('setup failed')\n"
        "@pytest.fixture\n"
        "def fail_teardown():\n"
        "    yield\n"
        "    raise RuntimeError('teardown failed')\n"
        "def test_setup_failure(fail_setup):\n"
        "    pass\n"
        "def test_teardown_failure(fail_teardown):\n"
        "    pass\n",
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"
    project_pc = Path(__file__).parents[4]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_pc)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            str(test_file),
            "-p",
            "et_test_platform.pytest_plugin",
            "--et-artifact-dir",
            str(artifact_dir),
        ],
        cwd=project_pc.parent.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    result_files = sorted((artifact_dir / "cases").glob("*/result.json"))
    assert len(result_files) == 2
    results = [json.loads(path.read_text(encoding="utf-8")) for path in result_files]
    assert all(result["status"] == "FAIL" for result in results)
    assert all(result["error"] for result in results)
