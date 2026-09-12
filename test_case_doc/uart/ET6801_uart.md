# ET6801 UART Chip Analysis & Adaptation Contract

> 本文件只记录 ET6801 UART 的 Hardware / SDK Driver / Register / Historical Evidence，以及该芯片到公共 UART Feature/Case Contract 的映射。
> 公共 Feature / Case / `ET_CASE_SPEC` 真值位于 [`uart.md`](uart.md)；本文件不得重新定义公共 Case 方法、Oracle 或报告语义。
> Hardware Support、Platform Adaptation 与真实 HIL Result 必须分开记录。

## 第一章 IP分析

### 1.1 IP资源

ET6801具有8个UART实例。UART0～UART7寄存器结构一致，每个实例有独立基地址和独立中断向量。

| 实例 | 普通基地址 | ACC别名地址 | IRQn | 当前板级可见路径 |
|---|---:|---:|---:|---|
| UART0 | `0x40500000` | `0x40580000` | 24 | GPIO12/13，经J27选择到J28串口；当前作为PC控制通道 |
| UART1 | `0x40501000` | `0x40581000` | 25 | GPIO44/45，J25.5 TX、J25.3 RX |
| UART2 | `0x40502000` | `0x40582000` | 26 | GPIO8/9，J30.5 TX、J30.3 RX |
| UART3 | `0x40503000` | `0x40583000` | 27 | GPIO10/11，J29.5 TX、J29.3 RX |
| UART4 | `0x40504000` | `0x40584000` | 28 | 当前核心板接口文档未给出固定UART外部路径 |
| UART5 | `0x40505000` | `0x40585000` | 29 | 当前核心板接口文档未给出固定UART外部路径 |
| UART6 | `0x40506000` | `0x40586000` | 30 | 当前核心板接口文档未给出固定UART外部路径 |
| UART7 | `0x40507000` | `0x40587000` | 31 | 当前核心板接口文档未给出固定UART外部路径 |

SVD和CMSIS证明硬件有8个实例，但当前正式Driver的`IS_UART_INSTANCE`只接受UART0～UART3，当前平台`ET_CHIP_UART_MAP_TABLE`只映射UART0～UART2。因此“硬件实例存在”“SDK Driver支持”和“平台当前可调用”必须分别记录，不能混为一个PASS。

### 1.2 工作原理

UART把并行数据转换为异步串行帧发送，并把RX输入上的串行帧恢复为并行数据。普通帧由起始位、5～9位数据、可选奇偶校验和停止位组成。发送与接收使用独立状态机和16深度FIFO，可同时进行全双工通信。

基础数据链路为：

```text
CPU或DMA写THR/TX FIFO
  → 波特率发生器和TX移位器
  → TX引脚
  → 对端RX引脚
  → RX采样、帧校验和RX FIFO
  → CPU或DMA读RBR
```

UART时钟经过整数分频`DLL/DLH`和小数分频`DLF`生成位时钟。两端只有在波特率、数据位、停止位和校验方式兼容时才能稳定收发。

### 1.3 工作模式

| 模式 | 主要机制 | 数字验证方式 |
|---|---|---|
| Normal | 普通异步全双工串口 | 内部loopback或UART1↔UART2交叉短接 |
| Loopback | TX在模块内部回送到RX，同时支持部分modem/flow-control自测 | 单实例片内闭环 |
| 9-bit | 第9位区分地址与数据，支持软/硬件发送及地址匹配接收 | 两个UART实例对测 |
| DMA | UART产生TX/RX DMA请求，支持single/multi模式 | UART1↔UART2 + DMA |
| Hardware Flow Control | CTS限制发送，RTS反压对端 | 需要RTS/CTS交叉连接 |
| RS485 | 支持全双工、软件半双工、硬件半双工以及DE/RE控制 | 需要RS485数字控制路径和收发器/连线 |
| IrDA SIR | 普通SIR和固定115200的低功耗SIR | 需要SIR收发路径或专用数字模型 |

### 1.4 FIFO、状态和中断

UART TX和RX FIFO深度均为16。可配置TX阈值0/2/4/8字节，RX阈值1/4/8/14字节。硬件提供FIFO复位、FIFO计数、忙状态、TX非满/空、RX非空/满等状态。

UART0～UART7各有一个物理IRQ，中断源在实例内部汇总，由`IIR.IID`给出当前最高优先级中断：

