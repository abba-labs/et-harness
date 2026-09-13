# ETIM Public Test Contract

时间：2026-09-06 16:22 CST

2026-09-08 19:02 CST补充：参考测试方法已逐项落实到芯片文档3.8；32个PLAN的开发准备度见芯片文档4.3。
2026-09-08 20:16 CST修正：开发工作、执行映射和局部未知判据分别处理，不再把未完成适配的29项整体判为不能编码；全部仍未实现、未实测。

当前结论（2026-09-06 22:48 CST）：**本轮范围收敛完成，必测方法有局部资料问题 / NOT_IMPLEMENTED / NOT_EXECUTED**。
保留45个Feature、32个PLAN，不增加Case数量。验收分母是已确认要求和历史有效测试目的，不是寄存器所有可编码组合或全部理论竞态。
必测目的、局部待答问题和本轮范围外扩展分别见第五节及芯片Source Item Trace；这不是整个IP Implementation Ready或硬件PASS。
2026-09-06 18:06 CST复核：使用继承资料解释原理并以目标SVD裁定差异，不以取得RTL为分析前提。
此前因任何UNKNOWN而否定整体分析完成的口径已由本次范围裁决修正；必要Oracle未知仍阻塞对应目的，不能静默算覆盖。
2026-09-06 20:35 CST继续复核：补充接收端事件、动态事件、外部同步/Fault/相位、动态死区和自然回卷方法；捕获数据搬运与捕获事件请求仍分开处置。
2026-09-06 21:24 CST继续复核：加入连续Capture四槽周期快照DMA和PWM Peer输入选路；普通外部Case增加单Tick高宽及近全量程捕获参数。周期快照不等于每次CEVT握手。
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
| `event_source / event_ticks` | ZERO、PERIOD、COMPARE_A、COMPARE_B、CUSTOM；CUSTOM在计数等于event_ticks时产生事件。事件输出使能独立于PWM和SyncOut；不得将Peer触发统称为相位同步 |
| `event_receiver` | 逻辑ADC、DAC或ACMP内部DAC接收端及子通道；DAC采用寄存器数据、触发Shadow加载，关闭自触发/输入流/Ramp，实际加载值不等于软件暂存值 |
| `receiver_latency_ticks` | 事件到接收硬件变化的独立上界，包含接收加载/转换与目标侧读事务；必须小于Case内要区分的事件时刻间隔，不以测得的延迟反向制定上界 |
| `fault_source` | SOFTWARE或映射中的独立EXTERNAL输入；外部刺激源及XBAR实际输出必须分别有身份，不能只写路由寄存器当作已产生Fault |
| `irq_source` | `FAULT_ONE_SHOT / FAULT_CBC / FAULT_OVERFLOW / COMPARE_ERROR / COMPARE_A / COMPARE_B / PERIOD / COUNTER_OVERFLOW / CAPTURE_1..4`中Capability支持的源 |
| `deadline_ms` | Firmware单动作有界截止时间；PC事务截止时间必须覆盖该动作及传输余量，禁止无限等待或隐式重试 |
| `capture_peer / peer_output` | 独立PWM Peer及其逻辑输出；Peer标准精度产生已知周期/高宽，ETIM只配置输入选择和捕获。Peer的周期编码、输出动作和时钟属于Peer契约及Mapping，不套用ETIM周期编码 |
| `dma_snapshot_epochs` | 有限连续采集轮数；每轮四个真实捕获值更新后，由PERIOD请求读出一行。行号属于计划/Artifact身份，不冒充硬件生成序号 |

PWM普通区间Oracle：设源时钟Fs、源分频Ds、接收时钟Fc、接收分频Dc，则期望周期捕获差值
`N = period_ticks * Ds * Fc / (Fs * Dc)`；A模式高宽使用`compare_a_ticks`替换period_ticks，
A_B模式高宽使用`compare_b_ticks-compare_a_ticks`。优先构造整数N，禁止由实际测得值倒算Expected。
绝对时间戳采用按硬件计数宽度的模减；普通Case保证相邻事件间隔小于一次回卷，不推断跨多次回卷。
异步边沿量化允许误差由已验证的捕获时钟/路由上界给出，作为`capture_error_ticks`保存在参数证据中；
没有这个上界时停止对应execution，不能借用历史代码的任意容差。
同源数字环回只能证明比例/数字路径，不能证明绝对频率、分辨率、引脚电气质量或两端同源错误不存在。

长间隔捕获仍限制每一对相邻边沿间隔小于一次回卷；允许四槽总体跨多次回卷，但只能先对每个相邻差值
做模减，再以64位数相加。禁止直接对跨两个回卷的首尾槽做一次模减。量程边缘的保护间隔必须大于
时钟容差累计值、刺激误差和捕获量化误差，不能把因计数位宽已知而计算出的理论时长宣称为实测极限。

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
| `update_start / status / result / abort` | 在预定计数窗口写周期、比较值、事件值、相位暂存值或延迟值；返回写入前后COUNT.LIVE、各次写入顺序与完成身份，窗口越界为执行错误；Shadow比较对另有显式commit，不自动提交半对值；相位写入不隐式emit_sync |
| `configure_sync / emit_sync` | 配置逻辑源、phase_ticks、输入使能和输出模式；emit只产生一次软件同步，不隐式清零其他通道 |
| `configure_fault / set_fault_input / clear_fault` | 配置CBC/ONE_SHOT及输出电平，设置软件故障输入，单独发出One-Shot Clear；IRQ清除不代替Fault恢复 |
| `configure_filter / configure_delay` | 停止状态配置逻辑窗口/阈值/初始化或输出支路四链参数；返回实际字段读回，不用读回证明波形 |
| `configure_dma_request` | 选择本通道PERIOD或COMPARE请求；DMA传输本身复用公共DMA动作，禁止ETIM Wrap越层调用DMA Wrap |
| `configure_event / set_event_enable / route_event` | 配置逻辑事件源、CUSTOM值、更新模式、输出使能及接收端选择；不隐式启动Peer、不将Event使能当SyncOut使能、不发送Peer软件触发 |
| `route_sync_output` | 把已选软件/周期SyncOut接到Bench端点，返回逻辑路由身份；脉冲延展属于独立映射参数，不预先承诺未确认的脉宽 |
| Peer协调动作 | Case分别调用各IP直接动作；需要紧邻计数的事件窗口操作由已有目标侧有界执行机制承载，各Service只访问本IP。Peer缺公共动作属于实现缺口，不授权ETIM Service/Wrap调用Peer Wrap或新增公共架构层 |

连续DMA使用公共DMA的P2M、32bit传输、有限LLI和缓存一致性语义。每描述符只搬四个相邻槽，
下一描述符重新指向首槽并指向下一目的行；每个外设请求只能完成本行，不能保持请求直到整链自动搬空。
DMA必须在生产者启动前武装，目的和描述符的生存期延续到硬件静止后；采集中CPU不得代替DMA写目的数据。
连续采集轮内不得冻结Capture、Rearm或逐轮停计数。Capture清计数固定关闭，计数周期重装不复位槽序列。
周期到来至下一轮首槽覆盖前，DMA的整行完成和下一描述符准备均须落在独立上界内；不能只靠“数据看起来合理”推断无混行。

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
| `EVENT.SOURCE / VALUE / ENABLE` | 三个独立配置读回，不能作为事件已经外送的证明 |
| `DAC.LOADED_CODE / TX_DONE` | DAC真实已加载数据与发送结束上报，分别记录，不读取待发送配置冒充已加载数据 |
| `ACMP_DAC.LOADED_CODE[side] / TX_DONE[side]` | 每侧内部DAC的真实加载和发送完成端点；两侧不得拼成一个无法核对的值 |
| `ADC.EOC_RAW / RESULT / TRIGGER_OVERFLOW` | 指定转换通道的完成pending、实际转换结果和接收过载；EOC必须选择转换结束，ISR计数/时间标记仍属于Service事实 |
| `ACMP.OUTPUT[side]` | 比较器滤波前实际状态，关闭反相、Blanking和滤波；用于阈值跨越的模拟链结果，不用DAC代码回显代替 |
| `SYNC_OUTPUT.EDGE_TIMES / XBAR.OUTPUT_LEVEL` | 前者为外部实测同步边沿，后者为路由Peer真实输出上报；二者不等同于软件设置值 |

