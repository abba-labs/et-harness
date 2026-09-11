# 五级部署脚本机制：编译→bit→ROM→PFLASH→运行

状态：active
适用范围：ET6801 FPGA lane（XC7VX980T 原型）；脚本位于 `tools/fpga/et6801/` 与 `tools/firmware/`。单核 Profile `et6801_fpga.yaml`；双核/IPCM 另绑 `run_et6801_formal_dualcore.ps1`。
最后核验：2026-09-10

操作入口与禁止手拼见 [test_execution_runbook](test_execution_runbook.md)。本文只讲部署阶段机制，不写 Case 选择；
哪些 IP 需要哪种部署形态见 [multiform_deployment_matrix](multiform_deployment_matrix.md)。

## 链路总览

`run_pipeline.py` 按固定顺序跑已启用阶段；Profile 只绑定仓库内 `.ps1` 和参数来源（`from: environment.tools.*` / `dut.*` 或字面量）。

```text
build.bootrom    build_bootrom.ps1
                 Keil -b ROM，map 校验链接基址 0x20500000
build.firmware   单核：build_et6801_test_firmware.ps1
                 （先 generate_keil_project.py，再 UV4 -r，Target SILICON）
                 双核/IPCM：run_et6801_formal_dualcore.ps1 -Action Build
deploy.bitfile   program_xc7vx980t.ps1 + tcl/program_xc7vx980t.tcl
                 Vivado 烧 XC7VX980T 配置 SRAM（volatile，掉电丢失）
deploy.bootrom   load_bootrom_keil_debug.ps1
                 Profile 固定 -SkipBuild -ConfirmRamLoad；只写 FPGA RAM 窗口
deploy.firmware  单核：flash_and_run_et6801_firmware.ps1
                 （UV4 -f + ET6801.FLM，再 J-Link 读向量表跳转）
                 双核：同一 PFLASH 后再 Invoke-PeerDeploy（Core1 ITCM）
execute.start_target  单核：同一 flash 脚本加 -SkipFlash（只再跳一次）
                      双核/IPCM：仍走 flash_and_run_et6801_firmware.ps1 -SkipFlash
                      （不是 dualcore Deploy 脚本）；-SkipFlash 不查 bit/ROM 前置
```

## 同轮硬约束（FPGA PFLASH）

顺序硬约束：`deploy.firmware` 依赖**同一次 Pipeline 运行**内 `deploy.bitfile` + `deploy.bootrom` 的 PASS Manifest。两层都会拦：

1. Profile：`deploy.firmware.requires: [deploy.bitfile, deploy.bootrom]`。只开 firmware 时 Runner 报 missing steps。GUI「烧录固件」会展开依赖，一次打开三级 deploy。
2. 脚本：`Assert-EtPipelineStagePassed` 检查本轮 `ET_ARTIFACT_RUN_DIR` 下 `stages/deploy_bitfile` 与 `deploy_bootrom` 的 `result=PASS`。手调 `.ps1`、或缺环境变量 → 「Pipeline run context is missing」，在任何擦写前失败。

原因：PFLASH 算法依赖本轮 FPGA 逻辑配置 + BootROM 系统初始化。bitfile 掉电即丢，不能凭「板上以前烧过」跳过。R500 §5.2：只要本轮要烧 FPGA 固件，即使 bit/ROM 源码没变，正式 HIL 仍必须完整三阶段。

GUI「加载 BootROM」**不会**自动先烧 bit（Profile 未声明该依赖）——FPGA 上仍应先 bit 后 ROM。

`-SkipFlash` 只用于不改 PFLASH 的 `start_target`，此时不查 bit/ROM 前置。

## `deploy.firmware` 与 `start_target` 互斥

`deploy.firmware` 已含首次跳转。正确配置：

- 烧录轮：`deploy.firmware: true`，`execute.start_target: false`
- 仅复跑已烧镜像：firmware false，`start_target: true`

`et6801_fpga.yaml` / `et6801_silicon.yaml` / `et6801_fpga_manual.yaml` 在 Profile 里声明了 `mutually_exclusive`。**`et6801_fpga_dualcore.yaml` / `et6801_fpga_ipcm.yaml` 没有声明**——两开关同时 true 时会烧完再跳一次。操作上仍禁止同时打开。

