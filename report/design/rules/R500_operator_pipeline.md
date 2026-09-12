---
schema: et.rule-document.v1
number: R500
domain: operator
lifecycle: active
owners: [operator_pipeline]
rule_ids: [ET-RULE-OPERATOR-PIPELINE]
---

# R500 Operator Pipeline / Run Config / Artifact 契约

## 1. 定位

本契约是人工和Agent执行环境检查、代码门禁、构建、部署、目标启动、Formal Case和
报告生成的唯一操作边界。它管理“一次运行如何被配置、选择、确认、执行和留证”，但不定义
IP/Case业务内容、Feature参数、芯片寄存器、板级引脚或仪器测量参数。

稳定入口只有：

```text
run_test.bat / run_config_gui.bat
  -> tools/runner/bootstrap.py
  -> tools/runner/run_pipeline.py
  -> Pipeline Profile中的受控脚本
  -> tools/runner/run_ip_tests.py
  -> Formal Case Registry
  -> Canonical Result -> 当次事实 / Excel -> Agent整理 -> Case Markdown知识
```

## 2. 单一配置源

- `run_config.example.yaml`是Git跟踪的完整模板和字段说明；安全默认值不得触发硬件。
- `run_config.yaml`是唯一生效的本机配置，必须被Git忽略；不得增加同义JSON或第二份配置。
- GUI和命令行必须读写同一个`run_config.yaml`，GUI只能编辑Schema声明的字段，不复制Pipeline逻辑。
- 配置只保存本机工具、DUT镜像与连接、配测设备、仪器连接、运行开关和产物策略。
- IP、P等级和Case定义只属于正式注册表；单次执行范围来自用户指令对应的运行参数或Task Context，Case不得读取`run_config.yaml`。
- TX/RX、Pin、实例配对和板间拓扑属于Bench Profile；单Case量程、触发和Feature参数属于Case/Driver。
- 密码、Token、私钥和Credential不得进入配置、快照或Manifest。

## 3. 配置分区职责

| 分区 | 唯一职责 |
|---|---|
| `config` | 本次配置的人读身份 |
| `target` | 目标形态、逻辑DUT、Pipeline Profile和Bench Profile |
| `pipeline` | 环境检查、代码检查、构建、部署、启动、测试和报告开关 |
| `environment` | 已启用步骤所需的本机工具路径 |
| `dut` | DUT工程、镜像、调试探针、控制通道和期望固件身份 |
| `companions` | 通用配测设备的类型、Profile和基础连接 |
| `instruments` | 外部仪器Driver选择和基础物理连接 |
| `test` | 重复轮数和失败停止策略，不选择IP/Case |
| `output` | `auto`或正式`artifacts/records`根；当前事实与长期知识按第6节固定布局 |

未知字段、错误类型、缺失的已启用步骤依赖、Profile/Target不匹配和仓库外输出必须失败关闭。

## 4. Pipeline Profile边界

`tools/profiles/pipeline/*.yaml`把通用阶段绑定到仓库内已审核脚本。Profile可以包含芯片或
目标形态适配，但必须满足：

- 脚本位于仓库`tools/`内，当前只接受PowerShell脚本；
- 参数只能来自`run_config.yaml`或受审查的Profile字面量；
- 本机绝对路径、COM口、探针号和个人镜像不得写入Profile；
- Profile不得选择IP/Case，也不得执行未在配置中启用的阶段；
- 阶段互斥和前置约束必须显式声明并在执行前验证。

普通新增芯片只增加或调整Profile、Chip/Board配置和专用脚本，不修改公共Runner。

## 5. 安全执行语义

1. Bootstrap只准备`.venv`、依赖和本地配置，然后转交统一Runner。
   `.venv`必须位于当前仓库根目录，依赖指纹只能读取当前仓库的`pyproject.toml`和`uv.lock`；
   禁止复用、写入或硬编码其他工作树、旧仓库和个人目录中的Python环境。
2. `--check-only`只验证配置和当前启用路径所需环境，不创建Run目录、不执行构建或硬件动作。
3. 非Renode目标只要选择真实测试或`hardware_action`阶段，必须显式设置
   `pipeline.confirm_hardware_actions: true`；该字段不是通用授权，具体硬件操作仍须遵守项目人工门禁。
