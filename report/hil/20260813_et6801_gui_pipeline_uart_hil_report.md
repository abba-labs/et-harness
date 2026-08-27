# ET6801 GUI配置、完整Pipeline与UART HIL验证报告

时间：2026-08-13 12:20 CST

## 1. 结论

本轮已经打通并实际验证以下链路：

```text
run_config_gui.bat
  -> run_config.yaml保存与检查
  -> 环境/代码门禁
  -> BootROM编译
  -> ET6801测试固件编译
  -> XC7VX980T bit配置
  -> BootROM临时加载并到达main
  -> PFLASH擦除、编程、Verify和Flash运行
  -> UART Formal Case执行
  -> Excel报告生成与复核
```

最终结果：Pipeline硬件部署PASS；UART共33个稳定Case，30 PASS、3 SKIP、0 FAIL；Excel报告成功生成，结构、内容、公式错误和视觉排版检查通过。

## 2. 范围与环境

- target：ET6801 FPGA原型。
- FPGA：XC7VX980T，Vivado Hardware Target `Digilent/210251A08870`。
- 控制链路：J-Link + JTAG，PFLASH编程时VTarget为3.251 V，JTAG Speed为5000 kHz。
- PC通信：J28 RS232，`COM12@115200`。
- Firmware Target：`ET6801_SILICON_FLASH`。
- Firmware身份：`et6801-silicon-common-v0.1`。
- Bench：`pc/et_test_platform/profiles/bench_topologies/et6801_uart_template.yaml`。
- 硬件影响：重新配置XC7VX980T bit；BootROM临时写入RAM；擦除并重写PFLASH0。未写OTP/NVR/Fuse。
- 恢复方式：重新配置已知bit、重新加载BootROM、重新烧录已知PFLASH镜像。

## 3. GUI卡顿整改与实际操作验证

`tools/runner/run_config_gui.py`将子进程日志改为有界批量刷新：每次最多处理200条、80 ms合并一次文本更新，避免Tk文本控件被逐行高频刷新拖慢。子进程同时固定`PYTHONIOENCODING=utf-8`，消除中文日志乱码。

通过真实`run_config_gui.bat`完成以下操作：

1. 打开GUI并修改`config.name`。
2. 点击保存，Shell重新读取`run_config.yaml`，确认修改值已经落盘。
3. 点击“检查配置”，GUI显示当前配置名称、环境检查结果和`Pipeline check-only: PASS`。
4. 恢复正式本地配置后再次检查，中文日志显示正常。

## 4. 56项GUI配置字段验证

自动化契约测试遍历`tools/runner/run_config_gui_schema.yaml`的全部56个字段：

1. 按字段控件类型生成替代值。
2. 通过GUI共用的原子YAML写入函数保存。
3. 重新读取并逐项核对值和类型。
4. 恢复目标/Profile一致性后由正式`run_pipeline.py`解析整份配置。

另外分别验证：

- target、DUT串口、配测FPGA、Peer开发板、示波器和电源配置进入正式运行环境。
- Python、Keil、Pack、Vivado、J-Link、BootROM工程、bitfile和探针配置进入对应动作命令。
- build/deploy/start/test/report开关、硬件确认门禁和关闭式未知字段校验生效。
- GUI Schema不包含IP、P等级和Case选择，测试选择仍由注册表管理。

软件验证结果：

```text
run_config.yaml --check-only                         PASS
Ruff（GUI/Pipeline/Operator Launcher）               PASS
Operator Launcher契约测试                            27 PASS
完整Software Quality Gate                           476 PASS / 9 SKIP
```

## 5. 实际Pipeline硬件结果

### 5.1 编译

- BootROM：0 Error、0 Warning；ROM 29836/32768 bytes，RAM 13632/16384 bytes。
- 测试固件：`ET6801_TEST_FIRMWARE_BUILD_PASS`，Target为`ET6801_SILICON_FLASH`。

### 5.2 bit配置

