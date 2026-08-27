# [R400] Backend Protocol And Transport Rules

ROM 数据链规则域负责 Backend、Protocol/Codec、Transport、Host Driver 的职责边界与共享实现方式。

## [R400.100] Backend Execution Boundary

### [R400.100.010] Backend Owns Product Operation Execution Sequence

Level: MUST
When: ROM 路线把正式 operation 落实为 BootROM 命令序列时
Rule: Backend 必须承担产品操作到协议/传输调用的执行编排，禁止把完整产品 operation 语义下沉到 Transport driver。
Refs: A050.020.030

## [R400.200] Protocol And Codec Boundary

### [R400.200.010] Protocol Must Not Open Physical Devices

Level: MUST_NOT
When: 编写或修改 command、frame、checksum、ACK/NACK、codec 或 parser 时
Rule: 禁止 Protocol/Codec 直接打开 UART/CAN 设备或依赖 concrete host driver；物理设备访问属于 Transport。
Refs: A050.020.040, A050.020.050

## [R400.300] Transport And Host IO Boundary

### [R400.300.010] Transport Must Not Own Chip Product Semantics

Level: MUST_NOT
When: 修改 UART/CAN/CANFD Transport 或 OS/vendor host driver 时
Rule: 禁止 Transport 根据芯片型号实现 erase/program/security 等产品操作语义；Transport 只负责字节/帧和设备 IO。
Refs: A050.020.050

## [R400.400] Dependency Direction

### [R400.400.010] ROM Layer Dependencies Must Flow Downward

Level: MUST
When: ROM 路线新增跨层依赖时
Rule: 依赖方向必须保持 Application/Workflow → Backend → Protocol/Transport，禁止 Protocol/Transport 反向依赖 chip-local CLI 或 GUI。
Refs: A050.020

## [R400.500] CAN Family Shared Implementation

### [R400.500.010] Shared CAN Family Code Must Preserve Route Specific Differences

Level: MUST
When: Classic CAN 与 CANFD 复用 Backend、Codec 或 Transport 主干时
Rule: 必须保留 route-specific admission、identify、driver 和 evidence 分叉，禁止因共享实现而把 Classic CAN 状态或证据自动继承给 CANFD。
Refs: A050.020.300.020, A050.020.300.030, A040.020, A040.030

## [R400.600] Concrete Host Driver Selection

### [R400.600.010] Concrete Driver Selection Belongs At Composition Boundary

Level: MUST
When: 选择 serial、classic CAN 或 CANFD concrete host driver 时
Rule: concrete driver 必须由 composition/route 入口选择，禁止在共享 Protocol 中硬编码某个 vendor driver。
Refs: A050.020.050, A050.040.010