## 各级通过标志与关键校验

| 级 | 终端标志 | 内嵌校验 |
|---|---|---|
| build.bootrom | `ET6801_BOOTROM_BUILD_PASS` | `0 Error(s)`；rom.axf/hex/bin/map 齐全；map 证明 0x20500000 |
| build.firmware | `ET6801_TEST_FIRMWARE_BUILD_PASS` 或 `ET6801_FORMAL_DUALCORE_BUILD_PASS` | 工程生成记录 SHA 双向校验（Keil GUI 改工程=拒）；axf/hex 齐全 |
| deploy.bitfile | `XC7VX980T_VOLATILE_PROGRAM_PASS` | 恰好一个 XC7VX980T（XC7Z045 拒烧）；CRC/EOS/DONE/IDCODE/Security；Vivado 全局 Mutex `ET_XC7VX980T_VOLATILE_PROGRAM` |
| deploy.bootrom | `ET6801_BOOTROM_MAIN_REACHED\|PC=0x20506348` | 隔离副本注入有界调试 INI，120s 超时杀进程；只写 RAM，不写 PFLASH/NVR |
| deploy.firmware | `ET6801_FLASH_RUN_PASS\|region=flash` | PFLASH 边界+算法绑定；Erase/Program/Verify 三证据缺一即 fail；向量表 MSP/handler；PC 落在 Flash/RAM |

产物根：`artifacts/records/ET6801/_PIPELINE/current/stages/<step>/manifest.txt`（`result=PASS` 才算本轮前置）。

## 门禁旗标（逐级独立确认）

Profile 注入 `-ConfirmProgram`（bit）/ `-ConfirmRamLoad`（ROM）/ `-ConfirmPFlashProgram`（破坏性烧写）+ `-ConfirmRunControl`（跳转）；双核另有 `-ConfirmPeerDeploy`。外层还有 `pipeline.confirm_hardware_actions: true` 与 GUI Yes/No。这不是通用授权；OTP/NVR/Option Byte 仍要外层人工门禁。

`-PrepareOnly` 打印动作计划不执行。编译（`hardware_action: false`）不要求 `confirm_hardware_actions`。

## 防呆设计（已在代码层堵死，勿绕）

- 生成工程被 Keil GUI 改过 → SHA 漂移拒绝烧写（必须 regenerate）
- J-Link 探针序列号：Keil 配置与运行控制一致性（`-1` 自动选择 ↔ UINT32_MAX 等价）
- 多 JTAG 链并存：TCL 拒绝非唯一 XC7VX980T（07-26 两个 Digilent 事故的固化）
- PFLASH Verify mismatch 教训：烧前必须完成**本轮** bit+BootROM，不得跳过直接重试 Flash
- 已有 `UV4` / `JLink` 进程 → 编译/烧录/跳转失败
- 低层 `.ps1` 不是人工入口；直调会被缺 `ET_ARTIFACT_RUN_DIR` 或缺本轮 Manifest 拒绝

## 边界与不适用

- 禁止把 OpenOCD / J-Link commander / `UV4 -f` 手拼成「等价部署」。
- `run_cli_flow.ps1`、`run_flash_and_run_et6801_firmware.ps1` 不是 Formal Pipeline 阶段。
- Silicon 无 bitfile/BootROM 前置；不要把 FPGA 三件套套到硅后。

## 依据与变化

- 2026-09-09 15:35 CST：全链路轮逐级实测通过（bootrom 15:1x → firmware build → bit → ROM main
  0x20506348 → PFLASH Verify OK → FLASH_RUN_PASS pc=0x0801C454 region=flash）；本文由脚本逐个
  精读 + 实测日志提炼。与 07-26/08-13 历史报告机制一致，未发现脚本层回归。当时链路按单核
  `build_et6801_test_firmware.ps1` / `flash_and_run_et6801_firmware.ps1` 记录。
- 2026-09-10 11:00 CST：补充双核/IPCM 脚本绑定、GUI「烧录固件」展开 `requires`、GUI「加载 BootROM」不带 bit、`ET_ARTIFACT_RUN_DIR` 本轮 Manifest 才是 PFLASH 前置、firmware/start_target 互斥在 dualcore/ipcm Profile 未声明、禁止手调 `.ps1`。不改 09-09 单核实测结论。
