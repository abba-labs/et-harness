# MCU 全 IP 自动化测试平台方案

**主题：** 基于 `pytest + labgrid + PyVISA + sigrok/Saleae + J-Link/OpenOCD` 的真实硬件/FPGA 自动化测试平台，并与 Renode 软件仿真平台统一
**适用对象：** MCU 芯片公司、SDK 团队、FPGA 原型验证团队、芯片 bring-up/EVT/DVT 验证团队
**核心目标：** 同一套 pytest 用例层，既能跑 Renode 虚拟平台，也能跑真实 MCU/FPGA 原型板；Renode 不具备的能力在同一份用例中明确报 `unsupported / xfail / skip / fail`，而不是另写一套测试。

---

## 0. 一句话结论

推荐把整个平台设计成：

```text
同一套 pytest 测试用例
        ↓
统一 Target / DUT 抽象接口
        ↓
能力矩阵 capability matrix
        ↓
RenodeBackend / HardwareBackend / FpgaBackend
        ↓
虚拟 MCU / 真实 MCU / FPGA 原型板 / 仪器
```

其中：

```text
pytest 用例层：必须统一
固件测试协议：必须统一
固件源码：尽量统一
固件二进制：可以按 Renode / 真实板 / FPGA 分别构建
Renode 不支持的能力：在同一份用例中显式 xfail / skip / fail
真实硬件平台：用于完整 IP、真实波形、真实电气、真实功耗、真实时序验证
Renode 平台：用于快速回归、软件路径验证、异常路径验证、虚拟外设验证
```

这套方案的关键不是“某一个工具很强”，而是**分层抽象**做得好。
只要 pytest 用例不直接依赖 Renode、J-Link、示波器或串口，而是依赖统一的 `Target API`，那么 Renode、真实 MCU、FPGA 原型板都可以作为不同 backend 接入。

---

## 1. 需求边界

你的需求不是普通的 SDK 单元测试，而是 **MCU 全 IP 自动化验证平台**。

它至少包含以下对象：

```text
被测对象：
- 真实 MCU 芯片
- FPGA 原型板
- EVB 开发板
- socket board
- Renode 虚拟 MCU / 虚拟板卡

调试/烧录：
- J-Link
- DAP-Link
- ST-Link
- OpenOCD
- pyOCD
- 厂商私有烧录工具

外部仪器：
- 示波器
- 逻辑分析仪
- 可编程电源
- 万用表
- 电子负载
- 信号源
- CAN/LIN/SPI/I2C/UART 协议分析仪
- 继电器/电源控制板
- DAQ/USB GPIO 板

测试软件：
- pytest
- labgrid
- PyVISA
- sigrok / Saleae API
- J-Link Commander / OpenOCD
- Renode
- CI 系统
- 报告系统
```

这类平台的难点不在于“写几个 Python 脚本”，而在于：

```text
1. 测试用例怎么统一？
2. 真实硬件和 Renode 怎么统一？
3. 固件层是否统一？
4. 平台不支持的能力怎么表达？
5. 仪器测量结果怎么抽象？
6. 板卡资源怎么管理？
7. 全 IP 测试如何组织？
8. 如何接入 CI 和长期回归？
```

---

## 2. 工具栈角色说明

### 2.1 pytest：测试用例层

pytest 负责：

```text
- 测试用例组织
- fixture 管理
- 参数化
- 断言
- marker
- skip / xfail
- JUnit XML / Allure 报告输出
- 命令行参数扩展
```

在本方案里，pytest 只应该写测试意图，不应该直接写底层工具细节。

错误示例：

```python
def test_uart():
    subprocess.run(["JLinkExe", "..."])
    ser = serial.Serial("COM3")
    ser.write(b"test uart\n")
```

推荐示例：

```python
def test_uart_echo(target, firmware):
    image = firmware.build("uart_echo")
    target.flash(image)
    target.reset()
    target.console.expect("TEST_READY")
    target.console.send("uart_echo 0x55")
    target.console.expect("TEST_PASS:uart_echo")
```

pytest 用例只调用 `target`，不关心 `target` 是 Renode、真实板卡还是 FPGA。

---

### 2.2 labgrid：板卡资源和远程控制层

labgrid 更像是 embedded board farm 的资源管理层，适合处理：

```text
- 板卡占用
- 串口
- 电源
- 复位
- 远程测试机
- 多块板卡共享
- pytest 集成
- board farm 管理
```

它可以解决的问题：

```text
- 哪块板现在空闲？
- 某块板对应哪个串口？
- 某块板对应哪个 J-Link？
- 某块板对应哪个电源通道？
- 多个测试任务如何避免抢同一块板？
- 测试机和板卡不在同一台 PC 上怎么办？
```

但是，labgrid 不是仪器自动化全家桶。
示波器、电源、逻辑分析仪等仍然建议用 PyVISA、Saleae API、sigrok 或厂商 SDK 接入。

---

### 2.3 PyVISA：仪器控制层

PyVISA 主要负责控制支持 VISA/SCPI 的仪器：

```text
- 示波器
- 可编程电源
- 万用表
- 电子负载
- 信号源
- 频谱仪
- 其他测试测量设备
```

典型用途：

```text
- 设置示波器通道、触发、时基、电压档位
- 读取 PWM 频率、占空比、上升沿、峰峰值
- 控制电源输出电压、限流、开关
- 读取电流、电压、功耗曲线
- 控制信号源输出 ADC 测试输入
- 保存波形截图和 CSV
```

示例抽象：

