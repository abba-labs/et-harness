# WDG Public Test Contract

> 本文件定义 WDG 的跨芯片稳定 Feature、Case、最小充分 Observation、Oracle 与未来自动化接口语义。
> 当前已实现并注册 14 个轻量 Formal Case；P2时基和NMI路径由CRG/CPU Owner提供独立入口，Case只负责跨IP顺序与证据断言。
> 具体芯片的实例、物理地址、IRQ、目标SDK符号、时钟物理字段、CPU/NMI Source绑定和历史验证证据只进入同目录 `<CHIP>_wdg.md`。
> Formal Case 前置隔离统一遵循 `R210`：第一次 Feature 配置前由 Case 显式复位本 Case 参与的全部 WDG 实例，并最后复位 Resource Pool；本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

### 0.1 稳定逻辑模型

| 稳定语义 | 公共含义 | 规则边界 |
|---|---|---|
| `mode` | `WINDOW` / `INDEPENDENT` | WINDOW 使用 low/high；INDEPENDENT 不依赖窗口门限。 |
| `work_mode` | `ROUND1_IRQ_ROUND2_RESET` / `SAME_ROUND_IRQ_RESET` | 描述自然事件轮次，不等于当前测试已经通过。 |
| `reload_count` | 一个完整超时轮次的重载尺度 | 非零安全值；最大范围由 Capability 声明。 |
| `window_low_count` / `window_high_count` | WINDOW 合法喂狗区间 | 稳定语义为闭区间 `[low, high]`，并满足 `low <= high <= reload`. |
| `reset_enable` | 是否允许 WDG 事件输出系统复位请求 | 关闭后用于在线观察自然 IRQ；开启后必须走真实 reset/reconnect 证据链。 |
| `halt_pause_enable` | Debugger Halt 期间是否暂停 WDG 计数 | `1=暂停`，`0=继续`；具体芯片 API 方向差异由 Chip Adaptation 处理。 |
| `irq_source` | 单个逻辑 `WDG_TIMEOUT` Source | Raw、有效状态、真实 ISR 交付与持久记录分开保存。 |
| `record_mask` | `RESET` / `INTERRUPT` | 两种持久历史不能互相冒充或用错 Clear 动作。 |

配置动作只能在目标定义允许的状态执行。未知枚举、未知 bit、非法窗口关系和保留字段必须失败关闭。时钟切换、CPU/NMI 路由、Debugger 与系统重连是对应 Owner 的 Case 编排职责，不得隐藏进 WDG Driver/Service。
公共 `WdgDriver` 构造必须显式接收 Profile/Fixture 解析后的逻辑 `instance_id`，禁止默认选择实例0。

### 0.2 稳定动作语义

未来公共 Driver / Firmware Service / Wrap 至少需要表达以下稳定动作；名称用于设计导航，不代表当前已经实现，也不要求现在冻结所有 Wire ID：

```text
CAPABILITIES_GET
CONFIGURE / CONFIG_GET
UNLOCK / LOCK
ENABLE / DISABLE
FEED
STATUS_GET
MODULE_RESET
IRQ_ENABLE / IRQ_DISABLE
IRQ_MASK / IRQ_UNMASK
IRQ_FORCE / IRQ_CLEAR / IRQ_SNAPSHOT_GET
RECORD_GET / RECORD_CLEAR
```

系统级 reset 发生后旧 Target Session 必须作废；PC Runtime 负责链路 reopen、重新 HELLO/Discover 和新 Session/Driver 构造。`MODULE_RESET` 只代表 WDG 模块生命周期，不能作为系统 reset Oracle。

NMI 路由不属于 WDG Wire Action。需要验证超时 NMI 时，由 CPU/NMI Owner 配置目标 Source、mask 和处理域，WDG 只负责产生自然超时事件。

### 0.3 稳定 Observation Endpoint

| 稳定 Endpoint | Evidence Source | 证明用途 |
|---|---|---|
| `CAPABILITY.RUNTIME` | Target Service | 运行时实例/模式/Feature结构快照。 |
| `CONFIG.READBACK` | DUT配置端点 | 证明配置实际接受值，尤其用于写保护。 |
| `STATE.ENABLED` | DUT状态端点 | 使能/禁用真实状态。 |
| `COUNTER.CURRENT` | DUT状态端点 | 当前计数，用于计数、feed和窗口Case。 |
| `IRQ_RAW.WDG` | DUT IRQ Raw端点 | Mask前逻辑Source pending。 |
| `IRQ_STATUS.WDG` | DUT IRQ有效端点 | Mask后有效Source状态。 |
| `IRQ_DELIVERY.LATCHED_SOURCE` | Firmware IRQ Service | 真实ISR锁存来源。 |
| `IRQ_DELIVERY.EVENT_COUNT` | Firmware IRQ Service | 真实ISR交付次数。 |
| `RECORD.INTERRUPT` | 持久系统状态端点 | WDG中断历史记录。 |
| `RECORD.RESET` | 持久系统状态端点 | WDG复位请求历史记录。 |
| `NMI_ROUTE.SOURCE_RAW` | CPU/NMI Peer | CPU NMI屏蔽前Source事实。 |
| `NMI_ROUTE.SOURCE_MASKED` | CPU/NMI Peer | CPU NMI屏蔽后Source事实。 |
| `NMI_DELIVERY.EVENT_COUNT` | CPU/NMI Service | 目标处理域真实NMI交付次数。 |

Canonical Observation 一端点一事实。独立时间、session generation、Expected window、计数速率比、处理域Expected等属于 Measurement/Oracle，不得伪装成 WDG 硬件端点。

### 0.4 Oracle / Evidence 强度

- **基础计数**：必须保存 `COUNTER.CURRENT` 的多个实际样本和独立时间区间；Driver 自报时钟不能单独证明计数速率。
- **喂狗**：必须证明 feed 前后 counter 真实重新装载，并证明原剩余超时边界被延后；API 返回成功不能自证。
- **Window**：early/inside/late 刺激必须按实际 counter 相对 high/low 位置触发；inside 才允许 reload，窗口两侧非法 feed 必须形成自然事件或保持原超时进程。
- **IRQ**：Force 只验证控制面；自然超时/窗口事件必须由真实 WDG 事件产生。Raw、Status、Delivery、persistent record 分层保存。
- **Reset**：必须发生真实 DUT 系统 reset、旧 Session 失效、重新连接、新 Session 和 `RECORD.RESET`；`MODULE_RESET` 不能替代。
- **Same-round IRQ+Reset**：不能强制要求普通 ISR 一定先执行；若 reset 抢占 ISR，重连后的 persistent interrupt/reset record 作为核心证据。
- **Debug Halt**：必须使用真实 Debugger Halt/Resume；软件 delay、busy-loop、WFI/WFE 不能替代。
- **Clock**：由时钟 Owner 配置两个以上时基，使用独立时间 Observer 比较 `COUNTER.CURRENT` 变化比例；不能用时钟 Driver getter 自证。
- **NMI**：由 CPU/NMI Owner配置Source和mask，WDG只产生自然超时；软件Pend NMI不能替代WDG自然NMI。

### 0.5 稳定资源边界

