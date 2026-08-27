# Framework Validation任务导航治理测试。
#
# 职责：验证工程地图、模块画像、规则Owner和Task Context之间的确定性链路。
# 边界：不执行业务Case、Firmware、硬件或外部工具。
# 依赖：仅动态加载正式Task Context编译器，并使用临时JSON验证失败关闭行为。

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

ROOT = Path(__file__).parents[5]
COMPILER = ROOT / "tools" / "governance" / "compile_task_context.py"
VALIDATOR = ROOT / "tools" / "validate_pc.py"


# 加载与总软件门禁相同的Task Context编译器。
def _load_compiler() -> ModuleType:

    spec = importlib.util.spec_from_file_location("task_context_compiler", COMPILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Task Context compiler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 加载与本地和CI相同的统一软件门禁入口。
def _load_validator() -> ModuleType:

    spec = importlib.util.spec_from_file_location("software_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load software validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 测试Feature：当前工程地图、模块画像和规则Owner引用全部闭合。
#
# 测试方法：直接运行正式导航治理校验，不使用Mock目录或宽松白名单。
#
# 通过条件：没有未知模块、未知Owner、危险路径、重复别名或非法Schema。
def test_current_task_navigation_governance_is_valid() -> None:

    compiler = _load_compiler()

    assert compiler.validate_navigation() == []


# 测试Feature：一个IP Case和Driver任务只加载相关代码入口和规则Owner。
#
# 测试方法：为AES公共Case与Driver编译上下文，并检查架构、阅读入口和写入范围。
#
# 通过条件：上下文包含公共IP契约、Case、Driver及对应规则，不包含具体芯片绑定。
def test_ip_task_context_is_focused_and_chip_neutral() -> None:

    compiler = _load_compiler()

    context = compiler.build_task_context(
        task_id="AES-PC-001",
        intent="开发AES Formal Case和PC Driver",
        modules=["ip-package"],
        changes=["case", "driver"],
        ip="aes",
        lanes=["pc"],
    )

    serialized = json.dumps(context, ensure_ascii=False)
    paths = {entry["path"] for entry in context["must_read"]}
    owners = {entry["owner_id"] for entry in context["rule_owners"]}
    assert "test_case_doc/aes/aes.md" in paths
    assert "pc/et_test_platform/test_cases/aes" in paths
    assert "pc/et_test_platform/drivers/aes" in paths
    assert "pc_case_responsibility" in owners
    assert "pc_layer_responsibilities" in owners
    assert "et6801" not in serialized.lower()
    assert context["write_scope"]["allowed"] == [
        "pc/et_test_platform/test_cases/aes/**",
        "test_case_doc/aes/aes.md",
        "pc/et_test_platform/drivers/aes/**",
        "pc/et_test_platform/framework_validation/unit/drivers/aes/**",
    ]


# 测试Feature：周报任务只路由到周报规则和正式报告目录。
#
# 测试方法：为周报编写任务生成Task Context，并检查Owner、必读规则和写入边界。
#
# 通过条件：上下文包含唯一周报Owner，只允许修改Weekly_report和报告总索引。
def test_weekly_report_task_context_is_focused() -> None:

    compiler = _load_compiler()

    context = compiler.build_task_context(
        task_id="WEEKLY-REPORT-001",
        intent="编写本周项目周报",
        modules=["governance"],
        changes=["weekly-report"],
        lanes=["docs"],
    )

    paths = {entry["path"] for entry in context["must_read"]}
    owners = {entry["owner_id"] for entry in context["rule_owners"]}

    assert "report/design/rules/R003_weekly_report_authoring.md" in paths
    assert "weekly_report_authoring" in owners
    assert context["write_scope"]["allowed"] == [
        "report/Weekly_report/**",
        "report/README.md",
    ]


# 测试Feature：批量Bug修复规则只能提供治理策略，不能授权业务源码修改。
#
# 测试方法：单独编译治理路由，再与UART Case路由组合编译并检查Owner及写入范围。
#
# 通过条件：单独路由只允许维护修复计划；组合后只增加UART Case既有范围，不放宽其他IP或公共层。
def test_bug_remediation_route_is_advisory_and_scope_bounded() -> None:

    compiler = _load_compiler()

    governance_context = compiler.build_task_context(
        task_id="BUG-BATCH-001",
        intent="规划一组Bug修复",
        modules=["governance"],
        changes=["bug-remediation"],
        lanes=["docs"],
    )
    combined_context = compiler.build_task_context(
        task_id="UART-BUG-BATCH-001",
        intent="修复UART Formal Case问题批次",
        modules=["governance", "ip-package"],
        changes=["bug-remediation", "case"],
        ip="uart",
        lanes=["pc"],
    )

    governance_owners = {entry["owner_id"] for entry in governance_context["rule_owners"]}
    combined_owners = {entry["owner_id"] for entry in combined_context["rule_owners"]}

    assert "bug_batch_remediation" in governance_owners
    assert governance_context["write_scope"]["allowed"] == ["report/plans/**"]
    assert "bug_batch_remediation" in combined_owners
    assert combined_context["write_scope"]["allowed"] == [
        "report/plans/**",
        "pc/et_test_platform/test_cases/uart/**",
        "test_case_doc/uart/uart.md",
    ]
    assert "pc/et_test_platform/test_cases/aes/**" not in combined_context["write_scope"]["allowed"]


# 测试Feature：手动固件诊断与PC串口捕获分别进入最小写入范围。
#
# 测试方法：分别编译Firmware手动Case和PC捕获工具上下文，检查共同规则Owner及各自路径。
#
# 通过条件：Firmware只写目标芯片手动目录和入口，PC工具只写manual_test工具目录及其单元测试。
def test_manual_firmware_diagnostic_routes_stay_isolated() -> None:

    compiler = _load_compiler()

    firmware_context = compiler.build_task_context(
        task_id="ET6801-MANUAL-DIAGNOSTIC-001",
        intent="开发ET6801手动固件诊断Case",
        modules=["firmware-platform"],
        changes=["manual-test"],
        chip="et6801",
        lanes=["firmware"],
    )
    capture_context = compiler.build_task_context(
        task_id="MANUAL-SERIAL-CAPTURE-001",
        intent="开发手动诊断串口捕获工具",
        modules=["operator-pipeline"],
        changes=["manual-capture"],
        lanes=["tooling"],
    )

    firmware_owners = {entry["owner_id"] for entry in firmware_context["rule_owners"]}
    capture_owners = {entry["owner_id"] for entry in capture_context["rule_owners"]}

    assert "firmware_manual_diagnostics" in firmware_owners
    assert "firmware_manual_diagnostics" in capture_owners
    assert firmware_context["write_scope"]["allowed"] == [
        "firmware/manual_tests/et6801/**",
        "firmware/application/src/main.c",
        "firmware/chips/et6801/project.yaml",
        "firmware/build/et6801/**",
    ]
    assert capture_context["write_scope"]["allowed"] == [
        "tools/manual_test/**",
        "pc/et_test_platform/framework_validation/unit/operator/test_manual_serial_capture.py",
    ]


# 测试Feature：芯片Capability任务必须显式提供芯片，且只把芯片事实放入适配路径。
#
# 测试方法：先省略chip验证失败关闭，再以et6801重新编译并检查适配入口。
#
# 通过条件：缺少chip时拒绝；提供后只增加芯片文档、Capability和映射写入范围。
def test_capability_task_requires_explicit_chip() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="requires task parameter"):
        compiler.build_task_context(
            task_id="AES-CAP-001",
            intent="生成目标芯片AES Capability",
            modules=["ip-package"],
            changes=["capability"],
            ip="aes",
        )

    context = compiler.build_task_context(
        task_id="AES-CAP-001",
        intent="生成目标芯片AES Capability",
        modules=["ip-package"],
        changes=["capability"],
        ip="aes",
        chip="et6801",
    )

    paths = {entry["path"] for entry in context["must_read"]}
    assert "test_case_doc/aes/ET6801_aes.md" in paths
    assert "pc/et_test_platform/profiles/chip_capabilities/et6801/ip/aes.yaml" in paths
    assert "test_case_doc/aes/ET6801_aes.md" in context["write_scope"]["allowed"]
    assert "test_case_doc/aes/et6801_aes.md" not in context["write_scope"]["allowed"]


# 测试Feature：Wrap任务必须显式选择芯片，并路由到真实Chip Config目录。
#
# 测试方法：先省略chip编译UART Wrap任务，再提供et6801并检查允许写入路径。
#
# 通过条件：缺少chip时失败关闭；提供后只授权公共UART Wrap、公共契约和目标芯片Config。
def test_wrap_task_requires_explicit_chip_and_routes_chip_config() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="requires task parameter"):
        compiler.build_task_context(
            task_id="UART-WRAP-001",
            intent="维护UART公共Wrap及目标芯片映射",
            modules=["ip-package"],
            changes=["wrap"],
            ip="uart",
        )

    context = compiler.build_task_context(
        task_id="UART-WRAP-001",
        intent="维护UART公共Wrap及目标芯片映射",
        modules=["ip-package"],
        changes=["wrap"],
        ip="uart",
        chip="et6801",
    )

    assert context["write_scope"]["allowed"] == [
        "firmware/wrap/include/et_uart_wrap.h",
        "firmware/wrap/src/et_uart_wrap.c",
        "firmware/chips/et6801/config/et_chip_wrap_config.h",
        "test_case_doc/uart/uart.md",
    ]


