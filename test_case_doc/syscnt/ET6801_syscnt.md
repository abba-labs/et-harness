# ET6801 SYSCNT分析与公共契约适配

更新时间：2026-09-04 08:50 CST。

当前共8条Case：7条正式Case已完成，1条外部脉宽测量PLAN待实现、按人工指令暂不测试。已有bitfile、BootROM与PFLASH部署通过；最近一次HIL为7条Case、23项参数执行全部PASS，Excel报告与流水线均通过。新增PLAN不改变旧运行统计。公共测试方法以[syscnt.md](syscnt.md)为唯一入口。本文件只记录ET6801硬件、SDK、历史证据、映射和未解决项，不定义第二套公共Case。

## 第一章 IP分析与Evidence

### 1.1 工作原理、实例与应用

ET6801 SVD描述一个64-bit系统时间戳计数器，两个APB访问窗口：

| 窗口 | 基址 | 作用 |
|---|---|---|
| `SYSCNT_CTRL` | `0x4040E000` | 使能、暂停配置、计数状态、装载和频率标识 |
| `SYSCNT_RO` | `0x4040D000` | 读取同一计数器的低/高32位；写属性存在资料冲突，见G04 |

实例/Handle：1个逻辑SYSCNT，不是2个；专用IRQ/Handler：SVD中0个，当前SDK未给出SYSCNT中断接口。它不是SysTick，也不是STIMER，不规划IRQ、DMA或周期比较中断。CPU Debug控制属于外部测试动作，不是SYSCNT IRQ。

`CNTCR.EN=1`时计数递增，清0后停止保持。计数可由软件在停止状态装载，再继续运行。典型应用为时间戳、耗时计算和软件超时；修改这个全局时间基准前必须确保框架和其他Core没有活动消费者。

SVD中`SYSC.CLK_SCNT.SEL_IN`选择内部OSC25M路径或XO25M；`SYSC.SCNT.HALT_MODE_EN`控制系统暂停通路；`SYSCNT_CTRL.CNTCR.HDBG`控制本计数器是否响应暂停请求。系统路由、本IP策略和CPU真实停核是三个不同条件。

### 1.2 Source Coverage

查询入口为`project-governance/ip-analysis-sources.yaml`的`roots1/intent_routing/chip_parameters`。本地`SDK`代表`D:/lihuan/vibe_code/code/SDK/git`，`ATP`代表当前ET_ATP_Testing工作树。只定向查询SYSCNT、相关Cortex/SYSCTRL/CRG符号与测试入口，未扫描所有IP正文。

| 资料根/来源 | 状态 | 命中或无匹配说明 |
|---|---|---|
| requirements：`SDK/test_case` | FOUND | `6003/3101/soc_subsystem.json`、`6003/3101/sysc.json`、`3101/bootrom.json`有相关条目；`6801`子目录未提供，记为该根内NO_MATCH，不伪称6801已有需求文件。 |
| ET6801完整SVD：`SDK/6801/et6801-verification/Tools/RegGen/ET6801.svd` | FOUND | 两个SYSCNT窗口及SYSC、CRG相关字段。 |
| ET6801拆分SVD：同根`Tools/RegGen/svd` | FOUND | `sysc.svd`、`crg_cfg.svd`含外围时钟/暂停事实；未找到独立SYSCNT文件，以完整SVD核对。 |
| ET6801 Driver根：同根`DFP/Drivers` | FOUND | SYSCNT的8个API位于`ET6x_Driver/{Inc,Src}/et6x_cortex.*`，不是独立syscnt文件；另读sysctrl/crg。 |
| ET6801 FPGA verification根 | FOUND | `DFP/Test/FPGATest/syscnt_fpga_test.c`、`Log/syscnt/coresight_soc400_technical_reference_manual_100536_0302_01_en.pdf`。 |
| ET6801 Test根：同根`DFP/Test` | FOUND | `UnitTest/test_syscnt.c`；其他IP中的delay/计时调用不是独立SYSCNT覆盖。`UnitTest/common.c`中入口注释，不证明当前执行。 |
| ET6003 SDK Driver/Test根：`SDK/6003/6003_sdk/et6003-sdk/DFP/{Drivers,Test}` | FOUND | `UnitTest/test_syscnt.c`与6801版本字节一致；当前Cortex Driver无SYSCNT API，不能用其测试文件存在证明可运行。 |
| ET6003 verification Driver/Test/FPGA根：`SDK/6003/et6003-verification` | FOUND | UnitTest四个函数、`FPGATest/Cortex-M7/syscnt.c`；SYSCTRL时钟枚举与6801不同，仅参考测试意图。 |
| ET3101 SDK Driver/Test根：`SDK/3101/et3101-sdk/DFP/{Drivers,Test}` | FOUND | UnitTest、`SmokeTest/systick_smoke_test.c`中的SYSCNT函数、`FunctionalTest/soc_test.c::SOC_TestCase14`及Cortex API。 |
| ET3101 verification Driver/Test/FPGA/SVD根：`SDK/3101/et3101-verification` | FOUND | UnitTest、FPGA Cortex-M7/syscnt.c及合并SVD有SYSCNT；不使用3101地址或频率证明6801。 |
| ET6003/ET3101登记SVD根 | FOUND | 两个`Tools/RegGen/svd`中均命中sysc/crg_cfg；完整SVD均含SYSCNT_CTRL/RO。只核对历史来源，不覆盖6801事实。 |
| BootROM Driver：`BOOT_ROM/bootrom-dev-et6801/source/Drivers` | FOUND | `ET6801/ET6x_Driver/Src/et6x_cortex.c`声明25MHz，start又调用旧`CRG_getSYSCNTClock()`；装载自动启动及拆分读取同类。不是当前FPGA实际频率的独立证据，不修改BootROM。 |
| 当前工程SVD/SDK | FOUND | `ATP/test_case_doc/ET6801.svd`两个SYSCNT窗口与最新SVD字段一致；本地cortex源码保留相同API问题。 |
| 当前Capability | FOUND | 正式`profiles/chip_capabilities/et6801/ip/syscnt.yaml`由SVD生成，唯一实例syscnt0；原CTRL/RO分组不作为Formal Case入口。 |
| 当前Formal/Service/Wrap | FOUND | 已实现SYSCNT九条命令、独立Wrap/Service与PC七条Case；硬件结果见第七章。 |
| ET6801 SVN需求文件定向检索 | NO_MATCH | `SVN/Software/ET6801`内未找到SYSCNT命名的测试表；不采用其他芯片手册替代6801硬件事实。 |

