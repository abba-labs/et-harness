# ET6801 DMA Chip Analysis & Adaptation Contract

> 本文件只记录 ET6801 DMA 的 Hardware / SDK Driver / Register / Historical Evidence，以及 ET6801 到公共 [`dma.md`](dma.md) 的适配映射。
> 公共 Feature / Case / `ET_CASE_SPEC` / `ET_CASE_REPORT` 真值只在 `dma.md`；本文件不得重新定义公共Case方法和Oracle。
> Hardware Support、Platform Adaptation、Historical HIL 与当前精确 SHA Result 必须分开。

## 第一章 IP分析

### 1.1 IP资源

| 项目 | AHBDMA0 | AHBDMA1 |
|---|---:|---:|
| 普通基地址 | `0x40200000` | `0x40201000` |
| ACC别名地址 | `0x40280000` | `0x40281000` |
| 通道数 | 8 | 8 |
| 通道编号 | CH0～CH7 | CH0～CH7 |
| 寄存器结构大小 | `0x3FC` | `0x3FC` |

ET6801共有2个DMA Controller、16个Channel。NORMAL与`*_ACC`是同一逻辑Controller的两套访问别名，不是4个DMA实例。

每个Controller有5类分类IRQ和1条Combined物理IRQ：

| 类型 | DMA0 IRQn | DMA1 IRQn |
|---|---:|---:|
| TRANSFER_DONE / TFR | 6 | 12 |
| BLOCK_DONE / BLOCK | 7 | 13 |
| SOURCE_TRANSACTION / SRCTRAN | 8 | 14 |
| DESTINATION_TRANSACTION / DSTTRAN | 9 | 15 |
| ERROR / ERR | 10 | 16 |
| COMBINED | 11 | 17 |

DMA SDK Driver不拥有用户业务Callback；平台由公共IRQ Manager绑定DMA Service回调，ISR只读取必要分类状态、清Pending并锁存事件。

### 1.2 稳定数据路径

```text
CPU / Service配置DMA
  -> Source / Destination Address
  -> Width / Address Mode / Burst / Block
  -> M2M / M2P / P2M / P2P
  -> FIFO / Reload / LLI / Gather / Scatter
  -> IRQ / Handshake / Request Interface
  -> Channel Start
  -> DMA Bus Read -> FIFO -> Bus Write
  -> Channel / IRQ / Descriptor终态
```

M2M不需要DMAMUX；M2P/P2M/P2P必须由外设和SYSCTRL Request Route提供硬件请求映射。

### 1.3 多块与Descriptor

- Reload：Block完成后按Source、Destination或双端重新装载地址继续执行。
- LLI：从内存Descriptor读取Source、Destination、Control和Next Descriptor。
- Gather：按Count读取后跳过Source Interval。
- Scatter：按Count写入后跳过Destination Interval。
- DONE：Descriptor完成后由硬件写回完成状态。

### 1.4 IRQ状态机

`TFR/BLOCK/SRCTRAN/DSTTRAN/ERR`均使用8-bit Channel位图：

```text
RAW*      = Mask前原始Pending
STATUS*   = Mask后的有效Pending
MASK*     = 中断Mask配置
CLEAR*    = W1C分类Pending
STATUSINT = 分类中断汇总状态
```

Combined是物理路由，不替代分类RAW/STATUS身份。

### 1.5 TCM地址视图

ET6801 SDK在配置Channel/LLI时包含Core0 ITCM/DTCM CPU Address到DMA Bus Alias的芯片适配逻辑。该事实只能存在于ET6801 Chip Driver/Execution Mapping；公共DMA Case不得硬编码这些地址。

当前P1_016只使用Resource Service普通SRAM Buffer，不能证明TCM Alias。TCM/Core动态证明只由`DMA_P2_014`规划承担，直到CORE1与安全TCM Window映射闭合。

## 第二章 SDK / 当前平台能力

### 2.1 目标SDK文件

| 文件 | 作用 |
|---|---|
| `et6x_ahbdma.h/.c` | DMA配置、状态、TCM地址转换和寄存器访问 |
| `et6x_sysctrl.h/.c` | 外设DMA Request Route |
| `et6x_interrupt.h/.c` | 芯片物理IRQ控制 |

