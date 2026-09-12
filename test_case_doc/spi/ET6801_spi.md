# ET6801 SPI Chip Analysis & Adaptation Contract

更新时间：2026-09-04 18:50 CST

范围：ET6801 SPI0～SPI3，FPGA/Silicon。12个Case已进入代码及SPEC；当前FPGA正式回归11 PASS、1 SKIP，参数执行116 PASS、36 SKIP、0 FAIL。实测仅SPI0/SPI1，不推广为四实例或硅后通过。另5个外部设备目标尚未实现/执行，不计本轮SKIP。公共Feature和Case以[spi.md](spi.md)为准；完整结果见6.5，QSPI不混入本IP。

# 第一章 IP分析与Source Coverage

## 1.1 工作原理与应用

四个SPI实例均可配置Controller/Target。Controller用APB输入时钟分频产生SCLK，CS选择外部Target；TX FIFO数据经移位输出，输入数据进入RX FIFO。CPU、IRQ、DMA只改变填充/读取方式，不替代串行传输。Target必须有外部SCLK/CS；片内SRL回环不证明PAD或接线。

应用为传感器、NOR Flash、ADC/DAC、显示器及两实例互联。首轮必须保留单实例MOSI-MISO真实回接和双实例四线收发；波形、协议、高阻等独立观测按其真实资源规划，不把它们缩成内部回环。

## 1.2 可复现资料定位

资料定位依据为`project-governance/ip-analysis-sources.yaml`的roots1。以下根均已定向搜索SPI，未全扫SDK或SVN：
| 代号 | 根路径，相对SDK_GIT | 搜索状态 | 读取范围 |
|---|---|---|---|
| SDK_GIT | D:/lihuan/vibe_code/code/SDK/git | FOUND | 本机根；云盘roots0不作为不可访问核心资料重复统计。 |
| V6801 | 6801/et6801-verification | FOUND | Tools/RegGen/SPI SVD、DFP/Drivers、Test/UnitTest、FunctionalTest、FPGATest、SmokeTest、StressTest、ChipSieveTest和TestLog。 |
| V6003 | 6003/et6003-verification | FOUND | SPI拆分SVD、ET6x_Driver、UnitTest与SmokeTest；无对应Functional/FPGA SPI文件不补造。 |
| S6003 | 6003/6003_sdk/et6003-sdk | FOUND | SPI SVD、ET6x_Driver、Unit/Functional/Smoke、StressTest和ChipSieveTest。 |
| V3101 | 3101/et3101-verification | FOUND | SPI SVD、ET3x_Driver、Unit/Smoke；不误用同名ET6x路径。 |
| S3101 | 3101/et3101-sdk | FOUND | SPI SVD、ET6x_Driver、Unit/Functional/Smoke、StressTest。 |
| REQ6003 | test_case/6003/spi.json | FOUND | 10条Test Point和16条Case；编号重复，以数组序号加名称定位。 |
| REQ3101 | test_case/3101/spi.json | FOUND | 10条Test Point和16条Case。 |
| REQ6801 | test_case/6801下SPI定向查询 | NO_MATCH | 未找到专属SPI需求，不否定硬件功能或其他适用需求。 |
| ATP | 当前仓库 | FOUND | firmware/chips/et6801/sdk/{CMSIS/Device/Include/et6801.h,ET6x_Driver/Inc/et6x_spi.h,ET6x_Driver/Src/et6x_spi.c}；SPI Capability及旧SPI文档。 |

当前SPI配置/IRQ Wrap、25条原子命令Service和PC Driver、应用注册、12个Formal Case及PC引脚调用已完成。GPIO独立Service/Wrap负责Pinmux，连接选择保存在硬件连接YAML。第24号FIFO_LIMITS_GET是新增只读查询，0～23号布局不变。完整Capability语义仍待补，基础spi.yaml不等于完整芯片能力，也不能据缺字段跳过测试。

证据路径：
- 主SVD：V6801/`Tools/RegGen/ET6801.svd`；单IP：`Tools/RegGen/svd/SPI_DWC_ssi.svd`。
- Driver：V6801/`DFP/Drivers/ET6x_Driver/{Inc,Src}/et6x_spi.*`，与ATP内同名关键函数复核。
- 公共历史文件以对应根下`DFP/Test/`为前缀：`UnitTest/test_spi.c`、`SmokeTest/test_spi_device.c`、`SmokeTest/test_spi_device_csgpio.c`；差异入口见第四章。
- V6801/`TestLog/spi_ut.log`属于历史辅助证据；记录、源码调用和有效断言分开，本文不据其宣称当前PASS。

| 证据 | SHA256 |
|---|---|
| V6801整片SVD | 49b2de29bd7a0a4a5fbdefc6e36d75cd6da53a46f5504f860dee53be9079cce4 |
| V6801单SPI SVD | fcfed495daf582f999313f05f80bb5f71e06f1b7e65cc1da00a5b705186c9b65 |
| V6801 SPI Driver C | ab6c9edd8cfc1b576063ed1a01882e54bd699e547174fd2cd19e553b0024778e |
| REQ6003 | 88476ff4424c27e65fa80f4c2112f2b170bc99c093301cd03644c3aeb21ae6af |
| REQ3101 | 24f7ca4cd2d8e3edb34bf887dd685363d23b23553a7adfbc936ae546c07e0802 |

## 1.3 关键Claim

