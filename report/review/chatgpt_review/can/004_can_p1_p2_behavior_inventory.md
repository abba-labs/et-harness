# CAN P1/P2 逐 Case 硬件行为盘点与瘦身映射清单 (Stage A)

> **关联指导**：`report/review/chatgpt_review/can/003_can_p1_p2_agent_execution_guide.md`  
> **调查基线 SHA**：`d6b91b65fd96c04f80e87e954c463be48607288b` (对齐原基线 `d4c2eb9fbebbc1a1d2a4c2a16fa501612a123130`)  
> **执行阶段**：阶段 A（只读盘点，不修改运行代码）  
> **盘点范围**：基线 `case_registry.py` 中登记的全部 **27 个稳定 Case**（19 个 P1，8 个 P2）

---

## 0. 盘点总述与执行原则

本清单是 CAN P1/P2 极简重构在**阶段 A（只读盘点）**的核心交付工件。它逐一解剖当前工程中全部 27 个测试用例，回答 13 项关键硬件行为指标，确保后续在实施“**三段式（<=20行）极简重构**”时，**100% 保持硬件测试的真实有效性**，严防“为了形式简化而删覆盖、假测试、改时序”。

### 核心结论速览

1. **总代码量可削减约 75%~85%**：当前 27 个 Case 总跨度达 **6,758 行**（平均每个 Case 250 行）。通过剥离漫天遍野的 `record_observation`、手写 JSON 报告、`case_cleanup_scope` 闭包和多实例外层嵌套，90% 的普通 Case 可压缩至 **20 行以内**。
2. **四类重构归属划分**：
   * **直接瘦身（Direct Slimming, 15 条）**：无复杂连续时序的独立 Case，直接改写为三段式，行数稳定在 15~20 行。
   * **可独立拆分（Independently Splittable, 4 条）**：原本在一个大函数中揉杂了多个不同特性的测试，拆分成单一职责的短 Case。
   * **必须连续（Must Remain Continuous, 7 条）**：包含 RAM March、Watchdog、连续超时、DMU 流水等不可打断的状态机，去除杂务后保持硬件时序连续，超长（25~45行）做合规说明。
   * **单实例范围调整（Single-Instance Scope Adjusted, 1 条）**：`can_p2_004` 为纯双实例隔离测试，在单实例策略下如实记账为范围调整，不作伪测试。

---

## 1. 27 个 Case 四分类索引汇总表

| 序号 | Case ID | 所在文件 | 原行数 | 拟重构分类 | 核心优化措施 |
| :---: | :--- | :--- | :---: | :---: | :--- |
| 1 | `can_p1_001_frame_formats` | `test_can_p1.py` | 154 | **直接瘦身** | 砍掉循环内每次 CRG/Resource 复位与打标，参数化 DLC/格式，收敛到 18 行 |
| 2 | `can_p1_002_standard_id_filter_and_routing` | `test_can_p1.py` | 202 | **直接瘦身** | 具名常量提取配置，消除 12 次 observation，保留参数化路由与断言 |
| 3 | `can_p1_003_extended_id_filter_and_mask` | `test_can_p1.py` | 212 | **直接瘦身** | 同上，收拢掩码与滤波配置，纯粹比对接收与拒绝 |
| 4 | `can_p1_004_remote_frame_policy` | `test_can_p1.py` | 219 | **直接瘦身** | 剥离 RTR 帧报告组装，保留 RTR 标志与接收/拒绝判定 |
| 5 | `can_p1_005_rx_fifo_watermark_full_and_wrap` | `test_can_p1.py` | 292 | **可独立拆分** | 拆分为 Watermark+Full（满）与 Wrap（环绕）两个独立短 Case |
| 6 | `can_p1_006_rx_fifo_blocking_and_overwrite` | `test_can_p1.py` | 200 | **直接瘦身** | 参数化 blocking/overwrite，清除多余清理闭包，保留溢出覆盖断言 |
| 7 | `can_p1_007_dedicated_rx_buffer_boundaries` | `test_can_p1.py` | 288 | **可独立拆分** | 拆分为 单Buffer命中 与 边界寻址遍历，消除嵌套循环打标 |
| 8 | `can_p1_008_tx_fifo_queue_order` | `test_can_p1.py` | 164 | **直接瘦身** | 参数化 FIFO/优先级模式，直接发送读回顺序比对，约 18 行 |
| 9 | `can_p1_009_tx_event_fifo_watermark_full_and_recovery` | `test_can_p1.py` | 291 | **可独立拆分** | 拆分为 Watermark/Full事件 与 清空恢复，保留精确事件断言 |
| 10 | `can_p1_010_message_marker_width` | `test_can_p1_marker.py` | 221 | **直接瘦身** | 参数化 8-bit/16-bit Marker，消除大段报告字典，保留 Marker 比较 |
| 11 | `can_p1_011_irq_lines_and_clear` | `test_can_p1.py` | 227 | **可独立拆分** | 拆分为 引脚路由分派 与 W1C清除，保留真实 ISR 捕获 |
| 12 | `can_p1_012_bitrate_matrix` | `test_can_p1_rates.py` | 200 | **直接瘦身** | 外部线路波特率矩阵参数化，剥离冗余能力打印，保留双向传输校验 |
| 13 | `can_p1_013_internal_timestamp` | `test_can_p1_timestamp.py` | 230 | **直接瘦身** | 保留分频器配置与单次读取（防副作用），剔除中间大量打印 |
| 14 | `can_p1_014_timeout_sources` | `test_can_p1_timeout.py` | 233 | **必须连续** | 4 个连续计数源与窗口观察不可切断，精简打标后作为长连续用例保留 |
| 15 | `can_p1_015_clock_stop_and_recovery` | `test_can_p1.py` | 156 | **直接瘦身** | 时钟停止请求 $	o$ 确认 $	o$ 唤醒恢复，标准线性三段式 |
| 16 | `can_p1_016_message_ram_march` | `test_can_p1.py` | 223 | **必须连续** | 6 阶段 March C- 算法是完整硬件闭环，辅助算法移入内部数据助手，保留连续时序 |
| 17 | `can_p1_018_tsu_capture` | `test_can_p1_tsu.py` | 378 | **必须连续** | TSU 外部/内部时钟参考与 STIMER 对齐时序不可打断，纯化硬件调用 |
| 18 | `can_p1_020_fd_format_matrix` | `test_can_p1_format.py` | 252 | **直接瘦身** | ISO/Non-ISO 矩阵参数化，去除复杂报告格式化，直接断言 DLC 与数据 |
| 19 | `can_p1_021_tdc_external_fd` | `test_can_p1_tdc.py` | 191 | **直接瘦身** | 高波特率下开启 TDC，读取测得延迟，断言无位错误，标准 15 行 |
| 20 | `can_p2_001_dmu_tx_rx` | `test_can_p2_dmu.py` | 360 | **必须连续** | RX DMA 先行 $	o$ 发送 $	o$ DMA 搬移，保持硬件通道顺序，剔除通用上下文 |
| 21 | `can_p2_002_dmu_tx_event` | `test_can_p2_dmu.py` | 290 | **必须连续** | DMU 抓取 TX Event 搬运至 SRAM，保持 DMA 初始化与触发时序 |
| 22 | `can_p2_003_ecc_interrupt_chain` | `test_can_p2_ecc.py` | 179 | **必须连续** | 单实例化（砍掉外层轮转），保留屏蔽观察/投递/清除/二次投递连续链（样板 16 行） |
| 23 | `can_p2_004_instance_ram_isolation` | `test_can_p2.py` | 254 | **单实例范围调整**| 纯跨实例隔离测试，单实例策略下无法维持原结论，做覆盖调整记账 |
| 24 | `can_p2_005_loopback_pin_comparison` | `test_can_p2_loopback.py` | 191 | **直接瘦身** | 对比内部回环与外部引脚模式差异，剔除双重复位与报告代码 |
| 25 | `can_p2_007_dmu_illegal_irq` | `test_can_p2_dmu_errors.py` | 365 | **必须连续** | 制造非法 DMA 地址，观察错误中断与首个读清错误，防重试洗刷现场 |
| 26 | `can_p2_008_dmu_rx_timestamp` | `test_can_p2_dmu_tsu.py` | 419 | **必须连续** | DMU 带时间戳搬运测试，保持 TSU 与 DMA 联合配置时序 |
| 27 | `can_p2_010_ram_watchdog` | `test_can_p2_watchdog.py` | 394 | **必须连续** | 门限1 $	o$ 关闭 $	o$ 恢复 3 阶段连续刺激，不可插入中途 reset |

