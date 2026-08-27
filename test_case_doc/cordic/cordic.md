# CORDIC Public Test Contract

> 本文件定义 CORDIC 的跨芯片稳定 Feature、Formal Case 设计、独立数学 Oracle、最小充分 Evidence 与未来报告语义。
> 当前已实现并注册24个Formal Case；P2_001已具备真实执行代码，当前芯片缺少DMA Execution Mapping时按内部集成缺口失败关闭，不允许记为SKIP。第二参数错误状态、自然IRQ与恢复合并为一次不可重复刺激，避免同一硬件状态被重复触发；重复的完成状态与完成IRQ Case已合入P1_007/P1_008，不再单独维护。
> 具体芯片的实例、物理地址、IRQ、SDK 类型、Raw 编码差异和已知实现缺口只进入同目录 `<CHIP>_cordic.md`。
> Formal Case 前置隔离统一遵循 `R210`：除纯只读能力查询外，第一次 Feature 配置前由 Case 显式复位参与 IP；DMA Case 先复位 DMA，再复位 CORDIC，最后复位 Resource Pool。本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

### 0.1 稳定逻辑数据模型

| 稳定语义 | 公共含义 | 边界 |
|---|---|---|
| `math_function` | SINCOS / PHASE_MODULUS / ARCTAN / HSINCOS / ATANH / EXP / LN / SQRT / TAN | 函数集合由Chip Capability确认；公共Case不暴露芯片SDK枚举。 |
| `numeric_mode` | FIXED / FLOAT32 | FIXED 的Raw Codec与FLOAT32边界由Capability和Chip Adaptation冻结。 |
| `arg_width` / `result_width` | 16-bit / 32-bit 逻辑宽度 | 支持组合由Capability声明；16-bit双结果/双参数打包必须保留Raw证据。 |
| `input_range` | NORMALIZED / DIRECT_ANGLE | 仅对Capability声明适用的函数生效；同一逻辑角度共享独立数学Oracle。 |
| `scale` | 逻辑Scale选项 | 具体数值范围和函数缩放公式由Capability/Chip Adaptation给出；没有公式不得靠历史magic factor实现。 |
| `precision_cycles` | 迭代周期/精度配置 | 公开选项和逐节点accuracy envelope由Capability给出；不假设所有低精度节点满足同一容差。 |
| `result_count` | ONE_RESULT / TWO_RESULTS | 只适用于声明支持双结果消费的函数；未声明结果不作为判据。 |
| `work_mode` | POLLING / INTERRUPT / ZERO_OVERHEAD / DMA | DMA仅在当前Execution Mapping闭合后可实施；空Mapping不能被解释为硬件不支持。 |
| `accuracy_budget` | 函数×数值格式×精度节点的允许误差预算 | 必须有可追溯来源；没有权威预算时保持Gap，不用统一`1e-4`机械覆盖全部函数/节点。 |

### 0.2 独立数学 Oracle

| Function | Logical Expected | 关键输入约束 |
|---|---|---|
| SINCOS | `cos(angle)` + `sin(angle)` | 角度编码由input_range/Codec处理。 |
| PHASE_MODULUS | `atan2(y, x)` + `hypot(x, y)` | 稳定事务顺序为x→y；具体量化/饱和由Capability定义。 |
| ARCTAN | `atan(x)` | 结果角度Codec由Capability定义。 |
| HSINCOS | `cosh(x)` + `sinh(x)` | 只使用已审核合法域。 |
| ATANH | `atanh(x)` | 只使用数学合法域和已审核硬件可表示域。 |
| EXP | `exp(x)` | 输入/输出Scale公式必须来自当前Capability/Chip Adaptation。 |
| LN | `log(x)` | 仅正值合法域；转换异常另由状态Case验证。 |
| SQRT | `sqrt(x)` | 仅非负合法域。 |
| TAN | `tan(angle)` | 目标Raw编码可能不同于普通定点结果，必须由Chip Codec映射解释。 |

独立 Oracle 只由 PC 标准数学实现计算；DUT roundtrip、历史硬件输出或同一硬件结果的再次解码不得充当 Golden。输入必须先按声明的数据格式量化，再用该逻辑输入计算 Expected。

### 0.3 稳定动作语义

未来公共 Driver / Firmware Service / Wrap 至少需要表达以下稳定动作；名称用于分析导航，不冻结 Wire Command ID，也不表示当前实现已经存在：

```text
CAPABILITIES_GET
CONFIGURE(numeric_mode, arg_width, result_width, input_range, scale, precision_cycles, result_count, work_mode)
ARG_SUBMIT(math_function, raw_value)
RESULT_GET(primary/secondary/raw_packed)
STATUS_SNAPSHOT / STATUS_CLEAR
ARG_COUNT_GET
FLOAT_CONVERSION_STATUS_GET / FLOAT_CONVERSION_STATUS_CLEAR
IRQ_ENABLE / IRQ_DISABLE / IRQ_MASK / IRQ_UNMASK / IRQ_FORCE / IRQ_CLEAR / IRQ_SNAPSHOT
ZERO_OVERHEAD_EXECUTE(math_function, args[], result_count)
TEST_EXECUTE_TIMED(math_function, args[], timeout) -> result + target_cycles
```

CRG复位、DMA Channel配置和外部计时资源由各自Owner在PC Case编排；CORDIC Service/Wrap不得跨IP持有这些职责。
PC Driver构造必须显式接收Capability/Fixture解析出的逻辑实例，不提供固定实例默认值；STATUS、转换状态和IRQ投递的有界等待由CORDIC Driver统一持有，Case只按测试步骤调用。

### 0.4 稳定 Observation Endpoint

| 公共稳定 Endpoint | 来源类型 | 证明用途 |
|---|---|---|
| `CAPABILITY.RUNTIME` | DUT只读能力端点 | 证明目标侧Service能返回当前CORDIC函数/格式/模式/IRQ能力快照。 |
| `RESULT.PRIMARY` | DUT结果端点 | 第一逻辑结果Raw值。 |
| `RESULT.SECONDARY` | DUT结果端点 | 双结果事务第二逻辑结果Raw值。 |
| `RESULT.PACKED16` | DUT结果端点 | 16-bit打包模式的完整Raw word，先保Raw再拆高/低半字。 |
| `STATUS.COMPLETE` | DUT状态端点 | 一次计算完成终态及显式Clear前后变化。 |
| `STATUS.ARG_OVERFLOW` | DUT状态端点 | 参数/请求数量越界状态。 |
| `STATUS.PM_ARG2_ERROR` | DUT状态端点 | PHASE_MODULUS等待第二参数时的来源顺序错误。 |
| `ARG_COUNT.CURRENT` | DUT状态端点 | 当前双参数/请求事务的参数提交阶段。 |
| `FLOAT2FIXED.OVERFLOW` | DUT状态端点 | 浮点内部转换溢出。 |
| `FLOAT2FIXED.UNDERFLOW` | DUT状态端点 | 浮点内部转换下溢。 |
| `IRQ_RAW.<Source>` | DUT IRQ Raw端点 | Mask前逻辑Source pending事实。 |
| `IRQ_STATUS.<Source>` | DUT IRQ有效状态端点 | Mask后的有效Source状态。 |
| `IRQ_DELIVERY.LATCHED_SOURCE` | Firmware/Service端点 | 真实ISR投递锁存；不能冒充IRQ_RAW/STATUS。 |
| `TIMING.CYCLE_COUNT` | 目标侧独立计时Observer | 表征一个正确CORDIC事务的目标周期数；不是CORDIC结果端点。 |
| `DMA.INPUT_CHANNEL.FREE/FIFO_EMPTY/IRQ_STATUS` | DUT DMA输入Channel端点 | 证明CORDIC输入Request真正推进DMA Channel且没有错误事件。 |
| `DMA.OUTPUT_CHANNEL.FREE/FIFO_EMPTY/IRQ_STATUS` | DUT DMA输出Channel端点 | 证明CORDIC结果Request真正推进DMA Channel且没有错误事件。 |
| `DMA.DESTINATION_BUFFER` | DUT DMA目的Buffer端点 | 证明真实DMA数据搬运，而不是只配置DMA模式。 |

Canonical Observation 保持一端点一事实。函数ID、logical input、Raw input、Golden、accuracy budget、event_count、error 等软件派生值属于 Measurement/Oracle，不得包装成硬件 Observation。

## 1. Feature Catalog

