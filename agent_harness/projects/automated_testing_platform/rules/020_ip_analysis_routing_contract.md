# [R020] IP Analysis Routing Contract

Boundary: 本文件只把 ATP 已有 R002 / R100 / R110 / R120 / R130 / R140 和 ip-package 模块画像投影到公共 Rule Manager；原规则正文仍是唯一 Owner。

## [R020.010] IP Analysis Must Compile The Existing Task Context

Level: MUST
When: 用户要求分析一个 IP、某颗芯片上的 IP、寄存器能力或芯片适配事实时
Rule: 必须按 R002 和 ip-package 模块画像建立 analysis Task Context，解析 module=ip-package、change=analysis、ip、chip、must_read、rule_owners、validation 与 write_scope；路由缺失或参数不确定时必须失败关闭，不能靠 Agent 猜测扩大范围。分析阶段 write_scope.allowed 只能来自项目编译结果。
Refs: report/design/rules/R002_task_context_navigation.md, project-governance/modules/ip-package.yaml, tools/governance/compile_task_context.py, K001.003, K001.004, K001.005, G010.010.010

## [R020.020] IP Analysis Must Use The Registered Source Workflow

Level: MUST
When: 收集、检索、读取或判断 IP 分析资料时
Rule: 必须按 R140 和 project-governance/ip-analysis-sources.yaml 处理项目资料源；每个适用 Source Item 都必须记录 FOUND、NO_MATCH 或 UNAVAILABLE，并保存来源身份、用途、支持的结论及可信或时效状态。外部资料只能作为带 Provenance 的只读来源，不能自动覆盖当前源码、活动规则或项目 Knowledge。
Refs: project-governance/ip-analysis-sources.yaml, report/design/rules/R140_ip_analysis_workflow.md, report/design/rules/R130_canonical_result_evidence.md, K001.008, K001.012

## [R020.030] IP Analysis Output Must Follow The Existing Contract

Level: MUST
When: 形成 IP 分析结果、公共契约、芯片适配文档或 Case 规划时
Rule: 必须按 R100、R110、R120、R130、R140 区分公共 IP 语义与目标芯片事实，并输出项目规则要求的公共 IP 文档与芯片适配文档。文档结构、机器块、Feature / Case 语义、资料处置、冲突与未知项均由当前活动 Owner 规定；不得把未知项、未执行验证或历史 Evidence 写成当前 PASS。
Refs: report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md, report/design/rules/R110_contract_document_sync.md, report/design/rules/R120_public_ip_machine_contract.md, report/design/rules/R130_canonical_result_evidence.md, report/design/rules/R140_ip_analysis_workflow.md, A010.020.010, K001.002, K001.008

## [R020.040] Analysis Must Not Drift Into Implementation

Level: MUST_NOT
When: 当前 Task Context 的 change 为 analysis
Rule: 禁止在分析任务中顺便修改 PC Driver、Formal Case、Firmware Service、Wrap、芯片 SDK、Capability 或硬件执行路径；实现需求必须另建 Task Context，并重新路由对应 Owner、write_scope 与验证。
Refs: project-governance/modules/ip-package.yaml, report/design/rules/R140_ip_analysis_workflow.md, A010.020, K001.005, G010.010.020
