# [A010] Product Capability Map

Role: ET-TOOL 的 canonical 产品能力主地图。以 Chip × Route × Operation 表达唯一能力实例，作为绝大多数开发需求的首要落点。
Boundary: 不复制 CLI、GUI、实现栈、Profile、测试和发布细节；这些由 A020–A060 作为投影视角或下钻地图引用本图。
Resources: source/profiles/chips/, source/apps/cli/chips/, source/apps/gui/chips/
Relations: A020, A030, A040, A050, A060

## [A010.010] ET3101

Role: ET3101 当前能力实例入口。
Resources: source/apps/cli/chips/et3101/, source/apps/gui/chips/et3101/, source/profiles/chips/et3101/
Relations: A020, A030, A040, A050, A060

### [A010.010.010] ET3101 UART

Role: ET3101 UART ROM 产品能力实例。
Relations: A020.020.010, A030.040.010, A040.010.010, A050.020.100.010, A060.010.010.010, A060.030.030.100.010, A060.040.010.100.010, A060.050.010.010

#### [A010.010.010.010] ET3101 UART Discovery And Readonly

Role: ET3101 UART identify/version/commands、readonly identity 与只读安全信息操作族。
Relations: A050.020.100.010, A060.010.010.010, A060.030.030.100.010

#### [A010.010.010.020] ET3101 UART Memory

Role: ET3101 UART PFlash/read/write 等内存操作族。
Relations: A050.020.100.010, A060.010.010.010, A060.030.030.100.010

#### [A010.010.010.030] ET3101 UART Program Erase Verify

Role: ET3101 UART program、erase、verify 操作族。
Relations: A050.020.100.010, A060.010.010.010, A060.020.010, A060.030.030.100.010, A060.040.010.100.010

#### [A010.010.010.040] ET3101 UART Security Option Protection

Role: ET3101 UART security、key、OTP、Option、WRP 等受保护状态操作族。
Relations: A050.020.100.010, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.010

#### [A010.010.010.050] ET3101 UART Control And Speed

Role: ET3101 UART Go、Speed 与相关控制操作族。
Relations: A050.020.100.010, A060.010.010.010, A060.030.030.100.010

### [A010.010.020] ET3101 CAN

Role: ET3101 Classic CAN ROM 产品能力实例。
Relations: A020.030.010, A030.050.010, A040.020.010, A050.020.100.020, A060.010.010.010, A060.030.030.100.020, A060.040.010.100.020, A060.050.010.010

#### [A010.010.020.010] ET3101 CAN Discovery And Readonly

Role: ET3101 CAN identify/version/commands 与只读信息操作族。
Relations: A050.020.100.020, A060.010.010.010, A060.030.030.100.020

#### [A010.010.020.020] ET3101 CAN Memory

Role: ET3101 CAN PFlash/read/write 等内存操作族。
Relations: A050.020.100.020, A060.010.010.010, A060.030.030.100.020

#### [A010.010.020.030] ET3101 CAN Program Erase Verify

Role: ET3101 CAN program、erase、verify 操作族。
Relations: A050.020.100.020, A060.010.010.010, A060.020.010, A060.030.030.100.020, A060.040.010.100.020

#### [A010.010.020.040] ET3101 CAN Security Option Protection

Role: ET3101 CAN security、key、OTP、Option、WRP 等受保护状态操作族。
Relations: A050.020.100.020, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.020

#### [A010.010.020.050] ET3101 CAN Control And Speed

Role: ET3101 CAN Go、Speed 与相关控制操作族。
Relations: A050.020.100.020, A060.010.010.010, A060.030.030.100.020

### [A010.010.030] ET3101 CANFD

Role: ET3101 CAN FD ROM 产品能力实例；逐 capability 硬件证据强度仍需由 A060 校验。
Relations: A020.040.010, A030.060.010, A040.030.010, A050.020.100.030, A060.010.010.010, A060.030.030.100.030, A060.040.010.100.030, A060.050.010.010

#### [A010.010.030.010] ET3101 CANFD Discovery And Readonly

Role: ET3101 CANFD identify/readonly 操作族。
Relations: A050.020.100.030, A060.010.010.010, A060.030.030.100.030

