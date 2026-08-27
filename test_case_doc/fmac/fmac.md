# FMAC Stable IP Contract

> 本文件定义 FMAC 的芯片中立硬件 Feature、Formal Case 规划、Oracle、Observation、资源和未来自动化动作语义。
> 当前已实现 FMAC PC Driver、Firmware Service、Common Wrap、目标芯片Driver Test Extension和23个Formal Case，并已接入全局运行时组合；PC模块边界与Public API说明已按R220注释契约复核。全部Case均可由DUT片内FMAC、DMA、内存和目标周期计数完成，不存在外部接线或仪器阻塞；源码实现不等于硬件PASS。
> 芯片实例、物理地址、IRQn、实际寄存器/Field、DMA request 编号、SDK API、Driver 缺陷、状态可见延迟和历史资料只进入同目录 `<CHIP>_fmac.md`。
> Formal Case 前置隔离统一遵循 `R210`：第一次 Feature 配置前由 Case 显式复位参与 IP；DMA Case 先复位 DMA，再复位 FMAC，最后复位 Resource Pool。本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

### 0.1 稳定数据、配置与执行语义

| 稳定对象 | 公共语义 | 约束 |
|---|---|---|
| `FmacDataFormat` | `Q15` / `FLOAT32` | Q15 固定为 signed s(16,15)；FLOAT32 为 IEEE754 single precision。 |
| `FmacFilterKind` | `FIR` / `IIR_DIRECT_FORM_1` | IIR 只冻结 Direct Form 1 模式身份；反馈符号、状态排列和中间量化必须由目标芯片证据闭合。 |
| `FmacBufferLayout` | `x1_start/x1_size/x2_start/x2_size/y_start/y_size` | 均为逻辑位置/容量；合法范围和组合约束由目标 Capability 给出。 |
| `FmacWatermark` | `ONE/TWO/FOUR/EIGHT` | 逻辑水位选项；支持集合和状态可见延迟由目标适配给出。 |
| `feedforward_taps` | FIR/IIR 前馈系数数量 | 必须与前馈系数装载数量及 X2 容量约束一致。 |
| `feedback_taps` | IIR 反馈系数数量 | FIR 必须为 0；IIR 反馈系数段紧随前馈段装载。 |
| `fir_first_valid_output_index` | FIR 第一项有效输出相对当前输入事务的逻辑索引 | 属于目标适配事实；未闭合时不得用历史数组平移或搜索最佳平移量代替。 |
| `iir_first_valid_output_index` | IIR 第一项有效输出相对当前输入事务的逻辑索引 | 必须与反馈初态和状态排列共同冻结。 |
| `FmacClipPolicy` | `WRAP` / `CLIP_SATURATE` | 控制内部累加越界处理。 |
| `FmacFinalPolicy` | `SATURATE` / `WRAP` | 控制最终 Q15 输出越界处理。 |
| `FmacOutputMode` | `RAW` / `SATURATE_12` / `SATURATE_16` | RAW 不消费 Offset/Shift/Saturation 后处理；Offset/Shift Case 必须选择真正消费这些配置的模式。 |
| `output_offset_code` | 16-bit 配置值 | 完整 signed/高位扩展语义由目标证据给出；公共基础 Case 可限制在无歧义范围。 |
| `FmacOutputShift` | `LEFT_8..LEFT_1 / NONE / RIGHT_1..RIGHT_7` | 共 16 个稳定逻辑选项；不发布超出 4-bit 编码域的额外选项。 |
| `FmacIrqSource` | 11 类 IRQ Source | `X1_WRITE_REQUEST / Y_READ_REQUEST / SATURATION / X1_OVERFLOW / Y_UNDERFLOW / P_ERROR / PQ_ERROR / Q_ERROR / X1_LOAD_ERROR / X2_LOAD_ERROR / Y_LOAD_ERROR`。 |
| `FmacDmaGate` | 输入写请求 / 输出读请求独立门控 | 只控制 FMAC request；DMA Channel、DMAMUX、目标内存属于 Peer/Execution Mapping。 |

IIR 系数稳定装载顺序固定为：先 `feedforward_taps` 个前馈系数，再 `feedback_taps` 个反馈系数。Y 反馈初始状态的排列只有在目标设计证据闭合后才能进入 bit-exact IIR Oracle。

### 0.2 稳定 Observation Endpoint

Canonical Observation 遵循“一条 Observation = 一个 `source + device_id + endpoint + raw value`”。以下名称只表达公共稳定语义；目标芯片实际 Field 由 `<CHIP>_fmac.md` 映射。

| Endpoint | 来源 | 原子事实 |
|---|---|---|
| `CONFIG.X1_START` | `dut` | X1 逻辑起始位置读回 |
| `CONFIG.X1_SIZE` | `dut` | X1 容量读回 |
| `CONFIG.X2_START` | `dut` | X2 逻辑起始位置读回 |
| `CONFIG.X2_SIZE` | `dut` | X2 容量读回 |
| `CONFIG.Y_START` | `dut` | Y 逻辑起始位置读回 |
| `CONFIG.Y_SIZE` | `dut` | Y 容量读回 |
| `STATUS.ACTIVE` | `dut` | 当前功能是否活动 |
| `STATUS.X1_SPARE_COUNT` | `dut` | X1 剩余可写元素数量 |
| `STATUS.Y_UNREAD_COUNT` | `dut` | Y 未读元素数量 |
| `STATUS.X1_FULL` | `dut` | X1 Full 状态 |
| `STATUS.Y_EMPTY` | `dut` | Y Empty 状态 |
| `STATUS.X1_OVERFLOW` | `dut` | X1 Overflow 状态 |
| `STATUS.Y_UNDERFLOW` | `dut` | Y Underflow 状态 |
| `STATUS.ACCUMULATOR_SATURATION` | `dut` | 内部累加器 Saturation 状态 |
| `STATUS.NEGATIVE_AFTER_OFFSET` | `dut` | Offset 后仍为负状态 |
| `STATUS.FLOAT_TO_Q15_OVERFLOW` | `dut` | Float 转 Q15 Overflow 状态 |
| `DATA.OUTPUT_STREAM` | `dut` | 数据输出端点原始样本序列 |
| `IRQ_RAW.<source>` | `dut` | 指定 Source 的 Raw pending |
| `IRQ_STATUS.<source>` | `dut` | 指定 Source 经 Enable/Mask 后的有效状态 |
| `IRQ_DELIVERY.LATCHED_SOURCE` | `dut` | 目标侧 ISR/Service 独立锁存的投递 Source |
| `DMA_CHANNEL_STATUS.INPUT` | `peer` | 输入 DMA Channel 硬件终态 |
| `DMA_CHANNEL_STATUS.OUTPUT` | `peer` | 输出 DMA Channel 硬件终态 |
| `DMA_TRANSFER_COUNT.INPUT` | `peer` | 输入 DMA 实际搬运数量 |
| `DMA_TRANSFER_COUNT.OUTPUT` | `peer` | 输出 DMA 实际搬运数量 |
| `DMA_DESTINATION_SEQUENCE` | `peer` | DMA 目的内存真实输出序列 |
| `TARGET_CYCLE_COUNT` | `observer` | 目标侧稳定周期 Observer 原始计数 |

### 0.3 稳定 Measurement 边界

以下事实属于 Measurement，不得伪装成 DUT Observation：

- `irq_delivery_count`：ISR/Service 软件累计计数，用于证明 bounded window 内“有/无新增投递”；`IRQ_DELIVERY.LATCHED_SOURCE` 仍是独立 Observation。
- `accepted_count / read_count / parameter_id / chunk_index / element_count`：协议或 Case 编排事实。
- `expected_* / golden_* / first_valid_output_index / output_digest / cycles_per_element`：Oracle、Artifact 摘要或派生测量。

### 0.4 稳定自动化动作

后续 PC Driver、Firmware Service 与 Common Wrap 只实现下表中的芯片中立原子能力，但本文不提前冻结数值 Service/Command ID。Case Fixture 只建立跨 Case 隔离基线；Feature 配置、激励、观测和断言仍由 Case 显式编排。

| 稳定动作 | 请求语义 | 约束 |
|---|---|---|
| `capabilities_get` | 获取格式、Filter、布局/水位、输出策略、IRQ、DMA、alignment 等目标事实 | 只发布目标机器事实。 |
| `state_reset` | 清除 FMAC Service 保存的配置标记、IRQ绑定和IRQ观测状态 | 等待一次响应，超时或目标失败时抛出异常；只处理本 Service 自有软件状态，不得调用CRG、Resource或其他IP Wrap，也不得替代FMAC硬件复位。 |
| `configure` | 提交布局、水位、数值和输出策略 | 准静态配置只允许在目标规定的 idle 状态修改；Case 只覆盖需要测试的维度，其余维度必须由PC显式提交，Service/Wrap不得补默认值。 |
| `config_snapshot_get` | 读取当前布局、水位、数值和输出策略快照 | 返回Case需要核对的稳定配置字段；底层硬件读取只允许由对应Chip Driver或Driver Test Extension提供。 |
| `x1_preload` | 向 X1 装载指定数量样本 | 用于独立验证 X1 Load、Spare/Full 和建立受控历史。 |
| `coefficients_load` | 向 X2 装载前馈段和可选反馈段 | IIR 顺序固定为前馈段后反馈段。 |
| `y_preload` | 向 Y 装载指定数量样本/状态 | 用于独立验证 Y Load/Unread/Empty、Float 转换或建立 IIR 反馈初态。 |
| `data_write_one_unchecked` | 对数据写端点执行一次不经软件 Full 保护的写 | 仅用于自然 X1 Overflow 刺激；目标适配必须明确安全实现。 |
| `data_read_one_unchecked` | 对数据读端点执行一次不经软件 Empty 保护的读 | 仅用于自然 Y Underflow 刺激；目标适配必须明确安全实现。 |
| `start` / `stop` | 开始/停止运行类功能 | `stop` 必须有界终止并使 `STATUS.ACTIVE=0`。 |
| `clear` | 清动态指针/状态 | `clear` 不替代 `stop`，也不代表准静态配置恢复；Case 重入必须重新显式提交完整配置，不能依赖上次事务遗留值。 |
| `stream_write` / `stream_read` | 有界流式输入/输出 | 长流由 PC 重复编排，单动作禁止无限阻塞。 |
| `process` | 有界 one-shot 数据事务 | Golden 必须由 PC 独立计算。 |
| `status_get` | 返回稳定状态字段 | DUT 侧不生成 Case PASS/FAIL。 |
| `irq_enable/disable/mask/unmask/force/clear` | Source mask | Force 不替代自然事件；Disable 与 Mask 的投递抑制必须可验证。 |
| `irq_snapshot_get` | Raw/Status + Delivery latch | `irq_delivery_count` 单独作为 Measurement 记录。 |
| `dma_request_set` | input/output gate | 只控制本 IP request；修改时机由目标适配规则约束。 |
| `timed_process` | 与 process 等价的功能事务 | 仅在目标侧稳定 Observer 存在时用于性能表征。 |

### 0.5 Oracle、Timeout、Known Baseline 与 Cleanup