当前分析记录的 `et6x_ahbdma.c` SHA256：
`018CD811BFA3774BEF4622E7E7C2D5CEF08FD5DD36A80A93A32AF74098067C1D`。

### 2.2 SDK稳定能力

- 8/16/32-bit transfer width。
- 1～4095 item Block Count。
- Burst 1/4/8/16/32/64/128/256 item。
- Increment/Decrement/Fixed地址模式。
- M2M/M2P/P2M/P2P。
- Priority 0～7、FIFO Mode、Request Interface 0～7。
- Reload、LLI、Source Gather、Destination Scatter、DONE写回。
- 分类IRQ状态、Mask、Clear。
- TCM CPU Address到DMA Alias转换由ET6801 SDK负责。

### 2.3 Gather / Scatter 已修复历史问题

SVD/CMSIS：

```text
SGC / DSC Count    = 12 bit -> max 0xFFF
SGI / DSI Interval = 20 bit -> max 0xFFFFF
```

历史驱动曾把两个上限写反，2026-07-26已修复。历史Keil编译PASS只证明构建，不代表当前SHA DMA HIL PASS。

### 2.4 当前公共平台暴露情况

| 能力 | 当前公共平台状态 | Human Review结论 |
|---|---|---|
| Component/Capability Snapshot | 已暴露 | P0_001 RECORD_ONLY；FIFO精确动态Depth仍Gap |
| Channel Status / Snapshot | 已暴露 | 可用于FREE、FIFO_EMPTY、Address与CTL/CFG配置证明 |
| RAW/STATUS/MASK/CLEAR | 已暴露Snapshot/Control | P1_006 RECORD_ONLY |
| Combined IRQ Route | 已暴露 | P2_004 RECORD_ONLY |
| Software Handshake Request | 已暴露 | P2_011逐Item因果证明已闭合 |
| Hardware/Software Handshake Select | 已暴露 | P2_012无Request负对照已闭合 |
| Handshake Polarity配置 | 配置字段存在 | 缺可控极性Request Source，F027保持Gap |
| Max AMBA Burst | 尚未形成完整公共Proof | P3_003 PLAN |
| AHB Master Select | 尚未形成完整公共Proof | P3_001 PLAN |
| Protection | 尚未形成安全Proof | P3_002 NEEDS_VERIFICATION |
| Flow Controller | 尚缺受控Peer | P3_004 PLAN |
| Low-Power Timeout | 尚缺完整状态/唤醒Contract | P3_005 PLAN |
| DFT/Test Slave | 仅设计批准后允许 | P3_006 NEEDS_VERIFICATION |

## 第三章 Register / Field Truth

### 3.1 Channel Cluster

ET6801 SVD中每个Channel由 `CHANNELX_CONFIG_CH<n>` Cluster承载：

| 公共含义 | ET6801 Register.Field |
|---|---|
| Source Address | `SARX.SAR` |
| Destination Address | `DARX.DAR` |
| Linked List Address | `LLPX.LOC`（地址按SVD定义还原） |
| Source Burst | `CTLX_L32.SRC_MSIZE` |
| Destination Burst | `CTLX_L32.DEST_MSIZE` |
| Source/Destination Width | `CTLX_L32.SRC_TR_WIDTH / DST_TR_WIDTH` |
| Source/Destination Address Mode | `CTLX_L32.SINC / DINC` |
| Transfer Type | `CTLX_L32.TT_FC` |
| LLI Enable | `CTLX_L32.LLP_SRC_EN / LLP_DST_EN` |
| Block Size | `CTLX_H32.BLOCK_TS` |
| Descriptor DONE | `CTLX_H32.DONE` |
| Channel Suspend | `CFGX_L32.CH_SUSP` |
| FIFO Empty | `CFGX_L32.FIFO_EMPTY` |
| Priority | `CFGX_L32.CH_PRIOR` |
| Handshake Select | `CFGX_L32.HS_SEL_SRC / HS_SEL_DST` |
| Handshake Polarity | `CFGX_L32.SRC_HS_POL / DST_HS_POL` |
| Max AMBA Burst | `CFGX_L32.MAX_ABRST` |
| Source/Destination Request Interface | `CFGX_H32.SRC_PER / DEST_PER` |
| Protection | `CFGX_H32.PROTCTL` |
| FIFO Mode | `CFGX_H32.FIFO_MODE` |
| Flow Controller Mode | `CFGX_H32.FCMODE` |
| Source Gather | `SGRX.SGC / SGI` |
| Destination Scatter | `DSRX.DSC / DSI` |

