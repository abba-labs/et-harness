# CORDIC_P1_002 — CORDIC参数/结果位宽与16-bit打包测试

整理时间：2026-09-11 21:00 CST；对照本轮 Canonical Session 更新，不是新增测试。

适用基线：ET6801 / FPGA（单核 Profile `et6801_fpga`）；本轮 2026-09-11 20:31 CST，源码 `095cd6dba09dfee2d135f74bc913ad065ec9d6bb`（source_dirty=false，clean）；固件 `et6801-silicon-common-v0.1`；bitstream/设备身份未知。不把本轮 FPGA 结果写成 Silicon 结论。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：覆盖16/32-bit参数×16/32-bit结果四种组合，使用非零SINCOS双结果节点区分参数存储位置和结果打包；判别向量取正负不对称且高/低半字可区分的输入，避免打包错误仍产生偶然相等。执行：按当前参数宽度编码Raw（支持packed双参数时记录高/低半字身份）→配置位宽与函数模式→提交事务并有界等待→读取RESULT.PRIMARY（32-bit双结果加读RESULT.SECONDARY，16-bit打包路径保留完整RESULT.PACKED16 Raw）→按当前结果宽度做有符号拆包/解码（禁止先丢弃Raw再比较）→与独立Golden比较并汇总。ET6801由CTRL0.ARGSIZE/RESSIZE（bit8/bit9）承载；SVD直接说明16-bit结果模式下SINCOS/PM/HSINCOS双结果在RES1_RPT高/低halfword打包，须先保存完整Raw word再做signed halfword decode。

## 复测要点与判断边界

- 判定：Capability声明的计划位宽组合全部执行；16-bit双结果高/低半字与稳定映射一致；同一非零逻辑角度在四种组合下数学结果一致（不被零输入掩盖存储位置错误）；所有Decoded Actual满足对应格式accuracy budget。
- RESULT.PACKED16必须保留完整Raw word后拆半字，先解码再丢Raw即违规。
- 16-bit packed双参数属映射边界：PM packed option归入P1_002宽度/打包矩阵，不与P1_006的x→y主路径混淆。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P1_002`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
