# ET6801 DMA UART1/UART2 全量硬件验证

时间：2026-08-03 12:15 CST  
目标：ET6801 XC7VX980T FPGA 原型，CORE0  
控制链路：J-Link + J28 RS232，COM12，115200 bps  
配测链路：UART1 与 UART2 板上接插件交叉短接  
结论：当前可安全执行的 DMA P0～P2 实例全部通过；68 PASS、0 FAIL、9 SKIP。

## 硬件连接

接口文档与实物接线一致：

```text
J25.3  UART1_RX  <-  J30.5  UART2_TX
J25.5  UART1_TX  ->  J30.3  UART2_RX
```

UART0 仅供 PC 协议通信，不参与 DMA 配测。DMA Case 只消费 bench profile 中的逻辑角色，UART1/UART2 实例号和 DMA request interface 没有写死在 Case 中。

## 本轮修复

首次全量执行中，DMA0/1 的 DSTTRAN 和 257-byte M2P 只收到部分数据。J-Link 只读诊断确认 UART1/UART2 初始时钟未打开且仍处于复位状态；修复后由 System Wrap 根据 board 声明统一释放测试 UART 的时钟和复位。

随后 1-byte M2P/P2M/P2P 已全部通过，但高负载 M2P 和 DSTTRAN 仍会丢数。根因是 UART2 配测接收依赖主循环轮询，DMA 中断和控制 UART 响应期间无法及时清空 RX FIFO。修复后：

- UART Service 通过公共 IRQ Manager 绑定捕获 UART 的 RX_READY/RX_IDLE 回调；
- ISR 只搬运字节到既有捕获缓冲区，不解析测试协议；
- UART Service 仍只调用 UART Wrap 和公共 IRQ Manager；
- 捕获优先级由 board 宏声明，不在 Service 或 Case 中写死。

针对性复测中，DMA0/1 的 DSTTRAN IRQ 和 257-byte M2P 共4项全部通过。

## DONE 语义更正

初版 Case 将 `CTL_H.DONE` 当成运行时“写回使能”。SVD 明确给出 `DMA_COMP_PARAMS_CHx.CHx_CTL_WB_EN` 是只读硬件能力参数，ET6801 每个通道均为1；`CTL_H.DONE` 是描述符完成状态。硬件在初始 DONE=0 时完成后写成1属于正确行为。

Case 已改为验证：

- 初始 DONE=0 或1均可构造；
- 传输完成后 DONE 必须为1；
- 业务数据正确；
- 描述符其他字段不得被意外修改。

DMA0/1 × 初始 DONE 0/1 共4项全部通过。

## 构建与部署

- 固件构建：0 Error，0 Warning；证据 `artifacts/firmware_build/20260803_120625_SILICON`。
- XC7VX980T bit：`artifacts/et6801_cli_flow/20260803_120809/01_xc7vx980t_program`，DONE/EOS=1，CRC/IDCODE/SECURITY error=0。
- bit SHA256：`953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`。
- BootROM 会话在 `0x20506348` 到达 main；会话日志为 `artifacts/et6801_cli_flow/keil_bootrom_debug_session.log`。
- 最新 PFLASH 镜像 SHA256：`3EFC0F8AAE43F496522C349807EE58AA903C2A74573CF9977CDDADB6C4FC422C`。
- PFLASH 擦除、编程、Verify 全部通过；运行 PC=`0x08007E98`，证据 `artifacts/flash_run/20260803_121304`。

本轮再次证明：当前原型在发生调试/复位扰动后，可靠部署顺序必须是 `重新配置 bit -> BootROM 到 main -> PFLASH 擦写与 Verify -> 从 Flash 运行`。

## 全量结果

JUnit：`artifacts/dma_uart_hil/20260803_1215_final_full/pytest_dma_full.xml`

| 等级 | 实例数 | PASS | FAIL | SKIP |
|---|---:|---:|---:|---:|
| P0 | 9 | 8 | 0 | 1 |
| P1 | 25 | 23 | 0 | 2 |
| P2 | 43 | 37 | 0 | 6 |
| 合计 | 77 | 68 | 0 | 9 |

已经实测通过 DMA0/1 的 M2M、M2P、P2M、P2P，1/17/257 字节外设传输，TFR/BLOCK/SRCTRAN/DSTTRAN/COMBINED 中断，LLI、Gather、Scatter、FIFO、别名地址、并发通道及长时间混合传输等当前可执行能力。

9项 SKIP 均为显式条件缺失，不是运行失败：

1. 未声明安全 ITCM/DTCM 破坏性窗口；
2. 优先级仲裁缺少可靠的完成/进度顺序观测；
3. reload 缺少通用的有界停止原语；
4. 未声明安全的无效 LLI 地址；
5. 未声明不会导致系统失联的 DMA bus-fault 地址；
6. 软件握手寄存器尚无公共 API；
7. 板级没有可控请求极性源；
8. CORE1 与安全 TCM 窗口未声明；
9. DMA 时钟/复位原子 Service 尚未实现。

## 剩余风险

BootROM 在本轮最后一次加载时已经到达 main，但 Keil 命令包装器在退出清理阶段超时并把资源任务记为失败；后续 PFLASH Verify、Flash 运行和全量 DMA 均成功，因此不影响本轮 DUT 功能结论。该问题属于命令行工具收尾可靠性，后续应单独修复，不能把该次包装器状态记为 PASS。

