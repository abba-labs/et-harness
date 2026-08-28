# ET6801 FMAC Chip Analysis & Adaptation Contract

> 本文件记录 ET6801 FMAC 的目标芯片 Hardware Truth、当前 SDK Driver、历史目标代码/日志、平台映射、Source Item Trace、Conflict/Unknown 与公共 `fmac.md` 的适配结果。
> ET6801 是本次唯一测试目标。ET3101/ET6003、ET60157 手册以及用户上传的其他 ET6x Driver 版本只作为 Family/Historical Reference，不能单独证明 ET6801 `SUPPORTED`，不能覆盖当前 ET6801 SVD 与 `review_code` Driver 事实。
> 当前已实现FMAC Driver Test Extension、Common Wrap、Firmware Service、PC Driver和23个Formal Case源码，并已接入全局运行时组合；ET6801 FMAC执行映射模块边界说明已按R220注释契约复核。2026-08-25 21:24 CST完成的49节点FPGA/HIL全量执行保留为历史基线。其后`FMAC_P1_002`、`FMAC_P1_006`、`FMAC_P1_010`和`FMAC_P1_014`完成修正版聚焦复测；2026-08-26经数字设计确认，原`FMAC_P1_016`对应的X1/X2 Load Error和Y Store Error属于普通软件不可构造的内部故障，已从Formal Case集合删除，但三个硬件Feature继续保留。按当前23个Case口径，已有证据汇总为46个执行节点、46 PASS、0 FAIL；历史日志中的PASS/FAIL仍只作为测试设计和问题证据。

# 第一章 Source Coverage 与 Evidence

## 1.1 分析目标、Freeze 边界与证据优先级

```text
Target = ET6801
analysis input baseline = review_code@3e4cfc134b86c7b17d24c656bba98aba11b93098

ET6801 当前直接硬件证据
  > ET6801 当前 review_code SDK Driver / Capability
  > ET6801 历史目标代码与日志
  > ET3101 / ET6003 / ET60157 / 其他ET6x Driver参考
```

本轮属于用户明确要求的FMAC完整重分析与源码实现。Freeze之前的FMAC文档提交统一视为分析Draft；当前公共Feature/Case ID和Wire接口按R100进入稳定绑定，后续不得再静默改义。源码实现与运行时组合、Keil构建和HIL结论必须分列，不得互相替代。

目标直接证据不足时保持 `UNKNOWN/CONFLICT`；禁止用前代芯片或不同版本 Driver 的相似实现补成目标真值。

## 1.2 Source Map Coverage

| Source | Source Map Locator | 状态 | FMAC定向检索结果 |
|---|---|---|---|
| requirement | `test_case` / Drive `1RrkQ-Tc2uGMszYbSnovdhH1N5cyQTVw9` | FOUND | ET3101/ET6003 `fmac.json` 均命中39个历史Test Point；只恢复需求意图。 |
| ET3101 SVD | Drive `1JxdvbRAl63mEhH0oWS9r1gXjnVbNZbuH` | FOUND | `fmac_cfg.svd`；Family Reference Only。 |
| ET3101 Driver A | Drive `1zJ6nJx-tqejf9ct81ZN_EM_vG9RKFNlZ` | FOUND | FMAC Driver；Family Reference Only。 |
| ET3101 Driver B | Drive `1_XYaPk7nhZB7YpcrJIWXW0E0tH2G1R6w` | FOUND | FMAC Driver lineage；Family Reference Only。 |
| ET3101 FPGA | Drive `1r7hW4mgXOPoOiLKvrndy9ob8C2GIKEF6` | FOUND | FMAC FPGA验证代码；Historical Reference Only。 |
| ET3101 Test A | Drive `1cBbUixPIcTSJIN_jNkyghFR3pD4kbd9c` | FOUND | Unit/Functional/Performance；Historical Reference Only。 |
| ET3101 Test B | Drive `1o92-FUR8ISa-lwVFqHDcc0YyTVSnpV-T` | FOUND | FMAC验证代码/日志；Historical Reference Only。 |
| ET6003 SVD | Drive `1Xus4MFSF-uVw5cXCBVEybgRdbE4RhQ57` | FOUND | `fmac_cfg.svd`；Family Reference Only。 |
| ET6003 Driver A | Drive `13r4PywFV_z9jMttRuZBxsXVZ8KrMcoQy` | FOUND | FMAC Driver；Family Reference Only。 |
| ET6003 Driver B | Drive `1w8NCOXSbBHWzIU-DQFM2BADvoR9ET0A0` | FOUND | FMAC Driver lineage；Family Reference Only。 |
| ET6003 FPGA | Drive `145tZT7xZnKse0o8J2mn4W61Y328Nl38R` | FOUND | FMAC FPGA验证代码；Historical Reference Only。 |
| ET6003 Test A | Drive `1ymCMrpQEQWMKd4ttQVoVcpNNHuZDCgiD` | FOUND | FMAC Unit/Functional；Historical Reference Only。 |
| ET6003 Test B | Drive `1XUS9HFbv00WXQZokRr3B5QKYn34MfPCk` | FOUND | FMAC验证代码/日志；Historical Reference Only。 |
| ET6801 SVD | Drive `1WNBK0Pxt8KFCwFQTiQRnJWHR3An_PQrp` | FOUND | `fmac_cfg.svd`（file `1Y7h6i7A0VcR_V_d3vu1MLtwoHYZHCW2i`）并与 merged `ET6801.svd` 交叉核对；Target Direct Evidence。 |
| ET6801 Driver | Drive `1umT9DaXv9MieLQwRugvXLfFxFkQodWgI` | FOUND | `et6x_fmac.h/.c` lineage；以 review_code 当前 Driver 为实现事实。 |
| ET6801 FPGA | Drive `160tw1UYl-FHWB57EvPa6_5bUhtEkbHcH` | FOUND | `fmac_fpga_test.c`；Target Historical Implementation Evidence。 |
| ET6801 Test | Drive `1Gc-kWlEbQC-V-ik6MPWTlTrhniHaugbd` | FOUND | `test_fmac.c`、`fmac_ft.c`、`fmac_time_test.c`、`fmac_ut.log` 等。 |

17个登记资料根均完成FMAC定向检索，当前无`UNAVAILABLE`。`FOUND`只表示命中相关资料，不代表各来源具有相同权威级别。

## 1.3 当前与用户新增 Evidence

| Evidence | 类型 | 用途 | 权威边界 |
|---|---|---|---|
| `test_case_doc/ET6801.svd` | Target Direct | instance/base/IRQ和FMAC当前字段交叉核对 | ET6801 Hardware Truth |
| Drive ET6801 `fmac_cfg.svd` file `1Y7h6i7A0VcR_V_d3vu1MLtwoHYZHCW2i` | Target Direct | Buffer/PARAM/CR/OUT/SR/IRQ/DMA语义 | ET6801 Hardware Truth |
| `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_fmac.h` | Target Current Driver | 当前枚举/API/IRQ命名 | Driver事实，不覆盖硬件 |
| `firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_fmac.c` | Target Current Driver | 当前API真实行为与实现缺陷 | Driver事实，不覆盖硬件 |
| `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h` | Target Current Driver | FMAC_RD/FMAC_WR request编号 | 芯片物理Mapping事实 |
| Drive `test_fmac.c` file `1-_U9vTfPf-fmk8NY94hcUwK_9Io7JtgL` | Target Historical Test | FIR/IIR/Stream/DMA/IRQ意图 | 旧Oracle不是当前真值 |
| Drive `fmac_ft.c` file `1RHwG6AFAfnhh-8xw1P7UAO4NnLe9hmy9` | Target Historical Test | Buffer/Output/Status/IRQ刺激线索 | 弱断言和旧命名需重审 |
| ET6801 `fmac_fpga_test.c` | Target Historical Test | FIR/IIR/DMA/IRQ/Float流程 | 非当前SHA执行结果 |
| ET6801 `fmac_time_test.c` | Target Historical Test | DWT/CPU/DMA性能方法 | 不继承magic correction |
| Drive `fmac_ut.log` file `1VPrwFK34fUbJdcvTVxpSJtWIr0GAbnQ2` | Target Historical Log | 多处Q15 actual与software expected存在系统性±1 LSB | 证明量化模型需独立闭合，不升级当前PASS |
| 用户上传 `ET6x_Driver.zip` | Version Reference | 不同ET6x API lineage对照 | 不能覆盖review_code当前Driver |
| ET60157用户/寄存器手册 | Family Reference | FMAC原理和Direct Form 1背景 | 不单独关闭ET6801 UNKNOWN |

## 1.4 Claim Ledger

