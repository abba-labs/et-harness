# ET-TOOL Knowledge Project Note

> 状态：KNOWLEDGE TAXONOMY v0.1 / CONTENT EMPTY  
> 本文件只用于人类说明，不参与 Knowledge 路由，也不是 Knowledge canonical source。

ET-TOOL 已切换到 `knowledge-library-v0.2` 项目知识库模式。

正式 canonical source：

```text
knowledge/TAXONOMY.yaml
knowledge/NNN_*.md
```

Source / Verification 辅助事实源：

```text
knowledge/SOURCES.yaml
knowledge/VERIFICATIONS.jsonl   # 首条 Verification 出现后创建
```

`knowledge/00_INDEX.md` 是 Knowledge Manager 自动生成目录，禁止人工或 Agent 手工维护。

当前阶段只建立分类体系与 Source/Verification 入口，不预先填充正式 Knowledge Leaf。

旧 `facts/`、`decisions/`、`memory/`、`tests/` 等 Phase 2 目录以及 `doc/current_design_analysis/` 继续作为 migration/reference 材料，不自动成为正式 Knowledge。后续必须重新核对当前代码、提炼最小 Knowledge Candidate、绑定 Source/Evidence 并通过 Verification/Validation 后，才可显式 Promote 为 VALIDATED。
