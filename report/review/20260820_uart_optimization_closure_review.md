# UART Optimization Closure Review — 2026-08-20

> Status: **SOFTWARE / CONTRACT / EVIDENCE / CHIP MAPPING / REPORT SCOPED CLOSURE — CLOSED**  
> Branch: `review_code`  
> Human Review baseline: `c217e7d6a21f171329f5bfcab6ca5379754fc1de`  
> Human Review freeze commit: `3a8cd0a046764f57cd76beddbd38e88733e4cbd4`  
> Validated temporary carrier source: `cbd841178216b3ab92e6df698c51125f343cce67`  
> Clean official UART implementation commit: `377a79574aefdf5179a39f3fad64855c1dae2bb7`  
> FPGA HIL: **NOT_EXECUTED / NOT_VERIFIED**  
> Silicon HIL: **NOT_EXECUTED / NOT_VERIFIED**

本记录是 UART 本轮优化的最终 Closure 事实记录，不是新的活动规则。规则权威仍为 `AGENTS.md` 与当前 active Rxxx 文档。本记录只说明当前 33 个已实现 Formal SPEC 在软件、Contract、Canonical Evidence、ET6801 Chip Mapping 与 Report/XLSX 层已经完成本轮闭环；它**不把软件验证、历史 UART 测试或芯片适配声明冒充当前 SHA 的 FPGA/Silicon HIL PASS**。

## 1. Baseline 与审查范围

UART 本轮进入 Human Review 时的真实规模：

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

7 个未实现 Case 继续保持 `ET_CASE_PLAN`，没有为了关闭 UART 被升级成 SPEC：

```text
UART_P3_001  RS485 transfer modes
UART_P3_002  RS485 DE/RE polarity
UART_P3_003  RS485 turnaround timing
UART_P3_004  SIR normal mode
UART_P3_005  low-power SIR
UART_P3_006  absolute baudrate / bit timing
UART_P3_008  protection / register timeout recovery
```

本轮不修改 UART Public Driver、Firmware Service、Common Wrap、Wire、Capability Schema 或 SVD；已有 Driver / Service / Wrap 只作为审查和回归依赖，不借 UART Case 优化扩大公共架构变更范围。

## 2. Human Review 冻结分类

33 个 Formal SPEC 在改代码前先完成 Human Review，并冻结为：

```text
RECORD_ONLY = 28
CASE_CHANGE = 5
----------------
Total       = 33
```

只有以下 5 个 Case 获准做最小行为增强：

```text
UART_P0_001  增加组件身份 Snapshot，并纠正 F003/F043 过强绑定
UART_P1_004  RX FIFO threshold-1 / threshold 因果边界
UART_P1_005  TX FIFO threshold 的 Halt/in-flight/Resume 因果边界
UART_P1_013  Halt 窗口不前进 + 同一 pending data Resume
UART_P2_005  9-bit mismatch 的有界稳定负对照
```

其余 28 个 Formal Case 只做 Contract / Evidence / Report Closure；没有因为“更严谨”而擅自增加新的硬件测试目标。

## 3. 最终实际改动文件

正式落入 `review_code` 的 UART 实现变更严格只有 8 个文件：

```text
test_case_doc/uart/uart.md
test_case_doc/uart/ET6801_uart.md

pc/et_test_platform/test_cases/uart/test_uart_p0.py
pc/et_test_platform/test_cases/uart/test_uart_p1.py
pc/et_test_platform/test_cases/uart/test_uart_p2.py
pc/et_test_platform/test_cases/uart/test_uart_p3.py

pc/et_test_platform/framework_validation/unit/results/test_uart_contract_consistency.py
pc/et_test_platform/framework_validation/unit/results/test_uart_report_export.py
```

临时 validation workflow、trigger、`tmp_uart_*` helper、诊断日志均只存在于临时 carrier branch；它们没有进入 `review_code`。

## 4. Public Contract Closure

`uart.md` 已从旧的短步骤 / 抽象 Observation / `expected_state` 式表达重构为可人工审核的稳定 Contract：

