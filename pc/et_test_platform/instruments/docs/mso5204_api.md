# RIGOL MSO5204 Python API 设计与最终覆盖说明

## 1. 状态

资料基线：

```text
MSO5000 Programming Guide
May. 2025
PGA25105-1110
Software Version 00.01.02.SP5
```

MSO5204 当前已经完成 **997 个 Typed/Named 原子 API**。Programming Guide Chapter 2 的公开命令族已经全部规范化进入 Driver，因此软件命令契约分母冻结为：

```text
997 / 997 = 100%
```

这里的 100% 只表示软件远程控制 API 覆盖，不代表真实 MSO5204 已进行 HIL 验证。

## 2. 分层

```text
VISA Transport
  -> ScpiSession
     -> Mso5204Driver
        -> 原子 Controls
           -> Operations
              -> Test Case
```

Driver 层始终保持“一项稳定控制/查询/动作语义一个 API”。多步高频流程可以继续在 `operations.py` 中组合，但不能把 PASS/FAIL、跨仪器编排或隐藏的自动配置塞回 Driver。

## 3. Control 分组

```text
basic
common
acquire
bodeplot
bus
channel
counter
cursor
display
dvm
histogram
logic_analyzer
lan
mask
math
measurement
power
quick
record
reference
save_load
search
source
system
timebase
trace
trigger
trigger_advanced
trigger_protocol
waveform
```

最终 API 数量见 [API_COVERAGE.md](API_COVERAGE.md)。

## 4. Bode Plot

```python
driver.bodeplot.enabled_set(True)
driver.bodeplot.start_frequency_set(10)
driver.bodeplot.stop_frequency_set(1e6)
driver.bodeplot.points_per_decade_set(30)
driver.bodeplot.voltage_set(1.0, "F1MHZ")
gain_margin_db = driver.bodeplot.gain_margin_get()
```

覆盖扫频显示、源、输入/输出参考、阻抗、频率范围、点数、电压 Profile、Gain Margin 和 Phase Margin。

## 5. LAN

```python
driver.lan.dhcp_set(False)
driver.lan.auto_ip_set(False)
driver.lan.manual_ip_set(True)
driver.lan.ip_address_set("192.168.1.10")
driver.lan.subnet_mask_set("255.255.255.0")
driver.lan.gateway_set("192.168.1.1")
driver.lan.apply()
```

`LAN:APPLy` 是显式动作；Driver 不会在修改单个网络字段后偷偷执行 Apply。

## 6. Power Analysis

```python
driver.power.analysis_type_set("QUALity")
driver.power.current_source_set("CHANnel2")
driver.power.voltage_source_set("CHANnel1")
driver.power.quality_frequency_reference_set("VOLTage")
```

覆盖 Power Quality/Ripple 与 Reference Level 百分比配置。

## 7. Quick Key

```python
driver.quick.operation_set("SWAVe")
operation = driver.quick.operation_get()
```

只配置前面板快捷键类型，不执行快捷键对应动作。

## 8. Arbitrary Trace

```python
payload = b"\x00\x00\xff\x3f"
driver.trace.dac16_data_set(1, payload)
```

对应：

```text
TRACe<n>:DATA:DAC16 volatile,END,<binary_block_data>
```

要求：

- AWG source 只能为 1 或 2；
- payload 为偶数字节；
- 长度 4~32768 Bytes；
- 每个 waveform point 对应两个字节，手册定义有效值范围为 `0x0000~0x3FFF`；
- Driver 不自动缩放样点、不自动打开 AWG Output。

## 9. 主要自动化能力示例

### 波形捕获

```python
configure_edge_capture(
    driver,
    1,
    vertical_scale_v=0.5,
    time_scale_s=1e-6,
    trigger_level=1.2,
)
driver.basic.single()
```

### 读取波形

```python
waveform = read_screen_waveform(driver, 1, start=1, stop=1000)
```

### CAN 解码

```python
driver.bus.mode_set(1, "CAN")
driver.bus.can_source_set(1, "CHANnel1")
driver.bus.can_baud_set(1, 500000)
```

### 协议触发

```python
driver.trigger.mode_set("CAN")
driver.trigger_protocol.can_source_set("CHANnel1")
driver.trigger_protocol.can_baud_set(500000)
```

### 内置 AWG

```python
driver.source.function_set(1, "SINusoid")
driver.source.frequency_set(1, 1000)
driver.source.amplitude_set(1, 1.0)
driver.source.output_enabled_set(1, True)
```

AWG、Bode 等能力依赖相应仪器 Option；API 存在不等于目标实机一定安装选件。

## 10. 最终验证边界

软件层已完成：

- 各命令族 Typed API；
- Set/Query/Action 原子映射；
- IEEE488.2 binary block；
- 波形 Preamble 物理量换算；
- Protocol Trigger / BUS Decode；
- Search / Reference / Save-Load / AWG；
- Bode / LAN / Power / Quick / Trace；
- API Inventory 单元测试；
- GitHub Software Quality Gate。

尚未执行：

```text
HIL = NOT_EXECUTED
```

后续工作重点应从“继续补 Driver 命令”切换为：

```text
Operations 常用组合
-> Test Case 使用接口
-> 仪器资源配置
-> 真机 HIL 验证
```
