# CAN改造验证与独立Review操作单

本文件规定后续需要执行的验证，不记录本轮已通过的测试。配合008、009、010逐卡使用。只读源码、收集测试、正常返回的模型，均不能单独证明真实CAN工作。

## 1. 四个状态必须区分

| 状态 | 足够的证据 | 尚不能说明 |
|---|---|---|
| COLLECTED | 真仓库成功导入/收集所选函数和参数，原始输出与SHA | Case正文执行、硬件行为 |
| SOFTWARE_VALIDATED | 正文真实执行、真实接口/Codec链、正常和错误路径、对应C/native证据 | 台架时序、总线、电路工作 |
| HIL_NOT_EXECUTED | 明确尚无当前SHA的实际硬件执行 | 不能借用旧SHA的HIL PASS |
| VERIFIED_FOR_SELECTED_SCOPE | 软件验证合格、批准的同设备同连接HIL复测、参数和证据对应当前SHA | 未选实例/新芯片/未覆盖场景 |

`REQUEST_CHANGES`表示存在已确认问题；`READABILITY_EXCEPTION_REVIEW_REQUIRED`表示正确性证据已具备但正文超过20行，需要对不可拆硬件关系的独立复核。两个状态可以同时存在，不能用长度理由豁免正确性。

## 2. 每张卡先写的对照表

开发前产生一个简短、可核对的文件，至少具有下列列。缺一项不是“默认保留”。

| 列 | 内容要求 |
|---|---|
| property_id | 例如ECC.REPEAT.UNMASK、DMA.RX.FIFO、RX.DATA.BYTE_EXACT |
| B位置 | d6b91b65…的文件、函数、行范围、原表达式 |
| 前置与输入 | 源、模式、阈值、两Pattern、长度、所选实例、支撑设备 |
| 原动作顺序 | 具体方法及参数；说明读清、副作用和等待前提 |
| 原Expected | 在设备返回前确定；指向原契约/向量 |
| 新位置 | 新Case/参数和表达式，或运行层接收位置 |
| 处置 | KEEP、MOVE、MERGE_DUPLICATE、SPLIT、SCOPE_OUT |
| 允许变化的理由 | 例如移出JSON；不能仅写“冗余” |
| 正向验证 | 实际命令、节点、结果与日志路径 |
| 错误反例 | 改什么、应该在哪个判据失败、实际结果 |

允许SCOPE_OUT的既定情况是用户确认的多实例范围，不包括payload、时序、窗口、错误状态。CASE名字中有`recovery`时，必须指明本Case自己在此前建立了什么故障/停钟/满状态。

## 3. 执行检查：三种测试不能互相替代

### 3.1 真实接口与类型检查

需要在真实仓库和真实依赖环境导入CanDriver、SysctrlDriver、DmaDriver、ResourceDriver及其dataclass/枚举。不是从源码抄几个方法到一个空文件测试。

检查每个新/改变调用的签名：位置参数、关键字参数、默认值、返回字段、枚举名、Mapping键。构造后应返回真实数据类型，不让Mock自动创造字段。

本批固定反例：

- 三参数调用旧`configure_dma_request`应因真实签名错误被检测；正确调用是V2。
- `CAN_DMU_REQUESTS[id]`没有rx0/rx1；RX源由CAN命令选择。
- ResourceRef没有slice，不能在测试替身中临时加slice。
- CanDmuCounters没有tx_count/rx0_count/event_count等虚构字段。
- CanDmuEventImage的实际成员是event，不是details.event。
- `dmu_rx_image_decode`必须得到FIFO而不是帧序号。

仅对Mock调用时，使用`create_autospec(真实对象, spec_set=True)`限制不存在方法与签名；返回值仍使用真实dataclass。autospec不会自动保证全部返回语义，因此它只是第一道检查。

依据：Python官方文档说明autospec检查调用签名、spec_set约束属性：
https://docs.python.org/3.12/library/unittest.mock.html#autospeccing

### 3.2 真实Python调用链

至少执行：真实Case正文 → 真实公开Driver → 真实Codec → 真实TargetClient → 被替换的最底层Transport/测试后端。替换层越高，证据等级越低，必须写清。

不得在`sys.modules`塞假的et_test_platform包使导入通过。不得用`__getattr__`把任何未知方法都变成成功。不得仅手动调用一条reset然后宣称所有Case都执行过。

