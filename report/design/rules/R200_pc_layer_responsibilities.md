---
schema: et.rule-document.v1
number: R200
domain: pc
lifecycle: active
owners: [pc_layer_responsibilities]
rule_ids: [ET-RULE-PC-LAYERS]
---

# R200 PC分层与Driver规则

## 1. 定位

本文只定义PC代码的分层、依赖方向和IP Driver公共接口边界。Case写法由R210负责，Python样式由R220负责，Wire由R400负责。

## 2. 固定分层

```text
Formal Case
  -> IP Driver
  -> TargetClient
  -> Transport / Backend

Formal Case
  -> Instrument Driver / Companion Driver

Profile + Capability + Bench Mapping
  -> Resolver / Fixture
  -> Formal Case参数
```

| 层 | 只负责 |
|---|---|
| Formal Case | 测试步骤、跨设备编排、最终断言 |
| Resolver / Fixture | 解析能力与台架映射，构造对象，管理基础生命周期 |
| IP Driver | 一个IP的稳定业务动作、参数校验、等待和单IP清理 |
| Codec / Contract | 纯Wire编解码、长度和保留位校验 |
| TargetClient | Service事务、超时、响应匹配和协议错误 |
| Transport / Backend | 字节收发或目标访问，不理解IP业务 |
| Result | 保存Canonical Result、Observation和Artifact引用 |

## 3. 固定依赖方向

1. Case只能调用公开Driver或仪器接口，不得调用Codec、Transport或裸TargetClient。
2. Driver只能调用本IP Codec和TargetClient，不得调用其他IP Driver。
3. Codec必须是纯函数，不得执行I/O、等待、重试或读取Profile。
4. Resolver和Fixture不得发送Feature配置、启动或停止命令。
5. 公共层不得导入具体芯片、板卡、端口、寄存器、IRQ或SDK类型。
6. 芯片差异进入Capability/Profile；物理连接进入Bench/Execution Mapping。

## 4. 一个IP一个Package

```text
pc/et_test_platform/drivers/<ip>/
├── __init__.py
├── models.py       # 稳定枚举、配置和结果
├── contract.py     # Service/Command ID与Wire常量
├── codec.py        # 纯编解码
├── validation.py   # 本IP参数规则
└── driver.py       # 稳定业务API
```

只在存在真实职责时创建文件。简单IP允许合并`models.py`或`validation.py`，不得为了目录整齐制造空抽象。

## 5. Driver接口

### 5.1 直接动作优先

Driver首先是“本IP可执行动作的稳定目录”。新Case应能用直接API按硬件顺序组合测试：

```text
initialize / deinitialize
configure / start / stop
write / read
capture_start / capture_wait / capture_cancel
irq_enable / irq_status_get / irq_clear
status_get / result_get
```

固定规则：

- 一个Public API尽量对应一个明确硬件动作，或一个不可再分的单IP操作。
- Driver必须隐藏Wire、编解码、Chunk、Deadline、有界Polling、Retry、响应校验和Target错误。
- Driver不得隐藏“配置 -> 激励 -> 观测 -> 断言”的测试业务流程；不得用`exchange()`类大动作代替Case编排。
- 已有`xxx_mode()`、`xxx_on_exit()`等生命周期包装只作兼容API；新Driver不得继续增加此类包装，新Case不将其作为首选接口。
- 可读性整理不得删除或改签名已发布Public API；契约变化必须拆成独立任务。

### 5.2 命名和参数

- 方法名表达业务动作，如`configure()`、`start()`、`status_get()`，不得使用`send_cmd_0x12()`。
- 参数使用平台稳定类型；不得暴露Wire字节、芯片SDK结构或物理地址。
- 长期共同出现且有明确含义的参数可组成不可变Config；单个参数不包装成万能字典。
- 实例、通道和事件由参数或解析结果传入，不得写死`uart1`、`dma0`或某芯片枚举。

```python
@dataclass(frozen=True, slots=True)
class TransferConfig:
    source: ResourceHandle
    destination: ResourceHandle
    length: int

class DmaDriver:
    def configure(self, channel: int, config: TransferConfig) -> None: ...
    def start(self, channel: int) -> None: ...
    def wait_complete(self, channel: int, *, timeout_s: float) -> DmaStatus: ...
```

### 5.3 Deadline、Retry和Polling

- 一次顶层操作只建立一个Deadline；嵌套调用使用剩余时间，不重新获得完整超时。
- Driver拥有本IP状态轮询；Case只决定何时调用，不重复实现寄存器式轮询。
- 只有明确幂等的请求允许自动重试；非幂等请求超时后先查询状态。
- 轮询必须有界并保留最后状态；禁止无限循环和为通过测试盲目增大超时。

### 5.4 Cleanup

- Driver只清理自己建立的单IP状态。
- Cleanup按逆序执行，全部尝试；Primary Error和Cleanup Error都必须保留。
- 跨IP清理顺序由Case显式编排，禁止建立万能Cleanup管理器。

### 5.5 方法排列与Private Helper

- `driver.py`按硬件功能排列Public API，例如“初始化、基本数据路径、中断、DMA、状态、私有辅助”；不按开发时间或生成顺序堆叠。
- Private Helper只在存在多个真实调用点、独立算法/编解码概念，或抽取后主流程明显更清楚时创建。
- 只有一个调用点且仅3～5行的逻辑默认保留在原方法；不得为减少行数制造跳转阅读。

## 6. 扩展边界

新增IP通常只增加Driver Package、Case和Profile/Capability，不修改PC公共层。只有至少两个不同IP出现相同、稳定且已验证的公共需求时，才允许评审公共抽象；不得以“未来可能用到”为理由提前增加Registry、Plugin、DI或通用资源图。

## 7. 验证

```powershell
python tools/quality/check_pc_code_rules.py --root . pc/et_test_platform/drivers/<ip>
python -m pytest -q pc/et_test_platform/framework_validation/unit
python tools/validate_pc.py
```
