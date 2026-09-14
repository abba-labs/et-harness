# CAN P1/P2 重构复核：正确性缺陷、剩余复杂度与下一轮整改

> 被审查提交：`d0c751f47b1d98e021758c7d96b70e620149cf12`  
> 对照提交：`d6b91b65fd96c04f80e87e954c463be48607288b`  
> 仓库与分支：`abba-labs/et-harness` / `chatgpt_review`  
> 复核结论：**REQUEST_CHANGES，不能按“硬件流程、覆盖与判据 100% 保持”验收。**  
> 本轮只提交审核文档与入口索引，不修改运行代码。本文不是新硬件测试报告。

## 1. 给负责人和开发 Agent 的结论

这次有真实的改进：`CanDriver.reset()` 已形成简短入口，很多 Case 的清理闭包、手工记录及交错逻辑确实减少了。但存在两类彼此独立的问题：

1. **可读性尚未达标。** 不少长 Case 仍然直接展开大量配置对象、位置参数、等待预算和多阶段分支，不能只添加三个段落注释就称为极简。
2. **正确性出现回退。** 已确认 ECC 重复触发漏 unmask、普通 IRQ Case 未建立捕获、DMA Case 调用与实际接口不符；另外有观察窗口、判据、证据和清理被直接删除。这些不是硬件环境不确定导致的推测，而是新源码与真实相邻接口/原流程之间的具体差异。

因此，不能把净删除 3,387 行、210 项 Driver 单元测试或 148 个收集节点等同于“27 条 Case 的运行行为已验证”。先修正确性，再继续瘦身；不恢复旧版冗长表达，也不推翻用户已认可的显式 reset 方向。

### 1.1 本轮审查及验证边界

已核对实时分支指向被审查 SHA、26 个变更文件清单、004/005/006 工件、Driver/固件新增复位差异，并重点阅读 ECC、普通 IRQ、March、Timeout、DMU 收发/事件、Watchdog、多实例 RAM、部分格式/过滤 Case，以及相邻的 SYSCTRL/Resource/CAN Model、Fixture 和报告代码。

这是一轮**源码审查、代表性函数行数统计和离线签名/字段核对**，不是对全部 27 个 Case 的完整动态回归。没有在本环境重跑仓库所称的 210 项测试，没有执行 Keil、实际固件 Native 测试或 HIL。下载完整 clone 的环境网络不可用，因而不把离线抽取检查写成真实仓库集成通过。

文中的确定性接口错误不需要 MCU 就能确认。硬件后果由当前固件语义推导，并明确与实际 HIL 结果区分。

## 2. 长不长：使用同一口径统计，而不是只看文件净减少

以下为从固定提交读取并逐字抽取的五个完整函数，经 Python AST 统计的结果。范围仅是这五个样本，不能外推成全量 27 个的分布。

- 函数跨度：从 `def` 到最后语句，包含正文空行、注释，不含前置装饰器。
- 正文代码行：不含函数签名、空行、独立注释；多行参数仍按实际物理行计数。
- 不能用分号、多动作同一行或极长表达式美化数字。

| Case | 函数跨度 | 正文代码行 | 主要判断 |
| --- | ---: | ---: | --- |
| P2_003 ECC 中断链 | 25 | 15 | 长度已接近目标，但漏了关键动作和覆盖，不能验收 |
| P1_011 IRQ 线路与清除 | 71 | 57 | 配置仍展开，且捕获链被删断；先恢复原语义 |
| P1_016 Message RAM March | 83 | 70 | 有真实算法复杂度，纯数据准备仍可外移，不能隐藏算法或重置连续现场 |
| P1_014 Timeout 四源 | 138 | 123 | 三阶段分派、计数/FIFO 联动和等待混合；有设计复杂度，也有表达问题 |
| P2_001 DMU TX/RX | 136 | 121 | 两套 DMA 配置、路由和观测多；同时存在确定性 API 错误 |

