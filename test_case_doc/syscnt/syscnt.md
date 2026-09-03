# SYSCNT Stable IP Contract

更新时间：2026-09-03 20:45 CST。

本文件是SYSCNT公共测试设计，不是已实现或已实测声明。7条Case全部为PLAN；硬件事实、历史资料处置及实施前缺口见同目录芯片文档。遵循R100、R110、R120、R130、R140，不新增规则。

## 0. Stable IP Contract

### 0.1 工作原理与边界

SYSCNT是持续递增的系统时间戳计数器，不是带周期比较中断的通用定时器。计数使能后每个输入Tick递增；停止时保持当前值；可停止后装载初值。主要用途是时间戳、软件超时和耗时测量。不同访问窗口读到的是同一个计数器，不是多个独立实例。

本契约测试计数与时间关系，不把SDK延时函数本身发布成硬件Feature。IRQ、DMA、PWM、比较匹配没有作为本IP已确认能力，不为凑覆盖而建立这些Case。

### 0.2 数据、配置与观测

| 对象 | 稳定语义 | 约束 |
|---|---|---|
| `instance_id` | 逻辑SYSCNT实例 | Capability选择一个实例，不写死物理Handle。 |
| `counter_bits` | 有效计数位宽，最大64 | 来自芯片事实；公共容器为无符号64位，模数M=2^counter_bits。 |
| `counter_word_bits` | 单次访问计数字的位宽 | 来自芯片事实；用于定义低字进位边界，不在Case写死32。 |
| `value_ticks` | 当前值或装载值 | 单位Tick；范围0至M-1，不用浮点保存。 |
| `read_view` | `CONTROL` / `READ` | 支持集合由Capability声明；READ只执行读取，不推定其写保护。 |
| `enabled` | 是否递增 | 与装载初值、时钟源和Debug Halt策略分离。 |
| `halt_policy` | `RUN_FREE` / `PAUSE` | 不等于CPU已经停核，也不等于硬件已经进入暂停状态。 |
| `frequency_id_hz` | 软件登记的计数频率标识 | 不是分频器，不用于自证真实计数速率。 |
| `clock_source` | 逻辑时钟源 | 由目标时钟Driver配置；SYSCNT Service不调用其他IP的Wrap。 |
| `actual_clock_hz` | 当前Lane下经确认的SYSCNT输入频率 | Profile事实，不能由frequency_id读回值反向推导。 |
| `reference_clock_hz` | 独立参考计数器频率 | 必须有独立于SYSCNT计数结果的依据。 |

| 稳定Endpoint | 原子硬件事实 | 报告含义 |
|---|---|---|
| `CONTROL.ENABLE` | 计数使能读回 | 布尔值。 |
| `CONTROL.HALT_ON_DEBUG` | 调试暂停配置读回 | 不用它替代暂停状态。 |
| `STATUS.DEBUG_HALTED` | 时间戳计数器的调试暂停状态 | 与CPU停核状态分别记录。 |
| `COUNT.CONTROL` | CONTROL窗口取得的连贯计数 | 原始整数，展示hex64。 |
| `COUNT.READ` | READ窗口取得的连贯计数 | 原始整数，展示hex64。 |
| `FREQUENCY.ID` | 频率标识读回 | 原始整数；Hz或hex32。 |
| `REFERENCE.COUNT` | 独立参考计数端点 | 与SYSCNT观测分开，不拼成一个寄存器值。 |
| `CLOCK.SOURCE` | 时钟选择硬件读回 | 由时钟所有者提供。 |
| `CPU.DEBUG_HALTED` | 调试器实际读到的CPU停核状态 | 来源observer；不是“发过halt命令”。 |

差值、计算的时长、误差、执行次数都是Measurement；不是新增硬件寄存器。

### 0.3 最小动作与Wire语义

公共链路保持`Case -> Own Driver -> TargetClient -> Own Service -> Own Wrap -> Own Chip Driver`。实例解析、位布局和SDK符号在芯片层。Service只校验长度/参数并调用SYSCNT动作，不做Case循环、数学判定或跨IP编排。

下表是待实现命令语义；不在本轮修改已发布协议或注册表。使用现有ET-Frame，全部整数小端；每个Request以`instance_id:u8`起始，保留字段必须为0。响应沿用公共Status，失败不返回伪造观测。

