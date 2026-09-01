# UART Reliability Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 UART 全链路评审中已确认的可靠性与架构一致性问题，同时保持 UART Service 单 `.c` 文件、无 RTOS、无动态内存、无新通用框架。

**Architecture:** UART Service 继续保留在 `et_uart_service.c`，但按功能区域整理。每个 UART 实例只保留一个 IRQ binding 和一个 IRQ callback；Capture 与普通 IRQ 通过统一硬件掩码合并。UART 生命周期收敛到幂等 `reset_to_idle`，FIFO/DMA 配置收敛到一个状态和一个事务应用函数。PC UART 行配置使用统一语义校验，9-bit 只由独立 Feature 命令管理。

**Tech Stack:** C11 embedded firmware、Python 3.10+、pytest、GitHub Actions、Keil 工程静态边界。

## Global Constraints

- `firmware/services/src/et_uart_service.c` 不拆分为多个 `.c` 文件。
- 使用清晰的 `/********************************** ... **********************************/` 区域分隔。
- 不引入 RTOS、动态内存、事件总线、插件系统或通用状态机框架。
- Test Case 不直接构造 Wire body。
- 非法参数继续由 PC Driver unit 验证，不新增普通 UART HIL raw-frame 注入。
- 所有修改先进入 `codex/uart-review-fixes-20260805`，不得直接修改 `main`。
- 完成前必须执行 Python unit、静态契约、C native/host compile（仓库现有能力范围内）和差异 Review；未执行的 Keil/HIL 不得声称 PASS。

---

### Task 1: Control UART fixture gate

**Files:**
- Modify: `pc/et_test_platform/scheduling/fixtures.py`
- Test: `pc/et_test_platform/framework_validation/unit/test_scheduling_fixtures.py` or existing fixture test file

**Interfaces:**
- Produces: `_validate_uart_role_mapping(pair)` and test-UART-only runtime checks.

- [ ] Write a failing unit test where UART0 is the control route and only UART1/UART2 are registered; `uart_pair_config` must not skip.
- [ ] Write a failing unit test where control, DUT and Peer roles overlap; fixture must raise `ConfigurationError` before constructing handles.
- [ ] Remove the requirement that `control_instance` appear as a UART test Service.
- [ ] Keep runtime/Profile checks for DUT and Peer only.
- [ ] Run the fixture unit tests.

### Task 2: Canonical PC UART line configuration

**Files:**
- Modify: `pc/et_test_platform/drivers/uart.py`
- Modify: `pc/et_test_platform/framework_validation/unit/test_uart_driver.py`

**Interfaces:**
- Produces: one private line-config encoder used by both `initialize()` and compatibility `configure_extended()`.

- [ ] Add failing tests: 9-bit line config rejected locally; 7-bit + 1.5 stop rejected; 7-bit + two stop encodes wire value 3; 5-bit + 1.5 stop encodes wire value 2.
- [ ] Implement one strict `_encode_line_config()` path for baudrate, data bits, stop bits and parity.
- [ ] Keep `configure_extended()` as a thin compatibility forwarder without separate semantics.
- [ ] Ensure rejected values do not call `TargetClient.request()`.
- [ ] Run UART Driver unit tests.

### Task 3: Single UART IRQ owner

**Files:**
- Modify: `firmware/services/include/et_uart_service.h`
- Modify: `firmware/services/src/et_uart_service.c`
- Modify: `pc/et_test_platform/framework_validation/unit/test_uart_firmware_contract.py`

**Interfaces:**
- Produces: one `uart_irq_callback()`, one `irq_route`, one binding, `uart_apply_irq_mask()`.

- [ ] Add failing static/behavior contract assertions: no `uart_capture_irq`, no callback rebinding helper, only one `et_irq_manager_bind` path for UART runtime IRQ.
- [ ] Replace capture/event dual binding state with one binding and unified requested/applied masks.
- [ ] Make Capture add/remove only its internal RX mask while preserving PC-configured IRQ sources.
- [ ] Make TX-empty one-shot update the applied mask so explicit re-arm works.
- [ ] Organize the single `.c` file with section dividers.
- [ ] Run firmware contract tests.

