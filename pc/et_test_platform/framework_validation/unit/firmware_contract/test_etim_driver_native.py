# ETIM目标SDK基础动作的寄存器级软件回归。
# 职责：编译完整真实Driver，检查通道隔离、时基、计数动作和IRQ寄存器契约。
# 边界：寄存器桩不证明计数速率、锁存时序、IRQ投递或硬件PASS。
# 依赖：本机C编译器、pytest及目标CMSIS结构和位定义。

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SDK = ROOT / "firmware/chips/et6801/sdk"

# 固定向量容量来自当前基础Wire最大Body，内容由共享JSON提供。
SERVICE_VECTOR_TYPE = r"""
typedef struct {
    unsigned command, model, request_size, status, response_size;
    uint8_t request[12], response[28];
} vector_t;
"""

# 同时编译真实Service/Wrap/SDK；不会把Stub实现当成待测Service。
SERVICE_HARNESS = r"""
static void test_service(void)
{
    et_etim_service_t service;
    et_irq_manager_t manager;
    et_service_factory_context_t factory = {0};
    const et_service_descriptor_t *descriptor;
    uint8_t response[32], invalid[32] = {0};
    uint16_t length;
    factory.irq_manager = &manager;
    assert(et_etim_service_init(NULL, 0, &manager) == -1);
    assert(et_etim_service_init(&service, 0, NULL) == -1);
    assert(et_etim_service_descriptor(NULL) == NULL);
    assert(et_etim_service_create(NULL, 0, &factory, &descriptor) == -1);
    assert(et_etim_service_create(&service, 0, NULL, &descriptor) == -1);
    assert(et_etim_service_create(&service, 0, &factory, NULL) == -1);
    for (unsigned channel = 0; channel < 12; ++channel)
    {
        reads = writes = 0;
        assert(et_etim_service_create(&service, channel, &factory, &descriptor) == 0);
        assert(reads == 0 && writes == 0);
        assert(descriptor->service_id == 0x010d && descriptor->instance_id == channel);
        assert(descriptor->poll == NULL);
        for (unsigned index = 0; index < sizeof(vectors) / sizeof(vectors[0]); ++index)
        {
            const vector_t *vector = &vectors[index];
            prepare_count(channel, vector->model);
            if (vector->model == 1) registers.CORE[channel].RLCNT_RPT = 45;
            registers.CMN_INT[channel].INT_EN = 0x800;
            registers.CMN_INT[channel].INT_MASK = 8;
            registers.CMN_INT[channel].INT_RAW_RPT = 0x100;
            registers.CMN_INT[channel].INT_STATUS_RPT = 0x80;
            memset(response, 0xa5, sizeof(response));
            assert(descriptor->handle(descriptor->context, vector->command, vector->request,
                vector->request_size, response, sizeof(response), &length) == vector->status);
            assert(length == vector->response_size);
            assert(memcmp(response, vector->response, length) == 0);
            assert(response[length] == 0xa5);
            if (vector->command == 11) assert(registers.CMN_INT[channel].INT_FORCE_IND == 0x40);
            if (vector->command == 12) assert(registers.CMN_INT[channel].INT_CLR == 8);

            /* Length and output capacity checks must precede all MMIO. */
            reads = writes = 0;
            assert(descriptor->handle(descriptor->context, vector->command, invalid,
                vector->request_size + 1, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
            assert(length == 0 && reads == 0 && writes == 0);
            assert(descriptor->handle(descriptor->context, vector->command, vector->request,
                vector->request_size, response, vector->response_size - 1, &length) == ET_STATUS_INVALID_PARAM);
            assert(length == 0 && reads == 0 && writes == 0);
        }
        for (unsigned reserved = 1; reserved < 4; ++reserved)
        {
            memset(invalid, 0, sizeof(invalid));
            invalid[reserved] = 1;
            reads = writes = 0;
            assert(descriptor->handle(descriptor->context, 5, invalid, 4,
                response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
            assert(length == 0 && reads == 0 && writes == 0);
        }
    }
    reads = writes = 0;
    assert(descriptor->handle(NULL, 1, NULL, 0, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 1, NULL, 0, NULL, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 1, NULL, 0, response, sizeof(response), NULL) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 2, NULL, 12, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(&service, 99, NULL, 0, response, sizeof(response), &length) == ET_STATUS_INVALID_COMMAND);
    assert(length == 0 && reads == 0 && writes == 0);
    assert(et_etim_service_init(&service, 12, &manager) == 0);
    assert(descriptor->handle(&service, 6, NULL, 0, response, sizeof(response), &length) == ET_STATUS_INVALID_PARAM);
    assert(length == 4 && response[0] == 0xff && reads == 0 && writes == 0);
}
"""


