# XC7Z045 JTAG 实时通信 Transport 与硬件基准

时间：2026-07-22 13:33 CST

## 结论

XC7Z045 已通过 PC 经 Digilent JTAG-SMT2、XSDB 和 ARM DAP 的持续双向通信验证。当前实现可作为自动化测试平台的控制面和中小规模波形/结果回传通道，但属于软实时通信，确定性触发和高速采样仍应在 PL 内完成。

优化后的 Mailbox 命令中位往返延迟为 `20.97 ms`，相对优化前的 `37.94 ms` 降低 `44.74%`。16 KiB 连续块实测读取 `0.281 MiB/s`、写入 `0.336 MiB/s`，所有写入均由目标端 CRC32 校验。

## 测试范围与安全边界

- 目标：`XC7Z045-FFG900`
- 路径：`PC -> Digilent JTAG-SMT2 -> XSDB -> ARM DAP -> Cortex-A9/DDR`
- JTAG 时钟：稳定工作频率 `15 MHz`
- 临时高 OCM 范围：`0xFFFF0000–0xFFFFFFFF`，64 KiB
- 临时 DDR 范围：`0x3FFFC000–0x3FFFFFFF`，16 KiB
- 非易失写入：无；未访问 Flash、QSPI、SD、OTP、NVR 或熔丝
- 恢复：测试前备份 OCM/DDR，测试后恢复并回读验证，双核 reset-and-run，最后复测 Fabric BIST

## Transport 设计

- 保持一个 XSDB 进程和一个 DAP 连接持续存在，避免每个命令重新启动工具。
- 块数据使用 `mrd -bin -file` / `mwr -bin -file`，避免控制台十六进制文本转换。
- Cortex-A9 代理运行在高 OCM，MMU 和 Cache 关闭；有效载荷位于已经验证的 DDR 窗口。
- 64 字节 Mailbox 使用序号、状态、长度和 CRC32。
- 主机将请求字 4–9 一次写入，`host_seq` 位于最后一个字，作为请求提交标志。
- 目标将响应字 10–15 一次读取，`target_seq` 位于最后一个字，作为响应完成标志。

## 实测结果

### 命令延迟

| 指标 | 优化前 | 优化后 | 变化 |
|---|---:|---:|---:|
| Mailbox median | 37.943 ms | 20.969 ms | -44.74% |
| Mailbox P95 | 46.158 ms | 33.496 ms | -27.43% |
| Mailbox min | 23.725 ms | 18.034 ms | -23.99% |
| XSDB bridge 本地管道 median | 0.109 ms | 0.069 ms | 仅表示 PC 进程间开销 |

Mailbox 最终状态为 `DONE`，`host_seq=target_seq=56`，`error_code=0`，最终 16 KiB CRC 一致。

### 连续块吞吐

| 块大小 | 读取 | 写入（bypass cache sync） |
|---:|---:|---:|
| 1 KiB | 0.095 MiB/s | 0.122 MiB/s |
| 4 KiB | 0.235 MiB/s | 0.288 MiB/s |
| 16 KiB | 0.281 MiB/s | 0.336 MiB/s |

单独的只读分块诊断显示，当块大小从 16 KiB 增长到 64 KiB、256 KiB 和 4 MiB 时，DAP 读取约为 `0.437`、`0.506`、`0.533` 和 `0.537 MiB/s`。因此当前 16 KiB 安全窗口尚未达到链路极限；未来若经新的硬件门禁批准扩展 DDR 缓冲区，应优先使用不小于 64 KiB 的批量传输。

### JTAG 时钟诊断

适配器报告支持 `30 MHz`，但切换后扫描链变为 `whole scan chain (incomplete IR length definition)`，APU 无法枚举；未在 30 MHz 下执行 DDR 读写。两次诊断均成功恢复到 `15 MHz`。因此本板当前可靠上限按 `15 MHz` 使用，不能把 30 MHz 作为可用优化方案。

## 故障修正

首次代理启动曾进入 Cortex-A9 Undefined Handler，现场为 `PC=0xFFFF0090`、`LR=0xFFFF0050`、错误码 `0xBAD00001`。根因是启动代码使用 Cortex-A9 不支持的旧式整 D-cache 失效操作 `mcr p15,0,<Rd>,c7,c6,0`。代理启动时 Cache 本就关闭，删除该操作后硬件运行通过；如未来需要 D-cache 维护，必须改用 set/way 流程。

## 恢复与最终状态

- `OCM_RESTORE_PASS|1`
- `DDR_RESTORE_PASS|1`
- `APU_RESET_RUN_PASS|1`
- `FABRIC_BIST_HARDWARE_PASS|1`
- Fabric BIST 最终值：`0xB101FFF0`
- 总验证结果：`XC7Z045_JTAG_TRANSPORT_VALIDATION_PASS|1`

## 验证入口与证据

执行命令：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  scripts\validation\run_xc7z045_jtag_transport_benchmark.ps1 `
  -ConfirmHardwareWrite
```

主要证据：

- 优化后完整产物：`artifacts/fpga/xc7z045_jtag_transport/20260722_133115/`
- 优化后结果：`artifacts/fpga/xc7z045_jtag_transport/20260722_133115/benchmark.json`
- 优化前基线：`artifacts/fpga/xc7z045_jtag_transport/20260722_132040/benchmark.json`
- 主机 Transport：`workspaces/xc7z045_jtag_transport/host/jtag_transport.py`
- Cortex-A9 代理：`workspaces/xc7z045_jtag_transport/src/jtag_agent.c`

此外，Python 协议单元测试 `5/5 PASS`，Python 编译检查、Cortex-A9 代理编译、实际 XSDB/Tcl 执行均通过。

## 剩余限制

- JTAG/XSDB 只提供软实时交互，不适合逐采样点持续上传高速原始波形。
- 当前可写 DDR 数据窗口只有 16 KiB；扩展到 64 KiB 以上需要单独确认安全内存范围并重新执行人工门禁。
- 当前结果来自单块板卡、单个适配器、15 MHz、室温短时测试，不代表多板、温压和长时间稳定性。
- Transport 尚未接入平台公共 `FpgaBackend` / Target API；当前为已实测的 XC7Z045 板级适配原型。
