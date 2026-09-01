# PC 控制面与 Firmware 执行面重构实施计划

文档状态：已实施设计基线 v1.1（软件层 Final Compliance Closure 后）
制定日期：2026-08-06
目标仓库：`Abba-shenfu/Automated_Testing_Platform`
目标分支：`review_code`
计划基线：`08de20cf13bf0157fcb90377fdeb803469419bca`

关联强制规则：

- `AGENTS.md`
- `report/design/firmware_service_execution_contract.md`
- `report/design/pc_code_design_rules.md`
- `report/design/pc_python_code_style_and_quality_gate.md`
- `report/design/pc_ip_package_template.md`
- `report/design/pc_firmware_architecture_review_checklist.md`

---

## 1. 计划目标

本次重构必须同时完成两类工作，不能只完成其中一类：

1. 解决前期 Review 已确认或仍未充分关闭的架构与可靠性问题；
2. 按最新 PC Python 规范重新组织代码，使 Test Case、Driver、Codec、Resolver 和单元测试可以被人工快速审核。

最终目标固定为：

```text
PC = 可信控制面
Firmware = 命令执行面
```

固定调用关系：

```text
PC Test Case
  -> PC Resolver / Capability
  -> PC IP Driver
  -> Codec / Contract
  -> TargetClient / ET-Frame
  -> Firmware IP Service
  -> 对应 IP Wrap
  -> 对应 Chip Driver
  -> Hardware
```

Firmware Service 的固定公式：

```text
Service = Decode + Execute Own Wrap + Encode Facts
```

PC Test Case 必须是：

- 跨 IP 顺序的唯一所有者；
- 整体 Deadline 和跨 IP Cleanup 的所有者；
- Evidence 的所有者；
- 最终 PASS/FAIL 的唯一所有者；
- 人工审核测试设计的主要入口。

---

## 2. 明确不采用的方案

本轮禁止以下做法：

- 一次性重写全部 PC 代码；
- 同一个提交同时做目录迁移、Wire 改义和功能修复；
- 为了快速删除兼容代码而静默复用旧 Command ID；
- 继续扩展 Firmware Endpoint/Route/Lease Registry；
- 在 Firmware 中重新验证 UART、DMA、SYSCTRL 等跨 IP 关系；
- Driver 调用其他 IP Driver；
- Fixture 或 Helper 隐藏完整 Test Case；
- 使用通用 Workflow Engine、依赖注入容器、插件系统或泛化资源图；
- 为满足行数要求机械拆出 `utils.py`、`common.py`、`helpers.py`、`misc.py`；
- 全仓一次性自动格式化并制造无法审核的大型 Diff；
- 未执行 Keil/HIL 却把结果写成 PASS。

---

## 3. 当前代码现状与确认的问题

### 3.1 PC Driver 仍是单文件聚合结构

当前主要 Driver 仍为：

```text
pc/et_test_platform/drivers/dma.py
pc/et_test_platform/drivers/uart.py
pc/et_test_platform/drivers/framework.py
pc/et_test_platform/drivers/resource.py
pc/et_test_platform/drivers/sysctrl.py
pc/et_test_platform/drivers/crg.py
```

其中 DMA 和 UART 单文件同时承担：

- Command ID；
- Wire `struct.Struct`；
- Enum；
- Dataclass；
- Encode/Decode；
- 参数校验；
- TargetClient 调用；
- Deadline/Polling；
- Cleanup；
- Compatibility。

这与最新规范要求的六文件 Package 不一致：

