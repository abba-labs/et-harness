# ET6801 AES Chip Adaptation

> 本文件只保存 ET6801 的硬件、寄存器/Field、DMA/IRQ 与平台适配事实；公共 Feature/Case/Report 以 `aes.md` 为唯一契约。
> 这里可以出现 ET6801 的实际寄存器名称，但公共 `aes.md` 和公共 Case 代码不得硬编码芯片地址。

## 第一章 当前硬件与 Capability 基线

当前机器 Capability 来源：

```text
pc/et_test_platform/profiles/chip_capabilities/et6801/ip/aes.yaml
source: ET6801.svd
generator_version: 8
instance: aes0
```

当前 Capability 已包含 AES semantic mapping，不再是早期“只有 instance/base/IRQ、无 semantic mapping”的状态。已生成的稳定能力包括：CPU register path、CTR、Encrypt/Decrypt、DMA/FIFO、IRQ、IV、Key、Module Enable、Padding、Status；`block_size_bytes=16`、`data_length_bits=36`，并声明 ECB/CBC/CTR、128/256-bit、LITTLE/BIG、FIFO/REGISTER DMA 与 7 个 IRQ Source。

`AES_P0_001` 因此采用两级门禁：先检查静态 semantic mapping；只有映射存在时才通过 AES Driver 执行只读 `CAPABILITIES_GET`，该查询不执行 Enable/Configure/Process。

## 第二章 ET6801 寄存器 / Field 映射

### 2.1 公共硬件 Observation 到 ET6801 实际名称

| 公共稳定语义 | ET6801 实际寄存器 / Field | 用途 |
|---|---|---|
| `STATUS.BUSY` | `RPT_AES_WORK.BUSY` | 运算忙状态；当前 Case 只证明完成后 BUSY=0 |
| `STATUS.DIN_REQ` | `RPT_AES_STS.DIN_FLG` | 非DMA输入请求状态，W1C |
| `STATUS.DOUT_REQ` | `RPT_AES_STS.DOUT_FLG` | 非DMA输出请求状态，W1C |
| `STATUS.FINISH` | `RPT_AES_STS.FINISH` | 运算完成状态，W1C |
| `RESULT_DOUT[0..3]` | `RESULT_DOUT0~RESULT_DOUT3` | CPU/IRQ/REGISTER DMA 128-bit 输出 |
| `IV[0..3]` | `WORK_IV0~WORK_IV3` | 128-bit IV 配置与读回 |
| `DATA_LENGTH[1:0]` | `DATA_SIZE0.SIZE0 + DATA_SIZE1.SIZE1` | 36-bit byte length |
| `IRQ_RAW.<Source>` | `RPT_AES_INT_RAW.<Source bit>` | IRQ 原始 pending 状态 |
| `IRQ_STATUS.<Source>` | `RPT_AES_INT_STATUS.<Source bit>` | Mask 后有效 IRQ 状态 |
| `IRQ_FORCE.<Source>` | `INT_FORCE_IND.<Source bit>` | 软件 Force 刺激 |
| `IRQ_CLEAR.<Source>` | `INT_CLR.<Source bit>` | IRQ 精确清除 |
| `DMA_REQUEST` | `DMA.EN` | AES 输入/输出 DMA Request Gate |
| REGISTER input | `DIN0~DIN3` | 4×32-bit 递增输入端点 |
| REGISTER output | `RESULT_DOUT0~RESULT_DOUT3` | 4×32-bit 递增输出端点 |
| FIFO input | `DATA.DIN` | 固定地址 DMA 输入端点 |
| FIFO output | `RESULT` | 固定地址 DMA 输出端点 |
| `TIMING.CYCLE_COUNT` | Cortex-M `DWT->CYCCNT` Test Extension | CPU路径目标侧周期测量，不是AES寄存器 |
| `DMA_TIMING.CYCLE_COUNT` | DMA目标端计时结果 | DMA输出Channel计时，不是AES寄存器 |
| `AES_CAPABILITIES` | Firmware `CAPABILITIES_GET` 返回的目标侧能力快照 | 运行时只读能力端点，不伪装成寄存器 |

