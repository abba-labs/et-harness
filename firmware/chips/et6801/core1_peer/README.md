# ET6801双核部署

本目录保存ET6801双核Smoke所需的Core1最小工程、调试选择文件和部署清单。

- `ET6801_CORE1_ITCM_PEER`：独立Core1 Peer目标，链接到Core1 ITCM/DTCM。
- `ET6801_FPGA_CORE1_SMOKE_ITCM`：主ET6801工程中的Core0 Launcher目标。
- `ET6801_CORE1_PFLASH1_PEER`：Silicon Core1目标，链接到PFLASH1 `0x08080000`。
- `ET6801_SILICON_CORE1_LAUNCHER_FLASH`：Silicon Core0 Launcher目标，链接到PFLASH0。
- Core0经AHB-AP[1]加载，Core1经AHB-AP[2]加载。
- Core0调用SDK `DUALCORE_startCore1(0)`；Core1通过`0x20440000`共享Mailbox返回身份、Ready和Heartbeat。
- FPGA Profile只临时写ITCM/DTCM，不擦写PFLASH，也不重新配置FPGA bit或BootROM。

生成工程：

```powershell
python tools/firmware/generate_keil_project.py --manifest firmware/chips/et6801/project.yaml
python tools/firmware/generate_keil_project.py --manifest firmware/chips/et6801/core1_peer/project.yaml
```

生成后的工程位于：

```text
firmware/build/et6801/ET6801_Automated_Test.uvprojx
firmware/build/et6801/core1_peer/ET6801_Core1_Peer.uvprojx
```

## 统一入口

双核构建和部署只使用一个脚本：

```text
tools/firmware/deploy_dualcore_firmware.ps1
```

平台公共Runner不保存芯片地址或AP信息。目标差异只存在于以下清单和Profile中：

```text
firmware/chips/et6801/core1_peer/deploy/et6801_fpga_itcm.json
firmware/chips/et6801/core1_peer/deploy/et6801_silicon_flash.json
tools/profiles/pipeline/et6801_fpga_dualcore.yaml
tools/profiles/pipeline/et6801_silicon_dualcore.yaml
```

正式运行仍从仓库根目录的`run_test.bat`进入，配置文件只选择对应Pipeline Profile。

FPGA真机执行顺序固定为：加载并运行Core0 Launcher、经AP2加载Core1 Peer、打开串口日志采集并发送启动触发字节。通过条件为Magic正确、Core Index等于2、Ready有效且Heartbeat递增。

Silicon Profile复用同一脚本，但使用PFLASH0/PFLASH1部署清单。首次实板确认Core1释放路径、双探针身份、PFLASH1算法和Option Word前，清单保持`deployment_enabled: false`，真实烧录必须失败关闭；构建和DryRun不受影响。
