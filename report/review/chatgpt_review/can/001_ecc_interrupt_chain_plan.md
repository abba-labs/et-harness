# CAN_P2_003：保持既有覆盖的简化方案

状态：PROPOSED，等待样板写法评审。本文件不是已经实施的修复，也不是硬件通过报告。
源码基线：`968cc410323ecade4068de5f73b46ac6b0de9157`，分支 `chatgpt_review`。
用户负责本地实施、检查和上传；后续复核以用户上传的精确提交为准。

## 1. 本轮实际审查范围

- `pc/et_test_platform/test_cases/can/test_can_p2_ecc.py`：完整 Case。
- `pc/et_test_platform/test_cases/can/conftest.py`：全部实例入口和对象构造。
- `pc/et_test_platform/drivers/can/driver.py`、`models.py`、`__init__.py`：ECC 命令、返回类型及等待。
- `firmware/services/src/et_can_service.c`、`firmware/services/include/et_can_service.h`：普通 IRQ、ECC、DMU 三套 Service 状态。
- `firmware/services/src/et_crg_service.c`、`firmware/wrap/src/et_crg_wrap.c`：硬件复位路径。
- `firmware/services/src/et_resource_service.c`、`firmware/wrap/src/et_resource_wrap.c`：资源池复位路径。
- `firmware/framework/src/et_irq_manager.c`：绑定、解绑及物理 IRQ 清理。

这些文件中的已读调用链是 Case 调用 Driver。没有在已读 CAN Driver/ECC 链路中发现 Driver 反向调用这条 Case。不要因可读性问题而凭空修改不存在的反向依赖。

## 2. 具体问题、原因和影响

### C01：五个阶段被合在字符串分派循环里

当前 Case 对 `masked/first/cleared/repeat/stopped` 进行循环，然后通过 if/elif 选择设备动作。Reviewer 必须同时理解当前阶段、first 是否为空、target/旁路实例以及不同条件下的 Expected。

修改：把屏蔽、首次投递、Clear、再次投递、退出按真实时间顺序展开。stage 只作为记录标签，不再用来分派设备动作。两次投递之间不重启 Capture，保留 generation 连续性检查。

### C02：清理逻辑淹没了主流程

当前清理使用多层 lambda、tuple 和推导式。它的全部尝试及保留主错误有价值，复杂表达没有必要。

修改：使用一个本 Case 文件内的动作列表构造函数；按普通 for/append/extend 返回现有 Driver 的直接清理动作。仍由已有 `case_cleanup_scope` 执行，不新增通用资源管理器。构造函数自身不执行 I/O、测试或断言。每实例仍按 mask、disable、stop、clear、CRG reset；最后 Resource reset。

### C03：记录和相同比较重复展开

四个硬件端点分别手写 record_observation，阶段公共比较也嵌在复杂循环里。

修改：保留原键 `ecc_raw/ecc_status/ecc_enabled/ecc_masked` 和端点 `ECC_IRQ.RAW/STATUS/ENABLED/MASKED`；数据记录函数只接收已经读出的 dataclass，不接收 Driver。每次成功读回立即记录，再读取下一项，再执行断言。这样下一个设备或下一条命令超时，之前已获得的观测仍保留。

公共字段比较放在同一 Case 模块的短纯比较函数中。期望 Raw、Count、Enabled 在主流程每个阶段显式给出；比较函数不读取设备、不触发、不等待、不按 stage 改变流程，也不进入 Driver 包。这种表达需在实施前与现有 R210/静态检查逐项核对，不能通过关闭检查或搬迁最终测试到 Driver 来通过门禁。

### C04：CRG 不复位 CAN Service 软件会话

CRG 最终只调用 `CRG_resetPeripheral`。CAN 的 `irq_event/irq_line_events/bound_lines`、`ecc_event/ecc_watched/ecc_bound`、`dmu_event/dmu_watched/dmu_bound` 是固件 RAM 状态，不会由该调用自动清除。

