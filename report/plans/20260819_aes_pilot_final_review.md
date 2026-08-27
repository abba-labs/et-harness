# AES Pilot Final Review

> Status: SOURCE / DESIGN REVIEW PASS
>
> Software / simulation execution: NOT_EXECUTED in the current connector-only environment
>
> Hardware re-run: UNAVAILABLE and not required for template/design review
>
> Scope: `test_case_doc/aes/aes.md`、`test_case_doc/aes/ET6801_aes.md`、现有 `test_aes_p0.py`～`test_aes_p3.py`、Canonical Evidence 与现有 Case Report/Excel 链路。
>
> Boundary: 本 Review 不修改 AES Driver/Firmware/Wire/Capability 架构，不新增/拆分 AES Formal Case，不拆分公共 `aes.md`。历史 HIL 结果保持原样。

## 1. Pilot 目标

AES 作为后续 IP 推广样板，最终形成：

```text
公共 aes.md
-> 现有 Formal Case
-> 稳定 Hardware Observation endpoint
-> Canonical Result / 单次最终 Artifact
-> chip_id 选择 ET6801_aes.md 实际寄存器映射
-> ET_CASE_REPORT
-> Excel 人工审核
```

Reviewer 应能只使用 `aes.md + Excel` 回答：测什么、输入/配置是什么、步骤是什么、从哪个硬件端点观察什么、Expected/Oracle 来自哪里、为什么 PASS/FAIL。

## 2. 最终设计结论

### 2.1 公共 Contract

- `aes.md` 保持单文件，不拆分。
- 34 个 Feature、26 个 Formal Case 已收敛到现有 P0～P3 实现。
- `method.inputs / steps / observations / pass_criteria` 使用稳定跨芯片语义。
- 公共 Observation 使用 `STATUS.FINISH`、`RESULT_DOUT[0..3]`、`IRQ_STATUS.<Source>` 等稳定 endpoint，不写物理地址。
- Golden、produced_bytes、参数、event_count 等软件/协议/Service 事实与真实 DUT Observation 分开记录。
- 26 个 Case 当前均为 `gap: []`；该状态的源码闭合由本 Review 逐项审核，机器 Gate 仍需在可执行环境复核。

### 2.2 ET6801 实际寄存器映射

`ET6801_aes.md` 的 2.1 表作为当前 AES 芯片实际名称映射源，例如：

```text
STATUS.FINISH       -> RPT_AES_STS.FINISH
STATUS.BUSY         -> RPT_AES_WORK.BUSY
STATUS.DIN_REQ      -> RPT_AES_STS.DIN_FLG
STATUS.DOUT_REQ     -> RPT_AES_STS.DOUT_FLG
RESULT_DOUT[0..3]   -> RESULT_DOUT0~RESULT_DOUT3
IV[0..3]            -> WORK_IV0~WORK_IV3
DATA_LENGTH[1:0]    -> DATA_SIZE0.SIZE0 + DATA_SIZE1.SIZE1
IRQ_RAW.<Source>    -> RPT_AES_INT_RAW.<Source bit>
IRQ_STATUS.<Source> -> RPT_AES_INT_STATUS.<Source bit>
```

### 2.3 Report chip resolver

现有 `case_report.py` 已实现最小解析：

```text
session/result chip_id = ET6801
-> 读取当前 aes.md 同目录 ET6801_aes.md
-> 解析稳定语义映射表
-> 根据真实 Observation.endpoint 取得 ET6801 寄存器/Field 名
-> ET_CASE_REPORT / Excel Remark 显示实际芯片名称
```

Canonical Result 仍保存稳定 endpoint；没有对应芯片映射时保留稳定语义，不猜测实际寄存器名。

### 2.4 模拟 Report / Excel Regression

已增加两层纯软件 Regression 源码：

