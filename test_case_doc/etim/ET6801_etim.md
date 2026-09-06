# ET6801 ETIM Chip Analysis & Adaptation

时间：2026-09-06 16:31 CST

目标：ET6801 / ETIM（SDK别名ETIMER），lane=docs。本轮未操作硬件，未修改实现。
公共语义唯一入口：[etim.md](etim.md)。文档记录遵循工作区`DOCUMENTATION_RULES.md`。
源码基线：ATP `codex_dev`，`a6b3e9b79815d11d97469b029063818591bf4f54`；本次分析前工作树干净。

**阶段结论：PARTIAL_ANALYSIS。** 继续复核后准入44个Feature并写30个PLAN，0个Formal Case实现、0个实测。
下面的Source Item全集含未闭合需求；不能用44/44映射或30/30机器块合法声称整个ETIM规划完成。
本地SDK中的测试函数、旧手册公式及入口调用均不是本轮FPGA/Silicon PASS。

2026-09-06 18:15 CST复核基线为`c5e7c24bba855f044e7f5353f41f53ad7999fb54`，工作树初始干净。
用户明确ETIM为继承IP，目标硬件交付只有SVD，无法提供RTL。本轮据此纠正分析方法：
6003/3101参考资料可以解释稳定机制，ET6801 SVD负责确认功能存在并约束字段、数量和路由差异。
RTL不是必需输入；旧芯片资料不再仅被当作“搜索线索”，但也不能单独证明ET6801硬件已验证。

2026-09-06 20:45 CST继续复核基线为`98e3b2236f1e063e4bf9ba3981a9bddb99740ea1`，初始工作树干净。
本轮只增加ETIM公共/芯片文档内容；相邻ADC/DAC/ACMP/XBAR资料只读，用于接收端Oracle及路由。

## 第一章 Source Coverage / Evidence Set

### 1.1 资料根与搜索口径

采用当前Source Map的`roots1`，不使用不可移植的历史云盘假定。

| 简写 | 精确根路径 |
|---|---|
| SDK | `D:/lihuan/vibe_code/code/SDK/git` |
| V6801 | `SDK/6801/et6801-verification` |
| V6003 | `SDK/6003/et6003-verification` |
| V3101 | `SDK/3101/et3101-verification` |
| S6003 | `SDK/6003/6003_sdk/et6003-sdk` |
| S3101 | `SDK/3101/et3101-sdk` |
| SVN | `D:/lihuan/vibe_code/SVN/Software` |
| BOOT | `D:/lihuan/vibe_code/code/boot_rom` |
| ATP | `D:/lihuan/vibe_code/codex/projects/ET_ATP_Testing` |

表中SDK等前缀按本表展开，不是另一份路径配置。搜索包括文件别名`etim/etimer`和符号`ETIMER_/_ETIM_`；
不把`writeTime`、文件时间戳等子串误报为ETIM。文档Locator中的空格与磁盘实际目录名不同处，
在相同已登记父根内定位实际文件并记录如下，没有用其他芯片文件静默替代目标资料。

| 登记资料根/入口 | 状态 | 找到的目标内容及边界 |
|---|---|---|
| SDK/test_case | FOUND | `6003/etimer.json`与`3101/etimer.json`；各62个有ID Test Point、44个Case。6801目录无同IP需求文件 |
| V6801/Tools/RegGen | FOUND | `ET6801.svd::ETIMER`及`svd/etim_cfg.svd`；目标主事实 |
| V6003/Tools/RegGen | FOUND | ETIMER拆分SVD，CORE=3、stride=0x2C，与目标不同 |
| V3101/Tools/RegGen | FOUND | ETIMER拆分SVD，CORE=14、stride=0x2C，与目标不同 |
| V6801/DFP/Drivers | FOUND | CMSIS `et6801.h`、ET6x_Driver的ETIMER及SYSCTRL DMA请求枚举 |
| V6003/DFP/Drivers；S6003/DFP/Drivers | FOUND | 两套ETIMER驱动/API版本；只作历史实现与差异证据 |
| V3101/DFP/Drivers；S3101/DFP/Drivers | FOUND | ET3x/ET6x命名差异；不得套用固定文件前缀后误判缺失 |
| V6801/DFP/Test | FOUND | UnitTest/test_etimer.c、FunctionalTest/etimer_ft.c、SmokeTest/etimer_smoke_test.c、FPGATest/etimer_fpga_test.c |
| V6801/Doc/examples/ETIMER（本轮query新增入口） | FOUND | 五个main.c：InputCapture_Interrupt、InputCapture_Oneshot、PWM_Compare_Shadow、PWM_Complement、PWM_Out_Fault；均按有效目的映射，未运行，不按示例名称计PASS |
| V6801/Tools/RegGen/svd相邻接收端（本轮定向扩读） | FOUND | dacc_cfg、cmpc_cfg、sarc_cfg、adcreg、xbar；只读取事件接收、结果和路由字段，未开展这些IP的全量分析 |
| V6003/DFP/Test | FOUND | UnitTest/test_etimer.c、FPGATest/ETIMER/etimer.c、ChipSieveTest/chip_sieve.c |
| S6003/DFP/Test | FOUND | UnitTest/test_etimer.c、FunctionalTest/etimer_ft.c、SmokeTest/etimer_smoke_test.c |
| V3101/DFP/Test | FOUND | UnitTest/test_etimer.c、FPGATest/ETIMER/etimer.c、ChipSieveTest/chip_sieve.c |
| S3101/DFP/Test | FOUND | UnitTest/test_etimer.c、FunctionalTest/etimer_ft.c、SmokeTest/etimer_smoke_test.c、ElectricalTest/electrical_test_etimer.c |
| V6801/DFP/Test/StressTest | NO_MATCH | 目标IP别名及符号定向搜索无有效ETIM测试 |
| V6003/DFP/Test/StressTest；V3101同路径 | NO_MATCH | 无有效ETIM测试，不据此新增压力覆盖 |
| V6801/DFP/Test/ChipSieveTest/chip_sieve.c | NO_MATCH | `i2c_writeTime`不是ETIM |
| V6003、V3101的ChipSieveTest/chip_sieve.c | FOUND | CS_ECAP_init、SRPWM_entry、ECAP_entry，外部捕获旧接口与断言 |
| V6801/DFP/Test/ElectricalTest | NO_MATCH | 登记entry存在，未找到有效ETIM测量体 |
| V6003、V3101的DFP/Test父根中ElectricalTest locator | NO_MATCH | 父根可访问，登记子路径不存在；没有将S3101电气源码伪称为V3101来源 |
| V6801/DFP/Test/Coremark | FOUND | README勾选ETIMER及复制驱动/CMSIS；没有独立ETIM性能测量体 |
| V6003、V3101的DFP/Test父根中Coremark locator | NO_MATCH | 父根可访问，子目录不存在 |
| V6801/DFP/Test/SignalChainbenchmark | NO_MATCH | 无有效ETIM测试 |
| V6003/DFP/Test父根中SignalChainbenchmark locator | NO_MATCH | 子目录不存在 |
| V3101/DFP/Test/SignalChainbenchmark | FOUND | 复制ETIMER驱动；不构成独立ETIM信号链测试 |
| 三个V根/DFP/Test/PerformceTest/IT_latency | NO_MATCH | 定向搜索无ETIM IRQ latency测试 |
| V6801/DFP/Project/base.uvprojx；V6003/V3101对应工程 | FOUND | 工程可定位，用于确认测试入口所在树，不以工程收录推断函数被调用 |
| SVN/ET6003及ET3101测试用例根 | FOUND | 原始etimer_testcase.xlsx与结构化JSON的source.sha256一致；按已提取需求阅读，未复制原始表全文 |
| SVN/ET6002/01设计文档/04 SDK详细设计 | FOUND | `ET6002 ETIMER模块软件详细设计书.docx`，历史14通道设计及PWM/Capture公式 |
| SVN/ET6003/03参考资料/IDS | FOUND | `ET6003-用户手册_寄存器定义_V1.0.0.docx`，ETIMER章；旧3通道机制 |
| SVN/ET6003/03参考资料 | FOUND | `ET60157-用户手册_V1.0.0.pdf`，第13章ETIMER，物理148～166页；非ET6801手册 |
| SVN/ET6801定向ETIM文档搜索 | NO_MATCH | 未找到可补齐目标时序的ETIM专用手册，不以其他芯片手册替代 |
| BOOT/bootrom-dev-et6801/source/Drivers | FOUND | CMSIS/交叉引用有ETIM事实，未发现ETIMER独立驱动或新增测试体 |
| BOOT/bootrom-dev-et6003/source/Drivers；BOOT/bootrom-dev-et3101/source/Drivers | FOUND | 两份ET6x_Driver/Src/et6x_etimer.c相同SHA256；旧四路全局DMA等API，无新增测试Oracle |
| ATP/pc/et_test_platform/test_cases；ATP/test_case_doc | NO_MATCH | 本次分析基线没有ETIM公共契约或Formal Case；本轮新增文档不反向计入历史覆盖 |

未选择的`roots0/GDRIVE_SDK`是备用Locator，不是当前环境的第二套必读副本。
已登记父根可访问且目标子路径不存在记为NO_MATCH；不是因权限或断连导致的UNAVAILABLE。
**这只表示资料定位完成，不表示需求或测试方法全部闭合。**

### 1.2 固定来源身份与使用方法

