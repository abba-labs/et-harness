# AES Pilot -> Rule Feedback Closure

> Status: APPLIED
>
> Input: `report/plans/20260819_aes_pilot_final_review.md`
>
> Boundary: 只把 AES Pilot 已经真实暴露并修复的问题反馈到现有 Rule Owner；不新增 Rule ID，不建立平行 Schema，不复制 R100/R140 已有规则。

## 1. 为什么只修改 R120 / R130 / R210

AES Pilot 最终审核后，R100 与 R140 已经明确覆盖：

- 公共稳定语义与芯片事实分层；
- `<CHIP>_<ip>.md` 保存公共 Observation -> 实际寄存器/Field 映射；
- 公共 Case 不写芯片地址；
- 人工报告允许展示解析后的实际寄存器/Field 名称；
- Feature 只收集最小充分 Hardware Observation。

因此不再给 R100/R140 增加重复规则。

本次实际暴露的规则缺口只有三类：

```text
1. ET_CASE_REPORT 如何避免把多个硬件来源合并成一个报告字段
2. Canonical Observation 如何保证 source/endpoint/value 原子来源正确
3. Formal Case 如何正确使用 record_observation，并区分 IRQ寄存器、Service latch、event_count
```

分别由 R120 / R130 / R210 负责。

## 2. R120 — Public Report Contract

已补充：

- `source: observation` 的一个报告字段必须对应一个原子 Canonical Observation key；
- 一个结论需要 RESULT_DOUT、FINISH、IRQ 等多个独立端点时，使用多个报告字段，不允许先把多个来源拼成一个值再挂到单一寄存器标签；
- 公共 `path/label` 继续芯片中立；
- 报告可根据 `chip_id + <CHIP>_<ip>.md` 把稳定 endpoint 展示为目标芯片实际寄存器/Field 名；
- 该展示不得修改 Canonical `endpoint/source/value`，映射缺失不得猜测。

这直接对应 AES `P1_008` 曾经暴露的“FINISH + RESULT_DOUT 被合并成一个现场”的问题，以及 ET6801 实际寄存器名进入 Excel 的需求。

## 3. R130 — Canonical Observation Provenance

已补充：

```text
one Observation
= one source + one device_id + one endpoint + one raw value
```

并明确：

- 多寄存器/Field/ISR端点必须拆成多条 Observation；
- `IRQ_RAW/IRQ_STATUS`、Service `latched`、`event_count` 是不同事实；
- event_count / delta / 协议计数默认是 Measurement，除非有明确硬件端点直接提供；
- Canonical 保存公共稳定 endpoint；目标芯片实际寄存器名只是报告层只读展示增强；
- 报告不得修改 Canonical key/value/source/endpoint。

## 4. R210 — Formal Case Implementation

已补充：

- `record_observation()` 一条只绑定一个真实硬件/设备端点；
- `RESULT_DOUT`、`STATUS.FINISH`、`IRQ_RAW/STATUS`、ISR latch 等必须按来源分别记录；
- IRQ 寄存器与 Service evidence 不得互相冒充；
- event_count/delta 默认使用 `record_property()`；
- 修正原规则最小示例，使其与真实 API 一致：

```python
record_observation(
    record_property,
    key="finish",
    value=status.finish,
    source="dut",
    endpoint="STATUS.FINISH",
)
```

## 5. 与实现/Regression 的对应关系

本次规则不是空中设计，已有 AES Pilot 实现作为前置事实：

```text
R120 原子报告字段
<-> AES_P1_008 ET_CASE_REPORT 已拆分 Golden / RESULT_DOUT / FINISH before / FINISH after

R130 原子 Observation
<-> AES P1 IRQ/状态 Evidence 已按 endpoint/source 拆分

R130/R120 chip display boundary
<-> case_report.py chip-id register-name resolver

Report Regression
<-> test_case_report.py
<-> test_aes_report_export.py（模拟 Canonical Result -> ET6801寄存器名 -> XLSX）

R210 API示例
<-> scheduling/run_context.py 实际 record_observation(record_property, *, ...)
```

## 6. Validation Boundary

当前 connector-only 环境未执行仓库本地命令，以下状态保持 `NOT_EXECUTED`：

```text
validate_case_docs
check_case_spec_implementation
check_case_orchestration_rules
pytest collect-only AES
case_report unit tests
AES simulated XLSX regression
validate_pc
```

GitHub 当前也没有可用 PR workflow run。规则修改因此只能声明“Rule text 已与当前 AES Pilot 实现/Regression 源码对齐”，不能声明机器 Gate 已通过。

## 7. Final Conclusion

```text
AES source/design review: PASS
Rule feedback: APPLIED
New rule file: NO
New rule ID: NO
Parallel schema: NO
R100 duplicated: NO
R140 duplicated: NO
R120 optimized: YES
R130 optimized: YES
R210 optimized: YES
Machine validation: NOT_EXECUTED
Historical HIL: unchanged
```

后续其他 IP 应先按更新后的现有规则复用 AES 模式；如果在第二个 IP 上再次暴露新的、可复现的规则缺口，再回到对应 Rule Owner 做最小扩展。