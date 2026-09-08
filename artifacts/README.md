# 测试产物目录使用说明

本文件只说明`artifacts/`的目录用途和查找方式。唯一权威规则是
[`R500 Operator Pipeline / Run Config / Artifact 契约`](../report/design/rules/R500_operator_pipeline.md)；
路径、命名、写入边界、Git和清理要求均以R500为准，本文件不建立第二套规则。

## 固定结构

```text
artifacts/
├─ README.md
├─ runs/
│  └─ current/
│     ├─ manifest.json
│     ├─ config/
│     │  └─ run_config.snapshot.yaml
│     ├─ stages/
│     │  └─ <build-or-deploy-step>/
│     └─ tests/
│        └─ <ip>/
│           ├─ session.json
│           ├─ cases/
│           └─ publication.json
├─ records/<CHIP>/<IP>/
│  ├─ README.md
│  ├─ results.json
│  ├─ test_report.xlsx
│  ├─ cases/<CASE_ID>.md
│  └─ evidence/<CASE_ID>.json、<CASE_ID>.zip
└─ reports/  # 历史或显式一次性导出
```

`runs/current`是正式入口的固定工作区；每轮发布档案后由回执保护复用。
`records/<CHIP>/<IP>`是长期查阅入口，参数与测试时间写在文件内容中。
原始附件在每Case的ZIP内按SHA256定位，对应文件名映射位于同名JSON。

## 快速定位

| 需要查找的内容 | 位置 |
|---|---|
| 最近工作区身份与状态 | `runs/current/manifest.json` |
| 最近工作区配置与阶段日志 | `runs/current/config/`、`runs/current/stages/` |
| 某芯片/IP当前索引 | `records/<CHIP>/<IP>/README.md` |
| Case方法、结果与人工分析 | `records/<CHIP>/<IP>/cases/<CASE_ID>.md` |
| 当前及受保护原始证据 | `records/<CHIP>/<IP>/evidence/<CASE_ID>.json`、同名ZIP |
| 人读Excel测试报告 | `records/<CHIP>/<IP>/test_report.xlsx`（启用报告时） |

旧时间戳/年月日目录和Excel保留为历史；独立诊断输出不代替Formal Case。

## 档案维护入口

以下命令从正式仓库根执行；操作语义和限额见R500第6节。

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py check --chip ET6801 --ip can
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py update `
  --chip ET6801 --ip can --lane fpga --source <Session目录> --manifest <原Manifest文件>
```

报告显示算法升级后的显式重建：在`check`命令后追加`--refresh-views`。
该操作只重建派生视图，先验证原始证据；普通`check`不修改文件。

阶段归档与保护释放（归档目标须人工指定新文件名；释放默认预览）：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py archive `
  --chip ET6801 --ip can --output <阶段归档.zip>
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py prune `
  --chip ET6801 --ip can --archive <阶段归档.zip> --case <CASE_ID>
```

中断工作区归档后，下一次正式运行才可验证并复用它：

```powershell
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py archive `
  --workspace artifacts/runs/current --output <现场归档.zip>
```

通用清理工具`clean_generated_outputs.py`默认只预览历史Run；它排除固定工作区、
档案与维护事务。历史删除另行审阅并显式执行；本次迁移不清理旧证据。