| Evidence | 文件/符号 | SHA256 |
|---|---|---|
| H1 | V6801/Tools/RegGen/ET6801.svd，ETIMER | `49B2DE29BD7A0A4A5FBDEFC6E36D75CD6DA53A46F5504F860DEE53BE9079CCE4` |
| H2 | V6801/Tools/RegGen/svd/etim_cfg.svd，全部字段 | `AB1171BD179360D5B3111240F0E7905D7A097328566321D82F157767DE8C9BED` |
| H3 | V6801/DFP/Drivers/CMSIS/Device/Include/et6801.h，ETIMER_Type及IRQ | `D0F2C9EA612A20D2DA5BA4C8F6A4E3DDF82B7F0F80F7F3CF0B5371801ABAA324` |
| D1 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_etimer.h | `87F90FA7D54C460E868C7DC5D67F702D2035FFB4DB202C77C1527910DACA5E4A` |
| D2 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_etimer.c | `C06DFB7FC779B8AFBDA68CCAEE3140EAC2124754C934813788AC3A0336549D5D` |
| R6 | SDK/test_case/6003/etimer.json | `6231288A1F4D191F58A1D2CF5EAEAB6B99377BC150E39D89DBAC396C0E32A357` |
| R3 | SDK/test_case/3101/etimer.json | `74D71BCC70FB7F76982B6F78F5AE6F3300EC91F36CC2970B1D7F62EF16A5D530` |
| X6 | R6所指原始etimer_testcase.xlsx | `9D08B47EF76AAF14A844E8908E936B7BC7E9C0DAD98D637C87E4C7DF9D5F72D1` |
| X3 | R3所指原始etimer_testcase.xlsx | `4A96FD6B12BC3DEDE2F4D0D516AD6CE3232D3B3EA79E255F23F7BEDFC67B0F47` |
| M1 | SVN/ET6003/03参考资料/IDS/ET6003-用户手册_寄存器定义_V1.0.0.docx | `4ABC402E551A37732369703E5E9CD2D5445CAA73344B56C5938463C72E25EE70` |
| M2 | SVN/ET6003/03参考资料/ET60157-用户手册_V1.0.0.pdf | `B4D2F0754CDD717CE4708E9BA1542730610C7F5A7FA7F20E364D91EC3D845AB4` |
| B1 | BOOT两份ET6x_Driver/Src/et6x_etimer.c | `6578D4228329D33CF877EB68C698C67AC4575F53769AD83E30409EE596B3665C` |
| H6 | V6003/Tools/RegGen/svd/etim_cfg.svd，继承字段复核 | `0D933B6EA0ECF45BEE94A53FC964527D0411C79F9E86A33D0E0E05E53282935F` |
| H7 | V3101/Tools/RegGen/svd/etim_cfg.svd，继承字段复核 | `E42753DAF63523DC1B46215742327995F5B80E1732FEF0AA5A4DAB82E2A2CDC6` |
| H8 | V6801/Tools/RegGen/svd/dacc_cfg.svd，触发及加载上报 | `D9AA49784F8560301F4CF4521E94A8877B884BBDF1CAAD4DB2E4F2E5DEE7DB09` |
| H9 | V6801/Tools/RegGen/svd/cmpc_cfg.svd，双DAC触发及比较状态 | `7B90FE4D069E3FB2AAB7CCAC72A8A61B0A1B55BF3A3C2882BFABA223131668D3` |
| H10 | V6801/Tools/RegGen/svd/sarc_cfg.svd，VC触发及EOC | `811F18CD4F6954FAC76F5B9846ADB4AE3C98C1654A7892FE08F54B8B80265920` |
| H11 | V6801/Tools/RegGen/svd/adcreg.svd，ADC结果端点 | `F3B597CEFF138EFD515A95B0B7B9F83285144D6D64E4E9B28A22C6ABD148FA97` |
| H12 | V6801/Tools/RegGen/svd/xbar.svd，ETXB及输出实时上报 | `BDB1C6EA2283A44AA37C6598F4FA73F30A6904C4779286FAC213CAF7712DE299` |
| D3 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_adc.h，目标触发枚举 | `3565B523BACFE75E6849E4FCCA1D96089CE03733FD77C65D70C476BEA1D4D9C5` |
| D4 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_dac.h，Shadow接收说明 | `32A99E55FE8A125CAFDF1CEDAF0361114A9E3A408B371C626D66A1687C78E78C` |
| D5 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_acmp.h，双DAC及模拟端选择 | `8D0E9394B3F980CEBF88EB7BF26556EB9CB589DF02D51BEDF968E5F72D3F020B` |
| D6 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_xbar.h，输入和EXTSYNCOUT路由枚举 | `DCDE5E74D86A0BFF6BC74088492ACFB10052DE251D3B2AC5B81DE2B1B3B057E4` |
| D7 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_dac.c，DAC_configTriggerMode | `38C5C9FA4EB60AEDA8605ED5332C42454264E8AB68B51EE0A94D2D76418E3D28` |
| D8 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_acmp.c，ACMP_configDAC及加载读取 | `7C47530FF86133E72BC9FD4EBB63190A1ED3B46662A0B5B0194C2CD18D5BDE1E` |
| T6 | S6003/DFP/Test/FunctionalTest/etimer_ft.c，事件接收及XBAR体 | `44DBD03B1E9F12D1D3743ACD75B0FE66BDE1CA54ACA9FB8FABD25E6172483B78` |
| T3 | S3101/DFP/Test/FunctionalTest/etimer_ft.c，事件接收及XBAR体 | `2EF73FAE26A07EF2D599927CAE921E43C130760A3F2D0B047A05B669642D5897` |

文档先使用ET技能导航和共享toolbox摘要，再定向解析DOCX XML/OMML公式、PDF文字与关键示意图。
目标SVD使用XML结构解析，特别处理本地拆分SVD中cluster内addressOffset已为绝对偏移的方言，
不再次叠加cluster起点。参考资料用于解释继承机制和设计Oracle，结合目标SVD确认适用范围，不能独自证明目标硬件SUPPORTED。
过程输出位于外层项目`Et_Automated_Testing_Platform_Code/artifacts/runs/20260906_154000_etim_analysis/`，
含chip query、doc discovery、定向文字提取和私有参考图；这些图不作为可公开波形报告。

## 第二章 ET6801 Hardware / Driver Facts

### 2.1 已确认位图与能力参数

下表VERIFIED指目标静态证据成立，不表示硅片实测。H1、H2、H3共同确认12通道，优先于D1的14通道旧常量。

| Claim | 状态 | 目标事实/用途 |
|---|---|---|
| 实例与基址 | VERIFIED | 单ETIMER块`0x40024000`，逻辑CORE[0..11]；不存在由驱动常量推导的CORE[12/13] |
| CORE布局 | VERIFIED | CORE[12]起点0x004、stride=0x30；周期/比较/计数/相位均32位 |
| 输出分组 | VERIFIED | OUT[6]起点0x244、stride=0x14，两个PWM支路一组，四条14位延迟计数 |
| CAP布局 | VERIFIED | CAP_CNT[12]起点0x2EC、stride=0x10，每通道四个32位CAP值 |
| 计数分频 | VERIFIED | PWM_CTRL.clkdiv_fac六位，编码0..63对应实际1..64，不限于历史需求列举的二次幂 |
| 周期普通点 | VERIFIED | 历史目标FT test_9明确以P=3000检查捕获值3001；M2也为0..P含终点，普通period_ticks编码P=period_ticks-1有一致证据；P=0和最大值运行边界另见G09 |
| 比较模式 | VERIFIED | PWM_CTRL.comp_mode选择A或A+B；COMPA、COMPB字段及比较IRQ存在；普通严格内部点的波形由参考语义和目标PWM/CAP测试交叉支持 |
| 软件锁存/清零 | VERIFIED | PWM_CTRL.cntlk/tclr写脉冲；LKCNT_RPT只读锁存值，RLCNT_RPT只读实时值；软件不得把脉冲读回为零当作唯一完成证明 |
| 分级Enable | VERIFIED | EN0上12位ETIM_EN、下12位TIMER_EN；EN1上12位PWM_EN、下12位CAP_EN；CAP_CTRL另有cap_load_en |
| 捕获槽序列 | VERIFIED | cap_stop_wrap编码0..3对应1..4槽；cap_mode=0连续/1单次；cap_mod_sts指下一槽；Rearm复位槽序列并解冻 |
| 捕获时间戳 | VERIFIED | 每槽独立polar和clr_cnt；0不清为绝对、1事件后清为相对；首槽启动延迟不得当成稳定期望 |
| 输入预分频 | VERIFIED | cap_pre_div=0旁路，1..31对应2、4、…62；它是输入事件分频，不是时基分频 |
| IRQ | VERIFIED | CMN_INT[12]起点0x3F0、stride=0x18；每源12bit，通道IRQ为167..178；INT_MASK复位值含bit3屏蔽配置错误 |
| IRQ源位序 | VERIFIED | bit0 OS Fault，1 CBC Fault，2 Fault overflow，3 A≥B配置错误，4 A比较，5 B比较，6周期，7计数回卷，8..11四槽捕获 |
| Shadow字段 | VERIFIED | PWM_CTRL.shdw_ug bit0周期、bit1比较对、bit2事件；目标描述为周期边界更新；UPDATE_VLD需在COMPA/B均写好后置位，硬件清除 |
| 同步字段 | VERIFIED | SYNC_CTRL.SYNCO_SEL=0软件、1周期、2/3禁用；SYNC_IN_EN及SW_SYNC脉冲；CTRPHS装载相位；准确边界见G06 |
| 自然事件 | VERIFIED | EVT_TO_ADC选择0周期、1零点、2 A、3 B、其余事件比较；EN3各通道事件使能，bit16公共延展描述待确认 |
| Fault字段 | VERIFIED | fault_sel=0软件、1 XBAR0、2 XBAR1、3保留；CBC/One-Shot、高低输出可配置；退出和优先级不能只由字段名推出 |
| DMA位图 | VERIFIED | CMN[12]每通道DMA三位字段；SYSCTRL的DMAMUX_REQ_ETIMER0=55至ETIMER11=66，共12个请求入口，不是旧4个全局请求通道 |

### 2.2 输入、同步及事件路由

| 目标字段 | 编码/路由事实 | 处置 |
|---|---|---|
| CAP_CTRL.cap_in_srcsel | 0..15 INPUTXBAR，16..27 OUTPUTXBAR，28..31 CLU，32..39 UART_RX，40..41 LIN_RX | 数量和路由选择为Capability；各Peer刺激方法G11未闭合 |
| 同上 | 42..77 SRPWM两路输出；78..89 ETIM1_PWM..ETIM12_PWM | 目标SDK零基枚举与SVD一基信号名要显式转换；内部ETIM PWM路由无需外部跳线 |
| 同上 | 90..122 CMPSS高/低/或，123..134 ADC事件，135..198 SDFM事件，199..210 CLB，211..218 GPIO2ETIM | SVD描述带排版编号噪声但编码字段明确；不把0..218都当成已测试输入源 |
| SYNC_CTRL.SYNC_SRC_SEL | 0..17 SRPWM，18..23 INPUTXBAR，24..35 ETIM；其余描述为零 | 旧芯片ETIM输入编码18不能移植到本目标 |
| SYNC_OUT.SYNC_OUT_SEL | 文本仍列到ETIM14，和12通道结构不一致 | 只有存在的源可用于后续映射，尾部选择值G06禁止猜测 |
| DACC / CMPC[11] | 两个DAC触发选择、每ACMP有独立DAC触发选择nibble；文本仍有超出目标通道的旧选择项 | G08；不能用驱动旧枚举宣称额外通道存在 |

最少接线路线是独立ETIM PWM通道经`cap_in_srcsel`输入另一ETIM Capture。
本轮只能确认这条数字路由存在，不能宣称全部输出支路、延迟旁路和捕获时钟误差上界已经实现映射。
尤其DB_SEL的a支路第3级MUX说明与支路标题不一致；普通PWM源优先选择有直接证据的支路，
其余支路保持G04，不允许把部分路由结果扩成12路PWM全覆盖。捕获通道可逐一轮换，生产者仍须独立。

### 2.3 已确认Driver风险（只记录，未修改）

| 来源/符号 | 事实 | 后续处理边界 |
|---|---|---|
| D1 ETIMER_CHANNEL_ALL及通道枚举 | 14通道、mask=0x3FFF、7输出组；与目标12通道/6组冲突 | Chip Driver约束0..11及0xFFF，不能在公共Case中补if-chip |
| D2 ETIMER_initTimeBase等循环 | 循环上界沿用14，旧通道12/13可能越过CORE数组；合法mask检查不等价于目标12位全集校验 | 后续Chip Driver任务修正，当前禁止运行旧测试 |
| D2 ETIMER_deinit | 复位主体被注释，实际无有效复位操作 | 不可把调用deinit视为隔离已完成；必须复用已验证CRG/平台复位 |
| D2 ETIMER_getCount | 写CNTLK后立即读LKCNT_RPT | 需目标侧有界可见性处理，不能把旧快照作为本次锁存值 |
| D2 ETIMER_initDB | 延迟输入和分组边界需针对6组/14bit检查 | 这是实现Gap，不是目标硬件不支持 |
| D1/D2 DMA API | D1仍为4个DMA channel枚举及0..55的旧CAP事件枚举；D2已改写CMN[index].DMA三位字段，却直接写入旧src且没有新枚举校验 | 新寄存器写法与旧API混用；大于7的src还可能写到字段外，禁止原样移植test_43 |
| D2 ETIMER_selectSyncToACMP | 对整个8bit DACCTRG_SEL清零后写src，会覆盖另一个DAC选择nibble | 需核对目标双nibble语义再修；不能以单路读回覆盖双路独立性 |
| D2 ETIMER_resetCapture | 接口接受mask形式但POSITION_VAL只选一个通道 | 公共直接动作采用单逻辑通道，适配层拒绝混合mask |
| H2 DB_SEL及同步/触发文字 | a支路文字指向b、若干选择项残留通道12/13 | 保留G04/G06/G08，寄存器字段存在不证明具体时序和路由文字都正确 |

### 2.4 继承机制复核与适用裁决

以下比较使用H2/H6/H7的XML字段内容，而不是仅看同名API或相同文件名。VERIFIED指所列
静态事实有证据；常规行为Oracle是基于目标字段与继承资料形成的待测契约，不等于ET6801实测。

