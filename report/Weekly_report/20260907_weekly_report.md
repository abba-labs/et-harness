# ET MCU 自动化测试平台 周报

日期：2026-09-07 09:04 CST
本期：2026-08-31～2026-09-06；统计口径修订于2026-09-07 09:23 CST，源码及HIL证据基线未变化。
项目整体进度：公共测试链路已建立，IP持续接入与FPGA问题闭环进行中；尚无稳定的全项目工作项分母，不给开发完成度百分比。
当前目标：以ET6801 FPGA推进IP功能覆盖，优先闭合CAN外部通信、既有FAIL与缺失观测条件，同时完成ETIM实施前梳理。平台公共层保持跨芯片，不把FPGA结果扩大为Silicon验证。

## 一、基础功能设施

- **公共执行与证据链（已建立）**：沿用Case → Driver → Service → Wrap → Chip Driver及Canonical Result → 报告链路。本期IPCM、SYSCNT、SPI、CAN均已有正式执行结果和报告记录；报告成功不替代硬件断言。
- **双核与调试观测（已用于测试）**：IPCM的ET6801 Core0测试端/Core1响应端链路完成本期HIL；STIMER、SYSCNT已使用停核期间的DHCSR和计数器采样。SYSCNT暂停通过，不代表STIMER暂停通过。
- **外设连接与仪器（部分具备）**：SPI0/SPI1四线互联已形成有效收发证据；CAN0与外部CAN盒子的通信仍未闭合。STIMER事件输出、独立参考及SYSCNT新增外部脉宽Case仍缺对应接线或实现，不能因平台已接入示波器就视为这些Case可执行。
- **报告与软件验证（本期局部问题已修正）**：SPI、SYSCNT的重复观测聚合/数组形状问题已在各IP范围内修正并完成最终报告；旧失败Run保留。最近CAN工作记录的软件门禁为1336 PASS、17条件SKIP，17项为宿主C编译器条件，不进入硬件统计。

## 二、IP梳理与测试

### 2.1 各IP的Case梳理、开发与测试情况

**当前已梳理331条测试Case，完成开发246条，待开发85条；最近已知测试结果为232 PASS、6 FAIL、8 SKIP。** 这是开发存量与各Case最近结果的快照，不是本周同一SHA全量回归。

六列的含义如下：

- **梳理的测试Case**：当前公共IP契约Case Catalog中已经登记的唯一Case ID，包括SPEC、PLAN和有Case ID的设计待确认项；不包含已废弃ID，不把Feature数或参数Execution数当Case数。
- **完成开发的Case**：已经形成正式SPEC、进入该IP Registry并具有PC测试实现及所需公共执行接口的Case。接线、仪器或目标安全映射未具备时可以SKIP；开发完成不等于硬件功能通过，也不等于所有芯片适配完成。
- **测试PASS / 测试FAIL / SKIP**：按每条已开发Case最近一次有效实际执行结果统计，跨Run按Case ID去重；后续未选中不抹掉已有FAIL。SKIP只计真实运行跳过，不计人工暂缓的PLAN。
- **待开发的Case**：已梳理但尚未完成正式Case开发，含只完成部分接口、尚未注册及设计条件待确认的项；`待开发 = 梳理总数 - 完成开发`。

| IP | 梳理的测试Case | 完成开发的Case | 测试PASS的Case | 测试FAIL的Case | SKIP的Case | 待开发的Case |
|---|---:|---:|---:|---:|---:|---:|
| AES | 26 | 26 | 26 | 0 | 0 | 0 |
| CAN | 42 | 16 | 15 | 1 | 0 | 26 |
| CORDIC | 24 | 24 | 23 | 0 | 1 | 0 |
| CPU | 2 | 0 | 0 | 0 | 0 | 2 |
| CRC | 24 | 23 | 22 | 1 | 0 | 1 |
| CRG | 0 | 0 | 0 | 0 | 0 | 0 |
| DMA | 39 | 28 | 28 | 0 | 0 | 11 |
| ETIM | 32 | 0 | 0 | 0 | 0 | 32 |
| FMAC | 23 | 23 | 23 | 0 | 0 | 0 |
| GPIO | 0 | 0 | 0 | 0 | 0 | 0 |
| IPCM | 13 | 13 | 13 | 0 | 0 | 0 |
| SPI | 17 | 12 | 11 | 0 | 1 | 5 |
| SPINLOCK | 11 | 11 | 11 | 0 | 0 | 0 |
| STIMER | 16 | 16 | 12 | 1 | 3 | 0 |
| SYSCNT | 8 | 7 | 7 | 0 | 0 | 1 |
| SYSCTRL | 0 | 0 | 0 | 0 | 0 | 0 |
| UART | 40 | 33 | 30 | 0 | 3 | 7 |
| WDG | 14 | 14 | 11 | 3 | 0 | 0 |
| 合计 | 331 | 246 | 232 | 6 | 8 | 85 |

