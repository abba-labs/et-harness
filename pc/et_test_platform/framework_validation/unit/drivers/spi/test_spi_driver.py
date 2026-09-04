# SPI软件合同回归。
# 职责：逐命令核对字节布局、无副作用重试资格和返回校验。
# 边界：不运行硬件，不计入17项Formal Case覆盖。
# 依赖：真实SPI Driver/Codec与严格Target桩。

from dataclasses import replace
from pathlib import Path
from struct import pack

import pytest
from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError, RequestTimeout
from et_test_platform.drivers.spi import (
    SpiCaptureError,
    SpiClockMode,
    SpiConfig,
    SpiCsPolicy,
    SpiDriver,
    SpiFormat,
    SpiIrq,
    SpiRole,
    SpiTransferMode,
    codec,
    contract,
)

CONFIG = SpiConfig(
    SpiRole.CONTROLLER,
    SpiFormat.MOTOROLA,
    SpiClockMode.MODE2,
    SpiTransferMode.TX_RX,
    SpiCsPolicy.AUTO,
    8,
    17,
    4,
    True,
    False,
    0,
    8,
    False,
    False,
    False,
)
# 独立固定向量，不调用待测Codec生成Expected。
CONFIG_WORDS = (1, 0, 2, 0, 0, 8, 17, 4, 1, 0, 0, 8, 0, 0, 0, 0)
SNAPSHOT_WORDS = (1, 1, 2, 3, 4, 5, 6, 16, 16, 16, 1, 0, 7, 8)
EVENT_WORDS = (16, 16, 16, 1, 0, 0, 1, 0)


# 测试 Feature：Case DMA配置保持单帧单访问、正确方向及固定外设地址。
# 测试方法：用非芯片地址和16-bit帧构造TX/RX，检查纯配置与打包的独立Expected。
# 通过条件：方向、增量、Interface及每帧一个32-bit槽均正确，不执行任何硬件I/O。
def test_spi_dma_case_data_contract():

    from et_test_platform.drivers.dma import DmaAddressMode, DmaTransferType, DmaWidth
    from et_test_platform.drivers.resource.models import ResourceRef
    from et_test_platform.test_cases.spi._support import dma_config, pack_frames, unpack_frames

    memory = ResourceRef(7, 16, 0x1000)
    frames = (0x1357, 0xFFFF, 0x1234, 0)
    encoded = b"\x57\x13\x00\x00\xff\xff\x00\x00\x34\x12\x00\x00\x00\x00\x00\x00"
    assert pack_frames(frames, 32) == encoded
    assert unpack_frames(encoded, 32) == frames

    # 两个方向分别检查，不把同一个配置对象反复改写后当成独立预期。
    for receive in (False, True):
        config = dma_config(3, 5, 0x4000, memory, 4, receive=receive, access_bits=32)
        assert config.source_width == config.destination_width == DmaWidth.BITS_32
        assert config.transfer_count == 4 and config.channel == 3
        assert config.source_interface == config.destination_interface == 5
        assert config.source_address == (0x4000 if receive else 0x1000)
        assert config.destination_address == (0x1000 if receive else 0x4000)
        assert config.transfer_type == (
            DmaTransferType.PERIPHERAL_TO_MEMORY
            if receive
            else DmaTransferType.MEMORY_TO_PERIPHERAL
        )
        assert config.source_address_mode == (
            DmaAddressMode.FIXED if receive else DmaAddressMode.INCREMENT
        )
        assert config.destination_address_mode == (
            DmaAddressMode.INCREMENT if receive else DmaAddressMode.FIXED
        )


# 测试 Feature：RX水位等待只读无副作用快照，不消费FIFO或错误状态。
# 测试方法：目标返回已经达到阈值的固定快照，严格检查只发送SNAPSHOT_GET。
# 通过条件：一次查询返回实际RX水位，目标不接受任何其他命令。
def test_spi_wait_rx_level_reads_only_snapshot():

    target = Target(10, result=SNAPSHOT_WORDS)
    actual = SpiDriver(target, 2).wait_rx_level(3, timeout_s=0.5)
    assert actual.rx_level == 3
    assert target.calls == 1


# 测试 Feature：DMA预装等待只读TX水位，不选择CS、不产生SPI数据。
# 测试方法：严格目标只接受快照，TX=2时等待2帧立即完成。
# 通过条件：一次读回达到水位，其他命令不被调用。
def test_spi_wait_tx_level_reads_only_snapshot():

    target = Target(10, result=SNAPSHOT_WORDS)
    assert SpiDriver(target, 2).wait_tx_level(2, timeout_s=0.5).tx_level == 2
    assert target.calls == 1


