# 职责：验证一键运行、Pipeline配置和报告串接的软件契约。
# 依赖：标准库、pytest、PyYAML和工具脚本的纯函数/子进程边界。
# 边界：不打开串口、不运行真实Formal Case，也不模拟DUT功能PASS/FAIL。

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import replace
from itertools import count
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

from et_test_platform.instruments.can_boxes.zlg import ZlgCanBox

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
QUALITY_WORKFLOW = REPOSITORY_ROOT / ".github/workflows/pc-quality.yml"


def _load_tool(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tool module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


BOOTSTRAP = _load_tool("et_test_bootstrap_tool", REPOSITORY_ROOT / "tools/runner/bootstrap.py")
ARTIFACT_LAYOUT = _load_tool("artifact_layout", REPOSITORY_ROOT / "tools/runner/artifact_layout.py")
PIPELINE_PROFILE = _load_tool(
    "pipeline_profile", REPOSITORY_ROOT / "tools/runner/pipeline_profile.py"
)
RUN_PIPELINE = _load_tool("et_run_pipeline_tool", REPOSITORY_ROOT / "tools/runner/run_pipeline.py")
RUN_CONFIG_GUI = _load_tool(
    "et_run_config_gui_tool", REPOSITORY_ROOT / "tools/runner/run_config_gui.py"
)
RUN_IP_TESTS = _load_tool("et_run_ip_tests_tool", REPOSITORY_ROOT / "tools/runner/run_ip_tests.py")
CASE_REPORT = _load_tool(
    "et_generate_case_report_tool", REPOSITORY_ROOT / "tools/reporting/generate_case_report.py"
)
IP_CHANGE_RULES = _load_tool(
    "et_ip_change_rules_tool", REPOSITORY_ROOT / "tools/quality/check_ip_change_rules.py"
)
CASE_DOCS = _load_tool(
    "et_validate_case_docs_tool", REPOSITORY_ROOT / "tools/quality/validate_case_docs.py"
)


def test_repository_keeps_one_run_config_template_and_no_legacy_json() -> None:
    assert (REPOSITORY_ROOT / "run_config.example.yaml").is_file()
    assert not (REPOSITORY_ROOT / "run_config.json").exists()
    assert not (REPOSITORY_ROOT / "run_config.example.json").exists()


def test_tools_root_only_contains_the_stable_gate_and_directory_rules() -> None:
    root_files = {path.name for path in (REPOSITORY_ROOT / "tools").iterdir() if path.is_file()}

    assert root_files == {"README.md", "validate_pc.py"}


# 测试 Feature：ET6801 FPGA正式双核Profile使用专用编排，Silicon仍保持失败关闭。
#
# 测试方法：读取两个Pipeline Profile，检查FPGA正式链路和Silicon诊断链路的脚本边界。
#
# 通过条件：FPGA绑定正式Core0+Peer编排；Silicon继续使用清单驱动脚本且不被误放开。
def test_et6801_dualcore_profiles_use_reviewed_target_workflows() -> None:

    profile_root = REPOSITORY_ROOT / "tools/profiles/pipeline"
    fpga = yaml.safe_load((profile_root / "et6801_fpga_dualcore.yaml").read_text(encoding="utf-8"))
    silicon = yaml.safe_load(
        (profile_root / "et6801_silicon_dualcore.yaml").read_text(encoding="utf-8")
    )

    for step in ("build.firmware", "deploy.firmware"):
        assert fpga["steps"][step]["script"] == "tools/firmware/run_et6801_formal_dualcore.ps1"
        assert silicon["steps"][step]["script"] == "tools/firmware/deploy_dualcore_firmware.ps1"

    silicon_manifest = silicon["steps"]["deploy.firmware"]["arguments"][0]["value"]

    assert fpga["steps"]["deploy.firmware"]["requires"] == [
        "deploy.bitfile",
        "deploy.bootrom",
    ]
    assert silicon_manifest.endswith("et6801_silicon_flash.json")


# 测试 Feature：ET6801正式双核编排保持Core0正式固件和Core1 Peer职责分离。
#
# 测试方法：读取ET6801专用编排脚本，检查构建、PFLASH部署、Peer构建和Mailbox验证入口。
#
# 通过条件：Core0沿用正式脚本，Core1只构建Peer，部署后必须验证Core1 Mailbox。
def test_et6801_formal_dualcore_orchestration_keeps_core_roles_explicit() -> None:

    script = (REPOSITORY_ROOT / "tools/firmware/run_et6801_formal_dualcore.ps1").read_text(
        encoding="utf-8"
    )

    assert "build_et6801_test_firmware.ps1" in script
    assert "flash_and_run_et6801_firmware.ps1" in script
    assert "-Action BuildPeer" in script
    assert "core1_hold" in script
    assert "core1_load_verify" in script
    assert "core1_release" in script
    assert "core1_mailbox_verify" in script


# 测试 Feature：IPCM Peer通过现有双核部署脚本的清单参数选择，不替换SPINLOCK默认镜像。
# 测试方法：比较两个Profile的编译/部署入口、Peer参数和Flash前置阶段。
# 通过条件：只有IPCM显式传入独立清单；两者均保持bitfile、BootROM前置和Core0正式Flash。
def test_ipcm_pipeline_selects_its_peer_without_changing_spinlock() -> None:

    root = REPOSITORY_ROOT / "tools/profiles/pipeline"
    ipcm = yaml.safe_load((root / "et6801_fpga_ipcm.yaml").read_text(encoding="utf-8"))
    spinlock = yaml.safe_load((root / "et6801_fpga_dualcore.yaml").read_text(encoding="utf-8"))

    # 两个阶段必须选择同一Peer，避免编译的是一个镜像而部署另一个镜像。
    for step in ("build.firmware", "deploy.firmware"):
        selected = ipcm["steps"][step]
        assert selected["script"] == spinlock["steps"][step]["script"]
        arguments = {item.get("option"): item for item in selected["arguments"]}
        assert arguments["-PeerManifest"]["value"].endswith("et6801_fpga_ipcm.json")
        assert arguments["-PeerManifest"]["base"] == "repository"
        assert not any(
            item.get("option") == "-PeerManifest" for item in spinlock["steps"][step]["arguments"]
        )

    assert ipcm["steps"]["deploy.firmware"]["requires"] == ["deploy.bitfile", "deploy.bootrom"]
    assert ["deploy.firmware", "execute.start_target"] in (ipcm.get("constraints") or {}).get(
        "mutually_exclusive", []
    )


# 测试 Feature：正式双核脚本兼容流水线实际调用的Windows PowerShell 5。
# 测试方法：由Windows PowerShell 5解析双核入口，不执行构建或硬件动作。
# 通过条件：原生解析器无语法错误，不能仅凭文本关键字检查宣称脚本可执行。
def test_formal_dualcore_script_parses_in_windows_powershell() -> None:

    powershell = shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("Windows PowerShell is not installed on this software-test host")
    path = REPOSITORY_ROOT / "tools/firmware/run_et6801_formal_dualcore.ps1"
    escaped = str(path).replace("'", "''")
    command = (
        "$tokens=$null; $errors=$null; "
        f"[void][System.Management.Automation.Language.Parser]::ParseFile('{escaped}', "
        "[ref]$tokens,[ref]$errors); if ($errors.Count) { $errors | Out-String; exit 1 }"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stdout.decode(errors="replace")


# 测试 Feature：ET6801双核清单完整表达两个Core并对Silicon真实部署失败关闭。
#
# 测试方法：读取FPGA与Silicon清单，检查Schema、Core集合、装载地址和部署门禁。
#
# 通过条件：FPGA允许已验证的ITCM部署；Silicon仅声明PFLASH0/PFLASH1事实且保持禁用。
def test_et6801_dualcore_manifests_keep_target_facts_isolated() -> None:

    manifest_root = REPOSITORY_ROOT / "firmware/chips/et6801/core1_peer/deploy"
    fpga = json.loads((manifest_root / "et6801_fpga_itcm.json").read_text(encoding="utf-8"))
    silicon = json.loads((manifest_root / "et6801_silicon_flash.json").read_text(encoding="utf-8"))

    assert fpga["schema"] == silicon["schema"] == "et-dualcore-deploy/v1"
    assert [core["id"] for core in fpga["cores"]] == ["core0", "core1"]
    assert [core["id"] for core in silicon["cores"]] == ["core0", "core1"]
    assert [core["load_address"] for core in fpga["cores"]] == ["0x00000000", "0x00000000"]
    assert [core["load_address"] for core in silicon["cores"]] == [
        "0x08000000",
        "0x08080000",
    ]
    assert fpga["deployment_enabled"] is True
    assert silicon["deployment_enabled"] is False
    assert silicon["blocked_reason"]


# 测试 Feature：双核ITCM部署在Core0运行前完成两个Core镜像装载。
#
# 测试方法：读取公共部署脚本，比较Core0装载、Core1装载和Core0运行调用的源码顺序。
#
# 通过条件：执行顺序固定为Core0 Load/Halt、Core1 Load/Verify、Core0 Run。
def test_et6801_dualcore_ram_deploy_loads_peer_before_launcher_runs() -> None:

    script = (REPOSITORY_ROOT / "tools/firmware/deploy_dualcore_firmware.ps1").read_text(
        encoding="utf-8"
    )

    core0_load = script.index("$core0LoadResult = Invoke-JLink")
    core1_load = script.index("$core1Result = Invoke-JLink", core0_load)
    core0_run = script.index("$core0RunResult = Invoke-JLink", core1_load)

    assert core0_load < core1_load < core0_run
    assert "('mem32 0x{0:X8}, 2' -f $core0Image.load_address)" in script[core0_run:]
    assert "'g'" in script[core0_run:]


# 测试 Feature：公司仓库复制工具只执行单向覆盖复制。
#
# 测试方法：读取PowerShell入口，检查源文件清单、产物排除、直接覆盖和Hash复核。
#
# 通过条件：工具不检查目标Git状态、不删除目标文件，也不会复制测试产物或执行Git写操作。
def test_company_repository_sync_has_a_bounded_and_verified_copy_contract() -> None:

    script = (REPOSITORY_ROOT / "tools/runner/repository_sync/sync_to_company_repo.ps1").read_text(
        encoding="utf-8"
    )

    assert "ls-files -z --cached --others --exclude-standard" in script
    assert "StandardOutputEncoding = [Text.Encoding]::UTF8" in script
    assert "Assert-CleanWorktree" not in script
    assert "artifacts/runs/" in script
    assert "artifacts/reports/" in script
    assert "$PSCmdlet.ShouldProcess" not in script
    assert "[IO.File]::Copy($sourcePath, $targetPath, $true)" in script
    assert "[IO.File]::Delete" not in script
    assert "Get-FileSha256" in script
    assert "git add" not in script.lower()
    assert "git commit" not in script.lower()
    assert "git push" not in script.lower()


# 测试 Feature：一键BAT从自身目录调用唯一同步实现，并允许显式覆盖目标路径。
#
# 测试方法：读取BAT入口，检查脚本相对寻址、默认公司路径、首参数覆盖和退出码传播。
#
# 通过条件：从任意当前目录双击都能定位实现，失败不会被BAT伪装成成功。
def test_company_repository_sync_batch_is_location_independent() -> None:

    launcher_path = REPOSITORY_ROOT / "tools/runner/repository_sync/sync_to_company_repo.bat"
    launcher_bytes = launcher_path.read_bytes()
    launcher = launcher_bytes.decode("ascii")

    assert b"\r\n" in launcher_bytes
    assert b"\n" not in launcher_bytes.replace(b"\r\n", b"")
    assert "%~dp0sync_to_company_repo.ps1" in launcher
    assert 'if not "%~1"=="" set "TARGET_REPOSITORY=%~1"' in launcher
    assert "-AllowDirtySource" not in launcher
    assert "-Confirm" not in launcher
    assert "Et_Automated_Testing_Platform_Code\\et_automated_testing_platform" in launcher
    assert "exit /b %SYNC_EXIT_CODE%" in launcher


# 测试 Feature：公司仓库复制工具允许源端和目标端同时存在未提交修改。
#
# 测试方法：
# 1. 创建内容一致且工作树干净的临时源仓库和目标仓库。
# 2. 修改源文件，同时在目标仓库修改同名文件并增加目标独有文件。
# 3. 执行真实复制，再检查覆盖、保留和排除结果。
#
# 通过条件：
# 1. 源端正式文件直接覆盖目标同名文件，新增文件进入目标仓库。
# 2. 目标独有文件和源端已删除文件保留，忽略文件、本机配置和运行产物不被复制。
def test_company_repository_sync_copies_dirty_source_worktree(tmp_path: Path) -> None:

    git = shutil.which("git")
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")

    if git is None or powershell is None:
        pytest.skip("Git and PowerShell are required for the repository synchronization test")

    source = tmp_path / "source"
    target = tmp_path / "target"
    script = REPOSITORY_ROOT / "tools/runner/repository_sync/sync_to_company_repo.ps1"

    def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    for repository in (source, target):
        repository.mkdir()
        run([git, "init"], cwd=repository)
        run([git, "config", "user.name", "ET Sync Test"], cwd=repository)
        run([git, "config", "user.email", "et-sync-test@example.invalid"], cwd=repository)
        (repository / ".gitignore").write_text("ignored.tmp\n", encoding="utf-8")
        (repository / "stable.txt").write_text("committed content\n", encoding="utf-8")
        (repository / "obsolete.txt").write_text("obsolete content\n", encoding="utf-8")
        run([git, "add", "."], cwd=repository)
        run([git, "commit", "-m", "baseline"], cwd=repository)

    (target / "stable.txt").write_text("target local content\n", encoding="utf-8")
    (target / "target_only.txt").write_text("keep target file\n", encoding="utf-8")

    (source / "stable.txt").write_text("dirty tracked content\n", encoding="utf-8")
    (source / "obsolete.txt").unlink()
    (source / "new_module").mkdir()
    (source / "new_module/new.txt").write_text("new source file\n", encoding="utf-8")
    (source / "中文 规则").mkdir()
    (source / "中文 规则/测试文件.md").write_text("中文路径内容\n", encoding="utf-8")
    (source / "ignored.tmp").write_text("ignored\n", encoding="utf-8")
    (source / "run_config.yaml").write_text("local: true\n", encoding="utf-8")
    (source / "artifacts/runs/case").mkdir(parents=True)
    (source / "artifacts/runs/case/output.log").write_text("generated\n", encoding="utf-8")

    completed = run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-SourceRoot",
            str(source),
            "-Destination",
            str(target),
        ]
    )

    assert "Copy completed and all selected files passed SHA256 verification." in completed.stdout
    assert (target / "stable.txt").read_text(encoding="utf-8") == "dirty tracked content\n"
    assert (target / "new_module/new.txt").read_text(encoding="utf-8") == "new source file\n"
    assert (target / "中文 规则/测试文件.md").read_text(encoding="utf-8") == "中文路径内容\n"
    assert (target / "obsolete.txt").read_text(encoding="utf-8") == "obsolete content\n"
    assert (target / "target_only.txt").read_text(encoding="utf-8") == "keep target file\n"
    assert not (target / "ignored.tmp").exists()
    assert not (target / "run_config.yaml").exists()
    assert not (target / "artifacts/runs/case/output.log").exists()


