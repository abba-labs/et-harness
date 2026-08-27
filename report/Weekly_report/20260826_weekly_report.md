# Et_Automated_Testing_Platform 周报

日期：2026-08-26

项目整体状态：框架公共能力已经形成稳定基线，ET6801 FPGA IP 功能闭环持续进行。

当前目标：基于当前 Registry、各 IP 最近有效 Formal HIL 和独立手动诊断，准确整理非 PASS Case，为后续修复策略提供可复核输入。

## 一、基础功能设施

1. PC 与固件通信框架（已完成）
   - ET-Frame、命令分发、超时控制、错误恢复和证据采集链路已经建立。
   - 固件执行原子 IP 命令，PC Case 负责配置、激励、观测和最终断言。

2. PC 与固件分层（已形成稳定基线）
   - PC 公共层、IP Driver、Case、Capability/Profile 和仪器接口职责已经分离。
   - 固件 Application、Framework、Service、Wrap 与 Chip Driver 边界已经建立；新增 IP 不应修改无关 IP 或稳定公共层。

3. Agent 规则治理（已形成稳定基线）
   - Task Context 能将任务路由到对应 Rxxx 权威规则，并限制允许修改的目录。
   - 周报统一遵循 `R003_weekly_report_authoring.md`，FAIL、SKIP、未执行和手动诊断不得混写。

4. 一键运行与报告输出（已可用）
   - 已支持环境检查、固件编译、bitfile/BootROM/PFLASH 操作、PC Case 执行和 Excel 报告生成。
   - 原始证据归档到 `artifacts/runs/`，生成报告归档到 `artifacts/reports/`。

5. 固件手动诊断（已建立）
   - 手动诊断与正式自动化测试隔离，用于复现 FAIL 或验证 SKIP 的前置条件。
   - 手动结果只补充根因分析，不直接改写 Formal Case 的 PASS、FAIL 或 SKIP。

## 二、IP 梳理与测试

### 2.1 当前总体情况

当前正式 Registry 共注册 188 个 IP Case；Framework Communication 另有 1 个公共 Case，不计入下表。

| IP | 当前Case总数 | PASS | FAIL | SKIP | NOT_EXECUTED | 统计说明 |
|---|---:|---:|---:|---:|---:|---|
| UART | 33 | 30 | 0 | 3 | 0 | 最近一次有效全量 Formal HIL |
| DMA | 28 | 28 | 0 | 0 | 0 | 最近一次有效全量 Formal HIL |
| CRC | 24 | 22 | 2 | 0 | 0 | 最近一次有效全量 Formal HIL |
| AES | 26 | 25 | 1 | 0 | 0 | 最近一次有效全量 Formal HIL |
| CORDIC | 24 | 7 | 1 | 0 | 16 | 当前文档登记的定向 Formal HIL |
| STIMER | 16 | 0 | 1 | 0 | 15 | 重构后仅完成 1 个定向 Formal Case |
| WDG | 14 | 10 | 1 | 3 | 0 | 全量 HIL 与后续 Debug Halt 定向 HIL 合并到 Case 级状态 |
| FMAC | 23 | 21 | 2 | 0 | 0 | 当前文档登记的 Formal HIL |
| 合计 | 188 | 143 | 8 | 6 | 31 | 多批次证据汇总，不代表当前 HEAD 的一次全量回归 |

说明：

- 当前 HEAD 为 `192c59aa02db2fa9afe5ee25f37efce71f84e957`；不同 IP 的有效证据来自不同 Source Revision，不能把上表描述为当前 HEAD 的一次全量 PASS。
- CORDIC 和 STIMER 的当前代码晚于其旧全量结果，因此未被当前定向 HIL 覆盖的 Case 计为 `NOT_EXECUTED`，没有沿用旧 PASS/SKIP 冒充当前结果。
- WDG 的 `wdg_p3_001` 在全量 HIL 中曾因缺少 Debugger 绑定而 SKIP，后续 Targeted HIL 已 PASS，因此当前 Case 级状态不再把它计入 SKIP。
- 2026-08-26 独立手动诊断共执行 15 项，只用于补充根因定位；其中对 FMAC、CRC 等 Case 得到的新现象，必须通过 Formal Case 复跑后才能改变上表状态。

