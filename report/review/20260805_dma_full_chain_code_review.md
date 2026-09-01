# DMA 全链路代码评审与优化设计

文档状态：第一轮 DMA 全链路静态评审，持续更新  
评审时间：2026-08-05 18:52 CST  
评审基线：`main@76a6785b0257b0d8a14af6df441338bccdf9a8c3`  
评审分支：`codex/dma-review-20260805`  
关联总评审：[平台代码评审记录](20260805_platform_code_review.md)  
当前限制：本轮结论来自代码、Capability Profile、DMA Case 与 SDK Driver 的静态贯通分析；尚未基于本轮问题执行 Keil 编译、HIL 或故障注入

> 本轮目标不是仅找出当前能触发的 Bug，而是为后续由同一评审者直接修改 DMA 代码确定长期可维护的实现方向。整改必须同时满足：符合既定分层、可靠、稳定、轻量、易扩展，并严格避免增加第二套状态、隐式旁路或芯片分支。

---

## 1. 评审范围

本轮沿 DMA 的实际调用链检查：

```text
DMA pytest Case
  -> DMA helper / peripheral pair
  -> PC DmaDriver
  -> TargetClient / ET-Frame
  -> Firmware DMA Service
  -> Framework IRQ Manager
  -> Common DMA Wrap
  -> ET6801 AHBDMA SDK / Test Driver Extension
  -> DMA / DMAMUX / UART / Resource memory
  -> IRQ evidence / result JSON / CaseResult
```

已重点阅读：

```text
firmware/services/include/et_dma_service.h
firmware/services/src/et_dma_service.c
firmware/wrap/include/et_dma_wrap.h
firmware/wrap/src/et_dma_wrap.c
firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_ahbdma.h
pc/et_test_platform/drivers/dma.py
pc/et_test_platform/test_cases/dma/dma_helpers.py
pc/et_test_platform/test_cases/dma/dma_irq_helpers.py
pc/et_test_platform/test_cases/dma/dma_test_case_p0.py
pc/et_test_platform/test_cases/dma/dma_test_case_p1.py
pc/et_test_platform/test_cases/dma/dma_test_case_p2.py
pc/et_test_platform/profiles/runtime_capabilities.py
pc/et_test_platform/profiles/chip_capabilities/et6801/ip/dma.yaml
test_case_doc/DMA.md
```

---

## 2. 总体评价

DMA 当前主分层方向是正确的：

- PC Case 通过 `DmaDriver` 使用稳定 Wire Command，不直接访问 DMA 寄存器。
- DMA Service 不包含 ET6801 SDK 类型，只调用 DMA Wrap 与公共 IRQ Manager。
- DMA Wrap 集中完成 chip-neutral config 到 ET6801 AHBDMA Driver 的映射。
- 外设传输通过 `DmaPeripheralPair`、SYSCTRL 与 UART handle 进行 Case 级编排，没有把跨 IP 流程塞进 DMA Service。
- IRQ Result 已使用 generation 保护读取一致性，方向优于普通裸字段返回。
- Capability v2 已提供实例、传输类型、每通道块大小、FIFO 深度、LLI、gather/scatter 等芯片事实。

但 DMA 当前已经出现与 UART 整改前类似、且更容易在并发场景放大的结构性风险：

```text
同一组中断 Mask 由 Managed IRQ 与 Raw Mask Command 两套入口共同修改
IRQ Result 的两个写者没有互斥，generation 只能保护读者，不能保护写者
一个控制器只保存一个 irq_channel，但物理 IRQ 是控制器级共享线路
通道配置、等待超时、IRQ teardown 失败后缺少唯一可恢复状态
公共 Case 大量写死 ET6801 的 2 控制器 / 8 通道 / 4095 / 0xFF
LLI Descriptor 接口允许固件按 PC 提供的原始地址直接写内存
```

如果继续直接增加错误注入、更多并发通道、ADC/SPI 外设链路和新芯片，DMA Service 与 Case 会快速形成多套隐式状态。因此后续整改应优先收敛：

1. 中断所有权；
2. 生命周期与失败恢复；
3. 原始地址安全边界；
4. Capability 驱动的公共 Case；
5. 可证明的并发测试方法。

---

## 3. 问题摘要

