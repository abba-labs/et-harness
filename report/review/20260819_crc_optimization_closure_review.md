# CRC Optimization Closure Review

> 状态：**CRC SOFTWARE / CONTRACT / EVIDENCE / REPORT CLOSURE**  
> 日期：2026-08-19  
> 分支：`review_code`  
> 推广计划：`report/plans/20260819_ip_optimization_rollout_plan.md`  
> AES Pilot 基线后的第二个硬件 IP：CRC

---

## 1. Closure 结论

CRC 已完成本轮计划要求的 **Human Review / Evidence Closure / Report Closure / 软件级验收**。

本轮闭合的是：

```text
公共 CRC Stable Contract
-> 24 个 Formal Case
-> Canonical Measurement / Observation
-> ET6801 Chip Register / Field Mapping
-> 单次最终 Structured Artifact
-> ET_CASE_REPORT
-> Excel Human Review
```

当前没有 FPGA / Silicon 真机环境，因此本结论 **不代表 CRC 硬件已经在当前精确 SHA 上 PASS**。

最终状态：

| 项目 | 状态 | 说明 |
|---|---|---|
| CRC Feature / Stable Contract | CLOSED | 24 个稳定 Case Contract 已完成审核与机器校验 |
| CRC Formal Case Source Design | CLOSED | P0/P1/P2/P3 已完成 Evidence 驱动优化 |
| Canonical Evidence | CLOSED | 决定性硬件事实已按来源拆分并进入 Observation |
| ET6801 Chip Mapping | CLOSED | 稳定 endpoint 与 ET6801 实际寄存器 / Field 已建立映射 |
| ET_CASE_REPORT / Excel 软件链 | CLOSED | 模拟 Canonical Result 已验证到 XLSX 导出 |
| CRC Contract ↔ Source ↔ Report 一致性 | CLOSED | CRC 专用 AST Gate 已加入并通过 |
| `CRC_F_012 FIFO Physical Depth` | OPEN GAP | 保留 `dynamic_fifo_depth_proof_gap`，不以 Threshold / Overflow 冒充闭环 |
| FPGA HIL @ validated source SHA | NOT_EXECUTED / NOT_VERIFIED | 当前无真机 |
| Silicon HIL @ validated source SHA | NOT_EXECUTED / NOT_VERIFIED | 当前无真机 |

---

## 2. 验证基线

### 2.1 CRC 优化起点

```text
baseline SHA:
ff55d7e537ea60a33c1022f7cff5f1b470f4658e

message:
docs(plan): define IP optimization rollout after AES pilot
```

### 2.2 本轮已验证 Source / Contract SHA

```text
validated source SHA:
96f87f642b87de7d193299b966665feb91260e0a

message:
test(crc): align report regression labels
```

本文件是 **验证完成后的 docs-only Closure Record**，因此后续 `review_code` HEAD 会比上述 validated source SHA 新；CRC 软件验收结论绑定的是上述精确 Source / Contract SHA，不用 Closure 文档提交本身替代验证 SHA。

---

## 3. 第一阶段 Human Review 冻结结论

用户人工确认后的第一阶段分类为：

| 分类 | 数量 | 说明 |
|---|---:|---|
| DOC_ONLY | 1 | `CRC_P0_001` 初始主要缺 Contract / Evidence 表达 |
| RECORD_ONLY | 20 | 硬件动作基本充分，主要缺 Canonical Evidence / Report Closure |
| CASE_CHANGE | 3 | `CRC_P1_007` / `CRC_P1_013` / `CRC_P1_018` |
| Case GAP | 0 | 无新增缺失 Formal Case |
| Feature Semantic GAP | 1 | `CRC_F_012 FIFO Physical Depth` |

后续实现未重新扩大 Feature Scope；只按冻结结论做最小充分修正。

---

## 4. 三个最小 CASE_CHANGE

### 4.1 CRC_P1_007 —— Arbitrary Byte Length + LENGTH Programming / Readback

旧实现能证明 remainder Byte 计算，但不能独立证明 LENGTH 编程 / 读回。

本轮补强：