| Claim | 状态 | Evidence | ET6801当前结论 |
|---|---|---|---|
| instance/base/IRQ | VERIFIED | E01 | `fmac0`；base `0x40204000`；IRQn `2`。 |
| X1/X2/Y布局 | VERIFIED | E02 | 三个区域均有8-bit逻辑起始位置/容量字段。 |
| X1 Full Watermark | VERIFIED | E02 | 1/2/4/8；Full条件为spare `< watermark`。 |
| X1 Full可见延迟 | VERIFIED | E02 | 最后一个可用空间填满后，Full上报约有3个FMAC clock延迟。 |
| Y Empty Watermark | VERIFIED | E02 | 1/2/4/8；Empty条件为unread `< watermark`。 |
| X1 Load | VERIFIED | E03 | FUNC=LOAD_X1，P=count；通过数据口写入X1。 |
| X2 Load | VERIFIED | E03 | FUNC=LOAD_X2；P/Q控制两段装载；current Driver写前馈B段后反馈A段。 |
| Y Load | VERIFIED | E03,E06 | FUNC=LOAD_Y，P=count；可建立Y数据/反馈初态；可与输入/输出格式转换组合形成直接转换测试路径。 |
| Enable/Disable | VERIFIED | E03 | PARAM.ENABLE=1启动；软件清0可停止正在运行的功能；初始化类功能由硬件自动清。 |
| Clear | CONFLICT | E04,E16 | `CR.CLR`可清动态指针、内部控制和ENABLE；当前FPGA中Float Overflow与Negative-after-offset两个sticky状态在`CR.CLR`、写1和写0三种尝试后均保持置位，不能宣称软件清除已闭合。 |
| FIR模式 | VERIFIED | E03 | FUNC=4；P=前馈系数数量。 |
| IIR模式 | VERIFIED | E03 | FUNC=5 Direct Form 1；P=前馈数量，Q=反馈数量。 |
| IIR bit-exact数学/状态更新 | UNKNOWN | E03,E12 | 当前SVD无完整方程、状态排列和逐级量化；历史lattice Oracle不可替代。 |
| PARAM.R算法作用 | UNKNOWN | E03 | 字段存在，但FUNC=1..5描述未定义用途。 |
| FIR first-valid-output | UNKNOWN | E12 | 历史ET6801使用数组一拍平移比较；目标设计未证明这是硬件固定对齐还是旧SDK/preload副作用。 |
| 一般Q15中间量化 | UNKNOWN | E13 | 历史`fmac_ut.log`多处±1 LSB差异，CMSIS默认舍入不能当目标硬件定义。 |
| Q15格式 | VERIFIED | E05 | fixed数据为signed s(16,15)。 |
| Float输入/输出 | VERIFIED | E06 | 支持Float32->Q15和Q15->Float32；current Driver提供Float写入与Float读取数据端点。 |
| Float钳位 | VERIFIED | E06 | 超范围输入被钳位到Q15上/下边界。 |
| Float Overflow状态 | VERIFIED | E06 | 记录之前发生且未被软件清除的Float->Q15越界。 |
| Internal Clip | VERIFIED | E07 | 内部s(26,22)越界支持Wrap/Clip。 |
| Final Saturate/Wrap | VERIFIED | E07 | 最终Q15支持Saturate/Wrap。 |
| Output Mode | VERIFIED | E07 | 0=RAW无Offset/Shift/Sat后处理；1=Offset+12-bit Sat；2=Offset+16-bit Sat。 |
| Offset字段存在 | VERIFIED | E07 | OUT_CR.OFT为16-bit配置字段。 |
| Offset完整signed/高位扩展解释 | UNKNOWN | E07 | 当前目标资料未完整定义OFT高位和符号扩展解释。 |
| Negative-after-offset | VERIFIED | E07 | ADD_OFT_IS_NEG_RPT可观察，软件写1清。 |
| Shift | VERIFIED | E07 | SH=0..15对应LEFT8..LEFT1/NONE/RIGHT1..RIGHT7。 |
| X1 Overflow状态 | VERIFIED | E08 | 无可写空间后继续写数据产生。 |
| Y Underflow状态 | VERIFIED | E08 | 无未读数据后继续读数据产生。 |
| Saturation状态 | VERIFIED | E08 | SR提供独立Saturation报告。 |
| DMA输入Request | VERIFIED | E09 | DMA_WEN；X1未满时产生写请求；只能在ENABLE=0修改。 |
| DMA输出Request | VERIFIED | E09 | DMA_REN；Y非空时产生读请求；只能在ENABLE=0修改。 |
| DMA Watermark | VERIFIED | E02,E09 | DMA写启用时X1 WM应为1；DMA读启用时Y WM应为1。 |
| 11类IRQ Source | VERIFIED | E10 | bit0..10分别为X1 req、Y req、Sat、X1 ovf、Y unf、P、PQ、Q、X1/X2/Y load error。 |
| IRQ Enable/Mask/Clear/Raw/Status/Force | VERIFIED | E10 | ET6801存在独立控制/状态语义。 |
| IRQ物理投递 | VERIFIED | E01,E10,E11,E16 | FMAC_IRQn=2；Force矩阵以及自然Request、Saturation、Y Underflow、P/PQ/Q错误均已由ISR Source latch在FPGA/HIL证明。 |
| 当前irq_delivery_count Measurement实现 | VERIFIED | E11,E16 | FMAC Service逐Source latch和delivery count已进入运行时组合，并由当前FPGA/HIL验证。 |
| P/PQ/Q自然错误条件 | VERIFIED | E10,E12,E16 | 当前最小非法参数刺激分别形成P、PQ、Q Raw/Status/ISR latch，三组参数化节点均PASS。 |
| X1/X2 Load Error与Y Store Error自然条件 | VERIFIED | E10,E19,E20 | Source身份明确；数字设计确认其属于普通软件不可构造的内部故障，不建立自然激励Formal Case。 |
| DMA controller/interface Mapping | VERIFIED | E09,E11 | ET6801 Profile已发布FMAC FIFO、双向Request、可选Controller和Interface集合；公共Case运行时解析。 |
| 当前自动化实现 | VERIFIED | E11,E16,E20 | FMAC Driver Test Extension、Wrap、Service、PC Driver和23个Formal Case源码已实现并进入运行时组合；三个内部故障Feature不建立Formal Case。 |
| 当前FPGA/Silicon Result | VERIFIED | E16,E17,E18,E20,E21 | FPGA/HIL历史全量基线为49个参数化节点；移除`FMAC_P1_016`三个无效软件刺激节点，并以修正版聚焦复测替代P1_006/P1_010旧失败后，当前Case集合证据汇总为46个节点、46 PASS、0 FAIL；Silicon未执行。 |

## 1.5 Claim Evidence Locator

