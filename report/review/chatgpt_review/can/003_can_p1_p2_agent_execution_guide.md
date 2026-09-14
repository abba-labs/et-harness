# CAN P1/P2 极简重构：开发 Agent 执行指导与验收标准

> 工作仓库：`abba-labs/et-harness`  
> 工作分支：`chatgpt_review`，不得改为 `dsh_dev`、`codex_dev` 或另建临时开发分支。  
> 本文核对基线：`d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130`。执行时必须重新读取实时 HEAD。  
> 状态：**用户已确认设计方向；本文是实施指导，不是实现完成报告或硬件通过证明。**  
> 本次文档提交不修改 Case、Driver、Firmware、规则正文或报告程序。后续由本地 Agent 按本文分批实施、自检、验证、上传，再交由复核。

## 0. 先读这段：到底要做什么

把已在硬件上通过的 CAN P1/P2 测试，改成工程师能够直接阅读、直接维护的代码。每条 Case 只呈现：

```text
1）复位：选择一个实例，显式调用一次 can_handle.reset()
2）IP 配置：按原硬件顺序配置、施加刺激、启动和等待
3）获取并判断结果：读取真实硬件/ISR/对端结果，使用明确 assert 判定
```

Case 的设备操作只调用公开 Driver。普通 Driver 方法仅完成一个下级命令或必要的单 IP 操作，不执行测试场景、不生成 Golden、不判断 PASS/FAIL。`reset()` 是用户明确认可的固定生命周期组合例外：CRG 硬件复位、CAN 软件上下文清理、公共资源池复位。

目标是**每条 Case 正文尽量不超过 20 行，且一眼看懂硬件原理**。不能靠删断言、删参数、减少刺激、改变状态延续，或把整个测试搬入 Helper/Driver 来实现短代码。

用户说明当前 Case 已在硬件测试通过。必须将现有已通过流程当作行为基线，不能按 Agent 的偏好重新设计硬件测试。优化后是否保持结果，需要真实链路的软件验证和硬件复测，不能凭行数、语法或自写模型保证。

---

## 1. 需求优先级与旧方案处置

### 1.1 本任务的四项验收问题

1. **硬件思想是否改变？** 输入、寄存器配置顺序、触发方式、等待条件、取证点、恢复语义是否保持？
2. **Case 是否极简三段式？** 能否只看正文就知道复位什么、配置什么、测什么、怎样判定？
3. **是否尽量在 20 行以内？** 是否通过删除杂务达到，而不是压缩排版或藏测试？
4. **Case 与 Driver 是否都检查了？** 不能只让 Case 变短，却使 Driver 成为新的复杂 Case。

发生冲突时：硬件正确性和结论真实性 > 流程清楚 > 20 行目标。超过 20 行必须说明具体不可拆的硬件原因和已去除的杂务；这不是跳过优化的默认借口。

### 1.2 不再照抄的旧方案

本目录 `001_ecc_interrupt_chain_plan.md`、`002_ecc_case_preview.md` 是早期讨论稿，不是当前 Case 写法样板。其多实例循环、`partial(check/record)`、阶段字符串分派、Case 内清理列表等不再作为实施目标。

对话中的 V2 隐式 `_establish_baseline()` 方案也不采用。V3 的**显式 `can.reset()` 方向**被用户认可，但其中候选代码没有因此自动成为已合入、已编译或已通过硬件测试的实现。

本文不另立一套全仓规则。与 R200/R210 等现行规则的具体冲突，按第 14 节同步最小边界；不得把旧草稿、本文或用户的“极简”误读成关闭全部质量检查的许可。

---

## 2. 本批范围：先做 CAN P1/P2，不顺手重构整个系统

### 2.1 已核对的稳定 Case 集合

基线 `pc/et_test_platform/test_cases/can/case_registry.py` 中，本批包含 **19 个 P1、8 个 P2，共 27 个稳定 Case ID**；参数化执行数量不等于稳定 Case 数量。

```text
P1：001 002 003 004 005 006 007 008 009 010
    011 012 013 014 015 016 018 020 021
P2：001 002 003 004 005 007 008 010
```

完整 ID 前缀分别为 `can_p1_`、`can_p2_`。不得从连续编号猜测缺号，也不得把 PLAN 当成已实现 Case。本地执行时重新从注册表、函数定义和公共契约三方核对，记录实时差异。

### 2.2 必须纳入调查的文件

路径均以仓库根为起点。

| 类别 | 路径与责任 |
| --- | --- |
| P1 入口 | `pc/et_test_platform/test_cases/can/test_can_p1.py` |
| P1 分文件 | 同目录 `test_can_p1_format.py`、`test_can_p1_marker.py`、`test_can_p1_rates.py`、`test_can_p1_tdc.py`、`test_can_p1_timeout.py`、`test_can_p1_timestamp.py`、`test_can_p1_tsu.py` |
| P2 入口 | 同目录 `test_can_p2.py` |
| P2 分文件 | 同目录 `test_can_p2_dmu.py`、`test_can_p2_dmu_errors.py`、`test_can_p2_dmu_tsu.py`、`test_can_p2_ecc.py`、`test_can_p2_loopback.py`、`test_can_p2_watchdog.py` |
| Case 配套 | 同目录 `conftest.py`、`_support.py`、`case_registry.py` |
| PC Driver | `pc/et_test_platform/drivers/can/{driver,models,codec,contract,__init__}.py` |
| 复位依赖 | `pc/et_test_platform/drivers/crg/`、`pc/et_test_platform/drivers/resource/`；默认复用，不扩围重构 |
| CAN 固件 | `firmware/services/include/et_can_service.h`、`firmware/services/src/et_can_service.c` |
| 固件相邻边界 | `firmware/wrap/src/et_can_wrap.c`、`et_crg_wrap.c`、`et_resource_wrap.c`；`firmware/framework/src/et_irq_manager.c` |
| 契约与事实 | `test_case_doc/can/can.md`、对应芯片 CAN 文档、Capability、Execution Mapping、硬件连接文件 |
| 结果/执行链 | `scheduling/run_context.py`、`scheduling/test_registry.py`、`pytest_plugin.py`、`results/case_report.py`（均位于 `pc/et_test_platform/`） |

这是调查清单，不是允许一次性修改全部路径。每个实施批次的写入范围必须更小。本文依据已读取的代表性流程与接口作指导，**不宣称已经逐行完成所有 27 条 Case 的等价性审查**；逐条审查是下一位 Agent 的第一项交付。

