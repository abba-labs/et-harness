# ET6801 DMA 全 Feature FPGA/HIL 验证报告

时间：2026-08-02 15:20 CST

## 结论

本轮已把 DMA 规格中的 39 个规划 Case 全部纳入正式执行和结果分类，覆盖 35 个硬件 Feature。这里的“全部测试”表示每个 Feature 都有明确结果，不代表全部 PASS。

- Case 级结果：17 PASS、1 FAIL、21 条件阻塞/未实现。
- 参数化硬件执行实例：65 个，其中 42 PASS、2 FAIL、21 SKIP。
- 唯一 FAIL：`DMA-F-020 DONE写回`。DMA0、DMA1 均在配置 disable（描述符初始 DONE=0）时，于传输完成后将 DONE 写成 1；数据搬运正确且描述符其他字不变，但与当前 enable/disable 契约不符。
- 其余可在当前板上自主执行的 M2M、双控制器、全通道、宽度、地址模式、burst、block 边界、FIFO、suspend/resume、TFR/BLOCK IRQ、RAW/MASK/CLEAR、gather/scatter、LLI、ACC 别名和 100 轮混合稳定性均通过。
- 需要外设 DMA 请求、CORE1/TCM、安全错误地址或未批准设计契约的项目没有冒充 PASS。

## 环境与镜像

- 目标：XC7VX980T 上的 ET6801 FPGA 原型，CORE0。
- 控制链路：J-Link JTAG + J28 RS232/COM12，115200 8N1。
- FPGA bit：`ET6801_RTLr1800_FPGAv102_20260313/bit_files/et6801_fpga_top.bit`。
- bit SHA256：`953CEAA20D9B64BD103769CD8B721BEE864377C812CD7BAE016BF2E109921B2C`。
- 固件：`et6801_test_silicon.axf`。
- 固件 SHA256：`F12EDCA36AFA140339F9F106B375302215043857F6A0EBBA35E521A42631CEC9`。
- Flash：PFLASH0 `0x08000000–0x0807FFFF`，Erase/Program/Verify OK；复位向量 `0x080003A1`，运行 PC `0x080074CA`，确认位于 Flash。
- 操作性质：bit 与 BootROM 为易失加载；PFLASH 擦写为破坏性操作。
- 恢复路径：重新配置已知 bit，加载 BootROM 到 `0x20500000` 并到达 main，再擦写/Verify PFLASH。

## 35 个 Feature 结果

