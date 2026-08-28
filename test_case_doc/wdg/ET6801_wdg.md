# ET6801 WDG Chip Analysis & Adaptation

> 本文件只记录 ET6801 WDG 的 Hardware Truth、Driver/Capability/Execution Mapping、历史验证输入与到公共 [`wdg.md`](wdg.md) 的适配。
> 公共 Feature、Case、Oracle 与 PLAN 方法只由 `wdg.md` 定义；本文允许出现目标寄存器、物理IRQ、SDK符号和处理域事实，但不得形成第二套公共Case。
> 当前WDG已实现14个公共Formal Case；本文不把历史源码、旧日志、软件Gate或尚未完成的本轮HIL写成硬件PASS。

## 分析基线与事实裁决

| Item | Current decision |
|---|---|
| Target | ET6801 / WDG |
| Public Contract | test_case_doc/wdg/wdg.md |
| Rule baseline | 当前活动R100/R110/R120/R130/R140；PLAN Human Review使用R120统一行语法。 |
| Primary Hardware Truth | ET6801.svd；SHA256 175a585fe736ca1300045bf147330296b97d3e3dcfac2227fcc8b603f67ad61c。 |
| Current SDK | et6x_wdg.h/.c；CRG相关动作由et6x_crg.c提供。 |
| Machine Capability | pc/et_test_platform/profiles/chip_capabilities/et6801/ip/wdg.yaml。 |
| Current-target validation input | ET6801 wdg_fpga_test.c + test_wdg.c；只作为设计/缺陷证据。 |
| Current-SHA HIL | NOT_EXECUTED / NOT_VERIFIED。 |

事实冲突按以下顺序裁决：

```text
ET6801 direct SVD / target integration evidence
> current ET6801 SDK implementation facts
> current-revision ET6801 validation source
> ET3101 / ET6003 historical requirement and code
> ET60157 cross-chip lineage
```

## 第一章 Source Coverage / Source Item Trace

### 1.1 Source Coverage

| Source Domain | Locator | State | WDG命中 | 边界 |
|---|---|---|---|---|
| Source Map | project-governance/ip-analysis-sources.yaml | FOUND | 定义17个登记资料根；本轮沿既有WDG coverage继续定向核对。 | 只导航，不定义权威级别。 |
| Requirements | ET3101 / ET6003 wdg.json | FOUND | ET3101 10个TP/20个Case；ET6003 10个TP/18个Case。 | 逐项Trace；不定义target寄存器事实。 |
| ET3101 SVD | 3101/.../svd/wwdg.svd | FOUND | 跨代reload/window/mode/IRQ结构线索。 | 仅lineage。 |
| ET3101 Drivers A/B | 3101 SDK + verification DFP/Drivers | FOUND | WDG API谱系。 | 仅lineage。 |
| ET3101 FPGA | 3101 verification | FOUND | 历史刺激/Oracle设计。 | 不等于current HIL。 |
| ET3101 Tests A/B | 3101 SDK + verification DFP/Test | FOUND | 历史Unit/Functional需求。 | 弱断言不升级为Feature proof。 |
| ET6003 SVD | 6003/.../svd/wwdg.svd + wdg_cfg.svd | FOUND | 跨代WDG结构；不同模型需隔离。 | 仅lineage。 |
| ET6003 Drivers A/B | 6003 SDK + verification DFP/Drivers | FOUND | WDG Driver谱系。 | 仅lineage。 |
| ET6003 FPGA | 6003 verification | FOUND | 历史验证入口。 | 不等于target truth。 |
| ET6003 Tests A/B | 6003 SDK + verification DFP/Test | FOUND | 历史Unit/Functional需求。 | 仅测试语义。 |
| ET6801 SVD | ET6801.svd SHA256 175a585f...ad61c | FOUND / PRIMARY | WDG0/1、寄存器、IRQ、SYSC record、CPU NMI mux、CRG时基字段。 | 目标Hardware Truth。 |
| ET6801 Driver | et6x_wdg.h/.c + et6x_crg.c | FOUND | 当前动作、module reset、IRQ API、CRG时钟实现与缺陷。 | 证明软件实现，不覆盖SVD。 |
| ET6801 FPGA verification | wdg_fpga_test.c SHA256 1cecfe90...ef952a | FOUND | 29个设计Case；当前top-level仅WDG_29 active。 | Current-target validation input，不声称PASS。 |
| ET6801 Tests | test_wdg.c SHA256 3bc1c8d9...d8c24 | FOUND | 22个UnitTest意图，含reset-record clear错误。 | Historical design input。 |
| ET60157 manuals | 用户手册/寄存器手册 | FOUND / USER-ADDED | NMI低2bit lineage、Watchdog结构、时钟/record语义。 | Cross-chip only；不能覆盖ET6801 bit/domain。 |
| ET6801 BootROM bundle | 6801_bootrom_and_driver.c SHA256 31979688...21c42 | FOUND / USER-ADDED | BootROM实际使用CRG_getWDGClock计算reload并用WDG0防护。 | 证明SDK调用暴露面；不等于WDG功能HIL。 |

17个登记资料根沿既有WDG coverage均为 `FOUND`；本轮从中断开始继续扩大到目标 `NMI_SEL`、双核NMI历史Case、target CRG时基与用户新增BootROM/ET60157资料。新增资料只补充Evidence Set，不改变目标direct evidence优先级。

### 1.2 ET3101 Requirement Case Trace

