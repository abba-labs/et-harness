# XC7Z045 GEM0 MDIO / Ethernet PHY smoke

时间：2026-07-22 09:25 CST

## 结论

PASS。通过 XC7Z045 PS JTAG DAP 临时将 `MIO52/MIO53` 复用为 GEM0
MDC/MDIO，成功发现板载 PHY，并确认当前网线链路已完成自动协商，工作在
1000 Mbps、全双工模式。测试后 GEM0 与 MIO 寄存器均恢复为测试前原值，
电脑端 USB 千兆网卡保持 `Up / 1 Gbps`。

## 范围与路径

- 目标：XC7Z045 PS GEM0、板载 U78 Ethernet PHY、J54 RJ45
- 路径：PC Realtek USB GbE -> 网线 -> J54 -> U78 -> GEM0 MDIO
- 控制：JTAG DAP / XSDB
- 性质：真实硬件，易失性寄存器测试
- 破坏性：否；未复位 CPU，未写 DDR、PL 或非易失存储

## 执行命令

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\lihuan\vibe_code\codex\projects\Et_Automated_Testing_Platform\scripts\validation\run_xc7z045_ethernet_phy_smoke.ps1" -ConfirmHardwareWrite
```

## 关键结果

```text
PS_SILICON_VERSION|3
MIO_52_BEFORE|0x00001601
MIO_53_BEFORE|0x00001601
MIO_52_TEST|0x00000280
MIO_53_TEST|0x00000280
PHY_CANDIDATE|addr=0|id1=0x0141|id2=0x0E90
PHY_ID|0x01410E90
PHY_LINK_UP|1
PHY_AUTONEG_COMPLETE|1
PHY_SPEED_RESOLVED|1
PHY_SPEED_MBPS|1000
PHY_FULL_DUPLEX|1
PHY_LINK_TEST_PASS|1
GEM0_RESTORE_PASS|1
MIO_RESTORE_PASS|1
ETHERNET_PHY_SELFTEST_PASS|1
XC7Z045_ETHERNET_PHY_SMOKE_PASS|1
```

恢复值：

```text
GEM0_NWCTRL_AFTER|0x00000000
GEM0_NWCFG_AFTER|0x00080000
MIO_52_AFTER|0x00001601
MIO_53_AFTER|0x00001601
```

## 证据

- 最终日志：`artifacts/fpga/xc7z045_ethernet_smoke/20260722_092553/ethernet_phy_link.log`
- PC 测试前状态：`artifacts/fpga/xc7z045_ethernet_smoke/20260722_092553/pc_adapter_before.txt`
- PC 测试后状态：`artifacts/fpga/xc7z045_ethernet_smoke/20260722_092553/pc_adapter_after.txt`
- 资源保护审计：`artifacts/resource-control/tasks/20260722_092555_40a586f4.jsonl`
- 首次无 MIO 复用诊断：`artifacts/fpga/xc7z045_ethernet_smoke/20260722_091921/ethernet_phy_link.log`

## 限制

- 本次只证明 RJ45/网线、PHY 链路协商和 GEM0 MDIO 管理路径。
- 未启用 `MIO16-MIO27` RGMII 数据通道，未收发 Ethernet frame。
- 未验证 GEM0 DMA、MAC 地址过滤、中断、ping、TCP/IP、吞吐率或长时间稳定性。
- 单块板、单根网线、单一电压和温度下的短时数字功能测试。
