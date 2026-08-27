# Formal Test Cases

本目录保存真正的pytest测试场景。Case负责显式编排Driver、执行最终断言并记录Evidence；主流程优先使用直接Driver调用和显式`try/finally`，只有确实需要保证多步清理全部尝试时才使用一个最外层`case_cleanup_scope`。Case不按芯片、硅前/硅后或IP实例复制测试代码，完整职责与清理规则以[R210 Formal Case规则](../../../report/design/rules/R210_pc_case_responsibility.md)为准。

## 固定结构

```text
test_cases/
├── ip_registry.py
├── framework_communication/
│   ├── case_registry.py
│   └── test_framework_communication_p3.py
├── dma/
│   ├── case_registry.py
│   ├── conftest.py
│   ├── _support.py
│   ├── dma_helpers.py
│   ├── dma_irq_helpers.py
│   ├── test_dma_p0.py
│   ├── test_dma_p1.py
│   ├── test_dma_p2.py
│   ├── test_dma_p3.py
│   └── deferred_features.py
└── uart/
    ├── case_registry.py
    ├── conftest.py
    ├── _support.py
    ├── uart_helpers.py
    ├── test_uart_p0.py
    ├── test_uart_p1.py
    ├── test_uart_p2.py
    ├── test_uart_p3.py
    └── deferred_features.py
```

`ip_registry.py`是平台级IP显式白名单；每个IP的`case_registry.py`是该IP正式Case显式白名单。只有同时注册的IP和Case才会进入pytest执行集合。未注册Case使用pytest标准`DESELECTED`语义，不执行、不访问Fixture，也不伪装成SKIP。

注册表只保存稳定Case ID，不导入Case函数，不保存Driver、Capability、Runtime Service或硬件状态。pytest收集完成后先校验IP、Case ID、P等级和`ip(name)` Marker，再过滤未注册项；现有硬件人工门禁仍独立生效。

`framework_communication/`中的`stress_case.py`只保存确定性的压力计划、Payload生成和统计辅助，不执行I/O，也不隐藏Case流程；P级文件仍是唯一正式Case入口。

- `test_<ip>_p0.py`：基本可用性和最小数据路径。
- `test_<ip>_p1.py`：常规Feature、配置矩阵和标准异常。
- `test_<ip>_p2.py`：高级Feature、复杂执行路径和跨IP配测。
- `test_<ip>_p3.py`：长稳、压力、性能和特殊环境。
- `conftest.py` / `_support.py`：只构造Driver并完成Runtime、Capability、Bench和Resolver Gate，不执行Feature动作或最终断言。
- `deferred_features.py`：尚不能形成可靠证据链的Feature计划，不伪装成pytest SKIP。

Case ID迁移见 [Formal Case P级别与ID迁移记录](../../../report/review/20260810_formal_case_id_migration_review.md)。完整写法遵循 [R210 Formal Case规则](../../../report/design/rules/R210_pc_case_responsibility.md)。

硬件Case默认不执行；只有显式提供`--et-hardware`、Bench Profile和证据目录后才允许操作真实设备。
