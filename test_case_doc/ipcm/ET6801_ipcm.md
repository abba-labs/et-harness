# ET6801 IPCM Chip Analysis & Adaptation Contract

> 本文件只分析 ET6801 的 IPCM 硬件事实、Driver、历史测试和公共 Contract 适配。
> 3101与6003为单核芯片，本轮不读取、不引用，也不作为IPCM Feature或Case证据。
> 当前文档是开发输入；没有当前提交的实现或HIL证据时，不得填写PASS。

# 第一章 IP分析与Source Coverage

## 1.1 分析目标与证据优先级

本轮目标是把ET6801 IPCM收敛为可开发、可审核、可自动化的双核通信Contract。硬件结论按以下优先级建立：

1. ET6801目标SVD与由其生成的CMSIS头文件；
2. ET6801当前SDK Driver；
3. ET6801历史FPGA测试源码；
4. 当前平台Capability与现有Core1 Peer部署基础；
5. 设计推断只能标记为`NEEDS_VERIFICATION`，不能升级为硬件事实。

历史源码仅用于提取测试思想。源码存在、函数名或打印文本都不能继承为当前PASS；入口未执行、Oracle不足或配置不一致的历史Case必须在Source Item Trace中明确降级。

## 1.2 Source Map Coverage

| 来源 | 路径 | 状态 | 用途与证据边界 |
|---|---|---:|---|
| ET6801 IPCM SVD | `<et6801-verification>/Tools/RegGen/svd/ipcm_cfg.svd` | FOUND | Target Direct Evidence；确认16个Mailbox、16个事件Channel、7个Data Word、4种Mode、Pending和多目标位图。 |
| ET6801 merged SVD | `test_case_doc/ET6801.svd` | FOUND | Target Direct Evidence；确认IPCM实例、Base Address和16条IRQ。 |
| ET6801 generated header | `<et6801-verification>/DFP/Drivers/CMSIS/Device/Include/et6801.h` | FOUND | Target Generated Evidence；确认`IPCM_Type`、Mailbox步长、ISR数组和CFGSTAT偏移。 |
| ET6801 IPCM Driver | `<et6801-verification>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_ipcm.*` | FOUND | Target Current Driver Evidence；确认正式API、参数、截断行为和中断位集合缺陷。 |
| ET6801 DualCore Driver | `<et6801-verification>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_dualcore.*` | FOUND | Target Current Driver Evidence；确认Core ID读取和Core1启动能力；不把CORE2CORE门铃并入IPCM。 |
| ET6801 FPGA测试源码 | `<et6801-verification>/DFP/Test/FPGATest/ipcm_fpga_test.c` | FOUND | Target Historical Test；Case0~9为IPCM测试思想，当前入口只执行非IPCM的Case10。 |
| ET6801 requirements | Source Map登记`test_case`根下定向检索 | NOT_FOUND | 未找到独立IPCM需求文档；不凭空补充SVD/Driver未表达的Feature。 |
| current capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/ipcm.yaml` | FOUND | 仅表达实例、Base和16条IRQ；全部IPCM Field仍未进入语义层。 |
| capability audit | `test_case_doc/reference_data/et6801/capability_generation/audit/ipcm.yaml` | FOUND | IPCM寄存器Field均为`no_semantic_mapping`，证明当前YAML不是完整能力声明。 |
| current Core1 Peer | `firmware/chips/et6801/core1_peer`与`firmware/build/et6801/core1_peer` | FOUND | 已有ET6801 Core1映像和部署基础；IPCM Peer Job尚未实现。 |
| current platform IPCM code | `firmware/{wrap,services}`与`pc/et_test_platform/{drivers,test_cases}` | NOT_FOUND | 当前没有IPCM公共实现和Formal Case。 |

本轮没有扫描或读取3101、6003。ET6801 SDK检索限定在IPCM、DualCore和对应历史测试文件，没有对整个代码库或文档库做无目标扫描。

## 1.3 IP工作原理与应用

ET6801 IPCM是一组片内Mailbox，用于两个Core之间传递短消息、事件和ACK。每个Mailbox包含：

1. Source位集合：声明消息发起端及ACK投递事件通道；
2. Destination位集合：声明消息接收端事件通道；
3. 7个32-bit Data寄存器：单Mailbox共28字节Payload；
4. Send状态：向Destination发送消息、向Source发送ACK或恢复Inactive；
5. Manual/Auto ACK与Auto Link模式；
6. 每个事件Channel独立的Raw和Masked Pending Mailbox位集合。

典型Manual ACK链路为：Core0配置Mailbox并写Payload，发送到Core1事件Channel；Core1从Pending位集合定位Mailbox，读取Payload，可选更新ACK Payload，再显式发送ACK；Core0从自己的事件Channel收到ACK并读取Data。Auto ACK模式下，Responder释放自己的Destination位后由硬件向Source产生ACK。Auto Link把连续Mailbox串成更长的消息链。

IPCM应用包括双Core控制命令、轻量状态通知、短Payload交换和需要明确ACK的核间事务。它不是共享内存一致性机制，也不包含DMA、FIFO或CORE2CORE门铃中断；大数据共享应由共享内存承载，IPCM只传递控制和完成事件。

## 1.4 Claim Ledger

| Claim | 状态 | 直接证据 | 当前结论 |
|---|---|---|---|
| 实例与地址 | VERIFIED | merged SVD / generated header | 单实例`ipcm0`，Base=`0x40208000`。 |
| Mailbox数量 | VERIFIED | `IPCMCFGSTAT.Mailboxes`与`MBOX[16]` | 16个Mailbox，ID 0..15。 |
| Channel/IRQ数量 | VERIFIED | `IPCMCFGSTAT.Interrupts`、`ISR[16]`和IRQ表 | 16个事件Channel，对应`IPCM0_IRQn`~`IPCM15_IRQn`。 |
| 单Mailbox Payload容量 | VERIFIED | `DataWords=7`与`DR[7]` | 7个32-bit Data Word，共28字节。 |
| Manual ACK | VERIFIED | `SEND=10b`与Driver | Responder可显式向Source发送ACK。 |
| ACK Payload更新 | VERIFIED | Data寄存器可写与`IPCM_updateAckData` | Manual ACK前可替换Data；需要HIL验证传递结果。 |
| Auto ACK | VERIFIED | `MODE.AutoAcknowledge`与历史源码 | Destination释放触发Auto ACK的测试思想存在；当前无执行证据。 |
| Auto Link | VERIFIED | `MODE.AutoLink`与历史源码 | 连续Mailbox链能力存在，最大范围由起始ID和剩余Mailbox共同限制。 |
| Auto ACK Link | VERIFIED | 两个MODE位组合 | `AUTO_ACK_LINK`硬件组合存在；当前无执行证据。 |
| IRQ/Polling | VERIFIED | `MSTATUS`描述、MIS/RIS | MSTATUS bit=1表示IRQ enabled，bit=0表示disabled并使用Polling。 |
| Multi-destination | VERIFIED | DSET/DSTATUS 32-bit与SEND描述`destination core(s)` | 一个Mailbox可设置多个Destination事件位；正式Driver未暴露集合接口。 |
| Mailbox释放清配置 | DRIVER_CLAIM | Driver注释与`SOURCE=0` | Driver声称清Source释放Mailbox并清全部Mailbox寄存器；SVD未明示，必须HIL读回。 |
| 双Core功能 | SOURCE_ONLY | 历史`IPCM_9`与DualCore Driver | 存在双核测试意图，但历史配置/发送不一致且无Ready握手，不能继承PASS。 |
| DMA/FIFO | NOT_APPLICABLE | ET6801 IPCM SVD/Driver | 没有DMA或FIFO寄存器/API。 |
| CORE2CORE门铃 | OUT_OF_SCOPE | `IPCM_10`直接操作SYSC | 属于Dual-Core/CPU系统中断，不是IPCM Mailbox Feature。 |

# 第二章 Driver分析

## 2.1 当前正式Driver API

| API | 当前行为 | 可复用判断 |
|---|---|---|
| `IPCM_mailboxStructInit` | 填充默认Source=0、Destination=1、Mailbox=0、Manual ACK、无Link | 只可作为内部默认值；公共层不能依赖固定Channel。 |
| `IPCM_mailboxInit` | 配置Source、Destination、Mode；Linked时配置连续Mailbox | 基础逻辑可复用，但缺少`start + linked < mailbox_count`边界。 |
| `IPCM_mailboxDeInit` | 将Source写0；Linked时逐项写0 | 可作为释放动作候选，必须增加状态读回并验证真实清除语义。 |
| `IPCM_sendData` | 写最多28字节并触发Destination发送 | 会静默截断、无返回值、无ID/指针校验，不可直接作为公共严格接口。 |
| `IPCM_receiveData` | 从最多7个Data Word读取指定字节数 | 会静默截断且32-bit强制解引用可能处理不了非对齐Buffer。 |
| `IPCM_updateAckData` | ACK前覆盖最多28字节 | 同样存在静默截断、无返回值和非对齐风险。 |
| `IPCM_sendDataLinked` | 从起始Mailbox连续写入并触发首Mailbox | 会按剩余Mailbox静默截断，未核对实际配置链长。 |
| `IPCM_clearDestination` | 清指定Destination和IRQ Enable位 | 可承接Auto ACK触发动作；公共输入应使用逻辑Endpoint。 |
| `IPCM_getMailboxInterrupt` | 从指定Channel的RIS寻找单个Mailbox | 多bit Pending时返回无效，不能用于Formal多Pending Case。 |
| `IPCM_clearMailboxInterruptAndSendAck` | `SEND=ACK_TO_SOURCE` | 可承接Manual ACK，但参数断言误用了Channel宏。 |
| `IPCM_clearMailboxInterrupt` | `SEND=INACTIVE` | 可承接仅清中断动作，但参数断言误用了Channel宏。 |

## 2.2 Driver Gap与最小补齐

Wrap必须只调用IPCM Driver。当前正式Driver未暴露的硬件Feature，后续只允许在`et6x_ipcm.h/.c`底部测试扩展区补齐，不允许Wrap直接操作寄存器。

需要的最小测试扩展能力：

1. `capability_get`：读取CFGSTAT并返回Mailbox、Channel和Data Word数量；
2. `mailbox_configure/release/snapshot`：使用Endpoint位集合配置和读取Source、Destination、Mode、IRQ Enable；
3. `message_write/read_exact`：严格校验ID、指针、长度和链容量，使用字节打包避免非对齐访问；
4. `pending_snapshot_get`：一次返回指定Channel完整RIS/MIS位集合；
5. `destination_release`、`interrupt_clear`和`ack_send`：动作语义分开，禁止隐式组合；
6. `linked_configure/send_exact`：校验`start_mailbox + linked_count <= mailbox_count`，拒绝截断；
7. `peer_job`：在已部署Core1 Peer中提供有界接收、ACK、双向、多Pending和Linked Job；Core1启动/烧录仍由部署层负责，不由IPCM Wrap调用DualCore Driver。

返回值使用平台稳定状态和实际处理字节数，公共头文件不暴露`IPCM_Type`、ET6801 Channel宏或寄存器位图类型。

## 2.3 当前Driver风险

- `IPCM_sendData/receiveData/updateAckData/sendDataLinked`没有Mailbox ID、空指针和有效长度检查，并把超长输入静默截断；这会让错误Case假通过。
- 32-bit整字访问直接强制转换用户Buffer；非4字节对齐指针可能产生Fault或非预期访问，必须改为安全字节打包。
- Linked初始化只校验`linkedMboxNum <= 15`，未校验起始Mailbox与链长组合；非0起始点可能越界访问`MBOX[16]`之后的寄存器。
- `IPCM_getMailboxInterrupt`要求RIS恰好等于单一bit；多个Mailbox同时Pending时无法返回任何有效ID。Formal接口必须返回完整位集合。
- `IPCM_getMailboxInterrupt`使用硬编码`16`和`0xFFFFFFFF`，不应进入公共Contract。
- 两个Clear API对Mailbox ID使用`IS_IPCM_CH_ID`断言；当前数值范围相同但语义错误，未来数量变化会留下缺陷。
- Driver顶部示例写“MSET=0 enable interrupt”，与SVD及实际代码“MSET写1、MSTATUS=1表示enabled”矛盾；公共命名统一使用`IRQ_ENABLED_ENDPOINTS`避免Mask正反语义误解。
- Driver无法表达Multi-destination集合，也没有配置、Destination、Mode、IRQ Enable的硬件快照。
- `mailboxDeInit`是否清除全部Mailbox状态只有Driver注释，没有SVD直接描述；必须通过HIL验证，不能在Case中预设成功。

# 第三章 寄存器分析

## 3.1 Register Map

每个Mailbox步长为`0x40`，`mailbox_id=n`的基址为`IPCM_BASE + 0x40*n`。

| Register | Mailbox内Offset | Access | Reset | 关键语义 |
|---|---:|---|---:|---|
| `SOURCE` | `0x00` | RW | `0x00000000` | Source及ACK事件Channel位集合；Driver以写0释放Mailbox。 |
| `DSET` | `0x04` | WO | `0x00000000` | 设置Destination位。 |
| `DCLEAR` | `0x08` | WO | `0x00000000` | 清除Destination位。 |
| `DSTATUS` | `0x0C` | RO | `0x00000000` | 当前Destination状态及消息事件路由位集合。 |
| `MODE` | `0x10` | RW | `0x00000000` | bit1 Auto Link，bit0 Auto ACK。 |
| `MSET` | `0x14` | WO | `0x00000000` | 设置IRQ Enable位。 |
| `MCLEAR` | `0x18` | WO | `0x00000000` | 清除IRQ Enable位。 |
| `MSTATUS` | `0x1C` | RO | `0x00000000` | bit=1启用Mailbox中断，bit=0禁用并使用Polling。 |
| `SEND` | `0x20` | RW | `0x00000000` | `0`Inactive，`1`消息到Destination，`2`ACK到Source，`3`非法。 |
| `DR[0..6]` | `0x24..0x3C` | RW | `0x00000000` | 7个消息Data Word，共28字节。 |

全局寄存器：

| Register | Offset | Access | Reset | 关键语义 |
|---|---:|---|---:|---|
| `ISR[channel].MIS` | `0x0800 + 8*channel` | RO | `0x00000000` | 指定Channel经过IRQ Enable后的Pending Mailbox位集合。 |
| `ISR[channel].RIS` | `0x0804 + 8*channel` | RO | `0x00000000` | 指定Channel原始Pending Mailbox位集合。 |
| `CFGSTAT` | `0x0900` | RO | `0x00101007` | Mailboxes=16、Interrupts=16、DataWords=7。 |

## 3.2 Field语义与公共映射

| Hardware Field | Bit | ET6801语义 | Public Endpoint/Feature |
|---|---:|---|---|
| `SOURCE` | 31:0 | Source与ACK事件Channel位集合 | `MAILBOX.SOURCE_ENDPOINTS` / `F_002` |
| `DSET/DCLEAR/DSTATUS` | 31:0 | Destination位集合的设置、清除和状态 | `MAILBOX.DESTINATION_ENDPOINTS` / `F_002`, `F_014` |
| `MODE.AutoAcknowledge` | 0 | 0 Manual ACK，1 Auto ACK | `MAILBOX.ACK_MODE` / `F_006`~`F_008`, `F_013` |
| `MODE.AutoLink` | 1 | 0 Single，1与下一Mailbox链接 | `MAILBOX.LINK_MODE` / `F_012`, `F_013` |
| `MSTATUS`目标位 | 31:0 | 1 IRQ enabled，0 Polling | `MAILBOX.IRQ_ENABLED_ENDPOINTS` / `F_005` |
| `SEND` | 1:0 | 0 Inactive，1 Send，2 ACK，3 Invalid | 消息、ACK和Clear动作内部映射 |
| `DR[0..6]` | 31:0 | Payload Data Word | `MESSAGE/ACK.PAYLOAD` / `F_003`, `F_007` |
| `MIS/RIS` | 31:0 | 每个bit对应一个Mailbox Pending | `CHANNEL.*_PENDING_MAILBOXES` / `F_004`, `F_010` |
| `CFGSTAT.Mailboxes` | 21:16 | Mailbox数量 | `CAPABILITY.MAILBOX_COUNT` / `F_001` |
| `CFGSTAT.Interrupts` | 13:8 | Channel数量 | `CAPABILITY.CHANNEL_COUNT` / `F_001` |
| `CFGSTAT.DataWords` | 2:0 | 单Mailbox Data Word数量 | `CAPABILITY.DATA_WORD_COUNT` / `F_001` |

人工报告只允许把上述稳定硬件Endpoint增强为ET6801实际寄存器/Field名称。`IRQ.CALLBACK_COUNT`、
`*_data_match`、`*_sequence_match`、`first_mismatch_offset`和执行次数属于Service或PC Measurement，
没有对应硬件寄存器，不得在报告中标成`IPCM.MIS/RIS/DSTATUS`等硬件反馈。完整Payload、全Mailbox
矩阵和Linked成员明细只进入绑定Artifact；Excel备注只展示长度、一致性、首个错误偏移和必要终态。

## 3.3 关键硬件约束

- `SEND=3`由SVD明确标记为非法且行为不可预测，任何自动化Case都禁止写入该值。
- `MSET/MCLEAR`是写动作，实际中断Enable状态必须从`MSTATUS`读取；不要根据“Mask”名称反向解释。
- `MIS/RIS`是Mailbox位集合，不是单一Mailbox编号；多Pending Case必须保留完整32-bit事实。
- Data寄存器不保存有效字节数，Wire/Peer Job必须显式携带Payload长度；否则最后一个Data Word的无效字节无法区分。
- Linked总容量等于实际链成员数乘以单Mailbox容量；起始Mailbox非0时最大链长必须相应缩短。
- 多Destination是否在最后一个Destination释放后才产生Auto ACK，是由寄存器语义推导出的待验证行为，`IPCM_P1_007`必须给出HIL证据。
- IPCM无DMA和FIFO；不能为了复用DMA/队列Case而创造不存在的Feature。

## 3.4 当前Capability语义缺口

现有`ipcm.yaml`只生成了`ipcm0`、Base和16条IRQ，`features/limits/options/parameters`均为空。开发前至少补齐：

```yaml
features:
  manual_ack: true
  ack_payload_update: true
  auto_ack: true
  auto_link: true
  auto_ack_link: true
  irq_delivery: true
  polling: true
  multi_destination: true
  dualcore_peer: true
