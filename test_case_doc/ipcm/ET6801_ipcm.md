# ET6801 IPCM Chip Analysis & Adaptation Contract

> 本文件只分析 ET6801 的 IPCM 硬件事实、Driver、历史测试和公共 Contract 适配。
> 3101与6003为单核芯片，本轮不读取、不引用，也不作为IPCM Feature或Case证据。
> 本文保存ET6801硬件事实、平台适配与当前测试证据；未执行的Lane不得继承其他Lane的PASS。
> 资料复核与修订时间：2026-09-03 19:15 CST。13条正式Case已实现；FPGA双核实测13条全部PASS，共34项Execution。Silicon尚未实测。

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

本地查询使用`project-governance/ip-analysis-sources.yaml`的`roots1`和`chip_parameters.et6801`，不再仅查云盘路径。下表`<et6801-verification>`展开为`D:/lihuan/vibe_code/code/SDK/git/6801/et6801-verification`；`<BOOT_ROM>`展开为`D:/lihuan/vibe_code/code/boot_rom`。`NO_MATCH`只表示所列路径和关键字未找到对应资料，不证明所有历史资料中都不存在。

| 来源 | 路径 | 状态 | 用途与证据边界 |
|---|---|---:|---|
| ET6801 IPCM SVD | `<et6801-verification>/Tools/RegGen/svd/ipcm_cfg.svd` | FOUND | Target Direct Evidence；确认16个Mailbox、16个事件Channel、7个Data Word、4种Mode、Pending和多目标位图。 |
| ET6801 merged SVD | `test_case_doc/ET6801.svd` | FOUND | Target Direct Evidence；确认IPCM实例、Base Address和16条IRQ。 |
| ET6801 generated header | `<et6801-verification>/DFP/Drivers/CMSIS/Device/Include/et6801.h` | FOUND | Target Generated Evidence；确认`IPCM_Type`、Mailbox步长、ISR数组和CFGSTAT偏移。 |
| ET6801 IPCM Driver | `<et6801-verification>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_ipcm.*` | FOUND | Target Current Driver Evidence；确认正式API、参数、截断行为和中断位集合缺陷。 |
| ET6801 DualCore Driver | `<et6801-verification>/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_dualcore.*` | FOUND | Target Current Driver Evidence；确认Core ID读取和Core1启动能力；不把CORE2CORE门铃并入IPCM。 |
| ET6801 FPGA测试源码 | `<et6801-verification>/DFP/Test/FPGATest/ipcm_fpga_test.c` | FOUND | Target Historical Test；Case0~9为IPCM测试思想，当前入口只执行非IPCM的Case10。 |
| ET6801寄存器扫描 | `<et6801-verification>/DFP/Test/FPGATest/regscan_smoke_test.c::IPCM_Test` | FOUND | 断言CFGSTAT=`0x00101007`，由P0_001逐字段比较承接。 |
| ET6801压力测试入口 | `<et6801-verification>/DFP/Test/StressTest/Integrated_StressTest.c::IPCM_entry`调用及`DFP/Test/ChipSieveTest/ChipSieveTest_config.h`声明 | FOUND | 只找到调用与声明，不能推断具体激励、循环次数或Oracle。 |
| ET6801压力测试正文 | `<et6801-verification>`的C/H文件定向查找`IPCM_entry`定义 | NO_MATCH | 需要补充正文或原测试需求；当前覆盖结论不包含未知正文。 |
| 本地SDK需求 | `D:/lihuan/vibe_code/code/SDK/git/test_case/6801/ipcm.json`及`test_case`下IPCM文件名 | NO_MATCH | 精确路径未命中，定向检索未找到独立IPCM需求。 |
| 本地SVN需求 | `D:/lihuan/vibe_code/SVN/Software/ET6801/04 测试用例/01 回片验证/02 测试用例/ipcm_testcase.xlsx`及该测试用例目录的IPCM文件名 | NO_MATCH | 主路径和`驱动开发-测试用例/01 已评审/ipcm_testcase.xlsx`回退路径均未命中。 |
| 云盘本地需求副本 | `G:/我的云端硬盘/ET_FILE/CODE/sdk/test_case`下IPCM文件名 | NO_MATCH | 根目录存在，未找到IPCM独立需求；不能替代本地SDK/SVN查询。 |
| BootROM复位映射 | `<BOOT_ROM>/bootrom-dev-et6801/source/Drivers/ET6801/ET6x_Driver/Inc/et6x_crg.h` | FOUND | 有`CRG_PERIPH_IPCM`映射，可与本项目SVD/CMSIS的SRST1 bit25交叉核对；不是IPCM测试证据。 |
| current capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/ipcm.yaml` | FOUND | 生成器v10从完整Mailbox形状生成9项Feature、5项容量和2项模式选项，保留Base与16条IRQ。 |
| capability audit | `artifacts/runs/20260903_ipcm_capability/audit/ipcm.yaml` | FOUND | 当前SVD的语义审计；reference_data中的v8产物仅为历史，不代表当前能力。 |
| current Core1 Peer | `firmware/chips/et6801/core1_peer`与`firmware/build/et6801/core1_peer` | FOUND | IPCM独立Core1 Service与共享控制通道已实现，ITCM Peer已完成本轮FPGA双核验证。 |
| current platform IPCM code | `firmware/{wrap,services}`、`firmware/chips/et6801/core1_peer`与`pc/et_test_platform/{drivers,test_cases}/ipcm` | FOUND | 本核Wrap/Service、Core1原子执行器、PC Driver与13条正式Case已实现；证据见当前芯片测试状态。 |

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
| Auto ACK | VERIFIED | `MODE.AutoAcknowledge`、历史源码与P1_002 HIL | MCLEAR只清消息不触发ACK；DCLEAR释放Destination后触发ACK。 |
| Auto Link | VERIFIED | `MODE.AutoLink`与历史源码 | 连续Mailbox链能力存在，最大范围由起始ID和剩余Mailbox共同限制。 |
| Auto ACK Link | VERIFIED | 两个MODE位组合与P2_002 HIL | 每个链成员接收后DCLEAR推进，Source只收到链尾ACK。 |
| IRQ/Polling | VERIFIED | `MSTATUS`描述、MIS/RIS | MSTATUS bit=1表示IRQ enabled，bit=0表示disabled并使用Polling。 |
| Multi-destination | VERIFIED | DSET/DSTATUS 32-bit与SEND描述`destination core(s)` | 一个Mailbox可设置多个Destination事件位；正式Driver未暴露集合接口。 |
| AUTO下显式ACK | VERIFIED | SVD `SEND=10b`、历史`IPCM_6`与P1_008 HIL | 保持MODE.bit0=1，直接SEND=2，不执行DCLEAR，Source收到一次ACK。 |
| Linked链尾ACK预期 | VERIFIED | 历史`IPCM_7/8`与P2_001/P2_002 HIL | 16次Destination接收、1次Source链尾ACK；Source原始Pending对应Mailbox15。 |
| Mailbox释放清配置 | UNKNOWN | Driver注释与`SOURCE=0` | Driver声称清Source会清全部Mailbox寄存器，SVD未明示；P0_001开发前须用最小读写/释放读回确认，不以CRG复位伪装成功。 |
| 多目标AUTO聚合ACK | UNKNOWN | DSET位集合与MODE.bit0只能分别证明能力存在 | 未说明首次或最后一次DCLEAR触发ACK；无历史Case，不能预设最后释放才ACK。P1_007改为MANUAL路由验证。 |
| 双Core功能 | INFERRED | 历史`IPCM_9`与DualCore Driver | 存在双核测试意图，但历史配置/发送不一致且无Ready握手；必须验证真实Core0/Core1，不能继承PASS。 |
| IPCM全实例复位位 | VERIFIED | 本项目CMSIS `CRG_SRST1_CRG_SRST_N_IPCM_Pos`、merged SVD与本轮Case基线 | `CRG.SRST1[25]`低有效复位；`CRG_PERIPH_IPCM`已补齐，每条Case配置前通过CRG Driver复位。 |
| DMA/FIFO不存在 | VERIFIED | ET6801 IPCM SVD/Driver定向核对 | 未描述DMA/FIFO寄存器或API；不为此IP规划DMA/FIFO Case。 |
| CORE2CORE门铃归属 | VERIFIED | `IPCM_10`直接操作SYSC | 属于Dual-Core/CPU系统中断，不是IPCM Mailbox Feature。 |

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
| `IPCM_clearMailboxInterruptAndSendAck` | `SEND=ACK_TO_SOURCE`，未限制Mode | 承接MANUAL或AUTO下的显式ACK，不得在Wrap中误拒绝AUTO；参数断言误用了Channel宏。 |
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
7. 事件采样复用上述快照与读数据接口：在ACK/Clear/Release前采集，不另增测试判定Driver。

Chip Driver返回值和类型遵循SDK；Wrap转换为平台稳定状态和实际处理字节数，Wrap公共头文件不暴露`IPCM_Type`、ET6801 Channel宏或寄存器位图类型。两者不能混写成同一接口规范。

Core1使用同一份IPCM Service及独立IRQ Manager，只执行PC指定的原子动作，不实现Case流程。IPCM Test Driver Extension提供共享SRAM控制通道的Submit/Result/Cancel及Peer端Take/Complete；它不实现消息接收、ACK顺序或Expected比较。IPCM Service只调用本IP Wrap，Core1部署和启动由既有部署层负责，禁止IPCM Wrap调用DualCore Driver。

IPCM专用构建目标为`ET6801_CORE1_ITCM_IPCM_PEER`及`ET6801_CORE1_PFLASH1_IPCM_PEER`，原SPINLOCK目标保持不变。控制通道位于`AXI_SRAM1_BASE=0x20440000`，前16字节沿用部署Ready契约，另以IPCM标签排除错误Peer镜像。当前要求两核D-cache关闭；DMB/DSB只负责发布顺序，不能代替Cache一致性。硬件Core1身份由`DUALCORE_getCurrentCoreId()`采集并经Execution Mapping核对，不能由PC Case写死。

正式FPGA Pipeline为`tools/profiles/pipeline/et6801_fpga_ipcm.yaml`，复用现有双核部署脚本，以IPCM Peer Manifest选择目标。Core0从PFLASH运行正式ET-Frame固件，Core1运行ITCM IPCM Peer；先通过P0双核Smoke，再执行全量13条Case。原SPINLOCK目标与部署Profile不变。部署、门禁和HIL证据统一见第六章与当前芯片测试状态。

Capability生成器开发路由已按人工授权补齐（`2b7e7a1`）。v10通用Mailbox推导只按容量配置、完整寄存器阵列、访问属性和SEND编码匹配，不按芯片名、外设名或地址分支。生成质量检查无错误；正式IPCM YAML逐字比对生成结果，13条Case通过Capability查询获取能力与容量。

每个Case由PC调用CRG Driver进行IPCM全实例复位；`SRST1[25]`及`GTEN1[25]`选择器已在独立CRG变更`3e317bf`补齐。此操作不能藏入IPCM Driver或Wrap，不能拿`IPCM_mailboxDeInit`代替IP复位。

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
| `MODE.AutoAcknowledge` | 0 | 0 Manual ACK，1 Auto ACK；显式SEND=2不要求清此位 | `MAILBOX.ACK_MODE` / `F_006`~`F_008`, `F_013`, `F_016` |
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
- `SEND=2`会结束Destination消息阶段，`SEND=0`会清Pending，`DCLEAR`也会改变接收路由；必须在这些动作之前采样RIS/MIS及Data。ISR快照与清除后的即时读回使用不同阶段标识，不能用后者否认前者发生过。
- Data寄存器不保存有效字节数，Wire/Peer Job必须显式携带Payload长度；否则最后一个Data Word的无效字节无法区分。
- Linked总容量等于实际链成员数乘以单Mailbox容量；起始Mailbox非0时最大链长必须相应缩短。
- 多Destination的AUTO聚合时序没有直接证据。`IPCM_P1_007`使用MANUAL+POLLING，两目标均读取后分别DCLEAR，最后SEND=2；不使用未经证实的“最后DCLEAR才ACK”作为PASS条件。该组合语义须补目标设计说明后再决定扩展，当前不记为已覆盖或SKIP。
- 历史Linked Case中`linkedMboxNum=15`是首Mailbox之外的15项，实际N=16；公共`linked_count`必须表示总成员数N。尾项MODE.AutoLink清0，Source ACK应落在尾项；Driver负责N到SDK参数N-1的转换。
- 每轮配置前的全实例复位由CRG Driver对`CRG.SRST1[25]`执行低有效复位并释放；单Mailbox的SOURCE=0仅验证释放语义，不具有全IP或跨Core软件状态复位的含义。
- IPCM无DMA和FIFO；不能为了复用DMA/队列Case而创造不存在的Feature。

## 3.4 当前Capability与Execution Mapping

当前`ipcm.yaml`保留实例、Base和16条IRQ，并已生成以下语义。此处为便于阅读的摘要，正式文件采用v2的按实例值结构：

```yaml
features:
  manual_ack: true
  ack_payload_update: true
  auto_ack: true
  explicit_ack_in_auto: true
  auto_link: true
  auto_ack_link: true
  irq_delivery: true
  polling: true
  multi_destination: true
