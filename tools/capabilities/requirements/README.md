# Capability Requirements

这里保存Capability生成器质量门禁所消费的Test Case语义需求，不属于PC运行时Profile，
也不保存芯片能力或寄存器描述。

- 一个测试等级一个 YAML，例如 `dma_p0.yaml`。
- 清单跨芯片复用，不得写芯片名、实例地址或寄存器字段名。
- 只列 Case 在运行前必须查询的能力；新增依赖必须显式增加，已发布依赖不得静默删除。
- 生成器使用 `--requirements-file` 将清单接入质量门禁；能力不存在或没有 Evidence 时失败。

框架通信压测不消费芯片 IP Capability，因此没有空清单。
