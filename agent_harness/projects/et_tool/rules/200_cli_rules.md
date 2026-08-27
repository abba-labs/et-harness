# [R200] CLI Rules

CLI 规则域负责统一入口、参数/命令合同、结果错误、实时增量进度输出、进程生命周期和 chip-local composition。后续命令级细则继续在本文件扩展。

## [R200.100] Unified Entry And Chip Dispatch

### [R200.100.010] Formal CLI Must Dispatch Through Chip Module Contract

Level: MUST
When: 新增或修改芯片 CLI 命令入口时
Rule: 必须保持统一 et-cli 入口与 chip-local module 分发边界，禁止在全局 main/dispatch 中直接堆叠芯片特定硬件实现逻辑。
Refs: A020.010, A020.080

## [R200.200] Argument And Command Contract

### [R200.200.010] Product Operations Must Use Stable Formal Arguments

Level: MUST
When: GUI、Automation 或用户脚本调用正式 et-cli 产品操作时
Rule: 必须通过正式 argv/command contract 表达操作参数，禁止依赖只在人工交互中成立的隐式状态或非正式参数拼接。
Refs: A020, A030.090, A060.040

## [R200.300] Result Error And Return Code

### [R200.300.010] Success Must Not Depend On Log Text

Level: MUST_NOT
When: CLI 返回产品操作结果时
Rule: 禁止仅通过 stdout/stderr 文本判断操作成功；必须使用正式 Result/Error/return-code 合同表达终态。
Refs: A020.070, A050.010

## [R200.400] Progress Output

### [R200.400.010] Progress Must Use Formal Progress Contract

Level: MUST
When: CLI 执行可观察的长时间产品操作时
Rule: 必须通过正式 progress contract/sidecar 输出进度，禁止新增只能由某个 GUI 页面解析的私有进度文本协议。
Refs: A020.070, A030.090

### [R200.400.020] Progress Must Be Published Incrementally

Level: MUST
When: Backend、Probe Algorithm 或其他正式执行链在长操作运行过程中产生新的有效 progress event 时
Rule: 新的有效进度必须通过正式 progress contract 持续增量发布并使下游能够及时消费；禁止把运行期进度缓存到操作结束后一次性输出，也禁止用 elapsed time 或 GUI 动画替代底层已确认的真实进度。
Refs: A020.070, A030.090, doc/current_design_analysis/09_PROGRESS_AND_TIMING_MODEL.md

## [R200.500] Process Lifecycle And Cancellation

### [R200.500.010] Cancel And Timeout Must Produce Terminal CLI Outcome

Level: MUST
When: CLI 操作被取消、超时或底层执行失败时
Rule: 必须停止继续提交新的硬件动作并返回明确终态，禁止子流程失败后仍以成功返回码结束产品操作。
Refs: A020.070, A060.020

## [R200.600] Composition Root

### [R200.600.010] Concrete Dependencies Belong In Chip Local Composition

Level: MUST
When: CLI 需要组合 concrete backend、transport、probe session、executor 或 workflow 时
Rule: concrete 依赖必须在 chip-local composition 边界装配，禁止把芯片/路线特定依赖反向写入共享 Domain 或统一 CLI contract。
Refs: A020.080, A050.040.010, A050.010