| 中断源 | 驱动标志 | 清除或结束条件 |
|---|---|---|
| Modem status | `UART_IT_MODEM_STATUS_FLAG` | 读取MSR |
| TX holding/FIFO empty | `UART_IT_TRANS_DATA_EMPTY_FLAG` | 读取IIR或继续写TX数据，具体行为受THRE模式影响 |
| RX data available | `UART_IT_RECV_DATA_AVAILABLE_FLAG` | 读取RBR直到低于阈值/为空 |
| RX line error | `UART_IT_ERROR_FLAG` | 读取LSR和对应RBR数据 |
| Busy detect | `UART_IT_UART_NOFIFO_BUSY` | 读取USR |
| Character timeout | `UART_IT_CHAR_TIMEOUT_FLAG` | 读取RX FIFO数据 |
| 9-bit address received | `UART_IT_9BITS_ADDR_RESV_FLAG` | 读取LSR/RBR |

ISR只负责读取中断来源、搬运必要的小量数据、更新计数/状态并清除硬件条件；数据比对、超时判定、协议响应和下一步调度必须在Service主流程完成。

### 1.5 当前板级连接

当前已确认的UART测试连接为：

```text
UART1_RX  J25.3 ← J30.5  UART2_TX
UART1_TX  J25.5 → J30.3  UART2_RX
GND              ↔       GND
```

该连接可以完成UART1与UART2的双向数字通信、帧格式、错误注入、9-bit、DMA和长稳测试。当前UART0经J28与PC通信，必须保持115200 8N1控制链路，不作为被测实例。

当前测试角色固定为逻辑角色而不是固定实例名：

| 逻辑角色 | 当前bench映射 | 职责 |
|---|---|---|
| Control | UART0 | PC与固件ET-Frame控制通道，不参与UART功能Case |
| DUT | UART1 | 唯一被测UART实例，所有Feature覆盖结果归属于该handle |
| Peer | UART2 | 只产生输入刺激或接收DUT输出，不计为第二份UART Feature覆盖 |

将来更换芯片、板卡或接线时只修改bench profile中的DUT/Peer映射，UART Case源码保持不变。

| UART | 3.3V TTL测试端 | 板载RS232路径 | 当前用途 |
|---|---|---|---|
| UART0 | J27 | U55 → J28 DB9 | J28连接PC，作为控制通道 |
| UART1 | J25 | U53 → J26 DB9 | J25与UART2交叉短接 |
| UART2 | J30 | U57 → J32 DB9 | J30与UART1交叉短接 |
| UART3 | J29 | U56 → J31 DB9 | 已引出，但当前未接入Wrap和bench pair |

核心板接口资料还表明：

- UART0和UART1对应带流控串口路径，但当前仅确认TX/RX数据线，未确认RTS/CTS/DTR/DSR等已交叉连接。
- UART2和UART3对应不带流控串口路径。
- 接口文档中的1.8V描述是XC7VX980T/ET6801侧数字电源域；UART0～3经过TXS0108E到J27/J25/J30/J29的3.3V TTL端，并可继续经过MAX3232到DB9 RS232端。TTL端可接3.3V数字配测设备，DB9 RS232端不能直接接普通TTL或XC7Z045 IO。测试Case只引用board profile中的逻辑端点，不在Case中写死接插件或电平事实。
- RS485和IrDA需要不同于普通RS232/TTL UART的物理收发路径，不能因为普通TX/RX已接通就判定这些模式可测。

### 1.6 典型应用

- BootROM、固件日志和PC控制协议。
- MCU与传感器、模块、另一颗MCU之间的低速/中速异步通信。
- 中断或DMA驱动的持续数据流。
- 9-bit多机地址通信。
- 带RTS/CTS的硬件流控通信。
- 通过外部收发器实现RS232、RS485或IrDA链路。

## 第二章 IP驱动分析

### 2.1 驱动文件和定位

| 文件 | 定位 |
|---|---|
| `et6x_uart.h` | UART枚举、配置结构、状态/中断标志和公共API |
| `et6x_uart.c` | 波特率、帧格式、FIFO收发、中断、9-bit、流控、DMA、SIR、RS485实现 |
| `et6801.h` | UART寄存器结构、8个实例、普通/ACC地址及IRQ定义 |
| `startup_et6801.s` | UART0～UART7弱中断入口 |

### 2.2 驱动配置结构

`UART_ConfigParams`统一描述：