# 测试 Feature：等待Raw只读取无副作用快照，不打开中断或消费错误状态。
# 测试方法：返回RX_FULL原始位，检查请求类型及一次完成；零Source在I/O前拒绝。
# 通过条件：保留原始快照，非法Source不产生新请求。
def test_spi_wait_irq_raw_is_observation_only():

    target = Target(10, result=SNAPSHOT_WORDS)
    driver = SpiDriver(target, 2)
    assert driver.wait_irq_raw(SpiIrq.RX_FULL, timeout_s=0.5).irq_raw == SpiIrq.RX_FULL
    with pytest.raises(ValueError, match="nonzero"):
        driver.wait_irq_raw(SpiIrq(0), timeout_s=0.5)
    assert target.calls == 1


# 测试 Feature：RX水位未达到时按总Deadline退出并保留最后硬件快照。
# 测试方法：固定返回RX=3，等待至少4帧，不追加复位或数据读取。
# 通过条件：抛RequestTimeout且消息含最后RX值，不扩展超时预算。
def test_spi_wait_rx_level_timeout_keeps_snapshot():

    target = Target(10, result=SNAPSHOT_WORDS)
    with pytest.raises(RequestTimeout, match="rx_level=3"):
        SpiDriver(target, 2).wait_rx_level(4, timeout_s=0.005)


# 只接受指定命令；错误请求不能在Fake里被自动补齐或放宽。
class Target:
    def __init__(self, command, arguments=(), result=()):
        self.command = command
        self.arguments = arguments
        self.result = result
        self.calls = 0

    def request(self, service_id, command_id, *, instance_id, body, timeout_s, retry_safe):
        assert (service_id, command_id, instance_id) == (0x010B, self.command, 2)
        assert body == b"\x02" + pack("<" + "I" * len(self.arguments), *self.arguments)
        assert retry_safe is (self.command in (0, 2, 10, 17, 22, 24))
        assert timeout_s is None or 0 < timeout_s <= 0.5
        self.calls += 1
        response = pack("<" + "I" * len(self.result), *self.result)
        return ServiceMessage(service_id, command_id, instance_id, body=response), object()


# 测试 Feature：25条SPI原子命令与公共Wire契约完全一致。
# 测试方法：独立给定请求和响应向量，调用真实Driver，检查命令、实例、长度和重试资格。
# 通过条件：每次只发一条目标命令；读回不能被请求缓存替代。
@pytest.mark.parametrize(
    "command,method,args,request_words,response",
    [
        (0, "limits_get", (), (), (4, 16, 16, 2, 65534, 65536, 255)),
        (1, "configure", (CONFIG,), CONFIG_WORDS, ()),
        (2, "config_get", (), (), CONFIG_WORDS),
        (3, "enable_set", (True,), (1,), ()),
        (4, "fifo_reset", (), (), ()),
        (5, "divider_set", (4,), (4,), ()),
        (6, "frame_count_set", (65536,), (65536,), ()),
        (7, "cs_set", (False,), (0,), ()),
        (8, "loopback_set", (True,), (1,), ()),
        (9, "fifo_thresholds_set", (2, 3, 4), (2, 3, 4), ()),
        (10, "snapshot_get", (), (), SNAPSHOT_WORDS),
        (11, "error_status_read", (), (), (0x61, 0x61)),
        (12, "try_write_frame", (0x1234,), (0x1234,), (1,)),
        (13, "try_read_frame", (), (), (1, 0x5678)),
        (14, "test_fifo_write_once", (0x1234,), (0x1234,), ()),
        (15, "test_fifo_read_once", (), (), (0x5678,)),
        (16, "dma_configure", (True, False, 7, 8), (1, 0, 7, 8), ()),
        (17, "dma_endpoint_get", (), (), (0x12345678, 1)),
        (18, "irq_mask_set", (SpiIrq.RX_FULL, False), (16, 0), ()),
        (19, "irq_clear", (SpiIrq.RX_OVERFLOW,), (8,), ()),
        (20, "irq_capture_start", (SpiIrq.RX_FULL,), (16,), ()),
        (21, "irq_capture_stop", (), (), ()),
        (22, "irq_event_get", (), (), EVENT_WORDS),
        (23, "irq_event_reset", (), (), ()),
        (24, "fifo_limits_get", (), (), (15, 7, 31, 15, 7)),
    ],
)
def test_spi_all_atomic_wire_commands(command, method, args, request_words, response):
    target = Target(command, request_words, response)
    value = getattr(SpiDriver(target, 2), method)(*args, timeout_s=0.5)
    assert target.calls == 1
    if command == 2:
        assert value == CONFIG
    elif command == 10:
        assert value.rx_level == 3 and value.start_threshold == 6
    elif command == 11:
        assert value.raw == 0x61 and int(value.flags) == 0x61
    elif command == 13:
        assert value == 0x5678
    elif command == 17:
        assert value == 0x112345678
    elif command == 22:
        assert value.event_count == 1 and value.generation == 1
    elif command == 24:
        assert (value.tx_irq_max, value.rx_irq_max, value.tx_start_max) == (15, 7, 31)
        assert (value.dma_tx_max, value.dma_rx_max) == (15, 7)


