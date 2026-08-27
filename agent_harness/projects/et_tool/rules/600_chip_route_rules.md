# [R600] Chip And Route Rules

Chip/Route 规则域负责芯片隔离、共享代码下沉、路线隔离、CAN/CANFD 边界、能力接入、变更影响隔离与 canonical capability 一致性。

## [R600.100] Chip Isolation

### [R600.100.010] Chip Local Code Must Not Depend On Another Chip Local Area

Level: MUST_NOT
When: 修改 ET3101、ET6002 或 ET6003 的 chip-local implementation 时
Rule: 禁止一个芯片的 chip-local 代码直接依赖另一个芯片的 chip-local 代码；可复用能力必须下沉到明确共享层。
Refs: A010, A050

## [R600.200] Shared Code Placement

### [R600.200.010] Cross Chip Reuse Must Move To Shared Layer

Level: MUST
When: 两个及以上芯片需要复用同一语义或基础设施时
Rule: 必须把真正共享的能力放入对应共享 Domain/Application/Protocol/Transport/Probe/Platform 边界，禁止复制后形成多份 canonical 实现。
Refs: A050

## [R600.300] Route Isolation

### [R600.300.010] Logical Routes Must Keep Independent Product State

Level: MUST
When: UART、CAN、CANFD、CMSIS-DAP 或 J-Link 复用物理设备或共享实现时
Rule: 各逻辑 route 必须保持独立 admission、Profile state 和 evidence，禁止从共享底层实现推导另一条 route 已支持。
Refs: A040, A060.010

## [R600.400] Classic CAN And CANFD

### [R600.400.010] Classic CAN Evidence Must Not Promote CANFD

Level: MUST_NOT
When: Classic CAN 与 CANFD 共用 CAN-family backend、codec 或 host interface 时
Rule: 禁止把 Classic CAN 的 capability、hardware evidence 或 release 状态继承给 CANFD；CANFD 必须有自身 route state 与证据。
Refs: A040.020, A040.030, A060.010

## [R600.500] Capability Integration

### [R600.500.010] New Chip Route Capability Must Update Product Truth And Validation Entry

Level: MUST
When: 新增一个正式 Chip × Route 能力或把 candidate/deferred 提升为 supported 时
Rule: 必须同步维护 A010 canonical capability、Profile/admission 状态和对应 validation/evidence 入口，禁止只提交 implementation code 就宣称产品能力完成。
Refs: A010, A060.010, A060.030

## [R600.600] Unsupported Boundary

### [R600.600.010] Unsupported Route Must Not Gain Synthetic Implementation

Level: MUST_NOT
When: 当前 Profile 明确某 Chip × Route 为 unsupported 时
Rule: 禁止通过拼接其他芯片、其他 route 或共享 driver 自动构造正式产品实现；新增支持必须作为显式能力开发处理。
Refs: A010.020.030, A060.010

## [R600.700] Change Impact Isolation

### [R600.700.010] Local Change Must Not Affect Unrelated Chip Route Or Feature

Level: MUST
When: 修改某颗芯片、某条 route 或某个具体 capability/function 的实现、配置或产品行为时
Rule: 变更影响范围必须限制在目标 Chip × Route × Capability 及其确有依赖的共享层；禁止因修改 UART、CAN、CANFD、CMSIS-DAP、J-Link 或某颗芯片的局部功能而改变无关芯片、无关 route 或无关功能的行为与合同。确需修改共享层时必须明确 impact scope，并按受影响范围执行对应回归验证。
Refs: A040, A050, A060.030, R800.600.010