---
schema: et.rule-document.v1
number: R330
domain: firmware
lifecycle: active
owners: [firmware_c_style]
rule_ids: [ET-RULE-FIRMWARE-C-STYLE]
---

# R330 Firmware C源码质量与可读性规则

## 1. 定位

本文定义平台自有Firmware C源码的确定性格式、函数可读性、注释契约和语义常量质量。它不定义Service、Wrap、IRQ或Chip Config的架构职责；这些边界分别由R300、R310和R320管理。

源码质量目标不是“格式统一”本身，而是让第一次进入模块的工程师或Agent能够按以下顺序理解代码：

```text
函数名 -> WHAT
Doxygen函数头 -> CONTRACT
Phase/Step与关键注释 -> FLOW / WHY
C实现 -> HOW
```

基础排版必须由仓库固定的`clang-format`配置生成；可静态判定的可读性要求必须由R330对应Checker失败关闭，不得只依赖人工Review。

## 2. 固定范围

### 2.1 排版受控范围

`check_firmware_c_format.py`只处理：

```text
firmware/application
firmware/framework
firmware/services
firmware/wrap
```

禁止批量格式化：

```text
firmware/chips
firmware/build
```

`firmware/chips`保留芯片SDK原始风格；`firmware/build`是生成目录。

### 2.2 可读性受控范围

`check_firmware_c_quality.py`检查平台自行维护的函数定义：

```text
firmware/application
firmware/boards
firmware/framework
firmware/services
firmware/wrap
```

`.c`和`.h`中的函数定义都属于受控对象，包括`static` helper、`static inline`、callback、IRQ callback、factory和Codec helper。

以下目录不进入函数文档门禁：

```text
firmware/chips
firmware/build
```

Chip Driver Test Extension和`et_chip_wrap_config.h`仍遵守第7节语义常量规则及R310规定，但本规则不要求批量改写原始芯片SDK函数注释。

## 3. 固定格式

- 控制语句、函数、结构体、枚举和复合语句使用Allman大括号风格；
- 缩进为4个空格，禁止Tab；
- `if`、`for`、`while`、`switch`和函数不得压缩为单行；
- `case`标签必须缩进；连续标签可以表达Fallthrough，实际执行体必须使用独立复合语句；
- 不同逻辑分支和不同`case`之间保留一个空行；
- 普通调用或赋值结束后进入`if/for/while/switch`时保留一个空行；
- 相邻的同级控制块之间保留一个空行，控制块结束后进入同级普通语句时保留一个空行；
- 函数已有执行语句时，最终`return`前保留一个空行；块内第一条语句是`return`时不增加空行；
- 说明某条控制语句或`return`的注释必须与该语句相邻，逻辑分隔空行放在注释块之前；
- 不得为满足列宽改变Wire常量、宏值、表达式顺序或业务语义。

长函数必须按真实功能阶段分组，禁止按固定物理行数或某个变量名机械插入空行：

- 输入校验、资源准备、硬件执行、状态观测、结果编码和清理/返回等不同阶段之间保留一个空行；
- 同一功能块内的连续调用或赋值保持相邻，例如连续编码多个响应字段及设置响应长度；
- 一个逻辑块通常不超过8个同级动作；超过时必须优先寻找真实功能边界，无法再分时提取具名辅助函数；
- 同一功能的批量字段写入、表项初始化或顺序硬件配置可以保持为一个完整逻辑块，不得为了满足计数拆散；
- Formatter只自动处理能够由语法结构确定的边界；功能阶段由开发者或Agent在实现时划分。

## 4. 函数职责与复杂度

- 一个函数只承担一个能够准确命名的职责；函数名应表达动作和对象，禁止使用`handle_misc`、`process_all`等无法说明边界的名字；
- 优先早返回，减少深层嵌套；错误处理和Cleanup必须保留真实执行顺序；
- 注释不能代替职责拆分。一个函数需要超过6个Phase，或多个Phase能够独立命名并被复用时，优先提取具名helper；
- 不得为了降低行数或绕过复杂度门禁创建只转发一次、无业务语义的helper；
- Codec、连续字段映射、静态表构造等同质逻辑可以保持完整，不按纯行数机械拆分。

R330机器门禁把满足任一条件的函数视为“复杂函数”并要求Flow导航：

```text
有效函数体 >= 70行
或
有效函数体 >= 40行 且 if/for/while/switch/do/goto 总数 >= 3
或
有效函数体 >= 20行 且存在 goto
```

阈值只用于触发“需要导航注释”，不是强制拆函数的唯一依据。

## 5. 函数Doxygen文档契约

每个平台自维护的函数定义都必须在定义前紧邻一个标准Doxygen块。public与`static`函数要求一致。

标准模板：

```c
/**
 * @brief Decode and validate one DMA channel configuration request.
 *
 * @param[in] service DMA Service instance that provides controller capability.
 * @param[in] body Raw ET-Frame command body.
 * @param[in] length Command body length in bytes.
 * @param[out] config Decoded chip-neutral DMA Wrap configuration.
 *
 * @note This function only decodes and validates the request. It does not
 *       configure or start DMA hardware.
 *
 * @return 0 if the request is decoded successfully.
 * @return -1 if the request is malformed or cannot be represented locally.
 */
static int decode_config(...);
```

