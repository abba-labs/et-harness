# [A050] Implementation Map

Role: 从 A010 产品能力实例向真实实现层下钻，回答“这个能力由哪些代码层共同实现、哪些是共享基础设施、哪些是 chip-local 实现”。
Boundary: 不作为用户业务需求的首要入口，不承载 Profile 支持状态、测试证据或发布结论；这些由 A060 管理。
Resources: source/domain/, source/application/, source/workflow/, source/backend/, source/protocol/, source/transport/, source/probe/, source/platform/, source/extension/, source/plugins/, source/apps/cli/
Relations: A010, A020, A030, A040, A060

## [A050.010] Shared Semantic Core

Role: 跨芯片/路线复用的低依赖语义基座。
Resources: source/domain/
Relations: A010, A050.020, A050.030

### [A050.010.010] Domain Models Result And Capability Vocabulary

Role: Result/Error、identity、operation model、capability metadata、vocabulary 等共享语义。
Resources: source/domain/
Relations: A050.020.010, A050.030.010

## [A050.020] ROM Execution Stack

Role: UART/CAN/CANFD BootROM 类产品能力的实现下钻主链；下级 Chip × Route 节点是 Agent 进入真实 ROM 实现的精确入口。
Relations: A010, A040.010, A040.020, A040.030

### [A050.020.010] ROM Application Contracts

Role: ROM 路线 typed request/result、backend interface、session/job/progress 等产品操作契约。
Resources: source/application/
Relations: A050.010, A050.020.020

### [A050.020.020] ROM Workflow Orchestration

Role: ROM 路线 request validation、capability/route admission、safety/recovery/geometry 检查与用例编排。
Resources: source/workflow/
Relations: A050.020.010, A050.020.030, A060.010, A060.020

### [A050.020.030] ROM Backend Execution

Role: 将产品操作接口落实为芯片 BootROM 命令序列或共享 ROM 执行流程。
Resources: source/backend/
Relations: A050.020.020, A050.020.040, A050.020.050

### [A050.020.040] ROM Protocol And Codec

Role: command、frame、checksum、ACK/NACK、字段编码与响应解析等协议语义。
Boundary: 不负责打开 UART/CAN 物理设备。
Resources: source/protocol/chips/et3101/et3101_openbl_protocol.h, source/protocol/chips/et3101/et3101_can_family_packet_codec.h, source/protocol/chips/et6002/et6002_openbl_protocol.h, source/protocol/chips/et6002/et6002_can_packet_codec.h, source/protocol/chips/et6003/et6003_openbl_protocol.h, source/protocol/chips/et6003/et6003_can_family_packet_codec.h
Relations: A050.020.030, A050.020.050

### [A050.020.050] ROM Transport And Host IO

Role: UART、CAN family 的字节/帧传输抽象与 concrete host driver。
Boundary: 不负责芯片 BootROM 产品操作语义。
Resources: source/transport/serial/uart_serial_transport.h, source/transport/serial/os_uart_serial_driver.h, source/transport/can/can_family_transport.h, source/transport/can/zlg_classic_can_driver.h, source/transport/can/zlg_canfd_driver.h
Relations: A050.020.030, A050.020.040, A050.040

#### [A050.020.050.010] UART Host Transport

Role: 三颗芯片 UART ROM 路线共享的 host serial transport 与 OS UART driver。
Resources: source/transport/serial/uart_serial_transport.h, source/transport/serial/os_uart_serial_driver.h
Relations: A040.010

#### [A050.020.050.020] CAN Family Host Transport

Role: Classic CAN/CANFD 共享 frame transport，按 route 选择 ZLG Classic CAN 或 CANFD concrete driver。
Resources: source/transport/can/can_family_transport.h, source/transport/can/zlg_classic_can_driver.h, source/transport/can/zlg_canfd_driver.h
Relations: A040.020, A040.030

### [A050.020.100] ET3101 ROM Implementation

Role: ET3101 UART/CAN/CANFD 的 chip-local ROM 实现入口；ET3101 使用 dedicated route CLI modules 与 adapters/runners，不强行套用 ET6002/ET6003 的实现形态。
Resources: source/apps/cli/chips/et3101/et3101_cli_module.cpp
Relations: A010.010.010, A010.010.020, A010.010.030, A020.020.010, A020.030.010, A020.040.010

#### [A050.020.100.010] ET3101 UART ROM Implementation

