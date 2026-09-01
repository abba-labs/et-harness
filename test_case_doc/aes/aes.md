# AES Stable IP Contract

<!-- Evidence closure sync 2026-08-19: 26 Formal Cases are aligned to register/field/hardware-endpoint observations, monotonic Evidence, and reviewer-facing report fields. No physical register addresses are used in this public contract. -->

> 本文件只定义跨芯片稳定 Feature / Case / Report Contract；芯片实际寄存器名、IRQ、SDK 和历史硬件证据位于同目录 `<CHIP>_aes.md`。
> 公共 Case 只写稳定寄存器/字段语义，如 `STATUS.FINISH`、`RESULT_DOUT[0..3]`；物理地址不得进入本文件。
> Formal Case 前置隔离统一遵循 `R210`：除纯只读能力查询外，第一次 Feature 配置前由 Case 显式复位参与 IP，并最后复位 Resource Pool；本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

- IP：`aes`。
- Feature/Case ID 绑定稳定语义，不绑定芯片；不同芯片的实际寄存器名由 `<CHIP>_aes.md` 映射。
- Hardware Observation 必须说明具体寄存器/Field/硬件端点、实际值和期望；`produced_bytes`、Golden、参数等软件事实与硬件 Observation 分开表达。
- 每个 Case 只收集足以证明 Feature 的最小充分 Evidence；Artifact 是完整 Snapshot，不作为增量日志。

### 0.1 Stable Runtime Contract

| Contract | Stable definition |
|---|---|
| Firmware Service | `service_id=0x0103`，`api_version=1` |
| Command range | `0x0001`～`0x001D`；Request/Response 长度由 PC/Firmware Contract 双向冻结 |
| AES byte model | Key、IV、Input、Output 使用 canonical byte sequence |
| Independent Golden | PC 使用 `Cryptodome.Cipher.AES`；不得用 DUT roundtrip 代替独立 Oracle |
| Evidence boundary | Software Gate 只证明实现；FPGA/Silicon HIL 才能形成对应硬件运行结论 |

### 0.2 Stable Service Command Contract

| Command | ID | Request bytes | Response bytes |
|---|---:|---:|---:|
| `CAPABILITIES_GET` | `0x0001` | 0 | 32 |
| `ENABLE` | `0x0002` | 0 | 0 |
| `DISABLE` | `0x0003` | 0 | 0 |
| `CONFIGURE` | `0x0004` | 12 | 0 |
| `KEY_SET` | `0x0005` | 36 | 0 |
| `IV_SET` | `0x0006` | 16 | 0 |
| `IV_GET` | `0x0007` | 0 | 16 |
| `DATA_LENGTH_SET` | `0x0008` | 8 | 0 |
| `DATA_LENGTH_GET` | `0x0009` | 0 | 8 |
| `PROCESS` | `0x000A` | 20 | 12 |
| `STATUS_GET` | `0x000B` | 0 | 8 |
| `STATUS_CLEAR` | `0x000C` | 4 | 0 |
| `IRQ_ENABLE` | `0x000D` | 4 | 0 |
| `IRQ_DISABLE` | `0x000E` | 4 | 0 |
| `IRQ_MASK` | `0x000F` | 4 | 0 |
| `IRQ_UNMASK` | `0x0010` | 4 | 0 |
| `IRQ_FORCE` | `0x0011` | 4 | 0 |
| `IRQ_CLEAR` | `0x0012` | 4 | 0 |
| `IRQ_SNAPSHOT_GET` | `0x0013` | 0 | 28 |
| `DMA_REQUEST_SET` | `0x0014` | 4 | 0 |
| `IRQ_TRANSFER_START` | `0x0015` | 20 | 0 |
| `IRQ_TRANSFER_STATUS_GET` | `0x0016` | 0 | 24 |
| `IRQ_TRANSFER_ABORT` | `0x0017` | 0 | 0 |
| `TIMED_PROCESS` | `0x0018` | 20 | 16 |
| `BLOCK_WRITE` | `0x0019` | 16 | 0 |
| `BLOCK_READ` | `0x001A` | 0 | 16 |
| `BLOCK_WRITE_DIRECT` | `0x001B` | 16 | 0 |
| `BLOCK_WRITE_PAIR_DIRECT` | `0x001C` | 32 | 0 |
| `BLOCK_WRITE_DISABLE_DIRECT` | `0x001D` | 16 | 0 |