上述映射与当前 SVD/Driver/Capability 一致。公共 `aes.md` 和 Canonical Observation 始终保存稳定语义；报告层根据当前 `chip_id` 选择本表，把稳定语义解析成 ET6801 实际寄存器/Field 名称。

### 2.2 RPT_AES_STS

```text
RPT_AES_STS.DOUT_FLG  -> DOUT_REQ -> W1C
RPT_AES_STS.DIN_FLG   -> DIN_REQ  -> W1C
RPT_AES_STS.FINISH    -> FINISH   -> W1C
```

当前 CPU blocking Driver 的稳定路径为：

```text
Input:
RPT_AES_STS.DIN_FLG = 1
-> Driver 清 DIN_FLG
-> 写 DIN0~DIN3
-> 后续读到 DIN_FLG = 0

Output:
RPT_AES_STS.DOUT_FLG = 1
-> Driver 清 DOUT_FLG
-> 读 RESULT_DOUT0~3
-> 后续读到 DOUT_FLG = 0
```

因此 `AES_P1_006/P1_007` 的 1→0 证明是“请求被 blocking I/O 稳定路径消费/清除”；之后显式 Clear 后继续为 0 只作为无残留复核。`AES_P1_008` 则直接取得 FINISH Clear 前 1、Clear 后 0，可独立证明 FINISH W1C。

### 2.3 IRQ bit 定义

7 个 Source：

```text
bit0 OUTPUT_CONFLICT
bit1 KEY_MISSING
bit2 IV_MISSING
bit3 COMPLETE
bit4 INCOMPLETE_DISABLE
bit5 DATA_IN_REQ
bit6 DATA_OUT_REQ
```

ET6801 Driver 当前 IRQ 路径：

```text
Enable      -> INT_EN
Mask        -> INT_MASK
Force       -> INT_FORCE_IND
Clear       -> INT_CLR
Raw         -> RPT_AES_INT_RAW
Status      -> RPT_AES_INT_STATUS
ISR Evidence-> Service latched + event_count
```

实际 ISR 会确认/清除硬件 pending，因此 IRQ Case 在 ISR 后看到 `RPT_AES_INT_RAW=0` / `RPT_AES_INT_STATUS=0` 是允许的；真实投递由 Service `latched/event_count` 与寄存器来源共同闭环，不能把 Service 值单独伪装成寄存器。

ET6801 Chip Driver 的 Test Extension保留以下受限激励：

```text
AES_testWriteInputBlockThenDisable
  -> 第一块按 DIN_FLG 正常握手写入
  -> 输入被硬件接受后立即 Disable
  -> 用于构造 INCOMPLETE_DISABLE 条件
```

`AES_testWriteInputBlockPair`仍可作为CPU双输入诊断接口，但CPU路径受`data_valid`反压，不能合法构造`OUTPUT_CONFLICT`，不再作为`AES_P1_009`的正式刺激。当前公共Case改用既有AES FIFO DMA、DMA Channel暂停和DMAMUX Route形成“上一笔输出DMA仍Busy时产生下一笔结果”的自然硬件条件。公共Case只使用芯片中立Driver与Execution Mapping，不依赖ET6801寄存器地址或SDK函数名。

上述Test Extension只位于ET6801 Driver的`TEST DRIVER EXTENSION`区域；公共Wrap仅调用稳定Driver接口，不直接访问ET6801寄存器。

## 第三章 Data / Mode / DMA 适配事实

### 3.1 Data Length / Mode

```text
DATA_SIZE1[3:0] : DATA_SIZE0[31:0]
= 36-bit byte count
```