# 测试 Feature：规则导航和模块画像变更必须触发远程软件总门禁。
#
# 测试方法：读取GitHub软件门禁工作流，检查PR路径过滤和统一验证入口。
#
# 通过条件：project-governance全部变更均被监听，且工作流调用唯一总门禁。
def test_quality_workflow_watches_governance_inputs() -> None:

    source = QUALITY_WORKFLOW.read_text(encoding="utf-8")

    assert '      - "project-governance/**"' in source
    assert "python tools/validate_pc.py" in source


# 测试 Feature：已注册 Formal IP 必须具有公开 Case 文档和完整报告备注契约。
#
# 测试方法：
# 1. 构造只含 Case Registry、但缺少公开文档的最小 IP Package。
# 2. 直接校验没有 ET_CASE_REPORT 的文档片段。
#
# 通过条件：
# 1. 缺少公开文档时返回 ETCASE001。
# 2. 缺少报告备注契约时返回 ETCASE600，不能以“旧 IP”名义放行。
def test_case_document_gate_rejects_missing_public_doc_and_report_contract(tmp_path: Path) -> None:

    package = tmp_path / "pc" / "et_test_platform" / "test_cases" / "demo"
    package.mkdir(parents=True)
    (package / "case_registry.py").write_text("CASE_REGISTRY = ()\n", encoding="utf-8")

    documents = CASE_DOCS.discover_case_documents(root=tmp_path)
    violations = CASE_DOCS.validate_paths(documents, root=tmp_path)

    assert {violation.code for violation in violations} == {"ETCASE001"}

    missing_report = CASE_DOCS._validate_report_notes(
        tmp_path / "test_case_doc" / "demo" / "demo.md",
        "# Demo\n",
        {"DEMO_P0_001"},
    )
    assert [violation.code for violation in missing_report] == ["ETCASE600"]


# 测试 Feature：报告备注中的 artifact 字段必须来自 Case 实际写入的结构化附件。
#
# 测试方法：构造一个包含有效字段和漂移字段的最小报告契约，并提供 Case 的实际字段集合。
#
# 通过条件：有效字段被接受，只有不存在的漂移字段返回 ETCASE614。
def test_case_document_gate_rejects_report_field_drift(tmp_path: Path) -> None:

    document = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema_version: 1
cases:
  DEMO_P0_001:
    summary: 示例观测。
    fields:
      - {label: 实际值, source: artifact, path: result.actual, role: actual, format: hex32}
      - {label: 漂移值, source: artifact, path: result.missing, role: actual, format: hex32}
```
<!-- ET_CASE_REPORT_END -->
"""
    violations = CASE_DOCS._validate_report_implementation_bindings(
        tmp_path / "demo.md",
        document,
        {
            "DEMO_P0_001": {
                "artifact": {"result", "result.actual"},
                "measurement": set(),
                "observation": set(),
            }
        },
        {},
    )

    assert [violation.code for violation in violations] == ["ETCASE614"]
    assert "result.missing" in violations[0].message


# 测试 Feature：报告字段必须绑定到真实Measurement/Observation记录点。
#
# 测试方法：声明一个Case从未记录的measurement字段并运行通用实现绑定检查。
#
# 通过条件：返回ETCASE615，不能让报告在HIL结束后才发现字段不存在。
def test_case_document_gate_rejects_missing_measurement_binding(tmp_path: Path) -> None:

    document = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  DEMO_P0_001:
    summary: 示例观测。
    fields:
      - {label: 实际值, source: measurement, path: missing_value, format: decimal}
```
<!-- ET_CASE_REPORT_END -->
"""
    violations = CASE_DOCS._validate_report_implementation_bindings(
        tmp_path / "demo.md",
        document,
        {
            "DEMO_P0_001": {
                "artifact": set(),
                "measurement": {"actual_value"},
                "observation": set(),
            }
        },
        {},
    )

    assert [violation.code for violation in violations] == ["ETCASE615"]
    assert "missing_value" in violations[0].message


# 测试 Feature：参数化Case的公共报告字段必须由每个参数分支产生。
#
# 测试方法：构造双参数Case，只在mode_a分支记录branch_value，再解析真实AST记录点。
#
# 通过条件：公共字段branch_value返回ETCASE616，分支外common_value保持合法。
def test_case_document_gate_rejects_parameter_branch_report_gap(tmp_path: Path) -> None:

    package = tmp_path / "test_cases" / "demo"
    package.mkdir(parents=True)
    (package / "test_demo_p0.py").write_text(
        "import pytest\n\n"
        "@pytest.mark.parametrize('mode', ['mode_a', 'mode_b'])\n"
        "def test_demo_p0_001(mode, record_property):\n"
        "    record_property('common_value', mode)\n"
        "    if mode == 'mode_a':\n"
        "        record_property('branch_value', 1)\n",
        encoding="utf-8",
    )
    document = """
<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  DEMO_P0_001:
    summary: 示例观测。
    fields:
      - {label: 公共值, source: measurement, path: common_value, format: text}
      - {label: 分支值, source: measurement, path: branch_value, format: decimal}