### 2.3 明确不做

- 不继续开发 Agent Harness，不修改 `agent_harness/`。
- 不重写其他 IP，不修改 CAN P0/P3 测试正文；公共 CAN Driver 变更仍需软件兼容检查它们的调用。
- 不默认改底层 SDK、IRQ Manager、公共通信协议或共享资源池实现。
- 不在本轮顺手实现 TTCAN、AUX 时钟或其他未完成 PLAN。
- 不把全部 IP HIL 当成每次保存后的必跑任务。
- FAIL-only 备注属于单独的公共报告批次；不得在每个 CAN Case 里各写一份。

---

## 3. 可行性结论：可以减很多，但要区分两种变化

### 3.1 可以保持所选实例硬件语义的变化

可优先移除重复的前置复位、手写 JSON/备注、Case 内资源标志、嵌套清理列表、无关能力检查和重复超时传递；使用有名称的纯数据配置替代长位置参数；复用已经存在的单 IP 等待接口。

这类改动的证明方式是：**相同所选实例、相同输入，产生相同的关键硬件动作、状态转换和断言。** 不是要求每条日志的时间戳或字节完全相同。

### 3.2 用户已经认可、但必须如实记录的范围变化

多实例 IP 普通功能只测试明确选中的一个实例，不自动遍历全部 CAN。两个 ECC 源、DLC、滤波方式、FIFO 路径、速率等属于**功能参数**，不因“单实例”被删除。

旧 Case 中纯粹证明“CAN0 与 CAN1 隔离”的部分，在只测一个实例时无法继续作同样结论。必须在覆盖映射和契约中标明本批移出，不得通过固定一个实例继续报告“实例隔离已通过”。如果整条 Case 的唯一目的就是跨实例隔离，列为范围调整项，保留历史定义与证据，不能随意用无意义单实例检查替代。

增加通用软件上下文复位也会改变前置流程。它可增强独立性，但仍需核对其是否提前清除了本来要观察的状态；不能只称作“纯排版优化”。

---

## 4. 开始改代码前，先建立逐 Case 行为清单

### 4.1 固定真实基线

在用户指定工作区核对：

```powershell
git rev-parse --show-toplevel
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short
```

工作树有用户未提交变化时，不覆盖、不 reset、不强行切分支。先记录并区分变化。本文 SHA 只作调查锚点，不能覆盖后来上传的新实现。

按 `AGENTS.md -> PROJECT_COGNITION.yaml -> system-map.yaml -> module profile -> rule_owner_catalog.yaml` 路由。使用现有 `compile_task_context.py` 编译实际批次，不能手写一个 JSON 冒充通过。

### 4.2 每条 Case 必须填写的表

先形成 `004_can_p1_p2_behavior_inventory.md`，再做源码修改。至少一行对应一个稳定 Case；复杂 Case 对每个连续场景增加子行。

| 字段 | 必须记录的内容 |
| --- | --- |
| 定位 | Case ID、文件、函数、基线 SHA、原代码行数、实际参数节点 |
| 目的 | 一句话说明测什么；不能只写“验证 CAN” |
| 资源 | 所选 CAN、辅助 DMA/STIMER/路由/盒子、资源池、消息 RAM 的使用范围 |
| 输入 | 源、ID、DLC、负载、速率、时序、阈值、轮数、比较值及其独立来源 |
| 前置 | 硬件复位、软件上下文、旧捕获、时钟/引脚、消息 RAM 初态 |
| 硬件顺序 | 按时间顺序列出 Driver 动作及关键参数；标出 INIT/CCE、Enable/Mask、Arm/Trigger/Ack |
| 连续性 | 哪些阶段必须共享同一配置、计数、generation、RAM 内容或错误状态；哪些原本独立复位 |
| 观测 | 从硬件、真实 ISR、DMA 目标内存、Peer 读什么；哪个读操作有副作用 |
| 判据 | 原始每个决定性 assert、容差、精确计数、错误位；不能只列最后一条 |
| 清理 | 正常与异常退出动作、所有者、顺序、失败后能否继续 |
| 修改方案 | 删除什么、移到哪里、为何不改变关键硬件行为 |
| 范围差异 | 单实例后的覆盖变化；拆分前后 ID/参数/场景对应 |
| 验证 | 软件用例、故障用例、真实 HIL 证据路径；未执行明确标记 |

原源码与契约不一致时，先记录差异。现有代码已通过硬件测试，不能为了迎合某段旧文档直接改动已验证的硬件顺序；应查证规格/芯片事实后单独解决。

---

## 5. Case 应该怎么写

### 5.1 正文只保留这些内容

- 选择一个 Driver 句柄，如 `can_handle = can0`。
- 第一次测试性配置之前调用 `can_handle.reset()`。
- 用明确的配置对象/具名参数调用公开 Driver，按原顺序产生刺激和等待。
- 读回真实值，用 `assert` 明确比较；必要的硬件相关循环仍可保留。

不放 `TargetClient`、Wire 编解码、`partial(check/record)`、`cleanup_actions()`、资源所有权布尔变量、文件目录拼装、JSON、报告备注或通用上下文管理。

“IP 配置”这一段包含该测试需要的激励、启动和等待，不是把 Force/发送/DMA Start 从测试删除。三段式是阅读结构，不是强制所有硬件观测只能在最后一次读取；负向窗口或破坏性操作前的中间观测必须保留。

### 5.2 目标样式，不是可直接覆盖原完整功能的补丁

以下展示单实例 ECC 一次投递。`reset()`、`CONTEXT_RESET` 和句柄定义必须先落地并通过第 16 节验证。该短例不替代屏蔽持续观察、选择性 Clear、重复投递及退出语义的全部覆盖。

```python
@pytest.mark.parametrize("source", (CanEccSource.CORRECTED, CanEccSource.UNCORRECTED))
def test_can_p2_003_ecc_interrupt_chain(can0, source):
    # 1）复位
    can_handle = can0
    can_handle.reset()

    # 2）IP 配置与激励
    can_handle.ecc_capture_start(source)
    can_handle.ecc_force(source)
    can_handle.ecc_mask_set(source, False)

    # 3）获取并判断结果
    event = can_handle.wait_ecc_event(0, timeout_s=5.0)
    state = can_handle.ecc_snapshot_get()
    assert event.event_count == 1
    assert event.instance_id == can_handle.instance_id
    assert event.latched_events == source
    assert event.raw_status == event.masked_status == source
    assert event.fault_flags == event.unexpected_count == event.overflow_count == 0
    assert (state.raw, state.status, state.enabled) == (source, CanEccSource.NONE, source)
    assert state.masked & source == source
```