WDG本体多数Case为DUT内部数字状态验证，最低可在R0完成。以下路径需要更高资源：系统reset/reconnect属于环境级生命周期；时钟Source/Divider需要片内Clock Peer；NMI需要CPU/NMI Peer；Debugger Halt需要真实Debugger控制。资源等级只说明证明强度，不代表Case状态或PASS。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| WDG_F_002 | WDG使能/禁用 | 使能后WDG进入真实计数过程；显式禁用后不得继续产生新的自然超时事件。 | `WDG_P0_002` |
| WDG_F_003 | WDG重载/当前计数 | 重载尺度与当前计数可被独立观测，并用于证明计数、feed和时基变化。 | `WDG_P0_002`, `WDG_P0_003`, `WDG_P2_001` |
| WDG_F_004 | WDG喂狗/重载 | 合法feed必须使当前计数重新回到配置重载尺度并延后原剩余超时。 | `WDG_P0_003`, `WDG_P1_002` |
| WDG_F_005 | WDG独立/窗口模式 | WDG支持独立模式与窗口模式，两种模式使用不同的feed合法性判据。 | `WDG_P0_003`, `WDG_P1_002` |
| WDG_F_006 | WDG窗口门限 | WINDOW模式仅允许counter位于`[low, high]`时正常feed；高于high时Feed触发窗口违规，低于low时硬件形成窗口超时。 | `WDG_P1_002` |
| WDG_F_007 | WDG复位输出 | WDG自然事件可关闭系统reset输出以在线观察IRQ，也可开启reset输出验证真实系统复位。 | `WDG_P0_004`, `WDG_P1_001`, `WDG_P1_003`, `WDG_P1_009` |
| WDG_F_008 | WDG IRQ/Reset轮次模式 | 两种轮次工作模式的自然事件时序可区分；同轮模式允许reset早于普通ISR执行。 | `WDG_P1_003` |
| WDG_F_009 | WDG Debug Halt行为 | 可选择真实Debugger Halt期间暂停WDG计数或继续推进并自然到期。 | `WDG_P3_001` |
| WDG_F_010 | WDG配置锁定/解锁 | Lock时受保护配置不得被修改；Unlock后新配置可实际生效并通过readback证明。 | `WDG_P1_005` |
| WDG_F_011 | WDG模块复位/恢复 | 目标WDG模块可独立复位并在系统连接保持在线的前提下重新配置、使能和运行。 | `WDG_P1_004` |
| WDG_F_012 | WDG IRQ使能/屏蔽/强制/清除与RAW/STATUS | 单逻辑WDG IRQ Source支持独立enable、mask、force、clear，并区分Mask前Raw和Mask后有效状态。 | `WDG_P1_001`, `WDG_P1_006` |
| WDG_F_013 | WDG IRQ真实投递 | 自然超时或窗口错误在IRQ使能且未屏蔽时形成真实ISR交付，并与Raw/Status保持因果一致。 | `WDG_P1_001`, `WDG_P1_002`, `WDG_P1_003`, `WDG_P1_006`, `WDG_P1_007` |
| WDG_F_014 | WDG复位记录 | 真实WDG系统复位后可读取目标逻辑实例的reset record，并可精确清除和复读。 | `WDG_P0_004`, `WDG_P1_003` |
| WDG_F_015 | WDG中断记录 | 真实WDG IRQ可形成目标逻辑实例interrupt record，并可与其他实例隔离、精确清除和复读。 | `WDG_P1_001`, `WDG_P1_007` |
| WDG_F_016 | WDG 多实例隔离 | 多个逻辑WDG实例的配置、计数、IRQ和持久记录只属于被操作实例，不发生跨实例污染。 | `WDG_P1_008` |
| WDG_F_017 | WDG时钟源/分频 | WDG计数与超时尺度随Clock Owner选择的片内时钟源和分频按可证明比例变化。 | `WDG_P2_001` |
| WDG_F_018 | WDG超时NMI路由 | Capability声明支持时，WDG自然超时可路由为CPU NMI，并只投递到目标处理域而不污染对照处理域。 | `WDG_P2_002` |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| WDG_P0_002 | P0 | WDG配置安全重载后使能可见计数推进，禁用后停止产生新的自然超时事件 | WDG使能禁用与计数基础测试 | SPEC |
| WDG_P0_003 | P0 | WDG独立模式合法喂狗使当前计数重新装载并延后原剩余超时 | WDG独立模式喂狗重载测试 | SPEC |
| WDG_P0_004 | P0 | WDG自然超时触发真实系统复位、旧Session失效、重连后目标实例reset record置位并可清除 | WDG真实超时复位与跨重启取证测试 | SPEC |
| WDG_P1_001 | P1 | WDG关闭复位输出后自然超时只产生真实IRQ与interrupt record且系统保持在线 | WDG复位输出关闭与自然中断测试 | SPEC |
| WDG_P1_002 | P1 | WDG窗口模式中Inside Feed合法重载、Early Feed形成违规IRQ、Late越过Low形成窗口超时IRQ | WDG窗口喂狗区域测试 | SPEC |
| WDG_P1_003 | P1 | WDG首轮IRQ次轮Reset与同轮IRQ+Reset两种工作模式的真实事件顺序和跨重启记录 | WDG轮次工作模式测试 | SPEC |
| WDG_P1_004 | P1 | WDG模块复位仅重置目标模块，系统连接保持在线并可重新配置运行 | WDG模块复位与恢复测试 | SPEC |
| WDG_P1_005 | P1 | WDG Lock期间配置保持原值且Unlock后新配置通过实际readback生效 | WDG配置写保护与解锁测试 | SPEC |
| WDG_P1_006 | P1 | WDG IRQ Enable/Disable/Mask/Unmask/Force/Clear对Raw、有效Status和真实Delivery的独立控制 | WDG中断控制矩阵测试 | SPEC |
| WDG_P1_007 | P1 | WDG自然IRQ使当前实例interrupt record置位并可精确清除 | WDG自然中断与中断记录测试 | SPEC |
| WDG_P1_008 | P1 | 两个WDG实例的配置、使能状态和IRQ投递互不污染 | WDG多实例隔离测试 | SPEC |
| WDG_P1_009 | P1 | 窗口模式下越过Low后开启reset输出可形成真实系统复位，并留下可清除的reset record | WDG窗口超时系统复位测试 | SPEC |
| WDG_P2_001 | P2 | 相同reload下片内WDG时钟源/分频变化引起COUNTER.CURRENT速率按独立时间比例变化 | WDG时钟源与分频集成测试 | IMPLEMENTED |
| WDG_P2_002 | P2 | WDG自然超时经CPU/NMI Owner路由到目标处理域且不错误投递到对照处理域 | WDG超时NMI路由与处理域隔离测试 | IMPLEMENTED |
| WDG_P3_001 | P3 | WDG调试暂停使能时真实Debugger Halt冻结超时进程，暂停失能时Halt期间继续计数并可自然到期 | WDG调试Halt行为测试 | SPEC |

## 3. Machine-readable Case Contract

> 已注册 Case 均使用 `ET_CASE_SPEC`。Capability一致性属于平台发现/契约门禁，不作为 WDG 硬件 Feature 或 Formal Case 计入覆盖。


### WDG_P0_002 - WDG使能禁用与计数基础测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P0_002
case_name: WDG使能禁用与计数基础测试
report_feature: |-
  1. WDG使能/禁用
  2. WDG重载/当前计数
p_level: P0
feature_refs: [WDG_F_002, WDG_F_003]
method:
  inputs:
  - 计数配置：选择两组彼此可区分且不会在测量窗口内造成系统复位的非零reload_count，并关闭复位输出。
  - 时间参考：准备与WDG数据路径独立的单调时间Observer，用于限定两次COUNTER.CURRENT采样间隔。
  steps:
  - 初始状态准备：解锁并禁用目标WDG，清除本Case相关IRQ与历史记录，配置独立模式、复位输出关闭和第一组安全重载值。
  - 使能前采样：读取STATE.ENABLED和COUNTER.CURRENT基线，确认目标尚未进入运行计数阶段。
  - 第一组计数启动：使能WDG，在两个有界独立时间点读取COUNTER.CURRENT并保存实际时间间隔。
  - 计数推进判定：比较两次计数值与独立时间事实，确认使能后计数按硬件定义方向单调推进且未出现自然超时事件。
  - 禁用行为验证：禁用WDG后再次读取STATE.ENABLED，并在覆盖原剩余超时的安全观察窗内检查没有新的IRQ或历史记录。
  - 第二组配置运行：在禁用态改为第二组reload_count，重复使能与计数采样并证明两组初始计数尺度可区分。
  - 结果汇总：保存两组reload配置、计数序列、使能状态和自然事件快照，随后禁用目标WDG。
  observations:
  - 使能状态端点：读取STATE.ENABLED，期望使能阶段为1、显式禁用后为0。
  - 当前计数端点：读取COUNTER.CURRENT序列，期望使能后按目标计数方向推进且第二组reload形成可区分的计数尺度。
  - 自然事件端点：读取IRQ_RAW.WDG与RECORD.INTERRUPT，期望安全测量窗和禁用观察窗内不新增超时事件。
  pass_criteria:
  - 使能计数有效：WDG使能后COUNTER.CURRENT在独立时间间隔内产生与目标计数方向一致的真实变化。
  - 重载配置生效：两组reload_count形成可区分的计数起始/尺度证据，而不是只依赖配置命令返回。
  - 禁用行为正确：显式禁用后STATE.ENABLED为0，且覆盖原剩余超时的观察窗内不产生新的自然WDG事件。
timeout: 5 s
cleanup:
- 运行清理：解锁并禁用本Case使用的WDG，清除本Case产生的IRQ和interrupt record。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: expected_counter_direction
  label: 期望计数方向
  source: oracle
  role: expected
  format: text
- key: enabled_counter_samples
  label: COUNTER.CURRENT实际序列
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P0_003 - WDG独立模式喂狗重载测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P0_003
case_name: WDG独立模式喂狗重载测试
report_feature: |-
  1. WDG重载/当前计数
  2. WDG喂狗/重载
  3. WDG独立/窗口模式