XC7VX980T配置后关键状态：

```text
CRC_ERROR=0
EOS=1
DONE_INTERNAL=1
DONE_PIN=1
IDCODE_ERROR=0
SECURITY_ERROR=0
```

### 5.3 BootROM与PFLASH

```text
ET6801_BOOTROM_MAIN_REACHED|PC=0x20506348
Erase Done.
Programming Done.
Verify OK.
ET6801_FLASH_RUN_PASS|reset=0x080003A1|pc=0x0800D016|region=flash
Configured pipeline: PASS
```

运行过程中发现本地`run_config.yaml`仍期待旧的FPGA RAM构建身份，正式Flash固件返回`et6801-silicon-common-v0.1`。身份门禁按设计拒绝继续执行；修正本机配置的`dut.expected.firmware_build_id`后重新运行通过。没有放宽身份校验或增加兼容分支。

## 6. UART HIL与报告

UART通过正式`tools/runner/run_ip_tests.py`入口执行，测试选择仍来自UART注册表，不向运行配置加入IP选择字段。

```text
33 collected
30 passed
3 skipped
0 failed
duration: 27.18 s
```

3个SKIP均由正式门禁产生：

| Case | 原因 |
|---|---|
| `uart_p1_008` | 当前TX/RX板级连接无法确定性制造framing error。 |
| `uart_p1_012` | 当前硬件在Driver有界触发窗口内未形成确定性Busy Detect条件。 |
| `uart_p3_009` | 当前Firmware运行时能力未提供`FIFO_ACCESS`。 |

生成报告：

`../../../artifacts/operator_hil/20260813_gui_pipeline/uart_case_run/20260813_120531_648746/et6801_UART测试报告.xlsx`

报告复核结果：

- 工作表：`测试报告`、`执行明细`、`规格追溯`。
- 结构：3张工作表、3个数据表，稳定Case 33项。
- 公式错误扫描：0。
- 视觉检查：标题、表头、PASS/SKIP配色、换行、执行错误列和规格追溯列均可读；未发现明显截断或布局破坏。
- 报告状态为“不完整”是因为3个稳定Case为SKIP，不是报告生成失败。

## 7. 证据

- 完整Pipeline日志：`../../../artifacts/operator_hil/20260813_gui_pipeline/pipeline.log`
- UART日志：`../../../artifacts/operator_hil/20260813_gui_pipeline/uart_hil.log`
- UART Session：`../../../artifacts/operator_hil/20260813_gui_pipeline/uart_case_run/20260813_120531_648746/session.json`
- UART Case结果：`../../../artifacts/operator_hil/20260813_gui_pipeline/uart_case_run/20260813_120531_648746/cases/`
- Excel报告：`../../../artifacts/operator_hil/20260813_gui_pipeline/uart_case_run/20260813_120531_648746/et6801_UART测试报告.xlsx`
- 环境Doctor：`../../../artifacts/operator_hil/20260813_gui_pipeline/et_config_doctor.json`
- BootROM构建：`../../../artifacts/et6801_cli_flow/20260813_115422/02_bootrom_build/`
- 固件构建：`../../../artifacts/firmware_build/20260813_115528_SILICON/`
- bit配置：`../../../artifacts/et6801_cli_flow/20260813_115658/01_xc7vx980t_program/`
- BootROM加载：`../../../artifacts/et6801_cli_flow/20260813_115936/04_bootrom_keil_debug/`
- Flash运行：`../../../artifacts/flash_run/20260813_120102/`

## 8. 剩余边界

- 3个UART SKIP仍需对应硬件激励或Firmware能力后才能转为PASS/FAIL，本轮没有伪造覆盖。
- 当前验证证明了ET6801 FPGA本机配置和现有硬件链路；换电脑后仍需在GUI中填写该机器的工具路径、端口、镜像和探针信息，再执行配置检查。
- 工作树存在未提交改动，因此本报告不等同于GitHub exact-SHA CI结论。