| Historical Case | Requirement | Current Case | Disposition | 处置 |
|---|---|---|---|---|
| WDG_001 | 超时复位 | WDG_P0_004 | MAPPED | 真实系统reset + record + reconnect替代单纯等待。 |
| WDG_002 | 复位失能 | WDG_P1_001 | MAPPED | 关闭reset输出后观察自然IRQ与系统存活。 |
| WDG_003 | debug halt使能 | WDG_P3_001 | MERGED | 与halt失能合并为真实Debugger参数矩阵。 |
| WDG_004 | debug halt失能 | WDG_P3_001 | MERGED | 同上。 |
| WDG_005 | 喂狗测试 | WDG_P0_003 | MAPPED | counter前后 + 原剩余超时边界形成强Oracle。 |
| WDG_006 | 工作模式测试 | WDG_P1_003 | MAPPED | 两种轮次模式分开保存IRQ/Reset证据。 |
| WDG_007 | 窗口上限前喂狗 | WDG_P1_002 | MERGED | 作为early点参数。 |
| WDG_008 | 窗口内喂狗 | WDG_P1_002 | MERGED | 作为inside点参数。 |
| WDG_009 | 窗口下限后喂狗 | WDG_P1_002 | MERGED | 作为late点参数。 |
| WDG_010 | 窗口成功喂狗 | WDG_P1_002 | MERGED | 与inside/边界样本统一。 |
| WDG_011 | 写保护锁测试 | WDG_P1_005 | MAPPED | 必须增加实际CONFIG readback，不继承弱等待Oracle。 |
| WDG_012 | 模块失能测试 | WDG_P0_002 | MAPPED | 禁用后无新自然事件。 |
| WDG_013 | 重置功能测试 | WDG_P1_004 | MAPPED | 区分模块reset与系统reset。 |
| WDG_014 | 同轮IRQ+Reset | WDG_P1_003 | MAPPED | 同轮reset可能抢占普通ISR，重连后用双record闭环。 |
| WDG_015 | 首轮IRQ次轮Reset | WDG_P1_003 | MAPPED | 首轮在线IRQ + 次轮真实reset。 |
| WDG_016 | 中断屏蔽测试 | WDG_P1_006 | MAPPED | Raw/Status/Delivery分层。 |
| WDG_017 | 重置历史记录 | WDG_P0_004 / WDG_P1_007 | SPLIT | reset record与interrupt record分别验证。 |
| WDG_018 | 屏蔽中断源信号 | WDG_P1_006 | MERGED | 并入IRQ控制矩阵。 |
| WDG_MAIN | 修改WDG时钟分频 | WDG_P2_001 | MAPPED | Clock Owner + 独立时间比例Oracle。 |
| WDG_019 | 中断NMI测试 | WDG_P2_002 | MAPPED | 原Requirement无steps/expected；由current ET6801 FPGATest WDG_23/28/29补齐有效测试语义。 |

### 1.3 ET6003 Requirement Case Trace

| Historical Case | Requirement | Current Case | Disposition | 处置 |
|---|---|---|---|---|
| WDG_001 | 超时复位 | WDG_P0_004 | MAPPED | 同ET3101语义。 |
| WDG_002 | 复位失能 | WDG_P1_001 | MAPPED | 同ET3101语义。 |
| WDG_003 | debug halt使能 | WDG_P3_001 | MERGED | 与halt失能统一。 |
| WDG_004 | debug halt失能 | WDG_P3_001 | MERGED | 同上。 |
| WDG_005 | 喂狗测试 | WDG_P0_003 | MAPPED | counter + 时间边界。 |
| WDG_006 | 工作模式测试 | WDG_P1_003 | MAPPED | 两种轮次模式。 |
| WDG_007 | 窗口上限前喂狗 | WDG_P1_002 | MERGED | early。 |
| WDG_008 | 窗口内喂狗 | WDG_P1_002 | MERGED | inside。 |
| WDG_009 | 窗口下限后喂狗 | WDG_P1_002 | MERGED | late。 |
| WDG_010 | 写保护锁测试 | WDG_P1_005 | MAPPED | 配置readback。 |
| WDG_011 | 模块失能测试 | WDG_P0_002 | MAPPED | 禁用后无新事件。 |
| WDG_012 | 重置功能测试 | WDG_P1_004 | MAPPED | 模块reset恢复。 |
| WDG_013 | 同轮IRQ+Reset | WDG_P1_003 | MAPPED | 同轮持久证据。 |
| WDG_014 | 首轮IRQ次轮Reset | WDG_P1_003 | MAPPED | 两轮时序。 |
| WDG_015 | 中断屏蔽测试 | WDG_P1_006 | MAPPED | Raw/Status。 |
| WDG_016 | 重置历史记录 | WDG_P0_004 / WDG_P1_007 | SPLIT | 两种持久record分开。 |
| WDG_017 | 屏蔽中断源信号 | WDG_P1_006 | MERGED | IRQ控制矩阵。 |
| WDG_MAIN | 修改WDG时钟分频 | WDG_P2_001 | MAPPED | 时基比例。 |

ET3101 `WDG_019` 原始Requirement只有NMI名称、缺少可执行steps/expected；旧文档因此保持UNKNOWN。当前target重新分析发现ET6801 `NMI_SEL`、CPU1继承模型以及WDG_23/28/29的current-target NMI验证设计，因此NMI不再静默丢失：公共新增 `WDG_F_018 / WDG_P2_002`，但target Source bit/处理域绑定仍保持 `NEEDS_VERIFICATION`。

### 1.4 Current-target ET6801 FPGATest Trace

| Historical Case | Intent | Current Case | Disposition | Review decision |
|---|---|---|---|---|
| WDG_01 | 基础超时/时间 | WDG_P0_004 | SUPERSEDED | 旧固定delay与不可达断言由reset-aware链替代。 |
| WDG_02 | 复位输出关闭 | WDG_P1_001 | MAPPED | 自然超时但系统保持在线。 |
| WDG_03 | Halt暂停使能 | WDG_P3_001 | MERGED | 与WDG_4统一为真实Debugger矩阵。 |
| WDG_04 | Halt暂停失能 | WDG_P3_001 | MERGED | 同上。 |
| WDG_05 | 独立模式feed | WDG_P0_003 | MAPPED | 改为counter前后与独立时间Oracle。 |
| WDG_06 | 轮次work mode | WDG_P1_003 | MAPPED | 第一轮IRQ/第二轮Reset。 |
| WDG_07 | 窗口较早阶段不复位 | WDG_P1_002 | MERGED | 并入完整窗口边界矩阵。 |
| WDG_08 | 窗口低于下限feed无效 | WDG_P1_002 | MERGED | late点。 |
| WDG_09 | 窗口高于上限feed无效 | WDG_P1_002 | MERGED | early点。 |
| WDG_10 | 窗口内feed有效 | WDG_P1_002 | MERGED | inside点。 |
| WDG_11 | lock | WDG_P1_005 | MAPPED | 升级为三阶段CONFIG.READBACK。 |
| WDG_12 | disable | WDG_P0_002 | MAPPED | 禁用后状态和自然事件。 |
| WDG_13 | module reset | WDG_P1_004 | MAPPED | 模块reset与系统reset明确分层。 |
| WDG_14 | 同轮IRQ+Reset | WDG_P1_003 | MAPPED | 源码明确ISR可能来不及进入，后重启持久record作Oracle。 |
| WDG_15 | 第一轮IRQ路径 | WDG_P1_003 | MAPPED | 首轮在线IRQ。 |
| WDG_16 | reset disabled natural IRQ | WDG_P1_001 | MAPPED | 自然IRQ在线证据。 |
| WDG_17 | early-window natural IRQ | WDG_P1_002 | MERGED | 早喂自然错误事件。 |
| WDG_18 | late-window natural IRQ | WDG_P1_002 | MERGED | 晚喂自然错误事件。 |
| WDG_19 | missed-window natural IRQ | WDG_P1_002 | MERGED | 未喂超时作为窗口Case对照。 |
| WDG_20 | interrupt mask Raw/Status | WDG_P1_006 | MAPPED | 历史已检查Status=0/Raw=1，新增Delivery分层。 |
| WDG_21 | reset record | WDG_P0_004 | MAPPED | 历史FPGA直接写SYSC清；正式Case使用正确record clear API/映射。 |
| WDG_22 | interrupt record | WDG_P1_007 | MAPPED | 正式Case做目标/对照实例隔离和复读。 |
| WDG_23 | WDG timeout NMI | WDG_P2_002 | MAPPED | CPU NMI配置是跨IP Owner，target bit归属仍需Mapping。 |
| WDG_24 | WDG1复位整芯片 | WDG_P0_004 / WDG_P1_008 | SPLIT | 系统reset范围与实例归属分层。 |
| WDG_25 | WDG0复位整芯片 | WDG_P0_004 / WDG_P1_008 | SPLIT | 同上。 |
| WDG_26 | WDG0 Halt与另一实例继续 | WDG_P3_001 / WDG_P1_008 | SPLIT | Halt语义与实例隔离分层。 |
| WDG_27 | WDG1 Halt与另一实例继续 | WDG_P3_001 / WDG_P1_008 | SPLIT | 同上。 |
| WDG_28 | WDG0 NMI仅目标处理域 | WDG_P2_002 | MAPPED | target验证设计支持处理域隔离意图。 |
| WDG_29 | WDG1 NMI仅目标处理域 | WDG_P2_002 | MAPPED | 当前top-level唯一active设计入口；仍不是current-HIL PASS。 |