```python
class Scope:
    def measure_pwm(self, channel: str) -> "PwmMeasurement":
        ...
```

pytest 用例不应该直接写 SCPI 命令，而应该调用抽象后的仪器 API。

---

### 2.4 sigrok / Saleae：逻辑分析和协议解码层

逻辑分析仪用于验证：

```text
- SPI 时序
- I2C ACK/NACK
- UART 波特率
- CAN/LIN 帧
- GPIO 中断响应
- DMA 触发后的外设波形
- 外设协议边界条件
```

两条路线：

```text
开源路线：sigrok / pulseview / sigrok-cli
商业常用路线：Saleae Logic 2 + Automation API
```

推荐抽象：

```python
class LogicAnalyzer:
    def capture(self, channels, duration_ms): ...
    def decode_spi(self, mosi, miso, clk, cs): ...
    def decode_i2c(self, sda, scl): ...
    def export_csv(self, path): ...
```

pytest 用例只关心解码结果，不直接关心仪器厂商。

---

### 2.5 J-Link / OpenOCD / pyOCD：烧录和调试访问层

这一层负责：

```text
- 烧录固件
- 擦除 Flash
- 复位芯片
- halt / run
- 读写寄存器
- 读写内存
- 读取芯片 ID
- 低层 bring-up 辅助
```

常见 backend：

```text
SEGGER J-Link Commander / JLinkGDBServer
OpenOCD telnet / TCL / GDB
pyOCD Python API
厂商私有 downloader
```

推荐抽象：

```python
class Programmer:
    def flash(self, image: str): ...
    def reset(self): ...
    def halt(self): ...
    def run(self): ...
    def read32(self, addr: int) -> int: ...
    def write32(self, addr: int, value: int): ...
```

上层 `HardwareTarget` 调用 `Programmer`，pytest 用例不直接调用 JLinkExe/OpenOCD。

---

### 2.6 Renode：软件仿真 / 虚拟硬件层

Renode 适合：

```text
- 虚拟 MCU / 虚拟板卡运行固件
- 启动流程验证
- UART/GPIO/Timer 等基础外设行为验证
- RTOS / shell / protocol stack 测试
- bootloader 软件流程测试
- CI 快速回归
- 多节点系统仿真
- 故障注入和异常路径测试
```

Renode 不适合替代：

```text
- ADC 精度
- DAC 输出电压
- OPAMP/COMP 模拟行为
- HRTIM 死区真实波形
- 低功耗电流
- 电源上下电真实时序
- 晶振起振
- PLL 抖动
- 信号完整性
- EMC/ESD
```

Renode 在统一架构里不是“另一套测试系统”，而是 `Target API` 的一个 backend：

```python
class RenodeTarget(Target):
    def flash(self, image):
        self.monitor.run(f"sysbus LoadELF @{image}")

    def reset(self):
        self.monitor.run("machine Reset")
        self.monitor.run("start")
```

---

## 3. 总体架构设计

### 3.1 分层架构

推荐架构：

```text
┌──────────────────────────────────────────────┐
│ CI / 调度层                                  │
│ Jenkins / GitLab CI / GitHub Actions          │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│ pytest 测试用例层                             │
│ tests/test_uart.py, test_pwm.py, test_adc.py  │
└───────────────────────┬──────────────────────┘
                        │
┌───────────────────────▼──────────────────────┐
│ Target / DUT 抽象层                           │
│ flash/reset/console/measure/register/require │
└──────────────┬──────────────────────┬────────┘
               │                      │
┌──────────────▼──────────────┐ ┌─────▼──────────────────┐
│ RenodeBackend               │ │ Hardware/FpgaBackend    │
│ .repl/.resc/virtual UART    │ │ labgrid/J-Link/PyVISA   │
└──────────────┬──────────────┘ └─────┬──────────────────┘
               │                      │
┌──────────────▼──────────────┐ ┌─────▼──────────────────┐
│ Renode 虚拟 MCU/虚拟外设     │ │ 真实 MCU/FPGA/外部仪器  │
└─────────────────────────────┘ └────────────────────────┘
```

核心原则：

```text
pytest 用例层不感知底层 backend。
Renode、真实硬件、FPGA 都实现同一套 Target API。
```

---

### 3.2 三种目标平台

#### 3.2.1 RenodeTarget

用于软件仿真：

```text
- 加载 .repl 平台描述
- 加载 .resc 启动脚本
- 加载 ELF
- 连接虚拟 UART
- 读写虚拟寄存器
- 访问虚拟 GPIO/PWM/Timer 状态
- 对不支持的真实仪器能力报 unsupported
```

#### 3.2.2 HardwareTarget

用于真实芯片/开发板：

```text
- J-Link/OpenOCD 烧录
- 真实 reset / power cycle
- pyserial 连接串口
- PyVISA 控制示波器、电源、万用表、电子负载
- Saleae/sigrok 控制逻辑分析仪
- JTAG/SWD 读写寄存器
```

#### 3.2.3 FpgaTarget

用于 FPGA 原型板：

```text
- FPGA bitstream 下载
- MCU 固件加载
- UART/JTAG/SWD 连接
- FPGA 板载寄存器访问
- 外部仪器测量真实 IO
- 可能需要处理 FPGA 原型频率与真实芯片不同的问题
```

---

## 4. pytest 用例层必须统一

### 4.1 不推荐的方式

不要这样组织：

```text
tests_renode/
├── test_uart.py
├── test_gpio.py

tests_hardware/
├── test_uart.py
├── test_gpio.py
```

这会导致：

