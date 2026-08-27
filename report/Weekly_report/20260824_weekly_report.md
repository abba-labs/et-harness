# Et_Automated_Testing_Platform 周报

日期：2026-08-24  
项目整体进度：30%  
当前主要目标：完善通用自动化测试框架，并在 ET6801 FPGA 原型平台上逐步闭合各数字 IP 的 Feature 与 Case。

## 一、基础功能设施（90%）

1. PC、固件通信框架（100%）
   - 已完成统一 ET-Frame 二进制协议、CRC 校验、错误帧恢复、超时重试和压力测试。
   - 固件负责解析 PC 命令并执行原子操作；测试组合与最终判断由 PC Case 完成。

2. PC 端分层架构（95%）
   - 已形成 Case、IP Driver、通信、调度、能力/Profile、仪器控制和报告输出等分层。
   - 新增 IP 主要增加该 IP 的 Driver、Case、Capability 和 Fixture，不修改稳定公共层。

3. 固件端分层架构（95%）
   - 已形成 Application、Framework、Service、Wrap、Chip Driver 和资源管理分层。
   - Service 只解析命令并调用本 IP Wrap；Wrap 只调用对应 IP Driver，不包含测试组合逻辑。

4. IP 与 Case 注册管理（100%）
   - 已建立 IP 注册表和 Case 注册表，可控制参与测试的 IP、等级和具体 Case。
   - 未注册 Case 不进入正式运行集合，便于维护和阶段性裁剪。

5. 芯片能力与 Profile 隔离（90%）
   - PC Case、Driver、固件 Service 和 Wrap 均按芯片中立语义设计。
   - 芯片实例、地址、中断、时钟和执行映射等事实由 Capability、Profile、Board 配置和 Chip Driver 隔离。

6. Agent 规则治理体系（95%）
   - 已建立 Task Context 路由、Rxxx 单一权威规则、模块责任边界和变更范围检查。
   - 开发流程统一为“任务识别 → 规则路由 → 受限开发 → Diff 反查 → 自动门禁”。

7. 自动化质量门禁（90%）
   - 已覆盖代码格式、注释格式、架构边界、Case 文档同步、Capability 同步、注册表完整性和报告契约检查。
   - 已增加跨 IP 修改和公共层修改边界检查，降低已验证 IP 被后续开发交叉影响的风险。

8. 一键运行流水线（90%）
   - 已支持环境检查、固件编译、bitfile 配置、BootROM 加载、PFLASH 烧录、PC Case 运行和报告生成。
   - 硅前、硅后目标和各工具路径由统一配置文件管理，避免人工拼接命令。

9. GUI 配置工具（90%）
   - 已支持必填项标记、环境检查、编译、固件烧录、bitfile 烧录、BootROM 烧录和 PC 测试独立按钮。
   - 已增加实时日志窗口，并完成主要控件真实点击验证。

10. 测试证据与 Excel 报告（90%）
    - 报告使用稳定 `case_id` 回溯测试代码，并输出 Feature、结果和面向人的硬件观测摘要。
    - PASS、FAIL 和 SKIP 均保留结构化原始证据；Excel 报告按时间戳独立归档。

11. 测试产物目录（100%）
    - 原始运行证据统一存放在 `artifacts/runs/<run_id>/`。
    - Excel 报告统一存放在 `artifacts/reports/`，不再散落在项目外部或临时目录。

12. 代码同步工具（100%）
    - 已提供 GitHub 分支提交和公司 Git 仓库目录同步流程。
    - 同步脚本会排除缓存、构建中间文件和测试产物，避免污染正式代码仓库。

## 二、IP 梳理、FPGA 测试（35%）

### 2.1 当前总体情况

| IP | 当前Case总数 | PASS | FAIL | SKIP | HIL通过率 |
|---|---:|---:|---:|---:|---:|
| UART | 33 | 30 | 0 | 3 | 91% |
| DMA | 28 | 28 | 0 | 0 | 100% |
| CRC | 24 | 22 | 2 | 0 | 92% |
| AES | 26 | 25 | 1 | 0 | 96% |
| CORDIC | 24 | 22 | 1 | 1 | 92% |
| STIMER | 16 | 11 | 1 | 4 | 69% |
| WDG | 14 | 10 | 1 | 3 | 71% |
| 合计 | 165 | 148 | 6 | 11 | 90% |

补充进展：

