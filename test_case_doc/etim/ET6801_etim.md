# ET6801 ETIM Chip Analysis & Adaptation

时间：2026-09-06 16:31 CST

目标：ET6801 / ETIM（SDK别名ETIMER），lane=docs。本轮未操作硬件，未修改实现。
公共语义唯一入口：[etim.md](etim.md)。文档记录遵循工作区`DOCUMENTATION_RULES.md`。
源码基线：ATP `codex_dev`，`a6b3e9b79815d11d97469b029063818591bf4f54`；本次分析前工作树干净。

**阶段结论：PARTIAL_ANALYSIS。** 已准入22个Feature并写12个PLAN，0个Formal Case实现、0个实测。
下面的Source Item全集含未闭合需求；不能用22/22映射或12/12机器块合法声称整个ETIM规划完成。
本地SDK中的测试函数、旧手册公式及入口调用均不是本轮FPGA/Silicon PASS。

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

文档先使用ET技能导航和共享toolbox摘要，再定向解析DOCX XML/OMML公式、PDF文字与关键示意图。
目标SVD使用XML结构解析，特别处理本地拆分SVD中cluster内addressOffset已为绝对偏移的方言，
不再次叠加cluster起点。参考手册只用于发现问题和保留测试目的，不能独自证明目标硬件SUPPORTED。
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
尤其DB_SEL的a支路第3级MUX说明错写为b支路；普通PWM源优先选择有直接证据的支路，
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
| TP004 | 相位装载后波形偏移 | CTRPHS/SYNC_CTRL存在；触发边界G06 | UNKNOWN |
| TP005 | A/A+B占空模式 | P1_001和P2_001分别内部与外部高低宽 | SPLIT |
| TP006 | A比较值影响波形 | 同上A模式参数分支，动态更新另G07 | MERGED |
| TP007 | B比较值影响波形 | 同上A_B分支，非法顺序P1_008 | SPLIT |
| TP008 | 死区上升延迟 | OUT.APOS_DLY/BPOS_DLY四链之一，延迟时钟G04 | UNKNOWN |
| TP009 | 死区下降延迟 | OUT.ANEG/BNEG，G04 | UNKNOWN |
| TP010 | 死区输入源选择 | DB_SEL.s0a/s0b存在，完整通路G04 | UNKNOWN |
| TP011 | 死区上升延迟使能 | DB_SEL.s1a/s1b，G04 | UNKNOWN |
| TP012 | 死区下降延迟使能 | DB_SEL.s2a/s2b，G04 | UNKNOWN |
| TP013 | 死区输出选择/反相 | DB_SEL.s3a/s3b文字冲突，G04 | CONFLICT |
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
| TP026 | 滤波时钟分频 | CAP_FILTER.CLKPRESCALE倍数公式缺失，G03 | UNKNOWN |
| TP027 | 滤波阈值 | 目标窗口计数阈值，不等于旧连续采样算法；G03 | UNKNOWN |
| TP028 | 滤波窗口大小 | 窗口+1明确，平局/输出保持规则缺失；G03 | UNKNOWN |
| TP029 | Fault各通道输入 | PWM_CTRL Fault字段明确，激活到输出/恢复G05 | UNKNOWN |
| TP030 | “采样转换结束时刻”Fault | 两份Case019步骤仅“删除”，无ETIM有效刺激/观测；不排除其他Fault需求 | REJECTED |
| TP031 | One-Shot Fault | 软件Fault及恢复步骤历史不一致；目标退出时序G05 | UNKNOWN |
| TP032 | CBC Fault | 需输入撤销与周期边界关系，G05 | UNKNOWN |
| TP033 | 软件Fault触发 | fault_sw存在，不能用IRQ Force替代；G05 | UNKNOWN |
| TP034 | XBAR Fault输入 | 两个目标XBAR选择；刺激路由和恢复G05/G11 | UNKNOWN |
| TP035 | Fault强制高电平 | fault_out=1明确，最终输出优先级和观察点G05 | UNKNOWN |
| TP036 | Fault强制低电平 | fault_out=0明确，最终输出优先级和观察点G05 | UNKNOWN |
| TP037 | Fault与互补 | 旧需求奇通道不变与旧手册继承关系冲突，目标新DB结构；G05 | CONFLICT |
| TP038 | 零点事件输出 | EVT_TO_ADC选择零点存在，接收端观测G08 | UNKNOWN |
| TP039 | 周期事件输出 | 同上周期事件，不能由内部IRQ替代外送事件；G08 | UNKNOWN |
| TP040 | A比较事件输出 | 同上A事件，G08 | UNKNOWN |
| TP041 | 自定义事件值输出 | EVENT_CNT存在，G08/G07 | UNKNOWN |
| TP042 | 同步输入相位校正 | 目标CTRPHS及SYNC_IN_EN；G06 | UNKNOWN |
| TP043 | 同步输入源选择 | 目标路由编码不同于历史；G06/G11 | UNKNOWN |
| TP044 | 同步输出到ETIM | 软件/周期源存在；接收相位Oracle G06 | UNKNOWN |
| TP045 | 同步输出到ADC | 接收ADC真实转换/时间证据G08 | UNKNOWN |
| TP046 | 同步输出到DAC | DACC选择存在，双路触发/更新证据G08 | UNKNOWN |
| TP047 | 同步输出到ACMP | CMPC[11]双nibble选择，G08 | UNKNOWN |
| TP048 | 同步输出到XBAR/PIN | SYNC_OUT/EN3脉冲宽度及端点G06/G08 | UNKNOWN |
| TP049 | IRQ Enable | P0_002强制投递、P1_007自然源投递；Fault/回卷自然源仍G05/G09 | SPLIT |
| TP050 | IRQ Disable | P0_002及P1_007关闭后静默窗，Service计数独立标注 | MERGED |
| TP051 | 全部IRQ源 | P0_002所有Force位，P1_007比较/周期/捕获自然源，P1_008配置错误；Fault/回卷G05/G09 | SPLIT |
| TP052 | IRQ Mask | P0_002 RAW保留且STATUS抑制，不接受最终全零单点证明 | MERGED |
| TP053 | IRQ Unmask | P0_002原pending恢复投递 | MERGED |
| TP054 | 运行时周期立即加载 | 不能由停止配置替代动态生效边界，G07 | UNKNOWN |
| TP055 | 运行时比较立即加载 | 同上，包含A/B过渡，G07 | UNKNOWN |
| TP056 | 运行时相位立即加载 | 新目标没有旧SHWD相位加载位，不能直接排除相位更新目的；G06/G07 | UNKNOWN |
| TP057 | 运行时死区立即加载 | 四链时序和过渡G04/G07 | UNKNOWN |
| TP058 | 运行时事件立即加载 | EVENT_CNT与接收端事件，G07/G08 | UNKNOWN |
| TP059 | 周期Shadow加载 | H2明确边界装载，但完整过渡观测G07 | UNKNOWN |
| TP060 | 比较Shadow加载 | UPDATE_VLD比较对提交存在；历史提交顺序错误，G07 | UNKNOWN |
| TP061 | 事件Shadow加载 | H2有SHDW_UG事件位，接收Oracle G07/G08 | UNKNOWN |
| TP062 | DMA事件请求 | 目标12路通道请求不同于旧4全局输出；G08 | CONFLICT |