4. Runner使用单机文件锁，禁止两个Pipeline同时占用同一测试环境。
5. GUI中的“软件质量门禁”固定调用`tools/validate_pc.py --skip-tests`，“全量门禁”固定调用
   `tools/validate_pc.py`；两者均不得选择、编译或操作硬件。
6. 单步编译、烧录、启动和测试按钮只执行自身选择的Pipeline阶段，不得隐式运行软件门禁；
   `code_check`只控制“完整流水线”是否在所选阶段前调用唯一总门禁。
7. 测试集合只读取`IP_REGISTRY`和各IP Case Registry；配置和Profile不得旁路注册表。
8. 任一阶段失败返回非零；报告生成不得把pytest FAIL改写为PASS。
9. FPGA PFLASH部署必须在同一次Pipeline运行中依次完成`deploy.bitfile`、
   `deploy.bootrom`和`deploy.firmware`；前两个阶段的`result=PASS` Manifest是唯一有效前置证据。
10. 低层部署脚本只是Pipeline内部阶段。缺少`ET_ARTIFACT_RUN_DIR`、当前Run前置证据或正确顺序时，
   PFLASH脚本必须在任何擦写动作前失败关闭；`-SkipFlash`仅用于不改写PFLASH的受控运行操作。

### 5.1 测试选择与执行级别

Runner只能从正式Registry中执行本次明确选中的集合。选择来源是用户指令对应的运行参数或当前Task Context；
`run_config.yaml`和Pipeline Profile仍不得保存或推断IP/Case集合。

| 执行级别 | 选择范围 | 使用时机 |
|---|---|---|
| Case专项 | 用户指定的一个或多个Case | 单点修复、诊断和复测 |
| IP回归 | 用户指定IP的全部已注册Case | 该IP开发或修复批次完成 |
| 问题批次回归 | 本轮明确受影响的多个Case/IP | 一组同类Bug收口 |
| 全量回归 | 全部已注册IP/Case | 用户明确要求、发布、冻结或最终验收 |

固定规则：

- Registry是可执行全集，不是默认执行范围；没有明确全量指令时禁止自动遍历全部IP。
- 用户指定Case、IP或问题批次时，Runner必须保持该范围；依赖性软件检查可以补充，但不得静默增加无关IP HIL。
- 公共层变化按R002和Task Context运行公共专项检查及代表性IP回归；是否执行全部IP HIL仍由用户指令决定。
- 总软件门禁、IP完整HIL和全部IP HIL是三个独立范围，禁止互相替代或绑定触发。

### 5.2 变更类型与部署矩阵

部署只由实际Diff和目标形态决定，禁止因为“准备测试”就机械重烧所有镜像：

| 实际变更 | FPGA目标 | Silicon目标 |
|---|---|---|
| 仅PC Case、Driver、报告或工具 | 不编译、不烧录、不重启Firmware | 不编译、不烧录、不重启Firmware |
| Firmware源码或工程 | 编译Firmware，并完整执行`bitfile -> BootROM -> firmware/PFLASH` | 编译并烧录Firmware；不执行FPGA专属步骤 |
| Bitfile或BootROM输入 | 从发生变化的阶段开始，并执行其全部下游部署阶段 | 不适用；按目标Profile失败关闭 |
| 仅规则或IP文档 | 只运行相应软件门禁 | 只运行相应软件门禁 |

当前FPGA环境中，即使Bitfile和BootROM源码未变化，只要Firmware发生变化，正式HIL前仍必须重新执行完整三阶段部署；这是当前部署基线，不得由Agent凭历史板上状态跳过。Pipeline Profile负责表达目标差异，Case、Driver和用户配置不得自行拼接烧录命令。

### 5.3 HIL前置契约预检

形成正式FPGA、Silicon或真实仪器结论前，当前逻辑批次必须通过同一套无硬件预检：

```text
规则与代码门禁
-> Formal Case及全部参数execution收集
-> SPEC / REPORT / Registry / Case字段同步
-> Canonical JSON类型往返
-> 代表性真实形状结果的报告模型与Excel导出
```

固定规则：