| ID | 等级 | 状态 | 问题摘要 |
|---|---|---|---|
| DMA-REV-001 | P1 | 已确认 | Managed IRQ 与 Raw Interrupt Mask/Pending Command 同时修改同一硬件状态，Service 缓存可能与真实 Mask 分叉 |
| DMA-REV-002 | P1 | 已确认 | `result_generation` 存在 ISR 与主循环两个写者，`IRQ_RESULT_CLEAR` 可与 callback 交错并丢失真实事件 |
| DMA-REV-003 | P1 | 已确认 | IRQ enable/disable 的失败回滚会丢失 binding 状态，后续重试可能形成重复 callback 或无法清理 |
| DMA-REV-004 | P1 | 已确认 | DMA 每控制器只跟踪一个 `irq_channel`，但物理 IRQ 为控制器级共享，其他通道事件会被计为 unexpected 或被忽略 |
| DMA-REV-005 | P1 | 已确认 | Channel configure 不是事务：基础寄存器已写入后握手配置仍可能失败，失败后留下半配置通道 |
| DMA-REV-006 | P1 | 已确认 | `START_WAIT` 与双通道完成顺序等待在超时/观察错误后不回收通道，远程状态可能长期不确定 |
| DMA-REV-007 | P1 | 已确认 | LLI Descriptor 初始化接受任意对齐原始地址，包括地址 0，固件可被请求写入未批准内存 |
| DMA-REV-008 | P1 | 已确认 | Suspend/Resume Case 的通过条件与真实状态机矛盾，可能在“已完成”或“未完成”两种情况下随机失败 |
| DMA-REV-009 | P1 | 高风险 | Priority arbitration 通过轮询 Channel Enable 位推断完成顺序，无法可靠观测同一轮询间隔内的先后关系 |
| DMA-REV-010 | P1 | 已确认 | 公共 DMA Case 写死 2 个控制器、8 个通道、`0xFF` 和 `4095`，违反跨芯片 Capability 架构 |
| DMA-REV-011 | P2 | 已确认 | Runtime Capability 在 ET6801 Wrap 中统一硬编码并无条件宣称全部扩展能力，未来芯片容易过度声明 |
| DMA-REV-012 | P2 | 已确认 | DMA PC Driver 的只读命令未使用 ET-Frame 安全重试，瞬态响应丢失会直接中断长 HIL |
| DMA-REV-013 | P2 | 已确认 | IRQ `overflow_count` 实际记录 clear failure 而非计数溢出，且所有计数器可自然回卷，诊断语义不可信 |
| DMA-REV-014 | P2 | 已确认 | C/Python DMA Wire Contract 与结果文件仍由多处手工复制，协议与证据存在长期漂移风险 |
| DMA-REV-015 | P2 | 已确认 | 多个 Case 的直接 `finally` 清理会在第一个 cleanup 异常后中止剩余回收，可能污染后续 Case |
| DMA-REV-016 | P2 | 已确认 | DMA 专项 JSON 与通用 CaseResult/evidence 未形成单一关联链，历史结果难以追溯完整基线 |

---

# 4. 详细问题

## DMA-REV-001：Managed IRQ 与 Raw Mask Command 形成双状态所有权

**等级：P1**  
**状态：已确认**

### 当前实现

DMA Service 提供两类会修改同一 DMA 中断 Mask 的命令。

Managed IRQ Session：

```text
IRQ_ENABLE / IRQ_COMBINED_ENABLE
  -> disable requested events
  -> clear pending
  -> bind IRQ route
  -> enable requested events
  -> 保存 irq_enabled / irq_channel / enabled_events / routes

IRQ_DISABLE
  -> disable requested events
  -> clear pending
  -> unbind route
  -> 清除 Service 状态
```

Raw Interrupt Control：

```text
INTERRUPT_MASK_ENABLE
INTERRUPT_MASK_DISABLE
INTERRUPT_PENDING_CLEAR
```

Raw Command 直接调用：

```c
et_dma_wrap_set_interrupt_mask(...)
et_dma_wrap_clear_interrupts(...)
```

它们不会更新：

```text
service->irq_enabled
service->irq_channel
service->enabled_events
service->route_count
```

### 确定性风险

1. Managed IRQ 已启用时执行 `INTERRUPT_MASK_DISABLE`：

```text
Service 认为 events 已启用
硬件 Mask 已关闭
IRQ_RESULT 永远不再增加
```

2. Raw Mask 已启用后执行 `IRQ_ENABLE`：

```text
IRQ_ENABLE 会先 disable + clear requested events
Raw test 原有状态被 Managed Session 隐式覆盖
```

3. Managed IRQ 活动期间执行 `INTERRUPT_PENDING_CLEAR`：

```text
真实 IRQ 可能在 callback 前被主循环清掉
Case 无法证明事件是否经过 IRQ Manager
```

4. Managed IRQ disable 以后无法恢复 Raw Command 之前的 Mask 状态。

### 推荐优化

不要引入通用中断框架，只定义清晰的两种互斥模式：

```text
Managed IRQ Session
  - Service 拥有 route、mask、pending clear、evidence

Raw Interrupt Register Test
  - 仅用于寄存器语义 Case
  - 必须在 Managed Session 未激活时执行
```

最轻量的第一阶段规则：

```text
irq_enabled != 0 时：
  INTERRUPT_MASK_ENABLE/DISABLE/PENDING_CLEAR -> BUSY

执行 Raw Mask Command 时：
  不允许同时创建 Managed Session
  Case 必须显式恢复默认 Mask
```

长期如需同时验证多通道 IRQ，再升级为每通道 Managed State，不应继续让两类命令无约束交叉。

### 验收条件

