# Evidence / State Manager v0.1

> 公共能力：`evidence.record` / `evidence.read` / `state.read` / `state.update`

## 1. 定位

这是公共运行时事实层，不是 Project Plugin 设计知识。

```text
Evidence = 不可变历史事实
State    = 当前状态投影
```

## 2. Evidence

```text
append-only
project_id 隔离
task_id 关联
稳定 Evidence ID
result = PASS / FAIL / INFO / SKIP
可关联 Gate / Artifact / Tool source
```

v0.1 不提供 Evidence 修改和删除 API。

## 3. State

```text
project_id
scope
key
value
version
reason
evidenceRefs
```

更新支持 `expectedVersion`，防止旧 Agent 静默覆盖新状态。

Evidence 引用必须真实存在并属于同一项目。

## 4. 存储

默认：

```text
~/.agent-harness/runtime
```

可通过：

```text
AGENT_HARNESS_STATE_ROOT
```

修改。

Evidence 使用 JSONL 追加；State 使用临时文件 + rename 原子替换。

## 5. 边界

不定义 Project Plugin 文件格式。

不把运行时 Evidence/State 塞进项目 Architecture/Rule/Knowledge/Gate 文档。

## 6. v0.1 限制

v0.1 以单 Harness Runtime Provider 为并发边界。

后续如果需要多进程/多机器共享，替换 Storage Provider，而不是修改上层 API。
