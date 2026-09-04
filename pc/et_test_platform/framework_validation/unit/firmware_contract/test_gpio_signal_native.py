# GPIO逻辑信号的固件契约回归；不替代引脚电气连接的真机验证。
# 职责：核对SDK信号映射、GPIO Service解码与非法请求边界。
# 边界：使用Wrap调用桩，不接入真实GPIO、不判断SPI传输结果。
# 依赖：pytest、本机C编译器及当前工程的GPIO契约头文件。
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
CONFIG = ROOT / "firmware/chips/et6801/config/et_chip_wrap_config.h"
SDK = ROOT / "firmware/chips/et6801/sdk/ET6x_Driver/Inc"


# 测试Feature：SDK所有SPI复用候选均能通过完整的GPIO、信号和实例身份查找。
# 测试方法：从SDK宏提取候选，与Chip Config逐行比较，不使用板级默认引脚代替全集。
# 通过条件：没有遗漏、额外候选、重复路由或错误实例/信号绑定。
def test_gpio_spi_signal_mapping_matches_sdk() -> None:

    expected = set(
        re.findall(
            r"#define\s+(GPIO\d+_MODE_SPI\d+_(?:CLK|CS_n|MOSI|MISO))\s",
            (SDK / "et6x_pinmap.h").read_text(encoding="utf-8"),
        )
    )
    config = CONFIG.read_text(encoding="utf-8")
    rows = re.findall(
        r"\{(GPIO\d+),\s*ET_GPIO_FUNCTION_SPI_(\w+),\s*ET6801_GPIO_SPI_INSTANCE_(\d),\s*(GPIO\d+),\s*(GPIO\d+_MODE_SPI\d+_\w+)\}",
        config,
    )
    actual = [row[4] for row in rows]
    assert expected and set(actual) == expected
    assert len(actual) == len(set(actual))

    for logical_pin, signal, instance, physical_pin, mux in rows:
        suffix = "CS_n" if signal == "CS" else signal
        assert logical_pin == physical_pin
        assert mux == f"{physical_pin}_MODE_SPI{instance}_{suffix}"


# 生成真实Service的最小Wrap桩，用调用记录判断解码与非法请求的副作用。
def write_gpio_service_harness(directory: Path) -> Path:

    for folder in (
        "firmware/framework/include",
        "firmware/services/include",
        "firmware/wrap/include",
    ):
        for header in (ROOT / folder).glob("*.h"):
            shutil.copyfile(header, directory / header.name)
    harness = directory / "gpio_service.c"
    harness.write_text(HARNESS, encoding="utf-8")
    return harness


# 测试Feature：GPIO两条命令独立派发、u16LE完整解码以及错误请求不调用Wrap。
# 测试方法：编译真实Service，依次输入Golden Vector、错误长度、未知命令和空指针。
# 通过条件：调用参数逐字段一致，返回码准确，所有响应为空，非法请求无Wrap调用。
def test_gpio_service_wire_contract(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")
    harness = write_gpio_service_harness(tmp_path)
    executable = tmp_path / "gpio_service.exe"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-I",
            str(tmp_path),
            str(ROOT / "firmware/services/src/et_gpio_service.c"),
            str(harness),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=5)


# C字符串是可执行夹具，不是Python函数文档注释。
HARNESS = r"""
#include <assert.h>
#include "et_gpio_service.h"
#include "et_gpio_wrap.h"
static unsigned validated, configured;
static et_wrap_status_t result;
et_wrap_status_t et_gpio_wrap_validate_signal(uint16_t pin, uint16_t function, uint16_t instance)
{
    assert(pin == 0x1234 && function == 0x5678 && instance == 0x9abc);
    ++validated;
    return result;
}
et_wrap_status_t et_gpio_wrap_configure_signal(uint16_t pin, uint16_t function, uint16_t instance)
{
    assert(pin == 0x1234 && function == 0x5678 && instance == 0x9abc);
    ++configured;
    return result;
}
int main(void)
{
    et_gpio_service_t service;
    uint8_t body[] = {0x34, 0x12, 0x78, 0x56, 0xbc, 0x9a};
    uint16_t length = 99;
    assert(et_gpio_service_init(&service, 1, NULL, 0) == -1);
    assert(et_gpio_service_init(&service, 0, NULL, 0) == 0);
    const et_service_descriptor_t *d = et_gpio_service_descriptor(&service);
    assert(d->service_id == 0x0014 && d->instance_id == 0);
    assert(validated == 0 && configured == 0);
    result = ET_WRAP_STATUS_OK;
    assert(d->handle(d->context, 1, body, 6, NULL, 0, &length) == ET_STATUS_OK);
    assert(validated == 1 && configured == 0 && length == 0);
    assert(d->handle(d->context, 2, body, 6, NULL, 0, &length) == ET_STATUS_OK);
    assert(validated == 1 && configured == 1 && length == 0);
    result = ET_WRAP_STATUS_NOT_SUPPORTED;
    assert(d->handle(d->context, 2, body, 6, NULL, 0, &length) == ET_STATUS_NOT_SUPPORTED);
    for (unsigned n = 0; n < 8; ++n)
    {
        if (n == 6) continue;
        assert(d->handle(d->context, 2, body, n, NULL, 0, &length) == ET_STATUS_INVALID_PARAM);
    }
    assert(d->handle(d->context, 99, body, 6, NULL, 0, &length) == ET_STATUS_NOT_SUPPORTED);
    assert(d->handle(d->context, 2, NULL, 6, NULL, 0, &length) == ET_STATUS_INVALID_PARAM);
    assert(d->handle(NULL, 2, body, 6, NULL, 0, &length) == ET_STATUS_INVALID_PARAM);
    assert(d->handle(d->context, 2, body, 6, NULL, 0, NULL) == ET_STATUS_INVALID_PARAM);
    assert(validated == 1 && configured == 2);
    return 0;
}
"""
