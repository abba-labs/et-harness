# Reference Data

这里保存IP Feature与Case规划所依赖、但不应进入PC运行时Python包的结构化参考数据。

```text
reference_data/<chip>/
  boards/                 # 板卡接口、电源域和接插件分析JSON
  capability_generation/  # Capability生成审计与质量报告
```

运行时芯片能力仍以
`pc/et_test_platform/profiles/chip_capabilities/<chip>/ip/*.yaml`为唯一来源。
参考数据不得由Test Case在运行期间直接读取。
