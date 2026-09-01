# DMA 第二轮代码复核与最终整改边界

文档状态：第二轮静态复核完成，作为后续 DMA 代码整改的最终审查输入  
复核时间：2026-08-05 19:05 CST  
复核基线：`main@76a6785b0257b0d8a14af6df441338bccdf9a8c3`  
复核分支：`codex/dma-review-20260805`  
关联文档：[DMA 全链路代码评审与优化设计](20260805_dma_full_chain_code_review.md)  
当前限制：本轮仍为代码、SDK、Capability、Case 和 Framework 的静态贯通复核，未执行本轮整改后的 Keil、Host C 行为测试或 HIL

> 本轮目的不是继续扩大问题清单，而是逐项验证第一轮结论，纠正过度判断，补齐第一轮遗漏的可靠性边界，并冻结后续实现方向。后续整改应以本文的“最终分类”和“目标结构”为准。

---

## 1. 第二轮复核范围

在第一轮基础上，追加检查了以下关键链路：

```text
TargetClient 请求超时与 retry_safe 语义
Service Router 同步 dispatch 行为
IRQ Manager bind / unbind 的真实错误传播
DMA Service IRQ session、Raw Mask、Result Clear 的交错
DMA Wrap 的地址、宽度、传输类型和握手映射
ET6801 AHBDMA Driver 的 enable/disable/init/deinit/free 真实语义
Resource Service 的 handle 与 raw address 边界
P0/P1/P2 Case 的控制器枚举、通道枚举、清理和通过条件
现有 unit/native 验证能够证明和不能证明的内容
```

重点补读：

```text
pc/et_test_platform/clients/target.py
firmware/framework/src/et_service_router.c
firmware/framework/include/et_irq_manager.h
firmware/framework/src/et_irq_manager.c
firmware/services/src/et_resource_service.c
firmware/wrap/include/et_resource_wrap.h
firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_ahbdma.c
pc/et_test_platform/framework_validation/unit/test_dma_*.py
pc/et_test_platform/framework_validation/native/
pc/et_test_platform/test_cases/dma/dma_peer.py
```

---

## 2. 第一轮结论复核结果

| ID | 第二轮结论 | 最终处理 |
|---|---|---|
| DMA-REV-001 | 确认 | Managed IRQ、Raw Mask/Pending、Controller Disable 确实存在多个硬件状态写入口，必须收敛所有权。 |
| DMA-REV-002 | 确认 | generation 只能保护读快照，不能保护 ISR 与主循环两个写者；`IRQ_RESULT_CLEAR` 存在丢事件窗口。 |
| DMA-REV-003 | 确认并扩大 | DMA Service 会丢 binding 状态；更底层的 IRQ Manager 还会吞掉物理 disable/clear/unregister 失败，必须先修 Framework 契约。 |
| DMA-REV-004 | 确认 | 一个 `irq_channel` 无法正确覆盖控制器级共享 IRQ；其他通道 pending 可能形成重复 IRQ。 |
| DMA-REV-005 | 调整等级 | 当前 ET6801 路径在寄存器写入前已经预校验握手参数，后续握手 helper 对合法参数不会正常失败，因此不是当前高概率功能 Bug；但 Wrap 没有通用回滚能力，仍是未来芯片和故障注入下的结构性缺口，调整为 P2。 |
| DMA-REV-006 | 确认并扩大 | 除超时不回收外，同步等待还会阻塞整个 ET-Frame 服务循环，并与 PC 默认响应超时形成双重不确定状态。 |
| DMA-REV-007 | 确认并扩大 | LLI descriptor 是直接 CPU 写地址；同时普通 DMA source/destination 也缺少批准区域和跨度校验。 |
| DMA-REV-008 | 调整表述 | 当前 Case 使用 Reload 维持通道活动，不一定随机失败；真正问题是它没有证明“传输中暂停”，而是可能在完整 block 已完成后才观察 suspend，属于通过条件与测试声明不一致，调整为 P2。 |
| DMA-REV-009 | 确认 | 通过 CHENREG 轮询推断优先级顺序不可靠；两个通道在同一轮询间隔完成时反而返回 IO_ERROR。 |
| DMA-REV-010 | 确认并扩大 | 除 Case 写死 2/8/4095 外，PC Driver 的 channel mask 和返回值校验也固定为 8 通道，且多个 Case 绕过统一 fixture。 |
| DMA-REV-011 | 确认 | Runtime capabilities 是 ET6801 编译常量，不随 build feature、真实 Driver 支持或未来芯片变化。 |
| DMA-REV-012 | 确认 | 所有 DMA 命令都使用默认单次请求；只读查询没有利用 ET-Frame exact-duplicate replay。 |
| DMA-REV-013 | 确认 | `overflow_count` 实际为中断清除失败次数，命名错误；计数器也没有饱和保护。 |
| DMA-REV-014 | 确认 | C/Python command、body layout、结果字段继续多处手工复制。 |
| DMA-REV-015 | 确认 | 只有部分 helper 使用 `_cleanup_all()`，多个 Case/Helper 仍会在第一个 cleanup 异常后停止。 |
| DMA-REV-016 | 确认 | DMA 专项 JSON 与通用 CaseResult、Git/firmware/profile 基线仍未形成单一证据链。 |

