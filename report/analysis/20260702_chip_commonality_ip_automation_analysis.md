# ET MCU 芯片共性、差异与自动化测试平台分析报告

时间：2026-07-02 19:02 CST

## 1. 结论摘要

当前本地 `code` 与 `SVN` 资料显示，ET 芯片资料不是一套空白体系，已经存在三类重要资产：

1. SDK 代码侧：`ET3101`、`ET6002`、`ET6003` 有结构相近的 SDK，均包含 `DFP/Drivers`、`DFP/Examples`、`DFP/Test`、`DFP/Project`、`Tools`、`Log`。
2. 软件测试资料侧：`ET3101`、`ET6001`、`ET6002`、`ET6003`、`ET6003EX`、`ET6801` 在 SVN `Software/` 下存在测试用例、FPGA 验证、回片验证等资料。
3. 硬件/样片测试侧：`ET3001`、`ET3101`、`ET3301`、`ET5601`、`ET6001`、`ET6002`、`ET6003`、`ET9001` 在 SVN `Hardware/` 下存在 datasheet、IO list、样片测试、FPGA、测试方案等资料。

自动化测试平台不应该绑定当前 SDK 的 `FunctionalTest` 或 `FPGA/TestCase` 实现，但这些现有代码和表格可以作为第一版 `IP contract`、`chip capability` 和 `testcase catalog` 的证据来源。

建议平台核心抽象为：

```text
IP Test Contract
  -> 稳定定义 IP feature/test semantic，例如 uart.loopback_internal
pytest Template
  -> 稳定测试模板，不出现具体芯片名
Chip Capability
  -> 每颗芯片声明有哪些 IP、instance、feature、限制、参数范围
Firmware Adapter
  -> 每颗芯片把统一命令适配到自身 SDK/register/BSP
Target Backend
  -> Renode / FPGA / HIL 只负责执行、观测、报告
```

核心原则：

```text
IP 新增功能：新增 contract feature + 芯片 capability + adapter，不改已有 pytest。
IP 减少功能：chip capability 标记 absent/unsupported，不删 pytest。
芯片 SDK 变化：只改 chip firmware adapter，不改 pytest。
板卡或仪器变化：只改 board/target capability，不改 pytest。
```

## 2. 分析范围与证据等级

本报告是本地仓库与资料库的结构化分析，不是完整芯片规格审计。

已检查根路径：

```text
源码库：/mnt/d/lihuan/vibe_code/code
资料库：/mnt/d/lihuan/vibe_code/SVN
工具库：/mnt/d/lihuan/vibe_code/ai_toolbox
```

证据等级：

| 等级 | 含义 |
|---|---|
| A | 有 SDK 源码、driver header、Examples、FunctionalTest 或 FPGA TestCase 证据。 |
| B | 有 SVN 软件测试用例表、FPGA 验证表、回片测试表证据。 |
| C | 有 SVN 硬件 datasheet、IO list、样片测试、测试方案目录证据。 |
| D | 仅发现目录名，尚未确认具体 IP/feature。 |

工具情况：

- `toolbox doctor` 和部分 `toolbox code/table` 通过 Windows bridge 调用时超过 60 秒无输出，已中止。
- `et_config_doctor.py` 在调用 document toolbox doctor 时卡住，已中止。
- `et_chip_query.py` 对 SDK 做查询时在递归扫描/路径解析阶段较慢，已中止。
- 本报告最终采用 `find`、`rg`、只读 `openpyxl` 和直接源文件抽样作为 fallback。

## 3. 芯片资产盘点