记录每个请求的service/command/instance/body与响应，检查：

1. 参数节点到真实Case分支的执行关系；不能把collect称为execute。
2. 写命令发生次数、关键先后顺序和实际参数。
3. 读命令返回的实际结构字段是否被该断言消费。
4. 发生失败时，后续刺激是否停止，收尾是否执行。
5. 正常模型先通过，错误变体再在预期位置失败；一个到处TypeError的程序不能算负向测试成功。

### 3.3 真实固件C/native

新增或修改CONTEXT_RESET、ISR、Manager、协议长度时，执行实际C的编译或现有native harness；Python重写一个同名逻辑不能替代。

最低矩阵：

| 场景 | 必须得到的结果 |
|---|---|
| 未绑定时reset | 正确返回，三类记录按契约复位 |
| 普通IRQ/ECC/DMU各有绑定 | 本实例实际绑定释放，事件清理，代次有效 |
| 三类同时存在 | 不只处理第一个；不误清长期descriptor/实例/manager依赖 |
| 共享物理线另有拥有者 | 不误关另一拥有者 |
| 部分绑定失败仍留Manager记录 | 不能仅凭局部bound标志认定干净 |
| 解绑失败 | 上报失败并保留足够状态；后续资源池不可被PC继续清掉 |
| 连续两次reset | 行为符合幂等/代次约定，没有旧句柄误命中 |
| CRC/长度/instance错误请求 | 不执行错误实例动作；旧命令兼容 |
| 中断到来与上下文清理边界 | 不能让清理后的旧回调重新污染新记录 |

已确认CRG复位CAN寄存器后，上下文命令不应再偷偷执行一套测试基线配置。审查下级Stop函数是否写了Mask/Enable；必要的NVIC解绑/清pending与多余CAN配置要区分。

## 4. 每条Case的行为对照怎么做

### 4.1 首先抓住不可改变的事件

将B和新代码按测试目的分段：初始复位、配置、刺激、首次观察、清除/Ack、重复/恢复、收尾。记录每段的具体命令和Expected。不是仅比较调用总数。

允许归一化的只有预先声明的非功能数据，例如run_id、绝对文件路径、动态时间戳标识。硬件时间戳数值可以按原数学关系比较，而非要求两次绝对相同。

禁止归一化掉：波特率/分频/阈值、Frame ID/flags/DLC/data、请求顺序、错误码、FIFO选择、ISR实例、实际时间窗口长度。不能将请求排序后称序列相同。

轮询读次数可以受实际响应延迟影响，但窗口起点、总预算、等待条件、是否读清、第一次决定性读值不能改变。写刺激次数保持原语义，不允许因为等待增加而自动补发。

### 4.2 三条示例

**ECC重复投递**：

```text
capture → Force → unmask → first_event(count=1)
→ clear目标Raw → Force → unmask → second_event(count=2,same generation)
```

缺第二个unmask必须在行为对照中立刻被发现，而不是等硬件超时才定位。

**IRQ Pending**：

```text
源关闭 → 真实TX/RX → 两个Raw=1且ISR=0
→ pending捕获绑定/开放 → 真实双线ISR → 逐源W1C
```

用会清Raw的Start替换Pending，或删除capture后直接读取line_events，都是失败。

**DMA恢复**：

```text
本节点实际故障 → 第一次真实错误证据 → 停止/原复位
→ 重新配置 → RX DMA先于TX DMA → 实际目标内存及地址/终态比较
```

最后一句不能改成“另一个普通DMA Case以前PASS”。

### 4.3 拆分后的对应关系

每个子Case的前置状态都独立产生。输入/步骤/判据映射为多对多时，说明前缀为什么复制，不能省略。

按原稳定Case家族汇总覆盖，不能直接比较新旧函数数量。多出子Case不自动增加硬件覆盖；删除实例维度也不表示删除其余参数被授权。

示例Ledger：

| 原性质 | 新子目的 | 子Case自己建立的前缀 | 结论 |
|---|---|---|---|
| ECC重复 | repeat_delivery | reset/capture/第一次ISR | 待验证 |
| ECC屏蔽 | masked_delivery | reset/capture/Force但不unmask | 待验证 |
| ECC选择性清除 | selective_clear | 两源Raw、目标投递 | 待验证 |
| 多实例串扰 | 无 | 用户单实例策略 | SCOPE_OUT，不是PASS |

