# Context Rules

正式语义规则源：

```text
agent_harness/project_contract/standards/11_CONTEXT_RECORD_STANDARD_V0_1.md
```

机器 Lint Profile：

```text
agent_harness/project_contract/standards/12_CONTEXT_LINT_PROFILE_V0_1.md
```

本插件执行两者。

核心要求：

```text
固定结构
短句单义
Confirmed / Assumption 分离
稳定引用优先
当前状态替换旧状态
Working Set 可 attach / detach / rebuild
Recent Tail 有上限
系统自动维护时间
Context 不保存完整历史
Context 必须可从长期治理层重建
```

Context Lifecycle API 见 `CONTEXT_LIFECYCLE_INTERFACE.md`。
