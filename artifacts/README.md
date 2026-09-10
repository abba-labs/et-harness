# 测试产物目录使用说明

本文件仅提供导航；唯一权威规则按职责分别见
[R500 Operator Pipeline](../report/design/rules/R500_operator_pipeline.md)第6节和
[R130 Result / Evidence](../report/design/rules/R130_canonical_result_evidence.md)第8.1节。
本文件不建立第二套规则。

## 固定结构

```text
artifacts/
├─ README.md
├─ records/<CHIP>/<IP>/
│  ├─ README.md
│  ├─ cases/<CASE_ID>.md
│  ├─ attachments/<CASE_ID>/...  # 必要时
│  ├─ current/  # 本IP当前一次测试：Manifest、Session、原始附件、事实和回执
│  └─ _maintenance/  # 固定锁与事务工作区
├─ records/<CHIP>/_PIPELINE/current/  # 公共阶段、配置和整轮回执
├─ records/_DIAGNOSTICS/<TOOL>/current/  # 独立诊断
├─ records/_TOOLING/<TASK>/current/  # 软件验证，主题名不带日期或轮次
└─ reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx  # 最近生成的Excel
```

## 快速定位

| 内容 | 位置 |
|---|---|
| 当前公共阶段身份、配置和日志 | `records/<CHIP>/_PIPELINE/current/` |
| 当前原始Case事实与附件 | `records/<CHIP>/<IP>/current/session.json`、`cases/<CASE_ID>/<SLOT>/` |
| 当前简短事实摘要 | `records/<CHIP>/<IP>/current/facts.md` |
| 某芯片/IP最近生成的Excel | `reports/<CHIP>/<CHIP>_<IP>测试报告.xlsx`（启用报告时更新） |
| 某芯片/IP知识索引 | `records/<CHIP>/<IP>/README.md` |
| Case方法、问题与可复用结论 | `records/<CHIP>/<IP>/cases/<CASE_ID>.md` |
| 正文引用的必要附件 | `records/<CHIP>/<IP>/attachments/<CASE_ID>/` |

例如：`reports/ET6801/ET6801_CAN测试报告.xlsx`。关闭报告时保留上次文件，运行日志提示本次未更新；报告首页的Run ID、Lane和时间用于确认来源。
旧`runs`、旧平铺Excel及旧固定JSON/ZIP仍为只读历史，不再新增或写入。`current`仅保留本次测试。人可不review即覆盖Hash完好的pending现场。Agent必须review。不按日期或轮次累积。

## 知识整理入口

以下命令从正式仓库根执行；`extract`默认输出Case/参数状态与错误摘要：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py extract `
  --chip ET6801 --ip can --lane fpga --source artifacts/records/ET6801/CAN/current
# 先列出Case可用键，再追加 --key measurement.<键> 或 --key observation.<键> 查询原始值：
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py extract `
  --chip ET6801 --ip can --lane fpga --source artifacts/records/ET6801/CAN/current --case CAN_P0_001
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py check --chip ET6801 --ip can
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py index --chip ET6801 --ip can
```

Agent读原始方法与已有知识、处理本次新知识后，必须显式确认全部已选Case；人连跑不依赖该命令：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py review `
  --chip ET6801 --ip can --lane fpga --source artifacts/records/ET6801/CAN/current
```

首次需要先写Case Markdown；重复PASS且无新知识时可以正文零修改后确认。
`check/index`不绑知识回执。脚本不会自动编写分析或关闭问题。覆盖Hash完好的pending `current/`不依赖`review`。

中断现场的人工显式恢复包（固定目标必须尚不存在，不作日常累积归档）：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py archive `
  --workspace artifacts/records/ET6801/CAN/current --output artifacts/records/ET6801/CAN/recovery.zip
```

旧Session可用`extract --source <历史Session目录>`只读查询；
已取消旧`update/prune/--refresh-views/--protect-case`流程。
通用清理工具排除固定工作区、知识树、维护事务与报告芯片目录。历史删除仍是独立任务。