- 49 个 Feature 保持稳定 Feature ID；
- 33 个 Formal SPEC 保持稳定 Case ID；
- 7 个未实现项继续保持 PLAN；
- 每个 Formal SPEC 使用具体 Inputs、6～8 步真实测试顺序、稳定 Observation/Measurement 语义、可核对 Pass Criteria、真实 `failure_observations` 与 `ET_CASE_REPORT`；
- Reviewer-facing label 使用可读中文，Canonical key/path 保持稳定机器身份；
- 公共 Contract 不包含 ET6801 物理地址、固定实例、IRQn 或 SDK 私有结构。

### 4.1 Feature 声明强度纠正

本轮明确保留并收窄以下边界：

- `UART_F_003` 普通/别名地址视图没有被 P0_001 Runtime Capability 查询冒充为动态 alias-access proof；
- `UART_F_043` Scratch **完整读写**已从 P0_001 Feature 绑定解绑；当前 Snapshot 只保留 Scratch 读值作为诊断事实，写证明继续保持 `scratch_write_proof_gap`；
- `UART_F_014` 独立 RX/TX FIFO reset 没有稳定公共动作/独立 Case，不由 software reset 或普通 FIFO config 替代；
- `UART_F_013` 边界数据/FIFO level 不冒充精确 physical FIFO depth Oracle；
- `UART_F_034` 当前动态覆盖 CTS/DSR，RI/DCD 继续保持 `ri_dcd_stimulus_gap`；
- `UART_F_048` 绝对 baudrate / bit timing 仍由 P3_006 PLAN 的独立时钟 Observer 负责。

## 5. Five CASE_CHANGE 最终审查

### 5.1 UART_P0_001 — Runtime Capability + Component Identity

原问题：旧 Case 只有 Runtime Capability，无法充分证明组件身份；同时 F043 Scratch read/write 绑定过强。

最终：

```text
Runtime Capability
-> initialize representative DUT
-> snapshot_get()
-> COMPONENT_PARAMETER / VERSION / PERIPHERAL_ID / SCRATCH read
-> Canonical Evidence
-> validity assertions
```

关键修正：

- `capabilities_features` 是 Wrap/Service/Capability 事实，记录为 Measurement，而不是伪装成某个 UART 寄存器 Observation；
- `component_parameter / version / peripheral_id / scratch_readback` 来自目标侧 Snapshot，保持硬件 Observation；
- F043 从本 Case 的 FeatureRef 解绑，Scratch write 继续是 Open Gap。

结论：**符合 Human Review，未扩大到 alias write 或 Scratch write。**

### 5.2 UART_P1_004 — RX FIFO Threshold

原问题：只发送恰好 threshold 的数据，无法区分真正阈值边界与其他 RX 事件。

最终每个代表阈值 `1/4/8/14`：

```text
threshold-1 negative control
-> Driver read_exact 确认数据已真实到达
-> IRQ Service session必须没有对应阈值事件
-> 重建独立基线
-> threshold positive control
-> Driver capture_wait 等待完整数据
-> IRQ Service session出现RX_READY
```

Case 不新增自由 `time.sleep()`；等待由已有 Driver/请求 Deadline 所有。负/正对照 event/fault/source 与实际数据均在决定性 Assert 前记录。

结论：**形成可区分因果边界，符合 R210 wait ownership 与 Evidence-before-Assert。**

### 5.3 UART_P1_005 — TX FIFO Threshold

原问题：旧 Case 只看一次 TX_READY，不能证明阈值边界。

最终每个 `0/2/4/8` 阈值：

```text
Halt TX
-> write_partial 装入同一短Payload
-> 读取 halted TX FIFO level，要求 > threshold
-> 使能TX_READY并读取held Service session
-> Resume，不重新提交Payload
-> Driver capture_wait 等待原数据完成
-> 读取 resumed TX FIFO level，要求 <= threshold
-> 检查TX_READY event/source + data
```

没有通过修改 sleep allowlist 或降低断言来通过 Gate。

结论：**真实证明 in-flight -> threshold crossing / terminal chain，而不是单次完成中断。**

### 5.4 UART_P1_013 — Halt / Resume

原问题：旧 Case 是 `halt -> snapshot -> resume -> 重新发送`，只能证明 Resume 后还能通信，不能证明 Halt 真正暂停同一发送。

最终：

