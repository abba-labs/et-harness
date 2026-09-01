# DMA Stable IP Contract

<!-- Contract Human Review 2026-08-19: AES/CRC discipline; exact-SHA software/CI/HIL未验证时不得写PASS。 -->

> 公共跨芯片DMA Feature/Case/Report唯一契约；芯片寄存器、IRQ、地址、SDK与历史证据只进入`<CHIP>_dma.md`。
> Formal Case 前置隔离统一遵循 `R210`：除纯只读能力查询外，第一次 Feature 配置前由 Case 显式复位参与的 DMA Controller 和 Peer IP，并最后复位 Resource Pool；本文件各 Case 不重复展开该公共前置条件。

## 0. Stable IP Contract

- Feature/Case ID绑定稳定语义，不绑定芯片、物理实例、IRQn、Base Address或SDK类型。
- Runtime Capability只决定实例/范围/选项，不代替硬件PASS。
- 数据路径以Destination/Peer实际数据 + Channel终态形成强Oracle；配置类Feature必须有配置读回或等价独立证明。
- IRQ寄存器、ISR/Service、Peer与软件Oracle分来源；决定性Evidence必须在Assert前进入Canonical Result；Artifact只发布完整Snapshot。
- 当前精确SHA无真机时，历史HIL仅作Historical Evidence。

### 0.1 Stable Canonical Endpoint

`DMA_CAPABILITIES.*`、`DMA_COMPONENT.*`、`DMA_CHANNEL_STATUS.FREE/FIFO_EMPTY/IRQ_EVENTS`、`DMA_CHANNEL.SOURCE_ADDRESS/DESTINATION_ADDRESS/LINKED_LIST_ADDRESS`、`DMA_CHANNEL_CFG.FIFO_MODE`、`DMA_CHANNEL_CTL.SOURCE_BURST/DESTINATION_BURST/BLOCK_SIZE`、`LLI_DESCRIPTOR.DONE/NEXT_ADDRESS`、`IRQ_RAW/STATUS/MASK.<Event>`、`IRQ_COMBINED.STATUS`、`ISR.LATCHED.<Event>`、`ISR.EVENT_COUNT`、`DMA_SOURCE_DATA`、`DMA_DESTINATION_DATA`、`PEER_UART.RX_CAPTURE`。

`ISR.EVENT_COUNT`、Request ID、Route、参数、Expected、拒绝层级默认是Measurement/Service/Mapping事实；只有真实硬件端点读值才是DUT/Peer Observation。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| DMA_F_001 | DMA Controller实例集合 | DMA控制器逻辑实例集合由Capability声明 | DMA_P0_001, DMA_P3_007 |
| DMA_F_002 | DMA Channel数量/集合 | 每个DMA控制器的Channel数量与集合由Capability/Runtime交集声明 | DMA_P0_001, DMA_P0_002, DMA_P1_001, DMA_P3_007 |
| DMA_F_003 | DMA Controller Enable/Disable控制 | Controller enable/disable以及重新使能后的可用性 | DMA_P0_002, DMA_P2_015 |
| DMA_F_004 | DMA Channel Configure/Start/Stop流程 | Channel configure/start/stop/deconfigure以及恢复可复用 | DMA_P0_002, DMA_P2_015 |
| DMA_F_005 | DMA Channel FREE/FIFO_EMPTY状态 | Channel free、FIFO empty与完成后可复用状态 | DMA_P0_002, DMA_P1_001, DMA_P2_015, DMA_P3_007 |
| DMA_F_006 | DMA Free Channel分配 | 运行时返回合法首个空闲Channel并在生命周期后可再次分配 | DMA_P0_002 |
| DMA_F_007 | DMA M2M/M2P/P2M/P2P传输 | M2M、M2P、P2M、P2P四类稳定数据路径 | DMA_P1_014, DMA_P1_016, DMA_P2_008, DMA_P2_009, DMA_P2_010, DMA_P2_015, DMA_P3_007 |
| DMA_F_008 | DMA 8/16/32-bit传输宽度 | 支持的8/16/32-bit传输宽度及其数据语义 | DMA_P1_014, DMA_P1_017, DMA_P3_007 |
| DMA_F_009 | DMA Source/Destination地址模式 | Source/Destination increment、decrement、fixed地址更新语义 | DMA_P1_014, DMA_P1_017 |
| DMA_F_010 | DMA Burst Item数量 | Source/Destination支持的1~256 item Burst配置与硬件读回 | DMA_P1_015, DMA_P1_017, DMA_P3_007 |
| DMA_F_011 | DMA Block Size配置 | Block Transfer Count合法边界与硬件配置 | DMA_P1_015, DMA_P1_017 |
| DMA_F_012 | DMA Channel Priority仲裁 | 竞争Channel的仲裁行为随配置Priority变化 | DMA_P1_002 |
| DMA_F_013 | DMA Single/Half-Depth FIFO模式 | Single与Half-Depth FIFO Mode配置与数据行为 | DMA_P1_010, DMA_P3_007 |
| DMA_F_014 | DMA Peripheral Request接口 | 外设DMA Request通过Capability/Resolver映射到稳定DMA接口 | DMA_P1_017, DMA_P2_008, DMA_P2_009, DMA_P2_010 |
| DMA_F_015 | DMA Suspend/Resume控制 | 传输中Suspend、FIFO drain、进度停滞与Resume恢复 | DMA_P1_003 |
| DMA_F_016 | DMA Source/Destination Reload模式 | Source/Destination/both Reload连续Block与BLOCK_DONE语义 | DMA_P1_007 |
| DMA_F_017 | DMA LLI Descriptor Chain链式传输 | 有限Descriptor Chain、单侧/双侧地址更新、链尾与错误恢复 | DMA_P2_001, DMA_P2_002, DMA_P2_003 |
| DMA_F_018 | DMA Source Gather模式 | Source Gather Count/Interval与Gather后目标布局 | DMA_P1_008, DMA_P1_017 |
| DMA_F_019 | DMA Destination Scatter模式 | Destination Scatter Count/Interval与Scatter目标布局 | DMA_P1_009, DMA_P1_017 |
| DMA_F_020 | DMA LLI DONE写回 | LLI Descriptor DONE初值与传输完成后DONE=1写回 | DMA_P1_011 |
| DMA_F_021 | DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断 | TRANSFER/BLOCK/SOURCE/DST/ERROR分类事件的交付与恢复 | DMA_P1_004, DMA_P1_005, DMA_P1_016, DMA_P2_005, DMA_P2_006, DMA_P2_007 |
| DMA_F_022 | DMA IRQ Channel位图 | 按Channel位对Mask/Status/Clear和分类事件进行操作 | DMA_P1_004, DMA_P1_005, DMA_P1_006, DMA_P1_016 |
| DMA_F_023 | DMA TCM Bus Alias转换 | 不同Core的ITCM/DTCM CPU地址到DMA Bus Alias的芯片适配语义 | DMA_P2_014 |
| DMA_F_024 | DMA Combined IRQ中断 | Combined物理IRQ路由汇总分类事件并保持分类身份 | DMA_P2_004 |
| DMA_F_025 | DMA IRQ RAW/STATUS/MASK/CLEAR | IRQ RAW、STATUS、MASK、CLEAR的状态机语义 | DMA_P1_006 |
| DMA_F_026 | DMA Software Handshake握手 | Source/Destination Software Request控制DMA Item推进 | DMA_P2_011 |
| DMA_F_027 | DMA Hardware Handshake极性 | Hardware Request active-high/active-low极性语义 | OPEN GAP |
| DMA_F_028 | DMA Hardware/Software Handshake选择 | 同一外设Endpoint可选择Hardware或Software Handshake且行为可因果区分 | DMA_P2_011, DMA_P2_012 |
| DMA_F_029 | DMA MAX_AMBA_BURST_LEN配置 | 最大AMBA Burst限制配置、边界与非法值拒绝 | DMA_P3_003 |
| DMA_F_030 | DMA Source/Destination AHB Master选择 | Source/Destination AHB Master选择与总线可达矩阵 | DMA_P3_001 |
| DMA_F_031 | DMA Protection属性 | Protection属性对允许/禁止区域的访问与恢复 | DMA_P3_002 |
| DMA_F_032 | DMA/Peripheral Flow Controller模式 | DMA-controlled与Peripheral-controlled结束条件 | DMA_P3_004 |
| DMA_F_033 | DMA Component ID/Channel能力/FIFO深度 | 组件ID、逐Channel静态能力和FIFO Depth硬件能力事实 | DMA_P0_001 |
| DMA_F_034 | DMA Low-Power Timeout低功耗超时 | Low-Power Timeout配置、进入/退出与唤醒恢复 | DMA_P3_005 |
| DMA_F_035 | DMA DFT/Test Slave模式 | 设计批准的DFT/Test Slave进入、规定响应与安全退出 | DMA_P3_006 |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| DMA_P0_001 | P0 | DMA声明实例的运行时能力、组件身份与逐Channel静态参数一致 | DMA声明实例的运行时能力、组件身份与逐Channel静态参数一致性测试 | SPEC |
| DMA_P0_002 | P0 | DMA Controller/Channel可完成空闲分配、基础生命周期并在重新使能后恢复M2M | DMA Controller/Channel基础生命周期、空闲分配与重复M2M恢复测试 | SPEC |
| DMA_P1_001 | P1 | DMA全部可用Channel可一次原子启动并独立完成各自M2M数据传输 | DMA全部可用Channel原子并发启动与独立数据一致性测试 | SPEC |
| DMA_P1_002 | P1 | 并发竞争时DMA通道仲裁表现随配置Priority变化而非固定Channel编号 | DMA通道优先级竞争与映射交换测试 | PLAN |
| DMA_P1_003 | P1 | DMA在进行中传输可Suspend至稳定停滞并在Resume后继续完整完成 | DMA传输中Suspend/FIFO Drain/Resume测试 | PLAN |
| DMA_P1_004 | P1 | DMA代表Channel完成M2M时TRANSFER_DONE被交付且数据与Channel终态一致 | DMA TRANSFER_DONE分类中断、数据完成与Channel终态一致性测试 | SPEC |
| DMA_P1_005 | P1 | DMA首/末边界Channel执行单节点LLI时BLOCK_DONE被交付且数据正确 | DMA单节点LLI的BLOCK_DONE中断与边界Channel行为测试 | SPEC |
| DMA_P1_006 | P1 | DMA TRANSFER_DONE在Mask关闭、Pending清除和重新使能过程中的RAW/STATUS/MASK语义正确 | DMA TRANSFER_DONE的RAW/STATUS/MASK/CLEAR状态机测试 | SPEC |
| DMA_P1_007 | P1 | DMA Source、Destination和双端Reload可连续执行多个Block并产生BLOCK_DONE | DMA Source/Destination/双端Reload连续Block与BLOCK_DONE测试 | SPEC |
| DMA_P1_008 | P1 | DMA Source Gather按Count/Interval跳过源间隔并连续写入目标数据 | DMA Source Gather Interval/Count与目标布局测试 | SPEC |
| DMA_P1_009 | P1 | DMA Destination Scatter按Count/Interval把连续源数据写入带间隔目标布局 | DMA Destination Scatter Interval/Count与目标布局测试 | SPEC |
| DMA_P1_010 | P1 | DMA Single与Half-Depth FIFO Mode均可正确编程并完成M2M | DMA M2M Single/Half-Depth FIFO Mode配置读回与数据测试 | SPEC |
| DMA_P1_011 | P1 | DMA LLI Descriptor DONE无论初始0/1，完成后均为1且其他字段保持不变 | DMA LLI Descriptor DONE完成状态写回测试 | SPEC |
| DMA_P1_014 | P1 | DMA 8/16/32-bit × 源/目标递增/递减/固定地址模式组合的数据布局正确 | DMA M2M传输宽度与源/目标地址模式组合测试 | SPEC |
| DMA_P1_015 | P1 | DMA Block Count边界和1~256 item Burst编码均可正确编程并完成M2M | DMA M2M Block Count边界与Source/Destination Burst配置读回测试 | SPEC |
| DMA_P1_016 | P1 | DMA在受Resource管理的SRAM Buffer之间完成M2M并交付TRANSFER_DONE | DMA受Resource管理SRAM Buffer的M2M数据完整性与TRANSFER_DONE测试 | SPEC |
| DMA_P1_017 | P1 | DMA非法Count/Width/Burst/Channel/Gather参数被预期层拒绝且随后合法M2M可恢复 | DMA非法配置拒绝边界与同Controller恢复测试 | SPEC |
| DMA_P2_001 | P2 | DMA双端LLI可按2/3/4节点有限Descriptor Chain完成分离Buffer传输 | DMA双端LLI 2/3/4块有限Descriptor Chain传输测试 | SPEC |
| DMA_P2_002 | P2 | DMA仅Source或仅Destination采用LLI时均能按Descriptor更新地址并完成三块数据 | DMA单侧Source/Destination LLI地址更新测试 | SPEC |
| DMA_P2_003 | P2 | DMA遇到批准的无效LLI节点时错误可有界捕获且清理后合法LLI可恢复 | DMA LLI无效节点错误与清理后恢复测试 | PLAN |
| DMA_P2_004 | P2 | DMA Combined IRQ物理路由可交付TRANSFER_DONE并保持分类事件与数据一致 | DMA Combined IRQ路由下TRANSFER_DONE交付与M2M数据测试 | SPEC |
| DMA_P2_005 | P2 | UART RX外设到内存DMA可同时交付SOURCE_TRANSACTION和TRANSFER_DONE且数据正确 | UART RX DMA的P2M SOURCE_TRANSACTION+TRANSFER_DONE中断测试 | SPEC |
| DMA_P2_006 | P2 | UART TX内存到外设DMA可同时交付DESTINATION_TRANSACTION和TRANSFER_DONE且Peer捕获数据正确 | UART TX DMA的M2P DESTINATION_TRANSACTION+TRANSFER_DONE中断测试 | SPEC |
| DMA_P2_007 | P2 | DMA受控总线错误可产生ERROR事件、清除并在同Controller恢复合法M2M | DMA受控Bus Error中断与恢复测试 | PLAN |
| DMA_P2_008 | P2 | DMA M2P通过UART TX硬件请求在1/17/257 Byte长度下完整输出到Peer | DMA M2P在1/17/257 Byte下的UART TX硬件握手数据路径测试 | SPEC |
| DMA_P2_009 | P2 | DMA P2M通过UART RX硬件请求在1/17/257 Byte长度下完整写入Memory | DMA P2M在1/17/257 Byte下的UART RX硬件握手数据路径测试 | SPEC |
| DMA_P2_010 | P2 | DMA P2P通过双UART Request Route在1/17/257 Byte下把Peer输入完整转发到Peer输出 | DMA P2P双UART Route在1/17/257 Byte下的数据路径测试 | SPEC |
| DMA_P2_011 | P2 | DMA Destination Software Handshake每次软件Request只推进受控Item并最终完成UART TX数据 | DMA Destination Software Handshake逐Item Request推进测试 | SPEC |
| DMA_P2_012 | P2 | UART TX Endpoint在Hardware与Software Handshake Mode下均可完成传输，Software Mode只有Request后才推进 | UART TX Endpoint的Hardware/Software DMA Handshake Mode因果对照测试 | SPEC |
| DMA_P2_013 | P2 | 同一逻辑DMA的NORMAL与ACC组件访问视图返回一致身份和组件参数 | DMA NORMAL/ACC组件访问别名一致性测试 | SPEC |
| DMA_P2_014 | P2 | DMA在不同Core与TCM/共享SRAM组合下使用正确总线别名且数据无地址混淆 | DMA多Core TCM CPU/DMA地址视图映射测试 | PLAN |
| DMA_P2_015 | P2 | DMA经过Clock Gate/Reset扰动后可重新使能并恢复正确M2M | DMA经CRG Clock Gate/Reset后的M2M恢复测试 | SPEC |
| DMA_P3_001 | P3 | DMA Source/Destination Master选择符合芯片总线可达矩阵并保持数据正确 | DMA Source/Destination AHB Master选择测试 | PLAN |
| DMA_P3_002 | P3 | DMA Protection属性对允许区域放行、对禁止区域受控拒绝且错误后可恢复 | DMA Protection/Permission允许与拒绝区域测试 | PLAN |
| DMA_P3_003 | P3 | DMA最大AMBA Burst限制配置在不同对齐/长度下生效且非法值被拒绝 | DMA最大AMBA Burst限制与边界测试 | PLAN |
| DMA_P3_004 | P3 | DMA与Peripheral两种Flow Controller模式都按控制方结束并产生正确长度和数据 | DMA/Peripheral Flow Controller结束条件测试 | PLAN |
| DMA_P3_005 | P3 | DMA Low-Power Timeout按配置进入/退出低功耗且唤醒后数据路径保持正确 | DMA Low-Power Timeout状态与唤醒恢复测试 | PLAN |
| DMA_P3_006 | P3 | DMA仅按批准DFT流程进入Test模式并在安全退出后恢复普通M2M | DMA DFT/Test Slave受控进入与退出测试 | PLAN |
| DMA_P3_007 | P3 | DMA在20轮跨实例与多参数混合M2M中持续保持数据完整与Channel可恢复 | DMA 20轮跨实例/Channel/Count/Width/Burst/FIFO混合M2M稳定性测试 | SPEC |