所有多字节整数使用 little-endian；未知命令、非法长度和非法枚举必须失败关闭。Wire 语义变化必须同步 PC/Firmware Contract。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| AES_F_001 | AES Module Enable/Disable控制 | AES 模块使能、关闭和重新进入可用状态 | `AES_P0_003` |
| AES_F_002 | AES Encrypt/Decrypt方向 | 加密与解密方向 | `AES_P0_002` |
| AES_F_003 | AES-128/AES-256密钥 | 128-bit / 256-bit 密钥 | `AES_P0_002` |
| AES_F_004 | AES ECB/CBC/CTR模式 | ECB / CBC / CTR 三种工作模式 | `AES_P0_002` |
| AES_F_005 | AES NONE/ZERO/PKCS7 Padding填充 | ECB/CBC 加密末块填充方式 | `AES_P1_001` |
| AES_F_006 | AES CBC/CTR IV配置/读回 | CBC/CTR 初始向量配置和读回 | `AES_P1_002` |
| AES_F_007 | AES Data Length配置/读回 | 数据长度支持范围和单位由Capability声明；当前Case显式验证bit32高位读回 | `AES_P1_003` |
| AES_F_008 | AES Little/Big Endian字节序 | LITTLE/BIG 只改变硬件 32-bit word 装配；公共接口保持 canonical bytes | `AES_P1_004` |
| AES_F_009 | AES CTR Initial Counter计数 | CTR 初始 32-bit Counter 参与独立算法结果 | `AES_P1_005` |
| AES_F_010 | AES BUSY状态 | 当前Formal Case只证明 PROCESS 完成后的 BUSY=0 终态 | `AES_P1_003` |
| AES_F_011 | AES DIN_REQ状态 | 非DMA输入路径可提供可观测输入请求状态 | `AES_P1_006` |
| AES_F_012 | AES DOUT_REQ状态 | 非DMA输出路径可提供可观测输出请求状态 | `AES_P1_007` |
| AES_F_013 | AES FINISH状态 | 运算完成可形成稳定可读 FINISH 状态 | `AES_P1_008` |
| AES_F_014 | AES Status W1C清除 | 输入请求、输出请求和完成状态的请求消费/清除语义 | `AES_P1_006`, `AES_P1_007`, `AES_P1_008` |
| AES_F_015 | AES CPU Polling Block I/O路径 | CPU可通过稳定分组输入/输出路径完成数据搬运 | `AES_P0_002` |
| AES_F_016 | AES OUTPUT_CONFLICT IRQ中断 | 上一笔DMA输出仍处于Busy状态时产生下一笔AES结果可形成OUTPUT_CONFLICT事件 | `AES_P1_009` |
| AES_F_017 | AES KEY_MISSING IRQ中断 | 未装载 Key 时可形成 KEY_MISSING 事件 | `AES_P1_010` |
| AES_F_018 | AES IV_MISSING IRQ中断 | 需要 IV 的模式未装载 IV 时可形成 IV_MISSING 事件 | `AES_P1_011` |
| AES_F_019 | AES COMPLETE IRQ中断 | 正常完成可形成 COMPLETE 中断事件 | `AES_P1_012` |
| AES_F_020 | AES INCOMPLETE_DISABLE IRQ中断 | 结果未读取时关闭 AES 可形成 INCOMPLETE_DISABLE 事件 | `AES_P1_013` |
| AES_F_021 | AES DIN_REQ IRQ中断 | IRQ transfer 会话可由输入请求事件推进 | `AES_P1_014` |
| AES_F_022 | AES DOUT_REQ IRQ中断 | IRQ transfer 会话可由输出请求事件推进 | `AES_P1_014` |
| AES_F_023 | AES IRQ Source Enable/Disable控制 | Capability声明的AES中断源可独立使能 | `AES_P1_015` |
| AES_F_024 | AES IRQ Mask/Unmask控制 | AES中断源支持Mask/Unmask并保持RAW/STATUS语义 | `AES_P1_016` |
| AES_F_025 | AES IRQ Force强制 | 支持对目标AES中断源执行软件Force并形成投递证据 | `AES_P1_015` |
| AES_F_026 | AES IRQ Clear清除 | 支持对单个AES中断源执行精确Clear | `AES_P1_017` |
| AES_F_027 | AES IRQ RAW/STATUS状态 | Mask状态保留RAW并抑制STATUS/ISR，Clear后目标位归零 | `AES_P1_016`, `AES_P1_017` |
| AES_F_028 | AES IRQ Delivery投递 | 实际IRQ由Service latched/event_count等结构化事实证明 | `AES_P1_009`～`AES_P1_015` |
| AES_F_029 | AES Input/Output DMA Request Gate控制 | AES输入/输出DMA Request Gate控制真实请求是否传递 | `AES_P2_001` |
| AES_F_030 | AES DMA递增端点模式 | DMA通过四个递增32-bit端点完成AES输入/输出搬运 | `AES_P2_002` |
| AES_F_031 | AES DMA FIFO Endpoint模式 | DMA通过固定地址FIFO端点分阶段完成AES输入/输出搬运 | `AES_P2_003` |
| AES_F_032 | AES DMA/CPU Result等价 | DMA与CPU路径均以同一独立AES Golden为Oracle | `AES_P2_002`, `AES_P2_003` |
| AES_F_033 | AES CPU Path Cycle Count周期 | CPU路径由目标侧周期计数器表征256/1024-byte处理周期 | `AES_P3_002` |
| AES_F_034 | AES DMA Path Cycle Count周期 | DMA路径由输出Channel目标侧计时事件表征1024-byte传输周期 | `AES_P3_003` |
| AES_F_035 | AES Component Identity/Capability身份 | AES实例、模式、密钥长度、IRQ、DMA与处理上限由Capability和Runtime只读身份共同声明 | `AES_P0_001` |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| AES_P0_001 | P0 | AES代表实例静态映射与目标侧运行时能力门禁有效性 | AES身份与运行时能力门禁测试 | SPEC |
| AES_P0_002 | P0 | AES ECB/CBC/CTR × AES-128/256 × 加密/解密标准向量运算正确性 | AES标准向量加解密正确性测试 | SPEC |
| AES_P0_003 | P0 | AES关闭后重新使能、重新配置并连续两轮正确运算 | AES关闭后重新使能与恢复运算测试 | SPEC |
| AES_P1_001 | P1 | AES ECB/CBC 下 NONE/ZERO/PKCS7 填充在 15/16-byte 输入边界的输出长度与密文正确性 | AES ECB/CBC 填充输出契约测试 | SPEC |
| AES_P1_002 | P1 | AES CBC/CTR 两组 IV 的写入读回与密文变化正确性 | AES CBC/CTR IV读回与算法影响测试 | SPEC |
| AES_P1_003 | P1 | AES DATA_LENGTH bit32 高位读回与 32-byte 运算完成后 BUSY/FINISH 终态 | AES高位数据长度读回与运算终态测试 | SPEC |
| AES_P1_004 | P1 | AES LITTLE/BIG 32-bit word 字节序配置下 canonical 字节输出一致性 | AES LITTLE/BIG字节序 canonical 输出测试 | SPEC |
| AES_P1_005 | P1 | AES CTR 初始 32-bit Counter 变化对单块输出的正确影响 | AES CTR初始Counter运算测试 | SPEC |
| AES_P1_006 | P1 | AES 非DMA输入请求 DIN_REQ 在写块前后的状态变化与清除复核 | AES非DMA输入请求状态测试 | SPEC |
| AES_P1_007 | P1 | AES 非DMA输出请求 DOUT_REQ、块读取结果与清除复核 | AES非DMA输出请求与块读取测试 | SPEC |
| AES_P1_008 | P1 | AES 完整 PROCESS 后的 FINISH 置位、输出正确性与 W1C 清除 | AES FINISH状态置位与W1C清除测试 | SPEC |
| AES_P1_009 | P1 | AES上一笔输出DMA未完成时产生下一块结果，触发OUTPUT_CONFLICT IRQ并验证清除与恢复 | AES输出冲突IRQ触发与恢复测试 | SPEC |
| AES_P1_010 | P1 | AES 未装载 Key 时触发 KEY_MISSING IRQ 并可精确清除 | AES Key缺失IRQ触发与清除测试 | SPEC |
| AES_P1_011 | P1 | AES CBC 已装载 Key 但未装载 IV 时触发 IV_MISSING IRQ 并可精确清除 | AES IV缺失IRQ触发与清除测试 | SPEC |
| AES_P1_012 | P1 | AES 正常单块运算产生 COMPLETE IRQ、得到正确输出并可清除 | AES正常完成IRQ与清除测试 | SPEC |
| AES_P1_013 | P1 | AES 结果未读取时关闭模块产生 INCOMPLETE_DISABLE IRQ 并重新使能恢复运算 | AES未完成关闭IRQ与恢复运算测试 | SPEC |
| AES_P1_014 | P1 | AES IRQ 传输会话的 IDLE→COMPLETE 状态、输入/输出 Offset 推进与单块结果正确性 | AES IRQ传输会话状态与数据路径测试 | SPEC |
| AES_P1_015 | P1 | AES 5 个参数化 IRQ Source 的软件 Force 投递、ISR 锁存与清除 | AES IRQ Force投递与清除测试 | SPEC |
| AES_P1_016 | P1 | AES COMPLETE IRQ 在 Mask 时仅保留 RAW、Unmask 后真实投递与锁存 | AES IRQ Mask/Unmask语义测试 | SPEC |
| AES_P1_017 | P1 | AES 7 个参数化 IRQ Source 在 Mask 状态下 Force 后的 RAW 单 bit 精确清除 | AES IRQ单Source精确清除测试 | SPEC |
| AES_P2_001 | P2 | AES 双向 DMA Request Gate 关闭时阻塞传输、开启后完成传输 | AES DMA Request Gate传递测试 | SPEC |
| AES_P2_002 | P2 | AES DMA REGISTER 模式通过递增 32-bit 端点完成单块双向传输并得到正确密文 | AES DMA REGISTER模式双向传输测试 | SPEC |
| AES_P2_003 | P2 | AES DMA FIFO 模式通过固定地址端点分阶段完成单块双向传输并得到正确密文 | AES DMA FIFO模式双向传输测试 | SPEC |
| AES_P3_001 | P3 | AES 8 轮多模式/密钥确定性运行的结果正确性与轮次状态隔离 | AES八轮确定性与状态隔离测试 | SPEC |
| AES_P3_002 | P3 | AES CPU 路径 256/1024-byte TIMED_PROCESS 目标周期测量与功能正确性 | AES CPU路径目标周期测量测试 | SPEC |
| AES_P3_003 | P3 | AES FIFO 双向 DMA 1024-byte 传输的目标端周期测量与数据正确性 | AES DMA路径目标周期测量测试 | SPEC |

## 3. Machine-readable Case Contract

> `ET_CASE_SPEC` 是已注册且有真实 `test_*` 的 Formal Case。以下方法、Observation 和 Pass Criteria 是人工审核与代码实现的共同基线。

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P0_001
case_name: AES身份与运行时能力门禁测试
report_feature: |-
  1. AES Component Identity/Capability身份
p_level: P0
feature_refs: [AES_F_035]
method:
  inputs:
  - 能力来源：使用当前芯片 Capability 选择的 AES 代表实例与 semantic mapping。
  - 运行时能力：映射存在后只执行 AES_CAPABILITIES 只读查询，不修改 AES 运行状态。
  steps:
  - 静态实例选择：从 Capability 取得代表 AES 实例并检查 semantic mapping。
  - 缺失能力处理：semantic mapping 缺失时明确 SKIP，且不发送目标侧 AES 请求。
  - 运行时能力读取：通过 AES Driver 执行 CAPABILITIES_GET，取得目标侧能力快照。
  - API有效性检查：检查 api_version 大于 0。
  - Feature有效性检查：检查 features 非零并保留实际 Feature bitmask。
  - 块尺寸检查：检查 block_size_bytes=16，并记录 hardware_data_length_bits。
  - 门禁证据记录：记录实例编号、静态门禁结果和 AES_CAPABILITIES 实际快照。
  observations:
  - 运行时能力端点：读取 AES_CAPABILITIES，期望 api_version>0、features!=0、block_size_bytes=16；用于证明目标侧 AES Service 与代表实例可正常响应只读能力查询。
  - 静态映射事实：instance_id 与 semantic mapping 来自芯片 Capability，仅用于运行前路由，不冒充硬件寄存器反馈。
  pass_criteria:
  - 静态映射有效：代表实例存在且 semantic mapping 完整。
  - 运行时能力有效：AES_CAPABILITIES 返回有效 API、Feature bitmask 和 16-byte block size。
  - 无运行副作用：本 Case 不执行 Enable/Configure/Process 等状态修改。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 只恢复本Case实际获得或修改的AES状态
