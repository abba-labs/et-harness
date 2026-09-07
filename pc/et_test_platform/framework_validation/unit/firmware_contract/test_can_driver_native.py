# CAN SDK驱动的寄存器级软件回归。
# 职责：编译完整真实Driver，验证三实例隔离、FDOE查询和时间戳分频边界。
# 边界：寄存器桩不模拟CAN总线，不替代FPGA收发或ECC硬件验证。
# 依赖：本机C编译器及ET6801生成头文件中的真实位定义。

import os
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
    irq_definitions = "\n".join(
        f"#define {name} {value}"
        for name, value in re.findall(r"\b(CAN[0-2]_INT[01]_IRQn|CAN_ECC_IRQn)\s*=\s*(\d+)", cmsis)
    )
    # DMUIR虽不被当前原语读取，仍保留在桩中作为无副作用哨兵。
    fields = sorted(set(re.findall(r"CANx->(\w+)", source)) | {"DMUIR"})
    stub = (
        "#pragma once\n#include <stdint.h>\n#include <stddef.h>\n#include <assert.h>\n"
        "#define assert_param(v) assert(v)\n#define DRV_OK 0\n#define DRV_ERROR (-1)\n"
        "uint32_t can_test_read(volatile uint32_t *address);\n"
        "void can_test_write(volatile uint32_t *address, uint32_t value);\n"
        "#define READ_REG(r) can_test_read(&(r))\n#define WRITE_REG(r,v) can_test_write(&(r),(v))\n"
        "#define READ_BIT(r,m) (READ_REG(r)&(m))\n"
        "#define MODIFY_REG(r,m,v) ((r)=((r)&~(m))|(v))\n"
        "#define SET_BIT(r,m) ((r)|=(m))\n#define CLEAR_BIT(r,m) ((r)&=~(m))\n"
        "#define REG32(a) (*(uint32_t *)(uintptr_t)(a))\n"
        "typedef struct { " + " ".join(f"uint32_t {field};" for field in fields) + " } CAN_Type;\n"
        "typedef struct {uint32_t MISC_STATUS, MISC_CTRL, DMU_DMA_CFG; "
        "uint32_t MTTCAN_INT_EN, MTTCAN_INT_MASK, MTTCAN_INT_FORCE, MTTCAN_INT_CLR; "
        "uint32_t MTTCAN_INT_RSTATUS, MTTCAN_INT_MSTATUS;} CAN_MISC_Type;\n"
        "typedef struct {uint32_t ECCEN;} SYSC_Type;\n"
        # CAN0前保留16KiB真实宿主内存，验证SDK地址偏移和RAM编码；其他实例仅测寄存器隔离。
        "typedef struct {uint8_t ram[16384]; CAN_Type blocks[3];} CAN_TestMemory;\n"
        "extern CAN_TestMemory test_memory;\n#define controllers test_memory.blocks\n"
        "extern CAN_MISC_Type misc_blocks[3];\n"
        "extern SYSC_Type system_control;\n#define SYSC (&system_control)\n"
        + "\n".join(
            f"#define CAN{index} (&controllers[{index}])\n"
            f"#define CAN_MISC{index} (&misc_blocks[{index}])"
            for index in range(3)
        )
        + "\n"
        + definitions
        + "\n"
        + irq_definitions
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
            # SDK使用32-bit地址；仅此临时Native测试映像放在32-bit可表示区，不修改正式链接。
            *(
                ["-Wl,--image-base,0x10000000", "-Wl,--disable-dynamicbase"]
                if os.name == "nt"
                else ["-no-pie"]
            ),
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
CAN_TestMemory test_memory;
CAN_MISC_Type misc_blocks[3];
SYSC_Type system_control;

/* The Service is tested with a bounded host-side IRQ Manager double. */
static et_irq_callback_t bound_callback[6];
static void *bound_context[6];
static et_irq_line_t bound_irq_line[6];
static uint32_t bound_route_events[6];
static unsigned fail_unbind_once;
static unsigned fail_bind_mode;

uint32_t et_irq_manager_enter_critical(void)
{
    return 0;
}

void et_irq_manager_exit_critical(uint32_t key)
{
    (void)key;
}

int et_irq_manager_bind(et_irq_manager_t *manager, const et_irq_route_t *route, uint8_t priority,
                        et_irq_callback_t callback, void *context)
{
    unsigned slot;

    (void)manager;
    (void)priority;
    if (fail_bind_mode==1) { fail_bind_mode=0; return -1; }

    for (slot = 0; slot < 6; ++slot)
    {
        if (bound_callback[slot] == NULL)
        {
            bound_callback[slot] = callback;
            bound_context[slot] = context;
            bound_irq_line[slot] = route->irq_line;
            bound_route_events[slot] = route->route_events;
            manager->bindings[slot].in_use=1;
            manager->bindings[slot].callback=callback;
            manager->bindings[slot].context=context;
            manager->bindings[slot].irq_line=route->irq_line;
            if (fail_bind_mode==2) { fail_bind_mode=0; fail_unbind_once=1; return -1; }

            return 0;
        }
    }

    return -1;
}

int et_irq_manager_unbind(et_irq_manager_t *manager, et_irq_line_t irq_line,
                          et_irq_callback_t callback, void *context)
{
    unsigned slot;

    (void)manager;
    if (fail_unbind_once) { fail_unbind_once=0; return -1; }

    for (slot = 0; slot < 6; ++slot)
    {
        if ((bound_callback[slot] == callback) && (bound_context[slot] == context) &&
            (bound_irq_line[slot] == irq_line))
        {
            bound_callback[slot] = NULL;
            bound_context[slot] = NULL;
            bound_irq_line[slot] = 0;
            bound_route_events[slot] = 0;
            memset(&manager->bindings[slot], 0, sizeof(manager->bindings[slot]));

            return 0;
        }
    }

    return -1;
}

/* Optional ECR.CEL read-clear model catches accidental repeated reads in a getter. */
static unsigned consume_enabled, ecr_reads, psr_reads, txbc_reads;
static unsigned ram_trace_enabled, ram_trace_count;
static uintptr_t ram_trace[4];
static unsigned timeout_write_count;
static unsigned timestamp_snapshot_model, timestamp_write_count;
static unsigned tsu_slot_reads, tsu_status_reads;
static unsigned ecc_status_model;
static unsigned dmu_counter_reads;
void can_test_write(volatile uint32_t *address, uint32_t value)
{
    for (unsigned i=0; i<3; ++i)
    {
        if (address == &misc_blocks[i].MTTCAN_INT_FORCE)
        {
            misc_blocks[i].MTTCAN_INT_RSTATUS |= value;
            *address = 0;
            return;
        }
        if (address == &misc_blocks[i].MTTCAN_INT_CLR)
        {
            misc_blocks[i].MTTCAN_INT_RSTATUS &= ~value;
            *address = 0;
            return;
        }
        if (timestamp_snapshot_model && address == &controllers[i].TSCV)
        {
            assert(value == 0);
            ++timestamp_write_count;
            *address = 1U;
            return;
        }
        if (address == &controllers[i].TOCV)
        {
            assert(value == 0);
            ++timeout_write_count;
            /* One simulated tick after reload proves the response is a read, not TOP echo. */
            *address = (controllers[i].TOCC >> 16) - 1U;
            return;
        }
    }
    *address = value;
}
uint32_t can_test_read(volatile uint32_t *address)
{
    uint32_t value=*address;
    for (unsigned i=0; i<3; ++i)
    {
        if (address == &controllers[i].DMUQC) { ++dmu_counter_reads; }
        if (ecc_status_model && address == &misc_blocks[i].MTTCAN_INT_MSTATUS)
        {
            return misc_blocks[i].MTTCAN_INT_RSTATUS & misc_blocks[i].MTTCAN_INT_EN &
                ~misc_blocks[i].MTTCAN_INT_MASK;
        }
        if (address == &controllers[i].TS0)
        {
            ++tsu_slot_reads;
            controllers[i].TSS1 &= ~0x00010001U;
        }
        if (address == &controllers[i].TSS1) { ++tsu_status_reads; }
    }
    if (ram_trace_enabled && (uintptr_t)address >= (uintptr_t)test_memory.ram &&
        (uintptr_t)address < (uintptr_t)CAN0 && ram_trace_count < 4)
    {
        ram_trace[ram_trace_count++] = (uintptr_t)address - (uintptr_t)test_memory.ram;
    }
    if (address==&CAN0->TXBC) { ++txbc_reads; }
    if (consume_enabled && address==&CAN0->ECR)
    {
        ++ecr_reads;
        *address &= ~0x00FF0000U;
    }
    if (consume_enabled && address==&CAN0->PSR) { ++psr_reads; }
    return value;
}

/* Software register model only: no IRQ delivery or RAM correction is claimed. */
static void test_ecc_register_contract(void)
{
    CAN_Type *instances[] = {CAN0, CAN1, CAN2};
    CAN_TestEccSnapshot snapshot;
    et_can_ecc_snapshot_t public_snapshot;
    CAN_MISC_Type saved[3];
    for (unsigned i=0; i<3; ++i)
    {
        for (uint32_t source=1; source<=2; ++source)
        {
            uint32_t other=3U ^ source;
            memset(misc_blocks, 0, sizeof(misc_blocks));
            misc_blocks[i].MTTCAN_INT_EN=0x80;
            misc_blocks[i].MTTCAN_INT_MASK=0x43;
            system_control.ECCEN=0x12345678;
            assert(CAN_testForceEcc(instances[i], 3)==DRV_OK);
            assert(misc_blocks[i].MTTCAN_INT_FORCE==0);
            assert(CAN_testSetEccEnabled(instances[i], source, 1)==DRV_OK);
            assert(CAN_testSetEccMasked(instances[i], source, 0)==DRV_OK);
            assert(misc_blocks[i].MTTCAN_INT_EN==(0x80 | source));
            assert(misc_blocks[i].MTTCAN_INT_MASK==(0x40 | other));
            /* Deliberately independent MSTATUS proves the getter reads it, not recomputes it. */
            misc_blocks[i].MTTCAN_INT_MSTATUS=other;
            assert(CAN_testGetEccSnapshot(instances[i], &snapshot)==DRV_OK);
            assert(snapshot.raw==3 && snapshot.status==other);
            assert(snapshot.enabled==source && snapshot.masked==other);
            assert(CAN_testClearEcc(instances[i], source)==DRV_OK);
            assert(misc_blocks[i].MTTCAN_INT_CLR==0);
            assert(misc_blocks[i].MTTCAN_INT_RSTATUS==other);
            assert(CAN_testForceEcc(instances[i], source)==DRV_OK);
            assert(misc_blocks[i].MTTCAN_INT_RSTATUS==3);
            assert(CAN_testSetEccMasked(instances[i], source, 1)==DRV_OK);
            assert(CAN_testSetEccEnabled(instances[i], source, 0)==DRV_OK);
            assert(misc_blocks[i].MTTCAN_INT_EN==0x80);
            assert(misc_blocks[i].MTTCAN_INT_MASK==0x43);
            assert(system_control.ECCEN==0x12345678);
            for (unsigned j=0; j<3; ++j)
            {
                if (j!=i) { CAN_MISC_Type zero={0}; assert(memcmp(&misc_blocks[j], &zero, sizeof(zero))==0); }
            }
            memcpy(saved, misc_blocks, sizeof(saved));
            assert(CAN_testSetEccEnabled(instances[i], 0, 1)==DRV_ERROR);
            assert(CAN_testSetEccEnabled(instances[i], source, 2)==DRV_ERROR);
            assert(CAN_testSetEccMasked(instances[i], 4, 1)==DRV_ERROR);
            assert(CAN_testSetEccMasked(instances[i], source, 2)==DRV_ERROR);
            assert(CAN_testForceEcc(instances[i], 4)==DRV_ERROR);
            assert(CAN_testClearEcc(instances[i], 0)==DRV_ERROR);
            assert(CAN_testGetEccSnapshot(instances[i], NULL)==DRV_ERROR);
            assert(memcmp(saved, misc_blocks, sizeof(saved))==0);
            assert(et_can_wrap_clear_ecc(i, ET_CAN_ECC_ALL)==ET_WRAP_STATUS_OK);
            assert(et_can_wrap_force_ecc(i, source)==ET_WRAP_STATUS_OK);
            assert(et_can_wrap_set_ecc_enabled(i, source, 1)==ET_WRAP_STATUS_OK);
            assert(et_can_wrap_set_ecc_masked(i, source, 0)==ET_WRAP_STATUS_OK);
            assert(et_can_wrap_get_ecc_snapshot(i, &public_snapshot)==ET_WRAP_STATUS_OK);
            assert(public_snapshot.raw==source && public_snapshot.status==other);
            assert(public_snapshot.enabled==source && public_snapshot.masked==other);
            memcpy(saved, misc_blocks, sizeof(saved));
            assert(et_can_wrap_force_ecc(i, 4)==ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(et_can_wrap_clear_ecc(i, 0)==ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(et_can_wrap_set_ecc_enabled(i, 1, 2)==ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(et_can_wrap_set_ecc_masked(i, 4, 1)==ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(et_can_wrap_get_ecc_snapshot(i, NULL)==ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(et_can_wrap_force_ecc(99, 1)==ET_WRAP_STATUS_NOT_SUPPORTED);
            assert(et_can_wrap_clear_ecc(99, 1)==ET_WRAP_STATUS_NOT_SUPPORTED);
            assert(et_can_wrap_set_ecc_enabled(99, 1, 1)==ET_WRAP_STATUS_NOT_SUPPORTED);
            assert(et_can_wrap_set_ecc_masked(99, 1, 1)==ET_WRAP_STATUS_NOT_SUPPORTED);
            assert(et_can_wrap_get_ecc_snapshot(99, &public_snapshot)==ET_WRAP_STATUS_NOT_SUPPORTED);
            assert(memcmp(saved, misc_blocks, sizeof(saved))==0);
        }
    }
    assert(CAN_testSetEccEnabled(NULL, 1, 1)==DRV_ERROR);
    assert(CAN_testSetEccMasked(NULL, 1, 1)==DRV_ERROR);
    assert(CAN_testForceEcc(NULL, 1)==DRV_ERROR);
    assert(CAN_testClearEcc(NULL, 1)==DRV_ERROR);
    assert(CAN_testGetEccSnapshot(NULL, &snapshot)==DRV_ERROR);
    memset(misc_blocks, 0, sizeof(misc_blocks));
}

/* Exercise the real Service callbacks through a shared-line Manager double. */
static void test_ecc_session_contract(void)
{
    et_can_service_t services[3];
    et_irq_manager_t manager={0};
    uint8_t request[9]={0}, response[36];
    uint16_t length=0;
    ecc_status_model=1;
    for (unsigned mode=1; mode<=2; ++mode)
    {
        assert(et_can_service_init(&services[0], 0, &manager, 2)==0);
        request[0]=0; request[1]=1;
        fail_bind_mode=mode;
        assert(services[0].descriptor.handle(&services[0], 75, request, 5, NULL, 0, &length)==ET_STATUS_INTERNAL_ERROR);
        assert(services[0].ecc_bound==(mode==2));
        assert(services[0].descriptor.handle(&services[0], 76, request, 1, NULL, 0, &length)==0);
        assert(services[0].ecc_bound==0 && services[0].ecc_watched==0);
        assert(services[0].descriptor.handle(&services[0], 75, request, 5, NULL, 0, &length)==0);
        assert(services[0].descriptor.handle(&services[0], 76, request, 1, NULL, 0, &length)==0);
    }
    for (unsigned target=0; target<3; ++target)
    {
        for (uint32_t source=1; source<=2; ++source)
        {
            uint32_t other=3 ^ source;
            memset(misc_blocks, 0, sizeof(misc_blocks));
            for (unsigned i=0; i<3; ++i)
            {
                assert(et_can_service_init(&services[i], i, &manager, 2)==0);
                request[0]=i; request[1]=source;
                assert(services[i].descriptor.handle(&services[i], 75, request, 5, NULL, 0, &length)==0);
                assert(services[i].ecc_event[6]==1 && services[i].ecc_event[8]==UINT32_MAX);
                assert(misc_blocks[i].MTTCAN_INT_EN==source && misc_blocks[i].MTTCAN_INT_MASK==source);
                assert(services[i].descriptor.handle(&services[i], 78, request, 1, NULL, 0, &length)==ET_STATUS_BUSY);
            }
            request[0]=target; request[1]=3;
            assert(services[target].descriptor.handle(&services[target], 72, request, 5, NULL, 0, &length)==0);
            for (unsigned slot=0; slot<6; ++slot)
            {
                if (bound_callback[slot])
                {
                    assert(bound_irq_line[slot]==CAN_ECC_IRQn);
                    bound_callback[slot](bound_context[slot], bound_irq_line[slot], bound_route_events[slot]);
                }
            }
            for (unsigned i=0; i<3; ++i) { assert(services[i].ecc_event[3]==0); }
            request[1]=source; request[5]=0;
            assert(services[target].descriptor.handle(&services[target], 71, request, 9, NULL, 0, &length)==0);
            for (unsigned slot=0; slot<6; ++slot)
            {
                if (bound_callback[slot])
                {
                    bound_callback[slot](bound_context[slot], bound_irq_line[slot], bound_route_events[slot]);
                }
            }
            for (unsigned i=0; i<3; ++i)
            {
                assert(services[i].ecc_event[3]==(i==target ? 1 : 0));
                assert(services[i].ecc_event[7]==0);
            }
            assert(services[target].ecc_event[0]==3 && services[target].ecc_event[1]==source);
            assert(services[target].ecc_event[2]==source && services[target].ecc_event[8]==target);
            assert(misc_blocks[target].MTTCAN_INT_RSTATUS==3);
            assert(services[target].descriptor.handle(&services[target], 77, request, 1, response, 35, &length)==ET_STATUS_INVALID_PARAM);
            assert(length==0);
            assert(services[target].descriptor.handle(&services[target], 77, request, 1, response, 36, &length)==0);
            assert(length==36 && response[12]==1 && response[32]==target);
            assert(services[target].descriptor.handle(&services[target], 73, request, 5, NULL, 0, &length)==0);
            assert(misc_blocks[target].MTTCAN_INT_RSTATUS==other);
            assert(services[target].descriptor.handle(&services[target], 72, request, 5, NULL, 0, &length)==0);
            assert(services[target].descriptor.handle(&services[target], 71, request, 9, NULL, 0, &length)==0);
            for (unsigned slot=0; slot<6; ++slot)
            {
                if (bound_callback[slot])
                {
                    bound_callback[slot](bound_context[slot], bound_irq_line[slot], bound_route_events[slot]);
                }
            }
            assert(services[target].ecc_event[3]==2 && services[target].irq_event[3]==0);
            services[target].ecc_event[3]=UINT32_MAX;
            assert(services[target].descriptor.handle(&services[target], 71, request, 9, NULL, 0, &length)==0);
            for (unsigned slot=0; slot<6; ++slot)
            {
                if (bound_context[slot]==&services[target])
                {
                    bound_callback[slot](bound_context[slot], bound_irq_line[slot], bound_route_events[slot]);
                    assert(services[target].ecc_event[3]==UINT32_MAX);
                    assert(services[target].ecc_event[5]==1 && services[target].ecc_event[7]==ET_CAN_IRQ_FAULT_OVERFLOW);
                    assert(services[target].descriptor.handle(&services[target], 71, request, 9, NULL, 0, &length)==0);
                    bound_callback[slot](bound_context[slot], CAN0_INT0_IRQn, bound_route_events[slot]);
                    assert(services[target].ecc_event[4]==1);
                    assert(services[target].ecc_event[7]==(ET_CAN_IRQ_FAULT_OVERFLOW | ET_CAN_IRQ_FAULT_UNEXPECTED));
                }
            }
            assert(services[target].descriptor.handle(&services[target], 72, request, 6, NULL, 0, &length)==ET_STATUS_INVALID_PARAM);
            request[5]=2;
            assert(services[target].descriptor.handle(&services[target], 70, request, 9, NULL, 0, &length)==ET_STATUS_INVALID_PARAM);
            request[5]=0;
            for (unsigned i=0; i<3; ++i)
            {
                request[0]=i;
                fail_unbind_once=1;
                assert(services[i].descriptor.handle(&services[i], 76, request, 1, NULL, 0, &length)==ET_STATUS_INTERNAL_ERROR);
                assert(services[i].ecc_bound==1 && misc_blocks[i].MTTCAN_INT_EN==0);
                assert(services[i].descriptor.handle(&services[i], 76, request, 1, NULL, 0, &length)==0);
                assert(services[i].ecc_bound==0 && misc_blocks[i].MTTCAN_INT_EN==0);
                assert(services[i].descriptor.handle(&services[i], 78, request, 1, NULL, 0, &length)==0);
                assert(services[i].ecc_event[6]==2 && services[i].ecc_event[8]==UINT32_MAX);
            }
            assert(misc_blocks[target].MTTCAN_INT_RSTATUS==3);
        }
    }
    ecc_status_model=0;
    memset(misc_blocks, 0, sizeof(misc_blocks));
}

/* Independent register and Wire vectors; no CAN bus or external input is simulated. */
static void test_tsu_contract(void)
{
    et_can_tsu_limits_t limits;
    et_can_tsu_config_t config = {1, 0, 0, 4}, actual;
    uint32_t new_flags, lost_flags, value;
    for (unsigned i=0; i<3; ++i)
    {
        CAN_Type *can = &controllers[i];
        for (unsigned count=0; count<3; ++count)
        {
            for (unsigned generic=0; generic<4; ++generic)
            {
                can->TSS2 = (count << 12) | (generic << 14);
                assert(et_can_wrap_get_tsu_limits(i, &limits) == ET_WRAP_STATUS_OK);
                assert(limits.slots == (4U << count));
                assert(limits.internal == (generic & 1));
                assert(limits.sof == (generic >> 1));
            }
        }
        can->TSS2 = 0x3000;
        assert(et_can_wrap_get_tsu_limits(i, &limits) == ET_WRAP_STATUS_STATE_ERROR);
        can->TSS2 = 0xD000;
        for (unsigned cce=0; cce<2; ++cce)
        {
            can->CCCR = 0x8001 | (cce << 1);
            assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_OK);
            assert(can->TSCFG == 0x301 && can->CCCR == (0x8001 | (cce << 1)));
            assert(et_can_wrap_get_tsu(i, &actual) == ET_WRAP_STATUS_OK);
            assert(actual.enabled == 1 && actual.external == 0 && actual.sof == 0);
            assert(actual.divisor == 4);
        }
        can->CCCR = 0;
        can->TSCFG = 0xAB00;
        assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_STATE_ERROR);
        assert(can->TSCFG == 0xAB00);
        can->CCCR = 1;
        can->TSS2 = 0x9000; /* SOF available, internal timebase absent. */
        assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_STATE_ERROR);
        assert(can->TSCFG == 0xAB00);
        config.external=1; config.sof=1; config.divisor=256;
        assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_OK);
        assert(can->TSCFG == 0xFF07);
        can->TSS2 = 0x5000;
        assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_STATE_ERROR);
        config.sof=0; config.external=0; config.divisor=0;
        assert(et_can_wrap_set_tsu(i, &config) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        config.divisor=4;
        can->TSS1 = 0x008100A5; can->TS0=0x12345678; can->ATB=0x89ABCDEF;
        tsu_slot_reads=0; tsu_status_reads=0;
        assert(et_can_wrap_get_tsu_flags(i, &new_flags, &lost_flags) == ET_WRAP_STATUS_OK);
        assert(new_flags==0xA5 && lost_flags==0x81 && tsu_status_reads==1 && tsu_slot_reads==0);
        assert(et_can_wrap_read_tsu_value(i, 0, &value) == ET_WRAP_STATUS_OK);
        assert(value==0x89ABCDEF && tsu_slot_reads==0 && can->TSS1==0x008100A5);
        assert(et_can_wrap_read_tsu_value(i, 1, &value) == ET_WRAP_STATUS_OK);
        assert(value==0x12345678 && tsu_slot_reads==1 && can->TSS1==0x008000A4);
        et_can_service_t service;
        et_irq_manager_t manager={0};
        uint8_t request[17]={i, 1,0,0,0, 0,0,0,0, 0,0,0,0, 4,0,0,0};
        uint8_t response[16];
        uint16_t length;
        assert(et_can_service_init(&service, i, &manager, 1)==0);
        const et_service_descriptor_t *desc=et_can_service_descriptor(&service);
        assert(desc->handle(desc->context,64,request,17,response,16,&length)==ET_STATUS_OK);
        assert(length==0 && can->TSCFG==0x301);
        assert(desc->handle(desc->context,65,request,1,response,16,&length)==ET_STATUS_OK);
        assert(length==16 && memcmp(response,&request[1],16)==0);
        assert(desc->handle(desc->context,66,request,1,response,16,&length)==ET_STATUS_OK);
        assert(length==12 && response[0]==8 && response[4]==1 && response[8]==0);
        can->TSS1=0x00010001;
        assert(desc->handle(desc->context,67,request,1,response,16,&length)==ET_STATUS_OK);
        assert(length==8 && response[0]==1 && response[4]==1 && can->TSS1==0x00010001);
        assert(desc->handle(desc->context,68,request,1,response,16,&length)==ET_STATUS_OK);
        assert(length==4 && memcmp(response,"\xEF\xCD\xAB\x89",4)==0);
        tsu_slot_reads=0;
        assert(desc->handle(desc->context,69,request,1,response,3,&length)==ET_STATUS_INVALID_PARAM);
        assert(tsu_slot_reads==0 && length==0);
        assert(desc->handle(desc->context,69,request,1,response,16,&length)==ET_STATUS_OK);
        assert(length==4 && memcmp(response,"\x78\x56\x34\x12",4)==0);
        assert(tsu_slot_reads==1 && can->TSS1==0);
        assert(desc->handle(desc->context,64,request,16,response,16,&length)==ET_STATUS_INVALID_PARAM);
        memset(can,0,sizeof(*can));
    }
}

/* DMA addresses are resolved only; the host must never dereference a virtual window. */
static void test_dmu_primitives(void)
{
    CAN_Type *instances[] = {CAN0, CAN1, CAN2};
    const uint32_t offsets[] = {0x200, 0x280, 0x300, 0x380};
    CAN_MISC_Type saved_misc[3];
    CAN_Type saved_can[3];
    CAN_TestDmuCounters counters;
    CAN_DMURxRequest request;
    uint32_t address;
    memset(controllers, 0, sizeof(controllers));
    memset(misc_blocks, 0, sizeof(misc_blocks));
    for (unsigned i=0; i<3; ++i)
    {
        CAN_Type *can=instances[i];
        can->DMUQC=0xFE807F01U;
        can->DMUIR=0x12345678U;
        can->DMUC=1;
        for (unsigned j=0; j<3; ++j) { misc_blocks[j].DMU_DMA_CFG=0xA5A500CFU+j; }
        memcpy(saved_can, controllers, sizeof(saved_can));
        memcpy(saved_misc, misc_blocks, sizeof(saved_misc));
        for (unsigned element=0; element<4; ++element)
        {
            assert(CAN_testGetDmuEndpoint(can, (CAN_TestDmuElement)element, &address)==DRV_OK);
            assert(address==(uintptr_t)can+offsets[element]);
        }
        address=0xDEADBEEFU;
        assert(CAN_testGetDmuEndpoint(can, (CAN_TestDmuElement)4, &address)==DRV_ERROR);
        assert(CAN_testGetDmuEndpoint(can, (CAN_TestDmuElement)-1, &address)==DRV_ERROR);
        assert(address==0xDEADBEEFU);
        assert(CAN_testGetDmuEndpoint(can, CAN_TEST_DMU_TX, NULL)==DRV_ERROR);
        dmu_counter_reads=0;
        assert(CAN_testGetDmuCounters(can, &counters)==DRV_OK);
        assert(dmu_counter_reads==1);
        assert(counters.txEnqueued==1 && counters.rx0Dequeued==127);
        assert(counters.rx1Dequeued==128 && counters.txEventDequeued==254);
        assert(CAN_testGetDmuCounters(can, NULL)==DRV_ERROR && dmu_counter_reads==1);
        assert(memcmp(saved_can, controllers, sizeof(saved_can))==0);
        assert(memcmp(saved_misc, misc_blocks, sizeof(saved_misc))==0);
        for (unsigned selection=0; selection<3; ++selection)
        {
            assert(CAN_testSetDmuRxRequest(can, (CAN_DMURxRequest)selection)==DRV_OK);
            assert(misc_blocks[i].DMU_DMA_CFG==((saved_misc[i].DMU_DMA_CFG&~0x30U)|(selection<<4)));
            request=CAN_DMU_REQ_TXER;
            assert(CAN_testGetDmuRxRequest(can, &request)==DRV_OK && (unsigned)request==selection);
            for (unsigned j=0; j<3; ++j)
            {
                if (j!=i) { assert(memcmp(&saved_misc[j], &misc_blocks[j], sizeof(saved_misc[j]))==0); }
            }
        }
        memcpy(saved_misc, misc_blocks, sizeof(saved_misc));
        assert(CAN_testSetDmuRxRequest(can, (CAN_DMURxRequest)3)==DRV_ERROR);
        assert(CAN_testSetDmuRxRequest(can, (CAN_DMURxRequest)-1)==DRV_ERROR);
        assert(CAN_testGetDmuRxRequest(can, NULL)==DRV_ERROR);
        assert(memcmp(saved_misc, misc_blocks, sizeof(saved_misc))==0);
        /* Independent register mutation proves GET does not echo the last successful SET. */
        misc_blocks[i].DMU_DMA_CFG &= ~0x30U;
        assert(CAN_testGetDmuRxRequest(can, &request)==DRV_OK && request==CAN_DMU_REQ_RX0R);
        misc_blocks[i].DMU_DMA_CFG |= 0x30U;
        request=CAN_DMU_REQ_RX1R;
        assert(CAN_testGetDmuRxRequest(can, &request)==DRV_ERROR && request==CAN_DMU_REQ_RX1R);
        assert(memcmp(saved_can, controllers, sizeof(saved_can))==0);
    }
    assert(CAN_testGetDmuEndpoint(NULL, CAN_TEST_DMU_TX, &address)==DRV_ERROR);
    assert(CAN_testGetDmuCounters(NULL, &counters)==DRV_ERROR);
    assert(CAN_testGetDmuRxRequest(NULL, &request)==DRV_ERROR);
    assert(CAN_testSetDmuRxRequest(NULL, CAN_DMU_REQ_RX0R)==DRV_ERROR);
    memset(controllers, 0, sizeof(controllers));
    memset(misc_blocks, 0, sizeof(misc_blocks));
}

int main(void)
{
    test_dmu_primitives();
    test_tsu_contract();
    test_ecc_register_contract();
    test_ecc_session_contract();
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
    uint8_t request[97] = {0};
    uint8_t response[96];
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
        /* Explicit format selection preserves unrelated controls and CCE. */
        et_can_event_format_t format = {16, 0}, format_actual;
        uint32_t format_before = instances[index]->CCCR;
        assert(et_can_wrap_set_event_format(index, &format) == ET_WRAP_STATUS_OK);
        assert(instances[index]->CCCR == (format_before | CAN0_CCCR_WMM_Msk));
        assert(et_can_wrap_get_event_format(index, &format_actual) == ET_WRAP_STATUS_OK);
        assert(format_actual.marker_bits == 16 && format_actual.tsu_enabled == 0);
        format.tsu_enabled=1;
        assert(et_can_wrap_set_event_format(index, &format) == ET_WRAP_STATUS_OK);
        assert(instances[index]->CCCR == (format_before | CAN0_CCCR_WMM_Msk | CAN0_CCCR_UTSU_Msk));
        format.marker_bits=8;
        assert(et_can_wrap_set_event_format(index, &format) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        format.tsu_enabled=0;
        assert(et_can_wrap_set_event_format(index, &format) == ET_WRAP_STATUS_OK);
        assert(instances[index]->CCCR == format_before);
        /* Non-ISO selection changes only NISO, preserving CCE and other instances. */
        for (unsigned permission = 0; permission < 2; ++permission)
        {
            instances[index]->CCCR = CAN0_CCCR_INIT_Msk | CAN0_CCCR_DAR_Msk |
                (permission ? CAN0_CCCR_CCE_Msk : 0);
            uint32_t before_format = instances[index]->CCCR;
            assert(et_can_wrap_non_iso_access(index, 1, NULL) == ET_WRAP_STATUS_OK);
            assert(instances[index]->CCCR == (before_format | CAN0_CCCR_NISO_Msk));
            assert(et_can_wrap_non_iso_access(index, 0, &initializing) == ET_WRAP_STATUS_OK);
            assert(initializing == 1);
            assert(et_can_wrap_non_iso_access(index, 0, NULL) == ET_WRAP_STATUS_OK);
            assert(instances[index]->CCCR == before_format);
            assert(et_can_wrap_non_iso_access(index, 2, NULL) == ET_WRAP_STATUS_INVALID_ARGUMENT);
            assert(instances[index]->CCCR == before_format);
            assert(instances[(index + 1) % 3]->CCCR == 0);
        }
        instances[index]->CCCR = CAN0_CCCR_DAR_Msk;
        assert(et_can_wrap_non_iso_access(index, 1, NULL) == ET_WRAP_STATUS_STATE_ERROR);
        assert(instances[index]->CCCR == CAN0_CCCR_DAR_Msk);
        assert(et_can_wrap_non_iso_access(99, 1, NULL) == ET_WRAP_STATUS_NOT_SUPPORTED);
        assert(et_can_wrap_set_initializing(index, 1) == ET_WRAP_STATUS_OK);
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
    assert(descriptor->handle(descriptor->context, 57, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_OK);
    assert(response_length == 0 && (controllers[0].CCCR & CAN0_CCCR_NISO_Msk));
    assert(descriptor->handle(descriptor->context, 58, request, 1,
                              response, 4, &response_length) == ET_STATUS_OK);
    assert(response_length == 4 && response[0] == 1 && response[1] == 0 &&
           response[2] == 0 && response[3] == 0);
    unchanged = controllers[0];
    request[1] = 2;
    assert(descriptor->handle(descriptor->context, 57, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(response_length == 0 && memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
    assert(descriptor->handle(descriptor->context, 57, request, 4,
                              NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(descriptor->handle(descriptor->context, 58, request, 1,
                              response, 3, &response_length) == ET_STATUS_INVALID_PARAM);
    assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
    request[1] = 0;
    assert(descriptor->handle(descriptor->context, 57, request, 5,
                              NULL, 0, &response_length) == ET_STATUS_OK);
    assert(!(controllers[0].CCCR & CAN0_CCCR_NISO_Msk));
    request[1] = 1;
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

    /* RAM configuration clears disabled sections and rejects TX overflow before writes. */
    {
        CAN_MsgRAMConfigParams ram = {0};
        CAN_MsgRAMConfigParams actual;
        et_can_ram_layout_t layout = {
            .std_offset=0, .std_count=2, .ext_offset=8, .ext_count=2,
            .tx_offset=24, .tx_buffer_count=2, .tx_fifo_count=0, .tx_queue=0,
            .tx_payload_bytes=64, .event_offset=168, .event_count=2, .event_watermark=1,
            .rx0_offset=184, .rx0_count=4, .rx0_watermark=2, .rx0_overwrite=0,
            .rx1_offset=472, .rx1_count=4, .rx1_watermark=2, .rx1_overwrite=1,
            .rx_buffer_offset=760, .rx_buffer_payload_bytes=64,
            .rx0_payload_bytes=64, .rx1_payload_bytes=64
        };
        et_can_ram_layout_t readback;
        et_can_ram_limits_t limits;
        const uint32_t words[] = {
            0,2,8,2,24,2,0,0,64,168,2,1,184,4,2,0,472,4,2,1,760,64,64,64
        };

        memset(&controllers[0], 0, sizeof(controllers[0]));
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);
        ram.lss=2; ram.lse=2; ram.rxFIFO0size=4; ram.rxFIFO1size=4;
        ram.txEventFIFOSize=2; ram.txBufNum=2;
        assert(CAN_msgRAMConfig(CAN0, &ram) == DRV_OK);
        unchanged = controllers[0];
        ram.txBufNum=32; ram.txFIFOSize=1;
        assert(CAN_msgRAMConfig(CAN0, &ram) == DRV_ERROR);
        assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
        assert(CAN_msgRAMConfig(CAN0, NULL) == DRV_ERROR);
        memset(&ram, 0, sizeof(ram));
        assert(CAN_msgRAMConfig(CAN0, &ram) == DRV_OK);
        CAN_testGetMsgRAMConfig(CAN0, &actual);
        assert(actual.lss==0 && actual.lse==0 && actual.rxFIFO0size==0);
        assert(actual.rxFIFO1size==0 && actual.txEventFIFOSize==0 && actual.txBufNum==0);

        assert(et_can_wrap_get_ram_limits(0, &limits) == ET_WRAP_STATUS_OK);
        assert(limits.ram_bytes==16384 && limits.rx_buffer_count==64);
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_ram_layout(0, &readback) == ET_WRAP_STATUS_OK);
        assert(memcmp(&layout, &readback, sizeof(layout)) == 0);
        unchanged = controllers[0];
        layout.tx_offset=0; /* Collision with active standard filters. */
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
        layout=readback; layout.rx_buffer_offset=limits.ram_bytes-4;
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        layout=readback; layout.tx_payload_bytes=9;
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        layout=readback; layout.rx0_count=65;
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        layout=readback; layout.tx_queue=2;
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        layout=readback; layout.std_offset=1;
        assert(et_can_wrap_set_ram_layout(0, &layout) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_NORMAL);
        assert(et_can_wrap_set_ram_layout(0, &readback) == ET_WRAP_STATUS_STATE_ERROR);
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);

        /* Service codec checks complete 97-byte SET and 96-byte GET independently. */
        request[0]=0;
        for (unsigned i=0; i<24; ++i)
        {
            for (unsigned byte=0; byte<4; ++byte)
            {
                request[1+i*4+byte]=(uint8_t)(words[i]>>(byte*8));
            }
        }
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RAM_LAYOUT_SET,
                                  request, 97, NULL, 0, &response_length) == ET_STATUS_OK);
        assert(response_length == 0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RAM_LAYOUT_GET,
                                  request, 1, response, 96, &response_length) == ET_STATUS_OK);
        assert(response_length==96 && memcmp(response, request+1, 96)==0);
        unchanged=controllers[0];
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RAM_LAYOUT_SET,
                                  request, 96, NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
        assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged))==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RAM_LAYOUT_GET,
                                  request, 1, response, 95, &response_length) == ET_STATUS_INVALID_PARAM);
        assert(response_length==0);
    }


    /* Each read comes from hardware, and loopback transitions clear stale MON. */
    {
        et_can_bus_config_t bus = {
            .monitor=0, .restricted=0, .timestamp_divisor=16,
            .timestamp_source=ET_CAN_TIMESTAMP_INTERNAL,
            .timeout_source=ET_CAN_TIMEOUT_RX1, .timeout_period=65535,
            .timeout_enabled=1, .reject_remote_ext=1, .reject_remote_std=1,
            .unmatched_ext=ET_CAN_UNMATCHED_REJECT, .unmatched_std=ET_CAN_UNMATCHED_RX1
        };
        et_can_bus_config_t observed;
        et_can_bus_limits_t limits;
        et_can_loopback_t loop;
        const uint32_t bus_words[] = {0,0,16,1,3,65535,1,1,1,2,1};

        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);
        assert(et_can_wrap_set_bus_config(0, &bus) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_bus_config(0, &observed) == ET_WRAP_STATUS_OK);
        assert(memcmp(&bus, &observed, sizeof(bus)) == 0);
        assert(et_can_wrap_get_bus_limits(0, &limits) == ET_WRAP_STATUS_OK);
        assert(limits.timestamp_divisor==16 && limits.timeout_period==65535);
        unchanged=controllers[0];
        bus.timestamp_divisor=0;
        assert(et_can_wrap_set_bus_config(0, &bus) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        bus.timestamp_divisor=17;
        assert(et_can_wrap_set_bus_config(0, &bus) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
        bus=observed; bus.unmatched_std=ET_CAN_UNMATCHED_POLICY_COUNT;
        assert(et_can_wrap_set_bus_config(0, &bus) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        bus=observed; bus.timeout_period=65536;
        assert(et_can_wrap_set_bus_config(0, &bus) == ET_WRAP_STATUS_INVALID_ARGUMENT);

        assert(et_can_wrap_set_loopback(0, ET_CAN_LOOPBACK_INTERNAL) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_loopback(0, &loop) == ET_WRAP_STATUS_OK && loop==ET_CAN_LOOPBACK_INTERNAL);
        assert(et_can_wrap_set_loopback(0, ET_CAN_LOOPBACK_EXTERNAL) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_loopback(0, &loop) == ET_WRAP_STATUS_OK && loop==ET_CAN_LOOPBACK_EXTERNAL);
        assert((CAN0->CCCR & CAN0_CCCR_MON_Msk)==0);
        assert(et_can_wrap_set_loopback(0, ET_CAN_LOOPBACK_DISABLED) == ET_WRAP_STATUS_OK);
        assert(et_can_wrap_get_loopback(0, &loop) == ET_WRAP_STATUS_OK && loop==ET_CAN_LOOPBACK_DISABLED);
        unchanged=controllers[0];
        assert(et_can_wrap_set_loopback(0, (et_can_loopback_t)99) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(memcmp(&unchanged, &controllers[0], sizeof(unchanged)) == 0);
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_NORMAL);
        assert(et_can_wrap_set_loopback(0, ET_CAN_LOOPBACK_INTERNAL) == ET_WRAP_STATUS_STATE_ERROR);
        assert(et_can_wrap_set_bus_config(0, &observed) == ET_WRAP_STATUS_STATE_ERROR);
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);

        for (unsigned i=0; i<11; ++i)
        {
            for (unsigned byte=0; byte<4; ++byte)
            {
                request[1+i*4+byte]=(uint8_t)(bus_words[i]>>(byte*8));
            }
        }
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_BUS_CONFIG_SET,
                                  request, 45, NULL, 0, &response_length) == ET_STATUS_OK);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_BUS_CONFIG_GET,
                                  request, 1, response, 44, &response_length) == ET_STATUS_OK);
        assert(response_length==44 && memcmp(request+1, response, 44)==0);
        request[1]=2;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_BUS_CONFIG_SET,
                                  request, 45, NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
    }


    /* Real host RAM exercises the SDK message packing, not a fake round-trip serializer. */
    {
        et_can_tx_frame_t outgoing = {0};
        et_can_rx_frame_t incoming;
        et_can_tx_status_t tx_status;
        et_can_rx_fifo_status_t fifo_status;
        et_can_rx_buffer_status_t buffer_status;
        CAN_RxBufElement raw;
        uint32_t *tx_words = (uint32_t *)(test_memory.ram + 24);
        uint32_t *rx_words = (uint32_t *)(test_memory.ram + 184);
        uint32_t *dedicated = (uint32_t *)(test_memory.ram + 760 + 63*72);

        assert((uintptr_t)CAN0 <= UINT32_MAX);
        assert((uint8_t *)CAN0 - test_memory.ram == 16384);
        CAN0->CCCR |= CAN0_CCCR_FDOE_Msk | CAN0_CCCR_BRSE_Msk;
        CAN0->TXBRP=0;
        outgoing.identifier=0x123;
        outgoing.flags=ET_CAN_FRAME_FD | ET_CAN_FRAME_BRS | ET_CAN_FRAME_STORE_EVENT;
        outgoing.dlc=15; outgoing.marker=0x5A;
        for (unsigned i=0; i<64; ++i) {outgoing.data[i]=(uint8_t)i;}
        assert(et_can_wrap_write_tx(0, 0, &outgoing) == ET_WRAP_STATUS_OK);
        assert(tx_words[0] == (0x123U << 18));
        assert(tx_words[1] == 0x5ABF0000U);
        assert(tx_words[2] == 0x03020100U && tx_words[17] == 0x3F3E3D3CU);
        CAN0->TXBRP=1;
        outgoing.data[0]=99;
        assert(et_can_wrap_write_tx(0, 0, &outgoing) == ET_WRAP_STATUS_BUSY);
        assert(tx_words[2] == 0x03020100U);
        CAN0->TXBRP=0;
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_NORMAL);
        CAN0->TXBAR=0x80;
        assert(et_can_wrap_request_tx(0, 3) == ET_WRAP_STATUS_OK && CAN0->TXBAR==3);
        assert(et_can_wrap_request_tx(0, 4) == ET_WRAP_STATUS_INVALID_ARGUMENT && CAN0->TXBAR==3);
        CAN0->TXBTO=1; CAN0->TXBCF=2;
        assert(et_can_wrap_get_tx_status(0, &tx_status) == ET_WRAP_STATUS_OK);
        assert(tx_status.completed==1 && tx_status.cancelled==2 && tx_status.pending==0);

        rx_words[0]=(0x321U << 18);
        rx_words[1]=0x003F1234U; /* FD BRS, DLC15, captured timestamp 0x1234. */
        for (unsigned i=0; i<16; ++i) {rx_words[2+i]=0xA0A0A000U+i;}
        CAN0->RXF0S=1; /* one entry, get index zero */
        assert(et_can_wrap_get_rx_fifo_status(0, 0, &fifo_status) == ET_WRAP_STATUS_OK);
        assert(fifo_status.fill==1 && fifo_status.get_index==0);
        assert(et_can_wrap_read_rx(0, ET_CAN_RX_FIFO0, 0, &incoming) == ET_WRAP_STATUS_OK);
        assert(incoming.identifier==0x321 && incoming.dlc==15 && incoming.timestamp==0x1234);
        assert(incoming.data_length==64 && incoming.index==0);
        assert(incoming.data[0]==0 && incoming.data[60]==15);
        assert(et_can_wrap_ack_rx_fifo(0, 0, 1) == ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_ack_rx_fifo(0, 0, 0) == ET_WRAP_STATUS_OK && CAN0->RXF0A==0);

        /* Slot capacity eight with DLC64: raw SDK must not read the following element. */
        CAN0->RXESC &= ~CAN0_RXESC_F0DS_Msk;
        memset(&raw, 0xCC, sizeof(raw));
        CAN_readMsgRam(CAN0, CAN_MEM_TYPE_FIFO, 0, CAN_RX_FIFO_NUM_0, &raw);
        assert(raw.data[7]==0xA0 && raw.data[8]==0xCCCC && raw.data[63]==0xCCCC);
        assert(et_can_wrap_read_rx(0, ET_CAN_RX_FIFO0, 0, &incoming) == ET_WRAP_STATUS_OK);
        assert(incoming.dlc==15 && incoming.data_length==8 && incoming.data[8]==0);
        CAN0->RXF0S=0;
        assert(et_can_wrap_read_rx(0, ET_CAN_RX_FIFO0, 0, &incoming) == ET_WRAP_STATUS_BUSY);

        dedicated[0]=(0x456U << 18); dedicated[1]=(8U << 16);
        dedicated[2]=0x44332211; dedicated[3]=0x88776655;
        CAN0->NDAT1=0; CAN0->NDAT2=0x80000000;
        assert(et_can_wrap_read_rx(0, ET_CAN_RX_BUFFER, 63, &incoming) == ET_WRAP_STATUS_OK);
        assert(incoming.identifier==0x456 && incoming.index==63 && incoming.data_length==8);
        assert(incoming.data[0]==0x11 && incoming.data[7]==0x88);
        assert(et_can_wrap_get_rx_buffer_status(0, &buffer_status) == ET_WRAP_STATUS_OK);
        assert(buffer_status.low==0 && buffer_status.high==0x80000000);
        assert(et_can_wrap_read_rx(0, ET_CAN_RX_BUFFER, 64, &incoming) == ET_WRAP_STATUS_INVALID_ARGUMENT);
    }


    /* Service sends the same public frame bytes to the real Driver and returns actual RAM. */
    {
        const uint32_t header[] = {0, 0x123, 12, 15, 0x5A};
        memset(request, 0, sizeof(request));
        for (unsigned i=0; i<5; ++i)
        {
            for (unsigned byte=0; byte<4; ++byte)
            {
                request[1+i*4+byte]=(uint8_t)(header[i]>>(byte*8));
            }
        }
        for (unsigned i=0; i<64; ++i) {request[21+i]=(uint8_t)i;}
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_WRITE,
                                  request, 85, NULL, 0, &response_length) == ET_STATUS_OK);
        assert(response_length==0);
        assert(*(uint32_t *)(test_memory.ram+24)==(0x123U<<18));
        assert(*(uint32_t *)(test_memory.ram+28)==0x5A3F0000U);
        assert(memcmp(test_memory.ram+32, request+21, 64)==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_READ,
                                  request, 5, response, 84, &response_length) == ET_STATUS_OK);
        assert(response_length==84 && memcmp(response, request+1, 84)==0);
        CAN0->CCCR |= CAN0_CCCR_WMM_Msk;
        request[17]=0xCD; request[18]=0xAB;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_WRITE,
                                  request, 85, NULL, 0, &response_length) == ET_STATUS_OK);
        assert(*(uint32_t *)(test_memory.ram+28)==0xCD3FAB00U);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_READ,
                                  request, 5, response, 84, &response_length) == ET_STATUS_OK);
        assert(response_length==84 && memcmp(response, request+1, 84)==0);
        CAN0->CCCR &= ~CAN0_CCCR_WMM_Msk;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_WRITE,
                                  request, 85, NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
        CAN0->TXBRP=1;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_READ,
                                  request, 5, response, 84, &response_length) == ET_STATUS_BUSY);
        CAN0->TXBRP=0;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_WRITE,
                                  request, 84, NULL, 0, &response_length) == ET_STATUS_INVALID_PARAM);
        memset(request, 0, sizeof(request)); request[5]=63;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RX_READ,
                                  request, 9, response, 96, &response_length) == ET_STATUS_OK);
        assert(response_length==96 && response[0]==0x56 && response[1]==0x04);
        assert(response[24]==8 && response[28]==63);
        assert(response[32]==0x11 && response[39]==0x88 && response[40]==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_RX_READ,
                                  request, 9, response, 95, &response_length) == ET_STATUS_INVALID_PARAM);
        assert(response_length==0);
        memset(request, 0, sizeof(request));
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_STATUS_GET,
                                  request, 1, response, 28, &response_length) == ET_STATUS_OK);
        assert(response_length==28 && response[4]==1 && response[8]==2);
    }

