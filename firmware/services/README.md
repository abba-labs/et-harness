# Firmware Services

本目录保存PC可调用的公共基础Service和各IP Service：

```text
services/
├─ include/    # Service公共头、Command定义和静态注册接口
└─ src/        # Framework Service及各IP Service实现
```

文件按Service或IP命名，不为单个Service重复建立`include/src`子树。目录内容用于代码导航，
不在本README重复Service职责、依赖、IRQ或Wire规则。

权威规则：

- [R300 Firmware Service](../../report/design/rules/R300_firmware_service.md)
- [R320 Firmware IRQ](../../report/design/rules/R320_interrupt_subsystem.md)
- [R400 ET-Frame v1](../../report/design/rules/R400_et_frame_v1.md)
