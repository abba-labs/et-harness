# ET Harness

ET Harness 是公共 Agent Governance / Project Plugin / Knowledge Governance 框架仓库。

## Branch model

- `main`: 公共 Harness 唯一上游，不包含具体项目业务代码或项目私有知识。
- `project/<name>`: 公共 Harness + 对应项目代码 + Project Plugin + Project Knowledge。

## Migration baseline

初始公共实现从 `abba-labs/et-tool` 的 `main` 分支提取。迁移期间源仓库保持不变；新仓库完成回归前不删除旧实现。