## 3. Machine-readable Case Contract

> Human Review冻结：20 RECORD_ONLY、5 CASE_CHANGE、2 DOC_ONLY、1 SEMANTIC/MAPPING GAP；详见`report/review/20260819_dma_contract_human_review.md`。
> Contract先冻结证明链，代码后续只按分类最小补录/增强。

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P0_001
case_name: "DMA声明实例的运行时能力、组件身份与逐Channel静态参数一致性测试"
report_feature: |-
  1. DMA Controller实例集合
  2. DMA Channel数量/集合
  3. DMA Component ID/Channel能力/FIFO深度
p_level: P0
feature_refs: [DMA_F_001, DMA_F_002, DMA_F_033]
method:
  inputs:
    - "实例与静态期望：Capability声明的全部DMA逻辑实例、逐Channel max_block_size与FIFO depth静态事实。"
    - "运行时能力期望：每个实例存在Runtime Service并返回合法Channel Count、Max Transfer、M2M Feature与IRQ集合。"
  steps:
    - "实例集合确认：取得全部逻辑实例并确认可构造公共DMA Driver。"
    - "运行时能力读取：逐实例读取DMA_CAPABILITIES。"
    - "组件身份读取：逐实例读取NORMAL DMA_COMPONENT快照。"
    - "能力合法性核对：Channel Count与组件参数数量一致且组件身份有效。"
    - "静态参数对照：逐Channel比较Capability max_block_size与Runtime MAX_TRANSFER_COUNT。"
    - "结果汇总：保存全部实例快照；FIFO depth只保留静态事实，不冒充动态深度证明。"
  observations:
    - "运行时能力端点：DMA_CAPABILITIES.CHANNEL_COUNT/MAX_TRANSFER_COUNT/FEATURES/IRQ_EVENTS应为合法能力集合。"
    - "组件身份端点：DMA_COMPONENT.DMA_ID/COMPONENT_ID应为有效值。"
    - "逐Channel参数：DMA_COMPONENT.CHANNEL_PARAMS[n]数量应等于Channel Count。"
  pass_criteria:
    - "实例完整性：全部静态实例均有Runtime Service。"
    - "能力合法性：CHANNEL_COUNT>0、MAX_TRANSFER_COUNT>0且包含M2M。"
    - "组件一致性：COMPONENT_ID有效且逐Channel max_block_size与Runtime上限一致。"
    - "证明边界：不宣称精确FIFO Physical Depth动态证明。"
timeout: "DMA Driver统一有界deadline"
cleanup: []
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "仅需DUT控制链路"}
backend: [FPGA, Silicon]
evidence: ["Canonical Measurement/Observation + bound structured Artifact"]
failure_observations:
  - {key: expected_instance_count, label: "Capability声明DMA实例数", source: oracle, role: expected, format: decimal}
  - {key: actual_channel_count, label: "DMA_CAPABILITIES.CHANNEL_COUNT", source: dut, role: actual, format: decimal}
  - {key: actual_component_id, label: "DMA_COMPONENT.COMPONENT_ID", source: dut, role: actual, format: hex32}
  - {key: actual_channel_params, label: "DMA_COMPONENT.CHANNEL_PARAMS", source: dut, role: actual, format: text}
