# ET 自动化测试平台——仪器驱动功能与 API 速查

> 适用仓库：`Abba-shenfu/Automated_Testing_Platform`
> 分支：`case_report_extension`
> 基线提交：`7bc630b688e3ea7fd4c9399c08cd4b3b46d05169`
> 文档目的：按“仪器 → 功能分类 → 推荐 Operations API → 原子 Control API”整理当前已开发仪器驱动，供 Test Case、平台开发和后续 HIL 验证时快速查阅。

---

## 1. 当前已开发仪器总览

| 仪器 | 类型 | 软件 API 覆盖 | 推荐高层入口 | 当前状态 |
|---|---|---:|---|---|
| RIGOL DP711 | 单通道直流电源 | 108 / 108 | `driver.operations` | 软件完成，HIL 未执行 |
| B&K Precision 9130B | 三通道直流电源 | 136 / 136* | `driver.operations` | 软件完成，HIL 未执行 |
| RIGOL DM3068 | 数字万用表 | 183 / 183* | `driver.operations` | 软件完成，HIL 未执行 |
| RIGOL MSO5204 | 混合信号示波器 | 997 / 997 | `driver.operations` + 原子 Controls | 软件完成，HIL 未执行 |

说明：

- `9130B 136 / 136` 指厂家编程手册**正文能够明确确认的稳定远程控制语义**。
- `DM3068 183 / 183` 指 **Common + RIGOL 原生命令体系**；Agilent / Fluke 兼容语法不重复做成公共 Python API。
- `MSO5204 997 / 997` 指 MSO5000 Programming Guide Chapter 2 规范化后的公开软件控制语义。
- 所有“完成”均指**软件命令契约与自动化测试完成**，不等于真实仪器 HIL 已通过。

---

## 2. API 使用原则

平台仪器驱动统一采用以下分层：

```text
Transport
  ↓
ScpiSession
  ↓
Driver
  ├─ Atomic Controls       # 一条稳定控制/查询/动作语义一个 API
  └─ Operations            # 常用的同仪器多步组合
        ↓
Test Case                  # 断言、PASS/FAIL、跨仪器编排
```

### 2.1 推荐优先级

业务用例优先使用：

```python
driver.operations.xxx(...)
```

当 Operations 没有覆盖某个特殊能力时，再直接调用：

```python
driver.<control>.<atomic_api>(...)
```

### 2.2 Driver / Operations 不负责的事情

仪器 Driver 和 Operations 不应该：

- 判断 Test Case PASS / FAIL；
- 跨仪器联动；
- 操作 DUT；
- 隐藏测试阈值；
- 隐式吞掉仪器异常；
- 在 Driver 构造阶段自动访问硬件。

这些行为应由 Test Case / Orchestration 层负责。

---

# 3. RIGOL DP711 直流电源

## 3.1 定位

DP711 是当前平台的单通道可编程直流电源 Driver。

主要支持：

- 电压、电流设置；
- 输出开关；
- OCP / OVP；
- 电压、电流、功率测量；
- Timer 输出；
- Memory 状态保存/恢复；
- 系统与 RS232 配置；
- 前面板、显示、远程模式等控制。

### 连接入口

```python
from et_test_platform.instruments.power_supplies.dp711 import create_dp711_serial_driver

driver = create_dp711_serial_driver("COM3")
driver.open()
```

常用生命周期：

```python
driver.open()
driver.close()
```

---

## 3.2 推荐 Operations API

### 3.2.1 安全配置电源输出

推荐：

```python
from et_test_platform.instruments.power_supplies.dp711 import Dp711OutputConfig

config = Dp711OutputConfig(
    voltage_v=5.0,
    current_a=1.0,
    enabled=True,
    ocp_limit_a=1.5,
    ovp_limit_v=5.5,
    disable_before_configure=True,
)

driver.operations.configure_output(config)
```

API：

```text
driver.operations.configure_output(config)
```

支持：

- 配置前先关闭输出；
- 设置 OCP 阈值并使能；
- 设置 OVP 阈值并使能；
- 设置电压；
- 设置电流；
- 设置最终输出状态；
- 整个 Config 在第一条 SCPI 写入前完成静态参数校验。

### 3.2.2 快速设置并打开输出

```python
driver.operations.configure_and_enable(5.0, 1.0)
```

等价业务意图：

```text
设置电压 → 设置电流 → 打开输出
```

### 3.2.3 安全关闭输出

```python
driver.operations.safe_output_off()
```

需要同时清除保护标志：

```python
driver.operations.safe_output_off(clear_protection=True)
```

### 3.2.4 一次读取输出状态

```python
measurement = driver.operations.read_output()
```

返回：

```python
Dp711Measurement(
    voltage_v=...,
    current_a=...,
    power_w=...,
)
```

---

## 3.3 原子 Control API 分类

