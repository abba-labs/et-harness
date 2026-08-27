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
报告生成的唯一操作边界。它只管理“一次运行如何被配置、确认、执行和留证”，不管理
IP/Case选择、Feature参数、芯片寄存器、板级引脚或仪器测量参数。

稳定入口只有：

```text
run_test.bat / run_config_gui.bat
  -> tools/runner/bootstrap.py
  -> tools/runner/run_pipeline.py
  -> Pipeline Profile中的受控脚本
  -> tools/runner/run_ip_tests.py
  -> Formal Case Registry
  -> Canonical Result / Excel Report
```

## 2. 单一配置源

- `run_config.example.yaml`是Git跟踪的完整模板和字段说明；安全默认值不得触发硬件。
- `run_config.yaml`是唯一生效的本机配置，必须被Git忽略；不得增加同义JSON或第二份配置。
- GUI和命令行必须读写同一个`run_config.yaml`，GUI只能编辑Schema声明的字段，不复制Pipeline逻辑。
- 配置只保存本机工具、DUT镜像与连接、配测设备、仪器连接、运行开关和产物策略。
- IP、P等级和Case选择只属于正式注册表；Case不得读取`run_config.yaml`。
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
| `output` | 仓库内`artifacts/runs`原始运行证据根策略；Excel报告固定进入`artifacts/reports` |

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
2. `--check-only`只验证配置和当前启用路径所需环境，不创建Run目录、不执行构建或硬件动作。
3. 非Renode目标只要选择真实测试或`hardware_action`阶段，必须显式设置
   `pipeline.confirm_hardware_actions: true`；该字段不是通用授权，具体硬件操作仍须遵守项目人工门禁。
4. Runner使用单机文件锁，禁止两个Pipeline同时占用同一测试环境。
5. `code_check`只调用唯一总门禁`tools/validate_pc.py`。
6. 测试集合只读取`IP_REGISTRY`和各IP Case Registry；配置和Profile不得旁路注册表。
7. 任一阶段失败返回非零；报告生成不得把pytest FAIL改写为PASS。
8. FPGA PFLASH部署必须在同一次Pipeline运行中依次完成`deploy.bitfile`、
   `deploy.bootrom`和`deploy.firmware`；前两个阶段的`result=PASS` Manifest是唯一有效前置证据。
9. 低层部署脚本只是Pipeline内部阶段。缺少`ET_ARTIFACT_RUN_DIR`、当前Run前置证据或正确顺序时，
   PFLASH脚本必须在任何擦写动作前失败关闭；`-SkipFlash`仅用于不改写PFLASH的受控运行操作。

### 5.1 HIL前置契约预检

任何FPGA、Silicon或真实仪器Formal Case运行前，当前源码必须先通过同一套无硬件预检：

```text
规则与代码门禁
-> Formal Case及全部参数execution收集
-> SPEC / REPORT / Registry / Case字段同步
-> Canonical JSON类型往返
-> 代表性真实形状结果的报告模型与Excel导出
```

固定规则：

- 预检只复用现有`tools/validate_pc.py`及其专项Checker/回归，不建立第二套总门禁；
- 参数、Evidence字段或报告模板发生变化时，必须覆盖受影响的参数分支和真实数据形状，不能只验证无参数理想样本；
- 预检失败必须在任何烧录、复位、上电或Formal HIL动作前停止；
- 软件预检PASS只证明软件契约可执行，不能替代真实硬件PASS。

推荐验证顺序固定为：

```text
无硬件预检
-> 单IP一个P0冒烟Case并生成报告
-> 单IP完整HIL并生成报告
-> 多IP或完整流水线
```

只有前一级的测试事实、Canonical Result和报告都闭合，才进入下一级；不得先跑完全量HIL再手工修报告。

## 6. 原始运行证据与人读报告

非`check-only`调用必须只创建一个原始运行根，并把Excel派生报告集中输出：

```text
artifacts/
├─ runs/<run_id>/
│  ├─ manifest.json
│  ├─ config/run_config.snapshot.yaml
│  ├─ stages/<stage>/...
│  └─ tests/<ip>/...
└─ reports/
   └─ <YYYYMMDD_HHMMSS_microseconds>_<CHIP>_<IP>测试报告.xlsx
```

固定规则：

- `artifacts/`根目录只允许`README.md`、`runs/`和`reports/`；不得新建平行的
  `case_runs/`、`firmware_build/`、`flash_run/`或其他顶层产物分类；
- `run_id`直接位于`runs/`下，不增加年月日桶或第二层执行时间戳；
- 默认`test.repeat: 1`时，IP结果直接写入`tests/<ip>/`，不得增加`round_01`；只有显式多轮执行时才使用`round_<NN>`隔离各轮原始结果；
- Pipeline通过`ET_ARTIFACT_RUN_DIR`把同一目录传给所有子步骤；
- Manifest至少记录配置引用与Hash、源码Revision/Dirty状态、目标形态、开始/结束时间、状态和退出码；
- 配置快照保存实际输入，Manifest使用可移植引用，不固化个人绝对路径；
- Case只使用注入的`et_artifact_dir`，不得推导仓库根或另建产物分类；
- 日志、Canonical Result、波形和截图只进入本Run目录；
- Excel报告只从Canonical Result只读生成，统一放入扁平的`artifacts/reports/`并使用完整时间戳命名，不在报告目录复制原始证据；
- 人工结论另存`report/`并引用对应Run证据或Excel报告。

当本次配置同时启用Formal Case和报告阶段时，Pipeline成功必须同时满足：

```text
pytest/Canonical Session完成
+ 每个选中IP的Canonical Result完整
+ 每个选中IP的Excel报告成功生成
+ Run Manifest状态与最终阶段退出码一致
```

测试PASS但报告缺失、报告字段无法解析、报告生成异常或Manifest与实际阶段状态矛盾时，本次Pipeline必须失败。
修复报告代码后手工重生Excel只能证明只读转换器已经恢复，不能回写旧Manifest或把旧失败Run改成正式PASS；
需要发布完整流水线PASS时，必须对受影响阶段或完整Pipeline重新执行并产生新的Run证据。

产物生命周期规则：

- 正式测试产物允许提交Git；缓存、临时锁和可重新生成的中间文件不得进入`artifacts/`；
- 单文件超过25 MiB时不得直接提交普通Git历史；大波形、bitstream等应裁剪、压缩或经团队确认后使用Git LFS，并在Manifest中保留说明；
- 旧仓库外产物不迁移、不复制，也不作为新运行输入；现存年月日桶只作为只读历史，不得继续追加；
- 删除历史运行必须是独立、可审阅的清理变更，不得混入功能开发；
- `artifacts/README.md`只提供本契约的目录使用导航，不得定义新的强制语义；发生冲突时以本契约为唯一权威。

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
  Manifest、顶层目录分类、默认单轮扁平路径、多轮隔离、报告时间戳与防覆盖、报告失败语义和可移植路径；
- Result/Report专项回归：Canonical JSON类型边界、参数化字段闭合、人工展示格式和Excel导出；
- `tools/quality/validate_rule_governance.py`：本契约Owner与生命周期；
- `tools/validate_pc.py`：完整软件回归。

真实编译、烧录、串口和HIL仍须在独立人工门禁后执行；软件门禁PASS不得替代硬件PASS。