当前 `WDG_FPGATest()` 只实际调用 `WDG_29()`；其他函数存在只能证明设计输入，不能作为current-SHA PASS。WDG_14源码还明确写出同轮IRQ+Reset时“来不及进入ISR即复位”，因此P1_003的同轮模式不能把普通ISR event_count设为复位前必需证据。

### 1.5 Historical UnitTest质量问题

- `WDG_UT_21` 读取 reset record 后误调用 `WDG_clearWatchdogInterruptRecordStatus(WDG0)`，随后却期望 reset record 被清；这是明确的历史Case错误。
- 历史Unit/FPGA大量使用固定delay和 `ET_TC_CHECK(true,true)`，只能保存测试意图；新Case全部改为counter、Raw/Status、持久record、真实ISR、真实reset/reconnect或Debugger等强Oracle。
- Window历史刺激虽然时间实现较弱，但target验证设计稳定支持 `counter > high` 为early、`low <= counter <= high` 为合法、`counter < low` 为late；新P1_002改为直接按 `COUNTER.CURRENT` 触发，不再依赖固定毫秒。

## 第二章 ET6801 Hardware / Driver / Interrupt Analysis

### 2.1 实例与基础事实

| Item | ET6801 current |
|---|---|
| instances | wdg0 / wdg1 |
| WDG0 | base 0x40402000 / external IRQ 18 |
| WDG1 | base 0x40403000 / external IRQ 19 |
| counter/reload | 32-bit |
| window thresholds | 32-bit high/low |
| normal IRQ source | 每实例1个WDG logical source |
| persistent records | 每实例独立 reset record + interrupt record |
| clock | 每实例OSC25M或APB1；APB1 path支持 /1..64 |

### 2.2 Target WDG Register Map

| Register | Offset | Field/Width | Automation meaning |
|---|---|---|---|
| LOCK | 0x0004 | 32-bit | 仅写入unlock key后允许修改WDG受保护配置。 |
| RELOAD | 0x0008 | 32-bit RW | 超时重载值，reset=0xFFFFFFFF。 |
| CUR_VAL | 0x000C | 32-bit RO | 当前计数值。 |
| HIGH_THRESHOLD | 0x0010 | 32-bit RW | 窗口上限，reset=0xFFFFFFFF。 |
| LOW_THRESHOLD | 0x0014 | 32-bit RW | 窗口下限，reset=0。 |
| EN | 0x0018 | bit0 | 0禁用 / 1使能。 |
| RELOAD_REQ | 0x001C | bit0 self-clear | 一次喂狗请求。 |
| CTRL | 0x0020 | bit1/bit0 | HALT_EN：debug暂停；RST_EN：复位输出。 |
| MODE | 0x0024 | bit0 | 0 WINDOW / 1 INDEPENDENT。 |
| WORK_MODE | 0x0028 | bit0 | 0首轮IRQ次轮Reset / 1同轮IRQ+Reset。 |
| INT_EN | 0x002C | bit0 | WDG MISC逻辑中断使能。 |
| INT_MASK | 0x0030 | bit0 | 1=Mask。 |
| INT_FORCE_IND | 0x0034 | bit0 self-clear | 写1强制测试中断。 |
| INT_CLR | 0x0038 | bit0 self-clear | 写1清中断状态。 |
| INT_RAW_RPT | 0x003C | bit0 RO | Mask前Raw。 |
| INT_STATUS_RPT | 0x0040 | bit0 RO | Mask后有效状态。 |
| IT_RST | 0x0044 | bit0 | 集成测试复位信号；不发布为公共module-reset动作。 |

`IT_RST` 是集成测试物理信号，不等于稳定公共 `MODULE_RESET`。公共module-reset语义由当前Driver的CRG peripheral reset路径承接，并需要current-HIL证明只影响目标WDG模块。

### 2.3 中断：Raw / Status / Delivery / Record四层必须分开

| Layer | ET6801 source | Semantics | Evidence | Rule |
|---|---|---|---|---|
| Normal IRQ | wdg0 / wdg1 | 独立外部IRQ line | SVD + static Capability | 用于普通IRQ Service/ISR交付；物理IRQ号只留芯片层。 |
| Raw | INT_RAW_RPT.bit0 | Mask前 | SVD | Force或自然事件后Raw可置位。 |
| Effective | INT_STATUS_RPT.bit0 | Mask后 | SVD | Mask时可为0而Raw保持1。 |
| Enable | INT_EN.bit0 | Source enable | SVD/Driver | 与Mask分开。 |
| Mask | INT_MASK.bit0 | 1=mask | SVD/Driver | current FPGATest WDG_20明确检查Status=0/Raw=1。 |
| Force | INT_FORCE_IND.bit0 | write1 self-clear | SVD | 硬件有，current WDG SDK没有公开API。 |
| Clear | INT_CLR.bit0 | write1 self-clear | SVD/Driver | 清后需复读Raw/Status。 |
| Persistent record | SYSC.RST_REC per-instance INT_REC | W1C历史 | target SVD/Driver | 必须与实时Raw/Status/ISR分开保存。 |

