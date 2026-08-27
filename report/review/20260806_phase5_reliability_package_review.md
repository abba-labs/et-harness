# Phase 5：可靠性与 Package 全面收敛 Review

文档状态：正式 Review 结论  
Review 日期：2026-08-06  
目标仓库：`Abba-shenfu/Automated_Testing_Platform`  
目标分支：`review_code`  
代码验证基线：`5b12f754c9093c216e6809cda050379c90e42e11`  
GitHub Actions：`PC Quality Gate` Run `31095000465`

---

## 1. Review 结论

Phase 5 规定的六个工作包已经完成：

```text
5A  DMA 严格 Deadline 与异常语义
5B  UART PC Package 与可靠性
5C  UART Firmware Cleanup 可重试
5D  IRQ Manager / Frame Parser 公共可靠性
5E  Resource / Framework / CRG 等 PC Package 规范化
5F  全量质量门禁与零 Allowlist
```

本阶段完成后：

- DMA 和 UART 的长操作均由一个总 `OperationDeadline` 管理；
- Primary Error 与 Cleanup Errors 可以同时保留；
- UART、Resource、Framework、CRG 已按 Model/Contract/Codec/Validation/Driver 分层；
- UART Firmware Cleanup、IRQ Manager Cleanup 均支持失败后从未完成步骤继续；
- Frame Parser 可在没有新字节时继续输出已缓存完整帧；
- Phase 5 PC 生产代码与全部 Unit/Contract 测试受统一 Ruff/AST 门禁；
- `pyproject.toml` 中历史 Ruff Allowlist 已清零；
- 最终 CI 通过。

结论：

```text
Phase 5：可靠性与 Package 全面收敛 —— DONE
```

允许进入：

```text
Phase 6：Test Case、Keil、HIL 与最终交付
```

---

## 2. 5A：DMA 严格 Deadline 与异常语义

### 2.1 新公共等待入口

新增：

```python
wait_complete(
    channel,
    *,
    timeout_s,
    poll_interval_s=0.001,
)
```

执行路径：

```text
创建一个 OperationDeadline
→ CHANNEL_START 使用 remaining_s()
→ 每次 CHANNEL_STATUS_GET 使用同一个 remaining_s()
→ 未完成时由 Deadline.sleep() 消耗剩余预算
→ 完成返回
```

旧接口：

```python
start_wait(channel, max_polls, poll_interval_s)
```

保留为 Compatibility Alias，通过 `max_polls * poll_interval_s` 转换为总 Deadline，不再拥有独立等待实现。

### 2.2 Primary Error 与 Cleanup Errors

ERROR 或 Deadline Exhaustion 作为 Primary Error。失败后依次尝试：

```text
CHANNEL_STOP
CHANNEL_DECONFIGURE
```

两个清理动作全部执行；失败通过：

```text
run_cleanup()
raise_with_cleanup()
OperationCleanupError
```

与 Primary Error 同时保留，不再由最后一个 Cleanup Error 覆盖原始失败。

### 2.3 测试

新增：

```text
framework_validation/unit/drivers/dma/test_deadline.py
```

覆盖：

- Fake Clock 下各子请求的 Deadline 单调递减；
- Deadline Exhaustion 后 Stop/Deconfigure 顺序；
- ERROR 与两个 Cleanup Failure 同时可见；
- `start_wait()` 兼容入口委托严格 Deadline。

---

## 3. 5B：UART PC Package 与可靠性

### 3.1 Package 拆分

删除：

```text
pc/et_test_platform/drivers/uart.py
```

新增：