1. Managed IRQ 活动期间 Raw Mask/Pending Command 返回稳定 `BUSY`，且不改变任何硬件状态。
2. Raw Mask Case 清理后才能进入 Managed IRQ Session。
3. 新增命令序列回归：Raw→Managed、Managed→Raw、Managed→Pending Clear。
4. HIL 中断结果不再出现“enabled_events 有值但硬件 Mask 为 0”的状态。

---

## DMA-REV-002：IRQ Result generation 不能保护两个并发写者

**等级：P1**  
**状态：已确认**

### 当前实现

`dma_irq_callback()` 与 `clear_result()` 都使用：

```c
++service->result_generation;
修改 irq_result
++service->result_generation;
```

`write_irq_result()` 通过前后 generation 相等且为偶数，获得一致读快照。

该机制只能在“单写者、多读者”条件下成立。目前存在两个写者：

```text
ISR writer：dma_irq_callback()
Main-loop writer：IRQ_RESULT_CLEAR -> clear_result()
```

### 可发生的交错

```text
Main: generation++              // odd
ISR : generation++              // even
ISR : 写入真实 event/count
ISR : generation++              // odd
Main: 清零全部 result
Main: generation++              // even
```

最终：

- generation 看起来合法；
- ISR 真实事件被清零；
- PC 永远看不到该事件。

这不是理论上的数据竞争，而是单核 MCU 上主循环可被中断抢占时的合法执行顺序。

### 推荐优化

保持 generation 作为读一致性机制，但必须把所有写者串行化。

轻量方案二选一：

**方案 A：短临界区**

```text
IRQ_RESULT_CLEAR
  -> 进入 Framework IRQ critical section
  -> clear_result_locked()
  -> 退出 critical section
```

**方案 B：临时屏蔽当前 Managed DMA IRQ routes**

```text
保存当前 route enable
关闭当前 DMA IRQ route
清零 result
恢复 route
```

优先使用项目已有的公共 IRQ 临界区 API；不要在 DMA Service 中直接写 NVIC。

### 验收条件

1. Native/host test 模拟 clear 期间 callback 抢占，事件不得丢失或生成非法 generation。
2. `write_irq_result()` 始终只看到完整旧快照或完整新快照。
3. `clear_result()` 只能由已序列化路径调用。
4. ISR callback 仍保持短路径，不增加动态分配或复杂锁。

---

## DMA-REV-003：IRQ teardown 失败后丢失真实 binding 状态

**等级：P1**  
**状态：已确认**

### 当前 `irq_disable()`

即使发生以下错误：

```text
硬件 disable interrupts 失败
IRQ Manager unbind 失败
```

函数仍然执行：

```c
service->irq_enabled = 0u;
service->route_count = 0u;
service->enabled_events = 0u;
service->irq_combined = 0u;
```

这会让软件声称 IRQ Session 已完全清理，但真实 IRQ binding 可能仍存在。

### 当前 `irq_enable()` 回滚

某一路由 bind 失败时，会尝试 unbind 已绑定路由，但：

- unbind 返回值被忽略；
- 无论是否解绑成功，都清空 `route_count` 和 `enabled_events`；
- 下一次 enable 可能重复绑定同一 callback。

硬件 enable 失败后的 unbind 同样忽略失败。

### 推荐优化

建立一个 DMA 私有、幂等的：

```text
dma_irq_reset_to_idle(service)
```

规则：

1. 先关闭硬件事件；
2. 每条 route 单独 unbind；
3. 只有确认 unbind 成功的 route 才从状态中删除；
4. 任一路由仍绑定时，保留 route 和 `irq_enabled/cleanup_pending` 状态；
5. 再次调用时继续回收，不创建重复 binding；
6. 全部清理成功后再清空 channel/events/combined。

可以使用固定数组和 bitmask 记录已绑定 route，无需动态结构。

### 验收条件

1. 在第 N 条 route unbind 注入失败，Service 保留准确的剩余 binding 集合。
2. 重复 `IRQ_DISABLE` 能继续回收并最终成功。
3. 清理失败后执行 `IRQ_ENABLE` 不得创建重复 callback。
4. 控制器 disable 在任何残留 binding 存在时返回 BUSY。

---

## DMA-REV-004：IRQ Service 只跟踪一个 Channel，但物理 IRQ 是控制器级共享

**等级：P1**  
**状态：已确认**

### 当前模型

每个 DMA Service 只有：

```c
et_dma_wrap_channel_id_t irq_channel;
uint32_t enabled_events;
```

物理 IRQ route 则是：

```text
DMAx_TFR_IRQn
DMAx_BLOCK_IRQn
DMAx_SRCTRAN_IRQn
DMAx_DSTTRAN_IRQn
DMAx_ERROR_IRQn
DMAx_COMBINED_IRQn
```

这些线路属于整个控制器，不属于某一个 channel。

Callback 触发后只查询：

```c
et_dma_wrap_get_pending_events(
    controller_id,
    service->irq_channel,
    &pending)
```

### 影响