### 2.2 当前 FAIL Case

#### FAIL Case `crc_p1_011`：CRC FIFO Threshold 生效边界

测试目的：

验证 CRC FIFO 未达到 Threshold 时计算结果保持不变，达到 Threshold 后开始消费输入并更新 `RESULT.CRC`。

测试Feature：

1. `CRC.FIFO_TRHD.CRC_FIFO_TRHD(bit3:0)`阈值配置。
2. Threshold 前后 `CRC.RESULT.CRC(bit31:0)`更新时机。
3. Threshold 测试过程中 `CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`保持未溢出。

测试方法：

1. 复位并初始化 ET6801 CRC0，配置 CRC32、多项式 `0x04C11DB7`、初值 `0xFFFFFFFF`和 Byte Swap。
2. 配置`CRC.FIFO_TRHD.CRC_FIFO_TRHD(bit3:0)=5`。
3. 经 CPU 路径连续写入 5 个 `0x12345678`，分别在写入前、第 4 次写入后和第 5 次写入后读取`CRC.RESULT.CRC(bit31:0)`。
4. 期望前 4 次写入尚未达到 Threshold，Result 保持不变；第 5 次写入达到 Threshold 后 Result 更新。
5. 同时读取`CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`，确认本 Case 没有被 FIFO Overflow 干扰。

失败现象：

- 写入前`CRC.RESULT.CRC=0xBD3A64DC`。
- 第 4 次写入后`CRC.RESULT.CRC=0xAD37D056`，已经提前变化；期望仍为`0xBD3A64DC`。
- 第 5 次写入后仍为`0xAD37D056`，没有在 Threshold 边界再次变化。
- `CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)=0`，说明本次失败不是 FIFO Overflow 导致。

结论：CRC 数据写入和 Result 更新路径能够工作，但当前 Formal Case 观察到的更新时机与`FIFO_TRHD=5`预期不一致。独立手动诊断曾得到 PASS，说明 Formal 与手动刺激时序存在差异；在对齐两条执行路径并复跑前，Formal 状态保持 FAIL。

#### FAIL Case `crc_p1_012`：CRC FIFO Overflow 与恢复

测试目的：

验证 CPU 快速连续写入导致 CRC FIFO Overflow 时，硬件能置位 Overflow 状态，并在复位恢复后继续得到正确 CRC。

测试Feature：

1. `CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`自然置位。
2. Overflow 后 CRC 模块复位恢复。
3. 恢复后的 CRC32 计算结果正确。

测试方法：

1. 复位并初始化 ET6801 CRC0，配置 CRC32、多项式`0x04C11DB7`、初值`0xFFFFFFFF`和 Byte Swap。
2. 配置`CRC.FIFO_TRHD.CRC_FIFO_TRHD(bit3:0)=1`，清除历史 Overflow 状态。
3. Formal Case 通过 CPU 连续写入 7 个`0x12345678`；独立手动诊断进一步采用紧凑 For 循环直接写入 64 个数据字。
4. 读取`CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`，期望快速写入后由 0 变为 1。
5. 通过 CRG 复位 CRC0，输入字节`01 02 03 04 05 06 07 08`，检查恢复后 CRC 是否等于`0x140B8DD8`。

失败现象：

- Formal Case 写入 7 个数据字后，`CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)=0`，期望为 1。
- 独立手动诊断连续写入 64 个数据字后，`CRC.RESULT.CRC=0x2F7ADCFC`，但`CRC.FIFO_OVF.CRC_FIFO_OVF_RPT(bit0)`仍为 0。
- CRG 复位后恢复计算正常，实际 CRC 与期望值均为`0x140B8DD8`。

结论：CRC 复位恢复和恢复后计算功能正常；当前 ET6801 FPGA 实现中，CPU 快速写入仍未使`FIFO_OVF(bit0)`置位。同事已确认当前 FPGA 的 FIFO_OVF 功能存在问题，Silicon 结果仍需独立验证。

#### FAIL Case `aes_p1_009`：AES Output Conflict IRQ

测试目的：

验证上一块 AES 输出尚未读取时再次启动新的加密输入，硬件能产生 Output Conflict Raw、Status 和中断投递。

测试Feature：