005 将 P2_001 新行数列成 94，与本提交函数跨度 136 不一致；其他几条样本的跨度与其表格一致。这说明自检表需要按实际提交统一生成，不能手工填旧数字。005 正文声称普通 15～35 行、复杂 40～60 行，也与自身表格中大量 70～140 行不相符。

### 2.1 为什么还长

**可以去掉的复杂度：** 反复构造相同配置、无语义的位置参数、纯布局/向量计算、手写剩余预算传播、阶段字符串分派、结果格式化、对象角色不清。

**必须保留的复杂度：** 两种 Pattern 和 DLC 矩阵、FIFO 满/覆盖/回绕的连续状态、IRQ 原始状态与 ISR 记录的区别、DMA 先接收后发送及真实终态、March 的访问顺序、Timeout 的启用/禁用对照、Watchdog 的有界观察和恢复。

结论不是“硬件复杂就不优化”，也不是“所有东西必须硬塞进 20 行”。应当先提纯输入数据、按真实动作线性表达，再判断是否能拆成独立目的。需要连续现场的流程不能为了行数拆成各自 reset 的独立测试。

## 3. 必须先修的运行与覆盖问题

### F01：ECC 第二次触发漏掉解除屏蔽，且选择性清除没有被证明【阻断】

文件：`pc/et_test_platform/test_cases/can/test_can_p2_ecc.py`，`test_can_p2_003_ecc_interrupt_chain`。

**当前实际顺序：** 第一次 `ecc_force(source)` → `ecc_mask_set(source, False)` → 等第一次回调 → `ecc_clear(source)` → 第二次 `ecc_force(source)` → 直接等待第二次回调。

**原因：** 当前固件 `can_ecc_callback()` 捕获后会再次屏蔽已发生的源；`ecc_force()` 不解除屏蔽。旧 Case 在每次首次/重复投递前都有 unmask，新 Case 第二轮遗漏了它。

**后果：** 在当前固件按既定行为工作的情况下，第二轮不会按预期产生新回调，等待第二次事件将超时；不能称这条 Case 已保持原中断流程。

另外：

- 清除后只断言 `state.status == NONE` 不足以证明 Raw 被清除，因为屏蔽时 Status 本来就可能为零。
- 新代码只 Force 目标源，没有建立另一源的 Raw，对“只清目标、不清对照源”不再有检测能力。
- 100 ms 屏蔽观察窗口、回调实例归属、首次 Raw/Status 记录及第二次诊断字段等检查被减少。
- 从全实例改成所选单实例是用户授权的范围调整；上述同实例检查的丢失不是该授权的含义。

**修复：**

1. 第二次 Force 后、等待前恢复 `ecc_mask_set(source, False)`。
2. 恢复明确的 Raw 读回和对照源验证；保持第一次/第二次事件同一 generation，不在中间 reset 或重开 capture。
3. 屏蔽、选择性清除可以按 003 规定拆成短小的独立目的 Case，但需同步新 ID/契约/选择矩阵，不能只是删除原检查。未完成拆分前不宣称原 Feature 完整覆盖。
4. 保留实际实例、源、计数及异常字段判定。仅为这几项多出数行，比用弱断言凑 20 行正确。

**验证：** 真实固件回调的自动屏蔽行为；两种源的重复投递；注入“清除无效/清错源”时必须失败；完整负向窗口。采集命令序列不能仅用始终返回成功的 Mock。

### F02：P1 IRQ Case 根本没有启动 IRQ Capture【阻断】

文件：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`test_can_p1_011_irq_lines_and_clear`。

当前函数调用 `irq_line_select_set()`、`irq_mask_set(sources, False)` 和 `irq_clear()`，随后传输并读取 `irq_line_events_get()`；函数内没有 `irq_capture_start()` 或 `irq_capture_pending()`。

