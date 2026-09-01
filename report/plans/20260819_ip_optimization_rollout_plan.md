# IP 优化推广总计划 —— 以 AES Pilot 为基线

> Status: ACTIVE IMPLEMENTATION PLAN / 非活动规则
>
> Baseline branch: `review_code`
>
> Baseline HEAD before this plan: `9b057c0645de0e7be271e6ea68779873aceca46b`
>
> Rollout progress (2026-08-20): `AES/CRC/DMA/UART historical closure recorded -> Human Review rule baseline upgraded @ 3245f43943c518982640b2e0da2184cb8cd942e5 -> repository-wide Contract revalidation / migration NEXT -> Framework Communication PAUSED`
>
> CRC Closure Record: `report/review/20260819_crc_optimization_closure_review.md`
>
> DMA Closure Record: `report/review/20260819_dma_optimization_closure_review.md`
>
> UART Closure Record: `report/review/20260820_uart_optimization_closure_review.md`
>
> 目的：把 AES Pilot 已经实际走通、并由 CRC 第二个真实硬件 IP 再次验证的“公共 Contract → Formal Case → Canonical Evidence → Chip Register Mapping → ET_CASE_REPORT → Excel 人工审核”流程固化为后续 IP 的统一实施顺序。
>
> 本文件是实施导航和审核清单，不是第二套 Rxxx 规则。任何冲突均按 `AGENTS.md > active Rxxx > ip.md > current source` 处理；本文件不得覆盖、改写或替代活动规则。

---

## 1. 本计划解决什么问题

后续 IP 不再采用“先随意读代码、看到哪里改哪里、最后再补文档”的方式优化，而固定采用下面的设计顺序：

```text
读取当前活动规则和目标IP真实现状
-> 先把公共 ip.md 梳理成可人工审核的稳定 Contract
-> 人工审核 ip.md
-> 对照已审核 Contract 检查真实 Case 代码
-> 只修真正的实现 / Evidence Gap
-> 生成 Canonical Result / ET_CASE_REPORT / Excel
-> 人工审核最终报告
-> 软件 Gate / CI / HIL 按实际执行状态单独闭环
```

本计划只推广已经由 AES Pilot 和 CRC 第二轮实践证明有必要的做法，不预设所有 IP 都有 AES/CRC 同样的问题，也不允许为了“统一风格”对所有 IP 机械复制 AES/CRC 的寄存器、Case、Evidence 或报告结构。

---

## 2. 权威来源与必须遵循的规则

### 2.1 权威顺序

后续任何 IP 优化都按仓库当前权威顺序判断：

```text
AGENTS.md
> report/design/rules/Rxxx_*.md
> report/design/rule_owner_catalog.yaml（机器索引，不是第二份规则正文）
> test_case_doc/<ip>/<ip>.md
> test_case_doc/<ip>/<CHIP>_<ip>.md
> 当前源码 / Case / Driver / Firmware / Test
> report/plans / report/review / report/archive
```

本 Plan 处于最后一层，只负责执行导航和历史总结。

### 2.2 每个 IP 优化默认必读规则

| 规则 | 本流程中负责的内容 |
|---|---|
| `AGENTS.md` | 仓库宪法、固定架构、可靠性优先级、验证和 Git/CI 完成条件 |
| `R001_agent_rule_governance.md` | Rule Owner、规则生命周期、禁止形成第二套规则正文 |
| `R002_task_context_navigation.md` | 每个新任务 / 扩围任务先编译 Task Context，确认 read/write scope |
| `R100_public_ip_semantics_and_chip_adaptation.md` | 公共稳定语义和芯片事实边界；公共代码芯片中立 |
| `R110_contract_document_sync.md` | `ip.md`、Case、Registry、Evidence、Report 必须双向一致 |
| `R120_public_ip_machine_contract.md` | `ET_CASE_SPEC / PLAN / REPORT` Schema、统一 Human Review 行语法、6～8 Step 机器结构红线和绑定关系 |
| `R130_canonical_result_evidence.md` | Measurement / Observation / Artifact 来源、生命周期、报告只读派生 |
| `R140_ip_analysis_workflow.md` | Feature/Case 分析、人审语义质量、最小充分硬件 Observation、Oracle、完成 Gate |
| `R210_pc_case_responsibility.md` | Formal Case 线性流程、真实硬件顺序、Evidence Closure、决定性断言前记录 |
| `R220_python_style_quality.md` | Python 结构、注释、类型、复杂度和 Ruff 质量要求 |

### 2.3 按变更范围条件必读规则

只有 Task Context 路由到对应责任时才读取和修改，不允许每个 IP 无差别扩围：

| 条件 | 规则 |
|---|---|
| 需要修改 PC Driver | `R200_pc_layer_responsibilities.md` |
| 需要修改 Firmware Service | `R300_firmware_service.md` |
| 需要修改 Firmware Wrap / Chip Config | `R310_firmware_wrap.md` |
| 涉及真实 IRQ 交付 / Service latch | `R320_firmware_irq.md` |
| 修改 Firmware C 源码 | `R330_firmware_c_style.md` |
| 修改 Wire / ET-Frame | `R400_et_frame_v1.md` |
| 修改 Capability / SVD 机器事实 | `R410_capability_v2.md` |
| 修改 Runner / Result / Report / Artifact | `R500_operator_pipeline.md` + R130 |

原则：**先由 R002 Task Context 路由，再读规则；不得凭历史记忆自行扩围。**

---

## 3. AES Pilot 优化全过程总结

### 3.1 AES Pilot 的目标

AES 不是为了重写测试框架，而是作为第一个“人可以直接审核”的完整样板：

```text
公共 aes.md
-> 26 个已注册 Formal Case
-> 稳定 Hardware Observation endpoint
-> Canonical Measurement / Observation
-> 单次最终 Artifact Snapshot
-> ET6801_aes.md 稳定 endpoint 到实际寄存器/Field映射
-> ET_CASE_REPORT
-> Excel 人工审核
```

Reviewer 的目标是只看 `aes.md + Excel` 就能回答：

1. 测什么 Feature；
2. 输入 / 配置是什么；
3. 真实执行步骤是什么；
4. 从哪个硬件寄存器 / Field / 端点观察什么；
5. Expected / Golden 从哪里来；
6. 为什么是 PASS / FAIL。

### 3.2 AES 初始发现的问题分类

AES 26 个 Formal Case 的初始 Evidence Review 分类为：

```text
CLOSED      = 6
RECORD_ONLY = 19
CASE_CHANGE = 1
Total       = 26
```

含义：

- `CLOSED`：现有硬件动作和 Evidence 已足够，只需同步人审 Contract / Report 表达。
- `RECORD_ONLY`：代码已经真实取得并断言决定性事实，但 Evidence 保存方式不满足最终报告闭合；只能补记录，不能增加硬件动作。
- `CASE_CHANGE`：现有动作本身不能充分证明 Feature；只有这种情况才允许最小增强测试行为。

### 3.3 AES 具体发现的问题

#### AES-ISSUE-001：公共 `aes.md` 人审信息过于抽象

问题：

- `report_feature`、`inputs`、`steps`、`pass_criteria` 过于概括；
- Reviewer 无法只靠文档复原测试逻辑；
- `observations` 没有统一写清具体硬件端点、期望现象和证明含义。

优化：

- 34 个 Feature、26 个 Formal Case 重新按稳定语义梳理；
- `inputs` 用 1～3 条说明参数矩阵 / 测试数据 / Golden 来源；
- `steps` 固定按真实顺序写 6～8 条；
- `observations` 只写最小充分硬件证明，具体到 `STATUS.FINISH`、`RESULT_DOUT[0..3]`、`IRQ_STATUS.<Source>`、`DMA_CHANNEL_STATUS.*` 等稳定 endpoint；
- `pass_criteria` 改成可以直接核对的条件，不再写“符合预期 / 状态正常”。

#### AES-ISSUE-002：同一路径 Artifact 被当成增量日志

问题：

旧 Case 多处在同一 execution 中多次向同一个 JSON 路径写阶段结果，默认以为后写字段会自动合并。

但 R130 明确：

```text
write_json_result()
= 完整 Snapshot
= 同一路径再次写入会替换旧 Snapshot
!= merge / append
```

因此早期 `data_length_readback`、IRQ before/after、每轮 Expected/Actual 等决定性事实可能被后续 Snapshot 覆盖。

优化：

- 小而决定 PASS/FAIL 的事实进入 Canonical Measurement / Observation；
- 循环型 Case 在内存中累计完整结构；
- 每个 execution 最终只发布一次完整 Artifact Snapshot；
- 真正需要多个阶段现场时才使用不同语义路径，不允许重复写同一路径模拟追加。

#### AES-ISSUE-003：读取并 Assert 了硬件事实，但没有进入 Canonical Evidence

典型：

- `AES_P0_002` 已读取 `FINISH`，但旧 Evidence 没保留；
- 多个 IRQ Case 已检查 event_count / clear / recovery，但最终报告无法解析全部关键事实；
- P3 性能 Case 取得 Actual / FINISH / cycles，但旧最终附件未完整保留。

优化：

```text
原来：
read hardware
assert hardware == expected

改为：
read hardware
record_property / record_observation
assert hardware == expected
```

关键 Evidence 必须在决定性断言前记录，避免 FAIL 时现场消失。

#### AES-ISSUE-004：Measurement 与真实 Hardware Observation 来源混淆

问题：

下列事实一度容易被写成“硬件 Observation”：

- PC Golden；
- `produced_bytes`；
- parameter_id；
- event_count / delta；
- 软件比较结果。

这些默认不是硬件寄存器值。

优化：

- PC Golden / 配置 / 软件计数使用 `record_property()`；
- 真实寄存器 / Field / DUT endpoint 使用 `record_observation()`；
- Canonical Observation 保持：

