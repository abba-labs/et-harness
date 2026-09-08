# ET6801 ETIM Chip Analysis & Adaptation

时间：2026-09-06 16:31 CST

目标：ET6801 / ETIM（SDK别名ETIMER），lane=docs。本轮未操作硬件，未修改实现。
公共语义唯一入口：[etim.md](etim.md)。文档记录遵循工作区`DOCUMENTATION_RULES.md`。
2026-09-08 20:16 CST开发入口修正：来源到方法见3.8，32项开发工作与执行前待定输入分别见4.3；撤销3项可推进、29项整体阻塞的分类。
本轮文档基线为`38c8173064980dff00f526f5dbe55ccc649d51ce`，`codex_dev`初始干净；此处仍为未实现、未操作硬件的设计状态。
源码基线：ATP `codex_dev`，`a6b3e9b79815d11d97469b029063818591bf4f54`；本次分析前工作树干净。

**当前结论（2026-09-06 22:48 CST）：本轮范围收敛完成，必测方法有局部资料问题。**
验收范围为ET6801支持的硅前/回片功能、R6/R3明确要求及目标/参考源码的有效测试目的；不是所有理论竞态或全部输入组合。
保留45个Feature、32个PLAN、0个Formal实现、0个实测。必要问题仅阻塞对应目的；范围外扩展不再否定本轮分析交付。
3.7和第七章为本次裁决；3.3～3.6及7.1～7.4保留分阶段历史，旧UNKNOWN待办不得重新汇总为当前全集阻塞。
本地SDK中的测试函数、旧手册公式及入口调用均不是本轮FPGA/Silicon PASS。

2026-09-06 18:15 CST复核基线为`c5e7c24bba855f044e7f5353f41f53ad7999fb54`，工作树初始干净。
用户明确ETIM为继承IP，目标硬件交付只有SVD，无法提供RTL。本轮据此纠正分析方法：
6003/3101参考资料可以解释稳定机制，ET6801 SVD负责确认功能存在并约束字段、数量和路由差异。
RTL不是必需输入；旧芯片资料不再仅被当作“搜索线索”，但也不能单独证明ET6801硬件已验证。

2026-09-06 20:45 CST继续复核基线为`98e3b2236f1e063e4bf9ba3981a9bddb99740ea1`，初始工作树干净。
本轮只增加ETIM公共/芯片文档内容；相邻ADC/DAC/ACMP/XBAR资料只读，用于接收端Oracle及路由。

2026-09-06 21:24 CST继续复核基线为`211f88eb08b5ded46fa62f9fbe83a97a5c82b82f`，初始工作树干净。
本轮继续四槽连续DMA、PWM Peer输入、时钟链和边界；只修改两份ETIM文档，无硬件或SDK修改。
修正：16:31版本把V6801 ElectricalTest记为NO_MATCH不准确；登记entry自身含54行有效PWM配置体，
21:24复核已固定为T9并纳入P2_001的3 Tick周期、1 Tick高宽参数。源码没有仪器断言不等于没有有效测试目的。

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
| V6801/DFP/Test/ElectricalTest | FOUND | 21:24修正：entry内Electrical_ETIMER_Test配置P=2、A=1；无仪器断言，但单Tick高宽目的有效 |
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
| RDB | SDK/test_case/6003/srpwm.json，仅Case008明确转引的DB正常/动态目的 | `9BFBCEDC7FE854998E6E32CAB18CF4ED170F1317DA4F6C425EF18B891DE793CE` |
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
| H13 | V6801/Tools/RegGen/svd/crg_cfg.svd，时钟源及分频、ETIM门控 | `433FA0DD700AA578E138CE465DB93E44DA6DB3E4105946ADBC84ED8D5A58C9D6` |
| H14 | V6801/Tools/RegGen/svd/hdmac_cfg.svd，P2M/LLI/Burst/硬件握手 | `9576DF2F575F59CB8C4388BB309121EBB5311442B7C4C9DB55B0B3CB5A7BB9C3` |
| H15 | V6801/Tools/RegGen/svd/sysc.svd，CFG_DMA_MUX_MK | `6264EA7385BDEF919ED052AFA51D71D26CF353586BCF554F5B22EB8FA2ACBB7D` |
| H16 | V6801/Tools/RegGen/svd/epwm_cfg.svd，标准精度时基及输出事件 | `9BFAF817E6EAF63850C5625F9F0B20BBF4C7652D347EC90BB8C484F17F8795AA` |
| D9 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_sysctrl.c，DMAMux请求和确认模式 | `44E40BCC54C81E3DA86B8680AD6B8B1C94326297ADDBAC9D1FB98C6850F8A07E` |
| D10 | V6801/DFP/Drivers/ET6x_Driver/Inc/et6x_sysctrl.h，请求55..66与模式枚举 | `5F0F9DF64B6435592B331B6C56270E6A12D5F142F97DDCF15438A445B2CA2DF3` |
| D11 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_crg.c，CPU/BUS/APB频率读取 | `CAD5D97F3A0E4F12D5038408F36469E79F20B92A3608473265EAC360D6EE465F` |
| D12 | V6801/DFP/Drivers/CMSIS/Device/Source/system_et6x.c，启动及SystemCoreClock | `699D287D3FEFE85F0A8158D5A6C4D5875345BCBD3D8D9D54E77B15C8C066DC4A` |
| D13 | V6801/DFP/Drivers/ET6x_Driver/Src/et6x_srpwm.c，SRPWM_initTB | `A86C7FD43AD5A1B93C127207A36E21B3DEC82F16B4F57747EB719716EDD9FFB4` |
| T8 | V6801/DFP/Test/FPGATest/etimer_fpga_test.c，ETIMER_1及ISR | `3CD44ACBDA3C7345309E506C99BAD9BD188C774523E9AD586DB35F94DE5AB2E8` |
| T9 | V6801/DFP/Test/ElectricalTest/electrical_test_entry.c，Electrical_ETIMER_Test | `333859316637AD84C7908A4AADB1AF5AE251D56A6C0BC7425F46081FC6707F17` |
| T10 | V6801/DFP/Test/FunctionalTest/xbar_ft.c，test_6到test_18 | `ED8F8F1A68F3826ABCCC2931BD2AC8D70B5CBE9D75958CF1CEF29B8C3A2429DB` |

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
| CAP_CTRL.cap_in_srcsel | 0..15 INPUTXBAR，16..27 OUTPUTXBAR，28..31 CLU，32..39 UART_RX，40..41 LIN_RX | 数量和路由选择为Capability；外部Capture按Bench绑定，其他输入类的全量刺激为3.7范围外扩展 |
| 同上 | 42..77 SRPWM两路输出；78..89 ETIM1_PWM..ETIM12_PWM | SRPWM0..17的A/B按42+2s+b转换，P2_018覆盖；ETIM零基枚举与SVD一基信号名显式转换，内部路由无需跳线 |
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
| 四链死区 | VERIFIED：三份SVD均有同样s0输入选择、s1上升延迟、s2下降延迟、s3旁路/直出/反相以及四个14bit延迟；a支路s3描述复制b也在两参考SVD存在 | P2_005先覆盖文字自洽的b支路；a仍为必测Q02，不是已证实目标新增机制；正常动态延迟P2_015，窄脉冲按3.7列范围外 |
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
| Capture DMA；H2 CMN.DMA，R6/R3 Case043，T6/T3 test_43 | UNKNOWN：目标3仅写“etimer 1事件”，前面又残留CEVT4..1旧列表，不能证明3=CEVT1或全部捕获事件；4～7无说明。1=PRD可明确使用 | P2_016为冻结端点，21:24新增P2_017为持续更新四槽的PRD快照；旧捕获事件请求仍未覆盖，二者不能合称逐CEVT全集 |

本轮没有发现现行ADC/DAC/ACMP/XBAR公共文档入口。上述Peer动作定义为ETIM Case所需的稳定
协作语义和真实端点，后续必须通过各IP合法Service/Wrap实现；本任务不新增Peer代码或公共架构。
共享CRG只确认ETIM门控和软复位字段，不能由此推出CAP_FILTER与DB的精确时钟编码公式。

### 2.6 连续DMA、Peer输入与时钟链定案

时间：2026-09-06 21:24 CST。以下均为静态资料裁决，非实测。

