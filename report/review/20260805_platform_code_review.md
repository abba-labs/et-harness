# ET 自动化测试平台代码评审记录

文档状态：持续更新中的代码评审基线  
首次建立：2026-08-05 15:33 CST  
评审基线：`main@b947b9c1ab6bd1db7cd9dccc8b164d21146dcdbc`  
评审方式：架构文档、PC 端 Python、DUT 固件 C 代码、Profile、测试 Case 与验证报告交叉阅读  
当前限制：本轮结论以静态代码分析为主，尚未在评审环境中重新执行 Keil 编译、pytest 全量回归或真实 HIL

> 本文是持续维护的 Review 文档。后续每完成一个模块的贯通分析，就在同一文档中补充问题、证据、影响、整改建议和验收条件。已经确认的问题不会因为后续代码变化而直接删除；修复后应改为“已修复待验证”或“已关闭”，并记录对应提交和验证证据。

---

## 1. 评审目标

本次评审不是只检查单个函数是否能运行，而是检查整条自动化测试链路是否真正闭环：

```text
pytest Test Case
  -> PC IP Driver
  -> TargetClient
  -> ET-Frame
  -> 固件 Framework
  -> IP Service
  -> Common Wrap
  -> ET6801 SDK Driver
  -> DUT 硬件
  -> 结果、证据和报告
```

重点检查以下问题：

1. 架构文档声明的分层和依赖方向，是否被实际代码遵守。
2. PC、固件、Profile、Bench 和 Runtime Service Registry 之间是否一致。
3. 硅前 FPGA、硅后芯片和后续新芯片是否能够真正复用同一套测试语义。
4. 协议超时、重试、重复请求、Session、CRC 和错误恢复是否闭环。
5. 测试 PASS/FAIL、外部证据、专项测量文件和最终报告是否能够一一追溯。
6. 验证报告是否能准确关联到被验证的代码、固件、Profile、Bench 和硬件版本。

---

## 2. 当前已审阅范围

| 领域 | 已重点阅读的文件/目录 | 当前关注点 |
|---|---|---|
| 总体架构 | `report/design/et_ip_automated_test_platform_architecture.md` | 平台角色、统一 IP 主线、PC/DUT/XC7Z045 职责 |
| PC 分层 | `report/design/pc_layered_architecture.md`、`pc/README.md` | Test Case、Driver、Client、Transport、fixture 和结果层边界 |
| 固件分层 | `report/design/firmware_layering.md`、`firmware/README.md` | Application、Framework、Service、Wrap、Chip SDK 依赖方向 |
| 固件入口 | `firmware/application/src/main.c` | 启动顺序、控制 UART、Runtime 和 Service 注册 |
| 固件协议 | `firmware/framework/src/et_protocol.c`、`et_service_router.c` | Session、重复请求、响应重放、服务分发 |
| PC 协议 | `pc/et_test_platform/communication/protocols/et_frame.py` | 帧格式、CRC、流式重同步 |
| PC Client | `pc/et_test_platform/clients/target.py` | 请求响应、超时、重试、事件队列 |
| Framework Driver | `pc/et_test_platform/drivers/framework.py` | HELLO、Session、Service Registry 哈希 |
| DMA 链路 | `drivers/dma.py`、`et_dma_service.[ch]`、DMA P0 Case | C/Python 协议契约、IRQ 观测、公共 Case 复用边界 |
| Capability | `report/design/capability_v2_contract.md`、`profiles/capabilities.py` | SVD 事实、语义能力、Evidence、Audit 和运行时交集 |
| pytest 调度 | `pytest_plugin.py`、`scheduling/fixtures.py`、`run_context.py` | 硬件门禁、fixture、CaseResult、Evidence 和退出状态 |
| Bench | `profiles/bench_topologies/et6801_uart_template.yaml` | 控制 UART、DUT UART、Peer UART 和 DMA 外设链路角色 |
| 验证报告 | `report/validation/dut/20260805_uart_split_cases_hil.md` 等 | 代码版本、固件版本、证据可追溯性 |

尚未完成的重点范围见本文末尾“后续评审计划”。

---

## 3. 问题等级与状态定义

