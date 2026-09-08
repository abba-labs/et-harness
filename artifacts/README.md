# 测试产物目录使用说明

本文件仅提供导航；唯一权威规则按职责分别见
[R500 Operator Pipeline](../report/design/rules/R500_operator_pipeline.md)第6节和
[R130 Result / Evidence](../report/design/rules/R130_canonical_result_evidence.md)第8.1节。
本文件不建立第二套规则。

## 固定结构

```text
artifacts/
├─ README.md
├─ runs/current/
│  ├─ manifest.json、config/、stages/
│  ├─ tests/<ip>/
│  │  ├─ session.json、cases/、pytest.log
│  │  └─ facts.md、publication.json
│  └─ publication.json
├─ records/<CHIP>/<IP>/
│  ├─ README.md
│  ├─ cases/<CASE_ID>.md
│  └─ attachments/<CASE_ID>/...  # 必要时
└─ reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx  # 最近生成的Excel
```

## 快速定位

| 内容 | 位置 |
|---|---|
| 当前运行身份、配置和阶段日志 | `runs/current/manifest.json`、`config/`、`stages/` |
| 当前原始Case事实与附件 | `runs/current/tests/<ip>/session.json`、`cases/` |
| 当前简短事实摘要 | `runs/current/tests/<ip>/facts.md` |
| 某芯片/IP最近生成的Excel | `reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx`（启用报告时更新） |
| 某芯片/IP知识索引 | `records/<CHIP>/<IP>/README.md` |
| Case方法、问题与可复用结论 | `records/<CHIP>/<IP>/cases/<CASE_ID>.md` |
| 正文引用的必要附件 | `records/<CHIP>/<IP>/attachments/<CASE_ID>/` |

例如：`reports/ET6801/ET6801_CAN测试报告.xlsx`。关闭报告时保留上次文件，运行日志提示本次未更新；报告首页的Run ID、Lane和时间用于确认来源。
旧时间戳目录、旧平铺Excel及旧固定JSON/ZIP仍为只读历史，不是新知识格式的依赖。

## 知识整理入口

以下命令从正式仓库根执行；`extract`默认输出Case/参数状态与错误摘要：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py extract `
  --chip ET6801 --ip can --lane fpga --source artifacts/runs/current/tests/can
# 先列出Case可用键，再追加 --key measurement.<键> 或 --key observation.<键> 查询原始值：
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py extract `
  --chip ET6801 --ip can --lane fpga --source artifacts/runs/current/tests/can --case CAN_P0_001
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py check --chip ET6801 --ip can
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py index --chip ET6801 --ip can
```

Agent读原始方法与已有知识、处理本次新知识后，显式确认全部已选Case：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py review `
  --chip ET6801 --ip can --lane fpga --source artifacts/runs/current/tests/can
```

首次需要先写Case Markdown；重复PASS且无新知识时可以正文零修改后确认。
`check/index`不放行覆盖，脚本不会自动编写分析或关闭问题。

中断现场的人工显式归档（目标为尚不存在的新文件）：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py archive `
  --workspace artifacts/runs/current --output <现场归档.zip>
```

旧Session可用`extract --source <历史Session目录>`只读查询；
已取消旧`update/prune/--refresh-views/--protect-case`流程。
通用清理工具排除固定工作区、知识树、维护事务与报告芯片目录。历史删除仍是独立任务。