```text
test_case_report.py
-> 验证 stable endpoint -> ET6801 寄存器名

test_aes_report_export.py
-> 构造模拟 Canonical session/result
-> build_case_report_model
-> ET_CASE_REPORT
-> 现有 generate_case_report._write_xlsx
-> 检查 XLSX XML 中存在 ET6801 实际寄存器名
```

覆盖代表映射：

```text
STATUS.FINISH -> RPT_AES_STS.FINISH
RESULT_DOUT[0..3] -> RESULT_DOUT0~RESULT_DOUT3
IRQ_STATUS.COMPLETE -> RPT_AES_INT_STATUS.COMPLETE
```

这些 Regression 只验证模板/报告链，不能形成或更新 HIL PASS。

## 3. 26 个 AES Case 源码 / Evidence 审核

### P0

- `P0_001`：静态 semantic mapping + 只读 `CAPABILITIES_GET`；不执行 Enable/Configure/Process，不冒充 AES 运算 PASS。
- `P0_002`：Expected、RESULT_DOUT Actual、STATUS.FINISH 在决定性 Assert 前进入 Canonical Result；单次最终 Artifact。
- `P0_003`：两轮 Expected/Actual/produced/FINISH 单调累计，最终只发布一次 Snapshot。

### P1

- Padding/IV/Data-Length/Endian/Counter Case 已分别保留 RESULT_DOUT、IV/Data-Length Readback、BUSY/FINISH 等真实来源。
- `P1_006/P1_007` 只把 DIN/DOUT 请求 `1->0` 解释为 blocking I/O 消费/清除；显式 Clear 后的 `0->0` 只作为无残留复核。
- `P1_008` 已完成原子 Evidence 修复：`RESULT_DOUT[0..3]` 与 `STATUS.FINISH` 分开记录；Clear 前/后 FINISH 分开记录；公共 `failure_observations` 和 `ET_CASE_REPORT` 已同步。
- `P1_009`～`P1_017` 的 IRQ RAW、STATUS、Service latch、event_count、Clear 后状态按真实来源拆分；event_count/delta 保持 Measurement，不冒充寄存器。
- `P1_014` 保留 IRQ Transfer 初态、STATE/Offset 推进、终态和 RESULT_DOUT；循环中没有同一路径增量 Snapshot。

### P2

- `P2_001` 是本轮唯一行为级增强：Gate 关闭时连续 8 次有界读取 DMA Channel 状态，确认两 Channel 全程 Not-Free 且无 Error；随后只打开 Gate，观察原 Channel 完成并校验 Destination 与 Golden。
- `P2_002/P2_003` 保持原 DMA REGISTER/FIFO 行为，只收敛 Evidence，没有新增无关硬件读取。

### P3

- `P3_001/P3_002` 在循环内使用 Canonical Measurement/Observation 保存决定性事实，最终 Artifact 只发布一次。
- `P3_003` 同时保留 timing、DMA Channel 终态和 FIFO Actual，不以周期值代替功能结果验证。

## 4. Failure Observation / Case Binding 审核

逐项核对 26 个 `failure_observations` 与现有 `test_*` 实现后，当前关键 key 均存在对应 `record_property()` 或 `record_observation()`；硬件事实使用 Observation，软件/Oracle 事实使用 Measurement。

重点闭合项：

```text
P0_002 expected_output / actual_output / finish_status
P1_003 expected_value / actual_value
P1_008 expected_output / actual_output / actual_state / finish_after_clear
P1_012 expected_irq / actual_irq / actual_irq_status
P1_015 expected_irq / actual_irq / actual_irq_status
P1_016 expected_irq / masked_raw / actual_irq_status
P2_001 gate_closed_input_active / gate_closed_output_active / gate_closed_no_error
P3_002 timed_expected_output / timed_actual_output / timed_elapsed_cycles
P3_003 expected_output / actual_output / timing_complete
```

同时核查 `record_result()` 生命周期：AES 当前循环型 Case 使用内存累计 + finally 单次发布，其他 Case 每 execution 只有一个最终 Snapshot publish site；未发现依赖“重复写同一路径自动合并”的 AES Case。

