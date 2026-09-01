# SPINLOCK Stable IP Contract

> 本文件定义 SPINLOCK 的芯片中立 Feature、Case、Oracle、Observation、资源和稳定自动化动作。
> 芯片实例、地址、寄存器、SDK API、Core 数量及目标适配差异只进入同目录 `<CHIP>_spinlock.md`。
> 当前11个Formal Case均已实现为`SPEC`；P2/P3依赖已部署片内Peer，源码实现和软件门禁均不等于硬件PASS。

## 0. Stable IP Contract

### 0.1 稳定对象与配置语义

| 稳定对象 | 公共语义 | 约束 |
|---|---|---|
| `SpinlockMode` | `ONE_STEP` / `TWO_STEP` | 一步模式只记录硬件 Owner；两步模式还记录软件 Process ID。目标支持集合由 Capability 给出。 |
| `resource_id` | 独立硬件锁资源编号 | 合法范围由 `resource_count` 决定，公共 Case 不写死最大编号。 |
| `process_id` | 同一 Master 内的软件执行实体编号 | 仅两步模式有效，合法范围由 `process_id_count` 决定。 |
| `wait_policy` | `TRY` / `BLOCKING` | `TRY` 必须有界返回；`BLOCKING` 只允许在异步 Peer Job 中执行，不能阻塞 PC 控制通道。 |
| `release_scope` | `RESOURCE` / `CURRENT_MASTER_ALL` / `GLOBAL_ALL` | 分别释放单资源、当前 Master 全部资源、所有 Master 的全部资源。 |
| `enabled` | 模块 Enable 状态 | Enable/Disable 与锁资源清除是两个独立动作；不得隐式等同。 |

### 0.2 稳定 Observation Endpoint

| Endpoint | 来源 | 原子事实 |
|---|---|---|
| `CONFIG.ENABLE` | `dut` | SPINLOCK 模块 Enable 状态。 |
| `CONFIG.MODE` | `dut` | 当前一步/两步模式。 |
| `RESOURCE_FLAGS.LOW` | `dut` | 低编号资源锁定状态位集合。 |
| `RESOURCE_FLAGS.HIGH` | `dut` | 高编号资源锁定状态位集合；目标没有第二组时由 Capability 声明不适用。 |
| `RESOURCE_INFO.LOCKED` | `dut` | 从无副作用的 Resource Flag 取得指定资源占用状态。 |
| `RESOURCE_INFO.MASTER_ID` | `dut` | 仅当 `LOCKED=1` 时读取的当前硬件 Owner；空闲时无效且禁止读取会触发 Acquire 的 Owner 端点。 |
| `RESOURCE_INFO.PROCESS_ID_VALID` | `dut` | 仅当 `LOCKED=1` 时有效的两步模式 Process ID 登记状态。 |
| `RESOURCE_INFO.PROCESS_ID` | `dut` | 仅当 `LOCKED=1` 且 `PROCESS_ID_VALID=1` 时有效的 Process ID。 |
| `PEER_JOB.STATE` | `peer` | 异步 Peer Job 当前状态。 |
| `PEER_JOB.ENTER_COUNT` | `peer` | Peer 成功进入受锁保护区域的次数。 |
| `SHARED_COUNTER.VALUE` | `measurement` | 位于 Capability/Execution Mapping 声明的片内共享可见内存中的计数终值。 |
| `CRITICAL_SECTION.VIOLATION_COUNT` | `measurement` | 位于同一共享可见内存中的临界区重入违规累计值。 |

### 0.3 稳定自动化动作

| 稳定动作 | 请求语义 | 约束 |
|---|---|---|
| `capabilities_get` | 获取模式、资源数量、Process ID数量、批量/全局释放、Peer能力和逻辑执行实体映射 | 只发布目标硬件事实；多Master Case要求逻辑实体到硬件Master ID映射已验证。 |
| `configure` | 设置 Enable 和 Mode | 不得隐式释放已占用资源；目标 Driver 若带隐式清除，必须由测试补充接口隔离。 |
| `config_snapshot_get` | 读取当前 Enable 和 Mode | 返回稳定逻辑值，不暴露芯片寄存器类型。 |
| `local_master_id_get` | 获取当前执行实体实际写入Owner字段的硬件Master ID | 只作为本地单Master Owner Oracle；不能替代多Core逻辑实体到Master ID的验证映射。 |
| `resource_acquire` | 按 Mode/Resource/Process/Wait Policy 获取资源 | `TRY` 有界；同步动作禁止无限等待。 |
| `resource_release` | 当前执行实体释放指定资源 | 非 Owner 释放不得改变真实 Owner。 |
| `resource_snapshot_get` | 先读取无副作用Flag；仅在Locked=1时读取Owner信息 | 空闲资源返回Locked=0且Owner字段无效，禁止为了观测Owner而读取会触发Acquire的端点。 |
| `batch_release` | 释放当前 Master 占用的全部资源 | 不得影响其他 Master 的资源。 |
| `global_release` | 初始化/恢复场景释放所有资源 | 是跨 Case 硬件基线动作，不代表普通业务释放。 |
| `clear_key_probe` | 以目标授权值执行 Batch/Global Clear 探测 | 仅当 Capability 声明 Key 保护可测；错误授权不得释放资源。 |
| `peer_job_start/status/result/abort` | 在片内 Peer 上异步执行持锁、阻塞获取或压力循环 | PC控制通道保持响应；Job必须具备STARTED/WAITING/HOLDING/DONE/ABORTED状态、明确ACK和可终止语义；持锁Job收到Release/Abort前不得自动释放。 |

