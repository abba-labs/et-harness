---
schema: et.rule-document.v1
number: R340
domain: firmware
lifecycle: active
owners: [firmware_manual_diagnostics]
rule_ids: [ET-RULE-FIRMWARE-MANUAL-DIAGNOSTICS]
---

# R340 Firmware手动诊断测试规则

## 1. 定位与目的

Firmware手动诊断测试用于以最短调用链复现自动化测试中的FAIL或争议现象，方便人工审核硬件配置、
Driver调用、寄存器状态和真实输出。

它是独立诊断通道，不是正式自动化测试的另一种Backend，也不属于ET-Frame、Service、Wrap、PC Driver、
pytest、Canonical Result或Excel报告链路。

固定调用链：

```text
main编译期开关
  -> et_manual_test_run()
      -> 手动测试独立芯片初始化
      -> 手动测试独立打印UART初始化
      -> et_manual_<ip>_test.c
          -> 当前芯片ET SDK <IP> Driver
          -> UART printf人工观测
```

## 2. 与自动化测试的隔离边界

手动诊断允许复用：

- 当前芯片CMSIS、Startup、System、Linker和原始ET SDK Driver；
- 经过审核且位于Chip Driver中的Test Driver Extension；
- 手动测试专用的UART打印和最小中断处理。

手动诊断禁止调用或包含：

- `firmware/framework`的ET-Frame、Runtime、Resource和IRQ Manager；
- `firmware/services`的任何Service；
- `firmware/wrap`的任何公共Wrap；
- PC自动化Driver、Fixture、Case Registry和pytest；
- Capability、Bench Profile、Execution Mapping和自动报告模型；
- 自动化固件的控制UART协议处理逻辑。

手动测试代码可以使用芯片SDK类型、物理实例、IRQ符号和芯片Driver API，因为它明确属于目标芯片诊断，
不构成公共跨芯片接口。禁止把这些事实反向复制到公共Service或Wrap。

## 3. 固定目录与文件

```text
firmware/manual_tests/
└─ <chip>/
   ├─ include/
   │  ├─ et_manual_test.h
   │  └─ et_manual_test_config.h
   └─ src/
      ├─ et_manual_test.c
      ├─ et_manual_uart_test.c
      ├─ et_manual_crc_test.c
      ├─ et_manual_aes_test.c
      └─ et_manual_<ip>_test.c
```

固定要求：

- 一个IP只建立一个`et_manual_<ip>_test.c`，该IP需要复现的Case全部集中在此文件。
- 一个Formal Case对应一个具名函数，例如`et_manual_uart_p1_008_run()`。
- `et_manual_test.c`只负责公共入口、手动测试初始化和调用当前选中的IP函数。
- 不为每个Case建立文件、目录、Service、Wrap、Registry或配置对象。
- 新芯片在`firmware/manual_tests/<chip>/`增加自己的诊断实现，不复制公共自动化层。

## 4. main入口规则

`firmware/application/src/main.c`只允许增加一个编译期分支。手动路径只能调用一个入口函数：

```c
#if ET_MANUAL_TEST_ENABLE
    return et_manual_test_run();
#else
    /* Existing automated firmware startup and protocol loop. */
#endif
```

禁止在`main.c`的手动分支中配置时钟、GPIO、UART、中断或被测IP。所有手动测试初始化必须封装在
`et_manual_test_run()`及目标芯片手动测试文件内。

`ET_MANUAL_TEST_ENABLE`默认必须为关闭。正式自动化固件构建不得链接或运行手动测试逻辑；手动诊断构建
必须使用独立Build Target或显式构建配置，不得在运行时切换两套模式。

## 5. 极简Case规则

手动Case只允许保留以下顺序：

```text
复位目标IP
-> 初始化本Case变量和Buffer
-> 配置目标IP
-> 施加一次明确激励
-> 读取一次或少量必要状态/结果
-> 与明确期望比较
-> printf打印配置、实际值、期望值和PASS/FAIL
-> return
```

固定要求：

1. 每个Case开始前必须复位目标IP，再重新初始化该Case使用的变量、Buffer和Driver配置结构。
2. 同一Case切换到另一组独立配置场景前，必须再次复位目标IP并重新初始化变量，不继承上一场景状态。
3. Case按源码从上到下顺序执行，禁止引入状态机、任务调度器、事件总线或异步Session框架。
4. 只调用本IP Driver和完成该Case必需的System、Clock、GPIO、IRQ Driver；禁止为了复用自动化代码调用Service或Wrap。
5. 中断Case只允许使用一个简单`volatile`标志或计数，在本文件直接定义目标IRQ Handler；ISR只记录必要事实。
6. 轮询只保留到达目标观测点所必需的最小循环；禁止增加自动重试、超时恢复、降级路径或替代判据。
7. 发现初始化、Driver调用或期望比较失败时，立即打印当前事实并返回；禁止尝试修复环境后继续伪装同一次测试。
8. 下一Case通过重新复位建立干净状态，不为上一Case编写Cleanup、Rollback、资源释放或失败回滚。

