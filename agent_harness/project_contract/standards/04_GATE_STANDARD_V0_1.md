# Gate Interface Standard v0.1

> 标准 ID：`gate-v0.1`  
> Node 前缀：`G`  
> 主文件格式：`NNN_<name>.yaml`  
> 继承：`Project Resource Routing Meta Standard v0.1`

## 1. 本标准只规定 Gate 接口

Gate Manager 不规定项目应该有哪些测试、验证或门禁分类。

项目自行决定 Gate 内容。

公共标准只保证：

```text
00_INDEX.md
   ↓
NNN_*.yaml
   ↓
Gxxx 编号 Gate Tree
   ↓
Executable Gate Leaf
```

---

## 2. `gates/00_INDEX.md` 是唯一机器入口

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

---

## 3. 文件命名与 File ID

```text
010_xxx.yaml → G010
020_xxx.yaml → G020
```

编号是稳定地址，业务名称由项目决定。

---

## 4. Gate Tree 是机器 YAML

```yaml
standard: gate-v0.1
file_id: G010
title: <项目定义>

nodes:
  - id: G010.010
    title: <分支>
    children:
      - id: G010.010.010
        title: <具体 Gate>
        gate:
          level: MUST
          when: <何时触发>
          steps:
            - id: build
              tool: build.execute
          pass:
            mode: all_steps_pass
          refs: []
```

规则：

```text
File ID 作为树根地址
每级编号固定三位
Branch 只有 children
Executable Gate 必须是 Leaf
Leaf 使用 gate 字段
```

---

## 5. Executable Gate 最小接口

```text
level
when
steps
pass
```

`level`：

```text
MUST
MAY
```

每个 step 至少：

```text
id
 tool capability
```

Tool Capability 必须使用稳定能力名，例如：

```text
build.execute
test.execute
lint.execute
hardware.validate
```

项目特殊能力通过 Adapter Provider 暴露 Capability，Gate 不硬编码实现类。

---

## 6. Gate Manager 不直接代替 Agent 执行

Gate Manager 输出：

```text
Gate Candidate
+
Execution Plan
```

Agent 负责：

```text
读取 Gate
调用对应 Tool Capability
观察结果
失败后修改代码 / 环境
再次执行
```

后续 Evidence Manager 负责记录执行证据。

因此 Gate Manager v0.1 不内置具体编译器、测试框架、硬件工具或项目命令。

---

## 7. Mandatory 语义

```text
level: MUST
```

表示该 Gate 一旦被确认适用于当前 Change，就不得由普通 Agent 自行绕过。

Governance 层负责后续强制完成状态检查和例外授权。

`MAY` 表示可选验证。

---

## 8. 高效路由

稳定 Gate ID：

```text
G010.020.010
→ O(1) 精确寻址
```

自然语言 / Change Scope：

```text
query / scope
   ↓
00_INDEX Cache
   ↓
候选 Gxxx File
   ↓
Gate Tree Cache
   ↓
Gate Leaf Candidates
   ↓
Agent 判断适用性
```

Gate Manager 不替 Agent 做最终语义判断。

---

## 9. 基础接入校验

Hard Reject：

```text
缺少 gates/00_INDEX.md
Index Front Matter 不符合母规范
正式文件不符合 NNN_<name>.yaml
File ID 与文件编号不一致
YAML standard / file_id 错误
Gate Node ID 重复 / 错位
父子编号关系非法
Branch 与 Gate Leaf 结构混用
Executable Gate 缺少 level / when / steps / pass
level 非法
step 缺少 id / tool
step id 重复
Tool Capability 格式非法
Index 漏文件 / 指向不存在文件
```

Warning：

```text
when 过长或过宽
可能存在重复 Gate
可能存在冲突触发
Tool Capability 当前不可用
Route Hints 太弱
```

---

## 10. 核心目标

```text
快速找到该验证什么
结构可以直接形成执行计划
Mandatory 语义明确
具体工具实现与项目 Gate 解耦
Agent 只读取当前修改相关 Gate
```

Gate 内容属于项目；接口、校验、路由和 Execution Plan 结构属于公共 Gate Manager。
