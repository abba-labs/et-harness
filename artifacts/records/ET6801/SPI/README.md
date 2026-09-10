# ET6801 SPI Case知识

更新时间：2026-09-09 11:00 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅Canonical事实后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖SPI注册表全部12个已注册Case。公共契约共14个Case：`SPI_P1_006`（CS/SCLK波形，R3）与`SPI_P2_007`（Target输出高阻，R4）依赖示波器/弱负载观测的Bench条件，未注册、无执行记录，不补造记录；本目录不表示公共SPI全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [SPI_P0_001 — SPI基础配置读回](cases/SPI_P0_001.md)
- [SPI_P0_002 — SPI片内回环模式与帧宽](cases/SPI_P0_002.md)
- [SPI_P1_001 — SPI单实例外部回接](cases/SPI_P1_001.md)
- [SPI_P1_002 — SPI双实例双向收发](cases/SPI_P1_002.md)
- [SPI_P1_003 — SPI Transfer Mode与接收帧数](cases/SPI_P1_003.md)
- [SPI_P1_004 — SPI FIFO容量与复位](cases/SPI_P1_004.md)
- [SPI_P1_005 — SPI FIFO IRQ触发与清除](cases/SPI_P1_005.md)
- [SPI_P1_007 — SPI Target空TX状态](cases/SPI_P1_007.md)
- [SPI_P1_008 — SPI TX启动阈值边界](cases/SPI_P1_008.md)
- [SPI_P2_001 — SPI DMA双向与水位](cases/SPI_P2_001.md)
- [SPI_P2_005 — SPI无时钟等待与恢复](cases/SPI_P2_005.md)
- [SPI_P3_002 — SPI DMA连续收发](cases/SPI_P3_002.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次运行：FPGA Lane，2026-09-04 18:42 CST，Source `d6832926244edeb4b8170ef66d652e395f7d3648`（clean），12 Case / 152 参数执行 = 11 Case全PASS + SPI_P1_001整Case SKIP（36参数，硬件动作前跳过）。状态块更新于2026-09-04 18:50 CST。
- **本树证据锚在仓库内**：Canonical Session为`artifacts/runs/20260904_184216_913276_local_et6801_fpga_atp_testing/tests/spi/`（session.json + 152份cases/<id>/result.json，Manifest记录运行身份与配置快照）。与UART不同，SPI的参数级Observation/Measurement可回查；该run属删除保留集——若未来清理runs，须先评估本链接并迁移原始JSON。
- 当日修复史（同日三轮152执行：171618 FAIL→182941 FAIL→184216 PASS，芯片文档"本轮闭合问题"节）：①接线修正后48组双SPI交换角色/4种CPOL-CPHA/3帧宽及Target回环开关通过，其中关闭回环的24组才是PAD双向数据证据；②SDK文档FIFO容量16经实测修正为32，IRQ/启动/DMA阈值仍按SVD四位字段限制0~15；③SPI Case在CRG复位DMA前先停止并解除通道配置再关Controller，消除Service旧配置影响；④报告摘要改为每Execution只登记一次。最终轮复用同一Flash固件（固件源码`ba5ba0b535a4e45ba485caed564f7251f34dabc8`）未重复烧录，仅修PC摘要。本轮知识以最终PASS轮为基线，不逐参数复制历史FAIL值。
- 方法权威：[公共SPI契约](../../../../test_case_doc/spi/spi.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 SPI芯片文档](../../../../test_case_doc/spi/ET6801_spi.md)。

## 未闭环问题

- [SPI_P1_001](cases/SPI_P1_001.md)：当前SPI0/SPI1四线互联不满足单实例MOSI→MISO回接，36参数在硬件动作前合法SKIP。复测条件：改为单实例回接并声明对应handle/GPIO及loopback角色。

## 关键变化

- 2026-09-09 11:00 CST：建立SPI固定Case档案，按R130 §8.1与R500 §6从Canonical Session（run 20260904_184216）与公共契约提炼12个已注册Case知识；未执行任何测试或硬件动作，未修改公共契约与芯片文档状态块。
