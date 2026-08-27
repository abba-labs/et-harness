# CRC Stable IP Contract

> 本文件只定义跨芯片稳定 Feature / Case / Report Contract；具体芯片 Hardware、Register、SDK Driver、IRQ、DMA 映射与历史证据位于同目录 `<CHIP>_crc.md`。
> 公共 PC Case / Driver / Firmware Service / Common Wrap 的稳定语义必须与本文件同步。
> `SUPPORTED / ADAPTED` 只表示硬件语义与平台实现已映射，不代表当前精确 SHA 的 FPGA/Silicon HIL 已 PASS。
> Formal Case 前置隔离统一遵循 `R210`：除纯只读能力查询外，第一次 Feature 配置前由 Case 显式复位参与 IP；DMA Case 先复位 DMA，再复位 CRC，最后复位 Resource Pool。本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

- IP：`crc`。
- Feature/Case ID 绑定稳定语义，不绑定具体芯片。
- 新芯片优先映射既有 Feature；参数、范围、实例和 IRQ 差异进入 Capability / Chip Adaptation。
- 公共 Case 只使用芯片中立的稳定硬件 endpoint；具体芯片地址、IRQn 和 SDK 类型只进入 Chip Adaptation，不进入公共 Contract/Case。
- Expected / Golden 来自独立 PC Reference、固定向量或规范状态，不允许 Firmware 复用同一算法自证 PASS。
- 当前 CRC Formal Set 为 23 个 SPEC、1 个 PLAN；`CRC_F_012 FIFO Physical Depth` 与 `CRC_F_013 FIFO Threshold` 均不得由错误的 Result 节拍断言冒充闭合。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| CRC_F_001 | CRC Module Enable/Disable控制 | Module Enable/Disable 后重新配置可恢复正常计算，不依赖上一轮残留状态 | `CRC_P0_003` |
| CRC_F_002 | CRC8/16/32 Kernel运算 | CRC8、CRC16、CRC32 三种自然宽度 Kernel 均可按独立 Golden 正确计算 | `CRC_P0_002`, `CRC_P3_001` |
| CRC_F_003 | CRC Polynomial配置 | 修改合法 Polynomial 后硬件结果与对应独立 Golden 一致 | `CRC_P1_001` |
| CRC_F_004 | CRC Initial Seed配置 | 修改合法 Initial Seed 后硬件结果与对应独立 Golden 一致 | `CRC_P1_002` |
| CRC_F_005 | CRC ByteSwap输入变换 | ByteSwap Off/On 按访问单元改变输入字节顺序且结果与独立 Golden 一致 | `CRC_P1_003` |
| CRC_F_006 | CRC RefIn位反转 | RefIn Off/On 对每个输入 Byte 执行稳定 reflection 语义 | `CRC_P1_004` |
| CRC_F_007 | CRC RefOut位反转 | RefOut Off/On 对最终 Kernel 结果执行当前 CRC 宽度 reflection | `CRC_P1_005` |
| CRC_F_008 | CRC XorOut输出异或 | XorOut 在当前 CRC 宽度内按 ALL_ZERO / ALL_ONE 处理最终结果 | `CRC_P1_006` |
| CRC_F_009 | CRC非整访问单元Byte长度 | 非整 16/32-bit 单元长度通过 remainder Byte 路径完整消费且结果正确 | `CRC_P1_007` |
| CRC_F_010 | CRC LENGTH配置/读回 | Byte 长度按当前 Kernel 宽度转换为硬件输入事务计数并可准确读回 | `CRC_P1_007` |
| CRC_F_011 | CRC Auto Length Reload模式 | ALR 开启后只配置一次 Length 即可连续两轮处理同长度不同 Payload | `CRC_P1_008` |
| CRC_F_012 | CRC FIFO Depth深度 | CRC 存在固定硬件 FIFO 队列容量；当前只有静态/间接证据，精确动态深度证明未闭合 | 无 Formal Case（`dynamic_fifo_depth_proof_gap`） |
| CRC_F_013 | CRC FIFO Threshold阈值 | `fifo_cnt <= FIFO_TRHD` 时产生 DMA Request，超过水位后撤销 Request | `CRC_P1_011`（PLAN） |
| CRC_F_014 | CRC FIFO Overflow状态 | 紧凑写入可形成 Overflow，重新进入 Module 后正常计算可恢复 | `CRC_P1_012` |
| CRC_F_015 | CRC8/16/32 Result Width | 硬件 Result 在 CRC8/16/32 模式下分别保持 8/16/32-bit 有效宽度 | `CRC_P0_002` |
| CRC_F_016 | CRC CHECK匹配 | CHECK 与计算结果一致时 CRC Result 正确且 CHECK_ERROR Raw/Status 不置位 | `CRC_P1_009` |
| CRC_F_017 | CRC CHECK_ERROR IRQ中断 | CHECK 与计算结果不一致时形成 CHECK_ERROR 并真实到达 CPU ISR | `CRC_P1_010` |
| CRC_F_018 | CRC LENGTH_ERROR IRQ中断 | 无剩余 Length 时继续合法宽度输入形成 LENGTH_ERROR 并真实到达 CPU | `CRC_P1_016` |
| CRC_F_019 | CRC BUS_ERROR状态 | CRC8 下合法 8-bit 基线不报错，非法 32-bit 输入访问形成 BUS_ERROR 且可恢复 | `CRC_P1_018` |
| CRC_F_020 | CRC IRQ Source Enable/Disable控制 | Source Enable 时事件可到达 CPU，Disable 后相同 Force 不再增加 Delivery 计数 | `CRC_P1_013` |
| CRC_F_021 | CRC IRQ Mask/Unmask控制 | Mask 保留 Raw 并抑制有效 Status/ISR；Unmask 后新事件可真实 Delivery | `CRC_P1_015` |
| CRC_F_022 | CRC IRQ Force强制 | BUS/LENGTH/CHECK 三类 Source 均可独立 Force 并形成对应事件证据 | `CRC_P1_013` |
| CRC_F_023 | CRC IRQ Clear清除 | Mask 状态下 Force 的目标 Raw 可被 Clear，且 Clear 不制造新 Delivery | `CRC_P1_014` |
| CRC_F_024 | CRC IRQ RAW/STATUS状态 | 同一 Source 在 Mask 状态可表现为 Raw=1、Status=0 | `CRC_P1_015` |
| CRC_F_025 | CRC IRQ Delivery投递 | 真实 IRQ 由 Service ISR latch/last_raw 与 event_count 证明，和当前 Raw/Status 分开表达 | `CRC_P1_010`, `CRC_P1_013`, `CRC_P1_016`, `CRC_P1_018` |
| CRC_F_026 | CRC DMA M2P输入 | DMA 按 CRC 自然宽度把 Memory 数据送入输入端点，Channel 完成后 CRC 与独立 Golden 一致 | `CRC_P2_001` |
| CRC_F_027 | CRC CPU Path Cycle Count周期 | 256/4096-byte CPU 路径由目标侧周期计数形成可重复测量，不使用 PC 往返时间 | `CRC_P3_002` |
| CRC_F_028 | CRC DMA Start-to-IRQ Cycle Count周期 | 256/4096-byte DMA 路径由目标侧 Timing/IRQ 周期形成可重复测量 | `CRC_P3_003` |
| CRC_F_029 | CRC Component Identity/Capability身份 | CRC实例、模式、IRQ、FIFO与同步计算上限由Capability和Runtime只读身份共同声明 | `CRC_P0_001` |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| CRC_P0_001 | P0 | CRC静态能力、Runtime Service能力与实例身份一致 | CRC运行时能力与身份一致性测试 | SPEC |
| CRC_P0_002 | P0 | CRC8/16/32三种Kernel结果和自然宽度正确 | CRC8/16/32基础计算测试 | SPEC |
| CRC_P0_003 | P0 | CRC模块关闭后可重新使能并恢复正确计算 | CRC模块启停与恢复测试 | SPEC |
| CRC_P1_001 | P1 | Polynomial可编程且硬件结果与对应Golden一致 | CRC多项式配置测试 | SPEC |
| CRC_P1_002 | P1 | Initial Seed可编程且硬件结果与对应Golden一致 | CRC初始值配置测试 | SPEC |
| CRC_P1_003 | P1 | CRC16/32 ByteSwap Off/On输入变换正确 | CRC输入字节交换测试 | SPEC |
| CRC_P1_004 | P1 | RefIn Off/On逐Byte bit reflection正确 | CRC输入位反转测试 | SPEC |
| CRC_P1_005 | P1 | RefOut Off/On自然宽度输出reflection正确 | CRC输出位反转测试 | SPEC |
| CRC_P1_006 | P1 | XorOut ALL_ZERO/ALL_ONE自然宽度处理正确 | CRC输出异或测试 | SPEC |
| CRC_P1_007 | P1 | 非整访问单元Byte长度正确且LENGTH可编程读回 | CRC非整字节长度与LENGTH读回测试 | SPEC |
| CRC_P1_008 | P1 | Auto Length Reload连续两轮同长度输入正确 | CRC自动长度重载测试 | SPEC |
| CRC_P1_009 | P1 | CHECK匹配时结果正确且CHECK_ERROR不置位 | CRC结果校验匹配测试 | SPEC |
| CRC_P1_010 | P1 | CHECK mismatch形成CHECK_ERROR并真实到达CPU | CRC校验错误中断测试 | SPEC |
| CRC_P1_011 | P1 | FIFO Threshold控制DMA Request水位边界 | CRC FIFO DMA请求水位测试 | PLAN |
| CRC_P1_012 | P1 | FIFO Overflow可检测且重新配置后恢复计算 | CRC FIFO溢出与恢复测试 | SPEC |
| CRC_P1_013 | P1 | IRQ Source Enable/Disable、Force与真实Delivery | CRC中断强制、投递与关闭测试 | SPEC |
| CRC_P1_014 | P1 | IRQ Pending可精确Clear且不制造新Delivery | CRC中断清除测试 | SPEC |
| CRC_P1_015 | P1 | IRQ Mask保留Raw并抑制Delivery，Unmask后可投递 | CRC中断屏蔽与Raw状态测试 | SPEC |
| CRC_P1_016 | P1 | LENGTH=0合法宽度输入形成LENGTH_ERROR真实IRQ | CRC长度错误中断测试 | SPEC |
| CRC_P1_018 | P1 | CRC8非法32-bit输入形成BUS_ERROR且可恢复 | CRC非法访问宽度BUS_ERR与恢复测试 | SPEC |
| CRC_P2_001 | P2 | DMA向CRC输入后Channel完成、Length归零且结果正确 | CRC DMA输入等价性测试 | SPEC |
| CRC_P3_001 | P3 | 连续20轮不同配置/长度CRC32结果稳定正确 | CRC确定性长稳测试 | SPEC |
| CRC_P3_002 | P3 | CPU路径256/4096-byte目标侧周期可重复表征 | CRC CPU输入路径吞吐表征测试 | SPEC |
| CRC_P3_003 | P3 | DMA路径256/4096-byte Start-to-IRQ周期可重复表征 | CRC DMA输入路径吞吐表征测试 | SPEC |

