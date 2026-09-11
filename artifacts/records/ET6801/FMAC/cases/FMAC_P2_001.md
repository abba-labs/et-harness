# FMAC_P2_001 — FMAC 双向DMA门控与FIR端到端测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

2026-08-28 FPGA全量运行（23 Case/46执行=23 PASS/0 FAIL/0 SKIP，来自芯片文档状态块）中本Case PASS；更早开发过程的历史失败已整改闭环，本文件不复述参数级细节。方法要点：从目标Profile解析FMAC输入/输出request、endpoint和transfer_width（禁止公共Case硬编码芯片编号或地址），确认双向Mapping且输入/输出宽度均16-bit、FMAC X1/Y Watermark均设1；使用[0x4000,0x2000,0x1000,0x0800]四抽头与恒定0x2000输入，DMA目的区域预填哨兵值；Gate关闭对照准备两条DMA描述符但不打开FMAC Request Gate，观察Channel不伪成功、目的区保持哨兵；保持FMAC idle期间打开两个Request Gate后Enable，等待两Channel进入明确终态；固定比较DMA目的序列最后4项=0x1E00。

## 复测要点与判断边界

- 判定：Gate关闭对照两Channel无伪成功且目的区域保持哨兵；Gate开启后输入/输出Channel均无ERROR并回到Free；DMA目的序列最后4项逐元素等于0x1E00。
- Request Gate只在FMAC idle修改且使用目标要求的DMA Watermark；`dma_execution_mapping_gap`已由本Case端到端闭环（芯片文档）。
- 清理严格逆序：STOP FMAC→关Request Gate→停/清DMA→释放映射→CLEAR FMAC和Resource。

## 依据与变化

方法权威：[公共FMAC契约](../../../../../test_case_doc/fmac/fmac.md)中的`FMAC_P2_001`；芯片适配见[ET6801 FMAC文档](../../../../../test_case_doc/fmac/ET6801_fmac.md)；历史开发过程与整改结论见[2026-08-25 FMAC HIL失败根因分析](../../../../../report/analysis/20260825_fmac_hil_failure_root_cause_analysis.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:07 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