# 测试Feature：新IP必须基于明确目标芯片先完成分析契约，再进入Case实现。
#
# 测试方法：先省略chip验证analysis失败关闭，再为不存在的IP和et6801编译analysis，最后尝试提前编译Case。
#
# 通过条件：analysis必须显式提供chip并加载R120/PLAN门禁；公共契约不存在时Case仍失败关闭。
def test_new_ip_bootstrap_is_analysis_first() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="requires task parameter"):
        compiler.build_task_context(
            task_id="SPI-ANALYSIS-001",
            intent="创建SPI公共IP分析契约",
            modules=["ip-package"],
            changes=["analysis"],
            ip="spi_not_created",
            lanes=["docs"],
        )

    context = compiler.build_task_context(
        task_id="SPI-ANALYSIS-001",
        intent="基于ET6801创建SPI公共IP分析契约",
        modules=["ip-package"],
        changes=["analysis"],
        ip="spi_not_created",
        chip="et6801",
        lanes=["docs"],
    )
    paths = {entry["path"] for entry in context["must_read"]}
    owners = {entry["owner_id"] for entry in context["rule_owners"]}
    public_doc = next(
        entry
        for entry in context["must_read"]
        if entry["path"] == "test_case_doc/spi_not_created/spi_not_created.md"
    )
    chip_doc = next(
        entry
        for entry in context["must_read"]
        if entry["path"] == "test_case_doc/spi_not_created/ET6801_spi_not_created.md"
    )
    assert public_doc["required"] is False
    assert public_doc["exists"] is False
    assert chip_doc["required"] is False
    assert chip_doc["exists"] is False
    assert "report/design/rules/R120_public_ip_machine_contract.md" in paths
    assert "ip_analysis_workflow" in owners
    assert "public_ip_machine_contract" in owners
    assert context["validation"] == [
        "python tools/quality/check_public_ip_contracts.py",
        "python tools/quality/validate_case_plans.py test_case_doc/spi_not_created/spi_not_created.md",
        "python tools/quality/validate_chip_ip_docs.py",
    ]

    with pytest.raises(ValueError, match="required navigation source"):
        compiler.build_task_context(
            task_id="SPI-CASE-001",
            intent="在公共契约前错误实现SPI Case",
            modules=["ip-package"],
            changes=["case"],
            ip="spi_not_created",
            lanes=["pc"],
        )