| Feature ID | 稳定 Feature | 公共测试语义 | 主要 Case |
|---|---|---|---|
| CORDIC_F_001 | CORDIC Sin/Cos双结果 | 单个角度输入产生cos与sin两个逻辑结果，结果按独立数学Oracle判定。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_002 | CORDIC Phase/Modulus双结果 | 按稳定x→y参数顺序提交二维向量，产生phase与modulus两个逻辑结果。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_003 | CORDIC atan运算 | 单输入反正切结果与独立atan Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_004 | CORDIC sinh/cosh双结果 | 单输入产生cosh与sinh两个逻辑结果并与独立Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_005 | CORDIC atanh运算 | 合法域单输入产生atanh结果并与独立Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_006 | CORDIC exp运算 | 合法域单输入产生exp结果并与独立Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_007 | CORDIC ln运算 | 正值合法域输入产生ln结果并与独立Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_008 | CORDIC sqrt运算 | 非负合法域输入产生sqrt结果并与独立Oracle一致。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_009 | CORDIC tan运算 | 合法角度域输入产生tan结果；目标格式的编码/缩放由Capability与Chip Adaptation解释。 | `CORDIC_P0_002`, `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_010 | CORDIC Fixed模式 | 逻辑输入经已审核定点Codec编码后进入DUT，硬件Raw结果经同一稳定Codec解码后与独立数学Oracle比较。 | `CORDIC_P0_002` |
| CORDIC_F_011 | CORDIC Float32模式 | float32逻辑输入由硬件浮点路径处理，Raw结果按浮点语义解码并与独立double-precision Oracle比较。 | `CORDIC_P0_003`, `CORDIC_P3_001` |
| CORDIC_F_012 | CORDIC 16-bit参数宽度 | Capability声明支持时，16-bit参数输入及双参数打包方式具有可验证的稳定编码语义。 | `CORDIC_P1_002` |
| CORDIC_F_013 | CORDIC 32-bit参数宽度 | 32-bit参数输入保持完整符号/数值语义并参与正确计算。 | `CORDIC_P0_002`, `CORDIC_P1_002` |
| CORDIC_F_014 | CORDIC 16-bit结果打包 | Capability声明支持时，双结果与单结果函数的16-bit Raw打包可被明确拆解并恢复逻辑结果。 | `CORDIC_P1_002` |
| CORDIC_F_015 | CORDIC 32-bit结果 | 32-bit结果路径保持完整Raw输出并可由稳定Codec恢复逻辑结果。 | `CORDIC_P0_002`, `CORDIC_P1_002` |
| CORDIC_F_016 | CORDIC Normalized Angle模式 | 正余弦支持归一化角度编码；同一逻辑角度的结果必须与独立sin/cos Oracle一致。 | `CORDIC_P1_001` |
| CORDIC_F_017 | CORDIC Direct Angle模式 | Capability声明支持时，正余弦可使用直接扩展角度编码，并与归一化路径得到同一逻辑结果。 | `CORDIC_P1_001` |
| CORDIC_F_018 | CORDIC Scale配置 | Scale选项只在Capability声明适用的函数上改变输入/输出解释；不适用函数不得被错误施加Scale语义。 | `CORDIC_P1_003` |
| CORDIC_F_019 | CORDIC Iteration/Precision配置 | Capability声明的迭代周期选项可配置；每个节点记录误差，最高精度节点必须满足已冻结精度预算。 | `CORDIC_P1_004` |
| CORDIC_F_020 | CORDIC Sin/Cos结果数量 | 正余弦可按Capability选择单结果或双结果消费语义，已声明结果必须正确。 | `CORDIC_P1_005` |
| CORDIC_F_021 | CORDIC Phase/Modulus结果数量 | 相位/模长可按Capability选择单结果或双结果消费语义，已声明结果必须正确。 | `CORDIC_P1_005` |
| CORDIC_F_022 | CORDIC sinh/cosh结果数量 | 双曲正余弦可按Capability选择单结果或双结果消费语义，已声明结果必须正确。 | `CORDIC_P1_005` |
| CORDIC_F_023 | CORDIC Phase/Modulus参数顺序 | 二维向量事务要求x后接y；在x等待y期间插入其他函数参数应形成目标错误语义而不能静默错配。 | `CORDIC_P1_006`, `CORDIC_P1_016` |
| CORDIC_F_024 | CORDIC Polling工作模式 | Polling模式下硬件产生可轮询的完成状态，软件可有界等待后读取与Oracle匹配的结果。 | `CORDIC_P1_007` |
| CORDIC_F_025 | CORDIC IRQ工作模式 | IRQ模式下计算完成可通过目标逻辑中断源形成真实投递，同时结果仍满足数学Oracle。 | `CORDIC_P1_008` |
| CORDIC_F_026 | CORDIC Zero-Overhead工作模式 | Zero-Overhead模式在受控原子窗口中提交输入并读取对应结果，不依赖固定sleep或状态轮询。 | `CORDIC_P1_009`, `CORDIC_P3_003` |
| CORDIC_F_027 | CORDIC DMA工作模式 | 硬件声明DMA工作模式时，只有当前Execution Mapping闭合且真实DMA搬运完成才算覆盖。 | `CORDIC_P2_001` |
| CORDIC_F_028 | CORDIC 计算完成状态 | 一次有效计算产生可观测完成状态，并可通过显式清除动作证明清除语义。 | `CORDIC_P1_007` |
| CORDIC_F_029 | CORDIC 参数溢出状态 | 超过目标事务/队列可接受参数数量时产生可观测参数溢出状态，并可恢复。 | `CORDIC_P1_011` |
| CORDIC_F_030 | CORDIC 第二参数错误状态 | 相位模长等待第二参数时插入错误来源参数可产生专用错误状态；W1C清除报告位后，由外层Owner复位并重新配置可恢复正常计算。 | `CORDIC_P1_016` |
| CORDIC_F_031 | CORDIC 参数计数状态 | 双参数事务可观测当前参数提交阶段；完成结果消费或错误清除后返回目标定义的空闲计数状态。 | `CORDIC_P1_006` |
| CORDIC_F_032 | CORDIC 浮点转换溢出状态 | 浮点输入超出内部可表示上界时，Capability声明适用的函数可形成独立溢出状态并支持清除。 | `CORDIC_P1_013` |
| CORDIC_F_033 | CORDIC 浮点转换下溢状态 | 浮点输入落入内部下溢条件时，Capability声明适用的函数可形成独立下溢状态并支持清除。 | `CORDIC_P1_013` |
| CORDIC_F_034 | CORDIC 计算完成中断源 | 计算完成可产生独立逻辑IRQ Source，Raw/Status硬件状态与真实软件投递证据分层记录。 | `CORDIC_P1_008` |
| CORDIC_F_035 | CORDIC 参数溢出中断源 | 参数溢出可产生独立逻辑IRQ Source，并由自然刺激证明来源因果。 | `CORDIC_P1_015` |
| CORDIC_F_036 | CORDIC 第二参数错误中断源 | 相位模长第二参数错误可产生独立逻辑IRQ Source，并由错误顺序刺激证明来源因果。 | `CORDIC_P1_016` |
| CORDIC_F_037 | CORDIC IRQ使能/禁用 | Capability声明的IRQ Source可独立Enable/Disable，禁用后不得产生新的有效投递。 | `CORDIC_P1_015`, `CORDIC_P1_016`, `CORDIC_P1_017` |
| CORDIC_F_038 | CORDIC IRQ屏蔽/解除屏蔽 | Mask应抑制有效状态/投递但保留Raw来源事实，Unmask后恢复规定语义。 | `CORDIC_P1_018` |
| CORDIC_F_039 | CORDIC IRQ软件强制 | Force指定逻辑IRQ Source后形成对应Raw/Status/Delivery，并支持清除恢复。 | `CORDIC_P1_017` |
| CORDIC_F_040 | CORDIC IRQ清除 | Clear目标IRQ Source后该Source消失且其他Source不被误清。 | `CORDIC_P1_019` |
| CORDIC_F_041 | CORDIC IRQ原始/有效状态 | Raw表示Mask前来源事实，Status表示Mask后的有效状态；两者不得混为同一Observation。 | `CORDIC_P1_018`, `CORDIC_P1_019` |
| CORDIC_F_042 | CORDIC IRQ真实投递 | 有效IRQ必须由ISR/Service锁存与event_count等软件事实证明真实投递，不能只看Raw/Status硬件状态。 | `CORDIC_P1_008`, `CORDIC_P1_015`, `CORDIC_P1_016`, `CORDIC_P1_017` |
| CORDIC_F_043 | CORDIC 多函数顺序执行 | 不同函数按受控顺序连续提交时，每次消费的Raw结果必须与对应请求/Oracle一致，不得读到前一请求残留。 | `CORDIC_P1_020` |
| CORDIC_F_044 | CORDIC Zero-Overhead原子窗口 | Zero-Overhead写入与结果读取属于同一原子事务；受控IRQ干扰不得造成跨请求结果错配。 | `CORDIC_P3_003` |
| CORDIC_F_045 | CORDIC 单次运算周期 | 在结果正确前提下，用目标侧独立周期计数器表征不同函数/数据形态的单次执行周期；无规格阈值时只报告测量值。 | `CORDIC_P3_002` |
| CORDIC_F_046 | CORDIC 复位恢复 | 由外层Owner执行模块复位后，CORDIC可重新配置并对已知向量再次得到正确结果，且不继承前一会话状态。 | `CORDIC_P0_004` |

## 2. Case Catalog

| Case ID | P | Case 名称 | 核心证明 | 状态 |
|---|---:|---|---|---|
| CORDIC_P0_002 | P0 | CORDIC定点核心数学函数矩阵测试 | CORDIC九类数学函数在32-bit定点路径下的代表合法域结果正确性 | SPEC |
| CORDIC_P0_003 | P0 | CORDIC浮点核心数学函数矩阵测试 | CORDIC九类数学函数在float32路径下的精确节点结果正确性 | SPEC |
| CORDIC_P0_004 | P0 | CORDIC复位后重新配置与运算恢复测试 | CORDIC在外层Owner复位后重新配置并恢复正确数学运算且不继承旧会话状态 | SPEC |
| CORDIC_P1_001 | P1 | CORDIC正余弦输入范围模式等价性测试 | CORDIC同一逻辑角度在归一化与直接扩展角度路径下的正余弦结果等价性 | SPEC |
| CORDIC_P1_002 | P1 | CORDIC参数/结果位宽与16-bit打包测试 | CORDIC 16/32-bit参数与结果组合下的Raw打包、符号和数学结果正确性 | SPEC |
| CORDIC_P1_003 | P1 | CORDIC Scale缩放语义测试 | CORDIC支持函数在各Scale选项下的输入/输出缩放关系与不适用函数隔离 | SPEC |
| CORDIC_P1_004 | P1 | CORDIC迭代周期与精度表征测试 | CORDIC各迭代周期配置下的误差分布、完成性与高精度预算满足性 | SPEC |
| CORDIC_P1_005 | P1 | CORDIC双结果数量选择测试 | CORDIC SINCOS/PHASE_MODULUS/HSINCOS单结果与双结果消费配置下的已声明结果正确性 | SPEC |
| CORDIC_P1_006 | P1 | CORDIC相位模长双参数顺序与当前计数测试 | CORDIC PHASE_MODULUS x→y两参数事务、当前参数计数与结果消费后的状态恢复 | SPEC |
| CORDIC_P1_007 | P1 | CORDIC轮询完成状态机测试 | CORDIC轮询模式下有界等待完成、读取正确结果并显式清除完成状态 | SPEC |
| CORDIC_P1_008 | P1 | CORDIC中断工作模式计算与结果测试 | CORDIC中断工作模式下计算完成真实投递、硬件状态与数学结果闭环 | SPEC |
| CORDIC_P1_009 | P1 | CORDIC零开销写读功能测试 | CORDIC零开销模式在同一原子事务中提交输入并取得对应正确结果 | SPEC |
| CORDIC_P1_011 | P1 | CORDIC参数数量溢出状态与恢复测试 | CORDIC超出已审核参数/请求容量时产生ARG_OVERFLOW并在清除后恢复正常运算 | SPEC |
| CORDIC_P1_013 | P1 | CORDIC浮点转定点溢出/下溢状态测试 | CORDIC float32输入触发内部转换Overflow/Underflow的独立状态、清除与边界恢复 | SPEC |
| CORDIC_P1_015 | P1 | CORDIC参数溢出IRQ自然投递测试 | CORDIC参数容量越界自然产生ARG_OVERFLOW IRQ并在清除后恢复 | SPEC |
| CORDIC_P1_016 | P1 | CORDIC第二参数错误状态、自然IRQ与恢复测试 | CORDIC PM等待y期间插入其他函数参数，单次刺激同时证明PM_ARG2_ERROR状态、自然IRQ投递与恢复 | SPEC |
| CORDIC_P1_017 | P1 | CORDIC IRQ使能/禁用与软件Force测试 | CORDIC三类逻辑IRQ Source的Enable/Disable、Force投递和清除因果 | SPEC |
| CORDIC_P1_018 | P1 | CORDIC IRQ Mask/Unmask与Raw/Status分层测试 | CORDIC目标IRQ Source在Mask时保留Raw且抑制Status/Delivery，Unmask后恢复有效语义 | SPEC |
| CORDIC_P1_019 | P1 | CORDIC IRQ单Source精确清除隔离测试 | CORDIC多个Raw pending共存时Clear目标Source只清除目标位并保留其他Source | SPEC |
| CORDIC_P1_020 | P1 | CORDIC多函数连续请求与结果对应测试 | CORDIC不同函数连续提交与消费时Raw结果按请求顺序正确对应且无残留错配 | SPEC |
| CORDIC_P2_001 | P2 | CORDIC DMA工作模式真实搬运等价性测试 | CORDIC DMA工作模式通过已验证Request Mapping完成真实搬运并得到与CPU路径等价的数学结果；当前映射缺失时按内部集成缺口失败关闭 | SPEC |
| CORDIC_P3_001 | P3 | CORDIC Float32代表节点重复稳定性测试 | CORDIC九类数学函数在固定代表合法节点上的重复正确性、完成状态与清理后状态稳定性 | SPEC |
| CORDIC_P3_002 | P3 | CORDIC目标侧单次执行周期表征测试 | CORDIC结果正确前提下使用目标侧独立周期计数器表征不同函数/数据形态的执行周期 | SPEC |
| CORDIC_P3_003 | P3 | CORDIC零开销原子窗口抗IRQ干扰测试 | CORDIC零开销PHASE_MODULUS写读窗口在受控IRQ干扰下保持请求/结果原子对应 | SPEC |

## 3. Machine-readable Case Contract

> 本节包含24个已注册/实现的`ET_CASE_SPEC`。P2_001在当前芯片缺少DMA Execution Mapping时由运行期Gate失败关闭，不得伪造PASS或SKIP，也不再保留PLAN。Capability一致性属于平台发现/契约门禁，不作为CORDIC硬件Feature或Formal Case计入功能覆盖。


### CORDIC_P0_002 - CORDIC定点核心数学函数矩阵测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P0_002
case_name: CORDIC定点核心数学函数矩阵测试
report_feature: |-
  1. CORDIC Sin/Cos双结果
  2. CORDIC Phase/Modulus双结果
  3. CORDIC atan运算
  4. CORDIC sinh/cosh双结果
  5. CORDIC atanh运算
  6. CORDIC exp运算
  7. CORDIC ln运算
  8. CORDIC sqrt运算
  9. CORDIC tan运算
  10. CORDIC Fixed模式
  11. CORDIC 32-bit参数宽度
  12. CORDIC 32-bit结果
p_level: P0
feature_refs:
- CORDIC_F_001
- CORDIC_F_002
- CORDIC_F_003
- CORDIC_F_004
- CORDIC_F_005
- CORDIC_F_006
- CORDIC_F_007
- CORDIC_F_008
- CORDIC_F_009
- CORDIC_F_010
- CORDIC_F_013
- CORDIC_F_015
method:
  inputs:
  - "函数向量矩阵：为SINCOS、PHASE_MODULUS、ARCTAN、HSINCOS、ATANH、EXP、LN、SQRT、TAN分别选择可复现的代表合法域向量，双参数函数提供有序x/y。"
  - "Codec与Golden：输入按目标Capability冻结的32-bit定点Codec编码；Expected由PC double-precision标准数学函数独立计算。"
  - "精度配置：使用Runtime声明的最高精度配置；P0代表节点采用历史Unit/Functional/FPGA共同使用并经本平台审核冻结的1e-4绝对误差预算。"
  steps:
  - "参数节点选择：选择当前函数和确定性逻辑输入，记录function_id与logical_input。"
  - "独立Golden生成：使用PC数学库计算逻辑Expected，并记录本函数适用的accuracy budget来源。"
  - "定点输入编码：按当前Capability/Chip Adaptation把逻辑输入编码为Raw参数；PM按x后y的稳定顺序准备。"
  - "CORDIC功能配置：配置FIXED、32-bit参数/结果、高精度节点和当前函数需要的Scale/Range选项。"
  - "运算提交与等待：写入一个完整逻辑事务，并以有界完成条件等待结果可用，不用固定sleep。"
  - "硬件结果读取：读取RESULT.PRIMARY；双结果函数同时读取RESULT.SECONDARY，并读取STATUS.COMPLETE终态。"
  - "结果解码比较：按已审核Codec把Raw结果恢复为逻辑值，分别与独立Golden按对应accuracy budget比较。"
  - "矩阵汇总：汇总九类函数全部参数节点，记录Raw、Decoded、Expected、Error和完成状态。"
  observations:
  - "主结果端点：读取RESULT.PRIMARY Raw值，期望解码后与当前函数第一逻辑Golden在已审核accuracy budget内一致；证明主结果路径正确。"
  - "第二结果端点：双结果函数读取RESULT.SECONDARY Raw值，期望解码后与第二逻辑Golden一致；单结果函数不虚构第二结果判据。"
  - "计算完成状态：读取STATUS.COMPLETE，期望为有效完成终态；证明本次Raw结果对应已完成计算。"
  pass_criteria:
  - "函数覆盖完整：九类函数及其计划代表向量全部执行并形成独立结果记录。"
  - "数学结果正确：每个Decoded Actual与对应double-precision Golden满足当前函数/格式/精度的已审核accuracy budget。"
  - "Raw可追溯：每个结果均保留Raw值、Codec身份和Decoded值，禁止只保存最终浮点比较结论。"
  - "完成状态有效：每个节点读取结果时STATUS.COMPLETE均处于当前事务规定的完成终态。"
timeout: "10 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_primary_raw", label: "独立定点主结果Golden Raw", source: "oracle", role: "expected", format: "hex32"}
- {key: "actual_primary_raw", label: "RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "actual_secondary_raw", label: "RESULT.SECONDARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P0_003 - CORDIC浮点核心数学函数矩阵测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P0_003
case_name: CORDIC浮点核心数学函数矩阵测试
report_feature: |-
  1. CORDIC Sin/Cos双结果
  2. CORDIC Phase/Modulus双结果
  3. CORDIC atan运算
  4. CORDIC sinh/cosh双结果
  5. CORDIC atanh运算
  6. CORDIC exp运算
  7. CORDIC ln运算
  8. CORDIC sqrt运算
  9. CORDIC tan运算
  10. CORDIC Float32模式
p_level: P0
feature_refs:
- CORDIC_F_001
- CORDIC_F_002
- CORDIC_F_003
- CORDIC_F_004
- CORDIC_F_005
- CORDIC_F_006
- CORDIC_F_007
- CORDIC_F_008
- CORDIC_F_009
- CORDIC_F_011
method:
  inputs:
  - "函数向量矩阵：九类数学函数分别使用确定性合法域节点；PM按x后y提交。"
  - "Golden来源：Expected由独立数学定义产生，并转换为IEEE-754 Float32 Raw bits。"
  - "误差预算：使用历史Unit/Functional/FPGA共同采用并经本平台审核冻结的1e-4绝对误差预算。"
  - "能力门禁：Runtime未声明的函数节点明确Skip，不能由其他函数的PASS代替。"
  steps:
  - "Golden构造：按当前函数节点生成独立Expected，并编码为IEEE-754 Float32 Raw bits。"
  - "独立配置：每个函数节点重新配置FLOAT32 Polling路径并清除历史状态。"
  - "参数提交：单参数函数提交一个Raw参数；Phase/Modulus严格按x后y提交两个Raw参数。"
  - "完成等待：在统一轮询上限内等待自然COMPLETE，不使用固定sleep。"
  - "结果读取：读取RESULT.PRIMARY；SINCOS、PHASE_MODULUS、HSINCOS同时读取RESULT.SECONDARY。"
  - "结果比较：将硬件Raw解码为Float32后与独立Golden按1e-4绝对误差预算逐项比较，并检查没有错误状态。"
  - "状态清除：对COMPLETE执行W1C并复读，保证下一参数节点没有完成状态残留。"
  observations:
  - "浮点主结果：读取RESULT.PRIMARY Raw bits并解码，期望与独立Float32 Golden的绝对误差不超过1e-4。"
  - "浮点第二结果：双结果函数读取RESULT.SECONDARY Raw bits并解码，期望与第二个Golden的绝对误差不超过1e-4。"
  - "完成状态：每个节点自然产生COMPLETE，清除后该位恢复为0且没有其他错误状态。"
  pass_criteria:
  - "函数覆盖完整：当前Runtime声明的九类Float32函数节点分别执行；缺失函数明确Skip。"
  - "数学结果正确：全部主结果与已声明第二结果均满足1e-4绝对误差预算。"
  - "状态边界正确：每个节点只产生COMPLETE，W1C后COMPLETE清零。"
timeout: "10 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_primary_raw", label: "独立Float32主结果Golden", source: "oracle", role: "expected", format: "hex32"}
- {key: "actual_primary_raw", label: "RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "actual_secondary_raw", label: "RESULT.SECONDARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P0_004 - CORDIC复位后重新配置与运算恢复测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P0_004
case_name: CORDIC复位后重新配置与运算恢复测试
report_feature: |-
  1. CORDIC 复位恢复
p_level: P0
feature_refs: [CORDIC_F_046]
method:
  inputs:
  - "恢复向量：使用结果易判别的Float32 SQRT(1.0)固定输入，分别用于复位前后计算。"
  - "复位Owner：复位动作由PC Case通过外层时钟/复位Owner执行，CORDIC Service不得跨IP直接调用复位实现。"
  - "Golden来源：两轮Expected均由独立PC数学Oracle计算。"
  steps:
  - "复位前配置：建立CORDIC已知配置，清理可清状态并执行第一组确定性输入。"
  - "第一轮结果读取：等待完成后读取RESULT.PRIMARY/必要第二结果并与第一轮Golden比较。"
  - "外层复位执行：由PC Case调用已审核复位Owner执行CORDIC复位，记录复位动作结果和边界。"
  - "复位后状态确认：重新配置CORDIC并清除状态，不把旧完成/错误状态当成本轮Evidence。"
  - "复位后运算：提交同一确定性SQRT(1.0)输入，等待完成并读取硬件Raw结果。"
  - "恢复判定：比较复位前后Actual与独立Golden，同时确认清除后状态归零。"
  observations:
  - "复位前硬件结果：读取RESULT.PRIMARY，期望与第一轮Golden一致；证明复位前基线可用。"
  - "复位后硬件结果：重新配置后读取RESULT.PRIMARY，期望与第二轮Golden一致且对应复位后重新提交的同一确定性输入。"
  - "复位后状态终态：读取STATUS.COMPLETE及错误状态快照，Expected只允许本轮运算产生的规定终态。"
  pass_criteria:
  - "两轮数据正确：复位前后Actual分别满足各自独立Golden和accuracy budget。"
  - "重新配置有效：复位后完整重新配置即可恢复运算，不依赖复位前的软件/硬件会话。"
  - "状态隔离：第二轮结果与状态均对应第二轮输入，不复用第一轮残留。"
  - "分层正确：复位由外层Owner编排，CORDIC公共Service不跨IP持有复位职责。"
timeout: "8 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_recovery_raw", label: "复位前后独立Golden", source: "oracle", role: "expected", format: "hex32"}
- {key: "pre_reset_result", label: "复位前RESULT.PRIMARY实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "post_reset_result", label: "复位后RESULT.PRIMARY实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "post_reset_status", label: "复位后STATUS.COMPLETE实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.complete_status"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_001 - CORDIC正余弦输入范围模式等价性测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_001
case_name: CORDIC正余弦输入范围模式等价性测试
report_feature: |-
  1. CORDIC Normalized Angle模式
  2. CORDIC Direct Angle模式
p_level: P1
feature_refs:
- CORDIC_F_016
- CORDIC_F_017
method:
  inputs:
  - "角度矩阵：选择0、典型正负角、象限边界附近及扩展范围内代表角度；每个逻辑角度分别构造两种合法编码。"
  - "Golden来源：Expected直接由PC sin/cos计算，两种输入编码共享同一逻辑Golden。"
  steps:
  - "角度节点选择：选择一个逻辑角度并生成NORMALIZED与DIRECT_ANGLE两种Capability允许的Raw输入。"
  - "归一化路径配置：配置FIXED、归一化范围和稳定高精度节点。"
  - "归一化路径运算：提交Raw输入，等待完成并读取两路结果。"
  - "直接角度路径配置：重建同等数值/精度配置，仅切换到直接扩展角度范围。"
  - "直接角度路径运算：提交对应Raw输入，等待完成并读取两路结果。"
  - "双路径解码：分别按各自Codec解码cos/sin Actual并记录Raw与逻辑值。"
  - "等价性比较：两条路径分别与同一sin/cos Golden比较，并汇总全部角度节点。"
  observations:
  - "归一化路径结果：读取RESULT.PRIMARY/SECONDARY，期望解码后分别等于cos/sin Golden。"
  - "直接角度路径结果：读取RESULT.PRIMARY/SECONDARY，期望解码后分别等于同一cos/sin Golden。"
  pass_criteria:
  - "范围覆盖完整：两种输入范围模式和全部计划角度节点均执行。"
  - "数学正确性：两路径各自Actual满足同一Golden与对应accuracy budget。"
  - "路径等价性：同一逻辑角度的两种Decoded结果差异不得超过两路径预算合成上界。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "logical_angle_radians", label: "独立逻辑角度", source: "oracle", role: "expected", format: "float"}
- {key: "range_primary_raw", label: "当前范围路径RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "range_secondary_raw", label: "当前范围路径RESULT.SECONDARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_002 - CORDIC参数/结果位宽与16-bit打包测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_002
case_name: CORDIC参数/结果位宽与16-bit打包测试
report_feature: |-
  1. CORDIC 16-bit参数宽度
  2. CORDIC 32-bit参数宽度
  3. CORDIC 16-bit结果打包
  4. CORDIC 32-bit结果
p_level: P1
feature_refs:
- CORDIC_F_012
- CORDIC_F_013
- CORDIC_F_014
- CORDIC_F_015
method:
  inputs:
  - "位宽矩阵：覆盖当前平台计划的16/32-bit参数×16/32-bit结果四种组合，使用非零SINCOS双结果节点区分参数存储位置和结果打包。"
  - "判别向量：使用正负不对称且高/低半字可区分的输入，避免打包错误仍产生偶然相等。"
  - "Golden与Codec：逻辑Expected来自独立数学Oracle；16-bit/32-bit Raw编码与解码规则来自当前Capability/Chip Adaptation。"
  steps:
  - "矩阵节点选择：选择函数、参数宽度、结果宽度与判别输入。"
  - "输入编码：按当前参数宽度将逻辑输入编码为Raw；支持packed双参数时同时记录高/低半字身份。"
  - "位宽配置：配置目标arg_width/result_width及函数所需稳定模式。"
  - "运算提交：提交完整输入事务并有界等待结果完成。"
  - "Raw结果读取：读取RESULT.PRIMARY；32-bit双结果路径读取RESULT.SECONDARY，16-bit打包路径保留完整RESULT.PACKED16 Raw。"
  - "结果拆解：按当前结果宽度进行有符号拆包/解码，禁止先丢弃Raw再比较。"
  - "数学比较：将每个Decoded Actual与独立Golden比较并汇总全部位宽组合。"
  observations:
  - "打包Raw结果：16-bit双结果模式读取RESULT.PACKED16，期望高/低半字身份与Chip Adaptation定义一致。"
  - "32-bit主结果：读取RESULT.PRIMARY，期望解码后与第一逻辑Golden一致。"
  - "32-bit第二结果：双结果32-bit模式读取RESULT.SECONDARY，期望解码后与第二逻辑Golden一致。"
  pass_criteria:
  - "组合覆盖完整：Capability声明的计划位宽组合全部执行。"
  - "打包位置正确：16-bit双结果高/低半字与稳定映射完全一致。"
  - "非零Codec正确：同一非零逻辑角度在四种位宽组合下均得到一致数学结果，不被零输入掩盖存储位置错误。"
  - "数学结果正确：所有Decoded Actual满足对应格式accuracy budget。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "logical_angle_radians", label: "位宽矩阵逻辑角度Golden", source: "oracle", role: "expected", format: "float"}
- {key: "width_primary_raw", label: "RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "width_packed_values", label: "RESULT.PRIMARY高低半字", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.result_packing"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_003 - CORDIC Scale缩放语义测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_003
case_name: CORDIC Scale缩放语义测试
report_feature: |-
  1. CORDIC Scale配置
p_level: P1
feature_refs:
- CORDIC_F_018
method:
  inputs:
  - "Scale矩阵：遍历Chip Execution Mapping声明的平台计划Scale选项，并选择一个已有直接证据的受影响函数和一个SVD明确不受影响的函数。"
  - "公式来源：每个受影响函数的逻辑输入/输出Scale关系必须来自已审核Capability/Chip Adaptation，不从历史Case中的magic factor推导。"
  steps:
  - "Scale节点选择：选择函数、Scale值与能区分缩放效果的稳定逻辑输入。"
  - "Expected构造：按已审核Scale公式生成该节点逻辑Golden和Raw编码Expected。"
  - "CORDIC配置：配置固定数值路径、当前Scale与稳定高精度节点。"
  - "运算执行：提交输入事务，有界等待并读取Raw结果和完成状态。"
  - "结果解码：按当前Scale公式与Codec把RESULT.PRIMARY/必要第二结果恢复为逻辑Actual。"
  - "适用函数比较：受Scale影响的函数逐节点与独立数学Golden比较。"
  - "不适用函数隔离：对声明Scale无效的函数比较多个Scale下结果，确认Scale不会改变其逻辑输出，并汇总矩阵。"
  observations:
  - "缩放后硬件结果：读取RESULT.PRIMARY，期望经当前Scale/Codec解码后与独立数学Golden一致。"
  - "Scale隔离结果：对Capability声明不受Scale影响的函数读取Actual，期望不同Scale节点的Decoded结果在量化预算内等价。"
  pass_criteria:
  - "Scale覆盖完整：Capability公开的计划Scale选项均被执行。"
  - "缩放公式正确：受影响函数各节点Actual满足已审核Scale公式和accuracy budget。"
  - "无效域隔离：明确不受Scale影响的函数不得因Scale切换产生超出量化预算的逻辑变化。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_scale_values", label: "Scale独立Expected", source: "oracle", role: "expected", format: "text"}
- {key: "scale_unaffected_primary_raw", label: "Scale隔离路径RESULT.PRIMARY", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.math_result"}
- {key: "scale_affected_primary_raw", label: "Scale受影响路径RESULT.PRIMARY", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.math_result"}
- {key: "scale_status_before_clear", label: "各Scale节点STATUS清除前值", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.complete_status"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_004 - CORDIC迭代周期与精度表征测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_004
case_name: CORDIC迭代周期与精度表征测试
report_feature: |-
  1. CORDIC Iteration/Precision配置
p_level: P1
feature_refs:
- CORDIC_F_019
method:
  inputs:
  - "精度节点：遍历Capability公开的precision_cycles选项，不假定历史Driver枚举就是硬件全部范围。"
  - "挑战向量：选择对低迭代精度敏感且定义域安全的固定向量，并由PC独立数学Oracle给出Expected。"
  - "判定预算：每节点允许误差包络和最高精度预算必须由Capability/审核结论冻结；不要求所有低迭代节点满足同一阈值。"
  steps:
  - "精度节点选择：选择precision_cycles与固定挑战向量，记录配置身份。"
  - "独立Golden生成：用PC double precision生成Expected，保持各精度节点输入完全相同。"
  - "CORDIC配置：配置当前precision_cycles、固定数据格式和函数模式。"
  - "运算执行：提交事务并有界等待完成，读取Raw结果。"
  - "误差计算：解码Actual并计算绝对/相对误差，记录但不把软件Error冒充硬件Observation。"
  - "节点判定：若Capability存在该节点误差包络则逐节点核对；否则只保留表征值并保持Gap。"
  - "精度汇总：比较全部节点，要求最高精度配置满足正式accuracy budget并记录趋势，不强制数学上未承诺的严格单调性。"
  observations:
  - "精度节点结果：读取RESULT.PRIMARY/必要第二结果，期望每个节点都产生可解码有限结果。"
  - "完成状态：读取STATUS.COMPLETE，期望所有precision节点均完成，不因低精度配置进入异常停滞。"
  pass_criteria:
  - "节点覆盖完整：Capability公开的全部计划precision节点执行并记录误差。"
  - "最高精度正确：最高精度节点必须满足已冻结函数/格式accuracy budget。"
  - "已发布包络满足：若Capability声明逐节点误差包络，则所有对应节点均不得越界。"
  - "完成性正确：所有合法precision节点均在deadline内形成完成结果。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_precision_budget", label: "最高精度节点绝对误差预算", source: "oracle", role: "expected", format: "float"}
- {key: "precision_primary_raw", label: "各precision节点RESULT.PRIMARY", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.math_result"}
- {key: "precision_secondary_raw", label: "各precision节点RESULT.SECONDARY", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.math_result"}
- {key: "precision_status_before_clear", label: "各precision节点STATUS清除前值", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.complete_status"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_005 - CORDIC双结果数量选择测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_005
case_name: CORDIC双结果数量选择测试
report_feature: |-
  1. CORDIC Sin/Cos结果数量
  2. CORDIC Phase/Modulus结果数量
  3. CORDIC sinh/cosh结果数量
p_level: P1
feature_refs:
- CORDIC_F_020
- CORDIC_F_021
- CORDIC_F_022
method:
  inputs:
  - "结果数量矩阵：对三类双结果函数分别执行ONE_RESULT与TWO_RESULTS选项，输入使用可区分两个结果的确定性向量。"
  - "Golden来源：每类函数两个逻辑Expected均由PC独立数学Oracle生成。"
  steps:
  - "函数节点选择：选择SINCOS、PHASE_MODULUS或HSINCOS及结果数量选项。"
  - "输入与Golden准备：构造确定性输入并生成第一/第二逻辑Golden。"
  - "结果数量配置：配置当前函数的result_count和稳定数据格式/精度。"
  - "运算执行：提交完整事务并有界等待结果完成。"
  - "结果读取：按当前result_count只读取合同声明应消费的结果端点，保留Raw值。"
  - "数据比较：ONE_RESULT只判断声明结果；TWO_RESULTS分别比较两个Decoded Actual与Golden。"
  - "矩阵汇总：确认三类函数两种结果数量选项均可重复进入，不对未声明结果端点编造有效性判据。"
  observations:
  - "主结果端点：读取RESULT.PRIMARY，期望与当前函数第一已声明Golden一致。"
  - "第二结果端点：仅TWO_RESULTS节点读取RESULT.SECONDARY，期望与第二Golden一致；ONE_RESULT不把未声明端点当决定性证据。"
  pass_criteria:
  - "选项覆盖完整：三类双结果函数的计划result_count选项全部执行。"
  - "声明结果正确：所有实际消费的结果端点均满足对应独立Golden和accuracy budget。"
  - "单结果边界准确：ONE_RESULT节点不因报告方便而要求硬件提供未声明第二结果。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "function", label: "双结果数学函数", source: oracle, role: expected, format: text}
- {key: "result_count", label: "结果数量配置", source: oracle, role: expected, format: text}
- {key: "primary_raw", label: "RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "secondary_raw", label: "RESULT.SECONDARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_006 - CORDIC相位模长双参数顺序与当前计数测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_006
case_name: CORDIC相位模长双参数顺序与当前计数测试
report_feature: |-
  1. CORDIC Phase/Modulus参数顺序
  2. CORDIC 参数计数状态
p_level: P1
feature_refs:
- CORDIC_F_023
- CORDIC_F_031
method:
  inputs:
  - "向量与顺序：使用Float32精确节点x=1、y=0，固定按x后y提交。"
  - "计数生命周期：事务开始、等待y、第二参数完成、结果消费后分别期望0、1、0、0。"
  steps:
  - "初始状态确认：清除残留状态并读取ARG_COUNT.CURRENT，确认进入目标事务的初始状态。"
  - "第一参数提交：提交PHASE_MODULUS的x参数，立即读取ARG_COUNT.CURRENT并记录等待第二参数阶段。"
  - "第二参数提交：向同一PHASE_MODULUS事务提交y参数并有界等待计算完成。"
  - "完成阶段读取：读取ARG_COUNT.CURRENT、STATUS.COMPLETE以及RESULT.PRIMARY/SECONDARY Raw值。"
  - "数学结果比较：将phase=0、modulus=1的实际Float32 Raw与独立Golden逐位比较。"
  - "结果消费与恢复：清除COMPLETE后执行SQRT(0.25)，确认参数计数保持0且结果为0.5。"
  observations:
  - "参数计数序列：读取ARG_COUNT.CURRENT，期望完整序列为0→1→0→0→0。"
  - "PM硬件结果：读取RESULT.PRIMARY/SECONDARY，期望Raw分别为Float32 0和1。"
  - "恢复硬件结果：后续SQRT事务RESULT.PRIMARY期望为Float32 0.5。"
  pass_criteria:
  - "顺序事务正确：每组向量都严格按x→y提交并完成，不出现第二参数错误状态。"
  - "参数计数正确：各阶段ARG_COUNT.CURRENT严格满足0→1→0生命周期。"
  - "数学结果正确：phase、modulus和恢复SQRT均与精确Float32 Golden逐位一致。"
  - "恢复正确：结果消费后可无残留地开始单参数事务。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "argument_count_sequence", label: "ARG_COUNT.CURRENT实际序列", source: "dut", role: "actual", format: "text", semantic_ref: "cordic.feature.argument_count"}
- {key: "pm_poll_count", label: "PM完成轮询次数", source: "dut", role: "actual", format: "decimal"}
- {key: "recovery_poll_count", label: "恢复事务轮询次数", source: "dut", role: "actual", format: "decimal"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_007 - CORDIC轮询完成状态机测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_007
case_name: CORDIC轮询完成状态机测试
report_feature: |-
  1. CORDIC Polling工作模式
  2. CORDIC 计算完成状态
p_level: P1
feature_refs:
- CORDIC_F_024
- CORDIC_F_028
method:
  inputs:
  - "轮询向量：选择一个单结果和一个双结果函数的确定性合法输入。"
  - "轮询边界：使用统一deadline与轮询间隔策略，不允许无限while或固定sleep替代状态条件。"
  steps:
  - "状态预清理：显式清除上一事务COMPLETE并确认STATUS.COMPLETE=0。"
  - "轮询模式配置：配置POLLING工作模式、稳定数据格式和精度。"
  - "运算提交：提交当前确定性输入事务并记录Expected。"
  - "有界状态轮询：重复读取STATUS.COMPLETE直到为1或deadline到期，记录poll_count与完成时间。"
  - "结果读取：完成后读取RESULT.PRIMARY/必要第二结果并保存Raw。"
  - "结果比较：解码Actual与独立Golden比较，同时确认没有目标错误状态。"
  - "状态清除恢复：显式Clear COMPLETE并复读STATUS.COMPLETE=0，为下一节点恢复基线。"
  observations:
  - "完成前后状态：轮询STATUS.COMPLETE，期望在deadline内从0进入1；证明轮询模式产生完成终态。"
  - "硬件输出结果：完成后读取RESULT.PRIMARY/SECONDARY，期望与独立Golden一致。"
  - "清除后状态：显式Clear后再次读取STATUS.COMPLETE，期望=0；证明本Case的完成状态可恢复。"
  pass_criteria:
  - "有界完成：每个节点都在统一deadline内观察到STATUS.COMPLETE=1。"
  - "数据正确：Actual满足对应独立Golden和accuracy budget。"
  - "清除闭环：Clear前COMPLETE=1且Clear后=0，不以只看最终0证明W1C。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_polling_results", label: "轮询运算精确期望", source: "oracle", role: "expected", format: "text"}
- {key: "sqrt_poll_count", label: "平方根完成轮询次数", source: "dut", role: "actual", format: "decimal"}
- {key: "pm_poll_count", label: "相位模长完成轮询次数", source: "dut", role: "actual", format: "decimal"}
- {key: "complete_after_clear", label: "清除后完成状态", source: "dut", role: "actual", format: "bit_bool", semantic_ref: "cordic.feature.complete_status"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_008 - CORDIC中断工作模式计算与结果测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_008
case_name: CORDIC中断工作模式计算与结果测试
report_feature: |-
  1. CORDIC IRQ工作模式
  2. CORDIC 计算完成中断源
  3. CORDIC IRQ真实投递
p_level: P1
feature_refs:
- CORDIC_F_025
- CORDIC_F_034
- CORDIC_F_042
method:
  inputs:
  - "IRQ向量：选择确定性数学输入及独立Golden，并选择CALC_COMPLETE逻辑Source。"
  - "IRQ会话：运行前清除目标Source，Enable且Unmask；ISR/Service必须提供Source级latched与event_count。"
  steps:
  - "IRQ基线建立：清除目标Source并记录event_count起点，确认无残留有效投递。"
  - "中断模式配置：配置INTERRUPT工作模式、数据格式和稳定精度。"
  - "Source启用：Enable并Unmask CALC_COMPLETE，启动目标侧IRQ会话。"
  - "运算提交：提交确定性输入事务并等待event_count在deadline内发生目标增量。"
  - "硬件与投递快照：读取IRQ_RAW.CALC_COMPLETE、IRQ_STATUS.CALC_COMPLETE和IRQ_DELIVERY.LATCHED_SOURCE。"
  - "结果读取：读取RESULT.PRIMARY/必要第二结果并与独立Golden比较。"
  - "清除恢复：Clear目标IRQ与COMPLETE状态，确认目标Source不再pending并停止IRQ会话。"
  - "证据汇总：分别保存寄存器Observation、Service latch和event_count Measurement，不合并来源。"
  observations:
  - "中断Raw状态：读取IRQ_RAW.CALC_COMPLETE，期望与当前ISR清除时序相容并保留实际快照。"
  - "中断有效状态：读取IRQ_STATUS.CALC_COMPLETE，期望在有效投递窗口体现目标Source状态。"
  - "真实投递来源：读取IRQ_DELIVERY.LATCHED_SOURCE，期望锁存CALC_COMPLETE；该端点是Service事实，不是IRQ寄存器。"
  - "硬件数学结果：读取RESULT.PRIMARY/必要第二结果，期望与独立Golden一致。"
  pass_criteria:
  - "真实投递：event_count相对基线增加且Service latch包含CALC_COMPLETE。"
  - "来源一致：Raw/Status/Service证据都只能解释本次目标Source，不把event_count冒充寄存器。"
  - "数据正确：IRQ工作模式下数学Actual仍满足独立Golden。"
  - "清除恢复：Case结束目标IRQ和完成状态均按显式清除语义恢复。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_irq_source", label: "期望中断源", source: "oracle", role: "expected", format: "text"}
- {key: "event_count_delta", label: "自然中断事件增量", source: "dut", role: "actual", format: "decimal"}
- {key: "complete_status", label: "硬件完成状态", source: "dut", role: "actual", format: "bit_bool", semantic_ref: "cordic.feature.complete_status"}
- {key: "irq_delivery", label: "中断处理锁存值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.interrupt.delivery_source"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_009 - CORDIC零开销写读功能测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_009
case_name: CORDIC零开销写读功能测试
report_feature: |-
  1. CORDIC Zero-Overhead工作模式
p_level: P1
feature_refs:
- CORDIC_F_026
method:
  inputs:
  - "零开销向量：选择单结果、双结果及PM双参数代表事务，使用可区分的确定性输入序列。"
  - "原子接口：未来公共Wrap必须提供同IP原子write→read语义；Case不直接依赖芯片SDK快捷Helper。"
  steps:
  - "零开销模式配置：配置ZERO_OVERHEAD、稳定数值格式和精度。"
  - "事务节点准备：为当前函数生成输入Raw与独立Golden，记录请求序号。"
  - "原子窗口进入：通过公共同IP原子接口进入禁止跨请求错配的受控窗口。"
  - "输入提交：在窗口内按当前函数参数数量提交完整输入事务。"
  - "结果立即读取：按result_count从RESULT.PRIMARY/SECONDARY读取本请求Raw结果，不插入固定sleep。"
  - "窗口退出与解码：结束原子窗口并按Codec恢复逻辑Actual。"
  - "序列比较：Actual与当前请求Golden比较，并对多个不同函数/输入重复确认无前一请求残留。"
  observations:
  - "零开销主结果：原子窗口内读取RESULT.PRIMARY，期望对应当前request_id的独立Golden。"
  - "零开销第二结果：双结果事务读取RESULT.SECONDARY，期望对应同一request_id第二Golden。"
  pass_criteria:
  - "数据正确：所有零开销事务Actual满足独立Golden和accuracy budget。"
  - "请求对应正确：每个Raw结果只能绑定当前request_id，不能读取到前一事务结果。"
  - "无等待替代：测试路径不依赖固定sleep或轮询完成状态来伪装零开销语义。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_zero_overhead_sequence", label: "零开销请求期望序列", source: "oracle", role: "expected", format: "text"}
- {key: "sqrt_primary_raw", label: "平方根主结果原始值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.zero_overhead_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_011 - CORDIC参数数量溢出状态与恢复测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_011
case_name: CORDIC参数数量溢出状态与恢复测试
report_feature: |-
  1. CORDIC 参数溢出状态
p_level: P1
feature_refs:
- CORDIC_F_029
method:
  inputs:
  - "溢出刺激：使用Chip Execution Mapping冻结且已由current FPGATest/HIL证明的确定性未消费提交次数；不把该次数解释为硬件最小容量。"
  - "恢复向量：准备一个合法正常事务与独立Golden，用于错误清除后的功能恢复证明。"
  steps:
  - "错误基线建立：清除ARG_OVERFLOW并确认STATUS.ARG_OVERFLOW=0。"
  - "正常基线执行：先完成并消费一个合法事务，确认当前数学与结果消费路径正常。"
  - "确定性溢出刺激：按映射次数连续提交未消费请求，自然触发ARG_OVERFLOW。"
  - "溢出状态读取：在任何Clear前读取STATUS.ARG_OVERFLOW，期望=1并记录提交次数。"
  - "显式状态清除：Clear ARG_OVERFLOW后再次读取该状态，期望=0。"
  - "恢复事务执行：重新建立正常配置并执行合法事务，读取RESULT.PRIMARY。"
  - "恢复结果比较：Actual与独立Golden比较，确认错误路径未导致不可恢复状态。"
  observations:
  - "溢出硬件状态：读取STATUS.ARG_OVERFLOW，期望确定性未消费提交序列后=1；证明参数数量越界被硬件检测。"
  - "刺激次数：保留映射给出的未消费提交次数，证明本次错误来自确定性序列。"
  - "清除后状态：Clear后STATUS.ARG_OVERFLOW期望=0。"
  - "恢复硬件结果：合法恢复事务读取RESULT.PRIMARY，期望与独立Golden一致。"
  pass_criteria:
  - "因果刺激明确：正常基线可完成，随后已审核的未消费提交序列自然产生ARG_OVERFLOW。"
  - "错误状态成立：Clear前STATUS.ARG_OVERFLOW=1。"
  - "清除有效：Clear后STATUS.ARG_OVERFLOW=0。"
  - "功能恢复：错误清除后合法事务结果满足独立Golden。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "overflow_status", label: "STATUS.ARG_OVERFLOW实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.arg_overflow_status"}
- {key: "recovery_result", label: "恢复事务RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_013 - CORDIC浮点转定点溢出/下溢状态测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_013
case_name: CORDIC浮点转定点溢出/下溢状态测试
report_feature: |-
  1. CORDIC 浮点转换溢出状态
  2. CORDIC 浮点转换下溢状态
p_level: P1
feature_refs:
- CORDIC_F_032
- CORDIC_F_033
method:
  inputs:
  - "确定性向量：仅使用Chip Execution Mapping已审核的OVF、UDF和合法恢复向量；这些向量不被解释为精确硬件阈值。"
  - "函数集合：选择硬件明确支持浮点转换异常观测的函数，并分别构造溢出与下溢刺激。"
  - "恢复对照：异常清除后使用一个合法输入证明普通计算路径恢复。"
  steps:
  - "异常基线清理：Clear FLOAT2FIXED.OVERFLOW/UNDERFLOW并确认两个状态均为0。"
  - "溢出刺激执行：提交已审核OVF向量，有界等待相关状态出现。"
  - "溢出现场记录：在Clear前读取FLOAT2FIXED.OVERFLOW与UNDERFLOW原子状态，确认仅目标语义生效。"
  - "下溢刺激执行：清理后提交已审核UDF向量，并以同样方式记录两个状态。"
  - "状态清除验证：分别Clear目标状态并复读，确认对应bit恢复0且另一bit不被误改。"
  - "合法恢复：重新执行恢复向量，确认数学结果可正常获得。"
  observations:
  - "浮点转换溢出：读取FLOAT2FIXED.OVERFLOW，期望OVF刺激后=1、Clear后=0。"
  - "浮点转换下溢：读取FLOAT2FIXED.UNDERFLOW，期望UDF刺激后=1、Clear后=0。"
  - "异常隔离状态：每种刺激同时读取另一状态，期望不因测试流程误触发。"
  - "恢复硬件结果：恢复节点读取RESULT.PRIMARY，期望满足合法输入Golden。"
  pass_criteria:
  - "异常可区分：OVF与UDF刺激分别只触发对应已声明状态。"
  - "清除精确：目标状态Clear后归零且不误清另一状态。"
  - "恢复正常：异常路径结束后合法运算可再次完成。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "conversion_overflow_status", label: "FLOAT2FIXED.OVERFLOW实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.float_conversion_status"}
- {key: "conversion_underflow_status", label: "FLOAT2FIXED.UNDERFLOW实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.float_conversion_status"}
- {key: "conversion_recovery_result", label: "恢复事务RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_015 - CORDIC参数溢出IRQ自然投递测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_015
case_name: CORDIC参数溢出IRQ自然投递测试
report_feature: |-
  1. CORDIC 参数溢出中断源
  2. CORDIC IRQ使能/禁用
  3. CORDIC IRQ真实投递
p_level: P1
feature_refs:
- CORDIC_F_035
- CORDIC_F_037
- CORDIC_F_042
method:
  inputs:
  - "溢出刺激：复用P1_011已审核的确定性未消费提交序列，不用软件Force制造ARG_OVERFLOW，也不声称测得最小容量。"
  - "IRQ配置：Enable且Unmask ARG_OVERFLOW，并记录Source级event_count基线。"
  steps:
  - "IRQ基线建立：清除ARG_OVERFLOW状态/IRQ并记录event_count起点。"
  - "Source启用：Enable并Unmask ARG_OVERFLOW，启动Source级IRQ会话。"
  - "正常基线：完成并消费一个合法事务，确认无历史ARG_OVERFLOW投递。"
  - "确定性溢出刺激：执行已审核的未消费提交序列，等待目标IRQ投递。"
  - "硬件与Service快照：读取STATUS.ARG_OVERFLOW、IRQ_RAW/STATUS.ARG_OVERFLOW和IRQ_DELIVERY.LATCHED_SOURCE。"
  - "清除恢复：Clear目标状态与IRQ，确认event_count不再增长。"
  - "功能恢复：执行合法数学事务并检查结果正确。"
  observations:
  - "参数溢出状态：读取STATUS.ARG_OVERFLOW，期望越界刺激后=1。"
  - "参数溢出IRQ状态：读取IRQ_STATUS.ARG_OVERFLOW，期望在有效投递窗口体现目标Source。"
  - "真实投递锁存：读取IRQ_DELIVERY.LATCHED_SOURCE，期望包含ARG_OVERFLOW。"
  pass_criteria:
  - "自然因果成立：正常基线无投递，确定性未消费提交序列使ARG_OVERFLOW event_count增加。"
  - "来源一致：Status/IRQ/Service均对应ARG_OVERFLOW。"
  - "清除恢复：清除后无新增残留投递且合法事务可再次正确运行。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "arg_overflow_status", label: "STATUS.ARG_OVERFLOW实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.arg_overflow_status"}
- {key: "arg_overflow_irq_raw", label: "IRQ_RAW.ARG_OVERFLOW实际值", source: "dut", role: "actual", format: "bool", semantic_ref: "cordic.interrupt.raw"}
- {key: "arg_overflow_irq_status", label: "IRQ_STATUS.ARG_OVERFLOW实际值", source: "dut", role: "actual", format: "bool", semantic_ref: "cordic.interrupt.status"}
- {key: "arg_overflow_irq_latched_source", label: "IRQ_DELIVERY.LATCHED_SOURCE实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.interrupt.delivery_source"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_016 - CORDIC第二参数错误状态、自然IRQ与恢复测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_016
case_name: CORDIC第二参数错误状态、自然IRQ与恢复测试
report_feature: |-
  1. CORDIC Phase/Modulus参数顺序
  2. CORDIC 第二参数错误状态
  3. CORDIC 第二参数错误中断源
  4. CORDIC IRQ使能/禁用
  5. CORDIC IRQ真实投递
p_level: P1
feature_refs:
- CORDIC_F_023
- CORDIC_F_030
- CORDIC_F_036
- CORDIC_F_037
- CORDIC_F_042
method:
  inputs:
  - "错误刺激：先提交PHASE_MODULUS的x，再向另一数学函数入口提交参数，自然触发PM_ARG2_ERROR，不使用Force。"
  - "IRQ配置：Enable且Unmask PM_ARG2_ERROR并记录Source级event_count基线。"
  - "恢复向量：W1C清除错误报告位后，由CRG Owner复位CORDIC并重新配置，再使用合法x→y序列验证phase/modulus结果。"
  steps:
  - "IRQ基线建立：Clear PM_ARG2_ERROR状态/IRQ并记录event_count起点。"
  - "Source启用：Enable并Unmask PM_ARG2_ERROR，启动IRQ会话。"
  - "PM第一参数提交：向PHASE_MODULUS提交x并确认进入等待第二参数阶段。"
  - "错误第二来源注入：向另一函数入口提交参数，制造已审核顺序错误。"
  - "投递与状态快照：等待event_count增加并读取STATUS.PM_ARG2_ERROR、IRQ_RAW/STATUS和Service latch。"
  - "目标清除：Clear PM_ARG2_ERROR状态和IRQ Raw，确认W1C报告位立即归零。"
  - "模块恢复：通过CRG专属Driver复位当前CORDIC实例，并重新提交完整配置。"
  - "合法PM恢复：复位后执行x→y正常事务并验证phase/modulus结果正确。"
  observations:
  - "PM错误状态：读取STATUS.PM_ARG2_ERROR，期望错误序列后=1。"
  - "真实投递锁存：读取IRQ_DELIVERY.LATCHED_SOURCE，期望包含PM_ARG2_ERROR。"
  - "恢复PM结果：读取RESULT.PRIMARY/SECONDARY，与独立atan2/hypot Golden比较。"
  pass_criteria:
  - "自然错误因果：x→其他函数参数序列产生PM_ARG2_ERROR真实投递。"
  - "来源一致：状态、IRQ和Service事实指向同一错误Source。"
  - "清除与恢复正确：W1C报告位和Raw归零；外层模块复位后，合法PM事务不再产生错误且数学结果正确。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "异常退出且尚未完成恢复时，由CRG Owner复位当前CORDIC实例，避免错误事务污染后续Case"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_arg2_error", label: "期望第二参数错误", source: "oracle", role: "expected", format: "bit_bool"}
- {key: "expected_irq_source", label: "期望第二参数错误中断源", source: "oracle", role: "expected", format: "text"}
- {key: "arg2_error_status", label: "第二参数错误状态", source: "dut", role: "actual", format: "bit_bool", semantic_ref: "cordic.feature.pm_arg2_error_status"}
- {key: "irq_delivery", label: "中断处理锁存值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.interrupt.delivery_source"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_017 - CORDIC IRQ使能/禁用与软件Force测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_017
case_name: CORDIC IRQ使能/禁用与软件Force测试
report_feature: |-
  1. CORDIC IRQ使能/禁用
  2. CORDIC IRQ软件强制
  3. CORDIC IRQ真实投递
p_level: P1
feature_refs:
- CORDIC_F_037
- CORDIC_F_039
- CORDIC_F_042
method:
  inputs:
  - "Source矩阵：参数化CALC_COMPLETE、ARG_OVERFLOW、PM_ARG2_ERROR等Capability声明IRQ Source。"
  - "Force策略：每个Source先在Enable+Unmask下Force，再在Disable下Force，比较Delivery增量。"
  - "基线计数：每阶段记录Service event_count，软件计数作为Measurement而非寄存器Observation。"
  steps:
  - "Source基线建立：对当前Source执行Clear，Unmask并记录event_count起点。"
  - "Enable阶段：Enable当前Source后执行一次Force。"
  - "Enable投递等待：等待event_count增加，读取IRQ_RAW/STATUS和Service latch。"
  - "Enable阶段清除：Clear目标Source并确认pending恢复。"
  - "Disable阶段：Disable同一Source，保持其他条件不变后再次Force。"
  - "Disable阶段观测：读取IRQ_RAW与IRQ_STATUS并记录event_count delta，确认禁用语义。"
  - "Source恢复汇总：Clear残留并恢复Enable/Mask配置，对全部Source重复。"
  observations:
  - "Enable Force Raw：读取IRQ_RAW.<Source>并保存实际值，证明Force刺激进入对应Source路径。"
  - "Enable Force Status：读取IRQ_STATUS.<Source>并保存实际值。"
  - "Enable真实投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望包含当前Source。"
  - "Disable后有效状态：Disable阶段读取IRQ_STATUS.<Source>并结合event_count delta，期望没有新的有效投递。"
  pass_criteria:
  - "Source覆盖完整：Capability声明的逻辑IRQ Source均完成Enable/Disable两阶段。"
  - "Enable投递成立：Enable+Unmask时Force使event_count增加且锁存当前Source。"
  - "Disable抑制成立：Disable后同Source Force不得产生新的有效Delivery。"
  - "恢复完整：每个Source结束后目标pending被清除且配置恢复。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_irq_control", label: "IRQ Enable/Disable期望", source: "oracle", role: "expected", format: "text"}
- {key: "irq_raw", label: "IRQ_RAW.<Source>实际值", source: "dut", role: "actual", format: "bit_bool"}
- {key: "irq_status", label: "IRQ_STATUS.<Source>实际值", source: "dut", role: "actual", format: "bit_bool"}
- {key: "irq_delivery", label: "IRQ_DELIVERY.LATCHED_SOURCE实际值", source: "dut", role: "actual", format: "text"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_018 - CORDIC IRQ Mask/Unmask与Raw/Status分层测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_018
case_name: CORDIC IRQ Mask/Unmask与Raw/Status分层测试
report_feature: |-
  1. CORDIC IRQ屏蔽/解除屏蔽
  2. CORDIC IRQ原始/有效状态
p_level: P1
feature_refs:
- CORDIC_F_038
- CORDIC_F_041
method:
  inputs:
  - "Source选择：至少覆盖一个可安全Force的逻辑IRQ Source；若Capability允许则参数化全部Source。"
  - "Mask对照：保持Source Enable，先Mask后Force，再Unmask同一pending Source。"
  - "投递计数：记录Mask前后event_count delta，软件计数不作为Raw/Status替代。"
  steps:
  - "IRQ基线建立：Enable当前Source、Clear pending并记录event_count起点。"
  - "Mask设置：Mask当前Source后执行一次Force。"
  - "Mask阶段读取：在Clear前读取IRQ_RAW.<Source>与IRQ_STATUS.<Source>并记录Service event_count delta。"
  - "Mask判定：确认Raw保留刺激事实、Status/Delivery被Mask抑制。"
  - "Unmask动作：不重新Force，直接Unmask同一pending Source。"
  - "Unmask投递等待：等待规定的有效投递并读取Service latch/Status。"
  - "清除恢复：Clear目标Source并确认Raw/Status恢复0，恢复Mask配置。"
  observations:
  - "Mask后Raw：读取IRQ_RAW.<Source>，期望=1；证明Mask没有抹掉来源pending。"
  - "Mask后Status：读取IRQ_STATUS.<Source>，期望=0；证明Mask抑制有效状态。"
  - "Unmask后投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望在同一pending Source释放后锁存目标Source。"
  - "清除后状态：Clear后读取Raw/Status，期望均=0。"
  pass_criteria:
  - "Raw/Status分层：Mask阶段必须同时满足Raw=1、Status=0。"
  - "Mask抑制Delivery：Mask阶段event_count不得增加。"
  - "Unmask因果：不重新Force即可按目标IRQ语义形成有效投递。"
  - "清除闭环：Clear后Raw/Status均恢复0。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_mask_state", label: "Mask/Unmask期望状态链", source: "oracle", role: "expected", format: "text"}
- {key: "raw_masked", label: "Mask后IRQ_RAW.<Source>", source: "dut", role: "actual", format: "bit_bool"}
- {key: "status_masked", label: "Mask后IRQ_STATUS.<Source>", source: "dut", role: "actual", format: "bit_bool"}
- {key: "irq_delivery", label: "Unmask后IRQ_DELIVERY实际值", source: "dut", role: "actual", format: "text"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_019 - CORDIC IRQ单Source精确清除隔离测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_019
case_name: CORDIC IRQ单Source精确清除隔离测试
report_feature: |-
  1. CORDIC IRQ清除
  2. CORDIC IRQ原始/有效状态
p_level: P1
feature_refs:
- CORDIC_F_040
- CORDIC_F_041
method:
  inputs:
  - "Source组合：选择两个不同且可安全Force的逻辑IRQ Source，分别记为target与neighbor。"
  - "屏蔽策略：优先在Mask状态构造Raw pending，避免ISR自动清除破坏清除隔离现场。"
  steps:
  - "IRQ基线建立：Mask并Enable target/neighbor，Clear二者并确认Raw均为0。"
  - "双Source Force：分别Force target与neighbor，保持两者Raw pending共存。"
  - "清除前快照：一次读取IRQ_RAW快照，确认target=1且neighbor=1。"
  - "目标Source清除：只对target执行IRQ_CLEAR，不操作neighbor。"
  - "清除后快照：再次读取IRQ_RAW，期望target=0而neighbor仍=1。"
  - "邻居清除：Clear neighbor并确认两个Source最终均为0。"
  - "配置恢复：恢复Mask/Enable配置并记录完整前后位图。"
  observations:
  - "清除前Raw位图：读取IRQ_RAW快照，期望target和neighbor同时为1。"
  - "目标清除后Raw：读取IRQ_RAW快照，期望target=0且neighbor=1。"
  - "最终Raw状态：清除neighbor后读取IRQ_RAW，期望测试Source均为0。"
  pass_criteria:
  - "共存前提成立：清除前两个Source Raw均真实pending。"
  - "目标精确清除：Clear target后只有target归零。"
  - "邻居隔离：neighbor在target清除后继续保持pending直到自身被Clear。"
  - "最终恢复：Case结束测试Source Raw均为0。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_clear_bitmap", label: "IRQ精确清除期望位图", source: "oracle", role: "expected", format: "text"}
- {key: "raw_before_clear", label: "Clear前IRQ_RAW实际位图", source: "dut", role: "actual", format: "hex8"}
- {key: "raw_after_target_clear", label: "目标Clear后IRQ_RAW实际位图", source: "dut", role: "actual", format: "hex8"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P1_020 - CORDIC多函数连续请求与结果对应测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P1_020
case_name: CORDIC多函数连续请求与结果对应测试
report_feature: |-
  1. CORDIC 多函数顺序执行
p_level: P1
feature_refs:
- CORDIC_F_043
method:
  inputs:
  - "请求序列：构造至少四种函数的确定性输入序列，包含单结果与双结果事务，并为每个request_id生成独立Golden。"
  - "执行模式：使用能够连续提交/消费的已审核工作模式；不假设未被硬件资料承诺的无限队列深度。"
  steps:
  - "请求序列准备：生成request_id、function_id、logical_input和独立Expected列表。"
  - "CORDIC统一配置：设置稳定数值模式、结果数量和高精度节点。"
  - "首批请求提交：按已审核硬件容量/消费协议提交前若干不同函数请求。"
  - "结果顺序消费：按照目标硬件结果消费协议读取RESULT.PRIMARY/SECONDARY，并为每次Raw结果绑定request_id。"
  - "后续请求推进：消费产生空间后继续提交剩余函数请求，禁止越过未声明容量。"
  - "逐请求解码比较：每个Raw结果按对应function codec解码并与该request_id Golden比较。"
  - "顺序汇总：检查全部request_id均恰好消费一次，无重复、丢失或上一请求残留。"
  observations:
  - "连续请求硬件结果：逐次读取RESULT.PRIMARY/SECONDARY并绑定request_id，期望每次Decoded值只匹配对应请求Golden。"
  - "异常状态：读取STATUS.ARG_OVERFLOW与STATUS.PM_ARG2_ERROR，合法序列期望不出现容量/顺序错误。"
  pass_criteria:
  - "请求覆盖完整：全部计划request_id都恰好产生一次结果集合。"
  - "结果对应正确：每个Actual满足本request_id独立Golden，不能用相邻请求Golden通过。"
  - "顺序无残留：无重复消费、丢结果或跨函数残留。"
  - "合法序列无错误：不产生ARG_OVERFLOW或PM_ARG2_ERROR。"
timeout: "5 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_request_count", label: "期望连续请求数量", source: "oracle", role: "expected", format: "decimal"}
- {key: "actual_request_count", label: "实际完成请求数量", source: "dut", role: "actual", format: "decimal"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P2_001 - CORDIC DMA工作模式真实搬运等价性测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P2_001
case_name: CORDIC DMA工作模式真实搬运等价性测试
report_feature: |-
  1. CORDIC DMA工作模式
p_level: P2
feature_refs:
- CORDIC_F_027
method:
  inputs:
  - "DMA映射：仅在当前芯片Execution Mapping明确给出CORDIC DMA Request、方向、端点与Channel资源后执行；禁止沿用历史Request ID。"
  - "测试向量：选择一个可由CPU路径独立验证的确定性函数/输入，Expected来自同一PC数学Oracle。"
  - "对照路径：先用非DMA路径得到合法基线结果，再用DMA路径执行相同逻辑输入。"
  steps:
  - "执行映射检查：确认DMA work mode、Request ID、数据方向、端点宽度与清理Owner均已在当前Mapping冻结。"
  - "CPU基线运行：用非DMA路径执行测试向量并读取正确Raw结果，与独立Golden比较。"
  - "DMA资源配置：配置Peer DMA Channel、Source/Destination和CORDIC DMA工作模式，记录初始Channel状态。"
  - "DMA事务启动：按Mapping启动Channel并提交CORDIC输入/结果搬运事务，不以配置返回成功作为完成。"
  - "完成等待：有界等待DMA_CHANNEL_STATUS进入完成且无Error，同时取得CORDIC规定终态。"
  - "目的端读取：读取DMA_DESTINATION_WORD/Buffer实际内容，按CORDIC Codec恢复逻辑Actual。"
  - "等价性比较：DMA Actual同时与独立Golden和CPU基线比较。"
  - "资源清理：停止/复位本Case DMA Channel，恢复CORDIC工作模式并释放跨IP资源。"
  observations:
  - "DMA通道状态：读取DMA_CHANNEL_STATUS，期望目标Channel真实完成且无Error；证明请求到达Peer DMA硬件。"
  - "DMA目的数据：读取DMA_DESTINATION_WORD/Buffer Actual，期望解码后与独立CORDIC Golden一致。"
  - "CORDIC结果等价：DMA结果与相同输入的CPU基线逻辑结果在同一accuracy budget内等价。"
  pass_criteria:
  - "映射有效：只使用当前已审核CORDIC DMA Execution Mapping，不使用历史猜测ID。"
  - "真实搬运完成：DMA Channel进入硬件完成终态且无Error。"
  - "数据正确：DMA Destination解码后满足独立数学Golden。"
  - "路径等价：DMA与CPU基线结果满足同一逻辑Oracle。"
timeout: "15 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R2
  full_coverage_level: R2
  board: "需要片内DMA可访问的输入/输出测试内存与当前芯片Execution Mapping"
  bench: "无外部仪器；依赖Peer DMA公共自动化链"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_dma_words", label: "CORDIC DMA独立Golden", source: "oracle", role: "expected", format: "text"}
- {key: "dma_input_channel_irq_status", label: "DMA输入Channel IRQ状态", source: "dut", role: "actual", format: "hex32"}
- {key: "dma_output_channel_irq_status", label: "DMA输出Channel IRQ状态", source: "dut", role: "actual", format: "hex32"}
- {key: "dma_destination", label: "DMA目标Buffer实际值", source: "dut", role: "actual", format: "text"}
- {key: "cordic_status", label: "CORDIC STATUS.COMPLETE实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.complete_status"}
gap:
- cordic_dma_execution_mapping_gap
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P3_001 - CORDIC Float32代表节点重复稳定性测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P3_001
case_name: CORDIC Float32代表节点重复稳定性测试
report_feature: |-
  1. CORDIC Sin/Cos双结果
  2. CORDIC Phase/Modulus双结果
  3. CORDIC atan运算
  4. CORDIC sinh/cosh双结果
  5. CORDIC atanh运算
  6. CORDIC exp运算
  7. CORDIC ln运算
  8. CORDIC sqrt运算
  9. CORDIC tan运算
  10. CORDIC Float32模式
p_level: P3
feature_refs:
- CORDIC_F_001
- CORDIC_F_002
- CORDIC_F_003
- CORDIC_F_004
- CORDIC_F_005
- CORDIC_F_006
- CORDIC_F_007
- CORDIC_F_008
- CORDIC_F_009
- CORDIC_F_011
method:
  inputs:
  - "固定向量集：使用固定seed标识九类函数各一个已审核Float32代表合法节点；不宣称覆盖定点Codec、边界或完整合法域。"
  - "数值配置：只使用Float32、32-bit、Normalized、Polling和Status能力；Expected由独立Float32 Raw Golden计算。"
  - "重复参数：每个函数节点执行固定重复轮数，计划轮数和完成轮数写入Artifact。"
  steps:
  - "向量集确认：加载固定seed向量清单并计算每个代表节点的独立Float32 Raw Golden。"
  - "能力与配置：确认所需Runtime Feature后配置Float32、32-bit、Normalized、Polling和Status。"
  - "重复激励：对每个函数节点按稳定参数顺序提交输入，连续执行固定重复轮数。"
  - "状态与结果读取：每轮在有界轮询内读取Complete、Primary和适用的Secondary Raw结果。"
  - "清除验证：每轮读取结果后清除Complete和错误状态，并读取清除后的状态快照。"
  - "稳定性比较：逐轮与Golden比较，并比较同一节点重复Raw序列的一致性。"
  - "证据汇总：记录seed、节点、计划轮数、完成轮数、Raw结果序列和状态序列。"
  observations:
  - "Primary结果序列：读取RESULT.PRIMARY逐轮Raw值，期望每轮与当前节点Golden一致且重复序列相同。"
  - "Secondary结果序列：双结果函数读取RESULT.SECONDARY，期望每轮与当前节点Golden一致且重复序列相同。"
  - "完成状态：每轮读取STATUS.COMPLETE，期望在有界轮询内形成完成终态。"
  - "清除后状态：读取清除后的STATUS.COMPLETE和错误状态，期望均为零。"
  pass_criteria:
  - "覆盖完成：九类函数节点和固定重复轮数全部完成，无超时。"
  - "结果正确：每轮Primary及适用的Secondary Raw结果与独立Float32 Golden逐字一致。"
  - "重复稳定：同一节点的重复Raw结果序列完全一致，不出现随机漂移。"
  - "状态闭环：每轮完成状态为COMPLETE，清除后COMPLETE和错误状态均为零。"
timeout: "30 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "vector_seed", label: "固定向量Seed", source: "artifact", role: "actual", format: "hex32"}
- {key: "planned_rounds", label: "计划执行轮数", source: "artifact", role: "actual", format: "decimal"}
- {key: "completed_rounds", label: "完成执行轮数", source: "artifact", role: "actual", format: "decimal"}
- {key: "vectors", label: "CORDIC结果与状态重复记录", source: "artifact", role: "actual", format: "text"}
- {key: "actual_primary_raw", label: "RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
- {key: "actual_status_after_clear", label: "清除后STATUS实际值", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.request_status"}
gap: []
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P3_002 - CORDIC目标侧单次执行周期表征测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P3_002
case_name: CORDIC目标侧单次执行周期表征测试
report_feature: |-
  1. CORDIC 单次运算周期
p_level: P3
feature_refs:
- CORDIC_F_045
method:
  inputs:
  - "性能矩阵：覆盖代表单输入单结果、单输入双结果、双输入双结果函数，并区分FIXED/FLOAT32等目标配置。"
  - "计时来源：只使用目标侧独立cycle counter或等价硬件Observer；PC wall-clock不得作为CORDIC周期结论。"
  - "性能判定：当前无权威绝对阈值时只表征cycles分布，不因测量值大小判PASS。"
  steps:
  - "计时能力检查：确认TIMING.CYCLE_COUNT Observer可用且测量开销处理方法已冻结。"
  - "函数节点准备：选择函数/格式/输入并生成独立Golden。"
  - "计时事务启动：在目标侧读取start_cycle并执行恰好一个CORDIC原子事务。"
  - "计时事务结束：结果可读后取得end_cycle并计算cycle delta，同时保留Raw结果。"
  - "功能正确性校验：先解码Actual并与独立Golden比较，功能错误节点不得进入性能统计。"
  - "重复采样：每个性能节点重复固定次数并记录原始cycle samples。"
  - "统计汇总：报告min/median/max或项目冻结统计量；无规格阈值时不声称性能达标。"
  observations:
  - "目标周期计数：读取TIMING.CYCLE_COUNT样本，期望每个有效事务取得非负且可追溯cycle delta。"
  - "关联硬件结果：读取RESULT.PRIMARY/必要第二结果，期望满足独立Golden；保证周期样本对应正确运算。"
  pass_criteria:
  - "功能先行：只有数学结果满足accuracy budget的样本才进入性能统计。"
  - "采样完整：各计划函数/格式节点达到规定重复次数并保留Raw cycle samples。"
  - "报告边界正确：没有冻结性能阈值时只发布表征值，不把“更快/更慢”自动判为硬件PASS/FAIL。"
  - "计时来源真实：所有cycles来自目标侧独立周期Observer而非PC耗时。"
timeout: "30 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "expected_primary_raw", label: "性能节点独立主结果Golden", source: "oracle", role: "expected", format: "hex32"}
- {key: "target_cycles", label: "TIMING.CYCLE_COUNT实际样本", source: "dut", role: "actual", format: "decimal", semantic_ref: "cordic.feature.timing_cycles"}
- {key: "timed_primary_raw", label: "计时事务RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.math_result"}
gap:
- cordic_accuracy_budget_gap
```
<!-- ET_CASE_SPEC_END -->