新ID只在SPEC/PLAN/注册表/函数查重后分配。编号表、参数数、报告选择和历史关系在同一逻辑变更同步；不是先生成新函数、最后才补契约。

## 5. 正常/失败/收尾验证矩阵

需要用真实pytest运行Fixture和Case，保存setup/call/teardown三个阶段，不仅手工调用生成器。

| 情况 | 预期 |
|---|---|
| 正常调用与正常收尾 | 正常结束、记录完整、选定资源安静 |
| CRG复位失败 | 无CONTEXT_RESET、无Resource reset、无配置刺激 |
| CONTEXT_RESET失败 | 无Resource reset、无后续配置刺激 |
| Resource reset失败 | 不开始测试配置 |
| 初始化一半失败 | 已登记的对应收尾执行，原失败保留 |
| 断言失败 | 先留决定性数据，再执行收尾 |
| 断言失败且解绑失败 | 两者都保留，不显示成功 |
| 等待超时且DMA活动 | 停止该任务访问者；未知状态阻止后续清池和Case |
| 外部盒子在中途异常 | 对应通道停止/关闭，不持续刺激下一条 |
| STIMER中途异常 | 执行其收尾，不让活动状态遗留 |
| 非can0 Fixture路径 | can_support/DMA/外部Case同样有收尾，而非遗漏 |
| 选择can1 | 构造、Mapping、pins、limits、所有请求全部为同一选择，不偷偷变can0 |

此矩阵是固定基础设施测试，无需把这些保护重复写到每个Case。

## 6. PASS证据和FAIL备注的验证

先跑一个最小ECC样板，确认不在Case手工打标也能从真实返回值生成Canonical Observation。记录适配层不能补发硬件命令或改变返回值。

| 输入情况 | 显示与数据要求 |
|---|---|
| 所有参数PASS | 备注为空；原始Observation/输入/固件信息仍在 |
| 一参数FAIL，其余PASS | 备注只包含失败参数及失败信息，不能把通过参数数据带入 |
| 缺某个FAIL必须数据 | 原因明确，不制造0值或空帧作硬件结果 |
| RUN_ERROR/EVIDENCE_MISSING/SKIP | 状态和原因保留，不冒充芯片FAIL或PASS |
| 同键多次采样 | 保留顺序及首次决定性值，不只保留最后一次 |
| 读清寄存器 | 保存原返回，不为报告再读取一次 |
| 报告生成失败 | 报告错误明确，原始结果不覆写 |

原 `_report_remark`、`_human_report_note` 对PASS/FAIL的行为要逐项测试。不要绕开报告校验器或删除SPEC中的证据需求以使报告“成功”。

## 7. 静态与采集命令

以下命令只执行软件验证或收集，不烧录设备。依赖环境先按仓库现有说明建立，运行后保存完整输出和退出码。命令不存在/参数不支持时查实际工具帮助，不能伪造执行记录。

```powershell
git rev-parse HEAD
git diff --check
uv run --extra test python -m pytest -q pc/et_test_platform/framework_validation/unit/drivers/can/test_can_driver.py
uv run --extra test python -m pytest --collect-only -q pc/et_test_platform/test_cases/can/ -k "test_can_p1_ or test_can_p2_"
python tools/quality/check_case_spec_implementation.py
python tools/quality/check_firmware_architecture_rules.py .
python tools/validate_pc.py
```

还要运行Task Context列出的固件专项、报告专项、Fixture故障测试和本次新增真实调用链测试。上述固定命令本身不保证覆盖全部新增内容。

此前“148个节点”是实施方声明，而且其表含P0/P3；本轮不要硬写148或把31个全CAN稳定ID称27个P1/P2。按实际选择列表生成总数并保存完整nodeid。

只有参数收集不会执行测试主体，参见pytest官方说明：
https://docs.pytest.org/en/stable/how-to/usage.html

## 8. 独立Reviewer逐步操作

### R0：固定审查输入

读取精确新SHA、B、007问题清单、008与本卡。自检报告只作导航，不作正确性证据。先检查diff范围：是否改了无关IP、旧验收文档、检查器、超时、旧错误处理。

### R1：逐个删除项审查

对所有删除的assert、设备调用、等待、参数、record、finally/finalizer逐项追踪去向。