### 0.4 Oracle、Timeout 与隔离

- 每个 Case 在第一次配置前执行 `global_release -> Service state reset -> Resource Pool reset`；任何一步失败立即终止 Case。
- 无副作用的Resource Flags是Locked/Free主证据；只有Flag证明Locked=1后，Owner端点读回才可作为Owner证据。API返回成功不能替代硬件状态。
- 多 Core Case 必须先证明 Peer Job 已进入预定状态，再执行竞争、释放和交接；禁止以固定 sleep 作为唯一同步依据。
- 多Core Case必须由Capability/Execution Mapping给出逻辑执行实体到硬件Master ID的已验证映射；映射未闭合时不得执行Owner Oracle。
- 共享计数压力Case的计数器、临界区标志和违规计数必须位于两个执行实体都可见的Coherent或Uncached共享内存；若使用Cacheable内存，执行映射必须定义必要的内存屏障和Cache维护，禁止把可见性问题误判为Spinlock失败。
- PC 持有 Case 总 deadline；Firmware 同步命令只做一次原子动作，阻塞获取和压力循环必须放入异步 Peer Job。
- Formal Case只依赖稳定SPINLOCK Driver、Capability/Resource Fixture和Canonical Evidence接口，不直接访问Codec、Transport或寄存器。
- 每个`failure_observations`同名硬件事实必须在对应断言前记录，确保断言失败时仍保留可回溯证据。
- Firmware Service只校验当前命令Wire、调用SPINLOCK Wrap并编码原始事实，不实现Case流程或通过判定。
- Cleanup 只需中止 Peer Job、执行 `global_release` 并 Disable 模块；下一 Case 仍重新建立完整基线。
- `GLOBAL_ALL` 仅用于初始化、恢复和专门 Case；普通释放路径不得借它掩盖 Owner 保护缺陷。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联 Case |
|---|---|---|---|
| SPINLOCK_F_001 | SPINLOCK模块Enable/Disable控制 | 模块可独立 Enable 和 Disable。 | `SPINLOCK_P0_001`, `SPINLOCK_P1_002` |
| SPINLOCK_F_002 | SPINLOCK一步锁模式 | 一步模式可按 Resource 建立和释放硬件 Owner。 | `SPINLOCK_P0_001`, `SPINLOCK_P0_002`, `SPINLOCK_P2_001`, `SPINLOCK_P2_002` |
| SPINLOCK_F_003 | SPINLOCK两步锁模式 | 两步模式可在硬件 Owner 基础上登记 Process ID。 | `SPINLOCK_P0_001`, `SPINLOCK_P0_003`, `SPINLOCK_P2_001`, `SPINLOCK_P2_002` |
| SPINLOCK_F_004 | SPINLOCK Resource Lock状态 | 指定 Resource 的占用状态可被读取。 | `SPINLOCK_P0_002`, `SPINLOCK_P0_003`, `SPINLOCK_P1_001` |
| SPINLOCK_F_005 | SPINLOCK Resource独立状态 | 不同 Resource 可独立锁定和释放，状态互不污染。 | `SPINLOCK_P1_001` |
| SPINLOCK_F_006 | SPINLOCK Process ID | 两步模式支持目标声明范围内的 Process ID。 | `SPINLOCK_P0_003` |
| SPINLOCK_F_007 | SPINLOCK Master Owner保护 | 非 Owner 不能释放或接管已锁定 Resource。 | `SPINLOCK_P2_001`, `SPINLOCK_P2_003` |
| SPINLOCK_F_008 | SPINLOCK阻塞获取与所有权移交 | 竞争者在 Owner 释放前保持等待，释放后取得 Resource。 | `SPINLOCK_P2_002` |
| SPINLOCK_F_009 | SPINLOCK Try成功/Timeout | Try 在空闲时成功，在竞争时有界失败，释放后可恢复成功。 | `SPINLOCK_P2_001` |
| SPINLOCK_F_010 | SPINLOCK当前Master批量释放 | 当前 Master 可一次释放自己占用的全部 Resource。 | `SPINLOCK_P2_004` |
| SPINLOCK_F_011 | SPINLOCK全部Master全局释放 | 初始化/恢复动作可释放全部 Master 的所有 Resource。 | `SPINLOCK_P2_004` |
| SPINLOCK_F_012 | SPINLOCK Disable锁状态保持 | Disable/Enable 不应隐式改变已存在的锁状态。 | `SPINLOCK_P1_002` |
| SPINLOCK_F_013 | SPINLOCK临界区互斥 | 多执行实体使用同一锁保护共享数据时不得同时进入临界区。 | `SPINLOCK_P3_001` |
| SPINLOCK_F_014 | SPINLOCK Clear Key保护 | 错误 Clear 授权值不得释放锁，正确授权值才能执行相应清除。 | `SPINLOCK_P1_003` |

