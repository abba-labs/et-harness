# Knowledge Source & Verification Standard v0.1

> Source Registry：`knowledge-source-registry-v0.1`  
> Verification：`knowledge-verification-v0.1`  
> 所属：公共 Knowledge Manager  
> Evidence 所属：公共 Evidence / State Manager  
> 规范关系：本标准是 `knowledge-library-v0.2` 的 canonical-data 扩展；启用本标准后，以本标准第 2 节扩展 `06_KNOWLEDGE_LIBRARY_STANDARD_V0_2.md` 的 Source of Truth 定义。

## 1. 核心边界

```text
Knowledge    = 当前认知
Source       = 参考依据
Evidence     = 实际发生的运行事实
Verification = Source / Evidence 对 Knowledge 的 SUPPORT / CONTRADICT 关系
```

Knowledge Manager 管理 Knowledge、Source、Verification。
Evidence / State Manager 独立管理 Evidence；Knowledge Manager 只读 Evidence 引用，不复制 Evidence 内容。

## 2. 同库 canonical 结构

启用 Source / Verification 后，Library canonical source 扩展为：

```text
<knowledge-root>/
├─ TAXONOMY.yaml
├─ SOURCES.yaml            # Source Registry canonical
├─ VERIFICATIONS.jsonl     # append-only Verification canonical
├─ NNN_*.md                # Knowledge canonical
└─ 00_INDEX.md             # generated
```

因此 `knowledge-library-v0.2` 中“`TAXONOMY.yaml + NNN_*.md` 是 canonical”的定义应理解为知识正文核心集合；本标准增加 `SOURCES.yaml + VERIFICATIONS.jsonl` 作为依据链 canonical 数据。`00_INDEX.md` 和机器索引仍然只是生成物。

`SOURCES.yaml` 在第一条 Source 注册前可以不存在；`VERIFICATIONS.jsonl` 在第一条 Verification 前可以不存在。

## 3. Source

Source 最小字段：

```text
sourceId
kind
status
title
location
registeredAt
revision?
contentHash?
note?
```

`kind`：

```text
DOCUMENT | SPEC | CODE | RTL | WEB | OTHER
```

稳定 Source ID：

```text
SRC000001
SRC000002
...
```

完整地址：

```text
source://global/SRC000001
source://project/<project-id>/SRC000001
```

同一 Library 内 `location + revision` 完全相同的 Source 拒绝重复注册。

## 4. Source Scope

```text
Global Knowledge
→ Source Verification 只能引用 Global Source

Project Knowledge
→ 可以引用 Global Source
→ 可以引用同 Project Source
→ 禁止引用其他 Project 私有 Source
```

项目发现可复用资料时，应先把资料注册为 Global Source，再用于 Global Knowledge。

## 5. Evidence URI

Evidence 保持由 Evidence / State Manager 管理。

Knowledge Verification 只使用稳定引用：

```text
evidence://project/<project-id>/<EV-ID>
```

建立 Verification 时必须即时确认 Evidence 存在且属于指定 Project。

项目卸载后 Verification 记录仍可保留 Evidence URI；不得为了长期可读而复制 Evidence 正文。

## 6. Verification

Verification 只有两个语义：

```text
SUPPORT
CONTRADICT
```

最小记录：

```text
verificationId
knowledgeUri
knowledgeFingerprint
basisKind: SOURCE | EVIDENCE
basisRef
relation: SUPPORT | CONTRADICT
recordedAt
note?
```

其中：

```text
knowledgeFingerprint = sha256(Fact + Scope)
```

Verification 必须绑定记录时的 Knowledge Claim，而不只绑定 K-ID。

因此 Candidate 修改 Fact / Scope 后：

```text
旧 Verification 保留
但不会继续支持 / 反证新的 Claim
```

Verification 是 append-only。v0.1 不提供修改和删除 API。

## 7. Evidence Scope

```text
Global Knowledge
→ 可以接受任意当前已注册 Project 的 Evidence

Project Knowledge
→ 只能接受当前 Project 自己的 Evidence
```

这样项目可以共同验证 Global Knowledge，但不能跨项目污染另一个 Project 的私有知识。

## 8. Verification 与 Promotion 分离

`recordVerification()` 只追加 SUPPORT / CONTRADICT，不直接修改 Knowledge Status。

Governance Runtime 可以在 8/8 Closure 完成后调用独立 Validation Policy：

```text
Verification Records
-> knowledgeValidationPolicy.evaluate()
-> READY 时 promote()
```

Promotion 失败是 Post-Closure warning，不允许破坏已经 CLOSED 的 Turn。

## 9. Source 与 Provenance

现有 `Provenance` 字段继续保留，作为 Knowledge Leaf 的简短来源说明 / 兼容字段。

正式可机器解析的依据关系以：

```text
Source Registry + Verification Records
```

为准。

Knowledge Leaf 可读取 `Sources:` 兼容字段，但 v0.1 不要求在 Leaf 与 Verification 中维护重复关系。

## 10. 轻量化原则

```text
不新增 Source Manager 插件
不复制 Evidence
不做置信度百分比
不做 LLM 自动可信判断
不自动晋级
不修改历史 Verification
```

目标是只建立稳定、可追溯、与具体 Claim 版本绑定的依据链。
