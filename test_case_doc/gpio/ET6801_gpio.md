# ET6801 GPIO Support Adaptation

更新时间：2026-09-04 22:54 CST。

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
| CAN0 RX | 58 | GPIO58_MODE_CANFD0_RX | 11 |
| CAN0 TX | 59 | GPIO59_MODE_CANFD0_TX | 11 |

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

## 本轮实现状态

2026-09-04 22:54 CST：追加CAN RX/TX稳定信号及上述两项SDK映射，配置由独立GPIO Service/Wrap执行，CAN Service不参与。用户声明的CANFD0 PAD对应公共can0；CAN盒子CAN1是外部设备通道，不是芯片CAN1。当前CAN PC信号枚举与Case尚未接入，尚未通过CAN HIL；不扩大为CAN所有PAD候选已支持。

2026-09-04 15:35 CST：GPIO Service提供VALIDATE_SIGNAL/CONFIGURE_SIGNAL，独立于SPI Service。GPIO Wrap新接口按GPIO、信号、外设实例三元组查表；信号表列入SDK的全部SPI CLK/CS/MOSI/MISO候选，不把本次接线固化为唯一可用组合。旧UART配置入口保持不变。Application只增加静态注册项，无硬件初始化动作。待软件验证和SPI实测，当前不声明硬件PASS。

2026-09-04 15:43 CST：上述固件批次已通过FPGA_ITCM和SILICON_FLASH两目标编译（均0错误、0警告），总软件门禁1064 PASS / 16 SKIP；另以WSL GCC编译真实GPIO Service完成Wire/非法请求测试。SKIP为主机软件测试条件，不是SPI硬件Case结论。证据：`artifacts/runs/20260904_spi_gpio/stages/`。PC独立GPIO Driver已补齐，等待本批软件门禁；没有执行烧录或HIL。

2026-09-04 15:53 CST：PC GPIO Driver的9项新增单测通过；本批总软件门禁1073 PASS / 16 SKIP，完整日志为`artifacts/runs/20260904_spi_gpio/stages/pc_gpio_gate_accept.log`。查询/配置请求、u16LE布局、非法输入无发送副作用及空响应检查均通过。GPIO/SPI分层无变更；SPI正式Case与HIL尚未完成，不能将本次软件结果记为SPI Case PASS。
