# MSO5204 接口参考

本文按**由高到低**的顺序列出全部接口：先讲库自己封装的便捷层，再往下到官方原子 API。
每一层都给出含义、使用场景和使用方法。

示波器：RIGOL MSO5204（4 通道）。当前台架地址 `169.254.201.131`（会变，用
`srpwm_bench/find_scope.py` 重新发现）。

## 代码归属：哪些是原厂、哪些是封装

库内**严格分目录**，看路径即可判断来源：

| 目录 | 归属 | 内容 |
|---|---|---|
| `mso5204/` | **原厂驱动**（未改动） | 997 个原子 API、厂商枚举/数据类、厂商 operations、validation、observer |
| `wrapper/` | **二次封装**（本仓库新增） | 台架对象、补充配置、波形分析、测量过滤 |
| `_internal/` | 通信支撑 | SCPI/VISA/Deadline/异常（为自包含而内联） |
| `interface.py` | 原厂契约 | 型号中立的 `SignalObserver`/`SignalEdge` |
| `demos.py`、`tests/` | 辅助 | 示例与冒烟测试，不参与驱动本体 |

**怎么判断一个方法是原厂还是封装**：

- 路径含 `wrapper` → 封装层
- 路径含 `mso5204/controls` → 原厂原子 API
- `mso5204/models.py` 的枚举 → 原厂；`wrapper/models.py` 的 `*Config` → 封装

原厂 `mso5204/` 目录**只被改动过 import 路径**（为了自包含，不依赖宿主工程），
其余代码与原厂逐字节一致。

---

## 目录

| 层 | 入口 | 归属 | 方法数 | 什么时候用 |
|---|---|---|---|---|
| 1. 台架层 | `wrapper.open_scope()` → `Mso5204Scope` | 封装 | 25 | **默认起点**。日常采集、测量、截图 |
| 2. 常用层 | `driver.operations` | 封装继承厂商 | 19+16 | 不要台架封装、想自己控制流程时 |
| 3. 分析层 | `wrapper.Wave` / `wrapper.analysis.*` | 封装 | 10 + 9 方法 | 把采样点算成物理量 |
| 4. 模型层 | `mso5204.models`（厂商）+ `wrapper.models`（封装） | 混合 | 16 枚举 + 8 数据类 | 传参和接结果 |
| 5. 原子层 | `driver.<命名空间>.<方法>` | **原厂** | 997 | 官方手册全覆盖，深度定制 |
| 6. 底层 | `_internal.*` | 支撑 | 6 模块 | 一般不用 |

---

# 1. 台架层：`Mso5204Scope`（封装）

**含义**：把"连仪器 → 配通道 → 采集 → 读数 → 关连接"收敛成一个对象。
**使用场景**：99% 的日常测试。**推荐用 `with` 语句**，异常时也能保证关闭连接。

```python
from oscilloscopes.wrapper import open_scope

with open_scope("TCPIP0::169.254.201.131::INSTR") as scope:
    ...
```

## 1.1 构造与连接

| 方法 | 含义 | 使用场景 |
|---|---|---|
| `open_scope(resource, *, visa_library="@py", timeout_s=10.0, channel=CH1, vertical_scale_v=1.0, trigger_level_v=1.5)` | 创建台架对象。**不连接仪器**，只建本地对象 | 所有场景的入口 |
| `open()` | 打开 VISA 连接 | 不用 `with` 时手动调用 |
| `close()` | 关闭连接，不复位仪器 | 不用 `with` 时手动调用 |
| `__enter__` / `__exit__` | 支持 `with`，自动开/关 | 推荐写法 |
| `reconnect()` | 关掉重开，用于链路异常恢复 | 仪器无响应、超时后 |

**连接参数说明**

- `resource`：VISA 资源串。LAN 用 `TCPIP0::<ip>::INSTR`；裸 socket 是 `::5555::SOCKET`
  （**不推荐**，跨通道测量项会挂死，见 §7）。
- `visa_library="@py"`：走 pyvisa-py，**不需要装厂商 VISA**。设 `None` 则用系统默认 VISA。
- `channel`：默认观测通道，影响那些不显式传通道的方法。
- `vertical_scale_v` / `trigger_level_v`：`prepare()` 的默认值。

```python
# 不用 with 的写法（记得 try/finally）
scope = open_scope("TCPIP0::169.254.201.131::INSTR")
scope.open()
try:
    print(scope.identify())
finally:
    scope.close()
```

## 1.2 身份与状态

| 方法 | 含义 | 返回 |
|---|---|---|
| `identify()` | 读 `*IDN?`，返回一行身份串 | `"RIGOL TECHNOLOGIES,MSO5204,MS5A241002099,00.01.03.03.00"` |
| `identity`（属性） | 底层 VISA 资源标识，**不发 SCPI** | `"visa:TCPIP0::...::INSTR"` |
| `channel`（属性） | 当前默认通道号 | `1` |
| `last_error()` | 读并弹出仪器错误队列 | `(0, "No error")` |
| `driver`（属性） | 拿到底层 `Mso5204Driver`，直通原子层 | 见 §5 |

