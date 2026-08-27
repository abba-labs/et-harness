# Gate Manager Project Interface

> 支持标准：`gate-v0.1`  
> 母规范：`Project Resource Routing Meta Standard v0.1`

## 1. 项目必须提供

```text
gates/
├─ 00_INDEX.md
├─ 010_<project-defined-name>.yaml
├─ 020_<project-defined-name>.yaml
└─ ...
```

项目自行决定 Gate 文件数量、分类和业务含义。

## 2. `00_INDEX.md`

```yaml
---
interface: project-resource-index-v0.1
resource: gates
standard: gate-v0.1
files:
  - id: G010
    file: 010_xxx.yaml
    title: <短标题>
    summary: <一句话>
    aliases: [<route-hint>]
---
```

所有正式 Gate 文件必须进入 Index。

## 3. Gate YAML Tree

```yaml
standard: gate-v0.1
file_id: G010
title: <项目定义>
nodes:
  - id: G010.010
    title: <分支>
    children:
      - id: G010.010.010
        title: <Gate>
        gate:
          level: MUST
          when: <触发条件>
          steps:
            - id: build
              tool: build.execute
          pass:
            mode: all_steps_pass
          refs: []
```

Branch 只允许 `children`；Executable Gate 必须是 Leaf 并携带 `gate`。

## 4. Gate Leaf 最小字段

```text
level = MUST | MAY
when
steps[]
pass
```

每个 Step 至少：

```text
id
tool
```

`tool` 必须是稳定 Tool Capability，不允许把项目命令写进公共 Gate Manager。

## 5. Gate Manager 输出

Gate Manager 只输出：

```text
Gate Candidate
Execution Plan
```

Agent 再调用 Tool Capability 执行。

Gate Manager 不直接替 Agent 运行编译器、测试工具或硬件工具。

## 6. 接入拒绝条件

```text
缺少 00_INDEX.md
Index 不符合母规范
编号文件非法
standard / file_id 错误
Node ID 重复 / 错位
父子关系非法
Branch 和 Gate 混用
Gate 缺 level / when / steps / pass
Step 缺 id / tool
Step ID 重复
Tool Capability 格式非法
Index 与实际文件不一致
```

## 7. Agent API

```text
refreshProject(projectId)
searchGates(request)
getNode(projectId, gateId)
getExecutionPlan(projectId, gateId)
listChildren(projectId, nodeId)
listFiles(projectId)
getIndex(projectId)
```

有稳定 G ID 时优先精确寻址；否则使用 Index → File → Gate Tree 候选路由。
