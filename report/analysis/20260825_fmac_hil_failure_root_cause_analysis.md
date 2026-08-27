# FMAC HIL 测试失败根因分析

- 时间：2026-08-25 CST
- 性质：只读分析报告（分析过程未修改任何源码、配置或硬件状态）
- 范围：FMAC IP 全量 Formal Case（PC + Firmware + 契约文档三侧对照）
- 证据基线：`artifacts/runs/fmac_full_hil_20260825_150808_580/`（session.json：49 执行，25 PASS / 24 FAIL）
- 辅助证据：
  - `artifacts/runs/fmac_probe_p1_003_20260825_150023_419/`（P1_003 单 Case 隔离探针）
  - `artifacts/runs/fmac_probe_p1_003_20260825_145945_872/`
  - `artifacts/runs/fmac_iir_diag_20260825_141810_007/`
  - `artifacts/runs/fmac_hil_p0_20260825_150737_404/` 等当日 P0 定向运行
- 运行环境：serial COM12@115200，chip=et6801，firmware=`et6801-silicon-common-v0.1`，
  bench=`pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`，
  source_revision=`7ddd82a2`，source_dirty=true

> 本轮为真实硬件 HIL 执行。PASS/FAIL 结论仅对上述运行环境有效；
> 未执行 Keil 构建、烧录或任何破坏性动作。

---

## 1. 总体结论

24 个失败执行可归并为 **5 组、3 类责任面**：

| 责任面 | 数量 | 组 |
|---|---:|---|
| 固件缺陷 / 芯片事实未闭合 | 17 | A(6) + B(2) + D(5) + E级联根因(1个刺激点) |
| Case 设计依赖未闭合芯片语义 | 7 | A组与C组的 Oracle 模型需在芯片事实闭合后修订 |
| 清理机制问题 | **0** | 无任何失败由清理不到位引起；清理仅放大了故障表现 |

**核心判断：所有失败都是确定性失败，与跨 Case 状态泄漏无关**
（判定证据见 §3）。E 组 10 个执行是同一固件挂死根因的级联，不是独立问题。
实际需要解决的独立缺陷只有 **4 个**。

---

## 2. 失败清单总表

会话执行顺序即收集顺序；`[setup]` 表示 Fixture 阶段超时（DUT 已失联）。

| # | Case[参数] | 结果 | 失败断言/异常位置 | 归属组 |
|---:|---|---|---|---|
| 1 | fmac_p1_002[wm_1] | FAIL(call) | `assert full.x1_full` False，test_fmac_p1.py:223 | A |
| 2 | fmac_p1_002[wm_2] | FAIL(call) | 同上 | A |
| 3 | fmac_p1_002[wm_4] | FAIL(call) | 同上 | A |
| 4 | fmac_p1_003[wm_1] | FAIL(call) | `after_read.y_unread_count==1`，test_fmac_p1.py:314 | A |
| 5 | fmac_p1_003[wm_2] | FAIL(call) | 同上 | A |
| 6 | fmac_p1_003[wm_4] | FAIL(call) | `written==read==4` 实际 read=2，test_fmac_p1.py:312 | A |
| 7 | fmac_p1_005 | FAIL(call) | `actual_q15==(0,0,0)` 期望 `(-8192,4096,12288)`，:608 | B |
| 8 | fmac_p1_006 | FAIL(call) | 钳位输出 `(0,0)` 期望 `(16383,-16384)`，:696 | B |
| 9 | fmac_p1_010 | FAIL(call) | `baseline_outputs[-1]==0` 应为负值，:1120 | C |
| 10 | fmac_p1_014[saturation] | FAIL(call) | 自然 Saturation 状态位未置位，:1509 | D |
| 11 | fmac_p1_014[x1_overflow] | FAIL(call) | 自然 X1 Overflow 状态位未置位，:1509 | D |
| 12 | fmac_p1_014[y_underflow] | FAIL(call) | 自然 Y Underflow 状态位未置位，:1509 | D |
| 13 | fmac_p1_015[p_error] | FAIL(call) | P=0 启动后参数错误 Raw Mask==0，:1600 | D |
| 14 | fmac_p1_015[pq_error] | FAIL(cleanup) | **执行中 DUT 失联**，cleanup 4 命令全部超时 | E根因 |
| 15 | fmac_p1_015[q_error] | FAIL(setup) | HELLO RequestTimeout（DUT 已挂死） | E级联 |
| 16 | fmac_p1_016[x1_load_error] | FAIL(setup) | 同上 | E级联 |
| 17 | fmac_p1_016[x2_load_error] | FAIL(setup) | 同上 | E级联 |
| 18 | fmac_p1_016[y_load_error] | FAIL(setup) | 同上 | E级联 |
| 19 | fmac_p2_001 | FAIL(setup) | 同上 | E级联 |
| 20 | fmac_p3_001 | FAIL(setup) | 同上 | E级联 |
| 21 | fmac_p3_002[n64] | FAIL(setup) | 同上 | E级联 |
| 22 | fmac_p3_002[n128] | FAIL(setup) | 同上 | E级联 |
| 23 | fmac_p3_002[n240] | FAIL(setup) | 同上 | E级联 |
| 24 | fmac_p3_003 | FAIL(setup) | 同上 | E级联 |

