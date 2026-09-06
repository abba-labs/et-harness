# ETIM Public Test Contract

时间：2026-09-06 16:22 CST

本轮为首次分析记录，状态为 **PARTIAL_ANALYSIS / NOT_IMPLEMENTED / NOT_EXECUTED**。
已确认测试方法的部分形成19个PLAN；其余有效需求保留在第五节及芯片Source Item Trace中。
2026-09-06 18:06 CST复核：使用继承资料解释原理并以目标SVD裁定差异，不以取得RTL为分析前提。
存在影响方法和Oracle的UNKNOWN，因此不能宣称整个IP规划完成或整体Implementation Ready。
内部数字测量、引脚波形测量和电气极限不是同一覆盖结论。所有PLAN均未注册、未实现、未实测。

## 0. Stable IP Contract

### 0.1 数据、单位与逻辑角色

公共Case只使用逻辑`dut_channel`、`pwm_source`、`capture_observer`和可选Bench端点。
生产者与捕获者必须为不同计数通道；同一通道的PWM与Capture共享计数器，不能当作独立时基。
实例数量、可路由组合、时钟、输出分组和物理连接由Capability/Execution Mapping提供。
不允许默认选第一个实例；未闭合的路由不能通过修改Case期望值适配。

| 数据 | 稳定语义与约束 |
|---|---|
| `divider` | 实际计数分频倍数，正整数；不是硬件编码。全部合法值从Capability取得 |
| `period_ticks` | 一个完整PWM周期的计数Tick数；公共使用可容纳最大周期的无符号64位数，适配层负责终值编码 |
| `compare_a_ticks / compare_b_ticks` | 周期内比较时刻；普通波形矩阵使用严格内部点，避免零宽度和边界未定行为 |
| `compare_mode` | `A`：高区间从周期起点到A；`A_B`：高区间从A到B，要求0<A<B<period_ticks |
| `capture_edges` | 按捕获槽顺序给出`RISING/FALLING`；本阶段使用前1～4槽，数量上限由Capability声明 |
| `clear_after_capture` | 每槽独立布尔值；false保存绝对时间戳，true在该捕获之后清计数器 |
| `capture_mode / stop_after` | `ONE_SHOT`在指定槽后冻结已捕获值；`CONTINUOUS`在该槽后回到首槽继续；stop_after为逻辑槽数，不是编码 |
| `input_divider` | 对输入信号预分频的实际倍数；独立于计数时钟divider。只使用Capability列出的合法倍数 |
| `filter_mode` | 基础捕获固定BYPASS；滤波专项使用WINDOW_MAJORITY，窗口W、阈值T满足W/2<T<=W，避免双方同时达阈值；采样周期范围由芯片时钟映射提供 |
| `update_mode` | IMMEDIATE或PERIOD_BOUNDARY；周期、比较对、事件分别选择；比较对Shadow需要先写完整A/B再显式commit |
| `phase_ticks / sync_source` | 同步时装入的计数值与逻辑同步源；同步源为SOFTWARE/PERIOD/DISABLED，输入使能独立控制 |
| `fault_mode / fault_level` | CBC或ONE_SHOT，强制LOW/HIGH；故障输入、故障状态退出Clear和IRQ Clear是三个不同动作 |
| `delay_config` | 输出支路、输入支路、上升/下降延迟使能、延迟Tick数、旁路/处理/反相；delay_tick_seconds由目标映射提供，不等同于计数Tick |
| `irq_source` | `FAULT_ONE_SHOT / FAULT_CBC / FAULT_OVERFLOW / COMPARE_ERROR / COMPARE_A / COMPARE_B / PERIOD / COUNTER_OVERFLOW / CAPTURE_1..4`中Capability支持的源 |
| `deadline_ms` | Firmware单动作有界截止时间；PC事务截止时间必须覆盖该动作及传输余量，禁止无限等待或隐式重试 |

PWM普通区间Oracle：设源时钟Fs、源分频Ds、接收时钟Fc、接收分频Dc，则期望周期捕获差值
`N = period_ticks * Ds * Fc / (Fs * Dc)`；A模式高宽使用`compare_a_ticks`替换period_ticks，
A_B模式高宽使用`compare_b_ticks-compare_a_ticks`。优先构造整数N，禁止由实际测得值倒算Expected。
绝对时间戳采用按硬件计数宽度的模减；普通Case保证相邻事件间隔小于一次回卷，不推断跨多次回卷。
异步边沿量化允许误差由已验证的捕获时钟/路由上界给出，作为`capture_error_ticks`保存在参数证据中；
没有这个上界时停止对应execution，不能借用历史代码的任意容差。
同源数字环回只能证明比例/数字路径，不能证明绝对频率、分辨率、引脚电气质量或两端同源错误不存在。

### 0.2 直接动作与异步执行

下列名称定义动作语义，不预占Wire数字ID，也不是本轮新增实现。后续命令必须使用R400 ET-Frame。

| 动作 | Request / Response语义 |
|---|---|
| `configure_timebase` | 输入逻辑通道、divider、period_ticks；仅在停止状态配置；返回实际配置读回与可用计数宽度 |
| `configure_pwm` | 输入通道、A/A_B、A/B比较时刻；基础Case启动前立即配置，专项Case才启用Fault、延迟或动态更新 |
| `configure_capture` | 输入通道、逻辑信号源、时基、模式、槽边沿/清零数组、input_divider、load_enable和filter=BYPASS；返回逐字段实际读回 |
| `set_enable` | 分别控制模块、计数器、PWM、Capture及Capture Load；不能把几个Enable压成一个不可区分动作 |
| `count_live / latch_count / clear_count` | 返回真实实时值、锁存值；锁存和清零必须完成硬件写脉冲及有界可见性确认，不能直接回显软件值 |
| `capture_rearm` | 在One-Shot冻结后复位槽序列并允许下一轮加载；不声称顺带清计数器或擦除旧CAP数据 |
| `irq_configure / force / clear / snapshot` | 独立Enable、Mask、Force、Clear；snapshot保留每源RAW和STATUS，不用一个总布尔值替代 |
| `irq_session_start / status / stop` | 绑定当前逻辑通道及源；真实ISR锁存首次来源和硬件现场后停止该源投递；Service事件数单列Measurement |
| `capture_start / status / result / abort` | start建立本次运行身份；status返回槽状态及目标捕获pending；result读取本次各槽真实值，不能返回上次会话缓存冒充本次值；abort停止相关生产者/接收者并释放IRQ |
| `update_start / status / result / abort` | 在预定计数窗口写周期或比较值；返回写入前后COUNT.LIVE、各次写入顺序与完成身份，窗口越界为执行错误；Shadow比较对另有显式commit，不自动提交半对值 |
| `configure_sync / emit_sync` | 配置逻辑源、phase_ticks、输入使能和输出模式；emit只产生一次软件同步，不隐式清零其他通道 |
| `configure_fault / set_fault_input / clear_fault` | 配置CBC/ONE_SHOT及输出电平，设置软件故障输入，单独发出One-Shot Clear；IRQ清除不代替Fault恢复 |
| `configure_filter / configure_delay` | 停止状态配置逻辑窗口/阈值/初始化或输出支路四链参数；返回实际字段读回，不用读回证明波形 |
| `configure_dma_request` | 选择本通道PERIOD或COMPARE请求；DMA传输本身复用公共DMA动作，禁止ETIM Wrap越层调用DMA Wrap |

Firmware负责同一动作内的时序敏感操作、短窗等待、原子现场采集和abort；PC负责参数化、独立Oracle、
最终断言、Bench和Artifact。Case不能直接访问SDK、IRQ控制器、芯片私有端点或仪器传输。
模块复位/资源隔离沿用平台已有机制；Common Wrap不得为获取Peer刺激越层调用其他IP的Wrap。
配置失败、能力不足、超时和abort必须显式返回，不自动重试可能重复触发的动作。
Result中分别保留原始硬件值、配置输入、Expected、量化误差上界和服务测量值。

### 0.3 最小硬件端点与证据身份

| 公共Endpoint | 事实来源及用途 |
|---|---|
| `TIMEBASE.DIVIDER / PERIOD_LIMIT` | 分频/周期终值实际读回；只证明配置，不能代替计时测量 |
| `COUNT.LIVE / LATCHED` | 实时计数与锁存计数两个独立硬件端点 |
| `ENABLE.MODULE / TIMER / PWM / CAPTURE / CAPTURE_LOAD` | 五个独立Enable字段；每个Observation只绑定一个字段 |
| `CAPTURE.VALUE[slot]` | 指定槽的硬件时间戳；每槽独立Observation，不拼成单个寄存器值 |
| `CAPTURE.NEXT_SLOT` | 下一捕获槽指示；冻结成立还必须比较冻结前后CAP值 |
| `IRQ_RAW.<source> / IRQ_STATUS.<source>` | 每源原始pending与有效pending；必须分别记录 |
| `IRQ_DELIVERY.FIRST_SOURCE / COUNT` | 真实ISR锁存来源与Service事件计数；属于服务事实，不标成IRQ寄存器 |
| `PWM_OUTPUT.EDGE_TIMES` | 外部Observer实际捕获的边沿序列；由波形附件支撑 |
| `STIMULUS_OUTPUT.EDGE_TIMES` | 仪器刺激的独立测量边沿；不使用仪器设定值冒充实测值 |
| `UPDATE.COMMIT_PENDING` | 比较对提交标识的实际值；写入配置读回不等于生效值，必须结合输出边沿 |
| `SYNC.PHASE / INPUT_ENABLE` | 相位值及同步输入开关分别读回；相位加载由COUNT.LIVE或输出证明 |
| `FAULT_OUTPUT.LEVEL` | 独立Observer测得的故障期间输出电平；不是fault_level配置回显 |
| `DMA_CHANNEL.COMPLETE / REMAINING` | 公共DMA端硬件完成及剩余量，分别采集；Destination数据另存Artifact |

各Case的人工报告关键字段在Case Catalog中确定，最多4项；一组重复采样可存入有身份的结构化Artifact，
其中仍保留逐槽、逐源、逐阶段端点，不能冒充单个Canonical寄存器Observation。
现阶段无SPEC，故不声明ET_CASE_REPORT；转为SPEC时再绑定这些真实字段及参数execution一致性。

## 1. Feature Catalog

