# Profiles

`profiles`只保存PC运行时需要加载的稳定配置和对应加载逻辑，不作为生成文件、
测试需求清单或板卡分析资料的收纳目录。

```text
profiles/
  bench.py                         # Bench强类型加载器
  capabilities.py                  # 芯片Capability稳定公共入口
  _capability_models.py            # 只读模型与查询
  _capability_loader.py            # YAML Schema加载与校验
  bench_topologies/                # 运行时台架连接配置
  chip_capabilities/<chip>/ip/     # 运行时芯片能力YAML
  chip_execution_mappings/         # 芯片能力到公共Driver参数的静态映射
  resolvers/                        # 基于Profile解析公共执行参数
```

与Profile相关、但不属于运行时配置的数据固定放置如下：

```text
tools/capabilities/requirements/                           # 生成器质量门禁使用的Case能力需求
test_case_doc/reference_data/<chip>/boards/                 # 板卡和接口分析JSON
test_case_doc/reference_data/<chip>/capability_generation/  # Capability审计与质量报告
```

新增真实仪器时，其连接参数应进入Bench Topology，并由`instruments`中的具体适配器
加载。不要预先建立没有真实配置和消费者的空Profile分类。
