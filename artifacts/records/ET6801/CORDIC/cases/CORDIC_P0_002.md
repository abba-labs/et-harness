# CORDIC_P0_002 — CORDIC定点核心数学函数矩阵测试

历史整理声明：2026-09-11 21:00 CST；原“对照本轮 Canonical Session”声明未获当前证据支持，撤回其已核实含义。

适用基线：ET6801 / FPGA；源码与运行对应关系未核实，不作为当前版本验证结论。

来源状态：UNVERIFIED

来源修正（2026-09-12 17:09 CST）：来源工作区现存 Session 为 `18bbc66f-6b0d-4396-adcb-0e92d2a957fa`，源码 `228df5bd75a11f7b27c691698d77e65d517fea99`；与本文原基线不一致。该 Session 包含本 Case，但不能据此证明旧正文描述的轮次、方法及观测属于它。本次仅标记来源冲突，未重跑测试、未改原始结果、未完成发布确认。以下原声明保留为历史，不能当作本轮已核实 PASS。

历史基线声明：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：为九类数学函数（SINCOS、PHASE_MODULUS、ARCTAN、HSINCOS、ATANH、EXP、LN、SQRT、TAN）选择可复现的代表合法域向量（双参数函数按x→y有序提交）；输入按Capability冻结的32-bit定点Codec编码，Expected由PC double-precision独立数学库计算；使用Runtime声明最高精度配置与已审核的1e-4绝对误差预算。先取证后判定：提交一个完整逻辑事务后有界等待完成（不用固定sleep），读取RESULT.PRIMARY（双结果函数加读RESULT.SECONDARY）与STATUS.COMPLETE，Raw与Decoded、Expected、Error全部入证据再比较。

## 复测要点与判断边界

- 判定：九类函数及全部计划代表向量执行完整；每个Decoded Actual满足对应accuracy budget；每个结果保留Raw值、Codec身份与Decoded值（禁止只存浮点结论）；每节点读取时STATUS.COMPLETE处于完成终态。
- 判别向量使用正负不对称、高/低半字可区分的输入，避免打包或存储位置错误被偶然相等掩盖；PM严格x后y顺序。
- TAN fixed Raw解码公式主要来自current FPGATest验证实现（CORDIC_DRV_006 codec gap），由独立codec helper+golden-vector回归冻结；单次读取异常不得直接归因硬件，需先排除Codec与Golden来源问题。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P0_002`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
