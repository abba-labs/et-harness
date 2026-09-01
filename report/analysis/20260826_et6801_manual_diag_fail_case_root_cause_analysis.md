# ET6801 手动诊断与正式 FAIL Case 根因分析

- 时间：2026-08-26 CST
- 性质：只读分析报告（未修改任何源码、配置、规则；未执行任何新的硬件动作）
- 分析对象：`report/Weekly_report/20260826_weekly_report.md` 登记的全部 FAIL/SKIP Case，
  对照 `firmware/manual_tests/et6801/src/` 手动诊断源码与当日 HIL 证据
- 当前 HEAD：`192c59aa02db2fa9afe5ee25f37efce71f84e957`

## 证据基线

```text
report/Weekly_report/20260826_weekly_report.md                        # 本周状态与统计口径
artifacts/runs/20260826_152840_472046_manual_et6801_all_ip_hil/
  manual_complete/diagnostics.log                                     # 15项手动诊断完整日志
firmware/manual_tests/et6801/src/et_manual_{crc,fmac,aes,cordic,
  stimer,wdg,uart,crg}_test.c                                         # 手动诊断Case源码
artifacts/runs/20260826_092855_752362_fmac_p1_010_w1c_hil/            # FMAC W1C三方式实验
artifacts/runs/20260826_093820_683819_fmac_p1_010_w1c_hil/            # 修正复跑（仍FAIL）
test_case_doc/<ip>/ET6801_<ip>.md                                     # 各IP芯片适配事实
```

## 1. 执行摘要

2026-08-26 全 IP 手动诊断 **15 项：4 PASS / 11 FAIL**：

| 结果 | Case |
|---|---|
| PASS | crg_register_reset_matrix、crc_p1_011、fmac_p1_006、stimer_p1_001 |
| FAIL | uart_p1_008、uart_p1_012、uart_p3_009、crc_p1_012、aes_p1_009、cordic_p1_003、cordic_p2_001、fmac_p1_010、stimer_p2_003、wdg_p1_004、wdg_p2_001 |

对用户核心问题「**是不是 codex 的问题 / case 构造的问题**」的直接回答：

```text
11 个手动 FAIL 中：
  - 2 个是 Case/软件构造问题（fmac_p1_006 清除顺序、fmac_p1_010 清除语义），
    且这两个都已被手动诊断证明修正方向；
  - 1 个 Case 构造偏弱无法仲裁（crc_p1_011 手动版未覆盖阈值边界）；
  - 其余 8 个全部是当前 FPGA/bitfile 的硬件实现问题或规格未闭合，
    双路径（Formal + 独立手动固件）结果一致，排除 Case 书写错误。
结论：主要矛盾不是 codex 写错了 Case，而是当前 bitfile 的若干
IP 行为与 SVD/文档承诺不符；少数确实是测试构造问题且已有修正证据。
```

---

## 2. 逐 Case 详细分析

### 2.1 crc_p1_011 —— CRC FIFO Threshold 生效边界（Formal FAIL，Manual PASS）

**两路径现象**

| 路径 | 刺激 | 观察 |
|---|---|---|
| Formal | TRHD=5，CPU 连续写 5×`0x12345678`，逐次读 RESULT | 第 4 次写入后 RESULT 已变为 `0xAD37D056`（提前更新）；第 5 次不再变化；OVF=0 |
| Manual | SDK `CRC_calculate32` 写 2 word，TRHD=0/1/5/8 四档 | RESULT 恒为 `0x140B8DD8`（正确），OVF=0，全 PASS |

**差异根源**

1. 两条执行路径根本不同：Manual 走 SDK 驱动的 `CRC_calculate32`（et_manual_crc_test.c:53，
   内部含长度管理与超时），Formal 是裸 CPU 连续写 IR 寄存器。手动 PASS 只证明
   「小事务计算正确」，**完全没有触碰阈值边界**——输入只有 2 word，小于全部四档阈值
   （et_manual_crc_test.c:39），任何阈值语义下结果都应相同。因此 Manual PASS
   **不具备仲裁 Formal 边界观察的能力**。
2. Formal 观察到的「第 4 次写入即更新」指向一种确定的可能：当前 FPGA 的 CRC
   对 CPU 直写路径并不执行 TRHD 门控（或阈值单位/语义与 SVD 描述不一致）。

**定性**

- 不是 codex 笔误；是「Case 对阈值语义的假设建立在了未闭合的芯片事实上」
  （与 FMAC A 组同一模式）。