**为什么每次改完配置要查 `last_error()`**：SCPI 是"发出去就不管"的，参数被仪器拒绝时
不会报错，只会静默留在错误队列里。查一次能确认命令真的被接受了。

## 1.3 采集控制

| 方法 | 含义 | 使用场景 |
|---|---|---|
| `prepare(*, time_scale_s, channel=None, vertical_scale_v=None, trigger_level_v=None, trigger_slope=RISING, settle_s=0.9)` | 一次配好通道+时基+EDGE 触发，然后 `RUN` 并等待 | **最常用**。开始测量前调一次 |
| `split_channels(upper, lower, *, headroom=1.15, margin_divisions=0.4, divisions=8.0)` | **把两路波形分到上下半屏**，自动选量程和偏移 | 双通道对比，避免两路重叠 |
| `run()` | 连续采集 | 恢复采集 |
| `stop()` | 停止采集 | 需要稳定画面 |
| `single()` | 单次采集（武装，不等触发） | 抓单次事件 |
| `force_trigger()` | 强制触发一次 | 触发迟迟不来 |
| `select_channel(n)` | 切换默认通道，**不发 SCPI** | 换通道读数 |

```python
scope.prepare(time_scale_s=5e-5)  # 20us/div
scope.prepare(time_scale_s=1e-6, vertical_scale_v=0.5, trigger_level_v=1.0)
scope.prepare(time_scale_s=5e-5, settle_s=0)  # 不等，自己控制时机
```

`settle_s=0.9` 是等采集稳定；设 0 就不等（例如紧接自己 `stop()`）。

### 1.3.1 双通道上下分离：`split_channels()`

两路都以 `offset=0` 时会**完全重叠**在屏幕中间。这个方法读各路的 VMAX/VMIN，
自动算出互不重叠的量程与偏移，把 `upper` 放到上半屏、`lower` 放到下半屏。

```python
layout = scope.split_channels(upper=2, lower=1)  # CH2 在上，CH1 在下
print(layout.upper.scale_v, layout.upper.offset_v)
print(layout.lower.scale_v, layout.lower.offset_v)
```

**它是怎么算的**（实测规律，见 §7.2）：

```
屏幕格数 = (信号电压 + offset) / 量程
→ offset = 目标格数 × 量程 − 信号中心电压
```

1. 读该路 `VMAX`/`VMIN`，得到中心电压与峰峰幅度；
2. 选量程：`量程 ≥ 幅度 × headroom ÷ 每路可用格数`，在仪器档位表里取最小够用档；
3. 算偏移：上半屏目标 `+4 格`、下半屏 `−4 格`（8 格屏），代入上式。

| 参数 | 含义 | 默认 |
|---|---|---|
| `upper` / `lower` | 上半屏/下半屏放哪个通道（必须不同） | 必填 |
| `headroom` | 幅度安全系数，小于 1 会裁切，因此被拒绝 | `1.15` |
| `margin_divisions` | 每半屏预留边距（格），防止波形贴边 | `0.4` |
| `divisions` | 屏幕垂直格数 | `8.0` |

返回 `Mso5204TwoChannelLayout`，含 `upper`/`lower` 两个 `Mso5204ChannelPlacement`
（`channel`、`scale_v`、`offset_v`、`scale_changed`、`offset_changed`）。

**注意**：

- 两路**可以有不同的量程**（各自按自己的幅度选档），不会强行统一成同一个值。
- 某路无有效信号时按零幅度处理，用默认量程，仍会放到对应半屏。
- `upper` 与 `lower` 传同一通道会抛 `ValueError`。
- 某路所需格数超过可用半屏时抛 `ValueError`，提示调大 `headroom` 或减小 `margin`。
- 调完后建议 `screenshot()` 存证；仪器屏幕刷新有延迟，隔一会儿再截。

## 1.4 测量

| 方法 | 含义 | 使用场景 |
|---|---|---|
| `measure(item, channel=None)` | 读一个测量项，**无效值返回 None** | 读频率/幅值/占空比 |
| `measure_signal(channel=None)` | 一次读 7 项（频率/周期/占空比/Vpp/Vrms/上升/下降） | 要一整份快照 |
| `measure_delay(item, a, b)` | 跨通道延迟/相位，**自动配 A/B 源** | 两路相位差 |
| `measure_statistic(stat, item, channel=None)` | 统计值（最大/最小/平均/偏差/次数） | 看抖动、看极值 |

```python
freq = scope.measure("FREQuency")  # 字符串名
freq = scope.measure(Mso5204MeasurementItem.FREQUENCY)  # 枚举，等价
vpp = scope.measure("VPP", channel=2)  # 指定通道

snap = scope.measure_signal()
print(snap.frequency_hz, snap.vpp_v, snap.duty_cycle_percent)

delay = scope.measure_delay("FFDelay", 1, 2)  # CH1 到 CH2 的下降-下降延迟
```

`measure()` 返回 `None` 表示仪器给了无效哨兵 `9.9E+37`——**没有有效波形时就是这样**，
不要当成数值用。

## 1.5 波形读取

