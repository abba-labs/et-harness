# ET6801 CRG Adaptation Facts

> 本文件只保存 ET6801 对公共 `crg.md` 的芯片适配事实，不定义第二套公共命令、Feature 或 Case。

## 1. Source Basis

- Chip Config：`firmware/chips/et6801/config/et_chip_wrap_config.h`。
- Chip Driver：`firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_crg.h` 与对应 Source。
- 寄存器字段来源：ET6801 CMSIS 头文件中的 CRG WDG 时钟选择和分频字段宏。

## 2. Public-to-Chip Mapping

| Public fact | ET6801 mapping |
|---|---|
| CORDIC clock/reset logical instance `0` | Chip Config 映射到 ET6801 CORDIC CRG selector |
| FMAC clock/reset logical instance `0` | Chip Config 映射到 ET6801 FMAC CRG selector |
| WDG logical instance `0` | `WDG0` |
| WDG logical instance `1` | `WDG1` |
| WDG source `HSOSC` | `CRG_WDG_CLKSRC_HSOSC` |
| WDG source `APB1` | `CRG_WDG_CLKSRC_APB1` |
| WDG divider maximum | 由 `CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk/Pos` 推导，不在公共层写死 |

## 3. Driver Extension Boundary

- 正式 SDK API `CRG_selectWDGClockSource()`负责设置时钟源与编码分频。
- 测试扩展 `CRG_testGetWDGClockConfig()`只读取源选择和分频字段，供公共 CRG Wrap 返回真实硬件读回。
- 测试扩展位于 SDK Driver 的测试扩展区域，仅在 `ET_ENABLE_TEST_DRIVER_EXTENSIONS` 构建中启用。
- 公共 Service/Wrap 不出现 ET6801 寄存器、SDK 枚举或物理地址。

### 3.1 Reset Selector Correction

- ET6801生成CMSIS将`CORDIC0`放在`SRST0/GTEN0 bit20`。
- ET6801生成CMSIS将`CRC`、`FMAC`、`AES`放在`SRST1/GTEN1 bit22/23/24`。
- CRG Chip Driver选择值直接复用生成CMSIS位置；公共CRG Wrap不保存寄存器位置。

## 4. Current Validation Boundary

- FPGA 与 Silicon 固件工程均已完成编译/链接验证。
- 本文不声明 WDG 时钟切换的 HIL PASS；实际比例和恢复结论由 WDG Formal Case 及其运行证据给出。
