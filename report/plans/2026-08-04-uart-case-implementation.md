# UART Case Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for each task. The current formal code tree is largely untracked, so work in the shared project tree, do not create commits, and never discard unrelated user files.

**Goal:** Implement the ET6801 UART firmware command surface and the PC-side P0-P3 Case set defined by `Et_Automated_Testing_Platform_Code/test_case_doc/UART.md`, with one profile-selected DUT and an optional stimulus-only Peer.

**Architecture:** Bench profiles resolve logical Control/DUT/Peer roles into `UartDriver` handles. PC Cases compose atomic UART, DMA and CRG operations; firmware UART Service only parses commands, calls UART Wrap and records UART events; UART Wrap only calls ET6x UART Driver APIs. P3 Cases that need unavailable board wiring, instruments or design contracts remain fully described deferred functions and are not collected.

**Tech Stack:** Python 3, pytest, PyYAML, ET-Frame v1, C11/CMSIS, ET6x UART Driver, Keil uVision ARM Compiler 6.

## Global Constraints

- UART0 is the PC control channel and must never be reset or used as the functional DUT.
- Current bench mapping is Control=0, DUT=1, Peer=2; Case source must not contain these numbers as instance selections.
- Every runtime Feature verdict belongs to `uart_dut_handle`; `uart_peer_handle` only supplies stimulus or observation.
- UART Service may call UART Wrap and the common IRQ Manager only; it must not call GPIO, CRG, DMA or another IP Wrap.
- UART Wrap may call only UART Driver APIs and must not read or write registers directly.
- Missing UART Driver APIs are added only in the isolated `ET_ENABLE_TEST_DRIVER_EXTENSIONS` section with `UART_test...` names.
- PC Case comments use Chinese `测试 Feature / 测试方法 / 通过条件` blocks before each function.
- P0=8, P1=13, P2=9 and P3=8 Case definitions; current evidence-backed collection is P0=8, P1=12, P2=6 and P3=0. The remaining 12 definitions are explicit deferred functions, not weakly asserted tests.
- No hardware programming, flash erase, reset or UART traffic is performed by this implementation plan.

---

### Task 1: UART logical roles and pytest handles

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/profiles/bench.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/scheduling/fixtures.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_bench_config.py`
- Create: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_uart_fixtures.py`

**Interfaces:**
- Produce `UartPairConfig(control_instance: int, dut_instance: int, peer_instance: int | None)`.
- Produce `load_uart_pair(profile_path, target_id, environment=None) -> UartPairConfig`.
- Produce fixtures `uart_pair_config`, `uart_dut_handle`, and `uart_peer_handle`.

- [x] Write failing tests proving strict role parsing, role uniqueness, DUT/Peer handle instance propagation and optional-Peer behavior.
- [x] Run the two focused unit files and confirm failures are caused by missing UART role APIs.
- [x] Implement the immutable profile object, parser and fixtures without modifying DMA-specific pair behavior.
- [x] Run the two focused unit files and the existing bench tests to green.

