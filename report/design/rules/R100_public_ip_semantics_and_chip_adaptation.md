---
schema: et.rule-document.v1
number: R100
domain: public-ip
lifecycle: active
owners: [public_ip_semantics, public_chip_neutrality, chip_adaptation_boundary]
rule_ids:
  - ET-RULE-PUBLIC-IP-SEMANTICS
  - ET-RULE-CHIP-NEUTRALITY
  - ET-RULE-CHIP-ADAPTATION
---

# R100 Public IP 语义与芯片适配边界

## 1. 定位与边界

本文只定义稳定公共IP语义与芯片事实的边界。Feature/Case规划由R140负责，Case机器块由R120负责。

## 2. 唯一分层

```text
test_case_doc/<ip>/<ip>.md
  = 稳定Feature / Case / Oracle / Report语义

公共实现
  = PC Case / Driver / Firmware Service / Common Wrap
  = 芯片中立

test_case_doc/<ip>/<CHIP>_<ip>.md
  = Hardware / Register / SDK Driver / 历史证据 / 公共语义映射

芯片事实
  = Capability / Board / Execution Mapping / firmware/chips/<chip> / Chip Driver
```

## 3. 稳定语义规则

- Feature/Case ID绑定稳定语义，不绑定芯片；已发布ID不得静默改义。
- 相同Feature复用ID；范围、选项、数量差异进入Capability。
- 实例、IRQ、基址、引脚、SDK调用差异进入芯片适配层。
- 新稳定硬件语义才新增Feature ID。
- 测试流程、Oracle或资源要求发生稳定变化才新增Case ID。
- 新芯片与旧语义冲突时保留旧ID含义，评审新Feature或兼容扩展。

## 4. 公共代码芯片中立规则

PC Formal Case、PC IP Driver/Codec/Model、Firmware IP Service、Common Wrap公共API和公共语义均不得包含芯片名、固定实例、IRQ符号、基址、寄存器布局或芯片SDK类型。

不得按芯片复制完整Case、Driver、Service或Wrap。芯片变化优先由Capability、Profile、Board、Execution Mapping、Chip Driver或Build适配表达。

## 5. 芯片适配规则

- 芯片能力必须来自目标芯片证据；公共Case/Driver不得猜测。
- Chip Driver、启动、链接、时钟、Board宏和物理IRQ可以按芯片存在。
- Common Wrap只能调用本IP Chip Driver；禁止调用其他IP Wrap/Driver。
- 只有证明为跨芯片稳定语义的变化，才允许修改公共抽象。

### 5.1 芯片分析文档映射契约

`test_case_doc/<ip>/<CHIP>_<ip>.md`必须包含：

```text
## 第五章 Chip -> Public Feature Mapping
## 第六章 Chip -> Public Case Adaptation
```

Feature Mapping固定五列：

```text
Public Feature | Hardware | 参数/差异 | Platform | Public Case
```

每个公共Feature必须且只能出现一次。

| Hardware | 含义 |
|---|---|
| `SUPPORTED` | 权威硬件证据明确支持 |
| `UNSUPPORTED` | 权威硬件证据明确不支持 |
| `NEEDS_VERIFICATION` | 证据不足 |

| Platform | 含义 |
|---|---|
| `ADAPTED` | 公共自动化链路已具备所需能力 |
| `PARTIAL_ADAPTATION` | 已适配部分能力，剩余Gap明确 |
| `IMPLEMENTATION_GAP` | Driver/Service/Wrap/Case等实现缺失 |
| `MAPPING_GAP` | Capability/Bench/Execution Mapping/逻辑实例映射未闭合 |
| `NOT_APPLICABLE` | 该Feature对目标芯片无适用执行语义 |
| `NEEDS_VERIFICATION` | 平台适配证据不足 |

Case Adaptation固定三列：

```text
Public Case | Adaptation | Reason / Gap
```

每个公共Case必须且只能出现一次。

| Adaptation | 含义 |
|---|---|
| `ADAPTED` | 目标芯片执行链已适配 |
| `NOT_APPLICABLE` | Case语义不适用 |
| `IMPLEMENTATION_GAP` | 公共或芯片实现缺失 |
| `MAPPING_GAP` | Capability/Bench/Execution Mapping/逻辑资源映射未闭合 |
| `BENCH_GAP` | 缺Peer/Observer/Instrument或配测拓扑 |
| `ENVIRONMENT_GAP` | 适配完成，但当前外部环境无法安全执行 |
| `NEEDS_VERIFICATION` | 证据不足 |

`ADAPTED`不等于`PASS`。真实FPGA/Silicon/HIL结果只能来自当前SHA的运行Evidence。

公共`<ip>.md`的`## 4. Chip Adaptation Summary`必须由上述映射表汇总，并链接目标芯片文档；不得与明细不一致。

## 6. 禁止项

- 公共Case按`chip_id`改变测试语义。
- 公共Driver/Service/Wrap硬编码芯片事实。
- 用芯片文档覆盖公共Feature/Case定义。
- 因单颗芯片缺Feature而删除或改义公共Feature。
- 混淆Renode、FPGA、Silicon/HIL证据。
- 把`SUPPORTED`或`ADAPTED`写成硬件PASS。

## 7. 验证与追溯

```powershell
python tools/quality/check_public_ip_contracts.py
python tools/quality/check_ip_change_rules.py --all-chip-neutral
python tools/quality/validate_chip_ip_docs.py
python tools/quality/check_firmware_architecture_rules.py .
```
