# RIGOL DM3068 Python API 设计与覆盖说明

## 1. 定位

DM3068 Driver 采用与 DP711、9130B 一致的两层设计：

```text
Control / Driver 原子层
  -> 一个 API 对应一个稳定控制或查询语义

Operations 组合层
  -> 只组合已经存在的同仪器原子 API
```

Driver 不包含 Test Case 判定，不跨仪器编排，也不把多步测量流程隐藏在底层原子方法里。

项目新台架固定采用 **LAN + VISA** 连接 DM3068。已有 RS232 构造保留用于旧台架兼容，
但不继续开发 USB/GPIB 专用 Connection 工厂。

## 2. 资料基线

主要依据为 Google Drive 中的官方资料：

- `DM3068_ProgrammingGuide_CN.chm`；
- `DM3068_UserGuide_CN.pdf`；
- `DM3068_DataSheet_CN.pdf`。

官方资料明确给出 USB Device、LAN(LXI-C)、RS232、GPIB 远程接口，并支持远程 SCPI 控制。
CHM 内部可识别五套命令体系：

- Common Command System；
- RIGOL Command System；
- Compatible Agilent Command System；
- Expanded Agilent Command System；
- Compatible Fluke Command System。

公共 Python Driver 以 **Common + RIGOL 原生命令体系**作为稳定语义基线。Agilent/Fluke
兼容命令主要用于兼容既有软件，不机械复制成第二、第三套公共 API。

## 3. 目录

```text
dmms/dm3068/
├── __init__.py
├── connection.py
├── driver.py
├── models.py
├── operations.py
├── validation.py
└── controls/
    ├── common.py
    ├── status.py
    ├── calculate.py
    ├── function.py
    ├── secondary_display.py
    ├── measurement.py
    ├── rate.py
    ├── system.py
    ├── trigger.py
    └── interface.py
```

## 4. 原子 API 覆盖

Common + RIGOL 原生命令页面规范化以后，当前提供 **183 个原子 API**。

| Control | API 数 | 主要能力 |
|---|---:|---|
| `common` | 18 | CMDSET、IEEE488.2 Common |
| `status` | 9 | OPERation、QUEStionable、PRESet |
| `calculate` | 29 | Statistic、REL、dB、dBm、P/F |
| `function` | 12 | DCV/ACV/DCI/ACI/2WR/4WR/CAP/FREQ/PERIOD/CONT/DIODE |
| `secondary_display` | 6 | FUNCtion2 双显示原生命令 |
| `measurement` | 34 | 测量值、量程、DCV 输入阻抗、测量模式 |
| `rate` | 14 | DCV/ACV/DCI/ACI/2WR/4WR/Sensor Rate |
| `system` | 24 | Error、Beeper、Display、Format、Language、设备信息 |
| `trigger` | 17 | Auto、Single、External、Reading Hold、VMC |
| `interface` | 20 | LAN、GPIB、RS232 仪器端参数 |
| **合计** | **183** | **Common + RIGOL 原生稳定语义覆盖** |

## 5. API 命名空间

### 5.1 `driver.common`

```text
command_set_set
command_set_get
clear_status
event_status_enable_set
event_status_enable_get
event_status_register_get
identity_get
operation_complete
operation_complete_get
power_on_status_clear_set
power_on_status_clear_get
reset
service_request_enable_set
service_request_enable_get
status_byte_get
trigger
self_test_get
wait
```

### 5.2 `driver.status`

```text
operation_condition_get
operation_enable_set
operation_enable_get
operation_event_get
preset
questionable_condition_get
questionable_enable_set
questionable_enable_get
questionable_event_get
```

### 5.3 `driver.calculate`

```text
function_set
function_get
statistic_minimum_get
statistic_maximum_get
statistic_average_get
statistic_count_get
statistic_state_set
statistic_state_get
relative_offset_set
relative_offset_get
relative_state_set
relative_state_get
db_get
db_reference_set
db_reference_get
db_state_set
db_state_get
dbm_get
dbm_reference_set
dbm_reference_get
dbm_state_set
dbm_state_get
pass_fail_get
pass_fail_lower_set
pass_fail_lower_get
pass_fail_upper_set
pass_fail_upper_get
pass_fail_state_set
pass_fail_state_get
```