| 机制 | 证据与裁决 | 可以确定的设计 / 剩余边界 |
|---|---|---|
| 窗口滤波 | VERIFIED：H2/H6/H7的CAP_FILTER四字段位宽和描述一致，均为W=SAMPWIN+1、T=THRESH+1、FILINIT选择全零或当前输入；并非从旧连续采样结构刚在6801改造 | P2_004用T>W/2消除双阈值歧义，短脉冲不足T次采样、长平台填满窗口；采样周期编码归G03映射，不用M2旧N+1公式覆盖窗口算法 |
| 四链死区 | VERIFIED：三份SVD均有同样s0输入选择、s1上升延迟、s2下降延迟、s3旁路/直出/反相以及四个14bit延迟；a支路s3描述复制b也在两参考SVD存在 | P2_005先覆盖文字自洽的b支路；a支路是共同文档歧义，不是已证实目标新增机制，不能无依据改正为确定事实；窄脉冲和动态延迟另G04 |
| Shadow | VERIFIED：目标shdw_ug明确周期边界加载，update_vld明确A/B都写完再提交并硬件清零；H6/H7及FT test_40/41保留同类需求 | P1_009/010已有独立过渡边沿Oracle；目标周期边界优先于M2旧SHWD可编程比较/事件装载点，不再等待RTL |
| 同步 | VERIFIED：三份CTRPHS均明说同步到达时装入计数器，SW_SYNC、SYNC_IN_EN、SYNCO_SEL语义一致；目标输入选择扩到6bit | P1_011验证运行中的相位跳变及禁用对照，目标ETIM输入24..35取代旧18起始；停止时、同拍清零等竞态不影响该正常路径规划 |
| Fault | VERIFIED：目标CBC/One-Shot、软件输入、Clear、输出极性及三个自然IRQ均存在且与继承结构相符；M2 13.4.5.2解释CBC周期退出、OS同周期撤销+Clear及重复输入overflow | P2_003将这些正常状态路径作为继承测试Oracle，保留无Clear负对照；没有将旧输出互补图套给新DB，Fault/DB优先级仍G05。若实测不符需登记目标差异，不改Expected凑PASS |
| DMA | VERIFIED：目标每通道DMA三位字段明确列出1=PRD、2=CMP，与SYSCTRL十二个请求入口共同确认普通请求选择；旧全局四路API与新字段不适用范围不同 | P2_006以公共DMA硬件终态和Destination证明基本搬运；3所称事件是哪一CAP槽及4..7仍UNKNOWN，旧src=0..55不能直接下发 |

G03的采样时钟、G04的延迟时钟、G06的同步传播界是实现时需要绑定的独立时钟/映射事实，
不是“滤波/死区/同步全部原理未知”。若映射未完成，相应execution不能开始，更不能自行放宽容差。
可继续从目标时钟字段、同族同结构说明或硬件方对具体字段的简短答复补齐，不要求内部RTL文件。

### 2.5 接收端事件、外部路径与剩余边界复核

| Claim / 来源符号 | 裁决与可证明事实 | Case和剩余限制 |
|---|---|---|
| Event不等于SyncOut；H2 EVENT_CNT、EVT_TO_ADC、DACC、CMPC及SYNC_CTRL | VERIFIED：计数事件为`etim2adc_evt`，DACC与CMPC选择的均是该事件；SYNCO_SEL另选软件或周期同步。R6/R3 Case029～031只有联合测试标题，没有要求以CTRPHS信号触发接收器 | 将旧“同步ADC/DAC/ACMP”按接收触发目的映射P2_008～012，不要求不存在的统一SyncOut接收链；不把字段存在当接收已执行 |
| DAC接收；H8 TRG_SEL/TRG_SET/DAC_TDAT_RPT/DAC_TXDN_RPT，D4/D7 | VERIFIED：TRG_SEL=2选ETIM，寄存器数据输入，LDMOD位由shadowLoadEn设置；DAC_TDAT_RPT是真实加载值而TDAT是待发送值。输入流模式会使TXDN常为1，必须禁用 | P2_008用旧值保持、新值加载和独立TXDN；P2_011补模拟端观察。无需用IRQ Force证明接收；加载传播上界仍须映射 |
| ACMP内部DAC接收；H9 DAC_TRG_SEL、DAC_LDMOD、CMPC_DAC_TDAT，D5/D8 | VERIFIED：两侧各有触发源2、LDMOD、TRGEN和TDAT；实际加载上报分别htdat_load_rpt/ltdat_load_rpt，不能读配置回显。CMPC_STS提供滤波前真实比较状态 | P2_008双侧独立路由；P2_011保留内部DAC模拟电压观察，P2_012另证阈值跨越。关闭Ramp、输入流、Blanking及反相；测试输出到物理端的路径待Bench绑定 |
| 目标DACC通道选择尾项；H2 CFG_ETIM_DACC | UNKNOWN：0～10文本自洽；描述漏11却列12/13，与12个CORE不符。CMPC选择0～11有明确文本，12/13同样越界 | DAC源0～10可进入普通映射，源11不得从邻项补字后当VERIFIED；其缺失为G08局部路由说明，不阻塞其他源方法 |
| ADC触发与结果；H10 VC配置/EOC_CTL/CFG_EOC_INT_SRC_SEL，H11 SOC_RESULT，D3 | VERIFIED：目标VC触发字段7bit，D3明确ETIMER0～11为36～47；H10 EOC模式1是转换结束，0是采样结束、2是采样开始；EOC四路再选择具体VC，不可复制旧API虚拟通道掩码 | P2_010使用一个转换VC和EOC选择，采真实结果和外部服务标记；ADC时钟、输入误差和转换/ISR界为Mapping。数字仿真结果不能替代该Silicon模拟链PLAN |
| 动态事件；H2 shdw_ug bit2/EVENT_CNT，R6/R3 Case038/042 | VERIFIED：目标事件Shadow在周期边界更新，不是M2旧SHWD指定点。Case042写入同一个0xFFFF且Expected忽略已有旧事件，旧步骤不能区分新旧加载 | P2_009使用6000/10000双向变化，当前与下一周期及另一个候选点分别观察真实接收完成；修正旧方法，保留事件延迟一周期生效目的 |
| 运行相位；H2 CTRPHS，R6/R3 Case037 | VERIFIED：相位在同步到来时装计数；Case037只写“和相位测试一致”，没有独立证据要求单写CTRPHS就重装 | P1_011加入运行中相位修改、不触发保持、下一同步用新值；P2_007独立外部相位波形。不把旧“立即加载”标题强行解释成目标不存在的相位Shadow开关 |
| 动态死区；H2/H6/H7 APOS/ANEG/BPOS/BNEG，R6/R3 TP057/Case039 | VERIFIED：直接延迟配置与继承立即更新测试目的适用；安全窗口先确保没有在途延迟，可由输入时刻和最大旧延迟建立Oracle | P2_015在本周期首个输入边沿前写新值，要求本周期后续边沿用新延迟；延迟正在计数时改值的重载/续数规则仍UNKNOWN，不发布全竞态结论 |
| 自然最大值回卷；H2 32bit TIMER_CYC/CTRPHS及IRQ bit7，M2 13.4.8.2 | VERIFIED：最大值回卷事件区别于普通周期事件，目标有独立bit6/7；相位同步可把运行计数装到最大值附近，不需要跑完整32bit周期 | P1_012比较普通周期与最大周期，并采临界前后实际计数、自然pending和ISR；这证明最大终点路径，不冒充从零完整跑满最大周期的长稳测试 |
| 外部SyncOut；H2 SYNC_OUT，H12输出XBAR，D6 EXTSYNCOUT，T6/T3 test_32 | VERIFIED：存在全局选定同步到XBAR/PIN路径；已存在ETIM源编码12～23，超出12通道的24/25不使用。旧函数实际选择PERIOD SyncOut而非CUSTOM Event | P2_013保留外部单次/周期脉冲及源选择。EN3 bit16描述称Event延展、旧enableSyncOut名称不够证明它是SyncOut总使能；具体外送开关和宽度仍G06 |
| 外部Fault；H2 fault_sel，H12 ETXB及OUT_RPT，D6，T6/T3 test_20 | VERIFIED：目标有两个外部选择，参考体以GPIO→INPUTXBAR→ETXB刺激Fault，目标XBAR存在直出及实际电平上报 | P2_014给可审核双输入选路、封波与退出方法。每CORE的XBAR0/1究竟绑定哪两个ETXB输出仍为明确Mapping Gap，禁止复制旧ETXB3或推断索引公式 |
| Capture DMA；H2 CMN.DMA，R6/R3 Case043，T6/T3 test_43 | UNKNOWN：目标3仅写“etimer 1事件”，前面又残留CEVT4..1旧列表，不能证明3=CEVT1或全部捕获事件；4～7无说明。1=PRD可明确使用 | P2_016以外部真实高低宽、冻结CAP端点、PRD请求和DMA目的内存闭合数据搬运；旧捕获事件请求及连续四槽DMA流仍未覆盖，不能改为MAPPED全集 |

本轮没有发现现行ADC/DAC/ACMP/XBAR公共文档入口。上述Peer动作定义为ETIM Case所需的稳定
协作语义和真实端点，后续必须通过各IP合法Service/Wrap实现；本任务不新增Peer代码或公共架构。
共享CRG只确认ETIM门控和软复位字段，不能由此推出CAP_FILTER与DB的精确时钟编码公式。

## 第三章 Source Item Trace

### 3.1 需求Test Point逐项处置

以下TP编号均指R6和R3中的`ETIMER_TP_nnn`，不是新公共ID。两份同义条目按相同目标处置，
参数差异归Capability；每行同时保留原验证目的和为什么没有直接复制历史方法。
`Gnn`与公共`EG-nn`一一对应。关联Gap的条目不计已规划覆盖。