```text
capture_start
-> Halt
-> write_partial 只提交一次Payload
-> TX FIFO必须存在待发送数据
-> 连续4次独立 capture_get（每次请求受Driver timeout约束）
-> received始终为0
-> Resume
-> 不重新write
-> 原Capture完成且数据一致
```

`paused_received`/sample count 是 Service/Measurement，TX FIFO level 与实际 Capture data 保持硬件/数据端点 Observation。

结论：**符合“同一 pending data 暂停后继续”的 Human Review 因果目标。**

### 5.5 UART_P2_005 — 9-bit Address Mismatch Filter

原问题：固定 `sleep(0.05)` 后单次 `RX_FIFO_LEVEL==0` 不能区分“未到达”和“已过滤”。

最终：

```text
matching address/data -> 正常进入RX
mismatch address/data -> bounded observation window
-> 多次读取 RX FIFO level
-> raw sample series进入Artifact
-> peak level / sample count / stable-empty作为Measurement
-> mismatch_window_stable必须成立
-> 退出9-bit并做普通模式恢复
```

没有把一组 sample list 冒充为一个原子 `UART_FIFO.RX_LEVEL` Observation；`failure_observations` 只保留最小充分证明，完整 sample list 留在 Artifact。

结论：**符合 R130 原子 Evidence 与最小充分 failure proof。**

## 6. RECORD_ONLY Evidence Closure

28 个 RECORD_ONLY Case 没有新增硬件目标，主要完成以下通用修正：

```text
hardware/service fact
-> record Measurement / Observation
-> decisive assert
-> final structured Artifact
```

重点闭合：

- DUT / Peer Capture 分来源保存；
- IRQ Service `pending/enabled/active/event_count/fault_count/source_observed` 与真实 UART register/数据 Observation 分离；
- Parity / Framing / Overrun / Break 的 `UART_STATUS.ERROR_FLAGS` 在 Assert 前保存；
- DMA Case 把 Peer data、DMA destination、DMA IRQ、Channel FREE 与软件 match/guard 分来源；
- 9-bit 实际 word/data 与 normal recovery 分开保存；
- Modem CTS/DSR raw status 与软件 coverage 描述分开；
- Shadow / Direct FIFO 的 typed readback / TFR / RFW 结果分别原子记录；
- P3_010 20轮稳定性每轮在决定性 Assert 前保存两个方向的实际 Capture，不再等全部轮次通过后才有最终现场。

## 7. Canonical Evidence / Provenance 审查

本轮最终明确执行以下边界：

```text
真实UART寄存器 / 硬件 / 数据端点 -> record_observation()
Service IRQ session / event count / runtime capability / 软件比较 -> record_property()
Peer事实 -> source=peer
DMA事实 -> DMA stable endpoint
完整多采样 / 多轮结构 -> Artifact
```

特别纠正：

- `UART_CAPABILITIES.*` 不冒充 UART 寄存器；
- `UART_ISR.PENDING_MASK / ENABLED_MASK / ACTIVE_MASK` 是 Firmware Service session/latch 事实，不冒充 `IIR/IER`；
- `event_count / fault_count / source_observed` 是 Measurement；
- Capture `received` 进度计数是 Service/Measurement；实际 Capture data 才作为数据端点 Observation；
- 软件 `data_match / identity_stable / guards_intact` 不标记成 DUT 寄存器 Observation；
- 一条 `record_observation()` 只绑定一个真实来源端点。

新增 `test_uart_contract_consistency.py` 对 Contract -> Registry -> Formal Case -> Evidence -> Report key 进行静态绑定，并新增专门 Regression 防止 Service/Measurement 再次伪装成 register Observation。

## 8. ET6801 Chip Mapping 审查

`ET6801_uart.md` 新增公共稳定 endpoint 到 ET6801 实际 Register/Field 的只读显示映射；映射已经对照现有 SDK Driver/Wrap/Service 实现重新审核。

主要映射：

