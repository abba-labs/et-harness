# XC7Z045 PS CPU、L1 Cache 与双核一致性硬件自检

时间：2026-07-22 08:18 CST

## 结论

在仅连接 Digilent JTAG、不使用 DDR、不连接网线/USB/外部仪器、也不驱动外部 IO 的条件下，XC7Z045 PS 两颗 Cortex-A9 的 OCM 自检、主要指令类别、异常入口、VFP、PMU、MMU、L1 I/D Cache、独占访问以及双核 SCU 一致性测试均为 **PASS**。测试结束后，两颗 CPU 均已恢复为 `Running`，原有 PL Fabric BIST 仍为 **PASS**。

PL310 L2 的 ID、类型、控制寄存器、辅助控制寄存器和事件计数器配置均可通过 DAP 正确读写并恢复原值；但 OCM 测试流量的 L2 请求数和命中数均为 0。因此当前只能证明 **L2 控制面可访问**，不能证明 L2 数据缓存通路已工作，也不能据此判定 L2 异常。直接验证 L2 数据通路需要使用确定经过 PL310 的内存，优先选择另行授权的 DDR 测试。

## 硬件门禁与范围

- 目标：XC7Z045-FFG900，芯片修订未知。
- 板卡：ET6001/ET6801 FPGA 平台板。
- 路由：Digilent JTAG-SMT2，序列号仅保存在原始日志中。
- 允许动作：暂停/复位 Cortex-A9、向高地址 OCM 下载并运行临时 ELF、修改易失性 CPU/SCU/PL310 寄存器、读取 BSCANE2 USER1 状态。
- 禁止动作：DDR 写入、Flash/SD/QSPI 启动介质写入、OTP/NVR/fuse 操作、外部 IO 驱动。
- 破坏性：否；未写入任何非易失性介质。
- 恢复路径：`rst -cores -start` 后显式继续两核；必要时可断电重启。最终已确认两核 `Running`。

## 测试程序

- 工作区：`workspaces/xc7z045_ps_selftest/`
- ELF：`workspaces/xc7z045_ps_selftest/build/ps_selftest.elf`
- 链接位置：高地址 OCM，向量 `0xFFFF0000`，入口 `0xFFFF0020`，mailbox `0xFFFFC000`。
- 构建器：项目本地 Arm GNU Toolchain 15.2.Rel1，未修改系统 PATH 或注册表。
- 运行环境：Vivado/XSDB 2024.2。
- 外部依赖：无 libc、无 UART、无 DDR、无 BSP。

## 已通过项目

### CPU0 与 CPU1 单核自检：PASS

两颗核分别得到：

- MIDR：`0x413FC090`。
- MPIDR：CPU0=`0x80000000`，CPU1=`0x80000001`。
- 失败掩码：`0x00000000`。
- 测试状态：CPU0=`0x50415330`，CPU1=`0x50415331`。
- PMU cycle counter 在测试区间内产生非零增量。

覆盖内容：

- 整数 ALU、移位、乘法/MAC、load/store、分支与循环。
- 4 KiB OCM 多模式读写。
- CP15 标识寄存器与 PMU 周期计数器。
- SVC 与 UDF 异常处理路径。
- VFP 单精度浮点加法。
- MMU 短描述符页表和 cacheable 虚拟别名。
- L1 D-cache clean/invalidate 可见性。
- L1 I-cache invalidate 后取到已更新指令。
- `LDREX/STREX` 独占访问。
- ACTLR.SMP 与 SCU 使能。

### L1 D-cache：PASS

- 初始别名值：`0x11223344`。
- cache 写入后、clean 前物理视图仍为：`0x11223344`。
- clean 后物理视图变为：`0xA5A55A5A`。
- 物理更新并 invalidate 后别名视图变为：`0x55AA33CC`。

这组结果证明当前测试地址上的 L1 D-cache write-back、clean 和 invalidate 路径生效。

### L1 I-cache：PASS

自修改代码测试在 invalidate 前返回 `0x11`，修改并执行 I-cache 维护后返回 `0x22`，证明本测试路径上的指令缓存维护生效。

### 双核 SCU 一致性：PASS

- CPU1 观察到 CPU0 的 cache 写入。
- CPU1 回写 `0x55AA6699`，CPU0 能观察到该值。
- 两核最终状态均 PASS，失败掩码均为 0。

### PL Fabric BIST 收尾复核：PASS

- 最终值：`0xB101FFF0`。
- 期望值：`0xB101FFF0`。
- 标记：`FABRIC_BIST_HARDWARE_PASS|1`。

