# ET6801 STIMER Chip Analysis & Adaptation

> 本文件只记录 ET6801 的 STIMER Hardware Truth、Driver/Capability/Bench 事实，以及这些事实如何适配公共 `stimer.md`。
> 公共 Feature、Case、Oracle 与报告语义以 `stimer.md` 为唯一稳定 Contract；本文件不得形成第二套公共 Case Schema。
> 当前 STIMER 已实现16个公共Formal Case；本文只记录ET6801适配事实。软件Gate与本轮HIL结果必须分别记录，不能由实现状态推导PASS。

## 分析基线与裁决顺序

| Item | Current Source / Decision |
|---|---|
| Target | `ET6801 / STIMER` |
| Public Contract | `test_case_doc/stimer/stimer.md` |
| Primary Hardware Truth | `ET6801.svd::STIMER0..STIMER5`，当前 Capability 记录 SVD SHA256=`175A585FE736CA1300045BF147330296B97D3E3DCFAC2227FCC8B603F67AD61C` |
| Current SDK Driver | `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_stimer.h` + `Src/et6x_stimer.c` |
| Current Machine Capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/stimer.yaml` |
| Historical ET6801 Unit Test | Google Drive `UnitTest/test_stm.c`，仅作历史实现证据，不作为当前 Formal Case |
| Historical ET6801 FPGA Test | Google Drive `FPGATest/stimer_fpga_test.c`，仅作历史硬件/Bench 线索，不作为当前 SHA HIL |
| Historical Requirements | ET3101 / ET6003 `stimer.json`，用于 Source Item Trace；与 ET6801 直接 SVD 冲突时不得覆盖目标芯片事实 |
| Cross-chip Manual | `ET60157-用户手册_V1.0.0.pdf`，只作同类 IP 历史语义对照 |
| Current Working-tree HIL | 基础全量回归已执行；2026-08-22另对`STIMER_P2_003`执行真实J-Link Halt/Resume专项HIL并得到FAIL |

裁决顺序固定为：

```text
ET6801 direct SVD / target-chip source
> ET6801 current SDK implementation facts
> ET6801 historical Unit/FPGA test behavior
> ET3101/ET6003 requirement-source history
> ET60157 cross-chip manual
```

Driver、历史测试或其他芯片资料与 ET6801 直接 SVD 冲突时，保留 ET6801 Hardware Truth，并把差异记录为 Driver / Mapping / Bench Gap，禁止反向降低或改写硬件事实。

---

## 第一章 Source Coverage / Source Item Trace

### 1.1 Source Coverage

| Source Domain | Status | 本轮使用内容 | 边界 |
|---|---|---|---|
| ET6801 SVD | FOUND / PRIMARY | 6 实例、计数/周期/模式、Compare、IRQ、DMA mux、诊断、Debug Halt、紧急捕获 | Hardware Truth 主来源 |
| ET6801 SDK STIMER Driver | FOUND | Public SDK API、参数校验、实际寄存器写法、实例限制 | 只能证明当前实现，不能覆盖 SVD |
| ET6801 Machine Capability | FOUND / INCOMPLETE | 6 实例、Base Identity、IRQ Identity | `features/limits/options/parameters` 当前为空，存在语义 Mapping Gap |
| ET6801 UnitTest `test_stm.c` | FOUND / HISTORICAL | Overflow、Pause/Clear、IRQ、One-Shot/Free-Run、Shadow、DMA 等历史测试行为 | 不等于当前 Formal Case / 当前 SHA HIL |
| ET6801 FPGA `stimer_fpga_test.c` | FOUND / HISTORICAL | Compare0..3 通过 Output XBAR 到 GPIO 的历史路由、DMA、IRQ、Debug 测试线索 | Debug 用例自身明确标注测试方法有问题 |
| ET3101 `stimer.json` | FOUND / REQUIREMENT-HISTORY | 11 个测试点、8 个历史测试用例 | 只用于跨产品需求追溯 |
| ET6003 `stimer.json` | FOUND / REQUIREMENT-HISTORY | 与 ET3101 基本一致的 STIMER 测试点/用例 | 只用于跨产品需求追溯 |
| ET60157 用户手册 | FOUND / CROSS-CHIP | 同类 STIMER 模式、事件与紧急捕获语义 | 不能覆盖 ET6801 数值边界 |

### 1.2 Requirement / Historical Source Item Trace

当前 ET3101 / ET6003 requirement-source 中的 STIMER 测试点仍逐项追溯，但不机械复制旧 Case：

| Source Item | 历史含义 | 当前公共归属 | ET6801 本轮决策 |
|---|---|---|---|
| `STM_TP_001` | 模块数量 / stimer实例 | Chip Identity | 由 SVD 直接确认 6 实例；不单独制造公共 Feature |
| `STM_TP_002` | 分频最大/最小 | `STIMER_F_002 / P1_001` | 保留；ET6801 逻辑范围以 direct SVD 为准 |
| `STM_TP_003` | One-Shot / Free-Run | `STIMER_F_004 / P1_002` | 保留并加强生命周期 Oracle |
| `STM_TP_004` | Immediate / Shadow | `STIMER_F_007 / P1_004` | 保留；按真实生效时刻而非配置写值判定 |
| `STM_TP_005` | 周期最大/最小 | `STIMER_F_003 / P0_002 / P1_004` | 保留；ET6801 周期字段为 32-bit |
| `STM_TP_006` | 4 个比较门限 | `STIMER_F_009 / P1_006` | 保留；当前 Driver 存在 confirmed compare 写寄存器错误 |
| `STM_TP_007` | stop / run / clear | `STIMER_F_001/F005/F006/F019` | 保留并拆成计数启停、清零、Pause/Resume与边界优先级硬件行为 |
| `STM_TP_008` | 计数锁存/读回 | `STIMER_F_008 / P1_005` | 保留；要求重复 Latch 产生新快照 |
| `STM_TP_009` | Overflow / Compare IRQ | `STIMER_F_011/F012/F017 / P1_007` | 保留并拆分 RAW / STATUS / Force / ISR Delivery 来源 |
| `STM_TP_010` | Event | `STIMER_F_010/F014/F018 / P1_008` | 保留；脉宽、Overflow History与Compare Repeat分别表达，需要连续数字Observer与原子诊断Snapshot |
| `STM_TP_011` | DMA | `STIMER_F_013 / P2_001` | 保留；必须证明真实 DMA 搬运而不是只配置 request |
| 历史 prescaler hot-change Case | 运行中改分频 | 不 Admission 为当前公共 Case | **REJECTED for ET6801**：direct SVD 明确分频为静态配置，运行中不可修改 |
| 历史 Debug Case | 软件延时/人工观察 CNT | `STIMER_F_015 / P2_003` | **SUPERSEDED**：FPGA 源码自己标注“测试方法有问题”，当前 Contract 改为真实 Debugger Halt/Resume |

### 1.3 历史 ET6801 测试能证明什么、不能证明什么

`UnitTest/test_stm.c` 和 `FPGATest/stimer_fpga_test.c` 证明 ET6801 曾存在以下真实测试路径：基本 Overflow、Pause/Clear、IRQ Handler、One-Shot/Free-Run、Shadow/Immediate、Compare 驱动调用、DMA 搬运和 Debug/Halt 尝试；FPGA 版本还把 `STM0_OC0..3` 通过 Output XBAR 路由到 GPIO。它们是重要的设计输入。

但历史源码存在明显证据局限：

- IRQ Handler 最终只留下一个 `STM_irqFlag` 布尔量，不能证明五个 Source 的 RAW / STATUS / Delivery 来源隔离；
- 多处依赖固定 `DELAY_US/ms`，不能替代统一状态驱动 Oracle；
- Compare 历史 Case 调用了当前已确认有寄存器写错的 Driver，因此不能把历史通过视为 Compare 当前正确；
- Debug FPGA Case 源码明确写有“用例判断方式有问题，需要修改测试方法”；
- 历史结果没有绑定本轮 `chatgpt_dev` 精确 SHA。

因此这些源码只用于 Source Trace / Bench 设计，不把它们包装成当前 Closure。

---

## 第二章 ET6801 Hardware / Register / Driver Claim

### 2.1 Hardware Truth 总览

| Capability | Hardware | ET6801 Direct Fact | Primary Evidence |
|---|---|---|---|
| 实例 | SUPPORTED | STIMER0..STIMER5，共 6 个独立实例 | SVD `STIMER0..5` |
| 计数器 | SUPPORTED | 32-bit 实时计数 + 32-bit 软件锁存快照 | `CNT_RPT`, `CNT_RPT_LATCH` |
| Start/Stop | SUPPORTED | `STM_TON_R` 控制模块使能；Disable 后中断/事件输出为 0 | `STM_SET.STM_TON_R` |
| Pause/Resume | SUPPORTED | `STM_THLT_R` 暂停；Pause 与 Overflow 同到达时 Overflow 优先 | `STM_SET.STM_THLT_R` |
| One-Shot/Free-Run | SUPPORTED | `STM_CONT_R=0/1` 分别为 One-Shot / FreeRUN | `STM_SET.STM_CONT_R` |
| 软件清零 | SUPPORTED | 软件清零把计数器置 0 | `STM_SET.STM_TCLR_R` |
| 预分频 | SUPPORTED | 16-bit 配置语义；**逻辑分频系数 1..65535，软件写 divider-1；运行中不可修改** | `STM_PSCL.STM_PSCL_R` description |
| 周期 | SUPPORTED | 32-bit 周期，SVD 声明范围 1..2^32-1 | `TCYC.STM_TCYC_R` |
| 周期加载 | SUPPORTED | Immediate 以 `STM_TCLD_R` 上升沿为加载时刻；Shadow 在计数到 0 或软件立即加载时生效 | `STM_TCLD_R`, `STM_SHDW_UG_R` |
| Compare | SUPPORTED | 4 路，各有 32-bit threshold | `OCWH0..3.STM_CPNM*` |
| Compare Event | SUPPORTED | 到门限产生 Compare0..3 单脉冲，可进入 IRQ | `OCWH0..3` descriptions |
| Event Width | SUPPORTED | Overflow + 4 路 Compare 均有 8-bit扩展；0 不扩展，127→128拍，255→256拍，默认15→16拍 | `STM_OFWH`, `STM_OCWH0..3` |
| IRQ | SUPPORTED | Overflow + Compare0..3 共 5 Source；Enable / Mask / Force / Clear / Raw / Status 均存在 | `STM_INT_*` |
| DMA Source Mux | SUPPORTED | 0=Overflow，1..4=Compare0..3，5..7回到Overflow | `DMA_HD_MUX.STM_DMA_HMUX` |
| Overflow History | SUPPORTED | `STM_OF_RPT`，readAction=clear | `STM_STATUS_RPT` |
| Compare Repeat Warning | SUPPORTED | Compare 脉宽扩展期间再次到同源事件时忽略重复脉冲并告警，readAction=clear | `STM_OC0_REPT_RPT..STM_OC3_REPT_RPT` |
| Compare Load Warning | SUPPORTED / SEMANTIC GAP | `STM_OCWR0_RPT..3` 存在且 read-to-clear，但 SVD 条件描述内部矛盾 | `STM_STATUS_RPT` |
| CPU Debug Halt | SUPPORTED | `STM_CPUHALT_MODE_R=0` Halt时暂停；=1 Halt时继续 | `STM_SET.STM_CPUHALT_MODE_R` |
| Emergency Route | SUPPORTED | 每实例有 ERG0/ERG1 两组、每组23-bit Source enable | `XBAR.STMnERG0_EN / STMnERG1_EN` |
| Emergency Capture | SUPPORTED | `SYSC.STM0..STM5.SYSC_ERG_CNT` 锁定紧急触发时当前 STIMER 值 | `SYSC.STM0..5` |

#### 2.1.1 预分频边界裁决

ET6801 direct SVD 的字段说明明确写：

```text
分频系数 1..65535
软件写 divider - 1
静态配置，运行中不可修改
```

因此本轮 **不再沿用旧文档“16-bit raw 0..65535 ⇒ 逻辑最大65536”的推断**。ET60157 历史手册或其他芯片若给出 65536，只表示跨芯片差异；ET6801 公共 Capability 必须按目标 SVD 冻结 `prescaler_divider.max=65535`，除非获得更高权威的 ET6801 资料推翻该描述。

#### 2.1.2 周期 Immediate Load

`STM_TCLD_R` 由底层采集**上升沿**作为实际加载时刻：

- 当前 Count < 新 Period：直接更新周期；
- 当前 Count >= 新 Period：Timer 立即清零并产生 Overflow；
- Shadow 模式：周期在计数到 0 或软件立即加载时生效；
- 非 Shadow：仅软件立即加载生效。

所以公共 `P1_004` 必须用下一终点/计数行为证明生效时机，不能只记录“写了新 Period”。Driver 的重复 immediate-load 动作还必须确认每次都能形成新的有效控制脉冲/上升沿。

#### 2.1.3 Pause / Overflow 同边界

SVD 明确：Pause 与 Overflow 同时到达时，Overflow 优先，计数先回到 0，再进入 Pause；Pause 时 Compare 输出自动关闭，避免停在门限处持续输出 Compare 事件。普通 Pause/Resume 可由计数前后值证明；“同边界优先级”需要同步刺激和连续 Observer，不能靠软件延时碰概率。

#### 2.1.4 Diagnostic read-to-clear

`STM_STATUS_RPT` 中 Overflow history、Compare repeat、Compare load warning 都是 read-to-clear。未来公共 `DIAGNOSTIC_SNAPSHOT` 必须读取**一次原始寄存器快照**后再拆字段；如果逐字段调用读接口，第一次读取可能已经消费其他决定性现场。

### 2.2 Current Driver Conflict / Gap Matrix

| ID | Severity | State | Hardware Truth | Current Driver Fact | 决策 / 解除条件 | 重点 Public Case |
|---|---|---|---|---|---|---|
| `STIM_DRV_001` | HIGH | CONFIRMED_DRIVER_GAP | SVD 有 6 实例 | `IS_STIM_ALL_PERIPH()` 只允许 STIMER0/1 | 扩展实例校验或改为 Capability-safe 实例映射；不得把4个实例当硬件不支持 | P0_001 / P2_001 |
| `STIM_DRV_002` | CRITICAL | **CONFIRMED_DRIVER_BUG** | `OCWHn` 是32-bit Compare threshold；`STM_OCWHn` 是8-bit pulse width | `STIMER_loadCounterCompareValue()` 以16-byte步进后把 low32 写 `reg_base+8`、high32 写 `reg_base+4` | 改为正确写32-bit threshold并触发 `STM_CPLDn` load；不得污染 pulse-width register | **P1_006** |
| `STIM_DRV_003` | HIGH | **CONFIRMED_DRIVER_BUG** | Period 是32-bit，1..2^32-1 | `STIMER_setPeriod(uint64_t)` 接受至2^64-1，`period-=1`后只写 `(uint32_t)period` | Public API/校验必须与32-bit硬件语义一致，超过可表示范围失败关闭 | P0_002 / P1_004 |
| `STIM_DRV_004` | MEDIUM | COMMENT / TYPE GAP | ET6801逻辑 divider 最大65535 | Driver注释写“1..65536”，但参数类型为`uint16_t`且validator最大0xFFFF | 以SVD+实际validator为准；修正文档并在Capability冻结max=65535 | P1_001 |
| `STIM_DRV_005` | HIGH | CONTROL-PULSE GAP | Immediate Period Load按 `STM_TCLD_R` 上升沿动作 | `STIMER_setLoadMode(IMMEDIATELY)` / `setPeriod()` 直接Set位，重复动作依赖硬件自清/脉冲行为 | 证明连续两次调用均形成新加载动作；若需要专用pulse API则补实现 | P1_004 |
| `STIM_DRV_006` | RESOLVED_BY_EXTENSION | API GAP | Overflow/Compare均支持8-bit event width | 正式SDK没有独立event-width配置API | Test Driver Extension按“周期数”语义写入对应宽度寄存器；外部脉宽实测仍由P1_008 Bench完成 | P1_008, P1_010 |
| `STIM_DRV_007` | LOW | TYPE GAP | Latched count为32-bit | `STIMER_getTimerCountLatch()` 返回`uint64_t` | 公共Evidence保持hex32/32-bit语义；Driver类型可后续收口 | P1_005 |
| `STIM_DRV_008` | MEDIUM | VALIDATION_GAP | IRQ合法位仅低5bit | `IS_STIMER_INTFLAG(flag)` 只检查与ALL存在交集，额外非法位仍可能通过 | 参数校验应失败关闭超出合法mask的bit | P1_007 |
| `STIM_DRV_009` | MEDIUM | COMMENT / SEMANTIC GAP | `STM_INT_MASK` 位=1表示屏蔽 | `setInterruptMask()` 实际Set mask位，但注释称“unmask”；`clearInterruptMask()`注释也混乱 | 公共语义冻结为MASK/UNMASK；Driver命名/注释与行为统一 | P1_007 |
| `STIM_DRV_010` | HIGH | EVIDENCE-LIFECYCLE GAP | `STM_STATUS_RPT` 整体read-to-clear | `STIMER_getStatus()` 可按mask读取，但一次寄存器读取会消费全寄存器现场 | 增加单次原子 diagnostic snapshot；之后再解析各字段 | P1_008 |

### 2.3 Current Capability Gap

当前 `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/stimer.yaml` 已稳定生成：

- STIMER0..STIMER5 identity；
- 六实例 Base Identity；
- 六实例 IRQ Identity。

但：

```yaml
capabilities:
  features: {}
  limits: {}
  options: {}
  parameters: {}