```text
UART_COMPONENT.COMPONENT_PARAMETER -> CPR
UART_COMPONENT.COMPONENT_VERSION   -> UCV
UART_COMPONENT.PERIPHERAL_ID       -> CTR
UART_COMPONENT.SCRATCH             -> SCR

UART_STATUS.LINE_STATUS / ERROR    -> LSR
UART_STATUS.STATE/FIFO flags       -> USR
UART_FIFO.TX_LEVEL                 -> TFL
UART_FIFO.RX_LEVEL                 -> RFL

UART_MODEM.INPUT/DELTA/RAW         -> MSR
UART_MODEM.OUTPUT                  -> MCR

UART_SHADOW.ENABLED                -> SFE
UART_SHADOW.TX_THRESHOLD           -> STET
UART_SHADOW.RX_THRESHOLD           -> SRT

UART_FIFO_ACCESS.ENABLED           -> FAR
UART_FIFO_ACCESS.TX_VALUE          -> TFR
UART_FIFO_ACCESS.RX_VALUE          -> RFW / RX data path

UART_BUSY.PRE_TRIGGER_USR          -> USR
UART_BUSY.OBSERVED_IIR             -> IIR.IID
UART_BUSY.OBSERVED_USR             -> USR
```

明确不做寄存器映射的事实：

```text
UART_CAPABILITIES.*
UART_ISR.* Service session/latch
Service event/fault/overflow count
PEER_UART.*
DMA_CHANNEL_STATUS.*
DMA_DESTINATION_DATA
data_match / guards / transaction count
```

公共 `uart.md` / Case 继续保持芯片中立；实际寄存器名称只用于 ET6801 Chip 文档和 Report 显示增强。

## 9. Report / XLSX Closure

新增：

```text
pc/et_test_platform/framework_validation/unit/results/test_uart_report_export.py
```

它模拟：

```text
Canonical Result
-> uart.md ET_CASE_REPORT
-> ET6801 endpoint/register-name resolver
-> Reviewer-facing Remark
-> XLSX export
```

P3_009 Direct FIFO 路径要求最终 Report/XLSX 能显示 `FAR / TFR / RFW`，同时不改变 Canonical stable endpoint。

`test_uart_contract_consistency.py` 继续验证每个 `ET_CASE_REPORT` 的 Measurement/Observation/Artifact key 必须由对应 Formal Case 真实产生。

## 10. Software Validation Result

最终 validated carrier `cbd841178216b3ab92e6df698c51125f343cce67` 只有在以下 UART scoped Gate 全部成功后才被 workflow 允许提交：

```text
Python compileall                                  PASS
Ruff format/check for UART scope                  PASS
validate_case_docs.py uart.md                     PASS
validate_case_plans.py uart.md                    PASS
Public chip-neutral / IP change rules             PASS
UART scoped Formal Case implementation binding    PASS
UART Case orchestration rules                     PASS
UART PC code rules                                PASS
git diff --check                                  PASS
UART Formal Case collect-only                     PASS
UART cases regression suite                       PASS
UART Driver regression suite                      PASS
UART Firmware/Wrap contract regressions           PASS
UART Contract/Source/Report consistency           PASS
UART Report / ET6801 mapping / XLSX regression    PASS
```

Formal Case collection：

```text
P0 = 4
P1 = 17
P2 = 9
P3 = 3
--------
Stable Formal SPEC IDs = 33
```

### 10.1 Repository-wide Software Quality Gate

Repository-wide `Software Quality Gate` **不得写成 PASS**。

在只包含 UART clean deliverables 的验证 PR 上，统一 `tools/validate_pc.py` 在进入 UART 专项检查前即被既有 repository baseline Ruff-format debt 阻塞；日志点名的文件包括通用 Report、AES Case 与通用 checker，而不属于本轮 UART 8 文件。

因此当前状态必须精确写为：

```text
UART scoped software gate       = PASS
Repository-wide quality gate    = NOT GREEN / blocked by pre-existing non-UART format debt
Exact review_code repository CI = NOT_VERIFIED as a global PASS
```

本轮没有为了让仓库总 Gate 变绿而顺手格式化 AES、Report 或通用 Checker，也没有扩大 UART 变更责任域。

## 11. HIL Status

当前没有执行本轮精确 SHA 的真实 FPGA / Silicon HIL：

```text
FPGA HIL @ current UART source    = NOT_EXECUTED / NOT_VERIFIED
Silicon HIL @ current UART source = NOT_EXECUTED / NOT_VERIFIED
```

历史 UART HIL / 旧代码运行结果只能作为历史上下文，不能替代本轮 `377a7957...` 的当前硬件证明。

