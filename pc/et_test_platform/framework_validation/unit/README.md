# Framework Unit Test Layout

本目录只保存跨平台PC框架的单元、契约与Native Harness测试。根目录仅保留pytest公共入口，测试文件按被测职责放置：

| 目录 | 职责 |
|---|---|
| `baseline/` | 已冻结公共API、Wire与可靠性基线 |
| `clients/` | TargetClient与目标连接创建 |
| `code_quality/` | 源码、文档、目录和治理门禁 |
| `communication/` | ET-Frame、C Golden Vector与Transport |
| `core/` | Deadline、Cleanup与Result核心模型 |
| `drivers/<ip>/` | 对应IP Driver、Codec与Wire契约 |
| `cases/common/` | Formal Case注册、清理和公共约束 |
| `cases/<ip>/` | 对应IP Case、Fixture和Support契约 |
| `firmware_contract/` | Firmware架构、配置与Native Harness |
| `instruments/` | 外部仪器Driver与操作契约 |
| `operator/` | 一键入口、运行配置与工具布局 |
| `profiles/` | Capability、Bench、Mapping与生成器 |
| `results/` | Observation、Canonical Result与报告转换 |
| `scheduling/` | Fixture、连接与RunContext |

新增测试应放到被测模块对应目录，不按修复批次、日期或单个问题新建目录。跨层测试按主要责任归属；只有确实验证Firmware C实现或Native Harness时才进入`firmware_contract/`。
