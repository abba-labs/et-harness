# XC7Z045 J58/J59 外部 IO 边界扫描回环验证

时间：2026-07-21 18:30 CST

## 结论

真实硬件验证通过。JTAG 链识别到 `xc7z045`，6 对杜邦线均完成双向低/高电平测试，共 24 个采样点，结果为 `pass=24, fail=0`。

本次使用 XC7Z045 的 BSDL 和 JTAG `EXTEST`，未下载业务 bit，未写配置 Flash，未使用外部仪器或外接电阻。进入 `EXTEST` 前先装载 BSDL 安全向量，普通 GPIO 输出控制单元均保持高阻；每次只使能一个被测源端。结束和异常路径均恢复安全向量并复位 JTAG TAP。

## 实测连接

| 短接 | FPGA 封装管脚 | 结果 |
|---|---|---|
| J58.95 ↔ J58.96 | P21 ↔ R21 | 双向 0/1 PASS |
| J58.91 ↔ J58.92 | R22 ↔ R23 | 双向 0/1 PASS |
| J58.87 ↔ J58.88 | T22 ↔ U22 | 双向 0/1 PASS |
| J59.3 ↔ J59.4 | Y30 ↔ Y28 | 双向 0/1 PASS |
| J59.7 ↔ J59.8 | Y26 ↔ Y27 | 双向 0/1 PASS |
| J59.11 ↔ J59.12 | AA29 ↔ AA30 | 双向 0/1 PASS |

## 路由与命令

- 目标器件：`XC7Z045-FFG900`
- JTAG 线缆：`Digilent JTAG-SMT2 210251A08870`
- JTAG 链：`arm_dap` + `xc7z045`
- 执行工具：`D:\Software\Xilinx\Vivado\2024.2\bin\xsdb.bat`
- 测试脚本：`workspaces/xc7z045_io_loopback/xsdb/xc7z045_boundary_loopback.tcl`
- 一键复测：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validation\run_xc7z045_boundary_loopback.ps1`
- 恢复路径：安全边界向量 → `HIGHZ` → TAP `RESET`；必要时板卡断电重启
- 破坏性：否

## 证据

- JTAG 发现：`artifacts/fpga/xc7z045_io_loopback/20260721_181017_discovery/jtag_devices.txt`
- 完整 PASS 日志：`artifacts/fpga/xc7z045_io_loopback/20260721_182600_boundary_scan/boundary_loopback_retry.log`
- 一键复测 PASS 日志：`artifacts/fpga/xc7z045_io_loopback/20260721_183430_boundary_scan/boundary_loopback.log`
- 退出后 IDCODE 复核：`artifacts/fpga/xc7z045_io_loopback/20260721_182600_boundary_scan/post_cleanup_idcode.log`
- BSDL：`D:\Software\Xilinx\Vivado\2024.2\data\parts\xilinx\zynq\public\bsdl\xc7z045_ffg900.bsd`

SHA256：

- BSDL：`DD43DEA85D0F2F8C611834DF1E8FCEC392DE0844259DE4B2BAE9289FB2BE7370`
- 测试脚本：`3997B18850C676BD78EA102C99ED34036EB5A7F82D10CD0C435BA04E109C8CC7`
- 一键复测脚本：`EEEA9AE3515EE37A903B1BC3EC2E1601A4AC2DA848D26EDB4BBE0F9075085920`
- PASS 日志：`BE8A333E6FE704A722C168A531F18F3B5A8A8F8E7CE025D4AAE6C4EDEE6CAAE4`
- 一键复测 PASS 日志：`E9559313E003FD28408BDD6B9C5776342E03130F84007FA00A1733BC5F0D5A8B`
- 退出后 IDCODE 日志：`931803260FF5A2B43088CBBCE1DED94D76AC53DA981D130F293C271733B51712`

## 限制与剩余风险

本次只证明这 12 个管脚、6 条外部短接路径、JTAG 链和对应边界扫描单元可用；不代表全部 J58/J59 IO 已验证，也不覆盖 FPGA fabric 数字逻辑、业务 bit、时序裕量、边沿质量、驱动能力或信号完整性。

当前 Vivado 2024.2 安装仅含 Zynq-7000 WebPACK 综合器件数据（可见 `xa7z010/020/030`），没有 `xa7z045` 综合器件数据库，因此暂时不能在本机生成 XC7Z045 测试 bit。SVN 中的旧 `top.bit` 目标确为 `7z045ffg900`，但逻辑与 IO 驱动状态未知，本次未下载该 bit。
