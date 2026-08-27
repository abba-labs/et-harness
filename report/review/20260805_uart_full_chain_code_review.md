# UART 全链路代码评审与优化设计

文档状态：第二轮代码评审，持续更新  
评审时间：2026-08-05 15:44 CST  
评审基线：`main@b93fd5810b3ff18a979ce024ec3814d92e57e0ea`  
关联总评审：[平台代码评审记录](20260805_platform_code_review.md)  
当前限制：本轮结论来自静态代码贯通分析，尚未在评审环境重新执行 Keil 编译、pytest 全量回归或真实 HIL

> 本轮不是只找 UART 的局部 Bug，而是为后续代码整改确定一个可长期维护的实现方向。所有建议必须同时满足：遵守既定分层、可靠、轻量、边界清晰、可验证，并避免为解决一个问题引入新的通用框架或多套并行机制。

---

## 1. 本轮评审目标

本轮沿 UART 的真实调用链逐层检查：

```text
UART pytest Case
  -> UART fixture / Bench role
  -> PC UartDriver
  -> TargetClient / ET-Frame
  -> 固件 UART Service
  -> Framework IRQ Manager
  -> Common UART Wrap
  -> ET6801 UART SDK Driver / Test Driver Extension
  -> UART 硬件
  -> CaseResult / UART 专项结果 / HIL 报告
```

重点回答：

1. UART Service 是否只有一个清晰的硬件状态所有者。
2. Capture、普通 IRQ、DMA、FIFO、9-bit 和恢复流程能否安全组合。
3. PC Driver 的公开语义是否与固件和 Wrap 完全一致。
4. Case 是否真的验证了它声称验证的 Feature，而不是由轮询或 PC 本地校验产生假证据。
5. 后续新增芯片或 UART Feature 时，是否只需在正确层增加能力，不会继续堆叠条件分支和重复状态。
6. 后续整改应如何切分，才能既修复问题，又保持固件轻量化。

---

## 2. 当前 UART 分层总体评价

当前 UART 链路的主分层方向是正确的：

- Case 使用 fixture 提供的逻辑 UART handle，没有直接创建 `TargetClient` 或写死 UART0/UART1/UART2。
- PC `UartDriver` 使用稳定的 Wire Command，不直接访问寄存器。
- UART Service 只调用 UART Wrap 和公共 IRQ Manager，不直接包含 ET6801 SDK 类型。
- UART Wrap 集中完成逻辑实例到 `UART_Type/IRQn` 的映射和 SDK 状态归一。
- ET6801 SDK 的测试扩展被隔离在 `ET_ENABLE_TEST_DRIVER_EXTENSIONS` 下。
- UART P0-P3 已经采用“一个独立 Feature 一个 Case”的方向，并明确区分可执行、SKIP 和 deferred。

但当前实现已经出现三个会持续放大的结构性风险：

```text
一个物理 IRQ 被两个回调和两套掩码状态共同管理
一个 UART 运行状态被多条重叠命令分别修改
一个 Feature 是否可测被静态 Capability、Runtime flag 和 Bench 条件分散判断
```

如果直接在现有结构上继续增加 RS485、SIR、更多 IRQ 源、更多 DMA 模式，UART Service 会快速演变成难以证明正确的状态机。因此，后续修改应优先收敛“状态所有权”和“契约语义”，而不是继续新增命令。

---

## 3. 本轮问题摘要

| ID | 等级 | 状态 | 问题摘要 |
|---|---|---|---|
| REV-009 | P1 | 已确认 | Capture 与普通 IRQ 同时管理同一物理 IRQ 和同一组硬件中断位，存在互相关闭和失败后状态破坏 |
| REV-010 | P1 | 已确认 | `IRQ_STATE_GET` 会通过轮询硬件状态补写事件，配合当前 Case helper 可能把“未经过 ISR 的状态”当作 IRQ PASS |
| REV-011 | P1 | 已确认 | PC UART 行配置 API 存在 9-bit 范围和 1.5/2 stop bits 语义不一致，单元测试还固化了错误含义 |
| REV-012 | P1 | 已确认 | `DMA_ENABLE_SET`、`FIFO_CONFIG` 和 `DMA_MODE_SET` 重叠修改 DMA/FIFO，硬件状态与 Service 缓存可能分叉 |
| REV-013 | P1 | 已确认 | UART 重配置和清理不是事务化、幂等的；失败或超时后无法可靠回到唯一空闲基线 |
| REV-014 | P2 | 已确认 | UART Service 已形成 33 个命令的单一长分支，现有静态字符串测试无法覆盖真实状态转换 |
| REV-015 | P2 | 已确认 | 静态芯片 Capability、运行固件能力和 Bench 可达性尚未形成统一但分层的 Case 准入模型 |
| REV-016 | P2 | 已确认 | UART 非法参数 HIL Case 只验证 PC 本地 `ValueError`，没有验证固件 Service 的防御性校验 |

---

# 4. 详细问题

## REV-009：Capture 与普通 IRQ 的状态所有权冲突

**等级：P1**  
**状态：已确认**  
**影响范围：RX Ready、Character Timeout、Capture、IRQ Case、清理、后续更多 UART IRQ Feature**

### 4.1 当前实现

`et_uart_service_t` 同时保存两组 IRQ 状态：

