# ET 自动化测试平台重构交付报告

> **2026-08-09 状态说明**：本文记录 2026-08-06/07 的历史“软件结构重构与质量门禁”交付闭环。后续 `review_code` 已继续进行公共层芯片无关化、UART/DMA Driver 收敛和 Case 可读性优化。本文中的“Formal Case Software Review PASS / 软件层整体重构 DONE”只表示当时结构与门禁成立，**不表示后续 Case 极简化已经完成**。当前阶段状态以 [PC公共层与UART/DMA Driver收敛阶段收口报告](20260809_pc_driver_convergence_phase_closure.md) 和 [report/README.md](../README.md) 为准。

原始日期：2026-08-06  
软件最终复核：2026-08-07  
仓库：`Abba-shenfu/Automated_Testing_Platform`  
分支：`review_code`  
软件闭环代码基线：`f7b8aba354f094cda793df4c4f343781690214fd`

## 1. 当前交付状态

本报告现在区分**软件层交付**与**真实硬件验证**：

```text
软件层重构与质量闭环     DONE
实际 Keil FPGA Build     NOT_EXECUTED
实际 Keil Silicon Build  NOT_EXECUTED
真实 HIL                  NOT_EXECUTED
```

因此，本轮用户要求的“非硬件软件层”已经完成；硬件 Build/HIL 不被虚构为 PASS，也不再反向否定软件层已经完成的事实。

软件最终证据：

- [软件层最终重构 Review](../review/20260807_software_layer_final_review.md)
- GitHub Actions Run `31137876718`

## 2. 最终软件架构

唯一正式主链：

```text
PC Test Case
  -> Resolver / Capability
  -> Single-IP Driver
  -> Contract / Codec
  -> TargetClient / ET-Frame
  -> Firmware IP Service
  -> Own IP Wrap
  -> SDK
```

最终边界：

- PC 是可信控制面；
- Firmware Service 只负责 Decode、执行本 IP Wrap、Encode Facts；
- Test Case 拥有跨 IP 顺序、Evidence、最终 Assertion 与整体 Cleanup；
- Driver 只负责单一 IP；
- Codec 只负责 Wire；
- Resolver 只解析 Capability/Mapping/Runtime/Bench 事实，不发送硬件命令；
- 不引入 Workflow Engine、通用跨 IP Resource Graph 或 DI 容器。

## 3. Wire 与执行映射

- Published Command ID 未静默改义；
- SYSCTRL DMA Mux 新语义使用 V2 Command；
- DMA LLI 新语义使用直接 Descriptor Address V2；
- UART DMA Route 由 PC Mapping/Resolver 解析；
- Firmware 不再承担 UART Endpoint Registry -> Resource Registry -> SYSCTRL V1 的跨 IP可信链；
- Formal Case 不再调用 SYSCTRL V1 `configure_dma_request()`；
- DMA 外设事务中断 Case 不再通过 `dma_peer.py` Adapter 隐藏 UART/SYSCTRL/DMA 生命周期。

## 4. 可靠性闭环

软件层最终具备：

- Request Write/Read/Retry 共享 Operation Deadline；
- Decoder 同批 Response 后 Event 不丢失；
- Duplicate Response Fail Closed；
- DMA/UART 长操作总 Deadline；
- Primary Error + 所有 Cleanup Error 同时保留；
- UART Deinit 失败不提前清真实 Handle；
- IRQ Bind 回滚失败保留 Cleanup Ownership；
- DMA ISR 读取状态失败可观测；
- UART Capture 内部 IRQ Cleanup Fault 不被数据匹配掩盖；
- Control UART Close、Resource Create、Service Registry 具备失败恢复/回滚；
- Frame Parser 无新字节时仍可 Drain 已缓存完整 Frame。

## 5. PC Package

DMA、UART、SYSCTRL、Resource、Framework、CRG 等已收敛到职责明确的 Package：

```text
models.py
contract.py
codec.py
validation.py
driver.py
__init__.py
```

历史 Ruff Allowlist 已清零。

## 6. Formal Test Case

DMA/UART Case 已按主要测试主体和 Feature 组织。

Formal Case 直接呈现：

```text
Arrange -> Resolve -> Configure -> Start -> Observe -> Assert -> Cleanup
```

永久规则禁止：

