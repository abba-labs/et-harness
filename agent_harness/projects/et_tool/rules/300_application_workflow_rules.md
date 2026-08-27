# [R300] Application And Workflow Rules

Application/Workflow 规则域负责 typed contract、capability/route admission、安全、geometry/range/alignment、recovery precondition、operation postcondition 与统一 cleanup 收敛。

## [R300.100] Typed Operation Contract

### [R300.100.010] Product Operations Must Preserve Typed Request Result Boundaries

Level: MUST
When: 新增或修改正式产品 operation 时
Rule: 必须通过现有 typed request/result 与 application contract 传递产品语义，禁止用 GUI 文本、CLI 日志或底层 driver 参数替代正式操作合同。
Refs: A050.020.010, A050.030.010

## [R300.200] Capability And Route Admission

### [R300.200.010] Admission Must Precede Hardware Execution

Level: MUST
When: operation 依赖特定 Chip × Route × Capability 才能执行时
Rule: 必须在提交真实硬件动作前完成正式 capability/route admission，deferred 或 unsupported 不得由 executor 自行放行。
Refs: A060.010.020, A050.020.020, A050.030.010

## [R300.300] Destructive Operation Safety

### [R300.300.010] Destructive Operations Must Pass Safety Preconditions

Level: MUST
When: 执行 erase、program、OTP、security、Option、WRP 或其他不可逆/高风险操作时
Rule: 必须经过对应 Workflow 的安全前置条件与必要的 operator confirmation，禁止 CLI/GUI 直接调用底层 executor 绕过安全门。
Refs: A060.020.010, A050.020.020, A050.030.010

## [R300.400] Geometry Range And Alignment

### [R300.400.010] Memory Operations Must Validate Target Geometry

Level: MUST
When: operation 涉及 address、range、sector、alignment 或 memory region 时
Rule: 必须在硬件执行前校验目标 memory geometry、范围和对齐约束，禁止依赖底层设备报错替代产品层参数校验。
Refs: A060.020.020

## [R300.500] Recovery And Preconditions

### [R300.500.010] Recovery Paths Must Be Explicit

Level: MUST
When: operation 需要 recovery、factory、project mode 或其他特殊前置状态时
Rule: 必须显式验证并记录所需前置状态，禁止普通产品路径隐式进入 recovery/factory 行为。
Refs: A060.020.010

## [R300.600] Operation Terminal Semantics

### [R300.600.010] Workflow Must Produce One Explicit Terminal Result

Level: MUST
When: Workflow 完成、失败、超时或被取消时
Rule: 必须产生唯一明确的 operation terminal result 并停止后续副作用，禁止失败后继续执行后续硬件步骤。
Refs: A020.070, A060.020

### [R300.600.020] Every Exit Path Must Converge On Cleanup

Level: MUST
When: operation success、failure、timeout、cancel、disconnect、返回首页、切换芯片/route、关闭窗口或退出软件时
Rule: 所有退出路径必须收敛到明确 cleanup：停止或收敛在途硬件动作，结束并回收 QProcess/QTimer/QThread 等运行对象，清理 progress sidecar 与临时运行资产，失效对应 logical session，并由资源所有者关闭 UART/CAN/HID/J-Link 等 host handle/session；若 operation contract 要求恢复或重置目标状态，也必须显式完成，禁止仅依赖进程退出假定全部资源和 target state 已恢复。
Refs: A020.070, A030.090, A050, doc/current_design_analysis/08_RESOURCE_AND_SHUTDOWN_LIFECYCLE.md