| 芯片/项目 | SDK 源码证据 | BootROM 源码证据 | SVN Software | SVN Hardware | 当前证据等级 |
|---|---:|---:|---:|---:|---|
| ET3001 | 未发现独立 SDK | 未发现 | 未发现 | datasheet/项目方案/原理图/IO list/样片测试 | C |
| ET3101 | `code/SDK/3101/et3101-sdk-main` | `code/boot_rom/bootrom-dev-et3101` | 设计文档、测试用例、FPGA 验证、Code | datasheet/项目方案/原理图/IO list/样片测试/数据手册 | A |
| ET3301 | 未发现独立 SDK | 未发现 | 未发现 | datasheet/项目方案/原理图/IO list/样片测试 | C |
| ET5601 | 未发现独立 SDK | 未发现 | FPGA 验证 | DATA/IOLIST/测试输入/SCH/PCB/测试数据 | B/C |
| ET6001 | 未发现独立 SDK 目录 | `code/boot_rom/et6001-bootrom-main` | 规范、设计、FPGA、测试用例、IP 资料、版本发布 | Design/IO/ATE/TEST/EVAL/自动化测试代码 | B/C |
| ET6002 | `code/SDK/6002/et6002-sdk-dev` | `code/boot_rom/et6002-bootrom-main` | 设计、测试用例、FPGA版本、版本发布、IP资料 | datasheet/FPGA/样片测试/软件代码 | A |
| ET6003 | `code/SDK/6003/et6003-sdk-dev_et6003`、`et6003-verification-function-test` | `code/boot_rom/bootrom-dev-et6003` | 项目计划、参考资料、测试用例、版本发布 | datasheet/项目方案/原理图/IO list/样片测试/数据手册 | A |
| ET6003EX | 未发现独立 SDK | 未发现 | FPGA 验证、回片测试、BootROM 测试表 | 未发现同名 Hardware 根目录 | B |
| ET6801 | 未发现 SDK | `code/boot_rom/bootrom-dev-et6801` | 设计、测试用例、FPGA版本、版本发布 | 未发现同名 Hardware 根目录 | B |
| ET9001 | 未发现 SDK | 未发现 | 未发现 | FPGA、Test-Solution | C |

备注：

- `Pegasus`、`XCVU13P` 更像项目/FPGA 平台或器件资料，不作为 ET MCU 芯片直接归类。
- `ET6003EX` 目前在 SVN Software 下有测试资料，但本轮未发现配套 SDK 源码根目录。

## 4. SDK 层共同点

`ET3101`、`ET6002`、`ET6003` 的 SDK 结构高度相似：

```text
DFP/Drivers/ET6x_Driver/Inc
DFP/Drivers/ET6x_Driver/Src
DFP/Examples/<IP>/<case>
DFP/Test/FunctionalTest
DFP/Test/TestFrame
DFP/Project
GCC
Tools
Log/<ip>
```

这说明平台可以抽象出稳定的 SDK 接入模式：

```text
chip_sdk_root
driver_include_root
driver_source_root
example_root
functional_test_root
test_frame_root
project_root
tool_root
```

但平台不应直接依赖具体路径写死。每颗芯片应该通过 `chip profile` 声明这些路径。

## 5. SDK Examples IP 对比

以下是从 `DFP/Examples/<IP>` 目录抽取的对比。