## 3. Machine-readable Case Contract

> 以下 23 个 `ET_CASE_SPEC` 均对应 Registry 中唯一真实 `test_*`；`CRC_P1_011` 保持为 `ET_CASE_PLAN`，等待独立 `dma_req/fifo_cnt` Observer。`method` 是人工审核和代码实现共同基线；Reviewer 只阅读本节即可复原输入、配置、刺激、硬件观测、Expected 和 PASS 逻辑。

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P0_001
case_name: CRC运行时能力与身份一致性测试
report_feature: |-
  1. CRC Component Identity/Capability身份
p_level: P0
feature_refs: [CRC_F_029]
method:
  inputs:
    - 静态能力集合：使用当前芯片 Capability 声明的全部 CRC 实例、模式、IRQ、FIFO Threshold 上限与同步计算上限。
    - 运行时能力集合：对每个静态实例读取 Firmware CRC_CAPABILITIES 只读快照，不修改 CRC 硬件状态。
  steps:
    - 静态实例选择：从 Capability 取得全部 CRC 逻辑实例并要求至少存在一个实例。
    - 运行时能力读取：逐实例执行只读 CAPABILITIES_GET，取得 API、Feature、Mode、IRQ 与限制。
    - 模式一致性检查：比较静态 modes 与 Runtime modes，要求集合完全一致。
    - Feature与IRQ检查：确认 Runtime 基础 Feature 完整且 IRQ Source bitmask 只包含 BUS/LENGTH/CHECK 三类稳定事件。
    - 限制一致性检查：比较 FIFO Threshold 上限，并确认同步 calculate 上限在有效范围内。
    - 实例闭合：确认每个静态实例均存在 Runtime Service，汇总全部实例快照形成报告证据。
  observations:
    - 运行时能力端点：CRC_CAPABILITIES 返回 API/Feature/Mode/IRQ/Limit；它是目标侧只读设备能力快照，不冒充单个硬件寄存器。
    - 静态路由事实：实例与 Capability 来自当前芯片 Profile，仅用于执行门禁，不作为硬件 PASS。
  pass_criteria:
    - 实例完整性：至少存在一个 CRC 实例且所有静态实例都有 Runtime Service。
    - 模式一致性：Static 与 Runtime CRC8/16/32 模式集合完全一致。
    - 能力合法性：基础 Feature、IRQ bits、FIFO Threshold 上限和同步计算限制均合法且无未知能力位。
timeout: 单次 Target 请求使用平台统一有界 deadline
cleanup: []
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 仅需 DUT 控制链路}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_modes, label: 静态声明模式, source: oracle, role: expected, format: text}
  - {key: actual_modes, label: CRC_CAPABILITIES实际模式, source: dut, role: actual, format: text}
  - {key: actual_irq_events, label: CRC_CAPABILITIES IRQ能力, source: dut, role: actual, format: hex32}
  - {key: actual_max_calculate_bytes, label: CRC_CAPABILITIES同步计算上限, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P0_002
case_name: CRC8/16/32基础计算测试
report_feature: |-
  1. CRC8/16/32 Kernel运算
  2. CRC8/16/32 Result Width
p_level: P0
feature_refs: [CRC_F_002, CRC_F_015]
method:
  inputs:
    - 固定向量矩阵：CRC8、CRC16、CRC32 各一组历史固定 Payload、Polynomial、Seed、RefIn/RefOut、ByteSwap/XorOut 配置。
    - 双重Oracle：历史固定 Expected 先由独立 PC CRC Reference Model 复核，防止 DUT 与软件同错。
  steps:
    - 参数实例选择：取得当前 CRC8/16/32 配置、Payload 与历史固定 Expected。
    - Golden复核：PC Reference 按稳定 Byte Stream 语义计算 Expected，并先与历史固定值精确比较。
    - 资源准备：把当前 Payload 写入对齐 Resource Buffer。
    - CRC配置：Enable 模块并写入当前 Kernel、Polynomial、Seed 与变换参数。
    - 硬件计算：执行有界 CALCULATE，取得 RESULT.CRC 与 LENGTH.REMAINING_INPUT_COUNT。
    - 独立读回：再次读取 RESULT.CRC，避免只依赖命令返回值。
    - 结果判定：比较 Actual/Readback/Golden，检查 Remaining=0，并按三种 Kernel 汇总结果。
  observations:
    - 硬件结果：读取 RESULT.CRC，期望等于当前历史固定 Expected 与 PC Golden；证明 Kernel 运算和自然宽度结果正确。
    - 输入消费终态：读取 LENGTH.REMAINING_INPUT_COUNT，期望=0；证明本轮 Payload 已完整消费。
  pass_criteria:
    - Oracle一致：PC Golden 与历史固定 Expected 精确一致。
    - 数据正确：RESULT.CRC 与独立 Expected 精确一致，独立 Result Readback 同值。
    - 终态完整：LENGTH.REMAINING_INPUT_COUNT=0，CRC8/16/32 三个参数实例全部通过。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放本Case Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_crc, label: PC/固定向量期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
  - {key: result_readback, label: RESULT.CRC独立读回, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P0_003
case_name: CRC模块启停与恢复测试
report_feature: |-
  1. CRC Module Enable/Disable控制
p_level: P0
feature_refs: [CRC_F_001]
method:
  inputs:
    - 固定配置：使用一组 CRC32 Polynomial/Seed/ByteSwap 配置。
    - 双轮输入：两份相同长度但内容不同的确定性 Payload，各自具有独立 PC Golden。
  steps:
    - 双轮准备：生成两份不同 Payload 与对应 Expected，并写入独立 Resource。
    - 第一轮配置：Enable CRC 并写入完整 CRC32 配置。
    - 第一轮计算：执行 CALCULATE，读取 RESULT.CRC 与 LENGTH.REMAINING_INPUT_COUNT。
    - 中间关闭：显式 Disable CRC，结束第一轮 Module 生命周期。
    - 第二轮重新配置：重新 Enable 并重新下发同一完整配置，不继承上一轮软件状态。
    - 第二轮计算：对第二份不同 Payload 执行 CALCULATE并读取 Result/Length。
    - 恢复判定：两轮 Actual 分别与各自 Golden 比较，确认 Remaining=0 且第二轮不是旧 Result 残留。
  observations:
    - 第一轮结果：RESULT.CRC 期望等于 first Golden，LENGTH.REMAINING_INPUT_COUNT 期望=0。
    - 第二轮结果：重新 Enable 后 RESULT.CRC 期望等于 second Golden，且第二轮输入与第一轮不同。
  pass_criteria:
    - 第一轮正确：first Actual=first Golden 且 Remaining=0。
    - 重新进入正确：Disable 后重新 Enable/Configure 的 second Actual=second Golden 且 Remaining=0。
    - 状态隔离：两份输入不同，第二轮结论不能由上一轮 Result 残留满足。
timeout: 所有CRC操作使用统一有界 deadline
cleanup: [最终Disable CRC, 释放本Case Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: first_expected_crc, label: 第一轮期望CRC, source: oracle, role: expected, format: hex32}
  - {key: first_actual_crc, label: 第一轮RESULT.CRC, source: dut, role: actual, format: hex32}
  - {key: second_expected_crc, label: 第二轮期望CRC, source: oracle, role: expected, format: hex32}
  - {key: second_actual_crc, label: 第二轮RESULT.CRC, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_001
case_name: CRC多项式配置测试
report_feature: |-
  1. CRC Polynomial配置
p_level: P1
feature_refs: [CRC_F_003]
method:
  inputs:
    - Polynomial矩阵：CRC32 固定 Seed/Payload 下参数化 0x04C11DB7、0x1EDC6F41、0xA833982B。
    - 独立Oracle：每个 Polynomial 由 PC Reference 单独计算 Expected。
  steps:
    - 参数选择：取得本轮 Polynomial 并构造仅该字段变化的 CRC32 配置。
    - Golden计算：PC 用相同 Payload/Seed 和当前 Polynomial 生成独立 Expected。
    - 资源准备：写入固定 Payload Resource。
    - 硬件配置：Enable CRC 并配置当前 Polynomial。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 LENGTH.REMAINING_INPUT_COUNT。
    - 参数判定：比较 Result/Golden 并要求 Remaining=0；三个 Polynomial 各自独立形成结果。
  observations:
    - 硬件结果：RESULT.CRC 期望等于当前 Polynomial 的独立 Golden；证明 Polynomial 真实参与硬件运算。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：三个Polynomial参数实例全部执行。
    - 结果正确性：每个RESULT.CRC精确等于对应PC Golden。
    - 输入消费：每轮LENGTH.REMAINING_INPUT_COUNT=0。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: polynomial, label: 当前Polynomial, source: dut_config, role: config, format: hex32}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_002
case_name: CRC初始值配置测试
report_feature: |-
  1. CRC Initial Seed配置
p_level: P1
feature_refs: [CRC_F_004]
method:
  inputs:
    - Seed矩阵：CRC32 固定 Polynomial/Payload 下参数化 0x00000000、0xFFFFFFFF、0x13579BDF。
    - 独立Oracle：每个 Seed 由 PC Reference 单独计算 Expected。
  steps:
    - 参数选择：取得当前 Seed 并构造仅 Initial Value 变化的配置。
    - Golden计算：PC 用固定 Payload/Polynomial 和当前 Seed 生成 Expected。
    - 资源准备：写入固定 Payload Resource。
    - 硬件配置：Enable CRC 并配置当前 Seed。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 LENGTH.REMAINING_INPUT_COUNT。
    - 参数判定：比较 Result/Golden 并要求 Remaining=0；三个 Seed 各自独立通过。
  observations:
    - 硬件结果：RESULT.CRC 期望等于当前 Seed 的独立 Golden；证明 Initial Seed 真实参与硬件运算。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：三个Seed参数实例全部执行且不依赖前一轮状态。
    - 结果正确性：每个RESULT.CRC精确等于对应PC Golden。
    - 输入消费：每轮LENGTH.REMAINING_INPUT_COUNT=0。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: initial_value, label: 当前Initial Seed, source: dut_config, role: config, format: hex32}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_003
case_name: CRC输入字节交换测试
report_feature: |-
  1. CRC ByteSwap输入变换
p_level: P1
feature_refs: [CRC_F_005]
method:
  inputs:
    - 参数矩阵：CRC16/CRC32 × ByteSwap Off/On，共4个参数实例。
    - 非对称Payload：使用不会因字节重复而掩盖交换效果的固定 Byte 序列。
    - 独立Oracle：PC Reference 按实际访问单元和 ByteSwap 语义计算 Expected。
  steps:
    - 参数选择：取得当前 CRC16/32 模式和 ByteSwap 开关。
    - Golden计算：按当前自然访问宽度处理完整单元，尾部 Byte 不跨界交换。
    - 资源准备：把非对称 Payload 写入对齐 Resource。
    - CRC配置：Enable 并下发模式、Polynomial、Seed 与 ByteSwap。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 Remaining Count。
    - 数据判定：Actual 与当前独立 Golden 精确比较，要求 Remaining=0。
    - 覆盖汇总：确认 CRC16/32 的 Off/On 四组都执行，不以“结果互不相等”代替精确Oracle。
  observations:
    - 硬件结果：RESULT.CRC 期望等于当前 ByteSwap 语义的 PC Golden。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：四个模式/开关参数实例全部执行。
    - 结果正确性：每组RESULT.CRC精确等于对应Golden。
    - 尾部语义：每轮Remaining=0，尾部Byte不被错误跨单元交换。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: mode, label: CRC模式, source: dut_config, role: config, format: text}
  - {key: byte_swap, label: ByteSwap配置, source: dut_config, role: config, format: bool}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_004