Role: ET3101 UART identify/read/write/program/verify/security/control 的首读实现集合。
Resources: source/apps/cli/chips/et3101/et3101_uart_cli_module.cpp, source/apps/cli/chips/et3101/et3101_uart_backend_adapters.h, source/apps/cli/chips/et3101/et3101_uart_memory_runner.h, source/apps/cli/chips/et3101/et3101_uart_program_runner.h, source/apps/cli/chips/et3101/et3101_uart_security_runner.h, source/protocol/chips/et3101/et3101_openbl_protocol.h, source/transport/serial/uart_serial_transport.h
Relations: A010.010.010, A020.020.010, A040.010, A050.020.050.010

#### [A050.020.100.020] ET3101 Classic CAN ROM Implementation

Role: ET3101 Classic CAN identify/read/write/program/verify/security/control 的首读实现集合。
Resources: source/apps/cli/chips/et3101/et3101_can_cli_module.cpp, source/apps/cli/chips/et3101/et3101_can_backend_adapters.h, source/apps/cli/chips/et3101/et3101_can_memory_runner.h, source/apps/cli/chips/et3101/et3101_can_program_runner.h, source/apps/cli/chips/et3101/et3101_can_security_runner.h, source/protocol/chips/et3101/et3101_can_family_packet_codec.h, source/transport/can/can_family_transport.h, source/transport/can/zlg_classic_can_driver.h
Relations: A010.010.020, A020.030.010, A040.020, A050.020.050.020

#### [A050.020.100.030] ET3101 CANFD ROM Implementation

Role: ET3101 CANFD route-local CLI/runners 复用 ET3101 CAN family codec 与 CAN family transport，并选择 CANFD concrete driver。
Resources: source/apps/cli/chips/et3101/et3101_canfd_cli_module.cpp, source/apps/cli/chips/et3101/et3101_canfd_memory_runner.h, source/apps/cli/chips/et3101/et3101_canfd_program_runner.h, source/apps/cli/chips/et3101/et3101_canfd_security_runner.h, source/protocol/chips/et3101/et3101_can_family_packet_codec.h, source/transport/can/can_family_transport.h, source/transport/can/zlg_canfd_driver.h
Relations: A010.010.030, A020.040.010, A040.030, A050.020.050.020

### [A050.020.200] ET6002 ROM Implementation

Role: ET6002 UART/Classic CAN 的统一 CLI + chip backend 实现入口；ET6002 CANFD 当前没有实现节点，保持 A010/A060 fail-closed 边界。
Resources: source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6002/et6002_cli_dispatch.h
Relations: A010.020.010, A010.020.020, A020.020.020, A020.030.020

#### [A050.020.200.010] ET6002 UART ROM Implementation

Role: ET6002 UART memory/readonly/option/security 主链，底层复用 ET6002 OpenBL protocol 与共享 UART transport。
Resources: source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6002/et6002_uart_memory_cli_runner.h, source/apps/cli/chips/et6002/et6002_uart_readonly_cli_runner.h, source/backend/chips/et6002/et6002_uart_memory_backend.h, source/backend/chips/et6002/et6002_uart_readonly_backend.h, source/backend/chips/et6002/et6002_uart_option_backend.h, source/backend/chips/et6002/et6002_uart_security_backend.h, source/protocol/chips/et6002/et6002_openbl_protocol.h, source/transport/serial/uart_serial_transport.h
Relations: A010.020.010, A020.020.020, A040.010, A050.020.050.010

#### [A050.020.200.020] ET6002 Classic CAN ROM Implementation

Role: ET6002 Classic CAN memory/readonly/option/security 主链，使用 ET6002 CAN packet codec 与 Classic CAN driver。
Resources: source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6002/et6002_can_memory_cli_runner.h, source/apps/cli/chips/et6002/et6002_can_readonly_cli_runner.h, source/backend/chips/et6002/et6002_can_memory_backend.h, source/backend/chips/et6002/et6002_can_readonly_backend.h, source/backend/chips/et6002/et6002_can_option_backend.h, source/backend/chips/et6002/et6002_can_security_backend.h, source/protocol/chips/et6002/et6002_can_packet_codec.h, source/transport/can/can_family_transport.h, source/transport/can/zlg_classic_can_driver.h
Relations: A010.020.020, A020.030.020, A040.020, A050.020.050.020

