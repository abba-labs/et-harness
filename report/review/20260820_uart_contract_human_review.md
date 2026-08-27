# UART Contract Human Review — 2026-08-20

> Status: **HUMAN REVIEW FREEZE / IMPLEMENTATION NOT YET CLOSED**  
> Branch: `review_code`  
> Audit baseline HEAD: `c217e7d6a21f171329f5bfcab6ca5379754fc1de`  
> Current FPGA/Silicon HIL: **NOT_EXECUTED / NOT_VERIFIED**
>
> 本记录冻结 UART 当前 33 个已注册 Formal SPEC 的 Human Review 结论。它只决定“现有行为是否足够、需要补什么 Evidence、哪些 Case 才允许改变行为”；不把历史测试、静态 Capability 或文档声明冒充当前精确 SHA 的硬件 PASS。

## 1. Baseline

当前公共与实现基线：

```text
Public Feature             = 49
Registered Formal SPEC     = 33
ET_CASE_PLAN               = 7
Total public Case catalog  = 40

P0 Formal SPEC             = 4
P1 Formal SPEC             = 17
P2 Formal SPEC             = 9
P3 Formal SPEC             = 3
```

33 个 Registry Case 与当前 `test_uart_p0.py / p1.py / p2.py / p3.py` 一一存在；7 个未实现 Case 继续保持 PLAN：

```text
UART_P3_001  RS485 transfer modes
UART_P3_002  RS485 DE/RE polarity
UART_P3_003  RS485 turnaround timing
UART_P3_004  SIR normal mode
UART_P3_005  low-power SIR
UART_P3_006  absolute baudrate / bit timing
UART_P3_008  protection / register timeout recovery
```

这些 PLAN 当前分别受 RS485 收发器/方向观察、独立时序 Observer、SIR 路径、绝对时钟 Observer、权限与 Fault Recovery Contract 等条件阻塞；本轮不得为了关闭 UART 而升级为 SPEC。

## 2. Human Review classification

本轮主分类冻结为：

```text
RECORD_ONLY = 28
CASE_CHANGE = 5
----------------
Total       = 33
```

没有为了统一格式机械增加 UART 硬件动作。Case 的 Feature 绑定过强、报告结论过强或未覆盖子能力作为独立 Contract/Feature Gap 记录，不强行扩大 Case。

