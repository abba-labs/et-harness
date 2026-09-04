# SPI Chip Driver原子动作的软件回归。
# 职责：编译真实SDK源码，用寄存器桩验证边界、读清副作用和无等待行为。
# 边界：不模拟串行波形，不把寄存器桩通过当作FPGA通过。
# 依赖：本机C编译器、pytest及目标芯片生成头文件。

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SDK = ROOT / "firmware/chips/et6801/sdk"
DRIVER = SDK / "ET6x_Driver/Src/et6x_spi.c"
WRAP = ROOT / "firmware/wrap/src/et_spi_wrap.c"
SERVICE = ROOT / "firmware/services/src/et_spi_service.c"


# 为真实Driver提供最小总线桩；位定义直接来自目标生成头，不能在测试里另造位号。
def write_spi_harness(directory: Path) -> Path:

    header = (SDK / "ET6x_Driver/Inc/et6x_spi.h").read_text(encoding="utf-8")
    cmsis = (SDK / "CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    source = DRIVER.read_text(encoding="utf-8")
    fields = sorted(set(re.findall(r"SPIx->(\w+)", source)) - {"DR"})
    definitions = "\n".join(
        line for line in cmsis.splitlines() if re.match(r"#define\s+SPI0_", line)
    )
    (directory / "et6x_spi.h").write_text(header, encoding="utf-8")
    # 使用真实实例映射及公共头，避免在桩里另建一套Wrap契约。
    for name in ("et_spi_wrap.h", "et_wrap_status.h", "et_irq_types.h"):
        shutil.copyfile(ROOT / "firmware/wrap/include" / name, directory / name)
    shutil.copyfile(
        ROOT / "firmware/services/include/et_spi_service.h", directory / "et_spi_service.h"
    )
    shutil.copyfile(
        ROOT / "firmware/services/include/et_service_factory.h", directory / "et_service_factory.h"
    )
    for name in (
        "et_service_router.h",
        "et_message.h",
        "et_irq_manager.h",
        "et_test_protocol_config.h",
    ):
        shutil.copyfile(ROOT / "firmware/framework/include" / name, directory / name)
    chip_config = (SDK.parent / "config/et_chip_wrap_config.h").read_text(encoding="utf-8")
    spi_macros = re.findall(
        r"^#define ET_CHIP_SPI_\w+[^\n]*(?:\n(?<=\\\n)[^\n]*)*", chip_config, re.MULTILINE
    )
    assert spi_macros
    (directory / "et_chip_wrap_config.h").write_text("\n".join(spi_macros) + "\n", encoding="utf-8")
    irq_lines = re.findall(r"^\s*(SPI[0-3]_IRQn\s*=\s*\d+),", cmsis, re.MULTILINE)
    assert len(irq_lines) == 4
    (directory / "et6x.h").write_text(
        "#pragma once\n#include <stdint.h>\n#include <stdbool.h>\n"
        "#include <stddef.h>\n#include <assert.h>\n"
        "#define __PACKED\n#define assert_param(x) assert(x)\n"
        "#define UNUSED(x) ((void)(x))\n" + "enum {" + ",".join(irq_lines) + "};\n"
        "typedef enum { DISABLE, ENABLE } ControlStatus;\n"
        "typedef enum { RESET, SET } FlagStatus;\n"
        "typedef enum { DRV_OK, DRV_PARAM_ERR, DRV_BUSY } DRV_Status;\n"
        "typedef struct { uint32_t DR[1]; "
        + " ".join(f"uint32_t {field};" for field in fields)
        + " } SPI_Type;\nextern SPI_Type registers[4];\n"
        + "\n".join(f"#define SPI{i} (&registers[{i}])" for i in range(4))
        + "\nuint32_t bus_read(uint32_t *address);\n"
        "#define READ_REG(r) bus_read(&(r))\n"
        "#define READ_BIT(r,m) (READ_REG(r) & (m))\n"
        "#define WRITE_REG(r,v) ((r) = (v))\n"
        "#define MODIFY_REG(r,m,v) ((r) = ((r) & ~(m)) | (v))\n"
        "#define SET_BIT(r,m) ((r) |= (m))\n"
        "#define CLEAR_BIT(r,m) ((r) &= ~(m))\n" + definitions + "\n",
        encoding="utf-8",
    )
    (directory / "et6x_crg.h").write_text(
        "#include <stdint.h>\nuint32_t CRG_getAPB3Clock(void);\n", encoding="utf-8"
    )
    harness = directory / "spi_driver_harness.c"
    harness.write_text(HARNESS, encoding="utf-8")
    return harness


# 测试Feature：帧数/偶数分频、FIFO阈值、正常/错误访问及TX/RX独立DMA请求。
# 测试方法：1. 编译完整真实Driver；2. 遍历合法边界和非法参数；3. 记录SR/DR读取次数。
# 通过条件：配置读回准确，非法输入无副作用，普通查询不清错误，非阻塞写能及时返回。
def test_spi_driver_atomic_register_contract(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")
    harness = write_spi_harness(tmp_path)
    executable = tmp_path / "spi_driver.exe"
    subprocess.run(
        [
            compiler,
            "-std=c11",
            "-DET_ENABLE_TEST_DRIVER_EXTENSIONS",
            "-I",
            str(tmp_path),
            str(DRIVER),
            str(WRAP),
            str(SERVICE),
            str(harness),
            "-o",
            str(executable),
        ],
        check=True,
        timeout=30,
    )
    subprocess.run([str(executable)], check=True, timeout=5)


# C源码字符串是可执行测试夹具，不是Python文档注释。
HARNESS = r"""
#include "et6x_spi.h"
#include "et_spi_wrap.h"
#include "et_spi_service.h"
#include <string.h>
SPI_Type registers[4];
static unsigned sr_reads, dr_reads, clear_reads;
static uint32_t input_clock = 25000000;
static et_irq_callback_t bound_callback;
static void *bound_context;
static et_irq_route_t bound_route;
static unsigned unbind_fail;
static unsigned bind_fail;
static unsigned dispatch_during_bind;
uint32_t et_irq_manager_enter_critical(void) { return 0; }
void et_irq_manager_exit_critical(uint32_t key) { (void)key; }
int et_irq_manager_bind(et_irq_manager_t *m, const et_irq_route_t *r, uint8_t p,
                        et_irq_callback_t cb, void *ctx)
{
    (void)p;
    if (bind_fail == 1) { return -1; }
    assert(!bound_callback);
    bound_callback = cb; bound_context = ctx; bound_route = *r;
    m->bindings[0].in_use = 1;
    m->bindings[0].irq_line = r->irq_line;
    m->bindings[0].callback = cb;
    m->bindings[0].context = ctx;
    if (dispatch_during_bind) { cb(ctx, r->irq_line, r->route_events); }
    return bind_fail == 2 ? -1 : 0;
}
int et_irq_manager_unbind(et_irq_manager_t *m, et_irq_line_t line, et_irq_callback_t cb, void *ctx)
{
    assert(bound_callback == cb && bound_context == ctx && line == bound_route.irq_line);
    if (unbind_fail) { return -1; }
    bound_callback = NULL; bound_context = NULL;
    memset(&m->bindings[0], 0, sizeof(m->bindings[0]));
    return 0;
}
static void verify_service(void)
{
    et_spi_service_t service;
    et_irq_manager_t manager = {0};
    const et_service_descriptor_t *d;
    uint8_t request[65] = {0}, response[64] = {0};
    uint16_t length = 0;
    unsigned words[] = ET_SPI_REQUEST_WORD_COUNTS;
    et_service_factory_context_t factory_context = {&manager, 2};
    SPI_Type initial = registers[0];
    assert(et_spi_service_create(&service, 0, &factory_context, &d) == 0);
    assert(d == &service.descriptor && memcmp(&initial, &registers[0], sizeof(initial)) == 0);
    assert(et_spi_service_create(&service, 0, NULL, &d) == -1);
    assert(et_spi_service_init(&service, 0, &manager, 2) == 0);
    d = et_spi_service_descriptor(&service);
    assert(d && d->service_id == 0x010b && d->poll == NULL);
    for (unsigned command = 0; command < ET_SPI_COMMAND_COUNT; ++command)
    {
        SPI_Type saved = registers[0];
        unsigned correct = 1 + 4 * words[command];
        assert(d->handle(&service, command, request, correct - 1, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
        assert(length == 0 && memcmp(&saved, &registers[0], sizeof(saved)) == 0);
    }
    assert(d->handle(&service, ET_SPI_COMMAND_COUNT, request, 1, response, sizeof(response), &length) == ET_STATUS_INVALID_COMMAND);
    request[0] = 1;
    assert(d->handle(&service, 0, request, 1, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    request[0] = 0;
    assert(d->handle(&service, 0, request, 1, response, 27, &length) == ET_STATUS_INVALID_PARAM);
    assert(d->handle(&service, 0, request, 1, response, sizeof(response), &length) == ET_STATUS_OK && length == 28);
    assert(response[0] == 4 && response[4] == 16 && response[8] == 32);
    assert(d->handle(&service, ET_SPI_COMMAND_FIFO_LIMITS_GET, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(length == 20 && response[0] == 15 && response[4] == 15 && response[8] == 15 && response[12] == 15 && response[16] == 15);
    request[1] = 0; request[2] = 1; /* u32 256 must not truncate to false. */
    assert(d->handle(&service, 3, request, 5, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    request[2] = 0;
    assert(d->handle(&service, 3, request, 5, response, sizeof(response), &length) == ET_STATUS_OK);
    /* Same independently specified Config golden vector as the PC Wire test. */
    const uint32_t config_words[16] = {1,0,2,0,0,8,17,4,1,0,0,8,0,0,0,0};
    for (unsigned n = 0; n < 16; ++n)
    {
        for (unsigned byte = 0; byte < 4; ++byte)
        {
            request[1 + n * 4 + byte] = (uint8_t)(config_words[n] >> (byte * 8));
        }
    }
    assert(d->handle(&service, 1, request, 65, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(d->handle(&service, 2, request, 1, response, sizeof(response), &length) == ET_STATUS_OK && length == 64);
    assert(memcmp(request + 1, response, 64) == 0);
    memset(request, 0, sizeof(request));
    request[1] = ET_SPI_IRQ_RX_FULL | ET_SPI_IRQ_TX_OVERFLOW;
    registers[0].IMR = SPI0_IMR_RXFIM_Msk;
    clear_reads = 0;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(bound_callback && service.event.generation == 1);
    assert(clear_reads == 0 && registers[0].IMR == SPI0_IMR_RXFIM_Msk);
    registers[0].ISR = registers[0].RISR = SPI0_IMR_RXFIM_Msk;
    registers[0].SR = SPI0_SR_TXE_Msk;
    registers[0].RXFLR = 4;
    sr_reads = dr_reads = 0;
    bound_callback(bound_context, bound_route.irq_line, bound_route.route_events);
    assert(service.event.event_count == 1 && service.event.masked_status == ET_SPI_IRQ_RX_FULL);
    assert(service.event.latched_events == ET_SPI_IRQ_RX_FULL && service.event.fault_flags == 0);
    assert((registers[0].IMR & SPI0_IMR_RXFIM_Msk) == 0 && registers[0].RXFLR == 4);
    assert(sr_reads == 0 && dr_reads == 0);
    assert(d->handle(&service, 22, request, 1, response, sizeof(response), &length) == ET_STATUS_OK && length == 32);
    assert(response[0] == ET_SPI_IRQ_RX_FULL && response[12] == 1 && response[24] == 1);
    assert(d->handle(&service, 23, request, 1, response, sizeof(response), &length) == ET_STATUS_BUSY);
    service.event.event_count = UINT32_MAX;
    bound_callback(bound_context, bound_route.irq_line, bound_route.route_events);
    assert(service.event.event_count == UINT32_MAX && service.event.overflow_count == 1);
    unbind_fail = 1;
    assert(d->handle(&service, 21, request, 1, response, sizeof(response), &length) == ET_STATUS_INTERNAL_ERROR);
    assert(service.bound && registers[0].IMR == 0);
    unbind_fail = 0;
    assert(d->handle(&service, 21, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(!service.bound && !bound_callback);
    assert(d->handle(&service, 23, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(service.event.generation == 2 && service.event.event_count == 0 && service.event.fault_flags == 0);
    /* Rejected before allocation must not create phantom Service ownership. */
    bind_fail = 1;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_INTERNAL_ERROR);
    assert(!service.bound && !bound_callback && registers[0].IMR == 0);
    assert(service.event.fault_flags == ET_SPI_CAPTURE_FAULT_IO);
    bind_fail = 0;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(d->handle(&service, 21, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    /* Partial allocation with failed rollback must retain retryable ownership. */
    bind_fail = 2; unbind_fail = 1;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_INTERNAL_ERROR);
    assert(service.bound && bound_callback && registers[0].IMR == 0);
    bind_fail = 0; unbind_fail = 0;
    assert(d->handle(&service, 21, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(!service.bound && !bound_callback);
    /* Successful rollback after partial allocation leaves no stale binding. */
    bind_fail = 2;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_INTERNAL_ERROR);
    assert(!service.bound && !bound_callback && registers[0].IMR == 0);
    bind_fail = 0;
    /* An active source may dispatch before bind returns; do not undo ISR masking. */
    dispatch_during_bind = 1;
    registers[0].ISR = registers[0].RISR = registers[0].IMR = SPI0_IMR_RXFIM_Msk;
    assert(d->handle(&service, 20, request, 5, response, sizeof(response), &length) == ET_STATUS_OK);
    assert(service.event.event_count == 1 && registers[0].IMR == 0);
    assert(d->handle(&service, 21, request, 1, response, sizeof(response), &length) == ET_STATUS_OK);
    dispatch_during_bind = 0;
}
uint32_t CRG_getAPB3Clock(void) { return input_clock; }
uint32_t bus_read(uint32_t *address)
{
    uint32_t result = *address;
    for (unsigned i = 0; i < 4; ++i)
    {
        if (address == &registers[i].SR)
        {
            ++sr_reads;
            *address &= ~(SPI0_SR_TXE_Msk | SPI0_SR_DCOL_Msk);
        }
        if (address == &registers[i].DR[0]) { ++dr_reads; }
        if (address == &registers[i].TXEICR || address == &registers[i].RXOICR ||
            address == &registers[i].RXUICR || address == &registers[i].MSTICR)
        { ++clear_reads; }
    }
    return result;
}
int main(void)
{
    SPI_TestSnapshot snapshot;
    uint32_t value = 0;
    uint8_t count = 0, threshold = 0;
    SPI_Config config;
    for (unsigned i = 0; i < 4; ++i)
    {
        SPI_Type *spi = &registers[i];
        memset(spi, 0, sizeof(*spi));
        assert(SPI_testSetFrameCount(spi, 1) == DRV_OK && spi->CTRLR1 == 0);
        assert(SPI_testSetFrameCount(spi, 65536) == DRV_OK && spi->CTRLR1 == 65535);
        assert(SPI_testSetFrameCount(spi, 0) == DRV_PARAM_ERR && spi->CTRLR1 == 65535);
        assert(SPI_testSetFrameCount(spi, 65537) == DRV_PARAM_ERR);
        assert(SPI_testSetDivider(spi, 2) == DRV_OK && spi->BAUDR == 2);
        assert(SPI_testSetDivider(spi, 65534) == DRV_OK && spi->BAUDR == 65534);
        assert(SPI_testSetDivider(spi, 3) == DRV_PARAM_ERR && spi->BAUDR == 65534);
        assert(SPI_testSetDivider(spi, 0) == DRV_PARAM_ERR);
        assert(SPI_testSetDivider(spi, 65536) == DRV_PARAM_ERR);

        SPI_setBaudRate(spi, 8000000);
        assert(spi->BAUDR == 4); /* ceil(25/8), not floor(25/8) rounded down. */
        SPI_setBaudRate(spi, 50000000);
        assert(spi->BAUDR == 2);
        SPI_setBaudRate(spi, 1);
        assert(spi->BAUDR == 2); /* Too slow cannot be represented: no mutation. */
        SPI_initStruct(&config);
        config.bitRate = 8000000;
        SPI_setConfig(spi, &config);
        assert(spi->BAUDR == 4);

        for (unsigned tx = 0; tx < 16; ++tx)
        {
            unsigned start = 15 - tx;
            SPI_setFIFOInterruptLevel(spi, tx, 0);
            SPI_setTansferStartFIFOLevel(spi, start);
            SPI_getTansferStartFIFOLevel(spi, &threshold);
            assert(threshold == start);
            assert((spi->TXFTLR & SPI0_TXFTLR_TFT_Msk) == tx);
        }
        for (unsigned tx = 0; tx <= 1; ++tx)
        {
            for (unsigned rx = 0; rx <= 1; ++rx)
            {
                assert(SPI_testConfigureDMA(spi, tx, rx, 15, 0) == DRV_OK);
                assert(spi->DMACR == ((tx ? SPI0_DMACR_TDMAE_Msk : 0) |
                                      (rx ? SPI0_DMACR_RDMAE_Msk : 0)));
            }
        }
        value = spi->DMACR;
        assert(SPI_testConfigureDMA(spi, 0, 0, 16, 0) == DRV_PARAM_ERR);
        assert(spi->DMACR == value && spi->DMATDLR == 15);
        assert(SPI_testConfigureDMA(spi, 2, 0, 0, 0) == DRV_PARAM_ERR);

        SPI_enableModule(spi);
        assert(SPI_testSetFrameCount(spi, 1) == DRV_BUSY);
        assert(SPI_testSetDivider(spi, 2) == DRV_BUSY);
        assert(SPI_testSelectCS(spi, 0) == DRV_OK && spi->SSIENR == 1);
        assert(SPI_testSelectCS(spi, 1) == DRV_OK && spi->SER == 1);
        assert(SPI_testSelectCS(spi, 2) == DRV_PARAM_ERR && spi->SER == 1);
        spi->SR = SPI0_SR_BUSY_Msk | SPI0_SR_TXE_Msk | SPI0_SR_DCOL_Msk;
        spi->TXFLR = 32;
        spi->RXFLR = 0;
        sr_reads = dr_reads = 0;
        assert(SPI_testGetSnapshot(spi, &snapshot) == DRV_OK);
        assert(SPI_testTryWriteFrame(spi, 0x1357, &count) == DRV_OK && count == 0);
        assert(SPI_testTryReadFrame(spi, &value, &count) == DRV_OK && count == 0);
        assert(sr_reads == 0 && dr_reads == 0);
        spi->TXFLR = 15;
        assert(SPI_testTryWriteFrame(spi, 0x1357, &count) == DRV_OK && count == 1);
        assert(spi->DR[0] == 0x1357);
        spi->RXFLR = 1;
        assert(SPI_testTryReadFrame(spi, &value, &count) == DRV_OK && count == 1);
        assert(value == 0x1357 && dr_reads == 1 && sr_reads == 0);
        SPI_writeDataNonBlocking(spi, 0x2468); /* BUSY stays set: must not wait. */
        assert(spi->DR[0] == 0x2468 && sr_reads == 0);
        assert(SPI_testReadStatus(spi, &value) == DRV_OK && sr_reads == 1);
        assert((value & SPI0_SR_TXE_Msk) != 0 && (value & SPI0_SR_DCOL_Msk) != 0);
        assert(SPI_testReadStatus(spi, &value) == DRV_OK && value == SPI0_SR_BUSY_Msk);
        spi->TXFLR = 32;
        spi->RXFLR = 0;
        assert(SPI_testWriteFIFOOnce(spi, 0xabcd) == DRV_OK && spi->DR[0] == 0xabcd);
        assert(SPI_testReadFIFOOnce(spi, &value) == DRV_OK && value == 0xabcd);
        assert(SPI_testGetSnapshot(spi, NULL) == DRV_PARAM_ERR);
        assert(SPI_testReadStatus(spi, NULL) == DRV_PARAM_ERR);
        assert(SPI_testTryWriteFrame(spi, 0, NULL) == DRV_PARAM_ERR);
        assert(SPI_testTryReadFrame(spi, NULL, &count) == DRV_PARAM_ERR);
        assert(SPI_testReadFIFOOnce(spi, NULL) == DRV_PARAM_ERR);

        /* Run the public Wrap against the same real Driver and instance mapping. */
        assert(et_spi_wrap_set_enabled(i, 2) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_spi_wrap_set_enabled(i, 0) == ET_WRAP_STATUS_OK && spi->SSIENR == 0);
        assert(et_spi_wrap_set_divider(i, 4) == ET_WRAP_STATUS_OK && spi->BAUDR == 4);
        assert(et_spi_wrap_set_divider(i, 3) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_spi_wrap_set_frame_count(i, 65536) == ET_WRAP_STATUS_OK);
        assert(et_spi_wrap_set_frame_count(i, 0) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_spi_wrap_set_enabled(i, 1) == ET_WRAP_STATUS_OK);
        assert(et_spi_wrap_set_divider(i, 4) == ET_WRAP_STATUS_BUSY);
        assert(et_spi_wrap_set_cs_selected(i, 1) == ET_WRAP_STATUS_OK && spi->SER == 1);
        assert(et_spi_wrap_configure_dma(i, 1, 0, 15, 0) == ET_WRAP_STATUS_OK);
        assert(spi->DMACR == SPI0_DMACR_TDMAE_Msk);
        sr_reads = dr_reads = 0;
        spi->TXFLR = 0;
        assert(et_spi_wrap_try_write_frame(i, 0x3210, &count) == ET_WRAP_STATUS_OK);
        assert(count == 1 && spi->DR[0] == 0x3210);
        spi->RXFLR = 1;
        assert(et_spi_wrap_try_read_frame(i, &value, &count) == ET_WRAP_STATUS_OK);
        assert(count == 1 && value == 0x3210 && sr_reads == 0);
        assert(et_spi_wrap_test_fifo_write_once(i, 0xabcd) == ET_WRAP_STATUS_OK);
        assert(et_spi_wrap_test_fifo_read_once(i, &value) == ET_WRAP_STATUS_OK);
        assert(value == 0xabcd && sr_reads == 0);
        assert(et_spi_wrap_reset_fifo(i) == ET_WRAP_STATUS_OK && spi->SSIENR == 1);

        /* Complete configuration comes from readback, not a cached request. */
        et_spi_config_t requested = {0}, observed;
        et_spi_snapshot_t facts;
        et_spi_limits_t limits;
        et_irq_route_t route;
        uintptr_t endpoint = 0;
        uint32_t flags = 0;
        requested.frame_bits = 8;
        requested.frame_count = 17;
        requested.divider = 4;
        requested.target_output_enabled = 1;
        requested.control_bits = 8;
        assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_BUSY);
        assert(et_spi_wrap_set_enabled(i, 0) == ET_WRAP_STATUS_OK);
        for (unsigned role = 0; role < 2; ++role)
        {
            for (unsigned mode = 0; mode < 4; ++mode)
            {
                for (unsigned bits = 4; bits <= 16; ++bits)
                {
                    requested.role = role;
                    requested.clock_mode = mode;
                    requested.frame_bits = bits;
                    sr_reads = dr_reads = 0;
                    assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_OK);
                    assert(et_spi_wrap_get_config(i, &observed) == ET_WRAP_STATUS_OK);
                    assert(memcmp(&requested, &observed, sizeof(requested)) == 0);
                    assert(sr_reads == 0 && dr_reads == 0);
                }
            }
        }
        for (unsigned format = 0; format < 3; ++format)
        {
            requested.frame_format = format;
            requested.target_output_enabled = 0;
            requested.rx_sample_delay = 255;
            requested.sequential = requested.transmit = requested.handshake = 1;
            assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_OK);
            assert(et_spi_wrap_get_config(i, &observed) == ET_WRAP_STATUS_OK);
            assert(memcmp(&requested, &observed, sizeof(requested)) == 0);
            assert((spi->CTRLR0 & SPI0_CTRLR0_SLV_OE_Msk) != 0);
        }
        SPI_Type saved = *spi;
        requested.reserved = 1;
        assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        requested.reserved = 0;
        requested.frame_bits = 3;
        assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        requested.frame_bits = 8;
        requested.cs_policy = ET_SPI_CS_TOGGLE;
        assert(et_spi_wrap_configure(i, &requested) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&saved, spi, sizeof(saved)) == 0);
        assert(et_spi_wrap_set_loopback(i, 1) == ET_WRAP_STATUS_OK);
        assert((spi->CTRLR0 & SPI0_CTRLR0_SRL_Msk) != 0);
        assert(et_spi_wrap_set_fifo_thresholds(i, 2, 3, 4) == ET_WRAP_STATUS_OK);
        assert(et_spi_wrap_set_fifo_thresholds(i, 16, 3, 4) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_spi_wrap_set_irq_enabled(i, ET_SPI_IRQ_ALL, 0) == ET_WRAP_STATUS_OK);
        assert(et_spi_wrap_set_irq_enabled(i, ET_SPI_IRQ_RX_FULL, 1) == ET_WRAP_STATUS_OK);
        spi->RISR = spi->ISR = SPI0_IMR_RXFIM_Msk;
        sr_reads = dr_reads = 0;
        assert(et_spi_wrap_get_snapshot(i, &facts) == ET_WRAP_STATUS_OK);
        assert(facts.tx_threshold == 2 && facts.rx_threshold == 3 && facts.start_threshold == 4);
        assert(facts.irq_raw == ET_SPI_IRQ_RX_FULL && facts.irq_status == ET_SPI_IRQ_RX_FULL);
        assert(facts.irq_enabled == ET_SPI_IRQ_RX_FULL && sr_reads == 0 && dr_reads == 0);
        spi->SR = SPI0_SR_BUSY_Msk | SPI0_SR_TXE_Msk | SPI0_SR_DCOL_Msk;
        assert(et_spi_wrap_read_error_status(i, &value, &flags) == ET_WRAP_STATUS_OK);
        assert(flags == (ET_SPI_STATUS_BUSY | ET_SPI_STATUS_TARGET_TX_ERROR | ET_SPI_STATUS_COLLISION));
        assert(sr_reads == 1 && spi->SR == SPI0_SR_BUSY_Msk);
        assert(et_spi_wrap_get_dma_endpoint(i, &endpoint) == ET_WRAP_STATUS_OK);
        assert(endpoint == (uintptr_t)&spi->DR[0] && dr_reads == 0);
        assert(et_spi_wrap_get_irq_route(i, &route) == ET_WRAP_STATUS_OK);
        assert(route.route_events == ET_SPI_IRQ_ALL);
        assert(et_spi_wrap_get_limits(i, &limits) == ET_WRAP_STATUS_OK);
        assert(limits.fifo_depth == 32 && limits.frame_count_max == 65536);
        et_spi_fifo_limits_t fifo_limits;
        assert(et_spi_wrap_get_fifo_limits(i, &fifo_limits) == ET_WRAP_STATUS_OK);
        assert(fifo_limits.tx_irq_max == 15 && fifo_limits.rx_irq_max == 15 && fifo_limits.tx_start_max == 15);
        assert(fifo_limits.dma_tx_max == 15 && fifo_limits.dma_rx_max == 15);
    }
    assert(et_spi_wrap_set_enabled(UINT16_MAX, 1) == ET_WRAP_STATUS_NOT_SUPPORTED);
    assert(et_spi_wrap_try_read_frame(UINT16_MAX, &value, &count) == ET_WRAP_STATUS_NOT_SUPPORTED);
    verify_service();
    return 0;
}
"""