硬件数据长度能力与当前运行时单次处理上限必须分开；公共 Capability 保存硬件 `data_length_bits=36`，运行时 Service/Resource 限制不能改写硬件字段宽度。

稳定算法模式：ECB / CBC / CTR；Key：128 / 256 bit；Padding：NONE / ZERO / PKCS7；Endian：LITTLE / BIG。

### 3.2 DMA Mode

SVD 的 `CRTL.DMA_MODE`：

```text
0 = FIFO, fixed endpoint
1 = REGISTER, 4-word register path
```

ET6801 SDK 历史字段名 `FIFOModeEn` 与硬件 bit 语义相反，因此适配层必须按硬件值翻译：

```text
Stable FIFO     -> hardware DMA_MODE=0
Stable REGISTER -> hardware DMA_MODE=1
```

公共 Case 不依赖 SDK 字段名。

### 3.3 DMA Request / Endpoint

当前 Execution Mapping 使用：

```text
Memory -> AES : DMAMUX_REQ_AES_WR
AES -> Memory : DMAMUX_REQ_AES_RD
```

端点：

```text
REGISTER input  -> DIN0~DIN3
REGISTER output -> RESULT_DOUT0~3
FIFO input      -> DATA
FIFO output     -> RESULT
```

`AES_P2_001` 当前新实现不再只采一次 Channel 状态，而是在 Request Gate 关闭期间连续 8 次读取 `DMA_CHANNEL_STATUS`：输入/输出 Channel 必须全程 Not-Free 且无 ERROR；随后开启 Gate，要求同一 Channel 完成并通过 Golden 数据检查。该增强尚需未来 HIL 复跑才能形成新的硬件 PASS；当前无真机时可以用模拟 Canonical Result 验证 Contract/Evidence/Report 链路。

## 第四章 当前 Evidence / 报告映射

ET6801 最终 Reviewer 关注的核心链：

```text
公共 Observation
-> 本文件实际寄存器/Field 映射
-> PC Case 通过 Driver/Service 取得值
-> record_observation 保留 source + endpoint
-> Canonical Result / 单次最终 Artifact
-> ET_CASE_REPORT
-> Excel Remark / Execution Detail
```

报告寄存器名称解析采用现有文档和现有报告模型，不在公共 `aes.md` 中加入芯片条件分支：

```text
session/result chip_id = ET6801
-> 报告读取同目录 ET6801_aes.md
-> 按 2.1 表解析 Observation.endpoint
-> STATUS.FINISH      -> RPT_AES_STS.FINISH
-> RESULT_DOUT[0..3]  -> RESULT_DOUT0~RESULT_DOUT3
-> IRQ_STATUS.COMPLETE -> RPT_AES_INT_STATUS.COMPLETE
-> Excel Remark 显示 ET6801 实际寄存器/Field 名称
```

Canonical Result 仍保存 `STATUS.FINISH` 等跨芯片稳定语义，因此更换芯片时不需要修改公共 Case；只需要存在对应 `<CHIP>_aes.md` 映射。找不到芯片映射时报告保留稳定语义，不猜测实际寄存器名。

典型示例：

```text
公共 STATUS.FINISH
-> ET6801 RPT_AES_STS.FINISH
-> Actual = 1

公共 RESULT_DOUT[0..3]
-> ET6801 RESULT_DOUT0~3
-> Actual = <16-byte hardware output>

PC Golden
-> Expected = <independent output>

判定
-> FINISH=1 && Actual==Golden
```

公共报告不写物理地址；ET6801 Reviewer 在 Excel 主备注中可看到解析后的实际寄存器/Field 名称，完整稳定 endpoint 仍保存在 Canonical Result / Execution Detail 中。

## 第五章 ET6801 Feature Mapping