# 测试Feature：真实芯片IP测试结果只能回写对应芯片文档。
#
# 测试方法：为ET6801 UART编译ip-package/test-result Task Context。
#
# 通过条件：Context读取R110/R130，只授权ET6801_uart.md，并启用强制状态表门禁。
def test_ip_test_result_routes_to_chip_document_only() -> None:

    compiler = _load_compiler()

    context = compiler.build_task_context(
        task_id="UART-HIL-RESULT-001",
        intent="回写ET6801 UART真实HIL结果",
        modules=["ip-package"],
        changes=["test-result"],
        ip="uart",
        chip="et6801",
        lanes=["hil"],
    )

    paths = {entry["path"] for entry in context["must_read"]}
    owners = {entry["owner_id"] for entry in context["rule_owners"]}

    assert "report/design/rules/R110_contract_document_sync.md" in paths
    assert "report/design/rules/R130_canonical_result_evidence.md" in paths
    assert "contract_document_sync" in owners
    assert context["write_scope"]["allowed"] == ["test_case_doc/uart/ET6801_uart.md"]
    assert context["validation"] == [
        "python tools/quality/validate_chip_ip_docs.py --require-test-status "
        "test_case_doc/uart/ET6801_uart.md"
    ]

    with pytest.raises(ValueError, match="requires task parameter"):
        compiler.build_task_context(
            task_id="UART-HIL-RESULT-NO-CHIP",
            intent="缺少目标芯片的UART HIL结果回写",
            modules=["ip-package"],
            changes=["test-result"],
            ip="uart",
            lanes=["hil"],
        )


