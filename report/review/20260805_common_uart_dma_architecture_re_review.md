# 公共层、UART 与 DMA 架构一致性复核

文档状态：第二轮独立代码 Review 完成，发现的问题尚未全部整改
复核日期：2026-08-05
目标仓库：`Abba-shenfu/Automated_Testing_Platform`
基线分支：

- 公共层：`main@76a6785b0257b0d8a14af6df441338bccdf9a8c3`
- UART 整改：`codex/uart-review-fixes-20260805@d76245d9388fe5c5c2906b414d73930dd15fc1f0`
- DMA 整改：`codex/dma-review-20260805@504af200c7119e51c14c6d4a224856f2bfece45e`
- 联合复核：`codex/platform-sync-20260805`

本次复核以以下正式设计为判定依据：

- `report/design/et_ip_automated_test_platform_architecture.md`
- `report/design/pc_layered_architecture.md`
- `report/design/firmware_layering.md`
- `report/design/wrap_layer_design.md`
- `report/design/interrupt_subsystem_design.md`
- `report/design/capability_v2_contract.md`

> 本文是代码和 Host 验证结论，不等同于 Keil 构建或真实 HIL PASS。发现的 P1 问题关闭前，不建议把 UART、DMA 分支直接并入 `main`。

---

## 1. 需求边界

本次 Review 严格沿用前期已经确定的边界，而不是重新设计一套框架：

1. PC Case 是测试编排者和最终 PASS/FAIL 判定者。
2. 固件是远端 IP 操作代理，不在一个 Service 命令中编排完整测试场景。
3. 公共 Framework、ET-Frame、IRQ Manager、Result 和 Capability 层必须与具体芯片、具体 IP 解耦。
4. 一个 Service 只拥有自身 IP 的运行状态，并调用自身 Wrap、Framework 公共接口和经过批准的公共资源接口。
5. 一个 Wrap 只适配一个 IP，不进行跨 IP 隐式操作，不形成 Case 级流程。
6. Control UART 属于 Application/Transport，必须从 Runtime UART Service 中保留并隔离。
7. 不引入 RTOS、动态内存、事件总线、通用 Observer Framework 或通用状态机框架。
8. 长操作优先使用 `start/status/abort` 或 PC 侧有期限轮询，不能在固件命令处理函数内长时间忙等。
9. 无效参数和 malformed frame 继续以 PC 单元/协议测试为主，不新增无必要的固件/HIL 畸形输入 Case。
10. UART Service 保持一个 `.c` 文件，以 `/********************************** ... **********************************/` 分区。

---

## 2. 总体结论

### 2.1 结论摘要

当前代码的主体方向是正确的：

- ET-Frame、Message、Service Router、TargetClient 的分层基本清晰；
- Control UART 与 Runtime UART Service 已实现角色隔离；
- UART 已收敛到单 IRQ Callback、单 Service 文件和静态定长状态；
- DMA 已收敛到单 Managed IRQ Session、显式 Channel 生命周期、地址校验和 Resource/Route Lease；
- PC Driver 与 Case 大体保持“Driver 做协议，Case 做流程”的边界；
- UART 与 DMA 两个整改分支的代码可联合合并，未出现代码冲突；
- 联合代码树的 Python 语法、广泛单元回归和相关 C 文件 Host 语法检查均通过。

但本轮仍发现 **11 项 P1 问题和 6 项 P2 问题**。其中最重要的不是语法错误，而是以下三类结构性问题：

1. **公共通信层存在边界恢复和响应缓存覆盖风险**；
2. **UART Service 仍保留固件内长轮询，并存在 FIFO/DMA 状态与 ISR 证据可靠性缺口**；
3. **DMA 为了地址安全形成了 `DMA Service -> SYSCTRL Wrap -> UART Wrap` 的跨 IP 调用链，明确违反既定 Service/Wrap 分层。**

因此当前状态应定义为：

```text
功能整改方向正确
+ 联合 Host 回归通过
- 公共层仍有 P1 可靠性缺口
- UART 仍有阻塞和状态一致性缺口
- DMA 跨 IP 依赖不符合框架设计
= 不建议直接合入 main
```