| 配置项 | 取值 |
|---|---|
| `baudRate` | 大于0且不超过3,000,000 |
| `wordLength` | 5、6、7、8 bit |
| `stopBits` | 1；5-bit时1.5；其他字长时2 |
| `parity` | none、even、odd、stick 0、stick 1 |
| `mode` | normal、SIR、low-power SIR、RS485、9-bit、loopback |
| `DMAMode` | disable、single、multi |
| `irqEnableFlag` | RX、TX、modem、timeout、9-bit address、error、programmable THRE |
| `hwFlowCtl` | disable、enable |
| `TXFIFOThreshold` | 0、2、4、8 bytes |
| `RXFIFOThreshold` | 1、4、8、14 bytes |
| `advancedInit` | RS485配置或9-bit配置 |

默认配置是9600、8N1、normal、DMA关闭、IRQ关闭、硬件流控关闭、TX阈值8、RX阈值1。

### 2.3 驱动API

| API组 | 主要API | 能力 |
|---|---|---|
| 基础 | `UART_initConfigParams`、`UART_config`、`UART_performSoftwareReset` | 默认配置、完整初始化、软件复位 |
| 波特率/帧 | `UART_setBaudrate`、`UART_setLineConfig` | 整数/小数分频、数据位、停止位、校验 |
| 收发 | `UART_transmit`、`UART_receive`、`UART_waitTransmitDone` | FIFO阻塞/非阻塞发送、FIFO接收、完成超时 |
| FIFO状态 | `UART_getRxFIFOStatus`、`UART_getTxFIFOStatus` | RX/TX FIFO计数 |
| 9-bit | `UART_config9BitMode`、`UART_triggerAddressSend`、`UART_setTransferAddress`、`UART_setReceiveAddress` | 9-bit软/硬件地址与数据传输 |
| 中断 | `UART_enableInterrupt`、`UART_disableInterrupt`、`UART_getInterruptStatus`、`UART_clearInterruptStatus` | 中断mask、识别和清除 |
| 状态 | `UART_getLineStatusFlag` | DR/OE/PE/FE/BI/THRE/TEMT/RFE/address状态 |
| 流控 | `UART_enableHWFlowMode`、`UART_disableHWFlowMode`、`UART_setRTSSign`、`UART_setDTRSign` | 自动流控和modem输出 |
| DMA | `UART_configDMA` | FIFO使能、阈值和single/multi DMA模式 |
| SIR | `UART_enableSIRMode`、`UART_disableSIRMode`、`UART_configSIRLowPowerMode` | 普通/低功耗SIR |
| RS485 | `UART_RS485_config`及DE/RE、TAT、DET、mode API | RS485模式、极性和时序 |
| 其他 | `UART_sendBreak`、`UART_haltTransmission`、`UART_resumeTransmission` | Break、暂停和恢复发送 |

### 2.4 驱动关键行为

- `UART_config`先软件复位，再按mode配置9-bit/SIR/flow-control、波特率、帧格式、DMA/FIFO、loopback、RS485和IRQ。
- `UART_configDMA`无论DMA是否启用都会使能并复位TX/RX FIFO，因此当前完整配置路径默认工作在FIFO模式。
- `UART_getInterruptStatus`只返回当前最高优先级中断，Service必须循环处理，直到返回`UART_IT_NONE`。
- RX available和character timeout不能仅靠读IIR清除，必须读取RBR/FIFO。
- 阻塞发送有驱动内部有限等待，非阻塞发送在FIFO满时返回实际写入数量。
- FPGA构建下驱动把UART输入时钟固定为25MHz；硅后构建通过`CRG_getAPB3Clock()`获取时钟。波特率Case必须记录lane和实际输入时钟。
- ET6801 Chip Config 使用 `UART_BAUDRATE_MAX`、`UINT16_MAX`、`GPIOx`/Mux 与 `UARTx_IRQn` 等 SDK/CMSIS 符号发布当前 UART0～UART2 映射；`1200` 最小波特率来自稳定 Common Wrap 契约。

### 2.5 当前Driver和Wrap缺口

