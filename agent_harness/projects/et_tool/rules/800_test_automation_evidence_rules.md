# [R800] Test Automation And Evidence Rules

Test/Automation/Evidence 规则域负责单元/集成/硬件验证分层、正式 automation 路径、证据来源、负边界与回归闭环。

## [R800.100] Validation Layer Separation

### [R800.100.010] No Hardware Tests Must Not Be Reported As Hardware Pass

Level: MUST_NOT
When: fake runtime、mock、unit、integration 或 no-hardware 测试通过时
Rule: 禁止把无真实目标硬件参与的测试结果表述为 hardware PASS；硬件结论必须来自正式 hardware validation/evidence 链。
Refs: A060.030.010, A060.030.020, A060.030.030

## [R800.200] Formal Product Automation

### [R800.200.010] Product Automation Must Exercise Formal CLI Boundary

Level: MUST
When: 自动化结果将用于产品验证、回归或 evidence 时
Rule: 自动化必须通过正式 et-cli 产品入口执行目标 operation，禁止直接调用底层 Transport/Probe Driver 并把结果作为正式产品 PASS。
Refs: A060.040.010, A020

## [R800.300] Evidence Provenance

### [R800.300.010] Evidence Must Preserve Operation And Artifact Provenance

Level: MUST
When: 生成或保存用于 capability 判断的测试证据时
Rule: 必须保留对应 operation、Chip、Route、关键输入、结果和 raw artifact/hardware record 的可追溯关系，禁止只保存无法还原来源的 PASS 文本。
Refs: A060.040.020

## [R800.400] Unsupported And Negative Validation

### [R800.400.010] Unsupported Boundaries Require Negative Validation

Level: MUST
When: 某 Chip × Route 当前为 unsupported 或 fail-closed 边界时
Rule: 验证必须证明正式产品入口拒绝该能力，禁止只证明“没有成功脚本”就认为 fail-closed 已成立。
Refs: A010.020.030, A060.030.030.200.030

## [R800.500] GUI Real Executable Validation

### [R800.500.010] GUI Hardware Validation Must Preserve GUI To CLI Product Chain

Level: MUST
When: 使用 GUI real-exe 测试验证真实硬件 operation 时
Rule: 必须验证 GUI → QProcess → et-cli → 正式执行链，禁止用测试注入直接跳过 CLI Bridge 证明 GUI 产品路径正确。
Refs: A030.090, A060.030.030

## [R800.600] Regression Scope

### [R800.600.010] Shared Layer Changes Must Cover Affected Routes And Chips

Level: MUST
When: 修改被多个 Chip 或 Route 复用的 Protocol、Transport、Probe Driver、Platform 或共享 Workflow/Application contract 时
Rule: 必须选择覆盖所有受影响 Chip/Route 的回归集合，禁止只运行触发本次修改的单一路线用例。
Refs: A050, A060.030