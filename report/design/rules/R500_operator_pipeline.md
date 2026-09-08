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
  -> Canonical Result -> maintain_test_records.py -> 固定Case档案 / Excel
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
| `output` | `auto`或仓库内`artifacts/runs`根；正式工作区与长期档案按第6节固定布局 |

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
- 同一源码状态和同一逻辑批次内，预检结果可供多个已选Case/IP复用，禁止为每个Case重复运行总软件门禁；
- 修复过程中的专项复测先运行Task Context列出的最小专项验证；批次代码完成后统一运行一次总软件门禁，再形成正式HIL结论；
- 参数、Evidence字段或报告模板发生变化时，必须覆盖受影响的参数分支和真实数据形状，不能只验证无参数理想样本；
- 定位和修复Bug期间允许单独执行环境检查、编译、烧录、启动或指定Case，不得因此自动运行门禁；
- 逻辑修复批次完成后、形成正式HIL结论或提交代码前必须单独运行“全量门禁”；
- 软件预检PASS只证明软件契约可执行，不能替代真实硬件PASS。

推荐验证顺序为：

```text
无硬件预检
-> 必要时执行本次选中范围的一个P0冒烟Case并生成报告
-> 执行本次选中Case/IP并生成报告
-> 用户明确要求时执行多IP或完整流水线
```

只有前一级的测试事实、Canonical Result和报告都闭合，才进入下一级；不得先跑完全量HIL再手工修报告。

## 6. 原始运行证据与人读报告

正式入口使用一个固定工作区和按芯片/IP固定的长期档案，不按测试次数增加目录：

```text
artifacts/
├─ runs/current/
│  ├─ manifest.json
│  ├─ config/run_config.snapshot.yaml
│  ├─ stages/<stage>/...
│  ├─ tests/<ip>/session.json、cases/<case_run_id>/...、pytest.log
│  └─ publication.json
├─ records/<CHIP>/<IP>/
│  ├─ README.md、results.json、test_report.xlsx
│  ├─ cases/<CASE_ID>.md
│  └─ evidence/<CASE_ID>.json、<CASE_ID>.zip
└─ reports/  # 历史或显式一次性导出；不是正式入口的日常输出
```

### 6.1 工作区和发布

- `artifacts/`根只允许`README.md`、`runs/`、`records/`、`reports/`。芯片/IP/Case使用稳定标识；时间和UUID写入内容，不写入日常档案目录名。
- Pipeline与独立`run_ip_tests.py`共用单机环境锁。`output.root`只接受`auto`或正式`artifacts/runs`根；不得通过自定义子目录恢复按Run增长。
- 每轮结果均写入`current/tests/<ip>/`；先发布上一轮，再复用同一路径，不增加`round_NN`。Case内部临时UUID目录不进入长期档案。
- Pipeline通过`ET_ARTIFACT_RUN_DIR`传递同一工作根；Case只使用注入的`et_artifact_dir`，不得推导档案根。
- Manifest记录独立逻辑Run UUID、配置引用/Hash、Source Revision/Dirty、Target形态、时间、状态和退出码；配置快照保存真实输入。Lane由目标形态显式传递，不根据固件名称猜测。
- `maintain_test_records.py update`是档案更新入口。Session必须终止；校验原始规范Hash、Selection、Canonical Result和已绑定附件后，只增量更新本次Case/参数。
- 更新在`artifacts/runs/record-maintenance/`暂存并持有IP锁；多文件发布使用可恢复事务。中断后先恢复、再校验旧档案；外部修改、容量不足或证据损坏必须失败关闭。
- 工作区复用前必须验证`publication.json`：文件Hash和目录成员未变，所需Case快照仍在档案内，或现场已被显式归档完整覆盖。未绑定文件、额外目录、未完成Session不得静默丢弃。
- 已发布Case的普通工作日志可在下一次运行时回收；无Case的成功普通阶段可标记复用。失败的前置阶段、未发布或损坏现场必须保留，直到人工显式归档；不得仅凭PASS文字清空。

