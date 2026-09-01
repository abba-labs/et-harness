# 平台公共层冻结前收口实施计划

时间：2026-08-10 11:30 CST
基线：`review_code@d2de2836e72f55652a6474869263c305db188aa1`
状态：本地软件收口完成，等待exact-SHA CI与独立HIL门禁
范围：PC公共层、UART/DMA/Framework Driver、Formal Case、质量门禁和当前文档；本计划不修改Wire Contract和Firmware硬件执行语义。

## 1. 目标

在不引入新框架、Registry、Workflow或依赖注入机制的前提下，完成公共层冻结前最后一轮收口：

- 新增普通IP时不修改公共Scheduling、Communication和pytest Plugin；
- IP-local Support只准备“能测”的环境事实，不执行Feature动作；
- DMA/UART长操作严格服从一个总Deadline；
- Cleanup只恢复本Case或Driver真实拥有的状态，并保留Primary/Cleanup错误；
- Formal Case按P0～P3、中文注释和Capability事实组织；
- 软件门禁与当前规则、README和实现保持一致；
- 运行语义变化由针对性HIL和最终exact-SHA全量HIL证明。

## 2. 固定边界

```text
Case = 测试流程 + 最终断言 + Evidence + 跨IP Cleanup顺序
Support = Runtime/Capability/Bench/Resolver Gate + Driver构造
Driver = 单IP稳定操作 + 单IP Deadline/Polling/Lifecycle
Codec = 纯Wire
Firmware Service/Wrap = 保持当前单IP执行边界
```

本轮明确不做：

- 不删除DMA CONFIGURE模糊超时后的幂等DECONFIGURE补偿；
- 不把Resource固定池升级为Lease/并行资源框架；
- 不增加BaseDriver、Mixin、Manager或通用Workflow；
- 不修改历史HIL/Review记录以适配新Case ID；
- 不把Software Gate PASS描述为硬件PASS。

## 3. 实施阶段

### 阶段A：规则和Checker一致化

- 统一所有权威文档的Case注释规则：函数前使用三段中文`#`注释，不使用函数Docstring承载Case说明；
- 允许`test_cases/<ip>/conftest.py`和`_support.py`构造Driver并聚合只读事实；
- Checker继续禁止Support执行initialize/configure/start/wait/reset/cleanup/assert；
- 增加合法Support和越界Support的正反向Checker Unit Test。

### 阶段B：公共扩展边界收口

- 将UART/DMA专用Fixture和Support迁入各自Case Package，保持Fixture名称和行为；
- 公共Scheduling只保留Target/Framework/Artifact/Capability/RunContext；
- 具体IP Service ID由`drivers/<ip>/contract.py`拥有；
- IP Marker由IP-local Conftest注册；
- 静态Chip Capability与IP-local Runtime Service Gate分开，第一次Feature Mutation前完成二者校验。

### 阶段C：Evidence与Result通用化

- 使用一个通用Required Evidence Marker声明`dut/peer/fpga/instrument`；
- `record_evidence()`只登记实际消费的证据；
- 删除对`uart_peer_handle`等IP Fixture名称的推导；
- setup/call/teardown多阶段失败按阶段标签合并进现有`error`字段，不增加第二套Status。

### 阶段D：Driver可靠性

- DMA `wait_channel_free/wait_channels_free/wait_irq/wait_irq_count`使用统一`OperationDeadline`并向每次Request传递剩余时间；
- UART `capture_wait()`使用相同Deadline契约；
- UART `exchange()`与DMA `wait_complete()`在`BaseException`下仍执行Cleanup；
- Framework重新发现Service前清除旧Cache，完整校验成功后再发布新Registry；
- 仅在IRQ所有权和退出语义明确且有命令序列Unit Test时增加DMA `irq_mode()`。

### 阶段E：Formal Case迁移

- 删除DMA Case重复Docstring，Framework改为P3文件和三段中文注释；
- 按固定P0～P3语义迁移UART/DMA Case；
- 用Capability提供Instance、Channel Count和传输上限，删除ET6801规模硬编码；
- Lifecycle Scope只恢复实际取得的状态；
- Evidence记录复用实际比较变量，不写第二份literal真值；
- Framework事务数和字节数由Formal Plan计算；
- 建立旧Case ID到新Case ID的迁移表，历史证据保持不变。

### 阶段F：文档和软件验收

- 同步当前Rules、Template、Checklist、README和Case规格；
- 执行`python tools/validate_pc.py`、`git diff --check`和Formal Case Collection；
- 推送后核对exact-SHA `Software Quality Gate / validate-software`。

### 阶段G：硬件验收

- 对DMA Deadline/Cleanup、UART Capture/Exchange和生命周期变化分别执行针对性HIL；
- 最终执行UART、DMA、UART-DMA和Framework全量exact-SHA HIL；
- HIL需要独立人工硬件门禁，原始日志进入`artifacts/`，当前结论进入`report/test_records/`或`report/hil/`。

## 4. 完成条件

```text
公共层无具体IP import/Service ID/Fixture/Marker
+ 新IP Support Checker正反例通过
+ Driver Deadline/Cleanup命令序列测试通过
+ Formal Case无芯片规模硬编码和重复Docstring
+ validate_pc.py PASS
+ exact-SHA CI PASS
+ 运行语义变化对应HIL PASS
```

在上述条件全部满足前，不把公共层标记为`FROZEN`。

## 5. 当前执行结果

截至2026-08-10，本地软件验收结果为：

```text
Python syntax                         PASS
Ruff format / lint                    PASS
PC AST architecture rules             PASS
PC documentation semantics            PASS
Formal Case orchestration rules        PASS
Firmware single-IP execution rules     PASS
ET6801 generated project contract      PASS
PC unit / contract / native            397 passed, 9 skipped
Formal Case collection                 121 nodes
git diff --check                       PASS
```

尚未执行：当前差异的远端exact-SHA CI、实际Keil Build和真实UART/DMA/Framework HIL。上述项目完成前，公共层状态保持`PENDING`。
