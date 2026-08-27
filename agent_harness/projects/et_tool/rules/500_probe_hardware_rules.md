# [R500] Probe And Hardware Rules

Probe/Hardware 规则域负责 Hardware Executor、Probe Driver/Session、Chip Algorithm、Vendor Runtime、DAP/J-Link 路线与硬件副作用边界。

## [R500.100] Hardware Executor Boundary

### [R500.100.010] Chip Local Executor Must Bridge Workflow To Probe Stack

Level: MUST
When: CMSIS-DAP/J-Link operation 需要 concrete hardware execution 时
Rule: chip-local executor 必须作为 Workflow 与 Probe Session/Algorithm 的连接边界，禁止 GUI 或共享 Domain 直接调用 chip algorithm。
Refs: A050.030.020, A050.030.010

## [R500.200] Probe Driver And Session

### [R500.200.010] Shared Probe Driver Must Stay Chip Agnostic

Level: MUST
When: 修改 CMSIS-DAP/J-Link Driver、Session 或 Platform Adapter 时
Rule: shared Probe Driver/Session 必须保持芯片无关，禁止写入 ET3101/ET6002/ET6003 专用 PFlash、Option 或寄存器算法。
Refs: A050.030.030

## [R500.300] Chip Probe Algorithm

### [R500.300.010] Chip Specific Target Behavior Belongs In Chip Algorithm

Level: MUST
When: 行为依赖芯片寄存器、Flash controller、Option/WRP 或 target memory 细节时
Rule: 芯片特定 target 行为必须放在对应 chip algorithm/executor 边界，禁止污染 shared J-Link/CMSIS-DAP driver。
Refs: A050.030.040

## [R500.400] Vendor Runtime Boundary

### [R500.400.010] Vendor Runtime Must Stay Behind Platform Adapter

Level: MUST
When: 使用 J-Link DLL、CMSIS-DAP HID 或其他 vendor runtime 时
Rule: vendor API 必须封装在 Platform/Driver 适配边界之后，禁止上层 GUI/Workflow/Application 直接依赖 vendor API。
Refs: A050.030.050

## [R500.500] Probe Route Isolation

### [R500.500.010] DAP And J-Link Must Remain Distinct Routes

Level: MUST
When: 同一芯片同时具备 CMSIS-DAP 与 J-Link concrete path 时
Rule: 必须保留独立 route admission、driver/session 和 evidence 语义，禁止因 SWD 目标相同而合并产品路线状态。
Refs: A040.040, A040.050, A060.010

## [R500.600] Hardware Side Effects

### [R500.600.010] Executor Must Not Bypass Workflow Safety

Level: MUST_NOT
When: Probe executor 可直接执行 program、erase、Option、WRP 或控制类硬件动作时
Rule: 禁止 executor 被 CLI/GUI 绕过 Workflow 安全与 admission 直接作为正式产品入口调用。
Refs: A050.030.010, A060.020