数量关系：`331 = 246 + 85`；本次已开发Case均有最近已知结果，故`246 = 232 + 6 + 8`，已开发但尚无任何有效执行记录的Case为0。**“有最近结果”不代表当前HEAD已全量复测，也不代表所有参数已覆盖。**

需要结合表格理解的边界：

1. CAN的1 FAIL是`CAN_P0_003`最近实际外部执行失败；17:32片内Run未选中它，不将其清零。`P1_011`的PASS仅有两个内部参数，四个外部参数未测试，不能扩大为整条Case所有参数通过。
2. CRG、GPIO、SYSCTRL的0表示**尚未建立独立测试Case目录**，不表示没有功能、没有接口代码或不再需要开发；三者的完整IP测试工作量尚未纳入331条分母。CPU当前仅梳理2条NMI Case，也不代表CPU全部功能范围。
3. STIMER的16条公共Case执行链已实现；`P2_002`仍缺ET6801已审核安全Source/路由，运行SKIP。该目标适配/Bench工作仍待闭合，不能因“待开发Case=0”宣称该IP已经验收。
4. 331条中包含CAN、SPI各3条设计待确认目标；它们有明确Case ID，但尚未达到可直接实施的PLAN深度，统一列入待开发，不能写成设计已全部闭合。
5. 另有1条框架通信Case，属于基础设施，不混入IP合计。

证据范围：AES/CORDIC/CRC/DMA/FMAC/UART/WDG沿用08-28全量记录，SPINLOCK沿用08-28双核记录；IPCM为09-03，SPI/SYSCNT为09-04，CAN为09-05按Case合并；STIMER仅`P2_003`更新为09-03，其余沿用08-28。各Run/SHA详见第四节。当前HEAD晚于这些证据；8月28日原始Run未在正式仓库找到，相关数量来自芯片文档保存的历史记录，本次未重新核验原始JSON。不计算跨期总体HIL通过率或全项目开发完成度。

**2026-09-07 09:23 CST口径修正**：09:04初稿把246条已注册/已开发Case当作梳理总数，遗漏未注册目标；本版改为331条梳理、246条开发、85条待开发，并把CAN最近实际外部FAIL纳入6条FAIL。没有新增执行或改写任何原始测试结果。

### 2.2 本期进展与待开发范围

- **CAN（开发、片内验证推进；外部通信阻塞）**：新增/完善复位与INIT/CCE保护、INT0/INT1中断路由与独立W1C清除、16KiB Message RAM固定/地址模式及March C-、三实例并存切片隔离。当前15条选中Case通过，但`P1_011`仅两个内部参数通过，四个外部参数未选；这不证明外部IRQ链路。42条目标中注册16条，尚有26条未注册；原13项可继续片内开发的任务已闭合4项，其余9项仍有实现缺口。
- **SPI（已注册范围完成本期执行）**：12条中11 PASS、1 SKIP。双SPI交换角色、CPOL/CPHA及帧宽矩阵完成；关闭Target内部回环的参数证明PAD双向数据，开启回环的参数不冒充完整外部链路。FIFO容量修正为实测32，阈值仍受四位字段0～15限制；自然Overflow、IRQ和DMA传输通过。17条设计目标另有5条未注册，不计作运行SKIP。
- **IPCM（13条全部PASS）**：Core0/Core1实际双核链路覆盖消息长度、Clear/Release、Polling/IRQ、16个Mailbox及跨核场景；使用当前正式Case和独立响应端，不以历史双核PASS代替本次执行。
- **SYSCNT（7条全部PASS，外部新增项待实施）**：64-bit装载、启停、进位/回绕、频率标识、DWT参考间隔、Debug Halt及重复启停完成。参考间隔检查不代表绝对晶振精度测试。`SYSCNT_P2_003`为新增PLAN，尚缺本地脉冲接口、Case及确认后的GPIO/示波器连接；人工“暂不测试”不是pytest SKIP。
- **STIMER（专项仍FAIL）**：9月3日仅复测`P2_003`，采样已放到CPU停核期间，排除了恢复后执行时间污染；PAUSE仍计数，需设计人员确认Halt关联。其余Case没有本期全量复测。
- **DMA（梳理39、开发28、待开发11）**：28条已开发Case保留历史PASS；剩余11条是Priority竞争、Suspend/Resume、无效LLI、受控Bus Error、多Core TCM视图，以及Master选择、Protection、最大Burst、Flow Controller、低功耗和DFT/Test模式。不能用28条PASS宣称39条目标已全部开发。
- **UART（梳理40、开发33、待开发7）**：33条已开发Case为30 PASS、3 SKIP；待开发为`P3_001～P3_006`及`P3_008`，覆盖RS485模式/方向与时序、SIR/低功耗SIR、外部波特率测量及保护属性。这7条PLAN不是运行SKIP。
- **AES、FMAC、SPINLOCK（保留历史全注册PASS）**：梳理数与开发数分别26/26、23/23、11/11；未取得本期新全量HIL，不宣称当前固件集成状态已复测。
- **CRC、CORDIC、UART、WDG（保留历史结果及问题）**：CRC Overflow 1 FAIL；WDG复位/轮次/分频3 FAIL；CORDIC 1项芯片不适用SKIP；UART 3项能力或确定性刺激SKIP。详见下文，不将旧问题写成本周新发现。
- **ETIM（梳理32、开发0、待开发32）**：已收敛45个Feature、32个PLAN；全部未注册实现、未HIL。5项局部问题仍限制判据，不能宣称所有方法完全闭合。32条进入梳理总数和待开发，不进入PASS/FAIL/SKIP。
- **CPU（梳理2、开发0、待开发2）**：`CPU_P1_001` NMI路由配置/状态、`CPU_P1_002` NMI有界交付已有PLAN，但没有独立注册Case；被WDG跨IP测试调用不能代替这2条Case的实现和执行。
- **CRG、GPIO、SYSCTRL（独立Case尚未梳理）**：已有跨IP支撑Owner/接口和文档；不能由被其他Case调用推导为独立IP全功能PASS，后续仍需确定独立测试范围。
- **CRC_P1_011**：旧Result节拍Oracle已撤销，当前是DMA Request水位PLAN；未注册、未测试，不计当前CRC的FAIL或SKIP。

