# Framework Validation测试模块。
#
# 职责：验证test_firmware_driver_boundary 对应的软件合同和回归行为。
# 边界：不作为平台运行时代码，不执行未经硬件门禁的真实设备操作。
# 依赖：仅依赖pytest、测试替身和被测模块。

from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[5]
WRAP_ROOT = PROJECT_ROOT / "firmware" / "wrap"
DRIVER_ROOT = PROJECT_ROOT / "firmware" / "chips" / "et6801" / "sdk" / "ET6x_Driver"
CHIP_PROJECT = PROJECT_ROOT / "firmware" / "chips" / "et6801" / "project.yaml"

TEST_DRIVER_BEGIN = "/******************** TEST DRIVER EXTENSION BEGIN ********************/"
TEST_DRIVER_END = "/********************* TEST DRIVER EXTENSION END *********************/"


def _without_c_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*?$", "", source, flags=re.MULTILINE)


# Catch any register implementation leaking from Driver into Wrap.
def test_wrap_sources_cannot_access_hardware_registers() -> None:
    forbidden_macros = re.compile(r"\b(?:READ_REG|WRITE_REG|SET_BIT|CLEAR_BIT|MODIFY_REG)\s*\(")
    register_member = re.compile(r"(?:&\s*)?\b[A-Za-z_]\w*\s*->\s*[A-Z][A-Z0-9_]*\b")
    raw_register_pointer = re.compile(r"\*\s*\(\s*volatile\s+(?:u?int\d+_t|unsigned\s+\w+)\s*\*")
    violations: list[str] = []

    for path in sorted(WRAP_ROOT.rglob("*.[ch]")):
        source = _without_c_comments(path.read_text(encoding="utf-8"))
        for pattern in (forbidden_macros, register_member, raw_register_pointer):
            for match in pattern.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{line}:{match.group(0)}")

    assert violations == [], "Wrap register access is forbidden:\n" + "\n".join(violations)


# Wrap实现只能消费通用映射表，不能识别具体芯片的实例编号或寄存器位名。
def test_wrap_sources_do_not_encode_selected_chip_topology() -> None:
    forbidden = re.compile(
        r"\b(?:ET_CHIP_(?:DMA|UART|CRC|AES)\d+_|"
        r"(?:DMA|UART|CRC|AES)\d+_(?:IRQn|[A-Z][A-Z0-9_]*_Msk)|"
        r"AHBDMA\d+(?:_ACC)?)\b"
    )
    violations: list[str] = []

    for path in sorted((WRAP_ROOT / "src").glob("*.c")):
        source = _without_c_comments(path.read_text(encoding="utf-8"))
        for match in forbidden.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(PROJECT_ROOT)}:{line}:{match.group(0)}")

    assert violations == [], "Wrap contains selected-chip topology:\n" + "\n".join(violations)