limits:
  mailbox_count: 16
  channel_count: 16
  data_word_count: 7
  mailbox_payload_bytes: 28
  linked_payload_bytes: 448
options:
  ack_modes: [manual, auto]
  link_modes: [single, linked]
```

具体YAML键必须通过现有Capability Schema和生成规则落地，以上仅说明必须表达的语义，不授权手工绕过生成链。

# 第四章 当前测试代码与历史覆盖分析

## 4.1 ET6801历史FPGA测试

| 历史Case | 测试思想 | 当前证据边界 | Public Case承接 |
|---|---|---|---|
| `IPCM_0` | Manual ACK返回原Payload | 同一Core使用Channel0/1自发自收；入口被注释 | `IPCM_P0_002`，升级为真实双Core |
| `IPCM_1` | Manual ACK前更新Payload | 同一Core自发自收；入口被注释 | `IPCM_P1_001` |
| `IPCM_2` | 两个Mailbox一收一发 | 同一Core两个Channel；入口被注释 | `IPCM_P1_005`，升级为双Core双向 |
| `IPCM_3` | 同一Mailbox分段发送100字节 | 固定忙等、没有deadline；入口被注释 | `IPCM_P2_003` |
| `IPCM_4` | Auto ACK由Destination Clear触发 | 同一Core；入口被注释 | `IPCM_P1_002`正向场景 |
| `IPCM_5` | Auto ACK模式只清中断不产生ACK | 同一Core；入口被注释 | `IPCM_P1_002`反向场景 |
| `IPCM_6` | Auto ACK模式下显式Manual ACK | 同一Core；与纯Auto ACK语义混合 | 不单独保留；Manual ACK与Auto ACK分别原子验证 |
| `IPCM_7` | Auto Link、16个Mailbox、445字节、Manual ACK | 注释误写32个Mailbox；入口被注释 | `IPCM_P2_001` |
| `IPCM_8` | Auto ACK Link、16个Mailbox、445字节 | 入口被注释 | `IPCM_P2_002` |
| `IPCM_9` | Core0/Core1通过两个Mailbox双向通信 | Mailbox12/13配置与发送方向不一致、无Peer Ready握手；入口被注释 | `IPCM_P1_005`，重新设计 |
| `IPCM_10` | CORE2CORE门铃中断 | 当前入口唯一启用项，但直接操作SYSC，不使用IPCM Mailbox | `REJECTED`，转Dual-Core/CPU Contract |

历史入口`IPCM_FPGATest()`将`IPCM_0`~`IPCM_9`全部注释，只执行`IPCM_10`。因此没有任何历史IPCM Mailbox Case可以认定为已执行PASS。

## 4.2 历史Case需要修正的测试方法

- Self-send只能验证Mailbox局部寄存器和同核IRQ路由，不能证明Core0到Core1的数据可见性、事件投递和ACK回程。
- 固定`SYSCNT_delay(100/1000)`和无限忙等不能建立可靠因果关系；Formal Case使用Peer Job状态和PC统一deadline。
- `IPCM_getMailboxInterrupt`不能处理多bit Pending；新Case必须直接取得完整Raw/Masked位集合。
- 历史Linked Case始终从Mailbox0开始，未暴露Driver的起始点加链长越界风险；开发接口必须先补边界校验。
- 历史Payload比较没有显式有效长度协议；Formal Peer Job必须同时记录长度和字节内容。
- `IPCM_9`不能照抄：两核必须先分别完成正向/反向Mailbox配置和Ready握手，再允许任一方向发送。

## 4.3 Source Item Trace

| Source Item | 判定 | Public Feature | Public Case | 说明 |
|---|---|---|---|---|
| CFGSTAT 16 Mailbox/16 Channel/7 Data Word | RETAINED | `F_001` | `P0_001`, `P1_004` | 数量进入Capability，Case不写死。 |
| SOURCE/DSET/DSTATUS路由 | RETAINED | `F_002`, `F_014` | `P0_001`, `P0_002`, `P1_007` | 公共层使用逻辑Endpoint集合。 |
| DR0..DR6变长Payload | RETAINED_WITH_STRONGER_ORACLE | `F_003` | `P0_002`, `P2_003` | 增加非4字节长度和严格不截断。 |
| MIS/RIS/MSTATUS | RETAINED | `F_004`, `F_005`, `F_010` | `P0_002`, `P1_003`, `P1_006` | 完整位集合、IRQ和Polling分别验证。 |
| Manual ACK原Payload | RETAINED | `F_006` | `P0_002` | 升级为真实双Core。 |
| Manual ACK更新Payload | RETAINED | `F_007` | `P1_001` | 请求与ACK使用不同Pattern。 |
| Auto ACK正反触发条件 | RETAINED | `F_008` | `P1_002` | 合并历史Case4/5，正反条件同Case闭合。 |
| 两Mailbox双向通信 | RETAINED_WITH_CORRECTION | `F_009` | `P1_005` | 修正历史Case9的配置/发送不一致和启动竞态。 |
| 多Mailbox同时Pending | NEW_FROM_HARDWARE | `F_010` | `P1_006` | SVD位集合能力，历史Driver实现无法正确识别。 |
| Mailbox释放复用 | RETAINED_WITH_STRONGER_ORACLE | `F_011` | `P1_004`, `P2_003` | 验证Driver“SOURCE=0清全部状态”的声明。 |
| Auto Link | RETAINED | `F_012` | `P2_001` | 承接历史Case7，严格记录全链成员。 |
| Auto ACK Link | RETAINED | `F_013` | `P2_002` | 承接历史Case8。 |
| Multi-destination | NEW_FROM_HARDWARE | `F_014` | `P1_007` | 来自DSET/DSTATUS位集合和SVD复数语义。 |
| 同Mailbox连续分段 | RETAINED_WITH_STRONGER_ORACLE | `F_015` | `P2_003` | 承接历史Case3，去除无限忙等。 |
| `SEND=3` | REJECTED_UNSAFE | — | — | SVD明确非法且不可预测。 |
| `IPCM_10` CORE2CORE中断 | REJECTED_OUT_OF_SCOPE | — | — | 不使用IPCM寄存器，属于系统双核门铃。 |
| DMA/FIFO | NOT_APPLICABLE | — | — | ET6801 IPCM没有该硬件能力。 |

# 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | ET6801参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| IPCM_F_001 | SUPPORTED | CFGSTAT=`16/16/7`，28字节单Mailbox | IMPLEMENTATION_GAP | `P0_001`, `P1_004` |
| IPCM_F_002 | SUPPORTED | SOURCE/DSET/DSTATUS为32-bit Endpoint位集合 | IMPLEMENTATION_GAP | `P0_001`, `P0_002`, `P1_005` |
| IPCM_F_003 | SUPPORTED | DR[7]，有效长度由协议携带 | IMPLEMENTATION_GAP | `P0_002`, `P2_003` |
| IPCM_F_004 | SUPPORTED | 16组MIS/RIS，每bit对应Mailbox | IMPLEMENTATION_GAP | `P0_002`, `P1_003` |
| IPCM_F_005 | SUPPORTED | MSTATUS=1启用IRQ，0仅Polling | IMPLEMENTATION_GAP | `P1_003` |
| IPCM_F_006 | SUPPORTED | SEND=2 Manual ACK | IMPLEMENTATION_GAP | `P0_002` |
| IPCM_F_007 | SUPPORTED | ACK前覆盖DR[0..6] | IMPLEMENTATION_GAP | `P1_001` |
| IPCM_F_008 | SUPPORTED | MODE.bit0，Destination Clear触发语义需HIL | IMPLEMENTATION_GAP | `P1_002` |
| IPCM_F_009 | SUPPORTED | ET6801 Core0/Core1，两个独立Mailbox | IMPLEMENTATION_GAP | `P1_005` |
| IPCM_F_010 | SUPPORTED | RIS/MIS完整Mailbox位集合 | IMPLEMENTATION_GAP | `P1_006` |
| IPCM_F_011 | NEEDS_VERIFICATION | Driver声称SOURCE=0释放并清全部状态 | IMPLEMENTATION_GAP | `P1_004`, `P2_003` |
| IPCM_F_012 | SUPPORTED | MODE.bit1，最多连续16个Mailbox | IMPLEMENTATION_GAP | `P2_001` |
| IPCM_F_013 | SUPPORTED | MODE.bit1+bit0 | IMPLEMENTATION_GAP | `P2_002` |
| IPCM_F_014 | SUPPORTED | DSET/DSTATUS 32-bit Multi-destination | IMPLEMENTATION_GAP | `P1_007` |
| IPCM_F_015 | SUPPORTED | Manual ACK完成后复用同一Mailbox | IMPLEMENTATION_GAP | `P2_003` |

# 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| IPCM_P0_001 | IMPLEMENTATION_GAP | 需要Capability语义、配置快照和严格释放读回Driver。 |
| IPCM_P0_002 | MAPPING_GAP | 需要Core0 Initiator、Core1 Responder和两个逻辑事件Endpoint；每个Payload长度形成独立parameter_id。 |
| IPCM_P1_001 | MAPPING_GAP | 需要Peer Manual ACK Update Job。 |
| IPCM_P1_002 | MAPPING_GAP | 需要Peer将interrupt_clear与destination_release分成两个原子动作。 |
| IPCM_P1_003 | MAPPING_GAP | 需要Peer分别执行Polling和IRQ接收并回报完整RIS/MIS。 |
| IPCM_P1_004 | MAPPING_GAP | 需要全16 Mailbox参数矩阵、释放快照和双核消息Job；每个mailbox_id形成独立parameter_id。 |
| IPCM_P1_005 | MAPPING_GAP | 需要两个方向Mailbox均Ready后再开始发送。 |
| IPCM_P1_006 | MAPPING_GAP | 需要禁止Peer提前处理，保留两个Raw Pending位后再逐项处理。 |
| IPCM_P1_007 | MAPPING_GAP | 需要Core1提供两个逻辑事件Endpoint，并补Multi-destination Driver接口。 |
| IPCM_P2_001 | MAPPING_GAP | 需要全链Manual ACK Peer Job和严格Linked边界Driver。 |
| IPCM_P2_002 | MAPPING_GAP | 需要全链Destination Release/Auto ACK Peer Job。 |
| IPCM_P2_003 | MAPPING_GAP | 需要连续分段接收与重组Peer Job。 |

## 6.1 ET6801 Execution Mapping

建议复用当前ET6801 Core1 Peer部署基础，不新建平行双核框架：

| 逻辑对象 | ET6801映射 | 状态 |
|---|---|---|
| `INITIATOR` | Core0正式自动化测试固件 | AVAILABLE |
| `RESPONDER` | 现有Core1 Peer映像扩展IPCM Job | IMPLEMENTATION_GAP |
| `INITIATOR_EVENT` | 候选Channel11 / `IPCM11_IRQn` | NEEDS_HIL_MAPPING |
| `RESPONDER_EVENT_PRIMARY` | 候选Channel10 / `IPCM10_IRQn` | NEEDS_HIL_MAPPING |
| `RESPONDER_EVENT_SECONDARY` | 从Capability选择与Primary不同的可用Channel | NEEDS_HIL_MAPPING |
| Core1部署 | FPGA ITCM与Silicon PFLASH1 Profile | AVAILABLE_FOR_EXTENSION |

Channel10/11只来自ET6801历史双核测试的候选映射，不能在公共Case中写死。开发时必须先做一个双核消息Smoke验证逻辑Endpoint到实际IRQn的映射，再开放完整Case。

## 6.2 实现顺序

1. 补齐ET6801 IPCM Capability语义，并验证CFGSTAT与YAML一致；
2. 在SDK Driver底部测试扩展区补严格边界、快照、完整Pending位集合和Multi-destination接口；
3. 实现芯片中立IPCM Wrap、Service和命令注册，Service只做命令解析与Driver调用；
4. 在现有Core1 Peer工程中增加IPCM异步Job，不新建第二套双核部署框架；
5. 实现PC IPCM Driver和12个Formal Case，Case只使用逻辑Endpoint和Capability；
6. 先执行`P0_001`和真实双核`P0_002` Smoke，再按P1、P2扩展；
7. FPGA与Silicon分别取得独立HIL证据并更新本文件测试状态。

## 6.3 当前覆盖结论

```text
Public Feature: 15
- ET6801 Hardware SUPPORTED: 14
- ET6801 Hardware NEEDS_VERIFICATION: 1
- Platform IMPLEMENTATION_GAP: 15

Formal Case: 12
- PLANNED: 12
- IMPLEMENTED: 0
- FPGA PASS/FAIL/SKIP: 0/0/0
- Silicon PASS/FAIL/SKIP: 0/0/0

External wiring required: 0
On-chip peer required: 11
R0 self-contained Case: IPCM_P0_001
```

## 6.4 剩余风险

- 当前Capability没有任何IPCM Feature/Limit语义；若不先补齐，公共Case会被迫写死ET6801数量。
- 历史双核Case没有Ready握手且Mailbox12/13配置与发送不一致，不能作为可运行模板。
- 正式Driver的静默截断、非对齐访问和Linked越界可能导致Fault或假通过，必须在Wrap开发前修复。
- Mailbox释放是否由`SOURCE=0`清除全部状态、多Destination最后释放是否触发Auto ACK，均需要最小HIL实证。
- Core1 Peer是片内配测执行实体，不是外部接线；Peer未部署属于Mapping/Implementation Gap，不能把Case删除或标成硬件不支持。