梳理/开发数量来自各IP公共契约的Case Catalog、SPEC/PLAN与Registry/测试函数交叉核对；结果来自对应`ET6801_<ip>.md`及Canonical Result。待开发数量可追溯到：[CAN](../../test_case_doc/can/can.md)、[CPU](../../test_case_doc/cpu/cpu.md)、[CRC](../../test_case_doc/crc/crc.md)、[DMA](../../test_case_doc/dma/dma.md)、[ETIM](../../test_case_doc/etim/etim.md)、[SPI](../../test_case_doc/spi/spi.md)、[SYSCNT](../../test_case_doc/syscnt/syscnt.md)、[UART](../../test_case_doc/uart/uart.md)。这8个IP的待开发数`26+2+1+11+32+5+1+7=85`。

### 2.3 当前FAIL明细

#### FAIL Case `CRC_P1_012`：FIFO Overflow状态与恢复

测试目的：验证紧凑输入触发Overflow报告，且重新进入模块后CRC计算恢复正常。

测试Feature：

1. `CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`置位。
2. Disable/Re-enable后的CRC计算恢复。

测试方法：

1. 经CRG复位ET6801 CRC实例并复位Resource池，启用CRC32；多项式`0x04C11DB7`、初值`0xFFFFFFFF`、ByteSwap开启。
2. 配置`CRC.FIFO_TRHD.CRC_FIFO_TRHD(bit3:0)=1`，读取输入前Overflow。
3. 目标端一次原子Burst向`CRC.IR`连续写7个`0x12345678`，读取`FIFO_OVF.bit0`，期望从0变1。
4. Disable/Re-enable，使用相同配置计算字节`01 02 03 04 05 06 07 08`，比较结果及剩余输入计数。

失败现象：

- `FIFO_OVF=0x00000000`，bit0输入前后均为0，期望输入后为1。
- 恢复CRC实际/期望均为`0x140B8DD8`，剩余输入计数为0。

结论：CRC计算与恢复正常，Overflow报告失败。芯片文档记录人工已确认当前FPGA的FIFO_OVF功能问题；范围仅限当时FPGA实现，不扩大为硅后结论。依据：[CRC当前状态及人工确认](../../test_case_doc/crc/ET6801_crc.md)。

#### FAIL Case `STIMER_P2_003`：Debug Halt时PAUSE未冻结

测试目的：验证CPU实际Halt期间，PAUSE冻结计数而RUN_FREE保持计数。

测试Feature：

1. `STIMER0.STM_SET.STM_CPUHALT_MODE_R(bit7)`策略配置及回读。
2. CPU Halt期间计数冻结/运行差异。
3. CPU恢复运行。

测试方法：