```text
Capture 路径：
- capture_irq_bound
- capture_irq_enabled
- capture_irq_priority
- capture_irq_route
- uart_capture_irq()

普通事件路径：
- irq_bound
- irq_enabled
- irq_priority
- irq_route
- irq_enabled_mask
- uart_irq_event()
```

两条路径实际控制的是同一个 UART 物理 IRQ。

初始化时，Service 先绑定 `uart_capture_irq()`。当 PC 配置普通 UART IRQ 后，`uart_bind_event_before_capture()` 会：

```text
解绑 capture callback
  -> 绑定 event callback
  -> 再绑定 capture callback
```

这样依赖 `IRQ Manager` 当前“按 binding 数组顺序 dispatch”的内部行为，让事件回调先读取状态，再让 capture 回调读取 FIFO。

Capture 启动时直接执行：

```c
et_uart_wrap_enable_interrupts(
    &service->handle,
    ET_UART_WRAP_IRQ_RX_READY | ET_UART_WRAP_IRQ_RX_IDLE);
```

Capture 完成或取消时又直接关闭同一组位。

普通 `IRQ_CONFIG` 则独立维护 `irq_enabled_mask`，并独立开启或关闭相同硬件中断位。

### 4.2 确定性问题一：Capture 会关闭普通 IRQ 所拥有的位

假设普通 IRQ 已配置：

```text
RX_READY 或 CHARACTER_TIMEOUT 已使能
```

随后启动一次 Capture。Capture 完成时会无条件关闭：

```text
RX_READY + RX_IDLE
```

但 Service 的 `irq_enabled_mask` 仍然保留普通 IRQ 已使能的记录。

结果变成：

```text
软件状态：RX_READY 已启用
硬件 IER：RX_READY 已关闭
```

后续 Case 读取 `IRQ_STATE_GET` 会看到 enabled mask，但真实中断已经不会进入 ISR。

### 4.3 确定性问题二：Capture 进行中修改 IRQ 会先破坏旧状态，再返回 BUSY

`IRQ_CONFIG` 当前顺序是：

```text
计算 new_mask
  -> uart_irq_unbind(service)
  -> 修改 priority / 清 pending
  -> uart_bind_event_before_capture(service)
```

但 `uart_bind_event_before_capture()` 在 `capture_active != 0` 时直接失败。

因此，在 Capture 进行中调用 `IRQ_CONFIG` 时：

```text
旧 event binding 已经被解除
旧硬件 route events 已经被关闭
Service 的旧 mask 已经被清零
  -> helper 才发现 capture_active
  -> 返回 BUSY
```

这是典型的“先修改、后校验”。一次被拒绝的命令可能破坏正在工作的 Capture 和原有 IRQ 配置。

### 4.4 确定性问题三：正确性依赖 IRQ Manager 的内部槽位顺序

UART Service 要求 event callback 必须先于 capture callback 执行，但 `et_irq_manager_bind()` 的公共契约只描述绑定，不承诺回调优先级或稳定顺序。

当前实现恰好通过“先占用第一个空槽”达到顺序，但未来只要发生以下任一变化，就可能失效：

- IRQ Manager 改为压缩或重排 binding；
- 增加显式优先级排序；
- 绑定失败后槽位分布变化；
- 同一 IRQ 增加第三个观察者；
- Service 重构后 bind/unbind 顺序改变。

UART 的功能正确性不应依赖 Framework 未承诺的内部数组布局。

### 4.5 推荐优化：每个 UART 实例只保留一个 IRQ callback

建议不要继续修补双回调顺序，而是收敛为：

```text
一个物理 UART IRQ
  -> 一个 uart_irq_callback()
      1. 读取一次 Wrap interrupt snapshot
      2. 先锁存通用 IRQ 事实
      3. 再按 capture_active 决定是否读取 RX FIFO
      4. 统一清除该次 snapshot
```

Service 内维护两种“需求”，但只有一个“硬件应用掩码”：

```c
typedef struct {
    uint32_t configured_wire_mask; /* PC IRQ_CONFIG 声明的事件 */
    uint32_t capture_wrap_mask;    /* Capture 活动期间的内部需求 */
    uint32_t applied_wrap_mask;    /* 当前真实写入硬件的掩码 */
} et_uart_irq_control_t;
```

统一函数：

```text
uart_required_wrap_mask()
  = irq_wire_to_wrap(configured_wire_mask)
  | (capture_active ? CAPTURE_IRQ_EVENTS : 0)

uart_apply_irq_mask()
  = 对比 required 与 applied，只开启新增位、关闭不再需要的位
```

这样：

- Capture 完成只移除自己的内部需求，不会关闭普通 IRQ 仍需要的位；
- `IRQ_CONFIG` 只更新 configured mask，不需要重绑 callback；
- Capture 与普通 IRQ 不再拥有两套 route、priority 和 bind 状态；
- 不再依赖回调顺序；
- 后续增加可编程 TX Empty、9-bit address 等事件时仍只有一条状态路径。

### 4.6 轻量化边界

本问题不需要引入事件总线、RTOS、动态订阅或通用 Observer Framework。只需要：

- 一个 UART 私有 IRQ callback；
- 一个静态状态结构；
- 一个应用掩码函数；
- 一组针对状态转换的 native test。

### 4.7 验收条件

