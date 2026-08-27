# AES Contract/Codec 单元测试。
#
# 职责：固定 AES Service 的 enum numeric、feature bits、结构体尺寸、Golden KAT 和边界拒绝。
# 边界：不构造 TargetClient、不访问硬件、不执行 Formal HIL Case。
# 依赖：AES Driver package、Cryptodome adapter 和 pytest。

from __future__ import annotations

import struct

import pytest

from et_test_platform.core.errors import ProtocolError
from et_test_platform.drivers.aes import (
    AES_CAPABILITIES_SIZE,
    AES_CONFIGURE_SIZE,
    AES_DATA_LENGTH_SIZE,
    AES_IRQ_SNAPSHOT_SIZE,
    AES_IRQ_TRANSFER_STATUS_SIZE,
    AES_KEY_SET_SIZE,
    AES_PROCESS_RESULT_SIZE,
    AES_PROCESS_SIZE,
    AES_STATUS_SIZE,
    AES_TIMED_RESULT_SIZE,
    AesCommand,
    AesConfig,
    AesDirection,
    AesDmaTransferMode,
    AesEndian,
    AesIrqEvent,
    AesKeySize,
    AesMode,
    AesPadding,
)
from et_test_platform.drivers.aes.codec import (
    CAPABILITIES,
    CONFIGURE,
    IRQ_SNAPSHOT,
    IRQ_TRANSFER_STATUS,
    KEY_SET,
    PROCESS,
    PROCESS_RESULT,
    STATUS,
    TIMED_PROCESS,
    TIMED_RESULT,
    decode_capabilities,
    decode_config,
    decode_process_result,
    encode_config,
    encode_key,
)
from et_test_platform.drivers.aes.models import AesFeature
from et_test_platform.test_cases.aes.aes_reference import aes_golden, nist_vectors


# 固定 Service Command ID，防止固件和 PC 在顺序或数值上漂移。
def test_aes_command_numeric_contract() -> None:

    # 断言：命令从 CAPABILITIES_GET=0x0001 连续到 BLOCK_WRITE_DISABLE_DIRECT=0x001D。
    assert [int(command) for command in AesCommand] == list(range(0x0001, 0x001E))


# 固定 AES enum numeric 和所有 feature bit，防止 Enum 自动重排或 TEST_EXTENSIONS 漂移。
def test_aes_enum_and_feature_bit_contract() -> None:

    # 断言：所有公开 enum 使用固件冻结编码。
    assert [int(item) for item in AesDirection] == [0, 1]
    assert [int(item) for item in AesKeySize] == [0, 1]
    assert [int(item) for item in AesMode] == [0, 1, 2]
    assert [int(item) for item in AesPadding] == [0, 1, 2]
    assert [int(item) for item in AesEndian] == [0, 1]
    assert [int(item) for item in AesDmaTransferMode] == [0, 1]
    assert [int(item) for item in AesIrqEvent if item.name != "ALL"] == [1, 2, 4, 8, 16, 32, 64]
    assert int(AesIrqEvent.ALL) == 0x7F
    assert int(AesFeature.TEST_EXTENSIONS) == 1 << 18
    assert int(AesFeature.TEST_EXTENSIONS) != 1 << 9
    assert int(AesFeature.TEST_EXTENSIONS) == max(int(item) for item in AesFeature)


# 固定每个 Request/Response struct 的 exact byte size 和 little-endian layout。
def test_aes_struct_size_contract() -> None:

    # 断言：Python struct size 必须等于 Firmware Wire 合同常量。
    assert CAPABILITIES.size == AES_CAPABILITIES_SIZE == 32
    assert CONFIGURE.size == AES_CONFIGURE_SIZE == 12
    assert KEY_SET.size == AES_KEY_SET_SIZE == 36
    assert struct.calcsize("<16s") == 16
    assert struct.calcsize("<Q") == AES_DATA_LENGTH_SIZE == 8
    assert PROCESS.size == AES_PROCESS_SIZE == 20
    assert STATUS.size == AES_STATUS_SIZE == 8
    assert PROCESS_RESULT.size == AES_PROCESS_RESULT_SIZE == 12
    assert IRQ_SNAPSHOT.size == AES_IRQ_SNAPSHOT_SIZE == 28
    assert IRQ_TRANSFER_STATUS.size == AES_IRQ_TRANSFER_STATUS_SIZE == 24
    assert TIMED_PROCESS.size == 20
    assert TIMED_RESULT.size == AES_TIMED_RESULT_SIZE == 16


# 固定 CONFIGURE、KEY_SET 和 PROCESS_RESULT 的字段偏移、reserved zero 和 canonical bool。
def test_aes_codec_field_layout_and_reserved_checks() -> None:

    # 准备：配置 BIG/CTR/REGISTER 和计数，验证逐字段 round-trip。
    config = AesConfig(
        AesDirection.DECRYPT,
        AesKeySize.AES256,
        AesMode.CTR,
        endian=AesEndian.BIG,
        dma_transfer_mode=AesDmaTransferMode.REGISTER,
        ctr_counter=0xFCFDFEFF,
    )
    encoded = encode_config(config)

    # 观察：CONFIGURE 保留字为零，枚举字段按冻结位置解包。
    assert encoded == struct.pack("<BBBBBB2xI", 1, 1, 2, 0, 1, 1, 0xFCFDFEFF)
    assert decode_config(encoded) == config
    assert encode_key(bytes(range(32)), AesKeySize.AES256) == KEY_SET.pack(1, bytes(range(32)))
    result = decode_process_result(struct.pack("<I4B4x", 16, 0, 0, 0, 1))
    assert result.produced_bytes == 16
    assert result.status.finish

    # 拒绝：reserved bytes 和非 canonical bool 不能静默接受。
    with pytest.raises(ProtocolError):
        decode_process_result(struct.pack("<I4B4x", 16, 0, 0, 0, 2))


# 固定 CAPABILITIES 8 个末尾字节的定义和 TEST_EXTENSIONS feature flags。
def test_aes_capabilities_tail_mapping() -> None:

    # 准备：尾字段依次放置 key/mode/padding/endian/dma/irq masks 和两个 bool。
    body = CAPABILITIES.pack(
        1,
        32,
        int(AesFeature.TEST_EXTENSIONS),
        16,
        36,
        4096,
        4112,
        0x03,
        0x07,
        0x07,
        0x03,
        0x03,
        0x7F,
        1,
        1,
    )
    capabilities = decode_capabilities(body)

    # 断言：每个字段都从其合同位置恢复，不能把 bool 混入 feature_flags。
    assert capabilities.features == AesFeature.TEST_EXTENSIONS
    assert capabilities.key_size_mask == 0x03
    assert capabilities.mode_mask == 0x07
    assert capabilities.padding_mask == 0x07
    assert capabilities.endian_mask == 0x03
    assert capabilities.dma_mode_mask == 0x03
    assert capabilities.irq_event_mask == AesIrqEvent.ALL
    assert capabilities.irq_transfer_supported is True
    assert capabilities.timed_process_supported is True


# 独立 Cryptodome adapter 必须通过完整 12-vector NIST matrix，尤其 CTR IV/counter 规则。
def test_aes_reference_nist_vectors() -> None:

    # 观察：每个向量都精确等于预置 expected，解密节点还原原始明文。
    vectors = nist_vectors()
    assert len(vectors) == 12
    for vector_id, key, payload, iv, config, expected in vectors:
        assert aes_golden(payload, key, iv, config) == expected, vector_id
