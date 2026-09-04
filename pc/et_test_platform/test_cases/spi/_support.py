# SPI Case只读依赖及纯数据辅助。
# 职责：保存选定实例、引脚和可编程范围，构造确定性配置及输入。
# 边界：不隐藏测试配置、激励、观测或断言；清理只返回直接动作。
# 依赖：SPI/GPIO/CRG公共Driver及连接配置。

from dataclasses import dataclass

from ...drivers.crg import CrgDriver
from ...drivers.gpio import GpioDriver, GpioFunction
from ...drivers.spi import (
    SpiClockMode,
    SpiConfig,
    SpiCsPolicy,
    SpiDriver,
    SpiFormat,
    SpiLimits,
    SpiRole,
    SpiTransferMode,
)

TIMEOUT_S = 5.0
SIGNALS = {
    "clk": GpioFunction.SPI_CLK,
    "cs": GpioFunction.SPI_CS,
    "mosi": GpioFunction.SPI_MOSI,
    "miso": GpioFunction.SPI_MISO,
}


# 一个角色的类型化只读依赖；handle和引脚始终来自连接文件。
@dataclass(frozen=True, slots=True)
class SpiEndpoint:
    handle: str
    spi: SpiDriver
    limits: SpiLimits
    pins: tuple[tuple[int, GpioFunction], ...]


# 本Case选择的两端及支撑Driver；不在构造时配置设备。
@dataclass(frozen=True, slots=True)
class SpiSupport:
    dut: SpiEndpoint
    ref: SpiEndpoint
    gpio: GpioDriver
    crg: CrgDriver


# 构造公开的普通Motorola配置；特殊模式由Case通过replace明确变更。
def basic_config(
    endpoint,
    *,
    role=SpiRole.CONTROLLER,
    mode=SpiClockMode.MODE0,
    bits=None,
    loopback=False,
    divider=None,
):

    limits = endpoint.limits
    return SpiConfig(
        role=role,
        frame_format=SpiFormat.MOTOROLA,
        clock_mode=mode,
        transfer_mode=SpiTransferMode.TX_RX,
        cs_policy=SpiCsPolicy.AUTO,
        frame_bits=bits if bits is not None else min(8, limits.frame_bits_max),
        frame_count=1,
        divider=divider if divider is not None else limits.divider_max,
        target_output_enabled=True,
        loopback=loopback,
        rx_sample_delay=0,
        control_bits=1,
        sequential=False,
        transmit=True,
        handshake=False,
    )


# 独立Expected按文档PATTERN_A/B计算，不使用接收值反推期望。
def pattern(count, bits, *, inverse=False):

    mask = (1 << bits) - 1
    return tuple(
        ((0x1357 ^ (index * 0x31)) & mask) ^ (mask if inverse else 0) for index in range(count)
    )


# 人读摘要保留完整帧宽；原始帧数组另存Measurement，不转成8-bit字节。
def frame_text(frames):

    return " ".join(f"0x{frame:X}" for frame in frames)
