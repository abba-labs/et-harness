# CRC 第一批实际改造：显式复位与基础向量样板

- 仓库：`abba-labs/et-harness`；分支：`chatgpt_review`。
- 修改前源码：`5eb0781ea7255b72f14f521aaa38b49b0a1e80a3`。
- 本批代码与测试提交终点：`536b266ac62e49c82c908878372c468cfe6e9811`；之后文档提交不改变被测运行代码。
- 状态：**第一批实现已提交，26 项针对性隔离测试通过；完整集成、全仓门禁、目标构建和 HIL 未执行。不是 CRC 全量改造完成或可发布版本声明。**

## 1. 范围与实际结果

只迁移 `test_crc_p0_002_mode_reference_vectors`，保留原稳定 ID、CRC8/CRC16/CRC32 三个参数和全部原向量。CRC_P0_001、CRC_P0_003、CRC P1/P2/P3、CAN 及公共报告程序没有在本批改写。

以格式化前后均相同的物理行口径统计：不含函数签名、空行和独立注释；多行参数照常计数。

| 指标 | 修改前 | 修改后 |
|---|---:|---:|
| 基础向量 Case 正文代码行 | 67 | 13 |
| 函数跨度（def 至最后一句，包含空行和注释） | 89 | 21 |
| 固定向量 | 3 | 3 |
| 决定性 assert | 4 | 4 |

正文就是：`crc_handle = crc0` → `reset()` → 独立 Expected 复核 → Resource create/write → CRC enable/configure → calculate/result_get → 明确断言。没有整条测试的隐藏执行函数，没有把硬件判定移到 Driver。

## 2. 删除、移动和保留对照

| 原有内容 | 处理与去向 |
|---|---|
| Case 显式 CRG 与两次前置 Resource reset | 合并到一次 `CrcDriver.reset()`，加入真实软件上下文清理；不附加 CRC Mask/Disable/Clear 基线写 |
| resource_owned/crc_enabled、cleanup_actions、case_cleanup_scope | 此单次同步样板的固定收尾由 crc0 Fixture 负责；没有隐藏初始 reset |
| CRC8/16/32 polynomial、seed、reflection、byte_swap、xor_out、payload、固定 Expected | `_P0_MODE_VECTORS` 原样保留；Golden 算法未改 |
| `expected == fixed_expected` | 留在 Case |
| `measured.result == expected` | 留在 Case |
| `measured.remaining_input_count == 0` | 留在 Case |
| `readback == expected` | 留在 Case；独立 RESULT_GET 请求保留 |
| 三项 record_observation | 由运行层 RecordedCrcDriver 保存 super 调用的真实返回值，不追加设备请求 |
| 原模式、Expected、payload hash、长度、JSON 文件 | 由 crc_reference_evidence 发布，保留旧文件名和字段；新增 result_readback |
| 断言失败时附件未写入 | 改为证据 Fixture 收尾发布，未观测值为 null，不补造零或 PASS |
| 自动选代表实例 | 该样板明确 crc0；没有 crc0 时明确报错，不静默切换其他实例 |

关键被测顺序仍是：分配 → 写入输入 → enable → configure → calculate → result_get → 判定。PC 能力缓存因 reset 失效后，calculate 会按原 `_runtime_maximum()` 逻辑重新查询只读能力；不是新增硬件配置。

注意：本批观察适配器会在 calculate 返回后、result_get 前保存数据。这适用于无后台输入的稳定 CRC 基础计算，不证明它适用于中断首现场、紧凑输入或性能测试；这些 Case 后续必须独立审核。

## 3. 复位不是伪接口

### 3.1 PC

`pc/et_test_platform/drivers/crc/driver.py` 已新增 `reset()`：

```text
失效本对象的模式和能力缓存
→ 现有 CrgDriver.reset(CRC, selected_instance)
→ 新增 CRC.CONTEXT_RESET（0x0015，空 body）
→ 现有 ResourceDriver.reset()
```

任一步失败立即向上抛出，不执行后续请求。CONTEXT_RESET 响应非空视为协议错误，不继续清池。三次请求不是原子事务，已经完成的硬件动作不会回滚。

旧 CrcDriver 的 27 个已有方法通过本地 AST 对照保持不变，本批没有删除它们的校验、IRQ 或性能逻辑。此项只证明源码未改，不能代替这些方法的回归测试。

### 3.2 Firmware

`firmware/services/src/et_crc_service.c` 中实际 dispatcher 已接入 `handle_context_reset()`；命令枚举在 PC 与固件同步追加为 `0x0015`。

处理实际 IRQ Manager 绑定表内归属于本 CRC callback/context 的记录，包括本地 irq_bound 标志为 0 的残留绑定。解绑全部成功后才清本 Service 的 enabled/configured/mode、IRQ owned/bound、计数、last_event/last_raw、route；保留身份、优先级、Manager 指针和 descriptor。

本函数不访问 CRC Wrap，不补写 CRC 寄存器，不清全局 IRQ Manager，不处理其他实例，不配置被测模式。当前 CRC 没有 generation 字段，不能照搬 CAN 文档声称“代次更新”。

前置条件是 CRC 硬件已由 CRG 复位，且独立 DMA 等资源访问者已停止。这是调用约定，不是该软件命令能够自行证明的硬件事实。接口详见仓库根 `test_case_doc/crc/crc_context_reset.md`。

