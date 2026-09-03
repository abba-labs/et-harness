# IPCM 原始 Driver、公共 Wrap 和 Service 的本机软件合同测试。
# 职责：执行真实 C 源码，检查边界、命令编码、事件保存和原子动作隔离。
# 边界：寄存器替身只提供软件观测，不证明目标芯片 ACK、Linked 或双核硬件行为。
# 依赖：pytest、C 编译器；编译器通过当前进程 PATH 提供，不写死电脑路径。

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
CHIP = ROOT / "firmware/chips/et6801"

# 这是 C 编译输入，不是 Python 注释或文档字符串。
# 寄存器名称来自实际 Driver；没有模拟自动 ACK 或 SOURCE 释放的硬件结论。
REGISTER_STUB = r"""
#ifndef ET6X_H
#define ET6X_H
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
typedef enum {DRV_OK=0, DRV_ERROR=1, DRV_PARAM_ERR=3, DRV_BUSY=5} DRV_Status;
extern uint32_t peer_memory[1024];
#define AXI_SRAM1_BASE ((uintptr_t)peer_memory)
#define __DMB() ((void)0)
#define __DSB() ((void)0)
typedef struct {
    uint32_t SOURCE,DSET,DCLEAR,DSTATUS,MODE,MSET,MCLEAR,MSTATUS,SEND,DR[7];
} Mailbox;
typedef struct {uint32_t MIS,RIS;} Pending;
typedef struct {Mailbox MBOX[16]; Pending ISR[16]; uint32_t CFGSTAT;} IPCM_Type;
typedef struct {uint32_t SL_LOCK_INFO_ARRAY[16];} SPINLOCK_Type;
#define SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Msk 0xff00u
#define SPINLOCK_SL_LOCK_INFO_ARRAY_SL_LOCK_INFO_SL_LOCK_INFO_PROCESS_ID_Pos 8u
extern IPCM_Type ipcm_registers;
#define IPCM (&ipcm_registers)
extern unsigned writes;
void register_write(uint32_t *reg, uint32_t value);
#define READ_REG(reg) (reg)
#define WRITE_REG(reg, value) register_write(&(reg),(value))
#define BIT_MASK(bit) (1u << (bit))
#define assert_param(condition) assert(condition)
#endif
"""

