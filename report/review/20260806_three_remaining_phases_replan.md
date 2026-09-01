# 剩余重构压缩为三个阶段的计划变更 Review

文档状态：正式计划变更记录  
日期：2026-08-06  
目标仓库：`Abba-shenfu/Automated_Testing_Platform`  
目标分支：`review_code`

---

## 1. 变更原因

Phase 0～3 已经完成，但原计划仍将剩余工作拆为多个小阶段，阶段切换、状态更新、Review 文档和等待确认的频率偏高，影响整体推进效率。

用户明确要求：

```text
后续只保留三个阶段；
每个阶段内部允许包含多个连续步骤；
三个阶段完成后，必须完成全部剩余重构、构建、HIL 和最终 Review。
```

本次计划变更只压缩执行节奏，不修改已经确认的 PC/Firmware 信任边界、Wire 兼容原则、Test Case 归属规则和最终硬件闭环要求。

---

## 2. 新的三个剩余阶段

### Phase 4：架构边界与执行映射闭环

合并原：

- Execution Mapping / Resolver；
- SYSCTRL V2；
- DMA Firmware 执行代理化。

本阶段一次性完成 PC 侧地址、Request ID、Controller、Interface 的强类型解析，以及 SYSCTRL/DMA Firmware 中跨 IP Registry、Route、Lease、Endpoint 逻辑的清理。

### Phase 5：可靠性与 PC/Firmware Package 全面收敛

合并原：

- DMA Deadline / 异常语义；
- UART PC Package / Deadline / Cleanup；
- UART Firmware Cleanup 可重试；
- IRQ Manager / Frame Parser；
- Resource / Framework / CRG 等其余 PC Package。

本阶段完成所有剩余公共可靠性和代码职责收敛，目标是 PC 全仓质量门禁通过、历史 Allowlist 清零。

### Phase 6：Test Case、构建、HIL 与最终交付

合并原：

- Test Case 按主要测试主体和 Feature 重构；
- Keil FPGA/Silicon Build；
- 真实 HIL；
- Final Architecture Review。

本阶段完成最终可读性、真实构建和硬件闭环，并形成最终交付报告。

---

## 3. 效率调整

新的执行方式：

1. 每个大阶段只维护一次 `IN_PROGRESS -> DONE/BLOCKED` 状态；
2. 阶段内部使用 4A/4B/4C、5A/5B 等工作包，不再为每个工作包单独停下来等待确认；
3. 每个主题仍保持独立 Commit，避免把 Wire、目录迁移、行为修复混为一个 Commit；
4. 每次 Push 继续运行快速 Host CI；
5. 每个大阶段只形成一份正式 Review 文档；
6. 只有架构冲突、Wire 无法兼容、测试无法稳定复现或真实硬件阻断时才暂停并汇报；
7. 未执行的 Keil/HIL 仍不得写成 PASS。

---

## 4. 不变的强制约束

- 只修改 `review_code`，禁止直接修改 `main`；
- PC 是可信控制面，Firmware 是执行面；
- Driver 只负责单一 IP；
- Firmware Service 只能调用本 IP Wrap；
- 已发布 Command ID 不得静默改义；
- 新 Wire 语义必须使用新 Command ID；
- UART DMA Case 按主要测试主体归入 `test_cases/uart/`；
- Host、C Native、Keil、HIL 结果分开记录；
- 错误 PASS 比缺少测试更严重，Result/Evidence 必须闭环。

---

## 5. 结论

原 Phase 4～12、Keil、HIL、Final 的剩余工作正式重映射为新的 Phase 4～6。

本次变更批准后，执行过程中不再按旧小阶段逐次等待确认；每完成一个新的大阶段，再进行一次完整汇报。
