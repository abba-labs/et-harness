# Firmware C格式工具回归。
# 职责：保护固定目录、Allman输出和case分支空行修复行为。
# 边界：只使用临时文本和工具纯函数，不改写正式Firmware源码。
# 依赖：tools.quality.check_firmware_c_format和固定clang-format测试依赖。

from __future__ import annotations

import subprocess
from pathlib import Path

from tools.quality.check_firmware_c_format import (
    FORMAT_CONFIG,
    REQUIRED_CLANG_FORMAT_VERSION,
    _case_block_violations,
    _clang_format_path,
    _discover_sources,
    _format_text,
    _normalize_case_blocks,
    _normalize_case_separators,
    _normalize_logical_separators,
)


# 受控文件只能来自四个公共Firmware目录，芯片SDK和生成工程必须排除。
def test_firmware_format_source_scope_is_fixed() -> None:

    relative_paths = tuple(path.as_posix() for path in _discover_sources())

    assert relative_paths
    assert all("/firmware/chips/" not in path for path in relative_paths)
    assert all("/firmware/build/" not in path for path in relative_paths)


# 显式路径只能缩小格式化范围，不能把芯片SDK或其他目录带入。
def test_firmware_format_explicit_paths_stay_inside_controlled_roots() -> None:

    selected = _discover_sources(("firmware/services/src/et_services.c",))

    assert len(selected) == 1
    assert selected[0].name == "et_services.c"

    try:
        _discover_sources(("firmware/chips/et6801/config/et_chip_wrap_config.h",))
    except ValueError as error:
        assert "outside controlled Firmware source roots" in str(error)
    else:
        raise AssertionError("chip config must not enter the common formatter scope")


# 独立case分支必须留空行，连续标签仍允许表达同一Fallthrough分支。
def test_case_separator_rule_distinguishes_branch_and_fallthrough() -> None:

    normalized = _normalize_case_separators(
        (
            "switch (value)",
            "{",
            "    case 1:",
            "    case 2:",
            "    {",
            "        break;",
            "    }",
            "    default:",
            "    {",
            "        break;",
            "    }",
            "}",
        )
    )

    assert normalized[7] == ""
    assert normalized[8] == "    default:"


# 分支说明注释必须与case保持相邻，空行放在整个注释块之前。
def test_case_separator_rule_keeps_branch_comment_attached() -> None:

    normalized = _normalize_case_separators(
        (
            "    }",
            "    /* next branch */",
            "",
            "    case 2:",
            "    {",
            "        break;",
            "    }",
        )
    )

    assert normalized[:4] == ["    }", "", "    /* next branch */", "    case 2:"]


# case可连续Fallthrough，但实际执行体必须由复合块限定变量作用域。
def test_case_block_rule_accepts_grouped_labels_and_rejects_unbraced_body(tmp_path) -> None:

    valid_source = tmp_path / "valid.c"
    valid_source.write_text(
        "switch (value)\n{\ncase 1:\ncase 2:\n{\nbreak;\n}\n}\n", encoding="utf-8"
    )
    invalid_source = tmp_path / "invalid.c"
    invalid_source.write_text(
        "switch (value)\n{\ncase 1:\nvalue = 2;\nbreak;\n}\n", encoding="utf-8"
    )

    assert _case_block_violations((valid_source,)) == []
    violations = _case_block_violations((invalid_source,))
    assert len(violations) == 1
    assert "ETFMT105" in violations[0]


# 自动修复只给实际执行体加一对复合块，并保留连续Fallthrough标签。
def test_case_block_fix_wraps_body_without_splitting_grouped_labels() -> None:

    normalized = _normalize_case_blocks(
        (
            "switch (value)",
            "{",
            "    case 1:",
            "    case 2:",
            "        value = 2;",
            "        break;",
            "",
            "    default:",
            "        break;",
            "}",
        )
    )

    assert normalized[3:8] == [
        "    case 2:",
        "    {",
        "        value = 2;",
        "        break;",
        "    }",
    ]
    assert normalized[-3:] == ["        break;", "    }", "}"]