同根的StressTest、ChipSieveTest、Coremark、PerformceTest中相关命中主要是延时、随机种子或耗时工具使用，不含新增SYSCNT正确性Oracle。ChipSieve配置注释提及双核SYSCNT，不等于存在已执行双核计数正确性Case。

ET Chip Insight工具缺少本地`.et-ai/paths.yaml`，本轮按Source Map解析明确路径后直接核对；PDF工具箱出现GBK输出错误，使用同一工具环境的PDF解析库读取相关页。没有修改资料源或工具配置。

### 1.3 关键Evidence与Claim

| 编号 | 来源/符号 | 状态 | 可证明事实 |
|---|---|---|---|
| E01 | 最新与工程SVD：`SYSCNT_CTRL/RO` | VERIFIED | 两个窗口、7个寄存器定义、32+32-bit计数、EN/HDBG/DBGH、频率标识，未列专用IRQ。 |
| E02 | `et6x_cortex.c::SYSCNT_*` | VERIFIED | 装载顺序低→高，但自动重新使能；start清零；getCurrentVal在一个表达式中各读一次高/低字，无一致性重读，C表达式也不保证两次读取顺序；暂停API同时写SYSC和SYSCNT。 |
| E03 | SVD：`SYSC.CLK_SCNT/SCNT` | VERIFIED | 6801两种时钟源选择值0/1、系统Halt通路使能bit0。 |
| E04 | SVD：`CRG.GTEN0/SRST0`及`et6x_crg.h/c` | VERIFIED | SYSCNT时钟门控为GTEN0 bit16；未列独立SYSCNT SRST位。旧枚举0x15配合通用函数会操作bit21，不是SYSCNT。 |
| E05 | `DFP/Test/UnitTest/test_syscnt.c` | VERIFIED | 存在4个历史函数，含延时观测与人工Halt意图；不代表4项已有有效PASS。 |
| E06 | `DFP/Test/FPGATest/syscnt_fpga_test.c::SYSCNT_1` | VERIFIED | 使用自身延时后自身读数，且两个断言都是上界，不能形成精度闭环。 |
| E07 | CoreSight SoC-400 TRM §3.10，PDF页244～248 | VERIFIED（通用说明） | CTRL装载需EN=0，先低后高；高字写入提交；FREQ应登记实际Tick频率，不是分频器。与6801字段结构和SDK写序一致，但不能据其管理寄存器表给6801增加寄存器。 |
| E08 | 同TRM只读窗口与6801 SVD | CONFLICT | TRM只读窗口为RO，而6801 SVD/CMSIS标为RW；本轮只使用读取，写保护测试保留G04。 |
| E09 | SDK静态`SYSCNT_clk`与`SYSCTRL_getSYSCNTClock()` | CONFLICT（软件频率来源） | 前者固定12.5MHz，后者固定25MHz；不能判定当前FPGA实际值，见G02。 |
| E10 | 当前PC STIMER停核Case与debug_controller | VERIFIED（软件路径） | 已有停核期间采样入口可复用；不是SYSCNT硬件Halt的通过证据。 |

输入身份：

| 输入 | SHA256 |
|---|---|
| SDK最新完整ET6801.svd | `49b2de29bd7a0a4a5fbdefc6e36d75cd6da53a46f5504f860dee53be9079cce4` |
| 工程ET6801.svd | `822f5b2e4d5e9910228f745aae307b479b611e94288c111830adddc70c387709` |
| SDK et6x_cortex.c | `98d05ae5a521c7f412e63df05c89fe3556f3d6c9da8851e595f029ed77bee3e5` |
| 6801 UnitTest/test_syscnt.c | `67063ca08befa3e99d24400f74fd5b565c295b0a71186df70238a08b51612873` |
| 6801 FPGATest/syscnt_fpga_test.c | `6d786a07c000a6f04751ea8ad4cc507cef1d0903da2e23ce4be6343b38c5b72f` |

## 第二章 Driver分析与实施缺口

### 2.1 当前API逐项分析

| API/对象 | 实际行为 | 自动化适配判断 |
|---|---|---|
| `SYSCNT_start()` | 将固定12.5MHz写CNTFID0，装载0并置EN | 不能直接实现公共ENABLE_SET；重新使能不应清零或改频率。 |
| `SYSCNT_stop()` | 清CNTCR.EN | 可复用停止动作；需读回确认停止与计数稳定。 |
| `SYSCNT_setValue(u64)` | 清EN、写CNTCVL、写CNTCVU、置EN | 不符合“装载后保持停止”；需补测试扩展，而不是Wrap直接操作寄存器。 |
| `SYSCNT_getCurrentVal()` | 一个按位OR表达式中各读取一次高/低字，再拼成64位；求值次序未固定 | 低字在两读间回绕可能拼错；需显式高→低→高有界重读。不能增加无界循环。 |
| `SYSCNT_enableDebugHalt()` | 置SYSC.SCNT.bit0及CNTCR.bit1 | 不能把系统路由隐式当成本IP配置；后续拆成PC显式系统配置、本IP策略两个动作。 |
| `SYSCNT_disableDebugHalt()` | 清上述两个位 | 同上；不能在Wrap调用时悄悄改其他模块状态。 |
| `SYSCNT_getDebugHaltStatus()` | 读CNTSR.DBGH | 可复用；它是实际暂停状态，不是HDBG配置读回。 |
| `SYSCNT_delay(ms)` | 重新装载0并使能，用固定频率换算，自身读数无限等待 | 不用于Formal等待或独立Oracle；否则可能永远阻塞且破坏全局时间。 |
| `SYSCTRL_selectSYSCNTClockSource()` | 写SYSC.CLK_SCNT.bit0 | 属于SYSCTRL；由PC调对应Driver，不从SYSCNT Service组合。 |
| `SYSCTRL_getSYSCNTClock()` | 固定返回25000000 | 不是当前FPGA实测，也不是独立测频，不能与12.5MHz混用。 |
| `CRG_PERIPH_SYSCNT=0x15` | 当前通用CRG函数以枚举/32和枚举%32选择寄存器/bit | 0x15=21，SVD的GTEN0/SRST0 bit21是CORDIC1；不能调用该枚举操作SYSCNT。 |

当前平台SYSCNT没有注册CRG映射，以上是**接入时会触发的已定位风险**，不是本轮硬件已发生误复位。不能因SDK存在枚举就推断复位有效。

### 2.2 后续最小补充面（本轮不实现）

