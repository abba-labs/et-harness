# DMA Contract Human Review Freeze

> 状态：**DMA HUMAN REVIEW / CONTRACT FREEZE**  
> 日期：2026-08-19  
> 分支：`review_code`  
> 基线 SHA：`17f8e30e9be65c272c3b0bdf3eef0c1ca9890f1a`  
> 推广计划：`report/plans/20260819_ip_optimization_rollout_plan.md`  
> 前序已闭环 IP：AES Pilot、CRC

---

## 1. 本轮边界

本轮只冻结 DMA 的 Human Review / Contract / Evidence 结论，不宣称当前 SHA 的 FPGA / Silicon HIL 已执行。

用户明确批准：由于当前环境无法执行仓库本地 `compile_task_context.py` 和真机 HIL，本轮暂时沿用 AES / CRC 的做法，允许跳过当前环境无法完成的 Task Context 本地编译步骤，但不得把未执行的软件门禁、CI 或 HIL 写成 PASS。

固定边界：

```text
允许：
- Human Review
- dma.md Contract重写
- ET6801 endpoint/register mapping梳理
- 既有硬件事实的Canonical Evidence补录
- 已审核Case的最小行为增强
- Report/Excel软件链闭合

禁止：
- 用历史HIL替代当前SHA HIL
- 为让Case通过而弱化断言或扩大SKIP
- 在DMA Case里直接读寄存器
- 因单颗芯片事实污染公共DMA语义
- 因CRC已经闭环而机械复制CRC endpoint/Case/Oracle
```

当前验证状态固定写法：

```text
SOURCE / DESIGN REVIEW: IN_PROGRESS
SOFTWARE GATE: NOT_EXECUTED
CI: NOT_VERIFIED
FPGA HIL: NOT_EXECUTED / NOT_VERIFIED
Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
```

---

## 2. 当前真实基线

### 2.1 Formal Case / PLAN

```text
Formal SPEC = 28
ET_CASE_PLAN = 11
公共 dma.md = 存在
ET6801_dma.md = 存在
DMA Case Registry = 28个已注册Formal Case
```

### 2.2 ET6801 硬件基础事实

```text
DMA Controller = 2
Channel / Controller = 8
Total Channel = 16
NORMAL / ACC = 同一Controller两套访问别名
```

分类中断包括：

```text
TRANSFER_DONE
BLOCK_DONE
SOURCE_TRANSACTION
DESTINATION_TRANSACTION
ERROR
COMBINED physical route
```

ET6801 DMA 芯片文档已经记录 `SAR/DAR/CTL/CFG`、LLI、Gather/Scatter、RAW/STATUS/MASK/CLEAR、软件握手、组件身份和能力寄存器等事实。

### 2.3 历史 HIL

DMA 存在 2026-08-02 / 2026-08-03 FPGA 历史验证，其中 2026-08-03 报告记录当前当时可安全执行实例 `68 PASS / 0 FAIL / 9 SKIP`。

这些记录只作为 Historical Evidence 使用，不替代本轮精确 SHA 的 HIL。

---

## 3. 现行 Human Review 标准

DMA 后续固定继承 AES / CRC 已验证的 Review Discipline：

1. 先 Human Review Contract，再碰代码。
2. 每个 Formal Case 的 `method.steps` 必须按真实执行顺序写 6～8 条。
3. `method.observations` 只保留最小充分硬件证明，并说明 endpoint、Expected 和 Proof Meaning。
4. 决定性 Assert 前必须先保存关键 Canonical Measurement / Observation。
5. Service / ISR 事实、寄存器事实、Peer 事实和软件 Oracle 分来源记录，禁止互相冒充。
6. Artifact 是单次完整 Snapshot，不是 Append Log。
7. `ET_CASE_REPORT` 每 Case 只保留 1～4 个真正支撑结论的字段，summary 写硬件结论而不是“验证完成”。
8. Public `dma.md` 保持芯片中立；ET6801 实际寄存器/Field 映射只进入 `ET6801_dma.md`。

---

## 4. 28 个 Formal Case 冻结分类