### Task 4: Pure and consistent IRQ evidence

**Files:**
- Modify: `firmware/services/include/et_uart_service.h`
- Modify: `firmware/services/src/et_uart_service.c`
- Modify: `pc/et_test_platform/test_cases/uart/uart_helpers.py`
- Modify: UART IRQ Case/unit tests

**Interfaces:**
- Produces: callback-only event evidence and generation-protected IRQ snapshot.

- [ ] Add failing tests that `IRQ_STATE_GET` contains no hardware snapshot call and does not mutate event fields.
- [ ] Add failing helper test: source bit without callback-count increment must not pass an IRQ delivery Case.
- [ ] Add `result_generation` around IRQ evidence updates and a bounded consistent snapshot on GET.
- [ ] Change `_require_irq_event()` to require both positive callback delta and requested source.
- [ ] Run UART IRQ helper and contract tests.

### Task 5: Transactional/idempotent lifecycle

**Files:**
- Modify: `firmware/services/src/et_uart_service.c`
- Modify: `pc/et_test_platform/framework_validation/unit/test_uart_firmware_contract.py`

**Interfaces:**
- Produces: `uart_reset_to_idle()`/equivalent private helper; idempotent DEINITIALIZE.

- [ ] Add failing contract tests for complete validation before release and idempotent deinitialize.
- [ ] Validate all line configuration fields before destroying the old handle.
- [ ] On init route/bind failure, return to a single idle baseline.
- [ ] Make DEINITIALIZE return OK when already idle.
- [ ] Make SOFTWARE_RESET synchronize Service capture/IRQ/FIFO/DMA state without leaving stale masks.
- [ ] Run firmware contract tests.

### Task 6: Unified FIFO/DMA state

**Files:**
- Modify: `firmware/services/include/et_uart_service.h`
- Modify: `firmware/services/src/et_uart_service.c`
- Modify: related UART DMA unit/contract tests

**Interfaces:**
- Produces: one FIFO/DMA state and `uart_apply_fifo_dma_state()`.

- [ ] Add failing tests that all three commands use one helper and `DMA_ENABLE_SET` preserves thresholds.
- [ ] Route `DMA_ENABLE_SET`, `FIFO_CONFIG`, and `DMA_MODE_SET` through one transactional helper.
- [ ] Commit cached state only after both Wrap operations succeed; rollback to old state on the second-step failure.
- [ ] Keep legacy command IDs, but remove direct Service use of `et_uart_wrap_set_dma_enabled(uart_id, ...)`.
- [ ] Run UART Driver/firmware contract tests.

### Task 7: Capability gate naming and UART skip clarity

**Files:**
- Modify: `pc/et_test_platform/profiles/runtime_capabilities.py`
- Modify: `pc/et_test_platform/scheduling/fixtures.py`
- Modify: imports/tests as needed

**Interfaces:**
- Produces: clearly named instance filtering and stable skip classes/messages.

- [ ] Add tests distinguishing missing Runtime Service from missing Runtime Feature and Bench role mismatch.
- [ ] Introduce a clear `filter_profile_instances_by_registry()` name; retain the old function only as a compatibility alias if needed.
- [ ] Keep static SVD Capability, Runtime Feature and Bench reachability separate.
- [ ] Run Profile/fixture unit tests.

### Task 8: Verification and review

**Files:**
- Create: `.github/workflows/uart-review.yml` if no existing CI is present
- Update: `report/review/20260805_uart_full_chain_code_review.md`

- [ ] Run `python -m compileall pc/et_test_platform`.
- [ ] Run `python -m pytest pc/et_test_platform/framework_validation/unit -q`.
- [ ] Run any existing native C harness/host compile tests selected by the unit suite.
- [ ] Inspect the complete branch diff for state ownership, error rollback, unused fields and stale tests.
- [ ] Check GitHub Actions status for the final commit.
- [ ] Record exact commands, results, remaining Keil/HIL work and commit SHAs in the Review document.