| 对象 | 已核实事实 | 适配决定 |
|---|---|---|
| 连续四槽数据；H2、H14、H15、D9/D10 | VERIFIED：Capture可CONTINUOUS且不清计数；PRD请求明确；DMA具32bit、P2M、4-item Burst及有限LLI，下一节点可重装源/目的地址 | P2_017以每周期四边沿、周期后读四槽保留连续真实数据，不再以冻结数据代替；每行源回CAP1，目的下一行，链尾停止 |
| DMAMUX确认模式；H15 CFG_DMA_MUX_MK | VERIFIED：0让一次触发响应多个ack直至finish；1屏蔽finish参与，一次触发仅响应一次ack。D10称前者BURST、后者SINGLE，不等于DMA的MSIZE字段 | P2_016逐字及P2_017逐行均明确使用模式1；P2_017的DMA source burst为4项。不能保留默认模式0，否则一次PRD可能提前填完链，制造连续采集假象 |
| DMA选择3/4..7；H1/H2及D1/D2 | UNKNOWN：目标新CMN三位字段与旧全局源枚举不一致；目标UnitTest和参考test_43仍用旧模型，不能由它们推导新编码 | 本轮不生成CEVT请求PLAN、不调用旧enableDMA；这些编码和逐事件ack按3.7属于扩展，不再阻塞明确PRD请求的数据目的 |
| SRPWM输入；H2/H3/H16、D1/D13、T8 | VERIFIED：18个SRPWM实例各A/B共36输入；标准精度UP模式、ZERO/CMPA置清输出，目标T8从SRPWM0_A取得四槽并检查高/低/周期 | 22:48范围修正：36×12只是可表达逻辑空间，不是历史要求的执行分母。P2_018保留SRPWM0/3的A/B到CORE0共4条代表路线（编码42/43/48/49），其中0_A和3_A保留历史选源，B及实例交换用于串路负对照；通道0..11遍历由P1 Capture矩阵承担 |
| T8断言适用性 | VERIFIED：源周期5000、A=2000；绝对R/F/R/F且连续模式；ISR末槽读取四值并关闭IRQ，断言窗口为1990..2010、2990..3010、4990..5010（严格不含端点） | 保留2000/3000/5000目的，不照搬先启动源、固定延时或旧±10；P2_018使用One-Shot稳定读取并单列未选对照。其余Continuous目的由P1_004/P2_017承担 |
| 外部Fault支路；T10 test_6→test_18、H2/H12 | VERIFIED：GPIO29经INXB0、ETXB0进入ETIMER0 Fault，CBC、强制LOW；旧注释称14输出而目标结构为12，SDK的XBAR旧名称须按fault_sel=1解释 | 已落实P2_014的第一条示例路由。第二输入和各CORE配对仍需逐项Mapping，不能从这一个函数外推整表；实测还须读ETXB实际状态及PWM封波 |
| 小周期输出；T9、H2、M2 | VERIFIED：T9终值2/A=1/divider=1即公共period_ticks=3、1 Tick高宽；文件仍include旧et6002.h，不能因此宣称本轮可编译 | P2_001加入3/4/5 Tick周期及最小/最大divider，无需另造Feature；旧S3101终值3/A=1则为4 Tick周期，不再只保留普通波形 |
| 近全量程捕获；H1/H2、M2计数/捕获机制 | VERIFIED：32bit CAP绝对/相对值、全宽计数和独立每槽清零支持每个相邻间隔小于2^32；多槽总时间可超过一次回卷 | P2_002加入M=2^32、间隔M-K/M-2K/M-3K、divider=1/64，真实等待三段时间；先逐相邻模减再64位累加，不用相位加载缩短长间隔测试 |

时钟链不能用一个`SystemCoreClock`常量替代。已把需要的证据分解为：

| 时钟层 | 当前裁决与精确字段 | 后续Mapping输入 |
|---|---|---|
| 外部/内部参考与PLL | H13 CFG_PLLREF_CFG选择参考，CFG_PLLCLK_CFG0选择OSC/PLL；D12的SystemCoreClock初值25MHz，300/200/100MHz配置和SystemClock_Config主体被注释 | 实际Board/FPGA参考频率及容差、启动配置、PLL生效字段快照；注释频率不是现场证据 |
| BUS分频 | H13 CFG_PLLCLK_CFG1.cfg_crg_div_bus合法编码0..7对应1..8；D11 CRG_getBUSClock先固定除3再除字段+1，OSC分支仍调用PLL函数，与H13描述不自洽 | 按实际选源和字段独立计算，不直接把CRG_getBUSClock结果当Oracle；本轮只记录风险，不修共享CRG Driver |
| ETIM计数 | M2 13.4.3明确继承计数源为AHB_BUS1；H13确认ETIM门控，H2计数divider明确为编码+1 | 同ETIM内部通道共享根时钟的数字比例可直接消掉根频率，Fc/Fs=1；跨IP/绝对时间仍需目标ETIM工作时钟到BUS的适用绑定，不能从门控位置推断是哪条BUS |
| SRPWM工作时钟 | H16周期单位为SRPWM工作时钟，D13把标准精度值移位7而非ETIM减1；H13的cfg_sel_pwm_intf只写接口时钟选择，不足以证明SRPWM计数时钟 | 固定Peer标准精度周期语义、实际工作时钟和ETIM/SRPWM时钟比；T8宽容差测试不证明二者永远同频 |
| 捕获滤波采样 | H2 CAP_FILTER.clkprescale为8bit，仅写采样预分频；与M2旧连续N+1稳定滤波器结构不同 | 精确提供输入时钟及编码到采样周期公式；禁止借用ETIM计数divider+1，也不从其他IP同名字段推出公式 |
| 死区延迟 | H2四条14bit延迟与旁路/MUX存在，但无独立精确clock公式 | 提供delay tick来源/倍数和目标支路延迟；不能默认等于分频后的ETIM计数Tick |

上述结论已定向核对目标CRG SVD、CMSIS启动、CRG频率函数、目标ETIM/SRPWM配置及继承手册，
不是“未找代码所以留待以后”。数字同根比例可继续推进；尚缺的是跨域连接和少数字段的精确定义。

边界竞态同样分开处置：M2时基单元段给出立即改周期时COUNT小于新终值继续计数、大于时从0重启；
目标H2只明确立即/Shadow选择，未说明比较采用大于还是等于，以及同拍写入仲裁。
参考T6/T3 test_3有运行写周期和写0，但没有写前COUNT、自然边界身份或输出断言，不能证明具体竞态。
因此已有P1_009继续覆盖严格早于新旧终点；“COUNT已越过新终值是否仍按M2重启”和“恰等于新终值时优先级”
均未定案，但22:48按3.7移出本轮要求范围；不用宽松周期集合把两种结果都判PASS。正常机制可继承不意味着所有竞态已定案。

## 第三章 Source Item Trace

### 3.1 需求Test Point逐项处置

以下TP编号均指R6和R3中的`ETIMER_TP_nnn`，不是新公共ID。两份同义条目按相同目标处置，
参数差异归Capability；每行同时保留原验证目的和为什么没有直接复制历史方法。
`Gnn`与公共`EG-nn`一一对应；SPLIT仅表示目的拆到多个Case，不自动表示未设计。
必要Oracle问题Q01～Q05与执行Mapping分别计数；G07/G09等范围外扩展不再扣减本轮目的覆盖。

