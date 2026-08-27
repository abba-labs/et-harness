# Public Evidence / State Manager

公共运行时事实层，不定义 Project Plugin 文件接口。

核心原则：

```text
Evidence = append-only / immutable
State = versioned / evidence-linked
Project = strict isolation
```

默认存储根：

```text
$AGENT_HARNESS_STATE_ROOT
```

未设置时使用：

```text
~/.agent-harness/runtime
```

该运行时数据不属于项目源代码知识文件。