1. `AES.INT_RAW_RPT.OUTPUT_CONFLICT(bit0)`自然置位。
2. `AES.INT_STATUS_RPT.OUTPUT_CONFLICT(bit0)`在使能且解除屏蔽后置位。
3. AES ISR 对 Output Conflict 的 latch 和 event count 记录。
4. `AES.INT_CLR.OUTPUT_CONFLICT(bit0)`清除恢复。

测试方法：

1. 复位并初始化 ET6801 AES0，配置 AES-128、ECB、Encrypt、Big Endian，数据长度设置为 32 Byte。
2. 写入 128-bit Key，清除历史 IRQ；配置`AES.INT_EN.bit0=1`、`AES.INT_MASK.bit0=0`。
3. 经 CPU Register 路径写入第一个 16 Byte Block，但不读取对应输出。
4. 立即写入第二个 16 Byte Block，尝试在旧输出未消费时制造 Output Conflict。
5. 读取`AES.INT_RAW_RPT.bit0`、`AES.INT_STATUS_RPT.bit0`、Service latch 和 event count；期望四项均反映一次新事件。

失败现象：

- 两个输入 Block 均已通过测试接口提交，输入路径没有返回配置或传输错误。
- `AES.INT_RAW_RPT.OUTPUT_CONFLICT(bit0)=0`，期望为 1。
- `AES.INT_STATUS_RPT.OUTPUT_CONFLICT(bit0)=0`，期望为 1。
- Service latched 为 0，event count 增量为 0。
- 独立手动固件采用相同方向刺激后，Raw 和 Status 仍为 0。

结论：AES 输入链路和 IRQ 读取链路具备其他错误源的有效对照，但当前刺激未产生 Output Conflict。权威触发条件尚未闭合，暂时不能确定是硬件 Feature 故障，还是测试刺激与真实触发条件不匹配。

#### FAIL Case `cordic_p1_003`：CORDIC ARCTAN Scale=7 精度

测试目的：

验证 CORDIC 在 Scale 0～7 下执行固定点 ARCTAN 时，结果符合 Scale 补偿公式和批准的精度预算。

测试Feature：

1. `CORDIC.CORDIC_CTRL0.CORDIC_SCALE(bit7:5)`配置与 Scale 隔离。
2. 固定点 ARCTAN 输入、输出补偿和 Raw 结果。
3. `COMPLETE`状态置位及清除。

测试方法：

1. 复位并初始化 ET6801 CORDIC0，配置 Fixed、Polling 工作模式。
2. 对 Scale 0～7 逐项写入`CORDIC.CORDIC_CTRL0.CORDIC_SCALE(bit7:5)`，每个节点使用相同逻辑输入和 ARCTAN 函数。
3. 对 Scale=7 输入 Raw 值`0x40000000`，等待`COMPLETE`后读取硬件结果。
4. 按当前执行语义计算 Golden Raw 和误差，使用现有统一预算`0x00000216`判定。
5. 清除`COMPLETE`并确认状态恢复，排除上一节点残留影响。

失败现象：

- Scale=7 硬件结果为`0x007EB700`，Golden Raw 为`0x007EBA14`。
- Raw 差值为`0x00000314`，大于当前预算`0x00000216`。
- 换算误差约为`1.4751e-4`，超过当前统一阈值`1.0e-4`。
- `COMPLETE`置位和清除正常，失败点只在 Scale=7 精度判据。

结论：CORDIC Scale 配置、计算完成和状态清除链路正常；Scale=7 结果超过当前统一预算。由于 ET6801 各 Scale 的权威精度包络尚未取得，暂时不能确定是硬件 Feature 故障，还是当前预算不适用于 Scale=7。

#### FAIL Case `stimer_p2_003`：STIMER Debug Halt Pause

测试目的：

验证 Cortex-M7 被 Debugger Halt 时，STIMER 的 PAUSE 模式停止计数，而 RUN_FREE 模式继续计数。

测试Feature：

1. `STIMER0.STM_SET.STM_CPUHALT_MODE_R(bit7)=0`的 PAUSE 行为。
2. `STIMER0.STM_SET.STM_CPUHALT_MODE_R(bit7)=1`的 RUN_FREE 行为。
3. Debugger Halt 期间`STIMER0.COUNT`计数增量对比。

测试方法：

