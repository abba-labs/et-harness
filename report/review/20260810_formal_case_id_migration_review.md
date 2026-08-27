# Formal Case P级别与ID迁移记录

时间：2026-08-10 14:20 CST
基线：`review_code@d2de2836e72f55652a6474869263c305db188aa1`
范围：UART、DMA、Framework Communication Formal Case

## 结论

本次是公共层冻结前唯一一次正式P级别纠正。迁移完成后，Case ID作为测试记录、Evidence和回归选择器的稳定标识，不再因文件排序或代码整理修改。历史HIL和报告继续引用旧ID，不回写历史记录。

## 迁移对照

| 旧Case ID | 新Case ID | 原因 |
|---|---|---|
| `uart_p0_005_line_format_matrix` | `uart_p1_014_line_format_matrix` | 帧格式矩阵属于常规配置Feature |
| `uart_p0_006_baudrate_matrix` | `uart_p1_015_baudrate_matrix` | 波特率矩阵属于常规配置Feature |
| `uart_p0_007_fifo_boundary_and_status` | `uart_p1_016_fifo_boundary_and_status` | FIFO边界属于常规Feature |
| `uart_p0_008_invalid_parameter_rejection` | `uart_p1_017_invalid_parameter_rejection` | 标准非法参数路径属于P1 |
| `uart_p2_009_long_run_mixed_transfer` | `uart_p3_010_long_run_mixed_transfer` | 长稳压力属于P3 |
| `dma_p0_003_m2m_width_address_matrix` | `dma_p1_014_m2m_width_address_matrix` | 位宽/地址模式矩阵属于常规Feature；避开既有P1-002 |
| `dma_p0_004_block_and_burst_boundaries` | `dma_p1_015_block_and_burst_boundaries` | Count/Burst边界属于常规Feature；避开既有P1-003 |
| `dma_p0_005_memory_region_matrix` | `dma_p1_016_memory_region_matrix` | Guard与IRQ组合路径属于P1 |
| `dma_p0_006_invalid_parameter_rejection` | `dma_p1_017_invalid_parameter_rejection` | 标准非法参数路径属于P1 |
| `dma_p2_016_long_run_mixed_transfer` | `dma_p3_007_long_run_mixed_transfer` | 长稳压力属于P3；避开P3-001～006设计保留项 |
| `test_framework_echo_stress` | `test_framework_communication_p3_001_echo_mixed_payload_stress` | Framework压力Case统一进入P3命名体系 |

## 固定规则

- P0只保留基本可用性、身份、初始化和最小数据路径。
- P1承载常规配置矩阵、中断、FIFO、标准边界和标准异常。
- P2承载高级Feature、复杂执行路径和跨IP配测。
- P3承载长稳、压力、性能和特殊环境测试。
- 新增Case只使用对应等级内新的未占用ID，不复用本表旧ID。
- 结果文件名、`record_result()` Case ID和pytest函数名必须使用同一个新ID。

## 验证状态

软件收集、规则检查和单元测试将在本轮代码收敛完成后统一执行；真实HIL需要独立硬件门禁，不能由本迁移记录替代。
