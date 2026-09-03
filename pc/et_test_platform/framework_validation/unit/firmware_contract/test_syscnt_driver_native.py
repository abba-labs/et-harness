# SYSCNT真实SDK测试扩展的寄存器桩验证。
# 职责：验证停止装载、独立启停、连贯读取和参考计数器借用契约。
# 边界：桩不能证明FPGA时钟速率或Debug Halt硬件联动。
# 依赖：本机C编译器、pytest及当前芯片SDK源码。

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SDK = ROOT / "firmware/chips/et6801/sdk"


# 提取真实测试扩展，避免在桩中重写待测实现。
def _extension(text: str) -> str:

    return (
        text.split("TEST DRIVER EXTENSION BEGIN", 1)[1]
        .split("*/", 1)[1]
        .split("/********************* TEST DRIVER EXTENSION END", 1)[0]
    )


# 测试 Feature：计数原子操作、双窗口进位保护、参考计数器所有权。
# 测试方法：
# 1. 用实际SVD宏和真实SDK函数编译寄存器桩。
# 2. 验证写序、副作用、非法参数和持续/暂态撕裂读取。
# 3. 验证参考采样不清零DWT，并只恢复借用的使能位。
# 通过条件：所有C断言通过；不把此结果视为硬件PASS。
def test_syscnt_atomic_driver_contract(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")
    symbols = "\n".join(
        line
        for line in (SDK / "CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8").splitlines()
        if re.match(r"#define\s+SYSCNT_CTRL_(CNTCR_(EN|HDBG)|CNTSR_DBGH)_", line)
    )
    header = _extension((SDK / "ET6x_Driver/Inc/et6x_cortex.h").read_text(encoding="utf-8"))
    implementation = _extension((SDK / "ET6x_Driver/Src/et6x_cortex.c").read_text(encoding="utf-8"))
    source = tmp_path / "syscnt.c"
    executable = tmp_path / "syscnt.exe"
    source.write_text(
        """
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
typedef enum { DRV_OK, DRV_ERROR, DRV_PARAM_ERR, DRV_BUSY } DRV_Status;
static struct { uint32_t CNTCR, CNTSR, CNTCVL, CNTCVU, CNTFID0; } ctrl, ro;
static struct { uint32_t CTRL, CYCCNT; } dwt;
static struct { uint32_t DEMCR; } debug;
#define SYSCNT_CTRL (&ctrl)
#define SYSCNT_RO (&ro)
#define DWT (&dwt)
#define CoreDebug (&debug)
#define DWT_CTRL_CYCCNTENA_Msk 1u
#define DWT_CTRL_NOCYCCNT_Msk (1u << 25)
#define CoreDebug_DEMCR_TRCENA_Msk (1u << 24)
#define __DSB() ((void)0)
#define __ISB() ((void)0)
static unsigned reads, writes, tear_mode, high_reads;
static uint32_t *write_addresses[2];
static uint32_t read_register(uint32_t *reg)
{
    ++reads;
    if ((reg == &ctrl.CNTCVU || reg == &ro.CNTCVU) && tear_mode)
    {
        ++high_reads;
        if (tear_mode == 2) return high_reads;
        if (high_reads == 1) return 0;
        return 1;
    }
    return *reg;
}
static void write_register(uint32_t *reg, uint32_t value)
{
    if (writes < 2) write_addresses[writes] = reg;
    ++writes;
    *reg = value;
}
#define READ_REG(r) read_register(&(r))
#define READ_BIT(r,m) (READ_REG(r) & (m))
#define WRITE_REG(r,v) write_register(&(r), (v))
#define MODIFY_REG(r,m,v) ((r) = ((r) & ~(m)) | (v))
#define SET_BIT(r,m) ((r) |= (m))
"""
        + symbols
        + "\n"
        + header
        + implementation
        + """
int main(void)
{
    uint64_t count = UINT64_MAX;
    uint32_t before, after;
    SYSCNT_TestControl snapshot;
    const uint32_t keep = 0xa5a50000;
    ctrl.CNTCR = keep;
    ctrl.CNTFID0 = 123;
    assert(SYSCNT_testLoadStopped(UINT64_C(0x123456789abcdef0)) == DRV_OK);
    assert(writes == 2 && write_addresses[0] == &ctrl.CNTCVL && write_addresses[1] == &ctrl.CNTCVU);
    assert(ctrl.CNTCVL == 0x9abcdef0 && ctrl.CNTCVU == 0x12345678 && ctrl.CNTCR == keep);
    assert(SYSCNT_testSetEnabled(1) == DRV_OK && ctrl.CNTCR == (keep | 1));
    assert(ctrl.CNTFID0 == 123 && ctrl.CNTCVU == 0x12345678);
    assert(SYSCNT_testLoadStopped(0) == DRV_BUSY && writes == 2);
    assert(SYSCNT_testSetFrequencyId(42) == DRV_BUSY && ctrl.CNTFID0 == 123);
    assert(SYSCNT_testSetEnabled(2) == DRV_PARAM_ERR && ctrl.CNTCR == (keep | 1));
    assert(SYSCNT_testSetHaltPolicy(1) == DRV_OK && ctrl.CNTCR == (keep | 3));
    assert(SYSCNT_testSetHaltPolicy(2) == DRV_PARAM_ERR && ctrl.CNTCR == (keep | 3));
    ctrl.CNTSR = SYSCNT_CTRL_CNTSR_DBGH_Msk;
    assert(SYSCNT_testGetControl(&snapshot) == DRV_OK);
    assert(snapshot.enabled && snapshot.halt_enabled && snapshot.debug_halted && snapshot.frequency_id_hz == 123);
    assert(SYSCNT_testSetEnabled(0) == DRV_OK && ctrl.CNTCR == (keep | 2));
    assert(SYSCNT_testSetHaltPolicy(0) == DRV_OK && ctrl.CNTCR == keep);
    assert(SYSCNT_testSetFrequencyId(0) == DRV_PARAM_ERR);
    assert(SYSCNT_testSetFrequencyId(42) == DRV_OK && ctrl.CNTFID0 == 42);
    assert(SYSCNT_testGetControl(NULL) == DRV_PARAM_ERR);
    assert(SYSCNT_testReadCount(SYSCNT_TEST_VIEW_CONTROL, &count) == DRV_OK);
    assert(count == UINT64_C(0x123456789abcdef0));
    ro.CNTCVU = 2; ro.CNTCVL = 3;
    assert(SYSCNT_testReadCount(SYSCNT_TEST_VIEW_READ, &count) == DRV_OK);
    assert(count == UINT64_C(0x200000003));
    assert(SYSCNT_testReadCount((SYSCNT_TestView)2, &count) == DRV_PARAM_ERR);
    assert(SYSCNT_testReadCount(SYSCNT_TEST_VIEW_READ, NULL) == DRV_PARAM_ERR);
    for (unsigned view = 0; view < 2; ++view)
    {
        tear_mode = 1; high_reads = 0;
        assert(SYSCNT_testReadCount((SYSCNT_TestView)view, &count) == DRV_OK);
        assert(high_reads == 4 && (count >> 32) == 1);
        tear_mode = 2; high_reads = 0; count = UINT64_MAX;
        assert(SYSCNT_testReadCount((SYSCNT_TestView)view, &count) == DRV_BUSY);
        assert(high_reads == 2 * SYSCNT_TEST_READ_ATTEMPTS && count == UINT64_MAX);
    }
    tear_mode = 0;
    assert(SYSCNT_testSampleReference(&before, &count, &after) == DRV_BUSY);
    assert(SYSCNT_testSampleReference(NULL, &count, &after) == DRV_PARAM_ERR);
    for (unsigned owned = 0; owned < 2; ++owned)
    {
        debug.DEMCR = 0x100 | (owned ? CoreDebug_DEMCR_TRCENA_Msk : 0);
        dwt.CTRL = 0x100 | owned; dwt.CYCCNT = 0x12345678;
        assert(SYSCNT_testSetReferenceEnabled(1) == DRV_OK);
        assert(SYSCNT_testSetReferenceEnabled(1) == DRV_OK);
        assert(dwt.CYCCNT == 0x12345678 && (dwt.CTRL & 1));
        assert(SYSCNT_testSampleReference(&before, &count, &after) == DRV_OK);
        assert(before == dwt.CYCCNT && after == dwt.CYCCNT && count == UINT64_C(0x200000003));
        debug.DEMCR |= 0x200; dwt.CTRL |= 0x200;
        assert(SYSCNT_testSetReferenceEnabled(0) == DRV_OK);
        assert(SYSCNT_testSetReferenceEnabled(0) == DRV_OK);
        assert(debug.DEMCR == (0x300 | (owned ? CoreDebug_DEMCR_TRCENA_Msk : 0)));
        assert(dwt.CTRL == (0x300 | owned) && dwt.CYCCNT == 0x12345678);
    }
    assert(SYSCNT_testSetReferenceEnabled(2) == DRV_PARAM_ERR);
    debug.DEMCR = 0x100; dwt.CTRL = DWT_CTRL_NOCYCCNT_Msk;
    assert(SYSCNT_testSetReferenceEnabled(1) == DRV_ERROR && debug.DEMCR == 0x100);
    assert(SYSCNT_testSampleReference(&before, &count, &after) == DRV_BUSY);
    return 0;
}
""",
        encoding="utf-8",
    )
    compiled = subprocess.run(
        [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    subprocess.run([str(executable)], check=True, timeout=5)