### 2.2 严重度统计

| 严重度 | 数量 | 含义 |
|---|---:|---|
| Critical | 0 | 未发现立即造成任意内存写或必现系统失控的问题 |
| P1 / Major | 11 | 应在合入主分支和正式 HIL 前关闭 |
| P2 / Minor | 6 | 不阻断本轮原型验证，但应进入后续治理 |

---

## 3. 架构一致性矩阵

| 层/模块 | 当前评价 | 符合项 | 主要偏差 |
|---|---|---|---|
| PC Case | 部分符合 | UART Case 已显式记录证据，流程主要在 PC | DMA Case 未统一登记 evidence，可能产生互相矛盾的 PASS/EVIDENCE_MISSING |
| PC Driver | 基本符合 | 协议编码、长度校验、动态能力缓存清晰 | UART exact API 把超大 poll budget 下沉固件；DMA error path 清理不够自洽 |
| Profile/Capability | 基本符合 | 静态 Profile 与 Runtime Registry 已分离 | ET6801 验收矩阵仍有少量固定实例/通道假设 |
| ET-Frame Parser | 不完全符合 | 长度、版本、CRC、重同步均有边界检查 | 重同步保留完整帧时可能吞掉下一帧首字节 |
| Protocol Runtime | 不完全符合 | Session、duplicate replay、partial TX 基本可靠 | 同一 RX chunk 中第二请求可覆盖尚未发完的第一响应 |
| Service Router | 符合 | 只按 Service/Instance 分发，不含 IP 逻辑 | 未发现新的跨层问题 |
| Control UART | 不完全符合 | Application 独占、Ring Buffer、IRQ Manager 接入正确 | RX idle 标志存在 ISR/主循环丢事件竞态；TX IRQ 模式存在双消费者隐患 |
| IRQ Manager | 基本符合 | 固定槽位、共享线、临界区、统一 Handler | 缺少 deactivate/完整重初始化生命周期，当前仅适合单次静态启动 |
| UART Service | 不完全符合 | 单文件、单 Callback、静态状态、Control UART 排除 | exact 命令固件忙等；FIFO/DMA 状态；ISR 状态和清中断失败证据 |
| UART Wrap | 基本符合 | 芯片类型封装在 Wrap，原子接口较清晰 | Deinit 未显式关闭 Busy Detect；线格式兼容逻辑越过 Wire 边界 |
| DMA Service | 功能可靠但分层不符合 | 生命周期、地址、租约、IRQ 所有权改善明显 | 直接调用 SYSCTRL Wrap，跨 IP 管理 Route |
| DMA Wrap | 基本符合 | DMA Driver 映射、原子操作和错误映射清晰 | 本身问题较少，主要偏差来自上层跨 IP 链 |
| SYSCTRL Wrap | 不符合 Wrap 规则 | DMAMUX 状态跟踪和 Lease 有价值 | 直接包含并调用 UART Wrap，形成跨 IP Wrap |
| Result/Evidence | 不完全符合 | RunContext 和统一 CaseResult 结构正确 | DMA 独立 Feature JSON 与通用 CaseResult 可能给出不同最终状态 |

---

## 4. 公共层问题

### COM-P1-001：Frame 重同步可能吞掉下一帧首字节

**位置**：`firmware/framework/src/et_frame.c`

`parser_resync()` 在坏帧内部找到新的 `ET` Magic 后，会把剩余数据前移，并在剩余内容已经包含完整 Header 时重建 `expected_length`。当剩余内容实际上已经是一帧完整合法帧时，函数仍返回 `DROPPED`，没有立即输出该帧。

下一次 `et_frame_parser_push()` 会先把“下一帧的第一个字节”追加到缓冲区，再发现前一帧已完整并输出它；随后 Parser 清零，刚追加的字节被一起丢弃。

**影响**：

- 坏帧恢复后，紧随其后的第三帧可能丢失首字节；
- PC 重试会降低表面故障概率，但会增加超时和恢复抖动；
- 这是公共协议层问题，会同时影响 UART、DMA 和未来所有 Service。

