# [R700] Profile Capability And Admission Rules

Profile/Capability 规则域负责产品事实权威、supported/deferred/unsupported 状态、connection/evidence、fail-closed 与实现/发布状态分离。

## [R700.100] Profile Authority

### [R700.100.010] Product Support Must Come From Current Profile State

Level: MUST
When: 判断某个 Chip × Route × Capability 是否可作为正式产品能力使用时
Rule: 必须以当前 capabilities/connections/evidence 等正式 Profile 状态为权威，禁止仅依据代码文件或 executor 存在判断支持。
Refs: A060.010.010, A060.010.020

## [R700.200] Supported Deferred Unsupported

### [R700.200.010] Deferred And Unsupported Must Remain Distinct From Supported

Level: MUST
When: Profile 返回 deferred 或 unsupported 状态时
Rule: 必须保持该状态并阻止其被普通正式产品路径当作 supported 使用，禁止由 GUI 可见性或实现存在覆盖 admission 结论。
Refs: A060.010

## [R700.300] Fail Closed Admission

### [R700.300.010] Unknown Or Missing Capability State Must Fail Closed

Level: MUST
When: capability/route 状态缺失、无法解析或不满足正式 admission 条件时
Rule: 必须拒绝继续正式硬件产品操作，禁止采用“可能支持”或其他 route 状态作为默认放行依据。
Refs: A060.010.020

## [R700.400] Evidence Ownership

### [R700.400.010] Evidence Must Match Exact Chip Route Capability

Level: MUST
When: 使用 hardware record、automation result 或 evidence 判断产品闭合时
Rule: 证据必须对应准确的 Chip × Route × Capability，禁止跨芯片或跨 route 借用证据提升支持状态。
Refs: A060.040.020, A060.010.010

## [R700.500] Implementation Support Visibility Separation

### [R700.500.010] Implementation Support Release And Hardware Pass Are Independent States

Level: MUST
When: 描述或判断某项能力当前状态时
Rule: 必须分别表达 implemented、Profile admitted、release visible 和 hardware PASS，禁止把其中任一状态自动等同其他状态。
Refs: A010, A060.010, A060.030, A060.050

## [R700.600] Profile Change Discipline

### [R700.600.010] Profile Promotion Must Have Matching Validation Evidence

Level: MUST
When: 把 capability/route 从 deferred 或 unsupported 改为 supported 时
Rule: 必须同时具备对应实现入口与可追溯验证/evidence 依据，禁止只修改 YAML 状态完成产品能力提升。
Refs: A060.010, A060.030, A060.040