当同一控制器的另一个 Channel 触发相同物理 IRQ：

```text
IRQ Manager 调用当前 Service callback
tracked irq_channel 没有 pending
pending == 0
unexpected_count++
```

因此：

- 多通道并发 IRQ 无法正确观察；
- Raw Mask Case 或遗留 Mask 可能污染 Managed IRQ Result；
- Combined IRQ 下问题更加明显；
- `unexpected_count` 可能不是“异常 IRQ”，而是“另一个合法 Channel 的 IRQ”。

### 推荐优化方向

两种设计必须明确选择一种。

**阶段一轻量方案：单 Channel IRQ Session 明确化**

- Managed IRQ 启用时确保同控制器其他 Channel 的相关 Mask 均关闭；
- Raw Mask Command 与 Managed Session 互斥；
- Runtime Capability 明确暴露 `single_channel_irq_session`。

**长期扩展方案：每 Channel 固定状态**

```c
irq_channel_state[channel_count]
```

每个 Channel 保存 enabled/latched/count；callback 读取控制器级 bitmaps 后按 Channel 分发。8 通道静态数组开销可控，比继续堆叠单 Channel 特例更易扩展。

考虑未来多通道 DMA IRQ、ADC/UART 并发搬运，推荐最终采用固定每 Channel 状态，但不需要动态订阅框架。

### 验收条件

1. 两个 Channel 同时产生 TFR 时，不得把其中一个记为 unexpected。
2. Combined IRQ 能区分多个 Channel 的 pending bitmap。
3. 单 Channel 模式下，Service 必须主动保证其他 Channel 的相关 Mask 不会触发当前 session。
4. Capability 与 Wire Contract 明确声明当前支持层级。

---

## DMA-REV-005：Channel configure 失败后留下半配置硬件

**等级：P1**  
**状态：已确认**

### 当前 Wrap 顺序

```text
validate config header
map controller/channel
确认 channel free
build_driver_config
map handshake mode/polarity
AHBDMA_initChannel()             // 已写通道寄存器
AHBDMA_testConfigureChannelHandshake()
```

如果最后一步 handshake 配置失败：

```text
Wrap 返回错误
但基础通道寄存器已经写入
```

PC 认为 `configure()` 失败，通常不会把该 Channel 标记为 configured，cleanup 也可能不执行 `deconfigure()`。

### 推荐优化

1. 所有可纯计算验证必须在硬件写入前完成。
2. `AHBDMA_initChannel()` 后任何步骤失败，必须执行：

```text
AHBDMA_deInitChannel(controller, channel)
```

3. 若 deinit 也失败，返回明确 `IO_ERROR`，并让 Service 进入 `cleanup_pending`，不能假装 configure 无副作用。
4. 更理想的是将 handshake 字段合入一次通道初始化，但需确认 SDK 结构和硬件写入顺序后再修改，不应在 Common Wrap 中直接写寄存器。

### 验收条件

1. 注入 handshake 配置失败后，Channel 状态与寄存器快照回到 idle/default。
2. 随后同 Channel 合法 configure 能成功，不需要控制器复位。
3. PC cleanup 不依赖“configure 调用已成功返回”才能恢复半配置状态。

---

## DMA-REV-006：等待命令失败后保留活动 Channel

**等级：P1**  
**状态：已确认**

### 涉及函数

```text
et_dma_wrap_start_channel_and_wait()
et_dma_wrap_start_channels_wait_order()
```

两者都先启动 Channel，再轮询。

超时或观察错误时直接返回：

```text
ET_WRAP_STATUS_TIMEOUT
ET_WRAP_STATUS_IO_ERROR
```

但没有停止已启动 Channel。

### 远程故障模型

PC 对 mutating request 默认不重试。出现以下情况时：

- DMA 执行时间超过 max_polls；
- 两 Channel 在同一轮询间隔内完成；
- ET-Frame 响应丢失；
- PC 收到 timeout/rejection；

PC 无法确定 Channel 当前是：

```text
仍运行 / 已完成 / 部分完成 / 已报错
```

### 推荐优化

`*_WAIT` 命令应定义成“有界事务”。非 OK 返回前：

```text
停止本命令启动的 Channel
等待 FIFO 到达可清理状态（有界）
返回原始错误 + cleanup 状态
```

为了保持 Wire 轻量，可先规定：

- timeout/error 时 Wrap 必须 best-effort stop；
- stop 失败统一升级为 `IO_ERROR`；
- PC 在失败后仍执行幂等 deconfigure/reset。

长期可增加 status response，但不要让一个错误码同时表示“已安全停止”和“仍在运行”。

### 验收条件

1. `START_WAIT` 超时后 Channel 不再 active。
2. 双 Channel wait-order 观察失败后两个 Channel 均被回收。
3. 下一条合法 DMA Case 无需 controller power cycle 即可执行。
4. 故障注入记录清楚区分原始 timeout 与 cleanup failure。

---

## DMA-REV-007：LLI Descriptor 初始化缺少内存授权边界

