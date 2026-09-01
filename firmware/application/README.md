# Application

本目录保存公共固件入口与控制通信编排：

- `main.c`：启动公共系统能力、Framework、Service 和控制通信。
- `et_control_uart.c`：通过公共 Wrap 组合控制 UART、GPIO 与 IRQ，并维护协议收发。

Application 的依赖边界、硬件访问方式和中断职责以以下权威规则为准：

- [R300 Firmware Service](../../report/design/rules/R300_firmware_service.md)
- [R310 Firmware Wrap](../../report/design/rules/R310_firmware_wrap.md)
- [R320 Interrupt Subsystem](../../report/design/rules/R320_interrupt_subsystem.md)
- [R400 ET-Frame V1](../../report/design/rules/R400_et_frame_v1.md)
