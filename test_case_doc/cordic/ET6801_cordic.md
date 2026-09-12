# ET6801 CORDIC Chip Analysis & Adaptation

> 本文件只记录 ET6801 的 CORDIC Hardware Truth、SDK Driver/Capability/Execution Mapping事实、历史验证输入，以及这些事实如何适配公共 `cordic.md`。
> 公共 Feature、Case、Oracle 与 SPEC 语义只由 `cordic.md` 定义；本文件可以出现实际寄存器/Field、物理IRQ和目标SDK事实，但不得形成第二套公共 Case Schema。
> 当前 CORDIC 已完成24个Formal Case的Case Contract映射。2026-08-28定向FPGA HIL确认：CORDIC_P1_003在人工批准的`1e-3`绝对误差预算下PASS。2026-08-28经设计人员确认，ET6801 CORDIC不支持DMA工作模式；公共CORDIC DMA Feature与Case代码继续保留，但`CORDIC_P2_001`对ET6801属于芯片能力不支持，不再作为FAIL复测。此前DMA超时结果只保留为历史证据。

## 分析基线与事实裁决

| Item | Current decision |
|---|---|
| Target | `ET6801 / CORDIC` |
| Public Contract | `test_case_doc/cordic/cordic.md` |
| Rule baseline | 当前活动 R100/R110/R120/R130/R140；Human Review method grammar以当前仓库R120为准 |
| Primary Hardware Truth | `ET6801.svd::CORDIC`；Capability记录SVD SHA256=`175A585FE736CA1300045BF147330296B97D3E3DCFAC2227FCC8B603F67AD61C` |
| Current SDK Driver | `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_cordic.h` + `Src/et6x_cordic.c` |
| Current Machine Capability | `pc/et_test_platform/profiles/chip_capabilities/et6801/ip/cordic.yaml` |
| Current-revision historical FPGA source | Google Drive `FPGATest/cordic_fpga_test.C`；35个设计函数，当前top-level只实际调用case34 |
| Historical requirement sources | ET3101 / ET6003 `cordic.json`，仅用于测试语义追溯 |
| Cross-chip manual | ET60157用户/寄存器手册只作同类CORDIC语义谱系与Revision Drift佐证，不用于覆盖ET6801 direct evidence |
| Current-SHA Software/HIL | Software Gate `773 PASS / 9 SKIP`；Working-tree定向FPGA HIL `19 PASS / 1 FAIL / 0 SKIP`，源码基线`edfd188173e93b3a580ba1d30587795c2ca1749c`且`source_dirty=true` |

事实冲突按以下顺序裁决：

```text
ET6801 direct SVD / target-chip integration evidence
> current ET6801 SDK implementation facts
> current-revision ET6801 validation source
> older revision / ET3101 / ET6003 historical requirement and code
> cross-chip ET60157 manual lineage
```

历史代码和跨芯片手册可以证明“长期存在什么语义、曾经想测什么、曾经如何刺激”，不能覆盖current SVD，也不能把旧DMA ID、旧控制模型或历史PASS写成当前结论。

## 第一章 Source Coverage / Source Item Trace

### 1.1 Source Coverage

| Source Domain | Search State | 本轮使用事实 | 结论边界 |
|---|---|---|---|
| `project-governance/ip-analysis-sources.yaml` | FOUND | 定位requirements、ET6801 SVD/Driver/FPGA验证/Test资料根 | 只负责导航，不定义权威级别 |
| requirements/test_case root | FOUND | ET3101 `cordic.json` 32个TP、ET6003 `cordic.json` 31个TP | 只用于测试语义全集追溯，不定义ET6801数值边界 |
| ET6801 SVD root / `CORDIC` | FOUND | 23个功能寄存器、9个函数入口、CTRL0模式、Status/IRQ、Raw结果 | Hardware Truth主来源 |
| ET6801 Driver root / CORDIC header+source | FOUND | SDK枚举、配置、输入、结果、Status/IRQ与zero-overhead helpers | 证明当前软件实现，不反向覆盖SVD |
| ET6801 FPGA verification root | FOUND | current-revision `cordic_fpga_test.C` 35个设计函数及目标侧Performance/DWT线索 | 历史验证设计输入；top-level当前仅case34 active，不能批量声称PASS |
| ET6801 Test root | FOUND | 旧Unit/Functional仍使用CTRL1/CTRL2、generic ARG/NARGS和旧DMA模型 | `STALE_REVISION_REFERENCE`；只保留需求/风险线索，禁止定义current寄存器/API/DMA事实 |
| ET6801 Machine Capability | FOUND | cordic0 identity/base/IRQ5，以及函数、位宽、Range、工作模式、结果数量、状态和IRQ Source等SVD可证明语义 | SVD无法完整表达的数值Codec、Scale公式、误差预算和确定性错误刺激由只读Execution Mapping补充 |
| ET60157 用户/寄存器手册 | FOUND | 提供Q31/Q15、float32、Scale、Precision、Polling/Interrupt/Zero-overhead/DMA等同类CORDIC历史语义 | 旧CTRL0/CTRL1/CTRL2架构且函数/IRQ集合不同，只作cross-chip lineage，不用于关闭ET6801 Scale/Codec/DMA等Gap |

### 1.2 ET3101 / ET6003 Historical Requirement Trace