---

## 2. 逐 Case 详细硬件行为盘点 (27 项完整记录)

以下按《执行指导》第 4.2 节要求的 13 项标准字段逐条展开：

---

### [Case 01] can_p1_001_frame_formats
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_001_frame_formats`，原 154 行。
* **参数节点**：`format_name` (Classic / FD / BRS), `flags`, `id_bound` (minimum 0 / maximum)。
* **目的**：验证 Classic 标准/扩展帧、FD/BRS 帧在 DLC 0~15 时的有效长度映射与 ID 极值。
* **资源**：`can0` (内部回环), Message RAM (RX0 槽, 64-byte 缓冲)。
* **输入**：DLC 0~15，标准 ID (0, 0x7FF) / 扩展 ID (0, 0x1FFFFFFF)，正反两组 pattern。
* **前置**：调用 `can_handle.reset()` 建立初态。
* **硬件顺序**：
  1. `can.initializing_set(True)` $	o$ `wait_initializing(True)`
  2. `can.timing_set(...)` $	o$ `can.options_set(...)` $	o$ `can.ram_layout_set(...)` $	o$ `can.loopback_set(INTERNAL)`
  3. `can.initializing_set(False)` $	o$ `wait_initializing(False)`
  4. `can.tx_write(0, frame)` $	o$ `can.tx_request(1)` $	o$ `can.wait_tx_complete(1)`
  5. `can.wait_rx_available(0)` $	o$ `can.rx_read(FIFO0)` $	o$ `can.rx_fifo_ack(0, index)`
* **连续性**：单帧测试独立，无多阶段状态依赖。
* **观测**：从 RX FIFO0 读回 `CanRxFrame`（ID、flags、DLC、data），读取 TX 完成状态。
* **判据**：`actual.identifier == identifier`，`actual.flags == flags`，`actual.dlc == dlc`，`actual.data == payload`，`tx.completed & 1`。
* **清理**：退出时无活动发送，依托 fixture/下一用例 reset。
* **修改方案**：
  * 去掉 16 次 DLC 循环内每次的 CRG/Resource 重复复位；
  * 去掉 `format_summary` 字符串拼装和 30 行 observation 打标；
  * 提取静态配置，用参数化或内联直发，缩减至 18 行。
* **范围差异**：原测试在单个测试函数内跑完所有 DLC，重构后保持 DLC 矩阵覆盖。
* **验证**：真实收发 32 帧且字节完全一致。

---

### [Case 02] can_p1_002_standard_id_filter_and_routing
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_002_standard_id_filter_and_routing`，原 202 行。
* **参数节点**：`node_name`, `filters`, `unmatched_policy`, `identifier`, `expected_fifo`, `expected_filter`, `high_priority`。
* **目的**：验证标准 11-bit ID 的 Range / Dual / Classic 过滤规则及未匹配报文路由策略。
* **资源**：`can0` (内部回环), Filter 槽位 0~7, RX FIFO0 / FIFO1。
* **输入**：标准 ID，不同的过滤元素配置与未匹配规则。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. 进入 INIT $	o$ 配置 Timing、Options、RAM Layout。
  2. 写入 Filter 表项 (`can.filter_set`) $	o$ 配置总线未匹配策略 (`can.bus_config_set`)。
  3. 退出 INIT $	o$ 开启回环 $	o$ 发送匹配/不匹配报文。
  4. 检查对应 FIFO 是否有数据，或未匹配是否正确被丢弃/路由。