由此得到的最小证据链：

```text
natural/force stimulus
→ INT_RAW_RPT
→ INT_STATUS_RPT (after enable/mask)
→ IRQ Service latch + event_count
→ SYSC persistent interrupt record
```

Force只能证明控制路径。P1_001/P1_002/P1_003/P1_007中的自然超时或窗口错误必须由自然WDG行为产生。P1_006专门验证Force/Mask/Clear；Mask时Raw可保持1而Status/Delivery被抑制，历史target WDG_20已经有这一设计证据。

### 2.4 Persistent Reset / Interrupt Record

| Semantic | Actual source | Bit | Clear | Meaning |
|---|---|---|---|---|
| WDG0 interrupt record | SYSC.RST_REC | bit6 | W1C | 看门狗0中断历史 |
| WDG1 interrupt record | SYSC.RST_REC | bit7 | W1C | 看门狗1中断历史 |
| WDG0 reset record | SYSC.RST_REC | bit2 | W1C | 看门狗0复位请求历史 |
| WDG1 reset record | SYSC.RST_REC | bit3 | W1C | 看门狗1复位请求历史 |

ET60157同名record位位置不同，原因是芯片/核布局不同；公共Feature只表达按逻辑实例区分的record，ET6801实际bit只存在于本文，严禁从跨芯片手册复制bit位置。

### 2.5 NMI：本轮从中断继续分析后的新增结论

target ET6801 direct SVD提供：CPU0 `NMI_SEL`（offset 0x002C）含 `NMI_SRC_RPT[11:8]`、`NMI_SRC_MASKED_RPT[7:4]`、`M7_NMI_MASK[3:0]`；CPU1 `derivedFrom=CPU0`，因此两个处理域都具备同结构NMI mux。写NMI mask前需要对应CPU key。

current-target FPGATest进一步给出三组验证设计：`WDG_23` 对WDG timeout配置NMI；`WDG_28` 设计为WDG0只向自身处理域交付NMI；`WDG_29` 设计为WDG1只向自身处理域交付NMI，而且当前top-level只激活WDG_29。

但direct ET6801 SVD只把NMI mux描述成“四路Source”，没有命名哪一个bit属于哪一个WDG/处理域。ET60157手册明确bit0=WDG0、bit1=WDG1，但这是cross-chip单核lineage，不能覆盖ET6801双核target。因此当前裁决为：

```text
Public stable NMI semantics: ADMITTED
ET6801 Hardware mapping: NEEDS_VERIFICATION
No guessed source bit
No cross-chip bit copy
CPU/NMI Owner controls NMI route; WDG Service only creates natural timeout
```

### 2.6 Work Mode与Reset时序

| Work mode | Target field | Expected causal chain | Case implication |
|---|---|---|---|
| ROUND1_IRQ_ROUND2_RESET | WORK_MODE=0 | 第一轮自然超时产生IRQ；第二轮自然超时产生系统Reset | P1_003首轮保存在线IRQ，第二轮必须走reset/reconnect + reset record。 |
| SAME_ROUND_IRQ_RESET | WORK_MODE=1 | 同一轮产生IRQ和Reset请求 | P1_003不能要求普通ISR一定在Reset前执行；重连后persistent interrupt+reset records是关键Oracle。 |

### 2.7 Driver / Implementation Binding

| Stable semantics | Current binding | Status / defect | Case |
|---|---|---|---|
| enable / disable / isEnabled | WDG_enableWatchdog / disable / isWatchdogEnabled | DIRECT | P0_002 |
| feed | WDG_serviceWatchdog | DIRECT；命令成功不能代替counter/event Oracle | P0_003/P1_002 |
| reload / counter | WDG_setWatchdogReloadValue / getWatchdogCounterValue | DIRECT | P0_002/P0_003 |
| window mode / thresholds | enable/disableWindowedWatchdog + setWatchdogWindowValue | DIRECT | P1_002 |
| work mode | WDG_setWatchdogWorkMode | DIRECT | P1_003 |
| reset output | WDG_setWatchdogMode | DIRECT | P0_004/P1_001/P1_003 |
| halt pause | WDG_enable/disableWatchdogInHalt | DIRECT WITH WORDING CONFLICT | P3_001 |
| lock / unlock | WDG_lock / WDG_unlock | DIRECT；完整readback缺失 | P1_005 |
| module reset | WDG_testResetModule -> CRG_resetPeripheral | TEST EXTENSION / NEEDS HW SCOPE VERIFY | P1_004 |
| IRQ enable/disable/mask/unmask/raw/status/clear | current SDK direct APIs | DIRECT | P1_001/P1_006/P1_007 |
| IRQ force | no public SDK API | TEST DRIVER EXTENSION GAP | P1_006 |
| reset / interrupt record | get/clear status APIs | DIRECT；历史UT21曾调用错clear类型 | P0_004/P1_007 |
| clock source/divider | CRG_selectWDGClockSource | CRG OWNER；setter正确写PLLCLK_CFG3 | P2_001 |
| clock getter | CRG_getWDGClock | CONFIRMED DRIVER BUG：读取PLLCLK_CFG0后套PLLCLK_CFG3 mask | P2_001 |

特别注意 `CRG_getWDGClock()`：setter使用 `PLLCLK_CFG3`，getter却先读取 `PLLCLK_CFG0` 再用 `PLLCLK_CFG3_CRG_WDGx_*` mask解释。BootROM bundle又直接用该getter计算WDG0 reload，因此这不是纯测试代码死角。P2_001在修复前禁止把getter自报频率当作Oracle。

### 2.8 Static Capability现状

当前Machine Capability只发布两个实例、`halt/rst/wwdg/wwdg_interrupt`四类通用生成Feature、base identity和IRQ；`limits/options/parameters`为空。按照R410，不能为了让WDG文档好看而手工把所有Runtime Feature镜像进Static Profile。Static/Runtime一致性由平台发现与契约门禁负责，不再作为WDG硬件Feature或Formal Case计入功能覆盖；原`WDG_F_001/WDG_P0_001`停止使用且ID不复用。

### 2.9 当前外部仪器边界

当前平台已经具备示波器、电源和万用表接口，但它们不是本IP剩余PLAN的决定性观测源：

