# 新芯片接入模板

一个新芯片目录包含：

```text
firmware/chips/<chip>/
├─ config/et_chip_wrap_config.h
├─ sdk/CMSIS/
├─ sdk/<driver-family>/
├─ linker/
├─ keil/
└─ project.yaml
```

每块目标板另提供`firmware/boards/<board>/et_board_config.h`。项目清单用于生成
`firmware/build/<chip>/`中的Keil工程。

本README只给出接入文件清单，不重新定义公共层、Wrap、Chip Config、Driver Extension或
芯片能力规则：

- [R100 公共IP与芯片适配](../../../report/design/rules/R100_public_ip_semantics_and_chip_adaptation.md)
- [R310 Firmware Wrap与Chip Config](../../../report/design/rules/R310_firmware_wrap.md)
- [R410 Capability v2](../../../report/design/rules/R410_capability_v2.md)