接收端事件的通用观察窗：先停止源并建立已加载旧值，再写入不同待加载值；使用慢计数和
足够分离的A/B/CUSTOM点，在预期事件前后读真实接收端点。读事务前后均取COUNT.LIVE，
保存所属周期；若窗口侵入事件或跨错周期，报告执行错误而不是容差内PASS。
ZERO与PERIOD只相隔一个计数Tick，相关实例必须加大分频并满足独立读事务/传播上界，
无法分辨时不能把两项合成一个“周期附近触发”结果。同步输出与Event输出是两个不同测试路径。

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
| ETIM_F_009 | ETIM 捕获边沿选择 | 按槽选择上升沿或下降沿，捕获值对应指定边沿序列 | ETIM_P1_002, ETIM_P1_003, ETIM_P2_002, ETIM_P2_018 |
| ETIM_F_010 | ETIM 绝对捕获时间戳 | 不清计数器，连续时间戳差值反映外部事件间隔 | ETIM_P1_002, ETIM_P2_002, ETIM_P2_018 |
| ETIM_F_011 | ETIM 相对捕获时间戳 | 在指定槽事件后清计数器，后续时间戳反映距该事件的间隔 | ETIM_P1_003, ETIM_P2_002, ETIM_P2_016 |
| ETIM_F_012 | ETIM 捕获输入预分频 | 输入预分频改变同极性捕获的事件间隔，不改变计数时钟配置 | ETIM_P1_005 |
| ETIM_F_013 | ETIM 捕获One-Shot | 指定槽后停止加载，后续刺激不能覆盖该轮数据 | ETIM_P1_004 |
| ETIM_F_014 | ETIM 捕获Continuous | 指定槽后回到首槽，后续刺激持续刷新捕获数据 | ETIM_P1_004, ETIM_P2_017 |
| ETIM_F_015 | ETIM 捕获Rearm | One-Shot冻结后重新武装，从首槽开始接收下一轮 | ETIM_P1_004 |
| ETIM_F_016 | ETIM Capture Load Enable/Disable | 关闭加载时CAP保持，恢复加载后随新事件更新 | ETIM_P1_006 |
| ETIM_F_017 | ETIM 中断Force/Clear | Force建立指定pending，Clear只清指定源；不替代自然事件测试 | ETIM_P0_002 |
| ETIM_F_018 | ETIM 中断Mask/Unmask | Mask抑制有效pending和投递，保留原始pending；Unmask恢复可投递状态 | ETIM_P0_002 |
| ETIM_F_019 | ETIM 中断Enable/Disable | 已使能源能够进入真实IRQ投递链；关闭后投递停止 | ETIM_P0_002, ETIM_P1_007 |
| ETIM_F_020 | ETIM Compare/Period中断 | 计数自然到达比较或周期事件后产生对应中断 | ETIM_P1_007 |
| ETIM_F_021 | ETIM Capture中断 | 对应捕获槽真实加载时产生指定捕获中断 | ETIM_P1_007, ETIM_P2_002 |
| ETIM_F_022 | ETIM COMPA≥COMPB配置错误 | A+B模式非法比较顺序触发配置错误，纠正后可清除 | ETIM_P1_008 |
| ETIM_F_023 | ETIM 周期Shadow加载 | 写入新周期后当前周期保留，周期边界后生效 | ETIM_P1_009 |
| ETIM_F_024 | ETIM 比较对Shadow提交 | A/B写完并提交后在周期边界成对生效，未提交不生效 | ETIM_P1_010 |
| ETIM_F_025 | ETIM 运行中立即加载 | 在安全更新窗口写入周期、比较或事件值后，本周期使用新值 | ETIM_P1_009, ETIM_P1_010, ETIM_P2_009 |
| ETIM_F_026 | ETIM 同步相位装载 | 选定同步到达后计数装入配置相位，关闭输入时不装载 | ETIM_P1_011, ETIM_P1_012, ETIM_P2_007 |
| ETIM_F_027 | ETIM 软件与周期SyncOut | 软件单次或周期事件产生同步，关闭输出无同步 | ETIM_P1_011, ETIM_P2_007, ETIM_P2_013 |
| ETIM_F_028 | ETIM CBC Fault封波 | 有效Fault强制输出，输入撤销后在周期边界恢复 | ETIM_P2_003, ETIM_P2_014 |
| ETIM_F_029 | ETIM One-Shot Fault封波 | 输入撤销后仍保持封波，同周期Clear满足退出条件后恢复 | ETIM_P2_003, ETIM_P2_014 |
| ETIM_F_030 | ETIM Fault重复输入中断 | Fault保持期间再次输入有效事件产生overflow pending | ETIM_P2_003 |
| ETIM_F_031 | ETIM 窗口阈值滤波 | 唯一多数阈值下抑制短脉冲并允许稳定长脉冲产生捕获 | ETIM_P2_004 |
| ETIM_F_032 | ETIM 死区支路处理 | 输入选择、边沿延迟和反相决定输出边沿；旁路恢复原支路 | ETIM_P2_005, ETIM_P2_015 |
| ETIM_F_033 | ETIM 周期与比较DMA请求 | 自然计数事件触发DMA完成指定搬运，停止事件时不传输 | ETIM_P2_006, ETIM_P2_016, ETIM_P2_017 |
| ETIM_F_034 | ETIM 计数事件选择 | 零点、周期、A、B和自定义比较分别决定接收端触发时刻 | ETIM_P2_008, ETIM_P2_009, ETIM_P2_010 |
| ETIM_F_035 | ETIM Event输出Enable/Disable | 关闭输出时接收端不响应，重新使能后由下一有效事件触发 | ETIM_P2_008, ETIM_P2_010 |
| ETIM_F_036 | ETIM 事件Shadow加载 | 更新所在周期保留旧事件点，下一周期改用新事件点 | ETIM_P2_009 |
| ETIM_F_037 | ETIM DAC事件路由 | 指定ETIM事件触发指定DAC加载，两接收端路由互不覆盖 | ETIM_P2_008, ETIM_P2_011 |
| ETIM_F_038 | ETIM ACMP内部DAC事件路由 | 指定事件触发比较器内部DAC加载，另一侧路由和数据不受影响 | ETIM_P2_008, ETIM_P2_011, ETIM_P2_012 |
| ETIM_F_039 | ETIM ADC采样触发 | 事件触发指定ADC转换，关闭事件无转换，恢复后获得新结果 | ETIM_P2_010 |
| ETIM_F_040 | ETIM 外部SyncOut | 所选软件或周期同步通过外部输出路由形成真实引脚脉冲 | ETIM_P2_013 |
| ETIM_F_041 | ETIM 外部Fault输入 | 选定外部输入产生封波与自然Fault中断，未选输入不产生Fault | ETIM_P2_014 |
| ETIM_F_042 | ETIM 死区运行更新 | 无未完成延迟的安全窗口写新值后，后续边沿采用新延迟 | ETIM_P2_015 |
| ETIM_F_043 | ETIM 捕获数据DMA搬运 | DMA从冻结槽或持续更新的捕获槽搬运真实时间戳，值与独立刺激一致；连续模式必须逐行证明无重复、缺失或混行 | ETIM_P2_016, ETIM_P2_017 |
| ETIM_F_044 | ETIM 计数器回卷中断 | 自然计数越过最大值产生回卷pending及真实IRQ，普通周期清零不冒充回卷 | ETIM_P1_012 |
| ETIM_F_045 | ETIM PWM Peer捕获选路 | 选中PWM Peer输出才刷新对应捕获槽，其他Peer输出不能替代被选源；周期与高低宽对应选中源 | ETIM_P2_018 |

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
| ETIM_P1_012 | 最大计数自然回卷与IRQ | P1 | R1 | PLANNED | 回卷前后COUNT.LIVE；overflow RAW；period RAW；ISR首次来源 |
| ETIM_P2_007 | 外部相位波形与运行相位更新 | P2 | R4 | PLANNED | 源和接收PWM边沿附件；相位写入窗口；实测相位差；Expected相位差 |
| ETIM_P2_008 | 事件选择与DAC接收路由 | P2 | R2 | PLANNED | 接收LOADED_CODE；TX_DONE；事件前后计数窗；未选端保持值 |
| ETIM_P2_009 | 事件立即与Shadow动态更新 | P2 | R2 | PLANNED | EVENT.VALUE；更新计数窗；接收LOADED_CODE阶段值；Expected事件时刻 |
| ETIM_P2_010 | 事件触发ADC转换与时刻 | P2 | R4 | PLANNED | ADC.EOC_RAW；ADC.RESULT；外部EOC标记波形；Expected转换窗口 |
| ETIM_P2_011 | 事件触发DAC模拟输出 | P2 | R4 | PLANNED | DAC.LOADED_CODE；DAC.TX_DONE；模拟输出波形；Expected电平窗口 |
| ETIM_P2_012 | 事件触发ACMP阈值更新 | P2 | R4 | PLANNED | 内部DAC加载值；ACMP.OUTPUT；实测输入电压；Expected比较状态 |
| ETIM_P2_013 | SyncOut外送与源选择 | P2 | R4 | PLANNED | SYNC_OUTPUT边沿附件；源PWM参考；软件触发标记；Expected边沿数 |
| ETIM_P2_014 | 外部XBAR Fault与恢复 | P2 | R4 | PLANNED | 实测Fault输入；XBAR.OUTPUT_LEVEL；自然Fault RAW；封波恢复波形 |
| ETIM_P2_015 | 死区安全窗口动态更新 | P2 | R4 | PLANNED | 更新窗口；输入输出边沿；新旧实测延迟；Expected延迟 |
| ETIM_P2_016 | 外部捕获值与DMA数据路径 | P2 | R4 | PLANNED | 输入波形；冻结CAPTURE.VALUE；DMA完成终态；Destination附件 |
| ETIM_P2_017 | 连续捕获四槽周期快照DMA | P2 | R4 | PLANNED | 实测输入与周期基准；DMA硬件终态；逐行Destination；逐行Expected |
| ETIM_P2_018 | PWM Peer捕获选路与隔离 | P2 | R2 | PLANNED | 选中Peer身份；CAPTURE.VALUE四槽；未选对照pending；Expected高低宽 |

普通点、单Tick高宽和近全量程参数均保留实际测量；它们不等于压力认证或未给适用规范的最高频率、最小电气脉宽认证。

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
    - 外部波形矩阵：对Bench声明可独立观测的PWM输出使用A和A_B模式，周期分别选为约0.1毫秒、1毫秒、5毫秒的整数Tick，A模式高宽约25%、50%、75%，A_B使用约25%到75%的高区间；另加入period_ticks为3、4、5的A模式，A固定1，divider覆盖最小及最大合法值，保留单Tick高宽目的而不假定电气最高频率。
    - 仪器时间基准：使用已校准示波器，记录时基精度、采样间隔、阈值和探头条件；Expected来自源时钟声明及分频配置，不从DUT捕获反推。
    - 误差预算：周期和高宽的允许误差分别由时钟容差、仪器时基容差及两边沿采样误差上界相加得到，运行前固定，不按实测偏差放宽；单Tick参数要求总误差小于半Tick并满足Bench带宽，不能用更长高宽替换后仍计入该参数。
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
    - 波形矩阵完整：全部声明输出端点、普通参数及3/4/5 Tick周期参数完成；最短高宽实测为1 Tick，未达到仪器分辨条件属于该参数未执行，不把未确认的最高频率或电气限值计入通过。
timeout: 每输出参数10秒，仪器单次采集等待最多5秒。
cleanup: [停止PWM输出, 恢复Bench安全输出状态, 停止仪器采集并释放会话, Disable并Clear本轮IRQ]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认的PWM输出端点及共地, bench: 已校准示波器和合适探头}
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
  4. ETIM Capture中断