| 计划Case | 外部仪器作用 | 不能替代的决定性资源 |
|---|---|---|
| `WDG_P0_004` / `WDG_P1_003` | 电源可作为恢复过程的安全辅助；示波器和万用表不证明系统复位来源 | 公共`target_lifecycle`已提供reset-aware断线识别、reopen/HELLO/Discover和新Session；仍需ET6801 HIL记录`RECORD.RESET` |
| `WDG_P2_001` | 示波器只有在存在已绑定外部时钟端点时才可做辅助观察；当前方案不依赖该端点 | CRG Clock Owner、WDG时基配置和独立目标侧时间Observer |
| `WDG_P2_002` | 外部仪器不能证明CPU NMI路由或处理域隔离 | CPU/NMI Route Owner、权威Source Mapping和目标处理域NMI Service |
| `WDG_P3_001` | 外部仪器不能替代CPU停核动作 | 公共`debug_controller`已提供脚本化Debugger Halt/Resume与真实时间线；仍需Bench/J-Link配置和HIL |

因此当前不因“仪器已接入”把上述Case升级为SPEC，也不新增固定通道、探头或接线。后续若Bench/Profile闭合物理端点，必须在对应执行映射中声明逻辑信号、通道、探头和安全范围；仪器结果仍只能作为辅助Evidence，不能覆盖缺失的数字Owner或会话恢复能力。

## 第三章 Stable Endpoint -> ET6801 Mapping

| Public endpoint | ET6801 actual source | Status | Note |
|---|---|---|---|
| CAPABILITY.RUNTIME | WDG Service CAPABILITIES_GET | MAPPED | Runtime稳定能力快照。 |
| CONFIG.READBACK | Driver Test Extension + WDG Wrap | MAPPED | 写保护Case决定性证据。 |
| STATE.ENABLED | EN.WWDG_EN / current getter | MAPPED | 使能状态。 |
| COUNTER.CURRENT | CUR_VAL.WWDG_CUR_VAL / current getter | MAPPED | 32-bit当前计数。 |
| IRQ_RAW.WDG | INT_RAW_RPT.bit0 | MAPPED | Mask前事实。 |
| IRQ_STATUS.WDG | INT_STATUS_RPT.bit0 | MAPPED | Mask后事实。 |
| IRQ_DELIVERY.LATCHED_SOURCE | WDG IRQ Service latch | MAPPED | 真实ISR来源。 |
| IRQ_DELIVERY.EVENT_COUNT | WDG IRQ Service counter | MAPPED | 真实交付计数。 |
| RECORD.INTERRUPT | SYSC.RST_REC target instance INT_REC | MAPPED | 持久中断记录。 |
| RECORD.RESET | SYSC.RST_REC target instance RST_REC | MAPPED | 持久复位记录。 |
| NMI_ROUTE.SOURCE_RAW | CPUx.NMI_SEL.NMI_SRC_RPT | MAPPED FIELD / SOURCE BINDING GAP | CPU Owner的NMI Source Raw。 |
| NMI_ROUTE.SOURCE_MASKED | CPUx.NMI_SEL.NMI_SRC_MASKED_RPT | MAPPED FIELD / SOURCE BINDING GAP | CPU Owner的NMI Source Masked。 |
| NMI_DELIVERY.EVENT_COUNT | CPU Owner `NMI_Handler` event_count | MAPPED | 目标处理域真实NMI交付。 |

## 第四章 Gap / Risk Registry