1. 复位并初始化 ET6801 STIMER0，配置 Free-run、Prescaler=1、Period=`0xFFFFFFFF`。
2. 配置`STM_CPUHALT_MODE_R(bit7)=0`，读取 Halt 前 Counter，由 J-Link Halt Cortex-M7，恢复后读取 Counter。
3. 配置`STM_CPUHALT_MODE_R(bit7)=1`，重复相同 Halt 和 Counter 采样。
4. 使用 PC 单调时钟记录两次真实 Halt 时间；期望 PAUSE 增量不超过 RUN_FREE 增量的 10%。

失败现象：

- PAUSE 轮 Counter 从`0x0009757B`增加到`0x00CA6818`，增量为`0x00C0F29D`，Halt 时间约`0.484 s`。
- RUN_FREE 轮 Counter 从`0x000928B2`增加到`0x00AFFF03`，增量为`0x00A6D651`，Halt 时间约`0.420 s`。
- PAUSE 增量没有接近 0，反而与 RUN_FREE 同量级，超过允许上限。
- 独立手动诊断得到相同方向：两种模式下 Counter 都继续推进。

结论：STIMER 自由运行计数正常，但当前 FPGA 中 Debug Halt 的 PAUSE 行为未生效。需要确认 Cortex-M7 Halt 信号到 STIMER 的 RTL 路径和 bitfile 实现，Silicon 仍需独立验证。

#### FAIL Case `wdg_p2_001`：WDG 时钟分频与 Counter 速率

测试目的：

验证 CRG 的 WDG 时钟源和 Divider 配置能真实改变 WDG Counter 的递减速率。

测试Feature：

1. `CRG.PLLCLK_CFG3.CRG_WDG0_SEL(bit0)`时钟源选择。
2. `CRG.PLLCLK_CFG3.CRG_WDG0_STB(bit6:1)`Divider 配置与读回。
3. `WDG0.COUNTER`在 Divider=/1 和 Divider=/2 下的实际递减速率比例。

测试方法：

1. 复位并初始化 ET6801 WDG0，保存原时钟配置，关闭 WDG 和历史 Timeout IRQ。
2. 选择 APB1 时钟源，分别配置`CRG_WDG0_STB(bit6:1)=0`和`=1`，对应预期 /1 与 /2。
3. 每个 Divider 使用相同 Reload 值启动 WDG0，读取两次`WDG0.COUNTER`，用 PC 单调时钟计算递减速率。
4. 两种 Divider 交错采样并取中位数，要求 /1 速率与 /2 速率的比值至少为 1.5。
5. 每次配置后读取 CRG Source/Divider，确认写入和读回一致。

失败现象：

- CRG Source 和 Divider 读回均与配置一致。
- Divider=0 的 Counter 中位速率约为`12,924,720 counts/s`。
- Divider=1 的 Counter 中位速率约为`12,415,681 counts/s`。
- 实际速率比约为`1.041`，低于期望下限`1.5`；两种 Divider 的 Counter 速率基本相同。

结论：CRG 配置写入和读回路径正常，但 WDG0 Counter 的实际时基没有按 Divider 变化。当前证据指向 FPGA WDG 时钟路径或 Divider 映射尚未闭合，不能只依据读回值判为功能正常。

#### FAIL Case `fmac_p1_006`：FMAC Float 转 Q15 钳位与 Overflow 清除

测试目的：

验证 Float 输入超出 Q15 范围时，FMAC 能正确钳位输出、置位 Overflow，并在后续正常输入后按规定清除状态。

测试Feature：

1. Float 转 Q15 正、负越界钳位。
2. `FMAC.SR.FLOAT2FIXED_OVF_RPT(bit12)`自然置位。
3. 正常输入解除越界条件后的 Overflow W1C 清除。

测试方法：

1. 每轮通过 CRG 复位 ET6801 FMAC，配置单抽头 0.5 FIR。
2. 配置`FMAC.CR.FLOAT2FIXED_IN_SEL(bit17)=1`，通过`FMAC.PARAM.FUNC(bit26:24)`选择处理功能并由`ENABLE(bit31)`启动。
3. 经`FMAC.FIFO_DATA`分别输入 Float `+2.0`和`-2.0`，检查 Q15 输出及`FMAC.SR.FLOAT2FIXED_OVF_RPT(bit12)`。
4. 旧 Formal Case 在越界条件仍存在时立即执行清除；修正版手动诊断先输入正常值`0.25`，再执行 W1C 并回读 bit12。