**等级：P1**  
**状态：已确认**

### 当前接口

PC 发送：

```text
64-byte DmaConfig
+ uint64 descriptor_address
+ is_last
```

Wrap 只检查：

```text
地址 <= UINT32_MAX
4-byte 对齐
```

没有检查：

- descriptor_address 是否为 0；
- 是否落在 Resource Service 分配池；
- 28-byte Descriptor 是否完整位于可写 SRAM；
- 是否与固件代码、栈、Service 状态或外设地址重叠。

随后直接执行：

```c
descriptor = (AHBDMA_LLI_TypeDef *)descriptor_address;
AHBDMA_initLLI(descriptor, ...);
```

PC 只要提交一个合法对齐地址，固件就会主动写该地址。

### 推荐优化

最低限度立即增加：

```text
descriptor_address != 0
address + sizeof(descriptor) 不溢出
完整范围位于 Board 批准的 DMA descriptor memory window
```

长期正确方案是避免 Wire 暴露任意写地址：

```text
Resource Service 分配 descriptor resource
PC 发送 resource handle + offset
Firmware 将 handle 解析为受控地址
```

若短期不改 Wire，可由 Application 在 DMA Service init 时注入一个只读 `validate_writable_range()` callback；DMA Service 只调用验证接口，不直接依赖 Resource Service 实现。

### 验收条件

1. 地址 0、越界、外设地址、固件代码区、跨资源尾部地址均被拒绝且不写内存。
2. Resource 分配的 28-byte 对齐区域可以正常初始化。
3. LLI fault test 使用批准的 fault window，不通过任意坏地址制造 HardFault。

---

## DMA-REV-008：Suspend/Resume Case 的状态断言互相矛盾

**等级：P1**  
**状态：已确认**

### 当前 Case

`test_dma_p1_003_suspend_resume`：

```text
配置 4095-byte M2M
start
立即 suspend
等待 FIFO empty
assert destination == complete source_data
assert channel is not free
resume
sleep 10 ms
再次 suspend
再次 assert complete data
```

### 问题

若第一次 suspend 真正在传输中生效：

- 目标数据通常只完成一部分；
- `destination == source_data` 不应成立。

若 DMA 已在 suspend 前完成：

- 完整数据可能成立；
- Channel 应当 free；
- `assert not is_free` 不应成立。

所以当前通过条件依赖一个非常窄且不可证明的硬件时序窗口。

此外 Case 把 source/destination update mode 设为 Reload，与“验证 suspend/resume”混入了另一个 Feature，增加不可控状态。

### 推荐优化

Suspend/Resume 必须使用可控背压：

- 使用 hardware/software handshake 限制每次只推进少量 item；
- 在明确 partial progress 后 suspend；
- 读取 channel snapshot，证明地址/remaining count 在 suspend 期间稳定；
- resume 后继续发 request，最终完成并校验数据。

如果当前 Bench 无法控制 DMA 进度，应把该 Case 标记为 deferred，而不是依靠 CPU 与 DMA 的竞速。

### 验收条件

1. Suspend 前证明已发生部分但未全部传输。
2. Suspend 期间两个快照之间地址/计数保持不变。
3. Resume 后从原位置继续，不重复或遗漏数据。
4. Case 不同时混测 Reload，除非测试目标明确为 Reload+Suspend 组合。

---

## DMA-REV-009：Priority arbitration 完成顺序观察方法不可靠

**等级：P1**  
**状态：高风险，需 HIL 复核**

### 当前观察方法

`et_dma_wrap_start_channels_wait_order()`：

1. 一次 mask 启动两个 Channel；
2. 轮询 Channel Enable bitmap；
3. 第一次发现一个 Channel disable，记为 first；
4. 再发现另一个 disable，记为 second；
5. 如果一次轮询发现两个都完成，返回 `IO_ERROR`。

### 风险

- 两个 M2M 传输可能在相邻 CPU 轮询之间全部完成；
- “同一次轮询都完成”不等于“没有先后顺序”，只是观察器分辨率不足；
- DMA priority 只在真实总线仲裁竞争时起作用，两个独立 SRAM 路径不一定形成足够稳定的竞争；
- PC Case 断言高优先级 Channel 必定先完成，可能把观察器局限当成硬件错误。

### 推荐优化

优先级 Case 应使用独立、足够分辨率的证据：

- 每 Channel 完成 IRQ + 硬件 timer/timestamp；或
- 在控制器侧固定记录 first-complete channel；或
- 构造明确的共享总线/端点背压，使 Channel 长时间竞争。

在没有可靠观察器前，建议把“精确完成顺序”降为 deferred，并保留：

- 两 Channel 原子启动成功；
- 两 Channel 最终数据正确；
- 配置寄存器 priority 值正确。

### 验收条件

1. 观察器能区分同一 CPU poll interval 内的完成顺序。
2. 反转 priority 后 first-complete 稳定反转。
3. 多次重复结果一致，且不是由 Channel 编号固定顺序造成。