- FMAC：已规划并注册 14 个 Formal Case，固件与 PC 端代码已开发；尚未完成正式真机验证，暂不计入上述 PASS/FAIL/SKIP。
- XC7Z045 配测 FPGA：JTAG、A9、DDR、L2 Cache、Fabric Logic、BRAM、DSP、MMCM，以及 J58/J59 外部 IO 回环均已通过基础验证。

### 2.2 UART（33项：30 PASS / 0 FAIL / 3 SKIP）

当前板级对测连接：

- ET6801 UART1：RX 为 J25.3，TX 为 J25.5。
- ET6801 UART2：RX 为 J30.3，TX 为 J30.5。
- 交叉连接：J25.5（UART1 TX）连接 J30.3（UART2 RX）；J30.5（UART2 TX）连接 J25.3（UART1 RX）。

#### SKIP Case `uart_p1_008`

测试 Feature：UART Framing Error 状态及 Line Error 中断。

测试方法：

1. 将 ET6801 UART1 配置为接收端，设置为 2 个停止位。
2. 将 ET6801 UART2 配置为发送端，设置为 1 个停止位。
3. UART2 通过现有交叉连线向 UART1 发送数据。这里的“失配帧”是指 UART2 在 1 个停止位后结束一帧，而 UART1 按 2 个停止位检查该帧。
4. 读取 UART1 的 Framing Error 状态及 Line Error 中断状态。
5. 将两路 UART 恢复为相同帧格式，再次收发数据，验证错误后的通信恢复能力。

测试现象：

- 本次在测试台能力门禁阶段停止；当前环境没有声明可确定性产生 Framing Error 的激励能力。
- 未执行失配帧发送，也未读取到可用于判定的 Framing Error 状态。

SKIP 原因：

- 仅通过 UART1/UART2 普通 TX/RX 交叉连接，停止位失配不能稳定、重复地制造 Framing Error，无法形成可靠自动化判据。

#### SKIP Case `uart_p1_012`

测试 Feature：UART Busy Detect 中断及清除恢复。

测试方法：

1. 初始化 ET6801 UART1，并建立正常收发基线。
2. 在 UART1 处于忙状态时尝试修改受保护的通信配置，制造 Busy Detect 条件。
3. 读取 UART1 的状态寄存器和中断识别结果，检查 Busy Detect 是否产生。
4. 清除中断并重新初始化 UART1，执行回环通信验证恢复能力。

测试现象：

- 已实际执行有界 Busy Detect 触发尝试。
- 在观察窗口内未稳定观测到 Busy Detect 状态或中断，因此没有进入后续有效断言。

SKIP 原因：

- 当前 FPGA 原型环境无法稳定进入 Busy Detect 的硬件触发条件；该前置条件未形成时不能把 Case 判为功能失败。

#### SKIP Case `uart_p3_009`

测试 Feature：UART Shadow/Direct FIFO 访问。

测试方法：

1. 初始化 ET6801 UART1，并使能 Direct FIFO 访问模式。
2. 暂停 UART1 TX 路径，向发送 FIFO 写入 `0x5A`，再读取发送 FIFO 读回接口。
3. 通过接收 FIFO 写入口注入 `0xA5`，再从 UART1 RX 路径读取该数据。
4. 关闭 Direct FIFO 模式，并执行普通 UART 收发，验证恢复能力。

测试现象：

- 运行时 Capability 未声明 `FIFO_ACCESS` 能力。
- Case 在能力门禁阶段停止，未执行 Direct FIFO 寄存器访问和数据注入。

SKIP 原因：

- 当前固件协议未对外提供 UART Direct FIFO 测试接口，PC Case 无法通过规范链路执行该 Feature。

### 2.3 DMA（28项：28 PASS / 0 FAIL / 0 SKIP）

- 已完成 M2M、M2P、P2M、P2P、Channel、优先级、Reload、Handshake、中断、错误恢复、时钟复位恢复等当前规划 Feature。
- UART1/UART2 外设链路 Case 使用动态 Capability 和 Execution Mapping，不在公共 Case 中写死芯片地址、DMA Request ID 或 Channel。

### 2.4 CRC（24项：22 PASS / 2 FAIL / 0 SKIP）

#### FAIL Case `crc_p1_011`

测试 Feature：CRC FIFO Threshold 触发时机。

测试方法：

1. 初始化 ET6801 CRC0，选择 CRC32，并把 FIFO Threshold 配置为 5。
2. 连续写入 5 个 `0x12345678` 数据字。
3. 分别读取写入前、第 4 次写入后和第 5 次写入后的 CRC Result。
4. 判断 CRC 硬件是否严格在达到 Threshold 后才处理 FIFO 数据。

