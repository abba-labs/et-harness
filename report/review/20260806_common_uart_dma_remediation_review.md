# 公共层、UART 与 DMA 整改完成 Review

文档状态：代码级整改、联合回归与二次人工 Review 完成；Keil 与真实 HIL 待执行  
整改日期：2026-08-06  
整改分支：`codex/common-uart-dma-fixes-20260806`  
验证代码提交：`6f7c04a8bd678c8f8607cd5d52928293bd18ffbb`  
验证运行：GitHub Actions Run `31058445204`，Job `92480975665`  
关联审查：[公共层、UART 与 DMA 架构一致性复核](20260805_common_uart_dma_architecture_re_review.md)

> 本文中的“已关闭”表示生产代码、单元/契约测试、Native C Harness、Host C 语法检查和人工 Review 已闭环。本文没有把未执行的 Keil 构建和真实硬件行为写成 PASS。

---

## 1. 整改约束

本轮没有重新设计平台，严格沿用已经冻结的架构边界：

1. PC Test Case 是跨 IP 流程和最终 PASS/FAIL 的唯一所有者。
2. Firmware Service 只执行本 IP 的原子操作并返回事实，不编排完整测试场景。
3. Framework、ET-Frame、IRQ Manager、Capability、Result 和公共 Resource 机制保持芯片/IP 中立。
4. 一个 IP Wrap 只封装一个 IP；禁止 `SYSCTRL Wrap -> UART Wrap` 等跨 IP Wrap 调用。
5. Control UART 保持 Application Transport，不暴露为可重配置 UART Test Service。
6. UART Service 继续保持一个 `.c` 文件，并使用既定分区注释组织代码。
7. 不引入 RTOS、动态内存、事件总线、通用 Observer、插件系统或通用状态机框架。
8. 长操作的 deadline、轮询、取消和最终判断放在 PC；Firmware 命令保持有界。
9. DMA 地址安全不得退化为任意裸地址访问；外设端点必须经过可信发布、路由绑定和 Lease。
10. 无效参数继续以 PC 单元测试和协议契约为主，不扩大为普通 HIL 畸形输入测试。

最终依赖方向保持为：

```text
PC Case
  -> PC IP Driver
  -> TargetClient / ET-Frame
  -> Firmware IP Service
  -> 本 IP Wrap
  -> Chip Driver
```

DMA 外设链路的最终组合为：

```text
UART Service --publish--> Common DMA Endpoint Registry
PC Case       --configure--> SYSCTRL Service -> SYSCTRL Wrap
DMA Service  --validate/acquire--> Common DMA Endpoint Registry
DMA Service  -> DMA Wrap
```

这里的 Common Registry 是固定容量静态表，只保存可信端点身份、Route 事实和 Lease 计数；它不配置硬件、不编排 Case，也不形成通用资源图。

---

## 2. 问题闭环总表

| ID | 状态 | 最终整改 |
|---|---|---|
| COM-P1-001 | 已关闭 | Frame Parser 在重同步后保留已缓存合法帧和后续字节；增加 Native 连续坏帧恢复测试。 |
| COM-P1-002 | 已关闭 | Protocol 保留未消费 RX Chunk；Pending Response 完整发送前停止解析后续请求，单一 `tx_frame` Owner 不再被覆盖。 |
| COM-P1-003 | 已关闭 | Control UART RX Idle 通过短临界区原子读取并清零；共享标志显式声明为 ISR 状态。 |
| COM-P1-004 | 已关闭 | `framework_communication` 自动登记 DUT evidence，Peer Fixture 自动登记 Peer evidence；DMA Feature JSON 改为 measurement，不再拥有第二个最终 `status`。 |
| COM-P2-001 | 已关闭 | Service 返回非法长度或响应编码失败时生成最小 `INTERNAL_ERROR` 响应，而不是静默超时。 |
| COM-P2-002 | 已关闭 | IRQ Manager 增加对称 deactivate；Runtime init 失败会回滚 active manager，并提供 Runtime deinit。 |
| COM-P2-003 | 已关闭 | Control UART 明确只支持 TX Polling；拒绝 TX IRQ/DMA，避免 ISR 与 Poll 两个消费者修改同一 TX Ring。 |
| UART-P1-001 | 已关闭 | WRITE/READ/9-bit/EXCHANGE 改为 Firmware 单次有界操作，deadline 与多次提交/读取移到 PC；RX flush 增加固定上限。 |
| UART-P1-002 | 已关闭 | FIFO enable、threshold 和 DMA mode 每次都完整 apply；DISABLED/SINGLE/MULTI 均显式写硬件，失败使用旧状态回滚。 |
| UART-P1-003 | 已关闭 | Wire `1/2/3` 分别固定为 1 stop、5-bit 1.5 stop、6–8-bit 2 stop；历史整数兼容只保留在 PC API。 |
| UART-P1-004 | 已关闭 | Capture/Mask 共享状态使用短临界区；新增 `irq_fault_count`，Snapshot/Clear/Mask 失败进入 PC 可查询证据。 |
| UART-P2-001 | 已关闭 | UART Wrap Deinit 显式关闭并清理 Busy Detect，再执行软件复位。 |
| DMA-P1-001 | 已关闭 | DMA Service 删除 SYSCTRL Wrap 依赖，只使用 DMA Wrap、IRQ Manager 和公共 Endpoint/Resource 接口。 |
| DMA-P1-002 | 已关闭 | SYSCTRL Wrap 删除 UART Wrap 依赖，只执行 DMAMUX 原子配置与释放。 |
| DMA-P1-003 | 已关闭 | Managed IRQ Enable 要求 `active_channels == 0`，固定顺序为 configure -> irq_enable -> start。 |
| DMA-P2-001 | 已关闭 | PC `start_wait()` 在 ERROR/timeout 路径 best-effort stop；清理失败通过异常链保留，不覆盖原始错误。 |
| DMA-P2-002 | 接受设计 | Resource Pool 继续使用全局 Lease。当前测试串行、可靠优先，不提前升级为按 Handle 资源图。 |