---

## 3. 第二轮新增问题摘要

| ID | 等级 | 状态 | 问题摘要 |
|---|---|---|---|
| DMA-REV-017 | P1 | 已确认 | 普通 DMA source/destination 只校验起始地址和对齐，不校验批准区域、完整访问跨度、递增溢出或递减下溢 |
| DMA-REV-018 | P1 | 已确认 | `START_WAIT` 和 `CHANNELS_START_WAIT_ORDER` 在同步 Service handler 中忙等，可能使 PC 超时且阻塞全部 ET-Frame 命令 |
| DMA-REV-019 | P1 | 已确认 | `CHENREG==0` 被同时解释为“空闲、未配置、成功完成或错误后停止”，当前等待命令可能把错误终止当成功 |
| DMA-REV-020 | P1 | 已确认 | DMA 没有静态 configured/owned channel 状态；`find_free_channel()` 可返回已配置但未启动的通道，Deinit 也没有恢复完整唯一基线 |
| DMA-REV-021 | P1 | 已确认 | IRQ Manager `unbind()` 先删除 binding，再忽略物理 IRQ disable/clear/unregister 失败，DMA Service 无法证明路由已真正释放 |
| DMA-REV-022 | P1 | 已确认 | Transfer Type 与地址模式、接口和握手的跨字段约束未校验，外设端可被配置为地址递增并访问相邻寄存器 |
| DMA-REV-023 | P2 | 已确认 | DMA Runtime Service 门禁与 Case 枚举不一致，多个 Case 直接构造 Driver、按 tuple 下标解释实例号并绕过 fixture |
| DMA-REV-024 | P2 | 已确认 | `resource.reset()` 是全局池复位，Helper 在 Case 内反复调用，未来并行或组合 Case 会使其他资源引用失效 |
| DMA-REV-025 | P2 | 已确认 | 当前 DMA 验证主要是 Python fake 与源码字符串契约，缺少可注入 Wrap/IRQ 失败的 DMA Service native 行为 harness |
| DMA-REV-026 | P2 | 已确认 | DMA Service 注册遇到第一个不支持实例即 `break`，不支持未来稀疏或非连续控制器编号 |

---

# 4. 第二轮新增问题详解

## DMA-REV-017：普通 DMA 地址缺少完整安全边界

**等级：P1**  
**状态：已确认**

### 当前实现

PC `DmaConfig` 将以下地址直接编码为 64-bit：

```text
source_address
destination_address
linked_list_address
```

DMA Service `decode_config()` 只检查地址是否能够放入 `uintptr_t`。ET6801 Wrap 进一步只检查：

```text
地址 <= UINT32_MAX
起始地址满足 1/2/4 byte 对齐
LLP 地址满足 4-byte 对齐
```

当前没有执行：

```text
地址属于 Resource Service 已分配的有效资源
地址属于经批准的外设 DMA endpoint
(start, count, width, address_mode) 的完整访问跨度不溢出
递减模式不会低于合法区域起点
递增模式不会越过资源结尾或 0xffffffff
```

### 确定性风险

对于递增模式：

```text
last = start + (transfer_count - 1) * width
```

当前没有乘法和加法溢出检查。

对于递减模式：

```text
first = start - (transfer_count - 1) * width
```

当前没有下溢检查。