### 3.1 严重等级

| 等级 | 定义 |
|---|---|
| P0 | 阻断平台基本运行、可能破坏硬件或造成结果完全不可信 |
| P1 | 高优先级问题，会导致 Case 错误 SKIP、错误 PASS、跨芯片复用失败或证据链断裂 |
| P2 | 中优先级问题，当前可能运行，但可靠性、维护性或长期扩展风险明显 |
| P3 | 低优先级问题，主要影响文档、可读性、开发效率或一致性 |

### 3.2 结论状态

| 状态 | 含义 |
|---|---|
| 已确认 | 从当前代码可以形成完整、确定的静态因果链 |
| 高风险 | 已有明确风险，但仍需运行时复现或更多模块交叉确认 |
| 待验证 | 已提出疑点，尚不能写成确定缺陷 |
| 已修复待验证 | 代码已修改，尚缺单元测试、集成测试或 HIL 证据 |
| 已关闭 | 修复和验证均完成，并记录提交和证据 |

---

## 4. 当前问题摘要

| ID | 等级 | 状态 | 问题摘要 |
|---|---|---|---|
| REV-001 | P1 | 已确认 | 控制 UART 被固件排除出测试 Service，但 PC fixture 又强制要求它存在于 Runtime Service Registry |
| REV-002 | P1 | 已确认 | 通用 CaseResult 与各 IP Case 自写的专项 JSON 没有统一关联，形成两套结果源 |
| REV-003 | P1 | 已确认 | `EVIDENCE_MISSING` 只写入结果 JSON，不会改变 pytest PASS 和进程退出码 |
| REV-004 | P1 | 已确认 | 公共 DMA Case 硬编码 ET6801 的控制器数量、通道数量和最大块大小，破坏跨芯片复用边界 |
| REV-005 | P2 | 已确认 | TargetClient 已支持安全重试，但 DMA 等 IP Driver 没有为只读命令声明 `retry_safe` |
| REV-006 | P2 | 高风险 | C 与 Python 分别手工维护 Service ID、Command ID、body 布局和长度，长期存在契约漂移风险 |
| REV-007 | P2 | 已确认 | Run/Case 结果和 HIL 报告缺少完整 Git/固件镜像/Profile 不可变版本基线，难以复现历史结论 |
| REV-008 | P3 | 已确认 | `pc/README.md` 仍引用已不存在的 `docs/design/...` 路径 |

---

# 5. 详细问题

## REV-001：控制 UART 的 Runtime Service 检查与固件注册策略互相矛盾

**等级：P1**  
**状态：已确认**  
**影响范围：UART Case、依赖 UART Pair 的 DMA 外设 Case、Capability/Runtime 交集、SKIP 原因可信度**

### 5.1.1 设计意图

当前架构将控制 UART 作为 PC 与 DUT 的基础通信通道。它承载 ET-Frame，不应再被普通 UART 测试命令重新配置，否则可能破坏平台控制链路。

`firmware/application/src/main.c` 将控制 UART 的逻辑实例写入：

```c
services_config.reserved_uart_instance =
    (uint16_t)ET_CONTROL_UART_ID;
```

`firmware/services/src/et_services.c` 在注册 UART 测试 Service 时明确跳过该实例：

```c
if (instance == config->reserved_uart_instance) {
    continue;
}
```

这个固件行为本身合理：控制 UART 被保留，不应暴露为普通测试 UART Service。

### 5.1.2 当前 PC 行为

Bench `pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml` 定义：

```yaml
control_instance: 0
dut_instance: 1
peer_instance: 2
```

但是 `pc/et_test_platform/scheduling/fixtures.py` 的 `uart_pair_config` fixture 在构造 UART 角色之前，调用：

```python
_require_uart_runtime_instance(
    framework_communication,
    target_capabilities,
    pair.control_instance,
    "Control",
)
```

而 `_require_uart_runtime_instance()` 首先要求该实例出现在 Firmware `SERVICE_LIST` 中。

### 5.1.3 确定性因果链

