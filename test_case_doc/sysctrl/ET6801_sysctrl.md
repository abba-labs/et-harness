# ET6801 SYSCTRL计数器路由适配

更新时间：2026-09-03 21:58 CST。

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
- 补充带test前缀的Halt路由设置及路由快照，位于Driver源/头文件底部测试扩展区；只有该Driver可以读写SYSC字段。
- SYSCTRL Wrap负责围绕写操作调用SYSC解锁/锁定，不改DMAMUX状态。
- `SYSCTRL_getSYSCNTClock()`固定返回25MHz，不能证明当前FPGA镜像实际计数频率；本轮接口不调用它，也不把25MHz写入公共层。
- 未确定全IP复位/中断等行为，不在本轮改动范围。

## 4. Validation Boundary

先以寄存器桩校验字段隔离和Wire协议，再编译当前固件。只有正式SYSCNT HIL能证明路由在当前FPGA上的行为，软件测试不能替代。