- 跨IP资源按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 按本Case声明资源执行。
  bench: 按本Case声明资源执行。
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_capability, label: AES_CAPABILITIES期望, source: oracle, role: expected, format: text}
- {key: actual_capability, label: AES_CAPABILITIES实际值, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P0_002
case_name: AES标准向量加解密正确性测试
report_feature: |-
  1. AES Encrypt/Decrypt方向
  2. AES-128/AES-256密钥
  3. AES ECB/CBC/CTR模式
  4. AES CPU Polling Block I/O路径
p_level: P0
feature_refs: [AES_F_002, AES_F_003, AES_F_004, AES_F_015]
method:
  inputs:
  - 参数覆盖矩阵：12组 NIST 固定向量，覆盖3种Mode×2种Key Size×2种Direction。
  - 模式参数与Golden：CBC/CTR使用对应IV/Counter；Expected由NIST固定值并用Cryptodome独立复核。
  steps:
  - 向量选择：取得当前 Mode、Key Size、Direction、Key、Input及所需IV/Counter。
  - 资源准备：按当前输入和期望输出长度准备独立 Source/Destination。
  - AES配置：Enable并配置Mode/Key Size/Direction，写入Key与需要的IV。
  - 运算启动：执行一次有界 PROCESS。
  - 硬件结果读取：从 RESULT_DOUT[0..3] 路径取得16-byte Actual，并读取 STATUS.FINISH。
  - Golden计算：PC以相同算法参数计算独立Golden并与NIST Expected交叉核对。
  - 结果判定：比较Actual/NIST/Golden，检查produced_bytes=16与FINISH=1，并按参数实例形成结果。
  observations:
  - 运算完成状态：读取 STATUS.FINISH，期望 FINISH=1；证明当前向量运算进入完成终态。
  - 硬件输出结果：读取 RESULT_DOUT[0..3] 形成Actual，期望与NIST Expected及PC Golden一致；证明算法结果正确。
  - 输出长度事实：produced_bytes期望16，属于协议结果，不作为寄存器Observation。
  pass_criteria:
  - 覆盖完整性：12个参数实例全部执行。
  - 数据正确性：Actual与NIST Expected及独立Golden逐字节一致。
  - 输出长度正确性：produced_bytes=16。
  - 硬件完成状态：STATUS.FINISH=1。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: PC/NIST Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
- {key: finish_status, label: STATUS.FINISH实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P0_003
case_name: AES关闭后重新使能与恢复运算测试
report_feature: |-
  1. AES Module Enable/Disable控制
p_level: P0
feature_refs: [AES_F_001]
method:
  inputs:
  - 算法与输入：固定AES-128/ECB/Encrypt与Key，准备两个不同16-byte输入。
  - Golden来源：每轮Expected均由独立AES Golden计算。
  steps:
  - 资源初始化：重置资源池并准备两轮独立输入/输出Buffer。
  - 第一轮配置：Enable AES，配置ECB并写Key。
  - 第一轮运算：执行PROCESS，读取RESULT_DOUT[0..3]与STATUS.FINISH并即时对照Golden。
  - 生命周期切换：第一轮完成后Disable AES。
  - 第二轮重建：重新Enable/Configure/Key，不继承上一轮运行状态。
  - 第二轮运算：执行PROCESS并再次读取RESULT_DOUT[0..3]与STATUS.FINISH。
  - 结果汇总：确认两轮均与各自Golden一致、produced_bytes=16且两组输出不同。
  observations:
  - 每轮完成状态：每轮读取 STATUS.FINISH，期望为1；证明重新进入后运算完成。
  - 每轮硬件输出：每轮从 RESULT_DOUT[0..3] 取得Actual，期望与该轮Golden一致。
  - 轮次隔离结果：两个不同输入的Actual应不同；该比较是软件判据，不是寄存器Observation。
  pass_criteria:
  - 数据正确性：两轮Actual均与各自Golden一致。
  - 输出与完成状态：两轮produced_bytes=16且FINISH=1。
  - 生命周期完整性：完成两轮Enable→Process→Disable。
  - 状态隔离：第二轮输出不复用第一轮结果。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: round_expected_output, label: 每轮PC Golden, source: oracle, role: expected, format: text}
- {key: round_actual_output, label: "每轮RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
- {key: round_finish_status, label: 每轮STATUS.FINISH实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_001
case_name: AES ECB/CBC 填充输出契约测试
report_feature: |-
  1. AES NONE/ZERO/PKCS7 Padding填充
p_level: P1
feature_refs: [AES_F_005]
method:
  inputs:
  - 参数矩阵：ECB/CBC；NONE使用16-byte，ZERO/PKCS7覆盖15/16-byte边界。
  - Golden与长度：Expected由独立AES Golden，Expected Length由公共输出长度规则计算。
  steps:
  - 参数选择：选择Mode/Padding/Input Length并生成确定性payload。
  - Golden准备：计算独立Golden和expected_output_length。
  - AES配置：Enable AES，配置Mode/Padding/Key，CBC同时写IV。
  - 运算启动：写入Source并执行PROCESS。
  - 硬件输出读取：从RESULT_DOUT[0..3]路径读取完整Actual。
  - 长度与数据比较：比较Actual与Golden、produced_bytes与Expected Length。
  - 参数汇总：10个参数实例分别形成独立结果。
  observations:
  - 硬件输出结果：读取 RESULT_DOUT[0..3] 形成Actual，期望与当前Padding参数的独立Golden一致。
  - 输出长度事实：produced_bytes期望等于expected_output_length，属于协议结果。
  pass_criteria:
  - 覆盖完整性：10个参数实例全部执行。
  - 数据正确性：Actual与独立Golden一致。
  - 输出长度正确性：produced_bytes精确等于Expected Length。
  - 边界契约：ZERO/PKCS7的15/16-byte输出长度符合公共规则。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: Padding独立Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_002
case_name: AES CBC/CTR IV读回与算法影响测试
report_feature: |-
  1. AES CBC/CTR IV配置/读回
p_level: P1
feature_refs: [AES_F_006]
method:
  inputs:
  - 模式与IV：CBC/CTR分别使用IV_A、IV_B，固定AES-128 Key与16-byte payload。
  - Golden来源：每个Mode/IV的Expected由独立AES Golden计算。
  steps:
  - 模式准备：选择CBC/CTR并建立独立AES生命周期。
  - IV配置：写入当前16-byte IV及Key。
  - IV硬件读回：读取IV[0..3]并与本次写入IV比较。
  - 运算执行：执行单块PROCESS并读取Actual。
  - Golden比较：将RESULT_DOUT[0..3] Actual与当前IV对应Golden比较。
  - 节点隔离：每个IV节点结束后Disable，再重新Enable完整配置。
  - 影响汇总：确认IV_A/IV_B读回正确、输出均正确且两组输出不同。
  observations:
  - IV寄存器读回：读取 IV[0..3] 的128-bit Readback，期望与写入IV一致。
  - 硬件输出结果：读取 RESULT_DOUT[0..3]，期望与当前Mode/IV的Golden一致；两组IV输出应不同。
  - 输出长度事实：produced_bytes=16，属于协议结果。
  pass_criteria:
  - IV读回正确：IV[0..3] Readback与写入值一致。
  - 数据正确性：每个IV的Actual与独立Golden一致。
  - 输出长度正确性：produced_bytes=16。
  - IV影响有效：同一Mode下IV_A与IV_B输出不同。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_value, label: 写入IV期望值, source: oracle, role: expected, format: text}
- {key: actual_value, label: "IV[0..3]实际读回", source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_003
case_name: AES高位数据长度读回与运算终态测试
report_feature: |-
  1. AES Data Length配置/读回
  2. AES BUSY状态
p_level: P1
feature_refs: [AES_F_007, AES_F_010]
method:
  inputs:
  - 高位长度：写入1<<32验证DATA_LENGTH bit32未截断。
  - 双块运算：AES-128/ECB/Encrypt处理32-byte payload，Expected由独立Golden计算。
  steps:
  - 能力检查：确认DATA_LENGTH至少33-bit。
  - 高位长度写入：Enable后写DATA_LENGTH=1<<32。
  - 长度硬件读回：读取DATA_LENGTH并与1<<32比较。
  - 生命周期重建：Disable后重新Enable并配置ECB/Key。
  - 双块运算：执行32-byte PROCESS并读取RESULT_DOUT路径Actual。
  - 终态读取：PROCESS完成后读取STATUS.BUSY和STATUS.FINISH。
  - 结果判定：检查Actual=Golden、produced_bytes=32、BUSY=0、FINISH=1。
  observations:
  - 数据长度读回：读取 DATA_LENGTH[1:0]，期望完整为1<<32。
  - BUSY完成终态：读取 STATUS.BUSY，期望0；不声称已观测运行中的BUSY=1。
  - FINISH完成终态：读取 STATUS.FINISH，期望1。
  - 硬件输出结果：RESULT_DOUT路径Actual期望与32-byte独立Golden一致。
  pass_criteria:
  - 高位长度读回：DATA_LENGTH读回=1<<32。
  - 数据正确性：32-byte Actual与Golden一致且produced_bytes=32。
  - BUSY终态：完成后STATUS.BUSY=0。
  - FINISH终态：完成后STATUS.FINISH=1。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_value, label: DATA_LENGTH期望值, source: oracle, role: expected, format: decimal}
- {key: actual_value, label: DATA_LENGTH实际读回, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_004
case_name: AES LITTLE/BIG字节序 canonical 输出测试
report_feature: |-
  1. AES Little/Big Endian字节序
p_level: P1
feature_refs: [AES_F_008]
method:
  inputs:
  - 判别输入：使用可区分32-bit word顺序的16-byte plaintext与固定Key。
  - 字节序参数：分别执行LITTLE/BIG；逻辑Expected均由canonical-byte Golden计算。
  steps:
  - 参数选择：选择LITTLE或BIG endian。
  - 资源准备：创建16-byte Source/Destination并写入判别输入。
  - AES配置：Enable并配置ECB/Encrypt/当前endian，写入Key。
  - 运算启动：执行单块PROCESS。
  - 硬件输出读取：从RESULT_DOUT[0..3]路径取得canonical Actual。
  - Golden比较：Actual与同一个独立canonical Golden比较。
  - 参数汇总：两个endian节点均独立配置并形成结果。
  observations:
  - 硬件输出结果：LITTLE/BIG均从 RESULT_DOUT[0..3] 取得canonical Actual，期望与同一Golden一致。
  - 字节序配置事实：ENDIAN来自配置输入，未读取CTRL.ENDIAN，不冒充硬件Readback。
  - 输出长度事实：produced_bytes=16。
  pass_criteria:
  - 参数覆盖完整：LITTLE/BIG均执行。
  - Canonical数据正确：两个节点Actual均与Golden一致。
  - 输出长度正确：produced_bytes=16。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: Canonical PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_005
case_name: AES CTR初始Counter运算测试
report_feature: |-
  1. AES CTR Initial Counter计数
p_level: P1
feature_refs: [AES_F_009]
method:
  inputs:
  - Counter组合：固定Key/WORK_IV/payload，参数化0xFCFDFEFF与0xFCFDFF00。
  - Golden来源：每个Counter对应Expected由独立CTR Golden计算。
  steps:
  - Counter选择：选择当前Counter并构造CTR配置。
  - 资源准备：创建16-byte Source/Destination。
  - CTR配置：Enable、配置Counter、写Key和WORK_IV。
  - 单块运算：执行PROCESS并读取Actual。
  - 完成状态读取：取得STATUS.FINISH。
  - 数据比较：RESULT_DOUT[0..3] Actual与当前Counter Golden比较。
  - 参数汇总：两个Counter节点分别记录produced_bytes与FINISH。
  observations:
  - 硬件输出结果：RESULT_DOUT[0..3] Actual期望与当前Counter Golden一致。
  - 运算完成状态：STATUS.FINISH期望1。
  - Counter配置事实：Counter来自配置输入，本Case不要求Counter寄存器读回。
  pass_criteria:
  - 参数覆盖完整：两个Counter均执行。
  - 数据正确性：Actual与对应Golden一致。
  - 输出长度正确：produced_bytes=16。
  - 硬件完成状态：STATUS.FINISH=1。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: CTR PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
- {key: finish_status, label: STATUS.FINISH实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_006
case_name: AES非DMA输入请求状态测试
report_feature: |-
  1. AES DIN_REQ状态
  2. AES Status W1C清除
p_level: P1
feature_refs: [AES_F_011, AES_F_014]
method:
  inputs:
  - 测试条件：AES-128/ECB/Encrypt+固定Key，配置完成后不提前写入输入。
  steps:
  - 等待输入配置：Enable后先设置16-byte数据长度，再配置ECB并写Key。
  - 写入前状态读取：读取STATUS.DIN_REQ。
  - 初始请求确认：确认DIN_REQ=1。
  - 输入块写入：通过BLOCK_WRITE写入16-byte block。
  - 写入后状态读取：再次读取STATUS.DIN_REQ。
  - 请求消费确认：确认DIN_REQ从1变为0。
  - 清除复核：显式Clear后再读STATUS.DIN_REQ，确认保持0且无残留。
  observations:
  - 输入请求置位：写入前读取 STATUS.DIN_REQ，期望1。
  - 请求消费状态：BLOCK_WRITE后读取 STATUS.DIN_REQ，期望0；1→0证明请求被消费/清除。
  - 清理复核：显式Clear后STATUS.DIN_REQ仍为0；该0→0只证明无残留。
  pass_criteria:
  - 写入前请求：STATUS.DIN_REQ=1。
  - 写入后请求：STATUS.DIN_REQ=0。
  - 清除后无残留：STATUS.DIN_REQ=0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_value, label: STATUS.DIN_REQ写入前期望, source: oracle, role: expected, format: bit_bool}
- {key: actual_value, label: STATUS.DIN_REQ写入前实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_007
case_name: AES非DMA输出请求与块读取测试
report_feature: |-
  1. AES DOUT_REQ状态
  2. AES Status W1C清除
p_level: P1
feature_refs: [AES_F_012, AES_F_014]
method:
  inputs:
  - 测试条件：AES-128/ECB/Encrypt+固定Key和16-byte block；Expected由独立Golden计算。
  steps:
  - AES配置：Enable后先设置16-byte数据长度，再配置ECB并写Key。
  - 输入刺激：BLOCK_WRITE写入一个完整block。
  - 读取前状态：读取STATUS.DOUT_REQ。
  - 输出请求确认：确认DOUT_REQ=1后执行BLOCK_READ。
  - 硬件输出比较：RESULT_DOUT[0..3] Actual与Golden比较。
  - 读取后状态：再次读取STATUS.DOUT_REQ并确认0。
  - 清除复核：显式Clear后再读DOUT_REQ，确认保持0。
  observations:
  - 输出请求置位：BLOCK_READ前STATUS.DOUT_REQ期望1。
  - 硬件输出结果：BLOCK_READ从RESULT_DOUT[0..3]取得Actual，期望与Golden一致。
  - 请求消费状态：读取后STATUS.DOUT_REQ期望0；显式Clear后仍为0。
  pass_criteria:
  - 读取前请求：STATUS.DOUT_REQ=1。
  - 输出数据正确：Actual与独立Golden一致。
  - 读取后请求：STATUS.DOUT_REQ=0。
  - 清除后无残留：STATUS.DOUT_REQ=0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: dout_req_before_read, label: STATUS.DOUT_REQ读取前实际值（期望=1）, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_008
case_name: AES FINISH状态置位与W1C清除测试
report_feature: |-
  1. AES FINISH状态
  2. AES Status W1C清除
p_level: P1
feature_refs: [AES_F_013, AES_F_014]
method:
  inputs:
  - 测试条件：AES-128/ECB/Encrypt+固定Key和16-byte block；Expected由独立Golden计算。
  steps:
  - 资源准备：创建单块Source/Destination。
  - AES配置：Enable、配置ECB并写Key。
  - 单块运算：执行PROCESS并读取Actual。
  - 清除前状态：读取STATUS.FINISH。
  - 输出与完成确认：Actual与Golden一致且FINISH=1。
  - W1C清除：对FINISH执行Clear。
  - 清除后状态：再次读取STATUS.FINISH并确认0。
  observations:
  - 硬件输出结果：RESULT_DOUT[0..3] Actual期望与Golden一致。
  - FINISH清除前：STATUS.FINISH期望1。
  - FINISH清除后：W1C后STATUS.FINISH期望0；1→0直接证明清除语义。
  pass_criteria:
  - 数据正确：Actual与Golden一致。
  - FINISH置位：Clear前STATUS.FINISH=1。
  - FINISH清除：Clear后STATUS.FINISH=0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
- {key: actual_state, label: STATUS.FINISH清除前实际值, source: dut, role: actual, format: bit_bool}
- {key: finish_after_clear, label: STATUS.FINISH清除后实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_009
case_name: AES输出冲突IRQ触发与恢复测试
report_feature: |-
  1. AES OUTPUT_CONFLICT IRQ中断
  2. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_016, AES_F_028]
method:
  inputs:
  - 冲突刺激：AES-128/ECB/Encrypt/FIFO DMA，输入DMA搬运2个block，输出DMA只接收1个block并在启动后暂停。
  - IRQ配置：目标Source=OUTPUT_CONFLICT，执行前Clear并Enable/Unmask。
  steps:
  - AES/IRQ配置：Enable AES、配置FIFO DMA/ECB/Key/32-byte长度并开启OUTPUT_CONFLICT。
  - 基线读取：取得触发前IRQ snapshot/event_count。
  - DMA路由：配置AES输入/输出DMAMUX Route和两条DMA Channel，先启动并暂停输出Channel。
  - 冲突刺激：开启AES双向DMA Request并启动输入Channel，使第一块输出DMA保持Busy时产生第二块结果。
  - 事件快照：读取IRQ_RAW/IRQ_STATUS/Service latched/event_count。
  - ISR判定：要求latched=OUTPUT_CONFLICT且event_count=baseline+1。
  - 目标清除：执行IRQ_CLEAR(OUTPUT_CONFLICT)。
  - 恢复复核：撤销DMA Route和Channel，复位AES后执行一次CPU PROCESS并与独立Golden比较。
  observations:
  - 冲突IRQ硬件视图：ISR确认后 IRQ_RAW.OUTPUT_CONFLICT 与 IRQ_STATUS.OUTPUT_CONFLICT 期望0。
  - ISR锁存证据：Service latch期望OUTPUT_CONFLICT且event_count=baseline+1。
  - 清除后状态：IRQ_CLEAR后IRQ_RAW.OUTPUT_CONFLICT期望0。
  - 恢复输出：AES复位后的CPU PROCESS输出必须等于独立Golden。
  pass_criteria:
  - 冲突事件锁存：latched=OUTPUT_CONFLICT且raw/status=0。
  - 事件计数：event_count=baseline+1。
  - IRQ清除：清除后目标RAW bit=0。
  - 错误恢复：复位后的CPU PROCESS输出精确等于独立Golden。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_state, label: OUTPUT_CONFLICT期望事件, source: oracle, role: expected, format: text}
- {key: actual_state, label: OUTPUT_CONFLICT ISR实际现场, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_010
case_name: AES Key缺失IRQ触发与清除测试
report_feature: |-
  1. AES KEY_MISSING IRQ中断
  2. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_017, AES_F_028]
method:
  inputs:
  - 缺Key条件：CRG复位隔离历史Key，配置AES-128/ECB/Encrypt但故意不Key Set。
  - IRQ配置：目标Source=KEY_MISSING并Enable/Unmask。
  steps:
  - 历史隔离：复位当前AES实例。
  - 缺Key配置：Enable、设置length/ECB但省略Key Set。
  - IRQ基线：Clear旧事件并读取baseline event_count。
  - 缺Key刺激：BLOCK_WRITE_DIRECT写入完整block。
  - 错误快照：读取IRQ_RAW/STATUS/latched/event_count。
  - 目标清除：IRQ_CLEAR(KEY_MISSING)。
  - 清除复核：确认RAW/STATUS/latched三个视图目标bit均为0。
  observations:
  - 缺Key硬件视图：ISR确认后IRQ_RAW.KEY_MISSING与IRQ_STATUS.KEY_MISSING期望0。
  - ISR锁存证据：Service latch期望KEY_MISSING且event_count=baseline+1。
  - 清除后状态：Clear后RAW/STATUS/latched中的KEY_MISSING均为0。
  pass_criteria:
  - KEY_MISSING锁存：latched=KEY_MISSING且raw/status=0。
  - 事件计数：event_count=baseline+1。
  - 精确清除：Clear后三个视图目标bit均为0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_state, label: KEY_MISSING期望事件, source: oracle, role: expected, format: text}
- {key: actual_state, label: KEY_MISSING ISR实际锁存, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_011
case_name: AES IV缺失IRQ触发与清除测试
report_feature: |-
  1. AES IV_MISSING IRQ中断
  2. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_018, AES_F_028]
method:
  inputs:
  - 缺IV条件：CRG复位隔离历史IV，配置AES-128/CBC/Encrypt与Key但故意不IV Set。
  - IRQ配置：目标Source=IV_MISSING并Enable/Unmask。
  steps:
  - 历史隔离：复位当前AES实例。
  - 缺IV配置：Enable、设置length/CBC/Key但省略IV Set。
  - IRQ基线：Clear旧事件并读取baseline event_count。
  - 缺IV刺激：BLOCK_WRITE_DIRECT写入完整block。
  - 错误快照：读取IRQ_RAW/STATUS/latched/event_count。
  - 目标清除：IRQ_CLEAR(IV_MISSING)。
  - 清除复核：确认RAW/STATUS/latched三个视图目标bit均为0。
  observations:
  - 缺IV硬件视图：ISR确认后IRQ_RAW.IV_MISSING与IRQ_STATUS.IV_MISSING期望0。
  - ISR锁存证据：Service latch期望IV_MISSING且event_count=baseline+1。
  - 清除后状态：Clear后RAW/STATUS/latched中的IV_MISSING均为0。
  pass_criteria:
  - IV_MISSING锁存：latched=IV_MISSING且raw/status=0。
  - 事件计数：event_count=baseline+1。
  - 精确清除：Clear后三个视图目标bit均为0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_state, label: IV_MISSING期望事件, source: oracle, role: expected, format: text}
- {key: actual_state, label: IV_MISSING ISR实际锁存, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_012
case_name: AES正常完成IRQ与清除测试
report_feature: |-
  1. AES COMPLETE IRQ中断
  2. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_019, AES_F_028]
method:
  inputs:
  - 正常输入：AES-128/ECB/Encrypt+固定Key和16-byte payload；Expected由Golden计算。
  - IRQ配置：COMPLETE执行前Clear并Enable/Unmask。
  steps:
  - 资源准备：创建单块Source/Destination。
  - AES/IRQ配置：Enable AES、配置ECB/Key并开启COMPLETE。
  - 基线读取：取得执行前event_count。
  - 正常运算：执行PROCESS，读取RESULT_DOUT与IRQ snapshot。
  - 输出校验：Actual与Golden一致且produced_bytes=16。
  - COMPLETE判定：latched=COMPLETE且event_count=baseline+1。
  - IRQ清除：Clear后确认RAW/STATUS/latched中的COMPLETE均为0。
  observations:
  - 硬件输出：RESULT_DOUT[0..3] Actual期望与Golden一致。
  - COMPLETE硬件视图：ISR确认后IRQ_RAW.COMPLETE/IRQ_STATUS.COMPLETE期望0。
  - ISR锁存：Service latch期望COMPLETE且event_count=baseline+1。
  - 清除后状态：Clear后三个视图COMPLETE均为0。
  pass_criteria:
  - 数据正确：Actual=Golden且produced_bytes=16。
  - COMPLETE锁存：latched=COMPLETE且raw/status=0。
  - 事件计数：event_count=baseline+1。
  - 清除结果：Clear后三个视图COMPLETE=0。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: COMPLETE期望事件, source: oracle, role: expected, format: text}