| Claim | 状态 | 可证明事实与边界 |
|---|---|---|
| 4个可配置双角色实例 | VERIFIED | 整片SVD的SPI0～SPI3及各CTRLR0.SSI_IS_MST；每实例独立IRQ、CRG Reset和TX/RX DMA请求。 |
| Motorola四模式、4～16bit配置 | VERIFIED | CTRLR0.DFS/SCPH/SCPOL及Driver合法范围；不推广到TI/Microwire的全部模式组合。 |
| FIFO容量32 | VERIFIED / FPGA实测 | NOT_RETAINED |
| 多CS | NOT_APPLICABLE | ET6801 SER只有bit0有效；保留单CS选择/窗口测试，不照搬历史CS1/CS2。 |
| 25MHz或50MHz一定可达 | UNKNOWN | 25MHz是参考需求/历史配置，50MHz是Driver校验上限；需当前APB3时钟和有效偶数分频。二者都不是当前FPGA已测上限。 |
| RX延迟全部0～255有效 | UNKNOWN | RSD为8bit；SVD说明超过内部移位深度时实际延迟退回0，但未提供该深度。 |
| TI/Microwire存在 | VERIFIED | FRF、CFS、MWCR提供硬件配置；完整引脚时序Oracle仍不足，不能直接宣布协议Case完成。 |
| Collision触发 | VERIFIED / 集成路由UNKNOWN | SR.DCOL描述Controller传输时ss_in_n被有效选中；ET6801该输入是否对外可控仍缺映射证据。 |

# 第二章 Driver分析

基本启停、四模式、帧宽、传输方向、回环、FIFO、IRQ、DMA均有API，但不能直接包一层就使用。下表保留开发前发现的问题与处理要求；实际修复进度见2.1节。

| ID | 源码锚点 | 问题与影响 | 后续处理 |
|---|---|---|---|
| SPI_DRV_001 | SPI_getTansferStartFIFOLevel | `REG & MASK >> POS`实际先移位MASK，读到低位TFT而非TXFTHR。 | 修为先掩码后移位；用TFT与TXFTHR不同值证明。 |
| SPI_DRV_002 | SPI_configFrameNum / SPI_setConfig | 前者num-1且num=0下溢；后者rxDataNum直接写NDF，同名“数量”语义不一致；uint16不能表达65536帧。 | 明确原API编码，公共frame_count统一真实帧数；必要时补uint32测试接口，1/65536边界必须覆盖。 |
| SPI_DRV_003 | IS_SPI_BAUDRATE / SPI_setBaudRate / SPI_setConfig | 校验未排除0；整数除法可能给出奇数分频，bit0不存储会向下取偶数造成超速；超范围时静默保留旧值。 | 零值拒绝；按要求选择合法偶数分频、返回实际频率，非法范围明确返回错误。 |
| SPI_DRV_004 | IS_SPI_FIFO_THRESHOLD | 旧校验依赖FIFO容量，而TFT/RFT/TXFTHR/DMATDL/DMARDL为4bit。 | 已独立按SDK字段掩码限制0～15，容量32不放宽阈值；新增FIFO_LIMITS_GET向PC发布五类阈值范围。 |
| SPI_DRV_005 | SPI_setDMATransmitDataLevel / SPI_setDMARecevieDataLevel | 仅求值IS_SPI_FIFO_THRESHOLD，没有assert_param也未校验实例。 | 使用原SDK风格补齐校验；分开TX/RX DMA请求开关。 |
| SPI_DRV_006 | SPI_Config.slaveOutputEn / SPI_setConfig | 值直接左移到SLV_OE，1实际上禁用输出；成员名易诱导ENABLE=允许输出。 | 芯片映射显式反向，公开target_output_enabled不沿用误导命名。 |
| SPI_DRV_007 | SPI_setCSLow/High、setcharLength、setConfig | CS函数更改SOFT_MODE而非任意拉低/拉高；多函数Disable/Enable导致FIFO清空。 | 配置全在装数据前完成；补真正SER选中/释放的直接接口，不能写完FIFO再调用重配函数。 |
| SPI_DRV_008 | SPI_writeDataNonBlocking | 函数名非阻塞，实际写后无限轮询SR的0x05/0x04；读取SR同时可能消耗TXE/DCOL读清状态。 | 必须修复或补无等待单次写接口；普通读写与错误刺激动作区分。 |
| SPI_DRV_009 | BlockingFIFO / NonFIFO / pollingFIFOTransaction | 多处无限等FIFO或BUSY；停钟会卡住控制通信。 | 不从Service调用这些无界函数；PC期限内组合单次动作。 |
| SPI_DRV_010 | SPI_getInterruptStatus / SPI_isBusy | 前者只有ISR无RISR/IMR；后者读整个SR，可能读清TXE/DCOL。 | 普通快照与显式错误读清分开；需要错误首次值时禁止提前读SR。 |
| SPI_DRV_011 | SPI_clearInterruptStatus | 已正确区分TXE/RXF电平消除与TXO/RXO/RXU/MSTICR读清。 | 复用现有正确实现；不能改成统一W1C。 |
| SPI_DRV_012 | SPI_setConfig / SPI_INTERRUPT_ALL | 0x3F是在IMR屏蔽所有源，不是清除所有IRQ；已有SPI_INTERRUPT_ALL可用。 | 使用已有SDK宏并解释作用，不新增重复Magic Number。 |
| SPI_DRV_013 | SPI_Config / MWCR | 未暴露FRF、CFS、Microwire模式/方向/握手，SER控制及完整直接快照也不足。 | 先补分析依据，再按测试Driver扩展区域约束补接口；Wrap不写寄存器。 |

24/32-bit helper是多帧打包，不证明SPI硬件有24/32bit单帧。帧外高位忽略及4/16bit测试由公共frame_bits覆盖，不能把SDK helper当新硬件Feature。历史chipSel成员已不在当前Config内，按SER实际集成适配。

## 2.1 本轮实现进度

2026-09-04 15:35 CST：加入SPI四实例的Application静态注册与工程源码清单，GPIO使用独立Service/Wrap提供逻辑复用配置。用户已确认SPI0/SPI1四线相连；PC通过连接YAML选择handle/GPIO，不在SPI Service中配置GPIO。尚未执行本次硬件测试。

2026-09-04 11:54 CST：以下为源码变化，不表示芯片实测通过。