HARNESS = r"""
#include <stdio.h>
#include <string.h>
#include "et6x_ipcm.h"
#include "et_ipcm_service.h"

IPCM_Type ipcm_registers;
uint32_t peer_memory[1024];
unsigned writes;
static et_irq_callback_t callbacks[ET_IPCM_SERVICE_CAPTURE_SLOTS];
static void *contexts[ET_IPCM_SERVICE_CAPTURE_SLOTS];
static et_irq_route_t routes[ET_IPCM_SERVICE_CAPTURE_SLOTS];
static unsigned binds, unbinds;

/* Model only direct register writes plus MSET/MCLEAR and DSET/DCLEAR aliases. */
void register_write(uint32_t *reg, uint32_t value)
{
    ++writes;
    *reg = value;
    for (unsigned m=0; m<16; ++m) {
        Mailbox *box=&IPCM->MBOX[m];
        if (reg==&box->MSET) box->MSTATUS |= value;
        if (reg==&box->MCLEAR) box->MSTATUS &= ~value;
        if (reg==&box->DSET) box->DSTATUS |= value;
        if (reg==&box->DCLEAR) box->DSTATUS &= ~value;
    }
    for (unsigned c=0; c<16; ++c) {
        uint32_t enabled=0;
        for (unsigned m=0; m<16; ++m)
            if (IPCM->MBOX[m].MSTATUS & (1u<<c)) enabled |= 1u<<m;
        IPCM->ISR[c].MIS=IPCM->ISR[c].RIS & enabled;
    }
}

uint32_t et_irq_manager_enter_critical(void) {return 0;}
void et_irq_manager_exit_critical(uint32_t key) {(void)key;}
int et_irq_manager_bind(et_irq_manager_t *manager, const et_irq_route_t *route,
    uint8_t priority, et_irq_callback_t callback, void *context)
{
    (void)manager; (void)priority;
    for(unsigned i=0;i<ET_IPCM_SERVICE_CAPTURE_SLOTS;++i)
        if(!callbacks[i]) {
            callbacks[i]=callback; contexts[i]=context; routes[i]=*route; ++binds; return 0;
        }
    return -1;
}
int et_irq_manager_unbind(et_irq_manager_t *manager, et_irq_line_t line,
    et_irq_callback_t callback, void *context)
{
    (void)manager;
    for(unsigned i=0;i<ET_IPCM_SERVICE_CAPTURE_SLOTS;++i)
        if(callbacks[i]==callback && contexts[i]==context && routes[i].irq_line==line) {
            callbacks[i]=NULL; ++unbinds; return 0;
        }
    return 0;
}

static void put16(uint8_t *bytes, uint16_t value) {bytes[0]=value; bytes[1]=value>>8;}
static uint32_t get32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] | (uint32_t)bytes[1]<<8 | (uint32_t)bytes[2]<<16 | (uint32_t)bytes[3]<<24;
}

static void driver_contract(void)
{
    uint8_t source[64], actual[64];
    IPCM_TestCapabilities caps;
    IPCM_TestPendingSnapshot pending;
    IPCM_TestMailboxSnapshot snapshot;
    unsigned previous;

    memset(IPCM,0,sizeof(*IPCM));
    IPCM->CFGSTAT=0x00101007;
    assert(IPCM_testGetCapabilities(&caps)==DRV_OK);
    assert(caps.mailboxCount==16 && caps.channelCount==16 && caps.dataWordCount==7);
    assert(IPCM_testConfigureMailboxes(0,1,1u<<11,1u<<10,MANUAL_ACK,0)==DRV_OK);

    for(unsigned i=0;i<sizeof(source);++i) source[i]=(uint8_t)(17+37*i);
    /* Exercise every byte length, including an intentionally unaligned source. */
    for(unsigned n=1;n<=28;++n) {
        memset(actual,0xcc,sizeof(actual));
        assert(IPCM_testWritePayloadExact(0,1,source+1,n)==DRV_OK);
        assert(IPCM_testReadPayloadExact(0,actual+1,n)==DRV_OK);
        assert(memcmp(source+1,actual+1,n)==0);
        assert(actual[0]==0xcc && actual[n+1]==0xcc);
        if(n%4) assert((IPCM->MBOX[0].DR[n/4] >> (8*(n%4)))==0);
        assert(IPCM->MBOX[0].SEND==0);
    }

    previous=writes;
    assert(IPCM_testWritePayloadExact(0,1,source,29)==DRV_PARAM_ERR);
    assert(IPCM_testConfigureMailboxes(15,2,1,2,AUTO_LINK,0)==DRV_PARAM_ERR);
    assert(IPCM_testConfigureMailboxes(0,1,3,4,MANUAL_ACK,0)==DRV_PARAM_ERR);
    assert(IPCM_testConfigureMailboxes(0,1,1,2,MANUAL_ACK,4)==DRV_PARAM_ERR);
    assert(IPCM_testConfigureMailboxes(0,1,1,1,MANUAL_ACK,0)==DRV_PARAM_ERR);
    assert(writes==previous);

    assert(IPCM_testConfigureMailboxes(14,2,1,2,AUTO_ACK_LINK,3)==DRV_OK);
    assert(IPCM->MBOX[14].MODE==AUTO_ACK_LINK && IPCM->MBOX[15].MODE==AUTO_ACK);
    assert(IPCM_testWritePayloadExact(14,2,source,31)==DRV_OK);
    assert(IPCM_testReadPayloadExact(14,actual,28)==DRV_OK);
    assert(IPCM_testReadPayloadExact(15,actual+28,3)==DRV_OK);
    assert(memcmp(source,actual,31)==0);

    IPCM->ISR[10].RIS=(1u<<0)|(1u<<7);
    IPCM->ISR[10].MIS=1u<<7;
    assert(IPCM_testGetPendingSnapshot(10,&pending)==DRV_OK);
    assert(pending.raw==129 && pending.masked==128);
    assert(IPCM_testGetMailboxSnapshot(14,&snapshot)==DRV_OK);
    assert(snapshot.source==1 && snapshot.destination==2 && snapshot.interruptEnable==3);

    assert(IPCM_testSendMessage(0)==DRV_OK && IPCM->MBOX[0].SEND==1);
    previous=writes;
    assert(IPCM_testConfigureMailboxes(0,1,1,2,MANUAL_ACK,0)==DRV_BUSY && writes==previous);
    assert(IPCM_testSendAck(0)==DRV_OK && IPCM->MBOX[0].SEND==2);
    assert(IPCM_testClearPending(0)==DRV_OK && IPCM->MBOX[0].SEND==0);
    assert(IPCM_testReleaseMailboxes(14,2)==DRV_OK);
    assert(IPCM->MBOX[14].SOURCE==0 && IPCM->MBOX[15].SOURCE==0);
    /* No invented cleanup writes: the release action is SOURCE=0 only. */
    assert(IPCM->MBOX[14].MODE==AUTO_ACK_LINK);
}

static void service_contract(void)
{
    et_ipcm_service_t service;
    et_irq_manager_t manager;
    uint8_t request[32]={0}, response[256]={0};
    uint16_t length;
    const et_service_descriptor_t *descriptor;
    unsigned before;

    memset(IPCM,0,sizeof(*IPCM));
    IPCM->CFGSTAT=0x00101007;
    assert(et_ipcm_service_init(&service,0,&manager,3)==0);
    descriptor=et_ipcm_service_descriptor(&service);
    assert(descriptor->service_id==0x0109);
#define CALL(cmd,req,len) descriptor->handle(&service,(cmd),(req),(len),response,sizeof(response),&length)
    assert(CALL(ET_IPCM_COMMAND_CAPABILITIES_GET,NULL,0)==ET_STATUS_OK);
    assert(length==16 && get32(response)==0x00100001);
    assert(response[4]==16 && response[6]==16 && response[8]==7 && response[10]==28);
    assert(CALL(0xffff,NULL,0)==ET_STATUS_INVALID_COMMAND);
    assert(CALL(ET_IPCM_COMMAND_CONFIGURE,request,19)==ET_STATUS_INVALID_PARAM);

    put16(request,0); put16(request+2,1);
    request[5]=8; /* source = logical endpoint 11 */
    request[9]=4; /* destination = logical endpoint 10 */
    assert(CALL(ET_IPCM_COMMAND_CONFIGURE,request,20)==ET_STATUS_OK);
    assert(IPCM->MBOX[0].SOURCE==(1u<<11));

    memset(request,0,sizeof(request));
    put16(request+2,10); put16(request+4,0); put16(request+6,3); request[8]=1;
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_ARM,request,10)==ET_STATUS_OK);
    assert(binds==1 && IPCM->MBOX[0].MSTATUS==(1u<<10));

    /* Inject pending, then dispatch via the registered callback: not a HIL result. */
    IPCM->MBOX[0].DR[0]=0x00332211;
    IPCM->ISR[10].RIS=1;
    IPCM->ISR[10].MIS=1;
    callbacks[0](contexts[0],routes[0].irq_line,routes[0].route_events);
    assert(IPCM->MBOX[0].MSTATUS==0 && IPCM->ISR[10].RIS==1);
    assert(IPCM->MBOX[0].SEND==0 && IPCM->MBOX[0].DSTATUS==(1u<<10));
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_GET,request,2)==ET_STATUS_OK);
    assert(length==45 && get32(response+4)==1 && get32(response+8)==1);
    assert(get32(response+16)==1 && response[42]==0x11 && response[44]==0x33);
    assert(response[40]==ET_IPCM_SERVICE_STAGE_MESSAGE);

    IPCM->ISR[10].RIS=0;
    IPCM->MBOX[0].DR[0]=0;
    callbacks[0](contexts[0],routes[0].irq_line,routes[0].route_events);
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_GET,request,2)==ET_STATUS_OK);
    assert(get32(response+16)==1 && response[42]==0x11);
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_ABORT,request,2)==ET_STATUS_OK && unbinds==1);

    /* Polling latches the full pending set but must never increment IRQ callback count. */
    request[8]=0;
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_ARM,request,10)==ET_STATUS_OK);
    IPCM->ISR[10].RIS=129; IPCM->ISR[10].MIS=0;
    descriptor->poll(&service);
    assert(CALL(ET_IPCM_COMMAND_CAPTURE_GET,request,2)==ET_STATUS_OK);
    assert(get32(response+4)==129 && get32(response+8)==0 && get32(response+16)==0);
    assert(get32(response)==2);
    before=writes;
    assert(CALL(ET_IPCM_COMMAND_STATE_RESET,NULL,0)==ET_STATUS_OK);
    assert(writes==before && IPCM->ISR[10].RIS==129);
    assert(service.slots[0].event.generation==2 && service.slots[0].event.state==ET_IPCM_CAPTURE_IDLE);
#undef CALL
}

/* Shared control transport only: no simulated IPCM hardware PASS. */
static void peer_contract(void)
{
    uint8_t request[]={0x11,0x22,0x33}, body[IPCM_TEST_PEER_BYTES];
    uint16_t command, length;
    uint32_t sequence, taken, cancel, cancelled;
    IPCM_TestPeerResult result;
    et_ipcm_service_t service;
    et_irq_manager_t manager;
    const et_service_descriptor_t *descriptor;
    uint8_t response[ET_IPCM_SERVICE_PEER_HEADER_SIZE+IPCM_TEST_PEER_BYTES];
    uint16_t produced;

    assert(IPCM_testPeerSubmit(1,NULL,0,&sequence)!=DRV_OK);
    IPCM_testPeerInitialize(2);
    assert(IPCM_testPeerResult(&result)==DRV_OK && result.state==IPCM_TEST_PEER_IDLE);
    assert(result.coreId==2);
    assert(IPCM_testPeerSubmit(6,request,sizeof(request),&sequence)==DRV_OK);
    assert(IPCM_testPeerSubmit(6,request,sizeof(request),&taken)!=DRV_OK);
    assert(IPCM_testPeerResult(&result)==DRV_OK && result.state==IPCM_TEST_PEER_QUEUED);
    assert(result.length==0);
    assert(IPCM_testPeerTake(&command,body,&length,&taken,&cancel)==DRV_OK);
    assert(command==6 && length==3 && taken==sequence && cancel==0);
    assert(memcmp(body,request,3)==0);
    assert(IPCM_testPeerComplete(taken,0,body,3,0)==DRV_OK);
    assert(IPCM_testPeerResult(&result)==DRV_OK && result.state==IPCM_TEST_PEER_DONE);
    assert(result.length==3 && memcmp(result.data,request,3)==0);

    /* Cancellation invalidates an in-flight completion and requires Core1 acknowledgment. */
    assert(IPCM_testPeerSubmit(1,NULL,0,&sequence)==DRV_OK);
    assert(IPCM_testPeerTake(&command,body,&length,&taken,&cancel)==DRV_OK);
    assert(IPCM_testPeerCancel(&cancelled)==DRV_OK && cancelled!=taken);
    assert(IPCM_testPeerComplete(taken,0,NULL,0,0)!=DRV_OK);
    assert(IPCM_testPeerTake(&command,body,&length,&taken,&cancel)==DRV_OK && cancel==1);
    assert(IPCM_testPeerComplete(taken,0,NULL,0,1)==DRV_OK);
    assert(IPCM_testPeerResult(&result)==DRV_OK && result.state==IPCM_TEST_PEER_CANCELLED);
    assert(result.sequence==cancelled && result.length==0);

    /* Execute the original atomic Service body and read its exact bytes through the envelope. */
    assert(et_ipcm_service_init(&service,0,&manager,3)==0);
    descriptor=et_ipcm_service_descriptor(&service);
    put16(body,ET_IPCM_COMMAND_CAPABILITIES_GET);
    assert(descriptor->handle(&service,ET_IPCM_COMMAND_PEER_SUBMIT,body,2,
        response,sizeof(response),&produced)==ET_STATUS_OK && produced==4);
    sequence=get32(response);
    assert(IPCM_testPeerTake(&command,body,&length,&taken,&cancel)==DRV_OK);
    assert(descriptor->handle(&service,command,body,length,response,sizeof(response),
        &produced)==ET_STATUS_OK);
    assert(IPCM_testPeerComplete(taken,0,response,produced,0)==DRV_OK);
    assert(descriptor->handle(&service,ET_IPCM_COMMAND_PEER_RESULT,NULL,0,response,
        sizeof(response),&produced)==ET_STATUS_OK);
    assert(produced==36 && get32(response)==sequence && response[4]==IPCM_TEST_PEER_DONE);
    assert(get32(response+12)==2 && get32(response+20)==0x00100001);
    put16(body,ET_IPCM_COMMAND_PEER_SUBMIT);
    assert(descriptor->handle(&service,ET_IPCM_COMMAND_PEER_SUBMIT,body,2,response,
        sizeof(response),&produced)==ET_STATUS_INVALID_PARAM);

    /* A ready image with a different transport tag must not be accepted. */
    peer_memory[4]=0;
    assert(IPCM_testPeerResult(&result)!=DRV_OK);
}

int main(void)
{
    driver_contract();
    service_contract();
    peer_contract();
    puts("ipcm_native=PASS");
    return 0;
}
"""


