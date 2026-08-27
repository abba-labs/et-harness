# Final Compliance Closure

文档状态：软件层规则闭环 PASS；硬件 Release Gate 待执行。  
日期：2026-08-07。  
软件实现验证基线：`review_code@62bfc99424d9cf9f94d1069bad26054e7cd173bb`。

## 结论

本轮遵守“冻结核心架构，只允许证据驱动的小范围收敛”，不新增 Workflow Engine、DI、插件系统、通用资源图或额外抽象层。修复优先复用现有 Model / Validation / Codec / Checker / pytest Plugin，以可靠、稳定、轻量为约束。

软件层当前结论为 **PASS**；该结论不包含 Keil Build 或真实 HIL。

主要关闭项：

- UART Formal Case 的 Cleanup 顺序由 Case 显式列出，删除 `cleanup_uart` / `uart_cleanup_scope` 生命周期黑盒；
- 删除 Cleanup Assertion 二次调用风险；
- Runtime Capability 查询与 `pytest.skip` 回到 Formal Case 可见位置；
- Resolver 使用中立 Service ID 合同，Profile/Capability 不再反向依赖 Driver Package 或 TargetClient；
- 永久 PC AST Gate 增加 Profile/Capability 依赖方向检查，防止上述边界回退；
- Formal Case 不再导入 ET-Message Wire Status；UART Driver 将 BUSY 翻译为领域 `OperationBusy`；
- DMA Configure Timeout 使用统一 Primary/Cleanup Error 聚合；
- `EVIDENCE_MISSING` 与统一 Case Result、JUnit/pytest Result、Session Exit Status 保持失败语义一致，不再存在“JSON 失败但进程成功”的双真值；
- DMA 稳定有限集合语义使用与 Firmware Wrap 一致的具名 Enum/Flag；Controller、Channel、Interface、Priority、Address、Count 等动态值继续保持数值类型，避免无意义过度类型化；
- 旧版 LLI Resource Handle 兼容入口只接受显式非零 `uint32` 整数，不再通过 `hasattr()` / 任意对象转换推断业务语义；正式 V2 仍使用直接 Descriptor Address；
- 公共 API 注释不再接受“对应的运行时测试上下文事实”模板；RunContext 与硬件 Fixture 已改为说明实际输入、输出、生命周期、Skip/Failure 语义；
- Unit Test 持续按 Clients / Drivers / Firmware Contract 镜像职责目录；
- 详细计划、Cleanup 规则和最终实现保持同步。

## 轻量化约束

本轮没有为了关闭局部问题增加新的框架层。采取的最小闭环方式为：

```text
明确根因
  -> 在现有职责层内修复
  -> 增加一个窄而稳定的回归检查
  -> 完整 Software Quality Gate
  -> 若 Gate 暴露新问题，修正问题本身而不是增加 allowlist
```

以下做法继续禁止：

- 为局部问题增加 Workflow Engine、DI Container、Plugin System；
- 新建泛化 `common/utils/helpers` 层隐藏业务边界；
- 为所有数值机械包装类型；
- 为让 CI 变绿而降低规则、增加永久豁免或隐藏失败；
- 软件验证替代真实 Build/HIL 证据。

## PC 注释标准

最终标准不是“有注释即可”。Module Docstring 说明模块职责边界；Public API Docstring 说明操作、返回事实或失败语义；Formal Case Docstring 必须说明 Feature、主体、支撑 IP、前置条件、步骤、Evidence、通过条件和 Cleanup。关键 Deadline、Compatibility、Retry Safety 和跨层边界解释为什么这样设计，而不是逐行翻译代码。

永久文档 Checker 只阻止已确认的模板化坏味道和明显缺失，不尝试引入复杂 NLP 规则；语义质量仍由窄规则、单元测试和人工 Review 共同保证。

## 软件验证证据

`Software Quality Gate` Run #391 在 `review_code@62bfc99424d9cf9f94d1069bad26054e7cd173bb` 完成：

- Python syntax：PASS；
- Ruff format：PASS；
- Ruff lint：PASS；
- PC AST architecture rules：PASS；
- PC documentation semantics：PASS；
- Formal Case orchestration rules：PASS；
- Firmware single-IP execution rules：PASS；
- Generated firmware project contract：PASS；
- PC unit / contract / native：`343 passed, 3 skipped`；
- Formal Case collection：PASS；
- Validation 后工作树保持 clean：PASS。

前序 Gate 曾分别暴露 Checker 作用域、Ruff 格式、短 Docstring、非法 Golden Vector 等问题；均修正根因后重新执行全量 Gate，没有通过 allowlist 或放宽生产规则规避失败。

## GitHub 治理边界

当前 `review_code` 的 Software Quality Workflow 已存在并持续运行，但 GitHub Branch Protection / Ruleset 是否将其配置为 Required Check 属于仓库服务端治理配置，不属于源代码修复。本软件 Closure 不以“Workflow 存在”等价替代“服务端不可绕过”。

## 硬件状态

实际 Keil Build 与真实 HIL 仍为 `NOT_EXECUTED`，不属于本轮软件规则闭环的 PASS 证据。只有当前最终代码基线完成对应 Build/HIL 后，才能给出 Hardware Release PASS。