- 完整 Case Helper；
- Helper 最终 Assertion；
- Helper 隐藏多阶段生命周期；
- Helper 持有整体 Cleanup；
- 非 Test Helper Module 同时编排多个 IP Driver；
- raw `finally` 顺序 Cleanup；
- Case-specific Conclusion Helper；
- Design/Observability Blocked Feature 伪装为正式 `test_*`。

不具备批准证据的 Feature 进入 `deferred_features.py`。

Measurement JSON 只保存事实/Measurement，不拥有第二套 PASS/FAIL。

## 7. UART / DMA 外设链路

UART DMA TX/RX/Full Duplex，以及 DMA Handshake、SOURCE_TRANSACTION IRQ、DESTINATION_TRANSACTION IRQ，均按照最终模型直接执行：

```text
Resolve Route
-> UART Configure
-> SYSCTRL V2
-> DMA Configure / IRQ / Start
-> Buffer/Capture/IRQ Evidence
-> Assert
-> Aggregate Cleanup
```

旧 `dma_peer.py` 已删除。

## 8. Protocol Capacity

UART PC/Firmware 的单次 Wire Payload 已与 ET-Frame/ET-Message 实际承载上限对齐：

- PC Driver 对长读写分块；
- Firmware Service 对长度 Fail Closed；
- Protocol Capacity 有独立 Unit Contract；
- Runtime Capability 不再承诺超出实际 Message Capacity 的单次 Body。

## 9. 最终软件验证

最终收口 Run：`31137876718`。

候选树验证通过后，Runner 删除所有临时迁移资产；随后在最终生产树上重新执行完整验证，仍通过。

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Formal Case Orchestration Rules       PASS
Generated Firmware Project Contract   PASS
Unit / Contract / Native               331 passed, 3 skipped
Formal Case Collection                235 nodes
Legacy Formal Case Path Scan          PASS / 0 hit
Git diff --check                      PASS
```

3 个 Skip 仍是显式环境门禁，不代表真实硬件 PASS。

235 个 Formal Case 节点只表示软件 Case 定义/Import/Fixture/参数化/Collection 全部成立，不等价于板卡执行。

## 10. 永久 CI 与迁移债务

最终 `.github/workflows/` 只保留永久：

```text
pc-quality.yml   # Software Quality Gate
```

永久门禁覆盖 PC、Firmware、Tools 与 Workflow 变化，并要求统一软件验证后工作树保持干净。

最终提交 `f7b8aba354f094cda793df4c4f343781690214fd` 删除：

- `tools/refactor/` 全目录；
- 所有 `one-shot-*.yml`；
- `case-orchestration-audit.yml`；
- `dma_peer.py`；
- 对应旧 Adapter/Helper 合同。

当前临时迁移债务：`0`。

## 11. 硬件验证状态

本轮按用户要求不继续硬件链路。

历史环境审计确认两个 Keil Target 存在，但实际工具环境没有执行：

```text
ET6801_FPGA_ITCM         NOT_EXECUTED
ET6801_SILICON_FLASH     NOT_EXECUTED
```

真实 FPGA/Silicon HIL：

```text
NOT_EXECUTED
```

对应记录：

- [ET6801 Keil实际构建报告](../build/20260806_et6801_keil_build_report.md)
- [ET6801真实HIL执行报告](../hil/20260806_et6801_hil_report.md)

## 12. 阶段状态

| 范围 | 状态 |
|---|---|
| Phase 0 基线与缺陷锁定 | DONE |
| Phase 1 质量门禁 | DONE |
| Phase 2 Core Reliability | DONE |
| Phase 3 DMA Package | DONE |
| Phase 4 架构边界与执行映射 | DONE |
| Phase 5 Reliability / Package | DONE |
| Phase 6A Formal Case Software | DONE |
| Phase 6B Software Static/Unit/Native | DONE |
| Phase 6E Software Final Review / CI | DONE |
| **软件层整体重构** | **DONE** |
| Phase 6C 实际 Keil Build | NOT_EXECUTED |
| Phase 6D 真实 HIL | NOT_EXECUTED |

## 13. 当前发布结论

```text
Software Architecture Review : PASS
Software Reliability Review  : PASS
Formal Case Software Review   : PASS
Permanent Software Gate       : PASS
Software Refactor             : DONE
Hardware Build/HIL            : NOT_EXECUTED
```

本轮可以正式宣布：**非硬件软件层重构已完成，并建立永久防回退规则。**

未来只有在需要宣布完整 FPGA/Silicon 硬件交付时，才继续执行实际 Keil Build、Build ID 匹配和真实 HIL。
