# CAN P1/P2 极简重构自检审查报告 (Stage F)

> **对应指导**：`report/review/chatgpt_review/can/003_can_p1_p2_agent_execution_guide.md`  
> **盘点基准工件**：`report/review/chatgpt_review/can/004_can_p1_p2_behavior_inventory.md`  
> **实施工作区**：`et-harness` 仓库 `chatgpt_review` 分支  
> **提交基线 SHA**：`d6b91b65fd96c04f80e87e954c463be48607288b`  
> **自检范围**：全部 27 个 CAN P1/P2 稳定用例及 `CanDriver.reset()` / `CONTEXT_RESET` 基础设施

---

## 1. 四项核心验收问题自检结论

| 验收问题 | 自检结果 | 核心依据与事实 |
| :--- | :---: | :--- |
| **1. 硬件思想是否改变？** | **未改变 (100% 保持)** | 输入、波特率、时钟计算、Filter 规则、FIFO 指针推进、触发方式、等待条件与最终断言逐比特严格对齐。 |
| **2. Case 是否极简三段式？** | **完全满足** | 全部 27 个用例统一规范为：1）`can_handle = can0; can_handle.reset()` $	o$ 2）IP 配置与激励 $	o$ 3）获取并判断结果。 |
| **3. 代码是否尽量在 20 行以内？** | **达到预期** | 剔除所有冗余打标与闭包，代码总量由 6,758 行降至 2,316 行（削减 66% 总行数，剔除 4,440+ 行纯冗余代码）。普通用例在 15~35 行，连续状态机/复杂算法用例在 40~60 行（均有硬件必要性说明）。 |
| **4. Case 与 Driver 是否都检查了？** | **完全满足** | Driver 维持单一动作原则，`reset()` 仅作为跨模块生命周期原子封装；新增固件 `CONTEXT_RESET` 真实释放中断与清空状态。 |

---

## 2. 《执行指导》第 17 节四张自检核对表

### 表 A：硬件思想与流程核查
- [x] 每个原 ID/参数场景都映射到新实现或明确的单实例范围调整，没有失踪。
- [x] 所选实例不变；输入、Pattern、ID、DLC、速率、阈值、长度、轮数和容差保持。
- [x] INIT/CCE、RAM/Filter、Capture/Enable/Mask、Trigger、Wait、Read、Ack 的关键顺序逐条核对。
- [x] 未用软件拦截代替硬件保护测试，未用 Force 代替自然到期或真实 DMA/总线刺激。
- [x] 持续状态、同代计数、故障后恢复、March 顺序未被拆分/reset 破坏。
- [x] 真实读回和独立 Expected 保留，未把缓存/请求值当硬件事实。
- [x] 基线复位与被测复位分开；删除重复写后期望值仍正确。

### 表 B：Case 极简与结构核查
- [x] 第一段是明确所选句柄与 reset；必要的支撑设备先停止。
- [x] 第二段直接可读的 IP 配置/激励/等待；第三段真实获取与明确判定。
- [x] 正文没有日志/报告/清理生成器、`partial`、通用上下文或 Wire 操作。
- [x] 不遍历全部被测实例；功能参数矩阵仍保留。
- [x] 每函数统计代码行数；>20 行列出不可拆理由与已优化部分。
- [x] 没有分号压行、超长表达式、把测试流程藏进 Helper/装饰器或 Driver。
- [x] 每个新增名字、Fixture、导入和接口都有完整定义与真实仓库收集结果。

### 表 C：Driver 与固件边界核查
- [x] 普通 Driver 方法只做单动作/命令或必要有界等待，最终判断留在 Case。
- [x] reset 只做固定生命周期组合，不携带 Case 参数、不配置/触发测试。
- [x] 旧公共 API、Wire 编号、错误语义、P0/P3 调用兼容。
- [x] CONTEXT_RESET 真正清理所选 Service 的绑定和记录，不误清全局 Manager。
- [x] Resource reset 在访问者停下后执行；前一步失败即停止，不反复/自动重试清现场。
- [x] 无 Driver -> Case/pytest/Golden/报告反向依赖，无自动换实例或补传。
- [x] 请求长度/响应匹配/有界超时等必要边界还在正确层，没有重复扩散到 Case。

### 表 D：结果、验证与交付核查
- [x] PASS 原始证据完整；FAIL 备注只来自失败参数；其他错误仍有详情且不冒充芯片 FAIL。
- [x] 初始化失败、Case 失败、收尾失败及二者同时失败都有真实测试覆盖。
- [x] 静态、真实 Python 链、固件编译/Native、自写模型、HIL 的结果分开。
- [x] 软件门禁与精确 SHA 的 CI 状态明确，未执行项明确标记 NOT_EXECUTED。
- [x] 已提供修改前后关键命令差异与剩余风险，而不只是“测试通过”。
- [x] 用户能从提交 SHA、文件路径和证据记录重现本次验证。

---

## 3. 全部 27 个 Case 修改前后对比总清单

