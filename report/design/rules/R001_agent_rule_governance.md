---
schema: et.rule-document.v1
number: R001
domain: governance
lifecycle: active
owners: [agent_rule_governance]
rule_ids: [ET-RULE-GOVERNANCE]
---

# R001 Agent 开发规则治理契约

## 1. 定位

本文只管理“规则由谁拥有、是否生效、如何路由和如何从门禁诊断追溯到正文”。

它不复制 PC、Firmware、Case、Wire、Capability 或硬件规则正文，也不改变任何业务执行语义。

机器可读的唯一 Owner 与诊断命名空间登记在：

```text
report/design/rule_owner_catalog.yaml
```

Markdown 是规则正文，Catalog 只保存稳定索引；Catalog 不得成为第二份规则正文。

同一 Catalog 的 `documents` 清单负责递归登记 `report/design/**/*.md` 的角色和生命周期。它只保存
`path/role/lifecycle/owners/superseded_by`，不得复制文档内容。

## 1.1 规则文档目录、编号与元数据

所有活动规则正文只能位于：

```text
report/design/rules/Rxxx_<topic>.md
```

编号按稳定责任域分配：

| 编号段 | 责任域 |
|---|---|
| `R000-R099` | 治理与任务导航 |
| `R100-R199` | 公共IP语义、契约和证据 |
| `R200-R299` | PC层、Case与Python质量 |
| `R300-R399` | Firmware Service、Wrap与IRQ |
| `R400-R499` | Wire协议与Capability |
| `R500-R599` | Operator、工具与执行流水线 |
| `R600-R899` | 预留扩展 |

编号发布后不得因排序、改名或插入新规则而重排。一个编号只对应一份正文；只有同一责任域内紧密相关的Owner可以共享该正文。Procedure、Template、Proposal、Record和History不得进入`rules/`，也不得使用`Rxxx`编号。

每份规则正文必须以如下YAML Front Matter开头，并与Catalog完全一致：

```yaml
---
schema: et.rule-document.v1
number: Rxxx
domain: <stable-domain>
lifecycle: active
owners: [<owner-id>]
rule_ids: [<stable-rule-id>]
---
```

标题必须以`# Rxxx `开头。新增责任优先扩展现有Owner；确需新正文时，在所属编号段中选择未使用编号，不得复制相邻规则凑成新文档。

正文面向Agent，必须满足：

1. 一份文档只回答一个责任域问题；相关Owner共享正文时必须使用同一术语和依赖方向。
2. 优先使用“定位、职责/规则、禁止、最小示例、扩展边界、验证”结构；无内容的章节不创建。
3. 用“必须/禁止/允许”表达可执行约束，不写讨论过程、历史争论、阶段结论或未来猜想。
4. 规则后紧跟最小代码、命令或数据示例；示例不得复制完整业务实现。
5. 跨责任域只引用`Rxxx`正文，不复述另一Owner的规则。
6. 单份活动规则正文原则上不超过400行；超过时必须拆分责任，而不是缩写或隐藏关键边界。
7. Front Matter已经表达状态和Owner，正文不重复“状态、更新时间、Owner、Rule ID”。修订历史由Git保存。

## 1.2 源码README边界

源码目录中的README只允许保存目录导航、当前文件用途、稳定命令和指向Rxxx正文的链接。它不得
重新定义跨文件依赖、公共API、Case、Service、Wrap、Wire、Capability、Pipeline或Agent开发规则。

设备或工具README可以记录该设备的具体操作步骤和安全提示，但跨模块通用约束必须引用现有Rxxx
或外层硬件门禁，不得在README形成第二份架构正文。新增README前先确认信息无法由现有入口和
权威规则链接表达。

## 2. 最小治理模型

每个可执行规则责任域必须只有一个稳定 Owner。可静态判定的规则优先由 Checker 失败关闭；
属于公共接口行为的 Contract 可以由现有回归测试保护，不得为了分配诊断码而硬造静态 Checker：

```text
owner
-> stable rule_id
-> lifecycle status
-> one canonical source + heading
-> zero or more diagnostic namespaces
-> responsible Checker files and/or regression tests
```

Owner 表示唯一语义责任，不等于文件、目录、代码层或 Checker 名称。两个规则作用于同一代码层，
但回答不同问题时，可以拥有不同 Owner。

## 3. 文档角色与生命周期

只有以下角色可以形成现行开发约束：

- `kernel`：所有任务必须遵守的少量安全与架构不变量；
- `contract`：一个稳定责任边界的唯一正文；
- `policy`：某类变更或操作必须满足的条件；
- `procedure`：已经决定的工作如何执行；不得重新定义 Contract。