| Evidence | 来源路径 / Locator | 符号 / 章节 / Case | 可证明事实 |
|---|---|---|---|
| E01 | `test_case_doc/ET6801.svd` | `peripheral FMAC`, `baseAddress`, `interrupt` | 当前目标实例、base与IRQ物理身份。 |
| E02 | Drive `1WNBK0Pxt8KFCwFQTiQRnJWHR3An_PQrp` / `fmac_cfg.svd` file `1Y7h6i7A0VcR_V_d3vu1MLtwoHYZHCW2i` | `X1_BUF`, `X2_BUF`, `Y_BUF`, `SR.X1_SPARE_NUM_RPT`, `SR.X1_FULL_RPT`, `SR.Y_UNRD_NUM_RPT`, `SR.Y_EMPTY_RPT` | Buffer布局、水位、计数、Full/Empty及X1 Full约3-clock可见延迟。 |
| E03 | 同一ET6801 `fmac_cfg.svd` + `firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_fmac.c` | `PARAM.FUNC/P/Q/R/ENABLE`, `FIFO_DATA`, `FMAC_selectFunc`, `FMAC_loadX1Buff`, `FMAC_IIR_loadX2Buff`, `FMAC_loadYBuff` | LOAD_X1/X2/Y、FIR/IIR、P/Q角色、R未定义用途、Enable/Disable及IIR前馈/反馈装载顺序。 |
| E04 | ET6801 `fmac_cfg.svd` + current FPGA HIL + current `et6x_fmac.c` | `CR.CLR`, `SR.FLOAT2FIXED_OVF_RPT`, `SR.ADD_OFT_IS_NEG_RPT` | `CR.CLR`清动态指针、内部控制和ENABLE；最新手动HIL表明`FLOAT2FIXED_OVF_RPT`经CR.CLR、SR写1和SR写0均不能清除，仅CRG复位可清；`ADD_OFT_IS_NEG_RPT`可由SR写1清除，CR.CLR和SR写0不能清除。两类状态不能继续共用同一清除结论。 |
| E05 | ET6801 `fmac_cfg.svd` | fixed/float数据路径描述、`FLOAT2FIXED_IN_SEL`, `FIXED2FLOAT_O_SEL` | fixed数据格式为signed s(16,15)。 |
| E06 | ET6801 `fmac_cfg.svd` + current `et6x_fmac.c` | `FLOAT2FIXED_IN_SEL`, `FIXED2FLOAT_O_SEL`, `SR.FLOAT2FIXED_OVF_RPT`, `FMAC_loadYBuffFloat`, `FMAC_getFIFOData`, `FMAC_getFIFODataFloat` | Float32<->Q15转换、Y直通转换测试路径、超范围钳位及sticky Overflow。 |
| E07 | ET6801 `fmac_cfg.svd` | `CR.CLIPEN`, `CR.ACC_OUT_WRAP_SEL`, `CR.DAT_OUT_SEL`, `OUT_CR.OFT`, `OUT_CR.SH`, `SR.ADD_OFT_IS_NEG_RPT` | Internal Clip、Final Saturate/Wrap、RAW/SAT12/SAT16、Offset、Shift和negative状态。 |
| E08 | ET6801 `fmac_cfg.svd` | `SR.X1_OVFL_RPT`, `SR.Y_UNFL_RPT`, `SR.SAT_RPT` | 三类状态的自然形成条件与可观测端点。 |
| E09 | ET6801 `fmac_cfg.svd` + `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h` | `CR.DMA_WEN`, `CR.DMA_REN`, `X1_FULL_WM`, `Y_EMPTY_WM`, `DMAMUX_REQ_FMAC_WR`, `DMAMUX_REQ_FMAC_RD` | 双向DMA request、idle-only修改、水位=1约束和物理request编号。 |
| E10 | ET6801 `fmac_cfg.svd` + current `et6x_fmac.h/.c` | `INT_EN`, `INT_MASK`, `INT_FORCE_IND`, `INT_CLR`, `INT_RAW_RPT`, `INT_STATUS_RPT`及bit0..10 | 11类IRQ身份和控制面；原Driver P/Q/R误写和Force目标寄存器冲突已在目标Chip Driver修正。 |
| E11 | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/fmac.yaml` + `pc/et_test_platform/profiles/chip_execution_mappings/et6801/fmac_routes.py` + current `review_code` tree | capability提供identity/base/IRQ，执行映射提供DMA物理事实；Driver、23个Case、Service和Wrap源码已实现 | 当前源码和运行时组合已实现；完整Keil构建、PFLASH运行和FPGA/HIL均已执行。 |
| E12 | Drive ET6801 Test root `1Gc-kWlEbQC-V-ik6MPWTlTrhniHaugbd` | `test_fmac.c::FMAC_UT_1/FM...`, `fmac_ft.c`, historical IIR/stream/DMA/IRQ cases | 历史测试意图、FIR数组一拍平移、IIR lattice历史Oracle和自然错误测试线索；不证明当前PASS。 |
| E13 | Drive `fmac_ut.log` file `1VPrwFK34fUbJdcvTVxpSJtWIr0GAbnQ2` | `FMAC_UT_1` actual/expected逐点日志 | 多处系统性±1 LSB差异，证明一般Q15量化模型尚未闭合。 |
| E14 | current `et6x_fmac.h/.c` | `FMAC_config`, `FMAC_forceInterrupt`, `FMAC_getStatus`, `FMAC_OutputDataShift`, `FMAC_loadX1Buff` | D01~D09 Driver Gap/Conflict的当前代码依据。 |
| E15 | ET3101/ET6003 Source Map roots + ET60157 manuals + uploaded `ET6x_Driver.zip` | family/historical FMAC资料 | 仅帮助理解继承和历史实现；不能单独关闭ET6801目标Claim。 |
| E16 | `artifacts/runs/20260825_212348_344047_fmac_formal_cases/tests/fmac` + `artifacts/reports/20260825_212446_465482_ET6801_FMAC测试报告.xlsx` | ET6801 FPGA/HIL正式执行与Excel报告 | 49个参数化节点：40 PASS、9 FAIL、0 SKIP/ERROR；只证明本次运行结果，不把失败Feature升级为PASS。 |
| E17 | `artifacts/runs/20260825_233023_383688_fmac_formal_cases/tests/fmac` + `artifacts/reports/20260825_233028_199395_ET6801_FMAC测试报告.xlsx` | `FMAC_P1_002`修正版FPGA/HIL聚焦复测 | WM=1/2/4三个参数节点全部PASS；证明X1 Spare、Full Watermark边界、Overflow置位与清除路径闭合，并替代E16中该Case的旧失败结论。 |
| E18 | `artifacts/runs/20260825_234451_089183_fmac_formal_cases/tests/fmac` + `artifacts/reports/20260825_234455_593803_ET6801_FMAC测试报告.xlsx` | `FMAC_P1_014`修正版FPGA/HIL聚焦复测 | Saturation、X1 Overflow、Y Underflow三个自然IRQ节点全部PASS；证明对应状态、Raw/Status、ISR Latch与投递计数链路闭合，并替代E16中X1 Overflow参数节点的旧失败结论。 |
| E19 | `artifacts/runs/20260826_082728_005875_manual_et6801_uart_crc/manual/uart_crc.log` | `fmac_p1_006`, `fmac_p1_010`, `fmac_p1_016`独立手动固件诊断 | P1_006四种清除方法中仅CRG复位清除目标位；P1_010由SR写1和CRG复位清除，CR.CLR/SR写0无效；P1_016对X1/X2/Y各执行合法边界、请求量越界、额外写入和物理边界跨越共12组刺激，`INT_RAW_RPT/INT_STATUS_RPT`始终为0。 |
| E20 | 本文`4.4.6`节，2026-08-26数字设计人工确认 | X1/X2 Load Error与Y Store Error触发来源 | 三个Source属于普通软件无法构造的内部故障；原P1_016的软件越界装载不是有效自然刺激，Feature保留但不再建立Formal Case。 |
| E21 | `artifacts/runs/20260828_140446_105424_manual_et6801_diagnostics/manual/diagnostics.log`、`artifacts/runs/20260828_142600_fmac_targeted_final/` | 2026-08-28 FMAC修正版手动诊断与Formal聚焦HIL | P1_006按“越界输入 -> 正常输入 -> W1C”执行后PASS；P1_010按正值恢复并W1C后PASS；正式PC到Firmware链路2/2 PASS。 |

# 第二章 ET6801 Hardware / Driver Facts

## 2.1 Identity 与主数据路径

```text
instance      = fmac0
base          = 0x40204000
irqn          = 2
local regions = X1 input / X2 coefficients / Y output-feedback
data endpoint = FIFO_DATA
```

目标测试主链：PC生成输入/系数/独立Oracle -> 配置X1/X2/Y -> CPU或DMA供数 -> FMAC MAC/地址生成 -> Y/FIFO输出 -> SR/IRQ/DMA Evidence。核心数字Oracle不依赖外部GPIO、示波器或Companion FPGA。

## 2.2 Buffer、Load、Watermark 与活动控制

| 对象 | ET6801当前硬件事实 | 对测试设计的约束 |
|---|---|---|
| X1布局 | start/size均8-bit | 布局Case通过配置读回和Spare行为证明。 |
| X1 Load | FUNC=1，P=count | X1状态Case使用Load建立不被FIR并发消费的受控占用。 |
| X1 Full WM | 1/2/4/8；spare小于WM置Full | 状态判定必须按目标可见窗口；最后空间填满后Full约3 clock延迟。 |
| X1 Overflow | 无可写空间后继续WDATA写产生 | 需要unchecked单写刺激；不能用Force替代。 |
| X2布局 | start/size均8-bit | 系数区域布局独立于算法参数。 |
| X2 Load | FUNC=2；P段后Q段 | FIR用前馈段；IIR current Driver写B前馈段后A反馈段。 |
| Y布局 | start/size均8-bit | IIR时同时承担反馈历史。 |
| Y Load | FUNC=3，P=count | Y状态Case直接使用Load/read；Float Case用Y Load/read隔离转换，不依赖FIR输出对齐。 |
| Y Empty WM | 1/2/4/8；unread小于WM置Empty | Unread/Empty状态通过直接Load/read模型验证。 |
| Y Underflow | 无未读数据后继续读产生 | 需要unchecked单读刺激。 |
| ENABLE | 1启动；软件清0停止；初始化功能硬件清0 | FIR/IIR不能在读完输出后假设自动停止，Formal Case必须显式Disable。 |
| CLR | 清动态指针/控制/ENABLE；当前FPGA实测不能清除两个软件可清SR位，其他配置保持 | `CLEAR`不能被公共实现当成准静态baseline reset；每个Case必须显式建立Known Baseline，软件可清SR位作为当前FPGA Gap记录。 |

## 2.3 数值与输出后处理

| 类别 | ET6801事实 | 公共处理 |
|---|---|---|
| Fixed | signed s(16,15) | 基础FIR使用量化不敏感向量；一般量化保持Gap。 |
| Float in | Float32->Q15 | P1_005/P1_006使用0.5单抽头真实FIR流式路径验证。 |
| Float out | Q15->Float32 | P1_005使用0.5单抽头真实FIR流式路径验证。 |
| Internal Clip | s(26,22) Wrap/Clip | 使用恒定历史/恒定输入构造对齐不敏感稳态刺激。 |
| Final policy | Q15 Saturate/Wrap | 与Internal Clip分开；使用对齐不敏感稳态刺激。 |
| Data mode | RAW/SAT12/SAT16 | RAW不消费Offset/Shift；模式、Offset、Shift Case均隔离其他后处理。 |
| Offset | 16-bit code | 当前仅覆盖无歧义范围；全域保持Gap。 |
| Negative report | 软件写1清 | 负值与非负子实例中间显式清除，避免sticky历史污染。 |
| Shift | 0..15=LEFT8..RIGHT7 | current SDK额外RIGHT8不得进入公共集合。 |

## 2.4 IRQ、R130 Evidence 与 DMA

ET6801 IRQ Source：

```text
bit0  X1_WRITE_REQUEST
bit1  Y_READ_REQUEST
bit2  SATURATION
bit3  X1_OVERFLOW
bit4  Y_UNDERFLOW
bit5  P_ERROR
bit6  PQ_ERROR
bit7  Q_ERROR
bit8  X1_LOAD_ERROR
bit9  X2_LOAD_ERROR
bit10 Y_LOAD_ERROR
```

`IRQ_RAW/IRQ_STATUS`是目标硬件Observation；未来FMAC ISR锁存的`IRQ_DELIVERY.LATCHED_SOURCE`是目标侧独立Observation；ISR/Service维护的`irq_delivery_count`只作为Measurement，用来证明bounded window内是否发生新增投递，不得登记为Observation。

DMA目标事实：

| Direction | Endpoint | Request | ET6801约束 |
|---|---:|---:|---|
| memory -> FMAC | `0x40204020` | `FMAC_WR = 2` | X1 WM应为1；DMA_WEN只能在ENABLE=0修改。 |
| FMAC -> memory | `0x40204020` | `FMAC_RD = 1` | Y WM应为1；DMA_REN只能在ENABLE=0修改。 |

request/endpoint以及当前ET6801 FPGA执行使用的DMA controller/interface/Channel Mapping均已由P2_001和P3_003验证。

## 2.5 Current review_code SDK Driver Audit

| ID | 对象 | 状态 | 影响与处理 |
|---|---|---|---|
| D01 | `FMAC_config()` | RESOLVED_IN_SOURCE | 已删除配置结束后错误复用`regVal`修改PARAM.P/Q/R的语句。 |
| D02 | `FMAC_forceInterrupt()` | RESOLVED_IN_SOURCE | 已改为写目标Force控制位；11类Source的Force、Raw、Status与ISR投递均已由P1_012验证。 |
| D03 | IRQ bit5/6/7命名 | ISOLATED | SDK历史命名未扩散到公共协议；Wrap/PC公共模型固定为P/PQ/Q语义。 |
| D04 | `FMAC_getStatus()` | RESOLVED_IN_SOURCE | 已补Float->Q15 Overflow状态，并由Wrap Snapshot公开。 |
| D05 | `FMAC_OutputDataShift` | ISOLATED | 公共Wrap只接受硬件合法0..15，拒绝Driver历史RIGHT_SHIFT_8(value=16)。 |
| D06 | 运行停止动作 | RESOLVED_IN_SOURCE | Driver Test Extension与Wrap已提供显式Stop。 |
| D07 | DMA Request Gate | RESOLVED_IN_SOURCE | Driver Test Extension与Wrap已提供idle-only输入/输出Gate设置。 |
| D08 | X1 Full流控 | ISOLATED | Formal Case不调用历史`FMAC_loadX1Buff()`；有界Test Extension按明确数量装载，流式路径依据状态分Chunk。 |
| D09 | 配置快照读取 | RESOLVED_IN_SOURCE | Driver Test Extension读取完整配置，Wrap转换为芯片中立Snapshot。 |

用户上传的另一版`ET6x_Driver.zip`出现不同API lineage，其中存在的接口不能证明review_code已经具备等价实现；只作为版本参考。

# 第三章 Source Item Trace

## 3.1 ET3101/ET6003 39项历史 Requirement 逐项处置

> 39项只恢复历史测试意图；Feature和Case均重新由ET6801目标硬件证据裁决。

| TP | 历史意图 | 当前Feature/Gap | Case | Disposition | ET6801裁决 |
|---:|---|---|---|---|---|
| 1 | X1 start | F001 | P1_001 | MAPPED | 与size合并为同一布局Feature。 |
| 2 | X1 size | F001 | P1_001 | MERGED | 同上。 |
| 3 | X1 Full WM | F002,F003,F004 | P1_002 | SPLIT | Watermark、Spare Count、Full状态分别报告，同一Case参数化。 |
| 4 | X2 start | F005 | P1_001 | MAPPED | 与size合并为X2布局。 |
| 5 | X2 size | F005 | P1_001 | MERGED | 同上。 |
| 6 | Y start | F006 | P1_001 | MAPPED | 与size合并为Y布局。 |
| 7 | Y size | F006 | P1_001 | MERGED | 同上。 |
| 8 | Y Empty WM | F007,F008,F009 | P1_003 | SPLIT | Watermark、Unread Count、Empty状态分别报告。 |
| 9 | Function select | F010,F011,F012,F013,F014 | P0_001,P0_002,P1_002,P1_003 | SPLIT | LOAD_X1/X2/Y、FIR、IIR按独立硬件功能拆分。 |
| 10 | execute/enable | F051 | P0_004 | MAPPED | Enable/Disable独立硬件Feature。 |
| 11 | P | Capability/Case参数 | P0_001,P0_002 | MAPPED | 不独立发布Feature。 |
| 12 | Q | Capability/Case参数 | P0_002 | MAPPED | 不独立发布Feature。 |
| 13 | R | `param_r_semantics` | — | UNKNOWN | 字段存在但目标FUNC未定义用途。 |
| 14 | final wrap/saturate | F023 | P1_008 | MAPPED | 最终输出策略。 |
| 15 | Clear | F017 | P0_003 | MAPPED | 独立Clear Feature。 |
| 16 | output mode | F024 | P1_009 | MAPPED | RAW/SAT12/SAT16参数化。 |
| 17 | internal clip | F022,F030 | P1_007 | SPLIT | Clip策略与Saturation状态分别报告。 |
| 18 | offset | F025,F026 | P1_010 | SPLIT | Offset数值与负值状态分别报告。 |
| 19 | shift | F027 | P1_011 | MAPPED | 16个合法选项参数化。 |
| 20 | float input/overflow | F018,F020,F021 | P1_005,P1_006 | SPLIT | 正常输入转换、钳位、Overflow状态拆分。 |
| 21 | float output | F019 | P1_005 | MAPPED | 独立输出转换Feature。 |
| 22 | DMA input | F031 | P2_001 | MAPPED | 真实DMA终态+数据闭环。 |
| 23 | DMA output | F032 | P2_001 | MAPPED | 与输入方向同Case但Feature独立。 |
| 24 | Y Empty | F009 | P1_003 | MAPPED | 独立状态Feature。 |
| 25 | X1 Full | F004 | P1_002 | MAPPED | 独立状态Feature并记录3-clock可见延迟。 |
| 26 | X1 Overflow | F028,F036 | P1_002,P1_014 | SPLIT | 状态与IRQ事件分开。 |
| 27 | Y Underflow | F029,F037 | P1_003,P1_014 | SPLIT | 状态与IRQ事件分开。 |
| 28 | Saturation | F030,F035 | P1_007,P1_014 | SPLIT | 状态与IRQ事件分开。 |
| 29 | negative after offset | F026 | P1_010 | MAPPED | 软件写1清；正负子实例隔离。 |
| 30 | Y unread | F008 | P1_003 | MAPPED | 独立Count Feature。 |
| 31 | X1 spare | F003 | P1_002 | MAPPED | 独立Count Feature。 |
| 32 | float overflow/clamp | F020,F021 | P1_006 | SPLIT | 钳位结果与Overflow状态分开。 |
| 33 | IRQ Enable | F044 | P1_012 | MAPPED | 独立控制Feature。 |
| 34 | IRQ Mask | F045 | P1_012 | MAPPED | 独立控制Feature。 |
| 35 | IRQ Clear | F046 | P1_012 | MAPPED | 独立控制Feature。 |
| 36 | IRQ Force/delivery | F049,F050 | P1_012 | SPLIT | Force动作与真实投递分开。 |
| 37 | IRQ Status | F048 | P1_012 | MAPPED | 独立状态Feature。 |
| 38 | IRQ Raw | F047 | P1_012 | MAPPED | 独立状态Feature。 |
| 39 | 11 IRQ Source | F033..F043 | P1_013..P1_016 | SPLIT | 11个硬件事件各自Feature，按相同路径参数化Case。 |

## 3.2 ET6801 直接硬件行为与历史目标代码/日志处置

| Source Item | 证据/现象 | 本次处理 | Disposition |
|---|---|---|---|
| `CR.CLR`保留其他寄存器设置 | E04 | 公共Automation Contract明确`clear`不是硬件复位；Case隔离先由CRG复位FMAC，再清FMAC Service状态和Resource Pool，Case仍显式提交完整Feature配置。 | MAPPED |
| CRG FMAC软复位 | ET6801 `SRST1.FMAC`与真机寄存器恢复证据 | ET6801 CRG映射使用SDK修正后的`CRG_PERIPH_FMAC`；每个FMAC Case开始前由PC先复位硬件，再复位FMAC Service状态和整个Resource Pool。 | MAPPED |
| X1 Full约3-clock可见延迟 | E02 | 只进入ET6801 Chip Adaptation；公共Case使用“目标有界可见窗口”，不写死芯片cycle。 | MAPPED |
| DMA WM=1 + idle-only gate | E02,E09 | 进入ET6801 DMA Feature差异和P2/P3 Case适配。 | MAPPED |
| Unit `FMAC_UT_1` / Functional FIR | FIR+CMSIS逐点比较，存在历史一拍平移 | 保留独立Golden思想；不冻结历史偏移，新增`fir_output_alignment_gap`。 | SUPERSEDED |
| `fmac_ut.log` | 多处actual与software expected相差±1 LSB | 作为`arithmetic_quantization_policy_gap`直接Evidence；禁止全局Tolerance掩盖。 | MAPPED |
| Unit/Functional IIR | Y预载 + historical lattice Golden | 只保留反馈初态受控思想；lattice不作为Direct Form 1真值。 | SUPERSEDED |
| Unit streaming | append输入/连续读出 | 保留Chunk连续性；数值Oracle依赖FIR语义闭合。 | SUPERSEDED |
| Unit/Functional DMA | 双向DMA FIR | 保留端到端DMA+Golden；补WM=1和idle-only gate。 | SUPERSEDED |
| ET6003/ET3101最新Functional X1 threshold | 容量200、WM=4时先写197项，立即观测Full=0，延时后观测Full=1 | 提取“Full由剩余空间低于Watermark产生”和“状态需要可见窗口”两项稳定思想；公共Case改为Runtime容量推导，不复制固定200项。 | SUPERSEDED |
| ET6003/ET3101最新Functional X1 overflow | 接近或填满X1后直接额外写一次`FIFO_DATA`并读取Overflow | 公共Case使用容量加1的LOAD_X1和连续unchecked写，保证最后1项真实到达无空间X1。 | SUPERSEDED |
| ET6003/ET3101旧Functional Load Error | X1/X2/Y超量装载测试存在参数数量不匹配、`uint8_t`数量溢出和Y事件误用X2位；最新版修复提交已删除这些Case | 只保留Source存在事实，不把旧刺激当作ET6801自然触发Oracle；维持`load_error_trigger_semantics_gap`。 | REJECTED |
| Functional Y threshold/underflow | Y请求/读空 | 改为Y Load/read独立状态机，避免依赖FIR产出。 | SUPERSEDED |
| Functional Float | Float FIR/转换混合 | 基础Float转换改用Y直通Load/read隔离，避免FIR对齐污染转换Oracle。 | SUPERSEDED |
| Functional offset/shift | SAT16下做offset/right-shift | 冻结Offset/Shift Case使用SAT16和对齐不敏感稳态刺激。 | SUPERSEDED |
| Functional IRQ | Enable/Force/Raw/Status | 增补Disable、ISR锁存和delivery-count Measurement，修正目标bit5/6/7命名。 | SUPERSEDED |
| Performance | target DWT + magic correction | 保留目标侧计时方向；不继承magic correction。 | SUPERSEDED |

# 第四章 Public Endpoint / Measurement 与 Current Platform Gap

## 4.1 Public Observation -> ET6801 Mapping

| Public Endpoint | ET6801实际来源 | 状态/说明 |
|---|---|---|
| `CONFIG.X1_START` | `X1_BUF.X1_BASE` | VERIFIED |
| `CONFIG.X1_SIZE` | `X1_BUF.X1_BUF_SIZE` | VERIFIED |
| `CONFIG.X2_START` | `X2_BUF.X2_BASE` | VERIFIED |
| `CONFIG.X2_SIZE` | `X2_BUF.X2_BUF_SIZE` | VERIFIED |
| `CONFIG.Y_START` | `Y_BUF.Y_BASE` | VERIFIED |
| `CONFIG.Y_SIZE` | `Y_BUF.Y_BUF_SIZE` | VERIFIED |
| `STATUS.ACTIVE` | `PARAM.ENABLE` | VERIFIED；运行类需软件Disable，初始化类可自动清。 |
| `STATUS.X1_SPARE_COUNT` | `SR.X1_SPARE_NUM_RPT` | VERIFIED |
| `STATUS.Y_UNREAD_COUNT` | `SR.Y_UNRD_NUM_RPT` | VERIFIED |
| `STATUS.X1_FULL` | `SR.X1_FULL_RPT` | VERIFIED；最后空间填满后约3 clock可见延迟。 |
| `STATUS.Y_EMPTY` | `SR.Y_EMPTY_RPT` | VERIFIED |
| `STATUS.X1_OVERFLOW` | `SR.X1_OVFL_RPT` | VERIFIED |
| `STATUS.Y_UNDERFLOW` | `SR.Y_UNFL_RPT` | VERIFIED |
| `STATUS.ACCUMULATOR_SATURATION` | `SR.SAT_RPT` | VERIFIED |
| `STATUS.NEGATIVE_AFTER_OFFSET` | `SR.ADD_OFT_IS_NEG_RPT` | VERIFIED；软件写1清。 |
| `STATUS.FLOAT_TO_Q15_OVERFLOW` | `SR.FLOAT2FIXED_OVF_RPT` | Hardware VERIFIED；完整状态通过Driver Test Extension提供。 |
| `DATA.OUTPUT_STREAM` | `FIFO_DATA` read path | VERIFIED |
| `IRQ_RAW.<source>` | `INT_RAW_RPT[10:0]` | VERIFIED |
| `IRQ_STATUS.<source>` | `INT_STATUS_RPT[10:0]` | VERIFIED |
| `IRQ_DELIVERY.LATCHED_SOURCE` | `FMAC_IRQn=2` -> FMAC Service latch | 源码已实现；尚未Keil/HIL验证。 |
| `DMA_CHANNEL_STATUS.INPUT` | AHB DMA input Channel status | 已由公共DMA Driver读取；待FMAC HIL。 |
| `DMA_CHANNEL_STATUS.OUTPUT` | AHB DMA output Channel status | 已由公共DMA Driver读取；待FMAC HIL。 |
| `DMA_TRANSFER_COUNT.INPUT` | AHB DMA input transfer count | 已由公共DMA Driver读取；待FMAC HIL。 |
| `DMA_TRANSFER_COUNT.OUTPUT` | AHB DMA output transfer count | 已由公共DMA Driver读取；待FMAC HIL。 |
| `DMA_DESTINATION_SEQUENCE` | DMA destination memory | 已由Resource Driver读取；待FMAC HIL。 |
| `TARGET_CYCLE_COUNT` | target cycle observer | CPU路径由FMAC DWT原子命令返回，DMA路径由DMA目标计时接口返回；待FMAC HIL。 |

## 4.2 Public Measurement -> ET6801 Mapping

| Measurement | ET6801来源 | 状态/说明 |
|---|---|---|
| `irq_delivery_count` | FMAC ISR/Service软件累计计数 | 源码已实现；按R130记录为Measurement，不得用`record_observation`登记。 |
| `accepted_count/read_count` | FMAC Service动作返回值 | 源码已实现；协议Measurement。 |
| `first_valid_output_index` | target Capability / design fact | NEEDS_VERIFICATION；FIR/IIR分别闭合。 |
| `output_digest` | PC由原始`DATA.OUTPUT_STREAM` Artifact派生 | IMPLEMENTATION_GAP；只作Measurement/Artifact摘要，失败报告必须保留原始Chunk。 |
| `cycles_per_element` | PC由TARGET_CYCLE_COUNT和element_count派生 | IMPLEMENTATION_GAP；派生Measurement，不覆盖原始周期Observation。 |

## 4.3 Current Platform Gap

| Layer | Current state | Classification |
|---|---|---|
| Capability | 仅identity/base/IRQ；FMAC features/limits/options/parameters未发布 | MAPPING_GAP |
| PC Driver | `drivers/fmac`已实现全部公共命令 | HIL_VERIFIED |
| PC Formal Case | 23个SPEC Case已实现并注册；21个Case全部节点PASS，2个Case存在非PASS节点 | PARTIALLY_HIL_VERIFIED |
| Firmware Service | `et_fmac_service.*`已实现并进入运行时组合 | HIL_VERIFIED |
| Common Wrap | `et_fmac_wrap.*`已实现且只调用FMAC Chip Driver | HIL_VERIFIED |
| Chip Driver | D01~D09已修复；测试补充接口位于Test Driver Extension | Keil构建和PFLASH运行PASS；剩余Hardware Truth Gap见当前状态表 |
| DMA Execution Mapping | ET6801 Profile发布FIFO、双向Request、Controller和Interface事实 | HIL_VERIFIED |
| FMAC IRQ latch/count | Service绑定和逐Source latch/count已由Force与多类自然Source验证 | HIL_VERIFIED |
| Target cycle observer | FMAC Test Driver Extension使用DWT原子采集CPU处理周期；DMA使用DMA目标侧计时接口 | HIL_VERIFIED |

## 4.4 当前执行状态

```text
Software implementation: IMPLEMENTED_AND_COMPOSED
Keil build for new FMAC automation: PASS
FPGA FMAC Formal Case: FULL_BASELINE_EXECUTED / 40 PASS / 9 FAIL / 0 SKIP / 0 ERROR
FPGA FMAC P1_002 focused rerun: EXECUTED / 3 PASS / 0 FAIL / 0 SKIP / 0 ERROR
FPGA FMAC P1_014 focused rerun: EXECUTED / 3 PASS / 0 FAIL / 0 SKIP / 0 ERROR
FPGA FMAC current Case set evidence roll-up: 46 PASS / 0 FAIL / 0 SKIP / 0 ERROR
Silicon FMAC Formal Case: NOT_EXECUTED / NOT_VERIFIED
Historical ET6801 tests/logs: REFERENCE_ONLY
```

### 4.4.1 2026-08-25 21:24 CST FPGA/HIL结果

测试前已执行三项Case起始隔离：通过CRG Driver复位FMAC、复位FMAC Service状态、整池复位Resource。CRG Driver本身另经FMAC/CRC/AES/CORDIC共10个寄存器、每项3轮写入与复位回读验证，`failed_registers=0`。

| 结果类别 | 数量 | Case / 参数 | 当前结论 |
|---|---:|---|---|
| PASS | 40 | 全部P0、P2、P3节点，以及P1_001/003/004/005/007/008/009/011/012/013/015和P1_014的Saturation、Y Underflow | 当前输入、输出与断言均满足；仅对本次参数节点成立。 |
| Assertion FAIL | 9 | `FMAC_P1_002`的WM=1/2/4、`P1_006`、`P1_010`、`P1_014`的X1 Overflow、`P1_016`的X1/X2/Y Load Error | 失败均有结构化硬件观测；不得降级为SKIP或弱化断言。 |
| Timeout / ERROR / SKIP | 0 | 无 | 所有49个节点均到达确定的PASS或Assertion FAIL结论。 |

证据目录：`artifacts/runs/20260825_212348_344047_fmac_formal_cases/tests/fmac`。报告：`artifacts/reports/20260825_212446_465482_ET6801_FMAC测试报告.xlsx`。

### 4.4.2 2026-08-25 22:41 CST 跨芯片历史Case复核修正

- `FMAC_P1_002`中“写入半容量后Spare应等于剩余容量”的失败仍成立；ET6003和ET3101最新代码使用等价的容量200、写入100、期望Spare=100方法。
- 原`FMAC_P1_002`把“写入Watermark项”误作Full边界，不能用于证明Full和Overflow失败。ET6801 SVD与6003/3101最新Case均表明，应写到“剩余空间等于Watermark”，再写1项并等待状态可见；公共Case源码已修正但尚未重新HIL。
- `FMAC_P1_014`使用容量200后第201项unchecked写，符合ET6801 SVD和6003/3101额外直写方法；其X1 Overflow失败仍是有效待定位现象。
- `FMAC_P1_016`旧6003/3101自然刺激存在API和Source选择错误，且已被两个芯片的最新版删除；本次容量8、写9失败只能证明该刺激未触发，不能据此判定RTL功能故障。

### 4.4.3 2026-08-25 23:16 CST `FMAC_P1_002`首次修正HIL复核

- 首次修正版在Watermark 1/2/4三个参数节点均读到`X1_SPARE_NUM_RPT=0`，失败发生在Watermark和Overflow断言之前。
- 结合ET6801 SVD中“循环模式”的状态描述以及6003/3101历史Case的“预装X1 -> 启动FIR -> 观测Spare/Full”顺序，确认Case仍在LOAD_X1初始化动作结束后过早读取动态状态。
- 公共Case已进一步收敛为“预装X1 -> 启动单抽头FIR -> 运行态读取Spare/Full -> 额外直写触发Overflow”；该版需重新HIL后才能更新PASS/FAIL结论。
- 第二次HIL进入FIR后读到`X1_SPARE_NUM_RPT=128`、`Y_UNRD_NUM_RPT=1`，相对预期Spare多1；这证明FIR启动立即消费了1个X1并产生1个Y，不是Spare读回链路故障。
- 为使Watermark/Overflow边界只由测试写入量决定，Case最终收敛为“预装满最小Y -> 启动FIR但不消费X1 -> 观测Spare/Full -> 容量外直写触发Overflow”；该版仍需HIL确认。
- 第三次HIL表明“预装满最小Y”在当前最小布局下使`Y_PRELOAD`超时，该构造不适合作为公共Case前置条件。
- 最终构造不再阻止FIR启动消费，而是显式核对并补偿“启动消费1项X1、产生1项Y”：Watermark预装量增加1，Overflow先补回空位再额外直写1项。
- 2026-08-25 23:30 CST正式聚焦复测中，WM=1/2/4三个参数节点全部PASS：半容量阶段读到`X1_SPARE_NUM_RPT=128`且`Y_UNRD_NUM_RPT=1`；边界前Spare等于Watermark且Full为0；再写1项后Spare降为`watermark-1`且Full为1；填满启动消费产生的空位后再额外写1项，Overflow置位并可清除。
- 本次证据确认原失败来自Case未补偿FIR启动消费，不是ET6801 X1状态链路硬件故障。证据见E17。

### 4.4.4 2026-08-25 23:44 CST `FMAC_P1_014`修正HIL复核

- 首次修正版复测中Saturation和Y Underflow继续PASS；X1 Overflow启动后读到`X1_SPARE_NUM_RPT=28`和`Y_UNRD_NUM_RPT=28`，证明Y容量28允许FIR连续消费28项X1，旧刺激仍未建立“只释放一个空位”的确定边界。
- X1 Overflow子实例将Y容量收紧为1后，FIR启动只消费1项X1；第一笔unchecked写补满该空位，第二笔在无空间时产生真实Overflow。
- 正式聚焦复测的Saturation、X1 Overflow、Y Underflow三个节点全部PASS，对应状态、IRQ Source和ISR投递链均闭合；原X1 Overflow失败属于Case构造错误，不是当前ET6801硬件问题。证据见E18。

### 4.4.5 2026-08-26 08:27 CST 剩余三个失败Case独立手动固件诊断

本轮使用独立手动测试固件，不经过PC Formal Case、Service或Wrap判据。每种方法开始前均通过CRG Driver复位FMAC，直接调用目标Chip Driver Test Extension或目标寄存器构造最小刺激，并通过UART0输出原始寄存器值。测试前重新配置XC7VX980T bitfile、加载BootROM、擦写并校验PFLASH，随后从Flash运行。

- `FMAC_P1_006`：四次均稳定触发`SR=0x08051000`，目标位为`0x00001000`。CR.CLR后目标位仍为1，SR写1后仍为1，SR写0后仍为1；仅CRG复位后`SR=0x00000001`，目标位清除。当前失败属于目标RTL/SVD清除语义冲突，不是PC观测或Service状态残留。
- `FMAC_P1_010`：四次均稳定触发`SR=0x03080800`，目标位为`0x00000800`。CR.CLR后目标位仍为1，SR写0后仍为1；SR写1后`SR=0x03080000`，目标位已清，CRG复位同样可清。当前Formal Case失败来自公共清除路径选择错误，应在后续获批任务中通过Chip Driver Test Extension提供专用W1C接口，不得在Wrap直接操作寄存器。
- `FMAC_P1_016`：对X1、X2、Y分别执行“请求8/写8”“请求9/写9”“请求8/写9”“base=252、size=8跨物理256项边界”四类刺激，共12组。PARAM变化与ENABLE自动清除证明命令和写入已到达硬件，但所有组的`INT_RAW_RPT`与`INT_STATUS_RPT`均为0。当前证据已排除单一容量8/写9构造不足，但在缺少RTL触发定义前仍不能把结论升级为确定RTL缺陷；Case继续保持FAIL/open。

证据：`artifacts/runs/20260826_082728_005875_manual_et6801_uart_crc/manual/uart_crc.log`。部署证据分别位于`artifacts/runs/20260826_082356_494865_xc7vx980t_program/`、`artifacts/runs/20260826_082614_207670_bootrom_debug_load/`和`artifacts/runs/20260826_082642_076442_firmware_flash_run/`。

### 4.4.6 2026-08-26 11:09 CST 内部Load/Store Error结论修正

- 数字设计确认：IRQ bit8、bit9和bit10对应FMAC内部X1/X2 Load Error与Y Store Error，普通软件无法构造对应内部故障。
- 原`FMAC_P1_016`的容量边界、请求数量越界和额外写入只证明普通软件写入路径不会产生该内部错误，不能作为三个Feature的有效自然激励，也不能继续记为硬件FAIL。
- 公共`FMAC_F_041`、`FMAC_F_042`和`FMAC_F_043`继续保留硬件Feature事实，但平台状态改为`NOT_APPLICABLE`，不再建立PC Formal Case；`FMAC_P1_016`已从文档、注册表和PC源码删除。
- 三个Source的Enable、Mask、Force、Clear、Raw、Status和ISR投递控制链仍由`FMAC_P1_012`覆盖。若未来需要验证自然检测逻辑，只能使用RTL/VIO/DFT或仿真Fault Injection，不属于当前软件自动化测试范围。

### 4.4.7 2026-08-26 15:18 CST Float转Q15 Overflow清除方法修正

- 数字设计确认：`SR.FLOAT2FIXED_OVF_RPT`置位后，如果产生Overflow的实时硬件条件仍然存在，软件W1C不能清除该报告位；必须先完成一次不产生Overflow的正常转换，再执行软件清除。
- 4.4.5中的手动诊断在2.0f越界转换后立即执行`CR.CLR`、SR写1和SR写0，没有先输入正常数据，因此“只能通过CRG复位清除”的判断不完整，不能作为目标位无法软件清除的最终结论。
- 修正后的最小测试顺序固定为：输入2.0f触发Overflow并读出结果 -> 输入0.25f并读出结果以撤销实时条件 -> 执行动态Clear和目标状态W1C -> 回读`SR.FLOAT2FIXED_OVF_RPT`。
- ET6801 Chip Driver Test Extension、独立手动测试和公共Formal Case均已按该顺序修正，公共Wrap、Service、Wire和PC Driver接口没有变化。
- 该硬件行为限制了软件清除时机，设计上不合理；2026-08-28修正版手动诊断和Formal HIL均已PASS，历史FAIL由本次E21证据替代。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| FMAC_F_001 | SUPPORTED | X1 start/size均8-bit。 | ADAPTED | `FMAC_P1_001` |
| FMAC_F_002 | SUPPORTED | X1 Full WM=1/2/4/8；WM=1/2/4修正版参数节点FPGA HIL全部PASS。 | ADAPTED | `FMAC_P1_002` |
| FMAC_F_003 | SUPPORTED | SR提供X1 Spare Count；修正版FPGA HIL已验证半容量、Watermark边界和满容量计数。 | ADAPTED | `FMAC_P1_002` |
| FMAC_F_004 | SUPPORTED | Full条件为剩余空间低于Watermark；WM=1/2/4边界前后状态FPGA HIL全部PASS。 | ADAPTED | `FMAC_P1_002` |
| FMAC_F_005 | SUPPORTED | X2 start/size均8-bit。 | ADAPTED | `FMAC_P1_001` |
| FMAC_F_006 | SUPPORTED | Y start/size均8-bit。 | ADAPTED | `FMAC_P1_001` |
| FMAC_F_007 | SUPPORTED | Y Empty WM=1/2/4/8；当前FPGA HIL三组节点PASS。 | ADAPTED | `FMAC_P1_003` |
| FMAC_F_008 | SUPPORTED | SR提供Y Unread Count；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P1_003` |
| FMAC_F_009 | SUPPORTED | SR提供Y Empty状态；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P1_003` |
| FMAC_F_010 | SUPPORTED | FUNC=LOAD_X1，P=count；写入数量、运行态Spare与边界状态链路FPGA HIL PASS。 | ADAPTED | `FMAC_P1_002` |
| FMAC_F_011 | SUPPORTED | FUNC=LOAD_X2；IIR时P段后Q段。 | ADAPTED | `FMAC_P0_001`, `FMAC_P0_002` |
| FMAC_F_012 | SUPPORTED | FUNC=LOAD_Y，P=count；可用于Y状态和Float直通转换测试。 | ADAPTED | `FMAC_P0_002`, `FMAC_P0_003`, `FMAC_P1_003` |
| FMAC_F_013 | SUPPORTED | FUNC=FIR，P=前馈抽头；first-valid index仍UNKNOWN。 | ADAPTED | `FMAC_P0_001`, `FMAC_P2_001`, `FMAC_P3_001`, `FMAC_P3_002`, `FMAC_P3_003` |
| FMAC_F_014 | SUPPORTED | FUNC=IIR Direct Form 1，P前馈/Q反馈；当前固定参考向量HIL PASS，一般bit-exact语义仍保持UNKNOWN。 | ADAPTED | `FMAC_P0_002` |
| FMAC_F_015 | SUPPORTED | fixed=signed s(16,15)。 | ADAPTED | `FMAC_P0_001`, `FMAC_P0_002` |
| FMAC_F_016 | SUPPORTED | 环形X1/Y+数据口支持连续流；历史代码只作实现意图参考。 | ADAPTED | `FMAC_P1_004`, `FMAC_P3_001` |
| FMAC_F_017 | SUPPORTED | CLR清动态指针、内部控制和ENABLE，其他配置保持；转换报告位还需在实时条件撤销后执行W1C。 | ADAPTED | `FMAC_P0_003` |
| FMAC_F_018 | SUPPORTED | Float32->Q15；当前0.5单抽头FIR路径HIL PASS。 | ADAPTED | `FMAC_P1_005` |
| FMAC_F_019 | SUPPORTED | Q15->Float32；当前0.5单抽头FIR路径HIL PASS。 | ADAPTED | `FMAC_P1_005` |
| FMAC_F_020 | SUPPORTED | Float超范围钳位到Q15上/下边界；当前正负边界HIL PASS。 | ADAPTED | `FMAC_P1_006` |
| FMAC_F_021 | SUPPORTED | FLOAT2FIXED_OVF_RPT可观察；数字设计确认需先完成正常转换撤销实时条件，再执行W1C，修正版待HIL。 | ADAPTED | `FMAC_P1_006` |
| FMAC_F_022 | SUPPORTED | CR.CLIPEN控制内部s(26,22) Wrap/Clip。 | ADAPTED | `FMAC_P1_007` |
| FMAC_F_023 | SUPPORTED | ACC_OUT_WRAP_SEL控制最终Q15 Saturate/Wrap；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P1_008` |
| FMAC_F_024 | SUPPORTED | DAT_OUT_SEL=RAW/SAT12/SAT16；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P1_009` |
| FMAC_F_025 | SUPPORTED | OUT_CR.OFT为16-bit；当前代表Offset数值HIL PASS，完整signed解释仍有Gap。 | ADAPTED | `FMAC_P1_010` |
| FMAC_F_026 | SUPPORTED | ADD_OFT_IS_NEG_RPT置位HIL PASS；当前FPGA软件清除FAIL。 | ADAPTED | `FMAC_P1_010` |
| FMAC_F_027 | SUPPORTED | OUT_CR.SH=0..15=LEFT8..RIGHT7；当前代表移位HIL PASS。 | ADAPTED | `FMAC_P1_011` |
| FMAC_F_028 | SUPPORTED | 无X1可写空间后继续写产生X1 Overflow；`P1_002`修正版已验证置位和清除，`P1_014`自然IRQ刺激仍待修正。 | ADAPTED | `FMAC_P1_002`, `FMAC_P1_014` |
| FMAC_F_029 | SUPPORTED | 无Y未读数据后继续读产生Y Underflow；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P1_003`, `FMAC_P1_014` |
| FMAC_F_030 | SUPPORTED | SR.SAT_RPT。 | ADAPTED | `FMAC_P1_007`, `FMAC_P1_014` |
| FMAC_F_031 | SUPPORTED | DMA_WEN；FMAC_WR=2；X1 WM=1；只能idle修改。 | ADAPTED | `FMAC_P2_001`, `FMAC_P3_003` |
| FMAC_F_032 | SUPPORTED | DMA_REN；FMAC_RD=1；Y WM=1；只能idle修改。 | ADAPTED | `FMAC_P2_001`, `FMAC_P3_003` |
| FMAC_F_033 | SUPPORTED | IRQ bit0=X1_WRITE_REQUEST；自然Source HIL PASS。 | ADAPTED | `FMAC_P1_013` |
| FMAC_F_034 | SUPPORTED | IRQ bit1=Y_READ_REQUEST；自然Source HIL PASS。 | ADAPTED | `FMAC_P1_013` |
| FMAC_F_035 | SUPPORTED | IRQ bit2=SATURATION；自然Source HIL PASS。 | ADAPTED | `FMAC_P1_014` |
| FMAC_F_036 | SUPPORTED | IRQ bit3=X1_OVERFLOW；补偿FIR启动消费后，当前FPGA自然Source与ISR投递HIL PASS。 | ADAPTED | `FMAC_P1_014` |
| FMAC_F_037 | SUPPORTED | IRQ bit4=Y_UNDERFLOW；自然Source HIL PASS。 | ADAPTED | `FMAC_P1_014` |
| FMAC_F_038 | SUPPORTED | IRQ bit5=P_ERROR；最小自然刺激HIL PASS。 | ADAPTED | `FMAC_P1_015` |
| FMAC_F_039 | SUPPORTED | IRQ bit6=PQ_ERROR；最小自然刺激HIL PASS。 | ADAPTED | `FMAC_P1_015` |
| FMAC_F_040 | SUPPORTED | IRQ bit7=Q_ERROR；最小自然刺激HIL PASS。 | ADAPTED | `FMAC_P1_015` |
| FMAC_F_041 | SUPPORTED | IRQ bit8=X1_LOAD_ERROR；数字设计确认属于普通软件不可构造的内部故障。 | NOT_APPLICABLE | — |
| FMAC_F_042 | SUPPORTED | IRQ bit9=X2_LOAD_ERROR；数字设计确认属于普通软件不可构造的内部故障。 | NOT_APPLICABLE | — |
| FMAC_F_043 | SUPPORTED | IRQ bit10=Y_STORE_ERROR；数字设计确认属于普通软件不可构造的内部故障。 | NOT_APPLICABLE | — |
| FMAC_F_044 | SUPPORTED | INT_EN逐Source控制；11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_045 | SUPPORTED | INT_MASK逐Source控制；11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_046 | SUPPORTED | INT_CLR逐Source清除；11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_047 | SUPPORTED | INT_RAW_RPT提供Raw pending；11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_048 | SUPPORTED | INT_STATUS_RPT提供有效Status；11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_049 | SUPPORTED | INT_FORCE_IND按Source强制；Driver已修正且11类Source HIL PASS。 | ADAPTED | `FMAC_P1_012` |
| FMAC_F_050 | SUPPORTED | 物理IRQn=2；Service latch证明具体Source投递，delivery count仅为Measurement。 | ADAPTED | `FMAC_P1_012`, `FMAC_P1_013`, `FMAC_P1_014`, `FMAC_P1_015` |
| FMAC_F_051 | SUPPORTED | PARAM.ENABLE：1启动；软件清0停止；初始化功能硬件清0；当前FPGA HIL PASS。 | ADAPTED | `FMAC_P0_004` |

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| FMAC_P0_001 | ADAPTED | 当前FPGA HIL两组参数节点PASS；FIR稳态输出和X2 Load路径已验证。 |
| FMAC_P0_002 | ADAPTED | 当前FPGA HIL PASS；固定Q15 IIR参考向量、X1/Y初态和两段系数装载已验证。 |
| FMAC_P0_003 | ADAPTED | 当前FPGA HIL PASS；Y Load、Clear和配置快照已验证。 |
| FMAC_P0_004 | ADAPTED | 当前FPGA HIL PASS；Start/Stop和Active状态恢复已验证。 |
| FMAC_P1_001 | ADAPTED | 当前FPGA HIL PASS；配置快照经Driver Test Extension、Wrap和Service完整读回。 |
| FMAC_P1_002 | ADAPTED | 修正版WM=1/2/4三个FPGA HIL节点全部PASS；已验证Spare Count、Full Watermark边界以及Overflow置位/清除。 |
| FMAC_P1_003 | ADAPTED | 当前FPGA HIL三组节点PASS；Y Watermark、Unread、Empty和Underflow路径已验证。 |
| FMAC_P1_004 | ADAPTED | 当前FPGA HIL两组Chunk节点PASS；one-shot与固定Chunk输出一致。 |
| FMAC_P1_005 | ADAPTED | 当前FPGA HIL PASS；0.5单抽头FIR双向Float转换已验证。 |
| FMAC_P1_006 | ADAPTED | 历史FPGA HIL中正负钳位和Overflow置位正确；旧Case缺少清除前的正常输入，修正版待HIL。 |
| FMAC_P1_007 | ADAPTED | 当前FPGA HIL PASS；Internal Clip、Wrap和Saturation状态已验证。 |
| FMAC_P1_008 | ADAPTED | 当前FPGA HIL PASS；Final Saturate/Wrap稳态输出已验证。 |
| FMAC_P1_009 | ADAPTED | 当前FPGA HIL PASS；RAW/SAT12/SAT16输出模式已验证。 |
| FMAC_P1_010 | ADAPTED | 当前FPGA HIL PASS；Offset数值、Negative置位、正常输入恢复和SR写1清除链路均已闭合。 |
| FMAC_P1_011 | ADAPTED | 当前FPGA HIL PASS；LEFT1/NONE/RIGHT1移位对照已验证。 |
| FMAC_P1_012 | ADAPTED | 当前FPGA HIL全部11类Force参数节点PASS；IRQ控制矩阵和ISR latch/count已验证。 |
| FMAC_P1_013 | ADAPTED | 当前FPGA HIL两组节点PASS；X1/Y自然Request Source已验证。 |
| FMAC_P1_014 | ADAPTED | 修正版三个FPGA HIL节点全部PASS；Saturation、X1 Overflow和Y Underflow自然状态及IRQ投递均已验证。 |
| FMAC_P1_015 | ADAPTED | 当前FPGA HIL三组节点PASS；P、PQ、Q最小非法参数和合法恢复已验证。 |
| FMAC_P2_001 | ADAPTED | 当前FPGA HIL PASS；ET6801双向DMA映射和16-bit FIR路径已验证。 |
| FMAC_P3_001 | ADAPTED | 当前FPGA HIL PASS；4096项固定Chunk双轮稳定性已验证。 |
| FMAC_P3_002 | ADAPTED | 当前FPGA HIL三组节点PASS；64/128/240项DWT周期和功能结果已验证。 |
| FMAC_P3_003 | ADAPTED | 当前FPGA HIL PASS；DMA目标周期、Channel终态和稳态输出已验证。 |

