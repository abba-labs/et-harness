# UART Stable IP Contract

<!-- Contract sync 2026-08-18: UART Firmware Service/Wrap source readability was revalidated under R330; stable Feature/Case/Report/Wire semantics remain unchanged. -->

<!-- Contract sync 2026-08-18: Firmware UART Service/Wrap composition was revalidated after the R300/R310 own-IP factory/manifest refactor; stable Feature/Case/Report semantics remain unchanged. -->

> 本文件只定义跨芯片稳定 Feature / Case / Report Contract；具体芯片 Hardware/Driver/Register/IRQ/历史证据位于同目录 `<CHIP>_uart.md`。
> 公共 PC Case / Driver / Firmware Service / Common Wrap 的稳定语义必须与本文件同步。
> Formal Case 前置隔离统一遵循 `R210`：第一次 Feature 配置前由 Case 显式复位参与的 DUT/Peer UART；DMA Case 先复位 DMA，再复位 UART，最后复位 Resource Pool。PC控制串口不得复位，本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

- IP：`uart`。
- Feature/Case ID 绑定稳定语义，不绑定具体芯片。
- 新芯片优先映射既有 Feature；参数/范围差异进入 Capability；物理实现差异进入 Chip/Board/Driver。
- 只有真正新增稳定硬件语义时才新增 Feature，只有测试路径/Oracle/Resource/Cleanup 不可复用时才新增 Case。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| UART_F_001 | UART Instance集合 | 可用UART逻辑实例集合由Capability声明 | `UART_P0_001`, `UART_P1_017`, `UART_P1_001` |
| UART_F_002 | UART IRQ路由 | 每个逻辑实例的IRQ路由由Capability/Chip Mapping声明 | `UART_P1_001` |
| UART_F_003 | UART Normal/Alias地址视图 | 普通与别名地址关系由Capability声明 | — |
| UART_F_004 | UART Component能力与Identity | 可查询的组件能力与身份字段由Capability/Runtime事实声明 | `UART_P0_001` |
| UART_F_005 | UART软件复位 | UART、RX FIFO、TX FIFO | `UART_P0_002`, `UART_P2_008` |
| UART_F_006 | UART Baud Rate配置 | 支持范围、分频能力和误差边界由Capability与稳定Driver契约声明 | `UART_P1_015`, `UART_P3_006` |
| UART_F_007 | UART Data Bits配置 | 5、6、7、8 bit | `UART_P1_014` |
| UART_F_008 | UART Stop Bits配置 | 1、5-bit时1.5、其他时2 | `UART_P1_014` |
| UART_F_009 | UART Parity配置 | none、even、odd、stick0、stick1 | `UART_P1_014` |
| UART_F_010 | UART Full-Duplex TX/RX收发 | 双向同时收发 | `UART_P0_003`, `UART_P0_004`, `UART_P2_003`, `UART_P3_010` |
| UART_F_011 | UART Internal Loopback回环 | enable、disable | `UART_P0_003` |
| UART_F_012 | UART FIFO使能 | TX/RX enable | `UART_P0_002`, `UART_P0_003`, `UART_P1_016` |
| UART_F_013 | UART FIFO Depth/Level/Status | FIFO深度、计数和状态能力由Capability/Runtime事实声明 | `UART_P0_002`, `UART_P1_016` |
| UART_F_014 | UART RX/TX FIFO复位 | 独立RX/TX FIFO reset需要稳定公共动作和独立证明 | — |
| UART_F_015 | UART TX FIFO阈值 | 可配置TX阈值集合由Capability声明 | `UART_P1_016`, `UART_P1_005` |
| UART_F_016 | UART RX FIFO阈值 | 可配置RX阈值集合由Capability声明 | `UART_P1_016`, `UART_P1_004` |
| UART_F_017 | UART Blocking/Non-blocking TX发送 | block、non-block、部分写 | `UART_P0_003`, `UART_P1_016`, `UART_P3_010` |
| UART_F_018 | UART TX完成/超时 | complete、bounded timeout | `UART_P0_003`, `UART_P1_016` |
| UART_F_019 | UART RX_DATA_AVAILABLE IRQ中断 | enable、status、service、disable | `UART_P1_002`, `UART_P1_004`, `UART_P1_011`, `UART_P3_010` |
| UART_F_020 | UART TX_EMPTY IRQ中断 | enable、status、service、disable | `UART_P1_003`, `UART_P1_005`, `UART_P1_011` |
| UART_F_021 | UART CHARACTER_TIMEOUT IRQ中断 | RX FIFO非空且停止接收 | `UART_P1_006`, `UART_P1_011` |
| UART_F_022 | UART Line Error IRQ/Status | PE、FE、OE、BI、RFE | `UART_P1_007`, `UART_P1_008`, `UART_P1_009`, `UART_P1_010` |
| UART_F_023 | UART PARITY_ERROR状态 | mismatch parity | `UART_P1_007` |
| UART_F_024 | UART FRAMING_ERROR状态 | stop/帧不匹配 | `UART_P1_008` |
| UART_F_025 | UART RX_OVERRUN状态 | RX未及时读取 | `UART_P1_009` |
| UART_F_026 | UART BREAK TX/RX检测 | 支持主动发送Break并在接收侧形成可观测Break状态 | `UART_P1_010` |
| UART_F_027 | UART BUSY_DETECT中断 | FIFO关闭/忙时配置或写入 | `UART_P1_012` |
| UART_F_028 | UART IRQ Enable/Identify/Clear | 中断源可独立使能、识别并按稳定清除语义恢复 | `UART_P1_002`, `UART_P1_003`, `UART_P1_006`, `UART_P1_007`, `UART_P1_008`, `UART_P1_009`, `UART_P1_011`, `UART_P1_012` |
| UART_F_029 | UART 9-bit TX发送 | software、hardware address send | `UART_P2_004`, `UART_P2_005` |
| UART_F_030 | UART 9-bit RX接收 | software、hardware | `UART_P2_004`, `UART_P2_005` |
| UART_F_031 | UART 9-bit地址匹配/过滤 | match、mismatch、address/data | `UART_P2_005`, `UART_P2_010` |
| UART_F_032 | UART RTS/CTS自动流控 | AFCE、RTS/CTS | `UART_P2_006` |
| UART_F_033 | UART RTS/DTR手动控制 | assert、deassert | `UART_P2_007` |
| UART_F_034 | UART Modem Status/Delta | CTS/DSR/RI/DCD及变化；当前Formal Case动态覆盖CTS/DSR，RI/DCD保留Gap | `UART_P2_007` |
| UART_F_035 | UART DMA Single Request模式 | TX、RX request | `UART_P2_001`, `UART_P2_002`, `UART_P2_003` |
| UART_F_036 | UART DMA Multi Request模式 | TX、RX request | `UART_P2_001`, `UART_P2_002`, `UART_P2_003` |
| UART_F_037 | UART TX Halt/Resume控制 | 发送路径可暂停并恢复，恢复后数据路径保持正确 | `UART_P1_013` |
| UART_F_038 | UART IrDA SIR模式 | normal SIR | `UART_P3_004` |
| UART_F_039 | UART Low-Power SIR模式 | 低功耗SIR的固定或可选波特率由Capability声明 | `UART_P3_005` |
| UART_F_040 | UART RS485 Transfer模式 | full、half SW、half HW | `UART_P3_001` |
| UART_F_041 | UART RS485 DE/RE控制与极性 | manual、active high/low | `UART_P3_002` |
| UART_F_042 | UART RS485 DET/TAT时序 | DET、TAT | `UART_P3_003` |
| UART_F_043 | UART Scratch读写 | Snapshot可读Scratch；完整读写能力需要稳定写API | — |
| UART_F_044 | UART Shadow FIFO/Direct FIFO访问 | 支持Shadow配置和受控Direct FIFO访问语义 | `UART_P3_007`, `UART_P3_009` |
| UART_F_045 | UART Clock/Reset恢复 | gate、ungate、reset、reinit | — |
| UART_F_046 | UART Instance隔离 | DUT reset/config不影响Peer和Control | `UART_P1_001` |
| UART_F_047 | UART Long-Run TX/RX传输 | 重复、变长、固定随机种子 | `UART_P3_010` |
| UART_F_048 | UART Baud Rate/Bit Timing测量 | bit time、误差ppm | `UART_P3_006` |
| UART_F_049 | UART Access Protection/Timeout恢复 | 访问保护级别和访问超时恢复能力由Capability声明 | `UART_P3_008` |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| UART_P0_001 | P0 | 选定 UART 实例的运行时能力和身份信息 | 选定 UART 实例的运行时能力和身份信息测试 | SPEC |
| UART_P0_002 | P0 | UART 软件复位、默认配置和实例生命周期 | UART 软件复位、默认配置和实例生命周期测试 | SPEC |
| UART_P0_003 | P0 | UART 内部回环的基本发送、接收和回环开关 | UART 内部回环的基本发送、接收和回环开关测试 | SPEC |
| UART_P0_004 | P0 | UART 逻辑 DUT 与 Peer 之间的双向基本收发 | UART 逻辑 DUT 与 Peer 之间的双向基本收发测试 | SPEC |
| UART_P1_014 | P1 | UART 数据位、停止位和校验方式的合法帧格式组合 | UART 数据位、停止位和校验方式的合法帧格式组合测试 | SPEC |
| UART_P1_015 | P1 | UART 代表性波特率配置和双向收发 | UART 代表性波特率配置和双向收发测试 | SPEC |
| UART_P1_016 | P1 | UART FIFO 配置、边界收发和状态快照 | UART FIFO 配置、边界收发和状态快照测试 | SPEC |
| UART_P1_017 | P1 | UART 参数校验对非法输入的拒绝和合法路径恢复 | UART 参数校验对非法输入的拒绝和合法路径恢复测试 | SPEC |
| UART_P1_001 | P1 | DUT UART 实例隔离和独立复位 | DUT UART 实例隔离和独立复位测试 | SPEC |
| UART_P1_002 | P1 | UART RX data available 中断和事件计数 | UART RX data available 中断和事件计数测试 | SPEC |
| UART_P1_003 | P1 | UART TX empty 中断在发送完成阶段的触发和关闭 | UART TX empty 中断在发送完成阶段的触发和关闭测试 | SPEC |
| UART_P1_004 | P1 | UART RX FIFO 阈值中断边界 | UART RX FIFO 阈值中断边界测试 | SPEC |
| UART_P1_005 | P1 | UART TX FIFO 阈值中断边界 | UART TX FIFO 阈值中断边界测试 | SPEC |
| UART_P1_006 | P1 | UART character timeout 中断和低于阈值数据的收取 | UART character timeout 中断和低于阈值数据的收取测试 | SPEC |
| UART_P1_007 | P1 | UART 奇偶校验错误检测和恢复 | UART 奇偶校验错误检测和恢复测试 | SPEC |
| UART_P1_008 | P1 | UART 停止位失配导致的 framing error 检测和恢复 | UART 停止位失配导致的 framing error 检测和恢复测试 | SPEC |
| UART_P1_009 | P1 | UART RX overrun 错误检测和 FIFO 恢复 | UART RX overrun 错误检测和 FIFO 恢复测试 | SPEC |
| UART_P1_010 | P1 | UART break 发送、接收检测和退出恢复 | UART break 发送、接收检测和退出恢复测试 | SPEC |
| UART_P1_011 | P1 | UART 中断源的 mask 使能、关闭和 Service session 状态 | UART 中断源的 mask 使能、关闭和 Service session 状态测试 | SPEC |
| UART_P1_012 | P1 | UART busy detect 中断、清除条件和恢复路径 | UART busy detect 中断、清除条件和恢复路径测试 | SPEC |
| UART_P1_013 | P1 | UART 发送 halt、resume 和数据路径恢复 | UART 发送 halt、resume 和数据路径恢复测试 | SPEC |
| UART_P2_001 | P2 | UART TX DMA 从内存到 UART TX 端点的单次传输 | UART TX DMA 从内存到 UART TX 端点的单次传输测试 | SPEC |
| UART_P2_002 | P2 | UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输 | UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输测试 | SPEC |
| UART_P2_003 | P2 | UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输 | UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输测试 | SPEC |
| UART_P2_004 | P2 | UART 9-bit 软件数据双向收发及普通模式恢复 | UART 9-bit 软件数据双向收发及普通模式恢复测试 | SPEC |
| UART_P2_005 | P2 | UART 9-bit 硬件地址匹配和不匹配地址过滤 | UART 9-bit 硬件地址匹配和不匹配地址过滤测试 | SPEC |
| UART_P2_006 | P2 | UART RTS/CTS 自动流控的暂停和恢复 | UART RTS/CTS 自动流控的暂停和恢复测试 | SPEC |
| UART_P2_007 | P2 | UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态 | UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态测试 | SPEC |
| UART_P2_008 | P2 | UART 软件复位后的实例身份和数据路径恢复 | UART 软件复位后的实例身份和数据路径恢复测试 | SPEC |
| UART_P3_010 | P3 | UART 双向混合收发 20 轮稳定性能力 | UART 双向混合收发 20 轮稳定性能力测试 | SPEC |
| UART_P2_010 | P2 | UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径 | UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径测试 | SPEC |
| UART_P3_001 | P3 | DUT在每种模式只做一组短双向数字帧 | DUT在每种模式只做一组短双向数字帧测试 | PLAN |
| UART_P3_002 | P3 | DUT逐极性控制DE/RE | DUT逐极性控制DE/RE测试 | PLAN |
| UART_P3_003 | P3 | DUT发送短帧 | DUT发送短帧测试 | PLAN |
| UART_P3_004 | P3 | DUT通过SIR收发器或可信数字模型与Peer通信 | DUT通过SIR收发器或可信数字模型与Peer通信测试 | PLAN |
| UART_P3_005 | P3 | 配置DUT低功耗SIR | 配置DUT低功耗SIR测试 | PLAN |
| UART_P3_006 | P3 | 独立观察DUT TX位宽、帧宽和长期平均波特率 | 独立观察DUT TX位宽、帧宽和长期平均波特率测试 | PLAN |
| UART_P3_007 | P3 | UART Shadow FIFO 配置（SFE/SRT/STET） | UART Shadow FIFO 配置（SFE/SRT/STET）测试 | SPEC |
| UART_P3_008 | P3 | 依据安全/总线设计契约 | 依据安全/总线设计契约测试 | PLAN |
| UART_P3_009 | P3 | UART Direct FIFO 访问（FAR/TFR/RFW） | UART Direct FIFO 访问（FAR/TFR/RFW）测试 | SPEC |

## 3. Machine-readable Case Contract

