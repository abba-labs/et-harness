# 公共框架与ET-Frame v1可靠性整改验证

时间：2026-07-25 19:15 CST

## 结论

本轮仅整改平台公共通信框架，不新增具体IP命令，不操作真实硬件。

整改后的固件端与PC端仍保持轻量分层，公共协议、Framework Service、
串口收发和压力测试结果模型之间的边界清晰。离线单元测试、固件C实现与
Python实现的一致性测试，以及ET6801 FPGA/SILICON双目标编译均已通过。

## 范围

- target：platform-common。
- lane：firmware、PC pytest、tooling和docs。
- hardware：未涉及。
- 芯片相关改动：仅删除ET6801 Board配置中不应写死的Session、Boot ID和
  Registry Hash宏；未修改ET6801寄存器、启动文件、System或Chip Driver。

## 主要整改

### 固件公共框架

- UART IDLE处理改为持续排空RX环形缓冲区，避免长帧因单次读取上限而被误判为残帧。
- Session ID由PC在HELLO请求中提出随机非零值，固件接受后绑定会话；
  不再使用板级静态Session ID。
- 错误响应保留Service返回的错误body，便于PC获得结构化失败上下文。
- 重复请求响应在首次发送前进入重放缓存；即使首次发送短写或PC超时，
  同一请求也只执行一次Service。
- TX短写支持从缓存响应的未发送位置继续发送；存在待发送响应时不读取下一请求。
- Service Router复制服务描述符，不依赖调用方局部变量生命周期。
- IRQ/DMA注册表明确并发约束，dispatch调用回调前先快照回调和上下文。
- Framework HELLO运行时计算服务注册表FNV-1a哈希，不再使用`empty`或板级硬编码。

### PC公共框架

- `TargetClient`严格校验响应Session，并完整保留固件错误body、Service、
  Command和Instance信息。
- `FrameworkDriver`在HELLO前生成随机非零Session，并核对固件接受的Session。
- bench profile明确期望的chip和可选firmware build；fixture在测试前通过
  HELLO校验目标身份，避免串口连接到错误目标后继续测试。
- 1000轮压力测试在首个失败时仍生成结构化JSON，记录失败轮次、载荷类型和原因。
- 修复源码绕层检查的扫描路径，并保证扫描集合非空，避免测试空跑。
- C原生协议测试程序与Python共享同一份golden vector，验证两端编码一致。

## 验证结果

### 公共框架单元测试

- 命令：
  `.venv\Scripts\python.exe -m pytest -q Et_Automated_Testing_Platform_Code\pc\et_test_platform\framework_validation\unit`
- 结果：40项PASS。
- 覆盖重点：
  - ET-Frame和Service Message编解码；
  - Session HELLO绑定；
  - 2048字节载荷分块接收；
  - 错误body透传；
  - TX短写续传；
  - 重复请求只执行一次并重放相同响应；
  - C固件实现与Python golden vector一致；
  - 分层和禁止硬编码检查。
- 资源控制证据：
  `D:\lihuan\vibe_code\codex\artifacts\resource-control\tasks\20260725_191319_9359ac3c.jsonl`。

### ET6801 FPGA固件编译

- Target：`ET6801_FPGA_ITCM`。
- 结果：0 error、0 warning。
- 构建证据：`artifacts/firmware_build/20260725_191337_FPGA`。
- AXF SHA256：
  `B8B0BAC969B01642A8155BF1D61EC53D0DFA24029B77A6471CEEA37AE474CB3F`。

### ET6801 SILICON固件编译

- Target：`ET6801_SILICON_FLASH`。
- 结果：0 error、0 warning。
- 构建证据：`artifacts/firmware_build/20260725_191437_SILICON`。
- AXF SHA256：
  `63750F2AE60A42DD53E79B0CB3480401372BDD81546C07A08DCC5B0102F114BF`。

## 未验证与限制

- 本轮没有把整改后的固件重新加载到XC7VX980T，也没有重跑真实J28串口1000轮测试。
- 当前注册表哈希表达`service_id + instance_id`拓扑，不表达每个Service内部命令schema。
- 本轮只编译ET6801的FPGA与SILICON目标，尚未接入其他芯片。
- UART DMA传输仍未实现；当前公共通信使用UART中断和环形缓冲区。
- 真实硬件回归涉及J-Link RAM写入、CPU run-control和串口访问，必须另行通过人工门禁。

## 关联文件

- `docs/design/et_frame_v1.md`
- `docs/design/firmware_layering.md`
- `docs/design/pc_layered_architecture.md`
- `Et_Automated_Testing_Platform_Code/firmware/framework/`
- `Et_Automated_Testing_Platform_Code/firmware/services/`
- `Et_Automated_Testing_Platform_Code/pc/et_test_platform/`