- Case Isolation：每个Case进入时显式执行`CRG reset(FMAC) -> FMAC state_reset -> Resource reset`。三步分别恢复FMAC硬件、FMAC Service自有状态和整个Resource Pool；任一步失败都必须在Feature配置前终止当前Case。
- Known Baseline：硬件和软件隔离完成后，Case仍必须显式提交当前Feature需要的完整FMAC配置，不得依赖复位值或上一Case配置。完整配置至少明确Q15输入/输出、Float转换关闭、RAW、Offset=0、Shift=NONE、内部Clip=WRAP和最终策略=SATURATE；Case覆盖的字段由当前参数替换。
- FIR：PC 使用独立数学模型；一般中间量化未闭合前只使用量化不敏感向量；`fir_first_valid_output_index` 未闭合时不得移动数组索引迎合 DUT。
- IIR：反馈符号、Y 状态排列、中间量化和 first-valid index 全部闭合后才允许 bit-exact Oracle。
- Float：正常转换优先使用 Q15 可精确表示值；Float 输入/输出基础 Case 使用 Y preload/read 直接验证转换，不依赖 FIR 对齐。
- Output：RAW、SAT12、SAT16、Offset、Shift、Clip 与 Final Policy 使用独立整数模型逐项隔离；需要 FIR 激励时优先使用对齐不敏感的恒定历史/恒定输入向量。
- IRQ：Enable、Mask、Clear、Raw、Status、Force、真实 Delivery 与 `irq_delivery_count` Measurement 是不同事实；自然 Source 必须由真实硬件条件产生。
- DMA：Request Gate 不是成功证据；必须同时观察 Peer DMA 终态、传输数量与目的数据。
- Timeout：PC 拥有 Case 顶层 deadline；Firmware/Driver 单动作有界；禁止固定 sleep 作为唯一完成判据。
- Cleanup：Case内部只保留当前Feature判定所需的Stop/Clear/IRQ或DMA收口动作；跨Case隔离不依赖逐资源逆序恢复，统一由下一Case入口的三步复位保证。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| FMAC_F_001 | FMAC X1区域布局 | X1 输入区域的逻辑起始位置和容量可配置。 | `FMAC_P1_001` |
| FMAC_F_002 | FMAC X1 Full Watermark | X1 Full 水位可配置。 | `FMAC_P1_002` |
| FMAC_F_003 | FMAC X1 Spare Count | 可读取 X1 剩余可写元素数量。 | `FMAC_P1_002` |
| FMAC_F_004 | FMAC X1 Full状态 | X1 到达当前 Full 水位条件后可观察 Full 状态。 | `FMAC_P1_002` |
| FMAC_F_005 | FMAC X2区域布局 | X2 系数区域的逻辑起始位置和容量可配置。 | `FMAC_P1_001` |
| FMAC_F_006 | FMAC Y区域布局 | Y 输出/反馈区域的逻辑起始位置和容量可配置。 | `FMAC_P1_001` |
| FMAC_F_007 | FMAC Y Empty Watermark | Y Empty 水位可配置。 | `FMAC_P1_003` |
| FMAC_F_008 | FMAC Y Unread Count | 可读取 Y 未读元素数量。 | `FMAC_P1_003` |
| FMAC_F_009 | FMAC Y Empty状态 | Y 到达当前 Empty 水位条件后可观察 Empty 状态。 | `FMAC_P1_003` |
| FMAC_F_010 | FMAC X1数据装载 | 初始化功能可向 X1 装载确定数量的输入/历史样本。 | `FMAC_P1_002` |
| FMAC_F_011 | FMAC X2系数装载 | 初始化功能可向 X2 装载 FIR 前馈段或 IIR 前馈/反馈系数段。 | `FMAC_P0_001`, `FMAC_P0_002` |
| FMAC_F_012 | FMAC Y数据装载 | 初始化功能可向 Y 装载确定数量的数据/反馈初态。 | `FMAC_P0_002` |
| FMAC_F_013 | FMAC Q15 FIR卷积 | signed Q15 输入与前馈系数执行 FIR 卷积。 | `FMAC_P0_001`, `FMAC_P2_001`, `FMAC_P3_001`, `FMAC_P3_002`, `FMAC_P3_003` |
| FMAC_F_014 | FMAC Q15 IIR Direct Form 1 | Q15 IIR Direct Form 1 使用独立前馈/反馈抽头数量。 | `FMAC_P0_002` |
| FMAC_F_015 | FMAC Q15数据格式 | 固定点输入、系数、状态和输出使用 signed s(16,15)。 | `FMAC_P0_001`, `FMAC_P0_002` |
| FMAC_F_016 | FMAC 流式连续处理 | 同一滤波会话可跨 Chunk 追加输入、读取输出并保持滤波状态连续。 | `FMAC_P1_004`, `FMAC_P3_001` |
| FMAC_F_017 | FMAC动态状态清除 | Clear 可清动态指针和状态；活动控制由Stop独立负责。 | `FMAC_P0_003` |
| FMAC_F_018 | FMAC Float输入转换 | IEEE754 Float32 输入可转换到内部 Q15 路径。 | `FMAC_P1_005` |
| FMAC_F_019 | FMAC Float输出转换 | 内部 Q15 结果可转换为 IEEE754 Float32 输出。 | `FMAC_P1_005` |
| FMAC_F_020 | FMAC Float转Q15钳位 | Float 超出 Q15 可表示范围时输出钳位到对应边界。 | `FMAC_P1_006` |
| FMAC_F_021 | FMAC Float转Q15 Overflow状态 | Float 转 Q15 发生越界后可观察并清除 Overflow 状态。 | `FMAC_P1_006` |
| FMAC_F_022 | FMAC 内部累加器Clip | 内部累加越界支持 Wrap 与 Clip/Saturate 策略。 | `FMAC_P1_007` |
| FMAC_F_023 | FMAC 最终输出Saturate/Wrap | 最终 Q15 输出越界支持 Saturate 与 Wrap。 | `FMAC_P1_008` |
| FMAC_F_024 | FMAC 输出数据模式 | 输出支持 RAW、12-bit Saturate、16-bit Saturate 三种模式。 | `FMAC_P1_009` |
| FMAC_F_025 | FMAC 输出Offset | 非 RAW 输出后处理可加入可配置 Offset。 | `FMAC_P1_010` |
| FMAC_F_026 | FMAC Offset后负值状态 | Offset 后仍为负时产生可观察且可清的状态。 | `FMAC_P1_010` |
| FMAC_F_027 | FMAC 输出Shift | 非 RAW 输出后处理支持 LEFT8..LEFT1、NONE、RIGHT1..RIGHT7。 | `FMAC_P1_011` |
| FMAC_F_028 | FMAC X1 Overflow状态 | X1 无可写空间后继续写数据可产生 Overflow 状态。 | `FMAC_P1_002`, `FMAC_P1_014` |
| FMAC_F_029 | FMAC Y Underflow状态 | Y 无未读数据后继续读数据可产生 Underflow 状态。 | `FMAC_P1_003`, `FMAC_P1_014` |
| FMAC_F_030 | FMAC 累加器Saturation状态 | 内部累加越界可产生独立 Saturation 状态。 | `FMAC_P1_007`, `FMAC_P1_014` |
| FMAC_F_031 | FMAC DMA输入写请求 | X1 可接收数据时可产生输入方向 DMA request。 | `FMAC_P2_001`, `FMAC_P3_003` |
| FMAC_F_032 | FMAC DMA输出读请求 | Y 存在可读数据时可产生输出方向 DMA request。 | `FMAC_P2_001`, `FMAC_P3_003` |
| FMAC_F_033 | FMAC X1写请求IRQ | X1 写请求条件可形成独立 IRQ Source。 | `FMAC_P1_013` |
| FMAC_F_034 | FMAC Y读请求IRQ | Y 读请求条件可形成独立 IRQ Source。 | `FMAC_P1_013` |
| FMAC_F_035 | FMAC Saturation IRQ | 累加器 Saturation 可形成独立 IRQ Source。 | `FMAC_P1_014` |
| FMAC_F_036 | FMAC X1 Overflow IRQ | X1 Overflow 可形成独立 IRQ Source。 | `FMAC_P1_014` |
| FMAC_F_037 | FMAC Y Underflow IRQ | Y Underflow 可形成独立 IRQ Source。 | `FMAC_P1_014` |
| FMAC_F_038 | FMAC P Error IRQ | P 参数错误可形成独立 IRQ Source。 | `FMAC_P1_015` |
| FMAC_F_039 | FMAC PQ Error IRQ | P/Q 组合参数错误可形成独立 IRQ Source。 | `FMAC_P1_015` |
| FMAC_F_040 | FMAC Q Error IRQ | Q 参数错误可形成独立 IRQ Source。 | `FMAC_P1_015` |
| FMAC_F_041 | FMAC X1 Load Error IRQ | X1内部装载错误可形成独立IRQ Source；普通软件无法构造该内部故障，后续不建立Formal Case。 | — |
| FMAC_F_042 | FMAC X2 Load Error IRQ | X2内部装载错误可形成独立IRQ Source；普通软件无法构造该内部故障，后续不建立Formal Case。 | — |
| FMAC_F_043 | FMAC Y Store Error IRQ | Y内部存储错误可形成独立IRQ Source；普通软件无法构造该内部故障，后续不建立Formal Case。 | — |
| FMAC_F_044 | FMAC IRQ Enable/Disable | IRQ Source 可独立 Enable/Disable。 | `FMAC_P1_012` |
| FMAC_F_045 | FMAC IRQ Mask/Unmask | IRQ Source 可独立 Mask/Unmask。 | `FMAC_P1_012` |
| FMAC_F_046 | FMAC IRQ Clear | 指定 IRQ Source 可被软件清除。 | `FMAC_P1_012` |
| FMAC_F_047 | FMAC IRQ RAW状态 | 可读取不受 Mask 吞掉的 IRQ Raw pending。 | `FMAC_P1_012` |
| FMAC_F_048 | FMAC IRQ STATUS状态 | 可读取 Enable/Mask 后的有效 IRQ Status。 | `FMAC_P1_012` |
| FMAC_F_049 | FMAC IRQ Force | 软件可按 Source 强制产生测试 IRQ 事件。 | `FMAC_P1_012` |
| FMAC_F_050 | FMAC IRQ投递 | 有效且未屏蔽的 FMAC IRQ 可到达目标中断输入；真实执行以目标侧 ISR 锁存 Source 证明。 | `FMAC_P1_012`, `FMAC_P1_013`, `FMAC_P1_014`, `FMAC_P1_015` |
| FMAC_F_051 | FMAC 功能Enable/Disable | 运行类功能可软件 Enable 启动并 Disable 停止；初始化类功能按目标硬件定义自动结束。 | `FMAC_P0_004` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---:|---|---|---|---:|---|
| FMAC_P0_001 | P0 | FMAC Q15 FIR稳态卷积测试 | X2系数装载、Q15 FIR、Q15格式 | 量化精确的正负稳态尾段逐元素等于独立Golden | R0 | SPEC |
| FMAC_P0_002 | P0 | FMAC Q15 IIR独立参考测试 | X2系数装载、Y装载、Q15 IIR、Q15格式 | 历史Q15 IIR向量逐元素等于独立Direct Form 1 Oracle | R0 | SPEC |
| FMAC_P0_003 | P0 | FMAC Clear与配置保持测试 | Clear | Clear 前后Y Underflow动态状态变化 + 准静态配置保持 | R0 | SPEC |
| FMAC_P0_004 | P0 | FMAC Enable/Disable与活动状态测试 | 功能Enable/Disable | Enable 后 ACTIVE=1；Disable 后 ACTIVE=0；初始化动作自动结束 | R0 | SPEC |
| FMAC_P1_001 | P1 | FMAC X1/X2/Y区域布局矩阵测试 | 三区域布局 | 六个配置读回 + X1/Y容量行为 | R0 | SPEC |
| FMAC_P1_002 | P1 | FMAC X1水位、容量状态与Overflow测试 | X1 Watermark/Spare/Full/Load/Overflow | Runtime容量布局 + 剩余空间跨Watermark + 容量外直写 | R0 | SPEC |
| FMAC_P1_003 | P1 | FMAC Y水位、容量状态与Underflow测试 | Y Watermark/Unread/Empty/Underflow | 单抽头FIR产生真实Y输出 + 耗尽后unchecked读 | R0 | SPEC |
| FMAC_P1_004 | P1 | FMAC 流式Chunk连续性测试 | 流式连续处理 | 同一输入的Chunk输出与one-shot参考序列完全一致 | R0 | SPEC |
| FMAC_P1_005 | P1 | FMAC Float输入输出正常转换测试 | Float输入/输出转换 | 0.5单抽头FIR双向转换独立Oracle，Overflow=0 | R0 | SPEC |
| FMAC_P1_006 | P1 | FMAC Float转Q15钳位与Overflow状态测试 | Float钳位、Overflow状态 | 0.5单抽头FIR正负边界 + 状态前后值 | R0 | SPEC |
| FMAC_P1_007 | P1 | FMAC 内部Clip与Saturation状态测试 | 内部Clip、Saturation状态 | 同一确定性越界刺激下Wrap/Clip输出分离 + Saturation状态与Clear恢复 | R0 | SPEC |
| FMAC_P1_008 | P1 | FMAC 最终输出Saturate/Wrap测试 | 最终Saturate/Wrap | 两种最终越界策略分别匹配独立 Expected | R0 | SPEC |
| FMAC_P1_009 | P1 | FMAC 输出数据模式矩阵测试 | 输出数据模式 | RAW/SAT12/SAT16 三套独立 Expected | R0 | SPEC |
| FMAC_P1_010 | P1 | FMAC 输出Offset与负值状态测试 | Offset、负值状态 | SAT16+NONE 下数值 Expected + 清除前后状态 | R0 | SPEC |
| FMAC_P1_011 | P1 | FMAC 输出Shift全合法编码测试 | 输出Shift | SAT16+offset0 下 16/16 Shift 逐元素匹配 Expected | R0 | SPEC |
| FMAC_P1_012 | P1 | FMAC 十一源IRQ控制、Force与投递矩阵测试 | IRQ控制/Raw/Status/Force/Delivery | 11 源逐源状态转换 + ISR锁存 + delivery-count Measurement | R0 | SPEC |
| FMAC_P1_013 | P1 | FMAC 自然请求IRQ测试 | X1写请求IRQ、Y读请求IRQ、IRQ投递 | 两类受控 Buffer 条件自然产生正确 Source | R0 | SPEC |
| FMAC_P1_014 | P1 | FMAC 自然运算与Buffer边界IRQ测试 | Saturation/X1 Overflow/Y Underflow IRQ、IRQ投递 | 对应错误状态先成立，再有正确 IRQ Source/Delivery | R0 | SPEC |
| FMAC_P1_015 | P1 | FMAC P/PQ/Q参数错误自然IRQ测试 | P/PQ/Q Error IRQ、IRQ投递 | P=0、P+Q越X2容量、Q越Y容量分别触发目标Source并完成合法恢复 | R0 | SPEC |
| FMAC_P2_001 | P2 | FMAC 双向DMA门控与FIR端到端测试 | DMA输入/输出请求、Q15 FIR | 芯片Profile解析FMAC双向DMA映射，16-bit DMA终态/数量/Golden闭合 | R2 | SPEC |
| FMAC_P3_001 | P3 | FMAC 确定性长流FIR稳定性测试 | Q15 FIR、流式连续处理 | 固定常值长流逐Chunk Golden + 无丢重样 + 跨轮一致性 | R0 | SPEC |
| FMAC_P3_002 | P3 | FMAC CPU路径周期性能表征 | Q15 FIR | FMAC目标侧原子计时 + Golden正确样本保留原始周期 | R0 | SPEC |
| FMAC_P3_003 | P3 | FMAC DMA路径周期性能表征 | DMA输入/输出请求、Q15 FIR | DMA目标侧周期接口 + 双向DMA终态/数量/Golden正确样本 | R2 | SPEC |

## 3. Machine-readable Case Contract

> 当前23个Case全部使用`ET_CASE_SPEC`，且均已完成对应Driver/Wrap/Service/PC Driver/Case与Execution Mapping实现。源码实现不等于HIL PASS，正式测试结果只允许记录在芯片事实文档。

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P0_001
case_name: FMAC Q15 FIR稳态卷积测试
report_feature: |-
  1. FMAC X2系数装载
  2. FMAC Q15 FIR卷积
  3. FMAC Q15数据格式