limits:
  mailbox_count: 16
  channel_count: 16
  data_word_count: 7
  payload_bytes_per_mailbox: 28
  linked_payload_max_bytes: 448
options:
  ack_modes: [manual, auto]
  link_modes: [single, linked]
```

容量以CFGSTAT有效Reset字段解码，并与实际Mailbox、Channel和DATA数组交叉核对；字段缺失、数量矛盾、SEND编码不明时不提升为能力。控制Feature绑定可写配置字段，容量绑定完整只读CFGSTAT，不能把RIS/MIS默认0误判为不支持IRQ。

`profiles/chip_execution_mappings/et6801/ipcm_routes.py`保存本核Endpoint11、Peer Endpoint10、第二目标Endpoint9和Core1硬件身份2。依据为ET6801历史IPCM_9与DualCore Driver；本轮P0_002验证11/10的实际IRQ投递，P1_007验证10/9的多目标Polling接收，未宣称端点9的IRQ已验证。Peer是否部署/Ready是Runtime资格，不属于IPCM硅能力，不在YAML伪造`dualcore_peer: true`。

# 第四章 当前测试代码与历史覆盖分析

## 4.1 ET6801历史FPGA测试

| 历史Case | 测试思想 | 当前证据边界 | Public Case承接 |
|---|---|---|---|
| `IPCM_0` | Manual ACK返回原Payload | 同一Core使用Channel0/1自发自收；入口被注释 | `IPCM_P0_002`，升级为真实双Core |
| `IPCM_1` | Manual ACK前更新Payload | 同一Core自发自收；入口被注释 | `IPCM_P1_001` |
| `IPCM_2` | 两个Mailbox一收一发 | 同一Core两个Channel；入口被注释 | `IPCM_P1_005`，升级为双Core双向 |
| `IPCM_3` | 同一Mailbox分段发送100字节 | 接收端每次按28字节追加，100字节Buffer的尾段可能越界；入口被注释 | `IPCM_P2_003`按实际段长重组，不照抄错误尾段 |
| `IPCM_4` | Auto ACK由Destination Clear触发 | 同一Core；入口被注释 | `IPCM_P1_002`正向场景 |
| `IPCM_5` | Auto ACK模式只清中断不产生ACK | 同一Core；入口被注释 | `IPCM_P1_002`反向场景 |
| `IPCM_6` | Auto ACK模式下显式ACK | MODE=AUTO_ACK，接收端直接SEND=2；这不是Case0或4的重复点，不能合并丢失 | `IPCM_P1_008` |
| `IPCM_7` | Auto Link、16个Mailbox、445字节、Manual ACK | 注释误写32；Source ISR只预期Mailbox15，接收端每项ACK推进链 | `IPCM_P2_001`，N次Destination+1次Source链尾ACK |
| `IPCM_8` | Auto ACK Link、16个Mailbox、445字节 | Source ISR只预期Mailbox15；接收端每项DCLEAR推进链 | `IPCM_P2_002`，N次Destination+1次Source链尾ACK |
| `IPCM_9` | Core0/Core1通过两个Mailbox双向通信 | Mailbox12/13配置与发送方向不一致、无Peer Ready握手；入口被注释 | `IPCM_P1_005`，重新设计 |
| `IPCM_10` | CORE2CORE门铃中断 | 当前入口唯一启用项，但直接操作SYSC，不使用IPCM Mailbox | `NOT_APPLICABLE`于本IP，归Dual-Core/CPU Contract |
| `regscan_smoke_test.c::IPCM_Test` | CFGSTAT整体值读回 | 检查`0x00101007`，没有消息/ACK测试 | `IPCM_P0_001`逐字段核对16/16/7 |
| `Integrated_StressTest.c::IPCM_entry` | IPCM压力子项入口 | 只见调用和头文件声明，未找到函数正文 | `UNKNOWN`，保留资料缺口，不编造压力Feature或Case |

历史入口`IPCM_FPGATest()`将`IPCM_0`~`IPCM_9`全部注释，只执行`IPCM_10`。因此没有任何历史IPCM Mailbox Case可以认定为已执行PASS。

## 4.2 历史Case需要修正的测试方法

- Self-send只能验证Mailbox局部寄存器和同核IRQ路由，不能证明Core0到Core1的数据可见性、事件投递和ACK回程。
- 固定`SYSCNT_delay(100/1000)`和无限忙等不能建立可靠因果关系；Formal Case使用Peer Job状态和PC统一deadline。
- `IPCM_getMailboxInterrupt`不能处理多bit Pending；新Case必须直接取得完整Raw/Masked位集合。
- 历史Linked Case始终从Mailbox0开始，未暴露Driver的起始点加链长越界风险；开发接口必须先补边界校验。
- 历史Payload比较没有显式有效长度协议；Formal Peer Job必须同时记录长度和字节内容。
- `IPCM_3`固定28字节读写尾段、`IPCM_7/8`读取最后Mailbox整容量，不能作为新Case的有效长度规则。当前长数据选择可复现Pattern，末项只保留真实字节；与历史相同的是分段/链路Feature，不是其Buffer越界。
- `IPCM_6`必须保持AUTO配置再显式ACK，不能拆成两个互不相关的MANUAL和AUTO Case声称覆盖。
- `IPCM_7/8`必须区分接收端每次ACK动作和Source只收到最终ACK；Source ISR读取的历史Mailbox15不是“所有Mailbox都向Source发ACK”的证据。
- `IPCM_9`不能照抄：两核必须先分别完成正向/反向Mailbox配置和Ready握手，再允许任一方向发送。

## 4.3 Source Item Trace

| Source Item | 判定 | Public Feature | Public Case | 说明 |
|---|---|---|---|---|
| CFGSTAT及`regscan_smoke_test.c::IPCM_Test` | MERGED | `F_001` | `P0_001`, `P1_004` | 整值0x00101007转成16/16/7逐字段核对，数量进入Capability。 |
| SOURCE/DSET/DSTATUS路由 | SPLIT | `F_002`, `F_014` | `P0_001`, `P0_002`, `P1_007` | 单目标路由与多目标释放分开，公共输入为逻辑Endpoint。 |
| DR0..DR6变长Payload | MAPPED | `F_003` | `P0_002`, `P2_003` | 非4字节长度和严格不截断。 |
| MIS/RIS/MSTATUS | SPLIT | `F_004`, `F_005`, `F_010` | `P0_002`, `P1_003`, `P1_006` | 完整位集合、IRQ、Polling分别验证，清除前采样。 |
| `IPCM_0` Manual ACK原Payload | MAPPED | `F_006` | `P0_002` | 真实双Core，替换同核自发自收。 |
| `IPCM_1` Manual ACK更新Payload | MAPPED | `F_007` | `P1_001` | 请求A和ACK B独立核对。 |
| `IPCM_4/5` Auto ACK正反触发 | MERGED | `F_008` | `P1_002` | 同Case两个独立参数：clear_only/release。 |
| `IPCM_2/9` 两Mailbox双向 | MERGED | `F_009` | `P1_005` | 保留双向思想，修正Case9配置/发送不一致和Ready竞态。 |
| 多Mailbox同时Pending | MAPPED | `F_010` | `P1_006` | SVD位集合能力；IRQ关闭时Raw含两位、Masked为0。 |
| Driver Mailbox释放声明 | MAPPED | `F_011` | `P0_001`, `P1_004` | 清Source后读回，用实测确认未知语义；连续分段Case不等于释放测试。 |
| `IPCM_7` Auto Link | MAPPED | `F_012` | `P2_001` | 保留全链成员和唯一Source链尾ACK的历史预期。 |
| `IPCM_8` Auto ACK Link | MAPPED | `F_013` | `P2_002` | 逐Destination释放推进，Source只接收链尾ACK。 |
| Multi-destination位集合 | MAPPED | `F_014` | `P1_007` | MANUAL逐目标释放，不叠加未知AUTO聚合规则。 |
| `IPCM_3` 同Mailbox连续分段 | MAPPED | `F_015` | `P2_003` | 保留4段思想，移除无界等待与尾段越界。 |
| `IPCM_6` AUTO下显式ACK | MAPPED | `F_016` | `P1_008` | 不改变MODE.bit0，不执行DCLEAR，直接SEND=2。 |
| `IPCM_entry`调用/声明 | UNKNOWN | — | — | 需获取压力测试正文或需求后再判断增量覆盖；不能凭入口名生成Case。 |
| 多目标AUTO聚合ACK | UNKNOWN | — | — | 需目标设计说明确认触发条件，不计入已覆盖。 |
| `SEND=3` | REJECTED | — | — | SVD明确非法且不可预测，禁止刺激。 |
| `IPCM_10` CORE2CORE中断 | NOT_APPLICABLE | — | — | 不使用IPCM寄存器，属于系统双核门铃。 |
| DMA/FIFO | NOT_APPLICABLE | — | — | ET6801 IPCM没有该硬件能力。 |

# 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | ET6801参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| IPCM_F_001 | SUPPORTED | CFGSTAT=`16/16/7`，28字节单Mailbox | ADAPTED | `P0_001`, `P1_004` |
| IPCM_F_002 | SUPPORTED | SOURCE/DSET/DSTATUS为32-bit Endpoint位集合 | ADAPTED | `P0_001`, `P0_002`, `P1_004`, `P1_005` |
| IPCM_F_003 | SUPPORTED | DR[7]，有效长度由协议携带 | ADAPTED | `P0_002`, `P2_003` |
| IPCM_F_004 | SUPPORTED | 16组MIS/RIS，每bit对应Mailbox | ADAPTED | `P0_002`, `P1_003` |
| IPCM_F_005 | SUPPORTED | MSTATUS=1启用IRQ，0仅Polling | ADAPTED | `P1_003` |
| IPCM_F_006 | SUPPORTED | SEND=2 Manual ACK | ADAPTED | `P0_002` |
| IPCM_F_007 | SUPPORTED | ACK前覆盖DR[0..6] | ADAPTED | `P1_001` |
| IPCM_F_008 | SUPPORTED | MODE.bit0，MCLEAR不ACK、DCLEAR触发ACK | ADAPTED | `P1_002` |
| IPCM_F_009 | SUPPORTED | ET6801 Core0/Core1，两个独立Mailbox | ADAPTED | `P1_005` |
| IPCM_F_010 | SUPPORTED | RIS/MIS完整Mailbox位集合 | ADAPTED | `P1_006` |
| IPCM_F_011 | SUPPORTED | SOURCE=0后配置、Destination、Raw/Masked清零；16个Mailbox均完成两轮复用读回 | ADAPTED | `P0_001`, `P1_004` |
| IPCM_F_012 | SUPPORTED | MODE.bit1，最多连续16个Mailbox | ADAPTED | `P2_001` |
| IPCM_F_013 | SUPPORTED | MODE.bit1+bit0 | ADAPTED | `P2_002` |
| IPCM_F_014 | SUPPORTED | DSET/DSTATUS 32-bit Multi-destination，MANUAL+Polling | ADAPTED | `P1_007` |
| IPCM_F_015 | SUPPORTED | Manual ACK完成后复用同一Mailbox | ADAPTED | `P2_003` |
| IPCM_F_016 | SUPPORTED | MODE.bit0=1时直接SEND=2，无需先DCLEAR | ADAPTED | `P1_008` |

# 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| IPCM_P0_001 | ADAPTED | CRG复位、CFGSTAT容量查询和SOURCE=0释放读回均已实现；配置前检查Capability。 |
| IPCM_P0_002 | ADAPTED | Core0/1及事件Endpoint由Execution Mapping提供；1/3/4/27/28字节分别执行，双端IRQ快照和Payload参与断言。 |
| IPCM_P1_001 | ADAPTED | PC逐步控制Peer接收、更新Payload和Manual ACK；Source检查更新后的数据。 |
| IPCM_P1_002 | ADAPTED | 两独立参数clear_only/release；动作前保存Peer快照，Source用100 ms无ACK窗口或ACK前锁存值。 |
| IPCM_P1_003 | ADAPTED | 两独立参数polling/irq，清除前保存完整RIS/MIS；两模式均只清消息、不发ACK。 |
| IPCM_P1_004 | ADAPTED | 从Capability生成16个Mailbox参数；每项独立执行两轮传输、释放及空闲快照核对。 |
| IPCM_P1_005 | ADAPTED | 双向Capture均Ready后发送；从实际Pending解码观测Mailbox ID，核对方向和数据。 |
| IPCM_P1_006 | ADAPTED | PC先保留两个Raw Pending位，再逐项命令Peer处理，不让Peer提前消费。 |
| IPCM_P1_007 | ADAPTED | Core1的Endpoint10/9以MANUAL+POLLING接收，分别DCLEAR后最后SEND=2；不需要第三个Core。 |
| IPCM_P1_008 | ADAPTED | AUTO下显式ACK，ACK前保存MODE、DSTATUS和RIS/MIS；不执行DCLEAR。 |
| IPCM_P2_001 | ADAPTED | 严格Linked边界；记录16次Destination消息和一次Source链尾ACK，按有效字节重组Payload。 |
| IPCM_P2_002 | ADAPTED | 逐成员DCLEAR；与P2_001相同，仅链尾产生Source ACK，不按16次Source IRQ断言。 |
| IPCM_P2_003 | ADAPTED | 87字节分28/28/28/3共4段，Peer回报有效片段，PC重组；段间不复位IP，验证同Mailbox复用。 |

## 6.1 ET6801 Execution Mapping

复用现有ET6801 Core1 Peer工程和部署脚本；以下映射均隔离在芯片配置中：

| 逻辑对象 | ET6801映射 | 状态 |
|---|---|---|
| `INITIATOR` | Core0正式自动化测试固件 | AVAILABLE |
| `RESPONDER` | Core1 IPCM原子命令执行器，硬件身份2 | FPGA_HIL_VERIFIED |
| `INITIATOR_EVENT` | Channel11 / `IPCM11_IRQn` | FPGA_IRQ_VERIFIED |
| `RESPONDER_EVENT_PRIMARY` | Channel10 / `IPCM10_IRQn` | FPGA_IRQ_VERIFIED |
| `RESPONDER_EVENT_SECONDARY` | Channel9，由同一Core1轮询读取 | FPGA_POLLING_VERIFIED |
| Core1部署 | FPGA ITCM IPCM Peer | FPGA_HIL_VERIFIED；Silicon PFLASH1尚未实测 |

Channel10/11来自ET6801历史双核测试，已由本轮P0 Smoke确认；Channel9由多目标Polling Case确认。编号没有写入公共Case或公共Driver，Core1未Ready、身份不匹配或能力缺失时不允许开始刺激。

复位是共享IP级动作：PC先等待Peer Cancel确认，再关闭本核Capture并复位本核Service；调用CRG复位IPCM后复位Peer Service及Resource Pool。两端静止后才复位共享IP，不让Core1仍在读写Mailbox时复位。Peer传输仅扩展本IP命令和现有共享控制区，不修改公共双核协议。

## 6.2 实现边界与验证证据

本轮代码落点与边界：

- SDK仅在`et6x_ipcm.h/.c`底部`TEST DRIVER EXTENSION`区域增加接口，不改变原API。`IPCM_testConfigureMailboxes`采用总成员数，先验证完整范围和空闲SEND，再写SOURCE/Destination/Mode/IRQ；链尾清AUTO_LINK。`IPCM_testWritePayloadExact/ReadPayloadExact`按字节装拆32位数据，非对齐地址安全，拒绝越界和截断。`IPCM_testGetPendingSnapshot`保留RIS/MIS完整位集合。
- `IPCM_testReleaseMailboxes`只执行原SDK的SOURCE=0；P0_001及P1_004的16个Mailbox两轮读回确认配置、Destination及Raw/Masked清零，软件不补写零伪造释放效果。SEND动作只允许0/1/2；显式ACK不改MODE、不提前DCLEAR。
- `et_chip_wrap_config.h`的IPCM分区保存实例、逻辑Endpoint到SDK Channel及CMSIS IRQn的映射，以及ACK/Link枚举映射。当前Endpoint0~15映射Channel0~15只是本芯片表，不写入公共Service/Case。
- CRG复位类别IPCM=8，实例0映射`CRG_PERIPH_IPCM`，选择值来自`CRG_GTEN1_CRG_CLK_GTEN_IPCM_Pos`，与SVD的SRST1[25]一致；复位与门控均复用现有CRG Driver。
- `et_ipcm_wrap.h/.c`只调用IPCM Driver；`et_ipcm_service.h/.c`新增0x0109服务，Wire见公共文档0.6。两种Board各注册逻辑实例0、IRQ优先级3；Application只增静态清单行，通用注册器、main和Framework不改。
- 当前Capture在清除前锁存RIS/MIS/Data，随后仅MCLEAR暂停投递；不会自动执行ACK或Destination释放。4 Slot/128字节是Service软件预算，不写入Chip Config能力事实。
- `project.yaml`纳入IPCM SDK、Wrap、Service。Core1以独立IPCM构建目标复用已有Peer工程；既有SPINLOCK实现及默认部署Profile不改。

2026-09-03本轮验证：

- 软件门禁：`tools/validate_pc.py`的918项测试通过，包括Native Driver/Wrap/Service合同、Peer票据及Deadline、Case报告绑定和Windows PowerShell语法检查。
- 正式部署：`artifacts/runs/20260903_190012_722671_local_et6801_fpga_atp_testing/`。BootROM、Core0固件和Core1 IPCM ITCM Peer完成构建；XC7VX980T重新烧录bitfile，BootROM到达main，Core0 PFLASH完成Erase/Program/Verify，再部署并核对Core1身份。Core0从Flash执行，不以RAM临时诊断替代正式测试。
- 部署脚本曾因Windows PowerShell 5.1不支持`4u/0u`数字后缀在编译阶段退出，未进入硬件阶段；修正后上述整条部署成功。失败日志保留在`artifacts/runs/20260903_185811_535172_local_et6801_fpga_atp_testing/`。BootROM旧的容量统计后处理打印编码错误，但编译0 Error/0 Warning且镜像已实际到main；本轮未修改BootROM源码。
- P0 Smoke：`artifacts/runs/20260903_190832_718847_ipcm_formal_cases/tests/ipcm/`，2条逻辑Case、6项参数化执行通过；通过后才执行完整IPCM。
- 全量IPCM：通过当前`run_config.yaml`解析的环境调用现有`run_ip_tests`入口，仅选择`ipcm`，没有修改其他IP注册项；13条逻辑Case、34项执行通过，证据见下方唯一本芯片状态区。
- 报告逐行审核：13个稳定Case ID均为PASS，参数化合并后备注保留实际硬件值；不存在空白测试结果、缺少Observation或JSON原样堆叠。

本轮HIL前机器映射、Runtime资格检查和全部Case代码已实现，但本文仍留有开发期Gap文字；按R110以直接证据确认映射闭合并同步为ADAPTED，未改变Case Oracle或通过条件。最终HIL的源码身份为`7d0d4a408cdc92f6837d4626b399619d4459ecfe`且工作树干净；此前部署manifest为dirty构建记录，不把该部署伪称为Exact-SHA构建。部署镜像校验以对应manifest和烧录Verify日志为准。

## 6.3 当前覆盖结论

```text
Public Feature: 16
- ET6801 Hardware SUPPORTED: 16
- Platform ADAPTED: 16

