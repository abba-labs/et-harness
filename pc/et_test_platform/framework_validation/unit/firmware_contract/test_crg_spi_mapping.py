# CRG的SPI增量映射契约检查。
# 职责：核对PC/Firmware类别、生成CMSIS位号和实际Chip Config映射。
# 边界：仅软件验证，不代表硬件复位或时钟门控已实测。
# 依赖：标准库、pytest及CRG公开Model/Codec。

import re
from pathlib import Path

import pytest

from et_test_platform.drivers.crg.codec import encode_clock_set, encode_reset
from et_test_platform.drivers.crg.models import CrgPeripheral

ROOT = Path(__file__).resolve().parents[5]


# 测试Feature：SPI使用新增类别9，既有四字节请求体不变。
# 测试方法：1. 读取固件枚举；2. 分别编码时钟和复位请求。
# 通过条件：四个实例均使用类别9，实例号原样保留，保留字节为零。
@pytest.mark.parametrize("instance", range(4))
def test_crg_spi_wire_matches_firmware(instance: int) -> None:

    header = (ROOT / "firmware/wrap/include/et_crg_wrap.h").read_text(encoding="utf-8")
    assert "ET_CRG_WRAP_PERIPHERAL_SPI = 9u" in header
    assert encode_reset(int(CrgPeripheral.SPI), instance) == bytes((9, instance, 0, 0))
    assert encode_clock_set(int(CrgPeripheral.SPI), instance, 1) == bytes((9, instance, 1, 0))


# 测试Feature：SPI时钟和复位选择使用同组同位，不能误用旧SDK的主从枚举。
# 测试方法：1. 检查CMSIS的GTEN/SRST位置；2. 检查Chip Config的选择式及表项。
# 通过条件：SPI0～3逐一映射到组1的bit14～17，角色不参与映射。
@pytest.mark.parametrize("instance, bit", [(0, 14), (1, 15), (2, 16), (3, 17)])
def test_crg_spi_selector_matches_generated_bits(instance: int, bit: int) -> None:

    chip = ROOT / "firmware/chips/et6801"
    cmsis = (chip / "sdk/CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    config = (chip / "config/et_chip_wrap_config.h").read_text(encoding="utf-8")

    # 核对目标芯片的门控和复位位，避免仅凭旧外设名猜测选择值。
    for prefix in ("CRG_GTEN1_CRG_CLK_GTEN", "CRG_SRST1_CRG_SRST_N"):
        assert re.search(rf"#define\s+{prefix}_SPI{instance}_Pos\s+\({bit}UL\)", cmsis)
    assert (
        f"#define ET6801_CRG_PERIPHERAL_SPI{instance} "
        f"(BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_SPI{instance}_Pos)"
    ) in config
    assert (
        f"{{ET_CRG_WRAP_PERIPHERAL_SPI, ET6801_CRG_SPI_LOGICAL_{instance}, "
        f"ET6801_CRG_PERIPHERAL_SPI{instance}}}"
    ) in config
