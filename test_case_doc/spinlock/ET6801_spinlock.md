# ET6801 SPINLOCK Chip Analysis & Adaptation Contract

> 本文件只记录 ET6801 SPINLOCK 的硬件、寄存器、Driver、历史测试和公共契约适配事实。
> 公共 Feature、Case、Oracle 和稳定接口以同目录 `spinlock.md` 为唯一权威来源。
> 当前已实现11个SPINLOCK Formal Case和ET6801双Core Peer映射。2026-08-28正式FPGA双核流程在提交`ba1304b`上完成15个参数化执行，结果15 PASS、0 FAIL、0 SKIP。

# 第一章 IP分析与Source Coverage

## 1.1 分析目标与证据优先级

```text
Target chip  = ET6801
Target IP    = SPINLOCK
Source SHA   = 5fffa0312a9a7317a933f2205a5efa85205de12e
Hardware run = FPGA PASS, 2026-08-28 20:20 CST

ET6801 SVD / current generated header
  > ET6801 current SDK Driver
  > ET6801 historical FPGA source and log
  > ET6003 / ET3101 family reference
```

前代芯片资料只用于识别稳定语义和测试方法，不能覆盖 ET6801 当前 SVD。源码存在不等于已进入自动化平台，历史日志也不等于当前工作树 PASS。

## 1.2 Source Map Coverage