| 项目 | 当前实现与保留边界 |
|---|---|
| CRG接入 | 公共CRG类别新增SPI=9；SPI0～3按生成CMSIS的GTEN1/SRST1 bit14～17映射。未使用旧SDK SPIM/SPIS选择值；尚未验证实机复位。 |
| SPI_DRV_001/004/005 | 修正TXFTHR getter的括号，FIFO阈值合法域改为0～15，补DMA水位函数的实例与参数断言。 |
| SPI_DRV_002 | 旧`SPI_configFrameNum`拒绝0；旧`SPI_Config.rxDataNum`仍保持NDF原始编码，避免静默改变历史API。新增`SPI_testSetFrameCount(uint32_t)`接受真实1～65536帧，启用状态返回BUSY，不自动清FIFO。 |
| SPI_DRV_003 | 原SDK频率设置改为向上量化偶数分频，不超过请求频率；非法/不可表达请求不修改硬件。因旧API为void，Formal链使用返回DRV_Status的`SPI_testSetDivider`明确报告非法参数，不依赖旧API的静默返回。 |
| SPI_DRV_007/008 | 新增SER选择接口，不改变SSIENR；修正`SPI_writeDataNonBlocking`，一次写入后立即返回，不轮询SR。旧Blocking接口保留，但不得进入Service。 |
| 无损观测 | `SPI_testGetSnapshot`读取配置、FIFO、IRQ、DMA请求，不读SR/DR/ICR；`SPI_testReadStatus`明确执行一次SR读取并消费TXE/DCOL。普通读写用FIFO Level判断，不偷读SR。 |
| 自然错误刺激 | 正常TryRead/TryWrite返回0或1帧；显式FIFOOnce接口绕过满空保护，供TXO/RXU刺激，不伪造错误状态。 |
| DMA方向 | `SPI_testConfigureDMA`独立设置TX/RX开关和水位，不调用DMA Driver，不配置DMA通道。 |
| 基础Wrap | 已增加公共`et_spi_wrap.h/.c`：启停、FIFO复位、精确分频、真实帧数、CS选择、正常/错误刺激单帧访问及独立DMA请求。实例只由Chip Config映射，Wrap不操作寄存器、不调用其他IP。 |
| 尚待完成 | 完整配置/快照/IRQ Wrap、Service/IRQ事件、PC Driver/Case、Capability和接线映射。第5/6章适配状态仍保持缺口，不升级为ADAPTED。 |

软件回归入口：`pc/et_test_platform/framework_validation/unit/firmware_contract/test_spi_driver_native.py`，编译真实SPI Driver，复用生成头位定义，验证非法参数无写入、帧数/分频边界、FIFO查询不清错误和非阻塞写无等待。寄存器桩不证明波形、真实FIFO或IRQ投递。

本批验证：ArmClang对真实SDK和SPI Wrap的语法检查通过；同一回归夹具通过WSL GCC编译真实Driver与Wrap并执行全部断言，退出码0。包含四实例映射、公共返回值、非法参数、BUSY以及不消耗SR错误的检查。原生夹具位于。Windows PATH没有本机C编译器，pytest会跳过该原生测试；WSL执行证据不能计入pytest通过数量。尚未进行完整固件链接、下载或HIL。

2026-09-04 12:02 CST：本批统一软件门禁`tools/validate_pc.py`通过，977 PASS、15 SKIP、0 FAIL；包含规则路由、范围、文档、C格式/注释、软件单测、既有Formal Case收集和报告导出检查。初次检查发现测试扩展缺少规范标记/编译开关，已按既有SDK隔离约定修正，未放宽Checker。关闭测试扩展的普通SDK语法检查及开启扩展的SDK/Wrap检查均通过。以上数量是软件门禁测试，不是SPI的17项硬件Case结果。

2026-09-04 12:54 CST：完成SPI原子命令和PC Driver这一逻辑批次。以下更新接替上表“尚待完成”中的部分事项，不回改历史验证结论。

| 项目 | 本批完成内容 | 验证边界 |
|---|---|---|
| Chip Driver / Wrap | 完整停机配置及读回、FIFO阈值/无损快照、独立错误读取、IRQ源屏蔽/清除/路由、DMA端点；公共Wrap不读写寄存器。 | 真实SDK、Wrap、Service通过ArmClang语法检查及原生寄存器桩回归；不证明总线时序。 |
| SPI Service | `0x010B`、25条固定布局命令；每条仅执行本IP原子动作。回调只锁存事实并屏蔽有效源，不排空FIFO，不执行Case断言。 | 固定向量、长度、实例及IRQ验证通过；薄工厂与Application/工程注册已完成。 |
| IRQ故障边界 | 注册失败时只读取本回调的Manager所有权，区分未分配与部分保留；不写Manager内部状态。没有分配的失败不留下虚假BUSY，部分解绑失败保留重试所有权。 | 原生夹具覆盖注册前失败、部分注册后回滚成功/失败、解绑重试和事件计数溢出；不模拟NVIC硬件。 |
| PC Driver / Codec | 25条直接命令、严格响应长度、正常/强制FIFO访问分离；多次读取共享Deadline，无跨IP初始化。 | NOT_RETAINED |
| 尚未完成 | Capability语义/执行映射、GPIO接线依赖、Application/Keil注册、17项目标对应的正式Case及报告模板。 | Formal Case仍为0，SPI HIL仍未执行；不能把本批软件测试数量填入第七章硬件PASS。 |

证据目录：。`armclang_final.log`记录目标工具链语法检查；`native_irq_failure.log`记录含IRQ故障注入的真实SDK/Wrap/Service原生执行；`software_gate_review.log`为本批最终软件门禁日志。Windows本机缺少原生C编译器，该pytest项目保持环境SKIP；WSL执行单独留证，不改写pytest计数。

TI/Microwire仍保留第5/6章的依据缺口：寄存器桩只能验证当前Driver编码写回，不能证明目标FRF枚举及MWMOD极性的硬件正确性，也不能证明协议时序。目标SVD没有给出的枚举含义不得据此升级为已验证能力；P2_002不能凭编码读回宣布完成。

