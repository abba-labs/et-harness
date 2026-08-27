# 外部仪器 API 覆盖度复核

文档状态：软件命令契约冻结；真实硬件验证未执行。

## 1. 统计口径

覆盖度按厂家 Programming Guide/Programming Manual 中公开的稳定远程控制语义统计：

1. Set 与 Query 是不同原子 API；
2. 同一语义的 SCPI 长名/短名、可选关键字和等价拼写不重复计数；
3. `MIN/MAX/DEF` 等参数形式由参数模型表达，不额外制造 API；
4. 通用 raw write/query 不计入覆盖率；
5. Option 命令仍进入软件 API，但不代表目标实机已经安装该 Option；
6. 软件命令契约覆盖与 HIL 硬件验证分开记录。

## 2. 最终软件 API 覆盖总表

| 仪器 | 规范化远程控制语义 | 当前状态 | 软件 API 覆盖 | HIL |
|---|---:|---|---:|---|
| RIGOL DP711 | 108 | 完成 | **108 / 108 = 100%** | NOT_EXECUTED |
| B&K Precision 9130B | 136 个正文明确语义 | 完成 | **136 / 136 = 100%** | NOT_EXECUTED |
| RIGOL DM3068 | Common + RIGOL 原生 183 | 完成 | **183 / 183 = 100%** | NOT_EXECUTED |
| RIGOL MSO5204 | 997 | 完成 | **997 / 997 = 100%** | NOT_EXECUTED |

这里的 100% 仅表示已冻结范围内的**软件远程控制契约覆盖**，不表示真实仪器行为已经验证。

## 3. MSO5204 最终 997 个原子 API

资料基线：

```text
MSO5000 Programming Guide
May. 2025
Publication Number: PGA25105-1110
Software Version: 00.01.02.SP5
```

Programming Guide 的 Chapter 2 命令族已经全部逐组核对并进入 Typed/Named API。最终分布：

| 模块 | API 数 | 状态 |
|---|---:|---|
| basic | 6 | 完成 |
| common | 15 | 完成 |
| acquire | 11 | 完成 |
| bodeplot | 28 | 完成 |
| bus | 126 | 完成 |
| channel | 22 | 完成 |
| counter | 12 | 完成 |
| cursor | 56 | 完成 |
| display | 16 | 完成 |
| dvm | 7 | 完成 |
| histogram | 19 | 完成 |
| logic_analyzer | 23 | 完成 |
| lan | 25 | 完成 |
| mask | 17 | 完成 |
| math | 65 | 完成 |
| measurement | 38 | 完成 |
| power | 16 | 完成 |
| quick | 2 | 完成 |
| record | 10 | 完成 |
| reference | 17 | 完成 |
| save_load | 16 | 完成 |
| search | 54 | 完成 |
| source | 54 | 完成 |
| system | 32 | 完成 |
| timebase | 18 | 完成 |
| trace | 1 | 完成 |
| trigger | 17 | 完成 |
| trigger_advanced | 134 | 完成 |
| trigger_protocol | 120 | 完成 |
| waveform | 20 | 完成 |
| **合计** | **997** | **100% 软件命令契约覆盖** |

## 4. 最后一批收尾能力

本批新增：

```text
BODeplot   28
LAN        25
POWer      16
QUICk       2
TRACe       1
----------------
合计       72
```

### BODeplot

覆盖 Enable、Display Type、Source、Sweep Type、Input/Output Reference、Impedance、Start/Stop Frequency、Point、Voltage/Profile、Gain Margin 和 Phase Margin。

### LAN

覆盖 DHCP、AutoIP、Static IP、Gateway、DNS、MAC、DHCP Server、IP、Subnet Mask、Status、VISA Address、mDNS、Host Name、Description 与 Apply。

### POWer

覆盖 Power Analysis Type、Current/Voltage Source、Power Quality Frequency Reference、Reference Level Method 和 High/Low/Mid Percentage。

### QUICk

覆盖前面板快捷键 Operation 类型设置与查询。

### TRACe

覆盖 `TRACe<n>:DATA:DAC16` 任意波形二进制下载；每点 2 Bytes，数据块长度 4 Bytes~32 kBytes，并使用公共 IEEE488.2 definite-length block 写入。

## 5. 完整命令族复核

MSO5000 Programming Guide Chapter 2 的命令族均已对应到 Driver：

```text
Top-level actions
ACQuire
BODeplot
BUS<n>
CHANnel<n>
COUNter
CURSor
DISPlay
DVM
HISTogram
IEEE488.2 Common
LA
LAN
MASK
MATH<n>
MEASure
POWer
QUICk
RECord
REFerence
SAVE / LOAD
SEARch
SOURce<n>
SYSTem
TIMebase
TRACe<n>
TRIGger
WAVeform
```

协议 Trigger 和 BUS Decode 的下级命令已经分别由 `trigger_protocol`、`trigger_advanced` 和 `bus` 覆盖，不再重复建立另一套 API。

## 6. 验证边界

当前已执行的软件验证用于检查：

- Python 语法、Ruff 与仓库架构规则；
- 原子 API -> SCPI 命令字符串/参数顺序；
- 数值、布尔、枚举文本和二进制 block；
- 非法参数在写入 Transport 前拒绝；
- 各批 API Inventory 数量；
- Driver 与 Operations 分层边界。

真实硬件仍保持：

```text
HIL = NOT_EXECUTED
```

因此最终结论是：**四台仪器的软件控制 API 已全部完成；下一阶段若继续开发，应转入组合 Operations、Test Case 接入和后续 HIL，而不是继续补基础 Driver 命令。**
