# Firmware C可读性门禁回归。
# 职责：保护R330函数Doxygen、参数绑定、复杂函数导航、语义数字和受控目录范围。
# 边界：只使用临时C文本或只读源码发现，不修改正式Firmware源码。
# 依赖：tools.quality.check_firmware_c_quality。

from __future__ import annotations

from pathlib import Path

import pytest

from tools.quality.check_firmware_c_quality import (
    REPOSITORY_ROOT,
    _discover_all_sources,
    _is_complex,
    check_file,
    discover_sources,
    find_function_definitions,
)


def _write_source(tmp_path: Path, source: str, name: str = "sample.c") -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


# 可读性门禁覆盖平台自有五个目录，明确排除芯片SDK和生成工程。
def test_firmware_quality_source_scope_includes_boards_and_excludes_chip_build() -> None:
    relative_paths = tuple(
        path.relative_to(REPOSITORY_ROOT).as_posix() for path in _discover_all_sources()
    )

    assert relative_paths
    assert any(path.startswith("firmware/boards/") for path in relative_paths)
    assert all(not path.startswith("firmware/chips/") for path in relative_paths)
    assert all(not path.startswith("firmware/build/") for path in relative_paths)


# 显式路径不能把原始芯片SDK或生成工程纳入函数文档迁移。
def test_firmware_quality_explicit_paths_stay_inside_controlled_roots() -> None:
    with pytest.raises(ValueError, match="outside controlled Firmware quality roots"):
        discover_sources(
            requested=("firmware/chips/et6801/config/et_chip_wrap_config.h",),
        )


# 标准Doxygen必须绑定真实参数、返回语义和副作用说明。
def test_complete_doxygen_contract_is_accepted(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Decode one request into a stable value.
 *
 * @param[in] body Raw request bytes.
 * @param[out] value Decoded stable value.
 *
 * @note This helper only decodes memory and does not access hardware.
 *
 * @return 0 when decoding succeeds.
 * @return -1 when an input pointer is invalid.
 */
static int decode_value(const uint8_t *body, uint32_t *value)
{
    if ((body == NULL) || (value == NULL))
    {
        return -1;
    }

    *value = body[0];

    return 0;
}
""",
    )

    assert check_file(path) == []


# static inline定义在头文件中同样属于平台维护函数，不能绕过文档契约。
def test_static_inline_header_function_is_checked(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
static inline uint32_t encode_value(uint32_t value)
{
    return value;
}
""",
        name="sample.h",
    )

    violations = check_file(path)

    assert [item.code for item in violations] == ["ETFMT201"]


# 一句话C注释不是Doxygen函数契约。
def test_legacy_one_line_function_comment_is_rejected(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/* Decode one value. */
static uint32_t decode_value(uint32_t value)
{
    return value;
}
""",
    )

    violations = check_file(path)

    assert [item.code for item in violations] == ["ETFMT201"]


# Doxygen必须紧邻函数定义，平台Marker不能被跨越后误认为函数注释。
def test_doxygen_must_be_adjacent_to_function_definition(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Build one service descriptor.
 *
 * @param[in] value Input value.
 *
 * @note This helper does not access hardware.
 *
 * @return The input value.
 */
/* ET_PLATFORM_SERVICE_FACTORY_BEGIN */
static uint32_t build_descriptor(uint32_t value)
{
    return value;
}
""",
    )

    assert [item.code for item in check_file(path)] == ["ETFMT201"]


# @brief、@return和@note都必须提供真实内容，不能用占位字段让门禁变绿。
def test_placeholder_doxygen_fields_are_rejected(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief .
 *
 * @param[in] value Input value.
 *
 * @note TODO
 *
 * @return TBD
 */
static uint32_t normalize(uint32_t value)
{
    return value;
}
""",
    )

    codes = {item.code for item in check_file(path)}

    assert {"ETFMT202", "ETFMT206", "ETFMT207"} <= codes


# 参数必须逐一绑定，不能漏写、写错名字或重复声明。
def test_parameter_binding_is_exact(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Copy one value.
 *
 * @param[in] source Source value.
 * @param[in] source Duplicate source description.
 * @param[out] unknown Output value.
 *
 * @note This helper only copies caller-owned memory.
 *
 * @return 0 when the copy succeeds.
 */
static int copy_value(const uint32_t *source, uint32_t *destination)
{
    *destination = *source;

    return 0;
}
""",
    )

    codes = {item.code for item in check_file(path)}

    assert "ETFMT203" in codes
    assert "ETFMT204" in codes


# @param必须包含方向和实际描述，不能只写参数名。
def test_parameter_direction_and_description_are_required(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Copy one value.
 *
 * @param source
 * @param[out] destination Copied value.
 *
 * @note This helper only copies caller-owned memory.
 *
 * @return 0 when the copy succeeds.
 */
static int copy_value(const uint32_t *source, uint32_t *destination)
{
    *destination = *source;

    return 0;
}
""",
    )

    codes = {item.code for item in check_file(path)}

    assert "ETFMT205" in codes or "ETFMT208" in codes


# void函数不需要伪造@return，但仍必须说明@note。
def test_void_function_does_not_require_return_tag(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Clear one caller-owned flag.
 *
 * @param[out] value Flag to clear.
 *
 * @note This helper does not access hardware.
 */
static void clear_flag(uint32_t *value)
{
    *value = 0u;
}
""",
    )

    assert check_file(path) == []


