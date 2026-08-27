# Framework Boundary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复已确认的固件分层、PC 启动校验和 DMA Case 组织问题，同时暂缓 Driver 缺失 Feature 时的 Wrap 规则。

**Architecture:** 固件把 Cortex、CRG、SYSCTRL 分成独立 Wrap，System Wrap 只保留系统时钟更新；CRG Service 只调用 CRG Wrap，SYSCTRL Service 只调用 SYSCTRL Wrap。PC 在 HELLO 后读取 SERVICE_LIST、复算 registry hash，并把本地 YAML 能力限制为运行固件实际公布的 IP 实例。

**Tech Stack:** C99、Keil uVision 工程生成、Python 3、pytest、YAML capability profile。

## Global Constraints

- 不处理 UART Wrap 中 Driver 未暴露 Feature 的通用规则。
- 不执行硬件烧录或运行控制。
- Wrap 之间不得相互调用；每个 Wrap 只能直接使用自身 Driver 家族。
- Service 不直接访问寄存器或 Chip Driver。
- 公共 DMA Case 不出现芯片名称或 ET6801 专有结论。

---

### Task 1: 固件 Wrap 边界与 DMA Manager 清理

**Files:**
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/include/et_cortex_wrap.h`
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/include/et_crg_wrap.h`
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/include/et_sysctrl_wrap.h`
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/src/et_cortex_wrap.c`
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/src/et_crg_wrap.c`
- Create: `Et_Automated_Testing_Platform_Code/firmware/wrap/src/et_sysctrl_wrap.c`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/wrap/include/et_system_wrap.h`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/wrap/src/et_system_wrap.c`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/application/src/main.c`
- Create: `Et_Automated_Testing_Platform_Code/firmware/services/include/et_crg_service.h`
- Create: `Et_Automated_Testing_Platform_Code/firmware/services/include/et_sysctrl_service.h`
- Create: `Et_Automated_Testing_Platform_Code/firmware/services/src/et_crg_service.c`
- Create: `Et_Automated_Testing_Platform_Code/firmware/services/src/et_sysctrl_service.c`
- Delete: `Et_Automated_Testing_Platform_Code/firmware/services/include/et_system_service.h`
- Delete: `Et_Automated_Testing_Platform_Code/firmware/services/src/et_system_service.c`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/framework/include/et_runtime.h`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/framework/src/et_runtime.c`
- Delete: `Et_Automated_Testing_Platform_Code/firmware/framework/include/et_dma_manager.h`
- Delete: `Et_Automated_Testing_Platform_Code/firmware/framework/src/et_dma_manager.c`

**Interfaces:**
- Produces: `et_cortex_wrap_enable_instruction_cache()`、`et_crg_wrap_prepare_uart()`、`et_crg_wrap_set_dma_clock()`、`et_crg_wrap_reset_dma()`、`et_sysctrl_wrap_configure_dma_request()`、`et_sysctrl_wrap_release_dma_request()`。
- Produces: SYSCTRL Service 继承 `0x0011`；新增 CRG Service `0x0012`，不保留多职责 System Service。

- [ ] **Step 1: Write the failing contract tests**

更新固件配置契约测试，使生成工程必须包含新增 Wrap、不得包含 DMA Manager，并要求每个 Wrap 只引用自身 Driver 家族。

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `python -m pytest pc/et_test_platform/framework_validation/unit/test_firmware_config_contract.py -q`

Expected: FAIL，因为新增 Wrap 尚不存在且旧 DMA Manager 仍在工程清单中。

- [ ] **Step 3: Implement the split and remove the dead manager**

迁移现有逻辑，并把原 System Service/Driver 拆成 SYSCTRL 与 CRG 两条单职责链；同时更新 `project.yaml` 和 Keil 模板来源。

- [ ] **Step 4: Regenerate the Keil project and verify GREEN**

Run: `python tools/firmware/generate_keil_project.py --chip et6801`

Run: `python -m pytest pc/et_test_platform/framework_validation/unit/test_firmware_config_contract.py -q`

Expected: PASS。

### Task 2: PC registry 与运行能力交集

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/drivers/framework.py`
- Create: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/profiles/runtime_capabilities.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/scheduling/fixtures.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_target_client.py`
- Create: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_runtime_capabilities.py`

**Interfaces:**
- Produces: `FrameworkDriver.discover_services()`，对 SERVICE_LIST 按固件 FNV-1a 规则复算并验证 HELLO registry hash。
- Produces: `intersect_runtime_capabilities(profile, services)`，只保留 DMA/UART 服务真实公布的实例。

- [ ] **Step 1: Write registry mismatch and intersection tests**

覆盖正确 hash、错误 hash、未知运行实例、本地存在但固件未公布实例四种行为。

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest pc/et_test_platform/framework_validation/unit/test_target_client.py pc/et_test_platform/framework_validation/unit/test_runtime_capabilities.py -q`

Expected: FAIL，因为发现和交集接口尚不存在。

- [ ] **Step 3: Implement minimal discovery and capability view**

fixture 必须在 yield Driver 之前完成 HELLO、SERVICE_LIST、hash 校验；`target_capabilities` 返回运行服务与 YAML 的交集。

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused pytest command. Expected: PASS。

### Task 3: DMA Case 归并与语义能力约束

**Files:**
- Move: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma_interrupt/transfer_done_case.py` to `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma/dma_irq_helpers.py`
- Delete: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma_interrupt/test_dma_transfer_done_interrupt.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/dma/dma_test_case_p1.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_dma_interrupt_case.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/test_cases/README.md`

**Interfaces:**
- Preserves: `execute_dma_transfer_done_interrupt()` helper behavior。
- Adds: DONE writeback Case 在硬件动作前要求 YAML `dma.feature.control_writeback` 和 `dma.parameter.control_writeback.channel_0 == true`。

- [ ] **Step 1: Write the failing semantic capability test**

验证缺少或关闭 control_writeback 时 Case 在任何 Driver 动作前 skip/拒绝。

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest pc/et_test_platform/framework_validation/unit/test_dma_interrupt_case.py -q`

Expected: FAIL，因为当前 Case 没有语义能力门控且仍依赖旧目录。

- [ ] **Step 3: Move helper, remove duplicate test, add semantic gate**

公共 Case 只描述“能力 profile 声明的硬件控制写回”，不得出现 ET6801 名称。

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the same focused pytest command. Expected: PASS。

### Task 4: 完整验证

**Files:**
- Modify only if validation exposes a regression in files already listed above.

**Interfaces:**
- Consumes: Tasks 1-3 的稳定接口。
- Produces: 单元测试、工程生成和固件编译证据。

- [ ] **Step 1: Run all PC framework unit tests**

Run: `python -m pytest pc/et_test_platform/framework_validation/unit -q`

Expected: all tests PASS。

- [ ] **Step 2: Run firmware boundary scans**

检查 Service 无 Chip Driver/寄存器访问、Wrap 无跨 IP Driver 调用、项目清单无 DMA Manager 或旧 DMA interrupt 目录引用。

- [ ] **Step 3: Build both ET6801 firmware targets**

按项目 `et-sdk-build` 工作流构建 FPGA ITCM 与 SILICON FLASH targets，要求 0 error；构建日志写入 `artifacts/`。

- [ ] **Step 4: Review the final diff against the five requested fixes**

确认 Driver 缺失 Feature 的 Wrap 规则未被扩大实现，且未触发任何硬件操作。