## 6. 明确禁止的复杂度

手动Case禁止出现：

- `goto cleanup`、Cleanup栈、资源作用域和统一资源管理器；
- 重试次数、指数退避、自动重连和多层超时策略；
- ET-Frame编码、命令解析、Service Dispatch和Resource Handle；
- Capability查询、动态实例发现和执行映射解析；
- Mock、Fixture、测试注册表和插件机制；
- 为复用三五行代码建立无业务含义的抽象层；
- 为了让结果变为PASS而改变自动化Case的Feature、输入或期望；
- 同一个函数同时复现多个无关Feature或多个IP。

代码重复少量初始化步骤是允许的；人工可读性优先于为消除几行重复而增加抽象。

## 7. 注释与打印格式

每个Case函数前必须使用简短注释说明：

```c
/*
 * 测试Feature：UART Framing Error状态和Line Error中断。
 * 测试方法：UART1按2个停止位接收，UART2按1个停止位发送，再读取UART1错误状态。
 * 通过条件：UART1产生Framing Error状态且IRQ Handler记录一次Line Error中断。
 */
```

函数内部只在配置、激励、观测和判断四个步骤前增加短注释，不逐行翻译C语句。

串口打印使用稳定、面向人的文本，不输出ET-Frame：

```text
[MANUAL][uart_p1_008] START
[CONFIG] receiver=UART1 stop_bits=2 sender=UART2 stop_bits=1
[OBSERVE] line_status=0x00000000 irq_count=0
[EXPECT] framing_error=1 irq_count>=1
[RESULT] FAIL
[MANUAL][uart_p1_008] END
```

固定要求：

- 必须打印目标芯片、IP实例、Case ID和关键配置；
- 寄存器、Mask和原始状态使用十六进制；长度、次数和时间使用带单位的十进制；
- 必须同时打印实际值和期望值，不能只打印`FAIL`；
- 禁止打印无解释的整块内存、无限日志或自动化协议字节流；
- 诊断UART与被测UART冲突时，必须在手动配置中选择另一实例，禁止共用同一硬件通道。

## 8. PC串口捕获工具

手动诊断的PC工具固定放在：

```text
tools/manual_test/capture_serial_log.py
```

它只负责：

1. 从命令行接收串口号、波特率、超时和输出路径；
2. 原样捕获Firmware打印并附加主机时间戳；
3. 在明确结束标记、用户中止或超时后关闭串口；
4. 把日志保存到`artifacts/records/_DIAGNOSTICS/MANUAL_ET6801/current/`固定现场；复用与保留门禁按R500，不新增时间戳或轮次目录。

它禁止发送ET-Frame、调用自动化PC Driver、重新判断硬件PASS/FAIL、生成Canonical Result或Excel报告。
工具可以显示Firmware打印的`[RESULT]`，但不得修改该结果。

串口号和本机路径必须由命令行传入，禁止写死个人COM口或绝对路径。

## 9. 结果使用边界

手动诊断是补充证据，不能直接覆盖正式自动化Case状态：

| 手动结果 | 后续判断 |
|---|---|
| 手动PASS、自动化FAIL | 优先检查自动化Case、Service/Wrap调用、时序或证据采集链路 |
| 手动FAIL、自动化FAIL | 增强Driver、芯片配置、RTL或硬件Feature问题的证据 |
| 手动无法执行 | 记录缺失环境，不伪造PASS/FAIL |

需要修改正式Case状态时，仍必须回到对应IP契约、自动化代码和正式HIL证据链完成闭环。

SKIP只允许表示当前物理连接、配测设备或仪器环境不能提供必要激励或观测。固件接口未开发、执行映射未配置、
Case代码未完成或测试已经执行但结果不符，均不得用SKIP掩盖。

## 10. 扩展与验证

新增失败Case时只允许：

1. 在对应`et_manual_<ip>_test.c`增加一个线性函数；
2. 在手动测试配置中选择该函数；
3. 编译手动诊断Target；
4. 使用独立串口捕获工具保存打印。

禁止因此修改自动化Framework、Service、Wrap、ET-Frame、PC Case或公共Runner。

实现代码后必须验证：

```powershell
python tools/quality/check_firmware_c_format.py
python tools/quality/check_firmware_c_quality.py --strict-magic <changed-manual-files>
python tools/quality/check_firmware_architecture_rules.py .
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_task_context_governance.py
```

真实编译、下载、运行和串口捕获必须使用手动诊断构建，并按项目硬件人工门禁执行。