2026-09-04 13:00 CST：与P1_005逐步对照后，取消`IRQ_CAPTURE_START`隐式清除锁存源及修改源屏蔽的行为。它只重置软件事件并绑定；PC负责Mask/Clear、制造刺激、保存Raw/Status，再开放投递。否则TXO/RXU/RXO会在投递前被清掉，Case无法按设计执行。新增原生回归检查启动不读ICR、不改变IMR，以及绑定期间立即进入ISR后不重新打开已被ISR屏蔽的源。公共IRQ Manager未修改。最新证据入口为`native_capture_final.log`、`armclang_capture_final.log`及`software_gate_closeout.log`，均位于上述stages目录；前述日志保留为阶段证据。

2026-09-04 13:10 CST：最终统一软件门禁通过，**1033 PASS、15 SKIP、0 FAIL**，资源控制任务`20260904_130643_460602eb`，退出码0。包含最终IRQ原子性修正；上述原生夹具及ArmClang检查也通过。此处仅是软件质量结论：SPI正式Case仍未落地、完整工程尚未链接、本轮未烧录或运行硬件，不能填写SPI硬件PASS数量。没有修改冻结Framework、Runner、IRQ Manager或其他未授权IP。

# 第三章 寄存器与Observation映射

以下位置取自ET6801单IP SVD。没有把其他芯片手册当作被测硬件依据。

| 公共语义 | ET6801寄存器/位 | 关键事实 |
|---|---|---|
| CONFIG.FRAME_BITS | CTRLR0.DFS[3:0] | 编码为位数减一，当前4～16；接收右对齐，高位补0。 |
| CONFIG.FRAME_FORMAT | CTRLR0.FRF[7:6] | Motorola/TI/Microwire；QSPI扩展描述不能推导此IP支持Dual/Quad。 |
| CONFIG.CLOCK_MODE | CTRLR0.SCPH[8]/SCPOL[9] | MODE0～3映射00/01/10/11，Motorola有效。 |
| CONFIG.TRANSFER_MODE | CTRLR0.TMOD[11:10] | TX_RX=0，TX_ONLY=1，RX_ONLY=2，EEPROM_READ=3。 |
| CONFIG.TARGET_OUTPUT_ENABLED | CTRLR0.SLV_OE[12] | 0允许Target输出、1高阻；Controller无效。 |
| CONFIG.LOOPBACK | CTRLR0.SRL[13] | Target回环仍需外部SCLK/CS。 |
| CONFIG.CS_POLICY | CTRLR0.SSTE[14]、spi_soft_mode[26] | SSTE只在Motorola SCPH=0有效；SOFT_MODE表示批间保持。 |
| CONFIG.ROLE | CTRLR0.SSI_IS_MST[31] | 1 Controller、0 Target。 |
| CONFIG.FRAME_COUNT | CTRLR1.NDF[15:0] | 数量=NDF+1，1～65536；仅Controller RX_ONLY/EEPROM_READ使用，Target不使用。 |
| CONFIG.ENABLE | SSIENR.SSIC_EN[0] | Disable停止操作并清TX/RX FIFO；不要装数据后重配。 |
| CS_SELECTED | SER[0] | 仅一个有效选择位；选择在启动传输时生效，不等价软件强制引脚电平。 |
| CONFIG.DIVIDER | BAUDR.SCKDV[15:1] | 整个BAUDR值为偶数分频2～65534；0停止SCLK。 |
| Microwire配置 | CTRLR0.CFS[19:16]、MWCR.MWMOD[0]/MDD[1]/MHS[2] | 顺序模式一个控制字对应整批，非顺序每个数据字前一个控制字；MDD=0接收/1发送；MHS只对Controller有效，末位后等ready才释放BUSY。 |
| FIFO.TX_THRESHOLD/START_THRESHOLD | TXFTLR.TFT[3:0]/TXFTHR[19:16] | TXE条件Level≤TFT；Controller启动条件Level>TXFTHR，不能只读回判生效。 |
| FIFO.RX_THRESHOLD | RXFTLR.RFT[3:0] | RXF条件Level≥RFT+1。 |
| FIFO.TX_LEVEL/RX_LEVEL | TXFLR.TXTFL/RXFLR.RXTFL | 当前占用帧数；被动调试读DR会改变RX Level，不能开自动DR刷新。 |
| STATUS.BUSY/TX_NOT_FULL/TX_EMPTY/RX_NOT_EMPTY/RX_FULL | SR[0]/[1]/[2]/[3]/[4] | 正常状态；一次SR读取也会影响下面的读清位。 |
| STATUS.TARGET_TX_ERROR | SR.TXE[5] | Target在TX无有效数据时开始发送，可能重发上次数据；读SR清除此状态。不是TX Empty IRQ。 |
| STATUS.CONTROLLER_COLLISION | SR.DCOL[6] | Controller传输时被其他Controller选中；读SR清状态，IRQ另读MSTICR清。 |
| IRQ.MASK/STATUS/RAW | IMR/ISR/RISR[5:0] | 0TXE、1TXO、2RXU、3RXO、4RXF、5MST；IMR位1=Unmask，不把名字Mask理解成相反极性。 |
| IRQ清除 | TXEICR、RXOICR、RXUICR、MSTICR | 读相应寄存器清锁存错误；TXEICR名称不能误认为清TX Empty电平。 |
| DMA请求 | DMACR.RDMAE[0]/TDMAE[1]，DMATDLR/DMARDLR[3:0] | TX Level≤T；RX Level≥R+1。尾包小于RX阈值会残留，普通传输RX阈值取0，边界测试单独控制帧数。 |
| CONFIG.RX_SAMPLE_DELAY | RX_SAMPLE_DELAY.RSD[7:0] | 单位输入时钟周期；超内部移位深度退回无延迟，深度UNKNOWN。 |
| TRANSFER.RX_DATA | DR[0] | 读出FIFO一帧；空读是错误刺激，普通读不能这样做。 |
| IRQ_EVENT | 固件ISR锁存结构 | 软件事实，记录首次ISR有效Source及计数，不伪装寄存器。 |
| DMA目的数据 | DMA通道完成/错误位及资源内存 | 引用DMA稳定契约，SPI Service不读取DMA寄存器。 |