```

因此当前机器层还无法回答：`prescaler_divider.max`、`period_ticks.max`、Compare channel count、IRQ source set、event-width range、DMA source set、Debug Halt / emergency capture 等公共 Feature/Limit。该缺口属于 **Capability semantic mapping gap**，不是硬件未知。

---

## 第三章 Stable Endpoint -> ET6801 Register / Observer Mapping

> 本章只用于目标芯片 Reviewer 展示与后续 Execution Mapping。Canonical Result 仍保存公共稳定 endpoint；不得把 ET6801 寄存器名反灌到公共 `stimer.md` 或公共 Case API。

| Public Stable Endpoint | ET6801 Actual Source | Mapping / Lifecycle | Current Status |
|---|---|---|---|
| `COUNT.LIVE` | `STIMERn.CNT_RPT.STM_CNT_RPT` | 32-bit realtime count | MAPPED |
| `COUNT.LATCHED` | `STIMERn.CNT_RPT_LATCH.STM_CNT_RPT` | 先发 `STM_SET.STM_CNTLK_R` latch pulse，再读取32-bit snapshot | MAPPED / repeat pulse需实现验证 |
| `IRQ_RAW.OVERFLOW` | `STM_INT_RAW_RPT[4]` | Mask前Raw | MAPPED |
| `IRQ_RAW.COMPARE[0..3]` | `STM_INT_RAW_RPT[0..3]` | SVD描述沿用 ACOMP0..3 字样，但语义对应 STIMER Compare0..3 | MAPPED |
| `IRQ_STATUS.OVERFLOW` | `STM_INT_STATUS_RPT[4]` | Mask后Status | MAPPED |
| `IRQ_STATUS.COMPARE[0..3]` | `STM_INT_STATUS_RPT[0..3]` | Mask后Status | MAPPED |
| `IRQ_DELIVERY.LATCHED_SOURCE` | Firmware IRQ Service / ISR latch | **不是寄存器别名**；必须独立记录Source级Delivery | MAPPED |
| `STATUS_HISTORY.OVERFLOW` | `STM_STATUS_RPT.STM_OF_RPT` | read-to-clear；必须原子snapshot后解析 | MAPPED |
| `STATUS_DIAG.COMPARE_REPEAT[0..3]` | `STM_OC0_REPT_RPT..STM_OC3_REPT_RPT` | read-to-clear | MAPPED |
| `EVENT_PULSE.COMPARE[0..3]` | STIMER compare event → Output XBAR → FPGA/Instrument | 历史 FPGA 已对 STIMER0 的 `STM0_OC0..3` 建立GPIO路由；当前自动化路由/采样约束未冻结 | BENCH_GAP |
| `EVENT_PULSE.OVERFLOW` | STIMER Overflow event → 待冻结数字Observer route | 硬件存在event-width配置，但当前资料未冻结稳定外部可观测路由 | MAPPING_GAP |
| `DMA_CHANNEL_STATUS` | Peer AHB-DMA Channel status | 公共DMA Driver返回Free/Error终态；真正完成事实来自DMA硬件，不来自STIMER | ADAPTED |
| `DMA_DESTINATION_WORD` | Peer DMA destination memory / verified destination endpoint | Resource读取目标内存并与独立Expected Word比较 | ADAPTED |
| `EMERGENCY_CAPTURE.COUNT` | `SYSC.STM0..STM5.SYSC_ERG_CNT` | 紧急触发锁存32-bit当前计数；触发Source由XBAR ERG group配置；Test Driver Extension以禁用ERG路由作为清理动作，下一次有效触发覆盖只读值 | MAPPED |
| `REFERENCE.CYCLE_COUNT` | Companion FPGA / Instrument / independent target reference | 不属于STIMER寄存器；用于Ratio/Long-run Oracle | BENCH_GAP |

`STM_OCWR0_RPT..STM_OCWR3_RPT` 是 ET6801 额外存在的 Compare-load warning。由于 direct SVD 对其精确触发条件存在自相矛盾的描述，本轮**不把它纳入公共 STIMER_F_014 的决定性证明**，只在本芯片保留 `stimer_diagnostic_warning_semantic_gap`；待更高权威资料澄清后再按 R140 重新 Admission，而不是先把不确定语义写进公共 Contract。

### 3.1 Compare Threshold / Event Width 实际寄存器映射

| Logical item | ET6801 actual register/field |
|---|---|
| Compare0 threshold | `OCWH0.STM_CPNM0_R` (32-bit) |
| Compare1 threshold | `OCWH1.STM_CPNM1` (32-bit) |
| Compare2 threshold | `OCWH2.STM_CPNM2` (32-bit) |
| Compare3 threshold | `OCWH3.STM_CPNM3` (32-bit) |
| Compare0..3 load pulse | `STM_CPLD0..3.STM_CPLD*_R` |
| Compare0 event width | `STM_OCWH0.STM_OCWH0_R` (8-bit) |
| Compare1 event width | `STM_OCWH1.STM_OCWH1_R` (8-bit) |
| Compare2 event width | `STM_OCWH2.STM_OCWH2_R` (8-bit) |
| Compare3 event width | `STM_OCWH3.STM_OCWH3_R` (8-bit) |
| Overflow event width | `STM_OFWH.STM_OFWH_R` (8-bit) |

这一映射是 `STIM_DRV_002` 判定为 confirmed bug 的直接依据。

### 3.2 IRQ Source bit mapping

| Public Source | RAW/STATUS bit | Enable/Mask/Force/Clear bit |
|---|---:|---:|
| Compare0 | 0 | 0 |
| Compare1 | 1 | 1 |
| Compare2 | 2 | 2 |
| Compare3 | 3 | 3 |
| Overflow | 4 | 4 |

R120/R130 报告层必须继续把 `IRQ_RAW.*`、`IRQ_STATUS.*`、`IRQ_DELIVERY.LATCHED_SOURCE` 和软件 `event_count` 分成不同来源字段。

### 3.3 DMA source mapping

| Logical `dma_request_source` | `DMA_HD_MUX.STM_DMA_HMUX` |
|---|---:|
| Overflow | 0（5..7按SVD同样回到Overflow） |
| Compare0 | 1 |
| Compare1 | 2 |
| Compare2 | 3 |
| Compare3 | 4 |

历史 ET6801 Unit/FPGA test 已有 `Compare0 -> AHB DMA -> TCYC value to memory` 路径，说明这一跨IP链路曾被实际使用；当前 Formal `P2_001` 已重新建立 Execution Mapping 与 Canonical Evidence，但仍必须取得 current-SHA HIL，不能直接继承历史 PASS。

---

## 第四章 ET6801 Mapping / Bench / Environment Gap

| Gap ID | Type | ET6801 当前事实 | 解除条件 |
|---|---|---|---|
| `stimer_instance_driver_coverage_gap` | IMPLEMENTATION | Hardware 6实例，current SDK validator仅允许0/1 | Driver/Wrap按Capability支持合法目标实例 |
| `stimer_capability_semantic_mapping_gap` | MAPPING | Capability只有identity/IRQ，Feature/Limit为空 | 把target SVD事实映射为公共Feature/Limit/Option/Parameter |
| `stimer_prescaler_limit_mapping_gap` | MAPPING | target SVD明确逻辑1..65535，但Machine Capability未发布 | Capability冻结min=1,max=65535并增加生成/审计回归 |
| `stimer_period_driver_width_gap` | CLOSED | Hardware period=32bit；当前测试补充Driver与Wrap均按32-bit范围校验并写入 | 保持32-bit边界校验；越界值由Driver在I/O前失败关闭 |
| `stimer_compare_driver_gap` | CLOSED | 原SDK Compare写寄存器问题已由隔离Test Driver Extension修正，Wrap只调用该接口 | 保持Compare threshold与event-width职责分离，并由P1_006验证 |
| `stimer_immediate_load_edge_semantic_gap` | MAPPING | Hardware采集TCLD上升沿；当前重复Set位行为未闭合 | 明确/实现每次PERIOD_UPDATE均产生新有效load pulse |
| `stimer_control_pulse_repeatability_gap` | IMPLEMENTATION | Clear/Latch/Compare Load等是脉冲型动作 | Driver/Service提供可重复pulse动作并用多次状态变化验证 |
| `stimer_irq_service_gap` | CLOSED | Firmware Service已提供Source级IRQ latch/event_count，并与RAW/STATUS分层保存 | 保持Source级Delivery Evidence；由P1_007验证 |
| `stimer_event_width_driver_gap` | CLOSED | Hardware支持OF/Compare width，正式SDK无配置API | Test Driver Extension、Wrap、Service和PC Driver已按1..256周期稳定语义闭合；外部脉宽测量仍属于Bench Gap |
| `stimer_event_route_bench_gap` | BENCH | STIMER0 Compare0..3历史XBAR→GPIO路由已出现；示波器Driver可用，但当前探头通道与DUT信号路由尚未绑定 | 冻结current board route、pin、示波器通道、探头倍率、触发电平、采样率和所有测试Source |
| `stimer_diagnostic_warning_semantic_gap` | MAPPING | OCWR告警字段存在但SVD描述自相矛盾 | ET6801更高权威资料或RTL/设计确认精确触发条件 |
| `stimer_atomic_status_snapshot_gap` | CLOSED | Chip Driver Test Extension对STM_STATUS_RPT执行单次原子读取，Wrap/Service只解析该Snapshot | 保持一次读取后再解析，禁止逐字段消费read-to-clear现场 |
| `stimer_dma_execution_mapping_gap` | CLOSED | Hardware mux + 历史真实DMA路径存在 | 公共Resolver、STIMER DMA Source选择、DMAMUX、DMA Channel与Destination数据链已闭合 |
| `stimer_emergency_trigger_mapping_gap` | MAPPING | XBAR有两组23-bit ERG enable，具体安全Source未冻结 | 指定安全可控Source、路由、刺激方法及禁止项 |
| `stimer_emergency_capture_cleanup_gap` | CLOSED | SYSC capture为只读；Test Driver Extension通过禁用ERG路由闭合清理，后续有效触发覆盖旧值，不向只读寄存器猜写清零 | 保持清理顺序：停止STIMER→禁用ERG路由→关闭外部激励 |
| `stimer_pause_overflow_boundary_bench_gap` | BENCH | Hardware优先级明确 | 建立可同步Pause/Overflow边界刺激和时序Observer |
| `stimer_debugger_bench_gap` | CLOSED | 公共DebugController已经通过J-Link执行两轮真实Halt/Resume，并记录实际halt window与调试器身份 | 保持Debugger动作与STIMER端点分离记录 |
| `stimer_debug_halt_behavior_gap` | FPGA_RTL_BEHAVIOR_GAP / HIL_FAIL | SVD定义PAUSE时CPU Halt应冻结、RUN_FREE时应继续；当前FPGA实测两轮Counter分别推进12,318,488和11,483,428，速率基本一致，PAUSE未冻结 | RTL/bit所有者确认CPU Halt信号是否真正接入STIMER及`STM_CPUHALT_MODE_R`语义；修复或说明后重跑P2_003，并在Silicon HIL独立验证 |
| `stimer_reference_observer_gap` | BENCH | P3长时绝对周期/漂移仍需要独立时钟参考；P1预分频比例已改为同一STIMER不同divider的内部计数速率比，不再依赖本Gap | Companion FPGA或示波器绑定到已审核事件路由，并冻结量化误差 |
| `stimer_long_run_reference_bench_gap` | ENVIRONMENT | 示波器与可编程电源接口可用，但长期事件路由、独立计数和Artifact链尚未闭合 | R5环境、独立Reference/Event Counter、稳定供电和Artifact retention闭合 |

---

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| STIMER_F_001 | SUPPORTED | SVD有6实例；当前ET6801运行时适配只发布SDK可安全访问的STIMER0/1 | ADAPTED | STIMER_P0_001, STIMER_P3_001 |
| STIMER_F_002 | SUPPORTED | ET6801逻辑divider=1..65535、静态配置；Runtime Capability发布最大divider，P1使用内部COUNT.LIVE速率比验证 | ADAPTED | STIMER_P1_001, STIMER_P3_001 |
| STIMER_F_003 | SUPPORTED | Period硬件宽度32-bit；隔离Test Extension与公共Wrap执行32-bit边界校验 | ADAPTED | STIMER_P0_002, STIMER_P1_002, STIMER_P1_004, STIMER_P3_001 |
| STIMER_F_004 | SUPPORTED | One-Shot/Free-Run已由公共Service/Formal Case表达 | ADAPTED | STIMER_P1_002, STIMER_P3_001 |
| STIMER_F_005 | SUPPORTED | 软件清零动作由公共Wrap/Service公开 | ADAPTED | STIMER_P1_003 |
| STIMER_F_006 | SUPPORTED | Pause/Resume由COUNT.LIVE分阶段证明 | ADAPTED | STIMER_P1_003 |
| STIMER_F_007 | SUPPORTED | Immediate/Shadow生效时机已由COUNT.LIVE与两轮自然Overflow形成硬件闭环；重复Immediate pulse仍作为独立Driver Known Issue保留，不扩大本Feature声明 | ADAPTED | STIMER_P1_004 |
| STIMER_F_008 | SUPPORTED | Live/Latch均32-bit；公共Case执行重复Latch并保存快照 | ADAPTED | STIMER_P1_005 |
| STIMER_F_009 | SUPPORTED | 4×32-bit Compare threshold；隔离Test Extension修正旧SDK写错寄存器问题 | ADAPTED | STIMER_P1_006 |
| STIMER_F_010 | SUPPORTED | OF/Compare各8-bit pulse-width；公共配置链已实现，连续数字Observer Bench尚未闭合 | ADAPTED | STIMER_P1_008 |
| STIMER_F_011 | SUPPORTED | 5 Source Enable/Mask/Raw/Status/Clear齐全并由公共端点表达 | ADAPTED | STIMER_P1_007 |
| STIMER_F_012 | SUPPORTED | 5 Source software-force由隔离Test Extension公开 | ADAPTED | STIMER_P1_007 |
| STIMER_F_013 | SUPPORTED | Overflow/Compare0..3可选DMA Request；公共执行映射与五类Source参数节点已实现 | ADAPTED | STIMER_P2_001 |
| STIMER_F_014 | SUPPORTED | Chip Driver Test Extension单次读取完整read-to-clear寄存器，公共Wrap只解析该Snapshot | ADAPTED | STIMER_P1_009 |
| STIMER_F_015 | SUPPORTED | CPU Halt时PAUSE/RUN_FREE策略与公共Driver/Service已实现，真实Debugger Bench已闭合；当前FPGA的PAUSE实测不冻结Counter | ADAPTED | STIMER_P2_003 |
| STIMER_F_016 | SUPPORTED | XBAR ERG route + SYSC capture硬件存在；公共Driver/Wrap/Service已实现逻辑路由、读值和禁用，ET6801默认Source mask保持0，安全Source仍待Bench确认 | MAPPING_GAP | STIMER_P2_002 |
| STIMER_F_017 | SUPPORTED | 5 Source共享硬件IRQ line；公共Service已保存Source级latch与event_count | ADAPTED | STIMER_P1_007, STIMER_P3_001 |
| STIMER_F_018 | SUPPORTED | 公共脉宽配置、短周期Free-Run、两次自然Compare Raw与原子read-to-clear诊断链已实现 | ADAPTED | STIMER_P1_010 |
| STIMER_F_019 | SUPPORTED | SVD明确Pause与Overflow同边界时Overflow优先并先回零；同步边界Observer仍缺 | MAPPING_GAP | STIMER_P1_003 |

说明：Feature 的`SUPPORTED`只表示ET6801 Hardware Truth已确认；`IMPLEMENTED / HIL_PENDING`表示平台链路已实现但尚不能写成硬件PASS。

---

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| STIMER_P0_001 | ADAPTED | Working-tree FPGA HIL PASS；Start/Stop与Live Count路径形成硬件证据 |
| STIMER_P0_002 | ADAPTED | Working-tree FPGA HIL PASS；32-bit Period与自然Overflow路径形成硬件证据 |
| STIMER_P1_001 | ADAPTED | Case动态读取Runtime divider边界，交错测量三轮COUNT.LIVE并比较中位速率比；无需外部接线，当前代码待Formal HIL重跑 |
| STIMER_P1_002 | ADAPTED | Working-tree FPGA HIL PASS；One-Shot/Free-Run生命周期与终态一致 |
| STIMER_P1_003 | ADAPTED | Working-tree FPGA HIL PASS；当前SPEC只验证基本Clear/Pause/Resume，同边界因果仍由F019 Gap保留 |
| STIMER_P1_004 | ADAPTED | Working-tree FPGA HIL PASS；Immediate当前周期生效、Shadow下一周期生效均由COUNT.LIVE与自然Overflow证明 |
| STIMER_P1_005 | ADAPTED | Working-tree FPGA HIL PASS；重复Latch与Canonical快照一致 |
| STIMER_P1_006 | ADAPTED | Working-tree FPGA HIL PASS；隔离Test Extension正确访问32-bit Compare寄存器 |
| STIMER_P1_007 | ADAPTED | Working-tree FPGA HIL PASS；Raw/Status/ISR latch/event_count形成分层证据 |
| STIMER_P1_008 | BENCH_GAP | Case已实现Compare0脉宽与stimer_output实测比例；仍需冻结DUT事件路由、探头通道和触发/采样配置 |
| STIMER_P1_009 | ADAPTED | Working-tree FPGA HIL PASS；自然Overflow、原子Snapshot与read-to-clear复核闭合 |
| STIMER_P1_010 | ADAPTED | Working-tree FPGA HIL PASS；两次自然Compare与Repeat状态生命周期闭合 |
| STIMER_P2_001 | ADAPTED | Working-tree FPGA HIL五个参数节点全部PASS；ISR清除前锁存、DMA Channel终态与Destination数据形成三重证据 |
| STIMER_P2_002 | BENCH_GAP | 公共Driver/Wrap/Service/PC Case已实现；Case通过`stimer_emergency_input`逻辑PulseStimulus触发，ET6801默认Source mask为0，运行前需Bench提供已审核安全ERG Source与路由 |
| STIMER_P2_003 | ADAPTED | 真实J-Link Halt/Resume与COUNT.LIVE执行链已闭合；当前FPGA专项HIL为FAIL，PAUSE和RUN_FREE两轮Counter均以相近速率推进。 |
| STIMER_P3_001 | BENCH_GAP | Formal Case已实现stimer_reference/stimer_output逻辑观测、Service IRQ累计与长时Artifact；运行前仍需Bench绑定逻辑信号和稳定时钟/供电 |

以上状态的含义是“当前最主要阻塞域”。`BENCH_GAP` 表示 Formal Case 已按真实接口实现，但运行所需的 Bench 绑定尚未具备；缺少接口的项目继续保持 `MAPPING_GAP` 或 `ENVIRONMENT_GAP`，不得伪造实现。

---

## 第七章 Current Review Conclusion

### 7.1 本轮已经冻结的分析结论

1. **公共设计边界重新收口。** 19个Feature、16个SPEC形成当前稳定基线；F017～F019分别承接IRQ Delivery、Compare Repeat状态和Pause/Overflow边界优先级。
2. **ET6801 目标边界纠正。** direct SVD 明确 `prescaler_divider=1..65535`，不再用 ET60157/其他芯片的 65536 结论覆盖目标事实。
3. **Compare Driver Bug 已隔离修复。** 原SDK Helper保持不动，测试补充接口在Driver Test Extension区按真实32-bit Compare寄存器实现。
4. **Period Driver Width Bug 已隔离修复。** 测试补充接口和公共Wrap只接受32-bit合法范围。
5. **IRQ Evidence 重新分层。** RAW / STATUS / ISR latch / event_count 不再合并成一个“IRQ成功”结论。
6. **Diagnostic Evidence 采用原子 Snapshot。** `STM_STATUS_RPT` read-to-clear，未来必须一次读取再解析，避免 FAIL 现场被早期读操作消费。
7. **Bench强度按 Feature 真正需求提升。** 事件脉宽、Pause/Overflow同边界、Debug Halt、长时精度都不能再由固定delay或单点软件读取替代。
8. **Emergency Capture 的代码链已实现，但ET6801运行时默认不发布该Feature。** `et6x_stimer` Test Driver Extension、STIMER Wrap、Service和PC Case均已闭合；由于当前没有批准的安全Source mask，Capability保持关闭，Bench确认后才能执行P2_002。

### 7.2 当前状态必须精确写为

```text
STIMER PUBLIC CONTRACT / CHIP ANALYSIS: UPDATED FOR CURRENT R120/R140 HUMAN-REVIEW BASELINE
16 ET_CASE_SPEC: IMPLEMENTED
Remaining 0 ET_CASE_PLAN
Formal Case Registry / test_stimer_p*.py: IMPLEMENTED
Previous Working-tree FPGA full HIL: EXECUTED / 27 executions / 22 PASS / 5 SKIP / 0 FAIL
Previous logical Case result: 11 PASS / 5 SKIP / 0 FAIL
Previous SKIP Cases: STIMER_P1_001, STIMER_P1_008, STIMER_P2_002, STIMER_P2_003, STIMER_P3_001
Previous SKIP Reasons: historical runner缺少stimer_reference/stimer_output observers、emergency-capture映射和debugger绑定
Previous Full HIL Evidence: artifacts/runs/20260821_171700_stimer_full_hil/tests/stimer/session.json
Targeted Debug-Halt HIL: STIMER_P2_003 / 1 execution / FAIL
Targeted Failure: PAUSE delta=12318488, RUN_FREE delta=11483428; both counters advanced during real J-Link Halt windows
Targeted HIL Evidence: artifacts/runs/20260822_140851_627657_stimer_formal_cases/tests/stimer
Firmware / Registry: et6801-silicon-common-v0.1 / d7dd2c5d
Exact committed SHA FPGA HIL: NOT_PROVEN / targeted source_revision=edfd188173e93b3a580ba1d30587795c2ca1749c and source_dirty=true
Current-SHA Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
Historical Unit/FPGA source: TRACEABLE DESIGN INPUT ONLY
```

上面的27-execution全量记录是早期Bench状态，不得继续把其中`STIMER_P2_003`的SKIP当作当前结论；Debugger绑定闭合后的最新专项结果是FAIL。`STIMER_P1_001`也已改为内部COUNT.LIVE速率比验证，历史SKIP不再有效，当前状态为NOT_EXECUTED。剩余`STIMER_P1_008`、`STIMER_P2_002`、`STIMER_P3_001`确实依赖外部物理观测或刺激Bench，可保留SKIP。

### 7.3 2026-08-22 Debug Halt行为诊断

1. PAUSE轮：真实J-Link Halt窗口为0.473677 s，`COUNT.LIVE`由597,494推进到12,915,982，delta=12,318,488。
2. RUN_FREE轮：真实J-Link Halt窗口为0.442484 s，`COUNT.LIVE`由609,341推进到12,092,769，delta=11,483,428。
3. Driver/Wrap映射复核：PAUSE与RUN_FREE分别按SVD语义配置`STM_CPUHALT_MODE_R=0/1`，Case没有直接操作寄存器，也没有以软件延时冒充Debugger Halt。
4. 结论：当前FPGA中两种策略的Counter速率基本一致，问题位于CPU Halt到STIMER的RTL/bit行为路径；Case保持严格FAIL，不通过放宽10%冻结阈值规避。

### 7.4 下一阶段入口条件

未来开始写 STIMER 代码前，至少先闭合：

```text
1. Machine Capability semantic mapping
2. STIM_DRV_002 compare bug
3. STIM_DRV_003 period width bug
4. repeatable control-pulse semantics
5. IRQ Service source-level evidence
6. event-width external observer bench route
7. emergency safe source / cleanup mapping
8. debugger / long-run bench contracts（对应P2/P3）
```

每解除一个 Gap，只更新对应 Feature/Case 的适配状态；不得因为某个 Driver API 修好就批量把其余 PLAN 改成 SPEC。

### 7.5 当前未通过测试记录

时间：2026-08-24 20:42 CST

| Case | 测试环境 | 实际硬件现象 | 已排除的软件链路问题 | 当前判定 | 闭环条件 |
|---|---|---|---|---|---|
| `STIMER_P2_003` | ET6801 FPGA、真实J-Link Halt/Resume、PAUSE与RUN_FREE两轮对照 | PAUSE轮Halt 0.473677 s期间Counter增加12,318,488；RUN_FREE轮Halt 0.442484 s期间增加11,483,428，两轮均以相近速率运行 | Driver/Wrap已按SVD分别配置`STM_CPUHALT_MODE_R=0/1`；Case使用真实Debugger Halt，不是软件延时模拟 | `FPGA_RTL_BEHAVIOR_GAP / HIL_FAIL` | RTL/bit所有者确认CPU Halt信号是否接入STIMER以及PAUSE语义；修复或说明后重跑，并在Silicon独立验证 |

证据位于`artifacts/runs/20260822_140851_627657_stimer_formal_cases/tests/stimer`。Case保持冻结阈值和严格FAIL，不通过放宽断言掩盖PAUSE未生效。

2026-08-24独立固件复测在J-Link持续连接状态下分别执行PAUSE和RUN_FREE两次真实Debugger Halt；PAUSE轮Counter增量=`0x70E87DFC`，RUN_FREE轮增量=`0x27D5C292`，两轮均明显推进。该结果再次证明PAUSE没有冻结Counter，不属于串口通信、BootROM或PFLASH加载问题；精确速率仍以Formal HIL时间线为权威。证据：`artifacts/runs/20260824_204258_094556_manual_et6801_uart_crc/manual/uart_crc.log`。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-26 12:15 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-22 14:08 CST` | `edfd188173e93b3a580ba1d30587795c2ca1749c` | `true` | `artifacts/runs/20260822_140851_627657_stimer_formal_cases/tests/stimer/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 16 | 1 | 0 | 1 | 0 | 15 | 1 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `STIMER_P1_001` | FPGA | NOT_EXECUTED | `STIMER_F_002` / 预分频比例 | 本次定向HIL未执行重构后的内部速率比Case | 原外部reference依赖已删除，新Case尚未完成Formal HIL | 运行三轮divider矩阵并按COUNT.LIVE中位速率比判定 | `pc/et_test_platform/test_cases/stimer/test_stimer_p1.py` |
| `STIMER_P2_003` | FPGA | FAIL | Debugger Halt模式 | PAUSE与RUN_FREE两轮真实Halt期间Counter均继续推进；独立固件复测得到相同方向的结果 | 当前FPGA的CPU Halt信号到STIMER路径或Pause语义未闭合 | RTL/bit确认该信号路径后重测，并在Silicon独立验证 | `artifacts/runs/20260824_204258_094556_manual_et6801_uart_crc/manual/uart_crc.log` |
<!-- ET_CHIP_TEST_STATUS_END -->

### 2026-08-26 12:15 CST SKIP分类复核

| Case ID | 当前分类 | 复核结论 |
|---|---|---|
| `STIMER_P1_001` | NOT_EXECUTED | 已改为芯片内部COUNT.LIVE速率比验证，不再需要stimer_reference接线；待Formal HIL重跑。 |
| `STIMER_P1_008` | SKIP | 必须观测STIMER事件输出脉宽，当前缺少DUT输出路由和示波器/FPGA采样接线。 |
| `STIMER_P2_002` | SKIP | 必须从外部向STIMER紧急捕获输入施加安全脉冲，当前缺少已审核Source路由和物理激励接线。 |
| `STIMER_P2_003` | FAIL | Debugger绑定已闭合，PAUSE和RUN_FREE下Counter均继续推进。 |
| `STIMER_P3_001` | SKIP | 长时稳定性需要独立参考时钟、事件输出观测和稳定供电Bench接线。 |

历史Full HIL的5个SKIP保留为原始Runner事实；当前有效分类为1个NOT_EXECUTED、3个物理Bench SKIP和1个FAIL。
