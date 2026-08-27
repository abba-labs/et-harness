# Rule Manager v0.1

> 状态：IMPLEMENTATION BASELINE  
> 公共能力：`rule.navigate`  
> 项目接口：`rule-v0.1`

## 1. 定位

Rule Manager 是公共项目资源插件。

它的职责只有两类：

```text
1. Rule Interface Standard Owner
2. High-efficiency Rule Router
```

它不负责：

```text
定义项目有哪些规则
替项目写规则
替 Agent 判断最终适用规则
```

## 2. 标准链路

```text
Agent
  ↓
Rule Manager
  ↓
Project Manager / ProjectContext
  ↓
rules/00_INDEX.md
  ↓
Rxxx File
  ↓
Rule Tree Cache
  ↓
Rule Branch / Leaf Candidate
  ↓
Agent
```

## 3. 两阶段模型

### Admission / Refresh

```text
读取 00_INDEX Front Matter
校验 rule-v0.1
校验编号文件
解析 Rule Tree
校验 Leaf 的 Level / When / Rule
建立内存 Cache
```

### Runtime Route

已知 Rule ID：

```text
R010.020.010
→ O(1) 精确寻址
```

自然语言：

```text
query
→ Index Cache
→ 候选 File
→ Rule Tree
→ Rule Leaf / Branch Candidates
```

查询阶段不重新扫描项目文件。

## 4. Agent-first Rule Leaf

```text
Level: MUST | MUST_NOT | MAY
When: <适用条件>
Rule: <直接约束>
Refs: <可选>
```

目标：

```text
短
直接
准确
可验证
少 Token
```

## 5. 公共 API

```text
refreshProject(projectId)
getIndex(projectId)
listFiles(projectId)
searchRules(request)
getNode(projectId, ruleId)
listChildren(projectId, nodeId)
removeProject(projectId)
```

## 6. 可靠性

Hard Reject：

```text
Index 非法
编号文件非法
Node ID 非法 / 重复
父节点缺失
树层级错误
Leaf 字段不完整
Level 非法
Index ↔ 文件不一致
```

刷新失败：

```text
旧 Cache 清除
```

Project 消失：

```text
旧 Cache 失效
```

## 7. 查询策略

Rule Manager 不做 LLM 推理。

第一版采用确定性路由：

```text
Index title / summary / aliases
+
Rule branch titles
+
Leaf title / When / Rule / Refs
+
Agent 可选 scope
```

Rule Leaf 优先；宽泛查询允许返回 Branch，供 Agent 继续缩小。

## 8. ET-TOOL 边界

当前 ET-TOOL 仅保留合法空接口：

```text
rules/00_INDEX.md
files: []
```

本阶段不设计、不迁移、不填充 ET-TOOL 具体规则。

## 9. v0.1 验收标准

```text
rule-v0.1 标准文档存在                         PASS
PROJECT_INTERFACE.md 存在                      PASS
Rule Tree parser                              PASS
Leaf Level / When / Rule validation           PASS
Index → File → Rule Tree cache                PASS
稳定 Rule ID 精确寻址                         PASS
自然语言候选路由                              PASS
宽泛 Branch 路由                              PASS
刷新失败清旧 Cache                            PASS
空标准接口 READY                              PASS
Project Manager 集成                          PASS
Governance capability = rule.navigate         PASS
Cordis lifecycle cleanup                      待真实 Gate
```

最终真实集成标记：

```text
PHASE3_RULE_MANAGER_INTEGRATION=PASS
```