### 3.2 历史44个Case逐项处置

编号均指R6/R3的`ETIMER_nnn`。参考源码函数同名不一定验证同一件事，下一小节单独追踪。
以下没有标作SUPERSEDED的条目不宣称历史全部覆盖被新Case替代。

| 历史Case | 真实目标/原Oracle问题 | 目标规划与处置 |
|---|---|---|
| 001 | PWM通道输出；步骤周期与“50kHz”期望未给一致时钟 | SPLIT：P1_001数字、P2_001外部；路由全集G02/G04，重算Oracle |
| 002 | PWM分频波形 | SPLIT：P1_001全部合法divider、P2_001外部时间 |
| 003 | 周期设置并看频率 | SPLIT：P0_001字段、P1_001/P2_001普通波形、动态与极限G07/G09 |
| 004 | 相位偏移输出 | UNKNOWN：G06；不能只读CTRPHS |
| 005 | 占空比调节 | SPLIT：P1_001/P2_001静态参数；运行时更新G07 |
| 006 | A比较模式 | SPLIT：P1_001/P2_001；保留高宽Oracle |
| 007 | A+B及非法比较顺序 | SPLIT：P1_001/P2_001波形、P1_008错误；动态边界G07 |
| 008 | 死区延迟、交换及反相 | UNKNOWN：G04；不沿用旧互补/交换接口 |
| 009 | 捕获通道及周期值 | MAPPED：P1_002/003/004覆盖捕获端通道，内部源映射G02 |
| 010 | 捕获输入预分频 | MAPPED：P1_005实际倍率全矩阵 |
| 011 | 捕获上下沿 | MAPPED：P1_002/003；原代码部分“下降沿”仍配置上升，改用非对称刺激 |
| 012 | 绝对/相对时间戳 | SPLIT：P1_002、P1_003、P2_002；不采用旧正脉宽/软件触发接口 |
| 013 | One-Shot | MERGED：P1_004冻结前后比较 |
| 014 | Continuous | MERGED：P1_004后续刷新，不以ISR出现一次代替 |
| 015 | Rearm | MERGED：P1_004新一轮数据及槽序列 |
| 016 | 滤波分频 | UNKNOWN：G03；历史threshold大于window、IRQ槽错配不能形成Oracle |
| 017 | OS Fault输出及退出 | UNKNOWN：G05 |
| 018 | CBC Fault输出及退出 | UNKNOWN：G05 |
| 019 | “采样转换时刻”，步骤为“删除” | REJECTED：无有效ETIM测试目的；仅排除此条，不删除Fault测试全集 |
| 020 | XBAR Fault输入 | UNKNOWN：G05/G11 |
| 021 | Fault输出高 | UNKNOWN：G05 |
| 022 | Fault输出低 | UNKNOWN：G05 |
| 023 | Fault与互补输出 | CONFLICT：G05；目标优先级未定 |
| 024 | 零点事件外送 | UNKNOWN：G08；同名FT实际配置DAC/ACMP，不按函数编号机械映射 |
| 025 | 周期事件外送 | UNKNOWN：G08；ADC完成须接收端真实证据 |
| 026 | A比较事件外送 | UNKNOWN：G08 |
| 027 | 自定义事件外送 | UNKNOWN：G08 |
| 028 | 同步输入 | UNKNOWN：G06 |
| 029 | 同步ADC | UNKNOWN：G08 |
| 030 | 同步DAC | UNKNOWN：G08 |
| 031 | 同步ACMP | UNKNOWN：G08 |
| 032 | 同步XBAR/PIN | UNKNOWN：G06/G08 |
| 033 | 自然IRQ，含Fault和回卷 | SPLIT：P1_007、P1_008；剩余G05/G09，不能由Force全部替代 |
| 034 | IRQ屏蔽和清除 | MAPPED：P0_002增加真实投递和选择清除证明 |
| 035 | 周期立即加载 | UNKNOWN：G07，停止后配置不是等价替代 |
| 036 | 比较立即加载 | UNKNOWN：G07 |
| 037 | 相位立即加载 | UNKNOWN：G06/G07 |
| 038 | 事件立即加载 | UNKNOWN：G07/G08 |
| 039 | 死区立即加载 | UNKNOWN：G04/G07 |
| 040 | 周期影子加载 | UNKNOWN：G07 |
| 041 | 比较影子加载 | UNKNOWN：G07；必须写好A/B再提交，不照搬历史顺序 |
| 042 | 事件影子加载 | UNKNOWN：G07/G08 |
| 043 | DMA搬运Capture值 | CONFLICT：G08；旧软件捕获API和四路全局DMA选择不可移植，但搬运目的保留 |
| 044 | 软件锁存、清零 | MAPPED：P0_001；R3仅标题和test_44仍保留有效目的，补齐前后计数Oracle |