p_level: P0
feature_refs: [WDG_F_003, WDG_F_004, WDG_F_005]
method:
  inputs:
  - 喂狗配置：使用INDEPENDENT模式、复位输出关闭和一个足以完成命令/采样的安全reload_count。
  - 触发位置：选择计数已明显离开重载值但仍远离自然到期的位置执行一次feed，保存feed前实际counter。
  steps:
  - 初始状态清理：禁用WDG、清IRQ/interrupt record并配置独立模式、安全reload和复位输出关闭。
  - 计数进程启动：使能WDG，轮询COUNTER.CURRENT直到进入预定中段区间，并保存feed前实际counter与时间。
  - 单次喂狗触发：执行一次FEED，不自动重试；命令返回只作为动作证据，不作为功能Oracle。
  - 重载结果读取：紧接feed读取COUNTER.CURRENT，确认实际值回到配置reload附近并明显大于feed前剩余值。
  - 原边界继续观察：在feed前剩余超时预算对应的独立时间窗内持续观察IRQ_RAW.WDG/RECORD.INTERRUPT。
  - 延长后自然到期：继续运行直到新重载对应的自然到期边界，确认最终可产生一次自然事件以证明WDG仍在运行。
  - 喂狗状态清理：清自然事件、禁用WDG并复读状态，保存完整counter和事件时间线。
  observations:
  - 喂狗前计数端点：读取COUNTER.CURRENT，保存执行FEED前的真实剩余计数。
  - 喂狗后计数端点：读取COUNTER.CURRENT，期望FEED后重新靠近配置reload尺度且明显高于feed前剩余值。
  - 超时事件端点：读取IRQ_RAW.WDG与RECORD.INTERRUPT，期望原剩余时间内无事件、新重载自然到期后出现事件。
  pass_criteria:
  - 真实重载发生：feed后COUNTER.CURRENT显示重新装载，而不是只以命令成功返回判断。
  - 原超时被延后：feed前剩余时间对应观察窗内不产生自然WDG事件。
  - 新超时仍有效：继续运行到新重载边界后能产生自然事件，证明feed没有停掉WDG。
timeout: 8 s
cleanup:
- 事件清理：禁用WDG，清本Case产生的IRQ和interrupt record，并恢复可重新配置状态。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: expected_reload_count
  label: 期望喂狗重载行为
  source: oracle
  role: expected
  format: text
- key: counter_after_feed
  label: FEED后COUNTER.CURRENT
  source: dut
  role: actual
  format: decimal
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P0_004 - WDG真实超时复位与跨重启取证测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P0_004
case_name: WDG真实超时复位与跨重启取证测试
report_feature: |-
  1. WDG复位输出
  2. WDG复位记录
p_level: P0
feature_refs: [WDG_F_007, WDG_F_014]
method:
  inputs:
  - 复位配置：选择目标实例、独立模式、reset_enable=1与足以让CONFIGURE/ENABLE响应先返回的安全短reload_count。
  - 会话策略：准备expected-reset运行模式；Arm成功后禁止自动重放WDG命令，并记录旧Session generation。
  - 记录基线：Arm前清目标/对照reset record并复读为0，避免把历史复位当成本轮结果。
  steps:
  - 重置前记录清理：在旧Session中禁用并解锁WDG，清目标和对照reset record并复读0。
  - 真实复位武装：配置独立模式、reset输出开启、安全短reload；先清除并使能timeout IRQ源，再使能WDG并确认最后一条Arm响应已经成功返回。
  - 命令发送停止：Arm响应后停止一切WDG业务命令和自动重试，开始独立reset/reconnect deadline。
  - 旧会话失效观测：观察目标连接因DUT reset而中断，保存断线时刻和旧Session generation，禁止继续复用旧Driver对象。
  - 目标重新连接：链路恢复后重新open、HELLO/Discover，并构造新的Session/Driver对象，确认generation已变化。
  - 复位记录读取：在新Session读取目标与对照RECORD.RESET，期望仅本次触发实例的record置位。
  - 复位记录清除：对目标record执行精确clear并复读为0，同时确认对照record没有被错误改变。
  - 跨重启结果汇总：保存disconnect/reconnect时间线、新旧Session身份和record before/after，完成新Session中的WDG禁用清理。
  observations:
  - 会话生命周期证据：保存expected disconnect、reopen成功以及新旧Session generation变化，证明发生真实系统reset而不是模块reset。
  - 复位记录端点：读取RECORD.RESET，期望目标实例从0变1，对照实例保持0。
  - 清除后记录端点：清目标record后复读RECORD.RESET，期望目标回到0且对照不受影响。
  pass_criteria:
  - 真实系统复位：必须出现DUT控制链中断并通过新HELLO/Discover建立新Session；旧Session不可复用。
  - 复位来源归属：重连后只有触发WDG逻辑实例的RECORD.RESET置位。
  - 记录可精确清除：目标reset record清除后复读为0且不修改对照实例。
  - 无自动重放：Arm后的断线恢复过程中不得自动重放ENABLE或其他非幂等WDG命令。
timeout: 30 s
cleanup:
- 跨重启清理：在新Session中禁用目标WDG，清本Case目标reset/interrupt record并确认连接恢复稳定。
resources:
  minimum_level: R5
  full_coverage_level: R5
  board: 控制链必须允许预期DUT Reset后的重新连接
  bench: 需要reset-aware链路恢复与Session重建能力
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: expected_reset_chain
  label: 期望系统Reset与重连链
  source: measurement
  role: expected
  format: text
- key: target_reset_record_after
  label: 目标实例重连后RECORD.RESET
  source: dut
  role: actual
  format: bool
- key: control_reset_record_after
  label: 对照实例重连后RECORD.RESET
  source: dut
  role: actual
  format: bool
- key: target_reset_record_after_clear
  label: 目标实例Clear后RECORD.RESET
  source: dut
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_001 - WDG复位输出关闭与自然中断测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_001
case_name: WDG复位输出关闭与自然中断测试
report_feature: |-
  1. WDG复位输出
  2. WDG IRQ使能/屏蔽/强制/清除与RAW/STATUS
  3. WDG IRQ真实投递
  4. WDG中断记录
p_level: P1
feature_refs: [WDG_F_007, WDG_F_012, WDG_F_013, WDG_F_015]
method:
  inputs:
  - 中断配置：选择独立模式、安全短reload、reset_enable=0，启用并取消屏蔽逻辑WDG IRQ Source。
  - 事件基线：清IRQ Raw/Status、IRQ Service event_count基线与目标interrupt record，并保留目标连接在线状态作为reset反证。
  steps:
  - 自然中断清场：禁用并解锁WDG，关闭reset输出，配置短reload并清实时IRQ和interrupt record。
  - IRQ交付准备：启用逻辑WDG IRQ、取消Mask，读取IRQ_RAW.WDG/IRQ_STATUS.WDG为0并记录Service event_count基线。
  - WDG自然启动：使能WDG后停止feed，不执行IRQ_FORCE或任何软件模拟中断。
  - 自然超时等待：在有界deadline内等待IRQ Service event_count增加，并同步读取IRQ Raw/Status状态。
  - 在线结果读取：确认Target Session仍在线，读取目标RECORD.INTERRUPT和对照实例record。
  - IRQ因果核对：核对Raw、Status、Service latched source/event_count与persistent record均来自同一自然超时窗口。
  - 中断状态清除：清实时IRQ并复读Raw/Status，精确清目标interrupt record并复读为0。
  - 结果汇总：保存自然IRQ时间线、连接存活事实和记录隔离结果，随后禁用WDG。
  observations:
  - 实时IRQ端点：读取IRQ_RAW.WDG与IRQ_STATUS.WDG，期望自然超时后目标Source置位且未屏蔽时二者一致。
  - 真实ISR端点：读取IRQ_DELIVERY.LATCHED_SOURCE和IRQ_DELIVERY.EVENT_COUNT，期望event_count相对基线增加并锁存目标WDG Source。
  - 中断历史端点：读取RECORD.INTERRUPT，期望目标实例置1、未触发对照实例保持0。
  - 在线连接事实：自然事件后Target Session仍可正常查询，证明reset输出关闭时系统没有复位。
  pass_criteria:
  - 自然IRQ真实到达：不使用Force的条件下Raw/Status与真实ISR event_count形成一致因果链。
  - 系统保持在线：reset_enable=0时自然超时后Target Session不发生expected-reset链。
  - 记录归属正确：仅目标实例interrupt record置位并能精确清除。
  - 清除语义有效：清IRQ后Raw/Status回零，清record后目标RECORD.INTERRUPT回零。
timeout: 8 s
cleanup:
- 中断清理：禁用WDG，清实时IRQ和目标interrupt record，恢复reset输出为安全默认状态。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: event_count_delta
  label: 期望自然IRQ链
  source: oracle
  role: expected
  format: text
- key: irq_last_raw
  label: 实际WDG IRQ快照
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_002 - WDG窗口喂狗区域测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_002
case_name: WDG窗口喂狗区域测试
report_feature: |-
  1. WDG喂狗/重载
  2. WDG独立/窗口模式
  3. WDG窗口门限
  4. WDG IRQ真实投递
