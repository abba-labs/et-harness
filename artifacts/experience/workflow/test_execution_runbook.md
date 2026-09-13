# 硬件测试全链路执行 SOP（脚本-only）

状态：active
适用范围：ET_ATP_Testing；ET6801 FPGA/Silicon lane；可执行 IP/Case **以当前源码注册表为准**，不是「只有 CAN」。
最后核验：2026-09-10

规则正文见 [R500](../../../report/design/rules/R500_operator_pipeline.md)。本文只写可照做的入口、顺序与禁止事项，不复制规则。部署脚本机制见 [deploy_chain_mechanism](deploy_chain_mechanism.md)；测完整理见 [evidence_review_loop](evidence_review_loop.md)。芯片名大小写与报告发布见 [runner_chip_compare_blocks_publish](../platform/runner_chip_compare_blocks_publish.md)（已修复，勿再当现行缺陷）。

## 现象/背景

2026-09-09 版 SOP 把 `IP_REGISTRY` 写成「当前只注册 can」，并把启动写成直接调 `run_pipeline.py`。2026-09-10 对照源码：注册表已是多 IP；正式 HIL 入口是 `run_test.bat` / GUI → bootstrap → pipeline。继续按旧文会误跑全集、或手拼 OpenOCD/J-Link/Keil/pytest。

## 根因/机制

正式 HIL **只有一条脚本链**（配置不能选 Case；低层工具禁止手拼）：

```text
run_test.bat / run_config_gui.bat
  → tools/runner/bootstrap.py     （.venv + 本机 run_config.yaml）
  → tools/runner/run_pipeline.py  （读配置、校验、按 Profile 调仓库内 .ps1）
  → Profile 绑定的构建/部署脚本
  → tools/runner/run_ip_tests.py  （pytest 由 wrapper 注入 --et-hardware）
```

`run_pipeline.py` 的 `PIPELINE_STEPS` 顺序（与口头五步对应；编译在烧录前）：

| 口头步骤 | Pipeline 阶段 | 默认位置 |
|---|---|---|
| （可选）编译 BootROM | `build.bootrom` | 1 |
| 编译固件 | `build.firmware` | 2 |
| 烧 bitfile | `deploy.bitfile` | 3 |
| 烧 ROM | `deploy.bootrom` | 4 |
| 烧固件（含首次跳转） | `deploy.firmware` | 5 |
| （可选）只跳转不烧 | `execute.start_target` | 与 5 **互斥** |
| Case 测试 | `execute.run_tests` → 对 **整个** `IP_REGISTRY` 调 `run_ip_tests.py --within-pipeline` | 最后 |

FPGA 上 `bitfile + BootROM + PFLASH` 必须是**同一次 Pipeline Run** 的 PASS Manifest，详见部署链文档。

## 解法/操作

### 0. 正确脚本入口（只准这些）

| 意图 | 入口 | 实际范围 |
|---|---|---|
| 按当前 `run_config.yaml` 整轮 | `run_test.bat` 或 GUI「开始完整流水线」 | 配置打开的阶段；若 `run_tests: true` = **注册表全部 IP** |
| 只校验不干活 | `.\.venv\Scripts\python.exe tools\runner\run_pipeline.py --config run_config.yaml --check-only` | 不建 Run、不编译、不烧 |
| GUI 环境检查 | 「环境检查」 | `--check-only`，保留原开关 |
| 只编译 | GUI「编译固件」 | 只 `build.firmware`（会改写并保存配置开关） |
| FPGA 三件套烧录 | GUI「烧录固件」 | Profile `requires` 展开为 **bitfile + bootrom + firmware** |
| 只烧 bit / 只加载 ROM | GUI 对应按钮 | **不会**自动带上另一级；ROM 仍应先 bit 后 ROM |
| 已烧板上、跑注册表全集 | GUI「运行 PC 测试用例」 | `run_tests + generate_report`，**全部已注册 IP** |
| **单 IP / 单 Case** | 下方 `run_ip_tests.py`（官方 wrapper） | 仅 `--ip` / `--include-case` / `--level` 选中的集合 |
| 软件门禁（非 HIL） | GUI 门禁按钮或 `tools\validate_pc.py` | **永不碰硬件** |

