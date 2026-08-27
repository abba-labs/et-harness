# Public Plugin Project Interface Ownership Standard v0.1

> 状态：DESIGN BASELINE  
> 原则：**任何消费 Project Plugin 私有资源的公共插件，都必须拥有并发布自己的项目接口规范，并继承 Project Resource Routing Meta Standard。**

## 1. 公共插件既是 Router，也是 Interface Standard Owner

面向项目资源的公共插件必须同时提供：

```text
规范
校验
路由
```

项目接口不符合规范时，公共插件必须拒绝正式接入，而不是偷偷兼容项目私有格式。

---

## 2. 强制发布 `PROJECT_INTERFACE.md`

每个面向项目资源的公共插件包必须包含：

```text
PROJECT_INTERFACE.md
```

该文档是项目作者实现接口的正式说明，不是普通 README。

它必须先声明：

```text
继承的 Meta Standard
支持的 standard id / version
Resource Kind
Node Prefix
主文件扩展名
```

---

## 3. 所有子规范必须继承统一寻址骨架

公共插件不得自行设计另一套基础路由结构。

统一继承：

```text
00_INDEX.md Front Matter
        ↓
NNN_<project-defined-name>.<ext>
        ↓
固定三位编号 Node Tree
        ↓
稳定 Node ID
        ↓
Minimal Content
```

项目具体内容类别完全由项目自己决定。

---

## 4. `PROJECT_INTERFACE.md` 只补充资源特有规则

至少说明：

```text
1. 插件消费哪一种 Project Resource
2. standard id / version
3. Node Prefix
4. 主文件扩展名
5. 文件内部树如何表达
6. Node 最小字段
7. 该资源特有的 Hard Reject
8. 该资源特有的 Warning
9. Agent 可以调用哪些路由接口
10. 最小合法示例
```

不得在公共接口规范中规定：

```text
项目必须有哪些业务类别
项目必须有哪些具体文件
某个具体项目的模块名 / 规则名 / Gate 名
```

---

## 5. 标准所有权

```text
Project Manager          owns Project Contract / project.yaml
Architecture Navigator  owns architecture-v0.1
Rule Manager            owns rule-v0.1
Knowledge Manager       owns knowledge-v0.1
Gate Manager            owns gate-v0.1
```

跨资源公共寻址规则由：

```text
Project Resource Routing Meta Standard v0.1
```

统一拥有。

具体公共插件只能扩展自己的资源特有部分，不能修改母规范语义。

---

## 6. 文档与代码必须一致

具体公共插件实现时必须：

```text
PROJECT_INTERFACE.md 与代码校验器使用同一 standard version
复用 Project Contract 的公共 Index / 文件编号 / Node ID 校验能力
子插件只增加自己的节点结构校验
```

禁止：

```text
代码接受一种格式，文档描述另一种格式
项目必须读插件源码才能知道接口怎么写
公共插件默默兼容项目私有格式
同一种公共能力针对不同项目定义不同基础格式
修改接口格式但不升级 standard version
```

---

## 7. 接入结果

公共插件对某个项目资源接口只允许明确状态：

```text
READY     → 结构符合规范，可以正式路由
REJECTED  → 存在 Hard Reject，禁止正式路由
```

Warning 不阻止 READY，但必须可查询、可治理。

---

## 8. 目标

新增项目时，项目作者应该只需要阅读：

```text
Project Contract
+
Project Resource Routing Meta Standard
+
对应公共插件 PROJECT_INTERFACE.md
```

就能实现标准接口。

公共插件则可以依赖统一地址体系完成高效、可靠路由，而不需要理解每个项目的私有目录习惯。