| Feature ID | Hardware | ET6801 关键依据 | Platform | 适配说明 |
|---|---|---|---|---|
| AES_F_001 | SUPPORTED | WORK.EN + 重新配置后硬件输出 | ADAPTED | 生命周期由公共Case验证 |
| AES_F_002 | SUPPORTED | CRTL.DIRECTION | ADAPTED | Encrypt/Decrypt均映射 |
| AES_F_003 | SUPPORTED | CRTL.KEY_SIZE + WORK_KEY0~7 | ADAPTED | 128/256-bit |
| AES_F_004 | SUPPORTED | WORK_MODE.MODE | ADAPTED | ECB/CBC/CTR |
| AES_F_005 | SUPPORTED | CRTL.PADDING | ADAPTED | NONE/ZERO/PKCS7 |
| AES_F_006 | SUPPORTED | WORK_IV0~3 | ADAPTED | IV写入/读回 |
| AES_F_007 | SUPPORTED | DATA_SIZE0/1 | ADAPTED | 36-bit byte length |
| AES_F_008 | SUPPORTED | CRTL.ENDIAN_SEL | ADAPTED | LITTLE/BIG |
| AES_F_009 | SUPPORTED | BLOCK_CNT | ADAPTED | CTR initial counter |
| AES_F_010 | SUPPORTED | RPT_AES_WORK.BUSY | ADAPTED | 当前只验证完成终态 |
| AES_F_011 | SUPPORTED | RPT_AES_STS.DIN_FLG | ADAPTED | 非DMA输入请求 |
| AES_F_012 | SUPPORTED | RPT_AES_STS.DOUT_FLG | ADAPTED | 非DMA输出请求 |
| AES_F_013 | SUPPORTED | RPT_AES_STS.FINISH | ADAPTED | 完成状态 |
| AES_F_014 | SUPPORTED | RPT_AES_STS W1C | ADAPTED | 请求消费/FINISH清除 |
| AES_F_015 | SUPPORTED | DIN0~3 / RESULT_DOUT0~3 | ADAPTED | CPU register path |
| AES_F_016 | SUPPORTED | OUTPUT_CONFLICT IRQ bit | ADAPTED | 当前历史HIL曾FAIL，保留真实结果 |
| AES_F_017 | SUPPORTED | KEY_MISSING IRQ bit | ADAPTED | 目标错误源 |
| AES_F_018 | SUPPORTED | IV_MISSING IRQ bit | ADAPTED | 目标错误源 |
| AES_F_019 | SUPPORTED | COMPLETE IRQ bit | ADAPTED | 正常完成中断 |
| AES_F_020 | SUPPORTED | INCOMPLETE_DISABLE IRQ bit | ADAPTED | 未完成关闭中断 |
| AES_F_021 | SUPPORTED | DATA_IN_REQ IRQ bit | ADAPTED | IRQ transfer输入推进 |
| AES_F_022 | SUPPORTED | DATA_OUT_REQ IRQ bit | ADAPTED | IRQ transfer输出推进 |
| AES_F_023 | SUPPORTED | INT_EN | ADAPTED | Source enable |
| AES_F_024 | SUPPORTED | INT_MASK | ADAPTED | Mask/Unmask |
| AES_F_025 | SUPPORTED | INT_FORCE_IND | ADAPTED | 软件Force |
| AES_F_026 | SUPPORTED | INT_CLR | ADAPTED | 精确Clear |
| AES_F_027 | SUPPORTED | RPT_AES_INT_RAW / RPT_AES_INT_STATUS | ADAPTED | RAW/STATUS语义 |
| AES_F_028 | SUPPORTED | IRQ寄存器 + Service latched/event_count | ADAPTED | 真实ISR Evidence |
| AES_F_029 | SUPPORTED | DMA.EN + DMA Channel状态 | ADAPTED | Request Gate；新8-sample实现待复跑 |
| AES_F_030 | SUPPORTED | DIN0~3 / RESULT_DOUT0~3 DMA端点 | ADAPTED | REGISTER模式 |
| AES_F_031 | SUPPORTED | DATA / RESULT固定端点 | ADAPTED | FIFO模式；历史HIL FAIL保留 |
| AES_F_032 | SUPPORTED | DMA Actual + independent Golden | ADAPTED | 与CPU路径共用独立Oracle |
| AES_F_033 | SUPPORTED | DWT->CYCCNT Test Extension | ADAPTED | CPU目标周期 |
| AES_F_034 | SUPPORTED | DMA TRANSFER_DONE目标计时 | ADAPTED | DMA目标周期；历史HIL FAIL保留 |
| AES_F_035 | SUPPORTED | AES实例、模式、密钥长度、IRQ、DMA与处理上限由Capability/Runtime身份声明 | ADAPTED | `AES_P0_001` |