修改：单独实现本 IP 的 `CanDriver.state_reset()` 与对应 CAN Service 命令。它是样板唯一拟新增的设备 API，尚未存在于源码中。先验证该原语，再把它用于 Case 基线。

## 3. state_reset 的具体边界

PC Driver 只编码并发送新的无参数 CAN 状态复位命令，沿用当前请求中的实例字段、超时与错误传递。不要让 CanDriver 调 CrgDriver、ResourceDriver、pytest 或 test_cases。

固件的执行位置是 `et_can_service.c`，只清理选中实例。

推荐实现顺序：关闭本实例普通 CAN/ECC/DMU 相关来源，停止本实例各捕获会话，通过现有 IRQ Manager 精确释放回调绑定；全部需要释放的绑定确认完成后，清软件观测计数、故障记录和已解除的运行标志。ECC/DMU 无回调实例字段恢复为当前契约的无实例表示，generation 按现有逻辑更新。

保留 can_id、descriptor、irq_manager、irq_priority 等长期依赖。不要对运行中的整个 Service 或全局 IRQ Manager 直接 memset，也不要把重新调用 service_init 当运行期清理。原有 stop 函数保留证据的语义不变，新 STATE_RESET 才负责建立新的空软件记录。

解绑只释放当前 callback/context 所有的条目，共享物理线路仍由 IRQ Manager 处理最后使用者清理。源未关或解绑未完成时返回失败，保留未完成状态，不能先将 bound/watched 标志清零而报告成功。全局 Manager 的历史故障统计不由单 CAN reset 擅自擦除。

这个命令不调用 CRG、不清公共资源池、不配置 GPIO、波特率、滤波器或回环，也不无条件清 CAN Message RAM。Message RAM 与公共 Resource Pool 是两种存储，复位覆盖要依据芯片事实另外核对。

实现文件涉及 CAN Driver/Contract/Codec、CAN Service 头和源码、公共 CAN 命令文档及对应软件测试。命令追加到当前表尾，旧命令号和旧公共签名保持不变。新命令不设为自动重试安全命令，除非另有完整幂等证明。

## 4. Case 基线及退出边界

对本 Case，每个 target/source 轮次先对所有参与实例执行 state_reset，再 CRG reset，最后 Resource reset。然后明确 mask 全部 ECC 源、disable 全部源、clear 全部 Raw，最后 start 当前 source 的捕获。保留全部实例同时捕获，轮转所有 target。

现有 capture_start 已会启动新的事件 generation；旧版 event_reset + capture_start 的具体 generation 更新次数需在原语实现测试中核对。测试依赖的是一轮内的连续性，不应增加对绝对 generation 数字的假设。

测试末尾的 mask、disable、capture_stop、clear、event_reset 和终态读回是本 Case 的测试内容。不能用 CRG 或 state_reset 直接抹平终态来让检查通过。异常退出才由外层固定清理执行兜底。

本 Case 没有活动 DMA。CAN 的 DMU/DMA Case 属于后续批次；那里要先停止相关 DMA、处理通道和请求路由，才允许清 CAN/资源池。不要把此样板基线无条件复制到所有组合 Case。失败清理没有恢复完成时不继续下一条测试。

每目标/source 保持现有 5.0 s 总预算；ECC 命令和等待继续传剩余时间，不改成每条命令重新获得 5 s。CRG/Resource 现有调用签名及超时边界须按当前实现检查，不为了样板擅自改公共层。新增基线开销需实测，不能先增大预算。

## 5. 逐项覆盖映射

