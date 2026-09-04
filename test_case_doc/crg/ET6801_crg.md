# ET6801 CRG Adaptation Facts

> 本文件只保存 ET6801 对公共 `crg.md` 的芯片适配事实，不定义第二套公共命令、Feature 或 Case。

更新时间：2026-09-04 23:32 CST。PC CAN类别10请求编码已专项验证；该软件验证不代表CAN物理复位HIL通过。

## 1. Source Basis

- Chip Config：`firmware/chips/et6801/config/et_chip_wrap_config.h`。
- Chip Driver：`firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_crg.h` 与对应 Source。
- 寄存器字段来源：ET6801 CMSIS 头文件中的 CRG WDG 时钟选择和分频字段宏。

## 2. Public-to-Chip Mapping

| Public fact | ET6801 mapping |
|---|---|
| CORDIC clock/reset logical instance `0` | Chip Config 映射到 ET6801 CORDIC CRG selector |
| FMAC clock/reset logical instance `0` | Chip Config 映射到 ET6801 FMAC CRG selector |
| IPCM clock/reset logical instance `0` | 已提供`CRG_PERIPH_IPCM`：`GTEN1/SRST1 bit25`；Chip Config行由IPCM接入批次加入。复位前须停止两个核访问 Mailbox |
| SPI clock/reset logical instances `0..3` | `GTEN1/SRST1 bit14..17`；选择值为`BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_SPI<n>_Pos`，分别映射SPI0～3；公共类别为SPI，不区分主从角色 |
| CAN clock/reset logical instances `0..2` | `GTEN1/SRST1 bit0..2`；CAN0/1复用正确SDK枚举，补充CAN2枚举，保留旧枚举值；公共类别为CAN。配置前由PC分别使能时钟、复位，不在CAN Wrap调用CRG |
| WDG logical instance `0` | `WDG0` |
| WDG logical instance `1` | `WDG1` |
| WDG source `HSOSC` | `CRG_WDG_CLKSRC_HSOSC` |
| WDG source `APB1` | `CRG_WDG_CLKSRC_APB1` |
| WDG divider maximum | 由 `CRG_PLLCLK_CFG3_CRG_WDG0_STB_Msk/Pos` 推导，不在公共层写死 |
| SYSCNT clock logical instance `0` | `CRG.GTEN0.CRG_CLK_GTEN_SYSCNT` bit16；使用生成宏`CRG_GTEN0_CRG_CLK_GTEN_SYSCNT_Msk`。SVD没有独立SYSCNT SRST位，故不加入通用RESET映射 |

## 3. Driver Extension Boundary

- 正式 SDK API `CRG_selectWDGClockSource()`负责设置时钟源与编码分频。
- 测试扩展 `CRG_testGetWDGClockConfig()`只读取源选择和分频字段，供公共 CRG Wrap 返回真实硬件读回。
- 测试扩展位于 SDK Driver 的测试扩展区域，仅在 `ET_ENABLE_TEST_DRIVER_EXTENSIONS` 构建中启用。
- 公共 Service/Wrap 不出现 ET6801 寄存器、SDK 枚举或物理地址。
- `CRG_testSetSYSCNTClock`和`CRG_testGetSYSCNTClock`只写/读GTEN0的SYSCNT位，绕开旧`CRG_PERIPH_SYSCNT=0x15`错误选择。保留旧枚举以免改变其他使用者ABI，但自动化路径禁止使用它；旧通用SDK接口风险尚存在，不宣称已经整体修复旧SDK。

### 3.1 Reset Selector Correction

- SPI旧SDK的`CRG_PERIPH_SPIM0/1/2/SPIS0`分别为`0x26..0x29`，不对应ET6801的SPI位。新增Chip Config映射使用生成CMSIS符号形成`0x2E..0x31`，复用现有CRG Driver原子操作，不改旧枚举和其他IP映射。此处不宣称整个旧SDK选择表已修复。
- ET6801生成CMSIS将`CORDIC0`放在`SRST0/GTEN0 bit20`。
- ET6801生成CMSIS将`CRC`、`FMAC`、`AES`放在`SRST1/GTEN1 bit22/23/24`。
- ET6801生成CMSIS将`IPCM`放在`SRST1/GTEN1 bit25`，选择值复用`CRG_GTEN1_CRG_CLK_GTEN_IPCM_Pos`，不新增寄存器访问函数。
- CRG Chip Driver选择值直接复用生成CMSIS位置；公共CRG Wrap不保存寄存器位置。

## 4. Current Validation Boundary

- 2026-09-04新增CAN0～2时钟/复位映射，PC类别接入和硬件复位回归尚未完成；不得把生成位号匹配计为HIL PASS。

- 2026-09-04新增SPI映射尚未执行HIL；静态映射、Wire和编译检查不能证明硬件复位已通过。
- FPGA 与 Silicon 固件工程均已完成编译/链接验证。
- 本文不声明 WDG 时钟切换的 HIL PASS；实际比例和恢复结论由 WDG Formal Case 及其运行证据给出。
- 2026-09-03新增IPCM映射尚未进行HIL；不得将静态映射检查计为IPCM复位实测通过。
