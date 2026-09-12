---
schema: et.rule-document.v1
number: R220
domain: pc
lifecycle: active
owners: [python_style_documentation]
rule_ids: [ET-RULE-PYTHON-QUALITY]
---

# R220 Python代码与注释规则

## 1. 定位

本文只定义Python文件的统一格式、注释、类型和质量门禁，不重复PC架构或Case业务规则。

PC运行时、Case与测试模块保持既有全树检查。`tools/`中的Python工具同样受本规则约束；
工具模块须声明职责、边界、依赖，公共API（含main）须说明操作与失败边界。工具API允许准确的中英文说明。
工具注释机器检查覆盖工作树全部新增/修改Python工具；CI指定change-base时还覆盖该基线至HEAD的变更工具，
每个入选文件检查完整内容，不按行忽略。未触碰工具逐次纳入，不建立路径或函数永久豁免；直接传目录可检查全树。
此增量机制不缩减PC既有全树注释检查；说明是否真实仍由Review负责。

## 2. 文件和类型

- 使用UTF-8、LF、Ruff格式；禁止人工列对齐和装饰性分隔。
- 公共配置和结果优先使用`@dataclass(frozen=True, slots=True)`或稳定Enum。
- 禁止万能`dict[str, Any]`穿过公共API；动态JSON边界必须立即校验并转换。
- 公共函数和方法必须有完整类型标注；不要用`Any`绕过设计。
- 文件按“模块注释、导入、常量、类型、纯函数、主要类、公开入口”排列。

## 3. 注释格式

项目代码注释统一使用`#`，不使用Docstring作为模块、类、函数或Case说明。

模块开头用四行以内说明：

```python
# DMA Wire编解码。
# 职责：提供纯Request/Response转换。
# 边界：不执行I/O、等待或Capability解析。
# 依赖：仅本IP Contract/Model和标准库。
```

公共API注释放在定义前，说明业务含义和边界：

```python
# 读取当前状态；只等待本次响应，不等待硬件状态变化。
def status_get(self, channel: int) -> DmaStatus:
    ...
```

注释解释“为什么、边界和判断”，不逐行翻译代码，也不在每个API上重复Deadline、Target异常或“跨IP由Case负责”等已有公共规则。TODO必须有可追踪编号或明确解除条件。

Case函数体内的阶段注释使用“阶段：目的”，例如：

```python
# 边界：16/17 Byte分别覆盖FIFO边界和跨边界场景。
for length in (16, 17):
    ...

# 观测：Capture必须先于发送启动，避免丢失起始字节。
capture.start(length)
```

不同阶段前留一个空行；阶段注释和其代码之间不留空行。P级Case文件仅允许在顶层功能分组使用下列唯一分隔样式，不得混用其他ASCII装饰：

```python
# =============================================================================
# 基本数据通路
# =============================================================================
```

## 4. 函数复杂度

- 一个函数只承担一个可命名职责；优先早返回，避免深层嵌套。
- 重复两次不自动抽象；至少两个不同调用方出现稳定同义逻辑后再提取。
- 不为了缩短行数隐藏业务步骤，也不建立Mixin、BaseDriver或通用Helper容器。
- 规模门禁是Review信号；超过阈值时先拆职责，不通过禁用Checker解决。

## 5. 异常和资源

- 异常必须包含操作、目标和关键参数上下文，不记录密钥或大块载荷。
- 禁止裸`except`和静默吞异常。
- 资源获取后立即建立释放边界；Cleanup错误必须聚合并保留。
- 测试Fake/Mock不得比真实接口更宽松，必须拒绝非法参数并验证命令顺序。

## 6. 当前项目自定义机器门禁

```powershell
python -m ruff check pc
python -m ruff format --check pc
python tools/quality/check_pc_code_rules.py --root . pc
python tools/quality/check_pc_documentation_rules.py
python tools/validate_pc.py
```

禁止用`noqa`、扩大allowlist、关闭测试或降低断言绕过门禁。确属误报时，先修正Owner规则和Checker回归测试，再修改Checker。
