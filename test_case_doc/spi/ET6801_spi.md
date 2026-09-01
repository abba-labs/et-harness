# ET6801 SPI Chip Analysis & Adaptation Contract

> 本文件只记录 ET6801 SPI 的 Hardware Truth、寄存器、Driver、历史测试、Capability 和 Board/Bench 适配事实。
> 公共 Feature、Case、Oracle、Observation 和稳定接口以同目录 `spi.md` 为唯一权威来源。
> QSPI 是独立 IP，不纳入本文分析和 Case 统计。

# 第一章 IP分析与Source Coverage

## 1.1 分析目标与证据优先级

```text
Target chip  = ET6801
Target IP    = SPI0..SPI3
Target lane  = FPGA / Silicon
Hardware run = NOT EXECUTED，本轮仅完成分析与Case Plan

ET6801 direct SVD / generated header
  > ET6801 current SDK Driver
  > ET6801 historical Unit / Functional / FPGA / Smoke source
  > ET6003 / ET3101 requirement and source reference
```

ET6003、ET3101只用于识别历史Feature和测试思想，不能覆盖ET6801 SVD事实。历史源码和日志只能证明曾采用某种测试方法，不能等同当前自动化平台PASS。

## 1.2 Source Map Coverage

| Source | Locator | 状态 | 定向结论 |
|---|---|---|---|
| ET6801 requirement | `project-governance/ip-analysis-sources.yaml::et6801.requirements` | NO_MATCH | 未找到ET6801专属SPI需求JSON；不据此否定Hardware Feature。 |
| ET6003 requirement | `<requirements>/test_case/6003/spi.json` | FOUND / FAMILY_REFERENCE | 包含模块、25MHz、Mode、角色、CS、位宽、Transfer Mode、FIFO、IRQ、DMA和历史Case。 |
| ET3101 requirement | `<requirements>/test_case/3101/spi.json` | FOUND / FAMILY_REFERENCE | 与ET6003覆盖域基本一致，Case ID较完整；只作历史Source Item。 |
| ET6801 SPI SVD | `<sdk.et6801>/Tools/RegGen/svd/SPI_DWC_ssi.svd` | FOUND / PRIMARY | Controller/Target、Motorola/TI/Microwire、Mode、位宽、FIFO、IRQ、DMA、CS、采样延迟和冲突状态的直接证据。 |
| merged SVD | `test_case_doc/ET6801.svd` | FOUND | 确认SPI0..SPI3实例、Base和IRQ合并事实。 |
| generated header | `firmware/chips/et6801/sdk/CMSIS/Device/Include/et6801.h` | FOUND | 确认4实例、IRQ、CRG Reset、DMA Mux和Pinmux枚举。 |
| ET6801 Driver | `<sdk.et6801>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_spi.*` | FOUND | 当前公开API覆盖基础配置、回环、FIFO、IRQ和DMA；存在若干实现与语义缺口。 |
| ET6801 UnitTest | `<sdk.et6801>/DFP/Test/UnitTest/test_spi.c` | FOUND / HISTORICAL | SPI0 Controller与SPI3 Target外部链路，覆盖FIFO、Mode、CS、位宽、IRQ和DMA。 |
| ET6801 FunctionalTest | `<sdk.et6801>/DFP/Test/FunctionalTest/spi_ft.c` | FOUND / HISTORICAL | 覆盖同实例MOSI-MISO外部回接、SPI0-SPI3配对、DMA、IRQ和25MHz Mode1。 |
| ET6801 FPGATest | `<sdk.et6801>/DFP/Test/FPGATest/spi_fpga_test.c` | FOUND / HISTORICAL | 给出SPI0/SPI3外部接插件路由及真实双实例传输方法。 |
| ET6801 SmokeTest | `<sdk.et6801>/DFP/Test/SmokeTest/{spi_smoke_test.c,test_spi_device*.c}` | FOUND / HISTORICAL | 包含片内回环、SPI0到SPI3及设备通信测试思想。 |
| ET6801 TestLog | `<sdk.et6801>/DFP/Test/TestLog/spi_ut.log` | FOUND / CONFLICTING | 部分Case输出与数据不一致，不能作为当前PASS；仅保留失败和仪器依赖线索。 |
| ET6003/ET3101 source | `<sdk.et6003>`、`<sdk.et3101>`定向SPI目录 | FOUND / FAMILY_REFERENCE | 确认外部回接、双角色、FIFO、IRQ、DMA、速率和设备通信是历史公共覆盖域。 |
| current capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/spi.yaml` | FOUND / INCOMPLETE | 只识别实例、Enable、Base、Version和IRQ；主要SPI字段仍在audit中未分类。 |
| current platform code | `firmware/{wrap,services}`、`pc/et_test_platform/{drivers,test_cases}` | NO_MATCH | 当前没有SPI公共Wrap、Service、PC Driver和Formal Case。 |

本轮只对SPI目标文件和登记路径定向检索，没有全量扫描整个SDK或文档库。

## 1.3 工作原理与应用

ET6801 SPI基于DW SSI类控制器，包含4个独立实例。Controller根据输入时钟和偶数分频产生SCLK，使用CS选择Target，并通过MOSI/MISO完成串行全双工或单向传输；Target由外部SCLK和CS驱动。数据先进入TX/RX FIFO，CPU、IRQ或DMA负责填充和读取。

主要应用包括：

- MCU与Flash、传感器、ADC/DAC、显示器等外部器件通信；
- 两个片上SPI实例通过板级连线形成Controller/Target自验证链路；
- FPGA作为可编程Peer，产生或捕获Motorola SPI、TI SSP和Microwire波形；
- 通过DMA完成跨FIFO深度的连续数据传输；
- 通过逻辑分析仪、FPGA或示波器验证SCLK、CS、CPOL、CPHA和频率。

片内`SRL`回环只连接控制器内部Shift Register，适合快速检查配置和数据通路。它不经过真实PAD，不能证明Pinmux、输出驱动、输入采样、板级连线或Target角色。因此公共计划必须保留外部MOSI-MISO回接和双实例Controller-Target两类真实链路Case。

# 第二章 Driver分析

## 2.1 当前Driver能力

当前`et6x_spi.h/.c`公开的主要能力如下：

| Driver能力 | 当前事实 | 公共映射 |
|---|---|---|
| Enable/Disable/Config | 已有 | `configure`、`enable`、`disable` |
| Role | Controller/Target | `role` |
| Motorola Clock Mode | 4种CPOL/CPHA组合 | `clock_mode` |
| Frame Bits | Driver校验4..16 bit | `frame_bits` |
| Transfer Mode | TX_RX、TX_ONLY、RX_ONLY、EEPROM_READ | `transfer_mode` |
| Bitrate | Driver按PCLK和偶数Divider计算；代码限制不高于50MHz | `bitrate_hz`，实际可达上限仍需HIL验证 |
| Frame Count | 配置接收帧数 | `frame_count`，公共输入必须大于0 |
| CS | 软件拉低/拉高、Target Select Toggle | `cs_policy` |
| Internal Loopback | 已有开关 | `loopback_set` |
| CPU Transfer | Blocking/Nonblocking、FIFO/Polling和24/32-bit helper | 公共动作必须保持有界，不能直接暴露无界循环 |
| FIFO | Reset、Threshold、Start Threshold和Level | `fifo_reset`、FIFO Snapshot |
| IRQ | Enable/Disable、Status读取和Clear | 尚缺Raw/Mask/Delivery完整稳定Snapshot |
| DMA | TX/RX Threshold和Enable/Disable | `dma_configure` |
| RX Sample Delay | Config结构含字段 | `rx_sample_delay` |

## 2.2 Driver Gap / Risk Matrix

| ID | Severity | Current Fact | 影响 | 后续决策 |
|---|---|---|---|---|
| `SPI_DRV_001` | HIGH | Config只暴露Motorola CPOL/CPHA，未暴露SVD中的FRF和MWCR | TI SSP/Microwire不能通过正式API配置 | 按测试Driver扩展规则在Driver底部补充芯片中立协议配置接口。 |
| `SPI_DRV_002` | HIGH | 当前只读取Mask后ISR，缺少Raw和Mask快照API | 无法准确验证IRQ Source、Mask和Delivery | 补充Raw/Mask/Snapshot测试接口，Wrap只调用Driver。 |
| `SPI_DRV_003` | HIGH | `SPI_getTansferStartFIFOLevel`掩码/移位表达式存在优先级风险 | Start Threshold读回可能错误 | 在实现前增加Driver单元检查并按原风格修复。 |
| `SPI_DRV_004` | MEDIUM | DMA Threshold函数参数校验调用形式不完整，实例校验不一致 | 非法输入可能未失败关闭 | 统一参数校验，不在Service补芯片判断。 |
| `SPI_DRV_005` | HIGH | `SPI_configFrameNum(num=0)`执行减一编码会下溢 | 公共非法输入可能污染硬件配置 | Public Driver/Wrap要求`frame_count>=1`并失败关闭。 |
| `SPI_DRV_006` | HIGH | 多个Blocking/Polling helper包含无界循环 | 可能阻塞ET-Frame控制通道 | Firmware仅提供一次原子读写/快照动作，deadline由PC控制。 |
| `SPI_DRV_007` | HIGH | 历史测试源码使用`chipSel`，当前Config结构已无该成员 | 历史代码与当前Driver版本冲突 | 不复制旧代码；CS数量和选择能力从当前SVD/Capability重建。 |
| `SPI_DRV_008` | MEDIUM | Driver使用`SPI_MAX_FIFO_DEPTH=16`，生成Capability未发布FIFO深度 | 公共Case无法芯片中立选择边界 | Capability补充`fifo_depth=16`及直接证据。 |
| `SPI_DRV_009` | MEDIUM | `SPI_setConfig`内部以`0x3F`清全部IRQ，缺少含义明确的SDK宏 | 可读性和后续维护风险 | 在测试驱动整改时使用SDK位集合宏，禁止新增Magic Number。 |

Driver Gap不能通过Wrap直接写寄存器绕过。需要测试但正式SDK未暴露的Feature，必须在SDK Driver文件底部测试扩展区域增加清晰命名接口，再由公共Wrap调用。

# 第三章 寄存器与Hardware Truth

## 3.1 实例与系统连接

| Hardware Fact | ET6801事实 |
|---|---|
| SPI实例 | SPI0、SPI1、SPI2、SPI3，共4个 |
| IRQ | 每实例一个独立IRQ |
| Reset | CRG为四个实例提供独立Software Reset位 |
| DMA Request | 每实例提供独立TX和RX DMA Mux Request |
| CS数量 | 当前集成`SER.SER`只有一个有效选择位，按单CS能力发布 |
| Pinmux | 每实例存在多组GPIO备份映射；具体测试接线由Board Profile选择 |

公开Contract不得出现Base Address、IRQn、CRG Bit或GPIO编号；这些值只允许在ET6801 Profile、Board配置和Firmware芯片层中出现。

## 3.2 核心寄存器语义

| Register / Field | Hardware Truth | 公共语义 |
|---|---|---|
| `CTRLR0.DFS` | 帧位宽编码 | `frame_bits` |
| `CTRLR0.FRF` | Motorola SPI、TI SSP、Microwire | `frame_format` |
| `CTRLR0.SCPOL/SCPH` | 时钟极性和相位 | `clock_mode` |
| `CTRLR0.TMOD` | TX_RX、TX_ONLY、RX_ONLY、EEPROM_READ | `transfer_mode` |
| `CTRLR0.SLV_OE` | Target输出控制 | `target_output_enabled` |
| `CTRLR0.SRL` | 片内Shift-register Loopback | `loopback_set` |
| `CTRLR0.SSTE` | Target Select Toggle | `cs_policy=FRAME_TOGGLE` |
| `CTRLR0.SPI_SOFT_MODE` | CS软件控制 | `cs_policy=SOFTWARE_HOLD` |
| `CTRLR0.SSI_IS_MST` | Controller/Target角色 | `role` |
| `CTRLR1.NDF` | 接收帧数减一编码 | `frame_count` |
| `SSIENR.SSIC_EN` | 模块Enable | `CONFIG.ENABLE` |
| `MWCR.*` | Microwire工作模式、方向和Handshake | Frame Format协议配置 |
| `SER.SER` | 片选使能 | CS选择 |
| `BAUDR.SCKDV` | 偶数分频2..65534；0停止SCLK | `bitrate_hz`底层映射 |
| `TXFTLR.TFT/TXFTHR` | TX IRQ Threshold与Start Threshold | FIFO阈值 |
| `RXFTLR.RFT` | RX Full IRQ Threshold | FIFO阈值 |
| `TXFLR/RXFLR` | TX/RX FIFO当前Level | FIFO Snapshot |
| `SR.*` | BUSY、FIFO状态、Target TX Error、Controller Collision | `STATUS.*` |
| `IMR/ISR/RISR` | Mask、Mask后Status、Raw Status | `IRQ.MASK/STATUS/RAW` |
| `TXEICR/RXOICR/RXUICR/MSTICR/ICR` | Source或全局中断清除 | IRQ Clear |
| `DMACR/DMATDLR/DMARDLR` | TX/RX DMA Enable及Watermark | DMA配置 |
| `RX_SAMPLE_DELAY.RSD` | RX采样延迟 | `rx_sample_delay` |
| `IDR/SSIC_VERSION_ID` | 组件Identity | Capability Identity，不单独制造功能Case |

## 3.3 FIFO与IRQ

当前Driver与字段宽度共同表明ET6801 SPI FIFO深度为16帧。IRQ Source包括：

1. TX Empty；
2. TX Overflow；
3. RX Underflow；
4. RX Overflow；
5. RX Full；
6. Multi-Controller Contention。

前5项由`SPI_P1_005`执行独立生命周期验证。Multi-Controller Contention需要安全可控的双Controller争用环境，单独放入`SPI_P2_004`，不能为了避免配测而删除，也不能直接短接推挽输出冒险触发。

## 3.4 当前Capability语义缺口

当前生成文件只表达：

```yaml
instances: [spi0, spi1, spi2, spi3]
features: {ssic: [spi0, spi1, spi2, spi3]}
interrupts: {irq: ...}
identities: {base_address: ..., ssic_comp_version: ...}
```

Audit中尚未分类的关键字段包括`DFS`、`FRF`、`SCPH`、`SCPOL`、`TMOD`、`SRL`、`SSI_IS_MST`、`SSTE`、`NDF`、`SCKDV`、FIFO、IRQ、DMA和RX Sample Delay。因此Capability必须补充：

- `roles`、`frame_formats`、`clock_modes`、`transfer_modes`；
- `frame_bits.min/max`、`fifo_depth`、`cs_count`；
- `bitrate`可配置语义及ET6801已验证上限；
- `irq_sources`、`dma_tx/rx`和Watermark范围；
- `rx_sample_delay.min/max`；
- `internal_loopback`、`target_output_enable`、`controller_collision`。

这些是确定的SVD语义映射缺口，不是Hardware Feature未知。最高稳定Bitrate和RX Sample Delay有效窗口仍需HIL表征，状态为`NEEDS_VERIFICATION`。

# 第四章 历史测试代码分析

## 4.1 历史覆盖与当前归属

| 历史测试思想 | ET6801历史证据 | 当前Case归属 | 当前处理 |
|---|---|---|---|
| 片内回环 | Smoke/Unit源码 | `SPI_P0_002` | 保留为基础Case，但不作为外部链路证据。 |
| 同实例MOSI-MISO外部回接 | `spi_ft.c` | `SPI_P1_001` | 保留并增加SCLK/CS外部Observer，强化说服力。 |
| SPI0 Controller到SPI3 Target | Unit/Functional/FPGA源码 | `SPI_P1_002` | 抽象为Capability选择的双实例，不写死SPI0/SPI3。 |
| 四种Transfer Mode | UnitTest | `SPI_P1_003` | 保留并要求方向、帧数和数据三类Oracle。 |
| FIFO Depth/Level/Threshold | UnitTest | `SPI_P1_004` | 保留；使用Capability发布深度。 |
| TX/RX FIFO IRQ | Unit/Functional | `SPI_P1_005` | 保留并拆清Raw、Status、Mask、Delivery、Clear。 |
| CS High/Low/Toggle | UnitTest | `SPI_P1_006` | 保留并使用外部数字波形作为Oracle。 |
| DMA | Unit/Functional/Smoke | `SPI_P2_001` | 保留；必须证明DMA终态和目标数据。 |
| 25MHz Mode1 | FunctionalTest | `SPI_P1_001`、`SPI_P2_003` | 25MHz作为ET6801候选节点，不写入公共Case固定值。 |
| NOR Flash设备通信 | Smoke device源码 | 不形成首轮公共Case | 属于设备协议集成，不是SPI控制器最小Feature；未来可作为Companion Device Case。 |
| TI SSP/Microwire | SVD有Hardware Truth，历史代码未有效覆盖 | `SPI_P2_002` | 新增通用FPGA Peer协议Case。 |
| Multi-Controller IRQ | SVD有Hardware Truth，历史日志称难触发 | `SPI_P2_004` | 保留，先确认RTL触发语义和安全Bench。 |

## 4.2 历史代码不能直接复用的原因

- 历史源码有`chipSel`等已不属于当前Driver结构的字段；
- 不同历史文件给出的Pinmux/接插件映射并不完全一致；
- 多处固定延时和无界Driver调用不能满足当前统一deadline规则；
- 部分日志显示“PASS”但打印的数据与期望不一致；
- 历史IRQ只看软件标志，不能证明Raw、Mask后Status和真实向量Delivery；
- 历史DMA Case若只看API返回，不能证明DMA目标Buffer和SPI数据链路。

因此只提取Feature和激励思想，重新适配当前稳定Contract，不照抄Case流程。

# 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| SPI_F_001 | SUPPORTED | 4实例均有独立Enable，Driver提供FIFO Reset。 | IMPLEMENTATION_GAP | `SPI_P0_001`, `SPI_P1_004` |
| SPI_F_002 | SUPPORTED | `SSI_IS_MST`选择Controller或Target。 | IMPLEMENTATION_GAP | `SPI_P0_001`, `SPI_P1_002` |
| SPI_F_003 | SUPPORTED | Motorola SPI支持4种CPOL/CPHA组合。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002`, `SPI_P1_006` |
| SPI_F_004 | SUPPORTED | Current Driver合法范围4..16 bit。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_005 | SUPPORTED | TX_RX、TX_ONLY、RX_ONLY、EEPROM_READ。 | IMPLEMENTATION_GAP | `SPI_P1_003` |
| SPI_F_006 | SUPPORTED | 偶数Divider；Driver软件上限50MHz，ET6801稳定上限尚未HIL闭合。 | NEEDS_VERIFICATION | `SPI_P0_001`, `SPI_P1_001`, `SPI_P1_006`, `SPI_P2_003` |
| SPI_F_007 | SUPPORTED | `SRL`提供片内移位链路回环。 | IMPLEMENTATION_GAP | `SPI_P0_002` |
| SPI_F_008 | SUPPORTED | 四个实例均有多组Pinmux；当前Board Mapping未冻结。 | IMPLEMENTATION_GAP | `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_009 | SUPPORTED | 自动、软件保持和Target Select Toggle字段存在。 | IMPLEMENTATION_GAP | `SPI_P1_006` |
| SPI_F_010 | SUPPORTED | `NDF`为帧数减一编码，公共输入必须大于0。 | IMPLEMENTATION_GAP | `SPI_P1_003` |
| SPI_F_011 | SUPPORTED | Current Driver声明FIFO深度16帧。 | IMPLEMENTATION_GAP | `SPI_P1_004` |
| SPI_F_012 | SUPPORTED | TX/RX Threshold和TX Start Threshold均存在；Start读回Driver需修复。 | IMPLEMENTATION_GAP | `SPI_P1_004`, `SPI_P1_005` |
| SPI_F_013 | SUPPORTED | BUSY和TX/RX满空状态完整。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_002`, `SPI_P1_004` |
| SPI_F_014 | SUPPORTED | 五类FIFO IRQ存在；Driver缺Raw/Mask稳定Snapshot。 | IMPLEMENTATION_GAP | `SPI_P1_005` |
| SPI_F_015 | SUPPORTED | 四实例均有TX/RX DMA Request和Watermark。 | IMPLEMENTATION_GAP | `SPI_P2_001` |
| SPI_F_016 | SUPPORTED | 8-bit RX Sample Delay字段存在，有效高速窗口尚未HIL表征。 | NEEDS_VERIFICATION | `SPI_P2_003` |
| SPI_F_017 | SUPPORTED | SVD有Motorola、TI SSP、Microwire；Current Driver只暴露Motorola配置。 | IMPLEMENTATION_GAP | `SPI_P2_002` |
| SPI_F_018 | SUPPORTED | Target Output Enable字段存在。 | IMPLEMENTATION_GAP | `SPI_P1_002` |
| SPI_F_019 | SUPPORTED | Collision状态和Multi-Controller IRQ存在，确定性安全触发语义待闭合。 | NEEDS_VERIFICATION | `SPI_P2_004` |

