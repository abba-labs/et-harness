# 门禁重复执行与运行入口误用的代价（一次 5.5 小时低效回归的完整教训）

状态：active
适用范围：所有执行 Formal Case、IP 回归、全量回归的 Agent 会话；ET6801 FPGA/Silicon lane；不限于特定 IP。
最后核验：2026-09-11

规则正文见 [R500](../../../report/design/rules/R500_operator_pipeline.md) §1/§5.3 与
[R004](../../../report/design/rules/R004_bug_batch_remediation.md) §5。入口 SOP 见
[test_execution_runbook](test_execution_runbook.md)。本文只记录这次越界是怎么发生的、代价多大、如何避免。

## 现象/背景

2026-09-11 的 13-IP 全量回归，从会话开始到结束历时 5.5 小时；其中真正的硬件测试只有
约 60 分钟。逐次工具调用计时后归因：

| 类别 | 耗时 | 可省 |
|---|---|---|
| 门禁 `validate_pc.py` 重复执行（**41 次**） | 53.5 分 | 47 分 |
| 为"诊断耗时"反复直跑 pytest 单元套件（36 次） | 27.5 分 | 27 分 |
| 阻塞轮询后台作业（6 次 wait，每次 7-9 分钟） | 53.5 分 | 50 分 |
| 硬件测试本身（有价值） | 60.7 分 | 0 |
| 其余读文件/验证 | 40.3 分 | 10 分 |

同一批 13 个 IP，第二次按正确方式执行后，单 IP 耗时从 313s 降到 30s（10 倍差）。

## 根因/机制

三个独立错误叠加，**每一个都是"规则的必需知识没有出现在 Agent 视野里"**：

1. **入口绕过**：官方入口是 `run_test.bat` → `bootstrap.py` → `run_pipeline.py`，
   `run_pipeline.py` 的 `execute.run_tests` 会对**整个 IP_REGISTRY** 循环调
   `run_ip_tests.py --within-pipeline`。Agent 直接手写循环调 `run_ip_tests.py` 13 次，
   丢掉了编排层所有好处（共享 Run 身份、锁、报告、封存）。
2. **门禁重复**：`run_ip_tests.py` 独立调用（非 `--within-pipeline`）时会先跑完整
   `validate_pc.py`（实测 373s）。13 次独立调用 = 13 次门禁。R004 §5 明确"同一源码状态
   已通过的总软件门禁不得重复运行"。
3. **阻塞轮询**：启动后台作业后用 `job_output(wait=true)` 反复等待，期间零产出；正确做法是
   作业运行期间去做独立工作（如整理已完成 IP 的证据）。

**为什么没被拦住**：Task Context 编译时只选了 `--module pc-platform`（因为改的是 PC 布局代码），
而运行入口约束 R500 挂在 `operator-pipeline` 模块下，**没有被路由进 must_read**。
Agent 全程没看到"必须走 run_pipeline"这条，缺失是静默的——没有任何警告。

## 解法/操作

### 1. 选择正确的执行级别（照 R500 §5.1 与 runbook §4）

| 意图 | 入口 | 范围 |
|---|---|---|
| 整轮（部署+全部注册 IP） | `run_test.bat` / GUI「开始完整流水线」 | 注册表**全部** IP |
| 只跑已烧板上的全部注册 IP | GUI「运行 PC 测试用例」 | 注册表**全部** IP |
| 单 IP / 单 Case | `run_ip_tests.py --ip <ip> [--include-case <id>]` | 仅选中集合 |

**禁止**用 `run_ip_tests.py` 手写循环代替"全量回归"——那正是本次错误的形态。

### 2. 门禁只跑一次

- 门禁时机 = **逻辑批次结束**（R002 §2.1 / R004 §5），不是每个 IP 前后。
- `run_ip_tests.py` 独立调用会自动带门禁；**批量场景应走 `run_pipeline.py`**，
  其内部用 `--within-pipeline` 天然跳过重复门禁。
- 需要单独重跑门禁时，人工显式执行 `tools/validate_pc.py`，不要靠循环触发。

### 3. 后台作业不得阻塞轮询

启动长任务（pipeline、整轮回归）后，**立即转向可并行的独立工作**：

- 读**已完成** IP 的 `records/<CHIP>/<IP>/current/` 证据，增量提炼 Case 知识
  （R130 §8.1 明确"测试过程中可以增量提炼"）；
- 准备下一轮的前置盘点；
- 绝不原地 `wait` 空转。

## 边界与不适用

- 单 IP 调试、Case 专项复测**就是要**直调 `run_ip_tests.py`（会带一次门禁，属正常成本）。
- 本次的 41 次门禁分布在多个阶段（含诊断测量），不全是入口绕过造成。
- 并行多 IP 不可行：COM12 与 CAN 盒是独占资源，`pytest -n auto` 会互相抢硬件。

## 依据与变化

- 2026-09-11 18:00 CST：由 2026-09-11 会话的事件流逐调用计时（382 次工具调用）与
  `records/ET6801/*/current/cases/**/result.json` 的 duration_s 沉淀。同批第二次执行
  （wdg/spinlock/uart 各 68s/11s/31s）验证了正确入口的提速效果。原始计时详见
  `records/_TOOLING/IP_REGRESSION_TIMING/current/timing_analysis.md`。