| 方法 | 含义 | 点数 | 使用场景 |
|---|---|---|---|
| `wave(channel=None, *, start=1, stop=1000, timeout_s=None)` | 屏幕波形（NORMal/BYTE） | ≤1000 | 看个大概 |
| `wave_raw(channel=None, *, start=None, stop=None, read_timeout_s=30.0)` | RAW 深存储 | 可达数百万 | **ns 级细节**（死区、上升沿） |
| `read_wave(...)` | 同 `wave()`，但直接返回可分析的 `Wave` | ≤1000 | 要算物理量 |
| `read_wave_raw(...)` | 同 `wave_raw()`，直接返回 `Wave` | 数百万 | 要算物理量 + 高分辨率 |

**选哪个**：只想知道频率占空比 → `measure()`；想看波形形状 → `wave()`；
要测 ns 级死区/边沿 → `read_wave_raw()`。

```python
wave = scope.read_wave()
print(wave.levels(), wave.period_s(), wave.duty_percent())

raw = scope.read_wave_raw(read_timeout_s=30.0)
print(len(raw), raw.x_increment_s)  # 4000000 点, 1.25e-10 s/点
```

`wave_raw` 内部会自动：等采集就绪 → `STOP` → 读数据 → 读 preamble → 恢复 `RUN`。
**不要自己在 RUN 状态下读 RAW**——实测会阻塞到超时（60s）。

## 1.6 截图与分析透传

| 方法 | 含义 |
|---|---|
| `screenshot(path, *, timeout_s=None)` | 存屏幕截图（BMP），返回字节数，目录自动创建 |
| `edge_offset_s(a, b, ...)` | 两路相位差（周期对齐） |
| `dead_time_s(a, b, *, direction=..., max_gap_s=None)` | 互补 PWM 死区 |

```python
size = scope.screenshot("out/wave.png")  # 实际是 BMP 内容
```

---

# 2. 常用层：`driver.operations`

**含义**：台架层之下的原语级封装，每个方法对应一组原子命令。
**使用场景**：不用 `Mso5204Scope`（比如已有自己的连接管理）、或需要更细的控制。

```python
from oscilloscopes.mso5204 import create_mso5204_visa_driver

driver = create_mso5204_visa_driver("TCPIP0::169.254.201.131::INSTR", visa_library="@py")
driver.open()
try:
    driver.operations.configure_edge_capture(config)
finally:
    driver.close()
```

## 2.1 配置类

| 方法 | 含义 | 关键点 |
|---|---|---|
| `configure_edge_capture(config: Mso5204EdgeCaptureConfig)` | 配置 EDGE 捕获（通道+时基+触发） | 一次发 9~12 条命令 |
| `configure_trigger(config: Mso5204TriggerConfig)` | 配置触发 | `None` 字段不动仪器；**扫描方式最后下发** |
| `configure_acquire(config: Mso5204AcquireConfig)` | 配置采集 | 平均次数必须配 `AVERAGE` 类型 |
| `configure_delay_sources(a, b)` | 配置跨通道延迟/相位的 A/B 源 | 发 4 条 `:MEASure:SETup:*` |

**为什么扫描方式最后下发**：`SINGle` 一旦下发会立即武装单次采集，
后续再设触发参数就把这次武装覆盖掉了。所以 `configure_trigger` 把它放最后。

```python
from oscilloscopes.mso5204 import Mso5204TriggerSweep
from oscilloscopes.wrapper import Mso5204TriggerConfig

scope.driver.operations.configure_trigger(
    Mso5204TriggerConfig(sweep=Mso5204TriggerSweep.SINGLE, edge_level_v=1.5)
)
```

## 2.2 测量类

| 方法 | 含义 | 无效时 |
|---|---|---|
| `measure_item(item, channel)` | 读一个测量项 | 返回 `None` |
| `measure_delay(item, a, b)` | 跨通道延迟/相位，**自动配源** | 返回 `None` |
| `measure_statistic(stat, item, channel)` | 统计项 | 返回 `None` |
| `measure_frequency/period/duty_cycle/vpp/vrms/rise_time/fall_time(channel)` | 单项快捷读法 | 抛异常 |
| `measure_signal(channel)` | 7 项快照 | 抛异常 |

**注意区别**：`measure_item` 系列**过滤无效值返回 None**；
`measure_frequency` 等旧快捷法不过滤，直接返回仪器原始值（可能是 `9.9E+37`）。
新代码用 `measure_item()`。

## 2.3 波形与辅助

| 方法 | 含义 |
|---|---|
| `read_screen_waveform(config) -> Mso5204Waveform` | 屏幕波形（≤1000 点） |
| `read_raw_waveform(config) -> Mso5204RawWaveform` | RAW 深存储；自动 STOP→读→RUN |
| `save_screenshot(path) -> int` | 存 BMP |
| `wait_acquired(*, timeout_s=6.0) -> bool` | 等采集就绪；**超时返回 False，不抛异常** |

```python
from oscilloscopes.wrapper import Mso5204RawWaveformConfig

if driver.operations.wait_acquired(timeout_s=6.0):
    raw = driver.operations.read_raw_waveform(Mso5204RawWaveformConfig(channel=1))
```

---

# 3. 分析层：`Wave` 与 `analysis.*`