```text
1. 两套用例逐渐分裂
2. 修改一个测试要改两份
3. Renode 和硬件测试结果难以对齐
4. 测试覆盖无法统一统计
5. 后续接 FPGA 会变成第三套用例
```

### 4.2 推荐的方式

只保留一套测试：

```text
tests/
├── test_uart.py
├── test_gpio.py
├── test_timer.py
├── test_pwm.py
├── test_adc.py
├── test_spi.py
├── test_i2c.py
├── test_dma.py
├── test_flash.py
├── test_can.py
└── test_bootrom.py
```

运行时选择 target：

```bash
pytest tests/ --target renode --unsupported=xfail
pytest tests/ --target real_evb --unsupported=fail
pytest tests/ --target fpga_proto --unsupported=fail
```

---

## 5. Target API 设计

### 5.1 基础接口

建议定义统一接口：

```python
class Target:
    name: str
    capabilities: set[str]

    def flash(self, image: str) -> None:
        ...

    def reset(self) -> None:
        ...

    def power_on(self) -> None:
        ...

    def power_off(self) -> None:
        ...

    def power_cycle(self) -> None:
        ...

    @property
    def console(self) -> "Console":
        ...

    def read_register(self, addr: int) -> int:
        ...

    def write_register(self, addr: int, value: int) -> None:
        ...

    def read_pin(self, pin: str) -> int:
        ...

    def set_pin(self, pin: str, value: int) -> None:
        ...

    def measure_pwm(self, channel: str) -> "PwmMeasurement":
        ...

    def capture_logic(self, config: dict) -> "LogicCapture":
        ...

    def require(self, capability: str) -> None:
        ...
```

### 5.2 Console 接口

```python
class Console:
    def send(self, line: str) -> None:
        ...

    def expect(self, text: str, timeout: float = 5.0) -> None:
        ...

    def expect_regex(self, pattern: str, timeout: float = 5.0) -> str:
        ...

    def expect_value(self, key: str, timeout: float = 5.0) -> float:
        ...
```

### 5.3 仪器测量结果对象

```python
from dataclasses import dataclass

@dataclass
class PwmMeasurement:
    freq_hz: float
    duty_percent: float
    vpp: float | None = None
    rise_time_ns: float | None = None
    fall_time_ns: float | None = None

@dataclass
class CurrentMeasurement:
    avg_ma: float
    peak_ma: float | None = None
    min_ma: float | None = None
    samples: list[float] | None = None
```

测试用例不应该关心示波器具体品牌，只关心 `PwmMeasurement`。

---

## 6. 能力矩阵 capability matrix

### 6.1 为什么需要能力矩阵？

Renode 和真实硬件能力不同：

```text
Renode 有虚拟 UART，但没有真实示波器。
Renode 可模拟 GPIO 状态，但不能测真实电压。
真实硬件能测 ADC 精度，但可能没有某个虚拟故障注入能力。
FPGA 原型可能有 UART/GPIO，但没有真实低功耗特性。
```

因此，不应该通过写两套用例解决，而是通过能力矩阵解决。

---

### 6.2 示例：renode.yaml

```yaml
target: renode
type: sil
capabilities:
  console: true
  register_access: true
  virtual_uart: true
  virtual_gpio: true
  gpio_observe: true
  timer_interrupt: true
  pwm_measurement: false
  scope: false
  logic_analyzer: false
  power_supply: false
  programmable_voltage_source: false
  current_measurement: false
  analog_accuracy: false
  fault_injection: true
```

### 6.3 示例：real_evb.yaml

```yaml
target: real_evb
type: hil
capabilities:
  console: true
  register_access: true
  virtual_uart: false
  virtual_gpio: false
  gpio_observe: true
  timer_interrupt: true
  pwm_measurement: true
  scope: true
  logic_analyzer: true
  power_supply: true
  programmable_voltage_source: true
  current_measurement: true
  analog_accuracy: true
  fault_injection: false
```

### 6.4 示例：fpga_proto.yaml

```yaml
target: fpga_proto
type: fpga
capabilities:
  console: true
  register_access: true
  gpio_observe: true
  timer_interrupt: true
  pwm_measurement: true
  scope: true
  logic_analyzer: true
  power_supply: true
  programmable_voltage_source: false
  current_measurement: false
  analog_accuracy: false
  fault_injection: false
notes:
  clock_scale: 0.25
  real_low_power_not_available: true
```

---

## 7. Renode 不支持能力时怎么处理？

建议提供统一命令行策略：

```bash
pytest --target renode --unsupported=skip
pytest --target renode --unsupported=xfail
pytest --target renode --unsupported=fail
```

含义：

```text
skip：平台不支持就跳过，适合日常快速回归
xfail：平台不支持就记为预期失败，适合报告中显式体现缺口
fail：平台不支持就失败，适合平台能力验收
```

建议默认：

```text
Renode 日常 CI：unsupported=xfail
Renode 冒烟 CI：unsupported=skip
真实硬件全量测试：unsupported=fail
FPGA 原型测试：unsupported=fail 或 xfail，视阶段而定
```

实现示例：

```python
class UnsupportedCapability(Exception):
    pass

class Target:
    def require(self, capability: str):
        if not self.capabilities.get(capability, False):
            raise UnsupportedCapability(capability)
```

在 pytest fixture 中统一处理：

```python
def handle_unsupported(request, capability):
    mode = request.config.getoption("--unsupported")
    reason = f"Target does not support capability: {capability}"

    if mode == "skip":
        pytest.skip(reason)
    elif mode == "xfail":
        pytest.xfail(reason)
    elif mode == "fail":
        pytest.fail(reason)
```

