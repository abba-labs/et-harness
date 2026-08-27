# [A060] Product Control And Validation Map

Role: 为 A010 产品能力实例提供 Profile 支持、运行时准入、安全门、测试、自动化证据、发布与交付的闭环视角。
Boundary: 不把“代码已实现”“Profile supported”“release visible”“hardware PASS”合并成同一状态；不复制具体实现代码链。
Resources: source/profiles/, source/workflow/, source/tests/, source/automation/, source/release/, source/apps/gui/release/
Relations: A010, A020, A030, A040, A050

## [A060.010] Profiles Capability And Route State

Role: 判断某个 Chip × Route × Operation 当前是否 supported/deferred/unsupported，以及 connection/capability 等产品事实。
Resources: source/profiles/chips/, source/profiles/kernel/, source/profiles/validation/
Relations: A010, A040, A050.020.020, A050.030.010

### [A060.010.010] Canonical Chip Profiles

Role: 每颗芯片 capabilities、connections、memory/route 与 evidence 等当前产品事实入口。
Resources: source/profiles/chips/
Relations: A010

#### [A060.010.010.010] ET3101 Profiles

Role: ET3101 当前产品能力、连接、内存与证据事实入口。
Resources: source/profiles/chips/et3101/chip.profile.yaml, source/profiles/chips/et3101/memory.yaml, source/profiles/chips/et3101/capabilities.yaml, source/profiles/chips/et3101/connections.yaml, source/profiles/chips/et3101/evidence.yaml
Relations: A010.010

#### [A060.010.010.020] ET6002 Profiles

Role: ET6002 当前产品能力、连接、内存与证据事实入口；CANFD unsupported 与 Probe deferred 状态必须从这里判定。
Resources: source/profiles/chips/et6002/chip.profile.yaml, source/profiles/chips/et6002/memory.yaml, source/profiles/chips/et6002/capabilities.yaml, source/profiles/chips/et6002/connections.yaml, source/profiles/chips/et6002/evidence.yaml
Relations: A010.020, A010.020.030, A010.020.040, A010.020.050

#### [A060.010.010.030] ET6003 Profiles

Role: ET6003 当前产品事实入口；各 ROM/Probe route 是否 supported/deferred/unsupported 必须以当前 Profile 为准。
Resources: source/profiles/chips/et6003/chip.profile.yaml, source/profiles/chips/et6003/memory.yaml, source/profiles/chips/et6003/capabilities.yaml, source/profiles/chips/et6003/connections.yaml, source/profiles/chips/et6003/evidence.yaml
Relations: A010.030, A010.030.030, A010.030.040, A010.030.050

### [A060.010.020] Capability Route Admission

Role: 以 capability × route 解析正式支持状态，并保持 deferred/unsupported 等 fail-closed 语义。
Resources: source/profiles/validation/profile_capability_resolver.h, source/profiles/kernel/profile_loader_engine.h
Relations: A010, A050.020.020, A050.030.010

## [A060.020] Operation Admission And Safety

Role: destructive operation、operator confirmation、project/factory/recovery precondition、geometry/range/alignment、hardware executor 等运行时准入视角。
Resources: source/workflow/, source/application/, source/profiles/
Relations: A010, A050.020.020, A050.030.010

### [A060.020.010] Safety Recovery And Destructive Gates

Role: 安全、恢复、破坏性操作与人工确认等 fail-closed 前置条件入口。
Resources: source/workflow/et3101/, source/workflow/et6002/, source/workflow/et6003/, source/application/et3101/, source/application/et6002/, source/application/et6003/
Relations: A010, A060.010

### [A060.020.020] Geometry Range And Executor Gates

Role: address/range/alignment/sector scope 与 allow_hardware/executor 等执行前约束入口。
Resources: source/workflow/et3101/, source/workflow/et6002/, source/workflow/et6003/, source/application/et3101/, source/application/et6002/, source/application/et6003/
Relations: A010, A050.020, A050.030

## [A060.030] Tests And Validation

Role: 证明代码边界、产品路径和硬件行为的测试入口；测试存在不自动等同所有硬件 capability PASS。
Resources: source/tests/
Relations: A010, A020.070, A030.090, A050