1. CRG复位STIMER0和Resource池，配置长周期Free-Run计数。
2. 分别设置`STM_CPUHALT_MODE_R(bit7)=0/1`（PAUSE/RUN_FREE），通过J-Link AP[1]使目标Cortex-M7停核。
3. 在停核内读取`DHCSR.S_HALT(bit17)`、`CNT_RPT`、`STM_SET`、DHCSR；请求200ms间隔后重复。两组计数均不是Resume后采样。
4. 要求两次采样前后bit17均为1，PAUSE计数不增长、RUN_FREE增长；随后Go并确认bit17=0。

失败现象：

- 两种策略各四次停核DHCSR均为`0x00030003`，bit17=1，CPU确实停核。
- PAUSE：`STM_SET=0x00000003`，bit7=0；`CNT_RPT: 0x013F16A9 → 0x018F5043`，增长5,257,626，期望冻结。
- RUN_FREE：`STM_SET=0x00000083`，bit7=1；`CNT_RPT: 0x00607D81 → 0x00AECADF`，增长5,131,614。
- Go后DHCSR=`0x01010001`，bit17=0，恢复正常。200ms仅为请求间隔，未用于精确频率计算。

结论：策略回读、停核、RUN_FREE及恢复有效；PAUSE未冻结。已排除CPU未停核和配置未写入，具体Halt信号、时钟域及多核关联仍需设计确认，未证明具体RTL根因。依据：[STIMER停核证据](../../test_case_doc/stimer/ET6801_stimer.md)。

#### FAIL Case `WDG_P0_004`：超时系统复位与跨重启记录

测试目的：验证WDG自然超时能触发系统复位，并由新Session和实例专属记录证明复位来源。

测试Feature：

1. `WDG0.CTRL.RST_EN(bit0)`控制真实系统复位输出。
2. `SYSC.RST_REC`的WDG0复位记录bit2与WDG1对照记录bit3隔离及清除。
3. 系统复位后的断线、HELLO/Discover及新Session恢复。

测试方法：

1. 复位WDG0（触发端）、WDG1（记录对照端）及Resource池；解锁、禁用两个实例并清除历史记录。
2. WDG0配置`RELOAD=0x004C4B40`（5,000,000），`MODE.WWDG_MODE(bit0)=1`独立模式，`CTRL.RST_EN(bit0)=1`，`EN.WWDG_EN(bit0)=1`。
3. 启动响应后不再发送WDG业务命令，由公共生命周期观察20s内真实断线并重连。
4. 仅在成功重连后检查WDG0复位记录bit2=1、WDG1记录bit3=0，再W1C清目标记录并复读；本次未到达此步骤。

失败现象：配置和启动已执行，但20s内目标通信始终在线，未出现预期断线/重连。跨重启寄存器值未取得，不能补写为0或1。

结论：配置/启动链路已执行；未观测到WDG输出形成系统复位，跨重启记录未验证。需设计人员确认Reset Output到系统复位及持久记录映射，不能仅凭在线超时定位具体RTL根因。依据：[WDG当前状态](../../test_case_doc/wdg/ET6801_wdg.md)。

#### FAIL Case `WDG_P1_003`：首轮IRQ、次轮Reset模式

测试目的：验证自然超时的首轮IRQ和次轮系统复位顺序，并为同轮IRQ+Reset模式建立独立证据。

测试Feature：

1. `WDG0.WORK_MODE.WWDG_WORK_MODE(bit0)=0`的首轮IRQ。
2. 次轮Reset Output和持久复位记录。
3. bit0=1的同轮IRQ+Reset及双记录（本次未到达）。

测试方法：

1. 复位WDG0和Resource池，解锁、禁用并清IRQ/历史记录。
2. 设置`RELOAD=0x004C4B40`、独立模式、`CTRL.RST_EN(bit0)=1`、`WORK_MODE.WWDG_WORK_MODE(bit0)=0`；`INT_EN.bit0=1`、`INT_MASK.bit0=0`，启动计数。
3. 等待自然Timeout ISR交付并读中断记录；不使用软件Force代替自然超时。之后停止WDG业务命令，等待30s内系统断线/重连。
4. 重连成功才检查`SYSC.RST_REC.bit2=1`，随后重新建基线切到WORK_MODE.bit0=1验证同轮双记录；本次在步骤3停止。

失败现象：第一轮Timeout IRQ能够到达；第二轮等待30s，目标仍在线，没有系统复位。不能把未执行的同轮模式写成PASS，也没有新的跨重启记录值。

结论：首轮自然IRQ有效，次轮系统复位失败；同轮模式后续步骤未验证。Reset链路及持久记录映射仍待设计确认。依据：[WDG当前状态](../../test_case_doc/wdg/ET6801_wdg.md)。

