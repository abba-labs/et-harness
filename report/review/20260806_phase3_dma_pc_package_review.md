# Phase 3：DMA PC Package 行为保持型迁移 Review

文档状态：正式 Review 结论  
Review 日期：2026-08-06  
目标仓库：`Abba-shenfu/Automated_Testing_Platform`  
目标分支：`review_code`  
代码验证基线：`5f657e144a1c5714b6b8adb1ec90358471e34cc5`  
GitHub Actions：`PC Quality Gate` Run `31082335860`

---

## 1. Review 结论

Phase 3 规定范围已经完成：

```text
Phase 3：DMA PC Package 行为保持型迁移 —— DONE
```

原单文件：

```text
pc/et_test_platform/drivers/dma.py
```

已拆分为：

```text
pc/et_test_platform/drivers/dma/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

旧单文件已经删除，不再保留两套实现。公开导入路径仍为：

```python
from et_test_platform.drivers.dma import DmaConfig, DmaDriver, DmaCommand
```

本阶段没有修改 Firmware、Command ID 或 Wire 语义。结论：**允许进入 Phase 4：PC Execution Mapping 与 DMA Route Resolver。**

---

## 2. 职责拆分结果

### `models.py`

只保留：

- DMA Enum/IntFlag；
- 强类型配置与结果 Model；
- `frozen=True, slots=True` Dataclass；
- 不访问 TargetClient；
- 不包含 `encode/decode/send/request`。

### `contract.py`

只保留：

- `DMA_SERVICE_ID`；
- `DmaCommand`；
- 已发布 Command ID 保持 `0x0001`～`0x001B` 不变。

### `codec.py`

独占：

- 全部 `struct.Struct`；
- Request Body Encode；
- Response Body Decode；
- Response Length 和固定 Wire 约束检查。

`DmaDriver` 中不再出现 `struct.pack/unpack` 或 Wire Offset 计算。

### `validation.py`

只负责 DMA 本 IP 参数：

- Handshake Mode/Polarity；
- Poll 参数；
- Channel Mask；
- LLI Handle/Offset。

跨 IP 地址、Request ID、Interface、Capability 与 Bench 一致性没有塞入 DMA Driver，继续留给 Phase 4 Resolver。

### `driver.py`

只负责：

- 单 DMA Service 命令；
- DMA 参数检查入口；
- Codec 调用；
- TargetClient 请求；
- 既有 Retry、Polling 与 Cleanup 行为；
- 返回稳定 Model。

没有导入或调用 Resource、SYSCTRL、UART、CRG 等其他 IP Driver。

### `__init__.py`

作为稳定 Facade：

- 重导出旧公开名称；
- 保持 `et_test_platform.drivers.dma` 导入路径；
- 保持历史 Struct 常量可导入；
- 使用 Compatibility Facade 保留 `DmaConfig.encode()`；
- 真正的 `models.DmaConfig` 不含 Wire 方法。

---

## 3. 公共 API 与 Wire 兼容

已锁定并验证：

- `DMA_SERVICE_ID == 0x0100`；
- 已发布 Command ID 未变化；
- `DMA_CONFIG.size == 64`；
- 其他已发布 Body Size 未变化；
- DMA Configure 代表性 Golden Bytes 未变化；
- `DmaConfig(...).encode()` 兼容入口仍可使用；
- `DmaDriver` 方法名和主要参数保持不变；
- Runtime Capability Cache 和 Retry-safe Command 集合保持原语义；
- LLI 仍使用旧版 `descriptor_handle + descriptor_offset + is_last` Wire，未提前改成地址语义。

代表性 64-Byte Golden Vector：

```text
000102030405060708090a0b0c0d0302
88776655443322111122334455667788
ddccbbaa04030201efcdab8967452301
14131211242322213433323144434241
```

---

## 4. 测试目录镜像

新增：

```text
pc/et_test_platform/framework_validation/unit/drivers/dma/
├── __init__.py
├── test_codec.py
├── test_validation.py
├── test_driver_commands.py
└── test_driver_errors.py
```

覆盖：

- Codec Golden Bytes；
- Model 无 Wire 方法；
- Compatibility Facade；
- Capability Decode；
- 参数校验；
- Command Mapping；
- Runtime Channel Limit；
- Configure Timeout 与 Cleanup Failure。

既有 DMA Contract、Case 和 Firmware Contract 测试继续执行，没有删除或弱化原有断言。针对 `slots=True`，旧测试中依赖 `__dict__` 的实现细节已改为标准 Dataclass `astuple()` 观测，不改变字段和值的断言。

---

## 5. 质量门禁

DMA Package 和镜像测试目录已加入统一质量范围：

```text
pc/et_test_platform/drivers/dma
pc/et_test_platform/framework_validation/unit/drivers/dma
```

实际通过：

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Committed Keil Artifact Contract      PASS
PC Unit / Contract Tests              279 passed, 3 skipped
```

GitHub Actions：

```text
Workflow : PC Quality Gate
Run ID   : 31082335860
Commit   : 5f657e144a1c5714b6b8adb1ec90358471e34cc5
Result   : SUCCESS
```

三个环境门禁项目仍记录为 `SKIPPED`，未写成 PASS。

---

## 6. AST 与结构检查结果

本阶段确认：

- `models.py` 无 `encode/decode/send/request`；
- `driver.py` 无直接 Struct 编解码；
- `codec.py` 不导入 TargetClient；
- DMA Driver 不导入其他 IP Driver；
- 新模块均有 Module Docstring；
- 公共 API 有类型标注；
- 未新增 `utils.py/common.py/helpers.py/misc.py`；
- DMA Package 没有新增 Ruff/McCabe Allowlist；
- 旧 `drivers/dma.py` 已删除。

---

## 7. Firmware、Keil 与 HIL

| 验证层级 | 本阶段状态 | 说明 |
|---|---|---|
| Python Syntax/Ruff/AST | PASS | GitHub Actions 实际执行 |
| Host Unit/Contract | PASS | 279 passed，3 skipped |
| Firmware Source/Wire | UNCHANGED | 本阶段未修改 Firmware |
| Keil 提交物 Contract | PASS | 只验证仓库提交物结构与 Hash |
| Keil FPGA/Silicon Build | NOT_EXECUTED | 不属于 Phase 3 |
| 真实 HIL | NOT_EXECUTED | 不属于 Phase 3 |

Keil 提交物 Contract 通过不等同于真实 Keil 编译通过。

---

## 8. 未关闭风险与后续约束

1. DMA `start_wait()` 仍保留旧 Poll-Count 期限语义，严格总 Deadline 属于 Phase 7；
2. DMA 地址、外设 Request ID、Controller Interface 和跨 IP 一致性尚未进入强类型 Resolver，属于 Phase 4；
3. SYSCTRL 仍使用旧 Endpoint/Instance/Address Contract，属于 Phase 5；
4. Firmware DMA Service 中的 Resource/Route/Lease 仍未删除，属于 Phase 6；
5. Keil 实际构建和 HIL 尚未执行，不能评价整体重构完成。

---

## 9. 是否允许进入下一阶段

允许进入：

```text
Phase 4：PC Execution Mapping 与 DMA Route Resolver
```

Phase 4 必须继续遵守：

- Mapping 数值必须来自 SDK、Chip Config、SVD 或手册证据，不得猜测；
- Resolver 只解析和验证，不执行硬件命令；
- 原始 YAML Dict 不直接泄漏到 Case；
- Phase 4 不提前复用旧 SYSCTRL Command ID 改义；
- SYSCTRL V2 Wire 变化必须留到 Phase 5，并使用新 Command ID。
