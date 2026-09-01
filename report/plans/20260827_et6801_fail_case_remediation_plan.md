# ET6801 FAIL Case 分类整改与复测计划

时间：2026-08-27 16:37 CST

文档记录遵循工作区根目录 `DOCUMENTATION_RULES.md`。

## 1. 目标与边界

本计划用于处理当前已经复盘的 ET6801 非 PASS Case。执行原则如下：

1. 已确认属于硬件问题或当前 FPGA 环境不支持的项目，不修改 Case，不弱化断言，只更新对应 `ET6801_<ip>.md` 的芯片事实、当前状态和复测条件。
2. 已确认属于 Case 构造、Oracle、软件路径或执行映射问题的项目，按已梳理的方法做最小修正，并重新执行定向 HIL。
3. `WDG_P1_004` 尚未完成根因裁决，独立处理，不与其他已明确项目混在一起。
4. 每个 IP 独立整改、独立验证、独立回写文档；禁止顺带修改其他 IP 或冻结公共层。
5. 手动诊断只用于定位根因，不能直接替代 Formal Case 的最终 PASS/FAIL 结果。

本计划不改变 ET-Frame、公共架构、Case ID、Feature ID或已经确认的硬件事实。

## 2. 问题分类与处理策略

### 2.1 只更新芯片文档，不修改 Case

| Case ID | 当前结论 | 处理内容 | 后续复测条件 |
|---|---|---|---|
| `CRC_P1_012` | 当前 ET6801 FPGA 的 CRC FIFO Overflow 功能存在问题 | 保留严格 FAIL；在 `ET6801_crc.md` 记录硬件现象、人工确认结论和时间戳；不删除 Overflow 断言，不改为 SKIP | RTL/bitfile 修复后重新执行 Formal Case；Silicon 需要独立验证 |
| `WDG_P2_001` | 当前 FPGA 中 WDG Divider 配置可读回，但 Counter 速率不体现分频效果 | 在 `ET6801_wdg.md` 记录 FPGA 时钟路径限制；Case保持原设计，不通过放宽比例门限获得 PASS | FPGA 时钟路径修复，或在 Silicon 上执行同一 Case |

### 2.2 修正 Case、Oracle或软件路径后重新测试

| Case ID | 已确认问题 | 最小整改方法 | 定向通过条件 |
|---|---|---|---|
| `STIMER_P2_003` | Halt窗口过短，且未考虑CPU Halt到STIMER Pause生效的同步延迟 | 延长真实J-Link Halt窗口；使用PAUSE与RUN_FREE两轮Counter增量的显著差异作为Oracle，不要求PAUSE增量绝对为0 | PAUSE轮增量显著小于相同时间尺度的RUN_FREE轮增量，恢复运行正常 |
| `CRC_P1_011` | 把`FIFO_TRHD`错误理解为CRC Result更新门限 | 将Case改为验证DMA Request/FIFO水位边界；不再用第4/5次CPU写入后的Result变化判断Threshold | Threshold边界前后DMA Request或等价硬件状态符合ET6801权威语义，CRC结果仍正确 |
| `AES_P1_009` | CPU双Block路径受`data_valid`反压，不能合法形成`OUTPUT_CONFLICT` | 改用DMA输出冲突场景：上一笔输出DMA尚未完成时产生下一笔AES结果；保留自然IRQ因果证明 | `OUTPUT_CONFLICT` Raw/Status/事件记录置位，可清除，清除后AES恢复工作 |
| `CORDIC_P1_003` | Scale=7使用了没有规格依据的统一`1e-4`误差门限 | 先把人工认可的ET6801误差预算写入公共Case契约，再调整Oracle；公式、Raw重复性和状态断言保持不变 | Scale 0～7均满足已批准的误差预算，Raw和公式结果可重复 |
| `CORDIC_P2_001` | CORDIC DMA Request、Endpoint和Direction映射没有接入平台 | 只补ET6801 Capability/Execution Mapping和必要的映射回归；不重写Case测试逻辑 | Case不再因Mapping缺失停止，DMA模式结果与CPU模式结果一致 |
| `FMAC_P1_006` | Overflow实时条件尚未撤销时立即清除状态 | 按“越界输入 → 正常输入撤销Overflow条件 → W1C清除”执行；保留正负Q15钳位断言 | 正负钳位正确，Overflow可置位，正常输入后W1C可清除，后续计算正常 |
| `FMAC_P1_010` | Formal软件路径使用了错误的状态清除语义 | 在ET6801 Chip Driver Test Extension中提供明确的W1C接口，Wrap只调用Driver；保留Offset数值和Negative状态断言 | Offset输出正确，Negative状态可置位并通过W1C清除，恢复路径正常 |