* **连续性**：参数化独立节点，各节点初态独立。
* **观测**：目标 FIFO 的 `rx_available`，读出帧中的 `filter_index`。
* **判据**：匹配帧必须进入指定 `expected_fifo`，`filter_index == expected_filter`；未匹配帧按 policy 拒收或进入指定槽。
* **清理**：清空已收报文，依托下一用例 reset。
* **修改方案**：消除每个参数节点的报告构造与 11 次 observation，配置打包为不可变常量，精炼至 18 行。
* **范围差异**：无。
* **验证**：软硬件核对 Filter 命中索引与丢弃表现。

---

### [Case 03] can_p1_003_extended_id_filter_and_mask
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_003_extended_id_filter_and_mask`，原 212 行。
* **参数节点**：`node_name`, `filters`, `extended_mask`, `unmatched_policy`, `identifier`, `expected_fifo`, `expected_filter`, `high_priority`。
* **目的**：验证 29-bit 扩展 ID 过滤规则及全局/专有扩展 ID 掩码逻辑。
* **资源**：`can0` (内部回环), 扩展 Filter 槽位, 全局掩码寄存器。
* **输入**：扩展 ID、掩码值、过滤项。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：与 Case 02 类似，额外增加 `can.extended_mask_set(extended_mask)` 配置。
* **连续性**：参数节点独立。
* **观测**：目标 FIFO 读出帧及其过滤索引。
* **判据**：在掩码运算后符合条件的报文准确落入指定 FIFO，不符合条件的被拒绝。
* **清理**：同 Case 02。
* **修改方案**：同 Case 02，删除清理闭包与打标，收敛至 19 行。
* **范围差异**：无。
* **验证**：真实收发核对掩码比特过滤结果。

---

### [Case 04] can_p1_004_remote_frame_policy
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_004_remote_frame_policy`，原 219 行。
* **参数节点**：`extended` (True/False), `dlc` (0, 8)。
* **目的**：验证远程帧 (RTR) 在总线上的过滤、透传或拒绝策略。
* **资源**：`can0` (内部回环), Filter 表项。
* **输入**：带有 RTR 标志的 Standard/Extended 帧。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：进入 INIT $	o$ 配置 `reject_remote_std` / `reject_remote_ext` $	o$ 退出 INIT $	o$ 发送 RTR 帧 $	o$ 验证接收或丢弃。
* **连续性**：独立节点。
* **观测**：RX FIFO 水位与接收帧的 `flags & CanFrameFlags.REMOTE`。
* **判据**：配置为拒绝时 FIFO 保持为空；配置为接收时读出 RTR 帧且无数据体。
* **清理**：标准收尾。
* **修改方案**：消除所有文本拼装与冗余断言，提炼为 15 行极简 Case。
* **范围差异**：无。
* **验证**：RTR 标志硬件触发与过滤验证。

---

### [Case 05] can_p1_005_rx_fifo_watermark_full_and_wrap
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_005_rx_fifo_watermark_full_and_wrap`，原 292 行。
* **参数节点**：`fifo` (0 或 1)。
* **目的**：验证 RX FIFO 水位中断触发、满状态标志及读出确认后的指针环绕 (Wrap) 机制。
* **资源**：`can0`, FIFO0/FIFO1 (深度设为如 3 或 4)。
* **输入**：连续发送多帧直至触发水位，再填满至上限，随后逐步 Ack。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. 配置 FIFO 深度与 Watermark 门限。
  2. 连续发送报文至水位线 $	o$ 读状态断言 `watermark` 置位。
  3. 继续发送至满 $	o$ 读状态断言 `full` 置位。
  4. 读出帧并执行 `rx_fifo_ack` $	o$ 校验读指针回绕到 0。
* **连续性**：**内部阶段连续**（水位 $	o$ 满 $	o$ 环绕）。
* **观测**：`can.rx_fifo_status_get(fifo)`（包含 fill, watermark, full, get_index）。
* **判据**：fill 达到门限时 watermark 为 True；达到深度时 full 为 True；连续 ack 后 get_index 正确环绕。
* **清理**：清空 FIFO 剩余报文。
* **修改方案**：
  * 该 Case 属于**可独立拆分**：可拆分为 `_watermark_full` 和 `_wrap` 两个用例；若不拆分，则剔除所有字典打标，保持 3 阶段硬件流水（约 25 行，符合长连续说明）。
* **范围差异**：无。
* **验证**：FIFO 硬件指针与状态位验证。

---

### [Case 06] can_p1_006_rx_fifo_blocking_and_overwrite
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_006_rx_fifo_blocking_and_overwrite`，原 200 行。
* **参数节点**：`fifo` (0/1), `overwrite` (True/False)。
* **目的**：验证 RX FIFO 在满载后的两种策略：Blocking（丢弃新帧并报溢出）与 Overwrite（覆盖最旧帧并更新指针）。
* **资源**：`can0`, FIFO0/1。
* **输入**：满载后的溢出注入帧。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置模式 $	o$ 连续填满 FIFO $	o$ 注入第 N+1 帧 $	o$ 检查丢弃或覆盖内容。
* **连续性**：独立节点。
* **观测**：`rx_fifo_status_get` 中的 `overflow` 标志与读出数据比对。
* **判据**：Blocking 下第 N+1 帧丢失，保留旧帧；Overwrite 下旧帧被覆盖，最新帧入队。
* **清理**：清空 FIFO。
* **修改方案**：直接瘦身至 18 行，参数化驱动。
* **范围差异**：无。
* **验证**：溢出与覆盖硬件标志核对。

