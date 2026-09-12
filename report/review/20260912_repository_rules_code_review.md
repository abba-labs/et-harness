# 仓库规则一致性与代码人工审查

时间：2026-09-12 17:47 CST

## 范围与结论

人工明确指定：执行一次总软件门禁，然后由Agent对照规则本地Review，不使用CodeRabbit。范围为platform-common的软件、注释、规则导航和证据文档；未执行硬件、烧录或Keil，未修改业务代码，未Commit/Push。

源码HEAD：`18c79e6fc6379a98077366b29e9e8f27782ceac1`，`codex_dev`，工作树包含既有ETIM与同步修正。固定审查基线由`project-governance/runtime/repository-rules-review.json`及其配套快照记录。不能把本次结果归为干净HEAD验证。

人工静态阅读了R001/R002/R220/R330/R130/R500、门禁入口、相关治理和证据工具，抽查ETIM Service/Wrap及CRC知识正文。不是逐文件完整业务正确性审计；没有检查所有Excel成品的视觉排版，也没有将语法通过当作文档或硬件通过。

## 实际门禁结果

命令：本项目resource guard内执行正式仓库`.venv/Scripts/python.exe -u tools/validate_pc.py`，2026-09-12 17:44 CST，退出码1。

- Python syntax：PASS。
- Ruff format：FAIL，7文件需要格式化，670文件格式已符合。
- Ruff lint及其后的Owner、Context、IP契约、注释语义、Firmware、单元测试、Case收集和Excel导出：NOT_EXECUTED。总入口在首个失败处停止，没有拆开补跑或跳过失败。
- [原始门禁日志](../../artifacts/records/_TOOLING/repository_rules_review/current/software_gate.log)。门禁入口SHA256：`5A71500C67565D88F3332F1FCBAD4137A8FB51CD231166B710CD035B9E512F1A`。

## 已确认问题

### 1. P1：独立Task Context没有接入总门禁

`tools/validate_pc.py:28,94-116,172-179`固定读取`current_task_context.json`，CLI没有Context参数。R002及导航README支持用独立`--output`保留既有脏树；本次新Context有效，但默认Context仍为2026-09-08的ETIM任务。格式修好后总门禁仍会检查错误任务，而不是本次固定边界。此项为静态确认，门禁尚未走到该阶段。

建议：给唯一总门禁显式Context选择并传给check/scope-check；默认行为保持兼容，校验所选Context的身份、完整性和固定基线。不得复制/改写旧ETIM上下文来伪装本次授权。

### 2. P1：IPCM诊断固定输出绕开现场复用约束

`tools/runner/ipcm_peer_mailbox_probe.py:63-71,101-102,145-148`在固定current直接建目录、覆盖命令/日志/JSON，没有调用已有工作区完整性与复用检查，也未产生完成回执。重复调用可以覆盖未完成或已改变的独立诊断现场；若直接写入已seal的Pipeline/stages，会使回执Hash失效。限定输出路径和人工硬件确认并不能保护旧现场。与R500 §6.1/6.3冲突。

建议：独立诊断复用现有工作区检查/锁/完成发布机制；Pipeline模式只允许所属活动阶段写入，不接受改写已seal现场。缺少回执或Hash变化时保持现场并报告，不自动清空。

### 3. P2：Python格式未收口

实际失败的7文件：

- `pc/et_test_platform/framework_validation/unit/code_quality/test_task_context_governance.py`
- `pc/et_test_platform/framework_validation/unit/operator/test_record_cli.py`
- `pc/et_test_platform/framework_validation/unit/operator/test_record_pipeline_monitor.py`
- `tools/governance/compile_task_context.py`
- `tools/runner/ipcm_peer_mailbox_probe.py`
- `tools/runner/record_workspace.py`
- `tools/runner/watch_pipeline_log.py`

违反R220 §2。属于前序同步修正未验证的问题，不能全部归因于源分支。建议仅机械格式化这些文件，保留语义和用户ETIM修改；本次未执行修复。

