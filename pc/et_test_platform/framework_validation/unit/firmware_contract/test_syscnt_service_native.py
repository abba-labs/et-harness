# SYSCNT正式Service与Wrap的Native契约测试。
# 职责：从注册Descriptor执行真实命令解析，核对参数、返回状态和Wire字节。
# 边界：只替换底层Chip Driver，不声明任何芯片硬件PASS。
# 依赖：本机C编译器、pytest及平台实际C头文件。

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]


# 测试 Feature：九条命令的完整Wire边界与Own Wrap调用链。
# 测试方法：
# 1. 编译真实Service/Wrap，用记录参数的Chip Driver替身接收调用。
# 2. 逐命令检查精确请求长度、输出容量、实例、有效请求和失败状态。
# 3. 比较固定Golden字节，并确认非法输入不触发硬件调用。
# 通过条件：C断言全部通过，任意失败的响应长度保持为零。
def test_syscnt_service_wire_and_wrap_contract(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")

    # 使用实际SYSCNT映射区；不要求本IP的Native桩模拟其他IP的全部SDK类型。
    chip_config = (ROOT / "firmware/chips/et6801/config/et_chip_wrap_config.h").read_text(
        encoding="utf-8"
    )
    start = chip_config.index("#define ET_CHIP_SYSCNT_FEATURE_FLAGS")
    end = chip_config.index("/* UART ", start)
    (tmp_path / "et_chip_wrap_config.h").write_text(chip_config[start:end], encoding="utf-8")
    header = tmp_path / "et6x_cortex.h"
    header.write_text(
        """
#ifndef TEST_CORTEX_H
#define TEST_CORTEX_H
#include <stdint.h>
typedef enum { DRV_OK, DRV_ERROR, DRV_PARAM_ERR, DRV_BUSY } DRV_Status;
#define SYSCNT_TEST_WORD_BITS 32u
typedef enum { SYSCNT_TEST_VIEW_CONTROL, SYSCNT_TEST_VIEW_READ } SYSCNT_TestView;
typedef struct { uint8_t enabled, halt_enabled, debug_halted; uint32_t frequency_id_hz; } SYSCNT_TestControl;
DRV_Status SYSCNT_testSetEnabled(uint8_t);
DRV_Status SYSCNT_testLoadStopped(uint64_t);
DRV_Status SYSCNT_testReadCount(SYSCNT_TestView, uint64_t *);
DRV_Status SYSCNT_testGetControl(SYSCNT_TestControl *);
DRV_Status SYSCNT_testSetHaltPolicy(uint8_t);
DRV_Status SYSCNT_testSetFrequencyId(uint32_t);
DRV_Status SYSCNT_testSetReferenceEnabled(uint8_t);
DRV_Status SYSCNT_testSampleReference(uint32_t *, uint64_t *, uint32_t *);
#endif
""",
        encoding="utf-8",
    )
    source = tmp_path / "syscnt_service.c"
    source.write_text(
        """
#include <assert.h>
#include <string.h>
#include "et6x_cortex.h"
#include "et_syscnt_service.h"
static unsigned calls, action;
static uint64_t argument;
static DRV_Status result;
static DRV_Status record(unsigned which, uint64_t value)
{ ++calls; action = which; argument = value; return result; }
DRV_Status SYSCNT_testSetEnabled(uint8_t value) { return record(1, value); }
DRV_Status SYSCNT_testLoadStopped(uint64_t value) { return record(2, value); }
DRV_Status SYSCNT_testReadCount(SYSCNT_TestView view, uint64_t *value)
{ *value = UINT64_C(0x123456789abcdef0); return record(3, view); }
DRV_Status SYSCNT_testGetControl(SYSCNT_TestControl *control)
{ control->enabled = 1; control->halt_enabled = 1; control->debug_halted = 0;
  control->frequency_id_hz = 0x12345678; return record(4, 0); }
DRV_Status SYSCNT_testSetHaltPolicy(uint8_t value) { return record(5, value); }
DRV_Status SYSCNT_testSetFrequencyId(uint32_t value) { return record(6, value); }
DRV_Status SYSCNT_testSampleReference(uint32_t *before, uint64_t *count, uint32_t *after)
{ *before = 0x12345678; *count = UINT64_C(0x123456789abcdef0); *after = 0x12345679; return record(7, 0); }
DRV_Status SYSCNT_testSetReferenceEnabled(uint8_t value) { return record(8, value); }
int main(void)
{
    et_syscnt_service_t service;
    et_irq_manager_t irq;
    et_service_factory_context_t factory = { &irq, 0 };
    const et_service_descriptor_t *descriptor;
    uint8_t request[16] = {0}, response[32];
    uint16_t length;
    const unsigned sizes[] = {1, 2, 9, 2, 1, 2, 5, 1, 2};
    const unsigned outputs[] = {8, 0, 0, 8, 8, 0, 0, 24, 0};
    const uint8_t count_bytes[] = {0xf0, 0xde, 0xbc, 0x9a, 0x78, 0x56, 0x34, 0x12};
    const uint8_t caps_bytes[] = {0x3f, 0, 0, 0, 64, 3, 32, 32};
    const uint8_t control_bytes[] = {1, 1, 0, 0, 0x78, 0x56, 0x34, 0x12};
    assert(et_syscnt_service_create(&service, 0, &factory, &descriptor) == 0);
    assert(calls == 0 && descriptor->service_id == 0x010a && descriptor->instance_id == 0);
    assert(descriptor->poll == NULL);
    assert(et_syscnt_service_init(&service, 256, &irq, 0) == -1);
    for (unsigned command = 0; command < 9; ++command)
    {
        unsigned previous = calls;
        for (unsigned size = 0; size < sizeof(request); ++size)
        {
            if (size == sizes[command]) continue;
            length = 99;
            assert(descriptor->handle(&service, command, request, size, response, sizeof(response), &length)
                   == ET_STATUS_INVALID_PARAM);
            assert(length == 0 && calls == previous);
        }
        request[0] = 1;
        assert(descriptor->handle(&service, command, request, sizes[command], response, sizeof(response), &length)
               == ET_STATUS_INVALID_PARAM);
        request[0] = 0;
        if (outputs[command])
        {
            assert(descriptor->handle(&service, command, request, sizes[command], response, outputs[command]-1, &length)
                   == ET_STATUS_INVALID_PARAM);
            assert(descriptor->handle(&service, command, request, sizes[command], NULL, outputs[command], &length)
                   == ET_STATUS_INVALID_PARAM);
        }
        assert(calls == previous);
        memset(response, 0xa5, sizeof(response));
        assert(descriptor->handle(&service, command, request, sizes[command], response, sizeof(response), &length)
               == ET_STATUS_OK);
        assert(length == outputs[command] && response[length] == 0xa5);
        if (command == 0) assert(memcmp(response, caps_bytes, sizeof(caps_bytes)) == 0);
        else assert(calls == previous + 1 && action == command);
        if (command == 3) assert(memcmp(response, count_bytes, sizeof(count_bytes)) == 0);
        if (command == 4) assert(memcmp(response, control_bytes, sizeof(control_bytes)) == 0);
        if (command == 7)
        {
            const uint8_t expected[] = {0x78,0x56,0x34,0x12,0,0,0,0,
                0xf0,0xde,0xbc,0x9a,0x78,0x56,0x34,0x12,0x79,0x56,0x34,0x12,0,0,0,0};
            assert(memcmp(response, expected, sizeof(expected)) == 0);
        }
        if (command != 0)
        {
            const DRV_Status errors[] = {DRV_BUSY, DRV_PARAM_ERR, DRV_ERROR};
            const unsigned statuses[] = {ET_STATUS_BUSY, ET_STATUS_INVALID_PARAM, ET_STATUS_INTERNAL_ERROR};
            for (unsigned i = 0; i < 3; ++i)
            {
                result = errors[i]; length = 99;
                assert(descriptor->handle(&service, command, request, sizes[command], response, sizeof(response), &length)
                       == statuses[i]);
                assert(length == 0);
            }
            result = DRV_OK;
        }
    }
    memcpy(&request[1], count_bytes, sizeof(count_bytes));
    assert(descriptor->handle(&service, 2, request, 9, NULL, 0, &length) == ET_STATUS_OK);
    assert(argument == UINT64_C(0x123456789abcdef0));
    assert(descriptor->handle(&service, 6, request, 5, NULL, 0, &length) == ET_STATUS_OK);
    assert(argument == 0x9abcdef0);
    request[1] = 1;
    assert(descriptor->handle(&service, 3, request, 2, response, 8, &length) == ET_STATUS_OK);
    assert(argument == SYSCNT_TEST_VIEW_READ);
    request[1] = 2;
    assert(descriptor->handle(&service, 3, request, 2, response, 8, &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 5, request, 2, response, 0, &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 9, request, 1, response, sizeof(response), &length) == ET_STATUS_INVALID_COMMAND);
    assert(descriptor->handle(NULL, 0, request, 1, response, 8, &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 0, NULL, 1, response, 8, &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 0, request, 1, response, 8, NULL) == ET_STATUS_INVALID_PARAM);
    assert(et_syscnt_service_create(NULL, 0, &factory, &descriptor) == -1);
    assert(et_syscnt_wrap_set_enabled(1, 1) == ET_WRAP_STATUS_NOT_SUPPORTED);
    return 0;
}
""",
        encoding="utf-8",
    )
    executable = tmp_path / "syscnt_service.exe"
    include_dirs = [
        tmp_path,
        ROOT / "firmware/services/include",
        ROOT / "firmware/wrap/include",
        ROOT / "firmware/framework/include",
        ROOT / "firmware/chips/et6801/config",
    ]
    compiled = subprocess.run(
        [
            compiler,
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            *(f"-I{directory}" for directory in include_dirs),
            str(source),
            str(ROOT / "firmware/services/src/et_syscnt_service.c"),
            str(ROOT / "firmware/wrap/src/et_syscnt_wrap.c"),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    subprocess.run([str(executable)], check=True, timeout=5)