Formal Case: 13 (P0=2, P1=8, P2=3, P3=0)
- SPEC / REGISTERED / IMPLEMENTED: 13 / 13 / 13
- FPGA PASS/FAIL/SKIP: 13/0/0 (Executions: 34 PASS)
- Silicon NOT_EXECUTED: 13

External wiring required: 0
On-chip peer required: 12
R0 self-contained Case: IPCM_P0_001
```

已找到正文的`IPCM_0~9`共10项历史测试思想全部映射至当前SPEC，另包含寄存器扫描，当前13条Case均已在FPGA执行。覆盖边界仍以公共Feature和Oracle为准；`IPCM_entry`压力正文未知、多目标AUTO聚合时序未定义，不能因此宣称所有未知历史需求或未规划组合已覆盖。

## 6.4 剩余风险

- Silicon尚未执行，不能继承FPGA PASS；本轮没有验证Core1 PFLASH1启动。
- 当前两核D-cache关闭；启用Cache后的共享控制区一致性不在本次验证范围。
- 多Destination AUTO聚合触发须先取得目标设计定义，不应靠试出的现象反向制定Oracle；当前只覆盖多目标MANUAL+Polling。
- 压力入口正文未找到，不能将13条SPEC宣称为所有历史需求的完整覆盖。补到正文后按有效Feature做增量映射，禁止凭函数名扩写复杂压力Case。
- Channel9只验证Polling；不能从此结果推断其IRQ投递已验证。Peer缺失时属于运行映射缺口，不是外部接线不支持。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-09-03 19:15 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-09-03 19:11 CST` | `7d0d4a408cdc92f6837d4626b399619d4459ecfe` | `false` | `artifacts/runs/20260903_191100_603939_ipcm_formal_cases/tests/ipcm/` |

Firmware Build ID：`et6801-silicon-common-v0.1`；Registry Hash：`7b3f1920`；串口：`COM12@115200`。Build ID中的silicon是现有Flash构建目标名称，实际Lane为XC7VX980T FPGA，不代表实物硅后测试。

本次Session的Spec SHA256：`e4ff9277017d47e772049687e9fe6ced470811e4cbb91c582b0c24f03ce9c3ef`。本轮后续只回写文档适配状态与结果，没有更改已测试Case代码、SPEC方法或报告模板。

Excel：`artifacts/reports/20260903_191135_589408_ET6801_IPCM测试报告.xlsx`。

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 13 | 13 | 13 | 0 | 0 | 0 | 34 |

执行明细：P0的2条Case共6项Execution，P1的8条Case共25项，P2的3条Case共3项。参数化增量来自P0_002的5种长度、P1_002的Clear/Release、P1_003的Polling/IRQ，以及P1_004的16个Mailbox；其余每条Case各1项Execution。逐Case方法见第六章，逐行结果与硬件备注见上述Excel及Canonical Result。

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |
<!-- ET_CHIP_TEST_STATUS_END -->
