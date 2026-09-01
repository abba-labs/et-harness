# ET6801 CRC Chip Analysis & Adaptation Contract

> 本文件只记录 ET6801 CRC 的 Hardware / Register / SDK Driver / Historical Evidence，以及 ET6801 到公共 CRC Feature/Case Contract 的映射。
> 公共 Feature / Case / `ET_CASE_SPEC` / `ET_CASE_REPORT` 真值位于 [`crc.md`](crc.md)。
> `SUPPORTED` / `ADAPTED` 只表示硬件事实和自动化链路已经建立，不代表当前精确 SHA 的 FPGA/Silicon HIL 已 PASS。

## 第一章：IP 分析——应用场景与工作原理

### 1.1 分析基线与资料清单

#### 1.1.1 当前权威资料

ET6801 CRC 结论由以下资料交叉确认：

```text
ET6801.svd
ET6x_Driver/Inc/et6x_crc.h
ET6x_Driver/Src/et6x_crc.c
firmware/wrap/src/et_crc_wrap.c
firmware/services/src/et_crc_service.c
pc/et_test_platform/drivers/crc/**
pc/et_test_platform/test_cases/crc/**
ET6801 历史 FunctionalTest / UnitTest / FPGATest / PerformanceTest
```

当前公共 Contract 与 Formal Case 以 `review_code` 当前源码为实现事实；历史源码只用于追溯测试意图和独立向量，不覆盖当前实现。

#### 1.1.2 Source Coverage

| 资料根 | 状态 | 当前用途 |
|---|---|---|
| ET6801 SVD | FOUND | Register、Field、IRQ、Base Address、Feature Truth |
| ET6801 SDK CRC Driver | FOUND | CRC8/16/32访问方式、Length、Result、FIFO、IRQ API |
| ET6801 Verification Test | FOUND | 历史固定向量、FIFO、BUS/LENGTH/CHECK错误刺激 |
| ET6801 Performance Test | FOUND | CPU/DMA目标侧周期测量边界 |
| 3101/6003 CRC历史资料 | FOUND | 跨代测试意图参考；不单独证明ET6801 Hardware SUPPORTED |
| 当前平台 CRC Driver/Service/Wrap/Case | FOUND | 当前自动化实现、Evidence与清理语义 |

当前没有以不可访问资料推导确定硬件结论的 Source Root。

### 1.2 CRC 解决的问题和应用场景

CRC（Cyclic Redundancy Check）用于对数据块计算循环冗余校验码，以发现传输或存储过程中产生的比特错误。ET6801 CRC IP 把常用 CRC 参数实现为可配置硬件数据路径，主要能力包括：

- CRC32 / CRC16 / CRC8 三种 Kernel；
- Polynomial、Initial Seed；
- ByteSwap、RefIn、RefOut、XorOut；
- Result Check；
- LENGTH 与 Auto Length Reload；
- FIFO Threshold 与 Overflow；
- CPU / DMA 输入；
- BUS_ERR / LENGTH_ERR / CHECK_ERR 中断源；
- 目标侧 DWT 周期测量 Test Driver Extension。

典型应用包括固件/参数区完整性校验、通信帧校验、DMA数据块CRC加速和量产自检。

### 1.3 实例、地址、IRQ 与关键寄存器

| 项目 | ET6801 当前事实 | 证据 |
|---|---|---|
| 实例 | `crc0` / SVD peripheral `CRC` | 当前仅1个实例 |
| Base Address | `0x40206000` | `CRC.baseAddress` |
| IRQ | `CRC_IRQn = 4` | SVD interrupt `CRC` |
| CPU/DMA输入 | `IR.CRC_IR` | CPU typed write / DMA M2P |
| 结果 | `RES.POST_CRC_CAL` | CRC8/16/32自然宽度有效 |
| Length | `LENGTH.CRC_LENGTH` | 硬件输入事务计数 |
| FIFO Threshold | `FIFO_TRHD.CRC_FIFO_TRHD` | SDK最大阈值8 |
| FIFO Overflow | `FIFO_OVF.CRC_FIFO_OVF_RPT` | 硬件Overflow事实 |
| IRQ Source | BUS_ERR / LENGTH_ERR / CHECK_ERR | raw/status/enable/mask/force/clear |

#### 1.3.1 关键寄存器地图

