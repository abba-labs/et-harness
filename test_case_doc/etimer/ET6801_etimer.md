# ET6801 ETIMER 芯片适配分析

> 本文件记录 ET6801 直接硬件/SDK事实、历史测试意图与公共 ETIMER Contract 的映射。未执行本仓库软件、FPGA 或 HIL；所有运行结论均为 `NOT_EXECUTED`。

## 第一章 Source Coverage / Source Item Trace

### 1.1 Source Coverage

| Source Root | Status | 本轮证据 | 边界 |
|---|---|---|---|
| requirement `test_case` | FOUND | ET3101/ET6003 `etimer.json`，62个有效Test Point、44个历史Case | 跨芯片稳定语义线索，不单独证明ET6801支持 |
| ET6801 SVD | FOUND | `Tools/RegGen/svd/etim_cfg.svd` 的Enable/Event/Sync配置 | 目标芯片直接寄存器证据；完整CORE寄存器还由SDK头/实现交叉核对 |
| ET6801 Drivers | FOUND | `DFP/Drivers/ET6x_Driver/Inc/et6x_etimer.h`、`Src/et6x_etimer.c` | 证明当前SDK API/实现，不等于硬件PASS |
| ET6801 Tests | FOUND | Unit/Functional/Smoke/FPGA eTimer源码 | 证明历史路径与意图；入口停用、仅打印/波形观察或API冲突时不算PASS |
| ET6801 FPGA verification | FOUND | `FPGATest/etimer_fpga_test.c`、Examples、Log | 只作路由/Bench线索；无当前SHA运行身份 |

### 1.2 Requirement Source Item Trace

| Source Item | 公共归属 | Disposition | ET6801依据/Gap |
|---|---|---|---|
| `ETIMER_TP_001..017` PWM通道/分频/周期/相位/Compare/Dead-time/Enable | F002/F003/F004；P1_001/P1_002/P1_005 | MERGED | 14通道SDK、32-bit period/phase/compare与Dead-time结构直接支持；外部波形Bench未接入 |
| `ETIMER_TP_018..028` Capture通道/分频/输入/四事件/时间戳/模式/Filter | F005/F006；P1_003 | MERGED | 14通道、1..62偶数分频、四事件边沿/时间戳/模式和Filter字段直接支持 |
| `ETIMER_TP_029..037` Fault通道/OS/CBC/SW/XBAR/极性/互补 | F007；P1_002 | MERGED | SDK定义OS/CBC、SW/XBAR和高低极性；安全Fault Bench未接入 |
| `ETIMER_TP_038..048` Event与同步输入/输出至ETIMER/ADC/DAC/ACMP/XBAR | F009；P2_001 | MERGED | SDK同步/事件路由API直接支持；Peer Execution Mapping未冻结 |
| `ETIMER_TP_049..053` IRQ Enable/Disable/Source/Mask | F008；P1_004 | MERGED | 12类IRQ位及Enable/Mask/Force/Clear/RAW/STATUS API直接支持；ATP IRQ Service缺失 |
| `ETIMER_TP_054..061` period/compare/phase/dead-time/event Immediate/Shadow | F002/F003/F004/F009；P1_005 | MERGED | SDK有period/compare/event shadow控制；实际生效边界必须由连续波形验证 |
| `ETIMER_TP_062` DMA请求源 | F010；P2_002 | MAPPED | 4个DMA通道选择器可选14通道×4 Capture Event；真实DMA搬运尚未接入 |
| 历史Case `ETIMER_001..044` | 8个公共PLAN | SUPERSEDED | 按共同刺激/Oracle合并为8个稳定Case；空Expected、固定delay和人工波形观察不直接沿用 |

## 第二章 ET6801 Hardware / Driver / Test Claims

