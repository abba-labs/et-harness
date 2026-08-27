# Xilinx JTAG scripts

This directory contains reusable Vivado and XSDB helpers for the platform's
two-FPGA JTAG topology. Temporary experiments must not be added here.

## Stable roles

| Role | Current device | Default hw_server URL | Responsibility |
| --- | --- | --- | --- |
| `observer` | XC7Z045 | `tcp:127.0.0.1:3121` | Test stimulus, capture, buffering, and PC transport |
| `dut` | XC7VX980T | `tcp:127.0.0.1:3122` | FPGA prototype of the device under test |

The role names are stable even when a future board uses a different FPGA.
Callers must verify the discovered part after connecting and must not select a
target only by list index.

The two current Digilent adapters advertise the same logical serial number.
One Vivado Hardware Manager can therefore expose only one adapter. The proven
workaround is to keep two independent `hw_server` processes and address them by
their TCP ports.

## Layout and naming

```text
xilinx_jtag/
  README.md
  powershell/
    invoke_xilinx_jtag_scan.ps1
  tcl/
    vivado_list_hw_targets.tcl
    vivado_scan_hw_devices.tcl
    xsdb_list_jtag_targets.tcl
    xsdb_verify_dual_fpga_jtag.tcl
```

Names follow `<tool>_<action>_<object>.<ext>`:

- `vivado_*` uses Vivado LabTools commands.
- `xsdb_*` uses XSDB/TCF commands.
- `list`, `scan`, and `verify` are read-only discovery actions.
- Future `program`, `reset`, or run-control actions require an explicit hardware
  gate and must not be hidden inside discovery scripts.

## Read-only examples

List the observer chain:

```powershell
& "D:\Software\Xilinx\Vivado\2024.2\bin\xsdb.bat" `
  ".\Et_Automated_Testing_Platform_Code\tools\fpga\xilinx_jtag\tcl\xsdb_list_jtag_targets.tcl" `
  "tcp:127.0.0.1:3121" "observer"
```

Verify both independently served chains:

```powershell
& "D:\Software\Xilinx\Vivado\2024.2\bin\xsdb.bat" `
  ".\Et_Automated_Testing_Platform_Code\tools\fpga\xilinx_jtag\tcl\xsdb_verify_dual_fpga_jtag.tcl"
```

Run a temporary Vivado scan on a selected free port:

```powershell
& ".\Et_Automated_Testing_Platform_Code\tools\fpga\xilinx_jtag\powershell\invoke_xilinx_jtag_scan.ps1" `
  -ServerPort 3122
```

The PowerShell wrapper writes its process logs under
`artifacts/fpga/xilinx_jtag/`; it does not program or reset either FPGA.
