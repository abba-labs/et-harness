# 平台公共层冻结前软件收口Review

时间：2026-08-10 14:45 CST
分支：`review_code`
基线：`d2de2836e72f55652a6474869263c305db188aa1`
范围：PC公共层、UART/DMA/Framework Driver与Formal Case、质量门禁和当前文档

## 结论

本地软件收口已完成，计划中的扩展边界、Deadline/Cleanup、Evidence、Case分级、硬件规模解耦和文档一致性问题均已落实，并通过统一软件质量门禁。

当前结论仅为本地软件PASS。当前差异尚未推送形成exact-SHA CI证据，也未经过实际Keil Build和真实UART/DMA/Framework HIL，因此公共层暂不标记为`FROZEN`。

## 已完成整改

- 公共`scheduling/`不再持有UART/DMA专用Fixture、Support和固定Service映射；IP Service Gate归属各自Case Package。
- `test_cases/<ip>/conftest.py`和`_support.py`可构造Driver、执行Capability/Runtime/Bench/Resolver Gate，但Checker禁止其执行Feature动作和最终断言。
- Required Evidence改为通用`dut/peer/fpga/instrument`元数据，不再依赖UART Fixture名称；setup/call/teardown失败合并保留。
- DMA/UART轮询共享单个`OperationDeadline`；Cleanup覆盖`BaseException`；Framework重新发现失败后不保留旧Registry。
- UART/DMA/Framework Case完成P0～P3迁移并冻结新ID；历史ID对照单独归档。
- DMA普通Feature使用Capability/Runtime交集选择代表实例；全通道Case按运行时`channel_count`遍历；最大边界按运行时上限计算。
- Case Evidence复用真实比较变量，不记录第二份literal真值；UART/DMA初始化和Capture Cleanup按实际所有权收口。
- Firmware manifest验证改为发现`firmware/chips/*/project.yaml`，新增芯片不修改公共验证入口。

## 本地验证

```text
Python syntax                         PASS
Ruff format / lint                    PASS
PC AST architecture rules             PASS
PC documentation semantics            PASS
Formal Case orchestration rules        PASS
Firmware single-IP execution rules     PASS
ET6801 generated project contract      PASS
PC unit / contract / native            397 passed, 9 skipped
Formal Case collection                 121 nodes
git diff --check                       PASS
```

统一入口：

```powershell
.\.venv\Scripts\python.exe tools\validate_pc.py
```

## 剩余风险与下一步

1. 推送后执行远端exact-SHA Software Quality Gate。
2. 在独立硬件门禁下执行实际Keil Build。
3. 对UART生命周期变化、DMA Deadline/Cleanup及Framework通信执行针对性HIL，再执行UART、DMA、UART-DMA和Framework全量HIL。
4. 只有CI和HIL证据都绑定当前SHA后，才把公共层标记为`FROZEN`。

## 2026-08-10 17:40 CST 冻结前复审修正

本次复审发现并收口了两个公共层问题：

- Runtime Service Gate不再为缺少`runtime_services`的Unit Test Fake静默放行；测试替身必须满足正式Fixture合同。
- Capability公共导入保持不变，内部按“只读模型/查询”和“YAML Schema加载/校验”拆分，不增加Manager、Registry或Factory。

规模约束按`pc_code_design_rules.md`第12节进行人工Review。以下项目保留明确例外，不为满足行数机械引入Mixin、BaseDriver或隐藏Case流程：

| 对象 | 当前规模 | 承担职责 | 保留原因与约束 |
|---|---:|---|---|
| `drivers/uart/driver.py` | 1033行 | UART单IP原子操作、Deadline和单IP生命周期 | 方法数量来自UART Feature数量；未混入其他IP、Profile、pytest或跨IP流程。拆成Mixin/代理会增加调用跳转和维护成本，因此保持单Driver，并继续由依赖门禁限制职责。 |
| `drivers/dma/driver.py` | 609行 | DMA单IP原子操作、IRQ等待和单IP生命周期 | 仅比原则上限多9行且没有职责混入；不为9行差异制造无语义子模块。 |
| UART/DMA三个超150行Case | 156～220行 | 明示跨IP准备、执行、Evidence、断言和Cleanup顺序 | 流程本身是被Review对象；抽入Helper会隐藏关键测试动作。继续由Case编排门禁禁止Codec/Transport调用和完整流程下沉。 |

上述例外不扩大公共核心冻结范围。Driver和Formal Case仍是按IP演进的扩展层；任何新增超限对象仍需单独Review，不得引用本表作为通用豁免。

2026-08-10 17:51 CST，本轮软件验证结果：

```text
Runtime Service/Fixture针对性测试       17 PASS
Capability/Profile针对性测试            43 PASS
文档与Case注释门禁针对性测试             12 PASS
统一软件质量门禁                         410 PASS、9 SKIP
Formal Case收集                          121项
Clean Wheel                              160 entries、0 forbidden
Keil/HIL                                 NOT_EXECUTED
exact-SHA CI                             PENDING
```

本轮未修改Wire、Firmware、Driver命令顺序、Deadline/Cleanup或硬件执行语义。公共层在形成干净提交并取得exact-SHA CI前仍保持`PENDING`，不得仅依据本地软件PASS标记为`FROZEN`。
