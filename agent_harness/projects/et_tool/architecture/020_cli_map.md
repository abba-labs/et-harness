# [A020] CLI Projection Map

Role: 从正式 et-cli 视角投影 A010 canonical 能力实例，回答“某个 Chip × Route 能力从 CLI 哪里进入”。
Boundary: 不重新定义产品能力，不复制底层实现事实；Chip × Route × Operation 的唯一能力语义在 A010，真实实现与验证分别下钻 A050/A060。
Resources: source/apps/cli/main.cpp, source/apps/cli/cli_chip_module.h
Relations: A010, A030, A040, A050, A060

## [A020.010] Unified CLI Entry And Chip Dispatch

Role: 统一 et-cli 入口、CliChipModule 合同与 chip-local module 分发边界。
Resources: source/apps/cli/main.cpp, source/apps/cli/cli_chip_module.h, source/apps/cli/CMakeLists.txt
Relations: A010, A050.040.010

## [A020.020] UART CLI Projection

Role: UART ROM 能力的 CLI 投影视角。
Relations: A010.010.010, A010.020.010, A010.030.010, A040.010, A050.020

### [A020.020.010] ET3101 UART CLI

Role: ET3101 UART 的 dedicated chip-local CLI 首入口。
Resources: source/apps/cli/chips/et3101/et3101_uart_cli_module.cpp, source/apps/cli/chips/et3101/et3101_uart_profile_admission.h
Relations: A010.010.010, A050.020.100.010, A060.030.030.100.010, A060.040.010.100.010, A020.080

### [A020.020.020] ET6002 UART CLI

Role: ET6002 统一 CLI 中的 UART runner 入口。
Resources: source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6002/et6002_uart_memory_cli_runner.h, source/apps/cli/chips/et6002/et6002_uart_readonly_cli_runner.h
Relations: A010.020.010, A050.020.200.010, A060.030.030.200.010, A060.040.010.200.010, A020.080

### [A020.020.030] ET6003 UART CLI

Role: ET6003 统一 CLI 中的 UART runner 入口。
Resources: source/apps/cli/chips/et6003/et6003_cli_module.cpp, source/apps/cli/chips/et6003/et6003_uart_memory_runner.h
Relations: A010.030.010, A050.020.300.010, A060.030.030.300.010, A060.040.010.300.010, A020.080

## [A020.030] CAN CLI Projection

Role: Classic CAN ROM 能力的 CLI 投影视角。
Relations: A010.010.020, A010.020.020, A010.030.020, A040.020, A050.020

### [A020.030.010] ET3101 CAN CLI

Role: ET3101 Classic CAN 的 dedicated chip-local CLI 首入口。
Resources: source/apps/cli/chips/et3101/et3101_can_cli_module.cpp, source/apps/cli/chips/et3101/et3101_can_profile_admission.h
Relations: A010.010.020, A050.020.100.020, A060.030.030.100.020, A060.040.010.100.020, A020.080

### [A020.030.020] ET6002 CAN CLI

Role: ET6002 统一 CLI 中的 Classic CAN runner 入口。
Resources: source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6002/et6002_can_memory_cli_runner.h, source/apps/cli/chips/et6002/et6002_can_readonly_cli_runner.h
Relations: A010.020.020, A050.020.200.020, A060.030.030.200.020, A060.040.010.200.020, A020.080

### [A020.030.030] ET6003 CAN CLI

Role: ET6003 统一 CLI 中的 Classic CAN/CAN-family runner 入口。
Resources: source/apps/cli/chips/et6003/et6003_cli_module.cpp, source/apps/cli/chips/et6003/et6003_can_memory_runner.h, source/apps/cli/chips/et6003/et6003_can_profile_admission.h
Relations: A010.030.020, A050.020.300.020, A060.030.030.300.020, A060.040.010.300.020, A020.080

## [A020.040] CANFD CLI Projection

Role: CAN FD ROM 能力与当前 fail-closed 边界的 CLI 投影视角。
Relations: A010.010.030, A010.020.030, A010.030.030, A040.030, A050.020

### [A020.040.010] ET3101 CANFD CLI

Role: ET3101 CANFD 的 dedicated chip-local CLI 首入口。
Resources: source/apps/cli/chips/et3101/et3101_canfd_cli_module.cpp, source/apps/cli/chips/et3101/et3101_canfd_profile_admission.h
Relations: A010.010.030, A050.020.100.030, A060.030.030.100.030, A060.040.010.100.030, A020.080

### [A020.040.020] ET6002 CANFD CLI Boundary

Role: ET6002 CANFD 当前没有正式产品升级 CLI route；该节点只导航 fail-closed/unsupported 产品事实，不提供伪实现入口。
Resources: source/profiles/chips/et6002/capabilities.yaml, source/profiles/chips/et6002/connections.yaml
Relations: A010.020.030, A060.010.010.020, A060.030.030.200.030

