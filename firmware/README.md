# Firmware

测试固件目录与Keil工程分组保持对应：

| 目录 | Keil分组 | 内容 |
|---|---|---|
| `application/` | `Application` | 公共入口、初始化顺序和控制通信ISR |
| `boards/<board>/` | `Board` | 目标板编译期宏 |
| `framework/` | `Framework` | ET-Frame、Router、缓冲区和runtime |
| `services/` | `Services` | 公共基础Service和各IP Service |
| `wrap/` | `Wrap` | 按IP划分的稳定公共驱动接口 |
| `chips/<chip>/` | `Chip_*` | 芯片配置、本地SDK、链接和工程清单 |
| `build/<chip>/` | Keil工程 | 生成后的工程与芯片本地构建输出 |

工程生成入口：

```powershell
python tools/firmware/generate_keil_project.py firmware/chips/<chip>/project.yaml
```

本README不定义Firmware依赖、Service、Wrap、IRQ或Wire规则。权威正文：

- [R300 Firmware Service](../report/design/rules/R300_firmware_service.md)
- [R310 Firmware Wrap与Chip Config](../report/design/rules/R310_firmware_wrap.md)
- [R320 Firmware IRQ](../report/design/rules/R320_interrupt_subsystem.md)
- [R400 ET-Frame v1](../report/design/rules/R400_et_frame_v1.md)