> `ET_CASE_SPEC` 是已注册、已实现的 Formal Case；`ET_CASE_PLAN` 是规划完成但尚未实现/注册的 Case。报告只消费 SPEC。
> 本节只保存跨芯片稳定测试语义；具体芯片 SVD/Register/SDK/历史证据只存在于 `<CHIP>_<ip>.md`。

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P0_001
case_name: 选定 UART 实例的运行时能力和身份信息测试
report_feature: |-
  1. UART Instance集合
  2. UART Component能力与Identity
p_level: P0
feature_refs:
- UART_F_001
- UART_F_004
method:
  inputs:
  - 目标实例：Capability/Runtime交集选出的代表UART DUT。
  - 身份Expected：Runtime Capability合法，组件参数/版本/类型来自目标侧Snapshot；Scratch仅验证读值，本Case不冒充Scratch写证明。
  steps:
  - 能力确认：读取UART Runtime Capability，取得Feature mask、最小/最大波特率和最大读写长度。
  - 能力确认：检查Capability范围自洽，并确认目标逻辑实例可由UART Service访问。
  - 代表波特率初始化：使用代表性合法波特率初始化目标UART实例。
  - 组件身份快照读取：读取UART_COMPONENT Snapshot，取得component parameter/version/peripheral id/scratch。
  - 能力与身份取证：把Capability与组件身份原始值先写入Canonical Observation，再执行合法性判断。
  - 状态恢复：反初始化本Case获得的UART实例并汇总身份/能力证据；普通/别名地址和Scratch写能力不在本Case扩大证明。
  observations:
  - Runtime能力：UART_CAPABILITIES.FEATURES/MIN_BAUDRATE/MAX_BAUDRATE/MAX_READ_SIZE/MAX_WRITE_SIZE必须构成合法范围。
  - 组件身份：UART_COMPONENT.COMPONENT_PARAMETER/COMPONENT_VERSION/PERIPHERAL_ID来自目标侧Snapshot。
  - 身份观测：Scratch只记录UART_COMPONENT.SCRATCH读值，不把单次读取写成Scratch读写已闭合。
  pass_criteria:
  - 波特率能力范围：MIN_BAUDRATE>0且MIN_BAUDRATE<=MAX_BAUDRATE。
  - 读写长度能力：MAX_READ_SIZE和MAX_WRITE_SIZE均大于0。
  - 组件身份完整性：组件parameter/version/peripheral id均取得稳定目标侧值。
  - 能力证明边界：不宣称F003 alias动态访问或F043 Scratch写证明。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全自主；只使用`uart_dut_handle`。
  bench: 完全自主；只使用`uart_dut_handle`。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: capabilities_features
  label: 运行时能力Feature位图
  source: measurement
  role: actual
  format: hex32
- key: component_parameter
  label: UART_COMPONENT.COMPONENT_PARAMETER
  source: dut
  role: actual
  format: hex32
- key: component_version
  label: UART_COMPONENT.COMPONENT_VERSION
  source: dut
  role: actual
  format: hex32
- key: peripheral_id
  label: UART_COMPONENT.PERIPHERAL_ID
  source: dut
  role: actual
  format: hex32
gap:
- scratch_write_proof_gap
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P0_002
case_name: UART 软件复位、默认配置和实例生命周期测试
report_feature: |-
  1. UART软件复位
  2. UART FIFO使能
  3. UART FIFO Depth/Level/Status
p_level: P0
feature_refs:
- UART_F_005
- UART_F_012
- UART_F_013
method:
  inputs:
  - 测试数据：目标UART DUT；复位前自定义7E2配置；复位后显式恢复115200 8N1；1 Byte恢复Payload。
  steps:
  - 复位前自定义帧配置：以7 data bits/even parity/2 stop bits初始化DUT并读取复位前组件Snapshot。
  - 状态恢复：执行UART software_reset，结束旧实例生命周期。
  - 复位后显式重配：显式以115200 8N1重新初始化DUT；本步骤不是读取硬件reset默认值。
  - 复位后身份与FIFO读取：读取复位后Snapshot，比较组件parameter/version/peripheral id并读取TX/RX FIFO level。
  - 复位后回环恢复激励：开启内部loopback，Capture先启动，再发送1 Byte恢复Payload并等待接收完成。
  - 复位恢复证据汇总：记录复位前后身份/FIFO终态/恢复实际数据，随后关闭loopback并反初始化。
  observations:
  - 组件身份：reset前后UART_COMPONENT.COMPONENT_PARAMETER/VERSION/PERIPHERAL_ID保持一致。
  - FIFO终态：复位后显式re-init后UART_FIFO.TX_LEVEL=0且UART_FIFO.RX_LEVEL=0。
  - 恢复数据：UART_CAPTURE.DATA等于1 Byte Expected。
  pass_criteria:
  - 复位前后身份：软件复位前后组件身份稳定。
  - 状态判据：重新初始化后TX/RX FIFO level均为0。
  - 复位后数据恢复：恢复发送/接收长度均为1且数据一致。
  - 状态判据：不宣称独立RX/TX FIFO reset或reset后未经初始化的默认8N1 readback。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: DUT内部loopback；不复位Control或Peer handle。
  bench: DUT内部loopback；不复位Control或Peer handle。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: identity_stable
  label: 软件复位前后组件身份稳定
  source: measurement
  role: actual
  format: bool
- key: final_tx_fifo_level
  label: UART_FIFO.TX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: final_rx_fifo_level
  label: UART_FIFO.RX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: recovery_actual_data
  label: UART_CAPTURE.DATA恢复数据
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P0_003
case_name: UART 内部回环的基本发送、接收和回环开关测试
report_feature: |-
  1. UART Full-Duplex TX/RX收发
  2. UART Internal Loopback回环
  3. UART FIFO使能
  4. UART Blocking/Non-blocking TX发送
  5. UART TX完成/超时
p_level: P0
feature_refs:
- UART_F_010
- UART_F_011
- UART_F_012
- UART_F_017
- UART_F_018
method:
  inputs:
  - 测试数据：DUT内部loopback；115200 8N1；1/16/17/64 Byte确定性Payload矩阵。
  steps:
  - 功能配置：初始化DUT为115200 8N1并建立loopback/capture cleanup责任。
  - 资源准备：按1/16/17/64 Byte顺序构造不同seed的确定性Payload。
  - 回环捕获启动：每轮开启内部loopback并先启动等长Capture。
  - 测试激励：调用有界UART write发送本轮Payload并等待Capture完成。
  - 证据采集：在每轮决定性Assert前记录实际UART_CAPTURE.DATA、发送数和接收数。
  - 结果判定：核对全部长度后关闭loopback、反初始化并发布一次完整矩阵Artifact。
  observations:
  - 数据观测：每轮UART_CAPTURE.DATA必须逐字节等于对应Payload。
  - 数据观测：每轮发送/接收计数必须等于本轮长度。
  pass_criteria:
  - 覆盖判据：1/16/17/64 Byte四条路径全部执行。
  - 数据判据：每轮发送和接收长度完整。
  - 数据判据：每轮实际数据与Expected逐字节一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 只使用`uart_dut_handle`。
  bench: 只使用`uart_dut_handle`。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: actual_capture_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: tx_completed
  label: 实际发送字节数
  source: measurement
  role: actual
  format: count
- key: rx_completed
  label: 实际接收字节数
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P0_004
case_name: UART 逻辑 DUT 与 Peer 之间的双向基本收发测试
report_feature: |-
  1. UART Full-Duplex TX/RX收发
p_level: P0
feature_refs:
- UART_F_010
method:
  inputs:
  - 测试数据：DUT与可信Peer交叉TX/RX；相同115200 8N1；两个方向各64 Byte不同Payload。
  steps:
  - 功能配置：初始化DUT与Peer为相同帧格式。
  - 资源准备：构造DUT→Peer与Peer→DUT两组不同64 Byte确定性Payload。
  - 测试激励：先启动Peer Capture，再由DUT发送第一组Payload并等待Peer完成。
  - 测试激励：先启动DUT Capture，再由Peer发送第二组Payload并等待DUT完成。
  - 证据采集：在Assert前分别记录PEER_UART.RX_CAPTURE与UART_CAPTURE.DATA原始数据及两个方向计数。
  - 结果判定：比较两个方向数据后按所有权反初始化Peer/DUT并发布完整双向Artifact。
  observations:
  - 数据观测：PEER_UART.RX_CAPTURE应等于DUT→Peer Payload。
  - 数据观测：UART_CAPTURE.DATA应等于Peer→DUT Payload。
  pass_criteria:
  - 数据判据：两个方向发送/接收长度均为64。
  - 数据判据：DUT→Peer数据逐字节一致。
  - 数据判据：Peer→DUT数据逐字节一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 使用逻辑DUT↔Peer pair；当前bench解析为DUT UART↔Peer UART。
  bench: 使用逻辑DUT↔Peer pair；当前bench解析为DUT UART↔Peer UART。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_rx_data
  label: PEER_UART.RX_CAPTURE
  source: peer
  role: actual
  format: bytes_hex
- key: dut_rx_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: dut_to_peer_match
  label: DUT到Peer数据一致
  source: measurement
  role: actual
  format: bool
- key: peer_to_dut_match
  label: Peer到DUT数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_014
case_name: UART 数据位、停止位和校验方式的合法帧格式组合测试
report_feature: |-
  1. UART Data Bits配置
  2. UART Stop Bits配置
  3. UART Parity配置
p_level: P1
feature_refs:
- UART_F_007
- UART_F_008
- UART_F_009
method:
  inputs:
  - 合法帧矩阵：5-bit/1.5/none、6-bit/2/even、7-bit/1/odd、8-bit/2/stick0、8-bit/1/stick1。
  steps:
  - 功能配置：逐组合使用独立DUT/Peer生命周期初始化相同帧格式。
  - 资源准备：按data_bits对确定性Payload进行有效位裁剪。
  - 测试激励：先启动Peer Capture，由DUT发送Payload并记录Peer实际数据。
  - 测试激励：再启动DUT Capture，由Peer发送相同Payload并记录DUT实际数据。
  - 证据采集：在每组合决定性Assert前记录两个方向Capture与发送/接收计数。
  - 结果判定：判断双向长度与数据后清理当前组合，再进入下一组合。
  - 结果判定：全部五组合完成后发布一次完整矩阵Artifact。
  observations:
  - 数据观测：PEER_UART.RX_CAPTURE与UART_CAPTURE.DATA分别证明两个方向的实际帧数据。
  - 配置观测：请求帧格式是Measurement/配置，不冒充寄存器readback。
  pass_criteria:
  - 覆盖判据：五个代表性合法组合全部执行。
  - 数据判据：每组合两个方向发送/接收长度完整。
  - 数据判据：每组合两个方向数据逐字节一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R2
  full_coverage_level: R2
  board: '`uart_dut_handle` + `uart_peer_handle`；当前映射DUT UART↔Peer UART，每个参数子项单独报告。'
  bench: '`uart_dut_handle` + `uart_peer_handle`；当前映射DUT UART↔Peer UART，每个参数子项单独报告。'
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_actual_data
  label: Peer实际接收数据
  source: peer
  role: actual
  format: bytes_hex
- key: dut_actual_data
  label: DUT实际接收数据
  source: dut
  role: actual
  format: bytes_hex
- key: all_data_match
  label: 全部帧格式双向数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_015
case_name: UART 代表性波特率配置和双向收发测试
report_feature: |-
  1. UART Baud Rate配置
p_level: P1
feature_refs:
- UART_F_006
method:
  inputs:
  - 能力约束：DUT/Peer Capability共同波特率区间；区间内最小、9600、115200、1M、1000003等代表候选。
  steps:
  - 能力确认：读取DUT与Peer Runtime Capability并计算共同baudrate区间。
  - 资源准备：在共同区间生成去重后的最小/常用/高速/非整除候选集合。
  - 功能配置：逐候选使用独立生命周期把DUT/Peer初始化为相同波特率。
  - 测试激励：执行DUT→Peer短帧并记录Peer实际Capture。
  - 测试激励：执行Peer→DUT短帧并记录DUT实际Capture。
  - 证据采集：在Assert前记录请求baudrate、双向Capture和计数并判断数据一致性。
  - 结果判定：全部候选完成后汇总；绝对bit-time/ppm不在本Case声称覆盖。
  observations:
  - 数据观测：每候选PEER_UART.RX_CAPTURE与UART_CAPTURE.DATA均与Expected一致。
  - 时序观测：请求baudrate来自能力交集，是配置Measurement而非绝对时序Observation。
  pass_criteria:
  - 波特率候选覆盖：共同范围内至少执行一个候选。
  - 数据判据：所有候选双向发送/接收完整。
  - 数据判据：所有候选双向数据一致。
  - 时序判据：不宣称P3_006绝对波特率/ppm。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R2
  full_coverage_level: R2
  board: '`uart_dut_handle` + `uart_peer_handle`；当前映射DUT UART↔Peer UART。本Case只证明DUT在该配置下通信，不声称证明绝对波特率精度。'
  bench: '`uart_dut_handle` + `uart_peer_handle`；当前映射DUT UART↔Peer UART。本Case只证明DUT在该配置下通信，不声称证明绝对波特率精度。'
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: requested_baudrate
  label: 请求波特率
  source: measurement
  role: config
  format: decimal
- key: peer_actual_data
  label: Peer实际接收数据
  source: peer
  role: actual
  format: bytes_hex
- key: dut_actual_data
  label: DUT实际接收数据
  source: dut
  role: actual
  format: bytes_hex
- key: all_data_match
  label: 全部候选双向数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_016
case_name: UART FIFO 配置、边界收发和状态快照测试
report_feature: |-
  1. UART FIFO使能
  2. UART FIFO Depth/Level/Status
  3. UART TX FIFO阈值
  4. UART RX FIFO阈值
  5. UART Blocking/Non-blocking TX发送
  6. UART TX完成/超时
