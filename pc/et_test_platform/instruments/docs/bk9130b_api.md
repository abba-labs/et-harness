# B&K Precision 9130B Python API

## 1. 设计范围

本型号实现依据 `9130B_Series_programming_manual.pdf` 的详细命令章节，并使用
`9130B_Series_datasheet.pdf` 确认 9130B 的输出范围：CH1/CH2 为 0~30 V，CH3 为
0~5 V，三个通道均为 0~3 A。

厂家资料明确给出三种远程接口：USB、RS-232、GPIB。其中 USB 为 USBTMC-compliant，
可通过 SCPI 由 PC 控制。项目新台架固定优先使用 **USBTMC + VISA**；已有 RS232 构造保留
用于旧台架兼容，不新增 GPIB 专用工厂。

Driver 仍遵守：

```text
一项稳定控制/查询语义 = 一个原子 API
```

`controls/` 不隐藏多步流程；多步动作只能放到 `operations.py`。

## 2. 目录

```text
bk9130b/
├── connection.py
├── driver.py
├── models.py
├── validation.py
├── operations.py
└── controls/
    ├── ieee488.py
    ├── system.py
    ├── status.py
    ├── output.py
    ├── source.py
    ├── display.py
    ├── trigger.py
    ├── channel.py
    ├── measurement.py
    └── apply.py
```

## 3. 原子 API 覆盖

| Driver 分组 | API 数 | 主要能力 |
|---|---:|---|
| `common` | 18 | *CLS / *ESE / *ESR / *IDN / *OPC / *RST / *SRE / *STB / *TRG / *SAV / *RCL / *TST / *WAI / *PSC |
| `system` | 11 | Error / Version / Remote / Local / RWLock / GPIB Address / Beeper / Interface / Memory Group |
| `status` | 39 | QUEStionable / OPERation / Instrument / ISUMmary1~3 |
| `output` | 12 | Output State / Timer / Tracking / Series / Parallel |
| `source` | 26 | Channel Output / Current / Voltage / Step / Triggered / OVP / Voltage Limit |
| `display` | 5 | Display State / Text / Clear |
| `trigger` | 3 | Immediate / Delay |
| `channel` | 9 | Select / NSelect / Combine / Trigger Couple |
| `measurement` | 5 | Voltage / Current / Power / All Channels |
| `apply` | 8 | Channel Apply / 3-channel Voltage / Current / Output |
| **合计** | **136** | **正文明确命令语义 100% 映射** |

## 4. 连接入口

### 4.1 推荐：USBTMC + VISA

项目新台架使用 `create_bk9130b_usb_driver()`。调用方传入实际 VISA backend 枚举到的
USB 资源字符串；工厂只接受 `USB...` 资源，构造阶段不会打开设备，也不会发送 SCPI。

```python
from et_test_platform.instruments.power_supplies.bk9130b import (
    Bk9130bChannel,
    create_bk9130b_usb_driver,
)

driver = create_bk9130b_usb_driver(
    "USB0::0xXXXX::0xXXXX::SERIAL::INSTR",
)
driver.open()
try:
    driver.channel.select_set(Bk9130bChannel.CH1)
    driver.source.voltage_set(5.0)
    driver.source.current_set(1.0)
    driver.source.channel_output_enabled_set(True)
finally:
    driver.close()
```

上面的 VID/PID/序列号只是资源格式示例，真实值应由当前 VISA backend/仪器枚举结果提供；
代码不会硬编码厂家 USB 标识。

### 4.2 兼容：RS232

已有 `create_serial_driver()` 继续保留。编程手册没有给出一个可以安全猜测的统一 RS232
默认参数，因此调用方仍必须显式提供波特率：

```python
from et_test_platform.instruments.power_supplies.bk9130b import create_serial_driver

driver = create_serial_driver(port="COM7", baudrate=9600)
```

这里的 `9600` 只是调用示例，不是代码硬编码的厂家默认值。

## 5. Operations

当前 Typed Operations 提供：

- `driver.operations.configure_channel(config)`：显式指定通道，配置电压、电流、可选 OVP 和最终输出状态；
- `driver.operations.configure_channel_and_enable(channel, voltage_v, current_a)`：兼容旧入口；
- `driver.operations.all_outputs_off()`：用一条 `APPLy:OUTput` 命令关闭三个通道；
- `driver.operations.read_all_outputs()`：返回三个通道电压/电流 Typed Snapshot；
- `driver.operations.read_channel(channel)`：显式选择指定通道后读取电压、电流和功率。

`Bk9130bChannelConfig` 会在第一条 SCPI 写入前完成通道相关范围校验，包括 CH3 的 5 V 上限。
Driver 原子层仍全部可独立使用。

## 6. 手册歧义与故意不复制的 API

命令总表存在正文没有详细说明的索引项：`SYSTem:MODUle?`、`SYSTem:TRAcking`、
`SYSTem:PARAllel`、裸 `CHANnel` / `CHANnel?`、`INSTrument:COMbine:OFF`、
`INSTrument:COMbine?`。这些条目没有被伪装成“已确认稳定 API”。

正文给出的 `FETCh[:VOLTage]?`、`FETCh:CURRent?` 与对应 `MEASure` 查询属于同一能力，
因此 Python 层只保留一个稳定测量语义，不复制兼容别名。

## 7. 当前验证边界

软件验证覆盖：

- 136 项原子 API Inventory；
- 关键 SCPI 映射、结构化响应和参数校验；
- Typed Operations 命令顺序与零 I/O 构造；
- USBTMC VISA Connection 工厂的资源类型约束与构造结果。

真实 USBTMC / RS232 / GPIB 通信以及输出电气行为仍为：

```text
HIL = NOT_EXECUTED
```

因此“完成”只表示软件契约与连接工厂已实现，不表示真实 9130B 硬件链路已经验证。
