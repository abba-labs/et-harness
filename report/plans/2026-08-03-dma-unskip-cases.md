# DMA Unskip Cases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用最小、直接、可恢复的硬件用例解除 ET6801 DMA 软件握手、有限 Reload、时钟/复位恢复三项 `skip`。

**Architecture:** 完整测试编排只放在 PC DMA Case；PC 仅调用既有 Resource、DMA、System 和可替换的 peripheral-pair Driver。固件 Service、Wrap 和协议保持现状，除非失败测试证明既有接口不足。

**Tech Stack:** Python 3、pytest、ET-Frame UART、Keil MDK、ET6801 FPGA/HIL。

## Global Constraints

- 不在 Case 中直接访问寄存器、串口实现或芯片 SDK。
- 不新增跨 IP Service 组合逻辑，不改变 Framework 分层。
- 每个用例只判断一个 DMA Feature，所有等待必须有界，`finally` 必须恢复 DMA 时钟和资源。
- `priority_arbitration`、故障注入、跨内存域及 CORE/TCM 在没有可靠证据前继续 `skip`。

---

### Task 1: PC orchestration contract tests

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_dma_helpers.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma/dma_helpers.py`

**Interfaces:**
- Consumes: `DmaDriver`, `SystemDriver`, `DmaPeripheralPair`, `ResourceDriver`
- Produces: 仅供 DMA Case 复用的有界等待/清理辅助逻辑

- [ ] 写失败单测，覆盖软件握手逐项请求、Reload 达到目标块计数后停止、异常路径恢复时钟。
- [ ] 运行定向 pytest，确认因辅助逻辑缺失而失败。
- [ ] 最小实现辅助逻辑，不增加新的平台抽象层。
- [ ] 重跑定向 pytest 并保持原 DMA 单测通过。

### Task 2: Replace three skips with direct feature cases

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma/dma_test_case_p1.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma/dma_test_case_p2.py`

**Interfaces:**
- Consumes: Task 1 helpers and existing pytest fixtures
- Produces: `reload_modes`, `software_handshake`, `reset_clock_recovery` hardware cases

- [ ] `reload_modes`：源、目的、双侧 Reload 分别运行；观察至少两个 BLOCK_DONE 后停止并校验数据。
- [ ] `software_handshake`：M2P 使用 profile 声明的 peripheral pair；每个数据项发出 destination TRANSFER+SINGLE 请求；校验捕获数据。
- [ ] `reset_clock_recovery`：基线 M2M、关/开 DMA 时钟、DMA reset、恢复 M2M；任意异常都恢复时钟。
- [ ] 每个 Case 写清 `Feature`、输入、输出、PASS/FAIL 和恢复方法。

### Task 3: Static and firmware validation

**Files:**
- No production file expected unless validation finds a defect.

**Interfaces:**
- Consumes: completed PC cases and existing firmware
- Produces: fresh unit, collection and Keil build evidence

- [ ] 运行 DMA/协议/Profile 定向单测。
- [ ] 收集 DMA 全量节点，确认仅目标三项不再静态 `skip`。
- [ ] 按 ET SDK build flow 生成/校验构建计划。
- [ ] 通过受控入口编译 `ET6801_FPGA_ITCM` 和 `ET6801_SILICON_FLASH`。

### Task 4: HIL gate and execution

**Files:**
- Create: `artifacts/dma_unskip_hil/<timestamp>/...`
- Update after evidence: `test_case_doc/DMA*.md` 中第七章状态表

**Interfaces:**
- Consumes: 已编译固件、XC7VX980T、J-Link、J28/COM、UART1↔UART2 短接
- Produces: Flash 运行与三项 DMA Case 的新鲜证据

- [ ] 提交硬件操作清单并等待人工确认。
- [ ] Flash 烧写、Verify、从 Flash 运行。
- [ ] 先单项运行，再运行 DMA P0-P2 回归。
- [ ] 按真实结果更新状态；不得由编译结果推断 HIL PASS。
