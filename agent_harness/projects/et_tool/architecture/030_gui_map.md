# [A030] GUI Projection Map

Role: 从统一 GUI、chip-local workbench、route/page/action 视角投影 A010 canonical 能力实例，回答“某个产品能力在 GUI 哪里呈现和触发”。
Boundary: 不重新定义产品能力，不复制底层实现；GUI 节点只锁定正式产品入口，并通过 A020/A050/A060 继续导航。
Resources: source/apps/gui/shell/et_tool_gui_main.cpp, source/apps/gui/chips/gui_builtin_preview_window_registry.cpp
Relations: A010, A020, A040, A050, A060

## [A030.010] Unified Shell And Chip Selection

Role: 统一 et-tool GUI 首页、芯片选择与进入 chip-local workbench 的入口。
Resources: source/apps/gui/shell/et_tool_gui_main.cpp, source/apps/gui/chips/gui_builtin_preview_window_registry.cpp
Relations: A010

## [A030.020] Connection And Identify Lifecycle

Role: 首页连接、identify、deadline、startup transaction 与进入 workbench 前的连接上下文建立。
Resources: source/apps/gui/shell/et_tool_gui_main.cpp, source/apps/gui/device/gui_connection_device_model.h, source/apps/gui/device/gui_qt_connection_device_discovery.h
Relations: A010, A020.070, A060.010

## [A030.030] Chip Local Workbench Projection

Role: 每颗芯片独立的 route/page/action/session 产品工作区投影。
Relations: A010

### [A030.030.010] ET3101 Workbench

Role: ET3101 chip-local GUI 工作区与 release visibility 入口。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010, A060.050.010.010

### [A030.030.020] ET6002 Workbench

Role: ET6002 chip-local GUI 工作区、CLI bridge/QProcess 与 release visibility 入口。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_preview_main.cpp, source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_cli_qprocess_runner.h, source/apps/gui/chips/et6002/preview/et6002_gui_release_visibility.h
Relations: A010.020, A060.050.010.020

### [A030.030.030] ET6003 Workbench

Role: ET6003 chip-local GUI 工作区、session 与 release visibility 入口。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h, source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h
Relations: A010.030, A060.050.010.030

## [A030.040] UART GUI Projection

Role: UART 产品能力的 GUI 页面、参数、动作与正式 CLI 调用投影。
Relations: A010.010.010, A010.020.010, A010.030.010, A020.020, A040.010

### [A030.040.010] ET3101 UART GUI

Role: ET3101 UART GUI surface；底层实现与验证分别沿 A050/A060 下钻。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010.010, A020.020.010, A050.020.100.010, A060.030.030.100.010, A060.050.010.010

### [A030.040.020] ET6002 UART GUI

Role: ET6002 UART GUI surface，经 ET6002 GUI CLI bridge/QProcess 调用正式 et-cli。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_preview_main.cpp, source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_cli_qprocess_runner.h
Relations: A010.020.010, A020.020.020, A050.020.200.010, A060.030.030.200.010, A060.050.010.020

### [A030.040.030] ET6003 UART GUI

Role: ET6003 UART GUI surface 与 session 入口。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h
Relations: A010.030.010, A020.020.030, A050.020.300.010, A060.030.030.300.010, A060.050.010.030

## [A030.050] CAN GUI Projection

Role: Classic CAN 产品能力的 GUI 投影。
Relations: A010.010.020, A010.020.020, A010.030.020, A020.030, A040.020

### [A030.050.010] ET3101 CAN GUI

Role: ET3101 Classic CAN GUI surface。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010.020, A020.030.010, A050.020.100.020, A060.030.030.100.020, A060.050.010.010

### [A030.050.020] ET6002 CAN GUI

Role: ET6002 Classic CAN GUI surface，经正式 CLI bridge/QProcess 调用产品链。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_preview_main.cpp, source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_cli_qprocess_runner.h
Relations: A010.020.020, A020.030.020, A050.020.200.020, A060.030.030.200.020, A060.050.010.020

### [A030.050.030] ET6003 CAN GUI

Role: ET6003 Classic CAN GUI surface；与 CANFD 的共享实现由 A050 表达，不在 GUI 层复制。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h
Relations: A010.030.020, A020.030.030, A050.020.300.020, A060.030.030.300.020, A060.050.010.030

## [A030.060] CANFD GUI Projection