| 缺口 | 影响 | 处理原则 |
|---|---|---|
| Driver实例检查只接受UART0～UART3 | UART4～UART7硬件存在但无法通过正式API配置 | 在Driver测试扩展区补齐实例支持，经审核后Wrap参数化 |
| 当前Wrap只映射UART0～UART2 | UART3～UART7无法由Service访问 | 后续从capability/芯片映射补齐，不复制Case |
| 当前Wrap只暴露none/even/odd | stick parity无法从公共接口配置 | 扩展稳定枚举，保持芯片SDK类型不外泄 |
| 当前Wrap capability未申报flow-control和break | PC会错误判定能力缺失 | 完成对应接口后由实际映射申报 |
| Driver没有公开FIFO disable、独立FIFO reset、shadow/direct FIFO接口 | 非FIFO和部分寄存器Feature无法按分层规则测试 | 如Feature必须测，在Driver文件底部“test add driver”区域增加测试API，Wrap只调用Driver |
| Driver没有公开component ID、version、CPR、SCR、PROT_LEVEL | 能力识别和保护配置缺少接口 | 仅为测试所需时增加受审测试Driver，Wrap不得直接操作寄存器 |
| `UART_setLineConfig`采用读取原LCR后按位OR新配置 | 从一种校验/停止位切换到另一种时，旧位可能残留 | 必须增加重配置Case；若证实失败，在Driver正式区修复或测试扩展区提供明确设置API |
| 当前自动生成`uart.yaml`只识别实例、IRQ、地址、ID/version和RS485 | SVD中的FIFO、9-bit、SIR、flow-control等尚不能被上游完整查询 | 补充通用SVD语义规则后重新生成，不在Case中硬编码ET6801事实 |
| UART API参考和部分旧测试仍使用旧接口/旧GPIO | 不能直接编译复用 | 以当前SVD、Driver和board profile为准 |

Wrap必须继续遵守平台规则：一个UART Wrap只能调用UART Driver；GPIO复用、CRG、NVIC和DMA分别由GPIO/CRG/IRQ/DMA Service通过各自Wrap执行。UART Service只解析UART命令、调用UART Wrap并返回结构化结果，不固化完整Case流程。

## 第三章 IP寄存器分析

### 3.1 基础收发和配置寄存器

| 寄存器 | 作用 | 对应Feature |
|---|---|---|
| `RBR/THR` | 接收/发送数据 | 普通、9-bit、FIFO、DMA收发 |
| `DLL/DLH/DLF` | 整数和小数波特率分频 | 波特率范围和精度 |
| `LCR` | DLAB、break、stick/even/odd parity、stop、5～8 bit | 帧格式和break |
| `MCR` | SIR、自动流控、loopback、RTS/DTR | loopback、SIR、flow-control、modem输出 |
| `SCR` | 8-bit scratch | 寄存器可写性/实例隔离辅助检查 |

### 3.2 FIFO、状态和中断寄存器

| 寄存器 | 作用 | 对应Feature |
|---|---|---|
| `IER` | 各类中断使能、programmable THRE | 中断mask |
| `IIR` | 最高优先级中断ID、FIFO使能状态 | 中断识别 |
| `FCR` | FIFO使能、TX/RX reset、DMA mode、TX/RX阈值 | FIFO和DMA |
| `LSR` | data ready、overrun、parity、frame、break、TX empty、RX FIFO error、9-bit address | 错误和线状态 |
| `MSR` | CTS/DSR/RI/DCD当前值及delta | modem status |
| `USR` | busy、TX not full/empty、RX not empty/full | 运行状态 |
| `TFL/RFL` | TX/RX FIFO当前数据量 | FIFO计数和边界 |
| `SRR` | UART、RX FIFO、TX FIFO软件复位 | 恢复和隔离 |
| `SRTS/SBCR/SDMAM/SFE/SRT/STET` | shadow控制寄存器 | 无DLAB/多功能别名影响的安全配置 |
| `HTX` | halt TX | 暂停/恢复 |
| `DMASA` | DMA software acknowledge | DMA握手辅助 |

### 3.3 9-bit、RS485和扩展寄存器

| 寄存器 | 作用 | 对应Feature |
|---|---|---|
| `LCR_EXT` | 9-bit使能、地址匹配、发送地址、软/硬件发送模式 | 9-bit |
| `RAR/TAR` | 接收匹配地址、发送地址 | 9-bit地址 |
| `TCR` | RS485使能、模式、DE/RE极性 | RS485 |
| `DE_EN/RE_EN` | DE/RE手动控制 | RS485方向控制 |
| `DET` | DE assertion/deassertion时间 | RS485 DE时序 |
| `TAT` | DE→RE、RE→DE turnaround时间 | RS485转换时序 |
| `LPDLL/LPDLH` | 低功耗SIR分频 | low-power SIR |

### 3.4 能力、调试和保护寄存器

| 寄存器 | 作用 | 测试处理 |
|---|---|---|
| `CPR` | FIFO mode、DMA extra、shadow、FIFO status/access、SIR、THRE、AFCE、APB宽度等硬件能力 | P0读取并与capability YAML核对 |
| `UCV` | UART component version | P0身份检查 |
| `CTR` | peripheral/component ID | P0身份检查 |
| `FAR/TFR/RFW` | FIFO direct access和带错误位的数据写入 | 设计确认后测试，不能当普通数据API |
| `PROT_LEVEL` | UART访问保护级别 | 需要权限模型和安全恢复方案 |
| `REG_TIMEOUT_RST` | 寄存器访问timeout reset | 需要RTL/总线契约后测试 |