| Feature ID | 报告名称 | 公共测试语义 | 主要Case |
|---|---|---|---|
| ETIM_F_001 | ETIM 计数与Enable/Disable | 计数使能时推进，停止后的有界观察窗保持不变 | ETIM_P0_001, ETIM_P1_006 |
| ETIM_F_002 | ETIM 计数预分频 | 实际分频倍数决定计数速率；数字比例和外部绝对时间分别证明 | ETIM_P0_001, ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_003 | ETIM 可编程周期 | 周期配置可保存并决定PWM重复间隔；边界配置不等于边界运行覆盖 | ETIM_P0_001, ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_004 | ETIM 计数锁存 | 显式锁存得到快照，实时计数继续推进时快照保持 | ETIM_P0_001 |
| ETIM_F_005 | ETIM 计数清零 | 非零计数停止后可清零，重新启动继续计数 | ETIM_P0_001 |
| ETIM_F_006 | ETIM PWM A比较模式 | A决定从周期起点开始的高电平宽度 | ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_007 | ETIM PWM A+B比较模式 | A和B分别确定高区间开始和结束 | ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_008 | ETIM PWM Enable/Disable | PWM关闭后无周期边沿，恢复后再次输出原配置周期 | ETIM_P1_006 |
| ETIM_F_009 | ETIM 捕获边沿选择 | 按槽选择上升沿或下降沿，捕获值对应指定边沿序列 | ETIM_P1_002, ETIM_P1_003, ETIM_P2_002 |
| ETIM_F_010 | ETIM 绝对捕获时间戳 | 不清计数器，连续时间戳差值反映外部事件间隔 | ETIM_P1_002, ETIM_P2_002 |
| ETIM_F_011 | ETIM 相对捕获时间戳 | 在指定槽事件后清计数器，后续时间戳反映距该事件的间隔 | ETIM_P1_003, ETIM_P2_002 |
| ETIM_F_012 | ETIM 捕获输入预分频 | 输入预分频改变同极性捕获的事件间隔，不改变计数时钟配置 | ETIM_P1_005 |
| ETIM_F_013 | ETIM 捕获One-Shot | 指定槽后停止加载，后续刺激不能覆盖该轮数据 | ETIM_P1_004 |
| ETIM_F_014 | ETIM 捕获Continuous | 指定槽后回到首槽，后续刺激持续刷新捕获数据 | ETIM_P1_004 |
| ETIM_F_015 | ETIM 捕获Rearm | One-Shot冻结后重新武装，从首槽开始接收下一轮 | ETIM_P1_004 |
| ETIM_F_016 | ETIM Capture Load Enable/Disable | 关闭加载时CAP保持，恢复加载后随新事件更新 | ETIM_P1_006 |
| ETIM_F_017 | ETIM 中断Force/Clear | Force建立指定pending，Clear只清指定源；不替代自然事件测试 | ETIM_P0_002 |
| ETIM_F_018 | ETIM 中断Mask/Unmask | Mask抑制有效pending和投递，保留原始pending；Unmask恢复可投递状态 | ETIM_P0_002 |
| ETIM_F_019 | ETIM 中断Enable/Disable | 已使能源能够进入真实IRQ投递链；关闭后投递停止 | ETIM_P0_002, ETIM_P1_007 |
| ETIM_F_020 | ETIM Compare/Period中断 | 计数自然到达比较或周期事件后产生对应中断 | ETIM_P1_007 |
| ETIM_F_021 | ETIM Capture中断 | 对应捕获槽真实加载时产生指定捕获中断 | ETIM_P1_007 |
| ETIM_F_022 | ETIM COMPA≥COMPB配置错误 | A+B模式非法比较顺序触发配置错误，纠正后可清除 | ETIM_P1_008 |
| ETIM_F_023 | ETIM 周期Shadow加载 | 写入新周期后当前周期保留，周期边界后生效 | ETIM_P1_009 |
| ETIM_F_024 | ETIM 比较对Shadow提交 | A/B写完并提交后在周期边界成对生效，未提交不生效 | ETIM_P1_010 |
| ETIM_F_025 | ETIM 运行中立即加载 | 在安全更新窗口写入周期或比较值后，本周期使用新值 | ETIM_P1_009, ETIM_P1_010 |
| ETIM_F_026 | ETIM 同步相位装载 | 选定同步到达后计数装入配置相位，关闭输入时不装载 | ETIM_P1_011 |
| ETIM_F_027 | ETIM 软件与周期SyncOut | 软件单次或周期事件产生同步，关闭输出无同步 | ETIM_P1_011 |
| ETIM_F_028 | ETIM CBC Fault封波 | 有效Fault强制输出，输入撤销后在周期边界恢复 | ETIM_P2_003 |
| ETIM_F_029 | ETIM One-Shot Fault封波 | 输入撤销后仍保持封波，同周期Clear满足退出条件后恢复 | ETIM_P2_003 |
| ETIM_F_030 | ETIM Fault重复输入中断 | Fault保持期间再次输入有效事件产生overflow pending | ETIM_P2_003 |
| ETIM_F_031 | ETIM 窗口阈值滤波 | 唯一多数阈值下抑制短脉冲并允许稳定长脉冲产生捕获 | ETIM_P2_004 |
| ETIM_F_032 | ETIM 死区支路处理 | 输入选择、边沿延迟和反相决定输出边沿；旁路恢复原支路 | ETIM_P2_005 |
| ETIM_F_033 | ETIM 周期与比较DMA请求 | 自然计数事件触发DMA完成指定搬运，停止事件时不传输 | ETIM_P2_006 |

上述新增Feature只覆盖已描述的常规行为，不吞并滤波平局、死区窄脉冲、Fault与死区优先级、
同步竞态或DMA捕获槽选择等剩余项。通道数、输入源数量和位宽仍是Capability参数。

## 2. Case Catalog

| Case ID | Case名称 | P等级 | 资源 | 状态 | 人工报告关键事实（其余进入Artifact） |
|---|---|---|---|---|---|
| ETIM_P0_001 | 计数配置、启停、锁存与清零 | P0 | R0 | PLANNED | TIMEBASE.PERIOD_LIMIT；COUNT.LIVE分阶段值；COUNT.LATCHED分阶段值；分频读回 |
| ETIM_P0_002 | IRQ强制、屏蔽、选择清除与投递 | P0 | R0 | PLANNED | 目标源IRQ_RAW；目标源IRQ_STATUS；保留源IRQ_RAW；ISR首次来源 |
| ETIM_P1_001 | PWM模式与时基数字环回矩阵 | P1 | R1 | PLANNED | CAPTURE.VALUE首槽；次槽；第三槽；Expected间隔 |
| ETIM_P1_002 | 绝对时间戳与捕获极性 | P1 | R1 | PLANNED | CAPTURE.VALUE首槽；次槽；第三槽；Expected间隔 |
| ETIM_P1_003 | 相对时间戳与逐槽清零 | P1 | R1 | PLANNED | CAPTURE.VALUE次槽；第三槽；末槽；Expected间隔 |
| ETIM_P1_004 | One-Shot、Continuous及Rearm | P1 | R1 | PLANNED | CAPTURE.NEXT_SLOT；首槽分阶段值；末有效槽分阶段值；末槽IRQ_RAW |
| ETIM_P1_005 | 捕获输入预分频矩阵 | P1 | R1 | PLANNED | CAPTURE.VALUE首槽；次槽；逻辑输入分频；Expected间隔 |
| ETIM_P1_006 | 计数、PWM与Capture Load独立门控 | P1 | R1 | PLANNED | 当前Enable字段；COUNT.LIVE分阶段值；CAPTURE.VALUE首槽分阶段值；恢复后周期 |
| ETIM_P1_007 | Compare、Period与Capture自然IRQ | P1 | R1 | PLANNED | IRQ_RAW目标源；ISR锁存IRQ_STATUS目标源；ISR首次来源；清除后IRQ_RAW |
| ETIM_P1_008 | A+B非法比较配置与恢复 | P1 | R0 | PLANNED | IRQ_RAW.COMPARE_ERROR清除前后；IRQ_STATUS.COMPARE_ERROR；比较输入关系 |
| ETIM_P2_001 | 外部时间基准PWM频率与占空比 | P2 | R4 | PLANNED | PWM_OUTPUT.EDGE_TIMES附件；实测周期；实测高宽；允许误差 |
| ETIM_P2_002 | 外部脉冲周期与脉宽捕获 | P2 | R4 | PLANNED | STIMULUS_OUTPUT.EDGE_TIMES附件；CAPTURE.VALUE次槽；第三槽；Expected间隔 |
| ETIM_P1_009 | 周期立即与Shadow运行更新 | P1 | R1 | PLANNED | 更新计数窗口；过渡周期；后续周期；Expected周期 |
| ETIM_P1_010 | 比较对提交与立即更新 | P1 | R1 | PLANNED | UPDATE.COMMIT_PENDING；更新计数窗口；边沿序列；Expected边沿 |
| ETIM_P1_011 | 软件和周期同步相位装载 | P1 | R1 | PLANNED | SYNC.PHASE；同步前COUNT.LIVE；同步后COUNT.LIVE；Expected区间 |
| ETIM_P2_003 | 软件Fault封波、重复输入与恢复 | P2 | R4 | PLANNED | FAULT_OUTPUT.LEVEL；模式IRQ_RAW；overflow IRQ_RAW；恢复边沿附件 |
| ETIM_P2_004 | 窗口滤波短脉冲抑制与长脉冲通过 | P2 | R4 | PLANNED | 输入边沿附件；短脉冲后槽状态；长脉冲CAPTURE.VALUE；捕获RAW |
| ETIM_P2_005 | 死区支路选择、延迟与反相 | P2 | R4 | PLANNED | 输入边沿附件；输出边沿附件；实测延迟；Expected延迟 |
| ETIM_P2_006 | 周期和比较事件触发DMA搬运 | P2 | R2 | PLANNED | DMA_CHANNEL.COMPLETE；DMA_CHANNEL.REMAINING；Destination数据；Expected数据 |

这些Case的语义不同于压力、最高频率、最小脉宽和最大捕获时长认证；后者仍为UNKNOWN，不能把普通矩阵当成替代。

## 3. Machine-readable Case Contract

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P0_001
case_name: 计数配置、启停、锁存与清零
report_feature: |-
  1. ETIM 计数与Enable/Disable
  2. ETIM 计数预分频
  3. ETIM 可编程周期
  4. ETIM 计数锁存
  5. ETIM 计数清零