本轮原审查中的 **11 项 P1 均已完成代码级关闭**。6 项 P2 中，5 项完成整改，1 项是经过 Review 接受的保守设计，不属于遗留缺陷。

---

## 3. 公共通信层 Review

### 3.1 Frame Parser 重同步

整改后 Parser 增加三个明确动作：

```text
parser_rebuild_expected()
parser_resync()
parser_consume()
```

关键语义：

1. 坏帧内找到新的 `ET` Magic 后，将剩余数据前移；
2. 如果新 Header 已完整，立即重建 `expected_length`；
3. 如果新合法帧已经完整缓存，本次调用即可输出；
4. 输出一帧后只消费该帧长度，保留其后的字节；
5. 下一帧首字节不会因 Parser 清零而被吞掉。

新增 Native Harness 实际构造：

```text
CRC 损坏外层帧
  + Payload 内嵌完整合法帧
  + 紧邻第三个合法帧
```

结果要求内嵌帧和第三帧均被完整解析且序号正确。

### 3.2 Pending Response 单一所有者

`et_protocol_t` 增加固定的 RX Chunk Offset/Length，不增加动态 Buffer。

最终行为：

```text
读取一个 RX Chunk
  -> 解析第一个请求
  -> 生成 encoded response
  -> 若 response 尚未全部写出，停止消费当前 Chunk
  -> 后续 poll 先继续发送同一 response
  -> response 完成后，再从原 Chunk offset 继续解析
```

这样保证：

- `tx_frame` 在完整发送前不会被第二个请求覆盖；
- duplicate replay metadata 与 encoded response 始终对应；
- 不需要消息队列、线程或新的异步框架；
- 正常单 outstanding `TargetClient` 行为不变。

Native Harness 将两个请求放入同一 RX Chunk，并把每次 TX 写入限制为 3 字节，验证：

- 第二个 Service 调用只能发生在第一响应完整发送之后；
- 两个响应均可重新解析；
- 响应序号顺序为 11、12；
- Service 各执行一次。

### 3.3 Response Fallback

公共 Protocol 在以下异常下不再直接丢弃响应：

- Service 返回的 `body_length` 超过 response capacity；
- 正常响应 Message 编码失败。

Protocol 会清空响应 Body，生成同 Service/Command/Instance 的 `ET_STATUS_INTERNAL_ERROR` 最小响应，同时增加公共错误统计。只有最小错误响应本身也无法编码时才无法发送。

---

## 4. Control UART 与 IRQ Manager Review

### 4.1 RX Idle 原子消费

`rx_idle_pending` 是 ISR 写、主循环读写的共享状态。当前 `take_rx_idle()` 在 IRQ Manager 提供的短临界区中完成：

```text
读取 pending
清零 pending
恢复原 PRIMASK
```

ISR 无法在“读取旧值”和“清零”之间插入新事件，因此不会覆盖新到的 Idle。

### 4.2 TX 只有一个消费者

平台当前正式模式为 RX IRQ + TX Polling。本轮明确拒绝：

- Control UART TX IRQ；
- Control UART RX/TX DMA。

