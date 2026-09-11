# ET 自动化测试平台公共层冻结收口

时间：2026-08-11；**2026-09-11 复核更新**
状态：软件架构 FROZEN
当前基线：\`codex_dev@1e584956\`（2026-09-11）

> 2026-09-11 更新说明：本文原基线为 \`review_code@25165e63\`。该分支已废弃（\`review_code\`
> 不再存在），且该提交不在当前仓库历史中，原文的 SHA、统计数字和分支引用已失效。
> 本轮按**当前仓库真实架构**复核重写第 4、5 节与基线，冻结结论与变更规则（第 1、2、6 节）
> 经复核仍然成立，无实质变化。

## 1. 冻结结论

公共软件架构已经完成冻结前最后一轮收口，后续普通 IP 开发不得再以“简化 Case”或“新增 IP”为理由修改公共运行机制。

冻结模型固定为：

\`\`\`text
Case = Test Flow + Evidence + PASS/FAIL + Cross-IP Cleanup Order
Support = Runtime/Capability/Bench/Resolver Gate + Driver Construction
Driver = One-IP Behavior + Deadline/Polling + Necessary One-IP Lifecycle
Codec = Pure Wire Encode/Decode
TargetClient = Common Request/Response
Firmware Service = Decode + Own Wrap + Encode Facts
Wrap = Own IP Chip Driver
\`\`\`

## 2. 冻结范围

以下公共软件语义进入 FROZEN：

\`\`\`text
pc/et_test_platform/core/**
pc/et_test_platform/clients/**
pc/et_test_platform/communication/**
pc/et_test_platform/scheduling/**
pc/et_test_platform/results/**
通用 Capability Model/Loader
通用 Deadline/Cleanup/Evidence/Result 机制
Formal Case 收集与稳定 ID 机制
\`\`\`

后续新增普通 IP，PC 侧主要变化范围应为：

\`\`\`text
drivers/<ip>/**
test_cases/<ip>/**
\`\`\`

允许在以下组合点增加本 IP 条目，但不得改变公共机制：

\`\`\`text
test_cases/ip_registry.py
Firmware Service 聚合注册处
Firmware Application/Board 实例声明
Keil 工程生成配置
\`\`\`

**2026-09-11 复核**：上述五个目录全部存在且结构未变；冻结范围继续成立。
\`ip_registry.py\` 仍是唯一的 Formal Case 静态注册入口，未引入第二套注册机制。

## 3. 最终规则真值

### Case

- 目录按主要测试 IP 归属；
- 文件按 P0～P3 等级组织；
- 文件内部按 Feature 分区；
- Case 前固定使用中文 \`#\` 三段说明：测试 Feature、测试方法、通过条件；
- 测试方法和通过条件必须编号；
- Case 内准备、配置、启动、观测、断言、恢复和记录保持直接可读；
- 不使用 Docstring 承担项目文档；
- 不隐藏完整场景到 Helper/Workflow；
- Formal Case Registry 只是不可变执行白名单，不是运行时对象 Registry。

### Driver

- 一个 Driver 只负责一个 IP；
- Deadline、Polling、Retry 分类和单 IP Cleanup 属于 Driver；
- 只在语义稳定、同一 IP、不会隐藏测试动作时增加生命周期 Scope；
- 不为了减少少量 Case 行数继续增加新的生命周期抽象；
- DMA IRQ 当前继续使用 Case 显式 Cleanup，没有 \`dma.irq_mode()\`。

### Wire/Firmware

- UART/DMA 保持已发布 V1 Wire Shape 和 Command ID；
- 废弃同步等待 Command ID 只保留兼容占位并返回 \`NOT_SUPPORTED\`；
- V1 poll-budget 字段只用于 Wire 兼容，真实 Deadline/Polling 仍由 PC Driver 负责；
- Firmware Service 不执行完整 Case、不跨 IP 编排、不形成最终 PASS/FAIL。

## 4. 当前软件验证（2026-09-11 复核）

本轮在 \`codex_dev\` 干净树（\`b6a889f9\`）上实测：

\`\`\`text
总软件门禁 tools/validate_pc.py          PASS（全阶段）
PC 单元 / 契约 / Native                   1993 passed, 17 skipped
Formal Case 注册 IP                       13
Formal Case 实际执行（全量回归）           736 execution
Repository clean after validation         PASS
\`\`\`\`

13 个已注册 IP 及其本轮全量回归执行数：

\`\`\`text
AES 59   CAN 148  CORDIC 53  CRC 44    DMA 88    FMAC 46
IPCM 34  SPI 152  SPINLOCK 15 STIMER 27 SYSCNT 23 UART 33  WDG 14
------------------------------------------------------------
Total   736
\`\`\`

说明：\`ip_registry.py\` 是**可执行全集**，不是默认执行范围；没有明确全量指令时禁止自动遍历
全部 IP（R500 §5.1）。本轮为 2026-09-09 用户指令下的全量硬件回归。

## 5. 硬件证据边界

2026-09-11 已在 ET6801 FPGA Lane 上完成 13 IP 全量回归（源码 \`b6a889f9\`，source_dirty=false）：

\`\`\`text
AES PASS(59/0)      CAN FAIL(139/9)     CORDIC PASS(52/1)   CRC FAIL(43/1)
DMA PASS(88/0)      FMAC PASS(46/0)     IPCM PASS(34/0)     SPI PASS(116/36skip)
SPINLOCK FAIL(7/8)  STIMER PASS(23/4)   SYSCNT PASS(21/2)   UART PASS(30/3)
WDG FAIL(9/4)
\`\`\`\`

（格式：PASS/FAIL，skip 单列。各 IP 的 Canonical Session、结果与当次事实位于
\`artifacts/records/ET6801/<IP>/current/\`；提炼知识位于同 IP 的 \`cases/*.md\`。）

未闭合失败项与归因边界：

- \`CRC_P1_012\`：ET6801 FPGA 的 \`FIFO_OVF\` 功能不翻转，属 RTL/bit 问题，不得删除断言或改为 SKIP。
- \`WDG\` 4 项：真实系统复位未形成，未观测到断连；不得用 \`MODULE_RESET\` 冒充系统 reset。
- \`SPINLOCK\` 8 项：全部为双核 \`[one]/[two]\` 参数，\`assert peer_ready is True\` 失败——
  本轮部署形态**未部署 SPINLOCK Peer**，不是 SPINLOCK 功能缺陷；需双核形态复测。
- \`CAN\` 9 项：\`P1_020\`×6 + \`P2_003\`×2 + \`P2_005\`×1，与 2026-08-28 基线一致。

**Silicon Lane 未执行**：以上全部为 FPGA Lane 结果，不得外推为 Silicon 结论。
Keil 编译验证与 Silicon HIL 的 exact-SHA 状态保持：

\`\`\`text
Silicon HIL exact-SHA regression    NOT_EXECUTED / NOT_VERIFIED
\`\`\`\`

该状态不改变“公共软件架构已冻结”的治理结论，但任何硬件发布或运行时等价性声明仍必须引用实际执行的对应 HIL 证据（R500 §5.3、R130）。

## 6. 冻结后的变更规则

冻结后，公共层只允许以下原因修改：

1. 已复现的公共层 Bug；
2. 新 IP 证明现有公共抽象无法表达的真实跨 IP 公共需求；
3. 安全、可靠性或协议缺陷需要修复；
4. 用户明确批准的公共 Contract 变更。

禁止：

- 为减少几行 Case 再增加 Manager、Workflow、DI、Plugin 或通用生命周期框架；
- 为单个 IP 修改公共 Scheduling/Communication/Result 语义；
- 为文件行数机械拆 BaseDriver/Mixin；
- 无硬件证据时修改已经 HIL 证明的运行时命令集合、顺序或 Cleanup 语义。

后续工作应从“继续重构公共架构”切换为“按冻结规则新增 IP 与 Feature”。

## 7. 依据与变化

- 2026-08-11：原版发布，基线 \`review_code@25165e63\`，Formal Case 122 节点，单元 423 passed。
- 2026-09-11：复核更新。\`review_code\` 分支已废弃，原基线提交不在当前仓库历史中；
  按 \`codex_dev\` 当前真实架构重写基线与第 4/5 节统计（13 IP / 736 execution /
  1993 passed / 17 skipped），补入本轮 13 IP 全量回归结果与各失败项归因边界。
  第 1、2、3、6 节的冻结结论与变更规则经复核无实质变化。