# Catch any current or future Test Driver API outside its guarded block.
def test_test_driver_extensions_are_isolated() -> None:
    required_paths = (
        DRIVER_ROOT / "Inc" / "et6x_uart.h",
        DRIVER_ROOT / "Src" / "et6x_uart.c",
        DRIVER_ROOT / "Inc" / "et6x_ahbdma.h",
        DRIVER_ROOT / "Src" / "et6x_ahbdma.c",
        DRIVER_ROOT / "Inc" / "et6x_crc.h",
        DRIVER_ROOT / "Src" / "et6x_crc.c",
        DRIVER_ROOT / "Inc" / "et6x_aes.h",
        DRIVER_ROOT / "Src" / "et6x_aes.c",
        DRIVER_ROOT / "Inc" / "et6x_fmac.h",
        DRIVER_ROOT / "Src" / "et6x_fmac.c",
        DRIVER_ROOT / "Inc" / "et6x_cordic.h",
        DRIVER_ROOT / "Src" / "et6x_cordic.c",
        DRIVER_ROOT / "Inc" / "et6x_cpu.h",
        DRIVER_ROOT / "Src" / "et6x_cpu.c",
        DRIVER_ROOT / "Inc" / "et6x_crg.h",
        DRIVER_ROOT / "Src" / "et6x_crg.c",
        DRIVER_ROOT / "Inc" / "et6x_stimer.h",
        DRIVER_ROOT / "Src" / "et6x_stimer.c",
        DRIVER_ROOT / "Inc" / "et6x_wdg.h",
        DRIVER_ROOT / "Src" / "et6x_wdg.c",
        DRIVER_ROOT / "Inc" / "et6x_spinlock.h",
        DRIVER_ROOT / "Src" / "et6x_spinlock.c",
    )
    test_api = re.compile(r"\b[A-Za-z_]\w*_test[A-Z]\w*\s*\(")
    paths_with_extensions: set[Path] = set()

    for path in sorted(DRIVER_ROOT.rglob("*.[ch]")):
        source = path.read_text(encoding="utf-8")
        matches = tuple(test_api.finditer(source))
        if not matches:
            continue

        paths_with_extensions.add(path)
        begin = source.find(TEST_DRIVER_BEGIN)
        end = source.find(TEST_DRIVER_END)
        assert begin >= 0, f"missing Test Driver begin marker: {path}"
        assert end > begin, f"missing Test Driver end marker: {path}"
        # The extension may legitimately grow beyond one quarter of a Driver
        # file.  "At the bottom" therefore means that no production function
        # definition is allowed after the guarded extension, rather than a
        # fragile source-length percentage.
        trailing = _without_c_comments(source[end + len(TEST_DRIVER_END) :])
        function_definition = re.compile(
            r"\b[A-Za-z_]\w*\s*\([^;{}]*\)\s*\{",
            flags=re.DOTALL,
        )
        assert function_definition.search(trailing) is None, (
            f"production function found after Test Driver block: {path}"
        )
        guard = source.rfind("#if defined(ET_ENABLE_TEST_DRIVER_EXTENSIONS)", 0, begin)
        assert guard >= 0, f"missing Test Driver compile guard: {path}"
        assert source.find("#endif", end) > end, f"missing Test Driver compile guard end: {path}"

        for match in matches:
            assert begin < match.start() < end, (
                f"Test Driver API outside extension block: {path}:{match.group(0)}"
            )

    assert paths_with_extensions == set(required_paths)

    uart_header = required_paths[0].read_text(encoding="utf-8")
    dma_header = required_paths[2].read_text(encoding="utf-8")
    crc_header = required_paths[4].read_text(encoding="utf-8")
    assert "UART_testGetTxDMAEndpointAddress" in uart_header
    assert "UART_testGetRxDMAEndpointAddress" in uart_header
    for name in (
        "AHBDMA_testEnableChannelsByMask",
        "AHBDMA_testGetEnabledChannels",
        "AHBDMA_testConfigureChannelHandshake",
        "AHBDMA_testSetSoftwareHandshakeRequest",
        "AHBDMA_testGetComponentSnapshot",
        "AHBDMA_testGetInterruptSnapshot",
        "AHBDMA_testGetChannelSnapshot",
    ):
        assert name in dma_header

    for obsolete_name in (
        "AHBDMA_enableChannelsByMask",
        "AHBDMA_getEnabledChannels",
        "AHBDMA_setSoftwareHandshakeRequest",
        "AHBDMA_setChannelInterruptMask",
        "AHBDMA_getComponentSnapshot",
        "AHBDMA_getInterruptSnapshot",
        "AHBDMA_getChannelSnapshot",
    ):
        assert obsolete_name not in dma_header

    for name in (
        "CRC_testWriteInput8",
        "CRC_testWriteInput16",
        "CRC_testWriteInput32",
        "CRC_testCalculate32Timed",
    ):
        assert name in crc_header

    project = yaml.safe_load(CHIP_PROJECT.read_text(encoding="utf-8"))
    targets = project["targets"]
    assert {target["name"] for target in targets} == {
        "ET6801_FPGA_ITCM",
        "ET6801_SILICON_FLASH",
        "ET6801_FPGA_MANUAL_FLASH",
        "ET6801_FPGA_CORE1_SMOKE_ITCM",
        "ET6801_SILICON_CORE1_LAUNCHER_FLASH",
    }
    assert all("ET_ENABLE_TEST_DRIVER_EXTENSIONS" in target["defines"] for target in targets)
