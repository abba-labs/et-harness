# AGENTS.md

本文件是仓库宪法和Agent唯一入口。它只定义不可违背的总约束与规则路由，不复制专项规则正文。

## 0. 不可违反

- 仓库：`Abba-shenfu/Automated_Testing_Platform`。
- 开发只能在`codex_dev`分支继续；仅当用户（人工）明确指定其他分支时才允许例外。不得根据旧文档、当前检出的分支或Agent建议自行换分支、新建分支或worktree。
- 本机正式仓库为`D:\lihuan\vibe_code\codex\projects\ET_ATP_Testing`（WSL：`/mnt/d/lihuan/vibe_code/codex/projects/ET_ATP_Testing`）。每次开始或恢复工作先核对`git rev-parse --show-toplevel`和`git branch --show-current`；不符时停止写入并报告，不自动切换或回退到旧副本。
- 禁止临时补丁分支、Force Push、改写历史、覆盖并行修改或丢弃用户变更。
- 公共架构已冻结；优先级为`可靠 > 稳定 > 轻量化 > 易扩展`。
- 局部问题优先复用正确层并做最小修改；禁止无证据增加Framework、Registry、Workflow、DI、Plugin或通用资源图。
- 公共Case、Driver、Firmware Service和Wrap必须芯片中立；芯片事实只能进入Profile、Capability、Board、Execution Mapping、Chip Driver和芯片文档。
- 禁止把未执行的软件、Keil、FPGA或HIL测试写成PASS，不同后端证据不得互相替代。
- 真实硬件、擦写、烧录、Option Byte、OTP/NVR/Fuse、电源和调试解锁必须遵守外层项目`AGENTS.md`的人工门禁。
- 新测试、诊断及软件验证证据统一按R500写入`artifacts/records/`固定`current`，每轮整理后复用，不写入旧`runs`或累积日期/轮次目录；长期Case知识和最近Excel亦由R500路由。

## 1. 固定任务链路

每个新的非平凡任务和每次实质扩围必须先遵循
`report/design/rules/R002_task_context_navigation.md`，编译新的Task Context：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py compile `
  --task-id <id> --intent "<intent>" `
  --module <module> --change <change> `
  [--ip <ip>] [--chip <chip>] [--lane <lane>]
```

只读取Task Context路由的模块入口、Owner正文、目标代码及相邻责任链。路由缺失必须失败关闭，不得凭文件名、历史文档或对话记忆猜测。
开发完成、运行验证前必须执行`compile_task_context.py scope-check`，确认本任务新增变化没有越过
`write_scope.allowed`。任务扩围时先检查已有变化，再编译扩围后的新上下文。

## 2. 权威来源

冲突优先级：

```text
AGENTS.md
> report/design/rules/Rxxx_*.md
> report/design/rule_owner_catalog.yaml（只作机器索引）
> test_case_doc/<ip>/<ip>.md（公共IP契约实例）
> test_case_doc/<ip>/<CHIP>_<ip>.md（芯片适配事实）
> 当前源码与测试
> report/plans、report/review、report/archive（意图或历史，不是规则）
```

活动规则正文只允许位于`report/design/rules/`。规则编号、Owner、生命周期和写作规范唯一由R001定义。

## 3. 规则路由

| 任务边界 | 必读Owner正文 |
|---|---|
| 规则、编号、Owner、Checker | R001 |
| 任务到代码/规则/验证导航 | R002 |
| 批量Bug修复的范围、定位和验证节奏 | R004 |
| 公共IP语义、芯片适配 | R100 |
| 文档与代码同步 | R110 |
| ET_CASE_SPEC / PLAN / REPORT | R120 |
| Result / Observation / Evidence | R130 |
| IP分析、Feature和Case规划 | R140 |
| PC分层、Driver | R200 |
| Formal Case | R210 |
| Python样式与注释 | R220 |
| Firmware Service | R300 |
| Firmware Wrap、Chip Config | R310 |
| IRQ | R320 |
| Firmware C源码质量 | R330 |
| ET-Frame | R400 |
| Capability | R410 |
| Runner、Run Config、Artifact | R500 |

Task Context必须通过Catalog中的Owner ID解析这些正文；本表只帮助人工定位，不替代机器路由。

## 4. 固定架构

```text
PC:       Case -> Driver -> TargetClient -> Transport/Backend
Firmware: Router -> Own Service -> Own Wrap -> Own Chip Driver
Evidence: Assertion -> Observation/Evidence -> Canonical Result -> Report
```

详细依赖和例外只由对应Rxxx正文定义。新增芯片通常只修改Profile/Capability/Board/Mapping/Chip Driver/芯片文档；新增IP通常只增加公共IP文档、Driver、Case、Service和Wrap。若任务要求修改冻结公共层，必须先证明是跨IP稳定缺口并获得用户批准。

## 5. 变更安全

- 修根因，不打补丁；一个逻辑变更只解决一个责任问题。
- 保持已发布Wire、公共API、Feature/Case语义和已证明HIL行为，除非用户明确批准契约变化。
- 禁止通过弱化Checker/断言、扩大Allowlist/SKIP、增加Timeout或删除覆盖让门禁变绿。
- 禁止混入无关重构、批量格式化、临时脚本、日志和生成物。
- 修改公共语义必须按R110同步公共IP文档；修改芯片事实必须同步`<CHIP>_<ip>.md`。
- 规则、Plan、Review和源码注释不得形成第二份专项规则正文。

## 6. 验证

先运行Task Context列出的最小专项验证。提交任何代码、配置、规则或工具前必须运行：

```powershell
python tools/validate_pc.py
git diff --check
git status --short
```

- Firmware变化还必须运行已有C语法、Contract或Native Harness。
- Wire变化必须同时验证PC、Firmware和Golden Vector。
- 公共层变化必须验证公共Framework及代表性已有IP。
- 软件门禁不能代替真实硬件验证；未执行项明确写`NOT_EXECUTED`。

## 7. Git与CI

1. 提交前确认Branch、Remote、HEAD和工作树，禁止覆盖意外变化。
2. Commit只包含本次逻辑变更，消息准确描述内容。
3. Push后仅当GitHub `Software Quality Gate / validate-software`的`head_sha`等于提交SHA且结论为`success`时，才可声明CI闭环。
4. CI失败必须修根因并产生新提交；无法验证精确SHA时报告`CI_PENDING/NOT_VERIFIED`。

## 8. 完成条件

```text
目标契约与实现一致
+ 公共/芯片边界正确
+ 变更范围单一
+ 专项验证PASS
+ 总软件门禁PASS
+ 精确SHA CI PASS（适用时）
+ 未执行硬件项单独声明
```

最终报告只说明：改了什么、为什么、验证结果、Commit/CI状态和剩余已确认风险。