- {key: actual_irq, label: COMPLETE ISR实际锁存, source: dut, role: actual, format: hex32}
- {key: actual_irq_status, label: IRQ_STATUS.COMPLETE实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_013
case_name: AES未完成关闭IRQ与恢复运算测试
report_feature: |-
  1. AES INCOMPLETE_DISABLE IRQ中断
  2. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_020, AES_F_028]
method:
  inputs:
  - 异常刺激：单块写入后不读结果，立即Disable。
  - 恢复条件：触发INCOMPLETE_DISABLE后重新Enable/Configure/Key并执行正常KAT。
  steps:
  - 资源/AES配置：准备资源并开启INCOMPLETE_DISABLE Source。
  - 基线读取：读取触发前event_count。
  - 未读结果关闭：BLOCK_WRITE_DISABLE_DIRECT写入后立即Disable。
  - 关闭事件读取：读取IRQ snapshot。
  - IRQ判定：要求latched=INCOMPLETE_DISABLE且event_count=baseline+1。
  - 恢复重配：重新Enable、配置length/ECB/Key。
  - 恢复KAT：PROCESS同一payload，读取RESULT_DOUT并与Golden比较后清除IRQ。
  observations:
  - 未完成关闭硬件视图：ISR确认后IRQ_RAW/STATUS.INCOMPLETE_DISABLE期望0。
  - ISR锁存：Service latch期望INCOMPLETE_DISABLE且event_count=baseline+1。
  - 恢复硬件输出：重新配置后RESULT_DOUT[0..3] Actual期望与Golden一致。
  pass_criteria:
  - 事件锁存：INCOMPLETE_DISABLE锁存正确。
  - 事件计数：event_count=baseline+1。
  - 恢复数据正确：恢复Actual与Golden一致。
  - 恢复长度：produced_bytes=16。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: INCOMPLETE_DISABLE期望事件, source: oracle, role: expected, format: text}