```text
pc/et_test_platform/drivers/uart/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

职责：

| 文件 | 职责 |
|---|---|
| `models.py` | 稳定枚举和返回模型 |
| `contract.py` | Service ID、Command ID、稳定常量 |
| `codec.py` | Struct、Wire Body 编解码、Response Length/Reserved 检查 |
| `validation.py` | UART 本 IP 参数校验 |
| `driver.py` | 单 UART Service 操作、Deadline、Polling、Cleanup |
| `__init__.py` | 旧 Public Import 兼容 Facade |

旧导入路径保持：

```python
from et_test_platform.drivers.uart import UartDriver
```

### 3.2 总 Deadline

以下操作均使用一个总 Deadline：

```text
write
read_exact
write_9bit
read_9bit
exchange
```

`exchange()` 不再为内部 Write 和 Capture 另建第二个 Deadline，其完整顺序为：

```text
CAPTURE_START
→ WRITE 循环
→ CAPTURE_GET 循环
→ 返回数据
```

每个 Target 请求都接收同一个 `OperationDeadline.remaining_s()`。

### 3.3 Cleanup 与 9-bit 校验

`exchange()` 失败后尝试 `CAPTURE_CANCEL`；取消失败与 Primary Error 同时保留。

9-bit API 在发送请求前校验：

- `timeout_s`；
- `poll_interval_s`；
- `max_polls`；
- Word Count；
- 9-bit Value 范围；
- Response 长度和 10-bit 非法值。

### 3.4 Public API 与 Wire

保持：

- UART Service ID；
- 所有已发布 Command ID；
- Struct Size；
- Line Config Wire；
- DMA Mode Wire；
- 旧公开枚举别名；
- Golden Bytes。

新增测试：

```text
framework_validation/unit/drivers/uart/test_uart_package.py
```

覆盖 Package 兼容、Line Config Golden Bytes、总 Deadline、Exchange Cleanup、9-bit 参数和 DMA Mode Wire。

---

## 4. 5C：UART Firmware Cleanup 可重试

`uart_reset_to_idle()` 已改为分步骤提交状态：

```text
Disable IRQ 成功
→ 清 irq_applied_wrap_mask

Unbind 成功
→ 清 irq_bound / irq_route

Deinit 成功
→ 清 initialized / handle
```

失败时保留尚未完成步骤所需的真实状态：

- Disable 失败时保留 Applied Mask、Binding、Handle；
- Unbind 失败时保留 Binding、Route、Handle；
- Deinit 失败时保留 Initialized 和 Handle；
- 再次调用只重试未完成的物理步骤；
- Cleanup Fault 通过 UART IRQ Fault 计数可见。

Initialize 中途失败继续使用同一个 `uart_reset_to_idle()` 入口，不建立另一套回滚逻辑。

新增 Failure Injection：

```text
framework_validation/unit/test_uart_cleanup_native.py
```

该测试从生产源文件提取 `uart_reset_to_idle()`，分别注入：

- Disable 第一次失败；
- Unbind 第一次失败；
- Deinit 第一次失败。

验证第二次清理成功、已完成步骤不重复、真实 Handle/Binding 不提前丢失。

---

## 5. 5D：公共 Firmware Reliability

### 5.1 IRQ Manager

更新：

```text
firmware/framework/include/et_irq_manager.h
firmware/framework/src/et_irq_manager.c
```

每个 Binding 增加 Cleanup Progress：

```text
ET_IRQ_CLEANUP_DISABLED
ET_IRQ_CLEANUP_PENDING_CLEARED
ET_IRQ_CLEANUP_UNREGISTERED
```

行为：

- Disable 成功后才记录 Disabled；
- Clear Pending 成功后才记录 Pending Cleared；
- Unregister 成功后才记录 Unregistered；
- Unbind/Deactivate 失败时保留 Binding 和已完成进度；
- 重试从第一个未完成物理步骤继续；
- 所有 Line 完成前不清 `active_manager`；
- Bind 回滚失败计入 `cleanup_fault_count`；
- Cleanup 进行中的 Binding 不再 Dispatch。

新增 Native Harness：

```text
framework_validation/native/et_irq_manager_reliability_harness.c
framework_validation/unit/test_irq_manager_reliability_native.py
```

覆盖 Clear、Unregister、Bind Rollback Failure 和 Deactivate Retry。

### 5.2 Frame Parser Buffered Drain

更新：

```text
firmware/framework/include/et_frame.h
firmware/framework/src/et_frame.c
firmware/framework/src/et_protocol.c
```

新增：

```c
et_frame_parser_drain(parser, frame)
```

Parser 在成功输出一帧后只消费该帧，保留后续缓存字节。Protocol 每次 Poll 在读取 Transport 前先 Drain Parser Buffer，因此：

```text
第一完整帧输出
→ 第二完整帧仍在 Buffer
→ 即使没有新字节，下一次 Poll 仍可继续输出第二帧
```

新增 Native Harness：

```text
framework_validation/native/et_frame_buffered_drain_harness.c
framework_validation/unit/test_frame_buffered_drain_native.py
```

---

## 6. 5E：PC Package 全面规范化

### 6.1 Resource

删除单文件并拆分：

```text
pc/et_test_platform/drivers/resource/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

Resource Driver 只负责固定池资源的 Create/Read/Write/Fill/Info，不承担跨 IP 资源图和 Route 推导。

### 6.2 Framework

拆分为同样的 Package 结构，完成：