```text
one Observation
= one source + one device_id + one endpoint + one raw value
```

#### AES-ISSUE-005：多个独立硬件来源被合并成一个 Observation / 报告字段

最典型问题出现在 `AES_P1_008`：旧表达把 `RESULT_DOUT` 与 `FINISH` 混到一个“actual_state/现场”概念里，来源语义不真实。

优化后：

```text
expected_output      -> Measurement / PC Golden
actual_output        -> Observation / RESULT_DOUT[0..3]
actual_state         -> Observation / STATUS.FINISH / before clear
finish_after_clear   -> Observation / STATUS.FINISH / after clear
```

报告层也分别展示，不允许一个字段挂一个寄存器标签却包含多个实际来源。

#### AES-ISSUE-006：IRQ 寄存器事实、ISR/Service latch、event_count 混用

问题：

```text
IRQ_RAW.<Source>
IRQ_STATUS.<Source>
ISR.LATCHED.<Source>
event_count
```

是四类不同来源事实，不能互相代替。

优化：

- RAW / STATUS 保持真实寄存器 Observation；
- Service ISR latch 保持独立端点；
- event_count / delta 默认作为 Measurement；
- 报告需要多个端点时使用多个原子字段。

#### AES-ISSUE-007：Feature 声明强度超过实际 Observation 强度

代表问题：

- `P1_006 / P1_007` 的 DIN_REQ / DOUT_REQ：真实 1→0 来自 blocking I/O 稳定路径消费请求；随后显式 Clear 的 0→0 只能证明无残留，不能声称独立证明 W1C 1→0。
- `P1_003` 只在 PROCESS 完成后观察 `STATUS.BUSY=0`，不能写成已证明运行期间 BUSY 先拉高再拉低。

优化：

**文档结论强度降到现有硬件证据真实能证明的范围，不为“描述完整”虚构状态变化。**

#### AES-ISSUE-008：`AES_P2_001` Gate 因果证明不足

这是 AES 26 个 Case 中唯一确认需要真实行为级增强的 Case。

旧逻辑：

```text
关闭 AES DMA Request Gate
-> 启动 DMA
-> 立即采样一次 Channel Active
```

单次瞬时 Active 不能区分：

```text
A. Gate 真正阻塞请求
B. DMA 只是刚启动，尚未来得及自然完成
```

优化：

```text
Gate 关闭
-> 启动原输入/输出 DMA Channel
-> 连续 8 次有界读取 Channel 状态
-> 确认两 Channel 在整个窗口持续 Not-Free 且 No Error
-> 只打开 Gate，不重启 Channel
-> 等待原 Channel 完成
-> 校验 Destination Actual == 独立 Golden
```

该增强保持原 Feature 因果目标，没有顺手增加新的 DMA/AES 覆盖。

#### AES-ISSUE-009：公共稳定 endpoint 与目标芯片实际寄存器名称之间缺少 Reviewer 友好的展示

公共 Contract 必须芯片中立，但最终人工报告希望看到 ET6801 实际寄存器/Field。

优化：

- Canonical Observation 保存稳定 endpoint；
- `ET6801_aes.md` 维护映射，例如：

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

- Report 根据本次 `chip_id` 只读解析显示实际寄存器名；
- 映射缺失时保留稳定 endpoint，不猜实际名称。

#### AES-ISSUE-010：历史 HIL 与当前代码状态容易被误写成同一个结论

历史 ET6801 FPGA 记录：

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

本轮 Evidence / Report 优化没有重新执行当前精确 SHA HIL，因此历史结果保持历史结果，不允许自动改写成当前 PASS。

### 3.4 AES Pilot 最终完成的优化

当前 AES 已完成以下**源码 / Contract / Evidence / Report 设计闭合**：

- 34 个 Feature、26 个 Formal Case 公共语义重新人审；
- 26 个 Case 当前 `gap: []`；
- P0/P1/P2/P3 关键 Expected / Actual / Status / IRQ / DMA 证据进入 Canonical Result；
- 循环型 Case 不再依赖同一路径增量 Snapshot；
- `P2_001` 完成 8-sample Gate-closed 因果增强；
- 公共 `aes.md` 与 `ET6801_aes.md` 完成稳定 endpoint / 实际寄存器映射；
- `ET_CASE_REPORT` 使用 1～4 个决定性字段；
- Report 增加 chip register-name resolver；
- 增加模拟 `Canonical Result -> chip mapping -> ET_CASE_REPORT -> XLSX` Regression 源码；
- AES Pilot 暴露的通用问题已反馈到现有 `R120 / R130 / R210`，没有新增 Rule ID 或平行 Schema。

当前结论必须精确写为：

```text
AES SOURCE / DESIGN REVIEW: PASS
Software checker / pytest execution on current environment: NOT_EXECUTED / NOT_VERIFIED
Current-SHA FPGA/Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
Historical HIL: unchanged
```

不得把 SOURCE/DESIGN PASS 写成“当前精确 SHA 已全软件 Gate PASS”或“59/59 HIL PASS”。

---

## 4. AES Pilot 实际修改的文件

以下列表以 AES Evidence Closure / Final Review / Rule Feedback 为边界。

### 4.1 AES 公共 / 芯片 Contract

```text
test_case_doc/aes/aes.md
test_case_doc/aes/ET6801_aes.md
```

主要变化：

- Feature / Case / 6～8 步 / Observation / Pass Criteria 人审收口；
- `failure_observations` 与真实 Canonical key 同步；
- `ET_CASE_REPORT` 原子字段同步；
- `case_measurement_gap` 逐项解除并最终全部 `gap: []`；
- ET6801 实际寄存器 / Field 映射建立。

### 4.2 AES Formal Case

```text
pc/et_test_platform/test_cases/aes/test_aes_p0.py
pc/et_test_platform/test_cases/aes/test_aes_p1.py
pc/et_test_platform/test_cases/aes/test_aes_p2.py
pc/et_test_platform/test_cases/aes/test_aes_p3.py
```

主要变化：

- 把已取得的 Expected / Actual / Status / IRQ / DMA 事实记录为 Canonical Measurement / Observation；
- 决定性断言前保留关键 Evidence；
- 循环型 Case 内存累计，最终单次 Snapshot；
- `AES_P2_001` 做唯一行为级最小增强；
- 不改变 Driver/Firmware/Wire/Capability 架构。

### 4.3 公共 Report 层

```text
pc/et_test_platform/results/case_report.py
pc/et_test_platform/framework_validation/unit/results/test_case_report.py
pc/et_test_platform/framework_validation/unit/results/test_aes_report_export.py
```

主要变化：

- `chip_id + <CHIP>_<ip>.md` 稳定 endpoint 映射到实际寄存器/Field 展示；
- 保持 Canonical source / endpoint / raw value 不变；
- 增加 AES 模拟 Excel Regression 源码。

### 4.4 活动规则反馈

```text
report/design/rules/R120_public_ip_machine_contract.md
report/design/rules/R130_canonical_result_evidence.md
report/design/rules/R210_pc_case_responsibility.md
```

只补 AES Pilot 实际证明缺失的通用规则：

- R120：Report Observation 字段原子化、芯片寄存器显示边界；
- R130：原子 Observation provenance，IRQ register / Service latch / event_count 来源分离；
- R210：`record_observation()` 一端点一事实，关键 Evidence 生命周期闭合。

没有新增新的 Rule 文件或 Rule ID。

### 4.5 AES Review / Plan 记录

```text
report/plans/20260819_aes_evidence_closure_review.md
report/plans/20260819_aes_evidence_implementation_status.md
report/plans/20260819_aes_pilot_final_review.md
report/plans/20260819_aes_rule_feedback.md
```

它们用于记录审查过程和状态，不是活动规则。

---

## 5. 当前 IP / Formal Domain 现状分类

这里必须区分“代码存在”“优化完成”“只有 PLAN”三个概念，不能统称“已完成”。

本计划中“代码存在”专指：

```text
pc/et_test_platform/test_cases/<ip>/
+ case_registry.py
+ 平台 ip_registry.py 已注册
+ 公共 <ip>.md 存在 ET_CASE_SPEC
```

不是指“仓库里某处存在 SDK Driver / Service / Wrap”。

### 5.1 A 类：Formal Case 代码 + 公共 ip.md 都存在

#### 1. AES —— Pilot 已完成优化

```text
Formal SPEC: 26
当前优化状态: SOURCE / DESIGN REVIEW PASS
当前-SHA软件执行: NOT_VERIFIED
当前-SHA HIL: NOT_VERIFIED
```

AES 是后续流程样板，不再作为下一轮普通 IP 重做。

#### 2. CRC —— Wave 1 首个推广 IP，已完成

```text
Formal SPEC: 24
公共 crc.md: 存在并已完成 Human Review
ET6801_crc.md: 存在并已完成稳定 endpoint -> 实际寄存器/Field 映射审核
Formal Case代码: 存在并注册
当前优化状态: SOFTWARE / CONTRACT / EVIDENCE / REPORT CLOSURE
validated source SHA: 96f87f642b87de7d193299b966665feb91260e0a
Closure Record: report/review/20260819_crc_optimization_closure_review.md
Current-SHA FPGA/Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
```

CRC 已完成 AES Pilot 后第一个真实硬件 IP 的推广闭环。24 个稳定 Case 的 Contract / Source / Canonical Evidence / Chip Mapping / ET_CASE_REPORT / Excel 软件链已经完成；`CRC_F_012 FIFO Physical Depth` 仍保留 `dynamic_fifo_depth_proof_gap`，不把 Threshold / Overflow 证据包装成精确物理深度证明。

#### 3. DMA —— Wave 1 第二个推广 IP，已完成