#### [A010.010.030.020] ET3101 CANFD Memory

Role: ET3101 CANFD memory 操作族；具体支持状态按 Profile capability 判断。
Relations: A050.020.100.030, A060.010.010.010, A060.030.030.100.030

#### [A010.010.030.030] ET3101 CANFD Program Erase Verify

Role: ET3101 CANFD program、erase、verify 操作族；硬件闭合程度按证据查询。
Relations: A050.020.100.030, A060.010.010.010, A060.020.010, A060.030.030.100.030, A060.040.010.100.030

#### [A010.010.030.040] ET3101 CANFD Security Option Protection

Role: ET3101 CANFD security/option/protection 操作族；具体支持状态按 Profile 与 evidence 判断。
Relations: A050.020.100.030, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.030

#### [A010.010.030.050] ET3101 CANFD Control And Speed

Role: ET3101 CANFD control/speed 操作族；具体支持状态按 Profile 判断。
Relations: A050.020.100.030, A060.010.010.010, A060.030.030.100.030

### [A010.010.040] ET3101 CMSIS-DAP

Role: ET3101 CMSIS-DAP SWD 产品能力实例。
Relations: A020.050.010, A030.070.010, A040.040.010, A050.030.020.010.010, A050.030.030.010, A050.030.040.010, A060.010.010.010, A060.030.030.100.040, A060.050.010.010

#### [A010.010.040.010] ET3101 DAP Connect And Identity

Role: ET3101 DAP connect-halt、identity 与 readonly smoke 操作族。
Relations: A050.030.020.010.010, A050.030.030.010, A060.010.010.010, A060.030.030.100.040

#### [A010.010.040.020] ET3101 DAP Memory And Registers

Role: ET3101 DAP memory/register read 操作族。
Relations: A050.030.020.010.010, A050.030.030.010, A050.030.040.010, A060.010.010.010, A060.030.030.100.040

#### [A010.010.040.030] ET3101 DAP PFlash Program Erase

Role: ET3101 DAP PFlash program/erase 产品操作族。
Relations: A050.030.020.010.010, A050.030.030.010, A050.030.040.010, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.040

#### [A010.010.040.040] ET3101 DAP Option And Protection

Role: ET3101 DAP Option、WRP 等配置与保护操作族。
Relations: A050.030.020.010.010, A050.030.030.010, A050.030.040.010, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.040

#### [A010.010.040.050] ET3101 DAP Control

Role: ET3101 DAP Go/Jump/Reset/debug-control 操作族。
Relations: A050.030.020.010.010, A050.030.030.010, A060.010.010.010, A060.030.030.100.040

### [A010.010.050] ET3101 J-Link

Role: ET3101 J-Link SWD 产品能力实例。
Relations: A020.060.010, A030.080.010, A040.050.010, A050.030.020.010.020, A050.030.030.020, A050.030.040.010, A050.030.050.020, A060.010.010.010, A060.030.030.100.050, A060.050.010.010

#### [A010.010.050.010] ET3101 J-Link Connect And Identity

Role: ET3101 J-Link connect-halt、identity 与 readonly smoke 操作族。
Relations: A050.030.020.010.020, A050.030.030.020, A060.010.010.010, A060.030.030.100.050

#### [A010.010.050.020] ET3101 J-Link Memory And Registers

Role: ET3101 J-Link memory/register read 操作族。
Relations: A050.030.020.010.020, A050.030.030.020, A050.030.040.010, A060.010.010.010, A060.030.030.100.050

#### [A010.010.050.030] ET3101 J-Link PFlash Program Erase

Role: ET3101 J-Link PFlash program/erase 产品操作族。
Relations: A050.030.020.010.020, A050.030.030.020, A050.030.040.010, A050.030.050.020, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.050

#### [A010.010.050.040] ET3101 J-Link Option And Protection

Role: ET3101 J-Link Option、WRP 等配置与保护操作族。
Relations: A050.030.020.010.020, A050.030.030.020, A050.030.040.010, A060.010.010.010, A060.020.010, A060.020.020, A060.030.030.100.050

#### [A010.010.050.050] ET3101 J-Link Control

Role: ET3101 J-Link Go/Jump/Reset/debug-control 操作族。
Relations: A050.030.020.010.020, A050.030.030.020, A060.010.010.010, A060.030.030.100.050