#### FAIL Case `WDG_P2_001`：分频读回正确但计数速率未变化

测试目的：验证CRG选择APB1的/1与/2分频后，WDG真实Counter体现对应速率差。

测试Feature：

1. `CRG.PLLCLK_CFG3.CRG_WDG0_SEL(bit0)`时钟源选择。
2. `CRG_WDG0_STB(bit6:1)`分频配置/回读。
3. `WDG0.CUR_VAL`实际递减速率。

测试方法：

1. 复位WDG0和Resource池，保存原始CRG配置，关闭WDG及IRQ。
2. 经CRG Owner设置`CRG_WDG0_SEL(bit0)=1`选择APB1，`CRG_WDG0_STB(bit6:1)`编码按`0,1,1,0,0,1,1,0`交错配置；0=/1，1=/2，每次读回源及分频字段。
3. 使用相同`RELOAD=0x004C4B40`、`CTRL.RST_EN(bit0)=0`，使能后在50ms请求窗口前后读取CUR_VAL，用PC单调时间实测间隔计算速率；两种编码各取4次中位数。
4. 要求Counter实际递减、读回匹配，`rate(div0)/rate(div1) >= 1.5`；最后禁用WDG并恢复时钟配置。

失败现象：APB1源及STB编码0/1读回正确，但中位速率为12,421,269.38与12,508,109.44 count/s；比值0.993057，低于1.5。

结论：配置传递、寄存器读回及计数推进正常；速率未体现分频。当前FPGA真实时钟路径/Divider接入仍待确认，保持严格FAIL，不放宽阈值。依据：[WDG分频问题](../../test_case_doc/wdg/ET6801_wdg.md)。

### 2.4 本轮未选中但仍未闭合的外部FAIL

#### FAIL Case `CAN_P0_003`（最近实际执行，非本轮结果）：正常外部总线

测试目的：验证ET6801 CAN0与ZLG USBCANFD_200U（设备0、CAN1通道，外部响应端）经真实收发器和总线完成双向数据及ACK。

测试Feature：

1. 非回环Classic CAN正常发送、ACK及TX完成。
2. 外部节点真实接收及反向帧接收（失败后未完成）。

测试方法：

1. 从连接配置选择CAN0、GPIO58 RX/GPIO59 TX和CAN盒子通道；预期连接为CAN0 TX/RX → 收发器 → CANH/CANL → 盒子，物理链路是否有效正是待定位项，不宣称已电气验证。
2. 复位CAN/资源，配置500kbit/s Classic CAN；`CAN0.CCCR.FDOE(bit8)=0`，回环关闭，正常模式`CCCR.MON(bit5)=0`，退出INIT后bit0=0。
3. 配置TX槽0和接收ID`0x321`的Filter。发送ID`0x123`、DLC=8、序号1/2的两帧；向`TXBAR.AR(bit31:0)`写`0x00000001`请求槽0，要求`TXBTO.TO(bit31:0)`的bit0=1且盒子逐字节收到。
4. 正向成功后才由盒子发送ID`0x321`两帧，CAN0读取并核对；本次在正向TX完成等待处失败。

失败现象：前次正式外部Run记录Pending=1、Completed=0（对应`TXBRP.TRP(bit31:0)`的bit0=1、`TXBTO.TO(bit31:0)`的bit0=0）；协议状态为ACK Error，TEC=128、REC=0、BUS_OFF=False，盒子错误值`0x00000000`。期望TX完成并由盒子接收到完整帧；反向验证未完成。

结论：片内回环结果不能覆盖此FAIL；外部链路未打通，ACK缺失原因尚未确认，暂时不能确定是硬件Feature故障，还是测试刺激与真实条件不匹配。9月5日17:32片内Run未选择此Case，不能据此关闭问题。依据：[CAN状态及外部Run指针](../../test_case_doc/can/ET6801_can.md)，正式失败Run为`20260905_135501_157677_local_et6801_fpga_atp_testing`；另行诊断不替代Formal结果。

### 2.5 SKIP明细

以下8条按运行SKIP保留；能力不适用、实现映射缺口、物理Bench缺口及不确定刺激分别说明。门禁前可能已做CRG/Resource隔离复位，不把“未配置测试功能”误写为“完全没有硬件动作”。

#### SKIP Case `CORDIC_P2_001`

测试Feature：CORDIC DMA输入、计算完成及DMA结果搬运等价性。

测试方法：