```text
Formal SPEC: 28
额外 PLAN: 11
公共 dma.md: 已完成 Human Review / Stable Contract
ET6801_dma.md: 已完成稳定 endpoint -> 实际寄存器/Field 映射与适配状态同步
Formal Case代码: 28个已注册并完成当前实现层 Evidence Closure
当前优化状态: SOFTWARE / CONTRACT / EVIDENCE / REPORT CLOSURE
validated source SHA: 3678fc95762b21c0de8f7ac7f42ff1f5779a688e
Closure Record: report/review/20260819_dma_optimization_closure_review.md
Current-SHA FPGA/Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
```

DMA 已完成当前28个已实现 Formal Case 的 Human Review、最小行为增强、Canonical Evidence、ET6801 Chip Mapping、ET_CASE_REPORT 与 XLSX 软件闭环。11个未实现Case继续保持 PLAN；FIFO精确动态深度、Handshake Polarity 与 NORMAL/ACC公共Feature身份等显式Gap继续保留，不冒充硬件覆盖。

#### 4. UART —— Wave 1 第三个推广 IP，已完成

```text
Formal SPEC: 33
额外 PLAN: 7
公共 uart.md: 已完成 Human Review / Stable Contract
ET6801_uart.md: 已完成 stable endpoint -> Register/Field 映射审核
Formal Case代码: 33个已注册并完成当前实现层 Evidence Closure
当前优化状态: SOFTWARE / CONTRACT / EVIDENCE / CHIP MAPPING / REPORT SCOPED CLOSURE
clean official source SHA: 377a79574aefdf5179a39f3fad64855c1dae2bb7
Closure Record: report/review/20260820_uart_optimization_closure_review.md
Current-SHA FPGA/Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
```

UART 已完成当前33个已实现 Formal Case 的 Human Review、28个 RECORD_ONLY Evidence Closure、5个最小 CASE_CHANGE、ET6801 Chip Mapping、ET_CASE_REPORT 与 XLSX 软件闭环。7个未实现Case继续保持 PLAN；Scratch写、精确FIFO物理深度、RI/DCD刺激、独立FIFO reset、CRG恢复、绝对baud/bit timing等显式Gap继续保留，不冒充硬件覆盖。

#### 5. Framework Communication —— 非硬件 IP，作为已实现 Formal Domain 单独处理

```text
Formal SPEC: 1
公共 framework_communication.md: 存在
Formal Case代码: 存在并注册
```

它验证公共通信链路，不是硬件 IP。为保持本轮“先硬件 IP，再平台测试域”的顺序，放在 CRC / DMA / UART 之后做同类 Human Review / Report Closure。

### 5.2 B 类：公共 ip.md + Chip 文档存在，但没有 Formal Case 代码

这些 IP 当前都只能保持 `ET_CASE_PLAN`，不得直接写成 SPEC。

#### STIMER

```text
PLAN: 14
公共 stimer.md: 存在
ET6801_stimer.md: 存在
Formal Case package / registry: 不存在
```

#### CORDIC

```text
PLAN: 28
公共 cordic.md: 存在
ET6801_cordic.md: 存在
Formal Case package / registry: 不存在
```

#### WDG

```text
PLAN: 14
公共 wdg.md: 存在
ET6801_wdg.md: 存在
Formal Case package / registry: 不存在
```

#### FMAC

```text
PLAN: 28
公共 fmac.md: 存在
ET6801_fmac.md: 存在
Formal Case package / registry: 不存在
```

FMAC 当前还存在独立模型 / 量化 / IIR / DMA 等显式设计 Gap，必须最后处理，禁止为了赶进度扩大容差或把未知算法语义直接写成 SPEC。

### 5.3 C 类：支撑 Contract 存在，但当前不属于 Formal Case 优化队列

#### CRG

```text
公共 crg.md: 存在
Formal Case Catalog / ET_CASE_PLAN / ET_CASE_SPEC: 当前没有
Formal Case package / registry: 不存在
```

CRG 当前是其他 IP 的稳定公共动作 / Service 支撑 Contract，不应为了“每个目录都一样”强行补 Case。

如果未来决定 CRG 本身需要独立 Formal Test Domain：

```text
先重新执行 ip-package/analysis
-> R140 审核 Feature / Case Admission
-> 形成合法 ET_CASE_PLAN
-> 人工审核
-> 再进入实现
```

禁止直接复制 AES / DMA Case 结构给 CRG。

---

## 6. 后续固定优化顺序

### Wave 0 —— 已完成 Pilot

```text
AES
```

目标：作为模板，不重复推倒重来。

### Wave 1 —— 先处理“代码 + ip.md 都存在”的硬件 IP

固定顺序不变，当前执行状态更新为：

```text
[COMPLETED UNDER PRE-3245 RULE BASELINE] 1. CRC
[COMPLETED UNDER PRE-3245 RULE BASELINE] 2. DMA
[COMPLETED UNDER PRE-3245 RULE BASELINE] 3. UART
```

原因与当前结论：

- CRC：已经完成第二个真实硬件 IP 推广验证，证明“先 Human Review Contract、再按 Gap 分类最小改代码、最后做 Evidence/Report Closure”的流程可以从 AES 推广到另一类自包含硬件 IP；
- DMA：已经完成当前28个已实现 Formal Case 的软件/Contract/Evidence/Report闭环；11个 PLAN 与显式Feature/Mapping Gap继续保留，当前精确SHA HIL仍未执行；
- UART：已经完成33个已实现 Formal Case 的 Contract/Evidence/Chip Mapping/Report scoped closure；7个 PLAN 与真实 Feature/Bench Gap继续保留，当前精确SHA FPGA/Silicon HIL仍未执行。

上述 Closure 记录作为**当时规则基线下的历史实施事实**保留；2026-08-20 R120/R140 Human Review 机器契约升级后，其“当前规则一致性”统一进入 `REVALIDATION_REQUIRED / NOT_VERIFIED`，详见第16节。历史 Evidence Closure 不因规则升级被抹去，但也不能自动等价为新规则 Gate PASS。

### Wave 1B —— 已实现但不是硬件 IP 的 Formal Domain

```text
[PAUSED] 4. Framework Communication
```

UART Closed 后原计划进入 Framework Communication。2026-08-20 在其只读 Human Review 中暴露出跨 IP 的 Human Review Contract 规则/机器门禁缺口，因此先暂停 Domain 实现修改，先完成第16节的一次性规则基线验证和公共 Contract 重校验。恢复后它仍然是下一个 Formal Domain。

### Wave 2 —— 再处理“只有 ip.md / PLAN，没有 Formal Case 代码”的 IP

固定顺序：

```text
5. STIMER
6. CORDIC
7. WDG
8. FMAC
```

排序依据：

#### STIMER 优先

- 14 个 PLAN，范围较小；
- 计数 / 周期 / 比较 / IRQ / DMA 的硬件 Observation 边界清晰；
- 适合先验证“PLAN-only IP 按新 R140 重做 Contract，再进入实现”的流程。

#### CORDIC 第二

- 28 个 PLAN，Case 数量较多；
- 核心数学 Feature 可以使用独立 PC Oracle；
- 大部分路径相对自包含，外部 Bench 依赖少；
- 在复杂系统状态 IP 之前处理更利于稳定流程。

#### WDG 第三

- 14 个 PLAN，但涉及真实系统 Reset、跨重启 Session、自然 IRQ、时钟、Debugger Halt；
- 风险和环境依赖显著高于 Case 数量本身；
- 必须等 PLAN-only 工作流稳定后再实现。

#### FMAC 最后

- 28 个 PLAN；
- Q15 / IIR / clip / saturation / offset / shift / float conversion / DMA / streaming / 性能同时存在；
- 当前文档已经明确部分算法量化和 IIR bit-exact 语义需设计证据解除；
- 禁止在这些 Gap 未闭合时提前写 Case 或放宽容差。

### CRG 不插入上述顺序

CRG 作为支撑 Contract，只有被正式 Admission 为独立 Formal Domain 后才进入新队列。

---

## 7. Wave 1：已有 Formal Case IP 的固定优化流程

以下流程适用于 CRC / DMA / UART / Framework Communication；CRC / DMA / UART 已完成历史实施闭环，当前还需按第16节对新 Human Review 行语法和机器 Gate 做 revalidation；Framework Communication 在该迁移完成后继续继承同一 Human Review / Evidence Closure 原则，但按通信域真实 Endpoint 选择证明。

### Step 1：确定真实状态，不直接改代码

必须先确认：

```text
当前 branch / HEAD
公共 <ip>.md
<CHIP>_<ip>.md
case_registry.py
平台 ip_registry.py
真实 test_<ip>_p*.py
当前已有 Result / Report Regression（若有）
```

输出一个只读基线：

```text
SPEC数量
PLAN数量
Formal Case实际注册数量
现有 Gap
历史 HIL 状态
当前精确 SHA 是否执行过软件 / HIL
```

### Step 2：按 R002 编译 `ip-package / case` Task Context

目标：只允许修改当前 IP 的：

```text
pc/et_test_platform/test_cases/<ip>/**
test_case_doc/<ip>/<ip>.md
```

如果后续确认需要修改公共 Report、Driver、Firmware、Wire、Capability：

**先停止当前任务 -> scope-check -> 重新编译对应 Task Context。**

禁止在 Case 任务中直接扩到这些层。

### Step 3：先审公共 `ip.md`，不以代码写法反向主导 Contract

逐 Feature / Case 检查：

#### 3.1 Feature

必须具体说明实际验证能力，不使用：

```text
功能矩阵
语义正确性
生命周期
数据路径
配置能力
```

这类空泛词作为完整 Feature 结论。

#### 3.2 Inputs

通常 1～3 条，必须说明：

- 真实参数组合；
- 测试数据来源；
- 模式 / 长度 / 方向等关键条件；
- Expected / Golden / 规范 Oracle 来源。

所有 `method.inputs[]` 必须满足 R120 唯一公共行语法：

