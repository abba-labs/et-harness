# ET6801 Keil 实际构建报告

日期：2026-08-06  
分支：`review_code`  
状态：`BLOCKED`  
证据：GitHub Actions `Phase 6 Hardware Audit Once`，Run `31098500232`

## 1. 结论

本次已经实际检查 Keil 工程与 Windows 构建环境，但没有执行出任何 Keil 编译结果。

```text
Keil Project 检查          PASS
FPGA Target 识别           PASS
Silicon Target 识别        PASS
UV4/ARMCLANG/fromelf 探测   NOT_FOUND
FPGA Keil Build             NOT_EXECUTED
Silicon Keil Build          NOT_EXECUTED
AXF/HEX/BIN 新产物          NOT_GENERATED
```

因此，本报告不能把 FPGA 或 Silicon 构建写成 PASS。

## 2. 工程事实

工程文件：

```text
firmware/build/et6801/ET6801_Automated_Test.uvprojx
```

Windows Runner 解析到两个 Target：

| Target | 编译器声明 | 关键宏 | 预期输出 |
|---|---|---|---|
| `ET6801_FPGA_ITCM` | ARM Compiler 6.16 / ARMCLANG | `FPGA_VERSION`, `ET_TARGET_FPGA`, `ITCM_CODE` | `Objects/FPGA_ITCM/et6801_test_fpga` |
| `ET6801_SILICON_FLASH` | ARM Compiler 6.16 / ARMCLANG | `ET_TARGET_SILICON`, `FLASH_CODE` | `Objects/SILICON_FLASH/et6801_test_silicon` |

工程结构和两个目标均可被 XML 正常解析；这只能证明工程元数据存在，不能代替编译。

## 3. 实际执行环境

审计运行于 GitHub Hosted Windows Runner：

```text
OS      : Microsoft Windows Server 2025
Runner  : windows-2025-vs2026
```

实际工具探测结果：

```text
UV4.exe       NOT_FOUND
armclang.exe  NOT_FOUND
fromelf.exe   NOT_FOUND
JLinkExe.exe  NOT_FOUND
```

Runner 中发现的 `jlink.exe` 位于 Java JDK 目录，是 Java 模块链接工具，不是 SEGGER J-Link，不能用于 ET6801 下载或调试。

由于 `UV4.exe` 不存在，工作流中的“遍历所有 Keil Target 并实际构建”步骤按条件被跳过。没有调用编译器，也没有生成新的 AXF、HEX 或 BIN。

## 4. 阻断条件

完成真实构建至少需要：

1. 一台 Windows 构建机或 Self-hosted Runner；
2. Keil MDK-ARM/uVision；
3. ARM Compiler 6.16 或经项目验证兼容的版本；
4. 可用许可证；
5. CMSIS Pack 与工程依赖；
6. 对两个 Target 分别执行完整 Rebuild；
7. 保存 Build Log、Warning 数、AXF/HEX/BIN 路径与 Build ID。

建议命令形态：

```powershell
UV4.exe -b firmware/build/et6801/ET6801_Automated_Test.uvprojx `
  -t ET6801_FPGA_ITCM -j0 -o et6801_fpga_build.log

UV4.exe -b firmware/build/et6801/ET6801_Automated_Test.uvprojx `
  -t ET6801_SILICON_FLASH -j0 -o et6801_silicon_build.log
```

只有命令实际返回成功、日志无构建错误且产物存在，才能更新为 PASS。

## 5. 当前记录

| 项目 | 状态 | 说明 |
|---|---|---|
| 工程文件存在 | PASS | 已实际解析 XML |
| FPGA Target 配置存在 | PASS | 未编译 |
| Silicon Target 配置存在 | PASS | 未编译 |
| FPGA 编译 | NOT_EXECUTED | 缺少 Keil/ARMCLANG |
| Silicon 编译 | NOT_EXECUTED | 缺少 Keil/ARMCLANG |
| Build ID 匹配 | NOT_EXECUTED | 没有新固件产物 |
| Warning 审查 | NOT_EXECUTED | 没有编译日志 |

## 6. 完成判定

本报告保持 `BLOCKED`，直到两个 Target 均在真实 Keil 环境完成构建并补充以下证据：

- Keil 与 Compiler 版本；
- 完整构建命令；
- 每个 Target 的 Result 与 Warning；
- AXF、HEX、BIN 路径和哈希；
- 固件 Build ID；
- 与 PC Build ID 的匹配结果。