TX Ring 只由主循环 Poll 路径 peek/discard，不再保留潜在双消费者结构。未来确有 TX IRQ 需求时，应先建立单一 TX Owner 协议，而不是同时打开 Poll 和 ISR。

### 4.3 IRQ Manager 生命周期

新增：

```c
et_irq_manager_deactivate()
et_runtime_deinit()
```

并收紧：

- 第二个不同 Manager 不能覆盖当前 Active Manager；
- Bind/Unbind/Dispatch 只允许 Active Manager；
- Runtime init 在 Protocol init 失败时回滚 IRQ Manager；
- Deactivate 按物理 Line 去重执行 disable、clear pending、unregister；
- 失败时保留状态供调用方处理，不伪装成功。

没有引入多 Runtime、动态注册中心或对象生命周期框架。

---

## 5. UART 最终结构 Review

### 5.1 单文件与职责

`firmware/services/src/et_uart_service.c` 继续保持单文件，并保留以下区域：

```text
Wire Helpers
IRQ Mapping
Threshold Mapping
Transfer Helpers
IRQ and Capture Management
Lifecycle and FIFO/DMA State
Command Helpers
Command Dispatch
Public Service Interface
```

Service 状态仍为静态定长：Capture 512 Bytes、9-bit Buffer 256 Words，无动态内存。

### 5.2 长操作回到 PC

Firmware 不再通过 `max_polls` 执行百万级循环：

- WRITE：单次非阻塞提交，返回实际提交数；
- READ_EXACT Wire 命令：单次读取，返回当前实际数据；
- 9-bit Write/Read：单次提交/读取；
- EXCHANGE Firmware 命令明确不再承担阻塞场景编排；
- `flush_rx_bounded()` 最多执行固定 64 次 Drain。

PC Driver 保持原有高层语义：

```text
write(data, timeout)
read_exact(length, timeout)
write_9bit(...)
read_9bit(...)
exchange(...)
```

但由 PC 使用 `time.monotonic()`、有限 poll count 和有限 sleep 负责编排。超时能够返回到调用者，不会冻结 Firmware ET-Frame 主循环。

### 5.3 FIFO/DMA 事务

目标状态包含：

```text
fifo_enabled
fifo_tx_threshold
fifo_rx_threshold
dma_mode
```

应用规则：

- FIFO Disabled：先显式写 DMA Disabled，再关闭 FIFO；
- FIFO Enabled：写 FIFO 后无论目标 DMA mode 是 Disabled/Single/Multi，都显式调用 DMA setter；
- 全部成功后才提交 Service Cache；
- 任一步失败，使用旧完整状态进行回滚；
- 回滚失败返回 I/O Error。

因此软件缓存与硬件配置不再因“切回 Disabled 未写硬件”而分叉。

### 5.4 IRQ Fault Evidence

`IRQ_STATE_GET` 从 20 Bytes 扩展为 24 Bytes：

```text
enabled_mask
pending_mask
active_mask
event_count
overflow_count
fault_count
```

以下失败会增加 `fault_count`：

- IRQ Snapshot 获取失败；
- TX Empty one-shot disable 失败；
- Clear Interrupt 失败；
- Capture 完成后恢复 Mask 失败；
- Capture Drain 的 Wrap 操作失败。

PC `_require_irq_event()` 同时要求：

```text
event_count delta > 0
目标 source bit 出现
fault_count delta == 0
```

因此“Callback 执行但清理失败”不会被写成 PASS。

### 5.5 Stop Bit Wire

最终边界：

| Data bits | Wire stop value | 语义 |
|---:|---:|---|
| 5 | 1 | 1 stop |
| 5 | 2 | 1.5 stop |
| 6–8 | 1 | 1 stop |
| 6–8 | 3 | 2 stop |

Wire `2 + 6/7/8 bits` 和 `3 + 5 bits` 均被拒绝，不再静默改义。PC 历史普通整数 `2` 仍先转换为规范 Wire `3`，但仅适用于 6–8 bit。

---

## 6. DMA Endpoint 分层 Review

### 6.1 删除跨 IP 调用链

整改前：

```text
DMA Service -> SYSCTRL Wrap -> UART Wrap
```

整改后：

```text
DMA Service -> Resource Endpoint Registry
DMA Service -> DMA Wrap
SYSCTRL Service -> Resource Endpoint Registry
SYSCTRL Service -> SYSCTRL Wrap
UART Service -> UART Wrap
UART Service -> Resource Endpoint Registry（只发布事实）
```

静态检查已确认：

- `et_dma_service.c` 不包含/调用 `et_sysctrl_wrap`；
- `et_sysctrl_wrap.c` 不包含/调用 `et_uart_wrap`。

