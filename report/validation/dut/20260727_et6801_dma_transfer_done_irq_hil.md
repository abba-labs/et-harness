# ET6801 DMA0 TRANSFER_DONE 中断 HIL 验证

时间：2026-07-27 07:46 CST

## 结论

在 XC7VX980T 承载的 ET6801 FPGA 原型 CORE0 上，已按正式硬件流程完成并通过：

1. 重新配置指定 XC7VX980T bitfile；
2. 将 BootROM 临时加载到 `0x20500000` 并运行到 `main`；
3. 擦除、编程并校验 PFLASH0；
4. 从 PFLASH0 向量直接运行测试固件；
5. 通过 J28 RS-232、COM12、115200 8N1 完成 HELLO 和服务枚举；
6. 执行 DMA0 Channel 0 的 256 字节内存搬运；
7. 通过公共 IRQ Manager 捕获并上报 `TRANSFER_DONE` 中断；
8. 正式 pytest 连续执行两次，独立结构化复核执行一次，结果均为 PASS。

本次结果证明：当前 Resource Service、DMA Service、PC Resource/DMA Driver、DMA Wrap、IRQ Wrap、IRQ Manager、ET-Frame 串口链路能够组成完整的首个 DMA 中断自动化测试闭环。

## 硬件和固定输入

- 目标：ET6801 FPGA prototype CORE0
- 承载 FPGA：XC7VX980T
- Xilinx JTAG：Digilent `210251A08870`
- CPU 调试：J-Link，AP[1] Cortex-M7
- UART：J28 RS-232，COM12，115200 8N1
- PFLASH0：`0x08000000..0x0807FFFF`
- bitfile SHA256：`953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`
- BootROM AXF SHA256：`C069198421F737D535BF5B75AC683FA6D32151D9530B798780C0DD896219CBEF`
- 应用 AXF SHA256：`324412780A334DD2BF68AC27DAD968023F5329CAC7FAF72D5D804DE40368B634`
- 固件 build ID：`et6801-silicon-common-v0.1`

## 部署链路

### XC7VX980T 配置

- 目标器件：`xc7vx980t_0`
- CRC error：0
- IDCODE error：0
- security error：0
- EOS：1
- DONE internal：1
- DONE pin：1
- 结果：PASS

证据：

- `artifacts/et6801_cli_flow/20260727_073950/01_xc7vx980t_program`
- manifest SHA256：`6347454B1577799A389C397A21AC4492E53FCDE5D63F23F8AF1BBF316A043E43`

### BootROM 初始化

- 加载窗口：`0x20500000`
- `main` Thumb 符号：`0x20506349`
- 实测 PC：`0x20506348`
- 结果：PASS

证据：

- `artifacts/et6801_cli_flow/20260727_074205/04_bootrom_keil_debug`
- manifest SHA256：`EE7B391753CBB0A7693F9A8A7C5287B7092D8142CDCAF7987C4A8CAF4EE56492`

### PFLASH 编程和运行

- Keil Flash：`Erase Done`
- Keil Flash：`Programming Done`
- Keil Flash：`Verify OK`
- Initial MSP：`0x20008B00`
- Reset_Handler：`0x080003A1`
- 运行后 PC：`0x08007216`
- PC 区域：PFLASH
- 结果：PASS

证据：

- `artifacts/flash_run/20260727_074227`
- manifest SHA256：`14AD94B4AF61FE82A076B76500F27D8CCC16DB61FCE9E0ACFFDA5B2540265AC7`
- Keil Flash log SHA256：`8225AF158F514A287E5B7B2826315A5E6AD198D532497602AE116A3D71F6E115`

本轮没有修改 `BOOTDEF`、NVR、OTP、fuse 或其他 option byte。从 Flash 运行采用 J-Link 读取向量并直接设置 MSP/PC，未声称已经验证断电或复位后的 BootROM 自动启动选择。

## HELLO 和服务枚举

- transport：`serial:COM12@115200`
- protocol version：1
- chip ID：`et6801`
- firmware build ID：`et6801-silicon-common-v0.1`
- registry hash：`1530f1dc`
- Framework Service：`0x0000/0`
- Resource Service：`0x0010/0`
- DMA0 Service：`0x0100/0`
- DMA1 Service：`0x0100/1`
- 结果：PASS