Feature表描述硬件全貌，不因当前Driver、平台代码或Bench未实现而删除Feature。

# 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| SPI_P0_001 | IMPLEMENTATION_GAP | SPI Wrap、Service、PC Driver和Case尚未实现。 |
| SPI_P0_002 | IMPLEMENTATION_GAP | 同上；片内回环Hardware和Current Driver均具备。 |
| SPI_P1_001 | MAPPING_GAP | 公共代码未实现，且外部MOSI-MISO回接Board Mapping待冻结。 |
| SPI_P1_002 | MAPPING_GAP | 公共代码未实现，且双实例四线Board Mapping待冻结。 |
| SPI_P1_003 | MAPPING_GAP | 复用双实例链路；Transfer Mode Hardware和Driver已具备。 |
| SPI_P1_004 | IMPLEMENTATION_GAP | Capability缺FIFO语义，Start Threshold读回Driver需修复。 |
| SPI_P1_005 | IMPLEMENTATION_GAP | 缺Raw/Mask/Delivery测试Driver接口。 |
| SPI_P1_006 | BENCH_GAP | 需要外部数字Observer验证CS和Clock Mode波形。 |
| SPI_P2_001 | MAPPING_GAP | SPI/DMA代码与双实例物理映射尚未闭合。 |
| SPI_P2_002 | BENCH_GAP | 需要Frame Format Driver扩展和通用协议Peer。 |
| SPI_P2_003 | NEEDS_VERIFICATION | 需要高速Peer表征Bitrate和RX Sample Delay有效窗口。 |
| SPI_P2_004 | NEEDS_VERIFICATION | 需要RTL触发定义和安全的FPGA隔离争用路由。 |

