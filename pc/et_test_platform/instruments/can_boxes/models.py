# CAN/CAN FD盒子的稳定数据模型。
# 职责：表达总线配置、完整帧和设备接收时间戳。
# 边界：不包含厂商结构、DLL、DUT寄存器或Case结论。
# 依赖：Python标准库。

from dataclasses import dataclass

FD_LENGTHS = (*range(9), 12, 16, 20, 24, 32, 48, 64)
STANDARD_ID_MAX = 0x7FF
EXTENDED_ID_MAX = 0x1FFFFFFF


# 总线模式由Case决定；波特率单位为bit/s，终端电阻由连接配置决定。
@dataclass(frozen=True, slots=True)
class CanBusConfig:
    nominal_bitrate: int = 500_000
    data_bitrate: int = 2_000_000
    listen_only: bool = False
    non_iso: bool = False

    # 不将厂商可接受参数猜测成当前DUT能力；这里只检查公共参数范围。
    def __post_init__(self) -> None:
        for value in (self.nominal_bitrate, self.data_bitrate):
            if type(value) is not int or not 1 <= value <= 10_000_000:
                raise ValueError("CAN bitrate must be an integer in 1..10000000 bit/s")
        if type(self.listen_only) is not bool or type(self.non_iso) is not bool:
            raise ValueError("CAN mode flags must be bool")


# DLC保留协议值，远程帧不带数据；不自动补零改变测试载荷。
@dataclass(frozen=True, slots=True)
class CanFrame:
    identifier: int
    data: bytes = b""
    extended: bool = False
    fd: bool = False
    brs: bool = False
    remote: bool = False
    dlc: int | None = None

    # 在发送前拒绝不可能的帧组合，不让DLL静默截断或补齐数据。
    def __post_init__(self) -> None:
        if any(type(flag) is not bool for flag in (self.extended, self.fd, self.brs, self.remote)):
            raise ValueError("CAN frame flags must be bool")
        maximum = EXTENDED_ID_MAX if self.extended else STANDARD_ID_MAX
        if type(self.identifier) is not int or not 0 <= self.identifier <= maximum:
            raise ValueError("CAN identifier exceeds selected frame format")
        if not isinstance(self.data, bytes):
            raise TypeError("CAN data must be immutable bytes")
        if self.remote and (self.fd or self.data):
            raise ValueError("remote frames must be Classic CAN with no data")
        if self.brs and not self.fd:
            raise ValueError("BRS requires CAN FD")
        length = len(self.data)
        if (self.fd and length not in FD_LENGTHS) or (not self.fd and length > 8):
            raise ValueError("payload length cannot be represented without padding")
        dlc = FD_LENGTHS.index(length) if self.fd else length
        if self.dlc is not None:
            dlc = self.dlc
        if type(dlc) is not int or not 0 <= dlc <= 15:
            raise ValueError("DLC must be in 0..15")
        expected = FD_LENGTHS[dlc] if self.fd else min(dlc, 8)
        if not self.remote and length != expected:
            raise ValueError("DLC and payload length disagree")
        object.__setattr__(self, "dlc", dlc)


# timestamp_us来自盒子硬件；不能用主机接收时间冒充总线时序观测。
@dataclass(frozen=True, slots=True)
class CanReceivedFrame:
    frame: CanFrame
    timestamp_us: int
    error_state_indicator: bool = False
    is_echo: bool = False
