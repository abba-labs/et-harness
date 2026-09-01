# AES 最小硬件证明集审查

> 状态：Review Draft（非规则、非运行结论）  
> 范围：仅审查 `AES_P0_001` ～ `AES_P3_003` 每个 Formal Case 至少需要哪些硬件反馈，才能证明“测试确实发生、硬件完成、结果成立”。  
> 本轮不修改 PC Case / Driver / Firmware / Wrap，不改变既有 PASS/FAIL。

## 1. 目的

`ip.md` 的测试方法回答“应该怎么测”；本审查回答另一个问题：**硬件至少要反馈什么，才足以证明这个 Case 真正测到了并且结论可信。**

后续统一按下面关系闭环：

```text
Feature / Steps
-> Minimum Hardware Proof Set
-> Runtime Observation / Artifact
-> Pass Criteria
-> Excel Remark / Execution Detail
```

最小证明集只保留决定结论的关键反馈，不要求给每个 Step 都打日志。若当前代码已经读取并断言但没有保存，归类为“记录缺口”；若当前代码根本没有形成足够证明，归类为“证明缺口”。

## 2. 状态定义

| 状态 | 含义 | 后续动作 |
|---|---|---|
| `OK` | 当前代码已经取得并判定关键硬件反馈 | 只需确认报告能展示 |
| `RECORD_GAP` | 当前代码已经取得/判定，但没有完整保留给报告 | 只补记录，不新增硬件动作 |
| `PROOF_GAP` | 当前执行逻辑本身还不足以证明目标 Feature | 需要最小受控测试增强 |
| `STATIC_GATE` | 本 Case 是静态能力门禁，不产生运行时硬件反馈 | 不伪装成硬件功能 PASS 证据 |

## 3. AES Case 最小硬件证明集

| Case | 最小硬件证明集 | 当前状态 | 说明 |
|---|---|---|---|
| `AES_P0_001` | 代表实例身份、`capability_gate_passed=true`；语义映射缺失时明确 SKIP | `STATIC_GATE` | 这是运行前静态门禁，不证明 AES 硬件运算功能 |
| `AES_P0_002` | 每个向量 `FINISH=true`；`produced_bytes=16`；16-byte Actual；Actual = NIST Expected = PC Golden | `RECORD_GAP` | 当前已读取/断言 FINISH，但 Artifact 未保留 FINISH |
| `AES_P0_003` | 两轮均取得 Actual、`produced_bytes=16`、`FINISH=true`；第二轮重新 Enable/Configure 后仍与独立 Golden 一致；两输入输出不同 | `RECORD_GAP` | 运行反馈已保留，建议补每轮 Expected 或 `data_match` 方便人审 |
| `AES_P1_001` | 每个 Padding 参数实例的 Actual；`produced_bytes=expected_output_length`；Actual = 独立 Golden | `OK` | 当前 Expected / Actual / produced_bytes 已结构化保存 |
| `AES_P1_002` | `IV_GET == IV_SET`；每个 IV 节点 Actual、`produced_bytes=16`；Actual = 对应 Golden；两 IV 输出不同 | `RECORD_GAP` | 当前读回和 Actual 已保存，但独立 Expected/比较关系未直接保留 |
| `AES_P1_003` | `DATA_LENGTH` bit32 读回正确；32-byte Actual；`produced_bytes=32`；完成后 `BUSY=false`、`FINISH=true` | `OK` | 当前关键硬件反馈均已保存 |
| `AES_P1_004` | LITTLE/BIG 两节点 Actual canonical bytes；`produced_bytes=16`；两节点均 = 同一 Golden | `OK` | 当前 Expected / Actual / produced_bytes 已保存 |
| `AES_P1_005` | 每个 Counter 的 16-byte Actual；`produced_bytes=16`；`FINISH=true`；Actual = 当前 Counter Golden | `OK` | 当前关键结果已保存 |
| `AES_P1_006` | 写入前 `DIN_REQ=1`；写块后请求被消费；若声明验证 W1C，则必须额外看到 **clear 前=1 -> W1C -> clear 后=0** | `PROOF_GAP` | 当前 W1C 执行前 DIN_REQ 已经是 0，不能证明 W1C 的 1→0 清除语义 |
| `AES_P1_007` | 读取前 `DOUT_REQ=1`；BLOCK_READ Actual = Golden；读取后请求被消费；若声明验证 W1C，则必须看到 **clear 前=1 -> W1C -> clear 后=0** | `PROOF_GAP` | 当前 W1C 执行前 DOUT_REQ 已因读取变成 0，不能证明 W1C 的 1→0 清除语义 |
| `AES_P1_008` | Actual = Golden；`produced_bytes=16`；W1C 前 `FINISH=1`；W1C 后 `FINISH=0` | `RECORD_GAP` | FINISH 转移已证明；建议补 Expected 或 `data_match` 供报告闭环 |
| `AES_P1_009` | 冲突后 `raw=0/status=0/latched=OUTPUT_CONFLICT`；`event_count+1`；清除后 OUTPUT_CONFLICT 在 raw/status/latched 均不存在 | `PROOF_GAP` | 当前清除后只确认 RAW，未证明 Service latched 同步清除 |
| `AES_P1_010` | `latched=KEY_MISSING` 且 `event_count+1`；ISR 后 raw/status=0；clear 后 raw/status/latched 全 0 | `RECORD_GAP` | 当前 event_count 被断言但 Artifact snapshot 未保存该计数 |
| `AES_P1_011` | `latched=IV_MISSING` 且 `event_count+1`；ISR 后 raw/status=0；clear 后 raw/status/latched 全 0 | `RECORD_GAP` | 当前 event_count 被断言但 Artifact snapshot 未保存该计数 |
| `AES_P1_012` | Actual = Golden；`produced_bytes=16`；`latched=COMPLETE`；`event_count+1`；clear 后 COMPLETE 全视图清零 | `RECORD_GAP` | IRQ证据充分；建议补 Expected 或 `data_match` 供报告展示数据正确性 |
| `AES_P1_013` | `latched=INCOMPLETE_DISABLE`；`event_count+1`；重新 Enable/Configure 后 Actual = Golden、`produced_bytes=16` | `RECORD_GAP` | 恢复 Actual 已保存，但 Expected/比较关系未保留 |
| `AES_P1_014` | 初始 `state=IDLE`；必须证明 `DATA_IN_REQ` 与 `DATA_OUT_REQ` 实际参与会话推进；Offset 最终 16/16；`state=COMPLETE`；`produced_bytes=16`；Actual = Golden | `PROOF_GAP` | 当前能证明会话完成/Offset/Actual，但没有强证据证明两个请求型 IRQ Source 都真实参与 |
| `AES_P1_015` | 每个 Source Force 后 `raw=0/status=0/latched=当前Source`；`event_count+1`；Disable/Clear 后全视图 0 且计数不增加 | `OK` | 当前关键 IRQ 反馈已结构化保存 |
| `AES_P1_016` | Mask 时 `raw=COMPLETE/status=0/latched=0`；Unmask 后 `raw=0/status=0/latched=COMPLETE`；`event_count+1` | `OK` | 当前 Mask/Unmask 关键转移已保存 |
| `AES_P1_017` | clear 前 `raw=当前Source/status=0/latched=0`；clear 后全视图 0；event_count 不变 | `OK` | 当前单 Source Clear 证据完整 |
| `AES_P2_001` | Gate 关闭期间输入/输出 Channel 在**有界观察窗口内持续 Active 且无 ERROR**；Gate 开启后两 Channel Free/无 ERROR；Actual = Golden | `PROOF_GAP` | 当前 Gate 关闭只做启动后的瞬时单次采样，阻塞证明偏弱 |
| `AES_P2_002` | REGISTER Mode 输入/输出 Channel 完成且无 ERROR；Destination 16-byte Actual = Golden | `RECORD_GAP` | `wait_channel_free` 会拒绝 ERROR，但报告只保存 `is_free`，建议同步保留无 ERROR 终态 |
| `AES_P2_003` | FIFO 输入 Channel 完成/无 ERROR；输出 Channel 完成/无 ERROR；Destination 16-byte Actual = Golden | `RECORD_GAP` | 功能判断已有；建议保存无 ERROR 终态供报告展示 |
| `AES_P3_001` | 8轮每轮 Actual；`produced_bytes=16`；`FINISH=true`；每轮 Actual = 独立 Golden；8/8 完整执行 | `RECORD_GAP` | 当前每轮硬件结果已保存，但 Expected/比较关系未直接保留 |
| `AES_P3_002` | 256/1024 两档 `elapsed_cycles>0`；`measured_bytes` 正确；`produced_bytes` 正确；`FINISH=true`；两档 Actual = Golden；1024 周期 > 256 | `RECORD_GAP` | 当前代码实际读取并断言 Actual，但 Artifact 没保留 Actual/Expected/produced_bytes |
| `AES_P3_003` | `timing.complete=true`；`elapsed_cycles>0`；两 DMA Channel Free/无 ERROR；1024-byte Actual = Golden | `RECORD_GAP` | 当前保存 timing/Free/Actual，建议补 Expected/比较结果和无 ERROR 终态 |