---

### [Case 07] can_p1_007_dedicated_rx_buffer_boundaries
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_007_dedicated_rx_buffer_boundaries`，原 288 行。
* **参数节点**：无（固定遍历首末专用 Buffer 槽位）。
* **目的**：验证专用接收缓冲区 (Dedicated RX Buffers) 的独立寻址、首末边界过滤与 NDAT（新数据到达）标志。
* **资源**：`can0`, 专用 RX Buffer 0 与最大 Buffer N。
* **输入**：分别命中不同 Buffer 槽位的特定 ID 帧。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置专用 Buffer 路由 $	o$ 发送匹配首槽的帧 $	o$ 检查 `ndat1` 相应位 $	o$ 读数据并清除 NDAT $	o$ 发送末槽帧 $	o$ 重复验证。
* **连续性**：首槽与末槽彼此独立。
* **观测**：`can.rx_buffer_read`，`can.rx_buffer_status_get`。
* **判据**：对应 NDAT 位置 1，读出数据完全匹配，清零后 NDAT 位归零。
* **清理**：清零 NDAT。
* **修改方案**：可拆分或直接瘦身，剥离冗余的全局配置打印，保留边界读写。
* **范围差异**：无。
* **验证**：专用 Buffer 硬件状态位验证。

---

### [Case 08] can_p1_008_tx_fifo_queue_order
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_008_tx_fifo_queue_order`，原 164 行。
* **参数节点**：`mode` (FIFO 模式 vs 优先级队列 Queue 模式)。
* **目的**：验证发送缓冲在 FIFO 模式（先请求先发）与 Queue 模式（ID 小的优先发送）下的仲裁次序。
* **资源**：`can0`, TX Buffers。
* **输入**：乱序写入多个不同 ID 的待发报文。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：进入 INIT $	o$ 设定 TX 模式 $	o$ 写入乱序 ID 报文 $	o$ 一次性请求发送 $	o$ 按接收端收到的顺序校验仲裁结果。
* **连续性**：单次写入发送完成，独立节点。
* **观测**：接收端接收帧的序列。
* **判据**：FIFO 模式下严格按请求序号出队；Queue 模式下优先由最小 ID 报文出队。
* **清理**：标准清理。
* **修改方案**：直接瘦身至 16 行，消除报告样板代码。
* **范围差异**：无。
* **验证**：硬件出队时序核对。

---

### [Case 09] can_p1_009_tx_event_fifo_watermark_full_and_recovery
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_009_tx_event_fifo_watermark_full_and_recovery`，原 291 行。
* **参数节点**：无。
* **目的**：验证发送事件 FIFO (TX Event FIFO) 的事件记录、水位、满溢及确认恢复。
* **资源**：`can0`, TX Event FIFO。
* **输入**：连续发送报文产生发送事件记录。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置 Event FIFO $	o$ 连续发送报文 $	o$ 读取事件水位状态 $	o$ 达到满载 $	o$ Ack 读取事件 $	o$ 恢复可用空间。
* **连续性**：填充 $	o$ 满 $	o$ 恢复三阶段连续。
* **观测**：`can.tx_event_fifo_status_get`，`can.tx_event_read`。
* **判据**：每个发送完成的帧产生一个包含正确 ID、Timestamp 和 Marker 的事件；满时报 full；ack 后恢复。
* **清理**：清空 Event FIFO。
* **修改方案**：保留连续发送与校验逻辑，剔除 26 处 observation 打标，控制在 25 行左右。
* **范围差异**：无。
* **验证**：发送事件 FIFO 硬件状态验证。

---

### [Case 10] can_p1_010_message_marker_width
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_marker.py`，`def test_can_p1_010_message_marker_width`，原 221 行。
* **参数节点**：`marker_bits` (8-bit 或 16-bit)。
* **目的**：验证发送报文标记 (Message Marker) 在 8 位与 16 位模式下的透传完整性。
* **资源**：`can0`, TX Event FIFO。
* **输入**：携带极值 Marker（如 0xFF, 0xFFFF）的发送帧。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置 Marker 宽度 $	o$ 写入带 Marker 的 TX 帧 $	o$ 发送 $	o$ 读回 TX Event 中的 Marker $	o$ 断言相等。
* **连续性**：独立节点。
* **观测**：TX Event 结构体中的 `marker` 字段。
* **判据**：8-bit 模式下低 8 位匹配高位截断；16-bit 模式下全 16 位匹配。
* **清理**：标准收尾。
* **修改方案**：直接瘦身至 15 行，去除长文本说明。
* **范围差异**：无。
* **验证**：Marker 比特位硬件校验。

---