保持硬件配置读回与 ISR 记录的区别。这里末尾源被重新屏蔽，是现有 ECC ISR 的行为，不是 Case 自己写回一个预期值再宣称正确。

### 5.3 20 行怎样统计，怎样避免形式主义

统计函数正文中实际代码的**物理行数**，排除空行、纯注释、装饰器和函数签名；多行调用、配置字面量按实际占用代码行计入。另报函数总跨度，避免统计口径掩盖阅读负担。

- 不用分号、巨长行、嵌套三元表达式或 `assert (...)` 巨元组堆积来刷指标。
- 可把固定测试向量、完整配置常量、无 I/O 的确定性数据生成放在同一功能文件附近；名字要能说明硬件意义。
- 不把改变时序、启动、Force、取证、比较的执行代码藏进常量生成器、Fixture、装饰器或 `run_scenario()`。
- 不允许为了短而新增 `driver.test_xxx()`、`driver.check_xxx()`、`run_and_assert()`。
- 普通 Case 力争 <=20 行；不可拆的复杂连续算法提交具体超长说明。不要把任何超过 20 行都解释成合理，也不要为了全绿删测。

### 5.4 哪些测试可以拆，哪些不能

相互独立、原本各自建立初态的 Feature 可以拆成多个短 Case；同一流程仅参数不同使用参数化。拆分必须同步稳定 ID、注册表、SPEC、参数计数、报告映射和覆盖记录。

**同一 generation 重复投递、同一 FIFO 状态下的 Mask/Clear、故障后的恢复、March 的跨地址次序，不得随意拆成各自 reset 的测试。** 可以先在原 Case 内去除记录/清理杂务；仍超长时保留清楚的必要流程并说明，不强拆。

原 ID 若保留，不得悄悄换成只覆盖一个小片段的定义却沿用原完整覆盖结论。稳定 ID 不允许由多个测试函数重复实现；新增 ID 需查 SPEC、PLAN、源码和注册表是否已占用。基线 P2_011/012 已有计划用途，不可抢用。

---

## 6. Driver 怎么保持极简

### 6.1 普通命令接口

推荐形状：合法的稳定参数 -> 本 IP 编码 -> 下级请求 -> 解码真实返回。

```python
# 现有直接命令的形状示例；不包含 Case 判据。
def ecc_force(self, sources, *, timeout_s=None):
    self._request(CanCommand.ECC_FORCE, (codec.ecc_sources(sources),), timeout_s=timeout_s)
```

不新增 Case 专用策略、默认纠错、自动切实例、自动放宽参数、自动重启后继续测试、重复刺激或 PASS 标志。Driver 不导入 `test_cases`、pytest、Case Helper、报告模板或 Golden。

保留同一 `_target` 连接，构造对象不得偷偷打开另一连接。旧公共方法名称、参数、返回数据模型、Wire 编号和异常语义默认兼容；P0/P3 和其他调用者不能因本轮整理失效。

### 6.2 允许保留的必要逻辑，不是“多余保护”

- Wire 长度、实例字段、保留位、类型范围和响应匹配：保留在 Codec/通信边界，不复制到每条 Case。
- 有限超时、单 IP 完成状态等待、分包：保留在已有正确层。不是把所有等待改成固定 Sleep，也不是删掉检查返回成功。
- 实际读回不能用 Driver 缓存的配置值或请求值代替。
- 不自动重发非幂等 Force、读清、FIFO Ack、入队等动作。
- 对“硬件是否拒绝写入”的测试，不可由 PC 参数保护提前拒绝请求，造成硬件路径根本没执行。

`wait_ecc_event()`、`wait_tx_complete()` 等已有方法可以保留：只读状态并有界等待，返回事实或通信/超时异常，不拥有最后的测试断言。不得改成驱动自己顺带 Force、初始化、检查整条 Case 或重试到通过。

### 6.3 reset 是唯一明确的跨 IP 固定组合例外

用户允许的目标形状：

```python
# 新增到现有 CanDriver；配套固件/契约实现完成前不能发布使用。
def reset(self) -> None:
    CrgDriver(self._target).reset(CrgPeripheral.CAN, instance=self.instance_id)
    self._request(CanCommand.CONTEXT_RESET)
    ResourceDriver(self._target).reset()
```

它只恢复共同初态，不接受本条 Case 的 source、bitrate、filter、payload、Expected 等业务参数。不得发展成 `reset_and_configure_and_test()`。

普通 CAN 方法仍不能调用 CRG/Resource/其他 IP。依赖检查只给这个真实需要的生命周期入口准确限定，不能改成“所有 Driver 可任意互调”。

---

## 7. reset 必须真实有效：不能只写一个名字

### 7.1 三个复位对象不能混淆

| 对象 | 实际 Owner | 必须做到 |
| --- | --- | --- |
| 所选 CAN 的硬件寄存器 | CRG Driver/Service/Wrap | 复用现有 `CRG_resetPeripheral` 路径；不顺带复位控制 UART、GPIO 域或其他 CAN |
| CAN 的软件上下文和 IRQ 绑定 | 所选 CAN Service 与现有 IRQ Manager | 普通 IRQ/ECC/DMU 的运行记录、回调归属、计数、故障记录清理；正确释放真实绑定 |
| 公共 Resource Pool | Resource Service/Wrap | 清描述符、内存和使用位置，更新句柄代次；旧句柄不应在本次分配后错误命中 |

**资源池是公共池，不是 CAN 私有池。CAN Message RAM 是另一套内存，不等于 Resource Pool。** 不可以把“整个 CAN 寄存器已复位”进一步推导为消息 RAM 内容、DMA 状态、外部盒子缓存或全局共享变量都已清空。

### 7.2 删除的是重复基线写，不是测试步骤

按用户确认的目标：CRG 已复位所选 CAN 的寄存器，不能再无条件执行下列命令当成每条 Case 的基线：

```python
can.ecc_mask_set(ALL, True)
can.ecc_enable_set(ALL, False)
can.ecc_clear(ALL)
```