| Offset | Register | Field / 作用 |
|---:|---|---|
| `0x0004` | `MODULE_EN` | `CRC_EN` |
| `0x0008` | `CTRL` | Kernel、ByteSwap、XorOut、RefOut、RefIn、ALR、Check |
| `0x000C` | `POLY` | `CRC_POLY` |
| `0x0010` | `FIFO_TRHD` | `CRC_FIFO_TRHD` |
| `0x0014` | `IR` | `CRC_IR` |
| `0x0018` | `INI` | `CRC_INI` |
| `0x001C` | `CHECK` | `CRC_CHECK` |
| `0x0020` | `LENGTH` | `CRC_LENGTH` |
| `0x0024` | `INT_EN` | BEF / LEF / CMF Enable |
| `0x0028` | `INT_MASK` | BEF / LEF / CMF Mask |
| `0x002C` | `INT_FORCE_IND` | BEF / LEF / CMF Force |
| `0x0030` | `INT_CLR` | BEF / LEF / CMF Clear |
| `0x0034` | `INT_RAW_RPT` | BEF / LEF / CMF Raw |
| `0x0038` | `INT_STATUS_RPT` | BEF / LEF / CMF Effective Status |
| `0x003C` | `RES` | `POST_CRC_CAL` |
| `0x0040` | `FIFO_OVF` | `CRC_FIFO_OVF_RPT` |

#### 1.3.2 公共稳定 Observation → ET6801 实际端点映射

> 本表只用于最终报告的只读显示增强。Canonical Observation 仍保存公共稳定 endpoint；映射不得反向修改 `source / endpoint / value`。

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `RESULT.CRC` | `RES.POST_CRC_CAL` | CRC8/16/32最终硬件结果 |
| `LENGTH.REMAINING_INPUT_COUNT` | `LENGTH.CRC_LENGTH` | 当前剩余输入事务数 / ALR重载值 |
| `FIFO.OVERFLOW` | `FIFO_OVF.CRC_FIFO_OVF_RPT` | FIFO Overflow硬件状态 |
| `IRQ_RAW.BUS_ERROR` | `INT_RAW_RPT.CRC_BEF_INT_RAW_RPT` | BUS_ERR Mask前Raw状态 |
| `IRQ_RAW.LENGTH_ERROR` | `INT_RAW_RPT.CRC_LEF_INT_RAW_RPT` | LENGTH_ERR Mask前Raw状态 |
| `IRQ_RAW.CHECK_ERROR` | `INT_RAW_RPT.CRC_CMF_INT_RAW_RPT` | CHECK_ERR Mask前Raw状态 |
| `IRQ_STATUS.BUS_ERROR` | `INT_STATUS_RPT.CRC_BEF_INT_STATUS_RPT` | BUS_ERR Mask后有效状态 |
| `IRQ_STATUS.LENGTH_ERROR` | `INT_STATUS_RPT.CRC_LEF_INT_STATUS_RPT` | LENGTH_ERR Mask后有效状态 |
| `IRQ_STATUS.CHECK_ERROR` | `INT_STATUS_RPT.CRC_CMF_INT_STATUS_RPT` | CHECK_ERR Mask后有效状态 |
| `TIMING.CYCLE_COUNT` | `DWT.CYCCNT` | CRC Test Driver目标侧周期计数边界 |

以下公共 endpoint 不伪装成 CRC 寄存器：

- `ISR.LATCHED.<Source>` / `ISR.LAST_RAW.<Source>`：Firmware CRC Service ISR 保存的结构化事实；
- `DMA_TIMING.COMPLETE` / `DMA_CHANNEL_STATUS.FREE`：属于 DMA 执行域；
- `CRC_CAPABILITIES`：属于 Firmware Runtime Service 只读能力快照。

### 1.4 输入—内部处理—输出数据路径

```text
Resource Byte Stream
  -> CPU typed access / DMA M2P
  -> IR.CRC_IR
  -> ByteSwap / RefIn
  -> FIFO
  -> CRC8/16/32 Kernel
  -> RefOut / XorOut
  -> RES.POST_CRC_CAL

LENGTH.CRC_LENGTH -> 输入事务计数 / ALR
CHECK.CRC_CHECK   -> Result Compare -> CHECK_ERR
IR访问宽度错误    -> BUS_ERR
Length耗尽继续输入 -> LENGTH_ERR
```

DMA 不属于 CRC Driver 内部职责。当前跨IP顺序固定在 Formal Case：

```text
CRC Case
-> Resource准备Payload
-> CRC配置与Length
-> SYSCTRL配置DMA Request Route
-> DMA配置Memory-to-Peripheral
-> DMA启动/等待Free
-> CRC读取Result/Length
-> PC独立Golden判定
```

### 1.5 Kernel、Polynomial、Seed 与数据变换

#### 1.5.1 Kernel

`CTRL.CRC_KERNEL_SEL` 支持：

```text
CRC32
CRC16
CRC8
```

当前公共 `CrcMode` 使用自然宽度 `32 / 16 / 8`，不暴露芯片SDK枚举值。

#### 1.5.2 Polynomial / Initial Seed

- CRC32使用32-bit自然值；
- CRC16/8公共API仍使用自然宽度值，Driver内部负责写入硬件对应位置；
- 禁止在公共Case中写ET6801寄存器移位细节。

#### 1.5.3 ByteSwap / RefIn / RefOut / XorOut

稳定 PC Golden 语义为：

```text
Resource Byte Stream
-> 按实际IR access width分组
-> ByteSwap（仅完整CRC16/32 access unit）
-> RefIn（每个输入Byte）
-> MSB-first CRC Kernel
-> RefOut（当前Kernel自然宽度）
-> XorOut（ALL_ZERO / 当前宽度ALL_ONE）
-> width mask
```

