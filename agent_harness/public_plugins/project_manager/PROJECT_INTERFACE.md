# Project Manager — PROJECT_INTERFACE

> 支持标准：`Project Contract v0.1`  
> 资源：`project.yaml`

Project Manager 只接受符合 Project Contract 的项目描述。

## 最小目录

```text
project.yaml
architecture/
rules/
knowledge/
gates/
```

## project.yaml

```yaml
contract_version: "0.1"

project:
  id: my-project
  name: My Project

root:
  markers:
    - src/

resources:
  architecture:
    path: architecture/
    standard: architecture-v0.1
  rules:
    path: rules/
    standard: rule-v0.1
  knowledge:
    path: knowledge/
    standard: knowledge-v0.1
  gates:
    path: gates/
    standard: gate-v0.1

adapters: {}
```

## 命名要求

`project.id`：

```text
项目内外长期稳定
全局可区分
小写字母 / 数字 / . _ -
不得用临时分支名或路径名代替
```

## Root Marker

Marker 必须：

```text
使用项目内稳定相对路径
至少一个
能够可靠证明当前目录是该项目
不得使用 .. 或绝对路径
```

## Resource Standard

四类资源必须声明公共标准：

```text
architecture-v0.1
rule-v0.1
knowledge-v0.1
gate-v0.1
```

Project Manager 会拒绝标准缺失或不兼容的 Manifest。

具体资源内容必须继续遵守对应公共插件的 `PROJECT_INTERFACE.md` / `project_contract/standards/`。

## Project Manager 提供给 Agent 的接口

```text
listProjects()
resolveProject(query)
getProjectContext(projectId)
getResourcePath(projectId, kind)
```

Project Manager 只返回项目候选、上下文和资源入口，不替 Agent 判断最终应该选择哪个项目或修改哪个模块。