**含义**：纯计算，把采样点变成物理量。**不做任何设备 I/O，不判 PASS/FAIL**。
**使用场景**：需要周期/占空比/边沿位置/相位差/死区这些仪器测量项给不出的量。

## 3.1 `Wave` 对象

| 成员 | 含义 | 返回 |
|---|---|---|
| `Wave(samples, x_increment_s, x_origin_s=0.0, channel=1)` | 直接构造 | — |
| `Wave.from_screen(w)` | 从 `Mso5204Waveform` 构造 | — |
| `Wave.from_raw(w)` | 从 `Mso5204RawWaveform` 构造 | — |
| `len(wave)` | 采样点数 | `int` |
| `wave.duration_s` | 总时长（秒） | `float` |
| `wave.time_at(i)` | 第 i 点的时间 | `float` |
| `levels()` | （低电平, 高电平） | `tuple[float, float]` |
| `denoise(window=5)` | 中值滤波，返回**新对象** | `Wave` |
| `crossings(level, *, rising=True)` | 穿越给定电平的**下标** | `list[int]` |
| `edges(*, rising=True)` | 边沿列表（下标+时间） | `list[Edge]` |
| `period_s()` | 周期（上升沿间隔中位数） | `float \| None` |
| `frequency_hz()` | 频率 | `float \| None` |
| `duty_percent()` | 高电平占比（%） | `float \| None` |

**三个反直觉但重要的设计**（都有实测依据）：

1. **`levels()` 用极值，不用分位数**。占空比 <10% 时 p90 仍落在低电平上，
   判据中点会退化成 0，边沿检测彻底失效——而死区/窄脉冲/Burst 恰好都是低占空比。
2. **`edges()` 对平信号返回空**。恒定直流极值相等，中点判据会把起点误判成穿越，
   凭空多一个边沿，`burst_pulse_count(直流)` 会返回 1。
3. **起点即高电平会被记为一个上升沿**（下标 0）。否则首脉冲被系统性漏掉。

```python
wave = scope.read_wave()
low, high = wave.levels()
mid = (low + high) / 2
print(wave.crossings(mid, rising=True))  # [0, 20, 40, ...] 下标
print(wave.period_s(), wave.frequency_hz(), wave.duty_percent())
```

## 3.2 分析函数

| 函数 | 含义 | 关键点 |
|---|---|---|
| `edge_offset_s(a, b, *, rising_a=True, rising_b=True, nth=0)` | 两路边沿时间差（B−A） | **按周期对齐**，不会带上整数个周期 |
| `dead_time_s(a, b, *, direction="a_fall_to_b_rise", max_gap_s=None)` | 互补 PWM 死区 | **取最小间隔**，避开跨周期误配 |
| `count_edges(wave, *, rising=True)` | 边沿计数 | — |
| `burst_pulse_count(wave)` | 脉冲串个数（上升沿数） | — |
| `edge_position_s(wave, *, rising=True, nth=0)` | 第 n 个边沿绝对时间 | 比较细调前后位移 |
| `high_level_v(wave)` / `low_level_v(wave)` | 高/低电平 | 等价 `levels()` |

**为什么 `edge_offset_s` 要"周期对齐"**：两路采集起点相位不同，
直接拿第 n 个边沿相减会凭空带上整数个周期。这里以 A 的边沿为基准，
在 B 里选**时间上最接近**的那个。

**为什么 `dead_time_s` 取最小值**：死区是每周期重复的最短间隔。
若某个 A 边沿后恰好跨过 B 的高电平区，配对会落到下一周期的 B 边沿，
得到远大于死区的值；这类异常只影响部分样本，取最小值仍能命中真实死区。

```python
from oscilloscopes.mso5204 import dead_time_s, edge_offset_s

w1, w2 = scope.read_wave(1), scope.read_wave(2)
print(edge_offset_s(w1, w2))  # 相位差（秒）
print(dead_time_s(w1, w2, direction="a_fall_to_b_rise"))
```

`direction` 只支持 `"a_fall_to_b_rise"` 和 `"a_rise_to_b_fall"`，
其他值抛 `ValueError`（不静默返回 None）。两路采样间隔不同时返回 `None`。

---

# 4. 模型层：`models.*`

**含义**：传参和接结果用的稳定类型。**都是纯数据，不访问仪器**。

## 4.1 枚举

| 枚举 | 取值 | 用途 |
|---|---|---|
| `Mso5204AnalogChannel` | `CH1..CH4` | 通道号 |
| `Mso5204AcquireType` | `NORMAL`, `AVERAGE`, `PEAK_DETECT`, `HIGH_RESOLUTION` | 采集模式 |
| `Mso5204MemoryDepth` | `AUTO`, `PTS_1K` … `PTS_200M` | 存储深度 |
| `Mso5204ChannelCoupling` | `DC`, `AC`, `GROUND` | 通道耦合 |
| `Mso5204BandwidthLimit` | `OFF`, `MHZ_20`, `MHZ_100` | 带宽限制 |
| `Mso5204TimebaseMode` | `YT`, `XY`, `ROLL` | 时基模式 |
| `Mso5204TriggerSlope` | `RISING`, `FALLING`, `EITHER` | 边沿斜率 |
| `Mso5204TriggerSweep` | `AUTO`, `NORMAL`, `SINGLE` | 触发扫描 |
| `Mso5204TriggerMode` | `EDGE`, `PULSE`, `RUNT`, `CAN`, `SPI` … 20 种 | 触发类型 |
| `Mso5204WaveformMode` | `NORMAL`, `MAXIMUM`, `RAW` | 波形读取模式 |
| `Mso5204WaveformFormat` | `BYTE`, `WORD`, `ASCII` | 传输编码 |
| `Mso5204MeasurementStatistic` | `MAXIMUM`, `MINIMUM`, `CURRENT`, `AVERAGE`, `DEVIATION`, `COUNT` | 统计类型 |

