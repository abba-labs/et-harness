# Framework

本目录保存芯片无关的固件基础设施：

- ET-Frame 编解码、CRC、错误恢复和重复响应重放；
- 公共 Service 消息编解码与固定容量路由；
- 环形缓冲区、IRQ/DMA 注册管理和 Runtime 轮询调度。

Framework 的职责边界与协议契约以以下权威规则为准：

- [R300 Firmware Service](../../report/design/rules/R300_firmware_service.md)
- [R320 Interrupt Subsystem](../../report/design/rules/R320_interrupt_subsystem.md)
- [R400 ET-Frame V1](../../report/design/rules/R400_et_frame_v1.md)
