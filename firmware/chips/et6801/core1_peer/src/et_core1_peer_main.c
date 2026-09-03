/**
 * @file et_core1_peer_main.c
 * @brief ET6801 Core1 peer entry for dual-core smoke and SPINLOCK jobs.
 */

#include "et6x_spinlock.h"
#if defined(ET_CORE1_PEER_IPCM)
void et_core1_ipcm_peer_run(void);
#endif

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
#if defined(ET_CORE1_PEER_IPCM)
    et_core1_ipcm_peer_run();
#else
    SPINLOCK_testPeerRunForever();
#endif

    return 0;
}