| IP | ET3101 | ET6002 | ET6003 | 判断 |
|---|---:|---:|---:|---|
| ACMP | 7 | 7 | 7 | 稳定，可抽象 |
| ADC | 13 | 13 | 13 | 稳定，但模拟精度测试需要仪器 |
| AES | 1 | 1 | 0 | 3101/6002 有，6003 release SDK 未见 |
| CAN | 6 | 6 | 6 | 稳定，但 CAN/CANFD 命名需分层 |
| CLB | 0 | 0 | 9 | 6003 新增/强化 |
| CORDIC | 2 | 2 | 3 | 基本稳定，6003 多 float sin |
| CPU | 2 | 2 | 2 | 稳定 |
| CRC | 1 | 1 | 1 | 稳定，适合全自动 |
| DAC | 2 | 2 | 0 | 3101/6002 有，6003 release SDK 未见 |
| DMA | 4 | 5 | 5 | 基本稳定，6002/6003 增 P2P |
| EQEP/QEP | EQEP 2 | EQEP 2 | QEP 2 | 功能近似，命名变化 |
| ETIMER | 5 | 5 | 5 | 稳定 |
| FLASH | 2 | 2 | 1 | 基本稳定，但介质/分区变化 |
| FMAC | 2 | 2 | 2 | 稳定 |
| FPU | 1 | 1 | 1 | 稳定 |
| GPIO | 1 | 1 | 1 | 稳定 |
| I2C | 1 | 1 | 1 | 稳定 |
| LAB_EXPERIMENT | 3 | 3 | 2 | 场景型，不宜作为核心 contract |
| LIN | 0 | 0 | 4 | 6003 新增/强化 |
| SDFM | 2 | 2 | 0 | 3101/6002 有，6003 release SDK 未见 |
| SPI | 1 | 1 | 1 | 稳定 |
| SRPWM | 12 | 13 | 12 | 稳定但 feature 很多，需要分 contract |
| STIMER | 3 | 3 | 3 | 稳定 |
| UART | 2 | 2 | 2 | 稳定 |
| WAG | 2 | 2 | 2 | 稳定 |
| WDG | 2 | 2 | 2 | 稳定 |
| XBAR | 4 | 4 | 4 | 稳定，但常与其它 IP 组合 |

从 Examples 看，跨 ET3101/ET6002/ET6003 共同存在的 IP：

```text
ACMP, ADC, CAN, CORDIC, CPU, CRC, DMA, ETIMER, FLASH, FMAC, FPU,
GPIO, I2C, LAB_EXPERIMENT, SPI, SRPWM, STIMER, UART, WAG, WDG, XBAR
```

只在 ET3101/ET6002 Examples 发现的 IP：

```text
AES, DAC, EQEP, SDFM
```

只在 ET6003 Examples 发现的 IP：

```text
CLB, LIN, QEP
```

注意：这只是 release SDK Examples 视角。`ET6003 verification-function-test` 里还出现了 `FDCAN`、`DAC`、`SDFM`、`EQEP`、`SRAM`、`Cortex-M7` 等 FPGA 验证用例。因此 report 中不能简单结论“ET6003 没有 DAC/SDFM/EQEP”，只能说“ET6003 release SDK Examples 未见，验证仓库/测试表仍有相关条目，需要芯片规格进一步确认”。

## 6. SVN 软件测试用例对比

`ET3101`、`ET6002`、`ET6003` 的 SVN 软件测试用例目录都采用 per-IP testcase xlsx 的形式。

共同出现于 ET3101/ET6002/ET6003 软件测试表的 IP：

```text
ADC, CAN, DAC, DMA, EQEP, ETIMER, FLASH, GPIO, I2C, SPI, SRPWM,
STIMER, SYSC, UART, WDG, XBAR
```

ET3101 测试表额外出现：

```text
ACMP, AES, CLB, CORDIC, CRC, FMAC, LIN, SDFM, WAG
```

ET6003 测试表额外出现：

```text
ACMP, CLB, CORDIC, CRC, CRG, FMAC, LIN, WAG
```

ET6002 本轮在 `04 测试用例/01 回片验证/02 测试用例` 下只见到共同集合中的一部分，这不代表芯片不支持其它 IP；因为 SDK Examples/Log 中仍有 ACMP、CORDIC、CRC、FMAC、WAG 等证据。

ET6003 单 IP 测试表规模示例：

| IP | 测试用例表行数（扣除表头） | 示例编号 |
|---|---:|---|
| ACMP | 77 | 1, 2, 3... |
| ADC | 57 | ADC_001... |
| CAN | 8 | CAN_TC_001... |
| CLB | 59 | 1, 2, 3... |
| CORDIC | 30 | 1, 2, 3... |
| CRC | 25 | 1, 2, 3... |
| DMA | 12 | DMA_TC_001... |
| ETIMER | 44 | ETIMER_001... |
| GPIO | 7 | GPIO_TC_001... |
| SRPWM | 105 | SRPWM_001... |
| UART | 5 | UART_TC_001... |
| WDG | 18 | WDG_001... |
| XBAR | 27 | XBAR-001... |