---

## 8. 统一 pytest 用例示例

### 8.1 UART 测试

UART 这类测试最容易统一，因为 Renode 和真实硬件都可以通过 console 交互。

```python
def test_uart_echo(target, firmware):
    image = firmware.build("uart_echo")

    target.flash(image)
    target.reset()

    target.console.expect("TEST_READY", timeout=5)

    target.console.send("uart_echo 0x55")
    target.console.expect("TEST_PASS:uart_echo", timeout=5)
```

Renode：

```text
flash = sysbus LoadELF
reset = machine Reset + start
console = virtual UART
```

真实硬件：

```text
flash = J-Link/OpenOCD
reset = reset pin / power cycle
console = pyserial
```

pytest 用例完全不变。

---

### 8.2 GPIO 输出测试

```python
def test_gpio_output_high(target, firmware):
    image = firmware.build("gpio_output")

    target.flash(image)
    target.reset()

    target.console.expect("TEST_READY")
    target.console.send("gpio_set PA0 1")
    target.console.expect("TEST_PASS:gpio_set")

    target.require("gpio_observe")

    level = target.read_pin("PA0")
    assert level == 1
```

Renode：

```text
read_pin = 读虚拟 GPIO 模型状态
```

真实硬件：

```text
read_pin = USB GPIO / DAQ / 逻辑分析仪 / 板卡回环
```

---

### 8.3 PWM 测试

```python
def test_pwm_1khz_50_percent(target, firmware):
    image = firmware.build("pwm_basic")

    target.flash(image)
    target.reset()

    target.console.expect("TEST_READY")

    target.console.send("pwm_start CH1 1000 50")
    target.console.expect("TEST_PASS:pwm_start")

    target.require("pwm_measurement")

    m = target.measure_pwm("CH1")

    assert 990 <= m.freq_hz <= 1010
    assert 48 <= m.duty_percent <= 52
```

Renode：

```text
如果虚拟 PWM 模型支持测量，则返回行为级结果。
如果不支持，则 xfail/skip/fail。
```

真实硬件：

```text
PyVISA 控制示波器读取频率、占空比、上升沿。
```

---

### 8.4 ADC 精度测试

```python
def test_adc_single_1v(target, firmware):
    target.require("programmable_voltage_source")
    target.require("analog_accuracy")

    image = firmware.build("adc_single")

    target.flash(image)
    target.reset()

    target.console.expect("TEST_READY")

    target.analog.set_voltage("ADC_IN0", 1.000)

    target.console.send("adc_read ADC_IN0")
    voltage = target.console.expect_value("ADC_VOLTAGE")

    assert 0.995 <= voltage <= 1.005
```

Renode：

```text
通常不支持 programmable_voltage_source 和 analog_accuracy。
同一条用例会被标记为 xfail/skip/fail。
```

真实硬件：

```text
信号源/电压源输出 1.000V。
固件采样 ADC。
pytest 解析采样结果。
```

---

### 8.5 低功耗测试

```python
def test_stop_mode_current(target, firmware):
    target.require("power_supply")
    target.require("current_measurement")

    image = firmware.build("low_power_stop")

    target.flash(image)
    target.reset()

    target.console.expect("TEST_READY")
    target.console.send("enter_stop")

    current = target.power.measure_current(duration_ms=1000)

    assert current.avg_ma < 0.1
```

Renode：

```text
没有真实电源电流，通常 xfail/skip。
```

真实硬件：

```text
可编程电源或电流计采样真实电流。
```

---

## 9. 固件层是否需要？

### 9.1 结论

**需要。大多数 MCU IP 测试必须需要芯片固件。**

pytest 跑在 PC 上，它不能直接让 MCU 内部外设工作。
要测 UART、GPIO、Timer、PWM、SPI、I2C、ADC、DMA、CAN、Flash 等 IP，通常必须让运行在芯片上的固件配置寄存器、处理中断、触发外设动作、输出结果。

固件在平台里的角色是：

```text
DUT 内部的 test agent / test firmware
```

pytest 的角色是：

```text
外部测试控制器 / 测试调度器 / 仪器控制器 / 结果判定器
```

职责边界：

| 动作 | 固件负责 | pytest 负责 |
|---|---:|---:|
| 配置 UART/SPI/I2C/Timer/ADC/DMA 寄存器 | 是 | 否 |
| 处理中断 | 是 | 否 |
| 启动 PWM 输出 | 是 | 否 |
| 启动 ADC 采样 | 是 | 否 |
| DMA memory compare | 是 | 可辅助 |
| 烧录固件 | 否 | 是 |
| 复位/上下电 | 否 | 是 |
| 控制示波器 | 否 | 是 |
| 控制电源 | 否 | 是 |
| 控制逻辑分析仪 | 否 | 是 |
| 保存波形/报告 | 否 | 是 |
| 最终 PASS/FAIL 判定 | 局部 | 是 |

一句话：

```text
固件负责“让芯片做事”。
pytest 负责“控制平台并验证这件事是否正确”。
```

---

### 9.2 哪些测试可以不需要固件？

少数测试可以不需要自定义固件：

```text
1. BootROM 测试
   - 上电进入 BootROM
   - UART/CAN/USB 下载协议
   - ROM 应答校验

2. JTAG/SWD 直接寄存器测试
   - 复位后读 CHIP_ID
   - 读默认寄存器值
   - 读 option bytes / fuse / efuse

3. 板级连通性测试
   - JTAG boundary scan
   - reset pin / boot pin / power rail 测试

4. 纯电源时序测试
   - 芯片保持 reset
   - 只测电源轨时序、上电电流、晶振输出
```