# 函数指针参数也必须解析到真实参数名，避免callback签名成为盲区。
def test_function_pointer_parameter_name_is_supported(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Store one callback through a caller-owned slot.
 *
 * @param[in] callback Callback invoked by the caller later.
 *
 * @note This helper validates documentation parsing only and does not invoke the callback.
 */
static void store_callback(void (*callback)(uint32_t event))
{
    (void)callback;
}
""",
    )

    assert check_file(path) == []


# 函数发现必须忽略结构体初始化和普通函数声明，只返回真实定义。
def test_function_discovery_ignores_initializers_and_prototypes(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
typedef struct
{
    uint32_t value;
} sample_t;

static const sample_t sample = {1u};

int declared_only(uint32_t value);

/**
 * @brief Return one stable value.
 *
 * @param[in] value Input value.
 *
 * @note This helper has no side effects.
 *
 * @return The original value.
 */
static int defined_only(uint32_t value)
{
    return (int)value;
}
""",
    )

    functions = find_function_definitions(path)

    assert [function.name for function in functions] == ["defined_only"]


# 复杂函数必须提供至少两个Phase/Step导航，避免长实现失去阅读主线。
def test_complex_function_requires_flow_navigation(tmp_path: Path) -> None:
    statements = "\n".join("    value += TEST_INCREMENT;" for _ in range(72))
    path = _write_source(
        tmp_path,
        f"""
#define TEST_INCREMENT 2u

/**
 * @brief Accumulate a synthetic long sequence.
 *
 * @param[in,out] value Accumulator value.
 *
 * @note This synthetic helper exists only to exercise the readability threshold.
 *
 * @return The accumulated result.
 */
static uint32_t long_flow(uint32_t value)
{{
{statements}

    return value;
}}
""",
    )

    function = find_function_definitions(path)[0]
    assert _is_complex(function)

    codes = {item.code for item in check_file(path)}
    assert "ETFMT209" in codes


# 两个标准Phase/Step注释可以为复杂函数建立最小执行路线图。
def test_complex_function_accepts_phase_navigation(tmp_path: Path) -> None:
    first = "\n".join("    value += TEST_INCREMENT;" for _ in range(36))
    second = "\n".join("    value ^= TEST_MASK;" for _ in range(36))
    path = _write_source(
        tmp_path,
        f"""
#define TEST_INCREMENT 2u
#define TEST_MASK 3u

/**
 * @brief Transform a synthetic long sequence.
 *
 * @param[in,out] value Accumulator value.
 *
 * @note This synthetic helper exists only to exercise Phase navigation.
 *
 * @return The transformed result.
 */
static uint32_t long_flow(uint32_t value)
{{
    /* Phase 1: Accumulate the first deterministic sequence. */
{first}

    /* Phase 2: Fold the second deterministic sequence. */
{second}

    return value;
}}
""",
    )

    assert check_file(path) == []


# 语义数字检查只在strict模式启用，避免把未迁移历史文件混入新代码失败关闭范围。
def test_magic_numbers_are_checked_only_in_strict_mode(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Apply one synthetic hardware configuration.
 *
 * @param[in,out] value Synthetic configuration word.
 *
 * @note This helper exists only to exercise semantic-literal diagnostics.
 *
 * @return Updated value.
 */
static uint32_t configure_value(uint32_t value)
{
    value += 16u;
    value |= 0x20u;

    return value;
}
""",
    )

    assert check_file(path) == []
    codes = [item.code for item in check_file(path, strict_magic=True)]
    assert codes.count("ETFMT211") == 2


# strict-magic用于任务改动范围：除0/1、直接数组下标和位移宽度外，任何非平凡裸值都必须具名。
def test_strict_magic_rejects_small_unnamed_literals(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Apply one synthetic retry count.
 *
 * @param[in,out] value Synthetic counter.
 *
 * @note This helper exists only to exercise strict semantic-literal diagnostics.
 *
 * @return Updated value.
 */
static uint32_t retry_value(uint32_t value)
{
    value += 2u;

    return value;
}
""",
    )

    assert check_file(path) == []
    assert [item.code for item in check_file(path, strict_magic=True)] == ["ETFMT211"]


# 直接字节下标和位移宽度属于集中Codec的机械表达，不要求为每一个数字再定义第二套符号。
def test_magic_number_checker_allows_direct_indexes_and_shift_widths(tmp_path: Path) -> None:
    path = _write_source(
        tmp_path,
        """
/**
 * @brief Decode one synthetic little-endian field.
 *
 * @param[in] data Source bytes.
 *
 * @note The direct byte index and shift width are local codec mechanics only.
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
