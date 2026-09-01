# UART 合规整改实施计划

**目标：** 修复 UART 固件与 PC 自动化测试中已确认的假 PASS、IRQ 语义泄漏、分层越界、能力门控、资源生命周期、通信重试和证据记录问题。

**架构约束：**

- 固件保持 `Service -> UART Wrap -> UART Driver/Test Driver`。
- 公共 Wrap 不暴露芯片 Driver 原始语义，Service 不直接调用 Driver 或寄存器。
- PC Case 只编排语义 Driver 与 fixture，不直接创建底层通信或资源 Driver。
- 有效能力由芯片静态 capability、固件运行时服务/Feature 与 bench 实例共同约束。
- pytest 公共层统一记录 PASS、FAIL、SKIP 和实际消费的证据源。
- 本轮只做代码、单元测试与编译，不烧录、不执行硬件测试。

## Task 1：固件 UART 中断语义边界

- [x] 公共头、Service 和 Application 不再依赖 `chip_status`。
- [x] Driver 原始中断快照仅保存在 Wrap 私有状态中。
- [x] Wrap 对外只提供归一化 interrupt/event/line/error flags。
- [x] 即使没有 wire event，也消费并清除私有中断快照。
- [x] 固件契约测试通过。

## Task 2：UART Case 强断言与无假 PASS

- [x] IRQ 来源和错误位使用稳定语义枚举精确断言。
- [x] 中断 mask Case 验证完整 enable/clear，不宣称未验证的优先级。
- [x] P0 cleanup 失败不得被忽略。
- [x] P2-008 只宣称并验证 reset recovery。
- [x] P3 Case 只依赖语义 Feature，不解释 ET6801 寄存器常量。
- [x] UART Driver/Case 契约测试通过。

## Task 3：Fixture、Bench 与能力交集

- [x] UART、DMA、Resource、SYSCTRL、CRG 依赖服务在执行前校验。
- [x] UART handle 由芯片 capability、运行时服务和 bench 实例交集产生。
- [x] P2 DMA Case 不再直接创建底层 Driver。
- [x] P2 DMA 使用 bench 中的 UART 参数和 DMA 端口。
- [x] Resource 清理无条件执行，清理失败进入 Case 失败结果。
- [x] bench 仅允许当前真实使用的 `stop_mismatch_framing` 错误刺激。
- [x] 相关单元测试通过。

## Task 4：通信重试与结果证据契约

- [x] 默认命令只发送一次；仅显式 `retry_safe` 命令可重试一次。
- [x] 重试复用同一帧、Sequence 和 Session ID。
- [x] Case 显式登记实际消费的证据源。
- [x] 声明需要外部证据但未消费时，不允许 PASS。
- [x] session/case 结果包含可追溯且不伪造的运行身份字段。
- [x] PASS、FAIL、SKIP 结果单元测试通过。

## Task 5：文档、固件构建与全量回归

- [x] 更新 UART 文档中的 Case 名称、统计、deferred 和当前验证事实。
- [x] 更新 PC 架构文档中的 retry/evidence/session 契约。
- [x] 完成 PC framework unit、UART collect-only、compileall 和分层扫描。
- [x] 使用项目受控 Keil 流程编译 `ET6801_FPGA_ITCM` 与 `ET6801_SILICON_FLASH`。
- [x] 更新 ACTIVE、ET skill notice，并刷新/复查项目状态。
