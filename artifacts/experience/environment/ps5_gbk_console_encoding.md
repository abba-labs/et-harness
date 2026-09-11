# PS5.1/GBK 控制台编码：崩溃与乱码的统一防御

状态：active
适用范围：本机所有长输出 Python/PowerShell 进程（DSH pwsh 工具即 PS5.1）。
最后核验：2026-09-09（全链路轮实测复现+解法验证）

## 现象/背景

三类症状：
1. **崩溃级**：流水线流式输出含 U+FFFD（replacement char）→ Python `print()` 在 GBK stdout 抛
   `UnicodeEncodeError: 'gbk' codec can't encode character '\ufffd'` → 整条流水线 abort 记 FAIL
   （2026-09-09 build.bootrom 阶段实际发生，流水线死亡于编译已成功之后）。
2. **乱码级**：PS5 控制台读 UTF-8 中文输出显示 mojibake（不影响文件内容，影响人读判读）。
3. **文件级**：`>` 重定向写 UTF-16、`-Encoding utf8` 带 BOM（写 JSON 会坏）。

## 根因/机制

- `run_pipeline._run` 对 PowerShell 子进程用 locale(cp936) + errors='replace' 解码输出；
  replacement 字符回流到 Python stdout（同样 GBK）时无法编码 → 异常。
- 平台 2026-09-08 已有同款教训（syscnt 芯片文档状态块记录"编码环境设置 PYTHONUTF8=1"），
  但未形成启动清单，后续会话再次踩坑。

## 解法/操作（启动环境变量，非代码修改）

```powershell
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
& .\.venv\Scripts\python.exe tools\runner\run_pipeline.py --config run_config.yaml
```

写文件类（PS5 侧）：
- JSON：`[System.IO.File]::WriteAllText($path, $text, (New-Object System.Text.UTF8Encoding($false)))`
- 读 UTF-8 文本：`Get-Content -Encoding utf8`（否则按 GBK）

## 边界与不适用

- PYTHONUTF8 只影响 Python 进程自身编码行为；PowerShell 原生输出乱码需在读取侧 -Encoding utf8。
- 长任务验证输出是否被污染：直接读落盘日志文件而非信任控制台回显。

## 依据与变化

- 2026-09-09 11:00 CST：PS5 乱码/重定向坑在本会话多次遇到并规避（此前记忆已有记录，本次纳入经验库体系）。
- 2026-09-09 14:50 CST：崩溃级复现（build.bootrom 流式输出 U+FFFD → 流水线 abort，现场保留于
  runs/tooling/pipeline-failed-scenes-20260909/scene2-gbk-crash，其中 Keil 日志证明编译实际成功）；
  PYTHONUTF8=1 重启后全链路通过。原教训升级：任何长输出子进程调用前必须设编码环境。
