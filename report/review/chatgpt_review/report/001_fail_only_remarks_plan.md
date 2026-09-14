# 报告备注仅显示 FAIL：独立修改方案

状态：PROPOSED，尚未修改报告实现。
源码基线：`968cc410323ecade4068de5f73b46ac6b0de9157`。
本改动属于公共报告展示层，与 CAN 固件及 ECC Case 可读性修改分别实施、分别验证。

## 1. 用户要求的准确含义

最终报告的备注只记录失败信息，PASS 行留空。对于同一稳定 Case 下混合 PASS/FAIL 的参数节点，备注也只取失败节点，不带上其他已通过节点的数据。

非 FAIL 状态的普通备注同样不展开；SKIP、NOT_EXECUTED、NOT_SELECTED、EVIDENCE_MISSING、RUN_ERROR 仍保留自己的状态、原始原因和执行级错误信息。不能为了有备注将运行异常改写为芯片 FAIL。

这只是报告投影变化，不等于 PASS 不记录数据。canonical result、observations、measurements、日志和附件保持原有保留与完整性校验。Case 和 Driver 不负责判断是否向备注写文字。

## 2. 已核对的实际入口

文件：`pc/et_test_platform/results/case_report.py`。

- `_case_row()` 先计算最终报告状态，再用 `_report_remark(spec, results, status)` 构建 `remark`。
- `_report_remark()` 当前对 PASS 和 FAIL 都调用 `_evidence_remark()`。
- `_evidence_remark()` 优先用 `_human_report_note()`，否则展开 Observation。
- `_human_report_note()` 当前把 PASS/FAIL 一起作为 completed 记录汇总。
- `_execution_row()` 已保留 measurements、observations、error、result_path 等执行级信息。

因此只把 PASS 行隐藏还不够：FAIL 行的子节点筛选也必须正确，否则会把通过参数的观测一并写进失败备注。

## 3. 修改位置与步骤

### 第一步：在唯一备注入口区分显示与数据保留

保持最终状态计算和证据完整性检查不变。只在 `_report_remark` 决定是否产生普通备注：

```python
def _report_remark(spec, results, status):
    if status != "FAIL":
        return ""

    failed_results = [
        item for item in results
        if str(item.get("status") or "").upper() == "FAIL"
    ]
    return _failure_remark(spec, failed_results)
```

`_failure_remark` 是拟议的本模块私有格式化函数，不是已经存在的 API。该函数不修改结果状态，不做设备 I/O，也不向 Case/Driver 加任何回调。

### 第二步：失败备注只写真正有用的失败项

按失败参数节点分段，记录：参数标识、已有明确的失败原因、可直接取得的失败阶段/实例、已有结构化的期望与实际值、相关证据引用。信息不存在时不编造。

不要将失败节点中所有成功阶段的读回、整个嵌套 JSON、ECC 的全部采样窗口逐项塞入备注。原始完整轨迹继续留在 result/附件中。对未定位到具体阶段的旧 Case，优先保留既有错误文本与证据位置，不依赖脆弱的 repr 正则猜测硬件事实。

示意（并非真实测试结果）：

```text
参数：UNCORRECTED
阶段：repeat，目标：can1
失败项：中断次数，期望 2，实际 1
证据：对应参数节点的 result.json
```

使用 `_human_report_note` 或 `_observation_lines` 的既有能力时，只将失败子集传入；通用备注模板若会展开成功步骤，则只复用必要的值格式化能力，不把整个成功/失败摘要原样复制回来。

### 第三步：避免“备注构建失败”掩盖原失败

早期失败可能没有某些报告模板字段。当前 `_human_report_note` 遇到缺字段或无法聚合会抛 ValueError。新增失败备注投影应在已经完成结果/契约检查之后，对缺少可选展示字段使用明确的简短错误摘要与证据引用，不重新标记通过，也不吞掉 canonical/schema/身份/文件损坏这类完整性错误。

范围只限可选备注格式化中的缺值回退；所有原有证据完整性检查和状态计算仍照常执行。不能通过 skip 校验、改状态或捕获所有异常让报告看起来成功。

### 第四步：核对所有报告输出使用同一备注字段

从 `_case_row` 返回的 `remark` 向下检查当前 Excel/其他报告渲染入口，确认没有针对 PASS 的二次自动补写。空备注保持空，不替换成“通过”“无异常”“详见证据”。现有状态列、统计、执行数及错误资料保持原样。

只修改命中的公共展示责任层，不给每个 IP 写一份 PASS/FAIL 格式化逻辑，不让 CAN Case 单独处理最终报告备注。

## 4. 回归矩阵

| 输入情况 | 备注期望 | 保持不变的内容 |
|---|---|---|
| 全部参数 PASS | 空字符串/空单元格 | PASS 状态、数量及完整证据 |
| 单个 FAIL | 该失败的摘要及相关证据 | 原 FAIL 状态与原始错误 |
| PASS + FAIL | 只显示失败参数 | 两个参数的原始记录与执行计数 |
| 多个 FAIL | 按失败参数逐段显示，不拼入通过节点 | 每条失败可单独追溯 |
| 同一 FAIL 内含成功阶段 | 备注聚焦失败项，不展开成功阶段全文 | 全阶段原始观测保留 |
| SKIP/NOT_EXECUTED/NOT_SELECTED | 普通备注空 | 各自状态与原始原因 |
| RUN_ERROR/EVIDENCE_MISSING | 普通备注空 | 运行错误/证据不足状态及诊断，不冒充 DUT FAIL |
| 早期失败缺可选备注字段 | 简短失败摘要/已有证据引用，不编造值 | 完整性判定不被跳过 |
| 报告重生成 | 备注规则一致，无新增设备操作 | 输入结果文件不被修改 |

关键断言：原始结果文件在生成前后内容不变；PASS 的 Observation 契约仍被验证；混合节点下失败备注里不出现仅来自 PASS 参数的数据；最终状态和统计计算与原实现一致。

## 5. 本地实施清单

先读取当前 HEAD 和实际报告调用链，按仓库规则建立只覆盖报告责任层的 Task Context。参考现有 `pc/et_test_platform/framework_validation/unit/results/test_case_report.py` 的测试结构补充上述场景；其他渲染测试路径以当前仓库实际定位为准。

记录实际修改文件、运行的专项命令及结果、生成报告的样例、原始结果保留验证、未执行项和提交 SHA。报告实现属于公共影响，提交不要混入 CAN Service、Wire 或其他 IP 重构。

本轮只是方案：未执行仓库报告测试，未生成真实硬件报告，未改变任何现有运行结果。