```text
drivers/<ip>/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

### 3.2 Test Case 仍按 P0/P1/P2/P3 大文件组织

当前 DMA Case 主要集中在：

```text
dma_test_case_p0.py
dma_test_case_p1.py
dma_test_case_p2.py
dma_test_case_p3.py
```

并存在体量较大的：

```text
dma_helpers.py
dma_irq_helpers.py
dma_peer.py
```

当前问题：

- 文件名不能直接表达 Feature；
- 单文件包含多个无直接关系的测试设计；
- 大型 Helper 可能隐藏测试步骤和 Cleanup；
- 单 IP Case 与 UART/SYSCTRL/DMA 跨 IP Case 边界不够明显；
- 当前 Case 说明以函数前注释为主，尚未统一为最新固定 Docstring；
- Feature JSON、Evidence 和 pytest 断言之间仍需要继续统一审核。

### 3.3 PC 单元测试仍为平铺结构

当前 `framework_validation/unit/` 中大量测试平铺在同一目录，尚未镜像源码结构。

目标结构：

```text
framework_validation/unit/
├── code_quality/
├── clients/
├── drivers/
│   ├── dma/
│   ├── uart/
│   ├── sysctrl/
│   ├── framework/
│   └── resource/
├── profiles/
│   └── resolvers/
├── communication/
└── firmware_contract/
```

### 3.4 Firmware 仍承担跨 IP 可信关系

当前 DMA Service 仍依赖 `et_resource_wrap.h`，并承担：

- Memory Range 判断；
- Peripheral Route 判断；
- Resource Pool Lease；
- DMA Route Lease；
- Source/Destination Route Ownership；
- LLI Descriptor Handle 到地址解析。

当前 SYSCTRL Service 仍承担：

- UART Provider 身份；
- Endpoint/Instance/Address 组合校验；
- DMA Route Registry 绑定与解绑。

当前 Resource Wrap 仍包含：

- DMA Endpoint Registry；
- DMA Route Registry；
- Route Lease；
- Pool Lease。

这些职责与最新规则冲突。最终 DMA Service 只能：

```text
解析 DMA 参数
-> 调用 DMA Wrap
-> 返回 DMA 事实
```

最终 SYSCTRL Service 只能：

```text
解析 controller/interface/request_id
-> 调用 SYSCTRL Wrap
-> 返回状态
```

### 3.5 PC Capability 尚缺少执行映射

当前 ET6801 UART Capability 已有：

- UART Instance；
- Base Address；
- IRQ；
- SVD Evidence。

但 PC 端尚未形成稳定、强类型的：

- UART TX/RX DMA Peripheral Address；
- UART TX/RX DMA Request ID；
- DMA Controller/Interface 选择；
- Address、Request ID、Interface 的跨 IP一致性解析结果。

目前这部分信息仍有一部分保存在 Firmware `et_chip_wrap_config.h` 的 UART DMA Request 表中。

重构后必须建立 PC 端 Chip Execution Mapping，且与 SVD 自动生成 Capability 分开，避免人工内容被重新生成覆盖。

### 3.6 已确认的 PC 可靠性问题

#### PC-REL-001：UART 子请求未继承整体 Deadline

UART `write()`、`read_exact()`、9-bit I/O 和 `exchange()` 虽然计算外层 Deadline，但内部 `_request()` 没有接收剩余时间，TargetClient 仍可对每次请求使用自身默认超时。

影响：

- 外层 `timeout_s` 不是严格总 Deadline；
- 单次子请求可能超过整体时间；
- 多次轮询会放大超时时间。

#### PC-REL-002：UART Exchange 使用两个独立超时窗口

当前 Exchange：

1. 调用 `write(..., timeout_s=...)`；
2. Write 完成后重新建立 Capture Deadline。

因此一次 Exchange 最坏可使用约两倍超时。

#### PC-REL-003：UART Exchange 吞掉 Cleanup Error

当前异常路径中 `capture_cancel()` 失败被 `except Exception: pass` 吞掉。

要求：保留 Primary Error，并同时暴露 Cleanup Error。

#### PC-REL-004：UART 9-bit I/O 策略参数检查不完整

9-bit Read/Write 需要与普通 I/O 一致校验：

- `timeout_s > 0`；
- `poll_interval_s > 0`；
- 使用同一个总 Deadline；
- 子请求传递剩余时间。

#### PC-REL-005：DMA `start_wait()` 以 Poll Count 作为主期限

当前 DMA 等待主要使用 `max_polls`，不便于人工理解真实时间预算，也不能保证子请求继承总 Deadline。

目标 API：

```python
dma.wait_complete(
    channel,
    timeout_s=...,
    poll_interval_s=...,
)
```

`max_polls` 只可作为内部防御上限，不再是主要公共期限语义。

#### PC-REL-006：TargetClient 每次调用的 Timeout 未显式校验

`TargetClient.request(timeout_s=...)` 需要拒绝零或负值，并为所有上层 Driver 提供严格剩余时间语义。

#### PC-REL-007：TargetClient Event Queue 静默丢弃

当前 `deque(maxlen=32)` 在队满时静默丢弃最旧 Event。

目标：

- Event Overflow 必须可观测；
- 不允许无统计静默覆盖；
- 保持固定容量，不引入动态队列或线程。

#### PC-REL-008：Framework Driver Cache 可能过期

新的 HELLO/Session 建立后，应清除旧的 Runtime Service Cache；连接重建后不能继续使用旧 `HelloInfo` 或旧 Service Registry。

### 3.7 已确认的 Firmware 可靠性问题

#### FW-REL-001：UART Reset 清理失败后仍清空关键状态

当前 `uart_reset_to_idle()` 在 IRQ Disable、IRQ Unbind 或 Wrap Deinit 失败时，仍可能：

- 清空 Handle；
- 清空 Applied Mask；
- 清空部分运行状态；
- 让后续重试失去真实硬件上下文。

目标：

- Cleanup 分阶段执行；
- 只有对应硬件动作成功后才提交软件状态；
- 失败后保留足够状态供同一命令重试；
- 返回第一错误，并让 Cleanup Fault 可查询或可诊断。

#### FW-REL-002：IRQ Manager 部分清理可能造成软硬件状态分叉

`deactivate()` 或 `bind()` 回滚中，如果前一个物理 IRQ Line 已成功清理、后一个 Line 失败，Manager Binding 表仍可能保留原状态，但硬件已部分失效。

目标：

- 采用分阶段 Cleanup；
- 每个物理 Line 保存明确 Cleanup Progress；
- 重试从未完成阶段继续；
- 不使用动态事务框架。

#### FW-REL-003：Frame Parser 缓存的下一完整帧缺少无新字节 Drain 路径

Parser 输出一帧后可能在 Buffer 中留下另一完整帧。若此后没有新字节，下一帧可能一直不被输出。

目标：

- 增加显式 Buffered Frame Drain；
- 不依赖新字节触发旧帧输出；
- Native Harness 覆盖“Buffer 中已存在两帧且后续无输入”。

### 3.8 已确认的可读性问题

- Module Docstring 过短，未说明职责边界；
- Protocol Enum 缺少面向人工审核的动作语义注释；
- 大量稳定业务值仍使用裸 `int`；
- Model 中存在 `encode()`；
- Driver 中直接出现 `struct.pack/unpack`；
- Driver 方法缺少统一行为边界、Deadline 和失败语义说明；
- Case 函数名包含 P0/P1/P2 编号但不能直接表达完整 Feature；
- Case 说明缺少统一的“前置条件、观测证据、清理要求”；
- 大型 Helper 隐藏关键步骤；
- 单元测试目录不能快速映射到被测源码。

---

## 4. 最终目标结构

### 4.1 PC Driver

```text
pc/et_test_platform/drivers/
├── dma/
│   ├── __init__.py
│   ├── models.py
│   ├── contract.py
│   ├── codec.py
│   ├── validation.py
│   └── driver.py
├── uart/
├── sysctrl/
├── resource/
├── framework/
└── crg/
```

对于代码很少且经 Review 确认不存在增长风险的 IP，可以使用精简模板，但必须保持：

```text
Public API
Wire Contract/Codec
Validation
```

三个职责不能重新混成不可审核的大文件。

### 4.2 PC Profile 与 Resolver

```text
pc/et_test_platform/profiles/
├── chip_capabilities/              # SVD 自动生成能力，不人工混入执行策略
├── chip_execution_mappings/        # 人工审核的芯片执行映射
│   └── et6801/
│       └── dma_requests.yaml
├── resolvers/
│   ├── __init__.py
│   └── dma_routes.py
└── models.py
```

`dma_requests.yaml` 示例结构：

```yaml
schema: et-chip-execution-mapping/v1
chip: et6801
dma_requests:
  uart0:
    tx:
      peripheral_address: 0x40500000
      request_id: <ET6801 UART0 TX Request Value>
    rx:
      peripheral_address: 0x40500000
      request_id: <ET6801 UART0 RX Request Value>
  uart1:
    tx:
      peripheral_address: 0x40501000
      request_id: <ET6801 UART1 TX Request Value>
    rx:
      peripheral_address: 0x40501000
      request_id: <ET6801 UART1 RX Request Value>