## 6.1 统计

| 类别 | Case数 | Case |
|---|---:|---|
| R0/R1片内自主完成 | 4 | P0_001、P0_002、P1_004、P1_005 |
| R2简单外部接线 | 4 | P1_001、P1_002、P1_003、P2_001 |
| R3通用FPGA/逻辑分析仪 | 4 | P1_006、P2_002、P2_003、P2_004 |
| 总计 | 12 | P0=2、P1=6、P2=4、P3=0 |

首轮开发不能只实现内部回环。至少应同步完成：

1. `SPI_P1_001`：一根MOSI-MISO短接线，加SCLK/CS数字捕获；成本最低，能证明真实PAD路径。
2. `SPI_P1_002`：两个SPI实例四线互连；不依赖外部SPI器件，能证明Controller、Target和双向数据链路。

这两项使用简单接线获得比纯内部回环更强的证据，是首轮最优外部验证组合。

## 6.2 ET6801 Execution Mapping待确认项

| Mapping | 当前事实 | 解除条件 |
|---|---|---|
| 代表实例 | 4实例均存在 | Board Profile选择可达引脚且不占用控制UART的实例。 |
| 单实例外部回接 | 历史FunctionalTest使用过 | 根据当前板卡原理图/接插件重新确认MOSI、MISO、SCLK、CS，不沿用冲突旧映射。 |
| 双实例配对 | 历史主要使用SPI0 Controller + SPI3 Target | 由当前Board Profile冻结逻辑Controller/Target，不写入公共Case。 |
| SCLK/CS Observer | 历史使用逻辑分析仪/FPGA人工观察 | 配置通用波形平台或逻辑分析仪Driver与实际通道。 |
| FPGA协议Peer | 当前平台已有通用波形平台设计，但SPI协议Peer未确认部署 | 完成Motorola/TI/Microwire收发和结构化Observation。 |
| DMA通道 | ET6801为4实例发布TX/RX Request | Capability与Resource Pool发布逻辑Request，不把Mux编号写入Case。 |
| 高速频率上限 | Driver限制50MHz，历史有25MHz用例 | 用外部SCLK和零误码共同表征ET6801已验证上限。 |
| Controller Collision | SVD有状态和IRQ，历史难触发 | 获取RTL触发定义并建立安全FPGA隔离合路后执行。 |

## 6.3 覆盖度结论

12个Case覆盖当前识别的19个SPI Feature，并包含ET6003/ET3101历史需求与ET6801历史源码曾覆盖的控制器核心功能。内部自主Case负责配置、回环、FIFO和IRQ；外部R2 Case负责真实PAD、Controller/Target、Transfer Mode和DMA；R3 Case负责CS波形、协议格式、高速采样和受控争用。

当前结论是“分析和Case Plan闭合”，不是“代码已实现”或“硬件已PASS”。下一阶段应先补Capability语义和公共SPI Driver/Wrap/Service，再实现P0与两个必须的R2外部Case；不得为了减少接线把外部Case改回内部回环。