# 测试Feature：模块别名和Lane均由工程地图确定，不接受自由文本。
#
# 测试方法：通过ip别名编译UART Case，并尝试传入未登记Lane。
#
# 通过条件：别名解析为ip-package；未知Lane明确失败关闭。
def test_module_alias_resolves_and_unknown_lane_fails() -> None:

    compiler = _load_compiler()

    context = compiler.build_task_context(
        task_id="UART-CASE-ALIAS-001",
        intent="通过模块别名维护UART Case",
        modules=["ip"],
        changes=["case"],
        ip="uart",
        lanes=["pc"],
    )
    assert context["task"]["modules"] == ["ip-package"]

    with pytest.raises(ValueError, match="unknown task lane"):
        compiler.build_task_context(
            task_id="UART-CASE-LANE-001",
            intent="错误Lane",
            modules=["ip-package"],
            changes=["case"],
            ip="uart",
            lanes=["not-a-lane"],
        )


# 测试Feature：FPGA/HIL任务不能绕过Operator Pipeline和R500执行契约。
#
# 测试方法：先只选择IP模块和FPGA Lane，再显式加入Operator Pipeline及pipeline change。
#
# 通过条件：缺少统一流水线路由时失败；补齐后Context包含operator_pipeline规则Owner。
def test_hardware_task_requires_operator_pipeline_route() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="FPGA/HIL hardware tasks require"):
        compiler.build_task_context(
            task_id="FMAC-FPGA-CASE-001",
            intent="开发并执行FMAC FPGA Case",
            modules=["ip-package"],
            changes=["case"],
            ip="fmac",
            lanes=["fpga"],
        )

    context = compiler.build_task_context(
        task_id="FMAC-FPGA-PIPELINE-001",
        intent="维护FMAC Case及其统一FPGA执行流水线",
        modules=["ip-package", "operator-pipeline"],
        changes=["case", "pipeline"],
        ip="fmac",
        lanes=["fpga"],
    )
    owners = {entry["owner_id"] for entry in context["rule_owners"]}

    assert "operator_pipeline" in owners


# 测试Feature：IP Case任务在开发前获得注释、编排和代码专项门禁。
#
# 测试方法：编译UART Case上下文并检查Owner与验证命令。
#
# 通过条件：R220、Case代码规则和编排规则均进入任务清单。
def test_ip_case_context_routes_python_and_orchestration_rules() -> None:

    compiler = _load_compiler()

    context = compiler.build_task_context(
        task_id="UART-CASE-QUALITY-001",
        intent="维护UART Formal Case",
        modules=["ip-package"],
        changes=["case"],
        ip="uart",
        lanes=["pc"],
    )

    owners = {entry["owner_id"] for entry in context["rule_owners"]}
    assert "python_style_documentation" in owners
    assert any("check_pc_code_rules.py" in command for command in context["validation"])
    assert any("check_case_orchestration_rules.py" in command for command in context["validation"])


# 测试Feature：Task Context允许范围能拒绝本任务新增的越界文件。
#
# 测试方法：用临时上下文和受控Git快照模拟一个合法Case变化和一个core越界变化。
#
# 通过条件：合法变化通过；core变化返回精确越界路径。
def test_task_scope_check_rejects_changes_outside_allowed_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    compiler = _load_compiler()
    context = {
        "schema": "et.task-context.v1",
        "fingerprint": "scope-test",
        "repository": {"available": True, "branch": "review_code", "head": "abc"},
        "scope_baseline": "task_context.json.baseline.json",
        "write_scope": {
            "allowed": ["pc/et_test_platform/test_cases/uart/**"],
            "protected": ["pc/et_test_platform/core/**"],
        },
    }
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    path = tmp_path / "task_context.json"
    path.write_text(json.dumps(context), encoding="utf-8")
    baseline = {
        "schema": "et.task-scope-baseline.v1",
        "repository": context["repository"],
        "context_integrity_fingerprint": context["integrity_fingerprint"],
        "write_scope": context["write_scope"],
        "worktree": {"existing.txt": "same"},
    }
    (tmp_path / "task_context.json.baseline.json").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    monkeypatch.setattr(
        compiler,
        "_git_state",
        lambda: {"available": True, "branch": "review_code", "head": "abc", "dirty": True},
    )
    monkeypatch.setattr(
        compiler,
        "_git_worktree_snapshot",
        lambda: {
            "existing.txt": "same",
            "pc/et_test_platform/test_cases/uart/test_uart_p1.py": "new",
            "pc/et_test_platform/core/errors.py": "unexpected",
        },
    )

    changed, errors = compiler.check_task_scope(path)

    assert changed == [
        "pc/et_test_platform/core/errors.py",
        "pc/et_test_platform/test_cases/uart/test_uart_p1.py",
    ]
    assert errors == ["path is protected by task scope: pc/et_test_platform/core/errors.py"]