p_level: P2
feature_refs: [ETIM_F_009, ETIM_F_010, ETIM_F_011, ETIM_F_021]
method:
  inputs:
    - 外部脉冲矩阵：信号源产生周期0.1毫秒、1毫秒、5毫秒、100毫秒且占空比25%、50%或75%的脉冲列，各已确认输入路由覆盖四槽RISING/FALLING/RISING/FALLING的绝对及全相对模式；另对每个计数实例的一条已确认外部输入，使用最大计数周期M和最小/最大divider，产生相邻间隔分别为M-K、M-2K、M-3K Tick的四边沿有限序列，覆盖近全量程；不把长时间矩阵重复扩乘全部等价输入选路。
    - 独立刺激观测：外部Observer在DUT输入端实测刺激边沿，输入电平、阈值及带宽由Bench确认；期望值来自实测刺激间隔乘接收计数频率。
    - 误差及量程：运行前固定计数时钟容差、捕获量化误差和外部测量误差；长间隔保护量K取不小于1024 Tick及最长间隔总误差八倍的整数，要求3K小于M/4，使每一间隔的上下界均严格位于0到M之间。若时钟/仪器条件不满足，不缩短间隔后冒称近全量程通过。
  steps:
    - 门禁与输入连接：人工确认板卡、接收端点、共地和允许电平后连接信号源及外部Observer，保持信号源输出关闭。
    - 刺激测量准备：配置当前周期波形或四边沿有限序列，读回设置并固定误差预算；长间隔Observer须覆盖全部三段并具有独立时基，不能用稀疏软件时间戳代替真实边沿时间。
    - 捕获端武装：配置DUT长周期、输入分频旁路、滤波旁路、四槽One-Shot及当前绝对或相对模式，绑定末槽自然IRQ会话、Enable并Unmask，清pending并先启动接收。
    - 外部刺激与采集：启动外部波形并同步保存DUT输入端真实边沿，普通参数在十个刺激周期内、长间隔参数在预先计算的三段总时长加余量内等待末槽真实ISR，ISR保存清除前RAW、STATUS及首次来源后关闭该源投递，禁止Force；长间隔期间不得停计数或相位预加载跳过真实等待。
    - 结果及刺激读取：关闭信号源后读取逐槽CAPTURE.VALUE和末槽RAW，同时取得覆盖本轮捕获窗的外部边沿附件。
    - 独立间隔判定：绝对模式只做相邻模减，相对模式舍弃首槽后比较后续槽；高宽、低宽Expected由外部实测刺激换算。普通周期或长序列中需要的总时长以64位累加相邻结果，不对跨多次回卷的首尾槽直接模减。
    - 输入矩阵汇总：逐输入路由、周期、占空比及时间戳模式保存完整证据，结束后恢复安全输入和释放仪器。
  observations:
    - 实际输入端刺激：STIMULUS_OUTPUT.EDGE_TIMES包含DUT端真正收到的高低间隔，避免源设定误差或接线异常被归为捕获误差。
    - DUT捕获时间戳：逐槽CAPTURE.VALUE及本轮末槽pending证明真实加载，真实ISR首次来源及清除前STATUS证明外部捕获进入IRQ链，不能用PC计算结果或仅轮询代替。
  pass_criteria:
    - 捕获时间正确：高宽、低宽及周期对应外部刺激的实测时间，换算误差不超过预先固定预算。
    - 路由模式完整：全部声明输入路由、普通脉冲及近全量程参数在两时间戳模式下完成，并有匹配本通道末槽的真实ISR及STATUS；首槽启动延迟不作相对模式Oracle，长间隔实际等待与原始边沿证据必须齐全。
timeout: 普通参数每实例10秒；长间隔参数在运行前由独立最慢计数频率计算三段总时长并加10%及5秒余量，固化为有界会话截止时间，PC短事务只查询会话状态，不自动重启长序列。
cleanup: [先关闭外部信号源, 停止Capture及计数器, 禁用清除本轮IRQ, 恢复输入安全状态并释放仪器]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认的外部Capture输入路由及共地, bench: 具备所需有限序列能力的函数发生器及已校准示波器}
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
    - 运行相位更新：在传播及采样上界内取得COUNT.LIVE，周期源连续检查三轮；软件分支在运行中把相位从100000改到300000或反向，先不发同步观察自由推进，再发下一次同步采集新装载值，记录写入前后计数且禁止停机重配。
    - 相位区间判定：有效软件或周期同步后的值落入当前phase_ticks加已知经过Tick的区间，DISABLED及输入关闭值落入自由运行区间；单写相位不改变当前计数，下一同步使用新相位，不能把旧需求的立即加载误解为写相位即清计数。
    - 路由矩阵汇总：每个相位和模式独立保存前后计数、触发身份与Expected区间，全部结束后关闭同步输入输出并停止两通道。
  observations:
    - 相位实际配置：SYNC.PHASE独立读回等于输入，作为装载Expected来源之一，但不代替实际计数跳变。
    - 接收计数现场：COUNT.LIVE在触发前后分别支持自由运行或相位装载区间，足以区分路由未通、重复加载和禁用无效。
  pass_criteria:
    - 装载与禁用正确：有效同步每次进入相位区间，两类禁用对照均不进入该区间，Expected区间必须预先确定且互不重叠。
    - 源模式正确：软件单次后自由推进，运行中双向修改相位不会在无同步时跳变而会在下一同步加载新值；周期模式连续三次装载，全部已声明路由和两相位参数均有实际证据。
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
    - 窗口阈值矩阵：实际W/T取8/5、8/8、16/9、16/16，以及Capability合法最大窗口Wmax搭配floor(Wmax/2)+1和Wmax；初始化为全零或当前低输入。采样实际分频必须含1和2，再取一个已映射较大合法值；不得用字段编码2代替实际2分频，T始终严格大于W的一半。
    - 脉冲宽度构造：独立时钟映射给采样周期下上界Ts_min和Ts_max；短高脉冲宽度小于(T-1)*Ts_min并留仪器误差余量，长高低平台各大于2*W*Ts_max。每个分频分别重算刺激，恰好阈值竞态及高输入初始化瞬态不属本轮基线。
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
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认外部捕获输入, bench: 具备所需脉冲能力的函数发生器和独立示波器及采样时钟范围映射}
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

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P1_012
case_name: 最大计数自然回卷与IRQ
report_feature: |-
  1. ETIM 计数器回卷中断
  2. ETIM 同步相位装载
p_level: P1
feature_refs: [ETIM_F_044, ETIM_F_026]
method:
  inputs:
    - 边界参数构造：按已声明计数位宽W设置最大period_ticks为2^W，软件同步相位为2^W减M；M至少65536 Tick并大于配置、采样及IRQ延迟上界的四倍，禁止直接写实时计数寄存器。
    - 自然源对照：普通period_ticks为65536，最大周期分支与普通周期分支均不Force；关闭PWM、Capture和周期同步，只允许一次软件同步装载。
  steps:
    - 普通周期对照：清理通道，运行普通周期至少两次，读取PERIOD与COUNTER_OVERFLOW的RAW，要求周期置位而最大值回卷源保持零。
    - 最大周期配置：停止并隔离后设置最大周期和当前相位，清除两个pending，绑定回卷IRQ会话并Enable及Unmask回卷源，保存实际配置。
    - 临界前相位装载：启动计数，由独立同步源发一次软件同步，读取COUNT.LIVE确实进入最大值前M Tick范围，再关闭同步输入，确认仍未回卷且overflow RAW为零。
    - 自然回卷等待：保持计数自然推进，不清零、不再次同步、不改周期，在按M和计数时钟得到的deadline内等待真实回卷ISR。
    - 边界现场保存：ISR记录回卷RAW及STATUS和来源，随后停止计数，读取低位区间COUNT.LIVE及PERIOD RAW，保留从临界前高值到回卷后低值的硬件证据。
    - 终态及清除比较：要求自然回卷pending和ISR成立、当前计数处于独立延迟预算给出的回卷后区间，最大周期同时到达周期终点；单独Clear后两个RAW归零。
    - 通道分频汇总：对全部逻辑通道及最小/最大合法divider完成普通与最大周期分支，任何临界前采样太晚或重复同步均记执行错误并安全退出。
  observations:
    - 真实计数跨界：COUNT.LIVE从最大值附近变为低值，配合临界前overflow为零及无清零动作证明自然跨界，不以小周期清零代替。
    - 自然回卷中断：IRQ_RAW.COUNTER_OVERFLOW与ISR现场IRQ_STATUS为一，普通周期负对照无此pending，PERIOD单独保存以区分两类源。
  pass_criteria:
    - 回卷事件正确：每实例必须先捕到临界前高计数和零pending，再有回卷后低计数、自然RAW及真实ISR，不接受仅强制中断通过。
    - 对照清理正确：普通周期仅产生周期事件，最大周期两终点事实按契约成立，停止和Clear后本轮pending均清零。
timeout: 每实例10秒；M换算后的等待不得超过5秒，不满足者在执行前重新选择合法M和时钟，不能增加超时掩盖失败。
cleanup: [关闭同步输入和输出, 停止计数, 停止IRQ会话并Mask及Disable, Clear本轮pending并释放通道]
resources: {minimum_level: R1, full_coverage_level: R1, board: 无外部跳线, bench: 独立内部软件同步源和有界IRQ现场采集}
backend: [FPGA, Silicon]
evidence: [临界前后COUNT.LIVE, 两源逐阶段RAW及回卷STATUS, ISR首次来源和独立时间预算]
failure_observations:
  - {key: live_count, label: 边界实际计数, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.count_live}
  - {key: overflow_raw, label: 自然回卷RAW, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.counter_overflow}
  - {key: expected_range, label: 期望回卷后区间, source: oracle, role: expected, format: text}