p_level: P1
feature_refs:
- UART_F_012
- UART_F_013
- UART_F_015
- UART_F_016
- UART_F_017
- UART_F_018
method:
  inputs:
  - 测试数据：DUT FIFO enable；TX threshold=2、RX threshold=4；1/15/16/17/32 Byte边界Payload。
  steps:
  - 功能配置：初始化DUT并配置FIFO enable、TX threshold=2、RX threshold=4。
  - 资源准备：逐1/15/16/17/32 Byte读取发送前UART FIFO level。
  - 功能配置：开启loopback并启动等长Capture。
  - 有界等待：有界发送当前Payload并等待Capture完成。
  - 证据采集：读取发送后UART_FIFO.TX_LEVEL/RX_LEVEL并在Assert前记录实际Capture。
  - 结果判定：判断数据与终态RX level后进入下一长度。
  - 结果判定：发布一次完整边界矩阵Artifact；精确16 Byte physical-depth不由长度边界现象冒充独立动态Oracle。
  observations:
  - 数据观测：每轮UART_CAPTURE.DATA必须正确。
  - 状态观测：UART_FIFO.TX_LEVEL/RX_LEVEL提供运行时FIFO状态；终态RX level应为0。
  pass_criteria:
  - 覆盖判据：1/15/16/17/32 Byte全部执行。
  - 数据判据：每轮发送/接收完整且数据一致。
  - 状态判据：每轮终态RX FIFO level=0。
  - 状态判据：不宣称独立FIFO reset；精确physical depth只保留静态/芯片事实。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 只使用`uart_dut_handle`内部loopback。
  bench: 只使用`uart_dut_handle`内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: actual_capture_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: before_rx_fifo_level
  label: 发送前UART_FIFO.RX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: after_rx_fifo_level
  label: 发送后UART_FIFO.RX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: all_data_match
  label: 全部边界数据一致
  source: measurement
  role: actual
  format: bool
gap:
- fifo_depth_dynamic_proof_gap
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_017
case_name: UART 参数校验对非法输入的拒绝和合法路径恢复测试
report_feature: |-
  1. UART Instance集合
p_level: P1
feature_refs:
- UART_F_001
method:
  inputs:
  - 7项非法公共API输入：0 baud、非法data bits、非法stop bits、零长度write/read/capture、非法TX threshold；随后8 Byte合法恢复。
  steps:
  - 非法参数门禁：依次调用七项非法操作并要求公共Driver在设备传输前抛ValueError。
  - 非法请求拒绝计数：记录每项拒绝结果并累计rejected_count。
  - 合法路径重新初始化：以合法115200 8N1初始化DUT。
  - 合法路径捕获启动：开启内部loopback并启动8 Byte Capture。
  - 测试激励：发送合法恢复Payload并等待Capture完成。
  - 拒绝与恢复证据记录：在Assert前记录rejected_count与恢复实际数据。
  - 结果判定：核对七项均拒绝且合法路径未被破坏后清理。
  observations:
  - 配置观测：非法请求属于公共Driver contract Measurement，不冒充DUT寄存器。
  - 数据观测：合法恢复UART_CAPTURE.DATA必须等于Expected。
  pass_criteria:
  - 错误判据：七项非法请求全部被ValueError拒绝。
  - 拒绝后合法初始化：拒绝发生后合法初始化仍成功。
  - 拒绝后数据恢复：8 Byte恢复发送/接收完整且数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全自主；assert构建和release构建分别定义预期。
  bench: 完全自主；assert构建和release构建分别定义预期。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: rejected_count
  label: 非法请求拒绝数
  source: measurement
  role: actual
  format: count
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: recovery_data_match
  label: 恢复数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_001
case_name: DUT UART 实例隔离和独立复位测试
report_feature: |-
  1. UART Instance集合
  2. UART IRQ路由
  3. UART Instance隔离
p_level: P1
feature_refs:
- UART_F_001
- UART_F_002
- UART_F_046
method:
  inputs:
  - 测试数据：DUT与Peer两个独立UART实例；DUT reset/reinit；DUT loopback和Peer→DUT短Payload。
  steps:
  - 功能配置：初始化DUT和Peer并读取Peer组件身份Snapshot。
  - 状态恢复：仅对DUT执行software reset并重新初始化，禁止触碰Peer生命周期。
  - DUT回环恢复取证：在DUT执行一次内部loopback恢复并记录实际Capture。
  - 测试激励：关闭DUT loopback后，由Peer向DUT发送另一组Payload并记录DUT Capture。
  - Peer身份隔离取证：再次读取Peer组件身份Snapshot并在Assert前保存before/after原始字段。
  - 结果判定：比较Peer身份和两条DUT数据路径，随后按所有权清理DUT/Peer。
  observations:
  - 身份观测：Peer UART_COMPONENT身份字段在DUT reset前后不变。
  - 数据观测：DUT reset后loopback与Peer→DUT UART_CAPTURE.DATA均正确。
  pass_criteria:
  - Peer身份隔离：Peer component parameter/version/peripheral id保持不变。
  - DUT复位后回环恢复：DUT内部恢复数据一致。
  - 数据判据：Peer→DUT数据一致。
  - 配置判据：持续控制命令可达只作为平台存活事实，不冒充UART0寄存器身份证明。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: DUT为唯一被测实例；Peer和Control只作为隔离观察对象，不执行全实例功能遍历。
  bench: DUT为唯一被测实例；Peer和Control只作为隔离观察对象，不执行全实例功能遍历。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_component_parameter_before
  label: Peer reset前COMPONENT_PARAMETER
  source: peer
  role: actual
  format: hex32
- key: peer_component_parameter_after
  label: Peer reset后COMPONENT_PARAMETER
  source: peer
  role: actual
  format: hex32
- key: peer_identity_unchanged
  label: Peer组件身份保持不变
  source: measurement
  role: actual
  format: bool
- key: peer_to_dut_actual_data
  label: DUT接收Peer数据
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_002
case_name: UART RX data available 中断和事件计数测试
report_feature: |-
  1. UART RX_DATA_AVAILABLE IRQ中断
  2. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_019
- UART_F_028
method:
  inputs:
  - 测试数据：DUT内部loopback；RX_READY中断；4 Byte确定性Payload。
  steps:
  - RX_READY中断配置：初始化DUT并使能RX_READY中断。
  - RX_READY基线快照：读取激励前UART ISR session基线event/fault/pending/active状态。
  - RX_READY捕获启动：开启loopback并先启动4 Byte Capture。
  - 测试激励：发送Payload并等待Capture完成。
  - RX_READY事件取证：读取激励后ISR session状态，在Assert前记录UART_CAPTURE.DATA、PENDING/ACTIVE mask及计数增量。
  - 结果判定：判断数据、event增量、source识别和fault增量后关闭RX_READY并清理。
  observations:
  - 数据观测：UART_CAPTURE.DATA等于Expected。
  - 中断观测：UART_ISR.PENDING_MASK/ACTIVE_MASK中至少一个阶段识别RX_READY；Service event_count产生正增量。
  pass_criteria:
  - 数据判据：发送/接收完整且数据一致。
  - 中断判据：event_count_delta>0。
  - 计数判据：fault_count_delta=0。
  - 中断判据：RX_READY来源被Service IRQ session识别。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback。
  bench: 内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: rx_actual_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: irq_pending_mask
  label: UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: event_count_delta
  label: RX_READY事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_003
case_name: UART TX empty 中断在发送完成阶段的触发和关闭测试
report_feature: |-
  1. UART TX_EMPTY IRQ中断
  2. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_020
- UART_F_028
method:
  inputs:
  - 测试数据：DUT内部loopback；TX_READY中断；8 Byte确定性Payload。
  steps:
  - TX_READY基线建立：初始化DUT并读取TX_READY使能前IRQ session基线。
  - TX_READY与回环配置：使能TX_READY中断并开启内部loopback。
  - 测试激励：启动8 Byte Capture后发送确定性Payload。
  - 有界等待：等待Capture完成并读取发送完成阶段IRQ session状态。
  - 证据采集：在Assert前记录实际Capture、PENDING/ACTIVE mask、event/fault增量。
  - 结果判定：关闭TX_READY并核对数据/来源/计数后执行cleanup。
  observations:
  - 数据观测：UART_CAPTURE.DATA等于Expected。
  - 中断观测：发送完成阶段UART_ISR.PENDING_MASK/ACTIVE_MASK识别TX_READY且event_count增加。
  pass_criteria:
  - 数据判据：数据完整一致。
  - 中断判据：TX_READY event_count_delta>0。
  - 计数判据：fault_count_delta=0。
  - 数据判据：TX_READY来源被识别。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback。
  bench: 内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: tx_actual_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: irq_pending_mask
  label: UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: event_count_delta
  label: TX_READY事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_004
case_name: UART RX FIFO 阈值中断边界测试
report_feature: |-
  1. UART RX FIFO阈值
  2. UART RX_DATA_AVAILABLE IRQ中断
p_level: P1
feature_refs:
- UART_F_016
- UART_F_019
method:
  inputs:
  - 参数矩阵：RX FIFO threshold矩阵1/4/8/14；每个阈值使用threshold-1负对照和threshold正对照；内部loopback。
  steps:
  - 功能配置：初始化DUT并为当前RX threshold设置FIFO配置与RX_READY中断。
  - 阈值负对照观测：读取本轮IRQ session基线，发送threshold-1字节并在有界窗口观察RX_READY是否未形成阈值事件。
  - 阈值IRQ基线重建：完成负对照数据收取/清理，重新建立当前threshold的独立IRQ基线。
  - 测试激励：发送恰好threshold字节并等待Capture/IRQ事实形成。
  - 阈值双对照取证：在Assert前记录负对照/正对照PENDING/ACTIVE mask、event增量和实际Capture。
  - 阈值矩阵判定：逐阈值判断`below无阈值事件 + at有事件 + 数据正确`，关闭IRQ后进入下一阈值。
  - 结果判定：四个阈值完成后发布一次完整边界矩阵Artifact并清理UART。
  observations:
  - 中断观测：每个阈值的below/at UART_ISR状态必须可区分。
  - 数据观测：正对照UART_CAPTURE.DATA必须等于对应Payload。
  pass_criteria:
  - 覆盖判据：1/4/8/14四个阈值全部执行。
  - 中断判据：每个threshold-1负对照不产生对应阈值事件。
  - 中断判据：每个threshold正对照产生RX_READY事件。
  - 数据判据：全部数据完整且fault增量为0。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback；每个阈值独立报告。
  bench: 内部loopback；每个阈值独立报告。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: below_event_delta
  label: threshold-1 RX_READY事件增量
  source: measurement
  role: actual
  format: count
- key: at_event_delta
  label: threshold RX_READY事件增量
  source: measurement
  role: actual
  format: count
- key: actual_capture_data
  label: threshold正对照UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_005
case_name: UART TX FIFO 阈值中断边界测试
report_feature: |-
  1. UART TX FIFO阈值
  2. UART TX_EMPTY IRQ中断
p_level: P1
feature_refs:
- UART_F_015
- UART_F_020
method:
  inputs:
  - 参数矩阵：TX FIFO threshold矩阵0/2/4/8；Halt/write_partial/TX FIFO level与TX_READY session用于形成可区分in-flight状态。
  steps:
  - TX阈值测试环境配置：初始化DUT、开启loopback并配置当前TX threshold与TX_READY中断。
  - TX阈值前在途状态：设置TX Halt，向FIFO写入受控短Payload并读取UART_FIFO.TX_LEVEL建立阈值前in-flight状态。
  - Halt窗口IRQ取证：在Halt窗口读取IRQ session，确认当前状态不会被发送完成自然事件混淆。
  - 测试激励：解除Halt，让同一FIFO数据继续发送并等待Capture完成。
  - TX阈值过程状态采集：读取发送过程中/终态TX FIFO level与TX_READY IRQ session事实。
  - TX阈值证据汇总：在Assert前记录阈值、FIFO level、event/fault增量及实际Capture。
  - 结果判定：逐阈值判断可区分边界；若某阈值无法形成确定in-flight条件则报告真实Gap而不是用单次TX_READY替代。
  observations:
  - 状态观测：UART_FIFO.TX_LEVEL在Halt/Resume链路中提供独立in-flight事实。
  - 中断观测：TX_READY Service IRQ session必须与发送完成/阈值条件一致，实际Capture不得损坏。
  pass_criteria:
  - 阈值矩阵证据完整性：0/2/4/8四个阈值均形成可审计的in-flight/终态证据或明确报告Gap。
  - 中断判据：TX_READY事件只在解除Halt后的真实发送链路中判定。
  - 数据判据：全部实际数据一致且fault增量为0。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback。
  bench: 内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: halted_tx_fifo_level
  label: Halt窗口UART_FIFO.TX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: resumed_tx_fifo_level
  label: Resume终态UART_FIFO.TX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: resumed_event_delta
  label: Resume后TX_READY事件增量
  source: measurement
  role: actual
  format: count
- key: actual_capture_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_006
case_name: UART character timeout 中断和低于阈值数据的收取测试
report_feature: |-
  1. UART CHARACTER_TIMEOUT IRQ中断
  2. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_021
- UART_F_028
method:
  inputs:
  - 测试数据：RX threshold=14；CHARACTER_TIMEOUT中断；低于阈值的2 Byte Payload。
  steps:
  - 字符超时FIFO配置：初始化DUT并把RX FIFO threshold配置为14。
  - 字符超时中断基线：使能CHARACTER_TIMEOUT中断并读取IRQ session基线。
  - 字符超时捕获启动：开启内部loopback并先启动2 Byte Capture。
  - 测试激励：发送仅2 Byte Payload，使数据不足以到达RX FIFO阈值。
  - 证据采集：用有界wait_irq_event等待CHARACTER_TIMEOUT，并在Assert前记录Capture与ISR状态。
  - 结果判定：核对数据、timeout来源、event/fault增量后关闭中断并清理。
  observations:
  - 数据观测：UART_CAPTURE.DATA应为2 Byte Expected。
  - 中断观测：UART_ISR.PENDING_MASK/ACTIVE_MASK识别CHARACTER_TIMEOUT且event_count增加。
  pass_criteria:
  - 数据判据：2 Byte数据完整一致。
  - 中断判据：CHARACTER_TIMEOUT事件增量>0。
  - 计数判据：fault_count_delta=0。
  - 字符超时来源：CHARACTER_TIMEOUT来源被识别。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback。
  bench: 内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: timeout_actual_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: irq_pending_mask
  label: UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: event_count_delta
  label: CHARACTER_TIMEOUT事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_007
case_name: UART 奇偶校验错误检测和恢复测试
report_feature: |-
  1. UART Line Error IRQ/Status
  2. UART PARITY_ERROR状态
  3. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_022
- UART_F_023
- UART_F_028
method:
  inputs:
  - 测试数据：DUT ODD、Peer EVEN parity mismatch；LINE_ERROR中断；失配与恢复各4 Byte Payload。
  steps:
  - 功能配置：初始化DUT为ODD、Peer为EVEN并使能DUT LINE_ERROR。
  - 奇偶失配基线与捕获：读取失配激励前IRQ session基线并启动DUT Capture。
  - 奇偶失配错误采集：Peer发送失配Payload，等待DUT接收后读取UART_STATUS.ERROR_FLAGS与IRQ session。
  - 奇偶错误事件取证：在Assert前记录PARITY错误、IRQ mask/计数和失配阶段实际数据。
  - 有界等待：完整退出失配配置，再把DUT/Peer统一初始化为NONE parity。
  - 奇偶错误后恢复取证：Peer发送恢复Payload，记录DUT实际Capture并判断恢复数据。
  - 结果判定：按所有权关闭中断、Capture和两端UART。
  observations:
  - 错误观测：UART_STATUS.ERROR_FLAGS必须包含PARITY。
  - 中断观测：LINE_ERROR Service IRQ session必须产生事件。
  - 数据观测：恢复阶段UART_CAPTURE.DATA必须正确。
  pass_criteria:
  - 错误判据：失配阶段PARITY flag=1。
  - 中断判据：LINE_ERROR event_count_delta>0且fault增量=0。
  - 错误后帧恢复：恢复帧完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；Peer仅产生错误刺激，覆盖归属于DUT。
  bench: 逻辑DUT↔Peer pair；Peer仅产生错误刺激，覆盖归属于DUT。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: error_flags
  label: UART_STATUS.ERROR_FLAGS
  source: dut
  role: actual
  format: hex32