```text
Byte Length
-> DATA_LENGTH_SET
-> LENGTH.REMAINING_INPUT_COUNT hardware readback
-> compare Expected Input Transaction Count
-> CALCULATE
-> RESULT.CRC == PC Golden
-> Remaining == 0
```

因此 `CRC_F_009` 与 `CRC_F_010` 不再混成同一个弱结论。

### 4.2 CRC_P1_013 —— IRQ Enable / Disable + Force + Delivery

旧实现只有：

```text
Enable -> Force -> Delivery
```

本轮补成因果闭环：

```text
Enable + Unmask
-> Force
-> Event Count +1 / ISR latch
-> Clear
-> Disable same Source
-> Force again
-> disabled_event_count_delta == 0
```

Disable 阶段 `IRQ_RAW.<Source>` 仍保留为 supplemental hardware context；决定性 Disable PASS / FAIL 字段是 `disabled_event_count_delta=0`。

### 4.3 CRC_P1_018 —— BUS_ERROR 因果证明

本轮保留 ET6801 历史刺激，但加入合法对照：

```text
CRC8 + LENGTH=1
-> legal 8-bit IR write
-> BUS_ERROR Raw/Status/Event delta == 0
-> reset stage
-> illegal 32-bit IR write
-> BUS_ERROR delivery == 1
-> lifecycle recovery
-> normal CRC8 RESULT.CRC == PC Golden
```

因此不再只证明“发生过 BUS_ERROR”，而是证明目标错误与非法访问宽度之间的因果关系。

---

## 5. Canonical Evidence Closure

本轮统一后的稳定 Observation endpoint 包括：

```text
RESULT.CRC
LENGTH.REMAINING_INPUT_COUNT
FIFO.OVERFLOW

IRQ_RAW.<Source>
IRQ_STATUS.<Source>
ISR.LATCHED.<Source>
ISR.LAST_RAW.<Source>

TIMING.CYCLE_COUNT
DMA_TIMING.COMPLETE
DMA_CHANNEL_STATUS.FREE

CRC_CAPABILITIES.MODES
CRC_CAPABILITIES.IRQ_EVENTS
CRC_CAPABILITIES.MAX_CALCULATE_BYTES
```

Evidence 身份规则：

- PC Golden / Expected / 配置参数：Measurement / Oracle；
- `RESULT`、`LENGTH`、FIFO、IRQ Raw / Status：DUT hardware Observation；
- Service `event_count`：Service evidence，不冒充寄存器；
- ISR latch / last_raw：真实 ISR 保存的 delivery evidence，与当前硬件 pending 状态分开；
- DMA Channel / Timing：对应 DMA hardware / target-local timing 事实，不冒充 CRC register；
- Runtime Capability：目标侧只读 DUT capability snapshot，不冒充单个寄存器。

P3 长稳 / 性能 Case 已改为：决定性事实先记录；最终结构化 Artifact 只发布一次，并尽量在中途 FAIL 时保留已经形成的轮次 / 周期 Snapshot。

---

## 6. ET6801 Chip Mapping Closure

公共 Case 保持芯片中立；ET6801 实际寄存器 / Field 由 `test_case_doc/crc/ET6801_crc.md` 解析。

核心映射包括：

```text
RESULT.CRC
-> RES.POST_CRC_CAL

LENGTH.REMAINING_INPUT_COUNT
-> LENGTH.CRC_LENGTH

FIFO.OVERFLOW
-> FIFO_OVF.CRC_FIFO_OVF_RPT

IRQ_RAW.<Source>
-> INT_RAW_RPT.<actual source field>

IRQ_STATUS.<Source>
-> INT_STATUS_RPT.<actual source field>
```

Service ISR、DMA 状态、DWT Timing 和 Runtime Capability 明确标为非 CRC 寄存器来源，避免 Reviewer 把软件 latch 或跨 IP 事实误认为 CRC 寄存器现场。

---

## 7. CRC_F_012 保留真实 Gap

`CRC_F_012 FIFO Physical Depth` 当前状态：

```text
Hardware feature: SUPPORTED
Platform adaptation: PARTIAL_ADAPTATION
Dynamic exact-depth proof: GAP
```

当前已有：

