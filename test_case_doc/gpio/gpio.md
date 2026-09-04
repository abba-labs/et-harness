# GPIO Stable Support Contract

更新时间：2026-09-04 15:20 CST。

本轮只定义SPI Case依赖的引脚复用动作，不表示GPIO独立Feature全集已经分析或测试。

## 0. Stable IP Contract

GPIO Driver接收逻辑GPIO号、信号功能和外设逻辑实例，不接收物理mux编码。GPIO Service只调用GPIO Wrap；GPIO Wrap从Chip Config查表并只调用GPIO Chip Driver。Case决定复位、引脚配置和外设配置的顺序。

### 0.1 数据与接口

- `gpio_id`：无符号16位逻辑引脚号，不是端口位掩码。
- `function`：保留已有GPIO=0、UART_TX=1、UART_RX=2；追加SPI_CLK=3、SPI_CS=4、SPI_MOSI=5、SPI_MISO=6。信号表示硬件信号身份，不随Controller/Target角色交换而改名。
- `instance_id`：无符号16位外设逻辑实例，由Capability解析handle获得。
- `validate_signal(gpio_id, function, instance_id)`：只查表，不操作硬件；组合未适配返回NOT_SUPPORTED。
- `configure_signal(gpio_id, function, instance_id)`：先验证完整组合，再调用GPIO Driver配置默认双向输入使能Pad和复用。禁止借此配置SPI、CRG或其他IP。
- 新接口不改变既有`configure(config)`的行为和结构体布局。旧GPIO/UART配置继续使用旧表；新接口仅接受显式信号映射，不猜测实例。
- Case在任何硬件配置前验证所有待用引脚；错误映射不能通过退回默认引脚执行。只检查当前Case冲突，不禁止不同串行Case复用GPIO。

### 0.2 Wire

Service ID `0x0014`，Service实例0表示引脚配置服务，不是被配置的外设实例。沿用ET-Frame v1。

| Command | ID | Request | Response |
|---|---:|---|---|
| VALIDATE_SIGNAL | 1 | gpio_id:u16LE, function:u16LE, instance_id:u16LE | 空 |
| CONFIGURE_SIGNAL | 2 | 同上 | 空 |

长度必须为6字节，未知命令NOT_SUPPORTED，错误长度INVALID_PARAM。VALIDATE允许既有安全重试；CONFIGURE不自动重试。配置成功仅表示Driver接受，不是引脚波形或SPI通信PASS。

## 1. Feature Catalog

本轮不发布独立GPIO Feature ID；引脚配置是SPI Case的前提，不包装成新的测试Feature。

## 2. Case Catalog

本轮没有独立GPIO Formal Case。SPI Case承担实际链路验证。

## 3. Machine-readable Case Contract

没有GPIO SPEC/PLAN；GPIO独立分析和测试不在本轮范围。

## 4. Chip Adaptation Summary

| Chip | Feature适配状态 | Case适配状态 | 主要Gap | 详细分析 |
|---|---|---|---|---|
| ET6801 |  |  | Firmware支持动作已实现；不声明GPIO全集或硬件PASS | `ET6801_gpio.md` |

## 5. Common Gap / Evolution

其他信号通过追加稳定功能和芯片映射扩展；不复制Service，不在公共Case填SDK mux。GPIO独立测试需要另行按R140完成资料全集分析。本轮仅复核SPI所需映射。