- {key: actual_irq, label: INCOMPLETE_DISABLE ISR实际锁存, source: dut, role: actual, format: hex32}
- {key: actual_irq_status, label: IRQ_STATUS.INCOMPLETE_DISABLE实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_014
case_name: AES IRQ传输会话状态与数据路径测试
report_feature: |-
  1. AES DIN_REQ IRQ中断
  2. AES DOUT_REQ IRQ中断
  3. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_021, AES_F_022, AES_F_028]
method:
  inputs:
  - 数据配置：AES-128/ECB/Encrypt+固定Key和16-byte Source/Destination。
  - 事件组合：DATA_IN_REQ、DATA_OUT_REQ、COMPLETE组成IRQ Transfer会话。
  steps:
  - 资源/AES初始化：准备Resource并Enable/Configure/Key/IRQ。
  - 初态读取：读取IRQ_TRANSFER.STATE，确认IDLE。
  - 会话启动：IRQ_TRANSFER_START绑定Source/Destination与长度。
  - 状态轮询：最多64次读取STATE/INPUT_OFFSET/OUTPUT_OFFSET，不固定sleep。
  - 终态捕获：进入COMPLETE/ABORTED/FAULT后停止轮询并读IRQ snapshot。
  - 推进判定：要求COMPLETE且input/output_offset=16、produced_bytes=16。
  - 输出校验：读取Destination Actual并与Golden比较。
  - 会话收尾：记录终态后Abort/Clear清理。
  observations:
  - 会话状态：IRQ_TRANSFER.STATE初始IDLE、终态COMPLETE。
  - 请求推进：IRQ_TRANSFER.INPUT_OFFSET/OUTPUT_OFFSET终态16/16；用于证明输入/输出请求路径实际推进。
  - IRQ来源：会话由IRQ_STATUS.DATA_IN_REQ/DATA_OUT_REQ/COMPLETE驱动，Service latch保留可追溯来源。
  - 硬件输出：Destination来自RESULT_DOUT路径，Actual期望与Golden一致。
  pass_criteria:
  - 状态完整：IDLE→COMPLETE。
  - 推进完整：input/output_offset=16且produced_bytes=16。
  - 轮询有效：Offset始终0..16且不用固定sleep。
  - 数据正确：Actual与Golden一致。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: IRQ Transfer期望状态, source: oracle, role: expected, format: text}
- {key: irq_transfer_initial_state, label: IRQ_TRANSFER.STATE初始实际值, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_015
case_name: AES IRQ Force投递与清除测试
report_feature: |-
  1. AES IRQ Source Enable/Disable控制
  2. AES IRQ Force强制
  3. AES IRQ Delivery投递
p_level: P1
feature_refs: [AES_F_023, AES_F_025, AES_F_028]
method:
  inputs:
  - Source覆盖：参数化5个非请求型AES IRQ Source，每个独立执行Enable/Unmask/Force/Clear。
  steps:
  - Source选择：确认Capability支持当前Source。
  - IRQ配置：Enable AES并Clear旧事件，Enable/Unmask当前Source。
  - 基线读取：保存Force前event_count。
  - Force刺激：执行IRQ_FORCE.<Source>并读snapshot。
  - ISR判定：要求raw/status=0、latched=当前Source、event_count+1。
  - 禁用与清除：Disable当前Source并IRQ_CLEAR。
  - 清除复核：确认raw/status/latched目标位为0且event_count不增加。
  observations:
  - Force刺激端点：IRQ_FORCE.<Source>是Stimulus，不作为事件已发生的Observation。
  - ISR投递：IRQ_RAW/STATUS.<Source>与Service latch共同证明投递，期望latched=当前Source。
  - 清除后状态：Clear后IRQ_RAW/STATUS.<Source>与Service latched目标位均0。
  pass_criteria:
  - Source覆盖：5个参数Source均执行。
  - ISR锁存正确：latched=当前Source。
  - 事件计数：Force后+1。
  - 清除后状态：三个视图为0且计数不增加。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: 当前IRQ Source期望事件, source: oracle, role: expected, format: text}