### [A020.040.030] ET6003 CANFD CLI

Role: ET6003 CANFD route-specific identify/admission 入口；memory/program/verify/security 主体继续复用 CAN-family implementation。
Resources: source/apps/cli/chips/et6003/et6003_cli_module.cpp, source/apps/cli/chips/et6003/et6003_canfd_identify_runner.h, source/apps/cli/chips/et6003/et6003_canfd_profile_admission.h
Relations: A010.030.030, A050.020.300.020, A050.020.300.030, A060.030.030.300.030, A060.040.010.300.030, A020.080

## [A020.050] CMSIS-DAP CLI Projection

Role: CMSIS-DAP SWD 能力的 CLI 投影视角。
Relations: A010.010.040, A010.020.040, A010.030.040, A040.040, A050.030

### [A020.050.010] ET3101 DAP CLI

Role: ET3101 DAP 正式 CLI 与 chip-local Probe 装配入口。
Resources: source/apps/cli/chips/et3101/et3101_debug_probe_cli_module.cpp
Relations: A010.010.040, A050.030.020.010.010, A050.030.030.010, A050.030.040.010, A060.030.030.100.040, A020.080

### [A020.050.020] ET6002 DAP CLI

Role: ET6002 DAP concrete CLI/executor 入口；正式产品 admission 仍由 A060 决定。
Resources: source/apps/cli/chips/et6002/et6002_debug_probe_cli_module.cpp
Relations: A010.020.040, A050.030.020.020.010, A050.030.030.010, A050.030.040.020, A060.010.010.020, A060.030.030.200.040, A060.040.010.200.040, A020.080

### [A020.050.030] ET6003 DAP CLI

Role: ET6003 DAP concrete CLI/executor 入口；正式产品 admission 仍由 A060 决定。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_read_mem_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_cmsis_dap_pflash_hw_executor.h
Relations: A010.030.040, A050.030.020.030.010, A050.030.030.010, A050.030.040.030, A060.010.010.030, A060.030.030.300.040, A060.040.010.300.040, A020.080

## [A020.060] J-Link CLI Projection

Role: J-Link SWD 能力的 CLI 投影视角。
Relations: A010.010.050, A010.020.050, A010.030.050, A040.050, A050.030

### [A020.060.010] ET3101 J-Link CLI

Role: ET3101 J-Link 正式 CLI 与 chip-local Probe 装配入口。
Resources: source/apps/cli/chips/et3101/et3101_debug_probe_cli_module.cpp, source/apps/cli/chips/et3101/et3101_debug_probe_jlink_hw_executor.h
Relations: A010.010.050, A050.030.020.010.020, A050.030.030.020, A050.030.040.010, A060.030.030.100.050, A020.080

### [A020.060.020] ET6002 J-Link CLI

Role: ET6002 J-Link concrete CLI/session 入口；部分 chip-specific J-Link executor 位于 Probe algorithm 层，正式产品 admission 仍由 A060 决定。
Resources: source/apps/cli/chips/et6002/et6002_debug_probe_cli_module.cpp, source/apps/cli/chips/et6002/et6002_debug_probe_jlink_readonly_hw_executor.h
Relations: A010.020.050, A050.030.020.020.020, A050.030.030.020, A050.030.040.020, A060.010.010.020, A060.030.030.200.050, A060.040.010.200.050, A020.080

### [A020.060.030] ET6003 J-Link CLI

Role: ET6003 J-Link 的正式 CLI 入口与 chip-local executor 集合；从这里可继续下钻 J-Link shared driver/runtime、ET6003 algorithm 与 Profile admission。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_read_mem_hw_executor.h, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_option_go_hw_executor.h
Relations: A010.030.050, A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A050.030.050.020, A060.010.010.030, A060.030.030.300.050, A060.040.010.300.050, A020.080

## [A020.070] Result Error And Progress Boundary

Role: CLI 对 GUI 与 Automation 输出 result、error、return code 与 progress 的正式产品边界。
Resources: source/application/kernel/operation_progress.h, source/domain/result/, source/apps/cli/
Relations: A030.090, A050.010, A060.030, A060.040

## [A020.080] CLI Composition Root

Role: chip-local CLI 组合 concrete driver、backend、executor、workflow 与 request 的当前具体装配边界。
Resources: source/apps/cli/chips/et3101/et3101_cli_module.cpp, source/apps/cli/chips/et6002/et6002_cli_module.cpp, source/apps/cli/chips/et6003/et6003_cli_module.cpp
Relations: A010, A050.020.100, A050.020.200, A050.020.300, A050.030.020