**关键语义：** `irq_mask_set` 的参数名是 `enabled`，传 False 是关闭源使能。`irq_line_events_get()` 读取固件 ISR 锁存数组，不是直接读取硬件路由寄存器。reset 会清除历史记录；没有绑定并使能捕获，就没有本轮 ISR 来填这组数据。

**后果：** 即使 CAN 帧收发正确，也不能得到预期的线路事件；现有 TX 线路断言没有建立必要前提。这同时丢掉了原 RX/TX 路由、Mask、W1C 对照和恢复的部分证据。

**修复：**

- 对照基线恢复捕获建立、来源使能和 Line0/Line1 归属的准确顺序。
- 要保留旧 Raw 的阶段使用已有 Pending 捕获语义，不随意改成会清 Raw 的 Start。
- 两个源的路由和选择性 Clear 均逐项保留；不能仅增加任意 capture 调用让 TX 单条断言变绿。
- 外部模式必须保留真实对端证据并关闭盒子；内部回环不需要外部设备。

**验证：** 三种模式 × 两个线路参数均实际执行函数；验证未绑定、错误线路、源关闭、清错源会被发现。6 个参数能收集不是这些动作执行过。

### F03：DMU Case 出现真实接口、映射键和模型字段不匹配【阻断】

文件：`pc/et_test_platform/test_cases/can/test_can_p2_dmu.py`。

| 新代码 | 当前实际定义 | 结果/正确修复方向 |
| --- | --- | --- |
| `sysctrl.configure_dma_request(controller, interface, request_id)` | V1 还需要 `endpoint, instance, address`；V2 才接收 controller/interface/request_id | 新调用缺少必填参数。恢复 `configure_dma_request_v2`，不要改旧 Driver 来迁就错误 Case |
| `requests[f"rx{fifo}"]` | ET6801 每个 CAN 映射只有 `tx`、`rx`；RX0/RX1/Event 由 DMU 选择 | `rx0/rx1` 不存在。恢复公共 RX 请求并显式选择 DMU 接收源 |
| `dmu_rx_image_decode(seq, raw)` | 第一个参数是 FIFO 号，不是循环帧序号 | 第二帧或 RX1 参数会解码错误 FIFO 的布局。传入 `fifo` |
| `counters.tx_count/rx0_count/rx1_count/event_count` | 模型是 `tx_enqueued/rx0_dequeued/rx1_dequeued/tx_event_dequeued/modulus` | 会访问不存在的字段。恢复真实模型字段及非目标队列检查 |
| `destination.slice(offset, event_bytes)` | ResourceRef 只有 handle、size、address | 没有 slice 方法。使用已有 `resource_driver.read(destination, size=event_bytes, offset=offset)` |
| `decoded.details.event` | CanDmuEventImage 为 `event` 与 `transferred_timestamp` | 应按真实模型读取 `decoded.event`，不能臆造嵌套 |
| Event 断言改为 `TRANSMITTED` | 原流程 automatic_retry=False，对应基线精确 Expected 为 `TRANSMITTED_AFTER_CANCEL` | 配置未变却把 Expected 从类型 2 改为 1，属于硬件判据改变，应恢复基线 |

前三个运行错误互相遮挡：程序可能先在错误路由调用处失败，因此后面没有实际触达。不能以修掉第一个异常就认定该 Case 已恢复。

本轮离线将源码真实签名用于 `inspect.signature(...).bind(...)`，三参数 V1 调用明确得到 `missing a required argument: 'instance'`；同时核对了真实 dataclass 字段、ResourceRef 无 slice、映射没有 rx0/rx1。该检查不发送任何硬件请求，也不冒充仓库 210 项单元测试。

**进一步必须核对：** 每帧前后的 DMA deconfigure、通道配置接受条件、真实完成与错误状态、地址推进、FIFO 索引、DMU 错误和两帧数据是否都保留。原断言不仅有 payload 相等；本次重写删掉了一批这些检查。