p_level: P0
feature_refs: [FMAC_F_011, FMAC_F_013, FMAC_F_015]
method:
  inputs:
    - "精确系数：使用四个2的幂Q15系数[0x4000,0x2000,0x1000,0x0800]，系数和为0.9375，避免未知舍入策略影响Expected。"
    - "FIR初始历史：向X1显式预装4个零样本，使四抽头FIR在one-shot事务开始前具备确定的历史状态。"
    - "正负稳态输入：分别连续输入12个0x2000和12个-0x2000样本；每组只比较最后4个稳态输出，避开尚未冻结的首输出对齐而不搜索动态偏移。"
  steps:
    - "能力确认：确认Q15、FIR、X2系数装载和至少4个前馈抽头均由Runtime Capability发布。"
    - "基线建立：显式Stop、Clear、提交完整配置并保持DMA Gate关闭，确认STATUS.ACTIVE=0。"
    - "系数与历史装载：向X2一次装载4个公开的2的幂Q15前馈系数，并向X1预装4个零样本建立确定初态。"
    - "正负事务：每个参数实例分别执行一次12样本one-shot FIR，并读取完整DATA.OUTPUT_STREAM。"
    - "稳态截取：固定选择每组最后4个输出作为稳态区间，不搜索、不拟合、也不声明首输出对齐。"
    - "独立比较：正输入稳态尾段逐项比较0x1E00，负输入稳态尾段逐项比较-0x1E00，并核对收发数量。"
    - "显式停止：每个实例执行Stop并确认STATUS.ACTIVE=0，保存完整输出及稳态尾段。"
  observations:
    - "FIR正向稳态输出：读取DATA.OUTPUT_STREAM最后4项，期望全部为0x1E00；该尾段证明正Q15输入、X2系数和四抽头MAC得到精确结果。"
    - "FIR负向稳态输出：读取DATA.OUTPUT_STREAM最后4项，期望全部为-0x1E00；该尾段证明signed Q15负输入沿同一数据路径正确运算。"
    - "FIR装载与传输数量：读取X1预装数量和PROCESS返回的accepted_count/read_count，期望分别为4、12、12；证明初态与事务均完整。"
    - "FIR停止状态：Stop后读取STATUS.ACTIVE，期望为0；证明每个参数实例均有界结束。"
  pass_criteria:
    - "正负数值正确性：两个稳态尾段分别4/4逐元素等于对应独立Golden，任何单点差异均FAIL。"
    - "事务完整性：每个参数实例X1预装数量=4、accepted_count=12且read_count=12。"
    - "生命周期完整性：每个实例Stop后ACTIVE=0，不存在永久Busy或残留活动状态。"