一个错误 Case、错误 offset 或 Wire body 可以让 DMA 写出 Resource pool，覆盖固件状态、协议缓冲区或其他外设寄存器。该问题不要求恶意输入，普通长度/宽度计算错误就可能触发。

### 推荐优化

短期不要引入通用内存管理框架，增加两类明确校验：

1. `et_dma_wrap_validate_span()`：只做无溢出的地址跨度计算和 transfer-type 基础语义。
2. DMA Service/公共 Resource 层验证 memory span 是否位于已批准资源；peripheral endpoint 必须来自受控 endpoint 表。

长期 Wire v2 应优先使用：

```text
Resource handle + offset + length
Peripheral endpoint ID + interface
```

而不是让业务 Case自由提交任意 raw address。

### 验收条件

- 递增上溢、递减下溢、跨资源边界全部在任何寄存器写入前拒绝。
- Memory endpoint 只能访问仍有效的 Resource handle 范围。
- Peripheral endpoint 只能使用 Wrap/Service 声明的地址和方向。
- LLI descriptor 不能使用地址 0 或未批准地址。

---

## DMA-REV-018：同步等待命令会阻塞控制平面

**等级：P1**  
**状态：已确认**

### 当前链路

`et_service_dispatch()` 同步调用 Service handler。DMA 以下命令在 handler 内进入轮询：

```text
CHANNEL_START_WAIT
CHANNELS_START_WAIT_ORDER
```

Wrap 使用 `max_polls` 持续读取 DMA 状态，直到完成或 target-side timeout。

PC `DmaDriver.start_wait()` 和 `start_channels_wait_order()` 默认使用：

```text
max_polls = 10_000_000
```

但没有给 `TargetClient.request()` 设置匹配的 `timeout_s`，因此使用 Bench/Client 默认响应超时。

### 风险链

```text
PC 发出等待命令
  -> Firmware 同步 handler 忙等
  -> 主循环无法继续处理后续 ET-Frame
  -> PC 先达到响应超时
  -> PC 认为命令失败，但 target 仍可能继续忙等或刚刚完成
  -> Cleanup 新请求无法被及时处理
```

这会形成“PC 超时、Target 仍执行、控制平面暂时失联”的三态不确定性。

此外 `ET_WRAP_STATUS_TIMEOUT` 被 `status_from_wrap()` 映射为 `ET_STATUS_INTERNAL_ERROR`，PC 无法区分 target-side poll timeout 和普通内部错误。

### 推荐优化

正式 Case 主路径删除同步 busy-wait：

```text
CHANNEL_START
  -> PC 使用 CHANNEL_STATUS_GET / IRQ_RESULT_GET 做墙钟超时轮询
  -> 超时后执行明确 stop/reset recovery
```

`CHANNELS_START_WAIT_ORDER` 不应继续承担优先级证明，见 DMA-REV-009。若保留为诊断命令，必须：

- 设置很小且可计算的上限；
- PC timeout 明确大于 target 上限；
- timeout 返回独立、可诊断状态；
- 命令退出前恢复或报告真实 channel mask。

---

## DMA-REV-019：Channel Free 不是成功完成证据

**等级：P1**  
**状态：已确认**

ET6801 `AHBDMA_isChannelFree()` 只读取 `CHENREG` 对应通道位：

```text
CHEN bit == 0 -> true
```

该状态可能表示：

- 从未配置；
- 已配置但未启动；
- 正常完成后硬件关闭；
- 被 stop/disable 强制关闭；
- 总线错误或其他异常后关闭。

当前：

```text
et_dma_wrap_start_channel_and_wait()
et_dma_wrap_start_channels_wait_order()
wait_channel_free()
```

都把 channel free 作为主要终止条件。其中 `start_channel_and_wait()` 在看到 free 后直接返回 `ET_WRAP_STATUS_OK`，没有检查 ERROR、TRANSFER_DONE 或完整数据状态。

### 推荐优化

定义轻量的终态观测：

```text
channel disabled
AND error event == 0
AND expected terminal event present（需要 IRQ 的 Case）
AND 数据/端点结果满足 Case 断言
```

Wrap 的等待 helper 如继续存在，应返回结构化 terminal result，而不是只有 OK/TIMEOUT。

---

## DMA-REV-020：缺少通道 ownership 与完整 idle 基线

**等级：P1**  
**状态：已确认**

### 当前问题一：Free Channel 只代表未启用