```text
<摘要>：<正文>
```

#### 3.3 Steps

每个 Case 必须按真实执行顺序写 6～8 条，并能覆盖该 Case 实际需要的：

```text
输入准备
-> DUT配置
-> 激励
-> Start / Wait
-> 硬件 Observation
-> Expected / Oracle
-> Compare / Assert
-> 参数化汇总（适用时）
```

不能机械套标题；无 Golden 的 IRQ / 状态 / 配置 Case 写真实规范状态或独立 Observer。所有 `method.steps[]` 同样必须满足 R120 的 `<摘要>：<正文>` 行语法；不能通过拆标题、重复摘要或空动作凑 6～8 条。

#### 3.4 Observations

只保留最小充分硬件证明：

```text
Observation摘要：稳定寄存器/Field/Endpoint + Expected + Proof meaning
```

例：

```text
运算完成状态：读取 STATUS.FINISH，期望=1；证明一次硬件运算进入完成终态。
```

不能只写：

```text
状态
Actual
结果
硬件反馈
```

#### 3.5 Pass Criteria

通常 2～5 条，写精确可核对条件：

```text
具体寄存器状态
具体数据一致条件
具体数量 / 长度
参数化完整执行数量
```

禁止“调用成功 / 结果正确 / 状态正常”。所有 `method.pass_criteria[]` 必须使用同一 `<摘要>：<正文>` 行语法。

#### 3.6 ET_CASE_REPORT

每 Case 只选 1～4 个真正支撑结论的字段。

优先：

- Expected / Golden；
- Actual hardware endpoint；
- 完成 / Error / IRQ / DMA 状态；
- 必要的配置 / count / timing。

完整调试信息留在 Canonical Result / Artifact，不把 Excel 变成 JSON dump。

### Step 4：人工审核 `ip.md`

在进入代码阶段前，Reviewer 必须只看 `<ip>.md` 能回答：

```text
测什么？
输入/配置什么？
6～8步怎样执行？
硬件从哪里看？
Expected是什么？
哪些事实决定PASS？
最终报告展示什么？
```

任何一项需要“等看代码才知道”，Contract 还没写完。

R120 机器 Gate 通过只证明统一行语法和 Steps 数量结构正确；它不能替代本 Step 的 R140 语义 Human Review。

### Step 5：逐 Case 对照代码做 Gap 分类

每个 Case 只能落入下列一种主分类：

#### A. CLOSED

文档与代码一致，关键 Evidence 已闭合。

动作：不改代码。

#### B. DOC_ONLY

测试行为和 Evidence 已正确，只是 `ip.md / ET_CASE_REPORT` 表达不满足新规则。

动作：只改文档。

#### C. RECORD_ONLY

代码已经真实读到 / 计算到决定性事实，也已经用于 Assert，但没有正确保存为 Canonical Measurement / Observation 或最终 Artifact。

允许动作：

```text
补 record_property
补 record_observation
调整内存累计
最终单次 Snapshot
```

不允许新增硬件访问。

#### D. CASE_CHANGE

当前 Case 动作本身不能证明已审核 Feature。

动作：

```text
先写明“缺什么因果证据”
-> 人工确认证明强度
-> 只做最小行为增强
```

AES `P2_001` 和 CRC `P1_007 / P1_013 / P1_018` 可作为“先证明 Gap，再最小增强”的历史参考，但不能机械复制刺激。

#### E. SEMANTIC / ARCHITECTURE GAP

出现以下任一情况：

- Driver Public API 根本拿不到需要的硬件事实；
- Firmware / Wrap / Wire 语义不足；
- Capability Mapping 不足；
- `ip.md` 与当前硬件权威资料冲突；
- Feature 本身可能定义错误。

动作：

**停止当前 Case 优化，不在当前任务猜修；重新编译对应 Task Context，单独评审。**

### Step 6：代码只按已审核 Contract 最小优化

核心要求：

```text
Feature / Pass Criteria
-> minimum sufficient hardware observation
-> Case真实取得该事实
-> 决定性断言前记录
-> execution结束后仍可从Canonical Result / bound Artifact解析
-> ET_CASE_REPORT可消费
```

CRC 进一步确认：多阶段 Case 如果早期 Assert 会让后续必要现场丢失，应先完成本 Case 安全且必要的 Observation / Snapshot，再统一做决定性断言；这不是允许无界继续执行。

### Step 7：同步 Chip Mapping

如果公共 `method.observations` 使用新稳定 endpoint：

- 检查 `<CHIP>_<ip>.md` 是否已有稳定语义到实际寄存器 / Field 映射；
- 映射缺失必须按 R100/R140 补芯片文档事实；
- 公共 `ip.md` 不写地址 / 基址 / 芯片 SDK 符号。

### Step 8：Report / Excel 闭合

必须验证：

```text
Canonical Result
-> failure_observations
-> ET_CASE_REPORT
-> chip endpoint mapping（适用时）
-> Excel Remark
```

Reviewer 最终看到的备注必须是 Evidence，不只是“验证完成”。

CRC 进一步确认：stable `path/key` 与 Reviewer-facing `label` 必须分层；label 调整后对应 Report Regression 也必须同步。

### Step 9：软件验证

至少按目标 IP Task Context 执行：

```powershell
python tools/quality/validate_case_docs.py test_case_doc/<ip>/<ip>.md
python tools/quality/validate_case_method_contract.py test_case_doc/<ip>/<ip>.md
python tools/quality/check_case_spec_implementation.py
python tools/quality/check_pc_code_rules.py --root . pc/et_test_platform/test_cases/<ip>
python tools/quality/check_case_orchestration_rules.py --root . pc/et_test_platform/test_cases/<ip>
python -m pytest --collect-only -q pc/et_test_platform/test_cases/<ip>
python tools/validate_pc.py
git diff --check
git status --short
```

如果涉及 Report 公共层，再执行其 Regression。

如果全仓 Gate 被已知非当前 IP 债务阻塞，可以增加**当前 IP scoped diagnostic** 来证明责任域状态，但必须同时保留 repository-wide Gate 的真实 FAIL/NOT_VERIFIED 结论；scoped PASS 不能冒充全仓 PASS。

### Step 10：当前 SHA CI / HIL 状态独立报告

只能按实际证据写：

```text
SOURCE / DESIGN REVIEW PASS
SOFTWARE GATE PASS / NOT_EXECUTED
CI PASS / CI_PENDING / NOT_VERIFIED
HIL PASS / FAIL / NOT_EXECUTED
```

软件 PASS 不能替代 HIL；历史 HIL 不能替代当前精确 SHA。

---

## 8. Wave 2：只有 `ip.md / PLAN`、没有 Formal Case 代码的固定流程

适用于 STIMER / CORDIC / WDG / FMAC。

### Step 1：必须先走 `ip-package / analysis`

按照 R002：

```text
新IP / 未实现IP
-> analysis先完成并人工审核
-> 才允许Case / Driver / Service / Wrap / Capability开发
```

不得从 `PLAN` 直接开始写 `test_*`。

### Step 2：重新按当前 R120 + R140 人审标准梳理现有 PLAN

旧 PLAN 中常见问题：

- `inputs / steps / observations / pass_criteria` 没有统一使用 `<摘要>：<正文>`；
- steps 少于 6 条；
- Observation 没有稳定硬件端点；
- Expected / Oracle 不明确；
- Chip Mapping 与公共语义没有闭合；
- Gap 只有名字，没有解除条件。

必须逐 Case 重写为 Implementation Ready Contract。结构先满足 R120 统一机器语法，语义再按 R140 Human Review 失败关闭；不得把“能过 Checker”当成“分析已完成”。

### Step 3：Chip 文档必须完成 Source / Mapping / Gap 闭合

`<CHIP>_<ip>.md` 必须至少确认：

```text
Source Coverage
Source Item Trace
Hardware / Register / Driver Claim
Conflict / Unknown
公共Observation -> 实际寄存器/Field映射
Chip -> Public Feature Mapping
Chip -> Public Case Adaptation
```

核心资料仍 `UNAVAILABLE` 或语义仍 `UNKNOWN/CONFLICT` 时不能宣称分析完成。

### Step 4：人工审核 PLAN

每个 Case 在写代码前必须达到：

```text
Feature具体
Inputs 1～3条，且每条为 <摘要>：<正文>
Steps 6～8条真实动作，且每条为 <摘要>：<正文>
最小充分硬件Observation明确，且每条为 <摘要>：<正文>
Expected / Oracle明确
Pass Criteria 2～5条且可核对，且每条为 <摘要>：<正文>
Resource / Cleanup / P级合理
Gap及解除条件明确
```

### Step 5：未实现 Case 必须继续使用 PLAN

```text
ET_CASE_PLAN
implementation_status: PLANNED
```

只有真实满足：

```text
Registry已注册
+ 唯一真实 test_* 已实现
+ 文档 / Evidence / Report绑定完成
```

才允许升级为 `ET_CASE_SPEC`。

### Step 6：实现阶段按责任域拆 Task Context

不要一个大任务一次改所有层。

典型顺序：

```text
analysis / Contract审核
-> capability / execution mapping（若缺）
-> PC Driver（若缺）
-> Firmware Service / Wrap / Chip Driver（若缺）
-> Formal Case
-> Report / Excel
```

如果需要新增或改变 Wire，必须作为独立跨层语义变更同时验证 PC / Firmware / Golden Vector，不能在 Case 实现里顺手加命令。

### Step 7：每实现一批 Case 就执行同一 Evidence Closure

不允许等全部 Case 写完再一次性补证据。

固定闭环：

```text
一个Case实现
-> Canonical Expected / Actual / Hardware Observation
-> Artifact lifecycle
-> ET_CASE_REPORT
-> software gates
```

---

## 9. Evidence / Report 统一重要点