1. 配置 RX_READY 后执行多次 Capture，Capture 完成后 RX_READY 硬件使能仍保留。
2. Capture 进行中修改普通 IRQ：要么安全合并，要么在任何状态修改之前拒绝。
3. Capture cancel 不得清除普通 IRQ 的配置和硬件使能。
4. UART 每个实例在 IRQ Manager 中只存在一个 binding。
5. 单元测试覆盖 `IRQ -> Capture -> Complete -> IRQ` 和 `Capture -> IRQ_CONFIG` 两种顺序。
6. HIL 重新执行 RX Ready、Character Timeout 和至少两次连续 Capture。

---

## REV-010：IRQ 查询路径可能制造“未经 ISR 的中断证据”

**等级：P1**  
**状态：已确认**  
**影响范围：所有 UART IRQ Case、P1/P2 IRQ 结论、事件计数可信度**

### 4.8 当前 IRQ 事实来源不唯一

`uart_irq_event()` 在真正进入 Framework IRQ dispatch 后会：

- 读取 Wrap interrupt snapshot；
- 将事件写入 `irq_pending_mask` 和 `irq_active_mask`；
- 增加 `irq_event_count`；
- 锁存错误状态。

但 `ET_UART_COMMAND_IRQ_STATE_GET` 不是纯查询。它再次读取硬件：

```c
et_uart_wrap_get_interrupt_status(...);
current_mask = irq_wrap_to_wire(irq_status.interrupt_flags);
service->irq_pending_mask |= current_mask;
service->irq_active_mask = current_mask;
```

该路径：

- 没有要求该事件属于 `irq_enabled_mask`；
- 没有证明 Framework IRQ callback 曾执行；
- 没有增加 `irq_event_count`；
- 会改变 Service 保存的 pending/active 状态。

因此 `IRQ_STATE_GET` 同时承担了“读状态”和“补采样事件”两个职责。

### 4.9 当前 Case helper 放宽了 ISR 证据要求

`_require_irq_event()` 的逻辑是：

```text
如果 event_count 没有增加，但是 pending/active 中出现目标 source，仍可通过。
```

结合 `IRQ_STATE_GET` 的硬件轮询行为，会出现：

```text
硬件 IIR/LSR 暂时显示某 source
  -> IRQ_STATE_GET 把 source 写入 pending/active
  -> Framework ISR 可能根本没有执行
  -> event_count delta == 0
  -> Case 因 source_observed == true 仍然 PASS
```

这使“UART 事件状态可轮询”与“UART 中断已正确路由、进入 NVIC、经过 IRQ Manager、执行 Service callback”混成一个结论。

### 4.10 多字段快照也不是一致的

`irq_pending_mask`、`irq_active_mask`、`irq_event_count` 和 `irq_overflow_count` 由 ISR 与主循环共同访问。虽然单个 32-bit 访问在当前 32-bit CPU 上通常是原子的，但四个字段不是同一时刻快照。ISR 可以在响应编码过程中更新其中一部分，PC 得到跨时刻组合。

DMA Service 已经使用 `result_generation` 形成类似 seqlock 的一致快照，UART 没有采用同样机制。

### 4.11 推荐优化：区分“IRQ Delivery Evidence”和“Raw Hardware Status”

`IRQ_STATE_GET` 应改为纯读取 callback 已锁存的事实，不再访问硬件、不再修改状态：

```text
configured_mask
latched_event_mask
last_event_mask
callback_count
snapshot_overflow_count
```

如确实需要观察当前 IIR/LSR，应提供独立、明确命名的查询，例如：

```text
RAW_INTERRUPT_STATUS_GET
```

该命令只返回原始状态，不增加 callback count，也不得被 IRQ delivery Case 当作通过依据。

一致快照可复用 DMA 的轻量做法：

```text
ISR 更新前 generation++ 变奇数
更新字段
generation++ 变偶数

主循环读取 generation -> 字段 -> generation
前后相同且为偶数才返回
```

也可在非常短的字段复制区使用 IRQ critical section；两者选择其一，不要同时引入两套机制。

### 4.12 Case 判定规则

对于声称验证“中断链路”的 Case，通过条件必须同时满足：

```text
callback_count 增量 > 0
AND
latched_event_mask 包含目标 source
```

只验证轮询状态的 Case，应单独命名为 status/polling Feature，不使用 IRQ Case ID。

### 4.13 验收条件

1. 构造“硬件状态存在但 IRQ Manager 未 dispatch”的 native 场景，IRQ Case 必须失败。
2. 真正 dispatch 后，callback count 和 source mask 同时增加。
3. `IRQ_STATE_GET` 连续调用不改变任何事件字段。
4. ISR 在快照读取期间更新时，响应要么重试得到一致状态，要么返回 BUSY，不得返回跨时刻组合。
5. 更新 `_require_irq_event()`，IRQ delivery Case 必须要求 count 增量和 source 同时成立。
6. 重新执行 UART P1 全部 IRQ Case。

---

## REV-011：PC UART 行配置公开语义与固件实际语义不一致

**等级：P1**  
**状态：已确认**  
**影响范围：P0 line format matrix、跨芯片 Driver 契约、后续 9-bit Feature、错误参数处理**

### 4.14 公开 API 重叠

PC Driver 当前同时提供：

```python
initialize(..., data_bits: int, stop_bits: int, parity: int)
configure_extended(..., data_bits: int, stop_bits: UartStopBits, parity: UartParity)
```

两者最终都发送同一个 `INITIALIZE` Wire Command，但校验规则不同：