### 4. P2：ETIM Wrap存在无大括号控制语句

`firmware/wrap/src/et_etim_wrap.c:33-35,114-116,143-145`等处使用不带复合语句的if，部分if与return之间还有空行；不符合R330 §3控制语句Allman大括号及相邻关系要求。文件属于平台Wrap受控范围，不适用芯片SDK格式豁免。

建议：按R330补完整控制块，机械格式修复不改变条件、返回值或调用顺序。这是保留的ETIM工作，未在本次改写。Firmware门禁尚未执行，此处为人工静态发现。

### 5. P2：公共任务参数文档与编译器冲突

`project-governance/README.md:101-112`列出多个公共模块任务无需芯片；`tools/governance/compile_task_context.py:1154-1165,1202-1214`却对这些非豁免模块在缺少chip时拒绝编译。规则R002新增pending检查也要求点名目标，但项目又要求公共层芯片中立。调用者照速查表操作必然被阻塞，并被迫为公共工作指定无关芯片。

建议：在R002明确“有实际目标的任务”和“纯公共代码任务”的pending检查边界，同步模块参数、README、编译器和回归；不得靠随机填写ET6801规避检查。

### 6. P2：注释宣称必写JSON，实际异常路径不保证

`tools/runner/ipcm_peer_mailbox_probe.py:96-99`的`subprocess.run(timeout=30)`位于异常处理块之前。启动失败或超时直接抛出，第二次采样失败还会丢失第一次已采集但尚未落盘的输出；`143`行“probe must always write JSON”与实际实现不符。固定JSON若已有旧内容，会继续残留。

建议：把进程启动、超时和采样持久化纳入失败处理，在保留既有现场约束下发布明确的本次失败身份和已获取日志；不能只改注释为“可能失败”而继续留下易误认的旧结果。

### 7. P2：工具注释检查有覆盖缺口，且已有过时说明

R220定义Python公共API注释规则，但`tools/validate_pc.py:233-240`只向注释Checker传PC目录，Checker的`_is_project_module`（`tools/quality/check_pc_documentation_rules.py:45-47`）也仅接受`pc/et_test_platform`。工具目录虽进入Ruff/AST检查，其自然语言模块/API说明并不进入同一注释语义检查。

实例：`tools/runner/maintain_test_records.py:3`仍写“确认后才允许复用原始工作区”，实际`record_workspace.py:172-175`明确`require_review=False`，R500也已区分“人可覆盖pending”与“Agent必须review”。`watch_pipeline_log.py:2-3`声称读取日志，而实现只读Manifest；两个诊断入口的公开main也缺少定义前的用途边界说明。

建议：修正具体注释，并由R220明确工具/测试的适用要求，使Checker覆盖范围与规则一致；不要批量生成空泛占位注释。

## 文档与清理状态

- 正式仓库`artifacts/runs`已经不存在，确认人工删除完成。旧历史报告保持原样；ACTIVE中的当前“删除受限”描述应更新为本次事实。
- 全部207份来源未核实Case仍有`来源状态：UNVERIFIED`；抽查CRC正文保留了历史声明及来源冲突说明。这是尚未闭合的证据问题，不是本次新测试失败，也不能删除标记冒充审核完成。
- 本次对目标Runner及芯片文档的旧runs路径搜索未发现新写入入口；排除列表与历史说明中的字样不应机械替换成current。此结论仅覆盖已检查路径。

## 建议修复顺序

先修独立Context接入和诊断现场保护，再收口Python/C格式及真实注释、公共参数规则一致性；207份证据来源另行逐项核对。后续门禁仍由人工明确指定，不能将本次授权无限延长为自动修复重跑循环。

## 2026-09-12 18:11 CST 修复与软件门禁闭环

人工追加授权“把问题修复完，完成门禁测试”。上述七类软件问题已修复；原审查内容保留为修复前事实。

