# ET6801 正式 PFLASH 启动与 UART 公共框架 HIL 验证

时间：2026-07-26 09:10 CST

## 结论

在 XC7VX980T 承载的 ET6801 FPGA 原型 CORE0 上，按照正式顺序完成并通过：

1. 重新配置 XC7VX980T bitstream；
2. 将 BootROM 加载到 FPGA BootROM 窗口并运行到 `main`；
3. 擦除、编程并校验 PFLASH0；
4. 从 PFLASH0 向量直接运行应用；
5. 通过 J28 RS-232、COM12、115200 8N1 完成 HELLO 身份识别；
6. 完成坏 CRC、噪声、半帧空闲恢复和单次超时重试验证；
7. 完成 1000 轮小/中/大载荷混合压力测试，共 3000 次事务；
8. 压力测试结束后再次完成 HELLO。

最终压力测试数据错误数为 0，自然重试数为 0。当前公共 UART 控制链路可以作为后续 IP 自动化测试的基础通信链路。

## 测试对象与固定输入

- 目标：ET6801 FPGA prototype CORE0
- 承载 FPGA：XC7VX980T
- Xilinx JTAG：Digilent `210251A08870`
- CPU 调试：J-Link，AP[1] Cortex-M7
- UART：J28 RS-232，COM12，115200 8N1
- PFLASH0：`0x08000000..0x0807FFFF`
- bit SHA256：`953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`
- BootROM AXF SHA256：`C069198421F737D535BF5B75AC683FA6D32151D9530B798780C0DD896219CBEF`
- 应用 AXF SHA256：`121B1E3335189C30E53CC50F226B6C0A68F3C6AB5DC5D4C22D18060AE3BA50BE`
- 固件 build ID：`et6801-silicon-common-v0.1`

## XC7VX980T bit 配置

- 识别器件：`xc7vx980t_0`
- CRC error：0
- IDCODE error：0
- security error：0
- EOS：1
- DONE internal：1
- DONE pin：1
- 结果：PASS

证据：

- `artifacts/et6801_cli_flow/20260726_085117/01_xc7vx980t_program`
- manifest SHA256：`B8BB4B6AF3083944C8679555C1DACE42893ACCC86C64412DDB4BE0A7316364C4`
- 资源任务：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085115_022a63ec.jsonl`

## BootROM 加载与 main

- 加载窗口：`0x20500000`
- `main` Thumb 符号：`0x20506349`
- 实测 PC：`0x20506348`
- 结果：PASS

证据：

- `artifacts/et6801_cli_flow/20260726_085315/04_bootrom_keil_debug`
- manifest SHA256：`F4C9006E246E0F5C9BABA9554D8834668720761B21D3F67597CFC4537126D8F4`
- 资源任务：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085313_b58e64af.jsonl`

## PFLASH 擦写、校验与运行

- Keil Flash：`Erase Done`
- Keil Flash：`Programming Done`
- Keil Flash：`Verify OK`
- Reset_Handler：`0x080003A1`
- 运行后 PC：`0x08003FA6`
- PC 所在区域：PFLASH
- 结果：PASS

证据：

- `artifacts/flash_run/20260726_085351`
- manifest SHA256：`CB9F4A73736020336EA0E0C1D7DEFAF882949B9F2E9F117C03BC97AB4F76DC80`
- Keil Flash log SHA256：`955D5202A824E1CE70E596CB6BC2DC2840AE030BC081812CFC4E849894A1DF1E`
- 资源任务：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085349_d84b0884.jsonl`

本轮没有修改 `BOOTDEF`、NVR、OTP 或其他 option byte。“从 Flash 运行”由 J-Link 读取 PFLASH 向量并直接设置 MSP/PC 完成；未验证断电或复位后 BootROM 依据 BOOTDEF 自动选择 PFLASH0。

## HELLO 身份识别

写入并运行后的首次 HELLO：

- transport：`serial:COM12@115200`
- chip ID：`et6801`
- protocol version：1
- firmware build ID：`et6801-silicon-common-v0.1`
- registry hash：`4b95f515`
- service：Framework Service `0/0`
- 结果：PASS

资源任务：

- `D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085520_056f6381.jsonl`

## 错误恢复与超时重试

- 坏 CRC 后恢复：PASS
- 噪声后重新同步：PASS
- 半帧空闲恢复：PASS
- 首次响应丢失后的超时重试：PASS
- 实际重试数：1
- 结果：PASS

证据：

- `artifacts/uart_protocol_fault_smoke/20260726_085538/result.json`
- SHA256：`CE0C7AEFC896DE50447727814F1DB6699B08F92798A906FCE96BBD9E121ADFE5`
- 资源任务：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085538_190ff899.jsonl`

## 1000 轮混合载荷压力测试

| 载荷类 | 载荷 | 事务数 | 重试数 | 最小延迟 | P50 | P95 | 最大延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|
| small | 16 B | 1000 | 0 | 11.280 ms | 12.092 ms | 13.021 ms | 113.436 ms |
| medium | 256 B | 1000 | 0 | 77.037 ms | 78.069 ms | 79.274 ms | 106.135 ms |
| large | 2048 B | 1000 | 0 | 568.730 ms | 569.877 ms | 570.961 ms | 581.622 ms |

汇总：

- 轮数：1000
- 事务数：3000
- 往返有效载荷：4,640,000 B
- 总耗时：660.855 s
- 有效载荷往返吞吐：7,021.2 B/s
- 数据错误：0
- 自然超时重试：0
- pytest：1 PASS

证据：

- `artifacts/framework_communication_hil/20260726_0856/framework_communication_stress_1000.json`
- 结果 SHA256：`714083F25CC0E409DD8CA7CA4F8E780C5DB857D8D511BE4DE58E4C5636DF569A`
- pytest stdout SHA256：`CF2CD43B7E1FA68DD7198994938F4B69DBD8CEF14C1EC47E4378CBC63FD793F4`
- 资源任务：`D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_085700_6d13b549.jsonl`

## 压测后存活检查

压力测试结束后再次执行 HELLO，chip ID、protocol version、firmware build ID、registry hash 和 Framework Service 均与压测前一致，结果 PASS。

资源任务：

- `D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260726_090839_9f837e58.jsonl`

## 问题复盘

第一次 bit 配置失败的直接原因是电脑同时连接了两个 Digilent JTAG，其中一个连接的是空 JTAG 链。Vivado 选择空链后报告 `No devices detected`。拔掉空 JTAG 后，脚本识别唯一 XC7VX980T 并成功配置。

此前一次直接 PFLASH 擦写出现大量 Verify mismatch。本轮恢复完整顺序“bit 配置 → BootROM 到达 main → PFLASH 擦写”后，使用同一应用镜像和 Flash 算法得到 `Verify OK`。这证明在当前 FPGA 原型上，PFLASH 擦写前必须执行已验证的 bit/BootROM 初始化顺序；不得跳过初始化直接重试 Flash。

## 限制与剩余风险

- 证据来自单块 XC7VX980T/ET6801 FPGA 原型、单个串口适配器和一次约 11 分钟压力测试。
- 当前验证 UART IRQ 与环形缓冲区路径；UART DMA 未实现、未测试。
- 未覆盖断电重启、BOOTDEF 自动启动、串口热插拔、不同波特率、不同 PC/适配器和数小时老化。
- 115200 bps 适合命令和普通测试数据，不适合高带宽实时波形流。
- 多 Xilinx JTAG 并存时必须按“非空 JTAG 链 + 目标器件型号”双重门禁选择目标，不能只按 USB 枚举顺序选择。