### 3.2 Controller公共寄存器

| 分组 | ET6801 Register.Field |
|---|---|
| 原始分类IRQ | `RAWTFR.RAW`, `RAWBLOCK.RAW`, `RAWSRCTRAN.RAW`, `RAWDSTTRAN.RAW`, `RAWERR.RAW` |
| 有效分类IRQ | `STATUSTFR.STATUS`, `STATUSBLOCK.STATUS`, `STATUSSRCTRAN.STATUS`, `STATUSDSTTRAN.STATUS`, `STATUSERR.STATUS` |
| IRQ Mask | `MASKTFR/MASKBLOCK/MASKSRCTRAN/MASKDSTTRAN/MASKERR.INT_MASK` |
| IRQ Clear | `CLEARTFR/CLEARBLOCK/CLEARSRCTRAN/CLEARDSTTRAN/CLEARERR` |
| Combined Status | `STATUSINT.TFR/BLOCK/SRCT/DSTT/ERR` |
| Software Handshake | `REQSRCREG`, `REQDSTREG`, `SGLRQDSTREG`, `LSTSRCREG`, `LSTDSTREG` |
| Module Enable | `DMACFGREG.DMA_EN` |
| Channel Enable | `CHENREG.CH_EN` |
| DMA Identity | `DMAIDREG.DMA_ID` |
| Component Identity | `DMACOMPSID.DMA_COMP_TYPE` |
| Channel Capability | `DMA_COMP_PARAMS_CH<n>` |
| Low Power Timeout | `DMALPTIMEOUTREG.DMA_LP_TIMEOUT` |
| Test Slave | `DMATESTREG.TEST_SLV_IF` |

### 3.3 FIFO Depth静态事实

生成Capability当前记录：

```text
DMA0/1 CH0, CH1 -> fifo_depth = 64
DMA0/1 CH2..CH7 -> fifo_depth = 16
all channel max_block_size = 4095
```

这是SVD/Capability静态硬件事实。当前没有独立动态Oracle证明“物理FIFO深度恰为N”，因此F033只对ID/Channel Capability形成动态Evidence，Exact FIFO Physical Depth保持`fifo_depth_dynamic_proof_gap`。

## 第四章 Historical Evidence

历史UnitTest/FPGATest对两个Controller包含通道遍历、Priority、Reload/BLOCK、UART/SPI外设DMA、ERR、LLI、P2P、最大Block、Gather/Scatter等思路，但历史入口大量被注释、存在固定延时/无限等待/ISR业务逻辑以及板级漂移，不能作为当前Formal Case。

2026-08-02与2026-08-03曾执行ET6801 FPGA DMA HIL；2026-08-03报告记录当时可安全执行实例 `68 PASS / 0 FAIL / 9 SKIP`，包括M2M/M2P/P2M/P2P、TFR/BLOCK/SRC/DST/COMBINED、LLI、Gather/Scatter等。

这些只属于Historical Evidence：

```text
Historical HIL != current exact SHA HIL
```