1. 若芯片支持并有审核后的映射，先Polling计算Q1.31的SQRT(0.25)，再配置相同输入的DMA模式和两条DMA通道。
2. 先武装结果通道，再启动输入通道；检查两通道完成、无DMA错误，并将目标Buffer与Polling及独立Golden对照。

测试现象：Runtime Capability拒绝DMA工作模式；未配置该DMA路径、未发送DMA激励。

SKIP原因：8月28日设计人员确认ET6801 CORDIC不支持DMA模式，属于NOT_APPLICABLE，不是接线缺失或未修复DMA故障。仅当后续权威能力声明改变时恢复。依据：[CORDIC最终修正](../../test_case_doc/cordic/ET6801_cordic.md)。

#### SKIP Case `SPI_P1_001`

测试Feature：单SPI的MOSI→MISO真实PAD回接，不使用内部回环。

测试方法：

1. 满足单实例短接且连接文件声明loopback角色后，复位SPI/资源并配置GPIO；内部Loopback关闭。
2. 覆盖4种CPOL/CPHA、3个帧宽节点、3个分频节点，每节点发送两组8帧Pattern；检查RX逐帧一致、BUSY清零和无FIFO残留。

测试现象：36个参数在配置前因无loopback角色跳过；未配置硬件、未发送回接激励。

SKIP原因：当前是SPI0/SPI1的SCLK、CS、MOSI、MISO四线互联，不是单SPI MOSI与MISO短接。需另行确认安全接线并声明对应实例/PAD角色。依据：[SPI当前状态](../../test_case_doc/spi/ET6801_spi.md)。

#### SKIP Case `STIMER_P1_008`

测试Feature：Compare事件脉宽配置与实际输出脉宽比例。

测试方法：

1. 完成STIMER0事件输出到示波器或FPGA采样端的路由后，配置Compare0、Free-Run和固定周期，依次设置最小/代表/扩展脉宽。
2. 由真实Compare IRQ确认事件，同时读取外部正脉宽/周期，比较其比例与配置脉宽/计数周期比例。

测试现象：缺少`stimer_output`逻辑观测器绑定，在取得观测器阶段停止；未进入脉宽测试配置、未发送事件输出激励。隔离复位不作为功能测试证据。

SKIP原因：缺少输出路由、示波器/FPGA采样接线及Observer绑定。依据：[STIMER当前状态](../../test_case_doc/stimer/ET6801_stimer.md)。

#### SKIP Case `STIMER_P2_002`

测试Feature：外部紧急事件触发计数捕获。

测试方法：

1. 映射完备后选择已审核的逻辑紧急源/组，配置长周期Free-Run及捕获路由，读取触发前COUNT.LIVE。
2. 通过`stimer_emergency_input`脉冲源发一个有界脉冲，读取EMERGENCY_CAPTURE.COUNT和触发后COUNT.LIVE，要求捕获值落入本次推进窗口；退出关闭路由/输出。

测试现象：Runtime缺少START_STOP、PERIOD、FREE_RUN和EMERGENCY_CAPTURE所需组合，在功能激励前停止；未配置紧急捕获路径、未发送外部脉冲。

SKIP原因：当前Service/Capability存在执行映射缺口，不是最终硬件“不支持”结论；修复映射后仍需审核安全Source和物理接线。依据：[STIMER当前状态](../../test_case_doc/stimer/ET6801_stimer.md)。

#### SKIP Case `STIMER_P3_001`

测试Feature：Free-Run运行窗口内，周期输出、IRQ累计及计数稳定性。

测试方法：

1. 取得独立参考频率与STIMER输出观测器，按参考及Runtime范围生成两组divider/period，配置Overflow脉宽并清理基线。
2. 每组运行有界2s窗口，读取外部周期、IRQ累计、COUNT.LIVE及诊断状态，与参考计算的事件数/频率比较；不是无限期老化测试。

测试现象：缺少`stimer_reference`独立参考观测器，未进入正式计数/波形测试配置、未产生长时测试激励。

SKIP原因：缺少独立参考、事件输出观测及对应稳定Bench条件，不能使用目标自身时基作为独立证明。依据：[STIMER当前状态](../../test_case_doc/stimer/ET6801_stimer.md)。

#### SKIP Case `UART_P1_008`

测试Feature：Framing Error（停止位采样不符合帧格式）及Line Error中断。

测试方法：

1. ET6801 UART1为接收端、UART2为发送端，UART2 TX→UART1 RX（反向TX/RX用于正常对测）；只有存在可确定性破坏接收停止位的刺激声明时，才设置两端停止位差异并开启LINE_ERROR。
2. 接收Capture先启动，发送4字节Pattern，检查Framing Error状态及真实中断来源，随后恢复正常收发。