### 5.4 `driver.function`

```text
current_get
capacitance_select
continuity_select
current_ac_select
current_dc_select
diode_select
frequency_select
resistance_4wire_select
period_select
resistance_2wire_select
voltage_ac_select
voltage_dc_select
```

### 5.5 `driver.secondary_display`

```text
function_get
clear
frequency_select
enabled_get
value1_get
value2_get
```

这里严格按 DM3068 RIGOL Command System 中能够识别的 FUNCtion2 原生命令页实现，没有把旧型号
或兼容命令集的双显示命令直接搬过来。

### 5.6 `driver.measurement`

```text
new_data_get
mode_set
voltage_dc_get
voltage_dc_range_set
voltage_dc_range_get
voltage_dc_impedance_set
voltage_dc_impedance_get
voltage_ac_get
voltage_ac_range_set
voltage_ac_range_get
current_dc_get
current_dc_range_set
current_dc_range_get
current_ac_get
current_ac_range_set
current_ac_range_get
resistance_2wire_get
resistance_2wire_range_set
resistance_2wire_range_get
resistance_4wire_get
resistance_4wire_range_set
resistance_4wire_range_get
frequency_get
frequency_range_set
frequency_range_get
period_get
period_range_set
period_range_get
capacitance_get
capacitance_range_set
capacitance_range_get
continuity_get
continuity_range_set
diode_get
```

量程 Setter 接受：

```python
int
Dm3068RangeKeyword.MINIMUM
Dm3068RangeKeyword.MAXIMUM
Dm3068RangeKeyword.DEFAULT
```

不同测量功能的量程索引数量并不相同。当前 Driver 不使用旧 DM3058 的物理量程表去限制 DM3068，
只校验索引必须为非负整数；最终合法性由 DM3068 自身命令语义决定。

### 5.7 `driver.rate`

```text
voltage_dc_set / voltage_dc_get
voltage_ac_set / voltage_ac_get
current_dc_set / current_dc_get
current_ac_set / current_ac_get
resistance_2wire_set / resistance_2wire_get
resistance_4wire_set / resistance_4wire_get
sensor_set / sensor_get
```

### 5.8 `driver.system`

```text
error_get
version_get
beeper
beeper_state_set
beeper_state_get
clock_get
configure_default
power_on_mode_set
display_brightness_set
display_brightness_get
display_contrast_set
display_contrast_get
display_invert
edition_get
decimal_mark_set
decimal_mark_get
digit_separator_set
digit_separator_get
language_set
language_get
mac_address_get
open_times_get
serial_number_get
type_get
```

### 5.9 `driver.trigger`

```text
source_set
source_get
auto_interval_set
auto_interval_get
auto_hold_set
auto_hold_get
auto_hold_sensitivity_set
auto_hold_sensitivity_get
single_count_set
single_count_get
single_trigger
external_mode_set
external_mode_get
vmc_polarity_set
vmc_polarity_get
vmc_pulse_width_set
vmc_pulse_width_get
```

### 5.10 `driver.interface`

```text
lan_dhcp_set / lan_dhcp_get
lan_auto_ip_set / lan_auto_ip_get
lan_manual_ip_set / lan_manual_ip_get
lan_ip_set / lan_ip_get
lan_mask_set / lan_mask_get
lan_gateway_set / lan_gateway_get
lan_dns_set / lan_dns_get
gpib_address_set / gpib_address_get
rs232_baudrate_set / rs232_baudrate_get
rs232_parity_set / rs232_parity_get
```

## 6. 连接层

### 6.1 推荐：LAN + VISA

项目新台架使用 `create_dm3068_lan_driver()`。调用方传入实际 VISA backend 枚举到的
TCPIP 资源字符串；工厂只接受 `TCPIP...` 资源，构造阶段不会打开网络连接，也不会发送 SCPI。

```python
from et_test_platform.instruments.dmms.dm3068 import create_dm3068_lan_driver

meter = create_dm3068_lan_driver(
    "TCPIP0::192.168.10.22::INSTR",
)
meter.open()
```