**验证：** 用真实 SYSCTRL/DMA/Resource/CAN 类及其数据模型执行每个 Case 正文，在底层通信边界替换硬件；禁止万能 MagicMock 接受任意方法、参数和属性。修复后再做包含真实固件的 CAN DMA 定点复测。

### F04：Watchdog 的 100 ms 观察窗口和计时证明被删除【高】

文件：`pc/et_test_platform/test_cases/can/test_can_p2_watchdog.py`，`test_can_p2_010_ram_watchdog`。

基线明确在开启/关闭阶段观察至少 100 ms，并保存 STIMER 计数来证明非零窗口。新函数启动了 STIMER，但没有保留这段持续观察和计数读回，只在搬运完成后读取一次 pending/event。

**后果：** 负向“规定窗口内没有 WDI”变成“这一次采样没有 WDI”；开启后的延迟事件也可能来不及观察。无证据证明新版与原硬件测试思想等价。保留了三组 limit/rounds，不等于保留了三个阶段的全部判据。

**修复：** 恢复窗口、计时事实、逐阶段 WDI/ISR/错误检查及退出恢复；对照原来的 8、8、1 帧刺激量，不能减少轮数。控制/等待实现可以收敛，但必须返回实际观测，不由 Driver 生成通过结论。

**验证：** 观察到窗口内延迟触发能够失败；不够 100 ms 或 STIMER 未推进不能当成完整负向通过；不要用固定一次快照替代。

### F05：收尾不是被简化，而是部分被删掉或吞错【高】

文件：`test_cases/can/conftest.py`，以及新 P1 IRQ / P2 DMU / Watchdog 等函数。

新增 `can0` Fixture 的退出只有 ECC/普通 IRQ capture stop，并对两次操作分别使用 `except Exception: pass`。这会隐去真实停止/解绑失败。

多个组合 Case 仍然请求 `can_support` 而不请求 `can0`，例如 P2_001/P2_002/P2_010。因此它们连这个不完整的 `can0` finalizer 也不会执行。新外部 IRQ Case 打开盒子后也没有对应的 finally/注册收尾。

**后果：**

- 正文断言成功但 teardown 失败，可能仍被当作成功；与 005 所称“保留双错误”相反。
- DMA、请求路由、计时器或外部激励在中途异常后可能继续活动，污染下一 Case。
- 下一条 `can.reset()` 清资源池不能代替停止上一条仍工作的 DMA。资源池是公共的，不归某个 CAN 独占。

**修复：**

- 保留用户要求的 Case 开头显式 reset；固定异常收尾继续放在运行收尾层，不重新往每条 Case 塞闭包。
- 对实际参与的设备，在首次获得资源前注册对应有限收尾；不借用一个未被依赖的 Fixture 假装全体覆盖。
- 不吞清理异常；保留 call 与 teardown 的两阶段结果。恢复失败则停止后续硬件 Case，不能靠扩大 SKIP 或重试掩盖。
- 组合测试先停止 DMA/外部激励，释放实际路由，再处置 CAN 和公共资源池；不能把一个普通 CAN reset 扩大成随意复位全部 IP。

**验证：** setup 中途失败、正文失败、清理失败、正文和清理同时失败四条路径；验证后续 Case 不会在未恢复状态下继续开始。

### F06：can0 的 Driver 与 support 可能指向不同实例【高】

新增 Fixture：当连接配置不是实例 0 时，通过 `CanDriver(can_support.can._target, 0)` 创建 CAN0，随后却无条件把原 `can_support` 挂到 `driver.support`。

**后果：** 当连接选择 CAN1 时，命令发给 CAN0，而 handle、RAM 区域、时钟/限制或外部引脚来自 CAN1。用户要求“显式选一个实例”不等于偷偷覆盖连接选择，更不等于混用两个实例的元数据。

**修复：** Driver、逻辑 handle、能力、RAM 区域和引脚绑定从同一个显式选择派生。`can0` 必须明确对应 CAN0；所选实例不可用或映射冲突时给出配置错误，不能静默 fallback。Fixture 提供对象和只读配置，不向 Driver 动态塞 Case Support 或让 Case 读取 Driver 私有 `_target`。