## 2. Case Catalog

| Case ID | P级 | Case名称 | 主要 Feature | 最小充分 Oracle | Resource | 状态 |
|---|---:|---|---|---|---:|---|
| SPINLOCK_P0_001 | P0 | SPINLOCK配置模式读回测试 | Enable/Disable、一步/两步模式 | Enable与Mode读回逐项等于配置 | R0 | IMPLEMENTED |
| SPINLOCK_P0_002 | P0 | SPINLOCK一步模式全Resource获取释放测试 | 一步模式、锁状态 | 每个Resource获取后置位、释放后清零 | R0 | IMPLEMENTED |
| SPINLOCK_P0_003 | P0 | SPINLOCK两步模式Process ID测试 | 两步模式、锁状态、Process ID | 全Process ID读回正确并可释放 | R0 | IMPLEMENTED |
| SPINLOCK_P1_001 | P1 | SPINLOCK跨状态组多Resource独立性测试 | 锁状态、Resource独立性 | 边界Resource同时持有并逐个独立清除 | R0 | IMPLEMENTED |
| SPINLOCK_P1_002 | P1 | SPINLOCK Disable锁状态保持测试 | Enable/Disable、状态保持 | Disable/Re-enable前后Flags与Owner不变 | R0 | IMPLEMENTED |
| SPINLOCK_P1_003 | P1 | SPINLOCK Clear Key保护测试 | Clear Key保护 | 错误授权不清锁，正确授权完成清除 | R0 | IMPLEMENTED |
| SPINLOCK_P2_001 | P2 | SPINLOCK双Core Try竞争与恢复测试 | 模式、Owner保护、Try | 竞争时有界失败，Owner释放后成功 | R2 | IMPLEMENTED |
| SPINLOCK_P2_002 | P2 | SPINLOCK双Core阻塞获取与交接测试 | 阻塞获取、Owner移交 | 释放前Peer不进入，释放后只进入一次 | R2 | IMPLEMENTED |
| SPINLOCK_P2_003 | P2 | SPINLOCK非Owner释放保护测试 | Master Owner保护 | 非Owner释放后Flags与Owner保持不变 | R2 | IMPLEMENTED |
| SPINLOCK_P2_004 | P2 | SPINLOCK Batch与Global Release范围测试 | Batch Release、Global Release | Batch仅清当前Master，Global清全部 | R2 | IMPLEMENTED |
| SPINLOCK_P3_001 | P3 | SPINLOCK双Core共享计数互斥压力测试 | 临界区互斥 | 共享计数等于理论值且违规计数为0 | R2 | IMPLEMENTED |

## 3. Machine-readable Case Contract

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P0_001
case_name: SPINLOCK配置模式读回测试
report_feature: |-
  1. SPINLOCK模块Enable/Disable控制
  2. SPINLOCK一步锁模式
  3. SPINLOCK两步锁模式