| Source Item | 原目的/刺激与观测 | 目标依据及目标Case/Gap | Disposition |
|---|---|---|---|
| TP001 | 各PWM通道输出波形 | H1/H3为12通道；P1_001/P2_001覆盖已确认路由，其余输出支路G04/G02 | SPLIT |
| TP002 | 分频改变波形频率 | 六位实际1..64；P0_001读回、P1_001数字比例、P2_001外部时间 | SPLIT |
| TP003 | 32位周期及输出周期 | P0_001配置边界、P1_001/P2_001普通波形；运行极限G09 | SPLIT |
| TP004 | 相位装载后波形偏移 | P1_011计数装载与P2_007引脚相位；后者独立外部Oracle，Bench为G10 | SPLIT |
| TP005 | A/A+B占空模式 | P1_001和P2_001分别内部与外部高低宽 | SPLIT |
| TP006 | A比较值影响波形 | 同上A模式参数分支，动态更新另G07 | MERGED |
| TP007 | B比较值影响波形 | 同上A_B分支，非法顺序P1_008 | SPLIT |
| TP008 | 死区上升延迟 | P2_005正常脉宽与已映射支路；a支路及窄脉冲G04 | SPLIT |
| TP009 | 死区下降延迟 | P2_005正常延迟；剩余同TP008 | SPLIT |
| TP010 | 死区输入源选择 | P2_005自身/另一支路来源Observer；a支路G04 | SPLIT |
| TP011 | 死区上升延迟使能 | P2_005单开/双开/旁路；未确认支路G04 | SPLIT |
| TP012 | 死区下降延迟使能 | P2_005单开/双开/旁路；未确认支路G04 | SPLIT |
| TP013 | 死区输出选择/反相 | P2_005覆盖自洽b支路，a支路s3仍CONFLICT G04 | SPLIT |
| TP014 | PWM使能后输出 | P1_006恢复后真实周期，不只Enable读回 | MERGED |
| TP015 | PWM失能停止输出 | P1_006稳定窗无新捕获，关闭电平不作假定 | MERGED |
| TP016 | Timer使能 | P0_001实时计数、P1_006恢复输出 | SPLIT |
| TP017 | Timer失能 | P0_001计数保持、P1_006无周期边沿 | SPLIT |
| TP018 | 捕获通道选择 | H1为12通道；P1_002/003/004/005轮换DUT | MERGED |
| TP019 | 输入预分频1～62 | H2为1及偶数2..62；P1_005全合法倍率 | MAPPED |
| TP020 | 输入源选择全集 | 目标编码0..218；内部PWM P1_002，外部P2_002，其他Peer G11 | SPLIT |
| TP021 | 上升/下降捕获 | P1_002/003非对称波形分别证明极性，P2_002外部复核 | SPLIT |
| TP022 | 绝对/相对时间戳 | P1_002绝对、P1_003逐槽清零、P2_002外部Oracle | SPLIT |
| TP023 | One-Shot | P1_004后续刺激下CAP保持 | MERGED |
| TP024 | Continuous | P1_004多窗口真实刷新 | MERGED |
| TP025 | One-Shot重装 | P1_004 ReArm后首槽及新数据，不以API返回成功替代 | MERGED |
| TP026 | 滤波时钟分频 | P2_004跨已映射采样设置；编码公式Mapping G03，精确分频比测量仍待规划 | SPLIT |
| TP027 | 滤波阈值 | P2_004唯一多数阈值；双方同时达阈值及精确边界G03 | SPLIT |
| TP028 | 滤波窗口大小 | P2_004的8/16窗口；全边界与初始化瞬态G03 | SPLIT |
| TP029 | Fault各通道输入 | P2_003软件、P2_014双外部输入；全输出支路及组合优先级仍G04/G05 | SPLIT |
| TP030 | “采样转换结束时刻”Fault | 两份Case019步骤仅“删除”，无ETIM有效刺激/观测；不排除其他Fault需求 | REJECTED |
| TP031 | One-Shot Fault | P2_003沿继承周期恢复模型，保留无Clear对照；同拍竞态G05 | SPLIT |
| TP032 | CBC Fault | P2_003输入撤销后周期边界恢复；同拍竞态G05 | SPLIT |
| TP033 | 软件Fault触发 | P2_003真实fault_sw输入及自然IRQ，不使用Force | MAPPED |
| TP034 | XBAR Fault输入 | P2_014选中/未选输入、自然封波和恢复；双外部输入到ETXB的精确绑定为G11 Mapping | MAPPED |
| TP035 | Fault强制高电平 | P2_003延迟/反相旁路下独立电平Observer，组合优先级G05 | SPLIT |
| TP036 | Fault强制低电平 | P2_003低电平参数，组合优先级G05 | SPLIT |
| TP037 | Fault与互补 | 旧需求奇通道不变与旧手册继承关系冲突，目标新DB结构；G05 | CONFLICT |
| TP038 | 零点事件输出 | P2_008真实DAC接收及P2_010 ADC；必须可分辨零点与周期末Tick，不能仅查ETIM IRQ | MAPPED |
| TP039 | 周期事件输出 | P2_008/010接收端，P2_011模拟输出；不能由ETIM周期pending替代 | SPLIT |
| TP040 | A比较事件输出 | P2_008/010按A时刻观察真实接收完成 | MAPPED |
| TP041 | 自定义事件值输出 | P2_008/010静态事件，P2_009动态事件；错误旧Shadow步骤已纠正 | SPLIT |
| TP042 | 同步输入相位校正 | P1_011运行计数器正常装载；停止和竞态G06 | SPLIT |
| TP043 | 同步输入源选择 | P1_011内部ETIM源；其余Peer G06/G11 | SPLIT |
| TP044 | 同步输出到ETIM | P1_011软件/周期/关闭模式与接收COUNT.LIVE | MAPPED |
| TP045 | 同步输出到ADC | P2_010保留联合触发、真实转换及外部时刻；目标实际是etim2adc_evt，不是CTRPHS SyncOut | MAPPED |
| TP046 | 同步输出到DAC | P2_008双路数字加载、P2_011模拟输出；源11选择文字缺失仍G08，不能称全部源已确认 | SPLIT |
| TP047 | 同步输出到ACMP | P2_008双侧加载、P2_011内部DAC模拟输出、P2_012比较阈值跨越 | SPLIT |
| TP048 | 同步输出到XBAR/PIN | P2_013保留引脚脉冲及源选择；精确延展宽度和bit16关联仍G06，不影响边沿方法 | SPLIT |
| TP049 | IRQ Enable | P0_002强制、P1_007自然、P1_012回卷、P2_003/014 Fault及P2_002外部捕获真实投递 | SPLIT |
| TP050 | IRQ Disable | P0_002及P1_007关闭后静默窗，Service计数独立标注 | MERGED |
| TP051 | 全部IRQ源 | P0_002所有Force位；P1_007比较/周期/捕获，P1_008配置错误，P1_012回卷，P2_003/014 Fault自然路径；同拍组合仍G05/G06 | SPLIT |
| TP052 | IRQ Mask | P0_002 RAW保留且STATUS抑制，不接受最终全零单点证明 | MERGED |
| TP053 | IRQ Unmask | P0_002原pending恢复投递 | MERGED |
| TP054 | 运行时周期立即加载 | P1_009安全窗口双向改变；计数已越过新值G07 | SPLIT |
| TP055 | 运行时比较立即加载 | P1_010先于比较点写入；已越过比较点G07 | SPLIT |
| TP056 | 运行时相位立即加载 | P1_011运行改相位后下一同步加载、P2_007引脚相位；按Case037“和相位测试一致”适配，不虚构相位Shadow位 | SPLIT |
| TP057 | 运行时死区立即加载 | P2_015无在途延迟时运行更新；正在计数的延迟及a支路仍G04/G07 | SPLIT |
| TP058 | 运行时事件立即加载 | P2_009运行安全窗口写入，当前周期真实DAC接收；已越过新值边界仍G07 | SPLIT |
| TP059 | 周期Shadow加载 | P1_009当前周期旧值、下一周期新值的连续边沿 | MAPPED |
| TP060 | 比较Shadow加载 | P1_010未提交/半对负对照与成对提交，不复制旧顺序 | MAPPED |
| TP061 | 事件Shadow加载 | P2_009当前旧点、下一周期新点及重复触发负对照，目标周期边界优先于旧SHWD字段 | MAPPED |
| TP062 | DMA事件请求 | P2_006周期/比较搬运、P2_016真实Capture值到内存；Capture槽请求/连续流仍UNKNOWN G08 | SPLIT |

### 3.2 历史44个Case逐项处置

编号均指R6/R3的`ETIMER_nnn`。参考源码函数同名不一定验证同一件事，下一小节单独追踪。
以下没有标作SUPERSEDED的条目不宣称历史全部覆盖被新Case替代。

| 历史Case | 真实目标/原Oracle问题 | 目标规划与处置 |
|---|---|---|
| 001 | PWM通道输出；步骤周期与“50kHz”期望未给一致时钟 | SPLIT：P1_001数字、P2_001外部；路由全集G02/G04，重算Oracle |
| 002 | PWM分频波形 | SPLIT：P1_001全部合法divider、P2_001外部时间 |
| 003 | 周期设置并看频率 | SPLIT：P0_001字段、P1_001/P2_001普通波形、动态与极限G07/G09 |
| 004 | 相位偏移输出 | SPLIT：P1_011计数装载及P2_007外部相位波形；两种Oracle独立保留 |
| 005 | 占空比调节 | SPLIT：P1_001/P2_001静态参数；运行时更新G07 |
| 006 | A比较模式 | SPLIT：P1_001/P2_001；保留高宽Oracle |
| 007 | A+B及非法比较顺序 | SPLIT：P1_001/P2_001波形、P1_008错误；动态边界G07 |
| 008 | 死区延迟、交换及反相 | SPLIT：P2_005自洽支路正常波形；a支路歧义、动态和窄脉冲G04 |
| 009 | 捕获通道及周期值 | MAPPED：P1_002/003/004覆盖捕获端通道，内部源映射G02 |
| 010 | 捕获输入预分频 | MAPPED：P1_005实际倍率全矩阵 |
| 011 | 捕获上下沿 | MAPPED：P1_002/003；原代码部分“下降沿”仍配置上升，改用非对称刺激 |
| 012 | 绝对/相对时间戳 | SPLIT：P1_002、P1_003、P2_002；不采用旧正脉宽/软件触发接口 |
| 013 | One-Shot | MERGED：P1_004冻结前后比较 |
| 014 | Continuous | MERGED：P1_004后续刷新，不以ISR出现一次代替 |
| 015 | Rearm | MERGED：P1_004新一轮数据及槽序列 |
| 016 | 滤波分频 | SPLIT：P2_004唯一多数窗口跨采样设置；精确分频比和边界G03，旧错误方法不复制 |
| 017 | OS Fault输出及退出 | SPLIT：P2_003正常周期恢复及无Clear对照；同拍竞态G05 |
| 018 | CBC Fault输出及退出 | SPLIT：P2_003正常周期恢复；同拍竞态G05 |
| 019 | “采样转换时刻”，步骤为“删除” | REJECTED：无有效ETIM测试目的；仅排除此条，不删除Fault测试全集 |
| 020 | XBAR Fault输入 | MAPPED：P2_014输入/XBAR上报/实际封波及恢复；目标双输入接线映射G11 |
| 021 | Fault输出高 | SPLIT：P2_003旁路输出高电平；互补/死区组合G05 |
| 022 | Fault输出低 | SPLIT：P2_003旁路输出低电平；互补/死区组合G05 |
| 023 | Fault与互补输出 | CONFLICT：G05；目标优先级未定 |
| 024 | 零点事件外送 | MAPPED：P2_008真实DAC接收；同名FT由3.6另行处置，不按编号机械对应 |
| 025 | 周期事件外送 | SPLIT：P2_008/010接收完成，P2_011外部模拟输出 |
| 026 | A比较事件外送 | MAPPED：P2_008/010按A时刻接收 |
| 027 | 自定义事件外送 | SPLIT：P2_008/010静态及P2_009动态事件 |
| 028 | 同步输入及软件同步到IO | SPLIT：P1_011内部输入、P2_007外部相位、P2_013软件SyncOut引脚；其他Peer输入仍G11 |
| 029 | 同步ADC | MAPPED：P2_010联合触发，按目标实际Event机制保留目的 |
| 030 | 同步DAC | SPLIT：P2_008加载及P2_011模拟输出；目标源11路由说明G08 |
| 031 | 同步ACMP | SPLIT：P2_008内部加载、P2_011内部DAC电压、P2_012比较结果 |
| 032 | 同步XBAR/PIN | SPLIT：P2_013单次/周期外送；延展精确宽度和使能字段关联G06 |
| 033 | 外部周期捕获IRQ，源全集由需求TP051补充 | SPLIT：P2_002加入100毫秒/50%及真实ISR；P1_007、P1_008、P1_012和P2_003/014覆盖其余自然源，不由Force替代 |
| 034 | IRQ屏蔽和清除 | MAPPED：P0_002增加真实投递和选择清除证明 |
| 035 | 周期立即加载 | SPLIT：P1_009运行安全窗口，计数已越过新值G07 |
| 036 | 比较立即加载 | SPLIT：P1_010运行安全窗口，已越过比较点G07 |
| 037 | 相位立即加载 | SPLIT：P1_011运行改相位、下一同步生效，P2_007外部波形；不把标题误解为写CTRPHS即改变COUNT |
| 038 | 事件立即加载 | SPLIT：P2_009真实DAC接收与当前周期时点；已越过事件值边界G07 |
| 039 | 死区立即加载 | SPLIT：P2_015正常安全窗口动态延迟；a支路和在途改值G04 |
| 040 | 周期影子加载 | MAPPED：P1_009运行中过渡周期Oracle |
| 041 | 比较影子加载 | MAPPED：P1_010半对/整对未提交负对照及边界提交 |
| 042 | 事件影子加载 | MAPPED：P2_009修正新旧值相同、遗漏旧事件的原步骤，按目标周期边界证明过渡 |
| 043 | DMA搬运Capture值 | SPLIT：P2_016保留100毫秒/40毫秒高宽及真实Capture到内存，明确采用PRD请求；旧CEVT请求和参考FT连续多槽流仍G08 |
| 044 | 软件锁存、清零 | MAPPED：P0_001；R3仅标题和test_44仍保留有效目的，补齐前后计数Oracle |

### 3.3 目标及参考源码的有效测试语义