### [Case 11] can_p1_011_irq_lines_and_clear
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_011_irq_lines_and_clear`，原 227 行（整体函数跨度达 700+ 行）。
* **参数节点**：`mode`, `tx_line` (Line 0 / Line 1)。
* **目的**：验证 CAN 中断向 Line 0 或 Line 1 的选通分派，以及写 1 清零 (W1C) 机制。
* **资源**：`can0`, IRQ Line 0, IRQ Line 1, `can_irq_peer`。
* **输入**：发送完成事件或接收中断刺激。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置中断引脚绑定 $	o$ 开启特定中断使能 $	o$ 产生中断刺激 $	o$ 读取引脚事件 $	o$ 下发清除命令 $	o$ 确认事件清零。
* **连续性**：触发 $	o$ 捕获 $	o$ 清除连续。
* **观测**：`can.irq_line_event_get`，`can.irq_status_get`。
* **判据**：中断仅在选定的引脚触发；执行 Clear 后状态寄存器归零。
* **清理**：解绑引脚并清零。
* **修改方案**：拆分或深度瘦身，移除冗余的轮转等待，只测选定 Line，收缩至 20 行以内。
* **范围差异**：无。
* **验证**：真实单片机引脚与 ISR 事件核验。

---

### [Case 12] can_p1_012_bitrate_matrix
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_rates.py`，`def test_can_p1_012_bitrate_matrix`，原 200 行。
* **参数节点**：`nominal_bitrate` (250k, 500k, 1M), `data_bitrate` (2M, 5M)。
* **目的**：验证外部实体总线上多种标称与数据波特率组合的无错通信能力。
* **资源**：`can0` (DUT), 外部硬件 Peer (盒子/第二通道)。
* **输入**：不同波特率预分频与时序参数配置。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：双方配置一致时钟与时序 $	o$ DUT 发送 $	o$ Peer 接收 $	o$ Peer 回发 $	o$ DUT 接收校验。
* **连续性**：独立波特率组合。
* **观测**：双向接收帧数据及错误计数器 (`error_counters_get`)。
* **判据**：收发数据完全一致，无位错误或总线错误发生 (`tec == 0, rec == 0`)。
* **清理**：停止收发。
* **修改方案**：直接瘦身至 18 行，去除繁复的报告字符串。
* **范围差异**：无。
* **验证**：真实物理总线外部传输闭环。

---

### [Case 13] can_p1_013_internal_timestamp
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_timestamp.py`，`def test_can_p1_013_internal_timestamp`，原 230 行。
* **参数节点**：`divisor` (1, 4, 16 等分频系数)。
* **目的**：验证内部 16-bit 时间戳计数器的分频精度、报文时间戳打标及计数器回绕。
* **资源**：`can0`, 内部时间戳计数器。
* **输入**：预设分频系数，固定间隔的报文收发。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置时间戳分频 $	o$ 读初始时间戳 $	o$ 发送接收报文 $	o$ 读报文附带时间戳 $	o$ 等待计数器自增 $	o$ 校验时间戳增量。
* **连续性**：必须注意单次读取（避免清除副作用）。
* **观测**：`can.timestamp_get`，接收帧中的 `timestamp`。
* **判据**：时间戳随时间单调递增，增量符合所选分频系数的物理时间。
* **清理**：标准收尾。
* **修改方案**：直接瘦身至 18 行，提取时间换算辅助。
* **范围差异**：无。
* **验证**：内部硬件计时器精度比对。

---

### [Case 14] can_p1_014_timeout_sources
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_timeout.py`，`def test_can_p1_014_timeout_sources`，原 233 行。
* **参数节点**：`source` (CONTINUOUS, TX_EVENT_FIFO, RX_FIFO0, RX_FIFO1)。
* **目的**：验证 4 种超时计数器源的计时触发与暂停控制（连续模式自减，FIFO 模式非空时自减）。
* **资源**：`can0`, 超时计数器。
* **输入**：超时周期设定值，空/非空 FIFO 状态切换。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. 设定超时源为目标 FIFO，注入数据使 FIFO 非空。
  2. 启动超时计数器 $	o$ 等待至少 2 倍超时周期。
  3. 观察超时中断置位 $	o$ 清空 FIFO $	o$ 确认计数器暂停。
* **连续性**：**必须连续**（状态演进不可插 reset）。
* **观测**：超时中断事件及计数器当前值。
* **判据**：FIFO 非空时能自然超时；FIFO 空时计数器停止且不产生中断。
* **清理**：清空 FIFO 并关闭超时中断。
* **修改方案**：去除中间阶段的冗余日志，保持连续观测（允许 25 行左右长用例）。
* **范围差异**：无。
* **验证**：超时硬件事件与周期测量。

---

### [Case 15] can_p1_015_clock_stop_and_recovery
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_015_clock_stop_and_recovery`，原 156 行。
* **参数节点**：无。
* **目的**：验证低功耗时钟停止 (Clock Stop Request) 协议应答及总线活动/软件恢复。
* **资源**：`can0`。
* **输入**：CSR 寄存器控制位。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：进入预备态 $	o$ 请求时钟停止 $	o$ 等待硬件应答 (Clock Stop Acknowledge) $	o$ 触发解除停止 $	o$ 发送报文验证通信功能完整恢复。
* **连续性**：时钟停止到恢复属于单次时序验证。
* **观测**：`can.clock_stop_get`，恢复后的回环报文数据。
* **判据**：请求后正确返回 ACK；恢复后通信无丢包、寄存器可读写。
* **清理**：恢复时钟。
* **修改方案**：直接瘦身至 15 行极简结构。
* **范围差异**：无。
* **验证**：低功耗控制与总线恢复硬件事实。

---

### [Case 16] can_p1_016_message_ram_march
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1.py`，`def test_can_p1_016_message_ram_march`，原 223 行。
* **参数节点**：无。
* **目的**：对 CAN 整个 16KB 消息 RAM 区域执行固定模式、地址模式及 March C- 内存内建自测，并在测试后不复位重建回环以证明恢复能力。
* **资源**：`can0`, 全部 Message RAM（通常 0 ~ 16KB）。
* **输入**：固定模式 (0x5A5A5A5A, 0xA5A5A5A5)，地址模式，March 6 阶段 (w0, up_r0w1, up_r1w0, down_r0w1, down_r1w0, r0)。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. 进入 INIT $	o$ 遍历写固定值 $	o$ 遍历读回比对。
  2. 遍历执行 March C- 读写状态机。
  3. 配置回环参数 $	o$ 退出 INIT $	o$ 发送单帧回环验证 RAM 可用性。