| 功能类别 | API 命名空间 | API 数 | 主要能力 | 常用 API |
|---|---|---:|---|---|
| 基础/设备 | `driver.basic` | 15 | IDN、Option、Apply、Reset、Save/Recall、Display、License | `identity_get()`、`options_get()`、`apply_set()`、`reset()` |
| 测量 | `driver.measurement` | 4 | 电压、电流、功率、三者一次读取 | `voltage_get()`、`current_get()`、`power_get()`、`all_get()` |
| Memory | `driver.memory` | 6 | 状态/Timer 文件存储、加载、删除、锁定、有效性 | `store()`、`load()`、`delete()`、`valid_get()` |
| 输出 | `driver.output` | 18 | 输出开关、CV/CC、OCP、OVP | `enabled_set()`、`mode_get()`、`ocp_value_set()`、`ovp_value_set()` |
| Source | `driver.source` | 16 | 电压、电流和 Source 路径保护 | `voltage_set()`、`current_set()`、`voltage_protection_*`、`current_protection_*` |
| System | `driver.system` | 37 | RS232、语言、亮度、按键锁、远程模式、错误、自检、触发 IO | `error_get()`、`rs232_baudrate_set()`、`remote_mode_set()` |
| Timer | `driver.timer` | 12 | Timer 组、循环、步骤、电压电流时间、触发模式 | `parameter_set()`、`cycles_set()`、`enabled_set()` |

### 3.3.1 基础与设备信息

```python
driver.basic.identity_get()
driver.basic.options_get()
driver.basic.reset()
driver.basic.self_test_get()
driver.basic.apply_set(voltage_v, current_a)
driver.basic.apply_get()
```

### 3.3.2 直接设置电压/电流

```python
driver.source.voltage_set(5.0)
driver.source.current_set(1.0)
```

### 3.3.3 输出开关

```python
driver.output.enabled_set(True)
driver.output.enabled_set(False)
state = driver.output.enabled_get()
```

### 3.3.4 OCP

```python
driver.output.ocp_value_set(1.5)
driver.output.ocp_enabled_set(True)
driver.output.ocp_alarm_get()
driver.output.ocp_questionable_get()
driver.output.ocp_clear()
```

Source 路径也提供：

```python
driver.source.current_protection_value_set(1.5)
driver.source.current_protection_enabled_set(True)
driver.source.current_protection_tripped_get()
driver.source.current_protection_clear()
```

### 3.3.5 OVP

```python
driver.output.ovp_value_set(5.5)
driver.output.ovp_enabled_set(True)
driver.output.ovp_alarm_get()
driver.output.ovp_clear()
```

Source 路径：

```python
driver.source.voltage_protection_value_set(5.5)
driver.source.voltage_protection_enabled_set(True)
driver.source.voltage_protection_tripped_get()
```

### 3.3.6 测量

```python
voltage_v = driver.measurement.voltage_get()
current_a = driver.measurement.current_get()
power_w = driver.measurement.power_get()
all_values = driver.measurement.all_get()
```

### 3.3.7 Timer

```python
driver.timer.groups_set(...)
driver.timer.cycles_set(...)
driver.timer.parameter_set(group, voltage_v, current_a, duration_s)
driver.timer.enabled_set(True)
driver.timer.trigger_mode_set(...)
```

---

# 4. B&K Precision 9130B 三通道电源

## 4.1 定位

9130B 是三通道可编程直流电源。

主要特点：

- CH1 / CH2：0～30 V；
- CH3：0～5 V；
- 三通道：0～3 A；
- 支持独立通道输出；
- 支持 Tracking / Series / Parallel；
- 支持 OVP；
- 支持三通道批量 Apply；
- 支持三通道测量；
- 支持状态寄存器、触发、定时、显示、远程接口等。

### 连接入口

```python
from et_test_platform.instruments.power_supplies.bk9130b import create_serial_driver

driver = create_serial_driver(port="COM7", baudrate=9600)
driver.open()
```

注意：示例中的 `9600` 只是调用参数，不代表代码假定厂家统一默认波特率。

---

## 4.2 推荐 Operations API

### 4.2.1 Typed 单通道配置

```python
from et_test_platform.instruments.power_supplies.bk9130b import (
    Bk9130bChannel,
    Bk9130bChannelConfig,
)

config = Bk9130bChannelConfig(
    channel=Bk9130bChannel.CH3,
    voltage_v=3.3,
    current_a=1.0,
    output_enabled=True,
    ovp_limit_v=4.0,
    ovp_enabled=True,
    disable_before_configure=True,
)

driver.operations.configure_channel(config)
```

API：

```text
driver.operations.configure_channel(config)
```

关键价值：