## 12. Open Gaps / Deferred Coverage

本轮 Closure 后仍然明确保留：

```text
7 ET_CASE_PLAN
  P3_001 RS485 transfer modes
  P3_002 RS485 DE/RE polarity
  P3_003 RS485 timing
  P3_004 normal SIR
  P3_005 low-power SIR
  P3_006 absolute baud/bit timing
  P3_008 protection/timeout recovery

Feature / proof gaps
  UART_F_003 alias-access dynamic proof
  UART_F_043 scratch_write_proof_gap
  UART_F_013 fifo_depth_dynamic_proof_gap
  UART_F_014 independent RX/TX FIFO reset proof
  UART_F_034 RI/DCD stimulus gap
  UART_F_045 CRG gate/reset recovery verification
  UART_F_048 absolute baudrate/bit timing observer proof
```

这些 Gap 是真实环境/公共 API/Observer/Bench 条件尚未满足，不是当前 33 个已实现 Formal SPEC 的软件 Closure 失败；禁止为了“UART 100%”把它们改成 PASS。

## 13. Rule Compliance Final Audit

本轮最终结果与活动规则的对应关系：

```text
R100  公共 Contract/Case 保持芯片中立；ET6801 Register事实留在Chip Mapping       PASS
R110  uart.md <-> Case <-> Evidence <-> ET_CASE_REPORT <-> Regression双向同步    PASS
R120  33 SPEC / 7 PLAN、Report字段1~4项、稳定机器绑定                            PASS
R130  Measurement/Observation/Artifact provenance与原子Evidence                   PASS
R140  Human Review先于行为修改；5 CASE_CHANGE / 28 RECORD_ONLY边界保持            PASS
R210  Case线性流程、等待所有权、Evidence-before-Assert、FAIL现场保留               PASS
R220  UART Python scope Ruff / 结构 / 可读性                                      PASS
```

独立最终审查曾实际抓到并纠正以下问题，而不是为了让第一次实现“看起来通过”而忽略：

- F043 仍被 P0_001 read-only 绑定；最终解绑；
- Runtime Capability 一度被记录为 DUT硬件 Observation；最终降为 Measurement；
- `UART_ISR.*` 一度被当成硬件寄存器 Observation；最终恢复 Service/Measurement 边界；
- P1_010 一度重复记录 Evidence；最终删除重复块；
- P2_005 一度把 sample list 绑定到单一原子 RX_LEVEL Observation；最终改成 Artifact + scalar Measurement；
- P1_004/P1_005/P1_013 一度新增 Case-owned `time.sleep()`；正式 wait-ownership regression 抓到后移除，未扩大 allowlist；
- P1_011 一度为了收窄语义修改稳定 Python 入口名；正式 Regression 抓到后恢复稳定函数名，只收窄人审 Contract；
- Report 中文 label 与 failure-observation 生命周期问题均由机器 Gate 检出并修正。

因此最终 Closure 不是第一次实现后的自我判定，而是在第二轮独立规则审查和完整 UART regression 之后形成。

## 14. Final Conclusion

当前可正式冻结：

```text
UART Stable Contract                              CLOSED
33 registered Formal SPEC                        CLOSED at scoped software layer
7 ET_CASE_PLAN                                    OPEN / PLANNED by design
Canonical Measurement / Observation              CLOSED
Evidence lifecycle / FAIL preservation           CLOSED
ET6801 stable endpoint -> register mapping        CLOSED
ET_CASE_REPORT / Remark / XLSX software path      CLOSED
Contract <-> Source <-> Report Regression         CLOSED
UART scoped software validation                   PASS
Repository-wide Software Quality Gate             NOT GREEN (pre-existing non-UART debt)
Current-SHA FPGA HIL                              NOT_EXECUTED / NOT_VERIFIED
Current-SHA Silicon HIL                           NOT_EXECUTED / NOT_VERIFIED
```

因此 UART 可以从当前 rollout 主队列中移出，进入下一 Formal Domain。后续如果补做 7 个 PLAN、F043/F013/F034 等 Gap 或当前 SHA HIL，应作为对应责任域的新任务继续，不反向改写本 Closure 的软件层事实。
