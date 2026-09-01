# XC7Z045 FPGA Fabric 必测项验证记录

时间：2026-07-21 19:27 CST

硬件完成时间：2026-07-21 21:43 CST

## 范围与安全边界

- 目标：XC7Z045-FFG900，速度等级按接口资料暂取 `-2`，芯片修订未知。
- 板卡：ET6001/ET6801 平台；链路：Digilent JTAG。
- 测试通道：FPGA/HIL。
- 本轮内部必测项：配置/JTAG链路、时钟与复位、LUT/FF/内部互联、Block RAM、DSP48。
- 本设计没有顶层用户 IO，不使用外部仪器，不写配置 Flash、PS 启动介质、OTP、NVR 或熔丝。
- 计划中的硬件下载仅为 PL SRAM 易失性配置；断电可清除。

## 自检设计

- 时钟/复位：`STARTUPE2.CFGMCLK` 经 BUFG 和 MMCM 产生测试时钟；检查 EOS、MMCM LOCKED、复位释放和配置时钟活动。
- 逻辑资源：32-bit LFSR 与 256-bit one-hot 寄存器环运行 4096 周期，验证 LUT、FF 和内部路由参与工作。
- BRAM：128-bit × 1024 的块 RAM 写入并逐地址回读确定性图样，综合后要求至少保留 4 个 RAMB36。
- DSP：25 × 18 乘法加 48-bit 加数，与禁止 DSP 推断的移位加法参考实现连续对拍 1024 组向量。
- 结果读取：通过 `BSCANE2 USER1` 暴露 32-bit 状态；完全通过值为 `0xB101FFF0`。

## 已执行验证

1. Vivado xsim 行为仿真：PASS。
   - `logic=1`、`bram=1`、`dsp=1`
   - 标志：`FABRIC_BIST_SIM_PASS|1`
2. 器件数据库与许可证：PASS。
   - `get_parts xc7z045ffg900-2` 返回 `xc7z045ffg900-2`。
   - 2026-07-21 21:10 CST 下载的 60 天 Vivado Enterprise Evaluation 许可证已安装到当前 Windows 用户的 Xilinx 许可证目录；综合和实现均成功检出许可证。
   - 早先的“缺少 XC7Z045 器件数据库”和“Synthesis/xc7z045 无许可证”阻断均已解除。
3. 综合资源检查：PASS。
   - `SYNTH_STATUS|synth_design Complete!`
   - `DSP48=2`、`RAMB36=4`、`LUT=1602`、`FF=582`
4. 布局布线与最终审核：PASS。
   - 受项目单进程 2048 MB 内存上限约束，采用“综合/布局、独立快速布线、独立单线程 bitgen”的分段流程，未放宽资源策略。
   - 最终审核：setup WNS `+7.329 ns`，hold WHS `+0.048 ns`。
   - 未约束内部端点 `0`，报告结论为 `All user specified timing constraints are met.`。
   - `FATAL_DRC_COUNT|0`、`CRITICAL_METHODOLOGY_COUNT|0`、`FABRIC_BIST_AUDIT_PASS|1`。
5. 最终 bit 生成与外部 IO 安全检查：PASS。
   - bitgen：0 error、0 warning、0 critical warning，`FABRIC_BIST_BITSTREAM_PASS|1`。
   - 文件大小：`1,545,229` bytes。
   - SHA-256：`705E4BDDF3EF62D77AD29FA85F557B4A8EBE6D7040FB91AEA739C5E15C7931CD`。
   - 布局后 `report_io`：`Total User IO = 0`，该 bit 不驱动 J58/J59 或其他 PL 用户引脚。
6. 2026-07-21 21:41 CST，XC7Z045 PL SRAM 易失性下载：PASS。
   - Digilent JTAG 目标中恰好识别到一个 `xc7z045`。
   - 下载前 DONE=0；下载后 startup status=HIGH，刷新后 Vivado 确认器件已配置。
   - 标志：`VOLATILE_SRAM_PROGRAM_PASS|1`。
   - 未写配置 Flash、PS 启动介质、OTP、NVR 或熔丝。
