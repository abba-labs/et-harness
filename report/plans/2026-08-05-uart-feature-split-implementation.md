# UART Feature拆分实施计划

时间：2026-08-05 09:04 CST

## 任务1：先固定Case契约

- 修改`test_uart_cases_contract.py`，声明拆分后的P2/P3函数、收集数和deferred数。
- 增加断言：P2-005不得再声称覆盖地址IRQ；P3 shadow和direct FIFO必须是两个函数。
- 运行该契约测试，确认在Case尚未修改时失败。

## 任务2：拆分可执行Case

- 在`uart_test_case_p2.py`新增独立9-bit地址IRQ Case，保留地址匹配Case原有纯数据判据。
- 在`uart_test_case_p3.py`把shadow配置和direct FIFO访问拆成两个Case，分别按CPR位独立gate。
- RI、DCD不引入假fixture或固定芯片连线，只在规划和状态表中拆成两个独立`blocked_by_board`项。

## 任务3：同步文档

- 更新`UART.md`第六章Case定义、Case数量和配测统计。
- 更新第七章状态：新拆出的Case在硬件重测前标记“待复测”；RI、DCD分别标记`SKIP/blocked_by_board`并说明解除条件。
- 保留旧HIL证据路径，不把旧组合Case结果转记为新Case PASS。

## 任务4：验证

- 运行UART Case contract和相关UART Driver/fixture unit。
- 运行P0～P3 collect-only并核对数量。
- 运行PC完整framework unit回归。
- 本轮不自动进行烧写、复位或硬件运行；需要HIL时单独列出硬件门禁信息。