| Case | 主分类 | Human Review 结论 |
|---|---|---|
| UART_P0_001 | CASE_CHANGE + Feature binding gap | 当前源码只读 Runtime Capability，尚不能充分证明“组件身份”；最小增强为初始化后读取 `snapshot_get()` 并记录 component parameter/version/type/scratch。`UART_F_003` 普通/别名地址视图仍属于 Capability/Chip Mapping；`UART_F_043` Scratch **读写**不能仅靠 Snapshot 读值宣称闭合，若无稳定写 API 则从本 Case 解绑并保留 Gap。 |
| UART_P0_002 | RECORD_ONLY + Contract narrowing | 软件复位、身份稳定、FIFO 终态和 1-byte loopback 恢复动作充分；但代码是“reset 后显式重新 initialize 8N1”，不能写成证明硬件 reset 后天然 default 8N1；也没有独立 RX/TX FIFO reset 动作，不应由本 Case 单独承诺 F014。 |
| UART_P0_003 | RECORD_ONLY | 1/16/17/64 Byte 内部 loopback 数据路径充分；需要把 raw capture、transfer count、FIFO/terminal facts 在 Assert 前进入 Canonical Evidence。Loopback disable 仅作为 cleanup，不夸大为独立 disable 因果测试。 |
| UART_P0_004 | RECORD_ONLY | DUT↔Peer 双向 64 Byte 行为充分；Peer Capture 与 DUT Capture 分来源记录。 |
| UART_P1_001 | RECORD_ONLY + Feature wording gap | DUT reset/reinit 后内部恢复 + Peer→DUT + Peer identity unchanged 足够证明 DUT/Peer 隔离；当前没有独立 UART0 Control 硬件身份 Observation，因此 F046 报告强度不得写成“Peer 和 Control 均被独立硬件观测”。后续控制命令持续可达可作为平台存活事实，但不是 UART0 register proof。 |
| UART_P1_002 | RECORD_ONLY | RX_READY 数据、Service IRQ session/event 与无 fault 行为已存在；需区分 UART 数据 Observation 与 ISR/Service Measurement。 |
| UART_P1_003 | RECORD_ONLY | TX_READY 数据和 IRQ session 行为已存在；同样需分离 Service event_count 与硬件/数据 Observation。 |
| UART_P1_004 | CASE_CHANGE | 当前每个 RX threshold 只发送“恰好 threshold”字节并观察事件，不能区分真实阈值行为与其他 RX 事件原因。最小增强：每个代表阈值至少形成 `threshold-1` 负对照 + `threshold` 正对照，并保持有界观察窗口。 |
| UART_P1_005 | CASE_CHANGE | 当前每个 TX threshold 只发送大于阈值的数据并观察 TX_READY，不能证明阈值边界。最小增强应利用现有 Halt / write_partial / TX FIFO level / IRQ state 构造可审计的 threshold 触发前后条件；若无法形成确定 in-flight FIFO 状态，则保留 Feature Gap，不以单次 TX_READY 冒充阈值证明。 |
| UART_P1_006 | RECORD_ONLY | RX threshold=14、仅送 2 Byte、等待 CHARACTER_TIMEOUT 的因果链较强；数据与 IRQ session 分来源保存即可。 |
| UART_P1_007 | RECORD_ONLY | ODD/EVEN parity mismatch → PARITY error + LINE_ERROR → normal parity recovery，行为充分。 |
| UART_P1_008 | RECORD_ONLY | Bench 先 Gate deterministic stop mismatch，再验证 FRAMING/LINE_ERROR 与恢复，行为充分；没有 bench stimulus 时继续合法 SKIP。 |
| UART_P1_009 | RECORD_ONLY | RX 压力 → OVERRUN/LINE_ERROR → software reset/recovery，行为充分；关键 error/status 必须在 Assert 前记录。 |
| UART_P1_010 | RECORD_ONLY | Peer Break stimulus → DUT BREAK/LINE_ERROR → release/recovery，行为充分。 |
| UART_P1_011 | RECORD_ONLY + Contract narrowing | 当前源码证明 IRQ source enable/disable 与 Service session 状态；`irq_config()` 重配置会重建 Service evidence，不能把 `enabled_mask` 清零写成“硬件 pending W1C/源条件清除”。F028 的“稳定清除语义”应由各源真实消费/恢复 Case 共同证明，不由本 Case 冒充一个通用 pending-clear register test。 |
| UART_P1_012 | RECORD_ONLY | `busy_detect_trigger()` 走隔离 Test Driver Extension，返回 `pre_trigger_usr / observed_iir / observed_usr / trigger_count / cleared / recovered` 等事实；现有行为无需搬到 PC 重做。Canonical Evidence 必须优先记录三个 raw hardware fields，`busy_observed / interrupt_observed / cleared / recovered` 作为目标侧派生 Measurement，不把 Bool 冒充寄存器。 |
| UART_P1_013 | CASE_CHANGE | 当前仅 `halt=True -> snapshot -> halt=False -> snapshot -> 之后再传输`，没有证明 Halt 期间 TX 路径真的暂停。最小增强需在 Halt 窗口内形成可观测的“不前进/不发送”负对照，再解除 Halt，让同一待发送数据继续并完成；不能只证明 resume 后还能通信。 |
| UART_P1_014 | RECORD_ONLY | 5/6/7/8 bit、1/1.5/2 stop、parity 代表组合的双向数据行为充分；这是端到端兼容帧证明，不冒充寄存器 readback。 |
| UART_P1_015 | RECORD_ONLY | 两端共同范围内多波特率双向数据充分证明“可配置并能通信”；它不证明绝对 bit-time/ppm，绝对精度继续只属于 P3_006 PLAN。 |
| UART_P1_016 | RECORD_ONLY + Feature binding gap | 1/15/16/17/32 Byte 边界数据与 RX FIFO terminal level 已存在；可证明 FIFO 数据路径/计数状态，不把 16 Byte 历史/静态深度包装成独立动态 physical-depth Oracle，也不宣称独立 FIFO reset。 |
| UART_P1_017 | RECORD_ONLY | 7 个非法公共 API 输入被拒绝 + 合法 loopback 恢复充分；拒绝计数是 Measurement，恢复数据是 DUT Observation。 |
| UART_P2_001 | RECORD_ONLY | UART TX DMA Route + DMA TFR + Peer Capture + Channel Free 行为充分；UART/DMA/SYSCTRL/Peer 证据必须分来源。 |
| UART_P2_002 | RECORD_ONLY | UART RX DMA + Guard + memory actual + DMA TFR/Free 行为充分；data_match/guards_intact 为 Measurement。 |
| UART_P2_003 | RECORD_ONLY | 双 Channel atomic mask start + 双向实际数据 + Guards + terminal states 充分；不宣称精确重叠时间。 |
| UART_P2_004 | RECORD_ONLY | 双向 9-bit 元素逐项保持第9位 + normal recovery，行为充分。 |
| UART_P2_005 | CASE_CHANGE | Match 路径充分；Mismatch 当前使用固定 `sleep(0.05)` 后单次 `RX_FIFO_LEVEL==0`，存在“尚未到达”与“已被过滤”不可区分。最小增强改为有界负对照窗口/稳定采样，证明不匹配地址后的数据在完整观察窗口内未进入 RX，再执行恢复。 |
| UART_P2_006 | RECORD_ONLY | CTS not-ready 阶段反复 `write_partial` 直到 0、恢复 RTS 后同一 pending 数据继续完成，已经具备因果暂停/恢复证明；补 Canonical Evidence 即可。 |
| UART_P2_007 | RECORD_ONLY + Feature coverage gap | 内部 Modem loopback 已充分证明 RTS→CTS、DTR→DSR 当前值与 Delta read-to-clear；源码明确 RI/DCD 未刺激。因此 F034 只能报告 CTS/DSR 已覆盖，RI/DCD 保留显式 Open Gap。 |
| UART_P2_008 | RECORD_ONLY | Software reset 前后身份 + normal data recovery 行为充分。 |
| UART_P2_010 | RECORD_ONLY | 9-bit address match + NINE_BIT_ADDRESS Service IRQ session + RX data + disable/recovery 行为充分；Service pending/active 与真实硬件 IIR/LSR 不混写。 |
| UART_P3_007 | RECORD_ONLY | Shadow FIFO enable/readback/disable + normal FIFO recovery 行为充分；typed Shadow state 是稳定配置 Observation。 |
| UART_P3_009 | RECORD_ONLY | FAR enable、HTX、TFR read、RFW inject、FAR disable、normal recovery 行为充分；Direct FIFO 各事实需原子记录。 |
| UART_P3_010 | RECORD_ONLY | 20 轮双向 4/32/257 Byte 行为充分；当前逐轮 Assert、最终才写 summary，FAIL 会丢前序现场。必须逐轮在决定性 Assert 前记录 Canonical Evidence，最终 Artifact 只写一次完整 Snapshot。 |