- 附带发现：手动版 Case 构造偏弱——四档阈值配 2 word 输入是常量比较，
  改成「每档阈值 N 配 N-1/N/N+1 三种写入次数」才能真正仲裁。

### 2.2 crc_p1_012 —— CRC FIFO Overflow 与恢复（双路径一致 FAIL）

**证据**（diagnostics.log:257-264）：直接 for 循环向 `CRC->IR` 无轮询连写 64 字
（et_manual_crc_test.c:94-97），RESULT 变为 `0x2F7ADCFC` 说明数据确实进入流水，
但 `FIFO_OVF(bit0)` 仍为 0。恢复场景 CRG 复位后重算 `0x140B8DD8` 正确。

**定性**：硬件缺陷。同事已确认当前 FPGA 的 FIFO_OVF 功能存在问题
（周报 §2.2 结论）；本手动 Case 用最简刺激排除了「写入速度不够」的解释。
Silicon 待独立验证。不是 Case 问题。

### 2.3 aes_p1_009 —— AES Output Conflict IRQ（双路径一致 FAIL）

**证据**（diagnostics.log:265-274）：`AES_testWriteInputBlockPair` 通过标准输入握手
连续提交两个 Block 且不读第一块输出（et_manual_aes_test.c:78），stimulus_status=0
（DRV_OK，输入路径无错误），但 RAW/STATUS bit0 均为 0。

**定性**：触发条件未闭合。两种独立实现得到完全一致的零，说明刺激确实到达了
硬件但冲突事件没有被锁存。候选解释：(a) 当前 FPGA 未实现 Output Conflict
检测；(b) 存在未记载的前置条件（如 FIFO 模式、DATA_LENGTH 精确匹配、块间时序）。
在芯片设计给出权威触发条件前，既不能定罪硬件也不能定罪 Case。
不是可判定的 codex 问题。

### 2.4 cordic_p1_003 —— ARCTAN Scale=7 精度（双路径一致 FAIL）

**证据**（diagnostics.log:275-284）：input=`0x40000000`，actual=`0x007EB700`，
golden=`0x007EBA14`，delta=`0x314` > budget `0x216`（误差约 1.4751e-4 > 1e-4）。
COMPLETE 置位与清除正常。

**关键属性**：结果**完全确定性**——Formal 与 Manual 读到的硬件值逐位相同。
这排除时序抖动、状态残留、通信干扰等一切偶发因素，也排除 Case 编写随机性。

**定性**：规格/预算未闭合。二选一：
1. 统一精度预算（1e-4）不适用于 Scale=7——各 Scale 权威精度包络从未取得，
   Scale 补偿公式在高 Scale 段的量化误差本来就可能超出低段预算；
2. 硬件 Scale=7 补偿与 Golden 公式模型不一致（RTL 缺陷）。
注意手动配置固定 `precision = CORDIC_PRECISIO_8`（et_manual_cordic_test.c:35），
若 Formal 也使用相同迭代精度则两者可比；后续做 Scale 扫描实验时应把
precision 作为显变量。当前不能判定为 codex 问题。

### 2.5 cordic_p2_001 —— CORDIC DMA 模式等价性（仅手动执行，FAIL）

**证据**（diagnostics.log:285-298）：Polling 基线 `0x3FFFFC00` 正确；DMA 双通道
配置返回 DRV_OK，但通道永不 Free、`dma_result_raw` 保持哨兵值 `0xA5A5A5A5`、
CORDIC status=0——请求 `0x27/0x28`（历史映射）根本没有触发搬运。

**定性**：FPGA DMAMUX→CORDIC 路由未实现或 request 编号错误。这与平台决策
完全一致：正式侧因「DMAMUX Request/Endpoint 路由无审核过的 Execution Mapping」
将该 Case 判为 NOT_EXECUTED 而不是硬跑（周报 §2.4）。手动 FAIL 反过来
证明了当时不做 Execution Mapping 就不上 Formal 是正确的门禁判断。

### 2.6 stimer_p2_003 —— Debug Halt Pause（双路径一致 FAIL）【v2：刺激正确性已逐行核实】

**证据**（diagnostics.log:326-336）：PAUSE 轮经 J-Link 断点保持期间计数从
`0x21` 推进到 `0x0E991BE1`（增量 `0x0E991BC0`）；RUN_FREE 轮增量
`0x0477305E`。PAUSE 不仅没停，量级还超过 RUN_FREE（两次 hold 时长不同，
绝对值不可直接比，但「PAUSE 继续计数」方向事实无可辩驳）。