| Source Item | 历史测试意图 | 当前Feature | 当前Case | Disposition | 说明 |
|---|---|---|---|---|---|
| TP01 | cos/sin历史拆分需求 | CORDIC_F_001 | CORDIC_P0_002/P0_003 | MERGED | 当前一次SINCOS事务产生双结果。 |
| TP02 | sin/cos历史拆分需求 | CORDIC_F_001 | CORDIC_P0_002/P0_003 | MERGED | 与TP1合并。 |
| TP03 | phase | CORDIC_F_002 | CORDIC_P0_002/P0_003 | MAPPED | 与modulus统一为PM双参数事务。 |
| TP04 | modulus | CORDIC_F_002 | CORDIC_P0_002/P0_003 | MERGED | 与TP3合并。 |
| TP05 | arctan | CORDIC_F_003 | CORDIC_P0_002/P0_003 | MAPPED | 独立atan Oracle。 |
| TP06 | hcos | CORDIC_F_004 | CORDIC_P0_002/P0_003 | MERGED | 当前HSINCOS双结果。 |
| TP07 | hsin | CORDIC_F_004 | CORDIC_P0_002/P0_003 | MERGED | 与TP6合并。 |
| TP08 | atanh | CORDIC_F_005 | CORDIC_P0_002/P0_003 | MAPPED | 合法域独立Oracle。 |
| TP09 | ln | CORDIC_F_007 | CORDIC_P0_002/P0_003 | MAPPED | 正值域。 |
| TP10 | sqrt | CORDIC_F_008 | CORDIC_P0_002/P0_003 | MAPPED | 非负域。 |
| TP11 | 16/32-bit输入宽度 | CORDIC_F_012/F013 | CORDIC_P1_002 | MAPPED | 当前ARGSIZE直接表达。 |
| TP12 | 16/32-bit输出宽度 | CORDIC_F_014/F015 | CORDIC_P1_002 | MAPPED | 当前RESSIZE及packed结果直接表达。 |
| TP13 | fixed/float | CORDIC_F_010/F011 | CORDIC_P0_002/P0_003 | SPLIT | 拆成独立定点/浮点矩阵。 |
| TP14 | 输入变量数量 | CORDIC_F_023/F031 | CORDIC_P1_006 | MAPPED | 旧generic配置迁移为PM顺序+当前参数计数。 |
| TP15 | 输入变量选择 | CORDIC_F_023/F043 | CORDIC_P1_006/P1_020 | SPLIT | 当前采用函数专用输入入口。 |
| TP16 | Scale | CORDIC_F_018 | CORDIC_P1_003 | MAPPED | 字段存在但公式Gap保留。 |
| TP17 | Precision/iteration | CORDIC_F_019 | CORDIC_P1_004 | MAPPED | 改为误差表征+高精度预算，不统一历史容差。 |
| TP18 | Result count | CORDIC_F_020/F021/F022 | CORDIC_P1_005 | SPLIT | 三类双结果函数参数化。 |
| TP19 | Interrupt work mode | CORDIC_F_025/F042 | CORDIC_P1_008 | MAPPED | 固定delay改为Source级Event+Deadline。 |
| TP20 | Polling mode | CORDIC_F_024/F028 | CORDIC_P1_007 | MAPPED | 无限while改为bounded polling。 |
| TP21 | Zero-overhead | CORDIC_F_026/F044 | CORDIC_P1_009/P3_003 | SPLIT | 功能与抗IRQ原子性分层。 |
| TP22 | DMA mode | CORDIC_F_027 | CORDIC_P2_001 | NOT_APPLICABLE | 设计人员确认ET6801 CORDIC不支持DMA工作模式；保留公共Feature和Case，不在ET6801上执行。 |
| TP23 | IRQ enable | CORDIC_F_037 | CORDIC_P1_017 | MAPPED | 按Source参数化。 |
| TP24 | IRQ mask | CORDIC_F_038/F041 | CORDIC_P1_018 | MAPPED | Raw/Status分层。 |
| TP25 | IRQ clear | CORDIC_F_040/F041 | CORDIC_P1_019 | MAPPED | 双Source位隔离。 |
| TP26 | IRQ force | CORDIC_F_039 | CORDIC_P1_017 | MAPPED | Force只作刺激，不代替自然IRQ Cases。 |
| TP27 | IRQ status | CORDIC_F_041 | CORDIC_P1_018/P1_019 | MAPPED | Mask后Status。 |
| TP28 | IRQ raw | CORDIC_F_041 | CORDIC_P1_018/P1_019 | MAPPED | Mask前Raw。 |
| TP29 | argument overflow | CORDIC_F_029/F035 | CORDIC_P1_011/P1_015 | SPLIT | 状态与自然IRQ分开。 |
| TP30 | calculation complete | CORDIC_F_028/F034 | CORDIC_P1_007/P1_008 | MERGED | COMPLETE状态W1C并入Polling Case，自然Complete IRQ并入Interrupt Case。 |
| TP31 | current arg count | CORDIC_F_031 | CORDIC_P1_006 | MAPPED | 按目标生命周期冻结Expected。 |
| TP32（ET3101-only） | float2fixed OVF/UDF | CORDIC_F_032/F033 | CORDIC_P1_013 | MAPPED | ET6003历史表无该TP；ET6801 current SVD/FPGATest均直接存在，边界刺激Gap保留。 |

旧requirements没有EXP/TAN、PM专用Arg2 Error和current多函数入口等新架构事实，因此历史TP全集不是current功能全集；current direct hardware新增项按R140独立Admission。

ET60157手册进一步证明“16/32-bit定点、float32、Scale、可配置迭代、Polling/Interrupt/Zero-overhead/DMA”属于同类CORDIC的长期语义谱系，但它使用旧`CTRL0/CTRL1/CTRL2 + function select + generic ARG`模型，且函数集合不含current ET6801新增的EXP/TAN、IRQ Source也更少。因此本轮只把它作为**跨芯片稳定语义佐证与Revision Drift证据**；所有ET6801具体Codec、Scale公式、DMA route、IRQ集合仍由ET6801 direct evidence决定。

### 1.3 Current-revision ET6801 FPGATest Source Trace

| Historical FPGA Case | Source intent | 当前公共Case | Disposition |
|---|---|---|---|
| case01 | SINCOS fixed sweep | CORDIC_P0_002 | MAPPED |
| case02 | SINCOS direct angle mode | CORDIC_P1_001 | MAPPED |
| case03 | SINCOS float sweep | CORDIC_P0_003 | MAPPED |
| case04 | PHASE_MODULUS fixed | CORDIC_P0_002 / CORDIC_P1_006 | MAPPED |
| case05 | PHASE_MODULUS float | CORDIC_P0_003 / CORDIC_P1_006 | MAPPED |
| case06 | ARCTAN fixed | CORDIC_P0_002 | MAPPED |
| case07 | ARCTAN float | CORDIC_P0_003 | MAPPED |
| case08 | HSINCOS fixed | CORDIC_P0_002 | MAPPED |
| case09 | HSINCOS float | CORDIC_P0_003 | MAPPED |
| case10 | EXP fixed | CORDIC_P0_002 | MAPPED |
| case11 | EXP float | CORDIC_P0_003 | MAPPED |
| case12 | ATANH fixed | CORDIC_P0_002 | MAPPED |
| case13 | ATANH float | CORDIC_P0_003 | MAPPED |
| case14 | LN fixed | CORDIC_P0_002 | MAPPED |
| case15 | LN float | CORDIC_P0_003 | MAPPED |
| case16 | SQRT fixed | CORDIC_P0_002 | MAPPED |
| case17 | SQRT float | CORDIC_P0_003 | MAPPED |
| case18 | TAN fixed special decode | CORDIC_P0_002 | MAPPED |
| case19 | TAN float | CORDIC_P0_003 | MAPPED |
| case20 | 16-bit width/packing | CORDIC_P1_002 | MAPPED |
| case21 | 16-bit direct angle | CORDIC_P1_001 / CORDIC_P1_002 | MAPPED |
| case22 | Scale 0..7 | CORDIC_P1_003 | MAPPED |
| case23 | Precision 1..8 | CORDIC_P1_004 | MAPPED_WITH_CORRECTION |
| case24 | Result count | CORDIC_P1_005 | MAPPED |
| case25 | Interrupt work mode | CORDIC_P1_008 | MAPPED |
| case26 | Zero-overhead | CORDIC_P1_009 | MAPPED |
| case27 | IRQ enable/force | CORDIC_P1_017 | MAPPED |
| case28 | IRQ raw/mask | CORDIC_P1_018 / CORDIC_P1_019 | MAPPED |
| case29 | Argument overflow IRQ | CORDIC_P1_011 / CORDIC_P1_015 | MAPPED |
| case30 | PM arg2 error status/IRQ/recovery | CORDIC_P1_016 | MAPPED |
| case31 | Complete status | CORDIC_P1_007 | MERGED |
| case32 | Current arg count lifecycle | CORDIC_P1_006 | MAPPED |
| case33 | Float2fixed OVF/UDF | CORDIC_P1_013 | MAPPED |
| case34 | Multi-function sequential result | CORDIC_P1_020 | MAPPED_WITH_ORDERING_REVIEW |
| case35 | IRQ interference / atomicity | CORDIC_P3_003 | SUPERSEDED_BY_STRONGER_ATOMIC_CONTRACT |

