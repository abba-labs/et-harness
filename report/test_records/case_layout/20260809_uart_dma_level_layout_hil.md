# UART/DMA 按测试等级归档后的 HIL 验证记录

时间：2026-08-09 11:58 CST

## 结论

UART 与 DMA Case 已按统一规则整理为“每个 IP 目录内按 P0～P3 测试等级建文件，文件内部再按 Feature 分区”。本轮真实 ET6801 FPGA 原型 HIL 结果如下：

| IP | 结果 | 说明 |
|---|---:|---|
| UART | 30 PASS / 3 SKIP / 0 FAIL | 3 个 SKIP 均有明确板级或运行时原因 |
| DMA | 187 PASS / 14 SKIP / 0 FAIL | 14 个 SKIP 均因当前 UART DMA 路由只映射 DMA0 |

本轮没有重新配置 bitstream，没有重新加载 BootROM，也没有擦写 PFLASH；测试使用当前已经运行的 `et6801-silicon-common-v0.1` 固件。

## 环境与路由

- 目标：ET6801 CORE0，XC7VX980T FPGA 原型。
- PC 通信：`COM12 @ 115200`。
- 外设连线：UART1 与 UART2 交叉短接。
- Bench：`pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`。
- 固件身份：`chip_id=et6801`、`registry_hash=6d69ded4`。

## 软件门禁

执行 `tools/validate_pc.py`，结果：

- Unit / Contract / Native：374 PASS、9 SKIP。
- Formal Case 收集：UART 33 项，DMA 201 项。
- Ruff format、Ruff lint、AST architecture、文档语义、Case orchestration 和 Firmware contract 全部通过。
- 资源守护任务：`20260809_115326_c3caf300`。

## UART HIL

- 原始证据：`../../../../artifacts/uart_hil/20260809_113028_uart_level_layout_after_rearm_fix/`。
- JUnit：33 项，30 PASS、3 SKIP、0 FAIL。
- `session.json`：`exitstatus=0`，固件、registry、Bench 和串口身份均匹配。
- P1-005 TX FIFO Threshold IRQ 在每个阈值前显式重新使能一次性 TX_READY IRQ；修复后定点 HIL 与全量 HIL 均通过。

3 个 SKIP：

1. Framing Error：当前板级连线没有确定性的错误帧激励源。
2. Busy Detect：当前运行时无法在有界窗口内稳定形成 Busy Detect 条件。
3. Direct FIFO Access：运行时能力未声明 `FIFO_ACCESS`。

## DMA HIL

- 原始证据：`../../../../artifacts/dma_hil/20260809_115446_dma_level_layout_after_uart_gate/`。
- JUnit：201 项，187 PASS、14 SKIP、0 FAIL。
- 结构化 DMA Case 结果：187 个 JSON，与 PASS 数量一致。
- `session.json`：`exitstatus=0`，固件、registry、Bench 和串口身份均匹配。
- 资源守护任务：`20260809_115446_834ce832`。

14 个 SKIP 都是执行映射门禁：当前 UART1/UART2 DMA 路由选择 DMA0，因此 DMA1 的 Source Transaction、Destination Transaction、M2P、P2M、P2P、Software Handshake 和 Handshake Mode 参数组合不执行。该结果与能力/执行映射一致，不属于 Case 重组回归。

## 代码归档结果

UART 活动文件：

- `test_uart_p0.py`
- `test_uart_p1.py`
- `test_uart_p2.py`
- `test_uart_p3.py`

DMA 活动文件：

- `test_dma_p0.py`：6 个 Case，114 个参数化实例。
- `test_dma_p1.py`：9 个 Case，42 个参数化实例。
- `test_dma_p2.py`：13 个 Case，45 个参数化实例。

DMA P3 仍属于设计条件类 Feature，没有创建空 Case 或 `pytest.skip` 伪装覆盖；相关计划继续保存在 `deferred_features.py` 和 `test_case_doc/DMA.md`。

## 剩余风险

- 当前 HIL 不能证明 DMA1 的 UART 外设握手路由；需要新增映射到 DMA1 的可控外设端点后再执行这些参数组合。
- pytest 使用 `junit_family=xunit2` 时会提示 `record_property` 兼容性警告；不影响本轮 PASS/FAIL 和 JSON 证据，但后续可单独统一 JUnit 属性记录方式。