- 明确指定 Channel，不依赖“当前通道”隐式状态；
- CH1 / CH2 自动按 30 V 上限校验；
- CH3 自动按 5 V 上限校验；
- 三通道电流统一按 3 A 上限校验；
- 可选 OVP；
- 可选配置前关闭通道输出；
- 参数在第一条 SCPI 写入前完成检查。

### 4.2.2 快速配置并打开某一路

```python
driver.operations.configure_channel_and_enable(
    Bk9130bChannel.CH1,
    5.0,
    1.0,
)
```

### 4.2.3 关闭三路输出

```python
driver.operations.all_outputs_off()
```

### 4.2.4 一次读取三通道电压/电流

```python
snapshot = driver.operations.read_all_outputs()
```

返回：

```python
Bk9130bOutputMeasurements(
    voltages_v=(ch1_v, ch2_v, ch3_v),
    currents_a=(ch1_a, ch2_a, ch3_a),
)
```

### 4.2.5 读取指定通道 V/I/P

```python
measurement = driver.operations.read_channel(Bk9130bChannel.CH1)
```

返回：

```python
Bk9130bChannelMeasurement(
    channel=...,
    voltage_v=...,
    current_a=...,
    power_w=...,
)
```

---

## 4.3 原子 Control API 分类

| 功能类别 | API 命名空间 | API 数 | 主要能力 | 常用 API |
|---|---|---:|---|---|
| IEEE488.2 | `driver.common` | 18 | IDN、Reset、Trigger、Save/Recall、Status、OPC、WAI | `identity_get()`、`reset()`、`trigger()` |
| System | `driver.system` | 11 | Error、Version、Remote/Local、RWLock、GPIB、Interface、Memory Group | `error_get()`、`version_get()`、`interface_set()` |
| Status | `driver.status` | 39 | QUEStionable、OPERation、Instrument、ISUMmary1~3 | `questionable_*`、`operation_*` |
| Output | `driver.output` | 12 | 总输出、Timer、Tracking、Series、Parallel | `enabled_set()`、`tracking_enabled_set()`、`series_enabled_set()`、`parallel_enabled_set()` |
| Source | `driver.source` | 26 | 当前通道 V/I、Step、Triggered、OVP、Voltage Limit、Channel Output | `voltage_set()`、`current_set()`、`channel_output_enabled_set()` |
| Display | `driver.display` | 5 | 显示开关、文本、清除 | `enabled_set()`、`text_set()`、`text_clear()` |
| Trigger | `driver.trigger` | 3 | Immediate、Delay | `immediate()`、`delay_set()`、`delay_get()` |
| Channel | `driver.channel` | 9 | 选择、编号、串/并/跟踪组合、Trigger Couple | `select_set()`、`combine_series_set()`、`couple_trigger_set()` |
| Measurement | `driver.measurement` | 5 | 当前通道 V/I/P、三通道全部 V/I | `voltage_get()`、`current_get()`、`power_get()`、`all_voltages_get()` |
| Apply | `driver.apply` | 8 | 单通道 Apply、三通道批量 V/I/Output | `channel_set()`、`voltages_set()`、`currents_set()`、`outputs_set()` |

### 4.3.1 通道选择

```python
driver.channel.select_set(Bk9130bChannel.CH1)
channel = driver.channel.select_get()
```

### 4.3.2 当前通道电压/电流

```python
driver.source.voltage_set(5.0)
driver.source.current_set(1.0)
driver.source.channel_output_enabled_set(True)
```

> 注意：直接使用 `driver.source` 时，其作用对象是“当前选中通道”。Case 如果希望避免隐式状态，优先使用 `driver.operations.configure_channel()`。

### 4.3.3 OVP

```python
driver.source.voltage_protection_level_set(6.0)
driver.source.voltage_protection_enabled_set(True)
tripped = driver.source.voltage_protection_tripped_get()
driver.source.voltage_protection_clear()
```

### 4.3.4 批量三通道设置

```python
driver.apply.voltages_set(ch1_v, ch2_v, ch3_v)
driver.apply.currents_set(ch1_a, ch2_a, ch3_a)
driver.apply.outputs_set(True, True, False)
```

### 4.3.5 串联 / 并联 / Tracking

```python
driver.output.series_enabled_set(True)
driver.output.parallel_enabled_set(True)
driver.output.tracking_enabled_set(True)
```

这些 API 只发送设备控制命令，不替代实际物理接线和测试安全规则。

---

# 5. RIGOL DM3068 数字万用表

## 5.1 定位

DM3068 当前公共 Driver 以：

```text
Common Command System
+
RIGOL Command System
```

作为稳定 API 基线。

主要支持：

- DCV / ACV；
- DCI / ACI；
- 2 线电阻 / 4 线电阻；
- 电容；
- 频率；
- 周期；
- 通断；
- 二极管；
- Statistic；
- REL；
- dB / dBm；
- Pass/Fail；
- 自动/单次/外部触发；
- Reading Hold；
- VMC；
- 双显示；
- LAN / GPIB / RS232 仪器端参数；
- 系统、显示、格式和设备信息。