`SUPPORTED/ADAPTED` 表示硬件语义和平台实现已映射，不代表最新 HIL 一定 PASS。

## 第六章 ET6801 Case Adaptation

| Case ID | Adaptation | ET6801 当前说明 |
|---|---|---|
| AES_P0_001 | ADAPTED | 静态semantic gate + 只读AES_CAPABILITIES；运行时查询可用仿真验证报告链路，硬件状态不因此升级 |
| AES_P0_002 | ADAPTED | NIST矩阵 + RESULT_DOUT + FINISH；历史HIL PASS |
| AES_P0_003 | ADAPTED | 双轮重新使能；历史HIL PASS |
| AES_P1_001 | ADAPTED | Padding边界；历史HIL PASS |
| AES_P1_002 | ADAPTED | IV读回/算法影响；历史HIL PASS |
| AES_P1_003 | ADAPTED | DATA_SIZE0/1 + BUSY/FINISH终态；历史HIL PASS |
| AES_P1_004 | ADAPTED | LITTLE/BIG canonical输出；历史HIL PASS |
| AES_P1_005 | ADAPTED | BLOCK_CNT；历史HIL PASS |
| AES_P1_006 | ADAPTED | DIN_FLG请求消费/清除复核；历史HIL PASS |
| AES_P1_007 | ADAPTED | DOUT_FLG + RESULT_DOUT；历史HIL PASS |
| AES_P1_008 | ADAPTED | FINISH 1→0 W1C + RESULT_DOUT独立来源；历史HIL PASS |
| AES_P1_009 | ADAPTED | 已按权威语义改为FIFO DMA输出Busy冲突刺激；2026-08-28定向FPGA HIL PASS，历史CPU双输入FAIL仅保留为旧刺激证据 |
| AES_P1_010 | ADAPTED | KEY_MISSING；历史HIL PASS |
| AES_P1_011 | ADAPTED | IV_MISSING；历史HIL PASS |
| AES_P1_012 | ADAPTED | COMPLETE IRQ + RESULT_DOUT；历史HIL PASS |
| AES_P1_013 | ADAPTED | 使用输入握手后立即Disable的Test Extension构造INCOMPLETE_DISABLE；当前FPGA HIL PASS |
| AES_P1_014 | ADAPTED | IRQ Transfer STATE/Offset/Output；历史HIL PASS |
| AES_P1_015 | ADAPTED | 5 Source Force/Delivery；历史HIL PASS |
| AES_P1_016 | ADAPTED | COMPLETE Mask/Unmask；历史HIL PASS |
| AES_P1_017 | ADAPTED | 7 Source RAW精确Clear；历史HIL PASS |
| AES_P2_001 | ADAPTED | 新增Gate关闭8次有界观测；旧实现历史PASS不能代替新实现复跑 |
| AES_P2_002 | ADAPTED | REGISTER双向DMA；历史HIL PASS |
| AES_P2_003 | ADAPTED | FIFO固定端点；历史FPGA HIL FAIL，未被本轮整改改写 |
| AES_P3_001 | ADAPTED | 8轮确定性/状态隔离；历史HIL PASS |
| AES_P3_002 | ADAPTED | CPU目标周期；历史HIL PASS |
| AES_P3_003 | ADAPTED | FIFO DMA目标周期；历史FPGA HIL FAIL，未被本轮整改改写 |

