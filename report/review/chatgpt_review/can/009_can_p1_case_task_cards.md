# CAN P1：19张逐项任务卡

行为对照B：`d6b91b65fd96c04f80e87e954c463be48607288b`；问题版本R：`d0c751f47b1d98e021758c7d96b70e620149cf12`。原代码已硬件通过是用户提供的背景，修改后的结果必须重新验证。本文件和任务卡不是已验证实现。

19张任务卡的完整正文分别保存在下方链接的文件中，避免让低上下文Agent每次加载整个P1文档。每张卡均包含原函数、固定源码引用、测试目的、拆分决定、具体优化位置、必要步骤、不可删除判据、禁止项、错误反例和Review交付要求。

## 每次开发的读取顺序

[008执行约束](008_can_refactor_execution_contract.md) → 本次的一张任务卡 → [011验证与独立Review](011_can_validation_and_review_runbook.md) → 卡片指定B版本的完整函数与当前真实接口。

先修行为，再做瘦身；每个删除项有明确去向。源码根为`pc/et_test_platform/test_cases/can/`。本批先完成008中的G0/G1和P2_003样板，经过复核后才进入P1批次。

子目的名称不是已经存在的API或正式Case ID；先建立拆分Ledger、检查SPEC/PLAN/注册表编号后实施。不得为了减少行数将动作隐藏在Driver或将读回变成Expected。

## 19张完整任务卡

| 原稳定Case | 原函数主题 | 完整任务卡 | 拆分决定摘要 |
|---|---|---|---|
| CAN_P1_001 | frame_formats | [P1_001](cards/P1_001.md) | 保留原格式/ID/DLC/A/B及跨帧顺序，不拆 |
| CAN_P1_002 | standard_id_filter_and_routing | [P1_002](cards/P1_002.md) | 可分接收路由、拒绝、HighPriority，原节点逐行映射 |
| CAN_P1_003 | extended_id_filter_and_mask | [P1_003](cards/P1_003.md) | 可分扩展接收路由、拒绝、HighPriority |
| CAN_P1_004 | remote_frame_policy | [P1_004](cards/P1_004.md) | 允许→拒绝→同ID数据恢复保持连续 |
| CAN_P1_005 | rx_fifo_watermark_full_and_wrap | [P1_005](cards/P1_005.md) | 可分水位/满与回绕；回绕子Case自己重建前缀 |
| CAN_P1_006 | rx_fifo_blocking_and_overwrite | [P1_006](cards/P1_006.md) | 填满→溢出→读取→恢复不拆 |
| CAN_P1_007 | dedicated_rx_buffer_boundaries | [P1_007](cards/P1_007.md) | 可分寻址与位图单清/重置位，后者自己建立多位前缀 |
| CAN_P1_008 | tx_fifo_queue_order | [P1_008](cards/P1_008.md) | 并存请求和顺序比较不拆 |
| CAN_P1_009 | tx_event_fifo_watermark_full_and_recovery | [P1_009](cards/P1_009.md) | 可分水位与满/丢失/恢复；恢复链保持 |
| CAN_P1_010 | message_marker_width | [P1_010](cards/P1_010.md) | 两事件同时保留与100ms尾窗不拆 |
| CAN_P1_011 | irq_lines_and_clear | [P1_011](cards/P1_011.md) | 先修原ID，再分屏蔽/pending路由与单清/再触发 |
| CAN_P1_012 | bitrate_matrix | [P1_012](cards/P1_012.md) | 速率参数保留，外部双向链不拆 |
| CAN_P1_013 | internal_timestamp | [P1_013](cards/P1_013.md) | 可分关闭对照与内部捕获/回卷/清零，内部链不再拆 |
| CAN_P1_014 | timeout_sources | [P1_014](cards/P1_014.md) | 四计数源的baseline→enabled→disabled不拆 |
| CAN_P1_015 | clock_stop_and_recovery | [P1_015](cards/P1_015.md) | 停钟与同实例唤醒恢复不拆 |
| CAN_P1_016 | message_ram_march | [P1_016](cards/P1_016.md) | 可分固定/地址模式与March/不reset重建 |
| CAN_P1_018 | tsu_capture | [P1_018](cards/P1_018.md) | 可分New/Lost/读清与内部时基比率，各自建立前置 |
| CAN_P1_020 | fd_format_matrix | [P1_020](cards/P1_020.md) | 可分格式匹配与失配，两者各自保留ISO恢复 |
| CAN_P1_021 | tdc_external_fd | [P1_021](cards/P1_021.md) | 原速率、A/B及外部双向不拆 |

## 完成标准

拆分时逐项遵循任务卡，不以本表摘要替代完整卡片。原完整函数的其他断言和参数也须逐项记账，未在摘要出现不等于允许删除。行数目标是正文尽量不超过20行，硬件正确性、取证顺序和明确判据优先；超长要列必要动作和状态关系，不能自行宣称达标。

交付与验证状态按照011记录。本次只发布文档，没有执行卡片对应的软件、固件或硬件测试，不新增PASS声明。