但 Case 正在测试 Mask、Enable、Clear 时，它们仍是必需刺激；必须显式保留。现有 `ecc_capture_start()` 自身有清旧所选源、建立事件代、绑定、使能且保持屏蔽的公开语义，本轮不要为了少几次写操作把该接口顺便重定义。

删除“全源屏蔽”以后，不能沿用人为制造的 `masked == ALL` 判据。根据被测目的，检查所选源相关位或芯片真正的复位值。既不能写回期待值制造通过，也不能把决定性比较随意改弱；在行为清单解释判据与基线的对应变化。

### 7.3 CONTEXT_RESET 的实现要求

基线中该命令还不存在。实施时必须连同 PC Contract、Firmware 命令表、分派、文档和测试一起交付。

1. 只操作本 `et_can_service_t` 的运行状态；保留实例 ID、descriptor、Manager 指针、固定 priority 等长期依赖。
2. 处理三套记录：`irq_event[]`、`irq_line_events[]`、`ecc_event[]`、`dmu_event[]`，以及 watched/line selection/bound 标志、运行期 route。
3. 通过现有 IRQ Manager 释放本 Service 的真实绑定，包括失败绑定留下的清理记录；不能仅依据本地 `bound_*` 为零就认为没有绑定。
4. 不 `memset` 整个 Service，不重跑启动时 `et_can_service_init()`，不清空全局 IRQ Manager，也不注销其他 Service 的共享线路绑定。
5. CRG 复位不负责 CPU 中断控制器 pending、向量注册或 Manager 表。必须复用 Owner 的解绑动作；共用物理线只在最后使用者退出时进行物理清理。
6. 复用已有短临界区并恢复原中断状态；不在长时间串口操作或轮询期间关闭全局中断。
7. 软件计数/故障归零与 generation 更新分开。保留原先溢出、代次、空实例哨兵语义，不把 generation 简单清零冒充全新记录。
8. 解绑失败或上下文复位失败时返回真实错误，不抹掉能定位失败的状态；PC 不继续 `ResourceDriver.reset()`，更不继续 Case 配置。
9. CRG 与上下文清理之间仍可能有已挂起 ISR。必须检查目标硬件复位后中断源确已静默，以及共享中断/回调执行时不会形成错误访问；不能用“Case 串行”代替该分析。
10. 不为替代已确认的硬件复位再发送一串全源 mask/disable/clear。若芯片资料或实测证明某个域不在该复位范围，列成明确的芯片适配差异，不能悄悄掩盖或声称全复位已被证实。

### 7.4 协议配套清单

基线现有 CAN 命令到 97。98 仅是该基线下的候选新增编号，实施时重新确认未被后续提交占用。

- PC `CanCommand`、`REQUEST_WORDS`、`RESPONSE_WORDS` 与固件 enum、COUNT、输入/输出字数一致；旧编号不挪动。
- 请求仍包含既有 CAN instance 前缀；零额外命令参数不等于整个 ET-Frame 无负载。
- 成功响应空命令体；错误使用现有明确状态，不制造虚假成功。
- `CONTEXT_RESET` 是写动作，不加入只读自动重试表。
- 在功能族分派前正确路由新命令，避免落入别的默认 handler。
- 原始请求/响应 Golden Vector、非法实例/长度、失败不上报成功均要测试。
- 新 PC 不能配旧固件。校验 firmware build、实际支持命令与服务发现；不支持时报告版本/集成错误，不跳过复位继续跑。

### 7.5 共同前置的适用条件

`can.reset()` 可作为所有 CAN Case 的共同基础，但不是每个组合 Case 的全部初始化。

- 仅 CAN：先存前次需要保留的证据，再按固定三步 reset。
- CAN+DMA/DMU：外部 DMA 仍会访问公共池时必须先停相应 DMA、处理通道和请求路由，再执行 CAN reset。DMU capture stop 不等于 DMA stop。
- CAN+STIMER：停止本次使用的计数参考及其活动路径；CAN reset 不替它恢复时钟/状态。
- 外部 CAN 盒子：先停持续刺激；盒子接收缓存通过盒子 Driver 清理，不能期待 DUT reset 处理。
- 进程被强杀或首次目标状态未知：使用已有平台恢复流程建立已知状态；仅靠清资源池不能恢复正在运行的未知 DMA。

组合场景需要显式、短小的支撑 IP Driver 调用，不为隐藏两行 `dma.stop()` 新建万能“依赖恢复管理器”。这些支撑动作属于第 1 段复位/准备，不破坏三段式。

### 7.6 复位本身是测试内容时

Case 开始的 `can.reset()` 是隔离。测试中途验证硬件 CRG 复位时仍调用裸 `crg.reset(...)`，随后读回被测状态；不能用复合 reset 清软件/资源来掩盖硬件复位的实际表现。

同代重复中断、连续 FIFO、RAM March、清除与恢复测试的中间阶段，不允许因为“三段式”再插入 reset。

---

## 8. 单实例如何实现，而不是只改个变量名

`can_handle = can0` 中，`can0` 必须是真实的公开 `CanDriver` 对象，绑定当前已打开的 TargetClient 和逻辑实例 0。Fixture 只负责连接、实例/映射核对、构造、被动记录和登记收尾，不在返回前再悄悄执行一次 reset。

- 修改为 `can1` 时，同时修改函数所需 Fixture/句柄来源，且它实际绑定逻辑实例 1；不能只改局部别名。
- 当前芯片没有所选实例、Runtime Service 缺失、外部接线不匹配时明确报告配置问题，不能自动回退 CAN0。
- 实例 ID 不等于寄存器地址。基址、IRQn、时钟、GPIO、DMA request 和 Message RAM 区域仍按选定实例从芯片/板级事实解析。
- 外部对端和片内 DMA 是必要配测资源，不是额外被测 CAN 实例；“只测一个 CAN”不能删掉对端 ACK/接收或 DMA 路径。
- 普通 Case 不能依赖 `can_all_supports` 并在内部轮转 target。原全实例专用 Fixture 不要求全仓删除，P0 等本批外使用者保持兼容。
- 本批形成的单实例规则适用于后续 IP 开发方向，但本次不自动批量修改其他 IP。

---

## 9. CAN P1/P2 特别容易被“简化坏”的地方