p_level: P0
feature_refs: [ETIM_F_001, ETIM_F_002, ETIM_F_003, ETIM_F_004, ETIM_F_005]
method:
  inputs:
    - 配置覆盖矩阵：遍历逻辑计数通道和全部合法divider；停止状态读写最小、最大及交替位周期终值，功能阶段统一采用足够长且不会在观察窗回卷的周期。
    - 计数观察窗口：依据时钟上界选取至少32个计数Tick且小于四分之一周期的目标侧等待窗，测试PWM和Capture均关闭。
  steps:
    - 通道隔离：解析目标通道与时钟，复位并关闭计数、PWM、Capture和IRQ，读取初始COUNT.LIVE。
    - 配置边界读回：停止时逐一写入周期和divider矩阵，读取TIMEBASE.PERIOD_LIMIT及DIVIDER并与适配后的输入逐项比较。
    - 计数启动采样：切换到长周期并清零，使能模块及计数器，在两个相隔观察窗的时点读取COUNT.LIVE。
    - 计数快照锁存：发出锁存并读取COUNT.LATCHED，保持运行一个观察窗，再同时采集实时计数和原锁存值。
    - 停止保持检查：关闭计数器，确认停止动作完成后连续两个观察窗读取COUNT.LIVE，要求两值相同。
    - 非零计数清除：确认停止值非零后清零，在有界deadline内读取COUNT.LIVE为零，重新启动并再次读取非零计数。
    - 通道结果汇总：保存配置读回和各阶段原始计数，逐参数核对推进、保持、锁存和清零条件，再停止本通道。
  observations:
    - 配置实际字段：TIMEBASE.PERIOD_LIMIT和DIVIDER分别等于目标适配后的输入，证明字段可保存，不代表该边界周期已经运行完成。
    - 实时计数变化：COUNT.LIVE在运行窗递增、停止窗保持、清零后为零、重启后非零，证明启停和清零作用。
    - 锁存计数保持：COUNT.LATCHED在显式锁存后处于相邻实时采样的有界区间，后续实时计数推进时锁存值不变。
  pass_criteria:
    - 参数执行完整：所有已声明逻辑通道、divider和周期配置点均执行，任何遗漏必须报告未执行而不是PASS。
    - 计数阶段正确：无回卷窗口内运行计数增加，停止后两次值相等，清零后为零且重启后增加。
    - 锁存读回正确：锁存值处于采样上下界内且在下一次显式锁存前保持，全部配置读回等于Expected。
timeout: 每参数实例5秒，Firmware单等待不超过1秒；按矩阵实例分别计时。
cleanup: [停止计数及PWM和Capture, 禁用并清除本通道IRQ, 释放逻辑通道并恢复隔离状态]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外接线, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [canonical result及逐阶段计数Observation, 配置矩阵和目标侧等待Tick记录]
failure_observations:
  - {key: live_count, label: 实时计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_live}
  - {key: latched_count, label: 锁存计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_latched}
  - {key: expected_limit, label: 期望周期终值, source: oracle, role: expected, format: hex32}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_001
case_name: PWM模式与时基数字环回矩阵
report_feature: |-
  1. ETIM 计数预分频
  2. ETIM 可编程周期
  3. ETIM PWM A比较模式
  4. ETIM PWM A+B比较模式
p_level: P1
feature_refs: [ETIM_F_002, ETIM_F_003, ETIM_F_006, ETIM_F_007]
method:
  inputs:
    - 波形参数矩阵：每条已确认的PWM到Capture内部路由，覆盖A和A_B模式；period_ticks取1000、3001、8000，A模式高宽取约四分之一、二分之一、四分之三周期，A_B取A约四分之一且B约四分之三周期。
    - 分频覆盖矩阵：对period_ticks为1000的两种模式遍历全部合法源divider，其余周期使用最小、中间、最大合法divider；捕获端固定最小divider、输入预分频旁路及滤波旁路。
    - 数字时间Oracle：由输入周期、比较时刻及独立时钟映射计算期望高宽、低宽和周期，要求全部间隔远大于capture_error_ticks且小于捕获回卷长度。
  steps:
    - 路由与时钟确认：解析互不冲突的生产者和捕获者，确认内部PWM路由及延迟旁路成立，记录双方时钟与量化误差上界。
    - PWM停止配置：停止两通道，配置源时基及当前A或A_B比较点，关闭Fault、同步加载和影子更新，确认本轮稳定配置读回。
    - 捕获准备：接收端使用长周期、绝对时间戳及RISING/FALLING/RISING/FALLING四槽One-Shot，清除旧pending并先武装接收端。
    - 波形启动等待：启动PWM源，在最多十个源周期加传输余量的deadline内等待第四槽捕获事件。
    - 时间戳现场读取：停止源并读取四槽CAPTURE.VALUE和末槽IRQ_RAW，保留本次完成身份及逐槽原始值。
    - 波形间隔比较：按模减计算高宽、低宽和周期，与输入和时钟关系得到的Expected逐项比较，禁止用源配置读回代替实际捕获。
    - 矩阵结果汇总：每个路由和参数独立保留Expected、Actual和误差上界，所有有效实例满足判据才通过该Case。
  observations:
    - 捕获完成事件：末槽IRQ_RAW有效，证明本次四个指定边沿已经到达，不使用历史CAP值判断完成。
    - 实际PWM时间戳：CAPTURE.VALUE各槽提供实际边沿时刻，差值对应高宽、低宽和完整周期。
  pass_criteria:
    - 波形间隔正确：每个实测高宽、低宽和周期与独立Expected之差不超过已声明capture_error_ticks。
    - 模式与矩阵完整：两模式及全部规定分频、周期、占空配置和已确认路由均完成，A_B高宽使用B减A而不是A。
    - 证据边界明确：该Case只给数字环回结论，不给绝对频率、引脚输出和极限脉宽结论。
timeout: 每实例最多十个源周期加2秒，总上限10秒；超出上限的参数不进入该普通矩阵。
cleanup: [先停止PWM生产者, 停止并撤销Capture, Disable并Clear本轮IRQ, 释放内部路由和两通道]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 已确认的IP内部PWM到Capture路由}
backend: [FPGA, Silicon]
evidence: [逐槽CAPTURE.VALUE Observation, 逻辑路由及PWM参数和时钟Oracle Artifact]
failure_observations:
  - {key: capture_value, label: 当前槽时间戳, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: expected_interval, label: 期望间隔Tick, source: oracle, role: expected, format: decimal}
  - {key: actual_interval, label: 实测间隔Tick, source: measurement, role: actual, format: decimal}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_002
case_name: 绝对时间戳与捕获极性
report_feature: |-
  1. ETIM 捕获边沿选择
  2. ETIM 绝对捕获时间戳
p_level: P1
feature_refs: [ETIM_F_009, ETIM_F_010]
method:
  inputs:
    - 捕获极性矩阵：遍历所有逻辑捕获通道，分别配置RISING/FALLING/RISING/FALLING、FALLING/RISING/FALLING/RISING和四个同极性槽，全部槽不清计数器。
    - 非对称刺激：内部PWM周期8000个源Tick、高宽2400个源Tick，输入预分频及滤波旁路，源和接收divider选择使Expected差值为整数。
  steps:
    - 捕获资源准备：选择与DUT不同的内部PWM生产者，解析时钟和路由，复位相关通道并关闭所有旧IRQ。
    - 非对称源配置：在停止状态配置PWM的8000周期及2400高宽，记录预期上升到下降、下降到上升和同极性间隔。
    - 绝对捕获配置：DUT配置长周期和当前四槽极性，全部clear_after_capture为false，使用四槽One-Shot并清除旧捕获pending。
    - 先收后发启动：先启动接收计数及Capture，再启动PWM，在十个源周期内等待末槽完成。
    - 绝对数据读取：停止源后逐槽读取CAPTURE.VALUE及末槽IRQ_RAW，保留首槽时间戳但不把启动软件延迟作为Oracle。
    - 极性间隔判定：相邻槽做模减并按当前边沿序列比较高宽、低宽或整周期，同极性三段应对应相同周期。
    - 全通道汇总：逐个逻辑捕获通道和极性序列保存完成状态及差值，结束会话后释放资源。
  observations:
    - 四槽时间戳：CAPTURE.VALUE保持绝对计数语义，相邻差值能区分2400高宽与5600低宽，避免对称波形掩盖极性错误。
    - 本轮末槽pending：IRQ_RAW.CAPTURE_4在启动前为零、完成后为一，证明数据属于本轮捕获。
  pass_criteria:
    - 边沿次序正确：每一相邻差值等于对应边沿间隔并落在声明误差内，不能只比较总周期。
    - 捕获矩阵完整：所有逻辑捕获通道和四种极性序列完成；每次必须有本轮末槽完成事实。
