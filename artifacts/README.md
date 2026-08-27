# 测试产物目录使用说明

本文件只说明`artifacts/`的目录用途和查找方式。唯一权威规则是
[`R500 Operator Pipeline / Run Config / Artifact 契约`](../report/design/rules/R500_operator_pipeline.md)；
路径、命名、写入边界、Git和清理要求均以R500为准，本文件不建立第二套规则。

## 固定结构

```text
artifacts/
├─ README.md
├─ runs/
│  └─ <YYYYMMDD_HHMMSS_microseconds>_<run-name>/
│     ├─ manifest.json
│     ├─ config/
│     │  └─ run_config.snapshot.yaml
│     ├─ stages/
│     │  └─ <build-or-deploy-step>/
│     └─ tests/
│        └─ <ip>/
│           ├─ session.json
│           └─ cases/
└─ reports/
   └─ <YYYYMMDD_HHMMSS_microseconds>_<CHIP>_<IP>测试报告.xlsx
```

`runs/`按一次运行归档原始证据。`run_id`已包含完整时间，因此新运行可以直接按
`runs/<run_id>/`查找，不需要先进入年月日目录。

默认单轮结果位于`tests/<ip>/`；配置多轮执行后，各轮结果位于`round_<NN>/`。

`reports/`集中保存从Canonical Result生成的人读Excel报告，文件名以完整时间戳开头，
可直接按文件名排序。

## 快速定位

| 需要查找的内容 | 位置 |
|---|---|
| 本次运行身份与最终状态 | `runs/<run_id>/manifest.json` |
| 本次实际配置 | `runs/<run_id>/config/` |
| 编译、部署和启动阶段证据 | `runs/<run_id>/stages/` |
| 某个IP的原始测试结果 | `runs/<run_id>/tests/<ip>/` |
| 人读Excel测试报告 | `reports/<timestamp>_<CHIP>_<IP>测试报告.xlsx` |

旧年月日目录是规则收口前的历史证据；新产物只按上面的稳定路径查找。

## 上传前清理

清理工具默认只预览`runs/`内容，不会立即删除：

```powershell
.\.venv\Scripts\python.exe tools\runner\clean_generated_outputs.py
```

预览默认只显示总数和空间；需要逐项核对时追加`--verbose`。

确认预览后，清空`runs/`内容但保留目录结构和本README：

```powershell
.\.venv\Scripts\python.exe tools\runner\clean_generated_outputs.py --execute
```

报告、Python缓存（包括`__pycache__`、`.pytest_cache`、`.ruff_cache`和`*.egg-info`）
以及`tmp/`必须显式选择；多个范围可组合：

```powershell
.\.venv\Scripts\python.exe tools\runner\clean_generated_outputs.py `
  --scope runs --scope reports --scope caches --scope tmp --execute
```

`.venv/`、第三方依赖和Firmware构建目录不属于本工具的删除范围。它们由`.gitignore`
阻止上传，避免每次清理后重复安装环境或重新生成工程。