- 在现有Cortex Chip Driver文件底部测试扩展区补充SYSCNT专属Enable、Stopped Load、View Read、Control Read、Halt Policy、Frequency ID接口，命名遵循`SYSCNT_test...`，头文件同步隔离；不新增Adapter层。
- 已有stop/状态读取等正确接口优先复用；错误副作用不在Wrap中用直接寄存器访问补偿。
- 短参考采样返回DWT前值→SYSCNT连贯值→DWT后值。DWT只是独立目标本地测量源，不做Case等待、循环计时、Expected计算或PASS判断。DWT位宽32，每个参数必须满足公共契约的完整回绕周期上界；不能为适配10秒参数改用错误的32-bit直接相减或删掉参数。
- Wrap只调用所属SYSCNT Chip Driver接口；Service只执行本IP原子命令；时钟源/系统Halt通路的控制由PC调用相应所有者。任何新增SYSCTRL/CRG公共接口需单独确认范围，不能夹在SYSCNT开发中修改公共层或其他IP。
- 两个SVD能力文件需要映射成一个逻辑SYSCNT，公开位宽、窗口、频率标识及暂停选项；不把测试通过与否写进硬件Capability。
- 没有自主异步计算任务，不需要新IRQ回调、Job调度或测试状态机。

### 2.3 固件开发前置整改清单

**执行顺序：先按本表修正已确认Driver问题、补测试扩展并验证，再实现SYSCNT Wrap/Service；禁止在Wrap/Service补寄存器操作来绕开。** 当前各项均未修改、未硬件验证。表内“行为不匹配”不等于原SDK违反硬件规格；应保留已有API的合法语义，用隔离测试扩展提供所需原子动作。

文件定位：Cortex/CRG/SYSCTRL均为工程内`firmware/chips/et6801/sdk/ET6x_Driver/{Src,Inc}/et6x_*.{c,h}`；硬件依据使用1.3节E01～E09，不修改外部参考仓库。

| 项目 | 分类与具体证据 | 后续先处理什么 | 验收依据 / 影响Case |
|---|---|---|---|
| D01 时钟门控编号 | 已确认Driver映射错误：`CRG_PERIPH_SYSCNT=0x15`，通用函数操作GTEN0 bit21；SVD的SYSCNT在bit16，bit21为CORDIC1 | 在CRG所有者内补正确的SYSCNT时钟操作；引用`CRG_GTEN0_CRG_CLK_GTEN_SYSCNT_Msk`，不直接把共享枚举改成0x10（旧枚举WDG0已用0x10）。CRG改动需独立授权范围 | 静态/寄存器桩验证仅目标时钟位变化，CORDIC1和其他位不变；所有Case前置 |
| D02 复位映射 | 未确认硬件能力，不是可凭猜测修复的编号：SVD无SYSCNT独立SRST位；旧0x15会复位CORDIC1 | 禁止继续用该枚举复位SYSCNT；时钟映射与复位资格分开。先闭合G01，绝不能以GTEN0 bit16推导SRST0 bit16 | 无未知或其他IP复位写入；批准基线后检查可控状态读回；所有Case前置 |
| D03 连贯64-bit读取 | 已确认源码一致性风险：`SYSCNT_getCurrentVal()`无跨字进位保护 | Chip Driver中显式高→低→高，变化时有界重读；可失败接口放在Test Driver Extension，禁止超限后返回拼接伪值 | 定向桩覆盖正常、两读间进位、最大值回绕、持续不一致；P1_001另验证实际跨界，不声称串口采样必然撞上两次总线读取之间 |
| D04 装载和启动 | 旧API行为与新原子语义不匹配：setValue自动置EN；start初始化、清零并写频率 | 补停止装载和不清零Enable/Resume测试接口；不把已有start静默改成resume | 停止装载读回准确且EN=0；Resume保留计数和频率标识；P0_001/P0_002/P3_001 |
| D05 频率来源 | 软件事实冲突：Cortex固定12.5MHz，SYSCTRL固定25MHz；BootROM源码也不能证明本镜像的实际时钟 | 闭合G02后使用已确认的目标/Lane时钟事实；频率登记与时钟选择分开，不根据SYSCNT自身测量校准自身 | 各源事实可追溯，计时按实际频率换算；P1_001/P1_002/P2_001 |
| D06 Halt配置及注释 | 旧API同时写SYSC.SCNT和CNTCR；getDebugHaltStatus注释把实际DBGH状态说成模式设置 | 修正状态注释；本IP测试接口只改CNTCR.HDBG，系统路由由SYSCTRL接口、PC编排；补HDBG配置读回 | HDBG配置与DBGH状态分开记录；真正停核后检查DBGH/计数；P2_002 |
| D07 正式API缺口 | 无双窗口选择读、控制快照、独立频率标识设置和短参考采样 | 优先复用正确stop/状态接口，其余按R310在源/头文件末尾Test Driver Extension补齐，名称带test且语义明确 | 原子动作、参数边界、错误返回、原始观测齐全；对应PLAN可直接调用，不在固件实现测试流程 |
| S01 RO窗口属性 | 资料CONFLICT：6801 SVD/CMSIS为RW，通用TRM为RO，尚无6801设计确认 | 在G04保留冲突；获得目标设计确认后再修SVD及生成头文件。确认前仅使用读接口，禁止擅写RO窗口 | 目标芯片证据闭合后核对SVD→CMSIS→Driver；不影响当前只读Case的编写 |

D03属于真正的读取风险；D04/D07属于接口适配，不应通过大改正式SDK语义解决。D01/D02涉及CRG，D05/D06可能涉及SYSCTRL，未来必须使用对应任务路由并获得用户要求的跨IP修改批准。本轮仅记录，不扩大当前文档任务。

### 2.4 Capability语义实施

2026-09-04：统一生成器的语义版本提升为11，事实分组版本提升为2。对于同时存在`<name>_CTRL`与`<name>_RO`的命名窗口，控制窗口归属逻辑`<name>`，读取窗口的原始Peripheral/字段仍完整保留；若已有同名裸外设则拒绝歧义。不按芯片或IP名分支。

正式`syscnt.yaml`由当前SVD生成，唯一实例`syscnt0`指向`SYSCNT_CTRL`。能力包含counter、debug_halt、frequency_id及64-bit计数/32-bit字宽；高低字位宽必须同时由“timestamp counter lower/upper”字段描述证明。读取窗口、外部时钟和调试观测端点由本芯片Execution Mapping解析，不把读取窗口作为第二个可配置计数器。历史`syscnt_ctrl.yaml`没有被用作新增Case的能力入口，不在本次修改其他IP基线文件。