| Case | 冻结分类 | Human Review 决策 |
|---|---|---|
| DMA_P0_001 | RECORD_ONLY + Feature Gap | Capability / Component Snapshot 已真实读取；补 Canonical Evidence。Exact FIFO Depth 动态证明单独保留 Gap |
| DMA_P0_002 | CASE_CHANGE | 补完整 Controller/Channel 生命周期、Free Channel、FIFO Empty 和重复恢复证明 |
| DMA_P1_001 | RECORD_ONLY | 全 Channel 原子启动、逐通道数据和 Free 已有 |
| DMA_P1_004 | RECORD_ONLY | TRANSFER_DONE、数据、Service IRQ、Channel终态已有 |
| DMA_P1_005 | RECORD_ONLY | BLOCK_DONE、单节点LLI、数据、终态已有 |
| DMA_P1_006 | RECORD_ONLY | before/masked/cleared/enabled 的 RAW/STATUS/MASK 快照已完整存在 |
| DMA_P1_007 | RECORD_ONLY | Reload、BLOCK_DONE>=2、地址Snapshot、数据已有；不得声称未实际采样的逐Block轨迹 |
| DMA_P1_008 | RECORD_ONLY | Gather布局、Guard、Free已有 |
| DMA_P1_009 | RECORD_ONLY | Scatter布局、Guard、Free已有 |
| DMA_P1_010 | CASE_CHANGE | 数据正确不能单独证明FIFO Mode生效；需稳定配置读回 |
| DMA_P1_011 | RECORD_ONLY | Descriptor DONE before/after、非控制字段、数据已有 |
| DMA_P1_014 | RECORD_ONLY | Width + inc/dec/fixed最终布局形成强Oracle |
| DMA_P1_015 | CASE_CHANGE | 数据结果不能证明Burst编码真正写入硬件；需Burst/Block配置读回 |
| DMA_P1_016 | DOC_ONLY | 当前代码实际是Resource SRAM M2M + TFR，不是TCM地址转换；解绑F023 |
| DMA_P1_017 | RECORD_ONLY | 7组非法参数拒绝层级 + 合法恢复传输已有 |
| DMA_P2_001 | RECORD_ONLY | 2/3/4节点有限LLI最终数据和Descriptor已有 |
| DMA_P2_002 | RECORD_ONLY | Source-only / Destination-only LLI最终布局已有 |
| DMA_P2_004 | RECORD_ONLY | Combined Route + IRQ latch + 数据已有 |
| DMA_P2_005 | RECORD_ONLY | P2M + SOURCE_TRANSACTION/TFR IRQ + UART Peer刺激已有 |
| DMA_P2_006 | RECORD_ONLY | M2P + DESTINATION_TRANSACTION/TFR IRQ + Peer Capture已有 |
| DMA_P2_008 | RECORD_ONLY | 1/17/257 Byte M2P + Peer Capture已有 |
| DMA_P2_009 | RECORD_ONLY | 1/17/257 Byte P2M + Peer Stimulus已有 |
| DMA_P2_010 | RECORD_ONLY | P2P双UART最终Peer数据Oracle已有 |
| DMA_P2_011 | CASE_CHANGE | “PC写Request”不能证明“DMA逐Item推进”；需每次Request对应真实进度证明 |
| DMA_P2_012 | CASE_CHANGE + Feature Gap | Hardware/Software Mode需增加因果负对照；Polarity没有真实刺激，不得声称覆盖F027 |
| DMA_P2_013 | SEMANTIC / MAPPING GAP | NORMAL/ACC Alias行为存在，但公共稳定Feature身份与跨芯片适用条件需要先冻结 |
| DMA_P2_015 | DOC_ONLY | 保留CRG扰动后的DMA Recovery Case；绑定既有Module/Channel/M2M Feature，不新增Reset Feature |
| DMA_P3_007 | RECORD_ONLY | 20轮混合M2M充分；需保证中途FAIL前已形成Evidence不丢失 |

冻结统计：

```text
RECORD_ONLY             = 20
CASE_CHANGE             = 5
DOC_ONLY                = 2
SEMANTIC / MAPPING GAP  = 1
--------------------------------
Formal Case Total       = 28
```