PASS 的 25 个执行：P0 全部（FIR/IIR/Clear/Active）、P1_004×2、P1_007、
P1_008、P1_009、P1_011、P1_012×11（Force 全源矩阵）、P1_013×2（自然请求 IRQ）。
这一半通过证明了 Q15 FIR/IIR 主数据通路、IRQ 控制面路由、输出后处理矩阵
和框架本身实现正确。

---

## 3. 方法论：为什么排除"跨 Case 状态泄漏 / 清理不到位"

三条独立证据：

### 3.1 隔离复现一致

`fmac_probe_p1_003_*` 只单独运行 P1_003，失败特征与全量运行完全一致：

```json
// artifacts/runs/fmac_probe_p1_003_20260825_150023_419/cases/*/artifacts/fmac_p1_003.json
watermark=1: written=4 read=4 unread_after_read=1 empty=false
watermark=2: written=4 read=4 unread_after_read=1 empty=true
watermark=4: written=4 read=2 unread_after_read=3 empty=true
```

单 Case 现场仍复现 → 排除上一 Case 遗留状态。

### 3.2 相邻 Case 对照

P1_012 十一个 IRQ 参数与 P1_013 两个参数紧挨在 D 组失败之前全部 PASS，
说明 Fixture 装配、Known Baseline 建立、case_cleanup_scope 清理链路工作正常。
若清理是系统性缺陷，P1_012/P1_013 不可能稳定通过。

### 3.3 每个 Case 开头强制重建现场

各 Case 主体第一步即 `support.resource.reset()`（整池复位）+ 完整 configure
提交（如 test_fmac_p1.py:197-199），失败均发生在重建之后的刺激/观测阶段，
时间上不可能继承前序 Case 的 IP 状态。

### 3.4 清理机制的实际"罪状"（间接）

清理不是任何失败的**原因**，但放大了故障表现：
`p1_015[pq_error]` 挂死后，细粒度 cleanup（IRQ disable → IRQ clear → stop →
clear，test_fmac_p1.py:68-78）逐条发出并逐条超时，最终把主错误包装成
`OperationCleanupError`（case_cleanup.py:30），既浪费时间又污染主错误信息。
这支持将清理收敛为「CRG 复位当前 IP + Resource 整池复位」两条命令的方向，
但属于可观测性优化，**不改变本次任何 FAIL 的归因**。
另注：DUT 死亡发生在 CPU/Framework 层（UART 不再应答），任何清理命令——
包括 CRG IP 复位——都无法挽救该场景，那是固件有界性问题。

---

## 4. 分组详细分析

### A 组：X1/Y 水位状态模型不匹配（6 个执行）

**现象**

