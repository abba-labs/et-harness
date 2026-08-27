# Framework Validation FMAC Wire合同测试。
#
# 职责：保证FMAC Firmware Service头文件与PC Contract/Codec保持相同编号和长度。
# 边界：只读取源码和常量，不执行固件、不访问硬件、不替代HIL。
# 依赖：仅依赖pytest、标准库及FMAC PC Contract/Codec。

from __future__ import annotations

import re
from pathlib import Path

from et_test_platform.drivers.fmac.codec import (
    CAPABILITIES,
    COEFFICIENTS,
    CONFIG,
    CONFIG_SNAPSHOT,
    COUNT,
    IRQ_SNAPSHOT,
    PROCESS,
    PROCESS_RESULT,
    RESOURCE,
    START,
    STATUS,
    TIMED_PROCESS_RESULT,
    UINT32,
)
from et_test_platform.drivers.fmac.contract import FMAC_SERVICE_ID, FmacCommand

PROJECT_ROOT = Path(__file__).parents[5]
SERVICE_HEADER = PROJECT_ROOT / "firmware" / "services" / "include" / "et_fmac_service.h"


# 读取FMAC Service头文件，作为Firmware侧Wire合同的唯一测试输入。
def _service_header() -> str:

    return SERVICE_HEADER.read_text(encoding="utf-8")


# 从简单整数宏中提取值；复杂表达式不属于本合同测试的输入。
def _macro_value(source: str, name: str) -> int:

    match = re.search(rf"^#define\s+{re.escape(name)}\s+(0x[0-9a-fA-F]+|[0-9]+)u?$", source, re.M)
    assert match is not None, f"missing simple FMAC Service macro: {name}"
    return int(match.group(1), 0)


# 测试Feature：FMAC Service ID和全部Command编号在PC/Firmware之间一致。
#
# 测试方法：读取Firmware Service头文件并逐项匹配PC公开枚举。
#
# 通过条件：Service ID和全部已发布Command编号精确一致。
def test_fmac_service_and_command_ids_match_pc_contract() -> None:

    source = _service_header()

    assert _macro_value(source, "ET_FMAC_SERVICE_ID") == FMAC_SERVICE_ID

    for command in FmacCommand:
        firmware_name = f"ET_FMAC_COMMAND_{command.name}"
        match = re.search(rf"\b{firmware_name}\s*=\s*(0x[0-9a-fA-F]+)u", source)
        assert match is not None, f"missing FMAC Firmware command: {firmware_name}"
        assert int(match.group(1), 0) == int(command)


# 测试Feature：FMAC固定请求和响应长度在PC Codec与Firmware之间一致。
#
# 测试方法：将PC Struct大小逐项对照Firmware公开Size宏。
#
# 通过条件：所有固定Wire Body长度精确一致，不存在隐式填充差异。
def test_fmac_fixed_wire_sizes_match_pc_codec() -> None:

    source = _service_header()
    expected = {
        "ET_FMAC_SERVICE_CAPABILITIES_SIZE": CAPABILITIES.size,
        "ET_FMAC_SERVICE_CONFIG_BODY_SIZE": CONFIG.size,
        "ET_FMAC_SERVICE_CONFIG_SNAPSHOT_SIZE": CONFIG_SNAPSHOT.size,
        "ET_FMAC_SERVICE_START_BODY_SIZE": START.size,
        "ET_FMAC_SERVICE_RESOURCE_BODY_SIZE": RESOURCE.size,
        "ET_FMAC_SERVICE_COEFFICIENT_BODY_SIZE": COEFFICIENTS.size,
        "ET_FMAC_SERVICE_PROCESS_BODY_SIZE": PROCESS.size,
        "ET_FMAC_SERVICE_COUNT_RESPONSE_SIZE": COUNT.size,
        "ET_FMAC_SERVICE_PROCESS_RESPONSE_SIZE": PROCESS_RESULT.size,
        "ET_FMAC_SERVICE_TIMED_PROCESS_RESPONSE_SIZE": TIMED_PROCESS_RESULT.size,
        "ET_FMAC_SERVICE_STATUS_RESPONSE_SIZE": STATUS.size,
        "ET_FMAC_SERVICE_SOURCE_BODY_SIZE": UINT32.size,
        "ET_FMAC_SERVICE_IRQ_SNAPSHOT_SIZE": IRQ_SNAPSHOT.size,
        "ET_FMAC_SERVICE_RAW_VALUE_SIZE": UINT32.size,
    }

    for name, size in expected.items():
        assert _macro_value(source, name) == size


# 测试Feature：FMAC PROCESS和IRQ响应字段偏移与PC解码顺序一致。
#
# 测试方法：检查Firmware公开字段偏移，并与连续32-bit PC Struct布局比较。
#
# 通过条件：PROCESS为0/4，IRQ六字段为0/4/8/12/16/20。
def test_fmac_response_offsets_match_pc_decode_order() -> None:

    source = _service_header()
    expected = {
        "ET_FMAC_SERVICE_PROCESS_INPUT_COUNT_OFFSET": 0,
        "ET_FMAC_SERVICE_PROCESS_OUTPUT_COUNT_OFFSET": 4,
        "ET_FMAC_SERVICE_TIMED_INPUT_COUNT_OFFSET": 0,
        "ET_FMAC_SERVICE_TIMED_OUTPUT_COUNT_OFFSET": 4,
        "ET_FMAC_SERVICE_TIMED_CYCLES_OFFSET": 8,
        "ET_FMAC_SERVICE_IRQ_RAW_OFFSET": 0,
        "ET_FMAC_SERVICE_IRQ_STATUS_OFFSET": 4,
        "ET_FMAC_SERVICE_IRQ_LATCHED_OFFSET": 8,
        "ET_FMAC_SERVICE_IRQ_EVENT_COUNT_OFFSET": 12,
        "ET_FMAC_SERVICE_IRQ_ENABLED_OFFSET": 16,
        "ET_FMAC_SERVICE_IRQ_MASKED_OFFSET": 20,
    }

    for name, offset in expected.items():
        assert _macro_value(source, name) == offset