### 6.2 可信 Endpoint 与 Route

外设地址的完整链路：

1. UART Service 通过 UART Wrap 得到真实 TX/RX Endpoint Address；
2. UART Service 将 `{provider, instance, endpoint, address}` 发布到固定 Endpoint 表；
3. PC 将同一地址和逻辑身份传给 SYSCTRL Service；
4. SYSCTRL Service 先验证并绑定可信 Route 身份，再配置 DMAMUX；
5. DMA Configure 只接受已存在并与地址一致的 Route；
6. Configured Channel 持有 Route Lease；
7. 有 Lease 时 SYSCTRL Release 返回 BUSY；
8. DMA Deconfigure 释放 Lease 后，PC 才释放 Route。

错误地址无法仅凭 PC 参数进入 DMA：它必须同时匹配 UART Service 已发布的可信 Endpoint 和当前 SYSCTRL Route。

Registry 固定容量：

```text
16 Endpoint Slots
16 Route Slots
uint16 lease_count
```

不使用 malloc，不扫描插件，不建立泛化依赖图。

### 6.3 Managed IRQ 顺序

DMA IRQ Enable 的准入条件已收紧为：

```text
controller_enabled
AND target channel configured
AND active_channels == 0
```

这样 `prepare_managed_irq_hardware()` 不会在目标 Channel 已运行时清掉本次传输事件。PC Case 的固定顺序为：

```text
configure
irq_enable
start
wait/result
irq_disable
deconfigure
```

---

## 7. PC Result 与错误恢复 Review

### 7.1 唯一最终状态

公共 `CaseResult` 继续是最终状态 Owner。DMA Helper 的 Feature 数据改为：

```json
{
  "measurement_status": "PASS|FAIL"
}
```

它不再写第二个顶层 `status`。因此不会出现 Feature JSON 写 PASS、公共 CaseResult 写 `EVIDENCE_MISSING` 的双结论。

### 7.2 Evidence 自动登记

- 使用 `framework_communication` 的 Case 自动登记 `dut`；
- 使用 `uart_peer_handle` 的 Case自动登记 `peer`；
- 外部 FPGA/Instrument 仍由真正消费它们的 Case 显式登记。

Fixture 只登记已经实际建立的公共通信/Peer 事实，不替代 Case 的业务测量和最终断言。

### 7.3 DMA Cleanup 错误链

PC DMA Driver 的模糊状态恢复规则：

- Configure Response Timeout：执行幂等 Deconfigure；若清理也失败，异常同时包含原超时和清理错误；
- Start Wait 检测 ERROR：best-effort Stop 后抛出 ERROR；
- Start Wait Timeout：best-effort Stop；Stop 失败通过异常链附加。

第一错误不会被清理错误静默覆盖。

---

## 8. 新增回归与验证结果

### 8.1 Native C Reliability Harness

新增：

```text
pc/et_test_platform/framework_validation/native/
  et_common_reliability_harness.c

pc/et_test_platform/framework_validation/unit/
  test_common_reliability_native.py
```

覆盖：

1. 坏帧内嵌合法帧后的连续重同步；
2. 同一 RX Chunk 两请求、TX 每次只写 3 Bytes 的 Response Owner；
3. Endpoint Publish 冲突拒绝；
4. Route Bind/Validate/Acquire/Release；
5. Route Lease 期间禁止 Unbind。

Native Harness 输出：

```text
common_reliability=PASS
```

### 8.2 Python 与单元回归

执行：

```text
python -m compileall -q pc/et_test_platform
python -m pytest pc/et_test_platform/framework_validation/unit -q \
  -k 'not generated_keil_project_matches_generation_record \
      and not generated_keil_project_uses_only_firmware_source_files'
```

结果：

```text
248 passed
3 skipped（既有环境条件）
0 failed
```

排除的两项仍是依赖生成工程记录和特定路径环境的既有 Keil 工程测试，本轮没有把它们写成 PASS。

### 8.3 Host C 语法检查

使用：

```text
GCC C11
-Wall -Wextra -Werror
-fsyntax-only
DET6801
DET_ENABLE_TEST_DRIVER_EXTENSIONS
```

检查范围：

```text
Framework:
  et_frame.c
  et_message.c
  et_protocol.c
  et_ring_buffer.c
  et_irq_manager.c
  et_runtime.c
  et_service_router.c

Application:
  et_control_uart.c

Wrap:
  et_resource_wrap.c
  et_sysctrl_wrap.c
  et_uart_wrap.c
  et_dma_wrap.c

Services:
  et_resource_service.c
  et_sysctrl_service.c
  et_uart_service.c
  et_dma_service.c
  et_services.c
```

