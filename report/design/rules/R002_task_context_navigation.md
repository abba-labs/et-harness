---
schema: et.rule-document.v1
number: R002
domain: governance
lifecycle: active
owners: [task_context_navigation]
rule_ids: [ET-RULE-TASK-CONTEXT]
---

# R002 Agent Task Context 导航规则

## 1. 定位与边界

本文只规定一次工程任务如何从任务描述确定性路由到工程模块、代码入口、规则Owner、写入边界和验证入口。

它不保存项目当前状态，不复制业务规则正文，不替代`project-control`，也不根据自然语言自动猜测模块和权限。

## 2. 强制执行链路

每个新的非平凡工程任务，以及任务发生实质扩围时，Agent必须重新执行：

```text
理解任务
  -> 从system-map选择模块
  -> 选择change kind
  -> 编译Task Context
  -> 阅读must_read和rule_owners
  -> 确认allowed/protected scopes
  -> 检查目标符号及相邻责任链
  -> 开发
  -> Task Scope检查
  -> 专项验证
  -> 逻辑批次完成
  -> 仓库总软件门禁
```

持续对话不豁免本规则。任务扩展到新模块、新责任或新芯片适配范围时，必须重新编译Task Context。
扩围前先对已经完成的变化运行Scope检查，再编译扩围后的新上下文；禁止通过重新编译隐藏越界变化。

Task Context必须在第一次写入前由干净Git工作树编译。编译器不得把已有源码变化收养为本任务基线；
工作树不干净时，Agent必须停止并区分用户变化、前序任务变化和待处理变化，不得使用重新编译绕过范围检查。

### 2.1 验证范围与门禁时机

验证范围必须服从用户明确指令，并限制在当前Task Context和实际Diff的影响边界内：

```text
用户指定的Case/IP/问题批次
  -> Task Context允许范围
  -> 实际Diff直接影响范围
  -> 本轮专项验证范围
```

- 用户指定Case时只验证该Case；指定IP时只验证该IP；指定问题批次时只验证该批次直接影响的Case/IP。
- 只有用户明确要求全量，或任务属于发布、冻结、最终验收时，才执行全部IP HIL。Registry表示可选全集，不表示每次必须全量运行。
- 修改公共层时，按Task Context补充公共专项验证和代表性已有IP回归；未经用户明确要求，不得自动扩大为全部IP HIL。
- 仓库总软件门禁只验证软件质量，不等于全部IP HIL。

开发过程以逻辑批次收口，不按每次保存或少量改动重复运行总软件门禁。逻辑批次包括：

1. 一个IP的本轮代码开发完成；
2. 一组同类Bug修复完成；
3. 一项公共契约、公共层或工具链变更完成。

批次内部先执行目标文件、目标模块或目标Case的最小专项验证。完整总软件门禁必须在以下时点执行一次；同一源码状态已经通过时不得重复执行：

1. 逻辑批次完成；
2. Commit或Push前；
3. 用户明确要求；
4. 公共Framework、Wire、Capability Schema、Canonical Result/Report Schema、Runner或部署流程发生变化。

有效变更达到300行时，当前逻辑步骤完成后必须收口该批次并运行总软件门禁，不得继续叠加新的独立修改。有效变更按新增行与删除行之和统计，包括源码、配置、规则和工具；不统计Artifact、生成文件、日志、普通说明文档和第三方代码。行数只作兜底：高风险公共变更即使不足300行仍按上述第4项执行，未完成的函数或原子操作不得为凑门禁时点被中途截断。

## 3. 标准命令

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py compile `
  --task-id <stable-task-id> `
  --intent "<one-sentence intent>" `
  --module <module-id> `
  --change <change-kind> `
  [--ip <ip>] [--chip <chip>] [--lane <lane>]
```