```

正式值必须从当前 SDK/Chip Config 核对，不得根据示例猜测。

Resolver 输出：

```python
@dataclass(frozen=True, slots=True)
class DmaPeripheralRoute:
    provider: str
    provider_instance: int
    endpoint: str
    controller: int
    interface: int
    request_id: int
    peripheral_address: int
```

### 4.3 Test Case

```text
pc/et_test_platform/test_cases/
├── dma/
│   ├── test_memory_to_memory.py
│   ├── test_channel_control.py
│   ├── test_interrupts.py
│   ├── test_linked_list.py
│   ├── test_gather_scatter.py
│   └── test_handshake.py
├── uart/
└── integration/
    ├── test_uart_dma_tx.py
    └── test_uart_dma_rx.py
```

P0/P1/P2/P3 保留为 Marker、Requirement 或报告优先级，不再作为大型源码文件的唯一分类。

### 4.4 Firmware

```text
UART Service    -> UART Wrap
DMA Service     -> DMA Wrap
SYSCTRL Service -> SYSCTRL Wrap
Resource Service -> Resource Wrap
```

最终禁止：

```text
DMA Service -> Resource Wrap
SYSCTRL Service -> Resource Wrap
UART Service -> Resource Wrap
```

例外：Framework IRQ Manager 仍可按既定规则供本 IP Service 绑定静态 Callback；这不是跨 IP 业务调用。

---

## 5. Wire Contract 迁移设计

### 5.1 总规则

- 旧 Command ID 不得静默改义；
- 新语义使用新 Command ID；
- 旧 Command ID 保留为 Deprecated/Reserved；
- PC 公共 API 可以兼容旧调用形式，但内部统一发送新 Wire；
- 所有变更必须有 Python Golden Vector 和 C Contract Test；
- Firmware/PC Build ID 必须同步更新；
- 真实 HIL 必须使用同一对 PC/Firmware 构建。

### 5.2 SYSCTRL DMA Mux Configure V2

当前旧命令：

```text
ET_SYSCTRL_COMMAND_DMA_REQUEST_CONFIGURE = 0x0001
Body = controller + interface + endpoint + instance + address
```

目标新增命令：

```text
ET_SYSCTRL_COMMAND_DMA_MUX_CONFIGURE = 0x0003
Body Size = 8 Bytes
```

建议 Wire：

```text
Offset  Size  Field
0       1     controller
1       1     interface
2       2     reserved = 0
4       4     request_id
```

Firmware 行为：

```text
Decode
-> et_sysctrl_wrap_configure_dma_request(controller, interface, request_id)
-> Encode Status
```

Firmware 不知道：

- UART/SPI/ADC；
- Provider；
- Instance；
- Endpoint；
- Peripheral Address。

旧 `0x0001` 在迁移完成后返回 `NOT_SUPPORTED`，不得复用为新语义。

### 5.3 DMA Configure

当前 64-Byte DMA Configure 已经直接传递：

- Source Address；
- Destination Address；
- Source Interface；
- Destination Interface；
- Transfer Type；
- Width/Burst/Address Mode；
- Transfer Count；
- Gather/Scatter/LLI 参数。

该 Wire Body 原则上保持不变。

变化只在 Firmware 所有权：

- 删除 Resource Range 校验；
- 删除 Peripheral Route 校验；
- 删除 Pool/Route Lease；
- 只保留 Wire 长度、Reserved Bit、地址宽度转换和本地状态数组安全；
- Wrap 负责本 IP 可表示性和硬件结果。

### 5.4 DMA LLI Descriptor Init V2

当前旧命令使用 Resource Handle + Offset，由 DMA Service 调用 Resource Wrap 解析地址。

目标新增命令：

```text
ET_DMA_COMMAND_LLI_DESCRIPTOR_INIT_V2 = 0x001c
Body Size = 76 Bytes
```

建议 Wire：

```text
Offset  Size  Field
0       64    DMA Config
64      8     descriptor_address
72      1     is_last
73      3     reserved = 0
```

PC 负责：

- 从 Resource Object 获取 `descriptor.address`；
- 确认地址来源与容量；
- 直接下发地址。

Firmware 负责：

```text
Decode Address
-> et_dma_wrap_init_lli_descriptor(...)
```

旧 `0x0014` 保留为 Deprecated/Reserved，迁移后返回 `NOT_SUPPORTED`。

### 5.5 UART DMA Endpoint Query

UART `DMA_ENDPOINT_GET` 可以保留为只读诊断命令，但必须删除：

- Endpoint Publish 副作用；
- Resource Registry 依赖；
- 控制流程对该命令的依赖。

PC Resolver 的执行映射是控制参数来源；只读查询只能用于 HIL 一致性检查，不得作为 Route 注册动作。

---

## 6. 分阶段实施原则

每个阶段必须遵守：

```text
先测试锁定
-> 再修改
-> 再运行局部验证
-> 再运行联合回归
-> 再人工 Review
```

提交拆分：

1. 结构迁移提交不修改行为；
2. 行为修复提交不混入全文件格式化；
3. Wire 变更单独提交；
4. Test Case 重写单独提交；
5. 质量门禁单独提交；
6. 每个 IP 完成后立即写 Review，不等待所有 IP 完成。

---

## 7. Phase 0：建立重构基线和问题锁定测试

### 7.1 目标

在移动文件或改变 Wire 前，把当前合法行为和已知错误场景固化为自动测试。

### 7.2 工作内容

新增或补充：

```text
Public Import Test
Command ID Stability Test
Body Size Stability Test
Golden Encode/Decode Test
Driver Command Mapping Test
Error/Cleanup Test
Deadline Test
Firmware Native Failure Injection Test
```

重点测试：

- UART 每个子请求接收剩余 Deadline；
- Exchange 只能使用一个总 Deadline；
- Exchange Primary Error + Cleanup Error 同时可观测；
- UART 9-bit 策略参数拒绝零/负值；
- DMA Wait 使用总 Deadline；
- TargetClient 拒绝零/负 `timeout_s`；
- Event Queue Overflow 有计数或显式状态；
- HELLO 后 Runtime Service Cache 被清除；
- UART Deinit/IRQ Unbind 失败后可重试；
- IRQ Manager 部分失败后状态可重试；
- Parser 在无新字节时输出已缓存下一帧。

### 7.3 验收

- 测试能够在修改前准确暴露对应缺陷；
- 不通过修改断言掩盖问题；
- Golden Vector 与当前合法 Wire 一致；
- 未改变生产代码行为。

---

## 8. Phase 1：先实现 PC 代码质量门禁

### 8.1 目标

在大规模移动 PC 文件前，先建立防止再次退化的自动机制。

### 8.2 文件

```text
pyproject.toml
tools/check_pc_code_rules.py
tools/validate_pc.py
pc/et_test_platform/framework_validation/unit/code_quality/
    test_pc_code_rule_checker.py
    test_pc_architecture_rules.py