- P1_002：LOAD_X1 装满后 `x1_spare_count==0` 但 `X1_FULL=False`；
  第 5 次 unchecked 写后 `X1_OVERFLOW` 也未置位（三个 watermark 参数一致）。
  失败时快照：`active=True, spare=0, y_unread=0, x1_full=False, y_empty=True`。
- P1_003：wm_4 时 4 项输入只读出 2 项输出；wm_1/wm_2 时全部读完后
  `Y_UNREAD_COUNT=1` 残留不为 0；Underflow 从未自然形成。

**对照的已发布事实**

芯片适配文档 `test_case_doc/fmac/ET6801_fmac.md`：

- :72 「X1 Full Watermark … Full 条件为 spare `< watermark`」
- :74 「Y Empty Watermark … Empty 条件为 unread `< watermark`」
- :118 E02 证据行提到 X1 Full 有约 3-clock 可见延迟
- :422-423 明确标注 FMAC_P1_002 / FMAC_P1_003 为 **NEEDS_VERIFICATION**，
  即水位行为从未被 HIL 证实过

硅上实测（探针运行）与文档模型矛盾：

- wm=1：读完 4 项后 unread 报告为 1（按文档模型应为 0）
- wm=4：unread=4 时仅能读出 2 项（可读性与 watermark 出现耦合）
- spare=0 且 active 时 FULL 不置位（按 "spare<watermark" 应置位）

**根因归属**

1. 主责：芯片水位/计数真实语义与 `<CHIP>_fmac.md` 记载不符
   （文档本身标注 NEEDS_VERIFICATION，属芯片事实未闭合）。
2. 次责：Case Oracle 把未验证的文档事实当作已知前提
   （如「Y 输出随时完全可读」「FULL 在装满后必然置位」）。

**修复路径**

用 Test Extension 直读 SR 原始值做定向硅实验，闭合以下问题后回写
`<CHIP>_fmac.md` 并同步修订两个 Case 的状态模型：

- X1_FULL_RPT 的真实触发条件（是否依赖功能类型 LOAD_X1/FIR？
  是否有远大于 3-clock 的可见窗口？是否与 watermark 编码相关？）
- Y_UNRD_NUM_RPT 与 watermark 的关系（残留 1 项是管线延迟还是计数口径差？）
- Y 可读性是否被 EMPTY_WM 门控（wm_4 只能读 2 项的现象）

### B 组：Float→Q15 转换路径整体失效（2 个执行）

**现象**

- P1_005：Float 输入转换后 Q15 读回 `(0,0,0)`，期望 `(-8192,4096,12288)`；
  而**同 Case 内**反方向 Q15→Float 正常（读回 `-0.25/0.125/0.375` 合理值）。
- P1_006：±2.0 钳位输出 `(0,0)`，期望 `(16383,-16384)`；Overflow 状态反而置位了
  （说明越界事件被感知，但转换结果恒零）。

**已核对的代码路径**

- Wrap 配置映射：`et_fmac_wrap.c:286-287` 把 `float_input→floatDataReadEn`、
  `float_output→floatDataWriteEn`；
- SDK 寄存器写入：`et6x_fmac.c:107-116` 映射到
  `FMAC_CR_FLOAT2FIXED_IN_SEL` / `FMAC_CR_FIXED2FLOAT_O_SEL`；
- FIFO float 访问：`et6x_fmac.c:818-839`（`FMAC_setFIFODataFloat/getFIFODataFloat`）。

形式上映射自洽，但 Float→Q15 方向端到端输出恒零。

**根因归属**：固件/硬件实现问题。候选方向（需硅实验区分）：

1. CR 使能位极性/命名交叉（FLOAT2FIXED_IN_SEL 实际控制的是输出方向？）；
2. float 写入 FIFO 前需要特定数据格式使能顺序（先写 CR 后 config？）；
3. 该硅版本 Float 输入转换功能本身有缺陷（SDK Driver 缺陷记录进
   `<CHIP>_fmac.md` 的 Driver 缺陷栏）。

