#include "et_manual_test_internal.h"

#include <stdint.h>

#include "et6x_dualcore.h"
#include "et_core1_peer_shared.h"
#include "et_manual_test_config.h"

/*
 * 测试Feature：Core0从目标链接地址启动Core1，并通过共享SRAM观测Core1身份和心跳。
 * 测试方法：清空AXI SRAM1 Mailbox，调用DUALCORE_startCore1，等待Core1发布READY和心跳。
 * 通过条件：Magic、Core Index和READY正确，且Heartbeat至少递增到目标值。
 */
int et_manual_dualcore_smoke(void)
{
    volatile et_core1_peer_mailbox_t *mailbox = ET_CORE1_PEER_MAILBOX;
    uint32_t wait_count = ET_CORE1_PEER_READY_WAIT_LIMIT;
    int result = ET_MANUAL_RESULT_PASS;

    /* 配置：清空本次Smoke唯一使用的共享Mailbox。 */
    mailbox->magic = 0u;
    mailbox->state = ET_CORE1_PEER_STATE_EMPTY;
    mailbox->core_index = 0u;
    mailbox->heartbeat = 0u;
    __DSB();

    et_manual_log_text("[MANUAL][dualcore_smoke] START\r\n");
    et_manual_log_u32("[CONFIG] core1_start_address", ET_CORE1_PEER_START_ADDRESS);
    et_manual_log_u32("[CONFIG] mailbox_address", (uint32_t)ET_CORE1_PEER_MAILBOX_ADDRESS);

    /* 激励：SDK Driver设置Core1启动地址、复位Core1并解除CPU WAIT。 */
    DUALCORE_startCore1(ET_CORE1_PEER_START_ADDRESS);

    /* 观测：等待Core1发布READY并产生至少两个心跳，证明代码持续运行。 */
    while ((wait_count > 0u) &&
           ((mailbox->state != ET_CORE1_PEER_STATE_READY) ||
            (mailbox->heartbeat < ET_CORE1_PEER_HEARTBEAT_TARGET)))
    {
        --wait_count;
        __DMB();
    }

    et_manual_log_u32("[OBSERVE] mailbox_magic", mailbox->magic);
    et_manual_log_u32("[OBSERVE] mailbox_state", mailbox->state);
    et_manual_log_u32("[OBSERVE] core_index", mailbox->core_index);
    et_manual_log_u32("[OBSERVE] heartbeat", mailbox->heartbeat);
    et_manual_log_u32("[EXPECT] mailbox_magic", ET_CORE1_PEER_MAILBOX_MAGIC);
    et_manual_log_u32("[EXPECT] core_index", ET_CORE1_PEER_EXPECTED_CORE_INDEX);

    /* 判断：只接受Core1写入的完整身份和持续执行证据。 */
    if ((wait_count == 0u) || (mailbox->magic != ET_CORE1_PEER_MAILBOX_MAGIC) ||
        (mailbox->state != ET_CORE1_PEER_STATE_READY) ||
        (mailbox->core_index != ET_CORE1_PEER_EXPECTED_CORE_INDEX) ||
        (mailbox->heartbeat < ET_CORE1_PEER_HEARTBEAT_TARGET))
    {
        result = ET_MANUAL_RESULT_FAIL;
    }

    et_manual_log_text((result == ET_MANUAL_RESULT_PASS) ?
                           "[MANUAL][dualcore_smoke] PASS\r\n" :
                           "[MANUAL][dualcore_smoke] FAIL\r\n");
    et_manual_log_text("[MANUAL][dualcore_smoke] END\r\n");

    return result;
}
