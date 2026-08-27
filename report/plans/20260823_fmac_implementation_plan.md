# ET6801 FMAC 实施计划

> 本计划记录 FMAC 从分析冻结进入自动化测试实现阶段的当前基线、已完成工作、剩余 Gap、实施顺序与 Codex 执行边界。
> 本文是实施计划，不是现行规则正文。所有实际开发仍必须从 `AGENTS.md -> Task Context -> Rxxx` 进入；发生冲突时以仓库规则和 `test_case_doc/fmac/` 冻结契约为准。

## 1. 当前基线

- 仓库：`Abba-shenfu/Automated_Testing_Platform`
- 工作分支：`review_code`
- FMAC 分析冻结基线：`ffea2f13d27d4afcd6887b9f92430f7794d4afbe`
- 公共契约：`test_case_doc/fmac/fmac.md`
- ET6801 芯片适配契约：`test_case_doc/fmac/ET6801_fmac.md`
- 实际测试目标：**ET6801**
- ET3101 / ET6003 / ET60157：仅 Family / Historical Reference，不得单独证明 ET6801 当前 Hardware Truth。

当前阶段结论：

```text
FMAC Analysis / Contract        COMPLETE
ET6801 Hardware Truth           COMPLETE WITH EXPLICIT GAPS
Feature Catalog                 51 FEATURES, FROZEN
Formal Case Plan                24 ET_CASE_PLAN, FROZEN
Feature Mapping                 COMPLETE
Case Adaptation                 COMPLETE
Source / Claim Traceability     COMPLETE
Implementation Classification  COMPLETE

ET6801 FMAC Chip Driver         NOT CLOSED, D01-D09
Common Wrap                     NOT IMPLEMENTED
Firmware Service                NOT IMPLEMENTED
PC Driver                       NOT IMPLEMENTED
Formal Case                     NOT IMPLEMENTED
DMA Execution Mapping           PARTIAL / GAP
Target Cycle Observer           GAP
Keil / FPGA / Silicon Formal    NOT_EXECUTED / NOT_VERIFIED
```

## 2. 已完成工作总结

### 2.1 资料与 Hardware Truth

已完成 ET6801 FMAC 的完整重新分析，并明确 ET6801 为唯一目标芯片。

已完成：

- 17 个登记 Source Root 的 FMAC 定向检索；
- ET3101 / ET6003 历史 39 个 Requirement / Test Point 的逐项处置；
- ET6801 merged SVD、FMAC SVD、current SDK Driver、历史 Unit / Functional / FPGA / Performance 代码、历史日志的交叉核对；
- Source Coverage、Source Item Trace、Claim Ledger、Claim Evidence Locator；
- Hardware Truth / Current Driver Fact / Historical Evidence / Family Reference 的权威边界拆分；
- 所有无法由 ET6801 直接证据闭合的语义保留为 `UNKNOWN / CONFLICT / MAPPING_GAP / IMPLEMENTATION_GAP`，没有用历史代码或前代芯片强行补齐。

### 2.2 公共 Feature

公共 FMAC Contract 已冻结为 **51 个原子 Hardware Feature**，覆盖：

- X1 / X2 / Y Layout；
- X1 Full Watermark / Spare Count / Full / Load / Overflow；
- Y Empty Watermark / Unread Count / Empty / Load / Underflow；
- X2 coefficient load；
- Q15 FIR；
- Q15 IIR Direct Form 1；
- Q15 data format；
- streaming continuity；
- Clear；
- Float input / output / clamp / overflow；
- internal Clip；
- final Saturate / Wrap；
- Output Mode / Offset / Shift；
- accumulator saturation status；
- DMA input / output request；
- 11 个 IRQ Source；
- IRQ Enable / Mask / Clear / Raw / Status / Force / Delivery；
- function Enable / Disable。

从 Freeze 开始，Feature ID 不得静默改义或重新编号。新硬件语义必须按 R100 评审新增或迁移。

### 2.3 Formal Case 设计

已冻结 **24 个 `ET_CASE_PLAN`**。

每个 Case 已完成：

- Inputs；
- 6～8 个测试步骤；
- 最小充分 Hardware Observation；
- 独立 Oracle / Expected；
- Pass Criteria；
- Timeout；
- Cleanup；
- Resource；
- Evidence；
- Gap；
- ET6801 Case Adaptation。

公共 Stable Automation Contract 已补齐：