### 连接入口

```python
from et_test_platform.instruments.dmms.dm3068 import create_dm3068_serial_driver

driver = create_dm3068_serial_driver("COM4", baudrate=115200)
driver.open()
```

---

## 5.2 推荐 Operations API

### 5.2.1 Typed 基础测量配置

```python
from et_test_platform.instruments.dmms.dm3068 import (
    Dm3068BasicMeasurementFunction,
    Dm3068MeasurementConfig,
    Dm3068RangeKeyword,
    Dm3068Rate,
)

config = Dm3068MeasurementConfig(
    function=Dm3068BasicMeasurementFunction.VOLTAGE_DC,
    range_value=Dm3068RangeKeyword.DEFAULT,
    rate=Dm3068Rate.MEDIUM,
)

driver.operations.configure_measurement(config)
```

支持 Typed 完整链：

```text
Function → Range → Rate
```

当前 Typed Operations 支持六类基础测量：

```text
VOLTAGE_DC
VOLTAGE_AC
CURRENT_DC
CURRENT_AC
RESISTANCE_2WIRE
RESISTANCE_4WIRE
```

### 5.2.2 读取已经配置好的基础测量值

```python
reading = driver.operations.read_measurement(Dm3068BasicMeasurementFunction.VOLTAGE_DC)
```

返回：

```python
Dm3068Reading(
    function=...,
    value=...,
)
```

### 5.2.3 配置并立即读一次

```python
reading = driver.operations.configure_and_read(config)
```

### 5.2.4 外部触发配置

```python
driver.operations.configure_external_trigger("RISE")
```

Operations 会：

```text
选择 EXT 触发源 → 配置外部触发模式
```

### 5.2.5 兼容函数式快捷入口

```python
configure_dc_voltage(driver)
configure_dc_current(driver)
configure_resistance_4wire(driver)
configure_external_trigger(driver, "RISE")
```

新代码优先推荐：

```python
driver.operations.xxx(...)
```

---

## 5.3 原子 Control API 分类

| 功能类别 | API 命名空间 | API 数 | 主要能力 | 常用 API |
|---|---|---:|---|---|
| Common | `driver.common` | 18 | CMDSET、IEEE488.2 | `identity_get()`、`reset()`、`self_test_get()`、`trigger()` |
| Status | `driver.status` | 9 | OPERation、QUEStionable、PRESet | `operation_event_get()`、`questionable_condition_get()` |
| Calculate | `driver.calculate` | 29 | Statistic、REL、dB、dBm、Pass/Fail | `statistic_*`、`relative_*`、`db_*`、`dbm_*`、`pass_fail_*` |
| Function | `driver.function` | 12 | 选择测量功能 | `voltage_dc_select()`、`current_dc_select()`、`resistance_4wire_select()` |
| Secondary Display | `driver.secondary_display` | 6 | FUNCtion2 双显示 | `frequency_select()`、`value1_get()`、`value2_get()` |
| Measurement | `driver.measurement` | 34 | 测量、量程、DCV 阻抗、模式 | `voltage_dc_get()`、`frequency_get()`、`capacitance_get()` |
| Rate | `driver.rate` | 14 | 各测量功能速率、Sensor Rate | `voltage_dc_set()`、`current_dc_set()`、`sensor_set()` |
| System | `driver.system` | 24 | Error、Beeper、Display、Format、Language、设备信息 | `error_get()`、`display_brightness_set()`、`serial_number_get()` |
| Trigger | `driver.trigger` | 17 | Auto、Single、External、Hold、VMC | `source_set()`、`single_trigger()`、`external_mode_set()` |
| Interface | `driver.interface` | 20 | LAN、GPIB、RS232 仪器端配置 | `lan_ip_set()`、`gpib_address_set()`、`rs232_baudrate_set()` |

### 5.3.1 选择测量功能

```python
driver.function.voltage_dc_select()
driver.function.voltage_ac_select()
driver.function.current_dc_select()
driver.function.current_ac_select()
driver.function.resistance_2wire_select()
driver.function.resistance_4wire_select()
driver.function.capacitance_select()
driver.function.frequency_select()
driver.function.period_select()
driver.function.continuity_select()
driver.function.diode_select()
```

### 5.3.2 DCV

```python
driver.measurement.voltage_dc_range_set(Dm3068RangeKeyword.DEFAULT)
driver.rate.voltage_dc_set(Dm3068Rate.MEDIUM)
value = driver.measurement.voltage_dc_get()
```

### 5.3.3 ACV / DCI / ACI

```python
ac_v = driver.measurement.voltage_ac_get()
dc_i = driver.measurement.current_dc_get()
ac_i = driver.measurement.current_ac_get()
```

### 5.3.4 电阻

