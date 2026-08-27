# ET6801 DMA + UART 外设链路硬件验证

时间：2026-08-02 18:55 CST  
目标：ET6801 FPGA原型（XC7VX980T，CORE0）  
链路：J-Link + J28 RS232（Prolific PL2303GT，COM12，115200 bps）  
总体结论：FAIL（DMA全量结果仍包含2个DONE语义失败；新增UART外设路径全部PASS）

## 验证目标

在不增加外设或仪器的前提下，确认当前控制UART能否承担DMA外设配测，并完成所有当前具备安全、确定判据的DMA Case。测试只覆盖数字功能。

UART复用边界：

- 可用：UART TX作为DMA目的外设，验证M2P、DMAMUX、外设握手、DSTTRAN和PC实际接收。
- 不可安全复用：UART RX作为DMA源时会与ET-Frame协议RX中断竞争同一FIFO，因此P2M不执行。
- 不可实现：只有一路已连接UART，P2P缺少第二个独立外设请求端。

## 实现链路

```text
pytest DMA Case
  -> ResourceDriver / DmaDriver / SystemDriver / UartDriver
  -> ET-Frame
  -> Resource / DMA / System / UART Service
  -> 对应Wrap
  -> ET6801 DMA、DMAMUX、UART Driver
  -> UART TX DMA request
  -> MAX3232/J28/RS232
  -> PC TargetClient EVENT队列
```

DMA发送的是一帧完整、CRC正确的ET EVENT。`CHANNEL_START_WAIT`仅在有界轮询确认DMA通道完成后才允许固件发送命令响应，因此DMA EVENT与响应不会交叉破坏串口协议。

## 构建与部署

- FPGA bitfile：`D:\lihuan\vibe_code\code\fpga\ET6801_RTLr1800_FPGAv102_20260313\bit_files\et6801_fpga_top.bit`
- bitfile SHA256：`953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`
- 固件AXF SHA256：`7FDF89FDCFDB295392F761356224FE2346ECD8DA05A45616A2E56DE69568095B`
- Keil FPGA和SILICON目标均0 Error编译通过。
- 首次PFLASH操作出现“Erase Done / Programming Done但Verify mismatch”；未启动该镜像。
- 按恢复路径重新配置bitfile、加载BootROM到`0x20500000`并到达main，再次擦写后得到`Erase Done`、`Programming Done`、`Verify OK`。
- Flash运行证据：reset handler `0x080003A1`，运行PC `0x08007CF2`。

## 结果

新增Case：

| Case | DMA0 | DMA1 | 关键判据 |
|---|---|---|---|
| DMA-P2-004 COMBINED IRQ | PASS | PASS | 单一combined物理路由，TFR状态、数据和清理正确 |
| DMA-P2-006 DSTTRAN IRQ | PASS | PASS | TFR与DSTTRAN均锁存，PC收到完整EVENT |
| DMA-P2-008 M2P | PASS | PASS | DMAMUX到UART TX，DMA发送字节与PC解码EVENT完全一致 |

全量DMA回归：

- Case级：20 PASS、1 FAIL、18 SKIP/阻塞，共39个规划Case。
- 实际硬件实例：48 PASS、2 FAIL；另有18个Case因明确条件阻塞而SKIP。
- 唯一失败仍是DMA-F-020：`writeback_enabled=false`时DMA0/1的LLI描述符DONE均由0变为1；数据搬运和其他描述符字段正确。
- 失败证据：`before_control_high=0x00000040`，`after_control_high=0x00001040`。

结构化结果目录：

- `artifacts/dma_uart_hil/20260802_1854_smoke`
- `artifacts/dma_uart_hil/20260802_1855_full`
- 其中JSON统计为48 PASS、2 FAIL。

## 未覆盖与下一步

- P2M：等待第二路独立UART/SPI等外设请求源，不能抢占控制UART RX。
- P2P：需要两个独立外设请求端。
- SRCTRAN：随P2M解锁。
- ERR：需要Profile声明不会导致系统失联的安全故障地址。
- 软件握手：SVD/头文件的软件请求寄存器定义存在不一致，不能猜地址实现。
- TCM/CORE1：需要安全窗口与核路由契约。
- P3：AMBA master、Protection、flow-control、低功耗和DFT先做设计契约确认。
- DONE：需要RTL/SVD确认该位究竟是“完成状态写回”还是可禁用的“写回使能”，在确认前保持FAIL，不修改断言。