原始生成与审计位于`artifacts/runs/20260904_syscnt_capability/`，CLI质量检查通过；新增5项专项测试验证真实字段、重命名/换地址、字段缺失和命名歧义，全部通过。能力生成不证明硬件PASS，也不确认实际时钟频率。

### 2.5 PC实施与待测事实

2026-09-04：PC Driver只封装九条原子请求，严格验证实例前缀、长度、保留位和枚举；没有新增公共层逻辑。Case注册为7个逻辑ID，按P0～P3分文件；参数包括六种装载位型、两类回绕边界、每个可用时钟源的五个时间窗口、两种停核策略。P3为20轮短重复，不是20个逻辑Case。

`syscnt_routes.py`记录CTRL/RO与DHCSR的观测地址；停核采样顺序为高→低→高→CNTSR→CNTCR，由既有Debugger在DHCSR.S_HALT包围下读取两组。DWT参考频率来自当前FPGA构建的`SystemCoreClock=25MHz`。2026-09-04 06:13部署后，以DWT独立参考分别在两个源下采样0.1/0.5/1s，计数比均符合1/2：五组精确为0.5，首次短窗口为0.4999885（采样开销）。因此当前FPGA映射两源均为12.5MHz，不将CNTFID0当实际时钟；不宣称两个物理振荡器不同，也不证明绝对晶振精度。原始计数见`artifacts/runs/20260904_syscnt_clock_probe/clock_probe.json`。

16项PC软件合同测试已通过（guard `20260904_055613_fc45c484`），覆盖九条Wire命令、参数边界、非法响应、参考计数回绕和停核读数撕裂；这些不是硬件结果。七条SPEC/REPORT、注册、注释和编排专项检查通过。首轮HIL已通过；G02/G05/G06在当前FPGA/Core0范围闭合，G07外部脉冲观测仍未覆盖。

## 第三章 寄存器与配置事实

### 3.1 本IP寄存器

| 寄存器 | 偏移 | 字段 | SVD访问/复位值 | 测试用途 |
|---|---|---|---|---|
| SYSCNT_CTRL.CNTCR | 0x00 | EN bit0；HDBG bit1 | RW / 0 | 启停配置、暂停策略；保留位不写。 |
| SYSCNT_CTRL.CNTSR | 0x04 | DBGH bit1 | RO / 0 | 真实计数暂停状态。 |
| SYSCNT_CTRL.CNTCVL | 0x08 | 低32位 | RW / 0 | 停止装载/CONTROL计数读取。 |
| SYSCNT_CTRL.CNTCVU | 0x0C | 高32位 | RW / 0 | 与低字组成64位；按低→高顺序装载。 |
| SYSCNT_CTRL.CNTFID0 | 0x20 | FREQ[31:0] | RW / 0 | 频率信息登记，描述上限4GHz。 |
| SYSCNT_RO.CNTCVL | 0x00 | 低32位 | SVD标RW / 0 | 只使用读操作，RO/RW争议不在本轮擅自定案。 |
| SYSCNT_RO.CNTCVU | 0x04 | 高32位 | SVD标RW / 0 | 同上。 |

复位值只用于描述SVD上电定义；普通Case的软件归一结果不能冒充已验证硬复位值。

### 3.2 外围依赖与风险

| 所有者/字段 | 6801事实 | 开发约束 |
|---|---|---|
| `SYSC.CLK_SCNT.SEL_IN` bit0 | 0=内部选择后的OSC25M；1=XO25M | 两路选择编码有依据；FPGA各路实际频率仍需绑定当前镜像事实。 |
| `SYSC.SCNT.HALT_MODE_EN` bit0 | 1启用系统SYSCNT Halt模式 | 与CNTCR.HDBG同时配置；系统路由操作归SYSCTRL。 |
| `CRG.GTEN0.CRG_CLK_GTEN_SYSCNT` bit16 | 1开时钟，0关时钟 | 不用旧枚举0x15；本轮不构造关总线时钟后的APB读取。 |
| `CRG.SRST0` | 没有SYSCNT命名复位位，bit15/16未列字段；bit21为CORDIC1 | 禁止把时钟门控位当复位位，禁止重置整个CoreSight尝试“顺便复位”。 |
| CPU Debug / DWT | 已有CoreDebug和DWT SDK定义及平台调试器路径 | 实际CPU停核、参考计数使能分别确认；SYSCNT Feature失败不得套用STIMER结论。 |

### 3.3 公共观测映射

| 公共稳定语义 | ET6801实际端点 | 读取/展示约束 |
|---|---|---|
| CONTROL.ENABLE | SYSCNT_CTRL.CNTCR.EN[0] | bool；读回配置。 |
| CONTROL.HALT_ON_DEBUG | SYSCNT_CTRL.CNTCR.HDBG[1] | bool；另记录系统Halt路由。 |
| STATUS.DEBUG_HALTED | SYSCNT_CTRL.CNTSR.DBGH[1] | bool；CPU停核期间由调试器读取。 |
| COUNT.CONTROL | SYSCNT_CTRL.CNTCVU/CNTCVL | 连贯64-bit逻辑计数；停止时两窗口比较需等待同步稳定。 |
| COUNT.READ | SYSCNT_RO.CNTCVU/CNTCVL | 连贯64-bit逻辑计数；可用高→低→高避免撕裂。 |
| FREQUENCY.ID | SYSCNT_CTRL.CNTFID0.FREQ | hex32或带Hz；不称作测得频率。 |
| CLOCK.SOURCE | SYSC.CLK_SCNT.SEL_IN[0] | 系统时钟选择事实，不能挂在CNTFID0名下。 |
| REFERENCE.COUNT | DWT.CYCCNT | 原始32-bit计数，用64-bit公共容器承载；delta与误差为Measurement。 |
| CPU.DEBUG_HALTED | CoreDebug.DHCSR.S_HALT[17] | observer事实，记录Probe/CPU身份；不能由软件写C_HALT推断S_HALT。 |
| CPU.DEBUG_STATUS | CoreDebug.DHCSR完整32-bit值 | 每个策略四次原始读数；两组计数前后均必须S_HALT=1。 |

## 第四章 历史测试与Source Item Trace

### 4.1 历史代码是否真正覆盖