## [A010.020] ET6002

Role: ET6002 当前能力实例入口；包含已产品化路线以及明确 unsupported/deferred 的当前边界。
Resources: source/apps/cli/chips/et6002/, source/apps/gui/chips/et6002/, source/profiles/chips/et6002/
Relations: A020, A030, A040, A050, A060

### [A010.020.010] ET6002 UART

Role: ET6002 UART ROM 主产品能力实例。
Relations: A020.020.020, A030.040.020, A040.010.020, A050.020.200.010, A060.010.010.020, A060.030.030.200.010, A060.040.010.200.010, A060.050.010.020

#### [A010.020.010.010] ET6002 UART Discovery And Readonly

Role: ET6002 UART identify/readonly 操作族。
Relations: A050.020.200.010, A060.010.010.020, A060.030.030.200.010

#### [A010.020.010.020] ET6002 UART Memory

Role: ET6002 UART memory 操作族。
Relations: A050.020.200.010, A060.010.010.020, A060.030.030.200.010

#### [A010.020.010.030] ET6002 UART Program Erase Verify

Role: ET6002 UART program、erase、verify 操作族。
Relations: A050.020.200.010, A060.010.010.020, A060.020.010, A060.030.030.200.010, A060.040.010.200.010

#### [A010.020.010.040] ET6002 UART Security Option Protection

Role: ET6002 UART security、key、OTP、Option、WRP 操作族；部分行为闭合仍需按证据确认。
Relations: A050.020.200.010, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.010

#### [A010.020.010.050] ET6002 UART Control And Speed

Role: ET6002 UART Go、Speed 与相关控制操作族。
Relations: A050.020.200.010, A060.010.010.020, A060.030.030.200.010

### [A010.020.020] ET6002 CAN

Role: ET6002 Classic CAN ROM 产品能力实例。
Relations: A020.030.020, A030.050.020, A040.020.020, A050.020.200.020, A060.010.010.020, A060.030.030.200.020, A060.040.010.200.020, A060.050.010.020

#### [A010.020.020.010] ET6002 CAN Discovery And Readonly

Role: ET6002 CAN identify/readonly 操作族。
Relations: A050.020.200.020, A060.010.010.020, A060.030.030.200.020

#### [A010.020.020.020] ET6002 CAN Memory

Role: ET6002 CAN memory 操作族；raw write 等具体产品状态按 capability 查询。
Relations: A050.020.200.020, A060.010.010.020, A060.030.030.200.020

#### [A010.020.020.030] ET6002 CAN Program Erase Verify

Role: ET6002 CAN program/erase/verify 操作族；standalone sector erase 等边界按 capability/evidence 查询。
Relations: A050.020.200.020, A060.010.010.020, A060.020.010, A060.030.030.200.020, A060.040.010.200.020

#### [A010.020.020.040] ET6002 CAN Security Option Protection

Role: ET6002 CAN security、Option、WRP 等操作族。
Relations: A050.020.200.020, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.020

#### [A010.020.020.050] ET6002 CAN Control And Speed

Role: ET6002 CAN Go、Speed 与相关控制操作族。
Relations: A050.020.200.020, A060.010.010.020, A060.030.030.200.020

### [A010.020.030] ET6002 CANFD

Role: ET6002 CANFD 当前明确 UNSUPPORTED / fail-closed 的能力边界；用于“新增 ET6002 CANFD”类需求定位现状，而不是表示已有产品能力。
Relations: A020.040.020, A030.060.020, A040.030.020, A060.010.010.020, A060.030.030.200.030, A060.050.010.020

#### [A010.020.030.010] ET6002 CANFD Unsupported Boundary

Role: 记录 ET6002 CANFD 当前没有正式产品升级路线，Classic CAN 能力与证据不得继承到 CANFD。
Relations: A020.040.020, A030.060.020, A040.030.020, A060.010.010.020, A060.030.030.200.030, A060.050.010.020

### [A010.020.040] ET6002 CMSIS-DAP

