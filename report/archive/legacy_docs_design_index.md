# docs/design

总体设计文档目录。

芯片能力专项设计：

[Capability v2 契约](../design/capability_v2_contract.md)

该文档冻结语义Capability、SVD证据、未分类审计产物和PC端自然查询接口。

当前架构基线：

[ET 全系列芯片 IP 自动化测试平台总体设计](../design/et_ip_automated_test_platform_architecture.md)

该文档基于 2026-07-21～2026-07-22 的 XC7Z045 实板验证、JTAG transport
基准和 ET6003/ET3101/ET6801 IP/SDK 演进分析，定义 PC、XC7Z045、
XC7VX980T/真实芯片之间的正式分工、数据链路、协议以及四侧软件/RTL 架构。

PC 端专项设计：

[ET IP 自动化测试平台 PC 端分层架构设计](../design/pc_layered_architecture.md)

该文档落实 Test Case、IP Driver、仪器库、Device Client、Communication、
Scheduling、Config 和 Result Pipeline 的职责与依赖关系，并定义自动数据分析、
自动报表和 Web 实时可视化的轻量扩展接口。PC 端实现以该专项设计为准。

固件 Wrap 专项设计：

[ET 自动化测试固件 Wrap 层设计规范](../design/wrap_layer_design.md)

该文档冻结 Wrap 的目录、命名、模块粒度、参数、返回值、原子接口、Resource Wrap
以及 Service/PC Case 边界。Wrap 实现与评审以该专项设计为准。

固件中断子系统专项设计：

[ET自动化测试固件中断子系统设计](../design/interrupt_subsystem_design.md)

该文档定义PC语义事件、IP Service静态回调、IP Wrap物理路由、IRQ Manager绑定分发、
IRQ Wrap/NVIC、启动文件适配，以及独立、组合、缺失和共享向量的统一生命周期。

芯片能力生成专项设计：

[SVD 到 IP Capability YAML 的确定性生成设计](../design/svd_capability_generation.md)

该文档定义通用 SVD 规范化、跨芯片 IP 规则、Capability 映射、规范 YAML 输出、
失败门禁和审核接口。正式能力 YAML 必须由该流程生成，不得按芯片手写。

历史通用方案：

[MCU HIL/SIL 通用测试平台方案](mcu_hil_sil_unified_test_platform.md)

历史方案用于保留 pytest/Target API/Renode/HIL 的通用讨论；若与当前架构基线冲突，
以 `et_ip_automated_test_platform_architecture.md` 和当前项目规则为准。