### [A060.030.010] Unit And Architecture Boundary Tests

Role: 单元、源码边界、CLI/GUI architecture guard、Profile admission 等结构与契约测试。
Resources: source/tests/unit/, source/tests/README.md
Relations: A020, A030, A050

#### [A060.030.010.010] Shared J-Link Contract Tests

Role: J-Link driver/session/platform adapter 与 Profile capability resolver 的共享单元契约验证入口。
Resources: source/tests/unit/probe/probe_jlink_swd_session_test.cpp, source/tests/unit/probe/probe_driver_platform_adapter_test.cpp, source/tests/unit/probe/probe_driver_factory_test.cpp, source/tests/unit/profiles/profiles_capability_resolver_test.cpp
Relations: A040.050, A050.030.030.020, A050.030.050.020

#### [A060.030.010.020] Shared CMSIS-DAP Contract Tests

Role: CMSIS-DAP session/driver/platform adapter 与 Profile capability resolver 的共享契约验证入口。
Resources: source/tests/unit/probe/probe_swd_session_skeleton_test.cpp, source/tests/unit/probe/probe_driver_platform_adapter_test.cpp, source/tests/unit/probe/probe_driver_factory_test.cpp, source/tests/unit/profiles/profiles_capability_resolver_test.cpp
Relations: A040.040, A050.030.030.010, A050.030.050.010

#### [A060.030.010.030] ET6003 GUI Architecture Boundary Tests

Role: ET6003 GUI 源码边界与产品入口结构验证；用于防止 GUI 绕开正式产品链路。
Resources: source/tests/unit/chips/et6003/apps/gui_et6003_preview_source_boundary_test.cpp
Relations: A030.030.030, A030.080.030

### [A060.030.020] No Hardware And Fake Runtime Tests

Role: fake session、no-hardware runtime、launch/smoke 等不依赖真实目标板的验证入口；当前测试实际分布在 unit/integration/mocks，而不是虚构的 no_hardware 目录。
Resources: source/tests/unit/, source/tests/integration/, source/tests/mocks/
Relations: A050.030, A060.010

### [A060.030.030] Hardware And Manual Validation

Role: 真实硬件/manual gate 与 route/capability 硬件验证入口；下级 Chip × Route 节点只给入口，不在 Architecture 中声明 PASS 结论。
Resources: source/tests/hardware/, source/automation/
Relations: A010, A060.010, A060.040

#### [A060.030.030.030] ET6003 J-Link Product Validation

Role: PR #8 发布的 ET6003 J-Link 精确验证兼容入口；正式 route 节点为 A060.030.030.300.050。
Resources: source/automation/scripts/chips/et6003/debug_probe/jlink/, source/scripts/et6003/gui/real_exe/run_et6003_jlink_full_suite.py, source/tests/hardware/et6003/
Relations: A010.030.050, A060.030.030.300.050, A060.040.010.030

#### [A060.030.030.100] ET3101 Route Validation

Role: ET3101 各 route 的测试/硬件证据入口；Probe route 当前没有与 ROM 同级的正式 automation 目录，不能由实现存在推导为自动化闭环。
Resources: source/tests/hardware/et3101/, source/automation/scripts/chips/et3101/
Relations: A010.010, A060.040.010.100

##### [A060.030.030.100.010] ET3101 UART Validation

Role: ET3101 UART formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et3101/uart_rom/, source/tests/hardware/et3101/
Relations: A010.010.010, A050.020.100.010, A060.040.010.100.010

##### [A060.030.030.100.020] ET3101 Classic CAN Validation

Role: ET3101 Classic CAN formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et3101/can_rom/, source/tests/hardware/et3101/
Relations: A010.010.020, A050.020.100.020, A060.040.010.100.020

##### [A060.030.030.100.030] ET3101 CANFD Validation

Role: ET3101 CANFD formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et3101/canfd_rom/, source/tests/hardware/et3101/
Relations: A010.010.030, A050.020.100.030, A060.040.010.100.030

##### [A060.030.030.100.040] ET3101 CMSIS-DAP Validation