```python
r_2w = driver.measurement.resistance_2wire_get()
r_4w = driver.measurement.resistance_4wire_get()
```

### 5.3.5 频率 / 周期 / 电容 / 通断 / 二极管

```python
freq_hz = driver.measurement.frequency_get()
period_s = driver.measurement.period_get()
cap = driver.measurement.capacitance_get()
continuity = driver.measurement.continuity_get()
diode = driver.measurement.diode_get()
```

### 5.3.6 测量模式

```python
from et_test_platform.instruments.dmms.dm3068 import Dm3068MeasurementMode

driver.measurement.mode_set(Dm3068MeasurementMode.AUTO)
driver.measurement.mode_set(Dm3068MeasurementMode.MANUAL)
```

### 5.3.7 Statistic

```python
driver.calculate.statistic_state_set(True)
minimum = driver.calculate.statistic_minimum_get()
maximum = driver.calculate.statistic_maximum_get()
average = driver.calculate.statistic_average_get()
count = driver.calculate.statistic_count_get()
```

### 5.3.8 REL / dB / dBm / Pass-Fail

```python
driver.calculate.relative_offset_set(...)
driver.calculate.relative_state_set(True)

driver.calculate.db_reference_set(...)
driver.calculate.db_state_set(True)

driver.calculate.dbm_reference_set(...)
driver.calculate.dbm_state_set(True)

driver.calculate.pass_fail_lower_set(...)
driver.calculate.pass_fail_upper_set(...)
driver.calculate.pass_fail_state_set(True)
result = driver.calculate.pass_fail_get()
```

### 5.3.9 Trigger

```python
driver.trigger.source_set(Dm3068TriggerSource.SINGLE)
driver.trigger.single_count_set(...)
driver.trigger.single_trigger()
```

外部触发：

```python
driver.trigger.source_set(Dm3068TriggerSource.EXTERNAL)
driver.trigger.external_mode_set("RISE")
```

### 5.3.10 LAN / GPIB / RS232

```python
driver.interface.lan_dhcp_set(True)
driver.interface.lan_ip_set("192.168.1.10")
driver.interface.gpib_address_set(10)
driver.interface.rs232_baudrate_set(115200)
```

> 这些接口只修改仪器端配置，不负责 PC Transport 自动重连。

---

# 6. RIGOL MSO5204 混合信号示波器

## 6.1 定位

MSO5204 是当前平台功能最完整的仪器 Driver，共 997 个规范化原子 API。

覆盖：

- 模拟通道；
- 时基；
- 采集；
- Edge / Advanced / Protocol Trigger；
- Waveform；
- 自动测量；
- Cursor；
- Counter；
- DVM；
- Logic Analyzer；
- BUS Decode；
- Math；
- Histogram；
- Mask；
- Search；
- Record；
- Reference；
- Save / Load；
- LAN；
- 内置 AWG Source；
- Arbitrary Trace；
- Bode Plot；
- Power Analysis；
- Quick Key；
- System / IEEE488.2；
- Display。

### 连接入口

```python
from et_test_platform.instruments.oscilloscopes.mso5204 import create_mso5204_visa_driver

driver = create_mso5204_visa_driver("TCPIP0::192.168.1.20::INSTR")
driver.open()
```

VISA 资源可以对应：

```text
USB / USBTMC
LAN / TCPIP / VXI-11
GPIB
```

---

## 6.2 推荐 Operations API

### 6.2.1 EDGE 捕获配置

```python
from et_test_platform.instruments.oscilloscopes.mso5204 import (
    Mso5204AnalogChannel,
    Mso5204EdgeCaptureConfig,
    Mso5204TriggerSlope,
)

config = Mso5204EdgeCaptureConfig(
    channel=Mso5204AnalogChannel.CH1,
    vertical_scale_v=0.5,
    time_scale_s=1e-6,
    trigger_level_v=1.0,
    trigger_slope=Mso5204TriggerSlope.RISING,
)

driver.operations.configure_edge_capture(config)
```

支持组合：

```text
Channel Display
Probe Ratio（可选）
Coupling
Bandwidth Limit（可选）
Vertical Scale
Vertical Offset（可选）
Timebase Mode / Scale / Offset
Acquire Type / Average Count（可选）
Trigger Mode
Trigger Source
Trigger Slope
Trigger Level
Trigger Sweep（可选）
```

### 6.2.2 常用自动测量

```python
frequency_hz = driver.operations.measure_frequency(1)
period_s = driver.operations.measure_period(1)
duty_percent = driver.operations.measure_duty_cycle(1)
vpp_v = driver.operations.measure_vpp(1)
vrms_v = driver.operations.measure_vrms(1)
rise_s = driver.operations.measure_rise_time(1)
fall_s = driver.operations.measure_fall_time(1)
```

### 6.2.3 一次读取常用信号指标