---

## DMA-REV-010：公共 DMA Case 写死 ET6801 拓扑与限制

**等级：P1**  
**状态：已确认**

### 具体硬编码

公共 Case 中存在：

```python
assert instances == ("dma0", "dma1")
for instance_id in range(2)
@pytest.mark.parametrize("instance_id", [0, 1])
assert dynamic.channel_count == 8
for channel in range(8)
dma.start_channels(0xFF)
transfer_count = 4095
for count in (..., 4094, 4095)
```

PC Driver 也限定：

```python
channel_mask <= 0xFF
first_channel < 8
second_channel < 8
```

### 架构冲突

平台设计要求：

- 公共 Case 按 Feature/Contract 编写；
- 芯片差异来自 Profile 与 Runtime Capability；
- 新芯片不复制整套 Case。

当前公共 DMA Case 实际是 ET6801 产品基线，新增 1 控制器/4 通道或 16 通道 DMA 时必须修改公共代码。

### 推荐优化

拆分两类测试：

**公共 Feature Case**

```text
instances = target_capabilities.instances("dma")
逐实例读取 runtime channel_count/max_transfer_count
channel_mask = (1 << channel_count) - 1
边界值从 runtime/profile 生成
```

**ET6801 Product Baseline Case**

```text
assert instances == dma0,dma1
assert channel_count == 8
assert max_transfer_count == 4095
```

Product Baseline 放在产品 profile validation，不污染公共 DMA Feature Case。

PC Driver 的 channel/mask 校验也应基于实例 capability，而不是固定 8；可在 Driver 构造后缓存一次 runtime capability，或由调用方传入 limits。不要为此让 Driver 读取 YAML。

### 验收条件

1. 模拟 1 控制器/4 通道 profile 时公共 Case 无代码修改即可收集与运行。
2. ET6801 精确资源断言仍由独立 baseline test 保留。
3. 公共 Case 中不再出现 `range(2)`、`range(8)`、`0xFF`、固定 `4095` 作为芯片事实。

---

## DMA-REV-011：Runtime Capability 统一硬编码并可能过度声明

**等级：P2**  
**状态：已确认**

### 当前 Wrap

```c
#define ET_DMA_WRAP_CHANNEL_COUNT 8u
#define ET_DMA_WRAP_MAX_TRANSFER_COUNT 4095u
```

两个控制器无条件返回相同 feature flags：

```text
M2M/M2P/P2M/P2P
Suspend/Resume
Interrupts
Reload
Gather/Scatter
LLI
Atomic mask start
Software handshake
Handshake mode/polarity
```

部分能力依赖 `ET_ENABLE_TEST_DRIVER_EXTENSIONS` 中的 SDK 扩展，但 Capability 不根据编译开关或具体 Driver 实现调整。

### 风险

- 新芯片 adapter 容易复制 ET6801 常量；
- 某个 build 未包含 test extension 时仍可能宣称 Feature；
- 两个控制器如存在参数差异，Runtime Capability 无法表达；
- Component Parameter 已有真实信息，但 capability 仍由手工常量维护。

### 推荐优化

保持 Common Wrap 类型稳定，但把芯片事实下沉到 chip adapter/config：

```text
ET_CHIP_DMA_CHANNEL_COUNT(controller)
ET_CHIP_DMA_MAX_TRANSFER_COUNT(controller)
ET_CHIP_DMA_FEATURE_FLAGS(controller, build_flags)
```

可从已验证的 SDK 宏、component parameter 或 chip config 生成。不要在 PC Case 中解析寄存器位来替代 Runtime Capability。

### 验收条件

1. 关闭某个 test extension 后，对应 Runtime Feature 自动消失。
2. controller 级差异可以独立返回。
3. Wrap 公共代码不包含 ET6801 固定资源数字。

---

## DMA-REV-012：只读 DMA Command 未使用安全重试

**等级：P2**  
**状态：已确认**

### 当前 Driver

所有命令最终进入：

```python
def _request(self, command, body=b""):
    return self._target.request(...)
```

没有为只读命令传入 `retry_safe=True`。

可安全重试的命令包括：

```text
CAPABILITIES_GET
CHANNEL_STATUS_GET
FREE_CHANNEL_FIND（需确认读取是否无副作用）
COMPONENT_SNAPSHOT_GET
INTERRUPT_SNAPSHOT_GET
CHANNEL_SNAPSHOT_GET
IRQ_RESULT_GET
```

### 推荐优化

建立 DMA 私有 command traits：

```python
_READ_ONLY_COMMANDS = {...}
```

`_request()` 根据 trait 启用 ET-Frame exact-frame retry。Mutating Command 继续默认不重试。

`FREE_CHANNEL_FIND` 若 Driver 内部只是读取，应标记 read-only；若存在硬件 reservation 语义，则不能重试，必须在契约中明确。

### 验收条件

