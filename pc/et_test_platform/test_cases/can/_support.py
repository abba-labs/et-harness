# CAN只读依赖和纯数据构造。
# 职责：保存明确选中的实例、引脚与限制，生成位时序和互不重叠的RAM布局。
# 边界：不执行配置、复位、收发、等待、断言或清理；流程必须保留在Case。
# 依赖：CAN/GPIO/CRG公共Model及芯片执行事实映射。

from dataclasses import dataclass
from importlib import import_module
from types import ModuleType

from ...core.errors import ConfigurationError
from ...drivers.can import CanDriver, CanPhaseTiming, CanRamLayout, CanRamLimits, CanTiming
from ...drivers.crg import CrgDriver
from ...drivers.gpio import GpioDriver, GpioFunction
from ...profiles import chip_execution_mappings

TIMEOUT_S = 5.0
SIGNALS = {"rx": GpioFunction.CAN_RX, "tx": GpioFunction.CAN_TX}
PATTERN_A = bytes.fromhex("31 42 53 64 75 86 97 A8")
PATTERN_B = bytes.fromhex("CE BD AC 9B 8A 79 68 57")
# 独立Expected表来自公共CAN标准DLC定义，不导入Driver的编码表当Oracle。
FD_LENGTHS = (0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64)


# 公共文档PATTERN_A/B：第i Byte=(0x31+17*i) mod256，B逐Byte取反。
# 只由输入长度生成Expected，不访问RX数据或硬件。
def pattern(length: int, *, inverse: bool = False) -> bytes:

    return bytes(
        (((0x31 + 17 * index) & 0xFF) ^ (0xFF if inverse else 0)) for index in range(length)
    )


# 只读入口返回的依赖集合，不在对象上封装“一键测试”或跨IP硬件操作。
@dataclass(frozen=True)
class CanSupport:
    handle: str
    can: CanDriver
    crg: CrgDriver
    gpio: GpioDriver
    pins: tuple[tuple[int, GpioFunction], ...]
    ram_limits: CanRamLimits
    timing_limits: CanTiming
    mapping: ModuleType
    clock_hz: int


# 按芯片加载已审核事实；缺失映射是开发错误，不能冒充外部环境SKIP。
def chip_mapping(chip_id: str) -> ModuleType:

    name = f"{chip_execution_mappings.__package__}.{chip_id}.can_routes"
    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        if error.name in (name, name.rpartition(".")[0]):
            raise ConfigurationError(f"CAN execution mapping is missing: {chip_id}") from error
        raise


