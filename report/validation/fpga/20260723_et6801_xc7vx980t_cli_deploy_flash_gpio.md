# ET6801/XC7VX980T 命令行部署、PFLASH0 与 GPIO 运行验证

时间：2026-07-23 12:58 CST

## 结论

在真实 XC7VX980T 承载的 ET6801 FPGA 原型上，以下命令行链路均已实测通过：

1. Vivado batch/Tcl 配置 XC7VX980T bit。
2. Keil Debug 命令行会话把 BootROM 加载到 `0x20500000` 并运行到 `main`。
3. Keil Flash 命令行会话擦除、编程并校验 PFLASH0
   `0x08000000–0x0807FFFF`。
4. J-Link 读取 PFLASH0 向量，直接启动 GPIO 固件，并观测到运行签名和翻转计数增长。

这证明了本次使用的 bit、CORE0 调试通路、BootROM RAM/ROM 映射、PFLASH0
擦写通路和 PFLASH 固件执行通路可用。

## 测试对象

- FPGA：XC7VX980T
- FPGA 设计：ET6801 FPGA 原型，CORE0
- bit：
  `D:\lihuan\vibe_code\code\fpga\ET6801_RTLr1800_FPGAv102_20260313\bit_files\et6801_fpga_top.bit`
- bit SHA256：
  `953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`
- BootROM AXF SHA256：
  `C069198421F737D535BF5B75AC683FA6D32151D9530B798780C0DD896219CBEF`
- 最终一键回归 GPIO PFLASH AXF SHA256：
  `A40EEB7A1CB159FE8D2AE16989B6701243FB783A53BA97E7A33E4EF59D1E347F`
- GPIO PFLASH HEX SHA256：
  `BB71AF17AA67B7BA8D7F32934E0C58DB3F5C1494035B72B71B25DBFCFDCF1FD1`
- Flash 算法：ET6801 DFP 0.1.0 `ET6801.FLM`

## 实测结果

### XC7VX980T bit 配置

- JTAG target：
  `localhost:3121/xilinx_tcf/Digilent/210251A08870`
- 识别器件：`xc7vx980t_0`
- EOS：1
- DONE internal：1
- DONE pin：1
- CRC error：0
- IDCODE error：0
- security error：0
- 结果：PASS

最终一键回归证据目录：
`artifacts/et6801_cli_flow/20260723_130435/01_xc7vx980t_program`

### BootROM 加载

- 加载基址：`0x20500000`
- 预期 `main`：`0x20506349`
- 实测 PC：`0x20506348`
- 说明：Thumb 函数符号最低位为 1，实测 PC 最低位清零，二者一致。
- 结果：PASS

最终一键回归证据目录：
`artifacts/et6801_cli_flow/20260723_130612/04_bootrom_keil_debug`

### PFLASH0 擦写

- 映像链接基址：`0x08000000`
- 允许范围：`0x08000000–0x0807FFFF`
- Keil 输出：`Erase Done`、`Programming Done`、`Verify OK`
- 结果：PASS

最终一键回归证据目录：
`artifacts/et6801_cli_flow/20260723_130630/05_gpio_pflash_program`

### GPIO 固件运行

- 初始 MSP：`0x20000818`
- Reset_Handler：`0x080003A1`
- 运行方式：J-Link 从 PFLASH0 向量直接跳转
- 运行时间：2600 ms
- 固件签名：`0x45543638`
- 相位：1
- GPIO 翻转计数：5
- 结果：PASS

最终一键回归证据目录：
`artifacts/et6801_cli_flow/20260723_130648/06_gpio_runtime`

## 一键集成回归

2026-07-23 13:03 CST 使用 `run_cli_flow.ps1` 一次性执行构建、bit 配置、
BootROM 加载、PFLASH0 擦写校验和 GPIO 运行验证，最终输出：

`ET6801_CLI_FLOW_PASS`

资源保护任务：
`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260723_130354_cf25fcc1.json`

## 问题与修正

第一次 Flash 会话停在映像加载阶段。只读复查时 PFLASH0 首字为
`0xFFFFFFFF`，因此未把该次会话判为成功。

最终定位到工程的 Flash 调试配置不完整：

- `UL2CM3` 缺少完整的 `ET6801.FLM` 路径和地址范围参数。
- `JLinkSettings.ini` 把目标设备设置成了 `ARM7`。
- PFLASH target 的链接配置最初仍落在 `0x00000000`。

修正为完整 ET6801 FLM 配置、`Device="Cortex-M7"`、`Override=1`，并使用
`0x08000000` scatter 文件后，Flash 擦写与校验在约 20 秒内完成。

## BOOTDEF 边界

本次没有修改 `BOOTDEF`。

源码表明 `BOOTDEF` 位于 DFLASH NVR option-byte 用户扇区 4 偏移 5，
`BOOTPIN_CONFIG` 位于同一扇区偏移 6。写入需要备份、擦除并回写整个
1 KiB NVR 扇区，且必须保持其他 option-byte 字段和校验信息一致。

因此本次只证明了“PFLASH 映像可执行”，没有证明“上电或复位后 BootROM
依据 BOOTDEF 自动选择 PFLASH0”。后者需要单独的 NVR 备份、目标值、
校验和恢复镜像，并再次进行明确的 option-byte 写入确认。

## 限制

- 单块 FPGA 板、单个 bit 和短时样本。
- GPIO 运行通过内存签名和计数证明，没有使用 XC7Z045 或外部仪器观测物理引脚。
- 未修改或验证 NVR/BOOTDEF 自动启动链。
- 未覆盖 PFLASH0 全容量逐字节测试、掉电保持、温压和长时间压力。
