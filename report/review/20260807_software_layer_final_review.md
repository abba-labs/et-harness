# 软件层最终重构 Review

日期：2026-08-07  
仓库：`Abba-shenfu/Automated_Testing_Platform`  
分支：`review_code`  
软件闭环代码基线：`f7b8aba354f094cda793df4c4f343781690214fd`  
最终收口执行：GitHub Actions Run `31137876718`

## 1. Review 结论

本 Review 只判定**非硬件软件层重构**，不把实际 Keil 编译、板卡下载或真实 HIL 作为本结论的通过条件。

结论：

```text
PC / Firmware 软件架构重构        DONE
Formal Test Case 软件实现          DONE
软件静态/Unit/Contract/Native      DONE
Formal Case 非硬件收集             DONE
永久软件质量门禁                  DONE
临时重构脚本/Workflow 清场         DONE
实际 Keil FPGA/Silicon Build       NOT_EXECUTED
真实 HIL                           NOT_EXECUTED
```

因此：**软件层允许标记为 DONE；硬件验证仍单独保持 NOT_EXECUTED。**

## 2. 最终强制架构

软件最终主链固定为：

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

强制约束：

- PC 是可信控制面；
- Firmware Service = Decode + Execute Own Wrap + Encode Facts；
- Test Case 是跨 IP 顺序、Evidence、Assertion 和整体 Cleanup 的唯一所有者；
- Driver 只负责一个 IP；
- Codec 只负责 Wire；
- Resolver 只解析事实，不执行硬件命令；
- Published Command ID 不静默改义；
- SYSCTRL 新执行语义使用 V2；
- DMA LLI 新执行语义使用直接地址 V2；
- JSON/Measurement 不拥有第二套 PASS/FAIL；
- 不具备批准证据的 Feature 进入 `deferred_features.py`，不得伪装成正式 `test_* + pytest.skip`。

## 3. 旧执行路径最终清零

最终生产树已禁止并扫描以下路径：

```text
execute_m2m_transfer
execute_peripheral_transfer
execute_dma_transfer_done_interrupt
_cleanup_all
build_dma_peripheral_pair
configure_dma_request(        # SYSCTRL V1 formal Case
uart_session(
loopback_transfer(
paired_transfer(
_require_irq_event(
require_cleanup(
```

最终收口 Run 在提交前和删除临时资产后分别执行遗留路径扫描，均通过。

### 3.1 UART DMA

UART DMA TX、RX、Full Duplex 正式 Case 直接展示：

```text
Resolve UART DMA Route
-> UART Configure
-> SYSCTRL V2 configure_route
-> DMA Configure / Start
-> Capture / Buffer Evidence
-> Assert
-> Aggregate Cleanup
```

不再依赖 Firmware Endpoint Registry 或 SYSCTRL V1 Endpoint/Instance/Address 路由。

### 3.2 DMA 外设事务中断

`SOURCE_TRANSACTION` 与 `DESTINATION_TRANSACTION` 两个 DMA Case 已移除 `dma_peer.py` Adapter，直接拥有：

```text
Resolver
UART DUT / Peer
SYSCTRL V2
DMA / IRQ
Evidence
Aggregate Cleanup
```

`dma_peer.py` 已从最终生产树删除。

### 3.3 DMA LLI

正式 LLI Case 使用 Descriptor Address V2；不再由 Formal Case 依赖旧 Handle V1 执行路径。

## 4. Formal Case 编排规则

永久工具：

```text
tools/check_case_orchestration_rules.py
```

最终规则至少强制：

- 禁止 Formal Case 调用完整执行 Helper；
- 禁止 Helper 拥有最终 Assertion；
- 禁止 Helper 同时隐藏 Arrange/Configure/Start/Observe/Cleanup 多阶段；
- 禁止 Helper 拥有生命周期 Cleanup；
- 禁止 `execute_*` 完整 Case Helper；
- 禁止非 Test Helper Module 同时导入多个 IP Driver；
- 禁止 Formal Case 使用 raw `finally` 顺序 Cleanup；
- 禁止 Helper 通过 `case_id` 抛 Case-specific Conclusion；
- 禁止 Design/Observability Blocked Feature 以正式 `test_*` 存在。

`cleanup_actions()` 是唯一允许的嵌套 Cleanup Factory，由 `case_cleanup_scope()` 统一聚合 Primary Error 与 Cleanup Errors。