---

## 5. Feature / Case 语义冻结

### 5.1 DMA_P1_016 不再证明 TCM 地址转换

当前 Case 只使用 Resource Driver 分配的普通 Buffer，不能证明 ITCM / DTCM CPU Address 到 DMA Bus Alias 的芯片转换。

冻结决策：

```text
DMA_P1_016
- 移除 DMA_F_023
- 绑定稳定 M2M + TRANSFER_DONE + Channel终态语义

DMA_F_023 TCM地址转换
- 只由 DMA_P2_014 继续承载规划
- 保持 MAPPING GAP / PARTIAL_ADAPTATION
- 等 CORE1 + safe TCM windows + address alias evidence 后解除
```

禁止为了闭合 P1_016 临时扩 Resource Framework 或在公共 Case 中加入 ET6801 地址常量。

### 5.2 DMA_P2_012 不再冒充 Handshake Polarity

当前实现只参数化：

```text
HARDWARE
SOFTWARE
```

没有 active-high / active-low 的独立可控 Request Source。

冻结决策：

```text
DMA_P2_012 -> DMA_F_028 hardware/software handshake selection
DMA_F_027 handshake polarity -> OPEN FEATURE GAP
```

Polarity 只有在 Bench / Peer 提供可控极性源后才能重新进入 Formal Proof。

### 5.3 DMA_P2_015 不新增 Reset Feature

P2_015 是已有 DMA 能力经过 CRG Clock Gate / Reset 扰动后的恢复测试。

冻结 FeatureRefs：

```text
DMA_F_003 Module Enable
DMA_F_004 Channel Lifecycle
DMA_F_005 Channel Status
DMA_F_007 M2M Data Path
```

独立 Case 的理由来自不同的 Precondition / Recovery / Cleanup 路径，不需要制造新的 DMA Reset Feature。

### 5.4 DMA_P3_007 不新增 Stability Feature

P3_007 对已有 Feature 做20轮组合压力：

```text
DMA_F_001 Controller集合
DMA_F_002 Channel集合
DMA_F_005 Channel状态
DMA_F_007 M2M
DMA_F_008 Width
DMA_F_010 Burst
DMA_F_013 FIFO Mode
```

重点是 Evidence 生命周期与中途失败现场，不新增稳定 Feature ID。

---

## 6. 五个允许最小行为增强的 CASE_CHANGE

### 6.1 DMA_P0_002 —— 基础生命周期闭环

目标链：

```text
find_free_channel
-> initial DMA_CHANNEL_STATUS.FREE / FIFO_EMPTY
-> Controller Enable + Configure
-> first M2M
-> final FREE / FIFO_EMPTY
-> Disable
-> Re-enable + second distinct payload
-> second M2M success + final FREE
```

优先复用现有 Driver，不为本 Case 增加 Framework。

### 6.2 DMA_P1_010 —— FIFO Mode 配置证明

旧证明：

```text
Configure FIFO Mode -> Data Match -> PASS
```

不足以排除硬件忽略 `fifo_mode` 参数。

目标 Proof：

```text
Expected FIFO Mode
-> Configure
-> DMA_CHANNEL_CFG.FIFO_MODE readback
-> Expected == Actual
-> M2M
-> Destination Data Match
-> Channel Free
```

若当前稳定 Driver Snapshot 无法解析 FIFO Mode，再单独进入 Driver Task，不允许 Case 直接访问寄存器。

### 6.3 DMA_P1_015 —— Burst / Block 配置证明

目标 Proof：

```text
Expected Burst / Block Count
-> Configure
-> DMA_CHANNEL_CTL.SOURCE_BURST
-> DMA_CHANNEL_CTL.DESTINATION_BURST
-> DMA_CHANNEL_CTL.BLOCK_SIZE
-> Start / Wait
-> Destination Data Match
-> Channel Free
```

### 6.4 DMA_P2_011 —— Software Handshake 逐Item因果证明

旧实现只能证明最终4 Byte完成且PC执行过8次请求写。

目标 Proof：