| 保留项目 | 简化后的对应位置 |
|---|---|
| CORRECTED 与 UNCORRECTED 两个 source 节点 | 保持原 parametrize |
| 全部声明实例轮流作为目标 | 外层 target 循环 |
| 所有实例同时作为旁路观察者 | 每阶段遍历全部 cans |
| 两源同时 Force，但只使能指定源 | 初始 ALL Force + capture_start(source) |
| 完整 0.1 s 内持续无 ISR | monotonic 窗口 + 全实例轮询；不改成一次快照 |
| 静默时 raw_status/masked_status/latched/count/instance/diagnostics | 原字段纯比较函数 |
| 首次 ISR 恰好 1 次、归属目标、Raw 两源、有效源仅 source | 首次 wait 后的明确检查 |
| 每阶段硬件 Raw/Status/Enabled/Masked | 逐实例先采样、记录，再比较 |
| Clear 只影响目标源，另一源 Raw 保留 | 独立 cleared 阶段，期望 ALL xor source |
| Clear 后已有事件仍保留 | cleared 阶段期望 Count=1 |
| 再次投递 Count=2、generation 不变 | 明确第二次 Force/放行/等待及 generation 比较 |
| 非目标实例无串扰 | 每阶段 Count=0、Instance=None、Latched=NONE、诊断为零 |
| 退出 Raw/Status/Enabled/Count 清净且保持全 mask | stopped 阶段读回 |
| 原始证据键及设备归属 | 数据记录函数保留旧键与端点 |
| 清理步骤全部尝试，主错误不被覆盖 | 复用已有 case_cleanup_scope |

这里验证的是 ECC 中断 Force/Mask/Clear 链路，不是实际 RAM 位错误注入、纠错算法或错误数据恢复。

## 6. 代码预览

完整预览及辅助函数见 `002_ecc_case_preview.md`。它是目标写法，不可在未实现并验证 state_reset 时直接替换运行文件。预览保留现有 Case ID、输入、时序与关键断言，但新增前置原语仍属于需要验证的行为变化，不能仅凭代码阅读宣称与旧硬件执行完全等价。

预览使用两个数据动作：record 只保存返回值；check 只比较传入数据。它们都在 Case 层，不接收设备对象。partial 仅固定本轮 target/source 和记录上下文，不产生回调反向依赖。

## 7. 本地实施与验证

第一批只补齐并验证 STATE_RESET。覆盖未绑定、普通 IRQ/ECC/DMU 活动、双实例共享 IRQ、第一次关闭或解绑失败、旧记录非零、连续 reset 等场景；确认其他实例及控制 UART 不受影响。同步长度映射、实例校验、错误编码和新旧命令向量。

第二批只改这条 ECC Case。实施前后比较采集到的稳定 Case ID 和参数节点数量；使用记录 Driver 或桩核对两次 Force、mask/unmask、Clear、capture_start/stop 的关键相对顺序。确认两个 source 均执行全部 target，各阶段旁路实例检查仍存在。比较正常路径和各失败点的清理顺序。

重点故障测试：负向窗口中途出现事件、错误实例回调、错误 source、Count 跳到 2、Unexpected/Overflow/Fault 非零、Clear 误清另一源、repeat 改 generation、终态残留、第二个实例读取超时、snapshot 成功但 event 读取失败、清理失败与主断言同时发生。逐次成功观测均应仍可追溯。

真实硬件回归保持原接线、构建配置和通过标准，记录精确固件/源码 SHA。先验证本 Case，再按实际改动影响验证 CAN 相邻 IRQ/ECC/DMU Case；不把未执行测试记为通过。

报告改动另见 `../report/001_fail_only_remarks_plan.md`，与 CAN 固件分为独立提交。

## 8. 本轮验证说明

这里只建立方案文件，没有替换运行代码。预览做过 Python AST 语法解析，以及用按当前字段定义构造的数据对纯比较/记录函数进行 58 项隔离检查；这些不是仓库单元测试，更不是 CAN/HIL 测试。仓库总门禁、Keil 和 HIL 均为 NOT_EXECUTED。本地实施仍需按当前规则编译 Task Context、检查范围并执行实际专项验证。
