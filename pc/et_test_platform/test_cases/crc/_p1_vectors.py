# CRC P1 的不可变输入数据；无设备调用、无测试流程、无通过判定。
from __future__ import annotations

from dataclasses import dataclass, replace

from ...drivers.crc import CrcConfig, CrcMode, CrcXorOut
from ._support import calculate_crc_reference, make_crc_pattern

BASE_PAYLOAD = bytes(range(1, 33))
CRC32_SWAP = CrcConfig(CrcMode.CRC32, 0x04C11DB7, 0xFFFFFFFF, byte_swap=True)
CRC8_IRQ = CrcConfig(CrcMode.CRC8, 0x07, 0xFF)
CHECK_CONFIG = CrcConfig(
    CrcMode.CRC32, 0x1EDC6F41, 0xFFFFFFFF, ref_in=True, ref_out=True,
    byte_swap=True, result_check=True, xor_out=CrcXorOut.ALL_ONE,
)


@dataclass(frozen=True, slots=True)
class CrcP1Vector:
    """Only original inputs and independent software expectations, never hardware facts."""
    config: CrcConfig
    payload: bytes
    second_payload: bytes = b""

    @property
    def expected(self) -> int:
        return calculate_crc_reference(self.config, self.payload)

    @property
    def second_expected(self) -> int:
        return calculate_crc_reference(self.config, self.second_payload)


def _vector(config, payload=b"", second_payload=b""):
    return CrcP1Vector(config, payload, second_payload)


def p1_vector(case_id: str, **parameters) -> CrcP1Vector:
    """Build original data only; missing required inputs or unknown IDs fail."""
    if case_id == "crc_p1_001":
        return _vector(replace(CRC32_SWAP, polynomial=parameters["polynomial"]), BASE_PAYLOAD)
    if case_id == "crc_p1_002":
        return _vector(replace(CRC32_SWAP, initial_value=parameters["initial_value"]), BASE_PAYLOAD)
    if case_id == "crc_p1_003":
        mode = parameters["mode"]
        config = CrcConfig(
            mode, 0x1021 if mode is CrcMode.CRC16 else 0x04C11DB7,
            0xFFFF if mode is CrcMode.CRC16 else 0xFFFFFFFF,
            byte_swap=parameters["byte_swap"],
        )
        return _vector(config, bytes((0x11, 0x22, 0x43, 0x84, 0x15, 0xA6, 0x37, 0xC8)))
    if case_id == "crc_p1_004":
        return _vector(
            replace(CRC32_SWAP, polynomial=0x1EDC6F41, ref_in=parameters["ref_in"]),
            BASE_PAYLOAD,
        )
    if case_id == "crc_p1_005":
        config = CrcConfig(
            CrcMode.CRC16, 0x1021, 0xC6C6, ref_in=True,
            ref_out=parameters["ref_out"], byte_swap=True,
        )
        return _vector(config, BASE_PAYLOAD[:15])
    if case_id == "crc_p1_006":
        config = CrcConfig(
            CrcMode.CRC16, 0x3D65, 0, ref_in=True, ref_out=True,
            byte_swap=True, xor_out=parameters["xor_out"],
        )
        return _vector(config, bytes(range(1, 8)))
    if case_id == "crc_p1_007":
        mode, length = parameters["mode"], parameters["length_bytes"]
        config = CrcConfig(
            mode, 0x1021 if mode is CrcMode.CRC16 else 0x04C11DB7,
            0xFFFF if mode is CrcMode.CRC16 else 0xFFFFFFFF, byte_swap=True,
        )
        return _vector(config, make_crc_pattern(length, seed=0x70000000 + length))
    if case_id == "crc_p1_008":
        return _vector(
            replace(CRC32_SWAP, auto_length_reload=True),
            make_crc_pattern(64, seed=0xA1), make_crc_pattern(64, seed=0xA2),
        )
    if case_id in {"crc_p1_009", "crc_p1_010"}:
        return _vector(CHECK_CONFIG, bytes(range(1, 8)))
    if case_id == "crc_p1_012":
        return _vector(replace(CRC32_SWAP, fifo_threshold=1), bytes(range(1, 9)))
    if case_id in {"crc_p1_013", "crc_p1_014", "crc_p1_015"}:
        return _vector(CRC8_IRQ)
    if case_id == "crc_p1_016":
        return _vector(CRC32_SWAP)
    if case_id == "crc_p1_018":
        return _vector(replace(CRC8_IRQ, ref_in=True, ref_out=True), bytes(range(1, 8)))
    raise ValueError(f"No declared CRC P1 input: {case_id}")