| 局部Command | Request（实例之后） | Success Response | 稳定动作 |
|---|---|---|---|
| `0 CAPABILITIES_GET` | 空 | feature_flags:u32、counter_bits:u8、read_view_mask:u8、reference_bits:u8、counter_word_bits:u8 | 获取硬件支持项；Service注册及实例列表沿用现有机制。 |
| `1 ENABLE_SET` | enabled:u8 | 空 | 只改变计数使能，不清零、不改频率标识。 |
| `2 VALUE_LOAD` | value:u64 | 空 | 仅在停止状态装载；完成后仍停止，运行时拒绝。 |
| `3 COUNT_GET` | view:u8 | value:u64 | 单次有界连贯读取，不启动或停止计数。 |
| `4 CONTROL_GET` | 空 | enabled:u8、halt_policy:u8、debug_halted:u8、reserved:u8、frequency_id_hz:u32 | 返回独立字段；不是对不同时间寄存器的原子快照承诺。 |
| `5 HALT_POLICY_SET` | policy:u8 | 空 | 只配置本IP暂停策略；必要的系统路由由PC显式配置。 |
| `6 FREQUENCY_ID_SET` | hz:u32 | 空 | 停止时设置标识，不改变时钟；合法范围由Capability约束。 |
| `7 REFERENCE_SAMPLE_GET` | 空 | reference_before:u64、count:u64、reference_after:u64 | 一个有界测量原语，按参考前值→SYSCNT值→参考后值读取，不等待目标时间、不判PASS。 |

Feature flags依次对应计数使能、停止装载、双窗口读取、频率标识、暂停策略、参考采样；它们描述动作支持，不编码Case等级或测试结论。`read_view`编码CONTROL=0、READ=1；policy编码RUN_FREE=0、PAUSE=1。公共状态适配使用现有Status/Wrap Status，不新增错误体系。

`REFERENCE_SAMPLE_GET`是待评审的目标侧短采样原语：芯片测试扩展可返回目标本地独立参考读数，但不得在Wrap/Service直接访问寄存器或调用其他IP Wrap。若既有测量原语能表达相同顺序则复用；否则实施前先审核芯片扩展边界。采样不复位参考计数器、不长时间关中断；参考中断、Debug或时钟变化造成的污染必须显式报告。

长时间等待、参数化循环和Oracle由PC负责。没有异步计算任务，不引入Start/Job/Result状态机；停核采样复用已有调试器控制与Execution Mapping，不在SYSCNT新建调试后端。

### 0.4 Case基线与共享资源

1. 所有Case在配置前先获得SYSCNT独占使用条件，其他Core及框架不得把它作为活动超时基准。
2. 有已验证独立复位映射的芯片先执行目标CRG复位，再执行Service状态和Resource Pool整池复位。**无已证实复位位时不得猜编号、复位整个CoreSight或调用其他IP复位代替。**
3. 无独立硬复位的芯片，候选基线为停止计数→RUN_FREE→装载0→登记经确认的频率→读回确认，再执行Service状态和Resource Pool复位。它只证明软件可控状态归一，不宣称硬件复位；实施需完成芯片文档G01裁决。
4. 时钟源和系统Halt路由由PC通过所属IP Driver设置；SYSCNT Wrap不越层配置CRG或SYSCTRL。每个参数实例重新建立基线。
5. 结束时停止SYSCNT、取消暂停策略、恢复本Case改变的系统路由/时钟源、释放测量资源；调试器在异常路径也必须恢复CPU运行。保留既有必要清理，不新建通用清理机制。

### 0.5 Oracle与采样约束

