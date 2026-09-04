# ET6801 CAN / CAN FD 分析与测试适配

更新时间：2026-09-05 00:25 CST

**状态：CAN开发进行中，尚未完成全部Case设计审核及实现。** 已完成盒子工具、接线配置、Capability身份及29条基础/收发/过滤命令；已注册P0_002、P1_001，尚未操作硬件。已定位39项能力/行为（37项准入Feature、2项待定）、42项测试目标；2项SPEC、37项PLAN、3项DESIGN_GAP。仪器按刺激/观测职责分别规划。CAN盒子已连接是用户确认的环境事实，不是CAN Case PASS；未实现代码或未确认硬件语义不计为SKIP。

## 第一章 IP分析

### 1.1 工作原理与应用

ET6801的CAN采用M_TTCAN类寄存器体系：CPU配置Filter和Message RAM，TX Handler从RAM取发送元素，协议引擎执行仲裁、帧编码、位同步、ACK与错误处理；RX Handler按Filter写FIFO或专用Buffer。发送事件进入独立TX Event FIFO。DMU提供虚拟数据窗口，DMA可以搬运头部、payload及可选TSU时间戳，避免CPU逐字处理。

Classic CAN适合小型控制消息；CAN FD提供更长payload及可变数据段速率。工业控制、车载网络是应用背景，不新增外部存储器或上层应用协议测试替代CAN Feature。基本内部回环可无接线测试，但不能证明PAD、收发器、实际BRS或总线错误行为。

### 1.2 实例及中断Handler

| 实例 | CAN基址（SVD） | INT0 | INT1 | DMU | ECC |
|---|---|---|---|---|---|
| CAN0 | 0x4051C000 | CAN0_INT0_IRQn=39 | CAN0_INT1_IRQn=40 | CAN0_DMU_IRQn=41 | 共享CAN_ECC_IRQn=48 |
| CAN1 | 0x40524000 | CAN1_INT0_IRQn=42 | CAN1_INT1_IRQn=43 | CAN1_DMU_IRQn=44 | 同一共享向量 |
| CAN2 | 0x4052C000 | CAN2_INT0_IRQn=45 | CAN2_INT1_IRQn=46 | CAN2_DMU_IRQn=47 | 同一共享向量 |

共3个控制器实例、9个实例专属中断向量和1个共享ECC向量，合计10个物理Handler入口。不能套用6003/3101的2实例数量或把共享ECC计算三次。Service实例仍按逻辑instance_id绑定，IRQ Wrap只做通用NVIC/向量配置；ECC回调必须读取来源并区分实例。

### 1.3 本轮资料定位与覆盖状态

所有本地资源从`project-governance/ip-analysis-sources.yaml`的roots1/intent_routing解析。锚点SDK=`D:/lihuan/vibe_code/code/SDK/git`，SVN=`D:/lihuan/vibe_code/SVN/Software`。下面相对路径均相对于SDK，不指向已经停用的旧ATP工作目录。

| 根/类别 | 本轮状态 | 命中路径与使用方式 |
|---|---|---|
| ET6801整片/独立SVD | FOUND | `6801/et6801-verification/Tools/RegGen/ET6801.svd`、`svd/mttcan_cfg.svd`、`svd/mttcan_misc.svd`；硬件位图主要依据 |
| ET6801驱动 | FOUND | `6801/et6801-verification/DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_can.*`；并核对本仓库`firmware/chips/et6801/sdk/ET6x_Driver/`实际版本 |
| ET6801验证根 | FOUND | `6801/et6801-verification/DFP/Test/UnitTest/test_can.c`、`test_canfd.c`、`FunctionalTest/can_ft.c`、`FPGATest/can_fpga_test.c`、`SmokeTest/regscan_smoke_test.c`的CAN片段 |
| ET6801 SDK Example | FOUND | `6801/et6801-verification/Doc/examples/CAN/CAN_init_TxRx/Source/main.c`、`CAN_init_transmit_priority_watermark/Source/main.c` |
| ET6003验证/测试根 | FOUND | `6003/et6003-verification/DFP/Test/UnitTest/test_can.c`、`test_canfd.c`、`FPGATest/CAN/can.c`、`FPGATest/FDCAN/fdcan.c`；参照行为，不移植地址 |
| ET6003独立SDK测试根 | FOUND | `6003/6003_sdk/et6003-sdk/DFP/Test/FunctionalTest/can_ft.c`、`SmokeTest/can_smoke_test.c`、`UnitTest/test_can.c`、`test_canfd.c` |
| ET3101验证/测试根 | FOUND | `3101/et3101-verification/DFP/Test/UnitTest/test_can.c`、`test_canfd.c`、`FPGATest/CAN/can.c`、`FPGATest/FDCAN/fdcan0.c` |
| ET3101独立SDK测试根 | FOUND | `3101/et3101-sdk/DFP/Test/FunctionalTest/can_ft.c`、`SmokeTest/can_smoke_test.c`、`UnitTest/test_can.c`、`test_canfd.c`；FT8/FT9补充80MHz/AUX |
| 结构化需求 | FOUND | `test_case/6003/can.json`：19个测试点行、8条Case记录；`test_case/3101/can.json`：19行、10条Case记录。两份都只有12个非空TP ID，续行不可漏 |
| ET6801结构化CAN需求 | NO_MATCH | 本轮在`test_case`按CAN名称定位只命中6003和3101；不把其他芯片需求当ET6801硬件事实 |
| ET6801 SVN内CAN命名资料 | NO_MATCH | ET资料扫描限定`SVN/ET6801`、文件名`*can*`，未命中；只代表该范围，不代表全库无CAN资料 |
| Bosch通用IP资料 | FOUND | M_TTCAN 3.3.0原厂手册、原厂M_CAN AN004 DMU handling应用说明与配套C代码；只补机制/原厂参考测试，不冒充ET6801历史测试，目标字段仍与ET6801 SVD逐项核对 |