问题现象：

- CRC Result 在第 4 次写入后已经发生变化。
- 第 5 次写入后 CRC Result 未继续变化，与 Threshold=5 的预期触发时机不一致。

问题原因分析：

- PC Driver、Firmware Service 和 Wrap 的配置及读回链路正常。
- 当前 FPGA 中 CRC FIFO Threshold 的实际行为与 SVD/历史测试预期不一致，需要结合 RTL 定义进一步确认。

#### FAIL Case `crc_p1_012`

测试 Feature：CRC FIFO Overflow 状态及错误后恢复。

测试方法：

1. 初始化 ET6801 CRC0，将 FIFO Threshold 配置为 1。
2. 连续快速写入 7 个数据字，尝试使输入速度超过 CRC FIFO 消费速度。
3. 读取 CRC FIFO Overflow 状态。
4. 重新初始化 CRC0，再执行标准 CRC 计算，验证错误后的恢复能力。

问题现象：

- 连续写入后，CRC FIFO Overflow 状态仍为 `false`。
- 未出现文档预期的 Overflow 硬件状态。

问题原因分析：

- 正常 CRC 计算与恢复路径可工作，未发现公共通信或 Service/Wrap 调用错误。
- 当前 FPGA 的 FIFO 深度、处理速率或 Overflow 实现可能与历史预期不同，需要 RTL 定义确认。

### 2.5 AES（26项：25 PASS / 1 FAIL / 0 SKIP）

#### FAIL Case `aes_p1_009`

测试 Feature：AES Output Conflict 自然中断及中断投递。

测试方法：

1. 初始化 ET6801 AES0，配置 AES-128、ECB 加密和 32 字节输入长度。
2. 写入第一个 16 字节数据块并等待输出就绪，但暂不读取该输出。
3. 在前一个输出仍未读取时写入第二个 16 字节数据块，制造输出冲突条件。
4. 读取 AES IRQ RAW、有效 STATUS、固件 ISR 锁存值和中断事件计数。

问题现象：

- Output Conflict 对应的 RAW、STATUS、锁存值和事件计数均未置位。

问题原因分析：

- AES 其他自然中断可以正常到达，说明公共 IRQ 注册、NVIC 和事件记录链路有效。
- 当前写入顺序可能未形成 RTL 定义的 Output Conflict 条件，或该中断位在当前 FPGA 版本中未实现，需要结合 RTL 时序定义确认。

### 2.6 CORDIC（24项：22 PASS / 1 FAIL / 1 SKIP）

#### FAIL Case `cordic_p1_003`

测试 Feature：CORDIC Scale 对 ARCTAN 和 SINCOS 运算结果的影响。

测试方法：

1. 初始化 ET6801 CORDIC0，并遍历规定的 Scale 配置。
2. 对受 Scale 影响的 ARCTAN 路径输入固定向量，读取硬件输出并与 PC 独立数学结果比较。
3. 对不应受 Scale 影响的 SINCOS 路径执行对照测试。
4. 对每个 Scale 使用既定误差阈值判断精度是否满足要求。

问题现象：

- Scale=7 时，ARCTAN 结果误差稳定约为 `1.475e-4`，超过当前 `1e-4` 阈值。
- 重复测试结果一致；其他已覆盖 Scale 和 SINCOS 对照路径正常。

问题原因分析：

- 当前尚未取得 ET6801 ARCTAN 各 Scale 的正式精度预算。
- 现有证据只能证明当前阈值不适用于该点，暂不能直接判定 RTL 缺陷，也不能为提高通过率而自行放宽公共阈值。

#### SKIP Case `cordic_p2_001`

测试 Feature：CORDIC DMA 输入、输出请求及 DMA 运算结果一致性。

测试方法：

1. 使用 ET6801 CORDIC0 的 CPU 读写路径计算固定输入，建立硬件基线。
2. 通过 DMA 把输入数据送入 CORDIC0，并通过另一 DMA 路径读取运算结果。
3. 同时比较 DMA 结果、CPU 路径结果和 PC 独立数学结果。

测试现象：

- Execution Mapping 中没有 CORDIC0 的 DMA Request、方向和端点映射。
- Case 在映射门禁阶段停止，未配置 DMA Channel，也未启动 CORDIC DMA 运算。

SKIP 原因：

- 当前缺少经过审核的 ET6801 CORDIC DMA Execution Mapping；为避免猜测 DMA Request ID，保持 SKIP。