### CORDIC_P3_003 - CORDIC零开销原子窗口抗IRQ干扰测试

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CORDIC_P3_003
case_name: CORDIC零开销原子窗口抗IRQ干扰测试
report_feature: |-
  1. CORDIC Zero-Overhead原子窗口
  2. CORDIC Zero-Overhead工作模式
p_level: P3
feature_refs:
- CORDIC_F_044
- CORDIC_F_026
method:
  inputs:
  - "原子事务：使用双参数PHASE_MODULUS或等价可暴露中断插入风险的零开销事务，Expected由atan2/hypot独立计算。"
  - "干扰源：使用平台已审核的可控目标侧IRQ，在关键窗口内尝试插入另一个CORDIC请求；干扰源不得直接越层访问CORDIC实现。"
  - "对照策略：分别执行原子保护开启与验证用受控干扰场景，记录request_id与中断发生事实。"
  steps:
  - "基线事务执行：无干扰条件下执行零开销原子事务，确认结果满足Golden。"
  - "干扰会话建立：配置可控IRQ并记录干扰event_count基线，不在ISR中直接绕过公共CORDIC路径。"
  - "原子保护节点：通过公共zero_overhead_execute进入受保护write→read窗口，同时触发IRQ干扰。"
  - "保护节点结果读取：窗口结束后绑定当前request_id的Raw结果并记录干扰是否延后交付。"
  - "干扰压力重复：使用固定seed/固定轮数重复原子窗口与IRQ交错，覆盖多个触发相位。"
  - "请求结果核对：每轮结果必须与本轮PM Golden对应，不能出现由ISR请求造成的错配。"
  - "干扰证据汇总：汇总CORDIC结果、request_id、IRQ event_count和异常状态，确认无ARG2_ERROR/ARG_OVERFLOW误触发。"
  - "恢复清理：停止干扰会话并确认后续普通CORDIC事务仍可正确运行。"
  observations:
  - "原子窗口硬件结果：读取RESULT.PRIMARY/SECONDARY，期望每轮只匹配当前PM request_id的Golden。"
  - "CORDIC错误状态：读取STATUS.PM_ARG2_ERROR与STATUS.ARG_OVERFLOW，受保护合法事务期望均为0。"
  - "干扰交付事实：IRQ event_count/latched来源作为软件Measurement/Service事实保存，不冒充CORDIC寄存器。"
  pass_criteria:
  - "基线正确：无干扰零开销事务满足独立Golden。"
  - "抗干扰正确：受控IRQ交错的所有受保护事务均保持request/result对应且数学结果正确。"
  - "无协议破坏：合法受保护事务不产生PM_ARG2_ERROR或ARG_OVERFLOW。"
  - "恢复正确：压力结束后普通CORDIC事务仍可正确完成。"