case_name: CRC输入位反转测试
report_feature: |-
  1. CRC RefIn位反转
p_level: P1
feature_refs: [CRC_F_006]
method:
  inputs:
    - RefIn矩阵：固定CRC32配置与Payload，仅参数化 RefIn Off/On。
    - 独立Oracle：PC Reference 对每个输入 Byte 按当前 RefIn 选择执行8-bit reflection。
  steps:
    - 参数选择：取得 RefIn Off/On 并保持其余配置固定。
    - Golden计算：PC 对相同 Payload 生成当前 RefIn 的精确 Expected。
    - 资源准备：写入固定 Payload Resource。
    - CRC配置：Enable并配置当前 RefIn。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 Remaining Count。
    - 结果判定：Actual与Golden精确比较并要求Remaining=0；两组参数均独立执行。
  observations:
    - 硬件结果：RESULT.CRC 期望等于逐Byte reflection后的独立Golden。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：RefIn Off/On两个实例全部执行。
    - 结果正确性：两组RESULT.CRC分别精确等于对应Golden，不以结果差异代替Oracle。
    - 输入消费：两轮Remaining=0。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: ref_in, label: RefIn配置, source: dut_config, role: config, format: bool}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_005
case_name: CRC输出位反转测试
report_feature: |-
  1. CRC RefOut位反转
p_level: P1
feature_refs: [CRC_F_007]
method:
  inputs:
    - RefOut矩阵：固定CRC16配置，参数化 RefOut Off/On。
    - 非整双字节Payload：15-byte输入同时保留真实尾部Byte路径。
    - 独立Oracle：PC Reference 在Kernel结束后按16-bit宽度执行RefOut。
  steps:
    - 参数选择：取得 RefOut Off/On，固定 CRC16 其余参数。
    - Golden计算：PC 对15-byte输入生成当前 RefOut 的 Expected。
    - 资源准备：写入非整双字节长度 Payload。
    - CRC配置：Enable并配置当前 RefOut。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 Remaining Count。
    - 结果判定：Actual等于Expected、结果不超16-bit且Remaining=0。
  observations:
    - 硬件结果：RESULT.CRC 期望等于16-bit RefOut Golden且有效值不超当前自然宽度。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：RefOut Off/On两个实例全部执行且各自精确匹配Golden。
    - 结果宽度：RESULT.CRC保持CRC16自然宽度。
    - 输入消费：Remaining=0，RefOut不改变输入消费语义。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: ref_out, label: RefOut配置, source: dut_config, role: config, format: bool}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_006
case_name: CRC输出异或测试
report_feature: |-
  1. CRC XorOut输出异或
p_level: P1
feature_refs: [CRC_F_008]
method:
  inputs:
    - XorOut矩阵：固定CRC16 Kernel，参数化 ALL_ZERO 与 ALL_ONE。
    - 独立Oracle：PC Reference 在最终16-bit结果上应用0x0000或0xFFFF XOR。
  steps:
    - 参数选择：取得当前 XorOut 并固定其余 CRC16 配置。
    - Golden计算：PC 生成当前 XorOut 的精确 Expected。
    - 资源准备：写入固定 CRC16 Payload。
    - CRC配置：Enable并配置当前 XorOut。
    - 硬件计算：执行 CALCULATE，读取 RESULT.CRC 与 Remaining Count。
    - 结果判定：Actual等于Expected、不超16-bit且Remaining=0；两种XorOut均执行。
  observations:
    - 硬件结果：RESULT.CRC 期望等于当前自然宽度XOR后的Golden。
    - 输入消费：LENGTH.REMAINING_INPUT_COUNT 期望=0。
  pass_criteria:
    - 参数覆盖：ALL_ZERO/ALL_ONE两个参数实例全部执行。
    - 结果正确性：两组RESULT.CRC分别精确等于对应Golden且不污染高位。
    - 输入消费：两轮Remaining=0。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: xor_out, label: XorOut配置, source: dut_config, role: config, format: text}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: LENGTH剩余输入事务数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_007
case_name: CRC非整字节长度与LENGTH读回测试
report_feature: |-
  1. CRC非整访问单元Byte长度
  2. CRC LENGTH配置/读回