# 测试Feature：即使重新计算Context完整性，也不能脱离编译时Scope快照扩大授权。
#
# 测试方法：先保存窄Scope及其Baseline，再只修改运行时allowed并重新计算Context摘要。
#
# 通过条件：Scope检查在读取工作树前即因Baseline授权不一致失败关闭。
def test_task_scope_rejects_resealed_runtime_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    compiler = _load_compiler()
    context = {
        "schema": "et.task-context.v1",
        "fingerprint": "scope-integrity-test",
        "repository": {"available": True, "branch": "review_code", "head": "abc"},
        "scope_baseline": "task_context.json.baseline.json",
        "write_scope": {
            "allowed": ["tools/governance/**"],
            "protected": ["pc/et_test_platform/core/**"],
        },
    }
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    baseline = {
        "schema": "et.task-scope-baseline.v1",
        "repository": context["repository"],
        "context_integrity_fingerprint": context["integrity_fingerprint"],
        "write_scope": context["write_scope"],
        "worktree": {},
    }
    path = tmp_path / "task_context.json"
    baseline_path = tmp_path / "task_context.json.baseline.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    context["write_scope"] = {"allowed": ["**"], "protected": []}
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    path.write_text(json.dumps(context), encoding="utf-8")
    monkeypatch.setattr(
        compiler,
        "_git_state",
        lambda: {"available": True, "branch": "review_code", "head": "abc", "dirty": True},
    )

    changed, errors = compiler.check_task_scope(path)

    assert changed == []
    assert errors == ["Task Scope baseline authorization does not match the Task Context"]


# 测试Feature：保护范围优先于其他模块给出的宽泛允许范围。
#
# 测试方法：让同一路径同时命中allowed和protected，再执行底层范围判定。
#
# 通过条件：公共Firmware文件仍被判为保护范围，不能由组合模块静默放行。
def test_protected_scope_has_precedence_over_allowed_scope() -> None:

    compiler = _load_compiler()
    context = {
        "write_scope": {
            "allowed": ["firmware/**"],
            "protected": ["firmware/framework/**"],
        }
    }

    errors = compiler._scope_violations(
        context,
        ["firmware/framework/et_protocol.c"],
    )

    assert errors == ["path is protected by task scope: firmware/framework/et_protocol.c"]


# 测试Feature：目标IP Chip Driver任务只能修改Own Driver文件。
#
# 测试方法：为STIMER编译Chip Driver上下文，并分别检查STIMER和AES Driver路径。
#
# 通过条件：STIMER头文件和源文件命中允许范围；AES Driver与共享工程Manifest均被拒绝。
def test_chip_driver_scope_rejects_other_ip_and_shared_manifest() -> None:

    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="STIMER-CHIP-DRIVER-001",
        intent="补充STIMER目标芯片Driver",
        modules=["ip-package"],
        changes=["chip-driver"],
        ip="stimer",
        chip="et6801",
    )
    allowed = context["write_scope"]["allowed"]

    assert any(
        compiler._matches_scope(
            "firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_stimer.c",
            scope,
        )
        for scope in allowed
    )
    assert not any(
        compiler._matches_scope(
            "firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_aes.c",
            scope,
        )
        for scope in allowed
    )
    assert not any(
        compiler._matches_scope("firmware/chips/et6801/project.yaml", scope) for scope in allowed
    )


# 测试Feature：Task Context不能在源码已修改后补编并收养现有Diff。
#
# 测试方法：模拟编译器发现Git工作树为dirty，不执行任何真实文件写入。
#
# 通过条件：编译立即失败，并明确要求从干净工作树开始。
def test_task_context_compile_rejects_dirty_worktree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    compiler = _load_compiler()
    monkeypatch.setattr(
        compiler,
        "build_task_context",
        lambda **_arguments: {"repository": {"available": True, "dirty": True}},
    )
    arguments = SimpleNamespace(
        task_id="DIRTY-001",
        intent="错误补编上下文",
        module=["governance"],
        change=["navigation"],
        ip=None,
        chip=None,
        lane=["tooling"],
        output=None,
    )

    with pytest.raises(ValueError, match="worktree must be clean"):
        compiler.compile_task_context(arguments)