`AHBDMA_findFreeChannel()` 同样只检查 CHEN 位。因此：

```text
configure(channel 0)
但尚未 start
  -> find_free_channel() 仍可能返回 channel 0
```

DMA Service 不保存 `configured_mask`、`owned_mask` 或 channel generation，无法阻止另一个流程覆盖已配置通道。

### 当前问题二：Deinit 不完整

`AHBDMA_deInitChannel()` 会重置主要地址、CTL、CFG 寄存器，但没有明确恢复：

- `SGR` / `DSR`；
- 该通道所有 interrupt mask；
- pending interrupt；
- software handshake request；
- Service 侧 managed/raw ownership。

因此“deconfigure 成功”不等于“回到唯一、可证明的空闲基线”。

### 推荐优化

使用固定 bitmap，不引入动态资源管理：

```c
uint32_t configured_mask;
uint32_t active_mask;
uint32_t recovery_required_mask;
```

统一内部函数：

```text
dma_channel_reset_to_idle(channel)
  -> stop（有界）
  -> disable/clear全部IRQ
  -> clear software request
  -> deinit全部通道寄存器
  -> 只有全部成功才清 configured/recovery bit
```

`find_free_channel()` 应返回“未被 Service 配置/占用”的通道，而不仅是 CHEN=0。

---

## DMA-REV-021：IRQ Manager 无法证明物理路由已释放

**等级：P1**  
**状态：已确认**

第一轮建议 DMA Service 在 `unbind` 失败时保留 route 状态并重试。第二轮检查发现，当前 Framework 契约本身不足：

`et_irq_manager_unbind()` 在找到 binding 后先清空 binding slot，然后调用：

```text
et_irq_wrap_disable()
et_irq_wrap_clear_pending()
et_irq_wrap_unregister()
```

但三个返回值都被忽略，函数仍返回成功。

结果：

- DMA Service 无法知道 NVIC/handler 是否真正关闭；
- binding 软件状态已删除，后续无法正常重试；
- 物理 IRQ 可能仍启用，但没有 callback binding；
- DMA 多路 route teardown 的正确性无法被 Service 层证明。

### 推荐优化

先修 Framework：

- unbind 必须在物理 teardown 成功后才最终删除最后一个 binding；
- 或保存“detached but cleanup pending”状态，允许幂等重试；
- 将 disable/clear/unregister 的失败传播给调用者；
- 增加 host/native fault-injection test。

DMA Service 的 IRQ 生命周期整改必须建立在该 checked-unbind 契约上，否则只修改 DMA 状态字段无法真正闭环。

---

## DMA-REV-022：Transfer Type 跨字段语义未校验

**等级：P1**  
**状态：已确认**

当前 Wrap 分别校验：

```text
transfer_type
source/destination address mode
source/destination interface
source/destination handshake mode/polarity
```

但没有校验它们之间的组合关系。

例如当前可接受：

```text
M2P + destination increment
P2M + source increment
P2P + source/destination increment
M2M + 任意 peripheral interface/handshake 组合
```

外设 endpoint 如果使用 increment/decrement，DMA 会继续访问相邻寄存器地址，可能写入控制寄存器或保留区。

### 推荐优化

在 PC Driver 和 Wrap 共享同一语义表：

| Transfer Type | Memory side | Peripheral side |
|---|---|---|
| M2M | 两端允许合法 memory address mode | 无 peripheral interface/handshake |
| M2P | Source 为 memory | Destination 必须 fixed，endpoint/interface/direction 匹配 |
| P2M | Destination 为 memory | Source 必须 fixed，endpoint/interface/direction 匹配 |
| P2P | 无 memory buffer | Source/Destination 都必须 fixed 且 endpoint 合法 |

PC 提前给出清晰错误；Wrap 必须重复关键安全校验，确保任何调用者都不能绕过。

---

## DMA-REV-023：Runtime 门禁与 Case 实例枚举不一致

**等级：P2**  
**状态：已确认**

当前同时存在两种路径：

```text
统一 fixture：
  Runtime Service -> Profile instance -> Bench role -> Driver

大量 P0/P1/P2 Case：
  framework.target_client -> DmaDriver(instance_id=0/1)
```

典型硬编码包括：

```python
for instance_id in range(2)
@pytest.mark.parametrize("instance_id", [0, 1])
for channel in range(8)
dma.start_channels(0xFF)
target_capabilities.instances("dma")[instance_id]
```

