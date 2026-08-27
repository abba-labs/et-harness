# UART 可靠性整改完成 Review

文档状态：代码整改完成，静态/单元/Host 语法验证通过，Keil 与 HIL 待执行  
整改日期：2026-08-05  
整改分支：`codex/uart-review-fixes-20260805`  
最终代码提交：`16e25e969b659bbeb1af955cb577bc47d435244e`  
关联问题分析：[UART 全链路代码评审与优化设计](20260805_uart_full_chain_code_review.md)

---

## 1. 整改边界

本轮按照已确认的工程约束完成 UART 整改：

1. `firmware/services/src/et_uart_service.c` 保持单文件，不拆分编译单元。
2. 单文件内部使用清晰区域分隔，按 Wire、IRQ 映射、传输、IRQ/Capture、生命周期、FIFO/DMA、命令和公共接口组织。
3. 不引入 RTOS、动态内存、事件总线、插件系统或通用状态机框架。
4. PC Driver 保持 UART API 边界；非法参数继续由 PC unit test 拦截，不给普通 Case 增加 raw Wire 逃生口。
5. Control UART 继续作为 ET-Frame 控制链路，不暴露为可重配置 UART Test Service。
6. 静态芯片能力、运行固件能力和 Bench 可达性保持分层，不相互写回或静默合并。

---

## 2. 问题闭环状态

| ID | 最终状态 | 整改结论 |
|---|---|---|
| REV-001 | 已关闭 | Control UART 不再要求出现在 UART Test Service Registry；DUT/Peer 仍分别执行 Runtime Service 与静态实例门禁。 |
| REV-009 | 已修复待 HIL | 每个 UART 实例只保留一个 IRQ binding 和一个 `uart_irq_callback()`；Capture 与普通 IRQ 使用统一的 applied mask。 |
| REV-010 | 已关闭 | `IRQ_STATE_GET` 改为纯缓存快照；IRQ Case 必须同时看到 callback count 增量和目标 source。 |
| REV-011 | 已关闭 | PC 行配置统一编码；普通配置只允许 5–8 bit；9-bit 由独立命令管理；1.5/2 stop bits 语义统一。 |
| REV-012 | 已修复待 HIL | `DMA_ENABLE_SET`、`FIFO_CONFIG`、`DMA_MODE_SET` 统一进入一个 FIFO/DMA 状态应用函数；删除绕过 handle 的 Wrap API。 |
| REV-013 | 已修复待 HIL | 生命周期收敛到幂等 `uart_reset_to_idle()`；初始化失败回滚、重复 deinit、IRQ unbind 失败重试和默认优先级恢复均有明确状态。 |
| REV-014 | 已关闭（按批准范围） | 不拆 `.c`；通过区域分隔、私有 helper、状态所有权和契约测试治理单文件复杂度。 |
| REV-015 | 已关闭 | 建立分层准入分类：`skip_by_chip_capability`、`skip_by_runtime_service`、`skip_by_runtime_feature`、`skip_by_bench`；UART Runtime Feature 使用共享 helper。 |
| REV-016 | 接受现状 | 按产品决策保留 PC 本地非法参数校验，不扩展为普通 UART HIL raw-frame 测试。 |

“已修复待 HIL”表示代码与 Host 验证闭环，但真实 NVIC、UART、DMA 和板级连线仍必须通过 Keil 构建与 HIL 复测后才能写成硬件 PASS。

---

## 3. 关键实现 Review

### 3.1 单一 IRQ 所有者

整改前：

```text
uart_irq_event()
uart_capture_irq()
两套 binding / route / mask
```

整改后：

```text
一个物理 UART IRQ
  -> uart_irq_callback()
      -> 一次读取 Wrap snapshot
      -> 锁存配置事件证据
      -> Capture 活动时读取 FIFO
      -> 清除本次硬件 snapshot
      -> 重新计算统一硬件 mask
```

最终状态只保留：

- 一个 `irq_route`
- 一个 `irq_bound`
- `irq_enabled_mask`：PC 配置语义
- `irq_applied_wrap_mask`：真实已写入硬件的 mask
- `irq_suppressed_wrap_mask`：TX Empty 等 one-shot source 已观测后的抑制状态

TX Empty 观测后会进入 suppressed 状态，Capture 或其他 mask 重算不会意外重新开启；只有显式 `IRQ_CONFIG` 才能 re-arm。

### 3.2 Capture 与普通 IRQ 合并

Capture 不再拥有独立 callback，也不直接无条件关闭 RX Ready/Timeout。

统一计算：

```text
configured IRQ mask
AND NOT one-shot suppressed mask
OR capture internal RX mask（仅 capture_active 时）
```

