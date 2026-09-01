---
schema: et.rule-document.v1
number: R400
domain: protocol
lifecycle: active
owners: [et_frame_v1]
rule_ids: [ET-RULE-ET-FRAME-V1]
---

# R400 ET-Frame v1 公共通信协议

ET-Frame v1是PC端`TargetClient`与DUT测试固件公共层之间的二进制协议。
协议不绑定UART实例、芯片寄存器、板卡引脚、PC串口号或具体IP。

当前协议只冻结：

- 公共帧格式；
- 公共命令头；
- 请求与响应规则；
- Framework公共服务的基础命令；
- 超时重试、重复请求重放和错误帧恢复规则。

SPI、CANFD、SRPWM等具体IP的`command_id`、请求参数和返回格式不在本文定义。
每个IP应在真正开发其测试Feature时独立设计自己的命令。

## 1. 设计原则

- 轻量化：不使用JSON、TLV、动态内存、RTOS消息队列或运行时插件扫描；
- 可靠：每个合法请求必须有明确响应，配置命令也必须返回成功或失败；
- 可扩展：公共层只根据`service_id + instance_id + command_id`分发；
- 职责清晰：UART中断只收发字节，不在中断中解析协议或执行命令；
- 单一协议：PC请求与固件响应使用相同ET-Frame和相同公共命令头。

## 2. 数据处理链路

```text
UART接收中断
  -> RX环形缓冲区
  -> 主循环解析ET-Frame并校验CRC
  -> 解析8字节公共命令头
  -> Service Router查找服务
  -> Framework Service或具体IP Service
  -> 使用相同格式编码RESPONSE
  -> TX环形缓冲区
  -> UART发送
```

UART ISR不得解析ET-Frame、查找Service或执行测试命令。ISR只搬运必要字节、
更新环形缓冲区和错误统计，所有协议解析和业务处理均在主循环完成。

## 3. ET-Frame格式

所有多字节整数均为little-endian。

| Offset | Size | Field | 说明 |
|---:|---:|---|---|
| 0 | 2 | Magic | 固定为ASCII `ET`，用于识别帧头和错误后的重新同步 |
| 2 | 1 | Version | 当前为1；只有不兼容的帧格式变化才升级 |
| 3 | 1 | Message Type | `REQUEST`、`RESPONSE`或预留的`EVENT` |
| 4 | 2 | Flags | v1请求和响应固定为0，保留给未来扩展 |
| 6 | 2 | Payload Length | Payload实际字节数，最大4096字节 |
| 8 | 4 | Sequence | PC请求序号；固件响应原样返回 |
| 12 | 4 | Session ID | PC在HELLO时提出的随机非零会话号，用于隔离旧数据 |
| 16 | N | Payload | 8字节公共命令头和可选命令body |
| 16+N | 4 | CRC32 | 帧头和Payload的完整性校验 |

CRC使用IEEE CRC32，初值`0xFFFFFFFF`，多项式反射值`0xEDB88320`，
结果异或`0xFFFFFFFF`。计算范围为header和payload，不包含末尾CRC字段。

### 3.1 Message Type

| Value | 名称 | 方向 | 说明 |
|---:|---|---|---|
| 1 | `REQUEST` | PC -> 固件 | PC发起命令 |
| 2 | `RESPONSE` | 固件 -> PC | 固件返回执行状态和可选数据 |
| 3 | `EVENT` | 固件 -> PC | 预留的主动事件；v1基础测试不得依赖 |

首版采用单请求、单响应模式。PC收到当前请求的响应或确认超时之前，不发送下一条请求。

## 4. 公共命令Payload

每个REQUEST和RESPONSE的Payload都使用相同的8字节公共命令头：

| Offset | Size | Field | 说明 |
|---:|---:|---|---|
| 0 | 2 | Service ID | 标识Framework或具体IP服务 |
| 2 | 2 | Command ID | 由所属Service定义 |
| 4 | 2 | Instance ID | 标识服务实例；Framework固定为0 |
| 6 | 2 | Status | 请求固定为0；响应返回执行状态 |
| 8 | N | Body | 命令参数或返回数据，可以为空 |

