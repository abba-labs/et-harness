# ET6801 UART 公共协议错误恢复与 1000 轮压力测试

时间：2026-07-24 15:18 CST

## 结论

ET6801 FPGA 原型通过 J28 DB9 RS-232、COM12、115200 8N1 与 PC 运行
ET-Frame v1 公共协议。本次实现并实板验证了 CRC 错帧恢复、噪声重同步、
截断帧恢复、单次超时重试和固件重复请求响应重放。

1000 轮混合数据压力测试 PASS。每轮依次测试 16 B、256 B 和 2048 B，
共 3000 次请求；所有响应均与请求载荷逐字节一致。

## 设计约束

- PC 超时后只重试一次，总尝试次数为两次。
- 重试复用原始编码帧，因此 session、sequence 和请求内容完全一致。
- 固件缓存最近一条完整响应；严格重复请求只重放响应，不重复执行命令。
- 相同 session/sequence 但内容不同的请求被丢弃。
- 解析器在错误帧内发现后续合法帧头时重新计算期望长度，避免截断帧永久卡死。
- UART 字符超时事件可主动清理残帧；解析器重同步不依赖某一芯片必须实现该中断。

## 构建与硬件写入

- 目标：ET6801 FPGA prototype CORE0，XC7VX980T
- bitfile：`ET6801_RTLr1800_FPGAv102_20260313/bit_files/et6801_fpga_top.bit`
- BootROM：临时加载至 `0x20500000`，到达 `main`
- 应用：`ET6801_SILICON_FLASH`
- PFLASH0：`0x08000000..0x0807FFFF`
- PFLASH 擦除、编程、Verify OK，Reset_Handler=`0x080003A1`
- 未写 BOOTDEF、NVR、OTP
- 固件 AXF SHA256：
  `86519690D5B8B8C1EE9CB0385AF8A4D981A37028FBE7FD3B9A9C7A7A65996E43`

硬件证据：

- `artifacts/et6801_cli_flow/20260724_150240/01_xc7vx980t_program`
- `artifacts/et6801_cli_flow/20260724_150456/04_bootrom_keil_debug`
- `artifacts/flash_run/20260724_150527`
- `artifacts/firmware_build/20260724_150037_SILICON`

## 错误恢复测试

结果：

- CRC 错帧后发送合法帧：PASS
- 合法帧前插入噪声：PASS
- 截断帧后发送合法帧：PASS
- PC 丢弃首个响应后超时重试一次：PASS
- 重试次数：1

证据：

- `artifacts/reliability/20260724_protocol_reliability/fault_smoke_after_resync_fix.json`
- SHA256：
  `5500FC00D6A2E23EDE96762166C53BE13074690EE20ED380CCEFCC1C55B6FBD3`

## 1000 轮混合数据压力测试

| 数据档 | 载荷 | 请求数 | 重试数 | 最小延迟 | P50 | P95 | 最大延迟 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 小 | 16 B | 1000 | 0 | 10.615 ms | 12.149 ms | 12.789 ms | 19.166 ms |
| 中 | 256 B | 1000 | 0 | 71.068 ms | 72.324 ms | 73.316 ms | 82.356 ms |
| 大 | 2048 B | 1000 | 0 | 522.572 ms | 523.798 ms | 525.054 ms | 567.371 ms |

汇总：

- 轮数：1000
- 请求数：3000
- 往返有效载荷：4,640,000 B
- 总耗时：609.224 s
- 有效载荷往返吞吐：7,616.3 B/s
- 数据错误：0
- 自然超时重试：0

证据：

- `artifacts/reliability/20260724_protocol_reliability/stress_1000.json`
- SHA256：
  `E71473DC0392029F7F70C8A2E3A92D85B57975E93FC8671BDC16F7BEF1B217D9`

## 其他验证

- PC 单元测试：24 PASS
- Keil ARM Compiler 6 构建：0 error，0 warning
- Python 验证脚本语法检查：PASS

## 限制与剩余风险

- 证据来自一块 XC7VX980T/ET6801 FPGA 原型、一个串口适配器和一次约 10 分钟压力测试。
- 当前验证的是 UART IRQ 模式；UART DMA 数据搬运尚未实现和验证。
- 未覆盖断电重启、反复复位、串口拔插、不同波特率、不同 PC/USB 适配器和数小时老化。
- 115200 bps 的 2048 B 往返延迟约 524 ms，适合命令与普通测试数据，不适合作为高带宽波形实时流通道。