timeout: 每实例十个源周期加2秒，最长10秒。
cleanup: [停止PWM源, 停止Capture及计数器, 清除本轮捕获pending, 释放通道与路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部PWM源及已确认时钟关系}
backend: [FPGA, Silicon]
evidence: [四个独立槽Observation和本轮完成状态, 极性序列及Expected间隔Artifact]
failure_observations:
  - {key: capture_value, label: 槽实际时间戳, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: expected_interval, label: 期望边沿间隔, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_003
case_name: 相对时间戳与逐槽清零
report_feature: |-
  1. ETIM 捕获边沿选择
  2. ETIM 相对捕获时间戳
p_level: P1
feature_refs: [ETIM_F_009, ETIM_F_011]
method:
  inputs:
    - 清零组合矩阵：各逻辑捕获通道使用RISING/FALLING/RISING/FALLING；逐槽清零数组分别为全true、仅首槽true、仅次槽true，并增加四个RISING且全true以及四个FALLING且全true。
    - 刺激与Oracle：周期8000、高宽2400的内部PWM；首槽之前的软件启动间隔不判定，后续Expected从最近一次清零槽或可相减的绝对槽计算。
  steps:
    - 资源与预期建立：解析内部PWM路由、计数宽度和时钟比例，根据边沿及清零数组生成每槽时间关系表。
    - 停止配置两端：配置非对称PWM和捕获长周期，禁用滤波及输入预分频，设置当前四槽极性及独立clear_after_capture。
    - 会话清理武装：清除旧pending，先启动捕获端四槽One-Shot，再启动PWM源。
    - 末槽完成等待：在十个源周期的目标侧边界内等待末槽pending，不因前面槽已完成提前读取结论。
    - 逐槽结果采集：停止源后读取四个CAPTURE.VALUE及末槽完成pending，保留原始值而不是只返回计算后脉宽。
    - 清零关系比较：全清零时后续槽值应反映相邻间隔；仅首槽清零时后续值应累积；仅次槽清零时末两槽应相对次槽，按量化上界逐项比较。
    - 参数清理汇总：记录每槽最近清零事件和Expected来源，完成全部通道与清零组合后恢复隔离状态。
  observations:
    - 相对槽实际值：CAPTURE.VALUE次槽至末槽随独立清零组合表现为单段或累积间隔，证明不是软件统一减首槽伪造相对时间戳。
    - 末槽捕获状态：本轮IRQ_RAW.CAPTURE_4有效，确保所比较的后续槽已经加载。
  pass_criteria:
    - 清零组合正确：每个可判定槽与最近清零事件的Expected时间关系一致，误差不超过声明上界。
    - 极性通道完整：所有规定组合均完成，首槽不确定启动延迟不得参与通过判据。
timeout: 每实例十个源周期加2秒，最长10秒。
cleanup: [停止PWM源和Capture, 禁用并清除捕获IRQ, 释放通道与路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部PWM源及已确认时钟关系}
backend: [FPGA, Silicon]
evidence: [逐槽硬件时间戳Observation, clear_after_capture数组及逐槽Expected来源]
failure_observations:
  - {key: relative_count, label: 槽实际捕获计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: expected_count, label: 期望相对计数, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P0_002
case_name: IRQ强制、屏蔽、选择清除与投递
report_feature: |-
  1. ETIM 中断Force/Clear
  2. ETIM 中断Mask/Unmask
  3. ETIM 中断Enable/Disable
p_level: P0
feature_refs: [ETIM_F_017, ETIM_F_018, ETIM_F_019]
method:
  inputs:
    - 中断源矩阵：每逻辑通道逐一测试全部合法IRQ源，再取目标源与另一不同源构造双pending，所有自然事件生产者保持停止。
    - 投递观察窗口：使用目标侧10毫秒静默窗和1秒投递deadline，Service首次ISR保存现场后关闭该源，禁止计数重复电平IRQ作为多次事件。
  steps:
    - 中断会话准备：复位通道并停止自然事件，绑定本轮ISR会话，使能待测源、全部Mask并Clear，确认目标RAW和STATUS为零。
    - 屏蔽状态强制：Force目标源，读取目标IRQ_RAW为一和IRQ_STATUS为零，并确认静默窗内没有ISR投递。
    - 双源选择清除：再Force保留源，确认两源RAW均为一，仅Clear目标源，确认目标RAW归零而保留源RAW仍为一。
    - 解屏蔽投递：重新Force目标源并Unmask目标源，等待真实ISR，保存ISR首次来源及清除前目标RAW和STATUS。
    - 禁用投递检查：停止会话并Disable目标源，Clear后再次Force目标源，保持Unmask，在静默窗确认没有新增ISR；不由此推断RAW的Enable门控位置。
    - 清除恢复验证：重新Mask全部源并Clear所有已Force的pending，读取目标与保留源RAW归零，再结束本轮会话。
    - 源矩阵汇总：逐通道逐源比较各阶段pending和Service投递事实，保留双源选择清除证据；不将Force结果扩写为自然Fault或溢出通过。
  observations:
    - 原始pending变化：IRQ_RAW目标源经历零到一再到零，选择Clear不清除保留源，证明强制和按源清除。
    - 有效pending变化：Mask时IRQ_STATUS目标源为零，Unmask且Enable时ISR现场为一，证明屏蔽作用。
    - 实际IRQ投递：ISR首次来源包含目标源，屏蔽或Disable窗口事件计数不增加；此项为服务事实而非寄存器。
  pass_criteria:
    - pending关系正确：每源Force和Clear均形成规定前后状态，双源测试只清目标源。
    - IRQ投递正确：Enable且Unmask后在deadline内进入真实ISR，Mask或Disable窗口无投递。
    - 覆盖与清理完整：每通道每合法源完成且最终所有本轮pending清零，不遗留活跃IRQ。
timeout: 每通道每源5秒；目标侧投递等待最长1秒。
cleanup: [停止IRQ会话, Mask并Disable全部本轮源, 停止事件生产者后Clear pending, 释放IRQ绑定]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外接线, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [canonical逐源逐阶段RAW及STATUS, ISR首次现场与事件计数Measurement]
failure_observations:
  - {key: irq_raw, label: 目标源RAW, source: dut, role: actual, format: bool, semantic_ref: etim.feature.irq_raw}
  - {key: irq_status, label: 目标源STATUS, source: dut, role: actual, format: bool, semantic_ref: etim.feature.irq_status}
  - {key: first_source, label: ISR首次来源, source: service, role: actual, format: text}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_004
case_name: One-Shot、Continuous及Rearm
report_feature: |-
  1. ETIM 捕获One-Shot
  2. ETIM 捕获Continuous
  3. ETIM 捕获Rearm
p_level: P1
feature_refs: [ETIM_F_013, ETIM_F_014, ETIM_F_015]
method:
  inputs:
    - 模式槽数矩阵：每捕获通道分别使用ONE_SHOT和CONTINUOUS，stop_after从1遍历到4；全部槽为上升沿、绝对时间戳，输入预分频及滤波旁路。
    - 持续输入波形：内部PWM周期8000源Tick、高宽2400源Tick；捕获计数周期大于整个观察窗，第一轮完成后继续输入至少八个源周期。
  steps:
    - 初始快照保存：隔离生产者和接收者，设置长周期及当前槽数，保存全部槽旧值并清除pending。
    - 本轮捕获启动：先武装接收端再启动PWM，等待第stop_after槽pending出现，立即读取有效槽值和CAPTURE.NEXT_SLOT。
    - 冻结或环绕观察：保持刺激至少八个源周期，再次读取所有槽；One-Shot有效槽必须保持，Continuous首槽必须刷新，未纳入序列的槽不得被本轮加载。
    - Rearm前停止刺激：仅One-Shot分支先停止生产者，确认没有新输入后清pending，发出Rearm并读取CAPTURE.NEXT_SLOT回到首槽。
    - 第二轮重新捕获：One-Shot分支重启源并等待末有效槽完成，读取第二轮有效槽；Continuous分支在新的观察窗再次读取首槽以证明持续更新。
    - 模式关系判定：比较冻结前后、Rearm前后和Continuous多窗口原始数据，要求第二轮时间戳属于更晚计数时刻且不沿用第一轮完成状态。
    - 槽数通道汇总：执行全部通道与模式槽数组合，记录每阶段完成事件和数据身份后停止两端。
  observations:
    - 有效槽保持或刷新：CAPTURE.VALUE在One-Shot后续刺激下不变，在Continuous相隔多周期窗口变化，证明冻结和环绕加载不同。
    - Rearm槽状态：无刺激时CAPTURE.NEXT_SLOT在Rearm后指向首槽，随后第二轮末槽pending重新产生且CAP值更新。
  pass_criteria:
    - 模式结果正确：One-Shot保持全部有效槽，Continuous至少首槽连续两窗口刷新，序列外槽保持初始值。
    - 重新武装有效：每个One-Shot槽数均从首槽开始新一轮并获得新的末槽事件和时间戳。
    - 矩阵覆盖完整：全部通道的两模式及四个槽数均满足判据，无跨计数回卷比较。
timeout: 每实例5秒；各观察窗按源周期计算且Firmware单等待不超过1秒。
cleanup: [停止PWM生产者, 停止Capture和计数器, 禁用并清除本轮IRQ, 释放两通道]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部PWM到Capture路由}
backend: [FPGA, Silicon]
evidence: [逐槽逐阶段CAPTURE.VALUE, CAPTURE.NEXT_SLOT及末有效槽RAW, 模式和槽数参数Artifact]
failure_observations:
  - {key: capture_value, label: 当前槽捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: next_slot, label: 下一捕获槽, source: dut, role: actual, format: decimal, semantic_ref: etim.feature.capture_next_slot}
  - {key: expected_relation, label: 期望保持或刷新关系, source: oracle, role: expected, format: text}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_005
case_name: 捕获输入预分频矩阵
report_feature: |-
  1. ETIM 捕获输入预分频
p_level: P1
feature_refs: [ETIM_F_012]
method:
  inputs:
    - 输入分频矩阵：每逻辑捕获通道遍历Capability声明的全部实际input_divider，包含旁路和最大倍数；计数divider固定不变。
    - 固定刺激参数：内部PWM周期1000源Tick、高宽300源Tick，四槽全部RISING且不清计数器，长周期足以覆盖四个最大分频后事件。
  steps:
    - 资源和倍率解析：选择独立PWM源，记录输入分频实际倍数集合及两端时钟，不把分频编码当作倍数。
    - 固定时基配置：停止两端后配置源1000周期及接收长周期，关闭滤波，保持计数divider在全部实例中一致。
    - 当前输入分频设置：配置本轮input_divider及四槽同极性One-Shot，清pending并先武装接收端。
    - 预分频捕获等待：启动源，在六个分频后周期内等待末槽捕获完成，最大分频使用按倍数计算的等待而不是固定短延时。
    - 捕获结果读取：停止源后读取四槽CAPTURE.VALUE及末槽RAW，记录实际计数divider读回以排除误改计数时钟。
    - 倍率Oracle比较：逐相邻槽计算差值，Expected为旁路输入周期乘实际input_divider再换算接收Tick，逐段按误差上界比较。
    - 分频通道汇总：确认所有倍率和通道均有三段有效差值，完成后清除本轮配置和会话。
  observations:
    - 分频后时间戳：CAPTURE.VALUE相邻差值随input_divider成比例变化，证明输入事件分频而非仅字段可写。
    - 计数时基读回：TIMEBASE.DIVIDER在全部实例中相同，排除由计数时钟变化伪装输入分频。
  pass_criteria:
    - 输入倍率正确：每段差值符合输入周期乘实际倍数的Expected，最大倍数与旁路均不例外。
    - 全矩阵完成：全部通道和合法倍率都有末槽完成事件及三段合格差值，计数divider未变化。
timeout: 每实例六个分频后周期加2秒，最长10秒。
cleanup: [停止PWM源, 停止Capture并清除pending, 释放通道与路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部PWM源及已确认时钟关系}
backend: [FPGA, Silicon]
evidence: [逐槽时间戳Observation, 实际输入倍率与计数divider读回, 独立Expected Artifact]
failure_observations:
  - {key: capture_value, label: 槽捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: expected_interval, label: 分频后期望间隔, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_006
case_name: 计数、PWM与Capture Load独立门控
report_feature: |-
  1. ETIM 计数与Enable/Disable
  2. ETIM PWM Enable/Disable
  3. ETIM Capture Load Enable/Disable
p_level: P1
feature_refs: [ETIM_F_001, ETIM_F_008, ETIM_F_016]
method:
  inputs:
    - 门控参数矩阵：对已确认的内部PWM路由分别控制生产者TIMER、生产者PWM及接收者CAPTURE_LOAD，每次只改变一个门控位。
    - 持续观察配置：源周期8000且高宽2400，接收者使用长周期、单槽RISING绝对时间戳Continuous，观察窗至少八个源周期且不回卷。
  steps:
    - 两端基线建立：配置并启动PWM及Capture，取得相隔两个源周期的CAPTURE.VALUE首槽，确认真实数据持续刷新。
    - 当前门控关闭：仅关闭本轮TIMER、PWM或CAPTURE_LOAD，读取对应ENABLE字段；等待一个源周期排除切换瞬间边沿。
    - 关闭窗口采样：在两个相隔观察窗的时点采集首槽时间戳及生产者COUNT.LIVE，其他Enable保持原值。
    - 停止关系判定：TIMER关闭时生产者计数保持且接收数据不刷新；PWM关闭时生产者计数推进但接收不刷新；CAPTURE_LOAD关闭时生产者计数推进但CAP值保持。
    - 门控恢复启动：恢复当前Enable，忽略第一个可能不完整的周期，等待至少四个完整周期后读取新的捕获数据。
    - 恢复间隔测量：转为四槽同极性One-Shot取得恢复后的周期，比较原时基Expected并确认未被门控动作改写。
    - 门控实例汇总：每路由每门控保留前、关闭、恢复阶段数据；不推断PWM关闭时具体高低电平。
  observations:
    - 独立Enable读回：当前ENABLE字段关闭再恢复，其他字段不变，证明没有通过全模块复位替代被测门控。
    - 计数与捕获关系：COUNT.LIVE和CAPTURE.VALUE首槽分别表明计数是否推进、输出边沿是否继续加载。
    - 恢复PWM周期：恢复后实际捕获周期等于原Expected，证明可继续工作而不是仅Enable读回成功。
  pass_criteria:
    - 门控行为正确：三个分支各自满足关闭窗口计数和CAP保持关系，切换瞬间不参与稳态无边沿判据。
    - 恢复结果正确：Enable恢复后有新捕获值且稳定周期在原Expected误差内，所有已确认路由完成。
timeout: 每门控实例5秒，单观察窗最长1秒。
cleanup: [停止生产者, 停止接收者, 恢复本轮门控为安全关闭状态, 禁用清除IRQ并释放路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部PWM到Capture路由}
backend: [FPGA, Silicon]
evidence: [逐阶段独立Enable及COUNT.LIVE和CAPTURE.VALUE, 恢复后周期Measurement]
failure_observations:
  - {key: enable_state, label: 当前门控状态, source: dut, role: actual, format: bool, semantic_ref: etim.feature.selected_enable}
  - {key: live_count, label: 源实时计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_live}
  - {key: capture_value, label: 接收首槽值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_007
case_name: Compare、Period与Capture自然IRQ
report_feature: |-
  1. ETIM 中断Enable/Disable
  2. ETIM Compare/Period中断
  3. ETIM Capture中断
p_level: P1
feature_refs: [ETIM_F_019, ETIM_F_020, ETIM_F_021]
method:
  inputs:
    - 自然中断矩阵：每通道依次测试COMPARE_A、COMPARE_B、PERIOD及CAPTURE_1到CAPTURE_4，不使用IRQ Force；Fault及真正计数回卷另属待确认项。
    - 有界事件配置：计数源配置长于ISR响应上界的周期，A约四分之一且B约四分之三周期；捕获分支采用内部PWM四槽上升沿One-Shot，只有当前源Enable且Unmask。
  steps:
    - IRQ会话隔离：停止自然事件并清除所有pending，绑定本轮逻辑通道ISR，确认目标RAW、STATUS和事件计数初值。
    - 被测事件配置：比较及周期分支配置计数时基和A_B内部比较点；捕获分支配置独立PWM源及四槽One-Shot，全部配置在停止时完成。
    - 自然事件启动：Enable并Unmask当前源，启动相应计数器或先收后发捕获链，禁止调用Force。
    - ISR首次现场等待：在deadline内等待真实ISR，ISR先锁存目标RAW、STATUS和来源，再关闭该源投递，不把PC轮询pending当作ISR成功。
    - 生产者停止取证：停止计数或PWM源，读取会话首次现场及当前捕获槽值，确认捕获分支确实发生了目标槽加载。
    - pending清除复核：在生产者停止后Clear当前源，读取目标RAW归零并确认Disable后静默窗无新增投递。
    - 自然源逐项汇总：每通道每源核对真实首次来源、硬件pending及清理状态，不要求周期性电平IRQ服务次数等于硬件事件次数。
  observations:
    - 自然源硬件pending：ISR清除前IRQ_RAW和IRQ_STATUS当前源为一，证明该自然事件建立有效pending。
    - 捕获端硬件数据：捕获分支目标CAPTURE.VALUE已有本轮数据，支撑Capture IRQ来自加载事件。
    - 投递与清除事实：ISR首次来源为当前源，生产者停止并Clear后目标RAW归零，Disable静默窗无新增服务事件。
  pass_criteria:
    - 自然投递成立：每实例无需Force即可在deadline内进入真实ISR且首次现场包含目标源RAW及STATUS。
    - 清除隔离正确：停止源后Clear使目标RAW为零，关闭投递后事件计数不增加，无遗留IRQ。
    - 自然源覆盖完整：全部通道的两比较源、周期源和四捕获源均完成，不能由Force Case代替。
timeout: 每通道每源5秒，目标侧事件等待不超过1秒。
cleanup: [停止本轮计数器及PWM源, 关闭IRQ会话并Disable及Mask, Clear pending, 释放IRQ与捕获资源]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 捕获分支需要内部PWM源}
backend: [FPGA, Silicon]
evidence: [ISR首次逐源RAW及STATUS现场, Service首次来源与事件计数, 捕获槽原始值]
failure_observations:
  - {key: irq_raw, label: 自然源RAW, source: dut, role: actual, format: bool, semantic_ref: etim.feature.irq_raw}
  - {key: irq_status, label: ISR现场STATUS, source: dut, role: actual, format: bool, semantic_ref: etim.feature.irq_status}
  - {key: first_source, label: ISR首次来源, source: service, role: actual, format: text}
gap: [case_implementation_gap, verified_route_and_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_008
case_name: A+B非法比较配置与恢复
report_feature: |-
  1. ETIM COMPA≥COMPB配置错误
p_level: P1
feature_refs: [ETIM_F_022]
method:
  inputs:
    - 比较关系矩阵：各逻辑通道使用A_B模式和period_ticks为8000，依次测试A为2000且B为6000、A与B均4000、A为6000且B为2000。
    - 错误观测设置：只Enable并UnmaskCOMPARE_ERROR，其余IRQ屏蔽；关闭PWM对外输出、Fault和影子加载，保留计数运行以满足事件检测。
  steps:
    - 合法基线配置：隔离通道并以A小于B配置，清除旧错误pending，Enable当前错误源并启动计数。
    - 无错误窗口观察：等待两个完整周期，读取IRQ_RAW.COMPARE_ERROR和IRQ_STATUS.COMPARE_ERROR，要求均为零。
    - 非法关系施加：暂停计数后分别写入A等于B或A大于B，重新启动，在两个周期内等待自然配置错误pending。
    - 错误前后取证：读取目标RAW及STATUS为一并记录本轮比较输入，不使用Force制造配置错误证据。
    - 合法关系恢复：停止计数，恢复A小于B，然后Clear错误pending，读取目标RAW及STATUS归零。
    - 恢复无错验证：重新运行两个周期后再次读取错误RAW和STATUS，确认没有重新置位，停止本通道。
    - 全通道错误汇总：每通道的等于及大于分支均保留基线、错误、恢复三阶段事实，非法配置不用于证明PWM波形。
  observations:
    - 配置错误原始状态：IRQ_RAW.COMPARE_ERROR在合法关系为零、非法关系为一、修正并Clear后为零。
    - 配置错误有效状态：Enable且Unmask时IRQ_STATUS.COMPARE_ERROR与上述阶段相符，证明错误不是始终屏蔽的旧pending。
  pass_criteria:
    - 非法关系检测：每通道A等于B及A大于B均自然产生错误，A小于B基线不产生。
    - 恢复结果正确：先修正配置再Clear后错误归零，重新运行两个周期不复发，全部通道完成。
timeout: 每通道5秒，目标侧各阶段最多两个配置周期加100毫秒。
cleanup: [停止计数, 恢复合法比较值, Mask及Disable错误IRQ后Clear, 保持PWM输出关闭]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外接线, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [COMPARE_ERROR逐阶段RAW及STATUS, A与B输入关系Artifact]
failure_observations:
  - {key: config_error_raw, label: 配置错误RAW, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.compare_error}
  - {key: expected_error, label: 期望错误状态, source: oracle, role: expected, format: bool}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_001
case_name: 外部时间基准PWM频率与占空比
report_feature: |-
  1. ETIM 计数预分频
  2. ETIM 可编程周期
  3. ETIM PWM A比较模式
  4. ETIM PWM A+B比较模式
p_level: P2
feature_refs: [ETIM_F_002, ETIM_F_003, ETIM_F_006, ETIM_F_007]
method:
  inputs:
    - 外部波形矩阵：对Bench声明可独立观测的PWM输出使用A和A_B模式，周期分别选为约0.1毫秒、1毫秒、5毫秒的整数Tick，A模式高宽约25%、50%、75%，A_B使用约25%到75%的高区间。
    - 仪器时间基准：使用已校准示波器或时间间隔分析仪，记录时基精度、采样间隔、阈值和探头条件；Expected来自源时钟声明及分频配置，不从DUT捕获反推。
    - 误差预算：周期和高宽的允许误差分别由时钟容差、仪器时基容差及两边沿采样误差上界相加得到，运行前固定，不按实测偏差放宽。
  steps:
    - 人工门禁与接线：确认目标板、输出端点、共地、允许电平及仪器输入规格，取得本次硬件门禁后连接并保存Bench身份。
    - 仪器基准设置：选择安全量程、测量阈值和至少能分辨最短高宽的采样率，读回设置并记录校准与时间精度信息。
    - PWM停止配置：按当前参数配置时基与比较模式，禁用Fault、同步及延迟反相处理，确认合法内部比较点后启动输出。
    - 稳态波形捕获：丢弃最初两个周期，使用独立外部Observer连续采集至少32个完整周期和高区间，保存原始波形。
    - 外部时间提取：从实测上升及下降时刻提取每周期长度、高宽、低宽及缺边沿事实，不以仪器设定值代替波形。
    - 独立时间比较：逐周期将实测周期和高宽与配置换算的Expected及预先固定的误差预算比较，同时检查没有缺失或额外边沿。
    - 参数恢复汇总：逐端点逐参数记录外部证据，停止PWM并将输出置于Bench规定安全状态后结束测量。
  observations:
    - 引脚实际边沿：PWM_OUTPUT.EDGE_TIMES附件包含至少32个完整周期的真实边沿，直接证明引脚波形而非内部配置。
    - 外部周期与高宽：由外部时间基准提取的每周期及高宽落在Expected误差预算内，证明普通工作点的绝对时间和占空比。
  pass_criteria:
    - 外部时间符合：每一有效周期和高宽均在预先固定的误差预算内，边沿序列无额外或缺失脉冲。
    - 波形矩阵完整：全部声明输出端点和普通参数完成，不把未确认的最高频率、最小脉宽或电气精度限值计入通过。
timeout: 每输出参数10秒，仪器单次采集等待最多5秒。
cleanup: [停止PWM输出, 恢复Bench安全输出状态, 停止仪器采集并释放会话, Disable并Clear本轮IRQ]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认的PWM输出端点及共地, bench: 已校准示波器或时间间隔分析仪和合适探头}
backend: [FPGA, Silicon]
evidence: [独立外部原始波形附件, 每周期与高宽Measurement, 预先固定误差预算和仪器身份]
failure_observations:
  - {key: measured_period, label: 外部实测周期秒, source: instrument, role: actual, format: float}
  - {key: measured_high_time, label: 外部实测高宽秒, source: instrument, role: actual, format: float}
  - {key: expected_period, label: 期望周期秒, source: oracle, role: expected, format: float}
gap: [case_implementation_gap, external_output_bench_mapping_gap, clock_accuracy_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_002
case_name: 外部脉冲周期与脉宽捕获
report_feature: |-
  1. ETIM 捕获边沿选择
  2. ETIM 绝对捕获时间戳
  3. ETIM 相对捕获时间戳
p_level: P2
feature_refs: [ETIM_F_009, ETIM_F_010, ETIM_F_011]
method:
  inputs:
    - 外部脉冲矩阵：信号源产生周期0.1毫秒、1毫秒、5毫秒且占空比25%或75%的脉冲列，各已确认输入路由覆盖四槽RISING/FALLING/RISING/FALLING的绝对及全相对模式。
    - 独立刺激观测：外部Observer在DUT输入端实测刺激边沿，输入电平、阈值及带宽由Bench确认；期望值来自实测刺激间隔乘接收计数频率。
    - 误差及量程：运行前固定计数时钟容差、捕获量化误差和外部测量误差，最长测量间隔小于一次计数回卷；不声明最大捕获时长或分辨率极限。
  steps:
    - 门禁与输入连接：人工确认板卡、接收端点、共地和允许电平后连接信号源及外部Observer，保持信号源输出关闭。
    - 刺激测量准备：配置当前周期与占空比及Observer采样，读回设置并固定误差预算，避免仅凭信号源面板值建立Oracle。
    - 捕获端武装：配置DUT长周期、输入分频旁路、滤波旁路、四槽One-Shot及当前绝对或相对模式，清pending并先启动接收。
    - 外部刺激与采集：启动外部波形并同步保存DUT输入端真实边沿，在十个刺激周期内等待DUT末槽完成。
    - 结果及刺激读取：关闭信号源后读取逐槽CAPTURE.VALUE和末槽RAW，同时取得覆盖本轮捕获窗的外部边沿附件。
    - 独立间隔判定：绝对模式做相邻模减，相对模式舍弃首槽后比较后续槽；高宽、低宽和周期Expected由外部实测刺激换算，逐项应用固定误差预算。
    - 输入矩阵汇总：逐输入路由、周期、占空比及时间戳模式保存完整证据，结束后恢复安全输入和释放仪器。
  observations:
    - 实际输入端刺激：STIMULUS_OUTPUT.EDGE_TIMES包含DUT端真正收到的高低间隔，避免源设定误差或接线异常被归为捕获误差。
    - DUT捕获时间戳：逐槽CAPTURE.VALUE及本轮末槽pending证明真实加载，不能用PC计算结果代替硬件捕获值。
  pass_criteria:
    - 捕获时间正确：高宽、低宽及周期对应外部刺激的实测时间，换算误差不超过预先固定预算。
    - 路由模式完整：全部声明输入路由和普通脉冲参数在两时间戳模式下完成，首槽启动延迟不作相对模式Oracle。
timeout: 每参数10秒，DUT等待最多十个刺激周期加1秒，仪器采集最多5秒。
cleanup: [先关闭外部信号源, 停止Capture及计数器, 禁用清除本轮IRQ, 恢复输入安全状态并释放仪器]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认的外部Capture输入路由及共地, bench: 信号源及已校准示波器或时间间隔分析仪}
backend: [FPGA, Silicon]
evidence: [DUT端外部刺激原始波形, 逐槽CAPTURE.VALUE及末槽RAW, 误差预算和独立Expected]
failure_observations:
  - {key: capture_value, label: 槽实际捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: measured_input_interval, label: 实测输入间隔秒, source: instrument, role: actual, format: float}
  - {key: expected_ticks, label: 期望捕获Tick, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, external_input_bench_mapping_gap, clock_accuracy_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_009
case_name: 周期立即与Shadow运行更新
report_feature: |-
  1. ETIM 周期Shadow加载
  2. ETIM 运行中立即加载
p_level: P1
feature_refs: [ETIM_F_023, ETIM_F_025]
method:
  inputs:
    - 周期更新矩阵：period_ticks在8000与12000之间双向切换，A固定1000；IMMEDIATE和PERIOD_BOUNDARY各执行一次，写入窗口选本周期计数2000至3000，远离新旧终点。
    - 独立时间依据：Capture计数时钟比和误差界由映射提供，接收器保存更新前至少两个、过渡一个及更新后至少三个完整周期；不得靠修改误差接纳第三种周期。
  steps:
    - 路由和时序准备：选择独立内部Capture Observer，配置源A模式及接收绝对捕获，关闭同步、Fault和延迟，建立新旧周期Expected。
    - 旧周期基线采集：先武装接收者再启动源，取得至少两个完整旧周期，确认本轮输入确实为旧配置。
    - 更新方式设置：保持源运行，单独选择周期立即或周期Shadow模式，记录配置读回但不据此判定加载已生效。
    - 安全窗口写入：Firmware在本周期计数2000至3000内写新周期，记录写入前后COUNT.LIVE及周期事件身份，窗口跨界则本次为执行错误。
    - 过渡波形采集：持续记录更新所在周期和至少三个后续周期，捕获丢边、超时或会话数据缺失必须失败关闭。
    - 新旧周期比较：立即模式更新所在周期应为新周期，Shadow模式该周期仍为旧周期且下一周期起为新周期；按独立时钟换算逐段比较。
    - 双向结果汇总：完成两模式与两更新方向四个实例，保存窗口、原始边沿和分段Expected后停止源及接收者。
  observations:
    - 写入时刻计数：COUNT.LIVE写前写后均在安全窗口且未跨周期，证明不是停止后配置或在边界后才写入。
    - 过渡边沿时间：CAPTURE.VALUE序列形成完整周期，当前与下一周期的长度区分立即和Shadow，不从配置读回猜生效值。
  pass_criteria:
    - 加载周期正确：四实例的过渡周期分别满足立即用新值、Shadow保留旧值，后续三周期均为新值且误差不超过映射界。
    - 采集证明完整：更新前、更新窗口、过渡和更新后的硬件证据齐全，无丢失边沿、额外周期或截止时间违规。
timeout: 每实例5秒；目标更新窗口等待最多三个旧周期，捕获最长十个较长周期。
cleanup: [停止PWM和Capture, 关闭Shadow并恢复停止配置, 清除本轮pending, 释放内部路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 连续边沿采集且有丢边检测的内部Capture Observer}
backend: [FPGA, Silicon]
evidence: [写入前后独立COUNT.LIVE, 带周期身份的原始捕获序列, 新旧周期及分段Expected]
failure_observations:
  - {key: update_count, label: 写入时实际计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_live}
  - {key: transition_period, label: 过渡周期Tick, source: measurement, role: actual, format: decimal}
  - {key: expected_period, label: 期望过渡周期Tick, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, continuous_capture_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_010
case_name: 比较对提交与立即更新
report_feature: |-
  1. ETIM 比较对Shadow提交
  2. ETIM 运行中立即加载
p_level: P1
feature_refs: [ETIM_F_024, ETIM_F_025]
method:
  inputs:
    - 比较更新参数：A_B模式period_ticks为16000，旧A/B为6000/12000，新A/B为8000/14000；两对高宽相同而相位不同，必须比较边沿位置而不只比较高宽。
    - 提交对照矩阵：Shadow分支分别经历仅写A、再写B但不提交、最后提交三个阶段；IMMEDIATE分支在计数1000至2000内完成两值写入，早于全部比较点。
  steps:
    - 旧比较波形建立：配置旧A/B并启动独立内部边沿Observer，记录周期基准与旧上升、下降边沿，关闭其他输出处理。
    - Shadow半对写入：使能比较Shadow，在安全窗口只写新A且不提交，持续观察两个周期，确认输出仍使用完整旧对。
    - Shadow整对暂存：写新B但仍不提交，观察两个周期，记录暂存配置与UPDATE.COMMIT_PENDING，波形仍应为完整旧对。
    - 原子提交执行：在计数1000至2000内发出commit，记录写前后计数及提交标识，采集当前周期和之后三个周期的完整边沿。
    - 立即加载对照：重新建立旧基线，关闭比较Shadow，在同一安全窗口完成新A/B写入，不发Shadow提交，采集更新所在周期和后续波形。
    - 边沿模型比较：Shadow提交所在周期保持旧边沿，下一周期为新边沿且不存在混合对；立即模式当前周期即为新边沿，提交标识最终被硬件清除。
    - 更新证据汇总：保存各阶段完整A/B写序、计数窗口和原始边沿，逐阶段比较后停止源，不以高宽恰好相同掩盖相位错误。
  observations:
    - 比较输出边沿：CAPTURE.VALUE与周期基准形成A和B各自位置，未提交、提交前后及立即分支均有独立实际序列。
    - 提交实际标识：UPDATE.COMMIT_PENDING在提交后的有界观察结束时为零；标识可能被快速清除，不强求软件一定采到瞬态一，原子性由波形证明。
  pass_criteria:
    - 暂存不泄漏：仅写A和整对未提交阶段均保持旧A/B边沿；不能出现新A旧B等混合对。
    - 生效边界正确：Shadow从提交后的下一周期成对生效，立即分支从写入所在周期生效，所有边沿误差不超过独立映射界。
timeout: 每分支5秒，单阶段捕获最多六个源周期；无法完整采集时返回执行错误。
cleanup: [停止输出和Observer, 关闭比较Shadow, 清理pending并恢复停止状态, 释放通道]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 内部Capture及独立周期基准采集}
backend: [FPGA, Silicon]
evidence: [分阶段边沿Artifact, 各次写入顺序和计数窗口, 提交标识独立Observation]
failure_observations:
  - {key: commit_pending, label: 实际提交标识, source: dut, role: actual, format: bool, semantic_ref: etim.feature.commit_pending}
  - {key: actual_edge, label: 实际比较边沿Tick, source: measurement, role: actual, format: decimal}
  - {key: expected_edge, label: 期望比较边沿Tick, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, continuous_capture_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_011
case_name: 软件和周期同步相位装载
report_feature: |-
  1. ETIM 同步相位装载
  2. ETIM 软件与周期SyncOut
p_level: P1
feature_refs: [ETIM_F_026, ETIM_F_027]
method:
  inputs:
    - 同步参数矩阵：对所有已确认内部同步源到接收通道组合，源周期为16000 Tick、接收周期为1000000 Tick，phase_ticks为100000或300000；源模式覆盖SOFTWARE、PERIOD、DISABLED。
    - 计数区间Oracle：保持接收计数器运行，以独立映射的同步传播和读事务上界构造装载后相位附近区间；区间必须与未同步自由运行区间不相交，禁止用DUT结果拟合延迟。
  steps:
    - 两通道基线建立：停止配置源和接收者，关闭PWM及捕获加载，清零后启动计数，读取无同步时的接收COUNT.LIVE推进序列。
    - 相位和路由配置：设置当前phase_ticks和逻辑同步源，先保持输入关闭，读取SYNC.PHASE与INPUT_ENABLE确认实际配置。
    - 输入关闭对照：源产生一次软件或数次周期同步，读取接收计数，要求保持自由运行区间而不是跳到相位附近。
    - 同步装载触发：使能输入，软件分支显式触发一次，周期分支跨过源周期边界，DISABLED分支只运行源；记录源前后计数与接收计数。
    - 装载后计数读取：在传播及采样上界内取得COUNT.LIVE，周期源连续检查三轮，软件源再观察一个无新触发窗口以确认不是持续重装。
    - 相位区间判定：有效软件或周期同步后的值落入phase_ticks加已知经过Tick的区间，DISABLED及输入关闭值落入自由运行区间；软件单次后继续正常递增。
    - 路由矩阵汇总：每个相位和模式独立保存前后计数、触发身份与Expected区间，全部结束后关闭同步输入输出并停止两通道。
  observations:
    - 相位实际配置：SYNC.PHASE独立读回等于输入，作为装载Expected来源之一，但不代替实际计数跳变。
    - 接收计数现场：COUNT.LIVE在触发前后分别支持自由运行或相位装载区间，足以区分路由未通、重复加载和禁用无效。
  pass_criteria:
    - 装载与禁用正确：有效同步每次进入相位区间，两类禁用对照均不进入该区间，Expected区间必须预先确定且互不重叠。
    - 源模式正确：软件单次后自由推进，周期模式连续三次装载，全部已声明路由和两相位参数均有实际证据。
timeout: 每实例5秒；每次等待不超过三个源周期加1秒。
cleanup: [关闭接收同步输入, 关闭源同步输出, 停止两计数器, 清理本轮pending并释放路由]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 已确认的内部同步路由及有界目标侧采样}
backend: [FPGA, Silicon]
evidence: [逐阶段COUNT.LIVE Observation, SYNC.PHASE独立读回, 触发身份及区间Oracle]
failure_observations:
  - {key: live_count, label: 同步后实际计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_live}
  - {key: phase_value, label: 实际相位配置, source: dut, role: actual, format: hex32, semantic_ref: etim.parameter.phase_ticks}
  - {key: expected_interval, label: 期望计数区间, source: oracle, role: expected, format: text}
gap: [case_implementation_gap, sync_route_and_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_003
case_name: 软件Fault封波、重复输入与恢复
report_feature: |-
  1. ETIM CBC Fault封波
  2. ETIM One-Shot Fault封波
  3. ETIM Fault重复输入中断
p_level: P2
feature_refs: [ETIM_F_028, ETIM_F_029, ETIM_F_030]
method:
  inputs:
    - Fault模式矩阵：CBC和ONE_SHOT分别交叉强制LOW/HIGH；普通PWM周期16000 Tick、高宽4000 Tick，死区和反相旁路，软件Fault初始无效。
    - 周期触发约束：故障输入撤销和One-Shot Clear在同一周期的中间安全窗口完成，窗口宽度覆盖写操作上界；输出独立测量且不连接功率负载。
  steps:
    - 安全输出准备：绑定已确认旁路输出与仪器端点，断开危险负载，配置当前模式、强制电平和自然Fault IRQ，采集至少两周期正常PWM。
    - 故障输入激活：置软件Fault有效，保持跨过两个周期，记录模式IRQ_RAW、真实ISR锁存和外部输出，确认封波不是关闭PWM导致。
    - 保持期间重复输入：ONE_SHOT分支撤销再重施输入但不Clear；CBC分支在同一周期内短暂撤销再重施且不跨退出边界，读取新的FAULT_OVERFLOW pending。
    - 输入撤销观察：在安全窗口撤销Fault；CBC观察下个周期恢复，ONE_SHOT不Clear并跨两个周期，要求继续保持强制电平。
    - 单次模式清除：ONE_SHOT在输入持续无效的某周期安全窗口发Clear，保持至下个周期；CBC无需Clear，均在恢复后单独清IRQ pending。
    - 输出恢复比较：比较Fault稳定窗电平和恢复后的三个完整PWM周期，读取Clear前后自然IRQ现场；退出边界只按正常周期路径判定，不测试同时事件竞态。
    - 矩阵安全收尾：四个模式电平组合分别保留原始波形、自然pending和动作窗口，任何超时先停止PWM，再撤销Fault并执行平台隔离。
  observations:
    - 故障输出电平：FAULT_OUTPUT.LEVEL在稳定Fault窗等于配置LOW或HIGH，基线和恢复PWM均有真实边沿，证明封波与恢复。
    - 自然故障中断：IRQ_RAW对应CBC或ONE_SHOT源置位，Fault未退出时重复输入产生FAULT_OVERFLOW，IRQ Force未参与刺激。
  pass_criteria:
    - 封波恢复正确：四实例均保持指定电平，CBC撤销输入后恢复，ONE_SHOT撤销而未Clear仍保持且满足同周期Clear后恢复，恢复波形与原配置一致。
    - 中断来源正确：模式pending和重复输入overflow来自真实Fault刺激，单独IRQ Clear后对应pending清除；不能用IRQ Clear替代故障状态Clear。
timeout: 每实例10秒；Fault保持阶段最多四个源周期，仪器采集最长5秒，超时必须执行安全隔离。
cleanup: [停止PWM输出, 撤销软件Fault输入并清Fault状态, 禁用并清IRQ, 停止仪器采集并恢复板级安全状态]
resources: {minimum_level: R4, full_coverage_level: R4, board: 输出无功率负载且安全电平已确认, bench: 独立数字示波器及动作周期标记}
backend: [FPGA, Silicon]
evidence: [封波和恢复连续波形, 模式RAW与overflow RAW分别记录, Fault输入和Clear动作窗口]
failure_observations:
  - {key: fault_output, label: 实际Fault输出电平, source: instrument, role: actual, format: bool}
  - {key: fault_raw, label: 自然Fault原始中断, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.fault_raw}
  - {key: overflow_raw, label: 重复Fault原始中断, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.fault_overflow}
gap: [case_implementation_gap, external_output_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_004
case_name: 窗口滤波短脉冲抑制与长脉冲通过
report_feature: |-
  1. ETIM 窗口阈值滤波
p_level: P2
feature_refs: [ETIM_F_031]
method:
  inputs:
    - 窗口阈值矩阵：实际W/T取8/5、8/8、16/9、16/16，初始化为全零或当前低输入；采样预分频选最小、中间、最大已映射合法值，T始终严格大于W的一半。
    - 脉冲宽度构造：独立时钟映射给采样周期下上界Ts_min和Ts_max；短高脉冲宽度小于(T-1)*Ts_min并留仪器误差余量，长高低平台各大于2*W*Ts_max，跳过恰好阈值竞态但不删除该剩余需求。
  steps:
    - 刺激量程确认：绑定外部输入及已校准测量端，校验短脉冲在旁路捕获能力范围内，确认宽度误差不侵入短长判据边界。
    - 旁路基线捕获：先关闭滤波，依次输入短脉冲和长脉冲，要求各自有真实上升下降捕获，证明刺激到达而非断线导致后续无事件。
    - 窗口滤波配置：停止接收，在低输入下设置当前W/T和初始化选项，启用滤波并保持低至少2W个最慢采样周期，清理所有旧pending后武装One-Shot。
    - 短脉冲抑制观察：施加一次短高脉冲，再保持低平台超过2W个最慢采样周期，读取CAPTURE.NEXT_SLOT及对应IRQ_RAW，要求没有新上升捕获。
    - 长脉冲通过观察：不关闭滤波，施加长高再长低平台，在有界窗口等待上升和下降槽完成，读取两槽CAPTURE.VALUE及本轮pending。
    - 过滤行为比较：按输入实测波形证明短脉冲不足T个采样、长平台足以填满窗口；要求只长脉冲产生两种极性事件，不从未知精确延迟反推滤波正确。
    - 参数清理汇总：对每个W/T、初始化与采样设置重做旁路对照和滤波阶段，保存逐阶段槽状态、输入波形及时间界后停刺激。
  observations:
    - 短脉冲槽状态：CAPTURE.NEXT_SLOT及目标IRQ_RAW相对武装基线不变，结合旁路已成功捕获同类脉冲证明抑制成立。
    - 长脉冲捕获值：CAPTURE.VALUE上升与下降槽均有本轮加载事件，间隔落在输入长平台加减窗口传播上界内，证明不是只固定输出低。
  pass_criteria:
    - 抑制通过正确：每实例旁路可见短长脉冲，滤波后短脉冲无新捕获、长脉冲两个极性均捕获，不能仅以没有IRQ判通过。
    - 预期时间独立：采样周期界及仪器误差来自独立映射，全部刺激满足设计不等式；未映射的分频值不得用实测结果自校准后算PASS。
timeout: 每实例10秒；各平台最长1秒，超出者不进入本普通矩阵，仪器采集最长5秒。
cleanup: [先停止并拉低外部刺激, 停止Capture并关闭滤波, 禁用清除本轮IRQ, 释放仪器与输入路由]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认外部捕获输入, bench: 脉冲源和独立示波器及采样时钟范围映射}
backend: [FPGA, Silicon]
evidence: [实测输入边沿, 旁路与滤波逐阶段槽和RAW, W/T及采样周期上下界]
failure_observations:
  - {key: next_slot, label: 短脉冲后下一槽, source: dut, role: actual, format: decimal, semantic_ref: etim.feature.capture_next_slot}
  - {key: capture_value, label: 长脉冲实际捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: pulse_width, label: 实测刺激宽度秒, source: instrument, role: actual, format: float}
gap: [case_implementation_gap, filter_sample_clock_mapping_gap, external_input_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_005
case_name: 死区支路选择、延迟与反相
report_feature: |-
  1. ETIM 死区支路处理
p_level: P2
feature_refs: [ETIM_F_032]
method:
  inputs:
    - 支路参数矩阵：对已确认支路选择自身和另一支路输入，旁路、处理直出、处理反相交叉上升延迟单开、下降延迟单开和两者开启；两源周期相同而占空分别四分之一和四分之三以辨认来源。
    - 延迟时间依据：延迟值取0、8、32及一个小于最短平台四分之一的较大合法值，预期延迟为delay_ticks乘独立delay_tick_seconds；全部输入平台远大于延迟，不把窄脉冲吞吐混入本Case。
  steps:
    - 输入输出基线采集：绑定两输入参考波形和待测输出Observer，关闭Fault并停止配置无延迟PWM，测得两源不同占空的基线边沿。
    - 输入选择配置：在停止状态选当前输入支路，保持处理直出且延迟关闭，启动后对比输出边沿来源，确认不是仅选择字段读回正确。
    - 边沿延迟施加：停止后配置当前上升下降使能及延迟值，再启动并连续采集至少四个周期的输入和输出边沿。
    - 反相处理复核：切换为处理反相并重复采集，按反相后的极性匹配原输入边沿，不能把上升下降对应关系直接沿用。
    - 旁路对照采集：保留延迟配置但选旁路输出，确认输出恢复原旁路输入波形，排除延迟使能残留影响旁路。
    - 独立边沿比较：逐极性比较实测延迟与独立Expected，未使能边沿相对基线不移动，反相电平互补且没有额外或遗漏边沿。
    - 全组合结果汇总：完成所声明组和支路的矩阵，保存输入来源、处理模式和原始波形；文字冲突尚未确认的支路保留缺口而不冒充全组覆盖。
  observations:
    - 输入参考边沿：独立输入波形标识自身或另一支路来源，允许将输出边沿逐一对应到真实输入事件。
    - 处理输出边沿：PWM_OUTPUT.EDGE_TIMES在指定极性发生Expected延迟或反相，旁路时回到基线，证明完整数据通路而非只读寄存器。
  pass_criteria:
    - 支路和处理正确：每个已映射组合输入身份正确、仅指定边沿被延迟、反相关系正确，旁路恢复，不出现多边沿或丢边沿。
    - 延迟误差有界：基线扣除后的各实测延迟与delay_ticks乘已知时钟周期一致，误差不超过仪器和映射预算，不能从DUT延迟拟合时钟。
timeout: 每实例10秒，单次采集最长5秒，源周期必须使四周期落在采集界内。
cleanup: [停止两PWM输入和输出, 恢复旁路并关闭所有延迟, 停止仪器采集, 释放支路及板级安全资源]
resources: {minimum_level: R4, full_coverage_level: R4, board: 可独立观察输入参考和处理输出且无功率负载, bench: 多通道示波器及独立延迟时钟映射}
backend: [FPGA, Silicon]
evidence: [输入输出原始波形, 每极性基线与延迟比较, 支路和延迟参数及误差预算]
failure_observations:
  - {key: actual_delay, label: 实测边沿延迟秒, source: instrument, role: actual, format: float}
  - {key: expected_delay, label: 期望边沿延迟秒, source: oracle, role: expected, format: float}
  - {key: output_level, label: 实际输出电平, source: instrument, role: actual, format: bool}
gap: [case_implementation_gap, delay_clock_mapping_gap, output_branch_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_006
case_name: 周期和比较事件触发DMA搬运
report_feature: |-
  1. ETIM 周期与比较DMA请求
p_level: P2
feature_refs: [ETIM_F_033]
method:
  inputs:
    - DMA请求矩阵：分别选择PERIOD和COMPARE自然事件，源周期12000 Tick且比较点4000 Tick；目标数据采用稳定TIMEBASE.PERIOD_LIMIT实际值，搬运长度8或32个字，目的预填与该值不同的哨兵。
    - 公共DMA配置：P2M硬件请求、源固定、目的递增、每请求一个字，禁用软件请求和自动重试；目标适配绑定本通道请求入口及合法总线访问，不照搬其他硬件的全局DMA源编号。
  steps:
    - 请求资源绑定：解析ETIM通道到DMA请求的映射和DMA时钟，停止源，配置周期与比较值，读取作为数据Oracle的TIMEBASE.PERIOD_LIMIT。
    - DMA接收准备：复用公共DMA动作配置固定源及目的递增搬运，填充哨兵并按平台缓存契约完成一致性准备，清理历史完成状态。
    - 无事件负对照：先启用DMA接收但保持ETIM计数停止，跨过至少三个预期事件间隔读取REMAINING和目的数据，要求未传输。
    - 自然事件启动：选择当前PERIOD或COMPARE请求后只启动ETIM计数，不发任何软件DMA请求，在有限事件预算内等待DMA硬件完成。
    - 完成现场采集：停止ETIM，读取DMA_CHANNEL.COMPLETE和REMAINING，完成缓存同步后读取全部Destination数据及边界哨兵。
    - 传输独立比较：要求完成有效、剩余为零、每个目的字等于之前读取的源实际值且范围外哨兵保持，负对照应完全无变化。
    - 矩阵恢复汇总：完成两源两长度及已绑定通道路由，记录真实DMA终态和数据，关闭请求并释放DMA会话，不能把搬运正确扩成精确事件计数证明。
  observations:
    - DMA硬件终态：DMA_CHANNEL.COMPLETE和REMAINING分别证明指定长度完成，不能用软件等待函数返回成功替代。
    - 实际目的数据：Destination逐字等于固定源读回值且边界哨兵未变，停止源负对照未搬运，证明ETIM自然事件参与硬件请求路径。
  pass_criteria:
    - 数据终态正确：全部实例完成有效、剩余零、目的字全匹配且范围外未改写，负对照保持初始剩余量和哨兵。
    - 请求来源明确：运行中没有软件DMA触发，通道和自然请求映射有证据；本Case不证明Capture槽选择、请求脉宽或丢请求上限。
timeout: 每实例5秒；DMA完成等待不超过四倍传输长度个源周期加1秒，超时必须Abort DMA。
cleanup: [先停止ETIM请求源, Abort或关闭DMA并等待静止, 清除完成和错误状态, 释放目的数据及两IP会话]
resources: {minimum_level: R2, full_coverage_level: R2, board: 无外部跳线, bench: 片内DMA Peer及已确认外设总线请求映射}
backend: [FPGA, Silicon]
evidence: [DMA两个独立硬件终态, Destination及边界哨兵Artifact, 停止源负对照和源实际值]
failure_observations:
  - {key: dma_complete, label: DMA实际完成状态, source: peer, role: actual, format: bool}
  - {key: dma_remaining, label: DMA实际剩余量, source: peer, role: actual, format: decimal}
  - {key: expected_word, label: 期望目的字, source: oracle, role: expected, format: hex32}
gap: [case_implementation_gap, dma_request_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Mapping | Case Adaptation | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=33 | IMPLEMENTATION_GAP=19 | 33个公共Feature、19个PLAN；0个实现、0个实测；剩余边界与联动项未完成 | `ET6801_etim.md` |

本汇总只统计已准入公共Feature和已定义PLAN，不是目标硬件需求全集的覆盖率分母。
未准入的有效需求逐项保留在芯片文档，不能因为未分配Feature ID而从完成Gate中消失。

## 5. Common Gap / Evolution

| Gap | 状态 | 未闭合内容与解除条件 |
|---|---|---|
| EG-01 | IMPLEMENTATION_GAP | 本轮只写文档；PC Driver/Case、Firmware Service/Wrap、Chip Driver及Capability均须独立任务实现并绑定R400，不能先注册PLAN |
| EG-02 | MAPPING_GAP | 内部输入路由、延迟旁路、逻辑通道、时钟比和捕获误差上界必须逐项有目标证据，不能以同源回环PASS自行标定误差 |
| EG-03 | UNKNOWN | P2_004已规划唯一多数阈值的短长脉冲方法；采样分频编码为Mapping待核，双方同时达阈值、精确阈值边界和高输入初始化瞬态仍待补充可适用说明 |
| EG-04 | UNKNOWN | P2_005已规划可确认支路的选择、正常延迟与反相；延迟时钟为Mapping，a支路MUX文字冲突、窄脉冲吞吐及运行中延迟更新仍单独待核 |
| EG-05 | UNKNOWN | P2_003已规划旁路输出下CBC/One-Shot、重复输入及正常周期恢复；Fault与死区/互补优先级及同拍撤销/Clear竞态仍待可适用行为依据 |
| EG-06 | UNKNOWN | P1_011已规划运行计数器的内部软件/周期同步及禁用对照；停止时加载、同拍清零/同步优先级、外送脉冲延展和非内部源仍待核 |
| EG-07 | UNKNOWN | P1_009/010已规划安全窗口内立即/周期Shadow和比较对提交；计数已越过新值、事件Shadow及运行中延迟更新仍未由这些Case覆盖 |
| EG-08 | UNKNOWN | P2_006已规划周期/比较自然请求到DMA的搬运；Capture槽选择、请求精确时序及ADC/DAC/ACMP/XBAR接收链仍须独立接收端Oracle，不要求提供RTL |
| EG-09 | UNKNOWN | 最小/最大运行周期、真正计数回卷IRQ、极限PWM脉宽与最大捕获时长、性能及压力目标；需目标限值及外部时间基准，普通Case不得替代 |
| EG-10 | MAPPING_GAP | 外部输入/输出Bench端点、仪器精度和计数时钟容差尚未绑定；P2普通测量方法保留，不能因当前未接线删除 |
| EG-11 | UNKNOWN | 非内部PWM输入源矩阵的各Peer刺激与接收Oracle未逐一闭合；输入选择数量只作Capability，不是全部路由已测 |

优先顺序：先复核并实现P0计数和IRQ基础，再闭合EG-02实施内部捕获/PWM；外部普通测量与
EG-03～EG-09的剩余边界按继承资料、目标字段说明及后续适配证据继续定向收敛；硬件执行另需授权。该顺序不缩小完整IP覆盖义务。
不能把UNKNOWN改写成DEFERRED或SKIP；只有方法、刺激和Oracle全部确定而仅缺物理资源时才可标记DEFERRED。
