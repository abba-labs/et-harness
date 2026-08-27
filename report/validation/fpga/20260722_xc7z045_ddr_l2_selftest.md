# XC7Z045 PS DDR3 与 PL310 L2 硬件自检记录

时间：2026-07-22 08:57 CST

## 结论

在 ET6001/ET6801 FPGA 板的 XC7Z045-FFG900（PS silicon revision 3）上，
通过 Digilent JTAG-SMT2 完成了受控的 PS DDR3 初始化、16 KiB DDR 数据通路
测试和 PL310 L2 Cache 数据通路观测，结果为 **硬件 PASS**。

本轮证明以下受测样本有效：

- 原板 revision 3 DDRIOB、DDR PLL、DCI 和 DDRC 初始化参数可使控制器从
  Init 模式进入 Normal 模式。
- `0x3FFFC000..0x3FFFFFFF` 的 4096 个 32-bit word 可通过固定图样和
  地址相关图样读写校验。
- 同一 DDR 物理区域经 WBWA 缓存别名读取时数据一致。
- PL310 在 DDR 流量下记录到非零读请求和非零命中，补齐了此前 OCM 流量
  无法证明 L2 数据通路的问题。
- 测试窗口已恢复并完成独立读回比较；PL310 控制状态、双核运行状态和
  原 PL Fabric BIST 均已恢复或保持正常。

## 硬件范围与安全边界

- 目标：XC7Z045-FFG900，PS silicon revision 3。
- 路由：Digilent JTAG-SMT2，序列号 `210251A08870`。
- DDR 依据：原理图中的两颗 Micron `MT41K256M16TW`，以及原板
  `BOOT.bin` 内 FSBL 的 `ps7_*_init_data_3_0` 参数。
- 写入区域：仅 DDR `0x3FFFC000..0x3FFFFFFF`，共 16 KiB。
- 易失性寄存器：DDRIOB、DDR PLL、DCI clock、DDRC、PL310、SCU 和 APU
  run-control。
- 非易失性写入：无；未访问 QSPI/Flash/SD/OTP/NVR/fuse 的写路径。
- 恢复路径：自动恢复测试窗口与 PL310/APU 状态；若初始化或恢复失败，
  断电重启板卡。

DDR 初始化本身可能改变全部易失性 DRAM 的意义。测试前 DDRC 处于 Init
模式，因此脚本只能在初始化完成后备份测试窗口，并恢复到该初始化后的快照，
不能声称保留未初始化 DDR 的原始内容。测试结束后 DDRC 仍处于 Normal 模式，
断电重启可恢复到初始状态。

## 实测结果

### DDR 初始化：PASS

- `PS_SILICON_VERSION|3`
- `DDRC_MODE_BEFORE|0`
- `DDRC_MODE_AFTER_INIT|1`
- `DDRC_DLL_STATUS|0x0013F9FF`
- 四个 training slice 均返回非零训练结果。

### DDR 数据通路：PASS

- 测试长度：`4096` word，即 16 KiB。
- 固定图样：`0x00000000`、`0xFFFFFFFF`、`0xAAAAAAAA`、`0x55555555`。
- 地址相关图样：`(index * 0x9E3779B9) ^ 0xA5A55A5A`。
- CPU 状态：`0x50415330`。
- 失败掩码：`0x00000000`。
- 非缓存校验和：`0x4271B800`。
- WBWA 别名校验和：`0x4271B800`。
- 首值：`0xA5A55A5A`；末值：`0x7CC14C1D`。

### PL310 L2 数据通路：PASS

- Data read requests：`0x000002E0`（736）。
- Data read hits：`0x000000E0`（224）。
- L2 control 测试前/恢复后：`0x00000000`。
- L2 auxiliary control 测试前/恢复后：`0x02060000`。

### 恢复与收尾：PASS

- 初始化后测试窗口备份：16384 bytes。
- 恢复后独立读回：16384 bytes。
- 两文件 SHA-256 均为
  `3422FADA9BBCAEB3C6D9F2285DC0A79B7843BE127255DD3A683D3D2D7092D596`。
- Cortex-A9 #0：`Running`。
- Cortex-A9 #1：`Running`。
- PL Fabric BIST：`0xB101FFF0`，`FABRIC_BIST_HARDWARE_PASS|1`。

## 实现与证据

- 固件：`workspaces/xc7z045_ps_selftest/src/ps_selftest.c`
- XSDB 执行器：`workspaces/xc7z045_ps_selftest/xsdb/run_ddr_l2_selftest.tcl`
- 受保护入口：`scripts/validation/run_xc7z045_ddr_l2_selftest.ps1`
- 证据目录：`artifacts/fpga/xc7z045_ddr_l2_selftest/20260722_085632/`
- 主硬件日志 SHA-256：
  `CF3876C5F4F245B17B5F7AC7A6BE1BC0D8BE606223898FBBACAAB92A71A13854`
- 最终 BIST 日志 SHA-256：
  `FA74D1C9776A2CD3DE00EC61023353FE2CE1F6EA0E4465B8EB713D694C4F8AC4`

## 限制与下一步

- 只测试了 1 GiB 地址空间中的 16 KiB 窗口，不是全容量 DDR 测试。
- 未做长时间 March、随机压力、DMA/HP/ACP 多主机并发或双核 DDR 一致性测试。
- 未做不同 DDR 频率、电压、温度和多板统计。
- 未测试 PS 外设、启动介质、Ethernet、USB 或外部 IO 电气特性。
- 本结果证明当前板卡的受测 DDR/L2 数字数据通路，不代表模拟或信号完整性指标。