Controller RX_ONLY必须写一帧启动字，不能仅配置NDF就等数据。EEPROM_READ必须先把命令段准备完整，再启动CS；Target对照端预装命令阶段占位帧及读阶段数据，避免把命令阶段消费的数据误当返回首帧。

# 第四章 历史Source Item逐项处置

## 4.1 两份需求的全量语义

REQ6003/REQ3101共有10类TP、各16条Case。下面“#n”是各JSON Case数组的1-based序号，不依赖重复旧ID。

| Source Item | 测试目的、原刺激及判据 | ET6801适用与处置 | 公共Case |
|---|---|---|---|
| TP001 | 各模块可用，旧模块数量不可写死。 | MAPPED；4实例来自目标SVD；同Case可传各handle，默认一个代表不等于全实例已测。 | P0_001、P1_002 |
| TP002；#14/#15 | 两方向速率，历史配置25MHz并比数据。 | SPLIT；目标可达分频的数据完整性与外部频率分别证明；25MHz不可达应给实际时钟依据。 | P1_001/P1_002、P1_006；极限P2_003待分析 |
| TP003 | CPOL/CPHA四组合。 | MAPPED；CTRLR0的两位存在；内部、外部及独立波形证据不混为一个。 | P0_002、P1_001、P1_002、P1_006 |
| TP004 | Controller/Target角色。 | MAPPED；SSI_IS_MST可配置，交换角色。 | P1_002 |
| TP005；#7/#8 | 硬件/软件CS与选择窗口。 | SPLIT；单CS自动/保持/切换保留；NOR应用中的GPIO CS随应用范围一起排除；多个硬件CS分支NOT_APPLICABLE，SER只有1位。 | P1_006 |
| TP006；#10 | 8/16及4bit边界，比较有效位。 | MERGED；全部4～16bit内部矩阵含8/16与4bit，外部矩阵保留边界。 | P0_002、P1_001、P1_002 |
| TP007；#6 | TR/T/R/E2PROM收发方向。 | MAPPED；有效方向用数据相等，RX_ONLY无效TX方向不能用“数据不同”判硬件错误。 | P1_003 |
| TP008；#5/#9 | FIFO深度、20字节超过16及阈值。 | SPLIT；容量/阈值读回、自然Overflow和有效阈值边界分开；丢弃旧“最后4字节必须不相等”的弱判据。 | P1_004、P1_005、P1_008 |
| TP009；#11/#12 | TX Empty/Overflow；RX Overflow/Underflow/Full IRQ。 | MAPPED；保留5个Source，分别验证Raw、Mask、真实ISR和正确消除方式。 | P1_005 |
| TP010；#13 | DMA M2P/P2M及双向对比。 | MAPPED；目标请求存在，要求通道真实完成和两端内存，而非固定延时。 | P2_001 |
| #1 | 内部Loopback数据一致。 | MAPPED；SRL存在，不算PAD证据。 | P0_002 |
| #2 | 关闭SRL，MOSI-MISO外接并比较。 | MAPPED；R2无强制仪器，SCLK波形另测。 | P1_001 |
| #3/#4 | 阻塞/非阻塞传输，断SCLK观察卡住/不卡住。 | SPLIT；正常数据路径由双实例覆盖，无时钟/恢复独立覆盖；无限卡死是旧SDK行为，不是应继承的硬件通过条件。 | P1_002、P2_005 |
| #16 | SFUD外部NOR擦、写、读与数据比较。 | 用户范围排除（2026-09-04）：NOR应用不纳入本轮SPI功能测试；不是硬件不适用，也不宣称该需求已覆盖。 | — |

## 4.2 源码入口、有效性与保留范围