```text
控制 UART0 被 main.c 标记为 reserved
  -> et_services.c 不注册 UART0 Service
  -> Framework SERVICE_LIST 不包含 UART Service instance 0
  -> uart_pair_config fixture 强制检查 UART0 Service
  -> fixture 执行 pytest.skip(skip_by_service)
  -> UART Case 无法进入真正测试步骤
  -> 依赖 uart_pair_config / uart_dut_handle / uart_peer_handle 的 DMA 外设 Case 同样被连带 SKIP
```

这个 SKIP 并不表示芯片不支持 UART0，也不表示 Bench 未连接，而是 PC 端把“控制通道存在”错误等价成了“控制实例必须注册为测试 Service”。

### 5.1.4 风险与影响

1. UART 测试可能在资源构造阶段被错误 SKIP。
2. DMA Memory-to-Peripheral、Peripheral-to-Memory 等依赖 UART Pair 的 Case 可能被连带 SKIP。
3. SKIP 原因会显示为 `skip_by_service`，掩盖真正的 fixture 逻辑错误。
4. 后续新芯片只要采用“保留控制 UART、不注册测试 Service”的正确固件策略，都会重复遇到同一问题。
5. 历史 HIL 报告是时间点证据，不能自动证明当前 `main` 上的 fixture 与 Runtime Registry 仍然一致。

### 5.1.5 建议整改

将“控制通道验证”和“可测试 UART Service 验证”拆开：

```text
Control UART：
- 验证 Bench 中已定义控制实例；
- 验证其与 DUT/Peer 实例不冲突；
- 可选：验证它没有被暴露为普通 UART Service。

DUT UART / Peer UART：
- 必须存在于生成 Capability；
- 必须存在于 Runtime Service Registry；
- 必须与 Bench 物理角色一致。
```

建议新增明确函数，例如：

```python
_validate_control_uart_role(...)
_require_test_uart_runtime_instance(...)
```

不要继续复用同一个 `_require_uart_runtime_instance()` 表达两种完全不同的语义。

### 5.1.6 验收条件

1. `SERVICE_LIST` 不包含控制 UART 测试 Service 时，`uart_pair_config` 仍可正常创建。
2. 控制 UART 与 DUT/Peer 配置为相同实例时，fixture 明确报 Bench 配置错误。
3. DUT/Peer UART 缺少 Runtime Service 时，相关 Case 仍正确 SKIP。
4. 增加单元测试覆盖：`UART0 reserved，UART1/2 registered`。
5. 在真实 Bench 上重新执行 UART smoke 和至少一个依赖 UART Pair 的 DMA Case。

---

## REV-002：通用 CaseResult 与 IP 专项结果文件形成两套结果源

**等级：P1**  
**状态：已确认**  
**影响范围：结果追溯、Web 展示、自动报告、参数化 Case、失败现场定位**

### 5.2.1 当前通用结果管线

`pc/et_test_platform/pytest_plugin.py` 为每个 pytest item 分配 `case_run_id`，并在 teardown 后调用 `RunContext.write_case_result()`，输出：

```text
<artifact_dir>/cases/<case_run_id>/result.json
```

该公共结果包含：

- `run_id`
- `case_run_id`
- `case_id`
- `status`
- chip/build/registry/bench/transport 等公共元数据
- evidence 完整性
- error

### 5.2.2 当前 IP Case 行为

已审阅的 DMA P0 Case 直接调用：

```python
write_json_result(
    et_artifact_dir / "dma_p0_001_controller_capabilities.json",
    {...},
)
```

其他 Case 也采用类似方式将测量值、地址、IRQ 计数和子用例写到 `artifact_dir` 根目录或自定义文件名。

这些专项 JSON：

- 不知道自己的 `case_run_id`；
- 没有自动登记到公共 `result.json` 的 `artifacts` 字段；
- 公共插件也不知道 Case 写出了哪些专项文件；
- 文件命名、目录层级和内容 Schema 由每个 IP Case 自行决定。

### 5.2.3 当前实际结构

```text
公共结果：
artifacts/cases/<uuid>/result.json
  - 知道 pytest Case 和公共状态
  - 不知道 DMA/UART 专项 JSON 在哪里

专项结果：
artifacts/dma_p0_001_controller_capabilities.json
  - 知道硬件测量和子用例
  - 不知道属于哪个 case_run_id
```

