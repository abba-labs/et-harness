# ET6801 Chip 层

更新时间：2026-07-24 19:10 CST

本目录是 ET6801 固件构建所需芯片内容的唯一来源：

```text
et6801/
├─ config/                  逻辑ID到ET6801物理资源的私有映射
├─ sdk/
│  ├─ CMSIS/               Core、Device、startup 和 system
│  └─ ET6x_Driver/         ET6x 公共驱动头文件与源文件
├─ linker/                  FPGA ITCM 与 Silicon Flash 链接脚本
├─ keil/
│  ├─ templates/           本地 Keil 工程与选项模板
│  └─ JLinkSettings.ini    调试器配置模板
├─ project.yaml            工程源码、包含目录、目标和分组清单
└─ README.md
```

生成后的 Keil 工程只能引用本项目 `firmware` 内的源码和头文件。不得从
`D:\lihuan\vibe_code\code`、其他 SDK 工作区或个人目录加载 startup、system、
CMSIS 或 ET6x Driver。

`sdk` 中保留完整 CMSIS 和 ET6x Driver，便于后续增加 IP；当前 `project.yaml`
只编译控制通信所需的 Cortex、CRG、GPIO、Interrupt 和 UART 驱动。增加 IP 时只在
`Chip_Drivers` 清单增加对应源文件，不复制新的芯片工程。

FPGA和硅后目标的公共层可见参数位于
`firmware/boards/et6801_fpga/et_board_config.h`和
`firmware/boards/et6801_silicon/et_board_config.h`。
`config/et_chip_wrap_config.h`只保存ET6801 SDK实例、物理引脚、复用和IRQ映射。
新增芯片时增加对应 Config、SDK、Board 和工程清单，不修改公共 Wrap、Service、
PC Driver 或 PC Case。

当前控制通道为 UART0、GPIO12 TX、GPIO13 RX、115200 8N1、RX IRQ 和 TX
polling。初始化顺序与 ISR 由 Application 负责。