## 4.2 配置类

| 类 | 字段 | 用途 |
|---|---|---|
| `Mso5204EdgeCaptureConfig` | `channel`, `vertical_scale_v`, `time_scale_s`, `trigger_level_v`, `trigger_slope`, `coupling`, `probe_ratio`, `bandwidth_limit`, `vertical_offset_v`, `time_offset_s`, `acquire_type`, `average_count`, `trigger_sweep` | EDGE 捕获全配置，`None` = 不动 |
| `Mso5204TriggerConfig` | `mode`, `sweep`, `coupling`, `holdoff_s`, `edge_source`, `edge_slope`, `edge_level_v`, `noise_reject` | 触发配置 |
| `Mso5204AcquireConfig` | `acquire_type`, `average_count`, `memory_depth`, `anti_alias` | 采集配置 |
| `Mso5204RawWaveformConfig` | `channel`, `start`, `stop`, `read_timeout_s`, `acquire_timeout_s`, `stop_first`, `restart_run` | RAW 读取选项 |
| `Mso5204WaveformReadConfig` | `channel`, `start`, `stop`, `timeout_s` | 屏幕波形读取 |

`Mso5204RawWaveformConfig` 的 `stop_first` / `restart_run` 控制对仪器运行状态的
临时影响，默认都 `True`（停一下再恢复）。若仪器本来就在 `STOP`，可都设 `False`。

## 4.3 结果类

| 类 | 字段 |
|---|---|
| `Mso5204Identification` | `manufacturer`, `model`, `serial_number`, `software_version` |
| `Mso5204SystemError` | `code`, `message` |
| `Mso5204WaveformPreamble` | 10 个换算参数（`x_increment_s`, `y_increment_v`, …） |
| `Mso5204Waveform` | `preamble`, `samples`, `times_s` |
| `Mso5204RawWaveform` | `channel`, `samples`, `x_increment_s`, `x_origin_s`；有 `time_at(i)` |
| `Mso5204SignalMeasurements` | `frequency_hz`, `period_s`, `duty_cycle_percent`, `vpp_v`, `vrms_v`, `rise_time_s`, `fall_time_s` |
| `Edge` | `index`, `time_s` |

## 4.4 测量项枚举（41 个）

`Mso5204MeasurementItem`：

```
电压类：VMAX VMIN VPP VTOP VBASE VAMPLITUDE VAVERAGE VRMS
        OVERSHOOT PRESHOOT VUPPER VMID VLOWER
时间类：PERIOD FREQUENCY RISE_TIME FALL_TIME
        POSITIVE_WIDTH NEGATIVE_WIDTH POSITIVE_DUTY NEGATIVE_DUTY
        TIME_VMAX TIME_VMIN
面积类：AREA PERIOD_AREA
边沿类：POSITIVE_SLEW_RATE NEGATIVE_SLEW_RATE
        POSITIVE_PULSES NEGATIVE_PULSES POSITIVE_EDGES NEGATIVE_EDGES
统计类：VARIANCE PERIOD_VRMS
跨通道：RR_DELAY RF_DELAY FR_DELAY FF_DELAY
        RR_PHASE RF_PHASE FR_PHASE FF_PHASE
```

跨通道类（`*_DELAY` / `*_PHASE`）**必须给两个源**，且需先设 A/B 源——
用 `scope.measure_delay(item, a, b)` 或 `operations.measure_delay()` 会自动处理。

---

# 5. 原子层：官方 API（997 个方法）

**含义**：直接对应 MSO5204 Programming Guide 的全部命令，一条 SCPI 一个方法。
**使用场景**：便捷层没覆盖的能力（总线解码、数学运算、直方图、模板测试等）。
**约定**：构造对象不发命令；`_set()` 发一次写，`_get()` 发一次查询。

```python
scope.driver.channel.scale_set(1, 0.5)  # :CHANnel1:SCALe 0.5
scale = scope.driver.channel.scale_get(1)  # :CHANnel1:SCALe?
```

命名空间与规模：