timeout: "30 s"
cleanup:
- "清除本Case产生且由CORDIC责任域拥有的可清状态/中断状态"
- "恢复本Case修改的CORDIC配置；跨IP资源由PC Case按owner逆序释放"
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: "无额外要求"
  bench: "无额外要求"
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- {key: "atomic_primary_raw", label: "原子窗口RESULT.PRIMARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.zero_overhead_result"}
- {key: "atomic_secondary_raw", label: "原子窗口RESULT.SECONDARY实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.zero_overhead_result"}
- {key: "forced_irq_pending", label: "受控IRQ Pending实际Raw", source: "dut", role: "actual", format: "hex32", semantic_ref: "cordic.feature.irq_raw"}
gap:
- cordic_zero_overhead_atomicity_gap
```
<!-- ET_CASE_SPEC_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | ADAPTED=46 | ADAPTED=24 | 原语义Gap已迁移到ET6801只读Execution Mapping；P1_003已采用人工批准的1e-3误差预算，P2_001已补齐DMA Mapping，两项均等待当前代码定向HIL | `ET6801_cordic.md` |

`SUPPORTED`或历史测试代码存在不等于当前平台已经实现，也不等于当前SHA HIL PASS。当前已完成P0_002、P0_003、P0_004、P1_001～P1_009、P1_011～P1_013、P1_015～P1_020、P2_001和P3_001～P3_003的Source/Design闭合；P2_001在当前DMA映射缺失时按内部集成缺口失败关闭。P1_003 current-code HIL已发现Scale=7误差超出历史统一预算，必须保留FAIL与原始证据，不能通过扩大公共容差或改为SKIP宣称通过。

## 5. Common Gap / Evolution

### 5.1 当前公共 Gap Registry

| Gap ID | 状态 | 解除条件 |
|---|---|---|
| `cordic_case_implementation_gap` | CLOSED | Registry、唯一真实 `test_cordic_p*.py`、Evidence/Report绑定已覆盖24个Formal Case；缺少内部运行映射时由Case运行期失败关闭。 |
| `cordic_capability_semantic_mapping_gap` | CLOSED | Machine Capability已发布SVD可证明的函数集合、位宽、Range、Result Count、Work Mode、状态和IRQ Source；SVD不能表达的数值事实由Chip Execution Mapping承接。 |
| `cordic_fixed_codec_mapping_gap` | PARTIAL | ET6801代表向量所需定点Codec、角度单位、Scale补偿和16-bit打包已进入只读Execution Mapping；完整合法域和所有函数Scale公式仍需更高权威证据。 |
| `cordic_float_codec_mapping_gap` | OPEN | 冻结float32 Raw传输、结果解码以及合法有限值边界，不用SDK pointer ABI充当公共Wire语义。 |
| `cordic_accuracy_budget_gap` | OPEN / HIL_FAIL | current-code HIL在ARCTAN Scale=7测得稳定绝对误差1.475113549724849e-4，超过历史源码中未实际调度执行的统一1e-4阈值；须获得权威设计/LRS逐函数×格式×Scale×precision误差预算，或经人工批准用current-HIL characterization冻结ET6801专属验收包络。不得直接放宽公共容差。 |
| `cordic_scale_formula_gap` | PARTIAL | ET6801已冻结ARCTAN受影响公式和SINCOS不受影响语义；其余适用函数公式仍需LRS/RTL/设计确认。 |
| `cordic_precision_limit_mapping_gap` | PARTIAL | ET6801平台计划节点1..8已由current Driver/FPGATest冻结；硬件完整MAX_ITER_CYC仍待设计资料确认。 |
| `cordic_result_count_mapping_gap` | CLOSED | 公共Config已映射三类ONE/TWO选项，P1_005按声明结果端点建立六节点回归；仍需本轮HIL确认实现事实。 |
| `cordic_arg_count_lifecycle_mapping_gap` | OPEN | 冻结双参数事务在首参数、第二参数、结果未消费/已消费阶段的 `ARG_COUNT.CURRENT` Expected序列。 |
| `cordic_argument_capacity_mapping_gap` | PARTIAL | ET6801已冻结可复现的四次未消费提交刺激；精确容量和最小越界点仍待设计资料确认。 |
| `cordic_float2fixed_boundary_gap` | PARTIAL | ET6801已冻结SQRT的确定性OVF/UDF与恢复向量；精确阈值和邻近边界仍待设计资料确认。 |
| `cordic_zero_overhead_atomicity_gap` | CLOSED | CORDIC Test Extension保存/恢复调用者PRIMASK，Wrap只调用该Driver入口；P3_003已完成受控Pending隔离。 |
| `cordic_current_pm_helper_bug` | OPEN | 目标Chip SDK的整数PM零开销Helper修复错误输入端点/参数模型，或公共Wrap明确不调用该Helper并由受测路径证明。 |
| `cordic_request_capacity_mapping_gap` | OPEN | 明确多函数连续请求可安全提交/消费的容量和顺序协议，不把历史“parallel”测试代码当规格。 |
| `cordic_dma_execution_mapping_gap` | OPEN | 当前Chip资料给出CORDIC DMA Request ID、方向、端点和DMA Channel映射；禁止沿用旧Revision ID。当前映射缺失只影响运行期可执行性，不影响Case实现状态。 |
| `cordic_dma_driver_mode_gap` | CLOSED | CORDIC稳定Config/WorkMode接口已支持DMA选择，Case只通过Driver/Service/Wrap调用，不直接写Raw控制位。 |
| `cordic_reset_execution_mapping_gap` | CLOSED | CRG专属Driver/Service/Wrap已提供CORDIC复位映射，P0_004由PC Case跨IP编排复位后重新配置。 |
| `cordic_timing_observer_mapping_gap` | CLOSED | CORDIC Test Extension在目标侧DWT边界内返回周期结果，P3_002只消费稳定Cycle Count。 |
| `cordic_legal_domain_vector_gap` | OPEN | 九类函数的合法域/边界向量集由目标资料与数学定义共同审核并固定seed。 |
| `cordic_irq_interference_test_support_gap` | OPEN | 提供可控目标侧IRQ干扰源，且不会在ISR中绕过公共CORDIC责任链。 |
| `cordic_width_capability_mapping_gap` | CLOSED | SVD Capability声明16/32-bit宽度，ET6801 Execution Mapping冻结参数存储位置与16-bit双结果打包语义。 |
| `cordic_codec_mapping_gap` | OPEN | P3覆盖所需FIXED/FLOAT32 Codec及Range/Scale组合全部有可追溯映射。 |

### 5.2 后续实现约束

1. `CORDIC_P0_001`停止使用且ID不得复用；Static/Runtime Capability一致性由平台发现与契约门禁负责，不计入CORDIC硬件覆盖。
2. 当前24个Case均为SPEC；P2_001的DMA路由由Execution Mapping提供，缺失时运行期失败关闭；P1_010已合入P1_007，P1_014已合入P1_008，P1_012已合入P1_016，重复Case ID不得恢复。
3. 数学正确性始终使用独立PC Oracle；历史FPGA输出只用于设计追溯，不能成为Golden。
4. 所有Hardware Observation使用稳定Endpoint并保留Raw值；Decoded值/Error/Golden属于Measurement。
5. IRQ Raw、IRQ Status、Service latch和event_count四类来源必须分开。
6. DMA Case必须使用芯片Execution Mapping提供的Request与Endpoint；Mapping闭合前失败关闭，闭合后仍需真实HIL形成结果。
7. Precision Case用于表征低精度误差并验证高精度预算，不要求所有precision节点满足同一固定容差。
8. Scale、TAN特殊Codec、float2fixed边界等目标语义不清时保留Gap，不用历史magic factor替代权威定义。
9. 文档完成后必须运行当前R120/R140 PLAN/Method/Chip Mapping门禁；门禁未实际PASS不得声明CORDIC文档完成。

### 5.3 Feature完整覆盖环境矩阵

| Feature | 最小环境/执行映射 | 当前结论 |
|---|---|---|
| F001～F009、F011、F013、F015、F020～F026、F028、F030～F031、F034、F036～F043 | DUT + 当前CORDIC Service/Wrap/Driver；IRQ项需要目标CPU真实ISR | 不需要外部仪器；已有部分Case，剩余按现有接口补齐 |
| F010、F012、F014、F016～F019、F029、F032～F033 | DUT + Chip Capability + ET6801只读Execution Mapping | 当前代表节点已闭合；更广合法域、完整Scale公式、硬件上限和精确阈值保留演进Gap |
| F027 | DUT + DMA Peer + 当前芯片CORDIC DMA Request/方向/端点映射 | 需要片内DMA配测，不需要外部仪器 |
| F044 | DUT + 可控目标侧IRQ干扰源 + Zero-Overhead原子事务入口 | 需要目标侧原子执行映射，不可由PC串口时序模拟 |
| F045 | DUT + 目标侧独立Cycle Counter/Test Extension | 需要片内性能观察源，不需要外部仪器 |
| F046 | DUT + CRG/Reset Owner + 复位后Service恢复 | 需要模块复位执行映射，不需要整板断电 |

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CORDIC_P0_002:
    summary: "CORDIC定点核心函数矩阵记录各函数的独立Golden与硬件Raw结果。"
    fields:
      - {source: measurement, path: function, label: 数学函数, format: text, aggregate: distinct}
      - {source: measurement, path: expected_primary_raw, label: 主结果Golden, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_primary_raw, label: RESULT.PRIMARY实际Raw, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_secondary_raw, label: RESULT.SECONDARY实际Raw, format: hex32, aggregate: distinct}
  CORDIC_P0_004:
    summary: "CORDIC经CRG专属复位后重新配置，复位前后SQRT结果和完成状态均可恢复。"
    fields:
      - {source: measurement, path: expected_recovery_raw, label: 复位前后独立Golden, format: hex32, aggregate: same}
      - {source: observation, path: pre_reset_result, label: 复位前RESULT.PRIMARY, format: hex32, aggregate: same}
      - {source: observation, path: post_reset_result, label: 复位后RESULT.PRIMARY, format: hex32, aggregate: same}
      - {source: observation, path: post_reset_status, label: 复位后STATUS.COMPLETE, format: hex32, aggregate: same}
  CORDIC_P0_003:
    summary: "CORDIC九类Float32函数在精确合法节点产生正确Raw结果并完成状态闭环。"
    fields:
      - {source: measurement, path: function, label: 数学函数, format: text, aggregate: distinct}
      - {source: measurement, path: expected_primary_raw, label: 主结果Golden, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_primary_raw, label: RESULT.PRIMARY实际Raw, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_secondary_raw, label: RESULT.SECONDARY实际Raw, format: hex32, aggregate: distinct}
  CORDIC_P1_001:
    summary: "CORDIC两种输入范围分别执行同一逻辑角度，并记录各路径的实际Raw结果。"
    fields:
      - {source: measurement, path: logical_angle_radians, label: 独立逻辑角度, format: float, aggregate: distinct}
      - {source: observation, path: range_primary_raw, label: 当前范围RESULT.PRIMARY, format: hex32, aggregate: distinct}
      - {source: observation, path: range_secondary_raw, label: 当前范围RESULT.SECONDARY, format: hex32, aggregate: distinct}
  CORDIC_P1_002:
    summary: "CORDIC不同参数/结果位宽记录完整Raw字及16-bit高低半字拆包结果。"
    fields:
      - {source: measurement, path: logical_angle_radians, label: 位宽矩阵逻辑角度Golden, format: float, aggregate: same}
      - {source: observation, path: width_primary_raw, label: RESULT.PRIMARY实际Raw, format: hex32, aggregate: distinct}
      - {source: observation, path: width_packed_values, label: RESULT.PRIMARY高低半字, format: text, aggregate: distinct}
  CORDIC_P1_003:
    summary: "CORDIC各Scale节点同时记录SINCOS隔离路径和ARCTAN缩放路径结果。"
    fields:
      - {source: measurement, path: expected_scale_values, label: Scale独立Expected, format: text, aggregate: same}
      - {source: observation, path: scale_unaffected_primary_raw, label: Scale隔离路径RESULT.PRIMARY, format: text, aggregate: distinct}
      - {source: observation, path: scale_affected_primary_raw, label: Scale受影响路径RESULT.PRIMARY, format: text, aggregate: distinct}
      - {source: observation, path: scale_status_before_clear, label: 各Scale节点STATUS清除前值, format: text, aggregate: distinct}
  CORDIC_P1_004:
    summary: "CORDIC各公开精度节点记录两个结果端点和完成状态。"
    fields:
      - {source: measurement, path: expected_precision_budget, label: 最高精度绝对误差预算, format: float, aggregate: same}
      - {source: observation, path: precision_primary_raw, label: 各精度节点RESULT.PRIMARY, format: text, aggregate: distinct}
      - {source: observation, path: precision_secondary_raw, label: 各精度节点RESULT.SECONDARY, format: text, aggregate: distinct}
      - {source: observation, path: precision_status_before_clear, label: 各精度节点STATUS清除前值, format: text, aggregate: distinct}
  CORDIC_P1_005:
    summary: "CORDIC三类双结果函数在ONE/TWO配置下返回正确的已声明结果。"
    fields:
      - {source: measurement, path: function, label: 双结果数学函数, format: text, aggregate: distinct}
      - {source: measurement, path: result_count, label: 结果数量配置, format: text, aggregate: distinct}
      - {source: observation, path: primary_raw, label: RESULT.PRIMARY实际Raw, format: hex32, aggregate: distinct}
      - {source: observation, path: secondary_raw, label: RESULT.SECONDARY实际Raw, format: hex32, aggregate: distinct}
  CORDIC_P1_011:
    summary: "CORDIC参数数量溢出状态可观测，清除后合法SINCOS事务恢复。"
    fields:
      - {source: observation, path: overflow_status, label: 参数溢出状态 STATUS.ARG_OVERFLOW, format: hex32, aggregate: same}
      - {source: observation, path: recovery_result, label: 恢复事务RESULT.PRIMARY, format: hex32, aggregate: same}
  CORDIC_P1_006:
    summary: "CORDIC Phase/Modulus参数计数按0→1→0变化，结果消费后可继续单参数运算。"
    fields:
      - {source: observation, path: argument_count_sequence, label: 参数计数序列, format: text, aggregate: distinct}
      - {source: measurement, path: pm_poll_count, label: PM完成轮询次数, format: decimal, aggregate: range}
      - {source: measurement, path: recovery_poll_count, label: 恢复事务轮询次数, format: decimal, aggregate: range}
  CORDIC_P1_007:
    summary: "CORDIC Polling模式下单参数与双参数事务均自然完成，COMPLETE可精确清除。"
    fields:
      - {source: measurement, path: expected_polling_results, label: 精确数学期望, format: text, aggregate: same}
      - {source: measurement, path: sqrt_poll_count, label: 平方根完成轮询次数, format: decimal, aggregate: range}
      - {source: measurement, path: pm_poll_count, label: 相位模长完成轮询次数, format: decimal, aggregate: range}
      - {source: observation, path: complete_after_clear, label: Clear后COMPLETE, format: bool, aggregate: same}
  CORDIC_P1_008:
    summary: "CORDIC Interrupt模式下真实计算可自然产生完成中断并交付CPU。"
    fields:
      - {source: measurement, path: expected_irq_source, label: 期望中断源, format: text, aggregate: same}
      - {source: measurement, path: event_count_delta, label: 自然中断事件增量, format: decimal, aggregate: same}
      - {source: observation, path: complete_status, label: 硬件完成状态, format: bool, aggregate: same}
      - {source: observation, path: irq_delivery, label: 中断处理锁存值, format: hex32, aggregate: same}
  CORDIC_P1_009:
    summary: "CORDIC Zero-Overhead原子请求返回当前事务结果，不读取上一事务残留。"
    fields:
      - {source: measurement, path: expected_zero_overhead_sequence, label: 原子请求期望序列, format: text, aggregate: same}
      - {source: observation, path: sqrt_primary_raw, label: SQRT主结果Raw, format: hex32, aggregate: same}
  CORDIC_P1_013:
    summary: "CORDIC浮点转定点溢出/下溢状态分别记录，并验证清除后的恢复结果。"
    fields:
      - {source: observation, path: conversion_overflow_status, label: 浮点转定点溢出 FLOAT2FIXED.OVERFLOW, format: hex32, aggregate: same}
      - {source: observation, path: conversion_underflow_status, label: 浮点转定点下溢 FLOAT2FIXED.UNDERFLOW, format: hex32, aggregate: same}
      - {source: observation, path: conversion_recovery_result, label: 恢复事务RESULT.PRIMARY, format: hex32, aggregate: same}
  CORDIC_P1_016:
    summary: "错误的PM第二参数来源同时产生专用状态和自然中断，清除后可恢复合法PM事务。"
    fields:
      - {source: measurement, path: expected_irq_source, label: 期望中断源, format: text, aggregate: same}
      - {source: measurement, path: event_count_delta, label: 自然中断事件增量, format: decimal, aggregate: same}
      - {source: observation, path: arg2_error_status, label: 第二参数错误状态, format: bool, aggregate: same}
      - {source: observation, path: irq_delivery, label: 中断处理锁存值, format: hex32, aggregate: same}
  CORDIC_P1_015:
    summary: "CORDIC参数溢出自然产生ARG_OVERFLOW IRQ，并记录清除前的状态与投递锁存。"
    fields:
      - {source: observation, path: arg_overflow_status, label: 参数溢出状态 STATUS.ARG_OVERFLOW, format: hex32, aggregate: same}
      - {source: observation, path: arg_overflow_irq_raw, label: 参数溢出 IRQ_RAW, format: bool, aggregate: same}
      - {source: observation, path: arg_overflow_irq_status, label: 参数溢出 IRQ_STATUS, format: bool, aggregate: same}
      - {source: observation, path: arg_overflow_irq_latched_source, label: 参数溢出中断锁存源, format: hex32, aggregate: same}
  CORDIC_P1_017:
    summary: "三类CORDIC IRQ Source在Enable时可由Force真实投递，Disable后不再产生新Delivery。"
    fields:
      - {source: measurement, path: expected_irq_source, label: 当前IRQ Source, format: text, aggregate: distinct}
      - {source: measurement, path: event_count_delta, label: Enable阶段事件增量, format: decimal, aggregate: same}
      - {source: observation, path: irq_delivery, label: Enable阶段ISR Latch, format: hex32, aggregate: distinct}
      - {source: measurement, path: disabled_event_count_delta, label: Disable阶段事件增量, format: decimal, aggregate: same}
  CORDIC_P1_018:
    summary: "CORDIC IRQ Mask保留Raw并抑制Status/Delivery，Unmask同一Pending后可真实投递。"
    fields:
      - {source: observation, path: raw_masked, label: Mask阶段IRQ Raw, format: bool, aggregate: same}
      - {source: observation, path: status_masked, label: Mask阶段IRQ Status, format: bool, aggregate: same}
      - {source: measurement, path: masked_event_count_delta, label: Mask阶段事件增量, format: decimal, aggregate: same}
      - {source: observation, path: irq_delivery, label: Unmask阶段ISR Latch, format: hex32, aggregate: same}
  CORDIC_P1_019:
    summary: "两个CORDIC IRQ Raw Source共存时，Clear目标Source不会误清邻居Source。"
    fields:
      - {source: measurement, path: expected_clear_bitmap, label: 期望Raw位图链, format: text, aggregate: same}
      - {source: observation, path: raw_before_clear, label: Clear前IRQ Raw位图, format: hex32, aggregate: same}
      - {source: observation, path: raw_after_target_clear, label: 目标Clear后IRQ Raw位图, format: hex32, aggregate: same}
      - {source: observation, path: raw_final, label: 最终IRQ Raw位图, format: hex32, aggregate: same}
  CORDIC_P1_020:
    summary: "CORDIC连续切换五种单参数函数时，每个结果都归属于当前请求。"
    fields:
      - {source: measurement, path: expected_request_count, label: 期望请求数, format: decimal, aggregate: same}
      - {source: measurement, path: actual_request_count, label: 实际完成请求数, format: decimal, aggregate: same}
  CORDIC_P2_001:
    summary: "CORDIC DMA模式记录独立Golden、DMA双通道IRQ状态和目标Buffer。"
    fields:
      - {source: measurement, path: expected_dma_words, label: CORDIC DMA独立Golden, format: text, aggregate: same}
      - {source: observation, path: dma_input_channel_irq_status, label: DMA输入Channel IRQ状态, format: hex32, aggregate: same}
      - {source: observation, path: dma_output_channel_irq_status, label: DMA输出Channel IRQ状态, format: hex32, aggregate: same}
      - {source: observation, path: dma_destination, label: DMA目标Buffer实际值, format: text, aggregate: same}
  CORDIC_P3_001:
    summary: "CORDIC九类Float32代表节点重复执行结果稳定，完成状态可清除。"
    fields:
      - {source: artifact, path: vector_seed, label: 固定向量Seed, format: hex32, aggregate: same}
      - {source: artifact, path: planned_rounds, label: 计划执行轮数, format: decimal, aggregate: same}
      - {source: artifact, path: completed_rounds, label: 完成执行轮数, format: decimal, aggregate: same}
      - {source: artifact, path: vectors, label: CORDIC结果与状态重复记录, format: text, aggregate: same}
  CORDIC_P3_002:
    summary: "CORDIC结果正确前提下记录目标侧单次执行周期和计时事务Raw结果。"
    fields:
      - {source: measurement, path: expected_primary_raw, label: 性能节点独立Golden, format: hex32, aggregate: same}
      - {source: observation, path: target_cycles, label: 目标侧执行周期 TIMING.CYCLE_COUNT, format: decimal, aggregate: distinct}
      - {source: observation, path: timed_primary_raw, label: 计时事务RESULT.PRIMARY, format: hex32, aggregate: same}
  CORDIC_P3_003:
    summary: "CORDIC零开销原子窗口在受控IRQ Pending下保持主次结果对应关系。"
    fields:
      - {source: observation, path: atomic_primary_raw, label: 原子窗口RESULT.PRIMARY, format: hex32, aggregate: same}
      - {source: observation, path: atomic_secondary_raw, label: 原子窗口RESULT.SECONDARY, format: hex32, aggregate: same}
      - {source: observation, path: forced_irq_pending, label: 受控IRQ Pending, format: hex32, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