* **连续性**：**绝对不可打断的连续测试**（中间禁止任何 reset）。
* **观测**：`ram_words_read`，`ram_words_exchange`，最终回环的 `rx_read`。
* **判据**：全部 16KB RAM 单元读出与期望无一比特差异；后续回环成功。
* **清理**：下一用例开头的 reset 会重置 RAM 状态。
* **修改方案**：
  * 切片分块与 March 循环模式提取为文件内纯数据助手函数；
  * Case 主体只保留“March执行 $	o$ 回环验证”，约 35 行，附合规说明。
* **范围差异**：无（全量遍历，严禁抽样）。
* **验证**：全 RAM 空间逐 word 读写比对。

---

### [Case 17] can_p1_018_tsu_capture
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_tsu.py`，`def test_can_p1_018_tsu_capture`，原 378 行。
* **参数节点**：`timebase` (内部时钟 vs 外部 STIMER 参考)。
* **目的**：验证高精度时间戳单元 (TSU) 在外设触发事件下的精准捕获与防溢出保护。
* **资源**：`can0`, TSU 寄存器, `can_stimer_reference`。
* **输入**：不同的时基配置，发送/接收触发信号。
* **前置**：`can_handle.reset()`，STIMER 重置。
* **硬件顺序**：配置 TSU 时基 $	o$ 开启捕获 $	o$ 激发报文事件 $	o$ 读取 TSU 捕获值并与参考时钟比对。
* **连续性**：必须保持时钟参考与 TSU 运行状态同步。
* **观测**：`can.tsu_capture_get`，`stimer.counter_get`。
* **判据**：捕获值与 STIMER 计数值在线性容差范围内完全对应。
* **清理**：停止 TSU 捕获与 STIMER。
* **修改方案**：消除大量冗余的时基单位换算打印，保持硬件调用时序，约 25 行。
* **范围差异**：无。
* **验证**：双时钟源关联精度核对。

---

### [Case 18] can_p1_020_fd_format_matrix
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_format.py`，`def test_can_p1_020_fd_format_matrix`，原 252 行。
* **参数节点**：`length` (0~64), `dut_non_iso`, `peer_non_iso`。
* **目的**：验证 ISO 与 Non-ISO CAN FD 报文在不同数据长度下的协议互通与错误识别。
* **资源**：`can0` (DUT), 外部 Peer。
* **输入**：不同载荷长度及 ISO/Non-ISO 配置位。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：双方配置匹配/不匹配格式 $	o$ 发送测试帧 $	o$ 检查正常接收或协议异常。
* **连续性**：独立参数化节点。
* **观测**：接收数据长度、CRC 状态、协议异常标志。
* **判据**：格式匹配时全长通信无误；格式失配（ISO vs Non-ISO）时必须被丢弃或报协议异常。
* **清理**：标准收尾。
* **修改方案**：参数化驱动，直接瘦身至 18 行。
* **范围差异**：无。
* **验证**：真实外部对端协议帧比对。

---

### [Case 19] can_p1_021_tdc_external_fd
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p1_tdc.py`，`def test_can_p1_021_tdc_external_fd`，原 191 行。
* **参数节点**：`data_bitrate` (2M, 5M)。
* **目的**：验证在高速 CAN FD 数据段开启发射机延迟补偿 (TDC) 时，延迟测量值与无误码通信。
* **资源**：`can0`, 外部收发器线路。
* **输入**：高速率（如 5 Mbps）、TDC 补偿偏移值。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：进入 INIT $	o$ 启用 TDC 并设置 Offset/Filter $	o$ 退出 INIT $	o$ 发送高速报文 $	o$ 读回 TDC 测得值与错误状态。
* **连续性**：单次收发测试。
* **观测**：`can.tdc_status_get`（获取实际 measured delay）。
* **判据**：测得延迟在收发器物理传播延时合法范围内，传输无位错误。
* **清理**：关闭 TDC。
* **修改方案**：直接瘦身至 16 行。
* **范围差异**：无。
* **验证**：收发器硬件回路延迟量测核对。

---

### [Case 20] can_p2_001_dmu_tx_rx
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_dmu.py`，`def test_can_p2_001_dmu_tx_rx`，原 360 行。
* **参数节点**：`fifo` (0 或 1)。
* **目的**：验证通过片内直接内存单元 (DMU) / DMA 引擎将接收 FIFO 报文自动搬运至 SRAM，以及从 SRAM 自动搬运至 TX Buffer 发送。
* **资源**：`can0`, DMU, DMA 通道, SRAM 资源池。
* **输入**：DMA 通道配置、源/目的地址、传输元素计数。
* **前置**：`dma.stop()` $	o$ `can_handle.reset()`。
* **硬件顺序**：
  1. 在 SRAM 分配 RX/TX 缓冲区。
  2. 先启动 RX DMA 待命 $	o$ 外部注入/回环发送。
  3. 硬件自动触发 DMA 搬运 $	o$ 校验 SRAM 中数据内容。
  4. 启动 TX DMA $	o$ 自动触发 CAN 发送 $	o$ 校验发送完成。
* **连续性**：**必须连续**（RX 先于 TX，DMA 搬运时序不可打乱）。
* **观测**：DMA 完成标志、SRAM 内存数据、CAN FIFO 状态。
* **判据**：SRAM 中的报文头与数据完全等于物理接收数据；DMA 传输计数归零。
* **清理**：停止 DMA 通道，释放资源。
* **修改方案**：剔除通用上下文包装，保持 DMA 真实流水线，约 25 行。
* **范围差异**：无。
* **验证**：真实 DMA 硬件搬运核验。

---