- `initialize()` 只检查参数能放进 uint8，不验证 UART 语义范围；
- `configure_extended()` 允许 `data_bits` 为 5 到 9；
- 固件 Wrap `et_uart_wrap_init()` 只接受 5 到 8 bit；
- 9-bit 实际由独立 `NINE_BIT_CONFIG` Feature 控制。

因此 `configure_extended(data_bits=9)` 会在 PC 端被接受，发送到 DUT 后才被拒绝。

### 4.15 Stop bits 枚举名称与 Wire 兼容值冲突

PC 定义：

```python
UartStopBits.ONE = 1
UartStopBits.ONE_AND_HALF = 2
UartStopBits.TWO = 3
```

Wrap 为兼容旧调用方，对 Wire 值 2 的解释是：

```text
data_bits == 5：1.5 stop bits
data_bits > 5：2 stop bits
```

这意味着：

```python
configure_extended(
    data_bits=7,
    stop_bits=UartStopBits.ONE_AND_HALF,
)
```

公开 API 表面声称配置 1.5 stop bits，实际硬件配置为 2 stop bits。

现有 `test_uart_driver.py` 还明确断言 7-bit + `ONE_AND_HALF` 编码为 Wire 值 2，等于把兼容编码固化成了错误的公开语义。

### 4.16 风险与影响

1. Case 报告中的帧格式与真实硬件格式不一致。
2. 新芯片若不需要旧值 2 兼容，将很难保持同一 PC API。
3. 9-bit 基础帧配置与 9-bit Feature 命令职责重叠。
4. 两个公开初始化入口会继续产生不同参数校验规则。
5. 后续再增加 RS485/SIR 配置时，容易继续复制“另一套 initialize”。

### 4.17 推荐优化：一个规范化的 Line Config 入口

PC 端保留一个正式公开语义：

```python
@dataclass(frozen=True)
class UartLineConfig:
    baudrate: int
    data_bits: int       # 5..8
    stop_bits: UartStopBits
    parity: UartParity
```

统一校验：

```text
5..8 bit：由 line config 管理
9-bit：只通过 nine_bit_config 管理
1.5 stop bits：只允许 data_bits == 5
2 stop bits：始终编码为 Wire 值 3
旧 Wire 值 2 + data_bits > 5：只在固件兼容解码保留，不作为新 PC API 输出
```

`initialize()` 可以接收 `UartLineConfig` 或明确的 typed 参数；`configure_extended()` 应删除、私有化或暂时保留为 deprecated 转发，但不能继续拥有另一套语义。

### 4.18 轻量化边界

不需要通用配置 DSL，也不需要为所有 IP 引入 dataclass 框架。这里只增加一个 UART 私有的不可变配置对象和一个校验函数，消除两个入口。

### 4.19 验收条件

1. `data_bits=9` 在发送请求前被 PC 明确拒绝，并提示使用 `nine_bit_config()`。
2. `data_bits=7 + 1.5 stop bits` 在 PC 端拒绝。
3. `data_bits=7 + 2 stop bits` 固定发送 Wire 值 3。
4. `data_bits=5 + 1.5 stop bits` 固定发送 Wire 值 2。
5. 单元测试以真实语义断言，不再断言错误兼容行为。
6. P0 line format matrix 的报告字段与实际 Wire 编码一致。

---

## REV-012：UART DMA/FIFO 存在多个重叠配置入口和两套状态

**等级：P1**  
**状态：已确认**  
**影响范围：UART DMA P2、DMA 外设 Pair、FIFO 阈值、恢复与清理、后续芯片适配**

### 4.20 当前存在三条配置路径

#### 路径 A：`DMA_ENABLE_SET`

Service 调用：

```c
et_uart_wrap_set_dma_enabled(service->uart_id, enabled)
```

Wrap 不使用当前 handle，而是通过逻辑 `uart_id` 找到外设，直接执行：

```text
enabled = true  -> MULTI DMA + TX threshold 8 + RX threshold 1
enabled = false -> DMA DISABLE + TX threshold 8 + RX threshold 1
```

#### 路径 B：`FIFO_CONFIG`

Service 先调用 `et_uart_wrap_configure_fifo()`，再调用 `et_uart_wrap_set_dma_mode()`，并更新：

```text
service->fifo_tx_threshold
service->fifo_rx_threshold
service->dma_mode
```

#### 路径 C：`DMA_MODE_SET`

Service 使用缓存的 FIFO threshold 调用 `et_uart_wrap_set_dma_mode()`，然后更新 `service->dma_mode`。

### 4.21 硬件与 Service 缓存可分叉

`DMA_ENABLE_SET` 修改了真实硬件 DMA/FIFO 配置，但没有更新 Service 的：

```text
dma_mode
fifo_tx_threshold
fifo_rx_threshold
```

例如：

```text
FIFO_CONFIG: tx=2, rx=4, dma=single
  -> Service cache = 2/4/single

DMA_ENABLE_SET(true)
  -> 硬件 = 8/1/multi
  -> Service cache 仍为 2/4/single

DMA_MODE_SET(disabled)
  -> 使用缓存 2/4 写回硬件
```

同一个 UART 的最终配置取决于命令历史，而不是一个可查询、可证明的状态模型。

### 4.22 API 边界也不一致

`DMA_ENABLE_SET` 只接收 `uart_id`，绕过 handle 生命周期；其他配置都以初始化后的 handle 为边界。以后新芯片若需要每个实例的私有状态或锁，绕过 handle 的入口会成为特殊例外。

