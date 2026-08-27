# ET 自动化测试平台公共层冻结收口

时间：2026-08-11
状态：软件架构 FROZEN
基线：`review_code@25165e63d93e296d19cea3f084c0396240f18a2d`

## 1. 冻结结论

公共软件架构已经完成冻结前最后一轮收口，后续普通 IP 开发不得再以“简化 Case”或“新增 IP”为理由修改公共运行机制。

冻结模型固定为：

```text
Case = Test Flow + Evidence + PASS/FAIL + Cross-IP Cleanup Order
Support = Runtime/Capability/Bench/Resolver Gate + Driver Construction
Driver = One-IP Behavior + Deadline/Polling + Necessary One-IP Lifecycle
Codec = Pure Wire Encode/Decode
TargetClient = Common Request/Response
Firmware Service = Decode + Own Wrap + Encode Facts
Wrap = Own IP Chip Driver
```

## 2. 冻结范围

以下公共软件语义进入 FROZEN：

```text
pc/et_test_platform/core/**
pc/et_test_platform/clients/**
pc/et_test_platform/communication/**
pc/et_test_platform/scheduling/**
pc/et_test_platform/results/**
通用 Capability Model/Loader
通用 Deadline/Cleanup/Evidence/Result 机制
Formal Case 收集与稳定 ID 机制
```

后续新增 ADC、CAN、SPI、I2C、TIMER 等普通 IP，PC 侧主要变化范围应为：

```text
drivers/<ip>/**
test_cases/<ip>/**
```

允许在以下组合点增加本 IP 条目，但不得改变公共机制：

```text
test_cases/ip_registry.py
Firmware Service 聚合注册处
Firmware Application/Board 实例声明
Keil 工程生成配置
```

## 3. 最终规则真值

### Case

- 目录按主要测试 IP 归属；
- 文件按 P0～P3 等级组织；
- 文件内部按 Feature 分区；
- Case 前固定使用中文 `#` 三段说明：测试 Feature、测试方法、通过条件；
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
- DMA IRQ 当前继续使用 Case 显式 Cleanup，没有 `dma.irq_mode()`。

### Wire/Firmware

- UART/DMA 保持已发布 V1 Wire Shape 和 Command ID；
- 废弃同步等待 Command ID 只保留兼容占位并返回 `NOT_SUPPORTED`；
- V1 poll-budget 字段只用于 Wire 兼容，真实 Deadline/Polling 仍由 PC Driver 负责；
- Firmware Service 不执行完整 Case、不跨 IP 编排、不形成最终 PASS/FAIL。

## 4. 当前软件验证

exact-SHA Software Quality Gate：

```text
SHA                                    25165e63d93e296d19cea3f084c0396240f18a2d
Workflow                               Software Quality Gate #583
Python syntax                          PASS
Ruff format / lint                     PASS
PC AST architecture rules              PASS
PC documentation semantics             PASS
Formal Case orchestration rules         PASS
Firmware single-IP execution rules      PASS
Generated firmware project contract     PASS
PC Unit / Contract / Native             423 passed, 3 skipped
Formal Case collection                  122 nodes
Repository clean after validation       PASS
```

Formal Case 节点分布：

```text
DMA P0                   2
DMA P1                  63
DMA P2                  22
DMA P3                   1
Framework Communication  1
UART P0                   4
UART P1                  17
UART P2                   9
UART P3                   3
---------------------------
Total                   122
```

## 5. 硬件证据边界

仓库已有上一轮公共层收口的真实硬件记录：

```text
Framework/UART/DMA 全量 HIL：118 PASS / 3 SKIP / 0 FAIL
FPGA Keil Target：PASS
SILICON Keil Target：PASS
```

对应记录：`report/validation/dut/20260810_et6801_pc_firmware_freeze_full_hil.md`。

但最终软件 SHA 在此后又恢复了 V1 Wire 兼容字段并补充 DMA 首/末 Channel 边界覆盖，因此**不得把上一轮 HIL 表述为最终 SHA 的 exact-SHA HIL PASS**。

当前最终 SHA 的硬件状态保持：

```text
Keil / HIL exact-SHA regression    NOT_EXECUTED / NOT_VERIFIED
```

该状态不改变“公共软件架构已冻结”的治理结论，但任何硬件发布或运行时等价性声明仍必须引用实际执行的对应 HIL 证据。

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
