# runner 芯片比对缺陷跳过报告发布（records/current 链）

状态：superseded（已在 `run_ip_tests.py::_execute_ip` 用 `safe_name(_session_chip(...)).upper()` 与 `target_chip()` 对齐；真芯片不一致仍跳过发布）
适用范围：ET_ATP_Testing 仓库 `tools/runner/run_ip_tests.py` 的 records/current 布局；FPGA/Silicon 任何 IP。
最后核验：2026-09-10（软件单测覆盖 `et6801` vs `ET6801` 发布，以及 `et9999` vs `ET6801` 跳过）

## 现象/背景

`run_ip_tests.py` 在 pytest 结束后比对 Session 芯片与 Bench 证据目录身份，不等则打印
"Actual Session chip differs from the Bench evidence destination; raw files retained." 并跳过
`prepare_review`——即不生成 facts.md、不生成 Excel、不写 publication 回执。历史缺陷是裸 `!=` 大小写敏感；现已归一。

## 根因/机制

- session.json 的 chip 字段来自固件 HELLO 上报，为小写 `'et6801'`（`run_context.py` 直接采用 HELLO 值）。
- `target_chip()` 返回 `safe_name(chip).upper()` = `'ET6801'`（bench profile 的 chip 字段大写化）。
- `_session_chip()` 返回 `payload.get("chip_id") or payload.get("chip")`；修复前未做大小写归一 → 与大写
  比较恒为不等 → 分支必触发。修复后比较为 `safe_name(...).upper() != chip`。
- **连锁**：child（CAN/current）无回执 → 收尾 `seal_pipeline` 对 child `verify_publication` 失败 →
  parent（_PIPELINE/current）也不发布 → 下一轮运行 `prepare_workspace` 被复用闸门拦截
  （"current workspace is unpublished"）。三层连锁，一层比一层隐蔽。

## 解法/操作（零代码，按 runner 原设计机制手动补跑）

```powershell
# 1. 补发布 child 回执（write_report=False 绕开可能卡死的 Excel 发布；需要报告时改 True）
.\.venv\Scripts\python.exe -c "import sys, json; sys.path.insert(0,'tools/runner'); sys.path.insert(0,'tools'); from pathlib import Path; from maintain_test_records import prepare_review; r = prepare_review(Path('.'), Path('artifacts/records/ET6801/CAN/current'), chip='ET6801', ip='can', lane='fpga', manifest=Path('artifacts/records/ET6801/CAN/current/manifest.json'), write_report=False); print(r['knowledge_review'])"

# 2. 补完 parent 封存（root 必须绝对路径，见下"边界"）
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'tools/runner'); from pathlib import Path; from record_workspace import seal_pipeline; seal_pipeline(Path.cwd(), (Path.cwd()/'artifacts/records/ET6801/_PIPELINE/current').resolve(), successful=False)"

# 3. 知识整理后显式 review 放行（--source 必须绝对路径，否则触发另一个缺陷）
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py review --chip ET6801 --ip can --lane fpga --source <绝对路径>\artifacts\records\ET6801\CAN\current --manifest <绝对路径>\...\manifest.json
```

## 边界与不适用

- 本文档只覆盖 `_session_chip` 比对缺陷；`review` CLI 相对路径崩溃见
  [review_cli_relative_source_crash](review_cli_relative_source_crash.md)。
- 手动补跑前确认 pytest 确已结束且 session.json 已定稿（`finished_at` 非空）。

## 依据与变化

- 2026-09-09 14:30 CST：CAN 复测轮首次确认（连续三轮：独立测试轮/复测轮/全链路轮均触发）；判定根因为大小写不归一，修复建议：`_session_chip` 返回值与比较双方统一 `.lower()` 或 `.upper()`（约1行）。Excel 连续三轮未生成，report 留 09-08 版并在 records/ET6801/CAN/README.md 声明。缺陷上报至用户，按"零代码修改"约束未修。
- 2026-09-09 15:35 CST：全链路轮（新编译固件）再次复现，确认与固件版本无关；补发布流程验证可行，双闸门（child+parent）成功放行。
- 2026-09-10：比较侧改为 `safe_name(_session_chip(run_dir)).upper() != chip`；固件 HELLO 与 bench.yaml 大小写均不改。仅大小写不同会继续 `prepare_review`；`et9999` 等真不一致仍打印原提示并保留 raw。历史未发布 current 仍可用上文零代码补发布。