| 命名空间 | 数量 | 内容 |
|---|---|---|
| `basic` | 6 | `autoscale` `clear` `run` `stop` `single` `force_trigger` |
| `common` | 15 | `*IDN?` `*RST` `*CLS` `*OPC` `*STB?` `*ESR?` 状态保存/恢复 |
| `acquire` | 11 | 采集类型、平均次数、存储深度、采样率 |
| `channel` | 22 | 显示、耦合、带宽、量程、偏移、探头、反相 |
| `timebase` | 18 | 主/延迟时基、偏移、参考点 |
| `trigger` | 17 | 边沿触发核心：模式、源、斜率、电平、释抑、耦合 |
| `trigger_advanced` | 134 | 脉宽/欠幅/斜率/超时/窗口/延迟/建立保持/第 N 边沿 |
| `trigger_protocol` | 120 | RS232 / I2C / SPI / CAN / LIN / FlexRay / I2S / MIL1553 |
| `measurement` | 38 | 41 个测量项、统计、阈值、延迟/相位源、光标位置 |
| `waveform` | 20 | 源、模式、格式、点数、preamble、数据传输 |
| `display` | 16 | 显示类型、余晖、亮度、栅格、**截图**、标尺 |
| `dvm` | 7 | 内置数字电压表 |
| `counter` | 12 | 内置频率计 |
| `cursor` | 56 | 光标测量（手动/追踪/自动） |
| `histogram` | 19 | 直方图分析 |
| `math` | 65 | 数学运算、FFT、滤波 |
| `mask` | 17 | Pass/Fail 模板测试 |
| `search` | 54 | 波形搜索 |
| `bus` | 126 | 总线解码（并行/I2C/SPI/RS232/CAN/LIN/…） |
| `logic_analyzer` | 23 | 数字通道（LA） |
| `reference` | 17 | 参考波形 |
| `save_load` | 16 | 保存/加载设置、波形、图片 |
| `record` | 10 | 波形录制与回放 |
| `source` | 54 | 内置 AWG 任意波 |
| `trace` | 1 | AWG 任意波轨迹 |
| `power` | 16 | 电源分析 |
| `bodeplot` | 28 | 伯德图 |
| `lan` | 25 | 网络配置 |
| `quick` | 2 | 快捷键 |
| `system` | 32 | 错误队列、时间日期、蜂鸣器、选件、通道数、设置存取 |

> ⚠️ **不要碰这几组**（需选件许可，无许可时会弹窗阻塞）：
> `source`（AWG）、`trace`、`power`、`bodeplot`、`mask`。
> 已确认本台 MSO5204 **无 AWG 许可**。

完整签名清单：见 §附录。

## 5.1 常用原子调用示例

```python
d = scope.driver

# 通道
d.channel.display_set(1, True)
d.channel.coupling_set(1, "DC")  # 或 Mso5204ChannelCoupling.DC
d.channel.scale_set(1, 0.5)
d.channel.offset_set(1, 0.0)
d.channel.bandwidth_limit_set(1, "20M")

# 时基
d.timebase.mode_set("MAIN")
d.timebase.main_scale_set(5e-5)
d.timebase.main_offset_set(0.0)

# 触发
d.trigger.mode_set("EDGE")
d.trigger.edge_source_set("CHANnel1")  # 必须 SCPI 记号，不能传整数
d.trigger.edge_slope_set("POSitive")
d.trigger.edge_level_set(1.5)
d.trigger.sweep_set("AUTO")

# 采集
d.acquire.type_set("AVERages")
d.acquire.averages_set(16)
d.acquire.memory_depth_set("1M")

# 波形
d.waveform.source_set("CHANnel1")
d.waveform.mode_set("RAW")
d.waveform.format_set("BYTE")
data = d.waveform.data_get(timeout_s=30.0)

# 状态
d.system.error_get()
d.system.analog_channel_count_get()
```

**易错点**：`edge_source_set` 不接受整数 `1`，必须是 `"CHANnel1"`——
官方校验会拒绝整数。用 `operations.configure_trigger()` 则自动转换。

---

# 6. 底层：`_internal.*`

**含义**：支撑层，让整包能独立拷走（不依赖宿主工程）。
**使用场景**：一般不用；除非要自己实现别的仪器驱动。

| 模块 | 内容 |
|---|---|
| `_internal.errors` | `OscilloscopeError`（基类）、`TransportError`、`OscilloscopeTimeout`（继承 TransportError）、`InstrumentProtocolError` |
| `_internal.scpi` | `ScpiSession`：一条命令一次写、一次查询一个响应；支持 IEEE488.2 数据块 |
| `_internal.visa` | `VisaTransport`：PyVISA 字节收发 |
| `_internal.transport` | `ByteTransport` 抽象 |
| `_internal.deadline` | `OperationDeadline`：一次操作的总时间预算 |

异常都继承 `OscilloscopeError`，可以统一捕获：

```python
from oscilloscopes._internal import OscilloscopeError, OscilloscopeTimeout

try:
    scope.read_wave_raw()
except OscilloscopeTimeout:
    print("读超时：采集可能未就绪")
except OscilloscopeError as exc:
    print("其他仪器错误:", exc)
```

---

# 7. 实测注意事项（踩过的坑）

1. **跨通道延迟项在裸 socket 上会挂死**。`RR/RF/FR/FF_DELAY` 只能走
   VXI-11（`::INSTR`）；`::5555::SOCKET` 会超时。
2. **强制输出后读原始波形会触发 VISA I/O 错误**并污染链路。
   强制态（TZ）请只读测量项（`VMAX`/`VMIN`），它们由前端硬件算，不受影响。