- 停止装载：Expected是PC给出的输入值；CONTROL/READ两个窗口都必须精确相等，延迟后保持不变。
- 连贯读取：拆分计数由Chip Driver有界执行高→低→高；两次高位不一致则重读，不能在Wrap补直接寄存器访问。停止时可直接读取，但不能因此声称运行态跨进位读取正确。
- 进位/回绕：初值为边界前K个Tick；K由已确认频率给出约50ms裕量。PC在不超过1秒的窗口内轮询；回绕前后用模M差值，不能把正常回绕当倒退。未观察到跨边界不得PASS。
- 独立计时：两个采样各得到`A_i, C_i, B_i`，其中A/B来自独立参考，C来自SYSCNT。参考模数R=2^reference_bits；以A_0为零点，将其余参考值按`(value-A_0) mod R`展开。PC从起点采样请求发出前到终点响应收到后的单调时间上界乘以参考最高频率，必须严格小于R，才能排除多次回绕；PC时间只验证这个上界，不充当精度Oracle。
- 实际参考时长被夹在`Tmin=(A_1-B_0)/Fref`和`Tmax=(B_1-A_0)/Fref`之间。计算`Tcnt=((C_1-C_0) mod M)/Fcnt`。只有`max(abs(Tcnt-Tmin), abs(Tcnt-Tmax)) <= 1ms`且`Tmax-Tmin <= 0.1ms`才证明本计划的相对计时预算。采样过宽是测量质量失败，不放大阈值或记为SKIP。
- 1ms是从历史需求保留的**测试验收预算**，不是已确认芯片绝对精度规格。共享同一晶振的参考只证明数字计数比例，不证明晶振绝对精度；不发布电气精度PASS。
- Debug Halt：在CPU已经停核、计数暂停状态稳定后才取两组样本；PAUSE要求计数完全不变，RUN_FREE要求增加。CPU运行前后两个值差小不能证明停核冻结。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | P等级 | 关联Case |
|---|---|---|---|---|
| SYSCNT_F_001 | SYSCNT计数值装载 | 停止时装载无符号初值，保留完整有效位。 | P0 | SYSCNT_P0_001、SYSCNT_P3_001 |
| SYSCNT_F_002 | SYSCNT计数Enable/Disable | 使能递增、停止保持、重新使能续计数。 | P0 | SYSCNT_P0_002、SYSCNT_P3_001 |
| SYSCNT_F_003 | SYSCNT计数进位与回绕 | 低字进位到高字，最大计数后按有效位宽回绕。 | P1 | SYSCNT_P1_001 |
| SYSCNT_F_004 | SYSCNT双窗口计数读取 | 两个访问窗口读取同一计数，运行态读数连贯。 | P0/P1 | SYSCNT_P0_001、SYSCNT_P1_001、SYSCNT_P3_001 |
| SYSCNT_F_005 | SYSCNT频率标识 | 软件可登记和读取Tick频率信息。 | P1 | SYSCNT_P1_002 |
| SYSCNT_F_006 | SYSCNT Debug Halt计数暂停 | PAUSE时停核冻结，RUN_FREE时停核仍计数。 | P2 | SYSCNT_P2_002 |
| SYSCNT_F_007 | SYSCNT计时间隔 | Tick差值与独立参考时间符合测试预算。 | P2 | SYSCNT_P2_001 |
| SYSCNT_F_008 | SYSCNT输入时钟源 | 在能力声明的时钟源下计数并保持对应时间比例。 | P2 | SYSCNT_P2_001 |

## 2. Case Catalog

| Case ID | 测试名称 | 等级 | 核心方法 | 最低资源 | 当前状态 |
|---|---|---|---|---|---|
| SYSCNT_P0_001 | 停止装载与双窗口读回 | P0 | 6类位型停止装载，两个窗口精确比对 | R0 | PLANNED |
| SYSCNT_P0_002 | 启停与续计数 | P0 | 运行增加→停止不变→继续增加且不清零 | R0 | PLANNED |
| SYSCNT_P1_001 | 低字进位与最大值回绕 | P1 | 两个边界附近装载，运行态跨边界读取 | R0 | PLANNED |
| SYSCNT_P1_002 | 频率标识设置与读取 | P1 | 停止时设置2个合法非零标识，读回且计数不变 | R0 | PLANNED |
| SYSCNT_P2_001 | 时钟源与独立参考计时 | P2 | 每个支持时钟源下10/50/100/1000/10000ms窗口，对比参考计数 | R0 | PLANNED |
| SYSCNT_P2_002 | CPU停核时的计数策略 | P2 | PAUSE/RUN_FREE下真实Halt并在停核期间读取 | R4 | PLANNED |
| SYSCNT_P3_001 | 20轮装载启停重复验证 | P3 | 固定20轮短流程，每轮重新建立基线 | R0 | PLANNED |

统计：8个Feature、7条逻辑Case，P0=2、P1=2、P2=2、P3=1。6条R0使用片内数字资源，1条R4使用现有外部调试仪器；现有7条不需要示波器、逻辑分析仪或新增引脚连线。历史外部脉冲测时尚未由这7条完整覆盖，见第5节。全部Case未实现、未执行，不统计为PASS/FAIL/SKIP；20轮属于单Case内部重复，不计20条Case。

## 3. Machine-readable Case Contract

### SYSCNT_P0_001：停止装载与双窗口读回

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P0_001
case_name: 停止装载与双窗口读回
report_feature: |-
  1. SYSCNT计数值装载
  2. SYSCNT双窗口计数读取