### 4.23 推荐优化：一个 FIFO/DMA 配置状态和一个应用函数

Service 内建立唯一状态：

```c
typedef struct {
    uint8_t fifo_enabled;
    uint8_t tx_threshold;
    uint8_t rx_threshold;
    uint8_t dma_mode;
} et_uart_fifo_dma_state_t;
```

所有命令最终进入一个事务函数：

```text
uart_apply_fifo_dma_state(service, proposed_state)
  1. 完整校验 proposed state
  2. 调用 Wrap 应用
  3. 成功后一次性提交 Service state
  4. 失败时保留旧 state 或回到明确 idle，不产生半提交
```

`DMA_ENABLE_SET` 若暂时必须兼容旧 PC，可实现为薄适配：

```text
enabled -> proposed_state.dma_mode = MULTI
false   -> proposed_state.dma_mode = DISABLED
阈值保持当前 state，不再硬编码重置为 8/1
```

后续正式代码只使用 `DMA_MODE_SET/FIFO_CONFIG` 的规范语义。兼容命令应标记为 legacy，不再扩展。

Wrap 层也应删除或内部化绕过 handle 的 `et_uart_wrap_set_dma_enabled(uart_id, ...)`，统一通过 handle 修改外设。

### 4.24 验收条件

1. 任意顺序组合 `FIFO_CONFIG`、`DMA_ENABLE_SET`、`DMA_MODE_SET` 后，读回状态与 Service 缓存一致。
2. 失败的配置不改变旧硬件状态和缓存状态。
3. UART DMA Pair 的 open/close 不再依赖绕过 handle 的特殊函数。
4. 清理后统一恢复 `fifo enabled + tx0 + rx1 + DMA disabled` 或设计明确的唯一默认值。
5. 增加命令序列单元测试和一次 UART TX/RX DMA HIL。

---

## REV-013：UART 生命周期与清理不具备事务性和幂等性

**等级：P1**  
**状态：已确认**  
**影响范围：失败恢复、协议超时、Case teardown、连续回归、后续远程自动化**

### 4.25 重配置先销毁旧配置，再尝试新配置

`handle_initialize()` 的顺序是：

```text
如果已经 initialized
  -> uart_release_handle()
  -> 构造新 config
  -> et_uart_wrap_init()
  -> 获取 IRQ route
  -> bind capture callback
  -> initialized = 1
```

请求长度和 reserved byte 在释放前检查，但波特率、data bits、stop bits、parity 等语义由 Wrap 在旧 handle 已释放后才校验。

因此一个非法或不受支持的新配置，会先摧毁原本工作的 UART，再返回错误。命令拒绝不是无副作用的。

### 4.26 Deinitialize 没有定义唯一硬件空闲基线

`et_uart_wrap_deinit()` 当前：

- 关闭部分中断源；
- 清零 opaque handle；
- 不显式执行 UART peripheral reset；
- 不统一恢复 loopback、break、halt、9-bit、flow control、FIFO direct access、DMA/FIFO 配置等所有 Feature。

Service 尝试在 `uart_release_handle()` 前调用多个清理动作，但一旦状态在超时或中间失败后与缓存不一致，就不能证明所有硬件位都已恢复。

### 4.27 Cleanup helper 名义幂等，协议行为并不幂等

`cleanup_uart()` 对每个 handle 依次调用：

```text
capture_cancel
break false
halt false
loopback false
nine-bit false
flow-control false
dma mode disabled
deinitialize
```

但 Service 的多数命令在 `initialized == 0` 时返回 `INVALID_PARAM`，`DEINITIALIZE` 也拒绝重复调用。

因此：

```text
重复 cleanup
初始化失败后的 cleanup
命令已经在 DUT 执行但 PC 因超时未收到响应后的 cleanup
```

都可能产生一串 TargetRejected，并把恢复问题与原始失败混在一起。

### 4.28 远程协议要求清理必须能处理“执行状态不确定”

TargetClient 对修改命令默认不重试，这是正确的，因为超时后无法确定命令是否已经执行。但这同时要求恢复命令必须是安全、幂等的，否则 PC 无法从不确定状态恢复。

当前 UART 清理依赖 PC 对 Service 状态的准确假设，与远程自动化的故障模型不匹配。

### 4.29 推荐优化：一个 `reset_to_idle`，一条生命周期主线

建议定义 UART Service 的唯一空闲基线：

```text
未初始化
无 IRQ binding
无 active capture
所有 UART 中断源关闭
DMA disabled
FIFO/threshold 为设计默认
loopback/break/halt/9-bit/flow/FAR 关闭
UART peripheral 已 reset
Service counters/state 清零
```

实现一个私有、可重复调用的：

```text
uart_reset_to_idle(service)
```

所有路径复用它：

- `DEINITIALIZE`
- 初始化失败回滚
- 软件复位后的 Service 状态同步
- Case teardown
- 未来 session reset

推荐生命周期：

```text
INITIALIZE
  1. 在不修改硬件的情况下完整校验请求
  2. reset_to_idle()
  3. 应用新配置
  4. 建立唯一 IRQ binding
  5. 成功后提交 initialized
  6. 任一步失败再次 reset_to_idle()
```

`DEINITIALIZE` 在已经 idle 时也返回 OK，使恢复操作真正幂等。