结果：项目代码通过。Host 64-bit 环境中的既有 CMSIS pointer-width warning 仅对两类转换 warning 降级；这不代表 Keil 编译结果。

### 8.4 架构不变量

自动检查通过：

- `git diff --check`；
- DMA Service 不依赖 SYSCTRL Wrap；
- SYSCTRL Wrap 不依赖 UART Wrap；
- UART Service 不包含原 exact transfer 长循环；
- 最终代码树无临时 remediation script；
- 除最终验证 Workflow 外无临时 Workflow。

---

## 9. 二次人工 Review

自动验证后，对以下路径重新人工检查：

1. Parser Resync 在完整内嵌帧和尾部残留字节下的 consume 行为；
2. Protocol partial TX 完成前是否可能继续 Dispatch；
3. Control UART Idle 临界区和 TX 单消费者；
4. IRQ Manager Activate/Deactivate 失败状态；
5. UART Mask 临界区的嵌套 PRIMASK 行为；
6. UART Capture 完成、取消、失败时对普通 IRQ 的影响；
7. UART Disabled DMA Mode 是否真实写回硬件；
8. UART Fault Count 是否覆盖 Snapshot/Clear/Mask 失败；
9. Endpoint Publish、Route Bind、DMA Lease 和 Route Release 顺序；
10. SYSCTRL 冲突 Route 配置是否会破坏已有 DMAMUX；
11. DMA IRQ Enable 是否允许 Active Channel；
12. PC Timeout 与 Cleanup 异常链；
13. Common CaseResult 与 Feature Measurement 的最终状态所有权。

人工 Review 过程中追加修复了一个事务顺序问题：SYSCTRL Service 原本先写 DMAMUX、后绑定 Registry；如果 Registry 发现冲突，可能先扰动已有 Route。最终改为“先保留可信 Route 身份，再写 DMAMUX；硬件失败回滚 Registry”。

本轮二次 Review 未发现新的 P1 代码问题。

---

## 10. 尚未执行的验证

以下仍不能写成 PASS：

### 10.1 Keil

- ET6801 FPGA/ITCM Target 完整编译和链接；
- ET6801 Silicon/PFLASH Target 完整编译和链接；
- UART Service 状态、Endpoint Registry 和 Native 测试新增代码的 Flash/RAM 占用；
- `ET_RESOURCE_POOL` 链接区和 ABI 检查；
- ARM Compiler 对嵌套临界区、volatile 和结构布局的告警。

### 10.2 真实 HIL

至少需要：

1. HELLO、SERVICE_LIST、连续请求和响应重试；
2. 控制 UART 长响应、RX Idle 和连续 Frame；
3. UART Normal/Loopback/Peer Transfer；
4. UART RX/TX/Error/Timeout/9-bit IRQ；
5. UART TX Empty one-shot 和 re-arm；
6. UART Capture 取消、失败和下一 Case 恢复；
7. UART FIFO/DMA Disabled/Single/Multi 切换；
8. DMA0/DMA1 M2M 矩阵；
9. DMA IRQ Enable-before-Start 和 Error 终态；
10. UART TX/RX DMA 外设 Route；
11. Configured Channel 持有 Route 时 Release 返回 BUSY；
12. DMA Deconfigure 后 Route 可释放；
13. 连续多轮、随机 Case 顺序和失败后恢复。

Priority Completion Order 和真正“传输进行中”的 Suspend/Resume 仍需要独立观察器，继续保持 SKIP，不用软件轮询伪造 PASS。

---

## 11. 最终结论

当前代码已经从：

```text
公共帧恢复可能丢字节
Partial Response 可能被覆盖
Control UART 共享标志竞态
UART Firmware 长轮询
UART IRQ 清理失败不可见
DMA Service/Wrap 跨 IP 调用
DMA Active 期间重配 IRQ
PC 存在双最终状态
```

收敛为：

```text
保留字节的 Frame Resync
单一 Pending Response Owner
原子 Control UART Idle
PC Deadline + Firmware 有界操作
可查询 UART IRQ Fault Evidence
固定容量 Common Endpoint Registry/Lease
严格 configure -> irq_enable -> start
Common CaseResult 唯一最终状态
```

**从代码和 Host Review 层面，前一轮确认的公共层、UART、DMA P1 问题已经关闭，当前结构符合既定“可靠、稳定、轻量、易扩展”的框架设计。**

剩余工作是 Keil 正式工具链和真实 HIL 验证。在这些验证完成前，不能把整个平台、UART 或 DMA 标记为硬件 PASS，也不应直接把“Host 全绿”替代为硅前/硅后结论。