### 2.3 `WDG_P1_004`独立裁决

当前只证明手动诊断中模块复位后WDG仍保持Enable且Counter继续递减，尚未证明这是WDG硬件故障。

按以下顺序处理：

1. 核对并修正`WDG_testResetModule()`的CRG写保护流程，确保SRST写入前执行解锁、复位后重新上锁。
2. 使用手动固件重复执行“启动WDG → 模块复位 → 读取Enable/Counter → 重新配置恢复”。
3. 若手动测试通过，补齐Formal Runtime的`MODULE_RESET`映射，再运行`WDG_P1_004`。
4. 若解锁后的手动测试仍失败，向设计确认“已Enable的WDG是否允许模块软复位清除”的权威语义。
5. 在Formal Case真正执行前，状态保持`NOT_EXECUTED / MANUAL_DIAGNOSTIC_FAIL / ROOT_CAUSE_PENDING`，不得直接写成硬件FAIL。

## 3. 执行顺序

### 阶段一：文档事实收口

1. 更新`ET6801_crc.md`中的`CRC_P1_012`硬件问题结论。
2. 更新`ET6801_wdg.md`中的`WDG_P2_001` FPGA限制。
3. 统一`WDG_P1_004`状态，删除同一文档中“SKIP、FAIL、待裁决”并存造成的当前结论冲突；保留历史记录，不回改历史证据。

### 阶段二：按IP逐项整改

建议顺序：

```text
FMAC_P1_006 / FMAC_P1_010
  -> STIMER_P2_003
  -> CORDIC_P1_003 / CORDIC_P2_001
  -> CRC_P1_011
  -> AES_P1_009
  -> WDG_P1_004独立裁决
```

每完成一个IP，立即执行该IP的软件专项门禁，不累计到最后一起排错。

### 阶段三：固件构建与定向HIL

1. 先完成Firmware工程构建和PC专项门禁。
2. 按正式部署流程烧录并从Flash运行，禁止使用临时RAM运行结果替代正式HIL。
3. 只运行本轮发生语义或实现变化的Case，并保留原始Canonical Result。
4. 定向Case通过后，再执行对应IP的完整回归，确认修复没有影响同IP其他Feature。
5. 所有IP定向回归完成后，再执行一次当前可运行IP集合回归；不同IP状态相互独立，不因单项FAIL中断其余IP取证。

## 4. 文档同步要求

每次真实测试完成后，必须在对应`test_case_doc/<ip>/ET6801_<ip>.md`中追加带时间戳的当前状态：

1. Case ID和测试Feature。
2. 测试环境、源码SHA和FPGA/板卡通道。
3. 实际配置、关键寄存器字段或硬件状态。
4. PASS、FAIL、SKIP或NOT_EXECUTED的准确分类。
5. 测试现象、根因结论和下一次复测条件。
6. `artifacts/runs/`中的Canonical Result或手动诊断证据路径。

硬件问题和FPGA限制只进入芯片适配文档，不反向污染公共`<ip>.md`的跨芯片Case语义。

## 5. 验证与完成标准

单个整改项只有同时满足以下条件才可关闭：

1. 修改范围仅覆盖目标IP和明确需要的ET6801芯片适配文件。
2. Case、Driver、Service、Wrap、Chip Driver仍符合既有分层规则。
3. 目标IP专项软件门禁通过，Firmware构建通过。
4. 需要复测的项目已经完成真实Formal HIL，并生成Canonical Result和Excel报告。
5. 对应`ET6801_<ip>.md`已按实际结果和时间戳更新。
6. 硬件问题没有通过弱化断言、扩大SKIP或删除Feature伪装成PASS。

本计划完成时，应形成三类清晰结论：

```text
已修复并Formal PASS
已确认硬件/FPGA限制，Case保持不变
仍待设计裁决或新硬件环境验证
```

## 6. 当前不执行项

本计划编写阶段不修改任何代码、不更新Case状态、不执行编译、烧录或硬件测试。实际整改必须按IP分别建立任务边界并取得真实硬件操作许可。