```
<!-- ET_CASE_REPORT_END -->
"""
    available, parameter_incomplete = CASE_DOCS._case_report_paths(package)
    violations = CASE_DOCS._validate_report_implementation_bindings(
        tmp_path / "demo.md",
        document,
        available,
        parameter_incomplete,
    )

    assert [violation.code for violation in violations] == ["ETCASE616"]
    assert "branch_value" in violations[0].message


def test_windows_launcher_reads_errorlevel_at_execution_time() -> None:
    launcher = (REPOSITORY_ROOT / "run_test.bat").read_text(encoding="utf-8")

    assert 'if not errorlevel 1 set "PYTHON_CMD=py -3"' in launcher
    assert 'if not errorlevel 1 set "PYTHON_CMD=python"' in launcher
    assert "if %errorlevel%==0" not in launcher


# 测试 Feature：Bootstrap只准备Python环境，并把YAML交给统一Pipeline Runner。
#
# 测试方法：构造Python和配置路径，检查启动命令不携带芯片、串口或烧录参数。
#
# 通过条件：命令只包含run_pipeline.py与--config。
def test_bootstrap_only_delegates_to_pipeline_runner(tmp_path: Path) -> None:

    python = tmp_path / "python.exe"
    config = tmp_path / "run_config.yaml"

    assert BOOTSTRAP._pipeline_command(python, config) == [
        str(python),
        str(BOOTSTRAP.PIPELINE_RUNNER),
        "--config",
        str(config),
    ]


# 测试 Feature：GUI入口复用Bootstrap环境与唯一的run_config.yaml。
#
# 测试方法：检查Bootstrap的GUI命令和GUI生成的检查命令。
#
# 通过条件：命令只调用配置GUI或正式Pipeline，不包含芯片、串口和测试选择参数。
def test_gui_entry_only_delegates_to_config_gui_and_pipeline(tmp_path: Path) -> None:

    python = tmp_path / "python.exe"
    config = tmp_path / "run_config.yaml"

    assert BOOTSTRAP._gui_command(python, config) == [
        str(python),
        str(BOOTSTRAP.CONFIG_GUI),
        "--config",
        str(config),
    ]
    assert RUN_CONFIG_GUI._pipeline_command(config, check_only=True) == [
        sys.executable,
        str(RUN_CONFIG_GUI.PIPELINE_RUNNER),
        "--config",
        str(config),
        "--check-only",
    ]


# 测试 Feature：GUI字段Schema覆盖运行配置，并明确排除测试选择源。
#
# 测试方法：读取GUI Schema，收集所有dotted path，并与模板逐项取值。
#
# 通过条件：所有GUI字段存在于模板，且不存在IP、P等级或Case选择字段。
def test_gui_schema_only_edits_runtime_environment_fields() -> None:

    schema = RUN_CONFIG_GUI._load_gui_schema()
    template = RUN_PIPELINE._read_yaml(
        REPOSITORY_ROOT / "run_config.example.yaml", label="template"
    )
    paths = {
        str(field["path"])
        for tab in schema["tabs"]
        for group in tab["groups"]
        for field in group["fields"]
    }

    for path in paths:
        RUN_CONFIG_GUI._get_dotted(template, path)
    forbidden = ("test.ip", "test.level", "test.case", "include_case", "exclude_case")
    assert not any(token in path for token in forbidden for path in paths)


# 测试 Feature：GUI快捷动作只声明现有Pipeline阶段或固定门禁，不注入命令或测试选择。
#
# 测试方法：解析Schema中的八个动作，检查动作标识、门禁类型、阶段选择和环境检查保留语义。
#
# 通过条件：动作集合固定完整，所有选择均为Pipeline dotted path，且不携带脚本字段。
def test_gui_quick_actions_are_controlled_operations() -> None:

    schema = RUN_CONFIG_GUI._load_gui_schema()
    actions = RUN_CONFIG_GUI._quick_actions(schema)

    assert [action["id"] for action in actions] == [
        "environment_check",
        "software_quality_gate",
        "full_gate",
        "build_firmware",
        "deploy_firmware",
        "deploy_bitfile",
        "deploy_bootrom",
        "run_tests",
    ]
    assert actions[0]["check_only"] is True
    assert actions[0]["preserve_selection"] is True
    assert actions[1]["gate"] == "software_quality"
    assert actions[2]["gate"] == "full"
    assert actions[-1]["select"] == ("execute.run_tests", "execute.generate_report")
    assert "script" not in schema["quick_actions"][0]


# 测试 Feature：单项快捷动作形成精确Pipeline预设并保留硬件人工确认。
#
# 测试方法：分别应用编译、硬件部署、PC测试和环境检查动作，读取全部阶段布尔值。
#
# 通过条件：普通动作只启用声明阶段且不隐式运行门禁，人工硬件确认不被篡改。
def test_gui_quick_action_presets_are_exact_and_safe() -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    schema = RUN_CONFIG_GUI._load_gui_schema()
    actions = {action["id"]: action for action in RUN_CONFIG_GUI._quick_actions(schema)}
    profile = RUN_CONFIG_GUI._selected_profile(
        payload, config_path=REPOSITORY_ROOT / "run_config.example.yaml"
    )
    original = json.loads(json.dumps(payload))

    compiled = RUN_CONFIG_GUI._apply_quick_action_preset(
        payload, actions["build_firmware"], profile
    )
    deployed = RUN_CONFIG_GUI._apply_quick_action_preset(
        payload, actions["deploy_firmware"], profile
    )
    tested = RUN_CONFIG_GUI._apply_quick_action_preset(payload, actions["run_tests"], profile)

    assert payload == original
    assert RUN_CONFIG_GUI._selected_pipeline_steps(compiled) == ("build.firmware",)
    assert compiled["pipeline"]["code_check"] is False
    assert RUN_CONFIG_GUI._selected_pipeline_steps(deployed) == (
        "deploy.bitfile",
        "deploy.bootrom",
        "deploy.firmware",
    )
    assert deployed["pipeline"]["code_check"] is False
    assert deployed["pipeline"]["confirm_hardware_actions"] is False
    assert set(RUN_CONFIG_GUI._selected_pipeline_steps(tested)) == {
        "execute.run_tests",
        "execute.generate_report",
    }
    assert tested["pipeline"]["code_check"] is False

    payload["pipeline"]["build"]["firmware"] = True
    checked = RUN_CONFIG_GUI._apply_quick_action_preset(
        payload, actions["environment_check"], profile
    )
    assert RUN_CONFIG_GUI._selected_pipeline_steps(checked) == ("build.firmware",)


# 测试 Feature：软件质量门禁和全量门禁使用唯一验证入口且不触发Pipeline硬件阶段。
#
# 测试方法：分别生成两个门禁按钮的命令，检查入口脚本和参数。
#
# 通过条件：软件质量门禁携带--skip-tests，全量门禁不携带裁剪参数。
def test_gui_gate_actions_use_canonical_validator() -> None:

    assert RUN_CONFIG_GUI._gate_command("software_quality") == [
        sys.executable,
        str(REPOSITORY_ROOT / "tools/validate_pc.py"),
        "--skip-tests",
    ]
    assert RUN_CONFIG_GUI._gate_command("full") == [
        sys.executable,
        str(REPOSITORY_ROOT / "tools/validate_pc.py"),
    ]


# 测试 Feature：快捷动作可用性由当前Pipeline Profile自动决定。
#
# 测试方法：分别加载FPGA和Silicon Profile，查询bitfile、BootROM和固件动作。
#
# 通过条件：FPGA支持自身部署动作，Silicon自动禁用未实现动作且仍支持固件部署。
def test_gui_quick_action_availability_follows_selected_profile() -> None:

    schema = RUN_CONFIG_GUI._load_gui_schema()
    actions = {action["id"]: action for action in RUN_CONFIG_GUI._quick_actions(schema)}
    fpga = RUN_CONFIG_GUI._read_yaml(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml", label="FPGA Profile"
    )
    silicon = RUN_CONFIG_GUI._read_yaml(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_silicon.yaml",
        label="Silicon Profile",
    )

    assert RUN_CONFIG_GUI._quick_action_supported(actions["deploy_bitfile"], fpga) is True
    assert RUN_CONFIG_GUI._quick_action_supported(actions["deploy_bootrom"], fpga) is True
    assert RUN_CONFIG_GUI._quick_action_supported(actions["deploy_bitfile"], silicon) is False
    assert RUN_CONFIG_GUI._quick_action_supported(actions["deploy_bootrom"], silicon) is False
    assert RUN_CONFIG_GUI._quick_action_supported(actions["deploy_firmware"], silicon) is True
    assert RUN_CONFIG_GUI._quick_action_supported(actions["run_tests"], silicon) is True


# 测试 Feature：FPGA固件烧录快捷动作自动包含Profile声明的BootROM前置阶段。
#
# 测试方法：分别对FPGA和Silicon Profile应用同一个烧录固件动作并读取阶段选择。
#
# 通过条件：FPGA按Profile加入bitfile和BootROM，Silicon保持单独固件烧录，不在GUI硬编码目标差异。
def test_gui_quick_action_expands_profile_step_dependencies() -> None:

    schema = RUN_CONFIG_GUI._load_gui_schema()
    action = next(
        item for item in RUN_CONFIG_GUI._quick_actions(schema) if item["id"] == "deploy_firmware"
    )
    config_path = REPOSITORY_ROOT / "run_config.example.yaml"
    fpga_payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    fpga_profile = RUN_CONFIG_GUI._selected_profile(fpga_payload, config_path=config_path)
    silicon_payload = json.loads(json.dumps(fpga_payload))
    silicon_payload["target"]["kind"] = "silicon"
    silicon_payload["target"]["pipeline_profile"] = "tools/profiles/pipeline/et6801_silicon.yaml"
    silicon_profile = RUN_CONFIG_GUI._selected_profile(silicon_payload, config_path=config_path)

    fpga_selected = RUN_CONFIG_GUI._apply_quick_action_preset(fpga_payload, action, fpga_profile)
    silicon_selected = RUN_CONFIG_GUI._apply_quick_action_preset(
        silicon_payload, action, silicon_profile
    )

    assert RUN_CONFIG_GUI._selected_pipeline_steps(fpga_selected) == (
        "deploy.bitfile",
        "deploy.bootrom",
        "deploy.firmware",
    )
    assert RUN_CONFIG_GUI._selected_pipeline_steps(silicon_selected) == ("deploy.firmware",)


# 测试 Feature：命令行Runner同样强制Profile阶段前置关系。
#
# 测试方法：在FPGA模板中只启用固件烧录，不选择其BootROM前置阶段后加载配置。
#
# 通过条件：Runner在创建Artifact或访问硬件前明确拒绝缺失的deploy.bootrom。
def test_pipeline_rejects_missing_profile_step_dependency(tmp_path: Path) -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    payload["pipeline"]["code_check"] = True
    payload["pipeline"]["confirm_hardware_actions"] = True
    payload["pipeline"]["deploy"]["firmware"] = True
    payload["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    config = tmp_path / "missing_dependency.yaml"
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="deploy.bootrom"):
        RUN_PIPELINE._load_context(config)


# 测试 Feature：GUI必填标记由Schema、Profile参数和Bench占位符共同生成。
#
# 测试方法：先启用bitfile部署，再切换为Formal Case，分别读取动态必填字段。
#
# 通过条件：只标记当前动作依赖；可选探针号不误标，测试通道和固件身份可被反查。
def test_gui_required_fields_follow_profile_and_bench_dependencies() -> None:

    config_path = REPOSITORY_ROOT / "run_config.example.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    schema = RUN_CONFIG_GUI._load_gui_schema()
    payload["pipeline"]["deploy"]["bitfile"] = True

    bitfile_required = RUN_CONFIG_GUI._required_config_fields(
        payload, schema, config_path=config_path
    )

    assert "environment.tools.vivado.root" in bitfile_required
    assert "dut.images.bitfile.path" in bitfile_required
    assert "dut.debug.probe_serial" not in bitfile_required

    payload["pipeline"]["deploy"]["bitfile"] = False
    payload["pipeline"]["execute"]["run_tests"] = True
    payload["pipeline"]["execute"]["generate_report"] = True
    test_required = RUN_CONFIG_GUI._required_config_fields(payload, schema, config_path=config_path)

    assert "dut.control.port" in test_required
    assert "dut.control.baudrate" in test_required
    assert "dut.expected.firmware_build_id" in test_required
    assert RUN_CONFIG_GUI._missing_required_fields(payload, test_required) == ["dut.control.port"]


# 测试 Feature：GUI保存采用原子替换并保留字段值类型。
#
# 测试方法：修改临时配置的整数和布尔字段，再写入并重新读取。
#
# 通过条件：YAML可解析且值类型未退化为字符串。
def test_gui_writes_configuration_atomically(tmp_path: Path) -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    RUN_CONFIG_GUI._set_dotted(payload, "test.repeat", 20)
    RUN_CONFIG_GUI._set_dotted(payload, "pipeline.code_check", True)
    output = tmp_path / "run_config.yaml"

    RUN_CONFIG_GUI._write_yaml_atomic(output, payload)
    restored = RUN_CONFIG_GUI._read_yaml(output, label="saved config")

    assert RUN_CONFIG_GUI._get_dotted(restored, "test.repeat") == 20
    assert RUN_CONFIG_GUI._get_dotted(restored, "pipeline.code_check") is True


# 测试 Feature：GUI Schema中的每个字段都能写入唯一配置并被Pipeline重新解析。
#
# 测试方法：按控件类型为全部字段生成替代值，逐项写入临时YAML并逐项回读；最后恢复
# 目标/Profile一致性和安全的关闭态，让正式Pipeline解析整份配置。
#
# 通过条件：每个字段均完成类型和值往返，最终配置能建立PipelineContext。
def test_every_gui_field_round_trips_and_pipeline_accepts_config(tmp_path: Path) -> None:

    schema = RUN_CONFIG_GUI._load_gui_schema()
    template = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    fields = [
        field for tab in schema["tabs"] for group in tab["groups"] for field in group["fields"]
    ]

    for index, field in enumerate(fields, start=1):
        path = str(field["path"])
        field_type = str(field["type"])
        if field_type == "bool":
            replacement: object = not bool(RUN_CONFIG_GUI._get_dotted(template, path))
        elif field_type == "integer":
            replacement = 100000 + index
        elif field_type == "choice":
            replacement = str(field["choices"][-1])
        elif field_type in {"pipeline_profile", "bench_profile"}:
            replacement = str(RUN_CONFIG_GUI._get_dotted(template, path))
        elif field_type == "directory_or_auto":
            replacement = "auto"
        else:
            replacement = f"gui_field_{index}"
        RUN_CONFIG_GUI._set_dotted(template, path, replacement)

        output = tmp_path / f"field_{index}.yaml"
        RUN_CONFIG_GUI._write_yaml_atomic(output, template)
        restored = RUN_CONFIG_GUI._read_yaml(output, label=path)
        assert RUN_CONFIG_GUI._get_dotted(restored, path) == replacement

    template = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    template["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    template["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    config = tmp_path / "valid_gui_config.yaml"
    RUN_CONFIG_GUI._write_yaml_atomic(config, template)
    RUN_PIPELINE._load_context(config)


# 测试 Feature：目标、DUT、配测设备和仪器配置会进入正式运行上下文。
#
# 测试方法：启用两类配测设备和两类仪器，构造PipelineContext并检查稳定环境变量。
#
# 通过条件：逻辑名称、Profile、连接方式、端口、Driver和资源均被真实消费。
def test_pipeline_consumes_runtime_device_configuration(tmp_path: Path) -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    payload["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    payload["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    payload["dut"]["control"].update({"port": "COM88", "baudrate": 230400})
    payload["companions"]["waveform_fpga"]["enabled"] = True
    payload["companions"]["waveform_fpga"]["connection"]["probe_serial"] = "FPGA-PROBE"
    payload["companions"]["peer_board"]["enabled"] = True
    payload["companions"]["peer_board"]["connection"]["port"] = "COM89"
    payload["instruments"]["scope"].update({"enabled": True, "driver": "scope_driver"})
    payload["instruments"]["scope"]["connection"]["resource"] = "TCPIP::scope"
    payload["instruments"]["power_supply"].update({"enabled": True, "driver": "power_driver"})
    payload["instruments"]["power_supply"]["connection"]["resource"] = "USB::power"
    config = tmp_path / "devices.yaml"
    RUN_CONFIG_GUI._write_yaml_atomic(config, payload)

    context = RUN_PIPELINE._load_context(config)

    assert context.environment["ET_TARGET_KIND"] == "fpga"
    assert context.environment["ET_TARGET_LOGICAL_NAME"] == "dut"
    assert context.environment["ET_DUT_SERIAL_PORT"] == "COM88"
    assert context.environment["ET_DUT_SERIAL_BAUD"] == "230400"
    assert context.environment["ET_COMPANION_WAVEFORM_FPGA_TYPE"] == "fpga"
    assert context.environment["ET_COMPANION_WAVEFORM_FPGA_PROFILE"]
    assert context.environment["ET_COMPANION_WAVEFORM_FPGA_PROBE_SERIAL"] == "FPGA-PROBE"
    assert context.environment["ET_COMPANION_PEER_BOARD_PORT"] == "COM89"
    assert context.environment["ET_INSTRUMENT_SCOPE_DRIVER"] == "scope_driver"
    assert context.environment["ET_INSTRUMENT_SCOPE_RESOURCE"] == "TCPIP::scope"
    assert context.environment["ET_INSTRUMENT_POWER_SUPPLY_DRIVER"] == "power_driver"
    assert context.environment["ET_INSTRUMENT_POWER_SUPPLY_RESOURCE"] == "USB::power"


# 测试 Feature：编译和部署配置会生成Profile声明的受控命令。
#
# 测试方法：为六个动作填写独立标记路径，逐项启用并检查命令使用对应工具、工程、镜像
# 和探针配置；参数值只来自run_config或受控Profile。PowerShell发现属于环境检查，不属于本测试。
#
# 通过条件：每个动作都生成预期脚本及参数，不存在GUI字段保存后未被消费的假配置。
def test_pipeline_steps_consume_configured_tools_and_images(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    monkeypatch.setattr(RUN_PIPELINE.shutil, "which", lambda _name: "powershell.exe")
    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    payload["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    payload["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    files = {
        "keil": tmp_path / "UV4.exe",
        "jlink": tmp_path / "JLink.exe",
        "bootrom_project": tmp_path / "bootrom.uvprojx",
        "bitfile": tmp_path / "dut.bit",
    }
    for path in files.values():
        path.write_bytes(b"unit")
    directories = {"pack": tmp_path / "packs", "vivado": tmp_path / "vivado"}
    for path in directories.values():
        path.mkdir()
    payload["environment"]["tools"]["keil"] = {
        "executable": str(files["keil"]),
        "pack_root": str(directories["pack"]),
    }
    payload["environment"]["tools"]["vivado"]["root"] = str(directories["vivado"])
    payload["environment"]["tools"]["jlink"]["executable"] = str(files["jlink"])
    payload["dut"]["sources"]["bootrom_project"] = str(files["bootrom_project"])
    payload["dut"]["images"]["bitfile"]["path"] = str(files["bitfile"])
    payload["dut"]["debug"]["probe_serial"] = "JLINK-SERIAL"
    config = tmp_path / "steps.yaml"
    RUN_CONFIG_GUI._write_yaml_atomic(config, payload)
    context = RUN_PIPELINE._load_context(config)

    commands = {
        step: RUN_PIPELINE._action_command(context, step) for step in RUN_PIPELINE.PIPELINE_STEPS
    }

    assert str(files["keil"]) in commands["build.bootrom"]
    assert str(directories["pack"]) in commands["build.bootrom"]
    assert str(files["bootrom_project"]) in commands["build.bootrom"]
    assert str(files["keil"]) in commands["build.firmware"]
    assert str(directories["vivado"]) in commands["deploy.bitfile"]
    assert str(files["bitfile"]) in commands["deploy.bitfile"]
    assert str(files["bootrom_project"]) in commands["deploy.bootrom"]
    assert str(files["jlink"]) in commands["deploy.firmware"]
    assert "JLINK-SERIAL" in commands["deploy.firmware"]
    assert "JLINK-SERIAL" in commands["execute.start_target"]


# 测试 Feature：GUI硬件二次确认判定覆盖部署、启动和HIL测试。
#
# 测试方法：从模板逐项启用真实硬件动作，并验证Renode不触发人工硬件提示。
#
# 通过条件：FPGA/Silicon真实动作返回True，Renode返回False。
def test_gui_detects_real_hardware_actions() -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    assert RUN_CONFIG_GUI._hardware_actions_selected(payload) is False

    payload["pipeline"]["deploy"]["firmware"] = True
    assert RUN_CONFIG_GUI._hardware_actions_selected(payload) is True

    payload["target"]["kind"] = "renode"
    assert RUN_CONFIG_GUI._hardware_actions_selected(payload) is False


# 测试 Feature：发布模板覆盖完整运行环境，同时把芯片动作隔离在Pipeline Profile。
#
# 测试方法：加载模板，核对稳定分区，并执行配置与Profile的联合解析。
#
# 通过条件：模板可直接解析，且用户配置不包含script字段。
def test_pipeline_template_is_complete_and_chip_actions_stay_in_profile() -> None:

    template = REPOSITORY_ROOT / "run_config.example.yaml"
    payload = RUN_PIPELINE._read_yaml(template, label="template")

    assert set(payload) == {
        "schema",
        "config",
        "target",
        "pipeline",
        "environment",
        "dut",
        "companions",
        "instruments",
        "test",
        "output",
    }
    assert "script:" not in template.read_text(encoding="utf-8")
    context = RUN_PIPELINE._load_context(template)
    assert context.profile["name"] == "et6801_fpga"
    assert context.bench_path.is_file()


# 测试 Feature：真实硬件操作必须由本地配置明确确认。
#
# 测试方法：在模板中启用Formal硬件测试但保持确认门禁关闭。
#
# 通过条件：配置解析阶段拒绝运行，不会到达串口或硬件工具。
def test_pipeline_rejects_unconfirmed_hardware_actions(tmp_path: Path) -> None:

    template = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    template["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    template["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    template["pipeline"]["execute"]["run_tests"] = True
    config = tmp_path / "run_config.yaml"
    config.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="confirm_hardware_actions"):
        RUN_PIPELINE._load_context(config)


# 测试 Feature：真实硬件单步动作与软件门禁解耦。
#
# 测试方法：启用Formal硬件测试和人工确认，并显式关闭code_check后解析配置。
#
# 通过条件：配置可以进入Runner；硬件确认仍然生效，门禁由独立按钮人工执行。
def test_pipeline_accepts_hardware_actions_without_implicit_software_gate(
    tmp_path: Path,
) -> None:

    template = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    template["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    template["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    template["pipeline"]["code_check"] = False
    template["pipeline"]["confirm_hardware_actions"] = True
    template["pipeline"]["execute"]["run_tests"] = True
    config = tmp_path / "run_config.yaml"
    config.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")

    context = RUN_PIPELINE._load_context(config)

    assert context.config["pipeline"]["code_check"] is False
    assert context.config["pipeline"]["confirm_hardware_actions"] is True


# 测试 Feature：配置字段采用关闭式契约，避免拼写错误被静默忽略。
#
# 测试方法：向pipeline中加入一个不存在的字段后重新解析。
#
# 通过条件：解析器报告unknown keys，不会按默认值继续运行。
def test_pipeline_rejects_unknown_configuration_keys(tmp_path: Path) -> None:

    payload = yaml.safe_load(
        (REPOSITORY_ROOT / "run_config.example.yaml").read_text(encoding="utf-8")
    )
    payload["target"]["pipeline_profile"] = str(
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml"
    )
    payload["target"]["bench_profile"] = str(
        REPOSITORY_ROOT / "pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml"
    )
    payload["pipeline"]["compile_firmare"] = True
    config = tmp_path / "run_config.yaml"
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="unknown keys.*compile_firmare"):
        RUN_PIPELINE._load_context(config)


# 测试 Feature：运行配置不建立第二套IP、等级和Case选择源。
#
# 测试方法：检查发布模板test分区，并让Pipeline构造CRC运行命令。
#
# 通过条件：test只保留执行控制，命令不携带level/include/exclude参数。
def test_pipeline_uses_formal_registries_as_the_only_test_selection() -> None:

    template = REPOSITORY_ROOT / "run_config.example.yaml"
    context = RUN_PIPELINE._load_context(template)
    command = RUN_PIPELINE._test_command(
        context,
        "crc",
        run_dir=REPOSITORY_ROOT / "artifacts/runs/unit",
        iteration=1,
    )

    assert set(context.config["test"]) == {"repeat", "stop_on_failure"}
    assert "--level" not in command
    assert "--include-case" not in command
    assert "--exclude-case" not in command


# 测试 Feature：正式入口和发布配置不携带开发电脑的绝对路径。
#
# 测试方法：扫描模板、Bootstrap、Pipeline Runner和Pipeline Profile。
#
# 通过条件：公开入口不存在Windows盘符或个人用户目录。
def test_operator_entry_files_do_not_embed_local_absolute_paths() -> None:

    paths = (
        REPOSITORY_ROOT / "run_config.example.yaml",
        REPOSITORY_ROOT / "run_test.bat",
        REPOSITORY_ROOT / "run_config_gui.bat",
        REPOSITORY_ROOT / "tools/runner/bootstrap.py",
        REPOSITORY_ROOT / "tools/runner/run_config_gui.py",
        REPOSITORY_ROOT / "tools/runner/run_config_gui_schema.yaml",
        REPOSITORY_ROOT / "tools/runner/run_pipeline.py",
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_fpga.yaml",
        REPOSITORY_ROOT / "tools/profiles/pipeline/et6801_silicon.yaml",
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert "C:\\" not in combined
    assert "D:\\" not in combined
    assert "\\Users\\admin" not in combined


def test_pipeline_validates_configured_serial_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from serial.tools import list_ports

    monkeypatch.setattr(list_ports, "comports", lambda: [SimpleNamespace(device="COM8")])

    RUN_PIPELINE._validate_serial_port("com8")
    with pytest.raises(RuntimeError, match="COM9.*COM8"):
        RUN_PIPELINE._validate_serial_port("COM9")


def test_bootstrap_recovers_pip_only_when_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    python = tmp_path / "python.exe"
    availability = iter((False, True))
    calls: list[list[str]] = []

    monkeypatch.setattr(BOOTSTRAP, "_pip_available", lambda _python: next(availability))
    monkeypatch.setattr(
        BOOTSTRAP.subprocess,
        "run",
        lambda command, **_kwargs: calls.append(list(command)),
    )

    BOOTSTRAP._ensure_pip(python)

    assert calls == [[str(python), "-m", "ensurepip", "--upgrade"]]


# 测试 Feature：Bootstrap环境完全归属于当前仓库，不依赖旧工作树或个人路径。
#
# 测试方法：读取Bootstrap解析出的仓库根、虚拟环境、依赖输入和安装目标。
#
# 通过条件：全部路径位于当前仓库；虚拟环境固定为根目录.venv；依赖安装使用当前项目。
def test_bootstrap_environment_is_repository_local() -> None:

    assert BOOTSTRAP.REPOSITORY_ROOT == REPOSITORY_ROOT
    assert BOOTSTRAP.VENV_ROOT == REPOSITORY_ROOT / ".venv"
    assert BOOTSTRAP._venv_python().is_relative_to(BOOTSTRAP.VENV_ROOT)
    assert BOOTSTRAP._DEPENDENCY_FILES == (
        REPOSITORY_ROOT / "pyproject.toml",
        REPOSITORY_ROOT / "uv.lock",
    )

    source = (REPOSITORY_ROOT / "tools/runner/bootstrap.py").read_text(encoding="utf-8")

    assert '"-e", ".[test]"' in source
    assert "Et_Automated_Testing_Platform_Code\\.venv" not in source


def test_run_ip_tests_builds_existing_pytest_boundary(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    command = RUN_IP_TESTS._pytest_command(
        ip="crc",
        bench="bench.yaml",
        target="dut",
        run_dir=run_dir,
        pytest_args=("-k", "crc_p0"),
    )

    assert command[:3] == [sys.executable, "-m", "pytest"]
    assert "--et-hardware" in command
    assert command[command.index("--et-bench") + 1] == "bench.yaml"
    assert command[command.index("--et-target") + 1] == "dut"
    assert command[command.index("--et-artifact-dir") + 1] == str(run_dir)
    assert command[-2:] == ["-k", "crc_p0"]


def test_run_ip_tests_records_source_and_spec_identity(tmp_path: Path) -> None:
    command = RUN_IP_TESTS._pytest_command(
        ip="crc",
        bench="bench.yaml",
        target="dut",
        run_dir=tmp_path / "run",
        pytest_args=(),
        source_revision="abc123",
        source_dirty=True,
        spec_sha256="deadbeef",
    )

    assert command[command.index("--et-source-revision") + 1] == "abc123"
    assert "--et-source-dirty" in command
    assert command[command.index("--et-spec-sha256") + 1] == "deadbeef"


def test_ip_change_rules_use_complete_base_diff_and_local_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_git(*args: str) -> str:
        if args[:2] == ("rev-parse", "--verify"):
            return "base-sha\n"
        if args[:2] == ("diff", "--name-only"):
            return "pc/et_test_platform/test_cases/crc/test_crc_p0.py\ntest_case_doc/crc/crc.md\n"
        if args[:2] == ("status", "--porcelain"):
            return " M tools/runner/run_ip_tests.py\n"
        return ""

    monkeypatch.setattr(IP_CHANGE_RULES, "_git", fake_git)

    assert IP_CHANGE_RULES.changed_paths(base_ref="base-sha") == {
        "pc/et_test_platform/test_cases/crc/test_crc_p0.py",
        "test_case_doc/crc/crc.md",
        "tools/runner/run_ip_tests.py",
    }


@pytest.mark.parametrize(
    "arguments",
    [
        ("--et-target", "peer"),
        ("--et-artifact-dir", "elsewhere"),
        ("-p", "no:et_test_platform.pytest_plugin"),
        ("pc/et_test_platform/test_cases/dma",),
    ],
)
def test_run_ip_tests_rejects_arguments_that_can_override_platform_control(
    arguments: tuple[str, ...],
) -> None:
    with pytest.raises(ValueError, match="unsupported pytest argument"):
        RUN_IP_TESTS._validate_pytest_args(arguments)


def test_run_ip_tests_defaults_to_project_artifacts() -> None:
    assert REPOSITORY_ROOT / "artifacts" / "records" == RUN_IP_TESTS.DEFAULT_OUTPUT_ROOT


# 测试 Feature：仓库内测试产物不得污染源码脏状态。
#
# 测试方法：在干净临时Git仓库提交基线，仅新增artifacts和tmp后重新采集源码身份。
#
# 通过条件：两次revision一致且source_dirty始终为False。
def test_source_identity_excludes_repository_owned_artifacts(tmp_path: Path) -> None:

    repository = tmp_path / "repository"
    repository.mkdir()
    RUN_PIPELINE.subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    RUN_PIPELINE.subprocess.run(
        ["git", "config", "user.email", "unit@example.invalid"], cwd=repository, check=True
    )
    RUN_PIPELINE.subprocess.run(["git", "config", "user.name", "unit"], cwd=repository, check=True)
    (repository / "source.txt").write_text("baseline\n", encoding="utf-8")
    RUN_PIPELINE.subprocess.run(["git", "add", "source.txt"], cwd=repository, check=True)
    RUN_PIPELINE.subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repository, check=True)

    before = ARTIFACT_LAYOUT.capture_source_identity(repository)
    (repository / "artifacts/runs/current").mkdir(parents=True)
    (repository / "artifacts/runs/current/manifest.json").write_text("{}\n", encoding="utf-8")
    (repository / "artifacts/reports").mkdir(parents=True)
    (repository / "artifacts/reports/report.xlsx").write_text("report\n", encoding="utf-8")
    (repository / "artifacts/records/CHIP/IP").mkdir(parents=True)
    (repository / "artifacts/records/CHIP/IP/results.json").write_text("{}", encoding="utf-8")
    (repository / "tmp").mkdir()
    (repository / "tmp/run.lock").write_text("0", encoding="utf-8")
    after = ARTIFACT_LAYOUT.capture_source_identity(repository)

    assert before == after
    assert after[1] is False


# 测试 Feature：Pipeline向Formal IP Runner传递一次性源码身份。
#
# 测试方法：构造测试命令并检查隐藏参数，不让子Runner在产物创建后重新判断。
#
# 通过条件：revision和clean/dirty状态均出现在命令中。
def test_pipeline_passes_source_identity_to_formal_runner(tmp_path: Path) -> None:

    context = RUN_PIPELINE._load_context(REPOSITORY_ROOT / "run_config.example.yaml")
    command = RUN_PIPELINE._test_command(
        context,
        "crc",
        run_dir=tmp_path,
        iteration=1,
        source_revision="abc123",
        source_dirty=False,
    )

    assert command[command.index("--source-revision") + 1] == "abc123"
    assert command[command.index("--source-state") + 1] == "clean"


# 测试 Feature：提交到Git的Pipeline清单不保存操作员配置绝对路径。
#
# 测试方法：对仓库内配置和仓库外配置分别生成清单引用。
#
# 通过条件：仓库内使用相对路径，仓库外只保留文件名标识。
def test_pipeline_manifest_uses_portable_configuration_reference(tmp_path: Path) -> None:

    assert RUN_PIPELINE._portable_path_reference(REPOSITORY_ROOT / "run_config.example.yaml") == (
        "run_config.example.yaml"
    )
    assert RUN_PIPELINE._portable_path_reference(tmp_path / "operator.yaml") == (
        "external:operator.yaml"
    )


# 测试 Feature：配置快照禁止携带未纳入Schema的凭据字段。
#
# 测试方法：分别校验正常配置和嵌套token扩展。
#
# 通过条件：正常配置通过，凭据字段在创建产物前被拒绝。
def test_pipeline_rejects_sensitive_configuration_extensions() -> None:

    RUN_PIPELINE._reject_sensitive_configuration({"environment": {"tools": {}}})
    with pytest.raises(RuntimeError, match="sensitive configuration"):
        RUN_PIPELINE._reject_sensitive_configuration(
            {"instruments": {"scope": {"token": "must-not-be-snapshotted"}}}
        )


# 测试 Feature：project路径基准保持指向外层项目目录。
#
# 测试方法：构造使用base=project的Profile参数并解析路径。
#
# 通过条件：相对路径以代码仓库外层项目目录为基准，不与repository混同。
def test_pipeline_project_path_base_keeps_outer_project_semantics() -> None:

    project_file = RUN_PIPELINE.PROJECT_ROOT / "project-base-unit.marker"
    project_file.write_text("unit\n", encoding="utf-8")
    try:
        context = RUN_PIPELINE._load_context(REPOSITORY_ROOT / "run_config.example.yaml")
        argument = {"value": project_file.name, "kind": "file", "base": "project"}
        assert RUN_PIPELINE._argument_value(context, argument) == str(project_file.resolve())
    finally:
        project_file.unlink(missing_ok=True)


# 测试 Feature：Pipeline子进程输出同时保留在控制台和统一运行日志。
#
# 测试方法：运行一个无硬件Python子进程并读取日志文件。
#
# 通过条件：退出码为0，命令和输出均写入pipeline.log。
def test_pipeline_child_output_is_persisted(tmp_path: Path) -> None:

    log_path = tmp_path / "stages/pipeline/pipeline.log"
    exit_code = RUN_PIPELINE._run(
        [sys.executable, "-c", "print('pipeline-log-proof')"],
        environment={},
        log_path=log_path,
    )

    content = log_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "pipeline-log-proof" in content
    assert sys.executable in content


# 测试 Feature：GUI启动的Python子进程以UTF-8传递中文日志。
#
# 测试方法：显式设置PYTHONIOENCODING并让Python子进程输出中文文本。
#
# 通过条件：Pipeline日志保留完整中文，不出现本地代码页误解码。
def test_pipeline_decodes_python_output_from_declared_encoding(tmp_path: Path) -> None:

    log_path = tmp_path / "stages/pipeline/pipeline.log"
    expected = "生成测试报告：硬件观测正常"
    exit_code = RUN_PIPELINE._run(
        [sys.executable, "-c", f"print({expected!r})"],
        environment={"PYTHONIOENCODING": "utf-8"},
        log_path=log_path,
    )

    content = log_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert expected in content


# 测试 Feature：Windows PowerShell子进程不继承PowerShell 7或Agent注入模块目录。
#
# 测试方法：模拟Windows路径分隔语义，构造包含错误PSModulePath的环境根并生成受控模块搜索路径。
#
# 通过条件：结果只包含Windows PowerShell的用户、系统和内置三条标准目录。
def test_pipeline_isolates_windows_powershell_module_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    monkeypatch.setattr(RUN_PIPELINE.os, "pathsep", ";")
    environment = {
        "USERPROFILE": r"C:\Users\agent",
        "PROGRAMFILES": r"C:\Program Files",
        "WINDIR": r"C:\Windows",
        "PSModulePath": r"C:\Program Files\PowerShell\Modules;C:\agent\Modules",
    }

    module_path = RUN_PIPELINE._windows_powershell_module_path(environment)

    assert module_path.split(";") == [
        r"C:\Users\agent\Documents\WindowsPowerShell\Modules",
        r"C:\Program Files\WindowsPowerShell\Modules",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules",
    ]


# 测试 Feature：多阶段CLI只创建一个共享运行目录。
#
# 测试方法：检查入口脚本在调用任何子阶段前设置ET_ARTIFACT_RUN_DIR，并在结束时收口清单。
#
# 通过条件：入口只调用一次运行目录创建函数，且成功和失败都进入finally收口。
def test_cli_flow_owns_one_shared_artifact_run() -> None:

    flow = (REPOSITORY_ROOT / "tools/fpga/et6801/run_cli_flow.ps1").read_text(encoding="utf-8")

    assert flow.count("Get-EtArtifactRunRoot") == 1
    assert "ET_ARTIFACT_RUN_DIR = Get-EtArtifactRunRoot" in flow
    assert "Complete-EtArtifactRun" in flow
    assert "finally" in flow


# 测试 Feature：BootROM调试不得改写操作员源工程。
#
# 测试方法：检查脚本只向临时副本写Debug_ROM.ini，并在finally删除副本。
#
# 通过条件：源INI只读，临时INI被写入，且临时工作区始终清理。
def test_bootrom_debug_uses_temporary_project_copy() -> None:

    script = (REPOSITORY_ROOT / "tools/fpga/et6801/load_bootrom_keil_debug.ps1").read_text(
        encoding="utf-8"
    )

    assert "Get-Content -LiteralPath $initFile -Raw" in script
    assert "Set-Content -LiteralPath $initFile" not in script
    assert "Set-Content -LiteralPath $temporaryInit" in script
    assert "Copy-Item -LiteralPath (Split-Path $projectDir -Parent)" in script
    assert "Remove-Item -LiteralPath $temporaryWorkspace" in script


# 测试 Feature：运行配置只能把产物写入仓库内 artifacts。
#
# 测试方法：分别解析 auto、仓库内自定义目录和仓库外目录。
#
# 通过条件：前两者映射到 artifacts 下，仓库外路径被拒绝。
def test_artifact_output_root_is_repository_local(tmp_path: Path) -> None:

    assert (
        ARTIFACT_LAYOUT.resolve_records_root("auto", config_directory=REPOSITORY_ROOT)
        == (REPOSITORY_ROOT / "artifacts/records").resolve()
    )
    for value in ("artifacts/runs", "artifacts/records/custom"):
        with pytest.raises(ValueError, match="canonical artifacts/records"):
            ARTIFACT_LAYOUT.resolve_records_root(value, config_directory=REPOSITORY_ROOT)

    with pytest.raises(ValueError, match="canonical artifacts/records"):
        ARTIFACT_LAYOUT.resolve_records_root(str(tmp_path), config_directory=REPOSITORY_ROOT)


# 正式入口只用固定current工作区；历史诊断路径函数的兼容性不放宽正式配置。
def test_formal_artifacts_reject_custom_subdirectory() -> None:
    with pytest.raises(ValueError, match="canonical artifacts/records"):
        ARTIFACT_LAYOUT.create_current_directory(
            REPOSITORY_ROOT, REPOSITORY_ROOT / "artifacts/runs/custom", chip="ET6801"
        )


# 测试 Feature：artifacts 顶层分类稳定，目录README不形成第二套规则。
#
# 测试方法：检查受版本控制的目录入口，并确认README把唯一规则Owner指向R500。
#
# 通过条件：根目录只存在README、runs和reports，README明确R500是唯一权威规则。
def test_artifacts_root_uses_one_run_taxonomy() -> None:

    artifact_root = REPOSITORY_ROOT / "artifacts"
    entries = {path.name for path in artifact_root.iterdir()}
    assert entries <= {"README.md", "runs", "reports", "records"}
    rules = (artifact_root / "README.md").read_text(encoding="utf-8")
    assert "R500_operator_pipeline.md" in rules
    assert "唯一权威规则" in rules
    assert "不建立第二套规则" in rules
    assert "reports/" in rules


# 测试 Feature：零动作Pipeline仍生成一致的运行清单和配置快照。
#
# 测试方法：使用安全模板执行Pipeline，并把运行根重定向到临时目录。
#
# 通过条件：返回0，manifest同时记录PASS和exit_code=0，配置快照存在。
def test_pipeline_writes_consistent_manifest_for_safe_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    context = replace(
        RUN_PIPELINE._load_context(REPOSITORY_ROOT / "run_config.example.yaml"),
        output_root=tmp_path / "artifacts/records",
    )
    monkeypatch.setattr(RUN_PIPELINE, "REPOSITORY_ROOT", tmp_path)

    assert RUN_PIPELINE._execute(context, check_only=False) == 0

    run_dir = tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["exit_code"] == 0
    assert manifest["run_id"] != "current"
    assert (run_dir / "config/run_config.snapshot.yaml").is_file()
    assert (run_dir / "publication.json").is_file()


@pytest.mark.parametrize("no_report", [False, True])
@pytest.mark.parametrize("status", ["PASS", "FAIL"])
def test_run_ip_tests_generates_report_even_when_pytest_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    no_report: bool,
    status: str,
) -> None:
    import importlib

    from .test_record_source import make_session

    source = importlib.import_module("record_source")
    original = make_session(source, tmp_path, chip_id="et6801")
    session_path = original / "session.json"
    session = json.loads(session_path.read_text())
    expected_exit = 1 if status == "FAIL" else 0
    session.update({"exitstatus": expected_exit, "status_counts": {status: 1}})
    session_path.write_text(json.dumps(session), encoding="utf-8")
    result_path = next((original / "cases").glob("*/*/result.json"))
    result = json.loads(result_path.read_text())
    result["status"] = status
    result_path.write_text(json.dumps(result), encoding="utf-8")
    case_root = tmp_path / "cases"
    document_root = tmp_path / "test_case_doc"
    output_root = tmp_path / "artifacts/records"
    (case_root / "crc").mkdir(parents=True)
    bench = tmp_path / "bench.yaml"
    bench.write_text("targets: {dut: {chip: et6801}}\n", encoding="utf-8")

    monkeypatch.setattr(RUN_IP_TESTS, "FORMAL_CASE_ROOT", case_root)
    monkeypatch.setattr(RUN_IP_TESTS, "DOCUMENT_ROOT", document_root)
    monkeypatch.setattr(RUN_IP_TESTS, "ARTIFACT_RECORDS_ROOT", output_root)
    monkeypatch.setattr(RUN_IP_TESTS, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(RUN_IP_TESTS, "capture_source_identity", lambda root: ("a" * 40, False))
    calls: list[list[str]] = []

    def fake_run(command: list[str], *, log_path: Path | None = None) -> int:
        calls.append(command)
        if Path(command[1]) == RUN_IP_TESTS.VALIDATE_PC:
            return 0
        if "pytest" in command:
            artifact_dir = Path(command[command.index("--et-artifact-dir") + 1])
            assert log_path == artifact_dir / "pytest.log"
            shutil.copytree(original, artifact_dir, dirs_exist_ok=True)
            return expected_exit
        raise AssertionError("unexpected subprocess")

    monkeypatch.setattr(RUN_IP_TESTS, "_run", fake_run)

    exit_code = RUN_IP_TESTS.main(
        [
            "--ip",
            "crc",
            "--bench",
            str(bench),
            "--target",
            "dut",
            "--output-root",
            str(output_root),
            "--lane",
            "fpga",
            *(["--no-report"] if no_report else []),
        ]
    )

    assert exit_code == expected_exit
    assert len(calls) == 2
    assert Path(calls[0][1]) == RUN_IP_TESTS.VALIDATE_PC
    pytest_command = calls[1]
    assert Path(pytest_command[pytest_command.index("--et-artifact-dir") + 1]) == (
        output_root / "ET6801/CRC/current"
    )
    root = output_root / "ET6801/CRC/current"
    assert not (root / "test_report.xlsx").exists()
    report = tmp_path / "artifacts/reports/ET6801/ET6801_CRC测试报告.xlsx"
    assert report.is_file() is not no_report
    assert f"| {status} |" in (root / "facts.md").read_text(encoding="utf-8")
    assert not (root.parent / "cases").exists()
    assert json.loads((root / "publication.json").read_text())["pending_review"] is True
    assert not (tmp_path / "artifacts/runs/current").exists()
    assert "Actual Session chip differs" not in capsys.readouterr().out


# 测试方法：Session 根写入测量 JSON 后 bind 再 prepare_review。
# 通过条件：源文件删除、Case 下有副本、publication/Excel 都能生成。
def test_binding_session_root_measurement_allows_prepare_review_to_seal(
    tmp_path: Path,
) -> None:
    from et_test_platform.results.recorder import write_json_result
    from et_test_platform.scheduling.run_context import ExecutionIdentity, RunContext

    from .test_record_source import make_session

    source = importlib.import_module("record_source")
    original = make_session(source, tmp_path, chip_id="et6801")
    current = tmp_path / "artifacts/records/ET6801/CRC/current"
    current.parent.mkdir(parents=True)
    original.rename(current)
    leftover = current / "measurement.json"
    write_json_result(leftover, {"measurement_schema": "et.measurement.v1", "value": 1})
    execution_dir = next(
        path
        for path in (current / "cases").glob("*/*")
        if path.is_dir() and path.name != "artifacts"
    )
    identity = ExecutionIdentity(
        layout="nested",
        case_id="crc_p1_001",
        ip_id="crc",
        parameter_id=None,
        slot=execution_dir.name,
        case_run_id="CRC_P1_001--noparam",
        execution_dir=execution_dir,
    )
    relative = RunContext(current).bind_case_artifact(identity, leftover)
    result_path = execution_dir / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["artifacts"]["measurement"] = relative
    result_path.write_text(json.dumps(result), encoding="utf-8")

    prepared = RUN_IP_TESTS.prepare_review(tmp_path, current, chip="ET6801", ip="crc", lane="fpga")

    assert not leftover.exists()
    assert (current / relative).is_file()
    assert (current / "facts.md").is_file()
    assert (current / "publication.json").is_file()
    assert json.loads((current / "publication.json").read_text(encoding="utf-8"))["pending_review"]
    assert Path(str(prepared["report"])).is_file()


# 测试方法：pytest 已写出 Session，但根上残留未绑定 JSON。
# 通过条件：prepare_review/seal 失败必须非零退出并明确日志，不得当测试绿而静默跳过报告。
def test_run_ip_tests_fails_closed_when_unbound_root_json_blocks_seal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from .test_record_source import make_session

    source = importlib.import_module("record_source")
    original = make_session(source, tmp_path, chip_id="et6801")
    case_root = tmp_path / "cases"
    document_root = tmp_path / "test_case_doc"
    output_root = tmp_path / "artifacts/records"
    (case_root / "crc").mkdir(parents=True)
    bench = tmp_path / "bench.yaml"
    bench.write_text("targets: {dut: {chip: et6801}}\n", encoding="utf-8")

    monkeypatch.setattr(RUN_IP_TESTS, "FORMAL_CASE_ROOT", case_root)
    monkeypatch.setattr(RUN_IP_TESTS, "DOCUMENT_ROOT", document_root)
    monkeypatch.setattr(RUN_IP_TESTS, "ARTIFACT_RECORDS_ROOT", output_root)
    monkeypatch.setattr(RUN_IP_TESTS, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(RUN_IP_TESTS, "capture_source_identity", lambda root: ("a" * 40, False))

    def fake_run(command: list[str], *, log_path: Path | None = None) -> int:
        if Path(command[1]) == RUN_IP_TESTS.VALIDATE_PC:
            return 0
        if "pytest" in command:
            artifact_dir = Path(command[command.index("--et-artifact-dir") + 1])
            shutil.copytree(original, artifact_dir, dirs_exist_ok=True)
            (artifact_dir / "leftover.json").write_text('{"value": 1}', encoding="utf-8")
            return 0
        raise AssertionError("unexpected subprocess")

    monkeypatch.setattr(RUN_IP_TESTS, "_run", fake_run)

    exit_code = RUN_IP_TESTS.main(
        [
            "--ip",
            "crc",
            "--bench",
            str(bench),
            "--target",
            "dut",
            "--output-root",
            str(output_root),
            "--lane",
            "fpga",
        ]
    )

    root = output_root / "ET6801/CRC/current"
    captured = capsys.readouterr().out
    assert exit_code == 2
    assert "publication/report was not sealed" in captured
    assert (root / "session.json").is_file()
    assert not (root / "publication.json").exists()
    assert not (tmp_path / "artifacts/reports/ET6801/ET6801_CRC测试报告.xlsx").exists()


# 测试 Feature：Session 与 Bench 目标芯片真不一致时必须跳过发布。
#
# 测试方法：合成 session.chip_id=et9999，Bench 目标仍为 et6801，走独立 IP runner。
#
# 通过条件：打印芯片不一致、不写 facts/publication/Excel，原始 session 保留。
def test_run_ip_tests_skips_review_when_session_chip_differs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import importlib

    from .test_record_source import make_session

    source = importlib.import_module("record_source")
    original = make_session(source, tmp_path, chip_id="et9999")
    case_root = tmp_path / "cases"
    document_root = tmp_path / "test_case_doc"
    output_root = tmp_path / "artifacts/records"
    (case_root / "crc").mkdir(parents=True)
    bench = tmp_path / "bench.yaml"
    bench.write_text("targets: {dut: {chip: et6801}}\n", encoding="utf-8")

    monkeypatch.setattr(RUN_IP_TESTS, "FORMAL_CASE_ROOT", case_root)
    monkeypatch.setattr(RUN_IP_TESTS, "DOCUMENT_ROOT", document_root)
    monkeypatch.setattr(RUN_IP_TESTS, "ARTIFACT_RECORDS_ROOT", output_root)
    monkeypatch.setattr(RUN_IP_TESTS, "REPOSITORY_ROOT", tmp_path)
    monkeypatch.setattr(RUN_IP_TESTS, "capture_source_identity", lambda root: ("a" * 40, False))

    def fake_run(command: list[str], *, log_path: Path | None = None) -> int:
        if Path(command[1]) == RUN_IP_TESTS.VALIDATE_PC:
            return 0
        if "pytest" in command:
            artifact_dir = Path(command[command.index("--et-artifact-dir") + 1])
            shutil.copytree(original, artifact_dir, dirs_exist_ok=True)
            return 0
        raise AssertionError("unexpected subprocess")

    monkeypatch.setattr(RUN_IP_TESTS, "_run", fake_run)

    exit_code = RUN_IP_TESTS.main(
        [
            "--ip",
            "crc",
            "--bench",
            str(bench),
            "--target",
            "dut",
            "--output-root",
            str(output_root),
            "--lane",
            "fpga",
        ]
    )

    assert exit_code == 2
    root = output_root / "ET6801/CRC/current"
    assert (root / "session.json").is_file()
    assert not (root / "facts.md").exists()
    assert not (root / "publication.json").exists()
    assert not (tmp_path / "artifacts/reports/ET6801/ET6801_CRC测试报告.xlsx").exists()
    assert "Actual Session chip differs" in capsys.readouterr().out


# 测试 Feature：默认与多轮执行都使用固定工作目录，轮间由发布回执保护复用。
#
# 测试方法：分别构造repeat=1和repeat=2的Pipeline测试命令并读取产物参数。
#
# 通过条件：始终写入tests/<ip>，并显式传递Lane与原始Manifest。
@pytest.mark.parametrize("kind,lane", [("renode", "sil"), ("fpga", "fpga"), ("silicon", "hil")])
def test_pipeline_uses_same_fixed_ip_directory_for_every_round(
    tmp_path: Path, kind: str, lane: str
) -> None:

    context = RUN_PIPELINE._load_context(REPOSITORY_ROOT / "run_config.example.yaml")
    context = replace(
        context, config={**context.config, "target": {**context.config["target"], "kind": kind}}
    )
    single = RUN_PIPELINE._test_command(
        context,
        "uart",
        run_dir=REPOSITORY_ROOT / "artifacts/records/ET6801/_PIPELINE/current",
        iteration=1,
        repeat_count=1,
    )
    repeated = RUN_PIPELINE._test_command(
        context,
        "uart",
        run_dir=REPOSITORY_ROOT / "artifacts/records/ET6801/_PIPELINE/current",
        iteration=2,
        repeat_count=2,
    )

    expected = REPOSITORY_ROOT / "artifacts/records/ET6801/UART/current"
    assert Path(single[single.index("--output-root") + 1]) == expected
    assert Path(repeated[repeated.index("--output-root") + 1]) == expected
    assert single[single.index("--lane") + 1] == lane
    assert Path(single[single.index("--manifest") + 1]) == (
        REPOSITORY_ROOT / "artifacts/records/ET6801/_PIPELINE/current/manifest.json"
    )


# 测试 Feature：Excel报告按芯片/IP固定命名。
#
# 测试方法：以芯片和IP重复调用共享报告路径函数。
#
# 通过条件：同芯片/IP总是同一个路径，已有报告允许安全替换。
def test_report_output_is_fixed_per_chip_ip(tmp_path: Path) -> None:

    output = ARTIFACT_LAYOUT.create_report_output(
        tmp_path,
        chip="et6801",
        ip="uart",
    )

    assert output == tmp_path / "ET6801/ET6801_UART测试报告.xlsx"
    assert not output.parent.exists()

    output.parent.mkdir()
    output.touch()
    assert ARTIFACT_LAYOUT.create_report_output(tmp_path, chip="ET6801", ip="UART") == output
    for invalid in ("../ET6801", "a/b", "CON", "bad chip"):
        with pytest.raises(ValueError):
            ARTIFACT_LAYOUT.create_report_output(tmp_path, chip=invalid, ip="uart")


# 测试 Feature：正式运行目录不得重复叠加日期桶或第二个执行时间戳。
#
# 测试方法：创建一个共享运行目录并检查它相对runs根目录的层级。
#
# 通过条件：诊断目录固定为records/_DIAGNOSTICS/<TOOL>/current，不含时间戳。
def test_diagnostic_run_directory_uses_fixed_current(tmp_path: Path) -> None:

    run_dir = ARTIFACT_LAYOUT.create_run_directory(
        tmp_path / "artifacts/records", run_name="Local ET6801 FPGA"
    )

    assert run_dir == tmp_path / "artifacts/records/_DIAGNOSTICS/LOCAL_ET6801_FPGA/current"
    assert not (tmp_path / "artifacts/runs").exists()


# 测试方法：从本轮Pipeline复制配置，拒绝其他轮/路径；通过条件：IP有自己的配置和逻辑身份。
def test_ip_pipeline_snapshot_is_bound_to_its_fixed_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RUN_IP_TESTS, "REPOSITORY_ROOT", tmp_path)
    parent = tmp_path / "artifacts/records/ET6801/_PIPELINE/current"
    (parent / "config").mkdir(parents=True)
    configuration = b"schema: unit\n"
    (parent / "config/run_config.snapshot.yaml").write_bytes(configuration)
    source = "a" * 40
    metadata = {
        "run_id": "pipeline-1",
        "source_revision": source,
        "status": "RUNNING",
        "configuration_snapshot": "config/run_config.snapshot.yaml",
        "configuration_sha256": RUN_IP_TESTS._file_sha256(
            parent / "config/run_config.snapshot.yaml"
        ),
    }
    (parent / "manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
    args = SimpleNamespace(within_pipeline=True, manifest=parent / "manifest.json")
    own: dict[str, object] = {}
    assert RUN_IP_TESTS._pipeline_snapshot(args, "ET6801", source, own) == configuration
    assert own["pipeline_run_id"] == "pipeline-1"
    assert own["configuration_snapshot"] == "config/run_config.snapshot.yaml"
    with pytest.raises(ValueError, match="source/state"):
        RUN_IP_TESTS._pipeline_snapshot(args, "ET6801", "b" * 40, {})
    with pytest.raises(ValueError, match="original manifest"):
        RUN_IP_TESTS._pipeline_snapshot(args, "ET6003", source, {})


# 测试方法：只调用PowerShell路径函数，不执行阶段；通过条件：诊断包装器传递路径可用，旧runs被拒绝。
def test_powershell_diagnostic_wrapper_keeps_fixed_context(tmp_path: Path) -> None:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell is required for path-only validation")
    script = REPOSITORY_ROOT / "tools/runner/artifact_paths.ps1"
    command = f"""
$ErrorActionPreference = 'Stop'
. '{str(script).replace("'", "''")}'
$root = '{str(tmp_path).replace("'", "''")}'
function Invoke-EtDiagnosticWorkspace {{
    param($CodeRoot, $RunRoot, $Operation)
    if ($CodeRoot -ne $root) {{ throw 'incorrect derived repository' }}
    New-Item -ItemType Directory -Force -Path $RunRoot | Out-Null
    if ($Operation -eq 'complete') {{ $script:completed = $true }}
}}
$env:ET_ARTIFACT_RUN_DIR = $null
$diagnostic = Get-EtArtifactRunRoot -CodeRoot $root -RunName 'unit_diagnostic'
$env:ET_ARTIFACT_RUN_DIR = $diagnostic
if ((Get-EtArtifactRunRoot -CodeRoot $root -RunName 'child') -ne $diagnostic) {{ throw 'lost context' }}
Complete-EtArtifactRun -RunRoot $diagnostic -Succeeded $true
if (-not $script:completed) {{ throw 'completion not recorded' }}
$env:ET_ARTIFACT_RUN_DIR = Join-Path $root 'artifacts/runs/current'
$rejected = $false
try {{ Get-EtArtifactRunRoot -CodeRoot $root -RunName 'child' }} catch {{ $rejected = $true }}
if (-not $rejected) {{ throw 'legacy path accepted' }}
"""
    completed = subprocess.run(
        [powershell, "-NoProfile", "-Command", command], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not (tmp_path / "artifacts/runs").exists()


# 测试 Feature：PowerShell独立工具与Python Pipeline使用同一扁平运行目录规则。
#
# 测试方法：检查共享PowerShell路径函数使用records固定诊断现场。
#
# 通过条件：脚本不再拼接yyyy/MM/dd目录，只保留一个run_id层级。
def test_powershell_artifact_path_uses_fixed_current() -> None:

    script = (REPOSITORY_ROOT / "tools/runner/artifact_paths.ps1").read_text(encoding="utf-8")

    assert "_DIAGNOSTICS\\$safeName\\current" in script
    assert "artifacts\\runs" not in script
    assert "ToString('yyyy')" not in script
    assert "ToString('MM')" not in script
    assert "ToString('dd')" not in script


# 测试 Feature：ET6801 FPGA PFLASH底层脚本不能绕过同一次Pipeline前置阶段。
#
# 测试方法：检查共享Artifact保护函数及PFLASH入口，并真实执行前置阶段PASS/FAIL验证。
#
# 通过条件：前置manifest为FAIL时拒绝，改为PASS后放行；脚本依赖bitfile和BootROM两阶段。
def test_et6801_pflash_requires_same_pipeline_prerequisites(tmp_path: Path) -> None:

    helper = REPOSITORY_ROOT / "tools/runner/artifact_paths.ps1"
    artifact_paths = helper.read_text(encoding="utf-8")
    flash_script = (REPOSITORY_ROOT / "tools/firmware/flash_and_run_et6801_firmware.ps1").read_text(
        encoding="utf-8"
    )

    assert "function Assert-EtPipelineStagePassed" in artifact_paths
    assert "Pipeline run context is missing" in artifact_paths
    assert "^result=PASS\\s*$" in artifact_paths
    assert "if (-not $SkipFlash)" in flash_script
    assert "-StageName 'deploy_bitfile'" in flash_script
    assert "-StageName 'deploy_bootrom'" in flash_script

    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell is required for the Pipeline stage guard test")
    code_root = tmp_path / "code"
    run_root = code_root / "artifacts/records/ET6801/_PIPELINE/current"
    bit_stage = run_root / "stages" / "deploy_bitfile"
    boot_stage = run_root / "stages" / "deploy_bootrom"
    bit_stage.mkdir(parents=True)
    boot_stage.mkdir(parents=True)
    (bit_stage / "manifest.txt").write_text("result=PASS\n", encoding="utf-8")
    (boot_stage / "manifest.txt").write_text("result=FAIL\n", encoding="utf-8")
    command = (
        "$ErrorActionPreference='Stop'; "
        f". '{str(helper).replace(chr(39), chr(39) * 2)}'; "
        f"Assert-EtPipelineStagePassed -CodeRoot '{str(code_root).replace(chr(39), chr(39) * 2)}' "
        "-StageName 'deploy_bootrom'"
    )
    environment = dict(os.environ)
    environment["ET_ARTIFACT_RUN_DIR"] = str(run_root)

    failed = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert failed.returncode != 0
    assert "did not pass" in failed.stderr

    (boot_stage / "manifest.txt").write_text("result=PASS\n", encoding="utf-8")
    passed = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert passed.returncode == 0


def test_run_ip_tests_no_report_still_rejects_empty_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case_root = tmp_path / "cases"
    document_root = tmp_path / "docs"
    (case_root / "crc").mkdir(parents=True)
    (document_root / "crc").mkdir(parents=True)
    (document_root / "crc" / "crc.md").write_text("# CRC\n", encoding="utf-8")
    monkeypatch.setattr(RUN_IP_TESTS, "FORMAL_CASE_ROOT", case_root)
    monkeypatch.setattr(RUN_IP_TESTS, "DOCUMENT_ROOT", document_root)
    runs_root = tmp_path / "artifacts/records"
    monkeypatch.setattr(RUN_IP_TESTS, "ARTIFACT_RECORDS_ROOT", runs_root)
    monkeypatch.setattr(RUN_IP_TESTS, "REPOSITORY_ROOT", tmp_path)

    def fake_run(command: list[str], *, log_path: Path | None = None) -> int:
        if Path(command[1]) == RUN_IP_TESTS.VALIDATE_PC:
            return 0
        artifact_dir = Path(command[command.index("--et-artifact-dir") + 1])
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "session.json").write_text(
            json.dumps(
                {
                    "run_id": "unit",
                    "finished_at": "2026-08-20T00:00:00Z",
                    "exitstatus": 0,
                    "selection": {"selected_executions": []},
                }
            ),
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(RUN_IP_TESTS, "_run", fake_run)
    bench = tmp_path / "bench.yaml"
    bench.write_text("targets: {dut: {chip: et6801}}\n", encoding="utf-8")

    assert (
        RUN_IP_TESTS.main(
            [
                "--ip",
                "crc",
                "--bench",
                str(bench),
                "--output-root",
                str(runs_root),
                "--no-report",
                "--lane",
                "fpga",
            ]
        )
        == 2
    )
    assert (runs_root / "ET6801/CRC/current/session.json").is_file()
    assert not (runs_root / "ET6801/CRC/current/publication.json").exists()


# 测试 Feature：pytest返回成功也不能掩盖参数execution结果缺失。
#
# 测试方法：先缺失一个参数结果，再补入EVIDENCE_MISSING结果并分别校验。
#
# 通过条件：缺失结果抛错；Evidence不完整时返回False，Runner最终不能标记PASS。
def test_run_ip_tests_rejects_incomplete_parameter_execution_results(tmp_path: Path) -> None:

    run_dir = tmp_path / "run"
    case_dir = run_dir / "cases" / "AES_P0_002" / "ecb128"
    case_dir.mkdir(parents=True)
    (run_dir / "session.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "finished_at": "2026-08-20T00:00:00Z",
                "exitstatus": 0,
                "selection": {
                    "selected_executions": [
                        {"case_id": "aes_p0_002", "parameter_id": "ecb128"},
                        {"case_id": "aes_p0_002", "parameter_id": "cbc128"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "case_run_id": "AES_P0_002--ecb128",
                "case_id": "aes_p0_002",
                "parameter_id": "ecb128",
                "status": "PASS",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="do not match selected executions"):
        RUN_IP_TESTS._validate_canonical_run(run_dir, pytest_exit=0)

    missing_evidence_dir = run_dir / "cases" / "AES_P0_002" / "cbc128"
    missing_evidence_dir.mkdir()
    (missing_evidence_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "case_run_id": "AES_P0_002--cbc128",
                "case_id": "aes_p0_002",
                "parameter_id": "cbc128",
                "status": "EVIDENCE_MISSING",
            }
        ),
        encoding="utf-8",
    )

    assert RUN_IP_TESTS._validate_canonical_run(run_dir, pytest_exit=0) is False


def test_validate_canonical_run_rejects_legacy_uuid_layout(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    case_dir = run_dir / "cases" / "06bd50ed-5154-4d57-ae75-78dded033a70"
    case_dir.mkdir(parents=True)
    (run_dir / "session.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "finished_at": "2026-08-20T00:00:00Z",
                "exitstatus": 0,
                "selection": {
                    "selected_executions": [
                        {"case_id": "crc_p0_002", "parameter_id": "crc32"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "result.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "case_run_id": case_dir.name,
                "case_id": "crc_p0_002",
                "parameter_id": "crc32",
                "status": "PASS",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nested"):
        RUN_IP_TESTS._validate_canonical_run(run_dir, pytest_exit=0)


# 测试 Feature：报告命令返回0后仍必须存在有效XLSX容器。
#
# 测试方法：分别提供缺失文件、普通文本和最小有效ZIP头文件。
#
# 通过条件：前两者失败关闭，满足大小和XLSX容器头的文件通过。
def test_run_ip_tests_validates_report_file_after_export(tmp_path: Path) -> None:

    output = tmp_path / "report.xlsx"
    with pytest.raises(ValueError, match="not generated correctly"):
        RUN_IP_TESTS._validate_report_output(output)

    output.write_text("not an xlsx", encoding="utf-8")
    with pytest.raises(ValueError, match="not a valid XLSX"):
        RUN_IP_TESTS._validate_report_output(output)

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("xl/workbook.xml", "<workbook />")
    RUN_IP_TESTS._validate_report_output(output)


def test_case_report_comments_have_a_nonempty_author(tmp_path: Path) -> None:
    output = tmp_path / "report.xlsx"
    model = {
        "chip_name": "ET6801",
        "ip_name": "CRC",
        "session_complete": True,
        "session": {"run_id": "unit"},
        "summary": {"stable_case_count": 1, "status_counts": {"PASS": 1}},
        "cases": [
            {
                "case_id": "crc_p0_001",
                "p_level": "P0",
                "report_feature": "运行时能力",
                "method": "读取能力。",
                "pass_criteria": "返回值有效。",
                "case_name": "CRC运行时能力测试",
                "status": "PASS",
                "coverage_complete": True,
                "remark": "硬件观测:\n- DUT / ET6801 / crc0 / CRC.RES\n  结果寄存器值: 0xAD37D056",
            }
        ],
        "executions": [],
        "spec_trace": [],
    }

    CASE_REPORT._write_xlsx(model, output)

    with zipfile.ZipFile(output) as archive:
        comment_files = [name for name in archive.namelist() if name.startswith("xl/comments")]
        assert comment_files
        comment_xml = archive.read(comment_files[0]).decode("utf-8")
        shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")

    assert "<author>ET Automated Testing Platform</author>" in comment_xml
    assert "测试Case ID" in shared_strings
    assert "crc_p0_001" in shared_strings
    assert "DUT / ET6801 / crc0 / CRC.RES" in shared_strings


# 使用真实接口限制Mock方法，时间每次前进一秒，避免测试等待真实两秒。
@pytest.fixture
def diagnostic(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, MagicMock, MagicMock]:
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "tools/runner"))
    tool = importlib.import_module("can_link_diagnostic")
    can = MagicMock(spec=tool.CanDriver)
    box = MagicMock(spec=ZlgCanBox)
    can.protocol_status_consume.return_value = SimpleNamespace(
        last_error=SimpleNamespace(name="ACK"), activity=SimpleNamespace(name="TRANSMITTER")
    )
    can.rx_fifo_status_get.return_value = SimpleNamespace(fill=0)
    ticks = count()
    monkeypatch.setattr(tool.time, "monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr(tool.time, "sleep", lambda seconds: None)
    return tool, can, box


# 两种向外发送场景均必须实际读取盒子，不先等待DUT发送完成。
@pytest.mark.parametrize("direction", ["forward", "listen_only"])
def test_empty_window_keeps_ack_status(diagnostic, direction: str) -> None:
    tool, can, box = diagnostic
    box.receive.side_effect = TimeoutError("no complete frame")
    result = tool._observe(can, box, direction)

    assert result["receive_count"] == 0
    assert result["last_error_name"] == "ACK"
    assert result["stimulus_error"] is None
    can.tx_request.assert_called_once_with(1)
    box.receive.assert_called_once_with(timeout_s=0.02)


# SDK拒绝发送不能伪装成正常激励，但不能妨碍读取错误现场。
def test_rejected_transmit_preserves_error_and_status(diagnostic) -> None:
    tool, can, box = diagnostic
    box.send.side_effect = OSError("transmit accepted 0, expected 1")
    box.error_get.return_value = 4
    result = tool._observe(can, box, "reverse")

    assert result["receive_count"] == 0
    assert result["stimulus_error"] == "transmit accepted 0, expected 1"
    assert result["box_error"] == 4
    can.protocol_status_consume.assert_called_once_with()


# 成功接收保留原帧；真正SDK接收错误必须抛出，不能按无帧处理。
def test_received_frame_and_sdk_failure_are_distinct(diagnostic) -> None:
    tool, can, box = diagnostic
    frame = tool.CanFrame(0x123, tool.PAYLOAD)
    box.receive.return_value = frame
    result = tool._observe(can, box, "forward")
    assert result["frames"] == [frame]
    assert result["receive_count"] == 1

    box.receive.side_effect = OSError("device disconnected")
    with pytest.raises(OSError, match="device disconnected"):
        tool._observe(can, box, "forward")