固定要求：

1. `@brief`必须存在且说明函数职责，禁止空白、`.`、`TODO`、`TBD`、`None`、`N/A`等占位内容；
2. 每个命名参数必须且只能有一个同名`@param`；
3. `@param`必须使用`[in]`、`[out]`或`[in,out]`方向，并提供参数语义，不得只重复参数名或类型；
4. 非`void`函数必须至少有一个非空`@return`，说明返回值或状态语义；`void`函数不要求伪造“return none”；
5. 每个函数必须至少有一个非空`@note`，说明最重要的副作用、调用边界、执行上下文、硬件影响或设计原因；
6. callback/IRQ callback的`@note`必须说明执行上下文和有界执行要求；
7. 直接修改硬件状态的函数，`@note`必须说明主要硬件副作用；只做解析、映射或查询的函数应明确说明不执行哪类硬件动作；
8. 修改Service、Runtime、IRQ evidence或共享状态的函数，`@note`应说明主要状态副作用；
9. 函数声明可以在公共头文件补充API级说明，但函数定义本身仍必须满足本节；不得只依赖远处声明让实现失去局部可读性。

Checker只验证结构、参数绑定和非空内容，不判断自然语言是否“足够好”；注释是否真实解释职责和边界仍由Review负责。

## 6. 函数内部Flow / Why注释

内部注释只解释执行路线、设计原因和不明显约束，不逐行翻译C语句。

复杂函数必须至少包含两个标准导航注释，格式只允许：

```c
/* Phase 1: Validate the fixed Wire envelope before decoding fields. */
/* Phase 2: Translate validated fields into the chip-neutral Wrap config. */
```

或：

```c
/* Step 1: Capture timing before clearing the hardware completion source. */
/* Step 2: Publish the completed evidence snapshot. */
```

`Phase`用于职责阶段，`Step`用于同一算法中的顺序步骤。简单helper不要求机械增加Phase/Step。

以下位置只要语义不明显，就必须解释“为什么”或“这一段处于什么阶段”：

- Wire解析、长度/保留位校验和地址宽度转换；
- Resource边界、整数溢出和Capability限制；
- 状态机迁移、异步Session创建/取消/清理；
- 硬件配置、启动、停止、复位和不可逆动作；
- IRQ bind/unbind、enable/disable、clear/force及失败回滚；
- 临界区、seqlock、`volatile`共享状态和ISR/线程同步；
- Cleanup、rollback和故障证据保留；
- Evidence/Observation提交；
- 字节序、位域、SDK/SVD事实到公共语义的转换；
- 硬件Errata、Workaround或顺序约束。

禁止：

```c
/* Increment index. */
++index;

/* Check pointer. */
if (ptr == NULL)

/* Return error. */
return -1;
```

推荐：

```c
/*
 * Sample the cycle counter before clearing the transfer source because the
 * clear operation destroys the hardware completion boundary.
 */
```

以及：

```c
/*
 * Keep generation odd while ISR-owned evidence is modified so thread context
 * cannot consume a partially updated snapshot.
 */
```

## 7. 语义常量与魔鬼数字

平台自有Firmware代码禁止使用无法从上下文直接判断硬件或业务含义的数字字面量。该规则适用于`firmware/application`、`firmware/framework`、`firmware/services`、`firmware/wrap`，也适用于平台维护的`et_chip_wrap_config.h`和Chip Driver Test Extension；它不授权批量改写原始SDK Driver。

下列内容必须使用已有公共宏、Enum、`sizeof`、标准整数限制宏或新增的具名语义常量：

- 协议字段长度、偏移、版本、命令和状态值；
- 算法Block、FIFO、水位、对齐和缓冲区容量；
- 超时、轮询、重试、循环上限和性能预算；
- 实例、通道、IRQ、DMA Request、时钟/复位选择；
- 寄存器掩码、位移、硬件边界和Capability限制；
- 任何需要读者查阅手册或追踪调用链才能理解的数字。

使用顺序固定为：

```text
已有平台公共符号
  -> 当前芯片SDK公开Enum或宏
  -> SVD生成的CMSIS符号
  -> 本模块具名语义常量
```

禁止为了绕过魔鬼数字规则重复定义已有符号。新增具名常量必须在定义处说明含义和单位；若数值来自硬件或外部契约，还必须说明来源。相同语义只能有一个权威定义，调用处必须复用，不能再次写入等价字面量。

以下不视为魔鬼数字：

- 含义显然的`0`和`1`，例如初始化、Boolean判断和单步增量；
- Enum或具名常量自身的值定义；
- `sizeof`结果和`UINT8_MAX`、`UINT16_MAX`等标准限制宏；
- 集中封装并已注明字节序的Codec内部直接数组下标与位移宽度；
- 测试向量自身的数据内容，但向量长度、格式和来源仍必须具名或注明。