### 3.3 目标及参考源码的有效测试语义

本表的“存在”“入口调用”“历史断言”严格分开；没有当前运行日志，不给历史PASS。
函数中错误配置只影响历史Oracle可信度，不能据此删除原测试目的。

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
| M2 Fault段及输出图，物理155～157页附近 | 旧OS退出要求输入无效与清除在同周期，CBC在周期边界退出；旧图Fault在互补之后 | 目标新DB链不能直接继承；保留G05，不发布目标优先级 |
| M1/M2滤波段 | 旧连续N+1采样与目标窗口阈值结构不同 | 不能用旧滤波延迟公式填补目标CLKPRESCALE/G03 |
| M2捕获和事件段，物理160～166页 | 输入预分频针对波形；旧四路DMA、旧同步编码和16时钟事件脉冲说明 | 只保留目的；目标DMA/SyncOut/EN3文本冲突仍G06/G08 |

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
| ETIM_F_011 | SUPPORTED | 每槽clr_cnt；精确误差预算G02 | IMPLEMENTATION_GAP | ETIM_P1_003, ETIM_P2_002 |
| ETIM_F_012 | SUPPORTED | 旁路1与偶数2..62 | IMPLEMENTATION_GAP | ETIM_P1_005 |
| ETIM_F_013 | SUPPORTED | stop_after=1..4 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_014 | SUPPORTED | stop_after=1..4回绕槽序列 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_015 | SUPPORTED | REARM复位MOD4并解冻 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_016 | SUPPORTED | CAP_LOAD_EN独立于CAP_EN | IMPLEMENTATION_GAP | ETIM_P1_006 |
| ETIM_F_017 | SUPPORTED | 每通道12源Force/Clear | IMPLEMENTATION_GAP | ETIM_P0_002 |
| ETIM_F_018 | SUPPORTED | RAW与STATUS独立，配置错误默认Mask | IMPLEMENTATION_GAP | ETIM_P0_002 |
| ETIM_F_019 | SUPPORTED | 12通道IRQ167..178，真实ISR尚未适配 | IMPLEMENTATION_GAP | ETIM_P0_002, ETIM_P1_007 |
| ETIM_F_020 | SUPPORTED | A/B/Period三个自然源；不含真正回卷 | IMPLEMENTATION_GAP | ETIM_P1_007 |
| ETIM_F_021 | SUPPORTED | Capture四槽bit8..11 | IMPLEMENTATION_GAP | ETIM_P1_007 |
| ETIM_F_022 | SUPPORTED | A≥B配置错误bit3 | IMPLEMENTATION_GAP | ETIM_P1_008 |

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