本轮对current FPGATest的关键质量裁决：

- `CORDIC_itn_test_23` 源码注释明确“低迭代误差判断不通过”，但代码仍对1..8节点统一使用同一历史容差；当前P1_004改为“逐节点误差表征 + 已发布包络 + 高精度预算”，不复制矛盾断言。
- `CORDIC_multi_func_parallel_test_34` 提供多函数连续提交/消费的真实设计线索，但其具体读取顺序不能被当作无限队列规格；当前P1_020要求先冻结安全请求/消费容量。
- `CORDIC_break_test_35` 用GPIO ISR直接再次访问CORDIC，只能证明“IRQ插入会破坏未保护write/read窗口”的历史风险；当前P3_003改为公共CORDIC原子事务 + 受控IRQ干扰，不复制跨层ISR写法。
- 历史随机输入、固定delay和无限while全部不进入新Contract；P3使用fixed seed，所有异步等待使用deadline。

## 第二章 Current Hardware / Driver Truth

### 2.1 ET6801 CORDIC Register Model

| Offset | Register | 关键硬件语义 |
|---:|---|---|
| 0x0004 | `CTRL0` | NRES / DMODE / FMODE / WORK_MODE / RESSIZE / ARGSIZE / SCALE / NOI |
| 0x0008 | `SINCOS_CAL` | SINCOS单输入入口 |
| 0x000C | `PM_CAL` | PHASE_MODULUS连续x/y或低精度packed xy入口 |
| 0x0010 | `ARCTAN_CAL` | ARCTAN单输入入口 |
| 0x0014 | `HSINCOS_CAL` | HSINCOS单输入入口 |
| 0x0018 | `HARCTAN_CAL` | ATANH单输入入口 |
| 0x001C | `EX_CAL` | EXP单输入入口 |
| 0x0020 | `LN_CAL` | LN单输入入口 |
| 0x0024 | `SQRT_CAL` | SQRT单输入入口 |
| 0x0028 | `TAN_CAL` | TAN单输入入口；SVD文字中误写sqrt，不能据此改函数身份 |
| 0x002C | `INT_EN` | 3个逻辑IRQ Source Enable |
| 0x0030 | `INT_MASK` | 3个逻辑IRQ Source Mask，1=Mask |
| 0x0034 | `INT_FORCE_IND` | 3个Source Force，写1硬件自清 |
| 0x0038 | `INT_CLR` | 3个Source Clear，写1硬件自清 |
| 0x003C | `INT_RAW_RPT` | Mask前Raw |
| 0x0040 | `INT_STATUS_RPT` | Mask后Status |
| 0x0044 | `STATUS_RPT` | ARG_OVERFLOW / COMPLETE / PM_ARG2_ERROR，W1C |
| 0x0048 | `WR_NARGS_CNT_RPT` | 当前参数写入计数 |
| 0x004C | `RPT_CORDIC_FLOAT2FIXED` | UDF/OVF sticky W1C |
| 0x0050 | `RES1_RPT` | 32-bit Result1 / 16-bit packed result word |
| 0x0054 | `RES2_RPT` | 32-bit Result2 |

### 2.2 CTRL0 可测试语义

| Field | Direct hardware fact | 当前自动化决策 |
|---|---|---|
| `CORDIC_HSINCOS_NRES` bit24 | 0=单结果消费；1=两个结果均读取 | P1_005参数化 |
| `CORDIC_PM_NRES` bit20 | 0=单结果消费；1=两个结果均读取 | P1_005参数化 |
| `CORDIC_SINCOS_NRES` bit16 | 0=单结果消费；1=两个结果均读取 | P1_005参数化 |
| `CORDIC_DMODE` bit13 | 0=归一化；1=sin/cos直接[-2π,+2π] | P1_001 |
| `CORDIC_FMODE` bit12 | 0=已处理定点；1=float内部转定点 | P0_002/P0_003/P1_013 |
| `CORDIC_WORK_MODE` bits10:11 | 00 Interrupt；01 Polling；10 Zero-overhead；11 DMA | P1_007~009/P2_001 |
| `CORDIC_RESSIZE` bit9 | 0=16-bit；1=32-bit | P1_002 |
| `CORDIC_ARGSIZE` bit8 | 0=16-bit；1=32-bit | P1_002 |
| `CORDIC_SCALE` bits5:7 | 3-bit Scale；sin/cos/phase/modulus不生效，其余函数公式引用LRS | P1_003；公式未取得前保持Gap |
| `CORDIC_NOI` bits0:4 | 实际周期=配置+1；超过MAX_ITER_CYC自动按最大值 | P1_004；SVD未给出MAX_ITER_CYC数值 |

### 2.3 16-bit Packing 与 PM 参数事务

SVD直接说明：16-bit Result 模式下，SINCOS / PHASE_MODULUS / HSINCOS 双结果会在 `RES1_RPT` 的高/低halfword打包；单结果函数只使用有效低halfword语义。P1_002必须先保存完整Raw word再做signed halfword decode。

`PM_CAL` 直接说明两种输入语义：

```text
full-precision path: x -> y sequential writes
lower-precision option: one packed Q1.15 xy write (when target Capability declares it)
```

P1_006主路径使用x→y顺序和`WR_NARGS_CNT_RPT`；packed option归入P1_002宽度/打包矩阵。

### 2.4 Status / IRQ

