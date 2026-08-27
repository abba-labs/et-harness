# Architecture Navigator v0.1

> 状态：IMPLEMENTATION BASELINE  
> 公共能力：`architecture.navigate`  
> 项目接口标准：`architecture-v0.1`

## 1. 定位

Architecture Navigator 是第一个真正消费 Project Plugin 私有资源的公共 Router。

它只承担：

```text
接口规范所有者
+
接入校验器
+
Architecture Route Index Builder
+
高频缓存 Router
```

它不承担：

```text
理解用户最终意图
规定项目有哪些模块
决定 Agent 最终应该改哪里
替 Agent 阅读全部源码
```

---

## 2. 数据流

```text
Agent
  ↓ query / Node ID
Architecture Navigator
  ↓
Project Manager
  ↓ ProjectContext / Architecture Resource Handle
architecture/00_INDEX.md
  ↓
NNN_*.md
  ↓
Axxx 编号树
  ↓
Route Cache
  ↓
CandidateResult / exact Node
  ↓
Agent
```

---

## 3. 两阶段模型

### Admission / Refresh

```text
确认 project 存在
确认 architecture-v0.1
读取 00_INDEX Front Matter
校验 Index ↔ 编号文件
解析 Architecture Tree
校验 Axxx Node
建立内存 Route Cache
```

任何 Hard Reject 都不允许进入 READY。

刷新前先清理旧 Cache；刷新失败不能继续提供旧架构数据。

### Runtime Route

稳定 ID：

```text
A010.020.010
```

优先 O(1) 精确寻址。

自然语言查询：

```text
Index Cache
  ↓
候选 File
  ↓
候选 Node
  ↓
排序
  ↓
少量 CandidateResult
```

查询阶段不重复扫描 Architecture 目录。

---

## 4. v0.1 API

```text
refreshProject(projectId)
getIndex(projectId)
listFiles(projectId)
searchArchitecture(request)
getNode(projectId, nodeId)
listChildren(projectId, nodeId)
removeProject(projectId)
```

其中：

```text
refreshProject = 重校验 + 重建缓存
searchArchitecture = 候选路由
getNode = 稳定地址读取
listChildren = Agent 继续向下探索
```

---

## 5. Router 算法原则

优先级：

```text
1. Node ID 精确寻址
2. File ID / 地址前缀
3. 00_INDEX aliases / title / summary
4. Node title / Role / Boundary / Resources / Relations
```

v0.1 采用轻量确定性匹配，不使用 LLM、Embedding 或向量数据库。

原因：

```text
地址可确定时不需要 AI
索引元数据足够时不需要全文搜索
公共插件负责缩小范围，不负责最终语义判断
```

后续可以替换排序 Provider，但不得破坏标准地址体系。

---

## 6. 可靠性约束

必须保证：

```text
不合规 Architecture → REJECT
刷新失败 → 旧 Cache 失效
Project 不存在 → Cache 失效
Project Resource Path 改变 → 自动重建
Candidate 带 project_id / provenance / location
```

项目文件内容改变但路径不变时，由调用方执行 `refreshProject()`；后续可通过文件变更事件自动触发刷新。

---

## 7. 当前 ET-TOOL 状态

ET-TOOL 当前：

```text
architecture/00_INDEX.md
files: []
```

因此它是：

```text
INTERFACE READY
CONTENT EMPTY
```

Architecture Navigator 应允许其 READY，但查询返回空结果。

当前阶段不填充任何 ET-TOOL 架构内容。

---

## 8. v0.1 验收

至少验证：

```text
合法编号树可解析
错误标题层级被拒绝
父 Node 缺失被拒绝
未索引正式文件被拒绝
Node ID 可精确寻址
自然语言通过 Index → File → Node 返回候选
刷新后查询只使用 Cache
空标准接口可以 READY
Governance 注册 architecture.navigate
插件卸载清理 Provider / Service
```

Architecture Navigator 通过后，再按同一模式实现 Rule Manager，而不是重新设计另一套路由体系。
