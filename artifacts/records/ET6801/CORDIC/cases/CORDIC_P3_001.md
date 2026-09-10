# CORDIC_P3_001 — CORDIC Float32代表节点重复稳定性测试

整理时间：2026-09-10 22:08 CST；对照本轮 Canonical Session 轻量确认，不是新增测试。

适用基线：ET6801 / FPGA；最近一次历史测试 2026-08-28 17:11 CST，源码 `596c1a73b91f6af577b1b274d49c34f8d9fb823a`（clean，来自芯片文档状态块）。板卡身份与bitstream版本未记录，不外推到其他FPGA版本或Silicon。关联Feature：CORDIC_F_001～F_009、CORDIC_F_011；资源等级 R0。 本轮已选节点 PASS，脏树不得外推（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）。

## 结果与可复用经验

最近一次CORDIC全量运行（2026-08-28 FPGA Lane，芯片文档状态块）本Case PASS，无FAIL记录；原始Canonical Session已删除，参数级观测值不可考，不引用不外推。方法要点：固定向量集使用固定seed标识九类函数各一个已审核Float32代表合法节点；数值配置只用Float32、32-bit、Normalized、Polling与Status能力，Expected由独立Float32 Raw Golden计算；每节点执行固定重复轮数，计划轮数与完成轮数写入Artifact。执行：加载固定seed向量清单并计算各节点Golden→确认Runtime Feature后配置→逐节点按稳定参数顺序连续执行固定重复轮数→每轮在有界轮询内读取Complete、Primary与适用Secondary Raw→每轮读取结果后清除Complete与错误状态并读清除后快照→逐轮与Golden比较，并比较同一节点重复Raw序列一致性→记录seed、节点、计划/完成轮数、Raw序列与状态序列。

## 复测要点与判断边界

- 判定：九类函数节点和固定重复轮数全部完成无超时；每轮Primary及适用Secondary Raw与独立Float32 Golden逐字一致；同一节点重复Raw序列完全一致、无随机漂移；每轮COMPLETE后清除，COMPLETE与错误状态均为零。
- 覆盖边界：只证固定代表节点的重复稳定性，不宣称覆盖定点Codec、边界向量、完整合法域或统一accuracy budget。
- 重复一致性是本Case独有判据：单轮正确不代表稳定，必须比较Raw序列本身，不能只看逐轮误差均值。

## 依据与变化

方法权威：[公共CORDIC契约](../../../../../test_case_doc/cordic/cordic.md)中的`CORDIC_P3_001`；芯片适配见[ET6801 CORDIC文档](../../../../../test_case_doc/cordic/ET6801_cordic.md)；历史结果与证据缺失声明见[历史来源与版本](../README.md)。本文不复制规范全文或运行包。

- 2026-09-09 11:30 CST：从芯片文档状态块与人读历史报告提炼方法要点与判断边界；未引用参数级观测值；未进行硬件复测。
- 2026-09-10 22:08 CST：本轮 FPGA 全量（源码 `7106a1562269da95d060e2cd756d53eef7e156d4`，source_dirty=true，固件 `et6801-silicon-common-v0.1`）本 Case 已选节点 PASS；脏树不得外推，方法正文不重写。
