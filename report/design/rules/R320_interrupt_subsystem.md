---
schema: et.rule-document.v1
number: R320
domain: firmware
lifecycle: active
owners: [interrupt_subsystem]
rule_ids: [ET-RULE-INTERRUPT-SUBSYSTEM]
---

# R320 Firmware中断规则

## 1. 定位

本文定义从“公共IP语义事件”到“芯片物理IRQ Line”的绑定、分发、状态和清理。公共Case、Driver、Service和Wrap不得依赖芯片启动文件中的Handler名称。

## 2. 三层标识

```text
semantic event   例如 transfer_complete
logical route    例如 instance + optional channel + event
physical IRQ     芯片IRQn / vector / shared line
```

PC只使用语义事件和公共实例/通道。Chip Config和启动适配负责逻辑Route到物理IRQ。物理IRQ新增、删除、合并或共享不得改变已发布的公共事件语义。

## 3. 固定职责

| 层 | 职责 |
|---|---|
| PC Case | 请求事件、产生刺激、读取结果、最终断言 |
| PC Driver | 编码事件Mask和公开IRQ动作 |
| IP Service | 调用本IP Wrap开关IP中断源，注册本IP回调，保存固定容量事件快照 |
| IP Wrap | 只操作本IP中断Enable/Mask/Raw/Clear/Force Driver API |
| IRQ Manager | 绑定逻辑Route与回调，分发、计数和解绑 |
| IRQ Wrap | NVIC使能、优先级、Pending和物理Line控制 |
| Chip/Startup | 提供IRQn、向量和共享Line入口 |

`IP Service -> IRQ Manager`是唯一公共绑定入口。`IP Service -> IRQ Wrap`、`IP Wrap -> IRQ Manager/IRQ Wrap`均禁止。

## 4. 注册和执行链路

```text
PC: irq_enable(instance, channel, event_mask)
  -> IP Service validates semantic event
  -> IP Service clears stale IP raw/status
  -> IP Service binds logical route to its callback in IRQ Manager
  -> IRQ Manager configures physical line through IRQ Wrap
  -> IP Service enables own IP interrupt source through Own Wrap

hardware event
  -> startup vector / shared-line entry
  -> IRQ Manager dispatch
  -> IP Service callback
  -> Own Wrap reads and clears IP source
  -> Service updates fixed snapshot/counter
  -> PC irq_result_get()
```

使能顺序和失败回滚必须严格逆序；清理时先关闭本IP源，再解绑Route，最后在无使用者时关闭物理Line。

## 5. 回调和ISR

- ISR/回调只读取必要状态、清除已识别源、更新固定计数和推进已启动的本IP异步状态。
- 禁止动态分配、阻塞等待、协议解析、日志格式化、跨IP调用和最终测试判断。
- 未识别源、计数溢出、回调缺失和清除失败必须进入可查询Fault字段。
- 共享Line必须遍历已注册Route并由各IP读取自己的Raw状态；不得假定一个Line只有一个事件。

## 6. 状态模型

最小快照包含：

```text
raw_status
masked_status
latched_events
event_count
unexpected_count
overflow_count
generation
fault_flags
```

`generation`在每次新会话递增，用于区分旧事件。Mask、Force、Clear分别验证真实语义；禁止仅凭回调被调用就判定具体事件正确。

## 7. 缺失、合并和多核

- 芯片没有某语义事件：Capability声明不支持，公共命令返回`NOT_SUPPORTED`。
- 多事件合并为一个向量：Chip/IRQ Manager共享Line，Service按Raw状态区分。
- 向量存在但硬件事件不可产生：Case按R210记录DEFERRED原因，不伪造Force覆盖真实路径。
- 多核使用独立IRQ Manager实例和芯片Route表；公共事件ID保持不变。

## 8. 控制UART

控制UART接收ISR属于Framework通信路径，只搬运字节到环形缓冲区并记录错误；不进入IP Service的测试事件会话。协议解析在主循环执行，禁止在UART ISR中解析ET-Frame或运行Case命令。

## 9. 验证

```powershell
python tools/quality/check_firmware_architecture_rules.py .
python -m pytest -q pc/et_test_platform/framework_validation/unit/firmware_contract/test_irq_manager_reliability_native.py
python -m pytest -q pc/et_test_platform/framework_validation/unit/firmware_contract/test_irq_capture_fault_contract.py
python tools/validate_pc.py
```
