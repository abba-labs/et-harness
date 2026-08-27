# Knowledge Source / Verification v0.1

## 定位

```text
Knowledge    = 当前认知
Source       = 参考依据
Evidence     = 实际运行事实
Verification = 依据与 Knowledge 的 SUPPORT / CONTRADICT 关系
```

归属：

```text
Knowledge / Source / Verification -> Knowledge Manager
Evidence / State                  -> Evidence / State Manager
```

## 数据结构

每个 Global / Project Knowledge Library 都可以包含：

```text
TAXONOMY.yaml
SOURCES.yaml
VERIFICATIONS.jsonl
NNN_*.md
00_INDEX.md          # generated
```

Source ID 在单库内稳定：`SRC000001`。

Qualified URI：

```text
source://global/SRC000001
source://project/<project>/SRC000001

evidence://project/<project>/EV-...
```

## Verification

只有：

```text
SUPPORT
CONTRADICT
```

Verification append-only，不修改、不删除，不复制 Evidence 内容。

Scope：

```text
Global Knowledge <- Global Source
Global Knowledge <- any active Project Evidence
Project Knowledge <- Global Source
Project Knowledge <- same Project Source
Project Knowledge <- same Project Evidence
```

禁止：

```text
Global Knowledge <- Project-private Source
Project-A Knowledge <- Project-B Source / Evidence
```

## v0.1 明确不做

```text
自动晋级 Candidate
自动降级 Validated
百分比置信度
LLM 自动判断可信度
自动改写冲突 Knowledge
```

这一步只提供可追溯的验证事实链，为后续 Validation Policy 提供稳定输入。