# 纯计数换算：每bit固定20 TQ，80%采样；实际输入时钟由Mapping提供。
# 不读设备、不改时钟；无法精确表达时失败，不通过取整悄悄改变标称速率。
def phase_timing(clock_hz: int, bitrate: int, limits: CanPhaseTiming) -> CanPhaseTiming:

    quanta = 20
    if bitrate <= 0 or clock_hz % (bitrate * quanta):
        raise ConfigurationError("CAN requested bitrate is not exactly representable with 20 TQ")
    phase = CanPhaseTiming(clock_hz // (bitrate * quanta), 15, 4, 4)
    if any(
        not 0 < getattr(phase, field) <= getattr(limits, field)
        for field in ("prescaler", "segment1", "segment2", "sjw")
    ):
        raise ConfigurationError("CAN requested timing exceeds the controller limits")
    return phase


# 纯布局计算：一个标准Filter、一个TX槽和四项RX0；其他计数区域关闭。
# Dedicated RX按硬件公开上限保留，元素头大小取芯片映射，不把CPU地址写入Case。
def loopback_ram(support: CanSupport, *, payload_bytes: int = 8) -> CanRamLayout:

    mapping = support.mapping
    limits = support.ram_limits
    payload = payload_bytes
    rx_count = 4
    if limits.std_count < 1 or limits.tx_count < 1 or limits.rx_fifo_count < rx_count:
        raise ConfigurationError(
            "CAN internal loopback requires one filter/TX slot and four RX entries"
        )
    stride = mapping.CAN_RAM_HEADER_BYTES + payload
    tx_offset = mapping.CAN_STD_FILTER_BYTES
    rx_offset = tx_offset + stride
    buffer_offset = rx_offset + rx_count * stride
    if buffer_offset + limits.rx_buffer_count * stride > limits.ram_bytes:
        raise ConfigurationError("CAN loopback layout exceeds the message RAM aperture")
    return CanRamLayout(
        std_offset=0,
        std_count=1,
        ext_offset=tx_offset,
        ext_count=0,
        tx_offset=tx_offset,
        tx_buffer_count=1,
        tx_fifo_count=0,
        tx_queue=False,
        tx_payload_bytes=payload,
        event_offset=rx_offset,
        event_count=0,
        event_watermark=0,
        rx0_offset=rx_offset,
        rx0_count=rx_count,
        rx0_watermark=0,
        rx0_overwrite=False,
        rx1_offset=buffer_offset,
        rx1_count=0,
        rx1_watermark=0,
        rx1_overwrite=False,
        rx_buffer_offset=buffer_offset,
        rx_buffer_payload_bytes=payload,
        rx0_payload_bytes=payload,
        rx1_payload_bytes=payload,
    )


# 纯布局计算：一个标准Filter、一个TX槽和当前FIFO四项；另一FIFO关闭。
# 水位和覆盖模式由Case显式传入，不在Support选择测试Expected。
def fifo_loopback_ram(
    support: CanSupport, *, fifo: int, watermark: int, overwrite: bool
) -> CanRamLayout:

    if fifo not in (0, 1):
        raise ConfigurationError(f"CAN FIFO index must be 0 or 1: {fifo}")
    if watermark not in range(5):
        raise ConfigurationError(f"CAN FIFO watermark must be within depth four: {watermark}")

    mapping = support.mapping
    limits = support.ram_limits
    fifo_count = 4
    payload = 8
    if limits.std_count < 1 or limits.tx_count < 1 or limits.rx_fifo_count < fifo_count:
        raise ConfigurationError("CAN FIFO Case requires one filter/TX slot and four RX entries")

    stride = mapping.CAN_RAM_HEADER_BYTES + payload
    tx_offset = mapping.CAN_STD_FILTER_BYTES
    fifo_offset = tx_offset + stride
    buffer_offset = fifo_offset + fifo_count * stride
    if buffer_offset + limits.rx_buffer_count * stride > limits.ram_bytes:
        raise ConfigurationError("CAN FIFO layout exceeds the message RAM aperture")

    return CanRamLayout(
        std_offset=0,
        std_count=1,
        ext_offset=tx_offset,
        ext_count=0,
        tx_offset=tx_offset,
        tx_buffer_count=1,
        tx_fifo_count=0,
        tx_queue=False,
        tx_payload_bytes=payload,
        event_offset=fifo_offset,
        event_count=0,
        event_watermark=0,
        rx0_offset=fifo_offset,
        rx0_count=fifo_count if fifo == 0 else 0,
        rx0_watermark=watermark if fifo == 0 else 0,
        rx0_overwrite=overwrite if fifo == 0 else False,
        rx1_offset=fifo_offset,
        rx1_count=fifo_count if fifo == 1 else 0,
        rx1_watermark=watermark if fifo == 1 else 0,
        rx1_overwrite=overwrite if fifo == 1 else False,
        rx_buffer_offset=buffer_offset,
        rx_buffer_payload_bytes=payload,
        rx0_payload_bytes=payload,
        rx1_payload_bytes=payload,
    )


# 纯布局计算：四项标准Filter、一个TX槽、四项RX0观察区和完整Dedicated RX区。
# Dedicated RX数量没有配置寄存器，按目标发布的真实上限保留全部空间。
def dedicated_loopback_ram(support: CanSupport, *, filter_count: int) -> CanRamLayout:

    mapping = support.mapping
    limits = support.ram_limits
    payload = 8
    fifo_count = 4
    if not 0 < filter_count <= limits.std_count:
        raise ConfigurationError("CAN dedicated Buffer Case exceeds the standard filter capacity")
    if limits.tx_count < 1 or limits.rx_fifo_count < fifo_count:
        raise ConfigurationError("CAN dedicated Buffer Case requires one TX and four RX0 entries")

    stride = mapping.CAN_RAM_HEADER_BYTES + payload
    filter_bytes = filter_count * mapping.CAN_STD_FILTER_BYTES
    tx_offset = filter_bytes
    rx_offset = tx_offset + stride
    buffer_offset = rx_offset + fifo_count * stride
    if buffer_offset + limits.rx_buffer_count * stride > limits.ram_bytes:
        raise ConfigurationError("CAN dedicated Buffer layout exceeds the message RAM aperture")

    return CanRamLayout(
        std_offset=0,
        std_count=filter_count,
        ext_offset=tx_offset,
        ext_count=0,
        tx_offset=tx_offset,
        tx_buffer_count=1,
        tx_fifo_count=0,
        tx_queue=False,
        tx_payload_bytes=payload,
        event_offset=rx_offset,
        event_count=0,
        event_watermark=0,
        rx0_offset=rx_offset,
        rx0_count=fifo_count,
        rx0_watermark=0,
        rx0_overwrite=False,
        rx1_offset=buffer_offset,
        rx1_count=0,
        rx1_watermark=0,
        rx1_overwrite=False,
        rx_buffer_offset=buffer_offset,
        rx_buffer_payload_bytes=payload,
        rx0_payload_bytes=payload,
        rx1_payload_bytes=payload,
    )


# 选择Dedicated RX首尾和32-bit位图分组边界；较小实现仅保留实际存在的节点。
# 返回值只依赖目标公开容量，Case仍逐项验证真实数据和位图。
def rx_buffer_boundary_indices(limits: CanRamLimits) -> tuple[int, ...]:

    if limits.rx_buffer_count <= 0:
        raise ConfigurationError("CAN target exposes no dedicated RX Buffer")

    candidates = (0, 31, 32, 63, limits.rx_buffer_count - 1)
    return tuple(dict.fromkeys(index for index in candidates if index < limits.rx_buffer_count))