- {key: actual_irq, label: ISR.LATCHED.<Source>实际值, source: dut, role: actual, format: hex32}
- {key: actual_irq_status, label: IRQ_STATUS.<Source>实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_016
case_name: AES IRQ Mask/Unmask语义测试
report_feature: |-
  1. AES IRQ Mask/Unmask控制
  2. AES IRQ RAW/STATUS状态
p_level: P1
feature_refs: [AES_F_024, AES_F_027]
method:
  inputs:
  - Mask事件：使用COMPLETE，先Enable并Mask，再Force产生待处理事件。
  steps:
  - Mask配置：Enable AES、Clear旧COMPLETE、Enable后保持Mask。
  - Force刺激：IRQ_FORCE.COMPLETE并读取masked snapshot。
  - Mask判定：要求IRQ_RAW.COMPLETE=1、IRQ_STATUS.COMPLETE=0、latched=0。
  - 解除屏蔽：记录masked event_count并执行Unmask。
  - Unmask读取：读取新的snapshot。
  - 投递判定：要求raw/status=0、latched=COMPLETE、event_count+1。
  - 事件清理：Clear并Disable COMPLETE。
  observations:
  - Mask硬件状态：IRQ_RAW.COMPLETE期望1、IRQ_STATUS.COMPLETE期望0。
  - Mask阶段ISR：Service latched期望0，event_count不增加。
  - Unmask投递：Unmask后Service latch期望COMPLETE且event_count+1。
  pass_criteria:
  - Mask语义：RAW=COMPLETE、STATUS=0、latched=0。
  - Unmask投递：raw/status=0、latched=COMPLETE。
  - 事件计数：Unmask后比masked+1。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: Mask/Unmask期望语义, source: oracle, role: expected, format: text}
- {key: masked_raw, label: IRQ_RAW.COMPLETE Mask时实际值, source: dut, role: actual, format: hex32}
- {key: actual_irq_status, label: IRQ_STATUS.COMPLETE Mask时实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P1_017
case_name: AES IRQ单Source精确清除测试
report_feature: |-
  1. AES IRQ Clear清除
  2. AES IRQ RAW/STATUS状态
p_level: P1
feature_refs: [AES_F_026, AES_F_027]
method:
  inputs:
  - Source覆盖：7个AES IRQ Source分别在Enable+Mask状态下Force/Clear。
  steps:
  - Source选择：确认Capability支持当前Source。
  - Mask配置：Enable AES、Clear旧事件、Enable当前Source并Mask。
  - Force刺激：IRQ_FORCE.<Source>并读clear前snapshot。
  - 清除前判定：要求IRQ_RAW=当前Source、STATUS=0、latched=0。
  - 单Source清除：仅IRQ_CLEAR当前Source。
  - 清除后读取：确认RAW/STATUS/latched目标bit均0。
  - 参数汇总：确认event_count Clear前后不变并Disable当前Source。
  observations:
  - 清除前硬件状态：IRQ_RAW.<Source>期望目标bit=1，IRQ_STATUS.<Source>=0。
  - 单Source清除：IRQ_CLEAR后IRQ_RAW.<Source>从1变0，直接证明精确清除。
  - ISR隔离：Mask状态下Service latched=0且Clear前后event_count不变。
  pass_criteria:
  - Source覆盖：7个Source均执行。
  - Force后RAW：raw=当前Source、status/latched=0。
  - 单Source清除：Clear后目标位三个视图均0。
  - 事件计数：Clear前后不变。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_irq, label: RAW清除期望状态, source: oracle, role: expected, format: text}
- {key: actual_irq, label: IRQ_RAW.<Source>清除前实际值, source: dut, role: actual, format: hex32}
- {key: actual_irq_status, label: IRQ_STATUS.<Source>清除前实际值, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P2_001
case_name: AES DMA Request Gate传递测试
report_feature: |-
  1. AES Input/Output DMA Request Gate控制
p_level: P2
feature_refs: [AES_F_029]
method:
  inputs:
  - DMA配置：AES-128/ECB/REGISTER DMA Mode+16-byte block，运行时选择两条空闲Channel。
  - Gate初态：两条DMA Channel先启动，AES Input/Output Request Gate保持关闭。
  steps:
  - 能力/资源准备：检查双向DMA并准备Source/Destination和Golden。
  - AES配置：Enable AES、配置REGISTER Mode/Key/data_length。
  - Route/Channel配置：配置DMAMUX与输入/输出Channel。
  - Gate关闭启动：先启动输出和输入Channel，Request Gate保持关闭。
  - 有界关闭观测：连续8次读取DMA_CHANNEL_STATUS，要求两Channel始终Not-Free且无Error。
  - Gate开启：打开Input/Output DMA Request并有界等待。
  - 完成与数据读取：两Channel进入Free后读取Destination Actual。
  - 最终判定：确认无Error且Actual与Golden一致。
  observations:
  - Gate关闭DMA状态：有界窗口内DMA_CHANNEL_STATUS.INPUT/OUTPUT始终Not-Free且无Error。
  - Gate开启DMA状态：开启后两Channel进入Free且无Error。
  - 最终数据：Destination来自RESULT_DOUT[0..3]的REGISTER DMA路径，Actual期望与Golden一致。
  pass_criteria:
  - Gate关闭行为：8次窗口内两Channel均Not-Free且无Error。
  - Gate开启完成：两Channel有界进入Free且无Error。
  - 数据正确：16-byte Actual与Golden一致。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: gate_closed_input_active, label: DMA_CHANNEL_STATUS.INPUT Gate关闭Active, source: dut, role: actual, format: bit_bool}
- {key: gate_closed_output_active, label: DMA_CHANNEL_STATUS.OUTPUT Gate关闭Active, source: dut, role: actual, format: bit_bool}
- {key: gate_closed_no_error, label: DMA_CHANNEL_STATUS Gate关闭无Error, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P2_002
case_name: AES DMA REGISTER模式双向传输测试
report_feature: |-
  1. AES DMA递增端点模式
  2. AES DMA/CPU Result等价
p_level: P2
feature_refs: [AES_F_030, AES_F_032]
method:
  inputs:
  - REGISTER配置：AES-128/ECB/Encrypt+16-byte block，两条DMA Channel。
  - 数据方向：Memory→DIN[0..3]与RESULT_DOUT[0..3]→Memory。
  steps:
  - 能力/资源准备：选择两条空闲Channel并准备Source/Destination/Golden。
  - AES配置：Enable、REGISTER DMA Mode、Key、data_length。
  - Route配置：配置输入/输出DMAMUX。
  - Channel配置：按四个递增32-bit端点配置双向Channel。
  - DMA启动：输出Channel先启动，再启动输入并打开双向Request。
  - 完成等待：两Channel有界回到Free。
  - 输出读取：读取Destination 16-byte Actual。
  - 数据判定：Channel完成且Actual与Golden一致。
  observations:
  - 端点映射：DIN[0..3]/RESULT_DOUT[0..3]来自Execution Mapping，不冒充Readback。
  - DMA完成：DMA_CHANNEL_STATUS.INPUT/OUTPUT期望Free。
  - DMA硬件输出：Destination中Actual来自RESULT_DOUT[0..3]，期望与Golden一致。
  pass_criteria:
  - DMA完成：输入/输出Channel均Free。
  - REGISTER数据正确：Actual与独立Golden一致。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: REGISTER路径PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: "DMA Destination<-RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P2_003
case_name: AES DMA FIFO模式双向传输测试
report_feature: |-
  1. AES DMA FIFO Endpoint模式
  2. AES DMA/CPU Result等价
p_level: P2
feature_refs: [AES_F_031, AES_F_032]
method:
  inputs:
  - FIFO配置：AES-128/ECB/Encrypt+16-byte block，两条DMA Channel。
  - 数据方向：Memory→DATA固定端点，再由RESULT固定端点→Memory。
  steps:
  - 能力/资源准备：准备Channel/Source/Destination/Golden。
  - AES配置：Enable、FIFO DMA Mode、Key、data_length。
  - Route配置：配置输入/输出DMAMUX。
  - Channel配置：按固定DATA/RESULT端点配置Channel。
  - 输入阶段：启动输入Channel，仅打开Input Request并等待Free。
  - 输出阶段：启动输出Channel，仅打开Output Request并等待Free。
  - 输出读取：读取Destination 16-byte Actual。
  - 数据判定：两阶段Channel完成且Actual与Golden一致。
  observations:
  - 端点映射：DATA/RESULT固定端点来自Execution Mapping。
  - 分阶段DMA状态：输入、输出DMA_CHANNEL_STATUS均期望Free。
  - FIFO硬件输出：Destination中Actual来自RESULT固定端点，期望与Golden一致。
  pass_criteria:
  - DMA完成：输入/输出Channel均Free。
  - FIFO数据正确：Actual与独立Golden一致。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: FIFO路径PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: DMA Destination<-RESULT实际输出, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P3_001
case_name: AES八轮确定性与状态隔离测试
report_feature: |-
  1. AES Encrypt/Decrypt方向
  2. AES-128/AES-256密钥
  3. AES ECB/CBC/CTR模式
  4. AES CPU Polling Block I/O路径
p_level: P3
feature_refs: [AES_F_002, AES_F_003, AES_F_004, AES_F_015]
method:
  inputs:
  - 确定性轮次：seed=0x0A350001，8轮Key Size交替、Mode循环。
  - 每轮Golden：独立payload/IV/Counter，Expected由独立AES Golden计算。
  steps:
  - 资源初始化：重置资源池并进入8轮循环。
  - 轮次生成：根据index生成Key Size/Mode/Key/IV/Counter/payload。
  - Golden/资源：计算Expected并创建独立Source/Destination。
  - AES配置：每轮重新Enable/Configure/Key/IV。
  - 单轮运算：PROCESS后读取RESULT_DOUT与STATUS.FINISH。
  - 即时判定：Actual=Golden、produced_bytes正确、FINISH=1。
  - 轮次清理：每轮Disable，避免状态跨轮。
  - 最终汇总：确认8轮完整并保留每轮Expected/Actual/FINISH。
  observations:
  - 每轮完成：STATUS.FINISH期望1。
  - 每轮硬件输出：RESULT_DOUT[0..3] Actual期望与本轮Golden一致。
  - 覆盖事实：seed/Mode/Key Size/轮数用于追溯，不是寄存器Observation。
  pass_criteria:
  - 轮次完整：8轮完成。
  - 数据正确：每轮Actual=Golden。
  - 输出与完成：每轮produced_bytes=16且FINISH=1。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: round_expected_output, label: 每轮PC Golden, source: oracle, role: expected, format: text}