## 5. Review Issues Closure

### REVIEW-001 — RESOLVED

旧问题：`P1_008` 把 FINISH 与 RESULT_DOUT 合并为一个 `actual_state`，来源语义错误。

当前：

```text
expected_output      -> Measurement / PC Golden
actual_output        -> Observation / RESULT_DOUT[0..3]
actual_state         -> Observation / STATUS.FINISH / before clear
finish_after_clear   -> Observation / STATUS.FINISH / after clear
```

公共 SPEC、Case 实现、ET_CASE_REPORT 已一致。

### REVIEW-002 — EXECUTION NOT VERIFIED

当前环境无法执行仓库本地命令，因此以下 Gate 仍标记 `NOT_EXECUTED`：

```text
python tools/quality/validate_case_docs.py test_case_doc/aes/aes.md
python tools/quality/check_case_spec_implementation.py
python tools/quality/check_case_orchestration_rules.py
python -m pytest --collect-only -q pc/et_test_platform/test_cases/aes
pytest pc/et_test_platform/framework_validation/unit/results/test_case_report.py
pytest pc/et_test_platform/framework_validation/unit/results/test_aes_report_export.py
python tools/validate_pc.py
```

GitHub 当前提交没有可用的 PR workflow run，因此不能用 CI 代替本地验证。

### REVIEW-003 — REGRESSION SOURCE CLOSED / EXECUTION NOT VERIFIED

模拟 `Canonical Result -> chip mapping -> ET_CASE_REPORT -> XLSX` Regression 已写入现有 framework validation；源码链路闭合，执行状态仍为 `NOT_EXECUTED`。

## 6. 历史 HIL 边界

历史 ET6801 FPGA：

```text
59 executions
56 PASS
3 FAIL
```

历史 FAIL：

```text
AES_P1_009
AES_P2_003
AES_P3_003
```

本轮 Evidence/Report 优化不得改变这些历史硬件结果。`AES_P2_001` 新的 8-sample 实现未来有硬件时需要重新执行；当前无真机只审核其设计与证据链。

## 7. Final Review Gate 结果

| Gate | 结论 |
|---|---|
| Feature / Case 公共语义 | PASS（源码/文档审核） |
| 26 Case Contract ↔ 实现 | PASS（源码逐项审核） |
| 最小充分 Hardware Observation | PASS（源码/文档审核） |
| Measurement / Observation 来源边界 | PASS（源码审核） |
| Artifact Snapshot 生命周期 | PASS（源码审核） |
| ET6801 稳定语义 ↔ 实际寄存器映射 | PASS（源码/文档审核） |
| ET_CASE_REPORT 原子字段 | PASS（源码/文档审核） |
| 模拟 Excel Regression 源码 | PASS（源码审核） |
| 本地 pytest / checker / export 实际执行 | NOT_EXECUTED |
| 当前 SHA FPGA/Silicon HIL | NOT_EXECUTED |

## 8. Final Conclusion

```text
AES PILOT SOURCE/DESIGN REVIEW: PASS
Architecture change: NO
New AES Formal Case: NO
Split public aes.md: NO
Driver/Firmware/Wire/Capability architecture change: NO
Register-name resolver: IMPLEMENTED
Atomic Evidence provenance: IMPLEMENTED
Synthetic Excel regression source: IMPLEMENTED
Software/Simulation execution: NOT_VERIFIED
Current-SHA HIL: NOT_VERIFIED
Historical HIL: unchanged
```

AES 现在可以作为**源码/Contract/Evidence/Report 设计样板**进入规则反馈阶段；它不能被描述为“当前精确 SHA 已通过全部软件 Gate 或 59/59 HIL”。

下一阶段只允许把本次 AES Pilot 已经实际暴露并解决的问题反馈到现有 Rule Owner：优先扩展现有 R120/R130/R210，不新建平行规则；已经由 R100/R140 明确覆盖的内容不重复写第二套规则。