| Source Item | 原目的/刺激与观测 | 目标依据及目标Case/Gap | Disposition |
|---|---|---|---|
| TP001 | 各PWM通道输出波形 | H1/H3为12通道；P1_001/P2_001覆盖已确认路由，其余输出支路G04/G02 | SPLIT |
| TP002 | 分频改变波形频率 | 六位实际1..64；P0_001读回、P1_001数字比例、P2_001外部时间 | SPLIT |
| TP003 | 32位周期及输出周期 | P0_001配置边界、P1_001/P2_001普通及单Tick波形；自然回卷P1_012 | SPLIT |
| TP004 | 相位装载后波形偏移 | P1_011计数装载与P2_007引脚相位；后者独立外部Oracle，Bench为G10 | SPLIT |
| TP005 | A/A+B占空模式 | P1_001和P2_001分别内部与外部高低宽 | SPLIT |
| TP006 | A比较值影响波形 | 同上A模式参数分支，正常动态更新P1_010 | MERGED |
| TP007 | B比较值影响波形 | 同上A_B分支，非法顺序P1_008 | SPLIT |
| TP008 | 死区上升延迟 | P2_005正常脉宽；两支路均为必测，a支路及delay时钟Q02，不要求窄脉冲吞吐 | SPLIT |
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
| TP020 | 支持多种输入源可选，波形及计数验证 | 原文125种为旧芯片能力数量且链接Case010实为输入预分频，并未要求源×通道穷举；目标合法表按H2，ETIM P1_002、外部P2_002、SRPWM P2_018保留历史来源类 | SPLIT |
| TP021 | 上升/下降捕获 | P1_002/003非对称波形分别证明极性，P2_002外部复核 | SPLIT |
| TP022 | 绝对/相对时间戳 | P1_002绝对、P1_003逐槽清零、P2_002外部Oracle | SPLIT |
| TP023 | One-Shot | P1_004后续刺激下CAP保持 | MERGED |
| TP024 | Continuous | P1_004多窗口真实刷新 | MERGED |
| TP025 | One-Shot重装 | P1_004 ReArm后首槽及新数据，不以API返回成功替代 | MERGED |
| TP026 | 滤波时钟分频 | P2_004明确实际1/2及一个较大分频；编码和采样时钟公式Q01，禁止把编码2当2分频 | SPLIT |
| TP027 | 滤波阈值 | P2_004唯一多数阈值与T=W，短抑制/长通过；双阈值仲裁不在本轮 | MAPPED |
| TP028 | 滤波窗口大小 | P2_004补8/16/32窗口，其中32为H2五位SAMPWIN+1最大值；高输入初始化瞬态不在本轮 | MAPPED |
| TP029 | Fault各通道输入 | P2_003软件、P2_014双外部输入；全输出支路及组合优先级仍G04/G05 | SPLIT |
| TP030 | “采样转换结束时刻”Fault | 两份Case019步骤仅“删除”，无ETIM有效刺激/观测；不排除其他Fault需求 | REJECTED |
| TP031 | One-Shot Fault | P2_003沿继承周期恢复模型，保留无Clear对照；同拍竞态不在本轮 | MAPPED |
| TP032 | CBC Fault | P2_003输入撤销后周期边界恢复；同拍竞态不在本轮 | MAPPED |
| TP033 | 软件Fault触发 | P2_003真实fault_sw输入及自然IRQ，不使用Force | MAPPED |
| TP034 | XBAR Fault输入 | P2_014选中/未选输入、自然封波和恢复；双外部输入到ETXB的精确绑定为G11 Mapping | MAPPED |
| TP035 | Fault强制高电平 | P2_003延迟/反相旁路下独立电平Observer，互补目的单列TP037 | MAPPED |
| TP036 | Fault强制低电平 | P2_003低电平参数，互补目的单列TP037 | MAPPED |
| TP037 | Fault与互补 | 必测Q03：Case023要求偶通道封低而未施Fault的互补奇通道继续输出；与旧M2关系冲突，目标新DB需确认两端Expected，不得移出范围 | CONFLICT |
| TP038 | 零点事件输出 | P2_008真实DAC接收及P2_010 ADC；必须可分辨零点与周期末Tick，不能仅查ETIM IRQ | MAPPED |
| TP039 | 周期事件输出 | P2_008/010接收端，P2_011模拟输出；不能由ETIM周期pending替代 | SPLIT |
| TP040 | A比较事件输出 | P2_008/010按A时刻观察真实接收完成 | MAPPED |
| TP041 | 自定义事件值输出 | P2_008/010静态事件，P2_009动态事件；错误旧Shadow步骤已纠正 | SPLIT |
| TP042 | 同步输入相位校正 | P1_011运行计数器正常装载、P2_007外部相位；停止和竞态不在本轮 | SPLIT |
| TP043 | 同步输入源选择 | Case028为相位同步及软件SyncOut到IO；P1_011、P2_007/013承接，不据标题推导全部非内部同步源穷举 | SPLIT |
| TP044 | 同步输出到ETIM | P1_011软件/周期/关闭模式与接收COUNT.LIVE | MAPPED |
| TP045 | 同步输出到ADC | P2_010保留联合触发、真实转换及外部时刻；目标实际是etim2adc_evt，不是CTRPHS SyncOut | MAPPED |
| TP046 | 同步输出到DAC | P2_008双路数字加载、P2_011模拟输出；采用文本自洽的0/1源作选择交换，未要求全部源到全部接收器；源11不声明确认 | SPLIT |
| TP047 | 同步输出到ACMP | P2_008双侧加载、P2_011内部DAC模拟输出、P2_012比较阈值跨越 | SPLIT |
| TP048 | 同步输出到XBAR/PIN | P2_013保留引脚脉冲及源选择；精确延展宽度和bit16关联仍G06，不影响边沿方法 | SPLIT |
| TP049 | IRQ Enable | P0_002强制、P1_007自然、P1_012回卷、P2_003/014 Fault及P2_002外部捕获真实投递 | SPLIT |
| TP050 | IRQ Disable | P0_002及P1_007关闭后静默窗，Service计数独立标注 | MERGED |
| TP051 | 全部IRQ源 | P0_002所有Force位；P1_007比较/周期/捕获，P1_008配置错误，P1_012回卷，P2_003/014 Fault自然路径；保留所有合法单源，不额外要求全部同拍组合 | SPLIT |
| TP052 | IRQ Mask | P0_002 RAW保留且STATUS抑制，不接受最终全零单点证明 | MERGED |
| TP053 | IRQ Unmask | P0_002原pending恢复投递 | MERGED |
| TP054 | 运行时周期立即加载 | P1_009运行安全窗口双向改变；Case035只要求改值后频率变化，无同拍要求 | MAPPED |
| TP055 | 运行时比较立即加载 | P1_010运行安全窗口写入；Case036要求占空变化，无已越过比较点要求 | MAPPED |
| TP056 | 运行时相位立即加载 | P1_011运行改相位后下一同步加载、P2_007引脚相位；按Case037“和相位测试一致”适配，不虚构相位Shadow位 | SPLIT |
| TP057 | 运行时死区立即加载 | P2_015无在途延迟时运行更新；a支路及delay时钟Q02仍必需，在途改值不在本轮 | SPLIT |
| TP058 | 运行时事件立即加载 | P2_009运行安全窗口写入，当前周期真实DAC接收；保留首次新事件时点判据，不穷举已越过新值 | MAPPED |
| TP059 | 周期Shadow加载 | P1_009当前周期旧值、下一周期新值的连续边沿 | MAPPED |
| TP060 | 比较Shadow加载 | P1_010未提交/半对负对照与成对提交，不复制旧顺序 | MAPPED |
| TP061 | 事件Shadow加载 | P2_009当前旧点、下一周期新点及重复触发负对照，目标周期边界优先于旧SHWD字段 | MAPPED |
| TP062 | DMA事件请求 | P2_006普通请求、P2_016真实40毫秒高宽数据、P2_017持续四槽到有限数组；按目标明确PRD请求适配数据目的，未要求逐CEVT握手或全部编码 | SPLIT |

### 3.2 历史44个Case逐项处置

编号均指R6/R3的`ETIMER_nnn`。参考源码函数同名不一定验证同一件事，下一小节单独追踪。
以下没有标作SUPERSEDED的条目不宣称历史全部覆盖被新Case替代。

| 历史Case | 真实目标/原Oracle问题 | 目标规划与处置 |
|---|---|---|
| 001 | PWM通道输出；步骤周期与“50kHz”期望未给一致时钟 | SPLIT：P1_001数字、P2_001外部；路由全集G02/G04，重算Oracle |
| 002 | PWM分频波形 | SPLIT：P1_001全部合法divider、P2_001外部时间 |
| 003 | 周期设置并看频率 | SPLIT：P0_001字段、P1_001/P2_001普通及小周期波形，正常运行更新P1_009；无独立竞态要求 |
| 004 | 相位偏移输出 | SPLIT：P1_011计数装载及P2_007外部相位波形；两种Oracle独立保留 |
| 005 | 占空比调节 | SPLIT：P1_001/P2_001静态参数；运行时更新P1_010 |
| 006 | A比较模式 | SPLIT：P1_001/P2_001；保留高宽Oracle |
| 007 | A+B及非法比较顺序 | SPLIT：P1_001/P2_001波形、P1_008错误；不附加同拍竞态 |
| 008 | 死区延迟、交换及反相 | SPLIT：P2_005两支路正常目的，a支路及delay时钟Q02；转引RDB不提供目标MUX/时钟答案，窄脉冲非本轮必测 |
| 009 | 捕获通道及周期值 | MAPPED：P1_002/003/004覆盖捕获端通道，内部源映射G02 |
| 010 | 捕获输入预分频 | MAPPED：P1_005实际倍率全矩阵 |
| 011 | 捕获上下沿 | MAPPED：P1_002/003；原代码部分“下降沿”仍配置上升，改用非对称刺激 |
| 012 | 绝对/相对时间戳 | SPLIT：P1_002、P1_003、P2_002；不采用旧正脉宽/软件触发接口 |
| 013 | One-Shot | MERGED：P1_004冻结前后比较 |
| 014 | Continuous | MERGED：P1_004后续刷新，不以ISR出现一次代替 |
| 015 | Rearm | MERGED：P1_004新一轮数据及槽序列 |
| 016 | 滤波分频及最大窗口 | SPLIT：P2_004补实际2分频与W=32，Q01待采样公式；旧期望计数/时间与步骤不一致，按实测刺激及独立时钟重算，不复制错误数值 |
| 017 | OS Fault输出及退出 | MAPPED：P2_003正常周期恢复及无Clear对照；同拍竞态不在本轮 |
| 018 | CBC Fault输出及退出 | MAPPED：P2_003正常周期恢复；同拍竞态不在本轮 |
| 019 | “采样转换时刻”，步骤为“删除” | REJECTED：无有效ETIM测试目的；仅排除此条，不删除Fault测试全集 |
| 020 | XBAR Fault输入 | MAPPED：P2_014输入/XBAR上报/实际封波及恢复；目标双输入接线映射G11 |
| 021 | Fault输出高 | MAPPED：P2_003旁路输出高电平，互补另见023 |
| 022 | Fault输出低 | MAPPED：P2_003旁路输出低电平，互补另见023 |
| 023 | Fault与互补输出 | CONFLICT：必测Q03，必须确定Fault前后两端波形及恢复；不以旁路高低电平代替 |
| 024 | 零点事件外送 | MAPPED：P2_008真实DAC接收；同名FT由3.6另行处置，不按编号机械对应 |
| 025 | 周期事件外送 | SPLIT：P2_008/010接收完成，P2_011外部模拟输出 |
| 026 | A比较事件外送 | MAPPED：P2_008/010按A时刻接收 |
| 027 | 自定义事件外送 | SPLIT：P2_008/010静态及P2_009动态事件 |
| 028 | 同步输入及软件同步到IO | SPLIT：P1_011内部输入、P2_007外部相位、P2_013软件SyncOut引脚；未要求其他Peer输入全集 |
| 029 | 同步ADC | MAPPED：P2_010联合触发，按目标实际Event机制保留目的 |
| 030 | 同步DAC | SPLIT：P2_008加载及P2_011模拟输出；代表源0/1选择交换，不要求未说明源11 |
| 031 | 同步ACMP | SPLIT：P2_008内部加载、P2_011内部DAC电压、P2_012比较结果 |
| 032 | 同步XBAR/PIN | SPLIT：P2_013单次/周期外送；延展精确宽度和使能字段关联G06 |
| 033 | 外部周期捕获IRQ，源全集由需求TP051补充 | SPLIT：P2_002加入100毫秒/50%及真实ISR；P1_007、P1_008、P1_012和P2_003/014覆盖其余自然源，不由Force替代 |
| 034 | IRQ屏蔽和清除 | MAPPED：P0_002增加真实投递和选择清除证明 |
| 035 | 周期立即加载 | MAPPED：P1_009运行安全窗口，改值后频率变化和过渡均保留；已越过新值为扩展 |
| 036 | 比较立即加载 | MAPPED：P1_010运行安全窗口，占空变化和过渡均保留；已越过比较点为扩展 |
| 037 | 相位立即加载 | SPLIT：P1_011运行改相位、下一同步生效，P2_007外部波形；不把标题误解为写CTRPHS即改变COUNT |
| 038 | 事件立即加载 | MAPPED：P2_009真实DAC接收与当前周期首次新事件时点；已越过事件值为扩展 |
| 039 | 死区立即加载 | SPLIT：P2_015正常安全窗口动态延迟；a支路和delay时钟Q02，在途改值为扩展 |
| 040 | 周期影子加载 | MAPPED：P1_009运行中过渡周期Oracle |
| 041 | 比较影子加载 | MAPPED：P1_010半对/整对未提交负对照及边界提交 |
| 042 | 事件影子加载 | MAPPED：P2_009修正新旧值相同、遗漏旧事件的原步骤，按目标周期边界证明过渡 |
| 043 | DMA搬运Capture值 | SPLIT：P2_016保留100毫秒/40毫秒高宽及真实Capture到内存；P2_017保留历史连续四槽到有限数组目的，二者明确PRD请求；逐CEVT请求不计本轮必测，也不宣称等价 |
| 044 | 软件锁存、清零 | MAPPED：P0_001；R3仅标题和test_44仍保留有效目的，补齐前后计数Oracle |