- FIFO 存在的静态硬件证据；
- FIFO Threshold 上限事实；
- Threshold 行为 Case；
- Overflow + Recovery Case。

当前没有：

- 独立、精确、安全的“物理深度恰好为 N”的动态 Oracle。

因此：

- `CRC_P1_011` 只证明 Threshold；
- `CRC_P1_012` 只证明 Overflow / Recovery；
- 不把两者组合包装成 FIFO Physical Depth PASS。

---

## 8. Contract ↔ Source ↔ Report 自动一致性 Gate

新增：

```text
pc/et_test_platform/framework_validation/unit/results/
    test_crc_contract_consistency.py
```

该 Gate 使用 AST 自动检查：

```text
24 ET_CASE_SPEC IDs
== CRC_CASE_REGISTRY 24 stable IDs
== CRC source test functions

failure_observations key
-> 对应 Formal Case 必须真实产生

ET_CASE_REPORT measurement / observation / artifact field
-> 对应 Formal Case 必须真实产生
```

目的不是补一项形式检查，而是避免以后出现：

```text
crc.md 写了字段
但 Case 没记录
或 Case 改了 key
但 Report 仍消费旧 key
```

这种静默 Contract 漂移。

---

## 9. Report / Excel 无真机回归

新增：

```text
pc/et_test_platform/framework_validation/unit/results/
    test_crc_report_export.py
```

该测试不访问硬件，只构造 synthetic Canonical Result，验证：

```text
Canonical Result
-> stable CRC endpoint
-> ET6801_crc.md actual register / Field mapping
-> ET_CASE_REPORT
-> human-readable Remark
-> XLSX export
```

当前覆盖至少包括：

```text
LENGTH.REMAINING_INPUT_COUNT
-> LENGTH.CRC_LENGTH

RESULT.CRC
-> RES.POST_CRC_CAL

IRQ_RAW.BUS_ERROR
-> ET6801 actual Raw field

IRQ_STATUS.BUS_ERROR
-> ET6801 actual Status field
```

**Synthetic Result PASS 只证明报告软件链正确，不能升级任何 CRC Hardware Feature 为 PASS。**

---

## 10. 最终 CRC-scoped Software Closure Gate

为避免当前仓库其他 IP / 全局基线债务遮蔽 CRC 自身结果，本轮使用临时 non-merge CRC Closure PR 运行同一仓库规则的 CRC Scope。

临时 PR：

```text
PR #24
ci(crc): closure gate after report regression sync
```

该 PR 已在验收完成后关闭，未合并。

CRC Closure workflow：

```text
run_id: 32236142671
job_id: 96016427996
job conclusion: success
```

以下 CRC Closure 项全部 PASS：

1. CRC Python syntax；
2. CRC Ruff format；
3. CRC Ruff lint；
4. CRC diff whitespace；
5. Rule governance；
6. Task context navigation schema `validate`；
7. CRC IP contract synchronization；
8. CRC public stable contract；
9. Chip adaptation contract；
10. CRC Formal Case specification contract；
11. CRC Formal Case implementation binding；
12. CRC Formal Case orchestration；
13. CRC PC AST architecture rules；
14. CRC PC documentation semantics；
15. CRC contract-source consistency；
16. CRC report / XLSX regression；
17. CRC Formal Case collection。

Collection 结果：

```text
test_crc_p0.py: 5 executions
test_crc_p1.py: 34 executions
test_crc_p2.py: 3 executions
test_crc_p3.py: 3 executions

Total parameterized pytest executions: 45
Stable Case IDs: 24
```

45 是参数化执行实例数，不是新增 45 个稳定 Case；稳定 Registry 仍严格保持 24 个 Case ID。

---

## 11. Full PC Unit Diagnostic 与 CRC Closure 的边界

同一临时 CRC workflow 额外运行了完整：

```text
python -m pytest pc/et_test_platform/framework_validation/unit
```

该步骤设置为 diagnostic / `continue-on-error`，实际结果：

```text
684 passed
3 skipped
4 failed
```

4 个失败均不是 CRC Closure 自身失败：

1. `test_generated_keil_project_matches_generation_record`
   - 缺 `firmware/build/et6801/ET6801_Automated_Test.generation.json`；