以上主状态选择最先阻塞的实现缺口，Reason中保留并存的Mapping/Bench缺口，不把它们互相覆盖。

## 第七章 Unknown / Conflict解除条件与完成Gate

| Gap | 当前目标证据缺口 | 解除所需最小资料/动作 |
|---|---|---|
| G02 | 具体内部PWM输出支路、同源时钟比、同步采样误差边界未绑定 | 目标时钟树/路由证据及适配映射；禁止从本次DUT测量反向调Expected或容差 |
| G03 | CAP_FILTER.CLKPRESCALE未说明是否编码+1；THRESH+1与SAMPWIN+1已知，但双方同时达到阈值、初始化到输出的规则未定 | ET6801当前Revision滤波RTL或时序规范，给出分频、平局和传播边界，随后设计短/长脉冲及阈值边界PLAN |
| G04 | DB_SEL.s3a文本复制b支路；APOS/ANEG/BPOS/BNEG计数时钟、窄脉冲吞吐和更新边界不明 | 当前DB数据通路图/RTL及delay时钟说明，逐支路建立独立外部边沿Oracle，再覆盖6组及延迟边界 |
| G05 | 只有Fault字段，缺目标CBC/OS退出、重复Fault溢出和Fault/DB优先级真值表 | 当前Fault状态机/时序表，明确输入撤销、Clear、周期边界同时发生的行为；补输出与RAW前后证据及安全恢复PLAN |
| G06 | SYNC_OUT选择文字仍列ETIM13/14；EN3公共延展位说明不充分；相位装载优先级不明 | 当前同步MUX表及SW/周期SyncOut脉冲、CTRPHS装载时序；不采用旧18起始输入编码和16周期脉冲假定 |
| G07 | Shadow边界和比较对提交字段存在，但读取配置不能区分当前生效值；立即更新和计数已越过新值时的行为未知 | 当前PWM更新时序/RTL；构造跨更新点的连续边沿证据、A/B原子提交与无提交对照，再形成完整PLAN |
| G08 | DMA字段仅3位却带旧通道描述，0/1/2/3含义对capture槽不明确，4..7未解释；ADC/DAC/ACMP接收链未闭合 | 当前每通道DMA事件真值表与请求脉冲/握手协议、接收端触发映射；保留Destination数据和接收端终态，不只测选择字段 |
| G09 | 目标最高频率/最小脉宽/最大捕获时长没有明确规范；P=0、P=max、计数回卷与周期事件关系不清 | 当前时序与电气限值、计数器边界RTL；外部仪器Oracle及安全有界运行方案，不能移植旧50MHz/5ns指标 |
| G10 | 实际封装/板卡引脚、仪器和时钟精度未作为本任务硬件输入 | 后续独立硬件计划中绑定Bench、误差预算和门禁；普通P2方法保留，不标成硬件不支持 |
| G11 | 其余输入源只有MUX枚举，Peer刺激/接收终态未完成逐路设计 | 针对所选ADC/SRPWM/CMP/SDFM/CLB/UART/LIN/XBAR的目标路由事实与公共Peer契约；逐项增加或复用Case，不能宣称219源已覆盖 |

完成Gate自检：

- Source Coverage：已按登记可访问父根定向搜索；未用其他芯片替代缺失目标时序文档。
- 需求Trace：62个有ID TP、44个历史Case及上述独立源码测试目的均有处置；Case019/TP030的删除占位为唯一无有效目的排除项。
- Feature准入：22项为目标可识别硬件功能；数量/地址/SDK接口不单造Feature；未知功能没有伪造Feature ID。
- 公共Case：12个PLAN，其中R0三项、R1七项、R4两项；未注册和未实现。
- 方法审核：已有PLAN给出了输入、7步动作、硬件观测、Oracle、Timeout、Cleanup及报告事实；目标时钟/路由仍须满足映射前提。
- **整体规划Gate：未通过。** G03～G09/G11仍影响适用性、刺激或判据，不能宣布ETIM整体分析完成。
- 新增ETIM实现、Keil、Renode、FPGA、Silicon/HIL：本轮全部NOT_EXECUTED；通用软件门禁不属于ETIM实测，不可替代硬件证据。

后续最小外部输入是ET6801当前ETIM时序说明或对应Revision RTL，优先补滤波、DB/Fault、Sync/Shadow和DMA。
在这些事实未明确前可以审核基础子集，但不得自动开展未授权的硬件试探来填补规范空白。

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