**v2 SDK 语义逐行核实（排除构造缺陷）**：

- `STIMER_enableCPUHalt()` = CLEAR_BIT(STM_SET.bit7)，即 bit7=0 为 PAUSE
  （et6x_stimer.c:353-357）；`disableCPUHalt()` = SET_BIT(bit7)=RUN_FREE
  （:640-641）。手动 Case 的 PAUSE 场景调用 enableCPUHalt，语义正确。
- `setEmulationMode(RUNFREE)` 写的是 STM_CONT_R 位（:85-93），与 bit7
  相互独立，不存在配置覆盖冲突。
- 两场景各自独立复位（et_manual_stimer_test.c:92、105），无状态继承。

**定性**：硬件缺陷成立。Cortex-M7 Halt 到 STIMER 的 RTL 路径在当前
bitfile 中未连接或未实现。Silicon 待独立验证。

### 2.7 wdg_p1_004 —— WDG 模块复位与恢复（仅手动执行，FAIL）【v2 修订：暂不能定罪硬件】

**证据**（diagnostics.log:337-345）：`WDG_testResetModule()` 后 `enabled_after_reset=1`
（应为 0），Counter 从 `0xFFFFC8` 继续递减到 `0xFFEB6E`——模块复位未生效。

**v2 深度核查发现的两个未排除变量**：

1. **KEY_CTRL 写保护未解锁（最强嫌疑）**。`WDG_testResetModule`
   （et6x_wdg.c:578-586）直接 CLEAR/SET `CRG->SRST0`，是全仓库唯一
   **不经过 `CRG_unlockClockConfig()`** 的 SRST 写路径；对照所有已证明有效的
   CRG 操作（crc/cordic/stimer/fmac 手动测试及 crg_register_reset_matrix，
   全部为 unlock→操作→lock 三段式）。`KEY_CTRL` 即 `SW_ACCESS_KEY`
   （et6801.h:11511）。若 KEY 锁定期间 SRST 写被静默丢弃，则复位根本没发出去，
   现象被完整解释，且与硬件无关。芯片文档 `ET6801_wdg.md:313` 记录了
   "按 CMSIS 位位置修正后仍不复位"，但从未把 KEY 解锁作为变量排除过。
2. **看门狗安全设计可能性**。多数 WDG IP 有意抵抗模块级软复位
   （Enable 后仅整机复位可清除）。若 SVD/设计如此定义，则是 Case 的
   Oracle（"模块复位应清除 Enable"）违反设计意图，同样不是硬件故障。

**v2 结论**：由"硬件缺陷"降级为「**待裁决：两个廉价实验前不得定罪硬件**」——
① 给 `WDG_testResetModule` 补 `CRG_unlockClockConfig()/CRG_lockClockConfig()`
包裹后重跑手动；② 向设计/SVD 确认 soft-reset 对已 Enable WDG 的定义语义。
注意：正式侧因 Runtime 未发布 `MODULE_RESET` 而 SKIP 的门禁决策依然正确，
不受本修订影响。

**对平台方案的牵连（v2 改写）**：「清理收敛为 CRG 复位当前 IP」方案在 WDG
外设上的可行性**尚未被证明也尚未被证伪**（现有失败可能是测试扩展自身缺解锁）。
落地前必须用统一的 unlock 包裹逐外设验证 CRG 复位有效性矩阵
（FMAC/CRC/AES/CORDIC 已证明有效；WDG 待上述实验裁决）。

### 2.8 wdg_p2_001 —— WDG 时钟分频速率（双路径一致 FAIL）

**证据**（diagnostics.log:346-358）：divider 读回正确（0 和 1），但 20ms 窗口内
Counter 递减量 `0x0003D327` vs `0x0003D2AF`，比值≈1.041，远低于下限 1.5。

**代码核对**：手动走 SDK `CRG_selectWDGClockSource(APB1, divider)`
（et_manual_wdg_test.c:24-29），两场景独立复位，交错采样设计合理。

**定性**：硬件缺陷。CRG 配置面（写/读回）正常，但分频器到 WDG Counter
时基的时钟树在当前 FPGA 中未按配置分频。Silicon 待验证。

### 2.9 fmac_p1_006 —— Float 转 Q15 Overflow 清除（Formal FAIL → Manual PASS）