p_level: P1
feature_refs: [WDG_F_004, WDG_F_005, WDG_F_006, WDG_F_013]
method:
  inputs:
  - 窗口配置：三个区域使用相同短Reload和各自可达的Low/High，均显式选择SAME_ROUND_IRQ_RESET。
  - 窗口矩阵：覆盖counter>high时的Early Feed、low<=counter<=high时的Inside Feed，以及counter越过low后的Late超时与无效Feed。
  - 状态隔离：从Capability与Runtime交集中选择两个实例；主实例执行Inside/Early，第二实例独立执行Late，避免复用已形成的违规状态。
  - 事件策略：关闭reset输出，以真实TIMEOUT IRQ观察Early Feed和Late越过Low，不把软件Force当作窗口事件。
  steps:
  - 能力确认：确认至少两个实例共同提供窗口模式、门限、Feed、Counter读回和自然IRQ投递能力。
  - IRQ会话清场：关闭reset输出，清除实时IRQ和interrupt record，再Enable并Unmask TIMEOUT Source。
  - Inside阶段：主实例在独立模式装载Reload，切入可稳定定位的中段窗口；等待Counter进入门限中部后执行合法Feed。
  - Early阶段：主实例在干净状态重新装载Reload，配置High低于初始Counter，读取实际Counter后执行非法Feed。
  - Late阶段：第二实例独立装载Reload，将Low配置在Reload下方少量计数处；先等待实际Counter低于Low并确认真实IRQ，再执行Feed并记录Counter。
  - 区域矩阵汇总：保存三个样本的阈值、Feed前后Counter与Event Count增量，并恢复禁用状态。
  observations:
  - Feed位置端点：读取Feed前COUNTER.CURRENT并与low/high比较，证明样本实际位于Early/Inside/Late区域。
  - Reload结果端点：读取Feed后COUNTER.CURRENT，只有Inside样本应回到Reload尺度。
  - 窗口事件端点：Early Feed和Late越过Low各形成至少一次真实ISR交付，Inside Feed不产生窗口事件；Level型违规源允许重复投递。
  pass_criteria:
  - Inside合法性：low<=counter<=high时Feed真实重载且Event Count不增加。
  - Early/Late语义：Early Feed产生真实IRQ；Late越过Low产生真实IRQ，后续Feed结果只记录为硬件事实，不附加未被公共契约定义的重载断言。
  - 样本可复现：三个Feed时刻均由实际COUNTER.CURRENT定位，不依赖固定sleep估算。
timeout: 15 s
cleanup:
- 窗口清理：禁用WDG，关闭并清除IRQ Source，清除interrupt record。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要两个可访问的逻辑WDG实例，不需要外连线
  bench: 无外部仪器
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: early_counter_before
  label: Early Feed前COUNTER.CURRENT
  source: dut
  role: actual
  format: decimal
- key: inside_counter_before
  label: Inside Feed前COUNTER.CURRENT
  source: dut
  role: actual
  format: decimal
- key: inside_counter_after
  label: Inside Feed后COUNTER.CURRENT
  source: dut
  role: actual
  format: decimal
- key: late_counter_before
  label: Late Feed前COUNTER.CURRENT
  source: dut
  role: actual
  format: decimal
- key: irq_event_deltas
  label: Early/Inside/Late IRQ事件增量
  source: measurement
  role: actual
  format: text
gap:
- wdg_exact_boundary_atomic_feed_gap
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_003 - WDG轮次工作模式测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_003
case_name: WDG轮次工作模式测试
report_feature: |-
  1. WDG复位输出
  2. WDG IRQ/Reset轮次模式
  3. WDG IRQ真实投递
  4. WDG复位记录
p_level: P1
feature_refs: [WDG_F_007, WDG_F_008, WDG_F_013, WDG_F_014]
method:
  inputs:
  - 模式矩阵：参数化ROUND1_IRQ_ROUND2_RESET与SAME_ROUND_IRQ_RESET，两模式均启用自然IRQ和系统reset输出。
  - 记录策略：每模式Arm前清实时IRQ、interrupt record和reset record；同轮模式不要求普通ISR一定在reset前运行。
  - 会话策略：需要系统reset的阶段使用expected-reset生命周期，不自动重放非幂等WDG命令。
  steps:
  - 模式基线清理：禁用WDG并清实时IRQ、目标interrupt/reset record，记录旧Session generation。
  - 首轮次轮模式武装：配置ROUND1_IRQ_ROUND2_RESET、安全reload、IRQ与reset输出，使能后停止feed。
  - 第一轮IRQ取证：等待第一轮自然超时，要求系统保持在线并读取Raw/Status、真实ISR event_count和interrupt record。
  - 同轮模式重新武装：同Session清全部目标事件记录，配置SAME_ROUND_IRQ_RESET并再次武装自然超时。
  - 同轮Reset等待：等待第一次自然到期和expected disconnect；不把“普通ISR一定先执行”作为通过前提。
  - 同轮持久证据读取：重连后读取interrupt record与reset record，期望同一轮事件留下两类持久来源证据。
  - 模式时序汇总：汇总两种模式的首个事件轮次、在线阶段、reset阶段和records，最后恢复WDG禁用。
  observations:
  - 首轮IRQ端点：ROUND1_IRQ_ROUND2_RESET第一轮读取IRQ Raw/Status、真实Delivery和RECORD.INTERRUPT，期望系统仍在线。
  - 同轮Reset端点：SAME_ROUND_IRQ_RESET通过disconnect/reconnect与RECORD.RESET证明真实系统reset。
  - 同轮持久记录端点：重连后读取RECORD.INTERRUPT和RECORD.RESET，期望两者均反映本轮事件。
  - 模式0复位边界：本FPGA上ROUND1_IRQ_ROUND2_RESET未观测到第二轮复位，该模式只取证第一轮在线IRQ，不作为复位已通过的证据。
  pass_criteria:
  - 模式0第一轮正确：只形成在线IRQ证据与interrupt record，不出现reset record。
  - 同轮事件正确：模式1第一次自然到期即形成reset，且重连后interrupt/reset两类持久记录均符合本轮事件。
  - ISR要求不过强：模式1不得以普通ISR在reset前必然执行作为必要判据，避免把reset抢占ISR误判为失败。
  - 记录来源可清：两种模式产生的目标records均可精确清除并复读为0。
timeout: 30 s
cleanup:
- 跨重启清理：确保最终处于新Session在线状态，禁用WDG并清实时IRQ和目标records。
resources:
  minimum_level: R0
  full_coverage_level: R5
  board: 控制链必须允许预期DUT Reset后的重新连接
  bench: 完整覆盖需要reset-aware会话重建
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: expected_sequence
  label: 期望WDG轮次事件序列
  source: measurement
  role: expected
  format: text
- key: first_round_event_count_delta
  label: 首轮IRQ实际投递次数增量
  source: measurement
  role: actual
  format: decimal
- key: round1_irq_last_raw
  label: 首轮IRQ实际Raw
  source: dut
  role: actual
  format: hex32
- key: round1_interrupt_record
  label: 首轮中断记录
  source: dut
  role: actual
  format: bool
- key: round1_reset_record
  label: 首轮复位记录（期望为0）
  source: dut
  role: actual
  format: bool
- key: same_round_interrupt_record
  label: 同轮中断实际记录
  source: dut
  role: actual
  format: bool
- key: same_round_reset_record
  label: 同轮Reset实际记录
  source: dut
  role: actual
  format: bool
- key: cleared_interrupt_record
  label: 清除后中断记录
  source: dut
  role: actual
  format: bool
- key: cleared_reset_record
  label: 清除后复位记录
  source: dut
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_004 - WDG模块复位与恢复测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_004
case_name: WDG模块复位与恢复测试
report_feature: |-
  1. WDG模块复位/恢复
p_level: P1
feature_refs: [WDG_F_011]
method:
  inputs:
  - 模块状态：先把目标WDG置于明显非默认状态，包括安全reload、独立模式、reset输出关闭并进入计数。
  - 恢复配置：准备第二组可区分安全配置，模块reset后用于证明重新配置/运行能力。
  steps:
  - 非默认状态建立：解锁并禁用WDG，配置第一组非默认参数，使能并读取STATE.ENABLED/COUNTER.CURRENT证明正在运行。
  - 模块复位执行：调用稳定MODULE_RESET动作一次，不自动重试，并等待其有界返回。
  - 模块状态读取：读取STATE.ENABLED、COUNTER.CURRENT和可获得配置readback，确认旧运行事务已经停止/回到目标复位态。
  - 第二组重新配置：重新解锁、写第二组安全配置并使能WDG，读取当前计数证明新配置能够开始运行。
  - 恢复状态复读：再次读取STATE.ENABLED与COUNTER.CURRENT，确认恢复后的运行状态来自硬件端点。
  - 结果与清理汇总：保存reset前、reset后和重新运行三阶段状态，最后禁用目标WDG。
  observations:
  - 模块状态端点：读取STATE.ENABLED/COUNTER.CURRENT及可用readback，证明旧运行事务被模块reset终止。
  - 恢复计数端点：第二组配置使能后读取COUNTER.CURRENT，期望重新进入正常计数过程。
  pass_criteria:
  - 旧事务被清理：模块reset后旧WDG运行状态不继续残留。
  - 模块可恢复运行：第二组配置可重新使能并产生有效计数。
