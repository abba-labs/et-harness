# DMA 可靠性整改完成 Review

文档状态：代码级整改与复核完成，Host 静态/单元/C 语法验证通过，Keil 与真实 HIL 待执行  
整改日期：2026-08-05  
整改分支：`codex/dma-review-20260805`  
最终代码提交：`8b516b28df01282a1cc1ccd0b26f05412ba9bd5c`  
关联评审：

- [DMA 全链路代码评审与优化设计](20260805_dma_full_chain_code_review.md)
- [DMA 第二轮代码复核与最终整改边界](20260805_dma_second_round_code_review.md)

> 本文记录 DMA 代码整改后的最终结构、问题闭环状态、人工 Review 结果和验证边界。本文中的“已关闭”仅表示代码与 Host 验证闭环；没有经过本轮 Keil 构建和真实硬件复测的内容，不写成硬件 PASS。

---

## 1. 整改约束

本轮严格遵守平台既定边界：

1. DMA Case 负责完整测试流程和 PASS/FAIL，DMA Service 不编排 UART、SYSCTRL、Resource 等跨 IP Case。
2. DMA Service 只维护一个控制器实例的静态、定长运行状态，不使用动态内存。
3. 不引入 RTOS、事件总线、Observer Framework、插件系统或通用状态机框架。
4. DMA Wrap 继续保持芯片中立；ET6801 SDK 类型和寄存器映射仍只存在于芯片适配层。
5. 使用现有 ET-Frame、Resource Service、SYSCTRL Wrap 和 IRQ Manager，不建立第二套通信或资源机制。
6. 优先修复状态所有权、失败恢复和证据可信度，而不是继续增加命令。
7. 不用轮询结果伪造 IRQ、优先级或暂停时序证据。
8. 不允许 PC 通过 DMA Service 任意写入未经批准的内存或外设地址。

整改后的核心模型是：

```text
一个 DMA Service 实例
  -> 一个 controller_id
  -> 固定 channel_count
  -> configured_channels / active_channels
  -> 一个 Managed IRQ Session
  -> 每通道固定长度的 Resource / Route ownership
```

---

## 2. 最终问题闭环状态