| 功能/定位 | 可以整理的部分 | 绝对不能偷偷改变的硬件含义 |
| --- | --- | --- |
| Classic/FD、DLC、ID、滤波、FIFO、Marker | 固定配置用具名不可变数据，报告杂务移出 | 两种 Pattern、DLC 与实际长度区别、标准/扩展格式、接收/拒绝目标、逐字节比较、TX 完成和 Lost/Error |
| `test_can_p1_016_message_ram_march` | 区域/chunk 计算是纯数据，可独立；复位/记录杂务可去重 | 固定模式先整区写再整区读；March 六阶段；每地址读后立即写；批间与批内降序一致；全范围不是抽样；结束后不额外 reset 就重建回环的恢复证明 |
| `test_can_p1_014_timeout_sources` | 不用 stage 字符串隐藏动作；固定输入清楚化 | 四个计数源、自然到期不是 Force；非目标 FIFO 为空；启用/禁用的连续状态；目标 FIFO 非空时的禁止计数对照；至少两倍周期观察 |
| Timestamp/TSU | 单次读回与纯换算分开，格式具名化 | 内部时间戳与 TSU 不混；读清寄存器不补读；Marker 宽度、指针、New/Lost、回绕、捕获源和时间窗保持 |
| Rates/TDC/外部回环 | 统一构造，不重复能力查询和日志 | 实际外部线路、真实 Peer、双方速率、BRS/FD、数据长度与方向；不能用内部回环冒充外部路径 |
| `CAN_P2_003` ECC | 单实例、重复基线去掉、独立功能合理拆分 | Force ECC 中断不等于真实 RAM 纠错；屏蔽观察窗口、目标源选择性清除、同代重复投递及退出读回；不把 Raw 当真实 ISR |
| `CAN_P2_001/002` DMU 与 DMA | DMA 配置数据及缓冲区表达清楚，统一记录 | RX DMA 先于 TX；真正由 DMA 访问窗口；不改 CPU 拷贝；元素头/有效负载/传输总长度区别；接口与路由；FIFO/Ack/计数推进；负载预填与完整读回 |
| DMU errors/DMU+TSU | 错误刺激与观测线性展开 | 故意非法方向/窗口访问、首个读清错误、独立 DMU 回调；不能被 Driver 参数保护挡掉，也不能重试清掉现场 |
| `test_can_p2_010_ram_watchdog` | 公共数据、记录与固定恢复收拢 | 门限 1、关闭、恢复三个阶段；8/8/1 帧刺激；100ms 窗口和 STIMER 证据；真实 WDI+ISR，禁止 Force 冒充 RAM 应答触发；没有触发不能改成 SKIP/PASS |

上述细节以已读取源码为依据。其余 P1/P2 同样必须逐函数补齐行为表，不能仅按文件头注释判定等价。

**负向观察不是“没读到就算通过”。** 必须真的覆盖规定时间窗，保存累计回调/故障与必要的硬件事实。通信超时、未完成窗口或捕获链未工作不能算“无中断”。若用单 IP 观察接口收拢轮询，该接口只能返回采样/持续时间事实，不得内置 Case 的无中断 PASS 结论。

---

## 10. 配置与等待的简化边界

### 10.1 不把复杂配置偷偷变成新默认值

允许把长 `CanOptions(...)`、RAM layout 或时序输入变成具名常量/纯数据函数；必须保留每个非默认关键字段、所选实例对应值以及原函数调用顺序。

不要用新的“通用默认配置”覆盖原来刻意不同的 DAR、MON、CCE、FD、BRS、过滤策略、IRQ mask、FIFO 深度或 DMA burst。将配置机械变成位置参数更短但更难读，不是优化。

不为压缩 20 行新增一个包揽 Timing/Options/RAM/Filter/Start/Wait 的 `configure_case()`。确需新的完整单 IP 配置 API，必须证明它是稳定硬件动作而不是这条 Case 的脚本，单独评审命令展开顺序；本批优先复用已验证 API。

### 10.2 超时不反复手传，但原预算不能偷偷改变

普通一次请求使用现有默认超时；Case 中保留有硬件意义的 `wait_...(..., timeout_s=...)`。Driver 内用现有有界等待，不加多套重试/锁/状态机。

若原契约是“一条路径总共 5s”，删除 `remaining()` 后让十个命令各得 5s，会改变超时语义。必须使用已有可复用预算方式，或将必要的总预算保留在正确层，并在行为表核对总耗时与超时点。不能只是省略参数就宣称等价。

必要预算无法在不增加抽象的前提下移出 Case 时，宁可明确少量预算代码或说明超长原因，不设计万能上下文注入/动态代理引擎。120s 的 March、5s 的普通路径、100ms 的负向窗口不是可以合并的同一数字。

---

## 11. 记录和清理移出正文，不能随之消失

### 11.1 记录

复用现有结果链，被动保存已经返回的真实值。Case 不拼 JSON、路径和备注；Driver 不依赖报告层、不算 PASS。

记录适配必须位于测试运行/记录边界，优先复用已有机制。确需适配时限定明确接口，不增加全方法反射、动态 monkeypatch 或第二套结果总线。

- 不为了记录再发一次读命令，特别是读清、出队或带副作用的读取。
- 不只记录函数最终返回，丢掉轮询中的首个故障、负向窗口或关键中间状态。
- reset/teardown 改现场之前保留已获得的证据。失败前未获得的值写未观测，不填 0/False 冒充硬件值。
- 原来源、endpoint、实例、源、参数、错误、generation 和附件关联继续可追溯。
- 核对 R130 的必需 Observation 与报告模板；通过断言但变成 EVIDENCE_MISSING 不是优化成功。
- 记录失效不能默默 PASS，也不能让记录异常覆盖更早的硬件失败。

### 11.2 清理

Case 不写 `with case_cleanup_scope(...)` 或清理 lambda 列表。通过现有 pytest/运行层在第一次设备修改前登记固定收尾，调用公开 Driver。正常完成、断言失败、请求超时、初始化部分失败都必须进入适当收尾路径。

收尾只停止本条已启动的活动、释放其所有权。下一条起始 reset 建立新的共同基线，普通成功路径不再无条件“退出整池 reset + 下一条再 reset”。最后一条也需要停止活动，不能因为没有下一条就留下 IRQ/DMA/外部发送。