p_level: P1
feature_refs: [CRC_F_009, CRC_F_010]
method:
  inputs:
    - 长度矩阵：CRC32执行8/9/10/11-byte，CRC16执行8/9-byte，覆盖整单元和1/2/3-byte remainder。
    - 事务计数Oracle：Expected Input Count = 完整自然宽度访问单元数 + 尾部Byte数。
    - 数据Oracle：每个长度使用确定性Payload并由PC Reference独立计算CRC Expected。
  steps:
    - 参数选择：取得当前Mode/Byte Length并生成对应Payload与CRC Golden。
    - 资源准备：创建满足当前模式对齐要求的Resource并写入完整Byte Stream。
    - CRC配置：Enable并配置当前CRC16/32模式。
    - LENGTH编程：按Byte Length执行DATA_LENGTH_SET，再立即读取LENGTH.REMAINING_INPUT_COUNT。
    - LENGTH判定：把硬件读回与模式对应Expected Input Count精确比较。
    - 硬件计算：执行CALCULATE，读取RESULT.CRC与计算后Remaining Count。
    - 结果判定：Actual等于Golden、计算后Remaining=0，并汇总6个长度参数实例。
  observations:
    - LENGTH编程读回：读取 LENGTH.REMAINING_INPUT_COUNT，期望等于完整访问单元数+remainder Byte事务数；证明Byte Length到硬件事务计数的配置语义。
    - 硬件结果：读取 RESULT.CRC，期望等于当前非整长度Byte Stream的PC Golden。
    - 计算终态：CALCULATE后再次读取LENGTH.REMAINING_INPUT_COUNT，期望=0。
  pass_criteria:
    - 组合覆盖：六个模式/长度实例全部真实执行。
    - 长度编程：每个programmed_input_count精确等于Expected Input Count。
    - 结果闭合：每个RESULT.CRC精确等于独立Golden，计算后Remaining=0且未通过补零规避remainder。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_input_count, label: 期望LENGTH事务数, source: oracle, role: expected, format: decimal}
  - {key: programmed_input_count, label: LENGTH编程硬件读回, source: dut, role: actual, format: decimal}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_008
case_name: CRC自动长度重载测试
report_feature: |-
  1. CRC Auto Length Reload模式
p_level: P1
feature_refs: [CRC_F_011]
method:
  inputs:
    - ALR配置：CRC32、Auto Length Reload开启，显式配置一次64-byte Length。
    - 双轮输入：两份64-byte、内容不同的确定性Payload，各自具有独立PC Golden。
  steps:
    - 双轮准备：生成两份不同Payload及各自Expected并写入独立Resource。
    - CRC配置：Enable、配置ALR并只执行一次DATA_LENGTH_SET(64)。
    - 第一轮计算：对第一份Payload执行CALCULATE并读取RESULT.CRC与Reload后的LENGTH。
    - 第一轮判定：Actual等于first Golden，Reload后的Input Count=16。
    - 第二轮计算：不重新写Length，直接对第二份不同Payload执行CALCULATE。
    - 第二轮观测：读取第二轮RESULT.CRC与Reload后的LENGTH。
    - 连续性判定：second Actual=second Golden且Count=16，排除上一轮Result或手工重写Length造成的假通过。
  observations:
    - 两轮硬件结果：每轮 RESULT.CRC 分别期望等于各自独立Golden。
    - 自动重载状态：两轮完成后 LENGTH.REMAINING_INPUT_COUNT 均期望自动恢复为16个32-bit输入事务。
  pass_criteria:
    - 首轮状态：第一轮Result=first Golden且Remaining=16。
    - 次轮状态：第二轮未重写Length仍Result=second Golden且Remaining=16。
    - 状态隔离：两份Payload不同，第二轮结果不能由旧Result残留满足。
