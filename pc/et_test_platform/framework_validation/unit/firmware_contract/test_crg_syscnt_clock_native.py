# CRG系统计数器时钟扩展的寄存器桩测试。
# 职责：执行真实Driver函数，证明只修改SVD指定的门控位。
# 边界：不模拟计数器时序，不声明FPGA通过。
# 依赖：本地C编译器、标准库和pytest。

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]


# 测试Feature：SYSCNT独立时钟门控，不触及其他位和复位寄存器。
# 测试方法：提取实际Driver函数和CMSIS位定义，编译后遍历初值、启停和非法参数。
# 通过条件：只有目标位变化，非法输入不写入；GET返回真实Boolean。
def test_crg_syscnt_clock_register_isolation(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")

    chip = ROOT / "firmware/chips/et6801/sdk"
    driver = (chip / "ET6x_Driver/Src/et6x_crg.c").read_text(encoding="utf-8")
    cmsis = (chip / "CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    start = driver.index("DRV_Status CRG_testSetSYSCNTClock(")
    functions = driver[
        start : driver.index("/********************* TEST DRIVER EXTENSION END", start)
    ]
    definitions = "\n".join(
        line
        for line in cmsis.splitlines()
        if re.match(r"#define\s+CRG_GTEN0_CRG_CLK_GTEN_SYSCNT_", line)
    )
    source = tmp_path / "crg_syscnt.c"
    executable = tmp_path / "crg_syscnt.exe"
    source.write_text(
        """
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
typedef enum { DRV_OK, DRV_PARAM_ERR } DRV_Status;
static struct { uint32_t GTEN0; uint32_t SRST0; } registers;
#define CRG (&registers)
#define MODIFY_REG(r,m,v) ((r) = ((r) & ~(m)) | (v))
#define READ_BIT(r,m) ((r) & (m))
"""
        + definitions
        + "\n"
        + functions
        + """
int main(void)
{
    const uint32_t patterns[] = { 0, UINT32_MAX, 0xaaaaaaaa, 0x55555555 };
    uint8_t readback = 99;
    registers.SRST0 = 0x12345678;
    assert(CRG_GTEN0_CRG_CLK_GTEN_SYSCNT_Msk == (1u << 16));
    for (unsigned i = 0; i < sizeof(patterns) / sizeof(patterns[0]); ++i)
    {
        registers.GTEN0 = patterns[i];
        assert(CRG_testSetSYSCNTClock(1) == DRV_OK);
        assert(registers.GTEN0 == (patterns[i] | (1u << 16)));
        assert(CRG_testGetSYSCNTClock(&readback) == DRV_OK && readback == 1);
        assert(CRG_testSetSYSCNTClock(0) == DRV_OK);
        assert(registers.GTEN0 == (patterns[i] & ~(1u << 16)));
        assert(CRG_testGetSYSCNTClock(&readback) == DRV_OK && readback == 0);
        const uint32_t before = registers.GTEN0;
        assert(CRG_testSetSYSCNTClock(2) == DRV_PARAM_ERR);
        assert(registers.GTEN0 == before);
        assert(registers.SRST0 == 0x12345678);
    }
    assert(CRG_testGetSYSCNTClock(NULL) == DRV_PARAM_ERR);
    return 0;
}
""",
        encoding="utf-8",
    )
    subprocess.run(
        [compiler, "-std=c99", "-Werror", str(source), "-o", str(executable)], check=True
    )
    subprocess.run([str(executable)], check=True, timeout=5)
