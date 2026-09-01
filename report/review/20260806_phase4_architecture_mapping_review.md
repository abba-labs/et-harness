# Phase 4：架构边界与执行映射闭环 Review

文档状态：正式 Review 结论  
Review 日期：2026-08-06  
目标仓库：`Abba-shenfu/Automated_Testing_Platform`  
目标分支：`review_code`  
代码验证基线：`8084d39aacc6a5ba7d8dc71a9c8ceb63ab549368`  
GitHub Actions：`PC Quality Gate` Run `31087265611`

---

## 1. Review 结论

新 Phase 4 规定的四个工作包已经完成：

```text
4A  ET6801 Execution Mapping / Resolver
4B  SYSCTRL V2
4C  DMA Firmware 执行代理化
4D  联合回归与架构检查
```

本阶段完成后，UART DMA 所需的外设地址、DMA Request ID、Controller 和 Interface 由 PC Resolver 统一核对；SYSCTRL Firmware 只执行直接 Request ID；DMA Firmware 不再维护 Resource Range、Endpoint、Route、Lease 或跨 Service 地址解析。

结论：

```text
Phase 4：架构边界与执行映射闭环 —— DONE
```

允许进入：

```text
Phase 5：可靠性与 Package 全面收敛
```

---

## 2. 4A：ET6801 Execution Mapping

新增：

```text
pc/et_test_platform/profiles/chip_execution_mappings/
├── __init__.py
└── et6801/
    ├── __init__.py
    └── dma_routes.py

pc/et_test_platform/profiles/resolvers/
├── __init__.py
└── dma_routes.py
```

### 2.1 已固化的 UART DMA 映射

| UART | 方向 | 外设地址 | Request ID |
|---|---:|---:|---:|
| UART0 | TX | `0x40500000` | `192` |
| UART0 | RX | `0x40500000` | `193` |
| UART1 | TX | `0x40501000` | `194` |
| UART1 | RX | `0x40501000` | `195` |
| UART2 | TX | `0x40502000` | `196` |
| UART2 | RX | `0x40502000` | `197` |

来源证据：

- 外设地址：ET6801 SVD 生成的 UART Capability，RBR/THR Offset 为 `0x0`；
- Request ID：`firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h`；
- 当前 Controller/Interface 边界：ET6801 Chip Config、SYSCTRL Wrap 和 Bench Topology。

Mapping 与自动生成 Capability 分开保存，没有向 SVD 生成文件写入人工事实。

### 2.2 Resolver 行为

新增强类型：

```text
DmaPeripheralMapping
DmaPeripheralRoute
DmaPeripheralDirection
```

`resolve_uart_dma_route()` 在返回 Route 前同时核对：

- Chip ID 必须为 `et6801`；
- Bench Provider 必须是 UART；
- Runtime Registry 必须包含 DMA、SYSCTRL、UART Service；
- UART Instance 必须存在于 Capability；
- SVD Base Address 必须与人工 Mapping 一致；
- DMA Controller 必须存在；
- Controller/Interface 必须在 Mapping 允许范围；
- TX 使用 Bench `destination_interface`；
- RX 使用 Bench `source_interface`。

Resolver 只读取事实并返回强类型结果，不访问 TargetClient，不调用 Driver，也不发送硬件命令。

---

## 3. 4B：SYSCTRL V2

### 3.1 PC Package

原单文件：

```text
pc/et_test_platform/drivers/sysctrl.py
```

已拆分并删除旧实现：