- `capabilities_get`
- `baseline_apply`
- `configure`
- `x1_preload`
- `coefficients_load`
- `y_preload`
- `data_write_one_unchecked`
- `data_read_one_unchecked`
- `start / stop`
- `clear`
- `stream_write / stream_read`
- `process`
- `status_get`
- IRQ control / snapshot
- `dma_request_set`
- `timed_process`

### 2.4 Known Baseline 与 Evidence 边界

已经明确：

- `CLEAR` 只负责动态状态，不等价于恢复所有准静态配置；
- 每个 Case 第一处 Hardware Mutation 前必须建立 Known Baseline；
- Case 不允许依赖上一 Case 遗留的 Float / Output / Offset / Shift / Clip / DMA / IRQ 配置；
- `irq_delivery_count` 是 Measurement，不是 DUT Observation；
- digest / count / index 等派生值不得冒充硬件 Observation；
- PASS 与 FAIL 必须保留同一组关键硬件事实；
- 长流失败必须保存真实失败 Chunk，而不是只保存 digest。

### 2.5 已识别 ET6801 Current Driver Gap

当前已识别 D01～D09：

| ID | Gap / Conflict | 后续处理 |
|---|---|---|
| D01 | `FMAC_config()` 存在 PARAM P/Q/R 写入逻辑冲突/错误风险 | 修 current Driver 根因并做回归 |
| D02 | `FMAC_forceInterrupt()` 当前实现不符合 ET6801 Force 语义 | 修正式 Driver 或隔离 Test Driver Extension |
| D03 | IRQ bit5/6/7 Driver 命名为 P/Q/R，Hardware Truth 为 P/PQ/Q | 按 ET6801 硬件统一 |
| D04 | `FMAC_getStatus()` 未完整暴露 Float->Q15 Overflow | 增加稳定 Driver 状态能力 |
| D05 | `FMAC_OutputDataShift` 含 RIGHT_SHIFT_8(value=16)，硬件 SH 仅 0..15 | 移除/隔离非法公开编码，保持兼容边界 |
| D06 | 缺满足公共 `stop` Contract 的稳定 API | 新增明确、可有界停止能力 |
| D07 | DMA Request Gate 混在完整 config 中，缺 idle-only 原子接口 | 新增独立 Gate 动作 |
| D08 | X1 Full 上报存在约 3 FMAC clock 可见延迟，current load 流控存在 WM=1 风险 | 修 Driver 流控模型，禁止固定 sleep 作为唯一判据 |
| D09 | 缺 X1/X2/Y 配置硬件读回 API，无法支撑 CONFIG.* Observation | 优先在 Chip Driver 增加隔离 Test Driver Extension；Wrap/Service/Case 禁止直接读寄存器 |

## 3. 尚未闭合的核心 Gap

以下 Gap 在获得新的 ET6801 目标证据之前不得由 Codex 自行猜测：

- `fir_output_alignment_gap`
- `iir_math_semantics_gap`
- `iir_output_alignment_gap`
- `arithmetic_quantization_policy_gap`
- `param_r_semantics`
- `output_offset_full_domain_semantics_gap`
- `parameter_error_trigger_semantics_gap`
- `load_error_trigger_semantics_gap`
- `dma_execution_mapping_gap`
- `timing_observer_gap`

重点约束：

1. 历史 FIR `SW[i-1]` 只能作为“存在对齐问题”的证据，不能直接冻结为 ET6801 硬件真值；
2. 历史 `fmac_ut.log` 的 ±1 LSB 差异说明通用 CMSIS Q15 不是 bit-exact Oracle，不能用全局 tolerance 掩盖；
3. 历史 IIR lattice Oracle 不能替代 ET6801 Direct Form 1 的目标数学定义；
4. P/PQ/Q 和 X1/X2/Y Load Error 的 Source 身份已明确，但自然触发最小条件未闭合；
5. DMA Request 已明确，不代表 DMA controller/interface/channel Execution Mapping 已闭合。

## 4. Case 实现分流

### 4.1 Group A：当前可以进入实现

共 15 个 Case：

