# ET6801 UART P2-010与P3-007独立HIL证据

时间：2026-08-05 09:46 CST

## 环境

- 目标：XC7VX980T原型中的ET6801 CORE0。
- 固件：PFLASH运行，HELLO build ID为`et6801-silicon-common-v0.1`。
- 控制链路：J28 RS232，COM12，115200-8-N-1。
- 功能链路：UART1与UART2交叉短接，`J25.3→J30.5`、`J25.5→J30.3`。
- Bench：`Et_Automated_Testing_Platform_Code/pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`。
- 本轮不烧bit、不加载BootROM、不擦写Flash，不触碰OTP/NVR/fuse。

## 方法

通过平台pytest硬件门禁，仅执行：

```text
uart_test_case_p2.py::test_uart_p2_010_nine_bit_address_irq
uart_test_case_p3.py::test_uart_p3_007_shadow_fifo_configuration
```

P2-010随后单独重复执行一次。Fixture在每次Case前完成串口打开、HELLO、chip/build校验和SERVICE_LIST发现；Case退出路径负责恢复UART配置。

## 结果

- P2-010：`FAIL`，连续两次一致。
  - IRQ使能读回：`enabled_mask=0x40`。
  - 匹配9-bit地址刺激已发送。
  - 刺激前后均为`event_count=0`、`pending_mask=0`、`active_mask=0`。
  - 结论：当前环境具备刺激和观测条件，不能标记SKIP；地址匹配数据路径PASS不等于地址IRQ PASS。
- P3-007：`PASS`。
  - CPR：`0x13DF2`，SHADOW能力存在。
  - 配置读回：enable、TX阈值2、RX阈值4。
  - 恢复读回：disable、TX阈值0、RX阈值1。
  - 恢复后4字节loopback完整一致。

## 证据

- `artifacts/uart_hil/20260805_094120_split_cases/p2-010_p3-007_junit.xml`
  - SHA256：`709728F7932B796CCD691587D420BF254B681F33987AD79E8C36E38972FC4630`
- `artifacts/uart_hil/20260805_094120_split_cases/p2-010_retest_junit.xml`
  - SHA256：`5E7DCA53DE745873C189C639C13B93A8D2000347E2FA21BE96730622379F3B7F`
- `artifacts/uart_hil/20260805_094120_split_cases/uart_p3_007_shadow_fifo_configuration.json`
  - SHA256：`E7B7F6F80D580E4E0D106BE543DA52D6436483C919FD53502D0F4A2A6153897B`
- P2 Case源码SHA256：`7B290F0465E99F9D3D6870F687505BFB7D7C110E2EC55BE7E8EBFF9A5BEAC25D`
- P3 Case源码SHA256：`1D2F6A0ABD341C1D9E742E0D5B72A7E537370546C188F749118A1196E6471DF6`

## 剩余风险

- P2-010尚未定位到RTL未实现、IIR/LSR清除语义、中断向量映射或Service IRQ来源转换中的具体一层；本记录只确认端到端地址IRQ未出现。
- P3-007只证明单板、单次shadow配置与恢复，不包含长稳、跨实例和异常复位覆盖。