但对于 **全 IP 功能测试**，固件基本不可避免。

---

## 10. 固件层如何统一？

### 10.1 三个层次

```text
固件测试协议：必须统一
固件源码：尽量统一
固件二进制：可以不同
```

### 10.2 固件测试协议必须统一

建议所有测试固件统一输出：

```text
TEST_READY
TEST_START:<case>
TEST_PASS:<case>
TEST_FAIL:<case>:<reason>
TEST_DONE
```

命令式 shell 示例：

```text
uart_echo 0x55
gpio_set PA0 1
pwm_start CH1 1000 50
adc_read ADC_IN0
spi_transfer 0x9F
dma_memcpy 1024
flash_erase_write 0x08020000 4096
```

pytest 只解析统一协议。

### 10.3 固件源码尽量统一

推荐目录：

```text
firmware_tests/
├── common/
│   ├── test_protocol.c
│   ├── test_shell.c
│   ├── test_assert.c
│   ├── test_log.c
│   └── test_utils.c
├── cases/
│   ├── test_uart.c
│   ├── test_gpio.c
│   ├── test_timer.c
│   ├── test_pwm.c
│   ├── test_adc.c
│   ├── test_spi.c
│   ├── test_i2c.c
│   ├── test_dma.c
│   ├── test_flash.c
│   └── test_can.c
├── boards/
│   ├── board_renode.c
│   ├── board_real_evb.c
│   └── board_fpga_proto.c
├── linker/
│   ├── renode.ld
│   ├── real_evb.ld
│   └── fpga_proto.ld
├── startup/
├── sdk/
└── main.c
```

### 10.4 固件二进制不一定完全同一个

理想：

```text
同一个 app.elf 同时跑 Renode 和真实硬件。
```

现实：

```text
同一套源码，不同 board config / linker / startup / clock config。
```

例如：

```bash
make BOARD=renode TEST=uart
make BOARD=real_evb TEST=uart
make BOARD=fpga_proto TEST=uart
```

不同 binary 是可接受的，只要满足：

```text
1. 被测 SDK driver 是同一套
2. 测试 case 源码是同一套
3. 测试协议是同一套
4. board 层差异被限制在 boards/、linker/、startup/ 中
```

---

## 11. 固件测试协议设计

### 11.1 最小协议

```c
void test_pass(const char *name)
{
    printf("TEST_PASS:%s\r\n", name);
}

void test_fail(const char *name, const char *reason)
{
    printf("TEST_FAIL:%s:%s\r\n", name, reason);
}

void test_ready(void)
{
    printf("TEST_READY\r\n");
}
```

### 11.2 命令式测试固件

建议固件启动后进入 test shell：

```text
TEST_READY
> uart_echo 0x55
TEST_PASS:uart_echo
> pwm_start CH1 1000 50
TEST_PASS:pwm_start
> adc_read ADC_IN0
ADC_VOLTAGE:1.002
TEST_PASS:adc_read
```

优点：

```text
1. 一个固件可以覆盖多个 case
2. pytest 可以精确控制测试步骤
3. 适合仪器联动
4. 适合异常路径测试
```

缺点：

```text
1. 固件 shell 需要维护
2. 复杂 IP 可能仍需独立测试固件
```

### 11.3 独立测试固件

对于复杂测试，也可以一个 case 一个固件：

```text
uart_echo.elf
gpio_output.elf
pwm_basic.elf
adc_accuracy.elf
dma_memcpy.elf
```

优点：

```text
1. 简单清晰
2. 每个固件职责单一
3. 出问题容易定位
```

缺点：

```text
1. 编译数量多
2. 测试耗时可能增加
```

### 11.4 推荐策略

```text
基础 IP：命令式 test shell
复杂 IP/边界条件：独立测试固件
BootROM/低功耗/特殊复位：独立测试流程
```

---

## 12. 全 IP 测试组织方式

### 12.1 不建议一个大固件测所有 IP

不推荐：

```text
all_ip_test.elf
```

问题：

```text
1. 一个 IP 挂死影响后续所有测试
2. 失败定位困难
3. 不利于并行
4. 不利于选择性回归
5. 测试结果粒度太粗
```

### 12.2 推荐按 IP 和 feature 拆分

示例：

```text
UART
├── uart_polling
├── uart_interrupt
├── uart_dma
├── uart_baudrate
├── uart_error_frame
└── uart_low_power_wakeup

GPIO
├── gpio_input
├── gpio_output
├── gpio_interrupt
├── gpio_pullup_pulldown
└── gpio_drive_strength

TIMER
├── timer_base
├── timer_interrupt
├── pwm_output
├── input_capture
├── encoder
└── deadtime

ADC
├── adc_single
├── adc_scan
├── adc_dma
├── adc_timer_trigger
├── adc_accuracy
└── adc_noise

SPI
├── spi_master_loopback
├── spi_slave
├── spi_dma
├── spi_cpol_cpha
├── spi_frequency
└── spi_error
```

### 12.3 每个测试的判定层级

建议分三类：

```text
A 类：固件自检
- DMA memory compare
- interrupt counter
- register readback
- internal status flag

B 类：外部数字观测
- GPIO 电平
- SPI/I2C/UART/CAN 协议解码
- 逻辑分析仪捕获

C 类：外部模拟/电气测量
- PWM 波形
- ADC/DAC 精度
- 电流功耗
- 电源时序
- 上升沿/下降沿
```

