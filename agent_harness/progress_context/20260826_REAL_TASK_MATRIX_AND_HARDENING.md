# ET-TOOL Harness Real Task Matrix And Minimal Hardening — 2026-08-26

> 本文件接续 `20260826_P0_P1_HARDENING.md`。它记录 P0/P1 合入 `main` 后的真实任务验证、暴露问题、最小修复和最终回归事实。

## 1. 本阶段目标

本阶段不继续扩张治理功能，只验证 Harness 在真实工作流中是否同时满足：

- Agent 能快速获得正确 Context、Rule、Knowledge 和 Gate；
- 只读任务不会制造无价值 Knowledge；
- 代码变更后不能绕过当前 Code Gate；
- 旧 Review / Evidence 不能授权新的代码变更；
- 编译构建只能进入正式 Release 脚本；
- 常见文件修改方式、失败后部分写入和多 Runtime 场景不能脱离约束。

P0/P1 已通过 PR #37 合入 `main`，合并提交为：

```text
00b4c16832a95c2bc4132227346e257e1d5d155f
```

随后从该提交创建：

```text
validation/harness-real-task-matrix-v0.1
```

## 2. 初始真实验证结果

首次 Workflow：

```text
run: 32954363984
assertions: 53
PASS: 40
FAIL: 13
```

其中 1 项是测试断言自身写错；其余失败归并为以下真实问题：

1. **Review 未绑定变更轮次**：相同文件第二次修改可能复用第一次 Packet / Evidence。
2. **Context 引用持续累加**：第二次治理刷新可能达到 Context 上限，导致当前 Review Packet 未生成。
3. **修改工具识别不全**：`python`、`node`、`GitHub.update_file` 等写文件方式未进入代码变更流程。
4. **失败写操作处理不安全**：工具写入一部分后抛错时，只记录 Tool Error，没有按“代码可能已改变”处理。
5. **构建入口存在漏判**：`msbuild`、`devenv`、`nmake` 未被识别为 Product Build。
6. **Release 入口匹配过宽**：字符串包含正式路径即可通过，伪后缀、前缀目录和路径穿越形式可能误放行；Windows 分隔符形式反而被误拒绝。

这些问题会导致 Agent 使用旧 Evidence、绕过当前 Gate 或直接绕过 Release 构建入口，因此属于必须修复的真实漏洞。

## 3. 最小修复

### 3.1 Review 与 Evidence 绑定当前变更轮次

- `reviewEpoch` 进入 Review Request、Packet ID 和 Evidence metadata；
- 每次代码修改都递增 `codeChangeEpoch`；
- 当前轮次没有 Review Packet 时，Build / Test 和 Task Complete 均 fail-closed；
- 相同文件再次修改也必须生成新的 Review Packet。

### 3.2 控制 Context 增长

- 代码变更后的新路由替换当前 Working Set，而不是无边界追加；
- Task Ledger 的 Scope / Constraint 引用各限制为 64 项；
- 当前路由优先保留，历史引用只作为后续补充。

### 3.3 补齐实际修改入口

增加对以下修改方式的识别：

```text
update_file
Python pathlib.write_text / write_bytes
Node writeFileSync / appendFileSync
常见 shell patch / redirect / move / remove / copy
```

对于可能修改文件的 Tool，即使最终返回 Error，也保守创建新的代码变更轮次并要求当前 Gate Review。

### 3.4 收紧 R900 构建入口

- 增加 `msbuild`、`devenv`、`nmake` 的 Build 识别与 Deny；
- 正确归一化 Windows 路径分隔符；
- Release Allow 必须匹配完整 canonical 路径边界；
- 拒绝伪后缀、额外前缀目录和路径穿越形式；
- 保持正式入口：

```text
source/release/release_gui.bat
```

## 4. 最终验证结果

### 4.1 Real Task Matrix

修复后 Workflow：

```text
run: 32956834172
package builds: 18/18 PASS
focused unit tests: 77/77 PASS
matrix iterations: 3
assertions per iteration: 53
matrix assertions: 159/159 PASS
```

三轮 Run ID：

```text
REAL-MATRIX-1-1296f080
REAL-MATRIX-2-69d3269d
REAL-MATRIX-3-8385a340
```

每轮覆盖：