```python
snapshot = driver.operations.measure_signal(1)
```

返回：

```python
Mso5204SignalMeasurements(
    frequency_hz=...,
    period_s=...,
    duty_cycle_percent=...,
    vpp_v=...,
    vrms_v=...,
    rise_time_s=...,
    fall_time_s=...,
)
```

### 6.2.4 屏幕波形读取

```python
from et_test_platform.instruments.oscilloscopes.mso5204 import Mso5204WaveformReadConfig

waveform = driver.operations.read_screen_waveform(
    Mso5204WaveformReadConfig(
        channel=1,
        start=1,
        stop=1000,
    )
)
```

返回：

```python
Mso5204Waveform
```

其中已经完成：

- Preamble 读取；
- BYTE 波形读取；
- ADC byte → 电压换算；
- 样点 index → 时间换算。

---

## 6.3 原子 Control API 总表

| Control | API 数 | 主要功能 | 典型入口 |
|---|---:|---|---|
| `driver.basic` | 6 | 运行、停止、单次等顶层动作 | `single()` |
| `driver.common` | 15 | IEEE488.2 Common | IDN / OPC / Reset / Status 等 |
| `driver.acquire` | 11 | 采集模式、平均、Memory Depth | `type_set()`、`averages_set()`、`memory_depth_set()` |
| `driver.bodeplot` | 28 | Bode 扫频、输入/输出、Margin | `enabled_set()`、`start_frequency_set()`、`gain_margin_get()` |
| `driver.bus` | 126 | CAN / LIN / I2C / SPI / UART 等 BUS Decode | `mode_set()`、`can_source_set()`、`can_baud_set()` |
| `driver.channel` | 22 | 模拟通道显示、探头、Scale、Offset、Coupling | `display_set()`、`scale_set()`、`offset_set()` |
| `driver.counter` | 12 | 硬件计数器 | `driver.counter.*` |
| `driver.cursor` | 56 | Cursor 模式和读数 | `driver.cursor.*` |
| `driver.display` | 16 | 显示参数 | `driver.display.*` |
| `driver.dvm` | 7 | Digital Voltmeter | `driver.dvm.*` |
| `driver.histogram` | 19 | Histogram | `driver.histogram.*` |
| `driver.logic_analyzer` | 23 | 数字通道 / LA | `driver.logic_analyzer.*` |
| `driver.lan` | 25 | DHCP / AutoIP / IP / DNS / VISA / mDNS | `dhcp_set()`、`ip_address_set()`、`apply()` |
| `driver.mask` | 17 | Mask Test | `driver.mask.*` |
| `driver.math` | 65 | Math 运算、FFT 等 | `driver.math.*` |
| `driver.measurement` | 38 | 自动测量、阈值、统计 | `item_get()` |
| `driver.power` | 16 | Power Analysis | `analysis_type_set()`、`current_source_set()` |
| `driver.quick` | 2 | Quick Key 类型 | `operation_set()`、`operation_get()` |
| `driver.record` | 10 | 波形 Record | `driver.record.*` |
| `driver.reference` | 17 | Reference Waveform | `driver.reference.*` |
| `driver.save_load` | 16 | Save / Load | `driver.save_load.*` |
| `driver.search` | 54 | 波形事件 Search | `driver.search.*` |
| `driver.source` | 54 | 内置 AWG Source | `function_set()`、`frequency_set()`、`amplitude_set()` |
| `driver.system` | 32 | System、Error、设备配置 | `driver.system.*` |
| `driver.timebase` | 18 | 时基 Mode / Scale / Offset / Reference | `mode_set()`、`main_scale_set()` |
| `driver.trace` | 1 | 任意波形 DAC16 下载 | `dac16_data_set()` |
| `driver.trigger` | 17 | 基础触发/Edge | `mode_set()`、`edge_source_set()`、`edge_level_set()` |
| `driver.trigger_advanced` | 134 | 高级触发 | `driver.trigger_advanced.*` |
| `driver.trigger_protocol` | 120 | CAN/LIN/I2C/SPI/UART 等协议触发 | `can_source_set()`、`can_baud_set()` 等 |
| `driver.waveform` | 20 | Waveform Source/Mode/Format/Preamble/Data | `preamble_get()`、`data_get()` |
| **合计** | **997** | Programming Guide Chapter 2 软件控制语义 | — |

---

## 6.4 常用功能与 API

### 6.4.1 模拟通道

```python
driver.channel.display_set(1, True)
driver.channel.probe_ratio_set(1, 10)
driver.channel.coupling_set(1, ...)
driver.channel.bandwidth_limit_set(1, ...)
driver.channel.scale_set(1, 0.5)
driver.channel.offset_set(1, 0.0)
```

### 6.4.2 时基

```python
driver.timebase.mode_set(...)
driver.timebase.main_scale_set(1e-6)
driver.timebase.main_offset_set(0.0)
```

