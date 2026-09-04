# ET6801 GPIO Support Adaptation

更新时间：2026-09-04 15:20 CST。

## 第一章 范围与依据

本轮仅为SPI对测提供GPIO复用支持，不是GPIO全集分析。直接证据：仓库`firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_pinmap.h`、`et6x_gpio.h`及`Src/et6x_gpio.c`。SDK符号证明复用选择，不能单独证明焊线正确；真实SPI数据仍需HIL。

资料导航已读取`project-governance/ip-analysis-sources.yaml`；本轮复用已审SPI文档的接线依据，不宣称已搜索GPIO所有历史测试资料或完成GPIO覆盖。

## 第二章 Driver

复用已有`GPIO_initPadConfigStruct`、`GPIO_setPadConfig`、`GPIO_setPinConfig`。默认Pad包含输入使能，适用于两端交换SPI主从角色。Wrap不得写IOMUX寄存器。新信号表独立于旧UART引脚表，旧控制UART不变。

## 第三章 信号映射

| 逻辑信号 | GPIO | SDK mux符号 | 编码 |
|---|---:|---|---:|
| SPI0 CLK | 60 | GPIO60_MODE_SPI0_CLK | 15 |
| SPI0 CS | 61 | GPIO61_MODE_SPI0_CS_n | 15 |
| SPI0 MOSI | 16 | GPIO16_MODE_SPI0_MOSI | 1 |
| SPI0 MISO | 55 | GPIO55_MODE_SPI0_MISO | 1 |
| SPI1 CLK | 65 | GPIO65_MODE_SPI1_CLK | 15 |
| SPI1 CS | 66 | GPIO66_MODE_SPI1_CS_n | 15 |
| SPI1 MOSI | 63 | GPIO63_MODE_SPI1_MOSI | 15 |
| SPI1 MISO | 64 | GPIO64_MODE_SPI1_MISO | 15 |

Chip Config必须使用表中的SDK宏，不能抄编码作为魔鬼数字。用户选择的GPIO与SPI实例/信号组合必须完整匹配，不能只按GPIO号匹配后忽略实例。

## 第四章 执行边界

用户2026-09-04确认SPI0/SPI1已接线。同名信号连接，1.8V板级接口及共地参见`../spi/ET6801_spi.md`。本轮尚无实测，不把接线确认记为PASS。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|

本轮只提供支持动作，无独立GPIO Feature。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|

无独立GPIO Case；SPI对应Case状态由SPI芯片文档记录。