# 测试Feature：递归目录Scope同时覆盖根README和任意深度子目录文档。
#
# 测试方法：用同一个`firmware/**/*.md`模式匹配零层和多层文件。
#
# 通过条件：两个合法文档均匹配，非Markdown文件不匹配。
def test_recursive_scope_matches_zero_or_more_directories() -> None:

    compiler = _load_compiler()

    assert compiler._matches_scope("firmware/README.md", "firmware/**/*.md")
    assert compiler._matches_scope("firmware/chips/et6801/README.md", "firmware/**/*.md")
    assert not compiler._matches_scope("firmware/application/main.c", "firmware/**/*.md")


# 测试Feature：单星号只能匹配一个目录段，不能静默扩大模块写入边界。
#
# 测试方法：使用公共Case Runtime的单层Python Scope分别匹配直属文件和IP子目录文件。
#
# 通过条件：直属文件匹配；嵌套IP Case被拒绝；只有双星号Scope允许递归路径。
def test_single_star_scope_does_not_cross_directory_boundary() -> None:

    compiler = _load_compiler()

    assert compiler._matches_scope(
        "pc/et_test_platform/test_cases/ip_registry.py",
        "pc/et_test_platform/test_cases/*.py",
    )
    assert not compiler._matches_scope(
        "pc/et_test_platform/test_cases/aes/test_aes_p0.py",
        "pc/et_test_platform/test_cases/*.py",
    )
    assert compiler._matches_scope(
        "pc/et_test_platform/test_cases/aes/test_aes_p0.py",
        "pc/et_test_platform/test_cases/**",
    )


# 测试Feature：双星号在路径中间和末尾均保持零层或多层目录语义。
#
# 测试方法：用Chip Driver Scope匹配直接Inc目录和多层SDK目录，并检查末尾递归Scope。
#
# 通过条件：合法的零层、多层和末尾递归路径全部匹配，平级错误目录不匹配。
def test_recursive_scope_preserves_segment_boundaries() -> None:

    compiler = _load_compiler()
    scope = "firmware/chips/et6801/sdk/**/Inc/**"

    assert compiler._matches_scope(
        "firmware/chips/et6801/sdk/Inc/et6x_uart.h",
        scope,
    )
    assert compiler._matches_scope(
        "firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_uart.h",
        scope,
    )
    assert not compiler._matches_scope(
        "firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_uart.c",
        scope,
    )


# 测试Feature：任务不能使用所选模块未声明的change kind。
#
# 测试方法：对governance模块请求IP Case变更。
#
# 通过条件：编译器明确拒绝，而不是猜测相近模块或扩展读取范围。
def test_task_context_rejects_unrouted_change_kind() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="does not support"):
        compiler.build_task_context(
            task_id="BROKEN-001",
            intent="错误路由",
            modules=["governance"],
            changes=["case"],
        )


# 测试Feature：每个显式选择的模块必须实际消费至少一个change kind。
#
# 测试方法：组合一个合法IP Case模块和一个不支持Case变更的治理模块。
#
# 通过条件：编译器拒绝零匹配的额外模块，不能用其他模块的匹配结果掩盖错误路由。
def test_task_context_rejects_selected_module_without_matching_change() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="does not support any requested change kind"):
        compiler.build_task_context(
            task_id="BROKEN-EXTRA-MODULE-001",
            intent="错误增加无职责模块",
            modules=["ip-package", "governance"],
            changes=["case"],
            ip="uart",
        )


# 测试Feature：工程地图登记的每个模块变更都能生成完整、可执行的Task Context。
#
# 测试方法：遍历system-map和全部模块画像，分别使用稳定示例参数编译每条模块路由。
#
# 通过条件：每条路由均有规则Owner、写入边界、验证命令，并记录唯一模块的匹配变更。
def test_every_registered_module_change_compiles_to_a_closed_context() -> None:

    compiler = _load_compiler()
    system_map = compiler._load_yaml(compiler.SYSTEM_MAP)

    for module_entry in system_map["modules"]:
        module_id = module_entry["id"]
        profile = compiler._load_yaml(compiler._safe_repository_path(module_entry["profile"]))
        for change in profile["changes"]:
            context = compiler.build_task_context(
                task_id=f"ROUTE-{module_id}-{change}",
                intent=f"验证{module_id}/{change}模块路由",
                modules=[module_id],
                changes=[change],
                ip="uart" if module_id == "ip-package" else None,
                chip=(
                    "et6801"
                    if module_id in {"ip-package", "pc-platform", "firmware-platform"}
                    else None
                ),
            )

            assert context["rule_owners"], f"{module_id}/{change} has no rules"
            assert context["write_scope"]["allowed"], f"{module_id}/{change} has no writes"
            assert context["validation"], f"{module_id}/{change} has no validation"
            assert context["task"]["matched_changes_by_module"] == {module_id: [change]}