### 3.3 目标及参考源码的有效测试语义

本表的“存在”“入口调用”“历史断言”严格分开；没有当前运行日志，不给历史PASS。
函数中错误配置只影响历史Oracle可信度，不能据此删除原测试目的。
本表保留早期逐源码判断，G03～G08待办先经3.5/3.6细化，再由3.7按本轮目标裁决；历史UNKNOWN不代表当前仍无方法。

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
| V6801 SmokeTest：TestCase1/2/3 | 1是PWM、2是DB、3是SRPWM内部Capture；入口只调用3；ISR接受3000或3001且关闭IRQ | PWM P1_001/P2_001、DB G04、Peer输入P2_018；内部环回不能宣称引脚电气PASS |
| T8 V6801 FPGATest：ETIMER_1 / ETIMER_1_it | SRPWM0_A驱动四槽RFRF绝对连续捕获并检查约2000/3000/5000；ISR末槽读四值后关IRQ，不持续检查后续组 | SPLIT：P2_018保留SRPWM Peer路径和时间目的；连续更新由P1_004/P2_017承担，不把旧±10当独立误差预算 |
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
| S6003 FT test_43 | 四个CAP值DMA到64项数组，DMA启动晚于输入，目的数组为局部栈且异步可能越过生存期，无数据断言 | SPLIT：P2_016静态双重Oracle、P2_017连续四槽及逐行Oracle；旧请求模型仍CONFLICT G08，拒绝局部数组和晚武装 |
| S3101 FT test_43 | 全局数组、关闭cache、配置8项后只使能一个DMA通道；仍旧全局请求模型，无数据断言 | SPLIT：P2_017保存连续输入和缓存一致性目的，改为有限LLI和唯一行；旧请求编码CONFLICT G08 |
| 同两文件：test_44 | 调用锁存/清零并把值存入局部变量，无前后关系断言 | P0_001补齐非零、保持、清零和重启观测；MAPPED |
| 两份FT总入口 | S6003仅调用test_32；S3101仅调用test_34；其他定义及声明不等于入口执行 | 不改变上述有效测试意图，也不增加历史PASS |
| S6003/S3101 SmokeTest | 两者有PWM、DB和SRPWM内部Capture三体；S6003入口只调用PWM，注释写64PIN无ECAP而禁用Capture；S3101只调用Capture | 静态PWM/P1与外部P2保留；封装备注不是目标ET6801不支持证据 |
| V6003/V3101 FPGATest/ETIMER/etimer.c | 绝对SRPWM与外部相对捕获均有2000/3000/5000±10断言；同步和DB无强Oracle；V6003入口调用1..4但4不返回，V3101文件无同样顶层入口且SRPWM初始化被注释 | 捕获目的P2_018/P2_002分别保留Peer和外部路径，同步/DB G06/G04；SPLIT |
| V6003/V3101 ChipSieveTest | CS_ECAP_init/SRPWM_entry/ECAP_entry使用旧GPIO软件触发；分别断言约500 Tick高宽和2000 Tick周期 | P2_002保留外部周期/脉宽Oracle；旧触发机制不适用但同一目的仍可测，非NOT_APPLICABLE |
| S3101 ElectricalTest：ETIMER_PWM | P=3、A=1，注释50MHz/25%和5ns；仅输出供仪器观察，没有当前实测 | P2_001明确4 Tick周期及1 Tick高宽，不再仅普通波形；目标最高频率/5ns限值G09，SPLIT |
| 同文件：ETIMER_Cap | 最大计数捕获意图；连续模式槽配置与ISR事件错配、打印无断言、无限等待、32位差值乘5有溢出风险 | P2_002补充真实近全量程长间隔及64位累加，禁止只移植普通脉宽；分辨率电气认证限值仍G09 |
| T9 V6801 ElectricalTest：Electrical_ETIMER_Test | P=2、A=1、divider=1，entry确实调用；没有独立观测或数值断言，旧头文件仍存在 | MAPPED：P2_001包含3 Tick周期及1 Tick高宽，旧NO_MATCH已在21:24修正，不表示源码已编译或执行 |
| T10 V6801 XBAR FT：test_6 / test_18 | GPIO29→INXB0→ETXB0→ETIMER0，CBC LOW且无封波观测断言；旧14输出注释与目标不一致 | SPLIT：P2_014第一条实际路线可绑定，另一Fault输入及其余CORE配对仍G11 |
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
| UnitTest DMA选择和普通目标请求字段 | P2_006普通搬运、P2_016冻结Capture、P2_017连续四槽PRD快照 | Capture数据目的已单独规划，旧CEVT请求编码仍G08；不能由常数源测试替代 |

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
| T6/T3 test_43及需求Case043：四CAP槽DMA到数组、40毫秒高宽 | P2_016逐槽冻结值及外部100毫秒/40毫秒高宽保留；P2_017补连续四槽流、先武装及逐行独立Oracle；P2_006仍为普通请求 | 旧每次CEVT请求仍G08；P2_017只证明保护窗内周期快照完整，不冒充逐捕获事件、高速压力或无限流 |
| 新入口PWM_Compare_Shadow/Source/main.c | 配置A模式并只改A后commit，无波形断言；P1_010覆盖成对提交与过渡，目标要求A/B准备完整优先 | 该示例不是目标B写入可以省略的硬件证据 |
| 新入口PWM_Complement/Source/main.c | a上升延迟、b选另一支路并下降延迟后反相，main调用后无限等待；P2_005覆盖已确认支路 | 使用a处理输出仅是API调用意图，未消解H2/H6/H7的a支路s3说明矛盾；G04保留 |
| 新入口PWM_Out_Fault/Source/main.c | OS、强制LOW，软件输入SET再RESET，main实际调用但无恢复和输出断言；P2_003覆盖并强化 | 无本轮或既有可信执行证据，不能计为Fault PASS |
| 新入口InputCapture_Interrupt及InputCapture_Oneshot/Source/main.c | 外部GPIO、单槽相对捕获、ISR取值及打印，后者有Disable/Enable再Rearm；main均调用；P1_004与P2_002保留模式、Rearm和外部IRQ目的 | 打印prd*5预设200MHz且可能溢出，无数据断言；旧GPIO及IRQ别名不作为目标映射 |

这些拆分按数据路径、独立Observer和资源等级进行。内部数字加载、外部模拟波形和比较器状态
互不替代；冻结Capture搬运与连续Capture请求互不替代。已定义PLAN的Mapping Gap不等于
不存在该功能，仍未确定刺激/判据的边界则继续保持UNKNOWN，整体Gate不通过。

