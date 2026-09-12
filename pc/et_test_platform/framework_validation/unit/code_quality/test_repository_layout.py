# Framework Validation测试模块。
#
# 职责：验证test_repository_layout 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from pathlib import Path

CODE_ROOT = Path(__file__).parents[5]
PROJECT_ROOT = CODE_ROOT.parent
UNIT_ROOT = Path(__file__).parents[1]


def test_formal_code_root_has_only_stable_categories() -> None:
    # tmp/ 是仓库内唯一的本地临时区（缓存/锁/草稿）；graphflow-out/ 是本地图工具输出。
    # 两者都被 .gitignore 忽略、不进入版本库；临时产物必须留在仓库内，不得写到仓库外。
    scratch = {"tmp", "graphflow-out"}
    assert {
        path.name
        for path in CODE_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.name not in scratch
    } == {
        "firmware",
        "pc",
        "companion",
        "tools",
        "test_case_doc",
        "report",
        "artifacts",
        "project-governance",
        "agent_harness",
    }

    for old_root in ("firmware", "platform", "tests", "configs", "scripts"):
        assert not (PROJECT_ROOT / old_root).exists()


def test_generated_build_files_stay_in_firmware_build() -> None:
    # tmp/ 与 graphflow-out/ 都是本地草稿区（gitignore，不提交）：pytest 现场会在此
    # 生成合成 artifacts/*.log，不代表真实产物布局，因此与其它生成目录一并跳过。
    generated_directories = {"__pycache__", ".pytest_cache", ".Xil", ".git", "tmp", "graphflow-out"}
    build_directories = {"Objects", "Listings"}
    build_suffixes = {".o", ".d", ".axf", ".bin", ".hex", ".jou", ".log"}
    firmware_build_root = CODE_ROOT / "firmware" / "build"
    # 新证据只写records；runs仅兼容既有只读历史，固定布局由Runner专项测试约束。
    artifact_roots = (CODE_ROOT / "artifacts/records", CODE_ROOT / "artifacts/runs")

    for path in CODE_ROOT.rglob("*"):
        if any(part in generated_directories for part in path.parts):
            continue
        if path.name in build_directories:
            assert path.is_relative_to(firmware_build_root)
        if path.is_file() and path.suffix.lower() in build_suffixes:
            assert path.is_relative_to(firmware_build_root) or any(
                path.is_relative_to(root) for root in artifact_roots
            )

    generated_project = (
        CODE_ROOT / "firmware" / "build" / "et6801" / "ET6801_Automated_Test.uvprojx"
    )
    assert generated_project.is_file()
    assert generated_project.is_relative_to(firmware_build_root)


def test_pc_source_tree_matches_layered_architecture() -> None:
    pc_root = CODE_ROOT / "pc"
    package_root = pc_root / "et_test_platform"

    assert {
        "cli",
        "clients",
        "communication",
        "core",
        "drivers",
        "framework_validation",
        "instruments",
        "profiles",
        "programmers",
        "results",
        "scheduling",
        "test_cases",
    } <= {path.name for path in package_root.iterdir() if path.is_dir()}

    assert {
        "bench_topologies",
        "chip_capabilities",
        "chip_execution_mappings",
        "resolvers",
    } == {
        path.name
        for path in (package_root / "profiles").iterdir()
        if path.is_dir() and not path.name.startswith("__")
    }

    assert (CODE_ROOT / "tools" / "capabilities" / "requirements" / "dma_p0.yaml").is_file()
    assert (
        CODE_ROOT
        / "test_case_doc"
        / "reference_data"
        / "et6801"
        / "boards"
        / "et6801_v0_core_board_interfaces.json"
    ).is_file()
    assert not (package_root / "profiles" / "instrument_profiles").exists()
    assert not (package_root / "profiles" / "test_case_capability_requirements").exists()
    assert not (package_root / "profiles" / "chip_capabilities" / "et6801" / "boards").exists()
    assert not (package_root / "profiles" / "chip_capabilities" / "et6801" / "audit").exists()
    assert not (
        package_root / "profiles" / "chip_capabilities" / "et6801" / "quality.json"
    ).exists()
    assert (
        CODE_ROOT
        / "test_case_doc"
        / "reference_data"
        / "et6801"
        / "capability_generation"
        / "quality.json"
    ).is_file()

    assert (package_root / "test_cases" / "README.md").is_file()
    assert (package_root / "framework_validation" / "unit").is_dir()
    assert (package_root / "framework_validation" / "test_data").is_dir()

    assert not (pc_root / "configs").exists()
    assert not (pc_root / "tests").exists()
    assert not (package_root / "transports").exists()


# 验证Unit测试按稳定职责分类，防止历史测试重新堆积到根目录。
def test_framework_validation_unit_tree_is_grouped_by_responsibility() -> None:
    assert {
        path.name
        for path in UNIT_ROOT.iterdir()
        if path.is_dir() and not path.name.startswith((".", "__"))
    } == {
        "baseline",
        "cases",
        "clients",
        "code_quality",
        "communication",
        "core",
        "drivers",
        "firmware_contract",
        "instruments",
        "operator",
        "profiles",
        "results",
        "scheduling",
    }
    assert not list(UNIT_ROOT.glob("test_*.py"))
