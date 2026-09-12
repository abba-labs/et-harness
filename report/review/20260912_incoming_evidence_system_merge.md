# DeepSeek证据系统同步与待修正清单

Time: 2026-09-12 17:00 CST
Status: 文件同步完成；测试 NOT_EXECUTED；不代表证据语义审查通过。

## 同步范围与边界

- 来源：`D:/lihuan/vibe_code/et-harness/workspace/ET_ATP_Testing`。
- 目标：`D:/lihuan/vibe_code/codex/projects/ET_ATP_Testing`。
- 来源版本：`18c79e6fc6379a98077366b29e9e8f27782ceac1`；对比基线：`ef541ce1`。30个提交涉及344个路径。
- 342个路径完成文件级同步，包括证据整理/发布、Runner、治理工具、规则与Case知识。未执行Git merge、暂存、提交、推送或分支切换；两目录共用Git工作树元数据，按人工要求不调整该关系。
- 保留本地18个ETIM开发文件；其中17个保持原字节，`test_case_doc/etim/ET6801_etim.md`仅合并3处旧证据路径说明，保留本地实现说明。不把源侧残缺句子直接覆盖过来。
- `firmware/build/et6801/core1_peer/ET6801_Core1_Peer.generation.json`保留本地生成路径，不复制来源机器路径。
- 同步前副本：`tmp/incoming-sync/before/`；同步路径、源哈希和ETIM原哈希：`tmp/incoming-sync/manifest.json`。这些是临时恢复材料，不是测试证据。
- 未迁入源侧原始current现场或运行回执，不能将源侧历史PASS当成本地当前版本PASS。

## 人工裁决落实

AGENTS、R002、R004、R500明确：专项测试、总门禁仅由人工指定执行；批次完成、提交前、公共层变化不自动授权执行。未指定记录为`NOT_EXECUTED`，不降低断言或伪造通过。

新证据遵循R500稳定的`records/<CHIP>/<IP>/current/`及对应_PIPELINE、_DIAGNOSTICS、_TOOLING目录。禁止新写`runs/`。

人工已授权删除整理过的目标`artifacts/runs`。删除工具调用被策略拒绝，目录尚未删除；其中存在指向共享Node依赖的node_modules联接，后续清理只能删除联接本身，不能递归删除其外部目标。本次不绕过限制。

## 待修正事项（非本次已修复项）

1. 来源10个IP共206份Case知识的头部来源SHA与所对照session不一致：AES 26、CORDIC 24、CRC 23、DMA 28、FMAC 23、SPI 12、STIMER 16、SYSCNT 7、UART 33、WDG 14。需逐项重建真实来源关系，不能批量改成当前SHA。CAN现场后续变化，未计入此数量。
2. IPCM_P0_001知识正文Session与对应现场不一致；CRC已发布标记不证明知识来源正确。发布Hash仅证明内容固定，不证明语义正确。
3. `_publication_pending`将读取/解析错误视为非pending，需区分无回执与损坏回执；platform-common任务的chip约束需另行审查。
4. 经验库仍有旧runs输出路径、旧自动门禁和覆盖流程描述，后续统一纠正；历史经验不能覆盖上述现行规则。
5. `watch_pipeline_log.py`识别PASS未充分绑定当前运行身份；IPCM诊断默认端口和心跳判断也需收紧，未执行诊断或硬件操作。
6. current回执含绝对根路径绑定，不得通过直接复制或改写身份声称已在本地复核。

## 检查与验证状态

已执行：启动身份检查、文件差异审阅、同步时SHA256核对、ETIM保留检查。未运行专项测试、总软件门禁、构建、仿真、烧录或HIL，全部`NOT_EXECUTED`。没有新建Task Context或宣称治理门禁通过；保留现有脏工作树。下一步先纠正证据来源与残留规则，再由人工指定需要运行的验证。

## 2026-09-12 17:28 CST 同步与清理收口记录

本节更新上述历史状态，不改写当时记录。

- 来源仍为18c79e6f且工作树干净。342个同步路径全部存在，来源Hash与同步清单一致，无新增遗漏；本地差异为ETIM保留项及随后明确修订。两份机器专属/重叠文件仍按“同步范围与边界”处理，没有强行覆盖。
- R002及编译器支持人工授权的固定脏树基线；已创建独立任务上下文，新增修改按原授权范围检查。没有暂存、提交、推送或变更共享Git元数据。
- 来源数量更正：196份是095cd6db与现存228df5bd Session不符；10份WDG混用其他历史基线；另1份IPCM Session引用不符。共207份保持UNVERIFIED，原文与来源冲突说明均保留。没有伪造正确版本、复制源侧current回执或把源侧PASS当成本地当前PASS。
- 已实现：损坏/不可读/非布尔pending回执失败关闭；来源UNVERIFIED阻止review；review相对路径统一；日志等待绑定精确Run ID与Manifest终态；IPCM诊断要求显式探针及人工硬件确认、固定输出路径，并通过两次读取确认心跳进展。均未运行回归或硬件，不宣称行为已验证。
- 已清理经验库中的自动门禁建议、搬回runs的恢复路径、pending复用的过时说法、临时脚本误放_TOOLING的建议；旧DSH工具差异不再被表述成绕过当前工具限制的许可。各主题保留修订时间和历史事实。
- 已删除本次用完的2个临时脚本。`tmp/incoming-sync/before/`和manifest保留为尚未提交修改的恢复材料；不把它们发布成测试证据。
- `artifacts/runs`仍存在。此前执行删除被工具策略拒绝，本轮未换解释器/API绕过。其node_modules联接指向共享依赖，后续人工删除时必须仅删除联接本身，不得递归进入共享目标。

检查范围：只读Git/文件Hash/数量检查、任务上下文编译与Scope检查；19路径源码/文档增量Scope检查通过（记录写入前）。专项测试、总门禁、构建、仿真、烧录、HIL均NOT_EXECUTED；没有新测试PASS。

未完成：207份历史正文与具体轮次/观测的完整对应关系尚不可确认，保持隔离；平台公共任务被要求点名chip的设计问题保留待审；runs物理删除仍需解除工具限制或由人工处理。同步完整不等于这些证据已获发布确认。
