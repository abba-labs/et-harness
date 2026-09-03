# ET6801 SYSCTRL计数器路由适配

更新时间：2026-09-03 22:41 CST。

只记录本轮获准修改的SYSCNT依赖；公共命令以`sysctrl.md`为准。无硬件测试结论。

## 1. Source Basis

- `test_case_doc/ET6801.svd`：SYSC.CLK_SCNT.SEL_IN、SYSC.SCNT.HALT_MODE_EN。
- `firmware/chips/et6801/sdk/CMSIS/Device/Include/et6801.h`：对应生成字段掩码/位移。
- `firmware/chips/et6801/sdk/ET6x_Driver/Inc/et6x_sysctrl.h`与对应Source：时钟源枚举、选择函数、SYSC解锁/锁定接口。
- SYSCNT资料根检索与历史需求归并沿用`../syscnt/ET6801_syscnt.md`第一、四章；该证据范围只覆盖计数器依赖，不声称SYSCTRL全集已检索或测试。

## 2. Public-to-Chip Mapping

| 公共事实 | ET6801映射 | 证据状态 |
|---|---|---|
| 计数器实例0 | 单个SYSCNT的系统路由 | VERIFIED：SVD命名字段 |
| INTERNAL | SYSCTRL_SYSCNT_CLKSRC_OSC25M，SYSC.CLK_SCNT[0]=0 | VERIFIED：目标SDK及SVD |
| EXTERNAL | SYSCTRL_SYSCNT_CLKSRC_XO25M，SYSC.CLK_SCNT[0]=1 | VERIFIED：目标SDK及SVD |
| halt_enabled | SYSC.SCNT.HALT_MODE_EN[0]，1为使能 | VERIFIED：目标SVD；不能由配置读回推断CPU真实停止 |

## 3. Driver Changes and Limits

- 复用`SYSCTRL_selectSYSCNTClockSource`，只改变CLK_SCNT指定字段。
- 已补充`SYSCTRL_testSetSYSCNTHaltRoute`和`SYSCTRL_testGetSYSCNTRouting`，位于Driver源/头文件底部测试扩展区；只有该Driver可以读写SYSC字段。
- SYSCTRL Wrap负责围绕写操作调用SYSC解锁/锁定，不改DMAMUX状态。
- `SYSCTRL_getSYSCNTClock()`固定返回25MHz，不能证明当前FPGA镜像实际计数频率；本轮接口不调用它，也不把25MHz写入公共层。
- 未确定全IP复位/中断等行为，不在本轮改动范围。

## 4. Validation Boundary

先以寄存器桩校验字段隔离和Wire协议，再编译当前固件。只有正式SYSCNT HIL能证明路由在当前FPGA上的行为，软件测试不能替代。

本轮状态（2026-09-03）：PC专项4项通过；新增Driver寄存器桩1项通过，验证CLK_SCNT与SCNT位隔离；受控Service/Wrap格式、严格语义常量及任务范围检查通过。Keil编译和HIL尚未执行。

2026-09-03 22:18的总软件门禁曾被两项旧合同测试误报阻塞；2026-09-03 22:38已按用户批准单独修复（本地提交`2d734c7`）：

- DMA合同现在只对DMAMUX配置、释放及控制器映射函数禁止端点/实例推导，保留直接Request ID检查；新增计数器映射不再误报。
- Driver合同现在允许合规的新扩展文件，仍遍历全部Driver校验隔离区/编译开关，并检查既有扩展与必需API没有丢失。

恢复本批SYSCTRL实现后的专项验证：PC及上述合同共33项通过，WSL Native寄存器桩1项通过；负向回归确认非法DMA推导、缺少扩展标记/编译开关、区外API及缺少既有扩展仍被拒绝。

2026-09-03 22:41：本批最终`python tools/validate_pc.py`通过，928 PASS、12项条件SKIP（软件测试节点，不是IP硬件Case数量）。新增Native项在Windows因无本机C编译器跳过，但已在WSL单独执行通过。全树格式/注释、受控变化严格语义常量、合同同步、Formal收集及11类报告软件导出均通过；运行标识`20260903_223855_f40af47c`。Keil编译及HIL仍为NOT_EXECUTED，不将软件验证记为硬件PASS。