**验证：** 连接选择 CAN0、CAN1、缺失实例和外部引脚不匹配四类；确认请求中的 instance_id 与全部配置事实一致。

### F07：原始证据被删除，FAIL-only 备注也没有真正落地【高】

新 ECC、DMU、Watchdog 等正文去掉了 `record_property/record_observation`。这本来应当配套转移到记录层，但本提交的 CanDriver 只增加 reset 及导入，Fixture 也没有添加读取记录适配。变更清单没有报告层或运行记录层的相应改动。

同时，`results/case_report.py` 仍按原逻辑处理 PASS/FAIL 备注。`_human_report_note()` 对缺少所需字段会报错，`_aggregate_report_status()` 在失败结果缺少硬件观测时会转为 RUN_ERROR。因此不能用“Case 不写备注”代替“报告层仅显示失败备注”，更不能称 PASS 原始证据已经完整保留。

**后果：** 丢失输入、实际硬件读回和首次失败现场，报告可能缺数据或生成失败。具体呈现由 canonical 状态和报告模板决定，不能一概宣称全部变成同一种状态。

**修复：**

- 原始事实在统一记录层保存，Case 不展开 JSON/证据列表；记录的仅是实际调用参数和真实返回，不发额外改变现场的读命令。
- 保留首个失败前的快照；不是清理后再读一次冒充失败现场。
- FAIL-only 仅改变报告展示；PASS 原始结果与异常信息仍保留。
- 先完成数据去向与真实模板端到端验证，再删除最后一个旧记录入口；不要生成占位 evidence 或硬编码通过值。
- 公共报告改动独立批次，范围与既有授权明确，不与其它 IP 无关重构混入。

### F08：单实例要求没有完全落实，多实例隔离不能改名后假装等价【中】

`test_can_p2_004_instance_ram_isolation` 仍使用 `can_instance_supports` 并枚举全部实例；Fixture 也仍要求至少两个实例。005 写“保留双实例”不等于实际限制到两个，当前代码按声明集合运行。

这条测试目的本身就是“多实例隔离”。不能在只保留一个实例后仍声称证明隔离，也不能以“保留功能”为由忽略用户明确的单实例范围。

**处理：** 按用户已确认方向将这项标记为本轮范围外，并同步执行选择与覆盖声明，保留历史原实现供追溯；若未来需要测隔离，再单独作为明确多实例专项。不要未经确认把它改成单实例 RAM 测试并沿用旧覆盖说明；不要用默认 SKIP 冒充符合单实例要求。

### F09：reset 入口方向正确，但“原子”和“纯软件上下文”描述不准确【设计与验证】

PC 端的三行 reset 是值得保留的变化：CRG → CONTEXT_RESET → Resource reset。它是**三个顺序请求、前一步失败不执行下一步**，不是具备回滚能力的原子事务。只收到第三条之前的异常时，硬件可能已经部分复位，不能把状态当成完全未变。

新 `handle_context_reset()` 调用原 `stop_irq_capture/stop_ecc_capture/stop_dmu_capture` 后再清事件；这些 stop 函数不仅解绑，还会执行来源 disable/mask 等 CAN 硬件动作。由此不能未经核对就称其只清软件、完全不改变 CRG 复位后的寄存器值。

**整改边界：**

- 不退回每 Case 全源 Mask/Disable/Clear 的旧冗余写法。
- 在固件明确区分“IP 已经 CRG 复位后的上下文释放”与“运行中正常 stop”；NVIC pending、回调解绑等仍由已有 IRQ Manager 处理，不能直接 memset Manager。
- 验证有/无旧 IRQ/ECC/DMU 会话以及解绑故障时的结果；确认基线不会随上条会话不同而出现未声明差异。
- 保留 Source/Context/Generation 的真实语义，不删掉必要的 IRQ 释放或边界检查。
- 补真实 C/Manager 边界测试和失败停止测试。新加入的 reset golden 测试只检查三个成功请求，不证明所有清理状态都正确。

