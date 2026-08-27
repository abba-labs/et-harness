# ET Harness 独立仓库迁移 Handoff

日期：2026-08-27  
目标仓库：`abba-labs/et-harness`  
来源仓库：`abba-labs/et-tool`  
性质：仓库拆分事实冻结、分支边界、验证结果与下一阶段入口

---

## 0. 一页结论

公共 Harness 已从 `abba-labs/et-tool` 提取到独立仓库，并按以下长期模型分离：

```text
et-harness/main
= 公共 Harness 唯一上游

et-harness/project/<name>
= 公共 Harness + 一个真实项目 + 该项目 Project Plugin / Knowledge
```

迁移不删除、不改写 `et-tool/main`。源仓库继续作为迁移期回滚来源，直到新仓库主线和至少一个真实项目分支完成闭环验证。

本次迁移不是把 ET-TOOL 产品改名为 Harness 仓库，而是把 `agent_harness/` 中真正公共的 Contract、插件、Runtime、模型边界、共享知识和 synthetic-project 验证建立为独立上游。

---

## 1. 来源基线

```text
source repo: abba-labs/et-tool
source branch: main
source HEAD: 496243ef2bdf56a5db7f81b2014970d3f8af34f9
last fully validated Harness code baseline:
f37b1080ca65388fc0e32f7fa75567b512c86752
```

`496243...` 相比最后完整功能回归基线只包含 Handoff 文档整理，没有额外 Harness 生产代码变化。

---

## 2. 迁移方法与完整性

由于空目标仓库不能直接引用另一个仓库的 Git Tree / Blob 对象，本次使用 GitHub Actions Artifact 建立当前快照：

```text
et-tool/main
→ migration/et-harness-export
→ 生成 agent_harness 快照
→ SHA-256 校验
→ 导入 et-harness 隔离迁移分支
```

关键记录：

```text
export commit:
1f180ecfa93c59b3db6fec0b9f54c51080b5b1c4

export workflow run:
33045770474

artifact id:
9635571961

artifact ZIP SHA-256:
1e47d5d6ab7a8388a51ed3aec62caa112523815a8f641855d0bc5fad4fde4986

snapshot TAR SHA-256:
aa99acc35df6b1abf6fa8382bc7db315e126757dc4ecbc2ac944d17cf4a91a9b

raw import commit:
f221ccfddb0d031041f64b3c97bcf744d1182faa
```

必须明确：目标仓库保存了经过校验的当前内容快照和完整来源记录，但没有复制 `et-tool` 的逐提交历史。迁移前历史继续以 `abba-labs/et-tool` 为权威追溯源。

---

## 3. Harness-only 主线分离

原始快照同时包含公共 Harness 和 ET-TOOL 项目私有内容，因此从 raw import 分出两条线：

```text
migration/harness-only-main-v0.1
→ 公共 main 候选

project/et-tool
→ ET-TOOL 项目型 Harness 内容暂存线
```

公共 main 候选删除了：

```text
agent_harness/projects/et_tool/
agent_harness/pilots/external_chat_agent/
agent_harness/pilots/real_provider/
ET-TOOL-dependent Pilot / negative matrix / real-task validation scripts
```

公共 main 候选保留：

```text
governance_core
project_contract
public_plugins
model_adapters
global_knowledge
generic examples / generic pilot
public and synthetic-project validation
design and progress_context
```

初始分离提交：

```text
e317336bfddcfb3e1039aee0db5186470e2fd2b8
```

`project/et-tool` 当前只是项目专属 Harness 内容的暂存分支，尚未导入完整 ET-TOOL 产品代码，不能把它描述为已经完成的 ET-TOOL 项目分支。

---

## 4. 冻结分支模型

### 4.1 `main`

只允许公共 Harness：

- 公共 Contract、公共插件与公共 Runtime；
- Provider-neutral Host / Model 边界；
- Global Knowledge；
- synthetic-project 测试；
- Harness 自身设计、验证和 Handoff。

禁止：

- 真实项目业务代码；
- 真实项目私有 Project Plugin 和 Project Knowledge；
- 依赖具体项目工作树的测试；
- 某个项目专属的 Workflow。

### 4.2 `project/<name>`

```text
main 当前公共 Harness
+ 项目完整代码
+ 项目 Project Plugin
+ 项目 Architecture / Rules / Knowledge / Gates
+ 项目自己的 Workflow
```

更新方向固定：

```text
main
  ↓ merge
project/<name>
```

禁止项目分支整体反向合入 `main`。

---

## 5. 新仓库公共门禁

新增：

```text
.github/workflows/harness-public-baseline.yml
```

门禁分三部分：

1. Repository boundary
   - 不存在真实 `projects/et_tool`；
   - 不存在 ET-TOOL 产品 `source/`、`doc/`、`html/`；
   - 公共生产包不引用真实 ET-TOOL Project Plugin。

2. Package build and test
   - 公共包按本地依赖拓扑顺序安装；
   - 有 test script 的包必须通过测试；
   - 所有公共包必须通过 TypeScript build。

3. Public integration
   - Public Plugins；
   - Public Layer current policy；
   - Auto Governance Orchestrator；
   - Agent Governance Kernel；
   - Governance Runtime；
   - Level-2 Model；
   - OpenAI-compatible Wrapper。

迁移完成时应以合并候选精确 HEAD 对应的 GitHub Check Suite 为最终机械证据，不能仅引用更早提交的成功结果。

---

## 6. 当前不能声称的内容

本次只完成公共 Harness 独立仓库迁移，尚未完成：

```text
完整 ET-TOOL 产品代码导入 project/et-tool
Automated Testing Platform 导入 project/automated-testing-platform
ATP Project Plugin 与独立 Knowledge Base 的最终接入
真实项目分支上的 Runtime 闭环
旧 et-tool 仓库中 agent_harness 的删除或归档
```

因此暂时不要关闭或删除源仓库，也不要把 staging 项目分支描述成已完成项目迁移。

---

## 7. 下一阶段顺序

```text
1. 将 Harness-only 候选合入 et-harness/main
2. 以 main 创建 project/automated-testing-platform
3. 从 Automated_Testing_Platform review_code 导入完整项目代码
4. 在同一分支建立 ATP Project Plugin / Knowledge
5. 直接完成单仓库、单工作树 Runtime 闭环
6. 再完成 project/et-tool 的完整项目导入
7. 两个项目分支稳定后，再处理旧仓库重复 Harness
```

不要重新回到跨仓库 `projectRoot / resourceBasePath` 路线；新的长期模型已经通过同仓库项目分支消除了该复杂度。

---

## 8. 冻结原则

> **Agent 不负责治理自己。Framework 负责治理 Agent。**

仓库拆分只改变代码与项目的版本组织方式，不改变公共治理边界：

```text
Framework：触发、校验、阻断、状态写入、Evidence、晋级
Agent：语义判断、Review 结论、Knowledge / Experience 提议
Project Plugin：项目识别、资源声明、项目私有 A/R/K/G 与 Knowledge
Project：继续拥有自己的业务实现
```
