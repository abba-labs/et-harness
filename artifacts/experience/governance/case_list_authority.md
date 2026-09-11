# 注册表是 Case 清单的唯一权威（一次伪造表述险情的完整教训）

状态：active
适用范围：一切"哪些 Case 存在/执行过/覆盖了什么"的判断——知识提炼、覆盖报告、经验总结。
最后核验：2026-09-09

## 险情实录

多 IP 知识迁移中，我为未注册的 `SYSCNT_P2_003` 写了知识文件，含"最近一轮执行通过"表述。
而它实际是 ET_CASE_PLAN：未注册、未实现、**从未执行**（三方证据：case_registry.py 只有 7 个 ID；
session.selection.selected_case_ids 只有 7 个；芯片文档状态块明写"G07 已形成 P2_003 PLAN，没有
对应实现和外部仪器结果"）。

## 根因/机制

- **契约文档 ≠ 注册表**。`<ip>.md` 的 Case Catalog/SPEC 块同时包含已注册（ET_CASE_SPEC）与
  未注册（ET_CASE_PLAN）的定义——"文档里有"不等于"注册了"，更不等于"执行过"。
- 批量 check 的 `case_count` 只数知识文件数量，不校验注册表归属——count 对不上 registry 数量
  是唯一的机器可见信号，最初被我忽略。
- 生产节奏（一次写 197 个文件）稀释了单 Case 的事实核对注意力。

## 解法/操作（双源核对规则）

**任何"Case 清单/覆盖/执行与否"的结论，必须同时满足：**

1. `pc/et_test_platform/test_cases/<ip>/case_registry.py` 的 ID 元组 = 允许写入知识树的清单；
2. `records/.../<ip>/current（或历史session）/session.json` 的 `selection.selected_case_ids`
   = 本次实际执行的清单（PLAN 项天然不在其中）；
3. 契约文档只提供方法语义（SPEC 才是已实现；PLAN 是规划，不建执行记录、不补造）。

三类 Case 状态的书写边界：
- 已注册且执行 → 知识文件（PASS/FAIL/SKIP 均可，如实写）；
- 已注册未执行 → 不写知识文件（下次运行的 NOT_SELECTED/NOT_EXECUTED 由报告层派生）；
- 未注册（PLAN/BENCH_GAP）→ 一律不建记录；README 覆盖声明中点名即可。

## 边界与不适用

- 本规则不阻止"PLAN 项后续实现并注册"——注册后即为正常 Case，按正常流程提炼。
- 知识文件 H1/索引必须与注册 ID 大小写规范一致（`<IP>_P<n>_<nnn>`）。

## 依据与变化

- 2026-09-09 12:25 CST：SYSCNT P2_003 险情发现与修正（文件删除+索引移除+README 修正条目），
  修正依据三方核对；未造成入库污染。
- 2026-09-09 13:00 CST：规则固化进全部 Tier B 子代理 prompt，后续 149 个 Case 零复发。
