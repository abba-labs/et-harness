# XC7Z045 GEM0 RGMII / DMA / PC 通信调查

时间：2026-07-22 10:33 CST

## 结论

当前结果为 **PARTIAL / 未打通 PC 通信**，不能把 GEM0 RGMII、ping 或 UDP 吞吐标记为 PASS。

已经验证：

- J54 外部 PHY 可通过 GEM0 MDIO 访问，PHY ID 为 `0x01410E90`。
- PHY 与 PC 能完成 10/100/1000 Mbps 自动协商，先前 1000BASE-T 全双工链路检查通过。
- Cortex-A9 裸机固件能在高 OCM 运行，GEM0 DMA 描述符能够启动发送。
- 每轮测试后的 PHY 状态、GEM/MIO/时钟寄存器、高 OCM 和 APU 均完成恢复。

尚未通过：

- PC 没有收到 FPGA 启动广播帧。
- GEM0 接收端持续报告 FCS/CRC 错帧，未形成可交给 DMA 的有效 ARP/ICMP/UDP 帧。
- 因此 ARP、ping、UDP echo 和吞吐率均未通过。

## 已排除项

- 网线未连接或 PHY 不存在：已排除，MDIO、链路和自动协商正常。
- PS PLL 未锁定：已排除，`PLL_STATUS=0x0000003F`。
- MIO16-MIO27 基本复用值错误：当前 `0x3902/0x1903` 与 Vivado 2024.2 的 ZC702 GEM0 RGMII 模板一致。
- 100 Mbps GEM 时钟使用错误分频：已修正为 `1300 MHz / 52 / 1 = 25 MHz`。
- 100 Mbps MAC 仍处于 10 Mbps 模式：已补上 `GEM_NWCFG.SPD`。
- PHY RGMII RX 内部延时：开、关两种均测试；关闭时 FCS 错误更多，保留开启配置。
- 降速绕过：10 Mbps 全双工、2.5 MHz 精确 GEM 时钟仍出现 FCS 错误。

## 当前卡点

卡点位于 `88E1318 PHY RGMII pins <-> XC7Z045 MIO16-MIO27/GEM0` 的数字帧通道。链路脉冲、MDIO 管理通道和 DMA 控制面正常，但 RGMII 接收采样得到的帧 CRC 不正确。下一步需要使用该板原始 Vivado PS7 Ethernet 配置或一份已知可工作的 FSBL/lwIP 工程作为初始化基线；若仍失败，应检查 PCB RGMII 走线、数据位顺序、RX_CTL/RX_CLK 和 PHY strap/时延配置。

## 关键证据

