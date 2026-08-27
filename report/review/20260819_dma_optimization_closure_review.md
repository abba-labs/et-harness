# DMA Optimization Closure Review — 2026-08-19

> Status: **FINAL SOFTWARE / CONTRACT / EVIDENCE / REPORT CLOSURE**  
> Branch: `review_code`  
> Final integrated source SHA: `3678fc95762b21c0de8f7ac7f42ff1f5779a688e`  
> Current FPGA/Silicon HIL: **NOT_EXECUTED / NOT_VERIFIED**
>
> 本记录只关闭当前已实现 DMA Formal Case 的软件、Contract、Evidence、Chip Mapping 与 Report 软件链；不把历史 HIL、静态 Capability 或 scoped CI 冒充当前精确 SHA 的硬件 PASS。

## 1. 最终结论

DMA 当前已实现 Formal Case 的优化与复审已经完成。

```text
Human Review / Contract                 CLOSED
28 Registered Formal Case               CLOSED at software/evidence layer
Canonical Measurement / Observation     CLOSED
DMA Case behavior changes               CLOSED
ET6801 Chip Mapping                     CLOSED
Contract -> Source -> Report binding    CLOSED
ET6801 mapping -> XLSX E2E              CLOSED
DMA scoped software validation          PASS
Repository-wide Software Quality Gate   NOT GREEN / unrelated baseline debt
Current-SHA FPGA HIL                    NOT_EXECUTED / NOT_VERIFIED
Current-SHA Silicon HIL                 NOT_EXECUTED / NOT_VERIFIED
```

Human Review 初始冻结分类保持为：

```text
RECORD_ONLY             = 20
CASE_CHANGE             = 5
DOC_ONLY                = 2
SEMANTIC / MAPPING GAP  = 1
--------------------------------
Formal Case Total       = 28
```

11 个未实现 Case 继续保持 `ET_CASE_PLAN`，没有为了“DMA CLOSED”被提升为 SPEC。

## 2. 第一轮完成内容

### 2.1 公共 Contract / Human Review

`test_case_doc/dma/dma.md` 已完成稳定跨芯片 DMA Feature/Case/Report Contract 重构：

- 35 个稳定 Feature；
- 28 个注册 Formal SPEC；
- 11 个显式 PLAN；
- Formal Case 使用可人工审核的 Inputs、6～8步真实执行链、最小充分 Observation、精确 Pass Criteria；
- `failure_observations` 与真实 Canonical key 对齐；
- `ET_CASE_REPORT` 只选择决定性字段，不再用“验证完成”代替 Evidence。

语义纠正包括：

- `DMA_P1_016` 不再宣称 TCM 地址转换，只证明 Resource SRAM M2M + TRANSFER_DONE；
- TCM/Core 真实证明保留在 `DMA_P2_014` PLAN；
- `DMA_P2_012` 只证明 Hardware/Software Handshake Mode，Handshake Polarity 保持独立 Open Gap；
- `DMA_P2_015` 作为现有 DMA Feature 经 CRG 扰动后的恢复测试，不制造新的 Reset Feature；
- `DMA_P3_007` 作为已有 Feature 的20轮稳定性组合测试，不制造新的 Stability Feature。

### 2.2 Formal Case / Evidence

28 个已注册 Case 已按 Human Review 结论完成 Evidence Closure；其中五个真实 CASE_CHANGE 已实现：

```text
DMA_P0_002
  Controller/Channel 两轮生命周期
  -> Free/FIFO Empty
  -> Disable/Re-enable
  -> 第二组不同 Payload
  -> 再次可分配

DMA_P1_010
  FIFO Mode Configure
  -> 硬件配置读回
  -> M2M数据
  -> Channel Free

DMA_P1_015
  Burst/Block Configure
  -> Source Burst / Destination Burst / Block Size硬件读回
  -> M2M数据
  -> Channel Free

DMA_P2_011
  Software Handshake
  -> 无Request不前进
  -> 逐Item Request
  -> Source Address逐项推进
  -> Peer Capture / Free

DMA_P2_012
  Hardware/Software Mode对照
  -> Software Mode无Request负对照
  -> 逐Item Request进度
  -> TRANSFER_DONE / Peer Capture / Free
```

关键 Case 已把决定性 Evidence 移到决定性 Assert 之前；P3_007 逐轮保存 Evidence，不再让中途 FAIL 丢失全部前序现场。

## 3. Final Correction Pass

在第一轮 Closure 后再次按 R100/R110/R130 做深度复审，发现并关闭了四类不能留到 UART 阶段的问题。

### 3.1 公共 PC Model 不再解释 ET6801 寄存器位布局

