# Framework Validation 测试模块。
# 职责：验证 CRC PC Driver、Wire Codec、Golden 算法和生命周期合同。
# 边界：不访问真实硬件，不替代 CRC HIL。
# 依赖：仅依赖 pytest、测试替身和 CRC 被测模块。
from __future__ import annotations

import struct

import pytest

from et_test_platform.communication.protocols.et_message import ServiceMessage
from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.crc import (
    CAPABILITIES,
    CRC_SERVICE_ID,
    CrcCommand,
    CrcConfig,
    CrcDriver,
    CrcFeature,
    CrcInputAccessWidth,
    CrcIrqEvent,
    CrcMode,
    CrcXorOut,
)
from et_test_platform.test_cases.crc._support import calculate_crc_reference


class _Target:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int, bytes, bool]] = []

    def request(
        self,
        service_id: int,
        command_id: int,
        *,
        instance_id: int = 0,
        body: bytes = b"",
        retry_safe: bool = False,
        timeout_s: float | None = None,
    ):
        del timeout_s
        self.calls.append((service_id, command_id, instance_id, body, retry_safe))
        responses = {
            int(CrcCommand.CAPABILITIES_GET): CAPABILITIES.pack(
                1, 16, (1 << 22) - 1, 0x07, 0x07, 8, 1, 4096
            ),
            int(CrcCommand.CALCULATE): struct.pack("<II", 0x12345678, 0),
            int(CrcCommand.DATA_LENGTH_GET): struct.pack("<I", 0),
            int(CrcCommand.RESULT_GET): struct.pack("<I", 0x12345678),
            int(CrcCommand.FIFO_STATUS_GET): b"\x01\x00\x00\x00",
            int(CrcCommand.IRQ_SNAPSHOT_GET): struct.pack("<IIIII", 1, 0, 4, 1, 1),
            int(CrcCommand.TEST_CALCULATE_TIMED): struct.pack("<IIII", 0x12345678, 321, 16, 0),
            int(CrcCommand.TEST_INPUT_BURST_32): struct.pack(
                "<BBHIIB3s", 2, 1, 0, 0xFFFFFFFF, 0x89ABCDEF, 0, b"\x00" * 3
            ),
        }
        return (
            ServiceMessage(
                service_id=service_id,
                command_id=command_id,
                instance_id=instance_id,
                body=responses.get(command_id, b""),
            ),
            object(),
        )


# CRC Runtime Capability 必须严格解码所有已发布字段和 Feature 位。
def test_crc_driver_decodes_capabilities_and_uses_selected_instance() -> None:

    target = _Target()
    crc = CrcDriver(target, instance_id=3)  # type: ignore[arg-type]
    capabilities = crc.capabilities_get()

    assert capabilities.api_version == 1
    assert capabilities.features == CrcFeature((1 << 22) - 1)
    assert capabilities.modes == (CrcMode.CRC8, CrcMode.CRC16, CrcMode.CRC32)
    assert capabilities.irq_events == CrcIrqEvent.ALL
    assert capabilities.fifo_threshold_max == 8
    assert capabilities.bounded_synchronous_calculate
    assert capabilities.max_calculate_bytes == 4096
    assert target.calls == [(CRC_SERVICE_ID, int(CrcCommand.CAPABILITIES_GET), 3, b"", True)]