timeout: CRC Driver统一有界 deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: first_expected_crc, label: 第一轮PC Golden, source: oracle, role: expected, format: hex32}
  - {key: first_actual_crc, label: 第一轮RESULT.CRC, source: dut, role: actual, format: hex32}
  - {key: second_expected_crc, label: 第二轮PC Golden, source: oracle, role: expected, format: hex32}
  - {key: second_actual_crc, label: 第二轮RESULT.CRC, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_009
case_name: CRC结果校验匹配测试
report_feature: |-
  1. CRC CHECK匹配
p_level: P1
feature_refs: [CRC_F_016]
method:
  inputs:
    - 确定性输入：固定CRC32配置与确定性Payload。
    - CHECK Oracle：PC独立计算当前Payload的正确CRC，并把该Expected写入CHECK。
  steps:
    - Golden准备：PC计算当前Payload的独立Expected。
    - 资源准备：写入确定性Payload。
    - CRC配置：Enable、开启Result Check并清除旧IRQ Pending。
    - CHECK配置：把正确Expected写入CHECK硬件配置。
    - 硬件计算：执行CALCULATE并读取RESULT.CRC及当前IRQ Raw/Status。
    - 匹配判定：Result=Expected且IRQ_RAW.CHECK_ERROR=0、IRQ_STATUS.CHECK_ERROR=0。
  observations:
    - 计算结果：RESULT.CRC期望等于独立Expected。
    - CHECK错误Raw：IRQ_RAW.CHECK_ERROR期望=False；证明匹配路径没有形成原始CHECK错误。
    - CHECK错误Status：IRQ_STATUS.CHECK_ERROR期望=False；证明匹配路径没有有效CHECK错误。
  pass_criteria:
    - 结果正确性：RESULT.CRC精确等于PC Golden。
    - 原始中断状态：IRQ_RAW.CHECK_ERROR=False。
    - 有效中断状态：IRQ_STATUS.CHECK_ERROR=False，不要求历史Service Last Event参与本Case证明。
timeout: CRC Driver和IRQ查询使用统一有界 deadline
cleanup: [清除本Case可能产生的CHECK_ERROR, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: check_error_raw, label: 校验错误原始状态, source: dut, role: actual, format: bool}
  - {key: check_error_status, label: 校验错误有效状态, source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_010
case_name: CRC校验错误中断测试
report_feature: |-
  1. CRC CHECK_ERROR IRQ中断
  2. CRC IRQ Delivery投递
p_level: P1
feature_refs: [CRC_F_017, CRC_F_025]
method:
  inputs:
    - 确定性输入：固定CRC32 Payload与配置，由PC Reference生成正确Expected。
    - 错误CHECK：使用Expected翻转最低1 bit得到确定不匹配的CHECK值。
  steps:
    - 资源与Golden准备：写入Payload并计算独立Expected/wrong CHECK。
    - IRQ会话建立：Enable CRC，清旧Pending，Enable并Unmask CHECK_ERROR，记录before Event Count。
    - CHECK配置：把wrong CHECK写入硬件。
    - 错误刺激：执行一次正常CRC计算，使正确Result与错误CHECK发生硬件比较。
    - 当前硬件观测：读取IRQ_RAW/IRQ_STATUS当前值；ISR可能已经清除硬件Pending，因此该值不代替Delivery证据。
    - ISR证据读取：读取Service event_count、ISR Last Event和ISR Last Raw。
    - 结果判定：Result仍等于PC Golden，Event Count+1且ISR latch/last_raw仅为CHECK_ERROR。
  observations:
    - 硬件结果：RESULT.CRC期望等于PC Golden；错误比较不能破坏CRC计算结果。
    - 当前寄存器状态：IRQ_RAW.CHECK_ERROR与IRQ_STATUS.CHECK_ERROR保留本次读取真实值，允许ISR已清Pending。
    - ISR投递证据：ISR.LATCHED.CHECK_ERROR与ISR.LAST_RAW.CHECK_ERROR期望只包含CHECK_ERROR，event_count_delta期望=1。
  pass_criteria:
    - 结果正确性：RESULT.CRC精确等于独立Golden。
    - 事件计数：event_count_delta=1。
    - 事件纯度：ISR Last Event=CHECK_ERROR且ISR Last Raw=CHECK_ERROR，不混入BUS/LENGTH错误源。
timeout: IRQ等待使用平台统一有界 deadline
cleanup: [Disable/清理本Case申请的CHECK_ERROR会话, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: CRC IRQ可到达CPU, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: event_count_delta, label: Service IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: isr_latched_event, label: 校验错误中断锁存, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CRC_P1_011
case_name: CRC FIFO DMA请求水位测试
report_feature: |-
  1. CRC FIFO Threshold阈值
p_level: P1
feature_refs: [CRC_F_013]
method:
  inputs:
    - 阈值矩阵：至少选择两个合法FIFO_TRHD值并覆盖水位边界两侧。
    - DMA刺激：使用Capability映射的CRC输入DMA Request和IR端点，不绑定ET6801地址或Request ID。
  steps:
    - 能力确认：确认目标芯片公开FIFO_TRHD范围、CRC DMA输入路由和独立dma_req或fifo_cnt Observer。
    - 测试准备：复位CRC、DMA与Resource Pool，准备固定Payload和独立CRC Golden。
    - 低水位配置：配置第一组FIFO_TRHD并启动受控DMA输入。
    - 低水位观测：在边界两侧采集fifo_cnt与dma_req，记录Request置位和撤销位置。
    - 高水位配置：复位后仅修改FIFO_TRHD，使用相同Payload和DMA配置重复刺激。
    - 高水位观测：再次采集边界两侧fifo_cnt与dma_req，确认边界随Threshold移动。
    - 结果校验：等待DMA完成并比较RESULT.CRC与独立Golden，排除Request水位测试破坏数据路径。
    - 证据汇总：保存Threshold、fifo_cnt、dma_req、DMA完成状态和CRC结果的结构化证据。
  observations:
    - 水位边界：独立Observer返回同一时刻的fifo_cnt与dma_req。
    - DMA闭环：DMA通道完成且输入长度完整消费。
    - CRC结果：RESULT.CRC与独立PC Golden一致。
  pass_criteria:
    - 请求置位：每组Threshold下fifo_cnt<=FIFO_TRHD时dma_req=1。
    - 请求撤销：每组Threshold下fifo_cnt>FIFO_TRHD时dma_req=0。
    - 边界可迁移：修改FIFO_TRHD后Request翻转边界按配置同步移动。
    - 数据正确：DMA完成且最终CRC结果等于独立Golden。
timeout: 统一有界deadline，Observer必须在同一目标侧原子窗口采样
cleanup: [复位CRC与DMA, 复位Resource Pool]
resources: {minimum_level: R0, full_coverage_level: R0, board: 需暴露CRC fifo_cnt或dma_req独立Observer, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [计划Canonical Evidence + fifo_cnt/dma_req边界轨迹]
failure_observations:
  - {key: fifo_threshold, label: FIFO_TRHD配置值, source: dut_config, role: config, format: decimal}
  - {key: fifo_count, label: FIFO实际占用数, source: dut, role: actual, format: decimal}
  - {key: dma_request, label: CRC DMA Request实际电平, source: dut, role: actual, format: bool}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, crc_fifo_request_observer_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_012
case_name: CRC FIFO溢出与恢复测试
report_feature: |-
  1. CRC FIFO Overflow状态
p_level: P1
feature_refs: [CRC_F_014]
method:
  inputs:
    - 溢出刺激：CRC32固定配置、Threshold=1、目标端原子连续7次0x12345678写入。
    - 恢复向量：重新Enable后使用8-byte正常Payload和独立PC Golden。
  steps:
    - 第一轮配置：Enable CRC并设置Threshold=1。
    - 溢出前观测：读取FIFO.OVERFLOW，期望=False。
    - 紧凑刺激：目标端一次原子Burst连续执行7次32-bit输入写入。
    - 溢出后观测：读取FIFO.OVERFLOW，期望=True。
    - 生命周期隔离：Disable溢出轮，重新准备正常恢复Payload与Golden。
    - 恢复配置：重新Enable并重新下发CRC配置。
    - 恢复计算：执行正常CALCULATE，读取RESULT.CRC与LENGTH.REMAINING_INPUT_COUNT。
    - 恢复判定：Overflow完成False→True转换，恢复Result=Golden且Remaining=0；不宣称精确FIFO物理深度。
  observations:
    - Overflow转换：FIFO.OVERFLOW在刺激前期望=False、刺激后期望=True。
    - 恢复结果：RESULT.CRC期望等于恢复轮PC Golden。
    - 恢复终态：LENGTH.REMAINING_INPUT_COUNT期望=0。
  pass_criteria:
    - 溢出触发：FIFO.OVERFLOW由False精确转换为True。
    - 恢复结果：重新Enable后的RESULT.CRC精确等于恢复Golden。
    - 恢复闭合：恢复Remaining=0且旧Overflow不破坏后续正常计算；本Case不闭合CRC_F_012物理深度。
timeout: Burst与恢复计算均使用统一有界deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: overflow_before, label: 刺激前FIFO.OVERFLOW, source: dut, role: actual, format: bool}
  - {key: overflow_after, label: 刺激后FIFO.OVERFLOW, source: dut, role: actual, format: bool}
  - {key: recovery_expected_crc, label: 恢复轮PC Golden, source: oracle, role: expected, format: hex32}
  - {key: recovery_actual_crc, label: 恢复轮RESULT.CRC, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_013
case_name: CRC中断强制、投递与关闭测试
report_feature: |-
  1. CRC IRQ Source Enable/Disable控制
  2. CRC IRQ Force强制
  3. CRC IRQ Delivery投递
p_level: P1
feature_refs: [CRC_F_020, CRC_F_022, CRC_F_025]
method:
  inputs:
    - IRQ Source矩阵：BUS_ERROR、LENGTH_ERROR、CHECK_ERROR三类稳定Source。
    - 最小CRC配置：CRC8固定配置，仅用于建立合法Module状态，不参与错误Oracle。
  steps:
    - Source准备：Enable CRC，清旧Pending，对当前Source执行Enable并Unmask，记录before Event Count。
    - Enable刺激：软件Force当前Source。
    - Delivery观测：读取Service Event Count、ISR Last Event和ISR Last Raw。
    - Enable判定：要求Event Count恰好+1且ISR latch/last_raw只包含当前Source。
    - Source关闭：Clear旧Pending并Disable当前Source，使CPU Delivery通路失效。
    - Disable刺激：对同一已Disable Source再次执行新的Force。
    - Disable观测：读取IRQ_RAW当前值与Service Event Count；Raw可反映Force刺激，但Event Count必须不增加。
    - 恢复清理：Clear第二阶段Pending，三个Source分别完成同一Enable/Disable证明。
  observations:
    - Enable投递：ISR.LATCHED.<Source>与ISR.LAST_RAW.<Source>期望只包含当前Source，event_count_delta期望=1。
    - Disable反证：再次Force后Service disabled_event_count_delta期望=0；证明Source Disable阻断真实CPU Delivery。
    - Disable阶段Raw：IRQ_RAW.<Source>保留真实硬件读取值，用于证明Force刺激与Delivery控制不是同一事实。
  pass_criteria:
    - 事件覆盖：三类Source在Enable/Unmask时均各产生一次准确Delivery。
    - 禁用语义：每个Source Disable后再次Force均不增加Event Count。
    - 事件纯度：ISR latch/last_raw不混入其他Source，三个参数实例全部通过。
timeout: IRQ请求和Snapshot均使用平台统一有界deadline
cleanup: [Clear本Case产生的目标Pending, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: CRC IRQ可到达CPU, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: event_count_delta, label: Enable阶段IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: delivered_isr_event, label: Enable阶段ISR Latch, source: dut, role: actual, format: hex32}
  - {key: disabled_event_count_delta, label: Disable阶段IRQ事件增量, source: service, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_014
case_name: CRC中断清除测试
report_feature: |-
  1. CRC IRQ Clear清除
p_level: P1
feature_refs: [CRC_F_023]
method:
  inputs:
    - 单一Source：BUS_ERROR。
    - Mask条件：Source保持Enable但Mask，保证Force只形成Raw而不进入CPU回调。
  steps:
    - CRC与IRQ准备：Enable CRC，清旧Pending，Enable并Mask BUS_ERROR，记录before Event Count。
    - Pending刺激：Force BUS_ERROR。
    - Clear前观测：读取IRQ_RAW.BUS_ERROR与IRQ_STATUS.BUS_ERROR。
    - Clear动作：对BUS_ERROR执行精确IRQ Clear。
    - Clear后观测：再次读取同一Raw/Status端点。
    - Delivery检查：比较Clear前后Event Count，确认Mask和Clear期间没有新增CPU Delivery。
    - 结果判定：Raw由True变False、Status始终False且Event Count不增加。
  observations:
    - Clear前Raw：IRQ_RAW.BUS_ERROR期望=True。
    - Clear前Status：IRQ_STATUS.BUS_ERROR期望=False，因为Source处于Mask状态。
    - Clear后状态：IRQ_RAW.BUS_ERROR=False且IRQ_STATUS.BUS_ERROR=False。
  pass_criteria:
    - 清除前状态：Clear前Raw仅包含BUS_ERROR且Status=0。
    - 清除后状态：Clear后Raw=0、Status=0。
    - 清除副作用：Event Count与基线相同，Clear本身不制造新的IRQ Delivery。
timeout: 单次IRQ命令与Snapshot使用平台统一有界deadline
cleanup: [Clear目标IRQ, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: raw_before_clear, label: Clear前IRQ_RAW.BUS_ERROR, source: dut, role: actual, format: bool}
  - {key: status_before_clear, label: Clear前IRQ_STATUS.BUS_ERROR, source: dut, role: actual, format: bool}
  - {key: raw_after_clear, label: Clear后IRQ_RAW.BUS_ERROR, source: dut, role: actual, format: bool}
  - {key: status_after_clear, label: Clear后IRQ_STATUS.BUS_ERROR, source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_015
case_name: CRC中断屏蔽与Raw状态测试
report_feature: |-
  1. CRC IRQ Mask/Unmask控制
  2. CRC IRQ RAW/STATUS状态
p_level: P1
feature_refs: [CRC_F_021, CRC_F_024]
method:
  inputs:
    - 单一Source：LENGTH_ERROR。
    - 两阶段条件：第一阶段Enable+Mask，第二阶段Clear后Unmask并重新Force。
  steps:
    - Mask阶段准备：Enable CRC，清旧Pending，Enable并Mask LENGTH_ERROR，记录baseline Event Count。
    - Mask阶段刺激：Force LENGTH_ERROR。
    - Mask阶段观测：读取IRQ_RAW/IRQ_STATUS与Event Count。
    - Mask阶段判定：要求Raw=True、Status=False且Event Count不变。
    - 阶段隔离：Clear第一阶段Pending并Unmask同一Source。
    - Unmask阶段刺激：重新Force一个新的LENGTH_ERROR。
    - Unmask阶段观测：读取Service Event Count、ISR Last Event/Last Raw及当前Raw/Status。
    - Unmask判定：要求Event Count+1且ISR latch/last_raw只包含LENGTH_ERROR，证明新事件真实Delivery。
  observations:
    - Mask阶段：IRQ_RAW.LENGTH_ERROR期望=True，IRQ_STATUS.LENGTH_ERROR期望=False，event_count_delta期望=0。
    - Unmask Delivery：ISR.LATCHED.LENGTH_ERROR与ISR.LAST_RAW.LENGTH_ERROR期望仅包含目标Source，event_count_delta期望=1。
    - 当前Raw/Status：ISR可能清除Pending，Unmask阶段寄存器读值保留真实事实但不代替ISR Delivery证据。
  pass_criteria:
    - 屏蔽阶段：Mask阶段Raw=True、Status=False、Event Count无增量。
    - 解除屏蔽：Clear后重新Unmask/Force形成一次新Delivery，Event Count恰好+1。
    - 事件隔离：ISR Last Event/Last Raw仅为LENGTH_ERROR，第二阶段不复用第一阶段Pending。
timeout: IRQ请求和Snapshot使用平台统一有界deadline
cleanup: [Clear目标IRQ, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: CRC IRQ可到达CPU, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: masked_raw_status, label: Mask阶段IRQ_RAW.LENGTH_ERROR, source: dut, role: actual, format: bool}
  - {key: masked_effective_status, label: Mask阶段IRQ_STATUS.LENGTH_ERROR, source: dut, role: actual, format: bool}
  - {key: unmasked_event_count_delta, label: Unmask阶段IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: unmasked_isr_event, label: Unmask阶段ISR Latch, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_016
case_name: CRC长度错误中断测试
report_feature: |-
  1. CRC LENGTH_ERROR IRQ中断
  2. CRC IRQ Delivery投递
p_level: P1
feature_refs: [CRC_F_018, CRC_F_025]
method:
  inputs:
    - 基础配置：CRC32固定配置。
    - 错误刺激：DATA_LENGTH=0后执行一次合法32-bit输入写入0x12345678。
  steps:
    - IRQ准备：Enable CRC，清旧Pending，Enable并Unmask LENGTH_ERROR，记录before Event Count。
    - Length配置：把DATA_LENGTH明确设置为0。
    - 合法宽度刺激：通过Test Driver执行一次32-bit输入写入，避免访问宽度错误混入。
    - 当前硬件观测：读取IRQ_RAW.LENGTH_ERROR与IRQ_STATUS.LENGTH_ERROR当前值。
    - ISR证据读取：读取Event Count、ISR Last Event与ISR Last Raw。
    - Source隔离：确认ISR latch/last_raw只包含LENGTH_ERROR，不包含BUS/CHECK。
    - 结果判定：event_count_delta=1且ISR证据精确匹配LENGTH_ERROR。
  observations:
    - 当前寄存器：IRQ_RAW.LENGTH_ERROR与IRQ_STATUS.LENGTH_ERROR保存真实读取值；ISR可能已清Pending。
    - ISR投递：ISR.LATCHED.LENGTH_ERROR与ISR.LAST_RAW.LENGTH_ERROR期望只包含LENGTH_ERROR。
    - Service计数：event_count_delta期望=1。
  pass_criteria:
    - 事件计数：Event Count恰好增加一次。
    - 事件类型：ISR Last Event=LENGTH_ERROR且ISR Last Raw=LENGTH_ERROR。
    - 错误归因：合法32-bit输入宽度确保本Case错误原因是Length语义而非BUS_ERROR。
timeout: IRQ请求和Snapshot使用平台统一有界deadline
cleanup: [Clear/Disable本Case申请的LENGTH_ERROR会话, Disable CRC]
resources: {minimum_level: R0, full_coverage_level: R0, board: CRC IRQ可到达CPU, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: expected_irq_event, label: 期望中断源, source: oracle, role: expected, format: text}
  - {key: event_count_delta, label: Service IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: isr_latched_event, label: 长度错误中断锁存, source: dut, role: actual, format: hex32}
  - {key: isr_last_raw, label: 长度错误ISR原始锁存, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P1_018
case_name: CRC非法访问宽度BUS_ERR与恢复测试
report_feature: |-
  1. CRC BUS_ERROR状态
  2. CRC IRQ Delivery投递
p_level: P1
feature_refs: [CRC_F_019, CRC_F_025]
method:
  inputs:
    - 基础配置：CRC8固定配置，LENGTH=1。
    - 因果对照：先执行合法8-bit输入0x12，再执行非法32-bit输入0x12345678。
    - 恢复向量：重新Enable后执行一组正常CRC8 Payload并用PC Reference生成Golden。
  steps:
    - IRQ准备：Enable CRC，清旧Pending，Enable并Unmask BUS_ERROR。
    - 合法基线起点：设置LENGTH=1并读取legal_before Event Count。
    - 合法8-bit刺激：执行8-bit输入，读取legal_after Raw/Status/Event Count并确认无BUS_ERROR增量。
    - 非法32-bit刺激：重新设置LENGTH=1，对CRC8输入端点执行32-bit访问。
    - 错误证据读取：读取当前Raw/Status、Event Count和ISR Last Event/Last Raw。
    - 错误判定：要求非法阶段Event Count+1且ISR latch/last_raw只包含BUS_ERROR。
    - 生命周期恢复：Disable错误轮，重新Enable/Configure并执行正常CRC8计算。
    - 恢复判定：恢复RESULT.CRC=PC Golden且LENGTH.REMAINING_INPUT_COUNT=0。
  observations:
    - 合法基线：IRQ_RAW.BUS_ERROR=False、IRQ_STATUS.BUS_ERROR=False且legal_event_count_delta=0；证明合法8-bit访问不会触发目标错误。
    - 非法访问Delivery：event_count_delta=1，ISR.LATCHED.BUS_ERROR与ISR.LAST_RAW.BUS_ERROR只包含BUS_ERROR。
    - 恢复结果：RESULT.CRC期望等于恢复Golden，LENGTH.REMAINING_INPUT_COUNT期望=0。
  pass_criteria:
    - 合法访问基线：合法8-bit基线Event Count不增加且BUS_ERROR Raw/Status均不置位。
    - 非法访问事件：非法32-bit访问恰好形成一次BUS_ERROR Delivery且不混入LENGTH/CHECK错误。
    - 错误恢复：重新Enable后的CRC8 Result精确等于Golden且Remaining=0。
timeout: IRQ等待与恢复计算均使用统一有界deadline
cleanup: [清除BUS_ERROR并Disable本CaseIRQ会话, Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: CRC IRQ可到达CPU, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: legal_event_count_delta, label: 合法8-bit阶段IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: event_count_delta, label: 非法32-bit阶段IRQ事件增量, source: service, role: actual, format: decimal}
  - {key: recovery_expected_crc, label: 恢复轮PC Golden, source: oracle, role: expected, format: hex32}
  - {key: recovery_actual_crc, label: 恢复轮RESULT.CRC, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P2_001
case_name: CRC DMA输入等价性测试
report_feature: |-
  1. CRC DMA M2P输入
p_level: P2
feature_refs: [CRC_F_026]
method:
  inputs:
    - 模式矩阵：CRC8/CRC16/CRC32，对应DMA 8/16/32-bit自然宽度。
    - 确定性数据：32-byte确定性Resource Payload，每个模式由PC Reference生成独立CRC Golden。
    - Route事实：CRC输入端点、DMA Request、Controller和Interface全部来自Capability/Execution Mapping。
  steps:
    - Route与输入准备：解析已审核DMA Route，创建32-byte源Resource并写入Payload。
    - CRC配置：Enable CRC，配置当前Kernel并设置本轮Data Length。
    - DMA配置：Enable Controller，配置SYSCTRL Route和Memory-to-Peripheral Channel。
    - 传输启动：启动当前Channel并等待硬件回到Free终态。
    - CRC观测：DMA完成后读取RESULT.CRC与LENGTH.REMAINING_INPUT_COUNT。
    - Golden比较：Actual与当前模式PC Golden精确比较，并检查Channel Free与Remaining=0。
    - 参数汇总：CRC8/16/32三组均执行，DMA Width必须等于模式自然宽度且Case不硬编码芯片地址/Request ID。
  observations:
    - DMA终态：DMA_CHANNEL_STATUS.FREE期望=True；证明本次Memory-to-Peripheral传输已完成。
    - CRC输入消费：LENGTH.REMAINING_INPUT_COUNT期望=0。
    - DMA输入结果：RESULT.CRC期望等于独立PC Golden；证明DMA数据真实进入CRC计算路径。
  pass_criteria:
    - 通道终态：三个模式实例的DMA Channel最终均Free。
    - 输入消费：三个模式Remaining均为0。
    - 结果正确性：三个RESULT.CRC均精确等于各自PC Golden，DMA Width与Kernel自然宽度一致。
timeout: DMA Driver与CRC Driver各自使用统一有界deadline
cleanup: [停止并Deconfigure DMA Channel, Release SYSCTRL Route, Disable CRC与DMA Controller, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无外部连接要求, bench: 需要芯片内部DMA执行映射}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: mode, label: CRC模式, source: dut_config, role: config, format: text}
  - {key: channel_free, label: DMA通道空闲状态, source: dut, role: actual, format: bool}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P3_001
case_name: CRC确定性长稳测试
report_feature: |-
  1. CRC8/16/32 Kernel运算
p_level: P3
feature_refs: [CRC_F_002]
method:
  inputs:
    - 固定20轮生成规则：每轮由index确定17~257-byte长度、Payload Seed、Polynomial、Initial Value、RefIn/RefOut。
    - 独立Oracle：每轮配置与Payload均由PC Reference生成对应Golden。
  steps:
    - 长稳资源准备：创建可复用最大Resource并Enable CRC，整个Case复用同一Module会话。
    - 轮次生成：按index生成本轮长度、Payload和完整CRC32配置。
    - Golden计算：PC Reference生成本轮Expected。
    - 本轮执行：覆盖Resource、重新Configure并执行CALCULATE。
    - 本轮观测：在断言前保存RESULT.CRC与LENGTH.REMAINING_INPUT_COUNT以及轮次配置。
    - 单轮判定：Actual=Expected且Remaining=0，首个失败立即停止后续轮次。
    - Evidence闭合：无论中途PASS/FAIL，最终Artifact只发布一次当前已形成的全部records和completed_rounds。
  observations:
    - 本轮结果：RESULT.CRC期望等于当前轮PC Golden。
    - 本轮终态：LENGTH.REMAINING_INPUT_COUNT期望=0。
    - 完成度：最终Artifact completed_rounds期望=20；失败时保留首个失败前已形成的全部轮次。
  pass_criteria:
    - 压力覆盖：20轮全部执行且每轮RESULT.CRC=对应Golden。
    - 输入消费：20轮Remaining均为0。
    - 完成计数：completed_rounds=20，失败轮参数和结果可由最终单次Snapshot复现。
timeout: 每轮CRC计算使用统一有界deadline且总轮数固定20
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: round_index, label: 当前轮次, source: stimulus, role: actual, format: decimal}
  - {key: expected_crc, label: 当前轮PC Golden, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: 当前轮RESULT.CRC, source: dut, role: actual, format: hex32}
  - {key: remaining_input_count, label: 当前轮LENGTH剩余数, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P3_002
case_name: CRC CPU输入路径吞吐表征测试
report_feature: |-
  1. CRC CPU Path Cycle Count周期
p_level: P3
feature_refs: [CRC_F_027]
method:
  inputs:
    - 基础配置：固定CRC32配置。
    - 长度矩阵：256-byte与4096-byte确定性Payload，每档重复3次。
    - 独立Oracle：每档Payload由PC Reference生成Golden；周期来自目标侧DWT计数边界。
  steps:
    - 资源与配置：Enable CRC并配置固定CRC32算法。
    - 当前长度准备：生成256或4096-byte Payload、PC Golden并写入Resource。
    - 目标计时执行：对当前长度调用Firmware原子Timed Calculate三次。
    - 单次观测：每次保存RESULT.CRC、measured_bytes与TIMING.CYCLE_COUNT。
    - 单次判定：Result=Golden、measured_bytes=请求长度、elapsed_cycles>0。
    - 中位数汇总：确认每档恰有3个有效样本，分别计算median_cycles_256/4096。
    - 性能表征判定：4096-byte中位周期>256-byte中位周期；最终Artifact只发布一次完整records和median。
  observations:
    - 功能结果：RESULT.CRC期望等于当前长度PC Golden。
    - 目标周期：TIMING.CYCLE_COUNT期望>0，来源为目标侧计数而非PC wall-clock。
    - 测量边界：measured_bytes期望等于请求长度；两档各3个样本形成中位数。
  pass_criteria:
    - 结果正确性：六次RESULT.CRC全部精确等于各自Golden。
    - 测量有效性：六次measured_bytes均等于请求长度且TIMING.CYCLE_COUNT>0。
    - 相对性能：两档各3个有效样本且median_cycles_4096>median_cycles_256，不设置跨芯片绝对阈值。
timeout: 每次Timed Calculate使用CRC统一有界deadline
cleanup: [Disable CRC, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 目标侧DWT可用, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: length_bytes, label: 测试长度, source: stimulus, role: actual, format: decimal}
  - {key: expected_crc, label: 软件期望CRC, source: oracle, role: expected, format: hex32}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: elapsed_cycles, label: TIMING.CYCLE_COUNT, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: CRC_P3_003
case_name: CRC DMA输入路径吞吐表征测试
report_feature: |-
  1. CRC DMA Start-to-IRQ Cycle Count周期
p_level: P3
feature_refs: [CRC_F_028]
method:
  inputs:
    - DMA执行环境：固定CRC32配置与已审核CRC DMA Execution Mapping。
    - 长度矩阵：256-byte与4096-byte确定性Payload，每档重复3次。
    - 独立Oracle：每档由PC Reference生成Golden；周期来自DMA目标侧Timed Start到完成IRQ边界。
  steps:
    - 输入准备：为两档长度创建独立Resource、Payload和PC Golden。
    - 公共资源配置：Enable CRC与DMA Controller，并配置SYSCTRL CRC DMA Route。
    - 当前长度配置：设置CRC Length并配置当前DMA Memory-to-Peripheral Channel。
    - 计时IRQ准备：清DMA旧IRQ结果，Enable当前Channel TRANSFER_DONE并执行Timed Start。
    - 完成等待：等待DMA_TIMING.COMPLETE与DMA_CHANNEL_STATUS.FREE。
    - 结果观测：读取RESULT.CRC与TIMING.CYCLE_COUNT，并在下一轮前撤销当前IRQ/Channel配置。
    - 单轮判定：Timing Complete、Channel Free、elapsed_cycles>0且Result=Golden。
    - 汇总判定：两档各3个有效样本，median_cycles_4096>median_cycles_256；最终Artifact只发布一次Route、records与median。
  observations:
    - DMA计时终态：DMA_TIMING.COMPLETE=True且DMA_CHANNEL_STATUS.FREE=True。
    - CRC结果：RESULT.CRC期望等于当前长度PC Golden。
    - 目标周期：TIMING.CYCLE_COUNT期望>0，属于当前Channel Start-to-IRQ目标侧计时事实。
  pass_criteria:
    - DMA完成状态：六次DMA均Timing Complete且Channel Free。
    - 结果与计时：六次RESULT.CRC均精确等于Golden且TIMING.CYCLE_COUNT>0。
    - 相对性能：两档各3个有效样本且median_cycles_4096>median_cycles_256，不减历史固定ISR修正常数。
timeout: DMA Timing与Channel终态等待均使用统一有界deadline
cleanup: [Disable DMA TRANSFER_DONE IRQ, Deconfigure DMA Channel, Release SYSCTRL Route, Disable CRC与DMA Controller, 释放Resource]
resources: {minimum_level: R0, full_coverage_level: R0, board: 目标侧DWT和DMA IRQ可用, bench: 需要芯片内部DMA执行映射}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
  - {key: timing_complete, label: DMA_TIMING.COMPLETE, source: dut, role: actual, format: bool}
  - {key: channel_free, label: DMA通道空闲状态, source: dut, role: actual, format: bool}
  - {key: actual_crc, label: RESULT.CRC实际值, source: dut, role: actual, format: hex32}
  - {key: elapsed_cycles, label: TIMING.CYCLE_COUNT, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=27; PARTIAL_ADAPTATION=2 | ADAPTED=23; IMPLEMENTATION_GAP=1 | `CRC_F_012 dynamic_fifo_depth_proof_gap`; `CRC_F_013 crc_fifo_request_observer_gap`; 当前精确SHA HIL未执行 | `ET6801_crc.md` |

## 5. Common Gap / Evolution

- `CRC_F_012 FIFO Physical Depth`：硬件与静态资料支持FIFO存在及阈值上限，但当前没有精确动态测得物理深度。在取得独立安全刺激与明确Depth Oracle前保持 `dynamic_fifo_depth_proof_gap`，不得由 `CRC_P1_011/P1_012` 冒充闭合。
- `CRC_F_013 FIFO Threshold`：权威RTL语义是DMA Request水位，不是CRC Result更新门限。当前平台没有独立暴露`fifo_cnt/dma_req`，因此`CRC_P1_011`保持PLAN和`crc_fifo_request_observer_gap`，不得恢复第4/5次Result变化的错误断言。
- 当前规划但尚未成为公共 Formal Case 的 Case：`CRC_P1_011`，等待`crc_fifo_request_observer_gap`闭合。
- 新芯片出现时先映射本文件已有 Feature/Case；不得复制芯片专用公共测试代码。
- 当前无真机环境时，只能闭合 Source / Design / Canonical Evidence / Report 软件链；当前精确SHA FPGA/Silicon HIL 必须保持 `NOT_EXECUTED / NOT_VERIFIED`。

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  CRC_P0_001:
    summary: "CRC静态实例与Runtime Service能力一致。"
    fields:
      - {source: artifact, path: instances, label: Runtime实例数量, format: count, aggregate: same}
  CRC_P0_002:
    summary: "CRC8/16/32基础计算结果与独立期望一致且输入完整消费。"
    fields:
      - {source: measurement, path: mode, label: CRC模式, format: text, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: PC/固定向量Expected, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: RESULT.CRC实际值, format: hex32, aggregate: distinct}
      - {source: observation, path: remaining_input_count, label: LENGTH剩余输入事务数, format: decimal, aggregate: same}
  CRC_P0_003:
    summary: "CRC关闭后重新使能的两轮运算均保持正确。"
    fields:
      - {source: measurement, path: first_expected_crc, label: 第一轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: first_actual_crc, label: 第一轮RESULT.CRC, format: hex32, aggregate: same}
      - {source: measurement, path: second_expected_crc, label: 第二轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: second_actual_crc, label: 第二轮RESULT.CRC, format: hex32, aggregate: same}
  CRC_P1_001:
    summary: "三个Polynomial参数实例均得到对应正确CRC结果。"
    fields:
      - {source: measurement, path: polynomial, label: 多项式配置, format: hex32, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
      - {source: observation, path: remaining_input_count, label: LENGTH剩余数, format: decimal, aggregate: same}
  CRC_P1_002:
    summary: "三个Initial Seed参数实例均得到对应正确CRC结果。"
    fields:
      - {source: measurement, path: initial_value, label: 初始种子配置, format: hex32, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
      - {source: observation, path: remaining_input_count, label: LENGTH剩余数, format: decimal, aggregate: same}
  CRC_P1_003:
    summary: "CRC16/32 ByteSwap Off/On均与对应独立Golden一致。"
    fields:
      - {source: measurement, path: mode, label: CRC模式, format: text, aggregate: distinct}
      - {source: measurement, path: byte_swap, label: 字节交换配置, format: bool, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P1_004:
    summary: "RefIn Off/On逐Byte reflection均得到精确正确结果。"
    fields:
      - {source: measurement, path: ref_in, label: 输入位反转配置, format: bool, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P1_005:
    summary: "RefOut Off/On自然宽度输出reflection均得到正确结果。"
    fields:
      - {source: measurement, path: ref_out, label: 输出位反转配置, format: bool, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P1_006:
    summary: "XorOut ALL_ZERO/ALL_ONE均在CRC16自然宽度内得到正确结果。"
    fields:
      - {source: measurement, path: xor_out, label: 输出异或配置, format: text, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P1_007:
    summary: "非整访问单元Byte长度计算正确且LENGTH编程读回与预期事务数一致。"
    fields:
      - {source: measurement, path: length_bytes, label: 输入字节长度, format: decimal, aggregate: range, unit: byte}
      - {source: observation, path: programmed_input_count, label: 长度编程读回, format: decimal, aggregate: distinct}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P1_008:
    summary: "Auto Length Reload下两轮不同Payload无需重写Length即可连续正确计算。"
    fields:
      - {source: measurement, path: first_expected_crc, label: 第一轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: first_actual_crc, label: 第一轮RESULT.CRC, format: hex32, aggregate: same}
      - {source: measurement, path: second_expected_crc, label: 第二轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: second_actual_crc, label: 第二轮RESULT.CRC, format: hex32, aggregate: same}
  CRC_P1_009:
    summary: "CHECK匹配时CRC结果正确且CHECK_ERROR Raw/Status均不置位。"
    fields:
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: same}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: same}
      - {source: observation, path: check_error_raw, label: 校验错误原始状态, format: bool, aggregate: same}
      - {source: observation, path: check_error_status, label: 校验错误有效状态, format: bool, aggregate: same}
  CRC_P1_010:
    summary: "CHECK mismatch形成一次CHECK_ERROR真实IRQ且CRC计算结果仍正确。"
    fields:
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: same}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: same}
      - {source: measurement, path: event_count_delta, label: IRQ事件增量, format: decimal, aggregate: same}
      - {source: observation, path: isr_latched_event, label: 校验错误中断锁存, format: hex32, aggregate: same}
  CRC_P1_012:
    summary: "FIFO Overflow由False转True且重新使能后的正常CRC计算恢复正确。"
    fields:
      - {source: observation, path: overflow_before, label: 刺激前FIFO.OVERFLOW, format: bool, aggregate: same}
      - {source: observation, path: overflow_after, label: 刺激后FIFO.OVERFLOW, format: bool, aggregate: same}
      - {source: measurement, path: recovery_expected_crc, label: 恢复轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: recovery_actual_crc, label: 恢复轮RESULT.CRC, format: hex32, aggregate: same}
  CRC_P1_013:
    summary: "三类IRQ Source在Enable时可真实Delivery，Disable后再次Force不再增加事件计数。"
    fields:
      - {source: measurement, path: event_count_delta, label: Enable阶段事件增量, format: decimal, aggregate: same}
      - {source: observation, path: delivered_isr_event, label: Enable阶段ISR Latch, format: hex32, aggregate: distinct}
      - {source: measurement, path: disabled_event_count_delta, label: Disable阶段事件增量, format: decimal, aggregate: same}
      - {source: observation, path: disabled_force_raw, label: Disable阶段IRQ_RAW, format: bool, aggregate: distinct}
  CRC_P1_014:
    summary: "BUS_ERROR Pending在Mask状态下可精确Clear且不会制造新Delivery。"
    fields:
      - {source: observation, path: raw_before_clear, label: Clear前IRQ_RAW.BUS_ERROR, format: bool, aggregate: same}
      - {source: observation, path: status_before_clear, label: Clear前IRQ_STATUS.BUS_ERROR, format: bool, aggregate: same}
      - {source: observation, path: raw_after_clear, label: Clear后IRQ_RAW.BUS_ERROR, format: bool, aggregate: same}
      - {source: observation, path: status_after_clear, label: Clear后IRQ_STATUS.BUS_ERROR, format: bool, aggregate: same}
  CRC_P1_015:
    summary: "Mask阶段保留Raw并抑制Delivery，Clear后Unmask的新事件可真实到达CPU。"
    fields:
      - {source: observation, path: masked_raw_status, label: Mask阶段IRQ_RAW.LENGTH_ERROR, format: bool, aggregate: same}
      - {source: observation, path: masked_effective_status, label: Mask阶段IRQ_STATUS.LENGTH_ERROR, format: bool, aggregate: same}
      - {source: measurement, path: unmasked_event_count_delta, label: Unmask阶段事件增量, format: decimal, aggregate: same}
      - {source: observation, path: unmasked_isr_event, label: Unmask阶段ISR Latch, format: hex32, aggregate: same}
  CRC_P1_016:
    summary: "LENGTH=0后合法32-bit输入形成一次LENGTH_ERROR真实IRQ。"
    fields:
      - {source: measurement, path: expected_irq_event, label: 期望中断源, format: text, aggregate: same}
      - {source: measurement, path: event_count_delta, label: IRQ事件增量, format: decimal, aggregate: same}
      - {source: observation, path: isr_latched_event, label: 长度错误中断锁存, format: hex32, aggregate: same}
      - {source: observation, path: isr_last_raw, label: 长度错误ISR原始锁存, format: hex32, aggregate: same}
  CRC_P1_018:
    summary: "合法8-bit输入不报BUS_ERROR，非法32-bit访问产生一次BUS_ERROR且恢复计算正确。"
    fields:
      - {source: measurement, path: legal_event_count_delta, label: 合法8-bit阶段事件增量, format: decimal, aggregate: same}
      - {source: measurement, path: event_count_delta, label: 非法32-bit阶段事件增量, format: decimal, aggregate: same}
      - {source: measurement, path: recovery_expected_crc, label: 恢复轮Expected, format: hex32, aggregate: same}
      - {source: observation, path: recovery_actual_crc, label: 恢复轮RESULT.CRC, format: hex32, aggregate: same}
  CRC_P2_001:
    summary: "DMA按CRC自然宽度完成输入传输并得到与独立Golden一致的CRC结果。"
    fields:
      - {source: measurement, path: mode, label: CRC模式, format: text, aggregate: distinct}
      - {source: observation, path: channel_free, label: DMA通道空闲状态, format: bool, aggregate: same}
      - {source: measurement, path: expected_crc, label: 软件期望CRC, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_crc, label: 硬件CRC结果, format: hex32, aggregate: distinct}
  CRC_P3_001:
    summary: "20轮确定性CRC32配置/长度变化全部形成可复现长稳证据。"
    fields:
      - {source: artifact, path: completed_rounds, label: 已完成轮数, format: decimal, aggregate: same}
      - {source: artifact, path: records, label: 轮次记录数, format: count, aggregate: same}
  CRC_P3_002:
    summary: "CPU路径六次目标周期测量均保持功能正确并形成两档中位周期。"
    fields:
      - {source: artifact, path: records, label: 有效测量记录数, format: count, aggregate: same}
      - {source: artifact, path: median_cycles, label: 256/4096-byte中位周期, format: text, aggregate: same}
  CRC_P3_003:
    summary: "DMA路径六次Start-to-IRQ目标周期测量均保持Channel终态和CRC结果正确。"
    fields:
      - {source: artifact, path: records, label: 有效测量记录数, format: count, aggregate: same}
      - {source: artifact, path: median_cycles, label: 256/4096-byte中位周期, format: text, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
