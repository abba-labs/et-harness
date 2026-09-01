# XC7Z045 新板双 JTAG、A9、OCM/DDR 与 Fabric BIST 复测

时间：2026-07-23 11:34 CST

## 结论

在当前双 JTAG 连接条件下，端口身份确认结果为：

- `tcp:127.0.0.1:3121`：XC7VX980T，仅进行只读识别。
- `tcp:127.0.0.1:3122`：ARM DAP + XC7Z045，本次所有测试与易失性写入均限定在该端口。

XC7Z045 的 A9、OCM/DDR 临时测试窗口、JTAG mailbox 传输、PL Fabric BIST 及 J58/J59 六组外部 IO 回环均通过。OCM 和 DDR 在测试后完成回写与 SHA256 一致性验证。Fabric BIST bitstream 仅写入 FPGA 配置 SRAM，没有写入 Flash、QSPI、SD、OTP、NVR 或熔丝。

## 实测结果

- JTAG 身份门禁：PASS，3122 仅发现 `arm_dap` 与 `xc7z045`。
- DDR 控制器状态：Normal mode，`DDRC_MODE=1`。
- Cortex-A9 agent：加载、运行及 mailbox 发布 PASS。
- OCM：`0xFFFF0000–0xFFFFFFFF`，64 KiB 备份、临时使用、恢复回读 PASS。
- DDR：`0x3FFFC000–0x3FFFFFFF`，16 KiB 备份、临时使用、恢复回读 PASS。
- APU 恢复：双核 reset-and-run PASS。
- JTAG mailbox/CRC：PASS。
- Fabric BIST：烧录后第一次读取 `0xB101FFF0`，Logic、BRAM、DSP、MMCM 全部 PASS。
- J58/J59 外部 IO：六组短接、双向 0/1 共 24 个采样点，`pass=24, fail=0`。

恢复校验：

- OCM 恢复前后 SHA256：`41666FCD94D1FBB44F8E38EAE4D48B18D9BA98A9404C0C67E70BFC3DA253017D`
- DDR 恢复前后 SHA256：`4FE7B59AF6DE3B665B67788CC2F99892AB827EFAE3A467342B3BB4E3BC8E5BFE`

## 证据

- 完整 A9/OCM/DDR/JTAG 测试：
  `artifacts/fpga/xc7z045_jtag_transport/20260723_112736`
- Fabric BIST 易失性烧录与状态：
  `artifacts/fpga/xc7z045_fabric_bist/20260723_113309_revalidation`
- J58/J59 外部 IO 回环：
  `artifacts/fpga/xc7z045_io_loopback/20260723_114645_boundary_scan`
- 双 JTAG 初始识别：
  `artifacts/fpga/xc7z045_revalidation/20260723_112238`
- Fabric BIST bitstream SHA256：
  `705E4BDDF3EF62D77AD29FA85F557B4A8EBE6D7040FB91AEA739C5E15C7931CD`

## 限制与当前状态

- OCM 测试覆盖高 64 KiB，DDR 本轮覆盖高 16 KiB，并非全存储单元 March/保持测试。
- Fabric BIST 为短时功能测试，不能替代温度、电压、老化或时序裕量测试。
- 外部 IO 仅覆盖 J58/J59 的 12 个管脚和 6 条短接路径，不代表全部 IO 已验证，也不覆盖驱动能力、边沿质量和信号完整性。
- 本轮未测试以太网、USB、启动介质或长期稳定性。
- XC7Z045 当前 PL 中保留的是临时 Fabric BIST 设计；要恢复观测器功能，需要重新烧录对应观测器 bitfile，或在板卡已配置上电启动镜像时断电重启。

## 2026-07-23 11:46 CST 追加 IO 复测

采用 XC7Z045 BSDL 与 JTAG `EXTEST`，进入 EXTEST 前预装安全高阻向量，每次仅使能一个源端。以下六组均完成双向低/高电平回环：

- J58.95 ↔ J58.96
- J58.91 ↔ J58.92
- J58.87 ↔ J58.88
- J59.3 ↔ J59.4
- J59.7 ↔ J59.8
- J59.11 ↔ J59.12

结果：`BOUNDARY_LOOPBACK_PASS|pairs=6|samples=24`。结束后恢复安全向量并复位 JTAG TAP；3122 临时 `hw_server` 已关闭，3121 的 XC7VX980T 服务保持运行。
