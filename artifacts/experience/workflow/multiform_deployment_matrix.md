# 全量回归的部署形态矩阵：13 个 IP 不能在一次部署里跑完

状态：active
适用范围：ET6801 FPGA lane 的 IP 回归与全量回归；Silicon 未验证，不得外推。
最后核验：2026-09-11

规则正文见 [R500](../../../report/design/rules/R500_operator_pipeline.md) §5.1/§5.2。执行入口与禁止手拼见
[test_execution_runbook](test_execution_runbook.md)；各阶段的脚本绑定与通过标志见
[deploy_chain_mechanism](deploy_chain_mechanism.md)。本文只写"哪几个 IP 归哪种部署形态、按什么顺序跑"。

## 现象/背景

2026-09-11 全量回归用单核 Profile `et6801_fpga.yaml` 一次跑完注册表的 13 个 IP，结果：

- `IPCM` 34 个 execution **全 FAIL**；
- `SPINLOCK` 8 个 execution FAIL（全部是 `p2_*`/`p3_*` 的双核参数，`assert peer_ready is True` 失败）。

两个失败都**不是 IP 功能缺陷**：本轮部署形态没有 Core1 Peer，而这两个 IP 有 Case 依赖它。
当时的判断（"部署形态问题"）方向正确，但没有给出正确做法，也没有意识到它推翻了
"一次部署跑完全部 IP"这个前提。

## 根因/机制

注册表的 13 个 IP 分属**三种互斥的部署形态**，一轮 Pipeline 只能覆盖同形态的 IP：

| 形态 | Pipeline Profile | Core1 Peer 清单 | 覆盖的 IP |
|---|---|---|---|
| 单核 | `et6801_fpga.yaml` | 无 | can, spi, stimer, syscnt, dma, crc, fmac, cordic, aes, wdg, uart（11 个） |
| 双核 SPINLOCK | `et6801_fpga_dualcore.yaml` | `et6801_fpga_itcm.json`（脚本默认值） | spinlock |
| 双核 IPCM | `et6801_fpga_ipcm.yaml` | `et6801_fpga_ipcm.json`（Profile 内置绑定） | ipcm |

机制依据：`run_et6801_formal_dualcore.ps1` 的 `-PeerManifest` 默认值是
`firmware/chips/et6801/core1_peer/deploy/et6801_fpga_itcm.json`，脚本注释写明
"Existing SPINLOCK deployment remains the default"；`et6801_fpga_ipcm.yaml` 则在
`build.firmware` 与 `deploy.firmware` 两处显式绑定 `et6801_fpga_ipcm.json`。

三个 Profile 都是**全量部署**（build + bitfile + BootROM + firmware），所以切换形态必须重跑部署。

## 解法/操作

按形态分三段执行；每段都是"改 `run_config.yaml` 的 profile → 完整部署 → 跑该形态的 IP"。

### 段 1：单核（11 个 IP）

```yaml
target:
  pipeline_profile: tools/profiles/pipeline/et6801_fpga.yaml
pipeline:
  build.firmware: true
  deploy: {bitfile: true, bootrom: true, firmware: true}
  execute: {start_target: false, run_tests: false}
```

部署后跑 11 个单核 IP（在 `run_tests` 关闭时用 `run_ip_tests.py` 逐个执行；见 runbook §0）。

### 段 2：双核 SPINLOCK（spinlock）

```yaml
target:
  pipeline_profile: tools/profiles/pipeline/et6801_fpga_dualcore.yaml
```

`deploy.firmware` 内部会做 PFLASH 后再 `Invoke-PeerDeploy`（Core1 ITCM）。部署后跑 `spinlock`。

### 段 3：双核 IPCM（ipcm）

```yaml
target:
  pipeline_profile: tools/profiles/pipeline/et6801_fpga_ipcm.yaml
```

**IPCM 专项硬约束**（详见 [ET6801 IPCM §6.1.1](../../../test_case_doc/ipcm/ET6801_ipcm.md)）：
Peer 部署成功且 Mailbox Ready 后**禁止**再对 Core0 执行 `execute.start_target` 或 J-Link `r`——
会连带打死 Core1，导致 Case 入口 `peer_cancel`/`PEER_RESULT` 超时、13 Case/34 execution 全 FAIL。
该约束只适用于 `et6801_fpga_ipcm`，不得外推到 `et6801_fpga_dualcore` / SPINLOCK 或 Silicon。

### 顺序与耗时

顺序无强制依赖，但**每段都要完整部署**（当前 FPGA 环境不满足"跳过 bit/ROM"的条件）。
实测参考（2026-09-11）：单核部署 186s，13 IP 测试 1119s。三段合计约 25-30 分钟。

## 边界与不适用

- 三段的 IP 归属以**当前源码注册表**与各 IP Case 的 Peer 依赖为准；新增依赖 Core1 的 IP
  必须先确认它属于哪种 Peer 形态，不能默认丢进单核段。
- 单核段跑了双核 IP 会得到 FAIL，但**该 FAIL 不是功能结论**，不得写入 Case 知识或芯片文档
  作为该 IP 的测试结果。
- IPCM 的 `start_target` 约束不得外推；SPINLOCK 的部署不要求跳过 `start_target`。
- Silicon lane 未验证本矩阵的适用性。

## 依据与变化

- 2026-09-11 21:00 CST：由当日全量回归的 IPCM 34 FAIL / SPINLOCK 8 FAIL 沉淀。失败现场为
  `records/ET6801/IPCM/current/` 与 `records/ET6801/SPINLOCK/current/`（单核部署下的结果，
  不作为功能结论）。机制依据来自 `run_et6801_formal_dualcore.ps1` 默认值与两个 Profile 的
  Peer 绑定，以及 [deploy_chain_mechanism](deploy_chain_mechanism.md) 的双核脚本说明。