单 IP / 单 Case（把 `can` / `can_p0_001` 换成用户指定的已注册 ID；bench 以本机配置的 `target.bench_profile` 为准）：

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe tools\runner\run_ip_tests.py `
  --ip can `
  --bench pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml `
  --target dut `
  --lane fpga `
  --include-case can_p0_001
```

独立调用会先跑完整 `validate_pc.py`；Pipeline 内部因 `--within-pipeline` 跳过。可用 `--level P0`、`--exclude-case`、受控 `--pytest-arg`。禁止改成裸 `pytest`。

### 1. 前置盘点（每轮）

```powershell
git -C <root> branch --show-current        # 必须 codex_dev（除非用户指定其他分支）
git -C <root> status --short
Get-Process UV4,JLink -ErrorAction SilentlyContinue   # 必须无
.\.venv\Scripts\python.exe -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

另查：

- 本次要跑的 IP 是否在 [`ip_registry.py`](../../../pc/et_test_platform/test_cases/ip_registry.py)（2026-09-10 核验 13 个：can, spi, stimer, syscnt, ipcm, dma, crc, fmac, cordic, aes, wdg, spinlock, uart）。**改注册表是代码变更，须用户指令。** Case 是否存在/执行过只信注册表 + session，见 [case_list_authority](../governance/case_list_authority.md)。
- `records/<CHIP>/<IP>/current` 与 `_PIPELINE/current` 回执；未整理会拦截，见证据回路文档。
- 串口必须在线（以本机 `dut.control.port` 为准）；HELLO 的 `firmware_build_id` 须等于 `dut.expected.firmware_build_id`。
- 编码环境见 [ps5_gbk_console_encoding](../environment/ps5_gbk_console_encoding.md)。`run_test.bat` 不设 `PYTHONUTF8`；Agent 终端长跑须先设上述环境变量。

### 2. 配置（本机 `run_config.yaml`，非代码）

- [`run_config.example.yaml`](../../../run_config.example.yaml)：Git 跟踪模板，安全默认全关、`confirm_hardware_actions: false`。**禁止当正式配置烧板。**
- `run_config.yaml`：唯一生效本机配置（`.gitignore`）。首次 `run_test.bat` 从 example 复制后立刻退出，须填本机路径再跑。GUI 首次复制后打开界面。
- `target.pipeline_profile`：单核 Formal 用 `tools/profiles/pipeline/et6801_fpga.yaml`；双核才用 `et6801_fpga_dualcore.yaml`（SPINLOCK）或 `et6801_fpga_ipcm.yaml`（IPCM）。本机当前选了哪个 **不是** 仓库默认。**13 个 IP 分属三种互斥形态，一轮部署跑不完**，见 [multiform_deployment_matrix](multiform_deployment_matrix.md)。
- 固定：`confirm_hardware_actions: true`（非 Renode 且选了硬件阶段或 `run_tests`）；`execute.start_target: false` 当本轮要 `deploy.firmware`。
- 开关矩阵（R500 §5.2；只按实际 Diff，禁止「准备测试就全烧」）：
  - **固件有变、全链路**：`build.firmware: true`，三级 `deploy.*: true`，`start_target: false`，`run_tests` 仅当用户要立刻测。
  - **只测已烧板上固件**：全部 build/deploy false，`run_tests: true`，`start_target: false`。
  - **只部署不测**：三级 deploy true，`run_tests: false`。
  - **只 PC 侧**：不编译不烧。

GUI 单步会**覆写并保存** pipeline 开关。点完「编译固件」「烧录固件」后，一键组合可能被清掉；下一轮一键前重新勾选。

### 3. 演练（非硬件）

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe tools\runner\run_pipeline.py --config run_config.yaml --check-only
```

PASS 才继续。缺工具路径、未知字段、Profile 与 `target.kind` 不匹配 → 退出码 2，不建 Run、不动硬件。

### 4. 启动（五选一，不要混用手拼）