上面的资源字符串只是格式示例，真实资源应以当前 VISA backend/仪器枚举结果为准。
LAN 会话使用 LF 作为 SCPI 命令终止符；响应若为 CRLF，`ScpiSession` 会在读取文本时去除 CR。

### 6.2 兼容：RS232

已有 `create_dm3068_serial_driver()` 继续保留，用于旧台架或没有网络条件的场景：

```python
from et_test_platform.instruments.dmms.dm3068 import create_dm3068_serial_driver

meter = create_dm3068_serial_driver(
    "COM4",
    baudrate=115200,
)
```

RS232 参数：

- 8 data bits；
- 1 stop bit；
- parity: NONE / ODD / EVEN；
- baudrate: 4800 / 9600 / 19200 / 38400 / 57600 / 115200；
- SCPI Session 结束符：`\r\n`。

型号 Driver 仍只依赖 `ScpiSession`，所以 183 个原子 API 与具体 Transport 解耦。
项目当前不开发 DM3068 的 USB/GPIB 专用 Connection 工厂。

## 7. Operations 组合层

当前 Typed Operations 以 `driver.operations` 为统一入口：

- `configure_measurement(config)`：按 Function -> Range -> Rate 完成基础测量配置；
- `read_measurement(function)`：读取已配置基础测量功能的一个 Typed 结果；
- `configure_and_read(config)`：配置后立即读取一次；
- `configure_external_trigger(mode)`：配置外部触发源和模式。

支持的基础 Typed Function：

```text
VOLTAGE_DC
VOLTAGE_AC
CURRENT_DC
CURRENT_AC
RESISTANCE_2WIRE
RESISTANCE_4WIRE
```

兼容函数式入口仍保留：

```text
configure_dc_voltage
configure_dc_current
configure_resistance_4wire
configure_external_trigger
```

例如：

```python
from et_test_platform.instruments.dmms.dm3068 import (
    Dm3068BasicMeasurementFunction,
    Dm3068MeasurementConfig,
    Dm3068Rate,
)

result = meter.operations.configure_and_read(
    Dm3068MeasurementConfig(
        function=Dm3068BasicMeasurementFunction.VOLTAGE_DC,
        rate=Dm3068Rate.MEDIUM,
    )
)
```

原子层仍然可以完全独立使用。

## 8. 兼容命令集边界

DM3068 CHM 还包含：

```text
Compatible Agilent Command System
Expanded Agilent Command System
Compatible Fluke Command System
```

当前公共 API 不重复实现这些语法别名。原因是公共 API 应表达“测量什么/配置什么”，而不是让
同一物理能力因为三套厂家语法出现三份 Python 方法。

一个需要单独记录的例外是 **Any Sensor 配置命令**：CHM 中 `ANYSensor:*` 页面位于 Expanded
Agilent Command System，而 RIGOL 原生命令页只明确存在 `RATE:SENSor`。因此当前 Driver 可以
控制 Sensor Rate，但没有凭猜测加入 `ANYSensor:APPLy/NAME/POINt/TYPE/UNIT` 的原生 API。
如果后续测试确实需要脚本创建自定义 Sensor，应在独立兼容层里按 Expanded Agilent 手册正文
逐项实现，而不是混入 RIGOL Control。

## 9. 无硬件验证

当前软件验证包括：

- Common/System 命令和结构化响应解析；
- DCV/ACV/DCI/ACI/2WR/4WR Function/Range/Rate/Measure 映射；
- Math、Trigger、接口配置映射；
- FUNCtion2 双显示映射；
- Typed Operations 命令顺序；
- 参数非法时不发送 SCPI；
- LAN VISA Connection 工厂的资源类型约束与零 I/O 构造；
- **183 API Inventory 固化测试**。

真实 DM3068 LAN/RS232 通信当前不可用，因此：

```text
HIL = NOT_EXECUTED
```

本文件中的“覆盖完成”只表示软件命令契约与连接工厂已经实现，不表示真实 DM3068 行为已经验证。
