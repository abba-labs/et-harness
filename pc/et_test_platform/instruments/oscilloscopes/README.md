# oscilloscopes — 自包含示波器仪器库

RIGOL **MSO5204** 示波器驱动库。整包拷贝即可使用，不依赖宿主工程任何代码。

- 台架仪器：RIGOL MSO5204（4 通道，序列号 MS5A241002099，固件 00.01.03.03.00）
- 外部依赖：**只有 `PyVISA` + `pyvisa-py`**（详见 [§1 环境依赖](#1-环境依赖先装这个)）

---

## 目录

1. [环境依赖（先装这个）](#1-环境依赖先装这个)
2. [架构分层](#2-架构分层)
3. [各文件夹与文件含义](#3-各文件夹与文件含义)
4. [调用链路](#4-调用链路)
5. [应用时参考哪些示例](#5-应用时参考哪些示例)
6. [怎么调用：三个层次](#6-怎么调用三个层次)
7. [实测注意事项](#7-实测注意事项)
8. [测试](#8-测试)

---

## 1. 环境依赖（先装这个）

### 必须安装

```bash
pip install pyvisa pyvisa-py
```

| 包 | 版本要求 | 作用 |
|---|---|---|
| `PyVISA` | >= 1.14 | VISA 抽象层（接口） |
| `pyvisa-py` | >= 0.7 | 纯 Python 的 VISA 实现（真正干活的） |

**两个都必须装。** 实测：只装 `pyvisa` 不装 `pyvisa-py`，连接时会报

```
ValueError: Could not locate a VISA implementation.
            Install either the IVI binary or pyvisa-py.
```

装了 `pyvisa-py` 后，**不需要** RIGOL 官方驱动，也**不需要** NI-VISA。

也装 `PyYAML`、`pyserial`？**不需要** —— 那是仓库其它模块要的，本库只用 PyVISA。

### Python 版本

**>= 3.10**（代码用了 `X | Y` 联合类型语法）。本机实测 3.13.3 可用。

### 安装方式

**方式 A：直接在包目录安装（推荐）**

```bash
cd oscilloscopes
pip install -e .          # 会自动装 pyvisa + pyvisa-py
```

装完在**任意目录**都能 `import oscilloscopes`。

**方式 B：不安装，加到 path**

```python
import sys

sys.path.insert(0, "/path/to/parent_of_oscilloscopes")
from oscilloscopes.wrapper import open_scope
```

**方式 C：离线移植**（公司电脑装不了软件）

全套装好才 **2.7 MB**，把 `site-packages` 里这几个拷到新机器即可：

```
pyvisa/            pyvisa_py/            typing_extensions.py
pyvisa-*.dist-info/  pyvisa_py-*.dist-info/  typing_extensions-*.dist-info/
```

或用 wheel 离线安装：

```bash
# 有网的机器
pip download pyvisa pyvisa-py -d ./wheels
# 目标机器
pip install --no-index --find-links ./wheels pyvisa pyvisa-py
```

### 网络前提

电脑要和示波器**同网段**。当前台架：

```
本机网卡 : 169.254.200.138/16
示波器   : 169.254.201.131   （TCPIP / VXI-11）
```

**这类仪器不响应 ping**，要探端口验证：

```python
import socket

sock = socket.socket()
sock.settimeout(1)
print(sock.connect_ex(("169.254.201.131", 111)) == 0)  # 111 = VXI-11
print(sock.connect_ex(("169.254.201.131", 5555)) == 0)  # 5555 = 裸 SCPI
```

IP 由 DHCP 分配，重启后会变。发现工具见 `srpwm_bench/find_scope.py`（在仓库内，不在本包内）。

---

## 2. 架构分层

**核心原则：厂商代码与二次封装严格分目录，看路径就知道来源。**

```
┌─────────────────────────────────────────────────────┐
│  你的测试代码 / 台架脚本                              │
└───────────────────────┬─────────────────────────────┘
                        │ 推荐从这里进
┌───────────────────────▼─────────────────────────────┐
│  wrapper/        二次封装（本仓库新增）               │
│    scope.py      台架对象：with 生命周期、split_channels│
│    operations.py 补充动作：测量过滤/RAW/截图           │
│    analysis.py   波形分析：Wave、死区、相位差          │
│    models.py     补充配置：Trigger/Acquire/RAW Config │
│    driver.py     把封装 Operations 装到厂商 Driver    │
└───────────────────────┬─────────────────────────────┘
                        │ 依赖
┌───────────────────────▼─────────────────────────────┐
│  mso5204/        厂商 MSO5204 驱动（原厂，未改动）     │
│    driver.py     聚合 30 个命名空间 / 997 个原子方法   │
│    controls/     31 个模块，一条 SCPI 命令一个方法     │
│    models.py     厂商枚举与数据类                     │
│    operations.py 厂商常用组合                         │
│    observer.py   SignalObserver 适配                  │
│    connection.py VISA 资源 → Driver 工厂              │
└───────────────────────┬─────────────────────────────┘
                        │ 依赖
┌───────────────────────▼─────────────────────────────┐
│  _internal/      通信支撑（为自包含而内联）            │
│    scpi.py       SCPI 会话：命令写入 / 响应解析         │
│    visa.py       VISA 字节收发（唯一用 pyvisa 的地方）  │
│    transport.py  字节传输抽象                          │
│    deadline.py   操作超时预算                          │
│    errors.py     异常层次                              │
└─────────────────────────────────────────────────────┘
```

**独立契约（不属于上面任何一层）**

```
interface.py   型号中立契约：SignalObserver / SignalEdge
               ↑ 由 mso5204/observer.py 实现
               ↑ 由 scheduling/fixtures.py、stimer 用例消费
```

---

## 3. 各文件夹与文件含义

### 3.1 `mso5204/` — 厂商驱动（原厂代码，未改动）

原厂 `mso5204/` 目录**只被改动过 3 行 import**（为自包含），其余逐字节一致。

| 文件 | 行数 | 含义 |
|---|---|---|
| `driver.py` | 92 | **聚合入口**。`Mso5204Driver(session)` 构造 30 个原子命名空间（`channel`/`trigger`/`waveform`…）。构造不发任何 SCPI |
| `controls/` | 30 个模块 + `__init__.py` | **原子 API**。一条 SCPI 命令对应一个方法，如 `channel.py` 的 `scale_set/scale_get`。覆盖手册全部命令组 |
| `models.py` | 247 | **厂商稳定类型**：16 个枚举（`Mso5204MeasurementItem`、`Mso5204TriggerSlope`…）+ 8 个数据类（`Mso5204Waveform`、`Mso5204EdgeCaptureConfig`…） |
| `operations.py` | 243 | **厂商常用组合**（10 个公开方法）：`configure_edge_capture`（一次配好通道+时基+触发）、`read_screen_waveform`、`measure_signal` |
| `validation.py` | 318 | **参数校验**：通道范围、量程合法性、SCPI 记号规范。非法输入在**发命令前**就拒绝 |
| `observer.py` | 121 | **契约适配器**：把 `SignalObserver` 契约方法翻译成 MSO5204 命令 |
| `connection.py` | 27 | **工厂**：`create_mso5204_visa_driver("TCPIP0::…")` → 未打开的 Driver |

**哪些是原厂原子 API**：`driver.<命名空间>.<方法>`，共 **997 个**（运行时含继承的实际数量）。
命名空间规模：`bus` 126、`trigger_advanced` 134、`trigger_protocol` 120、`math` 65、`cursor` 56、
`source` 54、`search` 54、`measurement` 38、`system` 32、`channel` 22 …

### 3.2 `wrapper/` — 二次封装（本仓库新增）

| 文件 | 行数 | 含义 |
|---|---|---|
| `scope.py` | 412 | **台架对象** `Mso5204Scope`：`open_scope()` 工厂、`with` 自动开关连接、`prepare/split_channels/measure/read_wave*` 等一站式方法 |
| `operations.py` | 261 | **补充动作**：`Mso5204WrapperOperations`（继承厂商 `Mso5204Operations`）。测量过滤、跨通道、RAW 深存储、截图 |
| `analysis.py` | 218 | **波形分析**（纯计算）：`Wave` 数据类 + `edge_offset_s`/`dead_time_s`/`burst_pulse_count` 等函数 |
| `models.py` | 84 | **补充配置**：`Mso5204TriggerConfig`、`Mso5204AcquireConfig`、`Mso5204RawWaveformConfig`、`Mso5204TwoChannelLayout` 等 |
| `driver.py` | 21 | **装配**：`install_wrapper_operations(driver)` 把厂商 Driver 的 `operations` 换成封装版 |
| `__init__.py` | 47 | 统一导出上述所有公开名字 |

**注意**：`wrapper/operations.py` 里的类是**继承**厂商 `Mso5204Operations` 的，
所以 `driver.operations` 同时能用到两层的方法（厂商 10 个 + 封装 9 个）。

### 3.3 `_internal/` — 通信支撑

**存在的唯一目的**：让整包不依赖宿主工程。这些文件原本在仓库的 `core/` 和 `communication/` 下。

| 文件 | 行数 | 含义 |
|---|---|---|
| `scpi.py` | 161 | SCPI 会话：一条命令一次写、一次查询读完整响应；支持 IEEE488.2 二进制块 |
| `visa.py` | 174 | VISA 字节收发。**全库唯一 `import pyvisa` 的地方** |
| `transport.py` | 40 | `ByteTransport` 抽象基类 |
| `deadline.py` | 71 | `OperationDeadline`：一次操作的总时间预算，嵌套调用只用剩余时间 |
| `errors.py` | 27 | 异常层次：`OscilloscopeError` 基类 + 3 个子类 |
| `__init__.py` | 23 | 统一导出 |

### 3.4 辅助目录

| 目录 | 文件 | 含义 |
|---|---|---|
| `demo/` | `demos.py` (404) + `__init__.py` | **15 个可运行示例**，每个自包含、互不依赖 |
| `mock_tests/` | `test_smoke.py` (493)、`test_analysis.py` (275) | **无硬件 mock 测试**共 53 项；用脚本化 Transport 验证 SCPI 拼装，不接真机 |
| `doc/` | `API.md` (684) | **完整接口参考**，含 997 个官方方法清单 |

### 3.5 根目录文件

| 文件 | 含义 |
|---|---|
| `interface.py` | **型号中立契约**（原厂）。放最外层是因为它不属于任何型号——`signal_generators/` 有对称的 `interface.py` |
| `__init__.py` | 只导出契约三件套（`SignalEdge`/`SignalObservation`/`SignalObserver`） |
| `pyproject.toml` | 打包配置。包名 `oscilloscope-lib`，`package-dir` 把本目录映射成顶层 `oscilloscopes` |
| `README.md` | 本文 |
| `.gitignore` | 保持目录干净（`__pycache__`、`.pytest_cache` 等） |

---

## 4. 调用链路

### 4.1 一次典型调用的完整路径

以 `scope.read_wave_raw()` 为例：

```
你的代码
  scope.read_wave_raw()
    │
    ├─ wrapper/scope.py          Mso5204Scope.read_wave_raw()
    │    └─ 构造 Mso5204RawWaveformConfig
    │
    ├─ wrapper/operations.py     Mso5204WrapperOperations.read_raw_waveform()
    │    ├─ 校验参数（validation.py）
    │    ├─ driver.channel.display_set()      ┐
    │    ├─ driver.waveform.source_set()      │ 都是原子 SCPI
    │    ├─ driver.basic.stop()               │
    │    ├─ driver.waveform.data_get()        ┘
    │    └─ 换算成物理量 → Mso5204RawWaveform
    │         │
    │         └─ mso5204/controls/waveform.py   ← 原子 API
    │              └─ _internal/scpi.py          ← 拼 SCPI 文本
    │                   └─ _internal/visa.py     ← pyvisa 收发字节
    │
    └─ wrapper/analysis.py       Wave.from_raw() → 可分析对象
```

### 4.2 对象构造链路

```
open_scope("TCPIP0::…")
  └─ create_mso5204_visa_driver()          mso5204/connection.py
       ├─ VisaTransport(resource)          _internal/visa.py    ← 尚未打开
       ├─ ScpiSession(transport)           _internal/scpi.py
       └─ Mso5204Driver(session)           mso5204/driver.py
            └─ 构造 30 个 Control 对象      mso5204/controls/*
  └─ install_wrapper_operations(driver)    wrapper/driver.py
       └─ driver.operations = Mso5204WrapperOperations(driver)
```

**构造阶段零副作用**：不打开仪器、不发任何 SCPI。真正连接发生在 `scope.open()`（或 `with` 进入时）。

### 4.3 `driver.operations` 的双层继承

```
Mso5204WrapperOperations   (wrapper/operations.py)   ← 9 个补充方法
        │ 继承
Mso5204Operations          (mso5204/operations.py)   ← 10 个厂商方法
```

所以 `scope.driver.operations.measure_item()`（封装）和
`scope.driver.operations.measure_signal()`（厂商）都能用。

### 4.4 契约链路（另一条独立路径）

```
interface.py  SignalObserver（Protocol）
      ↑ 实现
mso5204/observer.py  Mso5204SignalObserver
      ↓ 调用
mso5204/driver.py 原子 API

消费方（仓库内，不在本包内）：
  scheduling/fixtures.py              ← 台架注入
  test_cases/stimer/test_stimer_p*.py ← 测试用例
  framework_validation/…/test_signal_observer.py ← 契约测试
```

这条路径的价值：将来换别的牌子示波器，只要它实现 `SignalObserver`，用例一行都不用改。

---

## 5. 应用时参考哪些示例

**全部示例都在 `demo/demos.py`，一共 15 个。** 每个都是**完整可独立运行**的代码，不互相依赖。

| 编号 | 示例 | 对应接口层 |
|---|---|---|
| 1 | 连接与身份识别 | 台架 |
| 2 | 基础测量（频率/幅值/占空比） | 台架 + 常用 |
| 3 | 屏幕波形读取与物理量分析 | 台架 + 分析 |
| 4 | RAW 深存储读取（ns 级细节） | 台架 + 分析 |
| 5 | 触发配置 | 常用 |
| 6 | 采集配置（平均/存储深度） | 常用 |
| 7 | 完整测量快照 | 台架 |
| 8 | 跨通道延迟/相位 | 常用 |
| 9 | 统计测量 | 常用 |
| 10 | 屏幕截图存证 | 常用 |
| 11 | 错误队列检查 | 原子 |
| 12 | 异常处理 | 底层 |
| 13 | 官方原子 API | 原子 |
| 14 | 双通道波形比较 | 分析 |
| 15 | **双通道上下分离（split_channels）** | 台架 |

### 我要做 X，该看哪个示例

| 需求 | 看示例 |
|---|---|
| 第一次连上示波器 | **1** |
| 测频率/幅值/占空比 | **2**、7 |
| 想看波形形状、算周期 | **3** |
| 测 ns 级死区、上升沿 | **4**、14 |
| 改触发条件 | **5** |
| 降噪（多次平均） | **6** |
| 两路相位/死区对比 | **8**、14 |
| 两路波形重叠看不清 | **15** ← split_channels |
| 存图留证 | **10** |
| 命令好像没生效 | **11** |
| 连接失败怎么处理 | **12** |
| 手册上有但库没封装的命令 | **13** |

### 怎么读这些示例

每个示例都是**独立的函数**，直接抄里面代码即可。例如示例 15 的核心：

```python
with open_scope(SCOPE_RESOURCE) as scope:
    scope.prepare(time_scale_s=5e-5)
    layout = scope.split_channels(upper=2, lower=1)  # CH2 上、CH1 下
    print(layout.upper.offset_v, layout.lower.offset_v)
```

---

## 6. 怎么调用：三个层次

### 6.1 推荐入口（90% 场景）

```python
from oscilloscopes.wrapper import open_scope

with open_scope("TCPIP0::169.254.201.131::INSTR") as scope:
    print(scope.identify())  # 确认连对仪器
    scope.prepare(time_scale_s=5e-5)  # 配通道+时基+触发并启动
    freq = scope.measure("FREQuency")  # 读测量项（无效返回 None）
    wave = scope.read_wave()  # 采回即可分析
    print(wave.levels(), wave.period_s(), wave.duty_percent())
    scope.screenshot("out.bmp")  # 存图留证
```

`with` 块退出时**自动关闭连接**，异常时也不会漏。

### 6.2 双通道对比（重点场景）

两路都以 `offset=0` 时会**完全重叠**在屏幕中间。`split_channels()` 自动解决：

```python
with open_scope("TCPIP0::…::INSTR") as scope:
    scope.prepare(time_scale_s=5e-5)
    layout = scope.split_channels(upper=2, lower=1)  # CH2 上半屏、CH1 下半屏
    print(layout.upper.scale_v, layout.upper.offset_v)
    print(layout.lower.scale_v, layout.lower.offset_v)

    w1, w2 = scope.read_wave(1), scope.read_wave(2)
    print(edge_offset_s(w1, w2))  # 相位差
    print(dead_time_s(w1, w2))  # 互补死区
```

它内部：读该路 `VMAX`/`VMIN` → 按幅度选量程 → 算让信号落在指定半屏的偏移。
参数 `headroom`（默认 1.15）留安全余量，`margin_divisions`（默认 0.4）防止贴边。

### 6.3 直接用厂商原子 API

```python
from oscilloscopes.mso5204 import create_mso5204_visa_driver

driver = create_mso5204_visa_driver("TCPIP0::…::INSTR", visa_library="@py")
driver.open()
try:
    driver.channel.scale_set(1, 1.0)  # :CHANnel1:SCALe 1
    driver.trigger.edge_source_set("CHANnel1")  # 注意必须 SCPI 记号，不能传整数
    print(driver.measurement.item_get("VPP", "CHANnel1"))
finally:
    driver.close()
```

### 6.4 运行示例

```bash
cd oscilloscopes
pip install -e .
python -m oscilloscopes.demo.demos --list   # 看清单
python -m oscilloscopes.demo.demos 4        # 跑示例 4
python -m oscilloscopes.demo.demos all      # 全部跑一遍
```

运行前把 `demo/demos.py` 顶部的 `SCOPE_RESOURCE` 改成你的示波器地址。

---

## 7. 实测注意事项

1. **跨通道延迟项**（`RR/RF/FR/FF_DELAY`）在裸 socket `:5555::SOCKET` 上会挂起超时，
   只能走 VXI-11（`::INSTR`）。
2. **强制输出后读原始波形**（`:WAVeform:DATA?`）会触发 VISA I/O 错误并污染链路；
   强制态请只读测量项（`VMAX`/`VMIN`），它们由前端硬件计算，不受影响。
3. **RUN 状态下读 RAW 会阻塞到超时**（实测 60s）。必须先 `STOP` ——
   `read_raw_waveform()` 已自动处理。
4. **VXI-11 链路表**可能被中断的进程占满（`error creating link: 3`），
   需等待超时或重启示波器。
5. **仪器无效测量返回 `9.9E+37`**，不是 0 也不是异常。`measure_item()` 会转成 `None`。
6. **占空比单位**：`MEASure:ITEM? PDUTy` 实测返回**比值**（如 `0.243`，且 P+N=1.0），
   而 `Mso5204SignalMeasurements.duty_cycle_percent` 字段名写的是 percent。
   需要百分比时用 `Wave.duty_percent()`（返回 24.4），或对仪器值 `×100`。
   详见 `doc/API.md` §7.1。
7. **垂直偏移符号**：`offset` 取**正值时波形上移**，负值下移。
   换算关系：`屏幕格数 = (信号电压 + offset) / 量程`。详见 `doc/API.md` §7.2。
8. **不要碰需选件许可的组**：`source`(AWG)、`power`、`bodeplot`、`trace`、`mask`
   在无许可证时会弹窗阻塞。本台 MSO5204 无 AWG 许可。

---

## 8. 测试

```bash
cd oscilloscopes
pytest                 # 53 项 mock 测试，不接硬件
```

覆盖内容：SCPI 命令拼装是否正确、参数校验是否在发命令前拒绝非法值、
异常层次、波形分析算法（电平/边沿/周期/占空比/死区/相位）、
`split_channels` 的选档与偏移计算。

这些测试**跟着包走**，移植后可用于自检，不需要真实示波器。

---

## 附：设计约定

- **零副作用构造**：`create_*` / `Mso5204Driver(...)` 只建立本地对象，不打开仪器、不发 SCPI。
- **显式连接**：必须自己调 `open()` / `close()`；不自动扫描或选择设备。
- **一个方法一条命令**：`controls/` 里的公开 API 只发送一条 SCPI，不追加等待或判定。
- **判定权在调用方**：本库不含 PASS/FAIL 阈值，只回读仪器事实。
- **异常统一**：全部继承 `oscilloscopes._internal.errors.OscilloscopeError`：

| 异常 | 含义 |
|---|---|
| `TransportError` | 连接失败、未打开、短写、底层 VISA 异常 |
| `OscilloscopeTimeout` | 操作总时间预算耗尽（继承 `TransportError`） |
| `InstrumentProtocolError` | 仪器已响应，但返回内容不符合命令契约 |