- 问题1：总门禁新增显式`--context`并向freshness/scope检查传递同一文件；显式路径缺失即失败，不退回默认任务。新增选择与拒绝回退回归。
- 问题2、6：Peer Mailbox仅允许独立诊断current，不再接受Pipeline输出；复用R500环境锁、现场校验、原子写入与成功发布回执。每次采样立即保存输出；超时/启动失败产生本次失败JSON，保留已采样日志和未发布现场，下一次不能覆盖。模拟回归覆盖成功复用、篡改拦截、第二次超时/启动失败和Pipeline路径拒绝。
- 问题3：受影响Python文件机械格式化；后续门禁发现的scope函数复杂度超限通过提取基线指纹校验函数修复，没有调高阈值或屏蔽检查。
- 问题4：ETIM Wrap的15处单语句if补齐控制块并按R330格式化；对修复前后内容去除空白和大括号后核对一致。未改变条件、调用或返回表达式。
- 问题5：R002、导航README和编译器统一为“无实际目标的公共软件任务可不填芯片；有IP目标或FPGA/HIL执行仍要求芯片”。保留针对实际目标的知识pending检查，回归覆盖公共任务及HIL拒绝路径。
- 问题7：修正过时工具说明及公开入口注释；工具注释检查覆盖工作树和显式Git基线中的新增/修改工具整文件，模块头不得冒充首个API注释。未触碰工具历史全树不宣称全部合规；PC原有全树检查保持。

主要修改文件：`tools/validate_pc.py`、`tools/governance/compile_task_context.py`、`tools/quality/check_pc_documentation_rules.py`、`tools/runner/{ipcm_peer_mailbox_probe,record_workspace,maintain_test_records,watch_pipeline_log}.py`、相应治理/注释/Operator回归、`firmware/wrap/src/et_etim_wrap.c`、R002/R220及导航和工具README。

范围分批冻结并核对：governance、tooling、firmware-final分别通过8、10、1个变化路径检查；最后以`project-governance/runtime/rules-fix-final-gate.json`固定已完成批次，继续核对最终治理修复。不覆盖旧ETIM任务Context，不重置基线来隐藏未授权变化。提前编译的`rules-fix-firmware.json`未用于写入。

完整命令：resource guard内运行正式仓库`.venv/Scripts/python.exe tools/validate_pc.py --context <formal-root>/project-governance/runtime/rules-fix-final-gate.json`，未传`--skip-tests`。

2026-09-12 18:04—18:10 CST，退出码0：

- Python语法、678文件Ruff格式、Lint、规则Owner、Context与范围、公共IP/芯片适配契约、PC架构与注释：PASS。
- 14份Formal文档、实现绑定、8份规划文档、人工审查行语法与Case编排：PASS。
- Firmware架构、109文件C格式、112文件全树质量、4文件增量严格语义数字检查及生成工程契约：PASS。
- 单元/契约/Native测试集合：2084 PASS、18 SKIP；跳过项不计作验证通过，不据此声称全部Native执行完成。
- Formal Case全量收集及14类XLSX导出：PASS。导出使用空软件Session，只验证导出链与容器，不是硬件结果或Excel逐页视觉验收。

[完整门禁日志](../../artifacts/records/_TOOLING/rules_fixes/current/software_gate.log)；
日志SHA256：`239147299AE19FA7A8119B319D4627B8F5B2F63226ACE3B6F0914A148E3DA782`；
门禁入口SHA256：`38FD901B4A590D3175A6AFAACF099A84AE10EE95FF7C2F15A6E78B583B897372`。

验证对象是包含用户既有ETIM和同步修改的工作树，不是干净HEAD。门禁后仅补本记录和控制状态。再次确认`artifacts/runs`不存在；207份UNVERIFIED来源记录完整保留，须另行逐项溯源。未运行真实硬件、Keil、烧录或HIL，未暂存、Commit、Push或切换分支。此轮授权完成后，后续门禁仍等待人工指定。