Role: ET6002 CMSIS-DAP concrete path 已存在但当前 Profile 产品状态以 DEFERRED 为主的能力实例。
Relations: A020.050.020, A030.070.020, A040.040.020, A050.030.020.020.010, A050.030.030.010, A050.030.040.020, A060.010.010.020, A060.030.030.200.040, A060.040.010.200.040, A060.050.010.020

#### [A010.020.040.010] ET6002 DAP Connect And Identity

Role: ET6002 DAP connect/identity concrete path；正式放行仍以 Profile/admission 为准。
Relations: A050.030.020.020.010, A050.030.030.010, A060.010.010.020, A060.030.030.200.040, A060.040.010.200.040

#### [A010.020.040.020] ET6002 DAP Read And Program Candidate

Role: ET6002 DAP read/PFlash program candidate execution path；当前不能等同产品支持。
Relations: A050.030.020.020.010, A050.030.030.010, A050.030.040.020, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.040, A060.040.010.200.040

#### [A010.020.040.030] ET6002 DAP Option Protection Candidate

Role: ET6002 DAP Option/protection candidate path；产品状态按 Profile 查询。
Relations: A050.030.020.020.010, A050.030.030.010, A050.030.040.020, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.040, A060.040.010.200.040

#### [A010.020.040.040] ET6002 DAP Control Candidate

Role: ET6002 DAP control candidate path；产品状态按 Profile 查询。
Relations: A050.030.020.020.010, A050.030.030.010, A060.010.010.020, A060.030.030.200.040, A060.040.010.200.040

### [A010.020.050] ET6002 J-Link

Role: ET6002 J-Link concrete path 已存在但当前 Profile 产品状态以 DEFERRED 为主的能力实例。
Relations: A020.060.020, A030.080.020, A040.050.020, A050.030.020.020.020, A050.030.030.020, A050.030.040.020, A050.030.050.020, A060.010.010.020, A060.030.030.200.050, A060.040.010.200.050, A060.050.010.020

#### [A010.020.050.010] ET6002 J-Link Connect And Identity

Role: ET6002 J-Link connect/identity concrete path；正式放行仍以 Profile/admission 为准。
Relations: A050.030.020.020.020, A050.030.030.020, A060.010.010.020, A060.030.030.200.050, A060.040.010.200.050

#### [A010.020.050.020] ET6002 J-Link Read And Program Candidate

Role: ET6002 J-Link read/PFlash program candidate execution path；当前不能等同产品支持。
Relations: A050.030.020.020.020, A050.030.030.020, A050.030.040.020, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.050, A060.040.010.200.050

#### [A010.020.050.030] ET6002 J-Link Option Protection Candidate

Role: ET6002 J-Link Option/protection candidate path；产品状态按 Profile 查询。
Relations: A050.030.020.020.020, A050.030.030.020, A050.030.040.020, A060.010.010.020, A060.020.010, A060.020.020, A060.030.030.200.050, A060.040.010.200.050

#### [A010.020.050.040] ET6002 J-Link Control Candidate

Role: ET6002 J-Link control candidate path；产品状态按 Profile 查询。
Relations: A050.030.020.020.020, A050.030.030.020, A060.010.010.020, A060.030.030.200.050, A060.040.010.200.050

## [A010.030] ET6003

Role: ET6003 当前能力实例入口；ROM 路线按 capability 分级，Probe 路线当前以 deferred/mixed 状态为主。
Resources: source/apps/cli/chips/et6003/, source/apps/gui/chips/et6003/, source/profiles/chips/et6003/
Relations: A020, A030, A040, A050, A060

### [A010.030.010] ET6003 UART

Role: ET6003 UART ROM 主产品能力实例。
Relations: A020.020.030, A030.040.030, A040.010.030, A050.020.300.010, A060.010.010.030, A060.030.030.300.010, A060.040.010.300.010, A060.050.010.030

#### [A010.030.010.010] ET6003 UART Discovery And Readonly

Role: ET6003 UART identify/readonly 操作族。
Relations: A050.020.300.010, A060.010.010.030, A060.030.030.300.010

#### [A010.030.010.020] ET6003 UART Memory

Role: ET6003 UART memory 操作族。
Relations: A050.020.300.010, A060.010.010.030, A060.030.030.300.010

#### [A010.030.010.030] ET6003 UART Program Erase Verify