1. 只读 response 第一次丢失后 exact duplicate retry 成功。
2. Mutating command 不自动重试。
3. 单元测试覆盖 command trait，不由每个方法手工传布尔值。

---

## DMA-REV-013：IRQ 计数与错误字段语义不准确

**等级：P2**  
**状态：已确认**

### 当前 callback

```c
if (clear_interrupts(...) != OK) {
    ++overflow_count;
}
latched_events |= pending;
++irq_count;
```

`overflow_count` 实际记录“中断清除失败次数”，不是计数器 overflow。

同时：

```text
irq_count
unexpected_count
overflow_count
```

均直接 `++`，达到 `UINT32_MAX` 后自然回卷。

### 影响

- Case 报告 `overflow_count != 0` 时无法判断是 counter overflow 还是 clear failure；
- 长时间 stress 可能从最大值回到 0，形成假干净结果；
- clear failure 后同一 level IRQ 可能重复触发，`irq_count` 又被重复增加，放大诊断混乱。

### 推荐优化

字段改为明确语义：

```text
irq_callback_count
unexpected_irq_count
clear_failure_count
counter_saturated_mask
```

所有计数采用饱和递增。若保持 Wire 兼容，可暂时把原 `overflow_count` 明确定义为 `clear_failure_count` 并更新 PC 名称/文档，未来协议版本再扩展。

### 验收条件

1. clear failure 注入后只增加明确的 clear failure 字段。
2. 计数达到最大值后保持最大值，不回卷。
3. Case 报告能区分事件、非目标 IRQ、清除失败和计数饱和。

---

## DMA-REV-014：DMA Wire Contract 手工复制

**等级：P2**  
**状态：已确认**

### 重复事实

C：

```text
ET_DMA_COMMAND_* IDs
ET_DMA_CONFIG_REQUEST_SIZE = 64
request offset 0..63
response size magic number 8/16/20/36/48/64/76
```

Python：

```python
DmaCommand
DMA_CONFIG = struct.Struct("<16BQQIIQIIII")
IRQ_RESULT = struct.Struct("<IIII")
...
```

两端通过人工同步。

### 推荐优化

建立一个小型 DMA Contract Source，例如 YAML/JSON/Python declarative spec，生成：

- C command enum；
- Python IntEnum；
- request/response body size；
- field offset/codec；
- golden vectors；
- reserved byte validation tests。

不需要运行时反射，也不把生成器带入固件。生成结果仍是普通 C/Python 静态代码。

### 验收条件

1. 修改字段或命令 ID 只改一个源文件。
2. C/Python golden vector 在 CI 比较一致。
3. Service 不再散落 response magic size。

---

## DMA-REV-015：部分 Case 清理会被第一个异常中断

**等级：P2**  
**状态：已确认**

`dma_helpers._cleanup_all()` 已正确实现：

- 尝试全部清理；
- 保留原始测试异常；
- 无原始异常时报告第一个 cleanup 异常。

但多个 Case 仍直接在 `finally` 中顺序调用：

```python
for channel in configured:
    dma.stop(channel)
    dma.deconfigure(channel)
dma.controller_disable()
```

若第一个 `stop()` 失败：

- 后续 Channel 不再清理；
- controller disable 不执行；
- 下一 Case 继承污染状态。

### 推荐优化

所有多步骤 DMA cleanup 统一使用一个共享 helper，并记录每一步结果：

```text
irq disable
software request clear
channel stop
channel deconfigure
DMAMUX release
controller disable
resource reset
peer close
```

不要求引入 fixture 自动执行业务动作；Case 仍显式组织 cleanup，只复用幂等执行器。

### 验收条件

1. 任一 cleanup 步骤失败，剩余步骤仍执行。
2. 原始测试失败不被 cleanup exception 覆盖。
3. cleanup 结果写入 Case evidence。

---

## DMA-REV-016：DMA 专项结果与通用 CaseResult 未闭环

**等级：P2**  
**状态：已确认**

DMA Case 大量直接写：

```text
et_artifact_dir/dma_p*.json
```

通用 pytest plugin 同时写：

```text
cases/<case_run_id>/result.json
```

两者缺少稳定关联：

- DMA JSON 不一定包含 `case_run_id`；
- 通用 CaseResult 不一定登记 DMA JSON 相对路径/hash；
- Git SHA、firmware image SHA、Capability manifest SHA 尚未形成统一基线。

### 推荐优化

保持 DMA 专项明细文件，但由统一 recorder 注册：

```text
record_artifact(
  kind="dma_detail",
  relative_path=...,
  sha256=...,
)
```

CaseResult 只保存索引和摘要，不复制大数据。这样既轻量，又能从一次 Case 唯一追溯到专项结果和完整代码/固件基线。

---

# 5. 推荐目标实现

DMA 后续整改不应增加重量级框架，建议收敛为下面的静态结构：