本表的“存在”“入口调用”“历史断言”严格分开；没有当前运行日志，不给历史PASS。
函数中错误配置只影响历史Oracle可信度，不能据此删除原测试目的。
表中G03～G08原始待办按3.5节继承复核逐项细化，历史源码事实不因新增PLAN而改写。

| 来源/符号 | 实际刺激、观测和入口事实 | 目标处置 |
|---|---|---|
| V6801 UnitTest/test_etimer.c：TestCase0 | 时基/PWM/DB配置读回；uint8_t status却OR多个高于bit7的错误位，且部分Enable比较有运算优先级风险 | P0_001/P1_001保留时基PWM；DB G04；旧返回SUCCESS不算证明 |
| 同文件：TestCase1 | IRQ Enable/Mask读回，没有真实ISR投递Oracle | P0_002补齐RAW/STATUS及真实ISR；MERGED |
| 同文件：TestCase2 | Capture配置读回使用旧CH13且状态错误位可能截断 | 12通道事实优先，捕获P1_002～005；过滤G03；SPLIT |
| 同文件：TestCase3 | 软件Fault字段读回，不观测最终PWM输出和退出 | G05，UNKNOWN |
| 同文件：TestCase4 | Event值、Shadow及Enable读回 | G07/G08，UNKNOWN |
| 同文件：TestCase5 | 旧CMN_DMA/API、通道13和DMA字段读回 | G08，CONFLICT；不是DMA搬运验证 |
| 同文件：TestCase6 | 同步/ADC/DAC/ACMP路由旧API及字段读回 | G06/G08，UNKNOWN |
| V6801 FunctionalTest/etimer_ft.c：test_1 | P=3000、A约半周期的PWM；只有配置和输出，无外部断言；总入口全部调用被注释 | P1_001/P2_001保留波形目的，SPLIT |
| 同文件：test_8 | 死区延迟10及互补输出，未形成完整自动Oracle | G04，UNKNOWN |
| 同文件：test_9 | ETIM PWM内部到Capture，相对单槽在ISR检查3001；P=3000；使用旧IRQ/IO配置且入口未调用 | P1_003/P1_007；内部路由存在的线索，不作已执行证据 |
| V6801 SmokeTest：TestCase1/2/3 | 1是PWM、2是DB、3是SRPWM内部Capture；入口只调用3；ISR接受3000或3001且关闭IRQ | PWM P1_001/P2_001、DB G04、Peer输入G11；同源内部环回不能宣称引脚电气PASS |
| V6801 FPGATest：ETIMER_1 | SRPWM周期5000、高2000/低3000，经内部输入捕获RFRF绝对四槽，差值断言容差±10 | 数字捕获P1_002；SRPWM Peer语义仍G11，不能用ETIM源声称该Peer路由已覆盖 |
| 同文件：ETIMER_2 | GPIO输入相对RFRR，断言2000/3000/5000±10；IC结构未完整初始化 | P2_002保留外部输入方法，重建初始化与误差预算；MAPPED |
| 同文件：ETIMER_3 | 三通道延迟启动后周期同步，无可判定相位断言 | G06，UNKNOWN |
| 同文件：ETIMER_4 | 死区10并在20/80比较值之间切换，while(1)，无自动波形断言；顶层只调用4，结束标记不可达 | G04/G07，UNKNOWN；不把4个函数全算入口覆盖 |
| V6003/V3101 UnitTest及S6003/S3101 UnitTest | TestCase0..6同类配置目的，接口名、3/14通道、ADC/ACMP选择和DMA API版本不同；均不能从配置返回值推出数据通路通过 | 逐功能复用上列P0/P1与G03～G08；旧宽位错误码和CH13问题不得复制 |
| S6003/S3101 FT：test_1/2/3 | PWM通道、全部64编码分频、运行中改周期；S6003活跃test_1使用频率除法减1，S3101部分路径不减1并遍历边界异常 | 静态P1_001/P2_001，运行过渡G07和极限G09；SPLIT |
| 同两文件：test_4/28 | 相位及SyncOut；S3101 test_28全局选ETIM0却使用另一源，软件脉冲也不能证明正确链路；仅GPIO观察 | G06，UNKNOWN |
| 同两文件：test_5/6/7 | 改A、A_B高宽、A逐增B逐减直到配置错误；部分只有循环/printf或检查到错误即break | 静态P1_001、错误P1_008，动态过渡G07；SPLIT |
| 同两文件：test_8 | 死区上升/下降延迟、输入选择及反相，循环动态比较，无断言 | G04/G07，UNKNOWN |
| 同两文件：test_9 | 内部ETIM PWM周期P=3000，Capture期望3001；S3101 IRQ绑定与禁用通道不一致 | P1_003/P1_007修正本轮身份及IRQ绑定，MERGED |
| 同两文件：test_10 | 遍历cap_pre_div；S3101 ISR对k=1..31检查2002*k附近，S6003只存数组 | P1_005以实际1/2k倍率及独立时钟Oracle规划，不复制未初始化数组或任意容差 |
| 同两文件：test_11/12 | 边沿和时间戳；S3101“下降沿”代码仍为RISING，部分ISR仅true==true/存数组，无正确性判断 | P1_002/P1_003用非对称刺激和逐槽关系，SPLIT |
| 同两文件：test_13/14/15 | One-Shot四槽、Continuous、20次Rearm；部分中断号、槽选择错配且只有ISR进入断言 | P1_004明确冻结、环绕和第二轮数据；MERGED |
| 同两文件：test_16 | 滤波窗口/阈值配置有阈值大于窗口、使能槽与检查槽不一致，不能形成滤波强Oracle | G03，UNKNOWN；保留滤波完整需求 |
| 同两文件：test_17/18/21/23；S3101另test_22 | 软件OS/CBC及高低输出，IRQ中清Fault或关闭IRQ，重复输入与互补；无完整输出恢复断言 | G05，UNKNOWN；OS/CBC行为不由这些源码定案 |
| 同两文件：test_20 | GPIO经XBAR产生Fault刺激，输出观察，无目标路由映射 | G05/G11，UNKNOWN |
| S6003 FT test_24 | 实际ACMP内部DAC更新，源选择与H/L端说明不一致；ISR按比较事件改值，无接收断言 | G08，UNKNOWN；不能机械归入“零点事件通过” |
| S3101 FT test_24 | DAC双路TDAT递增、触发延迟/Shadow设置；只选择部分路由，无双路独立证据 | G08，UNKNOWN |
| 同两文件：test_25 | ETIM事件触发ADC，EOC ISR翻转GPIO，没有转换次数/时刻及数据强Oracle | G08，UNKNOWN |
| 同两文件：test_32 | ETIM同步输出到XBAR/PIN，输出持续约2秒，无自动脉宽断言 | G06/G08，UNKNOWN |
| 同两文件：test_33 | 自然IRQ分支；固定选中的源有限，S3101把P=50000路径称overflow但不足以证明32bit回卷 | P1_007/P1_008及G05/G09；SPLIT |
| 同两文件：test_34 | Force=0xFFF且全Mask，断言RAW=0xFFF、STATUS=0，Clear后RAW=0；无真实ISR | P0_002保留强pending测试并补投递；MAPPED |
| 同两文件：test_40/41 | 动态周期Shadow/Immediate对比及比较Shadow；test_41在写COMPA之前置UPDATE_VLD；没有过渡波形断言 | G07，UNKNOWN；不把错误提交顺序固化为公共动作 |
| S6003 FT test_43 | 四个CAP值DMA到64项数组，DMA启动晚于输入，目的数组为局部栈且异步可能越过生存期，无数据断言 | G08，CONFLICT；保留搬运目的但拒绝该实现作为Oracle |
| S3101 FT test_43 | 全局数组、关闭cache、配置8项后只使能一个DMA通道；仍旧全局请求模型，无数据断言 | G08，CONFLICT |
| 同两文件：test_44 | 调用锁存/清零并把值存入局部变量，无前后关系断言 | P0_001补齐非零、保持、清零和重启观测；MAPPED |
| 两份FT总入口 | S6003仅调用test_32；S3101仅调用test_34；其他定义及声明不等于入口执行 | 不改变上述有效测试意图，也不增加历史PASS |
| S6003/S3101 SmokeTest | 两者有PWM、DB和SRPWM内部Capture三体；S6003入口只调用PWM，注释写64PIN无ECAP而禁用Capture；S3101只调用Capture | 静态PWM/P1与外部P2保留；封装备注不是目标ET6801不支持证据 |
| V6003/V3101 FPGATest/ETIMER/etimer.c | 绝对SRPWM与外部相对捕获均有2000/3000/5000±10断言；同步和DB无强Oracle；V6003入口调用1..4但4不返回，V3101文件无同样顶层入口且SRPWM初始化被注释 | 捕获目的P1_002/P2_002，Peer G11，同步/DB G06/G04；SPLIT |
| V6003/V3101 ChipSieveTest | CS_ECAP_init/SRPWM_entry/ECAP_entry使用旧GPIO软件触发；分别断言约500 Tick高宽和2000 Tick周期 | P2_002保留外部周期/脉宽Oracle；旧触发机制不适用但同一目的仍可测，非NOT_APPLICABLE |
| S3101 ElectricalTest：ETIMER_PWM | P=3、A=1，注释50MHz/25%和5ns；仅输出供仪器观察，没有当前实测 | P2_001保留外部普通波形；目标最高频率/5ns限值G09，SPLIT |
| 同文件：ETIMER_Cap | 最大计数捕获意图；连续模式槽配置与ISR事件错配、打印无断言、无限等待、32位差值乘5有溢出风险 | P2_002只保留普通脉宽测法；最大时长及分辨率G09，不能称已覆盖极限 |
| Coremark/SignalChain/BootROM复制驱动 | 仅驱动/API/README存在，没有新的ETIM测量目的或测试Oracle | CAPABILITY_ONLY/NOT_PUBLIC_FEATURE；不是性能Case证据 |

两份FT中只有声明、没有实现体的历史编号仍由3.2需求表保留，不能因函数缺失删除对应需求。

### 3.4 参考手册裁决

| 来源位置 | 可证明范围 | 对目标的裁决 |
|---|---|---|
| ET6002详细设计PWM/Capture公式（含OMML） | 历史设计给PWM周期、A或B-A占空及绝对/相对捕获计算思路 | 采用数学关系，但其prd单位含混；由目标P=3000断言与M2包含终值解释普通P+1，不直接复制参数 |
| M2第13章计数图，物理153页附近 | 旧器件0..P含终点，A/(P+1)、(B-A)/(P+1) | 普通波形辅助证据；不能证明目标P=0、最大周期、最高频率 |
| M2 Fault段及输出图，物理155～157页附近 | 旧OS退出要求输入无效与清除在同周期，CBC在周期边界退出 | 结合目标同义Fault字段形成P2_003正常路径Oracle；不把旧互补图当目标DB优先级证据 |
| M1/M2滤波段 | 旧连续N+1采样与窗口阈值结构不同 | H6/H7已和H2同为窗口结构，P2_004依据三份SVD；不用旧公式填补CLKPRESCALE |
| M2捕获和事件段，物理160～166页 | 输入预分频针对波形；旧四路DMA、旧同步编码和16时钟事件脉冲说明 | 机制可继承、编码按H2；普通内部同步P1_011和DMA P2_006已规划，外送延展和Capture请求仍G06/G08 |

### 3.5 参考源码待办的继承复核处置

本表是3.3中相应G项的新处置，不把原来的无断言函数记成已有覆盖，也不删除未覆盖部分。