| 来源锚点 | 实际内容与问题 | 处置/去向 |
|---|---|---|
| V6801/V6003/V3101 UnitTest/test_spi.c::SPI_UT_1～11 | 1阻塞、2非阻塞、3容量、4方向、5/6CS、7阈值、8位宽、9/10IRQ、11DMA；历史配置含旧chipSel，函数存在不代表当前可编译。 | MERGED到上表相同刺激/Oracle；UT1/2→P1_002/P2_005，UT3/7→P1_004/5/8，UT4→P1_003，UT5/6→P1_006，UT8→P0_002/P1_002，UT9/10→P1_005，UT11→P2_001。 |
| S6003/S3101 UnitTest/test_spi.c::SPI_UT_0～11 | 额外UT0/1涉及内部/外部回环；部分Loopback设置与注释不一致。 | SPLIT；按实际SRL与线路重建P0_002/P1_001，不能仅看名称；其余按上行目的归并。 |
| V6801 FunctionalTest/spi_ft.c::SPI_FT_1/2/3/4/5 | 1外接回环；2SPI0→SPI3；3DMA；4阈值8后写9及17帧溢出；5Mode1/25MHz外接回环。 | MAPPED到P1_001、P1_002、P2_001、P1_005、P1_001/P1_006。历史频率配置不是当前实测值。 |
| V6801 FPGATest/spi_fpga_test.c::SPI_1～11及spi_pinmux | SPI0/SPI3板级四线，基础/FIFO/方向/CS/阈值/位宽/IRQ/DMA，显式workMode；SPI_6入口被注释。 | MERGED P1_002、P1_003、P1_004、P1_005、P1_006、P2_001；历史Pinmux与Smoke不同，当前板卡必须重核，不直接复制。 |
| V6801 FPGATest/spi_fpga_test.c::SPI_12/13 | 12设TXFTHR=6，发12帧后再发3帧，以接收内容不同推断未启动；13交换SPI0/SPI3角色。 | MAPPED P1_008保留外部Target独立观测，改为阈值前RX_LEVEL=0、越界后完整数据；P1_002保留角色互换。 |
| V6801 SmokeTest/spi_smoke_test.c::SPI_TestCase1/2 | 前者重复初始化且回环/对端读混杂；后者32字节DMA。 | MAPPED有效数据与DMA意图到P0_002/P1_002/P2_001，错误调用顺序不复用。 |
| 五个根SmokeTest/test_spi_device*.c::SPI_TestDevice/SPI_WriteData | ID、状态、擦除、编程、读回；GPIO CS变体；按块覆盖多页，存在整片擦除与无限等WIP。 | 用户范围排除：仅保留NOR应用来源，不再映射当前SPI Case。 |
| S6003/S3101 FunctionalTest/spi_ft.c及SmokeTest/spi_smoke_test.c::Norflash_test/sfud_demo | 外部NOR 1024字节递增Pattern擦写读；部分入口注释，函数有比较。 | 用户范围排除：原因是NOR应用不在本轮范围，不是入口注释或硬件不支持。 |
| 五个根SmokeTest/test_spi_device_csgpio.c::SPI_pressure_test | 循环器件测试；部分版本ERROR局部变量未初始化，S3101循环注释。 | 用户范围排除：NOR连续读写擦不纳入本轮SPI功能测试；不宣称历史压力已PASS。 |
| S6003 ChipSieveTest/chip_sieve.c::SPI_DMA_entry及StressTest/StressTest.c | 四通道双向32帧，主循环重复；某Target TX Mux仍写Controller请求，是参考代码缺陷。 | SPLIT P2_001功能矩阵与P3_002连续传输；端点依据ET6801，不沿用旧Mux。 |
| S3101 StressTest/CommPer_StressTest.c::SPI_DMA_entry与StressTest_multichip.c | 配置36/32帧不一致但只比32帧；25MHz，Target TX高优先级，循环调用。 | SPLIT P2_001/P3_002，保留双向DMA/跨FIFO/反复运行；统一两端帧数并核对全部数据，避免尾4帧假覆盖。 |
| S3101 StressTest/CommPer_StressTest.c::SPI_NOR_FLASH_SST26_test | 外部SST26擦写读及循环入口。 | 用户范围排除：SST26应用功能及压力不纳入本轮；不影响SPI DMA连续传输。 |
| V6801 StressTest/Integrated_StressTest.c::SPI_QSPI_entry；ChipSieveTest_config.h | 找到调用和声明，目标Test目录未找到定义，无法证明具体SPI/QSPI刺激。 | UNKNOWN实现证据；不统计为独立已覆盖Feature。SPI DMA连续目的由P3_002保留，NOR连续应用按用户范围排除，QSPI另行分析，不能据函数名推导更多覆盖。 |
| V6003/V3101 StressTest中SPI相关项 | 存在集成测试引用；没有据同名入口推定新波形/协议覆盖。 | 采用上述逐项已证明意图；未发现独立TI/Microwire、RX延迟边界或Collision有效Oracle。 |

32/36帧、Mux不一致、非阻塞函数含等待、IRQ满写时仍在排空等都是历史实现问题；需要修构造而非取消目的。数据比较、错误触发、真实IRQ投递应各自留下证据。