- {key: round_actual_output, label: "每轮RESULT_DOUT[0..3]实际输出", source: dut, role: actual, format: text}
- {key: round_finish_status, label: 每轮STATUS.FINISH实际值, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P3_002
case_name: AES CPU路径目标周期测量测试
report_feature: |-
  1. AES CPU Path Cycle Count周期
p_level: P3
feature_refs: [AES_F_033]
method:
  inputs:
  - 性能档位：256/1024-byte确定性payload，AES-128/ECB/Encrypt。
  - 计时与Golden：TIMED_PROCESS返回目标周期；功能Expected由独立Golden计算。
  steps:
  - 能力检查：确认CPU_REGISTER_PATH/TIMED_PROCESS/TEST_EXTENSIONS。
  - 档位生成：选择256或1024并计算Golden。
  - 资源准备：创建对应Source/Destination。
  - AES配置：每档重新Enable/Configure/Key。
  - 目标计时：执行TIMED_PROCESS取得elapsed_cycles/measured_bytes/FINISH。
  - 功能读取：读取RESULT_DOUT路径完整Actual。
  - 单档判定：Actual=Golden、cycles>0、measured_bytes正确、FINISH=1。
  - 趋势判定：1024-byte cycles大于256-byte。
  observations:
  - 目标周期：TIMING.CYCLE_COUNT对应elapsed_cycles，两档均>0且1024>256。
  - 运算完成：STATUS.FINISH每档期望1。
  - 硬件输出：RESULT_DOUT[0..3]路径Actual与各档Golden一致。
  pass_criteria:
  - 功能正确：两档Actual=Golden。
  - 计时有效：cycles>0、measured_bytes=请求长度、FINISH=1。
  - 周期趋势：1024 cycles>256 cycles。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: timed_expected_output, label: 当前档PC Golden, source: oracle, role: expected, format: text}