| 3.3来源集合/符号 | 本轮Case对应关系 | 仍未由该Case覆盖的目的 |
|---|---|---|
| 三芯片FT test_3及test_40 | P1_009运行周期立即/Shadow双向更新 | 新周期小于当前计数的异常边界G07、极限G09 |
| FT test_5/6/7、test_41；FPGA ETIMER_4动态比较部分 | P1_010比较立即与Shadow成对提交；P1_001静态占空仍保留 | 已越过比较点的更新G07；不称相同高宽即等价覆盖 |
| FT test_4/28；FPGA ETIMER_3 | P1_011内部同步软件/周期源与相位计数装载 | 外部相位波形、非内部源和同拍优先级G06/G11 |
| FT test_8、Smoke DB体、FPGA ETIMER_4死区部分 | P2_005正常延迟、输入选择、反相和旁路 | a支路歧义、窄脉冲及动态死区G04；动态比较由P1_010另行覆盖 |
| FT test_16及UnitTest滤波配置部分 | P2_004唯一多数阈值短长脉冲；修正threshold大于window和IRQ槽错配 | 精确采样分频、双阈值边界和初始化瞬态G03 |
| FT test_17/18/21/22/23中的软件Fault、test_33的Fault源 | P2_003软件CBC/OS、高低封波、恢复及重复输入自然IRQ | test_23互补组合优先级G05、test_20外部XBAR输入G11 |
| UnitTest DMA选择和普通目标请求字段 | P2_006目标PRD/CMP请求真实搬运 | 两参考FT test_43的Capture值搬运目的仍G08，不能由常数源测试替代 |

新增七个PLAN没有消除所有有效需求；G项只留下上表明确列出的差异、边界和联动，
不再笼统声称整个模块没有原理依据或需要目标RTL才能设计测试。

### 3.6 剩余源码目的的接收端复核处置

时间：2026-09-06 20:50 CST。本表更新3.3/3.5的相应待办，不回写历史运行结论。

| 来源/有效目的 | 新的覆盖对应关系 | 未被等价替代的部分 |
|---|---|---|
| T6 test_24/ETIMER_trigDACConfig及ISR：ACMP内部DAC 2048→1024，观察模拟电压 | P2_008证明真实加载，P2_011把内部DAC模拟观测作为接收类型保留；P2_012附加阈值跨越，不用比较器布尔状态替代原电压波形 | 目标内部DAC测试输出引脚、参考电压及误差为Bench/Mapping；旧先配L侧却选H侧的错误不继承 |
| T3 test_24：双DAC寄存器递增发波，配置反相触发及delay=255 | P2_008双路选择交换/独立加载，P2_011外部双向电平变化；以明确预装值替代无限递增，保证每次变化可追溯 | 旧反相/255是接收配置，不据此声称其精确延迟或反相时序已测；这些Peer配置的完整特性不由ETIM路由Case认证，G08保留时序映射 |
| T6/T3 test_25：ADC EOC翻转GPIO与PWM比较 | P2_010保留源PWM/EOC标记外部时间关系并增加真实EOC/RESULT及无Event负对照 | ISR标记不是采样时刻本身，必须扣除独立采样/转换/服务预算；不套用旧固定GPIO或任意容差 |
| T6/T3 test_32：全局SyncOut经XBAR送PIN | P2_013选中软件单次、未选对照、周期源交换和外送关闭 | EN3 bit16与SyncOut总开关的关系及精确脉宽仍G06；不能把旧enableSyncOut函数名当硬件说明 |
| T6/T3 test_20：GPIO→INPUTXBAR→ETXB产生Fault | P2_014真实输入、XBAR输出、自然Fault及封波恢复，保留未选输入负对照 | 每CORE双输入的ETXB配对公式未证实，映射前不得执行，不复制参考固定GPIO2/ETXB3 |
| 三树FT test_4/28、FPGA ETIMER_3，需求Case037 | P1_011增加运行相位写入及无同步保持；P2_007保留外部相位波形 | 停止计数器时收到同步、同拍清零/同步、非内部同步输入仍G06/G11 |
| FT test_8及FPGA ETIMER_4动态延迟；需求Case039 | P2_015在无在途延迟的运行窗口双向改值，P2_005静态处理保留 | a支路、窄脉冲及正在延迟时改值仍G04；没有用动态比较Case代替动态死区 |
| UnitTest事件配置、需求Case038/042 | P2_008计数事件接收、P2_009立即/Shadow过渡；旧新值不同且每个候选点均有独立完成事实 | 已越过新事件点、与周期/比较同拍的极端值仍G07 |
| FT test_33和需求所有IRQ，Case033明确外部100毫秒周期 | P1_012自然最大值回卷，P2_002补100毫秒/50%与真实捕获ISR；既有P1_007/P1_008/P2_003保留 | 不把最大值附近装载后跨界称为从零跑满整个32bit计数空间；电气极限G09仍在 |
| T6/T3 test_43及需求Case043：四CAP槽DMA到数组、40毫秒高宽 | P2_016逐槽冻结值到内存，外部100毫秒/40毫秒高宽和另一非对称刺激均保留；P2_006普通请求仍单独存在 | 旧每次CEVT请求、持续四槽流和无丢样要求不由冻结数据搬运等价替代，G08明确未完成 |
| 新入口PWM_Compare_Shadow/Source/main.c | 配置A模式并只改A后commit，无波形断言；P1_010覆盖成对提交与过渡，目标要求A/B准备完整优先 | 该示例不是目标B写入可以省略的硬件证据 |
| 新入口PWM_Complement/Source/main.c | a上升延迟、b选另一支路并下降延迟后反相，main调用后无限等待；P2_005覆盖已确认支路 | 使用a处理输出仅是API调用意图，未消解H2/H6/H7的a支路s3说明矛盾；G04保留 |
| 新入口PWM_Out_Fault/Source/main.c | OS、强制LOW，软件输入SET再RESET，main实际调用但无恢复和输出断言；P2_003覆盖并强化 | 无本轮或既有可信执行证据，不能计为Fault PASS |
| 新入口InputCapture_Interrupt及InputCapture_Oneshot/Source/main.c | 外部GPIO、单槽相对捕获、ISR取值及打印，后者有Disable/Enable再Rearm；main均调用；P1_004与P2_002保留模式、Rearm和外部IRQ目的 | 打印prd*5预设200MHz且可能溢出，无数据断言；旧GPIO及IRQ别名不作为目标映射 |

这些拆分按数据路径、独立Observer和资源等级进行。内部数字加载、外部模拟波形和比较器状态
互不替代；冻结Capture搬运与连续Capture请求互不替代。已定义PLAN的Mapping Gap不等于
不存在该功能，仍未确定刺激/判据的边界则继续保持UNKNOWN，整体Gate不通过。

## 第四章 Public Observation / Execution Mapping


### 4.1 字段映射

以下`i`是已解析的目标逻辑通道0..11，`s`是0..3捕获槽；公共Case不直接使用这些名称或地址。

| 公共语义 | ET6801实际端点/编码 | 适配注意事项 |
|---|---|---|
| TIMEBASE.DIVIDER | CORE[i].PWM_CTRL.clkdiv_fac | 实际divider=编码+1；Observation保留raw，另列逻辑值 |
| TIMEBASE.PERIOD_LIMIT | CORE[i].TIMER_CYC | 普通period_ticks=P+1，64位公共单位避免最大值加1溢出；运行极限未闭合 |
| COUNT.LIVE | CORE[i].RLCNT_RPT | 独立硬件实时端点 |
| COUNT.LATCHED | CORE[i].LKCNT_RPT | cntlk触发；必须区分本次锁存与旧值 |
| clear_count | CORE[i].PWM_CTRL.tclr | 脉冲；停止状态等待实时值归零 |
| ENABLE.MODULE | EN0.ETIM_EN[i] | 只读当前通道字段，不拼接为所有Enable状态 |
| ENABLE.TIMER | EN0.TIMER_EN[i] | 不等同于PWM使能 |
| ENABLE.PWM | EN1.PWM_EN[i] | 关闭后的输出电平尚不作公共承诺 |
| ENABLE.CAPTURE | EN1.CAP_EN[i] | 独立Capture使能 |
| ENABLE.CAPTURE_LOAD | CORE[i].CAP_CTRL.cap_load_en | 与CAP_EN分开，关闭加载不意味着关闭计数 |
| CAPTURE.VALUE[s] | CAP_CNT[i].CAP1/2/3/4 | 四个独立32位Observation；SDK getCaptureCnt0对应CAP1，避免一基/零基错配 |
| CAPTURE.NEXT_SLOT | CORE[i].CAP_CTRL.cap_mod_sts | 编码0..3指下一加载槽；冻结还须CAP前后相等 |
| capture_rearm | CORE[i].CAP_CTRL.cap_rearm | 复位MOD4到0并解冻，不据此假定CAP清零 |
| IRQ_RAW.source | CMN_INT[i].INT_RAW_RPT对应bit | 捕获1..4对应bit8..11，其他位见2.1 |
| IRQ_STATUS.source | CMN_INT[i].INT_STATUS_RPT对应bit | Mask后的独立端点 |
| irq Enable/Mask | CMN_INT[i].INT_EN / INT_MASK | 初始配置错误Mask位必须显式处理 |
| irq Force/Clear | CMN_INT[i].INT_FORCE_IND / INT_CLR | 对指定合法bit操作；避免读改写把其他源动作重复触发 |
| IRQ_DELIVERY.* | 平台当前IRQ会话的真实ISR锁存/计数 | 不是硬件寄存器，报告必须单列Service来源 |
| PWM_OUTPUT / STIMULUS_OUTPUT | Bench输出/输入端外部Observer边沿附件 | 目前未绑定引脚、仪器、精度、阈值，属于G10；禁止复用旧固定GPIO号 |
| UPDATE.COMMIT_PENDING | CORE[i].PWM_CTRL.update_vld | A/B写完再置位；硬件清零；读取零不是提交成功的充分证明 |
| update mode | CORE[i].PWM_CTRL.shdw_ug | bit0周期、bit1比较对、bit2事件；P1_009/010对应前两项，P2_009对应事件 |
| SYNC.PHASE / INPUT_ENABLE | CORE[i].CTRPHS / SYNC_CTRL.sync_in_en | 分别记录；实际相位作用通过RLCNT_RPT观测 |
| configure_sync / emit_sync | CORE[i].SYNC_CTRL.synco_sel / sync_src_sel / sw_sync | 内部源编码24+i；软件0、周期1、关闭2或3；不操作全局CFG_ETIM_SYNC_OUT就能验证内部同步 |
| configure_fault / set_fault_input / clear_fault | CORE[i].PWM_CTRL.fault_mode/out/en/sel/sw/clr | sel=0软件，CBC=0、OS=1；fault_clr与CMN_INT.INT_CLR严格区分 |
| FAULT_OUTPUT.LEVEL | 已确认旁路支路的外部Observer | 不从PWM_CTRL.fault_out回显构造Actual |
| filter WINDOW_MAJORITY | CORE[i].CAP_FILTER及EN2滤波使能 | W=SAMPWIN+1、T=THRESH+1，初始化按filinit，采样时钟范围G03；捕获输入预分频固定旁路 |
| configure_delay | OUT[g].DB_SEL及APOS/ANEG/BPOS/BNEG_DLY | g=0..5；b支路自洽，s0b=0自身/1另一支路；s3b=0或3旁路、1处理、2反相；a支路s3文字仍G04 |
| configure_dma_request | CMN[i].DMA.dma_ch_sel，SYSCTRL请求55+i | 1=周期、2=比较；不使用旧API的0..55源枚举 |
| DMA_CHANNEL.COMPLETE / REMAINING | 已有公共DMA契约解析的目标DMA端硬件终态 | ETIM文档不复制DMA寄存器布局；数据源绑定CORE[i].TIMER_CYC固定读，公共动作不得越层 |
| EVENT.SOURCE / VALUE / ENABLE | CORE[i].EVT_TO_ADC.evt_to_adc / EVENT_CNT.pwm_evtcnt / EN3.event_en[i] | 0=PERIOD、1=ZERO、2=A、3=B、4～7=CUSTOM，统一选4；三端点分别保存，不混用EN3 bit16 |
| route_event到独立DAC | CFG_ETIM_DACC.dacc0_trg_sel / dacc1_trg_sel；接收TRG_SEL=2 | 两个nibble分别修改并保留另一路；仅0～10文本自洽，11缺描述保留G08；禁止12/13越界源 |
| route_event到ACMP内部DAC | CFG_ETIM_CMPC[g].sel低/高nibble；ACMP DAC_TRG_SEL对应侧=2 | g=0..10，低nibble为DAC0/H、高nibble为DAC1/L；ETIM源0..11可用，写一个不能清另一个 |
| DAC.LOADED_CODE / TX_DONE | H8 DAC_TDAT_RPT.tdat_load_rpt / DAC_TXDN_RPT.dac_txdn_rpt | 分别12bit和W1C完成；TRG_SET选择寄存器输入、LDMOD=1、TRGEN=1、Mask=0；TDAT_SEL=1会使完成常高，不可用 |
| ACMP_DAC.LOADED_CODE[side] | H9 CMPC_DAC_TDAT.htdat_load_rpt / ltdat_load_rpt | 低12bit为H/DAC0、高12bit为L/DAC1；不是CFG_CMPC_DAC0_TDAT或DAC1_TDAT待发送寄存器 |
| ACMP_DAC.TX_DONE[side] | H9 CMPC_DAC_TXDN_RPT.cmpc_dac0_txdn_rpt / dac1_txdn_rpt | 两位分别W1C；关闭输入流、Ramp和自触发，双侧独立 |
| ACMP.OUTPUT[side] | H9 CMPC_STS.bfr_flt0_rpt / bfr_flt1_rpt | 比较器滤波前实际状态；D5 ACMP_REF_MUX_DAC绑定负端DAC，正端外部输入与参考/误差另行映射 |
| route_event到ADC | H10 VC配置的cfg_sarc_vc_trig_sel；D3 ETIMER0..11=36..47 | 先绑定ADC实例和VC，再选择EOC输出；7bit触发字段不是旧枚举位宽，禁止按旧通道常量写入 |
| ADC.EOC_RAW | H10 CFG_EOC_INT_RAW所选bit；CFG_EOC_INT_SRC_SEL选择目标VC的eoc_out_p | EOC_CTL.cfg_eoc_mod=1为转换结束，关闭EOC额外延迟及反馈触发；不是采样开始/结束事件 |
| ADC.RESULT | H11 SARCn_SOC_RESULT[vc/2].low_result或high_result | 偶数VC取low、奇数取high；结合本轮ADC对齐、位宽和符号约定解析，不直接套旧FIFO数据读取 |
| ADC.TRIGGER_OVERFLOW | H10 CFG_SARC_VC_OVF.cfg_sarc_vc_ovf[vc] | 表示真实硬件触发丢失，CFG_SARC_VC_OVF_CLR按位清；与EOC中断溢出不是同一个端点 |
| XBAR.OUTPUT_LEVEL | H12 ETXB_RPT.etxb_out_rpt[resolved_output] | 必须用实际解析的输出索引；不是etxb_lat_rpt锁存值，也不是SW配置值 |
| route_sync_output / SYNC_OUTPUT.EDGE_TIMES | H2 CFG_ETIM_SYNC_OUT选择12+i，经H12输出XBAR及D6 EXTSYNCOUT枚举到Bench引脚 | i只在0..11；全局旧尾项24/25禁用；外送开关和EN3 bit16关联必须独立核对，不能把驱动函数名当映射 |
| 外部fault_source | CORE[i].PWM_CTRL.fault_sel=1或2，resolved ETXB路由 | sel所称XBAR0/1与具体ETXB索引绑定尚未证实；实施前补映射，不默认第一输出或旧CH3 |
| P2_016 DMA捕获源 | CAP_CNT[i].CAP1..CAP4只读32bit固定源，CMN[i].DMA=1 | 在One-Shot冻结后先CPU读取留证再DMA；只恢复计数产生PRD，不能Rearm或伪装成CEVT请求 |

