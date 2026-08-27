# ET6801 UART 9-bit地址中断Driver修复与HIL证据

时间：2026-08-05 11:12 CST

## 现象

旧固件能够完成9-bit地址匹配、过滤和数据接收，但P2-010连续两次未得到地址中断事件：`enabled_mask=0x40`，而`event_count`、`pending_mask`和`active_mask`均为0。

## 修复范围

- 目标：XC7VX980T中的ET6801 CORE0。
- UART Test Driver：在隔离的测试扩展区增加IIR/LSR原子快照，将LSR `ADDR_RCVD`解析为9-bit地址事件；真实OE/PE/FE/BI/RFE错误继续保留为ERROR。
- UART Wrap：只调用UART Driver并转换公共标志，不直接访问寄存器。
- UART Service：只消费Wrap快照，不改变PC协议。
- 未修改其他IP、其他芯片、bitfile、BootROM、OTP/NVR/fuse。

## 硬件流程

```text
XC7VX980T bit重新配置
-> BootROM加载到0x20500000并到达main
-> PFLASH0擦除/编程/Verify
-> 从Flash向量运行
-> COM12 HELLO和SERVICE_LIST校验
-> UART1/UART2 9-bit地址中断P2-010
-> UART RX、parity error、IRQ mask/priority/clear影响回归
```

功能链路为`J25.3 UART1_RX <- J30.5 UART2_TX`和`J25.5 UART1_TX -> J30.3 UART2_RX`。控制链路为J28 RS232/Prolific COM12，115200-8-N-1。

## 结果

- bit：仅识别一个Digilent目标和一个XC7VX980T；CRC、IDCODE和安全错误为0，EOS、内部DONE和DONE pin为1。
- BootROM：加载到`0x20500000`，到达`main`，PC=`0x20506348`。
- PFLASH：`Erase Done`、`Programming Done`、`Verify OK`；从`0x080003A1`运行到Flash区域。
- P2-010：1 PASS、0 FAIL、0 SKIP。
  - 地址事件：`enabled_mask=0x40`、`pending_mask=0x40`、`event_count=1`、`event_count_delta=1`、`overflow_count=0`。
  - 9-bit地址和数据接收正确；清理后enabled/pending/active均为0；恢复收发数据一致。
- 影响回归：RX data available、parity error、IRQ mask/priority/clear共3 PASS、0 FAIL、0 SKIP。
- PC framework unit完整回归通过。
- `ET6801_SILICON_FLASH`构建为0 Error、0 Warning；前后两次构建HEX SHA256均为`5ECD5CA5256848089F292834DF61BDE2073012D087BF40A8F82BD936C4204300`。AXF因构建元数据不同而哈希变化，不代表Flash代码变化。

## 证据

- bit：`artifacts/et6801_cli_flow/20260805_110109/01_xc7vx980t_program/`
- BootROM：`artifacts/et6801_cli_flow/20260805_110343/04_bootrom_keil_debug/`
- PFLASH：`artifacts/flash_run/20260805_110455/`
- P2-010：`artifacts/uart_hil/20260805_110737_p2_010_driver_fix/`
  - JUnit SHA256：`7B1E047F92D2F2F38B0EC04AAD94065BC3F080E0366BFBDC3BDFD96FEAEF09F5`
  - 结果JSON SHA256：`46B652343AC6B0AD81B04FFDEF8DB5F61039FEF93301712EB22CA4BC3F612BFD`
- IRQ影响回归：`artifacts/uart_hil/20260805_110851_uart_irq_driver_regression/`
  - JUnit SHA256：`31E3ACCC7ED325046D26FAB7C37CA549F05748AB0A367B1C1AB7B8AF1874DEE4`
- 新构建：`artifacts/firmware_build/20260805_111040_SILICON/`

## 最终结论与边界

P2-010此前失败的直接原因位于ET6801 UART Driver的软件事件分类路径，不是UART1/UART2通信数据路径故障。修复后地址中断和相关错误/普通IRQ回归均在真实硬件上通过。

本证据只覆盖单块XC7VX980T ET6801原型、CORE0、UART1/UART2数字功能和室温短时运行；不覆盖电气指标、跨板时序裕量、长时间老化或其他芯片UART实现。