失败现象：

- 旧 Formal Case 中，正、负越界输出分别为`16383`和`-16384`，钳位正确，bit12 能稳定置位。
- 旧 Formal Case 立即清除后 bit12 仍为 1，因此记录为 FAIL。
- 数字设计说明必须先输入一个不溢出的数据，硬件当前错误条件消失后才能软件清除。
- 修正版独立手动诊断按“越界输入 → `0.25`正常输入 → W1C”执行后已 PASS，但修正版 Formal Case 尚未复跑。

结论：Float 转 Q15 钳位和 Overflow 置位正常；旧 Formal FAIL 由清除刺激顺序不符合当前硬件语义导致。手动诊断已验证修正方向，必须复跑 Formal Case 后才能把当前状态改为 PASS。

#### FAIL Case `fmac_p1_010`：FMAC Output Offset Negative 状态清除

测试目的：

验证 FMAC Output Offset 对数值的影响、负结果状态置位及其软件清除路径。

测试Feature：

1. `FMAC.OUT_CR.OFT(bit15:0)`正 Offset 数值作用。
2. `FMAC.SR.ADD_OFT_IS_NEG_RPT(bit11)`自然置位。
3. Negative 状态 W1C 清除和模块恢复。

测试方法：

1. 通过 CRG 复位 ET6801 FMAC，配置 SAT16 输出和单抽头 FIR。
2. 先配置`FMAC.OUT_CR.OFT(bit15:0)=0x0000`建立基线，再配置`0x3000`验证正 Offset 输出。
3. 输入负数样本触发`FMAC.SR.ADD_OFT_IS_NEG_RPT(bit11)`。
4. Formal 路径调用公共状态清除接口；独立手动固件分别执行`FMAC.CR.CLR`、向`FMAC.SR.bit11`写 0、向 bit11 写 1并回读。
5. 最后通过 CRG 复位 FMAC，验证模块可恢复到默认状态。

失败现象：

- 零 Offset 输出为 0，正 Offset 输出为 4096，数值路径正常。
- 负输入后`FMAC.SR.ADD_OFT_IS_NEG_RPT(bit11)=1`，状态置位正常。
- Formal 公共清除路径未清除 bit11，因此 Case FAIL。
- 独立手动固件证明：`FMAC.CR.CLR`和向 SR 写 0均无效；向`FMAC.SR.bit11`写 1可清除。

结论：Output Offset 数值和 Negative 状态置位正常，硬件 W1C 清除也可工作；当前失败点是公共 Chip Driver/Wrap 选择了错误清除语义，修正接口并复跑 Formal Case 后再更新结果。

### 2.3 当前 SKIP Case

#### SKIP Case `uart_p1_008`

测试Feature：UART Framing Error 状态和 Line Error IRQ。

测试方法：

1. 使用 ET6801 UART1 作为接收端：RX 为 J25.3、TX 为 J25.5；使用 ET6801 UART2 作为发送端：RX 为 J30.3、TX 为 J30.5。
2. 当前交叉连接为 UART1 TX → UART2 RX、UART2 TX → UART1 RX，并共地。
3. 计划将 UART1 配置为 8 Data Bits、2 Stop Bits，将 UART2 配置为 8 Data Bits、1 Stop Bit；这里的“失配帧”是发送端只输出 1 个停止位，而接收端要求检查 2 个停止位。
4. UART2 向 UART1 发送数据，读取 UART1 `LSR.FE(bit3)`、Line Error IRQ 和恢复后的正常收发结果。

测试现象：

- Formal Case 在确定性激励能力门禁阶段停止，未配置失配帧，也未发送硬件激励。
- 独立手动诊断发送`55 AA 00 FF`后，UART1 `LSR=0x61`、`FE(bit3)=0`、`IIR=0x00`，普通 TX/RX 交叉连接没有稳定制造 Framing Error。

SKIP原因：

- 当前板上只有普通 UART1/UART2 TX/RX 交叉连接，停止位失配不能确定性地把第二停止位采样点拉低，无法形成可重复的 Framing Error 激励和可靠自动化判据。

