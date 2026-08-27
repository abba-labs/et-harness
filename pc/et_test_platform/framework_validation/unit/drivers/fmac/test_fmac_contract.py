# FMAC Contract/Codec单元测试。
#
# 职责：固定FMAC命令编号、枚举、Wire尺寸和严格解码边界。
# 边界：不构造TargetClient、不访问硬件、不执行Formal Case。
# 依赖：仅依赖pytest、标准库及FMAC Contract/Codec/Model。

from __future__ import annotations

import struct

import pytest

from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.fmac import (
    FmacConfig,
    FmacFinalPolicy,
    FmacFunction,
    FmacIrqEvent,
    FmacOutputMode,
    FmacShift,
    FmacWatermark,
)
from et_test_platform.drivers.fmac.codec import (
    CAPABILITIES,
    CONFIG,
    CONFIG_SNAPSHOT,
    IRQ_SNAPSHOT,
    PROCESS,
    PROCESS_RESULT,
    RESOURCE,
    START,
    STATUS,
    TIMED_PROCESS_RESULT,
    decode_capabilities,
    decode_config_snapshot,
    decode_status,
    encode_config,
)
from et_test_platform.drivers.fmac.contract import (
    FMAC_CAPABILITIES_SIZE,
    FMAC_SERVICE_API_VERSION,
    FmacCommand,
)
from et_test_platform.drivers.fmac.models import FmacFeature


# 固定命令编号，防止PC和Firmware独立重排。
def test_fmac_command_numeric_contract() -> None:

    assert [int(command) for command in FmacCommand] == list(range(0x0001, 0x001B))


# 固定公共枚举和IRQ位，防止SDK枚举渗入Wire。
def test_fmac_enum_numeric_contract() -> None:

    assert [int(item) for item in FmacFunction] == [1, 2, 3, 4, 5]
    assert [int(item) for item in FmacWatermark] == [1, 2, 4, 8]
    assert [int(item) for item in FmacFinalPolicy] == [0, 1]
    assert [int(item) for item in FmacOutputMode] == [0, 1, 2]
    assert [int(item) for item in FmacShift] == list(range(16))
    assert int(FmacIrqEvent.ALL) == 0x07FF


# 固定全部FMAC Wire结构尺寸和Little Endian布局。
def test_fmac_wire_struct_sizes() -> None:

    assert CAPABILITIES.size == FMAC_CAPABILITIES_SIZE == 20
    assert CONFIG.size == 24
    assert CONFIG_SNAPSHOT.size == 16
    assert START.size == 4
    assert RESOURCE.size == 12
    assert PROCESS.size == 24
    assert PROCESS_RESULT.size == 8
    assert TIMED_PROCESS_RESULT.size == 12
    assert STATUS.size == 12
    assert IRQ_SNAPSHOT.size == 24


# 完整配置必须精确编码，并能从目标侧Snapshot恢复到强类型Model。
def test_fmac_config_round_trip() -> None:

    config = FmacConfig(
        x1_start=1,
        x1_size=8,
        x1_full_watermark=FmacWatermark.ITEMS_4,
        x2_start=32,
        x2_size=8,
        y_start=64,
        y_size=8,
        y_empty_watermark=FmacWatermark.ITEMS_2,
        final_policy=FmacFinalPolicy.WRAP,
        output_mode=FmacOutputMode.SAT16,
        internal_clip=True,
        float_input=True,
        float_output=True,
        output_shift=FmacShift.RIGHT2,
        output_offset=0x1234,
    )
    encoded = encode_config(config)
    snapshot = CONFIG_SNAPSHOT.pack(*CONFIG.unpack(encoded)[:14], 0x1234)

    assert encoded[-8:] == bytes(8)
    assert decode_config_snapshot(snapshot) == config


# Runtime Capability必须拒绝未知Feature和非法输出选项。
def test_fmac_capabilities_strict_decode() -> None:

    valid = CAPABILITIES.pack(
        FMAC_SERVICE_API_VERSION,
        FMAC_CAPABILITIES_SIZE,
        int(FmacFeature((1 << 13) - 1)),
        255,
        8,
        255,
        255,
        0x0F,
        0x07,
        16,
        int(FmacIrqEvent.ALL),
        0xFF,
        0xFF,
    )
    capabilities = decode_capabilities(valid)

    assert capabilities.fir_first_valid_output_index is None
    assert capabilities.iir_first_valid_output_index is None
    assert capabilities.watermarks == tuple(FmacWatermark)

    invalid = bytearray(valid)
    struct.pack_into("<I", invalid, 4, 1 << 31)
    with pytest.raises(ProtocolError):
        decode_capabilities(bytes(invalid))


# Status解码必须拒绝非Canonical Boolean，避免异常值被bool静默吞掉。
def test_fmac_status_rejects_noncanonical_boolean() -> None:

    with pytest.raises(ProtocolError):
        decode_status(STATUS.pack(2, 1, 1, 0, 0, 0, 0, 0, 0, 0))