注意公共契约 `fmac.md` §0.1 已声明 Float 精确语义属"目标证据闭合"范畴，
本组失败正是该缺口第一次被 HIL 暴露。

### C 组：SAT16 对负值的后处理行为（1 个执行）

**现象**

P1_010 零 Offset 基线（SAT16、Shift NONE、Offset=0）单抽头
`Q15_MAX × -0x2000` 应输出约 -0x2000，实际末项为 0。

**旁证链**

- P1_008 最终 WRAP 保留负值 `-8` 正常 → RAW/Wrap 路径负数没问题；
- P1_009 RAW/SAT12/SAT16 三模式用**正值**全 PASS → 模式编码正确；
- 即唯一未被正向验证过的组合是「负数经过 SAT12/SAT16 饱和模式」，
  而它恰好表现为输出被钳到 0。

**根因归属**

疑似 DAT_OUT_SEL 饱和模式对负数的处理与 PC 独立模型不符
（可能是硬件把饱和模式输出按无符号幅度处理，或 Offset 高位扩展语义影响）。
Case SPEC 自身已登记缺口 `gap: [output_offset_full_domain_semantics_gap]`，
属于已知未闭合域，非 Case 书写错误。

**修复路径**：定向实验确认 SAT12/SAT16 负值行为 → 回写芯片文档 →
关闭 gap → 修订 Expected 模型。

### D 组：自然错误条件不产生 SR 错误位 / IRQ Raw（5 个执行）

**现象**

- P1_014：人为制造 X1 Spare=0 后 unchecked 写、Y Unread=0 后 unchecked 读、
  16×0x7FFF 远越界累加后，对应的 `STATUS.X1_OVERFLOW/Y_UNDERFLOW/
  ACCUMULATOR_SATURATION` 均为 False（A 组同时显示这些状态位在其他场景也不置位）。
- P1_015[p_error]：经 raw 通道以 P=0 启动 FIR 后，IRQ_RAW 参数错误三位 Mask==0。

**决定性对照**

| 路径 | 结果 |
|---|---|
| Force 强制 11 个 IRQ Source（P1_012） | 11/11 PASS，Raw/Status/Latch/delivery 全对 |
| 自然请求条件 X1 写请求/Y 读请求（P1_013） | 2/2 PASS |
| 自然**错误**条件（P1_014/P1_015） | 全部失败 |

结论：IRQ 控制面与投递链是通的；坏的只是「真实错误条件 → 错误标志/Raw」
这一段因果链。结合 A 组（Overflow/Full 标志同样不置位），指向同一上游原因：
**错误/流控状态位的产生条件与平台理解不符**，而非 IRQ 子系统问题。

**根因归属**：固件/芯片。候选方向：

1. 错误标志要求特定 CR 使能位或功能上下文才锁存；
2. Wrap/Service 刺激方式未真正到达硬件错误检测点
   （如 unchecked 通道绕过了硬件判定的前置条件）；
3. 该硅错误标志行为与 SVD/文档描述不一致（芯片事实缺口）。

### E 组：固件挂死及级联（10 个执行 + 1 个根因点）

**时间线**

```text
p1_015[p_error]  FAIL(call)：Raw Mask==0（通信尚正常）
p1_015[pq_error] FAIL(cleanup)：以 P=4,Q=5（P+Q 超 X2 容量 8 共 1 项）启动 IIR 后
                 DUT 失联；cleanup 四条命令（IRQ disable/clear、stop、clear）
                 全部 RequestTimeout → OperationCleanupError
p1_015[q_error]  起 10 个执行全部 FAIL(setup)：HELLO(service=0x0000 command=0x0001)
                 两次尝试超时 —— CPU/Framework 层已死
```

**根因归属**：固件有界性缺陷。以非法 P+Q 组合启动 IIR 触发固件挂死
（硬 fault 或服务处理死循环），违反 R400「Firmware 单动作有界终止」约束。
清理机制无法自救——死亡在 CPU 层，UART 已不应答。