```text
Software Handshake Mode
-> Start DMA
-> snapshot progress before request
-> issue one request item
-> bounded wait for exactly one forward progress
-> repeat for each item
-> Peer Capture full payload
-> Channel Free
```

优先复用 `channel_snapshot_get()` 的稳定地址进度事实。

### 6.5 DMA_P2_012 —— Software Mode 负对照

目标增加：

```text
Software Mode Configure
-> Start
-> no software request
-> bounded observe: no transfer progress
-> issue software requests
-> observe progress
-> Peer Capture correct
-> TRANSFER_DONE + Channel Free
```

通过“无Request不前进 / 有Request才前进”排除实际上仍在Hardware Handshake运行的替代解释。

---

## 7. 稳定 Canonical Endpoint 冻结

公共 DMA Contract 后续优先使用以下芯片中立 endpoint：

```text
DMA_CAPABILITIES.FEATURES
DMA_CAPABILITIES.CHANNEL_COUNT
DMA_CAPABILITIES.MAX_TRANSFER_COUNT
DMA_CAPABILITIES.IRQ_EVENTS

DMA_COMPONENT.DMA_ID
DMA_COMPONENT.COMPONENT_ID
DMA_COMPONENT.CHANNEL_PARAMS[n]
DMA_COMPONENT.MULTI_BLOCK_PARAMS
DMA_COMPONENT.MAX_BLOCK_SIZE_PARAMS

DMA_CHANNEL_STATUS.FREE
DMA_CHANNEL_STATUS.FIFO_EMPTY
DMA_CHANNEL_STATUS.IRQ_EVENTS

DMA_CHANNEL.SOURCE_ADDRESS
DMA_CHANNEL.DESTINATION_ADDRESS
DMA_CHANNEL.LINKED_LIST_ADDRESS

DMA_CHANNEL_CFG.FIFO_MODE
DMA_CHANNEL_CTL.SOURCE_BURST
DMA_CHANNEL_CTL.DESTINATION_BURST
DMA_CHANNEL_CTL.BLOCK_SIZE

LLI_DESCRIPTOR.DONE

IRQ_RAW.<Event>
IRQ_STATUS.<Event>
IRQ_MASK.<Event>
IRQ_COMBINED.STATUS

ISR.LATCHED.<Event>
ISR.EVENT_COUNT

DMA_DESTINATION_DATA
PEER_UART.RX_CAPTURE
```

Evidence 来源边界：

- PC Expected / 参数：Measurement / Oracle；
- DMA register / typed status：DUT Observation；
- ISR latch：Service/ISR delivery evidence；
- event_count：Measurement，不冒充寄存器；
- UART Peer Capture：Peer Observation；
- Runtime Capability：目标侧只读能力快照，不冒充单一寄存器。

---

## 8. ET6801 Endpoint Mapping 目标

后续 `ET6801_dma.md` 需要把稳定 endpoint 映射到实际寄存器 / Field，包括但不限于：

```text
DMA_COMPONENT.DMA_ID
-> DMAIDREG

DMA_COMPONENT.COMPONENT_ID
-> DMACOMPSID

DMA_COMPONENT.CHANNEL_PARAMS[n]
-> DMA_COMP_PARAMS_CHn

DMA_CHANNEL.SOURCE_ADDRESS
-> SARx

DMA_CHANNEL.DESTINATION_ADDRESS
-> DARx

DMA_CHANNEL.LINKED_LIST_ADDRESS
-> LLPx

DMA_CHANNEL_CFG.FIFO_MODE
-> CFGx_L.FIFO_MODE

DMA_CHANNEL_CTL.SOURCE_BURST
-> CTLx_L.SRC_MSIZE

DMA_CHANNEL_CTL.DESTINATION_BURST
-> CTLx_L.DEST_MSIZE

DMA_CHANNEL_CTL.BLOCK_SIZE
-> CTLx_H.BLOCK_TS

LLI_DESCRIPTOR.DONE
-> CTLx_H.DONE

IRQ_RAW.TRANSFER_DONE
-> RAWTFR.<channel>

IRQ_STATUS.TRANSFER_DONE
-> STATUSTFR.<channel>

IRQ_MASK.TRANSFER_DONE
-> MASKTFR.<channel>
```