- key: irq_pending_mask
  label: UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: event_count_delta
  label: LINE_ERROR事件增量
  source: measurement
  role: actual
  format: count
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_008
case_name: UART 停止位失配导致的 framing error 检测和恢复测试
report_feature: |-
  1. UART Line Error IRQ/Status
  2. UART FRAMING_ERROR状态
  3. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_022
- UART_F_024
- UART_F_028
method:
  inputs:
  - 测试数据：Bench声明stop_mismatch_framing刺激；DUT 2 stop、Peer 1 stop；失配与恢复Payload。
  steps:
  - 帧错误环境门禁：在任何状态修改前确认Bench声明deterministic framing-error stimulus。
  - 功能配置：初始化DUT为2 stop、Peer为1 stop并使能DUT LINE_ERROR。
  - 帧错误基线与刺激：读取IRQ基线，启动DUT Capture，由Peer发送失配Payload。
  - 帧错误状态取证：读取UART_STATUS.ERROR_FLAGS与IRQ session并在Assert前记录FRAMING事实。
  - 有界等待：完整退出失配配置，再把DUT/Peer恢复默认帧格式。
  - 帧错误后恢复取证：由Peer发送恢复Payload并记录DUT实际Capture。
  - 结果判定：核对错误/IRQ/恢复数据后按所有权清理。
  observations:
  - 错误观测：UART_STATUS.ERROR_FLAGS必须包含FRAMING。
  - 错误观测：LINE_ERROR Service session产生事件。
  - 数据观测：恢复UART_CAPTURE.DATA正确。
  pass_criteria:
  - 帧错误合法跳过：无Bench确定性刺激时合法SKIP。
  - 中断判据：有刺激时FRAMING flag=1且LINE_ERROR事件增加。
  - 中断判据：IRQ fault增量=0。
  - 错误后数据恢复：恢复数据完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；若Peer无法稳定产生FE，按capability/board声明调整刺激，不使用随机噪声。
  bench: 逻辑DUT↔Peer pair；若Peer无法稳定产生FE，按capability/board声明调整刺激，不使用随机噪声。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: error_flags
  label: UART_STATUS.ERROR_FLAGS
  source: dut
  role: actual
  format: hex32
- key: event_count_delta
  label: LINE_ERROR事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_009
case_name: UART RX overrun 错误检测和 FIFO 恢复测试
report_feature: |-
  1. UART Line Error IRQ/Status
  2. UART RX_OVERRUN状态
  3. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_022
- UART_F_025
- UART_F_028
method:
  inputs:
  - 测试数据：DUT内部loopback；LINE_ERROR中断；64 Byte RX压力刺激；8 Byte恢复Payload。
  steps:
  - 功能配置：初始化DUT、使能LINE_ERROR并开启内部loopback。
  - 溢出测试基线：读取IRQ session基线，不启动Capture以保持RX读取压力。
  - RX FIFO溢出刺激：发送64 Byte确定性数据形成受控RX FIFO压力。
  - 溢出状态与事件取证：读取UART_STATUS.ERROR_FLAGS与IRQ session，在Assert前记录OVERRUN/事件事实。
  - 状态恢复：执行software reset并重新初始化DUT，重新开启loopback。
  - 溢出后恢复激励：启动8 Byte Capture并发送恢复Payload，记录实际恢复数据。
  - 结果判定：核对OVERRUN/LINE_ERROR和恢复数据后清理。
  observations:
  - 错误观测：UART_STATUS.ERROR_FLAGS必须包含OVERRUN。
  - 错误观测：LINE_ERROR Service session事件增加。
  - 数据观测：reset后UART_CAPTURE.DATA等于恢复Payload。
  pass_criteria:
  - 溢出标志：OVERRUN flag=1。
  - 中断判据：LINE_ERROR event_count_delta>0且fault增量=0。
  - 溢出后数据恢复：软件复位后8 Byte恢复数据完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback优先。
  bench: 内部loopback优先。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: error_flags
  label: UART_STATUS.ERROR_FLAGS
  source: dut
  role: actual
  format: hex32
- key: event_count_delta
  label: LINE_ERROR事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_010
case_name: UART break 发送、接收检测和退出恢复测试
report_feature: |-
  1. UART Line Error IRQ/Status
  2. UART BREAK TX/RX检测
p_level: P1
feature_refs:
- UART_F_022
- UART_F_026
method:
  inputs:
  - 测试数据：DUT/Peer；Peer Break=10ms；DUT LINE_ERROR；4 Byte恢复Payload。
  steps:
  - 功能配置：初始化DUT/Peer并使能DUT LINE_ERROR。
  - Break基线与拉低刺激：读取IRQ session基线后由Peer主动assert Break。
  - Break刺激与取证：保持Break约10ms后release，DUT读取UART_STATUS.ERROR_FLAGS与IRQ session。
  - Break状态与事件取证：在Assert前记录BREAK flag、IRQ来源/计数和fault增量。
  - 测试激励：启动DUT Capture，由Peer发送正常恢复Payload。
  - Break退出后恢复取证：记录恢复UART_CAPTURE.DATA并判断Break退出后的数据路径。
  - 结果判定：确保Peer Break release、关闭IRQ并反初始化两端。
  observations:
  - 错误观测：UART_STATUS.ERROR_FLAGS必须包含BREAK。
  - 错误观测：LINE_ERROR Service session产生事件。
  - 数据观测：Break release后UART_CAPTURE.DATA正确。
  pass_criteria:
  - 错误判据：BREAK flag=1。
  - 中断判据：LINE_ERROR event_count_delta>0且fault增量=0。
  - Break后数据恢复：恢复Payload完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；覆盖DUT的break发送和检测，不把Peer计为第二被测实例。
  bench: 逻辑DUT↔Peer pair；覆盖DUT的break发送和检测，不把Peer计为第二被测实例。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: error_flags
  label: UART_STATUS.ERROR_FLAGS
  source: dut
  role: actual
  format: hex32
- key: event_count_delta
  label: LINE_ERROR事件增量
  source: measurement
  role: actual
  format: count
- key: fault_count_delta
  label: IRQ fault增量
  source: measurement
  role: actual
  format: count
- key: recovery_actual_data
  label: Break退出后UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_011
case_name: UART 中断源的 mask 使能、关闭和 Service session 状态测试
report_feature: |-
  1. UART RX_DATA_AVAILABLE IRQ中断
  2. UART TX_EMPTY IRQ中断
  3. UART CHARACTER_TIMEOUT IRQ中断
  4. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_019
- UART_F_020
- UART_F_021
- UART_F_028
method:
  inputs:
  - 执行对象：RX_READY/TX_READY/CHARACTER_TIMEOUT三个UART IRQ source；12 Byte内部loopback。
  steps:
  - 三类请求中断配置：初始化DUT并逐项使能三个请求source。
  - 请求中断基线：读取激励前IRQ session基线。
  - 请求中断数据激励：开启loopback并启动12 Byte Capture后发送Payload。
  - 有界等待：等待数据完成并读取启用阶段UART_ISR.ENABLED/PENDING/ACTIVE mask与event/fault计数。
  - 有界等待：逐项关闭三个source并读取关闭后的UART_ISR.ENABLED_MASK。
  - 请求中断开关取证：在Assert前记录enable/disable mask、实际Capture和事件计数。
  - 结果判定：核对source enable/disable与数据/事件后清理；不把Service重配置清空证据冒充通用硬件pending W1C。
  observations:
  - 中断观测：UART_ISR.ENABLED_MASK启用阶段包含全部请求source，关闭阶段不再包含。
  - 中断观测：激励阶段产生有效IRQ session事件且UART_CAPTURE.DATA正确。
  pass_criteria:
  - 数据判据：启用mask包含RX_READY/TX_READY/CHARACTER_TIMEOUT。
  - 中断源关闭状态：关闭后enabled mask中三个source均为0。
  - 中断判据：event_count_delta>0且fault增量=0。
  - 覆盖判据：不宣称本Case独立证明每个硬件source的W1C pending clear。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 完全自主，仅使用DUT内部loopback；不宣称验证NVIC优先级。
  bench: 完全自主，仅使用DUT内部loopback；不宣称验证NVIC优先级。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: enabled_mask
  label: 启用阶段UART_ISR.ENABLED_MASK
  source: measurement
  role: actual
  format: hex32
- key: disabled_mask
  label: 关闭阶段UART_ISR.ENABLED_MASK
  source: measurement
  role: actual
  format: hex32
- key: event_count_delta
  label: 组合IRQ事件增量
  source: measurement
  role: actual
  format: count
- key: actual_capture_data
  label: UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_012
case_name: UART busy detect 中断、清除条件和恢复路径测试
report_feature: |-
  1. UART BUSY_DETECT中断
  2. UART IRQ Enable/Identify/Clear
p_level: P1
feature_refs:
- UART_F_027
- UART_F_028
method:
  inputs:
  - 测试数据：DUT；隔离UART Busy Detect Test Driver Extension；4 Byte恢复loopback Payload。
  steps:
  - 功能配置：初始化DUT并确认当前运行时允许形成Busy Detect验证条件。
  - 资源准备：调用稳定busy_detect_trigger接口，由隔离Test Driver完成目标侧trigger/observe/clear/recovery序列。
  - Busy状态证据采集：取得PRE_TRIGGER_USR、OBSERVED_IIR、OBSERVED_USR、trigger_count及派生恢复字段。
  - 证据采集：在Assert前把三个raw硬件字段分别记录为UART_BUSY.* Observation，Bool结论只记Measurement。
  - Busy状态链判定：核对busy/interrupt/cleared/recovered语义与trigger_count=1。
  - 状态恢复：重新初始化DUT，执行4 Byte内部loopback恢复并记录实际Capture。
  - Busy条件合法跳过：若目标侧无法在有界窗口形成Busy条件则按真实runtime条件SKIP，不伪造PASS。
  observations:
  - 调制解调观测：UART_BUSY.PRE_TRIGGER_USR/OBSERVED_IIR/OBSERVED_USR是目标侧raw验证事实。
  - 数据观测：恢复UART_CAPTURE.DATA证明Test Driver序列后普通数据路径仍可用。
  pass_criteria:
  - 计数判据：trigger_count=1。
  - Busy与中断一致性：raw USR/IIR事实支持busy与interrupt语义。
  - Busy清除状态：clear/recovery派生判断为真。
  - 错误后数据恢复：恢复数据完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全自主；若当前CPR/Driver不支持安全构造则`skip_by_capability`或`not_implemented`，不直接写寄存器。
  bench: 完全自主；若当前CPR/Driver不支持安全构造则`skip_by_capability`或`not_implemented`，不直接写寄存器。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: pre_trigger_usr
  label: UART_BUSY.PRE_TRIGGER_USR
  source: dut
  role: actual
  format: hex32
- key: observed_iir
  label: UART_BUSY.OBSERVED_IIR
  source: dut
  role: actual
  format: hex32
- key: observed_usr
  label: UART_BUSY.OBSERVED_USR
  source: dut
  role: actual
  format: hex32
- key: trigger_count
  label: Busy Detect触发次数
  source: measurement
  role: actual
  format: count
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P1_013
case_name: UART 发送 halt、resume 和数据路径恢复测试
report_feature: |-
  1. UART TX Halt/Resume控制
p_level: P1
feature_refs:
- UART_F_037
method:
  inputs:
  - 测试数据：DUT内部loopback；TX Halt；可装入FIFO的短Payload；有界暂停观察窗口。
  steps:
  - 功能配置：初始化DUT、开启loopback并先启动等长Capture。
  - 资源准备：assert TX Halt，并使用write_partial把同一Payload装入TX FIFO。
  - Halt在途FIFO确认：读取Halt状态下UART_FIFO.TX_LEVEL，确认存在待发送数据。
  - 测试激励：连续执行4次独立Capture读取；每次请求受Driver timeout约束，证明Halt期间接收进度保持0。
  - 有界等待：解除Halt，不重新写Payload，等待原Capture完成。
  - Halt与Resume证据汇总：在Assert前记录暂停窗口received/TX level以及Resume后的UART_CAPTURE.DATA。
  - 结果判定：核对`Halt不前进 + Resume同一数据完成`后恢复UART状态并清理。
  observations:
  - 状态观测：Halt窗口UART_FIFO.TX_LEVEL显示存在待发送数据，同时UART_CAPTURE.RECEIVED保持0。
  - 数据观测：解除Halt后同一UART_CAPTURE.DATA等于原Payload。
  pass_criteria:
  - 状态判据：Halt窗口存在非零待发送FIFO数据。
  - 数据判据：4次独立Capture采样均显示received=0。
  - 状态判据：解除Halt后无需重新提交Payload即可完成。
  - 数据判据：Resume后数据逐字节一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 内部loopback。
  bench: 内部loopback。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: halted_tx_fifo_level
  label: Halt窗口UART_FIFO.TX_LEVEL
  source: dut
  role: actual
  format: decimal
- key: paused_received
  label: Halt窗口UART_CAPTURE.RECEIVED
  source: measurement
  role: actual
  format: decimal
- key: resumed_actual_data
  label: Resume后UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
- key: resume_data_match
  label: Resume后数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_001
case_name: UART TX DMA 从内存到 UART TX 端点的单次传输测试
report_feature: |-
  1. UART DMA Single Request模式
  2. UART DMA Multi Request模式