p_level: P0
feature_refs: [SPINLOCK_F_001, SPINLOCK_F_002, SPINLOCK_F_003]
method:
  inputs:
    - 模式矩阵：ONE_STEP 与 TWO_STEP。
    - 状态矩阵：Enable 与 Disable。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 一步配置：Enable 模块并选择 ONE_STEP，读取 CONFIG 快照。
    - 一步判定：确认 CONFIG.ENABLE=1 且 CONFIG.MODE=ONE_STEP。
    - 两步配置：切换到 TWO_STEP，重新读取 CONFIG 快照。
    - 两步判定：确认 CONFIG.ENABLE=1 且 CONFIG.MODE=TWO_STEP。
    - 关闭判定：Disable 模块并确认 CONFIG.ENABLE=0。
  observations:
    - 配置状态：记录每轮 CONFIG.ENABLE 与 CONFIG.MODE 原始逻辑值。
  pass_criteria:
    - 一步配置：Enable 与 ONE_STEP 读回准确。
    - 两步配置：Enable 与 TWO_STEP 读回准确。
    - 关闭配置：Disable 后 Enable 读回为0。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: expected_enable, label: 期望Enable状态, source: oracle, role: expected, format: bool}
  - {key: actual_enable, label: CONFIG.ENABLE实际值, source: dut, role: actual, format: bool}
  - {key: expected_mode, label: 期望SPINLOCK模式, source: oracle, role: expected, format: text}
  - {key: actual_mode, label: CONFIG.MODE实际值, source: dut, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P0_002
case_name: SPINLOCK一步模式全Resource获取释放测试
report_feature: |-
  1. SPINLOCK一步锁模式
  2. SPINLOCK Resource Lock状态
p_level: P0
feature_refs: [SPINLOCK_F_002, SPINLOCK_F_004]
method:
  inputs:
    - Resource矩阵：由Capability发布的全部合法resource_id。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 模式配置：Enable SPINLOCK 并选择 ONE_STEP。
    - 单资源获取：按Capability顺序获取当前Resource。
    - 获取观测：读取当前Resource Flag和Owner，确认Locked=1且Owner为本执行实体。
    - 单资源释放：释放当前Resource并重新读取对应无副作用Flag。
    - 释放判定：确认当前Resource Flag=0，禁止读取空闲Resource的Owner端点，随后继续下一Resource。
    - 全域判定：确认全部Capability Resource均完成获取和释放。
  observations:
    - 获取状态：先记录对应Flag=1，再读取RESOURCE_INFO.MASTER_ID确认当前Owner。
    - 释放状态：记录释放后对应Flag=0；空闲状态不读取Owner端点。
  pass_criteria:
    - 全域覆盖：Capability发布的每个Resource恰好执行一轮。
    - 获取正确：每个Resource获取后Locked=1且Owner正确。
    - 释放正确：每个Resource释放后对应Flag=0。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: resource_id, label: 当前Resource ID, source: dut_config, role: config, format: decimal}
  - {key: locked_after_acquire, label: 获取后RESOURCE_INFO.LOCKED, source: dut, role: actual, format: bool}
  - {key: owner_after_acquire, label: 获取后RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
  - {key: flag_after_release, label: 释放后对应RESOURCE_FLAGS位, source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P0_003
case_name: SPINLOCK两步模式Process ID测试
report_feature: |-
  1. SPINLOCK两步锁模式
  2. SPINLOCK Resource Lock状态
  3. SPINLOCK Process ID
p_level: P0
feature_refs: [SPINLOCK_F_003, SPINLOCK_F_004, SPINLOCK_F_006]
method:
  inputs:
    - Process矩阵：由Capability发布的全部合法process_id。
    - Resource选择：Capability发布的一个代表性空闲Resource。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 模式配置：Enable SPINLOCK 并选择 TWO_STEP。
    - 两步获取：使用当前Process ID获取代表Resource。
    - Owner观测：读取Resource信息，确认Locked、Master、Process Valid和Process ID。
    - 资源释放：使用相同Process ID释放当前Resource。
    - 释放判定：确认对应Resource Flag=0且不读取空闲Owner端点，再执行下一Process ID。
    - 全域判定：确认全部Capability Process ID均独立完成获取与释放。
  observations:
    - Owner信息：记录LOCKED、MASTER_ID、PROCESS_ID_VALID和PROCESS_ID。
    - 释放信息：记录释放后的对应Flag；空闲状态不读取Owner端点。
  pass_criteria:
    - Process覆盖：Capability发布的每个Process ID均执行。
    - Owner正确：获取后Master正确、Process Valid=1且Process ID等于本轮配置。
    - 释放正确：使用相同Process ID释放后Resource变为空闲。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: expected_process_id, label: 期望Process ID, source: oracle, role: expected, format: decimal}
  - {key: actual_process_id, label: RESOURCE_INFO.PROCESS_ID实际值, source: dut, role: actual, format: decimal}
  - {key: process_id_valid, label: RESOURCE_INFO.PROCESS_ID_VALID, source: dut, role: actual, format: bool}
  - {key: actual_master_id, label: RESOURCE_INFO.MASTER_ID实际值, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P1_001
case_name: SPINLOCK跨状态组多Resource独立性测试
report_feature: |-
  1. SPINLOCK Resource Lock状态
  2. SPINLOCK Resource独立状态
p_level: P1
feature_refs: [SPINLOCK_F_004, SPINLOCK_F_005]
method:
  inputs:
    - 边界Resource集合：由Capability从首项、低组末项、高组首项和末项生成去重集合。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 模式配置：Enable SPINLOCK 并选择 ONE_STEP。
    - 多资源获取：依次获取全部边界Resource且中途不释放。
    - 状态观测：读取LOW/HIGH Flag Banks与每个Resource Owner信息。
    - 逐项释放：按获取顺序的逆序逐个释放Resource。
    - 独立判定：每次释放后只允许目标Resource Flag清零，其余已持有Resource保持锁定。
    - 最终判定：全部释放后两个Flag Banks均回到空闲基线。
  observations:
    - 状态组：记录每一步RESOURCE_FLAGS.LOW与RESOURCE_FLAGS.HIGH。
    - Owner信息：记录各边界Resource的LOCKED与MASTER_ID。
  pass_criteria:
    - 同时占用：全部边界Resource可同时保持Locked=1。
    - 独立释放：每次只清除目标Resource且其他Owner不变。
    - 最终恢复：释放结束后所有测试Resource均为空闲。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: boundary_resource_ids, label: 边界Resource ID集合, source: dut_config, role: config, format: text}
  - {key: flags_low, label: RESOURCE_FLAGS.LOW实际值, source: dut, role: actual, format: hex32}
  - {key: flags_high, label: RESOURCE_FLAGS.HIGH实际值, source: dut, role: actual, format: hex32}
  - {key: changed_resource_ids, label: 由前后Flag差值计算的Resource集合, source: measurement, role: actual, format: text}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P1_002
case_name: SPINLOCK Disable锁状态保持测试
report_feature: |-
  1. SPINLOCK模块Enable/Disable控制
  2. SPINLOCK Disable锁状态保持
p_level: P1
feature_refs: [SPINLOCK_F_001, SPINLOCK_F_012]
method:
  inputs:
    - 固定资源：Capability发布的一个代表性Resource。
    - 模式矩阵：ONE_STEP与TWO_STEP。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 锁定准备：Enable当前Mode并由本执行实体获取代表Resource。
    - 锁前观测：记录Resource Flags和完整Owner信息。
    - 模块关闭：只Disable模块，不执行任何Release或Clear。
    - 关闭观测：读取Config、Flags和Owner，确认锁状态没有变化。
    - 重新使能：以相同Mode重新Enable并再次读取Flags和Owner。
    - 结果判定：确认Disable/Re-enable全程Owner保持，最后由原Owner正常释放。
  observations:
    - 配置状态：记录CONFIG.ENABLE和CONFIG.MODE。
    - 保持状态：记录Disable前、Disable后和Re-enable后的Flags及Owner信息。
  pass_criteria:
    - Disable生效：CONFIG.ENABLE在关闭阶段为0。
    - 状态保持：三个观测点的Locked、Master和Process信息一致。
    - 恢复释放：Re-enable后原Owner可正常释放Resource。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: locked_before_disable, label: Disable前RESOURCE_INFO.LOCKED, source: dut, role: actual, format: bool}
  - {key: locked_while_disabled, label: Disable后RESOURCE_INFO.LOCKED, source: dut, role: actual, format: bool}
  - {key: owner_before_disable, label: Disable前RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
  - {key: owner_after_reenable, label: Re-enable后RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P1_003
case_name: SPINLOCK Clear Key保护测试
report_feature: |-
  1. SPINLOCK Clear Key保护
p_level: P1
feature_refs: [SPINLOCK_F_014]
method:
  inputs:
    - 锁资源集合：Capability发布的两个不同Resource。
    - 授权矩阵：无效Batch授权、无效Global授权和目标有效授权。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 锁定准备：Enable ONE_STEP并由本Master获取两个Resource。
    - 无效Batch刺激：提交错误Batch授权并读取两个Resource状态。
    - 无效Global刺激：提交错误Global授权并再次读取两个Resource状态。
    - 有效Batch刺激：提交目标有效Batch授权并读取Flags。
    - 结果判定：确认两次错误授权不改变锁状态，有效Batch授权清除本Master的两个Resource。
    - 最终恢复：执行有效Global Release建立下一Case安全基线。
  observations:
    - 授权前状态：记录两个Resource的LOCKED与MASTER_ID。
    - 授权后状态：分别记录无效Batch、无效Global和有效Batch后的LOW/HIGH Flag Bank原始值。
  pass_criteria:
    - 错误授权保护：两次错误授权后两个Resource仍由原Master持有。
    - 正确授权生效：有效Batch授权后两个Resource均为空闲。
    - 状态无旁路：判定依据为Resource Flags/Owner，而不是命令返回值。
timeout: 5s统一Case deadline
cleanup: [Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + bound structured Artifact]
failure_observations:
  - {key: flags_low_after_invalid_batch, label: 无效Batch后RESOURCE_FLAGS.LOW, source: dut, role: actual, format: hex32}
  - {key: flags_high_after_invalid_batch, label: 无效Batch后RESOURCE_FLAGS.HIGH, source: dut, role: actual, format: hex32}
  - {key: flags_low_after_invalid_global, label: 无效Global后RESOURCE_FLAGS.LOW, source: dut, role: actual, format: hex32}
  - {key: flags_high_after_invalid_global, label: 无效Global后RESOURCE_FLAGS.HIGH, source: dut, role: actual, format: hex32}
  - {key: flags_low_after_valid_batch, label: 有效Batch后RESOURCE_FLAGS.LOW, source: dut, role: actual, format: hex32}
  - {key: flags_high_after_valid_batch, label: 有效Batch后RESOURCE_FLAGS.HIGH, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P2_001
case_name: SPINLOCK双Core Try竞争与恢复测试
report_feature: |-
  1. SPINLOCK一步锁模式
  2. SPINLOCK两步锁模式
  3. SPINLOCK Master Owner保护
  4. SPINLOCK Try成功/Timeout
p_level: P2
feature_refs: [SPINLOCK_F_002, SPINLOCK_F_003, SPINLOCK_F_007, SPINLOCK_F_009]
method:
  inputs:
    - 模式矩阵：ONE_STEP与TWO_STEP。
    - 参与实体：DUT主执行实体与一个Capability声明的片内Peer，且两者到硬件Master ID的映射已验证。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - Owner获取：DUT在当前Mode获取代表Resource并确认Owner信息。
    - 竞争尝试：启动Peer TRY Job竞争同一Resource并等待有界结果。
    - 竞争判定：确认Peer返回Timeout或Busy，Resource Owner仍为DUT。
    - Owner释放：DUT释放Resource并确认Flag清零。
    - 恢复尝试：Peer再次TRY同一Resource并等待成功。
    - 移交判定：确认Owner切换为Peer，由Peer释放并在两个Mode重复执行。
  observations:
    - 竞争状态：记录Peer TRY结果、Resource Locked和Master Owner。
    - 恢复状态：记录第二次TRY结果及新的Master/Process信息。
  pass_criteria:
    - 竞争保护：DUT持锁时Peer TRY有界失败且Owner不变。
    - 释放恢复：DUT释放后Peer TRY成功。
    - 模式覆盖：ONE_STEP与TWO_STEP均完成同一因果链。
timeout: 10s统一Case deadline
cleanup: [Abort Peer Job, Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 目标提供至少两个可执行Master, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + Peer Measurement + bound structured Artifact]
failure_observations:
  - {key: peer_try_while_owned, label: Owner持锁时Peer TRY结果, source: peer, role: actual, format: text}
  - {key: owner_while_contended, label: 竞争期间RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
  - {key: peer_try_after_release, label: Owner释放后Peer TRY结果, source: peer, role: actual, format: text}
  - {key: owner_after_handoff, label: 交接后RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P2_002
case_name: SPINLOCK双Core阻塞获取与交接测试
report_feature: |-
  1. SPINLOCK一步锁模式
  2. SPINLOCK两步锁模式
  3. SPINLOCK阻塞获取与所有权移交
p_level: P2
feature_refs: [SPINLOCK_F_002, SPINLOCK_F_003, SPINLOCK_F_008]
method:
  inputs:
    - 模式矩阵：ONE_STEP与TWO_STEP。
    - 参与实体：DUT主执行实体与一个Capability声明的片内Peer，且两者到硬件Master ID的映射已验证。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - Owner获取：DUT获取代表Resource并确认Owner信息。
    - 阻塞启动：启动Peer异步BLOCKING Acquire Job并等待Job进入WAITING。
    - 等待反证：在有界观察窗口内确认Peer未进入临界区且Owner仍为DUT。
    - Owner释放：DUT释放Resource并等待Peer Job完成。
    - 交接观测：确认Peer只进入一次且Resource Owner切换为Peer。
    - 最终释放：由Peer释放Resource并在两个Mode重复执行。
  observations:
    - Job状态：记录PEER_JOB.STATE与ENTER_COUNT。
    - Owner交接：记录释放前后RESOURCE_INFO.MASTER_ID与LOCKED。
  pass_criteria:
    - 阻塞有效：Owner释放前Peer保持WAITING且ENTER_COUNT=0。
    - 交接有效：释放后Peer完成获取且ENTER_COUNT=1。
    - Owner准确：交接前后Master身份与实际执行实体一致。
timeout: 10s统一Case deadline
cleanup: [Abort Peer Job, Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 目标提供至少两个可执行Master, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + Peer Measurement + bound structured Artifact]
failure_observations:
  - {key: peer_state_before_release, label: Owner释放前PEER_JOB.STATE, source: peer, role: actual, format: text}
  - {key: peer_enter_count_before_release, label: Owner释放前PEER_JOB.ENTER_COUNT, source: peer, role: actual, format: decimal}
  - {key: peer_enter_count_after_release, label: Owner释放后PEER_JOB.ENTER_COUNT, source: peer, role: actual, format: decimal}
  - {key: owner_after_handoff, label: 交接后RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P2_003
case_name: SPINLOCK非Owner释放保护测试
report_feature: |-
  1. SPINLOCK Master Owner保护
p_level: P2
feature_refs: [SPINLOCK_F_007]
method:
  inputs:
    - 参与实体：DUT Owner与一个Capability声明的非Owner Peer，且两者到硬件Master ID的映射已验证。
    - 模式矩阵：ONE_STEP与TWO_STEP。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - Owner获取：DUT获取代表Resource并记录完整Owner信息。
    - 非Owner刺激：命令Peer对同一Resource执行Release。
    - 保护观测：读取Resource Flags与Owner信息。
    - 保护判定：确认Resource仍Locked且Master/Process信息没有改变。
    - 正常释放：由原Owner释放Resource并确认对应Flag清零；空闲状态不读取Owner端点。
    - 模式复测：在ONE_STEP和TWO_STEP下分别完成同一流程。
  observations:
    - 释放前信息：记录LOCKED、MASTER_ID、PROCESS_ID_VALID与PROCESS_ID。
    - 非Owner释放后信息：记录同一组Owner字段与Flag。
  pass_criteria:
    - 非Owner受限：Peer Release后Resource仍由原Owner持有。
    - Owner信息保持：Master和有效Process信息逐项不变。
    - 正常释放：原Owner Release后Resource变为空闲。
timeout: 10s统一Case deadline
cleanup: [Abort Peer Job, Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 目标提供至少两个可执行Master, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + Peer Measurement + bound structured Artifact]
failure_observations:
  - {key: owner_before_peer_release, label: 非Owner释放前RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
  - {key: owner_after_peer_release, label: 非Owner释放后RESOURCE_INFO.MASTER_ID, source: dut, role: actual, format: decimal}
  - {key: locked_after_peer_release, label: 非Owner释放后RESOURCE_INFO.LOCKED, source: dut, role: actual, format: bool}
  - {key: flag_after_owner_release, label: Owner释放后对应RESOURCE_FLAGS位, source: dut, role: actual, format: bool}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P2_004
case_name: SPINLOCK Batch与Global Release范围测试
report_feature: |-
  1. SPINLOCK当前Master批量释放
  2. SPINLOCK全部Master全局释放
p_level: P2
feature_refs: [SPINLOCK_F_010, SPINLOCK_F_011]
method:
  inputs:
    - Resource分组：DUT占用两个Resource，Peer占用另一个Resource；两者到硬件Master ID的映射已验证。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 分组占用：DUT获取两个Resource；Peer获取第三个Resource并进入HOLDING，在收到Release/Abort前持续持锁。
    - 初始观测：确认三个Resource均Locked且Owner分组正确。
    - Batch释放：由DUT执行Batch Release并读取三个Resource状态。
    - Scope判定：通过Flag确认DUT两个Resource清零；确认Peer Job仍为HOLDING，再读取Peer Resource Owner并确认不变。
    - Global释放：执行Global Release并重新读取三个Resource状态。
    - 最终判定：通过LOW/HIGH Flag Bank确认三个Resource全部为空闲；空闲资源不读取Owner端点。
  observations:
    - Batch结果：记录LOW/HIGH Flag Bank、Peer Job HOLDING状态及仍锁定Peer Resource的MASTER_ID。
    - Global结果：记录LOW/HIGH Flag Bank；空闲资源不读取Owner端点。
  pass_criteria:
    - Batch范围：只释放当前Master资源，不影响Peer Owner。
    - Global范围：释放所有Master的全部测试Resource。
    - 硬件证据：结论来自Flags与Owner读回，不依赖命令返回值。
timeout: 10s统一Case deadline
cleanup: [Abort Peer Job, Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 目标提供至少两个可执行Master, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + Peer Measurement + bound structured Artifact]
failure_observations:
  - {key: flags_low_after_batch, label: Batch后RESOURCE_FLAGS.LOW, source: dut, role: actual, format: hex32}
  - {key: flags_high_after_batch, label: Batch后RESOURCE_FLAGS.HIGH, source: dut, role: actual, format: hex32}
  - {key: peer_job_state_after_batch, label: Batch后PEER_JOB.STATE, source: peer, role: actual, format: text}
  - {key: peer_owner_after_batch, label: Batch后Peer Resource Master ID, source: dut, role: actual, format: decimal}
  - {key: flags_low_after_global, label: Global后RESOURCE_FLAGS.LOW, source: dut, role: actual, format: hex32}
  - {key: flags_high_after_global, label: Global后RESOURCE_FLAGS.HIGH, source: dut, role: actual, format: hex32}
gap: []
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
implementation_status: IMPLEMENTED
case_id: SPINLOCK_P3_001
case_name: SPINLOCK双Core共享计数互斥压力测试
report_feature: |-
  1. SPINLOCK临界区互斥
p_level: P3
feature_refs: [SPINLOCK_F_013]
method:
  inputs:
    - 执行轮数：由PC计划提供固定且可复现的loop_count。
    - 参与实体：DUT主执行实体与一个Capability声明的片内Peer，且两者到硬件Master ID的映射已验证。
    - 共享内存：Capability/Execution Mapping声明的Coherent或Uncached共享区；若为Cacheable区，必须声明屏障与Cache维护策略。
  steps:
    - 基线建立：执行 Global Release、Service State Reset 和 Resource Pool Reset。
    - 共享状态初始化：在声明的共享可见内存中清零Shared Counter、临界区标志和Violation Count，并完成必要的可见性同步。
    - 压力启动：两个执行实体使用同一ONE_STEP Resource并发执行loop_count轮。
    - 临界区操作：每轮获取锁，执行规定的内存屏障/Cache维护，检查独占标志、递增Shared Counter，再同步并释放锁。
    - 完成等待：PC轮询两个异步Job直到完成或统一deadline到期。
    - 终态观测：读取两个Job结果、Shared Counter、Violation Count和Resource状态。
    - 结果判定：确认计数为2倍loop_count、违规为0且Resource最终空闲。
  observations:
    - 共享结果：记录SHARED_COUNTER.VALUE与CRITICAL_SECTION.VIOLATION_COUNT。
    - Job结果：记录两个PEER_JOB完成轮数、状态和最终Resource Flag。
  pass_criteria:
    - 轮数完整：两个执行实体均完成全部loop_count轮。
    - 数据正确：SHARED_COUNTER.VALUE=2*loop_count。
    - 互斥成立：VIOLATION_COUNT=0且最终Resource为空闲。
timeout: 30s统一Case deadline
cleanup: [Abort Peer Jobs, Global Release, Disable SPINLOCK, Resource Pool Reset]
resources: {minimum_level: R2, full_coverage_level: R2, board: 目标提供至少两个可执行Master, bench: 无外部接线}
backend: [FPGA, Silicon]
evidence: [Canonical Observation + Peer Measurement + bound structured Artifact]
failure_observations:
  - {key: loop_count, label: 每个执行实体计划循环次数, source: dut_config, role: config, format: decimal}
  - {key: dut_completed_count, label: DUT实际完成循环次数, source: dut, role: actual, format: decimal}
  - {key: peer_completed_count, label: Peer实际完成循环次数, source: peer, role: actual, format: decimal}
  - {key: shared_counter, label: SHARED_COUNTER.VALUE实际值, source: measurement, role: actual, format: decimal}
  - {key: violation_count, label: CRITICAL_SECTION.VIOLATION_COUNT实际值, source: measurement, role: actual, format: decimal}
gap: []
```
<!-- ET_CASE_SPEC_END -->

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 | ADAPTED=14 | ADAPTED=11 | 双Core代码映射已完成；FPGA/Silicon仍须分别取得当前SHA HIL证据 | `ET6801_spinlock.md` |

目标芯片适配必须提供：

- SPINLOCK实例、支持模式、`resource_count`、`process_id_count`与可用Peer执行实体；
- Stable Endpoint到目标寄存器/Field的映射；
- Enable/Disable、Mode切换、单Resource Acquire/Release、Batch/Global Release的Driver映射；
- 不隐式清锁的配置接口，以及仅供验证Clear Key保护的受限Test Driver接口；
- 异步Peer Job启动、状态、结果和Abort执行映射；
- 逻辑执行实体到硬件Master ID的验证映射，以及双Core共享内存的Coherent/Uncached或Cache维护约束；
- FPGA和Silicon分别独立的硬件证据，不能用历史日志或源码替代。

## 5. Common Gap / Evolution

当前公共设计保留以下边界：

- 目标没有多个硬件Master时，P2/P3 Peer Case才可按真实环境标记不适用；不得因平台代码未实现而SKIP。
- Future IP若增加公平性、优先级、递归锁、超时寄存器、IRQ或DMA，应新增原子Feature与Case，不能改变现有Feature含义。
- `TRY`的软件轮询上限是执行策略，不是硬件Feature；报告必须记录真实Owner状态和最终结果。
- 阻塞获取必须异步执行，公共控制通道不得被无限循环占用。
- 11个Formal Case均已形成SPEC；P2/P3的硬件结论必须等待对应双核映像部署后的独立HIL证据。

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  SPINLOCK_P0_001:
    summary: "ONE_STEP、TWO_STEP和Disable配置均由硬件快照准确读回。"
    fields:
      - {source: measurement, path: config_snapshots, label: CONFIG Enable与Mode读回序列, format: text, aggregate: same}
  SPINLOCK_P0_002:
    summary: "Capability发布的全部Resource均完成ONE_STEP获取、Owner确认和释放。"
    fields:
      - {source: measurement, path: resource_measurements, label: 全Resource锁定与Owner观测, format: text, aggregate: same}
  SPINLOCK_P0_003:
    summary: "Capability发布的全部Process ID均在TWO_STEP模式准确登记并释放。"
    fields:
      - {source: measurement, path: process_measurements, label: 全Process ID与Owner观测, format: text, aggregate: same}
  SPINLOCK_P1_001:
    summary: "跨LOW/HIGH Flag Bank的边界Resource可独立锁定并逐项释放。"
    fields:
      - {source: measurement, path: flag_transitions, label: RESOURCE_FLAGS逐项变化, format: text, aggregate: same}
  SPINLOCK_P1_002:
    summary: "Disable及同模式Re-enable期间Resource锁定状态与Owner保持不变。"
    fields:
      - {source: measurement, path: state_hold, label: Disable前后Resource状态, format: text, aggregate: distinct}
  SPINLOCK_P1_003:
    summary: "错误Clear授权不改变锁状态，正确Batch授权清除当前Master资源。"
    fields:
      - {source: measurement, path: clear_key_observations, label: Clear授权前后RESOURCE_FLAGS, format: text, aggregate: same}
  SPINLOCK_P2_001:
    summary: "本地Master持锁时Peer TRY返回BUSY，释放后Peer取得同一Resource。"
    fields:
      - {source: observation, path: peer_try_while_owned, label: Owner持锁时Peer TRY结果, format: text, aggregate: same}
      - {source: observation, path: owner_after_handoff, label: 释放后Resource Master ID, format: decimal, aggregate: distinct}
  SPINLOCK_P2_002:
    summary: "Owner释放前Peer保持WAITING，释放后Peer只完成一次所有权交接。"
    fields:
      - {source: observation, path: peer_state_before_release, label: Owner释放前Peer Job状态, format: text, aggregate: same}
      - {source: observation, path: peer_enter_count_after_release, label: Owner释放后Peer进入次数, format: decimal, aggregate: same}
  SPINLOCK_P2_003:
    summary: "非Owner Peer执行Release后Resource Owner保持不变，原Owner可正常释放。"
    fields:
      - {source: observation, path: owner_before_peer_release, label: Peer释放前Resource Master ID, format: decimal, aggregate: same}
      - {source: observation, path: owner_after_peer_release, label: Peer释放后Resource Master ID, format: decimal, aggregate: same}
  SPINLOCK_P2_004:
    summary: "Batch只清除当前Master资源，Global清除两个Master的全部测试Resource。"
    fields:
      - {source: observation, path: flags_low_after_batch, label: Batch后RESOURCE_FLAGS.LOW, format: hex32, aggregate: same}
      - {source: observation, path: flags_low_after_global, label: Global后RESOURCE_FLAGS.LOW, format: hex32, aggregate: same}
  SPINLOCK_P3_001:
    summary: "两个Master完成全部互斥循环，共享计数等于理论值且违规计数为零。"
    fields:
      - {source: observation, path: shared_counter, label: 共享计数实际值, format: decimal, aggregate: same}
      - {source: observation, path: violation_count, label: 临界区互斥违规次数, format: decimal, aggregate: same}
```
<!-- ET_CASE_REPORT_END -->
