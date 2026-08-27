# Public Project Manager

公共 Project Manager 是 Agent 的项目路由工具。

它负责：

```text
注册项目
列出项目
返回项目候选
返回 ProjectContext
返回项目资源入口
```

它不负责：

```text
理解最终任务
决定修改哪个模块
决定哪些规则最终适用
替 Agent 开发
```

典型调用：

```text
Agent
→ projectManager.listProjects()
→ projectManager.resolveProject("ettool")
→ projectManager.getProjectContext("et-tool")
→ projectManager.getResourcePath("et-tool", "architecture")
```

普通项目可以通过 `project.yaml` 注册，不要求编写 TypeScript。