- {key: timed_actual_output, label: RESULT_DOUT路径当前档实际输出, source: dut, role: actual, format: text}
- {key: timed_elapsed_cycles, label: TIMING.CYCLE_COUNT实际值, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: AES_P3_003
case_name: AES DMA路径目标周期测量测试
report_feature: |-
  1. AES DMA Path Cycle Count周期
p_level: P3
feature_refs: [AES_F_034]
method:
  inputs:
  - DMA性能输入：AES-128/ECB/FIFO DMA+1024-byte payload。
  - 计时配置：输出Channel使用TRANSFER_DONE目标端计时，Expected由Golden计算。
  steps:
  - 能力准备：检查双向DMA+Interrupt并选择两条Channel。
  - AES/资源配置：准备1024-byte Source/Destination并配置FIFO/Key/length。
  - Route/Channel配置：配置DMAMUX和固定FIFO端点。
  - 计时IRQ配置：只启用输出Channel TRANSFER_DONE。
  - 计时启动：start_timed输出Channel，再启动输入并打开双向Request。
  - 完成等待：等待timing.complete并等待两Channel Free。
  - 输出读取：取得elapsed_cycles及Destination Actual。
  - 最终判定：cycles>0、Channel无Error、Actual与Golden一致。
  observations:
  - DMA计时完成：DMA_IRQ.TRANSFER_DONE对应timing.complete=true并产生elapsed_cycles>0。
  - DMA终态：DMA_CHANNEL_STATUS.INPUT/OUTPUT期望Free且无Error。
  - FIFO硬件输出：Destination中Actual来自RESULT固定端点，期望与Golden一致。
  pass_criteria:
  - 计时完成：timing.complete=true且cycles>0。
  - DMA终态：两Channel Free且无Error。
  - 数据正确：1024-byte Actual与Golden一致。
timeout: 使用当前AES Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup: [只恢复本Case实际获得或修改的AES状态, 跨IP资源按owner逆序释放并保留cleanup失败证据]
resources: {minimum_level: R0, full_coverage_level: R0, board: 按本Case声明资源执行。, bench: 按本Case声明资源执行。}
backend: [FPGA, Silicon]
evidence: [Canonical Measurement/Observation + bound structured Artifact]
failure_observations:
- {key: expected_output, label: FIFO DMA性能PC Golden, source: oracle, role: expected, format: text}
- {key: actual_output, label: DMA Destination<-RESULT实际输出, source: dut, role: actual, format: text}
- {key: timing_complete, label: DMA_IRQ.TRANSFER_DONE计时完成, source: dut, role: actual, format: bit_bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  AES_P0_001:
    summary: AES代表实例静态映射与目标侧只读能力门禁证据。
    fields:
    - {source: measurement, path: expected_capability, label: AES_CAPABILITIES期望, format: text, aggregate: same}
    - {source: observation, path: actual_capability, label: AES_CAPABILITIES实际值, format: text, aggregate: same}
    - {source: artifact, path: runtime.features, label: AES_CAPABILITIES.features实际值, format: hex32, aggregate: same}
  AES_P0_002:
    summary: AES标准向量的RESULT_DOUT、FINISH与独立Golden执行证据。
    fields:
    - {source: measurement, path: expected_output, label: PC/NIST Golden记录数, format: count, aggregate: all}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]实际输出记录数", format: count, aggregate: all}
    - {source: observation, path: finish_status, label: STATUS.FINISH（期望=1）, format: bit_bool, aggregate: all}
    - {source: artifact, path: produced_bytes, label: PROCESS produced_bytes（期望=16）, format: decimal, aggregate: distinct}
  AES_P0_003:
    summary: AES两轮重新使能后的RESULT_DOUT/FINISH完整快照。
    fields:
    - {source: artifact, path: rounds, label: "两轮RESULT_DOUT[0..3]/Golden/FINISH快照", format: text, aggregate: same}
    - {source: artifact, path: outputs_distinct, label: 两轮RESULT_DOUT不同（期望=true）, format: bool, aggregate: same}
  AES_P1_001:
    summary: AES Padding参数覆盖与RESULT_DOUT输出证据。
    fields:
    - {source: artifact, path: config.padding, label: Padding参数, format: text, aggregate: distinct}
    - {source: artifact, path: config.length, label: 输入长度, format: decimal, aggregate: distinct}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]硬件输出记录数", format: count, aggregate: all}
    - {source: artifact, path: produced_bytes, label: produced_bytes实际值, format: decimal, aggregate: distinct}
  AES_P1_002:
    summary: AES IV读回与不同IV输出影响证据。
    fields:
    - {source: artifact, path: mode, label: AES工作模式, format: text, aggregate: distinct}
    - {source: artifact, path: iv_results, label: IV读回/RESULT_DOUT节点记录, format: text, aggregate: all}
    - {source: artifact, path: outputs_distinct, label: IV_A/IV_B输出不同（期望=true）, format: bool, aggregate: all}
  AES_P1_003:
    summary: AES DATA_LENGTH bit32硬件读回证据；BUSY/FINISH/输出保留在执行明细。
    fields:
    - {source: measurement, path: expected_value, label: "DATA_LENGTH[1:0]期望", format: decimal, aggregate: same}
    - {source: observation, path: actual_value, label: "DATA_LENGTH[1:0]实际读回", format: decimal, aggregate: same}
  AES_P1_004:
    summary: AES LITTLE/BIG字节序下RESULT_DOUT canonical输出证据。
    fields:
    - {source: artifact, path: endian, label: ENDIAN配置, format: text, aggregate: distinct}
    - {source: measurement, path: expected_output, label: PC Golden记录数, format: count, aggregate: all}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]输出记录数", format: count, aggregate: all}
    - {source: artifact, path: produced_bytes, label: produced_bytes（期望=16）, format: decimal, aggregate: distinct}
  AES_P1_005:
    summary: AES CTR Counter节点的RESULT_DOUT与FINISH证据。
    fields:
    - {source: artifact, path: counter, label: Counter配置, format: hex32, aggregate: distinct}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]输出记录数", format: count, aggregate: all}
    - {source: artifact, path: status.finish, label: STATUS.FINISH（期望=1）, format: bit_bool, aggregate: all}
    - {source: artifact, path: status.produced_bytes, label: produced_bytes（期望=16）, format: decimal, aggregate: distinct}
  AES_P1_006:
    summary: AES非DMA输入请求的决定性硬件状态证据。
    fields:
    - {source: measurement, path: expected_value, label: STATUS.DIN_REQ写入前期望, format: bit_bool, aggregate: same}
    - {source: observation, path: actual_value, label: STATUS.DIN_REQ写入前实际值, format: bit_bool, aggregate: same}
  AES_P1_007:
    summary: AES非DMA输出请求读取前硬件状态；RESULT_DOUT与后续状态保留在执行明细。
    fields:
    - {source: observation, path: dout_req_before_read, label: STATUS.DOUT_REQ读取前实际值（期望=1）, format: bit_bool, aggregate: same}
  AES_P1_008:
    summary: AES FINISH置位、RESULT_DOUT与W1C清除的原子硬件证据。
    fields:
    - {source: measurement, path: expected_output, label: PC端Golden期望输出, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]实际输出", format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_state, label: STATUS.FINISH清除前实际值, format: bit_bool, aggregate: same}
    - {source: observation, path: finish_after_clear, label: STATUS.FINISH清除后实际值, format: bit_bool, aggregate: same}
  AES_P1_009:
    summary: AES DMA输出冲突ISR锁存、清除与恢复证据。
    fields:
    - {source: measurement, path: expected_state, label: OUTPUT_CONFLICT期望事件, format: text, aggregate: same}
    - {source: observation, path: actual_state, label: ISR.LATCHED.OUTPUT_CONFLICT实际现场, format: text, aggregate: same}
    - {source: measurement, path: recovery_expected, label: 复位后CPU PROCESS期望输出, format: bytes_hex, aggregate: same}
    - {source: observation, path: recovery_actual, label: 复位后RESULT_DOUT实际输出, format: bytes_hex, aggregate: same}
  AES_P1_010:
    summary: AES KEY_MISSING ISR锁存证据；清除后三视图保留在执行明细。
    fields:
    - {source: measurement, path: expected_state, label: KEY_MISSING期望事件, format: text, aggregate: same}
    - {source: observation, path: actual_state, label: ISR.LATCHED.KEY_MISSING实际值, format: hex32, aggregate: same}
  AES_P1_011:
    summary: AES IV_MISSING ISR锁存证据；清除后三视图保留在执行明细。
    fields:
    - {source: measurement, path: expected_state, label: IV_MISSING期望事件, format: text, aggregate: same}
    - {source: observation, path: actual_state, label: ISR.LATCHED.IV_MISSING实际值, format: hex32, aggregate: same}
  AES_P1_012:
    summary: AES COMPLETE IRQ与RESULT_DOUT硬件证据。
    fields:
    - {source: measurement, path: expected_output, label: PC端Golden期望输出, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: "RESULT_DOUT[0..3]实际输出", format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_irq, label: ISR.LATCHED.COMPLETE实际值, format: hex32, aggregate: same}
    - {source: observation, path: actual_irq_status, label: IRQ_STATUS.COMPLETE实际值, format: hex32, aggregate: same}
  AES_P1_013:
    summary: AES INCOMPLETE_DISABLE ISR证据；恢复RESULT_DOUT保留在执行明细。
    fields:
    - {source: measurement, path: expected_irq, label: INCOMPLETE_DISABLE期望事件, format: text, aggregate: same}
    - {source: observation, path: actual_irq, label: ISR.LATCHED.INCOMPLETE_DISABLE实际值, format: hex32, aggregate: same}
    - {source: observation, path: actual_irq_status, label: IRQ_STATUS.INCOMPLETE_DISABLE实际值, format: hex32, aggregate: same}
  AES_P1_014:
    summary: AES IRQ Transfer初始硬件会话状态；终态/Offset/输出保留在执行明细与Artifact。
    fields:
    - {source: measurement, path: expected_irq, label: IRQ Transfer期望状态, format: text, aggregate: same}
    - {source: observation, path: irq_transfer_initial_state, label: IRQ_TRANSFER.STATE初始实际值, format: text, aggregate: same}
  AES_P1_015:
    summary: AES参数化IRQ Force的ISR投递证据。
    fields:
    - {source: measurement, path: expected_irq, label: 当前Source期望事件, format: text, aggregate: distinct}
    - {source: observation, path: actual_irq, label: ISR.LATCHED.<Source>实际值, format: hex32, aggregate: distinct}
    - {source: observation, path: actual_irq_status, label: IRQ_STATUS.<Source>实际值, format: hex32, aggregate: distinct}
  AES_P1_016:
    summary: AES COMPLETE Mask阶段RAW/STATUS决定性证据；Unmask投递保留在执行明细。
    fields:
    - {source: measurement, path: expected_irq, label: Mask/Unmask期望语义, format: text, aggregate: same}
    - {source: observation, path: masked_raw, label: IRQ_RAW.COMPLETE Mask时实际值, format: hex32, aggregate: same}
    - {source: observation, path: actual_irq_status, label: IRQ_STATUS.COMPLETE Mask时实际值（期望=0）, format: hex32, aggregate: same}
  AES_P1_017:
    summary: AES参数化IRQ Source清除前RAW/STATUS决定性证据；清除后状态保留在执行明细。
    fields:
    - {source: measurement, path: expected_irq, label: RAW清除期望状态, format: text, aggregate: all}
    - {source: observation, path: actual_irq, label: IRQ_RAW.<Source>清除前实际值, format: hex32, aggregate: all}
    - {source: observation, path: actual_irq_status, label: IRQ_STATUS.<Source>清除前实际值, format: hex32, aggregate: distinct}
  AES_P2_001:
    summary: AES DMA Request Gate关闭窗口的Channel硬件状态证据；Gate开启完成与数据保留在执行明细。
    fields:
    - {source: observation, path: gate_closed_input_active, label: DMA_CHANNEL_STATUS.INPUT关闭窗口Active（期望=1）, format: bit_bool, aggregate: same}
    - {source: observation, path: gate_closed_output_active, label: DMA_CHANNEL_STATUS.OUTPUT关闭窗口Active（期望=1）, format: bit_bool, aggregate: same}
    - {source: observation, path: gate_closed_no_error, label: DMA_CHANNEL_STATUS关闭窗口无Error（期望=1）, format: bit_bool, aggregate: same}
  AES_P2_002:
    summary: AES REGISTER DMA双向Channel终态与RESULT_DOUT数据证据。
    fields:
    - {source: measurement, path: expected_output, label: REGISTER路径PC Golden, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: "DMA Destination<-RESULT_DOUT[0..3]实际输出", format: bytes_hex, aggregate: same}
    - {source: observation, path: input_channel_free, label: DMA_CHANNEL_STATUS.INPUT Free（期望=1）, format: bit_bool, aggregate: same}
    - {source: observation, path: output_channel_free, label: DMA_CHANNEL_STATUS.OUTPUT Free（期望=1）, format: bit_bool, aggregate: same}
  AES_P2_003:
    summary: AES FIFO DMA双向Channel终态与RESULT数据证据。
    fields:
    - {source: measurement, path: expected_output, label: FIFO路径PC Golden, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: DMA Destination<-RESULT实际输出, format: bytes_hex, aggregate: same}
    - {source: observation, path: input_channel_free, label: DMA_CHANNEL_STATUS.INPUT Free（期望=1）, format: bit_bool, aggregate: same}
    - {source: observation, path: output_channel_free, label: DMA_CHANNEL_STATUS.OUTPUT Free（期望=1）, format: bit_bool, aggregate: same}
  AES_P3_001:
    summary: AES固定seed八轮硬件结果闭合证据。
    fields:
    - {source: artifact, path: seed, label: 固定Seed, format: hex32, aggregate: same}
    - {source: artifact, path: round_count, label: 完成轮数（期望=8）, format: decimal, aggregate: same}
    - {source: artifact, path: results, label: RESULT_DOUT/FINISH轮次记录数（期望=8）, format: count, aggregate: same}
  AES_P3_002:
    summary: AES CPU路径目标周期与功能结果闭合证据。
    fields:
    - {source: artifact, path: measurements.256, label: 256-byte TIMING.CYCLE_COUNT实际周期, format: decimal, aggregate: same}
    - {source: artifact, path: measurements.1024, label: 1024-byte TIMING.CYCLE_COUNT实际周期, format: decimal, aggregate: same}
    - {source: artifact, path: throughput_order, label: 1024周期>256周期（期望=true）, format: bool, aggregate: same}
    - {source: artifact, path: details, label: RESULT_DOUT/FINISH/Golden档位记录数（期望=2）, format: count, aggregate: same}
  AES_P3_003:
    summary: AES FIFO DMA目标周期、TRANSFER_DONE与RESULT数据证据。
    fields:
    - {source: measurement, path: expected_output, label: FIFO DMA性能PC Golden, format: bytes_hex, aggregate: same}
    - {source: observation, path: actual_output, label: DMA Destination<-RESULT实际输出, format: bytes_hex, aggregate: same}
    - {source: observation, path: timing_complete, label: DMA_IRQ.TRANSFER_DONE计时完成（期望=1）, format: bit_bool, aggregate: same}
    - {source: observation, path: elapsed_cycles, label: DMA_TIMING.CYCLE_COUNT实际值, format: decimal, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 当前说明 | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=35 | ADAPTED=26 | 寄存器/Field 映射已建立；本轮 Evidence Closure 代码尚需精确 SHA 软件门禁与新 HIL 复跑 | `ET6801_aes.md` |

## 5. Evidence Closure / Known Hardware Status

- 本文件 26 个 Case 已不再使用 `case_measurement_gap`；运行时 Case 的决定性 Expected/Actual/Hardware Observation 已绑定 Canonical Result，结构化附件采用单次最终 Snapshot。
- `AES_P0_001` 先做静态 semantic mapping 门禁，映射存在后通过只读 `AES_CAPABILITIES` 获取目标侧运行时能力；它不执行 AES 运算或状态修改。
- `AES_P2_001` 已按 Contract 增加 Gate 关闭期间 8 次有界 `DMA_CHANNEL_STATUS` 观测窗口；只有新 HIL 运行通过后，才能把该增强后的 Gate 证明写成新的硬件 PASS。
- 历史 ET6801 FPGA 运行记录为 56 PASS / 3 FAIL；其中 `AES_P1_009`、`AES_P2_003`、`AES_P3_003` 的历史 FAIL 不能被本轮文档/证据整改自动改写为 PASS。
- `AES_P1_003` 只证明 PROCESS 完成后的 `STATUS.BUSY=0`，未声称已观测运行中的 BUSY 拉高。
- `AES_P2_002` / `AES_P2_003` 以 DMA Actual == 独立 AES Golden 闭合逻辑结果，不声称同一 Case 内直接比较 CPU 与 DMA 两次硬件输出。
- 推广到其他 IP 时复用本 AES 模式：`Feature -> 最小充分硬件观测 -> Canonical Evidence -> 单次 Artifact Snapshot -> ET_CASE_REPORT -> Excel人工审核`。
