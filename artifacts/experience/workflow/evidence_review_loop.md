# 证据回路与现场生命周期（facts/回执/review/复用/解阻）

状态：active
适用范围：`artifacts/records/<CHIP>/<IP>/`（current 工作区 + cases 知识树）+ `_PIPELINE/current`。
最后核验：2026-09-12（规则与源码静态核对；未运行测试）

## 生命周期

```text
pytest 结束（session.json 定稿）
→ prepare_review：写 facts.md + specification.md + publication.json 回执(pending_review=True)
   [+ Excel 到 reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx，原子替换]
→ Agent 逐 Case 提炼/确认（对照 cases/*.md 知识，增量追加带时间条目）
→ check（结构/链接/容量）→ review（显式放行，回执转已核）
→ 下一轮 prepare_workspace 校验回执后清空复用 current
```

pytest FAIL也保留真实事实。按[R500](../../../report/design/rules/R500_operator_pipeline.md)第6节，
Hash完好的已seal pending现场允许人工复用；Agent仍须整理。未发布、损坏或未完成现场不得清空。

## 回执状态与复用闸门

| current/publication.json | 复用检查（require_review=False） | 下一轮 |
|---|---|---|
| 不存在（unpublished） | ValueError "unpublished" | **被拦** |
| 存在，pending_review=True | 校验原始成员及Hash | 人可复用；Agent先整理 |
| 存在，pending_review=False（已 review） | 通过 | 复用（清空重建） |
| 存在，archive proof | 通过（校验 recovery.zip） | 复用 |

注意 `_PIPELINE/current` 同样有回执状态；runner 收尾 `seal_pipeline` 会校验所有 child 回执后封存
parent——child 未发布时 parent 也留未发布，下一轮流水线启动即被拦。

## 未发布现场的处理

1. **补发布**（runner 因缺陷跳过时）：手动调 `prepare_review`（write_report=False 绕开 Excel）
   → 得 pending 回执 → 整理 → review。若 parent 也未封存，再手动 `seal_pipeline`（**root 必须绝对路径**）。
2. **archive**：`maintain_test_records.py archive --workspace <current> --output <同级recovery.zip>`
   ——打包完整现场并发布 receipt。**单发限制**：recovery.zip 已存在则停止，要求人工处理。
3. archive不可用时原地保留并报告原因。禁止搬到旧runs或新建日期/轮次目录后清空current；
   “继续工作”不等于允许丢弃未整理现场。

## review 的父子联动（易踩）

`review` 会重封 CAN current 回执；若 `_PIPELINE/current` 回执存在且 child.manifest.pipeline_run_id
匹配，会**联动重封 parent**。相对路径曾在该分支失败；现入口已统一绝对路径，修订尚未运行回归，见
[review_cli_relative_source_crash](../platform/review_cli_relative_source_crash.md)。

## 知识整理的最小闭环

1. `extract --chip --ip --lane --source <current>`（只读）获取按 Case/参数的事实。
2. 逐 Case 对照知识文件：新现象→追加带时间条目；同现象复现→README 登记复测、正文不动（防流水账）。
3. FAIL 判读以 result.json 的 error 尾部为权威，**不信任控制台流**（会丢段/交错）。
4. `check` → `review`（绝对 --source）。

## 依据与变化

- 2026-09-12 17:20 CST：按R500和当前源码纠正pending复用、删除搬回runs的解阻建议；来源UNVERIFIED不得review。仅静态核对。
- 2026-09-09：三轮实测覆盖全部状态迁移；一次"未执行写成已执行"险情在 check 计数对账中拦截
  （见 [case_list_authority](../governance/case_list_authority.md)）；本轮沉淀的两种未发布解阻
  路径均已验证。
- 2026-09-10 11:00 CST：修正「review 相对路径崩溃」交叉引用，指向
  [review_cli_relative_source_crash](../platform/review_cli_relative_source_crash.md)，不再误指向已
  superseded 的芯片比对文档。测完仍须本回路 `review` 才允许下一轮覆盖 current（与
  [test_execution_runbook](test_execution_runbook.md) §6 一致）。