### 3.7 本轮要求与历史目的范围裁决

时间：2026-09-06 22:48 CST。基线为ATP `bf150412ec4ec3859a1dd91e1b85d716ef722ec0`，`codex_dev`，开始时干净。
修正对象是3.5/3.6及此前“任一未知项即整体未完成”的判断；不修改历史源码，不把静态分析计为实测。
本轮不再新增PLAN。R6/R3共62个TP、44个Case编号已逐行处置；Case019/TP030仍是唯一无有效目的的删除占位。

| 分类 | 要求/历史依据 | 本轮处置与完成边界 |
|---|---|---|
| 必测：基础计数、PWM、捕获、门控及IRQ | R6/R3 TP001～025、049～053、Case044；各树UnitTest/FT/Smoke | P0_001/002、P1_001～008、P2_001/002；保留12接收通道、64计数分频、合法捕获倍率和所有合法IRQ单源，不因收敛删除基本覆盖 |
| 必测：滤波实际2分频及最大窗口 | Case016明确2分频、MAX窗口；TP026～028 | P2_004补W=32与实际divider=2；保留唯一多数阈值及T=W，短抑制/长通过；采样周期公式Q01仍影响定量刺激 |
| 必测：死区正常选择、使能、延迟、反相及动态改值 | TP008～013/057、Case008/039、FT test_8、FPGA ETIMER_4；Case008转引RDB | P2_005/015保留两支路目的；b可先映射，a输出MUX及delay时钟Q02。RDB的SRPWM_059/091/097只有AHC/更新目的及旧数值（还含单位错误），不能证明目标a支路或delay公式 |
| 必测：Fault正常路径及互补输出 | TP029/031～037、Case017/018/020～023、FT test_17/18/20/21/22/23 | P2_003/014保留CBC/OS、高低输出、重复输入、恢复及XBAR；互补组合单列Q03，未有Expected前不伪造PLAN或计已设计 |
| 必测：运行更新与同步 | TP004/042～044/054～061、Case004/028/035～042，FT/FPGA相位及Shadow目的 | P1_009～011、P2_007/009/013/015保留安全窗口内真实运行变化、首次新事件、外部相位/引脚；本轮不要求COUNT已越点或同拍仲裁。SyncOut正常使能/可观测性仍Q04 |
| 必测：事件到真实接收端 | TP038～041/045～048、Case024～032，FT test_24/25/32 | P2_008～013保留ADC转换、双DAC加载/模拟输出、ACMP两侧DAC/比较结果和外送引脚；这些是输出接收路径，不随Capture输入扩展移出 |
| 必测：Capture真实值到内存、连续四槽 | TP062/Case043，T6/T3 test_43的8/64项有限数组目的 | P2_016保留100毫秒周期/40毫秒高宽双重Oracle，P2_017保留持续加载及逐行数据；目标使用明确PRD和有限LLI，禁止软件触发或冻结值冒充连续数据 |
| 必测：历史输入来源类及选择隔离 | TP020只陈述125源能力和波形/计数；T8、目标Smoke、T6/T3 FT分别选SRPWM0_A/3_A、ETIM1_PWM；FPGA/ChipSieve和Case009等保留外部输入 | P1 Capture遍历CORE0..11；P2_002保留外部；P2_018固定SRPWM0/3的A/B→CORE0四条路线，两种波形及未选活动对照。A/B辅助选择隔离，不展开36×12；实际工作时钟比Q05 |
| 必测：历史电气测试的有效方法 | T9 PWM小周期，S3101 ETIMER_PWM/ETIMER_Cap | P2_001保留3/4/5 Tick周期和1 Tick高宽，P2_002保留近全量程真实等待，P1_012保留真实回卷IRQ；不将这些已有方法重新列成“极限未设计” |
| 范围外：额外输入全集 | 未发现上述基线要求各逻辑/串行/模拟类Capture输入及全部非内部SYNC逐个注入，更未要求源×通道笛卡尔积 | 保留H2合法路由信息；219源、432组合以及CMP/SDFM/CLB/UART/LIN/CLU等扩展不计本轮漏项，不宣称已测或不支持 |
| 范围外：理论竞态及接收Peer配置全集 | 立即加载历史要求不含同拍优先级；滤波正常要求不含双阈值仲裁；DB正常要求不含在途改值 | COUNT已越新值/恰相等、比较与周期重合、Clear/Fault同拍、停止时SYNC、窄脉冲、滤波高电平初始化瞬态、Peer反相/255等精确延迟认证不阻塞本轮 |
| 范围外：旧请求编码与无规范认证 | Case043未要求逐CEVT latency/握手或枚举全覆盖；T9和S3101无目标电气认证规范 | DMA选择3及4..7、逐CEVT流、DACC未说明源11、P=0特例、未定义的最高频率/压力/5ns认证不进本轮；未来明确需求后单独准入 |

“必测方法已设计”与“适配可执行/硬件通过”分开：资源、引脚、实际时钟、DMA上界仍要绑定，但不据此说输入/步骤/Observer完全未设计。
Q03是仍未完整设计的明确历史目的；Q01/Q02/Q04/Q05分别限制相关方法的必要时钟、支路或输出判据。
这些问题不影响其他方法的审核，也不能因本轮范围收敛完成就计成“全部必测方法已闭合”。
本轮没有获准实测，FPGA/Silicon分别保留NOT_EXECUTED，Renode不能替代外部/电气结论。

证据：`artifacts/runs/20260906_223000_etim_scope/`中的资料定位和chip query；本节依赖的源身份由1.2及RDB固定。
22:35修正的doc discovery只在实际`ET6003/03 参考资料`定位两个既有手册；首次缺空格的include-root无效结果不用于结论。

### 3.8 五项必要问题的参考方法落实

时间：2026-09-08 19:02 CST。复用18:49的逐函数检查并重新核对T6、T3、T8及目标FT的SHA256，未发生来源漂移。
以下为当前方法裁决，不回改3.3中早期UNKNOWN记录；Q01～Q05均未因“找到相关代码”自动关闭。
目标FT身份补记：`V6801/DFP/Test/FunctionalTest/etimer_ft.c`，SHA256=`3765ED2C06A49AE9F50C980E0DAAB8125EFA057E308B325327D10A4CCF36BD9F`。

| 问题 / 参考定位 | 代码实际覆盖强度 | 可继承步骤及公共承接 | ET6801映射与仍缺的Oracle |
|---|---|---|---|
| Q01；T6 test_16（1248～1330）及ISR（1236～1246），T3 test_16（1423～1505）；V6003/V3101 UnitTest test_etimer.c（337～350） | T6设置filterClkDiv=2、window=2、threshold=25并Enable；捕获配置EVT0而ISR检查EVT3，无短长Expected断言。T3分频/窗口赋值被注释、threshold=99；UnitTest仅读回 | 保留低输入初始化、配置W/T、开启滤波、输入脉冲及捕获观测目的；P2_004改用合法唯一多数阈值、同一槽身份、逐次旁路正对照和短/长两阶段 | H2给W/T编码与EN2；缺采样根、CLKPRESCALE公式和实际1/2倍率编码，故不能生成Ts_min/Ts_max及合法刺激时间。修正旧配置不等于Q01已答复 |
| Q02；T6 test_8（581～628）、T3 test_8；目标FT test_8（125～162）；T8 ETIMER_4（336～373） | 有输入选择、上升/下降延迟和反相；T8用a s3=1、b s3=2、delay=10并循环改比较20/80，没有延迟测量断言 | P2_005保留来源可区分的两波形、逐极性延迟、反相、旁路；P2_015另保留运行中改延迟值，不把循环改比较值等同于动态延迟 | H2的b支路路径自洽，a支路s3文字仍冲突；D1仅列NONE=0/AFTER=1/INVERT=2，无编码3枚举，不能用它补全MUX表。四DLY时钟根及与计数divider关系仍未知 |
| Q03；T6 test_23（1542～1614）、T3 test_23（1767～1839）；T6 test_17（1353～1402）及ISR（1337起）；V6801 Doc/examples/ETIMER的PWM_Out_Fault、PWM_Complement各Source/main.c | 两test_23均为CBC LOW及50%互补，不是OS；故障动作次序不同且没有双端三阶段断言。test_17单端OS在ISR立即撤销并Clear。Out_Fault为单端25% OS、无恢复；Complement无Fault | 继承“配置互补、单端施Fault、分别看两输出”的目的；既有P2_003仍只承接旁路正常Fault。保留25%/75%、OS LOW、保持/撤销未Clear/有效Clear恢复的待答矩阵，不填猜测Expected | H2 Fault与DB字段存在，但不证明Fault在DB前后及是否影响另一端。Q03关闭须得到两端三阶段Expected及适用依据，再补既有Fault方法并审核；当前不能记入该PLAN已设计覆盖。示例readme仍为ET6002 Pack/EVB，目录归属不等于6801执行 |
| Q04；T6 test_32（2337～2414）、T3 test_32（约2540～2619）及各Driver enableSyncOut | 有PERIOD SyncOut→全局选择→OPXB EXTSYNCOUT→GPIO2链；关闭PulseStretch后Enable，延时约2秒供观察，无脉宽断言及关闭负对照。旧Driver设置EN3的SYNC_OUT_EVENT_EN | P2_013继承完整外送链，增加软件一次、未选源、两周期源交换、源运行但外送关闭等独立观察 | 目标源只取12+i（i=0..11），XBAR/引脚经H12与Bench绑定，不复制GPIO2。EN3 bit16作用及正常可测脉冲界仍Q04；旧API意图不能裁决冲突描述 |
| Q05；T8 SRPWM初始化（22～58）、ETIMER初始化（139～178）、ETIMER_1断言（242～259）；V6003/V3101 FPGA ETIMER/etimer.c对应断言（116～134 / 88～104） | 三树有2000/3000/5000高宽、低宽、周期的严格±10窗口断言；V3101 SRPWM初始化调用被注释。T8真实采用SRPWM0_A与四槽R/F/R/F，不是ETIM自环 | P2_018继承非对称高低宽及完整周期，改为先武装One-Shot再启动、冻结后读四槽，加入第二波形和未选活动对照；Continuous另由P1_004/P2_017保留 | 4.1已有42/43/48/49代表路线；SRPWM标准精度周期单位不能套ETIM的P+1。缺ETIM/SRPWM工作时钟关系及捕获量化上界，历史±10没有推导，不能直接发布为capture_error_ticks |

