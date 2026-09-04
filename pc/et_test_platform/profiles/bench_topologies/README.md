# bench_topologies

台架配置遵循 R100、R200、R410、R500，不保存 Case 参数或测试结果。

## 统一硬件连接

et6801_hardware_connections.yaml 只保存：

- chip：与目标 Capability 核对，防止加载错芯片。
- active：唯一生效开关，只能是 fpga 或 silicon。
- fpga/silicon → IP → dut/ref → handle、gpio：实例与信号 GPIO 号。

固定读取位置是配置的 active 分区，再按 IP、角色取值。不合并、不回退到另一环境。
硅后区为空时，选择其中的 IP 会报错；先补实际配置，再切换 active。

默认按目标芯片从 profiles/bench_topologies/<chip>_hardware_connections.yaml 读取，
不依赖工作目录，不需要 Case 手写文件路径。IP-local Support 使用：

    from et_test_platform.profiles.hardware_connections import load_hardware_connections

    # 核对运行目标；expected_lane不覆盖active。
    connections = load_hardware_connections(
        capabilities=capabilities, expected_lane=target_lane
    )

    # 配置前检查本Case所用IP；不同Case之间允许复用GPIO。
    spi = connections.select("spi")["spi"]
    dut_handle = spi["dut"].handle
    dut_clk_gpio = spi["dut"].gpio["clk"]

多 IP Case 使用 select("spi", "uart")，一次检查本 Case 全部 GPIO。
返回值只含生效区的只读 handle/GPIO；没有另一环境的数据或路由目录。

加载器检查实例存在、GPIO 为非负整数、重复键和 Case 内 IO 冲突。
GPIO 支持哪种复用由芯片适配负责，这里不再维护 Pinmux 表，
也不宣称仅凭 GPIO 号就证明复用合法。所需信号是否齐全由各 IP Support/Case 校验。

本接口尚未接入正式 SPI Case；现有 UART/DMA 仍使用下述入口，本轮不切换它们。

## 既有运行 Bench

et6801_uart_template.yaml 继续提供目标控制串口和既有 UART/DMA 实例配对。
COM 口、工具路径等机器环境信息仍按 R500 注入，不搬入硬件连接文件。

dma_peripheral_pair 的 dma_port_instance/peer_port_instance 指定两路外设，
provider 指定外设类型，source_interface/destination_interface 指定 DMA 请求接口。
UART0 是 PC 控制通道，不作 UART 对测端点。