执行开发前应确认：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py check
```

开发完成、运行专项验证前必须确认本任务新增变化全部位于`write_scope.allowed`：

```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py scope-check
```

Scope检查以Task Context编译时的干净Git工作树快照为基线，只接受`write_scope.allowed`内的变化。
`write_scope.protected`优先于`allowed`：任一已选模块声明为保护范围的路径，即使另一模块给出宽泛允许范围，
本任务仍必须拒绝。`artifacts/runs/`和`artifacts/reports/`属于生成证据，不进入源码范围检查。

Task Context中的任务声明、仓库身份、输入摘要、规则Owner、读写范围和验证入口必须由编译器写入完整性摘要；
`check`必须在任何治理输入豁免前验证该摘要。Scope baseline必须保存编译时的`write_scope`并与Context完整性摘要交叉校验；
`scope-check`只能使用该编译时授权快照判断变化，不能直接信任运行期JSON中后来改写的`allowed/protected`。

治理任务可能依法修改当前Context引用的规则或模块画像；此时原Context及原写入范围继续作为本任务固定边界。
只有当前Git branch/HEAD未变化、原Context完整性有效且Scope baseline仍与原授权一致时，
才允许已位于原`allowed`范围内的输入变化继续使用原Context；不得采用修改后的宽泛范围。
任务完成并恢复干净工作树后，后续任务再重新编译。

目标IP任务只能修改该IP的Case、Driver、Service、Wrap、公共IP文档和明确路由的芯片适配文件。
其他IP及冻结公共层默认只读。发现其他IP或公共层缺陷时必须停止当前任务，提交证据并取得用户明确批准；
批准后使用独立Task Context和独立Commit处理，不得把它并入当前IP任务，也不得通过组合宽泛模块扩大权限。

任何执行真实芯片IP测试并形成Case结论的任务，必须同时选择`ip-package/test-result`并传入`--ip --chip`。
该路由只授权更新对应`<CHIP>_<ip>.md`的当前状态，不授权修改Case、Driver、Service、Wrap或其他IP。

## 4. 失败关闭规则

- 未知模块、未知change、未知Owner、缺少必需参数或必读来源不存在时，编译必须失败。
- Git工作树不干净时不得编译新的Task Context；有源码变化但缺少Task Context时，总软件门禁必须失败。
- `protected`范围发生变化时必须失败；不得由另一模块的`allowed`范围覆盖。
- Task Context完整性摘要、Scope baseline授权快照或两者的交叉绑定不一致时必须失败；不得原地修改runtime JSON扩大权限。
- Agent不得从相似文件名、历史记录或个人记忆猜测缺失路由。
- 生成的`project-governance/runtime/current_task_context.json`只是临时派生导航，不是规则、状态或证据。
- `lane`只记录并校验任务通道，不代替`module/change`授权；允许值由`system-map.yaml`唯一登记。
- 选择`fpga`或`hil` Lane且任务不只是回写`test-result`时，必须同时选择
  `operator-pipeline/pipeline`，使R500、统一入口和硬件执行边界进入Task Context；编译器必须失败关闭。
- 新IP必须先单独执行`ip-package/analysis`创建并审核公共契约，之后才能编译Case、Driver、Service、Wrap或Capability任务。
- 简单事实回答和不检查、不改变工程状态的状态说明可以豁免；代码、配置、规则、工具、架构和持久文档变更不得豁免。

## 5. 轻量化与扩展规则

- 只允许显式模块画像和规则Owner ID，不引入图数据库、向量数据库、LLM规则路由或第二套工作流引擎。
- 新增IP或芯片通常只传入`--ip`或`--chip`，不得复制模块画像。
- 新增工程模块时，只增加一个单一职责画像并登记一次system-map。
- 只有现有Task Context字段无法表达新的跨模块通用事实时，才允许评审Schema变更。
- 不增加可由Agent自行填写的“批准字符串”或Allowlist例外；人工批准通过新的独立任务边界表达，机器门禁仍按最小范围失败关闭。

## 6. 验证与追溯

```powershell
python tools/governance/compile_task_context.py validate
python tools/governance/compile_task_context.py scope-check
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_task_context_governance.py
python tools/validate_pc.py
```

Owner、规则ID、正文和回归测试的唯一关系由`report/design/rule_owner_catalog.yaml`登记。