这证明 PS 自检及恢复流程未破坏当前易失性的 PL Fabric BIST 配置和状态。

## PL310 L2 结果：控制面通过，数据通路未证实

读回值：

- Cache ID：`0x410000C8`。
- Cache Type：`0x9E300300`。
- 初始 Control：`0x00000000`。
- 初始 Aux Control：`0x02060000`。
- 测试期间 Control：`0x00000001`。
- 测试期间 Aux Control：`0x02160000`。
- Debug Control：`0x00000004`。
- Event Control：`0x00000001`。
- Event Counter 0 Configuration：`0x0000000C`，配置为 data read request。
- Event Counter 1 Configuration：`0x00000008`，配置为 data read hit。
- OCM 流量后的 request/hit：均为 `0x00000000`。
- 清理后 Control/Aux Control：恢复为 `0x00000000` / `0x02060000`。

CPU 在 L2 打开期间仍正确完成 256 次 OCM cacheable-alias 读取，但 PL310 没有记录请求或命中。结合所有配置回读正确，最合理的硬件路径解释是当前 OCM 流量没有进入 PL310。此项状态记为 **INCONCLUSIVE**，不是 FAIL。

PL310 事件计数器寄存器、事件编码及控制位依据 [Arm CoreLink Level 2 Cache Controller L2C-310 Technical Reference Manual](https://documentation-service.arm.com/static/5e8e1b2b88295d1e18d360cf?token=)；Cortex-A9 的 CP15、缓存和多核机制依据 [Arm Cortex-A9 Technical Reference Manual](https://documentation-service.arm.com/static/5e7e23ffb471823cb9de5920?token=)。

## 测试夹具修正记录

下列问题均已修正并重新验证，不属于硬件故障：

1. 首次批处理参数顺序错误曾覆盖 Tcl 文件；增加扩展名和输出路径保护。
2. UDF handler 最初返回 `lr-4`，导致重复进入 UDF；修正为从异常返回地址继续。
3. CP15 MIDR 判定掩码最初错误；修正后两核均通过。
4. SCU 初值为 `0x2`，尚未使能；测试显式设置 SCU enable 和 ACTLR.SMP。
5. CPU1 首轮看到了 CPU0 遗留的 cache line；改单核测试前同时复位两核，并在结束时 clean/invalidate。
6. CPU 直接访问 PL310 控制地址发生 Data Abort；改由 JTAG DAP 访问 PL310，CPU 只生成测试流量。
7. XSDB 批处理可能不传播 Tcl 失败退出码；包装器增加 `SELFTEST_PASS|0` 日志检查并返回非零。
8. `rst -cores -start` 被调试器 Reset Vector Catch 暂停；恢复脚本增加逐核 `con`，最终两核均为 `Running`。

## 证据

硬件日志根目录：`artifacts/fpga/xc7z045_ps_selftest/20260722_0754/hardware/`

- CPU0：`cpu0_selftest_retry2.log`
- CPU1：`cpu1_selftest_retry2.log`
- 双核一致性：`dual_core_coherency.log`
- L2 初始状态：`l2_status_before.log`
- L2 最终诊断：`l2_cache_selftest_dap_retry2.log`
- APU 最终恢复：`apu_restore_run_retry1.log`
- PL BIST 最终复核：`fabric_bist_final.log`

主要资源守卫记录：

- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_080036_d11e0bc4.jsonl`
- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_080223_3c5e6ce9.jsonl`
- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_080245_10badb3d.jsonl`
- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_081551_372b0c3a.jsonl`
- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_081726_423b39d8.jsonl`
- `D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260722_081750_9f192bf2.jsonl`

## 未覆盖与下一步

- 未做 Cortex-A9 全指令集穷举，也未覆盖全部 NEON、GIC 中断/异常优先级、性能计数器事件和所有 CP15 组合。
- L2 数据通路仍需一次受控 DDR 测试；必须先明确 DDR 地址范围、初始化状态、备份/恢复方法并取得硬件门禁确认。
- 未测试 DDR 控制器/PHY、BootROM/启动介质、PS 外设、以太网、USB、CAN/SPI/I2C/SRPWM 等实际协议链路。
- 未测试外部 IO 动态时序或电气特性；这是本轮明确排除项。
- 当前结果证明的是本次样片、当前电压温度和当前 JTAG 路径下的抽样功能，不等于整颗芯片全部晶体管或全部资源的穷尽验证。