2. `test_generated_keil_project_uses_only_firmware_source_files`
   - 同一 generated metadata 未生成；
3. AES simulated report regression
   - AES synthetic YAML 中未引用的 `RESULT_DOUT[0..3]` label 导致 YAML ParserError；
4. 通用 case_report 的 AES mapping synthetic test
   - 同一类未引用 `RESULT_DOUT[0..3]` synthetic YAML ParserError。

因此本轮结论是：

```text
CRC-scoped unit / contract / report tests: PASS
Full PC unit suite: NOT GREEN because of unrelated existing infrastructure/AES diagnostic failures
```

不得把 full-unit diagnostic 的 4 个非 CRC 失败改写成 CRC FAIL，也不得为了 CRC Closure 越权修改 AES / Firmware build metadata。

---

## 12. Repository-wide Software Quality Gate 状态

同一临时 PR 自动触发仓库级：

```text
Software Quality Gate
run_id: 32236142661
job_id: 96016428108
conclusion: failure
```

该 Gate 在统一 `validate_pc.py` 的 Ruff format 阶段被 6 个当前基线的非 CRC / 全局文件阻塞：

```text
pc/et_test_platform/framework_validation/unit/results/test_case_report.py
pc/et_test_platform/results/case_report.py
pc/et_test_platform/test_cases/aes/test_aes_p1.py
pc/et_test_platform/test_cases/aes/test_aes_p2.py
pc/et_test_platform/test_cases/aes/test_aes_p3.py
tools/quality/check_case_spec_implementation.py
```

这些文件不属于本轮 CRC 修改 Scope。

所以仓库级状态必须写成：

```text
Repository-wide Software Quality Gate:
BLOCKED_BY_UNRELATED_BASELINE_DEBT
```

而不是：

```text
CRC software validation failed
```

后续若统一清理上述基线债务，再重新跑 repository-wide gate 即可；CRC Closure 不应为此跨 IP 扩大修改范围。

---

## 13. HIL 验收边界

当前没有真机，因此：

```text
FPGA HIL @ 96f87f642b87de7d193299b966665feb91260e0a
= NOT_EXECUTED / NOT_VERIFIED

Silicon HIL @ 96f87f642b87de7d193299b966665feb91260e0a
= NOT_EXECUTED / NOT_VERIFIED
```

未来有 FPGA / Silicon 后，需要针对当时精确 Source SHA 重新执行 CRC HIL。

未来 HIL 至少应重点关注：

- `CRC_P1_007` LENGTH 编程 / 读回新增因果证明；
- `CRC_P1_013` Disable 后 Force 的 Delivery 反证；
- `CRC_P1_018` legal 8-bit baseline → illegal 32-bit BUS_ERROR 因果链；
- IRQ ISR latch 与当前 Raw/Status 的真实时序；
- FIFO Threshold / Overflow 行为；
- DMA P2 路径；
- P3 target-local timing。

旧 SHA 的历史 HIL 不能自动替代上述当前 Source SHA 的新行为验证。

---

## 14. 最终 Closure 判定

本轮 CRC 可以从推广计划中的：

```text
CRC Human Review / Evidence Closure
```

升级为：

```text
CRC SOFTWARE / CONTRACT / EVIDENCE / REPORT CLOSED
HIL PENDING
ONE HONEST FEATURE GAP RETAINED: CRC_F_012
```

CRC 已证明 AES Pilot 的方法可以推广到第二个真实硬件 IP：

- 不要求重写全部 Case；
- 先判断 DOC / RECORD / CASE CHANGE / GAP；
- 只增强最小充分硬件因果证据；
- 将 Hardware Observation 与 Service / Oracle 分开；
- Stable Contract 与 Chip Mapping 分离；
- PASS / FAIL 共用同一 Evidence Contract；
- Report / Excel 成为 Reviewer 可直接审核的输出，而不是 pytest PASS 的装饰层。

**CRC 本轮收尾完成。**

下一个 IP 是否进入 DMA，应继续遵循推广计划的串行原则，由后续任务显式启动；本 Closure 文档本身不自动开启 DMA 修改。