| 来源 | 真实刺激/观测 | 当前裁决 |
|---|---|---|
| 6801 UnitTest Case2 | DWT观察DELAY_US(100/1000/10000)，只打印差值 | 不是SYSCNT正确性断言；作为独立参考计时思路，不计硬件已覆盖。 |
| 6801 UnitTest Case3 | 开关Halt、读DBGH、连续读计数并断言差值<100，提示Keil人工观察 | 意图保留；缺CPU停核事实，连续快读也可能PASS，改为停核期间两次采样。 |
| 6801 UnitTest Case4/5 | SYSCNT延时10/100ms，DWT换算；Case5附带GPIO翻转 | 参考计时意图保留；`ret2/12`固定300MHz/25MHz、起点未一致换算，不能复制。 |
| 6801/3101 FPGA SYSCNT_1 | SYSCNT_delay(1000)后再读SYSCNT | 自证时长；两个上界断言连0都可能满足。用独立参考和上下界取代。 |
| 6003 UnitTest Case2～5 | 与前述同类；部分版本DELAY_US却按ms计算 | 保留功能意图，纠正单位和参考频率。不能把6003频率/时钟枚举搬到6801。 |
| 6003 FPGA SYSCNT_1 | DELAY_US(1000)后读计数，仍使用约2500万上界 | 单位与约束不闭合；同样归入独立计时Case，不沿用断言。 |
| 3101 verification UnitTest Case5 | 实际delay与ret2采样被注释，ret2保持0 | 源码存在但无有效当前测试；正确计时意图由P2_001覆盖。 |
| 3101 SDK Smoke SYSCNT_TestCase0～3 | 多窗口DWT打印、人工Halt、10/100ms计时与GPIO翻转 | 合并同类计时/暂停语义；不照搬打印代替断言。`#if 0`波形函数仅作历史设计。 |
| 3101 SDK SOC_TestCase14 | 当前函数以GPIO脉宽观察1秒延时；精确DWT断言与入口被注释 | 只证明有测试思路，不证明PASS。GPIO是计时观测手段，不是SYSCNT引脚Feature。 |
| 其他IP中的SYSCNT_delay/计时 | 作为等待、种子或性能基准 | 不是独立SYSCNT测试，不能增加Case计数。 |

历史源码还使用`SYSCNT_delay_ms()`和`CRG_getSYSCNTClock()`；当前工程SDK及最新6801 Driver根中未找到对应声明/实现，只有旧注释。它们是历史源码兼容性问题，不能因为测试文件存在就认为可以原样编译运行；新Case按公共动作实现，不为照搬旧源码重复增加同义API。

### 4.2 需求和有效测试语义逐项映射

6003/3101两份soc_subsystem中的同名条目分别检索，以下合并列示不代表漏掉其中一份；3101/6003 sysc也使用同样处理。

| Source Item | 公共Feature / Case / Gap | Disposition | 说明 |
|---|---|---|---|
| soc_subsystem / BUS_TP_003 的syscnt APB访问子项 | F001/F004 → P0_001 | MERGED | 停止装载与双窗口精确读回覆盖相关数据访问，不声称覆盖整个APB总线。 |
| soc_subsystem / SYSCNT 精度标题 | F007 → P2_001 | MERGED | 标题归入具体计时条目。 |
| SYSCNT_TP_001 计数设定 | F001 → P0_001 | MAPPED | 包含高低位与全位型。 |
| SYSCNT_TP_002 启动 | F002 → P0_002 | MAPPED | 必须观察实际递增。 |
| SYSCNT_TP_003 关闭 | F002 → P0_002 | MERGED | 停止后间隔读数不变。 |
| SYSCNT_TP_004 Debug Halt | F006 → P2_002 | MAPPED | 真实CPU停核＋DBGH＋冻结计数。 |
| SYSCNT_TP_005 取消Debug Halt | F006 → P2_002 | MERGED | RUN_FREE同流程对照。 |
| SYSCNT_TP_006 最大值重计数 | F003 → P1_001 | MAPPED | 不等自然溢出，装载到边界前，实际跨界。 |
| SYSCNT_TP_007 计时精度 | F007 → P2_001 | MAPPED | 独立参考、时间区间与1ms历史验收预算；不是晶振绝对精度。 |
| SYSCNT_TP_008 时钟源 | F008 → P2_001 / G02 | MAPPED | 参数化所有已确认可用源，当前FPGA频率需独立来源。 |
| 6003 SOC_TC_024；3101 Case26 | F007/F008 → P2_001 | MERGED | 内部时钟源、1秒窗口、与校准DWT对比。 |
| 6003 SOC_TC_025；3101 Case27 | F007/F008 → P2_001 | MERGED | XO时钟源，同一计时方法参数化。 |
| 6003/3101 sysc CRG_TP_013及RESET标题 | F008 → P2_001；独立复位G01 | MERGED | 此处RESET是分类标题，不是SYSCNT硬复位寄存器证据。 |
| 3101 bootrom Case6脉冲计时 | F007/F008 → P2_003 PLAN；G07跟踪实现与台架 | MAPPED | 2026-09-04补充外部脉宽测量设计，保留独立示波器Oracle；只是规划映射，尚无实现或外部实测证据。 |
| 6801/6003/3101 UnitTest与Smoke暂停函数 | F006 → P2_002 | SUPERSEDED | 用停核状态和停核期间读数替代“连续两读差值小”。 |
| UnitTest/Smoke/SOC计时函数 | F007/F008 → P2_001 | MERGED | 按时钟源×时间窗口收敛，不按历史文件数量复制Case。 |
| 3101 Smoke `#if 0`脉冲段的10/50/100ms；活动SYSCNT_TestCase0的10000ms | F007/F008 → P2_001、P2_003 PLAN | SPLIT | P2_001保留片内计时；P2_003保留三个外部脉宽参数，分别形成单脉冲。旧代码打印或被屏蔽段不作为历史PASS证明。 |
| FPGA SYSCNT_1两个上界判据 | F007 → P2_001 | SUPERSEDED | 保留计数推进目的，改为独立参考有界比较。 |
| 单纯DELAY_US/DWT打印与其他IP计时调用 | 不发布独立Feature | NOT_APPLICABLE | 工具使用不等于SYSCNT功能已验证。 |
| SVD两窗口与frequency字段 | F004/F005 → P0_001/P1_001/P1_002 | MAPPED | 补齐历史未完整覆盖的硬件行为。 |
| 20轮独立启停 | F001/F002/F004 → P3_001 | MAPPED | 新增轻量重复验证，非长期可靠性承诺。 |
| 通用TRM ID寄存器、RO写保护 | G04 / 非公共Feature | UNKNOWN | 未在6801目标证据中闭合，不照抄通用IP可选寄存器。 |