```text
DMA Service（每 controller 一个）

  Controller lifecycle
    - controller_enabled
    - configured_channel_mask
    - active_channel_mask
    - cleanup_pending_mask

  Managed IRQ owner
    - managed session / raw register mode 互斥
    - bound_route_mask
    - per-channel IRQ result（最终目标）
    - serialized result clear

  Channel transaction helpers
    - configure with rollback
    - start/wait with bounded cleanup
    - idempotent stop/deconfigure

  Command dispatch
    - 继续保持静态 switch
    - 同类命令使用公共 validate/apply helper

DMA Wrap
  - 只做 chip-neutral 到 ET6801 Driver 映射
  - 所有纯校验先于寄存器写入
  - 寄存器写入失败执行最小回滚
  - Capability 来自 chip adapter/config，不来自公共硬编码
```

禁止引入：

- RTOS；
- 动态内存；
- 运行时插件；
- 通用事件总线；
- 每个 Command 一个文件；
- Case 直接访问 DMA 寄存器；
- 在 Common Case 中增加芯片名称分支。

---

# 6. 后续整改优先级

## 第一阶段：先关闭会产生错误状态和假证据的问题

1. DMA-REV-002：IRQ Result 双写者并发。
2. DMA-REV-001：Managed IRQ 与 Raw Mask 双所有权。
3. DMA-REV-003：IRQ teardown 失败状态保留。
4. DMA-REV-004：单 Channel IRQ 与控制器级 IRQ 冲突。
5. DMA-REV-005：Channel configure 失败回滚。
6. DMA-REV-006：wait timeout 后回收。
7. DMA-REV-007：LLI 地址授权边界。

## 第二阶段：修复不可靠 Case

1. DMA-REV-008：Suspend/Resume 重写或 deferred。
2. DMA-REV-009：Priority arbitration 重新定义证据。
3. DMA-REV-015：统一 cleanup。

## 第三阶段：长期架构收敛

1. DMA-REV-010：公共 Case Capability 化。
2. DMA-REV-011：Runtime Capability 下沉 chip adapter。
3. DMA-REV-012：只读 retry traits。
4. DMA-REV-013：IRQ 诊断字段语义。
5. DMA-REV-014：Wire Contract 生成。
6. DMA-REV-016：结果/evidence 关联。

---

# 7. 修改后的验证矩阵

| 层级 | 必须验证 | 硬件要求 |
|---|---|---|
| Python Driver unit | DmaConfig codec、command traits、动态 channel mask、response validation | 否 |
| Firmware native/host | IRQ clear 并发、bind/unbind 回滚、configure 失败回滚、wait timeout cleanup、raw/managed 互斥 | 否 |
| Static contract | Service/Wrap 分层、无 SDK 类型泄漏、公共 Case 无 ET6801 拓扑硬编码 | 否 |
| GCC host syntax | `et_dma_service.c`、`et_dma_wrap.c` 与新增 helper | 否 |
| Keil build | FPGA/ITCM 与 Silicon/PFLASH 正式 Target | 需要工具链 |
| HIL M2M | 所有 width/address/burst、边界 count、双 controller | 是 |
| HIL IRQ | 分类 IRQ、combined IRQ、多 Channel IRQ、clear failure recovery | 是 |
| HIL lifecycle | configure failure、wait timeout、重复 cleanup、下一 Case 恢复 | 是 |
| HIL LLI | 有限链、单侧链、批准 fault window、descriptor 边界 | 是 |
| HIL suspend/priority | 可控背压的 suspend/resume、独立顺序观察器 | 是 |
| HIL peripheral | UART/ADC/SPI 等 hardware handshake、DMAMUX release | 是 |

未实际执行的项目只能标记“代码分析/代码修复完成”或“待验证”，不得写成硬件 PASS。

---

## 8. 本轮结论

DMA 当前并非需要推倒重写。核心问题与 UART 类似：功能已经较多，但状态所有权没有完全收敛。

最重要的整改方向是减少并行机制：

```text
Managed IRQ + Raw Mask 无约束并行
  -> 两种明确互斥模式

单 channel 软件状态 + controller 级物理 IRQ
  -> 明确单 channel session，最终升级静态 per-channel state

ISR/Main 两个无锁 writer
  -> writer 串行化 + generation 读快照

configure/start wait 失败留半状态
  -> 有界事务 + 幂等 reset/cleanup

任意 LLI 原始地址
  -> Resource/approved memory range 验证

ET6801 固定拓扑公共 Case
  -> Feature Case + Product Baseline 分离
```

后续代码修改应首先关闭 DMA-REV-001 至 DMA-REV-007，再处理测试方法和跨芯片治理。这样可以在不增加重量级基础设施的前提下，保证 DMA 后续接入更多外设和芯片时不会继续积累隐式状态。

---

## 9. 更新记录

| 时间 | 基线 | 内容 |
|---|---|---|
| 2026-08-05 18:52 CST | `main@76a6785b0257b0d8a14af6df441338bccdf9a8c3` | 完成 DMA 第一轮全链路静态评审；记录 DMA-REV-001 至 DMA-REV-016，给出轻量化目标实现、整改优先级和验证矩阵 |
