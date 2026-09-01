# CPU Public Test Contract

> 本文件只定义自动化平台使用的跨芯片 CPU NMI Owner 稳定语义。CPU 内核指令、Cache、MPU 和异常全集不在本轮范围内。

## 0. Stable IP Contract

### 0.1 稳定数据与动作

| 稳定语义 | 公共含义 | 约束 |
|---|---|---|
| `nmi_source_mask` | CPU NMI Source屏蔽位集合；置位表示屏蔽，清零表示允许 | 支持位集合由Runtime Capability发布；公共层不绑定物理Source位含义 |
| `nmi_source_raw` | 屏蔽前NMI Source状态 | 只读硬件事实，不能由ISR计数替代 |
| `nmi_source_masked` | 屏蔽后NMI Source状态 | 只读硬件事实，必须与当前Mask分开报告 |
| `nmi_status` | CPU NMI输入状态 | 只读硬件事实，不等同于某个外设Source |
| `nmi_event_count` | 真实进入NMI向量的有界软件计数 | 只证明向量交付，不证明外设功能正确 |
| `bounded_delivery` | 首次NMI交付后，CPU Owner立即屏蔽全部已发布Source | 防止Level Source重复进入饿死线程；下一次交付必须由PC重新配置Mask显式Arm |

公共动作保持为：

```text
CAPABILITIES_GET
NMI_CONFIGURE(nmi_source_mask)
NMI_SNAPSHOT_GET
NMI_EVENT_CLEAR
```

`NMI_CONFIGURE`负责写入Mask并Arm一次有界交付。NMI Handler只允许执行两件事：饱和增加`nmi_event_count`，并通过CPU Wrap把全部已发布Source重新屏蔽。它不得识别或清理WDG、STIMER等其他IP Source。

### 0.2 稳定Observation Endpoint

| Endpoint | 事实 | 证明用途 |
|---|---|---|
| `NMI_ROUTE.SOURCE_RAW` | 屏蔽前Source状态 | 证明目标硬件Source真实有效 |
| `NMI_ROUTE.SOURCE_MASKED` | 屏蔽后Source状态 | 证明Mask后的路由状态 |
| `NMI_ROUTE.MASK` | 当前Source Mask | 证明配置与首次交付后的自动屏蔽状态 |
| `NMI_ROUTE.STATUS` | CPU NMI输入状态 | 证明CPU侧NMI状态 |
| `NMI_DELIVERY.EVENT_COUNT` | NMI向量进入次数 | 证明真实NMI向量交付 |

## 1. Feature Catalog

| Feature ID | 报告名称 | 公共测试语义 | 主要Case |
|---|---|---|---|
| CPU_F_001 | CPU NMI Source屏蔽配置 | 支持的NMI Source可被显式屏蔽或允许，配置必须有硬件Mask读回 | CPU_P1_001 |
| CPU_F_002 | CPU NMI Raw/Masked/Status状态 | CPU Owner可分别读取屏蔽前Source、屏蔽后Source和CPU NMI状态 | CPU_P1_001 |
| CPU_F_003 | CPU NMI有界交付 | 首次真实NMI进入向量后Event Count增加并自动屏蔽Source，协议线程仍可继续运行 | CPU_P1_002 |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| CPU_P1_001 | P1 | CPU NMI Source Mask配置及Raw/Masked/Status独立读回 | CPU NMI路由配置与状态测试 | PLANNED |
| CPU_P1_002 | P1 | CPU NMI真实向量进入、Event Count和首次交付后自动屏蔽 | CPU NMI有界交付测试 | PLANNED |

## 3. Machine-readable Case Contract

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CPU_P1_001
case_name: CPU NMI路由配置与状态测试
report_feature: |-
  1. CPU NMI Source屏蔽配置
  2. CPU NMI Raw/Masked/Status状态
p_level: P1
feature_refs: [CPU_F_001, CPU_F_002]
method:
  inputs:
    - Source能力：从Runtime Capability读取支持的NMI Source Mask，不写入未发布位。
    - Mask组合：至少选择全屏蔽和一个目标Source允许两组配置。
  steps:
    - 能力读取：获取当前CPU实例支持的NMI Source Mask并保存基线。
    - 初始配置：写入全屏蔽配置并读取NMI_ROUTE.MASK。
    - 目标Source配置：仅清除一个支持位并重新读取Mask。
    - 状态采集：读取SOURCE_RAW、SOURCE_MASKED和STATUS三个独立端点。
    - 配置比较：比较实际Mask与两组输入，不用命令返回代替硬件读回。
    - 状态恢复：恢复全屏蔽配置并复读Mask。
  observations:
    - Mask硬件读回：读取NMI_ROUTE.MASK，期望与当前配置完全一致；证明路由配置到达硬件。
    - NMI状态端点：分别读取NMI_ROUTE.SOURCE_RAW、SOURCE_MASKED和STATUS；证明三类状态未被混合解释。
  pass_criteria:
    - Mask配置正确：两组NMI_ROUTE.MASK均与对应输入完全一致。
    - 状态字段独立：Raw、Masked和Status由不同稳定端点返回且保留原始值。
