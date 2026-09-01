# Phase 6：Test Case、软件闭环、Keil/HIL 与最终交付 Review

日期：2026-08-06，软件最终复核更新于 2026-08-07  
分支：`review_code`  
软件闭环代码基线：`f7b8aba354f094cda793df4c4f343781690214fd`

## 1. 当前结论

Phase 6 现在必须分成“软件交付”和“真实硬件验证”两个维度记录：

```text
6A Formal Test Case 软件重构          DONE
6B 静态 / Unit / Contract / Native    DONE
6E 软件架构 Review / 文档 / CI         DONE
软件层 Phase 6                        DONE

6C ET6801 FPGA/Silicon 实际 Keil Build NOT_EXECUTED
6D ET6801 真实 HIL                      NOT_EXECUTED
完整硬件闭环                           PENDING
```

本轮用户明确要求先完成非硬件软件层，因此：**软件层允许标记 DONE；实际 Keil/HIL 仍单独保留 NOT_EXECUTED。**

最新软件结论详见：

- [软件层最终重构 Review](20260807_software_layer_final_review.md)

## 2. Formal Case 最终结构

DMA：

```text
test_cases/dma/
├── test_memory_to_memory.py
├── test_channel_control.py
├── test_interrupts.py
├── test_linked_list.py
├── test_gather_scatter.py
├── test_handshake.py
├── test_register_snapshots.py
└── deferred_features.py
```

UART：

```text
test_cases/uart/
├── test_polling.py
├── test_interrupts.py
├── test_dma_tx.py
├── test_dma_rx.py
├── test_dma_full_duplex.py
└── deferred_features.py
```

UART DMA TX/RX/Full Duplex 仍归属 UART，因为主要测试主体是 UART。

所有正式 Case 必须包含：

- 测试 Feature；
- 主要测试主体；
- 参与/支撑 IP；
- 前置条件；
- 测试步骤；
- 观测证据；
- 通过条件；
- 清理要求；
- `Arrange -> Resolve -> Configure -> Start -> Observe -> Assert -> Cleanup`。

不具备批准证据的设计项已经进入 `deferred_features.py`，不得再作为 Formal `test_* + pytest.skip` 伪装覆盖。

## 3. Test Case 编排整改

最终代码不再允许大型 Helper 拥有完整 Case 生命周期。

永久规则工具：

```text
tools/check_case_orchestration_rules.py
```

最终禁止：

```text
execute_m2m_transfer
execute_peripheral_transfer
execute_dma_transfer_done_interrupt
_cleanup_all
build_dma_peripheral_pair
SYSCTRL V1 configure_dma_request() in Formal Case
uart_session
loopback_transfer
paired_transfer
_require_irq_event
require_cleanup
```

### DMA 外设链路

DMA Handshake、SOURCE_TRANSACTION IRQ、DESTINATION_TRANSACTION IRQ 现在直接展示：

```text
Resolve UART DMA Route
-> UART Configure
-> SYSCTRL V2 configure_route
-> DMA Configure / IRQ / Start
-> Buffer / Capture / IRQ Evidence
-> Assert
-> Aggregate Cleanup
```

原 `dma_peer.py` 已删除。

### DMA LLI

正式 LLI Case 使用直接 Descriptor Address V2，不再依赖旧 Handle V1 执行语义。

### UART

UART 正式 Case 不再通过 `uart_session()`、`loopback_transfer()`、`paired_transfer()` 或 `_require_irq_event()` 隐藏生命周期和最终结论。Case 直接拥有相关调用与 Assertion。

## 4. Cleanup 与结论归属

Formal Case 使用 `case_cleanup_scope()` 与命名 `cleanup_actions()` 聚合 Cleanup：

```text
Primary Error
+ Stop / Disable / Deconfigure / Route Release / Deinit 等全部 Cleanup Error
```

不再使用 raw `finally` 顺序 Cleanup 导致第一个 Cleanup 失败阻止后续清理。

Measurement JSON 只保存事实与 Measurement；pytest Assertion/统一 Result 拥有最终 PASS/FAIL。

## 5. 最终非硬件质量门禁

最终软件收口 Run：`31137876718`。

候选树先完整验证；随后删除全部临时重构资产，再对最终生产树重复同一套验证。

最终结果：

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Formal Case Orchestration Rules       PASS
Generated Firmware Project Contract   PASS
PC Unit / Contract / Native            331 passed, 3 skipped
Formal Case Collection                235 nodes
Legacy Formal Case Path Scan          PASS / 0 hit
Temporary Refactor Asset Check        PASS
Git diff --check                      PASS
```

3 个 Skip 是非硬件测试环境中的显式环境门禁，不代表硬件 PASS。

235 个 Formal Case 节点只证明软件定义、Import、Fixture、参数化和收集链完整，没有在本 Review 中被解释为真实板执行通过。

## 6. 永久 CI

最终 `.github/workflows/` 只保留：

```text
pc-quality.yml
```

Workflow 名称为 `Software Quality Gate`，覆盖 `review_code` Push，并在 PR 修改以下路径时运行：

```text
pc/**
firmware/**
tools/**
pyproject.toml
.github/workflows/**
```

它执行统一 `python tools/validate_pc.py`，并检查验证后工作树必须保持干净。

统一验证入口包括：

```text
Python Syntax
Ruff Format / Lint
PC AST Architecture Rules
Formal Case Orchestration Rules
Generated Firmware Project Contract
PC Unit / Contract / Native
Formal Case Collection
```

Generated Firmware Project Contract 仅验证软件工程描述/生成合同，不代表真实 Keil 编译。

## 7. 临时重构资产

最终提交：

```text
f7b8aba354f094cda793df4c4f343781690214fd
refactor: complete software-layer architecture closure
```

提交中删除：

- `tools/refactor/` 全目录；
- `.github/workflows/case-orchestration-audit.yml`；
- 所有 `.github/workflows/one-shot-*.yml`；
- `test_cases/dma/dma_peer.py`；
- 对应旧 Helper/Adapter Unit Contract。

软件最终树不存在临时迁移脚本和一次性 Workflow。

## 8. Keil 状态

历史环境审计确认仓库存在：

- `ET6801_FPGA_ITCM`；
- `ET6801_SILICON_FLASH`。

但 Hosted Runner 未提供实际 Keil/ARM Compiler 执行环境，因此本轮仍记录：

```text
ET6801 FPGA Keil Build       NOT_EXECUTED
ET6801 Silicon Keil Build    NOT_EXECUTED
```

详见：

- [ET6801 Keil 实际构建报告](../build/20260806_et6801_keil_build_report.md)

## 9. HIL 状态

本轮按用户要求不继续硬件链路：

```text
ET6801 FPGA/Silicon HIL      NOT_EXECUTED
```

详见：

- [ET6801 真实 HIL 执行报告](../hil/20260806_et6801_hil_report.md)

## 10. 最终判定

```text
Software Architecture Review : PASS
Software Reliability Review  : PASS
Formal Case Software Review   : PASS
Permanent Software Gate       : PASS
Migration Debt                : 0
Hardware Build/HIL            : NOT_EXECUTED
```

因此本次“非硬件软件层重构”已完成。未来若要宣布完整 FPGA/Silicon 交付完成，仍需在真实环境执行 Keil Build 与 HIL，并单独更新硬件报告。