## 3. Five approved CASE_CHANGE

只有下列 5 个 Case 获准在后续实现阶段做最小硬件行为增强：

```text
UART_P0_001  补真正组件身份 Snapshot；同时纠正 F003/F043 过强绑定
UART_P1_004  RX FIFO threshold-1 / threshold 因果边界
UART_P1_005  TX FIFO threshold 可区分的 in-flight / IRQ 因果边界
UART_P1_013  Halt 窗口“不前进” + 同一数据 Resume 完成
UART_P2_005  9-bit mismatch 过滤的有界稳定负对照
```

除这 5 个之外，其余 28 个 Formal Case 不允许因为“这样更严谨”而擅自新增硬件目标；主要动作是 Evidence/Contract/Report Closure。

## 4. Canonical Evidence boundary

当前 UART 源码普遍是：

```text
hardware action / read
-> assert
-> record_result(JSON Artifact)
```

因此 PASS 时可见附件不等于 FAIL 也有完整 Canonical Evidence。本轮统一改为：

```text
hardware action / read
-> record raw Observation / Measurement
-> publish complete Artifact snapshot when needed
-> decisive assert
```

### 4.1 Observation candidates

后续 `uart.md` 使用跨芯片稳定 endpoint，不写 ET6801 地址：

```text
UART_COMPONENT.COMPONENT_PARAMETER
UART_COMPONENT.COMPONENT_VERSION
UART_COMPONENT.PERIPHERAL_ID
UART_COMPONENT.SCRATCH

UART_STATUS.LINE_STATUS
UART_STATUS.FIFO_FLAGS
UART_STATUS.STATE_FLAGS
UART_STATUS.ERROR_FLAGS
UART_FIFO.TX_LEVEL
UART_FIFO.RX_LEVEL

UART_CAPTURE.DATA
UART_9BIT.DATA

UART_MODEM.INPUT_FLAGS
UART_MODEM.DELTA_FLAGS
UART_MODEM.OUTPUT_FLAGS
UART_MODEM.RAW_STATUS

UART_SHADOW.ENABLED
UART_SHADOW.TX_THRESHOLD
UART_SHADOW.RX_THRESHOLD

UART_FIFO_ACCESS.ENABLED
UART_FIFO_ACCESS.TX_VALUE
UART_FIFO_ACCESS.RX_VALUE

UART_BUSY.PRE_TRIGGER_USR
UART_BUSY.OBSERVED_IIR
UART_BUSY.OBSERVED_USR

UART_ISR.PENDING_MASK
UART_ISR.ACTIVE_MASK
UART_ISR.ENABLED_MASK

DMA_CHANNEL_STATUS.FREE
DMA_CHANNEL_STATUS.IRQ_EVENTS
PEER_UART.RX_CAPTURE
DMA_DESTINATION_DATA
```

