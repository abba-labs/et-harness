# ET6801 CRC 全量 HIL 验证报告

时间：2026-08-11 23:43 CST

## 结论

本轮在 XC7VX980T ET6801 FPGA 原型上执行 CRC 全量正式 Case，结果为：

| 总数 | PASS | FAIL | SKIP |
|---:|---:|---:|---:|
| 45 | 43 | 2 | 0 |

除 FIFO Threshold 与 FIFO Overflow 两项外，CRC 的模式、数据宽度、Length、
Auto Length Reload、Result Check、IRQ、错误恢复、DMA 输入、稳定性和目标侧性能
测量均通过。两项 FIFO 失败使用 ET6801 历史 FunctionalTest 的原始配置和刺激，
并在目标端使用单条原子命令保持紧凑写入，不能归因于 PC 串口命令间隔。

本结果不把失败项改成 Deferred 或弱断言。当前结论是：所用
`ET6801_RTLr1800_FPGAv102_20260313` bitfile 的 CRC FIFO 行为与 ET6801 历史
FunctionalTest 预期不一致，需要由 RTL/设计侧核对当前 FPGA 实现。

## 环境与硬件链路

| 项目 | 实际值 |
|---|---|
| 被测目标 | ET6801 CORE0，XC7VX980T FPGA 原型 |
| bitfile | `D:/lihuan/vibe_code/code/fpga/ET6801_RTLr1800_FPGAv102_20260313/bit_files/et6801_fpga_top.bit` |
| bitfile SHA256 | `953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C` |
| BootROM | 临时加载至 `0x20500000`，到达 main，PC=`0x20506348` |
| 应用 | PFLASH0 `0x08000000..0x0807FFFF`，Erase/Program/Verify OK |
| 应用 AXF SHA256 | `F44D31E27F20F3BB4CD11847BB7D538C499572C04DB1D923E4CE777EB13DEC47` |
| 应用运行证据 | Reset=`0x080003A1`，PC=`0x0800A1C6`，位于 Flash |
| PC 控制链路 | J28 RS232，`COM12 @ 115200` |
| Firmware Build ID | `et6801-silicon-common-v0.1` |
| Registry Hash | `bd8d2981` |
| 硬件操作 | bit 易失配置、BootROM RAM 临时加载、PFLASH 擦写 |
| 未执行 | 未写 BOOTDEF、NVR、OTP、Fuse |

## 执行方法

1. 使用正式脚本生成 Keil 工程并构建 SILICON/PFLASH Target。
2. 按当前 FPGA 原型已验证顺序执行：bit 配置、BootROM 到 main、PFLASH
   擦除/编程/Verify、从 PFLASH 向量运行。
3. PC 通过 ET-Frame v1 与 CRC Service 交互，按注册表运行 P0～P3 共 45 项 Case。
4. CRC Golden 在 PC 端独立计算；DMA 与性能 Case 使用 DUT 返回的结果、IRQ、
   Channel 终态和 DWT 周期形成强证据。
5. FIFO Case 使用 ET6801 历史 `crc_ft.c` 的 Threshold、相同输入值和写入次数；
   写入集中在目标侧测试补充 Driver 中完成，Service/Wrap 不直接访问寄存器。

## 分级结果

| 等级 | 数量 | PASS | FAIL | 说明 |
|---|---:|---:|---:|---|
| P0 | 5 | 5 | 0 | 生命周期和 CRC8/16/32 基础向量 |
| P1 | 34 | 32 | 2 | FIFO 两项失败，其余配置、Length、Check、IRQ、错误路径通过 |
| P2 | 3 | 3 | 0 | CRC 与 DMA/SYSCTRL 路由组合通过 |
| P3 | 3 | 3 | 0 | 稳定性、CPU 与 DMA 目标侧性能测量通过 |

## 失败详情

### crc_p1_011：FIFO Threshold

- 配置：CRC32，Polynomial=`0x04C11DB7`，Initial=`0xFFFFFFFF`，
  Byte Swap Enable，FIFO Threshold=5。
- 刺激：目标端连续写入五次 `0x12345678`，第四次后读取检查点结果。
- 预期：第四次后 Result 保持写入前值，第五次后 Result 发生变化。
- 实际：写入前 Result=`3174720732`，第四次后 Result=`2906116182`，已经提前变化；
  第五次后仍为 `2906116182`。
- 结论：当前 FPGA 实现未表现出历史用例定义的 Threshold=5 更新节拍。

### crc_p1_012：FIFO Overflow

- 配置：CRC32，FIFO Threshold=1，其余配置同历史 FunctionalTest。
- 刺激：目标端连续写入七次 `0x12345678`。
- 预期：`FIFO_OVF=True`，随后重新配置可恢复正常计算。
- 实际：七次写入后 `FIFO_OVF=False`；因此 Case 在溢出强断言处失败，未伪造恢复 PASS。
- 结论：当前 FPGA 实现未产生历史用例预期的 FIFO Overflow 状态。

## 本轮发现并修复的 Case 问题

CRC P3 DMA Throughput 最初将 IRQ 注册放在 DMA Channel 配置之前，Firmware 按契约
返回 `BUSY`。Case 已改为：

```text
configure channel
-> enable IRQ
-> timed start / wait / result
-> disable IRQ
-> deconfigure channel
```

修正后 `crc_p3_003` 单项及最终全量回归均 PASS。该修复只改变 CRC P3 Case 的
编排顺序，没有修改公共层、Wire Contract 或 Firmware DMA 语义。

## 软件与构建验证

- SILICON Firmware：0 Error，0 Warning。
- Python `compileall`：PASS。
- CRC Driver 与代码规则单元测试：55 PASS。
- P3 DMA Throughput 定点复测：PASS。
- 最终全量 CRC HIL：43 PASS，2 FAIL，0 SKIP。

## 证据

- Firmware 构建：`artifacts/firmware_build/20260811_233022_SILICON/`
- XC7VX980T bit 配置：`artifacts/et6801_cli_flow/20260811_233207/01_xc7vx980t_program/`
- BootROM 到 main：`artifacts/et6801_cli_flow/20260811_233414/04_bootrom_keil_debug/`
- PFLASH Verify 与运行：`artifacts/flash_run/20260811_233541/`
- P3 DMA Throughput 复测：`artifacts/crc_hil/20260811_224300_et6801_crc/p3_rerun2/`
- 最终全量 CRC HIL：`artifacts/crc_hil/20260811_224300_et6801_crc/full_final2/`
- 最终 Session：`artifacts/crc_hil/20260811_224300_et6801_crc/full_final2/session.json`

## 剩余风险与下一步

1. 将两项 FIFO 失败连同 bitfile 版本、SVD 字段和历史 `crc_ft.c` 刺激提交 RTL/设计侧核对。
2. 在新的 RTL/bitfile 上只需先复测 `crc_p1_011`、`crc_p1_012`，通过后再跑 45 项全量。
3. 当前没有证据支持把失败归因于 PC、UART、ET-Frame、Service、Wrap 或 DMA；
   但在 RTL 设计侧确认前，也不能直接宣布 CRC FIFO 硬件缺陷。