| Gap ID | Type | Current fact | Release condition |
|---|---|---|---|
| wdg_case_implementation_gap | CLOSED / FPGA_HIL_PARTIAL | 14个Case均已闭合；2026-08-28修复WDG测试驱动的CRG写保护事务后，P1_004手动与Formal HIL均PASS；当前结论为11 PASS / 1 FAIL / 0 SKIP / 2 NOT_EXECUTED。 | 闭合P2_001硬件问题，重跑P0_004/P1_003，并执行Silicon HIL。 |
| wdg_runtime_capability_service_gap | CLOSED | Static Capability发布生成器事实，Runtime Service已实现。 | 保持Static/Runtime重叠事实一致。 |
| wdg_semantic_capability_mapping_gap | MAPPING | limits/options/parameters为空，Runtime-only语义无机器映射。 | 通过通用Capability规则/执行映射发布，不手工伪造Static镜像。 |
| wdg_config_readback_gap | CLOSED | 隔离Test Driver Extension已提供配置readback。 | 保持P1_005以硬件readback为判据。 |
| wdg_irq_force_gap | CLOSED | 隔离Test Driver Extension已提供最小Force动作。 | Force只用于控制链，不替代自然事件。 |
| wdg_irq_service_gap | CLOSED | 公共Source级ISR latch/event_count已实现。 | 保持Raw/Status/latch/event_count分层。 |
| wdg_unmask_pending_semantics_gap | SEMANTIC | Raw在Mask期间pending后Unmask是否立即形成Delivery尚未由target direct evidence冻结。 | RTL/LRS/current-HIL冻结；P1_006不预设。 |
| wdg_target_reset_recovery_gap | FPGA_MAPPING / RERUN_REQUIRED | expected-reset lifecycle已经具备；当前FPGA bit未观察到WDG系统复位输出。RESET_OUTPUT仍按SVD硬件契约发布，不能再通过Runtime裁剪形成SKIP。 | 当前FPGA重跑P0_004/P1_003并保留真实结果；Silicon按独立证据执行。 |
| wdg_module_reset_scope_gap | CLOSED / FPGA_HIL_PASS | 发布版WDG_resetWatchdog使用legacy CRG枚举值；测试扩展已按ET6801 SRST0位位置执行，并补齐CRG unlock/reset/lock完整事务。复位后Enable=0、Counter=0xFFFFFFFF，恢复后可重新计数。 | SDK发布前修复正式Driver并删除测试扩展；Silicon继续独立验证。 |
| wdg_clock_timebase_mapping_gap | FPGA_RTL_MAPPING_GAP / HIL_FAIL | ET6801 SVD定义APB1分频编码0=/1、1=/2；PC到Service、Wrap和CRG Driver的divider链路保持原值，PLLCLK_CFG3读回也分别为0和1。2026-08-22使用最低1.5倍速率比的强Oracle复测，divider=0/1的Counter中位速率分别为12,535,775.11 count/s与12,552,841.37 count/s，实际比值0.99864，未体现分频效果。 | RTL/bit所有者确认WDG时钟源与STB分频字段是否真正接入Counter时基；修复或说明映射后重跑P2_001，并在Silicon HIL独立验证。 |
| wdg_debug_halt_control_gap | CLOSED / FPGA_HIL_PASS | 公共DebugController已从Run Config取得J-Link路径和探针配置；P3_001真实执行两轮2 s Halt，暂停使能delta=3,889,169、暂停失能delta=28,398,807，满足最大0.25比例Oracle。 | 保持Run Config注入Debugger配置并补充Silicon HIL。 |
| wdg_nmi_route_mapping_gap | SEMANTIC / FPGA_HIL_PASS | P2_002已证明自然WDG timeout产生CPU NMI与WDG IRQ双事件；SVD仍未命名四路Source到WDG实例/处理域的精确bit绑定。 | 由RTL/LRS冻结精确Source位；当前公共Case不猜测该绑定。 |
| wdg_cpu_nmi_service_gap | CLOSED / FPGA_HIL_PASS | CPU Owner首次NMI后自动全屏蔽；实测CPU event_count 0->1、Mask=0xF，同时WDG event_count 0->1、IRQ Raw=1。 | 补充Silicon HIL，不改变CPU/WDG Owner边界。 |
| wdg_historical_reset_record_clear_bug | HISTORICAL | ET6801 UnitTest WDG_UT_21读取reset record后误调用interrupt-record clear。 | 新P0_004必须调用正确reset-record clear并复读，旧行为不继承。 |

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| WDG_F_002 | SUPPORTED | EN.WWDG_EN提供使能/禁用；current Driver有enable/disable/isEnabled。 | ADAPTED | WDG_P0_002 |
| WDG_F_003 | SUPPORTED | RELOAD与CUR_VAL均为32-bit；当前Driver有set reload/get counter。 | ADAPTED | WDG_P0_002, WDG_P0_003, WDG_P2_001 |
| WDG_F_004 | SUPPORTED | RELOAD_REQ为喂狗请求且硬件自清；公共Case验证Feed。 | ADAPTED | WDG_P0_003, WDG_P1_002 |
| WDG_F_005 | SUPPORTED | MODE=0 WINDOW、1 INDEPENDENT；Driver API直接表达。 | ADAPTED | WDG_P0_003, WDG_P1_002 |
| WDG_F_006 | SUPPORTED | Early/Inside/Late区域Case已实现；counter恰好等于low/high仍缺目标侧原子Feed映射。 | MAPPING_GAP | WDG_P1_002 |
| WDG_F_007 | SUPPORTED | CTRL.RST_EN直接存在；当前FPGA未观察到系统reset，必须执行Case保留真实FAIL，不能裁剪Runtime Capability。 | NEEDS_VERIFICATION | WDG_P0_004, WDG_P1_001, WDG_P1_002, WDG_P1_003 |
| WDG_F_008 | SUPPORTED | WORK_MODE轮次语义存在；当前FPGA的reset输出行为需要由P1_003重新执行裁决。 | NEEDS_VERIFICATION | WDG_P1_003 |
| WDG_F_009 | SUPPORTED | CTRL.HALT_EN直接存在，SYSC还有每实例Halt gating；SDK英文brief与硬件语义冲突已按SVD裁决，当前FPGA真实J-Link Halt专项HIL已PASS。 | ADAPTED | WDG_P3_001 |
| WDG_F_010 | SUPPORTED | LOCK保护与配置readback已由Driver Test Extension和公共Wrap表达。 | ADAPTED | WDG_P1_005 |
| WDG_F_011 | SUPPORTED | SVD定义模块复位；测试扩展按CMSIS位位置和CRG写保护事务执行，当前FPGA手动与Formal HIL均PASS。 | ADAPTED | WDG_P1_004 |
| WDG_F_012 | SUPPORTED | INT_EN/MASK/FORCE/CLR/RAW/STATUS已由公共端点分层表达。 | ADAPTED | WDG_P1_001, WDG_P1_006 |
| WDG_F_013 | SUPPORTED | 每实例独立IRQ已由公共Service保存Source与event_count。 | ADAPTED | WDG_P1_001, WDG_P1_002, WDG_P1_003, WDG_P1_006, WDG_P1_007 |
| WDG_F_014 | SUPPORTED | SYSC.RST_REC字段存在；当前FPGA系统reset链路未通过，必须由P0_004/P1_003执行并保留真实结果。 | NEEDS_VERIFICATION | WDG_P0_004, WDG_P1_003 |
| WDG_F_015 | SUPPORTED | 目标实例interrupt record由公共端点读取/清除。 | ADAPTED | WDG_P1_001, WDG_P1_007 |
| WDG_F_016 | SUPPORTED | 两个WDG实例的配置、使能与IRQ路由由公共Case验证。 | ADAPTED | WDG_P1_008 |
| WDG_F_017 | SUPPORTED | SVD定义APB1分频编码0=/1、1=/2；当前链路与寄存器读回正确，但FPGA Counter实测速率未体现分频效果。 | MAPPING_GAP | WDG_P2_001 |
| WDG_F_018 | SUPPORTED | P2_002已在FPGA证明自然WDG timeout形成CPU NMI与WDG IRQ双证据，首次NMI后CPU Mask自动恢复为0xF；精确Source bit仍待RTL冻结。 | ADAPTED | WDG_P2_002 |

说明：`SUPPORTED`只表示direct target资料支持该Hardware Feature；Platform状态描述当前自动化链路。`NEEDS_VERIFICATION`用于证据确实不足，不得改写为“实现困难”。

# 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| WDG_P0_002 | ADAPTED | 当前FPGA HIL PASS。 |
| WDG_P0_003 | ADAPTED | 当前FPGA HIL PASS。 |
| WDG_P0_004 | NEEDS_VERIFICATION | SVD声明RESET_OUTPUT；已移除FPGA Capability屏蔽，待Formal HIL重跑。当前状态为NOT_EXECUTED，不得继续记为SKIP。 |
| WDG_P1_001 | ADAPTED | Source级IRQ Service latch/event_count与自然超时Formal Case已实现。 |
| WDG_P1_002 | ADAPTED | 当前FPGA HIL PASS；Early/Inside/Late均由COUNTER.CURRENT定位并验证自然IRQ。 |
| WDG_P1_003 | NEEDS_VERIFICATION | SVD声明RESET_OUTPUT；已移除FPGA Capability屏蔽，待Formal HIL重跑。当前状态为NOT_EXECUTED，不得继续记为SKIP。 |
| WDG_P1_004 | ADAPTED | 当前FPGA手动与Formal HIL PASS；模块复位后WDG禁用且Counter恢复默认值，随后可重新配置和计数。 |
| WDG_P1_005 | ADAPTED | LOCK/UNLOCK与完整配置readback已实现。 |
| WDG_P1_006 | ADAPTED | Force API与Source级IRQ Service已实现。 |
| WDG_P1_007 | ADAPTED | 自然IRQ与interrupt record Case已实现。 |
| WDG_P1_008 | ADAPTED | 双实例配置、使能与IRQ隔离Case已实现。 |
| WDG_P2_001 | MAPPING_GAP | <span style="color: red;"><strong>当前FPGA HIL：FAIL。CRG的Source/Divider寄存器读回正确，但divider=0/1下的Counter速率中位数不满足SVD定义的分频关系；Case保持严格判定，不得通过放宽断言掩盖硬件路径问题。</strong></span> |
| WDG_P2_002 | ADAPTED | 当前FPGA HIL PASS；CPU NMI和WDG IRQ形成双证据，CPU首次交付后自动全屏蔽。 |
| WDG_P3_001 | ADAPTED | 当前Run Config已提供可编程J-Link映射；真实Halt专项HIL为PASS，暂停使能与失能两轮Counter变化可明确区分。 |