结论：SVN 测试表非常适合作为第一版 `IP Test Contract` 的来源，但要把测试表中的“测试步骤/预期结果”整理成稳定 feature id，而不是直接把 Excel 当运行时依赖。

## 7. FPGA 与验证仓库差异

`code/SDK/6003/et6003-verification-function-test` 提供了独立的 FPGA 验证结构：

```text
FPGA/TestCase/<IP>/*.c
FPGA/TestFrame
FPGA/Project
FPGA/FLM
```

发现的 FPGA TestCase IP：

```text
ACMP, ADC, ADDITION, AES, AHBDMA, BUS, CORDIC, CRC, Cortex-M7,
DAC, EQEP, ETIMER, FDCAN, FLASH, FMAC, GPIO, I2C, SDFM, SPI,
SRAM, SRPWM, STM, UART, WDG, XBAR
```

这说明 FPGA 验证不是 HIL 的简单子集，而是一个独立 target：

- FPGA 可能有真实数字 IO 和部分模拟接口，但时钟、Flash、模拟精度、低功耗、电源行为可能与样片不同。
- FPGA TestCase 中出现的 IP 与 release SDK Examples 不完全一致。
- 平台必须把 `target=fpga` 的 capability 独立配置，不能用 `target=real_chip` 或 `target=sdk_release` 推断。

## 8. 硬件/样片测试资料分类

以 ET6003 Hardware 样片测试资料为例，测试用例文件按物理测试类型划分：

```text
ETMCU-低速数字接口测试用例.xlsx
ETMCU-模拟测试用例.xlsx
ETMCU-功耗和热测试用例.xlsx
ETMCU-压力测试用例.xlsx
ETMCU-测试方案总结.xlsx
```

表内 sheet 体现了典型分类：

- 低速数字接口：`I2C`、`SPI`、`PMBUS`、`SMBUS`、`UART`。
- 模拟：`ADC`、`DAC`、`ACMP`、`PMU`、`CMU`、`DLL`。
- 功耗热：静态功耗、动态功耗、场景功耗、热测试。
- 压力：压力测试。

这类资料说明平台需要把自动化能力分级，而不是简单说某个 IP “可自动化/不可自动化”。

## 9. IP 复用性分级

### 9.1 高复用、低变化 IP

这些 IP 的测试语义相对稳定，适合作为平台第一批通用 contract：

| IP | 推荐 contract 粒度 | 自动化难度 |
|---|---|---|
| GPIO | output/readback、interrupt、pull、mux、drive strength | 中 |
| UART | internal loopback、external loopback、DMA、interrupt、baud range | 低到中 |
| SPI | master/slave、loopback、CPOL/CPHA、DMA、frequency | 中 |
| I2C | master transfer、addressing、ACK/NACK、interrupt/DMA | 中 |
| CRC | calculate、polynomial/init/xor、stream | 低 |
| WDG | feed、timeout halt/reset、window | 中 |
| STIMER | counter、interrupt、query time | 低 |
| ETIMER | base timer、input capture、PWM、fault | 中 |
| DMA/AHBDMA | M2M、M2P、P2M、P2P、LLI/scatter | 低到中 |
| FLASH | read、program、erase、verify、protection | 中，高风险 |
| XBAR | route source-to-sink、interrupt、trip path | 中 |

这些 IP 的 pytest 用例可以长期稳定。芯片差异主要进入：

```text
instances
pin mapping
supported features
limit/range
firmware adapter
board wiring
```

### 9.2 高复用但参数/观测差异大的 IP