timeout: "单参数实例使用统一有界deadline；状态轮询不得用固定sleep替代。"
cleanup: ["STOP停止当前功能", "关闭本Case启用的IRQ/DMA门控", "CLEAR清动态状态并释放Case资源"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Q15输入与系数", "正负稳态Golden", "完整DATA.OUTPUT_STREAM", "PROCESS数量", "Stop后STATUS.ACTIVE"]
failure_observations:
  - key: actual_output
    label: "FIR硬件输出"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.fir_output
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P0_002
case_name: FMAC Q15 IIR独立参考测试
report_feature: |-
  1. FMAC X2系数装载
  2. FMAC Y数据装载
  3. FMAC Q15 IIR Direct Form 1
  4. FMAC Q15数据格式
p_level: P0
feature_refs: [FMAC_F_011, FMAC_F_012, FMAC_F_014, FMAC_F_015]
method:
  inputs:
    - "IIR确定向量：使用平台固化的7项Ladder前馈系数、6阶Reflection反馈系数、32项输入和6项X1/Y零初态；向量来源与目标适配证据记录在芯片事实文档。"
    - "独立IIR Oracle：PC按Q15 Direct Form 1计算前馈输入项与正反馈输出项，统一右移15位并饱和，不调用DUT Driver计算Expected。"
  steps:
    - "空闲准备：显式Stop、Clear并提交X1=32、X2=16、Y=32的互不重叠布局。"
    - "系数装载：按公共语义向X2装载7项Ladder前馈系数和6项Reflection反馈系数。"
    - "反馈初态：向Y和X1分别装载6项Q15零初态，与独立Oracle的初始状态一致。"
    - "事务执行：以前馈抽头数7、反馈抽头数6启动IIR，提交32项固定输入并读取32项输出。"
    - "独立比较：PC运行Q15 Direct Form 1 Oracle，32项硬件输出逐元素严格等于Golden，不搜索偏移、不使用Tolerance。"
    - "显式停止：Stop后确认STATUS.ACTIVE=0，保存输入、系数、初态、Golden和Actual。"
  observations:
    - "IIR硬件输出：读取32项DATA.OUTPUT_STREAM，期望逐元素等于独立Q15 Direct Form 1 Golden；证明X2两段系数和X1/Y初态共同参与IIR数据路径。"
    - "IIR停止状态：Disable后读取STATUS.ACTIVE，期望为0；证明IIR由显式停止动作有界终止。"
  pass_criteria:
    - "IIR数值正确性：32项输出逐元素等于bit-exact Golden。"
    - "事务完整性：accepted_count和read_count均等于32。"
timeout: "每个IIR实例使用统一有界deadline；不得用固定sleep替代状态轮询。"
cleanup: ["STOP停止当前功能", "关闭本Case启用的IRQ/DMA门控", "CLEAR清动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["前馈/反馈抽头数与两段系数/初态", "Q15 Direct Form 1 Oracle", "32项Golden/Actual", "PROCESS数量", "STATUS.ACTIVE终态"]
failure_observations:
  - key: actual_output
    label: "IIR硬件输出"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.iir_output
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P0_003
case_name: FMAC Clear与配置保持测试
report_feature: |-
  1. FMAC动态状态清除
p_level: P0
feature_refs: [FMAC_F_017]
method:
  inputs:
    - "动态现场：配置单抽头FIR并产生一个真实Y输出，在活动会话中执行大于Y容量的有界超量读取，使STATUS.Y_UNDERFLOW由0变为1。"
    - "配置现场：保存完整准静态配置，用于验证Clear不会改写区域布局和输出配置。"
  steps:
    - "空闲基线：PC按0.5显式建立Known Baseline，提交X1/X2/Y容量均为4的完整配置。"
    - "现场建立：装载单抽头系数和零历史，启动FIR，写入一个样本产生真实Y输出。"
    - "异常刺激：在活动会话中执行Y容量加1次Unchecked Read，并确认STATUS.Y_UNDERFLOW=1。"
    - "显式停止：执行Stop并确认STATUS.ACTIVE=0；Clear不承担活动控制职责。"
    - "Clear执行：执行公共CLEAR动作并在统一deadline内等待动作完成。"
    - "动态终态：读取STATUS.Y_UNDERFLOW并确认恢复为0。"
    - "活动终态：读取Stop后的STATUS.ACTIVE并确认变为0。"
    - "配置保持：读取完整配置快照并与Clear前提交值逐字段比较。"
  observations:
    - "Clear前动态状态：执行Clear前读取STATUS.Y_UNDERFLOW，期望为1；证明动态错误状态真实建立。"
    - "Clear后动态状态：执行Clear后读取STATUS.Y_UNDERFLOW，期望为0；证明动态错误状态被清理。"
    - "Stop后活动状态：执行Stop后读取STATUS.ACTIVE，期望为0；证明活动控制由Stop独立终止。"
    - "Clear后配置快照：读取全部准静态配置字段，期望与Clear前提交值一致。"
  pass_criteria:
    - "清理真实性：Clear前STATUS.Y_UNDERFLOW=1，Clear后恢复为0。"
    - "活动状态正确性：Stop后STATUS.ACTIVE=0。"
    - "配置保持正确性：Clear后完整配置快照与提交配置一致。"
timeout: "FIR启动、流写、Unchecked Read、Stop、Clear和状态读取均受Case顶层有界deadline约束。"
cleanup: ["STOP停止当前功能", "CLEAR恢复空闲状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["FIR写入数量", "Clear前后Y Underflow", "Stop后ACTIVE", "完整配置快照"]
failure_observations:
  - key: underflow_after_clear
    label: "Clear后Y Underflow状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.clear_state
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P0_004
case_name: FMAC Enable/Disable与活动状态测试
report_feature: |-
  1. FMAC 功能Enable/Disable
p_level: P0
feature_refs: [FMAC_F_051]
method:
  inputs:
    - "运行刺激：使用Capability给出的最小合法X1/X2/Y布局，选择Q15 FIR、P=1并装载单个前馈系数0x4000；启动前不向X1写入数据，使FIR稳定等待输入。"
    - "初始化刺激：使用同一次coefficients_load装载上述单个前馈系数；该X2初始化动作完成后必须由硬件自动清除ACTIVE。"
  steps:
    - "空闲基线：PC按0.5显式建立Known Baseline，并读取STATUS.ACTIVE确认初始值为0。"
    - "最小配置：提交最小合法三区域布局、Q15 FIR和P=1配置，再用config_snapshot_get确认关键配置读回。"
    - "初始化终态：执行coefficients_load装载一个0x4000前馈系数，在有界窗口内确认动作完成且STATUS.ACTIVE自动回到0。"
    - "运行Enable：不向X1提交数据，执行start启动P=1 FIR并通过有界轮询等待STATUS.ACTIVE变为1。"
    - "活动保持：FIR仍等待X1输入且尚未stop时再次读取STATUS.ACTIVE，期望保持1。"
    - "运行Disable：执行stop并在deadline内等待STATUS.ACTIVE变为0。"
    - "重新启动与Clear：不做系统复位，再次start确认ACTIVE=1，随后执行clear并确认ACTIVE回到0。"
  observations:
    - "初始活动状态：空闲基线读取STATUS.ACTIVE，期望为0；证明测试从已知idle状态开始。"
    - "Enable活动状态：Enable运行类功能后读取STATUS.ACTIVE，期望为1；证明Enable动作真实启动运行功能。"
    - "保持活动状态：运行功能尚未Disable时再次读取STATUS.ACTIVE，期望为1；证明活动态不会在等待数据期间无因退出。"
    - "Disable活动状态：Disable运行类功能后读取STATUS.ACTIVE，期望为0；证明软件可停止正在运行的功能。"
    - "初始化活动终态：X2单系数装载动作完成后读取STATUS.ACTIVE，期望为0；证明初始化类功能由硬件自动结束。"
  pass_criteria:
    - "Enable正确性：运行类功能Enable后STATUS.ACTIVE在有界窗口内变为1并保持到显式Disable。"
    - "Disable正确性：显式Disable后STATUS.ACTIVE在有界窗口内变为0且允许再次Enable。"
    - "初始化终态正确性：X2单系数装载动作完成后STATUS.ACTIVE=0。"
timeout: "所有ACTIVE状态转换均使用有界轮询；禁止固定sleep作为唯一判据。"
cleanup: ["STOP停止当前功能", "CLEAR恢复空闲状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["ACTIVE状态序列", "Enable/Disable/Clear动作结果"]
failure_observations:
  - key: actual_active
    label: "实际活动状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.active_state
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_001
case_name: FMAC X1/X2/Y区域布局矩阵测试
report_feature: |-
  1. FMAC X1区域布局
  2. FMAC X2区域布局
  3. FMAC Y区域布局
p_level: P1
feature_refs: [FMAC_F_001, FMAC_F_005, FMAC_F_006]
method:
  inputs:
    - "布局矩阵：由Capability的逻辑地址上限、各区域最小容量和非重叠约束确定性生成layout_min、layout_shifted和layout_end_boundary；三者分别覆盖最小连续布局、整体右移一个逻辑单元和Y结束位置贴合地址上限。"
    - "容量刺激：每组布局令probe_count=min(2, X1容量, Y容量)且要求probe_count大于0，向X1和Y分别装载probe_count个递增Q15样本。"
  steps:
    - "资格确认：从Capability取得合法逻辑范围和组合约束，仅选择已声明合法的布局实例。"
    - "单实例准备：PC按0.5显式建立Known Baseline并确认STATUS.ACTIVE=0。"
    - "布局配置：提交当前X1/X2/Y起始位置和容量。"
    - "配置读取：调用config_snapshot_get，依次取得六个CONFIG端点并保存原始值。"
    - "X1容量行为：向X1装载固定数量样本并读取STATUS.X1_SPARE_COUNT。"
    - "Y容量行为：向Y装载固定数量样本，读取STATUS.Y_UNREAD_COUNT并读回已知Y序列。"
    - "矩阵汇总：六项配置和两类容量行为均符合当前布局参数后再进入下一实例。"
  observations:
    - "结构化证据：FMAC Case本地证据入口将配置和状态快照按字段名和值转换为可移植映射，禁止把PC语言对象直接写入Canonical Result。"
    - "X1起始位置：读取CONFIG.X1_START，期望等于当前X1起始参数；证明X1逻辑起始配置进入目标硬件。"
    - "X1容量：读取CONFIG.X1_SIZE，期望等于当前X1容量参数；证明X1容量配置进入目标硬件。"
    - "X2起始位置：读取CONFIG.X2_START，期望等于当前X2起始参数；证明X2逻辑起始配置进入目标硬件。"
    - "X2容量：读取CONFIG.X2_SIZE，期望等于当前X2容量参数；证明X2容量配置进入目标硬件。"
    - "Y起始位置：读取CONFIG.Y_START，期望等于当前Y起始参数；证明Y逻辑起始配置进入目标硬件。"
    - "Y容量：读取CONFIG.Y_SIZE，期望等于当前Y容量参数；证明Y容量配置进入目标硬件。"
    - "X1容量事实：读取STATUS.X1_SPARE_COUNT，期望等于当前X1容量减已装载数量；证明配置容量真实约束X1占用模型。"
    - "Y容量事实：读取STATUS.Y_UNREAD_COUNT，期望等于当前Y已装载未读数量；证明配置容量支持预期Y数据现场。"
    - "Y数据事实：读取DATA.OUTPUT_STREAM，期望逐元素等于当前Y装载序列；证明当前Y布局下数据可被正确存取。"
  pass_criteria:
    - "配置读回正确性：六个CONFIG端点均等于当前合法布局参数。"
    - "容量行为正确性：X1 Spare和Y Unread均符合当前布局下的状态模型。"
    - "数据顺序正确性：Y装载/读取序列保持元素数量和顺序。"
timeout: "每个布局实例使用独立有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清动态状态", "释放布局Case资源"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["布局矩阵", "六项CONFIG读回", "Spare/Unread状态", "Y读回数据"]
failure_observations:
  - key: actual_x1_size
    label: "实际X1容量读回"
    source: dut
    role: actual
    format: decimal
    semantic_ref: fmac.feature.buffer_layout
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_002
case_name: FMAC X1水位容量状态与Overflow测试
report_feature: |-
  1. FMAC X1 Full Watermark
  2. FMAC X1 Spare Count
  3. FMAC X1 Full状态
  4. FMAC X1数据装载
  5. FMAC X1 Overflow状态
p_level: P1
feature_refs: [FMAC_F_002, FMAC_F_003, FMAC_F_004, FMAC_F_010, FMAC_F_028]
method:
  inputs:
    - "Watermark矩阵：遍历Capability发布的X1 Full Watermark，X1容量由逻辑地址空间与单次最大传输数量共同确定。"
    - "Overflow刺激：先按容量完整装载X1，再启动一项LOAD_X1并直接写入，使该项在X1无可写空间时形成自然Overflow。"
  steps:
    - "能力确认：读取X1容量、Watermark支持集合和目标状态可见延迟规则。"
    - "单实例准备：根据Runtime Capability建立X2/X1/Y连续布局，X2和Y保留最小区域，其余安全空间分配给X1。"
    - "容量计数：装载X2系数和半容量X1，启动单抽头FIR，核对启动消费1项X1、产生1项Y后的Spare Count。"
    - "水位基线：CLEAR后重装X2，向X1预装“容量-Watermark+1”项以补偿FIR启动消费，启动单抽头FIR后确认Spare等于Watermark且Full=0。"
    - "水位跨越：FIR运行态直写1项并在有界窗口内轮询，确认Spare减少1且Full=1。"
    - "自然Overflow：CLEAR后重装X2并按容量装满X1，启动单抽头FIR；第1次直写补回启动消费的空位，第2次直写在无空闲空间时触发STATUS.X1_OVERFLOW。"
    - "Clear恢复：执行CLEAR并再次读取Overflow，确认错误状态归零。"
  observations:
    - "X1空闲数量：读取STATUS.X1_SPARE_COUNT，期望等于容量减已成功装载数量；证明X1装载动作与容量计数一致。"
    - "X1 Full状态：读取STATUS.X1_FULL，期望在当前Watermark边界满足后于目标允许窗口内有效；证明Full Watermark真实参与流控状态生成。"
    - "X1 Overflow基线：执行unchecked写前读取STATUS.X1_OVERFLOW，期望为0；证明错误事件尚未发生。"
    - "X1 Overflow触发：无空间unchecked写后读取STATUS.X1_OVERFLOW，期望为1；证明Overflow由真实无空间写入条件产生。"
    - "X1 Overflow清除：执行CLEAR后读取STATUS.X1_OVERFLOW，期望为0；证明错误状态能够按定义清理。"
  pass_criteria:
    - "容量模型正确性：装载半容量X1后，Spare Count等于容量减实际写入数量。"
    - "水位状态正确性：Full在目标允许的可见窗口内匹配当前Watermark边界。"
    - "Overflow因果正确性：基线为0，无空间unchecked写后为1，Clear后恢复为0。"
timeout: "状态可见性使用目标适配定义的有界轮询，不把芯片固定cycle写进公共Case。"
cleanup: ["STOP停止当前功能", "CLEAR清Overflow与X1动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Watermark参数", "Spare序列", "Full序列", "Overflow前后值"]
failure_observations:
  - key: actual_overflow
    label: "实际X1 Overflow状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.x1_overflow
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_003
case_name: FMAC Y水位容量状态与Underflow测试
report_feature: |-
  1. FMAC Y Empty Watermark
  2. FMAC Y Unread Count
  3. FMAC Y Empty状态
  4. FMAC Y Underflow状态
p_level: P1
feature_refs: [FMAC_F_007, FMAC_F_008, FMAC_F_009, FMAC_F_029]
method:
  inputs:
    - "Watermark矩阵：遍历Capability发布的Y Empty Watermark，Y容量固定为4。"
    - "输出刺激：装载0.5单抽头系数和零X1历史，写入4项Q15输入但暂不读取，使FIR产生4项真实Y输出。"
    - "Underflow刺激：按STATUS.Y_UNREAD_COUNT有界读取至0，再继续有界空读直到硬件报告Underflow。"
  steps:
    - "能力确认：读取Y容量和Watermark支持集合并建立Unread/Empty状态模型。"
    - "单实例准备：PC按0.5显式建立Known Baseline，并在完整配置中覆盖当前Y容量和Watermark。"
    - "FIR准备：装载单抽头系数与零历史，启动FIR后写入4项输入。"
    - "输出建立：暂不读取输出，确认STATUS.Y_UNREAD_COUNT=4。"
    - "完整读取：按Unread状态逐级读取至3、2、1、0并记录Empty；不假设FIFO读数据与状态同拍可见。"
    - "耗尽确认：读取至STATUS.Y_UNREAD_COUNT=0并确认STATUS.Y_EMPTY满足当前Watermark定义。"
    - "自然Underflow：Unread为0后有界执行unchecked读，直到STATUS.Y_UNDERFLOW置位。"
    - "Clear恢复：执行CLEAR后确认Underflow归零。"
  observations:
    - "Y未读数量：FIR写入完成后读取STATUS.Y_UNREAD_COUNT，期望为4；完整读取后期望为0。"
    - "Y Empty状态：读取STATUS.Y_EMPTY，期望符合当前Watermark边界；证明Empty Watermark真实参与Y流控状态生成。"
    - "Y读取现场：保存为跨越Unread边界执行的原始读取次数和状态序列；本Case只验证Y容量状态，不承担FIR数值Oracle。"
    - "Y Underflow基线：执行unchecked读前读取STATUS.Y_UNDERFLOW，期望为0；证明错误事件尚未发生。"
    - "Y Underflow触发：Unread=0后继续有界unchecked读，期望STATUS.Y_UNDERFLOW最终为1；证明Underflow由真实空读条件产生。"
    - "Y Underflow清除：执行CLEAR后读取STATUS.Y_UNDERFLOW，期望为0；证明错误状态能够按定义清理。"
  pass_criteria:
    - "计数正确性：FIR输入和输出数量均为4，Unread Count从4降为0。"
    - "水位状态正确性：Empty符合当前Watermark定义。"
    - "Underflow因果正确性：基线为0，空后unchecked读变为1，Clear后回到0。"
timeout: "每个装载、读取和状态动作有界；禁止固定sleep作为唯一判据。"
cleanup: ["STOP停止当前功能", "CLEAR清Underflow与Y动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Watermark参数", "FIR输入/输出数量", "Unread序列", "Empty序列", "Underflow前后值"]
failure_observations:
  - key: actual_underflow
    label: "实际Y Underflow状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.y_underflow
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_004
case_name: FMAC 流式Chunk连续性测试
report_feature: |-
  1. FMAC 流式连续处理
p_level: P1
feature_refs: [FMAC_F_016]
method:
  inputs:
    - "共同输入：使用固定非重复Q15序列和与P0 FIR一致的2的幂系数；one-shot和Chunk会话使用完全相同的输入、系数与配置。"
    - "Chunk矩阵：覆盖[1,3,2,6]和[4,4,4]两种固定切分，累计均为12项；非重复输入使丢样、重复或乱序可直接暴露。"
  steps:
    - "能力确认：确认Q15、FIR、Stream和至少4个前馈抽头均由Runtime Capability发布。"
    - "参考建立：在Clean baseline中装载系数和等长零X1历史，对完整12项输入执行one-shot FIR并保存原始输出序列和收发数量。"
    - "流式准备：Stop/Clear后重新提交同一完整配置、相同系数和等长零X1历史，Start同一FIR并确认STATUS.ACTIVE=1。"
    - "Chunk输入：按当前固定切分逐块调用有界STREAM_WRITE，每块必须完整接受后才进入下一块。"
    - "Chunk输出：每次写入后在统一有界轮询内读取对应数量，按输入顺序拼接原始输出并记录每块实际数量。"
    - "连续性比较：拼接后的12项输出逐元素等于one-shot参考序列，累计写入和读取数量均为12。"
    - "显式结束：Stop后确认STATUS.ACTIVE=0，两种Chunk切分全部满足同一判据后汇总PASS。"
  observations:
    - "One-shot硬件参考：读取一次完整DATA.OUTPUT_STREAM，作为同一硬件配置下不分Chunk的参考序列。"
    - "流式硬件输出：读取各Chunk的DATA.OUTPUT_STREAM，期望拼接后逐元素等于one-shot参考；证明Chunk边界没有改变输出序列。"
    - "Chunk实际数量：记录每块accepted_count/read_count，期望各块等于计划Chunk长度且累计均为12；证明没有丢样或静默截断。"
    - "流式活动状态：会话中读取STATUS.ACTIVE，期望为1；证明同一运行会话跨Chunk保持活动。"
    - "流式停止状态：显式Disable后读取STATUS.ACTIVE，期望为0；证明会话可以有界结束。"
  pass_criteria:
    - "Chunk等价性：两种切分的拼接输出均12/12逐元素等于one-shot参考序列。"
    - "Chunk完整性：每块和累计接受/读取数量均精确匹配计划，无丢样、重复或乱序。"
    - "状态连续性：Chunk边界不导致无因停止或滤波状态重置。"
timeout: "每个Chunk独立有界，同时受Case顶层deadline约束。"
cleanup: ["STOP结束流式会话", "CLEAR清动态状态", "释放Chunk资源"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Chunk边界与实际数量", "one-shot原始输出", "stream拼接原始输出", "ACTIVE前后值"]
failure_observations:
  - key: actual_stream
    label: "实际分块流序列"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.stream_output
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_005
case_name: FMAC Float输入输出正常转换测试
report_feature: |-
  1. FMAC Float输入转换
  2. FMAC Float输出转换
p_level: P1
feature_refs: [FMAC_F_018, FMAC_F_019]
method:
  inputs:
    - "正常Float集合：使用四项恒定0.5输入；Q15集合使用四项恒定0x4000，避免未知tie rounding影响正常路径。"
    - "真实数据路径：使用0.5单抽头系数和零X1历史，Float输入与Float输出分别通过独立FIR写入/读取路径观察。"
  steps:
    - "能力确认：确认Float输入转换、Float输出转换和FIR能力均已发布。"
    - "输入基线：按Q15格式装载0.5系数和零历史，再打开Float输入转换并确认Overflow基线为0。"
    - "Float输入处理：写入四项恒定0.5 Float32输入，以Q15格式读取全部四项FIR输出。"
    - "Float输入对齐：只比较最后两项稳态输出，避开首个有效输出索引尚未冻结的启动区。"
    - "Float输出准备：CLEAR后重新建立相同FIR，关闭Float输入转换并打开Float输出转换。"
    - "Float输出处理：写入四项恒定0x4000 Q15输入，以Float32格式读取全部四项FIR输出。"
    - "双向比较：两个方向均只比较最后两项稳态输出与独立Expected。"
  observations:
    - "Float输入硬件结果：有效Q15输出期望等于Float输入转换值乘0.5；证明转换真实经过FMAC输入和运算路径。"
    - "正常Overflow状态：Float输入子实例读取STATUS.FLOAT_TO_Q15_OVERFLOW，期望为0；证明正常范围转换没有错误产生Overflow。"
    - "Float输出硬件结果：有效Float32输出期望等于Q15输入乘0.5；证明转换真实经过FMAC运算和输出路径。"
  pass_criteria:
    - "Float输入正确性：全部正常Float输入产生正确Q15结果且Overflow=0。"
    - "Float输出正确性：全部Q15输入转换出的Float32结果满足独立Expected。"
    - "参数覆盖完整性：定义的正、负、零和边界内实例全部执行。"
timeout: "每个双向转换子实例使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清动态/Float状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Float参数", "独立转换Expected", "Q15硬件结果", "Float32硬件结果", "Overflow状态"]
failure_observations:
  - key: actual_numeric
    label: "实际Float转换结果"
    source: dut
    role: actual
    format: text
    semantic_ref: fmac.feature.float_conversion
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_006
case_name: FMAC Float转Q15钳位与Overflow状态测试
report_feature: |-
  1. FMAC Float转Q15钳位
  2. FMAC Float转Q15 Overflow状态
p_level: P1
feature_refs: [FMAC_F_020, FMAC_F_021]
method:
  inputs:
    - "边界向量：正超范围+2.0和负超范围-2.0分别形成独立四项恒定输入事务。"
    - "真实数据路径：使用0.5单抽头系数和零X1历史，通过FIR输入路径观察Float钳位和Overflow状态。"
  steps:
    - "能力确认：确认Float->Q15钳位、Overflow状态和FIR能力可用。"
    - "实例基线：每个超范围子实例前装载0.5单抽头系数和零X1历史。"
    - "路径配置：配置RAW输出、Float输入转换开启、Float输出转换关闭。"
    - "越界处理：以Float格式写入四项同值超范围输入，再以Q15格式读取四项FIR结果。"
    - "状态读取：读取STATUS.FLOAT_TO_Q15_OVERFLOW并记录当前输入类别。"
    - "正常输入：每个越界事务后继续输入一个0.25，并读取对应Q15结果，使硬件实时Overflow条件撤销。"
    - "状态清除：正常输入完成后执行Stop和Clear，读取Overflow清除状态。"
  observations:
    - "Overflow基线：越界输入前读取STATUS.FLOAT_TO_Q15_OVERFLOW，期望为0；证明当前子实例没有继承前序Overflow。"
    - "钳位硬件输出：读取最后一项稳态Q15输出，期望等于输入钳位边界再乘0.5的FIR结果。"
    - "Overflow触发状态：越界输入后读取STATUS.FLOAT_TO_Q15_OVERFLOW，期望为1；证明钳位事件同时形成Overflow状态。"
    - "正常输入完成状态：0.25输入的写入数和读取数均为1；证明清除前实时Overflow条件已经撤销。"
    - "Overflow清除状态：正常输入完成并执行清除后，STATUS.FLOAT_TO_Q15_OVERFLOW期望为0。"
  pass_criteria:
    - "双向钳位正确性：正负超范围输入先钳位到Q15边界，再经0.5系数得到对应稳态Expected。"
    - "状态因果正确性：基线为0，越界后为1，正常输入完成后执行Clear回到0。"
    - "恢复输入正确性：正常输入写入和读取均完成1项。"
timeout: "每个边界输入和状态清除动作均使用有界deadline。"
cleanup: ["正常输入解除实时Overflow条件", "STOP停止当前功能", "CLEAR清Overflow状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["Float边界输入", "Q15边界Expected", "硬件Q15输出", "正常恢复输入完成状态", "Overflow前后值"]
failure_observations:
  - key: actual_overflow
    label: "实际Float转Q15 Overflow状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.float_overflow
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_007
case_name: FMAC 内部Clip与Saturation状态测试
report_feature: |-
  1. FMAC 内部累加器Clip
  2. FMAC 累加器Saturation状态
p_level: P1
feature_refs: [FMAC_F_022, FMAC_F_030]
method:
  inputs:
    - "越界刺激：使用16项0x7FFF系数、16项0x7FFF X1历史和16项0x7FFF持续输入，使内部s(26,22)累加范围发生确定性正向越界。"
    - "正常对照：使用单项0x4000系数和0x2000输入，保证内部累加不越界。"
    - "策略矩阵：同一越界刺激分别执行CLIPEN=0和CLIPEN=1，最终输出策略固定为Wrap，避免最终s(16,15)饱和掩盖内部Clip差异。"
  steps:
    - "历史准备：显式Stop、Clear，配置足够容纳16抽头的X1/X2/Y区域，保持RAW输出、Offset=0、Shift=NONE和DMA Gate关闭。"
    - "Wrap执行：配置CLIPEN=0和最终Wrap，装载固定系数/历史，运行越界刺激并读取完整输出和Saturation状态。"
    - "Clip执行：Clear后重建相同配置、系数和历史，仅将CLIPEN改为1，运行相同刺激并读取完整输出和状态。"
    - "策略比较：固定比较两次运行最后4个稳态输出；要求两组各自跨重复执行完全一致，并且Wrap与Clip稳态尾段不同。"
    - "正常对照：执行不越界向量并确认两策略结果相同且Saturation不置位。"
    - "状态恢复：执行CLEAR并再次读取Saturation状态确认归零。"
  observations:
    - "Wrap硬件输出：CLIPEN=0子实例读取最后4项稳态输出，期望两次重复结果完全一致。"
    - "Clip硬件输出：CLIPEN=1子实例读取最后4项稳态输出，期望两次重复结果完全一致且与Wrap尾段不同。"
    - "Saturation触发状态：越界刺激后读取STATUS.ACCUMULATOR_SATURATION，期望为1；证明硬件检测到内部累加越界。"
    - "Saturation正常状态：正常范围对照读取STATUS.ACCUMULATOR_SATURATION，期望为0；证明正常运算不会误报Saturation。"
    - "Saturation清除状态：执行CLEAR后读取STATUS.ACCUMULATOR_SATURATION，期望为0；证明状态可恢复到清洁基线。"
  pass_criteria:
    - "策略路径有效性：相同越界刺激只改变CLIPEN后，Wrap与Clip稳态尾段必须不同，且各自重复运行结果完全一致。"
    - "状态因果正确性：真实内部越界产生Saturation，正常范围不产生。"
    - "状态恢复正确性：Clear后Saturation回到0且正常路径可继续。"
timeout: "每个策略实例和状态清除动作使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清Saturation现场"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["越界/正常刺激", "Wrap两轮输出", "Clip两轮输出", "Saturation前后值"]
failure_observations:
  - key: actual_saturation
    label: "实际累加器Saturation状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.saturation_status
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_008
case_name: FMAC 最终输出Saturate/Wrap测试
report_feature: |-
  1. FMAC 最终输出Saturate/Wrap
p_level: P1
feature_refs: [FMAC_F_023]
method:
  inputs:
    - "最终越界向量：目标至少支持8个前馈抽头且Capability声明内部累加范围可精确表示2.0时，使用8抽头恒定向量，X1输入和全部系数均为0x4000，使独立累加结果精确为2.0；最终SATURATE期望0x7FFF，最终WRAP期望0x0000。"
    - "正常对照向量：使用2抽头恒定0x4000输入/系数，使独立结果精确为0.5；两种最终策略期望均为0x4000。"
    - "对齐处理：预装恒定X1历史并读取稳态比较窗口，使比较值不依赖首个有效输出索引。"
  steps:
    - "越界隔离：确认刺激只依赖最终Q15越界，不触发内部Clip或Offset/Shift副作用。"
    - "Saturate准备：PC按0.5显式建立Known Baseline，建立恒定历史并在完整配置中选择最终SATURATE策略。"
    - "Saturate执行：运行当前稳态事务并读取完整比较窗口。"
    - "Wrap执行：CLEAR后重建同一baseline和相同历史，仅切换最终WRAP并读取同一稳态窗口。"
    - "独立比较：两组Actual分别与Q15 Saturate和Wrap独立Expected逐元素比较。"
    - "正常对照：运行不越界向量，确认两策略输出彼此一致。"
    - "矩阵汇总：SATURATE、WRAP和正常对照全部通过后才PASS。"
  observations:
    - "Saturate硬件输出：SATURATE子实例读取DATA.OUTPUT_STREAM，期望越界样本等于Q15饱和边界；证明最终Saturate策略生效。"
    - "Wrap硬件输出：WRAP子实例读取DATA.OUTPUT_STREAM，期望越界样本等于独立环绕结果；证明最终Wrap策略生效。"
    - "正常硬件输出：正常范围对照读取DATA.OUTPUT_STREAM，期望两策略均等于基础Expected；证明策略差异只来源于最终越界。"
  pass_criteria:
    - "最终策略正确性：两种越界处理分别逐元素等于独立Expected。"
    - "正常范围一致性：不越界时两策略输出相同且等于基础Expected。"
    - "策略覆盖完整性：SATURATE和WRAP均执行完成。"
timeout: "每个策略实例使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["最终越界刺激", "两策略Expected", "Saturate输出", "Wrap输出", "正常对照输出"]
failure_observations:
  - key: actual_output
    label: "实际最终策略输出"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.final_policy
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_009
case_name: FMAC 输出数据模式矩阵测试
report_feature: |-
  1. FMAC 输出数据模式
p_level: P1
feature_refs: [FMAC_F_024]
method:
  inputs:
    - "区分向量：使用单抽头系数0x2000和恒定输入0x4000，构造精确基础输出0x1000；RAW和SATURATE_16期望0x1000，SATURATE_12期望正12-bit上边界0x07FF。"
    - "模式矩阵：逐一执行三种模式并为每种模式生成独立后处理Expected。"
  steps:
    - "模式能力确认：确认RAW、SAT12和SAT16均发布并生成三套独立Expected。"
    - "实例清理：每个模式前由PC按0.5显式建立Known Baseline并重建相同恒定历史。"
    - "模式配置：只切换当前Output Mode，输入、系数和其他策略保持一致。"
    - "硬件执行：运行稳态短事务并读取完整比较窗口。"
    - "单模式比较：逐元素比较当前Actual与该模式独立Expected。"
    - "差异隔离：确认模式差异只发生在独立模型预测的位置。"
    - "三模式汇总：三种模式全部通过独立Oracle后才PASS。"
  observations:
    - "RAW硬件输出：RAW子实例读取DATA.OUTPUT_STREAM，期望等于未经额外模式处理的基础Expected；证明RAW路径不执行额外模式处理。"
    - "SAT12硬件输出：SAT12子实例读取DATA.OUTPUT_STREAM，期望等于独立12-bit Saturate Expected；证明12-bit输出模式生效。"
    - "SAT16硬件输出：SAT16子实例读取DATA.OUTPUT_STREAM，期望等于独立16-bit Saturate Expected；证明16-bit输出模式生效。"
  pass_criteria:
    - "模式数值正确性：RAW、SAT12和SAT16分别逐元素等于对应Expected。"
    - "模式覆盖完整性：三种公开模式全部执行。"
    - "副作用隔离：所有实例使用相同输入/系数且Offset=0、Shift=NONE。"
timeout: "每个模式实例使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["模式参数", "三套Expected", "三组硬件输出"]
failure_observations:
  - key: actual_output
    label: "实际输出模式结果"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.output_mode
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_010
case_name: FMAC 输出Offset与负值状态测试
report_feature: |-
  1. FMAC 输出Offset
  2. FMAC Offset后负值状态
p_level: P1
feature_refs: [FMAC_F_025, FMAC_F_026]
method:
  inputs:
    - "Offset子实例：仅使用正向无歧义Offset code 0x0800；负值子实例基础输出为-0x1000、Offset后期望-0x0800，非负子实例基础输出为0x0400、Offset后期望0x0C00。"
    - "固定后处理：Output Mode固定SATURATE_16，Shift固定NONE，避免RAW模式不消费Offset。"
  steps:
    - "范围确认：确认当前offset参数不依赖未闭合的高位/符号扩展解释。"
    - "负值准备：PC按0.5显式建立Known Baseline，重建恒定历史并在完整配置中选择SAT16、Shift NONE和当前offset。"
    - "负值执行：运行产生全部负Expected的稳态短事务并读取输出和负值状态。"
    - "状态恢复：停止已完成的负值事务，重建相同FMAC配置和单抽头数据路径，再提交正稳态输入撤销Offset后负值的实时硬件条件，确认恢复事务完整收发。"
    - "状态清除：实时条件撤销后执行公共clear动作清动态状态，并确认负值状态回0。"
    - "非负执行：重建同一baseline和相同历史，保持同一offset和后处理，运行全部非负Expected事务并读取输出。"
    - "非负状态：读取负值状态并确认未再次置位。"
    - "数值汇总：两类子实例的DATA.OUTPUT_STREAM均逐元素比较独立Offset Expected。"
  observations:
    - "负值子实例输出：读取DATA.OUTPUT_STREAM，期望逐元素等于负值Offset Expected；证明Offset真实参与输出后处理。"
    - "负值触发状态：负值子实例读取STATUS.NEGATIVE_AFTER_OFFSET，期望为1；证明Offset后仍为负的事件被硬件记录。"
    - "恢复事务数量：正稳态恢复事务的输入接收数和输出读取数均等于请求数；证明清除前实时负值条件已撤销。"
    - "负值清除状态：实时条件撤销并执行状态清除后读取STATUS.NEGATIVE_AFTER_OFFSET，期望为0；证明sticky状态能够被软件清除。"
    - "非负子实例输出：读取DATA.OUTPUT_STREAM，期望逐元素等于非负Offset Expected；证明同一Offset在非负路径数值关系正确。"
    - "非负子实例状态：非负子实例读取STATUS.NEGATIVE_AFTER_OFFSET，期望为0；证明清除后非负事务不会误置位。"
  pass_criteria:
    - "Offset数值正确性：负值和非负子实例输出均逐元素等于独立Expected。"
    - "负值状态正确性：负值实例置位，正稳态恢复事务完成后清除回0，非负实例保持0。"
    - "后处理模式正确性：全程使用SATURATE_16和Shift NONE。"
timeout: "每个Offset子实例和状态清除动作使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清负值状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["offset参数", "两类Offset Expected", "两类硬件输出", "恢复事务收发数量", "负值状态前后值"]
failure_observations:
  - key: actual_negative
    label: "实际Offset后负值状态"
    source: dut
    role: actual
    format: bool
    semantic_ref: fmac.feature.negative_after_offset
gap: [output_offset_full_domain_semantics_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_011
case_name: FMAC 输出Shift全合法编码测试
report_feature: |-
  1. FMAC 输出Shift
p_level: P1
feature_refs: [FMAC_F_027]
method:
  inputs:
    - "Shift矩阵：遍历LEFT_8..LEFT_1、NONE、RIGHT_1..RIGHT_7共16个公开逻辑选项。"
    - "固定后处理：使用基础输出+0x0020和-0x0020的两组恒定历史/输入，Output Mode固定SATURATE_16且Offset=0；两组值左移8位仍不越界，并可覆盖负数右移符号保持。"
  steps:
    - "能力确认：读取Capability发布的16个Shift逻辑选项。"
    - "NONE基线：PC按0.5显式建立Known Baseline，并以SAT16、offset0、NONE运行稳态基础事务。"
    - "单Shift配置：每个参数实例CLEAR并重建同一baseline和相同历史后只改变当前Shift选项。"
    - "硬件执行：运行同一稳态短事务并读取完整比较窗口。"
    - "独立计算：对基础Expected应用当前有符号移位规则生成Expected。"
    - "逐编码比较：逐元素比较Actual和Expected并记录逻辑Shift名称。"
    - "矩阵汇总：16/16公开选项全部通过后才PASS。"
  observations:
    - "Shift硬件输出：当前Shift子实例读取DATA.OUTPUT_STREAM，期望逐元素等于独立移位Expected；证明当前Shift编码真实参与输出后处理。"
    - "NONE硬件输出：NONE子实例读取DATA.OUTPUT_STREAM，期望等于SAT16基础Expected；证明无移位选项不改变基础输出。"
  pass_criteria:
    - "Shift矩阵正确性：16/16公开选项全部逐元素匹配各自Expected。"
    - "NONE语义正确性：NONE不引入额外移位。"
    - "后处理模式正确性：全程SATURATE_16且Offset=0。"
timeout: "每个Shift参数实例使用有界deadline。"
cleanup: ["STOP停止当前功能", "CLEAR清动态状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["16项Shift参数", "独立Shift Expected", "各编码硬件输出"]
failure_observations:
  - key: actual_output
    label: "实际Shift输出"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.output_shift
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_012
case_name: FMAC 十一源IRQ控制Force与投递矩阵测试
report_feature: |-
  1. FMAC IRQ Enable/Disable
  2. FMAC IRQ Mask/Unmask
  3. FMAC IRQ Clear
  4. FMAC IRQ RAW状态
  5. FMAC IRQ STATUS状态
  6. FMAC IRQ Force
  7. FMAC IRQ投递
p_level: P1
feature_refs: [FMAC_F_044, FMAC_F_045, FMAC_F_046, FMAC_F_047, FMAC_F_048, FMAC_F_049, FMAC_F_050]
method:
  inputs:
    - "IRQ矩阵：遍历11个公共Source，逐源执行Disable、Enable、Mask、Unmask、Force和Clear。"
    - "投递Measurement：每个Source开始前记录irq_delivery_count基线，用于有界判断Disable/Mask是否产生新增投递。"
  steps:
    - "基线建立：PC按0.5显式建立Known Baseline，保持全部Source Disable/Unmask/Clear，读取当前Source Raw/Status基线并记录irq_delivery_count。"
    - "Disable验证：保持当前Source Disable后执行Force，读取Raw/Status和Delivery latch，并在有界窗口内再次记录irq_delivery_count。"
    - "Enable验证：Clear后Enable当前Source并Force，读取Raw、Status和IRQ_DELIVERY.LATCHED_SOURCE，同时记录delivery count。"
    - "Mask验证：Clear后Mask当前Source再Force，读取Raw、Status并记录delivery count。"
    - "Unmask验证：Clear后Unmask并Force，读取Status和IRQ_DELIVERY.LATCHED_SOURCE并记录delivery count。"
    - "精确Clear：Clear当前Source，分别读取其Raw和Status并检查未选Source。"
    - "十一源汇总：11/11 Source全部满足控制、状态、投递Observation和delivery-count Measurement判据后才PASS。"
  observations:
    - "IRQ Raw基线：当前Source基线读取IRQ_RAW.<source>，期望为0；证明本子实例没有继承前序Raw事件。"
    - "IRQ Status基线：当前Source基线读取IRQ_STATUS.<source>，期望为0；证明本子实例没有继承前序有效IRQ状态。"
    - "Disable Raw状态：Source Disable后Force读取IRQ_RAW.<source>，期望为1；证明Force事件已经进入Raw事件面而不是没有产生刺激。"
    - "Disable Status状态：Source Disable后Force读取IRQ_STATUS.<source>，期望为0；结合delivery count不增加，证明Disable抑制有效IRQ和真实投递。"
    - "Enable Raw状态：Enable且Unmask后Force读取IRQ_RAW.<source>，期望为1；证明Force事件进入Raw事件面。"
    - "Enable Status状态：Enable且Unmask后Force读取IRQ_STATUS.<source>，期望为1；证明Enable+Unmask允许事件进入有效状态。"
    - "Enable投递Source：Enable且Unmask后Force读取IRQ_DELIVERY.LATCHED_SOURCE，期望为当前Source；证明有效事件到达真实目标中断投递链。"
    - "Mask Raw状态：Mask后Force读取IRQ_RAW.<source>，期望为1；证明Mask不吞掉Raw事件事实。"
    - "Mask Status状态：Mask后Force读取IRQ_STATUS.<source>，期望为0；证明Mask只抑制有效IRQ状态。"
    - "Clear Raw状态：Clear当前Source后读取IRQ_RAW.<source>，期望为0；证明目标Raw事件被清除。"
    - "Clear Status状态：Clear当前Source后读取IRQ_STATUS.<source>，期望为0；证明目标有效IRQ状态被清除。"
  pass_criteria:
    - "Source覆盖完整性：11/11公共Source均逐源完成完整控制序列。"
    - "投递Measurement正确性：Disable和Mask阶段irq_delivery_count在有界窗口内不增加，Enable+Unmask阶段相对基线恰增加一次。"
    - "Enable/Mask状态正确性：Disable与Mask阶段Raw均保持1而Status为0，Enable+Unmask阶段Raw/Status均为1。"
    - "Clear隔离性：Clear后目标Source Raw/Status归零且未刺激Source保持0。"
timeout: "每个IRQ Source使用独立有界deadline；等待投递不得只靠固定sleep。"
cleanup: ["IRQ_CLEAR清owned Source", "IRQ_DISABLE恢复Enable", "IRQ_UNMASK恢复Mask", "STOP并CLEAR FMAC"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["11源IRQ矩阵", "Raw序列", "Status序列", "IRQ_DELIVERY.LATCHED_SOURCE", "irq_delivery_count Measurement"]
failure_observations:
  - key: actual_irq_delivery
    label: "实际IRQ投递Source"
    source: dut
    role: actual
    format: hex32
    semantic_ref: fmac.feature.irq_delivery
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_013
case_name: FMAC 自然请求IRQ测试
report_feature: |-
  1. FMAC X1写请求IRQ
  2. FMAC Y读请求IRQ
  3. FMAC IRQ投递
p_level: P1
feature_refs: [FMAC_F_033, FMAC_F_034, FMAC_F_050]
method:
  inputs:
    - "请求矩阵：Known Baseline下分别用等待输入的FIR和保留未读输出的单抽头FIR建立X1写请求与Y读请求条件。"
    - "IRQ隔离：当前Request Source Enable/Unmask，其他FMAC Source保持禁用并清除，同时记录irq_delivery_count基线。"
  steps:
    - "请求能力确认：确认两类Request Source和目标Watermark条件均已发布。"
    - "X1请求基线：PC按0.5显式建立Known Baseline，在完整配置中设置X1水位，清IRQ并记录投递Measurement基线。"
    - "X1自然条件：通过受控X1装载使X1处于写请求有效条件，采集X1状态、IRQ状态和投递Source。"
    - "Y请求基线：CLEAR后重新应用baseline、配置Y水位并重新清IRQ、记录新的投递Measurement基线。"
    - "Y自然条件：装载单抽头系数与零历史，执行FIR并保留一项未读输出，使读请求条件成立。"
    - "Source比较：确认两类自然Source只在各自对应的Buffer条件下出现，禁止Force代替。"
    - "投递收敛：Service在首次投递后Mask仍保持条件有效的Request Level Source，PC显式Unmask时重新使能。"
    - "清理恢复：逐Source Clear/Disable并确认没有残留Raw/Status或新增投递Measurement。"
  observations:
    - "X1 Spare状态：X1请求子实例读取STATUS.X1_SPARE_COUNT，期望满足当前写请求条件；证明X1请求建立在真实可写容量状态上。"
    - "X1 Full状态：X1请求子实例读取STATUS.X1_FULL，期望与当前Watermark模型一致；证明请求条件与X1流控边界一致。"
    - "X1请求Raw：读取IRQ_RAW.X1_WRITE_REQUEST，期望为1；证明真实X1条件产生对应Raw Source。"
    - "X1请求Status：读取IRQ_STATUS.X1_WRITE_REQUEST，期望为1；证明该自然事件在Enable+Unmask下成为有效IRQ。"
    - "X1请求投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望为X1_WRITE_REQUEST；证明自然X1请求到达目标中断投递链。"
    - "Y Unread状态：Y请求子实例读取STATUS.Y_UNREAD_COUNT，期望满足当前读请求条件；证明Y请求建立在真实可读数据状态上。"
    - "Y Empty状态：Y请求子实例读取STATUS.Y_EMPTY，期望与当前Watermark模型一致；证明请求条件与Y流控边界一致。"
    - "Y请求Raw：读取IRQ_RAW.Y_READ_REQUEST，期望为1；证明真实Y条件产生对应Raw Source。"
    - "Y请求Status：读取IRQ_STATUS.Y_READ_REQUEST，期望为1；证明该自然事件在Enable+Unmask下成为有效IRQ。"
    - "Y请求投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望为Y_READ_REQUEST；证明自然Y请求到达目标中断投递链。"
  pass_criteria:
    - "自然条件真实性：X1写请求和Y读请求均由真实Buffer状态产生而不是Force。"
    - "IRQ身份正确性：两类Source的Raw、Status和Delivery Source与当前请求方向一致。"
    - "投递Measurement完整性：每个自然Source相对各自基线产生预期新增投递，未选Request Source不产生额外投递。"
timeout: "自然请求条件使用状态驱动有界deadline。"
cleanup: ["清X1/Y Request owned pending", "Disable本Case Request Source", "STOP并CLEAR FMAC"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["X1状态", "Y状态", "两类Request Raw/Status", "Delivery Source", "irq_delivery_count Measurement"]
failure_observations:
  - key: actual_irq_source
    label: "实际自然请求IRQ Source"
    source: dut
    role: actual
    format: hex32
    semantic_ref: fmac.interrupt.request_irq
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_014
case_name: FMAC 自然运算与Buffer边界IRQ测试
report_feature: |-
  1. FMAC Saturation IRQ
  2. FMAC X1 Overflow IRQ
  3. FMAC Y Underflow IRQ
  4. FMAC IRQ投递
p_level: P1
feature_refs: [FMAC_F_035, FMAC_F_036, FMAC_F_037, FMAC_F_050]
method:
  inputs:
    - "自然事件矩阵：Saturation使用16抽头、X1输入/系数均为0x7FFF形成内部s(26,22)远越界刺激；X1 Overflow先装满200项Buffer，再启动单抽头FIR并补偿其启动消费，随后额外直写；Y Underflow先形成并读完4项真实FIR输出后额外读取。"
    - "IRQ隔离：每个子实例只Enable/Unmask当前自然Source并清除其他owned Source，同时记录投递Measurement基线。"
  steps:
    - "Source能力确认：确认三个自然Source均发布并建立Known Baseline、清洁状态和IRQ基线。"
    - "Saturation刺激：使用16抽头远越界向量和最终Wrap策略；本子实例只判定Saturation状态及IRQ因果链，不对未闭合量化策略下的输出值作Oracle。"
    - "X1 Overflow刺激：配置并预装满200项X1，启动单抽头FIR并确认其消费1项；连续unchecked写入2项，第一项补满空位，第二项在无空间状态下形成Overflow，再依次采集状态、IRQ和投递。"
    - "Y Underflow刺激：配置4项Y和单抽头FIR，写入4项输入并等待4项真实输出；读完后在容量加一次的严格上界内继续读取，直到形成自然Underflow，随后采集状态、IRQ和投递。"
    - "逐源Clear：每个子实例后精确Clear并分别确认目标Raw和Status归零。"
    - "Source隔离检查：每个子实例读取完整IRQ_RAW和IRQ_STATUS Source Mask，确认两者均精确等于当前Source bit，且未刺激Source没有新增投递Measurement。"
    - "恢复确认：三个子实例结束后执行正常Buffer操作并确认无残留错误/IRQ。"
  observations:
    - "Saturation硬件状态：读取STATUS.ACCUMULATOR_SATURATION，期望为1；证明内部越界条件真实形成。"
    - "Saturation IRQ Raw：读取IRQ_RAW.SATURATION，期望为1；证明Saturation状态产生对应Raw事件。"
    - "Saturation IRQ Status：读取IRQ_STATUS.SATURATION，期望为1；证明自然事件进入有效IRQ状态。"
    - "Saturation IRQ投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望为SATURATION；证明自然Saturation事件到达目标中断链。"
    - "X1 Overflow硬件状态：读取STATUS.X1_OVERFLOW，期望为1；证明无空间写入形成真实Overflow。"
    - "X1 Overflow IRQ Raw：读取IRQ_RAW.X1_OVERFLOW，期望为1；证明Overflow状态产生对应Raw事件。"
    - "X1 Overflow IRQ Status：读取IRQ_STATUS.X1_OVERFLOW，期望为1；证明自然Overflow进入有效IRQ状态。"
    - "X1 Overflow IRQ投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望为X1_OVERFLOW；证明自然Overflow到达目标中断链。"
    - "Y Underflow硬件状态：读取STATUS.Y_UNDERFLOW，期望为1；证明空读形成真实Underflow。"
    - "Y Underflow IRQ Raw：读取IRQ_RAW.Y_UNDERFLOW，期望为1；证明Underflow状态产生对应Raw事件。"
    - "Y Underflow IRQ Status：读取IRQ_STATUS.Y_UNDERFLOW，期望为1；证明自然Underflow进入有效IRQ状态。"
    - "Y Underflow IRQ投递：读取IRQ_DELIVERY.LATCHED_SOURCE，期望为Y_UNDERFLOW；证明自然Underflow到达目标中断链。"
  pass_criteria:
    - "状态到IRQ因果链：三类事件均先形成对应硬件状态，再形成Raw/Status完整Mask且Mask精确等于当前Source bit。"
    - "投递身份正确性：每个自然事件的Delivery Source与当前Source一致且产生预期新增投递Measurement。"
    - "Source隔离性：未刺激Source不产生Raw/Status或新增投递。"
    - "恢复正确性：逐源Clear后无残留状态/IRQ且正常Buffer操作可继续。"
timeout: "每个自然事件子实例使用独立有界deadline。"
cleanup: ["逐源Clear并Disable本CaseIRQ", "STOP停止当前功能", "CLEAR恢复空闲状态"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["三类自然刺激", "三个硬件状态", "对应Raw/Status", "Delivery Source", "irq_delivery_count Measurement"]
failure_observations:
  - key: actual_irq_source
    label: "实际自然边界IRQ Source"
    source: dut
    role: actual
    format: hex32
    semantic_ref: fmac.interrupt.boundary_irq
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P1_015
case_name: FMAC P/PQ/Q参数错误自然IRQ测试
report_feature: |-
  1. FMAC P Error IRQ
  2. FMAC PQ Error IRQ
  3. FMAC Q Error IRQ
  4. FMAC IRQ投递
p_level: P1
feature_refs: [FMAC_F_038, FMAC_F_039, FMAC_F_040, FMAC_F_050]
method:
  inputs:
    - "P Error刺激：FIR布局设置X1容量为16，以P=17启动使P仅超出X1容量1项；合法对照使用P=1。"
    - "PQ Error刺激：IIR布局设置X2容量为8，以P=5、Q=4启动，使P+Q仅超出X2容量1项；合法对照使用P=4、Q=3。"
    - "Q Error刺激：IIR布局设置X2容量为8、Y容量为4，以P=1、Q=5启动，使Q仅超出Y容量1项且P+Q不超过X2容量；合法对照使用P=1、Q=3。"
  steps:
    - "单源基线：每个子实例先Stop、Clear并提交对应合法布局，只Enable/Unmask当前参数错误Source。"
    - "错误刺激：分别提交P越X1容量1项、P+Q越X2容量1项或Q越Y容量1项的最小非法参数。"
    - "自然IRQ采集：读取IRQ_RAW中的参数错误三位、当前Source Status和Delivery Source并记录delivery count。"
    - "合法恢复：Stop和Clear后先提交合法参数，使电平错误条件消失。"
    - "精确Clear：合法条件生效后Clear当前Source并分别确认Raw和Status归零。"
    - "三源汇总：P、PQ、Q三个Source均独立完成错误、投递、Clear和合法恢复。"
  observations:
    - "参数错误Raw Mask：当前错误子实例只截取IRQ_RAW的P/PQ/Q三位，期望精确等于当前Source bit；X1/Y请求等无关Raw位不参与本Case判定。"
    - "参数错误Status：当前错误子实例读取IRQ_STATUS.<source>，期望为1；证明当前Source在Enable+Unmask下成为有效IRQ。"
    - "参数错误投递：当前错误子实例读取IRQ_DELIVERY.LATCHED_SOURCE，期望为当前P/PQ/Q Source；证明错误事件到达真实目标中断链。"
    - "合法恢复Raw：合法参数恢复后读取IRQ_RAW.<source>，期望为0；证明合法参数不误触发同一错误Source。"
    - "合法恢复Status：合法参数恢复后读取IRQ_STATUS.<source>，期望为0；证明合法对照不会形成有效错误IRQ。"
  pass_criteria:
    - "自然Source独立性：P、PQ、Q每个子实例截取后的参数错误Raw Mask必须精确等于当前Source bit。"
    - "合法对照正确性：合法参数不产生对应Raw/Status且delivery count不增加。"
    - "投递身份正确性：每个错误子实例Delivery Source与当前Source一致。"
timeout: "每个错误刺激、IRQ观测和合法恢复使用统一有界deadline。"
cleanup: ["Clear并Disable三个参数错误Source", "STOP并CLEAR FMAC"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["P/PQ/Q参数与Buffer容量", "参数错误Raw三位", "P/PQ/Q Status", "Delivery Source", "irq_delivery_count Measurement"]
failure_observations:
  - key: actual_irq_source
    label: "实际参数错误IRQ Source"
    source: dut
    role: actual
    format: hex32
    semantic_ref: fmac.interrupt.parameter_error
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P2_001
case_name: FMAC 双向DMA门控与FIR端到端测试
report_feature: |-
  1. FMAC DMA输入写请求
  2. FMAC DMA输出读请求
  3. FMAC Q15 FIR卷积
p_level: P2
feature_refs: [FMAC_F_031, FMAC_F_032, FMAC_F_013]
method:
  inputs:
    - "DMA映射：从目标Profile解析FMAC输入/输出request、endpoint和transfer_width；公共Case不得硬编码任何芯片的编号或地址。"
    - "FIR向量：使用[0x4000,0x2000,0x1000,0x0800]四抽头和恒定0x2000输入；只比较最后4项稳态输出0x1E00，DMA目的区域预填哨兵值。"
  steps:
    - "资格门禁：解析双向Execution Mapping并确认输入/输出宽度均为16-bit；FMAC X1/Y Watermark均设置为1。"
    - "空闲基线：PC按0.5显式建立FMAC Known Baseline，装载系数和等长零X1历史并清两个DMA Channel，保持两个FMAC Request Gate关闭。"
    - "Gate关闭对照：准备两个DMA描述符但不打开FMAC Request Gate，观察Channel和目的区域。"
    - "双向配置：Gate关闭对照结束后保持FMAC idle，在两条已配置DMA Channel等待期间打开两个Request Gate。"
    - "DMA事务启动：Request Gate配置完成后Enable FMAC，在共享deadline内等待两条DMA Channel进入明确终态。"
    - "Peer证据读取：分别读取输入/输出Channel终态和目的数据。"
    - "端到端比较：确认两个Channel均无ERROR并回到Free，固定比较DMA目的序列最后4项均为0x1E00，不搜索动态偏移。"
    - "逆序清理：先STOP FMAC使其idle，再关闭Request Gate、停/清DMA、释放映射，最后CLEAR FMAC和Resource。"
  observations:
    - "Gate关闭输入终态：读取DMA_CHANNEL_STATUS.INPUT，期望不为成功完成；证明输入request gate关闭时不会伪造DMA完成。"
    - "Gate关闭输出终态：读取DMA_CHANNEL_STATUS.OUTPUT，期望不为成功完成；证明输出request gate关闭时不会伪造DMA完成。"
    - "Gate关闭目的数据：读取DMA_DESTINATION_SEQUENCE，期望保持预置哨兵值；证明Gate关闭期间没有实际结果搬运。"
    - "输入DMA终态：Gate开启后读取DMA_CHANNEL_STATUS.INPUT，期望明确完成；证明memory到FMAC输入请求路径真实工作。"
    - "输出DMA终态：Gate开启后读取DMA_CHANNEL_STATUS.OUTPUT，期望明确完成；证明FMAC到memory输出请求路径真实工作。"
    - "DMA目的数据：读取DMA_DESTINATION_SEQUENCE最后4项，期望全部为0x1E00；证明DMA完成对应真实FMAC稳态计算结果。"
  pass_criteria:
    - "Gate控制真实性：Gate关闭对照两个Channel均无伪成功且目的区域保持哨兵。"
    - "双向DMA终态：Gate开启后输入和输出Channel均无ERROR并回到Free。"
    - "端到端数据正确性：DMA目的序列最后4项逐元素等于0x1E00。"
    - "目标约束满足性：Request Gate只在FMAC idle修改且使用目标要求的DMA Watermark。"
timeout: "FMAC和两个DMA Channel共享Case顶层deadline；Gate关闭对照使用短有界观察窗。"
cleanup: ["STOP FMAC使其idle", "关闭FMAC Request Gate", "停止并清两条DMA Channel", "释放Mapping资源", "CLEAR FMAC和Resource"]
resources:
  minimum_level: "R2"
  full_coverage_level: "R2"
  board: "仅使用DUT片内FMAC、DMA和内存"
  bench: "需要目标芯片FMAC双向DMA Execution Mapping"
backend: [FPGA, Silicon]
evidence: ["Execution Mapping", "Request Gate配置", "两个DMA终态", "目的数据", "独立FIR Golden"]
failure_observations:
  - key: actual_output
    label: "实际DMA FIR稳态输出"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.dma_output
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P3_001
case_name: FMAC 确定性长流FIR稳定性测试
report_feature: |-
  1. FMAC Q15 FIR卷积
  2. FMAC 流式连续处理
p_level: P3
feature_refs: [FMAC_F_013, FMAC_F_016]
method:
  inputs:
    - "长流向量：固定使用[0x4000,0x2000,0x1000,0x0800]四抽头和0x2000恒定Q15输入，总样本数4096，Chunk长度固定轮换31、47、64。"
    - "目标资源：输入和输出各使用一个64项Buffer；每个Chunk完成后立即回传PC并复用同一Buffer，避免把完整长流同时驻留在目标资源池。"
    - "稳态Golden：前4项只保留原始Evidence，从第5项起每一项Expected固定为0x1E00，因此不依赖首输出对齐搜索。"
  steps:
    - "资格门禁：确认Runtime Capability允许4抽头、4096项累计事务和至少64项单次Chunk。"
    - "会话初始化：PC按0.5显式建立Known Baseline后装载系数和等长零X1历史并Enable，确认STATUS.ACTIVE=1。"
    - "分块长流：PC逐Chunk覆写同一个输入Buffer，按固定Chunk重复有界WRITE/READ；每个输出Chunk立即读回PC并保留输入/输出索引和实际数量。"
    - "在线比较：跳过全流前4项启动区后，每个输出Chunk立即逐元素比较0x1E00，首个Mismatch保存原始硬件Chunk和全局索引。"
    - "里程碑状态：按固定样本里程碑读取STATUS.ACTIVE和必要Buffer状态。"
    - "完整结束：全部输入/输出完成后Disable并核对累计数量和最终output_digest Measurement。"
    - "重复性验证：重建Clean baseline再运行1轮，比较两轮完整输出digest和4092项稳态结果。"
    - "长稳汇总：全部轮次无Mismatch、无丢重样且可清理后才PASS。"
  observations:
    - "长流硬件输出：当前Chunk读取DATA.OUTPUT_STREAM，第5项起期望逐元素等于0x1E00；证明长时间Chunk处理没有数值漂移或样本错序。"
    - "长流活动状态：中间里程碑读取STATUS.ACTIVE，期望为1；证明长稳会话没有无因停止。"
    - "长流停止状态：显式Disable后读取STATUS.ACTIVE，期望为0；证明长稳会话能够有界结束并进入清理。"
  pass_criteria:
    - "全流数值正确性：每轮4092项稳态输出全部等于0x1E00。"
    - "样本完整性：每轮累计输入/输出均为4096，无丢样、重复或乱序。"
    - "重复一致性：两轮output_digest Measurement一致且无跨轮状态泄漏。"
    - "运行稳定性：整个声明时段无无界等待或不可恢复错误。"
timeout: "Run Config声明总运行时段；每个目标动作仍有独立有界deadline。"
cleanup: ["STOP当前会话", "关闭本CaseIRQ/DMA门控", "CLEAR动态状态", "释放长流Artifact"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线但要求稳定目标供电/时钟"
  bench: "无外部仪器"
backend: [FPGA, Silicon]
evidence: ["固定系数/输入与规模", "Chunk索引/数量", "Golden/output_digest Measurement", "首个Mismatch原始Chunk", "里程碑状态"]
failure_observations:
  - key: actual_stream_tail
    label: "双轮长流硬件尾段"
    source: dut
    role: actual
    format: bytes_hex
    semantic_ref: fmac.feature.stream_output
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P3_002
case_name: FMAC CPU路径周期性能表征
report_feature: |-
  1. FMAC Q15 FIR卷积
p_level: P3
feature_refs: [FMAC_F_013]
method:
  inputs:
    - "性能矩阵：使用四抽头稳态FIR，元素规模固定为64、128、240；每个规模预热1次、正式测量5次。"
    - "功能Oracle：输入固定为0x2000，正式样本最后4项必须全部等于0x1E00。"
  steps:
    - "计时资格：确认Runtime Capability发布TIMED_PROCESS，命令返回目标侧DWT原始周期、accepted_count和read_count。"
    - "性能基线：PC按0.5显式建立Known Baseline，每轮装载系数和等长零X1历史并执行定义次数预热，预热不计入正式统计。"
    - "单样本准备：按当前元素规模准备输入、输出空间和独立Golden。"
    - "目标计时：FMAC Service在同一原子命令内读取DWT起点、执行有界FIR事务并读取DWT终点。"
    - "功能校验：核对accepted_count/read_count与元素规模一致，输出最后4项均为0x1E00；功能失败样本不得进入性能统计。"
    - "重复采集：按Run Config保存全部原始周期和实际元素数量。"
    - "规模汇总：只对功能PASS样本派生cycles_per_element等表征，不硬编码未定义阈值。"
  observations:
    - "目标周期事实：读取TARGET_CYCLE_COUNT，期望为来源明确的有效非负周期数；证明本性能样本使用目标侧周期Observer而非PC时间。"
    - "计时硬件输出：读取DATA.OUTPUT_STREAM最后4项，期望全部为0x1E00；证明被计时事务同时满足功能正确性。"
  pass_criteria:
    - "功能前置正确性：只有输出完全等于Golden的样本才进入性能结果。"
    - "周期Evidence有效性：每个规模保留Run Config定义次数的原始目标周期。"
    - "表征完整性：每个规模都有cycles、element_count和功能结果且不伪造性能阈值。"
timeout: "每个性能样本有界；总重复次数由Run Config限定。"
cleanup: ["STOP并CLEAR FMAC", "释放性能资源", "保留原始周期Artifact"]
resources:
  minimum_level: "R0"
  full_coverage_level: "R0"
  board: "无外部接线"
  bench: "无外部仪器；周期源为DUT目标侧DWT"
backend: [FPGA, Silicon]
evidence: ["Observer身份", "原始周期样本", "元素数量", "Golden/Actual"]
failure_observations:
  - key: elapsed_cycles
    label: "目标侧实际周期数"
    source: dut
    role: actual
    format: decimal
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FMAC_P3_003
case_name: FMAC DMA路径周期性能表征
report_feature: |-
  1. FMAC DMA输入写请求
  2. FMAC DMA输出读请求
  3. FMAC Q15 FIR卷积
p_level: P3
feature_refs: [FMAC_F_031, FMAC_F_032, FMAC_F_013]
method:
  inputs:
    - "DMA性能输入：从目标Profile解析双向Execution Mapping，使用240项0x2000固定输入和四抽头稳态FIR。"
    - "功能Oracle：输入/输出Channel无ERROR且回到Free，目的序列最后8项必须全部等于0x1E00。"
  steps:
    - "资格门禁：确认双向Mapping、16-bit传输宽度、FMAC X1/Y Watermark=1以及DMA target-local timing API可用。"
    - "性能基线：PC按0.5显式建立FMAC Known Baseline，装载系数和等长零X1历史并清DMA，执行定义次数预热。"
    - "单样本配置：配置两个DMA Channel，并在FMAC保持idle时设置目标Watermark和双向Request Gate。"
    - "目标计时：Request Gate配置完成后先启动输出DMA计时，再启动输入DMA和FMAC；两个Channel完成后读取目标侧elapsed cycles。"
    - "Peer证据：分别读取两个DMA终态、传输数量和目的序列。"
    - "功能校验：核对两个DMA传输数量，并固定比较DMA目的序列最后4项均为0x1E00。"
    - "重复采集：失败或Evidence不完整的样本不得进入性能聚合。"
    - "逆序清理：先STOP FMAC使其idle，再关闭Request Gate、停/清DMA、释放映射，最后CLEAR FMAC和Resource。"
  observations:
    - "DMA目标周期：读取TARGET_CYCLE_COUNT，期望来自目标Observer；证明本性能样本的周期来源是目标侧稳定计数。"
    - "DMA输入终态：读取DMA_CHANNEL_STATUS.INPUT，期望明确完成；证明输入DMA事务真实结束。"
    - "DMA输出终态：读取DMA_CHANNEL_STATUS.OUTPUT，期望明确完成；证明输出DMA事务真实结束。"
    - "DMA目的数据：读取DMA_DESTINATION_SEQUENCE最后8项，期望全部为0x1E00；证明被计时DMA事务同时满足端到端功能正确性。"
  pass_criteria:
    - "DMA功能前置正确性：双向DMA终态无ERROR并回到Free，且目的数据Golden通过。"
    - "周期Evidence有效性：周期必须来自目标Observer，禁止PC wall-clock或历史magic correction。"
    - "表征完整性：保存240项事务的原始cycles、两个Channel终态和功能结果。"
timeout: "每个DMA性能样本有界，FMAC和DMA共享Case deadline。"
cleanup: ["STOP FMAC使其idle", "关闭FMAC Request Gate", "停止并清两条DMA Channel", "释放Mapping资源", "CLEAR FMAC和Resource"]
resources:
  minimum_level: "R2"
  full_coverage_level: "R2"
  board: "DUT片内FMAC、DMA、内存与目标周期源"
  bench: "无外部仪器；需要目标Profile提供双向Execution Mapping"
backend: [FPGA, Silicon]
evidence: ["Execution Mapping", "原始目标周期", "两个DMA终态", "目的数据与Golden"]
failure_observations:
  - key: elapsed_cycles
    label: "目标侧实际DMA周期数"
    source: dut
    role: actual
    format: decimal
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  FMAC_P0_001:
    summary: "正负Q15稳态输入经过四抽头FIR后，尾段结果与独立精确Golden一致。"
    fields:
      - {source: artifact, path: input_value, label: Q15稳态输入, format: hex16, aggregate: distinct}
      - {source: artifact, path: expected_tail, label: 期望稳态尾段, format: text, aggregate: distinct}
      - {source: artifact, path: actual_tail, label: 实际稳态尾段, format: text, aggregate: distinct}
      - {source: artifact, path: counts, label: FMAC收发数量, format: text, aggregate: same}
  FMAC_P0_002:
    summary: "FMAC Q15 IIR输出与独立Direct Form 1整数Oracle逐元素一致。"
    fields:
      - {source: artifact, path: preload_counts, label: X1与Y初态装载数量, format: text, aggregate: same}
      - {source: artifact, path: process_counts, label: IIR收发数量, format: text, aggregate: same}
      - {source: artifact, path: expected, label: IIR期望输出, format: text, aggregate: same}
      - {source: artifact, path: actual, label: IIR实际输出, format: text, aggregate: same}
  FMAC_P0_003:
    summary: "FMAC Stop终止活动功能，Clear清除Y Underflow并保留准静态配置。"
    fields:
      - {source: artifact, path: counts, label: FIR装载与写入数量, format: text, aggregate: same}
      - {source: artifact, path: before.y_underflow, label: Clear前Y Underflow, format: bool, aggregate: same}
      - {source: artifact, path: after.y_underflow, label: Clear后Y Underflow, format: bool, aggregate: same}
      - {source: artifact, path: config_preserved, label: Clear后配置保持, format: bool, aggregate: same}
  FMAC_P0_004:
    summary: "FMAC两轮Start/Stop均形成Active 1到0的完整状态序列。"
    fields:
      - {source: artifact, path: active_sequence, label: Active状态序列, format: text, aggregate: same}
  FMAC_P1_001:
    summary: "FMAC全部公共配置字段与目标侧Snapshot精确一致。"
    fields:
      - {source: artifact, path: expected.x1_size, label: 期望X1容量, format: decimal, aggregate: same}
      - {source: artifact, path: actual.x1_size, label: 实际X1容量, format: decimal, aggregate: same}
      - {source: artifact, path: actual.output_offset, label: 实际Output Offset, format: hex16, aggregate: same}
      - {source: artifact, path: exact_match, label: 完整配置一致, format: bool, aggregate: same}
  FMAC_P1_002:
    summary: "X1装满后Spare为0、Full置位，额外写入形成Overflow并可Clear。"
    fields:
      - {source: artifact, path: watermark, label: X1满阈值, format: decimal, aggregate: distinct}
      - {source: artifact, path: threshold.after.spare, label: 达到阈值后X1剩余空间, format: decimal, aggregate: same}
      - {source: artifact, path: threshold.after.full, label: 达到阈值后X1装满状态, format: bool, aggregate: same}
      - {source: artifact, path: overflow.set, label: 额外写入后X1溢出状态, format: bool, aggregate: same}
  FMAC_P1_003:
    summary: "单抽头FIR产生4项Y数据，逐项读取跨越空阈值，耗尽后空读形成Underflow并可Clear。"
    fields:
      - {source: artifact, path: watermark, label: Y空阈值, format: decimal, aggregate: distinct}
      - {source: artifact, path: status.unread_after_load, label: 装载后Y未读数量, format: decimal, aggregate: same}
      - {source: artifact, path: status.unread_sequence, label: 逐级读取后的Y状态序列, format: text, aggregate: same}
      - {source: artifact, path: status.underflow, label: 空读后Y下溢状态, format: bool, aggregate: same}
  FMAC_P1_004:
    summary: "相同FIR事务按不同Chunk切分后，拼接输出与one-shot原始序列完全一致。"
    fields:
      - {source: artifact, path: chunk_plan, label: Chunk切分, format: text, aggregate: distinct}
      - {source: artifact, path: one_shot_output, label: One-shot硬件输出, format: text, aggregate: same}
      - {source: artifact, path: chunked_output, label: Chunk拼接硬件输出, format: text, aggregate: same}
      - {source: artifact, path: chunk_counts, label: 各Chunk收发数量, format: text, aggregate: same}
  FMAC_P1_005:
    summary: "Float32转Q15和Q15转Float32双向转换均与独立参考一致。"
    fields:
      - {source: artifact, path: input_values, label: Float输入样本, format: text, aggregate: same}
      - {source: artifact, path: actual_q15, label: Float转Q15结果, format: text, aggregate: same}
      - {source: artifact, path: actual_float, label: Q15转Float结果, format: text, aggregate: same}
      - {source: artifact, path: overflow, label: 正常范围Overflow状态, format: bool, aggregate: same}
  FMAC_P1_006:
    summary: "正负Float越界值钳位到Q15边界并置位Overflow，正常输入解除实时条件后Clear恢复。"
    fields:
      - {source: artifact, path: input_values, label: 越界Float输入, format: text, aggregate: same}
      - {source: artifact, path: actual, label: Q15钳位结果, format: text, aggregate: same}
      - {source: artifact, path: recovery_completed, label: 正常输入处理完成状态, format: bool, aggregate: same}
      - {source: artifact, path: overflow, label: 越界后与Clear后Overflow状态, format: text, aggregate: same}
  FMAC_P1_007:
    summary: "相同内部越界刺激下Wrap与Clip输出分离，Saturation状态可Clear。"
    fields:
      - {source: artifact, path: steady_outputs, label: Wrap与Clip稳态尾段, format: text, aggregate: same}
      - {source: artifact, path: saturation, label: 内部Saturation状态, format: text, aggregate: same}
      - {source: artifact, path: after_clear, label: Clear后Saturation状态, format: bool, aggregate: same}
      - {source: artifact, path: transfer_counts, label: 各策略收发数量, format: text, aggregate: same}
  FMAC_P1_008:
    summary: "相同远越界FIR刺激下Saturate与Wrap产生不同稳态结果。"
    fields:
      - {source: artifact, path: final_values.saturate, label: Saturate稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: final_values.wrap, label: Wrap稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: saturate_tail, label: Saturate稳态尾部, format: text, aggregate: same}
      - {source: artifact, path: wrap_tail, label: Wrap稳态尾部, format: text, aggregate: same}
  FMAC_P1_009:
    summary: "RAW、SAT12和SAT16三种输出模式形成符合位宽约束的稳态结果。"
    fields:
      - {source: artifact, path: output_values.RAW, label: RAW稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: output_values.SAT12, label: SAT12稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: output_values.SAT16, label: SAT16稳态末值, format: decimal, aggregate: same}
  FMAC_P1_010:
    summary: "正Offset改变稳态输出，负值状态可置位并经Clear恢复。"
    fields:
      - {source: artifact, path: outputs.zero_offset, label: 零Offset稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: outputs.positive_offset, label: 正Offset稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: negative_status.after_negative, label: 负输出状态, format: bool, aggregate: same}
      - {source: artifact, path: negative_status.after_clear, label: Clear后负值状态, format: bool, aggregate: same}
  FMAC_P1_011:
    summary: "LEFT1、NONE和RIGHT1三种Shift形成严格的稳态幅值顺序。"
    fields:
      - {source: artifact, path: output_values.LEFT1, label: LEFT1稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: output_values.NONE, label: NONE稳态末值, format: decimal, aggregate: same}
      - {source: artifact, path: output_values.RIGHT1, label: RIGHT1稳态末值, format: decimal, aggregate: same}
  FMAC_P1_012:
    summary: "11个IRQ Source的Mask、Force、Delivery和Clear控制链路均可观察。"
    fields:
      - {source: artifact, path: event, label: 当前IRQ Source, format: text, aggregate: distinct}
      - {source: artifact, path: masked.raw, label: Mask阶段IRQ Raw, format: hex32, aggregate: distinct}
      - {source: artifact, path: delivered.latched, label: Unmask阶段ISR Latch, format: hex32, aggregate: distinct}
      - {source: artifact, path: delivered.event_count, label: IRQ投递计数, format: decimal, aggregate: range}
  FMAC_P1_013:
    summary: "X1写请求和Y读请求均由真实Buffer状态产生并投递IRQ。"
    fields:
      - {source: artifact, path: event, label: 自然Request Source, format: text, aggregate: distinct}
      - {source: artifact, path: status.x1_spare, label: X1 Spare状态, format: decimal, aggregate: distinct}
      - {source: artifact, path: status.y_unread, label: Y Unread状态, format: decimal, aggregate: distinct}
      - {source: artifact, path: after.latched, label: 自然Request ISR Latch, format: hex32, aggregate: distinct}
  FMAC_P1_014:
    summary: "Saturation、X1 Overflow和Y Underflow均形成硬件状态和真实IRQ投递。"
    fields:
      - {source: artifact, path: event, label: 自然错误Source, format: text, aggregate: distinct}
      - {source: artifact, path: status_set, label: 对应硬件状态, format: bool, aggregate: same}
      - {source: artifact, path: after.latched, label: 自然错误ISR Latch, format: hex32, aggregate: distinct}
      - {source: artifact, path: after.event_count, label: IRQ投递计数, format: decimal, aggregate: range}
  FMAC_P1_015:
    summary: "P、PQ和Q非法参数分别产生对应自然IRQ并完成合法恢复。"
    fields:
      - {source: artifact, path: event, label: 参数错误IRQ Source, format: text, aggregate: distinct}
      - {source: artifact, path: parameters, label: 非法与合法参数, format: text, aggregate: distinct}
      - {source: artifact, path: invalid_snapshot, label: 非法参数IRQ快照, format: text, aggregate: distinct}
      - {source: artifact, path: recovery, label: 合法参数恢复状态, format: text, aggregate: distinct}
  FMAC_P2_001:
    summary: "FMAC双向DMA Gate开启后完成16-bit FIR输入、输出搬运和稳态计算。"
    fields:
      - {source: artifact, path: gate_closed, label: Gate关闭阶段DMA状态, format: text, aggregate: same}
      - {source: artifact, path: gate_closed_unchanged, label: Gate关闭阶段目的区保持, format: bool, aggregate: same}
      - {source: artifact, path: channel_status, label: Gate开启后DMA终态, format: text, aggregate: same}
      - {source: artifact, path: steady_tail, label: DMA FIR稳态尾段, format: text, aggregate: same}
  FMAC_P3_001:
    summary: "4096项FIR长流按固定Chunk连续处理，两轮数量、输出和停止状态一致。"
    fields:
      - {source: artifact, path: chunk_plan, label: 长流Chunk计划, format: text, aggregate: same}
      - {source: artifact, path: round_counts, label: 双轮收发与停止状态, format: text, aggregate: same}
      - {source: artifact, path: steady_tail, label: 双轮稳态尾段, format: text, aggregate: same}
      - {source: artifact, path: rounds_equal, label: 双轮输出一致, format: bool, aggregate: same}
  FMAC_P3_002:
    summary: "64、128和240项CPU FIR事务保留目标侧DWT原始周期和正确输出。"
    fields:
      - {source: artifact, path: item_count, label: FIR元素数量, format: decimal, aggregate: distinct}
      - {source: artifact, path: warmup_cycles, label: 预热目标周期, format: decimal, aggregate: distinct}
      - {source: artifact, path: elapsed_cycles, label: 正式目标周期样本, format: text, aggregate: distinct}
      - {source: artifact, path: steady_tails, label: 正式样本稳态尾段, format: text, aggregate: same}
  FMAC_P3_003:
    summary: "FMAC双向DMA FIR事务同时保留目标周期、Channel终态和稳态输出。"
    fields:
      - {source: artifact, path: timing, label: DMA目标侧计时结果, format: text, aggregate: same}
      - {source: artifact, path: channel_status, label: 双向DMA终态, format: text, aggregate: same}
      - {source: artifact, path: steady_tail, label: DMA FIR稳态尾段, format: text, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---|---|---|---|
| ET6801 | ADAPTED=48; NOT_APPLICABLE=3 | ADAPTED=23 | 23个Case均已完成平台适配；三个内部Load/Store Error Feature保留硬件事实，但普通软件不可激励，不建立Formal Case | `ET6801_fmac.md` |

## 5. Common Gap / Evolution

- `pre_freeze_rebaseline`：本轮 FMAC 在没有公共 Driver/Service/Case/Registry 实现的前提下，经用户明确要求进行了完整重分析和一次性 Contract re-baseline；本 Freeze 之前的 FMAC 文档提交视为分析 Draft，不作为后续 ID 兼容锚点。从本 Freeze 起，当前 Feature/Case ID 按 R100 稳定绑定语义，后续不得再静默改义。
- `fir_output_alignment_rule`：公共 FIR Case 不得继承历史数组平移，也不得搜索最佳平移；当前基础、DMA和长流Case统一使用稳态常值尾段规避启动区对齐歧义。
- `iir_algorithm_contract`：公共IIR语义采用Q15 Direct Form 1；前馈项使用当前/历史输入，反馈项使用历史输出，累加后统一右移15位并饱和。历史Lattice参考只作为来源处置记录，不再作为当前硬件Oracle。
- `arithmetic_quantization_rule`：一般Q15中间截断/舍入不得凭空假设；FIR/Clip/DMA/长流Case使用量化不敏感稳态向量，IIR Case只复现历史逐元素等价Oracle。
- `output_offset_full_domain_semantics_gap`：Offset 完整 signed/高位扩展解释未闭合；基础 Case 仅覆盖无歧义范围。
- `parameter_error_stimulus`：P=0、P+Q超出X2容量1项、Q超出Y容量1项分别作为P/PQ/Q最小内部刺激；Case只比较参数错误三位，避免无关Request Raw位污染判定。
- `internal_load_store_error_scope`：X1/X2 Load Error与Y Store Error属于内部故障Source；普通软件无法构造对应内部故障。公共Feature保留，后续不建立Formal Case；仅IRQ控制与强制投递链由`FMAC_P1_012`覆盖。
- `dma_execution_mapping_implementation_gap`：当前目标的FMAC双向DMA事实已经确认，待写入目标Profile并由Case解析；request编号、endpoint和传输宽度禁止在公共Case硬编码。
- `timed_process_command_gap`：DMA Driver已经提供目标侧DWT计时接口；FMAC CPU路径仍需增加一条原子TIMED_PROCESS命令，禁止用PC wall-clock替代。
- 未执行的软件、Keil、FPGA、Silicon/HIL 始终保持 `NOT_EXECUTED/NOT_VERIFIED`；历史测试与日志只作为设计/问题证据。