# 测试 Feature：C/Python的命令编号、字段数及配置向量一致。
# 测试方法：读取真实固件头，逐项核对已发布编号，另用独立固定字节验证配置。
# 通过条件：25项无偏移，保留字填零，读取不会改变配置语义。
def test_spi_firmware_ids_and_config_vector():
    root = Path(__file__).resolve().parents[6]
    header = (root / "firmware/services/include/et_spi_service.h").read_text(encoding="utf-8")
    for command in contract.SpiCommand:
        assert f"ET_SPI_COMMAND_{command.name} = {int(command)}u" in header
    assert codec.config_words(CONFIG) == CONFIG_WORDS
    encoded = codec.encode_request(contract.SpiCommand.CONFIGURE, 2, CONFIG_WORDS)
    assert encoded == b"\x02" + pack("<16I", *CONFIG_WORDS)
    assert codec.decode_config(CONFIG_WORDS) == CONFIG


# 测试 Feature：所有命令拒绝截断和尾随数据。
# 测试方法：分别构造错误长度的请求参数和成功响应。
# 通过条件：在边界抛出明确错误，不填零、不忽略尾部。
@pytest.mark.parametrize("command", list(contract.SpiCommand))
def test_spi_exact_lengths(command):
    count = contract.RESPONSE_WORDS[command]
    with pytest.raises(ProtocolError):
        codec.decode_response(command, bytes(count * 4 + 1))
    if count:
        with pytest.raises(ProtocolError):
            codec.decode_response(command, bytes(count * 4 - 1))
    with pytest.raises(ValueError):
        codec.encode_request(command, 2, (0,) * (contract.REQUEST_WORDS[command] + 1))


# 测试 Feature：非法枚举、Boolean和保留字段在本地失败关闭。
# 测试方法：构造不能映射的配置和读回，检查Target未被调用。
# 通过条件：写入ValueError、非法响应ProtocolError，不将任意整数当Boolean。
@pytest.mark.parametrize(
    "field,value", [("role", 2), ("loopback", 2), ("frame_count", -1), ("divider", True)]
)
def test_spi_invalid_configuration_no_io(field, value):
    target = Target(1)
    with pytest.raises(ValueError):
        SpiDriver(target, 2).configure(replace(CONFIG, **{field: value}))
    assert target.calls == 0


# 测试 Feature：空FIFO不等待，合法零值数据不被误认为空。
# 测试方法：分别提供空读、零值帧和满FIFO响应，调用直接动作。
# 通过条件：空读None、零值帧0、满FIFO返回0且只有一次尝试。
def test_spi_nonblocking_fifo_results():
    assert SpiDriver(Target(13, result=(0, 0)), 2).try_read_frame() is None
    assert SpiDriver(Target(13, result=(1, 0)), 2).try_read_frame() == 0
    target = Target(12, (0x1234,), (0,))
    assert SpiDriver(target, 2).write_frames([0x1234, 0x5678], timeout_s=0.5) == 0
    assert target.calls == 1
    with pytest.raises(ProtocolError):
        SpiDriver(Target(13, result=(0, 99)), 2).try_read_frame()


# 测试 Feature：IRQ捕获故障与等待超时不被掩盖。
# 测试方法：注入带故障快照及持续零事件，使用极短但有效的总Deadline。
# 通过条件：故障保留完整event；超时明确包含最后快照。
def test_spi_irq_fault_and_deadline():
    target = Target(22, result=(16, 16, 16, 1, 0, 0, 1, 1))
    with pytest.raises(SpiCaptureError) as error:
        SpiDriver(target, 2).irq_wait(timeout_s=0.5)
    assert error.value.event.fault_flags == 1
    with pytest.raises(RequestTimeout, match="last="):
        SpiDriver(Target(22, result=(0, 0, 0, 0, 0, 0, 1, 0)), 2).irq_wait(timeout_s=0.01)


# 测试 Feature：未知IRQ/状态位、非法Boolean和保留字响应必须拒绝。
# 测试方法：逐类损坏唯一字段，检查响应边界抛错。
# 通过条件：无错误读回被转换成合法硬件事实。
def test_spi_invalid_decoded_values():
    with pytest.raises(ProtocolError):
        codec.decode_fifo_limits((15, 15, 256, 15, 15))
    with pytest.raises(ProtocolError):
        codec.decode_config((*CONFIG_WORDS[:-1], 1))
    with pytest.raises(ProtocolError):
        codec.decode_snapshot((2, *SNAPSHOT_WORDS[1:]))
    with pytest.raises(ProtocolError):
        codec.decode_event((64, *EVENT_WORDS[1:]))
    with pytest.raises(ProtocolError):
        codec.decode_error((0, 128))
