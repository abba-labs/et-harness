# CRG Stable IP Contract

<!-- Contract sync 2026-08-26: added chip-neutral CRC/STIMER/WDG reset categories for deterministic Case isolation. -->

> 本文件只定义跨芯片稳定的 CRG 公共动作；芯片 Driver 的物理外设选择值仅允许出现在 Chip Config 映射中。

## 0. Stable IP Contract

- IP：`crg`。
- Firmware Service：`service_id=0x0012`，`instance_id=0`。
- CRG 公开接口使用稳定的外设类别和逻辑实例号，不暴露芯片 SDK 枚举值。
- 新芯片只在 `et_chip_wrap_config.h` 中将公共外设类别、逻辑实例映射到该芯片 Driver 选择值，不复制 PC Driver、Service 或 Wrap。

### 0.1 Stable Service Command Contract

| Command | ID | Request bytes | Response bytes | Stable semantics |
|---|---:|---:|---:|---|
| `CLOCK_SET` | `0x0001` | 4 | 0 | `peripheral:u8, instance:u8, enabled:u8, reserved=0` |
| `RESET` | `0x0002` | 4 | 0 | `peripheral:u8, instance:u8, reserved[2]=0` |
| `WDG_CLOCK_SET` | `0x0003` | 4 | 0 | `wdg_id:u8, source:u8, divider:u8, reserved=0`；选择逻辑 WDG 时钟，不启动 WDG |
| `WDG_CLOCK_GET` | `0x0004` | 4 | 4 | Request 同 SET 但未使用字段为 0；Response 为 `source:u8, divider:u8, reserved[2]=0` |

### 0.2 Stable Peripheral Categories

| Public value | Category | Stable semantics |
|---:|---|---|
| `0` | `UART` | UART 控制器逻辑实例 |
| `1` | `DMA` | DMA 控制器逻辑实例 |
| `2` | `AES` | AES 加速器逻辑实例 |
| `3` | `CORDIC` | CORDIC 加速器逻辑实例 |
| `4` | `FMAC` | FMAC 加速器逻辑实例 |
| `5` | `CRC` | CRC 计算单元逻辑实例 |
| `6` | `STIMER` | STIMER 定时器逻辑实例 |
| `7` | `WDG` | WDG 看门狗逻辑实例 |

类别编号是公共协议的一部分，不得重用或改义。芯片不具备某类别或实例时返回 `NOT_SUPPORTED`，不得猜测其他外设。

## 1. Layer Responsibilities

- PC Driver 只编码稳定类别、实例和动作。
- Firmware Service 只校验固定长度、保留位并调用 CRG Wrap。
- CRG Wrap 只查找 Chip Config 映射并调用 CRG Chip Driver。
- Case 负责跨 IP 执行顺序；CRG Service/Wrap 不保存测试流程和 PASS/FAIL。

### 1.1 WDG Clock Owner Boundary

- WDG 时钟源和编码分频属于 CRG Owner；WDG Driver/Service/Wrap 不访问 CRG。
- 公共源值固定为 `0=HSOSC`、`1=APB1`；新芯片通过 Chip Config 映射到本芯片 Driver。
- `WDG_CLOCK_SET` 只执行 CRG 原子配置；配置、启动、喂狗和测量仍由 PC Case 编排。
- `WDG_CLOCK_GET` 返回真实硬件字段读回，不把 PC 请求值缓存成硬件事实。

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---:|---:|---|---|
| ET6801 |  |  | CRG当前只作为公共Owner提供原子Clock/Reset动作，不单独发布Formal Case | `ET6801_crg.md` |

## 5. Common Gap / Evolution

- CRG公共动作由使用它的IP Case组合验证；未来只有形成独立CRG Feature/Case时，才扩展Feature Catalog与Case Catalog。
