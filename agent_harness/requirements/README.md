# ET Harness Real Requirements

本目录保存 **用户真实需求（Real Requirements）**。

这里不是设计文档、实现计划、测试报告或历史进度，而是用于回答三个最基本的问题：

1. 我们真正要解决什么问题？
2. 为什么要这样做？
3. 哪些理解和方案已经明确被否决？

后续任何 Agent、Harness、模型或新对话，在开始相关架构设计和实现前，应先阅读本目录中与任务相关的需求文档，再阅读 `design/`、`progress_context/` 和具体插件实现。

如果实现或设计与 Real Requirements 出现冲突，不得自行重新解释用户目标。应明确指出冲突，并回到需求层确认。

## 文档职责

```text
requirements/      用户真实目标、边界、已否决方案
        ↓
design/            如何实现这些目标
        ↓
public_plugins/    公共能力实现
projects/          项目插件与项目私有资源
        ↓
validation/        机械验证与证据
progress_context/  阶段性实现状态与交接
```

## 当前需求索引

- `001_WEB_CHATGPT_HOST_REAL_REQUIREMENTS.md`
  - 定义 ChatGPT 网页版在 ET Harness 中的真实定位；
  - 说明为什么网页版必须与 Codex / Claude 等本地 Harness 共用 Project Plugin、Rules、Knowledge、Context 和 Evidence；
  - 明确网页版不依赖本地 tunnel，也不是旁路 Worker 或只提交结果的外部 Agent；
  - 明确当前阶段优先完成单 Agent 基础闭环，多 Agent Context / Knowledge 并发合并暂缓设计。