- `FMAC_P0_003` Clear 与重入
- `FMAC_P0_004` Enable / Disable 与 ACTIVE
- `FMAC_P1_001` X1/X2/Y Layout
- `FMAC_P1_002` X1 Watermark / Spare / Full / Overflow
- `FMAC_P1_003` Y Watermark / Unread / Empty / Underflow
- `FMAC_P1_005` Float 输入输出正常转换
- `FMAC_P1_006` Float->Q15 Clamp / Overflow
- `FMAC_P1_007` Internal Clip / Saturation Status
- `FMAC_P1_008` Final Saturate / Wrap
- `FMAC_P1_009` Output Mode
- `FMAC_P1_010` Offset / Negative-after-offset
- `FMAC_P1_011` Shift 16 个合法编码
- `FMAC_P1_012` IRQ Control / Force / Delivery
- `FMAC_P1_013` Natural Request IRQ
- `FMAC_P1_014` Natural Saturation / X1 Overflow / Y Underflow IRQ

说明：Group A 表示 Hardware / Case 语义已经足够进入实现，不代表当前软件实现已存在，也不代表可直接声明 HIL PASS。

### 4.2 Group B：必须先取得 RTL / Design Evidence

- `FMAC_P0_001`：FIR first-valid-output / alignment
- `FMAC_P0_002`：IIR feedback sign、Y state ordering、bit-exact quantization、first-valid index
- `FMAC_P1_004`：Streaming 依赖 FIR alignment
- `FMAC_P1_015`：P/PQ/Q 自然错误最小触发条件
- `FMAC_P1_016`：X1/X2/Y Load Error 自然触发条件
- `FMAC_P3_001`：Long Stream 依赖 FIR alignment

### 4.3 Group C：DMA Mapping Blocked

- `FMAC_P2_001`
- `FMAC_P3_003`

需要补：

- FMAC input DMA controller/interface/channel mapping；
- FMAC output DMA controller/interface/channel mapping；
- resolver / Execution Mapping 可验证入口。

`P3_003` 还同时依赖 Target Cycle Observer。

### 4.4 Group D：Timing Observer Blocked

- `FMAC_P3_002`

需要稳定目标侧周期 Observer；不得使用 PC wall-clock 或历史 magic correction 替代。

## 5. 实施总顺序

后续 Codex 不得一次跨越全部责任层。固定按下面阶段执行：

```text
Phase 0  Task Context / Scope
    ↓
Phase 1  ET6801 FMAC Chip Driver D01-D09
    ↓
Phase 2  FMAC Common Wrap
    ↓
Phase 3  FMAC Firmware Service + IRQ
    ↓
Phase 4  PC FMAC Driver / Codec / Models
    ↓
Phase 5  ET6801 Capability / Execution Mapping
    ↓
Phase 6  Group A Formal Cases
    ↓
Phase 7  RTL / Design Gap Closure
    ↓
Phase 8  DMA / Performance Cases
    ↓
Phase 9  Build / FPGA / Silicon / Closure
```

## 6. Phase 0：Task Context 与工作范围

任何代码、配置、规则、工具或持久文档修改前，必须遵循 `AGENTS.md` 和 R002。

新的非平凡任务或责任扩围必须重新编译 Task Context。

每个 Phase 开始前：

1. 确认 branch / HEAD / worktree；
2. 编译对应 Task Context；
3. 运行 Context check；
4. 阅读 Context 路由的 must_read / rule_owners；
5. 确认 allowed / protected scopes；
6. 只读目标代码和相邻责任链；
7. 第一次写入前确认 Scope 合法。

开发完成、专项验证前必须执行 scope-check。

## 7. Phase 1：ET6801 FMAC Chip Driver

Task Context：

```text
module = ip-package
change = chip-driver
ip = fmac
chip = et6801
```

目标：关闭 D01～D09。

主要文件：

```text
firmware/chips/et6801/sdk/**/Inc/*fmac*
firmware/chips/et6801/sdk/**/Src/*fmac*
```

原则：

- 修根因，不在 Wrap / Service / Case 绕过 Driver；
- 官方 Driver 缺确实需要的测试能力时，按 R310 增加隔离 `FMAC_test...` Test Driver Extension；
- Extension 只补目标硬件已有且冻结 Case 真正需要的原子能力；
- 不把完整测试流程塞入 Driver；
- 不在这一 Phase 修改 PC Case、Service、Wrap 或公共 Framework；
- 新 API 必须有最小 Driver / Firmware Contract 回归；
- D08 必须使用有界状态模型处理 Full 可见延迟，不得依赖 magic sleep。

Phase 1 完成条件：