### 2.7 STIMER（16项：11 PASS / 1 FAIL / 4 SKIP）

#### FAIL Case `stimer_p2_003`

测试 Feature：STIMER 在 CPU Debug Halt 时的 Pause 和 Run-Free 行为。

测试方法：

1. 初始化 ET6801 STIMER0，并配置 Debug Pause 模式。
2. 通过 J-Link 暂停 ET6801 CPU，读取暂停前后的 STIMER0 Count，判断计数是否停止。
3. 将 STIMER0 改为 Run-Free 模式，再次暂停 CPU并读取 Count，判断计数是否继续。

问题现象：

- Pause 模式下，CPU Halt 期间 STIMER0 仍继续计数。
- Run-Free 模式下，CPU Halt 期间 STIMER0 同样继续计数。

问题原因分析：

- Wrap 配置和寄存器读回已检查，模式位可以正确写入。
- 当前 FPGA 中 CPU Debug Halt 到 STIMER0 Pause 控制的硬件链路未体现预期差异，需要确认 RTL 连接和实现。

#### SKIP Case `stimer_p1_001`

测试 Feature：STIMER Prescaler 分频与实际计数速率。

测试方法：

1. 对 ET6801 STIMER0 配置多个 Prescaler 分频值。
2. 在相同外部时间窗口内读取各配置下的 Count 增量。
3. 使用 XC7Z045、逻辑分析仪或示波器提供独立时间参考，判断计数速率是否符合分频比。

测试现象：

- 已发现并初始化 STIMER0，但测试台无法解析名为 `stimer_reference` 的独立时间观测通道。
- 未执行分频矩阵和计数速率测量。

SKIP 原因：

- 当前 Bench Profile 尚未配置独立时间参考设备及其连接关系，仅靠 PC 等待时间不能作为精度测试依据。

#### SKIP Case `stimer_p1_008`

测试 Feature：STIMER Overflow/Compare 输出脉宽及对应中断。

测试方法：

1. 配置 ET6801 STIMER0 Compare0 和多个输出脉宽。
2. 启动 STIMER0，检查 Compare/Overflow 中断是否到达。
3. 使用 XC7Z045或示波器捕获 STIMER0 输出，并测量实际脉宽。

测试现象：

- 当前测试台没有配置 `stimer_output` 物理观测通道。
- Case 在仪器连接门禁阶段停止，未启动脉宽测试。

SKIP 原因：

- 缺少 STIMER0 输出到配测设备或示波器的接线及 Bench Profile 绑定。

#### SKIP Case `stimer_p2_002`

测试 Feature：STIMER Emergency Capture 输入捕获。

测试方法：

1. 启动 ET6801 STIMER0 并读取当前 Count。
2. 由外部配测设备向 STIMER0 Emergency 输入发送一个确定脉冲。
3. 读取 Capture 值，判断其是否位于脉冲发生前后的 Count 区间内。

测试现象：

- 运行时 Capability 未声明 Emergency Capture，当前也没有外部脉冲路由。
- 未执行脉冲激励和 Capture 读取。

SKIP 原因：

- 当前固件命令和 ET6801 FPGA 板级路由均未提供 Emergency Capture 测试能力。

#### SKIP Case `stimer_p3_001`

测试 Feature：STIMER 长时间计数、周期、Overflow 和中断稳定性。

测试方法：

1. 对 ET6801 STIMER0 配置多组 Prescaler 和 Period。
2. 长时间运行并记录 Count、Overflow 次数和中断事件。
3. 使用独立时间参考和外部输出观测校验长期累计误差及事件数量。

测试现象：

- 准备 `stimer_reference` 独立时间通道时失败。
- Case 未进入长时间运行和外部观测阶段。

SKIP 原因：

- 当前 Bench Profile 尚未提供独立时间参考和 STIMER0 输出观测通道。

### 2.8 WDG（14项：10 PASS / 1 FAIL / 3 SKIP）

#### FAIL Case `wdg_p2_001`

测试 Feature：WDG 时钟源、分频配置及 Counter 实际计数速率。

测试方法：

1. 将 ET6801 WDG0 配置为 APB1 时钟、Divider=0，在固定 PC 时间窗口内读取 Counter 变化量。
2. 将 Divider 改为 1，在相同时间窗口内再次读取 Counter 变化量。
3. 读取 CRG 配置确认分频值写入成功，并比较两组实际计数速率。

问题现象：

