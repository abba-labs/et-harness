# bench_topologies

测试台架中的DUT、Peer、XC7Z045、通信端口、仪器和逻辑通道绑定。

端口、地址和预期固件Build ID通过环境变量注入，不写死在Python代码或Test Case中。

`dma_peripheral_pair`描述DMA外设传输所需的两个逻辑角色：

- `dma_port_instance`：连接DMA请求的外设实例；
- `peer_port_instance`：由CPU轮询驱动、负责发送或接收校验数据的对端实例；
- `provider`：角色实现类型。当前为`uart_loopback`，后续可增加其他外设实现，DMA Case不变；
- `source_interface`/`destination_interface`：DMA控制器的请求接口编号。

当前UART实现要求两路UART交叉连接：DMA端TX接Peer端RX，DMA端RX接Peer端TX，且共地。UART0为PC控制通道，不得填入这两个角色。