**整改要求**：

- 重同步后若缓冲区已包含完整帧，应在不消费新字节的情况下输出；或
- 支持“输出当前帧并重新处理本次输入字节”；
- 增加连续三段输入回归：坏帧 + 内嵌完整合法帧 + 紧邻第三帧。

---

### COM-P1-002：同一 RX Chunk 中的第二请求可覆盖未发送完的第一响应

**位置**：`firmware/framework/src/et_protocol.c`

`et_protocol_poll()` 只在进入函数时判断是否存在未发完响应。若本次读取的 `rx_chunk` 同时包含两个请求：

1. 第一个请求被执行并生成响应；
2. `flush_pending_response()` 只发送部分内容；
3. `for` 循环仍继续处理同一 Chunk 的剩余字节；
4. 第二个请求重新使用 `work_frame`、`tx_frame` 和 replay metadata；
5. 第一响应尚未发送的尾部可能被覆盖。

正常 `TargetClient` 当前是单 outstanding request，因此常规路径不容易触发；但 Raw Transport、错误恢复、重复注入或未来并发 Client 都可能触发。

**整改要求**：

- 一旦一个请求产生未发送完响应，立即停止解析本次 Chunk；
- 未消费的 RX 字节应保存在有界 pending input buffer，或下次重新送入 Parser；
- 必须保证任意时刻只有一个不可覆盖的 encoded response owner。

---

### COM-P1-003：Control UART RX Idle 标志存在丢事件竞态

**位置**：

- `firmware/application/src/et_control_uart.c`
- `firmware/application/include/et_control_uart.h`

ISR 将 `rx_idle_pending = 1`，主循环 `take_rx_idle()` 读取后直接清零。若 ISR 恰好在“主循环读取旧值”和“主循环写 0”之间发生，新事件会被清掉。

ET6801 FPGA Board 当前配置为 RX IRQ，因此该竞态属于当前实际运行路径，而不是纯理论问题。

**影响**：截断帧恢复可能被延迟，Parser 的 incomplete 状态可能保留到后续事件。

**整改要求**：使用 IRQ Manager/IRQ Wrap 临界区完成原子 take-and-clear，保持实现轻量，不引入锁框架。

---

### COM-P1-004：DMA Case 未接入统一 Evidence 判定

**位置**：

- `pc/et_test_platform/scheduling/run_context.py`
- `pc/et_test_platform/test_cases/dma/*.py`
- `pc/et_test_platform/test_cases/uart/*.py`

通用 `RunContext` 规定：使用 `framework_communication` 的 Case 至少需要登记 `dut` evidence；否则即使 pytest 调用阶段通过，通用 CaseResult 也会变成 `EVIDENCE_MISSING`。

UART Case 已调用 `record_evidence(record_property, "dut"/"peer")`，DMA Case 大量只写自己的 Feature JSON，没有登记通用 evidence。

**影响**：同一个 DMA Case 可能出现：

```text
Feature JSON: PASS
Common CaseResult: EVIDENCE_MISSING
```

这违反“PC Case 是唯一最终判定者”和“统一证据链”。

**整改要求**：

- DMA 硬件 Case 统一接收 `record_property` 并登记实际使用的 `dut/peer/fpga/instrument`；或
- 由成功建立并实际使用的公共 Fixture 自动登记证据；
- Feature JSON 只能作为测量附件，不再作为第二个独立最终状态源。

---

### COM-P2-001：Service 已产生副作用后，响应编码失败可能导致重复执行

**位置**：`firmware/framework/src/et_protocol.c`

`build_response()` 先 dispatch Service，再编码 Message/Frame。若 Service 违反响应长度契约导致编码失败，命令副作用已经发生，但没有可 replay 的响应，PC 重试可能再次执行命令。

**建议**：对 `body_length <= body_capacity` 建立强契约；越界时生成固定 `INTERNAL_ERROR` 响应，并增加 Service Contract 测试。

---

### COM-P2-002：Runtime/IRQ Manager 缺少完整停用和失败回滚生命周期