- 预检只复用现有`tools/validate_pc.py`及其专项Checker/回归，不建立第二套总门禁；
- 总软件门禁**由人工明确指定执行**，且同一源码状态**只跑一次**；任何Runner批量或循环调用都不得隐式或重复触发它。调用Runner本身不构成门禁授权，软件预检选项仅在人工明确指定时启用；
- 专项复测也须由人工明确指定范围与时机；批次代码完成仅要求列出待验证项，未执行记`NOT_EXECUTED`。没有相应真实执行证据不得形成正式HIL通过结论；
- 参数、Evidence字段或报告模板发生变化时，必须覆盖受影响的参数分支和真实数据形状，不能只验证无参数理想样本；
- 定位和修复Bug期间允许单独执行环境检查、编译、烧录、启动或指定Case，不得因此自动运行门禁；
- 软件预检PASS只证明软件契约可执行，不能替代真实硬件PASS。

推荐验证顺序为：

```text
无硬件预检
-> 必要时执行本次选中范围的一个P0冒烟Case并生成报告
-> 执行本次选中Case/IP并生成报告
-> 用户明确要求时执行多IP或完整流水线
```

只有前一级的测试事实、Canonical Result和报告都闭合，才进入下一级；不得先跑完全量HIL再手工修报告。

### 5.4 长时运行的并行职责与调试节奏

回归和Pipeline是长时运行。Agent在运行期间**不得空等**，必须转为可并行的独立工作：

- 运行期间读取**已完成**IP的`records/<CHIP>/<IP>/current/`，按R130 §8.1增量提炼Case知识；
- 禁止反复轮询等待进度（如连续`wait`），按完成通知推进；
- 运行结束后只做收尾复核，证据整理不再集中到最后一轮。

固定调试节奏：

- **全量/多IP回归**：一次跑完本轮全部选中IP，再统一查看失败项；不在回归中途插入单Case调试；
- **单Case调试**：确认失败项后，只运行该Case（`run_ip_tests.py --include-case`）定位与复测，
  不在每次修改后重跑整轮；复测完成必须恢复原选择，禁止形成第二套测试入口。

## 6. 当次运行事实与长期Case知识

全部新增证据进入`records`固定工作区；长期只维护按芯片/IP/Case组织的Markdown知识：

```text
artifacts/                              # 结论性产物；见 6.1
├─ records/<CHIP>/<IP>/
│  ├─ README.md
│  ├─ cases/<CASE_ID>.md
│  ├─ attachments/<CASE_ID>/...  # 仅正文不能替代的必要附件
│  ├─ current/                  # 仅本IP当前一次测试，不按轮次累积
│  │  └─ manifest.json、config/、session.json、cases/<CASE_ID>/<SLOT>/result.json、pytest.log、specification.md、facts.md、publication.json
│  └─ _maintenance/             # 固定锁与可恢复事务；完成后不保留历史副本
├─ records/<CHIP>/_PIPELINE/current/  # 当前公共阶段Manifest、配置、stages和回执
├─ records/_DIAGNOSTICS/<TOOL>/current/ # 独立诊断现场，不代表Formal Case验证
├─ records/_TOOLING/<TASK>/current/    # 软件门禁/工具验证；TASK为稳定主题，不用日期或轮次
└─ reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx  # 每芯片/IP一份最近生成的报告

tmp/                                    # 仓库内本地临时区，gitignore，非证据；见 6.1
```

### 6.1 当前工作区与复用门禁

