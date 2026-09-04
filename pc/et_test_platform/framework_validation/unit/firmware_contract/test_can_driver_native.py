# CAN SDK驱动的寄存器级软件回归。
# 职责：编译完整真实Driver，验证三实例隔离、FDOE查询和时间戳分频边界。
# 边界：寄存器桩不模拟CAN总线，不替代FPGA收发或ECC硬件验证。
# 依赖：本机C编译器及ET6801生成头文件中的真实位定义。

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SDK = ROOT / "firmware/chips/et6801/sdk"
SOURCE = SDK / "ET6x_Driver/Src/et6x_can.c"


# 保留真实API和位定义，仅把MMIO存储替换为相互独立的三组寄存器。
def write_can_driver_harness(directory: Path) -> Path:

    source = SOURCE.read_text(encoding="utf-8")
    cmsis = (SDK / "CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    shutil.copyfile(SDK / "ET6x_Driver/Inc/et6x_can.h", directory / "et6x_can.h")
    definitions = "\n".join(
        line
        for line in cmsis.splitlines()
        if re.match(r"#define\s+(CAN0_|CAN_MISC0_|SYSC_ECCEN_)", line)
    )
    fields = sorted(set(re.findall(r"CANx->(\w+)", source)))
    stub = (
        "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n#include <assert.h>\n"
        "#define assert_param(v) assert(v)\n#define DRV_OK 0\n#define DRV_ERROR (-1)\n"
        "#define READ_REG(r) (r)\n#define WRITE_REG(r,v) ((r)=(v))\n"
        "#define READ_BIT(r,m) ((r)&(m))\n"
        "#define MODIFY_REG(r,m,v) ((r)=((r)&~(m))|(v))\n"
        "#define SET_BIT(r,m) ((r)|=(m))\n#define CLEAR_BIT(r,m) ((r)&=~(m))\n"
        "#define REG32(a) (*(uint32_t *)(uintptr_t)(a))\n"
        "typedef struct { " + " ".join(f"uint32_t {field};" for field in fields) + " } CAN_Type;\n"
        "typedef struct {uint32_t MISC_STATUS, MISC_CTRL, DMU_DMA_CFG;} CAN_MISC_Type;\n"
        "typedef struct {uint32_t ECCEN;} SYSC_Type;\n"
        "extern CAN_Type controllers[3];\nextern CAN_MISC_Type misc_blocks[3];\n"
        "extern SYSC_Type system_control;\n#define SYSC (&system_control)\n"
        + "\n".join(
            f"#define CAN{index} (&controllers[{index}])\n"
            f"#define CAN_MISC{index} (&misc_blocks[{index}])"
            for index in range(3)
        )
        + "\n"
        + definitions
        + "\n"
    )
    (directory / "et6x.h").write_text(stub, encoding="utf-8")
    harness = directory / "can_driver_harness.c"
    harness.write_text(HARNESS, encoding="utf-8")
    return harness


# 测试Feature：FD状态、Timestamp分频、MISC实例隔离及Classic/FD/Remote数据长度。
# 测试方法：1. 编译真实驱动；2. 遍历分频和实例；3. 在消息缓存后设置哨兵验证写入边界。
# 通过条件：FDOE独立准确，非法分频无副作用，实例互不影响，DLC不会导致越界搬运。
def test_can_driver_register_contract(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")

    harness = write_can_driver_harness(tmp_path)
    executable = tmp_path / "can_driver.exe"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-I",
            str(tmp_path),
            str(SOURCE),
            str(harness),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=5)


# 这是可执行C夹具，不是Python注释；输入和期望独立构造，不调用待测代码生成期望。
HARNESS = r"""
#include "et6x_can.h"
#include <string.h>
CAN_Type controllers[3];
CAN_MISC_Type misc_blocks[3];
SYSC_Type system_control;

int main(void)
{
    CAN_Type *instances[] = {CAN0, CAN1, CAN2};
    CAN_ConfigParams config = {0};
    CAN_ECCConfigParams ecc = {0};
    const uint32_t divisors[] = {1, 16};
    CAN_TxBufElement tx = {0};
    CAN_RxBufElement rx = {0};
    uint32_t words[20];
    for (unsigned byte = 0; byte < CAN_MAX_PAYLOAD_BYTES; ++byte)
    {
        tx.data[byte] = (uint16_t)byte;
    }
    for (unsigned dlc = CAN_DLC_BYTES_8; dlc <= CAN_DLC_BYTES_64; ++dlc)
    {
        for (unsigned word = 0; word < 20; ++word) { words[word] = 0xA5A5A5A5U; }
        tx.fdf = CAN_CLASSIC_CAN; tx.rtr = CAN_DATA_FRAME; tx.dlc = dlc;
        CAN_copyMsgToBuffer(&tx, words);
        assert(words[2] == 0x03020100U && words[3] == 0x07060504U);
        assert(words[4] == 0xA5A5A5A5U);
        memset(&rx, 0, sizeof(rx));
        rx.data[8] = 0x5A;
        CAN_copyBufferToMsg(words, &rx);
        assert(rx.dlc == dlc && rx.fdf == CAN_CLASSIC_CAN);
        assert(rx.data[7] == 7 && rx.data[8] == 0x5A);
    }
    tx.fdf = CAN_FD_CAN; tx.dlc = CAN_DLC_BYTES_64;
    CAN_copyMsgToBuffer(&tx, words);
    assert(words[17] == 0x3F3E3D3CU && words[18] == 0xA5A5A5A5U);
    CAN_copyBufferToMsg(words, &rx);
    assert(rx.data[63] == 63);
    tx.fdf = CAN_CLASSIC_CAN; tx.rtr = CAN_REMOTE_FRAME;
    words[2] = 0xA5A5A5A5U;
    CAN_copyMsgToBuffer(&tx, words);
    assert(words[2] == 0xA5A5A5A5U);

    for (unsigned index = 0; index < 3; ++index)
    {
        memset(controllers, 0, sizeof(controllers));
        memset(misc_blocks, 0, sizeof(misc_blocks));
        instances[index]->CCCR = CAN0_CCCR_FDOE_Msk;
        assert(CAN_isFDOpEnable(instances[index]) == 1);
        instances[index]->CCCR = CAN0_CCCR_CCE_Msk;
        misc_blocks[index].MISC_STATUS = CAN_MISC0_MISC_STATUS_TTCAN_CCE_Msk;
        assert(CAN_isFDOpEnable(instances[index]) == 0);

        for (unsigned item = 0; item < 2; ++item)
        {
            config.tsPrescalar = divisors[item];
            config.tsSelect = CAN_TIMESTAMP_INTERNAL;
            assert(CAN_config(instances[index], &config) == DRV_OK);
            assert(((instances[index]->TSCC & CAN0_TSCC_TCP_Msk) >> CAN0_TSCC_TCP_Pos)
                   == divisors[item] - 1);
        }
        CAN_Type before = *instances[index];
        config.tsPrescalar = 0;
        assert(CAN_config(instances[index], &config) == DRV_ERROR);
        assert(memcmp(&before, instances[index], sizeof(before)) == 0);
        config.tsPrescalar = 17;
        assert(CAN_config(instances[index], &config) == DRV_ERROR);
        assert(memcmp(&before, instances[index], sizeof(before)) == 0);
        assert(CAN_config(instances[index], NULL) == DRV_ERROR);

        CAN_setDMURxRequest(instances[index], (CAN_DMURxRequest)1);
        ecc.enableRdModWr = 1;
        CAN_eccConfig(instances[index], &ecc);
        for (unsigned other = 0; other < 3; ++other)
        {
            assert(misc_blocks[other].DMU_DMA_CFG ==
                   (other == index ? (1U << CAN_MISC0_DMU_DMA_CFG_DMU_DMA_RX_SEL_Pos) : 0));
            assert(misc_blocks[other].MISC_CTRL ==
                   (other == index ? CAN_MISC0_MISC_CTRL_TTCAN_DIS_MORD_Msk : 0));
        }
    }
    return 0;
}
"""