### 9.1 Hardware Observation 必须是真硬件 / 设备事实

允许：

```text
STATUS.FINISH
RESULT_DOUT[0..3]
IRQ_RAW.COMPLETE
IRQ_STATUS.COMPLETE
DMA_CHANNEL_STATUS.INPUT
TIMING.CYCLE_COUNT
真实Instrument/Peer/FPGA endpoint
```

默认不属于 Hardware Observation：

```text
PC Golden
parameter_id
produced_bytes
event_count / delta
软件 data_match
执行轮数
配置输入值（未做真实readback）
```

### 9.2 一条 Observation 只允许一个来源端点

禁止：

```text
actual_state = {
  result_dout: ...,
  finish: ...,
  irq: ...
}
endpoint = STATUS.FINISH
```

正确做法是拆分。

### 9.3 配置值不等于硬件 Readback

Case 配置了 Mode / Counter / Endian，并不能把该配置值在报告中标为“DUT寄存器实际值”。

只有真实读取硬件端点，才可以写 Hardware Observation。

### 9.4 Feature 强度不能超过 Observation 强度

```text
只看到终态 BUSY=0
!= 证明运行期 BUSY 发生过 1->0

Clear后只看到0
!= 证明W1C语义

DMA Channel一瞬间Active
!= 证明Gate长期阻塞
```

### 9.5 Artifact 是完整 Snapshot

同一路径：

```text
第一次 write
第二次 write
```

不表示 Merge。

关键事实不能只存在于中间 Snapshot。

### 9.6 FAIL 必须保留足够现场

决定性 Assert 前先记录 Expected / Actual / Hardware State；不允许 Assert 失败后报告只剩 Python Exception。

CRC 补充经验：多阶段 Case 要把属于同一证明链的安全 Observation 完成后再统一断言，否则第一阶段 FAIL 会让后半段决定性 Evidence 永久缺失。

### 9.7 Excel 只展示关键 Evidence

每 Case 1～4 个字段；完整事实留在 Result / Artifact。

报告不是调试日志，也不是寄存器 dump。

### 9.8 failure_observations 不是“所有现场字段”

CRC `P1_013` 进一步证明：

```text
failure_observations
= minimum sufficient PASS/FAIL proof
!= every useful diagnostic field
```

补充硬件现场可以留在 Canonical Result / ET_CASE_REPORT，但不能因为“有价值”就把它升级为决定性失败字段。

---

## 10. 后续优化明确禁止项

下面任何一条发生，都必须停止当前优化并重新评审。

### 10.1 禁止绕过规则 / Task Context

- 禁止凭文件名猜规则；
- 禁止持续对话作为“不重新编译 Task Context”的理由；
- 禁止 Case 任务顺手改 Driver / Firmware / Wire / Capability / 公共 Framework；
- 禁止为了本 IP 修改冻结公共架构，除非证明为跨 IP 稳定缺口并获得用户批准。

### 10.2 禁止为了 Gate 变绿弱化测试

- 禁止删除 Case；
- 禁止降低 Assert；
- 禁止把 FAIL 改成 SKIP；
- 禁止扩大 allowlist；
- 禁止增加 Timeout 掩盖状态机问题；
- 禁止关闭 Checker / `noqa`；
- 禁止减少参数矩阵来规避失败。

### 10.3 禁止伪造 Evidence

- 禁止把配置值冒充 readback；
- 禁止把软件 Golden / produced_bytes / event_count 冒充寄存器；
- 禁止一个 Observation 合并多个端点；
- 禁止把 Service latch 冒充 IRQ_RAW / IRQ_STATUS；
- 禁止因为报告“看起来更完整”而增加无关硬件读取；
- 禁止扫描 Artifact 目录猜 Evidence，必须由 Canonical Result 显式绑定。

### 10.4 禁止无审核扩展 Case 语义

- `RECORD_ONLY` 只能补记录，不能增加硬件刺激；
- 只有明确 `CASE_CHANGE` 才允许行为增强；
- 行为增强前必须先人工确认 Feature 需要的证明强度；
- 不允许 Agent 因“这样更严谨”自行增加测试目标。

### 10.5 禁止公共 / 芯片事实混层

公共 `<ip>.md` / Case / Driver / Service / Wrap 禁止出现：

```text
芯片名
物理地址
固定基址
IRQn符号
目标芯片SDK结构体
固定实例
```

这些进入 `<CHIP>_<ip>.md`、Capability、Board、Mapping、Chip Driver。

公共文档可以使用稳定的寄存器 / Field 语义名称，但不写物理地址。

### 10.6 禁止 PLAN 冒充 SPEC / PASS

- 没有 Registry + test_* 的 Case 只能 PLAN；
- `ADAPTED` 不等于 HIL PASS；
- `SUPPORTED` 不等于软件已实现；
- 软件 Gate 不等于 HIL；
- 历史 HIL 不等于当前 SHA HIL；
- `SOURCE / DESIGN REVIEW PASS` 不等于软件或硬件全 PASS。

### 10.7 禁止无关重构

- 不批量格式化无关文件；
- 不为了代码短创建 Mixin / BaseDriver / 通用 Helper 容器；
- 不因为第二个 IP “可能以后会共用”就新增 Registry / Plugin / DI / 通用资源图；
- 一个问题只修一个责任根因。

### 10.8 禁止真实硬件危险操作绕过人工门禁

涉及真实 FPGA / Silicon、Flash、Option Byte、OTP/NVR/Fuse、电源、Debug Unlock 等操作时继续遵守外层人工门禁。

---

## 11. 每个 IP 的完成 Gate

### Gate A：Contract Human Review

必须全部满足：

- Feature 具体；
- `method.inputs / steps / observations / pass_criteria` 全部使用 R120 冻结的 `<摘要>：<正文>` 统一行语法；
- Inputs 可复原；
- 6～8 步可顺序复原测试逻辑；
- Observation 有具体稳定硬件端点 / Observer；
- Expected / Oracle 清楚；
- Pass Criteria 可直接核对；
- Report 字段能够证明本次执行；
- `validate_case_method_contract.py` 通过只代表机器结构正确，R140 Human Review 仍必须独立通过。

### Gate B：Contract ↔ Implementation

对 SPEC：

```text
ET_CASE_SPEC
<-> Registry case_id
<-> 唯一真实 test_*
<-> 实际 Driver调用顺序
<-> Actual / Expected / Assertion
<-> failure_observations
<-> ET_CASE_REPORT
```

任一不一致都不能完成。

### Gate C：Evidence Closure

每个 execution 都要满足：

```text
Pass Criteria
-> Evidence key
-> Canonical Measurement / Observation / bound Artifact
-> execution结束仍存在
-> Report可解析
```

### Gate D：Chip Mapping

如果报告需要显示目标芯片实际寄存器名称：

- 公共 stable endpoint 存在；
- `<CHIP>_<ip>.md` 映射存在；
- 无映射时不猜。

### Gate E：软件验证

必须真实执行适用 Checker / pytest / validate_pc，才能写 PASS。

不能执行时写 `NOT_EXECUTED` / `NOT_VERIFIED`。

如果只执行 scoped diagnostic，则只能写“当前 IP scoped checks PASS”；repository-wide 状态必须单独记录。

### Gate F：CI

只有 GitHub `Software Quality Gate / validate-software` 对**当前精确 head_sha**结论为 `success`，才算 repository-wide CI 闭环。

Scoped Gate / carrier PR 的成功不得替代 Gate F。

### Gate G：HIL

硬件结论只来自当前 SHA 的真实 FPGA / Silicon/HIL Evidence。

设计样板推广可以在 HIL 不可用时完成 SOURCE/DESIGN REVIEW 或软件 Evidence Closure，但不得写成硬件验证完成。

---

## 12. 每个 IP 结束时必须产出的 Review 记录

每个 IP 最终只需要一份简洁 Review 记录，至少包括：

```text
1. 优化基线 branch / SHA
2. SPEC / PLAN / Registry数量
3. 发现的问题分类
4. DOC_ONLY / RECORD_ONLY / CASE_CHANGE / GAP 数量
5. 改动文件
6. 为什么改
7. Contract / Evidence / Report审核结论
8. software gate实际结果
9. exact-SHA CI结果
10. current-SHA HIL结果
11. 未解决的真实风险
```

避免为同一 IP 创建大量重复规则式文档；过程 Plan / Review 只能记录事实和状态。

---

## 13. CRC 第二个硬件 IP 推广完成总结

CRC 是 AES Pilot 之后第一个真正按本计划完整推进的硬件 IP。完整 Closure 记录见：

```text
report/review/20260819_crc_optimization_closure_review.md
```

本节只提炼后续 DMA / UART 必须继承的**过程经验**，不把 CRC 的具体寄存器或 Case 结构升级成新规则。

### 13.1 CRC 最终 Closure 状态

```text
CRC Stable Contract                    CLOSED
24 Formal Case                         CLOSED
Canonical Measurement / Observation    CLOSED
ET6801 Chip Mapping                    CLOSED
ET_CASE_REPORT / Excel software path   CLOSED
Contract <-> Source <-> Report Gate    CLOSED
CRC_F_012 FIFO Physical Depth          OPEN SEMANTIC GAP
FPGA HIL @ validated source SHA        NOT_EXECUTED / NOT_VERIFIED
Silicon HIL @ validated source SHA     NOT_EXECUTED / NOT_VERIFIED
```

CRC 软件闭环绑定的精确 Source / Contract SHA：

```text
96f87f642b87de7d193299b966665feb91260e0a
```

后续 Closure / Plan 文档提交比该 SHA 新，不得用 docs-only HEAD 替代 validated source SHA。

### 13.2 CRC Human Review 初始分类

24 个稳定 SPEC 在进入实现修改前先完成人工分类：