# 从生成头文件提取本 Driver 的 CFGSTAT 字段与 IRQ 符号，不复制人工常量表。
def _chip_symbols() -> str:

    cmsis = (CHIP / "sdk/CMSIS/Device/Include/et6801.h").read_text(encoding="utf-8")
    fields = re.findall(r"^#define\s+IPCM_IPCMCFGSTAT_\w+[^\n]*", cmsis, re.MULTILINE)
    irqs = re.findall(r"\b(IPCM\d+_IRQn)\s*=\s*(\d+)", cmsis)
    assert len(fields) >= 6 and len(irqs) == 16
    return "\n".join([*fields, *(f"#define {name} {value}" for name, value in irqs)])


# 测试 Feature：IPCM 原子命令、非对齐 Payload、Linked 边界和事件保存。
# 测试方法：1. 编译真实 Driver、Wrap、Service，只替换寄存器与 IRQ Manager。
#           2. 遍历 Payload 长度；验证非法请求不写硬件，捕获先读后暂停中断。
#           3. 验证 Polling 不计 IRQ，历史快照不被即时状态覆盖，Reset 不冒充 IP 复位。
# 通过条件：所有 C 断言成立，程序正常退出；该结果只记为软件合同通过。
def test_ipcm_driver_wrap_service_native(tmp_path: Path) -> None:

    compiler = shutil.which("gcc") or shutil.which("clang") or shutil.which("cc")
    if compiler is None:
        pytest.skip("a native C compiler is required for IPCM software contracts")

    # 在隔离临时目录编译原始源码；只替换最底层硬件依赖。
    (tmp_path / "et6x.h").write_text(REGISTER_STUB + "\n" + _chip_symbols(), encoding="utf-8")
    shutil.copy2(CHIP / "sdk/ET6x_Driver/Inc/et6x_ipcm.h", tmp_path / "et6x_ipcm.h")
    harness = tmp_path / "ipcm_harness.c"
    harness.write_text(HARNESS, encoding="utf-8")
    executable = tmp_path / "ipcm_harness.exe"
    command = [compiler, "-std=c11", "-Wall", "-Wextra", "-DET_ENABLE_TEST_DRIVER_EXTENSIONS"]

    # Wrap 和 Service 使用仓库原有头文件及 Chip Config，不使用测试专用实现。
    for include in (
        tmp_path,
        CHIP / "config",
        ROOT / "firmware/wrap/include",
        ROOT / "firmware/services/include",
        ROOT / "firmware/framework/include",
    ):
        command.extend(("-I", str(include)))
    command.extend(
        str(path)
        for path in (
            harness,
            CHIP / "sdk/ET6x_Driver/Src/et6x_ipcm.c",
            ROOT / "firmware/wrap/src/et_ipcm_wrap.c",
            ROOT / "firmware/services/src/et_ipcm_service.c",
        )
    )
    command.extend(("-o", str(executable)))
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    # 运行有界本机程序，任何断言失败或挂起都失败，不转换成 SKIP。
    result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "ipcm_native=PASS"