p_level: P0
feature_refs: [SYSCNT_F_001, SYSCNT_F_004]
method:
  inputs:
    - 装载位型：取0、1、低字全1、单独高字最低位、有效位交替10、全有效位1，按counter_bits裁剪去重；每个值独立参数化。
    - 初始条件：CONTROL.ENABLE=0、RUN_FREE，PC输入整数作为Expected，不从DUT读回生成Expected。
  steps:
    - 独占与基线：确认无其他消费者，按已批准复位映射建立本实例基线，并清Service状态和资源池。
    - 停止确认：读取CONTROL.ENABLE并确认0，再选择本次value_ticks。
    - 初值装载：调用VALUE_LOAD写入本次输入，不隐式开启计数。
    - 双窗口读取：读取COUNT.CONTROL和COUNT.READ，同时读取CONTROL.ENABLE。
    - 保持观测：PC等待10ms后再次读取两个计数窗口，期间不启动SYSCNT。
    - 精确比较：先记录输入和全部硬件读数，再比较四次读数均等于输入且ENABLE仍为0。
    - 参数汇总：所有去重位型均完成才关闭本Case，停止并归一状态。
  observations:
    - 装载读回：COUNT.CONTROL和COUNT.READ均应等于value_ticks，证明装载和窗口指向正确。
    - 停止保持：间隔后两个计数读回仍等于value_ticks，CONTROL.ENABLE=0，证明装载未启动计数。
  pass_criteria:
    - 数据完整：所有位型的两个窗口首次和延后读数都精确等于输入，无截断或高低字互换。
    - 停止状态：装载前后CONTROL.ENABLE均为0。
    - 参数完整：计划位型全部执行，不能只测低32位。
timeout: 每个参数实例PC统一deadline为2秒。
cleanup: [停止计数并归一Service状态，资源池整池复位；不复位其他IP。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无新增接线, bench: 无外部设备}
backend: [FPGA, Silicon]
evidence: [canonical observations, 输入位型与两次双窗口读数附件]
failure_observations:
  - {key: expected_count, label: 期望装载计数, source: oracle, role: expected, format: hex64}
  - {key: control_count, label: CONTROL窗口计数, source: dut, role: actual, format: hex64, semantic_ref: syscnt.feature.counter}
  - {key: read_count, label: READ窗口计数, source: dut, role: actual, format: hex64, semantic_ref: syscnt.feature.counter}
  - {key: enabled, label: 计数使能, source: dut, role: actual, format: bool, semantic_ref: syscnt.feature.counter_enable}