### F10：自检报告中的“PASS”和“100% 保持”缺少对应证据【高】

006 明确记录了两种实际验证：Driver 单元测试、`pytest --collect-only`；同时明确 HIL_NOT_EXECUTED。这一点是正确的限制声明，应保留。

但 005 的逐 Case 表把收集节点写为 `PASS (N项)`，并把原流程/断言全保持、错误路径全覆盖等全部打勾。它与 F01～F07 的源码事实冲突。

必须纠正：

- 收集通过只表示测试节点能被发现，不会执行 Case 内的参数调用，也不会验证 Fixture 的实际 setup/teardown。此前 003 把“签名验证”笼统列入收集能力也不够精确：Case 内运行时接口仍需另外执行或严格静态绑定检查。
- Driver 单元测试调用 Driver，并不会自动执行全部重构后的 Case；本提交新增的 reset 测试使用 TargetStub，检查三次成功请求，不是固件或恢复测试。
- 27 是 P1/P2 稳定 ID 数；006 的收集清单还包含 P0/P3，不应把整个目录节点数直接当成本批节点数。
- 本轮查询精确 SHA 的 check-runs 返回 0 项，没有获得本提交 CI success 的证据；不能写 CI 已闭环。
- 未见本提交的真实固件编译、Native 故障验证或 HIL 通过证据，不能以 LSP 0 blocking errors 代替。

把 005/006 改为准确的 `COLLECTED`、`UNIT_PASS`、`NOT_EXECUTED`、`FAILED_REVIEW` 等分层说明；每条修复附原代码、修改代码、接口或命令序列证据，不再用统一勾选框替代检查。

## 4. 如何继续简化，而不是把错误修回几百行

### 4.1 保持用户已确认的主结构

```text
选择一个实例 + reset
→ 看得见的配置/激励/必要等待
→ 实际读取 + 明确断言
```

`reset()` 保持固定生命周期组合；普通 Driver 不含 Case 名、不接收 Expected、不计算 Golden、不决定 PASS/FAIL、不按测试阶段分派。不要新增 `run_case/check_all/execute_scenario` 把长流程隐藏起来。

### 4.2 先处理纯数据，不合并硬件动作

例如反复出现的 `CanOptions(True, True, False, False, False, True, False, 0, 0, 0)` 不是可读配置。允许把**完全相同、经核对的固定数据**放成具名不可变配置，Case 保留 `can.options_set(config)`。

同样，CAN timing、RAM 几何和两个 DMA 配置对象的纯计算可以抽出；输入、方向、传输长度、目标 FIFO 等决定测试含义的变量仍需在 Case 中明确。纯数据函数不得调用 Driver 或访问设备。

不要把十几个硬件配置动作压成 `configure_ecc_case()` 或 `prepare_all()`；也不要让 Fixture 悄悄发功能配置命令。

### 4.3 分清可拆的测试目的和不能断开的状态

| 类别 | 建议 | 不可接受的简化 |
| --- | --- | --- |
| ECC Force、Mask、Clear | 可按单一目的拆短；重复投递仍保留同一代的前后关系 | 第一次触发后 reset，再把第二次叫“重复投递” |
| 格式、ID、Filter | 保留参数化矩阵，纯输入命名清晰，标准/扩展差异不在设备流程里反复猜测 | 少测 DLC、删 Pattern、删拒绝路径，或 Expected 从 RX 生成 |
| FIFO 满/覆盖/回绕 | 用真实数据顺序线性表达，必须完整推进指针 | 每发一帧都 reset，把回绕测试变成独立单帧测试 |
| March 与恢复 | 外移 regions/chunks/固定表；保留访问方向、每地址读写顺序和不 reset 的重建证明 | Driver 内执行完整 March 并直接返回 True |
| Timeout | 减少无关样板；保留计数源和启用/禁用连续对照及观察窗口 | 固定一次快照、自然到期改 Force，或中途复位计数 |
| DMA/Watchdog | 数据配置提纯，收尾移出；保留通道、路由、窗口与真实错误判据 | CAN reset 假装也清了外部 DMA，或只比 payload |