```text
DOC_ONLY      = 1
RECORD_ONLY   = 20
CASE_CHANGE   = 3
Case GAP      = 0
Semantic GAP  = 1   # CRC_F_012 FIFO Physical Depth
```

三个真正需要行为级最小增强的 Case：

```text
CRC_P1_007  Arbitrary Byte Length + LENGTH Programming / Readback
CRC_P1_013  IRQ Enable / Disable + Force + Delivery causality
CRC_P1_018  BUS_ERROR legal-control / illegal-width causality + recovery
```

这再次证明：**绝大多数旧 Case 的问题不是“没有测试”，而是 Contract / Evidence / Report 没有把真实测试能力闭合。** 未分类前禁止默认改硬件动作。

### 13.3 CRC 实施中遇到的问题与解决方式

#### CRC-ISSUE-001：PASS 路径有证据，但 FAIL 路径会在过早 Assert 时丢现场

问题：

P0 生命周期 / 多阶段 Case 中，如果第一阶段立即 `assert`，后续本来属于同一 Case 的安全 Observation 和最终 Snapshot 可能永远无法形成。这样 PASS 有完整报告，FAIL 只剩异常。

解决：

```text
先完成该 Case 必要且安全的全部阶段 Observation
-> 发布单次完整 Snapshot
-> 再统一执行最终决定性 Assert
```

这不是“延迟失败”，而是让 PASS / FAIL 使用同一组决定性 Evidence。后续 DMA 的多 Channel / 多阶段 Case 必须特别检查这一点。

#### CRC-ISSUE-002：公共 Contract 文字本身也受芯片中立机器规则约束

问题：

`crc.md` 稳定区曾写“寄存器地址”一词，即使上下文是在说“公共 Case 不应写地址”，机器规则仍把它识别为稳定区物理术语泄漏。

解决：

改成芯片中立的人审表达，例如“具体芯片地址只进入 Chip Adaptation”，不在公共稳定 Contract 中出现物理地址术语。

经验：**不要和 Checker 辩论意图；公共 Contract 必须在文本层面也保持稳定、芯片中立。**

#### CRC-ISSUE-003：Chip Adaptation 机器摘要不能使用人类自创缩写

问题：

CRC Chip Summary 曾写：

```text
ADAPTED=27, PARTIAL=1
```

机器契约要求精确枚举：

```text
ADAPTED=27; PARTIAL_ADAPTATION=1
```

解决：

按机器 Schema 使用精确状态名，不发明 `PARTIAL` 等缩写。

经验：机器可解析段是 Contract，不是自由文本。

#### CRC-ISSUE-004：ET_CASE_REPORT 的稳定 key 与人审 label 是两层东西

问题：

部分 Report field 的 label 过于像英文标识符，触发 `ETCASE611` 可读中文要求；但直接修改 key 会破坏 Contract / Source 绑定。

解决：

```text
path/key: 保持稳定机器字段
label:    改成人能直接审核的中文说明
```

随后同步 Report/XLSX Regression 的显示文案断言。

经验：**机器身份稳定，Reviewer 文案可读；不要为了“中文化”重命名 Canonical key。**

#### CRC-ISSUE-005：不是所有可记录硬件事实都应该成为 failure_observations 决定性字段

问题：

`CRC_P1_013` Disable 阶段同时有：

```text
disabled_event_count_delta
IRQ_RAW.<Source> after Force
```

真正证明“Disable 后不再 Delivery”的决定性事实是：

```text
disabled_event_count_delta == 0
```

Raw 仍然有价值，但它只是补充说明 Force 刺激确实存在，不能反过来让 failure_observations 变得比 Pass Criteria 更宽。

解决：

- `disabled_event_count_delta` 保留为决定性失败字段；
- `disabled_force_raw` 继续留在 ET_CASE_REPORT / Canonical Result 作为 supplemental hardware context。

经验：**failure_observations 是 minimum sufficient proof，不是“所有能看到的字段列表”。**

#### CRC-ISSUE-006：原有 Case 能“看到现象”，但因果证明不一定够强

CRC 三个 CASE_CHANGE 的共同问题不是缺 API，而是旧证据无法区分多个可能原因。

处理方式：

```text
P1_007:
Byte Length
-> LENGTH programming/readback
-> CALCULATE
-> Result + Remaining terminal state

P1_013:
Enable + Unmask -> Force -> Delivery
-> Clear + Disable same Source -> Force again
-> no new Delivery

P1_018:
legal access control -> no BUS_ERROR
-> illegal width stimulus -> BUS_ERROR exactly once
-> lifecycle recovery -> normal CRC still works
```

经验：先写清“缺什么因果证据”，再做最小行为增强；不能因为想让 Case 更漂亮就扩 Feature。

#### CRC-ISSUE-007：Evidence 重排后仍必须满足 PC Case 可读性规则

问题：

P0 为了完整 FAIL Evidence 重排流程后，触发 `ETPC105 / ETPC106`：业务循环缺紧邻注释、Case body 缺业务目的注释。

解决：

只补真实业务目的注释，不修改执行行为。

经验：结构优化和可读性规则必须一起通过；不要用格式化或注释修改掩盖行为变化。

#### CRC-ISSUE-008：Contract label 更新后，Report Regression 也必须同步

问题：

Report 已正确输出新的中文 label，但模拟 XLSX Regression 还断言旧 label，导致软件回归失败。

解决：

同步 Regression 的 Reviewer-facing 文案期望；底层 stable endpoint / key 不变。

经验：R110 的“双向同步”不仅是 `ip.md <-> Case`，还包括 Report Regression。

#### CRC-ISSUE-009：仓库级 Gate 的无关债务不能被误判成 CRC 自身失败，也不能被 CRC 顺手修掉

CRC 最终 scoped Gate 中，CRC 自身以下检查全部通过：

```text
Python syntax / Ruff for CRC scope
git diff whitespace
Rule governance
Task context navigation
IP Contract sync
CRC public stable contract
Chip adaptation validation
CRC ET_CASE_SPEC validation
CRC implementation binding
Case orchestration
PC AST / documentation rules
CRC Contract-Source consistency regression
CRC Report / XLSX regression
CRC Formal Case collection
```

CRC Formal Case 的参数化 collection 当时为：

```text
P0: 5 executions
P1: 34 executions
P2: 3 executions
P3: 3 executions
Total: 45 executions
Stable Case IDs: 24
```

但仓库级统一 `Software Quality Gate` 仍暴露了**CRC 之外**的既有问题，包括：

- AES / 通用 Report / Checker 的 Ruff-format debt；
- Firmware generated metadata 缺失造成的 unit failure；
- AES synthetic YAML 中未加引号的 `[...]` label 导致解析失败。

独立 full-PC unit diagnostic 当时结果为：

```text
684 passed
3 skipped
4 failed
```

这 4 个失败均不属于 CRC 责任域。

处理原则：

```text
CRC scoped closure 用于证明 CRC 自身是否闭合
!= 宣称 repository-wide gate 已经 PASS

发现非 CRC 债务
-> 如实记录
-> 不跨 IP 顺手修
-> 留给对应责任域单独闭环
```

临时 CI carrier / validation PR 只用于获得可观察结果，最终全部关闭且不合并到 `review_code`。

#### CRC-ISSUE-010：软件 Closure 与当前精确 SHA HIL 必须继续分开

本轮没有可用 FPGA / Silicon 环境，所以：

```text
CRC software / contract / evidence / report closure = CLOSED
CRC current-SHA FPGA HIL = NOT_EXECUTED / NOT_VERIFIED
CRC current-SHA Silicon HIL = NOT_EXECUTED / NOT_VERIFIED
```

后续任何 Agent 都不得把软件闭环改写成硬件 PASS。

### 13.4 CRC 实际遵循 / 路由到的规则文档

本轮主路径实际依赖：

```text
AGENTS.md
R001_agent_rule_governance.md
R002_task_context_navigation.md
R100_public_ip_semantics_and_chip_adaptation.md
R110_contract_document_sync.md
R120_public_ip_machine_contract.md
R130_canonical_result_evidence.md
R140_ip_analysis_workflow.md
R210_pc_case_responsibility.md
R220_python_style_quality.md
R500_operator_pipeline.md        # 因 ET_CASE_REPORT / Excel / Result Regression 进入范围
R320_firmware_irq.md             # 用于核对 IRQ register / ISR latch / Service delivery 边界；未扩 Firmware 写范围
```

同时以以下当前真实 Contract / Closure 记录作为事实来源：

```text
test_case_doc/crc/crc.md
test_case_doc/crc/ET6801_crc.md
report/review/20260819_crc_optimization_closure_review.md
```

本轮没有因为 CRC 扩写 PC Driver / Firmware Service / Wrap / Wire / SVD，因此没有把 `R200 / R300 / R310 / R330 / R400 / R410` 对应责任域顺手拉入修改范围。

### 13.5 CRC 后确认可以继续推广的经验

后续 DMA / UART 固定继承：

1. **先 Human Review Contract，再碰代码。**
2. **先分类 DOC_ONLY / RECORD_ONLY / CASE_CHANGE / GAP，再决定是否允许新增硬件动作。**
3. **Failure path Evidence 与 Pass path 同等重要；决定性 Assert 前必须完成必要记录。**
4. **Canonical Observation 一端点一事实；寄存器、Service latch、event count、Oracle 不能混来源。**
5. **Artifact 是完整 Snapshot，不是 append log。**
6. **Stable key 与人审 label 分层；机器字段稳定，显示文字可读。**
7. **failure_observations 只保留最小充分证明，补充现场可留在 Canonical Result / ET_CASE_REPORT。**
8. **Chip Mapping 显示实际寄存器名，但公共 Contract / Case 保持芯片中立。**
9. **Contract / Source / Report 必须有自动一致性 Regression，不能只靠一次人工 Review。**
10. **Scoped Gate 可以隔离责任域诊断，但不能伪装成全仓 Gate PASS。**
11. **历史 HIL、软件 Gate、当前 SHA HIL 三种状态必须分别报告。**