| ID | 状态 | 可证明事实 | Evidence |
|---|---|---|---|
| ETIM_CLAIM_001 | VERIFIED | `ETIMER_CHANNEL_NUM=14`，Channel mask覆盖0..13 | `et6x_etimer.h:56-72` |
| ETIM_CLAIM_002 | VERIFIED | PWM时基支持1/2/4/8/16/32/64分频、32-bit period/phase与Compare A/B | `ETIMER_ClkDiv`、`ETIMER_TimeBaseInitParam`、`ETIMER_OCInitParam` |
| ETIM_CLAIM_003 | VERIFIED | Dead-time按7个AB group配置A/B上升/下降延迟与互补/输出状态 | `ETIMER_DBInitParam`、`ETIMER_initDB()` |
| ETIM_CLAIM_004 | VERIFIED | Capture支持四事件、上/下降沿、绝对/相对时间戳、Event0..3 One-shot/Continuous和Filter | `ETIMER_ICInitParam`与相关enum |
| ETIM_CLAIM_005 | VERIFIED | Fault支持高/低极性、CBC/OS与SW/XBAR触发 | `ETIMER_FaultInitParam`与相关enum |
| ETIM_CLAIM_006 | VERIFIED | IRQ支持Fault、CompareA/B、Period、Overflow与Capture Event0..3，具有Enable/Mask/Force/Clear/RAW/STATUS | `ETIMER_INT_*`、Driver IRQ API |
| ETIM_CLAIM_007 | VERIFIED | DMA请求可从14通道×4 Capture Event中选择到4个ETIMER DMA selector | `ETIMER_DMARequest`、`ETIMER_enableDMARequest()` |
| ETIM_CLAIM_008 | VERIFIED | Sync/Event可选Period/Zero/CompareA/B/EventCount，并路由到ETIMER、ADC/DAC/ACMP或XBAR/Pin | Sync/Event enum与Driver API |
| ETIM_CLAIM_009 | CONFLICT | 头文件声明`ETIMER_enableDMA(void)/disableDMA(void)`，当前实现只找到`ETIMER_enableDMARequest()`；Unit Test调用带参数的`ETIMER_enableDMA(...)` | 解除条件：构建对应配置并确认真实链接API，禁止据此宣称DMA已适配 |
| ETIM_CLAIM_010 | VERIFIED_LIMITATION | Unit Test验证寄存器配置；Functional入口多数注释；Smoke只启用Capture；FPGA默认只运行Dead-time且含无界循环 | 历史源码存在不等于当前自动化覆盖或PASS |

## 第三章 Public Endpoint -> ET6801 Mapping

| Public Endpoint | ET6801 Actual Source | Status |
|---|---|---|
| `COUNT.LIVE` | `CORE[n].LKCNT_RPT`，Driver `ETIMER_getCount()`先触发锁存后读取 | MAPPED；Live/Latch命名语义需实现阶段澄清 |
| `COUNT.LATCHED` | 同一锁存读取路径 | NEEDS_VERIFICATION；缺独立持续Live接口证据 |
| `PWM_OUTPUT[channel]` | ETIMER输出经Output XBAR映射到GPIO；FPGA源码示例0/1/2通道 | MAPPING_GAP；6801无固定ETIMER pin |
| `DEADTIME.A_RISE/B_FALL` | `OUT[group].APOS_DLY/ANEG_DLY/BPOS_DLY/BNEG_DLY` + 外部边沿 | MAPPED / BENCH_GAP |
| `CAPTURE.EVENT[0..3]` | `CAP_CNT[n].CAP1..CAP4` | MAPPED |
| `IRQ_RAW[source]` | `CMN_INT[n].INT_RAW_RPT` | MAPPED |
| `IRQ_STATUS[source]` | `CMN_INT[n].INT_STATUS_RPT` | MAPPED |
| `IRQ_DELIVERY.LATCHED_SOURCE` | 目标Firmware ISR/Service latch | IMPLEMENTATION_GAP |
| `FAULT.OUTPUT` | `CORE[n].PWM_CTRL`配置 + 外部输出波形 | MAPPED / BENCH_GAP |
| `SYNC.OUTPUT` | `CORE[n].SYNC_CTRL`、`EVT_TO_ADC`、DACC/CMPC/SYNC_OUT配置 + Peer端点 | MAPPING_GAP |
| `DMA_CHANNEL_STATUS` / `DMA_DESTINATION_WORD` | Peer DMA状态与目标内存 | IMPLEMENTATION_GAP |

## 第四章 Gap / Conflict / Unknown

