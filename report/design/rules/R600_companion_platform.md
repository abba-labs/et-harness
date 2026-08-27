---
schema: et.rule-document.v1
number: R600
domain: companion
lifecycle: active
owners: [companion_platform_responsibility]
rule_ids: [ET-RULE-COMPANION-PLATFORM]
---

# R600 Companion Platform 规则

## 1. 定位与边界

本规则只定义FPGA配测平台、Peer开发板和外部仪器适配模块的公共职责。
它不定义某个DUT芯片的寄存器、引脚、BootROM或测试Case，也不替代具体设备的数据手册和构建约束。

## 2. 固定职责链

```text
Formal Case
  -> 公共Instrument/Companion接口
  -> 设备Adapter
  -> 配测设备Firmware/RTL或仪器
  -> Canonical Observation/Evidence
  -> Case最终断言
```

- PC Case决定何时配置、Arm、启动、读取和断言。
- PC设备Adapter只负责稳定命令语义、连接、超时、数据转换和错误报告。
- 配测设备Firmware负责命令解析、状态、缓冲区和恢复。
- FPGA RTL负责确定性激励、采集、触发、时间戳和协议状态机。
- 报告层只消费Canonical Result/Observation/Evidence，不重新判断PASS/FAIL。

## 3. 芯片中立规则

- 公共接口、Adapter、Firmware协议和RTL Engine不得包含ET6801或其他DUT芯片语义。
- DUT引脚、板间连接、电压域、设备实例和工具路径只能进入Profile、Board约束或本地运行配置。
- 新设备能力通过新增稳定命令、Engine或Adapter实现，不复制PC Case和公共接口。
- 设备缺少某能力时必须通过Capability明确拒绝或SKIP，不得用弱断言伪造覆盖。

## 4. 确定性与安全规则

- 纳秒或微秒级动作必须在设备Firmware/RTL内完成，不能依赖Windows、pytest、UART或JTAG往返时序。
- 所有激励输出必须有可验证的安全态；初始化、异常、Abort和Cleanup均应恢复安全态。
- Capture溢出、事件丢失、协议版本不兼容和设备自检失败不得产生PASS。
- 大波形应在设备本地缓存；成功优先返回摘要，失败或显式请求时再读取原始数据。
- 真实硬件写入、复位、烧录和电源动作必须经过项目硬件人工门禁。

## 5. 新模块开发要求

首次增加一种Companion、FPGA Engine或仪器Adapter时，Task Context必须同时给出：

```text
- 稳定公共接口或命令语义
- 设备Capability与版本
- Profile/Board绑定位置
- Safe State和恢复路径
- 最小自检或仿真命令
- Canonical Observation/Evidence输出
```

若当前工程尚无该类代码的构建、仿真或静态验证入口，任务必须先补充专项门禁，不能仅以导航检查代替代码验证。

## 6. 禁止事项

- Case直接调用JTAG、SCPI、厂商DLL、寄存器或物理引脚。
- PC Adapter实现DUT测试流程或最终断言。
- A9/MCU Firmware承担边沿级硬实时判定。
- RTL解析pytest、芯片Profile或报告格式。
- 使用旧诊断脚本或历史硬件日志声称正式平台能力PASS。

## 7. 关联规则

- PC接口与依赖方向：R200。
- Canonical Observation/Evidence：R130。
- Run Config、工具路径、Artifact和硬件门禁：R500。
- Task Context导航和修改边界：R002。