| ID | 最终状态 | 整改结论 |
|---|---|---|
| DMA-REV-001 | 已关闭 | Managed IRQ 与 Raw Mask/Pending 命令互斥；Managed Session 建立前统一接管并清理控制器中断状态。 |
| DMA-REV-002 | 已关闭 | `IRQ_RESULT_CLEAR` 通过公共 IRQ 临界区与 ISR 写者串行化，generation 继续只负责一致读快照。 |
| DMA-REV-003 | 已关闭 | Service 精确保留 route binding 状态；IRQ Manager 仅在物理 disable/clear/unregister 成功后删除 binding。 |
| DMA-REV-004 | 已关闭（当前单 Session 契约） | callback 读取控制器级中断快照，清理全部相关通道，锁存目标通道证据并统计其他通道为 unexpected；不伪装支持多 Managed Session。 |
| DMA-REV-005 | 已关闭 | Channel 配置失败会执行 deconfigure 回滚；Resource/Route ownership 同步回滚，失败状态仍可继续清理。 |
| DMA-REV-006 | 已关闭 | 固件同步 busy-wait 命令返回 `NOT_SUPPORTED`；PC 使用可中断的 ET-Frame 状态轮询并在超时后执行恢复。 |
| DMA-REV-007 | 已关闭 | LLI descriptor 使用 Resource handle+offset；普通内存地址、首个 LLP 和描述符写入均受 Resource 范围约束。 |
| DMA-REV-008 | 测试声明已修正 | Suspend/Resume Case 暂时标记 `blocked_by_observability`，不再把“完整 block 后暂停”写成“传输中暂停”PASS。 |
| DMA-REV-009 | 测试声明已修正 | Priority Case 不再通过 CHENREG 轮询推断先后顺序；缺少独立观察器时明确 SKIP。 |
| DMA-REV-010 | 部分关闭，剩余 P2 | Service/Driver 使用 runtime channel count；PC mask 不再固定 `0xFF`。部分 ET6801 全量 Case 仍保留 2 控制器/8 通道矩阵，后续应由 Profile 参数化。 |
| DMA-REV-011 | 剩余 P2 | ET6801 Runtime Feature 仍主要由当前 Wrap 构建常量给出；新增芯片或裁剪构建前需改为构建能力派生。 |
| DMA-REV-012 | 已关闭 | 只读查询和真正幂等命令使用 exact-duplicate retry；Configure 超时通过幂等 deconfigure 恢复到已知状态。 |
| DMA-REV-013 | 部分关闭，兼容保留 | 所有计数改为饱和计数；Wire 字段 `overflow_count` 为兼容保留，实际语义明确为 IRQ clear failure count。 |
| DMA-REV-014 | 剩余 P2 | C/Python Wire 定义仍有手工镜像，已有契约测试但尚未生成式统一。 |
| DMA-REV-015 | 部分关闭 | 共享 DMA helper、外设 pair 和主要 Case 使用“全部尝试”的 cleanup；仍需逐步统一所有历史 Case。 |
| DMA-REV-016 | 剩余平台 P2 | 专项 JSON 已保留关键事实，但与通用 CaseResult、固件/profile SHA 的统一关联仍属结果系统工作。 |
| DMA-REV-017 | 已关闭 | 地址校验覆盖批准 Resource 区域、完整 span、递增溢出、递减下溢以及 gather/scatter 间隔跨度。 |
| DMA-REV-018 | 已关闭 | 固件 handler 不再忙等，ET-Frame 主循环可持续处理查询、停止和恢复命令。 |
| DMA-REV-019 | 已关闭 | Channel Status 返回当前通道 raw terminal events；启动前清旧状态；PC 发现 ERROR 时立即失败，不再把 `CHENREG==0` 单独当成功。 |
| DMA-REV-020 | 已关闭 | 增加 controller/configured/active/ownership 状态；`find_free_channel()` 排除已配置但未启动的通道。 |
| DMA-REV-021 | 已关闭 | IRQ Manager teardown 失败可重试，Service 不再错误声明 binding 已释放。 |
| DMA-REV-022 | 已关闭 | M2M/M2P/P2M/P2P 的地址模式、接口、握手端和路由地址执行跨字段约束。 |
| DMA-REV-023 | 部分关闭，剩余 P2 | Runtime channel count 与 Driver 校验已动态化；部分 Case 仍直接构造 Driver，尚未全部收敛到统一 DMA fixture。 |
| DMA-REV-024 | 安全问题已关闭 | Resource pool 使用 lease；DMA channel 配置期间禁止 reset/write/fill/可变 resolve。当前策略为全池保守锁定，后续可按资源细化。 |
| DMA-REV-025 | 剩余 P2 | 增加了可靠性静态契约和更广 Host 验证，但仍缺少可注入 Wrap/IRQ 失败的完整 DMA Service native harness。 |
| DMA-REV-026 | 已关闭 | DMA Service 注册遇到不支持实例时 `continue`，并用 `dma_count` 紧凑存储，支持稀疏实例。 |

最终分类：

```text
代码级 P1：已闭环
错误或不可证明的测试 PASS：已阻止
跨芯片、生成式协议、证据链和完整故障注入：保留为 P2
真实硬件结论：待 Keil/HIL
```

---

## 3. 中断所有权整改

### 3.1 整改前

同一组 DMA 中断 Mask 可由以下路径同时修改：

```text
IRQ_ENABLE / IRQ_DISABLE
INTERRUPT_MASK_ENABLE / DISABLE
INTERRUPT_PENDING_CLEAR
Controller Disable
```

Service 只保存一个 `irq_channel`，而分类 IRQ 和 Combined IRQ 都是控制器级物理线路。旧实现容易出现：