### 13.6 CRC 经验不能机械复制到 DMA 的部分

下面内容只属于 CRC，不是 DMA 模板：

- `RESULT.CRC / LENGTH.REMAINING_INPUT_COUNT / FIFO.OVERFLOW` 等 endpoint；
- CRC 的 PC Golden 算法和 polynomial / seed / remainder Oracle；
- `CRC_P1_007 / P1_013 / P1_018` 三个具体 Case 的刺激；
- FIFO Physical Depth 的具体 Gap 形式；
- CRC 的 24 Case 数量与 P0/P1/P2/P3 参数矩阵。

DMA 必须重新从自己的 Feature / Contract / Case / Chip Mapping 得出 minimum sufficient proof，不能因为 CRC 已经成功就复制同名字段或同样的 Case 模板。

### 13.7 DMA 推广结果

CRC Closure 后进入的 DMA Human Review / Evidence Closure 已完成。最终结果：

```text
28 Formal SPEC -> 当前实现层软件/Contract/Evidence/Report CLOSED
11 ET_CASE_PLAN -> 继续保持 PLAN
5 CASE_CHANGE -> 已按最小证明强度闭合
ET6801 stable endpoint/register mapping -> CLOSED
DMA Canonical Result -> ET_CASE_REPORT -> XLSX -> CLOSED
DMA scoped final correction gate -> PASS
Current-SHA FPGA/Silicon HIL -> NOT_EXECUTED / NOT_VERIFIED
```

详细结论与未解决硬件/Bench Gap 见：

`report/review/20260819_dma_optimization_closure_review.md`

DMA 与 UART 的 PLAN/Open Gap 后续在对应硬件、Observer 或 Bench 条件具备时单独继续，不阻塞当前推广队列进入 Framework Communication。

---

## 14. 当前总执行队列

```text
[历史 Closure 记录，需按 3245f439 新规则基线重校验]
AES  （Pilot）
CRC  （Wave 1 #1）
DMA  （Wave 1 #2，历史实现层软件/Contract/Evidence/Report CLOSED）
UART （Wave 1 #3，历史实现层软件/Contract/Evidence/Chip Mapping/Report CLOSED）

[当前 NEXT：一次性治理迁移]
Repository-wide Human Review Contract Revalidation / Migration
- SPEC / PLAN 统一 <摘要>：<正文>
- method.steps 统一 6～8 条真实动作
- 新 Checker 违例清单与逐 IP 清零

[迁移完成后 NEXT：Formal Domain]
Framework Communication（非硬件IP）

[再下一阶段：只有 PLAN / ip.md，无 Formal Case代码]
STIMER
CORDIC
WDG
FMAC

[支撑 Contract，暂不进入 Formal Case队列]
CRG
```

本次治理升级是一次性基线迁移，不等于重新做一遍所有 IP 的硬件测试。历史 Closure 记录继续作为当时基线下的 Evidence/Implementation 事实保存；只有新规则直接影响的 Contract Human Review 结构、语义和由此暴露出的真实实现/Evidence Gap 才进入本轮 revalidation。

在这次迁移完成前，**Framework Communication 不进入代码修改阶段**。

---

## 15. 下一步

当前不再直接进入 Framework Communication 实现修改，先执行：

```text
Repository-wide Human Review Contract Revalidation / Migration
```

固定顺序：

```text
确认 review_code 当前精确 HEAD 与 rule baseline commit 3245f43943c518982640b2e0da2184cb8cd942e5
-> 在可执行仓库环境补做规则治理 / Task Context / Checker Regression
-> 运行 validate_case_method_contract.py 全仓扫描
-> 生成按 IP / Case / SPEC-PLAN / diagnostic code 分组的 violation inventory
-> 先处理已实现 Formal Domain：AES -> CRC -> DMA -> UART -> Framework Communication
-> 再处理 PLAN-only Domain：STIMER -> CORDIC -> WDG -> FMAC
-> 每个 Domain 只做规则要求的最小 Contract 修复；语义不充分则进入 R140 Human Review，不允许机械拆句凑 6～8 步
-> 新 Checker 全仓清零后运行 repository-wide software gate
-> Framework Communication 恢复 Human Review / Evidence Closure
```

当前这一阶段的关键原则是：

**先证明新规则真的能发现问题，再修历史 Contract；不通过 allowlist、关闭 Checker、只检查新增文件等方式绕过迁移债务。**

详细事件、根因和执行计划见第16节。

---

## 16. 2026-08-20 Human Review Contract 规则基线修复与迁移计划

本节记录 2026-08-20 在进入 Framework Communication 之前发生的治理事件，以及由此产生的当前唯一优先任务。若本节的“当前状态 / NEXT”与前文较早的历史状态描述冲突，以本节和第14～15节更新后的状态为准。

### 16.1 发生了什么

UART Closure 后，原计划直接进入 `Framework Communication Human Review / Evidence Closure`。在对 Framework Communication 做只读基线检查时，发现其当前唯一 Formal SPEC 的 Human Review Contract 仍存在明显结构不足：

- `method.steps` 当前只有 3 条，不能按已约定的人审标准顺序复原完整测试流程；
- `inputs / observations / pass_criteria` 的表达仍偏聚合，Reviewer 需要结合源码才能完整理解事务执行和判定链；
- 当前 Formal Case 实际执行 20 rounds × small/medium/large 三类 payload，真实代码比公共 Contract 表达得更具体；
- Case 中 per-class `retry_count`、latency、throughput、transactions 等事实已经存在，但公共报告和失败字段并未完整体现 Feature F002/F003 的证明边界；
- ECHO mismatch 的决定性 Assert 发生在最终结构化 Result/Artifact 发布之前，FAIL Evidence 生命周期还需要单独审核。

这次检查暴露出的重点不是“Framework Communication 这个 IP 写得不好”，而是：**仓库此前虽然已经在 R140 中要求 Human Review 可复原、Steps 6～8 条，但公共格式的唯一 Owner 和机器失败关闭 Gate 没有真正闭合。**

继续只修 Framework Communication 会再次形成“当前 IP 看起来改好了，但下一个 IP 仍可使用另一种格式”的局部修复，因此暂停 Domain 推广，先修规则根因。

### 16.2 根因判断

确认的治理缺口包括：

1. **R120 之前只冻结 Case/Plan/Report Schema，没有把四个 `method.*` 列表的统一 Human Review 行语法明确收归公共机器契约 Owner。**
2. **R140 同时承担结构表达和语义质量，存在“优先使用”等容易被执行 Agent 当成写作建议而非统一红线的表述。**
3. **`validate_case_docs.py / validate_case_plans.py` 能检查 Schema 和字段存在性，但没有独立 Gate 强制每条使用同一种 `<摘要>：<正文>` 结构，也没有统一失败关闭 `steps=6..8`。**
4. **`tools/validate_pc.py` 此前没有这条专门的 repo-wide Human Review method checker，因此历史文档即使不满足统一表达，也可能在其他 scoped Gate 下被记录为 Closure。**
5. **Closure 状态和“当前规则一致性”此前没有区分。** 一个 IP 在当时规则和 scoped Evidence Gate 下 CLOSED，不代表未来活动规则升级后无需重新验证 Contract 结构。

因此本次问题定性为：

```text
PRIMARY ROOT CAUSE = RULE / MACHINE-GATE GAP
NOT = 单一 Framework Communication Case bug
NOT = DMA/UART/AES/CRC 需要无条件重写硬件行为
```

### 16.3 已完成的规则修复

规则基线修复提交：

```text
3245f43943c518982640b2e0da2184cb8cd942e5
governance: enforce uniform case method review grammar
```

该提交完成：

#### A. R120 冻结唯一公共 Human Review 行语法

所有 IP、所有 SPEC / PLAN 的：

```text
method.inputs[]
method.steps[]
method.observations[]
method.pass_criteria[]
```

统一使用：

```text
<摘要>：<正文>
```

并明确：

- 第一个结构分隔符必须是中文全角 `：`；
- 摘要和正文都不能为空；
- `输入1 / 步骤1 / 观测1 / 判据1` 及数字变体禁止作为占位摘要；
- `测试过程 / 功能验证 / 数据处理 / 其他` 等空泛摘要失败关闭；
- SPEC / PLAN 使用完全相同的结构语法；
- `method.steps` 必须为 6～8 条真实测试动作。

#### B. R140 回归单一职责

R140 不再自己定义第二套格式，而是明确：

```text
R120 = 机器可判定的统一行语法 / Steps 数量结构 Owner
R140 = Feature / Inputs / Steps / Observation / Oracle / Pass Criteria 的人审语义质量 Owner
```

即：

```text
Machine Gate PASS
!= Human Review PASS
```

机器只能证明格式合法，不能替 Reviewer 判断测试是否真的可复原、Observation 是否足够、Oracle 是否强。

#### C. 新增统一 Checker

新增：

```text
tools/quality/validate_case_method_contract.py
```

该 Checker 默认扫描所有公共 `test_case_doc/<ip>/<ip>.md`，同时解析 SPEC 和 PLAN，不做单 IP 私有判断。

固定诊断：

```text
ETCASE430 = SPEC method.* 行语法不合法
ETCASE431 = SPEC method.steps 数量不在 6..8
ETPLAN223 = PLAN method.* 行语法不合法
ETPLAN224 = PLAN method.steps 数量不在 6..8
```

#### D. 新增失败关闭 Regression

新增：

```text
pc/et_test_platform/framework_validation/unit/code_quality/test_case_method_human_review_contract.py
```

覆盖：