Role: ET3101 CMSIS-DAP 当前测试/硬件记录入口；没有 `automation/scripts/chips/et3101/debug_probe/dap`，因此不声称 formal automation 闭环。
Resources: source/tests/hardware/et3101/, source/tests/unit/probe/
Relations: A010.010.040, A050.030.020.010.010, A060.030.010.020

##### [A060.030.030.100.050] ET3101 J-Link Validation

Role: ET3101 J-Link 当前测试/硬件记录入口；没有 `automation/scripts/chips/et3101/debug_probe/jlink`，因此不声称 formal automation 闭环。
Resources: source/tests/hardware/et3101/, source/tests/unit/probe/
Relations: A010.010.050, A050.030.020.010.020, A060.030.010.010

#### [A060.030.030.200] ET6002 Route Validation

Role: ET6002 UART/CAN/DAP/J-Link 的测试与产品 automation 入口，同时保留 CANFD unsupported/fail-closed 边界。
Resources: source/tests/hardware/et6002/, source/automation/scripts/chips/et6002/
Relations: A010.020, A060.040.010.200

##### [A060.030.030.200.010] ET6002 UART Validation

Role: ET6002 UART formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et6002/uart_rom/, source/tests/hardware/et6002/
Relations: A010.020.010, A050.020.200.010, A060.040.010.200.010

##### [A060.030.030.200.020] ET6002 Classic CAN Validation

Role: ET6002 Classic CAN formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et6002/can_rom/, source/tests/hardware/et6002/
Relations: A010.020.020, A050.020.200.020, A060.040.010.200.020

##### [A060.030.030.200.030] ET6002 CANFD Unsupported Validation Boundary

Role: ET6002 CANFD 当前没有正式 route implementation/automation；验证任务首先检查 Profile fail-closed 状态，Classic CAN evidence 不得继承。
Resources: source/profiles/chips/et6002/capabilities.yaml, source/profiles/chips/et6002/connections.yaml, source/profiles/chips/et6002/evidence.yaml
Relations: A010.020.030, A060.010.010.020

##### [A060.030.030.200.040] ET6002 CMSIS-DAP Validation

Role: ET6002 DAP formal debug-probe automation 与 hardware record 入口；产品支持仍以 Profile admission 为准。
Resources: source/automation/scripts/chips/et6002/debug_probe/dap/, source/automation/scripts/chips/et6002/dap/, source/tests/hardware/et6002/
Relations: A010.020.040, A050.030.020.020.010, A060.040.010.200.040

##### [A060.030.030.200.050] ET6002 J-Link Validation

Role: ET6002 J-Link formal debug-probe automation 与 hardware record 入口；产品支持仍以 Profile admission 为准。
Resources: source/automation/scripts/chips/et6002/debug_probe/jlink/, source/tests/hardware/et6002/
Relations: A010.020.050, A050.030.020.020.020, A060.040.010.200.050

#### [A060.030.030.300] ET6003 Route Validation

Role: ET6003 UART/CAN/CANFD/DAP/J-Link 的正式 automation、GUI real-exe 与 hardware record 总入口。
Resources: source/tests/hardware/et6003/, source/automation/scripts/chips/et6003/, source/scripts/et6003/gui/real_exe/
Relations: A010.030, A060.040.010.300

##### [A060.030.030.300.010] ET6003 UART Validation

Role: ET6003 UART formal automation 与 hardware record 入口。
Resources: source/automation/scripts/chips/et6003/uart_rom/, source/tests/hardware/et6003/
Relations: A010.030.010, A050.020.300.010, A060.040.010.300.010

##### [A060.030.030.300.020] ET6003 Classic CAN Validation

Role: ET6003 Classic CAN formal automation、GUI real-exe 与 hardware record 入口。
Resources: source/automation/scripts/chips/et6003/can_rom/, source/scripts/et6003/gui/real_exe/run_et6003_can_full_suite.py, source/tests/hardware/et6003/
Relations: A010.030.020, A050.020.300.020, A060.040.010.300.020

##### [A060.030.030.300.030] ET6003 CANFD Validation

