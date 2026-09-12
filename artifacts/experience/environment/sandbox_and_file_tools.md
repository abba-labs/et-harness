# 沙箱与文件工具行为差异（DSH 环境特有）

状态：active
适用范围：DSH 会话内对 ET_ATP_Testing 工作区的文件操作。
最后核验：2026-09-09

## 现象/背景

同一路径下：`New-Item`/`Copy-Item`/`Set-Content`（PS cmdlet）报 `Access Denied`，
而 `git.exe` 写文件正常、DSH write 工具正常（含自动建父目录）。

## 根因/机制

DSH 文件沙箱对 pwsh 子进程的 cmdlet 文件创建路径有拦截（审批策略相关，2026-09-09 会话内
策略从 ask 切到 danger-full-access 后部分场景放开）；write 工具与 git.exe 走后端白名单。
具体拦截矩阵随沙箱策略变化，**不要依赖记忆中的矩阵，按"先试 write 工具"处理**。

## 解法/操作

- 建文件（含多级父目录）：一律用 DSH `write` 工具，不用 cmdlet。
- 改文件：DSH `edit` 工具（先 read 后 edit 是硬约束）。
- 目录创建供脚本使用：由 write 工具隐式完成；python 子进程在 danger-full-access 下可 mkdir。
- cmdlet 仅用于读、枚举、进程/服务查询。

## 边界与不适用

- 当前工具若明确拒绝某项操作，不得通过更换解释器或API绕过。下述历史工具差异仅作环境记录，不是替代权限或删除许可。
- danger-full-access 后 python -c 内 mkdir/unlink 实测可用；但勿在 ask 策略下假设可用。
- 本文档不覆盖 git 行为差异（见 [external_process_file_locks](external_process_file_locks.md)）。

## 依据与变化

- 2026-09-12 17:22 CST：补充安全边界；DSH历史操作方法不适用于当前Codex工具策略。
- 2026-09-09：知识迁移期间 cmdlet 建目录连续被拒、write 工具全部成功；备份目录创建失败
  （导致 stash 决策链恶化，见 external_process_file_locks）。已固化为"文件操作默认走 write 工具"。
