# UART Testable Cases and HIL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Every production change follows RED-GREEN-REFACTOR.

**Goal:** Turn every UART Feature that is testable with the current ET6801 prototype into an evidence-backed collected Case, then program the firmware to PFLASH and execute the UART HIL set.

**Architecture:** PC Cases keep all scenario composition. UART Service parses only UART commands, UART Wrap calls only UART Driver, and missing register-level primitives live only in the isolated `UART_test...` Driver extension section. Bench and capability data decide whether a Case executes; missing hardware is documented as `blocked_by_board`, never converted into PASS.

**Tech Stack:** Python 3, pytest, ET-Frame v1, C11/CMSIS, ET6x UART Driver, Keil ARM Compiler 6, Keil ET6801.FLM, J-Link, Vivado, COM12.

## Global Constraints

- Control UART0 is never reconfigured by a functional Case.
- Functional DUT/Peer handles come only from the bench profile; current physical pair is UART1 TX/RX crossed with UART2 RX/TX.
- No Service may call another IP Wrap; DMA full-duplex composition remains in the PC Case.
- UART Wrap never accesses registers directly.
- New register primitives use `UART_test...` names inside `ET_ENABLE_TEST_DRIVER_EXTENSIONS` only.
- Every HIL operation is bounded and records artifacts; PFLASH erase/program is destructive but OTP/NVR/fuses are not touched.
- Current testability target is 31 collected Cases: P0=8, P1=13, P2=9, P3=1. Seven P3 Cases remain board/design blocked.

---

### Task 1: Busy Detect atomic evidence

**Files:**
- Modify: `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_uart.h`
- Modify: `firmware/chips/et6801/sdk/ET6x_Driver/Src/et6x_uart.c`
- Modify: `firmware/wrap/include/et_uart_wrap.h`
- Modify: `firmware/wrap/src/et_uart_wrap.c`
- Modify: `firmware/services/include/et_uart_service.h`
- Modify: `firmware/services/src/et_uart_service.c`
- Modify: `pc/et_test_platform/drivers/uart.py`
- Modify: `pc/et_test_platform/test_cases/uart/uart_test_case_p1.py`
- Test: UART Driver/Wrap/Service/Case contract unit files.

**Interfaces:**
- Add `UART_testTriggerBusyDetect()` returning bounded pre-trigger USR, observed IIR/USR, trigger count and recovery state.
- Add one Wrap method and one UART Service command; Service does not reproduce the trigger sequence.
- Add `UartDriver.busy_detect_trigger()` and collect `test_uart_p1_012_busy_detect_irq`.

- [ ] Write failing wire, firmware-boundary and collection tests for the new result and Case.
- [ ] Run the focused tests and confirm failure is caused by the missing command/API.
- [ ] Implement a bounded no-FIFO busy trigger on DUT only: disable/reset FIFO, start one transmit byte, wait for USR.BUSY, write LCR through the Driver, observe Busy Detect, clear by the documented USR read, restore FIFO and wait idle.
- [ ] Assert one Busy Detect event, bounded clear and a successful post-recovery loopback frame.
- [ ] Run focused tests and both firmware syntax/build checks.

### Task 2: True overlapping UART DMA directions

**Files:**
- Modify: `pc/et_test_platform/test_cases/uart/uart_test_case_p2.py`
- Modify: `pc/et_test_platform/framework_validation/unit/test_uart_cases_contract.py`

**Interfaces:**
- Replace `_deferred_uart_p2_003_dma_full_duplex` with collected `test_uart_p2_003_dma_full_duplex`.
- Reuse `DmaDriver.start_channels(tx_mask | rx_mask)`; no UART or DMA firmware composite command.

- [ ] Write a failing Case contract requiring P2-003 collection and two distinct DMA channels/interfaces.
- [ ] Configure DUT TX M2P and DUT RX P2M, arm Peer capture, use a low functional baudrate and long literal patterns, atomically start both DMA channels, and verify both channels are active before Peer transmit begins.
- [ ] Send the reverse Peer pattern while DUT TX remains active; wait for both TFR completions.
- [ ] Compare Peer capture and DUT RX resource buffer independently, including guard regions and cleanup.
- [ ] Run focused unit and collection tests.

### Task 3: Internal-loopback modem and auto-flow coverage

**Files:**
- Modify: `pc/et_test_platform/test_cases/uart/uart_test_case_p2.py`
- Modify only if partial nonblocking TX is required: UART Driver/Wrap/Service/PC Driver and their contract tests.