- D01～D09 每项有代码处置或明确 remaining blocker；
- scoped validation PASS；
- firmware architecture rules PASS；
- `python tools/validate_pc.py` PASS；
- `git diff --check` PASS；
- exact-SHA CI 可验证后才声明 CI PASS。

## 8. Phase 2：FMAC Common Wrap

Task Context：

```text
module = ip-package
change = wrap
ip = fmac
chip = et6801
```

目标：实现 `fmac.md` 稳定原子动作的 Firmware Wrap 层。

文件目标：

```text
firmware/wrap/include/et_fmac_wrap.h
firmware/wrap/src/et_fmac_wrap.c
firmware/chips/et6801/config/et_chip_wrap_config.h   # 仅确有静态芯片映射需求时
```

强制边界：

- Wrap 只能调用 Own FMAC Chip Driver；
- Wrap 禁止直接访问寄存器；
- 公共头文件禁止暴露 ET6801 SDK 类型；
- 不推断默认参数；
- 不保存 Case 状态或最终 PASS/FAIL；
- 一个 API 对应一个清晰的本 IP 原子能力或不可再分的单 IP 动作。

## 9. Phase 3：FMAC Firmware Service + IRQ

Task Context：

```text
module = ip-package
change = service
ip = fmac
```

目标：建立 PC 命令到 FMAC Wrap 的薄执行层。

目标文件：

```text
firmware/services/include/et_fmac_service.h
firmware/services/src/et_fmac_service.c
```

至少覆盖：

- configure / baseline 所需原子命令；
- X1 / X2 / Y load；
- start / stop / clear；
- stream write / read；
- status / config snapshot；
- IRQ enable / disable / mask / unmask / clear / force / snapshot；
- DMA request gate；
- bounded asynchronous state when required。

IRQ 链路必须遵循 R320：

```text
Hardware Event
  -> IRQ Manager
  -> FMAC Service callback
  -> Own FMAC Wrap read/clear
  -> fixed snapshot / event_count / fault
  -> PC result query
```

`event_count / irq_delivery_count` 是 Measurement；Raw / Status / hardware endpoint 才是硬件 Observation。

如果需要修改公共 Service Registry，必须另起：

```text
module = firmware-platform
change = service-registry
```

不得把公共 Registry 变化混入 FMAC Service Commit。

## 10. Phase 4：PC FMAC Driver

Task Context：

```text
module = ip-package
change = driver
ip = fmac
```

推荐结构：