# 测试Feature：IP和芯片参数不能通过路径片段扩大允许修改范围。
#
# 测试方法：把IP参数设置为包含目录分隔符的值并编译公共IP任务。
#
# 通过条件：编译器在模板展开前拒绝该参数，不产生越界路径或Task Context。
def test_task_context_rejects_scope_injection_parameter() -> None:

    compiler = _load_compiler()

    with pytest.raises(ValueError, match="must be one identifier"):
        compiler.build_task_context(
            task_id="BROKEN-002",
            intent="错误路径参数",
            modules=["ip-package"],
            changes=["case"],
            ip="aes/../../core",
        )


# 测试Feature：Task Context输入发生变化后不能继续作为当前导航依据。
#
# 测试方法：生成真实上下文后篡改其输入指纹，再调用正式新鲜度检查。
#
# 通过条件：检查返回stale并要求重新编译。
def test_task_context_stale_fingerprint_fails_closed(tmp_path: Path) -> None:

    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="GOV-001",
        intent="维护任务导航链路",
        modules=["governance"],
        changes=["navigation"],
    )
    context["fingerprint"] = "0" * 64
    path = tmp_path / "task_context.json"
    path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

    errors = compiler.check_task_context(path)

    assert errors == ["Task Context is stale; recompile it before continuing"]


# 测试Feature：运行时Task Context不能通过直接改写allowed/protected扩大任务权限。
#
# 测试方法：生成真实Context后只篡改write_scope，不同步编译器生成的完整性摘要。
#
# 通过条件：check在任何授权豁免前失败关闭，并要求重新编译Context。
def test_task_context_runtime_authorization_tamper_fails_closed(tmp_path: Path) -> None:

    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="GOV-INTEGRITY-001",
        intent="维护任务导航完整性",
        modules=["governance"],
        changes=["navigation"],
    )
    context["write_scope"] = {"allowed": ["**"], "protected": []}
    path = tmp_path / "task_context.json"
    path.write_text(json.dumps(context, ensure_ascii=False), encoding="utf-8")

    assert compiler.check_task_context(path) == [
        "Task Context is stale; recompile it before continuing"
    ]


# 测试Feature：治理任务可以修改原Context已授权的规则输入，但不能采用修改后的范围扩权。
#
# 测试方法：构造一个指向临时规则文件的Context，改变文件内容并让重建指纹发生变化。
#
# 通过条件：原allowed范围覆盖该规则时Context保持有效；原范围不覆盖时仍判定stale。
def test_task_context_keeps_original_scope_for_authorized_governance_input_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    compiler = _load_compiler()
    monkeypatch.setattr(compiler, "ROOT", tmp_path)
    source = tmp_path / "report" / "design" / "rules" / "R002.md"
    source.parent.mkdir(parents=True)
    source.write_text("before\n", encoding="utf-8")
    repository = {"available": True, "branch": "review_code", "head": "abc", "dirty": False}
    context = {
        "schema": "et.task-context.v1",
        "fingerprint": "original",
        "task": {
            "id": "GOV-RULE-001",
            "intent": "维护导航规则",
            "modules": ["governance"],
            "changes": ["rule"],
            "lanes": ["tooling"],
            "ip": None,
            "chip": None,
        },
        "repository": repository,
        "source_inputs": [
            {
                "path": "report/design/rules/R002.md",
                "sha256": compiler._file_sha256(source),
            }
        ],
        "write_scope": {
            "allowed": ["report/design/**"],
            "protected": [],
        },
    }
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    path = tmp_path / "task_context.json"
    path.write_text(json.dumps(context), encoding="utf-8")
    source.write_text("after\n", encoding="utf-8")
    monkeypatch.setattr(
        compiler,
        "build_task_context",
        lambda **_arguments: {
            "fingerprint": "rebuilt",
            "repository": {**repository, "dirty": True},
        },
    )

    assert compiler.check_task_context(path) == []

    context["write_scope"]["allowed"] = ["tools/**"]
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    path.write_text(json.dumps(context), encoding="utf-8")

    assert compiler.check_task_context(path) == [
        "Task Context is stale; recompile it before continuing"
    ]