p_level: P2
feature_refs:
- UART_F_035
- UART_F_036
method:
  inputs:
  - 执行对象：UART DUT/Peer；32 Byte Resource Source；目标芯片Execution Mapping提供TX request route；一个空闲DMA Channel。
  steps:
  - 资源准备：准备Source Buffer/Payload并选择空闲DMA Channel。
  - UART DMA请求配置：初始化DUT/Peer并使能UART DMA request。
  - UART TX DMA通道映射：按Execution Mapping配置SYSCTRL UART TX request route和DMA M2P Channel。
  - UART TX DMA完成中断配置：使能DMA TRANSFER_DONE并先启动Peer Capture。
  - 测试激励：启动DMA，等待DMA IRQ、Peer Capture和Channel terminal state。
  - 证据采集：在Assert前分别记录PEER_UART.RX_CAPTURE、DMA IRQ事件和DMA_CHANNEL_STATUS.FREE。
  - 结果判定：核对数据/IRQ/Channel后按Peer→DMA IRQ→Channel→Route→UART→Controller→Resource逆序cleanup。
  observations:
  - 数据观测：PEER_UART.RX_CAPTURE必须等于Resource Source Payload。
  - 中断观测：DMA_CHANNEL_STATUS.IRQ_EVENTS包含TRANSFER_DONE且FREE=1。
  pass_criteria:
  - 数据判据：Peer实际数据与32 Byte Source一致。
  - 计数判据：TRANSFER_DONE被锁存且irq_count>=1。
  - 状态判据：unexpected/overflow=0且DMA Channel最终FREE。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair + DMA；UART Service不调用DMA Wrap，Peer只作为接收观察端。
  bench: 逻辑DUT↔Peer pair + DMA；UART Service不调用DMA Wrap，Peer只作为接收观察端。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_rx_data
  label: PEER_UART.RX_CAPTURE
  source: peer
  role: actual
  format: bytes_hex
- key: dma_irq_events
  label: DMA_CHANNEL_STATUS.IRQ_EVENTS
  source: dut
  role: actual
  format: hex32
- key: dma_channel_free
  label: DMA_CHANNEL_STATUS.FREE
  source: dut
  role: actual
  format: bool
- key: data_match
  label: UART TX DMA数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_002
case_name: UART RX DMA 从 UART RX 端点到带 Guard 的内存 Buffer 单次传输测试
report_feature: |-
  1. UART DMA Single Request模式
  2. UART DMA Multi Request模式
p_level: P2
feature_refs:
- UART_F_035
- UART_F_036
method:
  inputs:
  - 测试数据：UART DUT/Peer；32 Byte Peer Payload；带8 Byte前后Guard的Resource Destination；RX request route。
  steps:
  - DMA RX资源与Guard准备：重置Resource并创建带前后Guard的Destination，选择空闲DMA Channel。
  - UART DMA请求配置：初始化DUT/Peer并使能UART DMA request。
  - UART RX DMA通道映射：配置SYSCTRL UART RX route和DMA P2M Channel。
  - UART RX DMA启动顺序：使能TRANSFER_DONE并先启动DMA RX，再由Peer发送Payload。
  - 有界等待：等待DMA IRQ/Free后读取完整Destination和Guard。
  - 证据采集：在Assert前记录DMA_DESTINATION_DATA、DMA IRQ/Free以及Guard比较Measurement。
  - 结果判定：判断数据/Guard/IRQ后按所有权逆序cleanup。
  observations:
  - DMA观测：DMA_DESTINATION_DATA有效区应等于Peer Payload。
  - DMA观测：DMA TRANSFER_DONE与FREE必须成立；Guard作为独立Measurement保持不变。
  pass_criteria:
  - 数据判据：Peer完整发送32 Byte。
  - 数据判据：Destination有效区数据一致。
  - DMA RX边界保护：前后Guard均完整。
  - 状态判据：TRANSFER_DONE有效、unexpected/overflow=0且Channel FREE。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair + DMA；覆盖归属于DUT RX DMA。
  bench: 逻辑DUT↔Peer pair + DMA；覆盖归属于DUT RX DMA。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: dma_destination_data
  label: DMA_DESTINATION_DATA
  source: dut
  role: actual
  format: bytes_hex
- key: dma_irq_events
  label: DMA_CHANNEL_STATUS.IRQ_EVENTS
  source: dut
  role: actual
  format: hex32
- key: dma_channel_free
  label: DMA_CHANNEL_STATUS.FREE
  source: dut
  role: actual
  format: bool
- key: guards_intact
  label: Destination Guard完整
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_003
case_name: UART TX/RX 两个 DMA Channel 通过一次原子 Channel Mask 启动完成双向传输测试
report_feature: |-
  1. UART Full-Duplex TX/RX收发
  2. UART DMA Single Request模式
  3. UART DMA Multi Request模式
p_level: P2
feature_refs:
- UART_F_010
- UART_F_035
- UART_F_036
method:
  inputs:
  - 执行对象：UART DUT/Peer；TX/RX两个不同DMA Channel；两个方向各128 Byte；一次Channel Mask原子启动。
  steps:
  - 双向DMA资源准备：创建带Guard的TX/RX Resource并选择两个不同空闲DMA Channel。
  - UART双向DMA路由配置：初始化DUT/Peer，使能UART DMA并配置TX/RX两条SYSCTRL route。
  - UART双向DMA通道配置：配置DMA TX M2P与RX P2M两个Channel及TRANSFER_DONE IRQ。
  - 测试激励：先启动Peer Capture，一次CHANNELS_START提交包含两个Channel的mask，再由Peer发送反向Payload。
  - 有界等待：等待两个Channel FREE、DMA IRQ和Peer Capture，读取RX/TX Resource。
  - 证据采集：在Assert前记录两个方向实际数据、两个Channel terminal state和Guard Measurement。
  - 结果判定：判断双向数据/Guard/IRQ并逆序cleanup；不宣称精确重叠时长。
  observations:
  - DMA观测：PEER_UART.RX_CAPTURE与DMA_DESTINATION_DATA分别证明两个方向。
  - 错误观测：两个DMA_CHANNEL_STATUS.FREE均为1且无ERROR。
  pass_criteria:
  - DMA判据：一次mask包含且仅包含两个选定Channel。
  - 数据判据：两个方向128 Byte数据均一致。
  - 双向DMA边界保护：四个Guard完整。
  - 中断判据：两个Channel FREE且IRQ无unexpected/overflow。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair + DMA；Peer仅提供普通收发，不混入第二套DMA、优先级或错误注入。
  bench: 逻辑DUT↔Peer pair + DMA；Peer仅提供普通收发，不混入第二套DMA、优先级或错误注入。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_rx_data
  label: Peer收到UART TX DMA数据
  source: peer
  role: actual
  format: bytes_hex
- key: dma_destination_data
  label: UART RX DMA目标数据
  source: dut
  role: actual
  format: bytes_hex
- key: all_channels_free
  label: 两个DMA Channel最终FREE
  source: measurement
  role: actual
  format: bool
- key: all_data_match
  label: 双向DMA数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_004
case_name: UART 9-bit 软件数据双向收发及普通模式恢复测试
report_feature: |-
  1. UART 9-bit TX发送
  2. UART 9-bit RX接收
p_level: P2
feature_refs:
- UART_F_029
- UART_F_030
method:
  inputs:
  - 测试数据：DUT/Peer均具备NINE_BIT；两组包含第9位0/1的确定性word序列；普通8-bit恢复Payload。
  steps:
  - 9-bit能力门禁：在修改状态前Gate DUT/Peer NINE_BIT Runtime Feature。
  - 功能配置：初始化两端并开启软件9-bit模式。
  - 9-bit首轮发送取证：DUT发送第一组9-bit words，Peer读回并在Assert前记录PEER UART_9BIT.DATA。
  - 测试激励：Peer发送第二组9-bit words，DUT读回并记录UART_9BIT.DATA。
  - 有界等待：关闭两端9-bit并重新初始化DUT普通8-bit模式。
  - 证据采集：执行最小内部loopback恢复并记录UART_CAPTURE.DATA。
  - 结果判定：核对两组9-bit元素及普通恢复数据后cleanup。
  observations:
  - 数据观测：Peer/DUT UART_9BIT.DATA必须逐元素保留第9位。
  - 数据观测：关闭9-bit后UART_CAPTURE.DATA必须正确。
  pass_criteria:
  - 计数判据：两个方向9-bit元素数量完整。
  - 覆盖判据：两个方向每个9-bit值逐项相同。
  - 9-bit退出恢复：普通8-bit恢复数据完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；只把DUT TX/RX结果计入Feature覆盖。
  bench: 逻辑DUT↔Peer pair；只把DUT TX/RX结果计入Feature覆盖。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_9bit_data
  label: Peer UART_9BIT.DATA
  source: peer
  role: actual
  format: text
- key: dut_9bit_data
  label: DUT UART_9BIT.DATA
  source: dut
  role: actual
  format: text
- key: recovery_actual_data
  label: 普通恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_005
case_name: UART 9-bit 硬件地址匹配和不匹配地址过滤测试
report_feature: |-
  1. UART 9-bit TX发送
  2. UART 9-bit RX接收
  3. UART 9-bit地址匹配/过滤
p_level: P2
feature_refs:
- UART_F_029
- UART_F_030
- UART_F_031
method:
  inputs:
  - 执行对象：DUT/Peer NINE_BIT；匹配地址0x12；匹配序列与不匹配序列；有界mismatch稳定观察窗口。
  steps:
  - 9-bit地址匹配配置：Gate两端NINE_BIT并初始化，DUT开启hardware address match=0x12。
  - 资源准备：Peer发送匹配地址+数据，DUT读取普通RX数据并记录匹配实际值。
  - 地址不匹配刺激：清空/确认RX终态后由Peer发送不匹配地址+后续数据。
  - 测试激励：进入覆盖完整帧到达时间的有界观察窗口，重复读取UART_FIFO.RX_LEVEL而不是固定sleep单次采样。
  - 有界等待：把完整RX level采样序列保存到Artifact，并记录peak level/采样数/窗口稳定性Measurement。
  - 证据采集：关闭9-bit并恢复普通8-bit内部loopback，记录恢复实际数据。
  - 结果判定：在Assert前保存match/mismatch/recovery证据并判断过滤语义。
  observations:
  - 数据观测：匹配序列DUT实际RX数据应等于address低8位+数据。
  - 状态观测：不匹配窗口内UART_FIFO.RX_LEVEL持续为0。
  - 数据观测：恢复UART_CAPTURE.DATA正确。
  pass_criteria:
  - 数据判据：匹配地址路径数据正确。
  - 数据判据：不匹配完整观察窗口内所有RX level采样均为0。
  - 过滤观察窗口：观察窗口有明确deadline且至少取得规定采样数。
  - 普通模式恢复：普通模式恢复数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；Peer只产生地址帧刺激。
  bench: 逻辑DUT↔Peer pair；Peer只产生地址帧刺激。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: matched_actual_data
  label: 匹配地址实际接收数据
  source: dut
  role: actual
  format: bytes_hex
- key: mismatch_peak_rx_fifo_level
  label: 不匹配窗口RX FIFO最大Level
  source: measurement
  role: actual
  format: decimal
- key: mismatch_window_stable
  label: 不匹配窗口持续为空
  source: measurement
  role: actual
  format: bool
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_006
case_name: UART RTS/CTS 自动流控的暂停和恢复测试
report_feature: |-
  1. UART RTS/CTS自动流控
p_level: P2
feature_refs:
- UART_F_032
method:
  inputs:
  - 能力约束：DUT FLOW_CONTROL能力；内部modem loopback；9600 baud；128 Byte Payload；3s有界pause/resume deadline。
  steps:
  - 自动流控环境配置：Gate FLOW_CONTROL并初始化DUT/FIFO，开启内部loopback与自动流控。
  - 测试激励：启动128 Byte Capture后撤销RTS，使内部CTS进入not-ready。
  - 流控暂停窗口观测：在有界pause窗口反复capture_get/write_partial，累计accepted与received直到出现accepted=0。
  - 证据采集：记录暂停阶段accepted序列和Capture received事实。
  - 状态恢复：重新assert RTS，在有界resume窗口继续提交同一pending数据直到全部接受。
  - 有界等待：等待完整Capture并在Assert前记录UART_CAPTURE.DATA与resume计数。
  - 结果判定：判断暂停、恢复和数据一致后关闭流控/loopback并清理。
  observations:
  - 数据观测：暂停阶段必须出现write_partial=0且Capture进度受控。
  - 调制解调观测：恢复RTS后同一pending数据完成，UART_CAPTURE.DATA等于128 Byte Expected。
  pass_criteria:
  - 流控暂停证据：pause窗口至少出现一次0-byte acceptance。
  - 数据判据：resume窗口内全部pending数据被接受。
  - 数据判据：最终128 Byte Capture完整且数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 完全自主，依赖UART内部loopback和`FLOW_CONTROL` capability，不需要额外RTS/CTS接线。
  bench: 完全自主，依赖UART内部loopback和`FLOW_CONTROL` capability，不需要额外RTS/CTS接线。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: pause_zero_seen
  label: 暂停窗口出现0-byte acceptance
  source: measurement
  role: actual
  format: bool
- key: paused_received
  label: 暂停阶段UART_CAPTURE.RECEIVED
  source: measurement
  role: actual
  format: decimal
- key: resumed_bytes
  label: 恢复阶段接受字节数
  source: measurement
  role: actual
  format: count
- key: resumed_actual_data
  label: 恢复后UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_007
case_name: UART Modem 内部回环的 RTS/CTS、DTR/DSR 当前状态和 Delta 状态测试
report_feature: |-
  1. UART RTS/DTR手动控制
  2. UART Modem Status/Delta
p_level: P2
feature_refs:
- UART_F_033
- UART_F_034
method:
  inputs:
  - 能力约束：DUT MODEM能力；内部modem loopback；RTS/DTR低→单独升高→同时拉低序列。
  steps:
  - Modem回环能力门禁：Gate MODEM并初始化DUT，开启内部modem loopback。
  - 资源准备：把RTS/DTR置低并连续读取两次Modem状态，确认CTS/DSR Delta清零基线。
  - RTS到CTS状态采集：只拉高RTS，读取一次状态和一次clear后状态，记录CTS input/output/delta/raw。
  - 测试激励：保持RTS高再拉高DTR，读取一次状态和一次clear后状态，记录DSR事实。
  - 有界等待：同时拉低RTS/DTR，读取falling状态并再次读取clear状态。
  - 证据采集：在Assert前把各阶段UART_MODEM.RAW_STATUS及input/delta/output原始字段分别记录。
  - 结果判定：核对CTS/DSR current/delta/read-to-clear后cleanup；RI/DCD保持显式未覆盖。
  observations:
  - 调制解调观测：RTS→CTS、DTR→DSR当前输入/输出与Delta必须一致。
  - Modem Delta清除：第二次读取对应Delta应清零。
  - 调制解调观测：RI/DCD没有刺激，不能由本Case宣称通过。
  pass_criteria:
  - Modem初始状态：初始二次读取无CTS/DSR残留Delta。
  - RTS到CTS映射：RTS上升形成CTS current+delta，二次读取清零。
  - DTR到DSR映射：DTR上升形成DSR current+delta，二次读取清零。
  - Modem下降沿清除：同时下降形成CTS/DSR Delta后再次清零。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全自主，依赖`MODEM` capability；RI/DCD不在本Case内判定，分别在第7.3节列为`SKIP/blocked_by_board`子Feature。
  bench: 完全自主，依赖`MODEM` capability；RI/DCD不在本Case内判定，分别在第7.3节列为`SKIP/blocked_by_board`子Feature。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: rts_raw_status
  label: RTS阶段UART_MODEM.RAW_STATUS
  source: dut
  role: actual
  format: hex32