SVD把`RBR/THR/SRBR/STHR`数据字段定义为16 bit：普通UART路径使用低8 bit，9-bit软件收发必须使用`uint16_t`元素并按元素计数。SVD还把部分状态寄存器标为`read-write`，但字段描述体现为只读状态；测试不得依据宽泛access属性写状态寄存器，应以字段语义和Driver行为为准。

### 3.5 寄存器与驱动映射结论

- 普通收发、波特率、帧格式、FIFO、常用中断、9-bit、DMA、flow-control、SIR和RS485已有Driver API。
- component capability、SCR、FIFO直接访问、保护和timeout reset尚无公共Driver API。
- 当前自动化平台禁止UART Wrap直接访问上述寄存器。确需测试时，必须先在UART Driver底部受控测试扩展区增加命名清晰的测试API，再由UART Wrap封装。
- `CPR`声明的能力必须优先于“头文件存在某个位”；CPR未启用的能力按`skip_by_capability`处理，不能强行执行。


### 3.6 公共稳定 Observation -> ET6801 实际端点映射

> 本表只用于 Canonical Result / ET_CASE_REPORT / Excel 的只读显示增强。公共 Case 继续保存跨芯片稳定 endpoint；目标芯片寄存器名不得反向进入公共 Case/Driver。

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `UART_COMPONENT.COMPONENT_PARAMETER` | `CPR` | 组件能力参数原始值 |
| `UART_COMPONENT.COMPONENT_VERSION` | `UCV` | UART component version |
| `UART_COMPONENT.PERIPHERAL_ID` | `CTR` | peripheral/component identity |
| `UART_COMPONENT.SCRATCH` | `SCR` | Scratch当前读值；不等于完整读写证明 |
| `UART_STATUS.LINE_STATUS` | `LSR` | DR/OE/PE/FE/BI/THRE/TEMT/RFE/ADDR_RCVD线状态 |
| `UART_STATUS.ERROR_FLAGS` | `LSR.OE/PE/FE/BI/RFE` | 归一化Parity/Framing/Overrun/Break/RX-FIFO Error |
| `UART_STATUS.STATE_FLAGS` | `USR.BUSY/TFNF/TFE/RFNE/RFF` | UART运行状态 |
| `UART_STATUS.FIFO_FLAGS` | `USR.TFNF/TFE/RFNE/RFF` | FIFO空/满/非空/非满状态 |
| `UART_FIFO.TX_LEVEL` | `TFL` | TX FIFO当前Level |
| `UART_FIFO.RX_LEVEL` | `RFL` | RX FIFO当前Level |
| `UART_CAPTURE.DATA` | `RBR -> Firmware Capture Buffer` | DUT接收数据端点；报告可显示数据路径，不把Buffer冒充一个寄存器值 |
| `UART_9BIT.DATA` | `RBR/THR + 9-bit mode` | 9-bit收发数据语义 |
| `UART_MODEM.INPUT_FLAGS` | `MSR.CTS/DSR/RI/DCD` | Modem当前输入 |
| `UART_MODEM.DELTA_FLAGS` | `MSR.DCTS/DDSR/TERI/DDCD` | Modem变化/read-to-clear状态 |
| `UART_MODEM.OUTPUT_FLAGS` | `MCR.RTS/DTR` | Modem输出控制 |
| `UART_MODEM.RAW_STATUS` | `MSR` | Modem原始状态快照 |
| `UART_SHADOW.ENABLED` | `SFE` | Shadow FIFO enable readback |
| `UART_SHADOW.TX_THRESHOLD` | `STET` | Shadow TX empty threshold readback |
| `UART_SHADOW.RX_THRESHOLD` | `SRT` | Shadow RX trigger readback |
| `UART_FIFO_ACCESS.ENABLED` | `FAR` | FIFO access mode |
| `UART_FIFO_ACCESS.TX_VALUE` | `TFR` | Direct TX FIFO read |
| `UART_FIFO_ACCESS.RX_VALUE` | `RFW` | Direct RX FIFO write/readback data path |
| `UART_BUSY.PRE_TRIGGER_USR` | `USR` | Busy Detect刺激前UART状态 |
| `UART_BUSY.OBSERVED_IIR` | `IIR.IID` | Busy Detect中断识别原始事实 |
| `UART_BUSY.OBSERVED_USR` | `USR` | Busy Detect观察/clear序列中的UART状态 |

