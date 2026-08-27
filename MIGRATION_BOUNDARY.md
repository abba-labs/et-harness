# ET Harness Repository Boundary

## Main

`main` 是公共 Harness 唯一上游，只保存公共 Contract、公共插件、公共 Runtime、模型适配、共享知识、通用示例和不依赖真实项目的验证。

## Project branches

`project/<name>` 保存公共 Harness 与一个真实项目的完整组合。项目分支定期合并 `main`，禁止将项目分支整体反向合入 `main`。

## Initial separation

初始实现来自 `abba-labs/et-tool`。ET-TOOL Project Plugin、项目型 Pilot 和依赖真实 ET-TOOL 的验证已保留在 `project/et-tool`，未进入 Harness-only main 候选。