因此：

- Capture 完成只移除自身内部需求；
- 普通 RX Ready/Timeout 配置仍然保留；
- Capture cancel 不会误伤普通 IRQ；
- Capture 与 IRQ_CONFIG 不再依赖 IRQ Manager binding 数组顺序。

Capture 状态增加 generation 保护，`CAPTURE_GET` 只返回同一时刻的一致快照；读取到“非 active 且未达到 expected”的状态时，PC helper 会明确报告 capture aborted，而不是持续等待到笼统 timeout。

### 3.3 IRQ 证据语义

`IRQ_STATE_GET` 不再调用 `et_uart_wrap_get_interrupt_status()`，也不会补写 pending/active。

IRQ 证据只来自真正执行的 IRQ callback：

```text
callback 执行
  -> event_count 增加
  -> pending/active 锁存目标 source
```

PC `_require_irq_event()` 的通过条件收紧为：

```text
event_count delta > 0
AND
目标 source 出现在 pending/active
```

解决了“只轮询到寄存器状态但 NVIC/IRQ Manager/Service callback 未执行也可能 PASS”的问题。

### 3.4 生命周期与失败恢复

新增唯一生命周期回收入口：

```text
uart_reset_to_idle()
```

它负责：

- 阻止新 ISR 进入业务路径；
- 关闭已应用硬件 IRQ；
- 解绑唯一 IRQ callback；
- 释放并 reset UART Wrap handle；
- 清除 Capture、IRQ Evidence、FIFO/DMA 缓存；
- 恢复启动默认 IRQ priority；
- 回到唯一 idle 基线。

额外 Review 修复：

- `et_irq_manager_unbind()` 失败时不再错误清除 `irq_bound/irq_route`；后续幂等 reset 可以继续重试。
- `SOFTWARE_RESET` 不再先执行一次硬件 reset、随后 deinit 再 reset；现在只使用统一 idle reset 路径。
- `DEINITIALIZE` 在已经 idle 时返回成功，适合远程命令响应丢失后的安全恢复。

### 3.5 FIFO/DMA 状态所有权

三条兼容 Wire Command 仍保留，但内部只使用一套状态：

```text
fifo_enabled
fifo_tx_threshold
fifo_rx_threshold
dma_mode
```

统一进入：

```text
uart_apply_fifo_dma_state()
```

应用顺序：

1. 校验完整 proposed state；
2. 应用 FIFO 与 DMA 硬件设置；
3. 全部成功后提交 Service cache；
4. 中途失败时用旧状态回滚；
5. 回滚失败返回明确 I/O error，不伪装成功。

已删除 `et_uart_wrap_set_dma_enabled(uart_id, ...)`，避免绕过 initialized handle 与 Service 状态所有权。

### 3.6 PC UART 行配置

`initialize()` 与兼容入口 `configure_extended()` 现在共享同一编码函数。

规则：

- 普通 Line Config：5–8 data bits；
- 9-bit：只允许使用 `nine_bit_config()`；
- 5 data bits + 1.5 stop：Wire value 2；
- 6–8 data bits + 2 stop：Canonical Wire value 3；
- 旧调用方传 raw integer 2 时继续按历史“2 stop bits”解释，但新 Wire 不再生成含糊值；
- 非法语义在 PC 发请求前抛出 `ValueError`。

### 3.7 Capability Gate 分层

最终准入分类：

```text
Chip/SVD 静态实例缺失     -> skip_by_chip_capability
运行固件未注册 Service    -> skip_by_runtime_service
运行 Service 未声明 Feature -> skip_by_runtime_feature
Bench 角色/连线不匹配      -> skip_by_bench
```

`filter_profile_instances_by_registry()` 明确表示它只过滤实例；Runtime Feature 不写回 SVD Profile。P2/P3 的 UART Feature gate 统一使用 `require_uart_runtime_feature()`。

---

## 4. 单文件结构治理

`et_uart_service.c` 继续保持一个文件，当前区域为：

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

本轮未引入命令描述表或新编译单元。后续新增命令必须放入相应区域，并保持：

1. 查询命令不修改状态；
2. 配置命令先校验、后应用、最后提交缓存；
3. 每个硬件状态只有一个 Service 私有所有者；
4. Case 不直接访问 Wire 或寄存器；
5. Wrap 只做稳定语义到 SDK 的映射。

---

## 5. 验证结果

### 5.1 回归测试

最终验证环境：GitHub Actions Ubuntu 24.04、Python 3.11。

执行：

```text
python -m compileall -q pc/et_test_platform
```

结果：PASS。

UART 聚焦套件：