Role: CAN FD 产品能力与当前 unsupported 边界的 GUI 投影。
Relations: A010.010.030, A010.020.030, A010.030.030, A020.040, A040.030

### [A030.060.010] ET3101 CANFD GUI

Role: ET3101 CANFD GUI surface。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010.030, A020.040.010, A050.020.100.030, A060.030.030.100.030, A060.050.010.010

### [A030.060.020] ET6002 CANFD GUI Boundary

Role: ET6002 当前没有正式 CANFD 产品升级能力；GUI 需求必须先落 unsupported/fail-closed 产品事实，不提供虚假页面实现入口。
Resources: source/profiles/chips/et6002/capabilities.yaml, source/profiles/chips/et6002/connections.yaml, source/release/configs/customer_release.json
Relations: A010.020.030, A020.040.020, A060.010.010.020, A060.030.030.200.030, A060.050.010.020

### [A030.060.030] ET6003 CANFD GUI

Role: ET6003 CANFD GUI surface；route-specific状态与共享 CAN-family 实现分别沿 A060/A050 判断。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h, source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h
Relations: A010.030.030, A020.040.030, A050.020.300.020, A050.020.300.030, A060.030.030.300.030, A060.050.010.030

## [A030.070] CMSIS-DAP GUI Projection

Role: CMSIS-DAP 产品能力的 GUI 投影。
Relations: A010.010.040, A010.020.040, A010.030.040, A020.050, A040.040

### [A030.070.010] ET3101 DAP GUI

Role: ET3101 DAP GUI surface；正式实现从 Probe executor/driver/algorithm 下钻。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010.040, A020.050.010, A050.030.020.010.010, A060.030.030.100.040, A060.050.010.010

### [A030.070.020] ET6002 DAP GUI

Role: ET6002 DAP GUI surface；release visible 与 Profile admitted 必须分开判断。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_preview_main.cpp, source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_release_visibility.h
Relations: A010.020.040, A020.050.020, A050.030.020.020.010, A060.030.030.200.040, A060.050.010.020

### [A030.070.030] ET6003 DAP GUI

Role: ET6003 DAP GUI surface；release visible 与 Profile admitted 必须分开判断。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h, source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h
Relations: A010.030.040, A020.050.030, A050.030.020.030.010, A060.030.030.300.040, A060.050.010.030

## [A030.080] J-Link GUI Projection

Role: J-Link 产品能力的 GUI 投影。
Relations: A010.010.050, A010.020.050, A010.030.050, A020.060, A040.050

### [A030.080.010] ET3101 J-Link GUI

Role: ET3101 J-Link GUI surface。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_preview_main.cpp, source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h
Relations: A010.010.050, A020.060.010, A050.030.020.010.020, A060.030.030.100.050, A060.050.010.010

### [A030.080.020] ET6002 J-Link GUI

Role: ET6002 J-Link GUI surface；release visible 与 Profile admitted 必须分开判断。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_preview_main.cpp, source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_release_visibility.h
Relations: A010.020.050, A020.060.020, A050.030.020.020.020, A060.030.030.200.050, A060.050.010.020

### [A030.080.030] ET6003 J-Link GUI

Role: ET6003 J-Link 在 chip-local workbench 中的 GUI surface、session 与 release-visibility 入口；具体硬件动作仍通过正式 CLI 产品链。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_preview_main.cpp, source/apps/gui/chips/et6003/preview/et6003_gui_session_model.h, source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h
Relations: A010.030.050, A020.060.030, A050.030.020.030.020, A060.010.010.030, A060.030.030.300.050, A060.050.010.030

## [A030.090] CLI Bridge QProcess Result And Progress

Role: GUI 通过正式 et-cli argv、QProcess、stdout/stderr/return code 与 progress sidecar 驱动硬件操作和状态展示。
Resources: source/apps/gui/chips/et6002/application_bridge/et6002_gui_cli_bridge.h, source/apps/gui/chips/et6002/preview/et6002_gui_cli_qprocess_runner.h, source/application/kernel/operation_progress.h
Relations: A020.070, A060.030, A060.040

## [A030.100] Release Visibility Projection

Role: 从 GUI 视角导航 chip/route/page/action 的发布可见性；可见不等于 Profile 支持或硬件 PASS。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h, source/apps/gui/chips/et6002/preview/et6002_gui_release_visibility.h, source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h, source/release/configs/customer_release.json
Relations: A060.010, A060.050.010
