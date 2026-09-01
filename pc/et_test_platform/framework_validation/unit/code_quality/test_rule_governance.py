# Framework Validation规则治理测试。
#
# 职责：验证诊断码、唯一Owner和权威正文之间的失败关闭关系。
# 边界：不执行业务代码、硬件操作或规则正文迁移。
# 依赖：仅动态加载治理Checker并使用临时Checker源构造冲突。

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[5]
CHECKER = ROOT / "tools" / "quality" / "validate_rule_governance.py"


# 加载与总软件门禁相同的规则治理Checker。
def _load_checker() -> ModuleType:

    spec = importlib.util.spec_from_file_location("rule_governance_checker", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rule governance checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 测试Feature：当前全部诊断码均能追溯到唯一活动Owner和真实正文锚点。
#
# 测试方法：直接运行正式Catalog与全部quality Checker的治理校验。
#
# 通过条件：校验结果为空，不存在冲突、遗漏或失效锚点。
def test_current_rule_governance_is_traceable() -> None:

    checker = _load_checker()

    assert checker.validate_governance() == []


# 测试Feature：活动规则必须使用稳定Rxxx编号并与规则文件绑定。
#
# 测试方法：保留真实Catalog的其他字段，只把一个活动Owner编号改成非法值。
#
# 通过条件：结果包含ETGOV118，治理门禁不接受缺失或自由格式编号。
def test_rule_governance_rejects_invalid_rule_number(monkeypatch) -> None:

    checker = _load_checker()
    payload = checker._load_catalog()
    payload["owners"][0]["number"] = "RULE-1"
    monkeypatch.setattr(checker, "_load_catalog", lambda: payload)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV118") for item in errors)


# 测试Feature：两个Checker复用同一诊断码时治理门禁失败关闭。
#
# 测试方法：在临时quality目录创建两个均发出ETORCH101的最小Checker并运行正式校验。
#
# 通过条件：结果包含ETGOV109跨Checker冲突，不接受文件名或执行顺序消歧。
def test_rule_governance_rejects_duplicate_checker_code(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    quality_root = tmp_path / "quality"
    quality_root.mkdir()
    (quality_root / "first.py").write_text('CODE = "ETORCH101"\n', encoding="utf-8")
    (quality_root / "second.py").write_text('CODE = "ETORCH101"\n', encoding="utf-8")
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    errors = checker.validate_governance()

    assert any(
        "ETGOV109 diagnostic ETORCH101 is emitted by multiple Checkers" in item for item in errors
    )


# 测试Feature：Catalog正文标题失效时治理门禁失败关闭。
#
# 测试方法：复制一个最小Owner记录，但把heading改为不存在的标题并替换临时Catalog。
#
# 通过条件：结果包含ETGOV106，Agent不能继续猜测最接近的章节。
def test_rule_governance_rejects_missing_canonical_heading(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: broken_owner\n"
        "    rule_id: ET-RULE-BROKEN\n"
        "    lifecycle: active\n"
        "    source: AGENTS.md\n"
        "    heading: '## 不存在的标题'\n"
        "    diagnostics: [ETGOV101-ETGOV109]\n"
        "    checkers: [tools/quality/validate_rule_governance.py]\n",
        encoding="utf-8",
    )
    empty_quality = tmp_path / "quality"
    empty_quality.mkdir()
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", empty_quality)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV106") for item in errors)


# 测试Feature：唯一机器契约模板被复制到第二份规则正文时失败关闭。
#
# 测试方法：在临时design目录创建机器契约正文和含相同Schema标记的竞争文档。
#
# 通过条件：结果包含ETGOV110，治理门禁不允许两个规范文档同时拥有同一Schema模板。
def test_rule_governance_rejects_duplicate_normative_schema(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    design_root = tmp_path / "report" / "design"
    quality_root = tmp_path / "tools" / "quality"
    design_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    canonical = design_root / "public_ip_machine_contract.md"
    duplicate = design_root / "duplicate.md"
    canonical.write_text("# Public IP Machine Contract\n\nschema: et.case.v1\n", encoding="utf-8")
    duplicate.write_text("# Duplicate\n\nschema: et.case.v1\n", encoding="utf-8")
    checker_source = quality_root / "validate_rule_governance.py"
    checker_source.write_text('CODE = "ETGOV110"\n', encoding="utf-8")
    catalog = design_root / "rule_owner_catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: public_ip_machine_contract\n"
        "    rule_id: ET-RULE-IP-MACHINE-CONTRACT\n"
        "    lifecycle: active\n"
        "    source: report/design/public_ip_machine_contract.md\n"
        "    heading: '# Public IP Machine Contract'\n"
        "    diagnostics: [ETGOV110]\n"
        "    exclusive_markers: ['schema: et.case.v1']\n"
        "    checkers: [tools/quality/validate_rule_governance.py]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV110") for item in errors)


