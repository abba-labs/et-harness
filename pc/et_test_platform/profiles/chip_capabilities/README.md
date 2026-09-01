# Chip Capabilities

本目录保存打包发布的芯片IP能力YAML：

```text
chip_capabilities/<chip>/ip/<ip>.yaml
```

运行时通过`load_packaged_chip_capabilities(<chip_id>)`加载并缓存只读能力索引。Case使用
稳定语义查询，不读取YAML路径或寄存器字段：

```python
capabilities.has_feature("dma", "linked_list", instance="dma0")
capabilities.limit("dma", "max_block_transfers", instance="dma0")
capabilities.options("dma", "transfer_types", instance="dma0")
capabilities.interrupt("dma", "transfer_done", instance="dma0")
```

板卡资料和Capability生成审计位于`test_case_doc/reference_data/<chip>/`，不进入运行时包。
Capability生成、证据、语义命名、人工覆盖和失败关闭规则只由
[R410 Capability v2](../../../../report/design/rules/R410_capability_v2.md)定义。