| Public semantic | ET6801 field/bit | 生命周期 |
|---|---|---|
| `STATUS.ARG_OVERFLOW` | `STATUS_RPT.WR_NARGS_OVF_RPT` bit0 | sticky W1C |
| `STATUS.COMPLETE` | `STATUS_RPT.RRDY_FLG_RPT` bit4 | W1C |
| `STATUS.PM_ARG2_ERROR` | `STATUS_RPT.WR_ARG2_ERROR_RPT` bit8 | W1C |
| `ARG_COUNT.CURRENT` | `WR_NARGS_CNT_RPT.WR_NARGS_CNT_RPT[1:0]` | read-only |
| `FLOAT2FIXED.UNDERFLOW` | `RPT_CORDIC_FLOAT2FIXED.UDF` bit0 | sticky W1C |
| `FLOAT2FIXED.OVERFLOW` | `RPT_CORDIC_FLOAT2FIXED.OVF` bit1 | sticky W1C |
| IRQ Source `ARG_OVERFLOW` | INT bit0 | Enable/Mask/Force/Clear/Raw/Status |
| IRQ Source `CALC_COMPLETE` | INT bit1 | Enable/Mask/Force/Clear/Raw/Status |
| IRQ Source `PM_ARG2_ERROR` | INT bit2 | Enable/Mask/Force/Clear/Raw/Status |

### 2.5 Current SDK Driver Defect / Gap Matrix

| ID | Severity | State | Current fact | 影响 / 解除条件 | Public Case |
|---|---|---|---|---|---|
| `CORDIC_DRV_001` | CRITICAL | RESOLVED_BY_TEST_EXTENSION | integer `CORDIC_calcultePM()`仍是错误历史Helper；公共Wrap不调用该Helper | `CORDIC_testExecuteZeroOverhead()`按稳定函数ID提交一/两个参数，P1_009已绑定正确路径 | P1_009 / P3_003 |
| `CORDIC_DRV_002` | HIGH | CLOSED_BY_HARDWARE_TRUTH | SVD虽定义WORK_MODE=3，但设计人员确认ET6801 CORDIC硬件不支持DMA工作模式；历史Request39/40与旧版寄存器模型不能作为当前芯片支持证据 | ET6801不再执行P2_001；公共Case保留给明确声明支持CORDIC DMA的后续芯片 | P2_001 |
| `CORDIC_DRV_003` | HIGH | RESOLVED_BY_STABLE_API | `CORIDC_IsRReady()`会读取后清除COMPLETE，但公共Wrap不调用该Helper | 公共Wrap使用无副作用`CORDIC_getStatus()`保存Snapshot，再由显式Clear动作执行W1C | P1_007 |
| `CORDIC_DRV_004` | HIGH | RESOLVED_BY_TEST_EXTENSION | 历史zero-overhead helpers无条件重新开中断 | `CORDIC_testExecuteZeroOverhead()`保存并恢复调用前PRIMASK，公共Wrap只走该入口 | P1_009 / P3_003 |
| `CORDIC_DRV_005` | MEDIUM | RESOLVED_AT_SERVICE_BOUNDARY | SDK IRQ API自身不做完整合法位校验 | 公共Service/Wrap只接受稳定三Source掩码并拒绝额外bit | P1_017~P1_019 |
| `CORDIC_DRV_006` | MEDIUM | CODEC_GAP | TAN fixed Raw格式主要来自current FPGATest验证实现，SVD未给出完整解码公式 | 形成独立codec helper + golden-vector regression并用current-HIL冻结 | P0_002 |

### 2.6 Current Machine Capability 与 Execution Mapping

当前 `cordic.yaml` 已由ET6801 SVD确定性生成实例、地址、IRQ、九类函数、16/32-bit位宽、Range、结果数量、工作模式、状态与IRQ Source。SVD不能完整表达的数值事实保存在：

```text
pc/et_test_platform/profiles/chip_execution_mappings/et6801/cordic_semantics.py
```

该映射只保存ET6801已审核的Codec、代表向量、Scale公式、精度节点和确定性错误刺激；公共Case只消费稳定逻辑字段，不导入ET6801寄存器、SDK枚举或地址。

## 第三章 Stable Endpoint -> ET6801 Register / Observer Mapping

| Public Stable Endpoint | ET6801 Actual Source | Lifecycle / Note | Current Status |
|---|---|---|---|
| `CAPABILITY.RUNTIME` | 未来CORDIC Firmware Service `CAPABILITIES_GET` | 只读目标侧能力快照；不是物理寄存器别名 | IMPLEMENTATION_GAP |
| `RESULT.PRIMARY` | `RES1_RPT.CORDIC_RES1_RPT` | 32-bit Raw Result1 | MAPPED |
| `RESULT.SECONDARY` | `RES2_RPT.CORDIC_RES2_RPT` | 32-bit Raw Result2 | MAPPED |
| `RESULT.PACKED16` | `RES1_RPT.CORDIC_RES1_RPT` | 保留完整32-bit后按RESSIZE规则拆halfword | MAPPED |
| `STATUS.COMPLETE` | `STATUS_RPT.RRDY_FLG_RPT` | W1C；禁止用读后自动Clear helper作为Formal getter | MAPPED |
| `STATUS.ARG_OVERFLOW` | `STATUS_RPT.WR_NARGS_OVF_RPT` | W1C；确定容量刺激仍需Mapping | MAPPED |
| `STATUS.PM_ARG2_ERROR` | `STATUS_RPT.WR_ARG2_ERROR_RPT` | W1C | MAPPED |
| `ARG_COUNT.CURRENT` | `WR_NARGS_CNT_RPT.WR_NARGS_CNT_RPT` | 2-bit只读；阶段生命周期需冻结 | MAPPED / LIFECYCLE_GAP |
| `FLOAT2FIXED.OVERFLOW` | `RPT_CORDIC_FLOAT2FIXED.OVF` | sticky W1C；阈值待冻结 | MAPPED / BOUNDARY_GAP |
| `FLOAT2FIXED.UNDERFLOW` | `RPT_CORDIC_FLOAT2FIXED.UDF` | sticky W1C；阈值待冻结 | MAPPED / BOUNDARY_GAP |
| `IRQ_RAW.ARG_OVERFLOW` | `INT_RAW_RPT` bit0 | Mask前Raw | MAPPED |
| `IRQ_RAW.CALC_COMPLETE` | `INT_RAW_RPT` bit1 | Mask前Raw | MAPPED |
| `IRQ_RAW.PM_ARG2_ERROR` | `INT_RAW_RPT` bit2 | Mask前Raw | MAPPED |
| `IRQ_STATUS.ARG_OVERFLOW` | `INT_STATUS_RPT` bit0 | Mask后Status | MAPPED |
| `IRQ_STATUS.CALC_COMPLETE` | `INT_STATUS_RPT` bit1 | Mask后Status | MAPPED |
| `IRQ_STATUS.PM_ARG2_ERROR` | `INT_STATUS_RPT` bit2 | Mask后Status | MAPPED |
| `IRQ_DELIVERY.LATCHED_SOURCE` | 未来CORDIC IRQ Service / ISR latch | Service事实，不得改名为INT_RAW/STATUS | IMPLEMENTATION_GAP |
| `TIMING.CYCLE_COUNT` | Cortex-M DWT或等价目标侧cycle counter Test Extension | 不是CORDIC寄存器；仅结果正确样本进入统计 | MAPPING_GAP |
| `DMA_CHANNEL_STATUS` | Peer DMA Channel hardware status | 公共Case观测项；ET6801设计确认不支持CORDIC DMA | NOT_APPLICABLE_ET6801 |
| `DMA_DESTINATION_WORD` | Peer DMA destination memory/endpoint | 公共Case观测项；ET6801不配置CORDIC DMA Endpoint | NOT_APPLICABLE_ET6801 |

