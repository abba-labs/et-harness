# XC7Z045 DDR 1 GiB 地址空间抽样与防镜像测试

时间：2026-07-22 14:44 CST

## 结论

在 ET6001/ET6801 FPGA 板的 XC7Z045-FFG900（PS silicon revision 3）上，
通过 Digilent JTAG-SMT2 对标称 `0x00000000..0x3FFFFFFF` 的 1 GiB DDR3
地址空间完成了受控抽样写入、防镜像检查和恢复验证，结果为 **硬件 PASS**。

- DDRC 在测试前处于 Normal 模式。
- 每隔 128 MiB 选择一个 4 KiB 窗口，共 8 个窗口、总计 32 KiB。
- 8 个窗口全部完成备份、唯一地址相关图样写入和延后统一回读。
- 8 个回读 CRC32 各不相同，所有内容均与各自期望文件一致，未发现高地址镜像到低地址。
- 测试结束后 8 个窗口全部恢复，独立 SHA-256 比较确认恢复内容与备份一致。
- Cortex-A9 #0/#1 均恢复为 Running。
- 最终 PL Fabric BIST 状态为 `0xB101FFF0`，结果 PASS。

本结果证明当前样板的 1 GiB DDR 地址范围在抽样边界上可寻址、互不镜像，且受测
窗口可实际读写，可作为后续大容量波形缓存设计的硬件依据。

## 测试范围与安全边界

- 目标：XC7Z045-FFG900，PS silicon revision 3。
- 路由：Digilent JTAG-SMT2，15 MHz。
- 受测窗口：
  - `0x07FFF000..0x07FFFFFF`
  - `0x0FFFF000..0x0FFFFFFF`
  - `0x17FFF000..0x17FFFFFF`
  - `0x1FFFF000..0x1FFFFFFF`
  - `0x27FFF000..0x27FFFFFF`
  - `0x2FFFF000..0x2FFFFFFF`
  - `0x37FFF000..0x37FFFFFF`
  - `0x3FFFF000..0x3FFFFFFF`
- 每个窗口 4 KiB，总临时写入量 32 KiB。
- 只写易失性 DDR；未访问 Flash、QSPI、SD、OTP、NVR 或熔丝写路径。
- 写入前备份所有窗口，写入后逐窗口恢复并独立回读验证。
- 异常恢复路径：断电重启板卡。

## 实测结果

| 窗口 | 基地址 | 测试 CRC32 | 写入/回读 | 恢复 |
|---:|---:|---:|---|---|
| 0 | `0x07FFF000` | `0x95BA3665` | PASS | PASS |
| 1 | `0x0FFFF000` | `0xDFAB5CD4` | PASS | PASS |
| 2 | `0x17FFF000` | `0xA747647C` | PASS | PASS |
| 3 | `0x1FFFF000` | `0x4B8989B6` | PASS | PASS |
| 4 | `0x27FFF000` | `0xBB466E75` | PASS | PASS |
| 5 | `0x2FFFF000` | `0xBA51F8E6` | PASS | PASS |
| 6 | `0x37FFF000` | `0x2E32D34C` | PASS | PASS |
| 7 | `0x3FFFF000` | `0xB8BD2533` | PASS | PASS |

关键判据：

- `DDR_ALIAS_CHECK_PASS|1`
- `DDR_WINDOWS_RESTORE_PASS|1`
- `DDR_CAPACITY_SMOKE_PASS|1`
- `APU_RESTORE_RESET_START|1`
- `FABRIC_BIST_HARDWARE_PASS|1`
- `XC7Z045_DDR_CAPACITY_VALIDATION_PASS|1`

## 实现与证据

- 受保护入口：`scripts/validation/run_xc7z045_ddr_capacity_smoke.ps1`
- XSDB 执行器：`workspaces/xc7z045_ps_selftest/xsdb/run_ddr_capacity_smoke.tcl`
- 证据目录：`artifacts/fpga/xc7z045_ddr_capacity_smoke/20260722_144355/`
- 主硬件日志 SHA-256：
  `1DE02CD0E938885FCE497DC9BC374FCDA4118D96258BF1662C11202024BC12EA`
- 最终 BIST 日志 SHA-256：
  `296FA62793F65BD9BFCE63CB223B819AB00B0EE12337071AF1645C44BA672104`

## 限制与下一步

- 这是跨 1 GiB 地址空间的抽样和防镜像测试，不是逐字节全容量 March 测试。
- 未覆盖未抽样单元的永久故障、保持故障或相邻单元耦合故障。
- 未做长时间随机压力、DMA/HP/ACP 多主机并发、不同温度/电压/频率或多板统计。
- 本次证明硬件容量与抽样数据通路；正式波形缓存仍需在板级配置中分配不与程序、
  栈、控制邮箱冲突的连续 DDR 保留区。