### 4.2 后续实现前必须满足的映射前提

- CORE和OUT边界使用H1/H3，不调用旧14通道枚举执行全量。
- 选择独立PWM生产者和Capture接收者；CAP输入编码78..89与零基CORE逐项绑定。
- 证明所选输出支路确实绕过死区、反相和Fault；a支路文字冲突未消解前不能列为完整已确认输出矩阵。
- 查询并固定源/接收实际时钟关系与捕获量化上界；历史±10不是可自动复用的误差预算。
- R0锁存/清零和IRQ基础可先实现；R1/P2方法存在不等于目标映射已完成。
- 所有硬件执行必须另列板卡身份、准确命令、期望观察、恢复路径、Artifact路径及破坏性说明，并取得人工门禁。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| ETIM_F_001 | SUPPORTED | 12通道，分级模块/计数Enable | IMPLEMENTATION_GAP | ETIM_P0_001, ETIM_P1_006 |
| ETIM_F_002 | SUPPORTED | 实际1..64，非仅二次幂 | IMPLEMENTATION_GAP | ETIM_P0_001, ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_003 | SUPPORTED | 32位终值；普通P+1，运行极限G09 | IMPLEMENTATION_GAP | ETIM_P0_001, ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_004 | SUPPORTED | CNTLK到LKCNT_RPT，旧驱动可见性待处理 | IMPLEMENTATION_GAP | ETIM_P0_001 |
| ETIM_F_005 | SUPPORTED | TCLR脉冲，观察RLCNT_RPT | IMPLEMENTATION_GAP | ETIM_P0_001 |
| ETIM_F_006 | SUPPORTED | A模式存在；全部输出支路旁路G04 | IMPLEMENTATION_GAP | ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_007 | SUPPORTED | A+B模式存在；只规划普通严格内部点 | IMPLEMENTATION_GAP | ETIM_P1_001, ETIM_P2_001 |
| ETIM_F_008 | SUPPORTED | EN1.PWM_EN；关闭电平不作结论 | IMPLEMENTATION_GAP | ETIM_P1_006 |
| ETIM_F_009 | SUPPORTED | 每槽独立polar | IMPLEMENTATION_GAP | ETIM_P1_002, ETIM_P1_003, ETIM_P2_002 |
| ETIM_F_010 | SUPPORTED | clr_cnt=0，四槽32位值 | IMPLEMENTATION_GAP | ETIM_P1_002, ETIM_P2_002 |
| ETIM_F_011 | SUPPORTED | 每槽clr_cnt；精确误差预算G02 | IMPLEMENTATION_GAP | ETIM_P1_003, ETIM_P2_002, ETIM_P2_016 |
| ETIM_F_012 | SUPPORTED | 旁路1与偶数2..62 | IMPLEMENTATION_GAP | ETIM_P1_005 |
| ETIM_F_013 | SUPPORTED | stop_after=1..4 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_014 | SUPPORTED | stop_after=1..4回绕槽序列 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_015 | SUPPORTED | REARM复位MOD4并解冻 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_016 | SUPPORTED | CAP_LOAD_EN独立于CAP_EN | IMPLEMENTATION_GAP | ETIM_P1_006 |
| ETIM_F_017 | SUPPORTED | 每通道12源Force/Clear | IMPLEMENTATION_GAP | ETIM_P0_002 |
| ETIM_F_018 | SUPPORTED | RAW与STATUS独立，配置错误默认Mask | IMPLEMENTATION_GAP | ETIM_P0_002 |
| ETIM_F_019 | SUPPORTED | 12通道IRQ167..178，真实ISR尚未适配 | IMPLEMENTATION_GAP | ETIM_P0_002, ETIM_P1_007 |
| ETIM_F_020 | SUPPORTED | A/B/Period三个自然源；不含真正回卷 | IMPLEMENTATION_GAP | ETIM_P1_007 |
| ETIM_F_021 | SUPPORTED | Capture四槽bit8..11；外部捕获真实ISR另保留 | IMPLEMENTATION_GAP | ETIM_P1_007, ETIM_P2_002 |
| ETIM_F_022 | SUPPORTED | A≥B配置错误bit3 | IMPLEMENTATION_GAP | ETIM_P1_008 |
| ETIM_F_023 | SUPPORTED | shdw_ug bit0周期边界，H2 | IMPLEMENTATION_GAP | ETIM_P1_009 |
| ETIM_F_024 | SUPPORTED | shdw_ug bit1及update_vld，H2 | IMPLEMENTATION_GAP | ETIM_P1_010 |
| ETIM_F_025 | SUPPORTED | shdw_ug关闭为立即加载；安全窗口，H2 | IMPLEMENTATION_GAP | ETIM_P1_009, ETIM_P1_010, ETIM_P2_009 |
| ETIM_F_026 | SUPPORTED | CTRPHS同步到达时装载；H2/H6/H7 | IMPLEMENTATION_GAP | ETIM_P1_011, ETIM_P1_012, ETIM_P2_007 |
| ETIM_F_027 | SUPPORTED | SYNCO_SEL软件/周期/关闭，H2 | IMPLEMENTATION_GAP | ETIM_P1_011, ETIM_P2_007, ETIM_P2_013 |
| ETIM_F_028 | SUPPORTED | H2 CBC字段存在，正常恢复Oracle沿M2继承；目标未实测 | IMPLEMENTATION_GAP | ETIM_P2_003, ETIM_P2_014 |
| ETIM_F_029 | SUPPORTED | H2 OS和Clear字段存在，正常恢复Oracle沿M2继承；目标未实测 | IMPLEMENTATION_GAP | ETIM_P2_003, ETIM_P2_014 |
| ETIM_F_030 | SUPPORTED | H2 Fault overflow源，M2解释重复输入事件 | IMPLEMENTATION_GAP | ETIM_P2_003 |
| ETIM_F_031 | SUPPORTED | H2/H6/H7窗口结构一致；常规唯一多数阈值 | IMPLEMENTATION_GAP | ETIM_P2_004 |
| ETIM_F_032 | SUPPORTED | H2/H6/H7四链结构一致；当前仅自洽支路可映射 | IMPLEMENTATION_GAP | ETIM_P2_005, ETIM_P2_015 |
| ETIM_F_033 | SUPPORTED | H2每通道PRD/CMP选择与SYSCTRL请求入口 | IMPLEMENTATION_GAP | ETIM_P2_006, ETIM_P2_016 |
| ETIM_F_034 | SUPPORTED | H2 EVT_TO_ADC五类计数事件，接收时刻由H8/H10及M2解释 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_009, ETIM_P2_010 |
| ETIM_F_035 | SUPPORTED | H2 EN3.event_en每通道独立，不等于SyncOut开关 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_010 |
| ETIM_F_036 | SUPPORTED | H2 shdw_ug bit2周期边界生效，更新点不沿旧SHWD编码 | IMPLEMENTATION_GAP | ETIM_P2_009 |
| ETIM_F_037 | SUPPORTED | H2 DACC双nibble及H8触发2；源11漏描述仍G08 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_011 |
| ETIM_F_038 | SUPPORTED | H2 CMPC[11]双侧nibble及H9各侧触发2与加载上报 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_011, ETIM_P2_012 |
| ETIM_F_039 | SUPPORTED | H2计数事件，H10接收结构，D3目标触发36～47 | IMPLEMENTATION_GAP | ETIM_P2_010 |
| ETIM_F_040 | SUPPORTED | H2全局SyncOut与H12/D6 XBAR外送；开关及宽度G06 | IMPLEMENTATION_GAP | ETIM_P2_013 |
| ETIM_F_041 | SUPPORTED | H2 fault_sel=1/2，H12真实输出；双输入配对G11 | IMPLEMENTATION_GAP | ETIM_P2_014 |
| ETIM_F_042 | SUPPORTED | H2直接延迟字段与R6/R3继承更新要求；只准入无在途延迟的安全窗口 | IMPLEMENTATION_GAP | ETIM_P2_015 |
| ETIM_F_043 | SUPPORTED | H2只读CAP槽、PRD请求与DMA总线搬运；不是CEVT请求已确认 | IMPLEMENTATION_GAP | ETIM_P2_016 |
| ETIM_F_044 | SUPPORTED | H2 32bit边界及独立IRQ bit7，M2明确最大值回卷 | IMPLEMENTATION_GAP | ETIM_P1_012 |

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| ETIM_P0_001 | IMPLEMENTATION_GAP | 无Formal实现；需12通道安全Chip Driver和锁存可见性处理 |
| ETIM_P0_002 | IMPLEMENTATION_GAP | 无IRQ会话及Case实现；保持Force与自然事件边界 |
| ETIM_P1_001 | IMPLEMENTATION_GAP | 无实现；另有G02路由/时钟和G04输出支路旁路限制 |
| ETIM_P1_002 | IMPLEMENTATION_GAP | 无实现；逐Capture通道与输入源映射G02 |
| ETIM_P1_003 | IMPLEMENTATION_GAP | 无实现；精确时间戳误差及清零边界量化G02 |
| ETIM_P1_004 | IMPLEMENTATION_GAP | 无实现；Rearm不能依赖旧deinit空操作 |
| ETIM_P1_005 | IMPLEMENTATION_GAP | 无实现；输入倍率必须用实际1/2k，不混淆计数分频 |
| ETIM_P1_006 | IMPLEMENTATION_GAP | 无实现；独立门控及稳定观察窗不可合并为全复位 |
| ETIM_P1_007 | IMPLEMENTATION_GAP | 无实现；真实ISR及首次硬件现场必须绑定当前通道 |
| ETIM_P1_008 | IMPLEMENTATION_GAP | 无实现；默认错误Mask和修正配置后Clear顺序需明确实现 |
| ETIM_P2_001 | IMPLEMENTATION_GAP | 无实现；另有G10外部输出Bench与时钟精度映射，未操作仪器 |
| ETIM_P2_002 | IMPLEMENTATION_GAP | 无实现；另有G10外部输入Bench，不能以旧GPIO/软件捕获API替代 |
| ETIM_P1_009 | IMPLEMENTATION_GAP | 无实现；需无丢边连续Capture及写入窗口现场，目标Safe Window已明确 |
| ETIM_P1_010 | IMPLEMENTATION_GAP | 无实现；需周期基准及两种边沿，不以高宽单值代替相位和成对提交 |
| ETIM_P1_011 | IMPLEMENTATION_GAP | 无实现；内部SYNC编码和目标侧采样传播上界待绑定 |
| ETIM_P2_003 | IMPLEMENTATION_GAP | 无实现；外部旁路输出/仪器G10，继承正常恢复路径不含Fault/DB优先级 |
| ETIM_P2_004 | IMPLEMENTATION_GAP | 无实现；采样时钟编码/周期范围Mapping G03及外部输入Bench G10 |
| ETIM_P2_005 | IMPLEMENTATION_GAP | 无实现；delay时钟Mapping及a支路s3歧义G04，b支路正常路径可先映射 |
| ETIM_P2_006 | IMPLEMENTATION_GAP | 无实现；DMA Peer及请求55+i需绑定；不覆盖Capture槽DMA |
| ETIM_P1_012 | IMPLEMENTATION_GAP | 无实现；最大周期与近边界相位装载，需临界前采样及真实IRQ上界 |
| ETIM_P2_007 | IMPLEMENTATION_GAP | 无实现；外部相位波形及运行写入，Bench与同步传播界G10/G06 |
| ETIM_P2_008 | IMPLEMENTATION_GAP | 无实现；双接收真实加载及完成，独立读窗/延迟映射；DACC源11文本未确认 |
| ETIM_P2_009 | IMPLEMENTATION_GAP | 无实现；必须分辨新旧事件点并能预装第二代码以发现重复触发，禁止只查最终值 |
| ETIM_P2_010 | IMPLEMENTATION_GAP | 无实现；ADC结果/EOC选择和模拟输入/标记延迟待映射，仅Silicon模拟链规划 |
| ETIM_P2_011 | IMPLEMENTATION_GAP | 无实现；含独立及内部DAC模拟输出；内部DAC测试观测路由和模拟预算待绑定 |
| ETIM_P2_012 | IMPLEMENTATION_GAP | 无实现；两侧DAC与比较器模拟输入/参考映射及安全电压源，不能仅看代码回显 |
| ETIM_P2_013 | IMPLEMENTATION_GAP | 无实现；SYNC_OUT选择12+i及EXTSYNCOUT；外送开关/脉冲可测性为G06 Mapping |
| ETIM_P2_014 | IMPLEMENTATION_GAP | 无实现；fault_sel=1/2的目标ETXB配对未绑定，必须先解映射才能执行 |
| ETIM_P2_015 | IMPLEMENTATION_GAP | 无实现；仅文字自洽支路，运行安全窗需要输入/延迟时钟和有界写入事实 |
| ETIM_P2_016 | IMPLEMENTATION_GAP | 无实现；只覆盖冻结CAP值由PRD请求搬运，连续CEVT DMA仍UNKNOWN G08 |

