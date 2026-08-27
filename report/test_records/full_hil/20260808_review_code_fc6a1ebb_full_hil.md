# review_code@fc6a1ebb 全量HIL测试记录

## 测试结论

2026-08-08 12:05 CST，针对 `review_code@fc6a1ebb4590ab5daf5ad2760e27379886ea316d` 执行当前框架可收集的全量硬件测试，结果为 **PASS**：235项中218项PASS、17项按能力或执行映射SKIP、0项FAIL、0项ERROR。

本次未重新配置FPGA bitstream、加载BootROM或擦写PFLASH。Git差异确认该提交与板上已验证固件基线的`firmware/`目录无变化，因此复用板上已有固件。

## 测试环境

| 项目 | 内容 |
|---|---|
| 目标 | XC7VX980T中的ET6801 CORE0 |
| PC代码基线 | `fc6a1ebb4590ab5daf5ad2760e27379886ea316d` |
| 固件标识 | `et6801-silicon-common-v0.1` |
| 控制链路 | `COM12 @ 115200` |
| 功能链路 | UART1与UART2交叉短接 |
| Bench Profile | `pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml` |
| Registry Hash | `6d69ded4` |
| FPGA/BootROM/PFLASH | 本次未重新配置或烧录 |

## 执行范围与结果

| 测试域 | 收集 | PASS | SKIP | FAIL/ERROR |
|---|---:|---:|---:|---:|
| Framework通信 | 1 | 1 | 0 | 0 |
| DMA | 201 | 187 | 14 | 0 |
| UART | 33 | 30 | 3 | 0 |
| 合计 | 235 | 218 | 17 | 0 |

Framework通信完成20轮、60次小/中/大载荷事务。DMA覆盖当前可执行的控制器/通道、传输矩阵、边界、IRQ、LLI、握手、UART外设链路、恢复和长稳Case。UART覆盖轮询、FIFO、波特率/格式、IRQ、9-bit、流控、DMA TX/RX/全双工、恢复及1000轮双向混合长稳。

全部218个PASS Case的`evidence_complete`均为`true`。

## SKIP说明

DMA的14项SKIP全部由当前Bench执行映射决定：UART DMA物理路由只连接到DMA0，因此同一外设链路在DMA1参数上的M2P、P2M、P2P、软件握手、握手模式以及源/目的事务中断Case被明确标记为`skip_by_execution_mapping`。这不是功能失败，也没有以弱断言伪造覆盖。

UART的3项SKIP如下：

| Case | 原因 |
|---|---|
| Framing Error Detection | 当前TX/RX配对没有确定性的帧错误刺激源 |
| Busy Detect IRQ | 当前运行环境无法在Driver有界触发窗口内确定形成Busy Detect条件 |
| Direct FIFO Access | 运行时UART DUT未声明`FIFO_ACCESS` Feature |

## 验证链路

1. 仓库软件质量门禁通过：366 PASS、9 SKIP。
2. Target Smoke通过：HELLO、Build ID、Registry Hash、Service List均匹配。
3. 以显式`--et-hardware`门禁执行Framework、DMA和UART三个正式Case目录。
4. JUnit、Session以及每个Case的结构化结果统一写入项目级`artifacts/`。
5. JUnit确认235项无FAIL/ERROR；Case结果确认所有PASS证据完整。

## 原始证据

```text
artifacts/review_code_full_hil/20260808_1154_fc6a1ebb/
├── console.log
├── junit.xml
├── session.json
├── cases/<case_run_id>/result.json
└── <case_measurement>.json
```

资源受控执行记录：

```text
artifacts/resource-control/tasks/20260808_115352_2b9353db.jsonl
```

## 剩余风险

- 当前外设物理路由只覆盖DMA0，DMA1外设握手链路仍需新的Bench映射才能形成硬件证据。
- Framing Error、Busy Detect和Direct FIFO Access仍受当前板级刺激或运行时能力限制。
- pytest共报告235条`record_property`与JUnit xunit2不兼容警告，不影响本轮Case断言和PASS/SKIP结论，但应在后续统一结果输出契约时处理。
- 本次结论只覆盖当前ET6801 FPGA原型、现有固件和当前UART连接，不外推到其他芯片或其他Bench。