### [A050.020.300] ET6003 ROM Implementation

Role: ET6003 UART/CAN/CANFD 的统一 CLI 实现入口；Classic CAN 与 CANFD 共享 CAN-family runners/backend/codec，route-specific identify/admission/driver 保持分叉。
Resources: source/apps/cli/chips/et6003/et6003_cli_module.cpp, source/apps/cli/chips/et6003/et6003_cli_dispatch.h
Relations: A010.030.010, A010.030.020, A010.030.030, A020.020.030, A020.030.030, A020.040.030

#### [A050.020.300.010] ET6003 UART ROM Implementation

Role: ET6003 UART 产品操作主链；从统一 CLI 的 UART runners 下钻到 ET6003 OpenBL protocol 与共享 serial transport。
Resources: source/apps/cli/chips/et6003/et6003_cli_module.cpp, source/apps/cli/chips/et6003/et6003_uart_memory_runner.h, source/protocol/chips/et6003/et6003_openbl_protocol.h, source/transport/serial/uart_serial_transport.h, source/transport/serial/os_uart_serial_driver.h
Relations: A010.030.010, A020.020.030, A040.010, A050.020.050.010

#### [A050.020.300.020] ET6003 CAN Family Shared Implementation

Role: ET6003 Classic CAN 与 CANFD 共享 memory/PFlash/readonly/verify/security/speed runners、CAN-family backend 与 packet codec；不要把两条 route 误读成两份独立实现。
Resources: source/apps/cli/chips/et6003/et6003_can_memory_runner.h, source/apps/cli/chips/et6003/et6003_can_pflash_runner.h, source/apps/cli/chips/et6003/et6003_can_readonly_runner.h, source/apps/cli/chips/et6003/et6003_can_verify_runner.h, source/apps/cli/chips/et6003/et6003_can_security_runner.h, source/backend/chips/et6003/et6003_can_family_rom_backend.h, source/protocol/chips/et6003/et6003_can_family_packet_codec.h, source/transport/can/can_family_transport.h
Relations: A010.030.020, A010.030.030, A020.030.030, A020.040.030, A040.020, A040.030, A050.020.050.020

#### [A050.020.300.030] ET6003 CANFD Route Specific Implementation

Role: ET6003 CANFD 的 route-specific identify/profile admission 与 CANFD host driver；其 memory/program/verify/security 主体继续复用 A050.020.300.020。
Resources: source/apps/cli/chips/et6003/et6003_canfd_identify_runner.h, source/apps/cli/chips/et6003/et6003_canfd_profile_admission.h, source/transport/can/zlg_canfd_driver.h, source/automation/scripts/chips/et6003/canfd_rom/
Relations: A010.030.030, A020.040.030, A040.030, A050.020.300.020, A060.040

## [A050.030] Debug Probe Execution Stack

Role: CMSIS-DAP/J-Link SWD 类产品能力的实现下钻主链。
Relations: A010, A040.040, A040.050

### [A050.030.010] Probe Application And Workflow Contracts

Role: Probe 路线 typed request/result、HardwareExecutor contract、workflow admission 与操作编排。
Resources: source/application/et3101/, source/application/et6002/, source/application/et6003/, source/workflow/et3101/, source/workflow/et6002/, source/workflow/et6003/
Relations: A050.010, A050.030.020, A060.010, A060.020

### [A050.030.020] Chip Local Hardware Executor

Role: chip-local CLI 侧将 Workflow 连接到 concrete Probe Session/Algorithm 的硬件执行边界。
Resources: source/apps/cli/chips/
Relations: A020.050, A020.060, A050.030.030, A050.030.040

#### [A050.030.020.010] ET3101 Probe Hardware Executors

Role: ET3101 Probe CLI 组合入口；下级分别精确导航 CMSIS-DAP 与 J-Link executor。
Resources: source/apps/cli/chips/et3101/et3101_debug_probe_cli_module.cpp
Relations: A010.010.040, A010.010.050, A020.050.010, A020.060.010

##### [A050.030.020.010.010] ET3101 CMSIS-DAP Executors

Role: ET3101 CMSIS-DAP read/PFlash/Option/WRP/control 的 chip-local executor 集合。
Resources: source/apps/cli/chips/et3101/et3101_debug_probe_cmsis_dap_read_mem_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_cmsis_dap_pflash_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_cmsis_dap_option_go_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_cmsis_dap_wrp_hw_executor.h
Relations: A010.010.040, A020.050.010, A050.030.030.010, A050.030.040.010

