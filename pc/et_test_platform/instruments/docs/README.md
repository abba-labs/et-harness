# 外部仪器 Python API 目录设计

```text
连接层 -> SCPI Session -> Driver 原子 API -> Operations -> Test Case
```

Driver 保持单个控制、查询或动作一个 API；高频同仪器流程允许在 Operations 再组合。

## 当前型号

| 型号 | 软件 API 状态 |
|---|---|
| RIGOL DP711 | **108 / 108 = 100%** |
| B&K Precision 9130B | **136 / 136 = 100%** |
| RIGOL DM3068 | **183 / 183 = 100%** |
| RIGOL MSO5204 | **997 / 997 = 100%** |

当前四台仪器的**软件命令契约已经完成**。真实硬件验证单独记录，当前统一为 `HIL = NOT_EXECUTED`。

## MSO5204 Controls

```text
acquire
basic
bodeplot
bus_decode
channel
counter
cursor
display
dvm
histogram
ieee488
lan
logic_analyzer
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

其中 AWG、协议解码、Bode 等能力可能依赖仪器 Option。Driver 提供软件控制接口，但不会假设目标实机已经安装选件。

## 下一层开发重点

基础 Driver 不再继续无边界增加命令。后续新增内容优先进入：

```text
operations.py
```

用于组合常见同仪器流程，例如：

```text
configure_power_output
configure_dmm_measurement
configure_edge_capture
configure_can_decode
configure_uart_decode
configure_spi_decode
configure_i2c_decode
```

跨仪器编排和 PASS/FAIL 仍留在 Test Case，不进入 Instrument Driver。

覆盖详情见 [API_COVERAGE.md](API_COVERAGE.md)。