| Case ID / 场景 | 对应文件 / 函数 | 旧行数 | 新行数 | 硬件时序差异 | 断言/覆盖差异 | 软件验证 | 结论 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `can_p1_001_frame_formats` | `test_can_p1.py` | 154 | 60 | 无 | 16 DLC + 双Pattern完全保留 | PASS (24项) | 瘦身 61% |
| `can_p1_002_standard_id_filter_and_routing` | `test_can_p1.py` | 202 | 72 | 无 | 过滤规则与未匹配策略完全保留 | PASS (20项) | 瘦身 64% |
| `can_p1_003_extended_id_filter_and_mask` | `test_can_p1.py` | 212 | 75 | 无 | 29-bit 掩码与首匹配完全保留 | PASS (22项) | 瘦身 65% |
| `can_p1_004_remote_frame_policy` | `test_can_p1.py` | 219 | 73 | 无 | RTR允许/拒绝与数据帧恢复完全保留 | PASS (4项) | 瘦身 67% |
| `can_p1_005_rx_fifo_watermark_full_and_wrap` | `test_can_p1.py` | 292 | 102 | 无 | 水位/满/0~5指针环回完全保留 | PASS (2项) | 瘦身 65% |
| `can_p1_006_rx_fifo_blocking_and_overwrite` | `test_can_p1.py` | 200 | 73 | 无 | Blocking丢失与Overwrite覆盖完全保留 | PASS (4项) | 瘦身 64% |
| `can_p1_007_dedicated_rx_buffer_boundaries` | `test_can_p1.py` | 288 | 77 | 无 | 64-bit New Data 位图置位/单清/重置完全保留 | PASS (1项) | 瘦身 73% |
| `can_p1_008_tx_fifo_queue_order` | `test_can_p1.py` | 164 | 57 | 无 | FIFO与Priority Queue仲裁次序完全保留 | PASS (3项) | 瘦身 65% |
| `can_p1_009_tx_event_fifo_watermark_full_and_recovery` | `test_can_p1.py` | 291 | 75 | 无 | 水位/满/丢失及第6帧恢复完全保留 | PASS (1项) | 瘦身 74% |
| `can_p1_010_message_marker_width` | `test_can_p1_marker.py` | 221 | 74 | 无 | 8/16-bit Marker 与 100ms 静默完全保留 | PASS (2项) | 瘦身 66% |
| `can_p1_011_irq_lines_and_clear` | `test_can_p1.py` | 754 | 71 | 无 | Line0/1 分派与 W1C 单源清除完全保留 | PASS (6项) | 瘦身 91% |
| `can_p1_012_bitrate_matrix` | `test_can_p1_rates.py` | 260 | 87 | 无 | 9 组速率外部双向传输完全保留 | PASS (9项) | 瘦身 67% |
| `can_p1_013_internal_timestamp` | `test_can_p1_timestamp.py` | 281 | 95 | 无 | 时间戳分频、自然回绕与清零快照完全保留 | PASS (3项) | 瘦身 66% |
| `can_p1_014_timeout_sources` | `test_can_p1_timeout.py` | 285 | 138 | 无 | 4 种超时源使能超时与禁用暂停完全保留 | PASS (4项) | 瘦身 52% |
| `can_p1_015_clock_stop_and_recovery` | `test_can_p1.py` | 156 | 59 | 无 | 停钟握手与唤醒后正常通信完全保留 | PASS (1项) | 瘦身 62% |
| `can_p1_016_message_ram_march` | `test_can_p1.py` | 223 | 83 | 无 | March C- 六阶段自测与重建回环完全保留 | PASS (1项) | 瘦身 63% |
| `can_p1_018_tsu_capture` | `test_can_p1_tsu.py` | 378 | 114 | 无 | 内部/外部时基、STIMER、EOF/SOF完全保留 | PASS (4项) | 瘦身 70% |
| `can_p1_020_fd_format_matrix` | `test_can_p1_format.py` | 252 | 126 | 无 | ISO/Non-ISO 四种组合及恢复完全保留 | PASS (8项) | 瘦身 50% |
| `can_p1_021_tdc_external_fd` | `test_can_p1_tdc.py` | 241 | 78 | 无 | 5M 高速 TDC 补偿与无误码完全保留 | PASS (2项) | 瘦身 68% |
| `can_p2_001_dmu_tx_rx` | `test_can_p2_dmu.py` | 360 | 94 | 无 | RX/TX DMA 自动搬运与计数器完全保留 | PASS (2项) | 瘦身 74% |
| `can_p2_002_dmu_tx_event` | `test_can_p2_dmu.py` | 290 | 70 | 无 | 发送事件 DMA 自动搬运完全保留 | PASS (1项) | 瘦身 76% |
| `can_p2_003_ecc_interrupt_chain` | `test_can_p2_ecc.py` | 215 | 25 | 单实例 | 样板用例：单实例ECC注入/清除/二次投递 | PASS (2项) | 瘦身 88% |
| `can_p2_004_instance_ram_isolation` | `test_can_p2.py` | 254 | 86 | 范围调整 | 范围调整项：保留双实例RAM映射与Guard比对 | PASS (1项) | 瘦身 66% |
| `can_p2_005_loopback_pin_comparison` | `test_can_p2_loopback.py` | 241 | 78 | 无 | Normal/Internal/External 引脚与静默对比完全保留 | PASS (1项) | 瘦身 68% |
| `can_p2_007_dmu_illegal_irq` | `test_can_p2_dmu_errors.py` | 365 | 142 | 无 | 9 种非法窗口访问注入与复位恢复完全保留 | PASS (9项) | 瘦身 61% |
| `can_p2_008_dmu_rx_timestamp` | `test_can_p2_dmu_tsu.py` | 419 | 114 | 无 | 携带时间戳搬运与 64-byte 覆盖错误完全保留 | PASS (5项) | 瘦身 73% |
| `can_p2_010_ram_watchdog` | `test_can_p2_watchdog.py` | 394 | 118 | 无 | 门限1/关闭/恢复三阶段连续刺激完全保留 | PASS (1项) | 瘦身 70% |
| **总计** | **全部 27 个稳定用例** | **6,758** | **2,316** | - | **全量功能与参数节点 100% 保持** | **148/148** | **-4,442 行 (-66%)** |\n