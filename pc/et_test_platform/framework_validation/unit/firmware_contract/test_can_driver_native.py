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
    for name in ("et_can_wrap.h", "et_wrap_status.h"):
        shutil.copyfile(ROOT / "firmware/wrap/include" / name, directory / name)
    chip_config = (SDK.parent / "config/et_chip_wrap_config.h").read_text(encoding="utf-8")
    can_macros = re.findall(
        r"^#define ET_CHIP_CAN_.*", chip_config.replace("\\\n", " "), re.MULTILINE
    )
    (directory / "et_chip_wrap_config.h").write_text("\n".join(can_macros) + "\n", encoding="utf-8")
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
            "-DET_ENABLE_TEST_DRIVER_EXTENSIONS",
            "-I",
            str(tmp_path),
            "-I",
            str(ROOT / "firmware/services/include"),
            "-I",
            str(ROOT / "firmware/framework/include"),
            "-I",
            str(ROOT / "firmware/wrap/include"),
            str(SOURCE),
            str(ROOT / "firmware/wrap/src/et_can_wrap.c"),
            str(ROOT / "firmware/services/src/et_can_service.c"),
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
#include "et_can_wrap.h"
#include "et_can_service.h"
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
    et_can_identity_t identity;
    et_can_timing_limits_t limits;
    et_can_timing_t timing = {{2, 31, 8, 8}, {1, 15, 4, 4}};
    et_can_timing_t readback;
    et_can_options_t options = {1, 1, 1, 1, 1, 1, 1, 20, 10, 100};
    et_can_options_t options_read;
    uint8_t initializing;
    et_can_service_t service;
    et_irq_manager_t manager = {0};
    uint8_t request[33] = {0};
    uint8_t response[40];
    uint16_t response_length;
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
        instances[index]->CREL = 0x12345678;
        instances[index]->ENDN = 0x87654321;
        assert(et_can_wrap_get_identity(index, &identity) == ET_WRAP_STATUS_OK);
        assert(identity.revision == 0x12345678 && identity.endian == 0x87654321);
        assert(et_can_wrap_set_timing(index, &timing) == ET_WRAP_STATUS_STATE_ERROR);
        assert(et_can_wrap_set_initializing(index, 1) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_initializing(index, &initializing) == ET_WRAP_STATUS_OK);
        assert(initializing == 1);
        assert(et_can_wrap_get_timing_limits(index, &limits) == ET_WRAP_STATUS_OK);
        assert(limits.nominal_max.prescaler == 512 && limits.data_max.prescaler == 32);
        assert(et_can_wrap_set_timing(index, &timing) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_timing(index, &readback) == ET_WRAP_STATUS_OK);
        assert(memcmp(&timing, &readback, sizeof(timing)) == 0);
        assert(et_can_wrap_set_options(index, &options) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_options(index, &options_read) == ET_WRAP_STATUS_OK);
        assert(memcmp(&options, &options_read, sizeof(options)) == 0);
        assert(et_can_wrap_get_timing(index, &readback) == ET_WRAP_STATUS_OK);
        assert(memcmp(&timing, &readback, sizeof(timing)) == 0);
        CAN_Type option_before = *instances[index];
        options_read.tdc_offset_cycles = 128;
        assert(et_can_wrap_set_options(index, &options_read) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&option_before, instances[index], sizeof(option_before)) == 0);
        instances[index]->CCCR |= CAN0_CCCR_DAR_Msk;
        assert(et_can_wrap_get_options(index, &options_read) == ET_WRAP_STATUS_OK);
        assert(options_read.automatic_retry == 0);
        CAN_Type timing_before = *instances[index];
        readback.nominal.prescaler = 0;
        assert(et_can_wrap_set_timing(index, &readback) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        readback = timing;
        readback.data.prescaler = limits.data_max.prescaler + 1;
        assert(et_can_wrap_set_timing(index, &readback) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&timing_before, instances[index], sizeof(timing_before)) == 0);
        assert(et_can_wrap_set_initializing(index, 2) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_set_initializing(index, 0) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_initializing(index, &initializing) == ET_WRAP_STATUS_OK);
        assert(initializing == 0);
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
    assert(et_can_wrap_get_identity(3, &identity) == ET_WRAP_STATUS_NOT_SUPPORTED);
    assert(et_can_wrap_get_identity(0, NULL) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(et_can_wrap_set_timing(0, NULL) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(et_can_service_init(&service, 0, &manager, 0) == 0);
    const et_service_descriptor_t *descriptor = et_can_service_descriptor(&service);
    controllers[0].CREL = 0x12345678;
    controllers[0].ENDN = 0x87654321;
    assert(descriptor->service_id == 0x010C);
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IDENTITY_GET, request, 1,
                              response, sizeof(response), &response_length) == ET_STATUS_OK);
    assert(response_length == 8 && response[0] == 0x78 && response[4] == 0x21);
    CAN_Type unchanged = controllers[0];
    request[1] = 1;
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_INITIALIZING_SET, request, 4,
                              NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(response_length == 0 && memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
    request[0] = 1;
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_INITIALIZING_SET, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    request[0] = 0;
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_INITIALIZING_SET, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_OK);
    assert(CAN_getOpMode(CAN0) == CAN_OPERATION_MODE_SW_INIT && response_length == 0);
    request[2] = 1;
    unchanged = controllers[0];
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_INITIALIZING_SET, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IDENTITY_GET, request, 1,
                              response, 7, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_COUNT, request, 1,
                              response, sizeof(response), &response_length) == ET_STATUS_INVALID_COMMAND);
    assert(response_length == 0);
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_OPTIONS_GET, request, 1,
                              response, sizeof(response), &response_length) == ET_STATUS_OK);
    assert(response_length == 40);
    assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_OPTIONS_GET, request, 1,
                              response, 39, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(response_length == 0);
    return 0;
}
"""
