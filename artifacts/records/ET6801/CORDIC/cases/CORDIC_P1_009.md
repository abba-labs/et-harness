# CORDIC_P1_009 — CORDIC零开销写读功能测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_026；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：选择单结果、双结果及PM双参数代表事务，使用可区分的确定性输入序列；公共Wrap必须提供同IP原子write→read语义，Case不直接依赖芯片SDK快捷Helper。执行：配置ZERO_OVERHEAD（ET6801 CTRL0.WORK_MODE=10）与稳定数值格式精度→为当前函数生成输入Raw与独立Golden并记录请求序号→经公共同IP原子接口进入受控窗口（ET6801由CORDIC_testExecuteZeroOverhead()按稳定函数ID提交一/两个参数，且保存/恢复调用前PRIMASK）→窗口内按函数参数数量提交完整输入→按result_count从RESULT.PRIMARY/SECONDARY立即读取本请求Raw（不插固定sleep）→退出窗口并按Codec恢复逻辑Actual→与当前请求Golden比较，多个函数/输入重复确认无前一请求残留。

## 复测要点与判断边界

- 判定：所有零开销事务Actual满足独立Golden与accuracy budget；每个Raw结果只能绑定当前request_id，不能读到前一事务结果；测试路径不依赖固定sleep或轮询完成状态伪装零开销语义。
- SDK两条历史缺陷不得进入路径：integer `CORDIC_calcultePM()`是错误历史Helper（CORDIC_DRV_001，写SINCOS入口且参数模型不符x→y）；历史zero-overhead helpers无条件重开中断（CORDIC_DRV_004）。公共Wrap只走保存/恢复PRIMASK的稳定入口。
- 强干扰（IRQ交错下不发生跨请求结果错配）不归本Case，由P3_003单独证明。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_009`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