| Source | Locator | 状态 | 定向结论 |
|---|---|---|---|
| requirements | `ip-analysis-sources.yaml::et6801.requirements` | NO_MATCH | 对登记需求根执行 `spinlock/SpinLock/硬件锁/自旋锁` 定向检索，无匹配；不据此否定硬件Feature。 |
| ET6801 SVD | `<et6801-verification>/Tools/RegGen/svd/spinlock_cfg.svd` | FOUND | Target Direct Evidence；寄存器、Field、64 Resource、模式、Owner和Clear Key语义完整。 |
| merged SVD | `test_case_doc/ET6801.svd` | FOUND | Target Direct Evidence；确认实例、Base Address和最终合并命名。 |
| generated header | `firmware/chips/et6801/sdk/CMSIS/Device/Include/et6801.h` | FOUND | Target Generated Evidence；与SVD生成结构交叉核对。 |
| ET6801 Driver | `<et6801-verification>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_spinlock.*` | FOUND | Target Current Driver Evidence；确认正式API与隐式行为。 |
| ET6801 FPGA source | `<et6801-verification>/DFP/Test/FPGATest/spinlock_fpga_test.c` | FOUND | Target Historical Test；包含一步/两步双Core交接示例，但当前入口只调用一步模式。 |
| ET6801 test log | `<et6801-verification>/DFP/Test/TestLog/spinlock_testcase.log` | FOUND | Target Historical Log；有Core0/Core1 Case编号输出，但对应Case源码未找到，不能精确映射。 |
| ET6003/ET3101 source | `D:/lihuan/vibe_code/code/SDK/git/{6003,3101}` | FOUND | Family Reference Only；确认双Core交接、临界区和共享资源测试思想。 |
| current capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/spinlock.yaml` | FOUND | 已表达实例、Base、模式、Resource/Process数量及Batch、Global、Clear Key能力；Resource数量证据来自`SL_LOCK_INFO_ARRAY`寄存器数组。 |
| current platform code | `firmware/{wrap,services}`、`pc/et_test_platform/{drivers,test_cases}` | FOUND | 已实现SDK测试扩展、公共Wrap/Service、PC Driver和11个Formal Case；正式FPGA双核流程已形成当前提交硬件结论。 |

ET6801 G盘登记资料与本地SDK镜像中的目标SVD、Driver和FPGA测试源码已定向核对；关键文件内容一致。没有对整个SDK或文档库做无目标全量扫描。

## 1.3 IP工作原理与应用

ET6801 SPINLOCK提供64个独立硬件锁资源，用于两个Core或其他硬件Master之间保护共享内存、共享寄存器和不可重入临界区。读取空闲Resource的`SL_LOCK_INFO`会原子占用该Resource并记录当前CPU Master ID；Resource被占用后，只有原Master可以释放。

两种工作模式：

1. 一步模式：硬件原子获取Resource并登记Master ID，适合Core级快速互斥。
2. 两步模式：取得硬件Owner后再登记4-bit Process ID，适合同一Core内进一步区分线程或软件执行实体。

Batch Release按当前Master释放其全部Resource；Global Release忽略Master并清除全部Resource，只能用于初始化或异常恢复。SPINLOCK没有IRQ和DMA，完成判定依赖同步状态、异步Peer Job、无副作用Flags，以及仅对仍锁定资源执行的Owner读回。

## 1.4 Claim Ledger

| Claim | 状态 | 直接证据 | 当前结论 |
|---|---|---|---|
| 实例与地址 | VERIFIED | merged SVD | 单实例`spinlock0`，Base=`0x40209000`，别名窗口=`0x40289000`。 |
| Enable/Disable | VERIFIED | `CFG_SL_LOCK_EN.sl_lock_en` | bit0控制Enable，bit16为写使能；进入/退出不改变现有锁状态。 |
| 一步/两步模式 | VERIFIED | `sl_two_step_mode_en` | bit4=0一步，bit4=1两步，bit20为写使能。 |
| 64个Resource | VERIFIED | `SL_LOCK_INFO_ARRAY[64]`与两个Flag寄存器 | Resource 0..63，低高各32个Flag。 |
| Master Owner | VERIFIED | `SL_LOCK_INFO[15:8]`与SVD描述 | 读取空闲Resource原子加锁并记录Master；仅原Master可解锁。 |
| Process ID | VERIFIED | `SL_LOCK_INFO[7]`与`[3:0]` | 两步模式支持Process ID 0..15和初始化完成标志。 |
| Batch Release | VERIFIED | `CFG_SL_BATCH_LOCK_CLR` | 正确Key只清当前CPU/Master已占用资源。 |
| Global Release | VERIFIED | `CFG_SL_GLOBAL_LOCK_CLR` | 正确Key忽略Master清除全部64个Resource，只用于初始化。 |
| Clear Key保护 | VERIFIED | 两个Key字段描述 | 只有目标Key执行Clear；错误Key不应产生清除。 |
| Try有界返回 | DRIVER_VERIFIED | current Driver | Try循环上限1000，竞争时返回Timeout；这是Driver策略，不是硬件超时器。 |
| 双Core阻塞交接 | HIL_VERIFIED | 当前正式FPGA双核运行 | Core0/Peer交接、WAITING/HOLDING和Owner读回均由Formal Case验证。 |
| 两步双Core交接 | CODE_ONLY | ET6801 FPGA source | 两步模式源码存在但入口被注释，不能视为执行证据。 |
| 临界区互斥压力 | HIL_VERIFIED | 当前正式FPGA双核运行 | P3 Formal Case使用共享计数与违规计数形成严格Oracle并已通过。 |
| IRQ/DMA | NOT_APPLICABLE | ET6801 SVD/Driver | 当前SPINLOCK无IRQ和DMA寄存器或API。 |
| 自动化平台实现 | FPGA_VERIFIED | current tree与当前HIL证据 | Capability、SDK测试扩展、Wrap、Service、PC Driver和11个Formal Case已闭合；FPGA参数化执行15 PASS。 |

# 第二章 Driver分析

## 2.1 当前正式Driver API

| API | 模式 | 行为 | 自动化使用判断 |
|---|---|---|---|
| `SPINLOCK_init(mode)` | 一步/两步 | 写Mode/Enable后立即Global Release | 可用于普通基线，但不能用于Disable状态保持Case。 |
| `SPINLOCK_deInit()` | 通用 | 先Global Release再Disable | 不能验证“Disable不改变锁状态”。 |
| `SPINLOCK_acquire(res, process)` | 两步 | 无限轮询直到Master/Process/Valid完全匹配 | 只能用于异步Peer Job，禁止占用PC控制通道。 |
| `SPINLOCK_acquireTry(res, process)` | 两步 | 最多1000次尝试 | 可用于竞争Timeout与恢复Case。 |
| `SPINLOCK_release(res, process)` | 两步 | 写当前Master与Process、Flag=0释放 | 可用于Owner保护Case。 |
| `SPINLOCK_fastAcquire(res)` | 一步 | 无限轮询直到Master匹配 | 只能用于异步Peer Job。 |
| `SPINLOCK_fastAcquireTry(res)` | 一步 | 最多1000次尝试 | 可用于竞争Timeout与恢复Case。 |
| `SPINLOCK_fastRelease(res)` | 一步 | 写0释放指定Resource | 可直接适配。 |
| `SPINLOCK_isResourceAcquired(res)` | 通用 | 从两个Flag寄存器读取占用状态 | 只能证明Locked，不能证明Owner。 |
| `SPINLOCK_batchReleaseAll()` | 通用 | 写Batch Key | 可直接适配。 |
| `SPINLOCK_globalReleaseAll()` | 通用 | 写Global Key | 可直接适配为Case入口基线。 |

## 2.2 Driver缺口与补齐边界

当前已在SDK Driver底部测试扩展区补齐以下最小接口，Wrap仍只调用Driver：

1. 配置读回与“只切换Enable/Mode、不执行Global Release”的接口；
2. 两个Flag Bank和指定Resource完整Owner信息读取接口；
3. 受限Clear Key探测接口，用于提交错误Key验证保护；
4. 不需要新增IRQ、DMA或跨IP接口。

测试扩展API命名必须带明确`test`语义，并放入SDK发布时可整体删除的测试扩展区。不能让Wrap直接操作寄存器，也不能把ET6801寄存器类型暴露到公共头文件。

## 2.3 当前Driver风险

- `SPINLOCK_init()`与`deInit()`都会Global Release；若公共Wrap直接使用，会掩盖Disable状态保持Feature。
- 两个阻塞Acquire函数没有超时；若Service同步调用，控制UART会永久失去响应。
- `acquireTry`的1000次为软件轮询次数，不能报告成硬件Timeout精度。
- `isResourceAcquired`只读Flag；Formal Case必须同时读取Owner信息防止错误Owner也被误判为成功。

# 第三章 寄存器分析

## 3.1 Register Map

| Register | Offset | Access | Reset | 关键语义 |
|---|---:|---|---:|---|
| `ET_HEAD` | `0x0000` | R/W + RO | `0x534C534C` | 集成测试签名；不作为SPINLOCK功能Feature。 |
| `CFG_SL_LOCK_EN` / generated `SL_LOCK_EN` | `0x0004` | R/W | `0x00000000` | Enable、一步/两步Mode及各自写使能。 |
| `CFG_SL_BATCH_LOCK_CLR` / `SL_BATCH_LOCK_CLR` | `0x0008` | W/Read-zero | `0x00000000` | Key=`0x67891230`释放当前Master全部资源。 |
| `CFG_SL_GLOBAL_LOCK_CLR` / `SL_GLOBAL_LOCK_CLR` | `0x000C` | W/Read-zero | `0x00000000` | Key=`0xCDEF1230`释放全部Master资源。 |
| `SL_LOCK_FLAG_RPT1` | `0x0010` | RO | `0x00000000` | bit[31:0]对应Resource 31..0。 |
| `SL_LOCK_FLAG_RPT2` | `0x0014` | RO | `0x00000000` | bit[31:0]对应Resource 63..32。 |
| `SL_LOCK_INFO_ARRAY[64].SL_LOCK_INFO` | `0x0800 + 4*n` | R/W | `0x00000000` | 锁定、Master、Process Valid和Process ID；读空闲项会原子加锁。 |
| `ET_TAIL` | `0x0FFC` | R/W + RO | `0x00000000` | 集成测试寄存器；不作为SPINLOCK功能Feature。 |

## 3.2 Field语义

| Field | Bit | 语义 | Public Endpoint/Feature |
|---|---:|---|---|
| `SL_LOCK_EN.SL_LOCK_EN` | 0 | 模块Enable | `CONFIG.ENABLE` / `SPINLOCK_F_001` |
| `SL_LOCK_EN.SL_TWO_STEP_MODE_EN` | 4 | 0一步，1两步 | `CONFIG.MODE` / `SPINLOCK_F_002`, `F_003` |
| `SL_LOCK_EN.*_WRITE` | 16,20 | 对应配置字段写使能 | Chip Driver内部事实，不进入公共Case参数。 |
| `SL_LOCK_FLAG_RPT1/2`目标bit | 31:0 | 无副作用的Resource Locked状态 | `RESOURCE_INFO.LOCKED` / `F_004` |
| `SL_LOCK_INFO.FLAG` | 31 | Owner寄存器内的锁标志；读取空闲项会触发Acquire，不能作为空闲观测来源 | 仅在对应Flag已为1时辅助核对 |
| `SL_LOCK_INFO.MASTER_ID` | 15:8 | 当前硬件Owner | `RESOURCE_INFO.MASTER_ID` / `F_007`；仅在对应Flag=1时读取 |
| `SL_LOCK_INFO.PROCESS_ID_INIT` | 7 | Process ID登记完成 | `RESOURCE_INFO.PROCESS_ID_VALID` / `F_006`；仅在对应Flag=1时读取 |
| `SL_LOCK_INFO.PROCESS_ID` | 3:0 | 两步模式Process ID | `RESOURCE_INFO.PROCESS_ID` / `F_006`；仅在对应Flag=1时读取 |

## 3.3 关键硬件约束

- Resource信息寄存器不是普通无副作用状态寄存器：读取空闲Resource会触发原子加锁。测试Driver必须区分只读Flag与会产生Acquire副作用的Owner读取路径。
- `resource_snapshot_get`必须先读取`SL_LOCK_FLAG_RPT1/2`目标bit；只有bit=1时才允许读取对应`SL_LOCK_INFO`。bit=0时直接返回空闲且Owner字段无效。
- Batch/Global Clear寄存器回读恒为0，不能用寄存器回读证明动作完成；必须观察Resource Flags，并且只对Flag仍为1的资源读取Owner。
- Disable不会清除锁是SVD明确硬件语义，必须用不带Global Release的Driver路径验证。
- SVD没有IRQ、DMA、超时计数、公平性或优先级字段，不得凭空建立这些Feature。

# 第四章 当前测试代码与历史覆盖分析

## 4.1 ET6801 FPGA测试源码

| 历史函数 | 测试意图 | 当前证据边界 | Public Case承接 |
|---|---|---|---|
| `SPINLOCK_1` | 两步模式，Core0以Process 2持有Resource 7，Core1以Process 3等待交接 | 源码存在但当前入口被注释；只有打印和固定3秒Delay，无结构化断言 | `SPINLOCK_P2_002` |
| `SPINLOCK_2` | 一步模式，Core0持有Resource 5，启动Core1竞争，释放后Core1获取 | 当前入口调用；只有打印和Delay，未核对Flags/Owner/进入次数 | `SPINLOCK_P2_002` |

Formal Case不照抄固定Resource、固定地址或3秒Delay。它从Capability选择Resource，用异步Peer Job状态建立因果顺序，并通过Flags/Owner证明交接。

## 4.2 历史Test Log

`spinlock_testcase.log`记录Core0/Core1多个`test_case0..20`输出，但当前登记源码根中没有找到对应Case实现，无法确定每个编号实际配置、刺激和断言。因此：

- 日志只证明历史上存在更广测试活动；
- 不能把Case编号直接映射为某个Feature；
- 不能把日志中的`pass`继承为当前平台PASS；
- Source Item Trace保留`UNKNOWN`，等待找回对应源码后再精确映射。

## 4.3 前代芯片参考

ET6003/ET3101资料复现了以下稳定测试思想：一步/两步双Core交接、共享资源保护、临界区串行化和重复Acquire/Release。当前公共Case已承接这些Feature，但参数、Owner和执行路由必须由ET6801 Capability/Peer Mapping提供，不继承前代物理常量。

## 4.4 Source Item Trace

| Source Item | 判定 | Public Feature | Public Case | 说明 |
|---|---|---|---|---|
| SVD Enable/Disable且不改变锁状态 | RETAINED | `F_001`, `F_012` | `P0_001`, `P1_002` | 需要测试Driver隔离正式Driver的隐式Global Release。 |
| SVD一步/两步模式 | RETAINED | `F_002`, `F_003` | `P0_001`~`P2_002` | 模式身份进入Capability。 |
| SVD 64 Resource与双Flag Bank | RETAINED | `F_004`, `F_005` | `P0_002`, `P1_001` | P0覆盖全Resource获取释放；P1通过跨Flag Bank同时占用与逐项释放证明独立性。 |
| SVD Process ID 0..15 | RETAINED | `F_006` | `P0_003` | 全Process ID参数化。 |
| SVD Master only release | RETAINED | `F_007` | `P2_001`, `P2_003` | 必须使用真实Peer Master。 |
| Driver Blocking/Try | RETAINED_WITH_STRONGER_ORACLE | `F_008`, `F_009` | `P2_001`, `P2_002` | 增加Job状态、Owner和进入次数证据。 |
| SVD Batch/Global Key | RETAINED | `F_010`, `F_011`, `F_014` | `P1_003`, `P2_004` | 错误Key保护与Release Scope分开验证。 |
| ET6801双Core FPGA示例 | SUPERSEDED | `F_007`, `F_008` | `P2_002` | 去除固定Delay和纯打印判定。 |
| 前代Critical Zone示例 | RETAINED_AS_METHOD | `F_013` | `P3_001` | 用共享计数与Violation Count形成严格Oracle。 |
| `spinlock_testcase.log` Case0..20 | UNKNOWN | — | — | 缺少对应源码，不能建立无根据映射。 |
| `ET_HEAD/ET_TAIL` | REJECTED | — | — | 集成测试寄存器，不是SPINLOCK业务Feature。 |
| IRQ/DMA | NOT_APPLICABLE | — | — | ET6801目标硬件无此能力。 |

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | ET6801参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| SPINLOCK_F_001 | SUPPORTED | `SL_LOCK_EN.bit0`，bit16写使能 | ADAPTED | `P0_001`, `P1_002` |
| SPINLOCK_F_002 | SUPPORTED | FAST/一步模式，Mode bit4=0 | ADAPTED | `P0_001`, `P0_002`, `P2_001`, `P2_002` |
| SPINLOCK_F_003 | SUPPORTED | NORMAL/两步模式，Mode bit4=1 | ADAPTED | `P0_001`, `P0_003`, `P2_001`, `P2_002` |
| SPINLOCK_F_004 | SUPPORTED | 两个32-bit Flag Bank + 64项Info | ADAPTED | `P0_002`, `P0_003`, `P1_001` |
| SPINLOCK_F_005 | SUPPORTED | Resource 0..63 | ADAPTED | `P1_001` |
| SPINLOCK_F_006 | SUPPORTED | Process ID 0..15，仅两步模式 | ADAPTED | `P0_003` |
| SPINLOCK_F_007 | SUPPORTED | Master ID 8-bit；Core0/Core1均通过`DUALCORE_getCurrentCoreId()`发布并由Owner读回验证 | ADAPTED | `P2_001`, `P2_003` |
| SPINLOCK_F_008 | SUPPORTED | Core1异步Job通过WAITING/HOLDING/ENTER_COUNT提供可查询交接 | ADAPTED | `P2_002` |
| SPINLOCK_F_009 | SUPPORTED | Driver Try上限1000次；Peer TRY Job返回BUSY或进入HOLDING | ADAPTED | `P2_001` |
| SPINLOCK_F_010 | SUPPORTED | DUT与Peer分组持锁，Batch只清当前Master资源 | ADAPTED | `P2_004` |
| SPINLOCK_F_011 | SUPPORTED | Global Key清除两个Master的全部测试Resource | ADAPTED | `P2_004` |
| SPINLOCK_F_012 | SUPPORTED | SVD明确Disable不改变已有锁 | ADAPTED | `P1_002` |
| SPINLOCK_F_013 | SUPPORTED | AXI SRAM1共享计数区使用volatile、DMB/DSB和同一ONE_STEP Resource保护 | ADAPTED | `P3_001` |
| SPINLOCK_F_014 | SUPPORTED | Batch/Global各有固定授权Key | ADAPTED | `P1_003` |

当前`spinlock.yaml`已补充Mode集合、`resource_count=64`、`process_id_count=16`及Batch/Global/Key硬件能力；公共Case只通过Capability和Runtime Service取得这些目标事实，不写死ET6801数量。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| SPINLOCK_P0_001 | ADAPTED | 不隐式清锁的配置/读回Test Driver、Wrap、Service和PC Driver已实现。 |
| SPINLOCK_P0_002 | ADAPTED | Capability发布64个Resource，Formal Case按运行时数量完成全Resource矩阵。 |
| SPINLOCK_P0_003 | ADAPTED | Capability发布16个Process ID，安全Owner Snapshot和全Process矩阵已实现。 |
| SPINLOCK_P1_001 | ADAPTED | LOW/HIGH Flag Bank快照和Capability边界Resource独立性Case已实现。 |
| SPINLOCK_P1_002 | ADAPTED | 测试扩展配置接口只改变Enable/Mode，不调用Global Release。 |
| SPINLOCK_P1_003 | ADAPTED | 受限Key Probe只接收授权真假与作用域，不向公共层暴露ET6801 Key。 |
| SPINLOCK_P2_001 | ADAPTED | Peer TRY Job、BUSY结果、HOLDING状态和Peer Master读回均已实现。 |
| SPINLOCK_P2_002 | ADAPTED | Peer BLOCKING_HOLD Job提供WAITING/HOLDING、ENTER_COUNT和Release/Abort控制。 |
| SPINLOCK_P2_003 | ADAPTED | Peer RELEASE_ONCE Job已实现，Formal Case逐项比较非Owner释放前后Owner事实。 |
| SPINLOCK_P2_004 | ADAPTED | Peer HOLD Job维持跨Master分组占用，Formal Case分别验证Batch和Global范围。 |
| SPINLOCK_P3_001 | ADAPTED | Core0同步压力命令与Core1异步压力Job共用AXI SRAM1计数区及内存屏障。 |

### 6.1 实现顺序

1. 已完成Capability语义、SDK测试扩展、芯片中立Wrap/Service/PC Driver和11个Formal Case；
2. 已实现带WAITING/HOLDING/ACK/Abort语义的Core1 Peer Job及AXI SRAM1共享计数映射；
3. 已完成Core0 FPGA/Silicon与Core1 ITCM/PFLASH双目标编译；
4. 已通过正式Pipeline部署Core0 PFLASH固件和Core1 ITCM Peer，并验证Peer Mailbox；
5. 已完成FPGA P0~P3 HIL；Silicon结果仍须独立验证，禁止继承FPGA PASS。

### 6.2 当前覆盖结论

```text
Public Feature: 14
- ET6801 Hardware SUPPORTED: 14
- Platform ADAPTED: 14
- Platform IMPLEMENTATION_GAP: 0
- Platform MAPPING_GAP: 0