### 3.1 IRQ Source Bit Mapping

| Public Source | Enable/Mask/Force/Clear/Raw/Status bit |
|---|---:|
| ARG_OVERFLOW | 0 |
| CALC_COMPLETE | 1 |
| PM_ARG2_ERROR | 2 |

### 3.2 数学Codec与精度当前边界

current FPGATest能证明大量“当前验证假设”，但下列内容没有被direct SVD完整定义，不能静默升级为公共规格：

- FIXED各函数的Q格式、Scale补偿和TAN特殊Raw解码；
- 各函数/格式/precision节点的正式允许误差；
- `MAX_ITER_CYC`的目标硬件数值上限；
- float2fixed OVF/UDF的精确阈值与所有适用函数；
- 多函数连续提交的安全队列/结果消费容量。

这些项分别进入 `cordic_fixed_codec_mapping_gap / cordic_scale_formula_gap / cordic_accuracy_budget_gap / cordic_precision_limit_mapping_gap / cordic_float2fixed_boundary_gap / cordic_request_capacity_mapping_gap`。

## 第四章 ET6801 Gap / Risk Registry

| Gap ID | Type | 当前事实 | 解除条件 |
|---|---|---|---|
| `cordic_capability_semantic_mapping_gap` | CLOSED | Machine Capability已发布SVD可证明的函数、位宽、Range、工作模式、结果数量、状态和IRQ语义 | 后续新增SVD语义规则必须继续由generator与audit regression闭合 |
| `cordic_fixed_codec_mapping_gap` | MAPPING | current FPGATest含Q31、扩展角度及函数特定scale处理，但SVD未给全公式 | 获得LRS/RTL/设计依据或批准的current-HIL codec冻结，并建立PC pure-codec vectors |
| `cordic_accuracy_budget_gap` | SEMANTIC | 人工复核已批准ET6801当前数学结果使用`1e-3`绝对误差预算；低迭代节点仍不冒充逐节点精度包络 | 当前Formal Case使用已批准预算；未来取得正式逐函数/逐precision规格后再细化 |
| `cordic_scale_formula_gap` | SEMANTIC | SVD引用内部LRS说明其余函数Scale公式，本轮未取得该权威资料 | 取得LRS/RTL/设计确认并形成Chip Codec mapping |
| `cordic_precision_limit_mapping_gap` | MAPPING | SVD字段5-bit且提到MAX_ITER_CYC但无数值；current Driver/FPGATest仅1..8 | 目标设计资料确认硬件上限与平台公开option set |
| `cordic_arg_count_lifecycle_mapping_gap` | SEMANTIC | FPGATest case32显示ARG_COUNT随结果消费产生1→0、1→2等不同阶段 | 权威冻结每阶段Expected与结果消费关系 |
| `cordic_argument_capacity_mapping_gap` | SEMANTIC | ARG_OVERFLOW位存在，但最小确定容量未由SVD给数值 | 设计资料/RTL/current-HIL确定容量和最小越界刺激 |
| `cordic_float2fixed_boundary_gap` | SEMANTIC | OVF/UDF位存在；historical sqrt/ln数值只是验证向量 | 冻结目标边界向量及邻近合法对照 |
| `cordic_irq_service_gap` | CLOSED | CORDIC Service已提供Source级ISR latch/event_count，并与Raw/Status分层记录 | 已由CORDIC IRQ Service/Case闭合；更强异步干扰仍单独评估 |
| `cordic_current_pm_helper_bug` | IMPLEMENTATION | SDK integer zero-overhead PM helper仍写SINCOS入口且参数模型不符合x→y；公共测试路径不调用该Helper | 修SDK，或继续由CORDIC Test Extension generic path隔离错误Helper |
| `cordic_zero_overhead_atomicity_gap` | CLOSED | CORDIC Test Extension保存/恢复调用者PRIMASK，Wrap只调用该Driver接口 | 已由P3_003受控Pending与Driver扩展闭合当前测试路径 |
| `cordic_dma_execution_mapping_gap` | MAPPING | 已使用当前SVD端点及ET6801验证工程闭合Mapping：Controller 0，输入/输出Interface 0/1，输入Request 40（CORDIC_RX）、输出Request 39（CORDIC_TX），端点`SQRT_CAL=0x50000024`与`RES1_RPT=0x50000050` | 定向HIL确认当前Mapping与FPGA实现一致 |
| `cordic_timing_observer_mapping_gap` | CLOSED | CORDIC Test Extension在目标侧DWT边界内返回cycle count，Service/Case只消费稳定结果 | 已由P3_002 timed命令和目标侧周期证据闭合 |
| `cordic_reset_execution_mapping_gap` | CLOSED | CRG专属Driver/Service/Wrap通过生成CMSIS的GTEN0/SRST0 CORDIC0 bit20建立芯片映射，PC Case负责复位后重新配置 | 已由P0_004与P1_016跨IP编排闭合 |
| `cordic_request_capacity_mapping_gap` | SEMANTIC | case34提供多函数顺序线索但不等于queue spec | 设计/RTL/current-HIL冻结安全submit/consume协议 |

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| CORDIC_F_001 | SUPPORTED | SINCOS_CAL + RES1/RES2；Float32特殊节点与公共执行链已适配。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_002 | SUPPORTED | PM_CAL连续x/y输入 + RES1/RES2；Float32特殊节点与参数顺序链已适配，16-bit packed仍单独保持Mapping Gap。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_003 | SUPPORTED | ARCTAN_CAL单输入Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_004 | SUPPORTED | HSINCOS_CAL单输入双结果Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_005 | SUPPORTED | HARCTAN_CAL单输入Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_006 | SUPPORTED | EX_CAL单输入Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_007 | SUPPORTED | LN_CAL单输入Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_008 | SUPPORTED | SQRT_CAL单输入Float32特殊节点已由公共Case表达。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_009 | SUPPORTED | TAN_CAL单输入Float32特殊节点已由公共Case表达；SVD描述中的函数名copy/paste错误不进入公共语义。 | ADAPTED | CORDIC_P0_002, CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_010 | SUPPORTED | CTRL0.FMODE=0；ET6801 Execution Mapping已冻结当前代表向量的定点Codec、Scale与补偿语义。 | ADAPTED | CORDIC_P0_002 |
| CORDIC_F_011 | SUPPORTED | CTRL0.FMODE=1为float输入内部转换；公共Driver/Service/Wrap与特殊节点Case已适配。 | ADAPTED | CORDIC_P0_003, CORDIC_P3_001 |
| CORDIC_F_012 | SUPPORTED | CTRL0.ARGSIZE=16；Execution Mapping已冻结16-bit参数位于提交字高半字的当前Codec。 | ADAPTED | CORDIC_P1_002 |
| CORDIC_F_013 | SUPPORTED | CTRL0.ARGSIZE=32；Execution Mapping已冻结32-bit定点Codec。 | ADAPTED | CORDIC_P0_002, CORDIC_P1_002 |
| CORDIC_F_014 | SUPPORTED | CTRL0.RESSIZE=16；SVD与current FPGATest共同证明双结果在RES1高/低16-bit打包。 | ADAPTED | CORDIC_P1_002 |
| CORDIC_F_015 | SUPPORTED | CTRL0.RESSIZE=32；RES1/RES2分别保存两个32-bit结果。 | ADAPTED | CORDIC_P0_002, CORDIC_P1_002 |
| CORDIC_F_016 | SUPPORTED | CTRL0.DMODE=0；Execution Mapping冻结Normalized的角度除数和定点Codec。 | ADAPTED | CORDIC_P1_001 |
| CORDIC_F_017 | SUPPORTED | CTRL0.DMODE=1；Execution Mapping冻结Direct Angle的小数位Codec。 | ADAPTED | CORDIC_P1_001 |
| CORDIC_F_018 | SUPPORTED | CTRL0.SCALE为3-bit；P1_003同时覆盖不受影响的SINCOS以及current FPGATest已证明的ARCTAN输入/输出Scale公式。其他函数Scale公式仍保留公共Gap。 | ADAPTED | CORDIC_P1_003 |
| CORDIC_F_019 | SUPPORTED | CTRL0.NOI为5-bit；Execution Mapping按current Driver/FPGATest冻结平台计划节点1..8，硬件完整MAX_ITER_CYC仍保留Gap。 | ADAPTED | CORDIC_P1_004 |
| CORDIC_F_020 | SUPPORTED | CTRL0.SINCOS_NRES的一结果/两结果公共配置和Case已适配。 | ADAPTED | CORDIC_P1_005 |
| CORDIC_F_021 | SUPPORTED | CTRL0.PM_NRES的一结果/两结果公共配置和Case已适配。 | ADAPTED | CORDIC_P1_005 |
| CORDIC_F_022 | SUPPORTED | CTRL0.HSINCOS_NRES的一结果/两结果公共配置和Case已适配。 | ADAPTED | CORDIC_P1_005 |
| CORDIC_F_023 | SUPPORTED | PM连续x/y参数顺序、参数计数和ARG2错误恢复公共Case已适配。 | ADAPTED | CORDIC_P1_006, CORDIC_P1_016 |
| CORDIC_F_024 | SUPPORTED | CTRL0.WORK_MODE=01 Polling与COMPLETE终态Case已适配。 | ADAPTED | CORDIC_P1_007 |
| CORDIC_F_025 | SUPPORTED | CTRL0.WORK_MODE=00 Interrupt与自然Complete投递Case已适配。 | ADAPTED | CORDIC_P1_008 |
| CORDIC_F_026 | SUPPORTED | CTRL0.WORK_MODE=10基础原子事务已适配；受控IRQ干扰强度仍由P3_003单独保留。 | ADAPTED | CORDIC_P1_009, CORDIC_P3_003 |
| CORDIC_F_027 | UNSUPPORTED | 设计人员确认ET6801 CORDIC不支持DMA工作模式；SVD中的CTRL0.WORK_MODE=11及历史Request39/40不能覆盖该硬件事实。 | NOT_APPLICABLE | CORDIC_P2_001 |
| CORDIC_F_028 | SUPPORTED | STATUS_RPT.RRDY_FLG_RPT的Polling观测与W1C复核已适配。 | ADAPTED | CORDIC_P1_007 |
| CORDIC_F_029 | SUPPORTED | STATUS_RPT.WR_NARGS_OVF_RPT，W1C；Execution Mapping冻结current FPGATest/HIL已证明的四次未消费提交刺激。该Case不声称测得最小容量。 | ADAPTED | CORDIC_P1_011 |
| CORDIC_F_030 | SUPPORTED | STATUS_RPT.WR_ARG2_ERROR_RPT自然刺激与W1C已适配；ET6801 FPGA实测表明清报告位后仍需由CRG复位CORDIC0才能清内部错误事务。 | ADAPTED | CORDIC_P1_016 |
| CORDIC_F_031 | SUPPORTED | WR_NARGS_CNT_RPT[1:0]的0→1→0参数生命周期Case已适配。 | ADAPTED | CORDIC_P1_006 |
| CORDIC_F_032 | SUPPORTED | RPT_CORDIC_FLOAT2FIXED.OVF sticky W1C；Execution Mapping冻结SQRT确定性OVF刺激和恢复向量，不声称精确阈值。 | ADAPTED | CORDIC_P1_013 |
| CORDIC_F_033 | SUPPORTED | RPT_CORDIC_FLOAT2FIXED.UDF sticky W1C；Execution Mapping冻结SQRT确定性UDF刺激和恢复向量，不声称精确阈值。 | ADAPTED | CORDIC_P1_013 |
| CORDIC_F_034 | SUPPORTED | INT bit1 CALC_COMPLETE自然Source与ISR Evidence已适配。 | ADAPTED | CORDIC_P1_008 |
| CORDIC_F_035 | SUPPORTED | INT bit0 ARG_OVERFLOW；P1_015复用已审核的四次未消费提交刺激，自然形成状态与真实ISR投递。 | ADAPTED | CORDIC_P1_015 |
| CORDIC_F_036 | SUPPORTED | INT bit2 PM_ARG2_ERROR自然Source与恢复Case已适配。 | ADAPTED | CORDIC_P1_016 |
| CORDIC_F_037 | SUPPORTED | INT_EN低3bit的Enable/Disable与自然/Force投递Case已适配。 | ADAPTED | CORDIC_P1_008, CORDIC_P1_015, CORDIC_P1_016, CORDIC_P1_017 |
| CORDIC_F_038 | SUPPORTED | INT_MASK低3bit的Mask/Unmask分层Case已适配。 | ADAPTED | CORDIC_P1_018 |
| CORDIC_F_039 | SUPPORTED | INT_FORCE_IND低3bit的软件Force控制路径已适配。 | ADAPTED | CORDIC_P1_017 |
| CORDIC_F_040 | SUPPORTED | INT_CLR低3bit的目标Source精确Clear Case已适配。 | ADAPTED | CORDIC_P1_019 |
| CORDIC_F_041 | SUPPORTED | INT_RAW_RPT与INT_STATUS_RPT的Mask前/后分层观测已适配。 | ADAPTED | CORDIC_P1_018, CORDIC_P1_019 |
| CORDIC_F_042 | SUPPORTED | 硬件单IRQ line与公共Source级ISR latch/event_count已适配。 | ADAPTED | CORDIC_P1_008, CORDIC_P1_015, CORDIC_P1_016, CORDIC_P1_017 |
| CORDIC_F_043 | SUPPORTED | 九类函数顺序请求、消费和状态清理Case已适配。 | ADAPTED | CORDIC_P1_020 |
| CORDIC_F_044 | SUPPORTED | Zero-overhead硬件模式通过CORDIC Test Extension保存/恢复PRIMASK；公共Wrap只调用该稳定Driver入口，错误SDK PM helper不进入测试路径。 | ADAPTED | CORDIC_P3_003 |
| CORDIC_F_045 | SUPPORTED | current ET6801目标侧DWT周期计数通过CORDIC timed Service返回；公共Case只消费稳定周期结果。 | ADAPTED | CORDIC_P3_002 |
| CORDIC_F_046 | SUPPORTED | CRG GTEN0/SRST0 bit20控制CPU0 CORDIC；芯片映射使用生成CMSIS字段位置，复位恢复由PC Case跨IP编排。 | ADAPTED | CORDIC_P0_004, CORDIC_P1_016 |