- key: dtr_raw_status
  label: DTR阶段UART_MODEM.RAW_STATUS
  source: dut
  role: actual
  format: hex32
- key: falling_raw_status
  label: 下降沿UART_MODEM.RAW_STATUS
  source: dut
  role: actual
  format: hex32
- key: covered_inputs
  label: 已覆盖Modem输入
  source: measurement
  role: actual
  format: text
gap:
- ri_dcd_stimulus_gap
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_008
case_name: UART 软件复位后的实例身份和数据路径恢复测试
report_feature: |-
  1. UART软件复位
p_level: P2
feature_refs:
- UART_F_005
method:
  inputs:
  - 能力约束：DUT SOFTWARE_RESET能力；DUT/Peer默认配置；8 Byte恢复Payload。
  steps:
  - 软件复位能力门禁：Gate SOFTWARE_RESET并初始化DUT/Peer。
  - 软件复位前身份快照：读取reset前DUT组件Snapshot。
  - 状态恢复：执行software reset并显式重新初始化DUT。
  - 软件复位后身份快照：读取reset后组件Snapshot，在Assert前记录before/after身份字段。
  - 功能配置：开启DUT内部loopback并启动8 Byte Capture。
  - 测试激励：发送恢复Payload并记录UART_CAPTURE.DATA。
  - 结果判定：判断身份稳定与恢复数据后清理DUT/Peer。
  observations:
  - 身份观测：reset前后UART_COMPONENT.COMPONENT_PARAMETER/VERSION/PERIPHERAL_ID稳定。
  - 数据观测：恢复UART_CAPTURE.DATA正确。
  pass_criteria:
  - 软件复位能力存在性：SOFTWARE_RESET runtime feature存在。
  - 数据判据：三个组件身份字段保持一致。
  - 软件复位后数据恢复：8 Byte恢复数据完整一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全自主；当前Case不宣称验证CRG时钟门控读回或相邻实例隔离。
  bench: 完全自主；当前Case不宣称验证CRG时钟门控读回或相邻实例隔离。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: component_parameter_before
  label: reset前COMPONENT_PARAMETER
  source: dut
  role: actual
  format: hex32
- key: component_parameter_after
  label: reset后COMPONENT_PARAMETER
  source: dut
  role: actual
  format: hex32
- key: identity_stable
  label: reset前后组件身份稳定
  source: measurement
  role: actual
  format: bool
- key: recovery_actual_data
  label: 恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P3_010
case_name: UART 双向混合收发 20 轮稳定性能力测试
report_feature: |-
  1. UART Full-Duplex TX/RX收发
  2. UART Blocking/Non-blocking TX发送
  3. UART RX_DATA_AVAILABLE IRQ中断
  4. UART Long-Run TX/RX传输
p_level: P3
feature_refs:
- UART_F_010
- UART_F_017
- UART_F_019
- UART_F_047
method:
  inputs:
  - 测试数据：DUT/Peer；固定seed；20轮；长度按4/32/257 Byte循环；每轮两个方向不同Payload。
  steps:
  - 功能配置：初始化DUT/Peer为相同默认帧格式并建立20轮结果容器。
  - 资源准备：每轮按4/32/257 Byte选择长度并由round index生成两个方向不同Payload。
  - 压力轮DUT到Peer传输：先启动Peer Capture并执行DUT→Peer发送。
  - 压力轮Peer到DUT传输：再启动DUT Capture并执行Peer→DUT发送。
  - 证据采集：在每轮任何决定性Assert前记录两个方向实际Capture、计数和round/length Measurement。
  - 压力轮结果归档：判断本轮双向数据后把完整round结果加入单一内存Snapshot。
  - 压力矩阵汇总：20轮全部结束后只发布一次完整Artifact并核对40次事务/总字节统计。
  observations:
  - 数据观测：每轮PEER_UART.RX_CAPTURE与UART_CAPTURE.DATA均对应各自Expected。
  - 压力轮次证据：每轮Evidence在Assert前存在，避免中途FAIL丢失前序现场。
  pass_criteria:
  - 覆盖判据：20轮全部按4/32/257 Byte循环执行。
  - 数据判据：每轮两个方向发送/接收完整且数据一致。
  - 压力事务总数：总事务数=40。
  - 覆盖判据：最终Artifact一次性包含全部已执行轮次。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；不同时混入DMA、9-bit或错误注入。
  bench: 逻辑DUT↔Peer pair；不同时混入DMA、9-bit或错误注入。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: peer_actual_data
  label: 逐轮Peer实际数据
  source: peer
  role: actual
  format: bytes_hex
- key: dut_actual_data
  label: 逐轮DUT实际数据
  source: dut
  role: actual
  format: bytes_hex
- key: round_index
  label: 当前轮次
  source: measurement
  role: config
  format: decimal
- key: all_data_match
  label: 全部已执行轮次数据一致
  source: measurement
  role: actual
  format: bool
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P2_010
case_name: UART 9-bit 地址匹配对应的 NINE_BIT_ADDRESS 中断事件路径测试
report_feature: |-
  1. UART 9-bit地址匹配/过滤
p_level: P2
feature_refs:
- UART_F_031
method:
  inputs:
  - 测试数据：DUT/Peer NINE_BIT；address=0x12；NINE_BIT_ADDRESS IRQ；匹配地址+数据；普通恢复Payload。
  steps:
  - 9-bit地址IRQ配置：Gate两端NINE_BIT并初始化，DUT配置hardware address match=0x12。
  - 功能配置：使能NINE_BIT_ADDRESS source并读取IRQ session基线。
  - 匹配地址刺激：Peer发送匹配地址和一个数据word。
  - 9-bit地址IRQ取证：读取IRQ session并在Assert前记录PENDING/ACTIVE mask、event/fault增量。
  - 有界等待：DUT读取匹配后的普通RX数据并记录实际值。
  - 9-bit地址IRQ清理：关闭NINE_BIT_ADDRESS并读取Service清理后的session状态，再关闭9-bit。
  - 结果判定：执行普通loopback恢复并记录实际Capture，判断IRQ/data/recovery后cleanup。
  observations:
  - 中断观测：UART_ISR.PENDING/ACTIVE识别NINE_BIT_ADDRESS且event_count增加。
  - 数据观测：匹配RX数据正确；关闭source后Service session不再保留该source。
  - 数据观测：普通恢复UART_CAPTURE.DATA正确。
  pass_criteria:
  - 中断判据：event_count_delta>0且fault增量=0。
  - 9-bit地址中断来源：NINE_BIT_ADDRESS来源被识别。
  - 数据判据：匹配数据正确且关闭后Service pending/active无该source。
  - 9-bit IRQ退出恢复：普通恢复数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 逻辑DUT↔Peer pair；本Case不复用P2-005的历史PASS作为地址IRQ证据。
  bench: 逻辑DUT↔Peer pair；本Case不复用P2-005的历史PASS作为地址IRQ证据。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: irq_pending_mask
  label: UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: received_data
  label: 地址匹配实际RX数据
  source: dut
  role: actual
  format: bytes_hex
- key: cleared_pending_mask
  label: 关闭后UART_ISR.PENDING_MASK
  source: measurement
  role: actual
  format: hex32
- key: recovery_actual_data
  label: 普通恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_001
case_name: DUT在每种模式只做一组短双向数字帧测试
report_feature: |-
  1. UART RS485 Transfer模式
p_level: P3
feature_refs:
- UART_F_040
method:
  inputs:
  - 测试数据：DUT、可信RS485 Peer/收发器、full/half-SW/half-HW模式、短双向Payload。
  steps:
  - 能力确认：确认RS485收发器、方向控制和Peer连接证据已声明。
  - 功能配置：初始化DUT/Peer并配置第一种RS485模式。
  - RS485 DUT到Peer传输：执行DUT→Peer短帧并记录Peer数据与方向状态。
  - RS485 Peer到DUT传输：执行Peer→DUT短帧并记录DUT数据与方向状态。
  - 证据采集：依次覆盖full/half-SW/half-HW并每模式独立cleanup。
  - 状态恢复：退出RS485后恢复普通UART并执行最小数据恢复。
  observations:
  - 状态观测：每模式双向实际数据、方向状态和普通模式恢复事实。
  pass_criteria:
  - RS485模式覆盖：三种模式按设计支持矩阵执行。
  - 数据判据：每模式数据正确且方向无冲突。
  - RS485退出恢复：退出RS485后普通UART恢复。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要RS485收发器/数字模型；当前普通UART短接不足以证明。
  bench: 需要RS485收发器/数字模型；当前普通UART短接不足以证明。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: rs485_mode
  label: RS485模式
  source: measurement
  role: config
  format: text
- key: actual_state
  label: RS485数据/方向实际状态
  source: observer
  role: actual
  format: text
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_002
case_name: DUT逐极性控制DE/RE测试
report_feature: |-
  1. UART RS485 DE/RE控制与极性
p_level: P3
feature_refs:
- UART_F_041
method:
  inputs:
  - 执行对象：DUT、可信RS485方向Observer、DE/RE manual与active-high/low组合。
  steps:
  - 能力确认：确认DE/RE物理/数字观察路径与极性定义。
  - 功能配置：初始化DUT并进入受控RS485方向模式。
  - DE/RE极性配置：逐组合配置DE/RE控制与极性。
  - 测试激励：在每组合主动切换发送/接收方向。
  - 证据采集：由独立Observer记录DE/RE实际电平和转换。
  - 状态恢复：退出方向模式并恢复普通UART。
  observations:
  - 状态观测：请求方向/极性、Observer实际DE/RE电平与恢复状态。
  pass_criteria:
  - DE/RE电平正确性：各组合实际电平符合设计极性。
  - 方向切换互斥性：方向转换无非法同时驱动。
  - 模式退出恢复：普通UART恢复。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要可观察DE/RE路径。
  bench: 需要可观察DE/RE路径。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: expected_direction
  label: 期望DE/RE方向
  source: oracle
  role: expected
  format: text
- key: actual_direction
  label: Observer实际DE/RE方向
  source: observer
  role: actual
  format: text
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_003
case_name: DUT发送短帧测试
report_feature: |-
  1. UART RS485 DET/TAT时序
p_level: P3
feature_refs:
- UART_F_042
method:
  inputs:
  - 测试数据：DUT、独立数字时序Observer、代表DET/TAT tick配置、短发送帧。
  steps:
  - 能力确认：确认独立Observer tick/精度和RS485时序路径。
  - 功能配置：初始化DUT并配置代表DET/TAT值。
  - DE时序帧发送与采集：发送确定性短帧并同步采集TX/DE/RE。
  - DE相对TX边界测量：测量DE assertion/deassertion相对TX边界。
  - 证据采集：测量DE↔RE turnaround间隔并换算tick。
  - 结果判定：与设计容差比较后恢复普通模式。
  observations:
  - 配置观测：配置tick、实际测量tick、Observer精度与容差来源。
  pass_criteria:
  - 观测判据：DET/TAT测量值在设计+Observer误差内。
  - 覆盖判据：所有时序边界来自独立Observer。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R4
  full_coverage_level: R4
  board: 需要XC7Z045/逻辑分析仪或等价独立数字观察器。
  bench: 需要XC7Z045/逻辑分析仪或等价独立数字观察器。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: expected_ticks
  label: 期望DET/TAT tick
  source: oracle
  role: expected
  format: text
- key: measured_ticks
  label: Observer测得tick
  source: observer
  role: actual
  format: decimal
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_004
case_name: DUT通过SIR收发器或可信数字模型与Peer通信测试
report_feature: |-
  1. UART IrDA SIR模式
p_level: P3
feature_refs:
- UART_F_038
method:
  inputs:
  - 测试数据：DUT、可信SIR收发器或数字模型、支持波特率、短双向Payload。
  steps:
  - 能力确认：确认SIR物理/数字Peer路径和支持速率。
  - 功能配置：初始化普通UART并建立恢复基线。
  - SIR模式进入：进入normal SIR encode/decode模式。
  - 测试激励：执行DUT→Peer SIR数据并记录Peer实际数据。
  - 证据采集：执行Peer→DUT SIR数据并记录DUT实际数据。
  - 状态恢复：退出SIR、恢复normal UART并执行最小恢复帧。
  observations:
  - 错误观测：SIR模式/速率、双向实际数据、错误状态和normal恢复数据。
  pass_criteria:
  - 数据判据：SIR双向数据完整一致。
  - 错误判据：无意外错误状态。
  - SIR退出恢复：退出SIR后normal UART恢复。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要SIR物理/数字配测路径。
  bench: 需要SIR物理/数字配测路径。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: sir_expected_data
  label: SIR Expected
  source: oracle
  role: expected
  format: bytes_hex
- key: sir_actual_data
  label: SIR实际数据
  source: peer
  role: actual
  format: bytes_hex
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_005
case_name: 配置DUT低功耗SIR测试
report_feature: |-
  1. UART Low-Power SIR模式
p_level: P3
feature_refs:
- UART_F_039
method:
  inputs:
  - 执行对象：DUT、支持low-power SIR的Peer/模型、115200合法路径与一个非法速率。
  steps:
  - 能力确认：确认low-power SIR配测路径和固定/允许速率契约。
  - 功能配置：初始化DUT并进入low-power SIR 115200模式。
  - SIR DUT到Peer传输：执行DUT→Peer短帧并记录实际数据。
  - SIR Peer到DUT传输：执行Peer→DUT短帧并记录实际数据。
  - 证据采集：提交设计明确不支持的速率并验证稳定拒绝语义。
  - 状态恢复：退出low-power SIR并恢复normal UART数据路径。
  observations:
  - 数据观测：low-power分频/模式事实、双向数据、非法速率拒绝与normal恢复。
  pass_criteria:
  - SIR合法速率数据：115200合法路径双向正确。
  - SIR非法速率拒绝：非法速率按稳定契约拒绝。
  - SIR低功耗退出恢复：normal UART恢复。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要支持low-power SIR的配测路径。
  bench: 需要支持low-power SIR的配测路径。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: requested_baudrate
  label: 请求low-power SIR速率
  source: measurement
  role: config
  format: decimal