| Gap ID | Type | 当前事实 | 解除条件 |
|---|---|---|---|
| `etimer_atp_implementation_gap` | IMPLEMENTATION | ATP无ETIMER公共Driver/Service/Wrap/Formal Case | 按公共Contract实现，不复制芯片专属Case |
| `etimer_capability_gap` | MAPPING | ATP Capability未发布14通道、分频、IRQ、DMA/Sync选项 | 从目标直接证据生成并回归验证 |
| `etimer_output_xbar_gap` | MAPPING | 6801 ETIMER输出需经Output XBAR到GPIO | 冻结逻辑输出与板级路由，不把GPIO写进公共Case |
| `etimer_waveform_bench_gap` | BENCH | PWM/Dead-time/Fault/Shadow需要连续数字Observer | 发布Instrument/FPGA Bench与Evidence映射 |
| `etimer_capture_peer_gap` | MAPPING | 历史SRPWM内部刺激存在，ATP Peer映射未接入 | 发布片内Peer Capability与Execution Mapping |
| `etimer_irq_service_gap` | IMPLEMENTATION | 历史ISR直接操作，ATP Source级latch/event_count未实现 | 实现Firmware IRQ Service并与RAW/STATUS分层 |
| `etimer_dma_api_conflict` | CONFLICT | DMA enable声明、实现和Unit调用不一致 | 对目标构建执行编译/链接并修正真实责任层后再适配 |
| `etimer_hil_status` | ENVIRONMENT | 本轮未执行硬件 | 完成实现、Mapping和人工硬件门禁后运行current-SHA HIL |

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| ETIMER_F_001 | SUPPORTED | 14通道；SDK锁存读取语义待澄清 | IMPLEMENTATION_GAP | ETIMER_P0_001 |
| ETIMER_F_002 | SUPPORTED | 1/2/4/8/16/32/64分频，32-bit period/phase | IMPLEMENTATION_GAP | ETIMER_P1_001, ETIMER_P1_005 |
| ETIMER_F_003 | SUPPORTED | 32-bit Compare A/B，两种Compare模式 | IMPLEMENTATION_GAP | ETIMER_P1_001, ETIMER_P1_005 |
| ETIMER_F_004 | SUPPORTED | 7个AB group，16-bit delay字段 | IMPLEMENTATION_GAP | ETIMER_P1_002 |
| ETIMER_F_005 | SUPPORTED | 四Capture Event、边沿与时间戳模式 | IMPLEMENTATION_GAP | ETIMER_P1_003 |
| ETIMER_F_006 | SUPPORTED | 1..62偶数分频、Filter和One-shot/Continuous | IMPLEMENTATION_GAP | ETIMER_P1_003 |
| ETIMER_F_007 | SUPPORTED | OS/CBC、SW/XBAR、高/低极性 | IMPLEMENTATION_GAP | ETIMER_P1_002 |
| ETIMER_F_008 | SUPPORTED | 12个IRQ bit来源 | IMPLEMENTATION_GAP | ETIMER_P1_004 |
| ETIMER_F_009 | SUPPORTED | 多Source、多Peer路由 | MAPPING_GAP | ETIMER_P2_001 |
| ETIMER_F_010 | SUPPORTED | 4个DMA selector，56个Capture Event请求源 | IMPLEMENTATION_GAP | ETIMER_P2_002 |

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| ETIMER_P0_001 | IMPLEMENTATION_GAP | ATP Driver/Service/Case尚未实现，Live/Latch语义需澄清 |
| ETIMER_P1_001 | IMPLEMENTATION_GAP | 公共实现和数字Instrument Bench缺失 |
| ETIMER_P1_002 | BENCH_GAP | 公共实现、Fault刺激和双路波形Bench缺失 |
| ETIMER_P1_003 | MAPPING_GAP | 公共实现与SRPWM/输入路由Execution Mapping缺失 |
| ETIMER_P1_004 | IMPLEMENTATION_GAP | ATP IRQ Service与Formal Case缺失 |
| ETIMER_P1_005 | BENCH_GAP | 公共实现和连续更新边界Observer缺失 |
| ETIMER_P2_001 | MAPPING_GAP | Event/Sync到Peer的Capability和Execution Mapping缺失 |
| ETIMER_P2_002 | IMPLEMENTATION_GAP | DMA Host/Firmware链和Evidence映射缺失；SDK API存在冲突 |

## 当前测试状态

| Lane | Status | Evidence |
|---|---|---|
| Software | NOT_EXECUTED | 本轮只执行文档Contract验证，不构建目标SDK |
| FPGA | NOT_EXECUTED | 无current-SHA FPGA运行 |
| Silicon/HIL | NOT_EXECUTED | 未获人工硬件执行授权 |