```text
pytest:
- test_uart_driver.py
- test_uart_firmware_contract.py
- test_uart_cases_contract.py
- test_uart_fixtures.py
- test_uart_reliability_contract.py
- test_capability_profile.py
```

结果：72 项 PASS。

广泛 Unit/Static Contract 回归：

```text
python -m pytest pc/et_test_platform/framework_validation/unit -q
  -k 'not generated_keil_project_matches_generation_record
      and not generated_keil_project_uses_only_firmware_source_files'
```

结果：其余选中测试全部 PASS，3 项按既有环境条件 SKIP。

两个被排除项是现有 Windows/Keil 绝对路径契约，在 Linux Host 上不可直接执行；本轮未把它们标记为通过。

### 5.2 C Host 语法检查

执行对象：

```text
firmware/services/src/et_uart_service.c
firmware/wrap/src/et_uart_wrap.c
```

使用 ET6801 与 Test Driver Extension 宏，启用：

```text
-std=c11 -Wall -Wextra -Werror -fsyntax-only
```

结果：PASS。

仅对 CMSIS 在 64-bit Host 上产生的 `int-to-pointer-cast` / `pointer-to-int-cast` 降级为普通 warning；这些 warning 位于 ARM CMSIS Header，不来自本轮 UART Service/Wrap 代码。其他 warning 仍按 `-Werror` 处理。

### 5.3 Diff 与架构门禁

验证结果：

- `git diff --check` PASS；
- 双 callback/双 route 旧字段和 helper 已移除；
- handle-bypassing DMA Wrap API 已移除；
- one-shot suppression 与 default IRQ priority 存在契约测试；
- 临时 workflow 和 review patch script 已全部删除；
- 代码中没有保留生成器或压缩 payload。

关键验证运行：

- UART 状态与 C 语法整改：GitHub Actions Run `30995062895`，成功；
- Capability Gate 收口：GitHub Actions Run `30995488342`，成功。

---

## 6. 人工 Review 结论

完成自动验证后，又对以下关键路径进行了人工复核：

1. `uart_apply_irq_mask()` 的 disable/enable/rollback 顺序；
2. TX Empty one-shot suppression 与显式 re-arm；
3. Capture 开始、完成、取消时对普通 IRQ mask 的影响；
4. IRQ priority rebind 失败时的旧 binding 和硬件 mask 恢复；
5. `uart_reset_to_idle()` 在 unbind 失败后的可重试状态；
6. 初始化每个失败点是否回到唯一 idle；
7. FIFO/DMA 第二步失败后的旧状态回滚；
8. PC 5/6/7/8-bit 与 1/1.5/2 stop bits 编码；
9. Control UART 与 DUT/Peer UART 的职责分离；
10. Chip、Runtime Service、Runtime Feature、Bench 四类准入原因。

本次人工 Review 发现的二次问题（TX Empty 被 Capture 意外 re-arm、unbind 失败丢失 binding、默认 priority 未恢复、重复软件 reset、旧 DMA Wrap API）均已增加回归测试并修复。

---

## 7. 尚未执行的验证

以下内容仍需在有工具链和硬件的环境执行，不能由本报告写成 PASS：

### Keil 构建

至少需要：

```text
ET6801 FPGA/ITCM Target
ET6801 Silicon/PFLASH Target
```

检查：

- C 编译器差异；
- struct size/ABI；
- warning；
- 链接空间；
- generated Keil project 路径契约。

### HIL

至少复测：

1. HELLO / SERVICE_LIST；
2. UART internal loopback；
3. UART1/UART2 paired transfer；
4. RX Ready IRQ；
5. TX Empty IRQ one-shot 与显式 re-arm；
6. Character Timeout；
7. Error IRQ；
8. 9-bit address IRQ；
9. 连续多次 Capture；
10. UART TX DMA、RX DMA、full duplex DMA；
11. Case 中途失败后下一 Case 恢复；
12. 重复 deinitialize 和软件 reset。

---

## 8. 最终结论

本轮代码整改已经达到静态与 Host 验证范围内的目标：

```text
双 IRQ 所有者          -> 单一 IRQ callback 与 mask owner
查询补写中断证据       -> callback-only evidence
多条 FIFO/DMA 状态路径 -> 单一事务状态
非幂等清理             -> 唯一 reset_to_idle
含糊 Line Config       -> 单一 canonical encoder
能力原因混杂           -> 分层稳定分类
大文件无结构           -> 单文件区域治理
```

代码保持静态、无动态内存、无新通用框架；兼容 Wire Command 保留，但内部状态所有权已经收敛。下一步只有 Keil 与真实 HIL 复测，不再需要继续追加架构重构。