因此两个文件都不完整，后续消费者必须通过文件名猜测关联关系。

### 5.2.4 风险与影响

1. Web 页面或报告生成器无法可靠地从一个 CaseResult 找到对应测量和附件。
2. 参数化、重复运行或并行运行时，自定义固定文件名可能覆盖旧结果。
3. Case 修改名称后，历史工具可能无法再匹配专项文件。
4. 公共结果显示 PASS，但专项 JSON 写入失败时，两边状态可能不一致。
5. 专项 JSON 显示 PASS，但公共结果可能是 `EVIDENCE_MISSING` 或 teardown FAIL。
6. 后续仪器波形、FPGA 捕获、截图和协议 trace 会进一步放大目录混乱。

### 5.2.5 建议整改

提供统一的 `case_recorder` 或 `case_result` fixture，将当前 item 的 `run_id` 和 `case_run_id` 交给 Case：

```python
case_recorder.add_evidence("dut")
case_recorder.add_measurement("irq_count", result.irq_count)
case_recorder.write_json("dma_snapshot.json", snapshot)
case_recorder.add_artifact("dma_snapshot", "dma_snapshot.json")
```

统一落盘结构建议：

```text
artifacts/
├── session.json
└── cases/
    └── <case_run_id>/
        ├── result.json
        ├── measurements.json
        ├── protocol.json
        ├── dma_snapshot.json
        └── artifacts/
```

`result.json` 应保存所有附件的相对路径、SHA256、类型和 Evidence Source。

### 5.2.6 验收条件

1. 每个专项结果都位于对应的 `cases/<case_run_id>/` 下。
2. `result.json.artifacts` 能枚举该 Case 生成的全部文件。
3. 参数化和重复运行不会覆盖历史 Case 文件。
4. 文件写入失败会反映到当前 Case 的最终状态。
5. Web/报告工具只需读取 `session.json + cases/*/result.json`，无需猜测文件名。

---

## REV-003：`EVIDENCE_MISSING` 不会使 pytest 失败

**等级：P1**  
**状态：已确认**  
**影响范围：CI 门禁、硬件测试可信度、自动报告、PASS 定义**

### 5.3.1 当前逻辑

`pc/et_test_platform/scheduling/run_context.py` 会根据 fixture 推导必需 Evidence Source：

- 使用 `framework_communication`：要求 `dut`
- 使用 `uart_peer_handle`：要求 `peer`

当 Case 的 pytest 断言全部通过，但没有登记必需 Evidence 时：

```python
if status == "PASS":
    status = "EVIDENCE_MISSING"
    error = missing_message
```

该逻辑只修改写入 JSON 的业务状态。

`pytest_plugin.py` 在 `pytest_runtest_makereport` 的 teardown 阶段写入结果，但没有：

- 修改 pytest report 为 failed；
- 抛出异常；
- 增加 session 失败计数；
- 修改最终 `exitstatus`。

### 5.3.2 结果不一致

可能出现：

```text
pytest 控制台：PASSED
进程退出码：0
cases/<id>/result.json：EVIDENCE_MISSING
```

这意味着 CI、批处理脚本或上层自动化只检查 pytest 退出码时，会把“证据不完整”当成成功。

### 5.3.3 风险与影响

1. 平台无法强制执行自己定义的硬件证据要求。
2. CI 可能全绿，但最终结果库存在大量 `EVIDENCE_MISSING`。
3. 团队会出现两个 PASS 定义：pytest PASS 和业务结果 PASS。
4. 上层 Web 页面若只看业务结果，会与命令行结果冲突。
5. 领导或验证人员看到的“通过数量”取决于读取哪一套状态。

### 5.3.4 建议整改

必须明确选择一种策略，不能保持当前双重语义：

**推荐策略：证据不完整属于测试失败。**

可在 pytest session 中记录 `EVIDENCE_MISSING` 数量，并在 `pytest_sessionfinish` 中将退出状态改为失败；或者在 Case teardown finalizer 中触发明确的 pytest failure。

