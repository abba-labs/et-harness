# oscilloscopes — 自包含示波器仪器库

RIGOL **MSO5204** 示波器驱动库。整包拷走即可用，不依赖任何宿主工程代码，只需要 PyVISA。

## 快速开始

```bash
pip install -e .
```

```python
from oscilloscopes.mso5204 import open_scope

with open_scope("TCPIP0::169.254.201.131::INSTR") as scope:
    print(scope.identify())
    scope.prepare(time_scale_s=5e-5)  # 配置通道/时基/触发并启动采集
    print("频率:", scope.measure("FREQuency"), "Hz")  # 仪器自测
    wave = scope.read_wave()  # 采回即可分析
    print(wave.levels(), wave.period_s(), wave.duty_percent())
    raw = scope.read_wave_raw()  # RAW 深存储，ns 级细节
    print(len(raw), "点 @", raw.x_increment_s, "s/点")
    scope.screenshot("shot.bmp")
```

纯 LAN 环境用 `visa_library="@py"`（默认）走 pyvisa-py，不需要装厂商 VISA。

## 三层接口

| 层 | 入口 | 用途 |
|---|---|---|
| 原子 | `driver.channel.scale_set(1, 1.0)` | 429 个方法，一条命令对应一个 API，完全对应手册 |
| 常用 | `driver.operations.*` | 测量读取、触发/采集配置、波形读取、截图 |
| 台架 | `open_scope() -> Mso5204Scope` | `with` 生命周期 + 一站式便捷方法 |
| 分析 | `Wave` / `analysis.*` | 纯计算：电平、边沿、周期、占空比、相位、死区 |

**常用层（`operations`）**

| 方法 | 说明 |
|---|---|
| `measure_item(item, ch)` | 读单个测量项；**过滤无效值哨兵 9.9E+37 → None** |
| `measure_delay(item, a, b)` | 跨通道延迟/相位；**自动先配 A/B 源** |
| `measure_statistic(stat, item, ch)` | 统计测量项（MAX/MIN/AVG/DEV/CNT） |
| `configure_trigger(config)` | 触发配置；None 字段不动仪器，**扫描方式最后下发** |
| `configure_acquire(config)` | 采集配置；平均次数必须配 AVERage 类型 |
| `read_raw_waveform(config)` | RAW 深存储；**先 STOP 再读、读完恢复 RUN** |
| `save_screenshot(path)` | 存屏幕截图（BMP） |
| `wait_acquired(timeout_s)` | 等采集就绪；超时返回 False 不抛异常 |

**台架层（`Mso5204Scope`）**：`prepare` / `measure` / `measure_delay` / `measure_signal` /
`wave` / `wave_raw` / `read_wave` / `read_wave_raw` / `screenshot` / `stop` / `run` / `single` /
`force_trigger` / `last_error` / `reconnect` / `edge_offset_s` / `dead_time_s`，
以及 `driver` 属性直通原子层。

**分析层（`Wave`）**：把采样点变成物理量，纯计算不含判定。

| 方法 / 函数 | 说明 |
|---|---|
| `levels()` | 低/高电平。**用极值不用分位数**——低占空比时分位数法会让判据中点退化 |
| `denoise(window=5)` | 中值滤波抑制单点毛刺。**毛刺会污染极值法电平**，分析前建议先滤 |
| `edges(rising=)` / `crossings(level)` | 边沿定位。**起点即高电平会被记为上升沿**，避免漏掉首脉冲 |
| `period_s()` / `frequency_hz()` | 周期取相邻上升沿间隔的中位数 |
| `duty_percent()` | 高电平采样点占比 |
| `edge_offset_s(a, b)` | 两路相位差，**按周期对齐**，不会带上整数个周期 |
| `dead_time_s(a, b, direction=)` | 互补 PWM 死区，**取最小间隔**避开跨周期误配 |
| `burst_pulse_count(wave)` | 脉冲串个数 |
| `edge_position_s(wave, nth=)` | 第 n 个边沿绝对时间，用于比较细调前后位移 |

构造方式：`scope.read_wave()` / `scope.read_wave_raw()` 直接返回 `Wave`，
也可用 `Wave.from_screen(w)`、`Wave.from_raw(w)` 自行构造。

实测：同一 10kHz 方波，`Wave.frequency_hz()` 与仪器自带 `FREQuency` 测量项偏差 **0.000%**。

### 当前台架仪器

| 项 | 值 |
|---|---|
| 型号 | RIGOL MSO5204（4 通道） |
| 序列号 | MS5A241002099 |
| 固件 | 00.01.03.03.00 |
| 地址 | `169.254.201.131`（TCPIP/VXI-11） |

地址按 DHCP/自动 IP 分配，重启后可能变化；连接前先用
`srpwm_bench/find_scope.py` 重新发现。

## 目录结构

```text
oscilloscopes/
├── interface.py                # 型号中立的 SignalObserver / SignalEdge 契约
├── _internal/                  # 自包含支撑层（SCPI、VISA、Deadline、异常）
│   ├── errors.py
│   ├── deadline.py
│   ├── transport.py
│   ├── scpi.py
│   └── visa.py
├── mso5204/
│   ├── connection.py           # VISA 资源 → Driver 工厂
│   ├── driver.py               # 聚合全部原子控制命名空间
│   ├── models.py               # 稳定枚举 / 配置 / 结果模型
│   ├── validation.py           # 参数校验
│   ├── operations.py           # 常用多步组合（EDGE 捕获、测量、波形读取）
│   ├── observer.py             # SignalObserver 适配器
│   └── controls/               # 35 个原子 SCPI 控制模块
└── tests/                      # 不接硬件的冒烟测试
```

## 设计约定

- **零副作用构造**：`create_*` / `Mso5204Driver(...)` 只建立本地对象，不打开仪器、不发 SCPI。
- **显式连接**：必须自己调 `open()` / `close()`；不自动扫描或选择设备。
- **一个方法一条命令**：`controls/` 里的公开 API 只发送一条 SCPI，不追加等待或判定。
- **判定权在调用方**：本库不含 PASS/FAIL 阈值，只回读仪器事实。
- **不触碰需选件许可的组**：`source`(AWG)、`power`、`bodeplot`、`trace` 在无许可证时会弹窗阻塞，
  默认不要调用。

## 异常

全部异常继承 `oscilloscopes._internal.errors.OscilloscopeError`：

| 异常 | 含义 |
|---|---|
| `TransportError` | 连接失败、未打开、短写、底层 VISA 异常 |
| `OscilloscopeTimeout` | 操作总时间预算耗尽（继承 `TransportError`） |
| `InstrumentProtocolError` | 仪器已响应，但返回内容不符合命令契约 |

## 实测注意事项（MSO5204）

1. **跨通道延迟项**（`RR/RF/FR/FF_DELAY`）在裸 socket `:5555::SOCKET` 上会挂起超时，
   只能走 VXI-11（`::INSTR`）。
2. **强制输出后读原始波形**（`:WAVeform:DATA?`）会触发 VISA I/O 错误并污染链路；
   强制态请只读测量项（`VMAX`/`VMIN`），它们由前端硬件计算，不受影响。
3. **VXI-11 链路表**可能被中断的进程占满（`error creating link: 3`），
   需等待超时或重启示波器；裸 socket 仍可用但跨通道项不可用。
4. 示波器重启后 IP 可能变化（DHCP/自动 IP），连接前先确认地址。

## 测试

```bash
pytest          # 不接硬件的冒烟测试，验证 import、SCPI 拼装和参数校验
```