## 第七章 历史 HIL 与当前验收边界

2026-08-20 当次 ET6801 FPGA Evidence 记录：

```text
59 executions
58 PASS
1 FAIL
```

当次 FAIL：

```text
AES_P1_009 OUTPUT_CONFLICT
```

当前双输入块激励仍未使 `OUTPUT_CONFLICT` 的 RAW/STATUS/latched 置位，因此保留真实 FAIL，不通过弱化断言伪造覆盖。输入握手后立即 Disable 已稳定触发 `INCOMPLETE_DISABLE`，FIFO fixed RESULT 与 FIFO DMA timing/data 路径也在本轮通过；这些结论仅适用于本次 ET6801 FPGA Evidence。

当前 AES 的“模板验收”和“硬件验证状态”分开：

```text
模板/软件/Contract审核：
公共aes.md
+ ET6801寄存器映射
+ 现有Case实现
+ 模拟Canonical Result
+ Report/Excel输出
+ 现有Checker/Collection Gate（环境可执行时）

硬件验证状态：
当前精确SHA的FPGA/Silicon HIL
```

没有真机时，可以通过模拟 Canonical Result 完成 `Stable endpoint -> ET6801实际寄存器名 -> ET_CASE_REPORT -> Excel` 的报告链审核，并据此判断 AES 的 Case/Evidence/Report 设计是否可作为其他 IP 模板。模拟通过不能把任何 Feature 的硬件状态升级为 PASS；硬件状态只由对应精确代码和镜像的 HIL Evidence 更新。

### 7.1 OUTPUT_CONFLICT 整改闭环记录

时间：2026-08-28 08:08 CST

| Case | 测试环境 | 实际硬件现象 | 已排除的软件链路问题 | 当前判定 | Evidence |
|---|---|---|---|---|---|
| `AES_P1_009` | ET6801 FPGA；AES FIFO DMA输入2个Block，输出DMA仅接收1个Block并保持Busy | `ISR.LATCHED.OUTPUT_CONFLICT=1`，`event_count: 0→1`；清除后latched/raw/status均为0；复位后CPU PROCESS结果与Golden完全一致 | CPU双输入受`data_valid`反压，不能构造冲突；新Case改由真实DMA输出Busy状态产生第二笔AES结果 | `PASS` | `artifacts/runs/20260828_0811_aes_p1_009/` |

2026-08-24 CPU双输入复测结果保留为旧刺激诊断证据，不再代表当前正式Case结论。正式Case以2026-08-28 DMA Busy冲突HIL结果为准。

<!-- ET_CHIP_TEST_STATUS_BEGIN -->
## 当前芯片测试状态

状态更新时间：`2026-08-28 21:20 CST`

### 最近一次运行身份

| Lane | 测试时间 | Source Revision | Source Dirty | Evidence |
|---|---|---|---|---|
| FPGA | `2026-08-28 17:13 CST` | `596c1a73b91f6af577b1b274d49c34f8d9fb823a` | `false` | `artifacts/runs/20260828_170737_043300_local_et6801_fpga/tests/aes/` |

### 当前结果汇总

| Lane | 注册Case | 已执行Case | PASS | FAIL | SKIP | NOT_EXECUTED | Executions |
|---|---:|---:|---:|---:|---:|---:|---:|
| FPGA | 26 | 26 | 26 | 0 | 0 | 0 | 59 |

### 当前非PASS Case

| Case ID | Lane | 状态 | Feature | 测试现象 | 原因/阻塞 | 复测条件 | Evidence |
|---|---|---|---|---|---|---|---|
| — | FPGA | NONE | — | — | — | — | — |
<!-- ET_CHIP_TEST_STATUS_END -->