说明：`SUPPORTED`只表示目标Hardware Truth已确认；`Platform`表示当前自动化链路状态，不等于current-SHA HIL PASS。P1_003的Scale功能字段本身SUPPORTED，但精确公式仍是NEEDS_VERIFICATION。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| CORDIC_P0_002 | ADAPTED | 九类代表向量的定点Codec、函数Scale/补偿和当前误差预算由ET6801 Execution Mapping提供；一般合法域与权威全域误差包络仍保留公共Gap。 |
| CORDIC_P0_003 | ADAPTED | 九类Float32特殊节点使用精确Raw Golden，公共执行链已实现；一般合法域精度仍由P3_001保留。 |
| CORDIC_P0_004 | ADAPTED | 外层CRG专属Driver/Service/Wrap已提供CORDIC复位映射；Case负责复位前后重新配置与结果恢复。 |
| CORDIC_P1_001 | ADAPTED | SVD声明两种Range，Execution Mapping提供Normalized/Direct Raw Codec；Case对同一π/2逻辑角度建立双路径Oracle。 |
| CORDIC_P1_002 | ADAPTED | SVD声明位宽和16-bit双结果打包，Execution Mapping提供参数存储位置与定点Codec；Case用非零π/4节点覆盖四种组合。 |
| CORDIC_P1_003 | ADAPTED | Case覆盖SINCOS不受Scale影响以及current FPGATest提供的ARCTAN Scale 0..7公式；人工复核已批准ET6801按`1e-3`绝对误差预算验收，Scale=7历史误差`1.475113549724849e-4`在预算内。其他函数的Scale公式不由本Case宣称。 |
| CORDIC_P1_004 | ADAPTED | Execution Mapping冻结当前平台计划节点1..8和最高节点误差预算；硬件未公开的完整MAX_ITER_CYC不在本Case结论内。 |
| CORDIC_P1_005 | ADAPTED | SINCOS/PM/HSINCOS的一结果/两结果配置与硬件输出Case已实现。 |
| CORDIC_P1_006 | ADAPTED | PM x→y参数计数0→1→0生命周期与结果消费Case已实现。 |
| CORDIC_P1_007 | ADAPTED | Polling完成、结果读取及COMPLETE W1C复核已合并为一个原子Case。 |
| CORDIC_P1_008 | ADAPTED | Interrupt模式自然CALC_COMPLETE Source、ISR latch和event_count Case已实现。 |
| CORDIC_P1_009 | ADAPTED | Zero-overhead基础原子事务与结果校验已实现；IRQ干扰强度留在P3_003。 |
| CORDIC_P1_011 | ADAPTED | Execution Mapping冻结current FPGATest/HIL已证明的四次未消费提交刺激；Case验证自然状态、W1C和恢复，但不声称最小容量。 |
| CORDIC_P1_013 | ADAPTED | Execution Mapping冻结current FPGATest/HIL已证明的SQRT OVF/UDF与恢复向量；Case验证状态因果，不声称精确数值边界。 |
| CORDIC_P1_015 | ADAPTED | 复用P1_011的已审核刺激，验证ARG_OVERFLOW硬件状态、Service事件计数和自然IRQ投递。 |
| CORDIC_P1_016 | ADAPTED | PM_ARG2_ERROR自然Source、ISR Evidence、W1C报告位清除及CRG模块复位恢复已实现。 |
| CORDIC_P1_017 | ADAPTED | 三类Source的Enable/Disable/Force与Delivery控制矩阵已实现。 |
| CORDIC_P1_018 | ADAPTED | 三类Source的Mask、Raw、Status分层Case已实现。 |
| CORDIC_P1_019 | ADAPTED | 三类Source的目标Clear与非目标保持Case已实现。 |
| CORDIC_P1_020 | ADAPTED | 九类函数顺序执行、结果消费和终态清理Case已实现。 |
| CORDIC_P2_001 | NOT_APPLICABLE | 公共Case代码保留；设计人员确认ET6801 CORDIC不支持DMA工作模式，因此ET6801不执行该Case。 |
| CORDIC_P3_001 | ADAPTED | 仅实现九类Float32代表合法节点的固定重复稳定性；不宣称覆盖定点Codec、边界、完整合法域或统一accuracy budget。 |
| CORDIC_P3_002 | ADAPTED | CORDIC timed Service通过目标侧DWT返回周期结果，Case只验证数学结果正确前提下的周期样本。 |
| CORDIC_P3_003 | ADAPTED | Case通过公共Zero-Overhead与IRQ控制接口执行受控Pending隔离；更强的异步ISR干扰仍由独立Gap保留。 |