这些方法均已定位到既有PLAN或明确未完成目的，不新增Case以掩盖缺口。
T6总入口仅test_32、T3仅test_34、目标FT调用均注释；入口事实不改变有效目的，也不构成当前PASS。
可实施的方法以公共PLAN为准，不要求后续开发者再次从历史错误程序中推测测试意图。

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
| filter WINDOW_MAJORITY | CORE[i].CAP_FILTER及EN2滤波使能 | W=SAMPWIN+1、T=THRESH+1，Wmax=32；实际采样divider=1/2及较大合法值的编码待Q01，不混淆捕获输入预分频（固定旁路） |
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
| P2_016 DMA捕获源 | CAP_CNT[i].CAP1..CAP4只读32bit固定源，CMN[i].DMA=1；H15确认模式1 | 在One-Shot冻结后先CPU读取留证再DMA，source burst=1；只恢复计数产生PRD，不能Rearm或伪装成CEVT请求 |
| P2_017 连续DMA | CMN[i].DMA=1、SYSCTRL请求55+i、H15确认模式1；DMA P2M/32bit/HW SRC，source burst=4，每LLI 4字 | 每节点从CAP1递增到CAP4，下一节点回到CAP1且换目的行；节点有限且末尾停止。Snapshot最坏耗时含ack、总线争用和LLI装载，必须小于后续首槽覆盖窗 |
| P2_018 PWM Peer输入 | 合法编码42+2s+b；本轮s=0/3、b=0/1到CORE0，即42/43/48/49四条路线 | 36×12不作执行分母；每条两波形及未选对照。SRPWM标准精度UP、HR bypass及ZERO/CMPA动作由Peer负责；全部Capture接收通道另由P1矩阵遍历 |
| P2_014 首条Fault路线 | T10的GPIO29/INXB0/ETXB0，CORE0.fault_sel=1 | H12实际ETXB输出上报与外部封波并行证明；未指定板卡不能把此参考引脚写成已接线Bench |
| P2_002 长间隔 | TIMER_CYC=0xFFFFFFFF；CAP四槽绝对或逐槽clr_cnt；实际divider=1/64 | M用64位2^32表示，每段M-kK小于M；DUT要真实等待整个间隔，不能借P1_012近回卷相位预加载方法缩短等待 |

### 4.2 后续实现前必须满足的映射前提

- CORE和OUT边界使用H1/H3，不调用旧14通道枚举执行全量。
- 选择独立PWM生产者和Capture接收者；CAP输入编码78..89与零基CORE逐项绑定。
- 证明所选输出支路确实绕过死区、反相和Fault；a支路文字冲突未消解前不能列为完整已确认输出矩阵。
- 查询并固定源/接收实际时钟关系与捕获量化上界；历史±10不是可自动复用的误差预算。
- R0锁存/清零和IRQ基础可先实现；R1/P2方法存在不等于目标映射已完成。
- 所有硬件执行必须另列板卡身份、准确命令、期望观察、恢复路径、Artifact路径及破坏性说明，并取得人工门禁。

### 4.3 逐Case开发工作与执行前输入

时间：2026-09-08 20:16 CST。以下清单逐项核对公共PLAN的输入、七步方法、端点、Oracle、资源及清理。
这是文档分析结论，不是新增运行状态；第五/六章仍为45/32个IMPLEMENTATION_GAP。
修正：缺Case/Driver/Service/Wrap、IRQ绑定、内部路由或Peer公共动作是本轮要完成的实现工作，不是要求用户先补资料的理由。
板级引脚、接线及仪器型号/能力是实测配置；它们未绑定时不执行HIL，但不阻止已确定方法及软件链路开发。
只有实际UNKNOWN的硬件语义或无法固定的独立Oracle限制对应目的/参数的Formal发布，不限制其他已知动作开发；不得为凑完整Case发布猜测判据。
表中“时间预算待定”保留量化、传播、事务等实际未定上界，不意味着必须重新索要手册/RTL；先使用已有SVD、适用继承资料和目标实现的可证明界。