复审发现 `DmaChannelSnapshot` 曾通过位移/掩码直接解释 `control_low/control_high/config_high` 中的 Burst、Block、FIFO 字段。虽然 Case 的“配置读回”目标正确，但这种实现把目标芯片寄存器布局泄漏到公共 PC Model。

最终修正后的链路：

```text
ET6801 Chip Driver Test Extension
  -> 从真实 CTL/CFG Field 解码稳定语义
  -> sourceBurst / destinationBurst / blockSize / fifoMode

Common DMA Wrap
  -> 只复制稳定语义

DMA Firmware Service
  -> Channel Snapshot Response 36 Byte -> 52 Byte
  -> 原9个诊断Word + 4个归一化稳定字段

PC DMA Codec
  -> <13I> Wire解码

PC DmaChannelSnapshot
  -> typed source_burst / destination_burst / block_size / fifo_mode
  -> 不再解释ET6801 bit position
```

这样保留了 `P1_010/P1_015` 的真实硬件读回证明，同时恢复公共 Driver/Model 的芯片中立边界。

新增：

`pc/et_test_platform/framework_validation/unit/firmware_contract/test_dma_snapshot_wire_contract.py`

用于静态保护 Chip Driver -> Wrap -> Service -> PC Codec 的字段顺序、Response Size 和公共 Model 不解析寄存器位布局。

### 3.2 P0_002 Evidence provenance 修正

修正前曾把 `second_actual == expected` 的派生 Bool 作为 `DMA_DESTINATION_DATA` DUT Observation。

最终结构：

```text
second_actual_data
  = Observation / DMA_DESTINATION_DATA / raw actual bytes

second_data_match
  = Measurement / software comparison

final_fifo_empty
  = Observation / DMA_CHANNEL_STATUS.FIFO_EMPTY
```

没有增加硬件刺激，只纠正 Canonical Evidence 身份。

### 3.3 P2_015 原子 Observation 修正

修正前 `recovery_data_state` 把 Expected digest、Actual digest、data_match、channel_free 等多个独立事实放进一个对象，并挂到一个 DMA data endpoint。

最终拆分为：

```text
baseline_actual_data / recovery_actual_data
  -> DUT Observation / DMA_DESTINATION_DATA

baseline_channel_free / recovery_channel_free
  -> DUT Observation / DMA_CHANNEL_STATUS.FREE

baseline_data_match / recovery_data_match
  -> Measurement

clock_reset_sequence
  -> Measurement
```

满足一条 Observation = 一个真实来源端点 + 一个原始值。

### 3.4 DMA Chip Mapping / Report E2E 修正

DMA 的 endpoint 映射内容本身完整，但映射表曾使用自定义英文表头，导致现有 AES/CRC 已验证的 Report Resolver 无法加载。

最终统一为现有固定映射表 Contract：

```text
| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
```

新增：

`pc/et_test_platform/framework_validation/unit/results/test_dma_report_export.py`

模拟真实 Canonical Result，验证：

```text
DMA Canonical Result
-> ET_CASE_REPORT
-> ET6801 endpoint/register mapping
-> Reviewer Remark
-> XLSX
```

并检查 `FIFO_MODE / BLOCK_TS / SRC_MSIZE / DEST_MSIZE` 的 ET6801 实际寄存器/Field 名进入最终 Reviewer-facing 报告。

## 4. ET6801 Adaptation 最终同步

五个 CASE_CHANGE 已从 `IMPLEMENTATION_GAP` 调整为 `ADAPTED`：

```text
DMA_P0_002
DMA_P1_010
DMA_P1_015
DMA_P2_011
DMA_P2_012
```

当前 Case Adaptation 汇总：

```text
ADAPTED            = 27
IMPLEMENTATION_GAP = 8
MAPPING_GAP        = 2
NEEDS_VERIFICATION = 2
Total              = 39
```

这里 39 = 28 Formal SPEC + 11 PLAN。`ADAPTED` 仍然只表示执行链已适配，不代表当前精确 SHA HIL PASS。

Feature Platform 汇总继续保持：

```text
ADAPTED             = 22
PARTIAL_ADAPTATION  = 5
IMPLEMENTATION_GAP  = 8
Total               = 35
```

## 5. 最终 Scoped Software Validation

Final Correction 临时验证分支：

`dma-final-correction-20260819`

Validated correction payload commit：

`98949bc6d01721a0dd7e2cf9d9b8584990ca20a3`

Final diagnostic workflow：

`Software Quality Gate / dma-final-correction-diagnostic / run 32264453855`

结果：**SUCCESS**。

通过的 DMA 责任域检查包括：