**Interfaces:**
- Collect P2-006 and P2-007.
- P2-007 covers RTS->CTS and DTR->DSR current/delta states; RI/DCD remain explicitly blocked by missing stimulus.
- P2-006 uses FIFO-enabled internal loopback and AFCE. If existing synchronous write cannot expose pause/resume, add one atomic `WRITE_PARTIAL` command backed by official nonblocking `UART_transmit`.

- [ ] Write failing modem and flow Case contracts.
- [ ] Implement modem transition checks with immediate `MODEM_STATUS_GET` reads and a second read proving delta clear; do not call generic STATUS between transition and modem read.
- [ ] Implement flow pause/resume using bounded partial writes and RX FIFO draining; require complete final echo with no loss.
- [ ] Record RI/DCD as `blocked_by_board`, not PASS.
- [ ] Run focused unit/collection tests.

### Task 4: Shadow and direct FIFO access

**Files:**
- Modify: ET6x UART Driver extension, UART Wrap, UART Service, PC UART Driver.
- Modify: `pc/et_test_platform/test_cases/uart/uart_test_case_p3.py`
- Modify: UART contract unit files.

**Interfaces:**
- Add capability-gated `UART_test...` primitives for SFE/SRT/STET, FAR, TFR and RFW.
- Add stable Wrap/Service/PC operations for shadow configuration, FIFO-access enable, RX injection and TX inspection.
- Collect `test_uart_p3_007_shadow_and_direct_fifo_access` only when runtime CPR reports SHADOW/FIFO_ACCESS support.

- [ ] Write failing capability, wire and collection contracts.
- [ ] Implement Driver primitives with instance/capability validation and bounded restoration.
- [ ] Verify shadow readback and normal FIFO threshold behavior.
- [ ] Halt TX, enqueue a literal byte, inspect it through TFR; inject a literal byte through RFW and receive it through the normal data path.
- [ ] Restore FAR=0, reset FIFO, reinitialize and require a normal loopback frame.
- [ ] Run focused unit/collection tests and both Keil builds.

### Task 5: Document the actual execution boundary

**Files:**
- Modify: `Et_Automated_Testing_Platform_Code/test_case_doc/UART.md`
- Modify: `project-control/work/ACTIVE.md`

- [ ] Record 31 collected Cases and seven blocked Cases.
- [ ] State concrete reasons: three RS485 Cases need transceiver/DE/RE, two SIR Cases need an SIR path, absolute baud timing needs an independent observer, and protection/timeout needs a safe fault/recovery contract.
- [ ] Record that RI/DCD are not covered by the modem internal-loopback Case.

### Task 6: Non-hardware verification

- [ ] Run all UART contracts and collect-only; require P0=8, P1=13, P2=9, P3=1.
- [ ] Run the complete framework unit suite with no cache files in the formal code root.
- [ ] Regenerate and build `ET6801_FPGA_ITCM` and `ET6801_SILICON_FLASH`; require 0 errors and 0 warnings.
- [ ] Scan boundaries: Service only UART Wrap/IRQ Manager; Wrap only UART Driver; Case no chip/instance/pin hardcoding.

### Task 7: PFLASH HIL execution

**Hardware gate:** User explicitly requested hardware execution on 2026-08-04. Target is ET6801 CORE0 in the XC7VX980T prototype; UART route is COM12 control plus UART1<->UART2 TX/RX. The operation reconfigures the volatile FPGA, loads BootROM to prototype RAM, erases/programs/verifies PFLASH0 `0x08000000..0x0807FFFF`, and does not touch OTP/NVR/fuses.

**Recovery:** Reconfigure the known bitstream, reload BootROM, reflash the previous known-good image, or power-cycle the prototype.

**Artifacts:** `artifacts/uart_hil/<timestamp>/` plus existing bit/BootROM/flash script artifacts.

- [ ] Verify COM12 and exactly one intended J-Link route; stop if identity is ambiguous.
- [ ] Program the known XC7VX980T bitstream and load BootROM to `0x20500000`, proving `main` is reached.
- [ ] Program/verify the current Silicon Flash target and direct-vector run it.
- [ ] Require HELLO chip/build/service registry match before running UART Cases.
- [ ] Execute P0, then P1, P2 and P3-007 in increasing risk order; stop the current level on the first unrecovered failure.
- [ ] Save JUnit, per-Case JSON, console, flash and recovery evidence.
- [ ] Update `UART.md` with executed/pass/fail/blocked results; never infer hardware PASS from compilation.