如果团队希望“功能通过但证据不足”作为独立非失败状态，也必须：

- 使用非零专用退出码；
- CI 显式识别；
- 汇总报告不得计入 PASS；
- 控制台必须输出明确 warning 和总数。

### 5.3.5 验收条件

1. 构造一个缺少 `dut` Evidence 的伪硬件 Case。
2. pytest 控制台不得显示普通 PASS。
3. 进程退出码不得为 0。
4. `session.json.status_counts` 与 pytest 最终退出状态一致。
5. Evidence 完整的 Case 仍正常 PASS。

---

## REV-004：公共 DMA Case 硬编码 ET6801 产品参数

**等级：P1**  
**状态：已确认**  
**影响范围：跨芯片复用、Capability 价值、新芯片接入、Case 语义稳定性**

### 5.4.1 架构约束

总体设计明确要求测试资产按 `IP -> feature -> contract` 维护，不按芯片复制；芯片实例数量、限制和实现参数应由 Capability/Profile 表达。

### 5.4.2 当前 DMA P0 Case 中的硬编码

已审阅的 `pc/et_test_platform/test_cases/dma/dma_test_case_p0.py` 存在以下模式：

```python
assert instances == ("dma0", "dma1")
assert dynamic.channel_count == 8
assert dynamic.max_transfer_count == 4095

for instance_id in range(2):
    for channel in range(8):
        ...
```

其他 DMA 测试还使用固定 `0xFF` 通道掩码边界和固定最大传输边界。

### 5.4.3 为什么这是架构问题

这些值是 ET6801 当前产品实现事实，不是 DMA 通用 Feature 语义：

- 新芯片可能只有一个 DMA 控制器；
- 某个 DMA 实现可能只有 4 个通道；
- 最大传输数量可能不是 4095；
- 某些控制器只支持部分地址模式或突发长度；
- Runtime Service 可能只暴露芯片实际启用的部分实例。

当前公共 Case 会把这些合法差异当成测试失败。

### 5.4.4 风险与影响

1. 新芯片接入时必须修改公共 Case，违背“芯片增量接入”目标。
2. Capability 已经提供实例、limit、parameter，但 Case 没有真正消费它们生成矩阵。
3. 为兼容新芯片，开发者可能开始复制 `dma_test_case_p0_etxxxx.py`，最终重新形成多套测试主线。
4. “IP 通用功能失败”和“ET6801 产品规格不一致”两类问题混在同一断言中。

### 5.4.5 建议整改

拆分两类测试：

#### A. 公共 DMA 语义 Case

根据 Capability 和 Runtime Registry 动态生成：

```python
instances = capabilities.instances("dma")
for instance in instances:
    dynamic = dma.capabilities_get()
    channel_count = dynamic.channel_count
    expected_max = capabilities.parameter(...)
```

只验证稳定语义：

- 实例可用；
- 动态能力与 Profile Evidence 一致；
- 所有实际通道可完成生命周期；
- 所有 Profile 声明支持的 Option/Feature 可测试。

#### B. ET6801 产品基线一致性测试

单独验证：

```text
ET6801 必须有 dma0/dma1
每个控制器必须有 8 通道
max_transfer_count 必须为 4095
```

这类检查应属于芯片 Profile/产品基线验证，不应污染公共 DMA Feature Case。

### 5.4.6 验收条件

1. 使用合成 Capability：1 个 DMA、4 个通道、最大 1023，公共 Case 不需改代码即可收集并运行。
2. ET6801 的 2×8、4095 仍通过独立产品基线检查。
3. 公共 Case 中不出现 `range(2)`、`range(8)`、固定实例 tuple 等产品常量。
4. 测试矩阵只遍历 Capability/Runtime 共同支持的值。

---

## REV-005：只读 IP 命令没有使用 TargetClient 的安全重试能力

**等级：P2**  
**状态：已确认**  
**影响范围：串口瞬时丢包、长时间回归稳定性、误报 FAIL**

### 5.5.1 当前可靠性基础

`TargetClient.request()` 已实现：

