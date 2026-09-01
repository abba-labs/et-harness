# Report Repository Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将项目外层已有的人读设计、计划、分析和验证文档确定性地归档到正式代码仓库 `report/`，并建立后续文档的固定放置规则。

**Architecture:** 使用生命周期分类作为第一层，验证报告按 `fpga/dut/framework` 再分一层。`report/README.md` 是唯一入口；`test_case_doc/`、`project-control/` 和外层原始证据保持独立，迁移过程只复制或在正式仓库内分类移动，不删除外层来源。

**Tech Stack:** Markdown、PowerShell、Git、SHA256

## Global Constraints

- 不修改固件、PC 平台、配测设备或芯片源代码。
- 不执行硬件操作。
- 不删除或覆盖用户已有文档。
- `test_case_doc/` 目录和内容保持不变。
- 原始日志、波形、截图和大体积证据不得进入正式代码仓库。
- 目标存在但 SHA256 不同时立即停止，不得静默覆盖；迁移后相对链接调整必须在清单中单独标记。

---

### Task 1: 建立正式目录和唯一索引

**Files:**
- Create: `report/README.md`
- Create: `report/design/report_repository_governance.md`
- Create: `report/plans/20260805_report_repository_migration_plan.md`

**Interfaces:**
- Consumes: 已确认的生命周期分类方案和项目文档规则。
- Produces: GitHub 可直接浏览的固定目录、规则和入口索引。

- [x] 创建 `design/plans/analysis/validation/{fpga,dut,framework}/archive`。
- [x] 在 `report/README.md` 写明目录职责、当前文档索引、例外目录和新增文档命名规则。
- [x] 检查索引不得包含机器相关的绝对路径。

### Task 2: 迁移设计、规格和计划

**Files:**
- Copy: `docs/design/*.md` -> `report/design/`
- Copy: `docs/superpowers/specs/*.md` -> `report/design/`
- Copy: `docs/superpowers/plans/*.md` -> `report/plans/`
- Copy: `docs/design/mcu_hil_sil_unified_test_platform.md` -> `report/archive/`
- Copy: `docs/design/*.dc.html` -> `report/archive/`

**Interfaces:**
- Consumes: 外层现有设计与计划文档。
- Produces: 正式代码仓库内可同步的设计与计划集合。

- [x] 对每个源文件计算 SHA256。
- [x] 当前设计复制到 `design/`，历史设计和旧导出复制到 `archive/`。
- [x] 比较复制前后 SHA256；44份内容完全一致，2份仅修正迁移后的相对链接并在清单中标记。

### Task 3: 归类已有报告与人读证据

**Files:**
- Move within repository: `report/2026*.md` -> `report/analysis/` or `report/validation/**/`
- Copy selected: `project-control/evidence/*.md` -> `report/validation/**/`
- Replace: `report/00_index.md`
- Create: `report/archive/20260805_document_migration_manifest.md`

**Interfaces:**
- Consumes: 已确认与外层 `reports/` SHA256 相同的正式报告副本，以及三份人读 evidence。
- Produces: 无平铺混杂、可按用途查找的报告集合和可追溯迁移清单。

- [x] 将芯片共性、SDK 演进、问题调查和评审文档归入 `analysis/`。
- [x] 将 XC7Z045/XC7VX980T 能力验证归入 `validation/fpga/`。
- [x] 将 ET6801 Flash、UART、DMA HIL 归入 `validation/dut/`。
- [x] 将协议、框架边界和公共可靠性验证归入 `validation/framework/`。
- [x] 生成源路径、目标路径和 SHA256 迁移表。
- [x] 将旧 `00_index.md` 改为指向 `README.md` 的兼容入口，避免旧链接立即失效。

### Task 4: 固化项目规则和入口

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/README.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/DIRECTORY_LAYOUT.md`

**Interfaces:**
- Consumes: `report/design/report_repository_governance.md`。
- Produces: 对人和后续自动化代理一致的文档放置规则。

- [x] 将正式设计、计划、分析和验证报告统一指向代码根 `report/`。
- [x] 明确 `test_case_doc/`、`project-control/` 和 `artifacts/` 三类例外。
- [x] 明确外层 `docs/`、`reports/` 不再新增正式文档。

### Task 5: 完整性验证

**Files:**
- Verify: `report/**`
- Verify: project rules and indexes

**Interfaces:**
- Consumes: 完成后的目录和迁移清单。
- Produces: 可提交 GitHub 的文档集合及无遗漏验证结果。

- [x] 按迁移清单逐项校验源文件和目标文件 SHA256，并核对2份相对链接调整记录。
- [x] 检查 `report/README.md` 中每个相对链接均存在。
- [x] 检查 `report/` 不含日志、波形、截图、构建产物和机器生成索引。
- [x] 检查 `test_case_doc/` 状态与迁移前基线一致；保留已有 `UART.md` 修改且本任务未触碰。
- [x] 运行 `git diff --check`。
- [x] 运行 `project-control/scripts/context-doctor.bat -Quick`；指纹变化后已刷新并复检通过。
- [x] 仅报告本次文档变更，不将工作区原有固件和 PC 代码修改纳入本次提交范围。
