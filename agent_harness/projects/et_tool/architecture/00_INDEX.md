---
interface: project-resource-index-v0.1
resource: architecture
standard: architecture-v0.1
files:
  - id: A010
    file: 010_chip_map.md
    title: Product Capability Map
    summary: Canonical Chip × Route × Operation 能力主地图，是 ET-TOOL 开发需求的首要落点。
    aliases: [capability, product capability, chip, 芯片, 能力, ET3101, ET6002, ET6003, program, erase, verify, security, option]
  - id: A020
    file: 020_cli_map.md
    title: CLI Projection Map
    summary: 从 et-cli 视角投影 canonical 能力实例，导航 chip-local CLI 入口与装配边界。
    aliases: [cli, command line, 命令行, 执行入口, composition]
  - id: A030
    file: 030_gui_map.md
    title: GUI Projection Map
    summary: 从 GUI 视角投影 canonical 能力实例，导航 shell、workbench、route/page/action 与 CLI bridge。
    aliases: [gui, ui, 界面, 页面, workbench, qprocess]
  - id: A040
    file: 040_upgrade_route_map.md
    title: Route Projection Map
    summary: 从 UART、CAN、CANFD、CMSIS-DAP、J-Link 路线反向投影各芯片 canonical 能力实例。
    aliases: [upgrade, route, 升级, 串口, uart, can, canfd, fdcan, dap, cmsis-dap, jlink, j-link]
  - id: A050
    file: 050_shared_system_map.md
    title: Implementation Map
    summary: 从产品能力下钻到 Domain、Application、Workflow、Backend、Protocol、Transport、Probe、Platform 与装配基础设施。
    aliases: [implementation, 实现, shared, domain, application, workflow, backend, protocol, transport, probe, platform, executor, algorithm]
  - id: A060
    file: 060_product_control_validation_map.md
    title: Product Control And Validation Map
    summary: 导航 Profile 支持、运行时准入、安全门、测试、自动化证据、release visibility 与交付闭环。
    aliases: [profile, admission, gate, test, validation, automation, evidence, release, delivery, 验证, 证据, 发布, 准入]
---

# ET-TOOL Architecture Index

> 状态：Architecture v0.1 capability-centered draft / routable / relation-integrity ready

ET-TOOL Architecture 以 A010 canonical Product Capability Map 为中心。A020 CLI、A030 GUI、A040 Route 是对同一能力实例的不同投影视角；A050 负责下钻真实实现层；A060 负责产品状态、验证、证据与发布闭环。

目标不是复制代码目录，而是把用户需求从 Chip × Route × Operation 收敛到最小相关 Architecture Nodes 和真实 Resources，再由 Rule / Knowledge / Gate 继续补齐开发上下文。
