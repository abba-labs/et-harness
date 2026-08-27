# Rule Interface Standard v0.1

> 标准 ID：`rule-v0.1`  
> Node 前缀：`R`  
> 主文件格式：`NNN_<name>.md`  
> 继承：`Project Resource Routing Meta Standard v0.1`

## 1. 本标准只规定规则接口

Rule Manager 不规定项目应该有哪些规则类别，也不规定应该有多少规则文件。

项目自行设计规则分类。

公共标准只保证：

```text
00_INDEX.md
   ↓
NNN_*.md
   ↓
Rxxx 编号规则树
   ↓
Rule Leaf
```

---

## 2. `rules/00_INDEX.md` 是唯一机器入口

必须存在：

```text
rules/00_INDEX.md
```

YAML Front Matter 是正式路由接口：

```yaml
---
interface: project-resource-index-v0.1
resource: rules
standard: rule-v0.1
files:
  - id: R010
    file: 010_xxx.md
    title: <短标题>
    summary: <一句话>
    aliases: [<route-hint>, <route-hint>]
---
```

要求：

```text
Index 覆盖全部正式规则文件
id / file / title / summary / aliases 必须完整
Markdown 正文只用于可选说明，不参与机器路由
```

公共 Rule Manager 正常查询不得默认全文扫描全部规则文件。

---

## 3. 文件命名与 File ID

```text
010_xxx.md → R010
020_xxx.md → R020
```

要求：

```text
三位数字前缀
File ID = R + 文件编号
编号稳定，不因文件标题变化而改变
项目自行决定 xxx 的业务含义
```

---

## 4. 文件内部使用编号 Rule Tree

```markdown
# [R010] <规则文件主题>

## [R010.010] <规则分支>

### [R010.010.010] <子分支>

#### [R010.010.010.010] <具体规则名>

#### [R010.010.010.020] <具体规则名>
```

要求：

```text
每级固定三位编号
Rule Node ID 项目内唯一
第一段必须与 File ID 一致
标题可变，ID 不变
分支节点只负责导航
真正的规范性要求放在 Leaf Node
```

---

## 5. Rule Leaf 使用 Agent-first 最小格式

Rule 的服务对象是 Agent，不是人类说明书。

Leaf 最小格式：

```markdown
#### [R010.010.010.010] <短规则名>

Level: MUST
When: <什么情况下适用>
Rule: <必须 / 禁止做什么>
Refs: <可选；引用 Architecture / Knowledge / Gate / Resource ID>
```

`Level` 只允许：

```text
MUST
MUST_NOT
MAY
```

最低要求：

```text
稳定 Rule ID
短标题
Level
When
Rule
```

`Refs` 可省略。

---

## 6. 规则文字必须短、直接、准确

推荐：

```text
必须……
禁止……
当 X 时，必须……
只有满足 Y 后，才允许……
```

禁止：

```text
尽量……
最好……
一般来说……
看情况……
适当……
原则上……
```

要求：

```text
一句 Rule 优先只表达一个可执行约束
When 只描述适用条件
Rule 不重复 When
不写背景故事
不写历史说明
不复制 Architecture / Knowledge / Gate 正文
```

需要原因、历史或详细说明时，通过 `Refs` 路由到其他资源。

---

## 7. Canonical Rule 唯一性

同一个规则语义只能存在一个 canonical Rule Leaf。

其他位置需要使用时：

```text
引用 Rule ID
```

禁止复制 Rule 正文。

旧 Rule ID 一旦废弃，不允许重新分配给新的规则语义。

语义重复和冲突检测第一版可以作为 Warning，后续能力成熟后再提升强度。

---

## 8. 高效路由方式

### 8.1 接入 / 变更阶段

```text
读取 rules/00_INDEX Front Matter
   ↓
校验编号文件
   ↓
解析 Rule Tree
   ↓
校验 Rule Leaf 最小字段
   ↓
建立 Route Cache
```

### 8.2 Agent 查询阶段

如果 Agent 已经知道稳定 Rule ID：

```text
R010.020.010
   ↓
O(1) Node ID 精确寻址
```

如果只有自然语言需求：

```text
query / scope
   ↓
00_INDEX 缓存
   ↓
候选 Rxxx File
   ↓
缓存的 Rule Tree
   ↓
祖先分支 + Rule Leaf 字段匹配
   ↓
少量 Rule Leaf Candidates
   ↓
Agent 阅读并判断最终适用性
```

Rule Manager 不替 Agent 判断最终适用规则。

---

## 9. 基础接入校验

Hard Reject：

```text
缺少 rules/00_INDEX.md
Index Front Matter 不符合母规范
正式文件不符合 NNN_<name>.md
File ID 与文件编号不一致
Rule Node ID 重复
Node ID 与所在文件编号不一致
父 Node 缺失
标题层级与编号树深度不一致
Index 漏掉正式规则文件
Index 指向不存在文件
无法解析 Rule Tree
Rule Leaf 缺少 Level / When / Rule
Level 非法
```

Warning：

```text
Rule 正文过长
When 过于模糊
Rule 使用模糊词
可能存在语义重复
可能存在规则冲突
Route Hints 太弱
```

出现 Hard Reject 时，该项目 Rules 接口不得进入 READY。

---

## 10. Rule Manager 的公共职责

Rule Manager 负责：

```text
接口校验
索引构建
缓存刷新
稳定 ID 寻址
自然语言候选路由
返回来源与匹配原因
```

Rule Manager 不负责：

```text
定义项目有哪些规则
替项目写规则内容
替 Agent 决定最终适用规则
把项目私有分类写进公共层
```

---

## 11. 核心目标

Rule Standard 一切设计只服务：

```text
查得快
读得少
理解快
引用稳
```

标准路径：

```text
Agent
  ↓
00_INDEX Cache
  ↓
Rxxx File
  ↓
Rxxx.xxx Branch
  ↓
Rule Leaf
  ↓
最小规则内容
```
