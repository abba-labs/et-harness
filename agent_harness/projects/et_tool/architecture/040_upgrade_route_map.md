# [A040] Route Projection Map

Role: 从升级/调试路线维度反向投影 A010 canonical 能力实例，回答“某条 UART/CAN/CANFD/DAP/J-Link 路线覆盖哪些芯片实例、共享哪些基础设施”。
Boundary: 不复制具体芯片能力定义，不把 route visible、Profile supported、implemented、hardware PASS 混为同一状态。
Resources: source/transport/, source/probe/drivers/, source/platform/vendor/, source/profiles/chips/
Relations: A010, A020, A030, A050, A060

## [A040.010] UART ROM Route

Role: UART BootROM 路线视角；三颗芯片共享 UART host transport，但使用各自 OpenBL protocol 与 chip-local implementation。
Resources: source/transport/serial/uart_serial_transport.h, source/transport/serial/os_uart_serial_driver.h, source/protocol/chips/et3101/et3101_openbl_protocol.h, source/protocol/chips/et6002/et6002_openbl_protocol.h, source/protocol/chips/et6003/et6003_openbl_protocol.h
Relations: A010.010.010, A010.020.010, A010.030.010, A020.020, A030.040, A050.020.050.010

### [A040.010.010] ET3101 UART Projection

Role: UART 视角下的 ET3101 UART canonical 能力与精确实现/验证入口。
Relations: A010.010.010, A020.020.010, A030.040.010, A050.020.100.010, A060.030.030.100.010

### [A040.010.020] ET6002 UART Projection

Role: UART 视角下的 ET6002 UART canonical 能力与精确实现/验证入口。
Relations: A010.020.010, A020.020.020, A030.040.020, A050.020.200.010, A060.030.030.200.010

### [A040.010.030] ET6003 UART Projection

Role: UART 视角下的 ET6003 UART canonical 能力与精确实现/验证入口。
Relations: A010.030.010, A020.020.030, A030.040.030, A050.020.300.010, A060.030.030.300.010

## [A040.020] Classic CAN ROM Route

Role: Classic CAN BootROM 路线视角；共享 CAN family transport，按芯片选择 packet codec/backend，并使用 Classic CAN concrete driver。
Resources: source/transport/can/can_family_transport.h, source/transport/can/zlg_classic_can_driver.h, source/protocol/chips/et3101/et3101_can_family_packet_codec.h, source/protocol/chips/et6002/et6002_can_packet_codec.h, source/protocol/chips/et6003/et6003_can_family_packet_codec.h
Relations: A010.010.020, A010.020.020, A010.030.020, A020.030, A030.050, A050.020.050.020

### [A040.020.010] ET3101 CAN Projection

Role: Classic CAN 视角下的 ET3101 CAN canonical 能力与精确实现/验证入口。
Relations: A010.010.020, A020.030.010, A030.050.010, A050.020.100.020, A060.030.030.100.020

### [A040.020.020] ET6002 CAN Projection

Role: Classic CAN 视角下的 ET6002 CAN canonical 能力与精确实现/验证入口。
Relations: A010.020.020, A020.030.020, A030.050.020, A050.020.200.020, A060.030.030.200.020

### [A040.020.030] ET6003 CAN Projection

Role: Classic CAN 视角下的 ET6003 CAN canonical 能力；其实现与 CANFD 共享 CAN-family 主干。
Relations: A010.030.020, A020.030.030, A030.050.030, A050.020.300.020, A060.030.030.300.020

## [A040.030] CANFD ROM Route

Role: CAN FD BootROM 路线视角；ET3101/ET6003 使用 CAN family transport + CANFD driver，ET6002 保持 unsupported/fail-closed。
Resources: source/transport/can/can_family_transport.h, source/transport/can/zlg_canfd_driver.h, source/protocol/chips/et3101/et3101_can_family_packet_codec.h, source/protocol/chips/et6003/et6003_can_family_packet_codec.h, source/profiles/chips/et6002/capabilities.yaml
Relations: A010.010.030, A010.020.030, A010.030.030, A020.040, A030.060, A050.020.050.020, A060.010

### [A040.030.010] ET3101 CANFD Projection

Role: CANFD 视角下的 ET3101 CANFD canonical 能力与精确实现/验证入口。
Relations: A010.010.030, A020.040.010, A030.060.010, A050.020.100.030, A060.030.030.100.030

### [A040.030.020] ET6002 CANFD Unsupported Projection