8条核心SYSCNT测试点均有计划，不以历史测试自身错误删除Feature。外部脉冲计时尚未完整覆盖，不能把“记录了Gap”写成“Case全集已覆盖”；本轮没有把任何失败重新分类为SKIP。

### 4.3 分析阶段覆盖复核记录

复核时间：`2026-09-03 20:45 CST`。重新读取requirements JSON条目、6801 UnitTest/FPGATest、3101 Smoke的实际刺激，并核对6801 SVD与当前工程Driver。

| 核查集合 | 结果 | 边界 |
|---|---|---|
| requirements命中条目 | 29条：6003 14条、3101 15条；28条已有映射，1条外部脉冲测时为UNKNOWN/G07 | 含重复条目、分类标题和APB子项，不是29条逻辑Case |
| 两份SYSCNT_TP_001～008 | 8/8种核心语义有PLAN | 两份相同语义合并，不按芯片复制Case |
| 当前6801 SVD已准入Feature | 8/8有PLAN；7个本IP寄存器均有字段/观测映射 | SVD未声明的ID寄存器和存在争议的写权限不编造测试结论 |
| 历史计时参数 | 10/50/100/1000/10000ms均由P2_001参数化 | 纯DELAY_US/DWT测试不是SYSCNT功能；不继承旧固定频率和错误断言 |
| 外部脉冲独立观测 | 未闭合，G07 | 当前7条不能宣称完整替代外部精度观测；不是运行SKIP |
| 真实实现/实测 | 注册0、执行0 | 本轮是设计覆盖复核，不是代码覆盖或硬件PASS |

规则复核修正：Debug Halt使用外部调试仪器，资源等级由R2改为R4；公共契约补充Case依赖的`counter_word_bits`，去掉公共方法中的SDK函数名；参考计数展开改为有明确总时间上界的模数计算，以覆盖10s窗口。状态/报告/Feature文本继续使用R100/R120/R130现有契约，没有新建规则或Checker。

分析阶段结论：**核心数字测试点设计覆盖完整；参考资料全集尚有G07，当时整体Implementation Ready未通过。** Schema通过不替代R140人工语义审核；G01/G02/G05/G06仍按第六章解除后才编码其依赖的Formal Case。

专项验证：公共IP契约、Case PLAN、Case人审行格式与Feature一致性、芯片映射文档四项Checker通过；8个Feature均被7个PLAN引用，每个PLAN为6～7步。参考计数公式用25MHz/300MHz、五个时间窗及跨32-bit回绕的模拟输入核验通过，只验证设计计算，不作为硬件Evidence。未运行固件编译、HIL或全量软件回归；本轮没有修改运行代码、公共规则或Checker。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| SYSCNT_F_001 | SUPPORTED | CTRL窗口32+32位，停止后低→高装载；旧API有自动启动副作用 | ADAPTED | SYSCNT_P0_001、SYSCNT_P3_001 |
| SYSCNT_F_002 | SUPPORTED | CNTCR.EN bit0；旧start清零不能用于resume | ADAPTED | SYSCNT_P0_002、SYSCNT_P3_001 |
| SYSCNT_F_003 | SUPPORTED | 已实测低32-bit进位和64-bit自然回绕 | ADAPTED | SYSCNT_P1_001 |
| SYSCNT_F_004 | SUPPORTED | 两个窗口指向同一计数，运行读数需连贯性保护 | ADAPTED | SYSCNT_P0_001、SYSCNT_P1_001、SYSCNT_P3_001 |
| SYSCNT_F_005 | SUPPORTED | CNTFID0.FREQ是信息登记，不改变输入频率 | ADAPTED | SYSCNT_P1_002 |
| SYSCNT_F_006 | SUPPORTED | Core0实际Halt期间两种策略均通过；不外推双核同时活动场景 | ADAPTED | SYSCNT_P2_002 |
| SYSCNT_F_007 | SUPPORTED | 片内DWT双端夹取通过；外部示波器测量链尚未实现 | PARTIAL_ADAPTATION | SYSCNT_P2_001、SYSCNT_P2_003 |
| SYSCNT_F_008 | SUPPORTED | SEL_IN两个编码读回正确，当前FPGA两路计数均为DWT/2；外部时间基准仍需验证 | PARTIAL_ADAPTATION | SYSCNT_P2_001、SYSCNT_P2_003 |

SUPPORTED表示6801适用资料声明，不表示FPGA已PASS。32+32位SVD声明不得因读数异常被静默改成较小位宽以规避FAIL。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| SYSCNT_P0_001 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P0_002 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P1_001 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P1_002 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P2_001 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P2_002 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |
| SYSCNT_P2_003 | IMPLEMENTATION_GAP | PLAN已定义；目标端本地脉冲执行接口归属与代码待完成，GPIO到示波器的物理映射未确认。按人工指令本轮暂不测试；不能把软件缺口记成硬件不支持。 |
| SYSCNT_P3_001 | ADAPTED | 正式链路已实现，首轮HIL通过；当前FPGA时钟和Core0暂停证据见第七章。 |

### 6.1 实施前必须裁决的Gap

| Gap | 分类 | 具体问题 | 解除条件/最小处理 |
|---|---|---|---|
| G01 | CLOSED / 当前FPGA验证 | 没有独立SYSCNT复位位，旧CRG枚举还会选中CORDIC1；不能套用未知复位编号 | 2026-09-03用户批准停止→策略归一→装载0→读回的替代基线，同时执行资源整池复位。只声明软件可控状态归一，不声明全部内部状态硬复位；每个参数实例均执行。 |
| G02 | CLOSED / 当前FPGA映射 | SDK常量冲突保留为历史问题；独立DWT采样确认当前两源均为12.5MHz | 当前bitfile时钟说明或经批准的独立参考测量确定每路实际频率，再进入Lane Profile。不能用待测SYSCNT结果校准SYSCNT自身。 |
| G03 | CLOSED / 已实现验证 | start/load副作用、非连贯读、没有控制快照；SYSCNT公共链路未实现 | 先完成2.3节相应Driver整改及定向验证，再实现Wrap/Service/PC包；D01/D05/D06需要其他所有者改动时单独授权，不在Wrap补寄存器操作。 |
| G04 | CONFLICT / 非阻断读取 | RO窗口SVD标RW而通用TRM规定RO；目标SVD未列管理ID寄存器 | 设计人员或目标RTL/SVD修订确认访问属性；当前Case只读该窗口，不测试写保护或未列寄存器。 |
| G05 | CLOSED / 当前Core0配置 | 当前Core0暂停可使DBGH置位并冻结计数；其他核并行参与条件不在本次结论内 | 补目标Execution Mapping，明确需要停哪个Core及系统路由；先确认DHCSR.S_HALT，再观察DBGH和计数。不假定STIMER失败则SYSCNT也失败。 |
| G06 | CLOSED / 原子采样已验证 | 缺短三元组参考采样，跨串口命令时间不可当亚毫秒同步快照 | 复用或评审SYSCNT测试扩展中的短本地参考采样，参考启停所有权明确；只返回原始计数，不搬运Case判断进固件。 |
| G07 | PLANNED / 实现与台架未闭合 | 已由SYSCNT_P2_003承接外部脉宽目的，定义10/50/100ms、独立示波器Oracle和1ms测试预算；暂无该Case代码或外部结果 | 完成本地脉冲执行接口归属评审与实现，确认安全GPIO输出、示波器通道、共地和测量误差依据后再执行。本轮人工指定暂不测试；不能用旧7条PASS关闭本项。 |