当前精确SHA无真机执行时必须报告 `HIL NOT_EXECUTED / NOT_VERIFIED`。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| DMA_F_001 | SUPPORTED | 2个逻辑Controller | ADAPTED | `DMA_P0_001`, `DMA_P3_007` |
| DMA_F_002 | SUPPORTED | 每Controller 8 Channel | ADAPTED | `DMA_P0_001`, `DMA_P0_002`, `DMA_P1_001`, `DMA_P3_007` |
| DMA_F_003 | SUPPORTED | `DMACFGREG.DMA_EN` | ADAPTED | `DMA_P0_002`, `DMA_P2_015` |
| DMA_F_004 | SUPPORTED | Channel lifecycle | ADAPTED | `DMA_P0_002`, `DMA_P2_015` |
| DMA_F_005 | SUPPORTED | FREE/FIFO_EMPTY | ADAPTED | `DMA_P0_002`, `DMA_P1_001`, `DMA_P2_015`, `DMA_P3_007` |
| DMA_F_006 | SUPPORTED | Free Channel查询 | ADAPTED | `DMA_P0_002` |
| DMA_F_007 | SUPPORTED | M2M/M2P/P2M/P2P | ADAPTED | `DMA_P1_014`, `DMA_P1_016`, `DMA_P2_008`, `DMA_P2_009`, `DMA_P2_010`, `DMA_P2_015`, `DMA_P3_007` |
| DMA_F_008 | SUPPORTED | 8/16/32-bit | ADAPTED | `DMA_P1_014`, `DMA_P1_017`, `DMA_P3_007` |
| DMA_F_009 | SUPPORTED | inc/dec/fixed | ADAPTED | `DMA_P1_014`, `DMA_P1_017` |
| DMA_F_010 | SUPPORTED | Burst 1~256 | ADAPTED | `DMA_P1_015`, `DMA_P1_017`, `DMA_P3_007` |
| DMA_F_011 | SUPPORTED | Block 1~4095 | ADAPTED | `DMA_P1_015`, `DMA_P1_017` |
| DMA_F_012 | SUPPORTED | Priority 0~7 | IMPLEMENTATION_GAP | `DMA_P1_002` |
| DMA_F_013 | SUPPORTED | Single/Half-Depth | ADAPTED | `DMA_P1_010`, `DMA_P3_007` |
| DMA_F_014 | SUPPORTED | Request Interface 0~7 | ADAPTED | `DMA_P1_017`, `DMA_P2_008`, `DMA_P2_009`, `DMA_P2_010` |
| DMA_F_015 | SUPPORTED | Suspend/Resume | IMPLEMENTATION_GAP | `DMA_P1_003` |
| DMA_F_016 | SUPPORTED | Reload Source/Destination | ADAPTED | `DMA_P1_007` |
| DMA_F_017 | SUPPORTED | LLI + error recovery未闭合 | PARTIAL_ADAPTATION | `DMA_P2_001`, `DMA_P2_002`, `DMA_P2_003` |
| DMA_F_018 | SUPPORTED | Source Gather | ADAPTED | `DMA_P1_008`, `DMA_P1_017` |
| DMA_F_019 | SUPPORTED | Destination Scatter | ADAPTED | `DMA_P1_009`, `DMA_P1_017` |
| DMA_F_020 | SUPPORTED | DONE writeback | ADAPTED | `DMA_P1_011` |
| DMA_F_021 | SUPPORTED | TFR/BLOCK/SRC/DST已有；ERR安全刺激未闭合 | PARTIAL_ADAPTATION | `DMA_P1_004`, `DMA_P1_005`, `DMA_P1_016`, `DMA_P2_005`, `DMA_P2_006`, `DMA_P2_007` |
| DMA_F_022 | SUPPORTED | 8-bit Channel IRQ位图 | ADAPTED | `DMA_P1_004`, `DMA_P1_005`, `DMA_P1_006`, `DMA_P1_016` |
| DMA_F_023 | SUPPORTED | Core/TCM Alias需Execution Mapping | PARTIAL_ADAPTATION | `DMA_P2_014` |
| DMA_F_024 | SUPPORTED | Combined物理IRQ | ADAPTED | `DMA_P2_004` |
| DMA_F_025 | SUPPORTED | RAW/STATUS/MASK/CLEAR | ADAPTED | `DMA_P1_006` |
| DMA_F_026 | SUPPORTED | Software Request API与逐Item因果进度证明均已适配 | ADAPTED | `DMA_P2_011` |
| DMA_F_027 | SUPPORTED | active-high/low字段存在，但无可控极性源 | PARTIAL_ADAPTATION | `OPEN GAP` |
| DMA_F_028 | SUPPORTED | Hardware/Software Select | ADAPTED | `DMA_P2_011`, `DMA_P2_012` |
| DMA_F_029 | SUPPORTED | `CFGX_L32.MAX_ABRST` | IMPLEMENTATION_GAP | `DMA_P3_003` |
| DMA_F_030 | SUPPORTED | SMS/DMS | IMPLEMENTATION_GAP | `DMA_P3_001` |
| DMA_F_031 | SUPPORTED | `CFGX_H32.PROTCTL` | IMPLEMENTATION_GAP | `DMA_P3_002` |
| DMA_F_032 | SUPPORTED | `CFGX_H32.FCMODE` | IMPLEMENTATION_GAP | `DMA_P3_004` |
| DMA_F_033 | SUPPORTED | ID/Channel能力已适配；Exact FIFO Depth缺动态Oracle | PARTIAL_ADAPTATION | `DMA_P0_001` |
| DMA_F_034 | SUPPORTED | `DMALPTIMEOUTREG` | IMPLEMENTATION_GAP | `DMA_P3_005` |
| DMA_F_035 | SUPPORTED | `DMATESTREG`仅DFT批准后测试 | IMPLEMENTATION_GAP | `DMA_P3_006` |