当前为静态单实例启动，符合 ET6801 当前固件使用方式；但 `IRQ Manager activate` 后若后续初始化失败，没有对称 deactivate。未来若支持软重启、测试固件热重建或多个 Runtime 实例，状态会不干净。

**建议**：仅增加很小的 `deactivate/reset` 接口和失败回滚，不引入通用生命周期框架。

---

### COM-P2-003：Control UART TX IRQ 模式存在 ISR/主循环双消费者隐患

当前 Board 使用 TX Polling，因此暂不触发。若切换 TX IRQ，`transmit_to_port()` 既会在 ISR 中调用，也会在主循环 `poll()` 中调用；Ring Buffer 的 `peek/discard` 将出现两个消费者。

**建议**：在完成单消费者保护前明确拒绝 TX IRQ 配置，或保证只有 ISR/主循环中的一方消费 TX Ring。

---

## 5. UART 再次复核

### UART-P1-001：Service 仍在命令处理函数内执行长时间忙轮询

**位置**：`firmware/services/src/et_uart_service.c`

以下路径仍在一个 Service 请求内循环：

- `write_exact()`；
- `read_exact()`；
- 9-bit exact read/write；
- `exchange()` 间接调用 exact；
- `flush_rx()` 直到读空，且没有明确最大 drain 次数。

PC 默认 `max_polls` 达到 `1_000_000`。这些循环会阻塞 ET-Frame 主循环，使同一控制通道无法及时处理取消、查询或恢复命令。

**这与既定设计不一致**：DMA 已经把同步等待迁移到 PC，UART 也应采用相同原则。

**整改要求**：

1. 保留原子 `WRITE_PARTIAL`、`CAPTURE_START/GET/CANCEL`；
2. Exact Write/Read/Exchange 的 deadline 和重复提交移动到 PC Driver/Helper；
3. 9-bit 同样改为 partial 或 start/status；
4. `flush_rx()` 使用 FIFO 深度/固定上限进行有界 drain；连续输入时返回 BUSY 或显式 overflow；
5. 不新增 RTOS Task 或异步框架。

---

### UART-P1-002：FIFO/DMA 切换到 DISABLED 时，软件状态与硬件状态可能不一致

**位置**：`firmware/services/src/et_uart_service.c`

`uart_write_fifo_dma_hardware()` 只有在新 `dma_mode != DISABLED` 时才调用 `et_uart_wrap_set_dma_mode()`。

当硬件原先处于 MULTI DMA，随后请求切换到 DISABLED：

- Service 将 `dma_mode` 更新为 DISABLED；
- FIFO 配置接口会重写 FCR，但没有形成“总是显式应用目标 DMA mode”的事务；
- rollback 使用同一 helper，也可能不能精确恢复旧状态。

**整改要求**：无论目标是 DISABLED、SINGLE 还是 MULTI，都必须显式调用 DMA mode setter；将 FIFO enable、threshold、DMA mode 作为一个事务完整 apply/rollback。

---

### UART-P1-003：Stop Bit 的兼容语义泄漏到 Firmware Wire

PC API 已正确处理兼容：普通整数 `2` 代表历史调用中的 two-stop，并编码为规范 Wire 值 `3`；显式 `UartStopBits.ONE_AND_HALF` 才编码 Wire 值 `2`。

但 Firmware/Wrap 仍允许：

```text
wire stop_bits = 2 + data_bits = 6/7/8
```

并将其重新解释成 two-stop。Wire 上没有 Python 类型信息，因此这会把非法的“1.5 stop + 非5位数据”静默修正为另一个配置。

**整改要求**：

- Wire `1`：1 stop；
- Wire `2`：仅在 5 data bits 时合法，表示 1.5 stop；
- Wire `3`：6–8 data bits 的 2 stop；
- 历史整数兼容只保留在 PC API 入口，不进入 Firmware Wire。

---

### UART-P1-004：ISR 与命令上下文共享状态保护不足，清中断失败被静默忽略

**位置**：

- `firmware/services/include/et_uart_service.h`
- `firmware/services/src/et_uart_service.c`

ISR 与命令上下文共同读写：