PC `cleanup_uart()` 可从八个 Feature 关闭命令收敛为一次 `deinitialize/reset_to_idle`。只有需要保存 Feature 恢复证据的 Case 才显式逐项关闭。

### 4.30 轻量化边界

不引入通用状态机库。使用一个小型枚举或布尔状态、一个私有 reset helper 和清晰的提交顺序即可。

### 4.31 验收条件

1. 连续调用两次 `DEINITIALIZE` 都返回 OK。
2. 对已初始化实例提交非法重配置后，实例处于文档规定状态；推荐回到 idle，不留下半配置。
3. 在 init 的 Wrap config、IRQ route、IRQ bind 三个步骤分别注入失败，最终都无 binding、无 active capture、无中断使能。
4. 模拟 PC 响应超时后执行 deinitialize，能够安全恢复。
5. 连续执行 UART P0-P2 全集，前一个 Case 的失败不会污染后一个 Case。

---

## REV-014：UART Service 长分支和静态源码测试不足以证明状态机正确

**等级：P2**  
**状态：已确认**  
**影响范围：维护成本、Review 可读性、命令扩展、回归门禁**

### 4.32 当前复杂度

UART Service 当前包含 33 个 Command，全部进入同一个 `uart_handle()` 长 `if` 链。该文件还同时包含：

- Wire 编解码；
- Capture 状态机；
- IRQ callback 和回调重排；
- FIFO/DMA 缓存；
- 9-bit 临时缓冲；
- Modem、Busy Detect、Shadow、Direct FIFO 等高级 Feature；
- 生命周期和清理。

问题不是单纯“文件太长”，而是多个状态域在同一函数中通过分支隐式耦合。新增一个 Feature 时，很难系统检查它与 Capture、IRQ、DMA 和 reset 的交互。

### 4.33 当前测试主要检查源代码形状

`test_uart_firmware_contract.py` 和 `test_uart_cases_contract.py` 做了很多有价值的规则门禁，例如：

- Command ID 是否存在；
- Service 是否只调用 Wrap；
- Case 是否写中文说明；
- Case 是否写死芯片、实例或接插件；
- 某些关键字符串和调用顺序是否存在。

但静态字符串/正则无法发现：

- Capture 完成关闭了普通 IRQ；
- IRQ_CONFIG 返回 BUSY 前已经破坏旧状态；
- DMA_ENABLE_SET 与缓存分叉；
- 初始化失败没有完整回滚；
- 多字段快照不一致。

这些都是状态转换问题，必须执行代码才能验证。

### 4.34 推荐优化：小型命令描述表 + 分组 handler

不要为 33 个命令建立 33 个文件，也不要引入动态注册框架。建议在 UART Service 私有实现中使用静态描述表：

```c
typedef struct {
    uint16_t command_id;
    uint16_t request_min;
    uint16_t request_max;
    uint16_t response_size;
    uint16_t flags;
    et_uart_command_handler_t handler;
} et_uart_command_descriptor_t;
```

按职责只拆成少量分组：

```text
uart_service_lifecycle.c   # init/deinit/reset/capabilities
uart_service_io.c          # read/write/exchange/capture
uart_service_irq.c         # IRQ config/state/callback
uart_service_features.c    # FIFO/DMA/9-bit/modem/shadow/direct FIFO
```

也可以暂时保留一个 `.c` 文件，但先把每条命令抽成静态 handler 并由描述表分发。核心目标是：

- 参数长度和 response size 有统一入口；
- 每个 handler 只操作一个明确状态域；
- 公共前置条件不重复；
- 可在 native harness 中单独调用。

### 4.35 推荐行为测试

建立一个轻量 native C harness，用 fake UART Wrap 和 fake IRQ Manager 驱动真实 UART Service：

```text
- init 成功/失败回滚
- capture + configured IRQ 掩码合并
- capture complete/cancel
- IRQ callback 锁存和一致快照
- 重复 deinit
- FIFO/DMA 命令序列
- malformed body / response capacity
- 每个 mutating command 的失败后状态
```

PC Python 测试继续负责 Wire codec 和 Driver 参数语义。HIL 只验证真实硬件行为，不承担所有状态机分支覆盖。

### 4.36 验收条件

1. `uart_handle()` 不再包含 33 段重复长度/状态判断的长链。
2. Command 描述表成为 request/response 大小的单一代码事实来源。
3. native test 能在无板环境执行真实 UART Service 状态转换。
4. 静态规则测试继续保留，但不再被当作行为测试替代品。
5. 新增一个 UART Command 时，必须同时增加描述、PC codec 和行为测试。

---

## REV-015：静态 Capability、Runtime 实现和 Bench 可达性尚未形成清晰的三层准入

**等级：P2**  
**状态：已确认**  
**影响范围：SKIP 分类、新芯片接入、Feature 复用、Capability 架构一致性**

### 4.37 当前三类事实来自不同位置

#### 静态芯片语义

`profiles/chip_capabilities/et6801/ip/uart.yaml` 来自 SVD，包含：

- UART0..UART7 实例；
- RS485 Feature；
- IRQ；
- base address、component identity 等 Evidence。

#### Runtime Service 实现

`CAPABILITIES_GET` 由 UART Wrap 返回 Feature flags，例如：

- RX/TX polling；
- IRQ；
- DMA；
- FIFO；
- loopback；
- 9-bit；
- modem；
- shadow/direct FIFO。

