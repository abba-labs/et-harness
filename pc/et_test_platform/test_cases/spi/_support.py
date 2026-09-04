# SPI Case只读依赖及纯数据辅助。
# 职责：保存选定实例、引脚和可编程范围，构造确定性配置及输入。
# 边界：不隐藏测试配置、激励、观测或断言；清理只返回直接动作。
# 依赖：SPI/GPIO/CRG公共Driver及连接配置。

from dataclasses import dataclass
from importlib import import_module

from ...core.errors import ConfigurationError
from ...drivers.crg import CrgDriver
from ...drivers.dma import DmaAddressMode, DmaConfig, DmaTransferType, DmaWidth
from ...drivers.gpio import GpioDriver, GpioFunction
from ...drivers.spi import (
    SpiClockMode,
    SpiConfig,
    SpiCsPolicy,
    SpiDriver,
    SpiFifoLimits,
    SpiFormat,
    SpiLimits,
    SpiRole,
    SpiTransferMode,
)
from ...profiles import chip_execution_mappings

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
    fifo_limits: SpiFifoLimits


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
        frame_bits=bits
        if bits is not None
        else max(limits.frame_bits_min, min(8, limits.frame_bits_max)),
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


# 按芯片加载已审核的DMA端点事实；缺少映射是开发缺口，不伪装成接线SKIP。
def dma_mapping(chip_id):

    name = f"{chip_execution_mappings.__package__}.{chip_id}.spi_routes"
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        if error.name in (name, name.rpartition(".")[0]):
            raise ConfigurationError("SPI DMA execution mapping is missing") from error
        raise


# 纯配置构造：一次DMA仅搬运一个方向；通道启动和跨IP执行顺序由Case明确编排。
def dma_config(channel, interface, endpoint, memory, count, *, receive, access_bits):

    width = {8: DmaWidth.BITS_8, 16: DmaWidth.BITS_16, 32: DmaWidth.BITS_32}[access_bits]
    return DmaConfig(
        channel=channel,
        source_address=endpoint if receive else memory.address,
        destination_address=memory.address if receive else endpoint,
        transfer_count=count,
        transfer_type=(
            DmaTransferType.PERIPHERAL_TO_MEMORY
            if receive
            else DmaTransferType.MEMORY_TO_PERIPHERAL
        ),
        source_width=width,
        destination_width=width,
        source_address_mode=DmaAddressMode.FIXED if receive else DmaAddressMode.INCREMENT,
        destination_address_mode=DmaAddressMode.INCREMENT if receive else DmaAddressMode.FIXED,
        source_interface=interface,
        destination_interface=interface,
    )


# 每个SPI帧占一个端点访问单元；不把多帧打包成一次DR访问。
def pack_frames(frames, access_bits):

    return b"".join(frame.to_bytes(access_bits // 8, "little") for frame in frames)


# 保留完整DMA读回值，由Case比较独立Expected，不用掩码丢掉异常高位。
def unpack_frames(data, access_bits):

    size = access_bits // 8
    return tuple(
        int.from_bytes(data[index : index + size], "little") for index in range(0, len(data), size)
    )
