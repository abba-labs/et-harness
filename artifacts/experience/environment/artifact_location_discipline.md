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

### 硬禁令（用户指令 2026-09-11）

**不准向仓库外部输出任何文件。** 包括探针脚本、日志、备份、临时目录——一律不得写到
`C:\` 或其他仓库外路径。`TEMP/TMP` 若需重定向，只允许指到 `<repo>/tmp/` 或
`records/_TOOLING/<TASK>/current/`。

| 产物类型 | 正确位置 | 依据 |
|---|---|---|
| pytest 缓存、运行期临时目录 | `<repo>/tmp/`（已 gitignore） | `.gitignore` / `pyproject.toml` |
| 软件门禁、工具验证日志 | `artifacts/records/_TOOLING/<TASK>/current/` | R500 §6.3 |
| 该轮的临时脚本 | `<repo>/tmp/` | R500 §6.1 |
| 独立诊断现场 | `artifacts/records/_DIAGNOSTICS/<TOOL>/current/` | R500 §6.3 |
| Formal Case 证据 | `artifacts/records/<CHIP>/<IP>/current/` | R500 §6.1 |

仓库根目录**只允许**出现固定分类目录（`firmware/pc/companion/tools/test_case_doc/report/
artifacts/project-governance/agent_harness`）；`tmp/` 与工具输出目录（如 graphflow 的 `*-out/`）
应按当前目录规则管理；`tmp/`是R500明确允许的本地临时区，不是非法根目录。

### 临时脚本的两个去向（必须二选一，不得滞留）

写脚本前先判断它属于哪一类：

1. **长期固化 → `tools/`**：会被反复使用、有稳定职责的（如批量知识更新、现场审计、流水线监控），
   按仓库工具规范放入 `tools/<area>/`，成为正式工具。**优先复用已有工具，不要重复造。**
2. **本轮临时 → `<repo>/tmp/`**：只服务本轮任务的一次性脚本。
   **该任务 review 时必须清理**，否则该目录会无限膨胀。

判断标准：如果下一个任务还会用到 → `tools/`；如果只有本轮用 → 临时目录，并在 review 时删掉。

### `_TOOLING` 目录的容量纪律

`records/_TOOLING/<TASK>/current/`承载本轮结论性日志与小结（临时脚本留tmp），**它同样是会被覆盖的
"当前工作区"而非长期仓库**。每轮 review 时同步清理：一次性脚本删除、过时日志删除，
只保留本轮的结论性文件（如 `REPORT.md`）。单任务累积到数十个文件即说明清理没做。

## 边界与不适用

- `tmp/` 是本地草稿区，内容不提交、不对外引用；需长期留存的结论必须迁入
  `records/_TOOLING/` 或 `report/`。
- 本机 `C:\Users\admin\AppData` 的 ACL 异常是本机环境事实，见
  [sandbox_and_file_tools](../environment/sandbox_and_file_tools.md)；绕开它的正确方式是
  设置 `TEMP/TMP` 到仓库内可写目录，不是把产物搬去 C: 盘。

## 依据与变化

- 2026-09-12 17:22 CST：按R500纠正临时脚本位置及tmp根目录描述。历史ACL/清理记录不构成绕过工具安全限制的许可；未运行测试。
- 2026-09-11 18:00 CST：由当日会话沉淀。已执行的纠正：C: 盘目录整体删除，日志与备份迁入
  `records/_TOOLING/IP_REGRESSION_TIMING/current/`，`graphflow-out/` 加入 `.gitignore`，
  `tmp/` 清空。同轮修复了 `tools/runner/record_source.py` 的 Ruff 格式与两处 C901 复杂度。
- 2026-09-11 21:40 CST：**同一条规矩当日再次被违反**——Agent 在修复上述问题后，又陆续在
  `C:\Users\admin\atp_temp\` 写了 9 个探针脚本（`probe*.py`/`repro*.py`）、4 个工具脚本
  （`upd_*.py`/`check_exp.py`）与 3 个运行时目录（`pytest-of-admin/` 等）。说明"知道正确做法"
  不等于"会照做"。本轮按用户指令补充**硬禁令**与**临时脚本生命周期**两节，并把可复用的
  `ipcm_mailbox_probe.py`、`watch_pipeline.py`、`audit_evidence.py` 等迁入
  `records/_TOOLING/FULL_REGRESSION_TIMING/current/scripts/` 留待固化为正式工具。
