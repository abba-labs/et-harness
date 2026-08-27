# Experience / Memory Manager v0.1

> 公共能力：`experience.manage` / `memory.context`

## 1. 定位

Agent 是经验语义的提炼者。

Experience / Memory Manager 不从聊天记录自动“猜经验”，而是接收 Agent 明确提交的经验候选。

## 2. 候选链路

```text
完成任务
  ↓
Agent 总结值得复用的经验
  ↓
recordCandidate
  ↓
Evidence 引用校验
  ↓
Project-scoped CANDIDATE Memory
```

候选必须至少有一个 Evidence 引用。

## 3. Memory 查询

默认检索未决 `CANDIDATE`，并明确警告：

```text
尚未晋级为 VALIDATED Knowledge
```

Memory 用于跨任务提醒，不等同正式项目事实。

## 4. Knowledge 晋级

插件不决定知识分类和地址。

Agent 必须明确给出：

```text
File ID
Parent K Node ID
New K Node ID
Title
```

插件负责：

```text
校验目标
写入 Status: VALIDATED 的标准 Knowledge Leaf
Knowledge Manager 重新校验
更新 Experience 状态为 PROMOTED
任何失败 → 回滚文件
```

## 5. 去重

v0.1 对未拒绝候选执行规范化 Fact 精确去重。

后续可以增加语义相似度去重，但不得用不透明模型结果自动删除知识。

## 6. 边界

```text
Agent               → 总结经验、决定是否提交、决定晋级位置
Experience Manager  → 校验、保存、检索、受控晋级
Knowledge Manager   → 正式 Knowledge 接口与校验
Evidence Manager    → 事实证据
```

## 7. ET-TOOL

当前不提交任何 ET-TOOL 经验候选，也不写 ET-TOOL Knowledge。