- Python compile / Ruff format / Ruff lint；
- Firmware C format / strict quality；
- Firmware architecture rules；
- public code chip-neutral change rules；
- DMA scoped public/chip contract validation；
- `dma.md` Formal Case document validation；
- DMA scoped Formal Case implementation binding；
- DMA Case orchestration；
- DMA Snapshot Model/Wire regression；
- DMA Contract -> Source -> Report consistency regression；
- DMA atomic Evidence regression；
- DMA Canonical Result -> ET6801 mapping -> XLSX E2E regression；
- Firmware Contract suite（仅排除两条与本 DMA 变更无关、依赖缺失 generated Keil metadata 的既有基线测试）；
- DMA Formal Case collection；
- `git diff --check`。

DMA Formal Case 当前 collection：

```text
P0 = 2 executions
P1 = 61 executions
P2 = 22 executions
P3 = 1 execution
-------------------
Total = 86 executions
Stable Formal Case IDs = 28
```

最终通过审核的真实 payload 已选择性落入 `review_code`：

`3678fc95762b21c0de8f7ac7f42ff1f5779a688e`

临时 worker、临时 workflow、临时 PR-local `pc-quality.yml` 均未落入 `review_code`。

## 6. Repository-wide Gate 边界

Repository-wide `Software Quality Gate` 仍不是绿色，这不是 DMA Final Correction 引入的失败。

当前已确认的 baseline debt 包括：

- AES / 通用 Report / Tool 的既有 Ruff-format debt；
- `firmware/build/et6801/ET6801_Automated_Test.generation.json` 在 clean CI 环境缺失导致的 generated Keil metadata tests；
- 其他已知非 DMA 公共基线问题。

因此最终状态必须区分：

```text
DMA scoped software closure     PASS
Repository-wide Software Gate   NOT GREEN / unrelated baseline debt
review_code exact-SHA CI        NOT_VERIFIED as repository-wide PASS
FPGA HIL                        NOT_EXECUTED / NOT_VERIFIED
Silicon HIL                     NOT_EXECUTED / NOT_VERIFIED
```

Scoped PASS 不冒充 repository-wide PASS；软件 PASS 不冒充 HIL PASS。

## 7. 有意保留的真实 Open Work

这些不是本轮 Closure 遗漏，而是当前硬件/Bench/设计条件尚未允许合法实现的下一阶段工作。

### 7.1 11 个 PLAN

```text
DMA_P1_002  Priority arbitration observer
DMA_P1_003  Suspend/Resume deterministic in-flight window
DMA_P2_003  Safe invalid LLI fault window
DMA_P2_007  Safe non-fatal bus-fault window
DMA_P2_014  CORE1 + safe TCM window + CPU/DMA alias mapping
DMA_P3_001  Source/Destination AHB Master selection
DMA_P3_002  Protection / permission model
DMA_P3_003  Max AMBA Burst
DMA_P3_004  Peripheral Flow Controller
DMA_P3_005  Low-Power Timeout
DMA_P3_006  DFT/Test Slave authorization
```

它们继续保持 `ET_CASE_PLAN`，不得在没有相应设计/Bench/HIL条件时伪造成已实现覆盖。

### 7.2 Formal SPEC 显式保留的 Feature / Mapping Gap

```text
fifo_depth_dynamic_proof_gap
  = F033 精确 FIFO Physical Depth 尚无独立动态 Oracle

handshake_polarity_proof_gap
  = F027 缺可控 active-high / active-low Request Source

public_feature_identity_gap
  = P2_013 NORMAL/ACC Alias 行为已存在，但跨芯片公共 Feature Admission 尚未冻结
```

### 7.3 HIL

2026-08-02 / 2026-08-03 的历史 DMA FPGA Result 继续只作为 Historical Evidence。

当前 Final Closure Source SHA 没有真实 FPGA/Silicon 执行，因此：

```text
Current-SHA FPGA HIL   NOT_EXECUTED / NOT_VERIFIED
Current-SHA Silicon HIL NOT_EXECUTED / NOT_VERIFIED
```

## 8. 最终审核结论

在“不伪造当前 HIL、11 个 PLAN 不冒充 SPEC、三个真实 Feature/Mapping Gap 继续公开保留”的前提下：

> **DMA 当前已实现的 28 个 Formal Case 已完成 Contract / Source / Canonical Evidence / ET6801 Chip Mapping / ET_CASE_REPORT / XLSX 软件闭环，并通过 DMA scoped Final Correction 审核。**

因此 DMA 可以从 Wave 1 当前实施队列中标记为 **CLOSED at software/contract/evidence/report layer**；下一固定目标可以进入 UART Human Review。