```

### 8.3 Ruff 门禁

增加：

- Ruff Formatter Check；
- Ruff Lint；
- Import Sorting；
- 基础 Bugbear/Simplify/Upgrade 规则；
- McCabe Complexity。

原则：

- 初始只要求“新增和修改文件”全绿；
- 历史文件使用明确 Allowlist；
- 不一次性格式化全仓；
- 每完成一个 IP Package，删除该 IP 的 Allowlist；
- 最终 PC 全仓无 Allowlist。

### 8.4 AST 架构检查

至少实现：

```text
ETPC001  模块缺少 Module Docstring
ETPC006  Driver 导入其他 IP Driver
ETPC104  硬件 Case 缺少固定 Docstring 章节
ETPC202  Model 定义 encode/decode/send/request
ETPC205  Driver 直接使用 struct.pack/unpack
ETPC206  Codec 导入 TargetClient
ETPC207  Case 导入 codec/contract/transport
ETPC301  硬件 Case 缺少 hardware Marker
ETPC401  except Exception: pass
ETPC403  Production 代码使用 assert
ETPC410  公共 API 缺少类型标注
ETPC411  新增模糊文件名
```

### 8.5 统一入口

```bash
python tools/validate_pc.py
```

固定执行：

```text
Syntax
-> Ruff Format Check
-> Ruff Lint
-> AST Rules
-> Unit/Contract Tests
```

### 8.6 验收

- Checker 自身有正反单元测试；
- 新违规文件会稳定失败；
- 当前历史违规有明确、最小、可删除的 Allowlist；
- 不引入 pre-commit 作为唯一入口；CI 和本地均可直接运行。

---

## 9. Phase 2：PC Core 可靠性基础

### 9.1 新增明确公共能力

建议新增：

```text
pc/et_test_platform/core/deadline.py
pc/et_test_platform/core/cleanup.py
```

禁止创建模糊 `utils.py`。

### 9.2 Deadline

提供小型、不可变或函数式工具：

```python
OperationDeadline.start(timeout_s)
deadline.remaining_s()
deadline.sleep(poll_interval_s)
```

要求：

- 使用 `time.monotonic()`；
- 每个子请求传递 `remaining_s()`；
- Deadline 耗尽立即抛明确异常；
- 不引入线程和异步框架。

### 9.3 Cleanup Error

提供稳定异常结构：

```text
primary_error
cleanup_errors[]
```

禁止：

```python
except Exception:
    pass