Role: ET6003 UART program/erase/verify 操作族。
Relations: A050.020.300.010, A060.010.010.030, A060.020.010, A060.030.030.300.010, A060.040.010.300.010

#### [A010.030.010.040] ET6003 UART Security Option Protection

Role: ET6003 UART security、Option、protection 操作族。
Relations: A050.020.300.010, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.010

#### [A010.030.010.050] ET6003 UART Control And Speed

Role: ET6003 UART Go、Speed 与相关控制操作族。
Relations: A050.020.300.010, A060.010.010.030, A060.030.030.300.010

### [A010.030.020] ET6003 CAN

Role: ET6003 Classic CAN ROM 能力实例；逐 capability 支持状态是权威边界。
Relations: A020.030.030, A030.050.030, A040.020.030, A050.020.300.020, A060.010.010.030, A060.030.030.300.020, A060.040.010.300.020, A060.050.010.030

#### [A010.030.020.010] ET6003 CAN Discovery And Readonly

Role: ET6003 CAN identify/readonly 操作族。
Relations: A050.020.300.020, A060.010.010.030, A060.030.030.300.020

#### [A010.030.020.020] ET6003 CAN Memory

Role: ET6003 CAN memory 操作族；具体支持按 capability 查询。
Relations: A050.020.300.020, A060.010.010.030, A060.030.030.300.020

#### [A010.030.020.030] ET6003 CAN Program Erase Verify

Role: ET6003 CAN program/erase/verify 操作族；具体支持按 capability/evidence 查询。
Relations: A050.020.300.020, A060.010.010.030, A060.020.010, A060.030.030.300.020, A060.040.010.300.020

#### [A010.030.020.040] ET6003 CAN Security Option Protection

Role: ET6003 CAN security/option/protection 操作族；具体支持按 capability 查询。
Relations: A050.020.300.020, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.020

#### [A010.030.020.050] ET6003 CAN Control And Speed

Role: ET6003 CAN Go/Speed 与相关控制操作族。
Relations: A050.020.300.020, A060.010.010.030, A060.030.030.300.020

### [A010.030.030] ET6003 CANFD

Role: ET6003 CAN FD ROM 已实现但产品支持与硬件证据按 capability 呈 MIXED 的能力实例。
Relations: A020.040.030, A030.060.030, A040.030.030, A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.030.030.300.030, A060.040.010.300.030, A060.050.010.030

#### [A010.030.030.010] ET6003 CANFD Discovery And Readonly

Role: ET6003 CANFD identify/readonly 操作族；硬件证据为部分闭合。
Relations: A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.030.030.300.030

#### [A010.030.030.020] ET6003 CANFD Memory

Role: ET6003 CANFD memory 操作族；逐 capability 判断产品支持。
Relations: A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.030.030.300.030

#### [A010.030.030.030] ET6003 CANFD Program Erase Verify

Role: ET6003 CANFD program/erase/verify 操作族；产品与硬件状态按 capability/evidence 判断。
Relations: A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.020.010, A060.030.030.300.030, A060.040.010.300.030

#### [A010.030.030.040] ET6003 CANFD Security Option Protection

Role: ET6003 CANFD security/option/protection 操作族；当前为 route-specific mixed 状态。
Relations: A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.030

#### [A010.030.030.050] ET6003 CANFD Control And Speed

Role: ET6003 CANFD control/speed 操作族；逐 capability 与硬件证据判断。
Relations: A050.020.300.020, A050.020.300.030, A060.010.010.030, A060.030.030.300.030

### [A010.030.040] ET6003 CMSIS-DAP

Role: ET6003 CMSIS-DAP concrete execution path 已存在但当前 Profile 产品状态以 DEFERRED/MIXED 为主的能力实例。
Relations: A020.050.030, A030.070.030, A040.040.030, A050.030.020.030.010, A050.030.030.010, A050.030.040.030, A060.010.010.030, A060.030.030.300.040, A060.040.010.300.040, A060.050.010.030

#### [A010.030.040.010] ET6003 DAP Connect And Identity

Role: ET6003 DAP connect/identity concrete path；产品准入按 Profile 判断。
Relations: A050.030.020.030.010, A050.030.030.010, A060.010.010.030, A060.030.030.300.040, A060.040.010.300.040