1. **整轮（部署 + 注册表全部 IP）**：仅当用户明确要全量/发布/冻结。`run_test.bat` 或 GUI「开始完整流水线」。
2. **只编译**：GUI「编译固件」。
3. **FPGA 三件套**：GUI「烧录固件」（展开依赖）。不要只点「烧录 bitfile」再手烧 Flash。
4. **只跑已注册全集、不重烧**：GUI「运行 PC 测试用例」。
5. **单 IP / 单 Case**：§0 的 `run_ip_tests.py`。用户指定 CAN 一个 Case 时 **不要** `run_test.bat`。

Pipeline 与独立 `run_ip_tests.py` 共用单机锁，不能并行。

### 5. 监控与判读

```powershell
Get-Content artifacts\records\ET6801\_PIPELINE\current\stages\pipeline\pipeline.log -Tail 20
```

各阶段终端标志见部署链文档。pytest FAIL 仍写真实事实，不得改写成 PASS；缺 Evidence → `EVIDENCE_MISSING` 且非零。

真芯片不一致时 runner 会跳过报告发布（仅大小写不同已不再误跳过）——不代表测试无效，canonical 证据仍在 `current/`。

### 6. 证据闭环（R500 §6，测完必做）

按 [evidence_review_loop](evidence_review_loop.md)：`maintain_test_records.py extract` → 逐 Case 整理 → `check` → `review`（`--source` **绝对路径**）。不 review 则下一轮无法覆盖 `current`。

### 7. 禁止事项（硬约束）

- 禁止手拼 `openocd` / `JLink.exe` commander / `UV4.exe -f/-d/-b` / 裸 `pytest`。
- 禁止当正式 HIL 跑：`tools/fpga/et6801/run_cli_flow.ps1`（GPIO 诊断）、`tools/firmware/run_flash_and_run_et6801_firmware.ps1`（旧资源锁包装）、`tools/runner/can_box.py`（仪器诊断）。低层 `.ps1` 只允许被 Pipeline/GUI 调用。
- 禁止用 example yaml 直接烧板；禁止 `confirm_hardware_actions: false` 跑真实硬件。
- 禁止在 FPGA 上跳过**本轮** bitfile/BootROM 去重试 PFLASH（板上「以前烧过」不算）。
- 禁止 `deploy.firmware` 与 `execute.start_target` 同时开（双核/IPCM Profile **未声明**该互斥，更要靠配置）。
- 禁止用 Keil GUI 改生成的 `uvprojx`（SHA 漂移会拒烧，必须重新 generate）。
- 禁止把 `validate_pc.py` 绿当成 HIL PASS；未跑硬件写 `NOT_EXECUTED`。
- 禁止在用户只要单 IP/Case 时用 `run_test.bat` / GUI「运行 PC 测试用例」（会遍历整个 `IP_REGISTRY`）。
- 禁止为缩小测试面去改注册表，除非用户明确要求改代码。

## 边界与不适用

- 本 SOP 不覆盖 OTP/NVR/Option Byte/BOOTDEF；一键流程不写 BOOTDEF，那些仍要外层人工门禁。
- Silicon Profile 无 FPGA bit/ROM 前置；部署矩阵见 R500 §5.2。
- 2026-09-09 CAN 已知未闭环 FAIL 集合（P1_020×6 + P2_003×2 + P2_005×1）**只适用于当时 CAN 基线**，不得套到其他 IP。
- 本机 COM 口、Profile 选择、CAN 盒子开关只存在于被 git ignore 的 `run_config.yaml`，不是仓库默认。

## 依据与变化

- 2026-09-09 16:00 CST：按三次实测（测试轮/复测轮/全链路轮）固化为 SOP；当时注册表与验证面为 CAN，启动写法为直接 `run_pipeline.py`。
- 2026-09-10 11:00 CST：对照 `run_test.bat` / `bootstrap.py` / `run_pipeline.py` / `run_ip_tests.py` / `ip_registry.py` / GUI Schema / R500 修订。**废止「当前只注册 CAN」**：以源码 `IP_REGISTRY` 为准（当日 13 IP）。正式入口改为 bat/GUI → bootstrap；单 IP/Case 只允许 `run_ip_tests.py`。补充 example vs 本机配置、`confirm_hardware_actions`、firmware/start_target 互斥、GUI 单步覆写配置、禁止手拼与禁止诊断脚本冒充 HIL。交叉引用芯片比对经验（已 superseded），不在本文复述该缺陷。