```

### 9.4 TargetClient

整改：

- 校验每次 `timeout_s > 0`；
- Event Queue Overflow 可观测；
- 保留固定容量；
- 增加 `event_overflow_count` 或同等稳定事实；
- Retry 行为保持“调用方显式声明安全”。

### 9.5 Framework Driver

整改：

- `hello()` 开始前清除旧 HELLO/Service Cache；
- HELLO 成功后绑定新 Session；
- 新 Session 必须重新 Discover Services；
- 不允许旧 Runtime Registry 跨 Session 使用。

### 9.6 验收

- TargetClient、Framework 单元测试全绿；
- Retry/Timeout 行为不静默变化；
- Event Overflow 可查询；
- Cache 不跨新 Session 泄漏。

---

## 10. Phase 3：DMA PC Package 行为保持型迁移

### 10.1 目标

先拆文件，不改 Command ID、Wire Body 和公共导入路径。

### 10.2 原子替换

`drivers/dma.py` 与 `drivers/dma/` 不能长期并存形成导入歧义。

在同一结构迁移提交中完成：

```text
删除 drivers/dma.py
新增 drivers/dma/__init__.py
新增 drivers/dma/models.py
新增 drivers/dma/contract.py
新增 drivers/dma/codec.py
新增 drivers/dma/validation.py
新增 drivers/dma/driver.py
```

保持公共导入：

```python
from et_test_platform.drivers.dma import DmaDriver, DmaConfig
```

### 10.3 文件职责

`models.py`：

- `DmaConfig`；
- `DmaCapabilities`；
- `DmaStatus/Result/Snapshot`；
- 稳定业务 Enum。

`contract.py`：

- Service ID；
- Command ID；
- Wire Enum；
- Body Size。

`codec.py`：

- 全部 `struct.Struct`；
- Encode/Decode 纯函数；
- Response 长度；
- Reserved Field；
- Golden Vector。

`validation.py`：

- 本 IP 类型、范围、对齐和参数组合。

`driver.py`：

- TargetClient 调用；
- Retry Safe Set；
- 单 IP Deadline；
- 单 IP Cleanup；
- 稳定异常上下文。

### 10.4 可读性整改

迁移时同时完成但不改变行为：

- Module Docstring；
- Command Enum 语义注释；
- `frozen=True, slots=True`；
- 公共方法 Docstring；
- 固定方法排列顺序；
- 明确单位命名；
- 去除 Driver 中 `struct.pack/unpack`；
- 去除 Model 中 `encode()`。

### 10.5 验收

- Public Import Test 通过；
- 当前 DMA Driver Contract Test 全绿；
- Golden Bytes 不变；
- 没有 Firmware/Wire 修改；
- AST Rules 对 DMA Package 全绿；
- 删除 DMA Allowlist。

---

## 11. Phase 4：PC Execution Mapping 与 DMA Route Resolver

### 11.1 目标

把跨 IP 参数来源完整移到 PC。

### 11.2 新增文件

```text
profiles/chip_execution_mappings/et6801/dma_requests.yaml
profiles/resolvers/__init__.py
profiles/resolvers/dma_routes.py
profiles/models.py
```

### 11.3 数据来源

必须核对：

- UART Peripheral Address：SVD Capability / SDK；
- DMA Request ID：SDK `DMAMUX_REQ_*` 定义；
- Controller 和 Interface：Case Requirement/Bench Policy；
- Runtime Service：Framework Service Registry；
- Feature 支持：Capability + Runtime Capability。

不得：

- 在 Case 中散落地址；
- 从 Firmware Endpoint Registry 动态建立控制参数；
- 把 Board 连线和 Chip DMAMUX Request 混成同一字段；
- 修改 SVD 自动生成 YAML 来保存人工策略。

### 11.4 Resolver API

```python
resolve_dma_peripheral_route(
    *,
    chip_capabilities,
    runtime_services,
    execution_mapping,
    provider,
    provider_instance,
    endpoint,
    controller,
    interface,
) -> DmaPeripheralRoute
```

返回前必须完成全部 PC 端检查。

### 11.5 验收

- ET6801 UART0/1/2 TX/RX Mapping 有单元测试；
- 缺失 Address、Request ID、Interface、Runtime Service 时明确失败；
- Case 不直接读取原始 YAML Dict；
- Resolver 不执行硬件命令；
- Package Data 能包含新 Mapping 文件。

---

## 12. Phase 5：SYSCTRL V2 与 Firmware 信任边界整改

### 12.1 PC SYSCTRL Package

迁移为：

```text
drivers/sysctrl/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

新增公共 API：

```python
configure_dma_request(
    *,
    controller: int,
    interface: int,
    request_id: int,
) -> None
```

### 12.2 Firmware SYSCTRL

修改：

```text
et_sysctrl_service.c
et_sysctrl_service.h
et_sysctrl_wrap.c
et_sysctrl_wrap.h
```

最终：

- Service 不 include Resource Wrap；
- Service 不处理 Provider/Endpoint/Instance/Address；
- Wrap 不包含 UART DMA Mapping Table；
- Wrap 直接接收 Request ID；
- 只调用 SYSCTRL Driver。

### 12.3 验收

- V2 Golden Vector 通过；
- 旧 Command ID 不被复用；
- Firmware SYSCTRL 无 UART/Resource 依赖；
- C Syntax/Native Contract 通过；
- PC Driver 只接收直接执行参数。

---

## 13. Phase 6：DMA Firmware 执行代理化

### 13.1 删除职责

从 DMA Service 删除：

