# AES Evidence Closure Review

> Status: Review Draft
>
> Scope: AES Formal Case implementation readiness against R140/R210 hardware-observation and Evidence-lifecycle rules.
>
> Supersedes: `report/plans/20260818_aes_minimum_hardware_proofset_review.md`。旧文件仅保留为历史审查记录；后续 AES Evidence Closure 以本文件和当前 `aes.md` 为准。
>
> This file is a review/planning record, not an active rule and not a HIL PASS/FAIL result. It does not change Driver/Firmware/Wire/Capability semantics.

## 1. Review standard

For each Formal Case, review the chain:

```text
Feature / Pass Criteria
-> minimum sufficient hardware observation
-> current Case actually obtains the fact
-> decisive fact survives to final Canonical Result / bound Artifact
-> ET_CASE_REPORT can consume the fact
```

Three implementation-readiness states are used:

- `CLOSED`：现有测试动作与最终已发布 Evidence 已足以支撑当前 Feature；只需按新规则把 `aes.md` 的 Observation 描述写准确，不需要新增硬件动作或重构 Snapshot 生命周期。
- `RECORD_ONLY`：测试动作已经取得并断言决定性事实，但当前记录存在同一路径重复 Snapshot、关键字段未保留或未进入 Canonical Observation/Measurement；只允许优化 Evidence 记录，不新增硬件交互。
- `CASE_CHANGE`：当前测试动作本身缺少足以隔离并证明 Feature 的决定性观测；需要先按已审核 Contract 做最小测试行为调整，再完成 Evidence 记录。

## 2. Case classification