- 无 `：`；
- ASCII `:` 代替结构分隔符；
- 空摘要；
- 空正文；
- `步骤1` 等编号占位摘要；
- `测试过程` 等空泛摘要；
- 单条字符串换行；
- 5 Steps；
- 9 Steps；
- 正文内部额外出现全角冒号的合法情况。

#### E. 接入规则 Owner 和统一软件 Gate

同步：

```text
report/design/rule_owner_catalog.yaml
tools/validate_pc.py
```

`tools/validate_pc.py` 新增：

```text
Case human-review line grammar
-> tools/quality/validate_case_method_contract.py
```

因此后续不能再出现“规则里写了统一格式，但总软件 Gate 不检查”的状态。

### 16.4 当前不能声称什么

这次 GitHub 连接可以读取和提交仓库文件，但当前交互环境不能执行仓库本地 Python / pytest / Task Context 命令。因此截至本 Plan 更新时：

```text
Rule source change                         COMMITTED
New checker source                         COMMITTED
New checker regression source              COMMITTED
validate_pc integration                    COMMITTED
Repository-wide checker execution          NOT_EXECUTED / NOT_VERIFIED
Repository-wide pytest / validate_pc        NOT_EXECUTED / NOT_VERIFIED
Exact-SHA CI                               NOT_VERIFIED
FPGA/Silicon HIL                           NOT_APPLICABLE TO RULE CHANGE / NOT_EXECUTED
```

不得因为代码已经提交就写：

```text
repository-wide gate PASS
all IP migrated
DMA/UART current rule compliant
Framework Communication fixed
```

### 16.5 历史 Closure 如何处理

本次规则升级**不删除、不改写** AES / CRC / DMA / UART 已经形成的历史 Closure 事实。

正确状态拆分为：

| Domain | 历史实现 / Evidence Closure | 3245f439 后 Human Review Contract 状态 | 当前动作 |
|---|---|---|---|
| AES | 保留历史 Pilot 结论 | `REVALIDATION_REQUIRED / NOT_VERIFIED` | 新 Checker + R140 re-review |
| CRC | 保留 `96f87...` Closure 事实 | `REVALIDATION_REQUIRED / NOT_VERIFIED` | 新 Checker + 最小 Contract migration |
| DMA | 保留 `3678fc...` Closure 事实 | `REVALIDATION_REQUIRED / NOT_VERIFIED` | SPEC + 11 PLAN 全量扫描 |
| UART | 保留 `377a79...` Closure 事实 | `REVALIDATION_REQUIRED / NOT_VERIFIED` | SPEC + 7 PLAN 全量扫描 |
| Framework Communication | 尚未进入本轮 Closure | 已知至少存在 Human Review 结构 Gap | 规则迁移后恢复 Review |
| STIMER/CORDIC/WDG/FMAC | PLAN-only，未实现 | `REVALIDATION_REQUIRED` | 按 Wave 2 / R140 分域处理 |
| CRG | 支撑 Contract，无 SPEC/PLAN | 本 Checker 当前不适用 | 保持 Support Contract |

关键原则：

```text
历史 CLOSED
= 当时基线下的实施 / Evidence 事实

当前规则 PASS
= 必须重新通过当前活动 R120/R140 + Checker
```

二者不能互相覆盖。

### 16.6 下一步 Phase G0：先验证规则基线本身

在任何 IP 文档继续修改前，在可执行仓库环境先建立治理 Task Context，并执行当前规则自身的专项验证：

```powershell
python tools/quality/validate_rule_governance.py
python tools/governance/compile_task_context.py validate
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_case_method_human_review_contract.py
python tools/quality/validate_case_method_contract.py
python tools/validate_pc.py
```

如果 `validate_case_method_contract.py` 因历史 Contract 债务失败，**这是本阶段预期且有效的结果**；必须保存真实 violation inventory，不能为了变绿删除 Checker 或加历史 allowlist。

如果 Checker 自身 Regression 失败，则先修 Checker / R120/R140 一致性，不进入 IP migration。

### 16.7 下一步 Phase G1：形成全仓 Violation Inventory

运行新 Checker 后，把全部违例按以下维度归类：

```text
IP
Case ID
SPEC / PLAN
method.inputs / steps / observations / pass_criteria
Diagnostic Code
纯结构问题 / 需要 Human Review 的语义问题
是否影响已实现 Formal Case
```

最少输出：

```text
AES
CRC
DMA
UART
Framework Communication
STIMER
CORDIC
WDG
FMAC
```

不预先假设哪个 Domain 一定有多少违例；**数量必须来自 Checker 实际执行结果**。

### 16.8 下一步 Phase G2：一次性 Contract Migration

迁移按 Domain 顺序执行，不进行全仓机械搜索替换：

```text
A. 已实现 Formal Domain
AES -> CRC -> DMA -> UART -> Framework Communication

B. PLAN-only Domain
STIMER -> CORDIC -> WDG -> FMAC
```

每个 Domain 都先单独编译 R002 Task Context，再处理自己的公共文档。

#### 纯结构债务

如果原文测试语义已经完整，只缺统一行格式：

```text
分类 = DOC_ONLY
动作 = 只改 <ip>.md
禁止 = 改 Case / Driver / Firmware / Evidence
```

#### 语义不足

如果为了凑 6～8 条必须“猜一个步骤”或“把一句话拆成无意义两句”，则不能做机械迁移：

```text
停止格式修复
-> 回到 R140 Human Review
-> 对照真实 Case / Source / Oracle
-> 重建真实 6～8 步逻辑
```

对于 PLAN-only IP，如果现有 PLAN 本身无法支持 Implementation Ready，必须按 `ip-package / analysis` 重新审核；不得为了让 Checker 绿而编造未来实现行为。

### 16.9 下一步 Phase G3：已完成 Formal Domain 的增量 revalidation

AES / CRC / DMA / UART 不默认重新做硬件动作，只重新判断规则升级实际影响：

```text
DOC_ONLY
-> 只修文档

RECORD_ONLY
-> 仅当 re-review 发现已有决定性事实未进入 Canonical Evidence 时补记录

CASE_CHANGE
-> 只有新 Human Review 证明旧行为本身不能支撑 Feature 时才允许提出
-> 必须单独人工确认

SEMANTIC / ARCHITECTURE GAP
-> 停止当前 Domain
-> 按 R002 扩围
```

禁止因为新格式规则发布就批量触碰已经闭合的 Case 行为。

每个历史 Closure Review 不覆盖原记录；如 revalidation 产生实质变化，新增一个简洁 addendum / current-baseline review，明确：

```text
historical validated SHA
current rule baseline SHA
changed Contract only / Evidence / Case behavior
new software gate state
HIL unchanged or newly executed
```

### 16.10 下一步 Phase G4：恢复 Framework Communication

只有它自己的公共 Contract 完成当前 R120/R140 Human Review Freeze 后，才进入实现层。

恢复时优先核对目前已观察到的真实问题：

1. 把当前 3 条聚合 Steps 重写成真实可复原的 6～8 条通信事务流程；
2. 明确 small/medium/large deterministic payload、20 rounds、Expected/Actual 和完成条件；
3. 区分通信域的 Measurement 与 Device/Transport Observation，不机械伪造“寄存器 Evidence”；
4. `expected_transactions / transactions / error_count / retry_count / throughput / latency` 的 Canonical 身份和报告用途重新核对；
5. ECHO mismatch 的决定性 Evidence 必须在 Assert 前保留下来；
6. F002 只证明“bounded retry observability”时，不得在没有 fault injection 的情况下升级为“retry mechanism fault validation”；
7. F003 没有规范 throughput/latency threshold 时，只能报告测量值和完成稳定性，不能声称满足不存在的性能指标；
8. `ET_CASE_REPORT` 必须覆盖真正支撑 F001/F002/F003 的 1～4 个关键字段，不能只展示容易取得的 totals。

完成 Human Review 后再正式分类：

```text
CLOSED / DOC_ONLY / RECORD_ONLY / CASE_CHANGE / SEMANTIC-ARCHITECTURE GAP
```

当前只读分析提示存在 DOC_ONLY / RECORD_ONLY 候选，但在正式 Task Context + 当前 Contract Freeze 前不把它们写成最终数量。

### 16.11 一次性迁移完成 Gate

只有同时满足以下条件，才算本次规则基线迁移完成：

```text
R120 / R140 / rule_owner_catalog 一致
新 Checker Regression PASS
validate_case_method_contract.py repo-wide 0 violation
所有公共 SPEC / PLAN method.* 使用唯一 <摘要>：<正文> 语法
所有 method.steps 为 6～8 条真实动作
每个 Domain 的 R140 Human Review 语义结论有明确状态
历史 Closure 与 current-baseline revalidation 状态已分离
repository-wide software gate 按实际结果记录
CI 按 exact head_sha 记录
不伪造 HIL
```

如果 repo-wide `validate_pc.py` 仍被其他非本次 Contract 责任域债务阻塞，可以继续记录 scoped PASS / repository-wide FAIL 的双状态，但不得把新 method checker 自身的 violation 当成“无关债务”跳过。

### 16.12 本次治理修复后的长期约束

后续任何新 IP / 新 PLAN / 新 SPEC 都不再允许依赖“Reviewer 自己看得懂就行”的自由格式。

固定闭环变成：

```text
R140 定义测试语义应该多具体
-> R120 冻结机器可判定的统一表达结构
-> validate_case_method_contract.py 失败关闭格式漂移
-> validate_pc.py 纳入仓库软件 Gate
-> Reviewer 继续对机器无法判断的语义质量负责
```

这样才能避免再次出现：

```text
规则文字写了 6～8 步
但文档只有 3 步
Checker 不报错
Closure 仍被写成 CLOSED
下一个 IP 再重复人工发现
```

本次迁移的目标不是让所有 IP 文案长得一样，而是让**所有 IP 使用同一个可审核结构，同时保留各自真实的测试语义、硬件/通信 Endpoint 和 Oracle。**