注释不能替代语义符号。`process(data, 16u)`即使旁边写有“Block大小”，仍应改为`process(data, ET_AES_BLOCK_SIZE_BYTES)`或复用已有等价符号。

### 7.1 语义数字机器门禁

`check_firmware_c_quality.py --strict-magic`使用`ETFMT211`对函数体整数字面量执行确定性检查。机器规则只负责高置信度语法事实，不尝试用LLM猜数字语义：

- 新增或本次修改的受控Firmware文件必须执行`--strict-magic`；除`0/1`外，函数体中的未具名整数失败关闭；
- 集中Codec中的直接数组下标和位移宽度允许保留，例如`data[2]`、`value << 8u`，因为它们是局部机械编码位置而不是业务/硬件语义常量；
- 上述语法豁免不授权把业务字段号、Block Size、Timeout、Mask、IRQ、DMA Request或硬件限制伪装成Codec机械数字；语义上属于本节列表的事实仍必须具名；
- 禁止增加按路径、函数名或某个具体数字值的永久allowlist来让门禁变绿；
- `--all`负责全树Doxygen/Flow等已完成迁移的可读性基线；语义数字采用“所有新增/修改文件严格失败关闭”的确定性范围，避免为了启用新规则而重新解释未触碰历史文件中的局部机械数字。

因此，后续Agent只要修改一个Service/Wrap/Application/Framework/Board受控C/H文件，该文件全部函数都会进入严格语义数字检查；新文件同样全文件检查。

## 8. 自动化与失败关闭

`.clang-format`和`check_firmware_c_format.py`继续唯一负责机械排版；`check_firmware_c_quality.py`只做只读质量检查，不自动生成自然语言注释、不重命名函数、不拆函数，也不修改源码。

诊断分工：

```text
ETFMT101-ETFMT106  固定格式与formatter
ETFMT201-ETFMT208  Doxygen结构、参数、返回值和@note
ETFMT209           复杂函数缺少Phase/Step导航
ETFMT210           Checker调用、Git基线或受控路径错误
ETFMT211           本次受控文件函数体存在未具名语义整数
```

### 8.1 永久全树门禁

五个可读性受控根目录已经完成R330函数文档与Flow迁移。统一软件门禁每次执行必须同时运行：

```text
python tools/quality/check_firmware_c_quality.py --all
python tools/quality/check_firmware_c_quality.py --strict-magic --base-ref <change-base>
```

本地没有Git基线参数时，第二条命令检查当前工作区发生变化的受控Firmware文件。

永久要求：

1. `--all`检查`firmware/application`、`firmware/boards`、`firmware/framework`、`firmware/services`和`firmware/wrap`中的全部受控C/H函数定义，永久保护Doxygen、参数契约和Flow导航；
2. `tools/validate_pc.py`必须始终执行全树`--all`，并对本次实际变化附加`--strict-magic`；不得用changed-file检查替代全树可读性基线；
3. 禁止增加永久allowlist、路径豁免、函数名豁免或以“历史代码”为理由跳过本次修改文件的严格语义数字检查；
4. 任意受控文件出现缺失Doxygen、参数绑定错误、空`@note`、复杂函数缺少Flow导航，或本次修改文件被`ETFMT211`命中，统一软件门禁立即失败；
5. `--base-ref`、无参数changed-file模式和显式路径模式用于确定本次严格语义数字范围或Reviewer定位，不能替代总门禁中的`--all`；
6. 新增受控根目录时，必须同时更新本规则、Checker范围和对应回归测试；不得只更新其中一处；
7. IP Service/Wrap任务的Task Context必须在开发前路由`firmware_c_style`，并在专项验证中执行目标文件`--strict-magic`检查；
8. 本规则生效后的新代码必须直接满足第4、5、6、7节，不再存在一次性迁移阶段。

### 8.2 自动修复边界

- `check_firmware_c_format.py --fix <paths...>`只允许机械格式修复；
- `check_firmware_c_quality.py`没有`--fix`；
- Agent不得自动生成占位Doxygen让门禁变绿；
- 不得通过弱化复杂函数阈值、扩大排除目录、放宽语义数字检查或接受空注释绕过门禁；
- 注释整理不得改变Wire、公共API、硬件行为、状态机、IRQ语义或测试结论；
- Reviewer发现注释与真实实现不一致时，按源码质量缺陷处理，即使机器Checker能够通过也不得合并。

## 9. 验证

永久验证链：

```powershell
python tools/quality/check_firmware_c_format.py
python tools/quality/check_firmware_c_quality.py --all
python tools/quality/check_firmware_c_quality.py --strict-magic --base-ref <change-base>
python tools/quality/check_firmware_architecture_rules.py .
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_firmware_c_format.py
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_firmware_c_quality.py
python -m pytest -q pc/et_test_platform/framework_validation/unit/firmware_contract
python tools/validate_pc.py --change-base <change-base>
```

`tools/validate_pc.py`是统一软件总门禁；它同时包含全树R330函数可读性检查和本次变化的严格语义数字检查。显式文件检查可用于IP专项验证，但不能替代总门禁。
