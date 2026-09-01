# ET6801 UART/DMA 结构化观测与报告 HIL 验证

时间：2026-08-13 17:43 CST

## 1. 验证范围

- 目标芯片：ET6801 FPGA 原型。
- 目标链路：真实硬件/HIL，PC 经 COM12、115200 baud 与目标固件通信。
- 测试 IP：DMA、UART。
- 执行入口：仓库统一配置流水线；仅临时选择 DMA/UART 注册项，执行结束后注册表原样恢复。
- 部署动作：未重新配置 bitfile，未重新加载 BootROM，未重新擦写 PFLASH；复用已运行且身份匹配的固件 `et6801-silicon-common-v0.1`。
- 验证目标：确认结构化硬件观测同时进入 PASS/FAIL 报告，Excel 可回溯到 Case 与原始 JSON，Artifacts 按既定目录治理规则落盘，且未修改已冻结的 Firmware Service/Wrap/Driver、PC Driver、协议和 Backend。

## 2. 执行结果

| 项目 | 结果 | 说明 |
|---|---:|---|
| 软件质量门禁 | PASS | 503 passed，9 skipped；格式、Lint、Contract、Formal/Plan、Firmware Architecture 和 Excel 导出门禁均通过 |
| DMA HIL | PASS | 88 个执行节点通过；汇总为 28 个稳定 Case，28 个 Case 观测完整 |
| UART HIL | PASS（可执行项） | 30 PASS、3 SKIP、0 FAIL；30 个 PASS Case 观测完整 |
| Excel 结构检查 | PASS | DMA/UART 均包含“测试报告、执行明细、规格追溯”3 个工作表；公式错误扫描为 0 |
| Excel 视觉检查 | PASS | 表头、合并区、Case ID、结果、备注和规格追溯均可见，无明显裁切或错列 |
| Artifacts 治理 | PASS | 根目录仅保留 `README.md` 与 `runs/`；本轮输出位于 `runs/YYYY/MM/DD/<run_id>/`，未发现报告或 result/session 文件散落到规则目录外 |
| 冻结层审计 | PASS | 本轮未修改 Firmware Service/Wrap/Driver、PC Driver、Wire Contract、Backend 或 Programmer |

UART 的 3 个 SKIP 属于已声明的环境/能力边界：

1. `UART_P1_008`：当前 TX/RX 板级连接不能构造确定性的 framing error 激励。
2. `UART_P1_012`：当前硬件未能在有界触发窗口内形成确定性的 Busy Detect 条件。
3. `UART_P3_009`：运行时未声明 `FIFO_ACCESS` 能力。

上述项目没有使用弱断言伪造 PASS，也没有计入硬件失败。

## 3. 报告观测核验

- PASS 与 FAIL 使用同一套状态无关的结构化 Observation Contract。
- Case 声明了观测但实际缺失时，报告标记 `EVIDENCE_MISSING`，不会生成“无硬件事实的完整 PASS”。
- 现有 UART/DMA Case 生成的结构化 JSON 通过规范化结果路径绑定到 Case；报告不扫描目录、不解析自由文本、不包含 IP 专用判断。
- Excel 的“测试Case ID”直接对应测试源码稳定 Case ID。
- “备注”同时展示观测附件路径和具体硬件字段；PASS 结果也保留硬件事实。
- 原始 JSON 保留在 Case 目录中，Excel 仅作为人读视图，不替代原始证据。

## 4. 证据路径

- Run ID：`20260813_173531_420089_local_et6801_fpga`
- 运行清单：`artifacts/runs/2026/08/13/20260813_173531_420089_local_et6801_fpga/manifest.json`
- 流水线日志：`artifacts/runs/2026/08/13/20260813_173531_420089_local_et6801_fpga/stages/pipeline/pipeline.log`
- DMA 报告：`artifacts/runs/2026/08/13/20260813_173531_420089_local_et6801_fpga/tests/dma/round_01/20260813_173531_573585/et6801_DMA测试报告.xlsx`
- UART 报告：`artifacts/runs/2026/08/13/20260813_173531_420089_local_et6801_fpga/tests/uart/round_01/20260813_173633_172766/et6801_UART测试报告.xlsx`

## 5. 结论与边界

本轮改动达成预期：结构化硬件观测已进入通用报告链路，DMA 和 UART 可执行 HIL 项全部通过，报告内容和目录结构有效，冻结层未被 IP 专用逻辑污染。

本结论对应未提交工作树和上述固定 Run ID。由于源码状态为 dirty，不得把本报告自动升级为未来提交 SHA 的 CI/HIL 结论；提交后如需发布或合并，仍应对最终 exact SHA 重跑软件门禁与目标 HIL。