- `et_resource_wrap.h`；
- `memory_range_is_valid()`；
- `peripheral_endpoint_is_valid()`；
- `config_access_is_valid()`；
- `acquire_config_ownership()`；
- `release_channel_ownership()`；
- Pool/Route Ownership State；
- LLI Handle Resolve。

### 13.2 保留职责

保留：

- Wire Body 长度；
- Reserved Bit；
- 64-bit Address 到 `uintptr_t` 的无截断转换；
- Channel 数组和位移安全；
- DMA Controller/Channel 本地生命周期；
- IRQ Callback 所需固定状态；
- Wrap 状态映射；
- 原始事实返回。

### 13.3 LLI V2

- PC 下发 Descriptor Address；
- Firmware 直接调用 DMA Wrap；
- 旧 LLI Command 返回 `NOT_SUPPORTED`；
- Descriptor Address 正确性由 PC Resource/Resolver 保证。

### 13.4 Resource Wrap 收缩

在全仓确认零引用后删除：

- DMA Endpoint 类型和表；
- DMA Route 类型和表；
- Endpoint Publish；
- Route Bind/Unbind/Validate；
- Route Acquire/Release；
- 仅为 DMA 跨服务占用存在的 Pool Lease。

保留 Resource Service 本身的：

- Create；
- Read；
- Write；
- Fill；
- Resolve/Address；
- Reset。

PC Test Case 保证 DMA 完成和反配置前不 Reset Resource。

### 13.5 UART Endpoint Query

删除 UART Service 对 Resource Registry 的 Publish；只读地址查询如保留，必须无副作用。

### 13.6 验收

架构搜索必须为零：

```text
DMA Service -> Resource Wrap
SYSCTRL Service -> Resource Wrap
UART Service -> Resource Wrap
```

同时：

- DMA M2M Contract 回归通过；
- UART DMA TX/RX V2 Contract 通过；
- C Syntax 通过；
- DMA Service State 结构明显收缩；
- 不新增新的跨 IP 公共机制。

---

## 14. Phase 7：DMA Deadline 与异常语义修复

### 14.1 Driver API

新增/规范：

```python
start(channel)
read_status(channel)
wait_complete(channel, *, timeout_s, poll_interval_s)
```

`start_wait()`：

- 可暂时作为 Compatibility Alias；
- 内部调用 `start()` + `wait_complete()`；
- 发出 Deprecation 说明或在文档中标记；
- 不继续以 `max_polls` 作为主要公共语义。

### 14.2 失败语义

- Error Event：保留 DMA Error 作为 Primary Error；
- Timeout：保留 Timeout 作为 Primary Error；
- Stop/Deconfigure 失败：进入 Cleanup Errors；
- 每次 Target Request 使用剩余 Deadline；
- 不吞掉 Cleanup。

### 14.3 验收

- Fake Clock 单元测试；
- 慢子请求不会越过总 Deadline；
- Error + Cleanup Failure 同时可见；
- Public Docstring 明确“是否 Start、是否 Wait、Deadline 所有权”。

---

## 15. Phase 8：UART PC Package 与可靠性整改

### 15.1 Package 迁移