#### Bench 可达性

Bench 定义：

- control/dut/peer role；
- 实际交叉连接；
- DMA request interface；
- 波特率和帧格式。

RS485 收发器、SIR、绝对时序观察器等则尚未声明。

### 4.38 当前 `intersect_runtime_capabilities()` 只过滤实例

该函数名称容易让上层误以为已经完成静态与运行时 Feature 的交集，但实际只做：

```text
Service Registry 中有 uart1/uart2
  -> 从生成 Profile 中保留 uart1/uart2
```

它没有把 Runtime Feature flag 合并进 Profile，也不应在没有 Evidence 模型的情况下静默合并。

当前 Case 有时检查 Runtime flag，有时依赖 fixture，有时用 deferred，准入规则分散。

### 4.39 推荐优化：保持三层独立，但提供一个统一 Gate 结果

不要把三类事实压进一个巨大的 Capability YAML。设计上应继续保持：

```text
Chip Capability：硅片语义上有什么
Runtime Capability：当前固件实现并注册了什么
Bench Capability：当前物理环境能够刺激/观测什么
```

在 Scheduling/Profile 层提供一个轻量 Gate helper：

```python
require_case_capability(
    chip=...,
    runtime=...,
    bench=...,
    requirement=...,
)
```

返回或抛出稳定分类：

```text
skip_by_chip_capability
skip_by_runtime_service
skip_by_runtime_feature
blocked_by_bench
blocked_by_observer
```

同时重命名容易误导的对象：

```text
intersect_runtime_capabilities
  -> filter_profile_instances_by_registry

target_capabilities
  -> target_static_capabilities（或 chip_capabilities）
```

Runtime Feature 可由每个 IP Driver 的 capability object 单独提供，不写回生成 YAML。

### 4.40 Case 规则

- Case 不直接拼接三种判断。
- fixture 只提供事实和准入，不执行测试动作。
- Test Case 仍拥有完整测试步骤和最终断言。
- SKIP 必须明确是哪一层缺失，不能统一写成 `feature unavailable`。

### 4.41 验收条件

1. 一个 Feature 缺失时，结果能明确区分芯片不支持、固件未实现、Service 未注册或 Bench 无法观测。
2. 新芯片接入只新增 Profile/映射，不修改公共 UART Case 的芯片分支。
3. Runtime Feature 不污染 SVD 生成的 Evidence Profile。
4. UART deferred/skip 统计能够按阻塞层分类汇总。

---

## REV-016：非法参数 Case 只验证 PC 本地校验，没有验证 DUT 防御边界

**等级：P2**  
**状态：已确认**  
**影响范围：Service 参数校验、恶意/损坏帧防御、错误后状态保持、测试结论准确性**

### 4.42 当前 P0-008 实际验证内容

`test_uart_p0_008_invalid_parameter_rejection` 提交的操作包括：

```text
baudrate=0
data_bits=4
stop_bits=0
empty write
read length=0
capture length=0
invalid FIFO threshold
```

这些全部在 PC `UartDriver` 内抛出 `ValueError`，请求没有发送到 Target。

因此该 Case 实际证明的是：

```text
PC Python API 会拒绝部分非法调用
```

它没有证明：

- UART Service 会拒绝 malformed body；
- reserved byte 非零时会拒绝；
- Wrap 会拒绝非法枚举；
- 被拒绝命令不会改变已初始化状态；
- 固件在损坏帧之后仍可恢复通信。

### 4.43 为什么不能直接让普通 Case 绕过 Driver

公共 UART Case 按架构不应直接拼 Wire body 或调用低层 TargetClient，否则每个 IP 都会开始在 Test Case 中增加协议逃生口，破坏 Driver 边界。

### 4.44 推荐优化：把负向契约分成三层测试

#### PC Driver unit

验证：

```text
非法 Python 参数 -> ValueError
且 Target.request 调用次数不增加
```

#### Firmware native Service contract

用 fake Wrap 调真实 Service，验证：

```text
malformed request/reserved byte/非法枚举
  -> INVALID_PARAM 或 NOT_SUPPORTED
  -> fake Wrap 未被调用或只发生允许调用
  -> Service 状态保持不变
```

#### 可选 HIL 协议健壮性

放在 `framework_validation/integration` 或专门的协议 fault smoke 中，通过受控低层探针发送损坏 Service body，验证固件拒绝并恢复。它不是普通 UART Feature Case，也不向业务 Case 暴露 raw command API。

### 4.45 验收条件

1. P0-008 的名称和说明准确表述为 PC API 参数校验，或将其移到 Driver unit。
2. UART Service 每个命令组至少有 malformed body native test。
3. 非法重配置后 Service 生命周期状态符合 REV-013 的事务规则。
4. 可选 HIL fault probe 后，HELLO/ECHO 和合法 UART loopback 仍能执行。

---

# 5. 推荐的 UART 目标实现

整改后，UART 固件不需要更复杂，而应变得更单一：

```text
┌─────────────────────────────────────────────────────┐
│ UART Service                                        │
│                                                     │
│  Lifecycle state ── uart_reset_to_idle()            │
│                                                     │
│  FIFO/DMA state ── uart_apply_fifo_dma_state()      │
│                                                     │
│  IRQ control ───── uart_apply_irq_mask()            │
│       │                                             │
│       └── one uart_irq_callback()                    │
│             ├── latch event evidence                │
│             └── drain capture when active           │
│                                                     │
│  Command descriptor table                           │
│       └── small grouped handlers                    │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
              Common UART Wrap
                       │
                       ▼
              ET6801 UART SDK
```

