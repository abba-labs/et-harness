# PC 公共层与 UART/DMA Driver 收敛阶段收口报告

日期：2026-08-09
仓库：`Abba-shenfu/Automated_Testing_Platform`
分支：`review_code`
本阶段代码基线：`23a2ec86a7a5ec1dd8dedd7b8fbf58fbd221324e`

## 1. 收口结论

本报告只收口以下两个阶段，不把后续 Case 极简化混入本阶段：

```text
Phase A  公共层 / 芯片无关化             DONE
Phase B  UART / DMA Driver 边界与 Package  DONE
Phase C  Case 极简化                      NEXT / NOT_STARTED
第二芯片扩展验证                           NOT_STARTED
```

本阶段完成的含义是：公共层和 UART/DMA Driver 的职责、依赖方向、扩展位置与软件质量门禁已经形成稳定基线。后续没有新的当前-HEAD 违规证据时，不再为了“代码更短”继续拆 Driver，也不把 Case 生命周期复杂度算作本阶段未完成项。

同时必须明确：**当前 Formal Case 仍包含 `cleanup_actions()` / `case_cleanup_scope()` 等生命周期代码；这不属于本阶段交付目标，也不代表 Case 极简化已经完成。** Case 只保留测试相关代码的设计与实现，作为下一阶段单独处理。

## 2. Phase A：公共层 / 芯片无关化

### 2.1 当前结构

具体芯片执行事实被限制在芯片扩展目录，公共执行模型与加载入口位于通用层：

```text
profiles/chip_execution_mappings/
├── __init__.py
├── dma_routes.py           # 通用类型、通用加载入口
└── et6801/                 # ET6801 具体执行事实
```

公共层通过 Runtime Chip ID 和通用事实模型解析芯片差异，不要求 Core、Driver 或普通 Case 直接 import `et6801` 实现目录。

### 2.2 永久防回退

当前 AST 规则已经覆盖：

- 公共生产代码不得直接 import 具体芯片 execution mapping；
- Formal Case 不得直接 import 具体芯片 execution mapping；
- 芯片中立 PC 代码不得硬编码具体 Chip ID；
- 芯片扩展目录允许保存具体芯片 ID 和芯片事实。

因此新增芯片的预期扩展方式是“新增 capability/mapping 数据或芯片扩展模块”，而不是修改 Core 或在 Driver/Case 中增加 `if chip == ...`。

## 3. Phase B：UART / DMA Driver 收敛

### 3.1 Package 形态

UART 与 DMA 均使用相同职责模板：

```text
drivers/<ip>/
├── __init__.py
├── models.py
├── contract.py
├── codec.py
├── validation.py
└── driver.py
```

当前目录：

```text
drivers/uart/
drivers/dma/
```

### 3.2 Driver 职责已冻结

本阶段确认并固化以下边界：

```text
Driver 可以：
- 提供一个 IP 的稳定业务 API
- 做本 IP 参数校验
- 做本 IP Deadline / Retry / Polling / Cancel
- 调用本 IP Codec / Contract + TargetClient
- 返回稳定 Model
- 做本 IP 内部 rollback / cleanup

Driver 不可以：
- import Profile / Scheduling / Instrument / pytest
- 调用其他 IP Driver
- 读取 Bench 或选择具体芯片
- 执行 pytest.skip
- 执行最终 PASS/FAIL
- 生成 Case 报告
- 隐藏跨 IP 测试流程
```

永久规则 `ETPC214` 等已经把 Driver 的环境/测试编排依赖设为机器门禁。

### 3.3 不继续机械拆 Driver

本阶段的 DONE 标准是**职责边界稳定**，不是追求最短文件。

UART/DMA Driver 中涉及已经验证过的：

- polling / deadline；
- IRQ 状态与等待；
- cleanup / rollback；
- command ordering；
- public API / Wire Contract；

都属于运行语义。没有新的当前-HEAD 违规或故障证据时，不继续为了行数拆成 `BaseDriver`、`Manager`、`Factory`、`Workflow`、`Plugin Registry` 等新抽象。

如果未来第二芯片或真实 HIL 证明某个 Driver 职责必须再次拆分，再以最小证据驱动改动处理。

## 4. 本阶段软件证据

本阶段代码基线：