- 默认只发送一次；
- 调用者声明 `retry_safe=True` 时最多尝试两次；
- 重试复用完全相同的编码帧、sequence 和 session；
- 固件缓存上一请求的响应，对完全相同的重复请求执行响应重放，而不是再次执行命令。

Framework Driver 已正确为 `HELLO`、`ECHO`、`VERSION_GET`、`SERVICE_LIST`、`STATISTICS_GET` 等只读或幂等命令设置 `retry_safe=True`。

### 5.5.2 当前 DMA Driver 行为

`DmaDriver` 的所有命令最终进入同一个 `_request()`：

```python
def _request(self, command: int, body: bytes = b""):
    return self._target.request(
        DMA_SERVICE_ID,
        command,
        instance_id=self.instance_id,
        body=body,
    )
```

没有区分：

- 只读查询；
- 幂等清理；
- 会改变硬件状态且超时后状态不确定的命令。

因此以下典型只读命令在一次响应丢失后会直接失败：

- `CAPABILITIES_GET`
- `CHANNEL_STATUS_GET`
- `IRQ_RESULT_GET`
- `COMPONENT_SNAPSHOT_GET`
- `INTERRUPT_SNAPSHOT_GET`
- `CHANNEL_SNAPSHOT_GET`

### 5.5.3 风险与影响

1. 串口瞬时抖动会被误报为硬件 Feature 失败。
2. 长时间、多 Case 回归中偶发超时率会显著累积。
3. Framework 查询可靠，而 IP 查询不可靠，平台行为不一致。
4. 开发者可能在 Case 层自行写重试循环，破坏统一请求策略。

### 5.5.4 建议整改

为每个 Service 定义命令属性，而不是在 Case 层决定：

```python
COMMAND_TRAITS = {
    DmaCommand.CAPABILITIES_GET: CommandTraits(retry_safe=True),
    DmaCommand.CHANNEL_STATUS_GET: CommandTraits(retry_safe=True),
    DmaCommand.CHANNEL_CONFIGURE: CommandTraits(retry_safe=False),
    DmaCommand.CHANNEL_START: CommandTraits(retry_safe=False),
}
```

只读查询可以安全重试；修改硬件状态的命令继续保持默认单次发送，除非其协议语义经过专门设计和验证。

### 5.5.5 验收条件

1. 单元测试模拟第一次响应丢失、第二次响应成功。
2. 只读 DMA 命令成功返回，`retry_count` 增加一次。
3. `CHANNEL_START` 等状态变更命令仍只发送一次。
4. 固件 duplicate request 统计与 PC retry 计数一致。

---

## REV-006：C/Python Service 契约由人工双份维护

**等级：P2**  
**状态：高风险**  
**影响范围：协议兼容、命令扩展、跨语言维护、隐藏数据错位**

### 5.6.1 当前双份定义

DMA 命令在 C 端定义于：

```text
firmware/services/include/et_dma_service.h
```

Python 端再次定义于：

```text
pc/et_test_platform/drivers/dma.py
```

同时，DMA 64 字节配置体：

- Python 使用 `struct.Struct("<16BQQIIQIIII")` 编码；
- C 使用固定字节偏移和 `read_u32/read_u64` 手工解码；
- 请求/响应长度由两端分别写常量判断。

UART、Framework 和后续其他 IP Service 也会出现相同模式。

### 5.6.2 已有保护与不足

仓库已有协议 golden vector、C harness 和单元测试，这能降低风险，但不能消除以下问题：

- 新增 Command 时只修改一端；
- 字段插入后两端 offset 不一致；
- C 端 body size 与 Python `Struct.size` 不一致；
- 枚举数值漂移但测试向量没有覆盖新命令；
- 某个响应字段宽度变化后仍能解码，但含义错误。

### 5.6.3 风险与影响

1. 协议错误可能只在特定参数组合或真实硬件上出现。
2. Review 必须人工对照两种语言，容易漏项。
3. IP 数量增加后，维护成本近似按命令数线性增长。
4. 发生错位时，错误表现可能是硬件异常而不是明确的协议错误。

### 5.6.4 建议整改

推荐逐步引入轻量、机器可读的 Service Contract，例如：

