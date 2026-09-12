# review CLI 相对 --source 在父回执存在时崩溃

状态：active（修复已实现，回归NOT_EXECUTED）
适用范围：`tools/runner/maintain_test_records.py review` 命令；父回执（_PIPELINE/current/publication.json）已存在时。
最后核验：2026-09-09（全链路轮实测）

## 现象/背景

`review --source artifacts/records/ET6801/CAN/current`（相对路径）报错：
"'artifacts\\records\\ET6801\\CAN\\current' is not in the subpath of 'D:\\...\\ET_ATP_Testing'"。

## 根因/机制

`record_workspace.py::review_workspace` 在父回执存在时执行 `root.relative_to(repository)`——
CLI 传入的相对 source 无法对绝对仓库路径做 relative_to，抛 ValueError。

**关键陷阱**：同一条命令在父回执**不存在**时成功（该分支被跳过）——首轮 review 通过会诱导
第二轮继续用相对路径，然后在父回执已建后崩溃。前置状态决定行为，故障与其发生轮次绑定。

## 解法/操作

`--source` 与 `--manifest` 一律使用**绝对路径**：

```powershell
$cur = (Get-Location).Path
.\.venv\Scripts\python.exe tools\runner\maintain_test_records.py review --chip ET6801 --ip can --lane fpga `
  --source "$cur\artifacts\records\ET6801\CAN\current" `
  --manifest "$cur\artifacts\records\ET6801\CAN\current\manifest.json"
```

现已在`review_records`和`review_workspace`入口对repository/root使用`.absolute()`，统一相对路径，
保留后续safe_path对符号链接和仓库边界的检查；不使用resolve消除链接后绕过原检查。回归尚未执行。

## 边界与不适用

- extract/check/index 不经过该分支，相对路径可用（实测 check/index 正常）。
- 绝对路径方案在两种前置状态下均验证通过（父回执存在/不存在）。

## 依据与变化

- 2026-09-12 17:20 CST：完成入口路径修正并补回归用例；按人工要求未执行测试，因此不标记验证通过。
- 2026-09-09 15:35 CST：全链路轮收尾时发现；相对路径失败、绝对路径成功，双闸门放行验证。缺陷上报用户，未修（零代码约束）。
