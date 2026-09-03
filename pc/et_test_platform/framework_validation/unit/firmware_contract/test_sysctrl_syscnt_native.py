# SYSCTRL计数器路由测试扩展的寄存器桩验证。
# 职责：执行真实Driver代码并验证只改变目标字段。
# 边界：软件模型不声明实际FPGA时钟或Debug Halt联动通过。
# 依赖：本机C编译器和pytest。

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]


# 测试Feature：系统时钟选择和Halt路由位隔离、快照真实读回。
# 测试方法：1. 提取SDK原函数和SVD生成宏。2. 遍历初始模式及开关值。
# 通过条件：保留位不变，状态准确；非法Boolean及空输出指针均拒绝。
def test_sysctrl_syscnt_register_isolation(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")
    chip = ROOT / "firmware/chips/et6801/sdk"
    driver = (chip / "ET6x_Driver/Src/et6x_sysctrl.c").read_text(encoding="utf-8")
    start = driver.index("void SYSCTRL_selectSYSCNTClockSource(")
    selection = driver[start : driver.index("\n/**", start)]
    start = driver.index("DRV_Status SYSCTRL_testSetSYSCNTHaltRoute(")
    functions = driver[start : driver.index("#endif", start)]
    symbols = "\n".join(
        line
        for line in (chip / "CMSIS/Device/Include/et6801.h")
        .read_text(encoding="utf-8")
        .splitlines()
        if re.match(r"#define\s+SYSC_(CLK_SCNT_SEL_IN|SCNT_HALT_MODE_EN)_", line)
    )
    source = tmp_path / "sysctrl_syscnt.c"
    executable = tmp_path / "sysctrl_syscnt.exe"
    source.write_text(
        """
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
typedef enum { DRV_OK, DRV_PARAM_ERR } DRV_Status;
typedef enum { SYSCTRL_SYSCNT_CLKSRC_OSC25M, SYSCTRL_SYSCNT_CLKSRC_XO25M } SYSCTRL_SYSCNTClockSource;
typedef struct { SYSCTRL_SYSCNTClockSource source; uint8_t halt_enabled; } SYSCTRL_TestSyscntRouting;
static struct { uint32_t CLK_SCNT; uint32_t SCNT; } registers;
#define SYSC (&registers)
#define assert_param assert
#define MODIFY_REG(r,m,v) ((r) = ((r) & ~(m)) | (v))
#define READ_BIT(r,m) ((r) & (m))
#define READ_REG(r) (r)
"""
        + symbols
        + "\n"
        + selection
        + functions
        + """
int main(void)
{
    const uint32_t patterns[] = { 0, UINT32_MAX, 0xaaaaaaaa, 0x55555555 };
    SYSCTRL_TestSyscntRouting route;
    assert(SYSC_CLK_SCNT_SEL_IN_Msk == 1u);
    assert(SYSC_SCNT_HALT_MODE_EN_Msk == 1u);
    for (unsigned i = 0; i < sizeof(patterns)/sizeof(patterns[0]); ++i)
    {
        registers.CLK_SCNT = registers.SCNT = patterns[i];
        SYSCTRL_selectSYSCNTClockSource(SYSCTRL_SYSCNT_CLKSRC_XO25M);
        assert(registers.CLK_SCNT == (patterns[i] | 1u));
        assert(registers.SCNT == patterns[i]);
        assert(SYSCTRL_testSetSYSCNTHaltRoute(1) == DRV_OK);
        assert(registers.SCNT == (patterns[i] | 1u));
        assert(SYSCTRL_testGetSYSCNTRouting(&route) == DRV_OK);
        assert(route.source == SYSCTRL_SYSCNT_CLKSRC_XO25M && route.halt_enabled == 1);
        assert(SYSCTRL_testSetSYSCNTHaltRoute(2) == DRV_PARAM_ERR);
        assert(registers.SCNT == (patterns[i] | 1u));
        assert(SYSCTRL_testSetSYSCNTHaltRoute(0) == DRV_OK);
        SYSCTRL_selectSYSCNTClockSource(SYSCTRL_SYSCNT_CLKSRC_OSC25M);
        assert(registers.CLK_SCNT == (patterns[i] & ~1u));
        assert(registers.SCNT == (patterns[i] & ~1u));
        assert(SYSCTRL_testGetSYSCNTRouting(&route) == DRV_OK);
        assert(route.source == SYSCTRL_SYSCNT_CLKSRC_OSC25M && route.halt_enabled == 0);
    }
    assert(SYSCTRL_testGetSYSCNTRouting(NULL) == DRV_PARAM_ERR);
    return 0;
}
""",
        encoding="utf-8",
    )
    compiled = subprocess.run(
        [compiler, "-std=c99", "-Werror", str(source), "-o", str(executable)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    subprocess.run([str(executable)], check=True, timeout=5)