# 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| SPI_F_001 | SUPPORTED | SSIENR清零停止并清双FIFO；独立CRG复位。 | IMPLEMENTATION_GAP | `SPI_P0_001`, `SPI_P1_004` |
| SPI_F_002 | SUPPORTED | 四实例CTRLR0.SSI_IS_MST。 | IMPLEMENTATION_GAP | `SPI_P0_001`, `SPI_P1_002` |
| SPI_F_003 | SUPPORTED | SCPOL/SCPH仅Motorola有效。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002`, `SPI_P1_006` |
| SPI_F_004 | SUPPORTED | DFS加Driver合法域4～16bit。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_001`, `SPI_P1_002` |
| SPI_F_005 | SUPPORTED | TMOD四值；RX_ONLY写启动字，EEPROM命令段与读段分开。 | IMPLEMENTATION_GAP | `SPI_P1_003` |
| SPI_F_006 | SUPPORTED | APB3/偶数BAUDR；25MHz不是默认FPGA事实，P1_006测可达节点。 | IMPLEMENTATION_GAP | `SPI_P0_001`, `SPI_P1_001`, `SPI_P1_006`, `SPI_P2_003` |
| SPI_F_007 | SUPPORTED | SRL存在；P0_002测Controller回环，P1_002的Target回环节点由另一个实例提供SCLK/CS。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_002` |
| SPI_F_008 | SUPPORTED | SPI0/SPI1四线连接已固定；单SPI回接未配置。 | IMPLEMENTATION_GAP | `SPI_P1_001`, `SPI_P1_002`, `SPI_P2_005`, `SPI_P3_002` |
| SPI_F_009 | SUPPORTED | SSTE限SCPH=0；SOFT_MODE批间保持；SER单选择位。 | IMPLEMENTATION_GAP | `SPI_P1_006` |
| SPI_F_010 | SUPPORTED | NDF+1，仅Controller RX_ONLY/E2PROM；1～65536。 | IMPLEMENTATION_GAP | `SPI_P1_003` |
| SPI_F_011 | SUPPORTED | FPGA实测TX/RX容量32；逐帧Level、满空及清双FIFO通过。 | IMPLEMENTATION_GAP | `SPI_P1_004` |
| SPI_F_012 | SUPPORTED | TFT/RFT/TXFTHR独立4bit，0～15；getter/校验已修正，启动阈值逐值通过。 | IMPLEMENTATION_GAP | `SPI_P1_004`, `SPI_P1_005`, `SPI_P1_008` |
| SPI_F_013 | SUPPORTED | SR[0:6]；TXE/DCOL读清，快照不能提前消耗。 | IMPLEMENTATION_GAP | `SPI_P0_002`, `SPI_P1_002`, `SPI_P1_004`, `SPI_P1_007`, `SPI_P2_005` |
| SPI_F_014 | SUPPORTED | RISR/ISR/IMR五FIFO源；电平/读清不同。 | IMPLEMENTATION_GAP | `SPI_P1_005` |
| SPI_F_015 | SUPPORTED | 每SPI TX/RX请求存在，水位4bit；Mux按目标芯片发布。 | IMPLEMENTATION_GAP | `SPI_P2_001`, `SPI_P3_002` |
| SPI_F_016 | SUPPORTED | RSD8bit存在，内部有效深度与时序预算UNKNOWN。 | NEEDS_VERIFICATION | `SPI_P2_003` |
| SPI_F_017 | SUPPORTED | FRF/MWCR存在；TI同步、Microwire完整时序Oracle仍需目标资料。 | NEEDS_VERIFICATION | `SPI_P2_002` |
| SPI_F_018 | SUPPORTED | SLV_OE=1高阻；必须以弱上拉/下拉独立证据证明。 | IMPLEMENTATION_GAP | `SPI_P2_007` |
| SPI_F_019 | SUPPORTED | DCOL/MSTIR存在；ss_in_n在Controller模式的集成路由UNKNOWN。 | NEEDS_VERIFICATION | `SPI_P2_004` |

Platform栏的IMPLEMENTATION_GAP仍指完整Capability语义未发布，不表示下列已通过Case缺代码或硬件失败。Case范围内映射由SDK、LIMITS_GET及FIFO_LIMITS_GET核对；波形/协议仍有独立缺口，不把当前PASS升级为19个Feature全部闭合。

# 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| SPI_P0_001 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P0_002 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P1_001 | BENCH_GAP | Case已实现；当前四线对接不满足独立MOSI/MISO回接要求，实际运行SKIP。 |
| SPI_P1_002 | ADAPTED | SPI0/SPI1四线接线已修正；48个参数组合正式Case复测PASS，证据见6.5。 |
| SPI_P1_003 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P1_004 | ADAPTED | 容量修正32、阈值独立0～15，TX/RX容量、阈值与复位3个参数执行全部PASS。 |
| SPI_P1_005 | ADAPTED | 按32帧容量构造第33帧Overflow，五源三阈值共15个参数执行全部PASS。 |
| SPI_P1_006 | BENCH_GAP | 方法已明确；外部配测条件未就绪，本轮计划SKIP（未运行）；另有公共代码待实现，不把缺代码写成硬件原因。 |
| SPI_P1_007 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P1_008 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P2_001 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P2_002 | NEEDS_VERIFICATION | Motorola已有完整Case；TI帧同步边沿、Microwire控制段装载顺序及ready电平/采样边沿尚缺目标适用时序依据。MHS约束的是末位之后BUSY释放，不是数据开始，旧计划判断方向错误。 |
| SPI_P2_003 | NEEDS_VERIFICATION | RX延迟内部移位深度、输入建立/保持预算未定；不得用扫描中任意一个成功点证明整个Feature。 |
| SPI_P2_004 | NEEDS_VERIFICATION | 已知触发为Controller传输时ss_in_n有效；目标芯片该输入到PAD/FPGA的集成连接仍未知，不能用短接两个Controller输出来替代。 |
| SPI_P2_005 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |
| SPI_P2_007 | BENCH_GAP | 方法已明确；外部配测条件未就绪，本轮计划SKIP（未运行）；另有公共代码待实现，不把缺代码写成硬件原因。 |
| SPI_P3_002 | ADAPTED | 公共动作、GPIO/DMA映射及代码已实现，当前FPGA执行证据已取得；结果与范围见6.5。 |

## 6.1 统计与覆盖边界

- 19个Feature；17个测试目标，P0=2、P1=8、P2=6、P3=1。
- 14个完整PLAN；P2_002、P2_003、P2_004保留ID、简明设计草案和待确认项；当前外部设备测试执行安排见6.4，不把草案算作完整PLAN。
- R0/R1片内4项；R2板级简单连接8项；R3 FPGA4项（其中3项待分析）；R4电气测量1项；不再包含NOR应用。
- 当前12个注册Formal Case：P0=2、P1=7、P2=2、P3=1；首轮已执行，接线修正后仅重测P1_002，当前结果与证据见6.5。其余5个外部设备目标仍按6.4保留边界，不能将草案算作已实现。
- 当前不是“整体分析闭合”：所有已找到的需求条目均有处置，但3项设计及SPI_QSPI_entry定义缺口仍公开保留。不能以结构Checker通过代替语义闭合。
- 每份报告必须区分已测逻辑Case、参数执行数与实例覆盖。代表实例PASS不能证明4实例全覆盖；可复用同一Case参数对可达实例逐一运行。

## 6.2 后续最小实施顺序

1. 修第二章已确认的Driver问题；补配置、SER选择、单次FIFO访问和不会偷读错误状态的接口。
2. 依据本芯片SVD补SPI Capability，再按固定层次实现Wrap、Service、PC Driver。
3. 实现14个方法明确的PLAN；先片内、外部回接/双实例和DMA；波形和电气测量保留设计，当前先不执行。未具备物理资源仍保留代码和明确环境条件，不为了免接线弱化Case。
4. 补齐P2_002的目标协议时序、P2_003的实际延迟深度/时序预算、P2_004的ss_in_n连接。再完善原ID PLAN，不以“难测”判硬件不支持。
5. 本轮12个已实现Case的可执行项已完成门禁及FPGA回归；后续补完整Capability及外部设备缺口，不重复定位已闭合的首轮失败。

## 6.3 Board/Capability待落地事实

当前使用用户确认的SPI0/SPI1四线对接。唯一活动连接位于`pc/et_test_platform/profiles/bench_topologies/et6801_hardware_connections.yaml`：SPI0 CLK/CS/MOSI/MISO为GPIO60/61/16/55，SPI1为GPIO65/66/63/64。PC加载handle/GPIO并调用独立GPIO Driver，SDK复用枚举仍隔离在芯片配置。未占用控制UART。P1_001要求单实例MOSI→MISO短接，与当前四线对接不同；未在连接文件声明`spi.loopback`角色时按真实接线缺口SKIP，不能用双实例收发冒充。

SPI DMA执行映射位于`profiles/chip_execution_mappings/et6801/spi_routes.py`：DR[0]为各SPI_BASE+0x60，32-bit访问单元对应一帧；DMAMUX_REQ_SPI0_TX/RX至SPI3_TX/RX为214～221，来源为SDK `et6x_sysctrl.h`枚举。四通道按两端RX、Target TX、Controller TX顺序准备。公共Case不包含这些地址或请求号。

已知未闭合项：当前生成的SPI Capability仍仅包含SVD实例/IRQ和原始SSIC识别，缺完整角色/帧宽/格式语义。可编程范围暂由已实现的LIMITS_GET交叉核对SDK；这不等于完整芯片Capability已完成，不将该软件缺口列为硬件SKIP。

Capability需发布角色、格式、帧宽、TX/RX容量、水位域、CS适用组合、NDF范围、时钟源/分频及DMA端点。RSD“字段可写范围”与“物理有效深度”分开，后者没有依据时保持Unknown，不以0～255默认补齐。IRQ首次读清与ISR锁存证据在ET6801芯片实现内处理，公共Case不含寄存器地址或芯片名。

## 6.4 外部设备Case的当前执行安排

更新时间：2026-09-04 10:34 CST。按用户要求，以下5项先保留简单Case设计，当前计划SKIP，不阻塞双SPI对测开发。此处是执行安排，不是已经运行得到的SKIP统计；实际运行前缺少指定外部设备时，应在任何硬件配置前跳过并记录设备缺口。缺代码、时序依据或映射仍单独记录，设备接入后须先解决这些问题，不能直接宣称可执行。

| Case ID | 测试内容 | 当前安排 | 外部条件/暂不执行原因 | 恢复测试条件 |
|---|---|---|---|---|
| `SPI_P1_006` | CS窗口、CPOL/CPHA、SCLK频率 | 计划SKIP，未运行 | 配测FPGA尚未开发；也未建立本Case所需多信号同步示波器捕获连接和自动采集链路 | FPGA捕获可用，或确认示波器具备等效采样、通道与解码能力；按相同Oracle采集实际来源 |
| `SPI_P2_002` | TI SSP/Microwire帧格式 | 计划SKIP，未运行；设计依据待确认 | 缺可生成对应协议与ready时序的配测FPGA；普通示波器仅观测不能代替协议激励 | 协议时序和引脚映射明确，FPGA协议对端及捕获可用 |
| `SPI_P2_003` | 高速接收及RX采样延迟 | 计划SKIP，未运行；设计依据待确认 | 缺可控返回相位的FPGA对端与同步边沿测量条件 | 确认有效延迟深度和时序预算，部署相位可控对端及测量 |
| `SPI_P2_004` | Controller冲突状态及IRQ | 计划SKIP，未运行；输入路径待确认 | 配测FPGA尚未开发；ss_in_n到外部的物理路径也未确认，两者不能混为一个原因 | 设计确认输入引出和安全驱动方式，FPGA能在传输中施加有效刺激 |
| `SPI_P2_007` | Target MISO输出高阻 | 计划SKIP，未运行 | 尚无本Case的可切换弱上拉/下拉夹具及示波器/等效电压Observer连接 | 负载可受控切换，探头接入MISO，电压和负载预算确认 |

固定接线目标：双SPI四线互联，FPGA或示波器以固定探头并接观察；FPGA主动驱动时先确认闲置SPI引脚高阻。高阻测试的上下拉通过夹具切换，不人工换线。冲突输入若需额外引脚，应在一次接线表中预留；该路径未确认前不发布最终接线表。此处未指定实际GPIO/连接器，也未证明任一接线可用。

范围排除：SPI_P2_006、SPI_P3_001是用户明确排除的NOR应用Case，不是SKIP、不计当前17项；保留第四章来源以解释范围变化。实际SPI功能测试和原始来源记录不受删除应用PLAN影响。

## 6.5 当前FPGA测试记录

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-09-04 18:50 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-09-04 18:42 CST` | `d6832926244edeb4b8170ef66d652e395f7d3648` | `false` | NOT_RETAINED |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 12 | 12 | 11 | 0 | 1 | 0 | 152 |