若“停止/解绑/Clear 的结果”本身属于被测 Feature，则该动作和判据必须在 Case 正文显式保留；异常兜底清理不能替代测试该功能。

收尾失败保留原错误和清理错误，并阻止依赖该硬件/公共池的后续测试在脏状态下继续。重用已有错误聚合机制，不能吞异常或把 ERROR 改成 DUT FAIL 来简化报告。

---

## 12. 报告备注只写 FAIL：单独实施，不侵入 CAN Case

保留用户此前确认的需求：面向人的备注只展示失败项，PASS 备注为空；原始日志、Observation、状态和错误仍保存。

基线入口为 `pc/et_test_platform/results/case_report.py` 中 `_report_remark()`、`_evidence_remark()`、`_human_report_note()` 及其调用链。不是在每个 Case 中 `if failed: record(...)`。

- 使用最终报告状态，不改变状态聚合、覆盖计数或证据完整性判断。
- 同一稳定 Case 混合 PASS/FAIL 参数时，备注仅取失败参数，不汇总通过参数污染失败原因。
- FAIL 备注至少能定位 Case/参数/实例、失败步骤或断言、实际与预期（已获得时）、原始证据位置。缺信息如实说明，不能格式化失败把原错误盖住。
- 其他非 PASS 状态不能当 PASS，也不能假装是 DUT FAIL。若备注字段严格仅 FAIL，则运行异常/未执行/证据不足的原因放入现有详情/错误来源，必须仍可见、可定位。
- 报告渲染不能为提取备注重新读取硬件；也不能因为 PASS 不显示备注就跳过其证据校验。
- 报告单元测试覆盖 PASS、FAIL、混合参数、全部 SKIP、RUN_ERROR、EVIDENCE_MISSING、NOT_SELECTED、NOT_EXECUTED 及字段缺失。

这是公共报告改动，单独 Task Context、独立提交，不能借 CAN 优化随意改变所有 IP 的结果判定。

---

## 13. 哪些保护删，哪些保留：每项都要有去向

| 现状 | 处理 |
| --- | --- |
| CRG 后又全源 Mask/Disable/Clear，只为建立人为初值 | 核对复位域/默认值后删除；测试 Mask/Clear 的动作保留 |
| 同一基线重复资源池 reset | 合并到一次固定 reset；先停止所有访问者 |
| 每 Case 定义所有权布尔值、清理生成器 | 移出 Case，复用运行收尾和 Owner 的真实状态，不让调用者重建状态机 |
| 反复检查同一固定能力或连接信息 | 在已验证的连接/固件生命周期内复用；重连/固件变化时失效；能力本身是测试对象时不删 |
| Case 自己重复 Driver 轮询 | 复用已有单 IP 等待；不能新增等待后自动重试刺激 |
| 多层同一参数校验 | 明确可信边界与 Owner，避免同层重复；PC 早期诊断不能代替固件入口边界校验 |
| 不需要的并发锁、租约、调度机制 | 只有找到实际调用与证明串行单拥有者后才删除；不能因目录名字像 scheduling 就整块删 |
| ISR/主循环共享数据的短临界区 | 保留；Case 串行不等于硬件中断同步 |
| 帧匹配、长度/保留位校验、有限超时 | 保留在底层，不能去掉后让坏数据变成功 |
| 真实旧错误和失败证据 | 保存后再恢复；不能用 reset 擦掉错误后续跑宣称通过 |

输出“删除/合并/保留”清单，并写明原位置、原因、Owner 和验证方法。不得笼统写“已去掉多余保护”。

---

## 14. 规则与目录必须一起理顺，但不另造体系

当前 R200 限制 Driver 跨 IP 调用，R210 对前置复位显式位置及生命周期写法有旧约束。本任务用户已明确认可：单实例、Case 显式 `reset()`、极简正文与薄 Driver。落地时只同步这些**准确命中的差异**。

1. R200：限定 `CanDriver.reset()` 的固定 CRG/CAN Context/Resource 组合例外；普通方法继续单 IP。
2. R210：一次公开 Driver reset 可代表前置隔离；固定异常收尾、被动记录不应占用 Case 正文；测试本身的动作/断言仍可见。
3. 单实例：允许逻辑句柄选择；不允许在公共 Case 写芯片物理地址、IRQn、GPIO 编码。移除范围之外的跨实例覆盖必须记账。
4. 原 Checker 若误判新边界，增加准确的正反测试并修改相应判断；不能删除检查器、全文件 allowlist、关闭断言/证据规则来放行。
5. Task Context 的 allowed/protected 冲突不能靠手改 runtime JSON 或选一个更宽模块绕过。对必要模块/验证路径按现有路由单独声明；超出本任务范围的修改单独说明，不扩散其他 IP。

生产代码尽量留在原目录。可按硬件功能重排 Driver 方法（实例/复位、配置、TX/RX、IRQ、ECC、DMU、计时/RAM、私有请求），但保留稳定公开入口和外部导入。不要为目录整齐把每个小方法拆文件，也不要新建大量 Context/Manager/Registry。

---

## 15. 实施顺序：一次做小批，不一次性改完再看

### 阶段 A：只读盘点

完成第 4 节行为清单、Case/Driver 调用图、27 个稳定 ID 的参数与覆盖清点、规则冲突清单。先给出每条“直接瘦身/可独立拆分/必须连续/单实例范围调整”的分类。

### 阶段 B：先完成真实 reset 和句柄

交付 `CanDriver.reset()`、固件 CONTEXT_RESET、完整 Wire 配套、所选实例构造和运行层收尾。先做真实实现的软件测试和隔离验证，不允许 Case 已调用一个不存在的接口。

该阶段不改正常 ECC、TX/RX、Timing、DMA 的原功能命令语义，不重写 SDK。复位未验证成功就停止扩大 Case 改动。

### 阶段 C：先做 ECC 小批样板

以 `CAN_P2_003` 为起点。单实例下保留源矩阵，明确拆分可独立目的以及必须同代连续的目的。配套完整定义、注册、SPEC、取证和收尾全部可追溯；不能只提交 15 行正文。

先完成第 16、17 节自检；存在未定义 Fixture、失配签名、错误覆盖或脏状态时修根因，不继续改其他 Case。

### 阶段 D：逐功能完成 P1/P2

