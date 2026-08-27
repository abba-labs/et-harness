# Framework Validation测试模块。
#
# 职责：验证test_driver_contract 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[6]
DMA_HEADER = (
    PROJECT_ROOT / "firmware" / "chips" / "et6801" / "sdk" / "ET6x_Driver" / "Inc" / "et6x_ahbdma.h"
)
DMA_SOURCE = (
    PROJECT_ROOT / "firmware" / "chips" / "et6801" / "sdk" / "ET6x_Driver" / "Src" / "et6x_ahbdma.c"
)
DMA_WRAP_HEADER = PROJECT_ROOT / "firmware" / "wrap" / "include" / "et_dma_wrap.h"
DMA_WRAP_SOURCE = PROJECT_ROOT / "firmware" / "wrap" / "src" / "et_dma_wrap.c"
DMA_SERVICE_HEADER = PROJECT_ROOT / "firmware" / "services" / "include" / "et_dma_service.h"
DMA_SERVICE_SOURCE = PROJECT_ROOT / "firmware" / "services" / "src" / "et_dma_service.c"
CMSIS_HEADER = (
    PROJECT_ROOT
    / "firmware"
    / "chips"
    / "et6801"
    / "sdk"
    / "CMSIS"
    / "Device"
    / "Include"
    / "et6801.h"
)


