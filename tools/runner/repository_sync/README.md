# Repository Sync

本目录提供正式代码根到公司Git工作树的一键同步入口：

```text
sync_to_company_repo.bat
  -> sync_to_company_repo.ps1
  -> 当前工作树正式文件单向覆盖复制
  -> SHA256逐文件复核
```

默认目标：

```text
D:\lihuan\vibe_code\code\SDK\git\Et_Automated_Testing_Platform_Code\et_automated_testing_platform
```

## 同步内容

双击入口复制当前源工作树中的全部Git已跟踪文件，以及未被`.gitignore`排除的新文件，包括源码、规则、IP文档、测试、配置模板、Keil工程和CI配置。目标存在同名文件时直接覆盖；目标独有文件保持不变。

以下内容不进入公司工作树：

- 源仓库`.git/`；目标仓库自己的`.git/`始终保留；
- 被`.gitignore`忽略的文件；
- 本机`run_config.yaml`和`project-governance/runtime/`；
- `artifacts/runs/`、`artifacts/reports/`中的实际测试输出，占位`.gitkeep`除外；
- Python缓存、虚拟环境、IDE状态、Vivado临时文件和Firmware编译输出，因为它们已由`.gitignore`排除。

`report/`、`test_case_doc/`、`project-governance/`、`.github/`和已跟踪的Firmware工程文件属于正式仓库内容，必须同步。

## 使用方式

双击：

```text
sync_to_company_repo.bat
```

脚本打印复制和排除数量后直接执行。它不检查源端或目标端Git状态，不删除目标独有文件，也不执行`git add`、Commit或Push。

临时同步到其他公司工作树时，可传入第一个参数：

```bat
sync_to_company_repo.bat D:\path\to\another\worktree
```

## 安全规则

- 源目录必须是Git工作树根目录，以便稳定排除缓存和忽略文件；目标目录只需是有效目录。
- 源端和目标端均允许存在未提交修改，脚本不读取目标Git状态。
- 同名文件无条件覆盖；目标独有文件不删除。
- 风险由双击脚本的人工操作者确认，脚本只负责复制和SHA256复核。
- 同步结束后必须在公司仓库审核`git status`和Diff，再由人工Commit/Push。

Operator、工具目录和任务导航的通用约束仍以
[R500](../../../report/design/rules/R500_operator_pipeline.md)和仓库`AGENTS.md`为准。
