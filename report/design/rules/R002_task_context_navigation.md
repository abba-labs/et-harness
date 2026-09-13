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
本任务仍必须拒绝。`artifacts/runs/`、`artifacts/reports/`和`artifacts/records/`属于生成证据，不进入源码范围检查；其发布和保留边界仍受R500约束。

Task Context中的任务声明、仓库身份、输入摘要、规则Owner、读写范围和验证入口必须由编译器写入完整性摘要；
`check`必须在任何治理输入豁免前验证该摘要。Scope baseline必须保存编译时的`write_scope`并与Context完整性摘要交叉校验；
`scope-check`只能使用该编译时授权快照判断变化，不能直接信任运行期JSON中后来改写的`allowed/protected`。

治理任务可能依法修改当前Context引用的规则或模块画像；此时原Context及原写入范围继续作为本任务固定边界。
只有当前Git branch/HEAD未变化、原Context完整性有效且Scope baseline仍与原授权一致时，
才允许已位于原`allowed`范围内的输入变化继续使用原Context；不得采用修改后的宽泛范围。
任务完成并恢复干净工作树后，后续任务再重新编译。

单IP任务只能修改该IP被路由的文件；多IP任务必须遵守第3.1节逐IP声明边界。
未声明IP及冻结公共层默认只读。发现范围外缺陷时必须停止相关修改，提交证据并取得用户明确批准；
批准后建立独立Task Context和独立Commit，不得将无关修复混入原任务，也不得组合宽泛模块绕过保护范围。

任何执行真实芯片IP测试并形成Case结论的任务，必须为每个被测IP选择`ip-package/test-result`并传入`--chip`；
单IP使用`--ip`，多IP按第3.1节逐项声明`test-result`。
该路由只授权更新对应`<CHIP>_<ip>.md`的当前状态，不授权修改Case、Driver、Service、Wrap或其他IP。

### 3.1 显式多IP任务

允许把同一接入或修复目标所必需、且已获用户授权的多个IP放入一个Task Context和逻辑提交。
例如新增IP依赖CRG复位、GPIO复用，或一个芯片映射需要同步多个IP文档。不得因此授权全部IP。

- 旧单IP入口`--ip <ip> --change <kind>`保持不变。
- 多IP使用可重复的`--ip-scope <ip>:<change>[,<change>...]`；每个IP只展开自己声明的change，禁止交叉套用。
- `--ip-scope`必须选择`ip-package`，禁止与`--ip`混用。此时`--change`只用于其他模块。
- IP和change必须是明确标识；禁止通配符、路径、空项、重复IP、重复change、未知change或缺少必要参数。
- 只需同步已有契约时使用`contract-sync`：只允许该IP的公共文档和指定芯片文档，不授权Case、Driver、Service、Wrap或Capability文件；新IP分析仍使用`analysis`。
- 编译器合并各范围的必读来源、Owner和验证入口并去重；`protected`优先、干净Git基线、Diff检查、完整性摘要和人工硬件门禁均不改变。
- `task.ip_scopes`进入任务指纹；修改IP或change必须按扩围流程重新编译，禁止修改runtime JSON。
- Agent必须逐项核对用户授权；填写`--ip-scope`不是取得授权，编译器也不自行推断依赖或批准。

```powershell
python tools/governance/compile_task_context.py compile `
  --task-id SPI-CRG-ADAPT --intent "已批准：补齐CRG的SPI映射并同步SPI文档" `
  --module ip-package --chip et6801 --lane firmware `
  --ip-scope crg:wrap,driver,capability,chip-driver `
  --ip-scope spi:contract-sync
```

该示例不允许修改SPI Case/Service、GPIO或其他IP；新增依赖仍须单独授权并明确加入范围。

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
- 目标 CHIP/IP 的 `current/publication.json` 为 `pending_review=true`，且本次不是唯一的
  `operator-pipeline/knowledge-review` 时，compile 必须失败关闭且不得写入 Context JSON。
  探测只读该 JSON：缺文件不当 pending；禁止 `verify_publication`，禁止全树扫描。
  目标来自 `--ip` / `--ip-scope` / 仅 `--chip` 时的 `_PIPELINE` 与 `test_workspaces`。
  `governance` 与已有 `*/docs` 豁免；能写 Driver/Firmware/Case/Runner 的模块无点名目标时必须失败。
  `knowledge-review` 只作跳过补救，不豁免干净树，禁止 fpga/hil 与其它 change 混编：
```powershell
.\.venv\Scripts\python.exe tools\governance\compile_task_context.py compile `
  --task-id <id> --intent "<intent>" `
  --module operator-pipeline --change knowledge-review `
  --chip <CHIP> --ip <IP>
```
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