```yaml
service: dma
service_id: 0x0100
commands:
  capabilities_get:
    id: 0x0001
    request: []
    response:
      - {name: features, type: u32}
      - {name: channel_count, type: u16}
```

至少生成：

- C Command ID；
- Python Command ID；
- request/response body size；
- Python `struct.Struct`；
- C 端静态长度断言；
- 双端 golden vector。

在完整生成器落地前，也应增加自动契约测试，枚举全部 Command，并逐项核对 ID 和 body size。

### 5.6.5 验收条件

1. 任意一端修改 Command ID 后，单元测试立即失败。
2. 任意一端修改 body 长度或字段偏移后，双端向量测试立即失败。
3. 新增 Service Command 必须先进入统一契约或契约清单。
4. 不允许通过手工复制枚举完成新命令接入而没有测试门禁。

---

## REV-007：验证结果缺少完整不可变代码与固件基线

**等级：P2**  
**状态：已确认**  
**影响范围：历史复现、回归比较、问题归因、审计可信度**

### 5.7.1 当前 RunContext 元数据

`RunContext` 当前记录：

- `chip_id`
- `firmware_build_id`
- `registry_hash`
- `target_id`
- Bench 路径与 SHA256
- transport identity
- 预留的 bitstream/device identity

但没有稳定记录：

- Git commit SHA；
- 工作树是否 dirty；
- PC Python 包源码版本；
- 固件 ELF/BIN/HEX SHA256；
- Capability Profile 文件集合哈希；
- Keil 工程生成清单版本；
- FPGA bitstream SHA256（当前字段多数为 `None`）。

### 5.7.2 当前 HIL 报告特点

部分 HIL 报告会记录：

- HELLO build ID；
- Bench 路径；
- 某些 Case 源文件 SHA256；
- JUnit 或专项 JSON 的 SHA256。

这些信息有价值，但仍无法唯一回答：

```text
本次 HIL 到底对应 Git 仓库中的哪一个完整提交？
固件镜像是否由该提交无修改生成？
Capability、Bench、PC Driver、固件 Service 和 Wrap 是否属于同一版本？
```

只记录两个 Case 文件 SHA256 不能代表整个平台代码状态。

### 5.7.3 风险与影响

1. 当前 `main` 变化后，无法判断历史 PASS/FAIL 对应哪套完整代码。
2. 同一个 firmware build ID 被重复使用时，报告无法区分镜像内容。
3. 问题修复后无法精确比较“修复前提交”和“修复后提交”。
4. 外部审阅者难以复现结论，只能相信人工描述。
5. 当前代码与历史验证报告出现矛盾时，无法快速判断是代码回归还是报告属于旧版本。

### 5.7.4 建议整改

在 `session.json` 和每个 CaseResult 中增加不可变版本字段：

```json
{
  "source_revision": "<git sha>",
  "source_dirty": false,
  "pc_source_sha256": "...",
  "firmware_image_sha256": "...",
  "firmware_elf_sha256": "...",
  "capability_manifest_sha256": "...",
  "bench_sha256": "...",
  "bitstream_sha256": "..."
}
```

固件 `HELLO` 最好上报：

- build ID；
- source revision 短 SHA；
- build manifest hash；
- Service Registry hash。

### 5.7.5 验收条件

1. 任意 HIL `session.json` 可唯一定位 Git commit。
2. 固件镜像内容变化时，即使 build ID 未变，SHA256 也会变化。
3. Capability 或 Bench 变化时，结果基线哈希变化。
4. 验证报告只需引用 session 路径和哈希，不再手工枚举零散源码 SHA。

---

## REV-008：PC README 引用已不存在的设计路径

**等级：P3**  
**状态：已确认**  
**影响范围：文档导航、新成员理解、Review 效率**

### 5.8.1 当前问题

`pc/README.md` 声明：

```text
架构遵循 docs/design/pc_layered_architecture.md
```

但当前正式设计文档位于：

```text
report/design/pc_layered_architecture.md
```

仓库根目录不存在当前有效的 `docs/design/` 主线。

### 5.8.2 风险与影响

