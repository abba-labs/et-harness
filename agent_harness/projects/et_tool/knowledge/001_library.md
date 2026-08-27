# [K001] Managed Knowledge Shard K001

## [K001.001] Product Support Is Multi-Dimensional
Status: VALIDATED
Category: C010.040
Fact: ET-TOOL 的产品支持不是单一布尔值；Code Implemented、Profile support、Release visibility、Hardware evidence 和 Runtime safety gate 是彼此独立的产品状态，不能互相替代。
Scope: ET-TOOL product support model
Provenance: source://project/et-tool/SRC000001
Tags: [product-support, profile, release, evidence]
Refs: [A060, R700]
Sources: [source://project/et-tool/SRC000001]

## [K001.002] Capability Admission Uses Capability And Route
Status: VALIDATED
Category: C010.040
Fact: ET-TOOL 运行时 Capability Admission 以 capability × route 解析支持状态；只有 support=supported 才通过正式准入，deferred、unsupported、not_implemented 和 not_run_by_policy 不自动视为 supported。
Scope: ET-TOOL runtime capability admission
Provenance: source://project/et-tool/SRC000001
Tags: [capability, route, admission, fail-closed]
Refs: [A060.010.020, R700.200.010]
Sources: [source://project/et-tool/SRC000001]

## [K001.003] ET6002 CANFD Is Explicitly Fail Closed
Status: VALIDATED
Category: C010.020
Fact: ET6002 的 route.canfd.rom 当前 product_status 为 unsupported，profile_strategy 为 explicit_fail_closed；当前产品实现图没有 ET6002 CANFD ROM implementation node。
Scope: ET6002 CANFD product state
Provenance: source://project/et-tool/SRC000002
Tags: [et6002, canfd, unsupported, fail-closed]
Refs: [A010.020.030, A050.020.200, A060.030.030.200.030]
Sources: [source://project/et-tool/SRC000002]

## [K001.004] ET3101 Models Five Product Routes
Status: VALIDATED
Category: C010.010
Fact: ET3101 当前 Profile 建模 UART、Classic CAN、CANFD、J-Link 和 CMSIS-DAP 五条产品路线；具体 capability 的 hardware_status 与产品支持仍需按 route/capability 独立判断。
Scope: ET3101 product routes
Provenance: source://project/et-tool/SRC000003
Tags: [et3101, uart, can, canfd, jlink, cmsis-dap]
Refs: [A010.010, A060.010.010.010]
Sources: [source://project/et-tool/SRC000003]

## [K001.005] ET6003 ROM And Probe Route State
Status: VALIDATED
Category: C010.030
Fact: ET6003 当前 ROM 产品路线包含 UART、Classic CAN 和 CANFD；J-Link 与 CMSIS-DAP 在当前 Profile 中仍属于 deferred future routes，需要各自 closure 才能进入正式产品支持。
Scope: ET6003 product route state
Provenance: source://project/et-tool/SRC000004
Tags: [et6003, uart, can, canfd, jlink, cmsis-dap, deferred]
Refs: [A010.030, A060.010.010.030]
Sources: [source://project/et-tool/SRC000004]

## [K001.006] ROM Execution Layering
Status: VALIDATED
Category: C020.060
Fact: ET-TOOL ROM 产品操作主链为 Application/Workflow → Backend → Protocol/Transport；Backend 将产品操作落实为 BootROM 命令序列或共享 ROM 执行流程。
Scope: ET-TOOL ROM execution layering
Provenance: source://project/et-tool/SRC000005
Tags: [rom, workflow, backend, protocol, transport]
Refs: [A050.020, R400.100.010, R400.400.010]
Sources: [source://project/et-tool/SRC000005]

## [K001.007] Protocol Codec Does Not Own Physical IO
Status: VALIDATED
Category: C020.060
Fact: ET-TOOL Protocol/Codec 负责 command、frame、checksum、ACK/NACK、字段编码和响应解析，不负责打开 UART/CAN 物理设备；物理设备访问属于 Transport/Host IO。
Scope: ET-TOOL protocol transport boundary
Provenance: source://project/et-tool/SRC000005
Tags: [protocol, codec, transport, uart, can]
Refs: [A050.020.040, A050.020.050, R400.200.010]
Sources: [source://project/et-tool/SRC000005]

## [K001.008] Shared UART And CAN Family Host Transport
Status: VALIDATED
Category: C020.060
Fact: ET-TOOL 三颗芯片的 UART ROM 路线共享 host serial transport；Classic CAN 与 CANFD 共享 CAN-family transport，并在 composition/route 边界选择各自 concrete driver。
Scope: ET-TOOL shared host transport
Provenance: source://project/et-tool/SRC000005
Tags: [uart, can, canfd, transport, driver]
Refs: [A050.020.050.010, A050.020.050.020, R400.600.010]
Sources: [source://project/et-tool/SRC000005]

## [K001.009] ET6003 CAN And CANFD Share Main Implementation
Status: VALIDATED
Category: C020.030
Fact: ET6003 Classic CAN 与 CANFD 共享 memory、PFlash、readonly、verify、security、speed 等 CAN-family runner/backend/codec；CANFD 的 identify、Profile admission 和 host driver 保持 route-specific 分叉。
Scope: ET6003 CAN family implementation
Provenance: source://project/et-tool/SRC000005
Tags: [et6003, can, canfd, shared, route-specific]
Refs: [A050.020.300.020, A050.020.300.030]
Sources: [source://project/et-tool/SRC000005]

## [K001.010] Bundled ZLG Runtime Is Not USB Driver
Status: VALIDATED
Category: C030.020
Fact: ET-TOOL SDK 内置的 ZLG runtime bundle 可以满足编译、打包和程序启动所需 DLL，但不能替代 Windows 识别物理 CAN 适配器所需的 USB 驱动。
Scope: ET-TOOL Windows ZLG runtime
Provenance: source://project/et-tool/SRC000009
Tags: [zlg, windows, runtime, usb-driver, can]
Refs: [A060.050]
Sources: [source://project/et-tool/SRC000009]

## [K001.011] Machine Local Paths Belong In Local Environment
Status: VALIDATED
Category: C030.010
Fact: ET-TOOL 机器本地 Qt、ZLG runtime 和 build 路径应放在 source/release/configs/local_environment.json 或对应环境变量中；customer_release.json 只描述发布内容，不应提交机器本地路径。
Scope: ET-TOOL release environment configuration
Provenance: source://project/et-tool/SRC000009
Tags: [qt, zlg, build-path, local-environment, release-config]
Refs: [A060.050, R900]
Sources: [source://project/et-tool/SRC000009]

## [K001.012] GUI Connected State Is Logical Session
Status: VALIDATED
Category: C040.020
Fact: ET-TOOL GUI 中的“已连接”主要表示存在有效的逻辑 Session，而不是 GUI 进程长期持有 UART、CAN、CMSIS-DAP 或 J-Link 的底层硬件 Handle。
Scope: ET-TOOL GUI connection lifecycle
Provenance: source://project/et-tool/SRC000006
Tags: [gui, session, connection, handle, cli]
Refs: [A030, A060.020]
Sources: [source://project/et-tool/SRC000006]

## [K001.013] Runtime Resources Have Four Distinct Layers
Status: VALIDATED
Category: C040.020
Fact: ET-TOOL 运行资源应区分 GUI 逻辑状态、Qt 运行对象、et-cli 子进程内 Host 硬件资源、MCU Target 状态四层；它们的生命周期和所有权不能混为一谈。
Scope: ET-TOOL runtime resource ownership
Provenance: source://project/et-tool/SRC000006
Tags: [resource, qprocess, qthread, hardware-handle, target-state]
Refs: [A030, A050, A060.020]
Sources: [source://project/et-tool/SRC000006]

## [K001.014] Host Cleanup Is Not Target Recovery
Status: VALIDATED
Category: C040.040
Fact: ET-TOOL 中 Host resource cleanup 与 MCU target state recovery 是不同动作；关闭进程或 Host Handle 不代表目标芯片已经恢复到正确的 running/reset/boot 状态。
Scope: ET-TOOL cleanup and target recovery
Provenance: source://project/et-tool/SRC000006
Tags: [cleanup, target-recovery, reset, halt, resource]
Refs: [R300.600.020, A060.020]
Sources: [source://project/et-tool/SRC000006]

## [K001.015] Low Level Host Resources Use Close Plus RAII
Status: VALIDATED
Category: C040.020
Fact: ET-TOOL 当前 UART、ZLG CAN、J-Link 和 CMSIS-DAP 底层资源总体采用 explicit close 加 RAII destructor fallback 的双层释放机制。
Scope: ET-TOOL low-level host resource cleanup
Provenance: source://project/et-tool/SRC000006
Tags: [raii, close, uart, can, jlink, cmsis-dap]
Refs: [A050.020.050, A050.030]
Sources: [source://project/et-tool/SRC000006]

## [K001.016] OperationProgressEvent Is The Canonical Progress Semantic
Status: VALIDATED
Category: C040.030
Fact: ET-TOOL 正式进度语义由 OperationProgressEvent 表达，包含 operation、phase、current、total、unit、message 和 indeterminate；真实百分比不由 GUI 自行估算。
Scope: ET-TOOL operation progress contract
Provenance: source://project/et-tool/SRC000007
Tags: [progress, operation-progress, current, total, indeterminate]
Refs: [A050.020.010, R200.400.010]
Sources: [source://project/et-tool/SRC000007]

## [K001.017] Progress Flows Through CLI JSONL Sidecar
Status: VALIDATED
Category: C040.030
Fact: ET-TOOL 当前主要 Progress 数据链为 Backend/Probe Algorithm → OperationProgressCallback → chip-local CLI progress writer → JSONL sidecar → GUI parser → QProgressBar。
Scope: ET-TOOL progress data path
Provenance: source://project/et-tool/SRC000007
Tags: [progress, jsonl, sidecar, cli, gui]
Refs: [A030.090, R100.400.020, R200.400.020]
Sources: [source://project/et-tool/SRC000007]

## [K001.018] Progress Poll Cadence Is About 100ms
Status: VALIDATED
Category: C040.030
Fact: ET-TOOL 当前 GUI 默认约每 100 ms 增量读取 Progress sidecar；100 ms 是 UI 更新 cadence，不是设备 I/O timeout 或 operation deadline。
Scope: ET-TOOL current GUI progress polling
Provenance: source://project/et-tool/SRC000007
Tags: [progress, 100ms, poll, cadence, timeout]
Refs: [A030.090]
Sources: [source://project/et-tool/SRC000007]

## [K001.019] Elapsed Time Does Not Estimate Real Percentage
Status: VALIDATED
Category: C040.030
Fact: ET-TOOL 的 determinate progress 来自 Backend/Algorithm 已确认的 current/total；Elapsed Time 只表示 wall-clock 耗时，不用于计算或伪造真实进度百分比。
Scope: ET-TOOL progress versus elapsed time
Provenance: source://project/et-tool/SRC000007
Tags: [progress, elapsed, percentage, hardware-confirmed]
Refs: [R100.400.020, R200.400.020]
Sources: [source://project/et-tool/SRC000007]

## [K001.020] Progress Sidecar Is Per Job Temporary Asset
Status: VALIDATED
Category: C040.030
Fact: ET-TOOL 每个支持结构化进度的 job 使用独立 progress 临时文件并按 offset 增量读取；operation 完成后删除临时文件，捕获到的 progress JSONL 可进入 session log 作为过程记录。
Scope: ET-TOOL progress sidecar lifecycle
Provenance: source://project/et-tool/SRC000007
Tags: [progress, sidecar, temp-file, session-log, cleanup]
Refs: [A030.090, R300.600.020]
Sources: [source://project/et-tool/SRC000007]

## [K001.021] ET3101 Handles Indeterminate Progress As Valid Busy State
Status: VALIDATED
Category: C040.030
Fact: ET3101 当前 GUI 能把 indeterminate progress 作为合法 busy/waiting 状态处理，并使用约 250 ms determinate hold 缓冲确定进度与等待状态之间的频繁切换。
Scope: ET3101 GUI progress behavior
Provenance: source://project/et-tool/SRC000007
Tags: [et3101, progress, indeterminate, busy, 250ms]
Refs: [A030.040.010]
Sources: [source://project/et-tool/SRC000007]

## [K001.022] ET GUI Brand Red Is C00000
Status: VALIDATED
Category: C050.010
Fact: 当前 ET-TOOL GUI Visual Baseline 使用 ET 品牌红 #C00000 作为主要品牌强调色，白色和浅灰作为主要界面与功能区底色。
Scope: ET-TOOL desktop GUI visual baseline
Provenance: source://project/et-tool/SRC000008
Tags: [gui, visual, brand-red, c00000, red-white]
Refs: [R100.100.030]
Sources: [source://project/et-tool/SRC000008]

## [K001.023] Brand Primary And Danger Use Different Red Semantics
Status: VALIDATED
Category: C050.030
Fact: 当前 ET-TOOL GUI 视觉原型刻意区分品牌 Primary 红与 Danger 红；危险操作使用更深的危险红，避免把 ET 品牌红同时解释为品牌强调和危险语义。
Scope: ET-TOOL GUI semantic color baseline
Provenance: source://project/et-tool/SRC000008
Tags: [gui, semantic-color, primary, danger, red]
Refs: [R100.800.010]
Sources: [source://project/et-tool/SRC000008]

## [K001.024] GUI HTML Is Visual Reference Not Product Implementation
Status: VALIDATED
Category: C050.010
Fact: html/et_tool_ui_design_prototype_v3_et_red_white_polished.html 是当前 ET-TOOL GUI 的视觉与 Rendering Reference，不是正式产品 GUI 实现代码。
Scope: ET-TOOL GUI design reference
Provenance: source://project/et-tool/SRC000008
Tags: [gui, html, prototype, visual-reference]
Refs: [R100.100.020, R100.100.030]
Sources: [source://project/et-tool/SRC000008]

## [K001.025] Dev And Release Use One Release Framework
Status: VALIDATED
Category: C060.010
Fact: ET-TOOL Development/debug build 与正式 Release 共用 source/release 构建框架；开发构建通过 release_gui.bat --mode dev 进入 Debug、保留 build directory 并支持增量 Ninja 构建。
Scope: ET-TOOL build framework
Provenance: source://project/et-tool/SRC000009
Tags: [build, release, dev, release_gui, ninja]
Refs: [R900.300.020]
Sources: [source://project/et-tool/SRC000009]

## [K001.026] ETRC Is Compressed And Checksummed Not Encrypted
Status: VALIDATED
Category: C060.020
Fact: ET-TOOL formal release 使用 app/release_config.etrc；ETRC 是带长度和 CRC32 检查的压缩二进制容器，不提供加密语义，dev package 则保留可读 JSON 便于调试。
Scope: ET-TOOL release config packaging
Provenance: source://project/et-tool/SRC000009
Tags: [release, etrc, crc32, compression, json]
Refs: [A060.050]
Sources: [source://project/et-tool/SRC000009]

## [K001.027] Version Origin And Release Config Must Stay Consistent
Status: VALIDATED
Category: C060.030
Fact: ET-TOOL 工具基础版本来源是 source/CMakeLists.txt 的 project(VERSION ...)；正式发版时 customer_release.json 的 version 与 tool_name 必须同步，生成的 version.h、version.cmake 和 generated catalog 不应手工修改。
Scope: ET-TOOL version propagation
Provenance: source://project/et-tool/SRC000009
Tags: [version, cmake, release-config, generated-file]
Refs: [R900.500.010]
Sources: [source://project/et-tool/SRC000009]

## [K001.028] Newly Discovered Release Surfaces Default Disabled
Status: VALIDATED
Category: C060.020
Fact: ET-TOOL release config refresh 会从 Profiles、chip GUI release visibility 和 CMake 自动发现 chip/route/page/build target；新发现的 chip、route 和 page 默认关闭，避免新 SDK 功能被意外发布。
Scope: ET-TOOL release catalog discovery
Provenance: source://project/et-tool/SRC000009
Tags: [release, catalog, discovery, default-false, visibility]
Refs: [A060.050, R100.600.010]
Sources: [source://project/et-tool/SRC000009]