- HELLO/VERSION/SERVICE_LIST/STATISTICS Wire 解码移入 Codec；
- Registry Hash 移入 Codec；
- Session ID 校验移入 Validation；
- Driver 只负责 Framework Service 操作与 Cache；
- 旧 `Model.decode()` 和 `_registry_hash` 入口由 Facade 兼容。

### 6.3 CRG

拆分为 Model/Contract/Codec/Validation/Driver，Driver 只操作 CRG Service。

### 6.4 TargetClient

为清除最后的 C901 技术债，将 `request()` 拆分为：

```text
_encode_request
_allocate_attempt_deadline
_read_attempt_response
_select_matching_response
_validate_response_identity
_raise_if_rejected
_prepare_retry
```

保持：

- 一个总 Request Deadline；
- 非幂等请求默认不重试；
- Retry-safe 请求只重试一次；
- 第二次发送复用完全相同的编码 Frame；
- Event Queue 和 TargetRejected 语义。

---

## 7. 5F：质量门禁与零 Allowlist

### 7.1 统一质量范围

`tools/validate_pc.py` 当前覆盖 Phase 5 的全部 PC 生产目录：

```text
cli
clients
communication
core
drivers
instruments
profiles
programmers
pytest_plugin.py
results
scheduling
framework_validation/unit
```

`test_cases` 明确保留给 Phase 6 的 Feature/可读性重构，不作为隐式 Allowlist。

### 7.2 Ruff / AST

完成：

- Phase 5 范围全部 Ruff Format；
- Ruff Lint 全部通过；
- AST Architecture Rules 全部通过；
- Driver 跨 IP Import 检查；
- Driver 直接 Struct 检查；
- Codec/Model 边界检查；
- Production Assert 检查；
- Public API Type Annotation 检查；
- Module Docstring 检查。

`pyproject.toml` 已删除：

```text
[tool.ruff.lint.per-file-ignores]
```

并删除全部 `C901` 豁免。当前历史 Ruff Allowlist 数量：

```text
0
```

---

## 8. 最终自动验证证据

```text
Workflow : PC Quality Gate
Run ID   : 31095000465
Commit   : 5b12f754c9093c216e6809cda050379c90e42e11
Result   : SUCCESS
```

实际门禁：

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Committed Keil Artifact Contract      PASS
PC Unit / Contract / Native Harness    299 passed, 3 skipped
```

Native Harness 包括：

- 既有 Common Reliability Harness；
- IRQ Manager Retryable Cleanup；
- Frame Parser Buffered Drain；
- UART Firmware Cleanup Failure Injection。

三个环境门禁保持为 `SKIPPED`，未写成 PASS。

---

## 9. Keil 与 HIL 状态

| 验证层级 | Phase 5 状态 | 说明 |
|---|---|---|
| Python Syntax/Ruff/AST | PASS | GitHub Actions 实际执行 |
| Host Unit/Contract | PASS | `299 passed, 3 skipped` |
| Native Harness | PASS | CI 实际编译执行 |
| Keil 提交物 Contract | PASS | 仅仓库结构/Hash 合同 |
| ET6801 FPGA Keil Build | NOT_EXECUTED | Phase 6 执行 |
| ET6801 Silicon Keil Build | NOT_EXECUTED | Phase 6 执行 |
| 真实 HIL | NOT_EXECUTED | Phase 6 执行 |

Keil 提交物 Contract 不等同于真实 Keil Build。

---

## 10. 未关闭事项

剩余工作全部属于 Phase 6：

1. Test Case 按主要测试主体和 Feature 重组；
2. Hardware Case Docstring、步骤、证据、断言和 Cleanup 可读性收敛；
3. UART DMA Case 迁移到 SYSCTRL V2 / DMA LLI V2；
4. 全量静态和 Host 回归；
5. ET6801 FPGA Target 实际 Keil Build；
6. ET6801 Silicon Target 实际 Keil Build；
7. Framework、Resource、DMA、UART、UART DMA 和 Cleanup 真实 HIL；
8. Final Architecture Review 和最终报告。

---

## 11. 是否允许进入下一阶段

允许进入：

```text
Phase 6：Test Case、Keil、HIL 与最终交付
```

Phase 6 仍必须保持：

- Test Case 是跨 IP 编排和最终 PASS/FAIL 的唯一所有者；
- UART DMA Case 归入 UART；
- Driver 不跨 IP；
- Firmware Service 只调用本 IP Wrap；
- 未实际执行 Keil/HIL 不得写成 PASS；
- 整体计划只有在真实 Build、HIL 和 Final Review 完成后才能标记 `COMPLETED`。