参数执行116 PASS、36 SKIP、0 FAIL、0 ERROR。Run ID=`c1e307a9-cc2a-475c-8013-3149baea392e`，Pipeline退出码0。P3_002内部20轮不是20个Case。17项设计目标中另5项见6.4，未进入注册表，不计本表或运行SKIP。

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `SPI_P1_001` | FPGA | SKIP | SPI_F_008 / 单SPI PAD回接 | 配置前无loopback角色，36个参数执行在硬件动作前跳过；未观察回接收发 | 当前SPI0/SPI1四线互联，不满足单SPI MOSI→MISO短接 | 改为单实例回接并声明对应handle/GPIO及loopback角色后执行 | NOT_RETAINED |
<!-- ET_CHIP_TEST_STATUS_END -->

报告：`artifacts/reports/20260904_184643_846713_ET6801_SPI测试报告.xlsx`。原始结果及Excel均在规定artifacts目录，旧Run不改写。

本轮闭合问题与证据边界：

- 接线修正后，双SPI交换角色、4种CPOL/CPHA、3帧宽节点及Target回环开关共48组通过。关闭Target回环的24组证明PAD双向数据，回环开启的24组不冒充完整外部链路证据。
- SDK FIFO容量16修正为实测32；IRQ/启动/DMA阈值仍按SVD四位字段限制0～15。容量、自然Overflow、IRQ清除及DMA64/65帧传输通过，未放宽断言。
- SPI Case在CRG复位DMA前先停止、解除通道配置再关闭Controller，消除Service旧配置影响；未改DMA源码。DMA28组及连续20轮通过。
- 报告摘要每个Execution只登记一次，完整节点/轮次观测保留。只修SPI Case及模板，未改公共报告层。
- 部署证据：，固件源码`ba5ba0b535a4e45ba485caed564f7251f34dabc8`，按编译→bitfile→BootROM→PFLASH运行。该轮硬件同为116 PASS/36 SKIP，但报告失败，不能称整条Pipeline通过。最终Run仅修PC摘要并复用同一Flash固件，没有重复烧录。