### 6.4.3 采集

```python
driver.acquire.type_set(...)
driver.acquire.averages_set(16)
driver.acquire.memory_depth_set(...)
```

### 6.4.4 Edge Trigger

```python
driver.trigger.mode_set(...)
driver.trigger.edge_source_set("CHANnel1")
driver.trigger.edge_slope_set(...)
driver.trigger.edge_level_set(1.0)
driver.trigger.sweep_set(...)
```

### 6.4.5 单次捕获

```python
driver.basic.single()
```

### 6.4.6 自动测量原子 API

```python
value = driver.measurement.item_get(item, "CHANnel1")
```

常用业务值推荐直接使用：

```python
driver.operations.measure_frequency(1)
driver.operations.measure_period(1)
driver.operations.measure_duty_cycle(1)
driver.operations.measure_vpp(1)
driver.operations.measure_vrms(1)
driver.operations.measure_rise_time(1)
driver.operations.measure_fall_time(1)
```

### 6.4.7 波形

```python
driver.waveform.source_set("CHANnel1")
driver.waveform.mode_set(...)
driver.waveform.format_set(...)
driver.waveform.start_set(1)
driver.waveform.stop_set(1000)
preamble = driver.waveform.preamble_get()
payload = driver.waveform.data_get()
```

### 6.4.8 CAN Decode

```python
driver.bus.mode_set(1, "CAN")
driver.bus.can_source_set(1, "CHANnel1")
driver.bus.can_baud_set(1, 500000)
```

### 6.4.9 CAN Trigger

```python
driver.trigger.mode_set("CAN")
driver.trigger_protocol.can_source_set("CHANnel1")
driver.trigger_protocol.can_baud_set(500000)
```

### 6.4.10 内置 AWG

```python
driver.source.function_set(1, "SINusoid")
driver.source.frequency_set(1, 1000)
driver.source.amplitude_set(1, 1.0)
driver.source.output_enabled_set(1, True)
```

### 6.4.11 Arbitrary Waveform / Trace

```python
driver.trace.dac16_data_set(1, payload)
```

### 6.4.12 Bode Plot

```python
driver.bodeplot.enabled_set(True)
driver.bodeplot.start_frequency_set(10)
driver.bodeplot.stop_frequency_set(1e6)
driver.bodeplot.points_per_decade_set(30)
gain_margin_db = driver.bodeplot.gain_margin_get()
```

### 6.4.13 LAN

```python
driver.lan.dhcp_set(False)
driver.lan.auto_ip_set(False)
driver.lan.manual_ip_set(True)
driver.lan.ip_address_set("192.168.1.10")
driver.lan.subnet_mask_set("255.255.255.0")
driver.lan.gateway_set("192.168.1.1")
driver.lan.apply()
```

### 6.4.14 Power Analysis

```python
driver.power.analysis_type_set("QUALity")
driver.power.current_source_set("CHANnel2")
driver.power.voltage_source_set("CHANnel1")
driver.power.quality_frequency_reference_set("VOLTage")
```

### 6.4.15 Quick Key

```python
driver.quick.operation_set("SWAVe")
operation = driver.quick.operation_get()
```

---

# 7. 按测试需求快速找 API

| 我要做什么 | 仪器 | 推荐 API |
|---|---|---|
| 设置 5 V / 1 A 并打开单路电源 | DP711 | `driver.operations.configure_output(Dp711OutputConfig(...))` |
| 读取电源实际 V/I/P | DP711 | `driver.operations.read_output()` |
| 安全关闭电源 | DP711 | `driver.operations.safe_output_off()` |
| 配置 9130B 某一路输出 | 9130B | `driver.operations.configure_channel(Bk9130bChannelConfig(...))` |
| 读取 9130B 某通道 V/I/P | 9130B | `driver.operations.read_channel(channel)` |
| 一次读取 9130B 三路 V/I | 9130B | `driver.operations.read_all_outputs()` |
| 三路全部关断 | 9130B | `driver.operations.all_outputs_off()` |
| 测 DC 电压 | DM3068 | `driver.operations.configure_and_read(Dm3068MeasurementConfig(...VOLTAGE_DC...))` |
| 测 DC 电流 | DM3068 | `...CURRENT_DC...` |
| 测 AC 电压/电流 | DM3068 | `...VOLTAGE_AC...` / `...CURRENT_AC...` |
| 测 2 线/4 线电阻 | DM3068 | `...RESISTANCE_2WIRE...` / `...RESISTANCE_4WIRE...` |
| 测频率 | DM3068 | `driver.measurement.frequency_get()` |
| 测电容 | DM3068 | `driver.measurement.capacitance_get()` |
| 配置示波器 Edge 捕获 | MSO5204 | `driver.operations.configure_edge_capture(config)` |
| 示波器测频率 | MSO5204 | `driver.operations.measure_frequency(channel)` |
| 示波器测周期 | MSO5204 | `driver.operations.measure_period(channel)` |
| 示波器测占空比 | MSO5204 | `driver.operations.measure_duty_cycle(channel)` |
| 示波器测 Vpp | MSO5204 | `driver.operations.measure_vpp(channel)` |
| 示波器测 Vrms | MSO5204 | `driver.operations.measure_vrms(channel)` |
| 示波器测 Rise/Fall | MSO5204 | `measure_rise_time()` / `measure_fall_time()` |
| 一次读取常用信号指标 | MSO5204 | `driver.operations.measure_signal(channel)` |
| 读取屏幕波形 | MSO5204 | `driver.operations.read_screen_waveform(config)` |
| CAN 总线解码 | MSO5204 | `driver.bus.*` |
| CAN 协议触发 | MSO5204 | `driver.trigger_protocol.*` |
| 内置 AWG 输出 | MSO5204 | `driver.source.*` |
| Bode 扫频 | MSO5204 | `driver.bodeplot.*` |
| Power Analysis | MSO5204 | `driver.power.*` |

