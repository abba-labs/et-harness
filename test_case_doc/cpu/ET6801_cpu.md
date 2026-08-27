# ET6801 CPU NMI Adaptation

## 第一章 Source Coverage与硬件事实

| Source | 状态 | 可证明事实 |
|---|---|---|
| `test_case_doc/ET6801.svd` | FOUND / PRIMARY | CPU0/CPU1包含`NMI_SEL.NMI_SRC_RPT`、`NMI_SRC_MASKED_RPT`、`M7_NMI_MASK`和`STATUS_RPT.M7_NMI_RPT`。 |
| `firmware/chips/et6801/sdk/CMSIS/Device/Include/et6801.h` | FOUND / PRIMARY | 生成CMSIS符号确认四位Source/Mask字段和CPU NMI状态位。 |
| `firmware/chips/et6801/sdk/ET6x_Driver` | FOUND | 隔离Test Driver Extension提供Mask配置、快照和支持Mask读取。 |
| `firmware/services/src/et_cpu_service.c` | FOUND | CPU Owner发布固定Wire快照和NMI向量事件计数。 |

关键硬件事实：

- ET6801有CPU0、CPU1两个逻辑CPU寄存器实例；当前测试固件镜像只允许一个NMI向量Owner。
- `NMI_SEL.M7_NMI_MASK`为4 bit；SVD说明必须先写`sw_access_key=0x7879a8a9`才能更新。
- `NMI_SRC_RPT`与`NMI_SRC_MASKED_RPT`分别表示屏蔽前后四路Source状态。
- SVD没有命名四个Source位分别来自哪个外设，因此WDG到具体Source bit仍是Mapping Gap。
- 当前FPGA HIL中，WDG自然超时后NMI Level Source会重复进入NMI向量；只累加计数会饿死控制UART线程。CPU Owner必须在首次交付后屏蔽全部已发布Source，Peer Service仍负责清自己的外设Source。

## 第二章 Source Item Trace

| Source Item | Public映射 | 处置 |
|---|---|---|
| M7_NMI_MASK配置与读回 | CPU_F_001 / CPU_P1_001 | MAPPED |
| 屏蔽前/后Source与M7 NMI状态 | CPU_F_002 / CPU_P1_001 | MAPPED |
| NMI向量真实交付与Level Source有界处理 | CPU_F_003 / CPU_P1_002 | MAPPED |
| 四路Source的外设身份 | `cpu_nmi_source_identity_gap` | UNKNOWN；等待RTL/LRS或可重复HIL冻结 |

## 第三章 公共Observation到ET6801字段映射

| 公共Endpoint | ET6801字段 |
|---|---|
| `NMI_ROUTE.SOURCE_RAW` | `CPUx.NMI_SEL.NMI_SRC_RPT` |
| `NMI_ROUTE.SOURCE_MASKED` | `CPUx.NMI_SEL.NMI_SRC_MASKED_RPT` |
| `NMI_ROUTE.MASK` | `CPUx.NMI_SEL.M7_NMI_MASK` |
| `NMI_ROUTE.STATUS` | `CPUx.STATUS_RPT.M7_NMI_RPT` |
| `NMI_DELIVERY.EVENT_COUNT` | 测试固件`NMI_Handler`饱和事件计数 |

## 第四章 Gap / Risk Registry

| Gap ID | Current fact | Release condition |
|---|---|---|
| cpu_nmi_source_identity_gap | SVD只给出匿名四位Source状态，无法把具体bit静态绑定到WDG实例或处理域。 | RTL/LRS或逐Source可重复HIL给出权威映射。 |
| cpu_nmi_level_delivery_gap | CLOSED / FPGA_HIL_PASS：CPU Owner首次NMI后自动全屏蔽；WDG Peer实测event_count 0->1、Mask=0xF且协议线程继续响应。 | 补充Silicon HIL，不回退当前FPGA证据。 |

## 第五章 Chip -> Public Feature Mapping

| Public Feature | Hardware | 参数/差异 | Platform | Public Case |
|---|---|---|---|---|
| CPU_F_001 | SUPPORTED | 4 bit `M7_NMI_MASK`，写入需要CPU访问Key。 | ADAPTED | CPU_P1_001 |
| CPU_F_002 | SUPPORTED | Raw、Masked和M7 NMI Status分别存在。 | ADAPTED | CPU_P1_001 |
| CPU_F_003 | SUPPORTED | WDG Peer FPGA HIL已证明首次NMI进入后自动全屏蔽且协议线程继续响应。 | ADAPTED | CPU_P1_002 |

## 第六章 Chip -> Public Case Adaptation

| Public Case | Adaptation | Reason / Gap |
|---|---|---|
| CPU_P1_001 | IMPLEMENTATION_GAP | Driver/Wrap/Service接口已存在，独立Formal Case尚未实现。 |
| CPU_P1_002 | IMPLEMENTATION_GAP | 由真实Peer IP产生Level NMI；CPU Owner有界处理修复后再实现独立Case。 |

## 第七章 双核部署验证

更新时间：2026-08-27 12:03 CST

| 目标 | Core0镜像 | Core1镜像 | 部署方式 | 当前状态 |
|---|---|---|---|---|
| ET6801 FPGA | ITCM `0x00000000` | ITCM `0x00000000` | J-Link AHB-AP[1]/AHB-AP[2]临时加载 | 统一脚本已连续执行2轮；每轮Core1 Ready、Core Index=2、Heartbeat=5且`failure_count=0`。 |
| ET6801 Silicon | PFLASH0 `0x08000000` | PFLASH1 `0x08080000` | 双核PFLASH构建与烧录清单 | Core0/Core1目标均已构建；Core1释放、双探针身份、PFLASH1算法和Option Word完成首板确认前，Profile禁止真实烧录。 |

双核部署使用同一个公共脚本，FPGA和Silicon只替换芯片清单及烧录步骤。Silicon构建通过不能替代Silicon HIL结论。