```text
pc/et_test_platform/drivers/sysctrl/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

公开导入路径保持：

```python
from et_test_platform.drivers.sysctrl import SysctrlDriver
```

新增强类型：

```text
DmaRequestRoute(controller, interface, request_id)
```

新增 API：

```text
configure_dma_request_v2(controller, interface, request_id)
configure_route(route)
```

### 3.2 Wire Contract

旧命令保持原编号和原 Body：

```text
0x0001  DMA_REQUEST_CONFIGURE V1   <4BQ>  12 Bytes
0x0002  DMA_REQUEST_RELEASE        <2B2x> 4 Bytes
```

新语义使用新 Command ID：

```text
0x0003  DMA_REQUEST_CONFIGURE_V2   <4B>   4 Bytes
```

V2 Body：

```text
Byte 0  controller
Byte 1  interface
Byte 2  request_id
Byte 3  reserved = 0
```

旧 `0x0001` 没有被静默改义。PC 兼容编码仍保留；Firmware 明确将其标记为 Deprecated，并在 Body 长度合法时返回 `NOT_SUPPORTED`。

### 3.3 Firmware Service / Wrap

SYSCTRL Service 已删除：

- Resource Wrap 依赖；
- Provider/Endpoint/Instance/Address 解析；
- 64-bit 外设地址解析；
- 跨 IP Route 发布。

SYSCTRL Wrap 已删除：

- UART Request Table；
- UART Endpoint 到 Request ID 的映射；
- UART Instance 判断。

当前执行链：

```text
PC Resolver
→ SysctrlDriver V2
→ SYSCTRL Service Decode
→ SYSCTRL Wrap(controller, interface, request_id)
→ SYSCTRL_configDMAMux()
```

---

## 4. 4C：DMA Firmware 执行代理化

### 4.1 删除的跨 IP 状态和逻辑

DMA Service Header/Source 已删除：

- `resource_pool_owned_channels`；
- Source/Destination Route Ownership；
- Source/Destination Route Interface；
- Source/Destination Route Address；
- Resource Range Resolve/Contains；
- Peripheral Endpoint Validation；
- Route Acquire/Release；
- Pool Lease；
- Route Lease；
- LLI Handle 到 Address 的 Resource 解析；
- `et_resource_wrap` 依赖。

DMA Service 当前只保留：

- Controller Enable 状态；
- Channel Count；
- Configured/Active Channel Mask；
- Managed IRQ Session；
- IRQ Route Binding Progress；
- IRQ Result；
- Service Descriptor。

### 4.2 DMA Configure

DMA Configure 仍使用原 64-Byte Body，Service 只执行：

```text
Wire Length / Handshake Reserved 检查
→ Channel 边界检查
→ uint64 到 uintptr_t 无截断检查
→ Decode DMA 本 IP Config
→ et_dma_wrap_configure_channel()
```

Firmware 不再判断地址是否属于 Resource Pool，也不再判断地址是否对应当前 UART Route。相关一致性由 PC Resolver、Capability 和 Test Case 负责。

### 4.3 LLI V2

旧命令保持编号：

```text
0x0014  LLI_DESCRIPTOR_INIT V1
```

旧 V1 的 Handle+Offset Body 没有被改义，Firmware 明确返回 `NOT_SUPPORTED`。

新命令：

```text
0x001C  LLI_DESCRIPTOR_INIT_V2
```

V2 Body：

```text
64 Bytes  原 DMA Config
8 Bytes   Descriptor Address uint64
1 Byte    is_last
7 Bytes   reserved = 0
总计      80 Bytes
```

Firmware 校验：

- 固定长度；
- `is_last` 为 0/1；
- Reserved 全零；
- Descriptor Address 非零；
- uint64 到 `uintptr_t` 无截断；
- DMA Config 本身合法。

通过后直接调用：

```text
et_dma_wrap_init_lli_descriptor(config, descriptor_address, is_last)
```

---

## 5. 4D：测试与质量门禁

新增测试目录：

```text
framework_validation/unit/profiles/
└── test_dma_route_resolver.py

framework_validation/unit/drivers/sysctrl/
└── test_sysctrl_v2.py