CRC8 不接受 `byte_swap=true`。CRC16/32 remainder Byte 通过8-bit access输入，不与前一完整单元跨界ByteSwap。

### 1.6 LENGTH / Remainder / Auto Length Reload

当前 Wrap 将公共 `length_bytes` 转换为硬件输入事务数：

```text
input_count = length_bytes // width_bytes + length_bytes % width_bytes
```

因此：

- CRC32 8/9/10/11-byte → 2/3/4/5个输入事务；
- CRC16 8/9-byte → 4/5个输入事务；
- `DATA_LENGTH_GET` 直接返回 `CRC_getDataLength()` 硬件事实，不转换回Byte；
- ALR开启后，完成一轮输入后 `LENGTH.CRC_LENGTH` 自动恢复到原输入事务数。

`CRC_P1_007` 已按当前审核Contract显式执行 `set -> readback -> calculate -> final remaining`，同时证明 F009 remainder 与 F010 LENGTH programming/readback。

### 1.7 FIFO

当前权威资料证明：

- CRC存在FIFO结构；
- `FIFO_TRHD`支持阈值配置，ET6801当前SDK限制为0~8；
- `FIFO_OVF`提供Overflow状态；
- ET6801 RTL权威语义为`dma_req = (fifo_cnt <= cfg_crc_fifo_trhd)`，因此`FIFO_TRHD`控制DMA Request水位，不控制CRC Result更新节拍；
- `FIFO_OVF`在当前FPGA实现中已由人工确认存在硬件问题。

但必须区分：

```text
FIFO Threshold寄存器可配置
FIFO Overflow/Recovery Case已实现
≠
FIFO Threshold DMA Request边界已动态证明
FIFO Physical Depth已被精确动态测得
```

因此 `CRC_F_012 FIFO Physical Depth` 与 `CRC_F_013 FIFO Threshold` 当前状态分别保持：

```text
Hardware: SUPPORTED
Platform: PARTIAL_ADAPTATION
Gap: dynamic_fifo_depth_proof_gap / crc_fifo_request_observer_gap
```

当前平台没有独立暴露`fifo_cnt`或`dma_req`，`SYSC.DMA_REQ_REP_RPT`只表示DMA请求脉冲重复告警，不能替代Request当前电平或FIFO占用计数。因此`CRC_P1_011`撤销错误的Result节拍实现并保持PLAN；`CRC_P1_012`保留当前FPGA RTL FAIL。两者均不用于证明精确FIFO深度。

### 1.8 CHECK 与错误路径

#### CHECK Match

正确CHECK值下：

- `RES.POST_CRC_CAL` 与PC Golden一致；
- `INT_RAW_RPT.CRC_CMF_INT_RAW_RPT=0`；
- `INT_STATUS_RPT.CRC_CMF_INT_STATUS_RPT=0`。

该路径不需要用历史 Service `last_event` 证明“没有错误”。

#### CHECK Mismatch

错误CHECK值下：

- CRC Result本身仍应正确；
- CHECK_ERR真实IRQ到达由 `event_count + ISR last_event/last_raw` 证明；
- 当前 Raw/Status 可能已被ISR清除，必须与ISR latch分开记录。

#### LENGTH Error

稳定刺激为：

```text
CRC32
-> LENGTH=0
-> 合法32-bit IR write
-> LENGTH_ERR IRQ
```

合法访问宽度用于隔离 BUS_ERR 因素。

#### BUS Error

ET6801历史 Unit/FPGATest 的强刺激为：

```text
CRC8 + LENGTH=1
-> 合法8-bit IR write：无BUS_ERR
-> 重新LENGTH=1
-> 非法32-bit IR write：BUS_ERR
```

当前 `CRC_P1_018` 保留合法基线、非法刺激和重新Enable后的正常CRC8恢复三阶段证据。若未来当前硬件实测不触发BUS_ERR，应报告真实FAIL并调查RTL/Bitstream/Revision差异，不允许永久SKIP。

### 1.9 IRQ Source、Mask、Force、Clear 与 ISR Evidence

三类稳定Source：

```text
BUS_ERROR
LENGTH_ERROR
CHECK_ERROR
```

硬件寄存器事实与Service ISR事实严格分开：

```text
INT_RAW_RPT.*       = 当前硬件Raw
INT_STATUS_RPT.*    = 当前硬件Effective Status
Service event_count = 软件/ISR计数Measurement
Service last_event  = ISR latch Observation
Service last_raw    = ISR保存的回调时Raw Observation
```

ISR可以在回调中清除已消费的硬件Pending，因此“IRQ真实到达”不能要求回调返回后Raw仍为1；真实Delivery使用ISR latch + event_count闭合。

当前 `CRC_P1_013` 还增加了 Disable Source 后重新 Force 的反证：Force可形成硬件Raw刺激，但Service Event Count不得继续增加，从而独立证明 Source Enable/Disable 的Delivery控制。

