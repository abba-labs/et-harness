# Framework boundary cleanup evidence

Time: 2026-08-04 10:18 CST

Scope: platform-common firmware and PC framework, using ET6801 as the current build instance. No hardware operation was performed.

## Changes validated

- System, Cortex, CRG and SYSCTRL responsibilities are separated into distinct Wraps.
- CRG Service calls CRG Wrap only; SYSCTRL Service calls SYSCTRL Wrap only.
- The unused DMA Manager is removed from Runtime and the generated Keil project.
- PC startup validates the ordered SERVICE_LIST against the HELLO registry hash.
- Generated YAML capabilities are intersected with DMA/UART instances exposed by the running firmware.
- DMA interrupt helpers are under the DMA Case directory, and DONE writeback is gated by semantic `control_writeback` capability data.

## Validation

- PC unit suite: 131 passed.
- ET6801_FPGA_ITCM: 0 errors, 0 warnings.
- ET6801_SILICON_FLASH: 0 errors, 0 warnings.
- Generated project SHA256: `C25ECE54F9484B4F2CE7174E73E7F735D91CB871C494B5750774C1FF49DD8F0D`.
- FPGA build log: `artifacts/firmware_build/20260804_101420_FPGA/keil_fpga.log`, SHA256 `20D7362EE480D3E2B03015F5AD082956FE8EA7FDEE65B798FC66937B735AED44`.
- Silicon build log: `artifacts/firmware_build/20260804_101509_SILICON/keil_silicon.log`, SHA256 `38CDE3A5163DF90CC6D644C409D21017705B51F6C232FC8408047AE7FFC4EF32`.

## Remaining risk

- No target was flashed and no UART/HIL runtime regression was run.
- The separate policy for features absent from a Chip Driver is resolved by the addendum below.

## Wrap and Test Driver boundary addendum

Time: 2026-08-04 11:30 CST

- The binding rule is recorded in `docs/design/wrap_layer_design.md`: every Wrap calls the corresponding formal Driver first and never accesses registers.
- When a required hardware Feature has no formal Driver API or valid Driver composition, a human-reviewed Test Driver may be added only at the bottom of the corresponding Driver header/source.
- Test Driver APIs use `<IP>_test<FeatureAction>` names and are guarded by `ET_ENABLE_TEST_DRIVER_EXTENSIONS`; formal SDK Driver declarations, structures and implementations remain unchanged.
- UART DMA endpoint address access moved from UART Wrap register members to isolated UART Test Driver APIs.
- Historical DMA validation additions were renamed and isolated as `AHBDMA_test*` APIs. Handshake test fields were removed from the formal DMA initialization structure and implementation.
- The redundant DMA interrupt-mask Test Driver was deleted because the formal Driver already provides enable/disable APIs; DMA Wrap now calls those formal APIs directly.
- A new static boundary test rejects register macros, register-member access and raw volatile register pointers in all Wrap sources, and validates the Test Driver guards, markers and names.

Fresh validation:

- PC framework unit suite: 133 passed.
- ET6801 FPGA firmware: 0 errors, 0 warnings; `artifacts/firmware_build/20260804_113902_FPGA/keil_fpga.log`.
- ET6801 SILICON firmware: 0 errors, 0 warnings; `artifacts/firmware_build/20260804_114007_SILICON/keil_silicon.log`.
- No hardware was flashed or executed in this addendum.

## PC Test Case comment contract addendum

Time: 2026-08-04 12:05 CST

- `docs/design/pc_layered_architecture.md` now requires every formal PC `test_*` function to place a Chinese comment block immediately before the function definition.
- The fixed headings are `测试 Feature`、`测试方法` and `通过条件`; methods and criteria use numbered items and must describe the real Case rather than a generic template.
- All 36 formal DMA P0-P3 Case functions were reviewed and converted; the existing Framework communication stress Case was converted to the same format.
- `test_pc_case_comment_contract.py` scans all formal PC Cases, rejects missing or misordered headings, requires numbered methods and pass criteria, and rejects Case docstrings used instead of the comment block.

Fresh validation:

- PC framework unit suite: 134 passed.
- DMA P0-P3 collection: 90 parameterized instances collected.
- DMA formal functions: 36; DMA compliant comment blocks: 36.
- No firmware source, hardware state or Test Case execution logic was changed.