timeout: 8 s
cleanup:
- 模块清理：确保目标WDG处于禁用可配置状态，清本Case相关IRQ和record。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: enabled_states
  label: 期望模块复位作用域
  source: oracle
  role: expected
  format: text
- key: recovered_counter
  label: MODULE_RESET后实际状态
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_005 - WDG配置写保护与解锁测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_005
case_name: WDG配置写保护与解锁测试
report_feature: |-
  1. WDG配置锁定/解锁
p_level: P1
feature_refs: [WDG_F_010]
method:
  inputs:
  - 配置对照：准备可明确区分的配置A/B，至少让reload或模式字段不同且两组均合法安全。
  - 状态前提：整个写保护验证在WDG禁用态完成，避免运行态配置限制与lock效果混淆。
  steps:
  - 初始解锁配置：禁用并UNLOCK，写配置A并读取CONFIG.READBACK，确认A已成为当前实际配置。
  - 写保护进入：执行LOCK，再读取CONFIG.READBACK确认进入保护后配置仍为A。
  - 锁定写入尝试：在LOCK状态尝试CONFIGURE配置B，保存动作状态并禁止服务层伪造成功接受结果。
  - 锁定后实际复读：读取CONFIG.READBACK，期望实际配置仍为A；若Wire返回accepted readback也必须等于A。
  - 重新解锁：执行UNLOCK并确认后续配置路径重新可写。
  - 解锁后配置B：再次CONFIGURE配置B并读取CONFIG.READBACK，期望实际配置切换为B。
  - 写保护结果汇总：保存A、锁定写B、解锁写B三阶段readback和动作结果，并恢复可配置状态。
  observations:
  - 配置A实际读回：读取CONFIG.READBACK，期望初始UNLOCK写入后与A稳定语义一致。
  - 锁定后实际读回：LOCK状态尝试B后读取CONFIG.READBACK，期望仍为A且服务层不得报告B已被接受。
  - 解锁后实际读回：UNLOCK后再次写B并读取CONFIG.READBACK，期望实际配置变为B。
  pass_criteria:
  - 写保护有效：LOCK期间对受保护配置的修改不实际生效。
  - 无静默假成功：锁定写入不能返回与实际readback矛盾的成功accepted configuration。
  - 解锁恢复有效：UNLOCK后配置B能够真实readback。
timeout: 5 s
cleanup:
- 配置清理：UNLOCK并禁用WDG，恢复安全配置和中断状态。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: reload_readbacks
  label: CONFIG.READBACK实际值
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_006 - WDG中断控制矩阵测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_006
case_name: WDG中断控制矩阵测试
report_feature: |-
  1. WDG IRQ使能/屏蔽/强制/清除与RAW/STATUS
  2. WDG IRQ真实投递
p_level: P1
feature_refs: [WDG_F_012, WDG_F_013]
method:
  inputs:
  - IRQ矩阵：参数化Enable/Disable、Mask/Unmask、Force和Clear；复位输出关闭并使用足够长reload隔离自然超时。
  - 交付基线：每个子阶段清Raw/Status并记录IRQ Service event_count，Force只作为控制路径刺激。
  steps:
  - IRQ状态清场：禁用WDG自然计数影响或配置足够长reload，清IRQ并记录Raw/Status/EventCount全零基线。
  - 未屏蔽Force验证：Enable且Unmask后执行一次IRQ_FORCE，读取IRQ_RAW.WDG、IRQ_STATUS.WDG和真实Delivery增量。
  - Force清除验证：执行IRQ_CLEAR并复读Raw/Status回零，记录EventCount不会因Clear再次增加。
  - Mask状态Force验证：保持Enable但Mask后Force，期望Raw置位、Status被抑制且Delivery EventCount不增加。
  - Unmask语义复核：对Mask期间pending Raw执行Unmask，按Chip Adaptation冻结的pending语义观察Status/Delivery，再清状态。
  - Disable状态Force验证：Disable IRQ Source后执行Force，记录Raw是否产生并确认有效Delivery符合Enable语义。
  - 重复Clear隔离：在各控制状态后执行精确Clear并确认Raw/Status不残留、不额外投递ISR。
  - IRQ矩阵汇总：汇总Enable/Mask/Force/Clear组合的Raw、Status、latched source与event_count，恢复禁用/清零状态。
  observations:
  - Raw中断端点：读取IRQ_RAW.WDG，证明Force刺激是否进入Mask前Source pending。
  - 有效中断端点：读取IRQ_STATUS.WDG，证明Enable/Mask对有效Source的独立控制。
  - 真实ISR端点：读取IRQ_DELIVERY.LATCHED_SOURCE与IRQ_DELIVERY.EVENT_COUNT，证明只有有效交付条件下产生真实ISR。
  - 清除后端点：IRQ_CLEAR后复读Raw/Status，期望目标Source回零且Clear本身不新增Delivery。
  pass_criteria:
  - Force控制正确：Unmask+Enable时Force形成Raw、Status和一次真实Delivery。
  - Mask分层正确：Mask不抹除Raw事实，但抑制有效Status和新的真实Delivery。
  - Enable语义独立：Disable状态不得产生有效ISR交付；Raw行为按Chip冻结语义记录。
  - Clear精确有效：Clear后Raw/Status归零且不产生额外event_count。
timeout: 8 s
cleanup:
- IRQ清理：清Raw/Status，Disable并Unmask到安全状态，禁用WDG计数并清本Caserecord。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: delivery_count_delta
  label: 期望IRQ控制状态
  source: oracle
  role: expected
  format: text
- key: masked_raw
  label: Mask阶段实际IRQ_RAW
  source: dut
  role: actual
  format: hex32
- key: masked_status
  label: Mask阶段实际IRQ_STATUS
  source: dut
  role: actual
  format: hex32
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_007 - WDG自然中断与中断记录测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_007
case_name: WDG自然中断与中断记录测试
report_feature: |-
  1. WDG IRQ真实投递
  2. WDG中断记录
p_level: P1
feature_refs: [WDG_F_013, WDG_F_015]
method:
  inputs:
  - 目标实例：选择一个Capability声明存在的WDG逻辑实例并关闭reset输出。
  - 记录基线：清目标interrupt record并复读0，清目标实时IRQ并记录Service event_count基线。
  steps:
  - 记录清场：禁用目标WDG，清RECORD.INTERRUPT并确认基线为0。
  - 目标IRQ武装：只为目标实例配置独立模式、短reload、自然IRQ Enable+Unmask和reset输出关闭。
  - 自然超时触发：只使能目标WDG并停止feed，不对任一实例使用Force。
  - 真实ISR等待：等待目标IRQ Service event_count增加，读取目标Raw/Status并保存latched source。
  - 记录读取：读取目标RECORD.INTERRUPT，期望自然超时后置位。
  - 记录精确清除：Clear目标interrupt record并复读为0。
  - 证据汇总：保存事件前、事件后和清除后的记录序列，随后禁用目标实例。
  observations:
  - 目标ISR端点：读取目标IRQ Raw/Status和真实Delivery，证明interrupt record对应自然WDG IRQ而非手工写记录位。
  - 记录端点：读取目标RECORD.INTERRUPT，期望自然事件后置位。
  - 精确清除端点：目标record Clear后复读为0。
  pass_criteria:
  - 自然中断成立：目标实例自然超时形成Raw/Status与真实ISR交付。
  - 记录因果正确：自然超时前记录为0，事件后置位。
  - 记录精确清除：清除目标record后可以复读为0。
timeout: 10 s
cleanup:
- 实例清理：禁用本Case使用的全部WDG，清各自实时IRQ和interrupt record。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 无额外要求
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: interrupt_record_sequence
  label: 实际实例中断记录
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P1_008 - WDG多实例隔离测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_008
case_name: WDG多实例隔离测试
report_feature: |-
  1. WDG 多实例隔离
p_level: P1
feature_refs: [WDG_F_016]
method:
  inputs:
  - 实例矩阵：至少选择两个逻辑WDG实例，分别配置可区分的reload/模式并关闭reset输出。
  - 隔离刺激：只使能实例A，并只对实例A软件Force一个已使能且未屏蔽的IRQ事件；实例B保持禁用对照状态。
  steps:
  - 多实例清场：禁用两个实例，清各自IRQ与interrupt record，并分别写入可区分安全配置A/B。
  - 配置隔离读回：读取两实例CONFIG.READBACK或等价稳定配置事实，确认A/B映射到正确逻辑实例。
  - 仅运行实例A：只使能A并读取A/B STATE.ENABLED，期望A运行而B保持禁用。
  - A实例IRQ刺激：记录A/B事件计数基线，只对A执行IRQ Force并等待A的真实ISR投递。
  - B实例复读：读取B的Raw和Event Count，确认A的刺激未进入B实例。
  - 隔离矩阵汇总：保存A/B配置、使能状态和IRQ计数，确认逻辑实例路由无交叉。
  observations:
  - 双实例配置端点：读取A/B CONFIG.RELOAD，期望保持各自配置值。
  - 双实例使能端点：读取A/B STATE.ENABLED，期望只有A处于使能状态。
  - 双实例IRQ端点：读取A/B Delivery与B的Raw，期望Force事件只属于A。
  pass_criteria:
  - 配置与使能隔离：A/B配置读回互不覆盖，只有A处于运行状态。
  - IRQ交付隔离：A实例Force事件不得造成B实例Raw或Event Count变化。
