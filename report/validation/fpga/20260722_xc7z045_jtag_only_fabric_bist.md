# XC7Z045 JTAG-only Fabric BIST 硬件复测记录

时间：2026-07-22 06:53 CST

## 结论

XC7Z045 本轮 JTAG-only 数字 Fabric 必测项判定为 **硬件 PASS**。

本次证据来自 2026-07-22 的真实硬件重新下载和重新读回，不复用 2026-07-21 的硬件 PASS 日志作为本轮结论。

## 硬件门禁与范围

- 目标器件：XC7Z045-FFG900，芯片修订未知。
- 板卡：ET6001/ET6801 FPGA 平台板。
- 路由：Digilent JTAG。
- 用户确认：用户在已说明目标、命令类型、预期结果、恢复路径、日志路径及非破坏性边界后回复“开始做”。
- 写入类型：仅 PL SRAM 易失性配置。
- 破坏性：否；未写配置 Flash、PS 启动介质、OTP、NVR 或熔丝。
- 恢复路径：板卡断电即可清除本次 PL 配置。
- 外部 I/O：被下载 bit 的实现报告为 `Total User IO = 0`，未驱动 J58/J59 或其他 PL 用户引脚。

## 被测内容

- Digilent JTAG 链路和 XC7Z045 原始 IDCODE。
- PL SRAM 下载、startup 完成和配置状态读取。
- `STARTUPE2.CFGMCLK`、EOS、MMCM 锁定及复位释放。
- LUT、FF 和内部互联逻辑样本。
- 4 个 RAMB36 块 RAM 原语。
- 2 个 DSP48 推断路径。
- `BSCANE2 USER1` 片上结果读回。

## 输入工件

- bit：`artifacts/fpga/xc7z045_fabric_bist/20260721_211212/route_retry/audit3/xc7z045_fabric_bist_audited.bit`
- bit 大小：1,545,229 bytes。
- bit SHA-256：`705E4BDDF3EF62D77AD29FA85F557B4A8EBE6D7040FB91AEA739C5E15C7931CD`
- RTL SHA-256：`E05E568DB7A9B68855EA1BF63B185070D8B9F4DBBED18661F0BF7CBBCED9EC57`

## 本次实测结果

1. 2026-07-22 06:52 CST，PL SRAM 下载：PASS。
   - `PROGRAMMED_DEVICE|xc7z045`
   - `End of startup status: HIGH`
   - `CONFIG_STATUS|01010110000100000111111111111100`
   - `VOLATILE_SRAM_PROGRAM_PASS|1`
2. 第一次独立 XSDB/BSCANE2 读回：PASS。
   - `FINAL_STATUS|0xB101FFF0`
   - `FABRIC_BIST_HARDWARE_PASS|1`
3. 第二次独立 XSDB/BSCANE2 读回：PASS。
   - `FINAL_STATUS|0xB101FFF0`
   - `FABRIC_BIST_HARDWARE_PASS|1`
4. 下载后的原始 JTAG IDCODE 复查：PASS。
   - 期望和捕获的 LSB-first IDCODE 均为 `11001001000010001100111011000100`
   - `RAW_JTAG_IDCODE_PASS|1`

## 本次证据

- 下载日志：`artifacts/fpga/xc7z045_jtag_only/20260722_0000/hardware/vivado_program.log`
- 器件属性：`artifacts/fpga/xc7z045_jtag_only/20260722_0000/hardware/device_properties.rpt`
- 第一次片上结果：`artifacts/fpga/xc7z045_jtag_only/20260722_0000/hardware/bist_status_read1.log`
- 第二次片上结果：`artifacts/fpga/xc7z045_jtag_only/20260722_0000/hardware/bist_status_read2.log`
- IDCODE 复查：`artifacts/fpga/xc7z045_jtag_only/20260722_0000/hardware/jtag_idcode_after_bist.log`
- 下载资源守卫：`D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_065135_32a0b5db.jsonl`
- 两次读回资源守卫：`D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_065225_8e3e8d31.jsonl`、`D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_065245_78b88267.jsonl`
- IDCODE 资源守卫：`D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_065309_3655468d.jsonl`

## 未覆盖与风险边界

- 不是全部 LUT、FF、BRAM、DSP 和全部时钟资源的穷举测试。
- 未测试 PS、DDR、GT、高速接口、网口、USB、PCIe 或外部存储器。
- 未测试外部 I/O 动态时序、驱动强度、边沿、信号完整性或板级电气裕量。
- 未做长时间、多温度、多电压或多实现 seed 老化测试。
- 当前 FPGA 保持运行该 Fabric BIST bit；断电后配置消失。