以下 Canonical endpoint / Measurement **不映射成 UART 寄存器**：

- `UART_CAPABILITIES.*`：来自 Chip Mapping / Wrap / Service 的运行时能力声明，是Capability/配置事实，不冒充某个UART寄存器读回。
- `UART_ISR.ENABLED_MASK / PENDING_MASK / ACTIVE_MASK`：UART Firmware Service IRQ session/latch事实；它们用于证明Service delivery/source ownership，不等同于某一个当前硬件IIR/IER寄存器快照。
- `event_count / fault_count / overflow_count / source_observed`：Service/Measurement。
- `PEER_UART.RX_CAPTURE`：Peer设备事实。
- `DMA_CHANNEL_STATUS.* / DMA_DESTINATION_DATA`：DMA执行域事实。
- `data_match / guards_intact / transferred / received / round_count`：软件Measurement。

映射缺失时报告必须保留公共稳定 endpoint，不得猜测目标寄存器名称。

## 第四章 当前测试代码分析

### 4.1 历史测试位置和实际入口

| 代码 | 主要内容 | 当前入口状态 |
|---|---|---|
| `FunctionalTest/uart_ft.c::UART_FT_1` | UART1 loopback，FIFO/非FIFO各1024字节 | 在`UART_FTest`中被注释 |
| `FunctionalTest/uart_ft.c::UART_FT_2` | UART1 loopback + DMA TX/RX | 在`UART_FTest`中被注释 |
| `FunctionalTest/uart_ft.c::UART_FT_3` | UART1 RX available IRQ，16字节比对 | 当前功能测试只调用这一项 |
| `FPGATest/uart_fpga_test.c::UART_1` | loopback + DMA RX | UART FPGA总入口未默认启用 |
| `FPGATest/uart_fpga_test.c::UART_2` | 普通TX/RX轮询 | 依赖外部回送，无超时 |
| `FPGATest/uart_fpga_test.c::UART_3` | DMA TX | 只发送，不自动判定接收 |

因此，历史代码不能证明UART完整功能已经覆盖。

### 4.2 历史功能测试分析

`UART_FT_1`把loopback、FIFO、非FIFO、1024字节和固定1ms延时组合在一个Case中。其可借鉴点是使用已知递增数据并完整比对；问题是无法快速定位是FIFO、非FIFO还是长度边界失败。

`UART_FT_2`组合UART、DMAMUX、AHBDMA、两个DMA中断和loopback。DMA ISR中的判定是恒真的`SUCCESS == SUCCESS`，没有等待真实完成，只固定延时200ms后比对。这一测试思想应拆成独立的UART DMA TX、DMA RX和双向集成Case。

`UART_FT_3`验证RX available IRQ，但ISR中的静态`rx_cnt`不复位、没有边界保护和超时，重复执行可能错位或越界。新框架必须由资源上下文保存计数并在Case cleanup中复位。

### 4.3 历史FPGA测试分析

- `UART_1`可借鉴“DMA RX + loopback + 数据比对”，但直接清MCR寄存器且不验证DMA完成状态。
- `UART_2`依赖外部回送并使用无限`while(1)`等待8字节，断线时会永久挂死。
- `UART_3`只启动DMA TX并固定等待100us，没有接收端证据，不能形成自动PASS。
- UART FPGA测试入口在总FPGA测试文件中仍被注释，不能计为已执行覆盖。

### 4.4 示例代码分析

`UART_init_TxRx`展示了GPIO复用、UART0日志、UART1 FIFO收发流程；`UART_IT_receive`展示了IIR中断分派、环形缓冲和RX→TX中断回显。示例可借鉴初始化顺序和ISR最小搬运思想，但只打印结果、永久循环，且README中的GPIO与源码存在版本差异。

板级管脚必须来自当前board profile，不能从旧示例复制。

### 4.5 历史代码可借鉴与禁止沿用的内容

可借鉴：

- 已知pattern发送后逐字节或CRC+首错位置比对。
- 内部loopback优先验证UART核心，不依赖外部连线。
- RX/TX中断分别统计触发次数和实际搬运量。
- DMA TX、DMA RX分方向验证。

禁止沿用：