### 4.2 Measurement / Service facts

下列默认不是 UART 硬件寄存器 Observation：

```text
event_count / event_count_delta
fault_count / fault_count_delta
overflow_count
source_observed Bool
data_match / guards_intact
transferred / received count
round_count / transaction count
requested baudrate / requested threshold
route IDs / request IDs
busy_observed / cleared / recovered Bool
```

它们可作为 Measurement/Service Evidence，但不得伪装成单一 UART register value。

## 5. Public Feature / coverage gaps retained

本轮不会为了让 33 SPEC 看起来“全覆盖”而隐藏以下真实边界：

```text
UART_F_003  普通/别名地址视图
  -> 当前主要是 Capability / Chip Mapping 事实，不由 P0_001 Runtime Capability 查询自动变成动态 alias-access proof。

UART_F_043  Scratch 读写
  -> Snapshot 已提供 scratch 读值，但当前公共 Driver 未发现独立 Scratch write API；P0_001 不得仅凭读值宣称“读写闭合”。

UART_F_014  独立 FIFO reset
  -> P0_002 / P1_016 当前没有独立 RX/TX FIFO reset stimulus；不能靠 software reset 或普通 FIFO config 代替。

UART_F_034  RI / DCD modem input coverage
  -> P2_007 当前只刺激并证明 CTS/DSR；RI/DCD 明确保留未覆盖。

UART_F_045  clock/reset recovery
  -> Hardware Feature 已存在但当前无 Formal Case；继续 NEEDS_VERIFICATION，不借 P0/P2 software reset 冒充 CRG gate/reset coverage。

UART_F_048  absolute baudrate / bit timing
  -> 只由 P3_006 PLAN 覆盖，DUT/Peer 同源通信不能证明绝对 ppm。
```

## 6. Chip Mapping / Report gaps

`ET6801_uart.md` 当前已经有较完整 Hardware/Driver/Board/Feature/Case 分析，但还缺少 AES/CRC/DMA 已统一使用的 Reviewer-facing Stable Endpoint Mapping 表：

```text
| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
```

后续必须把真正可映射的 UART endpoint 映射到 CPR/UCV/CTR/SCR/USR/LSR/TFL/RFL/MSR/MCR/IIR 等 ET6801 实际 Field；Service ISR session、event_count、Peer Capture、DMA state 继续明确标注“不是 UART 寄存器”。

`uart.md` 当前 `ET_CASE_REPORT` 仍大量使用“……验证完成。”式 summary，且没有 UART 专项：

```text
test_uart_contract_consistency.py
test_uart_report_export.py
```

后续必须补：

```text
Registry
-> ET_CASE_SPEC
-> actual test function
-> failure_observations
-> ET_CASE_REPORT

Canonical Result
-> ET6801 UART endpoint mapping
-> Reviewer Remark
-> XLSX
```

两个回归闭环。

## 7. Next implementation order

后续 UART 不按文件从上到下随意修改，固定顺序：

```text
1. Rewrite uart.md Contract / Report
2. Add ET6801 stable endpoint -> register/field mapping
3. Implement 28 RECORD_ONLY Canonical Evidence closure
4. Implement five approved CASE_CHANGE only
5. Add UART Contract/Source/Report consistency regression
6. Add UART Canonical Result -> ET6801 mapping -> XLSX regression
7. Run UART scoped software/firmware/contract/collection gate
8. Write UART Optimization Closure Review
```

如果 CASE_CHANGE 暴露出当前公共 Driver / Firmware / Wire 确实拿不到必要事实，再单独打开 Architecture Correction；不得先猜测性扩 Wire。

## 8. Validation boundary

当前仅完成 Human Review / source audit，本文件创建时没有执行当前精确 SHA 的 UART FPGA/Silicon HIL。

```text
UART Human Review                 FROZEN
UART Contract rewrite             NOT_YET_CLOSED
UART Canonical Evidence closure   NOT_YET_CLOSED
UART Report/XLSX closure          NOT_YET_CLOSED
UART scoped software gate         NOT_YET_EXECUTED
Current-SHA FPGA HIL              NOT_EXECUTED / NOT_VERIFIED
Current-SHA Silicon HIL           NOT_EXECUTED / NOT_VERIFIED
```

历史 UART 测试只用于理解旧测试意图，不替代当前精确 SHA 证据。