## 第七章 Current Review Conclusion

### 7.1 本轮重构结论

1. **Revision Drift已显式隔离。** old generic CTRL1/CTRL2/NARGS/ARG/DMA模型不再进入current ET6801 Hardware Truth；当前模型只由direct SVD/current Driver/current-revision验证源定义。
2. **数学Oracle重新分层。** 九类函数的Expected由PC独立数学函数产生，但Raw Codec、Scale和accuracy budget必须有目标映射，历史magic factor不直接升级为稳定规格。
3. **46个稳定Feature。** F001～F045表达可由硬件行为直接证明的数学功能、模式、状态、IRQ与数据路径，F046表达模块Reset/Recovery；合法域边界与重复稳定性保留为P3测试维度，不再重复发布成硬件Feature。
4. **24个SPEC完成Human Review。** 已实现Case与Registry保持一一对应；P2_001作为公共Case保留，但ET6801能力声明为不支持。Capability一致性属于平台发现/契约门禁，不计入CORDIC硬件Case覆盖。
5. **IRQ证据分层。** Raw / Status / Service latch / event_count分开保存；Force只验证控制路径，自然Complete/Overflow类因果由独立Case证明。
6. **Zero-overhead原子性强化。** current PM int helper错误和PRIMASK恢复缺陷已列为阻塞Gap；P3_003不复制历史GPIO ISR跨层写法。
7. **DMA Case保留，ET6801不执行。** 公共F027/P2_001继续服务于支持CORDIC DMA的芯片；设计人员已确认ET6801不支持该模式，不再依据SVD字段或历史Request组合反复构造ET6801测试。
8. **Precision不伪造统一阈值。** 低迭代节点先记录误差；只有已发布节点包络/最高精度budget才能形成严格PASS。
9. **跨芯片ET60157资料只做谱系佐证。** 它确认Q31/Q15、float、Scale、Precision和多种工作模式长期存在，但旧架构不能关闭ET6801的Codec/Scale/DMA/IRQ Gap。