gap: [implementation_gap, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P0_002：启停与续计数

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P0_002
case_name: 启停与续计数
report_feature: |-
  1. SYSCNT计数Enable/Disable
p_level: P0
feature_refs: [SYSCNT_F_002]
method:
  inputs:
    - 起始计数：装载M/2，观察窗口10ms，总观察增量必须远小于M/2以排除回绕歧义。
  steps:
    - 建立基线：确认独占并归一硬件、Service和资源池，停止状态装载起始计数。
    - 开始计数：只置CONTROL.ENABLE，读取使能位及起始COUNT.READ。
    - 运行观测：PC等待10ms，读取COUNT.READ，检查相对起始值增加。
    - 停止计数：清CONTROL.ENABLE并读回0；等待同步稳定后保存COUNT.READ为停止值。
    - 保持检查：间隔10ms再次读取COUNT.READ，要求与停止值完全相同。
    - 恢复计数：重新使能而不装载，等待10ms后读取COUNT.READ及使能位。
    - 保存并判定：记录三个阶段硬件值，要求运行增加、停止不变、恢复后从停止值继续增加，结束时停止。
  observations:
    - 启停配置：CONTROL.ENABLE依次为1、0、1，证明命令确实改变硬件配置。
    - 三阶段计数：COUNT.READ分别表现为增加、保持、再次增加；恢复值不能回到0。
  pass_criteria:
    - 运行有效：第一次运行读数大于装载值，恢复读数大于停止值且无意外回绕。
    - 停止有效：停止稳定后的两次COUNT.READ精确相等。
    - 续计数有效：恢复动作没有清零或覆盖原计数。
timeout: PC统一deadline为2秒；不使用被测计数器的延时API作为等待依据。
cleanup: [停止计数并归一状态，资源池整池复位。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无新增接线, bench: 无外部设备}
backend: [FPGA, Silicon]
evidence: [canonical observations, 启动停止恢复阶段计数附件]
failure_observations:
  - {key: running_count, label: 运行计数, source: dut, role: actual, format: hex64}
  - {key: stopped_count, label: 停止计数, source: dut, role: actual, format: hex64}
  - {key: held_count, label: 停止后复读计数, source: dut, role: actual, format: hex64}
  - {key: resumed_count, label: 恢复计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P1_001：低字进位与最大值回绕

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P1_001
case_name: 低字进位与最大值回绕
report_feature: |-
  1. SYSCNT计数进位与回绕
  2. SYSCNT双窗口计数读取
p_level: P1
feature_refs: [SYSCNT_F_003, SYSCNT_F_004]
method:
  inputs:
    - 边界矩阵：分别选择低字进位边界和完整有效位回绕边界；起点为边界前K个Tick，K=ceil(actual_clock_hz/20)，两类独立参数化。
    - 采样约束：Capability给出计数位宽和字宽；两种边界、读数间最大时间及频率共同限定合法增量，不能从本次异常读数反推容差。
  steps:
    - 基线与选点：重建停止基线，检查counter_bits大于低字宽且K小于边界跨度。
    - 边界前装载：写入本次起点，读取两个窗口均等于Expected后才开始计数。
    - 运行态采样：在1秒内交替读取两个窗口的连贯计数，记录顺序和PC采样时间界限，不人为停止以避开读数撕裂。
    - 跨边界等待：低字场景等待高字增加，最大值场景等待模M后的低计数；发现异常仍保存已有样本。
    - 终态采集：停止计数、等待窗口稳定，分别读取COUNT.CONTROL和COUNT.READ。
    - 数学判定：PC按初值与模M展开序列，检查确实跨越目标边界、无不合理倒退或整字跳变，最后两个窗口相等。
    - 参数汇总：两类边界都执行并记录原始采样序列，任何一类未跨界或数据异常都不能PASS。
  observations:
    - 运行计数：COUNT.CONTROL与COUNT.READ的有序样本应能展开为同一递增时间线，不能出现高低字拼接错误。
    - 跨界终态：低字进位应使高字增加，最大值应回绕为小值；停止后的两个窗口应一致。
  pass_criteria:
    - 边界确实触发：两类参数均取得真实边界前装载读数和边界后运行读数。
    - 增量合法：模M展开后不倒退，增量不超过由采样时间上界和经确认最高频率给出的上限。
    - 窗口一致：停止稳定后的两个计数值完全一致。
timeout: 每个边界PC统一deadline为2秒，其中跨界观测窗口最多1秒。
cleanup: [停止计数并重新装载基线，资源池整池复位。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无新增接线, bench: 无外部设备}
backend: [FPGA, Silicon]
evidence: [canonical observations, 有序运行样本与模数展开结果附件]
failure_observations:
  - {key: initial_count, label: 跨界前计数, source: dut, role: actual, format: hex64}
  - {key: after_boundary_count, label: 跨界后计数, source: dut, role: actual, format: hex64}
  - {key: final_control_count, label: 停止后CONTROL计数, source: dut, role: actual, format: hex64}
  - {key: final_read_count, label: 停止后READ计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, coherent_read_extension, clock_mapping, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P1_002：频率标识设置与读取

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P1_002
case_name: 频率标识设置与读取
report_feature: |-
  1. SYSCNT频率标识
p_level: P1
feature_refs: [SYSCNT_F_005]
method:
  inputs:
    - 标识数据：选择Capability允许的两个不同非零Hz值；本Case只验证登记存储，不声称切换实际时钟。
  steps:
    - 建立基线：独占、归一Service和资源池，确认CONTROL.ENABLE=0。
    - 初态记录：读取FREQUENCY.ID与COUNT.READ，保存应恢复的正式频率标识。
    - 设置首值：停止时写入第一个标识，读取FREQUENCY.ID、COUNT.READ和CONTROL.ENABLE。
    - 设置次值：写入第二个标识，重复读取相同三个独立硬件端点。
    - 记录比较：将每个读回标识与对应输入精确比较，同时检查计数未变且仍停止。
    - 恢复标识：写回经确认的当前时钟频率标识并读回确认，保留两组结果。
  observations:
    - 标识读回：FREQUENCY.ID依次等于两次输入和最终恢复值，证明登记字段可读写。
    - 计数副作用：COUNT.READ不变且CONTROL.ENABLE=0，证明修改标识没有隐式装载或启动。
  pass_criteria:
    - 标识一致：两组写入值和恢复值都精确读回。
    - 状态不变：计数值与使能位在本Case内保持停止初态。
timeout: PC统一deadline为2秒。
cleanup: [恢复本Lane正式频率标识并保持停止，资源池整池复位。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无新增接线, bench: 无外部设备}
backend: [FPGA, Silicon]
evidence: [canonical observations, 标识输入与读回附件]
failure_observations:
  - {key: expected_frequency_id, label: 期望频率标识, source: oracle, role: expected, format: hex32}
  - {key: frequency_id, label: 硬件频率标识, source: dut, role: actual, format: hex32, semantic_ref: syscnt.feature.frequency_id}
  - {key: count, label: 停止计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P2_001：时钟源与独立参考计时

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P2_001
case_name: 时钟源与独立参考计时
report_feature: |-
  1. SYSCNT计时间隔
  2. SYSCNT输入时钟源
p_level: P2
feature_refs: [SYSCNT_F_007, SYSCNT_F_008]
method:
  inputs:
    - 时钟与窗口：每个已确认可用的逻辑时钟源分别覆盖约10ms、50ms、100ms、1000ms、10000ms五个窗口；同一路径参数化保留历史窗口，参考频率和被测频率从独立时钟事实取得。
    - 计时预算：使用0.5节的双端夹取公式，最坏时间误差不超过1ms，采样不确定区间不超过0.1ms；不是晶振电气精度指标。
  steps:
    - 独占基线：确认参考计数器可用且不依赖SYSCNT，归一硬件、Service和资源池。
    - 选择时钟：停止SYSCNT，由时钟Driver选择本参数源并读回CLOCK.SOURCE，登记对应频率标识后使能。
    - 起点采样：执行一次REFERENCE_SAMPLE_GET，保存参考前值、COUNT.READ和参考后值。
    - 区间推进：PC等待本参数的近似窗口，不调用被测SYSCNT延时函数；PC等待只分隔采样，不充当精度Oracle。
    - 终点采样：再次获取三个原始读数，检查参考持续运行且未复位/停核，并用PC包围时间上界确认总参考增量小于一个完整模数。
    - 独立换算：PC由两组参考值计算Tmin/Tmax，由SYSCNT差值计算Tcnt，先记录原始Observation再计算最坏误差。
    - 判定与恢复：所有时钟源和窗口都满足计时预算才PASS，停止SYSCNT并恢复时钟选择与参考资源。
  observations:
    - 实际时钟选择：CLOCK.SOURCE应等于本次请求源；同频两源仅有相同计数速率不能证明选择正确。
    - 被测计数：两次COUNT.READ形成实际Tick差值，不能从请求等待时长伪造计数。
    - 参考计数：每个采样的REFERENCE.COUNT前后值夹住被测读取时刻，独立确定实际时间范围。
  pass_criteria:
    - 比较边界：每个参数的最坏误差不超过1ms，参考区间宽度不超过0.1ms，超过时保留测量质量失败。
    - 时钟覆盖：声明可用的每个源均读回正确，并完成五个窗口；不能因参考位宽或软件未实现省略长窗口。
    - 参考有效：参考与SYSCNT都实际推进，参考频率有来源，参考测量过程无复位或停核污染。
timeout: 每个参数PC统一deadline为目标窗口加2秒，最长12秒；采样包围时间上界必须小于参考完整回绕周期。参考位宽无法覆盖时先解决测量能力缺口，不能伪造PASS或记硬件SKIP。
cleanup: [停止SYSCNT，恢复本Case时钟选择及参考计数器使能所有权，资源池整池复位。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 片内已实现的计数时钟源, bench: 片内独立参考计数器，不新增外部接线}
backend: [FPGA, Silicon]
evidence: [canonical observations, 三元组采样和时钟来源附件, 误差区间Measurement]
failure_observations:
  - {key: clock_source, label: 时钟选择读回, source: dut, role: config, format: text}
  - {key: count_before, label: 起点计数, source: dut, role: actual, format: hex64}
  - {key: count_after, label: 终点计数, source: dut, role: actual, format: hex64}
  - {key: reference_count, label: 独立参考计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, reference_sample_extension_review, clock_mapping, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P2_002：CPU停核时的计数策略

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P2_002
case_name: CPU停核时的计数策略
report_feature: |-
  1. SYSCNT Debug Halt计数暂停
p_level: P2
feature_refs: [SYSCNT_F_006]
method:
  inputs:
    - 策略矩阵：PAUSE与RUN_FREE分别执行相同流程，使用已有调试器保持CPU停核约100ms，两组计数均在停核期间读取。
    - 停核条件：Execution Mapping定义目标CPU、其他执行实体的静止条件、系统Halt路由和计数观测端点；不能把单步间隔当作Halt证明。
  steps:
    - 基线与路由：停止并归一SYSCNT、Service和资源池，由所属Driver配置系统Halt路由并确认计数器不被其他Core使用。
    - 策略配置：设置本参数策略、装载非边界值并启动，保存CONTROL.HALT_ON_DEBUG读回。
    - CPU停核：调试器发起Halt并实际读取CPU.DEBUG_HALTED=1；停核后不等待固件串口响应。
    - 起点观测：在有界同步窗口后读取STATUS.DEBUG_HALTED和连贯COUNT.READ，记录调试器身份与时间。
    - 停核保持：保持约100ms，仍在CPU停核期间读取第二组计数、暂停状态和CPU停核状态。
    - 恢复确认：恢复CPU运行，读取STATUS.DEBUG_HALTED回到0并确认COUNT.READ继续增加；所有异常路径均恢复CPU。
    - 分策略判定：记录两组策略证据，PAUSE要求停核期间计数不变且暂停状态为1，RUN_FREE要求增加且暂停状态为0。
  observations:
    - CPU停核事实：CPU.DEBUG_HALTED在两次计数采样时均为1，证明观测窗口真实有效。
    - 计数暂停状态：PAUSE下STATUS.DEBUG_HALTED应为1，RUN_FREE为0；配置位为1不能代替此状态。
    - 停核计数：两次COUNT.READ在PAUSE下精确相等，RUN_FREE下正向增加。
  pass_criteria:
    - 真实停核：两次取样都获得CPU停核读回，未确认停核时不得形成计数暂停PASS。
    - 策略有效：两种策略都满足各自暂停状态和计数变化判据。
    - 运行恢复：恢复CPU后计数器离开暂停状态并继续增加，控制通信恢复。
timeout: 每个策略PC统一deadline为5秒；停核同步最多100ms，保持约100ms，异常必须恢复CPU。
cleanup: [无条件恢复CPU运行，停止SYSCNT并设RUN_FREE，恢复系统Halt路由，资源池整池复位。]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已有调试接口，无新增引脚连线, bench: 可停核且停核期间可读计数的外部调试器}
backend: [FPGA, Silicon]
evidence: [canonical observations, Debugger身份和停核时间线附件]
failure_observations:
  - {key: cpu_halted, label: CPU实际停核状态, source: observer, role: actual, format: bool}
  - {key: debug_halted, label: SYSCNT实际暂停状态, source: dut, role: actual, format: bool, semantic_ref: syscnt.feature.debug_halt}
  - {key: halted_count_before, label: 停核起点计数, source: dut, role: actual, format: hex64}
  - {key: halted_count_after, label: 停核终点计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, halt_execution_mapping, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### SYSCNT_P3_001：20轮装载启停重复验证

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: SYSCNT_P3_001
case_name: 20轮装载启停重复验证
report_feature: |-
  1. SYSCNT计数值装载
  2. SYSCNT计数Enable/Disable
  3. SYSCNT双窗口计数读取
p_level: P3
feature_refs: [SYSCNT_F_001, SYSCNT_F_002, SYSCNT_F_004]
method:
  inputs:
    - 重复参数：固定20轮，轮次k从0到19，初值M/2+257*k；使用小于半模数的短运行窗口，不扩大成长时间老化。
  steps:
    - 轮次基线：每轮配置前独占并按批准映射归一SYSCNT、Service和资源池。
    - 初值装载：停止状态写入该轮初值，双窗口精确读回，避免前一轮状态残留。
    - 短时运行：使能计数并等待约1ms后读取COUNT.READ，确认高于初值。
    - 停止保持：停止并等待读数同步稳定，再间隔约1ms读取两次COUNT.READ。
    - 窗口核对：读取停止后的COUNT.CONTROL，要求与稳定COUNT.READ一致。
    - 逐轮记录：每轮断言前记录初值、运行值、停止值、保持值和两窗口结果；首次失败保存现场并结束。
    - 总体判定：只有20轮全部满足装载正确、运行增加、停止保持且窗口一致才PASS，结束时归一资源。
  observations:
    - 每轮计数：COUNT.CONTROL和COUNT.READ必须反映本轮初值、运行和停止状态，不沿用前轮缓存。
    - 每轮使能：CONTROL.ENABLE在运行及停止阶段分别为1和0。
  pass_criteria:
    - 重复完整：完成20轮且每轮输入、运行和保持判据全部满足；提前停止不能当完成。
    - 无状态污染：每轮停止装载读回等于本轮Expected，停止后的两个窗口一致且不再增加。
timeout: Case PC统一deadline为15秒；每轮硬件命令使用剩余deadline。
cleanup: [停止计数并归一本实例状态，资源池整池复位。]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无新增接线, bench: 无外部设备}
backend: [FPGA, Silicon]
evidence: [canonical observations, 20轮逐轮原始计数附件与完成轮数Measurement]
failure_observations:
  - {key: loaded_count, label: 本轮装载计数, source: dut, role: actual, format: hex64}
  - {key: running_count, label: 本轮运行计数, source: dut, role: actual, format: hex64}
  - {key: stopped_count, label: 本轮停止计数, source: dut, role: actual, format: hex64}
  - {key: held_count, label: 本轮保持计数, source: dut, role: actual, format: hex64}
gap: [implementation_gap, baseline_mapping_review]
```
<!-- ET_CASE_PLAN_END -->

### 3.1 实现阶段的报告字段选择

当前无SPEC，不提前添加ET_CASE_REPORT。以下是实现时应绑定的1～4项展示内容，不是第二套机器Schema；完整硬件Observation仍按各PLAN记录，PASS与FAIL使用相同字段。

| Case | 简短备注主题 | 建议展示字段 |
|---|---|---|
| P0_001 | 装载输入与双窗口实际计数对比 | Expected、CONTROL计数、READ计数、使能状态 |
| P0_002 | 运行、停止、保持及恢复计数变化 | 运行计数、停止计数、保持计数、恢复计数 |
| P1_001 | 跨界前后计数及停止后窗口一致性 | 初始值、跨界值、最终CONTROL值、最终READ值 |
| P1_002 | 频率标识写入与读回 | 输入标识、读回标识、停止计数 |
| P2_001 | 选择源与实际计时偏差 | 时钟源、计数Tick差值、参考时长区间、最坏时间误差 |
| P2_002 | CPU停核事实与SYSCNT暂停行为 | CPU停核状态、SYSCNT暂停状态、停核前计数、停核后计数 |
| P3_001 | 20轮全部完成及计数状态 | 完成轮数、装载结果、启停结果、窗口比较结果 |

派生误差/差值/比较结果使用Measurement或已绑定Artifact，不能标为硬件寄存器。参数化Case按参数分别保留原子事实再聚合，不把不同端点拼成一个Observation。

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=8 | IMPLEMENTATION_GAP=7 | 复位基线、时钟事实和停核映射待裁决；尚未实现公共测试链路 | `ET6801_syscnt.md` |

## 5. Common Gap / Evolution

- `implementation_gap`：本轮没有PC Driver/Case、Firmware Service/Wrap或运行注册，不把PLAN算成已实现。
- `baseline_mapping_review`：没有独立复位的目标必须先批准可证明的状态归一基线；禁止用错误CRG编号凑齐流程。
- `coherent_read_extension`：需要有界连贯读取，防止低字进位时读数撕裂。
- `clock_mapping`：实际Tick频率、参考频率与可用源必须来自目标事实；不能采用历史固定频率或由待测值校准自身。
- `reference_sample_extension_review`：只评审短原子采样，不引入Firmware Case或跨IP测试状态机。
- `halt_execution_mapping`：复用已有调试器能力；需明确CPU停核到计数暂停请求的实际连接，不能继承其他定时器的HIL结论。
- `external_timing_observation`：历史外部脉冲测时与片内参考比较不是等价证据。外部参考时间基准、脉冲与计数的绑定及误差预算未闭合前，不宣称完整覆盖该测试要求；闭合后使用独立Observer Case承接，不把片内DWT结果当作外部测量。

覆盖结论：8项已确认数字Feature都有PLAN；历史50ms/10s参数已补入同一计时Case。外部脉冲测时仅有Gap，尚无等价Case，因此不能宣称参考资料全部覆盖或整体Implementation Ready。RO窗口写属性、未列入目标SVD的识别寄存器和未证实的独立复位继续在芯片文档保留边界，不以SKIP掩盖缺口。
