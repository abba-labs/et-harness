# Target连接对象的轻量组合入口。
#
# 职责：把已经校验的Bench连接配置组合为公共TargetClient。
# 边界：不打开设备、不发送协议命令、不选择Case，也不隐藏跨IP执行流程。
# 依赖：仅依赖强类型Bench配置、TargetClient和对应的具体Transport。

from __future__ import annotations

from ..clients.target import TargetClient
from ..communication.transports.serial import SerialTransport
from ..profiles.bench import SerialTargetConfig


# 根据已校验的串口Bench配置创建TargetClient；只负责对象组合，不产生设备I/O。
def create_serial_target_client(config: SerialTargetConfig) -> TargetClient:

    transport = SerialTransport(
        port=config.port,
        baudrate=config.baudrate,
        bytesize=config.bytesize,
        parity=config.parity,
        stopbits=config.stopbits,
        dtr=config.dtr,
        rts=config.rts,
    )
    return TargetClient(
        transport,
        request_timeout_s=config.request_timeout_s,
    )