先普通配置/数据路径，再滤波/FIFO/Marker，再时间戳/Timeout/TSU 与外部路径，最后 DMA/DMU、RAM March、Watchdog 等连续或多资源流程。最终必须逐条说明 27 个原 ID 的归宿，不能只改两个文件就声称 P1/P2 完成。

每个批次记录变更、命令轨迹差异、Case 行数、Driver 变化、软件验证结果；有硬件条件和授权时按相同选定实例复测。不得把一条 Case 的成功推广到尚未跑的其他 Case。

### 阶段 E：单独处理 FAIL-only 备注

按第 12 节处理。公共报告回归与 CAN 功能回归分别记录，不能通过删 PASS 证据绕过报告问题。

### 阶段 F：完成后的自主复核与上传

先用第 17 节四张检查表逐项自审，再提交。每个逻辑批次独立提交，不强推、不重写用户历史。上传后给出精确 SHA 和验证范围；CI 只认该 SHA，不拿上一次成功结果代替。

---

## 16. 怎么证明是真优化，而不是只让模型测试通过

### 16.1 验证层级必须分开报告

| 层级 | 必须验证 | 能证明什么 / 不能证明什么 |
| --- | --- | --- |
| 静态/收集 | 真仓库 imports、Fixture、签名、标记、注册、SPEC、命令字数 | 能发现接入错误；不能证明硬件工作 |
| 实际 Driver 链 | 使用真实 CanDriver/Codec/TargetClient，替换最底层 Transport 或用现有测试后端 | 能证明命令及解码路径；不能证明 MCU 外设表现 |
| 固件原生/编译 | 实际 Service/Manager/Wrap 适当边界，编译真实 C；工具链与目标固件构建 | 能发现 C 实现和状态路径错误；不能冒充上板 |
| 故障测试 | 有意制造错误值、超时、绑定残留、清理失败 | 证明失败能被检出、不被掩盖；不是正常硬件回归 |
| 真实 HIL | 相同板卡/固件来源/映射/实例/输入，比较旧、新流程 | 才是修改后硬件行为与结果的证据 |

测试可以使用底层替身，但不能把待测 Driver 的所有方法替换成“总是返回期待值”，然后以通过数量证明实际链路正确。自写模型和候选代码共享同一错误假设时也会一起通过。

### 16.2 命令轨迹对照

在不引入额外硬件读取的情况下，记录已有请求的顺序、service/instance/command、关键参数、返回状态；区分准备、测试、取证、收尾。

对照至少包括：实例、配置字段、读写顺序、Force/发送次数、Capture-before-trigger、RX-before-TX、Ack 时机、DMA 长度、数据区域、恢复时点和等待预算。

允许差异必须逐条列白名单并说明：例如去掉重复 reset、上下文清理归并、日志重构、移出其他实例。不能用“都是 configure 类命令”忽略内部不同字段，也不能按最终 PASS 就认定整个顺序等价。

不要在为保证时序而设置的负向窗内增加大量同步日志；也不要删除必要等待或改变关键请求间隔。记录开销、串口速率和原有时间预算需要核对。

### 16.3 reset 专项回归

必须覆盖：

- 正常初态与重复 reset；没有注册回调时也成功，不要求 Case 预先 Capture。
- 所选实例普通 IRQ/ECC/DMU 记录存在、真实绑定存在时清理正确。
- CRG reset 本身不清软件状态；不能用测试替身把两者合并而漏掉 CONTEXT_RESET。
- 回调绑定失败后残留、解绑失败、中途错误：不报告 reset 成功、不继续配置、不清仍有访问风险的公共池。
- 其他 Service 共用物理 IRQ 时，选定 CAN 的清理不破坏其他 Owner。
- generation、空实例哨兵与溢出语义；不要声称有限位宽代次永不回绕。
- 资源池有旧描述符和旧数据，重置后分配有效、旧句柄在本次代次失效；资源池没有被调两遍。
- 不写 CAN 复位域以外的无关配置，不把整块消息 RAM 额外清空。
- 底层错误向上透传，当前采集失败与 teardown 失败都保留。

### 16.4 Case 故障检出回归

至少令以下错误各自导致非 PASS，并保留来源：回调不发生、回调多一次、源错误、实例错误、Raw/Status 错误、清错源、generation 异常、窗口未完成、Peer 少帧/错字节、DMA 不完成、断言后收尾失败。

对负向测试，应另外证明捕获链在同一配置下确实能观察正向刺激，不能把“捕获没启动”误判为“Mask 正确”。

### 16.5 本地验证入口

先执行当前 Task Context 给出的最小专项验证，再在逻辑批次完成时运行一次总软件门禁。以下命令来自基线模块路由；执行前确认本地脚本版本和适用参数：

```powershell
python tools/governance/compile_task_context.py check
python tools/governance/compile_task_context.py scope-check
python tools/quality/check_pc_code_rules.py --root . pc/et_test_platform/drivers/can
python tools/quality/check_pc_code_rules.py --root . pc/et_test_platform/test_cases/can
python tools/quality/check_case_orchestration_rules.py --root . pc/et_test_platform/test_cases/can
python tools/quality/validate_case_docs.py test_case_doc/can/can.md
python tools/quality/check_case_spec_implementation.py
python -m pytest --collect-only -q pc/et_test_platform/test_cases/can
python tools/validate_pc.py
git diff --check
git status --short
```

还需运行实际修改的 Driver、固件 Contract/Native、结果与注册专项测试，按本地真实路径选择，不虚构测试文件名。`--collect-only` 不操作设备。真实 HIL 使用现有 `tools/runner/run_ip_tests.py --ip can --include-case <实际ID>` 路由及 runbook 要求的完整配置/人工硬件授权，不能裸 pytest 冒充完整运行与证据发布。

没有硬件条件时允许提交待验证代码和自检结果，但必须写 `HIL_NOT_EXECUTED`；不能写“已保证硬件不受影响”。

---

## 17. 开发 Agent 完工后必须自己检查的四张表

### A. 硬件思想与流程

- [ ] 每个原 ID/参数场景都映射到新实现或明确的单实例范围调整，没有失踪。
- [ ] 所选实例不变；输入、Pattern、ID、DLC、速率、阈值、长度、轮数和容差保持。
- [ ] INIT/CCE、RAM/Filter、Capture/Enable/Mask、Trigger、Wait、Read、Ack 的关键顺序逐条核对。
- [ ] 未用软件拦截代替硬件保护测试，未用 Force 代替自然到期或真实 DMA/总线刺激。
- [ ] 持续状态、同代计数、故障后恢复、March 顺序未被拆分/reset 破坏。
- [ ] 真实读回和独立 Expected 保留，未把缓存/请求值当硬件事实。
- [ ] 基线复位与被测复位分开；删除重复写后期望值仍正确。

