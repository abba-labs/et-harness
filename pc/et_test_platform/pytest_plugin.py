# ET 自动化测试平台的 pytest 集成入口。
#
# 职责：注册命令行选项、Marker、Session 结果钩子和平台 Fixture 插件。
# 边界：不实现具体 IP 测试步骤、不解释 Wire；Evidence 完整性只作为平台结果一致性门禁，
# 不替 Test Case 产生 IP 业务断言。
# 依赖：依赖 pytest Hook、scheduling Fixture 与结果记录接口。

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from .results.recorder import bind_result_artifact_sink
from .scheduling.run_context import (
    RunContext,
    case_result_payload,
)
from .scheduling.test_registry import (
    RegistryError,
    discover_formal_case_ids,
    select_registered_cases,
    validate_registered_case_ids,
)
from .test_cases.ip_registry import IP_REGISTRY

pytest_plugins = ("et_test_platform.scheduling.fixtures",)

_RUN_CONTEXT_KEY: pytest.StashKey[RunContext] = pytest.StashKey()
_CASE_STATE_KEY: pytest.StashKey[dict[str, object]] = pytest.StashKey()
_RESULT_INTEGRITY_FAILURE_KEY: pytest.StashKey[bool] = pytest.StashKey()


# 把 Case 使用公共 recorder 生成的 JSON 附件自动绑定到 canonical result。
# Case 仍只负责写硬件事实，公共层只登记路径，不解析 IP 业务语义。
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item) -> Generator[None, object, None]:

    context = item.config.stash.get(_RUN_CONTEXT_KEY, None)
    state = item.stash.get(_CASE_STATE_KEY, None)
    if context is None or state is None:
        yield
        return

    def record_artifact(path: Path) -> None:
        relative_path = context.bind_case_artifact(str(state["case_run_id"]), path)
        property_value = ("measurement_artifact_result", relative_path)
        if property_value not in item.user_properties:
            item.user_properties.append(property_value)

    with bind_result_artifact_sink(record_artifact):
        yield


# 注册 ET 平台命令行选项；只定义运行入口，不执行设备操作或 Case 业务逻辑。
def pytest_addoption(parser: pytest.Parser) -> None:

    group = parser.getgroup("et-test-platform")
    group.addoption(
        "--et-hardware",
        action="store_true",
        default=False,
        help="Explicitly allow Cases that communicate with real hardware.",
    )
    group.addoption(
        "--et-bench",
        help="Bench topology YAML used to construct hardware resources.",
    )
    group.addoption(
        "--et-target",
        default="dut",
        help="Logical target name inside the selected bench profile.",
    )
    group.addoption(
        "--et-artifact-dir",
        help="Required output directory for hardware evidence.",
    )
    group.addoption(
        "--et-source-revision",
        help="Git revision of the platform source selected by the canonical runner.",
    )
    group.addoption(
        "--et-source-dirty",
        action="store_true",
        default=False,
        help="Record that the tested source tree contained uncommitted changes.",
    )
    group.addoption(
        "--et-spec-sha256",
        help="SHA-256 of the public IP specification selected by the canonical runner.",
    )


# 注册 Marker 并创建可选 RunContext；不发送硬件命令或决定 IP 测试结论。
def pytest_configure(config: pytest.Config) -> None:

    config.addinivalue_line(
        "markers",
        "hardware: requires an explicit real-hardware execution gate",
    )
    config.addinivalue_line(
        "markers",
        "ip(name): identifies the primary IP owned by a formal Case package",
    )
    config.addinivalue_line(
        "markers",
        "framework_communication: validates the common PC-DUT link",
    )
    context = RunContext.from_config(config)
    if context is not None:
        config.stash[_RUN_CONTEXT_KEY] = context
        config.stash[_RESULT_INTEGRITY_FAILURE_KEY] = False
        context.write_session()


# 为启用 Result 记录的每个 Case 分配运行标识；不执行 Case 或修改硬件状态。
@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(
    session: pytest.Session,
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:

    del session
    collected_count = len(items)
    case_root = Path(__file__).parent / "test_cases"
    try:
        validate_registered_case_ids(
            IP_REGISTRY,
            discover_formal_case_ids(case_root),
        )
        selection = select_registered_cases(
            items,
            IP_REGISTRY,
            case_root=case_root,
        )
    except RegistryError as exc:
        raise pytest.UsageError(f"invalid ET Formal Case registry: {exc}") from exc

    if selection.deselected:
        config.hook.pytest_deselected(items=list(selection.deselected))
    items[:] = list(selection.selected)

    context = config.stash.get(_RUN_CONTEXT_KEY, None)
    if context is None:
        return
    context.record_selection(
        list(items),
        collected_count=collected_count,
        deselected_count=len(selection.deselected),
    )
    for item in items:
        item.stash[_CASE_STATE_KEY] = {
            "case_run_id": context.allocate_case(),
            "reports": {},
            "written": False,
        }


# 汇总三阶段结果；PASS 缺少 Required Evidence 时同步失败 pytest/JUnit 结果通道。
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo[object],
) -> Generator[None, object, None]:

    outcome = yield
    report = outcome.get_result()
    state = item.stash.get(_CASE_STATE_KEY, None)
    context = item.config.stash.get(_RUN_CONTEXT_KEY, None)
    if state is None or context is None:
        return
    reports = state["reports"]
    if not isinstance(reports, dict):
        raise RuntimeError("pytest Case report state is invalid")
    reports[report.when] = report
    if report.when != "teardown" or bool(state["written"]):
        return

    # 兼容仍通过 record_property 显式登记附件的 Case：所有 ``*_result`` 都在写入
    # canonical result 前绑定到当前 execution，并统一为 Run-relative 路径。
    normalized_properties: list[tuple[str, object]] = []
    for name, value in item.user_properties:
        if name.endswith("_result"):
            if not isinstance(value, (str, Path)):
                raise RuntimeError(f"Case artifact property {name!r} must contain a path")
            value = context.bind_case_artifact(str(state["case_run_id"]), value)
        property_value = (name, value)
        if property_value not in normalized_properties:
            normalized_properties.append(property_value)
    item.user_properties[:] = normalized_properties

    framework = item.funcargs.get("framework_communication")
    config = item.config
    options = config.option
    payload = case_result_payload(
        item=item,
        reports=reports,
        framework=framework,
        target_id=getattr(options, "et_target", None),
        bench_path=getattr(options, "et_bench", None),
        case_run_id=str(state["case_run_id"]),
        run_id=context.run_id,
    )
    context.write_case_result(str(state["case_run_id"]), payload)
    context.record_status(str(payload["status"]))

    if payload["status"] == "EVIDENCE_MISSING":
        # Persist the domain result first, then fail the final pytest report. This keeps
        # result.json's precise status while preventing JUnit/CLI from claiming PASS.
        config.stash[_RESULT_INTEGRITY_FAILURE_KEY] = True
        report.outcome = "failed"
        report.longrepr = str(payload["error"] or "required evidence is missing")

    state["written"] = True


# 写入最终 Session；Evidence 完整性失败时强制非零退出，避免 JSON 与 CLI 双真值。
def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:

    config = session.config
    context = config.stash.get(_RUN_CONTEXT_KEY, None)
    result_integrity_failed = config.stash.get(_RESULT_INTEGRITY_FAILURE_KEY, False)
    if result_integrity_failed and exitstatus == int(pytest.ExitCode.OK):
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        exitstatus = int(session.exitstatus)
    if context is not None:
        context.write_session(exitstatus=int(exitstatus))