timeout: 15 s
cleanup:
- 多实例清理：禁用两实例并清各自IRQ状态。
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要至少两个逻辑WDG实例
  bench: 无额外要求
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: primary_reload_count
  label: Primary实例Reload读回
  source: dut
  role: actual
  format: decimal
- key: secondary_reload_count
  label: Secondary实例Reload读回
  source: dut
  role: actual
  format: decimal
- key: primary_enabled_state
  label: Primary实例使能状态
  source: dut
  role: actual
  format: bool
- key: secondary_enabled_state
  label: Secondary实例使能状态
  source: dut
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->


### WDG_P1_009 - WDG窗口超时系统复位测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P1_009
case_name: WDG窗口超时系统复位测试
report_feature: |-
  1. WDG窗口门限
  2. WDG复位输出
  3. WDG复位记录
p_level: P1
feature_refs: [WDG_F_006, WDG_F_007, WDG_F_014]
method:
  inputs:
  - 窗口配置：目标实例使用窗口模式，Low贴近Reload、High低于初始Counter，并开启reset输出与自然IRQ。
  - 对照实例：第二个实例保持禁用，用于证明复位来源只归属于目标实例。
  - 触发路径：越过Low后不Feed，让硬件自然形成窗口超时；不使用软件Force替代自然事件。
  steps:
  - 复位记录清场：禁用两个实例，清目标与对照reset/interrupt record并复读为0。
  - 窗口武装：配置窗口模式、Low/High门限、reset输出开启与安全短Reload；先清并使能timeout IRQ源。
  - 自然超时等待：使能目标实例后停止一切WDG业务命令，等待窗口超时形成真实系统复位。
  - 旧会话失效观测：观察控制链因DUT reset而中断，保存断线时刻与旧Session generation。
  - 目标重新连接：链路恢复后重新open与HELLO/Discover，确认Session已更新。
  - 复位记录读取：在新Session读取目标与对照RECORD.RESET，期望仅目标实例置位。
  - 复位记录清除：对目标record执行精确clear并复读为0，确认对照未被改变。
  observations:
  - 会话生命周期端点：保存expected disconnect与重连后的Session身份变化，证明发生真实系统reset。
  - 复位记录端点：读取RECORD.RESET，期望目标实例从0变1，对照实例保持0。
  - 清除后记录端点：清目标record后复读RECORD.RESET，期望目标回到0且对照不受影响。
  pass_criteria:
  - 窗口超时真实复位：越过Low后不Feed必须出现控制链中断，并由新HELLO/Discover建立新Session。
  - 复位来源归属：重连后只有配置窗口模式的实例RECORD.RESET置位，对照实例保持0。
  - 记录可精确清除：目标record清除后复读为0且不改变对照实例。
timeout: 30 s
cleanup:
- 跨重启清理：在新Session中禁用目标WDG，清目标reset/interrupt record并确认连接稳定。
resources:
  minimum_level: R0
  full_coverage_level: R5
  board: 需要两个可访问的逻辑WDG实例，控制链必须允许复位后重新连接
  bench: 完整覆盖需要reset-aware会话重建
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: expected_window_reset_chain
  label: 期望窗口超时复位与重连链
  source: measurement
  role: expected
  format: text
- key: target_window_low
  label: 目标窗口Low门限
  source: measurement
  role: actual
  format: decimal
- key: target_reset_record_after
  label: 目标实例重连后RECORD.RESET
  source: dut
  role: actual
  format: bool
- key: control_reset_record_after
  label: 对照实例重连后RECORD.RESET
  source: dut
  role: actual
  format: bool
- key: target_reset_record_after_clear
  label: 目标实例Clear后RECORD.RESET
  source: dut
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P2_001 - WDG时钟源与分频集成测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P2_001
case_name: WDG时钟源与分频集成测试
report_feature: |-
  1. WDG重载/当前计数
  2. WDG时钟源/分频
p_level: P2
feature_refs: [WDG_F_003, WDG_F_017]
method:
  inputs:
  - 时基节点：由CRG Owner提供APB1 divider=0和divider=1两个安全时基配置。
  - WDG配置：两轮使用相同reload、INDEPENDENT模式和关闭reset输出的配置。
  - 独立时间：使用PC单调时钟作为独立时间参考；每个Divider交错采样四轮并使用中位速率，不把CRG自报频率作为唯一Oracle。
  steps:
  - 原配置保存：禁用WDG并由CRG Owner读取进入Case前的时钟源和分频。
  - 采样基线清理：解锁并禁用目标WDG，关闭并清除本Case使用的超时IRQ，避免历史事件影响计数窗口。
  - 交错节点采样：按0/1、1/0的交错顺序切换APB1 Divider，每个节点配置相同reload并在固定PC时间窗口采样Counter两点。
  - 多轮速率计算：每个Divider采样四轮，逐轮计算Counter delta/PC elapsed，再计算两组中位递减速率和divider=0/divider=1速率比。
  - 证据汇总：记录每轮CRG读回、Counter采样点、时间窗、单轮速率、中位速率和速率比。
  - 原配置恢复：禁用WDG并由CRG Owner恢复进入Case前的时钟配置。
  observations:
  - Counter速率：记录每个Divider四轮COUNTER.CURRENT起止值、delta、PC elapsed和中位速率。
  - CRG读回：记录每轮CRG Owner实际读回的Source和Divider。
  pass_criteria:
  - CRG配置：每轮读回均与本轮APB1/Divider配置一致。
  - Counter速率：全部delta均为正；divider=0与divider=1的中位实际递减速率比不低于1.5，证明配置产生了可区分的/1与/2硬件效果，而不是采样噪声造成的方向偶然变化。
  - Owner边界：所有跨IP时基动作均由CRG Owner执行，WDG Service不操作CRG寄存器。
timeout: 20 s
cleanup:
- 时基清理：禁用WDG，由CRG Owner恢复原时钟Source/Divider并清本CaseWDG事件。
resources:
  minimum_level: R2
  full_coverage_level: R2
  board: 无额外要求
  bench: 需要片内CRG Owner与PC单调时间
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: crg_clock_source_samples
  label: 两阶段CRG WDG时钟源读回
  source: dut
  role: actual
  format: text
  semantic_ref: wdg.parameter.crg_clock_readback
- key: crg_clock_divider_samples
  label: 两阶段CRG WDG分频读回
  source: dut
  role: actual
  format: text
- key: counter_samples_divider_zero
  label: Divider0下COUNTER.CURRENT原始值
  source: dut
  role: actual
  format: text
- key: counter_samples_divider_one
  label: Divider1下COUNTER.CURRENT原始值
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P2_002 - WDG超时NMI路由与处理域隔离测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P2_002
case_name: WDG超时NMI路由与处理域隔离测试
report_feature: |-
  1. WDG超时NMI路由
p_level: P2
feature_refs:
- WDG_F_018
method:
  inputs:
  - NMI源掩码：CPU Owner发布当前源掩码；Case只使用公共mask语义，不猜测Source bit。
  - 自然超时：关闭系统reset输出，使用安全Reload并停止feed，产生自然WDG超时。
  - 双证据计数：CPU Owner记录NMI_Handler事件计数，WDG Service独立记录timeout IRQ；CPU Owner在首次交付后自动全屏蔽。
  steps:
  - 基线清理：禁用WDG并清WDG IRQ/record，CPU Owner清零NMI_Handler事件计数。
  - NMI配置：CPU Owner配置mask=0（所有已发布源不屏蔽），WDG Service只配置自身timeout IRQ。
  - WDG激励：配置独立模式和安全Reload，使能WDG后停止feed。
  - 双端等待：分别等待CPU NMI事件计数和WDG timeout IRQ事件计数增加。
  - 快照读取：读取CPU NMI raw/masked/mask/status和WDG IRQ快照，不以WDG ACK代替NMI证据。
  - 恢复清理：禁用WDG、清WDG事件，由CPU Owner恢复全屏蔽状态。
  observations:
  - WDG自然事件：读取IRQ event_count和last_raw。
  - CPU NMI交付：读取CPU Owner的NMI_Handler event_count及NMI源/状态字段，Mask应在首次交付后等于支持Source全集。
  pass_criteria:
  - NMI真实交付：CPU NMI_Handler事件计数相对基线增加。
  - WDG自然超时：timeout IRQ事件计数相对基线增加。
  - 有界投递：首次NMI后CPU NMI Mask等于Runtime发布的Source全集，WDG IRQ结果仍可通过协议读取。