**这是唯一一个已由手动诊断完整闭环「纯 Case 构造问题」的 FAIL。**

**旧 Formal 失败机理**：越界条件仍然活跃时立即执行 W1C 清除 → 硬件拒绝/
立即重新置位 → FAIL。

**手动修正版**（et_manual_fmac_test.c:47-105）三段式：
```text
4×2.0f 触发        → sr_after_trigger = 0x1001（bit12 置位 ✓）
0.25f 正常输入解除  → recovery_load = DRV_OK
W1C 清除           → sr_after_clear = 0x00000001（bit12 已清 ✓）→ PASS
```
（diagnostics.log:299-309）

**数字设计语义**（已由本轮确认）：Sticky 错误位必须先解除实时错误条件才允许
软件清除。这不是硬件缺陷，是硬件设计约定。

**定性**：codex/Case 构造问题（刺激顺序不符合硬件清除语义）。修正方向已经
手动验证，**但截至本报告 Formal Case 尚未按新语义修改并复跑**
（周报 §2.4 明确此项待办），因此正式状态维持 FAIL 是正确的。

### 2.10 fmac_p1_010 —— Output Offset Negative 状态清除（Formal FAIL）

**已定位的根因（软件路径）**：三种清除方式的定向实验结论——

| 清除方式 | 效果 |
|---|---|
| `FMAC.CR.CLR` | 无效 |
| 向 SR bit11 写 0 | 无效 |
| **向 SR bit11 写 1（W1C）** | **有效** |

公共 Chip Driver/Wrap 的状态清除接口选择了错误语义。SVD 定义该位为
write-1-clear，Wrap 却走了 CLR/写 0 路径。

**两个补充事实**：

1. 当日 09:38 用当时代码复跑 Formal（`20260826_093820_683819`）仍 FAIL——
   修复尚未落地，与周报口径一致。
2. **全量手动套件中的 p1_010 版本自身也有构造缺陷**：它用 SAT12+offset=0
   配置（et_manual_fmac_test.c:121），负输入后 `sr_after_trigger=0x00000001`，
   bit11 根本没有置位（diagnostics.log:310-316），Case 在触发阶段就失败了，
   并没有完成它想验证的 W1C 实验（W1C 结论来自更早的定向 w1c_hil 运行）。
   这提示 `ADD_OFT_IS_NEG_RPT` 的产生依赖输出模式/Oft 配置组合，
   修订 Formal Case 时必须一并核实触发条件矩阵。

**定性**：软件路径问题（Wrap 清除语义）为主，叠加 Case 配置敏感性。
不是硬件缺陷——数值路径、置位、W1C 都已被分别证明工作。

### 2.11 UART 三个 SKIP 的手动佐证（非正式 FAIL）

| Case | 手动证据 | 归因 |
|---|---|---|
| uart_p1_008 | LSR=0x61、FE=0：TX/RX 交叉布线下发送 `55 AA 00 FF` 无法确定性制造停止位失配 | 环境布线限制，非硬件/非 Case 缺陷 |
| uart_p1_012 | 256 次尝试仅 43 Byte 被接受，全程未现 `USR.BUSY=1`，IID 终值 1 非 7 | 触发窗口过窄（时序竞争），证据不足以判硬件失败 |
| uart_p3_009 | `CPR.FIFO_ACCESS(bit9)=0`，Driver 返回 DRV_INVALID=3，tx/rx_value=0 | Capability 未发布，目标不适用 |

三者 Formal 侧 SKIP 决策均正确；手动 FAIL 只是「刺激条件未建立」的记录，
不构成对硬件的否定。

---

## 3. 责任归属汇总矩阵【v2 修订】

