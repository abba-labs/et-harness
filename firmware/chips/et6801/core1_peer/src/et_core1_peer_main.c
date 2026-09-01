/**
 * @file et_core1_peer_main.c
 * @brief ET6801 Core1 peer entry for dual-core smoke and SPINLOCK jobs.
 */

#include "et6x_spinlock.h"

/**
 * @brief Publish Core1 readiness and serve chip-owned SPINLOCK Peer Jobs.
 *
 * @note The selected SPINLOCK Driver owns the ET6801 mailbox layout, hardware Master mapping and
 *       shared-memory barriers. This entry does not implement Case logic or the PC protocol.
 *
 * @return This function does not return during normal execution.
 */
int main(void)
{
    SPINLOCK_testPeerRunForever();

    return 0;
}
