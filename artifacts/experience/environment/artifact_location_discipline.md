# 运行产物与临时文件必须留在仓库内（C: 盘 ephemeral 目录误用）

状态：active
适用范围：一切 Agent 在 ET_ATP_Testing 内产生的临时文件、日志、备份与诊断产物；不限芯片/Lane。
最后核验：2026-09-11

## 现象/背景

2026-09-11 会话中，Agent 为绕开"沙箱下 `C:\Users\admin\AppData` 不可访问"的问题，
把探针脚本、运行日志、备份包共 25 个文件放到 `C:\atp_ephemeral_ctrl\`。用户随后指出
路径错误，要求迁回仓库。

## 根因/机制

- **仓库本来就有约定**：`.gitignore` 忽略 `tmp/`；`pyproject.toml` 写着
  `cache_dir = "../tmp/pytest_cache"`。正确位置是 `<repo>/tmp/`。
- Agent 之所以另起 C: 盘目录，是因为当时 `tmp/` 里存在**历史残留文件**，触发了
  `test_repository_layout.py` 的"仓库根只能有固定分类"断言。Agent 的错误选择是
  "换个更远的地方"，而正确做法是"清掉残留、继续用 tmp/"。
- 更深一层：临时文件的**最终去向**其实有明确规定——软件门禁/工具验证日志属于
  `records/_TOOLING/<TASK>/current/`（R500 §6.3），而不是随手一个 tmp 目录。

## 解法/操作

| 产物类型 | 正确位置 | 依据 |
|---|---|---|
| pytest 缓存、一次性探针 | `<repo>/tmp/`（已 gitignore） | `.gitignore` / `pyproject.toml` |
| 软件门禁、工具验证日志 | `artifacts/records/_TOOLING/<TASK>/current/` | R500 §6.3 |
| 独立诊断现场 | `artifacts/records/_DIAGNOSTICS/<TOOL>/current/` | R500 §6.3 |
| Formal Case 证据 | `artifacts/records/<CHIP>/<IP>/current/` | R500 §6.1 |

**禁止**把任何项目产物写到仓库外的系统盘路径。

仓库根目录**只允许**出现固定分类目录（`firmware/pc/companion/tools/test_case_doc/report/
artifacts/project-governance/agent_harness`）；`tmp/` 与工具输出目录（如 graphflow 的 `*-out/`）
出现在根目录会让 `test_repository_layout.py` 失败，应确保它们被 gitignore 且不长期滞留。

## 边界与不适用

- `tmp/` 是本地草稿区，内容不提交、不对外引用；需长期留存的结论必须迁入
  `records/_TOOLING/` 或 `report/`。
- 本机 `C:\Users\admin\AppData` 的 ACL 异常是本机环境事实，见
  [sandbox_and_file_tools](../environment/sandbox_and_file_tools.md)；绕开它的正确方式是
  设置 `TEMP/TMP` 到仓库内可写目录，不是把产物搬去 C: 盘。

## 依据与变化

- 2026-09-11 18:00 CST：由当日会话沉淀。已执行的纠正：C: 盘目录整体删除，日志与备份迁入
  `records/_TOOLING/IP_REGRESSION_20260911/current/`，`graphflow-out/` 加入 `.gitignore`，
  `tmp/` 清空。同轮修复了 `tools/runner/record_source.py` 的 Ruff 格式与两处 C901 复杂度。