Feature Platform汇总：`ADAPTED=22; PARTIAL_ADAPTATION=5; IMPLEMENTATION_GAP=8`。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| DMA_P0_001 | ADAPTED | Formal Case存在；需按新Contract补Canonical Evidence；FIFO exact-depth gap保留 |
| DMA_P0_002 | ADAPTED | CASE_CHANGE已闭合：两轮重新使能、FIFO_EMPTY与再次分配证明已实现 |
| DMA_P1_001 | ADAPTED | RECORD_ONLY：硬件动作充分，补Evidence |
| DMA_P1_002 | IMPLEMENTATION_GAP | priority_arbitration_observer_gap |
| DMA_P1_003 | IMPLEMENTATION_GAP | deterministic_inflight_window_gap |
| DMA_P1_004 | ADAPTED | RECORD_ONLY：TFR/data/free已取得 |
| DMA_P1_005 | ADAPTED | RECORD_ONLY：BLOCK/data/free已取得 |
| DMA_P1_006 | ADAPTED | RECORD_ONLY：before/masked/cleared/enabled快照已取得 |
| DMA_P1_007 | ADAPTED | RECORD_ONLY：Reload/地址/Block IRQ已有 |
| DMA_P1_008 | ADAPTED | RECORD_ONLY：Gather布局/Guard已有 |
| DMA_P1_009 | ADAPTED | RECORD_ONLY：Scatter布局/Guard已有 |
| DMA_P1_010 | ADAPTED | CASE_CHANGE已闭合：FIFO_MODE通过目标侧归一Snapshot完成硬件读回 |
| DMA_P1_011 | ADAPTED | RECORD_ONLY：DONE before/after与数据已有 |
| DMA_P1_014 | ADAPTED | RECORD_ONLY：Width/Address Mode数据Oracle已有 |
| DMA_P1_015 | ADAPTED | CASE_CHANGE已闭合：Block/Burst通过目标侧归一Snapshot完成硬件读回 |
| DMA_P1_016 | ADAPTED | DOC_ONLY：仅SRAM M2M+TFR；已从F023 TCM解绑 |
| DMA_P1_017 | ADAPTED | RECORD_ONLY：7组拒绝+合法恢复已有 |
| DMA_P2_001 | ADAPTED | RECORD_ONLY：有限LLI数据与Descriptor已有 |
| DMA_P2_002 | ADAPTED | RECORD_ONLY：单侧LLI数据已有 |
| DMA_P2_003 | IMPLEMENTATION_GAP | safe_lli_fault_window_gap |
| DMA_P2_004 | ADAPTED | RECORD_ONLY：Combined Route/TFR/data已有 |
| DMA_P2_005 | ADAPTED | RECORD_ONLY：P2M+SRC/TFR已有 |
| DMA_P2_006 | ADAPTED | RECORD_ONLY：M2P+DST/TFR+Peer Capture已有 |
| DMA_P2_007 | IMPLEMENTATION_GAP | safe_bus_fault_window_gap |
| DMA_P2_008 | ADAPTED | RECORD_ONLY：1/17/257 M2P Peer数据已有 |
| DMA_P2_009 | ADAPTED | RECORD_ONLY：1/17/257 P2M数据已有 |
| DMA_P2_010 | ADAPTED | RECORD_ONLY：P2P Peer数据已有 |
| DMA_P2_011 | ADAPTED | CASE_CHANGE已闭合：无Request停滞与逐Item Request地址进度证明已实现 |
| DMA_P2_012 | ADAPTED | CASE_CHANGE已闭合：Software Mode负对照已实现；Polarity仍不属于本Case |
| DMA_P2_013 | MAPPING_GAP | NORMAL/ACC行为存在；公共Feature身份/跨芯片适用条件待冻结 |
| DMA_P2_014 | MAPPING_GAP | CORE1 + safe TCM window + CPU/DMA Alias Mapping未闭合 |
| DMA_P2_015 | ADAPTED | DOC_ONLY：绑定已有Module/Channel/M2M恢复语义，不新增Reset Feature |
| DMA_P3_001 | IMPLEMENTATION_GAP | master_routing_contract_gap |
| DMA_P3_002 | NEEDS_VERIFICATION | permission_model_verification_gap |
| DMA_P3_003 | IMPLEMENTATION_GAP | max_amba_burst_contract_gap |
| DMA_P3_004 | IMPLEMENTATION_GAP | flow_controller_peer_gap |
| DMA_P3_005 | IMPLEMENTATION_GAP | low_power_contract_gap |
| DMA_P3_006 | NEEDS_VERIFICATION | dft_authorization_gap |
| DMA_P3_007 | ADAPTED | RECORD_ONLY：20轮行为充分，需解决中途FAIL Evidence生命周期 |