Role: ET6003 CANFD formal automation、GUI real-exe 与 hardware record 入口；与 Classic CAN 的共享实现和 route-specific evidence 必须分开理解。
Resources: source/automation/scripts/chips/et6003/canfd_rom/, source/scripts/et6003/gui/real_exe/run_et6003_fdcan_full_suite.py, source/tests/hardware/et6003/
Relations: A010.030.030, A050.020.300.020, A050.020.300.030, A060.040.010.300.030

##### [A060.030.030.300.040] ET6003 CMSIS-DAP Validation

Role: ET6003 DAP formal debug-probe automation 与 hardware record 入口；产品支持仍以 Profile admission 为准。
Resources: source/automation/scripts/chips/et6003/debug_probe/dap/, source/tests/hardware/et6003/
Relations: A010.030.040, A050.030.020.030.010, A060.040.010.300.040

##### [A060.030.030.300.050] ET6003 J-Link Validation

Role: ET6003 J-Link formal debug-probe automation、GUI real-exe 与 hardware record 入口；不在 Architecture 中声明 hardware PASS。
Resources: source/automation/scripts/chips/et6003/debug_probe/jlink/, source/scripts/et6003/gui/real_exe/run_et6003_jlink_full_suite.py, source/tests/hardware/et6003/
Relations: A010.030.050, A050.030.020.030.020, A060.040.010.300.050

## [A060.040] Automation Evidence And Hardware Records

Role: 通过正式 et-cli 执行产品自动化、收集 raw artifact/hardware record，并区分 candidate evidence 与 product evidence。
Resources: source/automation/, source/tests/
Relations: A010, A020.070, A060.030, A060.050

### [A060.040.010] Product Automation

Role: 正式产品自动化入口；产品 PASS 路径应调用正式 et-cli，而不是直接绕过产品边界访问硬件。
Resources: source/automation/README.md, source/automation/scripts/
Relations: A020, A010

#### [A060.040.010.030] ET6003 J-Link Product Automation

Role: PR #8 发布的 ET6003 J-Link automation 兼容入口；全项目精确入口为 A060.040.010.300.050。
Resources: source/automation/scripts/chips/et6003/debug_probe/jlink/run_et6003_debug_probe_jlink_all.py, source/automation/scripts/chips/et6003/debug_probe/jlink/run_et6003_debug_probe_pflash_ab_stress.py, source/automation/scripts/chips/et6003/debug_probe/run_et6003_debug_probe_pflash_hw_program.py
Relations: A010.030.050, A060.040.010.300.050, A060.030.030.030

#### [A060.040.010.100] ET3101 Product Automation

Role: ET3101 当前 formal automation 只覆盖 UART/CAN/CANFD ROM；Probe 未发现同级正式 automation 目录。
Resources: source/automation/scripts/chips/et3101/
Relations: A010.010

##### [A060.040.010.100.010] ET3101 UART Automation

Role: ET3101 UART 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et3101/uart_rom/
Relations: A010.010.010, A060.030.030.100.010

##### [A060.040.010.100.020] ET3101 Classic CAN Automation

Role: ET3101 Classic CAN 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et3101/can_rom/
Relations: A010.010.020, A060.030.030.100.020

##### [A060.040.010.100.030] ET3101 CANFD Automation

Role: ET3101 CANFD 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et3101/canfd_rom/
Relations: A010.010.030, A060.030.030.100.030

#### [A060.040.010.200] ET6002 Product Automation

Role: ET6002 UART/CAN 与 Probe automation 总入口；CANFD 当前没有 automation route。
Resources: source/automation/scripts/chips/et6002/
Relations: A010.020

##### [A060.040.010.200.010] ET6002 UART Automation

Role: ET6002 UART 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et6002/uart_rom/
Relations: A010.020.010, A060.030.030.200.010

##### [A060.040.010.200.020] ET6002 Classic CAN Automation

Role: ET6002 Classic CAN 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et6002/can_rom/
Relations: A010.020.020, A060.030.030.200.020

##### [A060.040.010.200.040] ET6002 CMSIS-DAP Automation

