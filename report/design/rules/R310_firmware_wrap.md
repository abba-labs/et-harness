---
schema: et.rule-document.v1
number: R310
domain: firmware
lifecycle: active
owners: [firmware_wrap_responsibility]
rule_ids: [ET-RULE-FIRMWARE-WRAP]
---

# R310 Firmware Wrap规则

## 1. 定位

Wrap是稳定公共接口到当前芯片Driver的唯一桥梁。Wrap名称、参数、返回值和语义必须芯片中立；内部只封装对应IP Driver，不承担应用或Case逻辑。

## 2. 文件与调用边界

```text
firmware/wrap/include/et_<ip>_wrap.h
firmware/wrap/src/et_<ip>_wrap.c

Service -> Own Wrap -> Own Chip Driver
```

- 一个IP一对Wrap文件，全部放在公共`include/`和`src/`，不按芯片复制。
- `<ip> Wrap`只能调用`<ip> Chip Driver`；Wrap之间禁止互调。
- Wrap不得调用Service、Framework、Board初始化、系统时钟、GPIO或IRQ Wrap。
- Wrap公共头文件不得包含芯片SDK类型。

`et_resource_wrap`是已发布的Framework公共资源接口，只做固定容量Resource Handle与内存范围管理，不是Feature IP到Chip Driver的桥梁。Service对它的受限调用遵循R300；不得以该例外增加新的跨IP Wrap调用。

## 3. 模块粒度

Wrap优先一一封装Driver原子能力；一个接口可以组合多个“本IP Driver”调用，以形成稳定且不可再分的业务动作。不得把完整测试流程、跨IP初始化或最终判断组合进Wrap。

```c
typedef struct
{
    uint32_t baudrate;
    uint8_t data_bits;
    uint8_t stop_bits;
    et_uart_parity_t parity;
    uint8_t reserved[5];
} et_uart_config_t;

et_status_t et_uart_wrap_configure(
    et_instance_id_t instance,
    const et_uart_config_t *config);
```

## 4. 参数与返回值

- 使用平台固定宽度类型、公共Enum、Handle和Config；禁止SDK结构、寄存器地址和芯片IRQ符号。
- Config保留字段必须为零并做校验；新增可选字段只能使用已预留空间或发布兼容扩展。
- 返回统一`et_status_t`；数据通过输出参数返回。禁止返回SDK状态码或把错误压成Boolean。
- 实例和通道由公共逻辑ID传入，再由Chip Config映射；不得写死物理实例。
- Wrapper不得推断默认参数；默认值由PC/Profile或Application明确提供。

## 5. Driver优先与测试扩展

Wrap禁止直接访问寄存器。需要的Feature若正式Driver未暴露，先在对应Chip Driver源文件和头文件底部增加隔离的Test Driver Extension：

```c
/******************** Test Driver Extension Begin ********************/
DRV_Status UART_testForceInterrupt(UART_Type *uart, uint32_t mask);
/********************* Test Driver Extension End *********************/
```

要求：

1. 命名清晰并带`test`语义，不能与正式API重复或产生歧义；
2. 实现风格、参数检查和返回值遵循原SDK Driver；
3. 只补足确实存在且Case需要的硬件Feature；
4. Wrap仍然只调用Driver接口；
5. SDK发布时可按隔离标记审查或删除测试扩展。

## 6. `et_chip_wrap_config.h`

该文件只保存公共Wrap适配当前芯片所需的编译期事实：

```c
enum
{
    ET_CURRENT_CHIP_UART_LOGICAL_0 = 0u,
    ET_CURRENT_CHIP_UART_LOGICAL_1 = 1u
};

#define ET_CHIP_UART_FEATURE_FLAGS  (ET_UART_WRAP_CAP_RX_IRQ | ET_UART_WRAP_CAP_TX_IRQ)

#define ET_CHIP_UART_MAP_TABLE                                                        \
    {{ET_CURRENT_CHIP_UART_LOGICAL_0, UART0, UART0_IRQn, ET_CHIP_UART_FEATURE_FLAGS}, \
     {ET_CURRENT_CHIP_UART_LOGICAL_1, UART1, UART1_IRQn, ET_CHIP_UART_FEATURE_FLAGS}}
```

允许：实例表、数量、IRQ Line、时钟/复位选择、SDK常量映射，以及由公共Wrap直接或间接消费的编译期Feature掩码和硬件限制值。

禁止：函数实现、运行时控制流、寄存器操作、Case默认值、板级引脚、动态状态、跨IP初始化、命令解析、Case策略和运行时Feature判断。Feature掩码只能描述芯片静态能力，不能根据命令、Case或运行状态动态选择行为。

新增项按IP连续分区，并由公共Wrap直接或通过同分区映射表消费；不再建立第二个Chip Config文件。公共Wrap直接消费的表级契约使用`*_MAP_TABLE`、`*_FEATURE_FLAGS`、`*_STATUS_MASKS`和`*_LIMITS`形态。映射表内部可以使用芯片本地具名Enum或宏表达缺失的逻辑ID和硬件事实，但必须满足R330的语义常量规则和本节的芯片证据要求；不得为每个数值创建无复用价值的别名。

### 6.1 可读性与来源

`et_chip_wrap_config.h`是芯片适配事实表，不是无注释的数字表。文件和每个IP分区必须让审查者直接看懂“公共逻辑语义如何映射到芯片SDK事实”：

- 文件头必须说明文件职责、允许内容、禁止内容和事实来源；
- 每个IP分区必须说明映射表字段顺序、每个字段的语义和单位；
- 每个物理实例、IRQ、时钟/复位选择、状态位、硬件上限和SDK对象必须使用能够表达含义的符号；
- 位置型初始化无法从字段名自解释时，必须在表定义前逐字段说明，禁止只靠数字排列推测含义；
- 注释解释“为什么使用该事实及其来源”，不得只把宏名翻译成中文。

### 6.2 芯片本地事实的额外证据

符号选择顺序、裸数字判定和新增具名常量的通用要求由R330唯一规定，本节不再重复。只有现有平台、芯片SDK和生成头文件均没有对应符号时，才允许在同一IP分区增加芯片本地事实；其注释除满足R330外，还必须明确：

```text
证据来源：SVD字段、寄存器手册章节或已审核芯片资料；
硬件含义：该值选择或限制什么；
单位/位域：Hz、Byte、Channel、Bit Mask等；
消费位置：对应映射表或结构体的哪个字段。
```

缺少以上任一项时，该值不能进入Chip Config。协议长度、重试次数、超时、Case参数、软件缓存预算和报告格式不属于芯片事实，禁止放入`et_chip_wrap_config.h`。

## 7. 状态与IRQ

- Wrap只保存映射或执行所必需的固定容量本IP状态。
- 异步操作由Service拥有会话，Wrap提供原子配置、启动、状态和清理动作。
- IRQ绑定、NVIC和向量分发由R320定义；普通IP Wrap不得注册ISR。

## 8. 扩展规则

新芯片只修改Chip Driver和`et_chip_wrap_config.h`映射，不改Wrap公开接口。只有出现新的跨芯片稳定语义时才增加接口；芯片独有能力先进入Capability，不能用`#ifdef CHIP`污染公共Wrap。

## 9. 验证

```powershell
python tools/quality/check_firmware_architecture_rules.py .
python tools/validate_pc.py
```