- `artifacts/`根只允许`README.md`、`records/`、`reports/`、`experience/`及既有只读`runs/`历史。`experience/`是Agent经验库，其分类、命名、结构与维护唯一由`artifacts/experience/RULES.md`约束，不承载测试状态或原始证据。禁止新增或继续写入`runs`，也禁止换用日期、UUID、`round_NN`等目录累积新证据；时间和UUID只写入内容。Formal `current/cases` 第一层为大写`case_id`，第二层为`parameter_id`经`safe_name`得到的 slot（无参数为`noparam`）；不得省略 slot，也不得用`case_run_id`当路径分量。
- Pipeline与独立`run_ip_tests.py`共用单机环境锁；`output.root`只接受`auto`或正式`artifacts/records`根。Bench目标芯片决定`<CHIP>/<IP>/current`，Session芯片必须复核一致。不同芯片/IP互不覆盖；同芯片/IP跨Lane共用当前现场。
- Pipeline通过`ET_ARTIFACT_RUN_DIR`传递`<CHIP>/_PIPELINE/current`阶段根，Manifest引用本轮各IP固定工作区，不复制它们。Case只使用注入的`et_artifact_dir`，不得推导知识根。每个IP自带Manifest、配置快照和Pipeline逻辑ID。整轮测试seal完成前（父或任一目标IP unpublished）不得复用。整轮仅pending时允许覆盖。Agent仍应整轮一起review。
- Manifest记录逻辑Run UUID、配置引用/Hash、Source Revision/Dirty、Target、时间、状态和退出码；配置快照保存真实输入。Lane显式传递，未知身份不得猜测。
- Session终止后，Runner校验Selection、Canonical Result、原始规范Hash及绑定附件，生成当次`facts.md`与待整理回执；可选Excel仅发布到`reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx`，芯片/IP大写，不带时间戳或版本后缀，不在`current`保存副本。
- Excel复用现有Canonical报告模型和三Sheet导出，不重新判定PASS/FAIL。每次只展示该Session；部分执行保留NOT_SELECTED/NOT_EXECUTED，不合并历史PASS。首页明确显示Run ID、Lane、时间和源码/固件身份。
- 同芯片/IP跨Lane共用最近生成报告。新报告完整生成并校验后才同目录原子替换；测试FAIL也更新真实失败报告。导出、校验或替换失败返回非零，保留旧报告和当前原始现场，不把旧报告声称为本次成功输出。
- `--no-report`保留最近生成的Excel且明确提示本次未更新；事实摘要和待整理回执仍生成。Excel不进入原始现场复用Hash，后续报告覆盖不得破坏Case知识整理门禁。
- 当次输出通过`records/<CHIP>/<IP>/_maintenance/`内的IP锁和可恢复事务发布。外部修改、容量不足、未绑定文件、额外目录和损坏证据必须失败关闭。
- 输出完成后回执为待整理状态；脚本不得自动`review`。无论测试PASS或FAIL，`prepare_workspace`可以覆盖Hash完好的pending `current/`。人可以不review。Agent必须review。不得把未review的一轮当作知识闭环。
- Agent可以在测试过程中增量提炼已确认的方法、问题和结论；每轮结束必须完成全部已选Case的整理核对。`review`只接受终止且完整的Session。覆盖看完整性；`review`看知识回执。进行中的增量笔记不能提前完成`review`。
- `review`复核当前原始文件与目录成员，检查本次全部已选Case Markdown及必要附件，刷新索引并绑定知识文件Hash。标有`来源状态：UNVERIFIED`的Case不得确认；须先核对原始来源并说明修正，不能只删除标记。首次没有知识文件时必须先整理；`check`、`index`和重复PASS均不能代替整理确认。
- 临时产物只使用仓库内`tmp/`（已由`.gitignore`忽略）：pytest缓存、流水线环境锁、一次性草稿脚本。`tmp/`不是证据区，内容不进Git，不作为知识或结果引用。仓库代码与配置不得把锁、缓存或脚本写到仓库之外的固定路径；`artifacts/`下的`records`、`reports`、`experience`仍是结论性产物的唯一去向，与`tmp/`职责不重叠。操作系统级临时目录由系统决定，不属于本规则范围。
- 复用前验证原始现场Hash与目录成员。已确认知识Hash仅当`records`非空时验证。pending且`records={}`时没有知识证明可验。知识被改后须再次`review`才能覆盖已review的工作区。
- 人的无人值守连跑可以覆盖已seal且Hash完好的pending工作区。Agent无人值守循环必须在每轮之间review。不得为了连续运行跳过Agent知识贡献。
- 无Case的成功普通阶段可标记复用；失败前置阶段、缺少/损坏回执及未完成Session只能保留，或经人工明确指定的完整现场归档恢复，不因PASS文字清空。
- 测试退出状态与知识整理状态独立。pytest失败仍应输出真实事实；输出失败返回非零并保留工作区。知识确认不是新测试、问题关闭或HIL PASS。

### 6.2 长期知识与轻量工具职责

