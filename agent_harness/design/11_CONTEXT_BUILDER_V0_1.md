# Context Builder v0.1

> 公共能力：`context.build`

## 1. 定位

Context Builder 不搜索项目，也不替 Agent 选上下文。

Agent 先通过 Architecture / Rule / Knowledge / Gate Router 得到稳定 Node ID，然后明确选择需要的资源。

Context Builder 只做：

```text
ID 解析
去重
结构化渲染
优先级排序
预算控制
最小 Context Pack 输出
```

## 2. 强制保留

```text
MUST / MUST_NOT Rule
MUST Gate
Agent 显式 required item
```

预算不足时不得静默删除这些内容；允许 Context Pack 标记 `overBudget`。

## 3. 非强制内容

```text
high
normal
low
```

预算不足时整项省略，不切断一条 Rule / Knowledge / Gate 的语义。

## 4. 安全边界

```text
禁止跨 project_id 混合
Knowledge 非 VALIDATED 时保留状态警告
不自动展开整棵树
不自动搜索更多资源
```

## 5. 核心原则

> Agent 决定“要什么”；Context Builder 负责“用最少上下文把这些东西可靠装进去”。