公共命令头不包含`case_run_id`、`execution_id`、`detail_code`或统一IP状态机。
如果某个IP未来确实需要执行编号、异步句柄或详细错误信息，应在该IP命令自己的
body中定义，不得增加公共协议复杂度。

## 5. 请求与响应

PC请求：

```text
Message Type = REQUEST
Sequence     = 新请求递增；超时重试保持不变
Session ID   = 当前会话；HELLO为PC新生成的随机非零值
Payload:
  service_id
  command_id
  instance_id
  status = 0
  body = 可选请求参数
```

固件响应：

```text
Message Type = RESPONSE
Sequence     = 原样复制请求Sequence
Session ID   = 当前会话
Payload:
  service_id  = 原样复制请求值
  command_id  = 原样复制请求值
  instance_id = 原样复制请求值
  status      = 执行结果
  body        = 可选返回数据
```

配置类命令可以不返回业务数据，但必须返回RESPONSE。`status = OK`且body为空，
即表示配置已被固件接受并执行。这样PC可以区分“执行成功”“参数错误”和“根本未收到命令”。

查询类命令使用相同格式，只是在成功响应的body中携带查询结果。公共协议不额外定义
ACK帧或单独的返回协议。

错误响应也可以携带body。公共层保留该body并交给PC Driver解释，具体IP可用它返回
参数位置、硬件状态或其他精简诊断信息，不需要增加第二套错误协议。

以下情况固件不返回响应，因为帧本身不可信或无法安全匹配请求：

- CRC错误；
- 长度错误或帧被截断；
- 无法恢复的非法帧头；
- 非`HELLO`请求的Session ID不匹配。

PC通过请求超时处理这些情况。

## 6. Framework公共服务

Framework公共服务固定为：

```text
service_id  = 0x0000
instance_id = 0
```

首版只定义必要的公共能力。除`ECHO`外，请求Body均为空；所有整数均为little-endian，
字符串统一编码为`u8 length + length字节UTF-8`，不含尾零：

| Command | ID | 请求Body | 成功响应Body | 用途 |
|---|---:|---|---|---|
| `HELLO` | `0x0001` | 空 | `u16 protocol_version + string chip_id + string firmware_build_id + string registry_hash` | 建立会话并确认目标 |
| `ECHO` | `0x0002` | 任意二进制数据 | 原样复制请求Body | 链路完整性和压力测试 |
| `VERSION_GET` | `0x0003` | 空 | `u16 protocol_version + string firmware_build_id` | 获取协议和固件版本 |
| `SERVICE_LIST` | `0x0004` | 空 | `u16 count + count * (u16 service_id + u16 instance_id)` | 确认固件提供的服务 |
| `STATISTICS_GET` | `0x0005` | 空 | `u32 rx_frames + u32 tx_frames + u32 parse_errors + u32 duplicate_requests` | 获取通信统计 |
| `RESET_REASON_GET` | `0x0006` | 空 | `u32 raw_reset_reason` | 获取当前启动的原始复位来源 |

响应Body必须严格消费完毕，不允许尾随字节。`RESET_REASON_GET`在目标无法提供可靠复位原因时返回
`NOT_SUPPORTED`且不返回成功Body，不能伪造默认值。

PC每次建立连接时生成一个随机非零Session ID，并在`HELLO`请求帧中提出。固件在
`HELLO`成功响应帧中原样返回并绑定该Session ID，PC随后用于全部请求。固件启动时
Session为0，非`HELLO`请求在会话尚未建立或Session不匹配时均被丢弃。超时重试必须
复用同一条HELLO帧，不能重新生成Session。

HELLO身份信息中的`registry_hash`由固件根据当前Router注册顺序内的
`service_id + instance_id`列表运行时计算，不由Board宏手工填写。算法固定为32-bit FNV-1a：
初值`2166136261`，依次输入每个条目的`service_id` little-endian 2字节和`instance_id`
little-endian 2字节，乘数`16777619`并按32-bit截断，最终编码为8个小写十六进制字符。
PC读取`SERVICE_LIST`后必须按同一算法复算并与HELLO值一致，才能发布Runtime Service Registry。
增加、删除或改变Service注册顺序后该值自动变化。