### 1.10 DMA 与性能

#### DMA Input

ET6801 Execution Mapping提供：

- DMA Controller / Interface；
- CRC request ID；
- CRC IR peripheral address。

这些事实不得硬编码在公共 CRC Case。

`CRC_P2_001` 使用 CRC8/16/32自然宽度的DMA M2P输入，并以：

```text
DMA_CHANNEL_STATUS.FREE
+ LENGTH.REMAINING_INPUT_COUNT=0
+ RESULT.CRC == PC Golden
```

形成最小充分证明。

#### CPU Timing

`CRC_P3_002` 使用 CRC Test Driver Extension 中的目标侧 DWT 周期；PC wall-clock 不参与性能Oracle。

#### DMA Timing

`CRC_P3_003` 使用 DMA target-local Timed Start / Completion IRQ 周期，要求：

```text
DMA_TIMING.COMPLETE
+ Channel Free
+ RESULT.CRC正确
+ elapsed_cycles>0
```

两档256/4096-byte各重复3次并比较中位周期，不使用跨芯片绝对阈值。

---

## 第二章：Evidence Set 与当前自动化实现状态

### 2.1 当前实现链路

当前 CRC 自动化链路已存在：

```text
PC Formal Case
-> CRC Driver
-> TargetClient / ET-Frame
-> CRC Firmware Service
-> CRC Common Wrap
-> ET6801 SDK Driver / isolated Test Driver Extension
-> Hardware
```

并已具备：

- Runtime Capability；
- CRC8/16/32 Calculate；
- Result / Length readback；
- Check Value；
- FIFO status与原子Burst测试扩展；
- IRQ enable/disable/mask/unmask/force/clear/snapshot；
- BUS/LENGTH/CHECK错误刺激；
- CPU target-local timed calculate；
- DMA cross-IP input / target timing路径；
- Canonical Measurement / Observation；
- ET_CASE_REPORT。

早期分析文档中的 `driver_gap / wrap_gap / firmware_service_gap / formal_case_gap / timing_test_extension_gap` 已被当前源码实现解除，不再属于当前 Gap。

### 2.2 当前剩余设计 Gap

当前保留两个Feature覆盖Gap，以及一个由当前FPGA HIL直接证明的硬件行为Gap：

| Gap | 当前事实 | 解除条件 |
|---|---|---|
| `dynamic_fifo_depth_proof_gap` | SVD/SDK/历史行为证明FIFO与Threshold/Overflow存在，但没有精确动态测得物理Depth | 形成不会被处理吞吐混淆的安全刺激 + 独立Depth Oracle，再单独评审新/扩展Case |
| `crc_fifo_request_observer_gap` | RTL已确认`FIFO_TRHD`是`fifo_cnt <= threshold`的DMA Request水位；旧`CRC_P1_011`用第4/5次CPU写入后的RESULT变化判断Threshold，测试语义错误。当前SVD/Driver没有暴露`fifo_cnt`或`dma_req`，`SYSC.DMA_REQ_REP_RPT`也只表示请求脉冲重复告警。 | 提供同一目标侧原子窗口内可采样的`fifo_cnt/dma_req` Observer，或提供经设计批准的等价硬件状态；随后按DMA水位矩阵实现并执行`CRC_P1_011`。 |
| `crc_fifo_overflow_behavior_gap` | `CRC_P1_012`测试链路有效；2026-08-24又以Threshold=1、连续64次CPU直接写入`IR`复测，`FIFO_OVF`仍为0，重新配置后的CRC恢复结果为`0x140B8DD8`。经项目同事人工确认，当前ET6801 FPGA实现的`FIFO_OVF`功能存在问题。 | 修复RTL/bit中的`FIFO_OVF`功能后重跑`CRC_P1_012`；修复前保持严格FAIL，不得删除Overflow断言或改为SKIP。 |

这些Gap不阻塞CRC计算、IRQ、DMA和Performance等已独立定义Feature；Threshold和Overflow自身保持未闭合状态。

### 2.3 HIL 状态边界

2026-08-22已经在ET6801 FPGA环境执行当时的CRC Formal Case。该记录属于历史Evidence；后续复盘已确认`CRC_P1_011`的Oracle错误，不能继续视为当前Formal FAIL。精确状态是：

```text
CRC SOURCE / DESIGN / EVIDENCE CLOSURE: 按当时源码与Contract审核
Historical Working-tree FPGA HIL: 24 logical Cases / 45 executions / 43 PASS / 2 FAIL
Historical FAIL Cases: CRC_P1_011（Oracle错误，已撤销实现）, CRC_P1_012（确认FPGA硬件问题）
Current CRC_P1_011: PLANNED / NOT_EXECUTED / crc_fifo_request_observer_gap
Current-SHA Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
Historical HIL / historical test assets: 仅作历史Evidence，不覆盖当前SHA
```