| IP | 共同点 | 变化点 |
|---|---|---|
| ADC | virtual channel、trigger、DMA、watchdog、sampling result | 精度、触发源数量、模拟通道、校准、输入源、仪器 |
| DAC | output、DMA wave、trigger | 并非所有芯片/SDK 都出现，精度和输出路径依赖板卡 |
| ACMP | DAC input、window、filter、interrupt、PWM/XBAR 联动 | 阈值、电气、输入 mux、模拟观测 |
| SRPWM | output、dead-band、trip、blanking、shadow load、ADC sync | 高精度、保护路径、波形质量、外部测量 |
| CAN/FDCAN | init、Tx/Rx、FIFO/buffer、interrupt | CAN vs FDCAN、收发器、bit timing、总线拓扑 |
| SDFM | filter、sync/fifo、DMA read | 仅部分芯片/资料出现，依赖外部 sigma-delta 输入 |
| WAG | sine/triangle/static waveform | 波形质量和模拟输出依赖仪器 |

这些 IP 的测试 contract 可以统一，但必须拆成两层：

```text
functional contract：固件可自检，适合自动化
electrical contract：需要仪器，属于 HIL/instrument capability
```

### 9.3 明显芯片差异 IP

| IP/模块 | 观察到的差异 |
|---|---|
| CLB | ET6003 release SDK Examples 有 CLB，ET3101/ET6002 Examples 未见，但 ET3101/ET6003 测试表中出现。需规格确认。 |
| LIN | ET6003 release SDK Examples 有 LIN，ET3101/ET6003 测试表有 LIN，ET6002 本轮回片表未见。 |
| AES | ET3101/ET6002 Examples 有，ET6003 release SDK Examples 未见；ET6003 FPGA TestCase 有 AES。 |
| DAC | ET3101/ET6002 Examples 有，ET6003 release SDK Examples 未见；ET6003 测试表和 FPGA TestCase 有 DAC。 |
| EQEP/QEP | ET3101/ET6002 使用 EQEP 命名，ET6003 release SDK 使用 QEP，测试表仍出现 EQEP。应在 contract 层统一为 qep/encoder。 |
| CAN/FDCAN | release SDK 多用 CAN，ET6003 verification repo 出现 FDCAN。contract 应拆成 can.classic 与 can.fd。 |
| FLASH/EFC | ET6003 verification Examples 出现 EFC，release SDK Examples 为 FLASH/PFLASH。应抽象为 nonvolatile_memory。 |
| PTIMER/STIMER/STM | 不同资料中出现 PTIMER、STIMER、STM。应统一 timer family，再映射到芯片实现。 |
| HDMA/XDMA/AHBDMA | ET6001 测试表中出现 HDMA/XDMA，ET3101/6002/6003 SDK 中常见 AHBDMA/DMA。contract 应统一为 dma，implementation_type 由 chip capability 声明。 |
| PMBUS/SMBUS/PMU/CMU/DLL | 主要在硬件/样片测试资料中出现，偏系统/模拟/电源侧，不能作为纯 SDK IP 处理。 |

## 10. 哪些 IP 基本没有变过

从 SDK Examples、FunctionalTest、Log、SVN 测试表综合看，以下 IP 的测试语义最稳定：

```text
GPIO
UART
SPI
I2C
CRC
WDG
STIMER
ETIMER basic
DMA basic
FLASH basic
XBAR route
CPU/FPU basic
```

这些适合第一阶段沉淀为正式 `IP Test Contract`。

原因：

- 多颗芯片都有对应 driver/example/testcase 证据。
- 测试目标容易表达为稳定语义，如 loopback、interrupt、readback、transfer、timeout、calculate。
- 大部分可通过固件自检、串口日志、简单板级回环完成。

## 11. 哪些 IP 可以完全自动化

这里的“完全自动化”按是否需要人工观察、示波器手调、手动接线、长时间人工监控来判定。

### A 类：可优先全自动化，软件/固件自检为主

