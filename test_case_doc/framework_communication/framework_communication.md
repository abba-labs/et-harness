# Framework Communication Stable Contract

> 本文件只定义测试框架与目标固件之间跨芯片稳定的通信 Feature、Case 和 Report Contract。
> 具体芯片连接方式、串口号、波特率、固件镜像和板级配置属于运行配置与 Bench Profile。

## 0. Stable Contract

- IP：`framework_communication`。
- 本测试域验证平台公共通信链路，不绑定具体芯片、Transport实现或物理接口。
- 载荷大小和轮数属于稳定测试计划；目标连接参数由运行配置提供。

## 1. Feature Catalog

| Feature ID | 报告名称 | 稳定语义 | 关联Case |
|---|---|---|---|
| FRAMEWORK_COMMUNICATION_F_001 | ET-Frame Mixed Payload ECHO完整性 | 小、中、大确定性载荷经公共协议往返后逐字节一致 | `FRAMEWORK_COMMUNICATION_P3_001` |
| FRAMEWORK_COMMUNICATION_F_002 | ET-Frame Bounded Retry重试 | 每类载荷的请求次数、重试次数和错误数均形成结构化事实 | `FRAMEWORK_COMMUNICATION_P3_001` |
| FRAMEWORK_COMMUNICATION_F_003 | ET-Frame Communication Throughput吞吐 | 固定轮次内完成全部事务并记录延迟和有效往返吞吐 | `FRAMEWORK_COMMUNICATION_P3_001` |

## 2. Case Catalog

| Case ID | P级 | 测试Feature | Case名称 | 状态 |
|---|---|---|---|---|
| FRAMEWORK_COMMUNICATION_P3_001 | P3 | 混合载荷ECHO完整性、有界重试和通信稳定性 | Framework混合载荷通信压力测试 | SPEC |

## 3. Machine-readable Case Contract

<!-- ET_CASE_SPEC_BEGIN -->
```yaml
schema: et.case.v1
case_id: FRAMEWORK_COMMUNICATION_P3_001
case_name: Framework混合载荷通信压力测试
report_feature: |-
  1. ET-Frame Mixed Payload ECHO完整性
  2. ET-Frame Bounded Retry重试
  3. ET-Frame Communication Throughput吞吐
p_level: P3
feature_refs:
  - FRAMEWORK_COMMUNICATION_F_001
  - FRAMEWORK_COMMUNICATION_F_002
  - FRAMEWORK_COMMUNICATION_F_003
legacy_trace:
  - 既有Framework ECHO小中大载荷压力测试
current_spec_evidence:
  - pc/et_test_platform/test_cases/framework_communication/test_framework_communication_p3.py
method:
  inputs:
    - Payload覆盖矩阵：使用测试计划声明的小、中、大三类确定性Payload及固定20轮执行次数。
    - 目标通信连接：使用运行配置和Bench Profile提供的同一ET-Frame目标连接。
  steps:
    - 通信会话建立：连接目标并完成HELLO及Framework Service能力确认。
    - Payload实例准备：按小、中、大顺序为当前轮构造确定性二进制Payload和独立Expected。
    - ECHO事务发送：为当前Payload发起一次有界ECHO事务，由公共Driver执行协议重试。
    - 响应数据核对：收到响应后立即逐Byte比较ECHO Actual与当前Payload Expected。
    - 事务测量累计：累计各类Payload的事务数、重试次数、延迟和往返字节数。
    - 覆盖矩阵推进：重复上述流程直至三类Payload均完成固定20轮执行。
    - 汇总结果校验：核对总事务数、总往返字节数、吞吐率和错误数并保存决定性Evidence。
  observations:
    - 分类事务统计：记录各Payload类别的完成事务数、协议重试次数和往返延迟。
    - 会话汇总统计：记录总事务数、总往返字节数、有效吞吐率和通信错误数。
  pass_criteria:
    - Payload完整性：每笔ECHO响应必须与对应请求Payload逐Byte完全一致。
    - 执行覆盖完整性：小、中、大三类Payload必须全部完成固定20轮事务。
    - 汇总统计正确性：总事务数和总往返字节数必须与测试计划一致，错误数必须为零。
timeout: 使用Framework Driver已有的单请求Deadline和固定20轮测试上限
cleanup:
  - 由公共Fixture关闭目标通信会话和Transport
resources:
  minimum_level: R1
  full_coverage_level: R1
  board: 需要一个能够运行公共测试固件的目标设备。
  bench: 需要运行配置声明的目标通信链路，不需要外部仪器。
backend:
  - FPGA
  - Silicon
evidence:
  - Framework通信压力结构化结果
  - canonical result.json与session.json
failure_observations:
  - key: expected_transactions
    label: 计划事务数
    source: oracle
    role: expected
    format: decimal
  - key: transactions
    label: 实际完成事务数
    source: dut
    role: actual
    format: decimal
  - key: error_count
    label: 通信错误数
    source: dut
    role: actual
    format: decimal
gap:
  - case_measurement_gap
```
<!-- ET_CASE_SPEC_END -->

<!-- ET_CASE_REPORT_BEGIN -->
```yaml
schema: et.case-report-note.v1
cases:
  FRAMEWORK_COMMUNICATION_P3_001:
    summary: "Framework混合载荷ECHO完整性和通信稳定性验证完成。"
    fields:
      - {source: "artifact", path: "transactions", label: "完成事务数", format: "decimal", aggregate: "same"}
      - {source: "artifact", path: "payload_bytes_round_trip", label: "往返数据量", format: "decimal", aggregate: "same", unit: "字节"}
      - {source: "artifact", path: "payload_throughput_bytes_per_second", label: "有效往返吞吐", format: "float", aggregate: "same", unit: "B/s"}
      - {source: "artifact", path: "error_count", label: "通信错误数", format: "decimal", aggregate: "same"}
```
<!-- ET_CASE_REPORT_END -->

## 4. Adaptation Boundary

- Transport类型、端口、目标身份和固件镜像由运行配置、Bench Profile及Backend适配。
- 公共Case、Driver和本契约不得出现具体芯片、串口号、物理实例或板级引脚。
- 新芯片只要实现同一公共通信协议即可复用本Case，不复制测试文件。
