# ET6801 CRC Case知识

更新时间：2026-09-10 22:06 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅人读历史证据后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖CRC注册表全部23个已注册Case（P0×3、P1×16、P2×1、P3×3）。公共Case Catalog中另有1个PLAN项（`CRC_P1_011` FIFO DMA请求水位测试：等待独立`fifo_cnt/dma_req` Observer，未注册、无执行记录，不补造记录）；公共契约同时保留`CRC_F_012 FIFO物理深度`的`dynamic_fifo_depth_proof_gap`，无对应Formal Case。本目录不表示公共CRC全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [CRC_P0_001 — CRC运行时能力与身份一致性测试](cases/CRC_P0_001.md)
- [CRC_P0_002 — CRC8/16/32基础计算测试](cases/CRC_P0_002.md)
- [CRC_P0_003 — CRC模块启停与恢复测试](cases/CRC_P0_003.md)
- [CRC_P1_001 — CRC多项式配置测试](cases/CRC_P1_001.md)
- [CRC_P1_002 — CRC初始值配置测试](cases/CRC_P1_002.md)
- [CRC_P1_003 — CRC输入字节交换测试](cases/CRC_P1_003.md)
- [CRC_P1_004 — CRC输入位反转测试](cases/CRC_P1_004.md)
- [CRC_P1_005 — CRC输出位反转测试](cases/CRC_P1_005.md)
- [CRC_P1_006 — CRC输出异或测试](cases/CRC_P1_006.md)
- [CRC_P1_007 — CRC非整字节长度与LENGTH读回测试](cases/CRC_P1_007.md)
- [CRC_P1_008 — CRC自动长度重载测试](cases/CRC_P1_008.md)
- [CRC_P1_009 — CRC结果校验匹配测试](cases/CRC_P1_009.md)
- [CRC_P1_010 — CRC校验错误中断测试](cases/CRC_P1_010.md)
- [CRC_P1_012 — CRC FIFO溢出与恢复测试（历史FAIL：FPGA FIFO_OVF硬件问题）](cases/CRC_P1_012.md)
- [CRC_P1_013 — CRC中断强制、投递与关闭测试](cases/CRC_P1_013.md)
- [CRC_P1_014 — CRC中断清除测试](cases/CRC_P1_014.md)
- [CRC_P1_015 — CRC中断屏蔽与Raw状态测试](cases/CRC_P1_015.md)
- [CRC_P1_016 — CRC长度错误中断测试](cases/CRC_P1_016.md)
- [CRC_P1_018 — CRC非法访问宽度BUS_ERR与恢复测试](cases/CRC_P1_018.md)
- [CRC_P2_001 — CRC DMA输入等价性测试](cases/CRC_P2_001.md)
- [CRC_P3_001 — CRC确定性长稳测试](cases/CRC_P3_001.md)
- [CRC_P3_002 — CRC CPU输入路径吞吐表征测试](cases/CRC_P3_002.md)
- [CRC_P3_003 — CRC DMA输入路径吞吐表征测试](cases/CRC_P3_003.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次CRC运行（[芯片文档状态块](../../../../test_case_doc/crc/ET6801_crc.md)）：FPGA Lane，2026-08-28 17:11 CST，Source `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean），23 Case/44执行=22 PASS/1 FAIL（CRC_P1_012）/0 SKIP，状态块更新于2026-08-28 21:26 CST。
- **原始Canonical证据已不在仓库**：状态块记录的Evidence路径已随早期清理不在本机两个工作树。本目录知识依据芯片文档状态块与人读报告整理；参数级execution明细（result.json、Observation原始值）不可考，一律不引用、不外推具体观测值；状态块明确记录的CRC_P1_012观测值（`FIFO.OVERFLOW`保持false、恢复轮CRC实际值与期望值均为`0x140B8DD8`、剩余输入计数0）注明"状态块记录"来源后引用。
- 两轮人读报告交叉印证（当时注册表为24稳定Case/45执行，含现已撤销为PLAN的`CRC_P1_011`；均无本IP当前注册Case之外的新增FAIL）：
  - 2026-08-11 CRC全量HIL：45执行=43 PASS/2 FAIL/0 SKIP，FAIL为FIFO两项（[报告](../../../../report/hil/20260811_et6801_crc_hil_report.md)）。
  - 2026-08-12 一键运行Excel HIL：45执行=43 PASS/2 FAIL/0 SKIP，稳定Case 24项中22 PASS/2 FAIL，两个FAIL均保留为真实硬件结论（[报告](../../../../report/hil/20260812_et6801_crc_operator_excel_hil_report.md)）。
  - 历史FAIL项`CRC_P1_011`（FIFO Threshold旧Result节拍Oracle）经2026-08-22复盘确认Oracle错误，已撤销实现并保持PLAN；`CRC_P1_012`为真实硬件FAIL延续至今（芯片文档§2.3/§6.3）。
- 方法补强史：[CRC Optimization Closure Review](../../../../report/review/20260819_crc_optimization_closure_review.md)对`CRC_P1_007`/`CRC_P1_013`/`CRC_P1_018`做CASE_CHANGE补强并冻结24个稳定Case Contract；补强后语义即当前注册表语义，并在2026-08-28运行中执行。当时无真机，FPGA HIL @ validated SHA为NOT_EXECUTED，不把软件闭环升级为硬件PASS。
- 环境身份（来自08-11报告）：ET6801 CORE0 XC7VX980T FPGA原型，bitfile `ET6801_RTLr1800_FPGAv102_20260313`，固件Build ID `et6801-silicon-common-v0.1`，PC控制链路J28 RS232 COM12 115200；08-28轮的bitstream与板卡身份未记录。
- 方法权威：[公共CRC契约](../../../../test_case_doc/crc/crc.md)各Case的`ET_CASE_SPEC`；芯片适配与Feature映射见[ET6801 CRC芯片文档](../../../../test_case_doc/crc/ET6801_crc.md#crc-record-index)。

## 未闭环问题

- [CRC_P1_012](cases/CRC_P1_012.md)：FIFO_TRHD=1并连续写入7次后`FIFO.OVERFLOW`仍保持false；恢复轮CRC实际值与期望值均为`0x140B8DD8`、剩余输入计数0（人工确认刺激方法有效）。结论：当前ET6801 FPGA实现的FIFO_OVF功能存在问题，CRC计算与恢复路径正常。复测条件：RTL/bit修复FIFO_OVF后用相同紧凑写入和恢复流程复测。

## 关键变化

- 2026-09-10 22:06 CST：对照本轮 Session（`7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，43 PASS / 1 FAIL）确认 CRC_P1_012 仍 OVERFLOW 不置位，恢复 CRC `0x140B8DD8`。

- 2026-09-09 11:30 CST：建立CRC固定Case档案，按R130 §8.1与R500 §6从人读历史报告与芯片文档状态块提炼23个已注册Case知识；原始Canonical Session缺失已在"历史来源与版本"如实声明；本次为知识迁移整理，未执行任何测试或硬件动作，未修改公共契约与芯片文档测试状态块。