##### [A050.030.020.010.020] ET3101 J-Link Executors

Role: ET3101 J-Link session/read/PFlash/Option/WRP/control 的 chip-local executor 集合。
Resources: source/apps/cli/chips/et3101/et3101_debug_probe_jlink_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_jlink_read_mem_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_jlink_pflash_erase_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_jlink_option_go_hw_executor.h, source/apps/cli/chips/et3101/et3101_debug_probe_jlink_wrp_hw_executor.h
Relations: A010.010.050, A020.060.010, A050.030.030.020, A050.030.040.010

#### [A050.030.020.020] ET6002 Probe Hardware Executors

Role: ET6002 Probe CLI 组合入口；下级分别导航 CMSIS-DAP 与 J-Link concrete executor/algorithm 边界。
Resources: source/apps/cli/chips/et6002/et6002_debug_probe_cli_module.cpp
Relations: A010.020.040, A010.020.050, A020.050.020, A020.060.020

##### [A050.030.020.020.010] ET6002 CMSIS-DAP Executors

Role: ET6002 CMSIS-DAP PFlash/Option/WRP/readonly/control 的 chip-local executor 集合。
Resources: source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_pflash_hw_executor.h, source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_option_user_hw_executor.h, source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_wrp_hw_executor.h, source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_readonly_hw_executor.h, source/apps/cli/chips/et6002/et6002_debug_probe_cmsis_dap_go_run_hw_executor.h
Relations: A010.020.040, A020.050.020, A050.030.030.010, A050.030.040.020

##### [A050.030.020.020.020] ET6002 J-Link Executors

Role: ET6002 J-Link 的 CLI/session 入口与 chip-specific J-Link hardware algorithm executor；正式产品 admission 仍由 A060 判断。
Resources: source/apps/cli/chips/et6002/et6002_debug_probe_jlink_readonly_hw_executor.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_pflash_hw_executor.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_option_user_hw_executor.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_wrp_hw_executor.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_go_run_hw_executor.h
Relations: A010.020.050, A020.060.020, A050.030.030.020, A050.030.040.020

#### [A050.030.020.030] ET6003 Probe Hardware Executors

Role: ET6003 Probe CLI 组合入口；下级分别精确导航 CMSIS-DAP 与 J-Link executor。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp
Relations: A010.030.040, A010.030.050, A020.050.030, A020.060.030

##### [A050.030.020.030.010] ET6003 CMSIS-DAP Executors

Role: ET6003 CMSIS-DAP readonly/read/PFlash/Option/control 的 chip-local executor 集合。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_read_mem_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_pflash_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_option_go_hw_executor.h
Relations: A010.030.040, A020.050.030, A050.030.030.010, A050.030.040.030

##### [A050.030.020.030.020] ET6003 J-Link Executors

Role: ET6003 J-Link session/read/PFlash/Option/control 的 chip-local executor 集合。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_read_mem_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_option_go_hw_executor.h
Relations: A010.030.050, A020.060.030, A050.030.030.020, A050.030.040.030

### [A050.030.030] Probe Driver And Session

Role: IProbeDriver/IProbeSession、CMSIS-DAP/J-Link driver/session 等 Probe 访问基础设施。
Resources: source/probe/kernel/, source/probe/drivers/
Relations: A050.030.020, A050.030.040, A050.030.050

#### [A050.030.030.010] CMSIS-DAP Driver And Session

Role: CMSIS-DAP SWD 的共享 packet IO、driver、session、platform adapter 与 factory 实现入口。
Resources: source/probe/drivers/cmsis_dap/cmsis_dap_probe_driver.h, source/probe/drivers/cmsis_dap/cmsis_dap_swd_session.h, source/probe/drivers/cmsis_dap/cmsis_dap_platform_adapter.h, source/probe/drivers/cmsis_dap/cmsis_dap_probe_driver_factory.h, source/probe/drivers/cmsis_dap/cmsis_dap_hid_packet_io_factory.h
Relations: A040.040, A050.030.050.010

#### [A050.030.030.020] J-Link Driver And Session