- 每Case固定一份`cases/<CASE_ID>.md`，IP的`README.md`仅为索引。正文由Agent维护，不设置自动结果机器区；知识内容和适用性归R130。
- 正文按实际知识选用章节，不强制空模板。最小结构包含Case标题、芯片/Lane适用基线、源码或版本说明（未知须明示）、CST更新时间及至少一段非空知识内容。
- 每份Case Markdown最多16 KiB；整理时保留关键结论与未关闭问题，不追加流水账。历史判断发生改变时保留简短、带时间的修正说明，不伪造过去结论。
- 只有波形、截图等无法由简短正文替代的必要材料才进入`attachments/<CASE_ID>/`并从正文显式引用；每Case引用附件合计不超过25 MiB。正文不得依赖旧evidence JSON/ZIP、results.json、旧报告或可覆盖的`current`/`_maintenance`才能读懂。
- `extract`只读当前或历史Session，按Case/精确键提取事实；不会迁移、修改或删除输入。`check`只做最小结构、容量、链接和附件检查，不验证分析正确性。`index`仅显式刷新IP索引并保留索引外说明。
- `review`表示调用者已完成知识整理或确认无新知识，机器只验证完整性；脚本不得自动调用自己作出此判断，不得因PASS自动确认。
- 不生成长期`results.json`、每Case证据JSON/ZIP、累计次数、保护快照或第二套状态历史。旧自动档案可被识别并提示尚未整理，不能作为本次知识确认依据。
- 不增加数据库、通用插件/工作流框架或新的报告格式。长期知识首先可被Agent直接阅读，工具只是辅助。

### 6.3 历史、恢复与容量

- 当前单个工作区最多256 MiB；到限停止并保留输入，不截断必需证据。已seal且Hash完好的pending `current/`对人可覆盖，回收不依赖`review`。unpublished、Hash或目录成员变化、容量超限、环境锁冲突和已有`recovery.zip`仍拒绝回收。Agent仍须review才算知识闭环。
- `archive --workspace ... --output ...`只用于人工显式保留/恢复当前现场；目标固定为该`current`同级尚不存在的`recovery.zip`，写前写后均校验成员与Hash。已有恢复包时停止，要求人工处理；不换名、不按轮次累积，也不自动覆盖恢复包。这不是日常归档或长期知识容器。
- 通用`clean_generated_outputs.py`不得处理`artifacts/runs`、`artifacts/records`或`artifacts/reports`下的芯片目录，包括其中缓存；默认只预览缓存。
- 旧时间戳Run、旧Excel及既有固定JSON/ZIP档案保持只读历史；迁移知识不改写或删除原始输入，不自动批量覆盖旧Case Markdown。历史删除是独立清理任务。
- 独立诊断新输出同样只使用`records/_DIAGNOSTICS/<TOOL>/current`。缺少完成回执的现场保持阻塞，须人工保留/恢复；诊断输出不能冒充Formal Case产品验证。软件验证新日志使用`records/_TOOLING/<TASK>/current`，保留当前批次而非多轮副本。
- 生成事实默认不进Git；已审阅Case知识与必要附件按普通逻辑变更显式提交。当前忽略规则下首次加入须精确`git add -f <已审阅文件>`，不得批量强制加入整个records树。后续已跟踪Markdown正常审阅Diff。
- 单文件超过25 MiB不得直接提交普通Git；大文件需团队确认LFS或外部归档。`artifacts/README.md`只提供导航，不建立第二套语义。

## 7. 扩展规则

| 变化 | 允许修改 | 禁止修改 |
|---|---|---|
| 新增芯片/目标形态 | Pipeline Profile、专用脚本、Run Config模板所需通用字段 | 为芯片复制Runner |
| 新增配测设备/仪器 | `companions`/`instruments`通用连接字段、GUI Schema、对应Adapter | 在Case读取本地连接配置 |
| 新增构建/部署动作 | 先证明现有阶段无法表达，再评审Profile阶段与Runner契约 | 从Profile注入任意命令 |
| 新增IP/Case | IP/Case Registry、Driver、Case和IP契约 | Run Config、公共Runner |
| 新增报告格式 | Reporting转换器，继续消费Canonical Result | 建立第二套PASS/FAIL系统 |

## 8. 验收门禁

本契约由以下证据共同保护：

- `test_operator_launcher.py`：配置、GUI、环境检查、硬件确认、Profile参数、注册表、
  Manifest、固定工作区、多轮复用、Lane传递、报告开关、发布失败语义和可移植路径；
- `test_record_*.py`：事实提取、Markdown不自动改写、索引幂等、链接/容量、事务恢复、整理门禁和显式现场归档；
- Result/Report专项回归：Canonical JSON类型边界、参数化字段闭合、人工展示格式和Excel导出；
- `tools/quality/validate_rule_governance.py`：本契约Owner与生命周期；
- `tools/validate_pc.py`：完整软件回归。

真实编译、烧录、串口和HIL仍须在独立人工门禁后执行；软件门禁PASS不得替代硬件PASS。