#### SKIP Case `uart_p1_012`

测试Feature：UART Busy Detect IRQ 和错误后恢复。

测试方法：

1. 初始化 ET6801 UART1，保持 FIFO 和正常发送路径开启。
2. 连续发送数据，在`UART1.USR.BUSY(bit0)=1`期间修改受保护的 LCR 配置，制造 Busy Detect。
3. 读取`UART1.IIR.IID(bit3:0)`，期望 Busy Detect 对应 IID=7；随后恢复 LCR 并执行正常收发。

测试现象：

- Formal Case 完成有界触发尝试，但观察窗口内没有形成稳定 Busy 状态，因此主动 SKIP。
- 独立手动诊断共尝试 256 次，其中发送路径接受 43 Byte；全程未观察到`USR.BUSY(bit0)=1`。
- 最终`IIR=0xC1`、`IID=1`，没有得到 Busy Detect IID=7；恢复收发能够通过。

SKIP原因：

- 当前 CPU/FPGA 执行速度和轮询时序无法稳定命中“UART 正在发送且软件同时修改 LCR”的窄触发窗口。现有证据只说明刺激条件未建立，不能据此判定 Busy Detect 硬件失败。

#### SKIP Case `uart_p3_009`

测试Feature：UART Direct FIFO Access。

测试方法：

1. 计划检查`UART1.CPR.FIFO_ACCESS(bit9)`是否声明 Direct FIFO 能力。
2. 若支持，则配置`UART1.FAR.FAR(bit0)=1`，暂停 TX 路径，向发送 FIFO 写入`0x5A`并从 TFR 读回。
3. 通过 RFW 向接收 FIFO 注入`0xA5`，再从 RX 路径读出，并在退出 Direct FIFO 模式后验证普通收发恢复。

测试现象：

- Runtime 读取到`UART1.CPR.FIFO_ACCESS(bit9)=0`，Formal Case 在 Capability 门禁阶段停止。
- 未写`FAR`，未执行 Direct FIFO 读写和数据注入。
- 独立手动诊断调用 Driver 后返回`DRV_INVALID=3`，与硬件未声明该能力一致。

SKIP原因：

- 当前 ET6801 FPGA UART 实例没有实现或没有发布 Direct FIFO Access 能力；该 Case 对当前目标不适用，不能通过强行访问未支持寄存器路径伪造覆盖。

#### SKIP Case `wdg_p0_004`

测试Feature：WDG 自然超时触发整芯片复位，并在重启后读取持久 Reset Record。

测试方法：

1. 计划初始化 ET6801 WDG0，配置 Reset Enable 和安全 Reload 值。
2. 启动 WDG0 后停止喂狗，等待自然超时导致 UART 会话断开和目标重新启动。
3. PC 重新连接后读取新 Session 和 SYSC 持久 WDG Reset Record，确认复位来源。
4. 清除记录并复读，确认记录清除路径。

测试现象：

- Formal Case 在 Runtime Capability 门禁阶段停止。
- 未配置 WDG0、未启动自然超时，也没有执行系统复位刺激。

SKIP原因：

- 当前 FPGA Runtime 未发布`RESET_OUTPUT`和`PERSISTENT_RECORDS`能力，且当前 bitfile 没有闭合 WDG 系统复位输出和跨重启记录映射；缺少安全恢复链路时不得执行破坏性复位 Case。

#### SKIP Case `wdg_p1_003`

测试Feature：WDG 两种 Work Mode 的 IRQ/Reset 轮次行为。

测试方法：

1. 计划配置 WDG0 `WORK_MODE=0`，验证第一轮自然超时产生 IRQ、第二轮产生系统 Reset。
2. 计划配置`WORK_MODE=1`，验证同一轮同时发出 IRQ 和 Reset 请求。
3. 每次系统复位后由 PC 重连，读取持久 Interrupt/Reset Record，避免要求 ISR 必须抢在 Reset 前执行。

测试现象：

- Formal Case 在 Runtime Capability 门禁阶段停止。
- 未写 WDG0 Work Mode、未启动自然超时，也未执行断线重连和持久记录读取。

SKIP原因：

- 当前 FPGA Runtime 缺少`RESET_OUTPUT`、`WORK_MODE`、`INTERRUPTS`和`PERSISTENT_RECORDS`的完整执行映射，无法安全区分两种轮次模式并形成跨重启证据链。

