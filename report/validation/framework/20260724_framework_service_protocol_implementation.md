# ET公共命令协议与Framework Service实现记录

时间：2026-07-24 23:30 CST

## 目标

按平台正式分层实现PC与固件公共通信能力，不复用旧的Case命令捷径，
不提前定义具体IP命令，并建立可重复执行的1000轮公共通信压力测试。

## 实现

- ET-Frame v1帧层保持不变。
- Payload统一为8字节Service Message公共头及可变body。
- 固件新增通用Service Router和Framework Service。
- PC新增通用Service Message、Framework Driver和正式pytest Case。
- 删除旧Command/Case固件分发器及旧PC FrameworkCommunicationDriver。
- UART ISR仍只负责收发字节，协议解析和命令执行位于主循环。
- 请求超时最多重试一次；重复请求由固件重放上次响应，不重复执行Service。

## 公共能力

Framework Service当前只包含：

- HELLO
- ECHO
- VERSION_GET
- SERVICE_LIST
- STATISTICS_GET
- RESET_REASON_GET

RESET_REASON_GET在ET6801尚无可靠Chip Driver支持时返回NOT_SUPPORTED，
不使用伪造值填充。

## 验证

时间：2026-07-24 23:30 CST

方法：

- 运行PC平台全量pytest。
- 对全部Python文件执行AST解析。
- 搜索旧Command/Case协议残留和绕层调用。
- 使用Fake Target完整执行正式1000轮混合载荷计划。

结果：

- pytest：39项PASS。
- Python AST：49个文件PASS。
- 旧协议残留：0项。
- 压测计划：1000轮。
- 每轮载荷：16、256、2048字节。
- 总事务：3000次。
- 往返载荷：4,640,000字节。
- 数据错误：0。
- ET6801_SILICON_FLASH：0 error、0 warning。
- ET6801_FPGA_ITCM：0 error、0 warning。
- SILICON证据：`artifacts/firmware_build/20260724_233215_SILICON`。
- FPGA证据：`artifacts/firmware_build/20260724_233244_FPGA`。

当时判断：

公共协议、PC分层和固件分层的离线实现及双目标编译已经闭环，可以进入
真实ET6801 FPGA原型压力测试。

## 未验证与风险

- 本记录中的1000轮结果来自离线完整执行，不是串口实板PASS。
- 实板测试前必须临时加载新FPGA ITCM固件；旧固件不支持新的Service Message协议。
- 实板操作包含J-Link RAM写入和CPU run-control，需单独人工确认。

## 关联文件

- `docs/design/et_frame_v1.md`
- `docs/design/firmware_layering.md`
- `Et_Automated_Testing_Platform_Code/firmware/framework/`
- `Et_Automated_Testing_Platform_Code/firmware/services/`
- `Et_Automated_Testing_Platform_Code/pc/et_test_platform/`
