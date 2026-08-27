# Firmware语义数字门禁回归。
# 职责：锁定R330 strict-magic对业务裸值与Codec机械数字的确定性边界。
# 边界：仅检查临时C源码，不修改正式Firmware。
# 依赖：Firmware C质量检查器和pytest临时目录。

from __future__ import annotations

from pathlib import Path

from tools.quality.check_firmware_c_quality import check_file


def _write_source(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "sample.c"
    path.write_text(source, encoding="utf-8")
    return path


# 非Codec函数中的固定数组下标和位移宽度仍然是未具名语义数字，不能借Codec豁免绕过。
def test_non_codec_array_index_and_shift_are_rejected(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Process one synthetic protocol field.
 *
 * @param[in] data Input bytes.
 * @param[in,out] value Accumulator value.
 *
 * @note This helper represents business logic rather than a dedicated codec boundary.
 *
 * @return Updated value.
 */
static uint32_t process_request(const uint8_t *data, uint32_t value)
{
    value |= data[2];
    value <<= 8u;

    return value;
}
""",
    )

    codes = [item.code for item in check_file(path, strict_magic=True)]
    assert codes.count("ETFMT211") == 2


# 专用Codec helper允许直接字节下标和位移宽度，因为它们只表达局部机械编码位置。
def test_codec_helper_keeps_mechanical_index_and_shift_exemption(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Decode one synthetic little-endian field.
 *
 * @param[in] data Input bytes.
 *
 * @note Direct byte positions and shift widths are local codec mechanics only.
 *
 * @return Decoded value.
 */
static uint32_t decode_field(const uint8_t *data)
{
    return ((uint32_t)data[2] << 8u) | data[1];
}
""",
    )

    assert check_file(path, strict_magic=True) == []


# 业务逻辑中0/1保留为明显Boolean/单步值，不要求制造无意义常量。
def test_strict_magic_keeps_zero_and_one_literals(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Normalize one synthetic Boolean value.
 *
 * @param[in] value Candidate Boolean.
 *
 * @note Zero and one are intentionally obvious Boolean facts under R330.
 *
 * @return Canonical Boolean value.
 */
static uint32_t normalize_boolean(uint32_t value)
{
    return (value == 0u) ? 0u : 1u;
}
""",
    )

    assert check_file(path, strict_magic=True) == []