#### [A010.030.040.020] ET6003 DAP Read And Program Candidate

Role: ET6003 DAP memory/PFlash program concrete path；当前不能由实现存在推导为产品支持。
Relations: A050.030.020.030.010, A050.030.030.010, A050.030.040.030, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.040, A060.040.010.300.040

#### [A010.030.040.030] ET6003 DAP Option Protection Candidate

Role: ET6003 DAP Option/protection concrete path；产品状态按 Profile/evidence 判断。
Relations: A050.030.020.030.010, A050.030.030.010, A050.030.040.030, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.040, A060.040.010.300.040

#### [A010.030.040.040] ET6003 DAP Control Candidate

Role: ET6003 DAP reset/run/debug-control concrete path；产品状态按 Profile 判断。
Relations: A050.030.020.030.010, A050.030.030.010, A060.010.010.030, A060.030.030.300.040, A060.040.010.300.040

### [A010.030.050] ET6003 J-Link

Role: ET6003 J-Link concrete execution path 已存在但当前 Profile 产品状态以 DEFERRED/MIXED 为主的能力实例；本节点是“修改 6003 J-Link”类需求的 canonical 首落点。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/profiles/chips/et6003/capabilities.yaml, source/profiles/chips/et6003/connections.yaml
Relations: A020.060.030, A030.080.030, A040.050.030, A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A050.030.050.020, A060.010.010.030, A060.030.030.300.050, A060.040.010.300.050, A060.050.010.030

#### [A010.030.050.010] ET6003 J-Link Connect And Identity

Role: ET6003 J-Link connect/identity concrete path；产品准入按 Profile 判断。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/workflow/et6003/et6003_debug_probe_readonly_hw_smoke_workflow.h, source/profiles/chips/et6003/capabilities.yaml
Relations: A050.030.020.030.020, A050.030.030.020, A060.010.010.030, A060.030.030.300.050, A060.040.010.300.050

#### [A010.030.050.020] ET6003 J-Link Read And Registers Candidate

Role: ET6003 J-Link memory/register read concrete path；产品状态按 Profile/evidence 判断。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_read_mem_hw_executor.h, source/workflow/et6003/et6003_debug_probe_read_mem_hw_workflow.h, source/profiles/chips/et6003/capabilities.yaml
Relations: A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A060.010.010.030, A060.030.030.300.050, A060.040.010.300.050

#### [A010.030.050.030] ET6003 J-Link PFlash Program Candidate

Role: ET6003 J-Link PFlash program concrete executor/algorithm path；当前不能由实现存在推导为正式产品支持。
Resources: source/application/et6003/et6003_debug_probe_command.h, source/workflow/et6003/et6003_debug_probe_pflash_hw_workflow.h, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_hw_executor.h, source/profiles/chips/et6003/capabilities.yaml
Relations: A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A050.030.050.020, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.050, A060.040.010.300.050

#### [A010.030.050.040] ET6003 J-Link Option Protection Candidate

Role: ET6003 J-Link Option/protection concrete path；产品状态按 Profile/evidence 判断。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_option_go_hw_executor.h, source/workflow/et6003/et6003_debug_probe_option_go_hw_workflow.h, source/probe/algorithms/chips/et6003/et6003_debug_probe_option_user_algorithm.h, source/profiles/chips/et6003/capabilities.yaml
Relations: A050.030.020.030.020, A050.030.030.020, A050.030.040.030, A060.010.010.030, A060.020.010, A060.020.020, A060.030.030.300.050, A060.040.010.300.050

#### [A010.030.050.050] ET6003 J-Link Control Candidate

Role: ET6003 J-Link reset/run/debug-control concrete path；产品状态按 Profile 判断。
Resources: source/apps/cli/chips/et6003/et6003_debug_probe_cli_module.cpp, source/apps/cli/chips/et6003/et6003_debug_probe_jlink_option_go_hw_executor.h, source/workflow/et6003/et6003_debug_probe_option_go_hw_workflow.h, source/profiles/chips/et6003/capabilities.yaml
Relations: A050.030.020.030.020, A050.030.030.020, A060.010.010.030, A060.030.030.300.050, A060.040.010.300.050