Formal Case: 11
- PLAN: 0
- SPEC: 11
- FPGA PASS/FAIL/SKIP: 11/0/0（15个参数化执行全部PASS）
- Silicon PASS/FAIL/SKIP: 0/0/0

External wiring required: 0
On-chip peer required: P2_001..P3_001
```

### 6.3 剩余风险

- 历史`test_case0..20`的对应源码缺失，尚不能证明公共11个Case已完全覆盖所有历史原子Feature；找回源码后必须重新做Source Item Trace。
- ET6801 Core0/Core1到SPINLOCK硬件Master ID的映射已由P2 Formal Case验证；Silicon仍需独立取证。
- AXI SRAM1共享区的volatile和DMB/DSB策略已由FPGA P3共享计数验证；Silicon Cache/总线行为仍需独立取证。
- SVD明确Owner语义，但Owner信息读取本身可能对空闲Resource产生Acquire副作用；实现测试Driver时必须避免把“观测”误做成“刺激”。
- 当前FPGA证据：`artifacts/runs/20260828_202500_formal_dualcore_spinlock_exact_sha/tests/spinlock/session.json`；Silicon尚无PASS证据。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:24 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 20:20 CST` | `ba1304b458148b681ec5f0a6a392cdf7c0757f76` | `false` | `artifacts/runs/20260828_202500_formal_dualcore_spinlock_exact_sha/tests/spinlock/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 11 | 11 | 11 | 0 | 0 | 0 | 15 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |
<!-- ET_CHIP_TEST_STATUS_END -->