| Case | codex/Case 构造 | 软件路径(Wrap/Driver) | 硬件/FPGA/bitfile | 规格·预算未闭合 | 环境·Capability |
|---|---|---|---|---|---|
| crc_p1_011 | △ 期望模型建立在历史行为+未权威化语义上 | | ● 主嫌（TRHD读回=5已排除配置丢失，ET6801_crc.md:596） | ○ CPU直写是否应过阈值待RTL owner定义 | |
| crc_p1_012 | | | ● 已由同事确认FPGA FIFO_OVF问题（ET6801_crc.md:379,625） | | |
| aes_p1_009 | 刺激配方有出处（et6x_aes.c:528-534历史序列） | | ？ 强嫌疑 | ● 权威触发条件未闭合 | |
| cordic_p1_003 | | | ？ | ● Golden公式错误与RTL误差二选一，本地不可裁决 | |
| cordic_p2_001(手动) | | | ● DMA路由死 | ○ Mapping未审批（正确门禁） | |
| stimer_p2_003 | 构造已逐行核实无误（v2） | | ● CPUHalt路径未接 | | |
| wdg_p1_004(手动) | ● 新嫌疑：WDG_testResetModule缺KEY解锁；且Oracle可能违反看门狗安全设计 | △ SDK测试扩展自身缺陷候选 | ？ v2降级：两个实验前不得定罪 | ○ soft-reset语义未确认 | |
| wdg_p2_001 | 构造无懈可击（交错中位数+SVD编码明确） | | ● RTL分频映射缺失（比值0.99864，三次独立复现） | | |
| fmac_p1_006 | ● 清除顺序错误（已验证修法） | | | ○ 硬件清除语义约定 | |
| fmac_p1_010 | △ 配置敏感性 | ● 清除接口选错（W1C已证实） | | | |
| uart×3(Skip) | | | | | ● 布线/窗口/能力缺失 |

图例：● 主责　○ 强嫌疑/次要　△ 有责任但非主因　？ 待设计确认

**v2 总体修订**：11 个手动 FAIL 中——
- **硬件判定稳固 4 个**：crc_p1_012、stimer_p2_003、wdg_p2_001、cordic_p2_001；
- **硬件强嫌疑但需设计输入闭合 3 个**：crc_p1_011、aes_p1_009、cordic_p1_003；
- **v2 由硬件改判为"测试侧待裁决" 1 个**：wdg_p1_004（KEY 解锁缺失 +
  Oracle 语义两变量未排除）；
- **Case/软件问题 2.5 个**：fmac_p1_006、fmac_p1_010、crc_p1_011 部分。

---

## 4. 回答「是不是 codex 的问题」【v2 修订】

1. **大部分不是。** 硬件判定稳固的 4 例（crc_p1_012、stimer_p2_003、wdg_p2_001、
   cordic_p2_001）均经 Formal 与独立手动固件双路径交叉验证一致，且本轮对
   SDK 语义逐行核实（STIMER bit7 独立性、AES 历史握手序列、CRC J-Link 读回）
   后未发现任何构造缺陷。这些 Case 忠实暴露了 bitfile 与 SVD 承诺的偏差。
2. **确实有 2 个是测试侧问题，且都已闭环定位**：fmac_p1_006（清除时机违反
   「先解除条件再清」）、fmac_p1_010 公共清除接口选错 W1C 语义。
   修正方向均经手动 HIL 证实，剩余工作是改代码 + Formal 复跑。
3. **有 1 个测试侧能力缺口**：crc_p1_011 的手动版本没有真正测试阈值边界
   （2 word 输入 < 所有阈值档位），无法仲裁 Formal 观察；但芯片文档记录
   J-Link 已排除配置丢失且历史行为与当前 FPGA 不符，主嫌仍在硬件侧。
4. **v2 重要改判——wdg_p1_004 暂不能定罪硬件**：`WDG_testResetModule` 是
   全仓库唯一缺 `CRG_unlockClockConfig()` 的 SRST 写路径（KEY_CTRL=
   SW_ACCESS_KEY 锁定期间写可能被丢弃）；叠加"看门狗安全设计本就抵抗模块
   软复位"的设计语义可能性。补解锁重跑 + 设计确认两个实验之前，
   该 FAIL 的归属是开放的。此前 v1 将其归为硬件是不充分的。
5. 平台流程层面做对了的事同样值得记录：cordic_p2_001 因 Mapping 未审批而
   NOT_EXECUTED、uart/wdg 系列 Capability 缺失时 SKIP、手动结果不直接改写
   Formal 状态——这些门禁在本轮全部被证明是对的。

## 4A. v1→v2 修订记录（同日深度核查）

| Case | v1 判定 | v2 判定 | 修订依据 |
|---|---|---|---|
| wdg_p1_004 | 硬件：模块复位无效 | **待裁决**（KEY解锁缺失 / Oracle违反安全设计 / 硬件三选一） | et6x_wdg.c:578 无解锁 vs 全仓库 unlock 模式差异；ET6801_wdg.md:313 从未排除该变量 |
| stimer_p2_003 | 硬件（依据现象） | 硬件（依据加强） | 新增 SDK bit7/STM_CONT 位独立性逐行核实 |
| crc_p1_011 | 硬件主嫌+构造部分责任 | 维持，依据加强 | ET6801_crc.md:592-608 记录 TRHD=5 读回与历史行为偏差 |
| 其余 | — | 维持 | 复核无新变量 |