/* Filters read independently seeded RAM, including all eleven standard ID bits. */
    {
        et_can_filter_t filter = {ET_CAN_FILTER_DUAL, ET_CAN_FILTER_ACTION_FIFO0, 0x401, 0x7FF, 0};
        et_can_filter_t actual;
        et_can_high_priority_status_t high_priority;
        uint32_t mask;
        uint32_t *std_words = (uint32_t *)test_memory.ram;
        uint32_t *ext_words = (uint32_t *)(test_memory.ram + 8);
        CAN_StdMsgIDFilterElement std_actual;
        CAN_ExtMsgIDFilterElement ext_actual;
        const uint32_t wire[] = {1,0,3,2,0x10000001,0x1FFFFFFF,0};

        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);
        CAN0->SIDFC = (2U << CAN0_SIDFC_LSS_Pos);
        CAN0->XIDFC = (2U << CAN0_XIDFC_LSE_Pos) | 8U;
        assert(et_can_wrap_set_filter(0, 0, 0, &filter) == ET_WRAP_STATUS_OK);
        assert(std_words[0] == 0x4C0107FFU);
        std_words[0] = 0xA7FF0401U; /* MASK + PRIORITY + ID1=7FF, ID2=401 */
        assert(et_can_wrap_get_filter(0, 0, 0, &actual) == ET_WRAP_STATUS_OK);
        assert(actual.type==ET_CAN_FILTER_MASK && actual.action==ET_CAN_FILTER_ACTION_PRIORITY);
        assert(actual.id1==0x7FF && actual.id2==0x401 && actual.buffer_index==0);
        assert(CAN_testGetStdMsgIDFilter(CAN0, 2, &std_actual)==DRV_ERROR);
        assert(et_can_wrap_set_filter(0, 0, 2, &filter)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_get_filter(0, 0, 2, &actual)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        filter.type=ET_CAN_FILTER_RANGE_NO_MASK;
        assert(et_can_wrap_set_filter(0, 0, 0, &filter)==ET_WRAP_STATUS_INVALID_ARGUMENT);

        filter.action=ET_CAN_FILTER_ACTION_FIFO1;
        filter.id1=0x10000001; filter.id2=0x1FFFFFFF;
        assert(et_can_wrap_set_filter(0, 1, 0, &filter)==ET_WRAP_STATUS_OK);
        assert(ext_words[0]==0x50000001U && ext_words[1]==0xDFFFFFFFU);
        ext_words[0]=0x61234567U; ext_words[1]=0x4ABCDEF0U;
        assert(et_can_wrap_get_filter(0, 1, 0, &actual)==ET_WRAP_STATUS_OK);
        assert(actual.type==ET_CAN_FILTER_DUAL && actual.action==ET_CAN_FILTER_ACTION_REJECT);
        assert(actual.id1==0x01234567 && actual.id2==0x0ABCDEF0);
        assert(CAN_testGetExtMsgIDFilter(CAN0, 2, &ext_actual)==DRV_ERROR);
        filter.type=ET_CAN_FILTER_DISABLED;
        assert(et_can_wrap_set_filter(0, 1, 0, &filter)==ET_WRAP_STATUS_INVALID_ARGUMENT);

        filter=(et_can_filter_t){ET_CAN_FILTER_RANGE, ET_CAN_FILTER_ACTION_BUFFER, 0x7FF, 0, 63};
        assert(et_can_wrap_set_filter(0, 0, 1, &filter)==ET_WRAP_STATUS_OK);
        assert(std_words[1]==0x3FFF003FU);
        assert(et_can_wrap_get_filter(0, 0, 1, &actual)==ET_WRAP_STATUS_OK);
        assert(actual.buffer_index==63 && actual.id2==0 && actual.id1==0x7FF);
        filter.buffer_index=64;
        assert(et_can_wrap_set_filter(0, 0, 1, &filter)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        std_words[1] |= 0x100U; /* This basic API must not hide timestamp/debug mode. */
        assert(et_can_wrap_get_filter(0, 0, 1, &actual)==ET_WRAP_STATUS_NOT_SUPPORTED);
        filter.buffer_index=0;
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_NORMAL);
        assert(et_can_wrap_set_filter(0, 0, 1, &filter)==ET_WRAP_STATUS_STATE_ERROR);
        assert(et_can_wrap_set_extended_mask(0, 0x1FFFFFFF)==ET_WRAP_STATUS_STATE_ERROR);
        CAN_setOpMode(CAN0, CAN_OPERATION_MODE_SW_INIT);
        assert(et_can_wrap_set_extended_mask(0, 0x1FFFFFFF)==ET_WRAP_STATUS_OK);
        CAN0->XIDAM=0x12345678;
        assert(et_can_wrap_get_extended_mask(0, &mask)==ET_WRAP_STATUS_OK && mask==0x12345678);
        assert(et_can_wrap_set_extended_mask(0, 0x20000000)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(CAN0->XIDAM==0x12345678);

        memset(request, 0, sizeof(request));
        for (unsigned i=0; i<7; ++i)
        {
            for (unsigned byte=0; byte<4; ++byte)
            {
                request[1+i*4+byte]=(uint8_t)(wire[i]>>(byte*8));
            }
        }
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_FILTER_SET,
                                  request, 29, NULL, 0, &response_length)==ET_STATUS_OK);
        assert(ext_words[0]==0x50000001U && ext_words[1]==0xDFFFFFFFU);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_FILTER_GET,
                                  request, 9, response, 20, &response_length)==ET_STATUS_OK);
        assert(response_length==20 && memcmp(response, request+9, 20)==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_FILTER_GET,
                                  request, 9, response, 19, &response_length)==ET_STATUS_INVALID_PARAM);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_FILTER_SET,
                                  request, 28, NULL, 0, &response_length)==ET_STATUS_INVALID_PARAM);
        assert(response_length==0);

        CAN0->HPMS = 17U | (2U << 6) | (5U << 8) | (1U << 15);
        assert(et_can_wrap_get_high_priority_status(0, &high_priority)==ET_WRAP_STATUS_OK);
        assert(high_priority.buffer_index==17 && high_priority.storage==ET_CAN_HIGH_PRIORITY_FIFO0);
        assert(high_priority.filter_index==5 && high_priority.extended_filter==1);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET,
                                  request, 1, response, 16, &response_length)==ET_STATUS_OK);
        assert(response_length==16 && response[0]==17 && response[4]==2);
        assert(response[8]==5 && response[12]==1);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_HIGH_PRIORITY_STATUS_GET,
                                  request, 1, response, 15, &response_length)==ET_STATUS_INVALID_PARAM);
        assert(response_length==0);

        CAN0->SIDFC=(2U<<CAN0_SIDFC_LSS_Pos) | 0x3FFCU;
        assert(et_can_wrap_get_filter(0, 0, 0, &actual)==ET_WRAP_STATUS_INVALID_ARGUMENT);
    }

    /* First protocol/counter sample must survive field decoding, including CEL. */
    {
        et_can_protocol_status_t snapshot;
        et_can_service_t service;
        et_irq_manager_t manager={0};
        const et_service_descriptor_t *descriptor;
        uint8_t request[5]={0}, response[60]={0};
        uint16_t length=99;
        uint32_t value=0;
        CAN0->PSR=0x00345BEDU;
        CAN0->ECR=0x005ACB81U;
        consume_enabled=1; ecr_reads=0; psr_reads=0;
        assert(et_can_wrap_consume_protocol_status(0, &snapshot)==ET_WRAP_STATUS_OK);
        assert(ecr_reads==1 && psr_reads==1 && CAN0->ECR==0x0000CB81U);
        consume_enabled=0;
        assert(snapshot.last_error==ET_CAN_ERROR_BIT0);
        assert(snapshot.activity==ET_CAN_ACTIVITY_IDLE);
        assert(snapshot.error_passive==1 && snapshot.warning==1 && snapshot.bus_off==1);
        assert(snapshot.data_last_error==ET_CAN_ERROR_ACK);
        assert(snapshot.received_esi==1 && snapshot.received_brs==1);
        assert(snapshot.received_fd==0 && snapshot.protocol_exception==1);
        assert(snapshot.tdc_position==0x34);
        assert(snapshot.tx_error_count==0x81 && snapshot.rx_error_count==0x4B);
        assert(snapshot.rx_error_passive==1 && snapshot.error_log_count==0x5A);
        assert(et_can_wrap_consume_protocol_status(0, NULL)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_consume_protocol_status(7, &snapshot)==ET_WRAP_STATUS_NOT_SUPPORTED);
        CAN0->TSCV=0x1234;
        CAN0->TOCV=0xABCD;
        assert(et_can_wrap_get_timestamp(0, &value)==ET_WRAP_STATUS_OK && value==0x1234);
        assert(et_can_wrap_reset_timestamp(0)==ET_WRAP_STATUS_OK && CAN0->TSCV==0);
        assert(et_can_wrap_get_timeout_counter(0, &value)==ET_WRAP_STATUS_OK && value==0xABCD);
        CAN0->CCCR=0x1234;
        assert(et_can_wrap_set_clock_stop(0, 2)==ET_WRAP_STATUS_INVALID_ARGUMENT && CAN0->CCCR==0x1234);
        assert(et_can_wrap_set_clock_stop(0, 1)==ET_WRAP_STATUS_OK && CAN0->CCCR==0x1234);
        assert(et_can_wrap_set_clock_stop(0, 0)==ET_WRAP_STATUS_OK && CAN0->CCCR==0x1224);
        CAN0->CCCR=8;
        assert(et_can_wrap_get_clock_stop_ack(0, &value)==ET_WRAP_STATUS_OK && value==1);
        assert(et_can_service_init(&service,0,&manager,0)==0);
        descriptor=et_can_service_descriptor(&service);
        CAN0->ECR=0x005ACB81U;
        assert(descriptor->handle(descriptor->context,29,request,1,response,60,&length)==ET_STATUS_OK);
        assert(length==60 && response[0]==5 && response[40]==0x34 && response[56]==0x5A);
        assert(descriptor->handle(descriptor->context,29,request,1,response,59,&length)==ET_STATUS_INVALID_PARAM);
        assert(length==0);
        request[1]=2;
        assert(descriptor->handle(descriptor->context,33,request,5,NULL,0,&length)==ET_STATUS_INVALID_PARAM);
        assert(CAN0->CCCR==8);
    }

    /* One Event read uses one RAM-config query (four TXBC fields), keeping bounds checks. */
    {
        et_can_tx_event_t event;
        uint32_t *entry=(uint32_t *)&test_memory.ram[128];
        CAN0->TXEFC=(2U<<16)|128U;
        CAN0->TXEFS=(1U<<16)|1U;
        entry[0]=0x369U<<18;
        entry[1]=(0x10U<<24)|(1U<<22)|(8U<<16)|0x3456U;
        txbc_reads=0;
        assert(et_can_wrap_read_tx_event(0,&event)==ET_WRAP_STATUS_OK);
        assert(txbc_reads==4);
        assert(event.identifier==0x369 && event.marker==0x10 && event.index==0);
        assert(event.timestamp==0x3456 && event.dlc==8);
        et_can_tx_event_details_t details;
        assert(et_can_wrap_read_tx_event_details(0,&details)==ET_WRAP_STATUS_OK);
        assert(details.internal_timestamp_valid==1 && details.event.timestamp==0x3456);
        CAN0->CCCR |= CAN0_CCCR_WMM_Msk;
        entry[1]=0xCD48AB00U;
        assert(et_can_wrap_read_tx_event(0,&event)==ET_WRAP_STATUS_STATE_ERROR);
        assert(et_can_wrap_read_tx_event_details(0,&details)==ET_WRAP_STATUS_OK);
        assert(details.event.marker==0xABCD && details.internal_timestamp_valid==0);
        assert(details.event.timestamp==0 && details.tsu_captured==0 && details.tsu_pointer==0);
        CAN0->CCCR |= CAN0_CCCR_UTSU_Msk;
        entry[1]=0x3448121FU;
        assert(et_can_wrap_read_tx_event_details(0,&details)==ET_WRAP_STATUS_OK);
        assert(details.event.marker==0x1234 && details.internal_timestamp_valid==0);
        assert(details.event.timestamp==0 && details.tsu_captured==1 && details.tsu_pointer==15);
        memset(request,0,sizeof(request));
        assert(descriptor->handle(descriptor->context,61,request,1,response,40,&response_length)==ET_STATUS_OK);
        assert(response_length==40 && response[20]==0x34 && response[21]==0x12);
        assert(response[28]==0 && response[32]==1 && response[36]==15);
        assert(descriptor->handle(descriptor->context,61,request,1,response,39,&response_length)==ET_STATUS_INVALID_PARAM);
        CAN0->CCCR &= ~(CAN0_CCCR_WMM_Msk | CAN0_CCCR_UTSU_Msk);
        CAN0->TXEFS=0;
        assert(et_can_wrap_read_tx_event(0,&event)==ET_WRAP_STATUS_BUSY);
        CAN0->TXEFS=3;
        assert(et_can_wrap_read_tx_event(0,&event)==ET_WRAP_STATUS_IO_ERROR);
    }

    /* Public semantic sources route through Service and leave fixed IRQ evidence. */
    {
        const uint32_t watched = ET_CAN_IRQ_RX_FIFO0_NEW | ET_CAN_IRQ_TX_COMPLETE;
        et_can_irq_snapshot_t snapshot;
        uint8_t request[9]={0}, response[32]={0};
        uint16_t length=99;

        memset(bound_callback, 0, sizeof(bound_callback));
        memset(bound_context, 0, sizeof(bound_context));
        CAN0->IR=0;
        CAN0->IE=0;
        CAN0->ILS=0;
        CAN0->ILE=0;

        request[1]=(uint8_t)watched;
        request[2]=(uint8_t)(watched>>8);
        request[5]=(uint8_t)ET_CAN_IRQ_TX_COMPLETE;
        request[6]=(uint8_t)(ET_CAN_IRQ_TX_COMPLETE>>8);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_CAPTURE_START,
                                  request, 9, NULL, 0, &length)==ET_STATUS_OK);
        assert(length==0 && CAN0->IE==watched && CAN0->ILS==ET_CAN_IRQ_TX_COMPLETE);
        assert(CAN0->ILE==3 && bound_callback[0]!=NULL && bound_callback[1]!=NULL);
        assert(bound_irq_line[0]==CAN0_INT0_IRQn && bound_irq_line[1]==CAN0_INT1_IRQn);

        CAN0->IR=watched;
        bound_callback[0](bound_context[0], bound_irq_line[0], bound_route_events[0]);
        bound_callback[1](bound_context[1], bound_irq_line[1], bound_route_events[1]);
        assert(CAN0->IE==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_EVENT_GET,
                                  request, 1, response, 32, &length)==ET_STATUS_OK);
        assert(length==32);
        assert(*(uint32_t *)&response[0]==watched);
        assert(*(uint32_t *)&response[4]==ET_CAN_IRQ_RX_FIFO0_NEW);
        assert(*(uint32_t *)&response[8]==watched);
        assert(*(uint32_t *)&response[12]==2);
        assert(*(uint32_t *)&response[16]==0 && *(uint32_t *)&response[28]==0);
        assert(*(uint32_t *)&response[24]==1);

        /* Line evidence is attributed from the actual callback IRQ, not copied from ILS. */
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_LINE_EVENTS_GET,
                                  request, 1, response, 32, &length)==ET_STATUS_OK);
        assert(length==8 && *(uint32_t *)&response[0]==ET_CAN_IRQ_RX_FIFO0_NEW);
        assert(*(uint32_t *)&response[4]==ET_CAN_IRQ_TX_COMPLETE);

        assert(et_can_wrap_get_irq_snapshot(0, &snapshot)==ET_WRAP_STATUS_OK);
        assert(snapshot.raw_status==watched && snapshot.enabled_sources==0);
        assert(snapshot.line1_sources==ET_CAN_IRQ_TX_COMPLETE && snapshot.enabled_lines==3);
        /* A foreign physical line must still be diagnosed after removing the impossible mask test. */
        CAN0->IE=ET_CAN_IRQ_RX_FIFO0_NEW;
        bound_callback[0](bound_context[0], CAN1_INT0_IRQn, bound_route_events[0]);
        assert(service.irq_event[ET_CAN_IRQ_EVENT_UNEXPECTED_COUNT]==1);
        assert(service.irq_event[ET_CAN_IRQ_EVENT_FAULT_FLAGS] & ET_CAN_IRQ_FAULT_UNEXPECTED);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_CAPTURE_STOP,
                                  request, 1, NULL, 0, &length)==ET_STATUS_OK);
        assert(CAN0->ILE==0 && bound_callback[0]==NULL && bound_callback[1]==NULL);

        /* Preserve an unrelated pending bit too: a hidden clear would overwrite this stub IR. */
        CAN0->IR=watched | ET_CAN_IRQ_TIMEOUT;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_CAPTURE_PENDING,
                                  request, 9, NULL, 0, &length)==ET_STATUS_OK);
        assert(CAN0->IR==(watched | ET_CAN_IRQ_TIMEOUT));
        assert(service.irq_line_events[0]==0 && service.irq_line_events[1]==0);
        assert(service.irq_event[ET_CAN_IRQ_EVENT_COUNT]==0);
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_IRQ_CAPTURE_STOP,
                                  request, 1, NULL, 0, &length)==ET_STATUS_OK);

        /* A per-slot event does not enable global IE/ILE; invalid slots have no side effect. */
        CAN0->TXBC=1U<<CAN0_TXBC_NDTB_Pos;
        CAN0->TXBTIE=0;
        memset(request,0,sizeof(request)); request[5]=1;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_BUFFER_IRQ_SET,
                                  request, 9, NULL, 0, &length)==ET_STATUS_OK);
        assert(CAN0->TXBTIE==1 && CAN0->IE==0 && CAN0->ILE==0);
        request[1]=1;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_BUFFER_IRQ_SET,
                                  request, 9, NULL, 0, &length)==ET_STATUS_INVALID_PARAM);
        assert(CAN0->TXBTIE==1);
        request[1]=0; request[5]=2;
        assert(descriptor->handle(descriptor->context, ET_CAN_COMMAND_TX_BUFFER_IRQ_SET,
                                  request, 9, NULL, 0, &length)==ET_STATUS_INVALID_PARAM);
        assert(CAN0->TXBTIE==1);
    }

    /* One continuous reload changes no configuration/IRQ; FIFO mode rejects without writes. */
    {
        uint32_t before=0, after=0;
        timeout_write_count=0;
        for (unsigned i=0; i<3; ++i)
        {
            instances[i]->TOCC=((1000U+i)<<16)|1U;
            instances[i]->TOCV=7U+i;
            instances[i]->IR=0x20000U;
            uint32_t cccr=instances[i]->CCCR;
            assert(et_can_wrap_reload_timeout(i,&before,&after)==ET_WRAP_STATUS_OK);
            assert(before==7U+i && after==999U+i);
            assert(instances[i]->TOCC==(((1000U+i)<<16)|1U));
            assert(instances[i]->IR==0x20000U && instances[i]->CCCR==cccr);
            instances[i]->TOCC|=2U;
            assert(et_can_wrap_reload_timeout(i,&before,&after)==ET_WRAP_STATUS_STATE_ERROR);
        }
        assert(timeout_write_count==3);
        assert(et_can_wrap_reload_timeout(0,NULL,&after)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_reload_timeout(9,&before,&after)==ET_WRAP_STATUS_NOT_SUPPORTED);
        assert(timeout_write_count==3);
        CAN0->TOCC=1000U<<16; CAN0->TOCV=9U;
        request[0]=0;
        assert(descriptor->handle(descriptor->context,62,request,1,response,8,&response_length)==ET_STATUS_OK);
        assert(response_length==8 && response[0]==9 && response[4]==0xE7 && response[5]==3);
        assert(descriptor->handle(descriptor->context,62,request,1,response,7,&response_length)==ET_STATUS_INVALID_PARAM);
        assert(descriptor->handle(descriptor->context,62,request,2,response,8,&response_length)==ET_STATUS_INVALID_PARAM);
        assert(timeout_write_count==4);
    }

    /* Snapshot returns actual reset advancement and preserves configuration/IRQ per instance. */
    {
        uint32_t before=0, after=0;
        timestamp_snapshot_model=1; timestamp_write_count=0;
        for (unsigned i=0; i<3; ++i)
        {
            instances[i]->TSCC=(i<<16)|1U;
            instances[i]->TSCV=0x9000U+i;
            instances[i]->IR=0x10000U;
            uint32_t cccr=instances[i]->CCCR;
            assert(et_can_wrap_reset_timestamp_snapshot(i,&before,&after)==ET_WRAP_STATUS_OK);
            assert(before==0x9000U+i && after==1U);
            assert(instances[i]->TSCC==((i<<16)|1U) && instances[i]->CCCR==cccr);
            assert(instances[i]->IR==0x10000U);
            instances[i]->TSCC=2U;
            assert(et_can_wrap_reset_timestamp_snapshot(i,&before,&after)==ET_WRAP_STATUS_STATE_ERROR);
            instances[i]->TSCC=0;
            assert(et_can_wrap_reset_timestamp_snapshot(i,&before,&after)==ET_WRAP_STATUS_STATE_ERROR);
        }
        assert(timestamp_write_count==3);
        assert(et_can_wrap_reset_timestamp_snapshot(0,NULL,&after)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_reset_timestamp_snapshot(9,&before,&after)==ET_WRAP_STATUS_NOT_SUPPORTED);
        CAN0->TSCC=1U; CAN0->TSCV=0xABCDU; request[0]=0;
        assert(descriptor->handle(descriptor->context,63,request,1,response,8,&response_length)==ET_STATUS_OK);
        assert(response_length==8 && response[0]==0xCD && response[1]==0xAB && response[4]==1);
        assert(descriptor->handle(descriptor->context,63,request,1,response,7,&response_length)==ET_STATUS_INVALID_PARAM);
        assert(descriptor->handle(descriptor->context,63,request,2,response,8,&response_length)==ET_STATUS_INVALID_PARAM);
        assert(timestamp_write_count==4);
        timestamp_snapshot_model=0;
    }

    /* Bounded RAM primitive preserves per-word descending order and validates before mutation. */
    {
        uint32_t input[2]={0x12345678U,0xABCDEF01U}, output[2]={0};
        uint32_t *ram=(uint32_t *)test_memory.ram;
        CAN0->CCCR=CAN_OPERATION_MODE_SW_INIT;
        ram[0]=7; ram[1]=8;
        ram_trace_enabled=1; ram_trace_count=0;
        assert(et_can_wrap_access_ram(0,0,2,input,output,1)==ET_WRAP_STATUS_OK);
        ram_trace_enabled=0;
        assert(output[0]==7 && output[1]==8);
        assert(ram[0]==input[0] && ram[1]==input[1]);
        assert(ram_trace_count==2 && ram_trace[0]==4 && ram_trace[1]==0);
        assert(et_can_wrap_access_ram(0,1,2,input,output,0)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_access_ram(0,16380,2,input,output,0)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(et_can_wrap_access_ram(0,0,65,input,output,0)==ET_WRAP_STATUS_INVALID_ARGUMENT);
        assert(ram[0]==input[0] && ram[1]==input[1]);
        CAN0->CCCR=0;
        assert(et_can_wrap_access_ram(0,0,2,input,output,0)==ET_WRAP_STATUS_STATE_ERROR);
        assert(ram[0]==input[0] && ram[1]==input[1]);
    }

    return 0;
}
"""