- 只读任务与同 Task Context 复用；
- 无价值 Knowledge 不沉淀；
- 文档支持的 Project Knowledge 创建、自动 VALIDATED 和下一轮自动路由；
- 真实临时 Git 工作区文件修改；
- 两次连续修改、两个独立 Review Epoch；
- Gate 前 Build BLOCK、Gate PASS 后正式 Release 入口放行；
- 旧 Evidence 无法授权第二次修改；
- CMake / Ninja / MSBuild / Devenv / NMake 与伪 Release 路径负向矩阵；
- Python、GitHub update、部分写入失败后的修改检测；
- 多 Runtime 隔离、Active Turn、错误 Turn、关闭后写入；
- Tool Error 不制造垃圾 Knowledge；
- 非法 Knowledge Category fail-closed。

### 4.2 原有基线回归

回归 Workflow：

```text
run: 32957212106
```

结果：

```text
Positive Public Governance Runtime: PASS
Round A Governance Adversarial: 9/9 PASS
Round B Knowledge Adversarial: 6/6 PASS
```

说明本轮修复没有破坏：

- 8/8 Mandatory Closure；
- Gateway 阻断与 R900；
- Global Knowledge 防过度晋级；
- Knowledge Category / Source / Evidence / Contradiction 边界；
- Tool Error 保持 CHECK 而不强制制造 Candidate。

### 4.3 PR 广泛回归暴露的旧 Batch 1 断言

PR #38 触发仓库现有 12 套 Harness 检查时，`ET-TOOL Knowledge Batch 1` 首次失败：

```text
K001.001 is not READY: INSUFFICIENT
已是文档验证级 VALIDATED；尚缺符合 Scope 的实际验证 Evidence
```

该失败不是 Runtime 或 Validation Policy 回归，而是旧脚本仍假设：

```text
所有 CANDIDATE / VALIDATED Knowledge 都必须返回 READY
```

正确验收为：

```text
CANDIDATE + 当前 Validation Policy 认可的 SUPPORT
  -> READY
  -> targetStatus = VALIDATED

VALIDATED + 只有 Source-backed SUPPORT、没有 Scope 合法 REAL_TEST
  -> INSUFFICIENT
  -> 等待 REAL_TEST Evidence
  -> 不重复 Promotion
```

Batch 1 的历史 Verification 记录使用 `basisKind: SOURCE`，未承诺固定的内部 `validationClass`。因此 Smoke 只验证：

- 每条 Knowledge 有 1 条当前 Claim 的独立 SUPPORT；
- 没有 CONTRADICT；
- CANDIDATE 仅在 Policy 返回 READY 时晋级；
- 已 VALIDATED 的 Knowledge 在缺少 REAL_TEST 时保持 INSUFFICIENT。

这里只更新 `phase4_ettool_knowledge_batch1_v0_1_integration.sh` 的过期或过强断言，没有放宽 Runtime、Knowledge Policy 或 Evidence 边界。

## 5. Agent 工作效率结论

当前证据支持以下结论：

- 只读任务能够复用 Context，不会强制进入复杂 Gate；
- 普通 Tool Error 不强制生成 Knowledge；
- 有权威 Source 的稳定知识可以自动沉淀并在下一 Turn 复用；
- 只有实际代码变更才进入 Code Gate；
- 同一任务的连续修改会产生新轮次，但不会无限累积 Working Set；
- 日常 Push / PR 默认运行 1 轮 53 项矩阵；手动验收默认运行 3 轮，以兼顾速度与置信度。

## 6. 当前未覆盖边界

本阶段没有伪造以下结论：

- Ubuntu CI 没有实际执行 Windows `release_gui.bat`；
- 没有启动真实 Qt GUI 产物；
- 没有连接 J-Link、CMSIS-DAP、CAN、UART 或真实芯片；
- Real Task Matrix 使用确定性的 Generic Model Contract Client，不是外部在线大模型；
- 本轮验证的是 Harness 生命周期和约束链，不是 ET-TOOL 全产品功能验证。

## 7. 下一步

只继续两类真实环境验证：

1. Windows 环境执行一次小型 ET-TOOL 代码修改，走完 Code Gate 和真实 `release_gui.bat --mode dev`；
2. 选择一条有硬件条件的只读或低风险功能，验证 Tool Adapter、Evidence、Reflection 和 Closure 全链。

在这两类验证暴露新问题前，不增加 Permit、签名、多项目 Quorum、复杂 Scope Arbiter 或完整零信任沙箱。
