# Knowledge Manager v0.1

> 状态：IMPLEMENTATION BASELINE  
> 公共能力：`knowledge.navigate`  
> 项目接口：`knowledge-v0.1`

## 1. 定位

Knowledge Manager 是项目私有正式知识的公共接口规范制定者和高速 Router。

负责：

```text
Knowledge 接口校验
Route Cache
稳定 K ID 寻址
validated-first 查询
来源和状态返回
```

不负责：

```text
规定项目知识类别
经验提炼
候选去重晋级
写回 canonical Knowledge
```

经验写回由后续 Experience / Memory Manager 负责。

## 2. 路由链

```text
Agent
  ↓
Knowledge Manager
  ↓
Project Manager / ProjectContext
  ↓
knowledge/00_INDEX.md
  ↓
Kxxx File
  ↓
Knowledge Tree Cache
  ↓
Knowledge Candidate
```

## 3. 可信状态

```text
CANDIDATE
VALIDATED
DEPRECATED
```

自然语言查询默认：

```text
VALIDATED only
```

显式 K ID：

```text
允许读取任意状态
但必须返回 Status + Warning
```

## 4. Knowledge Leaf

```text
Status
Fact
Scope? 
Provenance
Refs?
```

Fact 必须短；长日志和长证据通过引用访问。

## 5. API

```text
refreshProject(projectId)
getIndex(projectId)
listFiles(projectId)
searchKnowledge(request)
getNode(projectId, knowledgeId)
listChildren(projectId, nodeId)
removeProject(projectId)
```

## 6. 可靠性

```text
结构错误 → REJECT
刷新失败 → 清旧 Cache
项目消失 → 清旧 Cache
默认查询 → 不返回未验证事实
```

## 7. ET-TOOL 边界

ET-TOOL 仍保持空标准知识接口。

本阶段不迁移旧知识、不生成新知识、不修改项目业务内容。

## 8. 最终 Gate

```text
PHASE3_KNOWLEDGE_MANAGER_INTEGRATION=PASS
```

只有真实 Cordis 集成 Gate 运行通过后才能记录该 PASS。
