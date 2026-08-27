# ET6801 CRC一键运行与Excel报告HIL验证

时间：2026-08-12 23:20 CST

## 结论

本轮在ET6801 FPGA原型硬件上，通过正式入口`run_test.bat`完成CRC全量HIL测试，并成功生成Excel报告。

- 一键脚本：通过实际启动、环境检查、依赖恢复、pytest执行和报告导出验证。
- 硬件执行：45个参数化执行节点中43 PASS、2 FAIL、0 SKIP。
- 稳定Case汇总：24个稳定Case中22 PASS、2 FAIL，报告状态为“完整”。
- Excel报告：包含“测试报告”“执行明细”“规格追溯”三张工作表；公式错误扫描为0，三张工作表均完成可视化检查。
- 失败真实性：两个FAIL均保留为真实硬件结论，未放宽断言、未伪造PASS。

## 目标与环境

- 目标芯片：ET6801
- 目标形态：XC7VX980T FPGA原型
- 固件标识：`et6801-silicon-common-v0.1`
- Runtime Registry Hash：`bd8d2981`
- 连接路径：J28 RS232控制串口，`COM12 @ 115200`
- Bench：`pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`
- Bench SHA256：`983ac73927aa56460c2fd45c468fc0a917a5c13efebf20ccc3b7f1fdad220222`
- Case Spec SHA256：`38577702e06675f8559edcbd97844d27eb52fd3e6da00f2fd9736b7f56e08a3e`
- 源码Revision：`013426d740531bbb26b83a58629f2df18e4ddba6`
- 源码状态：Dirty；本报告只证明所记录工作树，不升级为exact-SHA发布结论。
- 破坏性：否；未重新配置bit、未加载BootROM、未擦写PFLASH。

## 测试方法

1. 使用`run_config.json`选择CRC、ET6801 Bench和`dut`目标，并配置真实串口环境变量。
2. 从正式入口`run_test.bat`启动，不绕过bootstrap或`run_ip_tests.py`。
3. 由脚本完成本地Python环境检查、依赖检查、Formal Case执行和Excel报告生成。
4. 对`session.json`和所有`result.json`核对选择范围、PASS/FAIL数量、证据完整性和失败测量值。
5. 用严格XLSX解析器导入报告，扫描公式错误，并渲染三张工作表做可视化检查。
6. 执行完整无硬件软件门禁，确认本轮修复没有破坏公共合同。

## 硬件结果

```text
Collected executions: 45
PASS:                 43
FAIL:                  2
SKIP:                  0

Stable cases:         24
Stable PASS:          22
Stable FAIL:           2
Report state:       完整
```

失败项：

1. `crc_p1_011_fifo_threshold`
   - 配置阈值：5
   - 写入前Result：`3174720732`
   - 第4次写入后Result：`2906116182`
   - 第5次写入后Result：`2906116182`
   - FIFO Overflow：`false`
   - 结论：硬件未呈现Case要求的“第5次达到阈值后才更新Result”行为。
2. `crc_p1_012_fifo_overflow_recovery`
   - 配置阈值：1
   - 连续写入次数：7
   - 期望FIFO Overflow：`true`
   - 实际FIFO Overflow：`false`
   - 结论：硬件未呈现Case要求的FIFO Overflow状态转换。

两个失败结果都具有完整DUT证据，脚本正确返回退出码1，同时仍生成完整Excel报告。这证明失败传播和失败报告链路有效。

## 测试中发现并修复的问题

本轮只做三个局部、可回归的工具层修复，没有修改公共架构、协议、Case语义、Driver、Firmware或硬件执行逻辑。

1. `run_test.bat`在括号块内使用`%errorlevel%`，会读取解析时旧值，导致已经存在`python.exe`时仍误报“Python未安装”。改为执行时判断`if not errorlevel 1`。
2. 已存在`.venv`但缺少pip时，bootstrap不能恢复。增加按需`ensurepip`恢复；只有pip缺失时执行，不改变正常路径。
3. XLSX Case批注作者为空，严格解析器拒绝导入。报告生成器使用统一非空作者，并增加实际生成XLSX后检查批注XML的行为测试。

## 回归验证

```text
Ruff format: PASS
Ruff lint: PASS
Software validation: 463 passed, 9 skipped
Formal Case collection: PASS
XLSX export gate: PASS
```

## 证据

- 原始运行日志：`artifacts/operator_hil/20260812_crc_full/run_test.log`
- 本轮Session：`artifacts/case_runs/20260812_230957_266699/session.json`
- Case结果：`artifacts/case_runs/20260812_230957_266699/cases/`
- Excel报告：`artifacts/case_runs/20260812_230957_266699/et6801_CRC测试报告.xlsx`
- 软件门禁日志：`artifacts/software_validation/20260812_post_hil/validate_pc.log`

## 剩余风险与下一步

- `crc_p1_011`和`crc_p1_012`仍是ET6801 FPGA硬件Feature失败，不能归类为平台失败，也不能改成SKIP或PASS。
- 本轮没有重新烧录当前工作树固件，因此结论绑定运行中固件标识和Registry Hash，不等同于最终提交SHA的完整Flash启动验证。
- 严格XLSX工具完成导入、公式扫描和三表渲染后，在进程退出阶段出现第三方原生运行时异常；已生成的渲染结果和工作簿检查数据完整，且XLSX容器与批注XML另行验证通过。该退出异常不影响报告文件，但后续可单独跟踪工具运行时兼容性。