- key: actual_data
  label: 实际SIR数据
  source: peer
  role: actual
  format: bytes_hex
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_006
case_name: 独立观察DUT TX位宽、帧宽和长期平均波特率测试
report_feature: |-
  1. UART Baud Rate配置
  2. UART Baud Rate/Bit Timing测量
p_level: P3
feature_refs:
- UART_F_006
- UART_F_048
method:
  inputs:
  - 执行对象：DUT、独立时钟域Observer、代表波特率、0x55 pattern。
  steps:
  - 能力确认：确认Observer独立时钟域、tick/ppm精度和采样配置。
  - 功能配置：初始化DUT为第一代表波特率并发送连续0x55。
  - UART外部时序测量：Observer测量单bit time和完整frame width。
  - 测试激励：在更长窗口测量平均baudrate并计算ppm误差。
  - 证据采集：对多个代表波特率重复测量并保存原始时间戳/统计。
  - 结果判定：按芯片规格容差+Observer精度判断，最后恢复UART。
  observations:
  - 时序观测：请求波特率、实际bit time/frame width/平均baudrate、ppm和Observer精度。
  pass_criteria:
  - 覆盖判据：所有代表值在芯片规格容差内。
  - 观测判据：绝对结果必须来自独立时钟域Observer。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R4
  full_coverage_level: R4
  board: 需要独立时钟域的XC7Z045、逻辑分析仪或示波器；同源DUT/Peer对测不能证明绝对精度。
  bench: 需要独立时钟域的XC7Z045、逻辑分析仪或示波器；同源DUT/Peer对测不能证明绝对精度。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: expected_baudrate
  label: 请求波特率
  source: oracle
  role: expected
  format: decimal
- key: measured_baudrate
  label: 独立Observer测量波特率
  source: observer
  role: actual
  format: float
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P3_007
case_name: UART Shadow FIFO 配置（SFE/SRT/STET）测试
report_feature: |-
  1. UART Shadow FIFO/Direct FIFO访问
p_level: P3
feature_refs:
- UART_F_044
method:
  inputs:
  - 能力约束：DUT SHADOW能力；Shadow FIFO enable；TX threshold=2、RX threshold=4；普通FIFO恢复Payload。
  steps:
  - Shadow能力门禁：Gate UartFeature.SHADOW并初始化DUT。
  - 资源准备：调用shadow_fifo_config(enable,2,4)并取得目标侧typed readback。
  - 证据采集：在Assert前分别记录UART_SHADOW.ENABLED/TX_THRESHOLD/RX_THRESHOLD。
  - Shadow FIFO关闭取证：调用shadow_fifo_config(disable,0,1)并记录关闭后的ENABLED状态。
  - 状态恢复：恢复普通FIFO配置并开启内部loopback。
  - Shadow退出恢复激励：发送最小恢复Payload、等待Capture并记录UART_CAPTURE.DATA。
  - 结果判定：判断Shadow readback/disable/recovery后清理。
  observations:
  - 数据观测：UART_SHADOW.ENABLED/TX_THRESHOLD/RX_THRESHOLD必须与请求一致。
  - 数据观测：关闭Shadow后ENABLED=False；普通恢复数据正确。
  pass_criteria:
  - Shadow能力存在性：SHADOW runtime feature存在。
  - Shadow使能读回：enable readback为True/2/4。
  - Shadow关闭读回：disable readback enabled=False。
  - Shadow退出恢复：普通FIFO恢复数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全片内，但必须先取得RTL/寄存器设计契约。
  bench: 完全片内，但必须先取得RTL/寄存器设计契约。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: shadow_enabled
  label: UART_SHADOW.ENABLED
  source: dut
  role: actual
  format: bool
- key: shadow_tx_threshold
  label: UART_SHADOW.TX_THRESHOLD
  source: dut
  role: actual
  format: decimal
- key: shadow_rx_threshold
  label: UART_SHADOW.RX_THRESHOLD
  source: dut
  role: actual
  format: decimal
- key: recovery_actual_data
  label: 普通恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: UART_P3_008
case_name: 依据安全/总线设计契约测试
report_feature: |-
  1. UART Access Protection/Timeout恢复
p_level: P3
feature_refs:
- UART_F_049
method:
  inputs:
  - 执行对象：DUT、已批准protection level、主机权限上下文、可恢复timeout/fault方案。
  steps:
  - 保护与超时契约确认：取得RTL/总线/安全设计对UART保护级别和timeout reset的正式契约。
  - 资源准备：在可恢复环境建立允许访问权限上下文并验证合法UART访问。
  - 受限权限访问刺激：切换到被拒绝权限上下文并执行设计批准的受控访问。
  - 受限访问结果取证：记录fault/拒绝结果，禁止让控制通道进入不可恢复状态。
  - 访问超时与恢复取证：按设计条件触发/观察访问timeout并执行批准的恢复。
  - 状态恢复：恢复普通权限并执行UART最小数据路径确认。
  observations:
  - 状态观测：权限上下文、访问结果、fault/timeout状态、恢复后的最小UART数据事实。
  pass_criteria:
  - 允许权限访问：允许访问成功。
  - 受限访问拒绝：拒绝访问按设计产生可恢复结果。
  - 超时后链路恢复：timeout恢复后控制链和UART均可用。
timeout: 实现时必须使用当前UART Driver/Case统一有界deadline，禁止固定sleep替代完成条件
cleanup:
- 实现时只恢复本Case实际获得或修改的UART状态
- 跨IP资源由PC Case按owner逆序释放并保留cleanup失败证据
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 需要权限模型、总线fault捕获和恢复方案；未确认前`blocked_by_design`。
  bench: 需要权限模型、总线fault捕获和恢复方案；未确认前`blocked_by_design`。
backend:
- FPGA
- Silicon
evidence:
- 实现时必须形成Canonical Measurement/Observation与必要Artifact
failure_observations:
- key: expected_access
  label: 设计期望访问结果
  source: oracle
  role: expected
  format: text
- key: actual_access
  label: 实际权限/fault结果
  source: dut
  role: actual
  format: text
gap:
- case_implementation_gap
- case_measurement_gap
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: UART_P3_009
case_name: UART Direct FIFO 访问（FAR/TFR/RFW）测试
report_feature: |-
  1. UART Shadow FIFO/Direct FIFO访问
p_level: P3
feature_refs:
- UART_F_044
method:
  inputs:
  - 能力约束：DUT FIFO_ACCESS能力；FAR；HTX；TFR读取0x5A；RFW注入0xA5；普通FIFO恢复Payload。
  steps:
  - FIFO直访能力门禁：Gate UartFeature.FIFO_ACCESS并初始化DUT/FIFO。
  - 功能配置：开启Direct FIFO access并记录UART_FIFO_ACCESS.ENABLED。
  - TX FIFO直访取证：Halt TX，向TX FIFO写入0x5A，通过TFR读取并记录UART_FIFO_ACCESS.TX_VALUE。
  - 测试激励：通过RFW向RX FIFO注入0xA5，普通read_exact读取并记录UART_FIFO_ACCESS.RX_VALUE。
  - 有界等待：解除Halt并关闭Direct FIFO access，记录关闭状态。
  - 状态恢复：恢复普通FIFO/loopback，发送恢复Payload并记录UART_CAPTURE.DATA。
  - 结果判定：判断TFR/RFW/FAR关闭与恢复数据后cleanup。
  observations:
  - 状态观测：UART_FIFO_ACCESS.ENABLED反映FAR状态。
  - 数据观测：TX_VALUE=0x5A且RX_VALUE=0xA5。
  - 数据观测：关闭FAR后普通loopback数据正确。
  pass_criteria:
  - 状态判据：FIFO_ACCESS runtime feature存在。
  - 配置判据：TFR读回0x5A。
  - 数据判据：RFW注入后普通RX读回0xA5。
  - FIFO直访退出恢复：FAR关闭且普通恢复数据一致。
timeout: 使用当前UART Driver/Case已有的有界等待与deadline契约
cleanup:
- 停止并释放本Case获得的UART运行资源、IRQ或跨IP资源（若启用）
- 恢复本Case实际修改的UART状态，不触碰未获得的资源
resources:
  minimum_level: R0
  full_coverage_level: R0
  board: 完全片内；需要具备FIFO_ACCESS的RTL/芯片版本。
  bench: 完全片内；需要具备FIFO_ACCESS的RTL/芯片版本。
backend:
- FPGA
- Silicon
evidence:
- Canonical Measurement/Observation + bound structured Artifact
failure_observations:
- key: fifo_access_enabled
  label: UART_FIFO_ACCESS.ENABLED
  source: dut
  role: actual
  format: bool
- key: tx_fifo_value
  label: UART_FIFO_ACCESS.TX_VALUE
  source: dut
  role: actual
  format: hex8
- key: rx_fifo_value
  label: UART_FIFO_ACCESS.RX_VALUE
  source: dut
  role: actual
  format: hex8
- key: recovery_actual_data
  label: 普通恢复UART_CAPTURE.DATA
  source: dut
  role: actual
  format: bytes_hex