最后一种还把 tuple 下标误当作真实 controller ID；当 Runtime 只暴露 `dma1` 或实例顺序变化时，可能得到 IndexError 或错误实例。

### 推荐优化

不需要建立复杂 fixture graph，只增加一个稳定的 DMA instance descriptor：

```text
instance_id
instance_name
DmaDriver
static capability
runtime capability
channel_count
```

所有公共 Case 从该 descriptor 参数化；产品基线测试才断言 ET6801 必须有 dma0/dma1 和 8 通道。

---

## DMA-REV-024：Resource Reset 是全局破坏性操作

**等级：P2**  
**状态：已确认**

多个 DMA helper 在 Case 内调用：

```python
resource.reset()
```

Resource Service 只有一个全局固定池，reset 会使全部已分配 handle 失效，不区分当前 Case 或调用者。

当前测试串行运行时通常不会暴露问题，但未来以下场景会产生隐式破坏：

- 一个 Case 同时组合 DMA 与其他需要 Resource 的 IP；
- 并行 pytest worker；
- fixture 预先分配长生命周期缓冲区；
- cleanup 重试仍持有旧 handle。

### 推荐优化

短期明确 DMA hardware suite 串行执行，并把 reset 放到 Case/fixture 生命周期边界，不在普通 helper 内隐式执行。

长期 Resource Service 增加轻量 session/owner generation；DMA helper 只释放自己创建的资源。

---

## DMA-REV-025：缺少 DMA Service 行为级 native harness

**等级：P2**  
**状态：已确认**

当前 native 目录只有公共协议 vector harness。DMA 相关验证主要依赖：

- Python fake Driver；
- C 源码字符串/正则契约；
- 真实 HIL。

这些测试不能低成本覆盖：

```text
第 N 条 route bind 失败
unbind 失败
IRQ clear 期间 callback 插入
硬件 enable 成功但 route 失败
channel reset 第 N 步失败
Raw Mask 与 Managed Session 交叉
```

### 推荐优化

新增一个 DMA Service host harness，使用 fake DMA Wrap 和 fake IRQ Manager，静态数组记录调用顺序和故障点。重点验证状态转换和回滚，不模拟 DMA 数据搬运。

该 harness 应成为后续 DMA 生产代码整改的主要回归保护，而不是继续增加源码字符串断言。

---

## DMA-REV-026：Service 注册假设控制器编号连续

**等级：P2**  
**状态：已确认**

`et_services_register_all()` 对 UART 初始化失败使用 `continue`，对 DMA 初始化失败使用 `break`。

因此未来如果：

```text
DMA0 不存在 / 被裁剪
DMA1 存在
```

注册会在 DMA0 失败后直接结束，DMA1 永远不会暴露。

当前 ET6801 的 dma0/dma1 连续存在，因此不是当前硬件 Bug；但它违反跨芯片和裁剪 build 的扩展目标。

推荐按 board/chip instance list 注册，或至少失败后 `continue`，并由最终 `dma_count` 和产品基线检查决定是否接受。

---

# 5. 最终目标结构

## 5.1 DMA Service 保持轻量，但必须拥有状态

不建议把 DMA Service 拆成通用调度框架，也不建议引入动态对象。推荐固定状态：

```c
typedef struct {
    uint32_t configured_mask;
    uint32_t recovery_required_mask;
    uint32_t managed_irq_event_mask[ET_DMA_MAX_CHANNELS];
    uint32_t raw_irq_owner_mask;
    uint8_t controller_enabled;
    uint8_t route_bound_mask;
    uint8_t reserved[2];
} et_dma_service_state_t;
```

物理 IRQ route 应按 controller/event 绑定一次，callback 读取控制器级 channel bitmap，再按每通道 owned event 处理。不要继续为每次单通道 session 重复 bind/unbind 同一控制器物理 route。

## 5.2 IRQ Evidence 必须带通道身份

当前：

```text
latched_events + irq_count
```

不能支持多通道并发。推荐 v2 evidence：

```text
transfer_channel_mask
block_channel_mask
source_channel_mask
destination_channel_mask
error_channel_mask
callback_count
unexpected_count
ack_failure_count
counter_overflow_count
```

Wire v1 可暂时保留单通道兼容，但内部状态只允许一套。