- Divider 配置读回正确。
- Divider=0 与 Divider=1 的计数速率几乎相同，测得比值约为 `0.998`，没有体现预期的 `/1` 与 `/2` 差异。

问题原因分析：

- CRG 配置写入和读回链路正常，但 WDG0 实际计数时钟没有随分频配置变化。
- 需要确认当前 FPGA 中 WDG0 时钟选择和 Divider 到计数器的 RTL 连接。

#### SKIP Case `wdg_p0_004`

测试 Feature：WDG System Reset 输出及复位原因记录。

测试方法：

1. 将 ET6801 WDG0 配置为超时后输出系统复位。
2. 停止喂狗，等待 ET6801 复位并观察通信断开。
3. 重新连接后读取复位原因记录，确认复位由 WDG0 触发。

测试现象：

- 运行时 Capability 未声明 `RESET_OUTPUT` 和 `PERSISTENT_RECORDS`。
- Case 在能力门禁阶段停止，未启动 WDG0 系统复位。

SKIP 原因：

- 当前 FPGA bitfile 未把 WDG0 Reset 输出接入 ET6801 系统复位链路，固件也未提供跨复位持久记录能力。

#### SKIP Case `wdg_p1_003`

测试 Feature：WDG 两轮超时中的第一轮中断、第二轮复位及跨复位记录。

测试方法：

1. 配置 ET6801 WDG0 第一轮超时产生中断，第二轮超时产生系统复位。
2. 停止喂狗，在线观察第一轮 WDG0 中断事件。
3. 继续等待第二轮复位，观察串口断开和重新连接。
4. 重连后读取持久记录，核对中断和复位顺序。

测试现象：

- 运行时 Capability 不具备 Reset Output、两轮工作模式和 Persistent Records。
- Case 在能力门禁阶段停止，未执行第一轮中断和第二轮复位。

SKIP 原因：

- 当前 FPGA 与固件无法闭合“中断 → 系统复位 → 重连 → 记录读取”的完整证据链。

#### SKIP Case `wdg_p1_004`

测试 Feature：WDG Module Reset 及模块状态恢复。

测试方法：

1. 将 ET6801 WDG0 配置为非默认状态并启动计数。
2. 对 WDG0 执行模块级复位。
3. 检查控制状态是否恢复默认，并重新配置 WDG0 验证可继续工作。

测试现象：

- 运行时 Capability 未声明 `MODULE_RESET`。
- Case 在能力门禁阶段停止，未执行模块复位。

SKIP 原因：

- 当前固件协议尚未提供 WDG 模块级复位命令，PC Case 无法通过规范链路执行该 Feature。

## 三、本周结论与下一步

1. 平台基础框架、规则治理、一键流水线、GUI 和报告链路已基本形成，可以继续按 IP 扩展。
2. DMA 已完成当前规划 Case 的全部真机闭环；UART 的剩余项主要受可重复错误激励和 Direct FIFO 接口限制。
3. CRC、AES、CORDIC、STIMER、WDG 的 6 个 FAIL 均保留真实硬件现象，没有通过放宽断言或改为 SKIP 来提高通过率。
4. 下一步优先完成 FMAC 真机验证，并结合 RTL/设计定义闭合 CRC FIFO、AES Output Conflict、CORDIC Scale、STIMER Debug Pause 和 WDG Clock Divider 问题。
5. 对依赖外部观测或复位链路的 SKIP Case，后续补充 Bench Profile、板级接线和固件能力后再转入正式执行。

## 四、统计口径说明

- Case 总数来自当前正式 IP Case 规划和代码注册集合。
- PASS、FAIL、SKIP 来自最近一次有效的 ET6801 FPGA 真机证据，统计截止到 2026-08-22。
- 当前源码基线为 `a45dee76c2eefab1e69c14003ac3def01f2a7c89`；2026-08-22 的HIL Manifest没有记录可核对的源码Revision，因此本周结果不能声明为该SHA的exact-SHA回归。
- 当前代码可能晚于上述真机证据；新增但尚未进行 HIL 的 FMAC 不计入 PASS、FAIL 或 SKIP。
- 表中“HIL通过率”按`PASS / (PASS + FAIL + SKIP)`计算；项目、基础设施和IP梳理进度属于当前稳定工作项范围下的管理估算，不使用HIL通过率替代。
- SKIP 分为两类：`uart_p1_012` 已实际尝试硬件激励但未形成确定触发条件；其余多数 Case 在 Capability、Execution Mapping 或 Bench 连接门禁阶段停止，未伪造硬件执行结果。