```text
Service enabled_events != 真实 Mask
unbind 失败但 Service 清空 route_count
其他通道 pending 未清导致物理 IRQ 重复进入
IRQ_RESULT_CLEAR 与 ISR 交错丢事件
```

### 3.2 整改后

DMA Service 明确定义两种互斥模式：

```text
Managed IRQ Session
  - Service 拥有 route、mask、pending、evidence 和 teardown

Raw Interrupt Register Test
  - 仅在 Managed Session 未激活时允许
  - 由 Case 显式恢复
```

Managed Session 建立步骤：

```text
校验 controller / channel / configured state
  -> 取得分类或 Combined routes
  -> 关闭所有通道的 DMA IRQ masks
  -> 清除所有通道的旧 pending
  -> 保存 Session 状态
  -> 逐 route bind，并记录 route_bound_mask
  -> 使能目标 channel/events
  -> 标记 irq_hardware_enabled
```

任一步失败时，只清除已经确认释放的状态；未成功解绑的 binding 仍保留，允许后续重复执行 `IRQ_DISABLE`。

### 3.3 Callback 证据

Callback 现在：

1. 读取一次控制器级分类中断快照。
2. 对 route 所声明且 Session 已启用的 event 分类检查所有通道。
3. 将目标 `irq_channel` 的事件写入 `latched_events`。
4. 对其他通道事件增加 `unexpected_count`。
5. 对实际出现事件的所有通道执行 clear，避免共享物理线路持续触发。
6. 所有计数器使用饱和增加，避免自然回卷。

这仍是一个轻量、静态 Session，没有增加每通道动态回调或事件订阅框架。

### 3.4 并发一致性

`IRQ_RESULT_GET` 仍通过 generation 取得一致快照。

`IRQ_RESULT_CLEAR` 不再作为第二个无保护写者，而是：

```text
enter Framework IRQ critical
  -> clear_result_locked
exit Framework IRQ critical
```

因此 PC 只能看到完整旧快照或完整新快照，不会出现 generation 为偶数但 ISR 事实被中间覆盖的非法状态。

---

## 4. 通道生命周期与恢复

### 4.1 状态所有权

每个 DMA Service 保存：

```text
controller_enabled
configured_channels
active_channels
resource_pool_owned_channels
route_ownership[channel]
source/destination route interface + address
```

状态变化：

```text
Controller Enable
  disabled -> enabled

Channel Configure
  unconfigured
    -> 校验配置和地址
    -> 获取 Resource pool lease
    -> 获取所需 peripheral route lease
    -> 写硬件配置
    -> configured

Channel Start
  configured + inactive
    -> 清旧 terminal facts
    -> active

Channel Status
  active
    -> 读取 raw terminal events
    -> CHENREG free 时清 active 标记

Channel Stop
  active -> configured/inactive

Channel Deconfigure
  configured
    -> 硬件 deinit
    -> release route leases
    -> release resource lease
    -> idle

Controller Disable
  仅当无 IRQ、无 configured channel、无 lease 时允许
```

### 4.2 幂等清理

以下操作允许重复调用：

- 停止已经 inactive 的 configured channel；
- deconfigure 已经 idle 的 channel；
- disable 已经关闭的 controller；
- disable 已经关闭的 Managed IRQ Session。

清理失败时，Service 不提前删除 ownership 位。下一次调用仍可根据保存状态继续清理。

### 4.3 Configure 超时

Mutating Configure 的响应丢失时，PC 无法知道固件是否已经配置成功。当前 Driver 处理为：

```text
configure request timeout
  -> 发送 retry-safe deconfigure(channel)
  -> 将远端恢复为 idle
  -> 向 Case 抛出原始 timeout
```

不对 Configure 本身盲目重发，避免重复执行状态不明确的修改。

---

## 5. 地址、LLI 与外设端点安全

### 5.1 普通内存地址

DMA memory side 必须落在 Resource Service 当前有效资源中，并校验：

