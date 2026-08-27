# ET6801 FPGA 原型命令行部署

本目录固化 XC7VX980T/ET6801 FPGA 原型的三条命令行链路：

1. Vivado batch/Tcl 配置 XC7VX980T。
2. Keil `UV4.exe -d` 自动加载 BootROM，运行到 `main`，记录证据并退出。
3. Keil `UV4.exe -f` 擦写并校验 PFLASH0；J-Link 读取向量表后直接跳转，验证 GPIO 固件计数持续增长。

运行输入：

- Vivado安装目录和bitfile不再使用开发电脑默认路径，必须通过`run_config.yaml`
  或脚本参数显式提供。
- BootROM 工程：
  `workspaces\et6801_bootrom_runtime\source\Project\ET6801.uvprojx`
- GPIO 工程：
  `workspaces\et6801_gpio_toggle\DFP\Project\ET6801_GPIO_Toggle.uvprojx`
- PFLASH0：`0x08000000..0x0807FFFF`
- Flash 算法：ET6801 DFP 0.1.0 的 `ET6801.FLM`

从正式测试入口运行时，在代码根目录的`run_config.yaml`中配置：

```yaml
pipeline:
  deploy:
    bitfile: true
environment:
  tools:
    vivado:
      root: C:/AMD/Vivado/2024.2
dut:
  images:
    bitfile:
      source: file
      path: C:/fpga_image/et6801_fpga_top.bit
```

双击`run_test.bat`后会先执行XC7VX980T易失性配置；配置失败时不会继续运行Formal
Case。以上路径仅为格式示例，必须替换为当前电脑的实际路径。

单独执行FPGA命令行流程时，必须显式传入工具和bitfile：

```powershell
$toolRoot = 'C:\AMD\Vivado\2024.2'
$bitfile = 'C:\fpga_image\et6801_fpga_top.bit'
& '.\tools\fpga\et6801\run_cli_flow.ps1' `
  -ToolRoot $toolRoot -BitFile $bitfile -PrepareOnly
```

`-PrepareOnly`会构建BootROM和GPIO固件，并打印硬件写入门禁，不操作硬件。

经人工核对门禁后，完整执行：

```powershell
& '.\tools\fpga\et6801\run_cli_flow.ps1' `
  -ToolRoot $toolRoot `
  -BitFile $bitfile `
  -HwServerPort 3121 `
  -ConfirmVolatileProgram `
  -ConfirmRamLoad `
  -ConfirmPFlashProgram `
  -ConfirmRunControl
```

如果电脑连接了多个 J-Link，必须额外传入 `-JLinkSerial <serial>`，禁止依赖探针枚举顺序。

分步脚本均支持单独执行：

- `program_xc7vx980t.ps1`
- `build_bootrom.ps1`
- `load_bootrom_keil_debug.ps1`
- `build_gpio_toggle.ps1`
- `flash_gpio_toggle.ps1`
- `verify_gpio_runtime.ps1`

当前运行验证是“从 PFLASH0 向量表直接跳转”，用于独立证明 Flash 内容可执行；它不等价于已经证明 BootROM 按启动配置自动选择并跳转 PFLASH0。后者应作为单独的启动链测试保留。

## 已验证基线

2026-07-23 12:58 CST，已在真实 XC7VX980T/ET6801 FPGA 原型上逐步实测通过：

- XC7VX980T bit 配置，DONE/EOS 为 1，CRC、IDCODE 和安全错误为 0。
- BootROM 加载到 `0x20500000`，到达 `main`，PC=`0x20506348`。
- GPIO 固件链接到 `0x08000000`，PFLASH0 擦除、编程和校验均通过。
- PFLASH0 向量为 MSP=`0x20000818`、Reset_Handler=`0x080003A1`。
- 直接从 PFLASH0 向量运行后，签名=`0x45543638`，GPIO 翻转计数=`5`。

Flash 下载必须同时保留以下两部分配置：

- Keil target 的 `FlashDriverDll`/`UL2CM3` 指向完整的 `ET6801.FLM`、`0x08000000` 和 `0x00080000`。
- `JLinkSettings.ini` 使用 `Device="Cortex-M7"` 且 `Override=1`。

缺少前者或把设备错误设置成 `ARM7`，会导致 Keil Flash 会话停在加载阶段。

## BOOTDEF 安全边界

`BOOTDEF` 不是普通内存寄存器。它位于 DFLASH NVR option-byte 用户扇区 4，
偏移 5；`BOOTPIN_CONFIG` 位于同一扇区偏移 6。修改任一字段都需要备份、
擦除并回写整个 1 KiB NVR 扇区，还必须保持该扇区其他字段和校验信息一致。

因此，现有一键流程不写 `BOOTDEF`。如需验证 BootROM 自动从 PFLASH0 启动，
必须另行完成 NVR 全扇区只读备份、目标值与校验计算、恢复镜像和人工写入门禁。