framework_validation/unit/drivers/dma/
└── test_lli_v2.py
```

覆盖：

- UART0/1/2 TX/RX 六条 Mapping；
- Mapping 来源证据非空；
- TX/RX Interface 选择；
- Runtime Service 缺失；
- 未核对 UART Instance；
- 非 UART Bench Provider；
- SYSCTRL V2 Command/Body Golden Bytes；
- SYSCTRL V1/Release Wire Stability；
- DMA LLI V2 80-Byte Golden Body；
- 非法 Descriptor Address；
- DMA/SYSCTRL Firmware 去 Resource/Route/Lease 架构搜索；
- 旧 V1 Command 明确 `NOT_SUPPORTED`；
- Pointer Width 安全检查；
- DMA IRQ/Channel 生命周期边界。

Phase 4 新 Package 已加入统一 Ruff/AST 范围：

```text
pc/et_test_platform/drivers/sysctrl
pc/et_test_platform/profiles/chip_execution_mappings
pc/et_test_platform/profiles/resolvers
framework_validation/unit/drivers/sysctrl
framework_validation/unit/profiles
```

---

## 6. 自动验证证据

GitHub Actions：

```text
Workflow : PC Quality Gate
Run ID   : 31087265611
Commit   : 8084d39aacc6a5ba7d8dc71a9c8ceb63ab549368
Result   : SUCCESS
```

实际结果：

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Committed Keil Artifact Contract      PASS
PC Unit / Contract / Existing Native  285 passed, 3 skipped
```

三个环境门禁项目保持为 `SKIPPED`，未写成 PASS。仓库现有 C/Native Contract 检查包含在全量测试中；本阶段没有用 Keil 提交物 Hash 检查替代真实 Keil Build。

---

## 7. Public API 与 Wire 变化

| 项目 | 结果 |
|---|---|
| DMA 旧 Public Import | 保持 |
| SYSCTRL 旧 Public Import | 保持 |
| DMA Configure 64-Byte Wire | 保持 |
| SYSCTRL V1 12-Byte Wire | 保持，Firmware Deprecated/NOT_SUPPORTED |
| SYSCTRL Release Wire | 保持 |
| 旧 Command ID | 未复用、未静默改义 |
| SYSCTRL V2 | 新增 `0x0003` |
| DMA LLI V2 | 新增 `0x001C` |
| Firmware Service 跨 IP Resource 依赖 | 已删除 |

---

## 8. Keil 与 HIL 状态

| 验证层级 | Phase 4 状态 | 说明 |
|---|---|---|
| Python Syntax/Ruff/AST | PASS | GitHub Actions 实际执行 |
| Host Unit/Contract | PASS | `285 passed, 3 skipped` |
| 现有 C/Native Contract | 随全量测试通过 | 3 个环境门禁仍为 Skip |
| Keil 提交物 Contract | PASS | 仅仓库结构/Hash |
| ET6801 FPGA Keil Build | NOT_EXECUTED | 留到 Phase 6 |
| ET6801 Silicon Keil Build | NOT_EXECUTED | 留到 Phase 6 |
| 真实 HIL | NOT_EXECUTED | 留到 Phase 6 |

---

## 9. 未关闭风险与后续约束

1. DMA `start_wait()` 仍是旧 Poll-Count 期限语义，严格总 Deadline 属于 Phase 5；
2. UART PC Package、总 Deadline、9-bit 参数和 Cleanup Error 属于 Phase 5；
3. UART Firmware Cleanup 可重试属于 Phase 5；
4. IRQ Manager Partial Cleanup 与 Frame Parser Buffered Drain 属于 Phase 5；
5. Resource/Framework/CRG 等其余 PC Package 全面规范化属于 Phase 5；
6. Test Case Feature 重组、真实 Keil Build、HIL 和 Final Review 尚未执行；
7. SYSCTRL V1 和 DMA LLI V1 当前只保留兼容编号/编码，不再由 Firmware 执行，后续 Case 必须迁移到 V2。

---

## 10. 是否允许进入下一阶段

允许进入：

```text
Phase 5：可靠性与 Package 全面收敛
```

Phase 5 执行过程中仍必须保持：

- 不复用旧 Command ID 改义；
- Driver 不跨 IP；
- Firmware Service 只调用本 IP Wrap；
- Resolver 不发送硬件命令；
- Primary Error 与 Cleanup Errors 均可见；
- 未执行 Keil/HIL 不得写成 PASS。