## 4. 记录和收尾如何与短 Case 接通

`crc0` Fixture 的 yield 之前只核对实例与服务、构造记录适配对象，不修改硬件。Case 仍须在正文调用 reset。

`RecordedCrcDriver` 位于 scheduling 层：调用原 Driver，保留已返回的 CrcCalculateResult/int，登记实际观测；没有 Expected、Golden 或最终 PASS/FAIL。

`crc_reference_evidence` 依赖 crc0，在 Case 执行前登记输入元数据和附件位置。收尾发布已取得值，然后 crc0 收尾关闭 CRC 并清池。只在初始 reset 成功时允许退出清池；reset 或 disable 失败将本次 session 标记停止，异常不吞掉。

该 Fixture 本批只用于一个不启动 DMA 的同步计算 Case。不能拿它替代 DMA/IRQ/连续输入场景的所有权和失败收尾。原始证据仍保存，公共报告 FAIL-only 备注没有在本批修改。

## 5. 本轮真实执行的验证

环境：Linux、CPython 3.13.5、pytest 9.0.2、Debian cc 14.2.0。不是用户 Windows/Keil 环境。

本环境无法通过 Git DNS 克隆完整仓库。通过 GitHub 连接读取固定 SHA 的必要源文件，复制后逐个核对 Git blob SHA；在这个**部分源码快照**中进行以下测试，未伪装为完整 Git 工作区。

### 5.1 Python：20 项通过

文件：`pc/et_test_platform/framework_validation/unit/drivers/crc/test_crc_reference_isolated.py`。

以 AST 装载并执行实际 Model、Codec、Validation、CrcDriver、记录适配、Fixture 和基础 Case 的定义。Target、CRG、Resource、记录/JSON边界使用显式替身；Fixture generator 被直接驱动，未启动全平台 pytest 生命周期。

覆盖：三份原向量的正常路径；实际结果错误、剩余数非零、独立读回错误共九个负例；CRG/CONTEXT_RESET/Resource 失败与非空响应；缺少 crc0 不回退；收尾 disable 失败不吞掉且不继续清池；未读值不造证据；13 行及四断言/命令编号检查。

该测试证明实际 Case 正文能在严格边界下发现这些错误，不证明包导入、真实 TargetClient/Transport、真正 Resource 分配、完整 Canonical Report 或 MCU 工作。

### 5.2 C：6 项通过

文件：`pc/et_test_platform/framework_validation/unit/firmware_contract/test_crc_context_reset_native.py`。

使用 `-std=c11 -Wall -Wextra -Werror` 编译完整实际 `et_crc_service.c` 和实际 CRC Service 头文件，通过其真实 descriptor.handle 调用新命令。

IRQ Manager、CRC Wrap、Router/Factory 类型边界与状态常量使用测试替身。六个场景：正常绑定、残留半绑定、解绑失败、非空请求、缺少 Manager、已经解绑/重复复位。检查其他 Owner 不变、Service 身份保留、软件记录清理、不发生 CRC Wrap 调用。

这不是实际 IRQ Manager/NVIC 联调，也不是芯片 Wrap/SDK 或目标固件构建。

### 5.3 实际命令与输出

在部分源码快照根执行的等价相对路径命令：

```bash
python -m pytest -q -p no:cacheprovider \
  pc/et_test_platform/framework_validation/unit/drivers/crc/test_crc_reference_isolated.py \
  pc/et_test_platform/framework_validation/unit/firmware_contract/test_crc_context_reset_native.py
```

最终重跑原始汇总：

```text
..........................                                               [100%]
26 passed in 0.15s
```

另完成 Python AST 语法检查、原向量/未改函数 AST 对照、原文件 blob 完整性校验。提交内容按 blob SHA 与本地受测文件核对；不包含下载用的未修改依赖、缓存、pyc、临时脚本或 native 可执行文件。

## 6. 未执行项目和下一步验收

以下全部为 **NOT_EXECUTED / NOT_VERIFIED**，不能由26项隔离测试替代：

- 完整仓库 Task Context 编译、scope-check、`tools/validate_pc.py`、全仓格式/规则检查。
- 真正包导入、原 CRC 全部单元测试与 Formal collect、真实 TargetClient/Transport 集成。
- 真实 IRQ Manager 与 Wrap 的链接及失败恢复联调。
- Canonical Result 与最终人工报告的端到端执行；Fixture call/teardown 同时失败的全平台聚合验证。
- Keil/目标固件构建、精确代码 SHA 的 CI、FPGA/Silicon HIL。

R200 原有跨 Driver 调用边界与用户批准的固定 reset 例外、R210 记录与收尾边界仍需在完整工作区作精确同步并跑检查；本批没有关闭检查器、修改全局规则或谎称门禁通过。`crc.md` 的主契约与新增补充接口说明也应纳入下一次完整契约同步检查。

第一次实际运行前必须构建并部署含 CRC 0x0015 的固件；旧固件会明确拒绝新命令。本批没有执行烧录或任何真实台架动作。

先完成上述真实链路集成与三向量 HIL，再迁移 CRC_P0_003 或 P1。不要把本次1条稳定Case的成功隔离测试扩大成“全部CRC已优化/已硬件通过”。CAN仍保留原复核状态，未由本批修改。