## 5. Deadline / Error / Cleanup

软件层最终保留以下可靠性规则：

- TargetClient Request 的 Write、Read、Retry 共享操作总 Deadline；
- 同一 Decoder Batch 中 Response 后续 Event 不再丢失；
- Duplicate Response Fail Closed；
- DMA/UART 长操作使用总 Deadline；
- Primary Error 与所有 Cleanup Error 同时可见；
- UART Wrap Deinit 失败不提前丢失真实 Handle；
- IRQ Bind 回滚失败保留可继续 Cleanup 的 Ownership；
- DMA ISR 状态读取失败形成可观测错误事实；
- UART Capture 内部 IRQ Cleanup Fault 不允许被数据匹配掩盖；
- Control UART Close、Resource Create、Service Registry 具备失败恢复/回滚语义。

## 6. Protocol Capacity

UART 软件传输上限已与 ET-Frame / ET-Message 实际 Payload Capacity 对齐：

- PC Driver 按安全 Body Capacity 分块；
- Firmware Service 对请求/响应长度 Fail Closed；
- 新增 UART Protocol Capacity Unit Contract；
- 不再对外宣称单次可承载超出 Frame/Message Capacity 的 Wire Body。

## 7. 最终非硬件验证

最终收口 Run `31137876718` 在**候选树**和**删除全部迁移资产后的最终生产树**上各执行一次软件验证。

结果：

```text
Python Syntax                         PASS
Ruff Format                           PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Formal Case Orchestration Rules       PASS
Generated Firmware Project Contract   PASS
PC Unit / Contract / Native            331 passed, 3 skipped
Formal Case Collection                235 nodes collected
Legacy Formal Case Path Scan          PASS / 0 hit
Temporary Refactor Asset Check        PASS
Git diff --check                      PASS
```

3 个 Skip 属于既有环境门禁，不代表任何硬件 PASS。

235 个 Formal Case 节点只表示软件定义、Fixture、Import、参数化和收集链完整；它们没有在本 Review 中被解释为真实硬件执行成功。

## 8. 临时资产清场

最终提交 `f7b8aba354f094cda793df4c4f343781690214fd`：

```text
82 files changed
2910 insertions
17680 deletions
```

并删除：

- `tools/refactor/` 全目录；
- `.github/workflows/case-orchestration-audit.yml`；
- 所有 `.github/workflows/one-shot-*.yml`；
- `test_cases/dma/dma_peer.py`；
- 对应旧 Adapter/Helper Unit Contract。

最终 `.github/workflows/` 只保留永久 `pc-quality.yml` 软件质量门禁。

## 9. 永久软件门禁

永久 Workflow 名称：`Software Quality Gate`。

它对 `review_code` Push 运行，并对以下 PR 变化触发：

```text
pc/**
firmware/**
tools/**
pyproject.toml
.github/workflows/**
```

门禁调用统一 `python tools/validate_pc.py`，并要求验证完成后工作树保持干净，避免验证脚本产生未跟踪或被修改的提交物。

统一验证入口永久包含：

```text
Python Syntax
Ruff Format
Ruff Lint
PC AST Architecture Rules
Formal Case Orchestration Rules
Generated Firmware Project Contract
PC Unit / Contract / Native
Formal Case Collection
```

其中 Generated Firmware Project Contract 只验证工程描述和提交物生成合同，不等价于实际 Keil Build。

## 10. 硬件边界

本轮按用户要求不继续硬件链路，因此以下项目保持：

```text
ET6801 FPGA Keil Build       NOT_EXECUTED
ET6801 Silicon Keil Build    NOT_EXECUTED
真实 FPGA/Silicon HIL        NOT_EXECUTED
```

这些状态不会反向阻止“软件层 DONE”，但在未来宣布“完整硬件交付完成”前仍必须实际执行。

## 11. 最终软件发布结论

```text
Software Architecture Review : PASS
Software Reliability Review  : PASS
Formal Case Software Review   : PASS
Software Quality Gate         : PASS
Temporary Migration Debt      : 0
Hardware Build/HIL            : NOT_EXECUTED
```

截至本 Review，前一轮人工代码审核发现的软件 Blocker/P1 已在软件范围内完成整改和回归；后续新增代码必须持续接受永久规则与 CI 的防回退检查。