gap: [fifo_depth_dynamic_proof_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P0_002
case_name: "DMA Controller/Channel基础生命周期、空闲分配与重复M2M恢复测试"
report_feature: |-
  1. DMA Channel数量/集合
  2. DMA Controller Enable/Disable控制
  3. DMA Channel Configure/Start/Stop流程
  4. DMA Channel FREE/FIFO_EMPTY状态
  5. DMA Free Channel分配
p_level: P0
feature_refs: [DMA_F_002, DMA_F_003, DMA_F_004, DMA_F_005, DMA_F_006]
method:
  inputs:
    - "目标资源：Capability/Runtime交集中的代表Controller/Channel和两组不同8 Byte Payload。"
    - "初始Expected：Channel FREE=1、FIFO_EMPTY=1且FREE_CHANNEL_FIND返回合法Channel。"
  steps:
    - "初始门禁：确认8 Byte M2M能力并读取FREE_CHANNEL_FIND和初始Channel Status。"
    - "第一轮准备：写入first Payload并预填Destination。"
    - "第一轮生命周期：Enable -> Configure -> Start -> Wait FREE。"
    - "第一轮观测：读取Destination、FREE和FIFO_EMPTY。"
    - "模块重新进入：Stop/Deconfigure/Disable后重新Enable并配置second Payload。"
    - "第二轮恢复：Start/Wait/Read，确认second数据、FREE/FIFO_EMPTY和再次可分配。"
  observations:
    - "初始/最终状态：DMA_CHANNEL_STATUS.FREE/FIFO_EMPTY应均为1。"
    - "两轮目标数据：DMA_DESTINATION_DATA分别应等于first/second Payload。"
  pass_criteria:
    - "状态判据：FREE_CHANNEL_FIND返回运行时范围内合法Channel。"
    - "状态判据：第一轮数据正确且FREE/FIFO_EMPTY=1。"
    - "数据判据：Disable/Re-enable后第二轮不同Payload仍正确。"
    - "通道再分配：第二轮后Channel可再次分配。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure本Case Channel", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Measurement/Observation + bound structured Artifact"]
failure_observations:
  - {key: initial_free, label: "初始DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
  - {key: initial_fifo_empty, label: "初始DMA_CHANNEL_STATUS.FIFO_EMPTY", source: dut, role: actual, format: bool}
  - {key: second_data_match, label: "重新使能后目标数据一致", source: measurement, role: actual, format: bool}
  - {key: final_free, label: "最终DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_001
case_name: "DMA全部可用Channel原子并发启动与独立数据一致性测试"
report_feature: |-
  1. DMA Channel数量/集合
  2. DMA Channel FREE/FIFO_EMPTY状态
p_level: P1
feature_refs: [DMA_F_002, DMA_F_005]
method:
  inputs:
    - "并发资源：代表Controller全部Runtime Channel，每Channel独立64 Byte Source/Destination与不同Payload。"
    - "启动集合：按Runtime Channel Count构造完整Mask。"
  steps:
    - "运行时Channel能力读取：读取Runtime Channel Count并逐Channel确认M2M能力。"
    - "资源准备：为每个Channel准备独立Source/Destination/Payload。"
    - "功能配置：Enable Controller并逐Channel Configure。"
    - "测试激励：一次CHANNELS_START启动完整Mask。"
    - "全Channel完成等待：逐Channel有界等待FREE。"
    - "并发数据与终态汇总：读取全部Destination与FREE状态并汇总。"
  observations:
    - "数据观测：每Channel DMA_DESTINATION_DATA应等于其独立Payload。"
    - "状态观测：全部DMA_CHANNEL_STATUS.FREE应为1。"
  pass_criteria:
    - "覆盖判据：Runtime全部Channel进入同一启动Mask。"
    - "数据判据：全部Channel数据无串扰且各自匹配。"
    - "状态判据：全部Channel最终FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["反向Stop/Deconfigure所有已配置Channel", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Measurement/Observation + bound structured Artifact"]
failure_observations:
  - {key: expected_channel_mask, label: "期望原子启动Mask", source: oracle, role: expected, format: hex32}
  - {key: actual_channel_mask, label: "实际启动Mask", source: dut_config, role: config, format: hex32}
  - {key: all_data_match, label: "全部Channel数据一致", source: measurement, role: actual, format: bool}
  - {key: all_channels_free, label: "全部Channel FREE", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "逐通道实际FREE状态", source: dut, role: actual, format: bool}

gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P1_002
case_name: "DMA通道优先级竞争与映射交换测试"
report_feature: |-
  1. DMA Channel Priority仲裁
p_level: P1
feature_refs: [DMA_F_012]
method:
  inputs:
    - "数据资源：低/中/高Priority竞争Channel与等长大Buffer，交换Channel/Priority映射复测。"
    - "预期结果：必须有独立硬件Progress/Timing Observer；不接受一次先完成作为唯一Oracle。"
  steps:
    - "能力确认：确认仲裁规格与统计判据。"
    - "资源准备：为竞争Channel准备独立等长数据。"
    - "优先级单变量配置：同Controller仅改变Priority配置。"
    - "测试激励：原子启动全部竞争Channel。"
    - "证据采集：记录首次进展/完成顺序并多轮统计。"
    - "结果判定：交换Channel/Priority映射复测并比较规律。"
  observations:
    - "时序观测：独立Progress/Timing端点应反映Priority仲裁。"
    - "数据观测：各Channel Destination最终应等于各自Payload。"
  pass_criteria:
    - "观测独立性：Observer不受CPU轮询偏差主导。"
    - "仲裁判据：规律随Priority移动而非固定Channel编号。"
    - "状态判据：全部数据正确且最终FREE。"
timeout: "统一有界deadline"
cleanup: ["恢复本Case配置的Channel与Controller"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需批准仲裁规格", bench: "需批准Progress/Timing Observer"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_priority_relation, label: "期望Priority仲裁关系", source: oracle, role: expected, format: text}
  - {key: actual_progress_trace, label: "Observer实际进度轨迹", source: observer, role: actual, format: text}
gap: [case_implementation_gap, priority_arbitration_observer_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P1_003
case_name: "DMA传输中Suspend/FIFO Drain/Resume测试"
report_feature: |-
  1. DMA Suspend/Resume控制
p_level: P1
feature_refs: [DMA_F_015]
method:
  inputs:
    - "挂起窗口数据：足够大的M2M传输，确保Suspend落在真实in-flight阶段。"
    - "Expected：Suspend后FIFO状态满足规范且Progress停滞，Resume后继续到完整数据。"
  steps:
    - "能力确认：确认安全in-flight窗口。"
    - "资源准备：准备大Source/Destination并Start。"
    - "传输中进度确认：读取Progress确认已开始未完成。"
    - "有界等待：请求Suspend并等待FIFO稳定状态。"
    - "挂起期进度采样：多次采样Progress确认暂停期无前进。"
    - "结果判定：Resume后等待FREE并比较完整Destination。"
  observations:
    - "状态观测：DMA_CHANNEL_STATUS.FIFO_EMPTY应满足Suspend规范。"
    - "时序观测：Source/Destination Progress暂停期应保持不变，Resume后继续。"
  pass_criteria:
    - "状态判据：Suspend发生于真实in-flight。"
    - "状态判据：暂停期无进度且FIFO状态正确。"
    - "状态判据：Resume后数据完整且FREE=1。"
timeout: "统一有界deadline"
cleanup: ["Stop/Deconfigure Channel", "Disable Controller"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "需确定性in-flight窗口"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_suspend_state, label: "期望Suspend状态", source: oracle, role: expected, format: text}
  - {key: actual_fifo_empty, label: "DMA_CHANNEL_STATUS.FIFO_EMPTY", source: dut, role: actual, format: bool}
gap: [case_implementation_gap, deterministic_inflight_window_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_004
case_name: "DMA TRANSFER_DONE分类中断、数据完成与Channel终态一致性测试"
report_feature: |-
  1. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
  2. DMA IRQ Channel位图
p_level: P1
feature_refs: [DMA_F_021, DMA_F_022]
method:
  inputs:
    - "数据资源：代表Controller/Channel，32 Byte确定性M2M Payload，目标事件TRANSFER_DONE。"
    - "中断条件：旧IRQ Result必须在Start前清除。"
  steps:
    - "能力确认：确认M2M与TRANSFER_DONE能力。"
    - "资源准备：准备Source/Destination。"
    - "DMA通道基础配置：Enable/Configure DMA。"
    - "完成中断启用与清零：Enable TRANSFER_DONE并Clear旧Result。"
    - "测试激励：Start，等待ISR Event Count>=1和Channel FREE。"
    - "证据采集：读取Destination、ISR Latch、异常计数与FREE并判定。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于Payload。"
    - "中断观测：ISR.LATCHED.TRANSFER_DONE=1，EVENT_COUNT>=1；计数属于Service Measurement。"
    - "状态观测：DMA_CHANNEL_STATUS.FREE=1。"
  pass_criteria:
    - "数据判据：数据正确。"
    - "中断判据：TRANSFER_DONE真实交付且unexpected/overflow=0。"
    - "状态判据：Channel FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable IRQ", "Stop/Deconfigure Channel", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_irq_event, label: "期望TRANSFER_DONE", source: oracle, role: expected, format: hex32}
  - {key: isr_latched_transfer_done, label: "ISR.LATCHED.TRANSFER_DONE", source: dut, role: actual, format: bool}
  - {key: irq_event_count, label: "ISR.EVENT_COUNT", source: service, role: actual, format: decimal}
  - {key: channel_free, label: "DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_005
case_name: "DMA单节点LLI的BLOCK_DONE中断与边界Channel行为测试"
report_feature: |-
  1. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
  2. DMA IRQ Channel位图
p_level: P1
feature_refs: [DMA_F_021, DMA_F_022]
method:
  inputs:
    - "执行资源：代表Controller首/末Channel两个参数实例。"
    - "数据资源：64 Byte Payload、单节点Descriptor、BLOCK_DONE。"
  steps:
    - "参数选择：选择first/last Channel。"
    - "资源准备：准备Source/Destination/Descriptor并初始化链尾。"
    - "LLI通道配置：Enable并Configure LINKED_LIST。"
    - "块中断启用与清零：Enable BLOCK_DONE并Clear旧Result。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：读取Destination、ISR Latch、计数与FREE并判定。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于Payload。"
    - "中断观测：ISR.LATCHED.BLOCK_DONE=1且EVENT_COUNT=1。"
    - "状态观测：DMA_CHANNEL_STATUS.FREE=1。"
  pass_criteria:
    - "覆盖判据：first/last两个实例均执行。"
    - "中断判据：数据正确、BLOCK_DONE精确交付、异常计数为0。"
    - "状态判据：Channel FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable IRQ", "Stop/Deconfigure Channel", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_irq_event, label: "期望BLOCK_DONE", source: oracle, role: expected, format: hex32}
  - {key: isr_latched_block_done, label: "ISR.LATCHED.BLOCK_DONE", source: dut, role: actual, format: bool}
  - {key: irq_event_count, label: "ISR.EVENT_COUNT", source: service, role: actual, format: decimal}
  - {key: channel_free, label: "DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_006
case_name: "DMA TRANSFER_DONE的RAW/STATUS/MASK/CLEAR状态机测试"
report_feature: |-
  1. DMA IRQ Channel位图
  2. DMA IRQ RAW/STATUS/MASK/CLEAR
p_level: P1
feature_refs: [DMA_F_022, DMA_F_025]
method:
  inputs:
    - "执行资源：Channel 0、TRANSFER_DONE、64 Byte M2M。"
    - "状态序列：before -> masked completion -> cleared -> enabled。"
  steps:
    - "资源准备：准备并Configure M2M。"
    - "功能配置：建立IRQ路由，Disable Mask并Clear Pending。"
    - "屏蔽前中断快照：读取before RAW/STATUS/MASK。"
    - "测试激励：Start/Wait，在Mask关闭时读取masked快照与Destination。"
    - "Pending清除后快照：Clear Pending后读取cleared RAW/STATUS。"
    - "状态恢复：重新Enable Mask并读取enabled状态与Channel FREE。"
  observations:
    - "中断观测：masked阶段IRQ_RAW.TRANSFER_DONE=1、IRQ_STATUS=0、IRQ_MASK=0。"
    - "状态观测：Clear后RAW/STATUS=0；重新Enable后MASK=1。"
  pass_criteria:
    - "初始中断状态：before RAW/STATUS/MASK均0。"
    - "屏蔽阶段状态：masked阶段RAW=1、STATUS=0、MASK=0。"
    - "状态判据：Clear后RAW/STATUS=0，Enable后MASK=1，数据正确且FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable Mask/IRQ", "Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: masked_raw, label: "Mask阶段IRQ_RAW", source: dut, role: actual, format: hex32}
  - {key: masked_status, label: "Mask阶段IRQ_STATUS", source: dut, role: actual, format: hex32}
  - {key: cleared_raw, label: "Clear后IRQ_RAW", source: dut, role: actual, format: hex32}
  - {key: enabled_mask, label: "重新使能IRQ_MASK", source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_007
case_name: "DMA Source/Destination/双端Reload连续Block与BLOCK_DONE测试"
report_feature: |-
  1. DMA Source/Destination Reload模式
p_level: P1
feature_refs: [DMA_F_016]
method:
  inputs:
    - "Reload矩阵：source/destination/both。"
    - "能力约束：使用Runtime MAX_TRANSFER_COUNT形成持续Reload，并要求BLOCK_DONE可用。"
  steps:
    - "能力确认：确认Reload/BLOCK_DONE能力。"
    - "资源准备：按当前模式准备Source/Destination与Expected。"
    - "功能配置：Enable/Configure Reload并Enable BLOCK_DONE。"
    - "有界等待：Start并Wait至少2次BLOCK_DONE。"
    - "状态恢复：主动Stop后读取Source/Destination Address Snapshot与Destination。"
    - "结果判定：按模式比较地址约束、数据、计数和异常状态。"
  observations:
    - "配置观测：DMA_CHANNEL.SOURCE_ADDRESS/DESTINATION_ADDRESS应满足当前Reload方向约束。"
    - "中断观测：ISR.LATCHED.BLOCK_DONE=1且EVENT_COUNT>=2。"
    - "数据观测：DMA_DESTINATION_DATA应符合当前模式Expected。"
  pass_criteria:
    - "覆盖判据：三种Reload模式全部执行。"
    - "数据判据：地址语义与数据正确。"
    - "中断判据：BLOCK_DONE>=2且unexpected/overflow=0。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable IRQ", "Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: reload_mode, label: "Reload模式", source: dut_config, role: config, format: text}
  - {key: source_address, label: "DMA_CHANNEL.SOURCE_ADDRESS", source: dut, role: actual, format: hex32}
  - {key: destination_address, label: "DMA_CHANNEL.DESTINATION_ADDRESS", source: dut, role: actual, format: hex32}
  - {key: block_event_count, label: "BLOCK_DONE事件计数", source: service, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_008
case_name: "DMA Source Gather Interval/Count与目标布局测试"
report_feature: |-
  1. DMA Source Gather模式
p_level: P1
feature_refs: [DMA_F_018]
method:
  inputs:
    - "数据资源：三组10 Byte有效数据+5 Byte间隔，Count=10、Interval=5。"
    - "数据资源：Expected为去除间隔后的连续30 Byte；Destination带Guard。"
  steps:
    - "能力确认：确认Source Gather能力。"
    - "资源准备：构造Source间隔布局和带Guard Destination。"
    - "功能配置：Enable/Configure Gather Count/Interval。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：读取完整Destination与Channel Status。"
    - "结果判定：比较目标有效区、Guard与Expected。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于三组有效数据连续拼接。"
    - "状态观测：Destination Guard保持哨兵值且FREE=1。"
  pass_criteria:
    - "有效区数据：目标有效区逐Byte等于Expected。"
    - "数据判据：Guard完整。"
    - "状态判据：Channel FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_data, label: "Gather Expected", source: oracle, role: expected, format: text}
  - {key: actual_data, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: guards_intact, label: "目标Guard完整", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_009
case_name: "DMA Destination Scatter Interval/Count与目标布局测试"
report_feature: |-
  1. DMA Destination Scatter模式
p_level: P1
feature_refs: [DMA_F_019]
method:
  inputs:
    - "数据资源：连续30 Byte Source，Count=10、Interval=1，Destination预填哨兵且带Guard。"
    - "预期结果：Expected为三组10 Byte之间保留1 Byte哨兵间隔。"
  steps:
    - "能力确认：确认Destination Scatter能力。"
    - "资源准备：准备Source与带Guard/间隔哨兵Destination。"
    - "功能配置：Enable/Configure Scatter Count/Interval。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：读取完整Destination与Channel Status。"
    - "结果判定：比较三组数据、间隔与Guard。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应形成10 Byte+间隔的预期布局。"
    - "状态观测：Guard和预期间隔保持哨兵，FREE=1。"
  pass_criteria:
    - "目标布局：目标布局逐Byte正确。"
    - "数据判据：Guard/间隔完整。"
    - "状态判据：Channel FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_layout, label: "Scatter Expected", source: oracle, role: expected, format: text}
  - {key: actual_layout, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: guards_intact, label: "Guard/间隔完整", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "DMA_CHANNEL_STATUS.FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_010
case_name: "DMA M2M Single/Half-Depth FIFO Mode配置读回与数据测试"
report_feature: |-
  1. DMA Single/Half-Depth FIFO模式
p_level: P1
feature_refs: [DMA_F_013]
method:
  inputs:
    - "FIFO矩阵：SINGLE/HALF_DEPTH，固定257 Byte M2M与16-item Burst。"
    - "数据资源：Expected FIFO Mode来自参数，数据Expected来自确定性向量。"
  steps:
    - "参数选择：选择FIFO Mode并确认257 Item能力。"
    - "资源准备：准备带Guard Source/Destination。"
    - "功能配置：Enable/Configure当前FIFO Mode。"
    - "FIFO模式读回：读取DMA_CHANNEL_CFG.FIFO_MODE并与Expected比较。"
    - "有界等待：Start并Wait FREE。"
    - "边界数据与Guard取证：读取Source/Destination/Guard并判定。"
  observations:
    - "配置观测：DMA_CHANNEL_CFG.FIFO_MODE应等于当前Expected。"
    - "状态观测：DMA_DESTINATION_DATA正确且FREE=1。"
  pass_criteria:
    - "覆盖判据：SINGLE/HALF_DEPTH均执行。"
    - "配置判据：每轮FIFO Mode硬件读回正确。"
    - "状态判据：数据、Guard、FREE均正确。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_fifo_mode, label: "Expected FIFO Mode", source: oracle, role: expected, format: text}
  - {key: actual_fifo_mode, label: "DMA_CHANNEL_CFG.FIFO_MODE", source: dut, role: actual, format: text}
  - {key: data_match, label: "目标数据一致", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_011
case_name: "DMA LLI Descriptor DONE完成状态写回测试"
report_feature: |-
  1. DMA LLI DONE写回
p_level: P1
feature_refs: [DMA_F_020]
method:
  inputs:
    - "基线条件：DONE初始False/True两个参数实例。"
    - "数据资源：64 Byte Payload；传输前后保存同一Descriptor内容。"
  steps:
    - "能力确认：确认Control Writeback能力。"
    - "资源准备：准备Source/Destination/Descriptor并写initial_done。"
    - "初始DONE与配置快照：读取before DONE与非控制字段。"
    - "功能配置：Enable/Configure LLI。"
    - "有界等待：Start并Wait FREE。"
    - "写后DONE与数据快照：读取after DONE、其他字段和Destination并判定。"
  observations:
    - "配置观测：LLI_DESCRIPTOR.DONE before应等于参数，after应为1。"
    - "数据观测：非控制字段不变，Destination正确。"
  pass_criteria:
    - "覆盖判据：两个initial_done实例均执行。"
    - "状态判据：完成后DONE均=1且非控制字段不变。"
    - "状态判据：数据正确且FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: initial_done, label: "LLI_DESCRIPTOR.DONE初始值", source: dut, role: actual, format: bool}
  - {key: final_done, label: "LLI_DESCRIPTOR.DONE完成值", source: dut, role: actual, format: bool}
  - {key: non_control_unchanged, label: "非控制字段不变", source: measurement, role: actual, format: bool}
  - {key: data_match, label: "目标数据一致", source: measurement, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_014
case_name: "DMA M2M传输宽度与源/目标地址模式组合测试"
report_feature: |-
  1. DMA M2M/M2P/P2M/P2P传输
  2. DMA 8/16/32-bit传输宽度
  3. DMA Source/Destination地址模式
p_level: P1
feature_refs: [DMA_F_007, DMA_F_008, DMA_F_009]
method:
  inputs:
    - "参数矩阵：8/16/32-bit × Source inc/dec/fixed × Destination inc/dec/fixed，共27实例。"
    - "数据资源：纯软件向量生成Source起始偏移和Expected Destination，Source/Destination均带Guard。"
  steps:
    - "参数选择：选择当前Width/Source Mode/Destination Mode。"
    - "资源准备：生成17 Item Source与Expected。"
    - "资源准备：准备带Guard Buffer。"
    - "功能配置：Enable/Configure当前参数。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：读取Source/Destination/Guard并汇总27实例。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于当前参数Expected。"
    - "状态观测：Source保持不变、Guard完整、FREE=1。"
  pass_criteria:
    - "覆盖判据：27参数实例全部执行。"
    - "数据判据：每轮Destination正确、Source不变。"
    - "状态判据：Guard完整且FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: parameter_id, label: "Width/Address Mode组合", source: oracle, role: expected, format: text}
  - {key: expected_data, label: "Expected Destination", source: oracle, role: expected, format: text}
  - {key: actual_data, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_015
case_name: "DMA M2M Block Count边界与Source/Destination Burst配置读回测试"
report_feature: |-
  1. DMA Burst Item数量
  2. DMA Block Size配置
p_level: P1
feature_refs: [DMA_F_010, DMA_F_011]
method:
  inputs:
    - "Count：1/2/3/4/7/8/15/16/255/256、Runtime MAX-1/MAX。"
    - "Burst：1/4/8/16/32/64/128/256 item，8-bit连续M2M。"
  steps:
    - "参数选择：解析Runtime MAX并生成当前Count向量。"
    - "资源准备：准备带Guard Buffer。"
    - "功能配置：Enable/Configure当前Block/Burst。"
    - "块与Burst配置读回：读取BLOCK_SIZE/SOURCE_BURST/DESTINATION_BURST并比较Expected。"
    - "有界等待：Start并Wait FREE。"
    - "Burst边界数据汇总：读取数据/Guard并汇总全部边界。"
  observations:
    - "配置观测：DMA_CHANNEL_CTL.BLOCK_SIZE/SOURCE_BURST/DESTINATION_BURST应等于Expected。"
    - "状态观测：DMA_DESTINATION_DATA正确且FREE=1。"
  pass_criteria:
    - "计数判据：Count边界与全部Burst编码均执行。"
    - "配置判据：硬件配置读回精确正确。"
    - "状态判据：数据、Guard、FREE均正确。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_block_size, label: "Expected Block Size", source: oracle, role: expected, format: decimal}
  - {key: actual_block_size, label: "DMA_CHANNEL_CTL.BLOCK_SIZE", source: dut, role: actual, format: decimal}
  - {key: actual_source_burst, label: "DMA_CHANNEL_CTL.SOURCE_BURST", source: dut, role: actual, format: text}
  - {key: actual_destination_burst, label: "DMA_CHANNEL_CTL.DESTINATION_BURST", source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_016
case_name: "DMA受Resource管理SRAM Buffer的M2M数据完整性与TRANSFER_DONE测试"
report_feature: |-
  1. DMA M2M/M2P/P2M/P2P传输
  2. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
  3. DMA IRQ Channel位图
p_level: P1
feature_refs: [DMA_F_007, DMA_F_021, DMA_F_022]
method:
  inputs:
    - "数据资源：两个Resource Driver管理的带Guard SRAM Buffer，256 Byte Payload。"
    - "执行资源：Channel 0启用TRANSFER_DONE；本Case不声明TCM/CPU别名覆盖。"
  steps:
    - "能力确认：确认256 Item M2M与TRANSFER_DONE能力。"
    - "资源准备：准备带Guard SRAM Source/Destination。"
    - "SRAM M2M通道配置：Enable/Configure SRAM M2M。"
    - "完成中断启用与清零：Enable TRANSFER_DONE并Clear旧Result。"
    - "测试激励：Start，Wait IRQ和FREE。"
    - "证据采集：读取Source/Destination/Guard/ISR Latch/FREE并判定。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于Payload且Guard完整。"
    - "中断观测：ISR.LATCHED.TRANSFER_DONE=1且FREE=1。"
  pass_criteria:
    - "数据判据：Destination正确、Source不变。"
    - "数据判据：Guard完整。"
    - "中断判据：TRANSFER_DONE交付且FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable IRQ", "Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_data, label: "期望SRAM数据", source: oracle, role: expected, format: text}
  - {key: actual_data, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: isr_latched_transfer_done, label: "TRANSFER_DONE ISR锁存", source: dut, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P1_017
case_name: "DMA非法配置拒绝边界与同Controller恢复测试"
report_feature: |-
  1. DMA 8/16/32-bit传输宽度
  2. DMA Source/Destination地址模式
  3. DMA Burst Item数量
  4. DMA Block Size配置
  5. DMA Peripheral Request接口
  6. DMA Source Gather模式
  7. DMA Destination Scatter模式
p_level: P1
feature_refs: [DMA_F_008, DMA_F_009, DMA_F_010, DMA_F_011, DMA_F_014, DMA_F_018, DMA_F_019]
method:
  inputs:
    - "7组非法矩阵：Count=0/MAX+1、未知Width/Burst、Channel越界、Gather Count/Interval越界。"
    - "恢复传输：随后32 Byte合法M2M恢复。"
  steps:
    - "证据采集：读取Runtime Count/Channel/Gather边界。"
    - "资源准备：准备合法恢复Source/Destination。"
    - "非法矩阵Controller使能：Enable同一Controller。"
    - "测试激励：逐项提交非法Config并记录预期/实际拒绝层。"
    - "能力确认：确认7/7均被正确拒绝。"
    - "合法M2M恢复执行：配置合法M2M并Start/Wait/Read恢复结果。"
  observations:
    - "状态观测：拒绝层/Status是Service Measurement，不冒充寄存器。"
    - "状态观测：恢复DMA_DESTINATION_DATA应等于Payload且FREE=1。"
  pass_criteria:
    - "访问判据：7/7非法向量被预期层拒绝。"
    - "数据判据：随后合法数据正确。"
    - "恢复后通道状态：恢复后FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure恢复Channel", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_rejected_count, label: "期望拒绝数", source: oracle, role: expected, format: decimal}
  - {key: actual_rejected_count, label: "实际拒绝数", source: service, role: actual, format: decimal}
  - {key: recovery_data_match, label: "恢复数据一致", source: measurement, role: actual, format: bool}
  - {key: recovery_channel_free, label: "恢复后FREE", source: measurement, role: actual, format: bool}
  - {key: recovery_free_state, label: "恢复后实际FREE状态", source: dut, role: actual, format: bool}

gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_001
case_name: "DMA双端LLI 2/3/4块有限Descriptor Chain传输测试"
report_feature: |-
  1. DMA LLI Descriptor Chain链式传输
p_level: P2
feature_refs: [DMA_F_017]
method:
  inputs:
    - "数据资源：2/3/4节点，每节点32 Byte独立Source/Destination与Descriptor。"
    - "描述符链接：Next Address按顺序链接，末节点Next=0。"
  steps:
    - "参数选择：选择block_count并生成每节点Pattern。"
    - "资源准备：准备N组Buffer与Descriptor。"
    - "参数选择：逐节点写Source/Destination/Next和链尾。"
    - "功能配置：Enable/Configure首Descriptor。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：读取全部Destination与Descriptor Chain并判定。"
  observations:
    - "数据观测：各Destination Block拼接应等于全部Source Pattern。"
    - "配置观测：LLI_DESCRIPTOR.NEXT_ADDRESS应形成有限链，末节点结束。"
  pass_criteria:
    - "覆盖判据：2/3/4节点均执行。"
    - "数据判据：链结构正确且数据逐Byte匹配。"
    - "状态判据：Channel FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: block_count, label: "LLI节点数", source: oracle, role: expected, format: decimal}
  - {key: descriptor_chain_valid, label: "Descriptor链结构有效", source: measurement, role: actual, format: bool}
  - {key: data_match, label: "全部目标块一致", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_002
case_name: "DMA单侧Source/Destination LLI地址更新测试"
report_feature: |-
  1. DMA LLI Descriptor Chain链式传输
p_level: P2
feature_refs: [DMA_F_017]
method:
  inputs:
    - "单侧LLI方向：source-only/destination-only两个方向，固定3节点×32 Byte。"
    - "数据资源：LLI侧分离Buffer，非LLI侧连续Buffer，Expected为三块Pattern拼接。"
  steps:
    - "参数选择：选择单侧LLI方向。"
    - "资源准备：按方向准备分离/连续Buffer和3个Descriptor。"
    - "单侧LLI配置：仅目标一侧配置LINKED_LIST，另一侧CONTIGUOUS。"
    - "功能配置：Enable/Configure首Descriptor。"
    - "有界等待：Start并Wait FREE。"
    - "结果判定：按Destination布局重建数据并读取Chain。"
  observations:
    - "配置观测：LLI_DESCRIPTOR.NEXT_ADDRESS应形成3节点有限链。"
    - "数据观测：重建DMA_DESTINATION_DATA应等于三块Expected。"
  pass_criteria:
    - "覆盖判据：source-only/destination-only均执行。"
    - "数据判据：链结构与数据正确。"
    - "状态判据：FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: lli_direction, label: "单侧LLI方向", source: oracle, role: expected, format: text}
  - {key: descriptor_chain_valid, label: "Descriptor链有效", source: measurement, role: actual, format: bool}
  - {key: data_match, label: "目标数据一致", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P2_003
case_name: "DMA LLI无效节点错误与清理后恢复测试"
report_feature: |-
  1. DMA LLI Descriptor Chain链式传输
p_level: P2
feature_refs: [DMA_F_017]
method:
  inputs:
    - "LLI故障刺激：Chip Profile批准的无效Next/断链/未对齐Descriptor。"
    - "LLI恢复对照：每个故障后运行合法有限LLI作为恢复对照。"
  steps:
    - "能力确认：确认安全故障窗口。"
    - "资源准备：构造故障链与目标保护区。"
    - "功能配置：Enable LLI与ERROR观测。"
    - "测试激励：Start并有界等待ERROR。"
    - "证据采集：读取ERROR、LLP/地址与保护区。"
    - "状态恢复：清理后运行合法LLI并确认恢复。"
  observations:
    - "中断观测：IRQ_RAW/STATUS.ERROR或ISR Latch应按场景出现。"
    - "数据观测：DMA_CHANNEL.LINKED_LIST_ADDRESS应定位故障节点，恢复数据应正确。"
  pass_criteria:
    - "错误判据：错误被有界捕获且不越过批准内存。"
    - "错误判据：错误现场可追溯。"
    - "LLI恢复结果：清理后合法LLI恢复成功。"
timeout: "统一有界deadline"
cleanup: ["Stop/Disable/Clear/Deconfigure", "运行恢复对照"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需安全无效LLI窗口", bench: "无外部仪器"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_error, label: "期望LLI错误", source: oracle, role: expected, format: text}
  - {key: actual_error_raw, label: "IRQ_RAW.ERROR", source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, safe_lli_fault_window_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_004
case_name: "DMA Combined IRQ路由下TRANSFER_DONE交付与M2M数据测试"
report_feature: |-
  1. DMA Combined IRQ中断
p_level: P2
feature_refs: [DMA_F_024]
method:
  inputs:
    - "执行资源：代表Controller Channel 0，64 Byte M2M，Combined Route承载TRANSFER_DONE。"
    - "Expected：单一Combined物理路由可让Service锁存TRANSFER_DONE。"
  steps:
    - "资源准备：准备64 Byte Source/Destination。"
    - "功能配置：Enable/Configure M2M。"
    - "组合中断路由：IRQ_COMBINED_ENABLE建立TRANSFER_DONE单一路由并Clear旧Result。"
    - "有界等待：Start并Wait ISR Event和FREE。"
    - "证据采集：读取Destination、ISR Latch、route_count与异常计数。"
    - "能力确认：确认route_count=1、数据正确、TRANSFER_DONE交付、FREE=1。"
  observations:
    - "组合路由计数：Combined route_count应=1，属于路由Measurement。"
    - "中断观测：ISR.LATCHED.TRANSFER_DONE=1，DMA_DESTINATION_DATA正确。"
  pass_criteria:
    - "计数判据：Combined route_count=1。"
    - "中断判据：TRANSFER_DONE真实交付且异常计数=0。"
    - "状态判据：数据正确、FREE=1。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["Disable Combined IRQ", "Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: combined_route_count, label: "Combined路由数量", source: service, role: actual, format: decimal}
  - {key: isr_latched_transfer_done, label: "TRANSFER_DONE ISR锁存", source: dut, role: actual, format: bool}
  - {key: data_match, label: "M2M数据一致", source: measurement, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_005
case_name: "UART RX DMA的P2M SOURCE_TRANSACTION+TRANSFER_DONE中断测试"
report_feature: |-
  1. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
p_level: P2
feature_refs: [DMA_F_021]
method:
  inputs:
    - "执行映射：Bench/Resolver提供UART RX DMA Route；DUT UART RX DMA、Peer UART Polling TX。"
    - "数据资源：31 Byte Payload；事件SOURCE_TRANSACTION|TRANSFER_DONE。"
  steps:
    - "P2M跨IP能力门禁：门禁DMA P2M/UART/Route/IRQ能力。"
    - "资源准备：准备31 Byte Destination。"
    - "UART RX DMA路由配置：初始化DUT/Peer UART，Enable UART DMA并配置SYSCTRL RX Route。"
    - "P2M通道与中断配置：Enable/Configure P2M并Enable两类IRQ。"
    - "测试激励：Start DMA后由Peer发送Payload。"
    - "有界等待：Wait IRQ/FREE，读取Destination与ISR Latch并判定。"
  observations:
    - "数据观测：DMA_DESTINATION_DATA应等于Peer Payload。"
    - "中断观测：ISR.LATCHED.SOURCE_TRANSACTION和TRANSFER_DONE均=1。"
  pass_criteria:
    - "Peer发送完整性：Peer完整发送31 Byte。"
    - "数据判据：Destination逐Byte正确。"
    - "中断判据：两类IRQ交付且FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Disable IRQ", "Stop/Deconfigure DMA", "Release SYSCTRL Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer或等价片内Peer", bench: "需UART DUT/Peer与RX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_payload, label: "Peer Payload", source: oracle, role: expected, format: text}
  - {key: actual_data, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: isr_latched_source_transaction, label: "SOURCE_TRANSACTION锁存", source: dut, role: actual, format: bool}
  - {key: isr_latched_transfer_done, label: "TRANSFER_DONE锁存", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_006
case_name: "UART TX DMA的M2P DESTINATION_TRANSACTION+TRANSFER_DONE中断测试"
report_feature: |-
  1. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
p_level: P2
feature_refs: [DMA_F_021]
method:
  inputs:
    - "执行映射：Bench/Resolver提供UART TX DMA Route；DUT UART TX DMA、Peer UART Polling RX。"
    - "数据资源：31 Byte Payload；事件DESTINATION_TRANSACTION|TRANSFER_DONE。"
  steps:
    - "M2P跨IP能力门禁：门禁DMA M2P/UART/Route/IRQ能力。"
    - "资源准备：准备31 Byte Source。"
    - "UART TX DMA路由配置：初始化UART/Peer，Enable UART DMA并配置TX Route。"
    - "M2P通道与中断配置：Enable/Configure M2P并Enable两类IRQ。"
    - "证据采集：Peer先Capture，再Start DMA。"
    - "有界等待：Wait Capture/IRQ/FREE并比较Peer数据与ISR Latch。"
  observations:
    - "数据观测：PEER_UART.RX_CAPTURE应等于Source Payload。"
    - "中断观测：ISR.LATCHED.DESTINATION_TRANSACTION和TRANSFER_DONE均=1。"
  pass_criteria:
    - "数据判据：Peer Capture数据正确。"
    - "中断判据：两类IRQ真实交付且异常计数=0。"
    - "状态判据：FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Cancel Capture", "Disable IRQ", "Stop/Deconfigure DMA", "Release Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer或等价片内Peer", bench: "需UART DUT/Peer与TX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_payload, label: "Source Payload", source: oracle, role: expected, format: text}
  - {key: peer_capture, label: "PEER_UART.RX_CAPTURE", source: peer, role: actual, format: text}
  - {key: isr_latched_destination_transaction, label: "DESTINATION_TRANSACTION锁存", source: dut, role: actual, format: bool}
  - {key: isr_latched_transfer_done, label: "TRANSFER_DONE锁存", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P2_007
case_name: "DMA受控Bus Error中断与恢复测试"
report_feature: |-
  1. DMA TRANSFER/BLOCK/SRC/DST/ERROR IRQ中断
p_level: P2
feature_refs: [DMA_F_021]
method:
  inputs:
    - "数据资源：Chip Profile批准的非致命bus-fault地址。"
    - "错误恢复传输：错误后32 Byte合法M2M恢复。"
  steps:
    - "能力确认：确认故障不会导致控制链路/CPU永久Fault。"
    - "功能配置：配置故障传输与ERROR观测。"
    - "测试激励：Start并有界等待ERROR。"
    - "DMA错误现场采集：读取IRQ ERROR/Channel/ISR现场。"
    - "错误状态清理确认：Mask/Stop/Clear/Deconfigure并确认ERROR清除。"
    - "结果判定：运行合法M2M恢复并比较数据。"
  observations:
    - "中断观测：IRQ_RAW/STATUS.ERROR或ISR.LATCHED.ERROR应按规格出现并可清。"
    - "数据观测：恢复DMA_DESTINATION_DATA应正确。"
  pass_criteria:
    - "错误判据：故障安全且ERROR可见。"
    - "错误判据：ERROR可清除。"
    - "错误恢复结果：后续合法M2M恢复成功。"
timeout: "统一有界deadline"
cleanup: ["完整ERROR Cleanup", "恢复合法M2M"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需批准非致命bus-fault地址", bench: "无外部仪器"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_error, label: "期望ERROR事件", source: oracle, role: expected, format: text}
  - {key: actual_error_raw, label: "IRQ_RAW.ERROR", source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, safe_bus_fault_window_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_008
case_name: "DMA M2P在1/17/257 Byte下的UART TX硬件握手数据路径测试"
report_feature: |-
  1. DMA M2M/M2P/P2M/P2P传输
  2. DMA Peripheral Request接口
p_level: P2
feature_refs: [DMA_F_007, DMA_F_014]
method:
  inputs:
    - "执行映射：长度1/17/257 Byte，Bench声明UART TX DMA Request Route。"
    - "数据资源：每长度确定性Payload，Peer Capture为独立Observer。"
  steps:
    - "M2P路由能力门禁：门禁DMA M2P/UART/Route能力。"
    - "资源准备：准备当前length Source。"
    - "UART TX握手路由配置：初始化UART/Peer、Enable DMA Request并配置TX Route。"
    - "硬件握手M2P配置：Enable/Configure硬件握手M2P。"
    - "证据采集：Peer先Capture再Start DMA。"
    - "有界等待：Wait Capture/FREE并比较数据，汇总三个长度。"
  observations:
    - "数据观测：PEER_UART.RX_CAPTURE应逐Byte等于Source Payload。"
    - "状态观测：DMA_CHANNEL_STATUS.FREE=1。"
  pass_criteria:
    - "覆盖判据：1/17/257三个长度均执行。"
    - "Peer接收数据：每轮Peer Capture正确。"
    - "状态判据：FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Cancel Capture", "Stop/Deconfigure", "Release Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer或等价片内Peer", bench: "需TX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_payload, label: "Expected Payload", source: oracle, role: expected, format: text}
  - {key: peer_capture, label: "PEER_UART.RX_CAPTURE", source: peer, role: actual, format: text}
  - {key: request_id, label: "DMA Request ID", source: mapping, role: config, format: decimal}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_009
case_name: "DMA P2M在1/17/257 Byte下的UART RX硬件握手数据路径测试"
report_feature: |-
  1. DMA M2M/M2P/P2M/P2P传输
  2. DMA Peripheral Request接口
p_level: P2
feature_refs: [DMA_F_007, DMA_F_014]
method:
  inputs:
    - "执行映射：长度1/17/257 Byte，Bench声明UART RX DMA Request Route。"
    - "数据资源：Peer TX确定性Payload，DMA Destination为Oracle。"
  steps:
    - "P2M路由能力门禁：门禁DMA P2M/UART/Route能力。"
    - "资源准备：准备当前length Destination。"
    - "UART RX握手路由配置：初始化UART/Peer、Enable DMA Request并配置RX Route。"
    - "硬件握手P2M配置：Enable/Configure硬件握手P2M。"
    - "测试激励：Start DMA后由Peer发送Payload。"
    - "有界等待：Wait FREE、Read Destination并汇总三个长度。"
  observations:
    - "数据观测：Peer transferred count应等于length。"
    - "状态观测：DMA_DESTINATION_DATA应等于Peer Payload且FREE=1。"
  pass_criteria:
    - "覆盖判据：1/17/257三个长度均执行。"
    - "数据判据：Peer完整发送且Destination正确。"
    - "状态判据：FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Release Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer或等价片内Peer", bench: "需RX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_payload, label: "Peer Payload", source: oracle, role: expected, format: text}
  - {key: transferred_bytes, label: "Peer实际发送字节", source: measurement, role: actual, format: decimal}
  - {key: actual_data, label: "DMA_DESTINATION_DATA", source: dut, role: actual, format: text}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_010
case_name: "DMA P2P双UART Route在1/17/257 Byte下的数据路径测试"
report_feature: |-
  1. DMA M2M/M2P/P2M/P2P传输
  2. DMA Peripheral Request接口
p_level: P2
feature_refs: [DMA_F_007, DMA_F_014]
method:
  inputs:
    - "数据资源：同一Controller解析UART RX Source与UART TX Destination两条Route。"
    - "数据资源：长度1/17/257 Byte，Peer Exchange最终接收数据为Oracle。"
  steps:
    - "P2P双向能力门禁：门禁DMA P2P与UART双向能力。"
    - "参数选择：解析并校验RX/TX两条Route属于当前Controller。"
    - "UART双向DMA路由配置：初始化UART/Peer、Enable UART DMA并配置两条Route。"
    - "P2P通道配置：Enable/Configure固定Peripheral到固定Peripheral P2P。"
    - "测试激励：Start DMA后执行Peer Exchange。"
    - "有界等待：Wait FREE并比较Peer最终数据，汇总三个长度。"
  observations:
    - "数据观测：Peer最终数据应逐Byte等于发送Payload。"
    - "状态观测：两条Route作为Mapping Measurement保存，FREE=1。"
  pass_criteria:
    - "覆盖判据：1/17/257三个长度均执行。"
    - "数据判据：两条Route完整且Peer数据正确。"
    - "状态判据：FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Stop/Deconfigure", "Release两条Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级双UART Peer或等价片内双端点", bench: "需RX/TX两条DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: expected_payload, label: "Peer发送Payload", source: oracle, role: expected, format: text}
  - {key: peer_capture, label: "Peer最终数据", source: peer, role: actual, format: text}
  - {key: source_request_id, label: "Source Request ID", source: mapping, role: config, format: decimal}
  - {key: destination_request_id, label: "Destination Request ID", source: mapping, role: config, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_011
case_name: "DMA Destination Software Handshake逐Item Request推进测试"
report_feature: |-
  1. DMA Software Handshake握手
  2. DMA Hardware/Software Handshake选择
p_level: P2
feature_refs: [DMA_F_026, DMA_F_028]
method:
  inputs:
    - "数据资源：4 Byte Payload，Destination Handshake=SOFTWARE，UART TX Route。"
    - "单次请求进度观测：每个Request前后读取Peer UART Capture接收计数，证明一个Item推进。"
  steps:
    - "软件握手能力门禁：门禁Software Handshake/UART Peer能力。"
    - "资源准备：准备Source、UART/Peer、TX Route和Capture。"
    - "功能配置：Enable/Configure Software Handshake并Start。"
    - "测试激励：无Request阶段读取Peer接收计数并确认不前进。"
    - "证据采集：逐Item发TRANSFER/SINGLE Request并读取每次Peer接收计数。"
    - "有界等待：Wait Capture/FREE并比较4 Byte数据和4个进度Delta。"
  observations:
    - "时序观测：无Request时Peer接收计数应保持不变。"
    - "时序观测：每次Request后Peer接收计数恰好增加一个Item；Peer Capture应等于Payload。"
  pass_criteria:
    - "无请求停滞：无Request不前进。"
    - "逐请求推进：4/4 Request逐Item推进。"
    - "状态判据：Peer数据正确且FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Cancel Capture", "Stop/Deconfigure", "Release Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer或等价片内Peer", bench: "需TX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: progress_before_request, label: "Request前Peer接收计数", source: peer, role: actual, format: decimal}
  - {key: progress_after_request, label: "Request后Peer接收计数", source: peer, role: actual, format: decimal}
  - {key: peer_capture, label: "PEER_UART.RX_CAPTURE", source: peer, role: actual, format: text}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_012
case_name: "UART TX Endpoint的Hardware/Software DMA Handshake Mode因果对照测试"
report_feature: |-
  1. DMA Hardware/Software Handshake选择
p_level: P2
feature_refs: [DMA_F_028]
method:
  inputs:
    - "数据资源：HARDWARE/SOFTWARE两个Mode，共用UART TX Endpoint与4 Byte Payload。"
    - "软件握手推进条件：Software Mode无Request不得推进，发Request后才逐Item前进。"
  steps:
    - "握手模式能力门禁：门禁Handshake Mode与UART Peer能力。"
    - "资源准备：准备Source/UART/Peer/TX Route和Capture。"
    - "功能配置：Enable/Configure当前Mode并Enable TRANSFER_DONE。"
    - "测试激励：Start；Hardware等待Request，Software先做无Request停滞观察。"
    - "证据采集：Software逐Item发Request并观察Peer接收计数变化。"
    - "结果判定：两种Mode均Wait Capture/IRQ/FREE并判定。"
  observations:
    - "时序观测：Software无Request时Peer接收计数不变，Request后逐Item增加。"
    - "数据观测：两种Mode的PEER_UART.RX_CAPTURE均等于Payload，TRANSFER_DONE锁存。"
  pass_criteria:
    - "覆盖判据：HARDWARE/SOFTWARE均执行。"
    - "软件握手行为：Software无Request不前进且发Request后推进。"
    - "中断判据：两种Mode数据正确、TRANSFER_DONE交付、FREE=1。"
timeout: "DMA/UART Driver统一有界deadline"
cleanup: ["Cancel Capture", "Disable IRQ", "Stop/Deconfigure", "Release Route", "Disable UART DMA", "Deinit UART/Peer"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "固定板级UART Peer；本Case不覆盖极性", bench: "需TX DMA Route"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: handshake_mode, label: "Handshake Mode", source: dut_config, role: config, format: text}
  - {key: peer_capture, label: "PEER_UART.RX_CAPTURE", source: peer, role: actual, format: text}
  - {key: isr_latched_transfer_done, label: "TRANSFER_DONE锁存", source: dut, role: actual, format: bool}
  - {key: channel_free, label: "Channel FREE", source: dut, role: actual, format: bool}
gap: [handshake_polarity_proof_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_013
case_name: "DMA NORMAL/ACC组件访问别名一致性测试"
report_feature: |-
  1. DMA Component ID/Channel能力/FIFO深度
p_level: P2
feature_refs: [DMA_F_033]
method:
  inputs:
    - "双访问路径快照：同一逻辑DMA实例的NORMAL与ACC Component Snapshot。"
    - "组件身份字段：比较DMA_ID、COMPONENT_ID、CHANNEL_PARAMS、MULTI_BLOCK/MAX_BLOCK参数。"
  steps:
    - "参数选择：选择逻辑DMA实例。"
    - "NORMAL组件快照：读取NORMAL完整组件Snapshot。"
    - "ACC组件快照：读取ACC完整组件Snapshot。"
    - "组件身份比较：比较DMA_ID/COMPONENT_ID。"
    - "组件能力参数比较：比较全部Channel/MultiBlock/MaxBlock参数。"
    - "双路径快照汇总：保存两套Snapshot并判定完全一致。"
  observations:
    - "身份观测：NORMAL DMA_COMPONENT.*完整快照。"
    - "身份观测：ACC DMA_COMPONENT.*完整快照；全部字段应与NORMAL相等。"
  pass_criteria:
    - "双路径身份一致性：身份完全一致。"
    - "双路径参数一致性：组件参数完全一致。"
    - "覆盖判据：不把Alias存在静默提升为所有芯片共有Feature。"
timeout: "DMA Driver统一有界deadline"
cleanup: []
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: normal_component_id, label: "NORMAL COMPONENT_ID", source: dut, role: actual, format: hex32}
  - {key: acc_component_id, label: "ACC COMPONENT_ID", source: dut, role: actual, format: hex32}
  - {key: snapshots_equal, label: "NORMAL/ACC Snapshot一致", source: measurement, role: actual, format: bool}
gap: [public_feature_identity_gap]
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P2_014
case_name: "DMA多Core TCM CPU/DMA地址视图映射测试"
report_feature: |-
  1. DMA TCM Bus Alias转换
p_level: P2
feature_refs: [DMA_F_023]
method:
  inputs:
    - "安全条件：Core0/Core1 × 各自允许ITCM/DTCM安全窗口 + 共享SRAM。"
    - "执行映射：Chip Mapping明确CPU Address、DMA Bus Alias、Cache策略和可破坏范围。"
  steps:
    - "能力确认：确认Core/TCM Execution Mapping。"
    - "资源准备：逐Core在批准窗口准备Source/Destination。"
    - "DMA地址语义配置：通过公共地址语义配置DMA，不硬编码芯片地址。"
    - "测试激励：执行批准的TCM<->SRAM组合。"
    - "证据采集：记录Core、CPU地址、DMA Alias和Cache维护。"
    - "结果判定：从CPU视图读回数据并完成矩阵判定。"
  observations:
    - "总线别名映射：CPU Address -> DMA Bus Alias应与Chip Mapping一致。"
    - "状态观测：对应Core读取Destination应等于Source且FREE=1。"
  pass_criteria:
    - "覆盖判据：所有执行组合都有明确Core/地址映射证据。"
    - "数据判据：数据正确且不访问未授权TCM。"
    - "状态判据：FREE=1。"
timeout: "统一有界deadline"
cleanup: ["恢复本CaseDMA/Memory/Cache状态"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需CORE1和安全TCM窗口", bench: "Execution Mapping未闭合前不得实现"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_dma_alias, label: "期望DMA Bus Alias", source: oracle, role: expected, format: hex32}
  - {key: actual_dma_address, label: "DMA实际地址视图", source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, case_measurement_gap, core_tcm_execution_mapping_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P2_015
case_name: "DMA经CRG Clock Gate/Reset后的M2M恢复测试"
report_feature: |-
  1. DMA Controller Enable/Disable控制
  2. DMA Channel Configure/Start/Stop流程
  3. DMA Channel FREE/FIFO_EMPTY状态
  4. DMA M2M/M2P/P2M/P2P传输
p_level: P2
feature_refs: [DMA_F_003, DMA_F_004, DMA_F_005, DMA_F_007]
method:
  inputs:
    - "数据资源：baseline/recovery两组不同32 Byte Payload。"
    - "时钟复位扰动：baseline后经公共CRG Driver执行Clock Disable/Enable + Reset。"
  steps:
    - "能力确认：确认32 Byte M2M和CRG资源能力。"
    - "资源准备：执行baseline M2M。"
    - "基线数据与终态取证：读取baseline Destination/FREE并完成阶段Cleanup。"
    - "时钟复位扰动执行：执行CRG Clock Disable->Enable->Reset。"
    - "扰动后M2M恢复：重新Enable/Configure并执行不同Payload recovery M2M。"
    - "恢复数据与终态比较：读取recovery Destination/FREE并比较两阶段。"
  observations:
    - "数据观测：baseline/recovery DMA_DESTINATION_DATA分别记录原始实际数据并应等于各自Payload。"
    - "状态观测：baseline/recovery DMA_CHANNEL_STATUS.FREE均=1；CRG动作作为跨IP Measurement。"
  pass_criteria:
    - "数据判据：baseline数据正确。"
    - "扰动序列完整性：Clock/Reset扰动序列完整。"
    - "状态判据：recovery不同Payload正确且FREE=1。"
timeout: "DMA/CRG Driver统一有界deadline"
cleanup: ["恢复本Case关闭的Clock", "Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: baseline_data_match, label: "Baseline数据一致", source: measurement, role: actual, format: bool}
  - {key: clock_reset_sequence, label: "CRG扰动序列", source: measurement, role: actual, format: text}
  - {key: recovery_data_match, label: "Recovery数据一致", source: measurement, role: actual, format: bool}
  - {key: recovery_channel_free, label: "Recovery FREE", source: dut, role: actual, format: bool}

gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_001
case_name: "DMA Source/Destination AHB Master选择测试"
report_feature: |-
  1. DMA Source/Destination AHB Master选择
p_level: P3
feature_refs: [DMA_F_030]
method:
  inputs:
    - "能力约束：Capability声明Source/Destination Master选项及可达Memory矩阵。"
    - "预期结果：每组合Expected为成功、拒绝或受控ERROR。"
  steps:
    - "能力确认：确认Master/Memory总线规格。"
    - "参数选择：选择当前Master组合与测试Memory。"
    - "功能配置：配置SMS/DMS并读取硬件配置。"
    - "测试激励：执行M2M并Wait完成或受控ERROR。"
    - "证据采集：读取数据/ERROR状态。"
    - "状态恢复：恢复默认Master并完成矩阵判定。"
  observations:
    - "配置观测：Master配置端点读回应等于Expected。"
    - "数据观测：可达组合数据正确，不可达组合按规格受控失败。"
  pass_criteria:
    - "配置判据：配置可证明。"
    - "访问判据：可达组合正确。"
    - "不可达组合处理：不可达组合受控且可恢复。"
timeout: "统一有界deadline"
cleanup: ["恢复默认Master配置", "清ERROR"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需批准总线矩阵", bench: "无外部仪器"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_master, label: "期望Master配置", source: oracle, role: expected, format: text}
  - {key: actual_master_config, label: "硬件Master配置读回", source: dut, role: actual, format: text}
gap: [case_implementation_gap, master_routing_contract_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_002
case_name: "DMA Protection/Permission允许与拒绝区域测试"
report_feature: |-
  1. DMA Protection属性
p_level: P3
feature_refs: [DMA_F_031]
method:
  inputs:
    - "安全条件：设计批准Protection属性、允许区与禁止区。"
    - "安全条件：禁止区必须是可恢复安全拒绝窗口。"
  steps:
    - "能力确认：确认权限模型。"
    - "功能配置：配置Protection并执行允许区M2M。"
    - "能力确认：确认允许区数据正确且无ERROR。"
    - "测试激励：访问批准禁止区。"
    - "证据采集：记录受控ERROR/安全状态。"
    - "状态恢复：清理后再次执行允许区恢复。"
  observations:
    - "配置观测：Protection配置端点读回正确。"
    - "错误观测：允许区数据正确；禁止区ERROR按规格出现。"
  pass_criteria:
    - "访问判据：允许区放行。"
    - "禁止区拒绝行为：禁止区受控拒绝且系统可恢复。"
    - "允许区恢复访问：清理后允许区再次通过。"
timeout: "统一有界deadline"
cleanup: ["清ERROR并恢复Protection"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需安全权限模型与拒绝窗口", bench: "DUT内部资源"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_access_result, label: "期望权限访问结果", source: oracle, role: expected, format: text}
  - {key: actual_error_status, label: "实际ERROR状态", source: dut, role: actual, format: hex32}
gap: [case_implementation_gap, permission_model_verification_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_003
case_name: "DMA最大AMBA Burst限制与边界测试"
report_feature: |-
  1. DMA MAX_AMBA_BURST_LEN配置
p_level: P3
feature_refs: [DMA_F_029]
method:
  inputs:
    - "AMBA Burst边界矩阵：设计允许max AMBA burst合法/边界/非法值。"
    - "数据资源：不同地址对齐与长度组合。"
  steps:
    - "能力确认：确认字段定义与合法范围。"
    - "参数选择：选择限制值/对齐/长度。"
    - "功能配置：配置并读取硬件值。"
    - "测试激励：执行合法M2M。"
    - "参数选择：遍历边界组合。"
    - "结果判定：提交非法值并确认拒绝。"
  observations:
    - "配置观测：Max Burst配置读回应等于Expected。"
    - "数据观测：合法数据正确，非法值在预期层拒绝。"
  pass_criteria:
    - "配置判据：合法配置读回正确。"
    - "数据判据：合法传输数据正确。"
    - "非法Burst恢复：非法值拒绝且Channel可恢复。"
timeout: "统一有界deadline"
cleanup: ["恢复默认Burst限制"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需设计确认", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_max_burst, label: "期望Max AMBA Burst", source: oracle, role: expected, format: decimal}
  - {key: actual_max_burst, label: "硬件Max AMBA Burst读回", source: dut, role: actual, format: decimal}
gap: [case_implementation_gap, max_amba_burst_contract_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_004
case_name: "DMA/Peripheral Flow Controller结束条件测试"
report_feature: |-
  1. DMA/Peripheral Flow Controller模式
p_level: P3
feature_refs: [DMA_F_032]
method:
  inputs:
    - "流控模式矩阵：DMA-controlled/Peripheral-controlled两种Mode。"
    - "流控Peer观测条件：具备可控结束条件和实际长度Observer的Peer。"
  steps:
    - "能力确认：确认Flow Control规格。"
    - "资源准备：准备Peer与数据。"
    - "功能配置：配置当前Control Mode与Route。"
    - "测试激励：启动并由控制方结束传输。"
    - "证据采集：读取Peer实际长度/数据/FREE。"
    - "结果判定：切换另一Mode复测并比较。"
  observations:
    - "数据观测：Peer实际长度应等于当前Mode Expected。"
    - "状态观测：Peer/DMA数据正确且FREE=1。"
  pass_criteria:
    - "覆盖判据：两种Mode均执行。"
    - "流控长度归属：结束长度由当前控制方决定。"
    - "流控数据与恢复：数据正确且可恢复。"
timeout: "统一有界deadline"
cleanup: ["释放Peer/Route/DMA"]
resources: {minimum_level: R2, full_coverage_level: R2, board: "需Flow Controller Peer", bench: "需结束条件和Route"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_length, label: "期望完成长度", source: oracle, role: expected, format: decimal}
  - {key: actual_peer_length, label: "Peer实际完成长度", source: peer, role: actual, format: decimal}
gap: [case_implementation_gap, flow_controller_peer_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_005
case_name: "DMA Low-Power Timeout状态与唤醒恢复测试"
report_feature: |-
  1. DMA Low-Power Timeout低功耗超时
p_level: P3
feature_refs: [DMA_F_034]
method:
  inputs:
    - "超时条件：代表性Timeout合法值。"
    - "低功耗场景矩阵：空闲进入、活动不误入、唤醒恢复三场景。"
  steps:
    - "能力确认：确认Timeout单位/状态/唤醒规格。"
    - "功能配置：配置Timeout并读取硬件值。"
    - "低功耗进入等待：空闲等待低功耗进入。"
    - "活动传输低功耗负对照：活动M2M确认不被错误中断。"
    - "低功耗唤醒与原因读取：触发规范唤醒并读状态/原因。"
    - "结果判定：唤醒后执行/完成M2M并比较数据。"
  observations:
    - "状态观测：Low-Power配置/状态应按规格变化。"
    - "数据观测：唤醒原因正确，恢复数据正确。"
  pass_criteria:
    - "配置判据：配置读回正确。"
    - "低功耗状态序列：进入/保持/退出状态符合规格。"
    - "唤醒后传输恢复：唤醒后DMA可继续工作。"
timeout: "统一有界deadline"
cleanup: ["恢复默认Low-Power配置"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "需低功耗规格和状态端点", bench: "不以模拟功耗值为Oracle"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_low_power_state, label: "期望低功耗状态", source: oracle, role: expected, format: text}
  - {key: actual_low_power_state, label: "实际低功耗状态", source: dut, role: actual, format: text}
gap: [case_implementation_gap, low_power_contract_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: DMA_P3_006
case_name: "DMA DFT/Test Slave受控进入与退出测试"
report_feature: |-
  1. DMA DFT/Test Slave模式
p_level: P3
feature_refs: [DMA_F_035]
method:
  inputs:
    - "测试模式：仅使用设计/DFT批准Test Slave模式和进入/退出序列。"
    - "测试模式退出对照：退出后32 Byte普通M2M作为恢复对照。"
  steps:
    - "能力确认：确认DFT授权与流程。"
    - "资源准备：先执行普通M2M基线。"
    - "测试模式进入：按批准序列进入Test Mode。"
    - "测试激励：执行规定有限响应并记录状态。"
    - "证据采集：按批准序列安全退出。"
    - "状态恢复：重新初始化并执行不同Payload M2M恢复。"
  observations:
    - "状态观测：Test Mode状态/规定响应符合DFT定义。"
    - "状态观测：退出后DMA_DESTINATION_DATA正确且FREE=1。"
  pass_criteria:
    - "测试模式切换顺序：进入/退出完全遵守批准序列。"
    - "测试模式响应：规定响应正确。"
    - "测试模式退出恢复：退出后普通M2M恢复。"
timeout: "统一有界deadline"
cleanup: ["安全退出Test Mode", "恢复普通DMA状态"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "必须DFT批准", bench: "产品不开放则NOT_APPLICABLE"}
backend: [FPGA, Silicon]
evidence: ["计划Canonical Evidence"]
failure_observations:
  - {key: expected_test_state, label: "期望Test模式状态", source: oracle, role: expected, format: bool}
  - {key: actual_test_state, label: "实际Test模式状态", source: dut, role: actual, format: bool}
gap: [case_implementation_gap, dft_authorization_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: DMA_P3_007
case_name: "DMA 20轮跨实例/Channel/Count/Width/Burst/FIFO混合M2M稳定性测试"
report_feature: |-
  1. DMA Controller实例集合
  2. DMA Channel数量/集合
  3. DMA Channel FREE/FIFO_EMPTY状态
  4. DMA M2M/M2P/P2M/P2P传输
  5. DMA 8/16/32-bit传输宽度
  6. DMA Burst Item数量
  7. DMA Single/Half-Depth FIFO模式
p_level: P3
feature_refs: [DMA_F_001, DMA_F_002, DMA_F_005, DMA_F_007, DMA_F_008, DMA_F_010, DMA_F_013]
method:
  inputs:
    - "20轮确定性序列：轮换Controller/Channel/Count/Width/Burst/FIFO。"
    - "预期结果：每轮独立Expected与Guard；决定性事实必须在Assert前记录。"
  steps:
    - "能力确认：读取可用实例Runtime Capability并生成20轮序列。"
    - "资源准备：逐轮准备带Guard Source/Destination和Expected。"
    - "轮次通道配置：逐轮Enable/Configure当前参数。"
    - "有界等待：Start并Wait FREE。"
    - "证据采集：Assert前记录数据/Guard/FREE。"
    - "结果判定：逐轮Cleanup，最终要求20/20轮Evidence闭合并一次发布Artifact。"
  observations:
    - "数据观测：每轮DMA_DESTINATION_DATA应等于Expected，Guard完整。"
    - "状态观测：每轮FREE=1；completed_rounds单调增加且中途FAIL不丢已形成Evidence。"
  pass_criteria:
    - "覆盖判据：20/20轮执行并有Evidence。"
    - "数据判据：20/20轮数据与Guard正确。"
    - "状态判据：20/20轮FREE=1且Cleanup完成。"
    - "前序证据保留：中途失败不丢前序Evidence。"
timeout: "DMA Driver统一有界deadline"
cleanup: ["每轮Stop/Deconfigure", "Disable Controller", "Reset Resource"]
resources: {minimum_level: R0, full_coverage_level: R0, board: "无额外要求", bench: "无额外要求"}
backend: [FPGA, Silicon]
evidence: ["Canonical Evidence"]
failure_observations:
  - {key: planned_rounds, label: "计划轮数", source: oracle, role: expected, format: decimal}
  - {key: completed_rounds, label: "已闭合Evidence轮数", source: service, role: actual, format: decimal}
  - {key: last_data_match, label: "最近一轮数据一致", source: measurement, role: actual, format: bool}
  - {key: last_channel_free, label: "最近一轮FREE", source: measurement, role: actual, format: bool}
  - {key: round_channel_free, label: "逐轮实际FREE状态", source: dut, role: actual, format: bool}

gap: []
```
<!-- ET_CASE_SPEC_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=22; PARTIAL_ADAPTATION=5; IMPLEMENTATION_GAP=8 | ADAPTED=27; IMPLEMENTATION_GAP=8; MAPPING_GAP=2; NEEDS_VERIFICATION=2 | TCM/Core、Polarity、FIFO Depth动态证明、8个PLAN实现Gap、2个Mapping Gap、2个Needs Verification | `ET6801_dma.md` |

## 5. Common Gap / Evolution

- F023 TCM：P1_016解绑，只由P2_014承载；等待CORE1 + safe TCM window + CPU/DMA alias映射。
- F027 Polarity：无可控active-high/low Request Source，保持Open Gap；P2_012只证明Hardware/Software Mode。
- F033 FIFO Depth：P0保留组件/静态能力证明，精确动态Depth仍为Gap。
- P2_013 NORMAL/ACC Alias：行为Case保留，公共Feature身份与跨芯片适用条件保持`public_feature_identity_gap`。
- 已闭合CASE_CHANGE：P0_002、P1_010、P1_015、P2_011、P2_012；其实现与Evidence已进入当前Formal SPEC。
- PLAN：P1_002、P1_003、P2_003、P2_007、P2_014、P3_001~P3_006。

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  DMA_P0_001:
    summary: "DMA全部声明实例的Runtime能力、组件身份与逐Channel参数集合保持一致。"
    fields:
      - {source: measurement, path: instance_count, label: Runtime实例数量, format: decimal, aggregate: same}
      - {source: observation, path: actual_channel_count, label: DMA通道数量, format: decimal, aggregate: range}
      - {source: observation, path: actual_component_id, label: DMA组件ID, format: hex32, aggregate: distinct}
      - {source: observation, path: actual_channel_params, label: 逐Channel组件参数, format: text, aggregate: distinct}
  DMA_P0_002:
    summary: "DMA Controller/Channel完成两轮生命周期后仍可重新分配并保持M2M正确。"
    fields:
      - {source: observation, path: initial_free, label: 初始Channel Free, format: bool, aggregate: same}
      - {source: observation, path: initial_fifo_empty, label: 初始FIFO Empty, format: bool, aggregate: same}
      - {source: measurement, path: second_data_match, label: 重新使能后数据一致, format: bool, aggregate: same}
      - {source: observation, path: final_free, label: 最终Channel Free, format: bool, aggregate: same}
  DMA_P1_001:
    summary: "全部运行时Channel可一次原子启动并分别完成独立M2M传输。"
    fields:
      - {source: measurement, path: channel_mask, label: 原子启动Channel Mask, format: hex32, aggregate: same}
      - {source: measurement, path: channel_count, label: 并发Channel数量, format: decimal, aggregate: same}
      - {source: measurement, path: all_data_match, label: 全部Channel数据一致, format: bool, aggregate: same}
      - {source: measurement, path: all_channels_free, label: 全部Channel最终Free, format: bool, aggregate: same}
  DMA_P1_004:
    summary: "TRANSFER_DONE在代表Channel完成M2M时真实交付且数据与终态一致。"
    fields:
      - {source: measurement, path: irq_event_count, label: IRQ事件计数, format: decimal, aggregate: same}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE ISR锁存, format: bool, aggregate: same}
      - {source: measurement, path: data_match, label: 目标数据一致, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P1_005:
    summary: "首/末边界Channel执行单节点LLI时BLOCK_DONE均可正确交付。"
    fields:
      - {source: measurement, path: boundary_channel, label: 边界Channel, format: decimal, aggregate: distinct}
      - {source: observation, path: isr_latched_block_done, label: BLOCK_DONE ISR锁存, format: bool, aggregate: same}
      - {source: measurement, path: irq_event_count, label: IRQ事件计数, format: decimal, aggregate: same}
      - {source: measurement, path: data_match, label: 目标数据一致, format: bool, aggregate: same}
  DMA_P1_006:
    summary: "TRANSFER_DONE在Mask关闭、Pending Clear和重新使能过程中的RAW/STATUS/MASK状态转换正确。"
    fields:
      - {source: observation, path: masked_raw, label: Mask阶段IRQ_RAW, format: hex32, aggregate: same}
      - {source: observation, path: masked_status, label: Mask阶段IRQ_STATUS, format: hex32, aggregate: same}
      - {source: observation, path: cleared_raw, label: Clear后IRQ_RAW, format: hex32, aggregate: same}
      - {source: observation, path: enabled_mask, label: 重新使能IRQ_MASK, format: hex32, aggregate: same}
  DMA_P1_007:
    summary: "Source/Destination/both Reload均持续完成多个Block并满足地址与BLOCK_DONE语义。"
    fields:
      - {source: measurement, path: reload_mode, label: Reload模式, format: text, aggregate: distinct}
      - {source: observation, path: source_address, label: Source地址快照, format: hex32, aggregate: distinct}
      - {source: observation, path: destination_address, label: Destination地址快照, format: hex32, aggregate: distinct}
      - {source: measurement, path: block_event_count, label: BLOCK_DONE事件计数, format: decimal, aggregate: range}
  DMA_P1_008:
    summary: "Source Gather按Count/Interval跳过源间隔并形成正确连续目标布局。"
    fields:
      - {source: measurement, path: gather_count, label: Gather计数, format: decimal, aggregate: same}
      - {source: measurement, path: gather_interval, label: Gather间隔, format: decimal, aggregate: same}
      - {source: observation, path: actual_data, label: Gather目标数据, format: text, aggregate: same}
      - {source: measurement, path: guards_intact, label: 目标Guard完整, format: bool, aggregate: same}
  DMA_P1_009:
    summary: "Destination Scatter按Count/Interval写入正确分段目标布局并保持间隔。"
    fields:
      - {source: measurement, path: scatter_count, label: Scatter计数, format: decimal, aggregate: same}
      - {source: measurement, path: scatter_interval, label: Scatter间隔, format: decimal, aggregate: same}
      - {source: observation, path: actual_layout, label: Scatter目标布局, format: text, aggregate: same}
      - {source: measurement, path: guards_intact, label: Guard/间隔完整, format: bool, aggregate: same}
  DMA_P1_010:
    summary: "Single与Half-Depth FIFO Mode均能被硬件正确编程并完成数据传输。"
    fields:
      - {source: measurement, path: expected_fifo_mode, label: 期望FIFO Mode, format: text, aggregate: distinct}
      - {source: observation, path: actual_fifo_mode, label: 硬件FIFO Mode读回, format: text, aggregate: distinct}
      - {source: measurement, path: data_match, label: 目标数据一致, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P1_011:
    summary: "LLI Descriptor DONE在初始0/1两种条件下完成后均为1且其他字段保持不变。"
    fields:
      - {source: observation, path: initial_done, label: 初始DONE, format: bool, aggregate: distinct}
      - {source: observation, path: final_done, label: 完成后DONE, format: bool, aggregate: same}
      - {source: measurement, path: non_control_unchanged, label: 非控制字段保持不变, format: bool, aggregate: same}
      - {source: measurement, path: data_match, label: 目标数据一致, format: bool, aggregate: same}
  DMA_P1_014:
    summary: "8/16/32-bit与Source/Destination三种地址模式组合均得到对应正确数据布局。"
    fields:
      - {source: measurement, path: parameter_id, label: Width/Address Mode组合, format: text, aggregate: distinct}
      - {source: measurement, path: expected_data_digest, label: Expected数据摘要, format: text, aggregate: distinct}
      - {source: measurement, path: actual_data_digest, label: 实际目标数据摘要, format: text, aggregate: distinct}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P1_015:
    summary: "Block Count边界与1~256 item Source/Destination Burst均可正确写入硬件并完成M2M。"
    fields:
      - {source: measurement, path: expected_block_size, label: 期望Block Size, format: decimal, aggregate: range}
      - {source: observation, path: actual_block_size, label: 硬件Block Size读回, format: decimal, aggregate: range}
      - {source: observation, path: actual_source_burst, label: Source Burst读回, format: text, aggregate: distinct}
      - {source: observation, path: actual_destination_burst, label: Destination Burst读回, format: text, aggregate: distinct}
  DMA_P1_016:
    summary: "受Resource管理的SRAM Buffer之间M2M数据正确且TRANSFER_DONE真实交付。"
    fields:
      - {source: measurement, path: data_match, label: SRAM目标数据一致, format: bool, aggregate: same}
      - {source: measurement, path: guards_intact, label: Source/Destination Guard完整, format: bool, aggregate: same}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE ISR锁存, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P1_017:
    summary: "七组非法DMA配置均在预期层被拒绝，随后同Controller合法M2M恢复成功。"
    fields:
      - {source: measurement, path: actual_rejected_count, label: 实际拒绝数量, format: decimal, aggregate: same}
      - {source: measurement, path: rejection_layers, label: 拒绝层级, format: text, aggregate: distinct}
      - {source: measurement, path: recovery_data_match, label: 恢复数据一致, format: bool, aggregate: same}
      - {source: measurement, path: recovery_channel_free, label: 恢复后Channel Free, format: bool, aggregate: same}
  DMA_P2_001:
    summary: "2/3/4节点双端LLI有限链均按Descriptor顺序完成全部分离Buffer传输。"
    fields:
      - {source: measurement, path: block_count, label: LLI节点数量, format: decimal, aggregate: range}
      - {source: measurement, path: descriptor_chain_valid, label: Descriptor链结构有效, format: bool, aggregate: same}
      - {source: measurement, path: data_match, label: 全部目标块数据一致, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_002:
    summary: "Source-only与Destination-only LLI两种单侧更新均完成三块正确数据传输。"
    fields:
      - {source: measurement, path: lli_direction, label: 单侧LLI方向, format: text, aggregate: distinct}
      - {source: measurement, path: descriptor_chain_valid, label: Descriptor链结构有效, format: bool, aggregate: same}
      - {source: measurement, path: data_match, label: 重建目标数据一致, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_004:
    summary: "Combined物理IRQ路由可把TRANSFER_DONE真实交付到Service并保持M2M数据正确。"
    fields:
      - {source: measurement, path: combined_route_count, label: Combined路由数量, format: decimal, aggregate: same}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE ISR锁存, format: bool, aggregate: same}
      - {source: measurement, path: data_match, label: M2M目标数据一致, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_005:
    summary: "UART RX P2M数据正确且SOURCE_TRANSACTION与TRANSFER_DONE均真实交付。"
    fields:
      - {source: measurement, path: request_id, label: RX DMA请求编号, format: decimal, aggregate: same}
      - {source: measurement, path: actual_data_digest, label: DMA目标数据摘要, format: text, aggregate: same}
      - {source: observation, path: isr_latched_source_transaction, label: SOURCE_TRANSACTION锁存, format: bool, aggregate: same}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE锁存, format: bool, aggregate: same}
  DMA_P2_006:
    summary: "UART TX M2P的Peer捕获数据正确且DESTINATION_TRANSACTION与TRANSFER_DONE均真实交付。"
    fields:
      - {source: measurement, path: request_id, label: TX DMA请求编号, format: decimal, aggregate: same}
      - {source: measurement, path: peer_capture_digest, label: Peer捕获摘要, format: text, aggregate: same}
      - {source: observation, path: isr_latched_destination_transaction, label: DESTINATION_TRANSACTION锁存, format: bool, aggregate: same}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE锁存, format: bool, aggregate: same}
  DMA_P2_008:
    summary: "UART TX硬件握手M2P在1/17/257 Byte下均完整到达Peer。"
    fields:
      - {source: measurement, path: length_bytes, label: 传输长度, format: decimal, aggregate: range, unit: byte}
      - {source: measurement, path: request_id, label: TX DMA请求编号, format: decimal, aggregate: same}
      - {source: measurement, path: peer_capture_digest, label: Peer捕获摘要, format: text, aggregate: distinct}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_009:
    summary: "UART RX硬件握手P2M在1/17/257 Byte下均完整写入Memory。"
    fields:
      - {source: measurement, path: length_bytes, label: 传输长度, format: decimal, aggregate: range, unit: byte}
      - {source: measurement, path: transferred_bytes, label: Peer实际发送字节, format: decimal, aggregate: range, unit: byte}
      - {source: measurement, path: actual_data_digest, label: DMA目标数据摘要, format: text, aggregate: distinct}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_010:
    summary: "双UART P2P在1/17/257 Byte下均把Peer输入完整转发到Peer输出。"
    fields:
      - {source: measurement, path: length_bytes, label: 传输长度, format: decimal, aggregate: range, unit: byte}
      - {source: measurement, path: source_request_id, label: 源请求编号, format: decimal, aggregate: same}
      - {source: measurement, path: destination_request_id, label: 目的请求编号, format: decimal, aggregate: same}
      - {source: measurement, path: peer_capture_digest, label: Peer最终数据摘要, format: text, aggregate: distinct}
  DMA_P2_011:
    summary: "Destination Software Handshake在无Request时停滞，每个Request推进受控Item并最终完成Payload。"
    fields:
      - {source: measurement, path: no_request_progress_delta, label: 无Request进度变化, format: decimal, aggregate: same}
      - {source: measurement, path: request_progress_deltas, label: 逐Request进度变化, format: text, aggregate: distinct}
      - {source: measurement, path: peer_capture_digest, label: Peer捕获摘要, format: text, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_012:
    summary: "Hardware/Software两种Handshake Mode均完成UART TX，且Software Mode仅在Request后推进。"
    fields:
      - {source: measurement, path: handshake_mode, label: 握手模式, format: text, aggregate: distinct}
      - {source: measurement, path: peer_capture_digest, label: Peer捕获摘要, format: text, aggregate: distinct}
      - {source: observation, path: isr_latched_transfer_done, label: TRANSFER_DONE锁存, format: bool, aggregate: same}
      - {source: observation, path: channel_free, label: Channel最终Free, format: bool, aggregate: same}
  DMA_P2_013:
    summary: "同一逻辑DMA的NORMAL与ACC组件访问视图返回完全一致的身份和参数。"
    fields:
      - {source: observation, path: normal_component_id, label: NORMAL组件ID, format: hex32, aggregate: distinct}
      - {source: observation, path: acc_component_id, label: ACC组件ID, format: hex32, aggregate: distinct}
      - {source: measurement, path: snapshots_equal, label: NORMAL/ACC快照一致, format: bool, aggregate: same}
  DMA_P2_015:
    summary: "DMA经过Clock Gate/Reset扰动后重新使能仍可完成正确M2M。"
    fields:
      - {source: measurement, path: baseline_data_match, label: 基线数据一致, format: bool, aggregate: same}
      - {source: measurement, path: clock_reset_sequence, label: CRG扰动序列, format: text, aggregate: same}
      - {source: measurement, path: recovery_data_match, label: 恢复后数据一致, format: bool, aggregate: same}
      - {source: observation, path: recovery_channel_free, label: 恢复后通道空闲, format: bool, aggregate: same}
  DMA_P3_007:
    summary: "20轮跨实例与多参数混合M2M均保持数据完整、Guard完整和Channel可恢复。"
    fields:
      - {source: measurement, path: planned_rounds, label: 计划轮数, format: decimal, aggregate: same}
      - {source: measurement, path: completed_rounds, label: 闭合Evidence轮数, format: decimal, aggregate: same}
      - {source: measurement, path: all_data_match, label: 20轮数据全部一致, format: bool, aggregate: same}
      - {source: measurement, path: all_channels_free, label: 20轮Channel全部Free, format: bool, aggregate: same}
```<!-- ET_CASE_REPORT_END -->