## 第七章 Current Review Conclusion

### 7.1 本轮重构结论

1. 中断链被拆成Raw、有效Status、真实ISR Delivery和持久Record四层；Force不再冒充自然IRQ。
2. 同轮IRQ+Reset不要求普通ISR先执行；current-target源码明确存在Reset抢在ISR前的风险，重连后的interrupt/reset双record更可靠。
3. NMI从旧UNKNOWN升级为稳定公共Feature/Case；CPU Owner已提供稳定掩码、快照和向量事件计数，ET6801具体Source bit与处理域绑定仍需HIL/RTL证据，绝不复制ET60157低2bit映射。
4. reset record与interrupt record分开建模；历史UnitTest WDG_UT_21调用错clear类型的错误被显式淘汰。
5. Window验证由固定delay升级为按实际COUNTER.CURRENT定位early/inside/late，并保留自然IRQ与完整reset两级证据。
6. 真实系统reset、module reset、Debugger Halt、NMI route和Clock source均按Owner分层；WDG Service不跨IP接管CRG/CPU/Debugger。
7. P2_001通过CRG Owner的测试读回扩展避开历史getter的错误源，并使用独立PC时间比例作为速率Oracle；正式SDK getter的历史问题仍独立记录，不污染WDG公共Case。2026-08-22增强HIL证明寄存器配置生效但Counter速率未体现分频，该结果按真实FAIL保留。
8. 当前保留17个硬件Feature，14个Case均已实现；2026-08-28修复P1_004的CRG写保护事务并完成HIL后，当前结论为11 PASS / 1 FAIL / 0 SKIP / 2 NOT_EXECUTED。P2_001保留真实FAIL，P0_004/P1_003等待Formal HIL。原F001/P0_001停止使用且ID不复用。

### 7.2 当前状态

```text
WDG Public Features: 17 active (WDG_F_001 retired, ID not reused)
WDG ET_CASE_SPEC: 14 / IMPLEMENTED / CURRENT=11 PASS + 1 FAIL + 0 SKIP + 2 NOT_EXECUTED
Remaining ET_CASE_PLAN: 0
Formal Case Registry / test_wdg_p*.py: IMPLEMENTED
PC Driver / Firmware Service / Common Wrap: IMPLEMENTED
Machine Capability semantic mapping: PARTIAL
Repository-native scoped document gate: PENDING AT DOCUMENT-WRITE TIME
Current classification: 14 logical Cases / 11 PASS / 1 FAIL / 0 SKIP / 2 NOT_EXECUTED
FAIL Cases: WDG_P1_004, WDG_P2_001
NOT_EXECUTED Cases: WDG_P0_004, WDG_P1_003 / capability correction requires a fresh Formal HIL run
FAIL Reasons: P1_004 module reset leaves WDG enabled and counting; P2_001 divider readback is correct but Counter rate does not follow the SVD-defined /1 versus /2 relationship
Full HIL Evidence: artifacts/runs/20260822_093418_044103_wdg_formal_cases/tests/wdg
Full Excel Report: artifacts/reports/20260822_093429_670487_ET6801_WDG测试报告.xlsx
Strengthened P2_001 Evidence: artifacts/runs/20260822_094927_699802_wdg_formal_cases/tests/wdg
Strengthened P2_001 Report: artifacts/reports/20260822_094932_225366_ET6801_WDG测试报告.xlsx
Minimum-ratio Oracle Evidence: artifacts/runs/20260822_wdg_divider_oracle_verified/tests/wdg
Debug-Halt PASS Evidence: artifacts/runs/20260822_wdg_debug_halt_verified/tests/wdg
Previous HIL Evidence: artifacts/runs/20260821_195200_wdg_full_hil/session.json
Firmware / Registry: et6801-silicon-common-v0.1 / d7dd2c5d
Exact committed SHA FPGA HIL: NOT_PROVEN / source_revision=edfd188173e93b3a580ba1d30587795c2ca1749c and source_dirty=true
Current-SHA Silicon HIL: NOT_EXECUTED / NOT_VERIFIED
Historical Unit/FPGA source: TRACEABLE DESIGN INPUT ONLY
```

门禁结论必须来自提交后实际运行的repository-native scoped gate；本文不自报PASS。

### 7.3 2026-08-22 09:55 CST 分频证据修正

现象：旧的20 ms单轮采样曾使P2_001在相邻运行中出现PASS与FAIL波动，无法稳定裁决divider硬件效果。

操作 / 测试方法：保持同一Feature，把采样改为divider=0/1交错执行、每组四轮、每轮50 ms，并以PC单调时间计算实际Counter递减速率的中位数；Oracle不再只比较快慢方向，而是要求divider=0与divider=1的中位速率比至少达到1.5，从而排除约1%采样抖动造成的偶然PASS。同时复核PC Codec、Firmware Service、CRG Wrap与ET6801 Driver的divider传递链。

结果：每轮PLLCLK_CFG3 Source/Divider读回均正确；最低速率比Oracle复测得到divider=0和divider=1的中位速率分别为12,535,775.11 count/s和12,552,841.37 count/s，实际比值0.99864，远低于1.5，不符合SVD定义的/1与/2关系。

后续修正 / 最终结论：撤回旧的`CLOSED / FPGA_HIL_PASS`判断。当前结论为`FPGA_RTL_MAPPING_GAP / HIL_FAIL`；公共Case、PC Driver、Service、Wrap与CRG Driver参数链路不通过放宽断言或改写结果规避该问题。