```text
transfer_count > 0
width = 1/2/4 bytes
起始地址对齐
increment: start + span 不越界
 decrement: start - delta 不下溢
gather/scatter: span 包含所有 interval 跳跃
整个实际访问区间属于一个有效 Resource descriptor
```

固定地址模式只验证一个 transfer item 的范围。

### 5.2 传输类型约束

```text
M2M
  source: Resource memory
  destination: Resource memory
  interfaces: memory interface

M2P
  source: Resource memory
  destination: fixed address
  destination interface/address: 当前 SYSCTRL route

P2M
  source: fixed address
  source interface/address: 当前 SYSCTRL route
  destination: Resource memory

P2P
  source/destination: fixed address
  两端 interface/address 均匹配当前 SYSCTRL route
```

因此错误的外设递增地址不会再连续写相邻寄存器，伪造的 MMIO 地址也不能仅凭“看起来像 UART 地址”通过。

### 5.3 SYSCTRL Route lease

SYSCTRL Wrap 保存每个：

```text
controller + interface
  -> endpoint type
  -> UART instance
  -> endpoint address
  -> lease_count
```

DMA Channel Configure 成功前获取 route lease；deconfigure 后释放。Route 被 lease 时：

- 相同配置可幂等确认；
- 不同 endpoint 不能覆盖；
- release route 返回 BUSY。

这避免 Case 在 DMA 仍配置或运行时重设 DMAMUX。

### 5.4 Resource pool lease

DMA Channel Configure 获取一个全局 Resource pool lease，deconfigure 后释放。lease 存在时：

- `RESOURCE_RESET` 返回 BUSY；
- Resource write/fill 返回 BUSY；
- 可变 `resolve_range` 返回 BUSY；
- Resource read 仍允许，用于完成后的数据观察。

这是有意采用的轻量保守策略。它不需要在 Service 中复制 Resource descriptor，也不增加动态引用图；代价是一个 configured DMA channel 会暂时锁定整个测试资源池。

### 5.5 LLI

旧 Wire：

```text
descriptor raw CPU address
```

新 Wire：

```text
Resource handle
Resource offset
is_last
```

固件通过 `et_resource_wrap_resolve_range()` 验证完整 28-byte descriptor 空间，再调用 Wrap 写描述符。普通配置中的首个 LLP 和后续 `linked_list_address` 也必须属于 Resource pool。

---

## 6. 非阻塞等待与终态证据

### 6.1 移除固件忙等

以下旧命令保留 Command ID 兼容，但固件返回 `NOT_SUPPORTED`：

```text
CHANNEL_START_WAIT
CHANNELS_START_WAIT_ORDER
```

原因：Service handler 内忙等会阻塞整个 ET-Frame 主循环，PC 可能先超时，且此时无法发送 stop/status/recovery。

PC `start_wait()` 现在执行：

```text
CHANNEL_START
  -> 周期性 CHANNEL_STATUS_GET
  -> ERROR: 立即失败
  -> is_free: 成功
  -> timeout: 尝试 CHANNEL_STOP 后抛 TimeoutError
```

### 6.2 终态事件

Channel Status 不再只返回经过 Mask 的分类状态，而是通过 raw interrupt snapshot 提取当前通道 terminal facts。

每次 start 前清除该通道旧事件，因此 Status 中的 ERROR 属于当前一次运行，不是前一 Case 残留。

完成判断变成：

```text
raw ERROR == 0
AND channel is_free == true
```

这比单独使用 `CHENREG==0` 更可靠，但仍不替代真实 Error HIL 和总线故障注入。

### 6.3 Priority 与 Suspend/Resume

当前没有可信独立观察器证明：

- 两个 DMA channel 的真实完成先后；
- Channel Suspend 发生时 block 是否仍在进行。

因此两个 Case 明确 SKIP，而不是输出弱证据 PASS。后续需要 FPGA observer、独立时戳或芯片提供的可靠进度事实后再恢复。