Case Platform汇总：`ADAPTED=27; IMPLEMENTATION_GAP=8; MAPPING_GAP=2; NEEDS_VERIFICATION=2`。

## 第七章 Stable Endpoint -> ET6801 Register / Field Mapping

本章只做只读显示映射，不改变公共Canonical Observation身份。

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `DMA_COMPONENT.DMA_ID` | `DMAIDREG.DMA_ID` | Controller身份 |
| `DMA_COMPONENT.COMPONENT_ID` | `DMACOMPSID.DMA_COMP_TYPE` | 组件类型/身份 |
| `DMA_COMPONENT.CHANNEL_PARAMS[n]` | `DMA_COMP_PARAMS_CH<n>` | 逐Channel能力参数 |
| `DMA_CHANNEL_STATUS.FREE` | `CHENREG.CH_EN[n] == 0` | 公共Driver归一为Free Bool |
| `DMA_CHANNEL_STATUS.FIFO_EMPTY` | `CHANNELX_CONFIG_CH<n>.CFGX_L32.FIFO_EMPTY` | FIFO Empty硬件状态 |
| `DMA_CHANNEL.SOURCE_ADDRESS` | `CHANNELX_CONFIG_CH<n>.SARX.SAR` | 当前Source Address |
| `DMA_CHANNEL.DESTINATION_ADDRESS` | `CHANNELX_CONFIG_CH<n>.DARX.DAR` | 当前Destination Address |
| `DMA_CHANNEL.LINKED_LIST_ADDRESS` | `CHANNELX_CONFIG_CH<n>.LLPX.LOC` | Descriptor地址字段 |
| `DMA_CHANNEL_CFG.FIFO_MODE` | `CHANNELX_CONFIG_CH<n>.CFGX_H32.FIFO_MODE` | Single/Half-Depth配置证明 |
| `DMA_CHANNEL_CTL.SOURCE_BURST` | `CHANNELX_CONFIG_CH<n>.CTLX_L32.SRC_MSIZE` | Source Burst编码 |
| `DMA_CHANNEL_CTL.DESTINATION_BURST` | `CHANNELX_CONFIG_CH<n>.CTLX_L32.DEST_MSIZE` | Destination Burst编码 |
| `DMA_CHANNEL_CTL.BLOCK_SIZE` | `CHANNELX_CONFIG_CH<n>.CTLX_H32.BLOCK_TS` | Block Transfer Count |
| `LLI_DESCRIPTOR.DONE` | Descriptor `CTL_H.DONE` / `CTLX_H32.DONE`同语义位 | 完成写回 |
| `IRQ_RAW.TRANSFER_DONE` | `RAWTFR.RAW[n]` | 原始TFR Pending |
| `IRQ_RAW.BLOCK_DONE` | `RAWBLOCK.RAW[n]` | 原始BLOCK Pending |
| `IRQ_RAW.SOURCE_TRANSACTION` | `RAWSRCTRAN.RAW[n]` | 原始Source Transaction Pending |
| `IRQ_RAW.DESTINATION_TRANSACTION` | `RAWDSTTRAN.RAW[n]` | 原始Destination Transaction Pending |
| `IRQ_RAW.ERROR` | `RAWERR.RAW[n]` | 原始Error Pending |
| `IRQ_STATUS.TRANSFER_DONE` | `STATUSTFR.STATUS[n]` | Mask后TFR状态 |
| `IRQ_STATUS.BLOCK_DONE` | `STATUSBLOCK.STATUS[n]` | Mask后BLOCK状态 |
| `IRQ_STATUS.SOURCE_TRANSACTION` | `STATUSSRCTRAN.STATUS[n]` | Mask后SRC状态 |
| `IRQ_STATUS.DESTINATION_TRANSACTION` | `STATUSDSTTRAN.STATUS[n]` | Mask后DST状态 |
| `IRQ_STATUS.ERROR` | `STATUSERR.STATUS[n]` | Mask后ERR状态 |
| `IRQ_MASK.TRANSFER_DONE` | `MASKTFR.INT_MASK[n]` | TFR Mask |
| `IRQ_MASK.BLOCK_DONE` | `MASKBLOCK.INT_MASK[n]` | BLOCK Mask |
| `IRQ_MASK.SOURCE_TRANSACTION` | `MASKSRCTRAN.INT_MASK[n]` | SRC Mask |
| `IRQ_MASK.DESTINATION_TRANSACTION` | `MASKDSTTRAN.INT_MASK[n]` | DST Mask |
| `IRQ_MASK.ERROR` | `MASKERR.INT_MASK[n]` | ERR Mask |
| `IRQ_COMBINED.STATUS` | `STATUSINT.TFR/BLOCK/SRCT/DSTT/ERR` | Combined分类汇总寄存器 |
| `DMA_CAPABILITIES.*` | Runtime DMA Service + ET6801 Chip Config / `DMA_COMP_PARAMS_*` | 目标侧能力快照，不冒充一个寄存器 |
| `ISR.LATCHED.<Event>` | DMA Service ISR latch | Service/ISR事实，不映射成当前Pending寄存器 |
| `ISR.EVENT_COUNT` | DMA Service计数 | Measurement，不是硬件寄存器 |
| `DMA_SOURCE_DATA` / `DMA_DESTINATION_DATA` | Resource/Memory实际读回 | Memory Endpoint，不是DMA寄存器 |
| `PEER_UART.RX_CAPTURE` | UART Peer Capture | Peer Endpoint，不是DMA寄存器 |