2026-09-03 21:36 CST实施授权：用户明确允许CRG/SYSCTRL的SYSCNT最小前置修改及G01替代基线。CRG/SYSCTRL改动分别使用独立Task Context和Commit；不扩大到其他IP功能、公共协议或规则修改。G01设计决策已闭合，尚待实现验证；G02/G05/G06仍需按各自证据条件闭合，不把未知硬件事实写成PASS。

### 6.2 Driver实施记录

2026-09-04：在现有`et6x_cortex.c/h`底部增加受`ET_ENABLE_TEST_DRIVER_EXTENSIONS`保护的SYSCNT原子接口，保留旧SDK调用行为。

| 测试扩展 | 行为与边界 |
|---|---|
| `SYSCNT_testSetEnabled` | 只修改CNTCR.EN，保留计数、频率标识和其他位。 |
| `SYSCNT_testLoadStopped` | EN=0才按低→高写入，完成后仍停止；运行时返回BUSY。 |
| `SYSCNT_testReadCount` | 两窗口都按高→低→高读取；最多4次，不一致返回BUSY且不改输出。 |
| `SYSCNT_testGetControl` | 分别读取EN、HDBG、DBGH和CNTFID0；不把暂停配置当暂停状态。 |
| `SYSCNT_testSetHaltPolicy` | 只改CNTCR.HDBG；SYSCTRL暂停路由由PC调用所属Driver。 |
| `SYSCNT_testSetFrequencyId` | 停止时写非零CNTFID0，不修改实际时钟。 |
| `SYSCNT_testSetReferenceEnabled` | 显式借用Cortex DWT，保存TRCENA/CYCCNTENA，释放仅恢复这些位；不清零CYCCNT。 |
| `SYSCNT_testSampleReference` | DWT→SYSCNT→DWT短采样，只返回原始值；未借用或使能丢失返回BUSY。 |

G06实现决策：SYSCNT测试扩展仍位于原Cortex Driver，DWT作为同一Cortex所有者的独立参考。PC承担等待、32位回绕上界验证和结果判定。参考频率仍需要G02独立证据；本决策不宣称FPGA精度通过。当前平台Application/Framework/Service未发现SYSCNT/DWT延时消费者，实际HIL前仍核对参与Core。

新增寄存器桩`test_syscnt_driver_native.py`执行真实测试扩展，覆盖写序、保留位、非法参数、双窗口正常/暂态进位/持续撕裂、DWT使能位借还及不清零约束。2026-09-04 04:57 CST，WSL GCC编译并执行通过（1个软件测试节点，guard `20260904_045723_613f31d4`）；软件桩不代替硬件结论。

2026-09-04 05:02 CST：本批次统一软件门禁通过（928 PASS、13条件软件SKIP，guard `20260904_045955_bf83dba1`）。其中新增Native测试在Windows因无C编译器SKIP，已由上面的WSL执行单独补证；仍未执行SYSCNT Keil/HIL。

### 6.3 Wrap/Service实施记录

2026-09-04：新增一对公共SYSCNT Wrap和Service文件，九条命令只执行本IP原子动作。Chip Config将唯一逻辑实例0映射为64位计数、两读取窗口、32位参考；不内置12.5/25MHz猜测值。Service ID为0x010A，消息实例与请求首字节强制一致，长度和响应容量在硬件调用前验证。

SDK归属门禁按现有职责表增加SYSCNT→Cortex映射：实际SYSCNT实现就在`et6x_cortex`内，不新增SDK转接层；CRG/SYSCTRL/UART/DMA Driver依赖仍被ETFW201拒绝。该独立门禁批次于2026-09-04 05:11 CST通过统一软件验证（929 PASS、13条件软件SKIP，guard `20260904_050945_de791109`）。未更改规则正文、协议公共层或其他IP执行代码。

新增`test_syscnt_service_native.py`从真实Descriptor进入命令处理、真实Wrap进入记录参数的SDK替身，验证九条命令的长度/实例/容量边界、Golden响应、错误码和无隐式初始化。当前没有Application注册，也尚未形成正式HIL结果。

2026-09-04 05:15 CST：该Native契约测试编译执行通过（guard `20260904_051519_f442ba9a`）；四个新C/H文件的严格语义数字、Doxygen与架构门禁通过。测试仅模拟本IP的底层Driver，其他IP没有运行。

2026-09-04 05:18 CST：Wrap/Service批次总软件门禁通过（929 PASS、14条件软件SKIP，guard `20260904_051600_98b1e87e`）。新增Native测试已在WSL单独执行通过，不把Windows缺编译器的条件SKIP记为IP硬件SKIP。

### 6.4 固件注册与构建

2026-09-04：Application静态Manifest增加SYSCNT组，FPGA/Silicon Board各声明逻辑实例0，既有工程Manifest加入本IP Service/Wrap源文件。保持main与公共注册算法不变，不在初始化时开启SYSCNT时钟或计数。构建与后续PFLASH部署仍使用现有配置流水线。

2026-09-04 05:20 CST：通过当前仓库`run_config.yaml`构建`ET6801_SILICON_FLASH`（该现有目标含FPGA_VERSION，用于当前FPGA的PFLASH流程），Keil结果0 Error/0 Warning。证据：`artifacts/runs/20260904_051954_352183_local_et6801_fpga_atp_testing/stages/build_firmware_silicon/keil_silicon.log`。编译通过不代表下载或HIL通过。

### 6.5 下一阶段最短路径

