# Phase 0～2 第一批重构 Review

文档状态：正式 Review 结论  
Review 日期：2026-08-06  
目标仓库：`Abba-shenfu/Automated_Testing_Platform`  
目标分支：`review_code`  
代码验证基线：`fb64ff6fef2d8ceb3cc49851403a4198616cab71`  
GitHub Actions：`PC Quality Gate` Run `31080015924`

---

## 1. Review 结论

第一批规定范围已经完成：

- Phase 0：Baseline Tests —— `DONE`；
- Phase 1：PC Quality Gate —— `DONE`；
- Phase 2：PC Core Reliability —— `DONE`。

本批次没有修改 Firmware Wire Contract、DMA/SYSCTRL/UART Command 语义、HIL Case 业务逻辑或 DMA/UART Driver 目录结构。现有公开导入、已发布 Command ID、Body Size 和代表性 Wire Bytes 已由基线测试锁定。

结论：**允许进入 Phase 3：DMA PC Package 行为保持型迁移。**

---

## 2. Phase 0：基线与问题锁定

### 新增基线

- Public Driver Import Baseline；
- Service ID / Command ID Stability；
- 已发布 Body Size Stability；
- DMA 64-Byte Configure Golden Vector；
- TargetClient 单次 Timeout 非法值回归；
- Event Queue Overflow 可观测回归；
- Framework 新 HELLO 后旧 Service Registry 不可复用回归。

主要文件：

```text
pc/et_test_platform/framework_validation/unit/baseline/
├── test_public_api_and_wire_baseline.py
└── test_core_reliability_regressions.py
```

仓库原有的 Driver Contract、Firmware Contract、C/Native 可靠性测试继续纳入全量单元测试入口，没有通过修改既有期望来掩盖生产代码问题。

### 结论

- 合法公共 API 和 Wire 已锁定；
- Phase 2 对应缺陷具有自动回归；
- 本阶段没有改变 Wire 语义。

---

## 3. Phase 1：PC 质量门禁

### 新增能力

- `pyproject.toml` 增加 Ruff Format/Lint、Import Sorting、Bugbear、Upgrade、Simplify 和 McCabe 配置；
- 新增 `tools/check_pc_code_rules.py`；
- 新增统一入口 `python tools/validate_pc.py`；
- 新增 Checker 正反单元测试；
- 新增 `.github/workflows/pc-quality.yml`，对 `review_code` 的每次 Push 自动执行统一入口。

### AST 规则

已实现并测试：

```text
ETPC000  Python Syntax
ETPC001  Module Docstring
ETPC006  Driver 跨 IP 导入
ETPC104  硬件 Case 固定 Docstring 章节
ETPC202  Model 禁止 encode/decode/send/request
ETPC205  Driver 禁止直接 struct.pack/unpack
ETPC206  Codec 禁止导入 TargetClient
ETPC207  Case 禁止导入 Codec/Contract/Transport
ETPC301  Hardware Case 存在性
ETPC401  禁止 except Exception: pass
ETPC403  Production 禁止 assert
ETPC410  Public API 类型标注
ETPC411  禁止新增模糊文件名
```

### 迁移范围

当前 Ruff/AST 全规则应用于第一批新增或修改范围；历史文件仍按后续 IP Phase 逐步纳入。当前仅保留两个明确、可删除的 McCabe 迁移项：

- `pc/et_test_platform/clients/target.py`；
- `tools/check_pc_code_rules.py`。

没有执行全仓自动格式化，也没有把新文件加入历史 Allowlist。

---

## 4. Phase 2：PC Core Reliability

### Deadline

新增：

```text
pc/et_test_platform/core/deadline.py
```

提供：

- `OperationDeadline.start()`；
- 基于 `time.monotonic()` 的严格总时间预算；
- `remaining_s()`；
- 不越过总 Deadline 的受限 Sleep；
- 可注入 Clock/Sleep 的 Fake Clock 测试；
- 零、负值、NaN、Infinity 和 Bool 拒绝。