# 调用、连续判断和return必须被稳定空行分隔，同类响应写入保持连续。
def test_logical_separator_rule_formats_service_flow() -> None:

    normalized = _normalize_logical_separators(
        (
            "    status = process();",
            "    if (status != OK)",
            "    {",
            "        return ERROR;",
            "    }",
            "    if (read_status() != OK)",
            "    {",
            "        return ERROR;",
            "    }",
            "    write_result();",
            "    *response_length = RESPONSE_SIZE;",
            "    (void)source_size;",
            "    return OK;",
        )
    )

    assert normalized == [
        "    status = process();",
        "",
        "    if (status != OK)",
        "    {",
        "        return ERROR;",
        "    }",
        "",
        "    if (read_status() != OK)",
        "    {",
        "        return ERROR;",
        "    }",
        "",
        "    write_result();",
        "    *response_length = RESPONSE_SIZE;",
        "    (void)source_size;",
        "",
        "    return OK;",
    ]


# 同一功能块中的连续字段写入不得按变量名或物理行数机械拆散。
def test_logical_separator_rule_keeps_homogeneous_writes_together() -> None:

    normalized = _normalize_logical_separators(
        (
            "    write_u32(&response[0], cycles);",
            "    write_u32(&response[4], produced);",
            "    write_u32(&response[8], measured);",
            "    *response_length = RESPONSE_SIZE;",
        )
    )

    assert normalized == [
        "    write_u32(&response[0], cycles);",
        "    write_u32(&response[4], produced);",
        "    write_u32(&response[8], measured);",
        "    *response_length = RESPONSE_SIZE;",
    ]


# 语句说明注释必须与被说明语句相邻，分隔空行放在注释块之前。
def test_logical_separator_rule_keeps_statement_comment_attached() -> None:

    normalized = _normalize_logical_separators(
        (
            "    status = process();",
            "    // Validate the target result.",
            "    if (status != OK)",
            "    {",
            "        return ERROR;",
            "    }",
        )
    )

    assert normalized[:4] == [
        "    status = process();",
        "",
        "    // Validate the target result.",
        "    if (status != OK)",
    ]


# 多行宏的每一行依赖反斜杠续行，格式工具不得在宏体内插入普通空行。
def test_logical_separator_rule_does_not_split_multiline_macro() -> None:

    normalized = _normalize_logical_separators(
        (
            "#define APPLY_ROUTE(value) \\",
            "    do \\",
            "    { \\",
            "        if ((value) != 0u) \\",
            "        { \\",
            "            return ERROR; \\",
            "        } \\",
            "    } while (0)",
        )
    )

    assert normalized == [
        "#define APPLY_ROUTE(value) \\",
        "    do \\",
        "    { \\",
        "        if ((value) != 0u) \\",
        "        { \\",
        "            return ERROR; \\",
        "        } \\",
        "    } while (0)",
    ]


# 固定clang-format必须输出Allman大括号、四空格缩进和独立case复合块。
def test_clang_format_configuration_produces_required_allman_style() -> None:

    executable = _clang_format_path()
    assert executable is not None

    version = subprocess.run(
        [str(executable), "--version"], check=True, capture_output=True, text=True
    ).stdout
    assert REQUIRED_CLANG_FORMAT_VERSION in version

    source = "int f(int x){if(x){return 1;}switch(x){case 2:{break;}default:{break;}}return 0;}"
    formatted = subprocess.run(
        [str(executable), f"--style=file:{FORMAT_CONFIG}", "--assume-filename=test.c"],
        input=source,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "int f(int x)\n{" in formatted
    assert "    if (x)\n    {" in formatted
    assert "        case 2:\n        {" in formatted


# 审查分类使用与--fix相同的内存流水线，不能只比较clang-format基础输出。
def test_review_diff_formatter_uses_complete_project_pipeline() -> None:

    executable = _clang_format_path()
    assert executable is not None

    source = "int f(int x){if(x){return 1;}return 0;}\n"
    formatted = _format_text(executable, source, Path("firmware/services/src/example.c"))

    assert "    if (x)\n    {" in formatted
    assert "    }\n\n    return 0;" in formatted