```text
drivers/uart/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

### 15.2 结构整改

- 全部 Struct 移入 Codec；
- `_encode_line_config()` 移入 Codec/Validation 明确边界；
- Compatibility 入口集中；
- Stable Enum 与 Wire Enum 分离；
- 公开方法按 Lifecycle/Configuration/Action/Status/Wait/Cleanup 排列；
- 每个状态改变或等待方法写详细中文 Docstring。

### 15.3 可靠性整改

- `write/read_exact/write_9bit/read_9bit/exchange` 使用同一 Deadline 工具；
- 每个 `_request()` 接收 `remaining_s()`；
- Exchange 只有一个总 Deadline；
- Capture Cancel 失败进入 Cleanup Errors；
- 9-bit 策略参数完整校验；
- Response Bool/Reserved/Length 统一由 Codec 检查。

### 15.4 验收

- Public Import 不变；
- Wire Golden Vector 不变；
- 所有普通与 9-bit Deadline 测试通过；
- Exchange Primary/Cleanup Error 测试通过；
- AST Rules 对 UART Package 全绿；
- 删除 UART Allowlist。

---

## 16. Phase 9：Firmware UART Cleanup 事务化

### 16.1 目标

让 `uart_reset_to_idle()` 在任何阶段失败后都可以安全重试。

### 16.2 分阶段状态

建议明确记录：

```text
interrupts_disabled
irq_unbound
hardware_deinitialized
```

不要求引入通用状态机，仅使用小型固定字段或由现有真实字段表达 Progress。

### 16.3 提交原则

- Disable Interrupt 成功后才清 Applied Mask；
- Unbind 成功后才清 `irq_bound/route`；
- Deinit 成功后才清 Handle/Initialized；
- 前一阶段失败时不伪装后续成功；
- Retry 不重复 Bind 或丢失 Handle；
- Initialization Failure Cleanup 也使用同一入口；
- 返回第一错误，必要时增加 Cleanup Fault 证据。

### 16.4 验收

Native Failure Injection：

- Disable 失败 -> 状态保留 -> 第二次成功；
- Unbind 失败 -> Binding 保留 -> 第二次成功；
- Deinit 失败 -> Handle 保留 -> 第二次成功；
- Init 中途失败 -> Cleanup 可重试；
- 无重复 IRQ Binding。

---

## 17. Phase 10：Test Case 按 Feature 重构

### 17.1 目标

让人工审核人员打开 Case 即可判断测试设计，而不是先阅读大型 Helper。

### 17.2 Case 文件

把 P0/P1/P2/P3 大文件按 Feature 迁移。

建议 DMA：

```text
test_memory_to_memory.py
test_channel_control.py
test_interrupts.py
test_linked_list.py
test_gather_scatter.py
test_handshake.py
test_register_snapshots.py
```

跨 IP：

```text
uart/test_dma_tx.py
uart/test_dma_rx.py
```

### 17.3 Case Docstring

每个硬件/集成 Case 必须包含：

```text
测试 Feature
前置条件
测试步骤
观测证据
通过条件
清理要求
```

复杂 Case 增加：

```text
设计说明
限制与未覆盖项
```

### 17.4 Case 代码结构

从上到下直接显示：

```text
Arrange
-> Resolve
-> Configure
-> Arm/Start
-> Observe
-> Assert
-> Cleanup
```

### 17.5 Helper 收缩

大型 `execute_xxx()` Helper 原则上拆回 Case。

允许保留的 Helper：

- 纯数据生成；
- 小型状态等待；
- Evidence 格式转换；
- 不隐藏关键顺序的重复 Cleanup；
- 至少稳定重复三次。

禁止 Helper：

- 完成完整 Test Case；
- 内部执行最终断言；
- 同时调用多个 IP 且 Case 看不到顺序；
- 自己写第二套 PASS/FAIL。

### 17.6 Evidence 与结果

- pytest Assertion 是最终判断；
- RunContext/Evidence 是统一证据链；
- JSON 只记录 Measurement/附件；
- JSON 不再拥有独立 `status=PASS` 结论；
- Case Cleanup Error 不得被结果写入覆盖。

### 17.7 验收

每个 Case 人工 Review 必须回答：

- 目标 Feature 是什么；
- 为什么输入覆盖目标；
- 为什么观测足以证明结果；
- 是否存在未覆盖限制；
- Cleanup 是否完整；
- 是否存在隐藏顺序。

---

## 18. Phase 11：公共 Firmware 可靠性闭环

### 18.1 IRQ Manager

实现轻量的阶段式 Cleanup：

- 对每个物理 Line 跟踪已完成步骤；
- Disable/Clear/Unregister 任一步失败保留可重试进度；
- Software Binding 与硬件进度一致；
- `deactivate()` 直到全部 Line 完成才清 Active Manager；
- `bind()` 回滚失败必须可观测。

### 18.2 Frame Parser

增加不依赖新输入的 Drain API，例如：

```text
et_frame_parser_take_buffered()
```

或等价的小型接口。

Protocol Poll 在一帧完成后继续 Drain 已缓存完整帧，直到：

- 无完整帧；
- 已生成 Pending Response；
- 本轮有界处理上限耗尽。

### 18.3 验收

Native Harness 必须覆盖：

- 两个完整帧已在 Parser Buffer；
- 输出第一帧后无任何新字节；
- 仍能输出第二帧；
- IRQ 多 Line Cleanup 中第二 Line 失败；
- 第一 Line 状态与重试结果一致；
- 最终 Deactivate 可完成。

---

## 19. Phase 12：其余 PC Package 迁移

顺序：

```text
SYSCTRL（Phase 5 已完成）
-> Resource
-> Framework
-> CRG
-> 其他新增 IP
```

规则：

- 一个 IP 一个提交系列；
- Public Import 保持稳定；
- 先 Golden Test，再移动；
- 新文件立即受 Ruff/AST 全规则约束；
- 每个 Package 完成后删除对应 Allowlist。

Framework 迁移必须同时关闭 Cache 问题；Resource 迁移必须明确“Buffer 管理”而不是“跨 IP 资源图”。

---

## 20. 验证矩阵

### 20.1 每个提交最小验证

```text
Python Syntax
Ruff Format Check（修改文件）
Ruff Lint（修改文件）
AST Rules（修改范围）
相关 Unit/Contract
Diff Review
```

### 20.2 每个 IP 完成验证

```text
Public Import
Codec Golden Vector
Validation
Driver Command
Deadline/Retry/Cleanup
Resolver
Case Collection
PC Full Unit
相关 Firmware C Syntax
相关 Native Harness
```

### 20.3 公共层完成验证

```text
全部 PC Unit/Contract
全部 Native C Harness
Framework/UART/DMA 联合回归
Architecture Invariant
临时文件检查
```

### 20.4 Keil

至少：

```text
ET6801 FPGA Target
ET6801 Silicon Target
```

必须记录：

- 实际命令；
- 编译器版本；
- Build Target；
- 结果；
- Warning；
- 输出路径。

### 20.5 HIL 顺序

```text
1. Framework HELLO/ECHO/Service List
2. Resource Create/Read/Write/Fill
3. DMA Memory-to-Memory
4. DMA IRQ
5. UART Polling
6. UART IRQ/Capture
7. SYSCTRL DMA Mux V2
8. UART TX DMA
9. UART RX DMA
10. Cleanup/重复执行/故障恢复
```

HIL 必须特别检查：

- PC Mapping 与真实 UART Address/Request ID 一致；
- Route Release 后下一 Case 不受污染；
- DMA 不再依赖 Firmware Endpoint Registry；
- UART Cleanup 失败后重试；
- 多次重复运行没有状态泄漏。

---

## 21. Issue 到 Phase 映射

| 问题 | 关闭阶段 |
|---|---|
| PC Driver 单文件杂糅 | Phase 3、5、8、12 |
| Case P0/P1/P2 大文件 | Phase 10 |
| Unit Test 平铺 | Phase 1、3、8、12 |
| Firmware Endpoint/Route/Lease | Phase 5、6 |
| PC 缺少 DMA Route Mapping | Phase 4 |
| UART 子请求不继承 Deadline | Phase 2、8 |
| UART Exchange 双 Timeout | Phase 8 |
| UART Cleanup Error 被吞 | Phase 2、8 |
| UART 9-bit 参数检查 | Phase 8 |
| DMA Poll Count 主期限 | Phase 7 |
| TargetClient Timeout 校验 | Phase 2 |
| Event Queue 静默覆盖 | Phase 2 |
| Framework Cache 过期 | Phase 2、12 |
| Firmware UART Reset 不可重试 | Phase 9 |
| IRQ Manager 部分 Cleanup | Phase 11 |
| Parser 无新字节 Drain | Phase 11 |
| 缺少代码质量自动门禁 | Phase 1 |
| Case 注释/人工审核不统一 | Phase 10 |

---

## 22. 实施顺序与阻断点

固定顺序：

```text
Phase 0  Baseline Tests
Phase 1  Quality Gate
Phase 2  Core Reliability
Phase 3  DMA PC Package
Phase 4  PC Mapping/Resolver
Phase 5  SYSCTRL V2
Phase 6  DMA Firmware Simplification
Phase 7  DMA Deadline
Phase 8  UART PC Package/Reliability
Phase 9  UART Firmware Cleanup
Phase 10 Case Refactor
Phase 11 Common Firmware Reliability
Phase 12 Remaining PC Packages
Keil
HIL
Final Review
```

阻断规则：

- Phase 0 测试未锁定，不进入结构迁移；
- Phase 1 门禁未能阻止新违规，不进入大规模 PC 拆分；
- SYSCTRL V2 Contract 未通过，不删除旧 Route Registry；
- PC Resolver 未提供真实 Request ID，不修改 Firmware 控制路径；
- DMA M2M 未通过，不执行 UART DMA HIL；
- UART Cleanup Native Test 未通过，不执行重复 HIL；
- Keil 未通过，不写 HIL PASS；
- HIL 未执行，不允许评价整体重构完成。

---

## 23. 每阶段 Review 输出

每个重要阶段在 `report/review/` 生成独立 Review：

```text
20260806_pc_quality_gate_review.md
20260806_dma_pc_package_refactor_review.md
20260806_pc_dma_route_resolver_review.md
20260806_sysctrl_dma_mux_v2_review.md
20260806_dma_firmware_execution_boundary_review.md
20260806_uart_pc_package_refactor_review.md
20260806_uart_cleanup_reliability_review.md
20260806_test_case_readability_review.md
20260806_common_reliability_final_review.md
```

实际日期按完成日期更新，不提前创建空 PASS 报告。

---

## 24. 最终验收标准

只有以下条件全部满足，才能宣布本轮重构完成：

### 架构

- [ ] PC 是跨 IP 参数和流程唯一控制面；
- [ ] Firmware Service 只调用本 IP Wrap；
- [ ] DMA/SYSCTRL/UART Service 不再使用 Resource Registry 建立跨 IP 关系；
- [ ] DMA Service 直接执行 PC 下发的 Address/Interface；
- [ ] SYSCTRL Service 直接执行 PC 下发的 Request ID；
- [ ] LLI Descriptor Address 由 PC 直接下发；
- [ ] Driver 不调用其他 IP Driver；
- [ ] Case 不绕过 Driver/Resolver。

### PC 可读性

- [ ] DMA、UART、SYSCTRL、Framework、Resource 按 Package 规范拆分；
- [ ] Driver 中无 `struct.pack/unpack`；
- [ ] Model 中无 `encode/decode`；
- [ ] 硬件 Case 均有固定中文 Docstring；
- [ ] 跨 IP 顺序在 Case 中显式可见；
- [ ] 不存在隐藏完整测试流程的大型 Helper；
- [ ] Test 文件按 Feature 命名；
- [ ] Unit Test 镜像源码结构。

### 可靠性

- [ ] UART/DMA 使用严格总 Deadline；
- [ ] Primary/Cleanup Error 同时可见；
- [ ] TargetClient Event Overflow 可观测；
- [ ] Framework Cache 不跨 Session；
- [ ] UART Reset 失败可重试；
- [ ] IRQ Manager 部分清理可重试；
- [ ] Parser 可无新字节 Drain 缓存帧。

### 质量门禁

- [ ] Ruff Format 全仓通过；
- [ ] Ruff Lint 全仓通过；
- [ ] AST Rules 全仓通过；
- [ ] 无历史 Allowlist；
- [ ] Unit/Contract/Native 全绿；
- [ ] 架构依赖搜索全绿。

### 构建与硬件

- [ ] ET6801 FPGA Keil Build 通过；
- [ ] ET6801 Silicon Keil Build 通过；
- [ ] Framework HIL 通过；
- [ ] DMA M2M/IRQ HIL 通过；
- [ ] UART Polling/IRQ HIL 通过；
- [ ] UART DMA TX/RX HIL 通过；
- [ ] 重复运行和 Cleanup HIL 通过。

---

## 25. 第一批实际工作范围

计划批准后，第一批只实施：

```text
Phase 0：Baseline Tests
Phase 1：PC Quality Gate
Phase 2：PC Core Reliability
```

第一批不修改：

- Firmware Wire Contract；
- DMA/SYSCTRL/UART Service Command；
- HIL Case 业务语义。

第一批完成并 Review 通过后，再开始 DMA Package 和 SYSCTRL V2。

这样可以确保后续每次结构迁移和行为变更都处于可回归、可审核的质量门禁之下，避免再次出现一次性大规模重构风险。