# 测试 Feature：12通道安全索引、1..64实际分频和五种独立使能位。
# 测试方法：
# 1. 直接编译完整SDK源码；从当前CMSIS提取结构与位定义，不重写待测函数。
# 2. 遍历全部通道、分频、周期边界，以整块寄存器对比检查隔离与保留字段。
# 3. 关闭SDK断言，确认非法输入不读写MMIO，运行态配置失败且读回不是缓存。
# 4. 模拟延迟/陈旧锁存、清零未完成和回卷；检查IRQ直接写与独立状态采样。
# 通过条件：全部C断言通过；仅作为软件契约证据。
def test_etim_timebase_and_enable_contract(tmp_path: Path) -> None:
    compiler = shutil.which("gcc") or shutil.which("clang")
    if compiler is None:
        pytest.skip("native C compiler unavailable")

    cmsis = (SDK / "CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    declarations = "\n".join(
        f"typedef struct {{{body}}} {name};"
        for body, name in re.findall(
            r"typedef struct\s*\{([^{}]*)\}\s*((?:ETIMER|SPINLOCK)(?:_\w+)?_Type);", cmsis
        )
    )
    definitions = "\n".join(
        line
        for line in cmsis.splitlines()
        if re.match(r"#define\s+(?:ETIMER|SPINLOCK)_\w+_(?:Pos|Msk)\b", line)
    )
    assert "CORE[12]" in declarations and "OUT[6]" in declarations
    shutil.copyfile(SDK / "ET6x_Driver/Inc/et6x_etimer.h", tmp_path / "et6x_etimer.h")
    (tmp_path / "et6x.h").write_text(
        STUB + declarations + "\n" + definitions + "\nextern ETIMER_Type registers;\n"
        "#define ETIMER (&registers)\n",
        encoding="utf-8",
    )
    (tmp_path / "et6x_crg.h").write_text("#pragma once\n", encoding="utf-8")
    harness = tmp_path / "etim_harness.c"
    golden = json.loads(
        (
            ROOT
            / "pc/et_test_platform/framework_validation/unit/drivers/etim/etim_wire_golden.json"
        ).read_text(encoding="utf-8")
    )
    vector_rows = []
    for vector in golden:
        request = bytes.fromhex(vector["request"])
        response = bytes.fromhex(vector["response"])
        request_c = ",".join(str(value) for value in request) or "0"
        response_c = ",".join(str(value) for value in response)
        vector_rows.append(
            f"{{{vector['command']},{vector['model']},{len(request)},"
            f"{vector['status']},{len(response)},{{{request_c}}},{{{response_c}}}" + "}"
        )
    vectors = "static const vector_t vectors[] = {" + ",\n".join(vector_rows) + "};\n"
    harness.write_text(
        HARNESS + COUNT_IRQ_HARNESS + SERVICE_VECTOR_TYPE + vectors + SERVICE_HARNESS,
        encoding="utf-8",
    )
    executable = tmp_path / "etim_harness.exe"
    compiled = subprocess.run(
        [
            compiler,
            "-std=c99",
            "-DET_ENABLE_TEST_DRIVER_EXTENSIONS",
            "-O2",
            "-Werror=implicit-function-declaration",
            "-Werror=array-bounds",
            "-I",
            str(tmp_path),
            "-I",
            str(ROOT / "firmware/wrap/include"),
            "-I",
            str(ROOT / "firmware/chips/et6801/config"),
            "-I",
            str(ROOT / "firmware/services/include"),
            "-I",
            str(ROOT / "firmware/framework/include"),
            "-I",
            str(ROOT / "firmware/config"),
            str(SDK / "ET6x_Driver/Src/et6x_etimer.c"),
            str(ROOT / "firmware/wrap/src/et_etim_wrap.c"),
            str(ROOT / "firmware/services/src/et_etim_service.c"),
            str(harness),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    subprocess.run([str(executable)], check=True, timeout=5)
    # 关闭测试扩展时必须明确不支持，不能链接回旧SDK动作。
    disabled = tmp_path / "etim_disabled.c"
    disabled.write_text(
        '#include <assert.h>\n#include "et_etim_wrap.h"\n#include "et_etim_service.h"\n'
        "int main(void) { et_etim_capabilities_t caps; "
        "et_etim_service_t service; et_irq_manager_t manager; uint8_t body[28]; uint16_t length; "
        "const et_service_descriptor_t *descriptor; "
        "assert(et_etim_wrap_capabilities_get(0, &caps) == ET_WRAP_STATUS_NOT_SUPPORTED); "
        "assert(et_etim_wrap_irq_force(0, ET_ETIM_IRQ_PERIOD) == ET_WRAP_STATUS_NOT_SUPPORTED); "
        "assert(et_etim_service_init(&service, 0, &manager) == 0); "
        "descriptor = et_etim_service_descriptor(&service); "
        "assert(descriptor->handle(&service, 1, 0, 0, body, sizeof(body), &length) == ET_STATUS_NOT_SUPPORTED); "
        "assert(length == 4 && body[0] == 0xfe && body[1] == 0xff && body[2] == 0xff && body[3] == 0xff); "
        "return 0; }\n",
        encoding="utf-8",
    )
    disabled_result = subprocess.run(
        [
            compiler,
            "-std=c99",
            "-I",
            str(tmp_path),
            "-I",
            str(ROOT / "firmware/wrap/include"),
            "-I",
            str(ROOT / "firmware/chips/et6801/config"),
            "-I",
            str(ROOT / "firmware/services/include"),
            "-I",
            str(ROOT / "firmware/framework/include"),
            str(ROOT / "firmware/wrap/src/et_etim_wrap.c"),
            str(ROOT / "firmware/services/src/et_etim_service.c"),
            str(disabled),
            "-o",
            str(executable),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert disabled_result.returncode == 0, disabled_result.stdout + disabled_result.stderr
    subprocess.run([str(executable)], check=True, timeout=5)


# 只替代宿主MMIO和CMSIS访问限定符；Release态assert_param有意关闭。
STUB = r"""
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
#define __IOM volatile
#define __IM volatile
#define __OM volatile
#define __PACKED __attribute__((packed))
typedef enum {RESET, SET} FlagStatus, ITStatus;
typedef enum {DISABLE, ENABLE} FunctionalState;
typedef enum {DRV_OK, DRV_ERROR, DRV_PARAM_ERR, DRV_FAIL, DRV_TIMEOUT, DRV_BUSY} DRV_Status;
#define assert_param(v) ((void)0)
uint32_t etim_read(volatile uint32_t *reg);
void etim_write(volatile uint32_t *reg, uint32_t value);
#define READ_REG(r) etim_read(&(r))
#define WRITE_REG(r,v) etim_write(&(r),(v))
#define READ_BIT(r,m) (READ_REG(r) & (m))
#define MODIFY_REG(r,m,v) WRITE_REG(r, (READ_REG(r) & ~(m)) | (v))
#define SET_BIT(r,m) MODIFY_REG(r,0,m)
#define CLEAR_BIT(r,m) MODIFY_REG(r,m,0)
#define DRV_IS_BIT_SET(r,m) (((r) & (m)) == (m))
#define BIT_MASK(n) (UINT32_C(1) << (n))
#define POSITION_VAL(v) ((uint32_t)__builtin_ctz(v))
"""

# Expected直接来自目标布局与公开单位，不调用被测函数构造。
HARNESS = r"""
#include "et6x_etimer.h"
#include "et_etim_wrap.h"
#include "et_etim_service.h"
ETIMER_Type registers;
static unsigned reads, writes;
static unsigned model, selected, delay, samples, pulse_writes;
static void test_count_irq(void);
static void test_service(void);
uint32_t etim_read(volatile uint32_t *reg)
{
    ++reads;
    if (model && pulse_writes && reg == &registers.CORE[selected].LKCNT_RPT)
    {
        ++samples;
        if (samples >= delay)
        {
            if (model == 1) registers.CORE[selected].LKCNT_RPT = 45;
            if (model == 2) registers.CORE[selected].RLCNT_RPT = 0;
            if (model == 4) registers.CORE[selected].RLCNT_RPT = 1;
        }
    }
    return *reg;
}
void etim_write(volatile uint32_t *reg, uint32_t value)
{
    ++writes; *reg = value;
    if (model && reg == &registers.CORE[selected].PWM_CTRL)
    {
        ++pulse_writes;
        /* A zero pulse readback deliberately precedes data visibility. */
        if (model != 5) *reg &= ~0x6000u;
    }
}
int main(void)
{
    ETIMER_Type expected;
    ETIMER_TestTimeBase config, actual;
    const uint64_t periods[] = {1, 2, 1001, UINT32_MAX, UINT64_C(0x100000000)};
    uint32_t enabled;
    assert(ETIMER_CHANNEL_NUM == 12 && ETIMER_CHANNEL_ALL == 0xfff);
    assert(sizeof(registers.CORE) / sizeof(registers.CORE[0]) == ETIMER_CHANNEL_NUM);
    assert(offsetof(ETIMER_Type, OUT) == 0x244);
    assert(offsetof(ETIMER_Type, EN0) == 0x3e0);
    for (unsigned channel = 0; channel < 12; ++channel)
    {
        for (unsigned divider = 1; divider <= 64; ++divider)
        {
            for (unsigned p = 0; p < sizeof(periods) / sizeof(periods[0]); ++p)
            {
                memset(&registers, 0xa5, sizeof(registers));
                registers.EN0 &= ~(1u << channel);
                registers.CORE[channel].PWM_CTRL = 0xffffffff;
                memcpy(&expected, &registers, sizeof(expected));
                expected.CORE[channel].PWM_CTRL =
                    (0xffffffffu & ~0x3f6120u) | ((divider - 1) << 16);
                expected.CORE[channel].TIMER_CYC = (uint32_t)(periods[p] - 1);
                config.divider = divider; config.periodTicks = periods[p];
                reads = writes = 0;
                assert(ETIMER_testConfigureTimeBase(channel, &config) == DRV_OK);
                assert(writes == 2 && memcmp(&registers, &expected, sizeof(expected)) == 0);
                assert(ETIMER_testGetTimeBase(channel, &actual) == DRV_OK);
                assert(actual.divider == divider && actual.periodTicks == periods[p]);
            }
        }
        for (unsigned field = 0; field < 5; ++field)
        {
            volatile uint32_t *expected_reg;
            uint32_t mask;
            memset(&registers, 0xa5, sizeof(registers));
            memcpy(&expected, &registers, sizeof(expected));
            if (field < 2) expected_reg = &expected.EN0;
            else if (field < 4) expected_reg = &expected.EN1;
            else expected_reg = &expected.CORE[channel].CAP_CTRL;
            mask = field == 4 ? (1u << 21) : (1u << (channel + (field % 2 == 0 ? 16 : 0)));
            for (unsigned state = 0; state < 2; ++state)
            {
                *expected_reg = (*expected_reg & ~mask) | (state ? mask : 0);
                assert(ETIMER_testSetEnable(channel, (ETIMER_TestEnable)field, state) == DRV_OK);
                assert(memcmp(&registers, &expected, sizeof(expected)) == 0);
                assert(ETIMER_testGetEnable(channel, (ETIMER_TestEnable)field, &enabled) == DRV_OK);
                assert(enabled == state);
            }
        }
        config.divider = 1; config.periodTicks = 100;
        registers.EN0 |= 1u << channel;
        writes = 0;
        assert(ETIMER_testConfigureTimeBase(channel, &config) == DRV_BUSY && writes == 0);
    }
    config.divider = 1; config.periodTicks = 1;
    reads = writes = 0;
    for (unsigned channel = 12; channel <= 32; ++channel)
    {
        assert(ETIMER_testConfigureTimeBase(channel, &config) == DRV_PARAM_ERR);
        assert(ETIMER_testGetTimeBase(channel, &actual) == DRV_PARAM_ERR);
        assert(ETIMER_testSetEnable(channel, ETIMER_TEST_ENABLE_MODULE, 0) == DRV_PARAM_ERR);
        assert(ETIMER_testGetEnable(channel, ETIMER_TEST_ENABLE_MODULE, &enabled) == DRV_PARAM_ERR);
    }
    assert(ETIMER_testConfigureTimeBase(UINT32_MAX, &config) == DRV_PARAM_ERR);
    assert(ETIMER_testConfigureTimeBase(0, NULL) == DRV_PARAM_ERR);
    assert(ETIMER_testGetTimeBase(0, NULL) == DRV_PARAM_ERR);
    config.divider = 0;
    assert(ETIMER_testConfigureTimeBase(0, &config) == DRV_PARAM_ERR);
    config.divider = 65;
    assert(ETIMER_testConfigureTimeBase(0, &config) == DRV_PARAM_ERR);
    config.divider = 1; config.periodTicks = 0;
    assert(ETIMER_testConfigureTimeBase(0, &config) == DRV_PARAM_ERR);
    config.periodTicks = UINT64_C(0x100000001);
    assert(ETIMER_testConfigureTimeBase(0, &config) == DRV_PARAM_ERR);
    assert(ETIMER_testSetEnable(0, ETIMER_TEST_ENABLE_MODULE, 2) == DRV_PARAM_ERR);
    assert(ETIMER_testSetEnable(0, (ETIMER_TestEnable)5, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testSetEnable(0, (ETIMER_TestEnable)-1, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testGetEnable(0, (ETIMER_TestEnable)5, &enabled) == DRV_PARAM_ERR);
    assert(ETIMER_testGetEnable(0, ETIMER_TEST_ENABLE_MODULE, NULL) == DRV_PARAM_ERR);
    assert(reads == 0 && writes == 0);
    registers.CORE[0].PWM_CTRL = 7u << 16; registers.CORE[0].TIMER_CYC = 42;
    assert(ETIMER_testGetTimeBase(0, &actual) == DRV_OK);
    assert(actual.divider == 8 && actual.periodTicks == 43);
    registers.EN0 = 0;
    assert(ETIMER_testGetEnable(0, ETIMER_TEST_ENABLE_MODULE, &enabled) == DRV_OK && enabled == 0);
    test_count_irq();
    test_service();
    return 0;
}
"""


# 宿主模型只注入可见性/故障顺序；不据此证明真实时延或NVIC投递。
COUNT_IRQ_HARNESS = r"""
static void prepare_count(unsigned channel, unsigned behavior)
{
    memset(&registers, 0, sizeof(registers));
    selected = channel; model = behavior; delay = 3; samples = pulse_writes = 0;
    registers.EN0 = 1u << (channel + 16);
    registers.CORE[channel].PWM_CTRL = 0x000704d3;
    registers.CORE[channel].LKCNT_RPT = 7;
    registers.CORE[channel].RLCNT_RPT = 40;
    reads = writes = 0;
}
static void test_count_irq(void)
{
    ETIMER_TestCountObservation count;
    ETIMER_TestInterruptSnapshot irq;
    ETIMER_Type expected;
    uint32_t live, latched;
    for (unsigned channel = 0; channel < 12; ++channel)
    {
        prepare_count(channel, 1);
        /* Live advance is modeled before the first post-command sample. */
        registers.CORE[channel].RLCNT_RPT = 45;
        assert(ETIMER_testLatchCount(channel, 4, &count) == DRV_OK);
        assert(count.before == 45 && count.previousLatch == 7 && count.latched == 45);
        assert(count.polls == 3 && pulse_writes == 1 && writes == 1);
        assert(registers.CORE[channel].PWM_CTRL == 0x000704d3);
        model = 0;
        registers.CORE[channel].RLCNT_RPT = 50;
        assert(ETIMER_testReadCount(channel, &live, &latched) == DRV_OK);
        assert(live == 50 && latched == 45);

        prepare_count(channel, 3);
        registers.CORE[channel].LKCNT_RPT = 40; /* stale value inside envelope */
        assert(ETIMER_testLatchCount(channel, 4, &count) == DRV_TIMEOUT);
        assert(count.latched == 40 && count.live == 40 && count.polls == 4 && pulse_writes == 1);
        prepare_count(channel, 4);
        assert(ETIMER_testLatchCount(channel, 4, &count) == DRV_BUSY);
        assert(count.live == 1 && pulse_writes == 1);
        prepare_count(channel, 5);
        assert(ETIMER_testLatchCount(channel, 2, &count) == DRV_TIMEOUT);
        assert(count.polls == 2 && pulse_writes == 1);

        prepare_count(channel, 2);
        assert(ETIMER_testClearCount(channel, 4, &count) == DRV_OK);
        assert(count.before == 40 && count.live == 0 && count.polls == 3 && pulse_writes == 1);
        prepare_count(channel, 3);
        assert(ETIMER_testClearCount(channel, 4, &count) == DRV_TIMEOUT);
        assert(count.live == 40 && count.polls == 4 && pulse_writes == 1);
        prepare_count(channel, 2);
        registers.EN0 |= 1u << channel;
        assert(ETIMER_testClearCount(channel, 4, &count) == DRV_BUSY && writes == 0);
        prepare_count(channel, 2);
        registers.CORE[channel].RLCNT_RPT = 0;
        assert(ETIMER_testClearCount(channel, 4, &count) == DRV_BUSY && writes == 0);
        prepare_count(channel, 1);
        registers.EN0 = 0;
        assert(ETIMER_testLatchCount(channel, 4, &count) == DRV_BUSY && writes == 0);
        for (unsigned bit = 0; bit < 4; ++bit)
        {
            const uint32_t pending[] = {0x20, 0x1000, 0x2000, 0x4000};
            prepare_count(channel, 1);
            registers.CORE[channel].PWM_CTRL |= pending[bit];
            assert(ETIMER_testLatchCount(channel, 4, &count) == DRV_BUSY && writes == 0);
        }

        model = 0;
        for (unsigned source = 0; source < 12; ++source)
        {
            uint32_t bit = 1u << source;
            memset(&registers, 0xa5, sizeof(registers));
            memcpy(&expected, &registers, sizeof(expected));
            expected.CMN_INT[channel].INT_EN = 0xa5a5a000u | bit;
            expected.CMN_INT[channel].INT_MASK = 0xa5a5a000u | (0xfffu ^ bit);
            assert(ETIMER_testConfigureInterrupt(channel, bit, 0xfffu ^ bit) == DRV_OK);
            assert(memcmp(&registers, &expected, sizeof(expected)) == 0);
            registers.CMN_INT[channel].INT_FORCE_IND = 0xfff;
            reads = writes = 0;
            assert(ETIMER_testForceInterrupt(channel, bit) == DRV_OK);
            assert(reads == 0 && writes == 1 && registers.CMN_INT[channel].INT_FORCE_IND == bit);
            registers.CMN_INT[channel].INT_CLR = 0xfff;
            reads = writes = 0;
            assert(ETIMER_testClearInterrupt(channel, bit) == DRV_OK);
            assert(reads == 0 && writes == 1 && registers.CMN_INT[channel].INT_CLR == bit);
            registers.CMN_INT[channel].INT_RAW_RPT = 0xface0123;
            registers.CMN_INT[channel].INT_STATUS_RPT = 0xbeef0456;
            writes = 0;
            assert(ETIMER_testGetInterrupt(channel, &irq) == DRV_OK && writes == 0);
            assert(irq.enabled == bit && irq.masked == (0xfffu ^ bit));
            assert(irq.raw == 0x123 && irq.status == 0x456); /* intentionally not inferred */
        }
    }
    reads = writes = 0;
    assert(ETIMER_testReadCount(12, &live, &latched) == DRV_PARAM_ERR);
    assert(ETIMER_testReadCount(0, NULL, &latched) == DRV_PARAM_ERR);
    assert(ETIMER_testReadCount(0, &live, &live) == DRV_PARAM_ERR);
    assert(ETIMER_testLatchCount(12, 1, &count) == DRV_PARAM_ERR);
    assert(ETIMER_testLatchCount(0, 0, &count) == DRV_PARAM_ERR);
    assert(ETIMER_testLatchCount(0, ETIMER_TEST_MAX_COUNT_POLLS + 1, &count) == DRV_PARAM_ERR);
    assert(ETIMER_testClearCount(UINT32_MAX, 1, &count) == DRV_PARAM_ERR);
    assert(ETIMER_testClearCount(0, 1, NULL) == DRV_PARAM_ERR);
    assert(ETIMER_testConfigureInterrupt(12, 0, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testConfigureInterrupt(0, 0x1000, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testConfigureInterrupt(0, 0, 0x1000) == DRV_PARAM_ERR);
    assert(ETIMER_testGetInterrupt(0, NULL) == DRV_PARAM_ERR);
    assert(ETIMER_testGetInterrupt(12, &irq) == DRV_PARAM_ERR);
    assert(ETIMER_testForceInterrupt(0, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testForceInterrupt(0, 0x1000) == DRV_PARAM_ERR);
    assert(ETIMER_testClearInterrupt(0, 0) == DRV_PARAM_ERR);
    assert(ETIMER_testClearInterrupt(12, 1) == DRV_PARAM_ERR);
    assert(reads == 0 && writes == 0);
    for (unsigned channel = 0; channel < 12; ++channel)
    {
        et_etim_capabilities_t caps;
        et_etim_timebase_t config = {64, UINT64_C(0x100000000)}, actual;
        et_etim_count_observation_t observation;
        et_etim_irq_snapshot_t snapshot;
        prepare_count(channel, 0);
        assert(et_etim_wrap_capabilities_get(channel, &caps) == ET_WRAP_STATUS_OK);
        assert(caps.maximum_divider == 64 && caps.maximum_period_ticks == UINT64_C(0x100000000));
        assert(caps.maximum_count_polls == 1024 && caps.irq_sources == 0xfff);
        assert(et_etim_wrap_timebase_configure(channel, &config) == ET_WRAP_STATUS_OK);
        assert(et_etim_wrap_timebase_get(channel, &actual) == ET_WRAP_STATUS_OK);
        assert(actual.divider == config.divider && actual.period_ticks == config.period_ticks);
        for (unsigned control = 0; control < ET_ETIM_ENABLE_COUNT; ++control)
        {
            uint32_t enabled;
            assert(et_etim_wrap_enable_set(channel, control, 1) == ET_WRAP_STATUS_OK);
            assert(et_etim_wrap_enable_get(channel, control, &enabled) == ET_WRAP_STATUS_OK && enabled == 1);
        }
        prepare_count(channel, 3);
        assert(et_etim_wrap_count_latch(channel, 4, &observation) == ET_WRAP_STATUS_TIMEOUT);
        assert(observation.live == 40 && observation.previous_latched == 7 && observation.polls == 4);
        prepare_count(channel, 2);
        assert(et_etim_wrap_count_clear(channel, 4, &observation) == ET_WRAP_STATUS_OK && observation.live == 0);
        model = 0;
        assert(et_etim_wrap_irq_configure(channel, ET_ETIM_IRQ_CAPTURE_4, ET_ETIM_IRQ_COMPARE_ERROR) == ET_WRAP_STATUS_OK);
        assert(registers.CMN_INT[channel].INT_EN == 0x800 && registers.CMN_INT[channel].INT_MASK == 8);
        registers.CMN_INT[channel].INT_RAW_RPT = 0x800;
        registers.CMN_INT[channel].INT_STATUS_RPT = 8;
        assert(et_etim_wrap_irq_snapshot_get(channel, &snapshot) == ET_WRAP_STATUS_OK);
        assert(snapshot.raw == ET_ETIM_IRQ_CAPTURE_4 && snapshot.status == ET_ETIM_IRQ_COMPARE_ERROR);
        assert(et_etim_wrap_irq_force(channel, ET_ETIM_IRQ_PERIOD) == ET_WRAP_STATUS_OK);
        assert(registers.CMN_INT[channel].INT_FORCE_IND == 0x40);
        assert(et_etim_wrap_irq_clear(channel, ET_ETIM_IRQ_COMPARE_ERROR) == ET_WRAP_STATUS_OK);
        assert(registers.CMN_INT[channel].INT_CLR == 8);
    }
    reads = writes = 0;
    assert(et_etim_wrap_irq_force(12, ET_ETIM_IRQ_PERIOD) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(et_etim_wrap_irq_configure(0, 0x1000, 0) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(et_etim_wrap_enable_set(0, (et_etim_enable_t)-1, 1) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(et_etim_wrap_count_get(0, &live, &live) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    assert(reads == 0 && writes == 0);
}
"""