### [Case 21] can_p2_002_dmu_tx_event
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_dmu.py`，`def test_can_p2_002_dmu_tx_event`，原 290 行。
* **参数节点**：无。
* **目的**：验证 DMU 自动将发送事件 FIFO (TX Event FIFO) 记录通过 DMA 搬移到 SRAM 缓冲区。
* **资源**：`can0`, DMU, DMA, SRAM。
* **输入**：多帧连续发送，DMA 传输描述符。
* **前置**：`dma.stop()` $	o$ `can_handle.reset()`。
* **硬件顺序**：配置 Event FIFO 的 DMA 触发源 $	o$ 启动 DMA $	o$ 触发多次 CAN 发送 $	o$ 校验 SRAM 中批量写入的事件记录。
* **连续性**：必须保持触发与接收的时序。
* **观测**：SRAM 缓冲区中的 `CanTxEvent` 结构体数组。
* **判据**：SRAM 中的事件条目数、Timestamp、Marker、ID 与实际发送完全一致。
* **清理**：停止 DMA。
* **修改方案**：精简至 20 行以内。
* **范围差异**：无。
* **验证**：事件 DMA 硬件搬运核验。

---

### [Case 22] can_p2_003_ecc_interrupt_chain
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_ecc.py`，`def test_can_p2_003_ecc_interrupt_chain`，原 179 行（旧长版 215 行）。
* **参数节点**：`source` (CORRECTED, UNCORRECTED)。
* **目的**：验证 ECC 单比特纠正与双比特不可纠正错误的 Force 故障注入、屏蔽、单源清除及重复投递中断链。
* **资源**：`can0`, ECC 注入控制。
* **输入**：`CanEccSource` 错误源。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. `ecc_capture_start(source)` $	o$ `ecc_force(source)` $	o$ `ecc_mask_set(source, False)`
  2. `wait_ecc_event(0)` $	o$ 校验首发事件
  3. `ecc_clear(source)` $	o$ 校验清零
  4. 二次 `ecc_force(source)` $	o$ 校验 event_count 增至 2
* **连续性**：**必须连续**（保持同代 generation 状态）。
* **观测**：ECC ISR 事件结构体 (`wait_ecc_event`)，ECC 状态快照 (`ecc_snapshot_get`)。
* **判据**：`event.latched_events == source`，`event.event_count` 正确递增，状态位匹配。
* **清理**：解绑并清零 ECC 错误。
* **修改方案**：**本项目的核心标杆样板！** 砍掉跨实例外层循环，直接单实例 `can0` 运行，16 行极简落地。
* **范围差异**：不再轮转测试多个 CAN 实例的共享线路串扰。
* **验证**：真实 ECC 中断触发与 ISR 记录核对。

---

### [Case 23] can_p2_004_instance_ram_isolation
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2.py`，`def test_can_p2_004_instance_ram_isolation`，原 254 行。
* **参数节点**：无（操作 CAN0 与 CAN1 两个句柄）。
* **目的**：验证两个物理 CAN 实例的消息 RAM 映射地址完全隔离，互不产生覆盖副作用。
* **资源**：`can0`, `can1` 两个真实硬件实例。
* **输入**：向 CAN0 写入特定 Pattern，向 CAN1 写入对照 Pattern。
* **前置**：双实例分别复位。
* **硬件顺序**：写 CAN0 RAM $	o$ 读 CAN1 确认未改变 $	o$ 写 CAN1 RAM $	o$ 读 CAN0 确认未改变。
* **连续性**：双实例交互。
* **观测**：两者的 `ram_words_read`。
* **判据**：双方独立隔离，无交叉写入。
* **清理**：双方复位。
* **修改方案**：
  * **单实例策略特例**：在纯单实例策略下，本用例无法在保留原物理意义的同时单实例运行。
  * **按《指导》第 3.2 节处理**：明确列为“单实例范围调整项”，保留原定义，不强行缩水成伪测试。
* **范围差异**：若单实例执行，标记为移出或保留双实例专测。
* **验证**：双实例真实硬件寻址边界。

---

### [Case 24] can_p2_005_loopback_pin_comparison
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_loopback.py`，`def test_can_p2_005_loopback_pin_comparison`，原 191 行。
* **参数节点**：无。
* **目的**：对比内部回环 (Internal Loopback) 与外部引脚回环 (External Loopback) 的总线物理电平与自收自发表现。
* **资源**：`can0`, 外部收发器。
* **输入**：标准回环测试报文。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置内部回环发送 $	o$ 校验总线静默 $	o$ 切换为外部引脚模式发送 $	o$ 校验物理引脚电平联动。
* **连续性**：两种模式对比。
* **观测**：RX 帧内容及 GPIO 线路电平状态。
* **判据**：内部模式不影响外部引脚；外部模式引脚信号与数据严格对应。
* **清理**：切回初始模式。
* **修改方案**：消除重复复位与大段报告生成，精简至 18 行。
* **范围差异**：无。
* **验证**：引脚与回环逻辑电平核查。

---