| IP/功能 | 自动化方式 |
|---|---|
| CRC | 固件计算并输出 PASS/FAIL。 |
| CORDIC | 固件计算固定输入/输出，允许误差阈值。 |
| FMAC | 固件跑 FIR/IIR golden vector。 |
| AES | 存在该 IP 的芯片可用 golden vector。 |
| CPU/FPU/CoreMark | 固件输出 score 或自检结果。 |
| SRAM/MarchC | 固件内存算法自检。 |
| DMA M2M | 内存 compare。 |
| UART internal loopback | 固件 loopback，自检 buffer。 |
| SPI internal/短回环 | 固件收发 compare，视板卡或内部 loopback 能力。 |
| I2C 基础收发 | 内部模拟或固定外设 fixture 可自动化。 |
| WDG halt 模式 | 可自动化，但 reset 模式需要复位观测。 |
| STIMER/ETIMER interrupt | 固件计数器/中断计数自检。 |
| GPIO 软件 readback | 只验证寄存器/内部读回，不代表外部电气。 |

### B 类：可自动化，但需要固定夹具/板卡连线/简单外设

| IP/功能 | 依赖 |
|---|---|
| UART external loopback | TX/RX 短接或继电器矩阵。 |
| CAN/CANFD | 收发器、终端电阻、总线 fixture。 |
| SPI master/slave | loopback、外部 flash、逻辑分析仪或第二节点。 |
| I2C EEPROM/传感器 | 固定 I2C 器件或仿真器。 |
| GPIO pin input/output | 回环线、DAQ、USB GPIO 或逻辑分析仪。 |
| XBAR route 到 PWM/GPIO/interrupt | 固定 board mux 和可观测点。 |
| FLASH program/erase/verify | 可自动化但需要破坏性操作 gate 和恢复路径。 |
| BootROM UART/CAN 下载 | 可自动化但涉及复位/boot pin/擦写时需 gate。 |

### C 类：可自动化，但必须接入仪器

| IP/功能 | 仪器 |
|---|---|
| ADC 精度/噪声/线性度 | 标准源、DMM、采集统计。 |
| DAC 输出精度/波形 | DMM/示波器。 |
| ACMP 阈值/迟滞/窗口 | 标准源/示波器。 |
| SRPWM 波形、死区、高精度、保护 | 示波器/逻辑分析仪。 |
| SDFM | sigma-delta 信号源或专用 fixture。 |
| WAG 波形质量 | 示波器。 |
| PMU/CMU/DLL | 电源、频率/时钟测量、示波器。 |
| 功耗/热测试 | 电源、电流计、热像/温度采集。 |

### D 类：不建议第一阶段追求完全自动化

| 类型 | 原因 |
|---|---|
| 长时间压力/老化 | 时间长，失败恢复复杂。 |
| 电气边界/ESD/EMC/SI/PI | 依赖实验环境和人工判读。 |
| 高风险 option/OTP/NVR/fuse/security | 破坏性强，需要人工 gate。 |
| 客户场景整机测试 | 外部系统复杂，先做半自动化记录。 |

## 12. 对统一架构的建议

### 12.1 平台不要复用 SDK 测试代码作为核心

现有 SDK 测试代码价值很高，但它是证据和迁移素材，不应成为平台核心。

原因：

- SDK 测试入口里存在手动注释/取消注释选择测试的模式。
- 不同仓库 release SDK、verification SDK、FPGA TestCase 内容不完全一致。
- 同一 IP 在不同芯片上命名不同，如 EQEP/QEP、CAN/FDCAN、FLASH/EFC、DMA/AHBDMA/HDMA/XDMA。

正确做法：

```text
从现有 SDK/TestCase/Excel 中抽取 IP contract
pytest 只依赖 contract
chip adapter 负责调用本芯片 SDK 或寄存器
```

### 12.2 第一版 IP Contract 应该从稳定 IP 开始

建议第一批：