1. GitHub 上链接不可用或指向不存在的位置。
2. 新开发者可能误以为还有另一套 `docs/` 设计主线。
3. 文档迁移已经完成，但入口文档仍保留旧路径，破坏“report 为唯一正式人读文档库”的治理规则。

### 5.8.3 建议整改

从 `pc/README.md` 使用正确相对链接：

```markdown
[PC端分层架构](../report/design/pc_layered_architecture.md)
```

同时对仓库 README、Firmware README 和子目录 README 执行一次链接扫描。

### 5.8.4 验收条件

1. GitHub 页面点击链接可直接打开正式设计文档。
2. 自动文档链接检查不再报告 `docs/design/...`。
3. 仓库不存在并行的正式设计目录入口。

---

# 6. 整改优先级建议

## 第一阶段：先保证测试结果可信

优先处理：

1. `REV-001` 控制 UART fixture 与 Runtime Registry 矛盾；
2. `REV-002` CaseResult 与专项结果统一；
3. `REV-003` Evidence 缺失必须影响退出状态；
4. `REV-007` 建立 Git/固件/Profile 不可变版本基线。

原因：如果资源门禁、结果和证据不可信，继续新增 IP Case 只会扩大返工范围。

## 第二阶段：恢复真正的跨芯片复用和通信可靠性

优先处理：

1. `REV-004` 去除公共 DMA Case 的 ET6801 硬编码；
2. `REV-005` 为只读命令补齐安全重试属性；
3. `REV-006` 建立跨语言 Service Contract 门禁。

## 第三阶段：文档和治理收口

处理：

1. `REV-008` 修复失效链接；
2. 扫描其他迁移后的路径漂移；
3. 将每项 Review 修复提交、验证命令和证据回填到本文。

---

# 7. 后续评审计划

下一轮继续按调用链逐层阅读，不只阅读单个文件：

## 7.1 UART 全链路

```text
UART pytest Case
  -> UartDriver
  -> UART Service
  -> UART Wrap
  -> ET6x UART Driver
  -> IRQ Manager
  -> Bench UART1/UART2 物理回环
```

重点检查：

- P0-P3 Case 是否与 `test_case_doc/UART.md` 一致；
- 控制 UART 与测试 UART 状态是否完全隔离；
- IRQ capture、FIFO、9-bit 地址、DMA、超时和清理路径；
- FAIL、SKIP 与 NOT_SUPPORTED 是否区分准确。

## 7.2 DMA P1-P3 与外设链路

重点检查：

- linked list、gather/scatter、软件握手、多通道启动；
- IRQ route 与 combined IRQ；
- Resource Service 分配的地址范围和保护；
- DMA 与 UART/SPI 等外设配合时的跨 IP 编排边界；
- Case 清理是否对所有失败路径成立。

## 7.3 Wrap 与 ET6801 SDK 映射

重点检查：

- Wrap 是否偷偷配置其他 IP；
- 是否存在直接寄存器访问；
- 逻辑 ID 到 SDK 实例、IRQ、IOMUX 的映射是否集中；
- `NOT_SUPPORTED`、非法参数和 SDK 返回值是否被正确归一。

## 7.4 Capability 生成器

重点检查：

- SVD Fact IR 是否真正无静默丢失；
- `derivedFrom`、数组、别名和重复路径；
- Semantic 规则是否出现隐式 IP 特判；
- Quality Report 是否能阻止错误 Profile 进入运行时；
- Runtime Service 交集是否会错误隐藏或错误保留实例。

## 7.5 构建、烧录与验证工具

重点检查：

- Keil 工程生成是否确定性；
- FPGA/Silicon Target 是否只切换允许的 Board、宏和链接脚本；
- PowerShell 脚本错误码、超时、日志和路径处理；
- 烧录、运行、pytest 和证据目录能否形成单一自动化入口。

---

# 8. 更新记录

| 时间 | 基线 | 内容 |
|---|---|---|
| 2026-08-05 | `b947b9c1ab6bd1db7cd9dccc8b164d21146dcdbc` | 建立 Review 文档；记录控制 UART、结果证据、pytest 退出状态、DMA 跨芯片复用、重试、协议契约、版本追溯和文档路径共 8 项问题 |