| Feature | 结果 | 本轮证据/限制 |
|---|---|---|
| DMA-F-001 双控制器 | PASS | DMA0、DMA1 均执行基础、并发、IRQ、LLI和稳定性用例 |
| DMA-F-002 8通道 | PASS | 生命周期覆盖 CH0～CH7；两控制器各8通道并发；TFR IRQ覆盖全部通道 |
| DMA-F-003 模块使能 | PASS | 两控制器重复 enable/disable 与恢复通过 |
| DMA-F-004 通道生命周期 | PASS | configure/start/stop/deconfigure 全通道通过 |
| DMA-F-005 通道状态 | PASS | free/busy/FIFO empty 在基础、暂停和完成路径验证 |
| DMA-F-006 空闲通道分配 | PASS | 初始空闲通道和生命周期后释放通过 |
| DMA-F-007 传输类型 | blocked_by_board | M2M PASS；M2P/P2M/P2P 缺少已配置外设请求端点 |
| DMA-F-008 传输宽度 | PASS | 8/16/32 bit，DMA0/1 |
| DMA-F-009 地址变化 | PASS | source/destination increment/decrement/fixed 矩阵 |
| DMA-F-010 burst item数 | PASS | 1/4/8/16/32/64/128/256 |
| DMA-F-011 block size | PASS | 1、2、3、4、7、8、15、16、255、256、4094、4095及非法0/4096 |
| DMA-F-012 通道优先级 | not_implemented | 缺少完成/进度顺序 trace，不能仅凭寄存器回读判定仲裁 |
| DMA-F-013 FIFO模式 | PASS | single、half-depth，双控制器 |
| DMA-F-014 外设请求接口 | blocked_by_board | 当前 bench 未冻结 DMAMUX 外设 peer 路由 |
| DMA-F-015 suspend/resume | PASS | 双控制器 reload 持续传输，suspend、FIFO drain、resume、再次 suspend、停止恢复 |
| DMA-F-016 多块模式 | not_implemented | contiguous、reload实际运行、LLI均已验证；有限 reload 精确 N 次停止原语未实现 |
| DMA-F-017 LLI描述符 | PASS | 双控制器2/3/4块有限链；source-only、destination-only、双边更新 |
| DMA-F-018 source gather | PASS | 双控制器数据布局和保护区通过 |
| DMA-F-019 destination scatter | PASS | 双控制器数据布局和保护区通过 |
| DMA-F-020 DONE写回 | FAIL | disable路径仍由0写为1；DMA0/1一致，数据正确、非CTL_H字未改 |
| DMA-F-021 分类中断 | blocked_by_board | TFR、BLOCK PASS；SRC/DST缺外设请求；ERR缺安全非致命故障地址 |
| DMA-F-022 中断位图 | PASS | 全通道TFR、BLOCK边界通道、独立mask/raw/status/clear状态机 |
| DMA-F-023 TCM地址转换 | blocked_by_profile | 未声明可破坏ITCM/DTCM窗口和CORE1视图 |
| DMA-F-024 COMBINED IRQ | not_implemented | Wrap尚未提供combined物理向量路由 |
| DMA-F-025 RAW/masked状态 | PASS | DMA0/1均验证masked RAW置位、STATUS抑制、CLEAR及重新unmask |
| DMA-F-026 软件握手 | not_implemented | 软件request寄存器尚无公共Wrap API |
| DMA-F-027 握手极性 | blocked_by_board | 当前bench无可控请求极性源 |
| DMA-F-028 软硬件握手选择 | not_implemented | 软件握手API和对应peer均未准备 |
| DMA-F-029 最大AMBA burst | blocked_by_design | 设计契约未批准 |
| DMA-F-030 AHB master选择 | blocked_by_design | master路由与可达存储矩阵未批准 |
| DMA-F-031 protection control | blocked_by_design | 权限属性与安全拒绝窗口未批准 |
| DMA-F-032 flow-control mode | blocked_by_design | 外设flow-controller端点未批准 |
| DMA-F-033 component capability/ID | PASS | 普通/ACC视图一致；组件ID、通道参数、多块和最大块参数可读 |
| DMA-F-034 low-power timeout | blocked_by_design | 低功耗状态与唤醒观测契约未批准 |
| DMA-F-035 test slave interface | blocked_by_design | DFT授权与安全序列未批准 |

## 39 个 Case 汇总

- P0：5 PASS，1 `blocked_by_profile`。
- P1：8 PASS，1 FAIL，2 `not_implemented`。
- P2：4 PASS，3 `blocked_by_profile`，6 `blocked_by_board`，3 `not_implemented`。
- P3：6 `blocked_by_design`。

参数化实例明细以 JUnit 为准：

- `artifacts/20260802_dma_all_features/formal_p0_final3/pytest_dma_p0.xml`
- `artifacts/20260802_dma_all_features/formal_p1_final/pytest_dma_p1.xml`
- `artifacts/20260802_dma_all_features/formal_p2_final/pytest_dma_p2.xml`
- `artifacts/20260802_dma_all_features/formal_p3_final/pytest_dma_p3.xml`

结构化子项证据位于上述各目录；Flash 证据为 `artifacts/flash_run/20260802_151425/manifest.json`。

## 发现与后续

1. DONE写回需要先确认 SVD/RTL 对 DONE 的真实契约。当前硬件事实是 `CTL_H: 0x00000040 -> 0x00001040`；在确认前不得把公共 flag 解释为可靠的“写回禁用”。
2. 优先级仲裁需要进度trace；有限reload需要通用、可复用的硬件停止条件，不能把Case逻辑塞进ISR。
3. M2P/P2M/P2P、SRC/DST IRQ和握手能力应在冻结 DMAMUX peer/双板 bench 后执行。
4. 错误注入、TCM/CORE1、复位时钟和P3设计条件项必须先批准安全窗口与契约。
5. 本轮仅证明数字功能，且为单块FPGA原型、单一bit/固件、常温短时验证；不覆盖电气、时序裕量、电压、温度和长期老化。