- Capture active/expected/received；
- IRQ enabled/applied/suppressed mask；
- Callback evidence 和 generation。

当前部分字段既没有完整临界区，也没有统一 fault latch。Callback 中以下失败被忽略：

- `et_uart_wrap_clear_interrupts()`；
- Capture 完成后的 `uart_apply_irq_mask()`。

PC 可能看到 event count 和 source bit，但不知道硬件清除或 mask 恢复失败。

**整改要求**：

- 用很小的临界区保护跨上下文 mask/capture 状态；
- 增加固定字段 `irq_fault_count` 或复用明确命名的 overflow/fault 位；
- Clear/Mask/Unbind 失败必须进入可查询证据；
- 不引入通用 Observer 或状态机。

---

### UART-P2-001：UART Wrap Deinit 未显式关闭 Busy Detect 源

`et_uart_wrap_deinit()` 的 blanket disable 列表包含 RX/TX/Timeout/Error/Modem/Address/Programmable THRE，但没有 Busy Detect。随后 Software Reset 很可能清除硬件状态，但在 reset 前仍存在不必要窗口，也不符合“先停源、再解绑/复位”的规则。

**建议**：将 Busy Detect 加入显式 disable mask，并保留 idempotent deinit。

---

### UART 符合项

本轮确认以下整改仍符合需求：

- UART Service 保持一个 `.c`，并使用要求的分区注释；
- Control UART 已从 Runtime Service Registry 排除；
- DUT/Peer 逻辑角色由 Bench/Fixture 解析，不在 Case 硬编码物理 UART；
- IRQ 已收敛为一个 Callback 和一个 Binding；
- 初始化先校验参数，再清理旧状态；Deinit/Reset 基本幂等；
- Capture 使用静态定长缓冲，无动态内存；
- PC line encoder、response size 校验和 Feature API 基本清晰；
- malformed/无效参数仍以 PC 测试为主，未引入无必要 HIL 畸形帧测试。

---

## 6. DMA 再次复核

### DMA-P1-001：DMA Service 直接调用 SYSCTRL Wrap，违反 Service 边界

**位置**：`firmware/services/src/et_dma_service.c`

DMA Service 为了验证和持有外设 Route，直接包含 `et_sysctrl_wrap.h`，调用：

- `validate_dma_endpoint`；
- `acquire_dma_endpoint`；
- `release_dma_endpoint`。

安全目标是正确的，但调用方向不符合正式设计。DMA Service 应只知道 DMA、IRQ 和公共资源，不应直接拥有 SYSCTRL IP 的 Route 生命周期。

**整改要求**：建立一个很小、芯片中立的公共 `DMA Endpoint Registry/Lease` 接口，或由 SYSCTRL Service 返回 opaque endpoint lease handle；DMA Service 只验证/持有公共 handle，不调用 SYSCTRL Wrap。

跨 IP 流程仍由 PC Case 编排：

```text
UART endpoint query
-> SYSCTRL route configure
-> obtain endpoint lease/handle
-> DMA configure
-> DMA start/status
-> DMA deconfigure
-> release route
```

---

### DMA-P1-002：SYSCTRL Wrap 直接调用 UART Wrap，违反“一 IP 一 Wrap”

**位置**：`firmware/wrap/src/et_sysctrl_wrap.c`

SYSCTRL Wrap 包含 `et_uart_wrap.h` 并调用 UART Wrap 获取 DMA endpoint address。这形成：

```text
DMA Service
  -> SYSCTRL Wrap
      -> UART Wrap
```

该结构有三个问题：

1. Wrap 不再是一 IP 原子适配；
2. SYSCTRL Wrap 对 UART endpoint enum 有编译依赖；
3. 未来加入 SPI/I2C/ADC DMA endpoint 时会不断扩展跨 IP 依赖。

**整改要求**：Endpoint 地址来自芯片静态配置、公共 Endpoint Provider 或各 IP Service 对 PC 的查询结果；SYSCTRL Wrap 只做 DMAMUX 原子配置和释放。

---

### DMA-P1-003：Managed IRQ 可在目标 Channel Active 时启用，并会清除运行中事件