3. **RUN 状态下读 RAW 会阻塞到超时**（实测 60s）。必须先 `STOP`——
   `read_raw_waveform()` 已自动处理。
4. **VXI-11 链路表会被中断的进程占满**（`error creating link: 3`），
   需等超时或重启示波器。`srpwm_bench/clear_vxi11_links.py` 可清理。
5. **仪器无效测量返回 `9.9E+37`**，不是 0 也不是异常。
   `measure_item()` 会转成 `None`。
6. **IP 会变**（DHCP/自动 IP）。用 `srpwm_bench/find_scope.py` 重新发现。
   这类仪器**不响应 ping**，要探端口（111 或 5555）。

## 7.1 ⚠️ 占空比单位：仪器返回的是**比值**，不是百分比

**这是实测确认的行为不一致，使用前必须知道。**

`MEASure:ITEM? PDUTy` 实测返回 `2.4300E-01`（= 0.243），且 `PDUTy + NDUTy = 1.0`：

```
:MEASure:ITEM? PDUTy,CHANnel1   ->  2.4300E-01    (0.243)
:MEASure:ITEM? NDUTy,CHANnel1   ->  7.5700E-01    (0.757)
                                    和 = 1.0      ← 证明是比值
```

同一信号用波形自算：`Wave.duty_percent()` → **24.4 %**。
即 `0.243 × 100 = 24.3 %`，两者一致。

**问题**：`Mso5204SignalMeasurements.duty_cycle_percent` 字段名带 `percent`，
但装的是仪器原值（比值 0~1）。`operations.measure_duty_cycle()` 同样返回比值。

| 取值方式 | 返回值 | 单位 |
|---|---|---|
| `scope.measure("PDUTy")` | `0.243` | **比值 0~1** |
| `scope.measure_signal().duty_cycle_percent` | `0.243` | **比值 0~1** |
| `scope.read_wave().duty_percent()` | `24.4` | 百分比 0~100 |

**建议**：需要百分比时用 `Wave.duty_percent()`，或自己对仪器值 `×100`。
本次未改动库的既有行为（会破坏已发布字段语义和既有测试），仅在文档与示例中标注。

`FREQuency` / `PERiod` / `VPP` / `VRMS` 等单位正常，不受此问题影响。

## 7.2 垂直偏移的符号方向与坐标换算

调 `channel.offset_set()` 时方向容易搞反。实测规律（像素级验证）：

```
屏幕格数 = (信号电压 + offset) / 量程        以屏幕中心为 0，正格数在上
```

即：

- **offset 取正值 → 波形上移**
- **offset 取负值 → 波形下移**

实测数据（2 V/div，3.5V 方波）：

| offset 设置 | 波形实际位置 |
|---|---|
| `0 V` | 居中 |
| `+2 V` | 偏上约 1 格 |
| `−2 V` | 偏下约 1 格 |
| `+4 V` | 偏上约 2 格 |

**反解目标位置**：想让信号中心落在第 `d` 格，则 `offset = d × 量程 − 信号中心电压`。

`split_channels()` 就是按这个公式算的：上半屏取 `+4 格`、下半屏取 `−4 格`（8 格屏）。

**一个自然的结果**：两路量程不同时，同样的 offset 值对应的格数不同——
所以分离两路必须**先定量程、再算偏移**，不能简单地把一路 `+2V`、另一路 `−2V`。

**另外注意**：`offset_set()` 的校验允许 ±100 V，但硬件实际受 ±5 格限制。
超出范围时仪器不会报错，只是回读值仍是设定值而波形已移出屏幕；
所以判断是否真的移出屏幕要看截图或波形数据，不能只看回读。

---

# 8. 附录：官方 API 完整签名

共 997 个方法。以下按命名空间列出，方法名为公开 API，签名中 `...` 表示省略默认值。

## basic — 顶层运行控制（6）

```
autoscale()
clear()
run()
stop()
single()
force_trigger()
```

## common — IEEE488.2 通用命令（15）

```
clear_status()                      event_status_enable_get() -> int
event_status_enable_set(value)      event_status_register_get() -> int
identity_get() -> Mso5204Identification
operation_complete()                operation_complete_get() -> int
reset()                             self_test_get() -> int
service_request_enable_get() -> int service_request_enable_set(value)
state_recall(index)                 state_save(index)
status_byte_get() -> int            wait()
```

## acquire — 采集系统（11）

```
anti_alias_get() -> bool            anti_alias_set(enabled: bool)
averages_get() -> int               averages_set(count: int)
logic_memory_depth_get() -> float   logic_sample_rate_get() -> float
memory_depth_get() -> float         memory_depth_set(depth)
sample_rate_get() -> float          type_get() -> str
type_set(acquire_type)
```

## channel — 模拟通道（22）

```
bandwidth_limit_get(channel) -> str         bandwidth_limit_set(channel, value)
coupling_get(channel) -> str                coupling_set(channel, value)
display_get(channel) -> bool                display_set(channel, enabled)
invert_get(channel) -> bool                 invert_set(channel, enabled)
offset_get(channel) -> float                offset_set(channel, offset_v)
position_get(channel) -> float              position_set(channel, offset_v)
probe_ratio_get(channel) -> float           probe_ratio_set(channel, ratio)
scale_get(channel) -> float                 scale_set(channel, scale_v)
time_calibration_get(channel) -> float      time_calibration_set(channel, delay_s)
units_get(channel) -> str                   units_set(channel, units)
vernier_get(channel) -> bool                vernier_set(channel, enabled)
```