Role: J-Link SWD 的共享 driver、session、platform adapter 与 factory 实现入口；不包含芯片特定 PFlash/NVR 算法。
Resources: source/probe/drivers/jlink/jlink_probe_driver.h, source/probe/drivers/jlink/jlink_swd_session.h, source/probe/drivers/jlink/jlink_platform_adapter.h, source/probe/drivers/jlink/jlink_probe_driver_factory.h
Relations: A040.050, A050.030.050.020

### [A050.030.040] Chip Probe Algorithm

Role: 芯片 PFlash/NVR/Option/WRP/control 等 probe-side 算法与 chip-local target 行为；这些算法可被 DAP/J-Link 两类 driver/session 复用。
Resources: source/probe/algorithms/chips/
Relations: A050.030.020, A050.030.030

#### [A050.030.040.010] ET3101 Probe Algorithms

Role: ET3101 PFlash/FLM/EFC、Option 与 readiness 等 chip-specific Probe 算法。
Resources: source/probe/algorithms/chips/et3101/et3101_debug_probe_pflash_algorithm.h, source/probe/algorithms/chips/et3101/et3101_debug_probe_pflash_flm_executor.h, source/probe/algorithms/chips/et3101/et3101_debug_probe_pflash_efc_executor.h, source/probe/algorithms/chips/et3101/et3101_debug_probe_option_user_algorithm.h, source/probe/algorithms/chips/et3101/et3101_debug_probe_readiness_algorithm.h
Relations: A010.010.040, A010.010.050

#### [A050.030.040.020] ET6002 Probe Algorithms

Role: ET6002 PFlash/Option/go-run 与 J-Link-specific executor 等 chip-specific Probe 算法。
Resources: source/probe/algorithms/chips/et6002/et6002_debug_probe_pflash_algorithm.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_option_user_algorithm.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_go_run_algorithm.h, source/probe/algorithms/chips/et6002/et6002_debug_probe_jlink_pflash_hw_executor.h
Relations: A010.020.040, A010.020.050

#### [A050.030.040.030] ET6003 Probe Algorithms

Role: ET6003 Probe 路线的 PFlash、FLM、Option/NVR 与 readiness 芯片算法入口。
Resources: source/probe/algorithms/chips/et6003/et6003_debug_probe_pflash_algorithm.h, source/probe/algorithms/chips/et6003/et6003_debug_probe_pflash_flm_executor.h, source/probe/algorithms/chips/et6003/et6003_debug_probe_option_user_algorithm.h, source/probe/algorithms/chips/et6003/et6003_debug_probe_readiness_algorithm.h
Relations: A010.030.040, A010.030.050

### [A050.030.050] Probe Platform Vendor Runtime

Role: CMSIS-DAP HID、J-Link DLL 等 OS/vendor runtime 适配。
Resources: source/platform/vendor/cmsis_dap/, source/platform/vendor/jlink/
Relations: A050.030.030

#### [A050.030.050.010] CMSIS-DAP Vendor Runtime

Role: CMSIS-DAP HID/vendor runtime 入口。
Resources: source/platform/vendor/cmsis_dap/cmsis_dap_hid_runtime.h
Relations: A040.040, A050.030.030.010

#### [A050.030.050.020] J-Link Vendor Runtime

Role: J-Link DLL API、内部 runtime bundle discovery 与 vendor runtime 入口。
Resources: source/platform/vendor/jlink/jlink_runtime.h, source/platform/vendor/jlink/jlink_dll_api.h, source/platform/vendor/jlink/bundle/
Relations: A040.050, A050.030.030.020

## [A050.040] Composition And Extension Infrastructure

Role: 将共享实现与 chip-local 能力装配成实际产品路径，并提供扩展注册基础设施。
Resources: source/apps/cli/chips/, source/extension/, source/plugins/
Relations: A020.080, A050.020, A050.030

### [A050.040.010] CLI Composition Root

Role: chip-local CLI 创建/组合 concrete driver、backend、executor、workflow 与 request。
Resources: source/apps/cli/chips/et3101/et3101_cli_module.cpp, source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6003/et6003_cli_module.cpp
Relations: A020.080, A050.020, A050.030

### [A050.040.020] Extension Registry And Plugins

Role: command/backend/protocol/transport/probe/profile 等可扩展注册与插件基础设施。
Resources: source/extension/registry/extension_registry.h, source/extension/builtin/register_builtins.cpp, source/plugins/CMakeLists.txt
Relations: A050.010, A050.020, A050.030