测试现象：芯片记录保存了既往“停止位改变仍无法稳定触发FE”的观察；当前源码在缺少`stop_mismatch_framing`声明时门禁跳过。未进入错误帧配置/发送（门禁前隔离复位除外），不把既往尝试写成本轮激励。

SKIP原因：现有UART交叉连接不能确定性制造停止位采样错误，需要可控错误帧/FPGA波形发生器或已验证的精确刺激端。依据：[UART当前状态](../../test_case_doc/uart/ET6801_uart.md)；本次无法回读08-28原始Run，停止阶段按当前未变化Case源码核对。

#### SKIP Case `UART_P1_012`

测试Feature：Busy Detect中断、清除及数据通路恢复。

测试方法：

1. 复位UART1和资源，初始化8N1；Driver在FIFO启用、持续发送期间修改LCR，形成有界Busy Detect刺激。
2. 观察USR忙状态、IIR中断、清除/恢复事实；若触发成功，再用4字节内部回环核对恢复数据。

测试现象：已经初始化并尝试硬件刺激；限定窗口内未形成确定性Busy Detect，Driver返回OperationBusy，Case跳过。后续中断清除和4字节恢复验证不能记为已完成。

SKIP原因：缺少准确触发时序或可控制发送与LCR写入相位的刺激；当前证据不足以判定该Feature PASS/FAIL。依据：[UART当前状态](../../test_case_doc/uart/ET6801_uart.md)。

#### SKIP Case `UART_P3_009`

测试Feature：Direct FIFO访问及退出后正常数据通路。

测试方法：

1. 芯片明确支持FIFO_ACCESS后才初始化UART1并开启Direct FIFO模式，使用FAR/TFR/RFW路径直接访问FIFO。
2. Halt TX后写`0x5A`并从TFR读回，Resume后经RFW注入`0xA5`并从普通RX读回；关闭FAR并检查关闭状态，再用4字节普通FIFO回环验证恢复。

测试现象：Capability查询未声明FIFO_ACCESS，在初始化前停止；未配置Direct FIFO、未执行FAR/TFR/RFW访问（隔离复位除外）。

SKIP原因：ET6801当前UART组件参数不提供该能力，只有后续RTL/芯片明确支持时才执行。依据：[UART当前状态](../../test_case_doc/uart/ET6801_uart.md)。

## 三、本周结论与下一步

当前开发存量是**梳理331条、完成开发246条、待开发85条**；已开发Case最近结果为232 PASS、6 FAIL、8 SKIP，其中CAN外部FAIL仍未关闭。待开发主要集中在ETIM 32条、CAN 26条、DMA 11条和UART 7条，其余为SPI 5条、CPU 2条、CRC/SYSCNT各1条。

本期实质进展是IPCM、SYSCNT完成当前注册集合验证，SPI双IP物理收发和DMA验证闭合，CAN片内覆盖扩展；不是全平台所有IP都完成本周复测。CRG、GPIO、SYSCTRL尚未建立独立Case分母，不能用331条推导整个项目的最终完成度。

1. **先闭合真实阻塞**：确认CAN0收发器/总线/盒子的ACK链路后复测P0_003及外部IRQ参数；由设计人员确认STIMER Halt关联、WDG系统复位和分频路径、CRC FIFO_OVF修复条件。不通过取消选择、放宽断言或改SKIP消除FAIL。
2. **按待开发Case排期**：CAN 26条待开发中，剩余9项片内实现缺口不必等待外部通信；DMA 11条、UART 7条也需继续开发，不能因为既有注册Case通过而遗漏。SPI 5条、CPU 2条、CRC Request水位与SYSCNT外部测量各1条分别排期。
3. **补足观测与执行映射**：STIMER输出/独立参考与紧急捕获映射分别闭合；UART FE/Busy取得确定性刺激；SPI单实例回接需要单独接线，不破坏当前双IP拓扑。
4. **实施前冻结ETIM判据**：先回答剩余5项局部问题，再实现32条PLAN；不把文档数量当作已开发或已测数量。SYSCNT外部P2_003先补接口/Case和安全接线条件。
5. **建立新的集成基线**：相关公共固件、CRG/板配置发生变化后，需要人工批准的新FPGA全量回归；补齐旧Run归档可达性，并为Silicon单独制定执行计划。此周报任务未进行任何硬件操作。

## 四、统计口径说明

### 4.1 源码和执行身份

源码快照：正式仓库`ET_ATP_Testing`，分支`codex_dev`，HEAD=`38b301dc700e363568beaf97c01f994379c22700`；初稿编写前工作树干净，本次修订保留同一HEAD下的周报/索引未提交变更。只修改本周报及其索引，不改Case、固件、配置或旧日期报告。

