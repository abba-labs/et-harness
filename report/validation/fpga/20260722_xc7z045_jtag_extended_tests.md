# XC7Z045 JTAG-only 扩展硬件测试记录

时间：2026-07-22 07:22 CST

## 结论

在当前仅连接 Digilent JTAG、未连接网线/USB/外部仪器的条件下，所有已规划且安全的扩展测试均为 **PASS**。

本轮证明了：PL 可以重复易失性配置；JTAG 原始 IDCODE 与 BSCANE2 USER1 读回在 1000 轮压力下无错误；配置 SRAM 可完整、重复回读；片上 System Monitor 可经 JTAG 读取且数值处于板卡常见工作范围；Zynq PS 调试链可只读枚举 APU 和两颗 Cortex-A9；测试结束后 Fabric BIST 仍保持通过。

这些结果不等价于整颗 XC7Z045 全资源、全部外设或板级接口均已验证。

## 硬件门禁与范围

- 目标器件：XC7Z045-FFG900，芯片修订未知。
- 板卡：ET6001/ET6801 FPGA 平台板。
- 路由：Digilent JTAG。
- 人工门禁：用户在已知当前只有 JTAG、没有网线或 USB 的条件下要求“把其他能测的都测试了”。
- 允许动作：JTAG 稳定性、PL SRAM 重复配置、配置状态、System Monitor 只读、配置 SRAM 只读回读、PS/DAP 只读枚举。
- 禁止动作：配置 Flash、SD/QSPI 启动介质、OTP/NVR/fuse 写入，DDR 写测试，Cortex-A9 halt/reset，以及外部 I/O 驱动。
- 恢复路径：本轮只写 PL SRAM；板卡断电即可清除 Fabric BIST 配置。

## 输入工件

- bit：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/xc7z045_fabric_bist_audited.bit`
- bit 大小：1,545,229 bytes。
- bit SHA-256：`705E4BDDF3EF62D77AD29FA85F557B4A8EBE6D7040FB91AEA739C5E15C7931CD`
- 实现报告：`Total User IO = 0`，因此本轮 bit 不驱动 J58/J59 或其他 PL 用户 I/O。
- Fabric BIST 期望状态：`0xB101FFF0`。

## 实测结果

### 1. PL SRAM 重复配置与配置状态：PASS

- 连续执行 5 次易失性 PL 下载，5 次均完成 startup。
- 每轮均验证 XC7Z045 IDCODE、CRC error=0、PLL lock=1、EOS=1、DONE internal=1、DONE pin=1。
- 每轮均验证 IDCODE/security/over-temperature/HMAC/bad-packet error=0。
- 结果：`REPROGRAM_COUNT|5`、`REPEATED_VOLATILE_PROGRAM_PASS|1`。

### 2. JTAG/USER1 压力：PASS

- 连续 1000 轮交替读取 BSCANE2 USER1 Fabric BIST 状态和原始 JTAG IDCODE，共 2000 次数据寄存器读事务。
- 错误数：0。
- 结果：`JTAG_STRESS_ITERATIONS|1000`、`JTAG_STRESS_ERRORS|0`、`JTAG_STRESS_PASS|1`。

### 3. System Monitor/XADC JTAG 读取：PASS

- 温度：38.5 °C。
- VCCINT：0.997 V。
- VCCAUX：1.801 V。
- VCCBRAM：0.998 V。
- 结果：`SYSMON_JTAG_READ_PASS|1`。

该项只证明片上监测通路可读且数值无明显异常，不作为校准精度、电源纹波、动态压降或温度精度证明。

### 4. 配置 SRAM 完整回读一致性：PASS

- 连续生成两份完整配置回读文件，每份 13,319,476 bytes。
- 两份 SHA-256 均为 `D540A6CFE8A6599DC4CB55E2A7D95BBFDF180404DC8537C3ED651CE8DBB195C3`。
- 回读后 CRC error 保持 0，DONE pin 保持 1。
- 结果：`CONFIGURATION_READBACK_PASS|1`。

该项证明两次 JTAG 配置 SRAM 回读结果完全一致；由于当前没有与 bit 匹配的 mask 文件，不能表述为对原始压缩 bit 文件的逐位 masked verify。

### 5. Zynq PS/DAP 只读枚举：PASS

- 可见 `APU`。
- 可见 `ARM Cortex-A9 MPCore #0 (Running)`。
- 可见 `ARM Cortex-A9 MPCore #1 (Running)`。
- 可见 `xc7z045`。
- 没有选择、停止、复位或写入 CPU。
- 结果：`PS_TARGET_ENUMERATION_PASS|1`。

该项只证明 PS 调试目标可被 JTAG/DAP 发现，不证明 CPU 指令、缓存、DDR、PS 外设或启动流程正确。

### 6. 测试后 Fabric BIST 复核：PASS

- 最终读取：`FINAL_STATUS|0xB101FFF0`。
- 结果：`FABRIC_BIST_HARDWARE_PASS|1`。
- 说明上述压力、SysMon、配置回读和 PS 枚举未破坏当前 PL BIST 状态。

## 证据

- 根目录：`artifacts/fpga/xc7z045_jtag_extended/20260722_0715/hardware/`
- 重复下载：`vivado_repeat_program.log`
- JTAG 压力：`jtag_stress_1000.log`
- System Monitor：`vivado_sysmon.log`、`sysmon_values.txt`
- 配置回读：`vivado_config_readback.log`、`configuration_readback_1.bin`、`configuration_readback_2.bin`
- PS/DAP 枚举：`ps_target_enumeration.log`
- 最终 BIST：`final_fabric_bist_status.log`
- 资源守卫证据：
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_071703_96b0849f.jsonl`
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_071748_59f4dc52.jsonl`
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_071807_d25948b2.jsonl`
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_071847_78ed29cb.jsonl`
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_072130_cd3b2a59.jsonl`
  - `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_072143_feb175eb.jsonl`

## 新增测试入口

- `scripts/validation/fpga_repeat_program_fabric_bist.tcl`
- `scripts/validation/fpga_read_sysmon.tcl`
- `scripts/validation/fpga_readback_config_twice.tcl`
- `workspaces/xc7z045_fabric_bist/xsdb/stress_fabric_bist_jtag.tcl`
- `workspaces/xc7z045_fabric_bist/xsdb/enumerate_ps_targets.tcl`

## 未覆盖与剩余风险

- Fabric BIST 只抽样了 LUT、FF、内部互联、4 个 RAMB36、2 个 DSP48、MMCM/时钟/复位，不是全片资源穷举。
- 未执行 CPU 指令、缓存、DDR、PS 外设、BootROM 或启动介质功能测试。
- 未连接网线/USB，未测试以太网 PHY/MAC、USB PHY/控制器和数据链路。
- 未测试 J58/J59 或其他外部 I/O 的动态时序、驱动能力、信号完整性和电气裕量。
- 未测试 CAN、SPI、I2C、SRPWM 等协议 IP；这些需要相应 FPGA 观测 bit、DUT 固件和实际板级连线。
- 未做长时间老化、多温度、多电压、多实现 seed、掉电重启或上电启动测试。
- 当前 FPGA 仍运行易失性的 Fabric BIST；断电后配置消失。
