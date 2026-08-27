# review_code@bf940723 UART DMA TX HIL 测试记录

## 测试结论

2026-08-08 06:53 CST，针对 `review_code@bf94072319b450d4b84b60162a427ff3fcf5f75e` 执行 UART DMA TX 单项 HIL，结果为 **PASS**。

本次只验证 UART DMA TX，没有重新配置 FPGA bitstream、加载 BootROM 或擦写 PFLASH。对比确认目标提交与板上最近一次已烧录版本 `56d2add65dfa48ed831bbc6ea1a9f1fee4f168ed` 的 `firmware/` 目录无差异，因此复用板上已有固件。

## 测试环境

| 项目 | 内容 |
|---|---|
| 目标芯片 | ET6801（XC7VX980T FPGA 原型） |
| PC 代码提交 | `bf94072319b450d4b84b60162a427ff3fcf5f75e` |
| 固件标识 | `et6801-silicon-common-v0.1` |
| 控制链路 | `COM12 @ 115200` |
| 数据链路 | UART1 TX → UART2 RX（板外短接） |
| Bench Profile | `pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml` |
| Capability 路由 | DMA0 / channel 0 / interface 1 / request ID 194 |
| FPGA/BootROM/PFLASH | 本次未重新配置或烧录 |

## 测试方法

1. 运行 Target Smoke，校验 HELLO、固件 Build ID、Registry Hash 和 Service List。
2. 由 PC Case 创建 32 字节源 Buffer，并配置 UART1 TX DMA 请求路由。
3. 启动 UART2 捕获，再启动 DMA memory-to-peripheral 传输。
4. 等待 DMA 完成中断和 UART2 捕获完成。
5. 校验接收数据与源 Buffer 完全一致、DMA 完成中断已发生、无异常/溢出且通道已释放。

执行节点：

```text
pc/et_test_platform/test_cases/uart/test_dma_tx.py::test_uart_p2_001_dma_tx
```

## 结果明细

| 检查项 | 结果 |
|---|---|
| Target Smoke | PASS |
| pytest | 1 passed / 0 failed / 0 skipped |
| 传输字节数 | 32 |
| UART2 捕获数据 | 与源 Buffer 完全一致 |
| DMA 完成中断 | 1 次 |
| Unexpected / Overflow | 0 / 0 |
| DMA 通道最终状态 | Free |
| DUT + Peer 双证据 | 完整 |

pytest 产生一条 `record_property` 与 JUnit xunit2 不兼容的警告，不影响 Case 执行和 PASS 判定；后续可单独统一 JUnit 属性输出方式。

## 原始证据

原始日志和机器可读结果位于项目级目录：

```text
artifacts/review_code_hil/20260808_0653_uart_dma_tx_bf940723/
├── console.log
├── junit.xml
├── session.json
├── uart_p2_001_dma_tx.json
└── cases/<case_run_id>/result.json
```

关键证据：

- `session.json`：运行状态 `PASS`，目标 `et6801`，传输 `serial:COM12@115200`。
- `uart_p2_001_dma_tx.json`：`bytes=32`、`irq_count=1`、`data_match=true`。
- `result.json`：`evidence_complete=true`，证据源为 `dut` 和 `peer`。

## 结论边界

本记录只证明该提交的 PC 端 UART DMA TX 调度与当前 ET6801 FPGA 原型、现有固件和 UART1/UART2 短接环境能够完成真实硬件闭环；不代表 UART 其他 Case、DMA 其他模式或全量回归已在本次执行。