本次运行来自dirty工作树，只能作为Working-tree FPGA HIL；不得写成Exact-SHA PASS。`CRC_P1_011`旧Oracle已撤销，`CRC_P1_012`保留严格FAIL，不影响其余43个Execution的独立结果。

---

## 第三章：历史测试资产与测试意图处置

### 3.1 历史资产

重点历史文件：

```text
FunctionalTest/crc_ft.c
UnitTest/test_crc.c
FPGATest/crc.c
PerformceTest/CRC/crc_time_test.c
Examples/CRC/CRC_calculate/**
```

3101/6003历史JSON与源码用于发现跨代测试意图和漂移，不作为ET6801 `SUPPORTED` 的唯一依据。

### 3.2 保留的历史测试语义

| 历史语义 | 当前处置 | 当前公共Case |
|---|---|---|
| CRC8/16/32固定参数向量 | SUPERSEDED by stronger exact Golden | `CRC_P0_002` |
| Module Enable/Disable | RETAINED with two independent payloads | `CRC_P0_003` |
| Polynomial | RETAINED with parameterized exact Golden | `CRC_P1_001` |
| Initial Seed | RETAINED with parameterized exact Golden | `CRC_P1_002` |
| ByteSwap | SUPERSEDED：不再只断言结果不同 | `CRC_P1_003` |
| RefIn | SUPERSEDED：修复历史Functional两轮均Disable缺陷 | `CRC_P1_004` |
| RefOut | SUPERSEDED：修复历史Functional未真正Enable缺陷 | `CRC_P1_005` |
| XorOut | SUPERSEDED：不再只断言结果不同 | `CRC_P1_006` |
| remainder Byte | CODE_ONLY / RETAINED | `CRC_P1_007` |
| LENGTH / ALR | RETAINED并补显式readback | `CRC_P1_007`, `CRC_P1_008` |
| CHECK match/mismatch | RETAINED并拆分当前寄存器与ISR证据 | `CRC_P1_009`, `CRC_P1_010` |
| FIFO Threshold | SUPERSEDED：旧原子Burst Result节拍语义错误；改为DMA Request水位PLAN | `CRC_P1_011`（PLAN） |
| FIFO Overflow | RETAINED + Recovery | `CRC_P1_012` |
| FIFO Physical Depth | PARTIAL；不再由Threshold/Overflow冒充 | `dynamic_fifo_depth_proof_gap` |
| IRQ Force | RETAINED并参数化三Source | `CRC_P1_013` |
| IRQ Clear | RETAINED精确Raw Clear | `CRC_P1_014` |
| IRQ Mask/Raw/Status | RETAINED两阶段因果证明 | `CRC_P1_015` |
| LENGTH_ERR | RETAINED真实错误刺激 | `CRC_P1_016` |
| BUS_ERR | RETAINED Unit/FPGATest强刺激；Functional旧实现有缺陷 | `CRC_P1_018` |
| DMA Input | RETAINED但去除固定地址/Request ID | `CRC_P2_001` |
| 长稳 | RETAINED并改为可复现固定Seed | `CRC_P3_001` |
| CPU/DMA Performance | RETAINED目标侧周期，不使用Host延迟 | `CRC_P3_002`, `CRC_P3_003` |

### 3.3 明确不继承的旧写法

以下旧模式不得重新引入当前Formal Case：

- Case直接访问 `CRC->IR / CRC->RES`；
- CRC Driver内部调用DMA/SYSCTRL；
- 固定delay替代完成条件；
- `actual1 != actual2` 作为配置正确性的唯一Oracle；
- ISR内部直接决定最终PASS/FAIL；
- 一个大 `CRC_FTest()` 串全部Feature；
- runtime随机种子导致失败无法复现；
- 固定ET6801地址、DMAMUX Request或Channel写入公共Case；
- 用Service event_count冒充硬件寄存器值；
- 用当前Raw=0反向否定已经发生并被ISR消费的真实IRQ。

---

## 第四章：ET6801 芯片适配边界

### 4.1 公共层与芯片层

```text
公共 crc.md
= Feature / Case / Oracle / stable endpoint / Report

公共 PC/Firmware
= 芯片中立业务API与执行语义

ET6801_crc.md
= ET6801 Hardware/Register/SDK/历史证据/endpoint mapping

ET6801 Capability / Execution Mapping / Chip Driver
= 机器可执行芯片事实
```

### 4.2 ET6801 Capability Truth

当前 `et6801/ip/crc.yaml` 已生成：

- instance `crc0`；
- modes `[crc8, crc16, crc32]`；
- Feature：module_enable、polynomial、initial_seed、byteswap、refin/refout、xor_out、alr、check、length、result、fifo_threshold、fifo_overflow、IRQ控制/状态；
- `fifo_threshold_max=8`；
- `length_field_max=65535`；
- result width；
- IRQn=4；
- Base Address；
- SVD Evidence Path。

Capability只表达硬件/机器事实，不保存Case PASS状态。

### 4.3 当前芯片专属限制