# 测试Feature：合法治理输入变化不能掩盖分支或HEAD已经变化这一独立失效条件。
#
# 测试方法：让规则文件变化仍命中原allowed，同时让重建Context返回不同HEAD。
#
# 通过条件：check优先判定仓库身份变化并失败关闭，不进入治理输入豁免。
def test_authorized_source_change_cannot_hide_repository_identity_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    compiler = _load_compiler()
    monkeypatch.setattr(compiler, "ROOT", tmp_path)
    source = tmp_path / "report" / "design" / "rules" / "R002.md"
    source.parent.mkdir(parents=True)
    source.write_text("before\n", encoding="utf-8")
    context = {
        "schema": "et.task-context.v1",
        "fingerprint": "original",
        "task": {
            "id": "GOV-HEAD-001",
            "intent": "维护导航规则",
            "modules": ["governance"],
            "changes": ["rule"],
            "lanes": ["tooling"],
            "ip": None,
            "chip": None,
        },
        "repository": {
            "available": True,
            "branch": "review_code",
            "head": "abc",
            "dirty": False,
        },
        "source_inputs": [
            {
                "path": "report/design/rules/R002.md",
                "sha256": compiler._file_sha256(source),
            }
        ],
        "write_scope": {"allowed": ["report/design/**"], "protected": []},
    }
    context["integrity_fingerprint"] = compiler._context_integrity_fingerprint(context)
    path = tmp_path / "task_context.json"
    path.write_text(json.dumps(context), encoding="utf-8")
    source.write_text("after\n", encoding="utf-8")
    monkeypatch.setattr(
        compiler,
        "build_task_context",
        lambda **_arguments: {
            "fingerprint": "rebuilt",
            "repository": {
                "available": True,
                "branch": "review_code",
                "head": "def",
                "dirty": True,
            },
        },
    )

    assert compiler.check_task_context(path) == [
        "Task Context is stale; recompile it before continuing"
    ]


# 测试Feature：生成的运行证据和Excel报告不计入源码任务范围变化。
#
# 测试方法：读取Task Context编译器的固定工作树排除项。
#
# 通过条件：runs和reports两个正式生成目录均被排除，其他源码目录不被放宽。
def test_task_scope_excludes_only_formal_generated_artifacts() -> None:

    compiler = _load_compiler()

    assert compiler.WORKTREE_EXCLUDES == (
        "artifacts/runs/**",
        "artifacts/reports/**",
    )


# 测试Feature：统一软件门禁不能遗漏当前Agent任务的新鲜度和实际Diff范围检查。
#
# 测试方法：提供一个受控Task Context文件并拦截统一门禁的子命令调用。
#
# 通过条件：同一次门禁依次执行现有Task Context的check和scope-check。
def test_unified_software_gate_checks_current_task_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    validator = _load_validator()
    context = tmp_path / "current_task_context.json"
    context.write_text("{}\n", encoding="utf-8")
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(validator, "TASK_CONTEXT_PATH", context)
    monkeypatch.setattr(
        validator,
        "_run",
        lambda label, command: calls.append((label, list(command))),
    )

    validator._validate_current_task_context("python")

    assert [label for label, _command in calls] == [
        "Current task context freshness",
        "Current task context scope",
    ]
    assert [command[2] for _label, command in calls] == ["check", "scope-check"]
    assert all(command[-2:] == ["--context", str(context)] for _label, command in calls)


# 测试Feature：普通用户或CI没有临时Task Context时仍可运行统一软件门禁。
#
# 测试方法：把Task Context路径指向不存在文件并拦截子命令调用。
#
# 通过条件：任务范围检查标记为不适用，不执行伪造或猜测的Scope检查。
def test_unified_software_gate_keeps_non_agent_runs_context_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    validator = _load_validator()
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(validator, "TASK_CONTEXT_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(validator, "_source_worktree_changes", lambda: ())
    monkeypatch.setattr(
        validator,
        "_run",
        lambda label, command: calls.append((label, list(command))),
    )

    validator._validate_current_task_context("python")

    assert calls == []


# 测试Feature：有源码变化时不能缺少Task Context运行统一门禁。
#
# 测试方法：模拟不存在Task Context但工作树包含一个Firmware源码变化。
#
# 通过条件：门禁失败关闭并报告变化路径，不把开发任务伪装成普通clean CI运行。
def test_unified_software_gate_rejects_source_changes_without_task_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    validator = _load_validator()
    monkeypatch.setattr(validator, "TASK_CONTEXT_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(
        validator,
        "_source_worktree_changes",
        lambda: ("firmware/wrap/src/et_aes_wrap.c",),
    )

    with pytest.raises(RuntimeError, match="require a compiled Task Context"):
        validator._validate_current_task_context("python")