### [Case 25] can_p2_007_dmu_illegal_irq
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_dmu_errors.py`，`def test_can_p2_007_dmu_illegal_irq`，原 365 行。
* **参数节点**：`fault` (非法地址, 非对齐访问等), `expected_error`。
* **目的**：验证 DMU 在非法配置或硬件总线异常时，能够准确捕获错误并触发故障中断，且故障可清除。
* **资源**：`can0`, DMU, DMA 错误中断通道。
* **输入**：故意构造的越界物理地址或错误长度参数。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置非法 DMU 描述符 $	o$ 触发传输 $	o$ 等待错误中断 $	o$ 读取并断言错误寄存器 $	o$ 清除错误标志。
* **连续性**：**必须连续**（不能被自动重试或额外 reset 冲掉故障现场）。
* **观测**：DMU 错误中断事件、硬件状态寄存器中的 Fault 码。
* **判据**：错误中断准确命中，`error_code == expected_error`，清除后恢复正常。
* **清理**：清空错误状态。
* **修改方案**：去除外层防御性重试，确保非法刺激直接命中下位机，收敛至 22 行。
* **范围差异**：无。
* **验证**：硬件故障注入与保护机制核验。

---

### [Case 26] can_p2_008_dmu_rx_timestamp
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_dmu_tsu.py`，`def test_can_p2_008_dmu_rx_timestamp`，原 419 行。
* **参数节点**：`fifo`, `transfer_timestamp`, `overwrite`。
* **目的**：验证在开启 TSU 高精度时间戳的情况下，DMU 自动将包含时间戳信息的扩展帧头完整搬移到 SRAM 中。
* **资源**：`can0`, DMU, TSU, DMA。
* **输入**：带有时间戳捕获的 CAN 报文。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：配置 TSU $	o$ 配置带时间戳的 DMU 描述符 $	o$ 激发报文到达 $	o$ DMA 自动传输 $	o$ 读取 SRAM 校验时间戳元数据。
* **连续性**：TSU 与 DMU 联合运行。
* **观测**：SRAM 中的 Header 数据（包含 32-bit 或 64-bit 时间戳）。
* **判据**：SRAM 里的时间戳非零且与硬件时钟增量一致。
* **清理**：停止 TSU 与 DMA。
* **修改方案**：消除大篇幅的时钟转换与元数据字典包装，精炼至 25 行。
* **范围差异**：无。
* **验证**：DMA 搬移时间戳字段的比特级核验。

---

### [Case 27] can_p2_010_ram_watchdog
* **定位**：`pc/et_test_platform/test_cases/can/test_can_p2_watchdog.py`，`def test_can_p2_010_ram_watchdog`，原 394 行。
* **参数节点**：无。
* **目的**：验证 CAN 消息 RAM 看门狗定时器 (RAM Watchdog) 在内存访问超时下的告警与保护恢复机制。
* **资源**：`can0`, RAM Watchdog 计数器, `can_stimer_reference`。
* **输入**：门限值设定，8/8/1 帧连续高速报文刺激。
* **前置**：`can_handle.reset()`。
* **硬件顺序**：
  1. 阶段 1（门限生效）：设置门限为 1 $	o$ 发送报文产生密集访问 $	o$ 观察看门狗事件。
  2. 阶段 2（关闭对比）：关闭看门狗 $	o$ 相同刺激下确认无事件。
  3. 阶段 3（恢复重开）：重新开启看门狗 $	o$ 恢复告警能力。
* **连续性**：**3 阶段绝对连续**（阶段间严禁执行 `can.reset()`，否则破坏门限与恢复语义）。
* **观测**：看门狗中断标志、STIMER 耗时证据。
* **判据**：真实 WDI 中断触发（严禁用软件 Force 伪造），关闭期间绝不误报，重开后恢复。
* **清理**：关闭看门狗并清除中断。
* **修改方案**：
  * 保留 3 阶段连续测试核心，剔除所有手动 JSON 生成与几十处 observation；
  * 保持 30~35 行紧凑流水线，提供合规超长说明。
* **范围差异**：无。
* **验证**：真实看门狗硬件触发与恢复。

---

## 3. Case / Driver 调用图与依赖边界

### 当前混乱依赖链
```text
Case 
  ├──> _support.py (CrcSupport/CanSupport 聚合怪)
  │      ├──> CanDriver (1000+ 行，封装了上下文管理器、轮询预算)
  │      ├──> CrgDriver (手写 reset)
  │      └──> ResourceDriver (手写 reset)
  ├──> case_cleanup_scope (手写闭包列表)
  ├──> record_observation (1000+ 次侵入式打标)
  └──> write_json_result (手写本地落盘)
```

### 极简重构后目标依赖链
```text
Case (<=20行，纯三段式)
  ├──> can.reset() (原子化一键复位)
  ├──> can.xxx() (直观硬件操作 API，如 init/write/read)
  └──> assert actual == expected (Pytest 原生断言)

CanDriver (薄驱动，职责单一)
  ├──> reset() ────> 调 CRG 发送硬件复位
  │            ├──> 发送 CanCommand.CONTEXT_RESET 给固件
  │            └──> 调 ResourceDriver 重置资源池
  └──> 普通方法 ──> 参数打包 -> self._request(CMD) -> 解包返回
```

---

## 4. 现行规则 (R200 / R210) 冲突与最小同步点

1. **R200 (PC分层规则) 冲突点**：
   * *原规则*：禁止 Driver 跨 IP 调用其他 Driver。
   * *最小同步*：明确将 `CanDriver.reset()` 作为**唯一允许的生命周期组合例外**，允许其内部协调 CRG 与 Resource，但严禁普通业务方法跨 IP。
2. **R210 (Case责任规则) 冲突点**：
   * *原规则*：要求 Case 显式包含 CRG 复位和 Resource 复位代码，并用 `case_cleanup_scope` 包裹。
   * *最小同步*：认可第一行调用 `can.reset()` 即为完整前置隔离基线，异常清理统一交由 pytest fixture 兜底，Case 正文彻底取缔 `case_cleanup_scope`。

---

## 5. 阶段 A 验收结论与进入阶段 B 准入准则

* **阶段 A 结论**：
  27 个 Case 的硬件时序、输入、观测点和判据已全部吃透锁定，没有任何功能被遗漏，没有任何暗坑未被识别。
* **阶段 B 准入清单**：
  1. 固件 `firmware/services/src/et_can_service.c` 增加 `handle_context_reset` 处理；
  2. PC `pc/et_test_platform/drivers/can/contract.py` 注册 `CanCommand.CONTEXT_RESET = 98`；
  3. `CanDriver` 增加原子 `reset()` 方法并完成无硬件依赖的协议级软件测试。