- CRC8不支持ByteSwap公共组合；
- CRC16 source至少2-byte对齐，CRC32至少4-byte对齐；
- 正常同步Calculate限定为非零且不超过当前Runtime max bytes；
- `length_bytes=0`只用于LENGTH Error原子刺激，不定义为空消息CRC；
- FIFO Threshold最大值为8，但这不是“动态证明FIFO物理深度=8”；
- BUS_ERR历史刺激需要Test Driver typed input write；
- Performance依赖目标侧DWT和对应Test Driver Extension；
- DMA路径依赖ET6801 Execution Mapping，不写入公共Case常量。

---

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| CRC_F_001 | SUPPORTED | MODULE_EN控制 | ADAPTED | `CRC_P0_003` |
| CRC_F_002 | SUPPORTED | CRC8/16/32 | ADAPTED | `CRC_P0_002`, `CRC_P3_001` |
| CRC_F_003 | SUPPORTED | POLY自然宽度配置 | ADAPTED | `CRC_P1_001` |
| CRC_F_004 | SUPPORTED | INI自然宽度配置 | ADAPTED | `CRC_P1_002` |
| CRC_F_005 | SUPPORTED | ByteSwap仅CRC16/32 | ADAPTED | `CRC_P1_003` |
| CRC_F_006 | SUPPORTED | RefIn逐Byte | ADAPTED | `CRC_P1_004` |
| CRC_F_007 | SUPPORTED | RefOut自然宽度 | ADAPTED | `CRC_P1_005` |
| CRC_F_008 | SUPPORTED | ALL_ZERO / ALL_ONE | ADAPTED | `CRC_P1_006` |
| CRC_F_009 | SUPPORTED | CRC16/32 remainder Byte路径 | ADAPTED | `CRC_P1_007` |
| CRC_F_010 | SUPPORTED | LENGTH保存输入事务数 | ADAPTED | `CRC_P1_007` |
| CRC_F_011 | SUPPORTED | CTRL.CRC_ALR_EN | ADAPTED | `CRC_P1_008` |
| CRC_F_012 | SUPPORTED | FIFO存在；精确物理Depth当前只有静态/间接证据 | PARTIAL_ADAPTATION | 无；`dynamic_fifo_depth_proof_gap` |
| CRC_F_013 | SUPPORTED | FIFO_TRHD 0~8；RTL语义为`fifo_cnt<=threshold`时DMA Request有效 | PARTIAL_ADAPTATION | `CRC_P1_011`（PLAN）；`crc_fifo_request_observer_gap` |
| CRC_F_014 | SUPPORTED | FIFO_OVF可读取并通过Module重新进入恢复 | ADAPTED | `CRC_P1_012` |
| CRC_F_015 | SUPPORTED | RES按CRC8/16/32自然宽度有效 | ADAPTED | `CRC_P0_002` |
| CRC_F_016 | SUPPORTED | CHECK match无CMF错误 | ADAPTED | `CRC_P1_009` |
| CRC_F_017 | SUPPORTED | CMF CHECK_ERR | ADAPTED | `CRC_P1_010` |
| CRC_F_018 | SUPPORTED | LEF LENGTH_ERR | ADAPTED | `CRC_P1_016` |
| CRC_F_019 | SUPPORTED | BEF BUS_ERR；历史强刺激CRC8+32-bit write | ADAPTED | `CRC_P1_018` |
| CRC_F_020 | SUPPORTED | INT_EN + Service IRQ route | ADAPTED | `CRC_P1_013` |
| CRC_F_021 | SUPPORTED | INT_MASK | ADAPTED | `CRC_P1_015` |
| CRC_F_022 | SUPPORTED | INT_FORCE_IND | ADAPTED | `CRC_P1_013` |
| CRC_F_023 | SUPPORTED | INT_CLR | ADAPTED | `CRC_P1_014` |
| CRC_F_024 | SUPPORTED | INT_RAW_RPT / INT_STATUS_RPT | ADAPTED | `CRC_P1_015` |
| CRC_F_025 | SUPPORTED | CRC_IRQn=4 + IRQ Manager + Service ISR evidence | ADAPTED | `CRC_P1_010`, `CRC_P1_013`, `CRC_P1_016`, `CRC_P1_018` |
| CRC_F_026 | SUPPORTED | DMAMUX CRC request + IR M2P输入 | ADAPTED | `CRC_P2_001` |
| CRC_F_027 | SUPPORTED | CRC Test Driver DWT计时 | ADAPTED | `CRC_P3_002` |
| CRC_F_028 | SUPPORTED | DMA target-local Start-to-IRQ计时 | ADAPTED | `CRC_P3_003` |
| CRC_F_029 | SUPPORTED | CRC实例、模式、IRQ、FIFO Threshold与同步计算上限由Capability/Runtime身份声明 | ADAPTED | `CRC_P0_001` |