关联文件 / 证据：`artifacts/runs/20260822_093418_044103_wdg_formal_cases/tests/wdg`、`artifacts/runs/20260822_094927_699802_wdg_formal_cases/tests/wdg`、`artifacts/runs/20260822_wdg_divider_oracle_verified/tests/wdg`、`artifacts/reports/20260822_094932_225366_ET6801_WDG测试报告.xlsx`。

### 7.4 2026-08-22 Debug Halt专项闭合

现象：早期独立Runner没有注入Run Config中的J-Link可执行文件和探针配置，因此`WDG_P3_001`按Bench Gap跳过；这不能用来判断硬件行为。

操作 / 测试方法：从`run_config.yaml`注入J-Link、Probe、COM12和Firmware Build ID，分别在暂停使能和暂停失能配置下执行真实2 s Debugger Halt/Resume，并读取两轮`COUNTER.CURRENT`前后值。

结果：暂停使能轮Counter delta=3,889,169，暂停失能轮delta=28,398,807；前者为后者的约13.7%，满足Case规定的不高于25%比例，专项HIL为PASS。

最终结论：原`BENCH_GAP`已经闭合，`WDG_P3_001`适配状态升级为`ADAPTED`。证据位于`artifacts/runs/20260822_wdg_debug_halt_verified/tests/wdg`；该运行来自dirty工作树，不能写成Exact-SHA PASS。

### 7.5 当前未通过测试记录

时间：2026-08-24 20:42 CST

| Case | 测试环境 | 实际硬件现象 | 已排除的软件链路问题 | 当前判定 | 闭环条件 |
|---|---|---|---|---|---|
| `WDG_P2_001` | ET6801 FPGA、PC单调时间Observer、divider=0/1交错四轮采样 | `PLLCLK_CFG3`的Source/Divider分别正确读回0和1，但Counter中位速率分别为12,535,775.11和12,552,841.37 count/s，速率比为0.99864，未体现SVD定义的/1与/2关系 | PC Codec、Firmware Service、CRG Wrap、ET6801 Driver的divider传递和寄存器读回均正确 | `FPGA_RTL_MAPPING_GAP / HIL_FAIL` | RTL/bit所有者确认WDG Counter真实时钟路径；修复或发布权威映射后重跑本Case，并在Silicon独立验证 |

本记录只描述当前dirty工作树和当前FPGA bit的行为，不代表Exact-SHA结论。禁止通过放宽1.5倍速率比Oracle、删除断言或改成SKIP关闭该问题。

2026-08-24独立固件复测得到divider=`0`和divider=`1`的配置读回均正确，但相同采样窗口内Counter增量分别为`0x0003D323`和`0x0003D2AD`，仍未体现`/1`与`/2`的速率差异，与Formal HIL结论一致。证据：`artifacts/runs/20260824_204258_094556_manual_et6801_uart_crc/manual/uart_crc.log`。

同次独立固件复测还观察到模块复位后WDG仍保持Enable，Counter继续递减；恢复配置后WDG仍可工作。2026-08-26按统一状态规则复核后，该现象判定为`WDG_P1_004`的真实FAIL；SVD已声明的`MODULE_RESET`不得再通过Runtime Capability屏蔽成SKIP。历史Formal Artifact保持原样，当前分类单独修正。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 14:24 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 14:24 CST` | `29cc76f38804cdc076d6fc604eba5c2ca1e85467` | `true` | 全量基线：`artifacts/runs/20260822_093418_044103_wdg_formal_cases/tests/wdg/`；Debugger聚焦证据沿用；P1_004手动诊断：`artifacts/runs/20260828_140446_105424_manual_et6801_diagnostics/manual/diagnostics.log`；Formal聚焦复测：`artifacts/runs/20260828_142500_wdg_targeted_after_fix/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 14 | 12 | 11 | 1 | 0 | 2 | 12 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `WDG_P0_004` | FPGA | NOT_EXECUTED | `WDG_F_007`、`WDG_F_014` / 系统复位 | 当前未执行破坏性系统复位刺激 | 当前bit没有安全的RESET_OUTPUT观测映射 | 发布安全的RESET_OUTPUT与跨重启记录映射后重测 | `artifacts/runs/20260822_093418_044103_wdg_formal_cases/tests/wdg/` |
| `WDG_P1_003` | FPGA | NOT_EXECUTED | `WDG_F_008`、`WDG_F_014` / 轮次复位 | 当前未执行两轮复位序列 | 当前bit没有安全的RESET_OUTPUT与跨重启记录映射 | 发布RESET_OUTPUT和跨重启记录映射后重测 | `artifacts/runs/20260822_093418_044103_wdg_formal_cases/tests/wdg/` |
| `WDG_P2_001` | FPGA | FAIL | `WDG_F_017` / 时钟分频 | Divider读回正确，但计数速率不随`/1`和`/2`变化；独立固件复测仍得到近似相同增量 | 当前FPGA WDG时钟路径或Divider映射未闭合 | RTL/bit确认Counter真实时钟路径后重测 | `artifacts/runs/20260824_204258_094556_manual_et6801_uart_crc/manual/uart_crc.log` |
<!-- ET_CHIP_TEST_STATUS_END -->

### 2026-08-26 12:15 CST 状态分类复核

历史Full HIL表保持原始Runner事实，不回改4个历史SKIP。按当前统一规则，只有外部物理接线、仪器或不可替代Bench拓扑缺失才允许SKIP；因此当前有效分类修正为：

| Case ID | 当前分类 | 复核结论 |
|---|---|---|
| `WDG_P0_004` | NOT_EXECUTED | 历史Capability屏蔽已删除；需重新执行系统复位Case，不能沿用SKIP。 |
| `WDG_P1_003` | NOT_EXECUTED | 历史Capability屏蔽已删除；需重新执行两轮复位Case，不能沿用SKIP。 |
| `WDG_P1_004` | FAIL | 现有手动HIL记录显示模块复位后仍Enable且Counter继续递减。 |
| `WDG_P2_001` | FAIL | Divider读回正确，但Counter速率不符合SVD的`/1`与`/2`关系。 |
| `WDG_P3_001` | PASS | 后续Targeted HIL已经闭合Debugger绑定并通过。 |

2026-08-28修正：`WDG_P1_004`失败来自测试驱动未解锁CRG写保护。补齐unlock/reset/lock事务后，手动HIL观察到Enable从1变为0、Counter恢复`0xFFFFFFFF`，Formal聚焦HIL PASS。当前汇总为11 PASS / 1 FAIL / 0 SKIP / 2 NOT_EXECUTED；P0_004/P1_003只有在重新执行后才能转成PASS或FAIL。
