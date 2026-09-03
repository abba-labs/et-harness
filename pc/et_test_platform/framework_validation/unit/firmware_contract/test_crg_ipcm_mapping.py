# CRG 到 IPCM 的双端映射契约检查。
# 职责：锁定公共类别和芯片复位、时钟选择位的一致性。
# 边界：静态源码检查，不代表硬件复位测试通过。
# 依赖：标准库、本 IP Codec 和生成 CMSIS 头文件。

import re
from pathlib import Path

from et_test_platform.drivers.crg.codec import encode_reset
from et_test_platform.drivers.crg.models import CrgPeripheral

ROOT = Path(__file__).resolve().parents[5]


# 测试 Feature：IPCM RESET 使用独立的新类别，保持原四字节命令体。
# 测试方法：编码实例 0 请求，同时检查固件公开枚举。
# 通过条件：两端类别均为 8，保留字节为零，不改变原命令结构。
def test_crg_ipcm_reset_wire_matches_firmware() -> None:

    header = (ROOT / "firmware/wrap/include/et_crg_wrap.h").read_text(encoding="utf-8")
    assert "ET_CRG_WRAP_PERIPHERAL_IPCM = 8u" in header
    assert encode_reset(int(CrgPeripheral.IPCM), 0) == bytes((8, 0, 0, 0))


# 测试 Feature：IPCM 时钟和复位使用同一 CRG Driver 选择值。
# 测试方法：检查 CMSIS 位定义和 SDK 选择表达式。
# 通过条件：GTEN1 和 SRST1 的位位置一致且均为 25，公共 Wrap 不保存物理位号。
def test_crg_ipcm_selector_uses_generated_clock_and_reset_bit() -> None:

    chip = ROOT / "firmware/chips/et6801"
    cmsis = (chip / "sdk/CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    driver = (chip / "sdk/ET6x_Driver/Inc/et6x_crg.h").read_text(encoding="utf-8")

    # 两种寄存器采用一致的组、位编码，现有 CRG 原子动作可以直接复用。
    for symbol in ("CRG_GTEN1_CRG_CLK_GTEN_IPCM_Pos", "CRG_SRST1_CRG_SRST_N_IPCM_Pos"):
        assert re.search(rf"#define\s+{symbol}\s+\(25UL\)", cmsis)
    assert "CRG_PERIPH_IPCM     = BITS_DWORD + CRG_GTEN1_CRG_CLK_GTEN_IPCM_Pos" in driver