### 4.4 20 行目标如何验收

普通单目的 Case 先以 20 行为目标。做完纯数据提取、冗余去重和独立目的拆分后，仍超过 20 行的连续硬件测试，必须列出多出来的每组动作及其不可删除原因。

不要预先给所有复杂测试发“可超过 20 行”的通行证；也不要为了数字损坏测试。可以保留一条有明确理由的 30～40 行连续测试，不能接受一条 15 行但遗漏源使能或数据判据的测试。

“已有 Case 设计复杂”不是推卸理由：先说明它包含几个验证目的，是否必须共享状态，哪些可参数化、哪些必须连着执行，再决定拆分。三段式是读代码的结构，不要求所有测试只能在最后才第一次断言；必要的中间硬件检查应保留。

## 5. 下一位 Agent 的执行顺序

### 批次 A：先修确定性回退，不继续批量删行

1. 修 F01、F02：ECC 和普通 IRQ 的命令顺序、真实字段与负向/对照检查。
2. 修 F03：逐个核对所有 CAN P1/P2 对 DMA/SYSCTRL/Resource/STIMER/盒子的调用，而不是只核对 CanDriver。
3. 恢复 F04 的观察窗口；检查其它 Case 是否发生相同删减。
4. 补 F05/F06：有限可靠收尾和一致的单实例选择。
5. 不自动覆盖或硬重置用户工作树；只在 chatgpt_review 上按精确 HEAD 开工，保留已通过旧行为作对照。

### 批次 B：补证据和准确状态

1. 修 F07 的原始记录通路、失败备注展示；FAIL 参数不混入 PASS 数据。
2. 修 F08/F10 的范围、数字、验证状态和自检表。
3. reset 的固件验证单列，保持 PC/固件命令 98 的真实配套。发现跨公共层需求时按最小授权范围单独处理，不顺带重构其它 IP。

### 批次 C：再做可读性第二轮

优先选择一条正常帧/过滤 Case、一条 ECC/IRQ Case、一条 DMA Case作对照。每条给出：旧关键命令顺序 → 新关键命令顺序 → 所有断言对应 → 行数及仍长的原因。

样板正确后再铺开，不以“27 个文件都修改过”作为完成条件。公共配置只共享数据，不能形成通用场景执行器。

## 6. 最低复验要求

1. **接口检查：** 真正执行 Case 正文或对其调用做严格签名绑定；真实 enum/dataclass/ResourceRef 不能用容忍任意属性的替身。所有参数节点均覆盖。
2. **实际 Python 链：** 使用真实 Driver/Codec/TargetClient，底层通信替换为可审阅的脚本传输；记录旧/新命令、配置值、实例、响应读取和 Ack 顺序。轮询次数可受时序影响，不据此要求字节级日志完全相同，但关键操作偏序和预算不能改。
3. **固件验证：** 编译实际 CONTEXT_RESET Service/IRQ Manager 边界；测试有效会话、空会话、绑定失败残留、解绑失败、代次、重复 reset 和不影响其它所有者。
4. **异常路径：** setup/call/teardown 各自失败和同时失败；清理失败后禁止未恢复状态下继续下一 Case。初始化成功次数不是清理成功证据。
5. **报告端到端：** 真实 canonical 结果输入现有报告生成器；验证 PASS 原始数据仍在、PASS 备注空、FAIL 只有失败参数、运行异常不冒充芯片故障。
6. **硬件：** 遵守现有人工 HIL 门禁，先 ECC 和 IRQ，再 DMA/Watchdog，再本次受影响的 CAN P1/P2；不自动扩展到全 IP。绑定源码 SHA、固件 build 与所选实例，历史通过不移植成当前通过。

