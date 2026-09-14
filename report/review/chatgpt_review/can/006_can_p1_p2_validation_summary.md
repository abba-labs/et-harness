# CAN P1/P2 极简重构验证汇总报告 (Stage F)

> **对应指导**：`report/review/chatgpt_review/can/003_can_p1_p2_agent_execution_guide.md`  
> **审查报告工件**：`report/review/chatgpt_review/can/005_can_p1_p2_self_review.md`  
> **代码基线 SHA**：`d6b91b65fd96c04f80e87e954c463be48607288b`  
> **工作区与分支**：`et-harness` (`chatgpt_review`)

---

## 1. 验证元数据与环境

* **源码分支**：`chatgpt_review`
* **目标芯片 / 代表实例**：ET6801 (`can0` 默认逻辑实例)
* **固件构建版本**：`ET_CAN_COMMAND_COUNT = 99`，支持 `ET_CAN_COMMAND_CONTEXT_RESET = 98u`
* **执行环境**：Python 3.12 (CPython x86_64, Windows), pytest 8.3+, uv 虚拟环境
* **运行入口**：
  - 驱动合同与软件契约单元测试：`uv run --extra test pytest pc/et_test_platform/framework_validation/unit/drivers/can/test_can_driver.py`
  - 测试用例收集与静态语法验证：`uv run --extra test pytest --collect-only -q pc/et_test_platform/test_cases/can/`
  - HIL 上板回归运行入口（硬件就绪时）：`python tools/runner/run_ip_tests.py --ip can --target dut --bench <bench_path> --lane hil`

---

## 2. 软件层级测试与收集结果

### 2.1 驱动契约与原子复位验证
* **测试文件**：`pc/et_test_platform/framework_validation/unit/drivers/can/test_can_driver.py`
* **测试用例数**：**210 项**（含新增 `test_can_driver_reset_golden`）
* **测试结果**：**210 passed in 0.49s (100% PASS)**
* **验证事实**：
  1. `CanDriver.reset()` 原子发送 CRG 复位 (0x0012, CMD 2)、CAN CONTEXT_RESET (0x010C, CMD 98) 与 Resource 复位 (0x0010, CMD 1)；
  2. 全部 98 项旧公共命令与 99 项 Wire 字段定义严格向前兼容；
  3. 异常边界与数据编码/解码完全符合契约规范。

### 2.2 Formal Case 静态收集与参数矩阵完整性
* **收集范围**：`pc/et_test_platform/test_cases/can/` 下全部 27 个稳定 Case
* **收集结果**：**全量 148 个参数化执行节点 100% 正常收集，零报错、零签名不匹配**
* **分模块收集节点明细**：
  - `test_can_p0.py`：3 个节点 (基准兼容未修改)
  - `test_can_p1.py`：90 个节点 (含 p1_001 24节点, p1_002 20节点, p1_003 22节点, p1_004 4节点, p1_005 2节点, p1_006 4节点, p1_007 1节点, p1_008 3节点, p1_009 1节点, p1_011 6节点, p1_015 1节点, p1_016 1节点)
  - `test_can_p1_format.py`：8 个节点 (p1_020)
  - `test_can_p1_marker.py`：2 个节点 (p1_010)
  - `test_can_p1_rates.py`：9 个节点 (p1_012)
  - `test_can_p1_tdc.py`：2 个节点 (p1_021)
  - `test_can_p1_timeout.py`：4 个节点 (p1_014)
  - `test_can_p1_timestamp.py`：3 个节点 (p1_013)
  - `test_can_p1_tsu.py`：4 个节点 (p1_018)
  - `test_can_p2.py`：1 个节点 (p2_004)
  - `test_can_p2_dmu.py`：3 个节点 (p2_001, p2_002)
  - `test_can_p2_dmu_errors.py`：9 个节点 (p2_007)
  - `test_can_p2_dmu_tsu.py`：5 个节点 (p2_008)
  - `test_can_p2_ecc.py`：2 个节点 (p2_003)
  - `test_can_p2_loopback.py`：1 个节点 (p2_005)
  - `test_can_p2_watchdog.py`：1 个节点 (p2_010)
  - `test_can_p3.py`：1 个节点 (基准兼容未修改)

### 2.3 语法、类型与代码质量检查
* `lens_diagnostics(mode="all")` 与 LSP 诊断：
  - 全部修改过的 12 个 Python/C 文件：**0 blocking errors (Confirmed clean)**。

---

## 3. 硬件在环 (HIL) 执行状态声明

* **当前状态**：**`HIL_NOT_EXECUTED`**
* **未执行原因**：当前工作会话位于代码重构与本地自检沙箱环境，尚未挂接物理单片机硬件台架与测试板卡。
* **上板前建议测试顺序**：
  1. 挂接板卡后，先烧录包含 `CONTEXT_RESET` (CMD 98) 的最新测试固件；
  2. 首先运行样板用例：`python tools/runner/run_ip_tests.py --ip can --include-case can_p2_003`；
  3. 确认样板用例在真实硬件上 PASS 后，全量回归 CAN P1/P2。\n