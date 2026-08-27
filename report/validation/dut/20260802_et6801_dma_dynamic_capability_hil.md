# ET6801 DMA 动态能力与 P0 中断实板验证

时间：2026-08-02 13:26 CST

## 结论

ET6801 FPGA 原型的正式 DMA P0 链路通过。测试不是从 RAM 临时运行：先配置
XC7VX980T，使用 BootROM 工程到达 `main`，再擦写并校验 PFLASH0，最后从
`0x08000000` Flash 向量运行应用固件。PC 通过 J28 的 RS232 链路在 COM12 完成
HELLO、静态芯片能力门禁、固件动态能力查询、DMA0 通道 0 的 256 字节存储器搬运和
TRANSFER_DONE 中断验证。

本次结果证明的是当前 FPGA 原型、当前固件和当前板卡连接下的一条 DMA P0 数字功能
链路，不代表全部 DMA Feature 已覆盖。

## 环境与路由

- target：ET6801 CORE0，XC7VX980T FPGA 原型。
- FPGA 配置：Xilinx JTAG，目标 `xc7vx980t_0`。
- MCU 调试/烧录：J-Link AP[1]，Cortex-M7 r1p2，CPUID `0x411FC272`。
- PC 通信：J28 RS232，Prolific PL2303GT，COM12，115200 bps。
- 应用工程：`ET6801_SILICON_FLASH`。
- 破坏性范围：仅 PFLASH0 `0x08000000..0x0807FFFF` 擦写；没有修改
  BOOTDEF、NVR、OTP 或熔丝。
- 恢复方式：重新加载 BootROM/应用，或重新配置 bitfile 后再次执行正式部署脚本。

## 执行链路与结果

1. 只读识别确认 Xilinx JTAG 上存在 `xc7vx980t_0`；J-Link AP[1] 可识别 Cortex-M7。
2. SILICON 固件编译通过，0 error。
3. XC7VX980T bitfile 配置通过，DONE/EOS 为 1，CRC、IDCODE、Security 错误为 0。
4. BootROM 编译并临时加载到 `0x20500000`，到达 `main`：符号地址
   `0x20506349`，PC 为 `0x20506348`。
5. PFLASH0 `Erase Done`、`Programming Done`、`Verify OK`；从 Flash 向量运行后
   PC 位于 `0x08006718`。
6. HELLO 返回 `chip_id=et6801`、协议版本 1、构建标识
   `et6801-silicon-common-v0.1`，Framework、Resource 和 DMA Service 可枚举。
7. 正式 pytest Case 通过，结构化结果如下：

```text
transfer_bytes: 256
data_match: true
source_sha256 == destination_sha256:
  2aeb6c09d761cd5251a33d9bd5c645a0661713b9aef2bce404549aeca1b978c6
TRANSFER_DONE latched_events: 1
irq_count: 1
unexpected_count: 0
overflow_count: 0
route_count: 1
```

运行中固件自报 DMA 能力：

```text
features: 0x000001FF
channel_count: 8
max_transfer_count: 4095
max_gather_scatter_interval: 1048575
max_gather_scatter_count: 4095
irq_events: 0x0000001F
```

PC Case 的执行顺序已经实机证明为：

```text
HELLO芯片身份
  -> SVD生成的静态Chip Profile门禁
  -> 固件CAPABILITIES_GET动态门禁
  -> Resource分配
  -> DMA配置与启动
  -> TRANSFER_DONE中断及搬运数据校验
```

## 软件回归

- DMA 动态能力定向单元测试：14 passed。
- PC framework 全量单元测试：90 passed。
- 正式 HIL：1 passed，0 failed，0 skipped。

## 证据

- 配置检查：`artifacts/20260802_dma_dynamic_hil/config_doctor.json`
- 构建计划：`artifacts/20260802_dma_dynamic_hil/build_plan.json`
- 固件构建：`artifacts/firmware_build/20260802_131402_SILICON/`
- FPGA 配置：`artifacts/et6801_cli_flow/20260802_131451/01_xc7vx980t_program/`
- BootROM 构建/加载：
  `artifacts/et6801_cli_flow/20260802_131648/02_bootrom_build/`、
  `artifacts/et6801_cli_flow/20260802_131658/04_bootrom_keil_debug/`
- PFLASH 编程与运行：`artifacts/flash_run/20260802_131724/`
- 结构化 DMA 结果：
  `artifacts/20260802_dma_dynamic_hil/formal_dma_p0/dma_transfer_done_p0.json`
- JUnit：
  `artifacts/20260802_dma_dynamic_hil/formal_dma_p0/pytest_dma_dynamic_p0.xml`
- PC framework全量单测JUnit：
  `artifacts/20260802_dma_dynamic_hil/pc_framework_unit.xml`

关键 SHA256：

```text
应用AXF：CBDB2BF94A42E7288B89762029A5D72B4D1E643A1CADA3B9D14AF9F754BAE5DD
应用HEX：BD6253CB996172AE3B0CE369A7EBB697EAF00FBC1B4F722E96B05136C7D9C6B8
bitfile：953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C
BootROM AXF：C069198421F737D535BF5B75AC683FA6D32151D9530B798780C0DD896219CBEF
Flash运行manifest：7A8E423AF96022C291A408639532C11975FA7F8C641C9C91AF9FB2EAA52A167F
DMA结果JSON：E8F8DB6B53367F1CBDF53AB8C27CC521466BFCA5122CB23C7107A4BA3BC483B5
JUnit XML：BFDBD96D3DBB2BFCD9A431E2B744FEF17DE17236356A6BAF0F6EBBC9C42EEEF7
PC framework单测JUnit：2611281F756114A034B748BC2364C73CE2EB5321ABE4F9BD1899464FBD0189C2
```

## 未测项与风险

- 仅验证 DMA0 通道 0、单次 256 字节 memory-to-memory 和 TRANSFER_DONE。
- BLOCK、ERROR、源/目的事务事件、DMA1、其他通道、不同传输宽度/突发、LLI、
  Gather/Scatter 尚未测试。
- Flash 运行采用 J-Link 读取向量并直接运行；断电或复位后的 BOOTDEF 自动启动未测。
- 单板、单串口适配器、常温短时数字功能验证；不覆盖电气、时序裕量、温压和老化。
- 通用 ET 调试技能的 `debug_plan` 当前没有可执行 backend，本轮按项目已验证的显式
  门禁脚本完成硬件操作；该工具缺口不影响本次硬件结果，但需后续完善。