> `PARTIAL_ADAPTATION` 用于 `CRC_F_012` 的动态物理深度证明缺口和 `CRC_F_013` 的DMA Request水位Observer缺口；它不否定硬件寄存器存在，但禁止把未证明语义写成Formal PASS。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| CRC_P0_001 | ADAPTED | Formal Case已存在；Runtime Capability链路已实现；当前SHA HIL未执行 |
| CRC_P0_002 | ADAPTED | 三Kernel固定向量 + PC Golden + Result/Length Evidence已实现；当前SHA HIL未执行 |
| CRC_P0_003 | ADAPTED | 双轮Disable/Re-enable恢复链已实现；当前SHA HIL未执行 |
| CRC_P1_001 | ADAPTED | Polynomial参数化Exact Golden已实现；当前SHA HIL未执行 |
| CRC_P1_002 | ADAPTED | Initial Seed参数化Exact Golden已实现；当前SHA HIL未执行 |
| CRC_P1_003 | ADAPTED | CRC16/32 ByteSwap矩阵已实现；当前SHA HIL未执行 |
| CRC_P1_004 | ADAPTED | RefIn Exact Golden已实现；当前SHA HIL未执行 |
| CRC_P1_005 | ADAPTED | RefOut自然宽度Exact Golden已实现；当前SHA HIL未执行 |
| CRC_P1_006 | ADAPTED | XorOut自然宽度Exact Golden已实现；当前SHA HIL未执行 |
| CRC_P1_007 | ADAPTED | remainder + LENGTH set/readback因果链已实现；当前SHA HIL未执行 |
| CRC_P1_008 | ADAPTED | ALR两轮不重写Length已实现；当前SHA HIL未执行 |
| CRC_P1_009 | ADAPTED | CHECK Match用Result + CMF Raw/Status最小证明；当前SHA HIL未执行 |
| CRC_P1_010 | ADAPTED | CHECK mismatch Result/ISR/count来源分离；当前SHA HIL未执行 |
| CRC_P1_011 | IMPLEMENTATION_GAP | 旧Result节拍Case已撤销；当前等待独立`fifo_cnt/dma_req` Observer后实现DMA Request水位边界测试。 |
| CRC_P1_012 | ADAPTED | Overflow + Recovery执行链完整；**不闭合CRC_F_012物理Depth**；当前FPGA HIL为FAIL，七次原子写入后Overflow仍为0，但恢复CRC正确。 |
| CRC_P1_013 | ADAPTED | Enable Delivery + Disable后re-Force反证已实现；当前SHA HIL未执行 |
| CRC_P1_014 | ADAPTED | Mask状态Force后Raw精确Clear已实现；当前SHA HIL未执行 |
| CRC_P1_015 | ADAPTED | Mask/Raw/Status + Unmask新Delivery两阶段已实现；当前SHA HIL未执行 |
| CRC_P1_016 | ADAPTED | LENGTH=0 + 合法宽度真实错误刺激已实现；当前SHA HIL未执行 |
| CRC_P1_018 | ADAPTED | 合法8-bit基线 + 非法32-bit BUS_ERR + Recovery已实现；当前SHA HIL未执行 |
| CRC_P2_001 | ADAPTED | Capability/Execution Mapping驱动DMA M2P链已实现；当前SHA HIL未执行 |
| CRC_P3_001 | ADAPTED | 20轮确定性长稳 + failure-safe Snapshot已实现；当前SHA HIL未执行 |
| CRC_P3_002 | ADAPTED | 256/4096×3 DWT计时 + failure-safe Snapshot已实现；当前SHA HIL未执行 |
| CRC_P3_003 | ADAPTED | DMA Start-to-IRQ计时 + failure-safe Snapshot已实现；当前SHA HIL未执行 |

### 6.1 当前结论

```text
Public Feature: 29
- ADAPTED: 27
- PARTIAL_ADAPTATION: 2 (CRC_F_012, CRC_F_013)

Formal Case: 24
- ADAPTED: 23
- PLANNED: 1 (CRC_P1_011)

Historical Working-tree FPGA HIL（旧Case语义，仅保留取证记录）:
- 24 logical Cases / 45 executions
- 43 PASS / 2 FAIL
- 旧FAIL: CRC_P1_011, CRC_P1_012

Current Formal Set:
- CRC_P1_011: PLANNED / NOT_EXECUTED
- CRC_P1_012: HIL_FAIL / CONFIRMED_FPGA_FUNCTION_ISSUE

Current-SHA Silicon HIL:
- NOT_EXECUTED / NOT_VERIFIED
```

`ADAPTED` 不等于 `PASS`。2026-08-22运行的Source Revision为`edfd188173e93b3a580ba1d30587795c2ca1749c`且`source_dirty=true`，因此只能证明当时工作树行为。该次`CRC_P1_011`采用已被推翻的Result节拍Oracle，不再代表当前Formal Case；原始证据仍保留在`artifacts/runs/20260822_104307_942751_local_et6801_fpga/tests/crc`，对应报告为`artifacts/reports/20260822_104835_661796_ET6801_CRC测试报告.xlsx`。