### 7.1 映射边界

- Canonical `endpoint/source/value`保持公共稳定语义；报告层只能基于当前`chip_id`补充上表实际寄存器/Field标签。
- Service latch、event_count、Route ID、Peer Capture、Memory数据不得标记成DMA寄存器。
- P1_010/P1_015若实现配置读回，必须经公共Driver/Service稳定接口取得，不允许PC Case直接读取上述寄存器。
- F023 TCM映射需要单独Execution Mapping；本章的普通Channel寄存器映射不构成TCM PASS。

## 第八章 历史文档生成时验证状态

以下内容只记录本文初次生成时的验证边界，不代表当前测试状态；当前结论只读取文末唯一`ET_CHIP_TEST_STATUS`区域：

```text
SOURCE / DESIGN REVIEW: CLOSED
DMA SCOPED SOFTWARE GATE: PASS @ carrier 288b45b785b25138840235fcc0e26366c8642bb5
REPOSITORY-WIDE SOFTWARE GATE: NOT GREEN / unrelated baseline formatting debt
review_code exact-SHA CI: NOT_VERIFIED
FPGA HIL: NOT_EXECUTED / NOT_VERIFIED
Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
```

### 8.1 同步规则

- ET6801 Feature/options/limits/实例/IRQ/Chip Driver/Execution Mapping变化必须同步本文件。
- 适配状态变化必须同步公共`dma.md` Chip Adaptation Summary。
- 本文件不保存`ET_CASE_SPEC`/`ET_CASE_PLAN`机器块，避免形成第二份公共Case真值。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:22 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:12 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/dma/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 28 | 28 | 28 | 0 | 0 | 0 | 88 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |
<!-- ET_CHIP_TEST_STATUS_END -->