关键规则：

1. 一个硬件状态只能有一个 Service 私有所有者。
2. 一个物理 IRQ 只绑定一个 callback。
3. 查询命令不改变状态。
4. 配置命令先校验、再应用、最后提交软件状态。
5. 清理命令必须幂等。
6. Wrap 只做稳定语义到 SDK 的映射，不保存应用状态。
7. Chip Capability、Runtime Feature 和 Bench Reachability 不混成一个配置文件。
8. 不新增 RTOS、动态内存、运行时插件、事件总线或通用工作流引擎。

---

# 6. 后续代码修改顺序

## 阶段 A：先修复会产生错误结论的链路

### A1. 修复 REV-001

文件：

```text
pc/et_test_platform/scheduling/fixtures.py
framework_validation/unit/test_uart_fixtures.py
```

目标：控制 UART 只验证 role，不要求注册普通 UART Service。

### A2. 修复 REV-010

文件：

```text
firmware/services/src/et_uart_service.c
firmware/services/include/et_uart_service.h
pc/et_test_platform/test_cases/uart/uart_helpers.py
framework_validation/unit/test_uart_*irq*
```

目标：IRQ Case 只使用 ISR callback 事实。

### A3. 修复 REV-009

文件：

```text
firmware/services/src/et_uart_service.c
firmware/services/include/et_uart_service.h
framework_validation/native/...
```

目标：一个 callback、一个硬件 mask 所有者。

## 阶段 B：收敛配置和生命周期

### B1. 修复 REV-013

建立 `uart_reset_to_idle()` 和幂等 deinitialize。

### B2. 修复 REV-012

统一 FIFO/DMA state，兼容命令只做薄转发。

### B3. 修复 REV-011

PC 端只保留一个规范 line config 入口，修复 stop bits 和 9-bit 语义。

## 阶段 C：建立长期门禁

### C1. 修复 REV-014

增加 command descriptor 和 native behavior harness。

### C2. 修复 REV-015

建立三层 capability gate 和稳定 SKIP 分类。

### C3. 修复 REV-016

分离 PC 参数单元测试、固件 malformed command 测试和可选 HIL fault probe。

---

# 7. 修改时必须遵守的范围控制

为避免后续越来越乱，本轮整改禁止顺手引入以下内容：

- 不创建“所有 IP 通用”的大型状态机框架。
- 不为每个 UART Command 建一个文件或一个类。
- 不把 UART Feature 判断写入 TargetClient 或 ET-Frame。
- 不让 Test Case 直接构造 Wire body。
- 不让 Wrap 调 GPIO、CRG、NVIC 或其他 IP；跨 IP 顺序仍由 Application/Test Case 负责。
- 不把 Bench 连接写入 Chip Capability。
- 不为了兼容旧命令保留两套长期公开语义；兼容入口只能薄转发，并明确删除边界。
- 不用历史 HIL PASS 替代整改后的重新验证。

---

# 8. 验证矩阵

| 层级 | 必须验证的内容 | 是否需要硬件 |
|---|---|---|
| Python Driver unit | line config、Wire codec、response size、retry trait、PC 参数拒绝 | 否 |
| Firmware native unit | Service 生命周期、IRQ/Capture 交互、FIFO/DMA 状态、malformed body、失败回滚 | 否 |
| Static contract | 分层边界、禁止 SDK 泄漏、Case 不写死芯片/实例 | 否 |
| Protocol integration | C/Python golden vector、重复请求、超时后清理 | 否/可选 |
| Keil build | FPGA ITCM、Silicon Flash 两个 Target | 否（需要工具链） |
| HIL smoke | HELLO、Service Registry、UART internal loopback、UART1/2 pair | 是 |
| HIL IRQ | RX、TX、timeout、error、9-bit address | 是 |
| HIL DMA | UART TX DMA、RX DMA、full duplex | 是 |
| 连续回归 | P0-P3 顺序执行，失败注入后继续下一 Case | 是 |

任何一项没有实际执行时，只能标记“代码分析完成”或“测试待执行”，不能写成 PASS。

---

# 9. 本轮结论

UART 当前不是整体架构方向错误，而是已经到了必须收敛状态所有权的节点。最关键的不是拆更多层，而是减少并行机制：

```text
双 IRQ callback      -> 单 callback
两套 IRQ mask        -> 单一 applied mask
三条 DMA/FIFO 路径   -> 单一状态与应用函数
多个初始化语义       -> 单一 Line Config
多步非幂等 cleanup   -> 单一 reset_to_idle
源码字符串测试       -> 静态规则 + native 行为测试
分散 capability 判断 -> 三层事实 + 统一 gate
```

按照该方向修改，既能解决当前可靠性问题，也能让后续 UART Feature 和新芯片接入继续遵守现有总体架构，而不需要增加重量级基础设施。

---

## 10. 更新记录

| 时间 | 基线 | 内容 |
|---|---|---|
| 2026-08-05 15:44 CST | `b93fd5810b3ff18a979ce024ec3814d92e57e0ea` | 完成 UART 全链路第二轮静态评审；新增 REV-009 至 REV-016，并给出轻量化目标实现、修改顺序和验证矩阵 |