```text
gpio
uart
spi
i2c
crc
wdg
stimer
etimer
dma
flash
xbar
```

第二批：

```text
adc
dac
acmp
srpwm
can/fdcan
cordic
fmac
aes
qep/eqep
sdfm
wag
```

第三批：

```text
pmu
cmu
dll
power
thermal
stress
bootrom/security/option/otp/nvr
```

### 12.3 Capability 需要分四层，而不是一张大表

```text
chip capability:
  芯片是否有这个 IP/feature/instance/参数范围。

board capability:
  板卡是否把引脚、回环、外设、测量点接出来。

target capability:
  Renode/FPGA/HIL 是否能执行和观测。

implementation capability:
  当前平台是否已经实现 pytest template、firmware adapter、backend adapter。
```

测试结果判定：

| 状态 | 含义 |
|---|---|
| PASS | 声明支持且验证通过。 |
| FAIL | 声明支持但验证失败。 |
| NA | 芯片/板卡本来不支持。 |
| XFAIL | target/backend 已知不能观测，例如 Renode 对真实电气。 |
| BLOCKED | 工具、固件 adapter、仪器、板卡条件缺失。 |
| CONFIG_FAIL | 规格/资料要求支持，但 capability 配置缺失或冲突。 |

### 12.4 Profile 最小字段建议

不要一开始做复杂大 schema，先做可维护的小 profile：

```yaml
chip: et6003
sdk_root: ...
ip:
  uart:
    instances: [uart0, uart1, uart2, uart3]
    features:
      internal_loopback: true
      external_loopback: true
      dma: true
      interrupt: true
    limits:
      baud_max: 2000000
  adc:
    instances: [adc0, adc1, adc2]
    features:
      single: true
      scan: true
      dma: true
      analog_accuracy: true
```

测试用例只引用：

```text
uart.internal_loopback
uart.dma
adc.single
adc.analog_accuracy
```

不要引用：

```text
ET6003 UART_FT_1
某个具体 SDK 函数名
某个 Excel 行号
```

## 13. 风险与未完成项

1. 本报告未深读寄存器手册、SVD/PDSC、datasheet 正文，因此不能作为最终 IP 存在性裁决。
2. `ET3001`、`ET3301`、`ET5601`、`ET9001` 当前主要是硬件/SVN 目录证据，缺少 SDK 源码层分析。
3. `ET6001` 本轮未找到独立 SDK 根目录，但 SVN 测试用例和 BootROM 代码较多，需要单独补充。
4. `ET6003 release SDK` 与 `ET6003 verification-function-test` 的 IP 覆盖不完全一致，需要后续建立“release SDK profile”和“FPGA verification profile”两个视角。
5. ET AI skill 和 toolbox 当前在 WSL/bridge 路径下存在超时和路径解析问题，建议先修工具链配置，否则后续大规模文档索引会很慢。

## 14. 下一步建议

建议按以下顺序落地：

1. 建立 `IP Contract Catalog v0.1`，先覆盖 GPIO/UART/SPI/I2C/CRC/WDG/STIMER/ETIMER/DMA/FLASH/XBAR。
2. 从 `ET3101`、`ET6002`、`ET6003` 的 Examples 和 SVN 测试表抽取每个 IP 的 feature id。
3. 为 ET3101/ET6002/ET6003 建最小 chip capability profile，只写 IP/instance/feature，不写复杂仪器。
4. 固件侧定义统一 command/result 协议，但 adapter 调用各芯片自己的 SDK。
5. pytest 先只实现 2-3 个稳定 IP 的模板，例如 CRC、UART internal loopback、GPIO readback。
6. 再把 target capability 拆成 `renode`、`fpga`、`hil`，避免一开始把所有仪器自动化都做进去。

最终目标：

```text
新增芯片：新增 chip profile + firmware adapter。
新增 IP feature：新增 contract + 对应芯片 capability。
已有 pytest 用例不因芯片变化而重写。
```