---

# 8. 常用 Typed Config / Result 模型

## DP711

```text
Dp711OutputConfig
Dp711Measurement
Dp711ApplyState
Dp711Options
Dp711TimerStep
Dp711SystemError
```

## B&K 9130B

```text
Bk9130bChannel
Bk9130bChannelConfig
Bk9130bChannelMeasurement
Bk9130bOutputMeasurements
Bk9130bApplyState
Bk9130bSystemError
```

## DM3068

```text
Dm3068BasicMeasurementFunction
Dm3068MeasurementConfig
Dm3068Reading
Dm3068MeasurementMode
Dm3068RangeKeyword
Dm3068Rate
Dm3068TriggerSource
Dm3068SystemError
```

## MSO5204

```text
Mso5204EdgeCaptureConfig
Mso5204WaveformReadConfig
Mso5204SignalMeasurements
Mso5204Waveform
Mso5204WaveformPreamble
Mso5204MeasurementItem
Mso5204MeasurementStatistic
Mso5204AcquireType
Mso5204AnalogChannel
Mso5204TriggerSlope
Mso5204TriggerSweep
Mso5204MemoryDepth
```

---

# 9. 推荐 Test Case 使用方式

## 9.1 电源类

Test Case 中优先：

```python
power.operations.configure_output(...)
# 或
power.operations.configure_channel(...)
```

而不是在每一个 Case 里重复：

```text
关输出
→ 设置保护
→ 设置电压
→ 设置电流
→ 开输出
```

## 9.2 万用表类

优先：

```python
meter.operations.configure_and_read(config)
```

特殊测量再直接使用：

```python
meter.measurement.frequency_get()
meter.calculate.statistic_average_get()
```

## 9.3 示波器类

普通波形测试优先：

```python
scope.operations.configure_edge_capture(...)
scope.basic.single()
measurements = scope.operations.measure_signal(...)
waveform = scope.operations.read_screen_waveform(...)
```

协议、AWG、Bode、Power 等专项能力直接使用对应 Control：

```text
scope.bus
scope.trigger_protocol
scope.source
scope.bodeplot
scope.power
```

---

# 10. 验证状态与边界

当前软件侧已验证内容包括：

- Python Syntax；
- Ruff Format / Lint；
- 工程架构规则；
- Driver / Operations 分层规则；
- 原子 API → SCPI 映射；
- 参数范围/枚举校验；
- 非法参数尽量在 Transport 写入前拒绝；
- Binary Block；
- Waveform Preamble 换算；
- API Inventory；
- GitHub Software Quality Gate。

当前统一硬件状态：

```text
HIL = NOT_EXECUTED
```

因此：

```text
软件 API 完成
≠
真实仪器所有行为已经完成硬件验收
```

后续真机阶段建议至少验证：

1. `*IDN?` / 连接；
2. 基础 Set / Query；
3. 参数边界；
4. Output / Trigger 等有状态行为；
5. Option 实际安装情况；
6. Waveform / Binary Block；
7. 错误队列；
8. 超时与恢复；
9. 多次循环稳定性；
10. 仪器断连 / 重连。

---

# 11. 源码位置

```text
pc/et_test_platform/instruments/
├── dmms/
│   └── dm3068/
├── power_supplies/
│   ├── dp711/
│   └── bk9130b/
└── oscilloscopes/
    └── mso5204/
```

每台仪器基本统一为：

```text
<model>/
├── __init__.py
├── connection.py
├── driver.py
├── models.py
├── operations.py
├── validation.py
└── controls/
```

---

# 12. 一句话使用原则

> **常用流程用 `driver.operations`，专项能力用 `driver.<control>`，测试判定永远留在 Test Case。**