# 测试Feature：无静态Checker的公共行为Contract可以由正式回归测试保护。
#
# 测试方法：建立无diagnostics/checkers、但声明真实测试文件的最小Owner Catalog。
#
# 通过条件：治理校验接受该Owner，不要求为行为Contract伪造诊断码或Checker。
def test_rule_governance_accepts_regression_test_owned_contract(
    tmp_path: Path, monkeypatch
) -> None:

    checker = _load_checker()
    design_root = tmp_path / "report" / "design"
    test_root = tmp_path / "tests"
    quality_root = tmp_path / "tools" / "quality"
    design_root.mkdir(parents=True)
    test_root.mkdir()
    quality_root.mkdir(parents=True)
    rules_root = design_root / "rules"
    rules_root.mkdir()
    contract = rules_root / "R130_result_contract.md"
    contract.write_text(
        "---\n"
        "schema: et.rule-document.v1\n"
        "number: R130\n"
        "domain: result\n"
        "lifecycle: active\n"
        "owners: [canonical_result]\n"
        "rule_ids: [ET-RULE-CANONICAL-RESULT]\n"
        "---\n\n"
        "# R130 Result Contract\n",
        encoding="utf-8",
    )
    regression = test_root / "test_result_contract.py"
    regression.write_text("def test_contract():\n    pass\n", encoding="utf-8")
    catalog = design_root / "rule_owner_catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: canonical_result\n"
        "    number: R130\n"
        "    rule_id: ET-RULE-CANONICAL-RESULT\n"
        "    lifecycle: active\n"
        "    source: report/design/rules/R130_result_contract.md\n"
        "    heading: '# R130 Result Contract'\n"
        "    diagnostics: []\n"
        "    checkers: []\n"
        "    tests: [tests/test_result_contract.py]\n"
        "documents:\n"
        "  - path: report/design/rules/R130_result_contract.md\n"
        "    number: R130\n"
        "    role: contract\n"
        "    lifecycle: active\n"
        "    owners: [canonical_result]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    assert checker.validate_governance() == []


# 测试Feature：report/design出现未登记文档时治理门禁失败关闭。
#
# 测试方法：在完整临时Inventory之外增加一份没有Catalog记录的设计文档。
#
# 通过条件：结果包含ETGOV113，Agent不能根据目录位置猜测文档角色。
def test_rule_governance_rejects_unregistered_design_document(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    design_root = tmp_path / "report" / "design"
    quality_root = tmp_path / "tools" / "quality"
    design_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    contract = design_root / "contract.md"
    contract.write_text("# Contract\n", encoding="utf-8")
    (design_root / "unknown.md").write_text("# Unknown\n", encoding="utf-8")
    catalog = design_root / "rule_owner_catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: owner\n"
        "    rule_id: ET-RULE-OWNER\n"
        "    lifecycle: active\n"
        "    source: report/design/contract.md\n"
        "    heading: '# Contract'\n"
        "    diagnostics: []\n"
        "    checkers: []\n"
        "    tests: [tests/test_owner.py]\n"
        "documents:\n"
        "  - path: report/design/contract.md\n"
        "    role: contract\n"
        "    lifecycle: active\n"
        "    owners: [owner]\n",
        encoding="utf-8",
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_owner.py").write_text("def test_owner():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV113 unregistered") for item in errors)


# 测试Feature：文档角色必须来自固定轻量枚举且非规则文档不能认领Owner。
#
# 测试方法：把现有Contract错误登记为自造角色并保留Owner绑定。
#
# 通过条件：结果包含ETGOV114，不接受自由文本角色扩张。
def test_rule_governance_rejects_unknown_document_role(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    design_root = tmp_path / "report" / "design"
    quality_root = tmp_path / "tools" / "quality"
    tests_root = tmp_path / "tests"
    design_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    tests_root.mkdir()
    contract = design_root / "contract.md"
    contract.write_text("# Contract\n", encoding="utf-8")
    (tests_root / "test_owner.py").write_text("def test_owner():\n    pass\n", encoding="utf-8")
    catalog = design_root / "rule_owner_catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: owner\n"
        "    rule_id: ET-RULE-OWNER\n"
        "    lifecycle: active\n"
        "    source: report/design/contract.md\n"
        "    heading: '# Contract'\n"
        "    diagnostics: []\n"
        "    checkers: []\n"
        "    tests: [tests/test_owner.py]\n"
        "documents:\n"
        "  - path: report/design/contract.md\n"
        "    role: important_note\n"
        "    lifecycle: active\n"
        "    owners: [owner]\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV114") for item in errors)


# 测试Feature：deprecated或superseded文档必须指向真实替代来源。
#
# 测试方法：把历史文档标记为superseded但省略superseded_by。
#
# 通过条件：结果包含ETGOV117，失效文档不能留下无路由的死入口。
def test_rule_governance_rejects_unrouted_superseded_document(tmp_path: Path, monkeypatch) -> None:

    checker = _load_checker()
    design_root = tmp_path / "report" / "design"
    quality_root = tmp_path / "tools" / "quality"
    design_root.mkdir(parents=True)
    quality_root.mkdir(parents=True)
    history = design_root / "old.md"
    history.write_text("# Old\n", encoding="utf-8")
    catalog = design_root / "rule_owner_catalog.yaml"
    catalog.write_text(
        "schema: et.rule-owner-catalog.v1\n"
        "status: active\n"
        "owners:\n"
        "  - id: governance\n"
        "    rule_id: ET-RULE-GOVERNANCE\n"
        "    lifecycle: active\n"
        "    source: report/design/old.md\n"
        "    heading: '# Old'\n"
        "    diagnostics: []\n"
        "    checkers: []\n"
        "    tests: [tests/test_governance.py]\n"
        "documents:\n"
        "  - path: report/design/old.md\n"
        "    role: history\n"
        "    lifecycle: superseded\n",
        encoding="utf-8",
    )
    tests_root = tmp_path / "tests"
    tests_root.mkdir()
    (tests_root / "test_governance.py").write_text(
        "def test_governance():\n    pass\n", encoding="utf-8"
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(checker, "CATALOG", catalog)
    monkeypatch.setattr(checker, "QUALITY_ROOT", quality_root)

    errors = checker.validate_governance()

    assert any(item.startswith("ETGOV117") for item in errors)