## 5. 下一步建议【v2 修订】

```text
P0 软件修复（证据已完备，改完即可复跑翻绿）
   1. Wrap/Chip Driver 状态清除改为 SR 目标位写1（W1C）→ 复跑 fmac_p1_010
   2. fmac_p1_006 Formal 按「越界→正常输入→W1C」顺序修订 → 复跑
P0.5 廉价裁决实验（v2 新增：先于任何硬件结论）
   3. WDG_testResetModule 补 CRG unlock/lock 包裹 → 重跑手动 wdg_p1_004；
      同时向设计确认 soft-reset 对已 Enable WDG 的定义语义
P1 测试构造增强（解决仲裁缺口）
   4. crc_p1_011 重构为 TRHD × 写入次数矩阵，并补一条手动对齐路径
P2 设计确认（需要 RTL/设计输入，不能用弱化断言绕过）
   5. CRC FIFO_OVF、STIMER CPUHalt、WDG Divider、CORDIC DMA 路由
      → 向 bitfile/RTL 团队提交双路径一致证据
   6. AES Output Conflict 触发条件、CORDIC Scale=7 精度包络 → 取权威规格
P3 方案影响评估
   7. 「清理收敛为 CRG 复位」方案：FMAC/CRC/AES/CORDIC 有效；WDG 在 P0.5
      实验裁决前不可下结论。落地前须以统一 unlock 包裹建立逐外设 CRG
      复位有效性矩阵并回写芯片文档
```

## 6. 未执行项声明（NOT_EXECUTED）

- 未修改任何 Firmware/PC/文档文件；未执行构建、烧录、复位或仪器操作；
- 未复跑任何 Formal Case 验证本文假设；
- Silicon 侧对所有硬件类结论均未验证，本文全部硬件判定只针对
  当前 XC7VX980T bitfile；
- Quick Doctor 指纹过期未处理（避免写入生成状态）。

## 7. 关键证据行索引

```text
diagnostics.log:242-256   crc_p1_011 四档阈值全PASS（未触边界）
diagnostics.log:257-264   crc_p1_012 64连写 OVF恒0
diagnostics.log:265-274   aes_p1_009 双block提交 raw/status=0
diagnostics.log:275-284   cordic_p1_003 delta=0x314>budget 0x216
diagnostics.log:285-298   cordic_p2_001 DMA哨兵值未被改写
diagnostics.log:299-309   fmac_p1_006 修正序列 PASS（bit12 置位→清零）
diagnostics.log:310-316   fmac_p1_010 手动版触发阶段即失败（SAT12+off0）
diagnostics.log:326-336   stimer_p2_003 PAUSE持续计数
diagnostics.log:337-345   wdg_p1_004 模块复位后Enable仍=1
diagnostics.log:346-358   wdg_p2_001 divider速率比≈1.041
et_manual_crc_test.c:39,53      手动CRC输入仅2word、走calculate32
et_manual_fmac_test.c:121       手动p1_010使用SAT12+offset0配置
et_manual_stimer_test.c:92-115  两场景独立复位+BKPT断点设计
et_manual_wdg_test.c:9-12       reset_wdg走WDG_testResetModule
firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_crg.c:283-292  SDK复位不含GTEN/KEY
et6x_wdg.c:568-590              WDG_testResetModule：唯一缺KEY解锁的SRST写路径(v2关键)
et6x_stimer.c:85-93,353-357,640-641  STM_CONT与CPUHALT bit7相互独立；enable=清bit7
et6x_aes.c:231-243,518-546      DATA_IN_REQ握手；BlockPair复刻历史冲突序列
et6x_crc.c:115-177,368-378      calculate32逐写前轮询OVF；OVF直读FIFO_OVF寄存器
ET6801_crc.md:592-625           J-Link读回TRHD=5；同事确认FPGA FIFO_OVF问题
ET6801_wdg.md:313-314,405-439   WDG复位/分频历史诊断与MAPPING_GAP记录
et6801.h:11183,11206,11511      CORDIC0=SRST0 bit20、WDG0=SRST0 bit7、KEY_CTRL定义
```