补充参考：[Bosch DMU应用包](https://www.bosch-semiconductors.com/media/ip_modules/m_can_an004_dmu_handling.zip)、[Bosch M_TTCAN 3.3.0手册镜像](https://raw.githubusercontent.com/linux-can/can-doc/master/m_can/mttcan_users_manual_v330.pdf)。原厂站点的M_TTCAN旧直链本次不可下载，使用linux-can保存的同名Bosch文档，不把镜像托管方当芯片设计者。手册第3.1.4/3.1.5节用于Monitor/Restricted，第3.5.3节用于取消，第4章用于TTCAN；AN004第2.3节及配套RX timestamp示例用于DMU/TSU。外部资料未证明ET6801综合参数或实测结果，芯片位号和差异仍来自目标SVD。

本轮未完整审核全部压力/筛选/电气测试目录中的嵌入式CAN调用；不得仅凭上述路径命中表宣称“所有参考源码已经逐函数全覆盖”。下一轮需沿已发现的入口完成增量覆盖，不全盘重复扫描。

### 1.4 输入指纹

| 输入 | SHA256 |
|---|---|
| ET6801.svd | `49B2DE29BD7A0A4A5FBDEFC6E36D75CD6DA53A46F5504F860DEE53BE9079CCE4` |
| mttcan_cfg.svd | `C8C86D0B9FD84CEFCDCD765AAF7267E853E4789617A187ED6CDB6D94E0CFFDC5` |
| mttcan_misc.svd | `A37DC838A947F22020714AB9D54BFD16427BE622FC10F577969338D30E28A539` |
| Bosch M_TTCAN 3.3.0 PDF | `E9C9CD0F6324FE2BEE0B48B5037359FFA53E26D8F7DF2F927F0E9FB5765432D3` |
| Bosch M_CAN AN004 DMU handling PDF | `669CC6F5A814F063EBCF9A5E3979FB4F30F94F3AED7117C1649BA92452DC5C74` |
| 当前仓库et6x_can.c | `9445B565297F9C4DF77F71869EA8DD09C3CC9FA480CF1980806A419DA3AB7E65` |
| 6003需求can.json | `DDF0A29F9C46AFAE57934AC3A24D22DDC94070BFB57DDCC2E2ECDBB2866D7099` |
| 3101需求can.json | `E233A191488B07533298DF36781548A62F4248DAB7EAEB1608FB5998F3B6DEB2` |

资料扫描记录：`artifacts/runs/20260904_192700_000000_can_analysis/stages/doc-search.json`、`chip-query.json`。这些是分析证据，不是HIL结果。

## 第二章 IP驱动分析

### 2.1 当前驱动分组

| 驱动入口/类型 | 功能与实施注意 |
|---|---|
| CAN_setOpMode、CAN_init、CAN_config、CAN_setBitTime | 先INIT，再CCE，再保护配置，完成后退出；不能假定CAN_init自动复位全部硬件 |
| CAN_msgRAMConfig、CAN_addStdMsgIDFilter、CAN_addExtMsgIDFilter | 分区地址、容量与元素格式；应由芯片Mapping限定可用区域，防止与另一实例共享区重叠 |
| CAN_writeMsgRam、CAN_txBufAddReq、CAN_readMsgRam、CAN_writeRxFIFOAck | 写数据、请求、读数据、Ack分开；正式测试必须核对TX硬件终态和实际RX |
| CAN_enableIntr、CAN_selectIntrLine、CAN_enableIntrLine、CAN_clearIntrStatus | 外设源与NVIC/向量分层；ISR不写Expected或最终测试结论 |
| TX FIFO/Queue、TX Event、New Data类接口 | 可复用底层语义，缺少批量TX请求等原子动作时补Chip Driver，不在Service拼测试循环 |
| CAN_enableDMUTransferTS、CAN_configTSU、CAN_setDMURxRequest | DMU帧大小、时间戳格式、RX选择有耦合；CAN只配置自己的端点，DMA通道由PC组合 |
| CAN_eccConfig | 现有实现涉及SYSC全局ECC开关；实施时由SYSCTRL与CAN各自接口分拆、PC组合，不能沿用跨IP调用作为Wrap捷径 |
| CAN_TxBufElement / CAN_RxBufElement | data为uint16_t[64]，每元素低8-bit承载一个线上Byte。64-byte帧比较128个结构内存字节不自动等于越界，但公共接口必须使用byte[]并解码后比较 |

### 2.2 已确认驱动问题与当前处理状态

| ID | 当前位置/证据 | 问题及影响 | 正确处理边界 |
|---|---|---|---|
| D01 | et6x_can.c：CAN_eccConfig、CAN_setDMURxRequest，均为CAN0分支否则CAN_MISC1 | CAN2的MISC配置误写CAN1，影响ECC/MORD和DMA RX选择；IS_CAN_PERIPH却允许CAN2 | Chip Driver按完整实例映射选择MISC；补三实例隔离回归，不修改公共Case写死CAN2 |
| D02 | CAN_isFDOpEnable读取MISC_STATUS.TTCAN_CCE | 查询FD实际返回配置变更使能，而非CCCR.FDOE；并有同样CAN2误选实例问题 | 正确读取FD语义对应字段；不能让Capability或Case用该错误值宣布不支持FD |
| D03 | CAN_config判断tsPrescalar≤CAN_TSCC_TCP_MAX，随后写tsPrescalar-1 | MAX为0xF，允许0、拒绝16；SVD TCP编码0～15对应实际分频1～16 | 入参范围1～16，保留SDK风格；回归0拒绝、1/16正确，修复后由Wrap使用实际分频 |
| D04 | CRG_getCANClock读取PLLCLK_CFG0旧字段；FPGA直接返回40000000；时钟选择配置段有注释关闭 | ET6801 SVD对应PLLCLK_CFG3 CAN分频/源选择；当前查询不能证明真实20/40/80MHz或AUX | 在后续获准的CRG范围内修驱动/Mapping，先确认FPGA时钟事实；不能在CAN Case补常量 |
| D05 | et6x_crg.h只列CRG_PERIPH_CAN0/CAN1，而SVD有FDCAN2门控 | 三实例复位/门控的公开枚举及底层映射需进一步核对，不能用旧枚举数值推断SRST位置 | 将CAN复位序列、共享时钟影响与CAN2映射核对列为开发前项；此项是待核对缺口，不断言已证全部复位错误 |

注意：CAN_enableDMUTransferTS关闭分支只清UTSU，**本轮不据此认定DMUC.TTS残留Bug**。SVD明确UTSU=0时TTS被硬件保持为0，后续应读回验证；不能按软件赋值缺一行就盲改。

2026-09-04修复进展：D01已补齐三实例MISC选择；D02改读CCCR.FDOE；D03在任何写入前校验实际分频1～16及Timeout上限。D05已核对GTEN1/SRST1 bit0～2，并补CAN2枚举和CRG公共类别CAN=10映射，旧类别不变。D04时钟源事实仍待闭合，未改成猜测值。

新增D06：原CAN_readMsg/CAN_writeMsg及DMU缓存编解码只按FD表换算DLC，导致Classic DLC9～15读取/写入超过8-byte，Remote也错误搬运payload。现按FDF/RTR分别计算实际数据长度，保留原始DLC。完整SDK源码的本机寄存器桩回归已执行通过，包括三实例隔离、FDOE/CCE独立对照、非法分频无副作用、Classic/FD/Remote搬运边界。它不是CAN硬件PASS；测试源码为`framework_validation/unit/firmware_contract/test_can_driver_native.py`。

### 2.3 需要补齐的Driver能力

优先复用现有接口；预计需要原子多项TX请求、受保护写测试、完整无隐式清除快照、受限Message RAM测试访问、完整TSU元素读取及DMU一次非法刺激接口。具体缺口须逐函数对照后定，不预先重复新增同名近似函数。所有测试补充函数放Chip Driver头/源底部隔离区，命名区分SDK常规驱动；Wrap调用Driver，Service只解码/执行对应Wrap动作。

**本轮没有确认“全部驱动接口已足够”，没有实现任何上述补充函数。**

## 第三章 IP寄存器分析

### 3.1 关键寄存器与副作用

偏移均相对于对应CAN基址；位号来自ET6801 SVD。这里只列测试相关字段，不将保留位批量写成全1。

| 寄存器/偏移 | 核心字段 | 测试意义 |
|---|---|---|
| CREL 0x000、ENDN 0x004 | 版本、端序标识；ENDN复位0x87654321 | 身份/可访问性，不证明功能收发 |
| DBTP 0x00C | TDC[23]、DBRP[20:16]、DTSEG1[12:8]、DTSEG2[7:4]、DSJW[3:0] | FD数据段位时序及TDC |
| TEST 0x010 | RX[7]、TX[6:5]、LBCK[4] | RX读入、TX测试控制与回环 |
| RWD 0x014 | WDV[15:8]、WDC[7:0] | Message RAM访问Watchdog |
| CCCR 0x018 | NISO15、TXP14、EFBI13、PXHD12、WMM11、UTSU10、BRSE9、FDOE8、TEST7、DAR6、MON5、CSR4、CSA3、ASM2、CCE1、INIT0 | 各配置独立；INIT复位为1，不能用“全部为0”检查复位 |
| NBTP 0x01C | NSJW[31:25]、NBRP[24:16]、NTSEG1[15:8]、NTSEG2[6:0] | 仲裁位时序；减一编码与公共整数分离 |
| TSCC 0x020、TSCV 0x024 | TCP[19:16]、TSS[1:0]、TSC[15:0] | 16-bit时间戳与分频1～16 |
| TOCC 0x028、TOCV 0x02C | TOP[31:16]、TOS[2:1]、ETOC0 | 连续/三个FIFO控制的超时；空FIFO重装 |
| ECR 0x040、PSR 0x044 | TEC/REC/CEL、LEC/DLEC、BO/EW/EP、TDCV | 错误状态读取有副作用，首个读取值要留证 |
| TDCR 0x048 | TDCO[14:8]、TDCF[6:0] | 延迟补偿窗口，不是普通CAN BRP |
| IR 0x050、IE 0x054、ILS 0x058、ILE 0x05C | IR/IE/ILS每源位；ILE bit0/1 | 原始事件、Source使能、路由、Line使能分开 |
| GFC 0x080、SIDFC 0x084、XIDFC 0x088、XIDAM 0x090 | Remote/未匹配策略；标准/扩展Filter位置和数量；29-bit AND Mask | 不同类型Filter及列表次序必须有边界输入 |
| HPMS 0x094、NDAT1/2 0x098/0x09C | 优先级Filter索引、64个RX New Data位 | 优先级记录和专用Buffer接收 |
| RXF0C/S/A 0x0A0/A4/A8，RXF1C/S/A 0x0B0/B4/B8 | F0OM/F1OM31、水位、大小、Full24/Lost25及Get/Put | 参数字段位宽不等于实际容量；RX FIFO最多64项的描述要按限制执行 |
| RXBC 0x0AC、RXESC 0x0BC | 专用Buffer起始、各RX元素数据容量 | RAM预算包含2-word头，不是payload乘条数 |
| TXBC 0x0C0、TXFQS 0x0C4、TXESC 0x0C8 | TFQM30、Queue/FIFO项数、专用Buffer数、payload容量 | 总TX索引32项，专用与FIFO/Queue共享预算 |
| TXBRP/BAR/BCR/BTO/BCF 0x0CC～0x0DC | 32-bit请求/取消/完成位图 | Pending和真实发送成功分开，取消竞态单列 |
| TXBTIE/BCIE 0x0E0/E4 | 按Buffer使能完成/取消中断 | 不能仅打开IE.TC就假定所有Buffer投递 |
| TXEFC/S/A 0x0F0/F4/F8 | 事件大小、水位、丢失、Get/Put | 事件清除/出队使用其Ack，不是RX Ack |
| TT寄存器 0x100～0x140 | TTTMC/TTRMC/TTOCF/TTMLM/TURCF/TTOCN/TTIR/TTIE/TTILS等 | 表明时间触发硬件存在；Level1最小周期/触发表见3.4；完整TT扩展不由基础Case推导 |
| TSU 0x160～0x1B0 | TSCFG、TSS1、TSS2、TS0、TS1、ATB | 内外时间基、指针、新/丢失；读取Timestamp会清对应TSS1位 |
| DMU虚拟窗口 0x200/0x280/0x300/0x380 | TX / RX0 / RX1 / TX Event | 虚拟访问顺序与RAM地址递增不是同一语义 |
| DMUI/DMUQC/DMUIR/DMUIE/DMUC 0x3C4～0x3D4 | Enqueue/Dequeue、非法访问、错误、TTS | 需要明确步进和元素结束动作 |
| MISC_CTRL，逻辑offset0x804 | DIS_MORD0、CLKSTOP_REQ1、DMA_ACK2等 | DIS_MORD=1禁止部分读清副作用；不能与ECC的读改写纠错混淆 |
| MISC ECC 0x820～0x834 | EN/MASK/FORCE/CLR/RAW/STATUS，bit0/1 | 仅Force不等于ECC数据注入 |
| MISC_STATUS 0x838、DMU_WAIT 0x83C、DMU_DMA_CFG 0x840 | 请求/应答事实、等待配置、RX_SEL[5:4] | CAN2实例映射必须修正后使用 |

IR常用源：RF0N/W/F/L=0～3，RF1N/W/F/L=4～7，HPM8、TC9、TCF10、TFE11、TEFN/W/F/L=12～15，TSW16、MRAF17、TOO18、DRX19、BEC20、BEU21、ELO22、EP23、EW24、BO25、WDI26、PEA27、PED28、ARA29。公共Case用逻辑Source，报告通过Mapping展示这些真实名字。

### 3.2 SVD/驱动冲突和待确认事实

| ID | 证据与矛盾 | 状态/处理 |
|---|---|---|
| S01 MISC地址 | 整片SVD把CAN_MISC0/1/2 base列为0x4051C800/0x40524800/0x4052C800，同时MISC寄存器又带0x800起始偏移；当前头文件CAN_MISC基址采用CAN基址，结构体保留0x800再到ET_HEAD | CONFLICT。按SVD直接base+offset会多加0x800。后续先核对RegGen源/合并映射并验证只读签名；本轮不修改SVD、不让生成器静默修正 |
| S02 TSU寄存器数量 | TSS2.NTSG默认编码1描述8个Timestamp，最少编码也有4个；当前独立SVD只列TS0/TS1，无对应TS2～TS7数组 | CONFLICT。不能把“只枚举两个”当硬件只有两个，也不能按手册猜地址写入；全槽地址仍需修订；P1_018只使用TS0、NTSG和TSS1即可构造New/Lost，不再因此阻塞单槽方法 |
| S03 Message RAM | 6801驱动/FPGA UT5采用CANx-0x4000、16KiB；6003/3101 FT7采用CANx-0x2000、8KiB；UT6文字称共享 | 当前6801范围有源码证据，物理容量/可共享关系仍NEEDS_VERIFICATION；不能复制旧8KiB，也不能凭UT6标题断言三实例别名 |
| S04 时钟 | CRG.PLLCLK_CFG3描述PLL/AUX及分频；驱动使用旧PLLCLK_CFG0，FPGA写死40MHz；分频描述里还有400M/600M混杂 | CONFLICT。20/40/80MHz组合、AUX路线和FPGA受控性需以当前实现确认，尚不能标“FPGA不支持” |
| S05 旧芯片描述残留 | MISC grant/exit类字段注释有“6002已经删除”等内容 | 不能据此判定ET6801功能不存在；相关RAM仲裁/时序结论保持待核实 |
| S06 ECC控制 | SYSC.INJECT[13]名为1BIT、[12]名为2BIT，但bit12描述同样写注入1-bit；旧FT7注入调用注释 | CONFLICT/UNKNOWN：不能只按宏名确定双错和注入时点；P2_006的写/读阶段分离诊断见3.4，不能宣称真实纠错已覆盖 |
| S07 DMU错误位 | DMUIR描述RX1错误bit16～21，但RX0对应组未列，resetMask相关位也不包含；Bosch通用配套源码列RX0错误 | CONFLICT。P2_007仅选目标SVD明确的9项；不得平移RX1位号补RX0。P2_008保留RX0数据路径，未映射的错误位单列缺口 |
| S08 TDCV含义 | PSR.TDCV描述是TX→RX测量延迟加TDCR.TDCO，即SSP位置 | VERIFIED：修正前稿“纯线路延迟”标签。线路实际延迟需独立测量，关闭TDC时不强断言TDCV有效 |
| S09 TEST/TSCFG访问属性 | SVD部分字段列read-only，但描述需要TEST.TX选择和TSCFG配置，SDK/原厂代码也执行配置写 | CONFLICT。实现时先按配置窗口及目标Driver读回验证；不按错误access属性直接判硬件不支持或批改SVD |

### 3.3 公共Observation -> ET6801映射

| 公共端点 | ET6801真实来源 |
|---|---|
| IDENTITY / CONFIG | CREL、ENDN、CCCR、NBTP/DBTP及各布局字段；配置前后直接读回 |
| CONFIG.INPUT_CLOCK_HZ | CRG实际源/分频与FPGA已证时钟输入组合；不是D04旧查询值 |
| TX.PENDING / COMPLETED / CANCELLED | TXBRP / TXBTO / TXBCF；请求来自TXBAR、取消来自TXBCR |
| RXn.FILL/FULL/LOST/GET_INDEX/PUT_INDEX | RXF0S/RXF1S对应FnFL/FnF/RFnL/FnGI/FnPI；Lost事件同时参考IR对应位 |
| RX.FRAME / FILTER_INDEX / ACCEPT_NON_MATCH | Message RAM RX元素的ID/RTR/XTD/FDF/BRS/DLC/FIDX/ANMF与payload |
| RX_BUFFER / NEW_DATA | RXBC指定RAM与NDAT1/NDAT2 |
| HIGH_PRIORITY | HPMS及IR.HPM |
| TX_EVENT | TXEFS、TXEFC、TXEFA及RAM事件ID/Marker/ET/Timestamp |
| IRQ.RAW / 使能/路由 | IR / IE / ILS / ILE；不要虚构不存在的统一IRQ_STATUS寄存器 |
| IRQ_EVENT | ISR读取源并锁存的实例、Line、Source、Count，属于软件观测 |
| TIMESTAMP / TIMEOUT | TSCV、TSCC、IR.TSW / TOCV、TOCC、IR.TOO |
| TDC.ENABLE / OFFSET / FILTER / SAMPLE_POINT | DBTP.TDC[23] / TDCR.TDCO[14:8] / TDCR.TDCF[6:0] / PSR.TDCV[22:16]；TDCV=测量延迟+TDCO，单位mtq，不是纯延迟；参数不直接沿用参考代码的4 |
| CLOCK.SOURCE / DIVIDER | CRG.PLLCLK_CFG3的CAN源选择及分频；D04修正后读取，不能以旧PLLCLK_CFG0读值作为证据 |
| CLOCK.STOP_REQUEST / STOP_ACK | CCCR.CSR / CSA；若改用MISC请求须单独说明两者连接依据 |
| DMA.STATUS / DESTINATION | AHBDMA通道Raw/终态及DMA目标RAM，CAN DMA请求与虚拟窗口映射独立提供 |
| DMU.ERROR | DMUIR及DMUI相关错误位，不能用DMA成功代替 |
| ECC_IRQ | CAN_MISCx.ECC_INT_RAW/STATUS/EN/MASK/FORCE/CLR |
| PROTOCOL | PSR与ECR；DIS_MORD控制的副作用必须标注本次是否消费 |
| TSU.NEW / LOST / TS0 / ACTIVE_TIMEBASE | TSS1.TSN[15:0] / TSL[31:16]、TS0、ATB；读TS0清TSN0/TSL0 |
| TSU.COUNT / CAPTURE_SOURCE | TSS2.NTSG[13:12] / ITBG[15:14]、TSCFG.TBCS[1]/SCP[2]/TBPRE[15:8]；分频实际值=编码+1 |
| TRANSMIT_PAUSE / MODE / TEST.RX | CCCR.TXP[14]/MON[5]/ASM[2]、TEST.RX[7]；TEST.TX[6:5]控制输出 |
| WATCHDOG.CONFIG / VALUE / IRQ.WDI | RWD.WDC[7:0]/WDV[15:8]、IR.WDI[26]；注入器记录真实CAN主机RAM应答延迟 |
| TT.SYNC_STATE / MASTER_STATE / CONFIG_ERROR | TTOST.SYS[5:4]/MS[3:2]（In_Schedule/Time Master均编码3）、TTIR.CER[18] |
| RX_TRIGGER.MSC | TTTMC所指Trigger RAM中接收触发元素的MSC；不是TTOST或PC累计值 |
| OBSERVER.CAPTURE | 实际另一CAN实例或外部分析仪的接收记录，不来自被测CAN本机自回环 |

### 3.4 本轮14项目标的硬件构造依据

以下位号用于芯片Mapping及人工复核，公共Case不直接写这些地址/编码。每项配置前复位CAN和资源；新增SYSCTRL/CRG/DMA动作分别走各自Driver，不塞进CAN Service。这里定义的是测试方法，不是当前FPGA结果。

| 目标 | ET6801关键配置/最短刺激 | 必须观察及判据 |
|---|---|---|
| P1_017 取消/重发 | CCCR.DAR[6]=1/0；正常总线仅Peer可ACK，将其设静默，向专用Buffer发一次TXBAR；DAR=0出现重复尝试后写对应TXBCR | 首次PSR.LEC=3 ACK错误；禁重发一次失败即退出Pending，允许重发至少两次；无ACK取消后TXBRP=0、TXBCF=1、TXBTO=0；恢复ACK再发成功。普通取消竞态允许BTO/BCF同时1，不能套本无ACK判据 |
| P1_018 TSU | CCCR.UTSU=1，TSCFG.TSUE=1、TBCS=0、TBPRE=3（实际4分频）；TX.TSCE=1，RX SSYNC/ESYNC=0，内部回环；N由TSS2.NTSG解码 | 最多N帧直到TSN0=1，读取TS0清TSN0/TSL0；不读槽连续2N个捕获令TSL0=1；内部TS0落ATB前后区间。外部TBCS=1由真实32-bit输入分别给两个常量，不把CAN盒子时间戳当输入 |
| P1_019 模式 | CCCR.MON[5]与ASM[2]分别设置，禁Loopback；Peer提供完整合法Classic位流，即使缺ACK也不破坏EOF | Normal接收/ACK/主动TX均可；Monitor接收、不ACK、不主动TX且TXBRP保持复位；Restricted接收并ACK、不主动TX。错误抑制不是本基础Case断言 |
| P1_020 FD格式 | CCCR.NISO[15]、FDOE[8]/BRSE[9]；DUT/Peer四种ISO组合×16/64-byte，失配只发一次 | 同格式有效RX数据相等；交叉格式无有效RX且首次LEC/DLEC属于实际协议错误，IR.PEA/PED有对应证据；不规定唯一首错误码 |
| P2_006 真实ECC | SYSC.ECCEN.MTTCAN[0]；INJECT单错bit13、双错bit12存在描述冲突；单word写/读阶段分别限时开启注入，禁止两个阶段同时注入 | 同时取数据、CAN_MISC ECC Raw及SYSC错误地址。单错=正确数据+Corrected+地址匹配；双错=Uncorrected+地址匹配。作用时点/范围未定，不是任一分支报警就PASS |
| P2_007 DMU错误 | DMUI.EHS需处于等起始地址的空闲状态、ENa有效；具体9条刺激见下表；除CCE负向外CCE=0；没有活动DMA | 对应DMUIR位0→1、DMUIE打开后实际CANx_DMU ISR首次记录同源并屏蔽该源，防止中断风暴。DMUIR的SVD只读，不能发明W1C；保存证据后CRG复位再做合法DMU回环 |
| P2_008 DMU时间戳 | CCCR.UTSU、DMUC.TTS、TSCFG.TSUE；RX Filter SSYNC/ESYNC=1。正例为8-byte payload、64-byte元素，避免有效数据占最后word | AN004明确RX末4-byte会被TSU值替换；比对有效8-byte、DMA末word与对应TSU值及ATB前后区间、DMUQC出队计数。原FT5的满64-byte不能原样当无损时间戳正例。P2_008在DMA后才读TS0，避免前置读清；TX Event TTS格式单列P2_013 |
| P2_009 协议错误 | ACK撤回、数据位翻转、6同值Stuff违例、固定分隔位违例、正确填充下错误CRC分别独立；只用数据段bit1错误反复推动Bus Off | PSR.LEC/DLEC、ECR.TEC/REC、IR.PEA/PED/EW/EP/BO首次值及注入位流；BO后INIT请求退出并给129×11 recessive恢复，不能CRG复位冒充协议恢复 |
| P2_010 RAM Watchdog | RWD.WDC=16，注入器只延迟CAN主机RAM应答8/32个系统时钟；再做WDC=0、延迟32对照 | 实际握手周期独立记录；只有16/32组合WDI=1并进ISR，其余无WDI。CPU睡眠、TOCC超时或DMA慢均不能代替 |
| P2_011 TTCAN | Level1 TTOCF.OM=1、TM=1，严格周期；参考ID 0x100和专用Buffer0，数据Buffer1，TTMLM.CCM=0、TXEW=15（16 NTU）、ENTT=1；6项Trigger见下文 | TTOST.SYS=3、MS=3；3稳定周期的真实TX采样时刻在窗口；接收正常MSC=0、只漏一帧后MSC=1；TTIR.CER=0。CAN盒子仅需ACK及按参考帧定时回复，不要求自身TTCAN栈 |
| P3_002 TDC边界 | DBTP.TDC=0/1、TDCR.TDCO=S/TDCF=0；DUT RX安全隔离回送，实际延迟选正常采样点S两侧，限制SSP范围 | 低延迟开/关成功，高延迟关报数据位错误、开成功；开启测量后PSR.TDCV约D+S。D由TX/RX探头实测，合计预算2 mtq；不称最大规格测试 |
| P3_003 边沿过滤 | CCCR.EFBI[13]=0/1；Bus Integration期间注入1/3 tq dominant，相位避免落在采样边界 | 过滤关的正对照同步、开时短脉冲不硬同步而长脉冲同步；TEST采样点能否唯一表征同步尚需确认，不能用“未收到帧”代替 |
| P3_004 TX Pause | CCCR.TXP[14]=0/1；TX FIFO预装4帧后一次TXBAR，Peer只ACK，保持Error Active | 3对EOF结束至下一SOF间隔差为2 nominal bit；500k下4 us，差分容差0.2 bit；禁止以PC命令间隔测量 |
| P3_005 TEST pins | CCCR.TEST=1，TEST.TX[6:5]=2/3/1分别dominant/recessive/sample point；实际RX分别低/高读TEST.RX[7] | 外部引脚低/高和8个采样脉冲；退出INIT后测周期=nominal bit±0.1 bit；退出TEST再正常双向收发。夹具隔离输出，禁止硬短接推挽 |

**DMU九个独立节点**：每行从新复位/空闲开始，不在一次失控状态上叠加错误。

| 节点 | CPU受限访问（相对当前CAN） | 目标DMUIR字段 |
|---|---|---|
| TX非法读 | read虚拟TX起始+0x200，返回数据不作判据 | TXEIR bit5 |
| RX1非法写 | write虚拟RX1起始+0x300 | RX1EIW bit19 |
| Event非法写 | write虚拟Event起始+0x380 | TXEEIW bit27 |
| RX1空出队 | RX1 FIFO空、DMUI.RX1R=0时read+0x300 | RX1EID bit17 |
| Event空出队 | Event FIFO空、DMUI.TXER=0时read+0x380 | TXEEID bit25 |
| DLC越容量 | TXESC.TBDS=0容量8-byte、有TXR，write T0后write T1为FD且DLC15 | TXEIDLC bit3 |
| 配置期访问 | CCCR.INIT/CCE=1时访问任一虚拟起始窗口 | IAC bit30 |
| TX非起始地址 | DMU空闲时先write+0x204 | TXENSA bit0 |
| TX地址不连续 | TXR=1时write+0x200，再跳过+0x204直接write+0x208 | TXEIAS bit2 |

TXEWATA bit4描述为“超过Trigger Address的多余写被丢弃/容忍”，不把它误列为等同中止的非法DLC。RX0错误位缺失见S07，没有据此删除RX0数据功能。

**TTCAN最小参数补充**：NTU=nominal bit=2 us；TURCF的NC=0x10000+NCL、DC非0，按实际host clock求NC/DC，满足Level1的NC≥4×DC，设定后才ELT=1。初始化Watchdog TTTMK=0xFFFF；不启用无关应用Watchdog/外部事件同步。Trigger为Time Base(100,TYPE9)、TX Continuous(1000,TYPE3,MNR1)、RX(5000,TYPE8,MNR为0x321的Filter)、TxRef(10000,TYPE0,MNR0)、Watch(12000,TYPE6)、End(TYPE10)。前3项CC=1每周期有效，MSC初始0；接收时间标记事件只用于ISR采集原始MSC/Cycle，不在ISR判Case。保持接收过滤列表只接收指定数据ID，参考消息由TTRMC识别。参考SOF与TX开始的采样基准按原厂4.5节换算，不直接把总线SOF边沿等同采样点，不把10000 NTU配置武断写成精确20ms实测周期。当前只覆盖最小Level1，不扩称全部TTCAN。

**剩余确认流程**：公共5.1～5.3给出ECC两阶段隔离、DMU Debug镜像/时间戳对比及边沿同步正反例。现阶段不运行这些诊断、不分配新Wire；确认缺口应由精确硬件定义或后续授权的最小诊断解决，不能继续无范围地扫描其他芯片。

## 第四章 参考测试代码与需求覆盖

### 4.1 需求逐项追踪

两份JSON的TP续行无ID仍保留。引用“6003/3101 TP行r”表示各自原source_row；Case引用“序号+原ID+名称”，因为CAN_TC_003/004重复，不能按ID去重导致FD/DMA丢失。

| Source Item | 原始测试意图 | ET6801适用性 | 对应目标/尚缺证明 | 处置 |
|---|---|---|---|---|
| 两份TP001，row2 | CAN0/1数量覆盖 | ET6801有3实例，覆盖应扩为实际声明实例 | P2_004，独立功能Case代表实例，不冒称全实例 | MAPPED |
| 两份TP002，row3 | CAN/CAN FD | SVD有FDOE/BRSE | P0_002、P1_001 | SPLIT |
| 两份TP003，row4 | 500k/1M/5M | 有位时序寄存器；实际时钟待D04 | P1_012；5M是FD数据段，不构造Classic 5M | MAPPED |
| 两份TP004，row5 | 全局/标准Filter | GFC/SIDFC | P1_002；扩展补P1_003 | MAPPED |
| 两份TP005，row6 | Message RAM最大/共享 | 物理关系S03尚未闭合 | P1_016、P2_004；最大合法各分区组合尚需增补，不能称全容量配置已覆盖 | UNKNOWN |
| 两份TP006，row7 | INT0/INT1 | 两线存在 | P1_011 | MAPPED |
| 两份TP006续行，row8 | DMU IRQ | 三实例DMU向量存在 | P2_007，9项最短非法访问加实际ISR，不由DMA TC替代 | MAPPED |
| 两份TP007，row9 | DMA/DMU send/receive | DMU及请求配置存在 | P2_001、P2_002、P2_008数据及RX时间戳均PLAN；独立Event附加仍见P2_013 | SPLIT |
| 两份TP008，row10/11 | TSU内部/外部 | SVD支持，单槽方案避开S02未列全地址 | P1_018内外时间基/New/Lost、P2_008 RX附加已PLAN，P2_013 Event格式另补；不以TSCV替代 | SPLIT |
| 两份TP009，row12 | 轮询收发 | Driver路径存在 | P0_002、P0_003 | SPLIT |
| 两份TP010，row13/14/15 | 20/40/80MHz采样点 | S04待确认实际可提供时钟 | P1_012；三行都保留，记录实际速率与采样点 | UNKNOWN |
| 两份TP011，row16 | ECC使能 | SYSC.ECCEN及MISC存在 | P1_016记录使能读回、P2_006真实ECC；Force不代替 | UNKNOWN |
| 两份TP011，row17 | March-C | SRAM访问方式存在 | P1_016明确March C-六阶段；不是仅0x5A/0xA5 | MAPPED |
| 两份TP011，row18 | RAM空间覆盖 | S03待确认范围 | P1_016全声明区域遍历，容量依据闭合前不能执行破坏写 | UNKNOWN |
| 两份TP012，row19/20 | 内部/外部回环 | TEST/CCCR可选 | P0_002和P2_005分别证明内部与引脚差异 | SPLIT |
| 两份Case序号1 TC001 内回环 | 1M、≥2帧不同8-byte、TX/RX IRQ、分析仪无数据 | 适用 | P0_002基础、P1_011 IRQ、P2_005外部静默；不要求每条Case重复所有条件 | SPLIT |
| 两份Case序号2 TC002 外回环 | 1M、≥2帧、TX/RX IRQ、外部分析仪收到 | 适用 | P2_005、P1_011；本轮P1_011显式保留外部回环+IRQ组合，不能只执行内部节点 | SPLIT |
| 两份Case序号3 TC003 速率 | 125k/250k/500k/800k/1M | 适用，受真实输入时钟约束 | P1_012 | MAPPED |
| 两份Case序号4 TC004 过滤 | Range/Dual/Classic Mask | 适用 | P1_002/003，不照抄旧FilterIndex覆盖 | MAPPED |
| 两份Case序号5 TC003 CAN FD | 2M、64-byte、两帧不同 | 适用 | P1_001、P1_012；不能被前一个重复ID挤掉 | SPLIT |
| 两份Case序号6 TC004 DMA/DMU | DMA发送与接收FD 64-byte | 适用 | P2_001；明确头部、payload、DMA字数 | MAPPED |
| 两份Case序号7 TC005 CAN_CLK | 20/40/80MHz | S04 | P1_012 | UNKNOWN |
| 两份Case序号8 TC006 RAM | 模式读写与ECC注入意图 | 注入时序未闭合，不是不适用 | P1_016、P2_006 | UNKNOWN |
| 3101 Case序号9 TC007 80M | 80MHz内核、1M通信、上位机比对 | ET6801有CAN时钟配置，不能略去 | P1_012的80M/1M节点 | MAPPED |
| 3101 Case序号10 TC008 AUX | 外部AUX信号源/PWM输入与CAN通信 | CRG明确有AUX选择，适用目标保留 | P2_012；当前连接与FPGA实现待核实 | UNKNOWN |

### 4.2 源码测试意图与有效性

| 文件/函数族 | 实际逻辑与局限 | 正式计划去向 |
|---|---|---|
| ET6801 UnitTest/test_can.c，CAN_UT_1～4 | 基础Classic/FD、IRQ、DMU；部分注释写内部，实际参数为EXTERNAL | P0_002/003、P1_001/011、P2_001；按实际Mode而非注释还原 |
| ET6801 test_canfd.c，InitDev、CanFrameTxRx、RemoteFrame、FDFrame | 初始化、多帧格式和Remote；打印及固定等待不等于完整硬件判据 | P0_001、P1_001/004 |
| 同文件_StdIDFilter/_ExtIDFilter | Range/Dual/Mask和FIFO/Buffer路由；部分专用Buffer项复用同一FilterIndex覆盖前项 | P1_002/003/007，各节点先独立复位，不照搬覆盖错误 |
| 同文件ITLine0/1、ISR、WaterMark、RejectRemote | 中断两线配置、水位/Remote意图；有些只配置/打印，缺少充分刺激 | P1_005/009/011/004 |
| 同文件PowerDown/Workmode/Speed，部分在#if 0 | 停钟请求、各Mode、速率意图仍保留；被注释不构成硬件不支持证据 | P1_015/019/012 |
| 同文件TxEvent、TxFIFOFull、timestamp、timeout、edgefilter、LongTimeRunning | 空函数或仅return；不能计历史实现覆盖或PASS，但功能目标保留 | P1_008/009/013/014、P3_003/001 |
| 同文件Can2Can、CAN_pressure_test | 双节点及200万帧FD 64-byte连续请求；压力中开启TDC，但只配置不证明延迟窗口 | P0_003、P3_001；TDC启用后的FD通信单独P1_021，延迟边界仍P3_002。20轮是当前快速回归规模，不宣称等价200万帧长稳 |
| ET6801 FunctionalTest/can_ft.c FT1/2/3、UT4、FT5 | Classic、速率、FIFO回传、FD、DMA+TSU；注释与BRS实际值可能不同，TSU附加格式要重审 | P0/P1_001/012、P2_001/008 |
| 同文件CAN_FT_4 | 实际调用SPI/EEPROM测试 | NO_MATCH_CAN：不纳入CAN Feature，不算删除CAN覆盖 |
| ET6801 FPGATest/can_fpga_test.c UT1～4 | Classic/FD/IRQ/DMA，入口并非全部启用 | 对应基础、帧、IRQ、DMU目标；本轮不声明旧HIL PASS |
| 同文件UT5 | 16KiB写5A/A5后回读；ECC注入调用注释，第一轮报错分支Expected误用A5 | P1_016；真实ECC另P2_006，修正Expected不能沿用错误诊断 |
| 同文件UT6 | CAN0/1/2不同偏移收发，标题称shared；不能仅凭标题证明RAM别名或并发仲裁 | P2_004，先闭合S03；跨节点总线仲裁仍待补 |
| ET6801 regscan_smoke_test.c CAN片段 | 写CUST/TTCSM后要求不变；当前SVD无CUST，TTCSM为只读 | 保留只读不可写意图到P0_001扩展项；先确认合法字段，不能盲写旧CUST保留地址 |
| 两个ET6801 Doc/examples | 一个基本回环读FIFO并Ack；另一个预装多帧、TX Event水位IRQ与发送优先级 | P0_002、P1_008/009/011；逐项提交可能第一帧已发送，正式顺序Case用原子请求 |
| 6003/3101 verification UnitTest/test_canfd.c | 两者SHA相同；与6801主要差异为引脚枚举改名；相同测试意图合并，不按芯片复制Case | 以上FDCAN同名族去向一致，不能将相同源码副本计为两套额外覆盖 |
| 6003 FPGATest/CAN、FDCAN；3101对应CAN、fdcan0 | 基础外回环、FD、DMA、中断 | P0_003、P1_001/011、P2_001；旧实例数、IRQ及RAM偏移不移植 |
| 两个独立SDK FunctionalTest/can_ft.c FT1～4 | Classic、速率、RX回传、FD | 基础及P1_001/012；固定等待改为真实TX/RX完成判据 |
| 同文件FT5、TJA1145等 | SPI访问及外部收发器配置；不属于CAN控制器内部Feature | 收发器由Bench负责必要初始化，排除SPI EEPROM应用测试 |
| 同文件FT6、FT7 | DMU+TSU、8KiB RAM模式；单错注入函数存在但调用注释 | P2_001/008、P1_016/P2_006；不能以“有函数”宣称注入曾通过 |
| 3101 SDK FT8 | 80MHz内核1M通信 | P1_012明确保留80M节点 |
| 3101 SDK FT9 | 20MHz AUX信号源、1M外回环；旧GPIO29与UART TX冲突，函数本身仅发送 | P2_012，不能复用旧管脚；先保证ATP控制UART不被占用，再补外部有效接收判据 |
| 两个SDK SmokeTest/can_smoke_test.c | 单帧外回环、8-byte逻辑数据、uint16数组比较16内存字节 | P0_002/003，字节表示转换后比较；比较16本身不是越界证据 |

源文件存在不等于执行过：6003 SDK CAN_FTest的多个FT调用已经注释，单独记录配置/辅助函数不能当有效测试结果。对仅扫描到函数族但尚未逐路径闭合的实现，沿表中缺口继续分析，不伪称来源全审完。

### 4.3 容易复发的Case设计错误

- 收到回环帧不能证明正常外部总线；必须关闭Loopback并读取另一节点数据。
- FD 64-byte不能固定“DMA=16 word”：还需头部及可选时间戳；uint16 SDK承载与线上Byte区分。
- ISR先Ack或读清再让PC观察，会丢水位/错误证据；需先定义谁拥有首次读取。
- 无ACK只证明ACK错误；不能自动推断一定Bus Off。外回环可能自确认，更不能用它制造真实ACK缺失。
- 仅Force ECC IRQ不证明纠错；仅调高FIFO阈值不等于制造溢出。
- 逐帧发送完再发下一帧不能证明Queue优先级；必须建立同时Pending。
- 未完成时钟、TSU、MISC映射不是SKIP依据；先列实现/硬件事实缺口，不伪装环境不支持。

### 4.4 历史方法的最小复用与证据边界

先复用历史真实刺激，再补独立Expected与完成判据；不因历史没有复杂测量设备，就给基础通信强加示波器。也不因函数为空或调用注释而假定某功能已经测过。

| 历史来源（相对1.3的SDK根） | 已提取方法 | 当前构造及保留边界 |
|---|---|---|
| `6801/et6801-verification/DFP/Test/UnitTest/test_canfd.c`，CAN_pressure_test，约1599～1640行；6003/3101同名族 | 外回环、FD BRS、64-byte，启用TDC；offset=4、filter=0 | 新P1_021使用正常外部总线，由CAN盒子双向收发，各2帧；记录DBTP.TDC、TDCR和PSR.TDCV。ET6801 offset须按实际数据位时序确定，不把4视为通用值；不要求另加延迟器，不声称边界已覆盖。 |
| `3101/et3101-sdk/DFP/Test/FunctionalTest/can_ft.c`，CAN_FT_9，约1061行 | 外部20MHz AUX，按20MHz表配置1Mbps，发Classic 8-byte，PC观察 | P2_012已形成PLAN：先供时钟、静态切源、正常总线双向两帧、切回后各一帧。CAN盒子负责数据观察；AUX入口/电平/FPGA透传是待完成映射，不再以没有接线为由不给PLAN。旧GPIO29不适用于本芯片。 |
| `6801/et6801-verification/DFP/Test/FunctionalTest/can_ft.c`，CAN_FT_5，约765～820行 | TSCFG启用，内部时间基、分频4；UTSU/TTS开启，Normal模式FD 64-byte，tx_tsce=1，efc=0，DMU写18word后读18word | AN004证实RX末word被时间戳替换：正常参数改为8-byte payload、64-byte元素，满64-byte作为覆盖冲突负向，不再要求数据和timestamp同时无损。RX0/RX1在P2_008。该历史函数efc=0，不能证明TX Event曾测试；Event附加是SVD另行声明的目标，P2_013保留其格式缺口。 |
| `6003/6003_sdk/et6003-sdk/DFP/Test/FunctionalTest/can_ft.c`、`3101/et3101-sdk/DFP/Test/FunctionalTest/can_ft.c`，CAN_FT_6 | 对应TSU配置及附加开关被注释，运行主体为DMU数据通信 | 只能支撑P2_001基础DMU搬运，不把6003/3101这两处称为真实TSU测试；P2_008依据单列6801代码。 |
| `6801/et6801-verification/DFP/Test/FPGATest/can_fpga_test.c`，ecc_canmsg_inject_ecc / CAN_UT_5，约778～814行 | 注入辅助函数设置SYSC单错注入位；调用被注释，实际主体为16KiB模式读写 | P1_016先保留确定模式读写；P2_006先单错单地址，明确注入作用时点后再读数据和错误源。不能复制被注释调用后直接要求纠错PASS；也不能用Force替代真实注入。 |
| `6801/et6801-verification/DFP/Test/UnitTest/test_canfd.c`，Workmode / edgefilter / DMUHandler | 模式代码注释、边沿函数空、DMU处理仅打印 | P1_019/P2_007已按ET6801寄存器构造完整PLAN；P3_003已有1/3 tq刺激及观测确认步骤，不能称这些空函数提供了历史PASS。 |

P1_018已用TS0、New/Lost及ATB区间构造内部测试；外部时间基需要真实32-bit输入。P2_013仍缺事件TTS访问格式，不是必须购置示波器。P2_010已固定RAM应答延迟矩阵，P2_011已参考原厂第4章构造Level1最小表；两者不是ET历史已经测过的Case。原厂新增参考只补方法，不改写6003/3101/6801历史覆盖结论。

本轮定向复核依据：ET6801 `mttcan_cfg.svd`的XIDAM.EIDM、CCCR.EFBI/CSR/CSA、TSU.TSN/TSL/TSP、DMUC.TTS和RX1EIO；Bosch M_TTCAN 3.3.0第2.4.2/2.4.6、3.1.8/3.1.9、3.2/3.3、3.4.1.5节核对元素格式、首匹配、XIDAM绕过、Clock Stop及计数方法。参考IP语义不能覆盖ET6801中未确认的集成映射。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| CAN_F_001 | SUPPORTED | CCCR.INIT[0]/CCE[1]/FDOE[8]；CREL/ENDN；当前配置查询存在D02 | IMPLEMENTATION_GAP | CAN_P0_001 |
| CAN_F_002 | SUPPORTED | CCCR.TEST[7]/MON[5]与TEST.LBCK[4]；必须区分内部和外部回环 | IMPLEMENTATION_GAP | CAN_P0_002、CAN_P2_005 |
| CAN_F_003 | SUPPORTED | 3个实例，GPIO复用与收发器连接尚未选定；正常模式不能直接TX/RX短接 | IMPLEMENTATION_GAP | CAN_P0_003、CAN_P2_005 |
| CAN_F_004 | SUPPORTED | Message RAM元素ID/XTD/RTR/DLC；SDK data为uint16_t[64]，每项低8-bit有效 | IMPLEMENTATION_GAP | CAN_P0_002、CAN_P0_003、CAN_P1_001 |
| CAN_F_005 | SUPPORTED | CCCR.FDOE[8]/BRSE[9]、DBTP；FD长度最大64-byte，BRS须读实际接收元数据 | IMPLEMENTATION_GAP | CAN_P1_001、CAN_P3_001 |
| CAN_F_006 | SUPPORTED | NBTP/DBTP；CRG.PLLCLK_CFG3[26:20]，FPGA实际时钟不能仅信SDK硬编码40MHz | IMPLEMENTATION_GAP | CAN_P1_012、CAN_P2_012 |
| CAN_F_007 | SUPPORTED | GFC/SIDFC、标准Filter元素；HPM/HPMS；Filter列表项数与区域预算分别验证 | IMPLEMENTATION_GAP | CAN_P1_002 |
| CAN_F_008 | SUPPORTED | XIDFC/XIDAM/扩展Filter；P1_003已补XIDAM全1/屏蔽低4位、EFT=3绕过及29-bit高位对照 | IMPLEMENTATION_GAP | CAN_P1_003 |
| CAN_F_009 | SUPPORTED | GFC.RRFS[1]/RRFE[0]；Classic RTR与FD必须分开 | IMPLEMENTATION_GAP | CAN_P1_004 |
| CAN_F_010 | SUPPORTED | RXF0C/RXF1C、RXF0S/RXF1S、RXF0A/RXF1A；深度字段7-bit，不代表128项 | IMPLEMENTATION_GAP | CAN_P1_005 |
| CAN_F_011 | SUPPORTED | RXFnC.FnOM[31]，RXFnS.RFnL[25]/FnF[24]；溢出原始状态留证后再清 | IMPLEMENTATION_GAP | CAN_P1_006 |
| CAN_F_012 | SUPPORTED | RXBC、NDAT1/NDAT2、专用Buffer索引；64项上限受RAM布局约束 | IMPLEMENTATION_GAP | CAN_P1_007 |
| CAN_F_013 | SUPPORTED | TXBC.TFQM[30]/TFQS/NDTB；TXBAR请求位；原子多项请求接口待补 | IMPLEMENTATION_GAP | CAN_P1_008 |
| CAN_F_014 | SUPPORTED | CCCR.DAR[6]、TXBRP/TXBCR/TXBTO/TXBCF；无ACK排除完成/取消竞态 | IMPLEMENTATION_GAP | CAN_P1_017 |
| CAN_F_015 | SUPPORTED | TXEFC/TXEFS/TXEFA；深度最大字段意义与空间预算一致 | IMPLEMENTATION_GAP | CAN_P1_009 |
| CAN_F_016 | SUPPORTED | CCCR.WMM[11]/UTSU[10]；WMM=1时TX Event 16-bit Timestamp位置改为Marker | IMPLEMENTATION_GAP | CAN_P1_010 |
| CAN_F_017 | SUPPORTED | IR/IE/ILS/ILE；每实例INT0/INT1独立，ECC只有一条共享向量 | IMPLEMENTATION_GAP | CAN_P1_011 |
| CAN_F_018 | SUPPORTED | TSCC.TCP[19:16]/TSS[1:0]、TSCV.TSC[15:0]、IR.TSW[16]；分频1～16 | IMPLEMENTATION_GAP | CAN_P1_013 |
| CAN_F_019 | SUPPORTED | TOCC.TOP[31:16]/TOS[2:1]/ETOC[0]、TOCV.TOC、IR.TOO[18] | IMPLEMENTATION_GAP | CAN_P1_014 |
| CAN_F_020 | SUPPORTED | CCCR.UTSU[10]、TSCFG/TSS1/TSS2/TS0/ATB；使用TS0避免推测缺失槽地址，外部总线接入仍待映射 | IMPLEMENTATION_GAP | CAN_P1_018、CAN_P2_008、CAN_P2_013 |
| CAN_F_021 | SUPPORTED | CCCR.CSR[4]/CSA[3]/INIT[0]；与MISC的CLKSTOP_REQ/ACK关系需区别 | IMPLEMENTATION_GAP | CAN_P1_015 |
| CAN_F_022 | SUPPORTED | 驱动CANx-0x4000、FPGA UT5测试16KiB；地址范围是驱动依据，不等于已经硅证全容量 | IMPLEMENTATION_GAP | CAN_P1_016 |
| CAN_F_023 | SUPPORTED | CAN0/1/2及其RAM；UT6标注共享但当前没有独立证据证明物理别名关系 | IMPLEMENTATION_GAP | CAN_P2_004 |
| CAN_F_024 | SUPPORTED | DMU虚拟TX+0x200、RX0+0x280、RX1+0x300；DMU_DMA_CFG.RX_SEL[5:4] | IMPLEMENTATION_GAP | CAN_P2_001、CAN_P2_008 |
| CAN_F_025 | SUPPORTED | DMU TX Event+0x380；接收选择与RX0/RX1互斥，不能同时当三个独立DMA请求 | IMPLEMENTATION_GAP | CAN_P2_002、CAN_P2_013 |
| CAN_F_026 | SUPPORTED | DMUIR bit30/27/25/19/17/5/3/2/0及DMUIE；RX0错误字段缺失不擅自套用相邻位 | IMPLEMENTATION_GAP | CAN_P2_007 |
| CAN_F_027 | SUPPORTED | MISC.ECC_INT_EN/MASK/FORCE/CLR/RAW/STATUS；Corrected bit0、Uncorrected bit1 | IMPLEMENTATION_GAP | CAN_P2_003 |
| CAN_F_029 | SUPPORTED | CCCR.MON[5]/ASM[2]；不用Loopback模拟模式行为 | IMPLEMENTATION_GAP | CAN_P1_019 |
| CAN_F_030 | SUPPORTED | DBTP.TDC、TDCR.TDCO/TDCF、PSR.TDCV；历史启用TDC通信存在，但不证明延迟极限 | IMPLEMENTATION_GAP | CAN_P1_021、CAN_P3_002 |
| CAN_F_032 | SUPPORTED | CCCR.TXP[14]；需要位级EOF/SOF观测，不是PC发送间隔 | IMPLEMENTATION_GAP | CAN_P3_004 |
| CAN_F_033 | SUPPORTED | PSR.LEC/DLEC/BO、ECR.TEC/REC、IR.PEA/PED/EW/EP/BO；首次错误锁存 | IMPLEMENTATION_GAP | CAN_P2_009 |
| CAN_F_034 | SUPPORTED | TTOCF/TTRMC/TTTMC/TTMLM/TURCF/TTOCN/TTOST/TTIR和Trigger RAM；不声明覆盖全部TT扩展 | IMPLEMENTATION_GAP | CAN_P2_011 |
| CAN_F_035 | SUPPORTED | RWD.WDC[7:0]/WDV[15:8]、IR.WDI[26]；FPGA延迟钩子未配置，不假称CPU延迟可代替 | IMPLEMENTATION_GAP | CAN_P2_010 |
| CAN_F_036 | SUPPORTED | 压力代码200万帧仅作历史意图，本计划20轮×双向32帧，不能声称同等时长或极限压力 | IMPLEMENTATION_GAP | CAN_P3_001 |
| CAN_F_037 | SUPPORTED | CCCR.NISO[15]、FDOE[8]/BRSE[9]；Peer须真实支持两种格式 | IMPLEMENTATION_GAP | CAN_P1_020 |
| CAN_F_038 | SUPPORTED | CCCR.TEST[7]、TEST.TX[6:5]/RX[7]；必须隔离收发器，非GPIO短接 | IMPLEMENTATION_GAP | CAN_P3_005 |
| CAN_F_039 | SUPPORTED | CRG.PLLCLK_CFG3 CAN源可选择AUX；S04和AUX PAD/FPGA接入未闭合，不代表当前FPGA已可执行 | IMPLEMENTATION_GAP | CAN_P2_012 |

Hardware=SUPPORTED仅表示寄存器/描述支持所述能力，不代表实际FPGA已经测通。本表37项已准入Feature；其余2项候选行为保留在公共第5节及本文件第三/四章，不提前发布公共ID。DMU RX时间戳已PLAN，TX Event附加格式仍为P2_013缺口。Platform全部未实现，没有ADAPTED。具体分析疑点不能被表格汇总覆盖。

## 第六章 Chip -> Public Case Adaptation

### 6.1 总体计划与当前环境

| 项目 | 数量 | 含义 |
|---|---:|---|
| 能力/行为目标 | 39 | 37项准入公共Feature；2项候选行为不提前发布ID |
| 测试目标 | 42 | P0=3、P1=21、P2=13、P3=5；P2_008拆出独立TX Event目标P2_013 |
| 完整格式PLAN | 37 | P0_002、P1_001已转SPEC；其余输入、6～8步流程、Observation、判据、资源已列 |
| 已实现SPEC | 2 | P0_002内部回环、P1_001帧格式/DLC矩阵，尚未HIL |
| DESIGN_GAP目标 | 3 | P2_006、P2_013、P3_003已有具体确认流程，关键语义未定；不是SKIP |
| 已设计核心可片内构造 | 24 | 含2项SPEC及22项PLAN；TSU外部节点和IRQ外部节点另需相应连接 |
| PLAN内固定CAN总线 | 7 | 原5项加取消/重发、ISO格式；仍需盒子相应静默/原始捕获/Non-ISO能力 |
| PLAN内总线加AUX输入 | 1 | P2_012；CAN盒子负责帧收发，另需合法时钟输入 |
| PLAN内专用刺激或计量 | 7 | Monitor原始位流、协议注入、RAM延迟、TTCAN定时响应、TDC延迟、Pause测量、TEST pins |
| 当前注册/执行 | 2 / 0 | 无PASS、FAIL或运行SKIP结论；参数展开13个节点不计作13条Case |

2026-09-04用户已确认：**当前FPGA CANFD0连接CAN盒子的CAN1通道**。连接文件选择can0、RX GPIO58、TX GPIO59；ET6801 SDK对应复用均为11。盒子适配器复用参考工程的ZLG接口，尚未实际打开设备确认型号/序列号、终端匹配和支持速率；不能把“已接盒子”写成这些能力全部具备。AUX输入和其他仪器连接均未确认。

CAN盒子优先满足普通帧收发，但不是仪器限制。需要位级刺激/时序的Case直接按公共0.5规划示波器、脉冲发生器或协议发生器；盒子若已具备等效能力可以复用，不为避免仪器而弱化判据。下表是能力清单，不是新增采购清单。

| Case范围 | 最小外部动作 | 当前结论 |
|---|---|---|
| P0_003 | 普通Classic发送与实际帧捕获 | 固定连接和ZLG适配代码已准备，盒子型号/终端及实际收发待验证；不需要示波器 |
| P1_012、P1_021、P3_001 | 对应速率的Classic/FD/BRS收发，连续捕获与真实发送结果 | 先查询盒子能力，不假定所有盒子都支持FD或5Mbps；不要求TDC延迟器用于基础通信 |
| P2_005 | 静默捕获，正对照确认捕获有效 | 先确认盒子是否支持listen-only；不直接要求新增分析仪 |
| P1_017、P1_019、P1_020 | 分别需无ACK尝试捕获、无ACK仍保持合法EOF的位流Peer、ISO/Non-ISO发送 | PLAN已写；普通盒子未必支持原始位流，尤其Monitor不能只看ACK错误后损坏帧的RX |
| P1_018、P2_008内部TSU/DMU部分 | 需要时只用盒子收发帧，时间戳从DUT硬件取得 | 内部TSU及DMU RX已有PLAN；TX Event格式缺口已单列P2_013，不阻挡RX开发 |
| P2_012 | CAN盒子收发，另有20MHz合法电平AUX源 | AUX路径/源未确认；方法已形成PLAN |
| P2_009、P3_002～005高级目标 | 指定位错误、受控延迟、窄脉冲或位级时间捕获/引脚激励 | 公共0.5已分别列协议/脉冲/延迟发生器和示波器端点；只有P3_003同步判据仍需设计确认，不是全部没有测试方法 |
| P2_010、P2_011 | 前者需被测FPGA RAM应答延迟钩子；后者由DUT任Time Master，Peer按参考帧定时回复 | 两项方法已PLAN；前者不是外部总线盒子功能，后者无需盒子有TTCAN协议栈但需定时能力 |

### 6.2 Case逐项适配

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| CAN_P0_001 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R0，按公共PLAN实施 |
| CAN_P0_002 | ADAPTED | 已按SPEC实现：500 kbit/s、两帧8-byte内部回环；未HIL，不冒充PASS |
| CAN_P0_003 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R2，按公共PLAN实施 |
| CAN_P1_001 | ADAPTED | 已实现6种格式×2个ID边界；每组DLC0～15及双Pattern，尚未HIL |
| CAN_P1_002 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_003 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_004 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_005 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_006 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_007 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_008 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、atomic_tx_request_driver_gap；资源R1，按公共PLAN实施 |
| CAN_P1_009 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_010 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_011 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1～R2，按公共PLAN实施 |
| CAN_P1_012 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、clock_profile_gap、board_mapping_gap；资源R2，按公共PLAN实施 |
| CAN_P1_013 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、atomic_timestamp_snapshot_gap；资源R1，按公共PLAN实施 |
| CAN_P1_014 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_015 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R1，按公共PLAN实施 |
| CAN_P1_016 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、message_ram_mapping_gap；资源R1，按公共PLAN实施 |
| CAN_P1_017 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P1_018 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R1～R3；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P1_019 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P1_020 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R2～R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P1_021 | IMPLEMENTATION_GAP | 已有基础PLAN；TDC时序Profile及CAN盒子FD/BRS能力映射待补，不要求高级延迟设备 |
| CAN_P2_001 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、dma_endpoint_mapping_gap；资源R1，按公共PLAN实施 |
| CAN_P2_002 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、dma_endpoint_mapping_gap；资源R1，按公共PLAN实施 |
| CAN_P2_003 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、misc_mapping_gap；资源R1，按公共PLAN实施 |
| CAN_P2_004 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、message_ram_mapping_gap；资源R1，按公共PLAN实施 |
| CAN_P2_005 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap、board_mapping_gap、observer_mapping_gap；资源R2，按公共PLAN实施 |
| CAN_P2_006 | NEEDS_VERIFICATION | 有注入位但注入作用于哪次RAM写/读、影响哪实例及单次/持续语义未闭合；ECC Force不是替代。 |
| CAN_P2_007 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R1；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P2_008 | IMPLEMENTATION_GAP | RX0/RX1接收TSU附加已PLAN；DMA前不读TS0，完成后比较TS0及独立ATB区间；RX1满payload覆盖错误单列负向参数。 |
| CAN_P2_009 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P2_010 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R3；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P2_011 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P2_012 | IMPLEMENTATION_GAP | 已有PLAN；AUX源/分频Driver、PAD/电平/FPGA路径和外部源映射待补；未接线不阻止保留历史需求 |
| CAN_P2_013 | NEEDS_VERIFICATION | 原P2_008的TX Event附加部分独立保留；TTS有效字数、timestamp位置及结束地址尚缺准确格式，见公共5.2。 |
| CAN_P3_001 | IMPLEMENTATION_GAP | 未开发；case_implementation_gap；资源R2，按公共PLAN实施 |
| CAN_P3_002 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P3_003 | NEEDS_VERIFICATION | 已设计脉冲发生器/AWG加双通道示波器，1/3 tq×过滤开关四节点；仍须确认TEST采样点与硬同步的唯一对应，仪器目标预算0.1 tq，见公共5.3。 |
| CAN_P3_004 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |
| CAN_P3_005 | IMPLEMENTATION_GAP | 完整方法见公共PLAN及本文件3.4；资源R4；尚需Driver/Mapping/台架能力适配，未执行 |

### 6.3 开发接入状态与下一阶段顺序

2026-09-04开发接入：CAN盒子Adapter与`tools/runner/can_box.py`已加入当前仓库，使用ZLG原生SDK接口，CAN1对应通道索引1。21项专项无硬件回归及总软件门禁通过（1101 PASS、16 SKIP）；证据：`artifacts/runs/20260904_can_development/stages/can_box_cli_gate.log`。这些是工具软件测试，CAN正式Case尚未注册，未运行CAN HIL。

本轮用上文指纹对应的最新整片SVD和现有生成器v11重新生成候选，仅更新正式`ip/can.yaml`，没有修改其他IP或生成器。旧文件中的CAN基址属于旧SVD，现已与1.2一致。共享ECC向量仍仅在SVD的CAN2节点列出，不能据此断言只有CAN2具备ECC。当前通用生成器只能导出CAN的实例、基址及中断；Feature/Option等语义仍为空，开发必须补齐有证据的映射，不能把空集合当作硬件不支持。候选/Audit/Quality：`artifacts/runs/20260904_can_development/stages/capability/`。

用户确认的FPGA连接为CANFD0 RX=GPIO58、TX=GPIO59，复用均为11，外部CAN盒子CAN1；已写入公共连接YAML，54项连接与Bench专项测试通过，GPIO CAN信号Mapping仍待接入。软件Handle遵循当前Capability的`can0`，不因PAD名CANFD0另外创建同一硬件的重复实例。

1. 先完成S01/S02/S03/S04及D01～D04核对，补全时钟、实例、RAM、DMU/TSU的芯片事实；这不是要求先做硬件全量回归。
2. 原14项已有11项完整PLAN；继续只针对P2_006注入作用时点、P2_013事件TTS格式、P3_003同步观察的三个具体确认流程收口，不重复扫描已审源码或伪造PLAN。
3. Filter重叠/XIDAM、Classic保留DLC及外回环+IRQ已补；继续处理最大RAM布局、跨节点仲裁、只读字段保护和时钟停振/唤醒剩余设计，不把仅列Feature视作完整覆盖。
4. 确定固定CAN连接和Observer实际能力。Case只读取当前active环境handle/GPIO；独立GPIO、CRG、SYSCTRL、DMA各负责自身配置。
5. 用户审核设计后再开发Driver修复、CAN Wrap/Service/PC Driver/Case；先修错误硬件映射，不能让Case绕开问题。开发任务另编译Task Context，任何跨IP改动先按R002取得范围授权。
6. 文档批量补齐后运行现有专项门禁；编码完成后再做统一软件门禁，最后按用户指定范围HIL。软件PASS不能替代CAN实际总线PASS。

基础Wrap补充（2026-09-04 23:01 CST）：新增独立CAN Wrap，逻辑实例0/1/2映射SDK CAN0/1/2。NBTP/DBTP各字段Mask推导实际计数上限，公开参数为正整数而非寄存器编码。`CREL`通过底部测试扩展`CAN_testGetRevision`读取，`ENDN`使用已有Driver。Native Harness编译完整真实CAN Driver和新Wrap，覆盖三实例身份/INIT、时序编码与读回、非法参数无副作用。寄存器桩不验证总线、真实INIT应答或CRG复位；目前没有CAN HIL结果。

GPIO依赖同步：公共GPIO功能新增CAN_RX/CAN_TX，ET6801映射为GPIO58_MODE_CANFD0_RX与GPIO59_MODE_CANFD0_TX（SDK均为mux11）。CAN Wrap不配置GPIO，后续PC通过独立GPIO Driver按连接文件下发；未改变GPIO命令长度。

基础命令接入（2026-09-04 23:09 CST）：CAN Service使用`0x010C`与公共0.7的6条命令。Board显式发布CAN0/1/2，Application仅新增一组静态存储及注册表项，main与公共注册算法不变。Chip工程清单加入CAN Driver、Wrap及Service。Native Harness同时编译真实Service，验证身份小端编码、实例隔离、精确请求长度、输出容量和非法Boolean不改变硬件；Formal PC Driver/Case及数据通路尚未完成。

核心选项补充（2026-09-04 23:18 CST）：在既有6条命令后追加OPTIONS_SET/GET、OPTION_LIMITS_GET，未复用旧ID。Wrap使用CAN_init设置FD/BRS/DAR/TXP/EFBI/PXHD/TDC/RWD，测试扩展`CAN_testGetInitConfig`独立读取真实配置。TDCO/TDCF上限由CMSIS Mask得127，WDC得255；非法值在任何Driver写入前拒绝。Native Harness覆盖选项读回、负语义DAR转换、真实寄存器变化可见、位时序保持以及非法值无副作用。

构建记录：配置流水线`artifacts/runs/20260904_can_development/stages/build_config.yaml`仅选择build.firmware。基础6命令版本于23:13完成ET6801_SILICON_FLASH（含FPGA_VERSION）Keil构建，0 Error、0 Warning；证据`artifacts/runs/20260904_231314_787462_can_firmware_build_only/stages/build_firmware_silicon/keil_silicon.log`。后续3命令选项扩展另行构建，不能直接沿用该构建结论。没有烧录或HIL。

本批验证补充（2026-09-04 23:27 CST）：9条基础/选项命令版本的ET6801_SILICON_FLASH配置流水线编译通过，0 Error、0 Warning，证据`artifacts/runs/20260904_232007_643938_can_firmware_build_only/stages/build_firmware_silicon/keil_silicon.log`。总软件门禁`can_service_gate_corrected.log`为1120 PASS、0 FAIL、0 SKIP（包括Native C）；新增CAN注册导致的两个静态数量检查已同步为明确的CAN表项与21 Wrap/20 Service，不修改公共注册器或降低断言。没有CAN HIL，也没有正式Case结果。

PC基础接口补充（2026-09-04 23:32 CST）：九个基础命令的Codec、不可变配置Model及CanDriver已实现。20项专项软件测试验证精确Wire、独立读回、非法参数无请求、Deadline、GPIO CAN信号和CRG CAN类别编码；无真实CAN收发，不能作为正式Case通过证据。

### 6.4 当前测试状态

正式Case基础批验证（2026-09-05 01:28 CST）：两条SPEC共收集13个参数节点；软件调用链回归16项通过，覆盖独立RX响应、384帧格式矩阵及末Byte损坏必须失败。总软件门禁1192 PASS、0 FAIL、0 SKIP，证据`artifacts/runs/20260904_can_development/stages/can_case_foundation_gate_verified.log`。本批仅PC/文档变化，未重新构建或烧录固件；没有CAN HIL结论。

正式Case接入（2026-09-05 01:06 CST）：P0_002已注册并与SPEC及报告绑定。CAN专属Fixture只读选择连接文件的can0（GPIO58 RX、GPIO59 TX），核对Capability实例/IRQ和Firmware Service；内部回环不执行GPIO配置。独立can_routes.py仅保存FPGA输入时钟40MHz（现有CRG Driver/硅前测试依据）及RAM头8-byte、标准Filter4-byte、扩展Filter8-byte、Event8-byte几何。Silicon的时钟D04尚未解决，映射缺失按集成错误处理，不标SKIP。Case直接建立CRG/资源池复位基线，发送文档PATTERN_A/B并比较全部元数据和字节；三项软件流程测试覆盖独立RX Golden、第二帧单Byte错误必须失败及失败后两项清理。这些不是HIL证据。

过滤器开发（2026-09-05 00:47 CST）：新增标准/扩展单槽设置与独立RAM读回、XIDAM设置/读回。SDK问题D10：CAN_addStdMsgIDFilter和CAN_addExtMsgIDFilter原检查允许index==列表长度，现改为严格小于，Release构建也在越界或空指针时直接返回。D11：SDK标准SFID1/SFID2读回掩码只含10位，现按11-bit标准ID改为0x07FF0000/0x000007FF；原写函数不使用这两个掩码，原总线过滤写入不因此被误判为已损坏。公共BUFFER目的地用独立buffer_index，时间戳/debug编码不冒充普通Buffer。新增Native Golden必须包括ID bit10、双字扩展过滤器、最大Buffer63、真实RAM变化与Wire长度；当前处于软件验证，未执行总线过滤HIL。

收发原语接入（2026-09-05 00:25 CST）：新增显式TX装载/原子请求/状态、RX读取/FIFO Ack/Buffer位图接口。标准ID移位仅在Chip Driver/Mapping内部处理，PC不传物理地址。新增问题D09：SDK旧CAN_readMsg按帧DLC读取，即使RX槽较小也会继续读邻槽；现以实际槽容量限制读取，公共RX同时保留原DLC与实际data_length。Native使用独立构造的真实宿主RAM头/数据，验证64-byte FD编码、原子TXBAR、不覆盖Pending、短槽邻接哨兵、Dedicated Buffer63及Service字节序；这是软件RAM模型，不模拟总线、ACK或IRQ。

总线控制接入（2026-09-05 00:09 CST）：追加11字段总线配置、回环和计时上限共5条命令。CAN_testGetConfig从CCCR/GFC/TSCC/TOCC独立读回，CAN_testGetLoopback从CCCR.TEST、TEST.LBCK及CCCR.MON判断有效回环；这些读取不触碰协议错误计数。SDK新增问题D08：从内部直接切外部回环原先不清CCCR.MON，现按外部回环语义清零，避免仍处于内部总线隔离。Native覆盖内部→外部→关闭和INIT/参数拒绝，不能替代外部引脚收发实测。

RAM配置接入（2026-09-04 23:52 CST）：新增RAM布局SET/GET和上限查询，全部字节偏移先检查对齐、容量和重叠。ET6801容量采用Driver/UT5的16KiB事实；Dedicated RX按SDK最大64项保留，不将不存在的数量字段伪装为可回读寄存器。

SDK新增问题D07：`CAN_msgRAMConfig`原先跳过大小为0的区域，导致旧Filter/FIFO配置残留；TX数量校验晚于其他配置写入，且拒绝合法RX-only配置。本轮改为TX数量先校验、全部区域显式更新、允许TX数量为0。Native测试验证关闭后数量清零、非法TX数量无任何寄存器变化；新增`CAN_testGetMsgRAMConfig`在测试驱动隔离区读取真实配置，Wrap不访问寄存器。该软件回归不代表总线HIL通过。

状态更新时间：2026-09-05 01:22 CST。基础命令、RAM布局、总线配置、回环、单次收发和具体ID过滤已贯通PC、Service、Wrap和Driver，共29条命令。此前过滤器批次总门禁1176 PASS、0 FAIL、0 SKIP，证据`artifacts/runs/20260904_can_development/stages/can_filter_gate.log`；配置流水线Keil构建0 Error、0 Warning，证据`artifacts/runs/20260905_004908_611574_can_firmware_build_only/stages/build_firmware_silicon/keil_silicon.log`。本批新增两条正式Case及对应SPEC/报告模板，尚未执行CAN硬件测试；此前门禁不替代本批验证。下表只统计正式Case，不把软件回归数量混入。

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | 说明 |
|---|---:|---:|---:|---:|---:|---|
| FPGA | 2 | 0 | 0 | 0 | 0 | NOT_EXECUTED；42个设计目标不作为注册Case统计 |
| Silicon | 2 | 0 | 0 | 0 | 0 | NOT_EXECUTED；时钟D04映射尚未闭合 |

### 6.5 覆盖结论

已建立19行×2份需求与8+10条历史Case记录的去向，没有因为来源芯片不同或重复ID而删掉要求；但**去向可追踪不等于设计已全部闭合**。39个PLAN覆盖基础数据/过滤/FIFO及本轮取消、TSU、模式、DMU非法访问、错误恢复、Watchdog、TTCAN、TDC/Pause/TEST等方法；剩余3个具体确认流程和6.3的补充项仍待完成。不得宣称全部Case设计完成或开始全部目标编码。参考代码没有充分断言的部分已经区分“保留测试意图”和“历史真实通过”，不再以高级测量要求阻挡已有基础通信方法。

### 6.6 文档验证记录

验证时间：2026-09-04 21:10 CST。Task Context范围检查为2个CAN文档；公共IP边界、芯片映射、PLAN Schema、Case方法和Feature一致性专项检查通过，38个PLAN被统一Checker解析。

本批统一软件门禁`tools/validate_pc.py`退出码0，1080 PASS、16 SKIP；日志为`artifacts/runs/20260904_192700_000000_can_analysis/stages/software_gate_hardware_methods.log`，不覆盖前轮日志。收尾修改仅补充本条验证记录及修正TDC第二采样点标签，最终文档另做专项复查。没有CAN硬件操作，6.4仍为NOT_EXECUTED；这些软件结果不是CAN Case通过数，也不能替代剩余3项的硬件语义确认。未改公共层或实现、未提交和推送。

### 6.7 Case复核与本轮修正

复核时间：2026-09-04 21:43 CST。逐项阅读原38个PLAN的输入、步骤、Observation及判据，并复查3个DESIGN_GAP；本轮仅修改CAN两份文档，没有开发和硬件运行。

| 复核范围 | 发现的问题与处理 |
|---|---|
| P0_001～003 | 保留配置/内回环/真实外部收发分工；只读字段保护扩展仍未完成，不以身份读取代替只读写保护测试 |
| P1_001～004 | 增补Classic DLC 9～15固定8-byte；标准/扩展两项首匹配重叠对照；XIDAM全1/局部屏蔽/绕过及29-bit高位；ANMF=1时FIDX无效，不强作等值断言 |
| P1_005～010 | FIFO/Buffer/Event/Marker方法保留；Overwrite先停止新帧再读取，避免CPU与覆盖写并发；未证实的Overwrite Lost不当成强判据 |
| P1_011～016 | IRQ增加外部回环和Normal路径；修正Clock Stop先CSA清零再INIT退出；16-bit计数窗口用monotonic保守上界排除回绕别名，原子清零读回耗时须实现前固定 |
| P1_017～021 | 复核无ACK、Monitor合法位流、ISO格式和TDC基础收发前提；仪器允许用于ACK槽/位流观测，不能等预期失败的TX成功后才开始计时 |
| P2_001～005/007 | 保留DMU真实搬运、Force与真实ECC区分、实例隔离；修正P2_005 Normal正对照须有ACK，回环阶段才让Peer静默 |
| P2_008/013 | 原混合目标拆分：RX0/RX1的TSU附加已PLAN；DMA后再读TS0、独立ATB区间校验、RX1满payload覆盖错误及恢复均写清。Event布局独立待确认，不冒充原FT5历史覆盖 |
| P2_009～012 | 保留精确错误注入、RAM握手延迟和TTCAN最小表；AUX增加入口实测；各类发生器、示波器观察点和固定夹具模式见公共0.5 |
| P3_001/002/004/005 | 连续收发不冒充极限性能；TDC/Pause/TEST明确独立波形及时间预算，仪器设定值不替代实际引脚观测 |
| P2_006、P3_003 | ECC实际注入时点仍未知；边沿过滤已明确AWG/脉冲源+示波器，不再强制配测FPGA，但采样相位与硬同步唯一关系仍需确认 |

设计结论：39 PLAN + 3 DESIGN_GAP，共42个目标；新增1个目标来自DMU原混合目标拆分，不是重复统计参数节点。剩余3项硬件语义和6.3所列覆盖扩展仍未闭合，不能宣布全部设计审核通过。公共及芯片文件的Feature/Case映射一并维护。

验证时间：2026-09-04 21:50 CST。Task Context范围、Public IP边界、Chip映射、PLAN格式、Case方法专项检查通过；另独立核对42个唯一Case目标与42条芯片适配记录完全对应，39个PLAN及3个缺口集合准确。本批`tools/validate_pc.py`退出码0；日志为`artifacts/runs/20260904_192700_000000_can_analysis/stages/software_gate_case_review.log`，未覆盖旧日志。没有硬件操作；软件门禁不能证明这些CAN Case已经实现或通过真机测试。实际工作树仅CAN两份文档变更，未修改规则、公共层或其他IP代码，未提交/推送。