梳理分母按当前公共契约第2节Case Catalog的唯一ID读取，并与机器块对照；其中246 SPEC、79 PLAN、6条设计待确认目标，共331条。开发分子按SPEC ID与各IP Registry、实际`test_*`函数一致性检查，不能只读顶层当前启用CAN的`IP_REGISTRY`。SPI第2节仍有历史“尚无实现”的文字，已被当前12 SPEC、Registry、源码及09-04正式结果取代，本周报不沿用该过时描述，也不越界修改契约。

| 证据组 | 时间（CST） | Source Revision | 范围/限制 |
|---|---|---|---|
| AES/CORDIC/CRC/DMA/FMAC/UART/WDG及STIMER非专项 | 2026-08-28 17:11～17:15 | `596c1a73b91f6af577b1b274d49c34f8d9fb823a`，clean记录 | 来自各芯片当前状态；正式仓库缺该原始Run，本次未复核原始JSON |
| SPINLOCK | 2026-08-28 20:20 | `ba1304b458148b681ec5f0a6a392cdf7c0757f76`，clean记录 | 双核历史结果；正式仓库缺该原始Run |
| STIMER | 2026-09-03 14:32 | `bedb44062af1d81b157cf980a7c7ca579061e4f0`，clean | 仅P2_003；此SHA为PC身份，板上固件/bit精确源SHA未取得 |
| IPCM | 2026-09-03 19:11 | `7d0d4a408cdc92f6837d4626b399619d4459ecfe`，clean | 13个注册Case |
| SYSCNT | 2026-09-04 06:39 | `2157037e3937d1d26a01390ae0bd652f40f788dd`，dirty | 7个注册Case；芯片记录说明dirty为文档修正，仍不写clean Exact-SHA |
| SPI | 2026-09-04 18:42 | `d6832926244edeb4b8170ef66d652e395f7d3648`，clean | 12个注册Case；复用`ba5ba0b535a4e45ba485caed564f7251f34dabc8`构建固件 |
| CAN外部 | 2026-09-05 13:55 | `0b9f7e38bc34773c4881f23c75cda9c37ae46f7c`，dirty | 仅P0_003，FAIL；作为该Case最近实际结果保留 |
| CAN | 2026-09-05 17:32 | `481d554000115e0c852506b05535e9d2ed988670`，clean | 15条选中Case；复用`e87ec3c2750a40aec2dd3d555e121a620eca61b5`构建固件 |

当前HEAD与08-28基线相比，旧AES/CORDIC/CRC/DMA/FMAC/UART/WDG/SPINLOCK的Case目录无差异，但公共CRG、板配置、服务清单及其他IP已变化；“Case未变”不足以证明当前集成固件仍PASS。所有证据Lane均为ET6801/XC7VX980T FPGA；Build ID带`silicon`只是工程命名，不能写成Silicon实测。

### 4.2 本次已只读核对的Canonical入口

- STIMER Session（原在 `artifacts/runs/**`，已随仓库清理删除）：1个选中Case，1 FAIL。
- IPCM Session（原在 `artifacts/runs/**`，已随仓库清理删除）：13个Case，34个参数Execution均PASS。
- SYSCNT Session（原在 `artifacts/runs/**`，已随仓库清理删除）：7个Case，23个参数Execution均PASS。
- SPI Session（原在 `artifacts/runs/**`，已随仓库清理删除）：12个Case，116 PASS/36 SKIP参数Execution；36个SKIP归属同一P1_001。
- CAN Session（原在 `artifacts/runs/**`，已随仓库清理删除）：15个选中Case，89个参数Execution均PASS；P1_011仅内部两个参数。
- CAN外部Session（原在 `artifacts/runs/**`，已随仓库清理删除）：1个选中Case P0_003，1 FAIL；与后续15条片内结果按Case ID合并，不修改任一Session。

同时按各Session下`cases/*/result.json`逐Case聚合核对，没有把参数节点数当Case数。上述Execution数仅用于核对统计，不作为开发进度。历史08-28缺失Artifact只保留芯片文档事实与原路径，不在旧副本寻找替代源码或伪造当前Evidence。

### 4.3 发布边界

本报告遵循R003固定四节结构与工作区DOCUMENTATION_RULES；报告工作流用于区分结果、解释和动作，按项目规则交付Markdown，不另建HTML或在线发布副本。工具箱代码摘要调用未返回有效输出，本次改用定向Registry、芯片契约、源码及Canonical JSON只读核对。没有执行新的软件功能测试、Keil构建、烧录、停核、仪器控制或HIL；文档检查结果不增加硬件PASS。