7. 片上 BIST 两次独立读取：PASS。
   - 第一次：`FINAL_STATUS|0xB101FFF0`，`FABRIC_BIST_HARDWARE_PASS|1`。
   - 第二次：`FINAL_STATUS|0xB101FFF0`，`FABRIC_BIST_HARDWARE_PASS|1`。
   - 两次均在第 0 次轮询得到完成状态。
8. 下载后的 JTAG IDCODE 复查：PASS。
   - 捕获值与 XC7Z045 期望的 LSB-first IDCODE 完全一致。
   - 标志：`RAW_JTAG_IDCODE_PASS|1`。

## 当前结论

XC7Z045 本轮内部 FPGA Fabric 必测项判定为 **硬件 PASS**。证据覆盖：JTAG 识别与易失性配置、配置启动/EOS、CFGMCLK 活动、MMCM 锁定与复位释放、LUT/FF/内部路由样本、4 个 RAMB36 和 2 条 DSP48 推断路径。两次片上状态均为完整通过值 `0xB101FFF0`，下载后的原始 JTAG IDCODE 仍正常。

本结论不等价于“整颗 FPGA 所有资源全部无故障”。本轮没有覆盖全部 LUT/FF/BRAM/DSP、所有时钟资源、PS/DDR、GT 收发器、模拟/电气性能，也没有重复测试此前已通过的 J58/J59 外部 IO 回环。速度等级仍按接口资料使用 `-2`，芯片修订未知。

## 后续条件

- 当前 Enterprise Evaluation 许可证为 60 天试用；试用到期后，重新综合/实现 XC7Z045 需要继续使用覆盖该器件的有效许可证。已生成的 `.bit` 不因许可证到期而失效。
- 如需扩大覆盖率，可再做多 seed、多温度/电压、更多 BRAM/DSP/LUT 分区、PS/DDR、GT 和板级时钟专项测试；这些属于后续扩展，不影响本轮必测项 PASS。

## 证据

- RTL：`workspaces/xc7z045_fabric_bist/rtl/xc7z045_fabric_bist.v`
- testbench：`workspaces/xc7z045_fabric_bist/sim/tb_fabric_bist.v`
- 约束：`workspaces/xc7z045_fabric_bist/constraints/xc7z045_fabric_bist.xdc`
- 构建脚本：`scripts/validation/fpga_build_fabric_bist.tcl`
- 独立布线脚本：`scripts/validation/fpga_route_fabric_bist_from_checkpoint.tcl`
- 审核脚本：`scripts/validation/fpga_audit_fabric_bist_routed.tcl`
- bit 生成脚本：`scripts/validation/fpga_write_fabric_bist_bitstream.tcl`
- 下载脚本：`scripts/validation/fpga_program_fabric_bist.tcl`
- 状态读取脚本：`workspaces/xc7z045_fabric_bist/xsdb/read_fabric_bist_status.tcl`
- 仿真日志：`artifacts/fpga/xc7z045_fabric_bist/20260721_192407/xsim.log`
- 综合/布局日志：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/vivado_build.log`
- 最终审核日志：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/vivado_audit.log`
- 审核后时序报告：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/timing_summary_audited.rpt`
- 审核后方法学报告：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/methodology_audited.rpt`
- 审核后 DRC 报告：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/drc_audited.rpt`
- 最终 bit：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/xc7z045_fabric_bist_audited.bit`
- 外部 IO 报告：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/vivado_project/xc7z045_fabric_bist.runs/impl_1/xc7z045_fabric_bist_io_placed.rpt`
- 下载日志：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/hardware/vivado_program.log`
- 第一次状态读取：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/hardware/bist_status_read1.log`
- 第二次状态读取：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/hardware/bist_status_read2.log`
- 下载后 IDCODE：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/hardware/jtag_idcode_after_bist.log`
- 最终 bitgen 资源守卫记录：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260721_213759_22609402.jsonl`
- 下载资源守卫记录：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260721_214117_efef075d.jsonl`
- 两次状态读取资源守卫记录：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260721_214251_492c0c3a.jsonl`、`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260721_214307_e4da5123.jsonl`
- 下载后 IDCODE 资源守卫记录：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260721_214340_96d719a3.jsonl`