Role: ET6002 CMSIS-DAP 正式 debug-probe automation 入口。
Resources: source/automation/scripts/chips/et6002/debug_probe/dap/, source/automation/scripts/chips/et6002/dap/
Relations: A010.020.040, A060.030.030.200.040

##### [A060.040.010.200.050] ET6002 J-Link Automation

Role: ET6002 J-Link 正式 debug-probe automation 入口。
Resources: source/automation/scripts/chips/et6002/debug_probe/jlink/
Relations: A010.020.050, A060.030.030.200.050

#### [A060.040.010.300] ET6003 Product Automation

Role: ET6003 UART/CAN/CANFD/DAP/J-Link formal et-cli automation 总入口。
Resources: source/automation/scripts/chips/et6003/
Relations: A010.030

##### [A060.040.010.300.010] ET6003 UART Automation

Role: ET6003 UART 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et6003/uart_rom/
Relations: A010.030.010, A060.030.030.300.010

##### [A060.040.010.300.020] ET6003 Classic CAN Automation

Role: ET6003 Classic CAN 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et6003/can_rom/
Relations: A010.030.020, A060.030.030.300.020

##### [A060.040.010.300.030] ET6003 CANFD Automation

Role: ET6003 CANFD 正式 et-cli automation 入口。
Resources: source/automation/scripts/chips/et6003/canfd_rom/
Relations: A010.030.030, A060.030.030.300.030

##### [A060.040.010.300.040] ET6003 CMSIS-DAP Automation

Role: ET6003 CMSIS-DAP 正式 debug-probe automation 入口。
Resources: source/automation/scripts/chips/et6003/debug_probe/dap/
Relations: A010.030.040, A060.030.030.300.040

##### [A060.040.010.300.050] ET6003 J-Link Automation

Role: ET6003 J-Link 正式 debug-probe automation 入口。
Resources: source/automation/scripts/chips/et6003/debug_probe/jlink/
Relations: A010.030.050, A060.030.030.300.050, A060.040.010.030

### [A060.040.020] Evidence And Hardware Record Chain

Role: 将 operation postcondition、raw artifact、hardware record 与产品证据关联起来。
Resources: source/automation/, source/tests/hardware/
Relations: A060.030, A060.050

## [A060.050] Release Visibility And Delivery

Role: 判断能力是否进入正式客户 surface、构建/测试/package plan 与交付链；release visible 不代表 Profile admitted 或 hardware PASS。
Resources: source/release/, source/apps/gui/release/, source/apps/gui/chips/
Relations: A010, A030.100, A060.010, A060.030, A060.040

### [A060.050.010] GUI And Customer Release Visibility

Role: chip/route/page/action 在正式客户 release 中的显示/隐藏入口。
Resources: source/release/configs/customer_release.json, source/apps/gui/release/
Relations: A030.100, A010, A060.010

#### [A060.050.010.010] ET3101 Release Visibility

Role: ET3101 GUI route/action 与客户 release 配置的真实可见性入口。
Resources: source/apps/gui/chips/et3101/preview/et3101_gui_release_visibility.h, source/release/configs/customer_release.json
Relations: A010.010, A030.100, A060.010.010.010

#### [A060.050.010.020] ET6002 Release Visibility

Role: ET6002 GUI route/action 与客户 release 配置的真实可见性入口。
Resources: source/apps/gui/chips/et6002/preview/et6002_gui_release_visibility.h, source/release/configs/customer_release.json
Relations: A010.020, A030.100, A060.010.010.020

#### [A060.050.010.030] ET6003 Release Visibility

Role: ET6003 GUI route/action 与客户 release 配置的真实可见性入口；可见不代表 Profile admitted 或 hardware PASS。
Resources: source/apps/gui/chips/et6003/preview/et6003_gui_release_visibility.h, source/release/configs/customer_release.json
Relations: A010.030, A030.100, A030.080.030, A060.010.010.030

### [A060.050.020] Build Test Package And Delivery Pipeline

Role: release config discovery、plan、build、CTest/runtime checks、package、hash、launch smoke 与正式交付入口。
Resources: source/release/README.md, source/release/scripts/
Relations: A060.030, A060.040, A060.050.010