Renode 通常覆盖 A 类和部分 B 类。
真实硬件覆盖 A/B/C 全部。

---

## 13. 项目目录结构建议

```text
mcu-validation/
├── README.md
├── pyproject.toml
├── requirements.txt
├── tests/
│   ├── conftest.py
│   ├── test_uart.py
│   ├── test_gpio.py
│   ├── test_timer.py
│   ├── test_pwm.py
│   ├── test_adc.py
│   ├── test_spi.py
│   ├── test_i2c.py
│   ├── test_dma.py
│   ├── test_flash.py
│   ├── test_can.py
│   └── test_bootrom.py
├── targets/
│   ├── base.py
│   ├── renode_target.py
│   ├── hardware_target.py
│   └── fpga_target.py
├── programmers/
│   ├── base.py
│   ├── jlink.py
│   ├── openocd.py
│   └── pyocd.py
├── instruments/
│   ├── scope.py
│   ├── power.py
│   ├── logic_analyzer.py
│   ├── dmm.py
│   ├── signal_generator.py
│   └── electronic_load.py
├── firmware/
│   ├── common/
│   ├── cases/
│   ├── boards/
│   ├── linker/
│   ├── startup/
│   ├── sdk/
│   └── build.py
├── renode/
│   ├── platforms/
│   │   └── my_mcu.repl
│   ├── scripts/
│   │   └── my_board.resc
│   └── peripherals/
├── configs/
│   ├── renode.yaml
│   ├── real_evb.yaml
│   ├── fpga_proto.yaml
│   └── instruments.yaml
├── reports/
├── logs/
├── artifacts/
└── ci/
    ├── Jenkinsfile
    └── gitlab-ci.yml
```

---

## 14. pytest 插件/fixture 设计

### 14.1 命令行参数

```python
def pytest_addoption(parser):
    parser.addoption("--target", action="store", required=True)
    parser.addoption("--unsupported", action="store", default="xfail",
                     choices=["skip", "xfail", "fail"])
    parser.addoption("--config", action="store", default=None)
```

### 14.2 target fixture

```python
@pytest.fixture(scope="session")
def target(request):
    target_name = request.config.getoption("--target")

    if target_name == "renode":
        return RenodeTarget.from_config("configs/renode.yaml", request)
    elif target_name == "real_evb":
        return HardwareTarget.from_config("configs/real_evb.yaml", request)
    elif target_name == "fpga_proto":
        return FpgaTarget.from_config("configs/fpga_proto.yaml", request)
    else:
        raise ValueError(f"Unknown target: {target_name}")
```

### 14.3 firmware fixture

```python
@pytest.fixture(scope="session")
def firmware(request):
    target_name = request.config.getoption("--target")
    return FirmwareBuilder(board=target_name)
```

---

## 15. RenodeBackend 设计

### 15.1 职责

```text
- 启动 Renode
- 加载平台描述
- 加载 ELF
- 控制 start/reset/pause
- 连接虚拟 UART
- 获取日志
- 读写虚拟寄存器
- 处理 unsupported capability
```

### 15.2 示例接口

```python
class RenodeTarget(Target):
    def __init__(self, config, request):
        self.config = config
        self.capabilities = config["capabilities"]
        self.unsupported_mode = request.config.getoption("--unsupported")
        self.renode = RenodeController(config["renode"])
        self.console = RenodeConsole(self.renode, "uart0")

    def flash(self, image: str):
        self.renode.monitor(f"sysbus LoadELF @{image}")

    def reset(self):
        self.renode.monitor("machine Reset")
        self.renode.monitor("start")

    def read_register(self, addr: int) -> int:
        return self.renode.monitor_read32(addr)

    def require(self, capability: str):
        if not self.capabilities.get(capability, False):
            self.handle_unsupported(capability)
```

### 15.3 Renode 的边界

Renode 能验证：

```text
- 固件能否启动
- vector table / reset handler 是否正确
- clock 初始化软件流程是否正确
- UART shell 是否可用
- Timer interrupt 软件路径是否正确
- SPI/I2C/CAN 协议栈部分流程
- DMA 软件配置路径
- bootloader 状态机
- 异常处理逻辑
```

Renode 不能替代：

```text
- 真实 ADC 精度
- 真实电流
- 真实边沿
- 真实上电时序
- 真实晶振和 PLL
- 真实 IO drive strength
- 真实模拟外设行为
```

---

## 16. HardwareBackend 设计

### 16.1 职责

```text
- 通过 J-Link/OpenOCD 烧录
- 控制真实复位/上下电
- 连接真实串口
- 调用仪器测量
- 读写真实寄存器
- 管理日志和波形文件
```

### 16.2 示例接口

```python
class HardwareTarget(Target):
    def __init__(self, config, request):
        self.config = config
        self.capabilities = config["capabilities"]
        self.programmer = JLinkProgrammer(config["programmer"])
        self.console = SerialConsole(config["serial"])
        self.scope = ScopeFactory.create(config.get("scope"))
        self.power = PowerSupplyFactory.create(config.get("power"))
        self.logic = LogicAnalyzerFactory.create(config.get("logic_analyzer"))

    def flash(self, image: str):
        self.programmer.flash(image)

    def reset(self):
        self.programmer.reset()
        self.console.reopen()

    def power_cycle(self):
        self.power.off()
        time.sleep(0.2)
        self.power.on()
        self.console.reopen()

    def measure_pwm(self, channel: str):
        self.require("pwm_measurement")
        return self.scope.measure_pwm(channel)

    def read_register(self, addr: int) -> int:
        return self.programmer.read32(addr)
```