### 6.2 固定档案

- 每Case固定一份Markdown、一份结构化证据JSON和一个扁平Hash附件ZIP；同Case的参数/Lane放在文件内部，不再建子目录。
- JSON保留实际Canonical事实；ZIP保存被引用的原始Session、Result、规范、配置/Manifest（有提供时）和附件字节。Markdown机器区、IP汇总和Excel只读派生，结果语义归R130。
- `cases/*.md`机器区只由工具更新；Agent仅维护标记外的方法补充、问题分析、下一步和最近3条关键变化。人工区最多16 KiB，不追加每轮流水账；需保留的旧结论先显式归档。
- 测试前Agent读取目标Case当前记录、原始方法和未关闭问题；测试后先更新并检查档案，再补充证据支持的分析。不得手工改机器结果、删除失败快照或将分析猜测写成已验证结论。
- `--no-report`或关闭报告阶段只省略Excel，JSON与Markdown仍须发布；开关变化与其他派生文件在同一事务中处理，不能留下旧Excel冒充当前报告。
- `check`默认只读；显示算法升级或派生视图损坏时，可显式`check --refresh-views`。必须先通过目录成员、容量、原始记录与附件Hash校验，只重建派生文件并保留人工区，禁止修补原始事实；完整检查通过才提交事务，失败回滚。
- 开启报告时，Pipeline成功要求pytest成功、选中execution完整、证据满足、档案检查通过、Excel成功生成且Manifest退出码一致。报告生成失败必须保留工作区并返回非零；测试FAIL仍应发布真实失败记录。
- 手工导入旧证据或重新生成Excel不能回写旧Manifest，也不能把历史FAIL变成新的Pipeline/HIL PASS。

### 6.3 容量、归档和整理

- 每Case最多64个受保护快照；Case结构化记录加解压附件最多25 MiB；每IP当前档案与单个工作区最多256 MiB。达到上限时停止发布并保留输入，不截断必需证据、不自动淘汰未解决失败。
- 日常成功复测只保留当前快照及累计次数；失败、首次修复和显式基线的保护语义归R130。不存在无限历史列表、自动阶段归档或第二套结果数据库。
- `archive`只能写入人工明确指定、尚不存在的单个ZIP，必须在当前档案/工作区之外；写前和写后均校验成员与Hash，禁止覆盖归档。
- 每个显式归档目标目录最多16个ZIP、总计1 GiB；超限要求人工管理，不自动换目录绕过限额。
- `prune --archive <file> --case <id>`默认只预览；只有追加`--execute`且归档覆盖该Case全部待释放保护快照时才释放。保留当前快照、累计计数与人工分析，不改变结果。
- 通用`clean_generated_outputs.py`不得处理`runs/current`、`artifacts/records`或`artifacts/runs/record-maintenance`，包括其中的缓存；中断工作区只能经维护入口的显式归档恢复。
- 旧时间戳/年月日Run和Excel保持只读，可经显式`update --source`校验导入，迁移不得修改或删除源目录。删除历史运行是独立清理任务，不得混入功能开发。
- 现有独立诊断脚本的时间戳目录保留兼容；其输出不是Formal Case档案，不能冒充产品验证。不得据此为正式入口新增时间戳路径。
- 生成证据默认不进Git；显式审阅后才可提交必要证据。单文件超过25 MiB不得直接提交普通Git；大文件需团队确认LFS或外部归档。
- `artifacts/README.md`只提供目录与命令导航，不建立第二套强制语义。

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
- `test_record_*.py`：增量、幂等、原始字节、受保护证据、容量、事务恢复、只读检查和显式归档/释放；
- Result/Report专项回归：Canonical JSON类型边界、参数化字段闭合、人工展示格式和Excel导出；
- `tools/quality/validate_rule_governance.py`：本契约Owner与生命周期；
- `tools/validate_pc.py`：完整软件回归。

真实编译、烧录、串口和HIL仍须在独立人工门禁后执行；软件门禁PASS不得替代硬件PASS。