| Case | Status | Current assessment |
|---|---|---|
| AES_P0_001 | CLOSED | 静态 Capability 门禁 Case；本身不声称运行时 AES 硬件功能 PASS，不要求伪造寄存器 Observation。 |
| AES_P0_002 | RECORD_ONLY | Actual/NIST Expected/produced_bytes 已保存，FINISH 已读取并断言但未进入最终 Evidence。 |
| AES_P0_003 | RECORD_ONLY | 两轮运算行为已执行；同一 Artifact 在轮次中重复发布，需改为单次最终 Snapshot 或 Canonical 关键事实记录。 |
| AES_P1_001 | CLOSED | 每个参数 execution 单次发布 Mode/Padding/Expected/Actual/produced_bytes；当前最小证明链可保留。 |
| AES_P1_002 | RECORD_ONLY | IV Readback 与 Actual 已取得，但同一 execution 内多次覆盖同一路径，且每个 IV 对应 Golden 关系未完整保留。 |
| AES_P1_003 | RECORD_ONLY | DATA_LENGTH Readback、BUSY/FINISH、Actual 均已真实取得；后一次 Snapshot 会丢失前面的 data_length_readback。 |
| AES_P1_004 | CLOSED | 每个 endian execution 独立单次发布配置、Expected/Actual 和 produced_bytes；不需要额外寄存器读取。 |
| AES_P1_005 | CLOSED | Counter 参数、Expected/Actual、produced_bytes、FINISH 已在单个 execution 的最终 Snapshot 中保留。 |
| AES_P1_006 | RECORD_ONLY | STATUS.DIN_REQ 的写入前/写入后/复核值已取得；当前多次发布同一路径，应改为一次最终 Snapshot/Canonical Observation。现有 BLOCK_WRITE 路径已包含请求消费/清除，不额外增加硬件动作。 |
| AES_P1_007 | RECORD_ONLY | STATUS.DOUT_REQ 的读取前/读取后/复核值及 Actual 已取得；当前多次发布同一路径，应改为一次最终 Snapshot/Canonical Observation。 |
| AES_P1_008 | RECORD_ONLY | STATUS.FINISH 的 1→0 与 Actual 已取得；同一路径分两次发布，需改为一次最终闭合记录。 |
| AES_P1_009 | RECORD_ONLY | OUTPUT_CONFLICT 的 ISR latched/event_count 与清除后 RAW 已取得；当前同一路径重复发布，需要最终 Snapshot/Canonical Observation 单调闭合。 |
| AES_P1_010 | RECORD_ONLY | KEY_MISSING snapshot/clear 行为已取得；event_count 被断言但未保留在最终 Snapshot，且存在重复发布。 |
| AES_P1_011 | RECORD_ONLY | IV_MISSING snapshot/clear 行为已取得；event_count 被断言但未保留在最终 Snapshot，且存在重复发布。 |
| AES_P1_012 | RECORD_ONLY | COMPLETE IRQ、Actual、produced_bytes、clear 状态已取得；当前重复发布，需要保留 Expected/Actual/IRQ 关系并单次发布。 |
| AES_P1_013 | RECORD_ONLY | INCOMPLETE_DISABLE 与恢复 KAT 已真实执行；当前重复发布，恢复 Golden/Actual 关系需最终保留。 |
| AES_P1_014 | RECORD_ONLY | IRQ Transfer 的 IDLE→COMPLETE、input/output offset 和 Actual 已足以证明会话推进；当前循环/终态多次覆盖同一路径，需改为 Canonical 关键事实 + 单次最终 Snapshot。 |
| AES_P1_015 | RECORD_ONLY | Force→ISR latched→Clear 的决定性事实已取得；当前同一路径前后两次发布，应合并为最终 Snapshot。 |
| AES_P1_016 | RECORD_ONLY | Mask 时 RAW=1/STATUS=0 与 Unmask 后 ISR latched 已取得；当前同一路径两次发布，应合并记录。 |
| AES_P1_017 | RECORD_ONLY | Clear 前 RAW=目标 bit、Clear 后 RAW=0 的硬件状态变化已取得；当前前后 Snapshot 重复发布，应合并记录。 |
| AES_P2_001 | CASE_CHANGE | 单次立即读取 Channel Active 无法充分隔离“Gate 阻塞”与“DMA 尚未自然完成”；需在 Gate 关闭状态增加最小有界观测窗口，证明两 Channel 在窗口内保持未完成/无错误，再开启 Gate 完成。 |
| AES_P2_002 | CLOSED | REGISTER 端点双向 DMA 完成状态与 Destination Actual/Golden 已单次发布；无需新增硬件动作。 |
| AES_P2_003 | CLOSED | FIFO 固定端点两阶段 DMA 完成状态与 Destination Actual/Golden 已单次发布；无需新增硬件动作。 |
| AES_P3_001 | RECORD_ONLY | 8 轮功能与 FINISH 均逐轮断言，但循环内反复覆盖同一 Snapshot，且每轮 Golden 关系未最终保留。 |
| AES_P3_002 | RECORD_ONLY | DWT/目标周期、measured_bytes、FINISH、Actual 均已取得；循环和最终汇总重复覆盖同一路径，最终 Snapshot 丢失功能结果与状态。 |
| AES_P3_003 | RECORD_ONLY | DMA timing、Channel Free 和 Actual 已取得；Expected/data_match 未进入最终 Evidence，需要补记录但不新增硬件交互。 |

Summary:

```text
CLOSED      = 6
RECORD_ONLY = 19
CASE_CHANGE = 1
Total       = 26
```

## 3. Implementation boundary

- `CLOSED`：后续只同步 `aes.md` Observation/Report 表达；不得为了“证据更多”新增寄存器访问。
- `RECORD_ONLY`：只调整 `record_property` / `record_observation` / 最终 Artifact 组装与发布方式；禁止改变 Driver 调用顺序、刺激、等待条件和硬件动作。
- `CASE_CHANGE`：只有 `AES_P2_001` 当前需要行为级最小增强；修改前后的 Feature、Step、Observation、Pass Criteria 必须保持同一因果目标，禁止顺手扩展 DMA/AES 覆盖范围。
- 在每个 Case 完成 Evidence Closure 前保留 `case_measurement_gap`；只有最终 Canonical Result 与 ET_CASE_REPORT 均能解析决定性事实后，才允许逐 Case 去除 gap。
