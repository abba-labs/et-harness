# [R100] GUI Rules

GUI 规则域负责布局与视觉基线、连接页/工作台流转、交互终态、连接生命周期、实时进度、CLI Bridge、芯片 GUI 隔离、语义配色、功能区可见性和发布可见性。后续 GUI 细则继续在本文件扩展，不为单个控件或单个页面另建规则文件。

## [R100.100] Layout And Visual Rendering

### [R100.100.010] Presentation Must Not Define Product Support

Level: MUST_NOT
When: 修改 GUI 布局、颜色、字体、边框、图标或状态渲染时
Rule: 禁止通过表现层硬编码或推导 Chip × Route × Capability 的支持结论；产品支持状态必须来自正式 Profile/Release 状态链。
Refs: A030, A060.010, A060.050

### [R100.100.020] Layout Must Be Compact And Structured

Level: MUST
When: 新增或修改 GUI 页面、功能区、表单、工具栏或工作台布局时
Rule: GUI 必须保持紧凑、整齐和结构化；相关控件必须按功能分区并保持清晰对齐、稳定层级和合理信息密度，禁止无意义的大面积留白、松散排列或视觉割裂。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

### [R100.100.030] GUI Must Follow ET Red And White Visual Baseline

Level: MUST
When: 新增或修改 GUI 主题、颜色、背景、边框、按钮、功能区或视觉样式时
Rule: ET-TOOL GUI 必须继承统一的 ET 红白视觉基线：白色与浅灰作为主要界面和功能区底色，ET 品牌红作为品牌强调和关键视觉锚点；禁止为单颗芯片自行创建脱离该基线的独立主题。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

## [R100.200] Interaction And UI State

### [R100.200.010] UI Must Enter Explicit Terminal State

Level: MUST
When: GUI 发起的操作进入 success、failure、timeout 或 cancel 终态时
Rule: 必须同步收敛相关控件、session 和操作状态，禁止遗留仍显示 running/loading 的伪运行状态。
Refs: A030.020, A030.090

### [R100.200.020] Connection Page Must Be The Initial Page

Level: MUST
When: ET-TOOL GUI 启动、重新进入产品入口或从芯片工作台返回首页时
Rule: GUI 必须首先呈现连接页，由用户完成芯片、通道和连接参数选择；禁止软件启动后直接进入某颗芯片的功能工作台。
Refs: A030, A030.020, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

### [R100.200.030] Function Workspace Requires Successful Connection

Level: MUST
When: GUI 准备从连接页进入芯片功能工作台时
Rule: 只有在正式连接成功并完成必要的芯片识别与准入后，才允许进入对应芯片功能页；连接、识别或准入失败时必须停留在连接流程并暴露明确失败状态。
Refs: A030.020, A030.030, A030.040, A030.050, A060.010

## [R100.300] Connection Timeout And Cleanup

### [R100.300.010] Timeout Must Close Operation Lifecycle

Level: MUST
When: connect、identify 或 GUI 发起的长操作超过正式 deadline 时
Rule: 必须结束或取消关联子进程，释放对应 session/connection 上下文，结束进度状态并向用户暴露明确失败终态。
Refs: A030.020, A030.090, A020.070

## [R100.400] Progress And Long Running Operations

### [R100.400.010] Progress Must Have One Terminal Outcome

Level: MUST
When: GUI 展示由 CLI 或长任务驱动的进度时
Rule: 每次进度生命周期必须最终收敛到 success、failure、timeout 或 cancel 之一，禁止进度条在底层操作结束后继续保持活动状态。
Refs: A030.090, A020.070

### [R100.400.020] Active Progress Must Refresh Continuously

Level: MUST
When: GUI 展示 program、erase、read、write、verify 或其他可观察长操作的运行进度时
Rule: 操作运行期间必须持续消费正式 progress contract 产生的新进度并刷新界面；确定进度必须来自 Backend/Algorithm 已确认的 current/total，无法确定百分比时使用明确的 indeterminate/busy 状态，禁止等待操作结束后一次性跳到 100% 或使用 elapsed time 伪造真实百分比。
Refs: A030.090, A020.070, doc/current_design_analysis/09_PROGRESS_AND_TIMING_MODEL.md

## [R100.500] CLI Bridge And Process Invocation

### [R100.500.010] Hardware Actions Must Use Formal CLI Path

Level: MUST
When: GUI 触发 UART、CAN、CANFD、CMSIS-DAP 或 J-Link 的硬件产品操作时
Rule: 必须通过正式 et-cli argv 与 QProcess 产品链发起操作，禁止 GUI 直接打开底层 Transport、Probe Driver 或 Vendor Runtime 执行硬件动作。
Refs: A030.090, A020, A050

## [R100.600] Release Visibility

### [R100.600.010] Visibility Must Not Be Treated As Support

Level: MUST_NOT
When: GUI 根据 release 配置显示或隐藏 chip、route、page 或 action 时
Rule: 禁止把 release visible 解释为 Profile admitted 或 hardware PASS；支持与证据状态必须分别查询正式产品状态链。
Refs: A030.100, A060.010, A060.050

## [R100.700] Chip GUI Architecture

### [R100.700.010] Chip GUI Implementations Must Remain Independent

Level: MUST
When: 新增或修改 ET3101、ET6002、ET6003 或后续芯片的 chip-local GUI 功能工作台和业务实现时
Rule: 不同芯片的 chip-local GUI 业务代码必须保持独立；禁止一颗芯片的 GUI 直接依赖、调用或复用另一颗芯片的专属 GUI 业务实现。跨芯片通用控件与视觉基础设施必须下沉到明确的 shared GUI 层。
Refs: A030.030, A030.040, A030.050

### [R100.700.020] All Chip GUIs Must Share One Visual Language

Level: MUST
When: 新增芯片 GUI、修改任一芯片工作台或引入跨芯片通用控件时
Rule: 各芯片 GUI 业务代码保持独立的同时，必须使用统一视觉语言；品牌颜色、字体层级、间距、边框、功能区结构、控件状态和语义颜色必须保持一致，禁止形成芯片专属视觉体系。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

## [R100.800] Semantic Functional Rendering

### [R100.800.010] Controls Must Use Semantic Functional Colors

Level: MUST
When: 渲染按钮、状态标签、进度、开关、风险操作或其他具有明确功能含义的控件时
Rule: 控件颜色必须按功能、状态和风险语义统一渲染；品牌主操作、正常/连接/成功、警告、危险和禁用状态必须具有稳定且可区分的视觉语义，禁止无规则分配颜色或把 ET 品牌红同时当作所有状态与风险含义。颜色不得成为唯一的状态或风险信息载体。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

## [R100.900] Functional Surface Visibility

### [R100.900.010] Primary Functional Controls Must Be Directly Visible

Level: MUST
When: 设计或修改正式支持的桌面功能工作台、参数区、操作区和状态区时
Rule: 当前功能页的主要参数、状态和操作控件必须在功能区直接呈现；禁止把日常主功能隐藏到折叠区、抽屉、二级展开或额外导航后才能访问。危险操作所需的确认对话框不属于功能隐藏。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html

### [R100.900.020] Desktop Function Workspace Must Not Require Horizontal Scrolling

Level: MUST_NOT
When: 设计或修改正式支持的桌面窗口尺寸下的功能工作台布局时
Rule: 禁止把横向滚动条、左右滑动或横向 Carousel 作为访问功能控件的正式交互方式；功能区必须通过 Grid、Column、Section 等布局适配可用宽度，内容超出垂直空间时允许纵向滚动。
Refs: A030, html/et_tool_ui_design_prototype_v3_et_red_white_polished.html