| Public Case | 开发处置 | 已有方法 / 核心Oracle | 实现工作及执行前必须固定的输入 |
|---|---|---|---|
| ETIM_P0_001 | 首批实现 | 2.1/4.1、T6/T3 test_44；配置读回、运行增加、停止保持、锁存包络及非零清零 | 安全约束12通道、CNTLK可见性、TCLR完成及有效复位；给出满足32 Tick且不回卷的有界观察窗。不以精确频率判通过，divider此处仅配置覆盖 |
| ETIM_P0_002 | 首批实现 | T6/T3 test_34；单源RAW/STATUS、双源选择Clear及真实ISR | 绑定12通道IRQ167～178和12源，隔离Force与自然生产者，ISR先取现场再停止投递；证明10ms静默窗/1s截止机制，不借Force证明自然事件 |
| ETIM_P1_001 | 实现推进；时间预算待定 | 3.3 FT test_1/2/6/7/9；两模式高低宽/周期及全部分频 | G02/Q05捕获量化上界、源到接收路由和G04旁路；同ETIM根频率可消去，但量化误差不能消去，不能套±10 |
| ETIM_P1_002 | 实现推进；时间预算待定 | 3.3 test_11/12；非对称绝对四槽及极性关系 | G02逐Capture通道路由、输入确实来自独立源、已固定capture_error_ticks；按四种极性序列确定逐段Expected |
| ETIM_P1_003 | 实现推进；时间预算待定 | 3.3 test_9/11/12；逐槽清零后的单段/累积时间 | G02/Q05捕获与清零边界误差预算、路由；不能用软件统一减首槽代替硬件清零 |
| ETIM_P1_004 | 实现与内部映射 | 3.3 test_13/14/15；冻结、持续刷新、Rearm第二轮及槽外保持 | G02可用内路由和不回卷的八源周期观察窗；核心Oracle是保持/变化，无需额外引入精确高低宽误差；修复deinit空操作及会话身份后复核 |
| ETIM_P1_005 | 实现推进；时间预算待定 | 3.3 test_10；输入实际1及偶数2..62的三段间隔 | G02时钟比例/量化界及全部合法倍率映射；等待按最大倍率计算，计数divider全程保持 |
| ETIM_P1_006 | 实现推进；时间预算待定 | 3.3 Enable目的；三种独立门控及恢复周期 | G02路由、稳定观察窗及恢复周期误差界；仅计数保持部分可复用P0_001，不能据此把完整Case标成候选 |
| ETIM_P1_007 | 实现与内部映射 | 3.3 test_9/33及IRQ要求；比较/周期/四槽自然ISR | 捕获分支G02路线、首次现场绑定及有界ISR窗口；不要求新增精确脉宽Oracle。只实现比较/周期分支不算该Case全完成 |
| ETIM_P1_008 | 首批实现 | 2.1、3.3 test_7/33；A<B无错、A≥B置错、修正后Clear不复发 | 显式处理默认bit3 Mask，保持输出关闭，合法/等于/大于分支及两周期观察完整；不需要输出路由或捕获时间误差 |
| ETIM_P2_001 | 实现推进；时间预算待定 | 3.3 T9/电气源码；外部周期/高宽含单Tick参数 | Q05目标计数根与实际频率/容差、G04输出旁路、G10引脚/仪器；最短点总误差小于半Tick，不以长脉宽替换 |
| ETIM_P2_002 | 实现推进；时间预算待定 | 3.3 FPGA ETIMER_2/ChipSieve；外部间隔及真实ISR、近量程等待 | Q05计数频率/捕获预算、G10输入端测量；据最坏误差固定K和有界长会话，真实等待三段，不用相位预加载缩短 |
| ETIM_P1_009 | 实现推进；时间预算待定 | 3.5 test_3/40；旧/过渡/新周期连续边沿 | G02捕获界、无丢边连续Observer及写入前后COUNT窗口；已确定周期边界语义，无需重开已越点竞态研究 |
| ETIM_P1_010 | 实现推进；时间预算待定 | 3.5 test_41；半对/未提交/提交/立即边沿位置 | G02捕获界、周期基准和两极性连续采集、两次写入均在安全窗；同高宽不等于同相位 |
| ETIM_P1_011 | 实现推进；时间预算待定 | 2.4及3.5 test_4/28/ETIMER_3；自由区间与相位区间 | Q05/G06同步传播及读事务独立上界、24+i内部源映射；两Expected区间不重叠。内部路径不必等待Q04外送bit16答案 |
| ETIM_P2_003 | 实现；实测配置待绑定 | 3.8 Q03、2.4继承正常Fault；旁路封波/撤销/Clear恢复和overflow | G04已确认旁路、G10外部Observer及周期动作窗先绑定。当前旁路Case不被Q03整体阻断，但其结果绝不能关闭Q03互补目的 |
| ETIM_P2_004 | 实现已知动作；Q01局部待定 | 3.8 Q01；旁路可捕获、短抑制、长双极性通过 | 先答Q01以生成合法分频及Ts上下界，再绑定G10脉冲/测量误差；不是仅缺接线，不能标DEFERRED |
| ETIM_P2_005 | 实现已知动作；Q02局部待定 | 3.8 Q02；输入身份、逐极性延迟、反相及旁路 | Q02 delay Tick及a支路MUX，G10多端同步测量；b支路只能先做映射，不能据此宣布两支路必测目的全部准备好 |
| ETIM_P2_006 | 实现与DMA集成 | 2.4/4.1目标PRD/CMP及公共DMA；固定读回值搬运和停止负对照 | G08请求55+i、字段1/2、每请求一字及公共DMA资源/缓存契约落地；源读回即数据Oracle，不依赖捕获精确时钟或未知CEVT编码 |
| ETIM_P1_012 | 实现推进；时间预算待定 | 2.5、M2继承回卷；临界前高值/后低值、自然bit7和普通周期对照 | Q05/G06一次同步、临界前采样及ISR上界，以其选M；不能只Force bit7，也不能略过高值零pending现场 |
| ETIM_P2_007 | 实现推进；时间预算待定 | 3.6相位目的；双输出下一同步前后相位轨迹 | Q05/G06同步偏移/误差和写入窗、G04双旁路、G10双端波形；不需Q04外送SyncOut引脚路径 |
| ETIM_P2_008 | 实现推进；时间预算待定 | 2.5及3.6 test_24；双接收LOADED_CODE/TX_DONE和选择交换 | G08两类Peer公共动作、独立接收/读事务界及两源路由；必须分辨ZERO/PERIOD一Tick间隔，不能只检查最终新值 |
| ETIM_P2_009 | 实现推进；时间预算待定 | 3.6 Case038/042；新旧候选点接收及重复触发对照 | G08 Peer动作、独立接收延迟和Clear/再预装窗口；四个更新实例均能采当前与后续周期，不能丢第二候选点 |
| ETIM_P2_010 | 实现；模拟及时间预算待定 | 3.6 test_25；转换RESULT/EOC及外部标记时间 | G08 ADC触发36～47与EOC选择、转换/ISR上界，G10输入参考及误差；Q05支持源时间换算。未确定模拟预算前非纯Bench缺口 |
| ETIM_P2_011 | 实现；模拟及时间预算待定 | 3.6 test_24；独立/内部DAC真实模拟变化及加载 | G08 Peer公共动作、加载/建立上界、内部DAC实际可观测路线，G10参考/负载/误差；数字加载不能代替模拟输出 |
| ETIM_P2_012 | 实现；模拟及时间预算待定 | 2.5/3.6内部DAC目的；低高低阈值与实际比较状态 | G08两侧映射和接收上界，G10安全输入/参考/迟滞及误差预算；路线/参数定案后才属于缺仪器的执行问题 |
| ETIM_P2_013 | 实现已知动作；Q04局部待定 | 3.8 Q04；软件一次、周期/源交换和关闭负对照 | Q04真正外送开关及可观测下界，G10 XBAR到引脚/Observer，Q05源时间预算；不照搬旧enableSyncOut |
| ETIM_P2_014 | 实现；实测配置待绑定 | 3.6 test_20/T10；未选输入对照、XBAR实值及封波恢复 | G11双Fault输入到各目标通道绑定、G04旁路、G10安全双刺激；T10仅首条路线。当前旁路恢复不证明Q03互补 |
| ETIM_P2_015 | 实现已知动作；Q02局部待定 | 3.8 Q02及3.6 Case039；本周期安全窗口更新真实delay值 | Q02时钟/MUX、G10输入输出Observer及目标写事务界；先证明无在途延迟，再执行8↔32双向更新 |
| ETIM_P2_016 | 实现推进；时间预算待定 | 3.6 test_43；真实外部捕获Oracle加冻结槽精确DMA比对 | Q05捕获时钟/量化、G08 PRD每字请求/公共DMA、G10外部输入；仅搬运值相等不能替代捕获时间正确 |
| ETIM_P2_017 | 实现推进；时间预算待定 | 2.6及3.6 test_43；8/64轮连续四槽唯一行 | Q05捕获/周期参考预算、G04参考输出、G08模式1/有限LLI/最坏整行及描述符时间、G10有限序列源；总误差须小于8 Tick并满足全部保护窗 |
| ETIM_P2_018 | 实现推进；时间预算待定 | 3.8 Q05；四代表路线、两波形及未选活动隔离 | Q05跨IP工作时钟比与capture_error_ticks、Peer标准精度公共动作及4.1路线；历史±10和ETIM自环均不能代替 |

计数核对：合计32个PLAN，0个SPEC、0个注册实现、0个实测；P0_001/P0_002/P1_008只是首批实现顺序，不是唯一允许开发的子集。
Q01～Q05保留实际未知部分；G02/G08/G10/G11等逐项区分源码实现、内部映射、时间预算与物理执行配置，不汇总为29项不能编码。
Q03互补目的尚未形成完整方法，另列于3.8，不塞进现有旁路Case后冒称32项覆盖全部必测目的。

后续顺序：先开发计数/IRQ/比较错误链路及无硬件回归，再推进P1_004/P1_007的捕获路线、有界窗口和P2_006的DMA绑定；随后推进定量捕获、PWM更新和跨IP方法。
用户已允许文档修正并本地提交后继续开发；代码工作另编译Task Context，真实硬件仍未授权。局部Q未知不伪造关闭，已知动作不停止开发。
外部仪器只有示波器和函数发生器，全部Case按公共文档5.2构造；ADC/DAC/ACMP电压观测使用示波器，安全DC/脉冲/有限序列刺激使用经型号确认具备相应能力的函数发生器。
现有设备精度或模式不足只限制对应实测参数，不引入其他仪器，不改变原始Expected或宣称电气精度覆盖。
若需要用硬件诊断补事实，须另提具体门禁；诊断实测不能反向自定正式Case Expected，也不替代适用规范的必要上界。


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
| ETIM_F_009 | SUPPORTED | 每槽独立polar | IMPLEMENTATION_GAP | ETIM_P1_002, ETIM_P1_003, ETIM_P2_002, ETIM_P2_018 |
| ETIM_F_010 | SUPPORTED | clr_cnt=0，四槽32位值 | IMPLEMENTATION_GAP | ETIM_P1_002, ETIM_P2_002, ETIM_P2_018 |
| ETIM_F_011 | SUPPORTED | 每槽clr_cnt；精确误差预算G02 | IMPLEMENTATION_GAP | ETIM_P1_003, ETIM_P2_002, ETIM_P2_016 |
| ETIM_F_012 | SUPPORTED | 旁路1与偶数2..62 | IMPLEMENTATION_GAP | ETIM_P1_005 |
| ETIM_F_013 | SUPPORTED | stop_after=1..4 | IMPLEMENTATION_GAP | ETIM_P1_004 |
| ETIM_F_014 | SUPPORTED | stop_after=1..4回绕槽序列 | IMPLEMENTATION_GAP | ETIM_P1_004, ETIM_P2_017 |
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
| ETIM_F_033 | SUPPORTED | H2每通道PRD/CMP选择与SYSCTRL请求入口 | IMPLEMENTATION_GAP | ETIM_P2_006, ETIM_P2_016, ETIM_P2_017 |
| ETIM_F_034 | SUPPORTED | H2 EVT_TO_ADC五类计数事件，接收时刻由H8/H10及M2解释 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_009, ETIM_P2_010 |
| ETIM_F_035 | SUPPORTED | H2 EN3.event_en每通道独立，不等于SyncOut开关 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_010 |
| ETIM_F_036 | SUPPORTED | H2 shdw_ug bit2周期边界生效，更新点不沿旧SHWD编码 | IMPLEMENTATION_GAP | ETIM_P2_009 |
| ETIM_F_037 | SUPPORTED | H2 DACC双nibble及H8触发2；源11漏描述仍G08 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_011 |
| ETIM_F_038 | SUPPORTED | H2 CMPC[11]双侧nibble及H9各侧触发2与加载上报 | IMPLEMENTATION_GAP | ETIM_P2_008, ETIM_P2_011, ETIM_P2_012 |
| ETIM_F_039 | SUPPORTED | H2计数事件，H10接收结构，D3目标触发36～47 | IMPLEMENTATION_GAP | ETIM_P2_010 |
| ETIM_F_040 | SUPPORTED | H2全局SyncOut与H12/D6 XBAR外送；开关及宽度G06 | IMPLEMENTATION_GAP | ETIM_P2_013 |
| ETIM_F_041 | SUPPORTED | H2 fault_sel=1/2，H12真实输出；双输入配对G11 | IMPLEMENTATION_GAP | ETIM_P2_014 |
| ETIM_F_042 | SUPPORTED | H2直接延迟字段与R6/R3继承更新要求；只准入无在途延迟的安全窗口 | IMPLEMENTATION_GAP | ETIM_P2_015 |
| ETIM_F_043 | SUPPORTED | H2只读CAP槽、PRD请求及H14/H15有限链；冻结和连续快照均有数据Oracle，非CEVT请求已确认 | IMPLEMENTATION_GAP | ETIM_P2_016, ETIM_P2_017 |
| ETIM_F_044 | SUPPORTED | H2 32bit边界及独立IRQ bit7，M2明确最大值回卷 | IMPLEMENTATION_GAP | ETIM_P1_012 |
| ETIM_F_045 | SUPPORTED | H2输入42..77、H3十八SRPWM及T8实际Peer捕获代码；A/B及跨实例选路 | IMPLEMENTATION_GAP | ETIM_P2_018 |

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
| ETIM_P2_014 | IMPLEMENTATION_GAP | 无实现；T10已定位CORE0第一条ETXB0路线，第二Fault源及其余配对G11，实际引脚Bench未绑定 |
| ETIM_P2_015 | IMPLEMENTATION_GAP | 无实现；仅文字自洽支路，运行安全窗需要输入/延迟时钟和有界写入事实 |
| ETIM_P2_016 | IMPLEMENTATION_GAP | 无实现；冻结CAP值由PRD请求搬运，连续数据另P2_017；逐CEVT握手不在本轮基线 |
| ETIM_P2_017 | IMPLEMENTATION_GAP | 无实现；目标PRD/模式1/4字LLI已明确，DMA最坏完成时间、周期参考和输入Bench需绑定；不覆盖CEVT编码 |
| ETIM_P2_018 | IMPLEMENTATION_GAP | 无实现；本轮四条路线见4.1，SRPWM公共动作、独立时钟比与捕获误差需绑定，不以ETIM自环替代Peer，不要求36×12执行 |