ECHO也必须经过正常Service Router和Framework Service，不得在协议层增加旁路。

## 7. 公共状态码

| Value | 名称 | 说明 |
|---:|---|---|
| 0 | `OK` | 命令执行成功 |
| 1 | `INVALID_SERVICE` | Service ID不存在 |
| 2 | `INVALID_COMMAND` | 该Service不支持此Command ID |
| 3 | `INVALID_PARAM` | Body长度、格式或参数值不合法 |
| 4 | `NOT_SUPPORTED` | 当前目标不支持该能力 |
| 5 | `BUSY` | 服务当前忙，不能接受该命令 |
| 6 | `INTERNAL_ERROR` | 固件内部执行失败 |

公共状态只描述通用结果。具体IP需要更详细的信息时，通过该IP响应body返回。

## 8. IP扩展规则

公共协议当前不定义SPI、CANFD、SRPWM等IP的命令，也不定义统一的
`CONFIGURE/START/STATUS/STOP/RESULT`流程。

新增IP时只增加：

- 该IP稳定的`service_id`；
- 该IP自己的`command_id`；
- 该IP每条命令的请求和响应body；
- 固件端对应IP Service；
- PC端对应IP Driver。

`command_id`只在所属Service内部有意义，不要求不同IP采用相同命令编号或测试方法。
PC Test Case不得直接拼接`service_id`或`command_id`，必须通过对应Driver调用。

## 9. 协议所在层

固件端：

```text
firmware/framework
  ET-Frame、公共命令头、请求响应、Session、重试去重、Service Router

firmware/services
  HELLO、ECHO、VERSION_GET等Framework公共命令

firmware/services/<ip>
  未来各IP自己的命令和Service实现
```

PC端：

```text
pc/et_test_platform/communication/protocols
  ET-Frame和8字节公共命令头

pc/et_test_platform/clients
  请求发送、响应匹配、超时和重试

pc/et_test_platform/drivers
  Framework及未来各IP的Command ID和body编解码
```

协议不得放入UART Wrap、Chip SDK、Board宏、UART ISR或pytest Test Case。

## 10. 可靠性约束

- PC端新请求递增`sequence`；只有Driver显式声明为`retry_safe`的命令，超时后才允许最多重试一次，
  总尝试次数为两次；变更型命令和未声明命令默认只发送一次；
- 安全重试必须复用完全相同的`session_id`、`sequence`和编码后帧字节；
- 固件只缓存最近一条请求的完整响应；
- Service执行和响应编码完成后先提交重放缓存，再尝试发送；发送短写时从缓存偏移继续，
  不得再次执行Service；
- 收到相同`session_id + sequence + request fingerprint`时，固件直接重放缓存响应，
  不再次执行命令；
- 相同`session_id + sequence`但请求指纹不同的帧必须丢弃；
- 已收到`BUSY`、`INVALID_PARAM`等业务响应时，PC不得自动重试；
- v1请求和响应的`flags`必须为0；两端在事务边界遇到非零`flags`时必须失败关闭，不能按未知扩展继续执行；
- CRC错误、前导噪声或截断帧不得永久阻塞解析器；
- 重新发现合法Magic后，解析器必须重建帧长度并继续解析；
- `EVENT`在首版只预留；基础测试和最终PASS不得依赖未确认的异步事件。

## 11. 两端一致性

C和Python分别实现协议，但必须使用同一组固定字节向量验证编码和解码结果。
黄金向量位于：

```text
Et_Automated_Testing_Platform_Code/pc/et_test_platform/
  framework_validation/test_data/protocol/et_frame_v1_golden.json
```

Python测试同时编译并运行`framework_validation/native/et_protocol_vector_harness.c`，
直接调用固件的`et_frame.c`和`et_message.c`完成编码及逐字节解码。相同请求经C和
Python编码后，最终字节必须完全一致。协议格式、公共命令号或状态码
发生变化时，必须同时更新文档、C实现、Python实现和黄金向量测试。