#### SKIP Case `wdg_p1_004`

测试Feature：WDG 模块复位清除 Enable、Counter 和运行状态，并允许重新配置。

测试方法：

1. 计划初始化并启动 ET6801 WDG0，读取复位前 Enable 和 Counter。
2. 通过 WDG 所属 CRG Module Reset 路径复位 WDG0。
3. 读取复位后的 Enable、Counter 和默认配置，期望 Enable=0且 Counter 回到默认状态。
4. 重新配置并启动 WDG0，验证模块可恢复工作。

测试现象：

- Formal Case 因 Runtime 未发布`MODULE_RESET`而在 Capability 门禁阶段 SKIP，未执行硬件复位刺激。
- 后续独立手动诊断实际执行模块复位后，WDG0 仍保持 Enable，Counter 继续递减，没有回到复位状态。

SKIP原因：

- 当前 Formal Runtime 没有可审核的 WDG Module Reset Execution Mapping。手动现象提示现有 CRG 路由或 FPGA 实现仍有问题，但在映射闭合并进入 Formal 链路前，不能把手动诊断直接改写为 Formal FAIL。

### 2.4 当前未执行和待闭环项

- `cordic_p2_001`：当前代码定义了 CORDIC DMA 工作模式 Case，但 ET6801 CORDIC DMAMUX Request 和 Endpoint 路由尚未形成经过审核的 Execution Mapping；当前状态为`NOT_EXECUTED`，不是 SKIP。
- STIMER 当前重构后只正式执行了`stimer_p2_003`。`stimer_p1_001`的新内部 Divider 比例 Case，以及其余 14 个 Case 都需要按当前代码重新执行；旧全量运行中的 PASS/SKIP 没有直接升级为当前结果。
- `fmac_p1_006`修正版手动诊断已 PASS，`fmac_p1_010`已定位到公共清除接口语义；两项都需要完成规则内代码修正和 Formal HIL 复跑。
- CRC Threshold 的 Formal FAIL 与手动 PASS 存在差异，需要先对齐两条路径的复位、写入次数和读取时机，再判断硬件行为。

## 三、本周结论与下一步

1. DMA 已有 28 个 Case 的有效全量 PASS 证据；UART、CRC、AES、WDG、FMAC 仍有明确非 PASS 项需要闭环。
2. 已确认部分非 PASS 来自 Case 或软件路径：`fmac_p1_006`刺激顺序、`fmac_p1_010`状态清除接口；修复后必须走 Formal Case 复测，不能由手动结果直接改状态。
3. CRC FIFO Overflow、STIMER Debug Halt、WDG Divider 和 AES Output Conflict 仍需 RTL/bitfile 或权威触发条件支持，当前不能用弱化断言提高通过率。
4. 下一步修改策略应优先处理“已经由手动诊断证明的软件问题”，再处理“需要设计确认的硬件语义”，最后补齐 CORDIC/STIMER 当前代码的未执行 Formal 回归。

## 四、统计口径说明

1. Case 总数来自当前`IP_REGISTRY`，当前 HEAD 为`192c59aa02db2fa9afe5ee25f37efce71f84e957`。
2. UART、DMA、CRC 的主要统计采用最近一次有效全量 Formal HIL；AES、CORDIC、STIMER、WDG、FMAC 采用各自 ET6801 IP 文档登记的最近有效状态。
3. 不同 IP 的 HIL Source Revision 和 Source Dirty 状态不同，因此本周没有声明当前 HEAD 的一次全量回归 PASS，也没有计算跨批次 HIL 通过率。
4. 最近一次干净的多 IP Formal 运行位于`artifacts/runs/20260825_124336_452200_local_et6801_fpga/`，Source Revision 为`9c7b45a5a2d177bace130f0ebd1ee8d82d13c1e3`。
5. 2026-08-26 手动诊断证据位于`artifacts/runs/20260826_152840_472046_manual_et6801_all_ip_hil/manual_complete/`；它用于解释触发和软件路径，不替代 Formal Canonical Result。
6. 本周报只整理现有证据，没有执行新的硬件操作，也没有修改 Firmware、PC Case、Driver、Service 或 Wrap。