# CRC Driver 必须按冻结 Wire 顺序编码配置和全部原子命令。
def test_crc_driver_command_wire_layout() -> None:

    target = _Target()
    crc = CrcDriver(target, instance_id=2)  # type: ignore[arg-type]
    config = CrcConfig(
        mode=CrcMode.CRC32,
        polynomial=0x04C11DB7,
        initial_value=0xFFFFFFFF,
        ref_in=True,
        ref_out=True,
        byte_swap=True,
        auto_length_reload=True,
        result_check=True,
        xor_out=CrcXorOut.ALL_ONE,
        fifo_threshold=5,
    )

    crc.capabilities_get()
    crc.enable()
    crc.configure(config)
    calculation = crc.calculate(0x20001000, 16)
    crc.data_length_set(16)
    assert crc.remaining_input_count_get() == 0
    assert crc.result_get() == 0x12345678
    crc.check_value_set(0x12345678)
    assert crc.fifo_status_get().overflow
    crc.irq_enable(CrcIrqEvent.BUS_ERROR)
    crc.irq_disable(CrcIrqEvent.BUS_ERROR)
    crc.irq_mask(CrcIrqEvent.LENGTH_ERROR)
    crc.irq_unmask(CrcIrqEvent.LENGTH_ERROR)
    crc.irq_force(CrcIrqEvent.CHECK_ERROR)
    crc.irq_clear(CrcIrqEvent.ALL)
    snapshot = crc.irq_snapshot_get()
    crc.test_input_write(CrcInputAccessWidth.BITS_32, 0xAABBCCDD)
    burst = crc.test_input_burst_32((0x11223344, 0x55667788), checkpoint_count=1)
    timed = crc.calculate_timed(0x20001000, 16)
    crc.disable()

    assert calculation.result == 0x12345678
    assert calculation.remaining_input_count == 0
    assert snapshot.raw == CrcIrqEvent.BUS_ERROR
    assert snapshot.status == CrcIrqEvent.NONE
    assert snapshot.event_count == 4
    assert burst.checkpoint_result == 0xFFFFFFFF
    assert burst.final_result == 0x89ABCDEF
    assert not burst.overflow
    assert timed.result == 0x12345678
    assert timed.elapsed_cycles == 321
    assert timed.measured_bytes == 16
    assert target.calls[2][3] == struct.pack("<BBBBII", 32, 0x1F, 1, 5, 0x04C11DB7, 0xFFFFFFFF)
    assert target.calls[3][3] == struct.pack("<QI", 0x20001000, 16)
    assert target.calls[16][3] == struct.pack("<B3xI", 32, 0xAABBCCDD)
    assert target.calls[17][3] == struct.pack("<BBH9I", 2, 1, 0, 0x11223344, 0x55667788, *(0,) * 7)
    assert target.calls[18][3] == struct.pack("<QII", 0x20001000, 16, 0)
    assert all(call[0] == CRC_SERVICE_ID and call[2] == 2 for call in target.calls)


# CRC Driver 必须在硬件请求前拒绝无效配置、宽度、地址和 IRQ 位。
def test_crc_driver_rejects_invalid_semantics_before_io() -> None:

    target = _Target()
    crc = CrcDriver(target)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="CRC8 does not support byte swap"):
        crc.configure(CrcConfig(CrcMode.CRC8, 0x07, 0xFF, byte_swap=True))
    with pytest.raises(RuntimeError, match="enabled and configured"):
        crc.result_get()

    crc.enable()
    crc.configure(CrcConfig(CrcMode.CRC16, 0x1021, 0xFFFF, byte_swap=True))
    with pytest.raises(ValueError, match="2-byte aligned"):
        crc.calculate(0x20000001, 2)
    with pytest.raises(ValueError, match="published non-zero"):
        crc.irq_force(CrcIrqEvent.NONE)
    with pytest.raises(ValueError, match="16-bit input width"):
        crc.test_input_write(CrcInputAccessWidth.BITS_16, 0x10000)
    with pytest.raises(ValueError, match="requires CRC32"):
        crc.test_input_burst_32((1,), checkpoint_count=0)


# CRC Capability 解码必须拒绝未知位，不能静默声明未来语义已受支持。
def test_crc_capability_codec_rejects_unknown_feature_bits() -> None:

    target = _Target()
    original_request = target.request

    def invalid_request(*args, **kwargs):
        message, frame = original_request(*args, **kwargs)
        return (
            ServiceMessage(
                service_id=message.service_id,
                command_id=message.command_id,
                instance_id=message.instance_id,
                body=CAPABILITIES.pack(1, 16, 1 << 31, 0x07, 0x07, 8, 1, 4096),
            ),
            frame,
        )

    target.request = invalid_request  # type: ignore[method-assign]
    with pytest.raises(ProtocolError, match="unknown feature bits"):
        CrcDriver(target).capabilities_get()  # type: ignore[arg-type]


# 独立 Golden 必须锁定历史 CRC8、CRC16 和 CRC32 固定向量。
@pytest.mark.parametrize(
    ("config", "payload", "expected"),
    (
        (
            CrcConfig(CrcMode.CRC8, 0x07, 0xFF, ref_in=True, ref_out=True),
            bytes(range(1, 8)),
            0x5C,
        ),
        (
            CrcConfig(
                CrcMode.CRC16,
                0x3D65,
                0,
                ref_in=True,
                ref_out=True,
                byte_swap=True,
                xor_out=CrcXorOut.ALL_ONE,
            ),
            bytes(range(1, 8)),
            0xEFE6,
        ),
        (
            CrcConfig(
                CrcMode.CRC32,
                0xA833982B,
                0xFFFFFFFF,
                ref_in=True,
                ref_out=True,
                byte_swap=True,
                xor_out=CrcXorOut.ALL_ONE,
            ),
            bytes(range(1, 9)),
            0x9D23C4CA,
        ),
    ),
)
def test_crc_reference_matches_historical_vectors(
    config: CrcConfig,
    payload: bytes,
    expected: int,
) -> None:

    assert calculate_crc_reference(config, payload) == expected