以上主状态选择最先阻塞的实现缺口，Reason中保留并存的Mapping/Bench缺口，不把它们互相覆盖。

## 第七章 Unknown / Conflict解除条件与完成Gate

| Gap | 当前目标证据缺口 | 解除所需最小资料/动作 |
|---|---|---|
| G02 | 具体内部PWM输出支路、同源时钟比、同步采样误差边界未绑定 | 目标时钟树/路由证据及适配映射；禁止从本次DUT测量反向调Expected或容差 |
| G03 | P2_004已给唯一多数窗口短长脉冲Oracle；未映射CLKPRESCALE编码/时钟界，双方同时达阈值、精确边界及高输入初始化瞬态未定 | 分频字段公式可由同结构说明或字段答复补齐；只针对剩余边界继续找适用资料，不再要求整个滤波RTL |
| G04 | P2_005/015已给正常处理和无在途延迟时动态更新；a支路s3复制文字、延迟时钟、窄脉冲及延迟正在计数时改值未定 | 确认a支路实际输入和delay时钟；针对在途更新是否重载/续数及窄脉冲规则取得简短适用说明，不阻塞自洽支路正常设计 |
| G05 | P2_003已按继承模型规划CBC/OS、重复输入和恢复；剩余Fault/DB优先级及同拍撤销/Clear竞态 | 针对组合优先级和同拍事件取得适用解释；正常路径不再等待目标状态机交付，实测不符则登记差异 |
| G06 | P1_011包含运行相位改写，P2_007/013已保留外部相位及SyncOut；剩余停止时/同拍清零、SYNC_OUT越界尾项、EN3 bit16作用对象与精确延展 | 内部24..35、外送已有源12..23可映射；补充bit16到底控制Event还是SyncOut、外送总使能位置和脉宽/传播界，不把旧函数名当结论 |
| G07 | P1_009/010与P2_009/015已覆盖正常立即/Shadow、事件接收及动态延迟；剩余计数已越过新值、重合比较/周期点、在途延迟改值 | 对这些准确边界取得适用说明；禁止使用加大Timeout或读最终值掩盖不确定过渡，不要求RTL文件 |
| G08 | P2_008～012已有接收端方法，P2_016已有冻结CAP搬运；剩余DMA选择3是否Capture或CUSTOM事件、4..7、连续CEVT握手、DACC选择11缺描述 | 所需最小补充是具体DMA选择表和DACC漏项；接收延迟、独立DAC/内部DAC模拟端及ADC输入误差是明确Mapping/Bench。0延迟常规接收不等于Peer反相/255等全部配置已测 |
| G09 | P1_012已有最大周期终点及自然回卷方法；P=0的可观测行为、最高频率/最小脉宽/最大捕获时长及压力限值仍缺适用规范 | 提供目标时钟/电气限值和最小周期边界说明；不移植旧50MHz/5ns，不把近边界加载测试称为全计数空间长稳 |
| G10 | 实际封装/板卡引脚、仪器和时钟精度未作为本任务硬件输入 | 后续独立硬件计划中绑定Bench、误差预算和门禁；普通P2方法保留，不标成硬件不支持 |
| G11 | P2_014的双外部Fault方法完整，但XBAR0/1与每CORE ETXB配对未绑定；其余Capture/SYNC输入Peer仍有未设计项 | 先补双Fault配对和物理路由映射；随后针对SRPWM/CMP/SDFM/CLB/UART/LIN/XBAR等逐路构造刺激及接收Oracle，不能宣称219源已覆盖 |

完成Gate自检：

- Source Coverage：已按登记可访问父根定向搜索；未用其他芯片替代缺失目标时序文档。
- 需求Trace：62个有ID TP、44个历史Case及上述独立源码测试目的均有处置；Case019/TP030的删除占位为唯一无有效目的排除项。
- Feature准入：44项为目标可识别硬件功能；本轮新增项结合H2及目标接收端H8～H12、继承要求/机制形成常规待测Oracle，数量/地址/SDK接口不单造Feature。
- 公共Case：30个PLAN，其中R0三项、R1十一项、R2三项、R4十三项；未注册和未实现。
- 方法审核：已有PLAN给出了输入、7步动作、硬件观测、Oracle、Timeout、Cleanup及报告事实；目标时钟/路由仍须满足映射前提。
- **整体规划Gate：未通过。** G03～G09/G11仍影响适用性、刺激或判据，不能宣布ETIM整体分析完成。
- 新增ETIM实现、Keil、Renode、FPGA、Silicon/HIL：本轮全部NOT_EXECUTED；通用软件门禁不属于ETIM实测，不可替代硬件证据。

后续继续按“同族原理 + 目标SVD差异”收敛上述具体边界及Peer联动，不把ET6801 RTL作为输入前提。
采样/延迟时钟等映射和复杂边界应分开处理；不能因一个边界未知阻塞已有30个PLAN的审核，
也不能把这30个PLAN当作整个ETIM全集已闭合。任何实际硬件执行仍须单独人工门禁。

### 7.1 文档校验记录

时间：2026-09-06 16:47 CST

- `compile_task_context.py scope-check`：通过，仅本目录两份文档。
- `validate_case_plans.py test_case_doc/etim/etim.md`：通过，12个PLAN。
- `check_public_ip_contracts.py`：通过，公共芯片中立边界成立。
- `validate_case_method_contract.py test_case_doc/etim/etim.md`：通过，只证明人审行语法和步骤结构。
- `validate_chip_ip_docs.py`：通过，22个Feature和12个Case映射及公共汇总一致。
- 初次草稿的semantic_ref命名、纯英文报告名称及公共约束文字触发的静态检查错误均已在文档内修正；未修改Checker、Schema或Allowlist。
- 总软件门禁与提交身份单独保存到过程目录`analysis_validation.md`，不将其结果写成ETIM硬件PASS。

可追溯专项任务记录：工作区`artifacts/resource-control/tasks/20260906_164510_889b6fe8.jsonl`、
`20260906_164515_9f6b9fe7.jsonl`、`20260906_164643_47cc0b98.jsonl`及`20260906_164646_ca97ad96.jsonl`。

### 7.2 继承复核文档校验

时间：2026-09-06 18:16 CST

- Scope检查通过：仅修改本目录两份ETIM文档；没有变更实现、其他芯片源码或检查器。
- PLAN、公共IP边界、芯片Feature/Case映射及统一方法行语法专项全部通过，当前33个Feature、19个PLAN。
- 新增七个PLAN逐项检查了输入、七步动作、硬件端点、独立Oracle、负对照、资源和安全清理；3.5保留未被等价覆盖的历史目的。
- 专项记录为工作区resource-control任务`20260906_181515_a5962005`、`20260906_181517_71b54b91`、`20260906_181520_998d3f38`、`20260906_181533_96d6d50f`。
- 本轮总软件门禁与精确提交身份另存过程Artifact `inheritance_validation.md`；不将软件校验写成ETIM实测PASS。

### 7.3 接收端与剩余目的复核校验

时间：2026-09-06 20:56 CST。

- Scope检查及`git diff --check`通过，仅本目录两份文档变化。
- PLAN、公共IP边界、统一方法行语法及芯片映射四个专项全部通过，当前44个Feature、30个PLAN。
- 本轮新增11个PLAN；另扩展P1_011运行相位更新、P2_002外部长周期与真实Capture ISR。3.6保留每个历史目的与剩余非等价部分，不以无断言示例计入实测。
- 专项resource-control任务：`20260906_205525_7c1e512d`、`20260906_205545_a9f94190`、`20260906_205548_4dcb5007`、`20260906_205551_a5ad1f96`。
- 总软件门禁和最终提交身份另存过程Artifact `remaining_coverage_validation.md`；这些校验不改变PARTIAL_ANALYSIS或NOT_EXECUTED硬件状态。