- 1 Gbps 双延时：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_101426/`
- 100 Mbps、曾收到 1 个 CRC 正确但非目标帧：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_101855/`
- 100 Mbps、精确 25 MHz、双延时：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_102716/`
- 100 Mbps、精确 25 MHz、关闭 RX 延时：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_102908/`
- 100 Mbps、补 `NWCFG.SPD`：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_103014/`
- 10 Mbps、精确 2.5 MHz：`artifacts/fpga/xc7z045_ethernet_data_path/20260722_103203/`

所有上述硬件轮次均记录 `ETHERNET_DATA_PATH_CLEANUP_PASS|1`。

## 恢复路径

测试脚本自动恢复所有暂时修改的易失状态并复位 APU。若后续测试清理失败，恢复方式为整板断电重启；未写入 QSPI、SD、eMMC、OTP、fuse 或其他非易失介质。

## 2026-07-22 11:15 CST 追加根因结论

结论升级为：**GEM0/CPU/DMA 正常，PC 通信失败的根因是原理图中
XC7Z045 固定 GEM0 MIO 信号与 88E1318 RGMII 网络名错接。** 这不是
ARP、ping、网线、PHY 自协商或普通 PHY 延时参数问题。

AMD UG585 的 GEM0 RGMII 固定引脚表要求：

| MIO | 固定 GEM0 功能 | V1 原理图网络 | 判定 |
|---:|---|---|---|
| 16 | TX_CLK | ETH0_TXCLK | 正确 |
| 17 | TX_D0 | ETH0_TXD0 | 正确 |
| 18 | TX_D1 | ETH0_TXD2 | 错接 |
| 19 | TX_D2 | ETH0_TXD3 | 错接 |
| 20 | TX_D3 | ETH0_TXCTL | 错接 |
| 21 | TX_CTL | ETH0_RXCLK | 错接且存在输出冲突风险 |
| 22 | RX_CLK | ETH0_RXD0 | 错接，GEM 接收时钟实际接到数据 |
| 23 | RX_D0 | ETH0_RXD1 | 错接 |
| 24 | RX_D1 | ETH0_RXD2 | 错接 |
| 25 | RX_D2 | ETH0_RXD3 | 错接 |
| 26 | RX_D3 | ETH0_RXCTL | 错接 |
| 27 | RX_CTL | ETH0_TXD1 | 错接 |

原理图证据：
`D:/lihuan/vibe_code/SVN/Software/ET6001/02 FPGA验证/硬件/01 SCH/ET6001FD980T_V1.pdf`
第 21 页。官方固定映射：
`https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/RGMII-Interface-via-MIO`。

### 分层实测闭环

- GEM 本地回环绕过 MIO 和 PHY 后正式 PASS：帧内容匹配 `4/4`，GEM
  TX/RX 均为 `4` 帧，FCS 错误 `0`，DMA 错误 `0`。证据：
  `artifacts/fpga/xc7z045_ethernet_data_path/20260722_110806/`。
- PHY 数字回环配置已经读回确认：Page 2 Reg21 为目标值，BMCR 为
  `0x6100`（100 Mbps、全双工、loopback）。帧从 GEM 发出并由 PHY
  返回后，GEM 记录 `TX=4`、有效 `RX=0`、`FCS error=4`。证据：
  `artifacts/fpga/xc7z045_ethernet_data_path/20260722_105627/`。
- PHY RGMII 延时四种组合均为同一结果，排除 RX/TX delay bit 选错：
  `both=20260722_105627`、`rx=20260722_110328`、
  `tx=20260722_110410`、`none=20260722_110442`。
- 铜缆链路和 MDIO 正常、外部 PC 收包为零，与错接现象一致：PHY 的
  铜缆侧可以独立建链，但 RGMII 数字帧无法正确进入/离开 GEM。

### 对早先判断的纠正

早先“`0x3902/0x1903` 与 ZC702 模板一致”的描述不准确。Vivado
2024.2 自带 ZC702 preset 对 MIO16–27 使用 `HSTL 1.8V`、slow slew、
pull-up disabled。已准备改为该官方电气配置进行补充复测，但因全局资源
守卫正被另一个项目的真实任务占用，尚未执行。即使该补测改善边沿质量，
也无法修复 MIO21/MIO22 的 TX_CTL/RX_CLK 固定功能错接，因此不改变根因。

### 修复建议

1. 先用 Cadence 从实际投板版本导出 `U75(MIO16–27) <-> U78` pin-to-pin
   netlist，确认实物 PCB 版本；V2 `.DSN/.brd` 目前没有可用 Cadence
   导出工具，不能仅凭文件名声称已经修正。
2. 下一版 PCB 必须按 UG585 固定顺序重连上述 12 根 RGMII 信号，并做
   RGMII 等长/时序审查。
3. 当前 PCB 无法靠 GEM0 MIO 软件重映射修复；MIO Ethernet 每根信号
   功能固定。若必须保留现板，只能硬件飞线/改板，或改用 PL+外接的正确
   Ethernet PHY/接口；JTAG 可继续作为低速控制通道。

## 2026-07-22 11:29 CST 补充复测

先前未执行的 AMD ZC702 MIO 电气配置复测现已完成。MIO16–27 使用
`HSTL 1.8V + slow slew + pull-up disabled`，PHY 使用官方 100 Mbps
数字回环配置。结果仍为：

- PHY Page 2 Reg21 读回：`0x2030`
- PHY BMCR 读回：`0x6100`
- GEM TX frame counter：`4`
- GEM valid RX frame counter：`0`
- GEM RX FCS error counter：`4`
- DMA error：`0`
- 清理恢复：`PHY_STATE_RESTORE_PASS`、`GEM_MIO_CLOCK_RESTORE_PASS`、
  `OCM_RESTORE_PASS`、`APU_RESTORE_RESET_START` 全部为 `1`

证据目录：
`artifacts/fpga/xc7z045_ethernet_data_path/20260722_112811/`。

因此已经排除早先 MIO 上拉、slew 和 HSTL 配置不准确导致失败的可能性。
当前证据直接证明故障在 GEM 管脚之后、PHY 回环内部之前的板级 RGMII
数字通道。V1 原理图中的固定 MIO 映射冲突是明确的设计错误；但若要把
结论严格表述为“当前这块实物 PCB 铜箔必然按 V1 错误网络连接”，仍需
确认实物 PCB 版本并导出该版本 pin-to-pin 网表，或做 MIO/U78 通断测量。
