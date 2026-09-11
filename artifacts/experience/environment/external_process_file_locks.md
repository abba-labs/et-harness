# 活进程文件锁与 git stash 半失败恢复法

状态：active
适用范围：共享工作树上运行中的服务（GraphFlow MCP、Keil、JLink、hw_server 等）持有文件时的一切 git 写操作。
最后核验：2026-09-09（实测：stash 半失败 → 零损失恢复）

## 现象/背景

对被活进程锁住的文件执行 `git stash push -u`：stash 提交**成功**，但随后的工作树清理
（unlink 21 个文件）**全部失败**（warning: unable to unlink ... Invalid argument）→
索引残留全部暂存项，工作树处于"既非干净也非原样"的半应用状态。任何一项后续 git 写操作
都可能在此状态上放大损害。

## 根因/机制

- `stash push` 的实现是"先入 stash 提交 → reset 清理工作树"，**清理失败不会自动回滚**到 stash 前状态。
- GraphFlow MCP 服务进程运行中持有 `.graphflow-cache/graphflow-out` 的 SQLite/JSON 句柄，
  Windows 上被占用的文件不可 unlink。
- 沉没成本陷阱：预备份步骤失败（沙箱拒绝）后继续执行 stash，是决策链恶化的起点。

## 解法/操作（零损失恢复）

```powershell
# 1. 确认 stash 提交里内容完整（与工作树 diff 为空 = 无丢失）
git diff stash@{0} -- <涉及路径>
# 2. 仅重置索引（--mixed 默认，不动工作树文件）
git reset
# 3. 逐条核对 git status --short 与操作前快照一致
```

预防清单（执行 stash 前逐项过）：
1. 目标路径是否被活进程持有（GraphFlow/Keil/JLink/编辑器）？是 → 不 stash 这些路径。
2. 备份是否已成功落盘？备份失败 → 停止，不继续。
3. pathspec 收窄到纯业务文件，永远不包含工具缓存目录。

## 边界与不适用

- 同仓库 worktree 家族（本仓库 git-common-dir 指向 codex/projects/ET_Harness_ATP/.git）：
  stash 是 per-worktree 私有 ref，不跨树可见；但 commit 会移动共享分支——本工作区禁止 commit（用户硬约束）。

## 依据与变化

- 2026-09-09 09:55 CST：Task Context 编译被脏树阻塞 → 批准的"备份+stash"方案在备份被沙箱拒绝后
  仍执行 → 半失败状态；按上述三步零损失恢复，stash@{0} 保留作 ETIM 改动备份。
- 2026-09-09：教训固化为预防清单；后续会话未再触发。
