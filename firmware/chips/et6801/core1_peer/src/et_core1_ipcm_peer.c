/** @file et_core1_ipcm_peer.c @brief Core1 atomic IPCM executor, no Case algorithms. */
#if defined(ET_CORE1_PEER_IPCM)
#include "et6x_ipcm.h"
#include "et6x_dualcore.h"
#include "et_irq_wrap.h"
#include "et_ipcm_service.h"

/* Local logical IPCM instance and IRQ priority; only this peer target consumes these. */
#define ET_CORE1_IPCM_INSTANCE 0u
#define ET_CORE1_IPCM_IRQ_PRIORITY 3u
static et_irq_manager_t peer_irq;
static et_ipcm_service_t peer_service;
static uint8_t request[IPCM_TEST_PEER_BYTES];
static uint8_t response[IPCM_TEST_PEER_BYTES];

/**
 * @brief Initialize the independent core-local Service and process bounded commands.
 * @note Core1 does not configure shared mailboxes automatically. PC owns all stimulus,
 *       ACK/clear/release ordering and assertions. IRQ callbacks belong to IPCM Service.
 *       SRAM control transport is outside the measured IPCM data path; D-cache stays disabled.
 */
void et_core1_ipcm_peer_run(void)
{
    const et_service_descriptor_t *descriptor;
    uint16_t command, length, produced, status;
    uint32_t sequence, cancel;

    /* Phase 1: Publish readiness only after vectors, Manager and Service are usable. */
    et_irq_manager_init(&peer_irq);
    if ((et_irq_wrap_init() != ET_WRAP_STATUS_OK) || (et_irq_manager_activate(&peer_irq) != 0) ||
        (et_ipcm_service_init(&peer_service, ET_CORE1_IPCM_INSTANCE, &peer_irq,
                              ET_CORE1_IPCM_IRQ_PRIORITY) != 0))
    {
        return;
    }
    descriptor = et_ipcm_service_descriptor(&peer_service);
    __enable_irq();
    IPCM_testPeerInitialize(DUALCORE_getCurrentCoreId());

    /* Phase 2: Each poll executes at most one atomic command, then services pending capture. */
    for (;;)
    {
        if (IPCM_testPeerTake(&command, request, &length, &sequence, &cancel) == DRV_OK)
        {
            produced = 0u;
            if (cancel != 0u)
            {
                command = ET_IPCM_COMMAND_STATE_RESET;
                length = 0u;
            }
            /* Peer forwarding is forbidden here: the request must terminate on this core. */
            status = ET_STATUS_INVALID_COMMAND;
            if (command < ET_IPCM_COMMAND_PEER_SUBMIT)
            {
                status = descriptor->handle(descriptor->context, command, request, length, response,
                                            sizeof(response), &produced);
            }
            (void)IPCM_testPeerComplete(sequence, status, response, produced, cancel);
        }
        descriptor->poll(descriptor->context);
    }
}
#endif