## timebase — 水平时基（18）

```
delay_enabled_get() -> bool         delay_enabled_set(enabled)
delay_offset_get() -> float         delay_offset_set(offset_s)
delay_scale_get() -> float          delay_scale_set(scale_s)
main_offset_get() -> float          main_offset_set(offset_s)
main_scale_get() -> float           main_scale_set(scale_s)
mode_get() -> str                   mode_set(mode)
reference_mode_get() -> str         reference_mode_set(mode)
reference_position_get() -> int     reference_position_set(position)
vernier_get() -> bool               vernier_set(enabled)
```

## trigger — 边沿触发核心（17）

```
coupling_get() -> str               coupling_set(coupling)
edge_level_get() -> float           edge_level_set(level)
edge_slope_get() -> str             edge_slope_set(slope)
edge_source_get() -> str            edge_source_set(source)
holdoff_get() -> float              holdoff_set(seconds)
mode_get() -> str                   mode_set(mode)
noise_reject_get() -> bool          noise_reject_set(enabled)
status_get() -> str                 sweep_get() -> str
sweep_set(sweep)
```

## measurement — 自动测量（38）

```
source_set/get                          item_enable(item, a?, b?)
item_clear(item)                        item_get(item, a?, b?) -> float
mode_set/get                            area_set/get
threshold_source_set / threshold_default
threshold_max_set/get  threshold_mid_set/get  threshold_min_set/get
all_measure_source_set/get
phase_source_a_set/get   phase_source_b_set/get
delay_source_a_set/get   delay_source_b_set/get
statistics_display_set/get   statistics_reset
statistics_item_enable(...)  statistics_item_get(...) -> float
cursor_a_position_set/get   cursor_b_position_set/get
category_set/get
```

## waveform — 波形传输（20）

```
source_set/get                      mode_set/get
format_set/get                      points_set/get
start_set/get                       stop_set/get
data_get(*, timeout_s) -> bytes     preamble_get() -> Mso5204WaveformPreamble
x_increment_get  x_origin_get  x_reference_get
y_increment_get  y_origin_get  y_reference_get
```

## display — 显示（16）

```
clear()                             type_set/get
persistence_set/get                 waveform_brightness_set/get
grid_set/get                        grid_brightness_set/get
screenshot_get(*, timeout_s) -> bytes      rulers_set/get
color_grade_set/get
```

## dvm — 数字电压表（7） / counter — 频率计（12）

```
[ dvm ] enabled_set/get   mode_set/get   source_set/get   current_get() -> float
[ counter ] enabled_set/get   mode_set/get   source_set/get
            digits_set/get    statistics_enabled_set/get
            totalize_clear()  current_get() -> float
```

## system — 系统（32）

```
error_get() -> Mso5204SystemError   analog_channel_count_get() -> int
beeper_set/get                      date_set/get   time_set/get
language_set/get                    power_on_mode_set/get
option_install(text)                option_status_get(type)
options_uninstall_all()             modules_get() -> tuple[int, ...]
key_press(key)                      key_increase/decrease(key, value?)
setup_set/get(*, timeout_s) -> bytes        locked_set/get
autoscale_key_enabled_set/get       screen_saver_time_set/get
auxiliary_output_set/get            horizontal_grid_count_get
gpib_address_set/get
```

## 其余命名空间的说明

篇幅原因，以下命名空间只列规模；调用模式与上面完全一致
（`_set()` 写、`_get()` 读），签名可用 `help()` 或见源码：

| 命名空间 | 数量 | 用途 |
|---|---|---|
| `trigger_advanced` | 134 | 脉宽/欠幅/斜率/超时/窗口/延迟/建立保持/第 N 边沿触发 |
| `trigger_protocol` | 120 | RS232/I2C/SPI/CAN/LIN/FlexRay/I2S/MIL1553 协议触发 |
| `bus` | 126 | 总线解码 |
| `math` | 65 | 数学运算、FFT、滤波 |
| `cursor` | 56 | 光标测量 |
| `source` | 54 | AWG ⚠️ 需许可 |
| `search` | 54 | 波形搜索 |
| `bodeplot` | 28 | 伯德图 ⚠️ 需许可 |
| `lan` | 25 | 网络配置 |
| `logic_analyzer` | 23 | 数字通道 |
| `histogram` | 19 | 直方图 |
| `reference` | 17 | 参考波形 |
| `mask` | 17 | 模板测试 ⚠️ 需许可 |
| `power` | 16 | 电源分析 ⚠️ 需许可 |
| `save_load` | 16 | 保存/加载 |
| `record` | 10 | 录制回放 |
| `quick` | 2 | 快捷键 |
| `trace` | 1 | AWG 轨迹 ⚠️ 需许可 |

查看任意方法的签名：

```python
import inspect

print(inspect.signature(scope.driver.cursor.mode_set))
# 或
help(scope.driver.cursor)
```