---

## 17. 仪器抽象设计

### 17.1 示波器

```python
class Scope:
    def setup_pwm_measurement(self, channel, trigger=None): ...
    def measure_pwm(self, channel) -> PwmMeasurement: ...
    def save_screenshot(self, path): ...
    def export_waveform(self, channel, path): ...
```

### 17.2 电源

```python
class PowerSupply:
    def set_voltage(self, channel, voltage): ...
    def set_current_limit(self, channel, current): ...
    def output_on(self, channel): ...
    def output_off(self, channel): ...
    def measure_voltage(self, channel) -> float: ...
    def measure_current(self, channel) -> float: ...
```

### 17.3 逻辑分析仪

```python
class LogicAnalyzer:
    def start_capture(self, config): ...
    def stop_capture(self): ...
    def decode_uart(self, channel, baudrate): ...
    def decode_spi(self, clk, mosi, miso, cs): ...
    def decode_i2c(self, sda, scl): ...
    def save_capture(self, path): ...
```

### 17.4 信号源/电压源

```python
class SignalSource:
    def set_dc_voltage(self, channel, voltage): ...
    def set_sine(self, channel, freq, amplitude, offset): ...
    def output_on(self, channel): ...
    def output_off(self, channel): ...
```

---

## 18. 测试报告设计

每条测试建议保存：

```text
- pytest 结果
- target 类型
- 固件版本
- SDK commit
- 编译参数
- 板卡序列号
- 芯片批次/版本
- 仪器型号和序列号
- 串口日志
- J-Link/OpenOCD 日志
- 示波器截图
- 波形 CSV
- 逻辑分析仪 capture
- 电流采样数据
- 失败时寄存器 dump
```

报告输出：

```text
- JUnit XML：给 CI 使用
- Allure：给团队查看
- CSV/数据库：长期趋势分析
- artifacts/：保存波形、截图、日志
```

---

## 19. CI 策略

### 19.1 每次提交

```text
- 编译所有基础测试固件
- Renode 跑 startup / UART / GPIO / Timer 快速测试
- unsupported=xfail 或 skip
```

### 19.2 每晚回归

```text
- 真实硬件跑基础 IP
- FPGA 原型跑可用 IP
- 仪器测 PWM/SPI/I2C/CAN/ADC/功耗
- 保存完整 artifacts
```

### 19.3 发版前

```text
- 全 IP 回归
- 多板卡并行
- 不同芯片版本/封装/板级配置
- 长稳测试
- 低功耗
- 异常路径
- bootloader/BootROM
- 边界条件
```

### 19.4 建议命令

```bash
# Renode 快速回归
pytest tests/ --target renode --unsupported=xfail --junitxml=reports/renode.xml

# 真实板卡基础回归
pytest tests/ --target real_evb --unsupported=fail --junitxml=reports/real_evb.xml

# FPGA 原型
pytest tests/ --target fpga_proto --unsupported=xfail --junitxml=reports/fpga_proto.xml

# 只跑仪器相关测试
pytest tests/ --target real_evb -m instrument --unsupported=fail
```

---

## 20. marker 设计

marker 不用于拆分用例文件，而是用于选择测试类别：

```python
@pytest.mark.ip_uart
def test_uart_echo(target, firmware):
    ...

@pytest.mark.ip_adc
@pytest.mark.instrument
def test_adc_single_1v(target, firmware):
    ...

@pytest.mark.low_power
@pytest.mark.instrument
def test_stop_mode_current(target, firmware):
    ...
```

pytest.ini：

```ini
[pytest]
markers =
    ip_uart: UART tests
    ip_gpio: GPIO tests
    ip_timer: Timer tests
    ip_pwm: PWM tests
    ip_adc: ADC tests
    ip_spi: SPI tests
    ip_i2c: I2C tests
    ip_dma: DMA tests
    ip_flash: Flash tests
    ip_can: CAN tests
    instrument: tests requiring external instruments
    low_power: low power tests
    bootrom: BootROM tests
```

运行：

```bash
pytest -m ip_uart --target renode
pytest -m "instrument and ip_pwm" --target real_evb
pytest -m "not low_power" --target fpga_proto
```

---

## 21. Renode 与真实硬件结果如何对齐？

同一用例在不同 target 上跑，建议输出统一结果表：

| Test Case | Renode | Hardware | FPGA | 说明 |
|---|---:|---:|---:|---|
| test_uart_echo | PASS | PASS | PASS | 完全统一 |
| test_gpio_output | PASS | PASS | PASS | Renode 读虚拟 pin，硬件读 DAQ |
| test_pwm_basic | XFAIL | PASS | PASS | Renode 暂无 PWM 测量能力 |
| test_adc_accuracy | XFAIL | PASS | XFAIL | Renode/FPGA 无模拟精度 |
| test_low_power_current | XFAIL | PASS | XFAIL | 仅真实硬件有效 |

判断逻辑：

```text
Renode PASS，硬件 PASS：
    软件路径和真实硬件均可信。

Renode PASS，硬件 FAIL：
    可能是真实寄存器行为、时钟、电气、板级、仪器或模型差异。

Renode FAIL，硬件 PASS：
    可能是 Renode 模型不完整或模型行为错误。

Renode FAIL，硬件 FAIL：
    大概率是 SDK/固件逻辑问题。

Renode XFAIL，硬件 PASS：
    正常，说明该项需要真实硬件。
```