证据：

- `artifacts/20260727_dma_irq_hil/hello_service_list_utf8.json`
- SHA256：`B65C5E0B8D698C2C3BD6D2E52A1E01D8EA56F16E4F4E810465B071D998DE3D98`

## DMA0 TRANSFER_DONE Case

测试链路：

```text
PC pytest
  -> Resource Driver 创建系统 SRAM 源/目标缓冲区
  -> DMA Driver 配置 DMA0 Channel 0
  -> DMA Service 调用 DMA Wrap
  -> DMA Wrap 调用 ET6801 DMA Driver
  -> IRQ Wrap/IRQ Manager 绑定并使能物理中断
  -> 硬件完成 256 字节搬运
  -> DMA ISR 进入 IRQ Manager
  -> DMA Service 回调锁存 TRANSFER_DONE 和 IRQ 计数
  -> PC 读取目标缓冲区和中断结果并判定
```

结构化结果：

| 项目 | 结果 |
|---|---:|
| DMA instance | 0 |
| Channel | 0 |
| 搬运长度 | 256 B |
| IRQ route count | 1 |
| latched events | `0x00000001` |
| TRANSFER_DONE | true |
| IRQ count | 1 |
| unexpected count | 0 |
| overflow count | 0 |
| Target retry count | 0 |
| 源/目标数据一致 | true |
| 源 SHA256 | `2aeb6c09d761cd5251a33d9bd5c645a0661713b9aef2bce404549aeca1b978c6` |
| 目标 SHA256 | `2aeb6c09d761cd5251a33d9bd5c645a0661713b9aef2bce404549aeca1b978c6` |

正式 pytest：

- `test_dma0_channel0_transfer_done_interrupt`：PASS
- JUnit：tests=1、failures=0、errors=0、skipped=0
- `artifacts/20260727_dma_irq_hil/pytest_dma_transfer_done.xml`
- SHA256：`DD1C77F28A23C47543B8E5099A432CFFB40BB241DEBB314A50EB86D740B1735A`
- `artifacts/20260727_dma_irq_hil/pytest_dma_transfer_done_utf8.log`
- SHA256：`EB4BD64F7014F7D42E9D358035802242741B974E8DFCD37C59F9C21CE29D781E`

结构化复核：

- `artifacts/20260727_dma_irq_hil/dma_transfer_done_result_utf8.json`
- SHA256：`C8CFEDE0BD19CD011258F8004786C53FB62FC4F7A33FEC36370A02D2E62A548E`

## 故障复盘

在重新配置 bitfile 前，两次 PFLASH 下载均显示 `Erase Done` 和 `Programming Done`，但出现完全相同的大量 Verify mismatch。实际读回值表现为旧数据和新数据只能继续清零，说明 PFLASH 擦除没有真正生效。

重新执行“指定 bitfile 配置 → BootROM 到达 main → PFLASH 擦写”后，同一应用和同一 Flash 算法立即得到 `Verify OK`。因此当前 FPGA 原型的正式部署流程必须保留 bit/BootROM 初始化，不能在 FPGA 状态来源不明确时直接重试 PFLASH。

失败日志保留为时间线证据：

- `artifacts/flash_run/20260727_072511/keil_cli_flash.log`
- `artifacts/flash_run/20260727_072723/keil_cli_flash.log`

## 限制和后续范围

- 仅验证单块 XC7VX980T/ET6801 FPGA 原型。
- 仅验证 DMA0 Channel 0、256 字节、内存到内存搬运和独立 `TRANSFER_DONE` 中断。
- 尚未覆盖 DMA1、其他 Channel、BLOCK、ERROR、源/目标事务中断、不同宽度/突发、LLI、Gather/Scatter、边界条件和压力测试。
- 尚未验证 BOOTDEF 自动启动、断电重启、长时间运行或多板一致性。
- 本结果只覆盖数字功能，不代表 PFLASH、IO 或时序的模拟/电气特性。