timeout: 10 s
cleanup:
- 跨IP清理：禁用WDG并清本CaseWDG事件，由CPU Owner恢复NMI mask。
resources:
  minimum_level: R2
  full_coverage_level: R2
  board: 当前固件CPU Owner实例
  bench: 不需要外部仪器；需要CPU Owner和WDG Service同时在线
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
failure_observations:
- key: cpu_nmi_mask
  label: CPU首次NMI后的Source Mask
  source: dut
  role: actual
  format: hex32
  semantic_ref: cpu.interrupt.nmi_mask
- key: wdg_irq_raw
  label: WDG自然timeout IRQ Raw状态
  source: dut
  role: actual
  format: hex32
  semantic_ref: wdg.interrupt.irq_raw
- key: expected_nmi_chain
  label: 期望WDG自然timeout到CPU NMI链路
  source: measurement
  role: expected
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

### WDG_P3_001 - WDG调试Halt行为测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: WDG_P3_001
case_name: WDG调试Halt行为测试
report_feature: |-
  1. WDG Debug Halt行为
p_level: P3
feature_refs: [WDG_F_009]
method:
  inputs:
  - 调试矩阵：同一安全reload下参数化halt_pause_enable开启/关闭，两轮均使用真实Debugger Halt/Resume。
  - 时间设计：Halt持续时间必须超过进入Halt前的剩余超时预算，并保存独立Debugger时间线。
  - 复位策略：暂停失能轮可关闭复位输出用自然IRQ在线证明继续计数；需要完整reset结论时使用reset-aware恢复链。
  steps:
  - 调试前清场：禁用并解锁WDG，清IRQ/record，配置安全reload并读取进入运行前的计数与事件基线。
  - 暂停使能武装：设置halt_pause_enable后使能WDG，运行到中间计数并记录Halt前COUNTER.CURRENT。
  - 真实Halt保持：由Debugger控制CPU进入Halt并保持超过原剩余超时预算，禁止用软件sleep或busy-loop代替。
  - 暂停使能恢复：Debugger Resume后立即读取COUNTER.CURRENT与IRQ/record，确认Halt期间未消耗完整超时预算。
  - 暂停失能重配：清场后关闭halt_pause_enable，使用同一reload重新运行到可比较的Halt前计数。
  - 继续计数Halt：再次真实Halt同等时长，观察WDG在CPU停止执行时继续推进并形成自然事件或预期reset。
  - 恢复与事件取证：Resume或reset-aware重连后读取counter、IRQ/record和必要reset record，证明两种配置行为可区分。
  - 调试矩阵汇总：保存两轮Halt/Resume时间线、计数和事件证据，恢复Debugger运行态并禁用WDG。
  observations:
  - Halt计数端点：两种配置分别读取Halt前后COUNTER.CURRENT，期望暂停使能时冻结/近似冻结，暂停失能时持续推进。
  - 自然事件端点：暂停使能轮不得因Halt本身到期；暂停失能轮在超过剩余预算时应形成自然IRQ或reset证据。
  - Debugger时间线证据：保存真实Halt/Resume时刻和持续区间，证明刺激来自Debugger而不是软件等待。
  pass_criteria:
  - 暂停语义可区分：halt_pause_enable开启与关闭在相同Halt窗口下表现出不同的WDG计数/超时行为。
  - 真实调试刺激：所有Halt结论必须由Debugger Halt/Resume形成，软件delay、WFI或busy-loop均不能替代。
  - 暂停开启正确：超过原剩余超时预算的Halt期间不产生本轮WDG超时。
  - 暂停关闭正确：相同Halt条件下WDG继续计数，并在足够长窗口内形成与自然超时一致的硬件证据。
timeout: 30 s
cleanup:
- 调试清理：确保Debugger Resume，禁用WDG并清IRQ/record；若发生reset则通过新Session完成清理。
resources:
  minimum_level: R5
  full_coverage_level: R5
  board: 需要可编程Debugger控制
  bench: 需要真实Debugger Halt/Resume；完整reset路径还需reset-aware恢复
backend:
- FPGA
- Silicon
evidence:
- 决定性硬件Observation、独立Expected/Measurement与绑定结构化Artifact
attachments:
- Debugger命令文件、stdout与stderr原始日志，按参数节点分别绑定到本execution
failure_observations:
- key: expected_halt_behavior
  label: 期望Halt计数行为
  source: measurement
  role: expected
  format: text
- key: pause_enabled_counter_samples
  label: Halt暂停使能时COUNTER.CURRENT前后值
  source: dut
  role: actual
  format: text
- key: pause_disabled_counter_samples
  label: Halt暂停失能时COUNTER.CURRENT前后值
  source: dut
  role: actual
  format: text
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  WDG_P0_002:
    summary: "WDG使能后计数递减，禁用后状态关闭，两组Reload配置可区分。"
    fields:
      - {source: measurement, path: expected_counter_direction, label: 期望计数方向, format: text, aggregate: same}
      - {source: observation, path: enabled_counter_samples, label: 使能阶段COUNTER.CURRENT, format: text, aggregate: distinct}
      - {source: observation, path: disabled_state, label: 禁用后STATE.ENABLED, format: bool, aggregate: same}
      - {source: observation, path: irq_raw, label: 安全窗口IRQ Raw, format: hex32, aggregate: same}
  WDG_P0_003:
    summary: "WDG独立模式Feed使Counter重载，新周期边界仍能自然产生Timeout。"
    fields:
      - {source: measurement, path: expected_reload_count, label: 配置Reload, format: decimal, aggregate: same}
      - {source: observation, path: counter_before_feed, label: Feed前COUNTER.CURRENT, format: decimal, aggregate: same}
      - {source: observation, path: counter_after_feed, label: Feed后COUNTER.CURRENT, format: decimal, aggregate: same}
      - {source: observation, path: interrupt_record, label: 自然Timeout中断记录, format: bool, aggregate: same}
  WDG_P1_001:
    summary: "WDG关闭Reset输出后自然Timeout产生真实IRQ投递和持久中断记录。"
    fields:
      - {source: measurement, path: event_count_delta, label: 自然Timeout事件增量, format: decimal, aggregate: same}
      - {source: observation, path: irq_last_raw, label: 自然Timeout最后Raw状态, format: hex32, aggregate: same}
      - {source: observation, path: interrupt_record, label: 持久中断记录RECORD.INTERRUPT, format: bool, aggregate: same}
  WDG_P1_002:
    summary: "WDG窗口内Feed合法重载Counter，Early Feed与Late越过Low分别产生真实窗口IRQ。"
    fields:
      - {source: artifact, path: counter_before_feed, label: 三个区域Feed前Counter, format: text, aggregate: distinct}
      - {source: artifact, path: counter_after_feed, label: 三个区域Feed后Counter, format: text, aggregate: distinct}
      - {source: artifact, path: event_count_delta, label: 三个区域IRQ事件增量, format: text, aggregate: distinct}
  WDG_P1_004:
    summary: "WDG模块复位清除运行状态，复位后可重新配置并恢复计数。"
    fields:
      - {source: observation, path: enabled_states, label: 复位前后使能状态, format: text, aggregate: distinct}
      - {source: observation, path: recovered_counter, label: 恢复后COUNTER.CURRENT, format: decimal, aggregate: same}
  WDG_P1_005:
    summary: "WDG Lock阶段拒绝配置修改，Unlock后新配置可读回。"
    fields:
      - {source: observation, path: reload_readbacks, label: Lock/Unlock配置读回, format: text, aggregate: distinct}
  WDG_P1_006:
    summary: "WDG IRQ在Mask、Unmask和Disable阶段分别保持Raw、真实投递和抑制语义。"
    fields:
      - {source: observation, path: masked_raw, label: Mask阶段IRQ_RAW, format: hex32, aggregate: distinct}
      - {source: observation, path: masked_status, label: Mask阶段IRQ_STATUS, format: hex32, aggregate: distinct}
      - {source: measurement, path: delivery_count_delta, label: Unmask投递增量, format: decimal, aggregate: same}
      - {source: measurement, path: disabled_count_delta, label: Disable投递增量, format: decimal, aggregate: same}
  WDG_P1_007:
    summary: "WDG自然Timeout置位持久中断记录，精确Clear后记录恢复。"
    fields:
      - {source: observation, path: interrupt_record_sequence, label: 中断记录变化序列, format: text, aggregate: distinct}
  WDG_P1_008:
    summary: "两个WDG实例的Reload、使能状态和IRQ投递保持独立。"
    fields:
      - {source: observation, path: primary_reload_count, label: Primary实例Reload读回, format: decimal, aggregate: same}
      - {source: observation, path: secondary_reload_count, label: Secondary实例Reload读回, format: decimal, aggregate: same}
      - {source: observation, path: primary_enabled_state, label: Primary实例使能状态, format: bool, aggregate: same}
      - {source: observation, path: secondary_enabled_state, label: Secondary实例使能状态, format: bool, aggregate: same}
  WDG_P1_009:
    summary: "窗口模式越过Low且不Feed时形成真实系统复位，重连后仅目标实例reset record置位并可清除。"
    fields:
      - {source: measurement, path: expected_window_reset_chain, label: 期望窗口复位链, format: text, aggregate: distinct}
      - {source: observation, path: target_window_low, label: 目标窗口Low门限, format: decimal, aggregate: same}
      - {source: observation, path: target_reset_record_after, label: 目标重连后Reset记录, format: bool, aggregate: same}
      - {source: observation, path: target_reset_record_after_clear, label: 目标清除后Reset记录, format: bool, aggregate: same}
  WDG_P0_004:
    summary: "WDG真实复位使旧Session失效，重连后目标reset record置位且可精确清除。"
    fields:
      - {source: measurement, path: expected_reset_chain, label: 预期复位Session链, format: text, aggregate: distinct}
      - {source: observation, path: target_reset_record_after, label: 目标实例重连后RECORD.RESET, format: bool, aggregate: same}
      - {source: observation, path: control_reset_record_after, label: 对照实例重连后RECORD.RESET, format: bool, aggregate: same}
      - {source: observation, path: target_reset_record_after_clear, label: 目标实例Clear后RECORD.RESET, format: bool, aggregate: same}
  WDG_P1_003:
    summary: "WDG两种IRQ/Reset轮次模式分别形成首轮在线IRQ与同轮IRQ加真实系统复位证据。"
    fields:
      - {source: measurement, path: expected_sequence, label: 期望轮次序列, format: text, aggregate: distinct}
      - {source: observation, path: round1_irq_last_raw, label: 首轮IRQ Raw, format: hex32, aggregate: same}
      - {source: observation, path: round1_interrupt_record, label: 首轮中断记录, format: bool, aggregate: same}
      - {source: observation, path: same_round_reset_record, label: 同轮Reset记录, format: bool, aggregate: same}
  WDG_P3_001:
    summary: "真实Debugger Halt下WDG暂停使能与失能产生可区分的计数和IRQ结果。"
    fields:
      - {source: measurement, path: expected_halt_behavior, label: 期望Halt行为, format: text, aggregate: distinct}
      - {source: observation, path: pause_enabled_counter_samples, label: Halt暂停使能时COUNTER.CURRENT, format: text, aggregate: distinct}
      - {source: observation, path: pause_disabled_counter_samples, label: Halt暂停失能时COUNTER.CURRENT, format: text, aggregate: distinct}
  WDG_P2_001:
    summary: "读取CRG时钟源与分频配置，并比较divider变化前后的WDG实际Counter速率。"
    fields:
      - {source: observation, path: crg_clock_source_samples, label: CRG WDG时钟源读回, format: text, aggregate: distinct}
      - {source: observation, path: crg_clock_divider_samples, label: CRG WDG分频读回, format: text, aggregate: distinct}
      - {source: observation, path: counter_samples_divider_zero, label: Divider0下COUNTER.CURRENT, format: text, aggregate: distinct}
      - {source: observation, path: counter_samples_divider_one, label: Divider1下COUNTER.CURRENT, format: text, aggregate: distinct}
  WDG_P2_002:
    summary: "WDG自然超时形成WDG IRQ和CPU NMI双证据，首次NMI后CPU Owner自动屏蔽全部Source。"
    fields:
      - {source: observation, path: cpu_nmi_mask, label: CPU首次NMI后的Source Mask, format: hex32, aggregate: distinct}
      - {source: measurement, path: cpu_nmi_event_count, label: CPU NMI事件计数前后值, format: text, aggregate: distinct}
      - {source: observation, path: wdg_irq_raw, label: WDG自然Timeout IRQ Raw状态, format: hex32, aggregate: distinct}
      - {source: measurement, path: wdg_irq_event_count, label: WDG IRQ事件计数前后值, format: text, aggregate: distinct}
