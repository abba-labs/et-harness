# Manual Diagnostic Tools

该目录只保存独立手动诊断固件的辅助工具，不参与正式 pytest 自动化测试。

## 构建 ET6801 手动诊断固件

```powershell
powershell -ExecutionPolicy Bypass -File tools/manual_test/build_et6801_manual_firmware.ps1
```

输出镜像：

```text
firmware/build/et6801/Objects/FPGA_MANUAL_FLASH/et6801_manual_uart_crc_fpga_flash.axf
```

## 运行和捕获串口日志

手动诊断固件与正式固件一样烧录到 PFLASH，并从 Flash 启动。固件启动后等待捕获工具发送单字节触发符，因此不会丢失首行日志。

完成 FPGA bit 配置、BootROM 加载和 PFLASH 烧录后，执行：

```powershell
python tools/manual_test/capture_serial_log.py --port COM12 --baudrate 115200 --timeout-s 30
```

捕获工具沿用正式自动化平台的串口配置：打开端口前将 DTR、RTS 设为低电平，再发送启动触发符 `R`。

默认日志和 manifest 写入
`artifacts/runs/<timestamp>_manual_et6801_diagnostics/manual/diagnostics.log`。
结束标记未出现时工具返回非零状态，不能把超时误判为测试完成。