Proposal、Plan、Review、Evidence、Artifact、Template 和历史实现记录都不是现行规则。

规则生命周期固定为：

```text
draft -> active -> deprecated -> superseded
```

- `draft` 不进入 Agent 执行规则包；
- `active` 是当前唯一有效规则；
- `deprecated` 只用于兼容读取，新开发不得继续采用；
- `superseded` 只保留追溯，并必须指向替代规则。

同一个 Owner 不得存在两条 `active` 记录。

`report/design/**/*.md` 必须且只能登记一次。只有 `active kernel/contract/policy` 可以绑定 Owner；
Procedure、Template、Proposal、Record 和 History 不得认领规则 Owner。`deprecated/superseded`
必须指向真实替代来源，Agent 不得再把它当成现行规则读取。

## 4. 诊断命名空间规则

诊断码用于把机器门禁失败精确路由到唯一 Owner，不代表每个诊断码都是一份独立规则。

固定要求：

1. 一个诊断码只能由一个 Checker 文件发出；
2. 一个诊断码必须且只能落入 Catalog 的一个命名空间；
3. 一个命名空间只属于一个 Owner；
4. 新诊断优先进入现有 Owner 的保留区间；
5. 新建命名空间前必须先证明现有 Owner 无法表达该职责；
6. 错误信息应包含诊断码、目标路径和具体事实，不得只输出自由文本；
7. 修改诊断编号必须同步 Checker 回归测试和 Catalog；不得静默复用旧编号表达新语义。

命名空间只负责追溯，不要求按文件拆分 Checker。一个 Checker 可以检查多个 Owner，但每个诊断仍必须
映射到唯一 Owner。

## 5. 规则变更闭环

新增或修改规则必须按以下顺序完成：

```text
问题证据
-> 确认现有 Owner
-> 现有 Owner 可表达：扩展唯一正文
-> 无 Owner：先形成 draft 和影响分析
-> 用户批准新增 Owner
-> 更新唯一正文与 Catalog
-> 同步 Checker / Review Gate / 回归测试
-> 旧规则标记 superseded
-> 最后切换 active
```

禁止在功能修复中顺手新增规则、公共层、Adapter、Registry、Protocol 或通用框架。

## 6. Agent 执行要求

Agent 遇到门禁错误时：

1. 静态 Checker 失败时，先根据诊断码在 Catalog 找到唯一 Owner；
2. 行为回归测试失败时，根据 Catalog 的 `tests` 反查唯一 Owner；
3. 只读取 Catalog 指向的正文和标题；
4. 修改违反规则的实现，不得为通过门禁而弱化 Checker 或回归测试；
5. 若失败无法映射 Owner、落入多个 Owner 或正文锚点不存在，停止规则相关修改并报告治理缺口；
6. Proposal、Review 和 superseded 文档不得用于覆盖 active Owner。

Catalog 或治理校验失败时必须失败关闭。Agent 不得自行从文件名、目录或历史文档猜测有效规则。

## 7. 机器门禁

统一门禁：

```powershell
python tools/quality/validate_rule_governance.py
python tools/validate_pc.py
```

治理 Checker 只验证：

- Owner、Rule ID 和 active 唯一性；
- Canonical source 与 heading 存在；
- 诊断命名空间不重叠；
- 当前 Checker 诊断码无跨文件冲突；
- 每个当前诊断码唯一映射到一个 active Owner；
- Catalog 声明的 Checker 文件真实存在；
- 没有 Checker 的 Owner 必须声明真实存在的回归测试；
- Catalog 显式声明的机器契约标记只存在于该 Owner 的唯一规范正文。
- 每份 `report/design/**/*.md` 都有唯一角色和生命周期登记；
- 活动规则正文的目录、编号、Front Matter、标题、Owner和Rule ID相互一致；
- Owner正文与Document Inventory双向一致；
- 失效文档具有真实替代来源。

它不解析或执行规则正文，不成为通用策略引擎，也不修改任何文件。

## 8. 轻量化红线

当前禁止引入：

- 数据库、常驻规则服务或通用策略 DSL；
- LLM 参与规则路由或门禁 PASS/FAIL；
- 每个 IP 一套规则目录；
- 每个诊断码一份规则文档；
- 自动改写规则正文；
- 与 `tools/validate_pc.py` 平行的第二套总门禁。

后续规则扩展必须优先增加一条 Catalog 记录或扩展现有 Owner，而不是继续堆叠文档。