以上主状态选择最先阻塞的实现缺口，Reason中保留并存的Mapping/Bench缺口，不把它们互相覆盖。

## 第七章 必要问题、执行映射与分层完成Gate

时间：2026-09-06 22:48 CST。以下五项只询问必测目的所缺信息，不再要求RTL或全部状态机。

| 问题 | 精确缺少的答复 | 影响范围 / 关闭证据 |
|---|---|---|
| Q01 / G03 | CAP_FILTER的采样输入来自哪条时钟？clkprescale编码到实际分频公式是什么，实际1/2分频分别用何编码？ | P2_004的短长刺激及Case016；H2/H6/H7只给8bit预分频、W/T公式。适用字段说明或设计确认即可；不询问双阈值/精确边界 |
| Q02 / G04 | DB_SEL.s3a的0/1/2/3各接哪条a原始/处理路径（现文字复制b）？四个DLY的一个Tick来自哪条时钟，是否受计数分频影响？ | P2_005/015两支路及正常PWM旁路；H2/H6/H7和RDB未解答。需要正确MUX表及delay时钟关系，不询问窄脉冲/在途更新 |
| Q03 / G05 | 同组a为25%且b配置为其75%互补时，仅向a施OS LOW Fault，a/b在保持、撤销输入但未Clear、有效Clear恢复三阶段各应输出什么？Fault位于DB前还是后，是否只作用选中通道？ | TP037/Case023明确必测；R6/R3期望未施Fault的互补端继续波形，M2继承图与目标DB不能直接证明。需目标适用的两端Expected/简图，之后补入既有Fault方法；未定案不计该目的已规划 |
| Q04 / G06 | 软件/周期SyncOut经全局选择和XBAR到PIN时，实际外送使能/关闭控制是什么？EN3 bit16控制Event还是SyncOut，正常输出脉冲宽度或可观察下界是什么？ | P2_013正常开关负对照及Observer能力；H2/H12/D6已定源12..23但旧函数名与描述不一致。需适用控制说明和常规脉冲界，不要求全部延展组合 |
| Q05 / G02 | ETIM计数根具体连哪条BUS、SRPWM标准精度工作时钟具体来自哪里？同步/Capture输入正常路径的最大采样传播与量化界是多少？ | P2_018跨IP比例、外部时间及连续DMA参考Oracle；H13门控/接口选择不证明工作时钟，D11/D12不能直接作Oracle。需目标时钟连接及适用上界，实际频率另由Bench配置绑定 |

执行映射不是新理论研究：G10仍需具体封装/板卡、引脚、仪器精度、安全电平和人工门禁；
G11需把P2_014的双Fault输入及目标通道路由按H12表逐项绑定（T10仅证明第一条参考路线）；
G08需公共DMA动作、模式1、缓存/有限LLI和独立最坏完成时间。清单内Mapping未完成不算可执行，也不因其存在否定已写的方法。
G07及G09剩余特例、G03/04/05/06的额外竞态、G08的逐CEVT/未说明编码、G11全部输入穷举均按3.7移出本轮。
仍为UNKNOWN的硬件事实没有被改成VERIFIED；OUT_OF_SCOPE不是硬件UNSUPPORTED、运行SKIP或未来永久删除。

| Gate | 当前结论 | 判定依据 |
|---|---|---|
| 本轮范围收敛 / 分析交付 | 完成 | 要求与历史有效目的逐项处置；必测保留、额外扩展移出、五项必要问题具体化；不再以所有未知作为全局否决 |
| 必测方法完整性 | 局部待答，不宣称全闭合 | 32个PLAN保留输入/步骤/Observer/Oracle；滤波最大窗口和2分频已补。Q03互补目的尚缺完整Expected，Q01/02/04/05限制相关判据 |
| 实现准备 / 执行映射 | 未完成 | 实现0，目标时钟、支路、Bench及DMA上界未全部绑定；其余方法可分别进入后续实现，不需等待范围外扩展 |
| 软件文档校验 | 见7.5及过程Artifact | 只证明契约结构、芯片中立和映射一致，不证明ETIM功能通过 |
| Keil / Renode / FPGA / Silicon-HIL | NOT_EXECUTED | 无硬件动作、无构建或ETIM实测；不同后端结论不得互相替代 |

45个Feature及32个PLAN数量未变（R0三项、R1十一项、R2四项、R4十四项），未注册实现；
任何实际硬件执行仍须单独人工门禁。后续优先回答必要问题与完成具体Mapping，不继续无依据扩大Case分母。

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

### 7.4 连续DMA、Peer和时钟边界复核校验

时间：2026-09-06 21:38 CST。

- 本轮新增P2_017/P2_018两个PLAN，扩展P2_001单Tick高宽、P2_002近全量程真实等待；当前45个Feature、32个PLAN，全部未实现和未实测。
- Scope检查通过，只改两份ETIM文档；Source Coverage的ElectricalTest遗漏已附时间戳修正，T8/T9/T10及H13～H16、D9～D13保留SHA256。
- PLAN、公共IP边界、方法行语法和芯片映射专项通过；初轮resource-control记录为`20260906_213444_00d95d8d`、`20260906_213628_cba964d6`、`20260906_213631_e8eb115c`、`20260906_213634_e1a7a52c`。
- 语义复核保留DMAMUX一次确认、逐行唯一Oracle、保护窗、Peer A/B互补及不同实例负对照、近全量程相邻模减和真实等待约束；结构校验不证明这些硬件路径PASS。
- 最终软件门禁、提交及复核结果保存在过程Artifact `dma_clock_routing_validation.md`；本轮没有真实板卡、FPGA、Renode、Keil执行或共享层/SDK修改。

### 7.5 要求与历史目的范围收敛校验

时间：2026-09-06 22:49 CST。

- Scope检查通过，仅两份ETIM文档；不修改Checker、实现、SDK或其他芯片文件。
- PLAN、公共IP芯片中立、方法行结构及芯片映射四个专项全部通过；45个Feature和32个PLAN不变。
- 人工复核确认：最大滤波窗口/实际2分频已补；Fault互补仍为必测Q03；输入笛卡尔积、理论竞态、逐CEVT及无规范认证不再混入本轮分母。
- 专项resource-control任务：`20260906_224844_462c0451`、`20260906_224847_6d8a6858`、`20260906_224849_9e66ec56`、`20260906_224852_3d5bd543`。
- 总软件门禁与提交身份另存`artifacts/runs/20260906_223000_etim_scope/scope_validation.md`；这些校验不关闭Q01～Q05，不代表硬件PASS。