## 4. 当前最值得先处理的证明缺口

只有 5 组需要优先考虑是否真的改测试逻辑，其余大多数只是“已经测了，但证据没完整留下”。

1. `AES_P1_006`：DIN_REQ W1C 当前没有形成 clear 前 1 -> clear 后 0。
2. `AES_P1_007`：DOUT_REQ W1C 当前没有形成 clear 前 1 -> clear 后 0。
3. `AES_P1_009`：OUTPUT_CONFLICT 清除后没有确认 latched 也被清除。
4. `AES_P1_014`：没有强证明 DATA_IN_REQ / DATA_OUT_REQ 两类事件都真实参与 IRQ Transfer。
5. `AES_P2_001`：Gate 关闭只瞬时读一次 Active，缺少“关闭期间持续被阻塞”的硬件证据。

这些必须先由人工确认“Feature是否真的要求这么强的证明”。确认后才能改测试代码；不能让 Agent 自己扩展测试语义。

## 5. 代码阶段的最小修改原则

后续若进入 Evidence Closure：

- 已经读取/断言的值，只补 `record_result` / Observation，不新增硬件动作。
- 只有 `PROOF_GAP` 才允许增加最少量硬件读取/状态窗口/清除后复核。
- 不改 Driver/Firmware，除非现有稳定接口根本拿不到所需反馈。
- 不为了报告增加无意义寄存器读回；只采集决定 PASS 的 Hardware Proof Set。
- 报告最终只展示 Proof Set 的摘要；完整参数级事实保留在执行明细和 Canonical Result/Artifact。

## 6. 建议下一步

人工先确认第4节这 5 组 `PROOF_GAP` 的证明强度。确认后，再把本表中的最小证明集正式写回 `test_case_doc/aes/aes.md` 的 `method.observations`，随后逐 Case 对照代码，只补真正缺失的 Evidence。