- 无限轮询、固定延时替代完成事件。
- ISR中执行大块比对、协议发送或恒真断言。
- 直接操作UART、GPIO、DMA或NVIC寄存器绕过Driver/Wrap。
- 把UART0控制通道同时作为DUT测试实例。
- 把多个不同机制组合成一个无法定位失败原因的大Case。
- 仅凭“发送成功”或PC人工看到字符就判定PASS。

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| UART_F_001 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_001`, `UART_P1_017`, `UART_P1_001` |
| UART_F_002 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_001` |
| UART_F_003 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_001` |
| UART_F_004 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_001` |
| UART_F_005 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_002`, `UART_P2_008` |
| UART_F_006 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | PARTIAL_ADAPTATION | `UART_P1_015`, `UART_P3_006` |
| UART_F_007 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_014` |
| UART_F_008 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_014` |
| UART_F_009 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_014` |
| UART_F_010 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_003`, `UART_P0_004`, `UART_P2_003`, `UART_P3_010` |
| UART_F_011 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_003` |
| UART_F_012 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_002`, `UART_P0_003`, `UART_P1_016` |
| UART_F_013 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_002`, `UART_P1_016` |
| UART_F_014 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_002`, `UART_P1_016` |
| UART_F_015 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_016`, `UART_P1_005` |
| UART_F_016 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_016`, `UART_P1_004` |
| UART_F_017 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_003`, `UART_P1_016`, `UART_P3_010` |
| UART_F_018 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_003`, `UART_P1_016` |
| UART_F_019 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_002`, `UART_P1_004`, `UART_P1_011`, `UART_P3_010` |
| UART_F_020 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_003`, `UART_P1_005`, `UART_P1_011` |
| UART_F_021 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_006`, `UART_P1_011` |
| UART_F_022 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_007`, `UART_P1_008`, `UART_P1_009`, `UART_P1_010` |
| UART_F_023 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_007` |
| UART_F_024 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_008` |
| UART_F_025 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_009` |
| UART_F_026 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_010` |
| UART_F_027 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_012` |
| UART_F_028 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_002`, `UART_P1_003`, `UART_P1_006`, `UART_P1_007`, `UART_P1_008`, `UART_P1_009`, `UART_P1_011`, `UART_P1_012` |
| UART_F_029 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_004`, `UART_P2_005` |
| UART_F_030 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_004`, `UART_P2_005` |
| UART_F_031 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_005`, `UART_P2_010` |
| UART_F_032 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_006` |
| UART_F_033 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_007` |
| UART_F_034 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_007` |
| UART_F_035 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_001`, `UART_P2_002`, `UART_P2_003` |
| UART_F_036 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P2_001`, `UART_P2_002`, `UART_P2_003` |
| UART_F_037 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_013` |
| UART_F_038 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_004` |
| UART_F_039 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_005` |
| UART_F_040 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_001` |
| UART_F_041 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_002` |
| UART_F_042 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_003` |
| UART_F_043 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P0_001` |
| UART_F_044 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P3_007`, `UART_P3_009` |
| UART_F_045 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | NEEDS_VERIFICATION | — |
| UART_F_046 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P1_001` |
| UART_F_047 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | ADAPTED | `UART_P3_010` |
| UART_F_048 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_006` |
| UART_F_049 | SUPPORTED | 以本文件前四章及当前 Capability 为准 | IMPLEMENTATION_GAP | `UART_P3_008` |

> `Hardware=SUPPORTED` 表示该 Feature 来自当前芯片 Hardware Feature Truth；Platform 只描述公共自动化适配，不代表本次 HIL PASS。

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| UART_P0_001 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P0_002 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P0_003 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P0_004 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_014 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_015 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_016 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_017 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_001 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_002 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_003 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_004 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_005 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_006 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_007 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_008 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_009 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_010 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_011 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_012 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P1_013 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_001 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_002 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_003 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_004 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_005 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_006 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_007 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_008 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P3_010 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P2_010 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P3_001 | BENCH_GAP | RS485模式需要可信Peer/收发器和板级连接证据 |
| UART_P3_002 | BENCH_GAP | DE/RE极性需要可信Peer/收发器和板级观察条件 |
| UART_P3_003 | BENCH_GAP | RS485时序需要独立时序Observer或可信Companion |
| UART_P3_004 | BENCH_GAP | SIR数据路径需要可信SIR收发器或数字模型 |
| UART_P3_005 | BENCH_GAP | 低功耗SIR需要对应外部/模型条件 |
| UART_P3_006 | BENCH_GAP | 绝对波特率与位时序需要独立Observer |
| UART_P3_007 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |
| UART_P3_008 | NEEDS_VERIFICATION | 访问保护与超时恢复需要权限模型、RTL/总线契约和安全恢复证据 |
| UART_P3_009 | ADAPTED | 已存在公共 Formal Case；真实执行结果以独立 HIL Evidence 为准 |

### 6.1 同步规则

- ET6801 的 Feature/options/limits/实例/IRQ/Chip Driver/Board/Mapping 事实变化时必须同步本文件。
- ET6801 的适配状态变化时，同时更新公共 `uart.md` 的 Chip Adaptation Summary。
- 本文件不保存 `ET_CASE_SPEC` / `ET_CASE_PLAN` 机器块，避免形成第二份公共 Case 真值。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:27 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:14 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | NOT_RETAINED |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 33 | 33 | 30 | 0 | 3 | 0 | 33 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| `UART_P1_008` | FPGA | SKIP | `UART_F_022` / Framing Error状态和Line Error中断 | 当前UART1/UART2交叉连接下，改变两端停止位后仍不能稳定形成可重复的Framing Error状态和中断 | 当前TX/RX连接无法确定性制造停止位采样错误，不能用不稳定刺激判断Feature | 提供可控错误帧发生器、FPGA波形发生器或可精确破坏停止位的Peer后复测 | NOT_RETAINED |
| `UART_P1_012` | FPGA | SKIP | `UART_F_027`、`UART_F_028` / Busy Detect中断及清除 | 正常启用FIFO并持续发送期间修改LCR，限定触发窗口内未形成确定性的Busy Detect中断 | 当前刺激不能稳定满足Busy Detect的硬件触发时序；现有结果不足以判定Feature PASS或FAIL | 取得ET6801 Busy Detect准确触发时序，或使用可控制发送与LCR写入相位的刺激后复测 | NOT_RETAINED |
| `UART_P3_009` | FPGA | SKIP | `UART_F_044` / Direct FIFO访问 | Capability读取结果表明Direct FIFO Access不可用，Case未执行FAR/TFR/RFW访问 | ET6801当前UART组件参数未声明Direct FIFO Access支持，目标芯片不具备该可执行能力 | 仅当后续RTL/芯片Capability明确支持Direct FIFO Access时复测 | NOT_RETAINED |
<!-- ET_CHIP_TEST_STATUS_END -->

<a id="uart-record-index"></a>

### 6.2 测试记录与知识索引

2026-09-09 10:13 CST补充：[33个已注册Case的提炼型知识](../../artifacts/records/ET6801/UART/README.md)已从人读历史报告与本文件状态块迁移，保留方法要点、修复史与验证边界；不是新增测试，不改变上方状态块数据。原始Canonical Session（2026-08-28 `runs/20260828_170737_043300_local_et6801_fpga`与2026-08-13 `operator_hil/20260813_gui_pipeline`）已随早期清理不在仓库，参数级execution明细不可考；本节只提供路径导航，不保存第二份当前测试状态。

| 入口 | 用途 |
|---|---|
| [UART Case知识索引](../../artifacts/records/ET6801/UART/README.md) | 33个已注册Case的提炼型知识（方法/结果边界/修复史）；历史来源与证据缺失声明见其"历史来源与版本" |
| [全量HIL报告 2026-08-10](../../report/validation/dut/20260810_et6801_pc_firmware_freeze_full_hil.md) | Framework/UART/DMA冻结全量HIL（118 PASS/3 SKIP/0 FAIL） |
| [GUI Pipeline UART HIL报告 2026-08-13](../../report/hil/20260813_et6801_gui_pipeline_uart_hil_report.md) | UART 33项 30 PASS/3 SKIP/0 FAIL；轮次环境身份以该报告为准 |
| [P2-010与P3-007独立HIL 2026-08-05](../../report/validation/dut/20260805_uart_split_cases_hil.md) | P2_010两次FAIL定位记录与P3_007实测（CPR=0x13DF2） |
| [9-bit地址中断Driver修复HIL 2026-08-05](../../report/validation/dut/20260805_uart_address_irq_driver_fix_hil.md) | P2_010修复后PASS与IRQ影响回归 |
| [正式PFLASH启动与UART公共框架HIL 2026-07-26](../../report/validation/dut/20260726_et6801_formal_flash_uart_hil.md) | 早期链路层验证（协议可靠性+1000轮混合载荷压力） |
| [公共UART契约](uart.md) | 各Case `ET_CASE_SPEC`方法权威 |

继续开发入口：先读本节索引对应Case的知识Markdown，再回[公共UART契约](uart.md)核对`ET_CASE_SPEC`；下一次真实运行后按R500在`artifacts/records/ET6801/UART/current/`建立当次工作区，本节链接的历史结论不替代当前回归。