- 找不到新位置：REQUEST_CHANGES。
- 原read变为缓存：REQUEST_CHANGES。
- 只在主流程正常末尾收尾：REQUEST_CHANGES。
- 原精准次数变成非零，没有规格变更：REQUEST_CHANGES。
- 仅“放到Driver”但Driver实际执行整个Case：REQUEST_CHANGES。

### R2：查真实接口，不猜名字

沿每个变化调用打开真实定义与模型。特查007列出的V1/V2、rx键、FIFO/seq、计数字段、slice、Event层级、type期望。检查P0/P3因共享Driver变化仍兼容，但不擅自运行所有IP HIL。

### R3：看波形意义上的先后关系

不是只看有没有调用。重点：INIT/CCE、Filter/RAM、Capture/Mask/Enable、DMA_RX/DMA_TX、刺激/读清、Read/Ack、故障/恢复。对照每卡的具体箭头和反例。

### R4：亲自运行反例

至少复现本批卡片的正向与错误变体；需要的是在指定判据失败，而不是因为Fixture未装/接口不存在而失败。核对模型是否真正包含待验证特性，例如ECC ISR后的自动Mask、FIFO的索引推进、DMU首次读清。

### R5：看简洁是否真实

Case能否只读正文了解被测配置和判据？是否仍混入partial/check/record、闭包、通用上下文、JSON组装？固定配置是否具有名称和独立定义？大段十参数位置值是否只是挤成一行？

Driver是否只做一个下级动作或必要的有界读等待？reset固定组合是否无测试配置？运行侧记录/收尾是否单一、没有变成第二套场景执行器？

### R6：查证据和表述

检查日志确实来自该SHA和命令；收集、模型、真实Python链、C/native、HIL各自区分；没有HIL就不能写“硬件流程100%验证通过”。先记录证据再给勾选，不允许整表预勾。

### R7：给出可复现结论

每条问题必须给出：严重性、文件/函数/行号、输入场景、原行为、新行为、后果、修复、能揭露它的最小测试。没发现新问题也只能写“本次范围未发现”，不是证明所有硬件环境绝对无错。

## 9. HIL回归怎么安排

实际硬件和烧录遵守用户及项目人工门禁。不要直接照抄旧报告可能已经失效的runner参数；先读取当前入口/帮助与台架配置。

顺序：复位原语专项 → ECC → 普通IRQ → DMU收发/Event → 已修改的P1/P2节点。只测所选代表CAN及其必要支撑IP，不自动扩大为所有CAN或所有芯片。

记录设备/芯片/FPGA或Silicon lane、连接文件、固件构建标识/哈希、PC源码SHA、时钟、Peer身份、所有参数与完整结果。修改C后必须确认设备正在跑配套固件，不能只修改PC后称新命令已验证。

验证单跑、必要的串行相邻运行、失败后隔离与重新开始。主机代码硬件不同时序的变化必须解释；不能只比较最后总体PASS数。

## 10. 开发者提交给Reviewer的最小目录

每批只保留一份可复用的工作记录，产物遵循R500既有路径，不扩散日期目录：

```text
本批说明.md              # 卡号、SHA、范围、执行状态
行为对照.md              # 原到新每个关键性质/步骤/判据
拆分映射.md              # 有拆分才需要；参数和独立前缀
验证索引.md              # 命令、退出码、日志/工件路径、反例
长度与边界.md            # 实际行数、Driver边界、例外理由
```

文件名可映射到仓库现有位置，但这五种信息不能遗漏。详细日志在artifacts，不复制进report。不能再提交“210通过+收集148所以所有27条正确”一类结论。

## 11. 给开发Agent的直接指令

> 本次先执行G0/G1和P2_003任务卡，不修改其他Case。读取B的完整流程与当前真实接口，逐项建立旧到新对照。保留显式can.reset方向和单实例策略。先恢复缺失的unmask、Raw对照、真实捕获和窗口，再迁移记录/收尾；所有删除项有接收位置。实际执行真实Python链和固件相关专项，并做卡片错误反例。没有对应测试日志不得标PASS。完成后提交精确SHA、对照表、反例和长度结果，等本轮复核结论再进入后续批次。不要自行改验收标准、扩大范围、编造接口或隐藏整个测试。

这段指令是后续执行入口，不表示本次已授权或已完成真实硬件操作。
