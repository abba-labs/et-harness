---
schema: et.rule-document.v1
number: R004
domain: governance
lifecycle: active
owners: [bug_batch_remediation]
rule_ids: [ET-RULE-BUG-BATCH-REMEDIATION]
---

# R004 批量 Bug 修复策略

## 1. 定位

本文只规定 Agent 同时修复一组 Bug 时，如何冻结范围、建立假设、选择验证、停止重复试验并收口证据。

具体 Case、Firmware、部署、SKIP 和文档同步规则仍分别由 R140、R210、R300、R500 和 R110 拥有；本文只引用，不复制这些规则。

## 2. 开始条件

批量修复开始前必须形成一份有边界的问题清单，每项至少包含：

```text
目标 Case / IP / 模块
已知现象和有效证据
当前判断或待验证假设
用户明确排除项
本轮完成条件
```

用户指定的 Case、IP 或问题集合就是本轮验证范围。禁止因为 Registry 中还存在其他 Case，静默扩大到无关 IP 或全量 HIL。

Task Context必须同时包含：

1. `governance/bug-remediation`，用于加载本文；
2. 实际修改模块的既有路由，用于授权源码范围和专项验证。

`bug-remediation`本身不授权修改业务源码。

## 3. 先分类，再修改

每个问题必须先归入一个主要责任层：

| 分类 | 首查位置 |
|---|---|
| Case刺激或判定错误 | IP文档、Case、历史测试思想和硬件事实 |
| PC调用或编解码错误 | Case、Driver、公共Wire契约 |
| Firmware执行错误 | Service、Wrap、Chip Driver及状态生命周期 |
| 部署或环境错误 | R500、Run Config、镜像和连接证据 |
| 硬件或RTL事实 | 芯片IP文档、SVD、真机证据和人工确认 |
| 原因未知 | 最小诊断或手动测试，不得直接改正式Case |

一个问题只选择一个当前主假设。新证据推翻假设后再换分类，禁止同时修改多个层“试试看”。

## 4. 固定修复链路

```text
冻结问题批次
-> 查阅对应规则、IP文档、源码和已有证据
-> 为一个问题建立一个可证伪假设
-> 必要时用最小手动诊断确认硬件事实
-> Case设计错误时先修正文档契约
-> 只在责任层做最小修复
-> 人工指定后运行目标Case或目标IP专项验证（否则NOT_EXECUTED）
-> 批次内继续处理下一项
-> 批次完成后列出待验证项；仅人工指定后运行总软件门禁
-> 按用户指定范围执行HIL回归
-> 按R110回写实际测试结论
```

手动测试只证明最短 `Chip Driver -> Hardware` 路径。手动PASS而Formal失败时，必须继续检查
`Case -> Driver -> Service -> Wrap -> Chip Driver`、Service状态、启动/停止/复位、Session和资源生命周期；禁止把手动PASS直接写成Formal PASS。

## 5. 测试与部署节奏

批次内每次复测前必须回答：

1. 相比上一次运行，代码、配置、刺激、环境或假设改变了什么？
2. 本次运行验证哪个唯一假设？
3. PASS和FAIL分别会产生什么新结论？

三个问题没有明确答案时，禁止重复运行。

固定节奏：

- 专项测试与总软件门禁的范围、时机均由人工明确指定，Agent不得自行运行；
- 一个IP开发完成、一组同类Bug修完或R002定义的逻辑批次结束后，收口并列出待验证项；未指定执行的验证记录为`NOT_EXECUTED`；
- 同一源码状态已经通过的总软件门禁不得重复运行；
- 只修改PC Case/Driver时，不编译、不烧录也不重启Firmware；
- 修改任何Firmware源码后，当前FPGA环境按R500执行完整 `bitfile -> BootROM -> firmware/PFLASH` 部署；
- 已由用户确认的硬件问题或明确排除项，除非硬件、RTL、环境或测试目标改变，否则不重复测试；
- 为定位问题可以临时只选择相关手动Case或Formal Case，测试完成后必须恢复原选择，禁止形成第二套测试入口。

## 6. 单项停止状态

每个问题只能以以下一种状态结束：

| 状态 | 含义 |
|---|---|
| `FIXED` | 根因已修复，目标专项验证通过 |
| `HARDWARE_FACT` | 已有硬件/RTL事实证明软件无法修复或当前Feature不成立 |
| `ENVIRONMENT_BLOCKED` | 当前硬件连接、仪器或部署环境不足，尚未执行有效测试 |
| `NEEDS_DECISION` | 证据仍不足，需要人工提供规格或决定测试边界 |

执行后得到错误结果属于FAIL，不得改写为SKIP。SKIP条件仍只由R140和R210定义。

## 7. 禁止事项

- 禁止在输入、源码、环境和假设均未变化时重复同一测试；
- 禁止每改几行代码就运行总软件门禁；
- 禁止PC-only变更触发无关Firmware部署；
- 禁止为提高通过率弱化断言、扩大SKIP、删除覆盖或增加无依据Timeout；
- 禁止修一个IP时修改其他IP或冻结公共层；确有公共缺陷必须先提供跨IP证据并获得用户批准；
- 禁止把诊断脚本、手动测试或历史样例当成正式Case PASS；
- 禁止因一次失败同时改Case、Driver、Service和Wrap，使根因不可追踪。

## 8. 最小路由示例

修复UART一组Formal Case问题时：

```powershell
python tools/governance/compile_task_context.py compile `
  --task-id UART-BUG-BATCH-001 `
  --intent "修复已确认的UART Formal Case问题批次" `
  --module governance --change bug-remediation `
  --module ip-package --change case --change driver `
  --ip uart --lane pc
```

如果实际Diff需要Firmware Service，再重新编译扩围后的Task Context并增加`--change service`；不得预先授权未使用的层。

## 9. 验证

```powershell
python tools/governance/compile_task_context.py scope-check
python tools/quality/validate_rule_governance.py
python -m pytest -q pc/et_test_platform/framework_validation/unit/code_quality/test_task_context_governance.py
python tools/validate_pc.py
```

硬件验证范围和部署步骤由用户指令与R500共同决定，不能由本规则自动扩大。