Role: CANFD 视角下的 ET6002 当前 unsupported/fail-closed canonical 边界；没有 A050 implementation 节点。
Resources: source/profiles/chips/et6002/capabilities.yaml, source/profiles/chips/et6002/connections.yaml, source/profiles/chips/et6002/evidence.yaml
Relations: A010.020.030, A020.040.020, A030.060.020, A060.010.010.020, A060.030.030.200.030

### [A040.030.030] ET6003 CANFD Projection

Role: CANFD 视角下的 ET6003 canonical 能力；memory/program/verify/security 复用 CAN-family 主干，identify/admission/driver 保持 route-specific。
Resources: source/apps/cli/chips/et6003/et6003_canfd_identify_runner.h, source/apps/cli/chips/et6003/et6003_canfd_profile_admission.h, source/transport/can/zlg_canfd_driver.h
Relations: A010.030.030, A020.040.030, A030.060.030, A050.020.300.020, A050.020.300.030, A060.030.030.300.030

## [A040.040] CMSIS-DAP SWD Route

Role: CMSIS-DAP SWD 的共享路线视角；共享 driver/session/HID runtime，芯片操作由各 chip-local executor/algorithm 实现。
Resources: source/probe/drivers/cmsis_dap/cmsis_dap_probe_driver.h, source/probe/drivers/cmsis_dap/cmsis_dap_swd_session.h, source/probe/drivers/cmsis_dap/cmsis_dap_platform_adapter.h, source/probe/drivers/cmsis_dap/cmsis_dap_probe_driver_factory.h, source/platform/vendor/cmsis_dap/cmsis_dap_hid_runtime.h
Relations: A010.010.040, A010.020.040, A010.030.040, A020.050, A030.070, A050.030.030.010, A050.030.050.010, A060.010

### [A040.040.010] ET3101 DAP Projection

Role: DAP 视角下的 ET3101 canonical 能力、executor/algorithm 与当前验证入口。
Relations: A010.010.040, A020.050.010, A030.070.010, A050.030.020.010.010, A050.030.040.010, A060.030.030.100.040

### [A040.040.020] ET6002 DAP Projection

Role: DAP 视角下的 ET6002 canonical 能力；concrete path 存在但正式状态仍由 Profile/admission 决定。
Relations: A010.020.040, A020.050.020, A030.070.020, A050.030.020.020.010, A050.030.040.020, A060.010.010.020, A060.030.030.200.040

### [A040.040.030] ET6003 DAP Projection

Role: DAP 视角下的 ET6003 canonical 能力；concrete path 存在但正式状态仍由 Profile/admission 决定。
Relations: A010.030.040, A020.050.030, A030.070.030, A050.030.020.030.010, A050.030.040.030, A060.010.010.030, A060.030.030.300.040

## [A040.050] J-Link SWD Route

Role: J-Link SWD 的共享路线视角；共享 driver/session/DLL runtime，芯片操作由各 chip-local executor/algorithm 实现。
Resources: source/probe/drivers/jlink/jlink_probe_driver.h, source/probe/drivers/jlink/jlink_swd_session.h, source/probe/drivers/jlink/jlink_platform_adapter.h, source/platform/vendor/jlink/jlink_runtime.h, source/platform/vendor/jlink/jlink_dll_api.h
Relations: A010.010.050, A010.020.050, A010.030.050, A020.060, A030.080, A050.030.030.020, A050.030.050.020, A060.010

### [A040.050.010] ET3101 J-Link Projection

Role: J-Link 视角下的 ET3101 canonical 能力、executor/algorithm 与当前验证入口。
Relations: A010.010.050, A020.060.010, A030.080.010, A050.030.020.010.020, A050.030.040.010, A060.030.030.100.050

### [A040.050.020] ET6002 J-Link Projection

Role: J-Link 视角下的 ET6002 canonical 能力；concrete path 存在但正式状态仍由 Profile/admission 决定。
Relations: A010.020.050, A020.060.020, A030.080.020, A050.030.020.020.020, A050.030.040.020, A060.010.010.020, A060.030.030.200.050

### [A040.050.030] ET6003 J-Link Projection

Role: J-Link 视角下的 ET6003 canonical 能力；连接 chip-local executor、ET6003 algorithms、Profile 与 validation 入口，不在本节点声明产品支持结论。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/profiles/chips/et6003/capabilities.yaml, source/profiles/chips/et6003/connections.yaml
Relations: A010.030.050, A020.060.030, A030.080.030, A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A050.030.050.020, A060.010.010.030, A060.030.030.300.050