### Task 2: UART atomic firmware/PC command contract

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/drivers/uart.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_uart_driver.py`
- Modify: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_firmware_driver_boundary.py`
- Create: `Et_Automated_Testing_Platform_Code/pc/et_test_platform/framework_validation/unit/test_uart_firmware_contract.py`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/services/include/et_uart_service.h`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/services/src/et_uart_service.c`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/wrap/include/et_uart_wrap.h`
- Modify: `Et_Automated_Testing_Platform_Code/firmware/wrap/src/et_uart_wrap.c`
- Modify only when an official API is absent: `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_uart.h` and `Src/et6x_uart.c`.

**Interfaces:**
- Preserve command IDs `0x0001..0x000B`.
- Add explicit commands for `SNAPSHOT_GET`, `SOFTWARE_RESET`, `LOOPBACK_SET`, `FIFO_CONFIG`, `STATUS_GET`, `IRQ_CONFIG`, `IRQ_STATE_GET`, `BREAK_SET`, `HALT_SET`, `DMA_MODE_SET`, `NINE_BIT_CONFIG`, `WRITE_9BIT`, `READ_9BIT`, `FLOW_CONTROL_SET`, `MODEM_CONTROL_SET`, and `MODEM_STATUS_GET` starting at `0x000C` in that order.
- Add PC immutable results `UartSnapshot`, `UartStatus`, `UartIrqState`, and `UartModemStatus`.
- Extend line configuration with stop selections `ONE`, `ONE_AND_HALF`, `TWO` and parity `NONE`, `EVEN`, `ODD`, `STICK_ZERO`, `STICK_ONE` while preserving the legacy `initialize()` wire command.

- [x] Write failing fake-Target tests for every new PC payload, response length, invalid enum/range and `instance_id` propagation.
- [x] Write failing firmware boundary tests that require matching command IDs, Service-to-Wrap calls, no UART register access in Wrap, and isolated Test Driver extensions.
- [x] Run focused PC tests and confirm expected missing-symbol/contract failures.
- [x] Add official-Driver-backed Wrap APIs and isolated `UART_test...` helpers only where the official Driver lacked an API.
- [x] Implement Service parsing, bounded responses, IRQ event counters and cleanup; do not add complete test scenarios to firmware.
- [x] Implement matching PC methods and strict decoding.
- [x] Run focused unit/boundary tests to green and compile both Keil targets.

### Task 3: P0 and P1 UART Cases

**Files:**
- Create: `pc/et_test_platform/test_cases/uart/__init__.py`
- Create: `pc/et_test_platform/test_cases/uart/uart_helpers.py`
- Create: `pc/et_test_platform/test_cases/uart/uart_test_case_p0.py`
- Create: `pc/et_test_platform/test_cases/uart/uart_test_case_p1.py`
- Create: `pc/et_test_platform/framework_validation/unit/test_uart_cases_contract.py`

**Interfaces:**
- `uart_helpers.py` provides bounded initialization, pair transfer, loopback transfer, cleanup, capture wait and result recording helpers; helpers receive handles and never construct `UartDriver`.
- P0 exposes exactly 8 collected `test_uart_p0_...` functions.
- P1 defines 13 Cases; 12 are collected and busy-detect remains an explicit deferred function until a deterministic safe trigger exists.

- [x] Write an AST/collection contract test for all definitions, Chinese comment blocks, required fixtures, and no hardcoded instance construction.
- [x] Implement P0 Cases from UART.md using literal input matrices and independent expected data.
- [x] Implement P1 evidence-backed Cases using UART IRQ/state commands; use Peer only for deterministic parity/framing/break stimulus.
- [x] Ensure every collected Case has bounded cleanup and writes structured PASS evidence.
- [x] Run focused fake-driver helper tests, AST contract and pytest collection to green.

### Task 4: P2 Cases and P3 deferred definitions

**Files:**
- Create: `pc/et_test_platform/test_cases/uart/uart_test_case_p2.py`
- Create: `pc/et_test_platform/test_cases/uart/uart_test_case_p3.py`
- Modify: `pc/et_test_platform/framework_validation/unit/test_uart_cases_contract.py`
- Modify: `pc/et_test_platform/pytest_plugin.py`

**Interfaces:**
- P2 defines 9 Cases: 6 collected functions and 3 `_deferred_uart_p2_...` functions for true simultaneous full-duplex DMA, missing flow-control wiring and missing modem wiring.
- P3 contains exactly 8 `_deferred_uart_p3_...` functions and none are collected.
- DMA Cases compose `DmaDriver`, `ResourceDriver`, `SysctrlDriver` and UART handles at PC level; UART Service never calls DMA APIs.

- [x] Extend the contract test and observe failures for absent P2/P3 definitions and markers.
- [x] Implement evidence-backed P2 DMA TX/RX, 9-bit software/address, clock-reset recovery and 1000-round mixed transfer; keep true simultaneous full-duplex, flow and modem deferred.
- [x] Implement all eight P3 method bodies using stable UART/instrument interfaces, but prefix them `_deferred_` until their board/design prerequisites exist.
- [x] Register the `uart` marker and validate collected/deferred counts.
- [x] Run UART Case collection and unit contracts to green.

### Task 5: Full non-hardware validation and records

**Files:**
- Update: `project-control/work/ACTIVE.md`
- Create: ET skill usage notice under `D:/lihuan/vibe_code/ai_toolbox/et-ai-skill-package/notice/`
- Generated: `project-control/context/PROJECT_STATE.json`

- [x] Run Python syntax/import checks and the complete framework unit suite.
- [x] Run UART P0/P1/P2/P3 collect-only and verify exact collected/deferred counts.
- [x] Regenerate the Keil project from `firmware/chips/et6801/project.yaml`.
- [x] Build `ET6801_FPGA_ITCM` and `ET6801_SILICON_FLASH` through the guarded build entrypoint; require zero errors and zero warnings.
- [x] Run source boundary scans for Service/Wrap/Driver layering and protocol ID parity.
- [x] Record commands, outputs and remaining HIL-only risks; refresh context and rerun Quick Doctor.