### B. Case 极简与结构

- [ ] 第一段是明确所选句柄与 reset；必要的支撑设备先停止。
- [ ] 第二段直接可读的 IP 配置/激励/等待；第三段真实获取与明确判定。
- [ ] 正文没有日志/报告/清理生成器、`partial`、通用上下文或 Wire 操作。
- [ ] 不遍历全部被测实例；功能参数矩阵仍保留。
- [ ] 每函数统计代码行数；>20 行列出不可拆理由与已优化部分。
- [ ] 没有分号压行、超长表达式、把测试流程藏进 Helper/装饰器或 Driver。
- [ ] 每个新增名字、Fixture、导入和接口都有完整定义与真实仓库收集结果。

### C. Driver 与固件

- [ ] 普通 Driver 方法只做单动作/命令或必要有界等待，最终判断留在 Case。
- [ ] reset 只做固定生命周期组合，不携带 Case 参数、不配置/触发测试。
- [ ] 旧公共 API、Wire 编号、错误语义、P0/P3 调用兼容。
- [ ] CONTEXT_RESET 真正清理所选 Service 的绑定和记录，不误清全局 Manager。
- [ ] Resource reset 在访问者停下后执行；前一步失败即停止，不反复/自动重试清现场。
- [ ] 无 Driver -> Case/pytest/Golden/报告反向依赖，无自动换实例或补传。
- [ ] 请求长度/响应匹配/有界超时等必要边界还在正确层，没有重复扩散到 Case。

### D. 结果、验证与交付

- [ ] PASS 原始证据完整；FAIL 备注只来自失败参数；其他错误仍有详情且不冒充芯片 FAIL。
- [ ] 初始化失败、Case 失败、收尾失败及二者同时失败都有真实测试。
- [ ] 静态、真实 Python 链、固件编译/Native、自写模型、HIL 的结果分开。
- [ ] 软件门禁与精确 SHA 的 CI 状态明确，未执行项不填 PASS。
- [ ] 已提供修改前后关键命令差异与剩余风险，而不只是“测试通过”。
- [ ] 用户能从提交 SHA、文件路径和证据记录重现本次验证。

任一涉及硬件思想、被测路径或虚假 PASS 的项目不满足，停止推广到其他 Case，先修根因。不能以平均行数下降或总通过率好看替代这些检查。

---

## 18. 下一位 Agent 必须交付的文件和汇报格式

在本目录继续形成以下材料，不重复建平行总规则库：

1. `004_can_p1_p2_behavior_inventory.md`：27 个原 Case、功能参数、连续场景与覆盖变化的完整清单。
2. `005_can_p1_p2_self_review.md`：逐条 Case/Driver 的修改前后路径、代码行数、关键动作差异、四项自检结论、具体问题与修复结果。
3. `006_can_p1_p2_validation_summary.md`：源码 SHA、板卡/所选实例/固件 build、运行入口、实际软件/HIL 结果和原始证据引用；未执行项明确。

文件名是后续交付约定，不表示本次已经生成这些实施报告。原始日志和自动报告仍按 R500 进入 `artifacts/records/.../current`，不要塞进 review 目录。

建议自检表一行一条 Case：

| Case ID / 场景 | 原→新文件/函数 | 旧→新正文行数 | 硬件顺序差异 | 断言/覆盖差异 | Driver差异 | 软件证据 | HIL证据 | 结论/剩余问题 |
|---|---|---:|---|---|---|---|---|---|
| 实际填写 | 实际填写 | 实测 | 无/逐项解释 | 无/范围调整 | 实际接口 | 精确日志路径 | 精确记录或 NOT_EXECUTED | 不能空写 PASS |

最终给用户的对话汇报保持短：改了哪些 P1/P2、Case 是否三段式/20 行、Driver 是否薄、硬件流程是否有差异、实际验证范围、提交 SHA、尚未确认的问题。详细依据放文档，不再用长篇解释代替可审查的代码和证据。

---

## 19. 来源与事实边界

本文的仓库事实均以以下基线文件为依据；链接固定在调查 SHA，实施时需读实时版本。用户“现有 Case 已硬件通过”的说明作为行为保持前提，本次没有重新执行硬件测试。

- [仓库入口与约束](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/AGENTS.md)
- [模块路由和精确检查入口](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/project-governance/modules/ip-package.yaml)
- [CAN 稳定 Case 注册表](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/case_registry.py)
- [公共 CAN 契约](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/test_case_doc/can/can.md)
- [CAN Driver：命令、等待和真实请求边界](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/drivers/can/driver.py)
- [CAN Contract：现有命令编号和字数](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/drivers/can/contract.py)
- [CAN Service：普通 IRQ/ECC/DMU 的绑定和记录](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/firmware/services/src/et_can_service.c)
- [CAN Service 运行状态字段](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/firmware/services/include/et_can_service.h)
- [CRG 硬件复位实现](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/firmware/wrap/src/et_crg_wrap.c)
- [Resource Pool 复位与句柄](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/firmware/wrap/src/et_resource_wrap.c)
- [IRQ Manager 的共享线路与解绑](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/firmware/framework/src/et_irq_manager.c)
- [P1 Message RAM March 及数据路径](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/test_can_p1.py)
- [P1 Timeout 连续阶段](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/test_can_p1_timeout.py)
- [P2 ECC 原始覆盖](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/test_can_p2_ecc.py)
- [P2 DMA/DMU 路径](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/test_can_p2_dmu.py)
- [P2 Watchdog 开启/关闭/恢复](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/test_cases/can/test_can_p2_watchdog.py)
- [人工报告备注与状态聚合](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/pc/et_test_platform/results/case_report.py)
- [R200 PC/Driver 边界](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/report/design/rules/R200_pc_layer_responsibilities.md)
- [R210 Case 与生命周期边界](https://github.com/abba-labs/et-harness/blob/d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130/report/design/rules/R210_pc_case_responsibility.md)

**本次状态：只提交指导文档和索引；没有实施上述生产改动，没有新增软件/HIL/CI 通过声明。**
