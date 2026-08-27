# Firmware Wrap

本目录保存跨芯片稳定的公共Wrap接口及实现：

```text
wrap/
├─ include/    # 公共Wrap头文件
└─ src/        # 公共Wrap实现
```

文件按职责命名，例如`et_uart_wrap.h/.c`、`et_dma_wrap.h/.c`和
`et_resource_wrap.h/.c`。本README只提供目录导航，不定义Wrap调用边界、Chip Config、
Driver Extension或IRQ规则。

权威规则：

- [R310 Firmware Wrap](../../report/design/rules/R310_firmware_wrap.md)
- [R320 Firmware IRQ](../../report/design/rules/R320_interrupt_subsystem.md)