# 第七章 Unknown / Conflict 与解除条件

| Gap / Conflict | 当前状态 | 解除条件 |
|---|---|---|
| `pre_freeze_rebaseline` | CLOSED_FOR_FREEZE | 本Freeze建立后，当前Feature/Case ID进入R100稳定绑定；后续任何语义变化必须按规则新增/迁移，不得继续以“重分析”为由复用ID。 |
| `fir_output_alignment_gap` | UNKNOWN | 取得ET6801目标设计/RTL对preload、Enable与第一项有效输出索引的正式定义并用受控向量回归；禁止最佳平移拟合。 |
| `param_r_semantics` | UNKNOWN | 取得ET6801设计/RTL对PARAM.R在FUNC=1..5中的定义；若无作用则保持非Feature。 |
| `iir_math_semantics_gap` | UNKNOWN | 取得反馈符号、Y初态排列和状态更新/量化规则，形成独立Direct Form 1模型。 |
| `iir_output_alignment_gap` | UNKNOWN | 与IIR状态初始化一起冻结第一项有效输出定义。 |
| `arithmetic_quantization_policy_gap` | UNKNOWN | 取得一般Q15中间截断/舍入顺序；必须解释历史`fmac_ut.log`的±1 LSB差异。 |
| `output_offset_full_domain_semantics_gap` | UNKNOWN | 取得OFT完整signed/高位扩展定义并增加边界向量。 |
| `parameter_error_trigger_semantics_gap` | CLOSED_BY_HIL | P超X1一项、P+Q超X2一项和Q超Y一项的最小刺激均形成对应Raw/Status/ISR latch。 |
| `load_error_trigger_semantics_gap` | CLOSED_NOT_SOFTWARE_TESTABLE | 数字设计确认X1/X2 Load Error与Y Store Error属于普通软件不可构造的内部故障；公共Feature保留，Formal Case删除。自然检测逻辑仅可由RTL/VIO/DFT或仿真Fault Injection验证。 |
| `x1_status_chain_hardware_conflict` | CLOSED_BY_HIL | `P1_002`补偿FIR启动消费后，Spare、Full Watermark与Overflow状态在WM=1/2/4三个节点全部PASS；`P1_014`收紧Y容量后，自然Overflow状态与IRQ投递也PASS。两项旧失败均由Case构造错误导致。 |
| `sticky_status_clear_hardware_conflict` | OPEN | Float Overflow和Negative-after-offset可自然置位，但CR.CLR、写1、写0均未清除；需RTL给出当前实现的清除语义。 |
| `dma_execution_mapping_gap` | CLOSED_BY_HIL | ET6801双向DMA映射已由P2_001和P3_003端到端验证。 |
| `timing_observer_gap` | CLOSED_BY_HIL | CPU和DMA目标周期接口均已采样，功能结果与周期Observation同时通过。 |
| D01~D09 | RESOLVED_AND_HIL_VERIFIED | 原SDK根因已修复，缺失观察/刺激接口隔离在Driver Test Extension；公共Wrap未直接访问寄存器，Keil构建、PFLASH运行和相关HIL路径已执行。 |

当前FMAC分析只有在剩余Hardware Truth Gap继续显式、23个Case源码不冒充硬件PASS、历史结果不升级为当前PASS时，才可作为后续HIL基线。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:23 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:14 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/fmac/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 23 | 23 | 23 | 0 | 0 | 0 | 46 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |
<!-- ET_CHIP_TEST_STATUS_END -->
