# ET6801 DMA中断Case硬件前验证

时间：2026-07-27 07:16 CST

## 范围

- 芯片：ET6801
- Lane：firmware、PC pytest
- 硬件：本记录阶段未操作真实硬件
- Case：DMA0 Channel 0内存搬运完成中断（`TRANSFER_DONE`）

## 实现结论

- IRQ Wrap已去除UART/DMA等IP语义，只接受物理`et_irq_line_t`并负责运行时向量、NVIC、Pending和临界区。
- IRQ Manager已实现固定数组绑定、共享Line分发、首绑定安装公共入口、末绑定卸载和幂等重复绑定。
- UART Wrap与DMA Wrap各自负责本IP语义事件到当前芯片物理Line的映射。
- 控制UART已迁移到相同IRQ Manager，不再由Application直接注册IRQ Wrap。
- 新增Resource Service，PC可创建、写入、填充和读回固件静态测试缓冲区。
- 新增DMA Service与PC DMA Driver；固件仅执行原子命令，完整DMA测试顺序由PC Case组合。
- Resource Pool由ET6801链接脚本放到`0x20400000`系统SRAM，避免DMA访问DTCM失败。

## 验证

1. `et-sdk-build`配置检查：`status=ok`。
2. ET6801 SDK布局扫描：`status=ok`。
3. PC框架单测：42项PASS。
4. `ET6801_FPGA_ITCM`：Keil 0 Error、0 Warning。
5. `ET6801_SILICON_FLASH`：Keil 0 Error、0 Warning。
6. FPGA与SILICON Map均确认`resource_pool_words = 0x20400000`，大小8192字节。
7. 正式DMA硬件Case收集成功：1项。

## 证据

- `artifacts/20260727_dma_irq_case/et_config_doctor.json`
- `artifacts/20260727_dma_irq_case/et_sdk_scan_et6801.json`
- `artifacts/firmware_build/20260727_071206_FPGA`
- `artifacts/firmware_build/20260727_071338_SILICON`
- `Et_Automated_Testing_Platform_Code/firmware/build/et6801/Listings/et6801_test_fpga.map`
- `Et_Automated_Testing_Platform_Code/firmware/build/et6801/Listings/et6801_test_silicon.map`

## 未完成与限制

- 尚未擦写真实PFLASH、执行真实DMA搬运或证明DMA中断进入；编译和单测PASS不能替代HIL PASS。
- 首个Case只覆盖DMA0 Channel 0、8-bit内存到内存搬运和`TRANSFER_DONE`独立向量。
- 真实硬件测试必须在单独人工门禁下执行，并保存Flash、HELLO和pytest日志。
