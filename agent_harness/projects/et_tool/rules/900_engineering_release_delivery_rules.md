# [R900] Engineering Release And Delivery Rules

跨域工程规则负责 release/package、build/composition、依赖方向、客户交付与共享变更回归。具体业务规则仍归各自 R100–R800 canonical 规则域。

## [R900.100] Release Packaging

### [R900.100.010] Release Package Must Come From Formal Release Pipeline

Level: MUST
When: 生成客户 release、factory package 或正式交付物时
Rule: 必须通过正式 release config、build、test、package、hash 与 launch-smoke 链生成，禁止把开发目录中的临时可执行文件直接当作正式交付物。
Refs: A060.050.020

## [R900.200] Customer Visibility

### [R900.200.010] Customer Surface Must Follow Release Configuration

Level: MUST
When: 决定客户版本中 chip、route、page 或 action 是否可见时
Rule: 必须通过正式 release visibility/configuration 控制客户 surface，禁止依赖开发构建中“代码存在”自动暴露功能。
Refs: A060.050.010, A030.100

## [R900.300] Build And Composition

本节首要构建约束：凡涉及 ET-TOOL 编译构建，统一进入 `source/release/` 正式构建流水线，不允许人工或 Agent 自行拼接构建命令替代该入口。

### [R900.300.010] Build Composition Must Preserve Module Boundaries

Level: MUST
When: 修改 CMake、模块组合或可执行目标依赖时
Rule: 必须保持现有分层与 chip/route 隔离边界，禁止通过构建依赖把上层 GUI/CLI 直接绑定到本应由 Backend/Transport/Probe/Platform 封装的底层实现。
Refs: A050

### [R900.300.020] Compilation And Build Must Use Release Scripts

Level: MUST
When: 涉及 ET-TOOL 的 CMake configure、编译、构建、链接、package 或任何需要生成/刷新构建产物的操作时
Rule: 必须通过 `source/release/` 下的正式脚本执行；当前统一入口为 `source/release/release_gui.bat`，开发构建使用其 `--mode dev` 等正式参数。禁止人工或 Agent 手工拼接 `cmake`、`ninja`、`ctest`、`make/nmake`、`msbuild/devenv`、Shell/PowerShell 命令链绕过 Release 构建流水线。
Enforcement: ACTION_GUARD
Action: PRODUCT_BUILD
Allow: [source/release/release_gui.bat]
Deny: [cmake, ninja, ctest, make, nmake, msbuild, devenv, meson]
Refs: A060.050.020, A050, A060.030

## [R900.400] Dependency Direction

### [R900.400.010] Shared Lower Layers Must Not Depend On Product Surfaces

Level: MUST_NOT
When: 修改 Domain、Protocol、Transport、Probe Driver 或 Platform 等共享低层模块时
Rule: 禁止依赖 GUI、chip-local CLI 或 release surface；需要产品语义时必须通过上层 contract 注入或 composition 连接。
Refs: A050.010, A050.020, A050.030

## [R900.500] Change Consistency

### [R900.500.010] Contract Changes Must Update Dependent Validation

Level: MUST
When: 修改公开 Application/Workflow contract、CLI result/progress contract、Profile schema/语义或共享 route contract 时
Rule: 必须同步更新受影响测试、Automation 或验证入口，禁止只改生产合同而保留已失真的旧验证。
Refs: A020.070, A060.030, A060.040

## [R900.600] Architecture Resource Consistency

### [R900.600.010] Moved Canonical Resources Must Update Architecture Navigation

Level: MUST
When: 被 Architecture `Resources` 引用的 canonical 代码、Profile、测试或 Automation 入口移动、改名或被替换时
Rule: 必须同步更新对应 Architecture Resource/Relation，禁止让 Agent 导航继续指向失效入口。
Refs: A010, A020, A030, A040, A050, A060