### 7.2 当前状态

```text
CORDIC public Feature catalog: 46 stable Features
CORDIC ET_CASE_SPEC: 24 / IMPLEMENTED
Formal Case code / registry: 24 / IMPLEMENTED
PC Driver / Firmware Service / Common Wrap: EXISTING / HIL_NOT_VERIFIED
Machine Capability semantic mapping: SVD SEMANTICS COMPLETE / NUMERIC EXECUTION MAPPING ADDED
Legacy full Working-tree FPGA HIL: EXECUTED / 53 executions / 52 PASS / 1 SKIP / 0 FAIL
Historical semantic migration HIL before hardware confirmation: EXECUTED / 20 executions / 19 PASS / 1 FAIL / 0 SKIP
Current logical classification after hardware confirmation: 7 PASS / 0 FAIL / 1 SKIP
Contract classification after hardware confirmation: ADAPTED=23 / NOT_APPLICABLE=1
Semantic mapping Cases current-code HIL PASS: CORDIC_P0_002, CORDIC_P1_001, CORDIC_P1_002, CORDIC_P1_004, CORDIC_P1_011, CORDIC_P1_013, CORDIC_P1_015
2026-08-28 targeted HIL PASS: CORDIC_P1_003 / ARCTAN Scale 0..7 within approved 1e-3 budget
2026-08-28 historical targeted HIL result: CORDIC_P2_001 / DMA input and output channels did not complete within 15 s；设计确认后归类为NOT_APPLICABLE
Firmware / Registry: et6801-silicon-common-v0.1 / d7dd2c5d
Exact committed SHA FPGA HIL: NOT_PROVEN / source revision recorded but working tree is dirty
Current-SHA Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
Historical FPGA / requirement corpus: TRACEABLE DESIGN INPUT ONLY
```

旧Runner结果证明上一版实现能够执行，但不能证明本轮语义迁移后的当前代码。上述8个Case已经完成current-code HIL：7个逻辑Case通过，P1_003稳定复现Scale=7在历史`1e-4`预算下的失败。2026-08-27人工复核已批准ET6801当前按`1e-3`绝对误差预算验收，因此该历史现象不再解释为硬件失败；仍需用当前代码定向回归形成新结果。

### 7.3 下一阶段验证与映射入口条件

CORDIC Case代码与Contract已完成；后续只在取得目标芯片直接证据后闭合以下映射或验证Gap：

```text
1. P1_003已按批准的ET6801 `1e-3`绝对误差预算完成定向回归并PASS
2. 补充尚未取得的其他函数Scale公式和权威全域accuracy budget
3. 补充硬件完整MAX_ITER_CYC、精确ARG_OVERFLOW容量与Float2Fixed阈值
4. 后续芯片只有在硬件能力明确支持CORDIC DMA时，才补充对应Execution Mapping
```

任何Gap解除后只更新对应Feature/Case适配状态；不得因为某个Driver API补齐就批量改写其他Case。ET6801的P2_001只有在设计人员重新确认硬件支持后才允许恢复执行。

### 7.4 当前未通过测试记录

时间：2026-08-24 20:42 CST

| Case | 测试环境 | 实际硬件现象 | 已排除的问题 | 当前判定 | 闭环条件 |
|---|---|---|---|---|---|
| `CORDIC_P2_001` | ET6801 FPGA，DMA0双通道，SQRT(0.25) Q1.31单输入/单结果 | 输入Request40、输出Request39及SQRT/RES1端点均已配置；两条DMA Channel在15秒内未进入Free | P1_003已独立PASS；P2_001已对齐历史ET6801 Request方向、端点、工作模式切换顺序和单字搬运 | `HIL_FAIL` | RTL/设计确认当前bit中的CORDIC DMA Request路径与Request ID |

本项暂不能直接判定为RTL缺陷，也不能通过自行放宽公共阈值关闭。原始证据未随仓库保留。

2026-08-24独立固件复测再次得到`Scale=7`、输入Raw=`0x40000000`、实际Raw=`0x007EB700`、期望Raw=`0x007EBA14`，绝对差值=`0x00000314`，仍超过当前容差`0x00000216`；完成状态和清除路径均正常。该结果确认现象可重复，但不把尚未权威化的精度预算解释为RTL缺陷。原始证据未随仓库保留。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:25 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:11 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | NOT_RETAINED |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 24 | 24 | 23 | 0 | 1 | 0 | 53 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `CORDIC_P2_001` | FPGA | SKIP | `CORDIC_F_027` / DMA工作模式 | Runtime Capability明确拒绝CORDIC DMA工作模式，Case未向硬件发起DMA刺激 | 2026-08-28设计人员确认ET6801 CORDIC不支持DMA工作模式，Case适配状态为NOT_APPLICABLE；不是Case逻辑FAIL，也不是外部接线阻塞 | 仅当设计人员重新确认ET6801硬件支持该模式时复测 | NOT_RETAINED |
<!-- ET_CHIP_TEST_STATUS_END -->

### 2026-08-26 12:15 CST 状态分类复核

`CORDIC_P2_001`在2026-08-21旧全量运行中的SKIP是历史Runner事实，Artifact保持不变；2026-08-28已使用当前Mapping完成真实HIL，当前分类升级为`FAIL`。该项不是外部接线阻塞，也不得重新降级为SKIP。

### 2026-08-28 15:12 CST 设计确认后的最终修正

设计人员确认ET6801 CORDIC硬件不支持DMA工作模式。此前`CORDIC_P2_001`的DMA Channel超时现象保留为历史测试事实，但不再解释为ET6801 CORDIC DMA Feature故障。当前最终分类为`SKIP`，芯片Case适配状态为`NOT_APPLICABLE`：公共Feature、公共Case及代码保留，ET6801不执行该Case；只有后续芯片明确声明支持CORDIC DMA时，才配置对应Execution Mapping并运行该Case。
