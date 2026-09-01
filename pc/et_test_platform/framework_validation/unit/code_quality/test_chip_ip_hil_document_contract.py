# Chip IP文档HIL状态闭环测试。
#
# 职责：验证Working-tree HIL结果具有最小追溯信息，且不会与旧Current-SHA状态冲突。
# 边界：只测试文档同步Checker，不读取硬件或运行Formal Case。
# 依赖：tools/quality/validate_chip_ip_docs.py。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[5]
CHECKER = ROOT / "tools" / "quality" / "validate_chip_ip_docs.py"


# 加载与软件总门禁相同的Chip IP文档Checker。
def _load_checker() -> ModuleType:

    spec = importlib.util.spec_from_file_location("chip_ip_document_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load chip IP document checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 测试Feature：执行过Working-tree HIL的文档必须记录逻辑Case、证据路径和Exact-SHA状态。
#
# 测试方法：构造缺少三项追溯字段的最小HIL状态文本并调用正式Checker。
#
# 通过条件：每个缺失字段都产生ETSYNC202，文档不能只留下PASS计数。
def test_executed_working_tree_hil_requires_traceability(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"

    violations = checker._validate_hil_sync(path, "Working-tree FPGA HIL: EXECUTED\n")

    assert [item.code for item in violations].count("ETSYNC202") == 3


# 测试Feature：Working-tree HIL已执行时禁止继续声明Current-SHA未执行而不解释Source身份。
#
# 测试方法：同时放入完整Working-tree追溯字段和旧Current-SHA NOT_EXECUTED语句。
#
# 通过条件：Checker返回ETSYNC203，强制文档改用Exact committed SHA的精确表述。
def test_executed_working_tree_hil_rejects_stale_current_sha_status(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"
    text = (
        "Working-tree FPGA HIL: EXECUTED / 1 PASS\n"
        "Logical Case result: 1 PASS / 0 SKIP / 0 FAIL\n"
        "HIL Evidence: artifacts/runs/example/session.json\n"
        "Exact committed SHA FPGA HIL: NOT_PROVEN / source_dirty=true\n"
        "Current-SHA FPGA HIL: NOT_EXECUTED / NOT_VERIFIED\n"
    )

    violations = checker._validate_hil_sync(path, text)

    assert any(item.code == "ETSYNC203" for item in violations)


# 测试Feature：完整且无矛盾的Working-tree HIL状态能够通过同步Checker。
#
# 测试方法：提供逻辑Case结果、Evidence路径和Exact committed SHA结论。
#
# 通过条件：Checker不返回任何同步违规。
def test_executed_working_tree_hil_accepts_complete_status(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"
    text = (
        "Working-tree FPGA HIL: EXECUTED / 1 PASS\n"
        "Logical Case result: 1 PASS / 0 SKIP / 0 FAIL\n"
        "HIL Evidence: artifacts/runs/example/session.json\n"
        "Exact committed SHA FPGA HIL: NOT_PROVEN / source_dirty=true\n"
    )

    assert checker._validate_hil_sync(path, text) == []


# 构造满足R110的当前芯片测试状态区域。
def _current_test_status_block() -> str:

    return """
<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-24 18:40 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-24 18:30 CST` | `0123456789abcdef` | `false` | `artifacts/runs/example/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 3 | 2 | 1 | 0 | 1 | 1 | 3 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `DEMO_P1_001` | FPGA | SKIP | `DEMO_F_001` / IRQ | 未观察到IRQ | 当前台架缺少激励 | 接入激励后重测 | `artifacts/runs/example/case.json` |
| `DEMO_P1_002` | FPGA | NOT_EXECUTED | `DEMO_F_002` / DMA | 尚未执行 | 内部DMA执行映射未闭合 | 补齐映射后执行 | `pc/et_test_platform/profiles/demo.yaml` |
<!-- ET_CHIP_TEST_STATUS_END -->
"""


# 测试Feature：正式芯片IP测试任务必须产生当前测试状态区域。
#
# 测试方法：对不含状态区域的芯片文档启用required模式。
#
# 通过条件：Checker返回ETSYNC204，不允许测试完成后只保留Artifact。
def test_current_test_status_is_required_for_test_result_task(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"

    violations = checker._validate_test_status(path, "", required=True)

    assert [item.code for item in violations] == ["ETSYNC204"]


# 测试Feature：当前状态区域必须同时闭合时间、运行身份、逻辑Case统计和非PASS详情。
#
# 测试方法：构造包含一次FPGA运行及一个SKIP Case的完整状态区域。
#
# 通过条件：Checker不返回任何同步违规。
def test_current_test_status_accepts_complete_tables(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"

    violations = checker._validate_test_status(
        path,
        _current_test_status_block(),
        required=True,
    )

    assert violations == []


# 测试Feature：状态汇总和非PASS Case明细必须保持数量一致。
#
# 测试方法：把完整状态中的SKIP统计改为0，但保留SKIP明细。
#
# 通过条件：Checker返回ETSYNC208，拒绝与实际Case列表矛盾的文档。
def test_current_test_status_rejects_inconsistent_counts(tmp_path: Path) -> None:

    checker = _load_checker()
    path = tmp_path / "ET6801_demo.md"
    text = _current_test_status_block().replace(
        "| FPGA | 3 | 2 | 1 | 0 | 1 | 1 | 3 |",
        "| FPGA | 3 | 2 | 2 | 0 | 0 | 1 | 3 |",
    )

    violations = checker._validate_test_status(path, text, required=True)

    assert any(item.code == "ETSYNC208" for item in violations)