### Cleanup

新增：

```text
pc/et_test_platform/core/cleanup.py
```

提供：

- `CleanupFailure`；
- `OperationCleanupError`；
- `run_cleanup()`；
- `raise_with_cleanup()`；
- Primary Error 与多个有序 Cleanup Error 同时保留；
- Cleanup 继续执行，不因第一个失败而隐藏后续事实。

### TargetClient

完成：

- 构造级和每次调用级 Timeout 必须是正有限数；
- Retry-safe 请求的多次尝试共享同一个总 Deadline；
- 保持 Mutating Command 默认不 Retry；
- 固定容量 Event Queue 在覆盖最旧 Event 时增加 `event_overflow_count`；
- Event Overflow 不再静默；
- Session 变化时清除旧 Event 和 Overflow 事实。

### Framework Session Cache

完成：

- 每次 `hello()` 开始前清除旧 `HelloInfo`；
- 每次 `hello()` 开始前清除旧 Runtime Service Registry；
- 新 Session 必须重新 `discover_services()`；
- HELLO 失败或 Session 重建后不能继续读取旧 Cache。

---

## 5. 自动验证证据

GitHub Actions：

```text
Workflow : PC Quality Gate
Run ID   : 31080015924
Commit   : fb64ff6fef2d8ceb3cc49851403a4198616cab71
Result   : SUCCESS
```

统一入口实际完成：

```text
Python Syntax                         PASS
Ruff Format Check                     PASS
Ruff Lint                             PASS
PC AST Architecture Rules             PASS
Committed Keil Artifact Contract      PASS
PC Unit / Contract Tests              269 passed, 3 skipped
```

三个环境门禁 Skip 保持为 Skip，未写成 PASS。

说明：本批次只验证已提交 Keil Project/Options/J-Link 支撑文件的仓库 Contract 与 Hash，不等同于真实 Keil 编译。

---

## 6. Wire 与公共 API

- Firmware Wire Contract：未修改；
- 已发布 Command ID：未修改；
- 已发布 Body Layout：未修改；
- DMA/SYSCTRL/UART Command 语义：未修改；
- DMA/UART Public Import：未修改；
- 新增公共内容仅为 PC Core Reliability Primitive 和 TargetClient 可观测属性。

---

## 7. C Syntax、Native、Keil 与 HIL

| 验证层级 | 本批状态 | 说明 |
|---|---|---|
| Python Syntax/Ruff/AST | PASS | GitHub Actions 实际执行 |
| Host Unit/Contract | PASS | 269 passed，3 skipped |
| 已有 C/Native Contract | 随全量测试执行 | 未把环境 Skip 改写为 PASS |
| Keil Build | NOT_EXECUTED | 不属于第一批；仅验证提交物 Contract |
| 真实 HIL | NOT_EXECUTED | 不属于第一批 |

---

## 8. 未关闭风险与后续约束

1. `OperationDeadline` 和 Cleanup 聚合已经成为公共基础，但 DMA/UART Driver 的全面接入分别属于 Phase 7 和 Phase 8；
2. Ruff/AST 当前是明确迁移范围，不代表历史 PC 全仓已无违规；后续每完成一个 IP Package 必须扩大范围并删除对应迁移项；
3. Keil FPGA/Silicon 实际构建及真实 HIL 尚未执行，不能评价整体重构完成；
4. 本批没有开始 DMA 文件拆分、Execution Mapping、SYSCTRL V2 或 Firmware 去 Registry。

---

## 9. 是否允许进入下一阶段

允许进入：

```text
Phase 3：DMA PC Package 行为保持型迁移
```

进入 Phase 3 后仍必须遵守：

- 先保持 Public Import、Command ID 和 Golden Bytes；
- 结构迁移不混入 Wire 改义；
- DMA Package 新文件立即受完整 Ruff/AST 规则约束；
- Phase 3 Review 通过后才能进入 Execution Mapping 与 SYSCTRL V2。