---

## 7. Capability 与跨芯片边界

已经动态化：

- DMA Service 初始化从 Wrap 获取 `channel_count`；
- Channel/mask 校验使用 runtime channel count；
- PC Driver 在取得 Capability 后缓存 channel count；
- Free Channel 返回值按 runtime count 校验；
- Service 注册允许稀疏 controller ID。

仍需后续治理：

1. ET6801 的 Runtime Feature flags 仍由当前 Wrap 编译常量集中声明。
2. P0/P1/P2 中部分“ET6801 全量芯片验收 Case”仍显式遍历 DMA0/DMA1 和部分固定通道。
3. 通用 Helper 已能力驱动，但芯片验收矩阵尚未全部由 Profile 自动参数化。

该剩余项不会阻断 ET6801 当前代码运行，但在新增通道数不同、Feature 裁剪或 controller 编号不连续的芯片前必须完成。

---

## 8. 人工 Review 结论

本轮修改后又进行了多轮代码复查，并追加关闭以下容易遗漏的问题：

1. Managed IRQ 仅关闭目标 channel，可能保留其他 Raw Mask：改为接管前清理所有通道。
2. 外设地址只检查 fixed mode，没有验证 DMAMUX route：增加 SYSCTRL endpoint route state。
3. Gather/Scatter 只按连续区间检查：将间隔跳跃纳入 span。
4. Configured DMA channel 期间 Resource reset 会使地址失效：增加 Resource pool lease。
5. Configured DMA channel 期间 DMAMUX route 可被释放或覆盖：增加 route lease。
6. Resource lease 期间 PC 仍可 write/fill：改为 BUSY，防止 DMA 与 PC 并发写同一 pool。
7. Channel Status 使用 masked status，错误可能被隐藏：改为 raw terminal facts。
8. Start 前未清旧 Error：启动前清该 channel 的所有旧事件。
9. Managed IRQ 所有者仍可被 Channel Deconfigure 删除：deconfigure 前返回 BUSY。
10. Wrap deconfigure 直接把 chip-neutral event bits 传 SDK：恢复显式 mapping。
11. PC mask 校验仍固定 8 通道：改为 runtime channel count。
12. Mutating 命令重试边界不清：只对只读和真正幂等命令声明 retry-safe。

### Review 后接受的保守设计

- 每个 DMA controller 当前只支持一个 Managed IRQ Session。
- Resource lease 当前锁整个 pool，而非按 Resource handle 锁定。
- Priority 和“传输中暂停”保持 blocked。
- 不引入多通道动态 IRQ Session、通用资源图或异步任务框架。

这些取舍符合当前“可靠优先、轻量、边界清晰”的需求。

---

## 9. 已执行验证

### 9.1 Python

已实际执行：

```text
python -m compileall -q pc/et_test_platform
```

结果：通过。

### 9.2 DMA 聚焦单元/契约验证

最终一次聚焦验证覆盖：

- DMA Driver Wire/codec；
- DMA Helper；
- DMA IRQ Case；
- DMA reliability contracts；
- UART/DMA 组合等待契约。

最终一次聚焦套件：57 tests passed。

前序整改批次还执行了更完整的 DMA focused suites，覆盖：

- `test_dma_driver_contract.py`
- `test_dma_extended_driver.py`
- `test_dma_helpers.py`
- `test_dma_interrupt_case.py`
- `test_dma_case_p2.py`
- `test_dma_reliability_contract.py`

均通过。

### 9.3 广泛单元回归

执行：

```text
python -m pytest pc/et_test_platform/framework_validation/unit -q
```

排除两项依赖生成工程记录的既有环境测试。

结果：通过，保留 3 项既有 SKIP。

### 9.4 Host C 语法检查

以 GCC C11、`-Wall -Wextra -Werror` 对本轮相关源码执行 `-fsyntax-only`，包括：