## 5.3 生命周期使用一个 reset-to-idle owner

统一：

```text
channel configure failure
wait timeout
Case teardown
controller disable
software request cleanup
IRQ teardown
```

全部调用同一内部恢复路径。失败时保留 `recovery_required_mask`，禁止把未知状态通道重新报告为 free。

## 5.4 地址与端点使用受控引用

目标不是给测试平台增加安全产品级 ACL，而是防止普通 Case 错误破坏固件：

```text
Memory -> Resource handle + offset/span
Peripheral -> registered endpoint + interface + direction
LLI -> Resource handle + descriptor offset
```

ET6801 TCM alias 转换继续只放在芯片 Driver 内，不进入 PC Case 或通用 Service。

---

# 6. 最终整改优先级

## 第一批：必须先修的基础契约

1. Framework checked IRQ unbind 与短临界区能力。
2. DMA IRQ 单一所有权、Result Clear 写者串行化。
3. Managed IRQ 与 Raw Mask 互斥。
4. 地址跨度、LLI descriptor 和 peripheral endpoint 校验。
5. channel reset-to-idle 与 recovery-required 状态。

## 第二批：删除不可靠的通过条件

1. 非阻塞替代 `START_WAIT` 主路径。
2. completion 必须检查 ERROR/terminal event，而不只看 CHEN。
3. 重写 Suspend/Resume Case 的观测方法。
4. Priority Case 改为可证明的握手/观察器方法；当前 CHEN 轮询结论不得保留为正式 PASS。

## 第三批：跨芯片与维护性

1. Capability 驱动实例、通道、mask 和 limit。
2. Runtime Service/Profile/Bench/Feature 分层 gate。
3. DmaDriver command traits 与只读安全重试。
4. Wire contract 生成或至少单一 golden-vector 来源。
5. DMA 专项结果接入统一 CaseResult/evidence。

---

# 7. 代码整改前必须增加的测试

## Native/Host 行为测试

- Result clear 与 callback 交错不丢事件。
- 第 N 个 route bind 失败后，已绑定 route 完整回滚。
- checked-unbind 物理 disable/clear/unregister 任一步失败可重试。
- Managed Session 活动时 Raw Mask/Pending 返回 BUSY 且零副作用。
- configure、stop、deconfigure、reset 任一步失败时状态 bitmap 正确。
- increment span overflow、decrement underflow、地址 0、跨 Resource 边界全部拒绝。
- M2P/P2M/P2P 非 fixed peripheral address mode 拒绝。

## Python Unit

- 只读命令传入 `retry_safe=True`，mutating 命令不重试。
- channel mask 根据 runtime `channel_count` 生成，不固定 `0xFF`。
- sparse instance 列表不会使用 tuple 下标推断 controller ID。
- cleanup ledger 会尝试所有安全的恢复步骤并保留第一错误。
- 专项 JSON 写入当前 `case_run_id`，包含 firmware/profile/Git 基线关联。

## HIL

- 两个通道同时产生不同 IRQ event，通道身份不丢失。
- IRQ clear failure/重复 pending 不形成中断风暴。
- 超时后下一个 Case 可直接执行，无需整板复位。
- M2M、M2P、P2M、P2P 均验证 terminal error 为 0。
- LLI、Gather/Scatter、Software Handshake 清理后寄存器回到批准基线。

---

# 8. 最终复核结论

DMA 当前不是“功能完全不可用”，其基础分层、Wrap 隔离、外设 Pair 编排和现有 ET6801 HIL 资产都有较好基础。真正需要优先处理的是以下四个根因：

```text
IRQ 状态所有权不唯一
通道生命周期没有唯一 idle/recovery 状态
Raw address 与 transfer semantics 缺少安全边界
Case 使用硬编码和不可证明的时序观测
```

第二轮复核后，第一轮大多数结论成立；其中 Configure 事务和 Suspend Case 的严重度/表述已经修正，避免把结构性风险描述成当前必现 Bug。同时补充确认了同步等待阻塞控制平面、Channel Free 不是成功证据、IRQ Manager 无法传播物理 teardown 失败、普通 DMA 地址跨度未校验等更关键问题。

在这些问题整改前，不建议继续增加新的 DMA Feature Case。否则新增 Case 会建立在不稳定的 IRQ、生命周期和地址契约上，后续只能继续堆叠例外处理。