### 6.2 2026-08-22 FIFO行为诊断

1. `CRC_P1_011`记录：Threshold=5，写入前RESULT=`0xBD3A64DC`，第四次写入后RESULT=`0xAD37D056`，第五次后仍为`0xAD37D056`，Overflow=0。
2. `CRC_P1_012`记录：Threshold=1，七次目标端原子写入后Overflow仍为0；Disable/Re-enable后的恢复CRC实际值与PC Golden均为`0x140B8DD8`，剩余输入计数为0。
3. J-Link只读诊断在P1_011配置保持期间读回`FIFO_TRHD=5`，排除了PC、Service、Wrap或Chip Driver没有写入Threshold的解释。
4. 后续复盘结论：`CRC_P1_011`的测试链路执行正常，但把Threshold错误解释成Result更新门限，该FAIL不再用于判断硬件；`CRC_P1_012`仍是当前FPGA CRC FIFO Overflow硬件问题，不得为了通过率弱化断言。

### 6.3 当前未通过测试记录

时间：2026-08-22 16:19 CST

| Case | 测试环境 | 实际硬件现象 | 已排除的软件链路问题 | 当前判定 | 闭环条件 |
|---|---|---|---|---|---|
| `CRC_P1_011` | ET6801 FPGA，FIFO Threshold=5，五次目标端紧凑32-bit写入 | 写入前`RESULT=0xBD3A64DC`；第四次写入后已变为`0xAD37D056`，第五次后保持不变 | J-Link在Case活动期间直接读回`FIFO_TRHD=5`，仅证明配置到达硬件；不能证明DMA Request水位 | `INVALID_ORACLE / SUPERSEDED` | 提供独立`fifo_cnt/dma_req` Observer后按DMA水位PLAN重新实现；不得继续使用Result节拍判断 |
| `CRC_P1_012` | ET6801 FPGA，FIFO Threshold=1，七次目标端原子写入并执行恢复路径 | 七次写入后`FIFO_OVF=0`；Disable/Re-enable后恢复CRC为`0x140B8DD8`，与PC Golden一致 | 原子刺激、Overflow读取和恢复路径均已执行，恢复结果证明模块后续可正常工作 | `FPGA_FIFO_OVERFLOW_BEHAVIOR_GAP / HIL_FAIL` | RTL/bit所有者确认可触发Overflow的真实FIFO路径和安全刺激；取得权威结果后重跑 |

`CRC_P1_011`旧结果只保留为错误Oracle的复盘证据；`CRC_P1_012`保持严格FAIL。二者均不用于宣称已经动态测得FIFO物理深度。证据位于`artifacts/runs/20260822_104307_942751_local_et6801_fpga/tests/crc`；本次运行来自dirty工作树。

### 6.4 CRC_P1_012人工确认与64次CPU直写复测

时间：2026-08-24 15:50 CST

现象：`CRC_P1_012`在当前ET6801 FPGA环境始终无法置位`FIFO_OVF.CRC_FIFO_OVF_RPT`。

操作 / 测试方法：

1. 配置CRC32，设置FIFO Threshold=1；
2. 使用独立手动测试固件，通过CPU `for`循环连续64次直接写入`CRC->IR`，中间不轮询、不读取结果；
3. 紧接着读取`CRC->RES`和`CRC->FIFO_OVF`；
4. 复位并重新配置CRC，计算固定输入，验证模块恢复能力。

结果：连续64次写入后`RESULT=0x2F7ADCFC`，但`FIFO_OVF=0`；复位并重新配置后的恢复CRC为`0x140B8DD8`，与预期一致。

后续修正 / 最终结论：经项目同事人工确认，当前测试方法正常，失败原因是当前ET6801 FPGA实现的`FIFO_OVF`功能存在问题。`CRC_P1_012`应继续记录为`HIL_FAIL / CONFIRMED_FPGA_FUNCTION_ISSUE`，不是SKIP，也不得通过弱化断言改成PASS。该结论仅限定当前FPGA实现，不代表未来修复后的RTL或硅后芯片行为。

关联文件 / 证据：`artifacts/runs/20260824_153942_456192_manual_et6801_uart_crc/manual/uart_crc.log`。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:26 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:11 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/crc/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 23 | 23 | 22 | 1 | 0 | 0 | 44 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `CRC_P1_012` | FPGA | FAIL | `CRC_F_014` / CRC FIFO Overflow状态 | `FIFO_TRHD=1`并连续写入7次后，`FIFO.OVERFLOW`仍由`false`保持为`false`；恢复轮CRC实际值与期望值均为`0x140B8DD8`，剩余输入计数为0 | 人工已确认刺激方法有效；当前ET6801 FPGA实现的`FIFO_OVF`功能存在问题，CRC计算与恢复路径正常 | RTL/bit修复`FIFO_OVF`后，使用相同紧凑写入和恢复流程复测 | `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/crc/` |
<!-- ET_CHIP_TEST_STATUS_END -->