**位置**：`firmware/services/src/et_dma_service.c`

当前 `irq_enable()` 只拒绝“其他 active channel”，允许目标 channel 已经 active。随后 `prepare_managed_irq_hardware()` 会遍历全部 Channel，Disable 并 Clear 所有 IRQ Event。

若目标传输已开始，这会：

- 清除已产生的当前传输事件；
- 错过完成边沿；
- 使 IRQ Case 得到不完整证据。

**整改要求**：Managed IRQ Setup 必须要求 `active_channels == 0`；PC 顺序固定为 `configure -> irq_enable -> start`。

---

### DMA-P2-001：PC `start_wait()` 在 ERROR 路径不执行 best-effort stop

`start_wait()` 在看到 ERROR 时直接抛异常；测试 Helper 的 finally 通常会清理，但直接调用 Driver 的其他代码可能留下 active/configured 状态。

**建议**：在 ERROR 和 timeout 路径统一 best-effort stop，并保留原始异常；cleanup 失败通过异常链记录，不覆盖第一错误。

---

### DMA-P2-002：Resource Pool 采用全局 Lease，安全但较保守

当前任意配置都会锁整个 Resource Pool，包括某些不使用 Memory Resource 的路径。这减少并发，但符合当前“可靠优先、轻量优先”的取舍。

**结论**：本轮接受，不作为合入阻断项。只有出现明确并发需求时，才升级为按 Resource Handle Lease，避免提前引入资源图框架。

---

### DMA 符合项

本轮确认以下整改方向正确：

- Service 不再执行同步 Channel wait；等待和 deadline 已回到 PC；
- Controller/Channel configured/active 状态明确；
- Managed IRQ 只有一个所有者；
- Runtime channel count 进入 Service 和 PC 校验；
- M2M 地址限制在 Resource Pool；外设地址有 Route 约束；
- Resource 和 Route 在 configured 周期内有 Lease；
- Start 前清当前 Channel 旧 terminal event；
- Channel Status 使用 raw ERROR + free 作为终态事实；
- Priority completion order 和真正传输中 Suspend/Resume 没有伪造 PASS；
- 全部状态为静态定长，无 RTOS、malloc、事件总线和通用状态机。

---

## 7. UART 与 DMA 联合验证

为避免分别在两个分支上“各自通过但合并失败”，本轮在临时联合树中执行：

```text
DMA 整改分支
+ UART 整改分支
+ 仅解决 report/README.md 文档索引冲突
```

### 7.1 合并结果

- UART 与 DMA **代码无冲突**；
- 唯一冲突是两个分支都修改了 `report/README.md`；
- `uart_test_case_p2.py` 自动合并成功；
- 文档索引需要正式集成时人工保留两侧新增链接。

### 7.2 已执行验证

1. `python -m compileall -q pc/et_test_platform`：通过。
2. `pc/et_test_platform/framework_validation/unit` 广泛回归：全部执行项通过，保留 3 项既有 SKIP。
3. Host GCC C11 `-Wall -Wextra -Werror -fsyntax-only`：以下相关文件通过：

```text
firmware/framework/src/et_frame.c
firmware/framework/src/et_protocol.c
firmware/framework/src/et_ring_buffer.c
firmware/framework/src/et_irq_manager.c
firmware/application/src/et_control_uart.c
firmware/wrap/src/et_resource_wrap.c
firmware/wrap/src/et_sysctrl_wrap.c
firmware/wrap/src/et_uart_wrap.c
firmware/wrap/src/et_dma_wrap.c
firmware/services/src/et_uart_service.c
firmware/services/src/et_dma_service.c
firmware/services/src/et_services.c
```

Host 64-bit 编译环境仍会输出既有 CMSIS pointer-width warning，本次仅对这两类 CMSIS warning 降级；这不代表 Keil 构建通过。

### 7.3 未执行验证

- ET6801 FPGA/ITCM Keil 完整构建；
- ET6801 Silicon/PFLASH Keil 完整构建；
- 合并后固件尺寸、RAM、Resource Pool 链接区检查；
- 合并后 UART/DMA 全量真实 HIL；
- 公共协议的连续坏帧/partial response 故障注入。