具体 Field 名最终以 SVD / ET6801 SDK / Wrap 的直接适用证据核定，禁止凭历史名称猜写。

---

## 9. Resource Level 修正

R2 表示片内 Peer 或固定板级 Passive Loop；R4 表示外部仪器或电气测量。

DMA 的 UART1/UART2 固定板级 Peer Case 不使用示波器/仪器作为 PASS Oracle，因此以下 Formal Case 目标 Resource Level 统一为 R2：

```text
DMA_P2_005
DMA_P2_006
DMA_P2_008
DMA_P2_009
DMA_P2_010
DMA_P2_011
DMA_P2_012
```

---

## 10. ET_CASE_REPORT 重写原则

当前 DMA Report 仍有大量 `summary: ...验证完成。` 和只显示软件计数而不显示关键硬件事实的问题。

后续固定：

1. summary 写硬件结论，不写“验证完成”。
2. IRQ Case 优先展示 Raw / Status / ISR latch / Event Count 中真正决定结论的1～4项。
3. 数据路径优先展示 Expected/Actual Hash或Data Match + Channel终态。
4. 配置类 Case 必须展示实际配置读回，不允许只展示请求参数。
5. Peer Case 的 Actual 必须保留 Peer source identity。
6. PASS/FAIL 使用同一字段模板。

示例：

```text
DMA_P1_006
旧：interrupt mask、raw/status 与 pending clear 验证完成。

新结论：
TRANSFER_DONE在Mask关闭时RAW置位但STATUS保持0，Clear后RAW/STATUS清零，重新Enable后Mask位恢复。
```

---

## 11. 当前 Open Gap

### 11.1 DMA_F_023 TCM / Core Address View

```text
Hardware: SUPPORTED
Platform: PARTIAL_ADAPTATION / MAPPING_GAP
解除条件：CORE1执行映射 + safe ITCM/DTCM destructive window + CPU/DMA alias evidence
```

### 11.2 DMA_F_027 Handshake Polarity

```text
Hardware: SUPPORTED
Platform: PARTIAL_ADAPTATION
解除条件：可控 active-high / active-low request source + 独立进度/数据Observer
```

### 11.3 DMA_F_033 Exact FIFO Depth Dynamic Proof

ET6801 Capability 已声明 CH0/1=64、CH2..7=16，但 P0_001 目前主要证明 Component Params / Capability 自洽。

在没有独立安全动态 Oracle 前：

```text
静态/组件能力识别可以报告
但不得把“exact FIFO physical depth动态验证”写成已闭环
```

---

## 12. 下一步实施顺序

冻结后按以下顺序实施，不重新扩大 Scope：

```text
1. 重写 test_case_doc/dma/dma.md 的28个 Formal SPEC
   - 1~3 Inputs
   - 6~8 Steps
   - atomic Observations
   - 2~5 Pass Criteria
   - failure_observations
   - ET_CASE_REPORT

2. 同步 ET6801_dma.md endpoint -> register/field mapping

3. 先处理20个 RECORD_ONLY
   - record_property
   - record_observation
   - assert前记录
   - final one-shot Artifact

4. 处理2个 DOC_ONLY

5. 逐个处理5个 CASE_CHANGE
   - 只按本文冻结的最小Proof增强
   - 如需Driver/Wire/Wrap扩围，停止并单独评审

6. P2_013单独完成Semantic/Mapping Review

7. 软件门禁与Report Regression

8. HIL保持NOT_EXECUTED，直到真实环境可用
```

---

## 13. Human Review Gate

本文件冻结的目标不是证明 DMA 已经闭环，而是冻结“下一步允许怎么改”。

后续实现不得自行改变：

```text
28个Formal Case身份
20 / 5 / 2 / 1分类
P1_016解除TCM错绑
P2_012解除Polarity错绑
P2_015不新增Reset Feature
P3_007不新增Stability Feature
F023 / F027 / F033保留真实Open Gap
```

任何超出上述边界的新 Driver / Firmware / Wire / Capability 变化，必须先停止当前 Case 优化并重新评审。
