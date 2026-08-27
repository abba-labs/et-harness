# ET6801 PC/Firmware 公共层收口与全量 HIL

时间：2026-08-10 21:44 CST

## 结论

本轮按“PC 定义当前命令契约，Firmware 只解析并执行当前命令”的边界完成收口。未恢复旧命令、旧字段或历史实例扫描逻辑，也未在 Firmware 增加兼容分支。

当前软件门禁、ET6801 FPGA/SILICON 两个 Keil Target 构建、XC7VX980T 配置、BootROM 临时加载、PFLASH 擦写校验以及 Framework/UART/DMA 全量 HIL 均已通过。全量 HIL 共收集 121 项，结果为 118 PASS、3 SKIP、0 FAIL。

## 主要整改

- Firmware Service 注册改为使用 Board 明确声明的 UART/DMA 实例列表，不再按固定上限盲扫实例。
- UART/DMA Service 的持久存储由 Application 明确提供；注册失败立即整体回滚并停止启动，不静默忽略缺失实例。
- 删除旧的固定实例上限和保留控制 UART 实例字段，控制 UART 通过 Board 的测试实例列表自然排除。
- PC 正式结果使用注册表中的稳定 Case ID 和 IP ID，参数化 ID、测量值及产物路径进入统一结果。
- 修正 UART Case 的资源释放顺序：先关闭 Capture/IRQ/loopback，最后反初始化 UART；不放宽 Firmware 的状态校验。
- 修正 BootROM Keil CLI 脚本：以本次会话日志中的 `ET6801_BOOTROM_MAIN_REACHED` 为完成证据，随后只终止本次启动的 UV4 进程，避免 GUI 调试循环导致假超时。

## 验证结果

### 软件与构建

- `tools/validate_pc.py`：415 passed，9 skipped；Python syntax、Ruff、PC AST architecture、文档语义、Formal Case 编排、Firmware 单 IP 执行规则和生成工程契约全部 PASS。
- PC/Firmware 命令枚举逐项对比：UART 32/32、DMA 26/26，缺失项、冗余项和值不一致项均为 0。
- Formal Case 收集：121 nodes。
- ET6801 FPGA Keil Target：0 error，PASS。
- ET6801 SILICON Keil Target：0 error，PASS。
- PowerShell 语法解析与 `git diff --check`：PASS。

### 部署链路

- XC7VX980T bit 配置：CRC/EOS/DONE/IDCODE/Security 状态正常。
- BootROM 临时加载：到达 `main`，运行 PC 为 `0x20506348`。
- PFLASH `0x08000000-0x0807FFFF`：Erase、Program、Verify 全部通过；跳转后 PC 位于 Flash 区域 `0x08009576`。
- HELLO/SERVICE_LIST：Framework 公共服务、UART1/UART2、DMA0/DMA1 与 Board 声明完全一致。

### 全量 HIL

- 结果：118 PASS、3 SKIP、0 FAIL，总耗时约 94 秒。
- DMA、UART、UART+DMA、Framework 20 轮混合载荷通信均完成。
- 3 个 SKIP 均为已知环境/能力边界：当前连线无法稳定制造 framing error；当前运行环境无法确定性形成 Busy Detect；DUT 未声明直接 FIFO Access Feature。

## 证据

- 首轮全量 HIL（暴露 4 个 PC 清理顺序问题）：`artifacts/platform_freeze_hil/20260810_2136_full_hil/`
- 4 项定点复测：`artifacts/platform_freeze_hil/20260810_2148_uart_cleanup_retest/`
- 最终全量 HIL：`artifacts/platform_freeze_hil/20260810_2142_full_hil_pass/`
- XC7VX980T 配置：`artifacts/et6801_cli_flow/20260810_210018/01_xc7vx980t_program/`
- BootROM 加载：`artifacts/et6801_cli_flow/20260810_210622/04_bootrom_keil_debug/`
- PFLASH 擦写校验：`artifacts/flash_run/20260810_210739/`
- FPGA Target 构建：`artifacts/firmware_build/20260810_205250_FPGA/`
- SILICON Target 构建：`artifacts/firmware_build/20260810_205409_SILICON/`
- 最终软件门禁资源记录：`D:/lihuan/vibe_code/codex/artifacts/resource-control/tasks/20260810_214259_53dbf29b.json`

## 剩余边界

- 3 个 SKIP 不是回归失败，需更换硬件刺激条件或芯片能力后再解除。
- pytest 的 xUnit2 输出仍提示 `record_property` 警告；平台正式 JSON 结果和本轮 PASS/FAIL 判定不依赖该字段，后续可单独做报告噪声清理，不应为此改动协议或 Firmware。
- 首次直接重写 PFLASH 出现 Verify mismatch；本 FPGA 原型的可靠恢复流程仍是重新配置 bit、BootROM 到 main、再擦写 PFLASH。本轮已按该流程完成并取得 Verify PASS。