timeout: 5 s
cleanup: [恢复全部已发布NMI Source为屏蔽状态]
resources: {minimum_level: R0, full_coverage_level: R0, board: 无额外要求, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [NMI Route配置读回与状态快照]
failure_observations:
  - {key: expected_nmi_mask, label: 期望NMI Source Mask, source: oracle, role: expected, format: hex32}
  - {key: actual_nmi_mask, label: NMI_ROUTE.MASK实际值, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

<!-- ET_CASE_PLAN_BEGIN -->
```yaml
schema: et.case-plan.v1
implementation_status: PLANNED
case_id: CPU_P1_002
case_name: CPU NMI有界交付测试
report_feature: |-
  1. CPU NMI有界交付
p_level: P1
feature_refs: [CPU_F_003]
method:
  inputs:
    - NMI激励：使用能够产生真实Level NMI Source的Peer IP，不使用软件伪造Event Count。
    - 有界策略：由CPU Owner在首次向量交付后自动屏蔽全部已发布Source。
  steps:
    - 基线清理：全屏蔽NMI Source并清零NMI_DELIVERY.EVENT_COUNT。
    - 路由Arm：仅允许目标Source并读取Mask与Event Count基线。
    - 自然激励：由Peer IP产生一次真实NMI Source并等待NMI向量进入。
    - 交付观测：读取Event Count、SOURCE_RAW、SOURCE_MASKED和STATUS。
    - 有界性确认：读取NMI_ROUTE.MASK并确认首次交付后已自动恢复全屏蔽。
    - 协议存活确认：在Source保持有效期间执行一次有界Framework查询，确认线程未被NMI风暴饿死。
    - 状态恢复：停止并清理Peer Source，保持CPU NMI Source全屏蔽。
  observations:
    - NMI向量交付：读取NMI_DELIVERY.EVENT_COUNT，期望相对基线至少增加一次；证明真实进入NMI Handler。
    - 自动屏蔽状态：读取NMI_ROUTE.MASK，期望首次交付后等于支持Source全集；证明Level Source被有界隔离。
    - 协议存活状态：读取Framework响应，期望在有界时间内返回；证明NMI没有持续饿死线程。
  pass_criteria:
    - 真实交付发生：NMI_DELIVERY.EVENT_COUNT相对基线增加且Source状态可追溯。
    - 有界处理正确：首次交付后全部已发布Source被自动屏蔽。
    - 线程保持可用：自动屏蔽后Framework查询能够正常响应。
timeout: 5 s
cleanup: [停止Peer Source并恢复全部NMI Source为屏蔽状态]
resources: {minimum_level: R1, full_coverage_level: R1, board: 需要能够产生真实NMI的Peer IP, bench: 无额外要求}
backend: [FPGA, Silicon]
evidence: [NMI向量计数、路由Mask和协议存活证据]
failure_observations:
  - {key: expected_bounded_delivery, label: 期望首次NMI后自动屏蔽, source: oracle, role: expected, format: bool}
  - {key: actual_nmi_event_count, label: NMI_DELIVERY.EVENT_COUNT实际值, source: dut, role: actual, format: decimal}
  - {key: actual_nmi_mask, label: NMI_ROUTE.MASK实际值, source: dut, role: actual, format: hex32}
gap: [case_implementation_gap]
```
<!-- ET_CASE_PLAN_END -->

## 4. Chip Adaptation Summary

| Chip | Feature Platform Summary | Case Adaptation Summary | 当前结论 | Detail |
|---|---|---|---|---|
| ET6801 | ADAPTED=3 | IMPLEMENTATION_GAP=2 | NMI Mask、Raw/Masked/Status和有界交付已形成稳定接口；WDG Peer FPGA HIL已证明首次NMI后自动全屏蔽，CPU独立Formal Case仍待实现 | `ET6801_cpu.md` |

具体CPU实例、物理寄存器、Source位含义和访问Key由`<CHIP>_cpu.md`记录。公共Service、Wrap和PC Driver不得出现芯片名、地址或芯片专属Source位。

## 5. Common Gap / Evolution

- `cpu_nmi_source_identity_gap`：若芯片资料只发布匿名Source位，公共层只按能力Mask处理，不猜测外设到Source位的绑定。
- `cpu_case_implementation_gap`：CPU独立Formal Case尚未实现；现有WDG Case可作为真实Peer激励消费CPU Owner稳定接口，但不能替代未来CPU自身Case。