gap: [case_implementation_gap, sync_route_and_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_007
case_name: 外部相位波形与运行相位更新
report_feature: |-
  1. ETIM 同步相位装载
  2. ETIM 软件与周期SyncOut
p_level: P2
feature_refs: [ETIM_F_026, ETIM_F_027]
method:
  inputs:
    - 相位波形矩阵：源和接收PWM使用相同计数频率、period_ticks为80000及A为10000；相位先取20000再改40000，另做反向变化，源周期SyncOut驱动接收相位装载。
    - 外部相位Oracle：同时实测两路PWM上升沿，接收下一周期起点相对同步到达的期望间隔为period_ticks减phase_ticks；同步到达相对源周期基准的固定偏移和误差界由映射提供，不用当前波形拟合。
  steps:
    - 外部端点准备：确认门禁、无危险负载和两路独立输出，配置示波器同步采集与时钟误差预算，关闭死区、Fault和反相。
    - 原相位同步启动：停止配置同频PWM及旧相位，先启动接收再启动周期同步源，等待两次有效同步后捕获至少四组源及接收上升沿。
    - 运行中相位写入：保持两计数器及同步运行，在源计数30000至40000的安全窗口写新phase_ticks，记录写前后计数，不能停机重配或主动额外同步。
    - 更新周期连续采集：保存覆盖写入前、写入后但下一同步前、下一次同步及之后至少四周期的连续波形，波形中保留写入窗口标记。
    - 外部相位比较：下一同步到达前接收保持旧相位轨迹，下一同步后采用新相位；相应完整上升沿位置符合独立Expected，允许的过渡截断仅由明确同步装载时刻推导。
    - 关闭输入对照：关闭同步输入后再修改相位并运行数周期，要求波形继续自由运行且不因单写相位出现计数重装所对应的跳变。
    - 双向路由汇总：完成两相位更新方向和已声明外部输出组合，保存原始波形和逐周期相位值，再关闭同步及PWM。
  observations:
    - 外部两路边沿：PWM_OUTPUT.EDGE_TIMES分别属于源和接收端，直接证明引脚相位，不以COUNT.LIVE读回替代。
    - 写入与生效关系：源COUNT.LIVE标记相位写入窗口，波形在下一同步前后分别符合旧新轨迹；无输入对照没有写相位导致的突变。
  pass_criteria:
    - 相位波形正确：稳定相位及更新后的四周期均符合period_ticks减phase_ticks与独立同步偏移的Expected，误差预算在运行前固定。
    - 动态时机正确：无停止重配，单写相位不立即重装计数，下一有效同步使用新值，两更新方向及禁用对照完整。
timeout: 每实例10秒，连续波形采集最长5秒。
cleanup: [先关闭同步输入输出, 停止两路PWM和计数器, 恢复安全输出, 停止仪器采集并释放端点]
resources: {minimum_level: R4, full_coverage_level: R4, board: 两路已确认PWM输出且无功率负载, bench: 多通道示波器及独立同步传播映射}
backend: [FPGA, Silicon]
evidence: [源与接收连续波形, 相位写入前后COUNT.LIVE, 逐周期独立Expected及误差预算]
failure_observations:
  - {key: actual_phase, label: 实测相位间隔秒, source: instrument, role: actual, format: float}
  - {key: expected_phase, label: 期望相位间隔秒, source: oracle, role: expected, format: float}
gap: [case_implementation_gap, external_output_bench_mapping_gap, sync_route_and_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_008
case_name: 事件选择与DAC接收路由
report_feature: |-
  1. ETIM 计数事件选择
  2. ETIM Event输出Enable/Disable
  3. ETIM DAC事件路由
  4. ETIM ACMP内部DAC事件路由
p_level: P2
feature_refs: [ETIM_F_034, ETIM_F_035, ETIM_F_037, ETIM_F_038]
method:
  inputs:
    - 事件接收矩阵：ZERO、PERIOD、COMPARE_A、COMPARE_B、CUSTOM分别路由至独立DAC及ACMP每侧内部DAC；period_ticks为16000，A为4000、B为8000、CUSTOM为12000，已声明可映射源和接收端逐一轮换。
    - 加载数据对照：以四分之一量程代码为旧值、四分之三为待加载值，接收端寄存器输入、Shadow加载、零附加延迟、无反相；两接收端同时绑定两个不同ETIM源并交替运行，避免单路测试掩盖另一路选择被覆盖。
    - 观察窗口要求：采用满足0.3的慢计数与独立接收延迟界；ZERO与PERIOD必须在末Tick及回零后分别取证，不能只检查下一周期数据已变。
  steps:
    - 接收旧值建立：停止ETIM源，经Peer正规配置把旧代码真实加载并读取LOADED_CODE，清除TX_DONE，关闭自触发、输入流及Ramp，随后切换ETIM触发Shadow方式。
    - 事件和路由配置：配置当前事件点及两接收端不同源，写入两端不同的待加载代码并分别读实际路由；源先保持Event关闭，计数可运行。
    - 输出关闭对照：跨过两个选定事件机会，要求两接收端LOADED_CODE仍为旧值且无新TX_DONE；证明待加载写入没有绕过事件路径。
    - 当前源事件激励：仅使能并运行被测源事件，保持另一路源停止；按预定事件前后计数窗读取目标LOADED_CODE和TX_DONE，同时读取未选接收端。
    - 接收选择切换：停止并恢复两端旧值与pending，交换两个接收端的源选择后只运行另一源，重复事件前后观察，配置写入必须保留另一个选择字段。
    - 计数事件比较：事件前目标保持旧值、事件后在独立延迟界内为新值且TX_DONE有效，未选接收端不变；逐一分辨五种计数点，不能以ETIM自身比较IRQ代替接收动作。
    - 接收矩阵汇总：完成全部已确认源、两类接收器、两侧路由和五事件，保存事件前后计数窗及独立加载上报，再关闭事件输出和Peer触发。
  observations:
    - 接收真实加载值：DAC.LOADED_CODE或ACMP_DAC.LOADED_CODE在事件前保持、事件后改变，使用硬件加载上报而非待发送配置读回。
    - 接收完成与隔离：对应TX_DONE在本轮事件后置位，另一接收端的加载值和完成状态保持；其独立路由字段未被覆盖。
  pass_criteria:
    - 事件时点正确：五种事件均在各自可分辨窗口触发接收加载，关闭Event负对照无更新，窗口越界不计通过。
    - 接收路由正确：两个不同源交替运行及选择交换均只更新对应接收端，旧新值精确匹配，全部声明矩阵完成。
timeout: 每实例10秒；目标侧单个阶段最多三个源周期加1秒。
cleanup: [停止ETIM计数及Event输出, 停止Peer触发并等待静止, 清除本轮发送完成, 恢复接收安全值并释放路由]
resources: {minimum_level: R2, full_coverage_level: R2, board: 无外部跳线且模拟输出无危险负载, bench: DAC或ACMP内部DAC Peer和有界目标侧分阶段读取}
backend: [FPGA, Silicon]
evidence: [各接收端独立LOADED_CODE和TX_DONE, 原始事件前后计数窗口, 双接收路由及交换负对照]
failure_observations:
  - {key: loaded_code, label: 接收实际加载代码, source: peer, role: actual, format: hex32}
  - {key: tx_done, label: 接收实际发送完成, source: peer, role: actual, format: bool}
  - {key: expected_code, label: 期望加载代码, source: oracle, role: expected, format: hex32}
gap: [case_implementation_gap, event_receiver_mapping_gap, receiver_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_009
case_name: 事件立即与Shadow动态更新
report_feature: |-
  1. ETIM 计数事件选择
  2. ETIM 事件Shadow加载
  3. ETIM 运行中立即加载
p_level: P2
feature_refs: [ETIM_F_034, ETIM_F_036, ETIM_F_025]
method:
  inputs:
    - 动态事件矩阵：period_ticks为16000，CUSTOM事件点在6000与10000之间双向改变；IMMEDIATE和PERIOD_BOUNDARY各执行，写入窗口为计数1000至2000，先于新旧事件点。
    - 接收与时间Oracle：DAC触发Shadow方式使用不同待加载代码标识每周期，事件前后由真实LOADED_CODE与TX_DONE证明；接收延迟及读窗口上界必须远小于4000 Tick事件间隔。
  steps:
    - 原事件基线建立：停止配置源和DAC，建立旧加载值，配置CUSTOM旧事件点并运行，确认至少一次接收变化发生于旧事件窗口。
    - 新周期接收准备：在下一周期开始后且早于更新窗口写不同待加载代码并清TX_DONE，保持DAC加载模式不变，只切换ETIM事件更新模式。
    - 安全窗口事件写入：在计数1000至2000内写新event_ticks，保存写前后COUNT.LIVE和EVENT.VALUE，不能停止源或用事件输出门控隐藏过渡。
    - 当前周期时点探测：分别在新旧事件点前后读取LOADED_CODE及TX_DONE；为识别后续重复事件，在第一次完成之后且下一候选点之前清TX_DONE并写另一不同代码，所有服务动作均必须落入已留出的安全间隔。
    - 下一周期时点探测：在周期边界后再次准备不同代码，按同样窗口检查新旧候选点及接收完成，保存至少两个后续周期且禁止遗漏第二次意外触发。
    - 动态Oracle比较：立即模式当前周期只在新事件点触发，Shadow模式当前周期只在旧点触发且下一周期只在新点触发；旧新事件不应在同周期各触发一次，未到候选点的加载值保持。
    - 双向模式汇总：完成两模式和两方向四实例，将更新窗口、各候选点完成前后状态和代码身份对应后关闭源及Peer。
  observations:
    - 更新现场计数：COUNT.LIVE写前写后都在新旧事件之前，EVENT.VALUE只作写入事实而不冒充当前生效事件。
    - 候选点接收状态：DAC.LOADED_CODE及TX_DONE在两个分离事件窗口分别保存，重新预装不同代码使额外触发无法被相同加载值掩盖。
  pass_criteria:
    - 生效周期正确：四实例符合当前或下一周期切换的Oracle，新旧值均可区分，不以最终稳定值正确替代过渡证明。
    - 无重复或提前：每完整周期只出现一次规定接收动作，另一候选点不触发，所有预装及Clear窗口均有硬件计数证据。
timeout: 每实例10秒；目标侧阶段不超过六个源周期加1秒。
cleanup: [停止ETIM Event及计数, 关闭事件Shadow并恢复停止配置, 停止DAC触发和清完成状态, 释放两IP资源]
resources: {minimum_level: R2, full_coverage_level: R2, board: 无外部跳线且无危险负载, bench: DAC实际加载Observer及有界周期窗口协调}
backend: [FPGA, Silicon]
evidence: [动态写入COUNT.LIVE, 按周期和候选事件点编号的LOADED_CODE及TX_DONE, 独立事件时刻Expected]
failure_observations:
  - {key: loaded_code, label: 候选时刻实际加载值, source: peer, role: actual, format: hex32}
  - {key: tx_done, label: 候选时刻接收完成, source: peer, role: actual, format: bool}
  - {key: expected_event, label: 本周期期望事件Tick, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, event_receiver_mapping_gap, receiver_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_010
case_name: 事件触发ADC转换与时刻
report_feature: |-
  1. ETIM 计数事件选择
  2. ETIM Event输出Enable/Disable
  3. ETIM ADC采样触发
p_level: P2
feature_refs: [ETIM_F_034, ETIM_F_035, ETIM_F_039]
method:
  inputs:
    - 事件与接收矩阵：五种计数事件分别触发一个ADC逻辑转换通道，ETIM周期约10毫秒且A/B/CUSTOM分别约四分之一、二分之一、四分之三周期；遍历已映射ETIM源及ADC实例，每次只开放一个转换通道。
    - 模拟输入与Golden：外部源依次提供约四分之一、四分之三参考量程的稳定安全电压，并在ADC引脚实测输入和参考；Expected代码区间来自ADC位宽、对齐、输入范围和既定误差规范，不以本次转换值标定。
    - 时刻独立预算：EOC选择转换结束，关闭连续自触发和EOC回馈触发；配置为每个外部事件接受一次转换的连续可触发方式。源周期须大于转换、ISR和清理上界，EOC标记延迟含采样窗口、转换和ISR上界，ZERO/PERIOD分辨要求另由0.3约束。
  steps:
    - 门禁与接收准备：绑定模拟输入、PWM周期参考及EOC服务标记引脚，确认安全电平，配置并校准ADC公共接收路径，只允许当前ETIM事件作触发源。
    - 无事件转换对照：ETIM计数运行但Event关闭，清ADC完成和历史会话，稳定输入后跨两个周期读取EOC及服务计数，要求无新转换完成。
    - 当前事件启动：配置所选事件和精确时刻，先武装ADC与外部Observer再Enable Event，记录首个完整观测周期身份，不发ADC软件触发。
    - 转换现场采集：连续接收八个事件，每次EOC ISR先保存当前EOC_RAW、RESULT及触发溢出，再产生标记并Clear；外部Observer同时采集源参考和全部标记，服务次数不得冒充硬件事件计数器。
    - 输入改变复核：关闭Event并等待接收静止，切换另一稳定输入并实测，重新启动八事件会话，要求新转换数据符合新电平而不是旧RESULT缓存。
    - 时间数据双判定：各RESULT落在独立Golden代码区间，每个EOC标记只对应一个Expected事件加转换/ISR延迟窗口；检查EOC源身份、没有触发溢出或多余标记，ZERO/PERIOD实例不可合并。
    - 关闭恢复汇总：关闭Event后等待在途转换完成并清状态，再观察两个周期无新EOC；重新使能应取得新完成，最后停止源、ADC和外部刺激。
  observations:
    - 接收转换现场：ADC.EOC_RAW为本次目标通道完成，ADC.RESULT为对应稳定输入的实际数据，ADC.TRIGGER_OVERFLOW为零；字段按Peer映射分别采集。
    - 外部时刻关系：PWM参考与EOC标记真实波形对应事件时刻及已知转换/服务上界；标记不是ADC硬件时间戳，报告必须保留其服务延迟来源。
  pass_criteria:
    - 事件转换成立：Event关闭静默、开启后每轮八个独立完成和新数据，恢复后可继续；没有软件触发或其他转换源参与。
    - 时刻数据正确：全部事件和两电平实例满足Expected代码区间及时间窗口，无丢失、多余完成或触发溢出，不把本Case当作ADC精度认证。
timeout: 每实例20秒，模拟稳定最长5秒，单轮八事件采集最长5秒，任一接收等待有界。
cleanup: [先关闭ETIM Event并停止计数, 等待或中止在途ADC转换, 关闭IRQ会话并Clear, 停止模拟刺激和仪器并恢复安全输入]
resources: {minimum_level: R4, full_coverage_level: R4, board: ADC安全输入及源参考和EOC标记端点, bench: 具备安全DC输出的函数发生器及满足电压误差预算的多通道示波器}
backend: [Silicon]
evidence: [ADC逐次原始完成及RESULT, 源参考和EOC服务标记波形, 实测电压与独立代码和时间预算]
failure_observations:
  - {key: adc_result, label: ADC实际转换结果, source: peer, role: actual, format: hex32}
  - {key: eoc_raw, label: ADC实际完成RAW, source: peer, role: actual, format: bool}
  - {key: expected_code_range, label: 期望转换代码区间, source: oracle, role: expected, format: text}
gap: [case_implementation_gap, event_receiver_mapping_gap, adc_bench_and_latency_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_011
case_name: 事件触发DAC模拟输出
report_feature: |-
  1. ETIM DAC事件路由
  2. ETIM 计数事件选择
  3. ETIM ACMP内部DAC事件路由
p_level: P2
feature_refs: [ETIM_F_037, ETIM_F_034, ETIM_F_038]
method:
  inputs:
    - 模拟输出参数：独立DAC及具备已确认模拟观测路由的ACMP内部DAC均作为逻辑接收端，依次由PERIOD及CUSTOM事件触发；源周期约10毫秒、CUSTOM约四分之三周期，待发送代码交替为四分之一与四分之三量程，使用寄存器输入、触发Shadow和零附加延迟。
    - 电平与时刻依据：参考电压、DAC映射及既定直流误差给出两电平Expected区间，仪器同时采集DAC模拟输出及源PWM周期参考；加载和模拟建立时间上界独立声明，不能只测最终电平。
  steps:
    - 安全模拟基线：确认门禁、输出负载和仪器输入安全，建立旧代码的实际模拟电平及DAC.LOADED_CODE，切换到ETIM触发并清发送完成。
    - 待发送代码暂存：停止事件源，写不同新代码且保持Shadow，测量模拟输出仍为旧电平并读取实际加载值保持，排除直接加载绕过触发。
    - 事件选择启动：配置当前PERIOD或CUSTOM事件及DAC路由，武装连续波形后启动ETIM计数和Event，不发DAC软件触发。
    - 事件模拟变化采集：捕获源基准、DAC电平跳变和建立过程，在事件后读取DAC.TX_DONE及LOADED_CODE，确保数字加载与模拟输出属于同一次事件。
    - 反向代码复测：每次事件完成后在下一事件前安全窗口预装相反代码，连续取得八次高低变化；另一DAC保持原事件路由停止，不得产生同样变化。
    - 外部时间电平比较：逐次检查变化不早于预期事件窗口、在独立建立上界内达到相应电平范围，数字加载等于预装代码，未选输出保持。
    - 输出路由汇总：完成各DAC、两事件及双向变化后关闭Event，确认不再变化，再恢复安全代码及停止仪器，外部波形结论不由内部数据上报替代。
  observations:
    - 实际模拟波形：DAC输出端波形包含事件前保持、触发后变化及稳态电平，直接证明发波链路。
    - 数字加载完成：独立DAC使用DAC.LOADED_CODE和TX_DONE，内部DAC使用对应ACMP_DAC端点，分别记录加载及完成并与外部波形核对，不用比较器状态代替内部DAC模拟波形。
  pass_criteria:
    - 模拟事件正确：每实例八次变化均与所选事件对应，提前更新或未选端跟随均失败，稳态电平落在独立Expected区间。
    - 观测链完整：每次有预装身份、加载端点和外部波形，关闭事件后保持；不将普通功能测量扩写为DAC全量电气指标通过。
timeout: 每实例20秒，单次连续采集最长5秒，模拟稳定等待按预先映射上界且不超过5秒。
cleanup: [停止ETIM Event和计数, 停止DAC触发, 恢复安全输出代码, 清完成并释放仪器及Peer]
resources: {minimum_level: R4, full_coverage_level: R4, board: 独立或内部DAC模拟输出观测路由及源PWM参考且无危险负载, bench: 满足输出及参考电压误差预算的多通道示波器}
backend: [Silicon]
evidence: [DAC模拟输出和源参考连续波形, LOADED_CODE及TX_DONE独立Observation, 电平和建立时间Expected]
failure_observations:
  - {key: actual_voltage, label: 实测DAC输出电压, source: instrument, role: actual, format: float}
  - {key: loaded_code, label: DAC实际加载代码, source: peer, role: actual, format: hex32}
  - {key: expected_voltage_range, label: 期望输出电压区间, source: oracle, role: expected, format: text}
gap: [case_implementation_gap, event_receiver_mapping_gap, dac_analog_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_012
case_name: 事件触发ACMP阈值更新
report_feature: |-
  1. ETIM ACMP内部DAC事件路由
p_level: P2
feature_refs: [ETIM_F_038]
method:
  inputs:
    - 阈值与输入矩阵：各已确认ACMP的两侧内部DAC分别使用四分之一和四分之三参考量程代码，比较器正端接外部稳定半量程输入、负端接本侧DAC，关闭反相、Blanking、Ramp和滤波，裕量大于全部误差及迟滞上界。
    - 独立事件配置：两侧内部DAC绑定不同ETIM源，当前源周期约10毫秒且CUSTOM事件约三分之二周期，另一源停止；两侧选择交换后再测，保持每侧配置独立。
  steps:
    - 模拟输入安全准备：门禁确认后接入并实测半量程电压及参考，建立当前侧低阈值，读取ACMP_DAC.LOADED_CODE及ACMP.OUTPUT为输入大于阈值的规范状态。
    - 新阈值Shadow暂存：将高阈值写入当前侧待发送寄存器，接收触发选择ETIM而源Event关闭，等待两个源周期，实际阈值和比较状态都必须保持旧值。
    - 当前侧事件激活：开启当前ETIM事件，保存事件前后的计数窗口，等待内部DAC实际加载高阈值及发送完成，再读取滤波前比较状态。
    - 反向阈值与隔离：预装低阈值，下一有效事件后要求状态反向恢复；每个阶段读取另一侧加载值和比较状态保持，不能通过共同复位两侧获得假隔离。
    - 双侧路由交换：重新建立基线后交换两侧事件源，只运行新选择源，重复低到高再到低阈值，并检查另一个选择字段未被覆盖。
    - 模拟比较判定：Expected由实测正端电压与低高阈值的独立规范区间确定；阈值低时输出为输入大于参考的状态，高时相反，必须同时符合内部加载值和实际比较结果。
    - 实例结果汇总：完成全部声明ACMP实例、两侧和路由交换，记录自然发送完成及比较前后状态后关闭事件、比较器和模拟输入。
  observations:
    - 内部DAC加载端点：每侧ACMP_DAC.LOADED_CODE在触发前后精确对应旧新阈值，TX_DONE单独保存，另一侧保持。
    - 实际模拟比较状态：ACMP.OUTPUT滤波前端点在输入不变的情况下随阈值跨越改变，并在反向更新后恢复；该端点不是DAC数据寄存器。
  pass_criteria:
    - 阈值比较正确：所有低高低转换均满足独立电压关系，关闭Event无变化，不能只有加载代码变化而没有实际比较器响应。
    - 双侧路由独立：当前事件只更新当前侧，另一侧选择及状态保持，交换后仍成立，无软件触发或Ramp参与。
timeout: 每实例20秒，输入稳定最长5秒，单次接收及比较等待最多三个事件周期加1秒。
cleanup: [先关闭ETIM Event和计数, 停止两侧DAC触发及比较器, 清完成并恢复安全配置, 停止外部电压源并释放Peer]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认比较器模拟输入及内部DAC参考连接, bench: 具备安全DC输出的函数发生器和满足输入及参考电压误差预算的示波器}
backend: [Silicon]
evidence: [逐侧LOADED_CODE及比较状态前后值, 实测输入参考电压与阈值Expected, 双侧源选择和事件窗口]
failure_observations:
  - {key: loaded_code, label: 内部DAC实际加载值, source: peer, role: actual, format: hex32}
  - {key: comparator_output, label: 比较器实际输出状态, source: peer, role: actual, format: bool}
  - {key: expected_output, label: 期望比较状态, source: oracle, role: expected, format: bool}
gap: [case_implementation_gap, event_receiver_mapping_gap, acmp_analog_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_013
case_name: SyncOut外送与源选择
report_feature: |-
  1. ETIM 外部SyncOut
  2. ETIM 软件与周期SyncOut
p_level: P2
feature_refs: [ETIM_F_040, ETIM_F_027]
method:
  inputs:
    - 外送源矩阵：两个不同ETIM源分别配置约1毫秒和3毫秒周期，逐一选为全局外送源；覆盖SOFTWARE、PERIOD、DISABLED及外送路由开启或关闭，源PWM参考保持可观测。
    - 波形观察约束：使用目标已确认的SyncOut到XBAR再到引脚路由及可采集脉冲配置，采样率足以分辨其脉宽；本Case判定脉冲出现、数量和周期，不擅自固定未知延展位的精确宽度。
  steps:
    - 外部路由准备：确认门禁和输出端点，配置XBAR直出、无反相和无额外锁存，外部Observer同时采集两源PWM及同步输出，记录选中路由读回。
    - 禁用静默基线：两源计数运行但SyncOut均DISABLED，持续观察至少十个慢源周期，要求外送端无同步脉冲。
    - 软件单次外送：选择当前源的SOFTWARE模式，只发一次软件同步，保存有界动作标记及外部输出；再对未选源发一次，要求只有选中源的动作产生一个脉冲。
    - 周期模式外送：选择当前源PERIOD模式，连续采集覆盖八个完整源周期的输出边沿，先前软件触发不参与周期判据。
    - 源选择及关闭对照：交换为另一周期源重复采集，再关闭外送路由，源仍运行，排除关闭计数器造成的假静默。
    - 外部边沿比较：软件有效触发仅一个脉冲，未选源及DISABLED无脉冲；周期输出与所选源的八个周期事件一一对应，间隔符合独立时钟预算而非另一源周期。
    - 外送矩阵汇总：逐路由和两源保存完整波形、模式及开启关闭现场，最后停止同步及PWM，不将本Case结果推广到未确认的延展宽度编码。
  observations:
    - 引脚同步边沿：SYNC_OUTPUT.EDGE_TIMES直接给出脉冲数量及间隔，源PWM参考证明同步来自当前选中源。
    - 外送关闭对照：路由关闭而源参考仍持续，外送端无新脉冲，区分外送门控与源停机。
  pass_criteria:
    - 软件周期正确：选中软件源单次仅一脉冲，周期源八个完整事件逐一可见，未选源软件动作没有输出。
    - 选择门控正确：交换源后周期随所选源改变，DISABLED和外送关闭均静默，所有声明物理路由完成。
timeout: 每实例10秒，单次波形捕获最长5秒。
cleanup: [关闭外送路由及两源SyncOut, 停止计数和PWM, 恢复引脚安全状态, 释放XBAR与仪器]
resources: {minimum_level: R4, full_coverage_level: R4, board: SyncOut外部端点及两源PWM参考, bench: 多通道数字示波器和可测脉冲宽度映射}
backend: [FPGA, Silicon]
evidence: [原始同步及源参考波形, 软件单次触发身份, 外送选择和禁用负对照]
failure_observations:
  - {key: pulse_count, label: 外部实测脉冲数, source: instrument, role: actual, format: decimal}
  - {key: actual_interval, label: 外部同步间隔秒, source: instrument, role: actual, format: float}
  - {key: expected_count, label: 期望脉冲数, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, external_sync_route_mapping_gap, sync_pulse_observer_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_014
case_name: 外部XBAR Fault与恢复
report_feature: |-
  1. ETIM 外部Fault输入
  2. ETIM CBC Fault封波
  3. ETIM One-Shot Fault封波
p_level: P2
feature_refs: [ETIM_F_041, ETIM_F_028, ETIM_F_029]
method:
  inputs:
    - 外部故障矩阵：已映射的两条逻辑外部Fault输入分别交叉CBC和ONE_SHOT及强制LOW/HIGH；PWM周期约100毫秒且高宽四分之一周期，延迟与反相旁路，软件Fault始终无效。
    - 独立刺激与对照：外部脉冲源经输入端和XBAR送选定Fault输入，另一路单独可激励；记录真实输入波形及XBAR实时输出上报，不连接功率负载，输出电平由外部Observer读取。
  steps:
    - 输入输出安全准备：门禁确认后绑定两Fault输入及旁路PWM输出，配置XBAR直通和已知有效极性，绑定当前模式IRQ会话并Enable及Unmask，清旧pending后保持两输入无效并采集正常PWM基线。
    - 未选输入负对照：只激励未选输入跨过两个周期，确认其XBAR实际输出有效而被选输入无效，PWM仍正常且目标Fault RAW未置位。
    - 选定输入激活：撤销对照后对选定输入施加有效电平并保持两周期，读取对应XBAR.OUTPUT_LEVEL、自然Fault RAW和实际PWM封波电平；真实ISR先锁存当前源及STATUS后关闭该源投递。
    - 故障输入撤销：撤销选定输入并以实测波形和XBAR上报确认无效，CBC观察下一周期恢复，ONE_SHOT保持两个周期不Clear，要求继续封波。
    - 单次恢复执行：ONE_SHOT在输入已无效的安全周期窗口发Fault Clear并保持输入无效，记录目标计数窗口，随后采集恢复后的三个完整PWM周期。
    - 外部行为比较：选中输入才会触发指定电平封波和模式pending，CBC与ONE_SHOT退出分别符合既定模型，恢复波形等于原配置；单独IRQ Clear不能作为退出动作。
    - 路由模式汇总：完成两输入、两模式、两输出电平和已映射通道组合，保留未选负对照和恢复证据，再先停PWM后撤销全部刺激并释放路由。
  observations:
    - 输入路径实际状态：外部输入波形与XBAR.OUTPUT_LEVEL分别证明物理刺激和路由输出成立，而不是软件选择字段正确。
    - 故障输出与中断：FAULT_OUTPUT.LEVEL和自然IRQ_RAW对应选中输入，关闭或未选输入下保持正常PWM，恢复后有完整实际边沿。
  pass_criteria:
    - 选路封波正确：每实例只有选中外部输入触发，封波电平、自然模式pending及真实ISR来源符合配置，软件Fault和Force未参与。
    - 退出恢复正确：CBC撤销后按周期恢复，ONE_SHOT未Clear保持且合法Clear后恢复，全部恢复周期符合原PWM及独立测量预算。
timeout: 每实例20秒，单个保持阶段最长四个PWM周期，仪器采集最长5秒；超时先安全停止PWM。
cleanup: [停止PWM输出, 撤销外部刺激并确认XBAR无效, 清Fault及IRQ并关闭路由, 恢复安全端点并释放仪器]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认双外部Fault输入和独立PWM输出且无功率负载, bench: 具备双通道安全脉冲输出的函数发生器及多通道示波器}
backend: [FPGA, Silicon]
evidence: [输入及封波恢复原始波形, XBAR实时输出Observation, 自然Fault RAW和Clear窗口]
failure_observations:
  - {key: xbar_level, label: XBAR实际输出电平, source: peer, role: actual, format: bool}
  - {key: fault_output, label: 外部实测封波电平, source: instrument, role: actual, format: bool}
  - {key: fault_raw, label: 自然Fault原始状态, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.fault_raw}
gap: [case_implementation_gap, external_fault_route_mapping_gap, external_output_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_015
case_name: 死区安全窗口动态更新
report_feature: |-
  1. ETIM 死区支路处理
  2. ETIM 死区运行更新
p_level: P2
feature_refs: [ETIM_F_032, ETIM_F_042]
method:
  inputs:
    - 动态延迟矩阵：对已确认支路分别更新上升、下降及两种延迟，旧新值8与32 Tick双向切换；源使用A_B模式，period_ticks为24000，A为6000、B为12000，保持处理直出和输入选择不变。
    - 安全窗口依据：根据独立delay_tick_seconds确认上一周期全部延迟已在本周期之前完成，当前计数1000至2000内写入新延迟且早于本周期全部边沿；全部输入高低平台远大于新旧延迟与写事务上界。
  steps:
    - 旧延迟基线：门禁和路由确认后配置旧延迟，关闭Fault和同步，以独立输入参考及输出Observer采集至少四个稳定周期。
    - 运行窗口确认：保持计数和PWM连续运行，基于已知边沿及最大旧延迟确认没有尚未完成的延迟事件，记录进入安全窗口的COUNT.LIVE。
    - 新延迟有界写入：在计数1000至2000内完成本轮单边或双边延迟写入，保存每次写前后计数和顺序，不改MUX、不关闭PWM、不通过停止后配置替代。
    - 过渡边沿采集：连续保存写入所在周期和之后至少四周期的输入输出边沿，要求更新窗内没有额外输出变化。
    - 延迟新旧比较：写入之前各边沿符合旧延迟，写入所在周期的后续被选边沿即使用新延迟，未更新的另一极性保持原值，不允许等到下一周期才加载。
    - 双向参数复核：交换新旧延迟并重复安全窗口更新，分别覆盖上升、下降和两者，使用独立时间预算判断每条边沿而非只看稳定高宽。
    - 数据与安全收尾：汇总更新窗口、完整波形和新旧Expected，确认无丢边或多边后停止输出，恢复延迟旁路；不对延迟正在计数时改值作未证实推断。
  observations:
    - 真实写入窗口：COUNT.LIVE证明运行中写入且无跨界，独立输入边沿与最大延迟模型证明当时没有未完成延迟。
    - 动态输出边沿：PWM_OUTPUT.EDGE_TIMES逐极性匹配旧新延迟，写入所在周期即可区分立即更新与周期Shadow。
  pass_criteria:
    - 更新作用正确：两方向所有组合均在同周期后续边沿采用新值，未选极性不变，实测延迟符合独立时钟和仪器误差预算。
    - 过渡无毛刺：安全窗口无额外边沿，预期边沿无遗漏，所有写事务有完整计数窗；窄脉冲或延迟计数期间更新属于本轮范围外扩展，不据此放宽本Case判据。
timeout: 每实例10秒，单次连续采集最长5秒。
cleanup: [停止PWM和计数, 恢复延迟旁路与停止配置, 停止仪器采集, 清本轮pending并释放支路]
resources: {minimum_level: R4, full_coverage_level: R4, board: 可独立观测原输入参考和处理输出且无功率负载, bench: 多通道示波器及独立延迟时钟和事务上界}
backend: [FPGA, Silicon]
evidence: [逐写入COUNT.LIVE和顺序, 输入输出连续波形, 新旧逐极性延迟Expected]
failure_observations:
  - {key: actual_delay, label: 动态实测延迟秒, source: instrument, role: actual, format: float}
  - {key: expected_delay, label: 当前边沿期望延迟秒, source: oracle, role: expected, format: float}
gap: [case_implementation_gap, delay_clock_mapping_gap, output_branch_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_016
case_name: 外部捕获值与DMA数据路径
report_feature: |-
  1. ETIM 捕获数据DMA搬运
  2. ETIM 相对捕获时间戳
  3. ETIM 周期与比较DMA请求
p_level: P2
feature_refs: [ETIM_F_043, ETIM_F_011, ETIM_F_033]
method:
  inputs:
    - 外部捕获矩阵：脉冲周期100毫秒且高宽40毫秒，以及周期200毫秒且高宽130毫秒；DUT采用四槽RISING/FALLING/RISING/FALLING、逐槽清零One-Shot，输入分频和滤波旁路，独立Observer实测输入。
    - DMA数据配置：分别选择四个已冻结CAP槽为固定源，目的递增搬运8个字，每请求一字且外围边界置哨兵；请求明确选择DUT的PERIOD而非未确认的CAPTURE事件，禁止软件DMA请求。
    - 时序隔离约束：DUT计数周期按最坏捕获完成时间和服务预算选择，至少四个最长输入周期且不超过1秒；冻结完成后停止外部脉冲并停止计数，DMA武装后再从当前计数继续运行至周期事件，不Rearm、不清计数、不改CAP数据。
  steps:
    - 捕获与仪器准备：门禁后连接安全脉冲源，配置长计数周期和四槽相对捕获，武装输入Observer并清历史pending，DMA保持停止。
    - 外部真实捕获：先启动DUT Capture再施加脉冲，在末槽完成后停止输入和计数，读取四槽CAPTURE.VALUE及本轮末槽RAW，确认One-Shot冻结。
    - 捕获Oracle校验：由实测输入高低间隔和独立计数频率验证第二至第四槽，首槽只保留真实值不猜启动延迟；保存冻结值作为逐字DMA数据Expected之一。
    - 冻结槽DMA武装：填充目的及边界哨兵，完成缓存准备，选择当前CAP槽固定源及PERIOD请求；保持计数停止跨两个预期周期，要求DMA剩余和目的均不变。
    - 周期请求搬运：保持Capture冻结且外部输入关闭，恢复DUT计数自然产生周期请求，等待DMA完成后停止计数，读取COMPLETE、REMAINING及同步后的Destination。
    - 双重数据比较：要求每目的字精确等于本轮当前槽冻结值且边界未改写，冻结CAP前后相同；后续槽还须满足外部时间Oracle，不能只比较两个同样错误的软件数组。
    - 槽和输入汇总：遍历四槽及两波形，保留捕获端和目的内存身份；本Case只证明Capture数据总线搬运，不声称CEVT请求选择、每次捕获DMA握手或无丢样流传输已覆盖。
  observations:
    - 捕获冻结端点：CAPTURE.VALUE及末槽RAW来自本轮外部脉冲，末三槽对应实测高低宽，搬运前后CAP保持。
    - DMA真实终态数据：DMA_CHANNEL.COMPLETE为有效、REMAINING为零，Destination各字与真实冻结槽值一致，停止计数负对照未传输。
  pass_criteria:
    - 捕获及搬运正确：两波形四槽共八实例均有真实末槽完成，后续槽时间正确，8字搬运及边界哨兵精确匹配，无软件DMA触发。
    - 证明范围清楚：Artifact明确PERIOD请求和CAP槽身份；逐Capture事件握手属于独立扩展，不能把重复读取冻结值称为连续采样DMA通过，连续数据目的另由P2_017承担。
timeout: 每实例30秒；捕获最长3秒，停止源负对照最长2秒，8字DMA等待最长12秒，超时Abort DMA。
cleanup: [先停止外部脉冲及DUT计数, Abort或关闭DMA并等待静止, 停止Capture和清pending, 释放数据及仪器和Peer]
resources: {minimum_level: R4, full_coverage_level: R4, board: 已确认外部Capture输入且DMA可访问冻结槽, bench: 脉冲源及独立时间Observer和片内DMA Peer}
backend: [FPGA, Silicon]
evidence: [真实外部输入波形, DMA前后四槽冻结值及末槽RAW, DMA终态和Destination及边界哨兵]
failure_observations:
  - {key: capture_value, label: DMA源实际捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: dma_remaining, label: DMA实际剩余量, source: peer, role: actual, format: decimal}
  - {key: expected_word, label: 期望目的字, source: oracle, role: expected, format: hex32}
gap: [case_implementation_gap, dma_request_mapping_gap, external_input_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_017
case_name: 连续捕获四槽周期快照DMA
report_feature: |-
  1. ETIM 捕获Continuous
  2. ETIM 捕获数据DMA搬运
  3. ETIM 周期与比较DMA请求
p_level: P2
feature_refs: [ETIM_F_014, ETIM_F_043, ETIM_F_033]
method:
  inputs:
    - 连续数据矩阵：每次运行8轮或64轮，DUT周期E为40000 Tick、四槽RISING/FALLING/RISING/FALLING且绝对连续捕获，同时产生A模式高宽2000 Tick、延迟旁路的周期参考输出；第j轮从0编号，令q为16j，四个刺激边沿相位分别为4000+q、10000+2q、22000+3q、30000+4q Tick，每行每槽均随轮次变化以暴露重复或混行。
    - 快照搬运配置：DMA采用硬件PERIOD请求、P2M、32bit、每请求四字；有限LLI每节点搬一行，源递增读取四槽后由下一节点回到首槽，目的递增至下一行，链尾终止。目的前后保留哨兵；请求路由必须为一次请求一次确认而非持续至整链完成。
    - 独立时序依据：脉冲源预载N段有限列表，由DUT每周期参考边沿逐次触发相应编号的四边沿段，段间保持LOW，不用PC逐段下发；外部Observer同时测输入和周期参考。参考边沿到计数零点的延迟界、捕获及计数时钟误差、整行DMA和描述符准备上界预先固定；每槽时间Oracle总误差小于8 Tick，DMA最坏时间小于周期请求到下一轮首槽覆盖的保护窗，运行前检查全部轮次而非用结果反推上界。
  steps:
    - 时序与门禁准备：确认安全输入和无负载周期参考输出，配置计数、四槽连续捕获、滤波及输入分频旁路，关闭Capture清计数、同步装载和Fault；固定每轮边沿Expected及保护窗。
    - DMA先行武装：初始化目的哨兵和有限描述符，完成缓存准备，选择PERIOD请求并启用DMA；保持计数和刺激停止跨两个预期周期，确认目的、剩余量均未变化且无软件请求。
    - 连续生产启动：先武装预载的有限列表和Observer，再启动DUT计数、PWM参考及Capture，每个周期参考触发列表下一段，恰好输出N段后停止接受触发；至有限链完成保持Capture连续加载，不冻结、不Rearm、不逐轮停机或CPU补写目的。
    - 周期快照执行：每轮四边沿完成后由该轮PERIOD请求搬一行，目标侧仅等待有界DMA终态；外部Observer连续记录全部输入和周期基准，不以ISR调用次数代替DMA硬件进度。
    - 完成数据取回：DMA完成后先停止输入和DUT计数，再确认DMA静止、读取COMPLETE及REMAINING并同步目的缓存，保存每节点配置和真实目的行、首尾哨兵及末轮CAP值。
    - 逐行独立比较：由该轮实测输入相对周期参考的边沿时间及独立计数时钟换算四槽Expected，逐行逐槽匹配；所有行必须依次不同，无重复、缺行或上一行与下一行混合，末行另与停止后CAP端点一致。
    - 轮数复核收尾：8轮及64轮各执行并保存完整波形和目的附件，链外哨兵保持、硬件无DMA错误且只完成计划行数；清理后说明这是PERIOD快照，不把它替代为每个CEVT自动握手或任意高速无丢样认证。
  observations:
    - 连续输入基准：STIMULUS_OUTPUT.EDGE_TIMES与PWM_OUTPUT.EDGE_TIMES证明每轮四边沿确实落入该轮计数窗口且保护窗未被侵入，建立独立逐行时间Oracle。
    - DMA终态与目的行：DMA_CHANNEL.COMPLETE有效、REMAINING为零，Destination逐行保存四个真实时间戳且边界未改写；末行CAPTURE.VALUE独立读回只能校验末行，不能替代全部行Oracle。
  pass_criteria:
    - 行数据与时序正确：两轮数实例每行四槽均在固定时间预算内，行顺序唯一且完整、无混行；保护窗与DMA独立上界满足，不能只验最后四字。
    - 请求与终态正确：停止生产的负对照不搬运，启动后只完成计划有限链，真实DMA终态和缓存同步后的目的同时成立，Capture期间未冻结或由软件产生DMA请求。
timeout: 每实例在运行前按最慢计数时钟计算N乘E的时长并加20%及2秒余量；任一超时先停止生产者，再Abort DMA并等待静止，不重试同一序列。
cleanup: [停止外部序列与DUT计数和PWM参考, 关闭Capture并确认DMA静止, 清本轮pending和释放DMA路由, 硬件静止后释放描述符及数据和仪器]
resources: {minimum_level: R4, full_coverage_level: R4, board: 有外部捕获输入和独立周期参考输出且DMA可访问四槽, bench: 可触发有限序列的脉冲源及多通道时间Observer和片内DMA Peer}
backend: [FPGA, Silicon]
evidence: [完整输入及周期参考边沿, 有身份的逐行Destination与Expected, DMA硬件终态及描述符和边界哨兵]
failure_observations:
  - {key: actual_row, label: 本轮DMA实际四槽数据, source: artifact, role: actual, format: text}
  - {key: expected_row, label: 独立时间期望四槽数据, source: oracle, role: expected, format: text}
  - {key: dma_remaining, label: DMA实际剩余量, source: peer, role: actual, format: decimal}
gap: [case_implementation_gap, dma_snapshot_timing_mapping_gap, external_input_bench_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: ETIM_P2_018
case_name: PWM Peer捕获选路与隔离
report_feature: |-
  1. ETIM PWM Peer捕获选路
  2. ETIM 捕获边沿选择
  3. ETIM 绝对捕获时间戳
p_level: P2
feature_refs: [ETIM_F_045, ETIM_F_009, ETIM_F_010]
method:
  inputs:
    - Peer路由矩阵：执行芯片适配中由要求和历史有效测试选定的有限路由清单，至少包含两个可区分Peer实例的选择交换及A/B输出辨别；Capability提供合法范围，不自动展开源与接收通道的笛卡尔积。Peer标准精度向上计数且关闭高精度、同步、保护和延迟；被选输出两波形为完整周期5000且高宽2000 Tick、完整周期8000且高宽5500 Tick。同一实例另一输出配置互补非50%波形，A/B分别作为被选输入，不能用同形波形掩盖A/B串路。
    - 输入隔离对照：每实例另选一个不同Peer实例的输出作为未选活动源，周期11000且高宽3500 Tick；被选Peer停止时其A/B均保持稳定，避免共享计数器造成对照污染，禁止由本DUT的PWM代替Peer。时钟比、Peer周期编码及捕获量化界在执行前固定。
  steps:
    - Peer和接收准备：分别通过各IP公共动作停止并配置两Peer，设置DUT最大周期、四槽绝对One-Shot、RISING/FALLING/RISING/FALLING、输入分频和滤波旁路，关闭DUT PWM及非目标同步和Fault。
    - 未选活动对照：被选Peer保持稳定，武装接收并清pending后先读取四槽基线，再仅启动未选Peer跨三个周期，读取四槽和CAPTURE RAW，要求槽值不刷新且没有新的捕获pending。
    - 被选波形启动：保持未选源运行，启动被选Peer并等待末槽真实pending，One-Shot冻结后停止被选Peer，读取四个CAPTURE.VALUE和各槽RAW，不使用预置数组替代端点。
    - 高低宽独立比较：按相邻模减得到高宽、低宽及同极性周期，以被选Peer的完整周期和高宽乘独立时钟比得到Expected；三者均须匹配，且与未选Peer的Expected可分离。
    - 输入选择交换：停止两源，重新配置DUT选择另一Peer实例的输出并交换两源身份，同时把新被选源配置为本轮被选波形、原被选源配置为11000/3500对照；重新武装后完整执行未选负对照和被选波形，不能只改字段读回。
    - 第二波形复核：把被选源改为第二组周期和高宽，从停止配置重新执行；保存每个Peer输出和DUT通道身份，避免互补A/B、同名通道或旧结果误绑定。
    - 路由汇总清理：本轮清单全部路由均完成两波形及未选对照，清单内未绑定项为Mapping缺口；清单外合法组合不计漏测，也不声明通过。保存清单及选择依据后先停止两Peer再清理Capture和路由。
  observations:
    - 未选源捕获端点：活动对照期间四槽CAPTURE.VALUE保持且IRQ_RAW.CAPTURE各槽无新pending，证明未选活动输入没有泄漏到接收器。
    - 被选源捕获时间戳：本轮四槽CAPTURE.VALUE和末槽RAW支撑高低宽与周期，三个时间量匹配被选Peer而非未选源，证明实际选路及捕获数据通路。
  pass_criteria:
    - 路由与隔离正确：两种选择方向的未选活动对照均无捕获，被选源启动后四槽确实更新；本轮清单保留实例和输出身份，不遗漏清单内未绑定项，不把代表路线外推为全输入认证。
    - 数字时间符合：每波形的高宽、低宽和周期均在独立时钟及捕获误差界内，与未选源Oracle区间不相交；仅证明数字Peer输入，不声称外部引脚或绝对频率认证。
timeout: 每路由参数5秒，单次末槽等待最多六个较慢Peer周期加1秒，超时停止两Peer且不隐式Rearm重试。
cleanup: [停止两个PWM Peer并保持稳定输出, 停止DUT Capture及计数, 清捕获pending并解除输入选择, 释放Peer和DUT资源]
resources: {minimum_level: R2, full_coverage_level: R2, board: 无外部跳线, bench: 两个可区分的片内PWM Peer输出及独立时钟映射}
backend: [FPGA, Silicon]
evidence: [Peer输出和DUT通道身份, 未选对照前后CAP及RAW, 被选四槽与独立高低宽及周期Expected]
failure_observations:
  - {key: capture_value, label: 被选源实际捕获值, source: dut, role: actual, format: hex32, semantic_ref: etim.feature.capture_value}
  - {key: unselected_raw, label: 未选源活动时捕获pending, source: dut, role: actual, format: bool, semantic_ref: etim.interrupt.capture_raw}
  - {key: expected_high, label: 被选源期望高宽Tick, source: oracle, role: expected, format: decimal}
gap: [case_implementation_gap, pwm_peer_action_mapping_gap, peer_capture_clock_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Mapping | Case Adaptation | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | IMPLEMENTATION_GAP=45 | IMPLEMENTATION_GAP=32 | 按实现工作、执行配置及局部判据分别推进；Q01～Q05未关闭；0个实现、0个实测 | `ET6801_etim.md` |

本汇总只统计已准入公共Feature和已定义PLAN，不是硬件PASS覆盖率。
参考方法与准备度详见[芯片文档](ET6801_etim.md)3.8及4.3。
未形成完整Oracle的必测目的仍在芯片文档保留；本轮范围外扩展不混入本轮完成Gate，也不改成SKIP或已覆盖。

## 5. Common Gap / Evolution

| Gap | 状态 | 未闭合内容与解除条件 |
|---|---|---|
| EG-01 | IMPLEMENTATION_GAP | 本轮只写文档；PC Driver/Case、Firmware Service/Wrap、Chip Driver及Capability均须独立任务实现并绑定R400，不能先注册PLAN |
| EG-02 | MAPPING_GAP | 内部输入路由、延迟旁路、逻辑通道、时钟比和捕获误差上界必须逐项有目标证据，不能以同源回环PASS自行标定误差 |
| EG-03 | UNKNOWN | 必测：最大窗口、实际1/2分频及唯一多数阈值已进入P2_004；采样时钟和分频公式仍需目标适用说明。双阈值仲裁、精确边界和高输入初始化瞬态为范围外扩展 |
| EG-04 | UNKNOWN | 必测：两支路正常选择、延迟、反相和安全窗口动态更新；处理支路文字冲突与delay时钟仍须答复。窄脉冲和在途改值为范围外扩展 |
| EG-05 | UNKNOWN | 必测：CBC/One-Shot、高低封波、重复输入、正常恢复以及历史明确的Fault互补输出；互补输出Expected须先定案。仅同拍撤销/Clear等竞态移出本轮，不移走互补目的 |
| EG-06 | UNKNOWN | 必测：内部同步、运行相位、外部相位及SyncOut，外送开关和可观察脉冲宽度映射须确认。停止时同步、同拍清零/同步及所有非内部源穷举为范围外扩展 |
| EG-07 | OUT_OF_SCOPE | P1_009/010和P2_009/015保留运行安全窗口的立即/Shadow判据；计数已越过新值、重合比较/周期点和延迟在途改值不在本轮基线，不视为已证明或硬件不支持 |
| EG-08 | MAPPING_GAP | 必测事件接收、真实Capture到内存和连续四槽数据已有P2_008～012/016/017；请求确认模式及DMA保护窗在实现时绑定。逐CEVT握手、未说明请求编码及接收Peer全部延迟/反相配置认证不在本轮基线 |
| EG-09 | OUT_OF_SCOPE | 必测的自然回卷/IRQ、单Tick高宽、3/4/5 Tick周期及近全量程真实捕获已保留。P=0精确行为、未提供规范的最高频率/精度认证和压力限值不阻塞本轮，不移植旧芯片电气数值 |
| EG-10 | MAPPING_GAP | 外部输入/输出Bench端点、仪器精度和计数时钟容差尚未绑定；P2普通测量方法保留，不能因当前未接线删除 |
| EG-11 | MAPPING_GAP | 必测为内部ETIM、PWM Peer代表路线、外部Capture及XBAR Fault；清单内路线必须落实。其他输入类、全部源乘全部接收通道及非内部同步源穷举为范围外扩展；ADC/DAC/ACMP接收端测试仍保留，不与Capture输入扩展混淆 |

优先顺序：先实现基础计数/IRQ/非法比较恢复链路，再按芯片文档4.3推进捕获、PWM及组合功能；接口、IRQ、内部路由和Peer动作缺失属于开发工作，不作为停止整个IP开发的理由。必要Oracle确实未知时只保留受影响目的，不猜测判据或发布完整Formal Case；硬件执行另需授权。
OUT_OF_SCOPE仅表示经本轮要求/历史目的复核后不进入本轮验收分母，不改变硬件能力、不生成SKIP，不授权删除已实现测试。
必要Oracle仍UNKNOWN时不得改写为DEFERRED；只有方法确定且仅缺物理资源时才可标记DEFERRED。后续明确增加要求时再纳入范围外扩展。

### 5.1 参考方法落实与开发入口

时间：2026-09-08 19:02 CST。此次只补证据到方法的对应关系和开发顺序，不改变32个PLAN的输入、步骤、Oracle或资源等级。

| 参考测试目的 | 已有公共方法承接 | 不可从参考代码直接继承的部分 |
|---|---|---|
| 滤波配置及输入捕获 | P2_004逐实例执行旁路基线、短脉冲抑制、长平台双极性通过 | 字段读回和IRQ出现不能替代短长判据；采样根、实际分频公式和刺激时间界须独立确认 |
| 输出支路延迟、反相及动态变化 | P2_005静态来源/边沿比较；P2_015无在途延迟的安全窗口更新 | 不照搬MUX编码、延迟时钟或只有循环改比较值的程序；动态比较不是动态死区覆盖 |
| Fault与互补输出 | P2_003保留旁路CBC/OS正常路径；EG-05保留尚缺Expected的互补目的 | 不把CBC互补程序称为OS互补三阶段验证；两个独立例程不能拼成组合覆盖，待判据确定后再评审如何纳入既有Fault方法 |
| 同步输出到外部端点 | P2_013软件单次、周期源交换、未选源及外送关闭负对照 | 外送函数名、源选择读回和固定等待不能证明实际开关及可测脉宽 |
| PWM Peer到捕获端 | P2_018保留非对称高低宽/周期、输入选择交换及未选活动对照 | 历史容差不是误差预算；时钟比、捕获量化界及Peer周期语义须在执行前独立固定 |

准备度按目标芯片记录，不增加机器Schema、Case状态或Registry条目。`ETIM_P0_001`、`ETIM_P0_002`、
`ETIM_P1_008`可先进入实现方案评审；这是已定义状态Oracle的有限子集，不表示全部Feature已覆盖。
其中计数分频在P0_001只验证配置读回，不证明实际速率；速率仍由P1_001/P2_001承担。
状态测试的等待窗也须满足其输入约束，只是不需要精确跨域时钟比或捕获量化Oracle。
其余Case按目标芯片分别完成实现、执行配置和必要判据。已有SVD与适用继承资料足以支撑的部分继续开发，不把额外手册或RTL作为统一前置条件；机器PLAN有效也不证明未知判据已关闭。

### 5.2 本轮仪器约束

时间：2026-09-08 20:16 CST。用户确认当前外部仪器只有示波器和函数发生器，本轮所有Case构造只使用这两类。
上述PLAN中的信号源、脉冲源、有限序列源及安全外部电压源均由函数发生器承担；独立外部Observer、边沿、输入和参考电压测量均由示波器承担。
不假设DMM、精密电压源、校准器、时间间隔分析仪、逻辑分析仪或Companion FPGA可用；片内ETIM/PWM/ADC/DAC/ACMP/DMA Peer不属于新增外部仪器。
DC、Burst、任意有限序列、双通道独立输出、最短脉宽和长记录并非任意型号都具备：执行前按实际型号、选件和校准资料核对功能、量程、带宽、存储深度、负载和误差预算。
能力或精度不够时保留受影响参数的未执行原因，不放宽Expected、不缩短近全量程或删去单Tick参数，也不自动换用第三类仪器；这不阻止无关的软件实现。
ADC的GPIO EOC标记只表示服务/ISR可见时刻，必须包含独立延迟上界，不能当作真实采样时刻；模拟结果仍从ADC结果及示波器实际输入电压交叉判断。