```text
firmware/framework/src/et_irq_manager.c
firmware/wrap/src/et_resource_wrap.c
firmware/wrap/src/et_sysctrl_wrap.c
firmware/wrap/src/et_dma_wrap.c
firmware/services/src/et_dma_service.c
firmware/services/src/et_services.c
firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_ahbdma.c
```

结果：项目代码语法检查通过。Host 64-bit 环境中 CMSIS 存在既有 pointer-width warning，已只对这两类 CMSIS warning 降级，不代表 Keil 构建结果。

### 9.5 Diff 与静态不变量

已检查：

- `git diff --check`；
- 临时 workflow/script 已从最终分支删除；
- Firmware Service 不再调用同步 wait Wrap；
- LLI Case 不再发送 descriptor raw address；
- Resource/route lease 存在；
- Endpoint route validation 存在；
- Runtime channel mask 存在；
- Raw terminal event 检查存在；
- 可靠性契约测试存在。

---

## 10. 尚未执行的真实验证

本轮没有在当前环境执行以下内容，因此不得写成 PASS：

### 10.1 Keil

- ET6801 FPGA/ITCM Target 完整构建；
- ET6801 Silicon/PFLASH Target 完整构建；
- 链接区 `ET_RESOURCE_POOL`、代码尺寸和 RAM 占用检查。

### 10.2 HIL

至少需要重新执行：

1. DMA0/DMA1 M2M 基础矩阵。
2. 1/2/4-byte width 和 increment/decrement/fixed。
3. block 1、边界和最大 4095。
4. Transfer/Block/SRC/DST/Error/Combined IRQ。
5. Managed IRQ 与 Raw Mask 顺序切换。
6. IRQ disable/unbind 后重复 enable。
7. M2P、P2M、P2P UART 外设链路。
8. SYSCTRL route 在 configured channel 期间的 BUSY 行为。
9. Resource reset/write/fill 在 lease 期间的 BUSY 行为。
10. LLI 2/3/4 节点、单侧 LLI、DONE 写回。
11. Gather/Scatter 边界和越界拒绝。
12. Hardware/Software handshake。
13. PC 响应超时、stop/deconfigure 恢复以及下一 Case 无污染。
14. DMA Error 安全注入和 raw ERROR 终态识别。
15. 连续多轮 Case、随机顺序和失败后恢复。

### 10.3 需要独立观察器后才能恢复

- Priority arbitration completion order。
- 真正处于进行中 block 的 Suspend/Resume。

---

## 11. 剩余 P2 工作

以下不属于本轮未关闭的 P1 生产可靠性问题，但应进入后续平台治理：

1. Runtime Capability 从构建配置和 Driver 可用 API 自动派生。
2. DMA 芯片验收矩阵由 Profile 自动生成 controller/channel 参数。
3. C/Python DMA Wire schema 生成式统一。
4. 建立可注入 Wrap、IRQ Manager、clear/unbind/deconfigure 失败的 native DMA Service harness。
5. DMA 专项 JSON 与通用 CaseResult、Git commit、firmware build、profile SHA 自动关联。
6. 资源池从全局 lease 逐步优化到按 Resource handle lease，仅在确有并发需求时实施。

---

## 12. 最终结论

当前 DMA 已从：

```text
多入口修改 IRQ
通道状态不可恢复
任意地址可写
固件忙等
弱终态证据
硬编码通道假设
```

收敛为：

```text
单 Managed IRQ 所有者
显式 controller/channel 生命周期
受 Resource 与 SYSCTRL route 约束的地址
Resource/route lease
PC 侧非阻塞轮询
raw ERROR + free 的终态判断
runtime channel count
不可证明 Case 明确阻止 PASS
```

从代码层面看，本轮审查确认的 DMA P1 可靠性问题已经完成整改和 Host 验证；剩余工作主要是 Keil 构建、真实 HIL、独立观察器，以及少量 P2 跨芯片与证据治理。只有这些真实验证完成后，才能将 DMA 整体状态升级为硬件 PASS。