```text
pc/et_test_platform/drivers/fmac/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

原则：

- R200 固定依赖：`Case -> FMAC Driver -> TargetClient -> Transport`；
- Codec 只做纯 Wire 编解码；
- Driver 隐藏 Wire、Payload、Deadline、Polling、Target Error；
- Driver 不隐藏完整测试业务流程；
- Driver 负责本 IP 单动作有界等待和单 IP cleanup；
- Case 不得调用裸 TargetClient / Codec / Transport。

## 11. Phase 5：ET6801 Capability / Mapping

Task Context：

```text
module = ip-package
change = capability
ip = fmac
chip = et6801
```

目标：只发布 Formal Case 真正需要、且有 Evidence 的机器能力事实。

至少评审：

- data formats；
- filter kinds；
- Buffer / Watermark legal options；
- Output Mode / Shift options；
- IRQ sources；
- alignment fact（只有目标证据闭合后）；
- DMA request facts；
- Execution Mapping（有证据才发布）；
- Target cycle observer（有稳定实现才发布）。

不得：

- 把寄存器清单直接搬进 Capability；
- 把 Case 名或 Case 覆盖率写进 Capability；
- 用人工猜测补 generator / profile 缺失语义；
- 在 Evidence 不足时把 Gap 伪装成 capability support。

## 12. Phase 6：Group A Formal Cases

Task Context：

```text
module = ip-package
change = case
ip = fmac
```

只实现当前 Group A 的 15 个 Case。

每个 Case 必须：

1. 从对应 `ET_CASE_PLAN` 原样继承 Feature、步骤和判断语义；
2. 代码阅读顺序尽量保持：输入 -> 配置 -> 激励 -> 等待 -> Observation -> Expected -> Assert -> Evidence/Cleanup；
3. R140 已审核的关键步骤必须在 Case 主体中可见；
4. Helper 只做纯数据生成、纯转换、无 I/O 比较；
5. Fixture 只做 Capability / Bench / Driver 构造和连接生命周期；
6. 第一次 Feature Mutation 必须在 Case 主体可见；
7. Observation 必须通过稳定 Driver / Service 取得，不得直接读寄存器；
8. PASS / FAIL 记录同一组关键 Evidence；
9. 正常、失败、超时均有可靠 Cleanup；
10. 只有实际代码、注册和文档同步完成后，才允许将对应 PLAN 升级为 SPEC。

Blocked Case 不得提前升级成 SPEC。

## 13. Phase 7：RTL / Design Gap Closure

只有取得新的 ET6801 Target Direct Evidence 后，才允许逐项解除：

- FIR first-valid output；
- IIR Direct Form 1 feedback sign / state layout / quantization / alignment；
- general Q15 quantization；
- PARAM.R semantics；
- Offset full-domain signed semantics；
- P/PQ/Q natural trigger；
- X1/X2/Y Load Error natural trigger。

Gap 关闭流程：

```text
New ET6801 Evidence
-> 更新 Claim Ledger / Evidence Locator
-> 评审 Public Contract 是否变化
-> 更新 Chip Adaptation
-> 更新 Capability（如适用）
-> 再进入 Case Implementation
```

禁止 Codex 通过历史 ET3101 / ET6003、旧日志或 SDK 行为自行关闭这些 Gap。

## 14. Phase 8：DMA / Performance

顺序：

1. 先关闭 `dma_execution_mapping_gap`；
2. 实现 `FMAC_P2_001`；
3. 再提供稳定 `TARGET_CYCLE_COUNT` Observer；
4. 实现 `FMAC_P3_002`；
5. 在 DMA Mapping + Cycle Observer + FIR alignment 全部闭合后实现 `FMAC_P3_003`。

Performance 规则：

- 功能错误样本不得进入性能统计；
- 保存原始目标周期；
- `cycles_per_element` 只作为派生 Measurement；
- 不硬编码没有规格依据的性能阈值；
- 不使用 PC wall-clock / 历史 magic correction 代替 target cycle observer。

## 15. Phase 9：Build / HIL / Closure

软件层完成后，执行：

```text
Task Scope / Software Validation
-> Keil Build
-> FPGA Formal Case
-> Silicon Formal Case
-> Canonical Result
-> Report / HIL Closure
```

所有未实际执行项目必须保持：

```text
NOT_EXECUTED / NOT_VERIFIED
```

历史 ET6801 测试和日志只作为参考 Evidence，不能升级为当前 SHA PASS。

## 16. 每个 Phase 的统一 Codex 工作流

每个 Phase 必须独立执行：

```text
1. 确认 review_code / HEAD / worktree
2. 编译对应 Task Context
3. Task Context check
4. 阅读 must_read + rule owners
5. 实施单一责任变化
6. scope-check
7. 最小专项验证
8. python tools/validate_pc.py
9. git diff --check
10. git status --short
11. 单一逻辑 Commit
12. push review_code
13. 查询 exact commit SHA CI
14. 只有 exact SHA Software Quality Gate = success 才允许声明 CI PASS
```

若 exact SHA 没有 CI 结果：

```text
CI = NOT_VERIFIED
```

不得把 branch 其他 SHA 的成功结果替代当前提交。

## 17. 给 Codex 的当前起始任务

下一次 Codex 会话从 **Phase 1：ET6801 FMAC Chip Driver D01～D09** 开始。

任务意图：

```text
Close ET6801 FMAC chip-driver gaps required by the frozen FMAC contract without changing public Feature/Case semantics.
```

在实际写 Driver 代码之前，必须先编译：

```text
module = ip-package
change = chip-driver
ip = fmac
chip = et6801
```

Codex 在 Phase 1 不得顺手实现：

- FMAC Wrap；
- FMAC Service；
- PC Driver；
- Formal Case；
- DMA Mapping；
- 公共 Framework；
- 其他 IP；
- 被 RTL / Design Gap 阻塞的语义。

如果实现过程中发现 frozen Contract 与新的 ET6801 直接证据冲突，立即停止代码扩展，先返回 `test_case_doc/fmac/` 做 Contract Review；禁止在代码里静默适配。

## 18. 当前计划停止点

本计划建立后，FMAC 工作从“分析设计”正式进入“分阶段实现”。

当前允许的下一动作只有：

**Phase 1：ET6801 FMAC Chip Driver D01～D09。**

完成 Phase 1 并通过 scope / software / exact-SHA CI 门禁后，再创建新的 Task Context 进入 Phase 2。
