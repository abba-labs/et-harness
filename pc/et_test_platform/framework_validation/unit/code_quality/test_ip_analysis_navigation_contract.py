# IP分析资料导航回归测试。
#
# 职责：验证新IP analysis Task Context必读资料索引及核心规则Owner。
# 边界：不读取外部资料内容，不执行IP分析或硬件测试。
# 依赖：正式Task Context编译器。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[5]
COMPILER = ROOT / "tools" / "governance" / "compile_task_context.py"


def _load_compiler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ip_analysis_task_context_compiler", COMPILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Task Context compiler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ip_analysis_context_requires_source_map_and_evidence_contract() -> None:
    compiler = _load_compiler()
    context = compiler.build_task_context(
        task_id="NEW-IP-ANALYSIS-001",
        intent="分析目标芯片新IP并形成公共契约",
        modules=["ip-package"],
        changes=["analysis"],
        ip="new_ip_not_created",
        chip="et6801",
        lanes=["docs"],
    )

    reads = {entry["path"]: entry for entry in context["must_read"]}
    owners = {entry["owner_id"] for entry in context["rule_owners"]}

    source_map = reads["project-governance/ip-analysis-sources.yaml"]
    assert source_map["required"] is True
    assert source_map["exists"] is True
    assert {
        "ip_analysis_workflow",
        "public_ip_machine_contract",
        "canonical_result_evidence",
    } <= owners