```text
review_code@23a2ec86a7a5ec1dd8dedd7b8fbf58fbd221324e
```

该 exact SHA 的永久 `Software Quality Gate / validate-software`：

```text
GitHub Actions Run 31299508213  PASS
```

统一软件验证：

```text
Python syntax                         PASS
Ruff format                           PASS
Ruff lint                             PASS
PC AST architecture rules             PASS
PC documentation semantics            PASS
Formal Case orchestration rules       PASS
Firmware single-IP execution rules    PASS
Generated firmware project contract   PASS
PC unit / contract / native            386 passed, 3 skipped
Formal Case collection                 235 nodes
Repository clean after validation      PASS
```

235 个 Formal Case 节点包含当前 DMA、UART 和 Framework Formal Case 的收集结果；它们证明软件定义、Import、Fixture 和参数化成立，不等价于本基线真实板卡执行。

## 5. 本阶段明确没有完成什么

以下项目**不允许被本报告误写为 DONE**：

### 5.1 Case 极简化

当前 Case 仍承担较多生命周期噪音，包括但不限于：

```text
xxx_initialized / xxx_enabled / xxx_configured 状态变量
cleanup_actions()
case_cleanup_scope(...)
部分资源与 Evidence plumbing
```

当前 `AGENTS.md` 和 `pc_code_design_rules.md` 仍要求 Case 持有跨 IP Cleanup 顺序，并要求 Formal Case 使用 `case_cleanup_scope(cleanup_actions)`。因此在下一阶段正式修改设计规则以前，不在本阶段偷偷迁移这些职责。

下一阶段要重新审查的核心问题是：

> 如何让 Formal Case 只保留测试意图、测试配置、Stimulus、Observe 和 Assert，同时保持失败恢复与 HIL 语义可靠。

### 5.2 第二芯片扩展验证

公共层已经为芯片扩展建立边界，但尚未用第二颗芯片完成“新增芯片是否可以不修改 Core / UART Driver / DMA Driver / 公共 Case”的实际接入证明。

因此：

```text
Architecture prepared for second chip  DONE
Second-chip onboarding proof            NOT_STARTED
```

## 6. 硬件状态

本阶段收口没有重新执行本 exact SHA 的 Keil / FPGA / Silicon / HIL：

```text
Keil FPGA Build     NOT_EXECUTED
Keil Silicon Build  NOT_EXECUTED
FPGA/Silicon HIL    NOT_EXECUTED
```

仓库存在更早的 UART/DMA HIL 历史证据，可用于保护已验证运行语义，但不能升级成本阶段 exact SHA 的硬件 PASS。

## 7. 冻结线

从本报告开始，以下内容进入“证据驱动修改”状态：

```text
Core architecture
公共 Chip-neutral dependency boundary
UART Driver responsibility boundary
DMA Driver responsibility boundary
Published Wire / public API
HIL-proven polling / deadline / cleanup / ordering semantics
```

后续 Case 极简化阶段不得顺手重构这些区域。若 Case 简化暴露出 Driver 或公共层真实缺口，必须先给出当前规则违规、当前 HEAD 证据、具体风险和验证方法，再单独修改。

## 8. 下一阶段入口

下一阶段从“Case 设计”重新开始，而不是继续机械删除 Helper。

进入下一阶段时先做：

```text
1. 选一个简单 UART Case 和一个复杂 DMA Case 作为参考样本
2. 区分“测试代码”和“环境生命周期代码”
3. 设计 Case 的目标最小形态
4. 明确 Fixture / Support / Driver 各自应接走什么
5. 评估 cleanup 规则是否需要正式修改
6. 先小范围 Pilot，再批量迁移
```

在该设计完成前，不批量迁移现有 `cleanup_actions()`，不创建新的通用 Workflow/Manager/DI 框架。

## 9. 阶段最终状态

```text
公共层芯片无关化                 DONE
UART Driver 收敛                 DONE
DMA Driver 收敛                  DONE
Driver 软件质量门禁              PASS
Case 极简化                      NEXT
第二芯片扩展验证                 NOT_STARTED
本阶段 exact-SHA Keil/HIL        NOT_EXECUTED
```

**结论：公共层与 UART/DMA Driver 收敛阶段正式结束；下一阶段单独进入 Formal Case 极简化设计。**