gap: []
```
<!-- ET_CASE_SPEC_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=40; PARTIAL_ADAPTATION=1; IMPLEMENTATION_GAP=7; NEEDS_VERIFICATION=1 | ADAPTED=33; BENCH_GAP=6; NEEDS_VERIFICATION=1 | 见芯片分析 | `ET6801_uart.md` |

## 5. Common Gap / Evolution

- 7个尚未实现Case继续保持PLAN：`UART_P3_001`、`UART_P3_002`、`UART_P3_003`、`UART_P3_004`、`UART_P3_005`、`UART_P3_006`、`UART_P3_008`。
- 当前33个Formal SPEC Human Review主分类：`RECORD_ONLY=28; CASE_CHANGE=5`；只有`P0_001/P1_004/P1_005/P1_013/P2_005`允许最小行为增强。
- `UART_F_043` Scratch完整读写保留`scratch_write_proof_gap`；当前Snapshot只闭合读值。
- `UART_F_013`精确FIFO physical depth保留`fifo_depth_dynamic_proof_gap`，边界数据/level事实不能冒充独立物理深度Oracle。
- `UART_F_034`当前动态覆盖CTS/DSR；RI/DCD保留`ri_dcd_stimulus_gap`。
- `UART_F_014`独立RX/TX FIFO reset当前没有稳定公共动作/Case，不由software reset或普通FIFO config替代。
- `UART_F_045`CRG gate/reset recovery继续NEEDS_VERIFICATION；`UART_F_048`绝对baud/bit timing继续由独立Observer PLAN覆盖。
- 新芯片出现时先映射已有Feature/Case；公共Feature/Case/API变化必须与源码同一逻辑变更同步。

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  UART_P0_001:
    summary: 目标UART实例的Runtime能力范围与组件身份字段均取得目标侧原始证据；Scratch仅闭合读值。
    fields:
    - source: measurement
      path: capabilities_features
      label: 运行时能力Feature位图
      format: hex32
    - source: observation
      path: component_parameter
      label: 硬件观测（UART_COMPONENT.COMPONENT_PARAMETER）
      format: hex32
    - source: observation
      path: component_version
      label: 硬件观测（UART_COMPONENT.COMPONENT_VERSION）
      format: hex32
    - source: observation
      path: peripheral_id
      label: 硬件观测（UART_COMPONENT.PERIPHERAL_ID）
      format: hex32
  UART_P0_002:
    summary: 软件复位后经显式重新初始化，组件身份保持稳定、FIFO回到空状态且最小loopback数据路径恢复。
    fields:
    - source: measurement
      path: identity_stable
      label: 软件复位前后组件身份稳定
      format: bool
    - source: observation
      path: final_tx_fifo_level
      label: 硬件观测（UART_FIFO.TX_LEVEL）
      format: decimal
    - source: observation
      path: final_rx_fifo_level
      label: 硬件观测（UART_FIFO.RX_LEVEL）
      format: decimal
    - source: observation
      path: recovery_actual_data
      label: UART_CAPTURE.DATA恢复数据
      format: bytes_hex
  UART_P0_003:
    summary: 内部loopback在FIFO边界附近及短/长Payload下均完成完整发送、接收和逐字节数据闭环。
    fields:
    - source: artifact
      path: last_capture_data
      label: 64 Byte轮实际回环数据（UART_CAPTURE.DATA）
      format: bytes_hex
    - source: measurement
      path: tx_completed
      label: 实际发送字节数
      format: count
    - source: measurement
      path: rx_completed
      label: 实际接收字节数
      format: count
  UART_P0_004:
    summary: 逻辑DUT与可信Peer两个方向均形成独立Capture证据并完成64 Byte数据一致性闭环。
    fields:
    - source: observation
      path: peer_rx_data
      label: 硬件观测（PEER_UART.RX_CAPTURE）
      format: bytes_hex
    - source: observation
      path: dut_rx_data
      label: 硬件观测（UART_CAPTURE.DATA）
      format: bytes_hex
    - source: measurement
      path: dut_to_peer_match
      label: DUT到Peer数据一致
      format: bool
    - source: measurement
      path: peer_to_dut_match
      label: Peer到DUT数据一致
      format: bool
  UART_P1_014:
    summary: 五组代表性合法帧格式均通过DUT/Peer双向实际Capture形成端到端兼容性证据。
    fields:
    - source: measurement
      path: combination_count
      label: 已验证帧格式组合数
      format: decimal
    - source: artifact
      path: last_peer_actual_data
      label: 最后一组Peer实际接收数据
      format: bytes_hex
    - source: artifact
      path: last_dut_actual_data
      label: 最后一组DUT实际接收数据
      format: bytes_hex
    - source: measurement
      path: matrix_all_data_match
      label: 全部帧格式双向数据一致
      format: bool
  UART_P1_015:
    summary: 能力交集内代表性低/常用/高速/非整除波特率均完成双向数据闭环；绝对时序精度仍留给独立Observer PLAN。
    fields:
    - source: measurement
      path: baudrate_count
      label: 已验证波特率数量
      format: decimal
    - source: measurement
      path: last_requested_baudrate
      label: 最后验证波特率
      format: decimal
    - source: artifact
      path: last_peer_actual_data
      label: 最后一档Peer实际接收数据
      format: bytes_hex
    - source: measurement
      path: matrix_all_data_match
      label: 全部候选双向数据一致
      format: bool
  UART_P1_016:
    summary: FIFO enable与1/15/16/17/32 Byte边界数据路径、FIFO level终态均取得运行时证据；精确物理深度不被过度声明。
    fields:
    - source: measurement
      path: boundary_count
      label: 已验证FIFO边界长度数量
      format: decimal
    - source: artifact
      path: last_capture_data
      label: 最后一档FIFO边界UART_CAPTURE.DATA
      format: bytes_hex
    - source: measurement
      path: final_rx_fifo_level
      label: 最终UART_FIFO.RX_LEVEL
      format: decimal
    - source: measurement
      path: matrix_all_data_match
      label: 全部边界数据一致
      format: bool
  UART_P1_017:
    summary: 七类非法公共参数均在数据传输前被拒绝，随后合法8 Byte loopback路径仍保持完整。
    fields:
    - source: measurement
      path: rejected_count
      label: 非法请求拒绝数
      format: count
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
    - source: measurement
      path: recovery_data_match
      label: 恢复数据一致
      format: bool
  UART_P1_001:
    summary: 仅复位DUT后Peer组件身份保持稳定，且DUT内部与Peer输入两条数据路径均恢复。
    fields:
    - source: observation
      path: peer_component_parameter_before
      label: Peer reset前COMPONENT_PARAMETER
      format: hex32
    - source: observation
      path: peer_component_parameter_after
      label: Peer reset后COMPONENT_PARAMETER
      format: hex32
    - source: measurement
      path: peer_identity_unchanged
      label: Peer组件身份保持不变
      format: bool
    - source: observation
      path: peer_to_dut_actual_data
      label: DUT接收Peer数据
      format: bytes_hex
  UART_P1_002:
    summary: RX_READY路径同时取得实际接收数据、Service IRQ来源和事件增量证据，且无IRQ维护故障。
    fields:
    - source: observation
      path: rx_actual_data
      label: 硬件观测（UART_CAPTURE.DATA）
      format: bytes_hex
    - source: measurement
      path: irq_pending_mask
      label: Service中断Pending掩码
      format: hex32
    - source: measurement
      path: event_count_delta
      label: RX_READY事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
  UART_P1_003:
    summary: TX_READY在真实发送完成路径形成Service IRQ来源/事件证据，同时loopback数据保持完整一致。
    fields:
    - source: observation
      path: tx_actual_data
      label: 硬件观测（UART_CAPTURE.DATA）
      format: bytes_hex
    - source: measurement
      path: irq_pending_mask
      label: Service中断Pending掩码
      format: hex32
    - source: measurement
      path: event_count_delta
      label: TX_READY事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
  UART_P1_004:
    summary: RX FIFO四档阈值均通过threshold-1负对照与threshold正对照形成可区分的中断边界证据。
    fields:
    - source: measurement
      path: threshold_count
      label: 已验证RX FIFO阈值档数
      format: decimal
    - source: measurement
      path: all_threshold_boundaries_valid
      label: 全部threshold-1/threshold中断边界符合预期
      format: bool
    - source: artifact
      path: last_capture_data
      label: 最后一档threshold正对照UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_005:
    summary: TX FIFO阈值使用受控Halt/in-flight FIFO状态与Resume后的TX_READY事件形成因果证据，不再只看一次发送完成中断。
    fields:
    - source: measurement
      path: threshold_count
      label: 已验证TX FIFO阈值档数
      format: decimal
    - source: measurement
      path: all_resume_events_observed
      label: 全部Resume路径均观测到TX_READY事件
      format: bool
    - source: artifact
      path: last_capture_data
      label: 最后一档Resume后的UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_006:
    summary: 低于RX阈值的短帧通过有界等待形成CHARACTER_TIMEOUT来源/事件证据并保留完整接收数据。
    fields:
    - source: observation
      path: timeout_actual_data
      label: 硬件观测（UART_CAPTURE.DATA）
      format: bytes_hex
    - source: measurement
      path: irq_pending_mask
      label: Service中断Pending掩码
      format: hex32
    - source: measurement
      path: event_count_delta
      label: CHARACTER_TIMEOUT事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
  UART_P1_007:
    summary: Parity mismatch形成PARITY/LINE_ERROR证据，退出失配配置后普通无校验数据路径完整恢复。
    fields:
    - source: observation
      path: error_flags
      label: 硬件观测（UART_STATUS.ERROR_FLAGS）
      format: hex32
    - source: measurement
      path: irq_pending_mask
      label: Service中断Pending掩码
      format: hex32
    - source: measurement
      path: event_count_delta
      label: LINE_ERROR事件增量
      format: count
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_008:
    summary: 在Bench明确提供停止位失配刺激时，FRAMING/LINE_ERROR被观测并且恢复帧数据路径保持正确。
    fields:
    - source: observation
      path: error_flags
      label: 硬件观测（UART_STATUS.ERROR_FLAGS）
      format: hex32
    - source: measurement
      path: event_count_delta
      label: LINE_ERROR事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_009:
    summary: 受控RX压力形成OVERRUN/LINE_ERROR现场，software reset后普通loopback数据路径恢复。
    fields:
    - source: observation
      path: error_flags
      label: 硬件观测（UART_STATUS.ERROR_FLAGS）
      format: hex32
    - source: measurement
      path: event_count_delta
      label: LINE_ERROR事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_010:
    summary: Peer主动Break在DUT形成BREAK/LINE_ERROR现场，释放Break后正常帧数据路径恢复。
    fields:
    - source: observation
      path: error_flags
      label: 硬件观测（UART_STATUS.ERROR_FLAGS）
      format: hex32
    - source: measurement
      path: event_count_delta
      label: LINE_ERROR事件增量
      format: count
    - source: measurement
      path: fault_count_delta
      label: IRQ fault增量
      format: count
    - source: observation
      path: recovery_actual_data
      label: Break退出后UART_CAPTURE.DATA
      format: bytes_hex
  UART_P1_011:
    summary: 三个UART中断source可按稳定Service契约组合使能并独立关闭；通用硬件pending清除不由Service mask重配置冒充。
    fields:
    - source: measurement
      path: enabled_mask
      label: 启用阶段UART_ISR.ENABLED_MASK
      format: hex32
    - source: measurement
      path: disabled_mask
      label: 关闭阶段UART_ISR.ENABLED_MASK
      format: hex32
    - source: measurement
      path: event_count_delta
      label: 组合IRQ事件增量
      format: count
    - source: observation
      path: actual_capture_data
      label: 硬件观测（UART_CAPTURE.DATA）
      format: bytes_hex
  UART_P1_012:
    summary: 隔离Test Driver返回Busy Detect前后USR/IIR原始事实并完成一次clear/recovery序列，随后普通数据路径恢复。
    fields:
    - source: observation
      path: pre_trigger_usr
      label: 硬件观测（UART_BUSY.PRE_TRIGGER_USR）
      format: hex32
    - source: observation
      path: observed_iir
      label: 硬件观测（UART_BUSY.OBSERVED_IIR）
      format: hex32
    - source: observation
      path: observed_usr
      label: 硬件观测（UART_BUSY.OBSERVED_USR）
      format: hex32
    - source: measurement
      path: trigger_count
      label: Busy Detect触发次数
      format: count
  UART_P1_013:
    summary: TX Halt窗口内已有待发送数据但接收进度不前进，解除Halt后同一数据继续并完整发送。
    fields:
    - source: observation
      path: halted_tx_fifo_level
      label: Halt窗口UART_FIFO.TX_LEVEL
      format: decimal
    - source: measurement
      path: paused_received
      label: Halt窗口UART_CAPTURE.RECEIVED
      format: decimal
    - source: observation
      path: resumed_actual_data
      label: Resume后UART_CAPTURE.DATA
      format: bytes_hex
    - source: measurement
      path: resume_data_match
      label: Resume后数据一致
      format: bool
  UART_P2_001:
    summary: UART TX DMA通过真实request route把Resource数据送到Peer，并以DMA TRANSFER_DONE/Free闭合执行终态。
    fields:
    - source: observation
      path: peer_rx_data
      label: 硬件观测（PEER_UART.RX_CAPTURE）
      format: bytes_hex
    - source: observation
      path: dma_irq_events
      label: 硬件观测（DMA_CHANNEL_STATUS.IRQ_EVENTS）
      format: hex32
    - source: observation
      path: dma_channel_free
      label: 硬件观测（DMA_CHANNEL_STATUS.FREE）
      format: bool
    - source: measurement
      path: data_match
      label: UART TX DMA数据一致
      format: bool
  UART_P2_002:
    summary: UART RX DMA把Peer数据写入受Guard保护的Resource Destination，并以TRANSFER_DONE/Free形成终态证据。
    fields:
    - source: observation
      path: dma_destination_data
      label: 硬件观测（DMA_DESTINATION_DATA）
      format: bytes_hex
    - source: observation
      path: dma_irq_events
      label: 硬件观测（DMA_CHANNEL_STATUS.IRQ_EVENTS）
      format: hex32
    - source: observation
      path: dma_channel_free
      label: 硬件观测（DMA_CHANNEL_STATUS.FREE）
      format: bool
    - source: measurement
      path: guards_intact
      label: Destination Guard完整
      format: bool
  UART_P2_003:
    summary: 一次原子Channel Mask启动UART TX/RX两条DMA路径，双向数据、Guard和两个Channel终态全部闭合。
    fields:
    - source: observation
      path: peer_rx_data
      label: Peer收到UART TX DMA数据
      format: bytes_hex
    - source: observation
      path: dma_destination_data
      label: UART RX DMA目标数据
      format: bytes_hex
    - source: measurement
      path: all_channels_free
      label: 两个DMA Channel最终FREE
      format: bool
    - source: measurement
      path: all_data_match
      label: 双向DMA数据一致
      format: bool
  UART_P2_004:
    summary: 软件9-bit模式在两个方向逐元素保留第9位，退出9-bit后普通8-bit数据路径恢复。
    fields:
    - source: observation
      path: peer_9bit_data
      label: 硬件观测（Peer UART_9BIT.DATA）
      format: text
    - source: observation
      path: dut_9bit_data
      label: 硬件观测（DUT UART_9BIT.DATA）
      format: text
    - source: observation
      path: recovery_actual_data
      label: 普通恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P2_005:
    summary: 9-bit匹配地址数据被接收，不匹配地址后的数据在完整有界观察窗口内持续未进入RX FIFO，随后普通模式恢复。
    fields:
    - source: observation
      path: matched_actual_data
      label: 匹配地址实际接收数据
      format: bytes_hex
    - source: measurement
      path: mismatch_peak_rx_fifo_level
      label: 不匹配窗口RX FIFO最大Level
      format: decimal
    - source: measurement
      path: mismatch_window_stable
      label: 不匹配窗口持续为空
      format: bool
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P2_006:
    summary: 自动RTS/CTS在CTS not-ready时使发送出现明确暂停，RTS恢复后同一pending数据继续并完整到达。
    fields:
    - source: measurement
      path: pause_zero_seen
      label: 暂停窗口出现0-byte acceptance
      format: bool
    - source: measurement
      path: paused_received
      label: 暂停阶段UART_CAPTURE.RECEIVED
      format: decimal
    - source: measurement
      path: resumed_bytes
      label: 恢复阶段接受字节数
      format: count
    - source: observation
      path: resumed_actual_data
      label: 恢复后UART_CAPTURE.DATA
      format: bytes_hex
  UART_P2_007:
    summary: 内部Modem loopback闭合RTS→CTS、DTR→DSR当前值与Delta read-to-clear；RI/DCD明确保留未覆盖。
    fields:
    - source: observation
      path: rts_raw_status
      label: RTS阶段UART_MODEM.RAW_STATUS
      format: hex32
    - source: observation
      path: dtr_raw_status
      label: DTR阶段UART_MODEM.RAW_STATUS
      format: hex32
    - source: observation
      path: falling_raw_status
      label: 下降沿UART_MODEM.RAW_STATUS
      format: hex32
    - source: measurement
      path: covered_inputs
      label: 已覆盖Modem输入
      format: text
  UART_P2_008:
    summary: software reset前后组件身份保持稳定，显式重新初始化后8 Byte普通loopback路径恢复。
    fields:
    - source: observation
      path: component_parameter_before
      label: reset前COMPONENT_PARAMETER
      format: hex32
    - source: observation
      path: component_parameter_after
      label: reset后COMPONENT_PARAMETER
      format: hex32
    - source: measurement
      path: identity_stable
      label: reset前后组件身份稳定
      format: bool
    - source: observation
      path: recovery_actual_data
      label: 恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P3_010:
    summary: 20轮变长双向传输逐轮在Assert前保存真实Capture，完整执行时形成40次事务稳定性证据。
    fields:
    - source: artifact
      path: last_peer_actual_data
      label: 最后一轮Peer实际数据
      format: bytes_hex
    - source: artifact
      path: last_dut_actual_data
      label: 最后一轮DUT实际数据
      format: bytes_hex
    - source: measurement
      path: transaction_count
      label: 已完成双向事务数
      format: decimal
    - source: measurement
      path: all_rounds_data_match
      label: 全部已执行轮次数据一致
      format: bool
  UART_P2_010:
    summary: 9-bit匹配地址形成NINE_BIT_ADDRESS Service IRQ事件和正确RX数据，关闭source后session清理且普通模式恢复。
    fields:
    - source: measurement
      path: irq_pending_mask
      label: Service中断Pending掩码
      format: hex32
    - source: observation
      path: received_data
      label: 地址匹配实际RX数据
      format: bytes_hex
    - source: measurement
      path: cleared_pending_mask
      label: 关闭后UART_ISR.PENDING_MASK
      format: hex32
    - source: observation
      path: recovery_actual_data
      label: 普通恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P3_007:
    summary: Shadow FIFO enable/threshold取得typed目标侧readback，显式关闭后普通FIFO数据路径恢复。
    fields:
    - source: observation
      path: shadow_enabled
      label: 硬件观测（UART_SHADOW.ENABLED）
      format: bool
    - source: observation
      path: shadow_tx_threshold
      label: 硬件观测（UART_SHADOW.TX_THRESHOLD）
      format: decimal
    - source: observation
      path: shadow_rx_threshold
      label: 硬件观测（UART_SHADOW.RX_THRESHOLD）
      format: decimal
    - source: observation
      path: recovery_actual_data
      label: 普通恢复UART_CAPTURE.DATA
      format: bytes_hex
  UART_P3_009:
    summary: Direct FIFO FAR/TFR/RFW路径分别取得0x5A/0xA5原始结果，关闭测试访问后普通FIFO通信恢复。
    fields:
    - source: observation
      path: fifo_access_enabled
      label: 硬件观测（UART_FIFO_ACCESS.ENABLED）
      format: bool
    - source: observation
      path: tx_fifo_value
      label: 硬件观测（UART_FIFO_ACCESS.TX_VALUE）
      format: hex8
    - source: observation
      path: rx_fifo_value
      label: 硬件观测（UART_FIFO_ACCESS.RX_VALUE）
      format: hex8
    - source: observation
      path: recovery_actual_data
      label: 普通恢复UART_CAPTURE.DATA
      format: bytes_hex
```
<!-- ET_CASE_REPORT_END -->