---

## 22. 分阶段落地路线

### 阶段 0：确定边界

产出：

```text
- 要覆盖的 IP 清单
- 每个 IP 的 feature list
- 目标板卡清单
- 仪器清单
- Renode 支持能力清单
- FPGA 原型能力清单
```

### 阶段 1：最小 HIL MVP

先不要引入太多工具，只做：

```text
pytest
pyserial
JLinkExe 或 OpenOCD
一个开发板
一个 UART 测试固件
一个 GPIO 测试固件
一个 Timer 测试固件
```

目标：

```text
烧录 → 复位 → 串口 expect → PASS/FAIL → JUnit XML
```

### 阶段 2：加入 Target API

把脚本整理成：

```text
Target
HardwareTarget
FirmwareBuilder
Console
Programmer
```

用例只依赖 `target`。

### 阶段 3：加入 RenodeBackend

新增：

```text
RenodeTarget
renode/platforms/my_mcu.repl
renode/scripts/my_board.resc
```

同一份 pytest 用例跑：

```bash
pytest tests/test_uart.py --target renode
pytest tests/test_uart.py --target real_evb
```

### 阶段 4：加入 capability matrix

实现：

```text
target.require()
--unsupported=skip/xfail/fail
renode.yaml
real_evb.yaml
fpga_proto.yaml
```

### 阶段 5：加入仪器控制

接入：

```text
PyVISA scope
PyVISA power
Saleae/sigrok logic analyzer
```

新增测试：

```text
PWM
SPI/I2C
ADC
DAC
低功耗
电源时序
```

### 阶段 6：加入 labgrid

当板卡数量增加后，引入：

```text
labgrid coordinator
board reservation
remote exporter
power/serial/programmer resources
```

### 阶段 7：接入 CI 和报告系统

新增：

```text
Jenkins/GitLab CI
JUnit XML
Allure
artifacts archive
daily regression
release regression
```

---

## 23. 风险与注意事项

### 23.1 不要让 pytest 用例直接绑工具

否则后续迁移困难。

错误：

```python
ser = serial.Serial("COM3")
scope.write(":MEAS:FREQ?")
```

正确：

```python
target.console.send("...")
target.measure_pwm("CH1")
```

### 23.2 不要要求 Renode 覆盖真实电气测试

Renode 是行为级虚拟平台，不是示波器、电源、ADC 精度验证平台。

### 23.3 不要一开始做全 IP 大平台

应该先跑通：

```text
UART
GPIO
Timer
```

再扩展：

```text
PWM
SPI
I2C
DMA
ADC
CAN
Flash
Low power
```

### 23.4 固件协议要尽早稳定

一旦 pytest 和固件协议频繁变化，整个平台会很难维护。

### 23.5 能力矩阵要显式

不要靠测试里隐式判断：

```python
if target.name == "renode":
    ...
```

应该靠：

```python
target.require("pwm_measurement")
```

---

## 24. 推荐最终方案

最终方案可以总结为：

```text
主测试框架：pytest
板卡资源管理：labgrid
仪器控制：PyVISA + sigrok/Saleae
烧录调试：J-Link/OpenOCD/pyOCD
软件仿真：Renode
统一接口：Target API
统一能力表达：capability matrix
统一固件交互：test shell / TEST_PASS 协议
统一报告：JUnit XML + Allure + artifacts
```

其中最重要的三条原则：

```text
1. pytest 用例层必须统一。
2. 固件测试协议必须统一。
3. Renode / Hardware / FPGA 只是不同 backend。
```

---

## 25. 推荐参考资料

以下是建议优先阅读的官方或项目资料：

1. pytest skip / xfail 文档
   https://docs.pytest.org/en/stable/how-to/skipping.html

2. pytest fixture 文档
   https://docs.pytest.org/en/stable/explanation/fixtures.html

3. labgrid 文档
   https://labgrid.readthedocs.io/

4. PyVISA 文档
   https://pyvisa.readthedocs.io/

5. Renode Testing 文档
   https://renode.readthedocs.io/en/latest/introduction/testing.html

6. Renode 官网
   https://renode.io/

7. sigrok 项目
   https://sigrok.org/

8. Saleae Logic 2 Automation API
   https://www.saleae.com/support/extensions-api/automation-api/automation

9. OpenOCD 官网
   https://openocd.org/

10. SEGGER J-Link Commander
    https://www.segger.com/products/debug-probes/j-link/tools/j-link-commander/

---

## 26. 最终结论

你提出的两个核心要求是合理的：

```text
1）pytest 用例层必须一致
2）Renode 与真实硬件/FPGA 必须通过同一套 pytest 用例运行
```

推荐实现方式是：

```text
同一份 pytest 用例
同一套固件测试协议
同一套 IP 测试源码
不同 target backend
不同 board support
不同 capability matrix
```

固件层是否需要？

```text
需要。
```

只要你要测 MCU IP 功能，大多数情况下都需要测试固件。
固件负责配置和驱动芯片 IP，pytest 负责外部控制、仪器测量和最终判定。

Renode 和真实硬件如何统一？

```text
不要在底层统一。
要在 Target API 和 pytest 用例层统一。
```

Renode 不具备的能力怎么办？

```text
同一条 pytest 用例中调用 target.require("capability")。
根据 --unsupported=skip/xfail/fail 生成明确结果。
```

这样，你的测试平台既能支持 Renode 快速回归，也能支持真实硬件和 FPGA 的完整 IP 自动化验证，并且不会产生两套互相分裂的测试体系。
