---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R100
    file: 100_gui_rules.md
    title: GUI Rules
    summary: GUI 紧凑布局、ET 红白视觉基线、连接页与功能页流转、交互终态、实时进度刷新、芯片 GUI 隔离、统一视觉语言、语义配色、功能区可见性、QProcess/CLI Bridge 与发布可见性规则。
    aliases: [gui, ui, layout, compact, visual, visual baseline, red white, et red, rendering, homepage, connection page, workspace, function page, chip gui, independent gui, consistent style, semantic color, control color, visible controls, horizontal scroll, swipe, carousel, progress, progress bar, live progress, realtime progress, refresh progress, connection, connect, identify, timeout, retry, cleanup, qprocess, dialog, loading, 页面, 布局, 紧凑, 红白, 品牌红, 视觉基线, 首页, 连接页, 功能页, 工作台, 芯片GUI, 独立, 统一风格, 语义配色, 控件颜色, 控件可见, 横向滚动, 左右滑动, 隐藏, 进度条, 实时进度, 实时刷新, 连接, 超时, 退出, 清理]
  - id: R200
    file: 200_cli_rules.md
    title: CLI Rules
    summary: et-cli 入口分发、参数合同、结果错误、return code、正式 progress contract、增量进度发布与进程生命周期规则。
    aliases: [cli, et-cli, command, argv, result, error, return code, stdout, stderr, progress, incremental progress, realtime progress, progress stream, process, cancel, dispatch, 命令行, 参数, 返回码, 错误, 进度, 增量进度, 实时进度, 进程, 取消]
  - id: R300
    file: 300_application_workflow_rules.md
    title: Application And Workflow Rules
    summary: typed operation、admission、安全门、破坏性操作、geometry/range/alignment、recovery、终态与 success/failure/timeout/cancel/disconnect/exit 统一资源清理规则。
    aliases: [application, workflow, operation, admission, safety, destructive, erase, program, otp, option, wrp, range, alignment, geometry, recovery, precondition, cleanup, resource cleanup, shutdown, disconnect, exit, close application, session cleanup, 工作流, 安全, 擦除, 烧写, 对齐, 范围, 恢复, 资源清理, 退出清理, 断开清理, 关闭软件, 会话清理]
  - id: R400
    file: 400_backend_protocol_transport_rules.md
    title: Backend Protocol And Transport Rules
    summary: ROM Backend、Protocol/Codec、UART/CAN/CANFD Transport、Host Driver 与依赖方向规则。
    aliases: [backend, protocol, codec, transport, uart, can, canfd, fdcan, serial, driver, frame, checksum, ack, nack, bootrom, 数据链, 协议, 传输, 串口, 驱动]
  - id: R500
    file: 500_probe_hardware_rules.md
    title: Probe And Hardware Rules
    summary: CMSIS-DAP/J-Link executor、driver/session、chip algorithm、vendor runtime 与硬件副作用规则。
    aliases: [probe, hardware, cmsis-dap, dap, jlink, j-link, swd, executor, session, algorithm, flm, vendor, runtime, debug probe, 调试器, 硬件, 算法, 会话]
  - id: R600
    file: 600_chip_route_rules.md
    title: Chip And Route Rules
    summary: 芯片隔离、共享代码下沉、路线隔离、CAN/CANFD 边界、新能力接入、局部变更影响隔离与 unsupported 规则。
    aliases: [chip, route, et3101, et6002, et6003, isolation, shared, can, canfd, uart change, can impact, change isolation, impact scope, feature isolation, unrelated route, unsupported, capability integration, 芯片, 路线, 隔离, 共享, 变更隔离, 影响范围, UART改动, CAN影响, 功能隔离, 无关路线, 新增芯片, 新增路线]
  - id: R700
    file: 700_profile_capability_rules.md
    title: Profile Capability And Admission Rules
    summary: Profile 权威、capability/connection/evidence、supported/deferred/unsupported 与 fail-closed 规则。
    aliases: [profile, capability, capabilities, connection, connections, evidence, supported, deferred, unsupported, fail closed, admission, support state, 配置, 能力, 支持状态, 准入, 证据]
  - id: R800
    file: 800_test_automation_evidence_rules.md
    title: Test Automation And Evidence Rules
    summary: Unit/integration/hardware 验证分层、正式 Automation、evidence provenance、negative boundary 与受影响 Chip/Route 回归规则。
    aliases: [test, unit test, integration test, hardware test, automation, evidence, regression, impact regression, affected routes, affected chips, smoke, real exe, fake runtime, no hardware, 测试, 自动化, 硬件验证, 证据, 回归, 影响回归, 受影响路线, 受影响芯片, 冒烟]
  - id: R900
    file: 900_engineering_release_delivery_rules.md
    title: Engineering Release And Delivery Rules
    summary: Release/package、正式 Release 构建脚本、客户可见性、Build/CMake、依赖方向、合同变更与 Architecture Resource 一致性规则。
    aliases: [engineering, release, delivery, package, build, compile, cmake, ninja, ctest, release script, release_gui, shell, powershell, dependency, customer, compatibility, contract change, resource move, 工程, 发布, 交付, 打包, 编译, 构建, release脚本, 手拼命令, 依赖, 客户版本]
---

# ET-TOOL Rule Index

> 状态：TAXONOMY v0.1 / INITIAL CANONICAL RULES

ET-TOOL 使用“少量规则域文件 + 文件内 Rule Tree + Leaf 精确路由”的规则组织方式。

规则域按稳定工程责任划分，而不是按单次任务、单颗芯片或单个控件拆文件。具体细则持续追加到对应 R100–R900 文件内部，并通过稳定 Rule ID、When/Rule/Refs 与 aliases 为 Agent 提供最小候选集。