本轮没有重跑这些全套验证。210 单元与 148 收集是被审查报告的声明，不是本次复核重新取得的通过记录。

## 7. 可复用的全量行数统计命令

在真实仓库根运行以下只读脚本，统一产生 27 个 Case 的实际指标；不要把报告手填值当成事实。这个脚本只度量代码，不判断测试是否正确。

```python
import ast
from pathlib import Path

root = Path('pc/et_test_platform/test_cases/can')
for path in sorted(root.glob('test_can_p[12]*.py')):
    text = path.read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    for node in ast.parse(text, filename=str(path)).body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith('test_can_p'):
            continue
        span = node.end_lineno - node.lineno + 1
        body = lines[node.body[0].lineno - 1:node.end_lineno]
        code = sum(bool(line.strip()) and not line.lstrip().startswith('#') for line in body)
        print(f'{node.name}: span={span}, body_code={code}, {path}:{node.lineno}')
```

## 8. 固定提交证据入口

以下链接均指向审核时的固定提交；阅读后续修复时重新固定新的 SHA，不使用浮动分支内容替代本轮证据。

### 新实现与相邻接口

- [ECC Case](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p2_ecc.py)
- [P1 主文件：IRQ、March、格式及过滤](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p1.py)
- [Timeout](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p1_timeout.py)
- [DMU 收发及事件](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p2_dmu.py)
- [Watchdog](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p2_watchdog.py)
- [多实例 RAM](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/test_can_p2.py)
- [CAN Fixtures](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/test_cases/can/conftest.py)
- [CAN Driver](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/drivers/can/driver.py)
- [CAN 模型字段](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/drivers/can/models.py)
- [SYSCTRL 两种路由接口](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/drivers/sysctrl/driver.py)
- [ResourceRef](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/drivers/resource/models.py)
- [Resource read 接口](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/drivers/resource/driver.py)
- [ET6801 CAN 请求与 RAM 映射](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/profiles/chip_execution_mappings/et6801/can_routes.py)
- [固件 CAN Service 与回调](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/firmware/services/src/et_can_service.c)
- [实际报告实现](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/results/case_report.py)
- [新增 reset 单元测试所在文件](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/pc/et_test_platform/framework_validation/unit/drivers/can/test_can_driver.py)

### 对照与自检声明

- [完整提交差异](https://github.com/abba-labs/et-harness/compare/d6b91b65fd96c04f80e87e954c463be48607288b...d0c751f47b1d98e021758c7d96b70e620149cf12)
- [基线 ECC](https://github.com/abba-labs/et-harness/blob/d6b91b65fd96c04f80e87e954c463be48607288b/pc/et_test_platform/test_cases/can/test_can_p2_ecc.py)
- [基线 DMU，含精确事件类型与地址/错误判据](https://github.com/abba-labs/et-harness/blob/d6b91b65fd96c04f80e87e954c463be48607288b/pc/et_test_platform/test_cases/can/test_can_p2_dmu.py)
- [基线 Watchdog 观察窗口](https://github.com/abba-labs/et-harness/blob/d6b91b65fd96c04f80e87e954c463be48607288b/pc/et_test_platform/test_cases/can/test_can_p2_watchdog.py)
- [被审查的自检表](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/report/review/chatgpt_review/can/005_can_p1_p2_self_review.md)
- [被审查的验证汇总](https://github.com/abba-labs/et-harness/blob/d0c751f47b1d98e021758c7d96b70e620149cf12/report/review/chatgpt_review/can/006_can_p1_p2_validation_summary.md)

---

**最终验收口径：短 Case、薄 Driver、真实复位、原硬件顺序与判据均成立，才叫优化完成。代码变短不能补偿接口不存在、IRQ 未使能、观察窗口被删或清理错误被吞掉。**