---

## 8. 推荐整改顺序

### 第一批：公共层 P1

1. 修复 Frame resync 吞字节；
2. 修复 pending response 被同 Chunk 后续请求覆盖；
3. 修复 Control UART RX idle 原子 take；
4. 增加公共协议对应单元/故障注入测试。

公共层先修，因为它承载 UART、DMA 和未来所有 IP。

### 第二批：UART P1

1. Exact read/write/9-bit/exchange deadline 移到 PC；
2. `flush_rx` 有界化；
3. FIFO/DMA state 总是完整 apply/rollback；
4. Firmware Wire 收紧 Stop Bit；
5. ISR 共享状态和 clear/mask fault 可观测化；
6. Deinit 显式关闭 Busy Detect。

### 第三批：DMA 分层 P1

1. 引入最小公共 DMA Endpoint Lease 接口；
2. 删除 `DMA Service -> SYSCTRL Wrap`；
3. 删除 `SYSCTRL Wrap -> UART Wrap`；
4. IRQ Enable 必须发生在所有 Channel inactive 时；
5. 保留现有安全校验和 Lease 语义，不退回任意外设地址。

### 第四批：PC 统一证据

1. DMA Case 登记 evidence；
2. Feature JSON 降级为附件/measurement；
3. Common CaseResult 保持唯一最终 PASS/FAIL；
4. 不新增重复的第二套 Report Framework。

### 第五批：正式集成验证

1. 以最新 `main` 建立一个正式集成分支；
2. 合入公共层修复、UART 修复、DMA 分层修复；
3. 运行全量 Unit/Contract；
4. 运行两个 Keil Target；
5. 运行 UART、DMA、UART+DMA 组合 HIL；
6. Review 无 P1 后再进入 `main`。

---

## 9. 整改验收标准

以下条件全部满足后，才能把本轮状态改为“架构 Review 通过”：

- [ ] Frame Parser 连续坏帧恢复不丢后续字节；
- [ ] Pending Response 在完整发送前不可被覆盖；
- [ ] Control UART RX idle 不丢事件；
- [ ] UART Service 不再执行百万级命令内轮询；
- [ ] UART FIFO/DMA 软件状态与硬件状态一致；
- [ ] Firmware Wire 不再静默重解释非法 Stop Bit；
- [ ] UART IRQ clear/mask 失败进入可查询证据；
- [ ] DMA Service 不直接调用 SYSCTRL Wrap；
- [ ] SYSCTRL Wrap 不直接调用 UART Wrap；
- [ ] DMA Managed IRQ 只在 inactive 状态配置；
- [ ] DMA CaseResult 与 Feature JSON 不产生相互矛盾的最终状态；
- [ ] UART+DMA 联合 Unit/Contract 全绿；
- [ ] ET6801 FPGA 与 Silicon Keil 构建通过；
- [ ] 真实 HIL 无状态污染和恢复失败。

---

## 10. 最终判断

### 公共层

整体分层设计是成立的，但 Frame 恢复、Response Owner 和 Control UART ISR 边界仍有 P1 可靠性问题，当前不能评价为“公共层完全稳定”。

### UART

前一轮整改关闭了角色冲突、双 Callback、生命周期和大部分配置问题；但固件长轮询、FIFO/DMA Disabled 事务、Stop Bit Wire 和 ISR fault evidence 仍需整改。UART 当前是“方向符合、尚未完全符合非阻塞和可靠性需求”。

### DMA

DMA 生命周期和安全性已经明显改善，但为实现 Route 安全而形成的跨 IP Service/Wrap 依赖不符合正式框架设计。必须在不降低地址安全的前提下改成公共 Endpoint Lease，才能评价为“分层符合”。

### 综合

```text
可编译、可回归
≠ 架构完全符合
≠ 真实硬件已通过
```

当前建议是：**不要回退现有可靠性整改，也不要直接合入 main；按照“公共层 -> UART -> DMA Endpoint 分层 -> Evidence -> Keil/HIL”的顺序关闭 P1。**