**连带影响**：p1_015[q_error]、p1_016×3、p2_001、p3_001、p3_002×3、p3_003
共 10 个执行的失败均为陪葬，**不代表这些 Case 本身有问题**，固件修复后直接重测。

---

## 5. 责任面汇总矩阵

| Case 组 | Case 设计问题 | 清理问题 | 固件/芯片问题 | 文档契约问题 |
|---|---|---|---|---|
| A（p1_002/p1_003） | 次责：Oracle 依赖未闭合事实 | 无 | 主责：水位/计数语义 | 主责：NEEDS_VERIFICATION 未闭合 |
| B（p1_005/p1_006） | 无 | 无 | 主责：Float→Q15 路径 | 缺口已登记 |
| C（p1_010） | 次责：同 A | 无 | 主责：SAT16 负值行为 | gap 已登记待闭合 |
| D（p1_014/p1_015[p_error]） | 无 | 无 | 主责：错误标志因果链 | — |
| E（pq_error 及 10 个级联） | 无 | 无（且无法自救） | 主责：有界性缺失致挂死 | — |

---

## 6. 修复优先级建议

```text
P0  固件挂死：IIR 非法 P+Q 启动的有界性（含 Service/Wrap 错误路径审计）
    → 解锁 E 组 10 个级联执行的重测
P1  Float→Q15 转换路径（CR 使能位极性 / FIFO float 时序 / 硅缺陷定性）
    → 解锁 B 组 2 个
P2  自然错误条件 → SR 错误位 / IRQ Raw 因果链（与 A 组水位问题合并做硅实验）
    → 解锁 D 组 4 个
P3  水位/计数硅行为闭合 → 回写 <CHIP>_fmac.md → 修订 A 组 Case 状态模型
    → 解锁 A 组 6 个
P4  SAT12/SAT16 负值行为闭合 → 关闭 output_offset gap → 修订 C 组 Oracle
    → 解锁 C 组 1 个
```

配套工程改进（非阻塞）：

- 将各 Case 细粒度 `_cleanup_actions` 收敛为「CRG 复位当前 IP +
  Resource 整池复位」两条命令（需先给 `CrgPeripheral` 补 FMAC 成员并确认
  ET6801 CRG 复位线覆盖，再按 R110 同步 fmac.md §0.5 Cleanup 行与
  各 ET_CASE_SPEC 的 cleanup 字段）；主要收益是挂死场景下不再产生
  逐条超时的 `OperationCleanupError` 噪声。

## 7. 未执行项声明（NOT_EXECUTED）

- 未执行任何固件修改、构建、烧录；
- 未执行任何 PC 代码修改；
- 未连接或操作外部仪器；
- 未重跑任何测试验证修复假设（所有结论基于 2026-08-25 当日既有运行证据）;
- Quick Doctor 报告的 Git 指纹过期未刷新（避免写入生成状态）。

## 8. 证据索引

```text
artifacts/runs/fmac_full_hil_20260825_150808_580/session.json          # 总会话与选择集
artifacts/runs/fmac_full_hil_20260825_150808_580/cases/*/result.json   # 逐Case canonical结果
artifacts/runs/fmac_probe_p1_003_20260825_150023_419/                  # P1_003隔离复现
artifacts/runs/fmac_iir_diag_20260825_141810_007/                      # IIR诊断
pc/et_test_platform/test_cases/fmac/test_fmac_p1.py                    # 失败断言所在Case源码
pc/et_test_platform/test_cases/fmac/_support.py                        # Golden参考算法
pc/et_test_platform/drivers/fmac/                                      # PC Driver五件套
firmware/wrap/src/et_fmac_wrap.c                                       # 公共Wrap
firmware/services/src/et_fmac_service.c                                # Service
firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_fmac.c                  # 芯片Driver/Test Extension
test_case_doc/fmac/fmac.md                                             # 公共IP契约（24个ET_CASE_SPEC）
test_case_doc/fmac/ET6801_fmac.md                                      # 芯片适配事实（NEEDS_VERIFICATION标记）
```
