# Agent 经验库索引（experience/）

面向后续 Agent 与人工的可复用操作经验库。**唯一约束正文：[RULES.md](RULES.md)**——写/改/归档
必须遵守 RULES；本索引在每次增删改后同步（RULES §7）。

状态说明：active=现行有效；superseded=已被修复/替代（保留追溯）。

## platform — 平台代码缺陷与行为

- [runner_chip_compare_blocks_publish](platform/runner_chip_compare_blocks_publish.md) — runner芯片比对曾因大小写跳过报告发布；比较侧已与 `target_chip()` 对齐，真不一致仍跳过（superseded）
- [review_cli_relative_source_crash](platform/review_cli_relative_source_crash.md) — 相对路径入口已统一，回归NOT_EXECUTED（active，待验证）

## environment — 本机环境与工具链

- [ps5_gbk_console_encoding](environment/ps5_gbk_console_encoding.md) — PS5.1/GBK控制台的编码崩溃与mojibake，PYTHONUTF8=1启动清单（active）
- [sandbox_and_file_tools](environment/sandbox_and_file_tools.md) — DSH历史工具差异；不可据此绕过当前工具限制（active）
- [external_process_file_locks](environment/external_process_file_locks.md) — 活进程文件锁下的git stash半失败机制与完整恢复法（active）
- [artifact_location_discipline](environment/artifact_location_discipline.md) — 临时脚本放tmp，结论性工具日志放records/_TOOLING（active）

## workflow — 可复用操作 SOP

- [test_execution_runbook](workflow/test_execution_runbook.md) — 全链路HIL执行SOP（脚本-only）：bat/GUI入口、禁止手拼、单IP走run_ip_tests、run_test.bat会跑注册表全集（active）
- [deploy_chain_mechanism](workflow/deploy_chain_mechanism.md) — 五级部署机制：同轮bit+ROM+PFLASH、firmware/start_target互斥、双核脚本、禁止直调.ps1（active）
- [evidence_review_loop](workflow/evidence_review_loop.md) — 已对齐R500：pending复用、Agent整理、禁止迁回runs（active）
- [gate_and_entry_antipattern](workflow/gate_and_entry_antipattern.md) — 保留历史耗时教训；当前门禁只由人工指定（active）
- [multiform_deployment_matrix](workflow/multiform_deployment_matrix.md) — 13个IP分属三种互斥部署形态（单核/双核SPINLOCK/双核IPCM），一次部署只能覆盖同形态IP（active）

## governance — 治理与权威源实践教训

- [case_list_authority](governance/case_list_authority.md) — 注册表是Case清单唯一权威：一次伪造执行表述的险情与双源核对规则（active）