```
<!-- ET_CASE_REPORT_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=12; MAPPING_GAP=2; NEEDS_VERIFICATION=3 | ADAPTED=14; MAPPING_GAP=1 | 15个Formal Case已注册；最近一次全量运行为14个Case 11 PASS / 3 FAIL / 0 SKIP，P0_004、P1_003的Reset Output未形成系统复位，P2_001的Counter速率未体现Divider效果；新增P1_009（窗口超时复位）尚未执行 | `ET6801_wdg.md` |

## 5. Common Gap / Evolution

- `case_implementation_gap`：14个Case均已由Registry、公共Driver/Service/Wrap和真实`test_*`闭合；P2_001/P2_002通过CRG/CPU Owner提供跨IP入口，软件门禁可验证，硬件结论仍需真实HIL。
- `wdg_exact_boundary_atomic_feed_gap`：PC串口往返不能保证Feed恰好落在`counter==low/high`；需要稳定的目标侧原子Feed触发接口后再补精确闭区间边界，不得用近似Counter冒充。
- `runtime_capability_service_gap`：已由Runtime Capability闭合；它只提供平台发现与契约门禁输入，不代替WDG硬件Feature测试。
- `chip_driver_config_readback_gap`：已由隔离的Driver Test Extension与公共Wrap闭合，写保护仍以实际`CONFIG.READBACK`为判据。
- `chip_driver_force_irq_gap` / `wdg_irq_service_gap`：已闭合Force、Raw/Status与真实ISR的分层端点；Force只用于控制路径，不替代自然IRQ Case。
- `target_reset_recovery_gap`：公共恢复链已具备；RESET_OUTPUT按SVD硬件契约发布，当前FPGA是否真正产生系统reset必须由Case执行后给出PASS/FAIL，不得通过Runtime Capability裁剪形成SKIP。
- `crg_wdg_timebase_control_gap` / `timebase_observer_gap`：公共CRG Owner与PC单调时间Observer已经具备；具体芯片仍必须通过P2_001证明配置读回和Counter速率同时符合其硬件语义，不得仅凭寄存器读回宣布闭合。
- `debug_halt_control_gap`：公共Debugger Owner已具备；P3_001已在Targeted HIL中通过，不再属于当前SKIP。
- `wdg_nmi_route_mapping_gap`：CPU Owner已提供稳定NMI掩码、Raw/Masked/Status和ISR事件计数；具体Source bit与目标处理域绑定仍需RTL/LRS或HIL冻结，不影响P2_002的软件实现。
- `cpu_nmi_service_gap`：已由CPU Owner闭合并通过FPGA HIL；首次NMI后自动全屏蔽，WDG Service仍只产生/清理自己的自然超时源。
- `WDG_F_001/WDG_P0_001`停止使用且ID不得复用；Static/Runtime Capability一致性由平台发现与契约门禁负责。
- 新芯片优先映射本文17个活动Feature与14个Case；实例数量、物理IRQ、时钟选择、NMI处理域绑定和具体范围全部留在Capability/Chip Adaptation。
- Software Gate只能证明文档/实现契约；未执行的FPGA/Silicon HIL不得写成PASS。

### 5.1 Feature完整覆盖环境矩阵

| Feature | 最小环境/执行映射 | 当前结论 |
|---|---|---|
| F002～F005、F010、F012～F013、F015～F016 | DUT + 当前WDG Service/Wrap/Driver；IRQ项需要目标CPU真实ISR | 不需要外部仪器；当前Case已覆盖主体路径 |
| F006 | DUT + 当前Counter定位可覆盖Early/Inside/Late；精确low/high边界另需目标侧原子Feed入口 | 区域行为已实现，精确闭区间边界是软件执行映射缺口 |
| F007～F008、F014 | DUT + 预期Reset/断线识别 + reopen/HELLO/Discover + 新Session + reset record读取 | 需要Runner恢复链路，不需要额外测量仪器 |
| F009 | DUT + 可脚本化Debugger Halt/Resume | 需要真实CPU Halt控制，不可用WDG配置命令冒充 |
| F011 | DUT + CRG/Reset Owner的目标WDG模块复位映射 | 需要片内模块复位Owner，不需要整板断电 |
| F017 | DUT + CRG Clock Owner + 独立Reference Counter | 需要时钟源/分频控制和独立时基 |
| F018 | DUT + CPU/NMI Route Owner + 目标处理域NMI Service | 需要NMI路由与处理域计数证据，不需要外部仪器 |

当前已接入的示波器、电源和万用表不改变上述结论：WDG剩余Case验证的是系统复位会话、片内计数时基、CPU/NMI路由和Debugger Halt等数字控制语义。示波器只能在已绑定物理端点时观察外部波形，电源/万用表只能作为供电与恢复辅助，均不能替代`RECORD.RESET`、独立`COUNTER.CURRENT`比例、NMI交付或真实Halt/Resume的决定性Oracle。Case不得写死仪器型号、通道、探头或接线；这些事实只能在后续Bench/Profile闭合后进入对应执行映射。
