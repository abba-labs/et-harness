# ET6801 SYSCNT Case知识

更新时间：2026-09-09 12:05 CST。

本目录长期保留每Case一份提炼型Markdown，由Agent审阅Canonical事实后维护；脚本只检查与生成导航，不自动编写结论。适用范围、问题、修复依据与未执行边界见各Case。本目录历史PASS不替代当前回归；当前测试结果以运行工作区Canonical Session为准。

本次迁移覆盖SYSCNT注册表全部7个已注册Case。公共契约共8条Case定义：`SYSCNT_P2_003`（外部脉宽测量计时间隔）为ET_CASE_PLAN——未注册、未实现、从未执行（芯片文档状态块与case_registry.py、session selection三方核对一致），不建知识记录、不补造执行表述；本目录不表示公共SYSCNT全部测试目标已实现。

<!-- ET_RECORD_AUTO_BEGIN -->

## Case知识索引

本索引不汇总测试状态；当前测试结果见运行工作区。

- [SYSCNT_P0_001 — 停止装载与双窗口读回测试](cases/SYSCNT_P0_001.md)
- [SYSCNT_P0_002 — 启停与续计数测试](cases/SYSCNT_P0_002.md)
- [SYSCNT_P1_001 — 低字进位与最大值回绕测试](cases/SYSCNT_P1_001.md)
- [SYSCNT_P1_002 — 频率标识设置与读取测试](cases/SYSCNT_P1_002.md)
- [SYSCNT_P2_001 — 时钟源与独立参考计时测试](cases/SYSCNT_P2_001.md)
- [SYSCNT_P2_002 — CPU停核时的计数策略测试](cases/SYSCNT_P2_002.md)
- [SYSCNT_P3_001 — 20轮装载启停重复验证测试](cases/SYSCNT_P3_001.md)

<!-- ET_RECORD_AUTO_END -->

## 历史来源与版本

以下为本次提炼依据，不是第二份活动状态：

- 最近一次运行：FPGA Lane 2026-09-04 06:39 CST，Source `2157037e3937d1d26a01390ae0bd652f40f788dd`（**dirty=true**，状态块如实记录），7 Case/23 执行=7 PASS/0 FAIL/0 SKIP（状态块更新 2026-09-04 08:50 CST）。23为参数Execution数，不是23条Case。
- **本树证据锚在仓库内**：Canonical Session为`artifacts/records/ET6801/SYSCNT/current`（session.json + 23份result.json）。当日另有两次同规模运行（061830 FAIL为平台轮、063223 PASS），最终轮为通过基线。原始的 artifacts/runs 执行目录已废弃并从仓库删除，本树不引用它。
- P2_002（CPU停核计数策略）在本轮PASS；注意与STIMER_P2_003（CPU Debug Halt的PAUSE策略FAIL）是同一停核问题域的两个IP实例——SYSCNT的HALT_ON_DEBUG路由验证通过、STIMER的Halt联动暂停失败，两条结论互为参照但不互相覆盖。
- 方法权威：[公共SYSCNT契约](../../../../test_case_doc/syscnt/syscnt.md)各Case的`ET_CASE_SPEC`；芯片适配见[ET6801 SYSCNT芯片文档](../../../../test_case_doc/syscnt/ET6801_syscnt.md)。

## 未闭环问题

本轮无FAIL/SKIP记录。`SYSCNT_P2_003`为未注册PLAN，无执行记录，不列入未闭环问题。

## 关键变化

- 2026-09-09 12:05 CST：建立SYSCNT固定Case档案，按R130 §8.1与R500 §6从Canonical Session（run 20260904_063646）与公共契约提炼7个已注册Case知识；未执行任何测试或硬件动作，未修改公共契约与芯片文档状态块。
- 2026-09-09 12:25 CST 修正：初版误将未注册的`SYSCNT_P2_003`（ET_CASE_PLAN）列入索引并在"未闭环问题"写了执行表述；经case_registry.py、session selection与状态块三方核对确认其未注册未执行后，已删除该文件并移出索引。修正依据：注册表只含7个ID，session selection同样只有7个。
