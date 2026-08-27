# Architecture Navigator

公共项目架构路由插件。

核心职责只有两项：

```text
1. 校验项目 Architecture Resource 是否符合 architecture-v0.1
2. 建立缓存 Route Index，并按最短路径返回 Architecture 候选节点
```

它不负责：

```text
理解用户最终意图
定义项目模块
决定 Agent 应该修改哪里
替 Agent 阅读全部源码
```

运行模型：

```text
Admission / Refresh
00_INDEX → 编号文件 → 编号标题树 → Route Cache

Runtime Query
Agent query → Cache → File → Node → CandidateResult
```

正式项目接口见 `PROJECT_INTERFACE.md`。