1. G01替代基线已获人工批准；实现前确认本次SYSCNT不是平台活动时间源。
2. 先按2.3节整改Chip Driver并做定向验证，再封装停止装载、读回、Enable/Disable和P0；禁止先堆Service再回头补驱动风险。
3. 独立确认时钟Profile与Halt路由，再补边界、计时和停核Case；需改其他IP时单独申请范围。
4. 完成一个逻辑开发批次再跑软件门禁；HIL按用户指定SYSCNT范围，通过配置流水线执行，不自动扩成全部IP。

## 第七章 当前芯片测试情况

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-09-04 08:50 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-09-04 06:39 CST` | `2157037e3937d1d26a01390ae0bd652f40f788dd` | `true` | `artifacts/runs/20260904_063646_997568_local_et6801_fpga_atp_testing/tests/syscnt/` |

Firmware Build ID：`et6801-silicon-common-v0.1`；Registry Hash：`6880b515`；COM12@115200；实际为XC7VX980T FPGA/Core0。Build ID不是Silicon实测声明。

部署证据：`artifacts/runs/20260904_060932_071362_local_et6801_fpga_atp_testing/`，同次bitfile→BootROM→PFLASH Verify→Flash运行全部通过。时钟独立诊断：`artifacts/runs/20260904_syscnt_clock_probe/clock_probe.json`。最终软件门禁951 PASS/14条件软件SKIP，不与硬件统计混合。

最终Excel：`artifacts/reports/20260904_064000_167713_ET6801_SYSCNT测试报告.xlsx`。三个Sheet分别为测试报告、执行明细、规格追溯；已只读核对7条Case均为PASS且备注非空，执行明细23条，寄存器名称和十六进制值均由真实结果及芯片映射生成。

Session Spec SHA256：`a9bfba50840b79c18a3b9d1c08b296bf39c1b985cbc5f08eaae5f85767218069`。运行时Dirty为文档中的M/4初值说明及观测表头修正，测试代码仍为上述Commit。之后只回写本芯片文档的运行事实，不改已测试公共SPEC/报告模板。

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 7 | 7 | 7 | 0 | 0 | 0 | 23 |

- SYSCNT_P0_001：六种64-bit位型停止装载，双窗口两次读回；6项PASS。
- SYSCNT_P0_002：运行→停止保持→恢复及EN读回；1项PASS。
- SYSCNT_P1_001：低32-bit进位、64-bit回绕及双窗口；2项PASS。
- SYSCNT_P1_002：12.5M→6.25M→12.5M频率标识，不启动计数；1项PASS。
- SYSCNT_P2_001：两个源×10/50/100/1000/10000ms，DWT双端夹取；10项PASS。
- SYSCNT_P2_002：PAUSE和RUN_FREE，实际DHCSR停核读回；2项PASS。
- SYSCNT_P3_001：每轮重建基线的20轮装载/启停；1项PASS。

### 新增规划Case的执行安排（不是运行结果）

`SYSCNT_P2_003`：规划状态为PLANNED；本轮安排为**SKIP（人工要求暂不测试）**；实际结果为NOT_EXECUTED，未产生波形或测量值。

- 外部条件：GPIO输出引脚、示波器通道、电压与共地接线尚未确认；完成安全连接确认后才具备外部测量条件。
- 实现条件：另有本地脉冲接口及Case实现缺口，须先完成，不能用SKIP掩盖。

当前总规划8条，已实现/注册7条，未实现PLAN 1条。上表SKIP仅表示本轮人工执行安排，不是pytest运行SKIP；最近一次运行仍保持7 PASS、0 FAIL、0 SKIP、23 Executions，不生成新的Session、Excel或虚假Evidence。既有示波器已接入平台不等于本Case的信号线与测量配置已确认。

ET6801适配要点：使用已确认的SYSCNT计数使能、64-bit连贯读取和时钟源映射；当前FPGA两个源名义输入均12.5MHz，外部测量不得用本次脉宽反向校准频率。输出GPIO从空闲安全引脚选择，不占用控制串口或其他已接线IP；本轮未指定端口、PAD或示波器通道。1ms为沿用片内Case的功能验收预算，不是3101 Case6给出的数字，也不是已确认的ET6801电气精度规格；仪器误差上界按实际仪器规格和采样设置计算。

首轮Report导出失败（不是硬件FAIL）：P1数组被重复聚合，P2暂停数组存在同类形状问题，P3重复使用final_count键。修复限于本IP Observation形状和文档模板，不修改断言、公共报告器或原始结果。新增真实数组形状软件测试；最终重跑全部SYSCNT及报告阶段成功，旧失败Run保留原状态。

关键实测：PAUSE两次计数均为`0x0000000100455EAF`；RUN_FREE从`0x00000001002FAF1E`增加到`0x00000001004419A4`。两个参数各四次DHCSR均为`0x00030003`，bit17 S_HALT=1。DBGH在PAUSE为1、RUN_FREE为0，恢复后为0且计数继续推进。原始DHCSR按参数保存，不依赖调试工具可能重名的日志附件。

两源五窗口的最坏相对参考误差不超过8.12µs，采样区间宽度不超过15.68µs，分别低于1ms/0.1ms预算。10ms等参数是PC等待窗口，实际两次硬件采样间隔还含通信时间；比较的是DWT实际测得间隔，不把PC睡眠值当精度Golden。不据此宣称绝对晶振精度已测试。

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |

### 覆盖边界与本轮决策

- 7条已注册Case及8个准入数字Feature均已执行；23为参数Execution数，不是23条Case。
- 当前FPGA/Core0的Halt响应已证实；不据此改变STIMER结论，也不宣称双Core活动组合已覆盖。
- G07已形成P2_003 PLAN，但没有对应实现和外部仪器结果；人工SKIP安排不改变历史运行统计。不能宣称参考要求全集已实测覆盖或整体Implementation Ready。G04只读窗口访问属性争议仍保留。
- 当前顶层Pipeline缺少单IP选择，会遍历全部Registry。本轮仅在调用进程中把Registry选择限制为原注册表的syscnt条目，再调用原Pipeline main；其全部Case仍由既有`run_ip_tests.py --ip syscnt`执行。选择入口留在诊断Artifact的`run_selected_ip.py`，不是新的平台Runner。连接和动作仍取同一run_config，源码注册表、公共Runner均未修改；没有运行其他IP HIL。
- 编码环境设置PYTHONUTF8=1，修复Windows GBK读取UTF-8 Git Diff的启动环境问题；没有修改公共Checker。
<!-- ET_CHIP_TEST_STATUS_END -->
