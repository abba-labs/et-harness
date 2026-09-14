# CAN P2：8张逐项任务卡

行为对照B：`d6b91b65fd96c04f80e87e954c463be48607288b`；问题版本R：`d0c751f47b1d98e021758c7d96b70e620149cf12`。原代码已硬件通过是用户提供的背景，修改后的结果必须重新验证。本文件和任务卡不是已验证实现。

8张任务卡的完整正文分别保存在下方链接的文件中。每次只读取公共约束、当前一张卡、验证操作单及基线源码，不必同时加载整个P2文档。

## 每次开发的读取顺序

[008执行约束](008_can_refactor_execution_contract.md) → 本次的一张任务卡 → [011验证与独立Review](011_can_validation_and_review_runbook.md) → 卡片指定B版本的完整函数与当前真实接口。

先完成008中的G0/G1和P2_003样板，提供行为对照和错误反例，复核后才进入后续批次。源码根为`pc/et_test_platform/test_cases/can/`。子目的名称不是已存在的API或正式Case ID，拆分前需要查重并同步契约、注册和选择关系。

## 8张完整任务卡

| 原稳定Case | 原函数主题 | 完整任务卡 | 拆分决定摘要 |
|---|---|---|---|
| CAN_P2_001 | dmu_tx_rx | [P2_001](cards/P2_001.md) | 保持TX/RX与两帧队列关系；RX0/RX1参数保留 |
| CAN_P2_002 | dmu_tx_event | [P2_002](cards/P2_002.md) | 保持事件产生、真实DMA搬运、两项同时保留与整区比较 |
| CAN_P2_003 | ecc_interrupt_chain | [P2_003](cards/P2_003.md) | 先修原ID，再分重复投递、屏蔽、选择性清除；每个子Case自建前置 |
| CAN_P2_004 | instance_ram_isolation | [P2_004](cards/P2_004.md) | 单实例策略下SCOPE_OUT_MULTI_INSTANCE；不冒充PASS |
| CAN_P2_005 | loopback_pin_comparison | [P2_005](cards/P2_005.md) | 保持Normal/Internal/External原对比链和物理路径观察 |
| CAN_P2_007 | dmu_illegal_irq | [P2_007](cards/P2_007.md) | 九个故障节点各自保留故障→原复位→真实DMA恢复 |
| CAN_P2_008 | dmu_rx_timestamp | [P2_008](cards/P2_008.md) | 五参数节点内完整搬运/时间戳/覆盖错误链不拆 |
| CAN_P2_010 | ram_watchdog | [P2_010](cards/P2_010.md) | 保留三个阶段、原阶段复位边界、100ms窗口及真实DMA/STIMER |

## 本批最先核对的确定性问题

P2_003第二次Force后必须再次解除屏蔽；硬件Raw与ISR历史记录分开判断。P2_001/002核对实际SYSCTRL V2签名、rx映射键、FIFO参数、Resource读取方式和真实返回字段，不通过修改旧Driver来迁就写错的Case。P2_010保留实际观察窗口和STIMER读数，不以启动计数器却不读取替代证据。具体步骤与完整禁止项以各卡及007为准。

## 完成标准

单实例只调整实例维度，不删除功能参数、两种Pattern、错误注入方式、精确判据、观察窗口和恢复关系。P2_004范围排除不能被计为通过；其他性质逐条有新的实现位置和验证证据。

正文目标尽量不超过20行，但不能将完整测试流程放入Driver、删除动作或压缩排版。必要超长按011独立复核，不自动判定“完全满足”。本次只发布文档，不修改运行代码，不新增软件或硬件PASS声明。