# Return one C function body while keeping assertions implementation-agnostic.
def _function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{name}\s*\([^)]*\)\s*\{{", source)
    assert match is not None, f"missing function {name}"
    depth = 0
    for index in range(match.end() - 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : index + 1]
    raise AssertionError(f"unterminated function {name}")


# Catch per-channel loops or non-atomic writes in the mask API.
def test_dma_driver_exposes_atomic_mask_enable_contract() -> None:
    header = DMA_HEADER.read_text(encoding="utf-8")
    source = DMA_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"DRV_Status\s+AHBDMA_testEnableChannelsByMask\s*\(\s*"
        r"AHBDMA_Type\s*\*AHBDMAx\s*,\s*uint32_t\s+channelMask\s*\)",
        header,
    )
    body = _function_body(source, "AHBDMA_testEnableChannelsByMask")
    assert "channelMask == 0U" in body
    assert "AHBDMA0_CHENREG_CH_EN_Msk" in body
    assert "DRV_PARAM_ERR" in body
    assert body.count("WRITE_REG(AHBDMAx->CHENREG") == 1
    assert "AHBDMA0_CHENREG_CH_EN_WE_Pos" in body


# Priority ordering must poll one atomic CHENREG snapshot.
def test_dma_driver_exposes_enabled_channel_snapshot_contract() -> None:
    header = DMA_HEADER.read_text(encoding="utf-8")
    source = DMA_SOURCE.read_text(encoding="utf-8")

    assert re.search(
        r"uint32_t\s+AHBDMA_testGetEnabledChannels\s*\(\s*"
        r"AHBDMA_Type\s*\*AHBDMAx\s*\)",
        header,
    )
    body = _function_body(source, "AHBDMA_testGetEnabledChannels")
    assert "READ_REG(AHBDMAx->CHENREG)" in body
    assert "AHBDMA0_CHENREG_CH_EN_Msk" in body


def test_dma_deprecated_wait_commands_remain_reserved_and_not_supported() -> None:
    wrap_header = DMA_WRAP_HEADER.read_text(encoding="utf-8")
    wrap_source = DMA_WRAP_SOURCE.read_text(encoding="utf-8")
    service_header = DMA_SERVICE_HEADER.read_text(encoding="utf-8")
    service_source = DMA_SERVICE_SOURCE.read_text(encoding="utf-8")

    assert "et_dma_wrap_start_channel_and_wait" not in wrap_header
    assert "et_dma_wrap_start_channel_and_wait" not in wrap_source
    assert "et_dma_wrap_start_channels_wait_order" not in wrap_header
    assert "et_dma_wrap_start_channels_wait_order" not in wrap_source
    assert "ET_DMA_COMMAND_CHANNEL_START_WAIT = 0x0018u" in service_header
    assert "ET_DMA_COMMAND_CHANNELS_START_WAIT_ORDER = 0x001bu" in service_header
    timing_commands = _function_body(service_source, "handle_channel_timing_commands")
    assert re.search(
        r"case\s+ET_DMA_COMMAND_CHANNEL_START_WAIT:\s*"
        r"case\s+ET_DMA_COMMAND_CHANNELS_START_WAIT_ORDER:\s*"
        r"\{\s*return\s+ET_STATUS_NOT_SUPPORTED;",
        timing_commands,
    )


# Catch handshake register access leaking into the official Driver path.
def test_dma_test_driver_configures_handshake_mode_and_polarity() -> None:
    header = DMA_HEADER.read_text(encoding="utf-8")
    source = DMA_SOURCE.read_text(encoding="utf-8")

    official_struct = re.search(
        r"typedef struct __PACKED\s*\{(?P<body>.*?)\}\s*"
        r"AHBDMA_Ch_Init_TypeDef;",
        header,
        flags=re.DOTALL,
    )
    assert official_struct is not None
    assert "Handshake" not in official_struct.group("body")
    for macro in (
        "AHBDMA_TEST_HS_HARDWARE",
        "AHBDMA_TEST_HS_SOFTWARE",
        "AHBDMA_TEST_HS_ACTIVE_HIGH",
        "AHBDMA_TEST_HS_ACTIVE_LOW",
    ):
        assert re.search(rf"#define\s+{macro}\b", header)

    init_body = _function_body(source, "AHBDMA_initChannel")
    assert "HS_SEL_SRC" not in init_body
    assert "HS_SEL_DST" not in init_body
    test_body = _function_body(source, "AHBDMA_testConfigureChannelHandshake")
    for bit_name in (
        "AHBDMA0_CH_CFGL_HS_SEL_SRC_Pos",
        "AHBDMA0_CH_CFGL_HS_SEL_DST_Pos",
        "AHBDMA0_CH_CFGL_SRC_HS_POL_Pos",
        "AHBDMA0_CH_CFGL_DST_HS_POL_Pos",
    ):
        assert bit_name in test_body


# Catch direction/kind collapse and raw-offset register access.
def test_dma_software_handshake_contract_uses_named_registers() -> None:
    header = DMA_HEADER.read_text(encoding="utf-8")
    source = DMA_SOURCE.read_text(encoding="utf-8")
    cmsis = CMSIS_HEADER.read_text(encoding="utf-8")

    assert re.search(
        r"DRV_Status\s+AHBDMA_testSetSoftwareHandshakeRequest\s*\(\s*"
        r"AHBDMA_Type\s*\*AHBDMAx\s*,\s*uint32_t\s+ch\s*,\s*"
        r"uint32_t\s+requestType\s*,\s*ControlStatus\s+status\s*\)",
        header,
    )
    for macro in (
        "AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_TRANSFER",
        "AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_TRANSFER",
        "AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_SINGLE",
        "AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_SINGLE",
        "AHBDMA_TEST_SOFTWARE_REQUEST_SOURCE_LAST",
        "AHBDMA_TEST_SOFTWARE_REQUEST_DESTINATION_LAST",
    ):
        assert re.search(rf"#define\s+{macro}\b", header)

    dma_type_match = re.search(
        r"typedef struct\s*\{(?P<body>.*?)\}\s*AHBDMA_Type;",
        cmsis,
        flags=re.DOTALL,
    )
    assert dma_type_match is not None
    dma_type = dma_type_match.group("body")
    for register, offset in (
        ("REQSRCREG", "0x00000368"),
        ("REQDSTREG", "0x00000370"),
        ("SGLRQSRCREG", "0x00000378"),
        ("SGLRQDSTREG", "0x00000380"),
        ("LSTSRCREG", "0x00000388"),
        ("LSTDSTREG", "0x00000390"),
    ):
        assert re.search(
            rf"\b{register};\s*/\*\!< \(@ {offset}\)",
            dma_type,
        )

    body = _function_body(source, "AHBDMA_testSetSoftwareHandshakeRequest")
    for register in (
        "REQSRCREG",
        "REQDSTREG",
        "SGLRQSRCREG",
        "SGLRQDSTREG",
        "LSTSRCREG",
        "LSTDSTREG",
    ):
        assert f"AHBDMAx->{register}" in body
    assert "AHBDMA0_REQSRCREG_SRC_REQ_WE_Pos" in body
    assert "AHBDMA0_REQDSTREG_DST_REQ_WE_Pos" in body
    assert "AHBDMA0_SGLRQSRCREG_SRC_SGLREQ_WE_Pos" in body
    assert "AHBDMA0_SGLRQDSTREG_DST_SGLREQ_WE_Pos" in body
    assert "AHBDMA0_LSTSRCREG_LSTSRC_WE_Pos" in body
    assert "AHBDMA0_LSTDSTREG_LSTDST_WE_Pos" in body
    assert "REG32(" not in body
    assert "OFFSET(" not in body
